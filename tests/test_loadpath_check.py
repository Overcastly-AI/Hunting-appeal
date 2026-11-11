"""BL-010 load-path verification: solver reproduction, loads re-derived, verdict logic, fixes and masses."""
import math

import pytest

from huntkit.gendesign import loadpath_check as LP
from huntkit.materials import load


@pytest.fixture(scope="module")
def res():
    return LP.compute(fea_live=False, log=None)


def test_hook_records_load_with_ratings():
    g = load("g_hook_25mm_aluminium")
    c = load("carabiner_wiregate_22kn")
    assert g.require("no_set_load_n") == 900 and g.require("breaking_strength_n") == 1200 and g.require("mass_g") == 8
    assert c.require("breaking_strength_n") == 21000 and c.require("minor_axis_strength_n") == 8000
    assert c.require("mass_g") == 22


def test_every_table_row_has_a_verdict(res):
    ids = [r["id"] for r in res["rows"]]
    # strap_architecture.md 7: 12 rows; attachment_diet.md 5: 5 rows; hipbelt_diet.md 5: 4 rows
    assert sum(i.startswith("S") for i in ids) == 12
    assert sum(i.startswith("A") and i != "A1-CF" for i in ids) == 5
    assert "A1-CF" in ids                         # additive BL-011 follow-up row
    assert sum(i.startswith("H") for i in ids) == 4
    for r in res["rows"]:
        assert r["verdict"].startswith(("PASS", "FAIL"))
        if r["verdict"] == "FAIL":
            assert "fix" in r and r["fix"]["after_verdict"].startswith("PASS")


def test_factored_loads_rederived(res):
    b = res["beam"]
    assert b["im3_meat"]["n"] == pytest.approx(605.0, abs=0.5)
    assert b["im1_meat"]["n"] == pytest.approx(273.0, abs=0.5)
    s = res["sim"]
    assert s["im3_M_notop_CORRIE"]["factored"] == pytest.approx(1702.2, abs=0.5)
    assert s["guy_REC_CORRIE"]["factored"] == pytest.approx(244.5, abs=0.5)
    assert res["float"]["us1_limit_n"] == pytest.approx(720.0, abs=2.0)
    assert res["belt"]["T_c2"] == pytest.approx(1000.0, abs=1.0)


def test_rec_bag_share_moves_from_im2_to_im3(res):
    # IM2 bag hooks deleted: IM2 governed by the meat strap only; IM3 bag cases rise but stay below the meat case
    assert res["beam"]["im2_bag"]["n"] == pytest.approx(511.9, abs=0.5)
    assert "im2_bag" not in res["beam_rec"]
    assert res["beam"]["im3_bag"]["n"] < res["beam_rec"]["im3_bag"]["n"] < res["beam_rec"]["im3_meat"]["n"]


def test_verdict_logic():
    ok = LP._chk("a", 100, 150, "strength", "r")
    assumed = LP._chk("b", 100, 120, "proof", "x", False, "T-1")
    bad = LP._chk("c", 100, 90, "proof", "r")
    assert LP.verdict([ok])["verdict"] == "PASS"
    assert LP.verdict([ok, assumed])["verdict"] == "PASS after T-1"
    v = LP.verdict([ok, assumed, bad])
    assert v["verdict"] == "FAIL" and v["governs"] == "c" and v["min"] == pytest.approx(0.9)


def test_open_items(res):
    rows = {r["id"]: r for r in res["rows"]}
    # meat-strap hook: 25 mm G-hook fails only the IM3 910 N proof, by 1 %
    assert rows["S2"]["verdict"] == "FAIL" and rows["S2"]["min"] == pytest.approx(900 / 907.5, abs=1e-3)
    # IM3 bag hook: 2200 N spec fails the 2553 N proof; the carabiner passes it
    a1 = rows["A1"]
    hook = next(c for c in a1["checks"] if c["item"].startswith("hook 2200"))
    assert hook["demand_n"] == pytest.approx(2553, abs=1) and hook["ratio"] < 1
    cp = next(c for c in a1["fix"]["checks"] if c["item"].startswith("carabiner proof"))
    assert cp["ratio"] > 1.5
    # W1-W3: unrated hook fails, fix passes
    assert rows["S9"]["verdict"] == "FAIL" and rows["S9"]["fix"]["after_min"] > 1.4


def test_im3_fairlead_fatigue_and_fix(res):
    rows = {r["id"]: r for r in res["rows"]}
    a1 = rows["A1"]
    fat = next(c for c in a1["checks"] if "fatigue" in c["item"] and "fairlead" in c["item"])
    assert fat["ratio"] == pytest.approx(0.80, abs=0.01)
    fat2 = next(c for c in a1["fix"]["checks"] if "fatigue" in c["item"])
    assert 1.0 <= fat2["ratio"] < 1.1
    # body fatigue per torso, restated
    assert res["body"]["h1_per_torso"]["fatigue"] == pytest.approx(1.150, abs=1e-3)
    assert res["body"]["rec_per_torso"]["fatigue"] >= 1.0


def test_masses(res):
    m = res["mass"]
    assert m["fix_g"]["BL-003"] == pytest.approx(35.0)          # 14 (IM3 free end) + 12 (hooks) + 9 (heavy locks)
    assert m["fix_g"]["BL-004"] == pytest.approx(16.0 + 2 * (9.53 - 6.13104), abs=0.01)   # A1 + A1-CF cheek
    assert m["fix_g"]["BL-006"] == 0.0
    assert m["meat_trip_kit_g"] == pytest.approx(16.0)
    assert res["booked"]["bag_hook_g"] == pytest.approx(14.0) and res["booked"]["w_hook_g"] == pytest.approx(4.0)


def test_front_pad_meets_limit(res):
    fp = res["front_pad"]
    assert fp["p_with_pad"]["worst"] <= fp["limit_kpa"]
    assert 10.0 < fp["g_each"] < 40.0


def test_fairlead_reproduces_released_record():
    r = LP.fairlead_im3(9.0)
    assert r["fi99"] == pytest.approx(LP.FROZEN["fairlead_record_fi99_1415"], rel=1e-6)
    r2 = LP.fairlead_im3(12.5)
    assert r2["fi99"] == pytest.approx(LP.FROZEN["fairlead_im3"][12.5]["fi99"], rel=2e-3)
    assert math.isclose(r2["added_g"], LP.FROZEN["fairlead_im3"][12.5]["added_g"], rel_tol=1e-2)
    r3 = LP.fairlead_im3(13.5)              # A1-CF chosen cheek, 27 mm
    assert r3["fi99"] == pytest.approx(LP.FROZEN["fairlead_im3"][13.5]["fi99"], rel=2e-3)


def test_a1_cf_per_torso_cheek(res):
    r = next(x for x in res["rows"] if x["id"] == "A1-CF")
    cf = res["corrie_f"]
    assert {int(k) for k in cf} == {15, 19, 23}
    assert cf[15 if 15 in cf else "15"]["n_1g"] == pytest.approx(552.4, abs=0.1)
    # the A1 25 mm cheek fails at 15 in on CORRIE F (coordinator's pro-rata 0.94)
    assert r["verdict"] == "FAIL" and r["min"] == pytest.approx(0.944, abs=0.005)
    ch = r["sizing"]["chosen"]
    assert ch["height_mm"] == 27.0 and ch["cheek"] == 8.0
    assert min(ch["fatigue"].values()) >= 1.0 and ch["strength"] >= 1.5
    # every lighter candidate fails one of the two rules
    for v in r["sizing"]["rows"]:
        if v["added_g"] < ch["added_g"]:
            assert not v["ok"]
    assert r["fix"]["mass_g"] == pytest.approx(2 * (9.53 - 8.80), abs=1e-6)
    clr = r["clearance"]
    assert clr["spreader_ok"] and clr["gap_mm"] == pytest.approx(76.5)
    assert r["fix"]["after_verdict"].startswith("PASS")
