"""Hipbelt fit / load-transfer model (huntkit.gendesign.hipbelt) and the concept study."""
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import hipbelt as hb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))


def test_anthro_forms_and_cone_sex_difference():
    a = hb.anthro()
    assert a["male"]["n"] == 4082 and a["female"]["n"] == 1986
    # the hip cone is steeper for women (median lateral and circumferential cone angles)
    assert a["female"]["cone_lateral_deg"]["p50"] > a["male"]["cone_lateral_deg"]["p50"] + 4
    assert a["female"]["cone_circ_deg"]["p50"] > a["male"]["cone_circ_deg"]["p50"]
    f = hb.hip_form("male", 34)
    assert 33.5 < f.circ_in < 34.5 and f.n > 100


def test_section_perimeter_matches_circumference():
    for sex, band in (("female", 30), ("male", 34), ("male", 40)):
        f = hb.hip_form(sex, band)
        sec = hb.section(f)
        assert abs(2 * sec.half_perim - f.circ) / f.circ < 0.01
        assert 1.8 < sec.ex < 4.0
        # ASIS on the front half, crest (lateral extreme) near the middle
        assert sec.s_crest < sec.s_asis < sec.half_perim


def test_across_height_force_balance():
    k, h, q = 0.01, 140.0, 3.0
    for delta in (0.0, 0.01, 0.05, -0.05, 0.3):
        u, p = hb._across_height(q, h, k, delta)
        assert np.trapezoid(p, u) == pytest.approx(q, rel=0.03)
        assert (p >= 0).all()
    # a large mismatch loads the lower edge (delta > 0) and lifts the top off
    u, p = hb._across_height(q, h, k, 0.3)
    assert p[-1] > 0 and p[0] == 0


def test_straight_wing_is_flat_and_cone_cut_bows():
    from hipbelt_concepts import B, C0
    f = hb.hip_form("male", 34)
    T0, B0, st0 = hb.wing_flat(C0, f, "M")
    assert hb.flat_sagitta(T0, B0) < 0.5 and st0 < 0.005
    size = B.size_for(f.circ_in)
    T1, B1, st1 = hb.wing_flat(B, f, size)
    bow = hb.flat_sagitta(T1, B1)
    assert 2.0 < bow < 15.0 and st1 < 0.005


def test_capacity_is_linear_in_tension_and_needs_load():
    d = hb.BeltDesign("t", "test")
    f = hb.hip_form("male", 34)
    v0 = hb.evaluate(d, f, 0.0, cg_aft=0.0).V_cap
    assert v0 == pytest.approx(0.0, abs=1e-6)
    v1 = hb.evaluate(d, f, 100.0).V_cap
    v2 = hb.evaluate(d, f, 200.0).V_cap
    v0c = hb.evaluate(d, f, 0.0).V_cap          # lumbar couple alone holds something
    assert v0c > 0
    assert (v2 - v1) == pytest.approx(v1 - v0c, rel=0.02)


def test_tension_for_hold_meets_the_need():
    d = hb.BeltDesign("t", "test")
    f = hb.hip_form("female", 32)
    T = hb.tension_for_hold(d, f)
    v = hb.evaluate(d, f, T, g=hb.WALK_G).V_cap
    need = hb.HIP_SHARE * hb.RATED_KG * hb.G * hb.WALK_G
    assert v == pytest.approx(need, rel=0.01)
    # more friction -> less tension
    assert hb.tension_for_hold(d, f, mu=0.5) < 0.7 * T


def test_recommended_belt_beats_current_on_women_and_clears_asis():
    from hipbelt_concepts import B, C0
    for sex, band in (("female", 30), ("female", 34)):
        f = hb.hip_form(sex, band)
        c0, rb = hb.study(C0, f), hb.study(B, f)
        assert rb["peak_wing_kpa"] < c0["peak_wing_kpa"] - 8
        assert rb["peak_lumbar_kpa"] < c0["peak_lumbar_kpa"]
        assert rb["hold_margin_at_allow"] > c0["hold_margin_at_allow"]
        assert rb["asis_clear_mm"] >= 0


def test_proposed_sizes_cover_more_of_ansur():
    from hipbelt_concepts import SIZES_B
    for sex in ("male", "female"):
        assert hb.coverage(SIZES_B, sex) >= hb.coverage(hb.SIZES_CURRENT, sex)
    assert hb.coverage(SIZES_B, "male") > 0.92


def test_bom_current_matches_panels_yaml():
    """Same-method mass of the current belt body vs panels.yaml H-01..H-09 (163.3 g) within 5 %."""
    import yaml
    from hipbelt_concepts import C0, belt_bom
    panels = yaml.safe_load((ROOT / "designs" / "pack_5200" / "panels.yaml").read_text())["panels"]
    booked = sum(p["mass_g_total"] for p in panels if p["id"] in {f"H-0{i}" for i in range(1, 10)})
    assert belt_bom(C0)["total_g"] == pytest.approx(booked, rel=0.05)


def test_pressure_limit_constant_from_wettenschwiler():
    assert hb.P_HIP_PEAK_KPA == pytest.approx(2.135 * 14 + 18.75, abs=0.1)
    assert math.isclose(hb.ASIS_HALF_MM * 2, 227.0)
