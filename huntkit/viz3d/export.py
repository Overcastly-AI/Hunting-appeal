"""GLB export (glTF binary, PBR materials + textures) and the viewer part manifest.

Axis change at export: FCS mm (x lateral, y aft, z up) -> glTF metres, +Y up:
    X = x/1000, Y = z/1000, Z = y/1000
The FCS is LEFT-handed as labelled (x+ = wearer's right, y+ aft, z up), so this map is a
reflection: face winding is reversed at export to keep outward normals. Result: seen from behind
(camera on +Z), the wearer's right is on screen right, as in the concept sketches. (Before v3 the
map was X = -x, a proper rotation that rendered x+ on the wearer's LEFT.)
So the bag's outer face looks toward +Z and the wearer stands at -Z.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
from trimesh.visual import ColorVisuals, TextureVisuals
from trimesh.visual.material import PBRMaterial

from . import geom as G
from . import textures as TX
from .params import REPO

M_FCS_TO_GLTF = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]]) / 1000.0
FLIP_WINDING = np.linalg.det(M_FCS_TO_GLTF) < 0


def to_gltf(v):
    return np.asarray(v, float) @ M_FCS_TO_GLTF.T


def colorway(p: dict) -> dict:
    """Body / trim / harness hex from designs/apparel/colorways.yaml (accent pairing id)."""
    out = {"body": "#6E745B", "trim": "#2D2B27", "harness": "#4A4B3C", "name": p.get("colorway", "talus")}
    try:
        import yaml
        cw = yaml.safe_load((REPO / "designs" / "apparel" / "colorways.yaml").read_text())
        solids = {s["key"]: s["hex"] for s in cw["solids"]}
        pair = next(a for a in cw["accent_pairings"] if a["id"] == p.get("colorway", "talus"))
        out.update(body=solids[pair["body"]], trim=solids[pair["trim"]], name=pair["display_name"])
        out["harness"] = solids.get("spruce_shadow", out["harness"])   # colorways.yaml: pack harness & hipbelt
    except Exception:  # noqa: BLE001
        pass
    return out


def _hex_factor(h, a=1.0):
    """glTF baseColorFactor is LINEAR: convert the sRGB hex."""
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = TX.hex_rgb(h)
    return [round(lin(r), 5), round(lin(g), 5), round(lin(b), 5), a]


def build_materials(p: dict) -> tuple[dict, dict]:
    cw = colorway(p)
    camo, camo_src = TX.owner_base_camo(1024)
    rip = TX.ripstop_normal(512)
    knit = TX.knit_mesh_normal(512)
    foam = TX.foam_normal(256)
    twill = TX.carbon_twill(512)

    def fab(name, hexc, normal=rip, rough=0.9, tex=None):
        return PBRMaterial(name=name, baseColorFactor=_hex_factor(hexc) if tex is None else None,
                           baseColorTexture=tex, normalTexture=normal, metallicFactor=0.0, roughnessFactor=rough)
    mats = {
        "carbon": PBRMaterial(name="carbon_twill", baseColorTexture=twill, metallicFactor=0.3, roughnessFactor=0.35),
        "fitting": PBRMaterial(name="anodized_black", baseColorFactor=_hex_factor("#1c1d20"), metallicFactor=0.55,
                               roughnessFactor=0.42),
        "printed_cf": PBRMaterial(name="printed_cf_nylon", baseColorFactor=_hex_factor("#2b2c2f"), metallicFactor=0.05,
                                  roughnessFactor=0.72),
        "hdpe": PBRMaterial(name="hdpe_framesheet", baseColorFactor=_hex_factor("#dedbd2"), metallicFactor=0.0,
                            roughnessFactor=0.6),
        # wet-layup board with peel-ply faces: satin, not clear-coated (spreader BP-06)
        "carbon_matte": PBRMaterial(name="carbon_peelply", baseColorTexture=twill, metallicFactor=0.15,
                                    roughnessFactor=0.62),
        "aluminium": PBRMaterial(name="aluminium_7075", baseColorFactor=_hex_factor("#aeb2b8"), metallicFactor=0.9,
                                 roughnessFactor=0.32),
        "hypalon": PBRMaterial(name="hypalon", baseColorFactor=_hex_factor("#6a5a45"), metallicFactor=0.0,
                               roughnessFactor=0.55),
        # BP-02 rails / hood lining: black XLPE (Minicel class), not pale grey (read as a white board in renders)
        "xlpe": PBRMaterial(name="xlpe_foam", baseColorFactor=_hex_factor("#1e1f1d"), normalTexture=foam,
                            metallicFactor=0.0, roughnessFactor=0.9),
        "titanium": PBRMaterial(name="titanium", baseColorFactor=_hex_factor("#b4b6ba"), metallicFactor=0.85,
                                roughnessFactor=0.45),
        "hardware": PBRMaterial(name="pom_black", baseColorFactor=_hex_factor("#202020"), metallicFactor=0.0,
                                roughnessFactor=0.55),
        "body": fab("cordura_body", cw["body"]),
        "pocket": fab("ultragrid_pocket", cw["body"], rough=0.85),
        "tpu": fab("tpu_840d", cw["harness"], rough=0.62),
        "trim": fab("binding_trim", cw["trim"], rough=0.85),
        "webbing": fab("webbing", cw["trim"], normal=foam, rough=0.8),
        "meat_strap": fab("meat_strap_38mm", "#cdbf9f", normal=foam, rough=0.8),   # v3.1 MEAT family (bone/stone webbing)
        "harness": fab("harness_shell", cw["harness"], normal=rip, rough=0.88),
        "spacer": fab("spacer_mesh", "#262724", normal=knit, rough=0.95),   # BP-01 black spacer mesh
        "camo": fab("camo_owner_base", "#ffffff", tex=camo),
        "game_bag": fab("game_bag_cotton", "#ffffff", normal=knit, rough=1.0, tex=TX.game_bag(512)),
        "bone": PBRMaterial(name="bone", baseColorFactor=_hex_factor("#e7dcc2"), metallicFactor=0.0, roughnessFactor=0.6),
        "blaze": fab("blaze_orange", "#ff5b14", rough=0.8),
        "clay": PBRMaterial(name="clay", baseColorFactor=_hex_factor("#cdc8be"), metallicFactor=0.0, roughnessFactor=0.78),
        "fea": PBRMaterial(name="fea_utilization", baseColorFactor=[1, 1, 1, 1], metallicFactor=0.0, roughnessFactor=0.5),
    }
    info = {"camo_source": camo_src, "colorway": cw}
    return mats, info


def scene_from_pack(pack, mats: dict) -> trimesh.Scene:
    scene = trimesh.Scene()
    for prt in pack.parts:
        m = prt.mesh
        v = to_gltf(m.vertices)
        tm = trimesh.Trimesh(vertices=v, faces=(m.faces[:, ::-1] if FLIP_WINDING else m.faces).copy(), process=False)
        if prt.colors is not None:
            tm.visual = ColorVisuals(tm, vertex_colors=prt.colors)
        else:
            uv = m.metadata.get("uv")
            if uv is None or len(uv) != len(v):
                uv = np.zeros((len(v), 2))
            if prt.material == "camo":     # owner base ACCENT repeat (owner_base.yaml) on small panels
                uv = uv * G.TILE_MM / pack.params.get("camo_repeat_mm", 380.0)
            tm.visual = TextureVisuals(uv=uv, material=mats[prt.material])
        scene.add_geometry(tm, node_name=prt.name, geom_name=prt.name)
    return scene


def manifest(pack) -> dict:
    parts = {}
    for prt in pack.parts:
        parts[prt.name] = {"group": prt.group, "torso": prt.torso, "modes": list(prt.modes),
                           "variant": getattr(prt, "variant", None),
                           "material": prt.material, "label": prt.label,
                           "explode": to_gltf(prt.explode).round(4).tolist(),
                           "haul": to_gltf(prt.haul).round(4).tolist(),
                           "floats": bool(getattr(prt, "floats", False)), "gap": getattr(prt, "gap", None),
                           "xray": bool(getattr(prt, "xray", False))}
    return parts


def export_glb(pack, path, mats=None) -> tuple[Path, dict]:
    if mats is None:
        mats, info = build_materials(pack.params)
    else:
        info = {}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = scene_from_pack(pack, mats)
    path.write_bytes(dedupe_glb(trimesh.exchange.gltf.export_glb(scene, include_normals=True)))
    return path, info


def write_metrics(pack, path, extra=None):
    m = dict(pack.metrics)
    m.update(extra or {})
    Path(path).write_text(json.dumps(m, indent=2, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def dedupe_glb(glb: bytes) -> bytes:
    """trimesh embeds a texture once per material; drop byte-identical images and rebuild the
    binary chunk (keeps the GLB small enough to inline in the viewer)."""
    import hashlib
    import struct
    jl = struct.unpack("<I", glb[12:16])[0]
    j = json.loads(glb[20:20 + jl])
    b0 = 20 + jl
    bl = struct.unpack("<I", glb[b0:b0 + 4])[0]
    bin_ = glb[b0 + 8:b0 + 8 + bl]
    views = j["bufferViews"]

    def vbytes(i):
        v = views[i]
        o = v.get("byteOffset", 0)
        return bin_[o:o + v["byteLength"]]
    first, img_map = {}, {}
    for i, im in enumerate(j.get("images", [])):
        h = hashlib.sha1(vbytes(im["bufferView"])).hexdigest()
        img_map[i] = first.setdefault(h, i)
    for t in j.get("textures", []):
        t["source"] = img_map[t["source"]]
    used_imgs = sorted(set(img_map.values()))
    new_img_idx = {old: k for k, old in enumerate(used_imgs)}
    for t in j.get("textures", []):
        t["source"] = new_img_idx[t["source"]]
    j["images"] = [j["images"][i] for i in used_imgs] if used_imgs else j.get("images", [])
    used_views = sorted({a["bufferView"] for a in j.get("accessors", []) if "bufferView" in a}
                        | {im["bufferView"] for im in j.get("images", [])})
    out, new_views, vmap = bytearray(), [], {}
    for i in used_views:
        while len(out) % 4:
            out.append(0)
        v = dict(views[i])
        data = vbytes(i)
        v["byteOffset"] = len(out)
        v["buffer"] = 0
        out += data
        vmap[i] = len(new_views)
        new_views.append(v)
    while len(out) % 4:
        out.append(0)
    for a in j.get("accessors", []):
        if "bufferView" in a:
            a["bufferView"] = vmap[a["bufferView"]]
    for im in j.get("images", []):
        im["bufferView"] = vmap[im["bufferView"]]
    j["bufferViews"] = new_views
    j["buffers"] = [{"byteLength": len(out)}]
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(out)
    return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(out), 0x004E4942) + bytes(out))
