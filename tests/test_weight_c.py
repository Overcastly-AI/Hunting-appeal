"""Package C structural gates (huntkit/gendesign/weight_c.py): closed-form checks of the new pieces, then results."""
import math

import numpy as np
import pytest

from huntkit.gendesign import hipbelt_structure as hs
from huntkit.gendesign import weight_c as W


# ------------------------------------------------------------------------------------------- forming (C-1)
def _epp_moment(kappa, t, sy, E, n=4001):
    """Moment per unit width of an elastic-perfectly-plastic strip, by direct integration through the thickness."""
    y = np.linspace(-t / 2, t / 2, n)
    s = np.clip(E * kappa * y, -sy, sy)
    return np.trapz(s * y, y), y, s


def test_springback_matches_direct_integration():
    t, sy, E = 1.2, 503.0, 71700.0
    for Ri in (40.0, 58.0, 80.0):
        M, _, _ = _epp_moment(1 / Ri, t, sy, E)
        k_res = 1 / Ri - M / (E * t ** 3 / 12)            # elastic unloading
        assert W.springback_final_radius(Ri, t, sy, E) == pytest.approx(1 / k_res, rel=2e-3)


def test_springback_limits():
    t, sy, E = 1.5, 276.0, 68900.0
    Re = W.elastic_limit_radius(t, sy, E)
    assert Re == pytest.approx(E * t / (2 * sy))
    assert math.isinf(W.springback_final_radius(Re * 1.01, t, sy, E))     # no set above the elastic limit radius
    assert W.springback_final_radius(1.0, t, sy, E) == pytest.approx(1.0, rel=0.02)   # deep plastic: tiny springback
    Ri = W.forming_radius_for(420.0, t, sy, E)
    assert W.springback_final_radius(Ri, t, sy, E) == pytest.approx(420.0, rel=1e-6)


def test_residual_stress_profile_is_self_equilibrated_and_matches_surface_value():
    t, sy, E, Ri = 1.2, 503.0, 71700.0, 58.0
    M, y, s = _epp_moment(1 / Ri, t, sy, E)
    res = s - M * y / (t ** 3 / 12)
    assert abs(np.trapz(res, y)) < 1e-6 * sy * t
    assert abs(np.trapz(res * y, y)) < 1e-6 * sy * t * t
    assert abs(res[-1]) == pytest.approx(W.residual_surface_stress(Ri, t, sy, E), rel=2e-3)


def test_goodman_without_residual_reduces_to_hipbelt_rule():
    sa, su = 192.2, 310.0
    assert W.goodman_smax(sa, su) == pytest.approx(2 * sa / (1 + sa / su), rel=1e-9)
    assert W.goodman_smax(sa, su, sr=100.0) < W.goodman_smax(sa, su)


def test_end_slope_of_the_recorded_arc():
    # hipbelt_structural.md: 14.6 deg end slope <-> R ~ 420 mm over the 105 mm half width
    assert W.end_slope_deg(420.0) == pytest.approx(14.5, abs=0.2)


# ------------------------------------------------------------------------------------------- holes (C-3)
def test_heywood_limits():
    assert W.heywood_kt_net(0.0, 60.0) == pytest.approx(3.0)
    assert W.heywood_kt_net(59.999, 60.0) == pytest.approx(2.0, abs=1e-6)


# ------------------------------------------------------------------------------------------- plates (C-4, C-7)
def test_gridplate_clamp_patch_gives_cantilever_strip():
    """The yoke clamp (w and both slopes held over a patch) on a strip: tip line load, delta = P L^3 / (3 D b)."""
    from huntkit.fea.plate_grid import GridPlate, iso_D
    E, nu, t, L, b, h = 45000.0, 0.3, 1.2, 60.0, 20.0, 2.0
    D = iso_D(E, t, nu)
    pl = GridPlate(-10.0, 0.0, int((L + 10) / h), int(b / h), h, D)
    xy = pl.node_xy()
    cl = np.nonzero(xy[:, 0] <= 1e-6)[0]
    pl.fix_w(cl)
    for n in cl:
        pl.fixed.update((3 * int(n) + 1, 3 * int(n) + 2))
    P = 10.0
    tip = np.nonzero(np.abs(xy[:, 0] - L) < 1e-6)[0]
    f = np.zeros(pl.ndof)
    f[3 * tip] = P / len(tip)
    w = pl.solve(f)["w"]
    Dc = D[0, 0]
    assert w[tip].mean() == pytest.approx(P * L ** 3 / (3 * Dc * b), rel=0.06)


def test_laminate_fi_matches_repo_bending_fi_and_is_linear():
    from huntkit.fea.plate_grid import laminate_bending_fi
    lam = W.yoke_laminate(1.2)
    M = np.array([[3.0, -1.0, 0.5]])
    assert W.laminate_fi(lam, np.zeros(3), M)[0] == pytest.approx(laminate_bending_fi(lam, M)[0], rel=1e-9)
    assert W.laminate_fi(lam, np.zeros(3), 2 * M)[0] == pytest.approx(2 * W.laminate_fi(lam, np.zeros(3), M)[0],
                                                                      rel=1e-9)


def test_yoke_laminate_is_near_isotropic_in_bending():
    lam = W.yoke_laminate(1.5)
    D = lam.D
    assert D[0, 0] / D[1, 1] == pytest.approx(1.0, abs=0.6)
    E_eff = 12 * (1 - 0.3 ** 2) * D[0, 0] / 1.5 ** 3
    assert 30000 < E_eff < 110000


def test_backer_equilibrium_and_contact_logic():
    L = hs.load_sets()
    thick = W.backer_solve(W.Backer("hdpe_sheet", 3.0), L["walk"].H)
    assert thick["F_body"] == pytest.approx(L["walk"].H, rel=2e-3)
    assert thick["F_spine"] == pytest.approx(0.0, abs=1e-6)
    thin = W.backer_solve(W.Backer("hdpe_sheet", 0.8, W.HDPE_CREEP_E_RATIO), L["walk"].H)
    assert thin["w_channel_max"] > thick["w_channel_max"]


# ------------------------------------------------------------------------------------------- results
@pytest.fixture(scope="module")
def c1():
    return W.c1(log=None)


def test_c1_saves_13_g_and_baseline_reproduces_record(c1):
    assert c1["mass_g"]["saved"] == pytest.approx(13.0, abs=0.3)
    assert c1["baseline_record"]["cases"]["C2"]["sf"] == pytest.approx(1.21, abs=0.01)
    assert c1["baseline_record"]["cases"]["walk"]["sf"] == pytest.approx(1.20, abs=0.01)


def test_c1_routes(c1):
    r = c1["routes"]
    assert r["hot_form"]["min_sf"] < 1.0                 # annealed: reject
    assert r["cold_roll_be"]["min_sf"] >= 1.0
    assert r["w_temper"]["min_sf"] >= 1.0
    assert r["bend_1"]["min_sf"] < r["bend_3"]["min_sf"]  # one sharp facet is worse than bump-bending
    # 400 mm hand form gives no permanent set on either plate (R_e 187 / 86 mm)
    assert c1["forming_6061_1.5"]["hand_form_400mm_slope_deg"] == 0.0
    assert c1["forming_7075_1.2"]["outer_strain_pct"] < 0.2 * c1["forming_7075_1.2"]["elong_pct"]
