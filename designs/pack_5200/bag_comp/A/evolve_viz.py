"""CORRIE E renders (Team A EVOLVE): the CORRIE B.2 viz3d model (huntkit/viz3d/corrie_b2.py) re-pointed at CORRIE E's
own cloth-sim drape, plus the CORRIE E parts. Nothing in huntkit is edited: the CORRIE model reads ``corrie.make`` /
``corrie.DOOR`` and its sim directory at call time, and ``repointed()`` swaps those for the duration of a build.

    python designs/pack_5200/bag_comp/A/evolve_viz.py --model [--coarse]     # GLB + viewer manifest + shots JSON
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_bagA/bagA.glb \\
        --shots outputs/pack3d_bagA/shots.json --views A_hero,A_side,A_door,A_feature,A_meat \\
        --samples 64 --prefix 20261110_bagA --out outputs/screens

CORRIE E parts added here: the camo tub wall (the sim's own B-05w piece, so camo follows the real drape), the
hip-reach pockets FP-L / FP-R (power mesh, shock-cord top) on the wings' lower front corners, the pole quiver (boot +
grip loop) with a pair of folded carbon poles, snack bars in FP-L.
"""
from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evolve as E  # noqa: E402
import evolve_bag as EB  # noqa: E402
import corrie as CO  # noqa: E402

ROOT = E.ROOT
OUT = ROOT / "outputs" / "pack3d_bagA"
SIM_FINE = ROOT / "outputs" / "clothsim" / "bagA_evolve_PR19_fine"
SIM_COARSE = ROOT / "outputs" / "clothsim" / "bagA_evolve_PR19"


@contextlib.contextmanager
def repointed(sim_dir: Path, fine: bool):
    import huntkit.viz3d.corrie as VC
    saved = (CO.make, CO.DOOR, VC.SCEN, VC.sim_skin.__defaults__, VC.CASE)
    CO.make = lambda rev=None: E.make()
    CO.DOOR = E.DOOR
    VC.SCEN = EB.scenario_file(19)
    VC.sim_skin.__defaults__ = (sim_dir, None, fine)
    try:
        with EB.patched():
            yield VC
    finally:
        CO.make, CO.DOOR, VC.SCEN, VC.sim_skin.__defaults__, VC.CASE = saved


def _unit(v):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def _outer_project(mesh, P, sx, push=30.0, k=6):
    """Point on the OUTBOARD face of a thin wing slab: from a point pushed outboard, IDW of the nearest slab vertices
    (the outboard face's vertices are the nearest ones) and their normals, flipped to point outboard."""
    from scipy.spatial import cKDTree
    V = np.asarray(mesh.vertices)
    vn = np.asarray(mesh.vertex_normals)
    key = id(mesh)
    if key not in _TREES:
        _TREES[key] = cKDTree(V)
    d, j = _TREES[key].query(np.atleast_2d(P) + np.array([sx * push, 0, 0]), k=k)
    w = 1.0 / np.maximum(d, 0.5) ** 2
    w /= w.sum(1, keepdims=True)
    q = np.einsum("ij,ijk->ik", w, V[j])
    n = _unit(np.einsum("ij,ijk->ik", w, vn[j]))
    n = np.where((n[:, :1] * sx) < 0, -n, n)
    return q, n


_TREES = {}


def wing_grid(mesh, nu=36, nv=72):
    """The outboard face grid of a clean wing slab (corrie._wing_clean / _slab: the first (nu+1)(nv+1) vertices are
    the top grid, uv = (u mm, z mm) / TILE_MM). Returns grid (nu+1, nv+1, 3), u mm (nu+1), z mm (nv+1)."""
    from huntkit.viz3d import geom as G
    n0 = (nu + 1) * (nv + 1)
    V = np.asarray(mesh.vertices)[:n0].reshape(nu + 1, nv + 1, 3)
    uv = np.asarray(mesh.metadata["uv"])[:n0].reshape(nu + 1, nv + 1, 2) * G.TILE_MM
    return V, uv[:, 0, 0], uv[0, :, 1]


def _resample_grid(Gd, us_src, zs_src, us, zs):
    from scipy.interpolate import RegularGridInterpolator
    out = np.zeros((len(us), len(zs), 3))
    UU, ZZ = np.meshgrid(us, zs, indexing="ij")
    for k in range(3):
        f = RegularGridInterpolator((us_src, zs_src), Gd[..., k])
        out[..., k] = f(np.column_stack([UU.ravel(), ZZ.ravel()])).reshape(UU.shape)
    return out


def pocket_parts(VC, G, S, wing_mesh, sx, a_of, yf_of, variant, bulge=34.0, tag="", snacks=False):
    """FP pocket on the wing's lower front corner: u 8-188 mm from the root, z 150-380 (E-4), on the wing's own
    outboard face grid."""
    Part = VC.Part
    z0, z1 = E.FP["z"]
    nu, nv = 26, 34
    us = np.linspace(8.0, 8.0 + E.FP["w"], nu + 1)
    zz = np.linspace(z0 + 4, z1, nv + 1)
    Wg, wu, wz = wing_grid(wing_mesh)
    print("wing grid", tag, round(wu.min(), 1), round(wu.max(), 1), round(wz.min(), 1), round(wz.max(), 1))
    q = _resample_grid(Wg, wu, wz, np.clip(us, wu.min(), wu.max()), np.clip(zz, wz.min(), wz.max()))
    du = np.gradient(q, axis=0)
    dv = np.gradient(q, axis=1)
    n = _unit(np.cross(du, dv))
    if np.mean(n[..., 0]) * sx < 0:
        n = -n
    U = (us - us[0]) / (us[-1] - us[0])
    V = (zz - zz[0]) / (zz[-1] - zz[0])
    # pillow: full bulge over the middle, sewn flat on 3 sides, mouth (top) gathered by the shock cord and angled forward
    bu = np.sin(np.pi * U) ** 0.55
    bv = np.clip(np.sin(np.pi * np.clip(V * 0.62 + 0.05, 0, 1)) ** 0.5, 0, 1)
    B = bulge * bu[:, None] * bv[None, :]
    outer = q + n * (3.0 + B[..., None])
    # the mouth drops 26 mm toward the aft side (opening faces forward / up)
    drop = 26.0 * U[:, None] * (V[None, :] ** 6)
    outer[..., 2] -= drop
    inner = q + n * 2.6
    Uu = (us[:, None] * np.ones((1, nv + 1))) / G.TILE_MM
    Zz = (np.ones((nu + 1, 1)) * zz[None, :]) / G.TILE_MM
    face = VC._slab(outer, outer + n * 1.1, Uu * 2.0, Zz * 2.0)
    # camo mouth band (25 mm, folded over the shock-cord channel): the owner's camo as the pocket's accent
    jb = int(np.searchsorted(zz, z1 - 25.0))
    band = VC._slab(outer[:, jb:] + n[:, jb:] * 1.3, outer[:, jb:] + n[:, jb:] * 2.6, Uu[:, jb:] * 0.66, Zz[:, jb:] * 0.66)
    parts = [Part(f"bagA_fp_band_{tag}", band, "camo", "bag", modes=VC.BAGM, explode=(sx * 120, 200, 0), floats=True,
                  variant=variant, label="E-4 pocket mouth band (camo)")]
    parts += [Part(f"bagA_fp_{tag}", face, "trim", "bag", modes=VC.BAGM, explode=(sx * 120, 200, 0), floats=True,
                  variant=variant, label="E-4 hip-reach pocket (power mesh, 2 box pleats, shock-cord top)")]
    # bound edges: sides + bottom sewn to the wing, top = shock-cord channel
    tubes = [G.tube(VC.smooth_line(outer[0], 3.0, 4.0), 2.4, n=8), G.tube(VC.smooth_line(outer[-1], 3.0, 4.0), 2.4, n=8),
             G.tube(VC.smooth_line(outer[:, 0], 3.0, 4.0), 2.4, n=8)]
    top = VC.smooth_line(outer[:, -1] + n[:, -1] * 1.0, 3.0, 5.0)
    tubes.append(G.tube(top, 3.4, n=10))
    parts.append(Part(f"bagA_fp_trim_{tag}", G.concat(tubes), "trim", "bag", modes=VC.BAGM, explode=(sx * 120, 200, 0),
                      floats=True, variant=variant, label="Pocket binding + shock-cord channel"))
    # cord lock + tail at the aft top corner
    ca = top[-1] + n[-1, -1] * 4.0
    lock = VC._block(ca + np.array([0, 0, -6.0]), (11, 9, 16), e=0.4)
    tail = G.tube(VC.smooth_line(np.array([ca, ca + [0, 4, -12], ca + [0, 8, -26]]), 2.0, 3.0), 1.5, n=6)
    parts.append(Part(f"bagA_fp_lock_{tag}", G.concat([lock, tail]), "hardware", "bag", modes=VC.BAGM,
                      explode=(sx * 120, 200, 0), floats=True, variant=variant))
    geo = {"outer": outer, "n": n, "q": q, "us": us, "zz": zz}
    if snacks:   # two snack bars peeking out of the mouth
        bars = []
        for k, (i, dz) in enumerate(((9, 0.0), (15, -10.0))):
            c0 = q[i, -6] + n[i, -6] * (8 + 12 * k)
            up = _unit(np.array([0, -0.25, 1.0]))
            bars.append(VC._block(c0 + up * (40 + dz), (34, 12, 120), e=0.25))
        parts.append(Part(f"bagA_snacks_{tag}", G.concat(bars), "hypalon", "bag", modes=VC.BAGM,
                          explode=(sx * 120, 200, 0), floats=True, variant=variant, label="Today's snacks (FP-L)"))
    return parts, geo


def pole_parts(VC, G, S, geo, wing_mesh, sx, variant, tag=""):
    """E-5: two folded carbon poles, tips in the boot at FP-R's front pleat, grips under the shock-cord loop."""
    Part = VC.Part
    out = geo["outer"]
    n = geo["n"]
    base = out[2, 2] + n[2, 2] * 6.0
    top = base + np.array([sx * 18.0, -14.0, 400.0])
    rods, grips, tips = [], [], []
    for k, off in enumerate((0.0, 17.0)):
        o = np.array([sx * off * 0.6, off * 0.8, 6.0 * k])
        a, b = base + o, top + o
        d = _unit(b - a)
        for s0, s1, r in ((0.0, 0.34, 7.0), (0.34, 0.67, 6.3), (0.67, 0.80, 5.7)):   # 3 folded sections
            rods.append(G.capsule_between(a + d * 400 * s0 + d * 3, a + d * 400 * s1 - d * 3, r))
        grips.append(G.capsule_between(a + d * 320, a + d * 400, 11.5))
        tips.append(G.capsule_between(a - d * 12, a + d * 14, 4.0))
        tips.append(G.capsule_between(a + d * 312, a + d * 322, 12.5))   # grip collar
    loop_c = top + np.array([0, 8.0, -60.0])
    ring = np.array([loop_c + 22 * np.array([np.cos(t) * 0.9, np.sin(t), 0.15 * np.cos(t)]) for t in np.linspace(0, 2 * np.pi, 33)])
    cord = G.tube(VC.smooth_line(ring, 3.0, 3.0, closed=True), 1.6, n=6)
    lock = VC._block(loop_c + np.array([sx * 6, -22.0, -12.0]), (11, 9, 16), e=0.4)
    tabq, tabn = _outer_project(wing_mesh, np.array([loop_c + np.array([0, -30.0, -18.0])]), sx)
    tab = VC._block(tabq[0] + tabn[0] * 2.0, (8, 25, 40), e=0.3)
    return [Part(f"bagA_poles_{tag}", G.concat(rods), "carbon", "bag", modes=VC.BAGM, floats=True, variant=variant,
                 label="Trekking poles (folded) in the E-5 quiver"),
            Part(f"bagA_pole_grips_{tag}", G.concat(grips), "xlpe", "bag", modes=VC.BAGM, floats=True, variant=variant),
            Part(f"bagA_pole_hw_{tag}", G.concat(tips + [lock]), "hardware", "bag", modes=VC.BAGM, floats=True,
                 variant=variant),
            Part(f"bagA_pole_loop_{tag}", G.concat([cord, tab]), "webbing", "bag", modes=VC.BAGM, floats=True,
                 variant=variant, label="Shock-cord grip loop on a webbing tab")]


def build(sim_dir=SIM_FINE, fine=True):
    from huntkit.viz3d import geom as G
    from huntkit.viz3d.params import load_params
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    with repointed(sim_dir, fine) as VC:
        from huntkit.viz3d.corrie_b2 import corrie_b2_pack
        pack = corrie_b2_pack(p)
        S = VC.Skin(VC.sim_skin())
        BC = sys.modules["bag_concepts"]
        c = E.make()
        a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
        yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
        names = [q.name for q in pack.parts]
        # ---- skin: body / camo tub from the sim's own pieces (replaces CORRIE's chevron split and its piping)
        piece = S.piece
        door_m, floor_m, tub_m = piece == "B-02door", piece == "B-05", piece == "B-05w"
        body = S.submesh(~(door_m | floor_m | tub_m))
        tub = S.submesh(tub_m)
        ch = VC.seam_chains(S.F, piece)
        zip_key = frozenset(("B-02door", "B-02u"))
        tubes = []
        for key, chains in ch.items():
            if key == zip_key:
                continue
            for cc in chains:
                if len(cc) > 3:
                    P = VC.smooth_line(S.V[cc], 4.0, 10.0)
                    q, _ = S.project(P, 1.2)
                    tubes.append(G.tube(q, 2.1, n=8))
        repl = {"corrie_body": body, "corrie_kick": tub, "corrie_seams": G.concat(tubes)}
        labels = {"corrie_body": "CORRIE E main bag (cloth-sim drape, packed, 19 in)",
                  "corrie_kick": "E-3 camo tub wall B-05w (500D printed, 60 mm)", "corrie_seams": "Seams"}
        for q in pack.parts:
            if q.name in repl:
                q.mesh = repl[q.name]
                q.label = labels[q.name]
        # ---- pockets, poles on the wings (one set per wing variant)
        new = []
        for q in list(pack.parts):
            if not q.name.startswith("corrie_wing_") or "bar" in q.name or "straps" in q.name or "hw" in q.name:
                continue
            sx = 1 if "_R" in q.name else -1
            tag = q.name.replace("corrie_wing_", "")
            pp, geo = pocket_parts(VC, G, S, q.mesh, sx, a_of, yf_of, q.variant, tag=tag, snacks=(sx < 0))
            new += pp
            if sx > 0:
                new += pole_parts(VC, G, S, geo, q.mesh, sx, q.variant, tag=tag)
        pack.parts += new
        pack.metrics["bag_type"] = "bagA_corrie_e"
        pack.metrics["wing_parts"] = [n for n in names if "wing" in n]
    return pack


SHOTS = {
    "A_hero": {"view": {"az": 38, "el": 12, "zoom": 1.15, "box": [-240, 0, -60, 300, 400, 1110]}, "state": {"mannequin": True, "lid": True},
               "caption": "CORRIE E: 3/4 rear on the display form",
               "sub": "Rounded aft corners, shoulder taper into the roll, camo tub base; poles in the right-wing quiver"},
    "A_side": {"view": {"az": 90, "el": 4, "zoom": 1.0, "box": [-200, -330, 0, 300, 440, 1150]}, "state": {"mannequin": True, "lid": True},
               "caption": "CORRIE E: side profile, wearer's right",
               "sub": "Hip-reach pocket at the belt root with the pole boot; tripod under the wing; tapered shoulder"},
    "A_door": {"view": {"az": -18, "el": 10, "zoom": 1.0, "box": [-260, 60, 60, 260, 420, 820]},
               "state": {"full": True, "lid": True},
               "caption": "CORRIE E: horseshoe door open",
               "sub": "Zip on the rounded corners: 294 / 311 / 334 mm clear at IM1 / IM2 / IM3 (CORRIE 214 / 242 / 281); camo tub base"},
    "A_feature": {"view": {"az": 104, "el": 14, "zoom": 1.0, "box": [180, -10, 110, 320, 240, 620]},
                  "state": {"mannequin": True, "lid": True},
                  "caption": "CORRIE E: hip-reach pocket and pole quiver (right wing)",
                  "sub": "Forward-facing power-mesh pocket at the belt root; pole tips in its boot, grips in a shock-cord loop"},
    "A_meat": {"view": {"az": 70, "el": 10, "zoom": 1.3}, "state": {"mode": "pack", "haul": True, "gap": 170.0},
               "caption": "CORRIE E: meat haul, float mode (170 mm / 6.7 in)",
               "sub": "Quarter in the US1/US2 cradle against the frame; bag hung on the B-24 links; W1-W3 round both"},
}


def model(coarse=False):
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = build(SIM_COARSE if coarse else SIM_FINE, fine=not coarse)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "bagA.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()}
    html = build_html(glb, manifest(pack), m, info, OUT / "bagA_viewer.html", title="Pack 5200 CORRIE E (Team A)")
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    # float meat mode baked for Cycles (cycles_render does not apply the viewer's float / haul offsets): every part
    # that floats moves aft by the 170 mm B-24 gap, haul offsets applied, so the haul state renders as the viewer shows
    import copy
    fl = copy.copy(pack)
    fl.parts = []
    for q in pack.parts:
        q2 = copy.copy(q)
        off = np.asarray(q.haul, float) + (np.array([0.0, 170.0, 0.0]) if q.floats else 0.0)
        if np.any(off):
            q2.mesh = q.mesh.copy()
            q2.mesh.apply_translation(off)
            q2.haul = (0.0, 0.0, 0.0)
        fl.parts.append(q2)
    glbf, _ = export_glb(fl, OUT / "bagA_float.glb", mats=mats)
    build_html(glbf, manifest(fl), m, info, OUT / "bagA_float_viewer.html", title="CORRIE E float (baked)")
    print("GLB", glb, "HTML", html, m.get("wing_parts"))


if __name__ == "__main__":
    if "--model" in sys.argv:
        model(coarse="--coarse" in sys.argv)
