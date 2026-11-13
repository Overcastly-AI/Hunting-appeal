"""BL-032 part A: CORRIE F rev 3 production patterns (designs/pack_5200/patterns_corrie_f_rev3.py)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import patterns_corrie_f_rev3 as PR  # noqa: E402


@pytest.fixture(scope="module")
def rsP():
    return PR.build("today")


@pytest.fixture(scope="module")
def rsB():
    return PR.build("B")


def test_every_seam_matches(rsP):
    rep = PR.seam_report(rsP, tol=1.0)
    assert len(rep.results) >= 28
    assert not rep.mismatches, [r.seam.name for r in rep.mismatches]
    names = {r.seam.name for r in rep.results}
    for must in ("door | blade U (#10 zip, R 55 corners)", "hinge band R | blade U", "B-29 crown | wall (ring)",
                 "B-29 wall | base (ring)", "B-29 aft wall #5 zip (upper | lower)", "collar | body tops (ring)"):
        assert must in names
    # the placeholder self-seams of corrie_f.build are replaced by real pairs
    for r in rep.results:
        a, b = r.seam.a, r.seam.b
        assert not (len(a) == 1 and len(b) == 1 and a[0].piece is b[0].piece and a[0].name == b[0].name), r.seam.name


def test_ledger_reconciles_one_to_one(rsB):
    rows = PR.ledger_rows()
    rec = PR.reconcile(rsB, rows)
    assert len(rec["rows"]) == len(rows)
    assert rec["unmatched_rows"] == [] and rec["multi_matched_rows"] == [] and rec["unused_entries"] == []
    assert rec["pieces_without_row"] == [] and rec["row_ids_not_drafted"] == []
    st = {o["status"] for o in rec["rows"]}
    assert st <= {"pattern", "webbing", "hardware", "removed", "not_drafted", "double_booked"}
    nd = [o["row"] for o in rec["rows"] if o["status"] == "not_drafted"]
    assert len(nd) == 3          # F-01 fly, its hem row, the US floor channels: reported, not hidden


def test_pattern_mass_within_3pct_of_ledger(rsB):
    mc = PR.mass_check(rsB)
    assert mc["ok"] and abs(mc["delta_pct"]) <= 3.0, mc
    rows = {r["row"][:6]: r for r in mc["rows"]}
    assert abs(rows["B-05 b"]["delta_g"]) < 0.05           # unchanged shell pieces weigh exactly what the ledger books
    assert rows["B-01 f"]["delta_g"] < -4.0                # B-01 loses its eight swell windows (ledger books them)


def test_fabric_maps_share_geometry(rsP, rsB):
    assert rsP.pieces["B-03"].material_id == "cordura_330d_nylon66"
    assert rsB.pieces["B-03"].material_id == "ultragrid_210d_uhmwpe_ripstop"
    assert rsP.pieces["B-06"].material_id == "robic_100d_ripstop" and rsB.pieces["B-06"].material_id == "nylon_ripstop_70d"
    assert rsP.pieces["B-05"].material_id == "cordura_500d_nylon66" and rsB.pieces["B-05"].material_id == "challenge_ultra_200"
    assert set(rsP.pieces) == set(rsB.pieces)
    for pid in rsP.pieces:
        assert rsP.pieces[pid].area_mm2 == pytest.approx(rsB.pieces[pid].area_mm2, rel=1e-9), pid


def test_every_piece_is_marked(rsP):
    for pid, p in rsP.pieces.items():
        assert p.piece_id and p.material_id and p.quantity >= 1, pid
        assert p.knife_direction, pid
        g0, g1 = p.grain_arrow()
        assert math.dist(g0, g1) > 5.0, pid
        sewn = p.material_id not in PR.WEBBING and p.material_id not in PR.FREE_ROTATION and \
            p.material_id != "hdpe_sheet" and p.seam_allowance_mm != 0.0
        if sewn:
            assert p.notches, f"{pid} has no notches"


def test_b01_windows_slits_and_creases(rsP):
    b01 = rsP.pieces["B-01"]
    win = [ln for ln in b01.internal_lines if ln.kind == "cut_inside" and ln.closed]
    assert len(win) == 8
    slits = [ln for ln in b01.internal_lines if ln.kind == "cut_inside" and not ln.closed]
    assert len(slits) == 2
    xs = sorted(round(ln.points[0][0]) for ln in slits)
    assert xs == [-52, 52]
    with PR.F.revision(3):
        M = PR._maps(PR.F.make())
    for ln in slits:      # slit z 595-745 (150 mm in z) unrolled on B-01: longer on the fabric above the z 631 crease
        assert PR._len(ln.points) == pytest.approx(M["s01"](745.0) - M["s01"](595.0), abs=0.01)
        assert 150.0 < PR._len(ln.points) < 160.0
    folds = [ln for ln in b01.internal_lines if ln.kind == "fold"]
    assert len(folds) >= 2


def test_b22_and_b28_tabs_sit_on_the_hinge_band(rsP):
    hb = rsP.pieces["B-02h"]
    g = rsP.geo["b22"]
    assert g["placed_x"] + PR.B22_WH[0] / 2 <= g["band_half_w_at_z"] - PR.B22_EDGE_CLEAR + 1e-6
    x0, y0, x1, y1 = hb.bounds(cut=False)
    for ln in hb.internal_lines:
        if ln.kind == "placement":
            for x, y in ln.points:
                assert x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6


def test_lid_draft(rsP):
    L = rsP.lid
    assert L["perimeter_mm"] == pytest.approx(PR.F.lid_geometry()["perimeter_mm"], abs=0.5)
    assert L["flat_crown_perimeter_mm"] > L["perimeter_mm"]             # the dome needs the darts
    for d in L["darts"]:
        assert d["open_mm"] > 10.0
    crown = rsP.pieces["B-29a"]
    for k in range(1, 5):
        assert crown.edge_length(f"dart{k}a") == pytest.approx(crown.edge_length(f"dart{k}b"), abs=0.1)
    spans = sum(crown.edge_length(n) for n in ("aft_L", "left", "front", "right", "aft_R"))
    assert spans == pytest.approx(L["perimeter_mm"], abs=0.5)
    wall = rsP.pieces["B-29c"].edge_length("top") + rsP.pieces["B-29d"].edge_length("top")
    assert wall == pytest.approx(L["perimeter_mm"], abs=0.5)
    assert rsP.pieces["B-29d"].edge_length("top") == pytest.approx(PR.LID["zip_mm"])


def test_lid_hours_on_drafted_pattern(rsP):
    h = PR.lid_hours(rsP)
    assert h["pieces_cut"] == 9
    assert h["hours"] == pytest.approx(sum(r["hours"] for r in h["rows"]), abs=0.02)
    assert h["bl030_h"] == pytest.approx(8.94, abs=0.01) and h["bl029_booked_h"] == pytest.approx(7.76, abs=0.01)
    assert h["hours"] > h["bl030_h"]          # four darts, one cut piece fewer


def test_crown_straps_and_w3_per_kit(rsP):
    g = rsP.graded["B-28"]
    assert set(g) == set(PR.CROWN_KITS)
    for k, p in g.items():
        assert p.edge_length("left") == pytest.approx(PR.F.crown_kit_straps(k)["cut_mm"], abs=0.1)
        assert p.quantity == 2
    w3 = rsP.graded["W3"]
    assert w3["S"].edge_length("left") > w3["M"].edge_length("left") > w3["L"].edge_length("left")
    ids = {w["id"] for w in rsP.webbing}
    for must in ("WX", "K-28", "K-IM", "K-RT", "RT", "W1", "W2", "B-25", "TG", "B-24"):
        assert must in ids
    wx = [w for w in rsP.webbing if w["id"] == "WX"][0]
    assert wx["qty"] == 3 and wx["kit"] == "meat_trip" and wx["length_mm"] == pytest.approx(740.0, abs=1.0)


def test_notch_pair_matches_positions():
    a = PR.Piece.from_edges("a", [("e", [(0, 0), (300, 0)]), ("f", [(300, 0), (300, 50), (0, 50)])], seam_allowance_mm=10)
    b = PR.Piece.from_edges("b", [("e", [(0, 0), (150, 0), (300, 0)]), ("f", [(300, 0), (300, 50), (0, 50)])],
                            seam_allowance_mm=10)
    n = PR.notch_pair([(a, a.edge_points("e"))], [(b, b.edge_points("e")[::-1])], "t", pitch=100.0)
    assert n == 2
    xa = sorted(round(k.x) for k in a.notches)
    xb = sorted(round(k.x) for k in b.notches)
    assert xa == [100, 200] and xb == [100, 200]
    assert np.allclose([k.y for k in a.notches + b.notches], 0.0)
