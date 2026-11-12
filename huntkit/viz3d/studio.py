"""Product-photography renders of any bag concept (BL-018): one entry point, ``studio.render``.

    from huntkit.viz3d import studio
    sc = studio.ConceptScene("my_bag")
    sc.add_fabric("body", drape_mesh, "body")                   # cloth-sim drape, UV = flat pattern mm / 500
    sc.add_seams_from_pieces(V, F, piece_of_tri, normals)        # ridge + topstitch + pucker on every piece boundary
    sc.add_strap("lid_strap", path, normals, 25.0, tail=80)      # webbing with thickness; dents the cloth
    sc.add_hardware("lid_buckle", "side_release_25", p, n, t)    # real buckle + the webbing wrapped through it
    sc.add_zip("door_zip", path, normals, size=10, sliders=(0.05,))
    studio.render(sc, studio.shots("hero", "side", "front34"), "outputs/screens", prefix="20261111_mybag")

Two stages, because ``bpy`` only installs for CPython 3.11 and the geometry needs scipy / trimesh / manifold3d:

1. ``ConceptScene.build`` (any Python with the repo requirements) runs the modelling layer in
   ``huntkit.viz3d.assets`` and writes ``<work>/<name>.glb`` + ``<name>.scene.json``;
2. ``render_scene`` (inside Blender's Python) imports the GLB, builds the per-fabric shaders, the studio (paper
   sweep, three softboxes + top strip, gradient world, depth of field) and renders each shot with Cycles.

``render`` runs stage 2 in-process when ``bpy`` imports, else as a subprocess of the interpreter named by
``bpy_python=`` or the ``HUNTKIT_BPY`` environment variable. See huntkit/viz3d/README.md.
"""
from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import math
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "outputs" / "studio_work"

FABRIC_KEYS = ("body", "camo", "tpu", "harness", "pocket", "ultra", "lining")
QUALITY = {"quick": {"res": (800, 600), "samples": 16}, "preview": {"res": (1200, 900), "samples": 40},
           "final": {"res": (1600, 1200), "samples": 72}}

# ------------------------------------------------------------------------------------------------ materials
# key -> shader spec. ``hex`` None = colourway (designs/apparel/colorways.yaml via export.colorway).
# Fabric numbers: weave pitch / ripstop grid are ASSUMPTION per fabric class (yarn count is not in the records;
# count the threads of the purchased roll); what the records do give (weave type, coating, thickness) picks the
# shader family: data/materials/textiles/<record>.yaml named in ``record``.
MATERIALS = {
    "body": {"shader": "fabric", "record": "cordura_330d_nylon66", "color": "body", "weave_mm": 0.42, "grid_mm": 0,
             "rough": 0.80, "sheen": 0.22},
    "camo": {"shader": "fabric", "record": "polyester_ht_630d_printable", "color": "camo", "weave_mm": 0.55,
             "grid_mm": 0, "rough": 0.82, "sheen": 0.4},
    "tpu": {"shader": "fabric", "record": "tpu_coated_nylon_840d", "color": "harness", "weave_mm": 1.2, "basket": 1,
            "grid_mm": 0, "rough": 0.62, "sheen": 0.25, "coat": 0.2},
    "harness": {"shader": "fabric", "record": "cordura_330d_nylon66", "color": "harness", "weave_mm": 0.42,
                "grid_mm": 0, "rough": 0.8, "sheen": 0.45},
    "pocket": {"shader": "fabric", "record": "robic_100d_ripstop", "color": "body", "weave_mm": 0.25, "grid_mm": 4.0,
               "rough": 0.7, "sheen": 0.35},
    "ultra": {"shader": "fabric", "record": "ultragrid_210d_uhmwpe_ripstop", "color": "body", "weave_mm": 0.3,
              "grid_mm": 6.0, "grid_white": 1, "rough": 0.55, "sheen": 0.2, "coat": 0.3},
    "lining": {"shader": "fabric", "record": "robic_100d_ripstop", "color": "harness", "weave_mm": 0.25,
               "grid_mm": 4.0, "rough": 0.75, "sheen": 0.3},
    "trim": {"shader": "fabric", "record": "binding grosgrain", "color": "trim", "weave_mm": 0.9, "rib": 1,
             "grid_mm": 0, "rough": 0.72, "sheen": 0.55},
    "webbing": {"shader": "webbing", "record": "nylon_webbing_25mm", "color": "trim"},
    "meat_strap": {"shader": "webbing", "record": "poly_webbing_38mm", "hex": "#cdbf9f"},
    "elastic": {"shader": "webbing", "record": "silicone_gripper_elastic_25mm", "hex": "#1b1b1a", "pick_mm": 0.7},
    "thread": {"shader": "thread", "record": "bonded_nylon_tex70", "color": "trim"},
    "zip_tape": {"shader": "fabric", "record": "coil_zipper_10", "color": "trim", "weave_mm": 0.5, "twill": 1,
                 "grid_mm": 0, "rough": 0.7, "sheen": 0.5},
    "zip_coil": {"shader": "plastic", "hex": "#1a1a1b", "rough": 0.33},
    "zip_metal": {"shader": "metal", "hex": "#26272a", "rough": 0.42, "paint": 1},
    "cord": {"shader": "cord", "color": "trim"},
    "grip": {"shader": "rubber", "hex": "#222220"},
    "spacer": {"shader": "spacer", "record": "spacer_mesh_3d"},
    "xlpe": {"shader": "foam"},
    "hypalon": {"shader": "hypalon", "record": "hypalon_coated_nylon", "hex": "#6a5a45"},
    "hardware": {"shader": "plastic", "hex": "#161617", "rough": 0.42},
    "aluminium": {"shader": "metal", "hex": "#2a2b2e", "rough": 0.40},
    "fitting": {"shader": "metal", "hex": "#1f2023", "rough": 0.45},
    "titanium": {"shader": "metal", "hex": "#8e9094", "rough": 0.36, "bare": 1},
    "printed_cf": {"shader": "printed"},
    "carbon": {"shader": "carbon", "coat": 0.9, "rough": 0.3},
    "carbon_matte": {"shader": "carbon", "coat": 0.0, "rough": 0.6},
    "hdpe": {"shader": "plastic", "hex": "#dedbd2", "rough": 0.5},
    "clay": {"shader": "form"},
    "form": {"shader": "form"},
    "stand": {"shader": "metal", "hex": "#1d1d1e", "rough": 0.5},
    "game_bag": {"shader": "fabric", "hex": "#e6dfcf", "weave_mm": 1.0, "grid_mm": 0, "rough": 0.95, "sheen": 0.6},
    "bone": {"shader": "plastic", "hex": "#e7dcc2", "rough": 0.6},
    "blaze": {"shader": "fabric", "hex": "#ff5b14", "weave_mm": 0.4, "grid_mm": 0, "rough": 0.8, "sheen": 0.4},
}
HARD_SHADERS = ("plastic", "metal", "printed", "rubber")

# ---------------------------------------------------------------------------------------------------- shots
# az deg: 0 = looking at the bag's outer (aft) face, +90 = from the wearer's right, 180 = from the front; el deg;
# ``box`` FCS mm [x0, y0, z0, x1, y1, z1] frames a detail; ``at`` FCS mm + ``span`` mm frames a macro.
PRESETS = {
    "hero": {"view": {"az": -38, "el": 12, "fov": 24, "fstop": 11, "frame": "pack"},
             "state": {"mannequin": True, "lid": True}, "caption": "3/4 rear"},
    "side": {"view": {"az": 90, "el": 4, "fov": 24, "fstop": 11, "frame": "pack"},
             "state": {"mannequin": True, "lid": True}, "caption": "Side"},
    "front34": {"view": {"az": 152, "el": 14, "fov": 24, "fstop": 11, "frame": "pack"},
                "state": {"mannequin": True, "lid": True}, "caption": "Front 3/4"},
    "macro": {"view": {"az": -20, "el": 20, "fov": 14, "fstop": 5.6, "span": 150},
              "state": {"mannequin": True, "lid": True}, "caption": "Detail"},
}


def shots(*names, **overrides) -> dict:
    """Shot dict from preset names: ``shots("hero", "side")``; override any with ``name={"view": {...}}``."""
    out = {n: json.loads(json.dumps(PRESETS[n])) for n in names}
    for n, o in overrides.items():
        base = out.setdefault(n, json.loads(json.dumps(PRESETS[o.get("preset", "macro")])))
        for k, v in o.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = v
    return out


# ============================================================================================ stage 1: build
@dataclass
class SPart:
    name: str
    mesh: object
    material: str
    group: str = "bag"
    modes: tuple = ("pack", "pack_haul", "frame", "frame_haul")
    torso: float | None = None
    variant: str | None = None
    gap: float | None = None
    label: str = ""
    drape: bool = False                # run the fabric realism pass on it
    look: object | None = None         # assets.fabric.Look override
    max_edge: float | None = None      # refine target, mm
    thickness: float = 0.0             # cloth thickness to add at free edges, mm
    uv_is_pattern: bool = False        # UVs are the flat pattern (strain field is meaningful)
    lining: str | None = None          # material of a lining built 1.2 mm inside the (displaced) cloth

    def vis(self) -> dict:
        return {"group": self.group, "modes": list(self.modes), "torso": self.torso, "variant": self.variant,
                "gap": self.gap}


class ConceptScene:
    """What a concept hands to the studio: meshes with materials, plus the things the modelling layer builds for it
    (fabric realism, seams, straps, hardware, zips). All coordinates FCS mm."""

    def __init__(self, name: str, colorway: str = "talus", camo_repeat_mm: float = 380.0, seed: float = 0.0):
        self.name = name
        self.parts: list[SPart] = []
        self.seam_lines: list = []
        self.strap_lines: list = []
        self.colorway = colorway
        self.camo_repeat_mm = camo_repeat_mm
        self.seed = seed
        self.report: dict = {"fabric": {}, "counts": {}}
        self.materials = json.loads(json.dumps(MATERIALS))

    # ---- generic parts
    def add_part(self, name, mesh, material, **kw) -> SPart:
        p = SPart(name, mesh, material, **kw)
        self.parts.append(p)
        self._extras(p)
        return p

    def _extras(self, p: SPart):
        """Side meshes of other materials carried in mesh.metadata['extras'] become sibling parts; strap records
        become dent lines for the fabric pass."""
        from .assets import concat
        md = getattr(p.mesh, "metadata", {})
        for mat, lst in md.get("extras", {}).items():
            q = dataclasses.replace(p, name=f"{p.name}__{mat}", mesh=concat(lst), material=mat, label="", drape=False,
                                    thickness=0.0)
            q.mesh.metadata.pop("extras", None)
            self.parts.append(q)
        for rec in md.get("straps", []):
            if p.variant in (None, "lid", "rolled"):
                self.strap_lines.append((rec["P"], rec["width"]))
        md.pop("extras", None)

    def add_fabric(self, name, mesh, material="body", look=None, max_edge=3.5, thickness=0.0, uv_is_pattern=True,
                   **kw) -> SPart:
        return self.add_part(name, mesh, material, drape=True, look=look, max_edge=max_edge, thickness=thickness,
                             uv_is_pattern=uv_is_pattern, **kw)

    # ---- seams
    def add_seam(self, name, P, N, side=1.0, material="body", rows=1, dent=True, **kw):
        from .assets import seams as SM
        s = SM.seam(P, N, side=side, rows=rows, seed=len(self.seam_lines) + self.seed)
        if dent:
            self.seam_lines.append(P)
        if len(s["ridge"].faces):
            self.add_part(f"{name}__ridge", s["ridge"], material, **kw)
            self.add_part(f"{name}__thread", s["thread"], "thread", **kw)

    def add_seams_from_pieces(self, V, F, piece, normals, name="seams", material="body", skip=(), project=None,
                              min_len=12.0, smooth=9.0, **kw):
        """Every boundary between two pattern pieces of a drape mesh becomes a seam. ``skip`` = pairs handled
        elsewhere (a zip). ``project(P) -> (P on the skin, normals)`` re-seats the smoothed line."""
        import numpy as np
        from .assets import arclen, concat
        from .assets import seams as SM
        rid, thr = [], []
        skip = {tuple(sorted(s)) for s in skip}
        for a, b, ch in SM.shared_seams(V, F, piece):
            if (a, b) in skip or len(ch) < 4:
                continue
            P = SM.smooth_path(np.asarray(V)[ch], 3.0, smooth)
            if arclen(P)[-1] < min_len:
                continue
            if project is not None:
                P, N = project(P)
            else:
                from scipy.spatial import cKDTree
                N = np.asarray(normals)[cKDTree(np.asarray(V)).query(P)[1]]
            s = SM.seam(P, N, side=1.0, seed=len(self.seam_lines) + self.seed)
            self.seam_lines.append(P)
            rid.append(s["ridge"])
            thr.append(s["thread"])
        self.add_part(f"{name}__ridge", concat(rid), material, **kw)
        self.add_part(f"{name}__thread", concat(thr), "thread", **kw)

    # ---- straps, hardware, zips
    def add_strap(self, name, P, N, width=25.0, material="webbing", tail=0.0, keeper=False, dent=True, **kw):
        """Webbing along P. ``tail`` mm of free tail continues from the last point (hanging, folded stop)."""
        import numpy as np
        from .assets import concat, unit
        from .assets import webbing as WB
        m = WB.strap(P, N, width)
        parts = [m]
        if tail > 0:
            P = np.asarray(P, float)
            Nn = np.asarray(N, float)
            n_end = Nn[-1] if Nn.ndim == 2 else Nn
            parts.append(WB.tail(P[-1], unit(P[-1] - P[-2]), n_end, tail, width, seed=len(self.strap_lines)))
        mm = concat(parts)
        if dent:
            self.strap_lines.append((m.metadata["strap"]["P"], float(width)))
        self.add_part(name, mm, material, **kw)
        if keeper:
            rec = m.metadata["strap"]
            i = int(len(rec["P"]) * 0.8)
            self.add_part(f"{name}__keeper", WB.keeper(rec["P"][i], rec["N"][i], rec["P"][i] - rec["P"][i - 1], width),
                          "elastic", **kw)

    def add_hardware(self, name, kind, p, n, t, material=None, threading=True, on_strap=True, **kw):
        """A piece from ``assets.hardware`` at p (a point ON the strap centreline or the surface), normal n, strap
        direction t. With ``on_strap`` it is lifted to sit on top of the webbing; ``threading`` adds the wraps."""
        import numpy as np
        from .assets import concat, frame, placed, with_extras
        from .assets import hardware as HW
        from .assets import webbing as WB
        sp = HW.SPECS[kind]
        R = frame(n, t)
        lift = (WB.thickness(sp.get("web", 25.0)) / 2 + 0.25 + sp["T"] / 2) if on_strap else sp["T"] / 2
        c = np.asarray(p, float) + R[:, 2] * lift
        m = placed(HW.build(kind), R, c)
        if threading:
            kit = WB.threading(kind)
            with_extras(m, webbing=[placed(q, R, c) for q in kit["webbing"]],
                        thread=[placed(q, R, c) for q in kit["thread"]])
        _ = concat
        return self.add_part(name, m, material or ("aluminium" if sp["material"] == "metal" else "hardware"), **kw)

    def add_zip(self, name, P, N, size=10, sliders=(0.04,), closed=(0.0, 1.0), pull_down=(0, 0, -1.0), dent=True,
                half=None, **kw):
        from .assets import zips as ZP
        z = ZP.coil_zip(P, N, size, sliders=sliders, closed=closed, pull_down=pull_down, half=half)
        if dent:
            self.seam_lines.append(P)
        for k, mat in (("tape", "zip_tape"), ("coil", "zip_coil"), ("slider", "zip_metal"), ("cord", "cord"),
                       ("grip", "grip"), ("thread", "thread")):
            if len(z[k].faces):
                self.add_part(f"{name}__{k}", z[k], mat, **kw)

    # ---- legacy viz3d packs
    def add_pack(self, pack, drape: dict | None = None, drop=()):
        """Take every part of a ``viz3d.model.PackModel``. ``drape`` = {part name: SPart keyword overrides} marks the
        cloth parts that get the realism pass. Parts whose mesh carries extras / strap records (built under
        ``upgraded_legacy``) bring their webbing wraps, stitches and dent lines with them."""
        drape = drape or {}
        for prt in pack.parts:
            if prt.name in drop or prt.colors is not None:
                continue
            kw = dict(group=prt.group, modes=tuple(prt.modes), torso=prt.torso, variant=prt.variant, gap=prt.gap,
                      label=prt.label)
            o = drape.get(prt.name)
            if o is not None:
                kw.update(drape=True, **o)
            self.add_part(prt.name, prt.mesh, prt.material, **kw)

    # ---- build
    def build(self, work_dir=None, verbose=True) -> Path:
        """Run the fabric pass, write ``<name>.glb`` and ``<name>.scene.json``; returns the JSON path."""
        import numpy as np
        import trimesh
        from trimesh.visual import TextureVisuals
        from trimesh.visual.material import PBRMaterial
        from . import export as EX
        from .assets import fabric as FB
        t0 = time.time()
        work = Path(work_dir or WORK / self.name)
        work.mkdir(parents=True, exist_ok=True)
        # blockers: a thinned cloud of every part's vertices, tagged by part
        clouds = {}
        for p in self.parts:
            V = np.asarray(p.mesh.vertices)
            if len(V):
                clouds[p.name] = V[:: max(1, len(V) // 6000)]
        linings = []
        for p in self.parts:
            if not p.drape or not len(p.mesh.faces):
                continue
            base = p.mesh
            m = FB.refine(base, max_edge=p.max_edge or 3.5)
            others = [c for n, c in clouds.items() if n != p.name and not n.startswith(p.name + "__")]
            lo, hi = m.vertices.min(0) - 30, m.vertices.max(0) + 30
            blk = np.vstack(others) if others else np.zeros((0, 3))
            blk = blk[np.all((blk > lo) & (blk < hi), axis=1)]
            look = p.look or FB.Look()
            kw = dict(seams=self.seam_lines, straps=self.strap_lines, blockers=blk, look=look,
                      seed=self.seed + len(self.report["fabric"]))
            if not p.uv_is_pattern:
                kw["uv_mm"] = None
            out, rep = FB.displace(m, **kw)
            rep["dev_max_mm"], rep["dev_rms_mm"] = FB.deviation(np.asarray(m.vertices), np.asarray(out.vertices))
            rep["verts"] = int(len(out.vertices))
            if p.lining:
                linings.append(dataclasses.replace(p, name=f"{p.name}__lining", mesh=FB.offset_copy(out, -1.2),
                                                   material=p.lining, drape=False, lining=None, label=""))
            if p.thickness > 0:
                out = FB.solidify(out, p.thickness)
            p.mesh = out
            self.report["fabric"][p.name] = rep
            if verbose:
                print(f"  fabric {p.name}: {rep['verts']} verts, |h| max {rep['max_abs_mm']:.2f} mm "
                      f"(limit {rep['limit_mm']}), slack {rep['slack_mean']:.2f}", flush=True)
        self.parts += linings
        # GLB
        cw = EX.colorway({"colorway": self.colorway})
        scene = trimesh.Scene()
        manifest = {}
        for p in self.parts:
            m = p.mesh
            if not len(m.faces):
                continue
            v = EX.to_gltf(m.vertices)
            tm = trimesh.Trimesh(vertices=v, faces=(m.faces[:, ::-1] if EX.FLIP_WINDING else m.faces).copy(),
                                 process=False)
            uv = m.metadata.get("uv")
            if uv is None or len(uv) != len(v):
                uv = np.zeros((len(v), 2))
            if p.material == "camo":
                uv = np.asarray(uv) * 500.0 / self.camo_repeat_mm
            tm.visual = TextureVisuals(uv=uv, material=PBRMaterial(name=p.material, baseColorFactor=[128, 128, 128, 255]))
            scene.add_geometry(tm, node_name=p.name, geom_name=p.name)
            manifest[p.name] = {**p.vis(), "material": p.material, "label": p.label}
        glb = work / f"{self.name}.glb"
        glb.write_bytes(trimesh.exchange.gltf.export_glb(scene, include_normals=True))
        self.report["counts"] = {"parts": len(manifest), "seam_lines": len(self.seam_lines),
                                 "strap_lines": len(self.strap_lines),
                                 "verts": int(sum(len(p.mesh.vertices) for p in self.parts))}
        self.report["build_s"] = round(time.time() - t0, 1)
        js = work / f"{self.name}.scene.json"
        js.write_text(json.dumps({"name": self.name, "glb": glb.name, "parts": manifest, "materials": self.materials,
                                  "colorway": cw, "camo_repeat_mm": self.camo_repeat_mm, "report": self.report},
                                 indent=1))
        if verbose:
            print(f"scene {js} ({glb.stat().st_size / 1e6:.1f} MB, {self.report['counts']}, {self.report['build_s']} s)")
        return js


# ------------------------------------------------------------------------------- legacy viz3d -> new assets
LEGACY_WRAPS = False      # BL-012: True = webbing wraps on the legacy belt ladder locks and the sternum buckle too


@contextmanager
def upgraded_legacy(belt_heavy=True):
    """While active, the legacy viz3d builders (``corrie.py``, ``corrie_b1.py``, ``model.py``) emit the new assets:
    webbing ribbons become ``assets.webbing.strap`` (and record their path so the cloth dents under them), the
    block-shaped G-hooks / ladder locks / side-release buckles become ``assets.hardware`` pieces with the webbing
    wrapped through them, and ``geom.concat`` carries those side meshes along. Nothing in those modules is edited."""
    import numpy as np
    from . import corrie as C
    from . import corrie_b1 as C1
    from . import geom as G
    from .assets import concat as aconcat
    from .assets import frame, placed, with_extras
    from .assets import hardware as HW
    from .assets import webbing as WB
    saved = []

    def patch(mod, attr, fn):
        if hasattr(mod, attr):
            saved.append((mod, attr, getattr(mod, attr)))
            setattr(mod, attr, fn)

    orig_ribbon, orig_concat, orig_sup = G.ribbon, G.concat, G.superellipsoid

    def EMPTY():
        return aconcat([])
    WIDTHS = (20.0, 22.0, 25.0, 30.0, 38.0, 50.0)

    def ribbon(path, width, thick, normals, tile=G.TILE_MM, step=8.0, caps=True):
        if float(width) not in WIDTHS or thick > 3.3 or len(np.atleast_2d(path)) < 2:
            return orig_ribbon(path, width, thick, normals, tile=tile, step=step, caps=caps)
        w = {22.0: 20.0, 30.0: 25.0}.get(float(width), float(width))
        m = WB.strap(np.asarray(path, float), np.asarray(normals, float), w, step=min(step or 3.0, 3.0))
        if not len(m.faces):
            return orig_ribbon(path, width, thick, normals, tile=tile, step=step, caps=caps)
        m.metadata["straps"] = [m.metadata.pop("strap")]
        return m

    def concat(meshes):
        meshes = [m for m in meshes if m is not None and len(m.faces)]
        out = orig_concat(meshes) if meshes else EMPTY()
        ex, st = {}, []
        for m in meshes:
            for k, lst in m.metadata.get("extras", {}).items():
                ex.setdefault(k, []).extend(lst)
            st.extend(m.metadata.get("straps", []))
        if ex:
            out.metadata["extras"] = ex
        if st:
            out.metadata["straps"] = st
        return out

    def hw(kind, p, n, t, legacy_lift=3.2, kit=True):
        sp = HW.SPECS[kind]
        R = frame(n, t)
        th = WB.thickness(sp.get("web", 25.0))
        c = np.asarray(p, float) + R[:, 2] * (-legacy_lift + th / 2 + 0.25 + sp["T"] / 2)
        m = placed(HW.build(kind), R, c)
        if kit:
            k = WB.threading(kind)
            with_extras(m, webbing=[placed(q, R, c) for q in k["webbing"]],
                        thread=[placed(q, R, c) for q in k["thread"]])
        return m

    def superellipsoid(center, radii, *a, **kw):
        if tuple(np.round(radii, 1)) == (26.0, 5.0, 16.0):            # model.py sternum buckle
            return hw("side_release_25", np.asarray(center, float), [0, -1.0, 0], [1.0, 0, 0], legacy_lift=4.0,
                      kit=LEGACY_WRAPS)
        return orig_sup(center, radii, *a, **kw)

    def block_b1(c, size, e=0.3, R=None):
        s = tuple(np.round(size, 1))
        if s == (46.0, 13.0, 40.0):                                   # belt buckle female -> whole 50 mm buckle
            return hw("side_release_50", np.asarray(c, float) + [-14.0, 0, 0], [0, -1.0, 0], [1.0, 0, 0],
                      legacy_lift=6.0, kit=False)
        if s in ((34.0, 9.0, 34.0), (10.0, 8.0, 22.0)):
            return EMPTY()
        return orig_block(c, size, e=e, R=R)

    orig_block = C._block
    patch(G, "ribbon", ribbon)
    patch(G, "concat", concat)
    patch(G, "superellipsoid", superellipsoid)
    for mod in (C, C1):
        patch(mod, "g_hook", lambda p, n, t: hw("g_hook_25", p, n, t))
        patch(mod, "side_release", lambda p, n, t: hw("side_release_25", p, n, t))
    patch(C, "ladder_lock", lambda p, n, t: hw("ladder_lock_25", p, n, t))
    patch(C1, "ladder_lock", lambda p, n, t: hw("ladder_lock_25_heavy" if belt_heavy else "ladder_lock_25", p, n, t,
                                                kit=LEGACY_WRAPS))
    patch(C1, "_block", block_b1)
    try:
        yield
    finally:
        for mod, attr, fn in reversed(saved):
            setattr(mod, attr, fn)
    _ = aconcat


def corrie_b2_scene(name="corrie_b2", params=None) -> ConceptScene:
    """CORRIE B.2 rebuilt through the modelling layer (the BL-018 proof). Geometry and design are the ones of
    ``viz3d.corrie_b2.corrie_b2_pack``; what changes is how cloth, seams, webbing, hardware and zips are modelled."""
    import numpy as np
    from . import corrie as C
    from . import geom as G
    from .assets import arclen
    from .assets import fabric as FB
    from .assets import seams as SM
    from .corrie_b2 import corrie_b2_pack
    from .params import load_params
    p = params or load_params(str(REPO / "designs" / "pack_5200" / "spec.yaml"))
    with upgraded_legacy():
        pack = corrie_b2_pack(p)
    sc = ConceptScene(name, colorway=p.get("colorway", "talus"), camo_repeat_mm=p.get("camo_repeat_mm", 380.0))
    L = FB.Look
    drape = {
        "corrie_body": dict(max_edge=3.2, uv_is_pattern=True),
        "corrie_kick": dict(max_edge=3.2, uv_is_pattern=True, look=L(fold=2.0)),
        "corrie_door": dict(max_edge=3.2, uv_is_pattern=True),
        "corrie_bottom": dict(max_edge=4.0, uv_is_pattern=True, look=L(fold=1.5)),
        "corrie_door_open": dict(max_edge=4.0, uv_is_pattern=False, look=L(slack=0.18, fold=2.2), lining="lining"),
        "corrie_roll": dict(max_edge=3.5, uv_is_pattern=False,
                            look=L(slack=0.75, slack_dir=(1, 0, 0), fold=2.6, fold_mm=(14.0, 34.0), hand=0.6)),
        "corrie_pouch": dict(max_edge=3.5, uv_is_pattern=False, look=L(slack=0.30, fold=1.8, hand=0.5)),
        "corrie_pouch_top": dict(max_edge=3.5, uv_is_pattern=False, look=L(slack=0.25, fold=1.6, hand=0.5)),
        "imp1_sleeve": dict(max_edge=4.0, uv_is_pattern=False, look=L(slack=0.35, fold=2.0)),
        "beltB_shell": dict(max_edge=3.5, uv_is_pattern=False, look=L(slack=0.10, fold=1.2, hand=0.35)),
        "beltB_pocket_L": dict(max_edge=3.5, uv_is_pattern=False, look=L(slack=0.25, fold=1.5)),
        "beltB_holster_back": dict(max_edge=4.0, uv_is_pattern=False, look=L(slack=0.15, fold=1.2)),
    }
    for nm in [q.name for q in pack.parts]:
        if nm.startswith("corrie_wing_") and not any(k in nm for k in ("bar", "straps", "hw")):
            drape[nm] = dict(max_edge=4.0, uv_is_pattern=False, look=L(slack=0.12, slack_dir=(0, 0, 1), fold=1.6,
                                                                       hand=0.5))
        if nm.startswith("shoulder_straps@"):
            drape[nm] = dict(max_edge=4.0, uv_is_pattern=False, look=L(slack=0.08, fold=1.0, hand=0.3))
    # corrie_door_lining: the inherited door builder's lining cuts through the folded door (dark blotches, BL-002);
    # the lining is rebuilt 1.2 mm inside the displaced door instead
    drop = ("corrie_seams", "corrie_door_zip", "corrie_zip_sliders", "corrie_zip_pulls", "corrie_door_lining")
    drop += tuple(q.name for q in pack.parts if q.name.startswith("imp6_hw@"))     # floats off the strap (legacy)
    # BL-020: the "floating shard" of defect 10 is the legacy phone slab (and its cord), drawn flat below the pocket
    drop += tuple(q.name for q in pack.parts if q.name.startswith(("imp6_phone@", "imp6_cord@")))
    import trimesh
    for q in pack.parts:                       # legacy harness: strap-tip slivers that float off the straps
        if q.name.startswith("shoulder_straps@"):
            tm = trimesh.Trimesh(q.mesh.vertices, q.mesh.faces, process=False)
            lab = trimesh.graph.connected_component_labels(tm.face_adjacency, node_count=len(tm.faces))
            keep = np.ones(len(tm.faces), bool)
            for k in np.unique(lab):
                fm = lab == k
                if np.ptp(tm.vertices[np.unique(tm.faces[fm])], axis=0).max() < 80.0:
                    keep[fm] = False
            if not keep.all():
                from .assets import mesh as amesh
                q.mesh = amesh(q.mesh.vertices, np.asarray(q.mesh.faces)[keep], q.mesh.metadata.get("uv"))
    sc.add_pack(pack, drape=drape, drop=drop)
    for q in sc.parts:                                              # display form: own materials
        if q.name.startswith("mannequin_stand@"):
            q.material = "stand"
        elif q.name.startswith("mannequin@"):
            q.material = "form"
    # seams and door zip from the sim's own piece boundaries
    S = C.Skin(C.sim_skin())
    vis = dict(group="bag", modes=C.BAGM)
    zip_key = ("B-02door", "B-02u")
    sc.add_seams_from_pieces(S.V, S.F, S.piece, S.vn, name="corrie_seams", material="body", skip=[zip_key],
                             project=lambda P: S.project(P, 0.0), smooth=24.0, **vis)
    ch = C.seam_chains(S.F, S.piece)
    ZP = C.smooth_line(C.join_chains([S.V[cc] for cc in ch[frozenset(zip_key)] if len(cc) > 5]), 3.0, 18.0)
    if ZP[0, 0] > ZP[-1, 0]:
        ZP = ZP[::-1]
    zq, zn = S.project(ZP, 0.3)
    Lz = arclen(zq)[-1]
    sc.add_zip("corrie_door_zip", zq, zn, size=10, sliders=(70.0 / Lz, 1 - 70.0 / Lz), variant="rolled", **vis)
    sc.add_zip("corrie_door_zip_open", zq, zn + 0, size=10, sliders=(0.012, 0.988), closed=(0.0, 0.0), half=1,
               variant="full", **vis)
    # kick-plate edge: the camo plate is top-stitched onto the body along its cut line
    kick = next(q for q in sc.parts if q.name == "corrie_kick")
    body = next(q for q in sc.parts if q.name == "corrie_body")
    from scipy.spatial import cKDTree
    tb = cKDTree(np.asarray(body.mesh.vertices))
    Vk, Fk = np.asarray(kick.mesh.vertices), np.asarray(kick.mesh.faces)
    for i, cc in enumerate(C.boundary_chains(Fk)):
        if len(cc) < 6:
            continue
        P0 = Vk[cc]
        d, _ = tb.query(P0)
        P0 = P0[d < 0.5]
        if len(P0) < 6 or arclen(P0)[-1] < 40:
            continue
        P = SM.smooth_path(P0, 3.0, 6.0)
        q, n = S.project(P, 0.0)
        sc.add_seam(f"corrie_kick_edge{i}", q, n, side=-1.0, material="camo", **vis)
    sc.report["source"] = {"sim": str(C.SIM_DIR.relative_to(REPO)), "case": C.CASE, "spec": "B.2"}
    _ = G
    return sc


def hardware_sheet_scene(name="hardware_sheet") -> ConceptScene:
    """Every hardware asset threaded on its webbing over a 330D swatch, plus a seam, a zip, a bartack and a box-X:
    the look-development board of the modelling layer."""
    import numpy as np
    from .assets import hardware as HW
    from .assets import mesh
    from .assets import seams as SM
    sc = ConceptScene(name)
    kinds = ["side_release_25", "side_release_38", "side_release_50", "ladder_lock_25", "ladder_lock_25_heavy",
             "tri_glide_25", "cam_buckle_38", "g_hook_25", "bag_hook_38", "d_ring_25", "cord_lock", "zip_slider_10"]
    cols, dx, dz = 4, 150.0, 120.0
    W, H = cols * dx + 60, 3 * dz + 150
    n = 60
    xs, zs = np.meshgrid(np.linspace(-W / 2, W / 2, n), np.linspace(0, H, n))
    V = np.column_stack([xs.ravel(), np.zeros(n * n), zs.ravel()])
    F = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            F += [[a, a + n + 1, a + 1], [a, a + n, a + n + 1]]
    sw = mesh(V, np.array(F), np.column_stack([xs.ravel(), zs.ravel()]) / 500.0)
    nrm = np.array([0.0, 1.0, 0.0])
    sc.add_fabric("swatch", sw, "body", max_edge=3.0, thickness=0.6, group="bag")
    for k, kind in enumerate(kinds):
        r, c = divmod(k, cols)
        ctr = np.array([(c - (cols - 1) / 2) * dx, 0.0, H - 70 - r * dz])
        sp = HW.SPECS[kind]
        w = sp.get("web", 25.0)
        if kind.startswith(("zip", "cord")):
            sc.add_hardware(kind, kind, ctr + nrm * 1.0, nrm, [1.0, 0, 0], threading=False, on_strap=False)
            continue
        P = ctr + np.outer(np.linspace(-62, 62, 30), [1.0, 0, 0]) + nrm * 1.0
        if kind.startswith(("g_hook", "bag_hook")):
            P = P[:16]
        if kind.startswith("d_ring") or kind.startswith("tri_glide") or kind.startswith("cam"):
            sc.add_strap(f"{kind}_web", P, nrm, w)
            sc.add_hardware(kind, kind, ctr + nrm * 1.0, nrm, [1.0, 0, 0], threading=False)
            continue
        Pm = P[P[:, 0] < ctr[0] - sp["L"] / 2 + 14]
        sc.add_strap(f"{kind}_web", Pm, nrm, w)
        sc.add_hardware(kind, kind, ctr + nrm * 1.0, nrm, [1.0, 0, 0])
    z0 = H - 70 - 3 * dz + 10
    Ps = np.column_stack([np.linspace(-W / 2 + 20, -20, 80), np.zeros(80), np.full(80, z0)])
    sc.add_seam("demo_seam", Ps, np.tile(nrm, (80, 1)))
    Pz = np.column_stack([np.linspace(20, W / 2 - 20, 80), np.zeros(80), np.full(80, z0)])
    sc.add_zip("demo_zip", Pz, nrm, size=10, sliders=(0.2,), closed=(0.2, 1.0), pull_down=(-0.3, 0, -1.0))
    sc.add_part("demo_bartack", SM.bartack([-W / 2 + 40, 0.9, z0 + 40], nrm, [1.0, 0, 0]), "thread")
    return sc


def fabric_swatch_scene(name="fabric_swatches") -> ConceptScene:
    """Two 330D panels from the same flat pattern, one held 3 % taut (left), one let in 6 % slack (right), each with
    a seam and a 25 mm strap: what the fabric pass does with the strain field."""
    import numpy as np
    from .assets import mesh
    sc = ConceptScene(name)
    n, S0 = 70, 360.0
    nrm = np.array([0.0, 1.0, 0.0])
    for k, (tag, comp) in enumerate((("taut", 1.03), ("slack", 0.94))):
        u, v = np.meshgrid(np.linspace(0, S0, n), np.linspace(0, S0, n))
        x0 = -S0 - 25 if k == 0 else 25.0
        bow = np.zeros(n * n) if k == 0 else 6.0 * np.sin(np.pi * u.ravel() / S0)   # the slack panel sags a little
        V = np.column_stack([x0 + u.ravel() * comp + (1 - comp) * S0 / 2, bow, 40 + v.ravel()])
        F = []
        for i in range(n - 1):
            for j in range(n - 1):
                a = i * n + j
                F += [[a, a + n + 1, a + 1], [a, a + n, a + n + 1]]
        sc.add_fabric(f"panel_{tag}", mesh(V, np.array(F), np.column_stack([u.ravel(), v.ravel()]) / 500.0), "body",
                      max_edge=2.6, thickness=0.6)
        xs = x0 + (1 - comp) * S0 / 2
        Ps = np.column_stack([np.linspace(xs + 10, xs + S0 * comp - 10, 90), np.zeros(90), np.full(90, 300.0)])
        sc.add_seam(f"seam_{tag}", Ps, np.tile(nrm, (90, 1)))
        Pw = np.column_stack([np.linspace(xs + 10, xs + S0 * comp - 10, 60), np.full(60, 1.0), np.full(60, 150.0)])
        if k == 1:
            Pw[:, 1] += 6.0 * np.sin(np.pi * (Pw[:, 0] - xs) / (S0 * comp))
        sc.add_strap(f"strap_{tag}", Pw, nrm, 25.0)
    return sc


CONCEPTS = {"corrie_b2": corrie_b2_scene, "hardware_sheet": hardware_sheet_scene,
            "fabric_swatches": fabric_swatch_scene}


# ============================================================================================ entry point
def find_bpy_python(bpy_python=None) -> str | None:
    for c in (bpy_python, os.environ.get("HUNTKIT_BPY")):
        if c and Path(c).exists():
            return str(c)
    return None


def _has_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def render(concept_scene, shots, out_dir, prefix=None, quality="final", start=1, captions=True, wearer=None,
           wearer_kwargs=None, pack_on_torso=None, bpy_python=None, work_dir=None, title=None, threads=None,
           camo=None, torso=19.0, cloth_pass=False) -> list[dict]:
    """Render ``shots`` of a concept to ``out_dir/<prefix>_<n>.png`` (PNG <= 1.5 MB each).

    concept_scene  a ``ConceptScene``, or the path of a ``*.scene.json`` an earlier ``build`` wrote.
    shots          {name: {"view": {...}, "state": {...}, "caption": str, "sub": str}} (``studio.shots(...)`` gives
                   the presets hero / side / front34 / macro), or a list of preset names.
    quality        "quick" (800 x 600, 16 spp, under 60 s a frame), "preview", "final" (1600 x 1200, 72 spp).
    wearer         optional figure that replaces the display form (BL-019). Either
                   * "package.module:function" (works across the bpy subprocess): called inside Blender as
                     ``function(**wearer_kwargs)``; it must add its objects to the current scene and return them
                     (a list of ``bpy.types.Object``) or a dict {"objects": [...], "pack_on_torso": 4x4}; or
                   * a callable, or a list of Blender objects already in ``bpy.data`` (in-process only).
    pack_on_torso  4x4 rigid transform (row-major nested lists, Blender world metres, Z up) applied to every pack
                   object so the pack sits on the wearer's torso. Identity = the pack stays in its own frame
                   (FCS x, -y, z in metres), which is where the display form stands.
    cloth_pass     BL-020 render-only cloth pass: True, a ``cloth_pass.ClothParams`` or a dict of its fields. Every
                   part marked with ``cloth_pass.register(scene, part, ...)`` is solved in Blender's cloth solver
                   (real folds, contact with its colliders) before the fabric pass. Presentation geometry only;
                   see ``huntkit/viz3d/cloth_pass.py`` and README "Cloth pass".
    Returns one dict per frame: view, file, seconds, mb."""
    if isinstance(shots, (list, tuple)):
        shots = globals()["shots"](*shots)
    out_dir = Path(out_dir)
    if cloth_pass and isinstance(concept_scene, ConceptScene):
        from . import cloth_pass as CP
        CP.apply(concept_scene, None if cloth_pass is True else cloth_pass)
    if isinstance(concept_scene, ConceptScene):
        scene_json = concept_scene.build(work_dir)
    else:
        scene_json = Path(concept_scene)
    prefix = prefix or time.strftime("%Y%m%d") + "_" + scene_json.name.split(".")[0]
    in_process = _has_bpy()
    if not in_process and (callable(wearer) or isinstance(wearer, (list, tuple))):
        raise ValueError("a callable / object-list wearer needs bpy in this interpreter; pass 'module:function'")
    if in_process:
        return render_scene(scene_json, shots, out_dir, prefix, quality, start, captions, wearer, wearer_kwargs,
                            pack_on_torso, threads, title, camo, torso)
    py = find_bpy_python(bpy_python)
    if py is None:
        raise RuntimeError("bpy is not importable here: set HUNTKIT_BPY (or bpy_python=) to the Python of the "
                           "Blender venv, see huntkit/viz3d/README.md")
    job = scene_json.with_suffix(".job.json")
    job.write_text(json.dumps({"scene": str(scene_json), "shots": shots, "out": str(out_dir), "prefix": prefix,
                               "quality": quality, "start": start, "captions": captions, "wearer": wearer,
                               "wearer_kwargs": wearer_kwargs, "pack_on_torso": pack_on_torso, "threads": threads,
                               "title": title, "camo": str(camo) if camo else None, "torso": torso}))
    env = dict(os.environ, HUNTKIT_PY=os.environ.get("HUNTKIT_PY", sys.executable))
    subprocess.run([py, "-m", "huntkit.viz3d.studio", "--job", str(job)], cwd=REPO, check=True, env=env)
    return json.loads(job.with_suffix(".result.json").read_text())


# ============================================================================================ stage 2: Blender
def _CR():
    from . import cycles_render as CR
    return CR


def _col(spec, cw):
    CR = _CR()
    if spec.get("hex"):
        return CR.hexlin(spec["hex"])
    key = spec.get("color", "body")
    return CR.hexlin(cw.get(key, "#6E745B"))


def sh_fabric(mat, base, spec, image=None, uv_mm=500.0):
    """Woven cloth: yarn-level weave bump and colour (plain / 2x2 basket / twill / rib), optional ripstop grid,
    sheen, roughness and dye variation. Fold-scale wrinkles are GEOMETRY (assets.fabric), not bump."""
    CR = _CR()
    nb = CR.NB(mat)
    w = float(spec.get("weave_mm", 0.45))
    if image is not None:
        tc = nb.n("ShaderNodeTexCoord")
        tex = nb.n("ShaderNodeTexImage", interpolation="Cubic")
        tex.image = image
        nb.link(tc.outputs["UV"], tex.inputs["Vector"])
        base_sock = tex.outputs["Color"]
    else:
        base_sock = base
    vm, _ = CR._uv_scaled(nb, uv_mm / w * math.pi)
    sep = nb.n("ShaderNodeSeparateXYZ")
    nb.link(vm.outputs["Vector"], sep.inputs[0])
    sx, sy = nb.math("SINE", sep.outputs["X"]), nb.math("SINE", sep.outputs["Y"])
    if spec.get("twill"):
        weave = nb.math("SINE", nb.math("ADD", sep.outputs["X"], nb.math("MULTIPLY", sep.outputs["Y"], 2.0)))
    elif spec.get("rib"):
        weave = nb.math("ABSOLUTE", sy)
    else:
        weave = nb.math("MULTIPLY", sx, sy)                     # plain weave / basket: over-under checker
    h = weave
    grid = None
    if spec.get("grid_mm"):
        grid = CR._grid_height(nb, uv_mm, float(spec["grid_mm"]), line=0.08)
        h = nb.math("ADD", nb.math("MULTIPLY", weave, 0.5), nb.math("MULTIPLY", grid, 1.6))
    nrm = CR._bump(nb, h, 0.00018 * max(w / 0.45, 0.6), 1.0)
    fz = CR._obj_noise(nb, 55.0, detail=5.0, stretch=(1.0, 1.0, 0.5), rough=0.65)      # fine cloth crinkle
    fz2 = nb.math("ABSOLUTE", nb.math("SUBTRACT", fz.outputs["Fac"], 0.5))
    nrm = CR._bump(nb, fz2, 0.0012, 0.55, normal=nrm.outputs[0])
    col = CR._mottle(nb, base_sock, 0.045, scale=7.0)
    # yarn-level shading: valleys between yarns darker (visible in macro, averages out at distance)
    _, fac, a, b, colw = CR._mix_rgba(nb, "MULTIPLY")
    mr = nb.n("ShaderNodeMapRange")
    nb.link(weave, mr.inputs["Value"])
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -1.0, 1.0
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.80, 1.06
    comb = nb.n("ShaderNodeCombineXYZ")
    for s in ("X", "Y", "Z"):
        nb.link(mr.outputs["Result"], comb.inputs[s])
    fac.default_value = 1.0
    nb.link(col, a)
    nb.link(comb.outputs[0], b)
    col = colw
    if grid is not None and spec.get("grid_white"):
        _, f2, a2, b2, c2 = CR._mix_rgba(nb, "MIX")
        nb.link(nb.math("MULTIPLY", grid, 0.8), f2)
        nb.link(col, a2)
        b2.default_value = (0.75, 0.75, 0.72, 1)
        col = c2
    CR._principled(nb, mat, col, CR._rough_var(nb, float(spec.get("rough", 0.8)), 0.05), nrm.outputs[0],
                   Sheen_Weight=float(spec.get("sheen", 0.45)), Sheen_Roughness=0.4, Specular_IOR_Level=0.3,
                   Coat_Weight=float(spec.get("coat", 0.0)), Coat_Roughness=0.4)


def sh_webbing(mat, base, spec, uv_mm=500.0):
    """Nylon webbing: weft picks at ``pick_mm`` as transverse ribs broken into a herringbone by the warp ends, proud
    selvedges, satin sheen. UV u across (mm), v along (mm)."""
    CR = _CR()
    nb = CR.NB(mat)
    pick = float(spec.get("pick_mm", 1.05))
    end = float(spec.get("end_mm", 0.85))
    tc = nb.n("ShaderNodeTexCoord")
    sep = nb.n("ShaderNodeSeparateXYZ")
    nb.link(tc.outputs["UV"], sep.inputs[0])
    u = nb.math("MULTIPLY", sep.outputs["X"], uv_mm)
    v = nb.math("MULTIPLY", sep.outputs["Y"], uv_mm)
    # herringbone: the rib phase shifts with a triangle wave across the width (period 6 mm)
    tri = nb.math("ABSOLUTE", nb.math("SUBTRACT", nb.math("FRACT", nb.math("DIVIDE", u, 6.0)), 0.5))
    ph = nb.math("ADD", nb.math("DIVIDE", v, pick), nb.math("MULTIPLY", tri, 0.9))
    rib = nb.math("SINE", nb.math("MULTIPLY", ph, 2 * math.pi))
    ends = nb.math("SINE", nb.math("MULTIPLY", nb.math("DIVIDE", u, end), 2 * math.pi))
    weave = nb.math("MULTIPLY", nb.math("ADD", nb.math("MULTIPLY", rib, 0.5), 0.5),
                    nb.math("ADD", nb.math("MULTIPLY", ends, 0.35), 0.65))
    nrm = CR._bump(nb, weave, 0.00045, 1.0)
    col = CR._mottle(nb, base, 0.05, scale=11.0)
    _, fac, a, b, colw = CR._mix_rgba(nb, "MULTIPLY")
    mr = nb.n("ShaderNodeMapRange")
    nb.link(weave, mr.inputs["Value"])
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.55, 1.10
    comb = nb.n("ShaderNodeCombineXYZ")
    for s in ("X", "Y", "Z"):
        nb.link(mr.outputs["Result"], comb.inputs[s])
    fac.default_value = 1.0
    nb.link(col, a)
    nb.link(comb.outputs[0], b)
    CR._principled(nb, mat, colw, CR._rough_var(nb, 0.6, 0.05), nrm.outputs[0], Sheen_Weight=0.25,
                   Sheen_Roughness=0.4, Specular_IOR_Level=0.4)


def sh_simple(mat, base, rough, metallic=0.0, coat=0.0, spec=0.5, bump=0.0, bump_scale=600.0, sheen=0.0,
              coat_rough=0.1, sss=0.0):
    CR = _CR()
    nb = CR.NB(mat)
    nrm = None
    if bump:
        nz = CR._obj_noise(nb, bump_scale, detail=2.0)
        nrm = CR._bump(nb, nz.outputs["Fac"], 0.00012, bump).outputs[0]
    kw = dict(Metallic=metallic, Coat_Weight=coat, Coat_Roughness=coat_rough, Specular_IOR_Level=spec,
              Sheen_Weight=sheen)
    b = CR._principled(nb, mat, CR._mottle(nb, base, 0.03, scale=20.0), CR._rough_var(nb, rough, 0.05, scale=30.0),
                       nrm, **kw)
    if sss:
        try:
            b.inputs["Subsurface Weight"].default_value = sss
            b.inputs["Subsurface Radius"].default_value = (0.0006, 0.0006, 0.0006)
        except KeyError:
            pass


def sh_printed(mat):
    """Printed PAHT-CF: matte, fibre-flecked, with layer lines (ASSUMPTION 0.2 mm layers, stacked along the part's
    z; the slicer profile settles it)."""
    CR = _CR()
    nb = CR.NB(mat)
    tc = nb.n("ShaderNodeTexCoord")
    sep = nb.n("ShaderNodeSeparateXYZ")
    nb.link(tc.outputs["Object"], sep.inputs[0])
    lay = nb.math("SINE", nb.math("MULTIPLY", sep.outputs["Z"], 2 * math.pi / 0.0002))
    lay = nb.math("ABSOLUTE", lay)
    nrm = CR._bump(nb, lay, 0.00006, 0.9)
    fl = CR._obj_noise(nb, 2600.0, detail=1.0, stretch=(1.0, 1.0, 6.0))
    nrm = CR._bump(nb, fl.outputs["Fac"], 0.00005, 0.6, normal=nrm.outputs[0])
    mr = nb.n("ShaderNodeMapRange")
    nb.link(fl.outputs["Fac"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.35, 0.75
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.72, 0.52
    CR._principled(nb, mat, CR._mottle(nb, CR.hexlin("#222325"), 0.08, scale=60.0), mr.outputs["Result"],
                   nrm.outputs[0], Specular_IOR_Level=0.35, Sheen_Weight=0.1)


def sh_spacer(mat, uv_mm=500.0, cell_mm=3.2):
    """3D spacer mesh: hex-ish open cells with real see-through holes (alpha) onto whatever is behind."""
    import bpy
    CR = _CR()
    nb = CR.NB(mat)
    vm, _ = CR._uv_scaled(nb, uv_mm / cell_mm)
    vor = nb.n("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    nb.link(vm.outputs["Vector"], vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 1.0
    vor.inputs["Randomness"].default_value = 0.12
    hole = nb.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    nb.link(vor.outputs["Distance"], hole.inputs["Value"])
    hole.inputs["From Min"].default_value, hole.inputs["From Max"].default_value = 0.16, 0.24
    land = nb.math("SUBTRACT", 1.0, hole.outputs[0])
    nrm = CR._bump(nb, land, 0.0010, 1.0)
    bsdf = nb.n("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = CR.hexlin("#232422")
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Sheen Weight"].default_value = 0.7
    nb.link(nrm.outputs[0], bsdf.inputs["Normal"])
    dark = nb.n("ShaderNodeBsdfPrincipled")
    dark.inputs["Base Color"].default_value = CR.hexlin("#070707")
    dark.inputs["Roughness"].default_value = 0.95
    mix = nb.n("ShaderNodeMixShader")
    nb.link(hole.outputs[0], mix.inputs[0])
    nb.link(bsdf.outputs[0], mix.inputs[1])
    nb.link(dark.outputs[0], mix.inputs[2])
    out = nb.n("ShaderNodeOutputMaterial")
    nb.link(mix.outputs[0], out.inputs["Surface"])
    _ = bpy


def sh_form(mat, uv_mm=500.0):
    """Display form: a fabric-covered tailor's form in pale grey jersey."""
    sh_fabric(mat, _CR().hexlin("#b7b3aa"), {"weave_mm": 0.8, "rough": 0.9, "sheen": 0.6}, uv_mm=uv_mm)


def build_materials(scene_spec, camo_png=None):
    import bpy
    CR = _CR()
    cw = scene_spec.get("colorway", {})
    specs = scene_spec.get("materials", MATERIALS)
    camo_img = bpy.data.images.load(str(camo_png)) if camo_png else None
    done = {}
    for mat in list(bpy.data.materials):
        if not mat.node_tree:
            continue
        key = mat.name.split(".")[0]
        spec = specs.get(key, {"shader": "plastic", "hex": "#777777", "rough": 0.6})
        sh = spec["shader"]
        _, img = CR._orig_params(mat)
        if sh == "fabric":
            if spec.get("color") == "camo":
                sh_fabric(mat, None, spec, image=camo_img or img, uv_mm=scene_spec.get("camo_repeat_mm", 380.0))
            else:
                sh_fabric(mat, _col(spec, cw), spec)
        elif sh == "webbing":
            sh_webbing(mat, _col(spec, cw), spec)
        elif sh == "thread":
            c = _col(spec, cw)
            sh_simple(mat, tuple(min(1.0, v * 1.0) for v in c[:3]) + (1.0,), 0.45, spec=0.5, sheen=0.5)
        elif sh == "cord":
            sh_fabric(mat, _col(spec, cw), {"weave_mm": 0.7, "twill": 1, "rough": 0.7, "sheen": 0.5}, uv_mm=40.0)
        elif sh == "plastic":
            sh_simple(mat, _col(spec, cw), float(spec.get("rough", 0.42)), spec=0.5, bump=0.25, bump_scale=900.0)
        elif sh == "rubber":
            sh_simple(mat, _col(spec, cw), 0.7, spec=0.3, bump=0.5, bump_scale=500.0)
        elif sh == "metal":
            if spec.get("bare"):
                sh_simple(mat, _col(spec, cw), float(spec.get("rough", 0.38)), metallic=1.0)
            else:                       # anodised / painted: dark, satin, slight clear layer
                sh_simple(mat, _col(spec, cw), float(spec.get("rough", 0.42)), metallic=0.85, coat=0.15,
                          coat_rough=0.3, bump=0.12, bump_scale=1500.0)
        elif sh == "printed":
            sh_printed(mat)
        elif sh == "spacer":
            sh_spacer(mat)
        elif sh == "foam":
            CR.foam(mat)
        elif sh == "hypalon":
            sh_simple(mat, _col(spec, cw), 0.62, spec=0.35, coat=0.12, coat_rough=0.45, bump=0.6, bump_scale=350.0)
        elif sh == "carbon":
            base, _ = CR._orig_params(mat)
            CR.solid(mat, CR.hexlin("#17181a"), float(spec.get("rough", 0.32)), image=None,
                     coat=float(spec.get("coat", 0.9)), spec=0.5, noise_bump=0.3)
            _carbon_twill(mat)
        elif sh == "form":
            sh_form(mat)
        else:
            sh_simple(mat, _col(spec, cw), 0.6)
        done[key] = sh
    return done


def _carbon_twill(mat):
    """2x2 twill carbon: a procedural tow pattern on the base colour (2 mm tows), under the existing coat."""
    CR = _CR()
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (500.0, 500.0, 500.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    wav = nt.nodes.new("ShaderNodeTexWave")
    wav.wave_type = "BANDS"
    wav.bands_direction = "DIAGONAL"
    wav.inputs["Scale"].default_value = 1.0
    wav.inputs["Distortion"].default_value = 0.0
    nt.links.new(mp.outputs["Vector"], wav.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = CR.hexlin("#0d0e0f")
    ramp.color_ramp.elements[1].color = CR.hexlin("#2a2c2f")
    nt.links.new(wav.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])


# ------------------------------------------------------------------------------------------------- the studio
def setup_render(samples, res, threads):
    CR = _CR()
    sc = CR.setup_scene(samples, res, threads or os.cpu_count() or 4)
    sc.render.film_transparent = False
    sc.cycles.adaptive_threshold = 0.025
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 6, 3, 3
    sc.cycles.transparent_max_bounces = 6
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.10
    return sc


def make_backdrop():
    """Seamless paper sweep: floor, a 0.9 m radius cove, a wall. Rotated per shot so the wall is behind the pack."""
    import bmesh
    import bpy
    R, half, depth, wall = 0.9, 7.0, 3.2, 5.5
    prof = [(-4.5, 0.0), (depth - R, 0.0)]
    for a in [math.radians(x) for x in range(-90 + 6, 1, 6)]:
        prof.append((depth - R + R * math.cos(a), R + R * math.sin(a)))
    prof.append((depth, wall))
    me = bpy.data.meshes.new("backdrop")
    bm = bmesh.new()
    rows = []
    for x in (-half, half):
        rows.append([bm.verts.new((x, y, z)) for (y, z) in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((rows[0][i], rows[1][i], rows[1][i + 1], rows[0][i + 1]))
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("backdrop", me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new("paper")
    m.use_nodes = True
    sh_simple(m, _CR().hexlin("#e4e2dc"), 0.92, spec=0.15)
    me.materials.append(m)
    return ob


def make_lights():
    CR = _CR()
    key = CR._area("key", 210.0, 1.5, (1.0, 0.96, 0.90), 1.2)
    fill = CR._area("fill", 14.0, 2.6, (0.90, 0.94, 1.0), 1.8)
    rim = CR._area("rim", 85.0, 0.7, (1.0, 1.0, 1.0), 2.2)
    top = CR._area("top", 22.0, 2.4, (1.0, 0.98, 0.95), 0.9)
    return key, fill, rim, top


def place_lights(rig, cam_az, tgt, radius):
    CR = _CR()
    key, fill, rim, top = rig
    for ob, (daz, el, r_mul) in zip((key, fill, rim), ((-52, 34, 1.0), (58, 12, 1.25), (150, 42, 1.05))):
        ob.data.energy = ob["e0"] * (radius * r_mul / CR.RIG_R0) ** 2
        d = CR.view_dir(cam_az + daz, el)
        ob.location = tuple(t + radius * r_mul * x for t, x in zip(tgt, d))
        CR._aim(ob, tgt)
    top.data.energy = top["e0"] * (radius / CR.RIG_R0) ** 2
    top.location = (tgt[0], tgt[1], tgt[2] + radius * 0.95)
    CR._aim(top, tgt)


def _fix_shading(ob, hard):
    """Hardware: drop the imported averaged normals and split at 38 deg so slots and edges stay crisp."""
    me = ob.data
    if hard:
        if "custom_normal" in me.attributes:
            me.attributes.remove(me.attributes["custom_normal"])
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        try:
            me.set_sharp_from_angle(angle=math.radians(38))
        except Exception:  # noqa: BLE001
            pass


def marker_wearer(height_m=1.829):
    """Stand-in for the wearer hook (tests, framing checks): one post of the wearer's height standing where the
    wearer stands (in front of the back panel). Not a figure; huntkit.viz3d.wearer builds the person."""
    import bpy
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=height_m, location=(0.0, 0.12, height_m / 2 - 0.9))
    return [bpy.context.active_object]


def _resolve_wearer(wearer, wearer_kwargs):
    """-> (objects, pack_on_torso or None)."""
    if wearer is None:
        return None, None
    if isinstance(wearer, str):
        mod, fn = wearer.split(":")
        wearer = getattr(importlib.import_module(mod), fn)
    res = wearer(**(wearer_kwargs or {})) if callable(wearer) else wearer
    if isinstance(res, dict):
        return list(res.get("objects", [])), res.get("pack_on_torso")
    if hasattr(res, "figure") or hasattr(res, "objects"):          # wearer.Wearer: take the person, not its own pack
        objs = list(getattr(res, "figure", None) or []) + list(getattr(res, "props", None) or [])
        if not objs:
            objs = list(res.objects)
        else:
            for o in getattr(res, "pack", None) or []:
                o.hide_render = True
        return objs, getattr(res, "pack_on_torso", None)
    return list(res), None


def render_scene(scene_json, shots, out_dir, prefix, quality="final", start=1, captions=True, wearer=None,
                 wearer_kwargs=None, pack_on_torso=None, threads=None, title=None, camo=None,
                 torso=19.0) -> list[dict]:
    """Stage 2 (needs bpy)."""
    import bpy
    from mathutils import Matrix, Vector
    CR = _CR()
    t0 = time.time()
    scene_json = Path(scene_json)
    spec = json.loads(scene_json.read_text())
    parts = spec["parts"]
    q = QUALITY[quality] if isinstance(quality, str) else quality
    res = tuple(q["res"])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(scene_json.with_name(spec["glb"])))
    sc = setup_render(q["samples"], res, threads)
    work = scene_json.parent
    camo_png = Path(camo) if camo else CR.owner_camo_png(REPO / "outputs" / "cycles_work")
    shaders = build_materials(spec, camo_png)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for ob in meshes:
        mk = parts.get(ob.name, {}).get("material")
        _fix_shading(ob, shaders.get(mk) in HARD_SHADERS)
    # wearer hook (BL-019): replaces the display form; the pack is moved onto the torso by one rigid transform
    w_objs, w_xf = _resolve_wearer(wearer, wearer_kwargs)
    xf = pack_on_torso if pack_on_torso is not None else w_xf
    if xf is not None:
        root = bpy.data.objects.new("pack_root", None)
        sc.collection.objects.link(root)
        for ob in meshes:
            if ob.parent is None:
                ob.parent = root
        root.matrix_world = Matrix([list(r) for r in xf])
        bpy.context.view_layer.update()
    backdrop = make_backdrop()
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    rig = make_lights()
    print(f"setup {time.time() - t0:.1f} s, {len(meshes)} meshes", flush=True)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for k, (vname, shot) in enumerate(shots.items()):
        state = {"torso": torso, **shot.get("state", {})}
        if w_objs is not None:
            state["mannequin"] = False
        vis = []
        for ob in meshes:
            on = CR.visible_for(parts.get(ob.name), ob.name, state)
            ob.hide_render = not on
            if on:
                vis.append(ob)
        allv = vis + [o for o in (w_objs or []) if getattr(o, "type", "") == "MESH"]
        lo, hi = CR.visible_bounds(allv)
        v = shot["view"]
        fov = v.get("fov", 24.0)
        if "box" in v:
            bmin, bmax = CR.fcs_box_to_blender(v["box"])
        elif "at" in v:
            c = (v["at"][0] / 1000.0, -v["at"][1] / 1000.0, v["at"][2] / 1000.0)
            h = v.get("span", 150.0) / 2000.0
            bmin, bmax = tuple(x - h for x in c), tuple(x + h for x in c)
        elif v.get("frame") == "pack":
            pk = [o for o in vis if parts.get(o.name, {}).get("group") != "mannequin"] or vis
            bmin, bmax = CR.visible_bounds(pk + [o for o in (w_objs or []) if getattr(o, "type", "") == "MESH"])
        else:
            bmin, bmax = lo, hi
        if xf is not None and ("box" in v or "at" in v):
            M = Matrix([list(r) for r in xf])
            cs = [M @ Vector((x, y, z)) for x in (bmin[0], bmax[0]) for y in (bmin[1], bmax[1])
                  for z in (bmin[2], bmax[2])]
            bmin = tuple(min(c[i] for c in cs) for i in range(3))
            bmax = tuple(max(c[i] for c in cs) for i in range(3))
        cd.angle_y = math.radians(fov)
        pos, tgt = CR.fit_camera(bmin, bmax, v["az"], v["el"], fov, res[0] / res[1], v.get("zoom", 1.0),
                                 fill=v.get("fill", 0.84))
        cam.location = pos
        CR._aim(cam, tgt)
        dist = math.dist(pos, tgt)
        cd.dof.use_dof = True
        cd.dof.focus_distance = dist
        cd.dof.aperture_fstop = v.get("fstop", 11.0)
        cd.clip_start, cd.clip_end = 0.01, 60.0
        backdrop.location = (tgt[0], tgt[1], lo[2] - 0.0005)
        backdrop.rotation_euler = (0.0, 0.0, math.radians(v["az"]) + (math.pi if True else 0.0))
        # wall behind the subject as seen from the camera: the sweep's +y points away from the camera
        d = CR.view_dir(v["az"], 0.0)
        backdrop.rotation_euler = (0.0, 0.0, math.atan2(-d[1], -d[0]) - math.pi / 2)
        place_lights(rig, v["az"], tgt, max(1.6, 0.8 * dist) if "at" not in v and "box" not in v else max(1.2, dist))
        sc.view_settings.exposure = v.get("exposure", 0.0)
        raw = work / f"_raw_{prefix}_{vname}.png"
        sc.render.filepath = str(raw)
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t1
        out = out_dir / f"{prefix}_{start + k}.png"
        finish(raw, out, (title + ": " if title else "") + shot.get("caption", vname) if captions else "",
               shot.get("sub", "") if captions else "")
        CR.shrink_png(out)
        results.append({"view": vname, "file": str(out), "seconds": round(dt, 1), "quality": quality,
                        "res": list(res), "samples": q["samples"], "mb": round(out.stat().st_size / 1e6, 2)})
        print(f"[{vname}] {out} {dt:.0f} s", flush=True)
    (work / f"{prefix}_timing.json").write_text(json.dumps(results, indent=1))
    return results


def finish(raw_png, out_png, caption="", sub=""):
    """Write the frame with its caption in a paper-coloured band BELOW the picture (never over the subject)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(raw_png).convert("RGB")
    w, h = im.size
    if caption:
        band = int(h * (0.105 if sub else 0.07))
        out = Image.new("RGB", (w, h + band), (238, 236, 230))
        out.paste(im, (0, 0))
        d = ImageDraw.Draw(out)
        try:
            f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", int(h * 0.030))
            f2 = ImageFont.truetype("DejaVuSans.ttf", int(h * 0.021))
        except OSError:
            f1 = f2 = ImageFont.load_default()
        x0 = int(w * 0.02)
        d.text((x0, h + int(h * 0.014)), caption, fill=(40, 40, 36), font=f1)
        if sub:
            d.text((x0, h + int(h * 0.058)), sub, fill=(96, 95, 88), font=f2)
        im = out
    im.save(out_png, optimize=True)
    return out_png


def sheet(pairs, out_png, titles=("BEFORE", "AFTER"), subs=("", ""), width=2400):
    """Before / after sheet: ``pairs`` = [(before png, after png), ...], one row each."""
    from PIL import Image, ImageDraw, ImageFont
    CR = _CR()
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        fs = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        f = fs = ImageFont.load_default()
    cw = (width - 12) // 2
    rows = []
    for b, a in pairs:
        ims = []
        for pth in (b, a):
            im = Image.open(pth).convert("RGB")
            ims.append(im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS))
        hh = max(i.height for i in ims)
        row = Image.new("RGB", (width, hh), (244, 243, 239))
        row.paste(ims[0], (0, 0))
        row.paste(ims[1], (cw + 12, 0))
        rows.append(row)
    head = 120
    im = Image.new("RGB", (width, head + sum(r.height for r in rows) + 12 * (len(rows) - 1)), (244, 243, 239))
    d = ImageDraw.Draw(im)
    for i in range(2):
        d.text((28 + i * (cw + 12), 12), titles[i], fill=(30, 30, 30), font=f)
        d.text((28 + i * (cw + 12), 68), subs[i], fill=(95, 95, 88), font=fs)
    y = head
    for r in rows:
        im.paste(r, (0, y))
        y += r.height + 12
    im.save(out_png, optimize=True)
    CR.shrink_png(Path(out_png))
    return out_png


def main(argv=None):
    ap = argparse.ArgumentParser(description="huntkit.viz3d.studio: build and render a concept (see module docstring)")
    ap.add_argument("--job", help="internal: job JSON written by studio.render (runs stage 2 in Blender's Python)")
    ap.add_argument("--concept", choices=sorted(CONCEPTS), help="build a registered concept (stage 1)")
    ap.add_argument("--scene", help="existing *.scene.json to render")
    ap.add_argument("--shots", help="shots JSON, or comma list of presets (hero,side,front34)")
    ap.add_argument("--out", default=str(REPO / "outputs" / "screens"))
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--quality", default="final", choices=sorted(QUALITY))
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--title", default=None)
    ap.add_argument("--no-caption", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    a = ap.parse_args(argv)
    if a.job:
        j = json.loads(Path(a.job).read_text())
        res = render_scene(j["scene"], j["shots"], j["out"], j["prefix"], j["quality"], j["start"], j["captions"],
                           j.get("wearer"), j.get("wearer_kwargs"), j.get("pack_on_torso"), j.get("threads"),
                           j.get("title"), j.get("camo"), j.get("torso", 19.0))
        Path(a.job).with_suffix(".result.json").write_text(json.dumps(res))
        return res
    scene = Path(a.scene) if a.scene else None
    if a.concept:
        sc = CONCEPTS[a.concept]()
        scene = sc.build()
    if a.build_only or scene is None:
        return scene
    if a.shots and Path(a.shots).exists():
        sh = json.loads(Path(a.shots).read_text())
    else:
        sh = shots(*[s for s in (a.shots or "hero,side,front34").split(",") if s])
    return render(scene, sh, a.out, a.prefix, a.quality, a.start, not a.no_caption, title=a.title)


if __name__ == "__main__":
    main()
_ = field
