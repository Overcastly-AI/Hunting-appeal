"""BL-030: CORRIE F rev 3 is the design of record (module default, ledger's adopted bag, roll-up), the B-28 crown strap
diet (20 mm, cut from the rolled top) and the lid-hold paper check.

    python -m pytest -q tests/test_corrie_f_adopt_rev3.py
"""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(CONCEPTS / "corrie_f_sim"), str(ROOT / "designs" / "pack_5200")):
    if p not in sys.path:
        sys.path.insert(0, p)

import corrie_f as F  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402


def _need_paths():
    if not (F.CROWN_PATHS.exists() and F.CROWN_ROLLED.exists()):
        pytest.skip("crown path files missing: corrie_f.py --bl029 and python -m huntkit.viz3d.corrie_f --crown-paths")


# ------------------------------------------------------------------------------------------- default everywhere
def test_rev3_is_the_default_and_revs_0_to_2_stay_reproducible():
    assert F.REVISION == 3 and F.REVS[3]["crown_lid"] and F.REVS[3]["guy_port"]
    assert F.sim_rev() == 1 and F.sim_rev(0) == 0                 # stored runs: revs 1-3 share the F_r1 shell
    for n in (0, 1, 2):
        with F.revision(n):
            a = F.addons()
            assert "top_pouch" in a and "crown_lid" not in a
            assert F.crown_strap_w() == 25.0
    assert F.REVISION == 3 and F.GUY_X == 52.0 and F.TOP_SETBACK_MM == 30.0


def test_ledger_names_rev3_as_the_adopted_bag_and_books_it():
    _need_paths()
    assert L.ADOPTED_BAG["revision"] == 3 and L.ADOPTED_BAG["door"] == "D2"
    rows = L.adopted_bag_rows("M")
    names = [r["name"] for r in rows]
    assert not any("top_pouch" in n for n in names)
    lid = [r for r in rows if "crown_lid" in r["name"]]
    cs = [r for r in rows if "crown_straps" in r["name"]]
    assert len(lid) == 1 and len(cs) == 1 and lid[0]["cfg"] == cs[0]["cfg"] == "as_hunted"
    assert any(r["name"].startswith("BL-028 rev 2: B-27") and r["cfg"] == "base" for r in rows)
    # BL-031: the adopted B-28 is 25 mm, cut for crown kit M (BL-030's 20 mm diet is history)
    assert cs[0]["g"] == pytest.approx(F.crown_kit_straps("M")["mass_g"], abs=0.01)
    assert sum(r["g"] for r in rows) == pytest.approx(sum(r["g"] for r in F.parts("M")), abs=0.01)


def test_rollup_books_the_ledger_revision():
    import weight_rollup_v2 as W
    assert W.CORRIE_F_REV == L.ADOPTED_BAG["revision"]
    rows = [{"system": "straps_compression", "cfg": "as_hunted", "name": "add-on crown_straps: B-28", "g": 10.0},
            {"system": "pouch", "cfg": "as_hunted", "name": "add-on crown_lid: B-29", "g": 40.0}]
    assert W._item(rows, "pouch") == 50.0                         # the leaders' 'lid in' basis takes lid + straps


# ------------------------------------------------------------------------------------------- crown strap diet
def test_cut_covers_the_longest_rolled_path_at_15in_plus_tail_and_loop():
    _need_paths()
    d = F.crown_strap_diet()
    rp = json.loads(F.CROWN_ROLLED.read_text())["states"]
    longest = max(max(s["length_mm"] for s in v["straps"].values()) for v in rp.values())
    shortest = min(min(s["length_mm"] for s in v["straps"].values()) for v in rp.values())
    assert d["torso"]["d15_max_mm"] > 0 > d["torso"]["d23_min_mm"]          # the bar is lowest at 15 in
    assert d["path_max_mm"] == pytest.approx(longest + d["torso"]["d15_max_mm"], abs=0.1)
    assert d["path_min_mm"] == pytest.approx(shortest + d["torso"]["d23_min_mm"], abs=0.1)
    assert d["cut_mm"] == pytest.approx(d["path_max_mm"] + F.CROWN_TAIL + F.CROWN_LOOP, abs=0.1)
    assert d["tail_at_shortest_mm"] == pytest.approx(d["cut_mm"] - F.CROWN_LOOP - d["path_min_mm"], abs=0.1)
    # the rolled 6-day path is the ~505 mm the ticket names; the standing-collar full top is longer
    assert 470.0 < d["rolled_19in_mm"]["sixday"] < 540.0 < d["rolled_19in_mm"]["full"]


def test_20mm_straps_are_lighter_by_the_target_and_rated_for_the_loads():
    _need_paths()
    d = F.crown_strap_diet()
    w20, w25 = d["options"]["w20"], d["options"]["w25"]
    # BL-029's pair, reproduced by crown_straps(25): 67.46 g on the 3.0 g toggle ASSUMPTION; BL-034 books the pom_toggle
    # record (1.7 g), so the history pair is 2 x 1.3 g lighter
    from huntkit.gendesign import attach_system as AS
    assert d["bl029_g"] == pytest.approx(67.46 - 2 * (3.0 - AS.TOGGLE_G), abs=0.05)
    assert -25.0 <= w20["delta_vs_bl029_g"] <= -15.0              # ticket target
    assert w20["delta_vs_bl029_g"] < w25["delta_vs_bl029_g"]
    # mass: records x cut, no hand-typed total
    web = 2 * w20["cut_mm"] * F.WEB20_GM / 1000.0
    hw = 2 * (w20["toggle_g"] + F.LL20["mass_g"] + 60.0 * F.WEB20_GM / 1000.0 + 60.0 * F.WEB25 / 1000.0)
    assert w20["mass_g"] == pytest.approx(web + hw, abs=0.02)
    # ratings: the 288 N factored guy envelope governs (3.0 x 96 N); 20 mm lock tensile is the cited 65 kg
    assert d["demand_n"] == pytest.approx(3.0 * 96.0) and d["demand_n"] >= d["loads"]["hand_cinch_n"]
    assert F.LL20["tensile_n"] == pytest.approx(637.4, abs=0.1)
    assert w20["margin_slip"] == pytest.approx(0.5 * 637.4 / 288.0, abs=0.01) and w20["margin_slip"] >= 1.0
    assert w20["margin_webbing"] > 10.0
    # BL-030 adopted 20 mm (``chosen``, kept as history); BL-031 put rev 3 back on 25 mm (owner 2026-11-12)
    assert d["chosen"] is not None and d["chosen"]["width_mm"] == 20.0 and d["pass"]
    assert F.crown_strap_w() == 25.0


def test_extender_option_is_lighter_still_and_shortens_the_tail():
    _need_paths()
    d = F.crown_strap_diet()
    e = d["options"]["w20_ext"]
    assert e["cut_mm"] < d["cut_mm"] and e["tail_at_shortest_mm"] < d["tail_at_shortest_mm"]
    assert e["mass_g"] < d["options"]["w20"]["mass_g"]
    assert e["extender_mm"] > d["rolled_19in_mm"]["full"] - d["rolled_19in_mm"]["sixday"]


# ------------------------------------------------------------------------------------------- lid hold
def test_lid_hold_paper_check_follows_the_strap_wrap():
    _need_paths()
    h = F.lid_hold()
    m, k = h["lid_kg"], h["clamp_factor"]
    assert k == pytest.approx(2 * math.sin(math.radians(min(h["wrap_deg"], 180.0)) / 2), abs=1e-3)
    for a in (1.0, 3.0):
        c = h["cases"][f"{a:.0f}g"]
        assert c["inertia_n"] == pytest.approx(m * a * 9.80665, abs=0.06)
        assert c["outward_added_T_per_strap_n"] == pytest.approx(c["inertia_n"] / (2 * k), abs=0.06)
        assert c["outward_margin_slip"] > 3.0                     # lid thrown outward: far inside the lock slip
        assert c["slide_ok_cinch"]                                # hand-cinched (80 N): friction holds 3 g
    assert not h["cases"]["1g"]["slide_ok_relaxed"]               # relaxed cinch: friction alone does not (reported)
    assert h["captured_by_state"]["sixday"] and not h["captured_by_state"]["full"]


# ------------------------------------------------------------------------------------------- lid build hours
def test_lid_seam_list_adds_the_ring_handling_the_estimate_left_out():
    d = F.lid_seam_list()
    H = F.BC.HOURS
    assert d["hours"] == pytest.approx(sum(r["hours"] for r in d["rows"]), abs=0.05)
    rings = [r for r in d["rows"] if "ring handling" in r["op"]]
    assert len(rings) == 2 and all(r["rate_h"] == H["ring"] for r in rings)
    per = F.lid_geometry()["perimeter_mm"] / 1000.0
    curved = [r for r in d["rows"] if r["rate_h"] == H["curved_m"]]
    assert len(curved) == 2 and all(r["qty"] == pytest.approx(per, abs=1e-3) for r in curved)
    # the check is the estimate + 2 ring handlings + 1 more piece (zip splits the aft wall) + the wall closing seams
    extra = 2 * H["ring"] + H["cut_piece"] + F.LID_WALL_CLOSE * (F.LID["wall"] + 2 * F.SA_BODY) / 1000 * H["straight_m"]
    assert d["delta_h"] == pytest.approx(extra, abs=0.05)
    assert d["hours"] > d["bl029_estimate_h"] > d["pouch_h"]
