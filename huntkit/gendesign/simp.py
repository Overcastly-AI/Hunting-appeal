"""SIMP topology optimization on structured voxel/pixel grids (2D Q4 plane stress, 3D H8).

    min_x  sum_c w_c * F_c^T U_c        (weighted multi-load-case compliance)
    s.t.   K(xPhys) U_c = F_c,  mean(xPhys over the design region) <= volfrac,  0 <= x <= 1
    E(xPhys) = Emin + xPhys^p (E0 - Emin)

Pipeline per iteration: density filter (hat, radius rmin) -> Heaviside projection (beta
continuation, eta 0.5; Wang/Lazarov/Sigmund 2011) -> passive solid/void override -> FE solve
(AMG-PCG) -> sensitivities (chain rule through projection and filter) -> optimality-criteria
update with bisection on the volume constraint.

Minimum member size: the filter radius sets the length scale (~ rmin for eta = 0.5 projection,
not a hard guarantee; the measured minimum wall of the result is reported by
``min_feature_mm``). Overhang: handled at the orientation step (``surface.best_orientation``),
not inside the optimization.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .fem import Assembler, Grid, Solver, density_filter, ke_h8, ke_q4


@dataclass
class SimpProblem:
    grid: Grid
    loads: np.ndarray                      # (ndof, ncases)
    fixed: np.ndarray                      # bool (ndof,)
    passive_solid: np.ndarray | None = None   # bool (ne,)
    passive_void: np.ndarray | None = None    # bool (ne,)
    volfrac: float = 0.15
    rmin_vox: float = 1.5
    penal: float = 3.0
    E0: float = 1.0
    nu: float = 0.3
    Emin_ratio: float = 1e-6
    weights: np.ndarray | None = None
    thickness: float = 1.0                 # 2D only


@dataclass
class SimpResult:
    x: np.ndarray
    xPhys: np.ndarray
    history: list = field(default_factory=list)       # dicts: it, compliance, volume, change, beta
    U: np.ndarray | None = None
    compliance: float = np.nan
    seconds: float = 0.0


def _project(xt, beta, eta=0.5):
    if beta <= 0:
        return xt, np.ones_like(xt)
    d = np.tanh(beta * eta) + np.tanh(beta * (1 - eta))
    xp = (np.tanh(beta * eta) + np.tanh(beta * (xt - eta))) / d
    dx = beta * (1 - np.tanh(beta * (xt - eta)) ** 2) / d
    return xp, dx


def run_simp(pb: SimpProblem, iters: int = 60, beta_schedule=(0, 1, 2, 4, 8), beta_every: int = 12,
             move: float = 0.2, tol_change: float = 0.005, log=None, solver_tol: float = 1e-7) -> SimpResult:
    g = pb.grid
    t0 = time.time()
    KE = ke_h8(g.h, 1.0, pb.nu) if g.dim == 3 else ke_q4(g.h, 1.0, pb.nu, pb.thickness)
    ps = np.zeros(g.ne, bool) if pb.passive_solid is None else pb.passive_solid.copy()
    pv = np.zeros(g.ne, bool) if pb.passive_void is None else (pb.passive_void & ~ps)
    # nodes touched only by passive-void elements carry nothing: drop them (better CG conditioning)
    fixed = pb.fixed.copy()
    act = np.zeros(g.nn, bool)
    act[np.unique(g.enodes[~pv])] = True
    fixed |= np.repeat(~act, g.dim)
    asm = Assembler(g.edof, g.ndof, KE, fixed)
    solver = Solver(g.node_coords(), fixed, tol=solver_tol)
    design = ~(ps | pv)
    H, Hs = density_filter(g, pb.rmin_vox)
    F = pb.loads.reshape(g.ndof, -1).copy()
    F[fixed] = 0.0
    w = np.ones(F.shape[1]) if pb.weights is None else np.asarray(pb.weights, float)
    Emin = pb.Emin_ratio * pb.E0

    x = np.where(ps, 1.0, np.where(pv, 0.0, pb.volfrac))
    hist = []
    U = None
    beta_i = 0

    def phys(xv, beta):
        xt = H @ xv / Hs
        xp, dxp = _project(xt, beta)
        xp = np.where(ps, 1.0, np.where(pv, 0.0, xp))
        return xp, dxp

    beta = beta_schedule[0]
    xPhys, dproj = phys(x, beta)
    loop_change = 1.0
    for it in range(1, iters + 1):
        E = Emin + xPhys ** pb.penal * (pb.E0 - Emin)
        K = asm.assemble(E)
        U = solver.solve(K, F, x0=U)
        ce = np.zeros(g.ne)
        for c in range(F.shape[1]):
            Ue = U[g.edof, c]
            ce += w[c] * np.einsum("ij,jk,ik->i", Ue, KE, Ue)
        comp = float(np.sum(E * ce))
        dc = -pb.penal * xPhys ** (pb.penal - 1) * (pb.E0 - Emin) * ce
        dv = np.ones(g.ne)
        dc = np.where(design, dc * dproj, 0.0)
        dv = np.where(design, dv * dproj, 0.0)
        dc = H.T @ (dc / Hs)
        dv = H.T @ (dv / Hs)
        dc = np.minimum(dc, -1e-30)
        dv = np.maximum(dv, 1e-30)
        # OC with bisection on the projected volume of the design region
        l1, l2 = 1e-12, 1e12
        xd = x[design]
        Be = np.sqrt(-dc[design] / dv[design])
        nd = design.sum()
        while (l2 - l1) / (l1 + l2) > 1e-4:
            lm = np.sqrt(l1 * l2)
            xn = x.copy()
            xn[design] = np.clip(xd * Be / np.sqrt(lm), np.maximum(0.0, xd - move), np.minimum(1.0, xd + move))
            xp, _ = phys(xn, beta)
            if xp[design].sum() / nd > pb.volfrac:
                l1 = lm
            else:
                l2 = lm
        loop_change = float(np.abs(xn - x).max())
        x = xn
        xPhys, dproj = phys(x, beta)
        vol = float(xPhys[design].mean())
        hist.append({"it": it, "compliance": comp, "volume": vol, "change": loop_change, "beta": beta,
                     "cg_iters": list(solver.last_iters)})
        if log:
            log(f"  it {it:3d}  c={comp:.4g}  vol={vol:.3f}  ch={loop_change:.3f}  beta={beta}  cg={solver.last_iters}")
        if (it % beta_every == 0 or loop_change < tol_change) and beta_i + 1 < len(beta_schedule):
            beta_i += 1
            beta = beta_schedule[beta_i]
            xPhys, dproj = phys(x, beta)
        elif loop_change < tol_change and beta_i + 1 >= len(beta_schedule):
            break
    # final state
    E = Emin + xPhys ** pb.penal * (pb.E0 - Emin)
    K = asm.assemble(E)
    U = solver.solve(K, F, x0=U)
    comp = float(sum(w[c] * F[:, c] @ U[:, c] for c in range(F.shape[1])))
    return SimpResult(x=x, xPhys=xPhys, history=hist, U=U, compliance=comp, seconds=time.time() - t0)


# ----------------------------------------------------------------------------- benchmarks
def mbb_problem(nelx=120, nely=40, volfrac=0.5, rmin=2.0) -> SimpProblem:
    """Half MBB beam (Sigmund 99-line / Andreassen top88): left edge symmetric (ux = 0), bottom-right
    roller (uy = 0), unit downward load at the top-left corner."""
    g = Grid((nelx, nely), 1.0)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    left = np.where(np.isclose(nc[:, 0], 0))[0]
    fixed[2 * left] = True
    br = np.where(np.isclose(nc[:, 0], nelx) & np.isclose(nc[:, 1], 0))[0]
    fixed[2 * br + 1] = True
    F = np.zeros((g.ndof, 1))
    tl = np.where(np.isclose(nc[:, 0], 0) & np.isclose(nc[:, 1], nely))[0][0]
    F[2 * tl + 1, 0] = -1.0
    return SimpProblem(grid=g, loads=F, fixed=fixed, volfrac=volfrac, rmin_vox=rmin)


def cantilever3d_problem(nx=32, ny=8, nz=16, volfrac=0.15, rmin=1.5) -> SimpProblem:
    """3D cantilever: x = 0 face clamped, line load (-z) along the free-end bottom edge's mid line."""
    g = Grid((nx, ny, nz), 1.0)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    cl = np.where(np.isclose(nc[:, 0], 0))[0]
    for d in range(3):
        fixed[3 * cl + d] = True
    F = np.zeros((g.ndof, 1))
    tip = np.where(np.isclose(nc[:, 0], nx) & np.isclose(nc[:, 2], nz / 2))[0]
    F[3 * tip + 2, 0] = -1.0 / len(tip)
    return SimpProblem(grid=g, loads=F, fixed=fixed, volfrac=volfrac, rmin_vox=rmin)


def min_feature_mm(solid: np.ndarray, h: float) -> float:
    """Smallest member thickness of a binary voxel/pixel body: 2 x the distance-transform value on its
    medial axis (skeleton), 5th percentile (robust to single stair-step voxels)."""
    from scipy import ndimage
    from skimage.morphology import skeletonize
    if solid.sum() == 0:
        return 0.0
    dt = ndimage.distance_transform_edt(np.pad(solid, 1)) * h
    sk = skeletonize(np.pad(solid, 1))
    vals = 2 * dt[sk > 0]
    return float(np.percentile(vals, 5)) if vals.size else float(h)
