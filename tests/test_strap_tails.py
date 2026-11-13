"""BL-031: B-28 crown straps cut per crown kit at 25 mm, and the pack-wide strap tail rule.

    python -m pytest -q tests/test_strap_tails.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(CONCEPTS / "corrie_f_sim"), str(ROOT / "designs" / "pack_5200")):
    if p not in sys.path:
        sys.path.insert(0, p)

import corrie_f as F  # noqa: E402
import strap_tails as ST  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402


def _need_paths():
    if not (F.CROWN_PATHS.exists() and F.CROWN_ROLLED.exists()):
        pytest.skip("crown path files missing: corrie_f.py --bl029 and python -m huntkit.viz3d.corrie_f --crown-paths")


# ------------------------------------------------------------------------------------------- crown straps per kit
def test_rev3_default_is_25mm_per_kit_and_bl030_20mm_is_history():
    _need_paths()
    assert F.REVISION == 3 and F.crown_strap_w() == 25.0 and F.REVS[3]["crown_kits"]
    cs = F.crown_straps()
    assert cs["width_mm"] == 25.0 and cs["kit"] == F.CROWN_KIT_DEFAULT == "M" and cs["adjusters"] == 2
    assert F.crown_straps(25.0, "S")["kit"] == "S"
    assert F.crown_straps(20.0)["width_mm"] == 20.0                     # BL-030's diet, still reproducible
    assert F.crown_strap_diet()["chosen"]["width_mm"] == 20.0
    # BL-035 (one mass basis): BL-029's strap is re-booked on the pom_toggle record (1.7 g, was the 3.0 g ASSUMPTION
    # BL-029 used): 67.46 -> 64.86 g = 2 toggles x -1.3 g. The cut and the path are unchanged (history geometry).
    bl029 = F.crown_straps_bl029()
    assert bl029["mass_g"] == pytest.approx(64.86, abs=0.05)
    assert bl029["mass_g"] - 2 * (bl029["toggle_g"] - 3.0) == pytest.approx(67.46, abs=0.05)   # BL-029 as booked
    with F.revision(2):
        assert F.crown_straps()["cut_mm"] == F.crown_straps_bl029()["cut_mm"]


def test_kits_take_their_own_torso_range_from_the_paths():
    _need_paths()
    rp = json.loads(F.CROWN_ROLLED.read_text())["states"]
    full = max(s["length_mm"] for s in rp["full"]["straps"].values())
    day = min(s["length_mm"] for s in rp["day"]["straps"].values())
    td = F._crown_torso_delta()["all"]
    assert F._crown_delta_at(19.0) == pytest.approx([0.0] * len(td[15]))
    assert F._crown_delta_at(15.0) == pytest.approx(td[15]) and F._crown_delta_at(23.0) == pytest.approx(td[23])
    kits = F.crown_kits()
    assert kits == {"S": (15.0, 18.0), "M": (17.5, 20.5), "L": (20.0, 23.0)}
    cuts = []
    for k, (lo, hi) in kits.items():
        a = F.crown_kit_straps(k)
        ds = F._crown_delta_at(lo) + F._crown_delta_at(hi)
        assert a["path_max_mm"] == pytest.approx(full + max(ds), abs=0.1)
        assert a["path_min_mm"] == pytest.approx(day + min(ds), abs=0.1)
        assert a["cut_mm"] == pytest.approx(a["path_max_mm"] + 2 * F.TAIL_GRIP_MM, abs=0.1)
        # two adjusters share the slack: each tail = grip + half the take-up
        assert a["tail_worst_mm"] == pytest.approx(F.TAIL_GRIP_MM + a["adjust_range_mm"] / 2, abs=0.1)
        assert a["tail_used_mm"] == pytest.approx(F.TAIL_GRIP_MM + (a["path_max_mm"] - a["path_used_mm"]) / 2, abs=0.1)
        one = F.crown_kit_straps(k, adjusters=1)
        assert one["tail_used_mm"] > a["tail_used_mm"] and one["mass_g"] < a["mass_g"]
        cuts.append(a["cut_mm"])
    assert cuts[0] > cuts[1] > cuts[2]                                   # S is longest: its bar sits lowest
    # S full-at-15 in is BL-030's single cut path; L's day-at-23 in is its shortest path
    d = F.crown_strap_diet()
    assert F.crown_kit_straps("S")["path_max_mm"] == pytest.approx(d["path_max_mm"], abs=0.1)
    assert F.crown_kit_straps("L")["path_min_mm"] == pytest.approx(d["path_min_mm"], abs=0.1)


def test_crown_strap_mass_from_records_and_keepers():
    _need_paths()
    a = F.crown_kit_straps("M")
    import attach_diet as AD
    tabs = 3 * F.CROWN_TAB
    want = 2 * ((a["cut_mm"] + tabs) * F.WEB25 / 1000 + AD.TOGGLE_G + 2 * F._rec("ladder_lock_25mm_heavy", "mass_g")
                + a["keepers_per_strap"] * F.TAIL_KEEPER_G)
    assert a["mass_g"] == pytest.approx(want, abs=0.02)
    assert a["keepers_per_strap"] == 2 and a["tail_worst_mm"] > F.KEEPER_OVER_MM
    t = F.crown_kit_table()
    assert t["kits"]["M"]["margin_slip"] == pytest.approx(490.0 / 288.0, abs=0.01) and t["kits"]["M"]["margin_slip"] >= 1.0
    # the lid-hold check now reads the 25 mm heavy lock
    assert F.lid_hold()["slip_n"] == 490.0


# ------------------------------------------------------------------------------------------- the audit
def test_every_adjustable_strap_meets_the_rule_or_has_a_keeper():
    _need_paths()
    au = ST.audit("M", "M")
    ids = {r["id"] for r in au["rows"]} | {o["id"] for o in au["other"]}
    for need in ("B-28", "LL", "ST", "HS", "HB", "W1", "W2", "W3", "IM1", "IM2", "IM3", "US", "RT", "B-24", "B-25",
                 "B-26", "PG", "SH"):
        assert need in ids
    for r in au["rows"]:
        a = r["after"]
        assert a["rule_used"] or a["keeper"], r["id"]
        assert (a["tail_worst_mm"] <= F.KEEPER_OVER_MM) or a["keeper"], r["id"]
        assert a["tail_longest_path_mm"] >= F.TAIL_GRIP_MM - 5.0 - 1e-6, r["id"]   # always a gloved grip (floor-5 cut)
    assert au["all_pass"]
    # before BL-031 these did not meet the rule and had no keeper
    before = {r["id"]: r["before"] for r in au["rows"]}
    for k in ("ST", "HS", "IM1", "B-28"):
        assert not before[k]["rule_used"] and not before[k]["keeper"]
    # roll clips: on the cloth-pass roll the 350 mm cut could not reach a full bag (collar standing)
    rt = {r["id"]: r for r in au["rows"]}["RT"]
    if ST.ROLL_CLIPS.exists():
        assert rt["before"]["cut_mm"] - ST.ROLL_END_MM < rt["paths_mm"]["max"] <= rt["after"]["cut_mm"] - ST.ROLL_END_MM


def test_wraps_cut_for_carry_with_haul_extenders():
    _need_paths()
    g = {w["id"]: w for w in ST._geo()["haul_wraps"]}
    for r in ST.wrap_rows("M"):
        w = g[r["id"]]
        assert r["before"]["cut_mm"] == pytest.approx(w["cut_length_mm"] - 100.0)      # A-2 250 -> 150 mm tails
        assert r["after"]["cut_mm"] == pytest.approx(ST.W_HOOK_END_MM + r["paths_mm"]["max"] + F.TAIL_GRIP_MM, abs=0.1)
        assert r["after"]["tail_used_mm"] <= F.TAIL_RULE_MM
        # the extender restores the haul path with the same grip
        assert r["haul"]["extender_mm"] == pytest.approx(r["haul"]["path_mm"] - r["paths_mm"]["max"]
                                                         + ST.W_EXT_ENDS_MM, abs=0.1)
        assert r["haul"]["tail_after_mm"] == pytest.approx(F.TAIL_GRIP_MM, abs=0.1)


def test_belt_tail_follows_closure_and_the_2to1():
    import hipbelt_diet as HD
    for s in ("S", "M", "XL"):
        r = ST.belt_row(s)
        c = HD.closure(s)
        assert r["before"]["tail_worst_mm"] == pytest.approx(c["tail_at_min_mm"], abs=1.0)
        assert r["after"]["tail_worst_mm"] == pytest.approx(F.TAIL_GRIP_MM + 2 * (c["leg_max_mm"] - c["leg_min_mm"]))
        assert r["after"]["keeper"]


def test_lifter_path_is_the_crown_setting_geometry():
    from huntkit.gendesign import attach_system as AS
    cs = AS._bg().crown_settings()
    angs = {round(c["lifter_angle_deg"], 1) for c in cs}
    assert len(angs) == 1                                              # same lifter angle at every setting
    r = ST.lifter_row()
    assert r["paths_mm"]["used"] == pytest.approx(140.0 / math.cos(math.radians(angs.pop())), abs=0.1)
    assert r["after"]["rule_used"] and r["after"]["cut_mm"] % 5 == 0


# ------------------------------------------------------------------------------------------- mass booking
def test_bag_rows_are_in_the_adopted_bag_and_suspension_rows_in_the_ledger():
    _need_paths()
    rows = L.adopted_bag_rows("M")
    names = {r["name"]: r for r in rows}
    for s, n, g, c, src in ST.bag_rows():
        assert n in names and names[n]["g"] == pytest.approx(g, abs=0.01) and names[n]["cfg"] == c
    corr = L.corrections("corrie_b2_h1", "M")["BL031"]
    assert len(corr) == len(ST.suspension_rows("M"))
    assert sum(r["g"] for r in corr) == pytest.approx(sum(r[2] for r in ST.suspension_rows("M")), abs=0.05)
    ext = [r for s, n, g, c, r in ST.bag_rows() if c == "meat_trip"]
    assert len(ext) == 1                                              # the haul extenders ride in the meat-trip kit
    ms = ST.mass_summary()
    assert ms["base"]["total_g"] < 0 and ms["meat_trip"]["total_g"] > 0
