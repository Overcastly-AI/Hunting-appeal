"""Closed-form verification of the voxel (H8) linear eigenvalue buckling solver (huntkit.fea.voxel_buckling), BL-065."""
import math

import numpy as np
import pytest

pytest.importorskip("pypardiso")

from huntkit.fea import voxel_buckling as VB  # noqa: E402


def test_geo_blocks_symmetric_and_rigid_free():
    G = VB.geo_blocks(2.0)
    assert G.shape == (6, 24, 24)
    assert np.allclose(G, np.transpose(G, (0, 2, 1)))
    # a rigid translation has no displacement gradient: K_sigma t = 0 for every stress component
    for d in range(3):
        t = np.zeros(24)
        t[d::3] = 1.0
        assert np.allclose(G @ t, 0.0, atol=1e-12)
    # uniaxial unit stress, linear field u_y = x on a cube: phi^T K phi = sigma_xx (du_y/dx)^2 V = h^3
    h = 2.0
    from huntkit.gendesign.fem import H8_LOCAL
    u = np.zeros(24)
    u[1::3] = H8_LOCAL[:, 0] * h
    assert u @ G[0] @ u == pytest.approx(h ** 3, rel=1e-12)


def test_cantilever_column_matches_euler():
    """Fixed-free 12 x 8 x 120 mm column (K = 2), 2 mm voxels (4 through the weak depth): within +6 %; full-integration
    H8 is slightly stiff in bending."""
    r = VB.column_ratio(12.0, 8.0, 120.0, 2.0, "cantilever", E=1000.0)
    assert 0.98 < r["ratio"] < 1.06


def test_pinned_column_matches_euler():
    """Pinned-pinned 16 x 12 x 180 mm (the H1 upper-branch R flat section): voxel P_cr = Euler within 3 %."""
    r = VB.column_ratio(16.0, 12.0, 180.0, 2.0, "pinned", E=1621.2)
    assert r["ratio"] == pytest.approx(1.0, abs=0.03)
    assert r["Pcr_euler"] == pytest.approx(math.pi ** 2 * 1621.2 * 16 * 12 ** 3 / 12 / 180.0 ** 2, rel=1e-9)


def test_linear_in_modulus_and_energy_positive():
    g, active, fixed, F = VB.column_case(8.0, 8.0, 80.0, 2.0, "cantilever")
    a = VB.linear_buckling(g, active, fixed, F, 1000.0, k=1)
    b = VB.linear_buckling(g, active, fixed, F, 2000.0, k=1)
    assert b["lam"][0] == pytest.approx(2 * a["lam"][0], rel=1e-6)
    en = VB.geometric_energy(a["rs"], a["stress"], a["modes"][:, 0], g.h)
    assert en.sum() > 0                    # compression drives the mode
    # square section: Euler cantilever within 6 %
    pe = math.pi ** 2 * 1000.0 * 8 ** 4 / 12 / (2 * 80.0) ** 2
    assert a["lam"][0] / pe == pytest.approx(1.0, abs=0.06)
