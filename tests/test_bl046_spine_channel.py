"""BL-046: H1 spine channel for the OD 20 spine tube + 6 mm rack, spine axis, clamp on the real crown, masses."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "designs" / "pack_5200" / "analysis"
PRINT = REPO / "designs" / "pack_5200" / "print" / "frame_h1"


@pytest.fixture(scope="module")
def C():
    from huntkit.gendesign import h1_spine_channel as C
    return C


# ------------------------------------------------------------------------------------------- 1. channel geometry
def test_channel_holds_tube_rack_and_pawl_with_clearance(C):
    """By hand: tube r 10 + clearance 1 aft; rack 6 + pawl zone 9.3 fore of the tube; 22 mm wide."""
    c = C.channel_dims()
    assert c["aft_r"] == pytest.approx(C.SPINE_OD / 2 + C.RUN_CLEAR)
    assert c["fore_rel"] == pytest.approx(-(10.0 + 6.0 + 9.3))
    assert c["depth"] == pytest.approx(11.0 + 25.3)
    assert c["width"] == pytest.approx(22.0)
    sec, mov = C.channel_section(), C.moving_envelope()
    assert sec.contains(mov.buffer(C.RUN_CLEAR - 0.02))           # running clearance all round (96-gon chords)
    assert sec.contains(C.pawl_zone())
    assert mov.bounds[3] - mov.bounds[1] == pytest.approx(C.SPINE_OD + C.RACK_T)   # 26 mm, BL-045's minimum


def test_rack_and_pawl_dims_from_the_print_files(C):
    import trimesh
    e = sorted(trimesh.load(REPO / "designs/pack_5200/print/crown_rack_fdm_pacf.stl").extents)
    assert e[0] == pytest.approx(C.RACK_T, abs=0.01) and e[1] == pytest.approx(C.RACK_W, abs=0.01)
    p = sorted(trimesh.load(REPO / "designs/pack_5200/print/crown_pawl_fdm_pacf.stl").extents)
    assert C.PAWL_W in [pytest.approx(v, abs=0.01) for v in p]


def test_housing_walls_and_envelope(C):
    from huntkit.gendesign.frame_topopt import Y_LO, load_envelope
    h = C.housing_dims()
    assert min(h["fore_wall"], h["aft_wall"], h["side_wall"]) >= C.MIN_WALL
    env = load_envelope()
    for z in h["z"]:
        y_aft = float(C.axis_y(z)) + h["aft_rel"]
        y_fore = float(C.axis_y(z)) + h["fore_rel"]
        assert y_aft <= float(env.y_hi(z)) + 1e-6          # inside the bag envelope (y_hi already 1 mm in)
        assert y_fore >= Y_LO                               # behind the back-pad limit
        assert y_fore >= C.HOUSING_FORE_Y_AT_PAWL - 0.5     # YOKE-PATH: fore face not moved toward the wearer


def test_axis_decision_puts_the_spine_in_the_legs_plane(C):
    d = C.axis_decision()
    assert not d["printed_axis_possible"]                    # BL-045's 15.85 mm fore cannot hold tube + rack + pawl
    assert d["axis_y_most_fore_mm"] > d["printed_bl045_axis_y_mm"]
    assert d["chosen_offset_from_legs_mm"] == 0.0
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.gendesign.frame_topopt import FRAME_YAML
    n = build_frame_from_yaml(FRAME_YAML, torso_in=19.0)["nodes"]
    sp = [k for k in n if k.startswith("SP")]
    for k in sp:                                              # the model's spine nodes lie on the chosen axis
        assert n[k][1] == pytest.approx(float(C.axis_y(n[k][2])), abs=0.05)


def test_every_setting_has_the_pawl_on_the_rack(C):
    s = C.settings()
    assert len(s) == 21 and {q["kit"] for q in s} == {"S", "M", "L"}
    assert all(q["pawl_on_rack"] for q in s)
    assert max(q["bottom_z"] for q in s) == pytest.approx(504.25, abs=0.1)       # 15.8 mm tail below the pawl line
    assert C.guide_bay()["z_top"] >= max(q["bottom_z"] for q in s)


def test_voxel_channel_matches_the_section(C):
    """2 mm voxel body: the channel voxels are empty, the housing ring is solid, nothing changes far away."""
    from huntkit.gendesign import frame_h1 as H1
    cen = H1.base()["cen"]
    solid = np.zeros(len(cen), bool)
    new, cnt = C.voxel_channel(solid, cen)
    assert cnt["removed"] == 0 and cnt["added"] > 0
    x, y, z = cen[new].T
    assert np.all(np.abs(x) <= C.HOUSING_HALF_W + 1e-6)
    assert np.all((z >= C.HOUSING_BOT_Z) & (z <= C.HOUSING_TOP_Z))
    from shapely import contains_xy
    assert not contains_xy(C.channel_section(), x, y - C.axis_y(z)).any()
    vol = cnt["added"] * 8.0
    exact = (C.housing_section().area - C.channel_section().area) * (C.HOUSING_TOP_Z - C.HOUSING_BOT_Z)
    assert vol == pytest.approx(exact, rel=0.2)                # less the bay


# ------------------------------------------------------------------------------------------- 2. print files
@pytest.fixture(scope="module")
def stl_check(C):
    return C.check_stl_channel(PRINT / "h1_assembled.stl")


def test_print_stl_channel_slice_check(C, stl_check):
    r = stl_check
    assert r["all_pass"]
    assert r["min"]["clear_mm"] >= C.RUN_CLEAR - C.MESH_TOL
    assert r["min"]["walls_ok"]
    assert len(r["settings"]) == 21 and all(s["pass"] for s in r["settings"])
    top = [s for s in r["settings"] if s["bottom_z"] > 500]
    assert len(top) == 3 and all(s["guide_b"]["clear_mm"] is not None and s["guide_b"]["pass"] for s in top)


def test_slice_check_catches_the_old_channel(C):
    """The check fails a plate-spine channel (a mesh with the BL-045 40.2 x 18.3 channel and housing)."""
    import manifold3d as m3d
    from shapely.geometry import box
    from huntkit.gendesign.surface import _from_manifold
    y0 = float(C.axis_y(520.0))
    old = C._prism(box(-25.3, -38.8 - y0, 24.3, 0.6 - y0), 506.0, 536.0) - \
        C._prism(box(-20.6, -34.8 - y0, 19.6, -16.5 - y0), 470.0, 560.0)
    m = _from_manifold(old)
    s = C.slice_channel(m, 520.0)
    assert not s["tube_rack_clear"] and s["clear_mm"] == 0.0


def test_print_files_closed_and_fairleads_kept():
    import trimesh
    from huntkit.gendesign import h1_fairleads as HF
    for nm in ("h1_assembled", "h1_lower_flat", "h1_upper_flat"):
        m = trimesh.load(PRINT / f"{nm}.stl")
        assert m.is_watertight, nm
        assert len(m.split(only_watertight=False)) == 1, nm
    assert HF.check_stl(PRINT / "h1_assembled.stl")["all_pass"]


# ------------------------------------------------------------------------------------------- 3. real crown model
def test_real_crown_moves_the_top_bar_and_adds_the_clamp(C):
    import yaml
    g = yaml.safe_load((REPO / "designs/pack_5200/geometry.yaml").read_text())
    assert C.TOP_BAR_AFT_MM == g["frame"]["members_topology"]["crown"]["top_bar_aft_offset_mm"]
    from huntkit.gendesign import crown_diet as CD
    m0 = CD.build(CD.specs()["a_S"], 15.0)
    m1 = C.real_crown(m0)
    assert m1["nodes"]["TB1"][1] - m0["nodes"]["TB1"][1] == pytest.approx(25.0)
    assert m1["nodes"]["CLtop"] == m0["nodes"]["CLtop"]
    assert m1["nodes"]["SPC"][1] == pytest.approx(m0["nodes"]["TB1"][1])
    ids = {q["id"] for q in m1["members"]}
    assert "TB1-SPC" in ids and not any(i.startswith("TB1-SP") and i != "TB1-SPC" for i in ids)


def test_real_crown_statics_by_hand(C):
    """The crown alone (legs fixed at their tops), a pull P along the spine axis at its bottom: the spine's top
    carries P axially and the clamp member delivers P x 25 mm to the bar at TB1 (the line of action passes SPC)."""
    from huntkit.fea.frame import solve
    from huntkit.gendesign import crown_diet as CD
    full = C.real_crown(CD.build(CD.specs()["a_L"], 23.0))
    keep = [q for q in full["members"] if all(n.startswith(("TB", "SP", "CL", "CR")) for n in q["nodes"])]
    used = {n for q in keep for n in q["nodes"]}
    m = {"nodes": {k: v for k, v in full["nodes"].items() if k in used}, "members": keep,
         "supports": {"CLtop": "fixed", "CRtop": "fixed"}}
    sp = [k for k in m["nodes"] if k.startswith("SP") and k != "SPC"]
    last = min(sp, key=lambda k: m["nodes"][k][2])
    u = np.array(m["nodes"]["SPC"]) - np.array(m["nodes"][last])
    u /= np.linalg.norm(u)
    P = 500.0
    m["loads"] = {last: list(-P * u) + [0.0, 0.0, 0.0]}
    res = solve(m)
    ef = {q["id"]: np.asarray(q["end_forces"], float) for q in res.members}
    sid = next(k for k in ef if k.startswith("SPC-SP"))
    assert abs(ef[sid][0][0]) == pytest.approx(P, rel=0.01)
    assert np.linalg.norm(ef[sid][0][4:]) == pytest.approx(0.0, abs=0.01 * P)       # no moment at the spine's top
    assert np.linalg.norm(ef["TB1-SPC"][0][3:]) == pytest.approx(P * 25.0, rel=0.01)


# ------------------------------------------------------------------------------------------- 4. clamp, record, masses
@pytest.fixture(scope="module")
def res():
    return json.loads((ANALYSIS / "h1_spine_channel.json").read_text())


def test_clamp_on_the_real_crown_passes(res):
    c = res["clamp"]
    for k in ("socket", "saddle"):
        m = c["margins"][k]
        assert m["avg"]["sf"] >= 1.0 and m["peak"]["sf"] >= 1.0 and m["fat_avg"]["sf"] >= 1.0, k
    assert c["margins"]["socket_bending"]["sf_yield"] >= 1.0
    assert c["margins"]["webs"]["sf_yield"] >= 1.0 and c["margins"]["webs"]["sf_fatigue_kt2"] >= 1.0
    assert c["spine_axis_offset_fore_mm"] == pytest.approx(25.0, abs=0.3)


def test_published_clamp_constants_match(res):
    from huntkit.gendesign import crown_spine_clamp as CSC
    c = res["clamp"]
    assert CSC.SPINE_CLAMP_HALF_X == pytest.approx(c["half_x_mm"], abs=0.05)
    assert CSC.SPINE_CLAMP_COLLAR == pytest.approx(c["collar_below_bar_underside_mm"], abs=0.05)
    assert CSC.SPINE_CLAMP_MASS_G == pytest.approx(c["mass_g"], abs=0.05)
    assert CSC.SPINE_AXIS_FORE_MM == pytest.approx(c["spine_axis_offset_fore_mm"], abs=0.05)


def test_ledger_books_clamp_and_channel(res):
    from huntkit.mass import ledger as L
    m = res["mass"]
    assert m["clamp_g"] == pytest.approx(res["clamp"]["mass_g"])
    rows = L.corrections("corrie_b2_h1", "M")["BL046"]
    assert len(rows) == 2
    assert sum(r["g"] for r in rows) == pytest.approx(m["clamp_g"] - m["clamp_booked_g"] + m["channel_net_g"], abs=0.01)
    today = L.corrections("corrie_b2_today", "M")["BL046"]
    assert len(today) == 1 and today[0]["g"] == pytest.approx(m["clamp_g"] - m["clamp_booked_g"])


def test_body_margins_recorded_for_every_r1_basis(res):
    for k in ("loads_as_recorded", "loads_real_crown"):
        b = res["body"][k]
        assert set(b) >= {"fine_sm8", "fine", "beam", "fine_sm8.cyc"}
        for v in b.values():
            assert v["strength"] > 0 and v["fatigue"] > 0 and v["buckling"] > 0
