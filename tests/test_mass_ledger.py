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
    assert L.total("corrie_b2_today", "M") == pytest.approx(h["today_corrected"]["corrie_b2_M_g"], abs=0.5)
    assert L.total("corrie_b2_h1", "M") == pytest.approx(h["h1"]["corrie_b2_M_g"], abs=0.5)
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
    b1 = WP.breakdown("M")["reconciliation_g"]
    for s in L.SIZES:
        rec = [r for r in L.parts("corrie_b2_h1", s) if r["group"] == L.WP.G_REC]
        assert len(rec) == 1 and rec[0]["system"] == "misc"
        assert rec[0]["g"] == pytest.approx(b1, abs=0.1)


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
