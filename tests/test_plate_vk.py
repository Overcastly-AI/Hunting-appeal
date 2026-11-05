"""Verification of the von Karman (large-deflection) plate solver in huntkit.fea.plate_grid.

Reference: cylindrical bending of a long plate with built-in, immovable edges under uniform pressure
(Timoshenko & Woinowsky-Krieger, Theory of Plates and Shells, 2nd ed., sec. 3). For a given membrane force
N the deflection is exact (beam-column): w = q x (b - x) / (2N) + C [cosh k(x - b/2) - cosh(kb/2)],
C = q b / (2 N k sinh(kb/2)), k^2 = N / D. The edges are immovable, so N = A11 / (2b) * int w'^2 dx,
which is solved for N by root finding.
"""
import numpy as np
from scipy.optimize import brentq

from huntkit.fea.plate_grid import GridPlate, iso_A, iso_D, solve_von_karman

E, NU, T, B, Q = 1000.0, 0.3, 1.0, 100.0, 0.002


def _strip_exact(q=Q):
    D = E * T ** 3 / (12 * (1 - NU ** 2))
    A11 = E * T / (1 - NU ** 2)
    x = np.linspace(0, B, 4001)

    def wfun(N):
        k = np.sqrt(N / D)
        C = q * B / (2 * N * k * np.sinh(k * B / 2))
        w = q * x * (B - x) / (2 * N) + C * (np.cosh(k * (x - B / 2)) - np.cosh(k * B / 2))
        return w

    def res(N):
        w = wfun(N)
        wp = np.gradient(w, x)
        return N - A11 / (2 * B) * np.trapezoid(wp ** 2, x)

    N = brentq(res, 1e-6, 1e3)
    return float(wfun(N).max()), N


def _strip_model(q=Q, nx=25):
    h = B / nx
    pl = GridPlate(0.0, 0.0, nx, 2, h, iso_D(E, T, NU))
    xy = pl.node_xy()
    n0 = pl.ndof
    extra = []
    edge = np.nonzero((xy[:, 0] < 1e-9) | (xy[:, 0] > B - 1e-9))[0]
    for n in range(pl.nn):
        extra += [3 * n + 2, n0 + 2 * n + 1]          # w,y = 0 and v = 0: cylindrical bending, plane strain
    for n in edge:
        extra += [3 * n, 3 * n + 1, n0 + 2 * n]       # built-in, immovable
    f = pl.load_vector(np.full((pl.nx, pl.ny), q))
    return pl, f, extra, edge


def test_vk_clamped_strip_matches_exact():
    w_ex, N_ex = _strip_exact()
    pl, f, extra, edge = _strip_model()
    sol = solve_von_karman(pl, f, iso_A(E, T, NU), fix_uv_nodes=edge, extra_fixed=extra, n_steps=4)
    w = sol["w"].max()
    # linear answer for scale: q b^4 / (384 D)
    D = E * T ** 3 / (12 * (1 - NU ** 2))
    w_lin = Q * B ** 4 / (384 * D)
    assert w_ex < 0.7 * w_lin            # the case is genuinely nonlinear
    assert abs(w - w_ex) / w_ex < 0.03
    Nx = sol["N"][..., 0][pl.active].mean()
    assert abs(Nx - N_ex) / N_ex < 0.05


def test_vk_small_load_equals_linear():
    pl, f, extra, edge = _strip_model(q=1e-6)
    pl.fixed_dofs_extra = {d for d in extra if d < pl.ndof}
    lin = pl.solve(f)
    sol = solve_von_karman(pl, f, iso_A(E, T, NU), fix_uv_nodes=edge, extra_fixed=extra, n_steps=1)
    assert np.allclose(sol["w"], lin["w"], rtol=1e-4, atol=1e-12)
