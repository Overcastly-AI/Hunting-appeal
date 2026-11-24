"""BL-068: C' pattern work on CORRIE F rev 3 (P1 level wraps, P2 roll taper, P3 lid locks, RT-PULL)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(PACK), str(PACK / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_geometry as BG  # noqa: E402
import corrie_f as F  # noqa: E402
import patterns_corrie_f_rev3 as PR  # noqa: E402
import strap_tails as ST  # noqa: E402


@pytest.fixture(scope="module")
def rs():
    return PR.build("today", addons=False)


@pytest.fixture(scope="module")
def before():
    import bl068_cprime as X
    with X.state(False, False, False):
        return PR.build("today", addons=False)


# ------------------------------------------------------------------------------------------------ P1 level wraps
def test_p1_geometry_yaml_wraps_level_on_existing_lash_points():
    g = yaml.safe_load((PACK / "geometry.yaml").read_text())
    hp = g["frame"]["hard_points"]
    w = {x["id"]: x for x in g["haul_wraps"]}
    assert BG.W_LEVEL
    for wid, z in (("W1", 250.0), ("W2", 420.0)):
        assert w[wid]["z_R_at_19in"] == w[wid]["z_L_at_19in"] == w[wid]["z_at_19in"] == z
        assert w[wid]["anchor_R"] in hp and w[wid]["anchor_L"] in hp
        assert hp[w[wid]["anchor_R"]][2] == hp[w[wid]["anchor_L"]][2] == z
        assert hp[w[wid]["anchor_R"]][0] == -hp[w[wid]["anchor_L"]][0]         # mirror pair


def test_p1_helix_reproducible(rs):
    import bl068_cprime as X
    h = {w["id"]: w for w in X.helix_wraps()}
    assert (h["W1"]["z_R_at_19in"], h["W1"]["z_L_at_19in"]) == (80.0, 250.0)
    assert (h["W2"]["z_R_at_19in"], h["W2"]["z_L_at_19in"]) == (250.0, 420.0)
    assert h["W1"]["cut_length_mm"] == 1440 and h["W2"]["cut_length_mm"] == 1512     # geometry.yaml before BL-068


def test_p1_keepers_level_and_clearances(rs, before):
    assert rs.geo["kw_z"] == {"W1": {"R": 250.0, "L": 250.0}, "W2": {"R": 420.0, "L": 420.0}}
    assert before.geo["kw_z"]["W1"]["R"] < before.geo["kw_z"]["W1"]["L"]          # the helix climbed R -> L
    wl = rs.geo["bl068"]["w_level"]
    assert wl["ok"]
    assert wl["level"]["min_bow_gap_mm"] == pytest.approx(PR.B11_BOW_Z[0] - PR.B11_H / 2 - 420.0 - 12.5)
    assert wl["level"]["min_bow_gap_mm"] >= PR.RT_CLEAR
    for s in ("R", "L"):
        assert wl["level"][s]["W1_band_to_IMP8_mm"] > 0                            # IMP-8 freed of W1
        assert wl["level"][s]["W1_crosses_FP"]
    assert wl["helix"]["R"]["W1_band_to_IMP8_mm"] < 0                              # it lay on IMP-8 before
    # K-W notches on the gusset aft edge sit at the level heights on both sides
    G = rs.pieces["B-03"]
    labs = [n.label for n in G.notches if "K-W" in n.label]
    assert any("K-W keeper W1 (R only)" in t and "K-W keeper W1 (L only)" in t for t in labs)   # one pattern, both sides
    # DECISION KW-HP-L: level W2 lands on the L aft seam's z 420 hard-point loop: no second loop there
    assert rs.geo["kw_shared"] == [{"wrap": "W2", "side": "L", "z": 420.0, "hard_point_z": 420.0, "offset_mm": 0.0}]
    assert any("hard-point loop (L only)" in t and "W2 runs through this loop" in t for t in labs)
    assert next(w for w in rs.webbing if w["id"] == "K-W")["qty"] == 3


def test_p1_tripod_lower_end_held_no_fallback(rs):
    t = rs.geo["bl068"]["tripod"]
    assert t["lower_end_held_all"] and not t["fallback_needed"]
    # the heavy tripod in the IMP-8 cup is held by the cup, W1 and W2; feet-on-FP placement gained W2 (helix: none)
    assert [n for n, _ in t["rows"]["level tripod_heavy cup"]["holds"]] == ["IMP-8 cup", "W1", "W2"]
    assert not t["rows"]["helix tripod_heavy fp_top"]["lower_end_held"]
    assert t["rows"]["level tripod_heavy fp_top"]["lower_end_held"]


def test_p1_lash_loads_new_point_and_mirror():
    import bl068_cprime as X
    j = X.lash_loads()
    assert j["new_points"] == ["load_wing_lash_z420_R"]
    assert j["status"]["load_wing_lash_z80_R"].startswith("UNLOADED")
    assert "load_wing_lash_z250_L" in j["changed_points"]
    for k in ("load_wing_lash_z420_R", "load_wing_lash_z250_L"):
        a = j["after"][k]
        assert a["rise_deg"] == 0.0                                                # level wraps
        assert abs(sum(v * v for v in a["strap_dir_unit"]) - 1.0) < 1e-3
        assert abs(sum(v * v for v in a["force_design_n"]) ** 0.5 - X.W_DESIGN_N) < 0.5
    assert j["mirror_check"]["load_wing_lash_z420_R"]["is_mirror_image"]           # R z420 mirrors L z420 in plan


# ------------------------------------------------------------------------------------------------ P2 roll taper
def test_p2_collar_tapered_and_matched(rs, before):
    p6f, p6, p7, p7s = (rs.pieces[k] for k in ("B-06f", "B-06", "B-07", "B-07s"))
    for p, q in ((p6f, before.pieces["B-06f"]), (p6, before.pieces["B-06"])):
        assert p.edge_length("bottom") == pytest.approx(q.edge_length("bottom"), abs=0.05)     # collar seam unchanged
        assert q.edge_length("bottom") - p.edge_length("top") == pytest.approx(2 * 70.4, abs=0.2)
        assert p.edge_length("left") == pytest.approx(p.edge_length("right"), abs=0.01)
    assert p6f.edge_length("left") == pytest.approx(p6.edge_length("right"), abs=0.01)         # side seams match
    assert p7.edge_length("bottom") == pytest.approx(2 * F.ROLL_MOUTH_FLAT_MM, abs=0.05)
    assert before.pieces["B-07"].edge_length("bottom") - p7.edge_length("bottom") == pytest.approx(281.7, abs=0.3)
    assert p7s.edge_length("bottom") == pytest.approx(F.ROLL_MOUTH_FLAT_MM - 40.0, abs=0.05)
    o = rs.geo["rt_origin"]
    assert o["layers_at_roll_ends_mm"] == [pytest.approx(F.ROLL_MOUTH_FLAT_MM, abs=0.5)] * 2   # folds flat at the roll ends
    assert o["collar_side_cut_mm"] == pytest.approx(70.4, abs=0.1)


def test_seams_match_and_grain_everywhere(rs):
    rep = PR.seam_report(rs)
    assert len(rep.mismatches) == 0
    full = PR.build("today")
    for p in full.pieces.values():
        g0, g1 = p.grain_arrow()                                                   # every piece carries a grain line
        assert p.grain is not None and g0 != g1, p.piece_id


def test_p2_rtm_tab_cannot_rise_so_rt_is_635(rs):
    rr = rs.geo["bl068"]["rtm_raise"]
    assert not rr["any_ok"]
    for k, v in rr["raised"].items():
        assert "S 15 in" in v["w3_corners_failing"]                               # buckle in W3's sweep (W3-OVER)
    assert rr["raised"]["66"]["rt_cut_mm"] == 565.0                              # the raise would have kept 565
    assert ST.roll_row()["after"]["cut_mm"] == 635.0
    rt = next(w for w in rs.webbing if w["id"] == "RT")
    assert rt["length_mm"] == 635.0
    with F.cprime(roll_taper=False):
        assert ST.roll_row()["after"]["cut_mm"] == 565.0


def test_p2_volume_and_loadout():
    import bl068_cprime as X
    v = X.volume_loadout()
    assert v["mouth_perimeter_mm"]["after"] == pytest.approx(768.0)
    assert v["mouth_perimeter_mm"]["before"] == pytest.approx(4 * 262.45, abs=0.1)
    assert 0.5 < v["collar_loss_L"] < 1.0
    assert v["headline_in_band"]
    assert not v["loadout_fails"]                                                 # every bag item passes the mouth


# ------------------------------------------------------------------------------------------------ P3 lid locks
def test_p3_one_lock_rear_boxed():
    import attach_diet as AD
    a, b = F.crown_kit_straps("M"), F.crown_kit_straps("M", rear="lock")
    assert (a["adjusters"], a["rear"], a["tabs_per_strap"]) == (1, "box", 3)
    assert a["cut_mm"] == pytest.approx(b["cut_mm"] - F.TAIL_GRIP_MM + F.CROWN_REAR_FOLD, abs=0.01)
    llh = F._rec("ladder_lock_25mm_heavy", "mass_g")
    want = 2 * ((a["cut_mm"] + 3 * F.CROWN_TAB) * F.WEB25 / 1000 + AD.TOGGLE_G + llh + a["keepers_per_strap"] * F.TAIL_KEEPER_G)
    assert a["mass_g"] == pytest.approx(want, abs=0.02)
    assert a["keepers_per_strap"] == 1 and a["tail_worst_mm"] > F.KEEPER_OVER_MM
    assert a["tail_used_mm"] == pytest.approx(F.TAIL_GRIP_MM + a["path_max_mm"] + F.CROWN_SPARE_MM - a["path_used_mm"],
                                              abs=0.1)


def test_p3_pattern_and_hardware(rs):
    b28 = rs.pieces["B-28"]
    boxes = [ln for ln in b28.internal_lines if "rear end on B-28t" in (ln.label or "")]
    assert boxes, "rear-end box drawn on B-28"
    assert rs.pieces["K-28"].quantity == 2
    ll = next(h for h in rs.hardware if h["material_id"] == "ladder_lock_25mm_heavy")
    assert ll["qty"] == 7 and "B-28 (2)" in ll["item"]


# ------------------------------------------------------------------------------------------------ mfg + kit
@pytest.fixture(scope="module")
def pk():
    import mfg_corrie_f_rev3 as M
    return M.package()


def test_mfg_check_min_sf_no_holds(pk):
    import mfg_corrie_f_rev3 as M
    c = M.checks(pk)
    assert c["min_sf"] >= 1.36 and not c["holds"] and not c["box_mismatches"] and not c["unsequenced"]
    rows = {r["point"]: r for r in pk["load_points"]}
    front = next(v for k, v in rows.items() if k.startswith("crown strap front lock tab"))
    rear = next(v for k, v in rows.items() if k.startswith("crown strap rear end on its tab"))
    assert rear["sf"] == front["sf"] and rear["load_n"] == front["load_n"] == M.GUY_N
    assert rear["hardware"].startswith("none") and "LL-H" in rear["proof"]
    assert not any("B-28 (new piece)" in k for k in rows)
    rt = [v for k, v in rows.items() if k.startswith("roll-top clip")]
    assert rt and all(v["sf"] >= 2.0 and "RT-PULL 338 N" in v["proof"] for v in rt)


def test_rt_pull_in_register_and_kit(pk):
    import physical_test_kit as K
    reg = {r["id"]: r for r in K.new_rows(K.release_levels(), K.lid_mass_g(), K.crown_cut_mm())}
    r = reg["RT-PULL"]
    assert "338 N" in r["title"] and "34.4 kg" in r["steps"] and r["status"] == "ACTIVE"
    assert K.TEST_RELEASE["RT-PULL"] == "BAG-CUT"
    assert any("RT-PULL" in g["tests"] for g in K.GROUPS)
    rel = {t["id"]: t for t in pk["tests"]}
    assert "RT-PULL" in rel


def test_bl068_record_written():
    j = json.loads((PACK / "analysis" / "bl068_cprime.json").read_text())
    assert j["seams"]["mismatches_1mm"] == 0 and not j["grain_missing"]
    led = j["ledger"]
    assert led["alone"]["P3"]["adopted_bag_g"]["base"] == 0.0 and led["alone"]["P3"]["adopted_bag_g"]["as_hunted"] < -14.0
    assert led["alone"]["P2"]["adopted_bag_g"]["base"] < -10.0
    lash = json.loads((PACK / "analysis" / "bl068_lash_loads.json").read_text())
    assert lash["new_points"] == ["load_wing_lash_z420_R"]


def test_before_state_reproduces_the_bl067_ledger():
    """state(0, 0, 0) is rev 3 as released before BL-068: the BL-067 ledger basis (proven now 4038.1 g, after tests
    3450.9 g, belt M, crown kit M; iter1_weight)."""
    import bl068_cprime as X
    s = X._run_state((0, 0, 0))
    assert s["iter1_g"]["P_base"] == pytest.approx(4038.1, abs=0.05)
    assert s["iter1_g"]["A_base"] == pytest.approx(3450.9, abs=0.05)
    assert s["w_cuts_mm"] == {"W1": 750.0, "W2": 822.0, "W3": 986.6} and s["rt_cut_mm"] == 565.0
    assert s["b28"]["adjusters"] == 2 and s["b28"]["cut_mm"] == pytest.approx(1006.9, abs=0.05)
