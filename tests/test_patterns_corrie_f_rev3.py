"""BL-032 part A + BL-033 fixes: CORRIE F rev 3 production patterns (designs/pack_5200/patterns_corrie_f_rev3.py)."""
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
    nd = [o["row"] for o in rec["rows"] if o["status"] in ("not_drafted", "double_booked")]
    assert nd == []              # BL-033: the fly, its hem, the US channels drafted; the swell-patch double booking gone
    assert not any(r["name"] == "attachment: B-01 swell patches" for r in rows)


def test_pattern_mass_within_3pct_of_ledger(rsB):
    mc = PR.mass_check(rsB)
    assert mc["ok"] and abs(mc["delta_pct"]) <= 3.0, mc
    rows = {r["row"][:6]: r for r in mc["rows"]}
    assert abs(rows["B-05 b"]["delta_g"]) < 0.05           # unchanged shell pieces weigh exactly what the ledger books
    assert abs(rows["B-01 f"]["delta_g"]) < 0.05           # BL-033: the ledger books B-01 net of its windows too
    assert abs(rows["F-01 r"]["delta_g"]) < 0.05           # the fly is booked from its drafted pieces
    assert abs(rows["US-cha"]["delta_g"]) < 0.05


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
    assert len(win) == 6         # BL-033 H-1: IM1-IM3 only, no hinge window
    # no window crosses a B-18 doubler (the hinge load path)
    b18 = [ln for ln in b01.internal_lines if ln.kind == "placement" and ln.label.startswith("B-18")]
    assert len(b18) == 2
    for d in b18:
        dx0, dx1 = min(x for x, _ in d.points), max(x for x, _ in d.points)
        dy0, dy1 = min(y for _, y in d.points), max(y for _, y in d.points)
        for w in win:
            wx0, wx1 = min(x for x, _ in w.points), max(x for x, _ in w.points)
            wy0, wy1 = min(y for _, y in w.points), max(y for _, y in w.points)
            assert wx1 <= dx0 or wx0 >= dx1 or wy1 <= dy0 or wy0 >= dy1
        assert min(wy0 for w in win for wy0 in [min(y for _, y in w.points)]) - dy1 > 50.0
    assert "B-13xh" not in rsP.pieces and rsP.pieces["B-13x"].quantity == 6
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
    assert h["booked_now_h"] == pytest.approx(h["hours"], abs=0.005)   # BL-033: corrie_f books the drafted hours


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


# ---------------------------------------------------------------------------- BL-033
def test_fp_pocket_165_face_fits_the_gusset(rsP):
    fp = PR.F.fp_spec()
    assert fp["w"] == 165.0 and fp["w"] + fp["pleat"] == pytest.approx(260.0)    # mesh kept, pleats take the 15 mm
    assert rsP.pieces["FP-a"].edge_length("top") == pytest.approx(260.0)
    assert rsP.geo["fp_min_margin_mm"] >= rsP.geo["fp_clear_req_mm"]          # plain rectangle, no clamp
    assert rsP.geo["fp_clamped_mm"] == 0.0
    G = rsP.pieces["B-03"]
    fp_line = [ln for ln in G.internal_lines if ln.label.startswith("FP hip-reach")][0]
    xs = sorted({round(x, 3) for x, _ in fp_line.points})
    widths = [max(x for x, _ in fp_line.points) - min(x for x, _ in fp_line.points)]
    assert widths[0] >= 165.0 - 1e-6 and len(xs) >= 2


def test_rain_fly_drafted_and_sewn(rsP):
    sp, sd = rsP.pieces["F-01a"], rsP.pieces["F-01b"]
    assert sp.material_id == sd.material_id == "silicone_coated_poly_ripstop_40d"
    assert sd.quantity == 2 and sd.mirror
    rep = PR.seam_report(rsP)
    fly = [r for r in rep.results if r.seam.name.startswith("F-01a spine")]
    assert len(fly) == 2 and all(abs(r.error_mm) < 0.5 for r in fly)
    g = rsP.geo["fly"]
    # covers the full rolled state: the side panel reaches the lid wall top
    assert g["lid_top_z"] > 1000.0 and g["seam_mm"] > 1200.0
    # the fly fits one width of its roll (60 in silpoly, usable 1473 mm)
    x0, y0, x1, y1 = sp.bounds()
    assert min(x1 - x0, y1 - y0) < 1473.0
    assert any(w["id"] == "F-EL" for w in rsP.webbing)


def test_us_floor_channels(rsP):
    b16 = rsP.pieces["B-16"]
    assert b16.quantity == 2
    f02 = rsP.pieces["F-02"]
    ch = [ln for ln in f02.internal_lines if ln.label.startswith("B-16 channel")]
    assert len(ch) == 4
    x0, y0, x1, y1 = f02.bounds(cut=False)
    for ln in ch:
        for x, y in ln.points:
            assert y0 < y < y1


def test_b27_facing_on_the_fabric_slit(rsP):
    gp = PR.F.guy_port()
    assert gp["slit_mm"] == pytest.approx(156.2, abs=0.05)
    assert rsP.pieces["B-27f"].edge_length("left") == pytest.approx(gp["slit_mm"] + 2 * PR.F.PORT_END, abs=0.05)


# ---------------------------------------------------------------------------------------------------------- BL-035
def _boxes(p):
    """(w, h, label, (x0, y0, x1, y1)) of every box-X rectangle drawn on a piece."""
    out = []
    for ln in p.internal_lines:
        if ln.closed and "box-X" in (ln.label or ""):
            xs, ys = [q[0] for q in ln.points], [q[1] for q in ln.points]
            out.append((round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1), ln.label,
                        (min(xs), min(ys), max(xs), max(ys))))
    return out


def test_bl035_b28_split_toggle_loop_passes(rsP):
    """B-28s (the B-25 second fold) has a 21 x 15 box at the tip end: the loop left at the fold passes the POM toggle."""
    t, s = rsP.pieces["B-28t"], rsP.pieces["B-28s"]
    assert t.quantity == 4 and s.quantity == 2                      # 6 tabs of CROWN_TAB as before (mass unchanged)
    assert [(b[0], b[1]) for b in _boxes(t)] == [(21.0, 20.0)]
    (w, h, _, (x0, y0, x1, y1)), = _boxes(s)
    assert (w, h) == (21.0, 15.0)
    fold = PR.F.CROWN_TAB / 2
    loop = (y0 - fold) if y0 >= fold else (fold - y1 if y1 <= fold else 0.0)   # clear length, fold to box edge
    perim = 2 * (8.0 + 5.0)                                            # pom_toggle 30 x 8 x 5 cross-section
    assert loop == pytest.approx(13.0, abs=0.01) and 2 * loop >= perim
    assert y1 == pytest.approx(2 * fold - PR.BOX_TIP_GAP, abs=0.01)    # tip end
    ids = {w_["id"] for w_ in rsP.webbing}
    assert {"B-28t", "B-28s"} <= ids


def test_bl035_llt_box_matches_band_mark(rsP):
    llt = [(b[0], b[1]) for b in _boxes(rsP.pieces["LLT"])]
    band = [(b[0], b[1]) for b in _boxes(rsP.pieces["B-02h"]) if "LLT" in b[2]]
    assert llt == [PR.LLT_BOX] and band and all(b == PR.LLT_BOX for b in band)


def test_bl035_b24_capacity_uses_the_drawn_boxes(rsP):
    from huntkit.gendesign import attach_system as AS
    bx = [(b[0], b[1]) for b in _boxes(rsP.pieces["B-24"])]
    assert bx[0] == AS.LINK_HOOK_BOX and bx[1:] == [AS.LINK_LOOP_BOX] * 3
    import inspect
    src = inspect.getsource(AS.fab_parts) if hasattr(AS, "fab_parts") else inspect.getsource(AS)
    assert "box_x(*LINK_HOOK_BOX)" in src and "box_x(*LINK_LOOP_BOX)" in src      # the capacity row
    assert AS.box_x(*AS.LINK_HOOK_BOX)["cap_n"] > 941.0 * 4          # misuse 941 N: box-X is not the weak link


def test_bl035_muzzle_keeper_in_ledger_and_bom_inputs(rsP):
    mk = PR.F.muzzle_keeper()
    assert mk["qty"] == 2 and mk["cut_mm"] == pytest.approx(299.0)          # BL-041 MK-GAP: tabs 60 apart (was 70: 309)
    assert mk["mass_g"] == pytest.approx(2 * (299.0 * 6.0 / 1000 + 2.5), abs=0.01)    # shock_cord_3mm + cord_lock_spring
    row = [r for r in PR.ledger_rows() if r["name"].startswith("BL-035: rifle muzzle keepers")]
    assert len(row) == 1 and row[0]["g"] == pytest.approx(mk["mass_g"]) and row[0]["cfg"] == "base"
    w = [x for x in rsP.webbing if x["id"] == "MK-cord"]
    assert len(w) == 1 and w[0]["material_id"] == "shock_cord_3mm" and w[0]["qty"] == 2
    locks = sum(h["qty"] for h in rsP.hardware if h["material_id"] == "cord_lock_spring")
    assert locks == 1 + 2                                                # E-5 + 2 muzzle keepers
