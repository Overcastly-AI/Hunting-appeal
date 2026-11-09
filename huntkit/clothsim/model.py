"""Energy terms and the static solver.

Units: mm, N, MPa (N/mm^2), kg. Energy in N mm. Positions ``x`` are (n, 3).

The solver minimises the total potential energy (membrane + bending + cables + contact + pins
- work of gravity, dead loads and pressure) with a Levenberg-Marquardt damped Newton method and a
backtracking line search. This is the infinite-time-step limit of Baraff-Witkin implicit cloth
(docs/research/cloth_sim_methods.md). Each term returns (energy, gradient, Hessian-or-None); the
Hessians are positive semi-definite approximations (Gauss-Newton + positive geometric stiffness),
the gradients are exact (checked against finite differences in tests/test_clothsim.py).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial import cKDTree

from .mesh import ClothMesh

GRAV = 9.81  # m/s^2 -> with kg gives N


def _scatter(n: int, idx: np.ndarray, vals: np.ndarray) -> np.ndarray:
    """Sum (k, 3) values into (n, 3) by node index."""
    out = np.zeros((n, 3))
    for d in range(3):
        out[:, d] = np.bincount(idx, vals[:, d], minlength=n)
    return out


def _block_sparse(n: int, nodes: np.ndarray, H: np.ndarray) -> sp.csr_matrix:
    """(T, m) node ids and (T, 3m, 3m) element Hessians -> (3n, 3n) sparse."""
    T, m = nodes.shape
    dof = (3 * nodes[:, :, None] + np.arange(3)[None, None, :]).reshape(T, 3 * m)
    r = np.repeat(dof[:, :, None], 3 * m, 2)
    c = np.repeat(dof[:, None, :], 3 * m, 1)
    return sp.coo_matrix((H.ravel(), (r.ravel(), c.ravel())), shape=(3 * n, 3 * n)).tocsr()


# ============================================================================ terms
class Membrane:
    """Orthotropic CST membrane on Green strain in the warp frame.

    W = A0 [ k1' E11^2 / 2 + k2' E22^2 / 2 + 2 g E12^2 ],  k' = k (E > 0) or c k (E < 0).
    E12 is the tensor shear strain (engineering gamma = 2 E12), so g is a shear stiffness N/mm/rad."""
    name = "membrane"

    def __init__(self, mesh: ClothMesh):
        self.m = mesh

    def strains(self, x):
        m = self.m
        X = x[m.tris]                                   # T,3,3
        F = np.einsum("tid,tia->tda", X, m.beta)        # T,3,2
        C = np.einsum("tda,tdb->tab", F, F)
        E = 0.5 * (C - np.eye(2))
        return F, C, E

    def stress(self, x):
        m = self.m
        F, C, E = self.strains(x)
        e11, e22, e12 = E[:, 0, 0], E[:, 1, 1], E[:, 0, 1]
        k1e = np.where(e11 > 0, m.k1, m.c * m.k1)
        k2e = np.where(e22 > 0, m.k2, m.c * m.k2)
        S = np.zeros((len(e11), 2, 2))                  # 2nd PK membrane force per unit rest width
        S[:, 0, 0] = k1e * e11
        S[:, 1, 1] = k2e * e22
        S[:, 0, 1] = S[:, 1, 0] = 2 * m.g * e12
        return F, E, S, k1e, k2e

    def __call__(self, x, hess=True):
        m = self.m
        F, E, S, k1e, k2e = self.stress(x)
        e11, e22, e12 = E[:, 0, 0], E[:, 1, 1], E[:, 0, 1]
        W = m.A0 * (0.5 * k1e * e11 ** 2 + 0.5 * k2e * e22 ** 2 + 2 * m.g * e12 ** 2)
        SA = S * m.A0[:, None, None]
        FS = np.einsum("tda,tab->tdb", F, SA)
        Gt = np.einsum("tia,tda->tid", m.beta, FS)      # T,3(vertex),3(dim)
        grad = _scatter(m.n, m.tris.ravel(), Gt.reshape(-1, 3))
        H = None
        if hess:
            b = m.beta
            J11 = (b[:, :, 0, None] * F[:, None, :, 0]).reshape(-1, 9)
            J22 = (b[:, :, 1, None] * F[:, None, :, 1]).reshape(-1, 9)
            J12 = (0.5 * (b[:, :, 0, None] * F[:, None, :, 1] + b[:, :, 1, None] * F[:, None, :, 0])).reshape(-1, 9)
            He = (m.A0 * k1e)[:, None, None] * J11[:, :, None] * J11[:, None, :]
            He += (m.A0 * k2e)[:, None, None] * J22[:, :, None] * J22[:, None, :]
            He += (4 * m.A0 * m.g)[:, None, None] * J12[:, :, None] * J12[:, None, :]
            # positive part of the geometric stiffness
            w, V = np.linalg.eigh(SA)
            Sp = np.einsum("tab,tb,tcb->tac", V, np.maximum(w, 0), V)
            Kg = np.einsum("tia,tab,tjb->tij", b, Sp, b)            # T,3,3
            Hg = np.einsum("tij,de->tidje", Kg, np.eye(3)).reshape(-1, 9, 9)
            H = _block_sparse(m.n, m.tris, He + Hg)
        return float(W.sum()), grad, H

    def tri_forces(self, x):
        """Per-triangle internal nodal forces (T,3,3): the force each triangle exerts ON its nodes."""
        m = self.m
        F, E, S, _, _ = self.stress(x)
        FS = np.einsum("tda,tab->tdb", F, S * m.A0[:, None, None])
        return -np.einsum("tia,tda->tid", m.beta, FS)


class Bending:
    """Quadratic isometric bending (Bergou/Wardetzky): E = 1/2 sum_d x_d^T Q x_d."""
    name = "bending"

    def __init__(self, mesh: ClothMesh):
        self.Q = mesh.Q
        self.H = sp.kron(mesh.Q, sp.eye(3), format="csr")
        n = mesh.n
        # kron gives node-major dof ordering only if Q is node-indexed: (Q kron I3)[3i+d, 3j+e] = Q_ij delta_de
        self.n = n

    def __call__(self, x, hess=True):
        g = self.Q @ x
        return float(0.5 * np.sum(x * g)), g, (self.H if hess else None)


class Gravity:
    name = "gravity"

    def __init__(self, mass: np.ndarray, g: float = GRAV, scale: float = 1.0):
        self.mass, self.gacc, self.scale = mass, g, scale

    def __call__(self, x, hess=True):
        w = self.mass * self.gacc * self.scale
        grad = np.zeros_like(x)
        grad[:, 2] = w
        return float(np.sum(w * x[:, 2])), grad, None


class DeadLoad:
    """Fixed nodal forces f (k,3) on nodes idx (k,): E = - sum f . x."""
    name = "dead_load"

    def __init__(self, idx, f, scale: float = 1.0, label: str = "dead"):
        self.idx, self.f, self.scale, self.name = np.asarray(idx), np.asarray(f, float), scale, label

    def __call__(self, x, hess=True):
        n = len(x)
        grad = -_scatter(n, self.idx, self.f * self.scale)
        return float(-np.sum(self.f * self.scale * x[self.idx])), grad, None


class Pressure:
    """Interior pressure p(z) = p0 + rho_g (z_ref - z) on a closed, outward-oriented surface.

    Potential  Pi = - int_V p dV = - sum_t N_z(t) <F(z)>_t,  F(z) = p0 z + rho_g (z_ref z - z^2 / 2),
    N_z = z-component of the triangle's vector area. Exact for linear triangles (quadratic F).
    p0 in MPa, rho_g in N/mm^3 (= rho[kg/L] * 9.81e-6)."""
    name = "pressure"

    def __init__(self, tris: np.ndarray, p0: float = 0.0, rho_g: float = 0.0, z_ref: float = 0.0,
                 scale: float = 1.0):
        self.tris, self.p0, self.rho_g, self.z_ref, self.scale = tris, p0, rho_g, z_ref, scale

    def _parts(self, x):
        a, b, c = (x[self.tris[:, j]] for j in range(3))
        Nz = 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
        z = np.stack([a[:, 2], b[:, 2], c[:, 2]], 1)
        m1 = z.mean(1)
        m2 = (np.sum(z ** 2, 1) + z[:, 0] * z[:, 1] + z[:, 1] * z[:, 2] + z[:, 2] * z[:, 0]) / 6
        return a, b, c, Nz, z, m1, m2

    def __call__(self, x, hess=True):
        s = self.scale
        p0, rg, zr = self.p0 * s, self.rho_g * s, self.z_ref
        a, b, c, Nz, z, m1, m2 = self._parts(x)
        phi = p0 * m1 + rg * (zr * m1 - 0.5 * m2)
        E = -np.sum(Nz * phi)
        P = [a, b, c]
        G = np.zeros((len(Nz), 3, 3))
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            G[:, i, 0] = -0.5 * (P[j][:, 1] - P[k][:, 1]) * phi
            G[:, i, 1] = -0.5 * (P[k][:, 0] - P[j][:, 0]) * phi
            G[:, i, 2] = -Nz * (p0 / 3 + rg * (zr / 3 - (2 * z[:, i] + z[:, j] + z[:, k]) / 12))
        grad = _scatter(len(x), self.tris.ravel(), G.reshape(-1, 3))
        H = None
        if hess:
            # load stiffness: -p_t d2V_t (V_t = det[a,b,c]/6 about the centroid; the sum over a closed
            # surface equals the Hessian of the exact potential for uniform p, approximate for hydrostatic)
            o = x.mean(0)
            A, Bv, Cv = a - o, b - o, c - o
            pt = p0 + rg * (zr - z.mean(1))

            def skew(v):
                Z = np.zeros((len(v), 3, 3))
                Z[:, 0, 1], Z[:, 0, 2], Z[:, 1, 2] = -v[:, 2], v[:, 1], -v[:, 0]
                Z[:, 1, 0], Z[:, 2, 0], Z[:, 2, 1] = v[:, 2], -v[:, 1], v[:, 0]
                return Z
            He = np.zeros((len(Nz), 9, 9))
            for (i, j, w) in ((0, 1, Cv), (1, 2, A), (2, 0, Bv)):
                M = -(pt / 6)[:, None, None] * (-skew(w))        # d2(-pV)/dx_i dx_j
                He[:, 3 * i:3 * i + 3, 3 * j:3 * j + 3] = M
                He[:, 3 * j:3 * j + 3, 3 * i:3 * i + 3] = np.transpose(M, (0, 2, 1))
            H = _block_sparse(len(x), self.tris, He)
        return float(E), grad, H

    def volume(self, x) -> float:
        _, _, _, Nz, _, m1, _ = self._parts(x)
        return float(np.sum(Nz * m1))


class Pins:
    """Zero-length springs node -> target: E = k/2 |x_i - p|^2."""
    name = "pins"

    def __init__(self, idx, targets, k=500.0):
        # k: one stiffness for all pins, or one per pin (N/mm)
        self.idx, self.p = np.asarray(idx), np.asarray(targets, float)
        self.k = k if np.ndim(k) == 0 else np.asarray(k, float)

    def _kc(self):
        return self.k if np.ndim(self.k) == 0 else self.k[:, None]

    def __call__(self, x, hess=True):
        d = x[self.idx] - self.p
        kc = self._kc()
        grad = _scatter(len(x), self.idx, kc * d)
        H = None
        if hess:
            n = len(x)
            dof = (3 * self.idx[:, None] + np.arange(3)).ravel()
            kd = np.broadcast_to(kc, d.shape).ravel()
            H = sp.coo_matrix((kd, (dof, dof)), shape=(3 * n, 3 * n)).tocsr()
        return float(0.5 * np.sum(kc * d * d)), grad, H

    def forces(self, x):
        return -self._kc() * (x[self.idx] - self.p)


@dataclass
class Cable:
    """Tension-only cable through a chain of points: fixed 3D anchors or mesh nodes.

    The energy depends only on the total length L (frictionless eyelets at the nodes), so the
    tension T = k (L - L0) is the same along the cable: a strap sliding through channels/keepers.
    k = EA / L0."""
    name: str
    nodes: np.ndarray            # (m,) node id or -1
    fixed: np.ndarray            # (m,3) used where nodes == -1
    EA: float
    L0: float
    kind: str = "strap"
    material_id: str = ""
    meta: dict = field(default_factory=dict)
    T_const: float | None = None   # cinched strap: constant tension (E = T L), else elastic tension-only

    def points(self, x):
        P = self.fixed.copy()
        msk = self.nodes >= 0
        P[msk] = x[self.nodes[msk]]
        return P

    def length(self, x) -> float:
        return float(np.linalg.norm(np.diff(self.points(x), axis=0), axis=1).sum())

    def tension(self, x) -> float:
        if self.T_const is not None:
            return float(self.T_const)
        L = self.length(x)
        return max(0.0, self.EA / self.L0 * (L - self.L0))


class Cables:
    name = "cables"

    def __init__(self, cables: list[Cable]):
        self.cables = cables

    def __call__(self, x, hess=True):
        n = len(x)
        E = 0.0
        grad = np.zeros_like(x)
        Hs = []
        for cb in self.cables:
            P = cb.points(x)
            d = np.diff(P, axis=0)
            ell = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
            L = ell.sum()
            if cb.T_const is not None:
                k, T = 0.0, float(cb.T_const)
                E += T * L
            else:
                if L <= cb.L0:
                    continue
                k = cb.EA / cb.L0
                T = k * (L - cb.L0)
                E += 0.5 * k * (L - cb.L0) ** 2
            u = d / ell[:, None]
            dL = np.zeros_like(P)
            dL[1:] += u
            dL[:-1] -= u
            msk = cb.nodes >= 0
            np.add.at(grad, cb.nodes[msk], T * dL[msk])
            if hess:
                mpt = len(P)
                Hc = k * np.einsum("i,j->ij", dL.ravel(), dL.ravel())
                for s in range(len(d)):
                    B = T * (np.eye(3) - np.outer(u[s], u[s])) / ell[s]
                    for (p_, q_, sg) in ((s, s, 1), (s + 1, s + 1, 1), (s, s + 1, -1), (s + 1, s, -1)):
                        Hc[3 * p_:3 * p_ + 3, 3 * q_:3 * q_ + 3] += sg * B
                idx = np.where(msk)[0]
                dofl = (3 * idx[:, None] + np.arange(3)).ravel()
                dofg = (3 * cb.nodes[idx][:, None] + np.arange(3)).ravel()
                sub = Hc[np.ix_(dofl, dofl)]
                r = np.repeat(dofg, len(dofg))
                c = np.tile(dofg, len(dofg))
                Hs.append(sp.coo_matrix((sub.ravel(), (r, c)), shape=(3 * n, 3 * n)))
        H = None
        if hess:
            H = sum(Hs[1:], Hs[0]).tocsr() if Hs else None
        return float(E), grad, H


class Contact:
    """Penalty contact of mesh nodes against a rigid point cloud with outward normals (frame, spreader).

    gap = (x - p) . n - clearance, with p the nearest cloud point within ``cutoff``;
    E = kc/2 gap^2 for gap < 0."""
    name = "contact"

    def __init__(self, points, normals, kc: float = 50.0, clearance: float = 1.0, cutoff: float = 15.0,
                 nodes=None, label="contact"):
        self.P = np.asarray(points, float)
        nn = np.asarray(normals, float)
        self.N = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
        self.tree = cKDTree(self.P)
        self.kc, self.clr, self.cut = kc, clearance, cutoff
        self.nodes = nodes
        self.name = label

    def _active(self, x):
        idx = np.arange(len(x)) if self.nodes is None else np.asarray(self.nodes)
        d, j = self.tree.query(x[idx], distance_upper_bound=self.cut)
        ok = np.isfinite(d)
        idx, j = idx[ok], j[ok]
        n = self.N[j]
        gap = np.einsum("ij,ij->i", x[idx] - self.P[j], n) - self.clr
        a = gap < 0
        return idx[a], n[a], gap[a]

    def __call__(self, x, hess=True):
        idx, n, gap = self._active(x)
        E = 0.5 * self.kc * np.sum(gap ** 2)
        grad = _scatter(len(x), idx, self.kc * gap[:, None] * n)
        H = None
        if hess and len(idx):
            Hn = self.kc * np.einsum("ki,kj->kij", n, n)
            H = _block_sparse(len(x), idx[:, None], Hn)
        return float(E), grad, H

    def forces(self, x):
        idx, n, gap = self._active(x)
        return idx, -self.kc * gap[:, None] * n


class Anchor:
    """Weak springs to a reference shape (removes rigid-body modes in free-floating tests)."""
    name = "anchor"

    def __init__(self, X0, k=1e-6):
        self.X0, self.k = np.asarray(X0, float), k

    def __call__(self, x, hess=True):
        d = x - self.X0
        H = sp.identity(3 * len(x), format="csr") * self.k if hess else None
        return float(0.5 * self.k * np.sum(d * d)), self.k * d, H


# ============================================================================ solver
def _linsolve(A, rhs):
    """Sparse symmetric solve: SuperLU with a symmetric minimum-degree ordering and no pivoting
    (fast for these SPD-ish systems), falling back to the default pivoting solve."""
    A = A.tocsc()
    try:
        lu = spla.splu(A, permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0,
                       options=dict(SymmetricMode=True))
        sol = lu.solve(rhs)
        if np.all(np.isfinite(sol)):
            return sol
    except Exception:  # noqa: BLE001
        pass
    try:
        return spla.spsolve(A, rhs)
    except Exception:  # noqa: BLE001
        return np.full(len(rhs), np.nan)


@dataclass
class SolveInfo:
    converged: bool
    iterations: int
    residual_n: float
    energy: float
    seconds: float
    history: list = field(default_factory=list)
    reason: str = ""


class Sim:
    def __init__(self, mesh: ClothMesh, terms: list):
        self.mesh, self.terms = mesh, terms

    def term(self, name):
        for t in self.terms:
            if getattr(t, "name", "") == name:
                return t
        return None

    def evaluate(self, x, hess=True):
        n = len(x)
        E, g = 0.0, np.zeros_like(x)
        H = sp.csr_matrix((3 * n, 3 * n)) if hess else None
        for t in self.terms:
            e, gg, hh = t(x, hess)
            E += e
            g += gg
            if hess and hh is not None:
                H = H + hh
        return E, g, H

    def energy(self, x):
        return sum(t(x, False)[0] for t in self.terms)

    def solve(self, x0=None, tol=1e-3, max_iter=300, time_cap=600.0, verbose=False, lam0=1e-4,
              free=None) -> tuple[np.ndarray, SolveInfo]:
        """Damped Newton. ``tol``: max nodal residual force (N). ``free``: optional bool (n,) mask of
        moving nodes (others held at x0)."""
        t0 = time.time()
        x = (self.mesh.X0 if x0 is None else x0).copy()
        n = len(x)
        fdof = None
        if free is not None:
            fdof = np.repeat(np.asarray(free, bool), 3)
        lam = lam0
        hist = []
        E, g, H = self.evaluate(x)
        reason = "max_iter"
        it = 0
        for it in range(1, max_iter + 1):
            gf = g.copy()
            if free is not None:
                gf[~np.asarray(free, bool)] = 0
            res = float(np.max(np.linalg.norm(gf, axis=1)))
            hist.append((it, E, res, lam))
            if verbose:
                print(f"  it {it:3d}  E {E:.6e}  res {res:.3e} N  lam {lam:.1e}  {time.time() - t0:.1f}s")
            if res < tol:
                reason = "converged"
                break
            if time.time() - t0 > time_cap:
                reason = "time_cap"
                break
            D = H.diagonal()
            dscale = np.maximum(D, 1e-9 * max(D.max(), 1e-12))
            accepted = False
            for _ in range(12):
                A = H + sp.diags(lam * dscale + 1e-12)
                rhs = -gf.ravel()
                if fdof is not None:
                    A = A[fdof][:, fdof]
                    rhs = rhs[fdof]
                sol = _linsolve(A, rhs)
                if not np.all(np.isfinite(sol)):
                    lam *= 10
                    continue
                dx = np.zeros(3 * n)
                if fdof is not None:
                    dx[fdof] = sol
                else:
                    dx = sol
                dx = dx.reshape(n, 3)
                # cap the step (robust against huge first steps in slack cloth)
                mx = np.max(np.linalg.norm(dx, axis=1))
                cap = 50.0
                if mx > cap:
                    dx *= cap / mx
                slope = float(np.sum(gf * dx))
                a = 1.0
                for _ls in range(12):
                    Et = self.energy(x + a * dx)
                    if Et <= E + 1e-4 * a * min(slope, 0.0):
                        accepted = True
                        break
                    if Et <= E + 1e-11 * max(1.0, abs(E)):
                        # energy flat to round-off: accept only if the force residual drops
                        gt = self.evaluate(x + a * dx, hess=False)[1]
                        if free is not None:
                            gt[~np.asarray(free, bool)] = 0
                        if np.max(np.linalg.norm(gt, axis=1)) < res:
                            accepted = True
                            break
                    a *= 0.5
                if accepted:
                    x = x + a * dx
                    lam = max(lam * (0.3 if a == 1.0 else 1.0), 1e-9)
                    break
                lam *= 10
            if not accepted or lam > 1e10:
                reason = "line_search" if not accepted else "stalled"
                break
            E_old = E
            E, g, H = self.evaluate(x)
            if abs(E_old - E) < 1e-14 * max(1.0, abs(E)) and res < 50 * tol:
                reason = "stalled"
                break
        info = SolveInfo(reason == "converged", it, hist[-1][2] if hist else np.nan, E, time.time() - t0, hist, reason)
        return x, info


# ============================================================================ smooth obstacle field
class GapField:
    """One-sided gap to a rigid surface, sampled on a regular grid and trilinearly interpolated
    (continuous energy, exact gradient of the interpolant: Newton-friendly, unlike a raw
    nearest-sample point cloud). Built from surface samples with outward normals by a moving
    least-squares foot point: g(q) = (q - p_bar) . n_bar over the k nearest samples."""

    def __init__(self, origin, spacing, values):
        self.o = np.asarray(origin, float)
        self.h = float(spacing)
        self.v = np.asarray(values, float)

    @classmethod
    def from_samples(cls, P, N, spacing=2.0, margin=25.0, k=8, sigma=None, far=50.0, edge=None):
        P = np.asarray(P, float)
        N = np.asarray(N, float)
        N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
        lo, hi = P.min(0) - margin, P.max(0) + margin
        shape = np.ceil((hi - lo) / spacing).astype(int) + 1
        axes = [lo[d] + spacing * np.arange(shape[d]) for d in range(3)]
        Q = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
        tree = cKDTree(P)
        sig = sigma or 1.5 * spacing
        d_nn = cKDTree(P).query(P[:: max(1, len(P) // 2000)], k=2)[0][:, 1]
        edge = edge or 1.5 * float(np.median(d_nn)) + spacing
        vals = np.full(len(Q), far)
        step = 400000
        for s in range(0, len(Q), step):
            q = Q[s:s + step]
            d, j = tree.query(q, k=k, distance_upper_bound=margin)
            ok = np.isfinite(d[:, 0])
            if not ok.any():
                continue
            d, j, qq = d[ok], j[ok], q[ok]
            fin = np.isfinite(d)
            jj = np.where(fin, j, 0)
            w = np.where(fin, np.exp(-((d - d[:, :1]) / sig) ** 2), 0.0)
            w /= w.sum(1, keepdims=True)
            pb = np.einsum("ik,ikd->id", w, P[jj])
            nb = np.einsum("ik,ikd->id", w, N[jj])
            nb /= np.maximum(np.linalg.norm(nb, axis=1, keepdims=True), 1e-12)
            g = np.einsum("id,id->i", qq - pb, nb)
            # beyond the edge of the sampled surface (foot point off the sheet): fade to "far" so a
            # plate does not act as an infinite plane; smooth over two sample spacings
            tan = np.linalg.norm(qq - pb - g[:, None] * nb, axis=1)
            wt = np.clip(1.0 - (tan - edge) / (2 * edge), 0.0, 1.0)
            g = wt * g + (1 - wt) * far
            sub = vals[s:s + step]
            sub[np.where(ok)[0]] = g
            vals[s:s + step] = sub
        return cls(lo, spacing, vals.reshape(shape))

    def smoothed(self, sigma_mm: float) -> "GapField":
        """Gaussian-rounded copy (2026-11-09, CORRIE convergence). The trilinear gap has a gradient kink along
        plate edges (spreader rim, frame members): a node sitting on that crease has no smooth equilibrium and the
        damped Newton step chatters between the two faces (residual 1.5-5 N, LM lambda -> 1e4). Blurring the sampled
        gap by ``sigma_mm`` rounds convex edges to a radius of order sigma; a flat face is unchanged (a linear field
        is invariant under a symmetric blur). ASSUMPTION: a 6 mm edge rounding is inside the real parts' edge radii
        plus the foam / mesh cover."""
        from scipy.ndimage import gaussian_filter
        return GapField(self.o, self.h, gaussian_filter(self.v, float(sigma_mm) / self.h, mode="nearest"))

    def __call__(self, x):
        """gap (n,) and gradient (n,3); points outside the grid get a large positive gap."""
        u = (np.asarray(x, float) - self.o) / self.h
        sh = np.array(self.v.shape)
        inside = np.all((u >= 0) & (u <= sh - 1.000001), axis=1)
        g = np.full(len(u), 1e3)
        dg = np.zeros((len(u), 3))
        if not inside.any():
            return g, dg
        ui = u[inside]
        i0 = np.floor(ui).astype(int)
        f = ui - i0
        V = self.v
        c = np.zeros((len(ui), 2, 2, 2))
        for a in (0, 1):
            for b in (0, 1):
                for cc in (0, 1):
                    c[:, a, b, cc] = V[i0[:, 0] + a, i0[:, 1] + b, i0[:, 2] + cc]
        fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
        c00 = c[:, 0, 0, 0] * (1 - fx) + c[:, 1, 0, 0] * fx
        c01 = c[:, 0, 0, 1] * (1 - fx) + c[:, 1, 0, 1] * fx
        c10 = c[:, 0, 1, 0] * (1 - fx) + c[:, 1, 1, 0] * fx
        c11 = c[:, 0, 1, 1] * (1 - fx) + c[:, 1, 1, 1] * fx
        c0 = c00 * (1 - fy) + c10 * fy
        c1 = c01 * (1 - fy) + c11 * fy
        gi = c0 * (1 - fz) + c1 * fz
        dz = c1 - c0
        dy = (c10 - c00) * (1 - fz) + (c11 - c01) * fz
        dx_ = ((c[:, 1, 0, 0] - c[:, 0, 0, 0]) * (1 - fy) * (1 - fz) + (c[:, 1, 1, 0] - c[:, 0, 1, 0]) * fy * (1 - fz)
               + (c[:, 1, 0, 1] - c[:, 0, 0, 1]) * (1 - fy) * fz + (c[:, 1, 1, 1] - c[:, 0, 1, 1]) * fy * fz)
        g[inside] = gi
        dg[inside] = np.column_stack([dx_, dy, dz]) / self.h
        return g, dg


class FieldContact:
    """Penalty contact against a :class:`GapField`: E = kc/2 min(g - clearance, 0)^2."""

    def __init__(self, field: GapField, kc=50.0, clearance=1.0, nodes=None, label="contact"):
        self.f, self.kc, self.clr, self.nodes, self.name = field, kc, clearance, nodes, label

    def _active(self, x):
        idx = np.arange(len(x)) if self.nodes is None else np.asarray(self.nodes)
        g, dg = self.f(x[idx])
        gap = g - self.clr
        a = gap < 0
        return idx[a], dg[a], gap[a]

    def __call__(self, x, hess=True):
        idx, dg, gap = self._active(x)
        E = 0.5 * self.kc * np.sum(gap ** 2)
        grad = _scatter(len(x), idx, self.kc * gap[:, None] * dg)
        H = None
        if hess and len(idx):
            H = _block_sparse(len(x), idx[:, None], self.kc * np.einsum("ki,kj->kij", dg, dg))
        return float(E), grad, H

    def forces(self, x):
        idx, dg, gap = self._active(x)
        return idx, -self.kc * gap[:, None] * dg

    def gap(self, x, idx):
        return self.f(x[idx])[0]


class PressureProfile(Pressure):
    """Interior pressure with any depth profile p(z) (antiderivative F(z) given): exact potential
    -sum N_z <F>_t with 3-point edge-midpoint quadrature (exact for quadratic F)."""
    name = "pressure"

    def __init__(self, tris, p_of_z, F_of_z, scale=1.0):
        super().__init__(tris, scale=scale)
        self.pf, self.Ff = p_of_z, F_of_z

    def __call__(self, x, hess=True):
        s = self.scale
        a, b, c, Nz, z, m1, m2 = self._parts(x)
        mids = [(0, 1), (1, 2), (2, 0)]
        zm = np.stack([0.5 * (z[:, i] + z[:, j]) for i, j in mids], 1)
        Fm = self.Ff(zm) * s
        pm = self.pf(zm) * s
        phi = Fm.mean(1)
        E = -np.sum(Nz * phi)
        P = [a, b, c]
        G = np.zeros((len(Nz), 3, 3))
        for i in range(3):
            j, k = (i + 1) % 3, (i + 2) % 3
            G[:, i, 0] = -0.5 * (P[j][:, 1] - P[k][:, 1]) * phi
            G[:, i, 1] = -0.5 * (P[k][:, 0] - P[j][:, 0]) * phi
            # vertex i sits in midpoints (i,j) and (k,i)
            G[:, i, 2] = -Nz * (pm[:, i] + pm[:, k]) / 6
        grad = _scatter(len(x), self.tris.ravel(), G.reshape(-1, 3))
        H = None
        if hess:
            self.p0, self.rho_g, self.z_ref = float(np.mean(pm)), 0.0, 0.0
            sc, self.scale = self.scale, 1.0
            H = Pressure.__call__(self, x, True)[2]
            self.scale = sc
        return float(E), grad, H

    def pressure_at(self, z):
        return self.pf(np.asarray(z, float)) * self.scale


class GasFill(Pressure):
    """Packed contents as a polytropic fill: p = p_pack (V_c / V)^n (n > 1), or a constant
    pressure p_pack when V_c is None. Potential: p_pack V_c^n V^(1-n) / (n - 1). The contents
    resist being squeezed (straps, meat) instead of vanishing like a constant-pressure gas."""
    name = "gas"

    def __init__(self, tris, p_pack, V_c=None, n=3.0, scale=1.0):
        super().__init__(tris, p0=1.0, scale=scale)
        self.pp, self.Vc, self.n = p_pack, V_c, n

    def p_eff(self, V):
        s = self.scale
        if self.Vc is None:
            return self.pp * s
        return self.pp * s * (self.Vc / V) ** self.n

    def __call__(self, x, hess=True):
        V = self.volume(x)
        pe = self.p_eff(V)
        self.p0, self.rho_g, sc = 1.0, 0.0, self.scale
        self.scale = 1.0
        _, gV, HV = Pressure.__call__(self, x, hess)      # derivatives of -V
        self.scale = sc
        if self.Vc is None:
            E = -pe * V
        else:
            E = self.pp * sc * self.Vc ** self.n * V ** (1 - self.n) / (self.n - 1)
        return float(E), pe * gV, (pe * HV if HV is not None else None)
