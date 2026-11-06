"""Tests for huntkit.viz3d: watertight meshes, volume method vs analytic boxes, GLB round trip."""
import json
import struct

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from huntkit.viz3d import geom as G  # noqa: E402
from huntkit.viz3d.params import CU_IN_TO_L, load_params  # noqa: E402


@pytest.fixture(scope="module")
def pack():
    from huntkit.viz3d.model import build_pack
    p = load_params(overrides={"fea": {"enabled": False}, "frame_type": "tube"})
    return build_pack(p)


# --------------------------------------------------------------------------- volume method
def test_volume_matches_analytic_box():
    box = trimesh.creation.box(extents=(340.0, 320.0, 788.0))
    assert G.volume_mm3(box) == pytest.approx(340 * 320 * 788, rel=1e-9)


def test_soft_box_volume_matches_analytic_outline_area():
    # sharp-edged box bag (r_edge -> 0, square top corners): outline area x depth, R60 bottom corners
    W, H, D, R = 340.0, 788.0, 320.0, 60.0
    m = G.soft_box(W, H, 35.0, 20.0, D, R, 0.01, r_edge=1e-3, rings_edge=2)
    area = W * H - 2 * (R * R - np.pi * R * R / 4)
    assert G.volume_mm3(m) == pytest.approx(area * D, rel=2e-3)   # arc chords: <0.2 %
    assert G.is_closed(m)


def test_superellipse_loft_converges_to_box():
    a, b, h = 100.0, 60.0, 200.0
    rings = [G.superellipse_ring(a, b, 60.0, 60.0, M=400, z=z) for z in (0.0, h)]
    m = G.loft(np.array(rings), cap_start=True, cap_end=True)
    assert G.volume_mm3(m) == pytest.approx(4 * a * b * h, rel=0.02)


# --------------------------------------------------------------------------- the pack
def test_main_bag_volume_is_5200_cu_in(pack):
    v = pack.metrics["bag_volume_l"]
    assert v == pytest.approx(85.2, abs=1.0)                  # DESIGN R-01: 85.2 L +/- 1 L
    assert pack.metrics["bag_volume_cu_in"] == pytest.approx(v / CU_IN_TO_L)
    # and the mesh agrees with the pack-designer's geometric value
    assert v == pytest.approx(pack.geometry["volumes"]["main_bag_L"], rel=0.01)


@pytest.mark.parametrize("name", ["bag_body", "lid", "frame_stays", "frame_bars", "lumbar_plate",
                                  "side_pockets", "quarter_proxy", "hipbelt", "bag_shards",
                                  "quarter_proxy", "mannequin@t19"])
def test_watertight_parts(pack, name):
    assert G.is_closed(pack.part(name).mesh), name


def test_crown_follows_torso(pack):
    tops = {t: v["crown_top_z"] for t, v in pack.metrics["torsos"].items()}
    assert tops[15.0] < tops[19.0] < tops[23.0]
    for t in (15.0, 19.0, 23.0):
        zmax = pack.part(f"crown@t{t:g}").mesh.vertices[:, 2].max()
        assert zmax == pytest.approx(tops[t], abs=15)


def test_frame_stays_follow_geometry_hard_points(pack):
    hp = pack.geometry["frame"]["hard_points"]
    v = pack.part("frame_stays").mesh.vertices
    keys = ("stay_foot_R", "lumbar_elbow_R" if "lumbar_elbow_R" in hp else "stay_lumbar_node_R", "stay_top_crown_socket_R")
    for key in keys:
        d = np.linalg.norm(v - np.array(hp[key]), axis=1).min()
        assert d <= pack.metrics["tube_sizes"]["stay_od"] / 2 + 1.0, key


def test_every_part_has_uvs_and_known_material(pack):
    from huntkit.viz3d.export import build_materials
    mats, _ = build_materials(pack.params)
    for prt in pack.parts:
        assert prt.material in mats, prt.name
        assert prt.mesh.metadata["uv"].shape == (len(prt.mesh.vertices), 2), prt.name


# --------------------------------------------------------------------------- GLB export
def test_glb_exports_and_reloads(pack, tmp_path):
    from huntkit.viz3d.export import export_glb, manifest
    path, info = export_glb(pack, tmp_path / "pack.glb")
    raw = path.read_bytes()
    assert raw[:4] == b"glTF"
    jl = struct.unpack("<I", raw[12:16])[0]
    doc = json.loads(raw[20:20 + jl])
    names = {m["name"] for m in doc["materials"]}
    assert {"carbon_twill", "camo_owner_base", "cordura_body"} <= names
    assert len(doc["images"]) == len({doc["bufferViews"][i["bufferView"]]["byteLength"] for i in doc["images"]})
    scene = trimesh.load(path)
    assert set(manifest(pack)) == set(scene.graph.nodes_geometry)
    bag = scene.geometry["bag_body"]
    # glTF is metres, Y up: volume in m^3 must match the mm^3 model
    assert G.volume_mm3(bag) * 1e9 == pytest.approx(G.volume_mm3(pack.part("bag_body").mesh), rel=1e-4)
    assert bag.bounds[1][1] > 0.8                             # bag top ~0.82 m up the Y axis


# --------------------------------------------------------------------------------------------
# v3 SPINE teardrop bag (geometry.yaml bag.profile)
# --------------------------------------------------------------------------------------------
def test_v3_teardrop_parts_and_states(pack):
    if pack.geometry["bag"].get("type") != "teardrop_rolltop":
        pytest.skip("geometry.yaml is not the v3 teardrop")
    for name in ("bag_body_full", "diagonal_band", "rolltop", "rolltop_full", "compression_straps"):
        assert G.is_closed(pack.part(name).mesh), name
    full = pack.part("bag_body_full").mesh
    rolled = pack.part("bag_body").mesh
    # the counted 85.2 L is the FULL drafted state; the displayed mesh drapes B-01 over the hard parts and carries
    # the sewn fairlead swells, so it is a little smaller (reported separately)
    vd = pack.metrics.get("bag_volume_draped_l", pack.metrics["bag_volume_l"])
    assert G.volume_mm3(full) / 1e6 == pytest.approx(vd)
    assert 0.0 <= pack.metrics["bag_volume_l"] - vd < 1.0
    assert pack.metrics["bag_volume_rolled_l"] == pytest.approx(pack.geometry["volumes"]["rolled_down_L"], rel=0.01)
    assert G.volume_mm3(rolled) < G.volume_mm3(full)
    assert pack.part("bag_body").variant == "rolled" and pack.part("bag_body_full").variant == "full"
    # teardrop: slim at the hips, fullest high up; depth within the owner's v3.1 cap (11.5-12 in at the widest)
    st = np.array(pack.geometry["bag"]["profile"]["stations"])
    k = int(np.argmax(st[:, 3]))
    assert st[0, 3] < st[k, 3] <= 12.0 * 25.4
    assert st[0, 1] < st[:, 1].max()
    assert st[k, 0] > st[0, 0] + 0.4 * (st[-1, 0] - st[0, 0])


def test_export_puts_wearers_right_on_screen_right():
    # FCS is left-handed as labelled (x+ = wearer's right, y+ aft, z up): the export must mirror
    from huntkit.viz3d.export import M_FCS_TO_GLTF, to_gltf
    assert np.linalg.det(M_FCS_TO_GLTF) < 0
    assert to_gltf([100.0, 0, 0])[0] > 0          # camera on +Z (behind the wearer): +X = screen right


def test_v31_no_shelf_internal_meat_harness(pack):
    """v3.1 (owner): shelf deleted; meat held by internal straps anchored at bonded frame nodes."""
    g = pack.geometry
    if not g.get("meat_harness"):
        pytest.skip("geometry.yaml predates v3.1")
    assert not g.get("load_shelf")
    names = {p.name for p in pack.parts}
    assert "load_shelf" not in names and "meat_straps" in names
    hp = g["frame"]["hard_points"]
    for s in g["meat_harness"]["straps"]:
        for a in s["anchors"]:
            assert a in hp
        assert s["z"] in (190.0, 330.0, 520.0)                 # bonded nodes, never mid-span
    assert g["meat_harness"]["load_cases"]["min_margin"] >= 1.0
    assert g["head_clearance"]["all_pass"]


# --------------------------------------------------------------------------------------------
# Joint, spreader and back panel (design state 2026-11-06: huntkit.viz3d.attach)
# --------------------------------------------------------------------------------------------
def _attach_or_skip(pack):
    if "spreader_board" not in {p.name for p in pack.parts}:
        pytest.skip("geometry.yaml predates the attachment phase")


def _split(mesh):
    m = mesh.copy()
    m.merge_vertices(digits_vertex=4)               # sweeps leave their caps unmerged
    return m.split(only_watertight=False)


def _components(mesh):
    return len(_split(mesh))


def test_attachment_parts_present(pack):
    _attach_or_skip(pack)
    names = {p.name for p in pack.parts}
    want = {"spreader_board", "spreader_tubes", "spreader_pucks", "spreader_clips", "back_panel", "rail_foam",
            "rail_backers", "fairlead_cleats", "cradle_fairleads", "fairlead_pins", "hinge_pins", "captive_eyes",
            "tab_b17", "doublers_b18_b23", "hinge_eyes", "hook_tongues", "bag_hooks", "hood_ladders", "guy_tabs_b22",
            "bow_carry", "bow_carry_hook", "under_straps", "under_straps_open", "cradle_straps", "quarter_between",
            "meat_straps_between", "meat_straps"}
    for t in (15, 19, 23):
        want |= {f"crown_hood@t{t}", f"crown_hood_open@t{t}", f"top_guys@t{t}", f"top_guys_full@t{t}"}
    assert want <= names, sorted(want - names)
    # retired parts: the curved rev-B sheet STL, the LINK toggles, the shelf
    assert not ({"frame_barrier", "bag_link", "load_shelf"} & names)


def test_spreader_is_the_flat_sandwich_v2_board(pack):
    _attach_or_skip(pack)
    from huntkit.viz3d import attach as A
    w, h = A.panel_size("BP-06")
    t = float(A.panels()["BP-06"]["thickness_mm"])
    v = np.asarray(pack.part("spreader_board").mesh.vertices)
    assert v[:, 0].max() - v[:, 0].min() == pytest.approx(w, abs=0.5)        # 242
    assert v[:, 2].max() - v[:, 2].min() == pytest.approx(h, abs=0.5)        # 318
    off = v[:, 1] - A.board_wearer_y(v[:, 2])                                 # distance from the flat wearer plane
    assert off.min() == pytest.approx(0.0, abs=1e-6)
    assert off.max() == pytest.approx(t, abs=1e-6)                           # 7.44, nothing curved
    # wearer plane is a plane: y linear in z
    zz = np.linspace(112, 430, 9)
    yy = A.board_wearer_y(zz)
    assert np.ptp(np.diff(yy) / np.diff(zz)) < 1e-6
    # notches at the cleats and slots: less area than the plain rectangle
    shp = A.board_shape()
    assert shp.area < w * h - 2000
    S = A._S()
    assert pack.metrics["spreader"]["edge_tubes"] == len(S.EDGE_TUBES) == 2
    assert pack.metrics["spreader"]["clips"] == 6 and pack.metrics["spreader"]["pucks"] == 11
    assert _components(pack.part("spreader_tubes").mesh) == 2


def test_back_rails_and_backers_from_records(pack):
    _attach_or_skip(pack)
    from huntkit.viz3d import attach as A
    rw, rl = A.panel_size("BP-02")
    bw, bl = A.panel_size("BP-08")
    for name, w, l in (("rail_foam", rw, rl), ("rail_backers", bw, bl)):
        v = np.asarray(pack.part(name).mesh.vertices)
        R = v[v[:, 0] > 0]
        assert R[:, 0].max() - R[:, 0].min() == pytest.approx(w, abs=0.5), name
        assert R[:, 2].max() - R[:, 2].min() == pytest.approx(l, abs=0.5), name
        assert (R[:, 0].max() + R[:, 0].min()) / 2 == pytest.approx(A._S().STAY_X, abs=0.5)   # centred on the stay
    assert rw == 120 and bw == 80                                              # back_rail.md released r120_b80
    bp = pack.metrics["back_panel"]
    assert bp["gutter_mm"] == pytest.approx(110.0)
    m = np.asarray(pack.part("back_panel").mesh.vertices)
    assert m[:, 0].max() - m[:, 0].min() == pytest.approx(A.panel_size("BP-01")[0], abs=0.5)    # 370 mesh
    # backers sit on the wearer side of the stays, foam on the wearer side of the backers
    assert np.asarray(pack.part("rail_backers").mesh.vertices)[:, 1].max() < A.stay_y(260.0) - 9.0


def test_fairleads_pins_and_eyes(pack):
    _attach_or_skip(pack)
    from huntkit.viz3d import attach as A
    assert _components(pack.part("fairlead_cleats").mesh) == 8                 # hinge + IM1-IM3, both sides
    assert _components(pack.part("cradle_fairleads").mesh) == 4                # US1 / US2
    pins = pack.part("fairlead_pins").mesh
    BA = A._BA()
    for st in BA.stations():
        if st["name"] == "hinge":
            continue
        v = np.asarray(pins.vertices)
        on = v[np.abs(v[:, 0] - st["x"]) <= 25.5]                              # 50 mm pin centred on the cleat
        rad = np.hypot(on[:, 1] - A.pin_y(st["z"]), on[:, 2] - st["z"])
        assert np.isclose(rad, 2.5, atol=0.05).any(), st["id"]                  # 5 mm pin on the hole axis
    assert pack.part("hinge_pins").modes == ("pack", "pack_haul")              # pins leave with the bag


def test_bag_hooks_rated_and_on_the_eyes(pack):
    _attach_or_skip(pack)
    from huntkit.gendesign.attach_system import HOOK_RATED_N
    hk = pack.part("bag_hooks")
    assert f"{HOOK_RATED_N:.0f} N" in hk.label and pack.metrics["attach"]["hook_rated_n"] == HOOK_RATED_N
    parts = _split(hk.mesh)
    assert len(parts) == 4
    zc = sorted(round(float(p.vertices[:, 2].mean())) for p in parts)
    assert zc[0] > 260 and zc[1] < 330 and 450 < zc[2] < 520                   # below IM2 (330) and IM3 (520)
    assert hk.swing and pack.part("tab_b17").swing


def test_crown_hood_on_the_bar_lip_relieved(pack):
    _attach_or_skip(pack)
    from huntkit.gendesign.attach_system import BAR_OD, HOOD, WRAP
    cs = {c["torso_in"]: c for c in pack.geometry["frame"]["crown_settings"]}
    for t in (15, 19, 23):
        v = np.asarray(pack.part(f"crown_hood@t{t:g}").mesh.vertices)
        yc, zc = cs[float(t)]["top_bar_centre"][1:]
        crown = v[v[:, 2] > zc + BAR_OD / 2]
        assert crown[:, 2].min() >= zc + BAR_OD / 2 - 0.1                       # sits ON the bar
        assert crown[:, 0].max() == pytest.approx(HOOD["width"] / 2, abs=0.5)   # 190 mm shell
        lip = v[(v[:, 1] < yc - BAR_OD / 2) & (v[:, 2] < zc)]                   # J-lip on the wearer side, below centre
        assert len(lip) and np.abs(lip[:, 0]).max() <= HOOD["lip_half"] + 0.5   # relieved to x +/-66
        assert np.abs(lip[:, 0]).max() < WRAP["x_start"] - 9.0                  # clear of the wraps with the 9 mm float


def test_ladder_and_guys_follow_the_records(pack):
    _attach_or_skip(pack)
    from huntkit.gendesign.attach_system import GUY, LADDER
    v = np.asarray(pack.part("hood_ladders").mesh.vertices)
    assert v[:, 2].min() == pytest.approx(LADDER["z_lo"], abs=1.0)
    assert v[:, 2].max() == pytest.approx(LADDER["z_lo"] + LADDER["h"], abs=1.0)
    R = v[v[:, 0] > 0]
    assert (R[:, 0].max() + R[:, 0].min()) / 2 == pytest.approx(LADDER["x"], abs=2.0)
    gx, gz = GUY["bag_xz"]
    for t in (15, 19, 23):
        g = np.asarray(pack.part(f"top_guys@t{t}").mesh.vertices)
        for s in (-1, 1):
            side = g[np.sign(g[:, 0]) == s]
            far = side[np.argmax(side[:, 1])]                                   # bag end of the guy
            assert abs(abs(far[0]) - gx) < 15 and abs(far[2] - gz) < 15
    gl = pack.metrics["attach"]["guy_model_mm"]["19_rolled"]
    assert gl == pytest.approx(GUY["free_mm"], rel=0.15)                       # drafted path vs the record free length


def test_between_mode_swing_matches_meat_haul_record(pack):
    _attach_or_skip(pack)
    import json
    from huntkit.viz3d.params import REPO
    rec = json.loads((REPO / "designs/pack_5200/analysis/meat_haul_modes.json").read_text())["between"]
    h = pack.metrics["hinge"]
    assert h["angle_deg"] == pytest.approx(rec["angle_deg"]) and h["z"] == 60.0
    for z, mm in rec["opening_mm"].items():                                    # wedge left for the meat
        assert pack.metrics["between_wedge_mm"][z] == pytest.approx(mm, abs=10.0)
    for name in ("bag_body", "bag_body_full", "hook_tongues", "crown_hood_open@t19", "top_guys_open@t19"):
        assert pack.part(name).swing, name
    assert not pack.part("quarter_between").swing and pack.part("quarter_between").modes == ("pack_haul",)
    assert pack.part("quarter_proxy").modes == ("frame_haul",) and pack.part("cradle_straps").modes == ("frame_haul",)
    from huntkit.viz3d.export import manifest
    man = manifest(pack)
    assert man["bag_body"]["swing"] and man["bag_body"]["xray"] and not man["spreader_board"]["swing"]


def test_bow_riser_carry_on_the_right(pack):
    _attach_or_skip(pack)
    v = np.asarray(pack.part("bow_carry").mesh.vertices)
    assert (v[:, 0] > 0).all()                                                 # D-30: right face
    assert pack.part("bow_carry").swing


def test_captions_match_the_current_design(pack):
    from huntkit.viz3d.cli import shots
    m = dict(pack.metrics)
    m["torsos"] = {float(k): v for k, v in m["torsos"].items()}
    txt = " ".join((s["caption"] + " " + s["sub"]).lower() for s in shots(m))
    assert "frame, crown, shelf" not in txt and "shelf straps" not in txt
    assert txt.count("shelf") == txt.count("no shelf")                          # only ever 'no shelf'
    assert "hinges back" not in txt and "link" not in txt and "lumbar plate" not in txt
    names = [s["name"] for s in shots(m)]
    if "spreader_board" in {p.name for p in pack.parts}:
        assert {"between", "attach", "bagoff", "hood", "spreader", "backpanel", "bow"} <= set(names)
