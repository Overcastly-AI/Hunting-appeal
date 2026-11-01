"""Tests for huntkit.patterns (pattern engine)."""
import itertools
import math
import re

import ezdxf
import numpy as np
import pytest

from huntkit.patterns import (GradeRules, Piece, Seam, SeamMismatchError, bezier, box_bag,
                              box_bag_volume, check_seams, cut_list, cylinder, dart_seams,
                              darted_panel, develop_ruled_surface, export_dxf, export_pdf_tiled,
                              export_svg, grade, nest, rect_panel, tapered_panel)
from huntkit.patterns.export_pdf import MM


# ------------------------------------------------------------------ seam allowance
def test_uniform_seam_allowance_offset():
    p = rect_panel("r", 200, 100, 0, seam_allowance_mm=10)
    x0, y0, x1, y1 = p.bounds()
    assert (x0, y0, x1, y1) == pytest.approx((-10, -10, 210, 110))
    assert p.area_mm2 == pytest.approx(220 * 120)
    assert p.seam_area_mm2 == pytest.approx(200 * 100)


def test_per_edge_seam_allowance_offset():
    p = rect_panel("r", 200, 100, 0, seam_allowance_mm={"default": 10, "top": 25, "left": 0})
    x0, y0, x1, y1 = p.bounds()
    assert (x0, y0, x1, y1) == pytest.approx((0, -10, 210, 125))
    assert p.area_mm2 == pytest.approx(210 * 135)
    # cut-line vertices above the top edge sit exactly 25 mm out; left edge has none (0 SA)
    assert all(q[1] == pytest.approx(125) for q in p.cut_line() if q[1] > 100)
    assert min(q[0] for q in p.cut_line()) == pytest.approx(0)


def test_curved_edge_offset_distance():
    curve = bezier((0, 0), (60, 80), (140, 80), (200, 0), n=60)
    p = Piece.from_edges("arch", [("arch", curve), ("base", [(200, 0), (0, 0)])],
                         seam_allowance_mm=12)
    from shapely.geometry import Point
    seam = p.seam_polygon().exterior
    d = [seam.distance(Point(q)) for q in p.cut_line()]
    assert min(d) == pytest.approx(12, abs=0.05)
    assert max(d) <= 12 * 4.0 + 1e-6  # miter limit respected


def test_unknown_edge_allowance_rejected():
    with pytest.raises(KeyError):
        rect_panel("r", 100, 100, seam_allowance_mm={"nope": 5})


# ------------------------------------------------------------------ mirror
def test_mirrored_piece():
    p = tapered_panel("t", 200, 120, 300, align="left", seam_allowance_mm={"default": 10,
                                                                            "right": 20},
                      quantity=2, mirror=True, grain=80)
    p.add_notch_on_edge("right", 0.5)
    p.add_drill_hole(30, 40)
    m = p.mirrored()
    assert m.seam_area_mm2 == pytest.approx(p.seam_area_mm2)
    assert m.area_mm2 == pytest.approx(p.area_mm2)
    assert m.seam_polygon().exterior.is_ccw
    assert set(m.edge_names) == set(p.edge_names)
    for e in p.edge_names:
        assert m.edge_length(e) == pytest.approx(p.edge_length(e))
        assert m.allowance(e) == p.allowance(e)
    # mirror about x: x coords flip around the bbox centre, y unchanged
    xc = 100.0
    assert m.drill_holes[0].xy == pytest.approx((2 * xc - 30, 40))
    assert m.grain == pytest.approx(100.0)
    # mirroring twice is the identity
    mm = m.mirrored()
    assert mm.seam_polygon().equals_exact(p.seam_polygon().normalize(), 1e-6) or \
        mm.seam_polygon().symmetric_difference(p.seam_polygon()).area < 1e-6
    inst = p.instances()
    assert len(inst) == 2 and [f for _, f in inst] == [False, True]
    assert "1 PAIR" in " ".join(p.label_lines())


# ------------------------------------------------------------------ seams
def test_seam_matching_detection():
    a = rect_panel("a", 300, 400)
    b = rect_panel("b", 100, 400)
    c = rect_panel("c", 100, 395)
    ok = Seam(a.edge("right"), b.edge("left").reversed())
    bad = Seam(a.edge("left"), c.edge("right"))
    eased = Seam(a.edge("left"), c.edge("right"), ease_mm=5)
    rep = check_seams([ok, bad, eased])
    assert not rep.ok
    assert [r.seam for r in rep.mismatches] == [bad]
    assert rep.mismatches[0].error_mm == pytest.approx(5)
    assert "MISMATCH" in str(rep)
    with pytest.raises(SeamMismatchError):
        check_seams([bad], raise_on_error=True)
    assert check_seams([ok, eased]).ok


def test_seam_multi_edge_side_and_notches():
    bag = box_bag(300, 400, 150, 60)
    rep = check_seams(bag.seams, tol_mm=0.01)
    assert rep.ok, str(rep)
    # bottom perimeter vs the three edges it meets on the front side (single edge here)
    s = Seam([bag.pieces["side_left"].edge("bottom"), bag.pieces["side_right"].edge("bottom")],
             [bag.pieces["bottom"].edge("left"), bag.pieces["bottom"].edge("right")])
    assert check_seams([s]).ok
    # match notches added on both sides
    assert bag.pieces["front"].notches and bag.pieces["side_right"].notches


def test_dart_and_cylinder_seams():
    d = darted_panel("d", 400, 300, 40, 100, n_darts=2)
    assert check_seams(dart_seams(d)).ok
    assert d.cut_polygon().is_valid
    cyl = cylinder(200, 300, rolltop_mm=150)
    assert check_seams(cyl.seams).ok
    assert cyl.volume_mm3() == pytest.approx(math.pi * 100**2 * 300, rel=2e-3)


# ------------------------------------------------------------------ volume
@pytest.mark.parametrize("W,H,D,r", [(300, 400, 150, 0), (300, 400, 150, 60), (250, 500, 200, 120)])
def test_box_bag_volume_vs_analytic(W, H, D, r):
    bag = box_bag(W, H, D, r)
    analytic = (W * H - 2 * (1 - math.pi / 4) * r * r) * D
    vol = box_bag_volume(bag.pieces["front"], bag.pieces["side_left"])
    assert vol == pytest.approx(analytic, rel=1e-3)
    assert check_seams(bag.seams).ok


def test_develop_ruled_surface_cylinder_and_cone():
    t = np.linspace(0, math.pi, 80)
    A = np.c_[100 * np.cos(t), 100 * np.sin(t), 0 * t]
    B = np.c_[100 * np.cos(t), 100 * np.sin(t), 0 * t + 200]
    dev = develop_ruled_surface(A, B, n=80)
    assert dev.max_strain < 1e-9
    piece = dev.to_piece("half_cyl")
    # flattened half cylinder = rectangle (polyline circumference) x 200
    assert piece.edge_length("a") == pytest.approx(dev.length_a_3d, rel=1e-6)
    assert piece.seam_area_mm2 == pytest.approx(dev.length_a_3d * 200, rel=1e-4)
    # cone frustum: developable, slant-preserving
    B2 = np.c_[50 * np.cos(t), 50 * np.sin(t), 0 * t + 150]
    dev2 = develop_ruled_surface(A, B2, n=80)
    assert dev2.max_strain < 1e-9
    assert dev2.to_piece("cone").edge_length("b") == pytest.approx(dev2.length_b_3d, rel=1e-6)


# ------------------------------------------------------------------ grading
def test_point_grading_deltas():
    p = rect_panel("f", 300, 400, size="M")
    p.add_notch_on_edge("top", 0.5)
    rules = {"sizes": ["S", "M", "L", "XL"], "base": "M",
             "points": {"br": (10, 0), "tr": (10, 15), "tl": {"S": (0, -12), "L": (0, 15),
                                                              "XL": (0, 32)}}}
    g = grade(p, rules)
    assert list(g) == ["S", "M", "L", "XL"]
    for sz, k in (("S", -1), ("M", 0), ("L", 1), ("XL", 2)):
        gp = g[sz]
        assert gp.size == sz
        assert gp.points["br"] == pytest.approx((300 + 10 * k, 0))
        assert gp.points["tr"] == pytest.approx((300 + 10 * k, 400 + 15 * k))
        assert gp.points["bl"] == pytest.approx((0, 0))
        assert gp.edge_length("bottom") == pytest.approx(300 + 10 * k)
        assert gp.edge_names == p.edge_names
    assert g["XL"].points["tl"] == pytest.approx((0, 432))
    # notch on top edge moved with the edge (interpolated)
    assert g["L"].notches[0].y == pytest.approx(415)


def test_proportional_grading_fallback():
    p = rect_panel("f", 200, 100)
    g = grade(p, GradeRules(sizes=["S", "M", "L"], base="M", scale_step=(0.1, 0.05)))
    assert g["L"].edge_length("bottom") == pytest.approx(220)
    assert g["S"].edge_length("left") == pytest.approx(95)
    with pytest.raises(ValueError):
        grade(p, {"sizes": ["S", "M"], "base": "M"})


def test_graded_seams_still_match():
    from huntkit.patterns.cli import grade_stuff_sack
    for sz, (pieces, seams) in grade_stuff_sack().items():
        assert check_seams(seams).ok, sz


# ------------------------------------------------------------------ exports
def _demo_pieces():
    from huntkit.patterns.cli import build_stuff_sack
    return build_stuff_sack()


def test_dxf_round_trip(tmp_path):
    pieces, _ = _demo_pieces()
    pieces[0].add_internal_line([(0, 100), (100, 100)], "placement")
    path = export_dxf(pieces, tmp_path / "p.dxf")
    doc = ezdxf.readfile(path)
    assert doc.header["$INSUNITS"] == 4
    for lay in ("CUT", "SEW", "NOTCH", "GRAIN", "DRILL", "TEXT"):
        assert lay in doc.layers
    refs = list(doc.modelspace().query("INSERT"))
    assert len(refs) == 3
    for ref, piece in zip(refs, pieces):
        blk = doc.blocks[ref.dxf.name]
        cuts = [e for e in blk if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT"]
        assert len(cuts) == 1
        pts = [tuple(v[:2]) for v in cuts[0].get_points()]
        from shapely.geometry import Polygon
        assert Polygon(pts).area == pytest.approx(piece.area_mm2, rel=1e-6)
        texts = " ".join(e.dxf.text for e in blk if e.dxftype() == "TEXT")
        assert piece.piece_id in texts and "FACE UP" in texts
        assert any(e.dxf.layer == "NOTCH" for e in blk)
        assert any(e.dxf.layer == "GRAIN" for e in blk)
    assert any(e.dxf.layer == "DRILL" for e in doc.blocks[refs[0].dxf.name])


@pytest.mark.parametrize("paper,size_pt", [("letter", (612, 792)), ("a4", (595.2756, 841.8898))])
def test_pdf_tiled_true_scale(tmp_path, paper, size_pt):
    pieces, _ = _demo_pieces()
    path = tmp_path / f"t_{paper}.pdf"
    info = export_pdf_tiled(pieces, path, paper=paper)
    data = path.read_bytes().decode("latin-1")
    assert info["pages"] == info["rows"] * info["cols"] + 1 and info["pages"] > 1
    # 100 mm square = 283.4646 pt, 4 in = 288 pt, on every page, with no scaling CTM
    sq100 = re.findall(r"[-\d.]+ [-\d.]+ 283\.464\d* 283\.464\d* re", data)
    sq4in = re.findall(r"[-\d.]+ [-\d.]+ 288 288 re", data)
    assert len(sq100) == info["pages"] and len(sq4in) == info["pages"]
    assert 100 * MM == pytest.approx(283.4646, abs=1e-4)
    for m in re.finditer(r"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) [-\d.]+ [-\d.]+ cm", data):
        a, b, c, d = map(float, m.groups())
        assert (a, b, c, d) == (1, 0, 0, 1), "unexpected scaling transform"
    boxes = re.findall(r"/MediaBox \[ 0 0 ([\d.]+) ([\d.]+) \]", data)
    assert len(boxes) == info["pages"]
    assert all(float(w) == pytest.approx(size_pt[0], abs=0.01) and
               float(h) == pytest.approx(size_pt[1], abs=0.01) for w, h in boxes)


def test_pdf_large_format_single_sheet(tmp_path):
    pieces, _ = _demo_pieces()
    info = export_pdf_tiled(pieces, tmp_path / "a0.pdf", paper="a0")
    assert info["single_sheet"] and info["pages"] == 1
    info = export_pdf_tiled(pieces, tmp_path / "p36.pdf", paper="plotter36")
    assert info["single_sheet"] and info["page_size_mm"][0] == pytest.approx(914.4)


def test_svg_export(tmp_path):
    pieces, _ = _demo_pieces()
    path = export_svg(pieces, tmp_path / "laser.svg")
    txt = path.read_text()
    assert 'id="CUT"' in txt and "#FF0000" in txt and 'mm"' in txt


# ------------------------------------------------------------------ nesting
@pytest.mark.parametrize("grain", [True, False])
def test_marker_no_overlap_within_width(grain):
    from huntkit.patterns.cli import grade_stuff_sack
    pieces = [p for ps, _ in grade_stuff_sack().values() for p in ps]
    extra = tapered_panel("wing", 300, 150, 250, quantity=2, mirror=True, grain=75,
                          material_id=pieces[0].material_id)
    pieces.append(extra)
    W, sel, gap = 1000.0, 15.0, 3.0
    m = nest(pieces, W, grain_constraint=grain, selvedge_mm=sel, spacing_mm=gap, units=2)
    n_expected = 2 * sum(p.quantity for p in pieces)
    assert len(m.placements) == n_expected and not m.unplaced
    polys = [pl.polygon for pl in m.placements]
    for p in polys:
        x0, y0, x1, y1 = p.bounds
        assert y0 >= sel - 1e-6 and y1 <= W - sel + 1e-6 and x0 >= -1e-6
    for a, b in itertools.combinations(polys, 2):
        assert a.intersection(b).area < 1e-6
        assert a.distance(b) >= gap - 0.01
    assert 0 < m.efficiency < 1
    assert m.length_mm == pytest.approx(max(p.bounds[2] for p in polys))
    assert m.yield_m_per_unit == pytest.approx(m.length_mm / 1000 / 2)
    if grain:
        # grain lines parallel to the warp (marker x axis)
        for pl in m.placements:
            assert pl.piece.grain % 180 == pytest.approx(0, abs=1e-6) or \
                pl.piece.grain % 180 == pytest.approx(180, abs=1e-6)
    # mirrored halves present
    assert sum(pl.mirrored for pl in m.placements) == 2


def test_marker_exports(tmp_path):
    pieces, _ = _demo_pieces()
    m = nest(pieces, 1420, units=1)
    assert m.export_pdf(tmp_path / "m.pdf").stat().st_size > 1000
    doc = ezdxf.readfile(m.export_dxf(tmp_path / "m.dxf"))
    assert len(doc.modelspace().query('LWPOLYLINE[layer=="CUT"]')) == 3


def test_nest_rejects_mixed_materials():
    a = rect_panel("a", 100, 100, material_id="x")
    b = rect_panel("b", 100, 100, material_id="y")
    with pytest.raises(ValueError):
        nest([a, b], 1000)


# ------------------------------------------------------------------ cut list
def test_cut_list():
    p = rect_panel("panel", 200, 100, 0, seam_allowance_mm=10, quantity=2, mirror=True,
                   material_id="robic_210d_ripstop", size="M")
    cl = cut_list([p])
    row = cl.rows[0]
    assert row["area_m2"] == pytest.approx(0.0264)
    assert row["total_area_m2"] == pytest.approx(0.0528)
    assert row["perimeter_mm"] == pytest.approx(680)
    assert row["mirror"] == "L+R"
    assert "piece_id" in cl.csv().splitlines()[0]
    assert "| PANEL |" in cl.markdown()


def test_demo_runs(tmp_path):
    from huntkit.patterns.cli import demo
    res = demo(tmp_path / "demo")
    assert res["seams"].ok and res["graded_seams"].ok
    for f in ("stuff_sack_M.dxf", "stuff_sack_M_tiled_letter.pdf", "marker_SML.pdf",
              "marker_SML.dxf", "cut_list.csv", "cut_list.md"):
        assert (tmp_path / "demo" / f).exists()
