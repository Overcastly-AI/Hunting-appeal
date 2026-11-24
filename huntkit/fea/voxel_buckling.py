"""Linear eigenvalue (bifurcation) buckling of voxel (H8) bodies.

Small-strain linear buckling: (K + lam K_sigma(S0)) phi = 0, where S0 is the linear stress field of the reference load
set and K_sigma is the initial-stress (geometric) stiffness

    K_sigma^e = int dN^T S0 dN dV  (x) I_3,

evaluated with the element's centroid stress (constant over the voxel) and 2 x 2 x 2 Gauss integration of the
shape-function gradient products. lam is the load multiplier on the reference set at bifurcation.

Works on any structured voxel grid of ``huntkit.gendesign.fem.Grid`` through ``frame_topopt.ReducedSystem`` (same DOF
reduction and upper-triangular storage the voxel strength checks use). The eigenproblem is solved as

    -K_sigma phi = mu K phi,   lam = E / mu   (K assembled at unit modulus),

the largest positive mu giving the lowest positive lam (Lanczos, ARPACK mode 2, K factorised once with PARDISO).

Verification (``tests/test_voxel_buckling.py``): voxel columns against Euler (cantilever K = 2, pinned-pinned K = 1),
flat and square sections, and the H8 locking / shear ratio that ``column_ratio`` reports for a section of a given
voxel count (full-integration H8 is slightly stiff in bending; the ratio is used as a stated correction).
Units N, mm, MPa.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from huntkit.gendesign.fem import H8_LOCAL, Grid, ke_h8

# Voigt order of the voxel stress recovery (fem._B_h8 rows): xx, yy, zz, xy, yz, xz
VOIGT = ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2))


def _dN(xi: np.ndarray, h: float) -> np.ndarray:
    s = 2 * H8_LOCAL - 1
    d = np.zeros((8, 3))
    for a in range(8):
        for k in range(3):
            f = s[a, k] / 8.0
            for o in range(3):
                if o != k:
                    f *= 1 + s[a, o] * xi[o]
            d[a, k] = f * 2.0 / h
    return d


def geo_blocks(h: float) -> np.ndarray:
    """(6, 24, 24): K_sigma of a cube of edge h for a unit value of each Voigt stress component (shear components
    include both (i, j) and (j, i))."""
    g = 1 / math.sqrt(3)
    M = np.zeros((3, 3, 8, 8))
    for xi in itertools.product((-g, g), repeat=3):
        d = _dN(np.array(xi), h)
        for i in range(3):
            for j in range(3):
                M[i, j] += np.outer(d[:, i], d[:, j]) * (h / 2) ** 3
    out = np.zeros((6, 24, 24))
    for c, (i, j) in enumerate(VOIGT):
        Hc = M[i, j] if i == j else M[i, j] + M[j, i]
        out[c] = np.kron(Hc, np.eye(3))
    return out


def assemble_geometric(rs, stress_active: np.ndarray, h: float) -> sp.csr_matrix:
    """Upper-triangular reduced K_sigma on ``rs`` (frame_topopt.ReducedSystem) from the per-active-element Voigt stress
    (n_active, 6). Chunked to bound memory."""
    G = geo_blocks(h).reshape(6, -1)                       # (6, 576)
    S = np.asarray(stress_active, float)
    ne = S.shape[0]
    data = np.zeros(rs.rows.size)
    keep = rs.keep
    inv = rs.inv
    # rs.keep is (ne, 576) boolean; rs.inv indexes the kept entries in row-major order
    counts = keep.sum(axis=1)
    start = np.concatenate([[0], np.cumsum(counts)])
    step = 20000
    for a in range(0, ne, step):
        b = min(ne, a + step)
        vals = (S[a:b] @ G)[keep[a:b]]
        data += np.bincount(inv[start[a]:start[b]], weights=vals, minlength=rs.rows.size)
    return sp.csr_matrix((data, rs.cols, rs.indptr), shape=(rs.n, rs.n))


def sym_full(Ku: sp.csr_matrix) -> sp.csr_matrix:
    return (Ku + sp.triu(Ku, 1).T).tocsr()


class Factor:
    """K^-1 by PARDISO (SPD, upper storage); scipy splu fallback."""

    def __init__(self, Ku: sp.csr_matrix):
        Ku = Ku.tocsr()
        Ku.sort_indices()
        self.Ku = Ku
        try:
            import pypardiso
            self.s = pypardiso.PyPardisoSolver(mtype=2)
            self.s.factorize(Ku)
            self.kind = "pardiso"
        except ImportError:                                 # pragma: no cover
            self.s = spla.splu(sym_full(Ku).tocsc())
            self.kind = "splu"

    def solve(self, b: np.ndarray) -> np.ndarray:
        b = np.ascontiguousarray(b, float)
        if self.kind == "pardiso":
            return np.asarray(self.s.solve(self.Ku, b)).reshape(b.shape)
        return self.s.solve(b)                              # pragma: no cover

    def free(self):
        if self.kind == "pardiso":
            try:
                self.s.free_memory(everything=True)
            except Exception:                               # pragma: no cover
                pass


def eig_buckling(Ku: sp.csr_matrix, KGu: sp.csr_matrix, E: float = 1.0, k: int = 6, factor: Factor | None = None,
                 tol: float = 1e-8, v0: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Lowest positive buckling multipliers lam (ascending) and modes (n, k) of (E K + lam K_sigma) phi = 0, with
    Ku, KGu the upper-triangular reduced matrices at unit modulus."""
    Kf = sym_full(Ku)
    A = -sym_full(KGu)
    fac = factor or Factor(Ku)
    n = Kf.shape[0]
    Minv = spla.LinearOperator((n, n), matvec=lambda x: fac.solve(x), dtype=float)
    if v0 is None:
        v0 = np.random.default_rng(0).standard_normal(n)
    mu, V = spla.eigsh(A, k=k, M=Kf, Minv=Minv, which="LA", tol=tol, v0=v0, ncv=max(2 * k + 1, 24))
    if factor is None:
        fac.free()
    order = np.argsort(-mu)
    mu, V = mu[order], V[:, order]
    pos = mu > 0
    lam = np.full(mu.shape, np.inf)
    lam[pos] = E / mu[pos]
    return lam, V


# ---------------------------------------------------------------------------------------------- linear solve + stress
def element_stress_active(rs, U: np.ndarray, h: float, nu: float, weights: np.ndarray | None = None) -> np.ndarray:
    """Centroid Voigt stress (unit modulus x weight) of every active element of ``rs``."""
    from huntkit.gendesign.fem import b_h8_center, iso_D3
    D = iso_D3(1.0, nu)
    B = b_h8_center(h)
    Ue = U[rs.g.edof[rs.ae]]
    S = (Ue @ B.T) @ D.T
    if weights is not None:
        S = S * np.asarray(weights, float)[:, None]
    return S


class VoxelBuckler:
    """One voxel body, factorised once: prestress solves for any number of load vectors, then eigen runs on each.

    fixed: supports of the reference (prestress) solve. extra_fixed: DOFs held in the EIGEN problem only (bracing
    that carries no load in the reference state, e.g. a harness in equilibrium with the load set)."""

    def __init__(self, g: Grid, active: np.ndarray, fixed: np.ndarray, nu: float = 0.35,
                 weights: np.ndarray | None = None, extra_fixed: np.ndarray | None = None):
        from huntkit.gendesign import frame_topopt as ft
        self.g, self.nu = g, nu
        KE = ke_h8(g.h, 1.0, nu)
        self.rs0 = ft.ReducedSystem(g, active, fixed, KE)
        self.w = np.ones(self.rs0.ae.size) if weights is None else np.asarray(weights, float)[self.rs0.ae]
        K0 = self.rs0.assemble(self.w)
        K0.sort_indices()
        self.K0 = K0
        self.fac0 = Factor(K0)
        if extra_fixed is not None and np.any(extra_fixed & ~fixed):
            self.rs = ft.ReducedSystem(g, active, fixed | extra_fixed, KE)
            self.K = self.rs.assemble(self.w)
            self.K.sort_indices()
            self.fac = Factor(self.K)
        else:
            self.rs, self.K, self.fac = self.rs0, K0, self.fac0
        self.ae = self.rs.ae
        self._fixed = fixed
        self._active = active
        self.variants = {}

    def add_variant(self, name: str, extra_fixed: np.ndarray):
        """Another eigen support (reference supports + extra_fixed), sharing the prestress system."""
        from huntkit.gendesign import frame_topopt as ft
        rs = ft.ReducedSystem(self.g, self._active, self._fixed | extra_fixed, ke_h8(self.g.h, 1.0, self.nu))
        K = rs.assemble(self.w)
        K.sort_indices()
        self.variants[name] = (rs, K, Factor(K))

    def view(self, variant: str | None = None, braced: bool = True):
        from types import SimpleNamespace
        rs = self.variants[variant][0] if variant else (self.rs if braced else self.rs0)
        return SimpleNamespace(rs=rs, g=self.g, ae=rs.ae)

    def prestress(self, F: np.ndarray) -> list:
        """Physical centroid stresses (n_active, 6) for each column of F (ndof,) or (ndof, m)."""
        F2 = F.reshape(F.shape[0], -1)
        Ur = self.fac0.solve(F2[self.rs0.free]).reshape(self.rs0.free.size, -1)
        out = []
        for j in range(Ur.shape[1]):
            U = np.zeros(self.g.ndof)
            U[self.rs0.free] = Ur[:, j]
            out.append(element_stress_active(self.rs0, U, self.g.h, self.nu, self.w))
        return out

    def eig(self, S: np.ndarray, E: float, k: int = 6, kg_weight: np.ndarray | None = None, tol: float = 1e-8,
            braced: bool = True, variant: str | None = None):
        """(lam, modes (ndof, k) global) for the prestress S (active order). kg_weight (g.ne) scales K_sigma per
        element: 0 outside a member isolates that member, the rest of the body acting as its stress-free elastic
        end restraint. braced=False solves on the reference supports only (no extra_fixed)."""
        if variant is not None:
            rs, K, fac = self.variants[variant]
        else:
            rs, K, fac = (self.rs, self.K, self.fac) if braced else (self.rs0, self.K0, self.fac0)
        Sk = S if kg_weight is None else S * np.asarray(kg_weight, float)[self.ae][:, None]
        KG = assemble_geometric(rs, Sk, self.g.h)
        lam, V = eig_buckling(K, KG, E=E, k=k, factor=fac, tol=tol)
        modes = np.zeros((self.g.ndof, V.shape[1]))
        modes[rs.free] = V
        return lam, modes

    def unbraced(self):
        """A view with the reference-support system (for mode energy on the unbraced eigen problem)."""
        from types import SimpleNamespace
        return SimpleNamespace(rs=self.rs0, g=self.g, ae=self.rs0.ae)

    def free(self):
        for _, _, f in self.variants.values():
            f.free()
        self.variants = {}
        self.fac.free()
        if self.fac0 is not self.fac:
            self.fac0.free()


def linear_buckling(g: Grid, active: np.ndarray, fixed: np.ndarray, F: np.ndarray, E: float, nu: float = 0.35,
                    k: int = 6, weights: np.ndarray | None = None, extra_fixed: np.ndarray | None = None,
                    kg_weight: np.ndarray | None = None, tol: float = 1e-8) -> dict:
    """Whole pipeline for one load vector F (ndof,): returns lam (load multipliers on F), modes (ndof, k), the
    physical stresses and the eigen system ``rs``. See VoxelBuckler for extra_fixed / kg_weight."""
    vb = VoxelBuckler(g, active, fixed, nu, weights, extra_fixed)
    S = vb.prestress(F)[0]
    lam, modes = vb.eig(S, E, k, kg_weight, tol)
    vb.free()
    return {"lam": lam, "modes": modes, "stress": S, "rs": vb.rs}


# ---------------------------------------------------------------------------------------------- verification helpers
def column_case(b_mm: float, d_mm: float, L_mm: float, h: float, ends: str = "cantilever", P: float = 1.0):
    """Voxel column, section b (x) x d (y), length L along z, axial load P (compression) on the top face.

    ends: 'cantilever' (base clamped, top free: K = 2) or 'pinned' (both ends pinned about the weak axis: a line of
    nodes at mid-depth in y fixed in x, y (and z at the base); K = 1 in the weak plane (bending about x, deflection
    in y))."""
    nx, ny, nz = int(round(b_mm / h)), int(round(d_mm / h)), int(round(L_mm / h))
    g = Grid((nx, ny, nz), h)
    active = np.ones(g.ne, bool)
    nc = g.node_coords()
    top = np.isclose(nc[:, 2], nz * h)
    bot = np.isclose(nc[:, 2], 0.0)
    fixed = np.zeros(g.ndof, bool)
    F = np.zeros(g.ndof)
    # consistent nodal load of a uniform pressure on the top face
    wx = np.where(np.isclose(nc[:, 0], 0) | np.isclose(nc[:, 0], nx * h), 0.5, 1.0)
    wy = np.where(np.isclose(nc[:, 1], 0) | np.isclose(nc[:, 1], ny * h), 0.5, 1.0)
    wt = (wx * wy)[top]
    F[3 * np.where(top)[0] + 2] = -P * wt / wt.sum()
    if ends == "cantilever":
        fixed[(3 * np.where(bot)[0][:, None] + np.arange(3)).ravel()] = True
    elif ends == "pinned":
        ymid = np.isclose(nc[:, 1], ny * h / 2)
        b0 = np.where(bot & ymid)[0]
        t0 = np.where(top & ymid)[0]
        fixed[(3 * b0[:, None] + np.arange(3)).ravel()] = True
        fixed[(3 * t0[:, None] + np.arange(2)).ravel()] = True
        # the base pin line takes the reaction; spread the base reaction by fixing z only on that line (pin)
    else:
        raise ValueError(ends)
    return g, active, fixed, F


def column_ratio(b_mm: float, d_mm: float, L_mm: float, h: float, ends: str = "cantilever", E: float = 1000.0,
                 nu: float = 0.35) -> dict:
    """Voxel P_cr / Euler P_cr for a solid b x d column (weak axis I = b d^3 / 12 with d <= b)."""
    g, active, fixed, F = column_case(b_mm, d_mm, L_mm, h, ends)
    r = linear_buckling(g, active, fixed, F, E, nu, k=2)
    I = min(b_mm * d_mm ** 3, d_mm * b_mm ** 3) / 12.0
    K = 2.0 if ends == "cantilever" else 1.0
    pe = math.pi ** 2 * E * I / (K * L_mm) ** 2
    return {"Pcr_fe": float(r["lam"][0]), "Pcr_euler": pe, "ratio": float(r["lam"][0]) / pe}


def mode_q(rs, phi_global: np.ndarray, h: float) -> np.ndarray:
    """(n_active, 6): phi_e^T K_sigma(unit Voigt component c)^e phi_e. The geometric energy of the mode under any
    prestress S is then -(q * S).sum(axis=1) per element."""
    G = geo_blocks(h)
    out = np.zeros((rs.ae.size, 6))
    step = 50000
    for a in range(0, rs.ae.size, step):
        b = min(rs.ae.size, a + step)
        pe = np.asarray(phi_global[rs.g.edof[rs.ae[a:b]]], float)
        out[a:b] = np.einsum("ni,cij,nj->nc", pe, G, pe)
    return out


def geometric_energy(rs, stress_active: np.ndarray, phi_global: np.ndarray, h: float) -> np.ndarray:
    """Per active element -phi_e^T K_sigma^e phi_e (positive = the element's compression drives the mode). Its sum
    over the body equals mu x phi^T K phi for an eigenpair, so the shares say WHERE a mode is driven."""
    return -(mode_q(rs, phi_global, h) * stress_active).sum(axis=1)
