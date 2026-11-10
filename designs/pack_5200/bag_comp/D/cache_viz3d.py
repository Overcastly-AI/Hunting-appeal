"""CACHE (team D) render model: CORRIE B.2's render pack (same cloth-sim shell drape, frame H1 geometry as in the
CORRIE renders, harness, belt B, display form) with the CACHE changes:

* no wings, no roll-top: a cinched drawcord collar (lofted from the sim drape's ring at z 800, gathered with folds)
  and the LID module strapped over it (2 rear straps to the frame-side collar, 2 front cinch straps to the aft
  corners: the top compression);
* optics pod (left): CORRIE's IMP-1 sleeve tube, now hooked straight to the gusset with 4 G-hook tabs;
* tripod kit (right): the tripod on the gusset under 2 cinch straps, foot in a cup;
* modules from Blender cloth (module_cloth_bpy.py): SWAP slab, CAMP, KILL; and the meat-mode SWAP liner.

Four GLBs (one per scene state, because the viewer variants only know door open / closed):
  closed (hero, side), access (door open, CAMP half out), modules (all modules out on the floor), meat (meat mode).

    python designs/pack_5200/bag_comp/D/cache_viz3d.py            # GLBs + shots.json in outputs/pack3d_bagD/
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs" / "pack3d_bagD"

from huntkit.viz3d import geom as G  # noqa: E402
from huntkit.viz3d.corrie import (ROLL_R, Skin, _block, _concept, _frame, _pouch, _sub, _unit,  # noqa: E402
                                  boundary_chains, g_hook, ladder_lock, sim_skin, smooth_line, split_by_field)
from huntkit.viz3d.model import Part  # noqa: E402

BAGM = ("pack", "pack_haul")
DROP_PREFIX = ("corrie_roll", "corrie_pouch", "corrie_wing", "imp4_")
Z_CUT = 800.0          # the drawcord collar is lofted from the sim drape's ring here
Z_MOUTH = 968.0        # cinched mouth (fill line 1056 less the gathered height, ASSUMPTION for the picture)


def base_pack():
    f = OUT / "base_pack.pkl"
    if f.exists():
        return pickle.loads(f.read_bytes())
    from huntkit.viz3d.corrie_b2 import corrie_b2_pack
    from huntkit.viz3d.params import load_params
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pk = corrie_b2_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    f.write_bytes(pickle.dumps((p, pk)))
    return p, pk


def _trim_above(m, z):
    """Cut a mesh exactly at height z, keep below."""
    uv = m.metadata.get("uv", np.zeros((len(m.vertices), 2)))
    V, A, Fneg, Fpos, cut = split_by_field(m.vertices, m.faces, {"uv": uv}, np.asarray(m.vertices)[:, 2] - z)
    return _sub(V, Fneg, A["uv"]), V, Fneg, cut


def _drop_above(m, z):
    """Remove whole faces above z (thin tubes: seams)."""
    keep = np.asarray(m.vertices)[m.faces][:, :, 2].max(1) <= z
    uv = m.metadata.get("uv", np.zeros((len(m.vertices), 2)))
    return _sub(np.asarray(m.vertices), m.faces[keep], uv)


def _ring_at_cut(V, F, cut):
    cs = set(cut.tolist())
    chains = [ch for ch in boundary_chains(F, keep=lambda e: e[0] in cs and e[1] in cs) if len(ch) > 20]
    ch = max(chains, key=len)
    return V[ch]


def collar(body_ring, yf_top):
    """Cinched drawcord collar: from the body ring (z 800) up and in to a gathered mouth, folds growing to the top.
    The frame side stays near the frame (the hood and B-06f), the gather moves the mouth slightly toward it."""
    c0 = body_ring.mean(0)
    th0 = np.arctan2(body_ring[:, 1] - c0[1], body_ring[:, 0] - c0[0])
    o = np.argsort(th0)
    R = body_ring[o]
    th = th0[o]
    M = 240
    tt = np.linspace(-np.pi, np.pi, M, endpoint=False)
    Rx = np.interp(tt, th, R[:, 0], period=2 * np.pi)
    Ry = np.interp(tt, th, R[:, 1], period=2 * np.pi)
    rings = []
    K = 30
    rng = np.random.default_rng(7)
    ph = rng.uniform(0, 2 * np.pi, 3)
    for k in range(K + 1):
        t = k / K
        z = Z_CUT + (Z_MOUTH - Z_CUT) * t
        s = 1.0 - 0.52 * t ** 2.2
        cy = c0[1] - 0.18 * (c0[1] - yf_top) * t ** 2
        bul = 10.0 * np.sin(np.pi * min(t / 0.75, 1.0)) * (1 - t)            # stuffed shoulder below the gather
        fold = (6.5 * t ** 1.8) * (np.sin(16 * tt + ph[0]) + 0.35 * np.sin(29 * tt + ph[1]))
        dx, dy = Rx - c0[0], Ry - c0[1]
        rr = np.hypot(dx, dy)
        ux, uy = dx / rr, dy / rr
        x = c0[0] + dx * s + ux * (bul + fold)
        y = cy + dy * s + uy * (bul + fold)
        zz = np.full(M, z) + 3.0 * t * np.sin(16 * tt + ph[2])
        rings.append(np.column_stack([x, y, zz]))
    # rosette: the gathered fabric above the cord folds in to the centre
    top = rings[-1]
    cm = top.mean(0)
    for j, f in enumerate((0.8, 0.58, 0.34, 0.12)):
        r = cm + (top - cm) * f
        r[:, 2] = Z_MOUTH + 10 + 6 * j + 5 * np.sin(16 * tt + ph[0]) * f
        rings.append(r)
    mesh = G.loft(np.array(rings), pole_end=[cm[0], cm[1], Z_MOUTH + 36])
    chan = rings[int(0.9 * K)]
    ch_pts = np.vstack([chan, chan[:1]])
    hem = G.tube(smooth_line(ch_pts, 3.0, 6.0, closed=True), 6.5, n=10)
    # cord lock + cord ends at the aft centre of the channel
    i = int(np.argmax(chan[:, 1]))
    p = chan[i] + np.array([0, 8, -4])
    lock = _block(p + [0, 6, -18], (16, 12, 26), e=0.4)
    cords = [G.tube(G.catmull_rom(np.array([p + [sx * 4, 2, 0], p + [sx * 3, 8, -12], p + [sx * 2, 12, -40],
                                            p + [sx * 6, 14, -70]]), 8), 1.5, n=6) for sx in (-1, 1)]
    pull = G.capsule_between(p + [0, 15, -72], p + [0, 16, -96], 4.0)
    return mesh, hem, G.concat([lock, pull]), G.concat(cords), cm


def lid_parts(S, cm, yf_of, a_of, yb_of):
    """CORRIE's pouch builder seated on the cinched mouth (a straight 'roll line' at the mouth height), with the front
    straps re-aimed at the aft-corner loops at the collar seam (z 745)."""
    BC, CO = _concept()
    P = {"L": 280.0, "W": 190.0, "H": 60.0}
    xs = np.linspace(-170, 170, 40)
    line = np.column_stack([xs, np.full(40, cm[1] + 8), np.full(40, Z_MOUTH + 26 - ROLL_R)])
    paths = []
    for sx in (-1, 1):
        z = 748.0
        tgt, _ = S.on([sx * (a_of(z) - 18), yb_of(z) - 6, z], 3.0)
        paths.append(np.repeat(tgt, 20, axis=0))
    pm, pc, ptrim, pzip, pzhw, pstr, phw, ptab = _pouch(S, P, line, paths, yf_of, pull_tab=True)
    return pm, pc, ptrim, pzip, pzhw, pstr, phw, ptab


def pod_tabs(S, sleeve, a_of, yf_of, yb_of):
    """Optics pod hook-up: 2 fixed G-hook tabs on its frame edge (z 230 / 545) to the B-01|gusset loops, and 2 cinch
    straps from the aft-corner loops round the pod's outer face to a ladder lock on the frame-edge tab (they also hold
    a sit pad / poles flat over the pod)."""
    V = np.asarray(sleeve.vertices)
    rib, hooks = [], []
    xo = V[:, 0].min()
    for z in (260.0, 520.0):
        band = V[np.abs(V[:, 2] - z) < 12]
        if len(band) < 3:
            band = V[np.argsort(np.abs(V[:, 2] - z))[:40]]
        ef = band[np.argmin(band[:, 1])]
        tf, _ = S.on([-a_of(z), yf_of(z) + 6, z], 1.6)
        tf = tf[0]
        path = G.catmull_rom(np.array([ef + [2, 0, 0], 0.5 * (ef + tf) + [-4, 0, 0], tf]), 6)
        rib.append(G.ribbon(path, 25.0, 1.6, np.tile([-1.0, 0, 0], (len(path), 1)), step=3.0))
        hooks.append(g_hook(tf + [-3.5, 0, 0], np.array([-1.0, 0, 0]), tf - ef))
        ta, _ = S.on([-a_of(z), yb_of(z) - 6, z], 1.6)
        ta = ta[0]
        ya, yfr = band[:, 1].max(), band[:, 1].min()
        pts = np.array([ta, [xo - 2.5, ya + 4, z], [xo - 4.0, 0.5 * (ya + yfr), z], [xo - 2.5, yfr + 6, z],
                        ef + [-8, -4, 0]])
        P = G.catmull_rom(pts, 10)
        t = np.gradient(P, axis=0)
        nrm = _unit(np.column_stack([-t[:, 1], t[:, 0], np.zeros(len(P))]))
        nrm[nrm[:, 0] > 0] *= -1
        rib.append(G.ribbon(P, 25.0, 1.6, nrm, step=3.0))
        k = int(0.78 * len(P))
        hooks.append(ladder_lock(P[k] + nrm[k] * 3.5, nrm[k], t[k]))
    return G.concat(rib), G.concat(hooks)


def pod_camo(sleeve):
    """25 mm camo bar on the pod's outer face, 12 mm in from its aft edge (faces facing -x in that band)."""
    m = trimesh.Trimesh(np.asarray(sleeve.vertices), sleeve.faces, process=False)
    c = m.triangles_center
    fn = m.face_normals
    ya = c[:, 1].max()
    sel = (fn[:, 0] < -0.75) & (c[:, 1] > ya - 34) & (c[:, 1] < ya - 12) & (c[:, 2] > 185) & (c[:, 2] < 580)
    F = m.faces[sel]
    used = np.unique(F)
    remap = -np.ones(len(m.vertices), int)
    remap[used] = np.arange(len(used))
    vn = np.asarray(m.vertex_normals)[used]
    V = m.vertices[used] + vn * 0.7
    uv = np.column_stack([V[:, 1], V[:, 2]]) / 380.0
    return G._mesh(V, remap[F], uv, flip_if_negative=False)


def hinge_bar(S, a_of, yb_of):
    """SH-09: 25 mm camo bar across the hinge band, just under the B-22 tabs' line (z 712)."""
    z = 712.0
    a = a_of(z) - 62
    P0 = np.array([[x, yb_of(z) + 5, z] for x in np.linspace(-a, a, 60)])
    q, n = S.project(P0, 0.9)
    m = G.ribbon(q, 25.0, 0.8, n, step=3.0)
    V = np.asarray(m.vertices)
    m.metadata["uv"] = np.column_stack([V[:, 0], V[:, 2]]) / 380.0
    return m


def tripod_kit(S, tri, a_of, yf_of, yb_of):
    """Foot cup (folded 330D) round the tripod feet and 2 cinch straps (G-hook to the B-01|gusset loop, ladder lock
    at the aft-corner loop) wrapping over the tripod at z 300 and 560."""
    x, y, R = tri["x"], tri["y"], tri["R"]
    cup = G.superellipsoid([x - 2, y, 140], (R + 10, R + 14, 60), e_ns=0.35, e_ew=0.6, nu=40, nv=16)
    rim = G.tube(np.column_stack([x - 2 + (R + 10) * np.cos(np.linspace(0, 2 * np.pi, 49)),
                                  y + (R + 14) * np.sin(np.linspace(0, 2 * np.pi, 49)), np.full(49, 199.0)]), 2.0, n=8)
    straps, hw = [], []
    for z in (300.0, 560.0):
        A, nA = S.on([a_of(z), yf_of(z) + 8, z], 1.6)
        B, nB = S.on([a_of(z), yb_of(z) - 8, z], 1.6)
        A, B = A[0], B[0]
        over = np.array([x + R + 3, y, z])
        pts = np.array([A, 0.5 * (A + over) + [6, 0, 0], over + [0, -R * 0.7, 0], over, over + [0, R * 0.7, 0],
                        0.5 * (B + over) + [6, 0, 0], B])
        P = G.catmull_rom(pts, 8)
        nn = np.tile([1.0, 0, 0], (len(P), 1))
        straps.append(G.ribbon(P, 25.0, 1.6, nn, step=3.0))
        hw.append(g_hook(A + [4, 0, 0], np.array([1.0, 0, 0]), B - A))
        hw.append(ladder_lock(B + [5, 0, 0], np.array([1.0, 0, 0]), B - A))
    # 2 cup tabs to the gusset (the cup hooks to 2 loops in the B-03R | B-05 seam)
    for dy in (-R * 0.8, R * 0.8):
        A = np.array([x - R - 8, y + dy, 175.0])
        B, _ = S.on([a_of(150), y + dy, 150.0], 1.4)
        P = G.catmull_rom(np.array([A, 0.5 * (A + B[0]) + [0, 0, 6], B[0]]), 6)
        straps.append(G.ribbon(P, 25.0, 1.6, np.tile([1.0, 0, 0], (len(P), 1)), step=3.0))
        hw.append(g_hook(B[0] + [3, 0, 0], np.array([1.0, 0, 0]), B[0] - A))
    return cup, rim, G.concat(straps), G.concat(hw)


# ---------------------------------------------------------------- modules
MOD_DIR = OUT / "cloth"
SCALE_D = {"MS": 150.0 / 207.0, "MC": 1.0, "MK": 1.0, "MS_liner": 1.0}   # SWAP slab held to ~150 mm by its contents


def module_mesh(mid):
    d = np.load(MOD_DIR / f"module_{mid}.npz")
    V = d["V"].copy()
    V -= [0.5 * (V[:, 0].max() + V[:, 0].min()), 0.5 * (V[:, 1].max() + V[:, 1].min()), V[:, 2].min()]
    V[:, 1] *= SCALE_D.get(mid, 1.0)
    tm = trimesh.Trimesh(V, d["F"], process=False)
    trimesh.smoothing.filter_taubin(tm, lamb=0.5, nu=-0.53, iterations=4)
    V = np.asarray(tm.vertices)
    uv = np.column_stack([V[:, 0] + V[:, 1], V[:, 2]]) / G.TILE_MM
    return G._mesh(V, d["F"], uv, flip_if_negative=False)


def module_kit(mid, rolled=True, tab="blaze"):
    """Module body + its roll (3 turns, HDPE edge) + roll keeper strap and G-hook + colour tab, in module-local
    coordinates (floor centre at the origin, x = width, y = depth)."""
    m = module_mesh(mid)
    V = np.asarray(m.vertices)
    top = V[:, 2].max()
    w = V[:, 0].max() - V[:, 0].min()
    parts = {"body": m}
    if rolled:
        r = 16.0
        line = np.column_stack([np.linspace(-w / 2 + 14, w / 2 - 14, 30), np.zeros(30), np.full(30, top - 6 + r * 0.4)])
        parts["roll"] = G.tube(line, r, n=28, tile=G.TILE_MM)
        sp = []
        for end, sgn in ((0, -1), (-1, 1)):
            th = np.linspace(0, 6 * np.pi, 120)
            rr = 3 + (r - 4) * th / th[-1]
            c = line[end] + [sgn * 0.6, 0, 0]
            sp.append(G.tube(c + np.column_stack([np.zeros(120), rr * np.cos(th), rr * np.sin(th)]), 0.9, n=5))
        parts["roll_ends"] = G.concat(sp)
        # keeper: from the roll's middle, down the aft face to the hang loop, G-hook
        yb = V[np.abs(V[:, 0]) < 30][:, 1].max()
        kp = np.array([[0, 0, top + r + 6], [0, r + 4, top + 4], [0, yb + 2, top - 40], [0, yb + 2.5, top - 90]])
        P = G.catmull_rom(kp, 8)
        parts["keeper"] = G.ribbon(P, 25.0, 1.6, np.tile([0, 1.0, 0], (len(P), 1)), step=3.0)
        parts["hook"] = g_hook(np.array([0, yb + 5, top - 96]), np.array([0, 1.0, 0]), np.array([0, 0, -1.0]))
        xt = w / 2 - 60
        loc = V[(np.abs(V[:, 0] - xt) < 12) & (V[:, 2] > top - 100) & (V[:, 2] < top - 20)]
        yt = loc[:, 1].max() if len(loc) else yb
        tabp = np.array([[xt, yt - 3, top - 28], [xt, yt + 5, top - 44], [xt, yt + 3, top - 84]])
        parts["tab"] = G.ribbon(G.catmull_rom(tabp, 8), 25.0, 2.0, np.tile([0, 1.0, 0], (17, 1)), step=3.0)
    else:   # zip clamshell (KILL): zip round 3 sides of the aft face
        yb = V[:, 1].max()
        hz = V[:, 2].max()
        path = np.array([[-w / 2 + 18, yb * 0.92, 20], [-w / 2 + 14, yb * 0.95, hz - 18], [w / 2 - 14, yb * 0.95, hz - 18],
                         [w / 2 - 18, yb * 0.92, 20]])
        P = G.catmull_rom(path, 20)
        # snap to the surface
        from scipy.spatial import cKDTree
        tmm = trimesh.Trimesh(V, m.faces, process=False)
        _, j = cKDTree(V).query(P)
        n = np.asarray(tmm.vertex_normals)[j]
        q = V[j]
        q = smooth_line(q, 3.0, 6.0)
        _, j = cKDTree(V).query(q)
        n = np.asarray(tmm.vertex_normals)[j]
        parts["zip"] = G.concat([G.ribbon(q + n * 0.6, 9.0, 1.0, n, step=3.0), G.tube(q + n * 1.4, 1.4, n=6)])
        parts["tab"] = G.concat([_block(q[len(q) // 3] + n[len(q) // 3] * 3, (18, 6, 10), e=0.35),
                                 G.capsule_between(q[len(q) // 3] + n[len(q) // 3] * 6 + [0, 0, -4],
                                                   q[len(q) // 3] + n[len(q) // 3] * 8 + [0, 0, -36], 4.0)])
    return parts


def place(mesh, R=np.eye(3), t=(0, 0, 0)):
    V = np.asarray(mesh.vertices) @ np.asarray(R).T + np.asarray(t)
    return G._mesh(V, mesh.faces, mesh.metadata.get("uv", np.zeros((len(V), 2))), flip_if_negative=False)


def rz(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def rx(deg):
    a = np.radians(deg)
    return np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])


MOD_MAT = {"MS": "mod_sage", "MC": "mod_stone", "MK": "mod_brown", "MS_liner": "mod_sage"}
KIT_MAT = {"body": None, "roll": None, "roll_ends": "trim", "keeper": "webbing", "hook": "aluminium", "tab": "blaze",
           "zip": "hardware"}


def module_parts(mid, R, t, name, variant=None, rolled=True):
    out = []
    for k, m in module_kit(mid, rolled=rolled).items():
        mat = KIT_MAT[k] or MOD_MAT[mid]
        if k == "tab":
            mat = "blaze" if mid == "MK" else "camo"     # camo accent tabs; blaze only on the KILL module
        out.append(Part(f"{name}_{k}", place(m, R, t), mat, "bag", modes=BAGM, variant=variant,
                        label=f"{name} {k}"))
    return out


# ---------------------------------------------------------------- assemble
def build():
    p, pk = base_pack()
    BC, CO = _concept()
    c = CO.make()
    S = Skin(sim_skin())
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    d = {x.name: x for x in pk.parts}
    keep = [x for x in pk.parts if not x.name.startswith(DROP_PREFIX)]
    # trim the shell drape + its lining + seams at the collar cut
    body_cut, V, Fneg, cut = _trim_above(d["corrie_body"].mesh, Z_CUT)
    ring = _ring_at_cut(V, Fneg, cut)
    for x in keep:
        if x.name == "corrie_body":
            x.mesh = body_cut
        elif x.name in ("corrie_lining",):
            x.mesh = _trim_above(x.mesh, Z_CUT)[0]
        elif x.name in ("corrie_seams",):
            x.mesh = _drop_above(x.mesh, Z_CUT + 2)
    col, hem, lock, cords, cm = collar(ring, yf_of(Z_CUT))
    keep += [Part("cache_collar", col, "body", "bag", modes=BAGM, label="Drawcord collar (100D), cinched"),
             Part("cache_collar_hem", hem, "body", "bag", modes=BAGM, label="Drawcord channel D-07"),
             Part("cache_cordlock", lock, "hardware", "bag", modes=BAGM, label="Cord lock + pull"),
             Part("cache_cord", cords, "trim", "bag", modes=BAGM, label="3 mm drawcord")]
    pm, pc, ptrim, pzip, pzhw, pstr, phw, ptab = lid_parts(S, cm, yf_of, a_of, yb_of)
    keep += [Part("cache_lid", pm, "body", "bag", modes=BAGM, label="LID module 2.7 L"),
             Part("cache_lid_top", pc, "body", "bag", modes=BAGM),
             Part("cache_lid_tab", ptab, "camo", "bag", modes=BAGM, label="camo pull tab"),
             Part("cache_lid_seams", ptrim, "trim", "bag", modes=BAGM),
             Part("cache_lid_zip", pzip, "hardware", "bag", modes=BAGM),
             Part("cache_lid_pull", pzhw, "webbing", "bag", modes=BAGM),
             Part("cache_lid_straps", G.concat(pstr), "webbing", "bag", modes=BAGM, label="lid straps"),
             Part("cache_lid_hooks", G.concat(phw), "aluminium", "bag", modes=BAGM)]
    # optics pod tabs
    rib, hooks = pod_tabs(S, d["imp1_sleeve"].mesh, a_of, yf_of, yb_of)
    keep += [Part("cache_pod_tabs", rib, "webbing", "bag", modes=BAGM, label="optics pod G-hook tabs"),
             Part("cache_pod_hooks", hooks, "aluminium", "bag", modes=BAGM)]
    # camo accents: optics pod aft-edge bar (PO-c) and the hinge-band top bar (SH-09)
    keep += [Part("cache_pod_camo", pod_camo(d["imp1_sleeve"].mesh), "camo", "bag", modes=BAGM,
                  label="optics pod camo edge bar PO-c"),
             Part("cache_hinge_camo", hinge_bar(S, a_of, yb_of), "camo", "bag", modes=BAGM,
                  label="hinge-band camo bar SH-09")]
    # tripod kit (tripod drawn in every state)
    from huntkit.viz3d.corrie import _tripod_axis
    tri = _tripod_axis(S, a_of, yf_of, yb_of)
    for x in keep:
        if x.name in ("corrie_tripod", "corrie_tripod_parts"):
            x.variant = None
    cup, rim, tst, thw = tripod_kit(S, tri, a_of, yf_of, yb_of)
    keep += [Part("cache_tripod_cup", cup, "body", "bag", modes=BAGM, label="tripod foot cup"),
             Part("cache_tripod_cup_rim", rim, "trim", "bag", modes=BAGM),
             Part("cache_tripod_straps", tst, "webbing", "bag", modes=BAGM, label="tripod cinch straps"),
             Part("cache_tripod_hw", thw, "aluminium", "bag", modes=BAGM)]
    pk.parts = keep
    geo = {"a_of": a_of, "yf_of": yf_of, "yb_of": yb_of, "S": S, "cm": cm}
    return p, pk, geo


def floor_z(pk, mannequin=False):
    zs = []
    for x in pk.parts:
        if x.group == "mannequin" and not mannequin:
            continue
        if "pack" not in x.modes or (x.torso is not None and abs(x.torso - 19) > 0.01):
            continue
        if x.variant in ("full", "lid"):
            continue
        zs.append(np.asarray(x.mesh.vertices)[:, 2].min())
    return float(min(zs))


def scene_parts(state, pk, geo):
    """Extra module parts per GLB state."""
    zf = floor_z(pk)
    out = []
    if state == "access":
        # CAMP module pulled half out through the open door, resting on the sill / U-surround lip; KILL module inside
        out += module_parts("MC", rx(24), (10, 455, zf + 4), "cache_mc", variant="full")
        out += module_parts("MK", rz(-28), (-230, 520, zf), "cache_mk_floor", variant="full", rolled=False)
    elif state == "modules":
        out += module_parts("MS", rz(-18), (430, 300, zf), "cache_ms", variant="full")
        out += module_parts("MC", rz(-30), (360, 610, zf), "cache_mc", variant="full")
        out += module_parts("MK", rz(-40), (60, 640, zf), "cache_mk", variant="full", rolled=False)
    elif state == "meat":
        # the SWAP slab, emptied, back in at the frame side as the liner; game bags inside; IM1-IM3 over it
        out += module_parts("MS_liner", np.eye(3), (0, 78, 40), "cache_liner", variant="full", rolled=False)
        out += meat_parts(geo)
        out += module_parts("MC", rz(-28), (380, 470, zf), "cache_mc", variant="full")
    return out


def meat_parts(geo):
    """Game-bag lumps in the liner mouth and IM1-IM3 round the liner's aft face (port to port on B-01)."""
    parts = []
    rng = np.random.default_rng(3)
    lumps = []
    for i, (x, z) in enumerate(((-70, 560), (60, 575), (0, 600))):
        lumps.append(G.superellipsoid([x, 120 + rng.uniform(-8, 8), z], (95, 62, 70), e_ns=0.7, e_ew=0.8, nu=36, nv=18))
    parts.append(Part("cache_meat_bags", G.concat(lumps), "game_bag", "bag", modes=BAGM, variant="full",
                      label="boned meat in game bags, in the SWAP liner"))
    lin = np.load(MOD_DIR / "module_MS_liner.npz")["V"]
    yb = lin[:, 1].max() - lin[:, 1].min()
    sts, hw = [], []
    for z in (190.0, 330.0, 520.0):
        yy = 78 + yb / 2 + 4
        xs = 168.0
        pts = np.array([[-117, 22, z], [-xs, 60, z], [-xs + 20, yy - 4, z], [0, yy + 2, z], [xs - 20, yy - 4, z],
                        [xs, 60, z], [117, 22, z]])
        P = G.catmull_rom(pts, 10)
        t = np.gradient(P, axis=0)
        nrm = np.column_stack([t[:, 1], -t[:, 0], np.zeros(len(P))])
        nrm = -_unit(nrm)
        sts.append(G.ribbon(P, 38.0, 1.8, nrm, step=3.0))
        k = int(0.62 * len(P))
        hw.append(_block(P[k] + nrm[k] * 5, (40, 44, 9), e=0.3, R=_frame(nrm[k], t[k])))
    parts.append(Part("cache_im_over", G.concat(sts), "meat_strap", "bag", modes=BAGM, variant="full",
                      label="IM1-IM3 cinched over the liner"))
    parts.append(Part("cache_im_cams", G.concat(hw), "aluminium", "bag", modes=BAGM, variant="full"))
    return parts


def materials(p):
    from huntkit.viz3d.export import PBRMaterial, _hex_factor, build_materials
    from huntkit.viz3d import textures as TX
    mats, info = build_materials(p)
    rip = TX.ripstop_normal(512)
    # module silpoly: ripstop fabric shader (same Cycles branch as the harness shell), three solid tones
    for k, hexc in (("mod_sage", "#a8a07f"), ("mod_stone", "#7c7e77"), ("mod_brown", "#5a4a3a")):
        mats[k] = PBRMaterial(name="harness_shell", baseColorFactor=_hex_factor(hexc), normalTexture=rip,
                              metallicFactor=0.0, roughnessFactor=0.8)
    return mats, info


SHOTS = {
    "D_hero": {"view": {"az": -38, "el": 12, "zoom": 1.0}, "state": {"mannequin": True},
               "caption": "CACHE (team D): 3/4 rear on the display form",
               "sub": "Light shell, drawcord collar under the LID module; optics pod (left) and tripod kit (right) hook on"},
    "D_side": {"view": {"az": -90, "el": 4, "zoom": 1.0}, "state": {"mannequin": True},
               "caption": "CACHE: side profile, wearer's left",
               "sub": "Optics pod on 4 G-hooks (85 mm spotter), no wing; LID straps cinch the collar = top compression"},
    "D_access": {"view": {"az": -24, "el": 14, "zoom": 1.0, "box": [-280, 0, -170, 260, 600, 1000]},
                 "state": {"full": True},
                 "caption": "CACHE: door open, a module slides out",
                 "sub": "Horseshoe #10 door; CAMP module (stone) comes out like a drawer; KILL module (brown) on the floor"},
    "D_modules": {"view": {"az": -14, "el": 22, "zoom": 1.0, "box": [-300, -40, 20, 640, 760, 1000]},
                  "state": {"full": True},
                  "caption": "CACHE: the modules out (best idea: one module, two jobs)",
                  "sub": "SWAP slab (sand, frame zone), CAMP (stone), KILL (brown): silpoly roll-tops, G-hook keepers"},
    "D_meat": {"view": {"az": -18, "el": 22, "zoom": 1.0, "box": [-280, 0, -140, 540, 620, 920]},
               "state": {"full": True},
               "caption": "CACHE: meat mode, the SWAP slab becomes the liner",
               "sub": "SWAP slab emptied, back in at the frame as a wipeable liner; meat in game bags, IM1-IM3 over it; CAMP out"},
}


def export_all():
    from huntkit.viz3d.export import export_glb, manifest
    from huntkit.viz3d.viewer import build_html
    p, pk, geo = build()
    mats, info = materials(p)
    base = list(pk.parts)
    files = {}
    for state in ("closed", "access", "modules", "meat"):
        pk.parts = base + scene_parts(state, pk, geo)
        if state != "closed":     # the door-open scenes drop the fixed IM straps (the meat scene draws its own)
            pk.parts = [x for x in pk.parts if not (state == "meat" and x.name in ("corrie_im_straps", "corrie_im_hooks"))]
        glb, _ = export_glb(pk, OUT / f"cache_{state}.glb", mats=mats)
        m = dict(pk.metrics)
        m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()}
        build_html(glb, manifest(pk), m, info, OUT / f"cache_{state}_viewer.html", title=f"CACHE (team D) {state}")
        files[state] = str(glb)
        print(state, glb, flush=True)
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    return files


if __name__ == "__main__":
    export_all()
