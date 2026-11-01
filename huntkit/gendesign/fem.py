"""Voxel / pixel finite elements for topology optimization (8-node hex H8, 4-node quad Q4).

Structured grids only. Element e of an (nx, ny, nz) grid has index ``ix + nx*(iy + ny*iz)``;
node ``(ix, iy, iz)`` of the (nx+1, ny+1, nz+1) node grid has index ``ix + (nx+1)*(iy + (ny+1)*iz)``.
DOFs are 3 per node (2 in 2D), interleaved. Units mm, N, MPa.

Assembly uses a precomputed CSR pattern so that K(E_e) = sum_e E_e KE costs one ``np.bincount``
per optimization iteration. Fixed DOFs are eliminated symmetrically (rows/cols zeroed, unit
diagonal), so the reduced system stays SPD for conjugate gradients.

Solver: preconditioned CG with a pyamg smoothed-aggregation preconditioner built with the rigid
body modes as near-null space (falls back to scipy CG with a Jacobi preconditioner if pyamg is
missing).
"""
from __future__ import annotations

import itertools

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

try:   # OpenBLAS threading thrashes on the small dense ops inside pyamg/CG: pin to 1 thread
    from threadpoolctl import threadpool_limits
    threadpool_limits(1)
except ImportError:          # pragma: no cover
    pass

try:
    import pyamg
except ImportError:          # pragma: no cover
    pyamg = None

H8_LOCAL = np.array([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                     (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])
Q4_LOCAL = np.array([(0, 0), (1, 0), (1, 1), (0, 1)])


def iso_D3(E=1.0, nu=0.3):
    l = E * nu / ((1 + nu) * (1 - 2 * nu))
    m = E / (2 * (1 + nu))
    D = np.zeros((6, 6))
    D[:3, :3] = l
    D[np.arange(3), np.arange(3)] += 2 * m
    D[3:, 3:] = np.eye(3) * m
    return D


def iso_D2(E=1.0, nu=0.3):
    """Plane stress."""
    return E / (1 - nu ** 2) * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])


def _B_h8(xi, h):
    s = 2 * H8_LOCAL - 1                       # corner signs (8, 3)
    dN = np.zeros((8, 3))
    for a in range(8):
        for d in range(3):
            f = s[a, d] / 8.0
            for o in range(3):
                if o != d:
                    f *= 1 + s[a, o] * xi[o]
            dN[a, d] = f * 2.0 / h             # d/dx = (2/h) d/dxi
    B = np.zeros((6, 24))
    for a in range(8):
        x, y, z = dN[a]
        B[0, 3 * a] = x; B[1, 3 * a + 1] = y; B[2, 3 * a + 2] = z
        B[3, 3 * a] = y; B[3, 3 * a + 1] = x
        B[4, 3 * a + 1] = z; B[4, 3 * a + 2] = y
        B[5, 3 * a] = z; B[5, 3 * a + 2] = x
    return B


def ke_h8(h=1.0, E=1.0, nu=0.3):
    """24x24 stiffness of a cube of edge h (2x2x2 Gauss)."""
    D = iso_D3(E, nu)
    g = 1 / np.sqrt(3)
    K = np.zeros((24, 24))
    for xi in itertools.product((-g, g), repeat=3):
        B = _B_h8(np.array(xi), h)
        K += B.T @ D @ B * (h / 2) ** 3
    return K


def b_h8_center(h=1.0):
    return _B_h8(np.zeros(3), h)


def _B_q4(xi, h):
    s = 2 * Q4_LOCAL - 1
    dN = np.zeros((4, 2))
    for a in range(4):
        dN[a, 0] = s[a, 0] * (1 + s[a, 1] * xi[1]) / 4 * 2 / h
        dN[a, 1] = s[a, 1] * (1 + s[a, 0] * xi[0]) / 4 * 2 / h
    B = np.zeros((3, 8))
    for a in range(4):
        B[0, 2 * a] = dN[a, 0]; B[1, 2 * a + 1] = dN[a, 1]
        B[2, 2 * a] = dN[a, 1]; B[2, 2 * a + 1] = dN[a, 0]
    return B


def ke_q4(h=1.0, E=1.0, nu=0.3, t=1.0):
    D = iso_D2(E, nu)
    g = 1 / np.sqrt(3)
    K = np.zeros((8, 8))
    for xi in itertools.product((-g, g), repeat=2):
        B = _B_q4(np.array(xi), h)
        K += B.T @ D @ B * (h / 2) ** 2 * t
    return K


def b_q4_center(h=1.0):
    return _B_q4(np.zeros(2), h)


# ----------------------------------------------------------------------------- grids
class Grid:
    """Structured voxel (3D) or pixel (2D) grid with origin ``x0`` (mm) and spacing ``h``."""

    def __init__(self, shape, h, x0=None):
        self.shape = tuple(int(s) for s in shape)
        self.dim = len(self.shape)
        self.h = float(h)
        self.x0 = np.zeros(self.dim) if x0 is None else np.asarray(x0, float)
        self.nshape = tuple(s + 1 for s in self.shape)
        self.ne = int(np.prod(self.shape))
        self.nn = int(np.prod(self.nshape))
        self.ndof = self.nn * self.dim
        loc = H8_LOCAL if self.dim == 3 else Q4_LOCAL
        idx = np.indices(self.shape).reshape(self.dim, -1, order="F").T    # (ne, dim) element ijk
        nodes = np.zeros((self.ne, len(loc)), dtype=np.int64)
        for a, off in enumerate(loc):
            nodes[:, a] = np.ravel_multi_index(tuple((idx + off).T), self.nshape, order="F")
        self.enodes = nodes
        self.edof = (nodes[:, :, None] * self.dim + np.arange(self.dim)).reshape(self.ne, -1)
        self.eijk = idx

    def elem_centers(self):
        return self.x0 + (self.eijk + 0.5) * self.h

    def node_coords(self):
        idx = np.indices(self.nshape).reshape(self.dim, -1, order="F").T
        return self.x0 + idx * self.h

    def to_array(self, v):
        return np.asarray(v).reshape(self.shape, order="F")

    def from_array(self, a):
        return np.asarray(a).reshape(-1, order="F")


class Assembler:
    """K = sum_e w_e KE over a fixed sparsity pattern, with fixed DOFs eliminated."""

    def __init__(self, edof: np.ndarray, ndof: int, KE: np.ndarray, fixed=None):
        ne, nd = edof.shape
        rows = np.repeat(edof, nd, axis=1).ravel()
        cols = np.tile(edof, (1, nd)).ravel()
        fixed = np.zeros(ndof, bool) if fixed is None else np.asarray(fixed)
        if fixed.dtype != bool:
            m = np.zeros(ndof, bool); m[fixed] = True; fixed = m
        self.fixed = fixed
        keep = ~(fixed[rows] | fixed[cols])
        key = rows.astype(np.int64) * ndof + cols
        key_k = key[keep]
        fx = np.where(fixed)[0].astype(np.int64)
        allkeys = np.concatenate([key_k, fx * ndof + fx])
        uniq, inv = np.unique(allkeys, return_inverse=True)
        self.inv = inv[: key_k.size].astype(np.int64)
        self.inv_fixed = inv[key_k.size:]
        self.keep = keep
        self.rows = (uniq // ndof).astype(np.int32)
        self.cols = (uniq % ndof).astype(np.int32)
        self.nnz = uniq.size
        self.ndof = ndof
        self.ke_flat = KE.ravel()
        self.ne, self.nd = ne, nd
        indptr = np.zeros(ndof + 1, np.int64)
        np.add.at(indptr, self.rows.astype(np.int64) + 1, 1)
        self.indptr = np.cumsum(indptr)

    def assemble(self, w: np.ndarray) -> sp.csr_matrix:
        vals = (w[:, None] * self.ke_flat[None, :]).ravel()[self.keep]
        data = np.bincount(self.inv, weights=vals, minlength=self.nnz)
        data[self.inv_fixed] = 1.0
        return sp.csr_matrix((data, self.cols, self.indptr), shape=(self.ndof, self.ndof))


def rigid_modes(coords: np.ndarray) -> np.ndarray:
    n, dim = coords.shape
    c = coords - coords.mean(axis=0)
    if dim == 2:
        B = np.zeros((2 * n, 3))
        B[0::2, 0] = 1; B[1::2, 1] = 1
        B[0::2, 2] = -c[:, 1]; B[1::2, 2] = c[:, 0]
        return B
    B = np.zeros((3 * n, 6))
    for d in range(3):
        B[d::3, d] = 1
    x, y, z = c.T
    B[0::3, 3] = -y; B[1::3, 3] = x
    B[1::3, 4] = -z; B[2::3, 4] = y
    B[0::3, 5] = z;  B[2::3, 5] = -x
    return B


class Solver:
    """PCG with a (re-usable) AMG preconditioner. ``refresh`` = rebuild the hierarchy every n calls."""

    def __init__(self, coords: np.ndarray, fixed: np.ndarray, tol=1e-7, refresh=1, maxiter=200,
                 direct_below: int = 30000):
        self.direct_below = direct_below
        self.B = rigid_modes(coords)
        self.B[np.asarray(fixed, bool)] = 0.0
        self.tol, self.refresh, self.maxiter = tol, refresh, maxiter
        self.ml, self.calls = None, 0
        self.last_iters = []

    def precond(self, K):
        if pyamg is None:
            d = K.diagonal()
            return spla.LinearOperator(K.shape, matvec=lambda x: x / d)
        if self.ml is None or self.calls % self.refresh == 0:
            self.ml = pyamg.smoothed_aggregation_solver(K, B=self.B, symmetry="symmetric",
                                                        max_coarse=300, coarse_solver="splu")
        return self.ml.aspreconditioner(cycle="V")

    def solve(self, K, F, x0=None):
        """F (ndof,) or (ndof, ncases) -> U of the same shape."""
        if K.shape[0] <= self.direct_below:
            self.calls += 1
            lu = spla.splu(K.tocsc())
            self.last_iters = [0]
            return lu.solve(F.reshape(F.shape[0], -1)).reshape(F.shape)
        M = self.precond(K)
        self.calls += 1
        F2 = F.reshape(F.shape[0], -1)
        U = np.zeros_like(F2)
        its = []
        for c in range(F2.shape[1]):
            n = [0]

            def cb(_):
                n[0] += 1
            x_init = None if x0 is None else x0.reshape(F.shape[0], -1)[:, c]
            u, info = spla.cg(K, F2[:, c], x0=x_init, rtol=self.tol, maxiter=self.maxiter, M=M, callback=cb)
            if info != 0:   # fall back to a direct solve (small/awkward problems)
                u = spla.spsolve(K.tocsc(), F2[:, c])
            U[:, c] = u
            its.append(n[0])
        self.last_iters = its
        return U.reshape(F.shape)


def von_mises_3d(s):
    sx, sy, sz, txy, tyz, tzx = s.T
    return np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + tyz ** 2 + tzx ** 2))


def von_mises_2d(s):
    sx, sy, txy = s.T
    return np.sqrt(sx ** 2 - sx * sy + sy ** 2 + 3 * txy ** 2)


def density_filter(grid: Grid, rmin_vox: float, active=None) -> tuple[sp.csr_matrix, np.ndarray]:
    """Linear hat density filter (Bruns/Tortorelli; Andreassen 2011 top88). Returns (H, Hs)."""
    r = int(np.ceil(rmin_vox)) - 1 if float(rmin_vox).is_integer() else int(np.floor(rmin_vox))
    offs = [o for o in itertools.product(range(-r, r + 1), repeat=grid.dim)
            if rmin_vox - np.sqrt(sum(v * v for v in o)) > 0]
    ijk = grid.eijk
    rows, cols, vals = [], [], []
    shape = np.array(grid.shape)
    e_all = np.arange(grid.ne)
    for o in offs:
        n = ijk + np.array(o)
        ok = np.all((n >= 0) & (n < shape), axis=1)
        j = np.ravel_multi_index(tuple(n[ok].T), grid.shape, order="F")
        rows.append(e_all[ok]); cols.append(j)
        vals.append(np.full(ok.sum(), rmin_vox - np.sqrt(sum(v * v for v in o))))
    H = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(grid.ne, grid.ne))
    Hs = np.asarray(H.sum(axis=1)).ravel()
    return H, Hs
