"""BL-080 metal-stay frame concepts: fatigue formula, model surgery, mass/cost booking, ranking, record."""
import json
import math

import pytest

from huntkit.gendesign import bl080_metal_frame as B


def test_fatigue_allow_6061_closed_form():
    # Basquin 0.9 Su @1e3 -> Se @5e8 (S-basis Su 290, Se 96.5 x 290/310), Goodman on the notched mean, R 0
    from huntkit.fea.fatigue import basquin
    su, se = 290.0, 96.5 * 290 / 310
    s = float(basquin(su, se, Ne=5e8).stress_amplitude(1e5))
    assert B.metal_fatigue_allow("alu_6061_t6", 2.0) == pytest.approx(2 * s / (2 * (1 + s / su)), rel=1e-9)
    assert 95 < B.metal_fatigue_allow("alu_6061_t6", 2.0) < 115
    assert B.metal_fatigue_allow("alu_6061_t6", 3.0) < B.metal_fatigue_allow("alu_6061_t6", 2.0)
    assert B.metal_fatigue_allow("alu_7075_t6", 2.0) > 1.6 * B.metal_fatigue_allow("alu_6061_t6", 2.0)


def test_stock_geometry_and_bolts():
    a = B.section_area("t875_049")
    assert a == pytest.approx(math.pi * (22.225 ** 2 - (22.225 - 2 * 1.2446) ** 2) / 4, rel=1e-6)
    # Speedy lists 0.0125 lb/in for 7/8 x .049: 0.2232 g/mm
    assert a * B.RHO["alu_6061_t6"] == pytest.approx(0.0125 * 453.6 / 25.4, rel=0.03)
    assert 6.0 < B._bolt_g(5, 30) < 9.5
    # 7/8 x .049 bore takes the OD 16 crown leg with >= 1.5 mm bushing wall
    s = B.STOCK["t875_049"]
    assert (s["od"] - 2 * s["t"] - 16.0) / 2 >= 1.5


def test_model_surgery_materials():
    c = {**B.CONCEPTS["D"], "stay": "t875_049", "ubar": "t1000_049"}
    m = B.build_model(c, 19.0)
    mats = {mm["group"]: B._mid(mm["material"]) for mm in m["members"]}
    assert mats["stay_upper_L"] == "alu_6061_t6" and mats["upper_bar"] == "alu_6061_t6"
    assert mats["crown_leg_L"] is None          # crown carries over (composite section from frame.yaml)
    cb = {**B.CONCEPTS["B"], "stay": "t875_049", "ubar": "t1000_049"}
    mb = B.build_model(cb, 19.0)
    assert any(mm["group"] == "lumbar_cross_tube" for mm in mb["members"])
    soft = [mm for mm in mb["members"] if mm["group"] == "lumbar_plate"]
    assert soft and all(mm.get("no_kg") for mm in soft)


def test_single_case_runs_and_reports_metal_sf():
    from huntkit.fea.load_standard import ls1_cases
    c = {**B.CONCEPTS["D"], "stay": "t875_049", "ubar": "t1000_049"}
    m = B.build_model(c, 19.0)
    case = [x for x in ls1_cases() if x.name == "static_carry"][0]
    r = case.run(m)
    stays = [mm for mm in r.members if mm["group"].startswith("stay")]
    assert stays and all(math.isfinite(mm["sf"]) and mm["sf"] > 1.0 for mm in stays)
    jf = B._joint_forces(r, m)
    assert jf["hub_L_force_n"] > 100 and jf["upper_bar_L_shear_n"] >= 0


def test_mass_and_cost_booking():
    c = {**B.CONCEPTS["D"], "stay": "t875_049", "ubar": "t1000_049"}
    mass = B.mass_table("D", c)
    assert mass["body_g"] == pytest.approx(sum(mass["rows"].values()), abs=0.6)
    assert mass["body_g"] < B.H1["body_g"]
    cost = B.cost_table("D", c, mass)
    assert cost["per_frame_usd"] == pytest.approx(sum(l["usd"] for l in cost["lines"]), abs=0.05)


def test_rank_orders_strong_then_cap_then_mass():
    con = {
        "X": {"strong_pass": False, "checks": {"min_margin": 0.5}, "cost": {"within_cap": True, "per_frame_usd": 90},
              "mass": {"body_g": 500}},
        "Y": {"strong_pass": True, "checks": {"min_margin": 1.1}, "cost": {"within_cap": False, "per_frame_usd": 160},
              "mass": {"body_g": 700}},
        "Z": {"strong_pass": True, "checks": {"min_margin": 1.2}, "cost": {"within_cap": True, "per_frame_usd": 140},
              "mass": {"body_g": 900}},
    }
    assert [d["concept"] for d in B.rank(con)] == ["Z", "Y", "X"]


def test_record_is_consistent():
    if not B.REC_JSON.exists():
        pytest.skip("run python -m huntkit.gendesign.bl080_metal_frame run first")
    rec = json.loads(B.REC_JSON.read_text())
    assert set(rec["concepts"]) == {"A", "B", "C", "D"}
    pick = rec["pick"]
    e = rec["concepts"][pick]
    assert e["strong_pass"] and e["cost"]["within_cap"]
    assert e["mass"]["body_g"] < B.H1C["body_g"]
    assert rec["ranking"][0]["concept"] == pick
    for k, e in rec["concepts"].items():
        assert e["strong_pass"] == (e["checks"]["min_margin"] >= 1.0)
