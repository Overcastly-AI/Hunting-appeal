"""huntkit.viz3d.cycles_render: pure-Python helpers always; a tiny Cycles render only if bpy is installed."""
import json
import math

import pytest

from huntkit.viz3d import cycles_render as CR


PARTS = {
    "body": {"group": "bag", "modes": ["pack", "pack_haul"], "torso": None, "variant": "rolled", "gap": None},
    "body_full": {"group": "bag", "modes": ["pack"], "torso": None, "variant": "full", "gap": None},
    "man19": {"group": "mannequin", "modes": ["pack"], "torso": 19.0, "variant": None, "gap": None},
    "man23": {"group": "mannequin", "modes": ["pack"], "torso": 23.0, "variant": None, "gap": None},
    "tripod": {"group": "bag", "modes": ["pack"], "torso": None, "variant": "lid", "gap": None},
    "bp": {"group": "backpanel", "modes": ["pack"], "torso": None, "variant": None, "gap": None},
    "link170": {"group": "bag", "modes": ["pack_haul"], "torso": None, "variant": None, "gap": 170.0},
}


def vis(state):
    return {n for n, p in PARTS.items() if CR.visible_for(p, n, state)}


def test_visibility_matches_viewer_rules():
    assert vis({}) == {"body", "bp"}
    assert vis({"mannequin": True}) == {"body", "bp", "man19"}
    assert vis({"mannequin": True, "torso": 23}) == {"body", "bp", "man23"}
    assert vis({"full": True}) == {"body_full", "bp"}
    assert vis({"lid": True}) == {"body", "bp", "tripod"}
    assert vis({"haul": True}) == {"body", "link170"}
    assert vis({"bp": False}) == {"body"}


def test_every_shot_names_a_known_view():
    for s in CR.SHOTS.values():
        assert s["view"] in CR.VIEWS


def test_view_dir_axes():
    # az 0 = camera on the bag's outer face (+Z glTF = -Y Blender); az +90 = from the wearer's right (+X)
    assert CR.view_dir(0, 0) == pytest.approx((0, -1, 0))
    assert CR.view_dir(90, 0) == pytest.approx((1, 0, 0), abs=1e-12)
    assert CR.view_dir(0, 90) == pytest.approx((0, 0, 1), abs=1e-12)


def test_fit_camera_fills_frame():
    lo, hi = (-0.2, -0.15, 0.0), (0.2, 0.15, 0.9)
    fov, aspect, fill = 30.0, 4 / 3, 0.86
    pos, tgt = CR.fit_camera(lo, hi, -38, 14, fov, aspect, 1.0, fill)
    d = tuple(p - t for p, t in zip(pos, tgt))
    assert tgt == pytest.approx((0, 0, 0.45))
    n = math.sqrt(sum(x * x for x in d))
    assert tuple(x / n for x in d) == pytest.approx(CR.view_dir(-38, 14))
    # the worst corner sits at `fill` of the half-frame
    fwd = tuple(-x / n for x in d)
    right = CR._norm(CR._cross(fwd, (0, 0, 1)))
    up = CR._cross(right, fwd)
    th = math.tan(math.radians(fov) / 2)
    m = 0
    for i in range(8):
        c = (hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1], hi[2] if i & 4 else lo[2])
        r = tuple(a - b for a, b in zip(c, pos))
        dep = CR._dot(r, fwd)
        m = max(m, abs(CR._dot(r, right)) / (dep * th * aspect), abs(CR._dot(r, up)) / (dep * th))
    assert m == pytest.approx(fill, rel=2e-3)


def test_fcs_box_to_blender():
    lo, hi = CR.fcs_box_to_blender([-240, 0, 20, 240, 340, 1060])
    assert lo == pytest.approx((-0.24, -0.34, 0.02))
    assert hi == pytest.approx((0.24, 0.0, 1.06))


def test_manifest_from_viewer_html(tmp_path):
    glb = tmp_path / "x.glb"
    glb.write_bytes(b"")
    (tmp_path / "x_viewer.html").write_text("<script>const DATA = " + json.dumps({"parts": PARTS}) + ";\nconst P=1;")
    assert CR.load_manifest(glb) == PARTS


def test_tiny_cycles_render(tmp_path):
    pytest.importorskip("bpy")
    trimesh = pytest.importorskip("trimesh")
    from trimesh.visual import TextureVisuals
    from trimesh.visual.material import PBRMaterial
    import numpy as np
    box = trimesh.creation.box(extents=(0.3, 0.8, 0.2))
    box.visual = TextureVisuals(uv=np.zeros((len(box.vertices), 2)),
                                material=PBRMaterial(name="cordura_body", baseColorFactor=[0.3, 0.35, 0.2, 1]))
    glb = tmp_path / "t.glb"
    glb.write_bytes(trimesh.Scene({"body": box}).export(file_type="glb"))
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"body": {"group": "bag", "modes": ["pack"], "torso": None, "variant": None,
                                        "gap": None}}))
    res = CR.render_views(glb, ["hero"], 2, tmp_path, "t", man, None, (64, 48), threads=1)
    assert (tmp_path / "t_1.png").exists() and res[0]["view"] == "hero"
