"""BL-005 back-system integration: solver verification and result checks (fast; no full spreader runs)."""
import math

import numpy as np
import pytest

from huntkit.gendesign import back_rail as BR
from huntkit.gendesign import back_system2 as B
from huntkit.gendesign import spreader as S


# ------------------------------------------------------------------ solver verification
def test_section2_reproduces_spreader_rail_backed():
    """Shear-rigid strip: identical to the released model (spreader.rail_backed via back_rail.section)."""
    r = BR.released()
    for q in (0.5, 1.33, 2.5):
        a = BR.section(r, q)
        b = B.section2(q, BR.backer_D(r), math.inf, B.foam_layers(10.0), half=60.0, strip_w=80.0)
        assert b["peak_kpa"] == pytest.approx(a["peak_kpa"], rel=1e-6)
        assert b["indent_mm"] == pytest.approx(a["indent_mm"], rel=1e-6)


def test_section2_equilibrium():
    """Contact pressure integrates to the stay line load."""
    s = B.section2(1.5, 5000.0, math.inf, B.foam_layers(10.0), half=60.0, strip_w=80.0)
    x = np.asarray(s["x"])
    trap = getattr(np, "trapezoid", None) or np.trapz
    assert trap(np.asarray(s["p_kpa"]) / 1000.0, x) == pytest.approx(1.5, rel=0.02)


def test_timoshenko_cantilever_closed_form():
    """The strip element used in section2: tip deflection P L^3 / 3D + P L / S (Timoshenko cantilever)."""
    D, Sh, L, P, n = 5.0e4, 300.0, 40.0, 2.0, 20
    le = L / n
    phi = 12 * D / (Sh * le ** 2)
    c = D / (le ** 3 * (1 + phi))
    k = c * np.array([[12, 6 * le, -12, 6 * le], [6 * le, (4 + phi) * le ** 2, -6 * le, (2 - phi) * le ** 2],
                      [-12, -6 * le, 12, -6 * le], [6 * le, (2 - phi) * le ** 2, -6 * le, (4 + phi) * le ** 2]])
    K = np.zeros((2 * n + 2, 2 * n + 2))
    for e in range(n):
        K[2 * e:2 * e + 4, 2 * e:2 * e + 4] += k
    f = np.zeros(2 * n + 2)
    f[-2] = P
    u = np.linalg.solve(K[2:, 2:], f[2:])
    assert u[-2] == pytest.approx(P * L ** 3 / (3 * D) + P * L / Sh, rel=1e-9)


def test_sandwich_strip_stiffer_and_lighter_than_twill():
    tw, sw = B.TODAY_BACKER, B.backer_by_key("swR71c3_70")
    assert sw.D() > 10 * tw.D()
    assert sw.mass_pair_g() < 0.6 * tw.mass_pair_g()
    # the sandwich D is the skins' parallel-axis term to within the core and ply-own terms
    Ef = 58000.0
    d = 3.0 + 0.22
    assert sw.D() == pytest.approx(Ef * 0.22 * d ** 2 / 2, rel=0.08)


def test_framesheet_equilibrium_and_rigid_limit():
    """Without a bone the foundation carries exactly the sheet's share of the meat force (cinch self-equilibrated)."""
    fs = B.Framesheet("t", core_t=7.0, h=5.0)
    r = B.framesheet_solve(fs, "walk", None, n_sec=4)
    share = BR.meat_force_n(B.E_REVC, 1.6) * (fs.z_hi - fs.z_lo) / 420.0
    assert r["reaction_n"] == pytest.approx(share, rel=1e-3)


# ------------------------------------------------------------------ reproduction and results
def test_today_skin_reproduced_within_2pct():
    side = B.bone_side_n()
    assert side == pytest.approx(203.6, rel=0.02)
    s = B.skin(B.TODAY, B.E_REVC, side)
    assert s["peak_kpa"] == pytest.approx(13.8, rel=0.02)


def test_today_full_check_reproduced_within_2pct():
    tf = B.today_full()
    assert tf["sf_fatigue"] == pytest.approx(1.09, rel=0.02)
    assert tf["sf_fpf"] == pytest.approx(1.25, rel=0.02)
    assert tf["skin_peak_kpa"] == pytest.approx(13.8, rel=0.02)


def test_ledger_split_adds_up():
    led = B.ledger_layers()
    assert led["panel_split_sum"] == pytest.approx(led["panel_g"], abs=0.2)
    assert sum(led["spreader_split"].values()) == pytest.approx(led["spreader_g"], abs=0.2)
    assert led["back_total_g"] == pytest.approx(led["panel_g"] + led["spreader_g"], abs=0.05)


def test_a1_bag_side_extension_does_not_back_the_rail():
    side = B.bone_side_n()
    v = next(v for v in B.rail_variants() if v.key == "a1_wide_bagside")
    assert B.skin(v, B.E_REVC, side)["peak_kpa"] > 25.0


def test_recommended_sandwich_strip_passes_and_saves():
    side = B.bone_side_n()
    tf = B.today_full()
    t0 = {"walk": B.skin(B.TODAY, B.E_REVC, side), "fact": B.skin(B.TODAY, B.E_REVC, side, "factored")}
    v = next(v for v in B.rail_variants() if v.key == B.RECOMMENDED)
    r = B.evaluate_rail(v, side, tf, t0)
    assert r["passes"]
    assert r["peak_kpa"] <= 13.8
    assert min(r["backer_sf_fpf"], r["backer_sf_fatigue"]) >= 1.0
    assert r["mass_delta"]["total"] < -35.0
    # target honestly not met: 320 g needs far more than the backer strip offers
    assert B.ledger_layers()["back_total_g"] + r["mass_delta"]["total"] > B.TARGET_G


def test_thin_twill_fails_strength():
    side = B.bone_side_n()
    v = next(v for v in B.rail_variants() if v.key == "b_tw051_80")
    r = B.evaluate_rail(v, side, B.today_full())
    assert not r["passes"]
