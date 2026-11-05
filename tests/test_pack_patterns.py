"""Pack 5200 v3.1 production patterns (designs/pack_5200/patterns_v31.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import develop_region, develop_ruled_surface, nest  # noqa: E402


@pytest.fixture(scope="module")
def ps():
    import patterns_v31 as PV
    return PV.build(spacing=14.0)


def test_every_piece_is_complete(ps):
    for pid, p in ps.pieces.items():
        assert p.material_id, pid
        MAT.load(p.material_id)                       # material record exists
        assert p.piece_id == pid and p.name
        assert p.quantity >= 1
        if p.mirror:
            assert p.quantity % 2 == 0, pid
        g0, g1 = p.grain_arrow()
        assert np.hypot(g1[0] - g0[0], g1[1] - g0[1]) > 5, pid
        assert any(t.startswith("ID:") for t in p.label_lines())
        assert p.knife_direction
        assert p.cut_polygon().is_valid and p.area_mm2 >= p.seam_area_mm2 - 1e-6, pid


def test_no_frame_or_spreader_pieces(ps):
    assert "BP-06" not in ps.pieces                   # carbon spreader: printed/cut part, other owner
    assert not any(p.material_id.startswith(("cfrp", "pa12_cf", "pa6_cf")) for p in ps.pieces.values())


def test_seams_match(ps):
    import patterns_v31 as PV
    rep, graded = PV.seam_report(ps)
    assert rep.ok, str(rep.mismatches)
    assert len(rep.results) >= 60
    for s, g in graded.items():
        assert g.ok, (s, str(g.mismatches))
    assert set(graded) >= {"S", "M", "L", "XL", "strap-J", "strap-S"}


def test_flattening_strain_under_2pct(ps):
    body = ["B-01", "B-01b", "B-01u", "B-02a", "B-02b", "B-02c", "B-02d", "B-03", "F-01a", "F-01b", "F-01c"]
    for pid in body:
        st = ps.strain[pid]
        assert st["p99_pct"] <= 2.0, (pid, st)
        assert st["folded"] == 0, pid
    for pid in ("B-13", "B-14a", "B-14b", "B-15a", "B-15b", "D-01", "R-01"):
        assert ps.strain[pid]["p99_pct"] < 0.1, pid      # ruled / conical: developable


def test_volume_rebuilt_from_flats(ps):
    import patterns_v31 as PV
    v = PV.volume_check(ps)
    assert v["design_L"] == pytest.approx(85.16, abs=0.05)
    assert v["pattern_total_L"] == pytest.approx(85.2, abs=1.0)    # R-01: 85.2 +/- 1 L
    assert abs(v["pattern_body_L"] - v["master_surface_body_L"]) < 0.3
    assert v["collar_fits"]


def test_eight_swells_and_ports(ps):
    w = ps.swell_windows
    assert len(w) == 8
    assert {(s["station"], s["side"]) for s in w} == {(k, sd) for k in ("hinge", "im1", "im2", "im3") for sd in "LR"}
    for s in w:
        assert s["height"] == 16.0 and s["length"] == pytest.approx(90.0)
    b01 = ps.pieces["B-01"]
    assert sum(1 for l in b01.internal_lines if l.kind == "cut_inside") == 8
    assert ps.pieces["B-12"].quantity == 6
    caps = sum(ps.pieces[k].quantity for k in ("B-13", "B-14a", "B-14b", "B-15a", "B-15b"))
    assert caps == 16


def test_grading(ps):
    import patterns_v31 as PV
    h = ps.graded["H-01"]
    assert list(h) == ["S", "M", "L", "XL"]
    lens = [h[s].bounds(cut=False)[2] - h[s].bounds(cut=False)[0] for s in h]
    want = [PV.WING_LEN[s] for s in h]
    assert np.allclose(lens, want, atol=0.5)
    assert np.allclose(np.diff([h[s].edge_length("root") for s in h]), 0, atol=1e-6)   # root constant
    st = ps.graded["HS-1"]
    assert set(st) == {"J", "S"} and st["S"].piece_id == "HS-S1"
    assert st["J"].edge_length("top") == pytest.approx(st["S"].edge_length("top"), abs=0.5)


def test_notches_on_long_seams(ps):
    for pid in ("B-01", "B-03", "B-02b", "B-05", "B-06"):
        assert len(ps.pieces[pid].notches) >= 10, pid
    assert len(ps.pieces["B-01"].drill_holes) >= 8 * 4


def test_marker_fits_roll_width(ps):
    p = ps.pieces["B-03"]
    rw = float(MAT.load(p.material_id).require("roll_width_mm"))
    uw = float(MAT.load(p.material_id).require("usable_width_mm"))
    mk = nest([ps.pieces[k] for k in ("B-03", "B-02a", "B-02b")], rw, selvedge_mm=(rw - uw) / 2)
    assert not mk.unplaced and 0.3 < mk.efficiency <= 1.0


def test_develop_region_cylinder_is_exact():
    R = 100.0
    surf = lambda uv: np.column_stack([R * np.cos(uv[:, 0] / R), R * np.sin(uv[:, 0] / R), uv[:, 1]])  # noqa: E731
    fm = develop_region(surf, [(0, 0), (200, 0), (200, 300), (0, 300)], spacing=20)
    assert fm.strain_stats()["max_pct"] < 0.5          # chord-triangulation noise only
    assert fm.area_flat == pytest.approx(200 * 300, rel=1e-3)
    sph = lambda uv: np.column_stack([R * np.sin(uv[:, 1] / R) * np.cos(uv[:, 0] / R),  # noqa: E731
                                      R * np.sin(uv[:, 1] / R) * np.sin(uv[:, 0] / R), R * np.cos(uv[:, 1] / R)])
    fs = develop_region(sph, [(0, 80), (120, 80), (120, 200), (0, 200)], spacing=15)
    assert fs.strain_stats()["max_pct"] > 2.0          # a sphere patch is not developable


def test_develop_ruled_surface_keeps_correspondence():
    t = np.linspace(0, 1, 30)
    A = np.column_stack([t * 100, np.zeros(30), np.zeros(30)])
    B = np.column_stack([t ** 2 * 100, np.full(30, 50.0), np.zeros(30)])
    d = develop_ruled_surface(A, B, resample=False)
    assert len(d.edge_a) == 30
    assert np.allclose(np.linalg.norm(d.edge_b - d.edge_a, axis=1), np.linalg.norm(B - A, axis=1), atol=1e-6)


def test_greedy_nest_places_everything(ps):
    """time_limit_s=0 forces the greedy mode from the first piece: nothing may be left unplaced."""
    pcs = [p for p in ps.all_pieces(kit={"base"}, sizes={"M", "J"}) if p.material_id == "cordura_330d_nylon66"]
    rw = float(MAT.load("cordura_330d_nylon66").require("roll_width_mm"))
    uw = float(MAT.load("cordura_330d_nylon66").require("usable_width_mm"))
    mk = nest(pcs, rw, selvedge_mm=(rw - uw) / 2, units=2, time_limit_s=0.0)
    assert not mk.unplaced and len(mk.placements) == 2 * sum(p.quantity for p in pcs)
    polys = [pl.polygon for pl in mk.placements]
    for i, a in enumerate(polys):
        for b in polys[i + 1:]:
            assert a.distance(b) >= 2.9
