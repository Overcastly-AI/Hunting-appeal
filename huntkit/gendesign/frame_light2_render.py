"""3D render of the recommended light frame next to today's printed branch frame (Blender Cycles).

Two halves:
- ``build_meshes(cand)`` (repo Python: numpy, scikit-image, trimesh) writes STL files per material: carbon tubes and
  tendon wraps from the beam-model geometry of ``frame_light2.build`` (19 in), organic printed knuckles as a
  smooth-union signed-distance field (sockets + tapered root fingers) meshed by marching cubes, the formed pan, the
  Ti mount; and today's frame (``print/frame/genframe_assembled.stl`` + the same carbon crown), placed 420 mm to the
  left.
- ``render_all(ctx)`` runs Blender (bpy venv, see ``huntkit/viz3d/README.md``) on ``_bpy_main`` below, which reuses
  the studio scene, materials and compositing of ``huntkit.viz3d.cycles_render``.

Run alone: ``python -m huntkit.gendesign.frame_light2_render`` (reads the saved results JSON).
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / "outputs" / "frame_light2_render"
BPY = Path(os.environ.get("HUNTKIT_BPY", "/tmp/claude-0/-home-user-Hunting-appeal/"
                          "4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/scratchpad/bpyenv/bin/python"))
TODAY_DX = -420.0


# ----------------------------------------------------------------------------- geometry helpers
def _cyl(p0, p1, r, sections=28):
    import trimesh
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    if L < 1e-6:
        return None
    c = trimesh.creation.cylinder(radius=r, height=L, sections=sections)
    T = trimesh.geometry.align_vectors([0, 0, 1], (p1 - p0) / L)
    c.apply_transform(T)
    c.apply_translation((p0 + p1) / 2)
    return c


def _cone(p0, p1, r0, r1, sections=28):
    """Truncated cone from p0 (radius r0) to p1 (radius r1)."""
    import trimesh
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    n = sections
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring0 = np.c_[r0 * np.cos(th), r0 * np.sin(th), np.zeros(n)]
    ring1 = np.c_[r1 * np.cos(th), r1 * np.sin(th), np.full(n, L)]
    V = np.r_[ring0, ring1, [[0, 0, 0], [0, 0, L]]]
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    m = trimesh.Trimesh(V, np.array(F), process=True)
    m.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], (p1 - p0) / L))
    m.apply_translation(p0)
    return m


def _seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1), t


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def knuckle_mesh(center, arms, core_r, h=1.0, k=5.0, fingers=4, finger_len=1.7):
    """Organic printed knuckle: sphere core + one socket capsule per arm (direction, tube radius, socket length,
    socket wall) + tapered root fingers spiralling a little along each tube. Smooth union, marching cubes."""
    import trimesh
    from skimage.measure import marching_cubes
    center = np.asarray(center, float)
    reach = max(a[2] * finger_len + a[1] + 4 for a in arms) + core_r
    lo, hi = center - reach, center + reach
    xs = [np.arange(lo[i], hi[i] + h, h) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing="ij")
    P = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    d = np.linalg.norm(P - center, axis=1) - core_r
    for (u, rt, L, wall) in arms:
        u = np.asarray(u, float) / np.linalg.norm(u)
        a, b = center, center + u * L
        dist, t = _seg_dist(P, a, b)
        rs = rt + wall * (1.0 - 0.45 * t)                       # socket tapers to the lip
        d = _smin(d, dist - rs, k)
        # root fingers on the tube surface
        e1 = np.cross(u, [0, 0, 1.0] if abs(u[2]) < 0.9 else [1.0, 0, 0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(u, e1)
        for f in range(fingers):
            ph = 2 * np.pi * f / fingers + 0.35
            off0 = (rt + wall * 0.6) * (np.cos(ph) * e1 + np.sin(ph) * e2)
            ph1 = ph + 0.35
            off1 = (rt + 0.6) * (np.cos(ph1) * e1 + np.sin(ph1) * e2)
            fa, fb = center + u * (0.5 * L) + off0, center + u * (L * finger_len) + off1
            dd, tt = _seg_dist(P, fa, fb)
            d = _smin(d, dd - (1.9 * (1 - tt) + 0.5), 2.5)
    V = d.reshape(X.shape)
    verts, faces, _, _ = marching_cubes(V, 0.0, spacing=(h, h, h))
    m = trimesh.Trimesh(verts + lo, faces, process=True)
    trimesh.smoothing.filter_taubin(m, iterations=8)
    return m


def build_meshes(cand: dict, out: Path = WORK) -> dict:
    """Write STLs (mm, frame coordinates) for the concept and today's frame. Returns {material: path}."""
    import trimesh
    from huntkit.fea.sections import from_spec
    from . import frame_light2 as L
    out.mkdir(parents=True, exist_ok=True)
    m = L.build(cand, 19.0)
    N = {k: np.array(v, float) for k, v in m["nodes"].items()}
    od = lambda spec: from_spec(L._spec(*spec)).dims["od"]
    ds, dbar, dub = od(cand["stay"]), od(cand["bar"]), od(cand["ubar"])
    wrap = cand.get("joint_mode") == "wrap"
    carbon, printed, ti = [], [], []
    crown = []
    for tag, sx in (("L", -1), ("R", 1)):
        carbon.append(_cyl(N[f"S{tag}0"], N[f"S{tag}530"], ds / 2))
        crown.append(_cyl(N[f"C{tag}530"], N[f"C{tag}top"], 8.0))
    carbon.append(_cyl(N["SL330"], N["SR330"], dbar / 2))
    carbon.append(_cyl(N["SL520"], N["SR520"], dub / 2))
    crown.append(_cyl(N["CLtop"], N["CRtop"], 9.0))
    sp_end = [n for n in N if n.startswith("SP")]
    lowest = min(sp_end, key=lambda n: N[n][2])
    crown.append(_cyl(N["TB1"], N[lowest], 10.0))
    if cand.get("branch"):
        db = od(cand["branch"]["sec"])
        for tag in ("L", "R"):
            carbon.append(_cyl(N[m["plate_grid"]["2,1" if tag == "L" else "2,3"]], N[f"S{tag}330"], db / 2))
    # formed lumbar pan: face + two return flanges (y toward the body)
    yL = N["SL120"][1]
    pan = trimesh.creation.box(extents=(250.0, cand["pan_t"] * 1.2, 140.0))
    pan.apply_translation((0.0, yL - ds / 2 - 1.0, 120.0))
    carbon.append(pan)
    for z in (50.0, 190.0):
        fl = trimesh.creation.box(extents=(250.0, 25.0, 1.8))
        fl.apply_translation((0.0, yL - ds / 2 - 13.0, z))
        carbon.append(fl)
    # knuckles
    t = 2.4
    r_s = ds / 2 + 0.5
    up = N["SL530"] - N["SL0"]
    up /= np.linalg.norm(up)
    tendons = []
    for tag, sx in (("L", -1.0), ("R", 1.0)):
        inward = np.array([-sx, 0.0, 0.0])
        for z, rb in ((330.0, dbar / 2 + 0.5), (520.0, dub / 2 + 0.5)):
            c = N[f"S{tag}{z:g}"]
            arms = [(up, r_s, 32.0, t), (-up, r_s, 32.0, t), (inward, rb, 34.0, t)]
            if cand.get("branch") and z == 330.0:
                d_br = N[m["plate_grid"]["2,1" if tag == "L" else "2,3"]] - c
                arms.append((d_br, od(cand["branch"]["sec"]) / 2 + 0.5, 30.0, t))
            printed.append(knuckle_mesh(c, arms, core_r=r_s + 6.5, k=7.0))
            if wrap:
                for u, rr, LL in ((up, ds / 2, 40.0), (-up, ds / 2, 40.0), (inward, rb - 0.5, 30.0)):
                    tendons.append(_cone(c + u * (0.55 * LL + 8), c + u * (LL + 26), rr + 1.3, rr + 0.45))
        # foot node
        c = N[f"S{tag}0"]
        printed.append(knuckle_mesh(c + up * 4, [(up, r_s, 40.0, t), (np.array([sx * 0.3, 1.0, 0.0]), 5.0, 14.0, 3.0)],
                                    core_r=r_s + 5.0))
        if wrap:
            tendons.append(_cone(c + up * 34, c + up * 70, ds / 2 + 1.3, ds / 2 + 0.45))
        # stay-top collar
        c = N[f"S{tag}530"]
        printed.append(knuckle_mesh(c - up * 18, [(up, r_s, 16.0, 3.0), (-up, r_s, 22.0, 3.0)], core_r=r_s + 2.5,
                                    fingers=3, finger_len=1.4))
        # clips
        for z in (80.0, 110.0, 190.0, 250.0, 420.0):
            p = N["SL0"] + (N["SL530"] - N["SL0"]) * (z / N["SL530"][2])
            p[0] *= -1 if tag == "R" else 1
            printed.append(knuckle_mesh(p, [(up, r_s, 9.0, 2.0), (-up, r_s, 9.0, 2.0),
                                            (np.array([0.0, 1.0, 0.0]), 3.0, 9.0, 2.0)], core_r=r_s + 2.0,
                                        fingers=2, finger_len=1.3, k=3.0))
    # hip node: flange on the pan + boss to the pivot
    hp = N["HP"]
    face = np.array([0.0, yL - ds / 2 - 2.5, 120.0])
    printed.append(knuckle_mesh(face, [(np.array([-1.0, 0, 0]), 4.0, 30.0, 2.5), (np.array([1.0, 0, 0]), 4.0, 30.0, 2.5),
                                       (np.array([0, 0, 1.0]), 4.0, 26.0, 2.5), (np.array([0, 0, -1.0]), 4.0, 26.0, 2.5),
                                       (hp - face, 10.0, float(np.linalg.norm(hp - face)) - 4, 5.0)],
                                core_r=14.0, fingers=2, finger_len=1.2))
    ti.append(_cyl(hp + np.array([0, 3.0, 0]), hp - np.array([0, 6.0, 0]), 9.0))
    files = {}
    for name, parts, dx in (("light_carbon", carbon + tendons + crown, 0.0), ("light_printed", printed, 0.0),
                            ("light_ti", ti, 0.0), ("today_carbon", crown, TODAY_DX)):
        mm = trimesh.util.concatenate([p for p in parts if p is not None])
        mm.apply_translation((dx, 0, 0))
        f = out / f"{name}.stl"
        mm.export(f)
        files[name] = str(f)
    body = trimesh.load(REPO / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    body.apply_translation((TODAY_DX, 0, 0))
    f = out / "today_printed.stl"
    body.export(f)
    files["today_printed"] = str(f)
    (out / "manifest.json").write_text(json.dumps({"files": files, "concept": cand["name"]}, indent=1))
    return files


# ----------------------------------------------------------------------------- Blender side
def _bpy_main(argv):
    """Runs inside the bpy venv: python frame_light2_render.py --bpy <work> <out_prefix> <samples> <caption>"""
    import bpy
    sys.path.insert(0, str(REPO))
    from huntkit.viz3d import cycles_render as CR
    work, prefix, samples, label = Path(argv[0]), argv[1], int(argv[2]), argv[3]
    man = json.loads((work / "manifest.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = CR.setup_scene(samples, (1600, 1100), 4)
    mats = {}
    for key, base, rough, coat, bump in (("carbon", "#101112", 0.28, 0.9, 0.0), ("printed", "#4b4945", 0.72, 0.0, 0.35),
                                         ("ti", "#8d8a84", 0.35, 0.0, 0.0)):
        mt = bpy.data.materials.new(key)
        mt.use_nodes = True
        CR.solid(mt, CR.hexlin(base), rough, metallic=1.0 if key == "ti" else 0.0, coat=coat, noise_bump=bump)
        mats[key] = mt
    objs = []
    for name, path in man["files"].items():
        bpy.ops.wm.stl_import(filepath=path)
        ob = bpy.context.selected_objects[0]
        ob.scale = (0.001, 0.001, 0.001)
        mat = "carbon" if "carbon" in name else ("ti" if "ti" in name else "printed")
        ob.data.materials.clear()
        ob.data.materials.append(mats[mat])
        for p in ob.data.polygons:
            p.use_smooth = True
        objs.append(ob)
    bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    CR.solid(fm, CR.hexlin("#d9d6cd"), 0.9, spec=0.2)
    floor.data.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    key = CR._area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2)
    fill = CR._area("fill", 22.0, 2.4, (0.88, 0.93, 1.0), 1.6)
    rim = CR._area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0)
    shots = [("pair", -30.0, 14.0, None, 1.0, f"Today's printed frame (left) vs {label} (right)",
              "same carbon crown; dark matte = printed PAHT-CF, gloss = carbon"),
             ("knuckle", -40.0, 18.0, ((0.05, -0.05, 0.27), (0.16, 0.05, 0.39)), 1.0,
              f"{label}: mid knuckle (z 330) close-up", "printed knuckle and root fingers; carbon tendon wraps on the tubes"),
             ("light_rear", 200.0, 16.0, ((-0.16, -0.08, -0.01), (0.16, 0.05, 0.72)), 0.95,
              f"{label}: back (wearer) side", "formed carbon lumbar pan, printed hip node with the Ti pivot mount")]
    outs = []
    for k, (nm, az, el, box, zoom, cap, sub) in enumerate(shots):
        for o in objs:
            o.hide_render = nm != "pair" and o.name.startswith("today")
        lo, hi = CR.visible_bounds([o for o in objs if not o.hide_render])
        floor.location = (0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2] - 0.001)
        if box is None:
            bmin, bmax = lo, hi
        else:
            # frame coords (x, y aft, z up) in m -> Blender (x, -y?): STL kept as is, so Blender = frame coords
            bmin, bmax = box
        cd.angle_y = math.radians(28.0)
        pos, tgt = CR.fit_camera(bmin, bmax, az, el, 28.0, 1600 / 1100, zoom)
        cam.location = pos
        CR._aim(cam, tgt)
        dist = math.dist(pos, tgt)
        cd.dof.use_dof = True
        cd.dof.focus_distance = dist
        cd.dof.aperture_fstop = 8.0
        CR.place_rig((key, fill, rim), az, tgt, max(1.6, 0.75 * dist))
        raw = work / f"_raw_{nm}.png"
        sc.render.filepath = str(raw)
        bpy.ops.render.render(write_still=True)
        out = Path(f"{prefix}_{nm}.png")
        CR.composite(raw, out, cap, sub)
        CR.shrink_png(out)
        outs.append(str(out))
        print("RENDERED", out, flush=True)
    return outs


def render_all(ctx, samples: int = 24) -> list[str]:
    """Build meshes for the recommended concept and render the three shots. Returns the screenshot paths
    (outputs/screens/<SHOT>_4.._6.png)."""
    from . import frame_light2 as L
    from .frame_light2_report import recommend
    best = recommend(ctx)
    cand = ctx["concepts"][best]["cand"]
    cand = {**cand, "stay": tuple(cand["stay"]), "bar": tuple(cand["bar"]), "ubar": tuple(cand["ubar"])}
    if cand.get("branch"):
        cand["branch"] = {"sec": tuple(cand["branch"]["sec"])}
    build_meshes(cand)
    prefix = WORK / "shot"
    r = subprocess.run([str(BPY), str(Path(__file__).resolve()), "--bpy", str(WORK), str(prefix), str(samples), best],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    out = []
    for i, nm in enumerate(("pair", "knuckle", "light_rear"), start=4):
        src = Path(f"{prefix}_{nm}.png")
        dst = L.SCREENS / f"{L.SHOT}_{i}.png"
        dst.write_bytes(src.read_bytes())
        out.append(str(dst))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bpy":
        _bpy_main(sys.argv[2:])
    else:
        from . import frame_light2 as L
        ctx = json.loads(L.RESULTS.read_text())
        print(render_all(ctx))
