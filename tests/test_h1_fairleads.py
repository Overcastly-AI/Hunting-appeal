"""BL-042: H1 fairleads complete on the print files, hinge eye clearance, slice check on the STL itself."""
import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import bag_attach as BA
from huntkit.gendesign import h1_fairleads as FL

REPO = Path(__file__).resolve().parents[1]
STL = REPO / "designs" / "pack_5200" / "print" / "frame_h1" / "h1_assembled.stl"
RES = REPO / "designs" / "pack_5200" / "analysis" / "h1_fairleads.json"


def _legacy_field(pts, stay_r):
    """bag_attach.fairlead_local as it stood on 2026-11-01 (module constants, root at y_hole - HOLE_D/2 - 0.8)."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    y_root, y_hole = stay_r - BA.EMBED, stay_r + BA.HOLE_PROUD
    y_tip = y_hole + BA.HOLE_D / 2 + BA.WALL_FRONT
    sdf = np.full(len(pts), 40.0)
    for s in (1.0, -1.0):
        a, b = s * BA.THROAT / 2, s * (BA.THROAT / 2 + BA.CHEEK)
        sdf = np.minimum(sdf, BA._box(pts, np.array([min(a, b), y_root, -BA.HALF_Z]), np.array([max(a, b), y_tip, BA.HALF_Z])))
    root = BA._box(pts, np.array([-(BA.THROAT / 2 + BA.CHEEK), y_root, -BA.HALF_Z]),
                   np.array([BA.THROAT / 2 + BA.CHEEK, y_hole - BA.HOLE_D / 2 - 0.8, BA.HALF_Z]))
    sdf = BA._smin(sdf, root, 3.0)
    hole = np.hypot(y - y_hole, z) - BA.HOLE_D / 2
    hole = np.where(np.abs(x) <= BA.THROAT / 2 + BA.CHEEK + 0.5, hole, 40.0)
    return np.maximum(sdf, -hole)


def test_default_field_unchanged():
    """geom=None reproduces the 2026-11-01 field (every voxel pipeline that unions it is unchanged)."""
    rng = np.random.default_rng(1)
    pts = rng.uniform([-22, -5, -14], [22, 30, 14], (20000, 3))
    for r in (9.35, 16.8):
        assert np.allclose(BA.fairlead_local(pts, r), _legacy_field(pts, r), atol=1e-9)
    assert BA.legacy_geom().gap_under_pin == pytest.approx(1.9)          # the review's Z-1 number


def test_hinge_envelope_meets_the_eye():
    """Z-1: 3 plies x 1.5 mm + 1 mm under the pin; throat clears the widest neck; constant matches the geometry."""
    g, e = BA.HINGE_GEOM, BA.HINGE_EYE_ENVELOPE
    # BL-049: the hinge floor is 1 mm lower (gap 6.5); BL-042's hinge had 5.5
    assert g.gap_under_pin == pytest.approx(6.5) and e["gap_under_pin_mm"] == pytest.approx(6.5)
    assert BA.HINGE_GEOM_BL042.gap_under_pin == pytest.approx(5.5)
    assert g.gap_under_pin >= 3 * 1.5 + 1.0 - 1e-9
    assert g.throat - e["neck_w_max_mm"] >= 1.0 - 1e-9 and g.throat - 18.0 == pytest.approx(2.0)
    assert e["pin_centre_above_stay_surface_mm"] == g.hole_proud
    assert e["stay_r_mm_at_z60"] == pytest.approx(float(__import__("huntkit.gendesign.frame_branch", fromlist=["x"])
                                                        .stay_radius(60.0, BA.SCALE)), abs=1e-3)
    # the design field itself leaves the eye (stepped ply stack + margin) clear under the pin, fillets included
    r = e["stay_r_mm_at_z60"]
    y_top = r + g.hole_proud - g.pin_d / 2
    for hw, t in e["eye_section_steps_mm"]:
        xs = np.linspace(-hw, hw, 41)
        ys = np.linspace(y_top - t - e["eye_margin_mm"], y_top - 1e-3, 41)
        X, Y = np.meshgrid(xs, ys)
        f = BA.fairlead_local(np.c_[X.ravel(), Y.ravel(), np.zeros(X.size)], r, g)
        assert (f > -1e-6).all(), (hw, t)            # touching the floor at exactly 1.0 mm margin is allowed


def test_pin_bending_closed_form():
    """Simply supported pin, load spread over b: M = F (2L - b) / 8; sigma = 32 M / (pi d^3)."""
    r = FL.pin_bending(1000.0, throat=20.0, cheek=8.0, pin_d=5.0, g_times_req=3.0)
    M = 1000.0 * (2 * 28.0 - 20.0) / 8.0
    assert r["M_nmm"] == pytest.approx(M)
    assert r["sigma_mpa"] == pytest.approx(32 * M / (math.pi * 125.0))
    # point load at mid-span (b -> 0): F L / 4
    assert FL.pin_bending(1000.0, 1e-9, 28.0, 5.0, 3.0)["M_nmm"] == pytest.approx(1000.0 * 28.0 / 4.0, rel=1e-6)


def test_fairlead_fea_reproduces_solve_fairlead():
    """The generalised FEA with the legacy geometry and no lateral load is bag_attach.solve_fairlead (rev C record)."""
    rc = json.loads((REPO / "designs/pack_5200/analysis/rev_c_verification_results.json").read_text())["attachments"]
    f = rc["gov_c"]["hinge"]
    r = FL.fairlead_fea(BA.legacy_geom(), 9.354545454545455, {"rc": [0.0, f["fy"], f["fz"]]}, h=1.0)
    # BL-045: the record now holds the BL-042 hinge; the legacy value it held is kept as bl045_previous_sf
    assert r["loads"]["rc"]["sf"] == pytest.approx(rc["bl045_previous_sf"]["hinge"], rel=1e-6)
    r2 = FL.fairlead_fea(BA.HINGE_GEOM_BL042, 9.354545454545455, {"rc": [0.0, f["fy"], f["fz"]]}, h=1.0)   # the record's
    assert r2["loads"]["rc"]["sf"] == pytest.approx(rc["fairlead_fea"]["hinge"]["sf"], rel=1e-6)
    s = BA.solve_fairlead(9.354545454545455, np.array([f["fy"], f["fz"]]), h=1.0)
    assert r["loads"]["rc"]["fi99"] == pytest.approx(s["fi99"], rel=1e-9)


def _stay_body():
    """A synthetic frame: one cylinder stay per fairlead station (both sides), as a manifold."""
    import manifold3d as m3d
    man = None
    for p in FL.placed():
        c = m3d.Manifold.cylinder(60.0, p["stay_r"], p["stay_r"], 64, center=True).translate((p["x"], p["yc"], p["z"]))
        man = c if man is None else man + c
    return man


def test_check_catches_clipped_and_passes_complete():
    """The slice check passes a body with add_fairleads and fails the same body clipped at y 15.46 (the Z-2 export)."""
    import manifold3d as m3d
    from huntkit.gendesign.surface import _from_manifold
    st = {}
    full = FL.add_fairleads(_stay_body(), log=None, stats=st)
    ok = FL.check_stl(_from_manifold(full))
    assert ok["all_pass"], {k: v for k, v in ok.items() if isinstance(v, dict) and not v["pass"]}
    assert ok["hinge_R"]["gap_under_pin"] == pytest.approx(BA.HINGE_EYE_ENVELOPE["gap_under_pin_mm"], abs=0.05)
    assert ok["hinge_R"]["eye_fits"]
    assert ok["im3_L"]["cheeks"]["out"]["cheek_height_mm"] == pytest.approx(28.0, abs=0.3)
    clip = full ^ m3d.Manifold.cube((400, 200, 700)).translate((-200, -184.54, -50))   # keep y <= 15.46
    bad = FL.check_stl(_from_manifold(clip))
    assert not bad["all_pass"]
    assert all(not bad[k]["pass"] for k in ("hinge_R", "hinge_L", "im1_R", "im3_R"))
    assert bad["hinge_R"]["cheeks"]["in"]["front_wall_mm"] == 0.0


def test_legacy_hinge_cannot_take_the_eye():
    """The 2026-11-01 hinge (1.9 mm gap, 18 mm throat) fails the eye envelope on the same synthetic body."""
    from huntkit.gendesign.surface import _from_manifold
    import huntkit.gendesign.h1_fairleads as M
    old = M.station_geom
    try:
        M.station_geom = lambda n: FL.legacy_geom_of(n)
        full = FL.add_fairleads(_stay_body(), log=None)
    finally:
        M.station_geom = old
    r = FL.check_stl(_from_manifold(full), geom_of=FL.legacy_geom_of)
    assert r["hinge_R"]["eye_overlap_mm2"] > 10.0 and not r["hinge_R"]["eye_fits"]


@pytest.mark.skipif(not STL.exists(), reason="print files not generated")
def test_print_files_have_complete_fairleads():
    """Z-2 on the shipped files: every fairlead passes the slice check; halves watertight, one shell each."""
    import trimesh
    r = FL.check_stl(STL)
    assert r["all_pass"], {k: v for k, v in r.items() if isinstance(v, dict) and not v["pass"]}
    for k in ("hinge_L", "hinge_R"):
        assert r[k]["gap_under_pin"] >= 5.5 - 0.3 and r[k]["throat_min_w"] >= 20.0 - 0.2 and r[k]["eye_fits"]
    for k in ("im3_L", "im3_R"):                                     # the 28 mm IM3 cheek is still there
        assert all(c["cheek_height_mm"] >= 27.5 for c in r[k]["cheeks"].values())
    m = trimesh.load(STL)
    assert m.is_watertight and m.bounds[1][1] > 25.0                  # no longer clipped at y 15.46
    for nm in ("lower", "upper"):
        h = trimesh.load(STL.parent / f"h1_{nm}_flat.stl")
        assert h.is_watertight and len(h.split(only_watertight=False)) == 1


@pytest.mark.skipif(not STL.exists(), reason="print files not generated")
def test_print_halves_fit_the_h2s_bed():
    """BL-050: the US2 outer clevis is a bolt-on piece (h1_bedfit) and the halves are written turned on the plate.
    (BL-049 had this as a strict xfail: the US2 lugs made the lower half 367.5 mm wide.)"""
    import trimesh
    for nm in ("lower", "upper"):
        h = trimesh.load(STL.parent / f"h1_{nm}_flat.stl")
        assert sorted(h.extents)[-1] <= 340 and sorted(h.extents)[-2] <= 320


@pytest.mark.skipif(not RES.exists(), reason="h1_fairleads.json not written")
def test_results_record():
    """Cheek strength kept (rev C and sim loads), test pieces pass, body checks re-run, mass booked."""
    from huntkit.mass import ledger as L
    d = json.loads(RES.read_text())
    leg, new = d["fea"]["legacy"], d["fea"]["bl042"]
    assert new["revC_sf"] >= leg["revC_sf"] and new["revC_fatigue"] >= leg["revC_fatigue"]
    assert new["revC_fatigue"] >= 1.15 and new["sim_worst"]["fatigue"] >= 1.15 > leg["sim_worst"]["fatigue"]
    assert new["pin_revC"]["sf_yield"] >= 1.0 and new["pin_sim"]["sf_fatigue"] >= 1.0
    assert d["check_after"]["all_pass"] and not d["check_before"]["all_pass"]
    for nm in ("hinge", "im3"):
        pc = d["pieces"][nm]
        assert pc["watertight"] and pc["shells"] == 1 and pc["slice_check"]["pass"]
    for b, v in d["body"]["bases"].items():
        for k in ("strength", "fatigue", "creep", "buckling"):
            assert v["after"][k] >= v["before"][k] - 0.02, (b, k)
    rows = L.corrections("corrie_b2_h1", "M")["H1F"]
    assert len(rows) == 1 and rows[0]["g"] == pytest.approx(d["mass"]["net_g"]) and rows[0]["system"] == "frame"
    assert L.corrections("corrie_b2_today", "M")["H1F"] == []
    # BL-045's boss-core fix adds about 2.6 g of skin round the four bolt bosses (not fairlead mass)
    assert d["mass"]["net_g"] == pytest.approx(d["assembled"]["g_after"] - d["assembled"]["g_before"] - 2.6, abs=1.0)
