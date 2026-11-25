"""huntkit.fea.tube_solid verification against closed forms (BL-081): Heywood open-hole Kt, beam bending / torsion,
Roark ring under a diametral line load. Coarse meshes keep the run short; tolerances are set for them."""
import math

import numpy as np
import pytest

from huntkit.fea.tube_solid import Hole, TubeFE, TubeModel, heywood_kt


def test_heywood_closed_form():
    assert heywood_kt(0.0) == pytest.approx(3.0)
    assert heywood_kt(0.2) == pytest.approx((2 + 0.8 ** 3) / 0.8)


@pytest.fixture(scope="module")
def big_plate():
    # a 400 mm tube is a plate for a 6 mm hole: d / W = 6 / 1257 -> Kt 3.0
    m = TubeModel(L=120.0, od=400.0, t=2.0, holes=[Hole(60.0, 0.0, 6.0, through=False)], h=8.0, h_hole=0.3,
                  n_layers=1)
    return TubeFE(m)


def test_open_hole_kt_plate_limit(big_plate):
    fe = big_plate
    A = math.pi * (200.0 ** 2 - 198.0 ** 2)
    u = fe.solve(fe.end_load(N=1000.0))
    pk = fe.peak_principal(u, 0)
    assert pk / (1000.0 / A) == pytest.approx(heywood_kt(6.0 / (math.pi * 398.0)), rel=0.08)


@pytest.fixture(scope="module")
def plain_tube():
    m = TubeModel(L=100.0, od=25.4, t=1.651, h=2.0, n_layers=2)
    return TubeFE(m)


def test_bending_and_torsion_vs_beam(plain_tube):
    fe = plain_tube
    ro, ri = 12.7, 12.7 - 1.651
    I = math.pi * (ro ** 4 - ri ** 4) / 4
    u = fe.solve(fe.end_load(My=1e4))
    assert fe.surface_peak(u, 35, 65)["max_principal"] == pytest.approx(1e4 * ro / I, rel=0.05)
    u = fe.solve(fe.end_load(T=1e4))
    # FE reads 7 % high in torsion on this 2-layer mesh (conservative for the hole Kt, which shares the normalisation)
    assert fe.surface_peak(u, 35, 65)["max_principal"] == pytest.approx(1e4 * ro / (2 * I), rel=0.08)
    # tip deflection of the cantilever under a tip shear vs Euler-Bernoulli (+ shear, short tube: 10 %)
    u = fe.solve(fe.end_load(Vz=100.0))
    U = u[fe.basis.nodal_dofs]
    tip = np.abs(fe.mesh.p[0] - 100.0) < 1e-6
    w = float(U[2, tip].mean())
    assert w == pytest.approx(100.0 * 100.0 ** 3 / (3 * 68900 * I), rel=0.12)


def test_ring_diametral_load_vs_roark(plain_tube):
    """Two opposite narrow full-length patches pulling the wall out: ring moment at the load 0.318 P R
    (Roark Table 9.2 case 1), sigma = 6 M / t^2, checked on the hoop stress in the middle (end effects away)."""
    fe = plain_tube
    a = math.radians(4.0)
    F = 1000.0
    f = fe.patch_pressure(0.0, 100.0, 0.0, a, F, "inner") + fe.patch_pressure(0.0, 100.0, math.pi, a, F, "inner")
    u = fe.solve(f)
    P = F / 100.0
    Rm = 12.7 - 1.651 / 2
    sig = 6 * 0.318 * P * Rm / 1.651 ** 2
    assert fe.surface_hoop(u, 40, 60) == pytest.approx(sig, rel=0.2)
