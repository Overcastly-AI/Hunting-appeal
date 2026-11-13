"""BL-001 mass ledger: totals reproduce the existing bookings, every part sits in exactly one system, and the fixed
group definitions add up."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from huntkit.mass import ledger as L

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "designs" / "pack_5200" / "analysis"
KEYS = {"id", "name", "group", "system", "g", "source", "load_path", "base"}


def _j(name):
    return json.loads((ANALYSIS / name).read_text())


@pytest.mark.parametrize("size", L.SIZES)
def test_today_reproduces_weight_table(size):
    """corrie_b2_today = corrie.weight_table(size, 'B.2') + the one correction row (z 234 dowels) it never booked."""
    import corrie as C
    rows = L.parts("corrie_b2_today", size)
    corr = [r for r in rows if r.get("note", "").startswith("CORRECTION")]
    assert len(corr) == 1 and corr[0]["g"] == pytest.approx(_j("frame_mass_production.json")["z234_dowels_mma_g"])
    wt = C.weight_table(size, spec="B.2")["total_g"]
    assert L.total(rows) - corr[0]["g"] == pytest.approx(wt, abs=0.5)
    assert L.weight_table_total(size) == wt


def test_cross_check_frame_mass_h1_json():
    h = _j("frame_mass_h1.json")
    # frame_mass_h1.json is BL-007's record (pack totals at the masses of 2026-11-10). The bag and shared rows have been
    # re-booked on material records since (BL-034 / BL-035), +46.5 g on both configs; the frames are unchanged:
    #   +26.0 #10 door sliders (slider_10 19.0 g, was 6 g), +16.0 stainless US tri-glides (2 x 11 g, was 2 x 3 g),
    #   +1.9 IMP-4 #5 slider (slider_5 4.9 g, was 3 g)                                    [BL-034 records]
    #   +4.5 elastic hook keepers (6 x 1.35 g, was 6 x 0.6), -0.8 lifter tri-glides (2 x 2.6, was 2 x 3),
    #   -1.1 torso adjust (cam 12.2 + toggle 1.7, was 12 + 3)                              [BL-035 records]
    #   -2.6 hood POM toggles (2 x 1.7, was 2 x 3), -0.8 guy tri-glides (attach_system phase rows on the records),
    #   -2.7 misc thread no longer counts the S-strap set                              [BL-036]
    rebook = 26.0 + 16.0 + 1.9 + 4.5 - 0.8 - 1.1 - 2.6 - 0.8 - 2.7
    assert L.total("corrie_b2_today", "M") == pytest.approx(h["today_corrected"]["corrie_b2_M_g"] + rebook, abs=0.5)
    assert L.total("corrie_b2_h1", "M") == pytest.approx(h["h1"]["corrie_b2_M_g"] + rebook, abs=0.5)
    assert L.total("corrie_b2_today", "M") == pytest.approx(4023.4, abs=0.1)   # BL-036 (was 4029.5)
    assert L.total("corrie_b2_h1", "M") == pytest.approx(3967.4, abs=0.1)   # BL-036 (was 3973.5)
    fr = lambda c: sum(r["g"] for r in L.parts(c, "M") if r["system"] == "frame" and not r["name"].startswith("torso"))  # noqa: E731
    assert fr("corrie_b2_today") == pytest.approx(h["today_corrected"]["frame_g"], abs=0.2)
    assert fr("corrie_b2_h1") == pytest.approx(h["h1"]["frame_g"], abs=0.2)


@pytest.mark.parametrize("config", L.CONFIGS)
@pytest.mark.parametrize("size", L.SIZES)
def test_rows_one_system_each_and_groups_add_up(config, size):
    rows = L.parts(config, size)
    assert rows
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "row ids must be unique"
    for r in rows:
        assert KEYS <= set(r), r
        assert isinstance(r["system"], str) and r["system"] in L.SYSTEMS, r
        assert isinstance(r["load_path"], bool) and isinstance(r["base"], bool)
        assert r["source"]
    # the systems partition the rows: sum over systems = total
    bs = L.by_system(rows)
    assert sum(bs.values()) == pytest.approx(L.total(rows), abs=0.15)
    assert set(L.BAG_SIDE) | set(L.SUSPENSION) | {"misc"} == set(L.SYSTEMS)
    assert not set(L.BAG_SIDE) & set(L.SUSPENSION)
    lf = L.like_for_like(rows)
    assert lf["bag_side"] + lf["suspension"] + lf["misc"] == pytest.approx(L.total(rows), abs=0.15)
    assert L.bag_system(rows) == pytest.approx(sum(bs[s] for s in L.BAG_SYSTEM), abs=0.15)


def test_bag_system_is_one_number():
    """The bag system and the bag side do not depend on the frame config or the belt size."""
    b = L.corrie_bag_system()
    side = L.like_for_like("corrie_b2_h1", "M")["bag_side"]
    for c in L.CONFIGS:
        for s in L.SIZES:
            assert L.bag_system(c, s) == b
            assert L.like_for_like(c, s)["bag_side"] == side
    assert 500 < b < 1500


def test_reconciliation_row_is_spec_and_size_independent():
    """The only balancing row equals the weight pass's own B.1 reconciliation at every size: B.2 differs from B.1 only by
    rows the ledger itemizes (corrie.b2_rows + the B.2 part list)."""
    import weight_pass_corrie as WP
    b1 = next(p["g"] for p in WP.breakdown("M")["parts"] if p["group"] == WP.G_REC)
    got = []
    for s in L.SIZES:
        rec = [r for r in L.parts("corrie_b2_h1", s) if r["group"] == L.WP.G_REC]
        assert len(rec) == 1 and rec[0]["system"] == "misc"
        got.append(rec[0]["g"])
    # weight_table totals are rounded to 0.1 g and ~100 part rows to 0.01 g: allow 0.2 g of rounding
    assert max(got) - min(got) < 0.2
    for g in got:
        assert g == pytest.approx(b1, abs=0.2)
        assert abs(g) < 5.0      # a balancing row, not a hidden part


def test_frames_and_package_c():
    import corrie as C
    today, h1, hc = (L.by_system(c, "M") for c in ("corrie_b2_today", "corrie_b2_h1", "corrie_b2_h1_c"))
    for s in L.SYSTEMS:
        if s != "frame":
            assert today[s] == h1[s]
    assert today["frame"] - h1["frame"] == pytest.approx(-_j("frame_mass_h1.json")["h1"]["delta_vs_today_g"], abs=0.2)
    c_rows = C.package_c_rows()
    c_net_no_c9 = sum(g for n, g, _ in c_rows if not n.startswith("C-9"))
    assert L.total("corrie_b2_h1_c", "M") - L.total("corrie_b2_h1", "M") == pytest.approx(c_net_no_c9, abs=0.15)
    c9 = [r for r in L.parts("corrie_b2_h1_c", "M") if r["name"].startswith("C-9")]
    assert len(c9) == 1 and c9[0]["g"] == 0.0 and "NOT APPLIED" in c9[0]["note"]
    assert hc["frame"] == h1["frame"] and hc["belt"] < h1["belt"] and hc["harness"] > h1["harness"]


def test_system_sorting_spot_checks():
    rows = {r["name"]: r for r in L.parts("corrie_b2_h1", "M")}
    sys_of = lambda prefix: {r["system"] for n, r in rows.items() if n.startswith(prefix)}  # noqa: E731
    assert sys_of("IMP-6") == {"harness"}
    assert sys_of("IMP-1") == sys_of("IMP-2") == sys_of("IMP-4") == sys_of("IMP-8") == {"bag_pockets"}
    assert sys_of("IMP-5") == sys_of("IMP-3") == {"belt"}
    assert sys_of("M-01") == sys_of("SH-06") == sys_of("wing strap") == {"straps_compression"}
    assert sys_of("haul wraps") == sys_of("A-2") == {"straps_compression"}
    assert sys_of("internal meat harness") == sys_of("under-straps") == sys_of("float-mode") == {"straps_meat"}
    assert sys_of("B-13x") == {"attachment"}
    assert sys_of("L-2") == {"pouch"} and sys_of("pouch: 4 x 25 mm") == {"straps_compression"}
    assert sys_of("G-2") == sys_of("rain fly") == {"fly"}
    assert sys_of("B-02door") == sys_of("horseshoe door zip") == {"bag_shell"}
    # load path flags
    assert all(r["load_path"] for r in rows.values() if r["system"] == "frame" and not r["name"].startswith("torso"))
    assert not any(r["load_path"] for r in rows.values() if r["system"] in ("bag_shell", "bag_pockets", "pouch", "fly"))
    assert all(r["load_path"] for n, r in rows.items() if n.startswith("internal meat harness: 3 x 38"))
    assert all(r["base"] for r in rows.values())


def test_unknown_inputs_raise():
    with pytest.raises(KeyError):
        L.parts("spine", "M")
    with pytest.raises(KeyError):
        L.parts("corrie_b2_h1", "XS")
    with pytest.raises(KeyError):
        L._system("new group", "new part")


def test_no_hand_typed_masses_in_module():
    """The module reads masses; numeric literals are only formatting / plotting constants and unit factors."""
    src = (ROOT / "huntkit" / "mass" / "ledger.py").read_text()
    code = re.sub(r'""".*?"""', "", src, flags=re.S)
    lits = {float(x) for x in re.findall(r"(?<![\w.])(\d+\.\d+)(?![\w.])", code)}
    allowed = {L.LB, L.OZ, 9.0, 9.5, 0.62, 0.8, 1.12, 0.25, 0.5, 0.09, 0.05, 0.0}
    assert lits <= allowed, sorted(lits - allowed)
    for bad in ("3964", "3927", "3983", "884", "1062", "823.2", "710.6", "3943"):
        assert bad not in code, bad


def test_teams_on_one_basis():
    base = L.corrie_bag_system()
    rows = {t["team"]: t for t in L.teams()}
    assert set(rows) == {"A", "B", "B day", "C", "D", "E"}
    for t in rows.values():
        assert t["ledger_g"] == pytest.approx(base + t["published_g"] - t["baseline_g"] + t["adj_g"], abs=0.15)
        assert t["pack_M_h1_g"] == pytest.approx(L.total("corrie_b2_h1", "M") - base + t["ledger_g"], abs=0.15)
    # A, B, C: nothing in their metric falls outside the ledger bag system, so their deltas do not move
    for k in ("A", "B", "C"):
        assert rows[k]["adj_g"] == pytest.approx(0.0, abs=0.05)
    # E's strap pocket and D's strap pocket go to the harness; D's double-counted HDPE strip comes back
    assert rows["E"]["adj_g"] < -10 and rows["D"]["ledger_delta_g"] < rows["D"]["published_delta_g"]
    # FELL stays the lightest entry on the ledger basis
    assert min((t for k, t in rows.items() if k != "B day"), key=lambda t: t["ledger_g"])["team"] == "B"


# =====================================================================================================================
# BL-023: the BL-013 booking corrections folded into the ledger
# =====================================================================================================================
@pytest.mark.parametrize("config", L.CONFIGS_V2)
@pytest.mark.parametrize("size", ("S", "M", "XXL"))
def test_v2_rows_valid_and_add_up(config, size):
    rows = L.parts(config, size)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    for r in rows:
        assert KEYS <= set(r) and r["system"] in L.SYSTEMS and r["source"]
    corr = [r for r in rows if r["group"] == L.G_CORR]
    want = set(L.CORRECTIONS) - (set(L.H1_ONLY) if config == "corrie_b2_today_v2" else set())
    assert {r["correction"] for r in corr} == want                            # H1B applies to the H1 bodies only
    assert all(r["note"].startswith("CORRECTION") for r in corr)
    bs = L.by_system(rows)
    assert sum(bs.values()) == pytest.approx(L.total(rows), abs=0.35)       # 12 systems, each rounded to 0.1 g


@pytest.mark.parametrize("config", L.CONFIGS)
def test_legacy_configs_reproducible_behind_the_flag(config):
    """The BL-001 names are unchanged; corrected=True is the _v2 config; v2 = legacy + the correction rows."""
    legacy = L.parts(config, "M")
    assert not any(r["group"] == L.G_CORR for r in legacy)
    v2 = L.parts(config + L.SUFFIX, "M")
    assert L.parts(config, "M", corrected=True) == v2
    assert v2[: len(legacy)] == legacy
    corr = sum(r["g"] for rs in L.corrections(config, "M").values() for r in rs)
    assert L.total(config + L.SUFFIX, "M") == pytest.approx(L.total(config, "M") + corr, abs=0.15)
    assert L.total(config, "M", corrected=True) == L.total(config + L.SUFFIX, "M")


def test_corrections_match_their_sources():
    led = {r["name"]: r["g"] for r in L.parts("corrie_b2_h1", "M")}
    c = {k: sum(r["g"] for r in v) for k, v in L.corrections("corrie_b2_h1", "M").items()}
    assert c["C1"] == pytest.approx(-led["attachment: printed fairleads (8)"])
    assert c["C2"] == pytest.approx(-led["attachment: B-01 swell patches"])
    cw = L.corner_wraps()
    assert 15.0 < cw["wraps_g"] < 20.0
    assert c["C3"] == pytest.approx(cw["unbooked_g"], abs=0.02)
    assert c["C4"] == pytest.approx(-8.0)
    assert c["C5"] == pytest.approx(L.non_body_sources()["short_g"], abs=0.02)
    assert c["C5"] == pytest.approx(9.1, abs=0.1)
    assert c["C6"] == pytest.approx(0.0) and c["C7"] == pytest.approx(0.0)        # a move and a cfg split
    c6 = L.corrections("corrie_b2_h1", "M")["C6"]
    assert {r["system"] for r in c6} == {"attachment", "harness"}
    c7 = L.corrections("corrie_b2_h1", "M")["C7"]
    assert sorted(r["cfg"] for r in c7) == ["as_hunted", "base"] and sum(r["g"] for r in c7 if r["base"]) > 0
    import hipbelt_diet as HD
    assert c["C8"] == pytest.approx(HD.closure("M")["delta_g"], abs=0.05)
    # net effect on the whole H1 pack (every item booked), belt M: the C1..C8 meat-trip deltas of BL-013 sum to -49.1 g,
    # and H1B adds the 2026-11-12 body (+42.9 g, h1_buckling.md / DECISIONS BL-027 row)
    assert L.total("corrie_b2_h1_v2", "M") - L.total("corrie_b2_h1", "M") == pytest.approx(sum(c.values()), abs=0.15)
    assert sum(v for k, v in c.items() if k not in ("H1B", "BL031")) == pytest.approx(-49.1, abs=0.5)
    import strap_tails as ST                                       # BL-031: harness / belt side of the tail rule
    assert c["BL031"] == pytest.approx(sum(r[2] for r in ST.suspension_rows("M")), abs=0.05) and c["BL031"] < 0
    assert c["H1B"] == pytest.approx(42.9, abs=0.1)


def test_h1_body_correction_traces_to_h1_buckling():
    """H1B: the H1 body as adopted (BL-024 +18.8 g, BL-027 members +22.2 g, 28 mm IM3 cheeks +2.0 g; 800.7 g raster),
    read from analysis/h1_buckling.json, on top of the 757.7 g that frame_mass_h1.json books. Not on today's frame."""
    hb = L.h1_body_update()
    hj = _j("h1_buckling.json")["chosen"]
    assert hb["booked_g"] == _j("frame_mass_h1.json")["h1"]["body_g"] == pytest.approx(757.7)
    assert hb["body_g"] == hj["body_raster_g"] == pytest.approx(800.7, abs=0.05)          # DECISIONS BL-027 row
    assert hb["bl024_g"] == pytest.approx(18.8, abs=0.05)                                  # DECISIONS BL-024 row
    assert hb["bl027_members_g"] == pytest.approx(22.2, abs=0.05)                          # DECISIONS BL-027 row
    assert hb["im3_cheek_28_g"] == pytest.approx(2.0, abs=0.05)                            # h1_buckling.md line 13
    assert hb["steps_sum_g"] == pytest.approx(hj["added_vs_h1_g"], abs=1e-6)
    for cfg in ("corrie_b2_h1", "corrie_b2_h1_c"):
        rows = L.corrections(cfg, "M")["H1B"]
        assert len(rows) == 3 and all(r["system"] == "frame" and r["base"] and r["load_path"] for r in rows)
        assert all("h1_buckling.json" in r["source"] for r in rows)
        body = sum(r["g"] for r in L.parts(cfg + L.SUFFIX, "M") if r["name"].startswith(("frame: H1 PAHT", "H1 body")))
        assert body == pytest.approx(800.7, abs=0.1)
    assert L.corrections("corrie_b2_today", "M")["H1B"] == []
    assert "H1B" in L.H1_ONLY


def test_v2_shifts_systems_as_booked():
    old, new = L.by_system("corrie_b2_h1", "M"), L.by_system("corrie_b2_h1_v2", "M")
    assert new["attachment"] < old["attachment"]
    # harness: + the C6 keepers moved in, + BL-031's lifters and sternum cut to length (negative)
    corr = L.corrections("corrie_b2_h1", "M")
    assert new["harness"] - old["harness"] == pytest.approx(
        sum(r["g"] for k in ("C6", "BL031") for r in corr[k] if r["system"] == "harness"), abs=0.15)
    assert new["frame"] - old["frame"] == pytest.approx(
        sum(r["g"] for k in ("C3", "C4", "C5", "H1B") for r in L.corrections("corrie_b2_h1", "M")[k]), abs=0.15)
    assert L.bag_system("corrie_b2_h1_v2", "M") == L.corrie_bag_system()      # C1/C2/C6 are outside the bag system
    assert L.DEFAULT_CONFIG == "corrie_b2_h1_v2" and L.total() == L.total("corrie_b2_h1_v2", "M")
    with pytest.raises(KeyError):
        L.parts("corrie_b2_h1_v3", "M")
