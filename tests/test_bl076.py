"""BL-076 (huntkit.gendesign.bl076): the hip bearing plates that replace the BL-073 ring (plate-on-foundation model
verified against closed forms, laser-cut rules, lightest passing option, files), the SHARE-GAUGE algebra, the spool
count read from the BL-074 build output, and the 'Open items' section of bl070_h1p.md."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import bl070_h1p as P
from huntkit.gendesign import bl073_hotwet as B
from huntkit.gendesign import bl076 as X

REC = P.REC_JSON
has_rec = REC.exists() and "bl076" in json.loads(REC.read_text())


# ------------------------------------------------------------------------------------------------ solver checks
def test_plate_on_winkler_point_load_closed_form():
    """Infinite plate on a Winkler foundation, point load P: w0 = P / (8 sqrt(k D)) (Hetenyi / Timoshenko). A large
    disc through the BL-076 model path (tributary springs, bilateral as the closed form, no rigid zones) reproduces it
    (< 2 %); with compression-only springs the plate lifts off the kei lobe and w0 reads ~5 % higher."""
    from shapely.geometry import Point
    from huntkit.fea.plate_grid import iso_D
    t, k0, Pn, h = 1.6, 244.0, 100.0, 0.25
    pl, act, rig, trib, nodes = X._model(Point(0, 0).buffer(30.0, 128), t, k0, h, rigid=False, unilateral=False)
    f = pl.load_vector(point=[(0.0, 0.0, Pn)])
    r = pl.solve(f)
    al = X._al()
    D = iso_D(al["E"], t, al["nu"])[0, 0]
    w0 = Pn / (8 * math.sqrt(k0 * D))
    assert r["w"].max() == pytest.approx(w0, rel=0.02)
    assert r["spring_force"].sum() == pytest.approx(Pn, rel=1e-6)
    pl2, *_ = X._model(Point(0, 0).buffer(30.0, 128), t, k0, h, rigid=False, unilateral=True)
    w_uni = pl2.solve(pl2.load_vector(point=[(0.0, 0.0, Pn)]))["w"].max()
    assert w0 < w_uni < 1.08 * w0


def test_stiff_plate_bears_as_a_rigid_body():
    """A near-rigid plate (t 40) on the springs: each arc plate's pressure is the rigid-body field p = k (a + b x +
    c y) from force and moment equilibrium of its own 4 nut loads on its own springs (closed form, < 2 %)."""
    d = {**X.design(), "t": 40.0}
    k0 = X.foundations()["cold"]
    F = 500.0
    r = X.plate_solve(d, [F] * 8, k0, 0.4, rigid=False, unilateral=False)
    pl, act, rig, trib, nodes = X._model(X.outline(d), d["t"], k0, 0.4, rigid=False, unilateral=False)
    xy, A = r["_xy"], trib[nodes]
    assert r["reaction_n"] == pytest.approx(8 * F, rel=1e-6)
    bolts = np.asarray(X.bolt_xy())
    for side in (1.0, -1.0):
        m = np.sign(xy[:, 0]) == side
        Ai, xi, yi = A[m], xy[m, 0], xy[m, 1]
        G = np.array([[Ai.sum(), (Ai * xi).sum(), (Ai * yi).sum()],
                      [(Ai * xi).sum(), (Ai * xi * xi).sum(), (Ai * xi * yi).sum()],
                      [(Ai * yi).sum(), (Ai * xi * yi).sum(), (Ai * yi * yi).sum()]])
        bb = bolts[np.sign(bolts[:, 0]) == side]
        rhs = F * np.array([len(bb), bb[:, 0].sum(), bb[:, 1].sum()])
        coef = np.linalg.solve(G, rhs)                 # pressure field p = c0 + c1 x + c2 y
        p_rigid = coef[0] + coef[1] * xi + coef[2] * yi
        assert r["_p"][m].max() == pytest.approx(p_rigid.max(), rel=0.02)
        assert r["_p"][m].min() == pytest.approx(p_rigid.min(), rel=0.03)


def test_superposition_matches_the_nonlinear_solve():
    """checks() superposes bilateral unit fields; at the design load every spring is in compression, so the
    unilateral solve gives the same peak bearing."""
    d, tq = X.design(), B.TORQUE_NM
    c = X.checks(d, tq, 0.25)
    F = X.preload(tq)["max"]
    r = X.plate_solve(d, [F] * 8, X.foundations()["cold"], 0.25)
    assert c["min_contact_pressure_mpa"] > 0.0
    assert r["p_max"] == pytest.approx(c["p_per_n_cold"] * F, rel=0.01)


# ------------------------------------------------------------------------------------------------ the plates
def test_bl073_ring_fails_the_laser_guide_and_the_new_plates_pass():
    old = X.options()[0]
    lo = X.laser_rules(old)
    assert X.ligaments(old)["outer_mm"] == pytest.approx(1.75) and not lo["edge_ok_1p5t"]
    d = X.design()
    lr = X.laser_rules(d)
    lg = X.ligaments(d)
    assert lr["ok"] and lr["stock_gauge"] and lr["fits_spot_face"] and lr["hole_ok"]
    assert d["t"] == pytest.approx(0.063 * 25.4, abs=0.01)
    for k in ("outer_mm", "inner_mm", "end_mm"):
        assert lg[k] >= 1.5 * d["t"] - 1e-9, k
    # in the D49 spot face no 2 mm part can meet 1.5 t on the outer ligament
    assert (B.SPOT_D / 2 - X.SPOT_CLEAR - 19.0 - B.HOLE_D / 2) < 1.5 * 2.03


def test_chosen_is_the_lightest_passing_option_and_bl073_carries_it():
    res = X.search()
    ch = X.choose(res)
    assert X._key(ch["design"]) == X._key(X.design())
    assert ch["torque_nm"] == pytest.approx(B.TORQUE_NM)
    lighter = [r for r in res if r["g"] < ch["g"]]
    assert all(not (r["ok"] and X.checks(r["design"], r["torque_nm"], X.FE_H)["pass"] and X.study_ok(r["design"], r["torque_nm"]))
               for r in lighter)
    assert ch["g"] < 0.5 * X.mass_g(X.options()[0])


def test_plate_rows_pass_at_the_design_torque():
    c = X.checks(X.design(), B.TORQUE_NM)
    assert c["pass"]
    assert c["bearing_min"]["strength"] >= 1.5 and c["bearing_min"]["fatigue"] >= 1.15 and c["bearing_min"]["creep"] >= 1.5
    assert c["bending_sf"] >= 1.5 and c["plate_fatigue_sf"] >= 1.15
    assert min(c["punch_sf"], c["tearout_sf"], c["hole_bearing_sf"], c["nut_face_sf"]) >= 1.5
    assert c["closed_at_walk"] and c["residual_preload_min_n"] >= X.CLOSE_MARGIN * c["walk_t_n"]
    assert X.study_ok(X.design(), B.TORQUE_NM)
    # one torque step up fails a row (the torque is the highest passing step)
    assert not X.checks(X.design(), B.TORQUE_NM + 0.05)["pass"]


def test_hip_plate_uses_the_plate_model():
    hp = B.hip_plate()
    assert hp["pressure_mpa_per_kn"] / 1e3 == pytest.approx(X.checks(X.design(), B.TORQUE_NM)["p_per_n_cold"], rel=1e-3)
    assert hp["pressure_mpa_per_kn"] > hp["hetenyi"]["mpa_per_n"] * 1e3       # the 1D read was optimistic
    assert hp["pass"] and hp["webs"]["ring_outer_ligament_mm"] >= 1.5 * B.RING_T
    assert hp["screw"]["screw_l_mm"] == 35


def test_hip_parts_files(tmp_path):
    import ezdxf
    import trimesh
    out = B.hip_parts(tmp_path)
    doc = ezdxf.readfile(tmp_path / "hip_bearing_ring.dxf")
    msp = doc.modelspace()
    polys = [e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUT"]
    circ = [e for e in msp if e.dxftype() == "CIRCLE" and e.dxf.layer == "CUT"]
    assert len(polys) == 2 and all(p.closed for p in polys)
    assert len(circ) == 8 and all(c.dxf.radius == pytest.approx(B.HOLE_D / 2) for c in circ)
    rmax = max(math.hypot(x, y) for p in polys for x, y, *_ in p.get_points())
    assert rmax <= B.SPOT_D / 2 - X.SPOT_CLEAR + 1e-6
    for c in circ:                                       # every hole sits inside a plate with >= 1.5 t of metal round it
        from shapely.geometry import Point, Polygon
        hole = Point(c.dxf.center[0], c.dxf.center[1]).buffer(B.HOLE_D / 2 + 1.5 * B.RING_T - 1e-3)
        assert any(Polygon([(x, y) for x, y, *_ in p.get_points()]).contains(hole) for p in polys)
    m = trimesh.load(tmp_path / "hip_bearing_ring.stl", force="mesh")
    assert m.is_watertight and m.extents[2] == pytest.approx(B.RING_T)
    assert out["hip_bearing_ring"]["pieces"] == 2
    assert out["hip_bearing_ring"]["g"] == pytest.approx(X.mass_g(X.design()), rel=0.01)


# ------------------------------------------------------------------------------------------------ SHARE-GAUGE
def test_share_line_algebra_recovers_the_share():
    g = {"read": {"inner": {"mpa_per_n": -0.4, "near_mpa_per_n": [-0.39, -0.4, -0.41]},
                  "outer": {"mpa_per_n": -1.0, "near_mpa_per_n": [-1.0, -1.0, -1.0]},
                  "both": {"mpa_per_n": -0.7}},
         "site": {"x": 0.0}, "cheek_x": {"inner": 24.0, "outer": 52.0}}
    sl = X.share_line(g, 0.79)
    u0, u1 = -0.4, -1.0
    for s in (0.0, 0.3, 0.6, 0.79, 1.0):
        u = (1 - s) * u0 + s * u1
        assert (u - u0) / (u1 - u0) == pytest.approx(s)
        assert u / u1 == pytest.approx(s + (1 - s) * sl["r_point"])         # the BL-074 rule over-reads
    assert sl["pass_ratio_no_u0"] == pytest.approx(math.floor((0.39 + 0.79 * 0.61) * 100) / 100)
    assert sl["superposition_check"] == pytest.approx(1.0)


@pytest.mark.skipif(not has_rec, reason="run python -m huntkit.gendesign.bl076 report")
def test_share_gauge_record():
    sg = json.loads(REC.read_text())["bl076"]["share_gauge"]
    assert sg["linear"] and not sg["proportional"]
    assert abs(sg["superposition_check"] - 1.0) < 0.02                   # inner + outer = 2 x both (one linear body)
    assert 0.3 < sg["r_point"] < 0.55 and sg["r_band"][0] <= sg["r_point"] <= sg["r_band"][1]
    assert abs(sg["r_beam"] - sg["r_point"]) < 0.06                       # statics on the lever arms agrees
    assert sg["share_max"] == 0.79 and sg["pass_ratio_no_u0"] > sg["share_max"]


# ------------------------------------------------------------------------------------------------ spools, md, record
def test_spool_count_from_the_build_output():
    if not X.SPOOL_CSV.exists():
        pytest.skip("run designs/pack_5200/frame_h1p_build.py")
    sc = X.spool_count()
    rows = X.SPOOL_CSV.read_text().strip().splitlines()[1:]
    assert sc["spools"] == len(rows)
    assert sc["spools_fa_as_frame"] == sc["spools"] - len(sc["upper_only"])
    md = P.REC_MD.read_text()
    assert f"**book {sc['spools']} spools**" in md and "book 5 spools" not in md
    assert f"{sc['spools_fa_as_frame']} if the first-article upper half" in md


@pytest.mark.skipif(not has_rec, reason="run python -m huntkit.gendesign.bl076 report")
def test_record_and_open_items():
    r = json.loads(REC.read_text())
    x, h = r["bl076"], r["h1p"]
    md = P.REC_MD.read_text()
    assert "## Open items" in md and "## BL-076" in md
    oi = md.split("## Open items")[1].split("\n## ")[0]
    lug = h["rows_by_name"]["US2 lug fatigue"]
    assert "see OPEN" in lug["gated_by"] and "US2 lug fatigue" in oi and "US2-LUG-PPA" in oi
    assert [o["id"] for o in X.open_items(r)][0].startswith("ROW: ")
    # hip rows hold with the plates; keys kept
    for nm, goal in (("hip mount strength (through_bolt)", 1.5), ("hip mount fatigue (through_bolt)", 1.15),
                     ("hip mount creep (through_bolt)", 1.5)):
        assert h["rows_by_name"][nm]["value"] >= goal and h["rows_by_name"][nm]["pass"]
    hm = h["hip_mount"]
    for k in ("od_mm", "id_mm", "t_mm", "holes", "g", "material"):
        assert k in hm["ring"]
    assert hm["ring"]["t_mm"] == B.RING_T and hm["torque_nm"] == B.TORQUE_NM
    assert x["mass"]["delta_g"] < -2.5 and x["before"]["torque_nm"] == 0.6
    assert x["bl073_ring_on_plate_model"]["bearing_min"]["creep"] < 1.5      # the BL-073 ring did not hold either
    assert x["bending_sf_study_max"] >= 1.5
    assert np.isclose(r["bl073"]["margins_bl073_hw"]["hip mount creep"], hm["min_sf"]["creep"])
