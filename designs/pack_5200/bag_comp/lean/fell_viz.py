"""FELL (Team B LEAN) for the viz3d / Blender Cycles renders, built on FELL's OWN fine cloth-sim drape.

    python designs/pack_5200/bag_comp/lean/fell_clothsim.py 19 --fine --cases packed --tag _fine   # the drape
    python designs/pack_5200/bag_comp/lean/fell_viz.py --model      # GLB + viewer manifest + shots.json
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_fell/fell.glb \\
        --shots outputs/pack3d_fell/shots.json --views fell_hero,fell_side,fell_access,fell_feature,fell_meat \\
        --samples 64 --prefix 20261110_bagB --out outputs/screens

The scene (frame, harness, padded belt B, display form, IMP-6 phone pocket) is CORRIE B.2's
(huntkit/viz3d/corrie_b2.corrie_b2_pack); every bag part of CORRIE is dropped and FELL's parts are placed on the
FELL drape (fell_clothsim.py, packed case, 19 in, h 25 mm) with the same helpers (huntkit.viz3d.corrie: Skin,
patch, strap, roll-top, pouch, wing panel, tripod). huntkit is only imported.

Render-only liberties (stated so nobody reads them as results): skin Taubin-smoothed + subdivided once (as CORRIE);
roll, pods, straps, wraps and the open zip are placed geometry on the drape (not simulated); the spotter is drawn
70 mm out of its sleeve to show it.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from huntkit.viz3d import geom as G  # noqa: E402
from huntkit.viz3d import corrie as VC  # noqa: E402
from huntkit.viz3d.corrie import (WEB, Skin, _block, _frame, _pouch, _rolltop, _tripod, _tripod_axis, _unit,  # noqa: E402
                                  _vnormals, _wing, boundary_chains, g_hook, ladder_lock, patch, seam_chains,
                                  smooth_line, split_by_field, strap, _sub)
from huntkit.viz3d.model import BAGM, Part  # noqa: E402

import fell as F  # noqa: E402

import os
SIM_DIR = Path(os.environ.get("FELL_SIM_DIR", ROOT / "outputs" / "clothsim" / "fell_PR19_fine"))
SCEN = HERE / "scenarios" / "fell_PR19.yaml"
OUT = Path(os.environ.get("FELL_OUT", ROOT / "outputs" / "pack3d_fell"))
BE = (0.0, 260.0, 0.0)
CASE = "packed"


def fell_skin(case=CASE) -> dict:
    xf = SIM_DIR / f"x_{case}.npy"
    key = ROOT / "outputs" / "clothsim" / "cache" / f"fell_skin_{SIM_DIR.name}_{case}_{int(xf.stat().st_mtime)}.pkl"
    if key.exists():
        return pickle.loads(key.read_bytes())
    import fell_clothsim as FC
    FC.install()
    from huntkit.clothsim.pack import PackModel, load_scenario
    pm = PackModel(load_scenario(str(SCEN)), fine="fine" in SIM_DIR.name, verbose=False)
    m = pm.mesh
    x = np.load(xf)
    uv = np.zeros((m.n, 2))
    for p in m.pieces:
        uv[p.gid] = p.xy
    out = {"X": x, "X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    key.parent.mkdir(parents=True, exist_ok=True)
    key.write_bytes(pickle.dumps(out))
    return out


def _env():
    BC = F.BC
    c = F.make()
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    return BC, c, a_of, yf_of, yb_of


def _open_map(P, x0, sx, a_of, yb_of):
    """Zip open: aft-face points near the centre line spread sideways into a lens (half-width up to 105 mm at the
    middle of the run) and the flap edge curls out ~30 mm, fading to zero 70 mm outboard and at both zip ends."""
    zl, zh = F.ZIP["z_lo"], F.ZIP["z_hi"]
    z = x0[:, 2]
    t = np.clip((z - zl) / (zh - zl), 0, 1)
    w = 105.0 * np.sin(np.pi * t) ** 0.55
    aft = np.clip((x0[:, 1] - (np.array([yb_of(v) for v in z]) - 40.0)) / 30.0, 0, 1)
    ax = np.abs(x0[:, 0])
    band = 70.0
    m = (ax < w + band) & (aft > 0) & (t > 0) & (t < 1)
    out = P.copy()
    k = np.clip(1 - ax / (w + band + 1e-9), 0, 1)
    dx = sx * w * k
    out[m, 0] += (dx * aft)[m]
    out[m, 1] += (30.0 * k ** 2 * np.sin(np.pi * t) * aft)[m]
    return out


def fell_parts(pack) -> list:
    BC, c, a_of, yf_of, yb_of = _env()
    sk = fell_skin()
    S = Skin(sk)
    piece = S.piece
    Z0 = BC.Z0
    floor_m = piece == "B-05"
    body_m = ~floor_m
    a0 = a_of(Z0)
    parts = []

    # ---- skin: kick band (V-notch, camo) | body | floor; the body cut again along x = 0 so the zip can open
    def kick_line(x0):
        x, y, z = x0
        if y < yf_of(z) + 4:
            return Z0 - 60.0
        if abs(y - yb_of(z)) < 4 or y > yb_of(z):
            return Z0 + 70.0 - 25.0 * (1 - min(abs(x) / a0, 1.0))
        return Z0 + 70.0
    fk = np.array([z - kick_line(x0) for x0, z in zip(S.x0, S.x0[:, 2])])
    Vk, Ak, Fneg, Fpos, cut = split_by_field(S.V, S.F[body_m], {"uv": S.uv, "x0": S.x0}, fk)
    kick = _sub(Vk, Fneg, Ak["uv"])
    body = _sub(Vk, Fpos, Ak["uv"])
    floor = S.submesh(floor_m)
    lab = "FELL main bag: cloth-sim drape of its own flat pieces (packed, 19 in), ULTRAGrid body"
    parts += [Part("fell_body", body, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled", label=lab),
              Part("fell_kick", kick, "camo", "bag", modes=BAGM, explode=BE, floats=True,
                   label="V-notch kick band SH-01 (owner camo, wear line)"),
              Part("fell_bottom", floor, "tpu", "bag", modes=BAGM, explode=(0, 260, -40), floats=True,
                   label="Bottom B-05 (ULTRA 200X)")]
    fw = VC.float_wraps([Part("corrie_body", body, "body", "bag")])[0]
    fw.name = "fell_float_wraps_g170"
    parts.append(fw)
    # open variant: the body (above the kick band) split at x0 = 0, each half spread by _open_map
    used = np.unique(Fpos)
    rem = -np.ones(len(Vk), int)
    rem[used] = np.arange(len(used))
    Vb, Fb, x0b, uvb = Vk[used], rem[Fpos], Ak["x0"][used], Ak["uv"][used]
    Vs, As, Fl, Fr, _ = split_by_field(Vb, Fb, {"uv": uvb, "x0": x0b}, x0b[:, 0] - 0.5)   # seam nodes go left
    halves = []
    for Fh, sx in ((Fr, 1), (Fl, -1)):
        uh = np.unique(Fh)
        rr = -np.ones(len(Vs), int)
        rr[uh] = np.arange(len(uh))
        Vo = _open_map(Vs[uh], As["x0"][uh], sx, a_of, yb_of)
        halves.append((Vo, rr[Fh], As["uv"][uh], As["x0"][uh]))
    op = G.concat([G._mesh(v, f, u, flip_if_negative=False) for v, f, u, _ in halves])
    parts.append(Part("fell_body_open", op, "body", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                      label="FELL with the centre zip open"))
    lin = []
    rims = []
    for Vo, Fh, uh, xh in halves:
        mm = G._mesh(Vo, Fh, uh, flip_if_negative=False)
        vn = _vnormals(mm)
        cen = Vo.mean(0)
        if np.mean(np.einsum("ij,ij->i", vn, Vo - cen)) < 0:
            vn = -vn
        lin.append(G._mesh(Vo - 1.6 * vn, Fh[:, ::-1], uh, flip_if_negative=False))
        # zip rims: the opened centre edge, z 110-650
        for ch in boundary_chains(Fh, keep=lambda e, xh=xh: abs(xh[e[0], 0]) < 1.0 and abs(xh[e[1], 0]) < 1.0):
            Pc = Vo[ch]
            aftm = xh[ch, 1] > np.array([yb_of(v) for v in xh[ch, 2]]) - 40.0
            Pc = Pc[(xh[ch, 2] > F.ZIP["z_lo"] - 2) & (xh[ch, 2] < F.ZIP["z_hi"] + 2) & aftm]
            Pc = Pc[np.argsort(Pc[:, 2])]
            if len(Pc) > 4:
                Pc = smooth_line(Pc, 3.0, 14.0)
                rims.append(G.ribbon(Pc, 10.0, 1.2, _unit(np.cross(np.gradient(Pc, axis=0), [0, 0, 1.0])), step=3.0))
                rims.append(G.tube(Pc, 2.0, n=8))
    parts += [Part("fell_lining", G.concat(lin), "harness", "bag", modes=BAGM, explode=BE, floats=True, variant="full",
                   label="Inside of the bag (seen through the open zip)"),
              Part("fell_zip_rims", G.concat(rims), "hardware", "bag", modes=BAGM, explode=BE, floats=True,
                   variant="full", label="#10 coil zip halves, open")]
    # IM1-IM3 inside (through the zip)
    ims, imh = [], []
    for zs in (190.0, 330.0, 520.0):
        pts0 = np.array([[x, yf_of(zs) + 2, zs] for x in np.linspace(-120, 120, 25)])
        q, nn = S.on(pts0, -7.0)
        q = smooth_line(q, 4.0, 8.0)
        _, nn = S.project(q)
        ims.append(G.ribbon(q, 38.0, 1.8, -nn, step=4.0))
        for k in (0, -1):
            t = q[1] - q[0] if k == 0 else q[-1] - q[-2]
            imh.append(g_hook(q[k] - nn[k] * 3, -nn[k], t))
    parts += [Part("fell_im_straps", G.concat(ims), "meat_strap", "bag", modes=BAGM, floats=True, variant="full",
                   label="IM1-IM3 internal meat straps (38 mm), reached through the zip"),
              Part("fell_im_hooks", G.concat(imh), "aluminium", "bag", modes=BAGM, floats=True, variant="full")]

    # ---- seams (piping on the sim's own piece boundaries); centre seam: zip z 110-650, plain seam elsewhere
    ch = seam_chains(S.F, piece)
    zkey = frozenset(("B-02R", "B-02L"))
    tubes, ztape, zc = [], [], None
    for key, chains in ch.items():
        for cc in chains:
            if len(cc) <= 3:
                continue
            P = smooth_line(S.V[cc], 4.0, 10.0)
            q, n = S.project(P, 1.2)
            if key == zkey:
                q = q[np.argsort(q[:, 2])]
                zz = S.x0[cc][:, 2]
                lo = q[q[:, 2] < F.ZIP["z_lo"] + 2]
                hi = q[q[:, 2] > F.ZIP["z_hi"] - 2]
                for seg in (lo, hi):
                    if len(seg) > 3:
                        tubes.append(G.tube(seg, 2.1, n=8))
                mid = q[(q[:, 2] >= F.ZIP["z_lo"]) & (q[:, 2] <= F.ZIP["z_hi"])]
                if len(mid) > 4:
                    mid = smooth_line(mid, 3.0, 22.0)
                    zq, zn = S.project(mid, 1.0)
                    ztape += [G.ribbon(zq, 13.0, 1.0, zn, step=3.0), G.tube(zq + zn * 1.0, 1.9, n=8)]
                    zc = (zq, zn)
                continue
            tubes.append(G.tube(q, 2.1, n=8))
    parts += [Part("fell_seams", G.concat(tubes), "trim", "bag", modes=BAGM, explode=BE, floats=True,
                   label="Seams (301 + seared allowance)"),
              Part("fell_zip", G.concat(ztape), "hardware", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                   label="#10 coil centre zip, straight, 540 mm")]
    # slider parked at the top under a camo garage, cord pull
    zq, zn = zc
    i = int(np.argmin(np.abs(zq[:, 2] - (F.ZIP["z_hi"] - 40))))
    t = zq[min(i + 1, len(zq) - 1)] - zq[max(i - 1, 0)]
    sl = _block(zq[i] + zn[i] * 3.5, (24, 13, 6), e=0.35, R=_frame(zn[i], t))
    nn_ = zn[i]
    down = _unit(np.array([0, 0, -1.0]) - np.dot([0, 0, -1.0], nn_) * nn_)
    side = np.cross(nn_, down)
    base = zq[i] + nn_ * 6.0
    loop = np.array([base, base + down * 18 + side * 6 + nn_ * 3, base + down * 40 + nn_ * 5,
                     base + down * 18 - side * 6 + nn_ * 3])
    pull = [G.tube(G.catmull_rom(loop, 8, closed=True), 1.5, n=6),
            G.capsule_between(base + down * 34 + nn_ * 6, base + down * 60 + nn_ * 7, 4.2)]
    j = int(np.argmin(np.abs(zq[:, 2] - (F.ZIP["z_hi"] + 10))))
    gar = patch(S, zq[j], 42, 62, lift=2.6, thick=1.4)
    parts += [Part("fell_zip_slider", sl, "aluminium", "bag", modes=BAGM, explode=BE, floats=True, variant="rolled",
                   label="One #10 slider (parks at the top)"),
              Part("fell_zip_pull", G.concat(pull), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                   variant="rolled"),
              Part("fell_zip_garage", gar, "camo", "bag", modes=BAGM, explode=BE, floats=True,
                   label="Zip garage SH-07 (camo)")]

    # ---- B-22 guy tabs + top guys (hood ears -> tabs)
    tabs = [patch(S, S.on([sx * 149.0, yb_of(695.0), 695.0])[0][0], 34, 46, lift=1.4, thick=1.6) for sx in (1, -1)]
    parts.append(Part("fell_b22", G.concat(tabs), "hypalon", "bag", modes=BAGM, explode=BE, floats=True,
                      label="B-22 guy tabs, z 695"))
    gu = []
    for sx in (1, -1):
        A = np.array([sx * 95.0, 21.7, 702.6 + 6])
        Bp, _ = S.on([sx * 149.0, yb_of(695.0), 695.0], 3.0)
        sd, _ = S.on([sx * a_of(700), 0.5 * (yf_of(700) + yb_of(700)), 705], 4.0)
        pts = np.array([A, A + [sx * 40, 4, 2], sd[0], Bp[0] + [0, -14, 0], Bp[0]])
        rib, _, _ = strap(S, G.catmull_rom(pts, 10), clear=2.5, sigma=14.0)
        gu.append(rib)
    parts.append(Part("fell_top_guys@t19", G.concat(gu), "webbing", "attach", torso=19.0, modes=("pack",),
                      label="Top guys: crown hood ears -> B-22"))

    # ---- roll-top (70D collar, ULTRAGrid hem), roll clips
    roll_line, roll, spiral, rstraps, rhw, clip_paths = _rolltop(S, c, a_of, yf_of, yb_of)
    parts += [Part("fell_roll", roll, "body", "bag", modes=BAGM, explode=BE, floats=True,
                   label="Roll-top closed, 3 turns (70D collar, ULTRAGrid hem)"),
              Part("fell_roll_ends", spiral, "trim", "bag", modes=BAGM, explode=BE, floats=True),
              Part("fell_roll_straps", G.concat(rstraps), "webbing", "bag", modes=BAGM, explode=BE, floats=True),
              Part("fell_roll_buckles", G.concat(rhw), "hardware", "bag", modes=BAGM, explode=BE, floats=True)]
    # ---- A3 lid pod (variant lid: only on when fitted)
    pe = (0, 200, 160)
    pm, pcamo, ptrim, pzip, pzhw, pstr, phw, ptab = _pouch(S, F.CO.POUCH_B2, roll_line, clip_paths, yf_of, pull_tab=True)
    parts += [Part("fell_lidpod", G.concat([pm, pcamo]), "body", "bag", modes=BAGM, explode=pe, floats=True,
                   variant="lid", label="A3 lid pod 2.7 L (add-on)"),
              Part("fell_lidpod_seams", ptrim, "trim", "bag", modes=BAGM, explode=pe, floats=True, variant="lid"),
              Part("fell_lidpod_zip", pzip, "hardware", "bag", modes=BAGM, explode=pe, floats=True, variant="lid"),
              Part("fell_lidpod_pull", pzhw, "webbing", "bag", modes=BAGM, explode=pe, floats=True, variant="lid"),
              Part("fell_lidpod_straps", G.concat(pstr), "webbing", "bag", modes=BAGM, explode=pe, floats=True,
                   variant="lid"),
              Part("fell_lidpod_hooks", G.concat(phw), "aluminium", "bag", modes=BAGM, explode=pe, floats=True,
                   variant="lid")]
    if ptab is not None:
        parts.append(Part("fell_lidpod_tab", ptab, "camo", "bag", modes=BAGM, explode=pe, floats=True, variant="lid"))

    # ---- hard-point loops: 4 frame-corner + 4 aft-corner, z 260 / 490 (25 mm webbing loops proud of the seam)
    loops = []
    for sx in (1, -1):
        for zs in F.HARD_Z:
            for y in (yf_of(zs) + 3.0, yb_of(zs) - 3.0):
                q, n = S.on([sx * a_of(zs), y, zs], 0.0)
                loops.append(patch(S, q[0], 26, 30, lift=1.0, thick=2.6, up=(0, 0, 1)))
    parts.append(Part("fell_hardpoints", G.concat(loops), "webbing", "bag", modes=BAGM, explode=BE, floats=True,
                      label="8 hard-point loops in the corner seams (add-on anchors)"))

    # ---- A1 glass pod (left): panel + camo bar + 2 cinch straps, padded sleeve, 85 mm spotter
    tg = _tripod_axis(S, a_of, yf_of, yb_of, sx=-1, u=0.48, R=55.0)
    tg = dict(tg, z0=165.0, z1=600.0)
    w, hem, bar, st, hw = _wing(S, -1, a_of, yf_of, yb_of, tg, clean=True)
    ex = (-120, 200, 0)
    x, y = tg["x"], tg["y"]
    lift = 70.0
    zb = 172.0 + lift
    sleeve = G.superellipsoid([x, y, 380.0], (53.0, 53.0, 213.0), e_ns=0.08, e_ew=1.0, nu=48, nv=24)
    mouth = G.tube(np.array([[x + 54.0 * np.cos(a), y + 54.0 * np.sin(a), 592.0] for a in np.linspace(0, 2 * np.pi, 61)]),
                   3.2, n=8)
    cl = _block([x - 50.0, y + 30.0, 600.0], (12, 9, 18), e=0.35)
    scope = [G.superellipsoid([x, y, zb + 55], (47.0, 47.0, 55.0), e_ns=0.15, e_ew=1.0, nu=48, nv=16),
             G.capsule_between([x, y, zb + 100], [x, y, zb + 300], 40.0, 37.0),
             G.superellipsoid([x, y, zb + 250], (41.5, 41.5, 30.0), e_ns=0.2, e_ew=1.0, nu=48, nv=12)]
    ep0 = np.array([x, y, zb + 296.0])
    ep1 = ep0 + _unit(np.array([0.0, 0.6, 0.8])) * 92.0
    eye = [G.capsule_between(ep0, ep1, 24.0, 21.0),
           G.capsule_between(ep1 - _unit(ep1 - ep0) * 6, ep1 + _unit(ep1 - ep0) * 18, 23.0)]
    parts += [Part("fell_pod_panel", G.concat([w, hem]), "tpu", "bag", modes=BAGM, explode=ex, floats=True,
                   label="A1 glass pod back panel 200 x 450 (ULTRAGrid), hooks to 4 loops"),
              Part("fell_pod_bar", bar, "camo", "bag", modes=BAGM, explode=ex, floats=True,
                   label="A1 leading-edge bar (owner camo)"),
              Part("fell_pod_straps", G.concat(st), "webbing", "bag", modes=BAGM, explode=ex, floats=True),
              Part("fell_pod_hw", G.concat(hw), "aluminium", "bag", modes=BAGM, explode=ex, floats=True),
              Part("fell_pod_sleeve", sleeve, "body", "bag", modes=BAGM, floats=True,
                   label="A1 padded spotter sleeve (70D over 3 mm XLPE)"),
              Part("fell_pod_mouth", G.concat([mouth]), "trim", "bag", modes=BAGM, floats=True),
              Part("fell_pod_cordlock", cl, "hardware", "bag", modes=BAGM, floats=True),
              Part("fell_scope", G.concat(scope), "fitting", "bag", modes=BAGM, floats=True,
                   label="85 mm spotter (drawn up 70 mm)"),
              Part("fell_scope_eye", G.concat(eye), "hardware", "bag", modes=BAGM, floats=True)]

    # ---- right side: tripod in the A2 strap pair, feet in the cam / tripod cup
    tri = _tripod_axis(S, a_of, yf_of, yb_of)
    tri_m, tri_rub = _tripod(tri)
    parts += [Part("fell_tripod", tri_m, "carbon", "bag", modes=BAGM, floats=True, label="Tripod in the A2 side straps"),
              Part("fell_tripod_parts", tri_rub, "hardware", "bag", modes=BAGM, floats=True)]

    def push_tri(Q, tg=tri, extra=3.5):
        Q = Q.copy()
        Rc = tg["R"] + extra
        dy = Q[:, 1] - tg["y"]
        dx = Q[:, 0] - tg["x"]
        d = np.hypot(dx, dy)
        m = (d < Rc) & (Q[:, 2] > tg["z0"] - 10) & (Q[:, 2] < tg["z1"] + 10)
        Q[m, 0] = tg["x"] + dx[m] / np.maximum(d[m], 1e-6) * Rc
        Q[m, 1] = tg["y"] + dy[m] / np.maximum(d[m], 1e-6) * Rc
        return Q
    a2, a2hw = [], []
    for zs in F.HARD_Z:
        A, nA = S.on([a_of(zs), yf_of(zs) + 3.0, zs], 3.0)
        B, nB = S.on([a_of(zs), yb_of(zs) - 3.0, zs], 3.0)
        over = np.array([tri["x"] + tri["R"] + 4.0, tri["y"], zs])
        pts = np.array([A[0], 0.5 * (A[0] + over) + [6, 0, 0], over, 0.5 * (over + B[0]) + [6, 0, 0], B[0]])
        rib, Pp, nn = strap(S, G.catmull_rom(pts, 10), clear=2.5, sigma=6.0, extra_push=push_tri)
        a2.append(rib)
        t0 = Pp[3] - Pp[0]
        a2hw.append(g_hook(Pp[2] + nn[2] * 3.5, nn[2], t0))
        t1 = Pp[-1] - Pp[-4]
        a2hw.append(ladder_lock(Pp[-6] + nn[-6] * 3.5, nn[-6], t1))
        tail = np.array([Pp[-6] + [0, 0, -k] for k in np.linspace(0, 65, 12)])
        tq, tn = S.project(tail, 2.2)
        a2.append(G.ribbon(tq, WEB, 1.4, tn, step=4.0))
    parts += [Part("fell_side_straps", G.concat(a2), "webbing", "bag", modes=BAGM, floats=True,
                   label="A2 side strap pair (G-hook to the frame-corner loop, ladder lock at the aft-corner loop)"),
              Part("fell_side_hw", G.concat(a2hw), "aluminium", "bag", modes=BAGM, floats=True)]
    # cam / tripod-foot cup (IMP-8 geometry), right foot
    cc = S.on([a_of(95.0), yb_of(95.0) - 40.0, 92.0], 0.0)[0][0]
    parts += [Part("fell_cup", patch(S, cc, 62, 112, lift=1.5, thick=13.0), "body", "bag", modes=BAGM, floats=True,
                   label="Cam / tripod-foot cup"),
              Part("fell_cup_base", patch(S, cc + np.array([0, 0, -50.0]), 66, 24, lift=14.0, thick=2.4), "hypalon",
                   "bag", modes=BAGM, floats=True)]

    # ---- W1 / W2 haul wraps doing their carry-mode job: compression across the aft face (diagonal, as geometry.yaml)
    wr, whw = [], []
    for zR, zL in ((80.0, 250.0), (250.0, 420.0)):
        pts = [np.array([115.0, 10.0, zR])]
        for sx, z in ((1, zR), (-1, zL)):
            pass
        g1 = S.on([a_of(zR + 10), yf_of(zR + 10) + 40, zR + 10], 3.0)[0][0]
        g2 = S.on([a_of(zR + 25), yb_of(zR + 25) - 20, zR + 25], 3.0)[0][0]
        f1 = S.on([0.0, yb_of(0.5 * (zR + zL)), 0.5 * (zR + zL)], 3.0)[0][0]
        h2 = S.on([-a_of(zL - 25), yb_of(zL - 25) - 20, zL - 25], 3.0)[0][0]
        h1 = S.on([-a_of(zL - 10), yf_of(zL - 10) + 40, zL - 10], 3.0)[0][0]
        pts = np.array([[115.0, 14.0, zR], g1, g2, f1, h2, h1, [-115.0, 14.0, zL]])
        rib, Pp, nn = strap(S, G.catmull_rom(pts, 12), clear=2.6, sigma=12.0, extra_push=push_tri)
        wr.append(rib)
        k = int(0.82 * len(Pp))
        whw.append(g_hook(Pp[k] + nn[k] * 3.5, nn[k], Pp[k + 2] - Pp[k - 2]))
        k = int(0.12 * len(Pp))
        whw.append(ladder_lock(Pp[k] + nn[k] * 3.5, nn[k], Pp[k + 2] - Pp[k - 2]))
    parts += [Part("fell_wraps", G.concat(wr), "webbing", "bag", modes=("pack",), floats=True,
                   label="W1 / W2 haul wraps as carry compression (unhook the G-hook to open the zip)"),
              Part("fell_wraps_hw", G.concat(whw), "aluminium", "bag", modes=("pack",), floats=True)]

    # ---- IMP-2 hose port on B-03R at z 700 + hose over the right strap (as CORRIE B.1, on FELL's drape)
    from huntkit.viz3d.corrie_b1 import _at, _strap_runs
    P0, n0 = S.on([a_of(700.0), yf_of(700.0) + 20.0, 700.0], 1.0)
    P0, n0 = P0[0], n0[0]
    port = patch(S, P0, 40, 60, lift=1.4, thick=2.2)
    R = _strap_runs(pack)[1]
    Ptop = R["front"][0]
    pts = [P0 + n0 * 4, P0 + n0 * 10 + [0, -10, 40], np.array([a_of(760) + 10, 40.0, 780.0]),
           np.array([Ptop[0] + 30, Ptop[1] + 60, Ptop[2] + 30])]
    for sgo in np.linspace(10, 250, 14):
        Pq, tq, nq, wq = _at(R, sgo)
        pts.append(Pq + nq * 6.0 + wq * 31.0)
    hose = smooth_line(np.array(pts), 4.0, 10.0)
    Pe, te, ne, we = _at(R, 255.0)
    valve = [G.capsule_between(hose[-1], hose[-1] + te * 34, 6.5, 7.5),
             G.capsule_between(hose[-1] + te * 34, hose[-1] + te * 50, 6.0, 4.0)]
    clips = []
    for sgo in (60.0, 180.0):
        Pq, tq, nq, wq = _at(R, sgo)
        clips.append(_block(Pq + nq * 6.5 + wq * 26.0, (14, 10, 18), e=0.35, R=_frame(nq, tq)))
    parts += [Part("fell_hose_port", port, "hypalon", "bag", modes=BAGM, floats=True, label="Hose port, B-03R z 700"),
              Part("fell_hose@t19", G.concat([G.tube(hose, 4.6, n=12)] + clips), "hardware", "suspension", torso=19.0,
                   modes=("pack",)),
              Part("fell_valve@t19", G.concat(valve), "hypalon", "suspension", torso=19.0, modes=("pack",))]
    # ---- A4 strap pod on the RIGHT strap (snacks / GPS), below the hose clips
    parts += strap_pod(pack, side=1)
    return parts


def strap_pod(pack, side=1) -> list:
    from huntkit.viz3d.corrie_b1 import _strap_runs
    from huntkit.viz3d.corrie import _slab
    runs = _strap_runs(pack)
    Lr = runs[1] if side == 1 else runs[-1]
    w_, h_, g_ = 120.0, 190.0, 34.0
    s1 = float(Lr["s"][-1]) - 4.0
    s0 = s1 - h_
    ssg = np.linspace(s0, s1, 30)
    ww = np.linspace(-w_ / 2, w_ / 2, 16)
    Fr = np.array([[np.interp(v, Lr["s"], Lr["front"][:, k]) for k in range(3)] for v in ssg])
    N_ = _unit(np.array([[np.interp(v, Lr["s"], Lr["n"][:, k]) for k in range(3)] for v in ssg]))
    W_ = _unit(np.array([[np.interp(v, Lr["s"], Lr["w"][:, k]) for k in range(3)] for v in ssg]))
    bu = G.bump(np.linspace(0, 1, len(ww)), 0.25)[:, None] * G.bump(np.linspace(0, 1, len(ssg)), 0.2)[None, :]
    Bot = Fr[None, :, :] + ww[:, None, None] * W_[None, :, :] + N_[None, :, :] * 1.5
    Top = Bot + N_[None, :, :] * (2.0 + g_ * bu)[..., None]
    Uu = (ww[:, None] - ww[0]) * np.ones((1, len(ssg))) / G.TILE_MM
    Vv = np.ones((len(ww), 1)) * (ssg - s0)[None, :] / G.TILE_MM
    face = _slab(Top - N_[None, :, :] * 1.0, Top, Uu, Vv)
    back = _slab(Bot, Bot + N_[None, :, :] * 1.6, Uu, Vv)
    # bellows: the side walls between back and mesh face (70D)
    walls = []
    for i in (0, -1):
        B2 = np.stack([Bot[i], Top[i]], 0)
        walls.append(_slab(B2, B2 + W_[None, :, :] * (1.2 if i == -1 else -1.2), Uu[:2] * 0, Vv[:2]))
    tn, tw, tt = N_[0], W_[0], _unit(Fr[1] - Fr[0])
    bar = G.ribbon(np.array([Fr[0] + tw * u + tn * (3 + g_ * 0.8 * G.bump(np.array([(u + w_ / 2) / w_]), 0.25)[0])
                             for u in np.linspace(-w_ / 2, w_ / 2, 20)]), 12.0, 1.6,
                   np.repeat(tt[None], 20, 0), step=4.0)
    lock = _block(Fr[2] + tw * (w_ / 2 + 5) + tn * 6.0, (10, 16, 9), e=0.35, R=np.column_stack([tw, tt, tn]))
    snack = _block(Fr[0] - tt * 30 + tn * 14.0, (95, 40, 16), e=0.25, R=np.column_stack([tw, tt, tn]))
    return [Part("fell_strappod_back@t19", G.concat([back] + walls), "body", "suspension", torso=19.0, modes=("pack",),
                 label="A4 strap pod back + bellows (70D)"),
            Part("fell_strappod_mesh@t19", face, "spacer", "suspension", torso=19.0, modes=("pack",),
                 label="A4 strap pod stretch-mesh face (snacks / GPS), right strap"),
            Part("fell_strappod_cord@t19", bar, "camo", "suspension", torso=19.0, modes=("pack",),
                 label="camo binding on the pod mouth"),
            Part("fell_strappod_lock@t19", G.concat([lock]), "aluminium", "suspension", torso=19.0, modes=("pack",)),
            Part("fell_strappod_snack@t19", snack, "blaze", "suspension", torso=19.0, modes=("pack",))]


def fell_pack(params):
    from huntkit.viz3d.corrie_b2 import corrie_b2_pack
    pack = corrie_b2_pack(params)
    drop = ("corrie_", "imp1_", "imp2_", "imp4_", "imp8_")
    pack.parts = [p for p in pack.parts if not p.name.startswith(drop)]
    pack.parts += fell_parts(pack)
    # float mode for the Cycles path (it does not apply the viewer's float offset): every floating part gets a
    # pack_haul copy moved aft by the 170 mm B-24 gap; the original stays for carry mode only
    import copy
    extra = []
    for p in pack.parts:
        if getattr(p, "floats", False) and "pack_haul" in p.modes and p.gap is None:
            q = copy.copy(p)
            q.mesh = p.mesh.copy()
            q.mesh.apply_translation([0.0, 170.0, 0.0])
            q.name = p.name + "__float170"
            q.modes = ("pack_haul",)
            q.floats = False
            extra.append(q)
            p.modes = tuple(m for m in p.modes if m != "pack_haul")
    pack.parts += extra
    pack.metrics["bag_type"] = "fell_lean"
    return pack


SHOTS = {
    "fell_hero": {"view": {"az": -38, "el": 12, "zoom": 1.0}, "state": {"mannequin": True, "lid": False},
                  "caption": "FELL (Team B LEAN): 3/4 rear on the display form",
                  "sub": "Roll-top, one straight #10 zip, W1/W2 as compression; glass pod left, tripod strap pair right"},
    "fell_side": {"view": {"az": 90, "el": 4, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
                  "caption": "FELL: side, wearer's right (sheep config, lid pod on)",
                  "sub": "Tripod in the A2 strap pair, feet in the cup; lid pod on the roll; hose port; belt-B bottle holster"},
    "fell_access": {"view": {"az": -14, "el": 10, "zoom": 1.0, "box": [-260, 60, 60, 260, 420, 760]},
                    "state": {"full": True, "lid": False},
                    "caption": "FELL: access, the straight centre zip open",
                    "sub": "540 mm #10 coil zip, z 110-650, IM1-IM3 inside; W1/W2 still hooked across it (unhook 2 G-hooks to clear it)"},
    "fell_feature": {"view": {"az": -62, "el": 14, "zoom": 1.0, "box": [-330, 40, 120, -60, 360, 720]},
                     "state": {"lid": False},
                     "caption": "FELL: the add-on hard points (best idea)",
                     "sub": "8 seam loops take G-hook modules: glass pod with 85 mm spotter here; strap pair, lid and strap pods"},
    "fell_meat": {"view": {"az": 75, "el": 8, "zoom": 1.0}, "state": {"haul": True, "gap": 170.0, "mannequin": True},
                  "caption": "FELL: meat haul, float mode",
                  "sub": "Bag floated 170 mm on the B-24 links, meat on US1/US2 against the frame, W1-W3 round both"},
}


def model():
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = fell_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "fell.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m.get("torsos", {}).items()}
    html = build_html(glb, manifest(pack), m, info, OUT / "fell_viewer.html", title="Pack 5200 FELL (Team B LEAN)")
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    print("GLB", glb, "HTML", html, len(pack.parts), "parts")


if __name__ == "__main__":
    if "--model" in sys.argv:
        model()
