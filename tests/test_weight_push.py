"""BL-037 weight push (designs/pack_5200/weight_push.py): lever list, picks, roll-up step, and the honest answer."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "designs" / "pack_5200", ROOT / "designs" / "pack_5200" / "concepts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import weight_push as WP  # noqa: E402
import weight_rollup_v2 as W  # noqa: E402
from huntkit.materials import load  # noqa: E402


@pytest.fixture(scope="module")
def lv():
    return WP.levers("M", WP.ca1_check())


def test_baseline_is_rollup_after_tests_without_bl037():
    """The 'before' pack is the roll-up's after-tests base minus exactly this ticket's step."""
    st = W.step_deltas("M")
    a = W.scenario_table("M")["A"]["base"]
    assert WP.baseline_total("M") == pytest.approx(a - st[WP.STEP]["base"], abs=0.2)
    assert 3200 < WP.baseline_total("M") < 3420          # BL-049 +90.8 g (lug arms, hinge, Ti pins), BL-047 -6.7 g now
    #                                                      in the roll-up; BL-046 +35.9 g; 3211.4 g before BL-037 (BL-036 result); BL-041 +11.2 g; BL-042/045 H1F +50.4 g, BL-043 +2.9 g, BL-044 rows


def test_rollup_step_equals_picks(lv):
    """The A_bl037 rows are the picks, gram for gram, all base, all class A (proven now unchanged)."""
    assert W.STEP_META[WP.STEP][0] == "A"
    rows = W.steps("M")[WP.STEP]
    assert all(r["cfg"] == "base" and r["step"] == WP.STEP for r in rows)
    assert sum(r["g"] for r in rows) == pytest.approx(sum(x["g"] for x in WP.picks(lv)), abs=0.3)
    assert WP.STEP not in {r["step"] for r in W.scenario_rows("P")}


def test_j_strap_reproduces_booking():
    """The J-strap breakdown from the records reproduces geometry.yaml's harness_J soft goods (91.0 g)."""
    j = WP.j_strap_breakdown()
    assert j["total_g"] == pytest.approx(j["booked_g"], abs=0.6)
    rho = load("xlpe_foam_l200").require("density_kg_m3") / load("eva_foam_45c").require("density_kg_m3")
    assert j["delta_g"] == pytest.approx(-j["load_foam_eva_g"] * (1 - rho), abs=0.01)
    assert -23.0 < j["delta_g"] < -21.5


def test_belt_picks_pass_the_fit_model():
    """B-1/B-2/B-3 in one combined run: worst wing and hold no worse than belt B, lumbar under the 48.6 kPa watch."""
    b = WP.belt_check()
    p, lim = b["package + BL-037"], b["limits"]
    assert b["passes"]
    assert p["worst_wing_kpa"] <= lim["worst_wing_kpa"] + 1e-9 and p["worst_hold"] >= lim["worst_hold"] - 1e-9
    assert p["worst_lumbar_kpa"] <= lim["lumbar_watch_kpa"]
    bi = WP.belt_items()
    assert bi["d2"] + bi["d4"] == pytest.approx(-31.9, abs=0.2)          # the BL-006 'belt-foam reserve'


def test_record_based_levers():
    st = WP.sternum()
    assert st["delta_g"] == pytest.approx(load("buckle_side_release_25mm").require("mass_g")
                                          - load("fidlock_magnetic_buckle_25mm").require("mass_g"))
    assert st["side_release_break_n"] >= st["fidlock_break_n"]          # no strength lost on the sternum
    ds = WP.door_sliders()
    assert ds["delta_g"] == pytest.approx(2 * (WP.SLIDER_CORD_G - load("slider_10").require("mass_g")))
    cm = WP.camo_swap()
    assert 0.5 < cm["factor"] < 0.6 and cm["delta_g"] < -20
    assert "SH-01b kick bands" in cm["kept_630d"]
    assert WP.back_strip()["delta_g"] == pytest.approx(-5.4, abs=0.2)
    assert WP.bushings()["delta_g"] == pytest.approx(-4.0, abs=0.1)


def test_spreader_share_is_not_22_g():
    """BL-027's '22 g could come back off' fails on its own data: the fill hipbelt-off set (no cinch) puts the
    H1-G0.55 mid bar below 1.0 whatever the spreader does, so at most the upper-branch growth is a lever."""
    sp = WP.spreader_share()
    assert sp["worst_mid_bar"]["margin_via_stays"] < 1.0
    assert "S_fill" in sp["worst_mid_bar"]["set"]
    assert -sp["upper_only_saving_g"] < sp["members_added_g"]
    assert sp["branch_growth_g"] + sp["mid_growth_g"] == pytest.approx(sp["members_added_g"], abs=2.5)


def test_ca1_lever_record():
    """F-1 as run (results kept in the json): fatigue scales with the ratio; Euler buckling does not and fails."""
    res = json.loads(WP.RESULT.read_text())
    c = res["ca1"]
    assert c["available"]
    for b, v in c["bases"].items():
        assert v["fatigue_040"] == pytest.approx(v["fatigue_030"] * 0.40 / 0.30, abs=0.002)
    assert c["buckling_min"] < 1.0 and not c["passes_buckling"]
    f1 = next(x for x in res["levers"] if x["key"] == "F-1")
    assert f1["status"] == "option"                                      # never picked while it fails buckling


def test_honest_answer(lv):
    """The ticket's 220 g is not met by picks; the report says so and keeps the frozen features out of the route."""
    sm = WP.summary(lv)
    assert not sm["met"] and -sm["picks_g"] < WP.TICKET_G
    assert sm["after_g"] == pytest.approx(sm["before_g"] + sm["picks_g"], abs=0.1)
    assert sm["after_g"] > W.TARGET_G
    frozen = [x["key"] for x in lv if "owner-frozen" in x["owner"] and x["status"] == "owner"]
    assert set(frozen) == {"O-IMP-8", "O-US-"}
    assert not set(frozen) & set(sm["owner_route_take"])
    assert not any("owner-frozen" in c["owner"] for c in sm["closers"])
    assert all(x["risk"] in ("low", "medium") for x in WP.picks(lv))   # no high-risk item is picked
    assert sm["cheek_risk_g"] > 0


def test_every_pick_has_gate_check_and_source(lv):
    for x in WP.picks(lv):
        assert x["gate"] and x["gate"] != "-", x["key"]
        assert x["check"] and x["source"], x["key"]
        assert x["g"] < 0, x["key"]


def test_leader_table_ranks_frame_structure_worst():
    sy = WP.system_table()
    g = sy["groups"]
    assert g["frame_side"] + g["bag_side"] + g["unsplit"] == pytest.approx(sy["total_base_g"], abs=0.5)
    assert sy["ranked_vs_lightest"][0]["function"].startswith("frame structure")
    bag = next(f for f in sy["functions"] if f["leader"].startswith("Exo K4 5000"))
    assert bag["ratio"] < 1.0               # after tests the bag side is lighter than the leaders' bags (BL-008 split)
    fs = [f for f in sy["functions"] if f["ours_key"] == "frame_side"]
    assert all(f["ratio"] > 1.5 for f in fs)                            # the gap is on the frame side


def test_rollup_no_longer_counts_the_belt_foam_reserve_twice():
    """BL-006 d2 + d4 are booked in A_bl037, so the roll-up's feature section must not offer them again."""
    fc = W.feature_costs("M")
    assert fc["reserve_booked_bl037"] and fc["belt_foam_reserve_g"] == 0.0


def test_ca1_sizing_recorded():
    """One member re-growth step on the F-1 body is kept in the json: lighter than the adopted body, still < 1.0."""
    c = json.loads(WP.RESULT.read_text())["ca1"]
    sz = c["sizing"]
    assert sz and all(-25.0 < s["delta_g"] < 0 for s in sz)
    assert not any(s["passes_buckling_fine_sm8"] for s in sz)
