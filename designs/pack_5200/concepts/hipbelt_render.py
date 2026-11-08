"""Hipbelt B on the mannequin: Blender Cycles render (pack-designer, 2026-11-08).

Two stages, because bpy only runs on the CPython 3.11 venv (huntkit/viz3d/README.md):

1. ``python designs/pack_5200/concepts/hipbelt_render.py --mesh``  (repo python) writes OBJ meshes to
   ``outputs/cycles_work/hipbelt/``: a mannequin pelvis/torso lofted from the ANSUR II male-34-in median hip form
   (the same superellipse section the pressure model uses), the recommended belt B size L (cone 5 deg, wing from
   ``hipbelt.wing_edges``), the terraced lumbar pad, the centre plate + Ti pivot, 50 mm front webbing, 25 mm 2:1
   pulls with D-rings, the buckle and two pockets.
2. ``$SCRATCH/bpyenv/bin/python designs/pack_5200/concepts/hipbelt_render.py --render`` imports them, swaps the
   materials for the Cycles shaders of ``huntkit.viz3d.cycles_render`` and renders rear-3/4 and side views.

Visual only: the shapes come from the analysis model; nothing here is a build file.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
WORK = ROOT / "outputs" / "cycles_work" / "hipbelt"
SCREENS = ROOT / "outputs" / "screens"


# =========================================================================================== stage 1: meshes
def _grid_faces(nu, nv, closed_u=False):
    f = []
    for i in range(nu - (0 if closed_u else 1)):
        for j in range(nv - 1):
            a = i * nv + j
            b = ((i + 1) % nu) * nv + j
            f.append((a, b, b + 1, a + 1))
    return f


def build_meshes():
    import numpy as np
    sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
    import hipbelt_concepts as HC
    from huntkit.gendesign import hipbelt as hb

    form = hb.hip_form("male", 34)
    d = HC.B
    size = d.size_for(form.circ_in)
    sec = hb.section(form)
    ex = sec.ex
    objs = {}       # name -> (material, verts list, faces list)

    def add(name, mat, V, F):
        objs[name] = (mat, np.asarray(V, float), list(F))

    # ---------------- mannequin: torso loft z -330 .. +360 (z 0 = iliac crest), two thigh stubs
    zs = np.linspace(-300, 360, 67)
    M = 96
    rings = []
    for z in zs:
        zc = min(z, 110.0)
        zz = max(zc, -170.0)
        a = form.a0 - form.tan_lat * zz
        bb = form.b0 - form.tan_post * zz
        bf = form.b0
        if z > 110:                      # toward the ribcage: widen gently (visual only)
            k = (z - 110) / 250.0
            a *= 1 + 0.10 * k
            bb *= 1 + 0.12 * k
            bf *= 1 + 0.14 * k
        if z < -170:                     # buttock -> upper thigh: round off (visual only)
            k = (-170 - z) / 130.0
            a *= 1 - 0.10 * k
            bb *= 1 - 0.25 * k ** 1.5
        t, P = hb._se_pts(a, bf, bb, ex, m=M + 1)
        P = P[:-1]
        rings.append(np.column_stack([P, np.full(M, z)]))
    V = np.vstack(rings)
    F = []
    nz = len(zs)
    for j in range(nz - 1):
        for i in range(M):
            a_, b_ = j * M + i, j * M + (i + 1) % M
            F.append((a_, b_, b_ + M, a_ + M))
    add("mannequin_torso", "clay", V, F)

    # ---------------- belt band: lumbar + both wings as one parametric surface
    s_root = d.lumbar_w / 2
    s_tip = s_root + d.wing_len(size)
    ns, nv = 140, 18
    s = np.linspace(-s_tip, s_tip, ns)
    sa = np.abs(s)
    cx = np.interp(sa, sec.s, sec.xy[:, 0]) * np.sign(s + 1e-9)
    cy = np.interp(sa, sec.s, sec.xy[:, 1])
    nx = np.interp(sa, sec.s, sec.nrm[:, 0]) * np.sign(s + 1e-9)
    ny = np.interp(sa, sec.s, sec.nrm[:, 1])
    nn = np.hypot(nx, ny)
    nx, ny = nx / nn, ny / nn
    frac = np.clip((sa - s_root) / (s_tip - s_root), 0, 1)
    fh, hh = zip(*d.wing_h)
    h = np.where(sa <= s_root, d.lumbar_h, np.interp(frac, fh, hh))
    beta = np.where(sa <= s_root, math.atan(form.tan_post * 0.8), math.radians(d.beta(size)))
    t_w = sum(L.t for L in d.wing_foam) + 3.0
    t_l = sum(L.t for L in d.lumbar_foam) + 3.0
    tk = np.where(sa <= s_root, t_l, t_w * (1 - 0.35 * frac))
    v = np.linspace(-1, 1, nv)
    inner, outer = [], []
    for i in range(ns):
        g = np.array([-math.sin(beta[i]) * nx[i], -math.sin(beta[i]) * ny[i], math.cos(beta[i])])
        n3 = np.array([nx[i], ny[i], 0.0])
        for vv in v:
            base = np.array([cx[i], cy[i], 0.0]) + n3 * 1.5 + g * (vv * h[i] / 2)
            # rounded edge: thickness tapers near the top / bottom edges
            tt = tk[i] * (1 - vv ** 8) + 2.0
            if sa[i] <= s_root:          # terraced lumbar: thicker at the top (fills the lumbar hollow)
                tt += max(0.0, d.taper(size) * (vv + 1) / 2 * h[i]) * 0.9
            inner.append(base)
            outer.append(base + n3 * tt)
    inner, outer = np.array(inner), np.array(outer)
    Fi = []
    for i in range(ns - 1):
        for j in range(nv - 1):
            a = i * nv + j
            Fi.append((a, a + 1, a + nv + 1, a + nv))
    add("belt_face_spacer", "spacer_mesh", inner, Fi)
    Fo = [(f[0], f[3], f[2], f[1]) for f in Fi]
    add("belt_shell", "harness_shell", outer, Fo)
    # binding along top / bottom edges and tips (thin strips joining inner and outer)
    Vb, Fb = [], []
    for j in (0, nv - 1):
        base_i = len(Vb)
        for i in range(ns):
            Vb.append(inner[i * nv + j])
            Vb.append(outer[i * nv + j])
        for i in range(ns - 1):
            a = base_i + 2 * i
            Fb.append((a, a + 2, a + 3, a + 1) if j == 0 else (a, a + 1, a + 3, a + 2))
    for i in (0, ns - 1):
        base_i = len(Vb)
        for j in range(nv):
            Vb.append(inner[i * nv + j])
            Vb.append(outer[i * nv + j])
        for j in range(nv - 1):
            a = base_i + 2 * j
            Fb.append((a, a + 2, a + 3, a + 1) if i == 0 else (a, a + 1, a + 3, a + 2))
    add("belt_binding", "binding_trim", Vb, Fb)

    def strap(path_pts, width, thick, normal_fn, mat, name):
        P = np.asarray(path_pts, float)
        Vs, Fs = [], []
        for k, p in enumerate(P):
            n = normal_fn(k)
            up = np.array([0, 0, 1.0])
            for (du, dn) in ((-width / 2, 0), (width / 2, 0), (width / 2, thick), (-width / 2, thick)):
                Vs.append(p + up * du + n * dn)
        for k in range(len(P) - 1):
            for q in range(4):
                a, b = k * 4 + q, k * 4 + (q + 1) % 4
                Fs.append((a, b, b + 4, a + 4))
        add(name, mat, Vs, Fs)

    # ---------------- front webbing: 50 mm from each tip to the buckle, across the abdomen (on the skin + 4 mm)
    s_front = np.linspace(s_tip - 30, sec.half_perim - 34, 40)
    for sgn in (-1, 1):
        pts, nrms = [], []
        for ss in s_front:
            px = np.interp(ss, sec.s, sec.xy[:, 0]) * sgn
            py = np.interp(ss, sec.s, sec.xy[:, 1])
            qx = np.interp(ss, sec.s, sec.nrm[:, 0]) * sgn
            qy = np.interp(ss, sec.s, sec.nrm[:, 1])
            pts.append((px + qx * (4 + t_w * 0.6), py + qy * (4 + t_w * 0.6), -4.0))
            nrms.append(np.array([qx, qy, 0.0]) / math.hypot(qx, qy))
        strap(pts, 50.0, 2.0, lambda k, N=nrms: N[k], "webbing", f"web50_{'L' if sgn < 0 else 'R'}")
        # 2:1 pulls: two 25 mm straps from the tip D-ring forward to the buckle, stacked above/below the 50 mm
        for dz in (-34.0, 34.0):
            pts2 = [(p[0] + n[0] * 3, p[1] + n[1] * 3, dz * 0.55) for p, n in zip(pts[:28], nrms[:28])]
            strap(pts2, 22.0, 1.6, lambda k, N=nrms: N[k], "webbing", f"pull_{'L' if sgn < 0 else 'R'}_{int(dz)}")
        # D-ring at the tip (torus, POM-black anodised Al)
        p0 = np.array(pts[0])
        n0 = nrms[0]
        Vr, Fr = [], []
        R, r = 16.0, 2.6
        nu, nw = 24, 10
        tang = np.array([-n0[1], n0[0], 0.0])
        for i in range(nu):
            a = 2 * math.pi * i / nu
            c = p0 + n0 * 6 + (tang * math.cos(a) + np.array([0, 0, 1.0]) * math.sin(a)) * R
            radial = (tang * math.cos(a) + np.array([0, 0, 1.0]) * math.sin(a))
            for j in range(nw):
                b = 2 * math.pi * j / nw
                Vr.append(c + (radial * math.cos(b) + n0 * math.sin(b)) * r)
        for i in range(nu):
            for j in range(nw):
                a = i * nw + j
                b = ((i + 1) % nu) * nw + j
                c2 = ((i + 1) % nu) * nw + (j + 1) % nw
                e = i * nw + (j + 1) % nw
                Fr.append((a, b, c2, e))
        add(f"dring_{'L' if sgn < 0 else 'R'}", "aluminium_7075", Vr, Fr)

    # buckle at the front centre: two halves as rounded boxes
    yf = float(np.interp(sec.half_perim, sec.s, sec.xy[:, 1])) - 8
    def box(cx_, cy_, cz_, sx, sy, sz, name, mat):
        Vb2 = [(cx_ + dx * sx / 2, cy_ + dy * sy / 2, cz_ + dz * sz / 2) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
        Fb2 = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        add(name, mat, Vb2, Fb2)
    box(-22, yf, -4, 46, 12, 62, "buckle_female", "pom_black")
    box(22, yf, -4, 40, 9, 56, "buckle_male", "pom_black")

    # centre plate + Ti pivot directly behind the lumbar pad (frame side, +y)
    lum = [i for i in range(ns) if sa[i] <= s_root]
    yb = float(max(outer[i * nv + j][1] for i in lum for j in range(nv)))
    box(0, yb + 3, 0, 100, 6, 110, "centre_plate", "pom_black")
    th = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    Vp = [(6 * math.cos(a), yb + 6 + dy, 6 * math.sin(a)) for dy in (0, 36) for a in th]
    Fp = [(i, (i + 1) % 24, 24 + (i + 1) % 24, 24 + i) for i in range(24)]
    add("ti_pivot", "titanium", Vp, Fp)

    # ---------------- pockets on both wings: curved boxes on the wing outer face
    for sgn in (-1, 1):
        sel = [i for i in range(ns) if (sgn * s[i] > s_root + 30) and (sgn * s[i] < s_tip - 40)]
        P_ = []
        Fq = []
        for k, i in enumerate(sel):
            n3 = np.array([nx[i], ny[i], 0.0])
            o = outer[i * nv + nv // 2]
            for (dz, dn) in ((-48, 0), (48, 0), (44, 32), (-44, 32)):
                P_.append(o + np.array([0, 0, dz - 6]) + n3 * dn)
        for k in range(len(sel) - 1):
            for q in range(4):
                a, b = k * 4 + q, k * 4 + (q + 1) % 4
                Fq.append((a, b, b + 4, a + 4))
        n0 = len(sel)
        Fq.append((0, 1, 2, 3))
        Fq.append(((n0 - 1) * 4 + 3, (n0 - 1) * 4 + 2, (n0 - 1) * 4 + 1, (n0 - 1) * 4))
        add(f"pocket_{'L' if sgn < 0 else 'R'}", "cordura_body", P_, Fq)

    WORK.mkdir(parents=True, exist_ok=True)
    mtl = WORK / "hipbelt.mtl"
    mats = sorted({m for m, _, _ in objs.values()})
    mtl.write_text("".join(f"newmtl {m}\nKd 0.5 0.5 0.5\n\n" for m in mats))
    lines = ["mtllib hipbelt.mtl\n"]
    off = 1
    for name, (mat, Vv, Ff) in objs.items():
        lines.append(f"o {name}\nusemtl {mat}\n")
        lines += [f"v {x / 1000:.5f} {y / 1000:.5f} {z / 1000:.5f}\n" for x, y, z in Vv]
        lines += ["f " + " ".join(str(off + q) for q in f) + "\n" for f in Ff]
        off += len(Vv)
    (WORK / "hipbelt.obj").write_text("".join(lines))
    return WORK / "hipbelt.obj", size, form.name


# =========================================================================================== stage 2: render
SHOTS = {
    "rear34": {"cam": (0.80, 1.00, 0.16), "tgt": (0.0, 0.01, -0.02), "lens": 55,
               "caption": "Hipbelt B on a male 34 in ANSUR II hip (size L), rear 3/4",
               "sub": "cone-cut wings (5 deg), terraced dual-density lumbar, centre plate + Ti pivot, 2:1 pulls"},
    "side": {"cam": (1.25, -0.10, 0.06), "tgt": (0.0, -0.01, -0.02), "lens": 55,
             "caption": "Hipbelt B, side: the wing follows the hip cone",
             "sub": "top edge tucks in over the crest; soft tip stops behind the ASIS; 50 mm buckle + 2:1 pulls"},
}


def render(samples=40, res=(1400, 1050), views=("rear34", "side"), start=6):
    import bpy
    from huntkit.viz3d import cycles_render as CR
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(WORK / "hipbelt.obj"), forward_axis="Y", up_axis="Z")
    sc = CR.setup_scene(samples, res, threads=4)
    for mat in list(bpy.data.materials):
        if not mat.use_nodes:
            mat.use_nodes = True
        name = mat.name.split(".")[0]
        if name == "clay":
            CR.solid(mat, CR.hexlin("#9a9a98"), 0.72, spec=0.3)
        elif name == "harness_shell":
            CR.fabric(mat, CR.hexlin("#4a4d3c"), uv_mm=500.0, rough=0.78, grid_mm=6.0, sheen=0.4, wrinkles=0.6)
        elif name == "cordura_body":
            CR.fabric(mat, CR.hexlin("#5b5a45"), uv_mm=500.0, rough=0.76, grid_mm=6.0, sheen=0.45)
        elif name == "binding_trim":
            CR.fabric(mat, CR.hexlin("#a5662f"), uv_mm=500.0, rough=0.72, grid_mm=None, weave_mm=0.8, sheen=0.55,
                      wrinkles=0.0)
        elif name == "spacer_mesh":
            CR.spacer_mesh(mat, 500.0)
        elif name == "webbing":
            CR.webbing(mat, CR.hexlin("#26271f"), 500.0)
        elif name == "pom_black":
            CR.solid(mat, CR.hexlin("#141415"), 0.5, spec=0.4, noise_bump=0.3)
        elif name == "aluminium_7075":
            CR.solid(mat, CR.hexlin("#1b1c1e"), 0.42, metallic=0.75, spec=0.5)
        elif name == "titanium":
            CR.solid(mat, CR.hexlin("#8e9094"), 0.38, metallic=1.0)
        elif name == "carbon_twill":
            CR.solid(mat, CR.hexlin("#1e1f21"), 0.32, coat=0.9, spec=0.5)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            for p in ob.data.polygons:
                p.use_smooth = not ob.name.startswith(("buckle", "centre_plate", "lumbar_pan"))
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, -0.31))
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    key = CR._area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2)
    fill = CR._area("fill", 18.0, 2.4, (0.88, 0.93, 1.0), 1.6)
    rim = CR._area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0)
    out = []
    for k, v in enumerate(views):
        sh = SHOTS[v]
        cam.location = sh["cam"]
        CR._aim(cam, sh["tgt"])
        cd.lens = sh["lens"]
        cd.dof.use_dof = False
        az = math.degrees(math.atan2(sh["cam"][0], -sh["cam"][1]))   # cycles_render.view_dir convention
        CR.place_rig((key, fill, rim), az, sh["tgt"], 2.2)
        raw = WORK / f"_raw_{v}.png"
        sc.render.filepath = str(raw)
        bpy.ops.render.render(write_still=True)
        dst = SCREENS / f"20261108_hipbelt_{start + k}.png"
        CR.composite(raw, dst, sh["caption"], sh["sub"])
        CR.shrink_png(dst)
        out.append(str(dst))
        print(dst, flush=True)
    return out


if __name__ == "__main__":      # pragma: no cover
    if "--mesh" in sys.argv:
        print(build_meshes())
    if "--render" in sys.argv:
        print(render())
