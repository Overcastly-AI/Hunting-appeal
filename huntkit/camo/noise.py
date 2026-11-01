"""Seamless (periodic) procedural noise primitives — numpy/scipy only.

Every function here works on a periodic grid of ``ny x nx`` samples spanning a physical
repeat of ``height_mm x width_mm``. Because every primitive is built either in the
Fourier domain (periodic by construction) or with periodic distance metrics
(``cKDTree(boxsize=...)``), anything composed from them tiles seamlessly.

All randomness comes from ``numpy.random.Generator`` objects derived from an integer seed
plus a string key (``substream``), so results are fully deterministic and independent of
evaluation order.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np
from scipy import ndimage, sparse
from scipy.spatial import cKDTree


# ----------------------------------------------------------------------------- RNG
def substream(seed: int, key: str) -> np.random.Generator:
    """Deterministic generator for (seed, key). Stable across runs/platforms (crc32)."""
    return np.random.default_rng([int(seed) & 0xFFFFFFFF, zlib.crc32(key.encode("utf-8"))])


# ----------------------------------------------------------------------------- grid
@dataclass(frozen=True)
class Grid:
    """Periodic sample grid over one repeat."""

    width_mm: float
    height_mm: float
    nx: int
    ny: int

    @classmethod
    def from_density(cls, width_mm: float, height_mm: float, px_per_mm: float) -> "Grid":
        return cls(width_mm, height_mm, max(8, int(round(width_mm * px_per_mm))),
                   max(8, int(round(height_mm * px_per_mm))))

    @property
    def dx(self) -> float:  # mm per sample, x
        return self.width_mm / self.nx

    @property
    def dy(self) -> float:
        return self.height_mm / self.ny

    def coords_mm(self) -> tuple[np.ndarray, np.ndarray]:
        """(Y, X) sample-centre coordinates in mm, shape (ny, nx)."""
        x = (np.arange(self.nx) + 0.5) * self.dx
        y = (np.arange(self.ny) + 0.5) * self.dy
        return np.meshgrid(y, x, indexing="ij")


def normalize(a: np.ndarray) -> np.ndarray:
    """Zero mean, unit standard deviation (float32)."""
    a = np.asarray(a, dtype=np.float64)
    s = a.std()
    return ((a - a.mean()) / (s if s > 0 else 1.0)).astype(np.float32)


# ----------------------------------------------------------------------------- FFT fractal noise
def fbm(grid: Grid, rng: np.random.Generator, scale_mm: float, min_mm: float | None = None,
        beta: float = 1.8, aniso_ratio: float = 1.0, aniso_angle_deg: float = 0.0) -> np.ndarray:
    """Band-limited fractal (1/f^beta amplitude) noise synthesised in the Fourier domain.

    ``scale_mm``  : largest feature size (low-frequency corner, f0 = 1/scale_mm).
    ``min_mm``    : smallest feature size (Gaussian high-frequency roll-off at 1/min_mm).
    ``beta``      : amplitude spectral slope; 1.0 = pink-ish/rough, 2.0+ = smooth blobs.
    ``aniso_ratio``: >1 elongates features along ``aniso_angle_deg`` (0 = horizontal).

    Periodic by construction (only integer cycles-per-repeat frequencies exist on the grid).
    Returns a zero-mean, unit-std float32 array (ny, nx).
    """
    fx = np.fft.fftfreq(grid.nx, d=grid.dx)  # cycles / mm
    fy = np.fft.fftfreq(grid.ny, d=grid.dy)
    FY, FX = np.meshgrid(fy, fx, indexing="ij")
    if aniso_ratio != 1.0:
        th = np.deg2rad(aniso_angle_deg)
        u = FX * np.cos(th) + FY * np.sin(th)     # along elongation axis
        v = -FX * np.sin(th) + FY * np.cos(th)
        # features long along u -> compress frequencies along u
        FX, FY = u * aniso_ratio, v
    f = np.sqrt(FX ** 2 + FY ** 2)
    f0 = 1.0 / float(scale_mm)
    f1 = 1.0 / float(min_mm) if min_mm else np.inf
    with np.errstate(divide="ignore", invalid="ignore"):
        amp = (f ** 2 / (f ** 2 + f0 ** 2)) * np.power(np.maximum(f, 1e-12), -beta)
        if np.isfinite(f1):
            amp *= np.exp(-((f / f1) ** 2))
    amp[0, 0] = 0.0
    spec = (rng.standard_normal(f.shape) + 1j * rng.standard_normal(f.shape)) * amp
    return normalize(np.fft.ifft2(spec).real)


# ----------------------------------------------------------------------------- domain warp
def warp_coords(grid: Grid, rng: np.random.Generator, scale_mm: float, amp_mm: float,
                iterations: int = 1, beta: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Periodic domain-warp: returns warped (Y, X) mm coordinates.

    Iterated warping: p <- p + amp * n(p), where n is a periodic fbm vector field sampled at
    the already-warped position (Quilez-style). Displacements are periodic, so the warped
    coordinates still map the repeat onto itself seamlessly.
    """
    Y, X = grid.coords_mm()
    Y = Y.astype(np.float64)
    X = X.astype(np.float64)
    for it in range(max(1, int(iterations))):
        nx_ = fbm(grid, rng, scale_mm, None, beta)
        ny_ = fbm(grid, rng, scale_mm, None, beta)
        # sample the displacement fields at the current (warped) position
        ry, rx = Y / grid.dy - 0.5, X / grid.dx - 0.5
        dxs = ndimage.map_coordinates(nx_, [ry, rx], order=1, mode="grid-wrap")
        dys = ndimage.map_coordinates(ny_, [ry, rx], order=1, mode="grid-wrap")
        a = amp_mm / (it + 1)  # later iterations add finer, weaker distortion
        X = X + a * dxs
        Y = Y + a * dys
    return Y, X


def sample_periodic(field: np.ndarray, grid: Grid, Y: np.ndarray, X: np.ndarray,
                    order: int = 1) -> np.ndarray:
    """Sample a periodic field (on ``grid``) at arbitrary mm coordinates (wrapping)."""
    return ndimage.map_coordinates(field, [Y / grid.dy - 0.5, X / grid.dx - 0.5],
                                   order=order, mode="grid-wrap").astype(np.float32)


# ----------------------------------------------------------------------------- periodic Voronoi
def voronoi(grid: Grid, rng: np.random.Generator, cell_mm: float, Y: np.ndarray,
            X: np.ndarray, jitter: float = 1.0) -> dict[str, np.ndarray]:
    """Periodic (toroidal) Voronoi evaluated at mm coordinates (Y, X).

    Sites: jittered grid with ~cell_mm spacing (``jitter`` 1.0 = fully random within cell).
    Distances use cKDTree's periodic ``boxsize`` so cells wrap across repeat edges.
    Returns dict with ``f1``, ``f2`` (mm), ``cell`` (site index) and ``value`` (uniform
    random per-cell value in [-1, 1]).
    """
    W, H = grid.width_mm, grid.height_mm
    ncx = max(1, int(round(W / cell_mm)))
    ncy = max(1, int(round(H / cell_mm)))
    gx, gy = np.meshgrid((np.arange(ncx) + 0.5) * W / ncx, (np.arange(ncy) + 0.5) * H / ncy)
    jx = (rng.random(gx.shape) - 0.5) * jitter * W / ncx
    jy = (rng.random(gy.shape) - 0.5) * jitter * H / ncy
    sites = np.column_stack([np.mod(gx + jx, W).ravel(), np.mod(gy + jy, H).ravel()])
    values = rng.uniform(-1.0, 1.0, len(sites))
    tree = cKDTree(sites, boxsize=[W, H])
    q = np.column_stack([np.mod(X, W).ravel(), np.mod(Y, H).ravel()])
    # guard the exact-boundary case for cKDTree periodic queries
    q[:, 0] = np.where(q[:, 0] >= W, 0.0, q[:, 0])
    q[:, 1] = np.where(q[:, 1] >= H, 0.0, q[:, 1])
    k = 2 if len(sites) > 1 else 1
    d, idx = tree.query(q, k=k, workers=-1)
    if k == 1:
        d = np.column_stack([d, d + cell_mm])
        idx = np.column_stack([idx, idx])
    shape = Y.shape
    return {
        "f1": d[:, 0].reshape(shape).astype(np.float32),
        "f2": d[:, 1].reshape(shape).astype(np.float32),
        "cell": idx[:, 0].reshape(shape),
        "value": values[idx[:, 0]].reshape(shape).astype(np.float32),
    }


# ----------------------------------------------------------------------------- periodic resampling
def _cubic_periodic_matrix(n_in: int, n_out: int) -> sparse.csr_matrix:
    """Sparse (n_out x n_in) Catmull-Rom interpolation matrix with periodic wrap.

    Sample centres are aligned (grid mode): out sample j sits at (j+0.5)*n_in/n_out - 0.5
    in input index space.
    """
    pos = (np.arange(n_out) + 0.5) * (n_in / n_out) - 0.5
    i0 = np.floor(pos).astype(np.int64)
    t = pos - i0
    t2, t3 = t * t, t * t * t
    w = [(-t3 + 2 * t2 - t) / 2, (3 * t3 - 5 * t2 + 2) / 2,
         (-3 * t3 + 4 * t2 + t) / 2, (t3 - t2) / 2]
    rows = np.repeat(np.arange(n_out), 4)
    cols = np.stack([(i0 - 1) % n_in, i0 % n_in, (i0 + 1) % n_in, (i0 + 2) % n_in], 1).ravel()
    vals = np.stack(w, 1).ravel()
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n_out, n_in))


class PeriodicUpsampler:
    """Separable periodic cubic resampler: field (ny, nx) -> (NY, NX), evaluated in row strips."""

    def __init__(self, ny: int, nx: int, NY: int, NX: int):
        self.Ay = _cubic_periodic_matrix(ny, NY)
        self.AxT = _cubic_periodic_matrix(nx, NX).T.tocsr()  # (nx, NX)
        self.NY, self.NX = NY, NX

    def rows(self, field: np.ndarray, r0: int, r1: int) -> np.ndarray:
        tmp = self.Ay[r0:r1] @ field.astype(np.float64)     # (r, nx)
        return np.asarray((self.AxT.T @ tmp.T).T, dtype=np.float32)  # (r, NX)

    def full(self, field: np.ndarray) -> np.ndarray:
        return self.rows(field, 0, self.NY)
