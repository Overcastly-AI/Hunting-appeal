"""Regular-grid Kirchhoff plate (ACM rectangle) with unilateral contact and beam supports.

Built for flat sheets that rest on a frame: a spreader on stays, a framesheet on rails.

Element: Adini-Clough-Melosh 12-dof rectangle (w, dw/dx, dw/dy at each corner). It is
non-conforming but passes the patch test and converges in deflection and moment
(Zienkiewicz & Taylor, The Finite Element Method Vol. 2, ch. 4). The 3x3 bending stiffness
D may differ per element, so a laminate (from ``composite.Laminate.D``), a bead strip or a
perforated region is just another D. Inactive elements are holes.

Supports:
- ``fix_w`` : bilateral w = 0 at nodes (clips, bolted points).
- ``Spring``: plate node to ground or to a beam node, stiffness k, gap g. Unilateral springs
  act only when the plate has closed the gap (w_plate - w_other >= g). Positive w is toward
  the support side ("into" the frame).
- ``Beam``  : an Euler-Bernoulli beam (w, theta) along a chain of points, with clamped or free
  ends. Frame members that the sheet can land on (branches, bars) are beams.

Contact is solved by an active-set loop with a penalty spring. Linear sparse solve per pass.

Verified in ``tests/test_spreader.py`` against: the Navier series for a simply supported
plate under a centre patch, the Timoshenko clamped-plate coefficient, an orthotropic Navier
series, and the Hetenyi/Timoshenko infinite plate on a Winkler foundation.

Units: mm, N, MPa. Moments are per unit width (N mm / mm).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp

try:  # pragma: no cover - optional speed-up
    from pypardiso import spsolve as _spsolve
except Exception:  # pragma: no cover
    from scipy.sparse.linalg import spsolve as _spsolve


def iso_D(E: float, t: float, nu: float) -> np.ndarray:
    d = E * t ** 3 / (12.0 * (1.0 - nu ** 2))
    return d * np.array([[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu) / 2.0]])


# ----------------------------------------------------------------------------- element
_POW = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (3, 0), (2, 1), (1, 2), (0, 3), (3, 1), (1, 3)]


def _P(x, y):
    return np.array([x ** a * y ** b for a, b in _POW])


def _Px(x, y):
    return np.array([a * x ** (a - 1) * y ** b if a > 0 else 0.0 for a, b in _POW])


def _Py(x, y):
    return np.array([b * x ** a * y ** (b - 1) if b > 0 else 0.0 for a, b in _POW])


def _Pxx(x, y):
    return np.array([a * (a - 1) * x ** (a - 2) * y ** b if a > 1 else 0.0 for a, b in _POW])


def _Pyy(x, y):
    return np.array([b * (b - 1) * x ** a * y ** (b - 2) if b > 1 else 0.0 for a, b in _POW])


def _Pxy(x, y):
    return np.array([a * b * x ** (a - 1) * y ** (b - 1) if (a > 0 and b > 0) else 0.0 for a, b in _POW])


@dataclass
class ACMElement:
    hx: float
    hy: float
    Ainv: np.ndarray = field(init=False)
    Kb: np.ndarray = field(init=False)       # (6, 12, 12) basis stiffness for D11,D22,D12,D33,D13,D23
    fN: np.ndarray = field(init=False)       # (12,) integral of N for a unit uniform pressure
    gauss: list = field(init=False)

    def __post_init__(self):
        hx, hy = self.hx, self.hy
        nodes = [(0.0, 0.0), (hx, 0.0), (hx, hy), (0.0, hy)]
        A = []
        for x, y in nodes:
            A += [_P(x, y), _Px(x, y), _Py(x, y)]
        self.Ainv = np.linalg.inv(np.array(A))
        g, wg = np.polynomial.legendre.leggauss(3)
        Kb = np.zeros((6, 12, 12))
        fN = np.zeros(12)
        for gi, wi in zip(g, wg):
            for gj, wj in zip(g, wg):
                x, y = (gi + 1) * hx / 2, (gj + 1) * hy / 2
                wt = wi * wj * hx * hy / 4
                B = self.B(x, y)
                b1, b2, b3 = B
                Kb[0] += wt * np.outer(b1, b1)
                Kb[1] += wt * np.outer(b2, b2)
                Kb[2] += wt * (np.outer(b1, b2) + np.outer(b2, b1))
                Kb[3] += wt * np.outer(b3, b3)
                Kb[4] += wt * (np.outer(b1, b3) + np.outer(b3, b1))
                Kb[5] += wt * (np.outer(b2, b3) + np.outer(b3, b2))
                fN += wt * (_P(x, y) @ self.Ainv)
        self.Kb, self.fN = Kb, fN
        s = 1.0 / np.sqrt(3.0)
        self.gauss = [((a + 1) * hx / 2, (b + 1) * hy / 2) for a in (-s, s) for b in (-s, s)]

    def B(self, x, y) -> np.ndarray:
        """Curvature operator: kappa = [w_xx, w_yy, 2 w_xy] = B @ u_e."""
        return np.array([_Pxx(x, y), _Pyy(x, y), 2.0 * _Pxy(x, y)]) @ self.Ainv

    def N(self, x, y) -> np.ndarray:
        return _P(x, y) @ self.Ainv


def _Dvec(D):
    D = np.asarray(D)
    return np.stack([D[..., 0, 0], D[..., 1, 1], D[..., 0, 1], D[..., 2, 2], D[..., 0, 2], D[..., 1, 2]], -1)


# ----------------------------------------------------------------------------- model
@dataclass
class Spring:
    node: int                     # plate node index
    k: float
    gap: float = 0.0
    other: int | None = None      # global dof of the other end (beam w); None = ground
    unilateral: bool = True
    tag: str = ""
    sense: float = 1.0            # +1: acts in compression (closing the gap); -1: tension only (a clip)


@dataclass
class Beam:
    xy: np.ndarray                # (n, 2) points in plate coordinates
    EI: float
    clamp_start: bool = True
    clamp_end: bool = True
    tag: str = ""
    dof0: int = -1                # set by the model: first global dof (w0, th0, w1, th1, ...)
    pin_start: bool = False       # w = 0 only (a socket); ignored when clamp_start is set
    pin_end: bool = False


class GridPlate:
    """Plate on a regular grid. ``x0, y0`` lower-left corner, ``nx, ny`` elements, ``h`` size.

    ``D`` is (3,3) or (nx, ny, 3, 3). ``active`` (nx, ny) bool masks holes.
    """

    def __init__(self, x0: float, y0: float, nx: int, ny: int, h: float, D, active=None):
        self.x0, self.y0, self.nx, self.ny, self.h = float(x0), float(y0), int(nx), int(ny), float(h)
        self.el = ACMElement(h, h)
        D = np.asarray(D, float)
        if D.ndim == 2:
            D = np.broadcast_to(D, (nx, ny, 3, 3)).copy()
        self.D = D
        self.active = np.ones((nx, ny), bool) if active is None else np.asarray(active, bool)
        self.nn = (nx + 1) * (ny + 1)
        self.ndof_plate = 3 * self.nn
        self.beams: list[Beam] = []
        self.springs: list[Spring] = []
        self.fixed: set[int] = set()
        self.ties: list[tuple[int, int, float]] = []
        ii, jj = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
        n00 = jj * (nx + 1) + ii
        self.enodes = np.stack([n00, n00 + 1, n00 + nx + 2, n00 + nx + 1], -1)   # (nx, ny, 4)
        self.edof = (3 * self.enodes[..., :, None] + np.arange(3)).reshape(nx, ny, 12)
        self._K0 = None

    # geometry helpers
    def node_xy(self) -> np.ndarray:
        i = np.arange(self.nn) % (self.nx + 1)
        j = np.arange(self.nn) // (self.nx + 1)
        return np.c_[self.x0 + i * self.h, self.y0 + j * self.h]

    def elem_xy(self) -> np.ndarray:
        ii, jj = np.meshgrid(np.arange(self.nx), np.arange(self.ny), indexing="ij")
        return np.stack([self.x0 + (ii + 0.5) * self.h, self.y0 + (jj + 0.5) * self.h], -1)

    def node_at(self, x: float, y: float) -> int:
        i = int(np.clip(round((x - self.x0) / self.h), 0, self.nx))
        j = int(np.clip(round((y - self.y0) / self.h), 0, self.ny))
        return j * (self.nx + 1) + i

    def active_nodes(self) -> np.ndarray:
        m = np.zeros(self.nn, bool)
        m[self.enodes[self.active].ravel()] = True
        return m

    # supports
    def add_beam(self, beam: Beam) -> Beam:
        beam.dof0 = self.ndof + 0
        self.beams.append(beam)
        self._K0 = None
        return beam

    @property
    def ndof(self) -> int:
        return self.ndof_plate + sum(2 * len(b.xy) for b in self.beams)

    def add_tie(self, dof_a: int, dof_b: int, k: float = 1.0e5):
        """Bilateral spring between two global dofs (e.g. two beams that cross)."""
        self.ties.append((int(dof_a), int(dof_b), float(k)))
        self._K0 = None

    def fix_w(self, nodes):
        for n in np.atleast_1d(nodes):
            self.fixed.add(3 * int(n))
        self._K0 = None

    # assembly
    def _K_base(self):
        if self._K0 is not None:
            return self._K0
        act = self.active
        Dv = _Dvec(self.D[act])                                    # (ne, 6)
        Ke = np.einsum("ek,kab->eab", Dv, self.el.Kb)              # (ne, 12, 12)
        ed = self.edof[act]
        rows = np.repeat(ed, 12, axis=1).ravel()
        cols = np.tile(ed, (1, 12)).ravel()
        K = sp.coo_matrix((Ke.ravel(), (rows, cols)), shape=(self.ndof, self.ndof))
        self._K0 = K.tocsr() + self._K_supports()
        return self._K0

    def _K_supports(self, ndof: int | None = None):
        """Beams and ties only (no plate bending), size ``ndof`` (default self.ndof)."""
        ndof = self.ndof if ndof is None else ndof
        parts = [sp.csr_matrix((ndof, ndof))]
        for b in self.beams:
            n = len(b.xy)
            L = np.linalg.norm(np.diff(b.xy, axis=0), axis=1)
            r, c, v = [], [], []
            for e in range(n - 1):
                l = L[e]
                k = b.EI / l ** 3 * np.array([[12, 6 * l, -12, 6 * l], [6 * l, 4 * l * l, -6 * l, 2 * l * l],
                                              [-12, -6 * l, 12, -6 * l], [6 * l, 2 * l * l, -6 * l, 4 * l * l]])
                d = b.dof0 + 2 * e + np.arange(4)
                r += list(np.repeat(d, 4)); c += list(np.tile(d, 4)); v += list(k.ravel())
            parts.append(sp.coo_matrix((v, (r, c)), shape=(ndof, ndof)))
        if self.ties:
            r, c, v = [], [], []
            for a, b, k in self.ties:
                r += [a, b, a, b]; c += [a, b, b, a]; v += [k, k, -k, -k]
            parts.append(sp.coo_matrix((v, (r, c)), shape=(ndof, ndof)))
        return sum(p.tocsr() for p in parts)

    def _fixed_dofs(self) -> np.ndarray:
        fx = set(self.fixed)
        inact = ~self.active_nodes()
        for n in np.nonzero(inact)[0]:
            fx.update((3 * n, 3 * n + 1, 3 * n + 2))
        for b in self.beams:
            n = len(b.xy)
            if b.clamp_start:
                fx.update((b.dof0, b.dof0 + 1))
            if b.clamp_end:
                fx.update((b.dof0 + 2 * (n - 1), b.dof0 + 2 * (n - 1) + 1))
            if b.pin_start and not b.clamp_start:
                fx.add(b.dof0)
            if b.pin_end and not b.clamp_end:
                fx.add(b.dof0 + 2 * (n - 1))
        fx.update(getattr(self, "fixed_dofs_extra", set()))
        return np.array(sorted(fx), int)

    def load_vector(self, q_elem=None, point=None) -> np.ndarray:
        """q_elem (nx, ny) uniform pressure per element (MPa). point: list of (x, y, F)."""
        f = np.zeros(self.ndof)
        if q_elem is not None:
            q = np.where(self.active, q_elem, 0.0)
            np.add.at(f, self.edof.reshape(-1, 12), q.reshape(-1, 1) * self.el.fN[None, :])
        for (x, y, F) in point or []:
            n = self.node_at(x, y)
            f[3 * n] += F
        return f

    def patch_pressure(self, xc: float, yc: float, d: float, F: float, sub: int = 6) -> np.ndarray:
        """Element pressure field of a force F spread uniformly on a disc of diameter d."""
        h = self.h
        s = (np.arange(sub) + 0.5) / sub * h
        XY = self.elem_xy() - h / 2
        frac = np.zeros((self.nx, self.ny))
        for a in s:
            for b in s:
                frac += (np.hypot(XY[..., 0] + a - xc, XY[..., 1] + b - yc) <= d / 2)
        frac /= sub * sub
        frac = np.where(self.active, frac, 0.0)
        area = frac.sum() * h * h
        if area <= 0:
            return np.zeros_like(frac)
        return F * frac / area

    # solve
    def solve(self, f: np.ndarray, k_pen: float = 2.0e4, max_iter: int = 80, active0=None) -> dict:
        K0 = self._K_base()
        fixed = self._fixed_dofs()
        free = np.setdiff1d(np.arange(self.ndof), fixed)
        S = self.springs
        a_dof = np.array([3 * s.node for s in S], int)
        o_dof = np.array([(-1 if s.other is None else s.other) for s in S], int)
        kk = np.array([s.k if s.k > 0 else k_pen for s in S], float)
        gg = np.array([s.gap for s in S], float)
        uni = np.array([s.unilateral for s in S], bool)
        sen = np.array([s.sense for s in S], float)
        act = (gg <= 0) | ~uni if active0 is None else np.asarray(active0, bool).copy()
        u = np.zeros(self.ndof)
        for it in range(max_iter):
            a = act
            r, c, v = [], [], []
            fs = f.copy()
            ad, od, ka, ga = a_dof[a], o_dof[a], kk[a], gg[a]
            r += list(ad); c += list(ad); v += list(ka)
            np.add.at(fs, ad, ka * ga)
            m = od >= 0
            r += list(od[m]); c += list(od[m]); v += list(ka[m])
            r += list(ad[m]); c += list(od[m]); v += list(-ka[m])
            r += list(od[m]); c += list(ad[m]); v += list(-ka[m])
            np.add.at(fs, od[m], -ka[m] * ga[m])
            Ks = sp.coo_matrix((v, (r, c)), shape=K0.shape).tocsr()
            K = (K0 + Ks)[free][:, free]
            u = np.zeros(self.ndof)
            u[free] = _spsolve(K.tocsr(), fs[free])
            wo = np.where(o_dof >= 0, u[np.maximum(o_dof, 0)], 0.0)
            pen = u[a_dof] - wo - gg
            new = np.where(uni, sen * pen > 0.0, True)
            chg = new != act
            nchg = int(chg.sum())
            if nchg == 0 or (it >= 30 and nchg <= max(2, len(S) // 500)):
                act = new if nchg == 0 else act
                break
            if it >= 8:
                # active-set chatter: flip only the worst violators (largest |penetration error|)
                viol = np.where(chg, np.abs(pen), -1.0)
                keep = max(1, nchg // 4)
                idx = np.argsort(viol)[::-1][:keep]
                new = act.copy()
                new[idx] = ~act[idx]
            act = new
        wo = np.where(o_dof >= 0, u[np.maximum(o_dof, 0)], 0.0)
        pen = u[a_dof] - wo - gg
        force = np.where(act, kk * pen, 0.0)
        return {"u": u, "w": u[0:self.ndof_plate:3], "active": act, "spring_force": force, "iters": it + 1}

    # post
    def moments(self, u: np.ndarray) -> np.ndarray:
        """Moments (nx, ny, 4 gauss, 3) [Mx, My, Mxy] with M = -D kappa (sagging positive)."""
        ue = u[self.edof]                                           # (nx, ny, 12)
        out = np.zeros((self.nx, self.ny, 4, 3))
        for g, (x, y) in enumerate(self.el.gauss):
            kap = np.einsum("ab,ijb->ija", self.el.B(x, y), ue)
            kap[..., 2] = kap[..., 2]  # engineering twist 2 w_xy already
            out[:, :, g, :] = -np.einsum("ijab,ijb->ija", self.D, kap)
        out[~self.active] = 0.0
        return out

    def w_grid(self, u: np.ndarray) -> np.ndarray:
        """Nodal deflection as (nx+1, ny+1)."""
        return u[0:self.ndof_plate:3].reshape(self.ny + 1, self.nx + 1).T


def laminate_bending_fi(lam, M: np.ndarray, knockdown=None, criterion: str = "tsai_wu") -> np.ndarray:
    """Tsai-Wu (or max-stress) failure index for pure bending moments M (..., 3) on a symmetric laminate."""
    from .composite import DEFAULT_KNOCKDOWN, Q_matrix, T_eps, max_stress_fi_vec, tsai_wu_fi_vec
    kd = DEFAULT_KNOCKDOWN if knockdown is None else knockdown
    shp = M.shape[:-1]
    Mf = M.reshape(-1, 3)
    d = np.linalg.inv(lam.D)
    kap = Mf @ d.T                                                   # (n, 3) curvatures
    best = np.zeros(len(Mf))
    for i, (p, a) in enumerate(zip(lam.plies, lam.angles)):
        pk = p.knocked_down(kd)
        for zz in (lam.z[i], lam.z[i + 1]):
            sig = (Q_matrix(p) @ T_eps(a) @ (zz * kap.T)).T
            fi = tsai_wu_fi_vec(sig, pk) if criterion == "tsai_wu" else max_stress_fi_vec(sig, pk)
            best = np.maximum(best, fi)
    return best.reshape(shp)


# ----------------------------------------------------------------------------- von Karman (large deflection)
def _q4_Bm(h: float, x: float, y: float) -> np.ndarray:
    """Bilinear membrane strain operator (3, 8) on an h x h square, node order as ACM
    (0,0), (h,0), (h,h), (0,h); dofs (u0, v0, u1, v1, ...)."""
    xi, et = x / h, y / h
    dNx = np.array([-(1 - et), (1 - et), et, -et]) / h
    dNy = np.array([-(1 - xi), -xi, xi, (1 - xi)]) / h
    B = np.zeros((3, 8))
    B[0, 0::2] = dNx
    B[1, 1::2] = dNy
    B[2, 0::2] = dNy
    B[2, 1::2] = dNx
    return B


def solve_von_karman(pl: GridPlate, f: np.ndarray, A, fix_uv_nodes=(), n_steps: int = 6, tol: float = 1e-7,
                     max_newton: int = 40, k_pen: float = 2.0e4, active0=None, extra_fixed=(), max_dw: float = 2.0, verbose: bool = False) -> dict:
    """Geometrically nonlinear (von Karman) solve of the same plate: ACM bending plus bilinear membrane
    dofs (u, v), strains eps = grad(u)_sym + 1/2 grad(w) x grad(w). Total Lagrangian, Newton-Raphson with
    load stepping; the unilateral springs are updated inside the Newton loop (semi-smooth Newton).

    ``A``: membrane stiffness (3, 3) or (nx, ny, 3, 3) (N/mm), e.g. Laminate.A or E t / (1 - nu^2) [...].
    ``fix_uv_nodes``: plate nodes held in-plane (clips, rivets). At least the in-plane rigid-body modes must
    be held; inactive nodes are held automatically.

    Returns the same keys as ``GridPlate.solve`` plus ``N`` and ``M`` (nx, ny, 9, 3) at the 3x3 Gauss points
    (N mm/mm, M with the sign of D kappa) and ``uv`` (nn, 2).

    Verified in ``tests/test_plate_vk.py`` against the exact cylindrical-bending solution of a clamped strip
    with immovable edges (Timoshenko & Woinowsky-Krieger, Theory of Plates and Shells, sec. 3) and against the
    linear solver at small load."""
    nx, ny, nn = pl.nx, pl.ny, pl.nn
    n0 = pl.ndof
    ndof = n0 + 2 * nn
    A = np.asarray(A, float)
    Ae = np.broadcast_to(A, (nx, ny, 3, 3)) if A.ndim == 2 else A
    act = pl.active
    De = pl.D[act]
    Aa = Ae[act]
    ne = int(act.sum())
    edw = pl.edof[act]                                                   # (ne, 12)
    edm = n0 + (2 * pl.enodes[act][..., None] + np.arange(2)).reshape(ne, 8)
    ed = np.c_[edw, edm]                                                 # (ne, 20)
    el = pl.el
    g, wg = np.polynomial.legendre.leggauss(3)
    gps = []
    for gi, wi in zip(g, wg):
        for gj, wj in zip(g, wg):
            x, y = (gi + 1) * pl.h / 2, (gj + 1) * pl.h / 2
            Gx = np.array([_Px(x, y), _Py(x, y)]) @ el.Ainv               # (2, 12)
            gps.append((wi * wj * pl.h * pl.h / 4, el.B(x, y), Gx, _q4_Bm(pl.h, x, y)))
    # linear parts (plate bending + beams + ties, and the membrane Bm' A Bm) are assembled once
    K0 = pl._K_base()
    Ksup = sp.block_diag([K0, sp.csr_matrix((2 * nn, 2 * nn))]).tocsr()
    Kmm_e = np.zeros((ne, 8, 8))
    for wt, Bb, Gx, Bm in gps:
        Kmm_e += wt * (Bm.T @ Aa @ Bm)
    rm = np.repeat(edm, 8, axis=1).ravel()
    cm = np.tile(edm, (1, 8)).ravel()
    Ksup = Ksup + sp.coo_matrix((Kmm_e.ravel(), (rm, cm)), shape=(ndof, ndof)).tocsr()
    # fixed dofs: plate/beam fixed + membrane of inactive nodes + requested in-plane holds
    fx = set(pl._fixed_dofs().tolist())
    inact = ~pl.active_nodes()
    for n in np.nonzero(inact)[0]:
        fx.update((n0 + 2 * n, n0 + 2 * n + 1))
    for n in np.atleast_1d(np.asarray(fix_uv_nodes, int)):
        fx.update((n0 + 2 * int(n), n0 + 2 * int(n) + 1))
    fx.update(int(d) for d in extra_fixed)
    fixed = np.array(sorted(fx), int)
    free = np.setdiff1d(np.arange(ndof), fixed)
    S = pl.springs
    a_dof = np.array([3 * s.node for s in S], int)
    o_dof = np.array([(-1 if s.other is None else s.other) for s in S], int)
    kk = np.array([s.k if s.k > 0 else k_pen for s in S], float)
    gg = np.array([s.gap for s in S], float)
    uni = np.array([s.unilateral for s in S], bool)
    sen = np.array([s.sense for s in S], float)
    actS = ((gg <= 0) | ~uni) if active0 is None else np.asarray(active0, bool).copy()
    fext = np.zeros(ndof)
    fext[:n0] = f[:n0]
    rows = np.repeat(ed, 20, axis=1).ravel()
    cols = np.tile(ed, (1, 20)).ravel()

    def internal(u):
        """Nonlinear part only: the linear bending and Bm' A Bm terms are in Ksup."""
        ue = u[ed]
        uw, um = ue[:, :12], ue[:, 12:]
        fe = np.zeros((ne, 20))
        Ke = np.zeros((ne, 20, 20))
        Ns, Ms = [], []
        for wt, Bb, Gx, Bm in gps:
            gw = uw @ Gx.T                                               # (ne, 2)
            enl = np.c_[0.5 * gw[:, 0] ** 2, 0.5 * gw[:, 1] ** 2, gw[:, 0] * gw[:, 1]]
            eps = um @ Bm.T + enl
            N = (Aa @ eps[:, :, None])[:, :, 0]
            Nnl = (Aa @ enl[:, :, None])[:, :, 0]
            Lam = np.zeros((ne, 3, 2))
            Lam[:, 0, 0] = gw[:, 0]; Lam[:, 1, 1] = gw[:, 1]; Lam[:, 2, 0] = gw[:, 1]; Lam[:, 2, 1] = gw[:, 0]
            Hm = Lam @ Gx                                                # (ne, 3, 12)
            HmT = np.transpose(Hm, (0, 2, 1))
            fe[:, :12] += wt * (HmT @ N[:, :, None])[:, :, 0]
            fe[:, 12:] += wt * (Nnl @ Bm)
            Nm = np.empty((ne, 2, 2))
            Nm[:, 0, 0] = N[:, 0]; Nm[:, 1, 1] = N[:, 1]; Nm[:, 0, 1] = Nm[:, 1, 0] = N[:, 2]
            Ke[:, :12, :12] += wt * (HmT @ (Aa @ Hm) + Gx.T @ Nm @ Gx)
            Kwm = HmT @ (Aa @ Bm)
            Ke[:, :12, 12:] += wt * Kwm
            Ke[:, 12:, :12] += wt * np.transpose(Kwm, (0, 2, 1))
            Ns.append(N)
            Ms.append((De @ (uw @ Bb.T)[:, :, None])[:, :, 0])
        F = np.zeros(ndof)
        np.add.at(F, ed.ravel(), fe.ravel())
        K = sp.coo_matrix((Ke.ravel(), (rows, cols)), shape=(ndof, ndof)).tocsr()
        return F, K, np.stack(Ns, 1), np.stack(Ms, 1)

    def springs(u, a):
        ad, od, ka, ga = a_dof[a], o_dof[a], kk[a], gg[a]
        wo = np.where(od >= 0, u[np.maximum(od, 0)], 0.0)
        fs = ka * (u[ad] - wo - ga)
        F = np.zeros(ndof)
        np.add.at(F, ad, fs)
        m = od >= 0
        np.add.at(F, od[m], -fs[m])
        r = list(ad) + list(od[m]) + list(ad[m]) + list(od[m])
        c = list(ad) + list(od[m]) + list(od[m]) + list(ad[m])
        v = list(ka) + list(ka[m]) + list(-ka[m]) + list(-ka[m])
        return F, sp.coo_matrix((v, (r, c)), shape=(ndof, ndof)).tocsr()

    u = np.zeros(ndof)
    fn = max(np.linalg.norm(fext[free]), 1e-12)
    it_tot = 0
    for step in range(1, n_steps + 1):
        lam = step / n_steps
        for it in range(max_newton):
            it_tot += 1
            Fi, Kt, _, _ = internal(u)
            Fs, Ks = springs(u, actS)
            R = Fi + Ksup @ u + Fs - lam * fext
            K = (Kt + Ksup + Ks)[free][:, free]
            du = np.zeros(ndof)
            du[free] = _spsolve(K.tocsr(), -R[free])
            dw = np.abs(du[0:pl.ndof_plate:3]).max(initial=0.0)
            if dw > max_dw:                          # step limiter: an indefinite tangent (membrane
                du *= max_dw / dw                    # compression round a dimple) must not throw the iterate
            u = u + du
            wo = np.where(o_dof >= 0, u[np.maximum(o_dof, 0)], 0.0)
            pen = u[a_dof] - wo - gg
            new = np.where(uni, sen * pen > 0.0, True)
            changed = int((new != actS).sum())
            if it >= 15 and changed:
                viol = np.where(new != actS, np.abs(pen), -1.0)
                idx = np.argsort(viol)[::-1][:max(1, changed // 4)]
                nw = actS.copy(); nw[idx] = ~actS[idx]; new = nw
            actS = new
            res = np.linalg.norm(R[free]) / fn
            if verbose:
                print(f"step {step} it {it} res {res:.2e} dw {dw:.3g} active {int(actS.sum())} changed {changed} wmax {u[0:pl.ndof_plate:3].max():.3g} wmin {u[0:pl.ndof_plate:3].min():.3g}")
            if changed == 0 and dw <= max_dw and (np.linalg.norm(du[free]) <= tol * max(np.linalg.norm(u[free]), 1e-9)
                                                  or res < tol):
                break
    Fi, _, N, M = internal(u)
    wo = np.where(o_dof >= 0, u[np.maximum(o_dof, 0)], 0.0)
    pen = u[a_dof] - wo - gg
    force = np.where(actS, kk * pen, 0.0)
    Nf = np.zeros((nx, ny, 9, 3)); Mf = np.zeros((nx, ny, 9, 3))
    Nf[act] = N; Mf[act] = M
    return {"u": u, "w": u[0:pl.ndof_plate:3], "uv": u[n0:].reshape(nn, 2), "active": actS,
            "spring_force": force, "iters": it_tot, "N": Nf, "M": Mf, "ndof": ndof}


def iso_A(E: float, t: float, nu: float) -> np.ndarray:
    a = E * t / (1.0 - nu ** 2)
    return a * np.array([[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu) / 2.0]])


def iso_surface_vm(N: np.ndarray, M: np.ndarray, t: float) -> np.ndarray:
    """Max von Mises over both faces: sigma = N / t +- 6 M / t^2 (plane stress). N, M (..., 3)."""
    out = None
    for s in (1.0, -1.0):
        sg = N / t + s * 6.0 * M / t ** 2
        vm = np.sqrt(sg[..., 0] ** 2 - sg[..., 0] * sg[..., 1] + sg[..., 1] ** 2 + 3.0 * sg[..., 2] ** 2)
        out = vm if out is None else np.maximum(out, vm)
    return out
