"""Path-traced product renders of a viz3d GLB with Blender Cycles (headless, CPU + OpenImageDenoise).

The three.js viewer (``viewer.py`` + ``render.js``) stays the quick, interactive look. This module is the
"product photography" look. It imports the same GLB and swaps every glTF material, by name, for a
physically based Cycles shader:

* ripstop nylon: Principled BSDF with sheen, a procedural ripstop grid at true pitch as bump, fine
  stretched-noise wrinkles (shader bump only, so the cloth-sim geometry is unchanged), and roughness
  and dye mottling;
* camo: the owner's base camo (``huntkit.camo.owner_base``) re-rasterised at 2048 px for one 380 mm
  accent repeat, the same UV scale as ``export.py``. Same ripstop bump;
* webbing weave bump, matte black POM / anodised hardware, clear-coated carbon twill;
* back panel: dark spacer mesh (open hex cells) over black XLPE foam (BP-01 / BP-02);
* matte grey mannequin.

Studio rig: three area lights placed relative to the camera azimuth, a gradient "HDRI-like" world and a
shadow-catcher floor (contact shadows). AgX view transform, mild depth of field. Film is transparent and
the frame is composited onto the viewer's seamless backdrop gradient with Pillow.

Part visibility and the camera presets mirror the viewer (``viewer.py`` ``visibleFor`` / ``VIEWS``), so a
Cycles frame and a three.js frame of the same view compare 1:1.

Needs ``bpy`` (the Blender-as-a-module wheel, Python 3.11 only). It is not in requirements.txt (about
1 GB). Install it OUTSIDE the repo; see huntkit/viz3d/README.md::

    python3.11 -m venv /path/to/bpyenv && /path/to/bpyenv/bin/pip install bpy pillow pyyaml
    /path/to/bpyenv/bin/python -m huntkit.viz3d.cycles_render \\
        --glb outputs/pack3d_corrie/corrie.glb --views rear34,side,door,wing,hero --samples 128 \\
        --out outputs/screens --prefix 20261108_cycles

The pure-Python helpers (manifest, visibility, camera fit) import without bpy; tests use them.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------------------------------------ shots
# Camera presets copied from viewer.py VIEWS (az deg: 0 = looking at the bag outer face from +Z(glTF),
# +90 = from the wearer's right; el deg; zoom; optional close-up box in FCS mm [x0,y0,z0,x1,y1,z1]).
VIEWS = {
    "hero": {"az": -38, "el": 14, "zoom": 1},
    "side": {"az": 90, "el": 4, "zoom": 1},
    "front": {"az": 0, "el": 6, "zoom": 1},
    "back": {"az": -150, "el": 14, "zoom": 1},
    "door": {"az": -22, "el": 10, "zoom": 1, "box": [-240, 0, 20, 240, 340, 1060]},
    "pouch": {"az": -36, "el": 28, "zoom": 1, "box": [-310, 20, 870, 320, 320, 1070]},
    "wing": {"az": 58, "el": 10, "zoom": 1, "box": [-60, -20, 60, 260, 330, 980]},
    "backpanel": {"az": -160, "el": 8, "zoom": 1, "box": [-200, -60, 20, 200, 30, 520]},
}
DEFAULT_STATE = {"mode": "pack", "haul": False, "mannequin": False, "torso": 19, "harness": True, "full": False,
                 "lid": False, "bp": True, "posts": False, "fea": False, "gap": None}
# Named shots. "hero" uses exactly the state + camera of outputs/screens/20261108_corrie_1.png (three.js),
# so it is the before/after pair.
SHOTS = {
    "rear34": {"view": "hero", "state": {"mannequin": True}, "caption": "CORRIE: 3/4 rear on the wearer",
               "sub": "19 in torso. Blender Cycles path trace"},
    "side": {"view": "side", "state": {"mannequin": True}, "caption": "CORRIE: side profile on the wearer",
             "sub": "Wing over the side gusset, roll-top clipped to the sides, 4 L pouch on the roll"},
    "door": {"view": "door", "state": {"full": True}, "caption": "CORRIE: horseshoe door open",
             "sub": "Door folded over the hinge band; meat straps IM1-IM3 and the floor in reach"},
    "wing": {"view": "wing", "state": {"lid": True}, "caption": "CORRIE: tripod under the right wing",
             "sub": "Wing tensioned over the tripod legs by two G-hook straps"},
    "hero": {"view": "hero", "state": {}, "caption": "CORRIE: 3/4 rear, pack alone",
             "sub": "Same camera and state as the three.js render 20261108_corrie_1"},
    "backpanel": {"view": "backpanel", "state": {}, "caption": "CORRIE: back panel (wearer side)",
                  "sub": "BP-01 spacer mesh over the BP-02 XLPE rails, 370 x 440 mm (14.6 x 17.3 in)"},
}


# --------------------------------------------------------------------------------------- pure helpers
def load_manifest(glb: Path, manifest: Path | None = None) -> dict:
    """Part manifest (viewer ``DATA.parts``): explicit JSON, else ``<glb dir>/<stem>_viewer.html``."""
    if manifest:
        d = json.loads(Path(manifest).read_text())
        return d.get("parts", d)
    html = Path(glb).with_name(Path(glb).stem + "_viewer.html")
    if not html.exists():
        cands = sorted(Path(glb).parent.glob("*_viewer.html"))
        if not cands:
            raise FileNotFoundError(f"no manifest: pass --manifest or keep {html.name} next to the GLB")
        html = cands[0]
    text = html.read_text()
    key = "const DATA = "
    i = text.index(key) + len(key)
    data, _ = json.JSONDecoder().raw_decode(text[i:])
    return data["parts"]


def visible_for(p: dict | None, name: str, state: dict) -> bool:
    """Python port of viewer.py ``visibleFor`` (no explode, no fit roots)."""
    if p is None:
        return True
    st = {**DEFAULT_STATE, **state}
    mode = st["mode"] + ("_haul" if st["haul"] else "")
    if mode not in p["modes"]:
        return False
    if p.get("torso") is not None and abs(p["torso"] - st["torso"]) > 0.01:
        return False
    v = p.get("variant")
    if (v == "full" and not st["full"]) or (v == "rolled" and st["full"]):
        return False
    if (v == "lid" and not st["lid"]) or (v == "nolid" and st["lid"]):
        return False
    if p.get("gap") is not None:
        gap = st["gap"] if st["gap"] is not None else 170.0
        if abs(p["gap"] - gap) > 0.5:
            return False
    g = p["group"]
    if g == "mannequin":
        return bool(st["mannequin"])
    if g == "fea":
        return bool(st["fea"])
    if (g == "suspension" and not st["harness"]) or (g == "backpanel" and not st["bp"]):
        return False
    if g == "accessory" and not st["posts"]:
        return False
    return True


def fcs_box_to_blender(b):
    """viewer close-up box, FCS mm -> Blender metres (FCS x, -y, z; glTF import is Y-up -> Z-up)."""
    x0, y0, z0, x1, y1, z1 = (v / 1000.0 for v in b)
    return (min(x0, x1), min(-y0, -y1), min(z0, z1)), (max(x0, x1), max(-y0, -y1), max(z0, z1))


def view_dir(az_deg: float, el_deg: float):
    """Unit vector target -> camera in Blender axes (viewer: glTF (sin az cos el, sin el, cos az cos el))."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    gx, gy, gz = math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)
    return (gx, -gz, gy)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return tuple(x / n for x in a)


def fit_camera(bmin, bmax, az, el, fov_v_deg=30.0, aspect=4 / 3, zoom=1.0, fill=0.86):
    """Same iteration as viewer.py ``view()``: the box's 8 corners fill ``fill * zoom`` of the frame.
    Returns (camera position, target) in Blender metres."""
    tgt = tuple((a + b) / 2 for a, b in zip(bmin, bmax))
    d = view_dir(az, el)
    fwd = tuple(-x for x in d)
    right = _norm(_cross(fwd, (0, 0, 1)))
    up = _cross(right, fwd)
    th = math.tan(math.radians(fov_v_deg) / 2)
    corners = [(bmax[0] if i & 1 else bmin[0], bmax[1] if i & 2 else bmin[1], bmax[2] if i & 4 else bmin[2])
               for i in range(8)]
    dist = math.dist(bmin, bmax) * 1.5
    for _ in range(6):
        cam = tuple(t + dist * x for t, x in zip(tgt, d))
        m = 0.0
        for c in corners:
            r = _sub(c, cam)
            depth = _dot(r, fwd)
            m = max(m, abs(_dot(r, right) / (depth * th * aspect)), abs(_dot(r, up) / (depth * th)))
        dist *= m / (fill * zoom)
    return tuple(t + dist * x for t, x in zip(tgt, d)), tgt


def shrink_png(path: Path, max_bytes: int = 1_500_000):
    """Keep a screenshot under the phone budget: optimise, then 256-colour dither, then downscale."""
    from PIL import Image
    path = Path(path)
    im = Image.open(path).convert("RGB")
    im.save(path, optimize=True)
    while path.stat().st_size > max_bytes and im.width > 1100:      # 24-bit first: no posterised shadows
        im = im.resize((int(im.width * 0.9), int(im.height * 0.9)), Image.LANCZOS)
        im.save(path, optimize=True)
    while path.stat().st_size > max_bytes:
        im = im.resize((int(im.width * 0.88), int(im.height * 0.88)), Image.LANCZOS)
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                    dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)


# ---------------------------------------------------------------------------------------- camo texture
def owner_camo_png(cache_dir: Path, size: int = 2048) -> Path | None:
    """Owner base camo, re-rasterised from the master SVG at ``size`` px per 380 mm repeat (runs the repo's
    own Python, which has cairosvg/scipy; bpy's interpreter usually doesn't). A 3x3 mode filter removes the
    1-px cairosvg hairlines without blending inks. Returns None if the repo Python can't do it."""
    out = Path(cache_dir) / f"owner_base_camo_{size}.png"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    py = os.environ.get("HUNTKIT_PY", "python3")
    code = ("import warnings; warnings.simplefilter('ignore');"
            "from huntkit.camo.owner_base import load_owner_base; from PIL import Image, ImageFilter;"
            f"im = Image.fromarray(load_owner_base().rgb({size})).convert('RGB');"
            f"im.filter(ImageFilter.ModeFilter(3)).save(r'{out}')")
    try:
        subprocess.run([py, "-c", code], cwd=REPO, check=True, timeout=300, capture_output=True)
        return out
    except Exception as e:  # noqa: BLE001
        print("owner camo re-raster failed, using the GLB texture:", e)
        return None


# ===================================================================================== Blender section
def _bpy():
    import bpy  # noqa: PLC0415
    return bpy


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    h = h.lstrip("#")
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)


class NB:
    """Tiny node-graph builder for one material."""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = -1600

    def n(self, kind, **inputs):
        node = self.nt.nodes.new(kind)
        node.location = (self.x, 0)
        self.x += 160
        for k, v in inputs.items():
            if hasattr(node, k) and not isinstance(v, (tuple, list)) and k not in node.inputs:
                setattr(node, k, v)
            else:
                self.set(node, k, v)
        return node

    def set(self, node, key, v):
        sock = node.inputs[key]
        if hasattr(v, "is_output") or (hasattr(v, "outputs") and not isinstance(v, (int, float))):
            self.link(v, sock)
        else:
            sock.default_value = v

    def link(self, src, dst):
        if hasattr(src, "outputs") and not hasattr(src, "is_output"):
            src = src.outputs[0]
        self.nt.links.new(src, dst)

    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op)
        m.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m


def _uv_scaled(nb, scale):
    tc = nb.n("ShaderNodeTexCoord")
    vm = nb.n("ShaderNodeVectorMath", operation="SCALE")
    nb.link(tc.outputs["UV"], vm.inputs[0])
    vm.inputs["Scale"].default_value = scale
    return vm, tc


def _grid_height(nb, uv_mm, pitch_mm, line=0.10):
    """Ripstop grid: 0..1 ridges every ``pitch_mm`` in both fabric directions."""
    vm, _ = _uv_scaled(nb, uv_mm / pitch_mm)
    sep = nb.n("ShaderNodeSeparateXYZ")
    nb.link(vm.outputs["Vector"], sep.inputs[0])
    out = []
    for ax in ("X", "Y"):
        f = nb.math("FRACT", sep.outputs[ax])
        a = nb.math("ABSOLUTE", nb.math("SUBTRACT", f, 0.5))
        mr = nb.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        nb.link(a, mr.inputs["Value"])
        mr.inputs["From Min"].default_value = 0.5 - line
        mr.inputs["From Max"].default_value = 0.5
        out.append(mr)
    return nb.math("MAXIMUM", out[0].outputs[0], out[1].outputs[0])


def _weave_height(nb, uv_mm, pitch_mm):
    """Plain/twill weave: sin(u) * sin(v) at the yarn pitch."""
    vm, _ = _uv_scaled(nb, uv_mm / pitch_mm * 2 * math.pi)
    sep = nb.n("ShaderNodeSeparateXYZ")
    nb.link(vm.outputs["Vector"], sep.inputs[0])
    return nb.math("MULTIPLY", nb.math("SINE", sep.outputs["X"]), nb.math("SINE", sep.outputs["Y"]))


def _obj_noise(nb, scale, detail=4.0, stretch=(1, 1, 1), rough=0.55):
    tc = nb.n("ShaderNodeTexCoord")
    mp = nb.n("ShaderNodeMapping")
    nb.link(tc.outputs["Object"], mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = stretch
    nz = nb.n("ShaderNodeTexNoise")
    nb.link(mp.outputs["Vector"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = rough
    return nz


def _bump(nb, height, dist, strength=1.0, normal=None):
    b = nb.n("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    nb.link(height, b.inputs["Height"])
    if normal is not None:
        nb.link(normal, b.inputs["Normal"])
    return b


def _principled(nb, mat, base, rough, normal=None, **kw):
    bsdf = nb.n("ShaderNodeBsdfPrincipled")
    if isinstance(base, tuple):
        bsdf.inputs["Base Color"].default_value = base
    else:
        nb.link(base, bsdf.inputs["Base Color"])
    if isinstance(rough, (int, float)):
        bsdf.inputs["Roughness"].default_value = rough
    else:
        nb.link(rough, bsdf.inputs["Roughness"])
    if normal is not None:
        nb.link(normal, bsdf.inputs["Normal"])
    for k, v in kw.items():
        bsdf.inputs[k.replace("_", " ")].default_value = v
    out = nb.n("ShaderNodeOutputMaterial")
    nb.link(bsdf.outputs[0], out.inputs["Surface"])
    return bsdf


def _mix_rgba(nb, blend="MIX"):
    """ShaderNodeMix in RGBA mode. Its sockets share names across data types ("A", "Result"), so pick the
    colour ones by index: inputs 0 factor, 6 A colour, 7 B colour; output 2 colour result."""
    m = nb.n("ShaderNodeMix", data_type="RGBA", blend_type=blend)
    return m, m.inputs[0], m.inputs[6], m.inputs[7], m.outputs[2]


def _mottle(nb, base, amount=0.06, scale=9.0, lighten=None):
    """Base colour (tuple or socket) x (1 +/- amount) low-frequency dye/soil mottling; optional ripstop
    yarn lightening ``lighten=(height socket, factor)``."""
    nz = _obj_noise(nb, scale, detail=3.0)
    mr = nb.n("ShaderNodeMapRange")
    nb.link(nz.outputs["Fac"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1 - amount, 1 + amount
    _, fac, a, b, col = _mix_rgba(nb, "MULTIPLY")
    fac.default_value = 1.0
    if isinstance(base, tuple):
        a.default_value = base
    else:
        nb.link(base, a)
    comb = nb.n("ShaderNodeCombineXYZ")
    for s in ("X", "Y", "Z"):
        nb.link(mr.outputs["Result"], comb.inputs[s])
    nb.link(comb.outputs[0], b)
    if lighten is not None:
        h, f = lighten
        _, fac2, a2, b2, col2 = _mix_rgba(nb, "SCREEN")
        nb.link(nb.math("MULTIPLY", h, f), fac2)
        nb.link(col, a2)
        b2.default_value = (1, 1, 1, 1)
        col = col2
    return col


def _rough_var(nb, rough, amount=0.06, scale=14.0):
    nz = _obj_noise(nb, scale, detail=2.0)
    mr = nb.n("ShaderNodeMapRange")
    nb.link(nz.outputs["Fac"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = rough - amount, rough + amount
    return mr.outputs["Result"]


def fabric(mat, base, uv_mm=500.0, rough=0.78, grid_mm=6.0, sheen=0.45, wrinkles=1.0, spec=0.35,
           coat=0.0, weave_mm=0.9, image=None):
    """Woven nylon face fabric (ripstop when ``grid_mm``) with sheen, bump and fine wrinkles."""
    nb = NB(mat)
    if image is not None:
        tc = nb.n("ShaderNodeTexCoord")
        tex = nb.n("ShaderNodeTexImage", interpolation="Cubic")
        tex.image = image
        nb.link(tc.outputs["UV"], tex.inputs["Vector"])
        base_sock = tex.outputs["Color"]
    else:
        base_sock = base
    hgt = None
    if grid_mm:
        hgt = _grid_height(nb, uv_mm, grid_mm)
    weave = _weave_height(nb, uv_mm, weave_mm)
    h = nb.math("ADD", nb.math("MULTIPLY", weave, 0.35), hgt) if hgt is not None else weave
    nrm = _bump(nb, h, 0.00012, 0.8)
    if wrinkles:
        # fine stretched crease noise (pack-cloth "hand"): shader-only, geometry untouched
        w = _obj_noise(nb, 18.0, detail=5.0, stretch=(1.0, 1.0, 0.4), rough=0.6)
        w2 = nb.math("ABSOLUTE", nb.math("SUBTRACT", w.outputs["Fac"], 0.5))
        nrm = _bump(nb, w2, 0.006 * wrinkles, 1.0, normal=nrm.outputs[0])
    col = _mottle(nb, base_sock, 0.05, lighten=(hgt, 0.025) if hgt is not None else None)
    _principled(nb, mat, col, _rough_var(nb, rough), nrm.outputs[0], Sheen_Weight=sheen, Sheen_Roughness=0.35,
                Specular_IOR_Level=spec, Coat_Weight=coat, Coat_Roughness=0.35)


def webbing(mat, base, uv_mm=500.0):
    nb = NB(mat)
    weave = _weave_height(nb, uv_mm, 1.4)
    rib = _grid_height(nb, uv_mm, 2.8, line=0.25)
    nrm = _bump(nb, nb.math("ADD", weave, nb.math("MULTIPLY", rib, 0.6)), 0.0004, 1.0)
    col = _mottle(nb, base, 0.05)
    _principled(nb, mat, col, _rough_var(nb, 0.62), nrm.outputs[0], Sheen_Weight=0.6, Sheen_Roughness=0.3,
                Specular_IOR_Level=0.45)


def spacer_mesh(mat, uv_mm=500.0, cell_mm=3.2):
    """BP-01: black 3D spacer mesh. Open hex-ish cells (Voronoi edge distance) read as holes onto the black
    foam behind; monofilament sheen on the lands."""
    nb = NB(mat)
    vm, _ = _uv_scaled(nb, uv_mm / cell_mm)
    vor = nb.n("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    nb.link(vm.outputs["Vector"], vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 1.0
    vor.inputs["Randomness"].default_value = 0.15
    hole = nb.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    nb.link(vor.outputs["Distance"], hole.inputs["Value"])
    hole.inputs["From Min"].default_value, hole.inputs["From Max"].default_value = 0.10, 0.22
    land = nb.math("SUBTRACT", 1.0, hole.outputs[0])
    nrm = _bump(nb, land, 0.0012, 1.0)
    _, fac, a, b, col = _mix_rgba(nb)
    nb.link(hole.outputs[0], fac)
    a.default_value = hexlin("#2a2b28")
    b.default_value = hexlin("#0b0b0b")
    rough = nb.n("ShaderNodeMapRange")
    nb.link(hole.outputs[0], rough.inputs["Value"])
    rough.inputs["To Min"].default_value, rough.inputs["To Max"].default_value = 0.55, 0.95
    _principled(nb, mat, col, rough.outputs["Result"], nrm.outputs[0], Sheen_Weight=0.7,
                Sheen_Roughness=0.3, Specular_IOR_Level=0.4)


def foam(mat, base=hexlin("#1d1e1c")):
    """BP-02 XLPE (Minicel class) closed-cell foam: matte, fine cell bump."""
    nb = NB(mat)
    nz = _obj_noise(nb, 900.0, detail=2.0)
    nrm = _bump(nb, nz.outputs["Fac"], 0.0003, 0.6)
    _principled(nb, mat, base, 0.82, nrm.outputs[0], Sheen_Weight=0.15, Specular_IOR_Level=0.3)


def solid(mat, base, rough, metallic=0.0, coat=0.0, spec=0.5, noise_bump=0.0, image=None, coat_rough=0.06):
    nb = NB(mat)
    col = base
    if image is not None:
        tc = nb.n("ShaderNodeTexCoord")
        tex = nb.n("ShaderNodeTexImage", interpolation="Cubic")
        tex.image = image
        nb.link(tc.outputs["UV"], tex.inputs["Vector"])
        col = tex.outputs["Color"]
    nrm = None
    if noise_bump:
        nz = _obj_noise(nb, 400.0, detail=2.0)
        nrm = _bump(nb, nz.outputs["Fac"], 0.0002, noise_bump).outputs[0]
    _principled(nb, mat, col, _rough_var(nb, rough, 0.04), nrm, Metallic=metallic, Coat_Weight=coat,
                Coat_Roughness=coat_rough, Specular_IOR_Level=spec)


def _orig_params(mat):
    """(base colour RGBA linear, image or None) from the imported glTF material."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return (0.5, 0.5, 0.5, 1.0), None
    sock = bsdf.inputs["Base Color"]
    img = None
    if sock.is_linked:
        n = sock.links[0].from_node
        seen = 0
        while n is not None and n.type != "TEX_IMAGE" and seen < 6:
            ins = [i for i in n.inputs if i.is_linked]
            n = ins[0].links[0].from_node if ins else None
            seen += 1
        img = n.image if n is not None and n.type == "TEX_IMAGE" else None
    return tuple(sock.default_value), img


def build_materials(camo_png: Path | None, camo_repeat_mm=380.0, uv_mm=500.0):
    """Replace every imported glTF material by name. UV units: 1 = geom.TILE_MM (500 mm) on fabric,
    1 = one camo repeat (380 mm, owner_base.yaml accent) on camo parts (export.py rescales those UVs)."""
    bpy = _bpy()
    camo_img = bpy.data.images.load(str(camo_png)) if camo_png else None
    done = []
    for mat in list(bpy.data.materials):
        if not mat.node_tree:
            continue
        name = mat.name.split(".")[0]
        base, img = _orig_params(mat)
        if name == "camo_owner_base":
            fabric(mat, None, uv_mm=camo_repeat_mm, rough=0.8, image=camo_img or img, sheen=0.4)
        elif name == "cordura_body":
            fabric(mat, base, uv_mm=uv_mm, rough=0.76, grid_mm=6.0, sheen=0.45)
        elif name == "harness_shell":
            fabric(mat, base, uv_mm=uv_mm, rough=0.78, grid_mm=6.0, sheen=0.4, wrinkles=0.6)
        elif name == "tpu_840d":      # 840D TPU-laminated: heavier weave, satin film
            fabric(mat, base, uv_mm=uv_mm, rough=0.6, grid_mm=None, weave_mm=1.3, sheen=0.25, spec=0.5,
                   coat=0.25, wrinkles=0.7)
        elif name == "binding_trim":
            fabric(mat, base, uv_mm=uv_mm, rough=0.72, grid_mm=None, weave_mm=0.8, sheen=0.55, wrinkles=0.0)
        elif name in ("webbing", "meat_strap_38mm"):
            webbing(mat, base, uv_mm)
        elif name == "spacer_mesh":
            spacer_mesh(mat, uv_mm)
        elif name == "xlpe_foam":
            foam(mat)
        elif name in ("pom_black", "anodized_black"):
            solid(mat, hexlin("#141415"), 0.5, spec=0.4, noise_bump=0.3)
        elif name == "aluminium_7075":   # G-hooks, links, sliders: black hard-anodised
            solid(mat, hexlin("#1b1c1e"), 0.42, metallic=0.75, spec=0.5)
        elif name == "titanium":
            solid(mat, hexlin("#8e9094"), 0.38, metallic=1.0)
        elif name == "carbon_twill":
            solid(mat, base, 0.32, image=img, coat=0.9, spec=0.5)
        elif name == "carbon_peelply":
            solid(mat, base, 0.6, image=img, spec=0.4, noise_bump=0.4)
        elif name == "printed_cf_nylon":
            solid(mat, hexlin("#232426"), 0.68, spec=0.35, noise_bump=0.6)
        elif name == "hypalon":
            solid(mat, base, 0.58, spec=0.4, coat=0.15, coat_rough=0.4, noise_bump=0.5)
        elif name == "clay":             # mannequin: matte grey
            solid(mat, hexlin("#9a9a98"), 0.72, spec=0.3)
        elif name == "game_bag_cotton":
            fabric(mat, None, uv_mm=uv_mm, rough=0.95, grid_mm=None, weave_mm=1.0, sheen=0.6, image=img, spec=0.2)
        else:                            # bone, anything new: keep the colour, sensible satin
            solid(mat, base, 0.6, image=img)
        done.append(name)
    return done


def setup_scene(samples: int, res=(1600, 1200), threads=4):
    bpy = _bpy()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    try:
        cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        cy.denoising_prefilter = "ACCURATE"
    except Exception:  # noqa: BLE001
        pass
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 3, 3
    cy.transmission_bounces, cy.transparent_max_bounces = 2, 4
    cy.caustics_reflective = cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    sc.render.threads_mode = "FIXED"
    sc.render.threads = threads
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.view_settings.exposure = 0.0
    # world: soft studio "HDRI" - warm floor bounce, bright horizon, cooler zenith
    w = bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.35, (0.30, 0.28, 0.25, 1)
    cr.elements[1].position, cr.elements[1].color = 0.5, (0.95, 0.94, 0.90, 1)
    e = cr.elements.new(0.85)
    e.color = (0.70, 0.74, 0.80, 1)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.25
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return sc


def _area(name, energy, size, color, size_y=None):
    bpy = _bpy()
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.shape = "RECTANGLE"
    ld.size = size
    ld.size_y = size_y or size
    ob = bpy.data.objects.new(name, ld)
    ob["e0"] = energy
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _aim(ob, target):
    from mathutils import Vector  # noqa: PLC0415
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


RIG_R0 = 2.6     # m: rig radius the light energies are set for; closer rigs are dimmed by (r / R0)^2


def place_rig(rig, cam_az, tgt, radius):
    """Key (warm, camera-left high), fill (cool, camera-right low), rim (behind, high), all softboxes.
    Energy scales with radius^2 so close-ups expose like full views."""
    for ob, (daz, el, r_mul) in zip(rig, ((-30, 40, 1.0), (70, 15, 1.2), (160, 48, 1.0))):
        ob.data.energy = ob["e0"] * (radius * r_mul / RIG_R0) ** 2
        a, e = math.radians(cam_az + daz), math.radians(el)
        d = view_dir(math.degrees(a), math.degrees(e))
        ob.location = tuple(t + radius * r_mul * x for t, x in zip(tgt, d))
        _aim(ob, tgt)


def visible_bounds(objs):
    from mathutils import Vector  # noqa: PLC0415
    lo, hi = [1e9] * 3, [-1e9] * 3
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
    return tuple(lo), tuple(hi)


def composite(rgba_png: Path, out_png: Path, caption="", sub=""):
    """Transparent Cycles frame (incl. shadow-catcher shadows) over the viewer's seamless backdrop."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: PLC0415
    fg = Image.open(rgba_png).convert("RGBA")
    w, h = fg.size
    import numpy as np  # noqa: PLC0415
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - 0.5 * w) / (1.2 * w), (yy - 0.38 * h) / (0.9 * h)) * 2
    stops = np.array([0.0, 0.48, 1.0])
    cols = np.array([[251, 250, 247], [236, 235, 229], [207, 205, 196]], float)
    bg = np.stack([np.interp(r, stops, cols[:, k]) for k in range(3)], -1)
    bg += 0.5     # round, not floor (no noise: it would triple the PNG size and force quantising)
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    im.alpha_composite(fg)
    im = im.convert("RGB")
    if caption:
        d = ImageDraw.Draw(im)
        try:
            f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.030))
            f2 = ImageFont.truetype("DejaVuSans.ttf", int(h * 0.021))
        except OSError:
            f1 = f2 = ImageFont.load_default()
        x0, y0 = int(w * 0.03), int(h * 0.90)
        d.text((x0, y0), caption, fill=(38, 38, 34), font=f1)
        d.text((x0, y0 + int(h * 0.042)), sub, fill=(98, 97, 90), font=f2)
    im.save(out_png, optimize=True)
    _ = ImageFilter
    return out_png


def render_views(glb: Path, views: list[str], samples: int, out_dir: Path, prefix: str, manifest=None,
                 camo_png: Path | None = None, res=(1600, 1200), torso=19, captions=True, threads=4,
                 work_dir: Path | None = None, start_index=1) -> list[dict]:
    bpy = _bpy()
    t0 = time.time()
    parts = load_manifest(glb, manifest)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    sc = setup_scene(samples, res, threads)
    mats = build_materials(camo_png)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # shadow-catcher floor
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    fm = bpy.data.materials.new("floor")
    solid(fm, hexlin("#d9d6cd"), 0.9, spec=0.2)
    floor.data.materials.append(fm)
    # camera (sensor fit vertical -> fov matches three.js vertical fov)
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    key = _area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2)
    fill = _area("fill", 18.0, 2.4, (0.88, 0.93, 1.0), 1.6)
    rim = _area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0)
    print(f"setup {time.time() - t0:.1f} s, {len(meshes)} meshes, materials: {sorted(set(mats))}")
    work = Path(work_dir or out_dir)
    work.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for k, vname in enumerate(views):
        shot = SHOTS.get(vname, {"view": vname, "state": {}, "caption": f"CORRIE: {vname}", "sub": ""})
        state = {**shot["state"], "torso": torso}
        vis = []
        for ob in meshes:
            on = visible_for(parts.get(ob.name), ob.name, state)
            ob.hide_render = not on
            if on:
                vis.append(ob)
        lo, hi = visible_bounds(vis)
        floor.location = (0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2] - 0.001)
        v = VIEWS[shot["view"]]
        bmin, bmax = fcs_box_to_blender(v["box"]) if "box" in v else (lo, hi)
        fov = v.get("fov", 30.0)
        cd.angle_y = math.radians(fov)
        pos, tgt = fit_camera(bmin, bmax, v["az"], v["el"], fov, res[0] / res[1], v["zoom"])
        cam.location = pos
        _aim(cam, tgt)
        dist = math.dist(pos, tgt)
        cd.dof.use_dof = True
        cd.dof.focus_distance = dist
        cd.dof.aperture_fstop = 4.0 if dist > 2.0 else 5.6     # mild: the whole bag stays sharp
        place_rig((key, fill, rim), v["az"], tgt, max(2.2, 0.75 * dist))
        raw = work / f"_raw_{prefix}_{vname}.png"
        sc.render.filepath = str(raw)
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t1
        n = start_index + k
        out = out_dir / f"{prefix}_{n}.png"
        composite(raw, out, shot["caption"] if captions else "", shot["sub"] if captions else "")
        shrink_png(out)
        results.append({"view": vname, "file": str(out), "seconds": round(dt, 1),
                        "mb": round(out.stat().st_size / 1e6, 2)})
        print(f"[{vname}] {out} {dt:.0f} s render, {out.stat().st_size / 1e6:.2f} MB", flush=True)
    return results


def before_after(before_png: Path, after_png: Path, out_png: Path, width=2400):
    """Side-by-side sheet: three.js (before) | Cycles (after), same view and state."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    a, b = Image.open(before_png).convert("RGB"), Image.open(after_png).convert("RGB")
    b = b.resize(a.size, Image.LANCZOS)
    head = 130
    im = Image.new("RGB", (a.width + b.width + 12, a.height + head), (244, 243, 239))
    im.paste(a, (0, head))
    im.paste(b, (a.width + 12, head))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
        fs = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        f = fs = ImageFont.load_default()
    d.text((30, 14), "BEFORE: three.js raster", fill=(30, 30, 30), font=f)
    d.text((30, 72), "flat PBR, shadow map, 1024 px camo", fill=(95, 95, 88), font=fs)
    d.text((a.width + 42, 14), "AFTER: Blender Cycles path trace", fill=(30, 30, 30), font=f)
    d.text((a.width + 42, 72), "fabric sheen + ripstop bump, soft area lights, contact shadows, AgX",
           fill=(95, 95, 88), font=fs)
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    im.save(out_png, optimize=True)
    shrink_png(out_png)
    return out_png


def main(argv=None):
    if "--" in (argv or sys.argv):
        argv = (argv or sys.argv)[(argv or sys.argv).index("--") + 1:]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--glb", default=str(REPO / "outputs" / "pack3d_corrie" / "corrie.glb"))
    ap.add_argument("--manifest", default=None, help="parts JSON (default: <glb stem>_viewer.html next to it)")
    ap.add_argument("--views", default="rear34,side,door,wing,hero",
                    help=f"comma list from {sorted(SHOTS)} or raw viewer views {sorted(VIEWS)}")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--out", default=str(REPO / "outputs" / "screens"))
    ap.add_argument("--prefix", default=time.strftime("%Y%m%d") + "_cycles")
    ap.add_argument("--start", type=int, default=1, help="number of the first output file")
    ap.add_argument("--res", default="1600x1200")
    ap.add_argument("--torso", type=float, default=19)
    ap.add_argument("--camo", default=None, help="camo PNG (one 380 mm repeat); default: re-raster owner SVG")
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--no-caption", action="store_true")
    ap.add_argument("--before", default=None, help="three.js PNG of the 'hero' view -> before/after sheet")
    ap.add_argument("--before-out", default=None, help="before/after sheet path (default <out>/<prefix>_0.png)")
    a = ap.parse_args(argv)
    res = tuple(int(x) for x in a.res.lower().split("x"))
    glb = Path(a.glb).resolve()
    out = Path(a.out).resolve()
    work = REPO / "outputs" / "cycles_work"
    camo = Path(a.camo) if a.camo else owner_camo_png(work)
    views = [v.strip() for v in a.views.split(",") if v.strip()]
    t0 = time.time()
    res_ = render_views(glb, views, a.samples, out, a.prefix, a.manifest, camo, res, a.torso,
                        not a.no_caption, a.threads, work, a.start)
    if a.before:
        hero = next((r["file"] for r in res_ if r["view"] == "hero"), None)
        if hero:
            sheet = Path(a.before_out) if a.before_out else out / f"{a.prefix}_0.png"
            before_after(Path(a.before), Path(hero), sheet)
            print("before/after", sheet, f"{sheet.stat().st_size / 1e6:.2f} MB")
    (work / f"{a.prefix}_timing.json").write_text(json.dumps(
        {"samples": a.samples, "res": res, "threads": a.threads, "total_s": round(time.time() - t0, 1),
         "frames": res_}, indent=2))
    print(f"total {time.time() - t0:.0f} s")
    return res_


if __name__ == "__main__":
    main()
