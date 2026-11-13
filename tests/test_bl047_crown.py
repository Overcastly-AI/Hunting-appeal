"""BL-047: crown GNL on the real crown, pawl bore / window / LP pawl, keep-outs, clamp web, review items m-1 / M-A / M-C."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
REC = REPO / "designs" / "pack_5200" / "analysis" / "crown_gnl.json"
STL = REPO / "designs" / "pack_5200" / "print" / "frame_h1" / "h1_assembled.stl"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


# ------------------------------------------------------------------------------------------------ GNL
def test_gnl_record_no_limit_point(rec):
    s = rec["gnl"]["summary"]
    assert s["n_runs"] >= 60
    assert s["all_reach_lam_max"] and s["limit_points"] == 0
    assert s["margin_min"] >= 1.0 - 1e-9                      # HA-LS-1: lambda_c / 1.5 >= 1 (path stopped at 2.0)
    assert s["lowest_tangent_eig"]["value"] > 0.0
    assert s["linear_margin_range"][1] < 1.0                  # the linear check it replaces did not pass
    for r in rec["gnl"]["table"]:
        assert r["lam_reached"] >= 2.0 - 1e-9
        assert r["member_min"] >= 1.0
    kits = {r["kit"] for r in rec["gnl"]["table"]}
    assert kits == {"a_S", "a_M", "a_L"}
    assert {r["support"] for r in rec["gnl"]["table"]} == {"sling_back", "sling_free", "yoke_back"}


def test_strap_model_replaces_springs_with_tension_only_straps():
    from huntkit.gendesign import crown_gnl as G
    case, mr, lm = G.linear_model("a_M", 19.0)
    sm = G.strap_model(lm, 1.0)
    frame_nodes = set(mr["nodes"])
    assert not (set(sm["supports"]) & frame_nodes)            # nothing grounded on the frame itself
    assert {c["id"] for c in sm["cables"]} >= {"shoulder_L", "shoulder_R", "lifter_L", "lifter_R"}
    assert all(c["dir"] == [0.0, -1.0, 0.0] for c in sm["contacts"])
    assert 38.0 < G.lifter_angle(lm) < 48.0                   # geometry.yaml lifter_angle_deg 40.6


def test_linear_c8_spring_pushes_the_yoke_aft():
    """The reason the linear check is unphysical: the shoulder spring reaction on the yoke points aft (+y)."""
    from huntkit.fea.frame import solve
    from huntkit.gendesign import crown_gnl as G
    case, mr, lm = G.linear_model("a_L", 23.0)
    r = solve(lm).reactions
    assert r["SP150"][1] > 500.0                              # pushes aft: a strap cannot
    assert r["TB0"][1] < -300.0 and r["TB2"][1] < -300.0


def test_cable_is_tension_only():
    from huntkit.fea.gnl import GNL
    m = {"nodes": {"A": [0, 0, 0], "B": [0, 0, 100.0]}, "members": [], "supports": {"A": "fixed", "B": {"fix": "x y rx ry rz", "spring": [0, 0, 1.0, 0, 0, 0]}},
         "cables": [{"id": "c", "nodes": ["A", "B"], "EA": 1e5}], "loads": {"B": [0, 0, -10.0, 0, 0, 0]}}
    g = GNL(m)
    g.path(lam_max=1.0, dlam=0.5, track_eig=False)
    assert g._cable_t["c"] == 0.0                             # pushed together: slack
    assert g.state[0][g.idx["B"], 2] == pytest.approx(90.0, rel=1e-6)    # the spring alone: 10 N / 1 N/mm


# ------------------------------------------------------------------------------------------------ pawl
def test_lp_pawl_fits_and_old_one_does_not():
    from huntkit.gendesign import h1_pawl as P
    pl = P.frame_place()
    assert P.max_py(P.lp_profile()) < pl["face_py"] - 0.5 + 1e-6
    assert P.max_py(P.old_profile()) > pl["face_py"]
    assert P.lift_at_teeth(P.PAWL_LIFT_DEG) >= 1.85 + 0.5      # teeth clear the rack tips at full swing
    assert P.lift_at_teeth(7.9) == pytest.approx(2.35, abs=0.05)
    assert P.lp_profile().bounds[1] >= -1.86                   # nothing below the teeth tips
    # nothing behind the pivot dips under the tooth face when swung (old hub went to -1.0)
    from shapely.geometry import box
    for d in (0.0, 5.0, 10.0):
        back = P.rotated(P.lp_profile(), d).intersection(box(-5, -5, 8, 5))
        assert back.bounds[1] >= -0.15 - 1e-6


def test_pawl_slice_check_on_exported_stl(rec):
    c = rec["pawl"]["check"]
    assert c["pass"]
    assert c["lp_min_dist_mm"] >= 0.45 and c["old_min_dist_mm"] < 0.0
    assert all(b["bore_clear"] and b["wall_2mm_full"] > 0.97 for b in c["bores"])
    assert rec["pawl"]["cheek"]["cheek"]["built"]["sf_fi"] >= 1.0


def test_window_and_bore_in_the_stl():
    import trimesh
    from shapely.geometry import Point, box
    from huntkit.gendesign import h1_fairleads as HF
    from huntkit.gendesign import h1_pawl as P
    from huntkit.gendesign import h1_spine_channel as SC
    mesh = trimesh.load(str(STL))
    pl = P.frame_place()
    S = HF._xplane(mesh, 0.0)
    z = 515.0
    y0 = float(SC.axis_y(z))
    wall = box(y0 + pl["housing_fore_rel"] - 0.5, z - 0.5, y0 + pl["channel_fore_rel"], z + 0.5)
    assert S.intersection(wall).area < 0.05                    # window open at the centre
    S2 = HF._xplane(mesh, 18.0)
    yb = float(SC.axis_y(pl["z_pivot"])) + pl["pivot_y_rel"]
    assert S2.intersection(Point(yb, pl["z_pivot"]).buffer(3.7)).area < 0.05
    assert S2.intersection(Point(yb, pl["z_pivot"]).buffer(6.0).difference(Point(yb, pl["z_pivot"]).buffer(4.0))).area > 0.95 * math.pi * (36 - 16)


def test_channel_check_still_passes(rec):
    assert rec["channel_check"]["all_pass"]
    assert rec["channel_check"]["settings_pass"] == rec["channel_check"]["n"] == 21
    assert rec["channel_check"]["min"]["fore_wall_mm"] >= 2.0


# ------------------------------------------------------------------------------------------------ keep-outs, clamp, ledger
def test_keepouts_rebased(rec):
    k = rec["keepouts"]
    assert k["outside envelope (voxels)"] == 0
    assert k["spine channel BL-046 (tube + rack, h1_spine_channel) empty"] == pytest.approx(1.0)
    assert "pawl present" not in k and "spine_channel empty" not in k
    assert k["pawl housing ring (BL-046, cheeks for the BL-047 pivot) present"] > 0.95


def test_clamp_web_2mm_holds(rec):
    from huntkit.gendesign import crown_spine_clamp as CS
    from huntkit.gendesign import h1_spine_channel as SC
    assert CS.WEB_T_MM == SC.CLAMP_WEB_T == 2.0
    w0, w1 = rec["clamp_web"]["bl046_2p5"], rec["clamp_web"]["bl047_2p0"]
    assert w1["webs"]["sf_yield"] >= 1.0 and w1["webs"]["sf_fatigue_kt2"] >= 1.0
    for grp in ("socket", "saddle", "socket_with_shear", "saddle_with_shear"):
        for k in ("avg", "peak", "fat_avg", "fat_peak"):
            assert w1[grp][k]["sf"] >= w0[grp][k]["sf"] - 1e-6   # nothing got worse
    assert CS.SPINE_CLAMP_MASS_G == pytest.approx(rec["mass"]["clamp_g"], abs=0.05)


def test_ledger_books_bl047(rec):
    from huntkit.mass import ledger as L
    m = rec["mass"]
    assert "BL047" in L.CORRECTIONS
    assert m["h1_print_delta_g"] == pytest.approx(m["pawl_print_net_g"] + m["hinge_relief_g"], abs=0.02)
    assert m["clamp_delta_g"] == pytest.approx(m["clamp_g"] - m["clamp_bl046_g"], abs=0.05)
    assert m["pawl_delta_g"] < 0.0


# ------------------------------------------------------------------------------------------------ review items
def test_m1_relief_clears_the_corner(rec):
    he = rec["he"]
    assert he["as_written"]["pass"]
    assert he["per_ply"]["1.6"]["worst"] >= 0.5               # was 0.19 in the throat-corner fillet
    assert he["tol_0p15"]["worst_under_pin_clear_mm"] >= 0.5


def test_mc_one_hinge_number():
    from huntkit.gendesign import bl047_frame_items as B
    from huntkit.gendesign import h1_fairleads as HF
    txt = (REPO / "designs" / "pack_5200" / "mfg_corrie_f_rev3.py").read_text()
    assert "HINGE_N = 1019.0" in txt and B.HINGE_ROW_N == 1019.0
    h = B.hinge_one_number()
    g = HF.station_geom("hinge")
    M = 1019.0 * (2 * (g.throat + g.cheek) - g.throat) / 8.0
    assert h["pin_7075_5mm"]["sigma_mpa"] == pytest.approx(M / (math.pi * g.pin_d ** 3 / 32), rel=1e-3)
    assert h["pin_7075_5mm"]["sf_yield"] >= 1.0
    # linear scaling: strength at 1019 N = strength on file x (force on file / 1019)
    assert h["revC_direction"]["sf_strength"] < 3.73 and h["revC_direction"]["sf_strength"] > 2.0


def test_ma_tl1_on_bl046_geometry():
    from huntkit.gendesign import bl047_frame_items as B
    rv = B.run_vector()
    assert rv["spine_fore_mm"] == pytest.approx(25.02, abs=0.05) and rv["collar_mm"] == pytest.approx(6.0)
    assert rv["u_run"][1] < 0.0                                # the run heads fore, toward the spine
    assert 30.0 < rv["plan_angle_fore_deg"] < 45.0             # review: about 38 deg fore in plan
    t = B.tl1_recheck()
    assert t["k_vector_bl046"] < t["k_vector_bl045"]           # the fore pull offsets the guy's aft pull
    assert t["proof_publish_n"] >= 497.0
    assert t["rows"]["vector_bl046"]["sf_static"] >= 1.0 and t["rows"]["vector_bl046"]["sf_fatigue"] >= 1.0
    rb = t["pull"]["rig_B_run_loaded"]
    assert rb["guy_outboard_pct"] > 10.0 and rb["guy_below_horizontal_deg"] > 50.0
    assert np.linalg.norm(t["pull"]["rig"]["guy_unit_x_out_y_aft_z_up"]) == pytest.approx(1.0, abs=0.01)
