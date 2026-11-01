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
    p = load_params(overrides={"fea": {"enabled": False}})
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
                                  "load_shelf", "mannequin@t19"])
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
    for key in ("stay_foot_R", "lumbar_elbow_R", "stay_top_crown_socket_R"):
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
