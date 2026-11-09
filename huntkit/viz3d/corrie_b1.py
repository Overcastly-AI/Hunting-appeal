"""CORRIE rev B.1 for the viz3d / Cycles renders (2026-11-09): the CORRIE pack (``corrie.corrie_pack``) with

* hipbelt B (``designs/pack_5200/concepts/hipbelt_concepts.py``) as a padded, curved, cone-cut belt on the
  mannequin's pelvis: lumbar pad, wings with the B height profile (150 / 145 at 45 % / 105 mm at the tip) leaning in by
  the size's cone angle, bound edges, spacer-mesh face, centre plate on the Ti pivot, 50 mm buckle, 2:1 pulls
  (25 mm webbing, D-rings at the tips, heavy ladder locks), stabilizer straps;
* IMP-5 left hipbelt pocket (cut to the wing outline, ``corrie.hip_layout``), IMP-3 1 L bottle holster on the right
  wing behind the crest;
* IMP-1 padded scope sleeve with an 85 mm angled spotter under the left wing (the wing is laid over it);
* IMP-2 hose port in B-03R at z 700 and the drinking hose up and down the right shoulder strap to a bite valve;
* IMP-4 zipped kill-kit pocket on the inside of the (open) door, blaze cord pull;
* IMP-6 phone pocket on the left shoulder strap;
* IMP-8 cam cup at the foot of the right wing.

Visual only: dimensions from ``designs/pack_5200/concepts/corrie.py`` (rev B.1 section); nothing here is a build file.
"""
from __future__ import annotations

import sys

import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from . import geom as G
from .corrie import (BAGM, Part, Skin, _block, _concept, _frame, _slab, _tripod_axis, _unit, _vnormals, _wing,
                     corrie_pack, g_hook, ladder_lock, patch, sim_skin, smooth_line)
from .params import REPO

SUSP = ("pack", "pack_haul")


def _hc():
    sys.path.insert(0, str(REPO / "designs" / "pack_5200" / "concepts"))
    import corrie as CO  # noqa: E402
    import hipbelt_concepts as HC  # noqa: E402
    return CO, HC


# ============================================================================================ pelvis (as model.py)
def pelvis(params: dict):
    """The mannequin's own torso section (model.Body, 19 in torso: the superellipse ring its loft is built from) at the
    hipbelt pivot height. ``ring_pt(s, off, z)``: point at arc length ``s`` from the back centre (s > 0 = wearer's
    right) on the ring offset outward by ``off`` mm at height z."""
    from .model import DEFAULT_PARAMS, IN, Body, deep_merge, load_geometry
    p = deep_merge(DEFAULT_PARAMS, params or {})
    g = load_geometry(p)
    hp = g["frame"]["hard_points"]
    pv = np.array(hp["hipbelt_pivot"], float)
    hz = float(pv[2])
    tb = p["hipbelt"]["thick"]
    bhb = pv[1] - 8.0 - tb
    T0 = p["default_torso_in"] * IN
    b0 = Body(T0, hz, back_hip=bhb)
    b0 = Body(T0, hz, back_hip=bhb + (bhb - float(b0.y_back(hz))))
    BU, BH = b0.bu, b0.bu + b0.dl
    body = Body(19.0 * IN, hz, BU, BH)
    cache = {}

    def ring(off, z):
        key = (round(off, 2), round(z, 1))
        if key not in cache:
            a, b = (float(v) for v in body.ab(z))
            th = np.linspace(np.pi / 2, -np.pi / 2, 1441)
            c_, s_ = np.cos(th), np.sin(th)
            ne = np.where(s_ >= 0, 3.0, 2.4)
            x = (a + off) * np.sign(c_) * np.abs(c_) ** (2 / ne)
            y = float(body.yc(z)) + (b + off) * np.sign(s_) * np.abs(s_) ** (2 / ne)
            P = np.column_stack([x, y, np.full_like(x, z)])
            sk = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            cache[key] = (P, sk)
        return cache[key]

    def ring_pt(s, off=0.0, z=hz):
        P, sk = ring(off, z)
        sa = np.clip(abs(s), 0, sk[-1])
        q = np.array([np.interp(sa, sk, P[:, k]) for k in range(3)])
        q[0] *= 1.0 if s >= 0 else -1.0
        return q
    half = float(ring(0.0, hz)[1][-1])
    return {"ring_pt": ring_pt, "ring": ring, "hz": hz, "pv": pv, "hp": hp, "half_circ": half,
            "circ_in": 2 * half / 25.4, "BU": BU, "BH": BH, "body": body}


def mannequin_apose(params: dict) -> list:
    """The viz3d clay mannequin (model.Body) with the arms in a relaxed A-pose, so the hipbelt is not hidden behind
    the forearms in belt close-ups (visual only)."""
    from .model import DEFAULT_PARAMS, IN, Body, deep_merge
    p = deep_merge(DEFAULT_PARAMS, params or {})
    pl = pelvis(params)
    out = []
    for tin in p["torsos_in"]:
        body = Body(tin * IN, pl["hz"], pl["BU"], pl["BH"])
        T, hz, c7 = body.T, body.hz, body.c7
        # model.Body.meshes() without its arms (same torso loft, neck, head, jaw, legs)
        fs = np.array([r[0] for r in body.RINGS])
        zs = hz + T * np.linspace(fs[0], fs[-1], 48)
        rings = []
        for z in zs:
            a, b = body.ab(z)
            rings.append(G.superellipse_ring(a, b, 3.0, 2.4, M=56, cy=float(body.yc(z)), z=z))
        torso = G.loft(np.array(rings), pole_start=[0, float(body.yc(zs[0])), zs[0] - 16], cap_end=True)
        ycn = float(body.yc(c7)) + 10
        neck = G.capsule_between([0, ycn, c7 - 30], [0, ycn - 8, c7 + 95], 50, 46)
        head = G.superellipsoid([0, ycn - 24, c7 + 185], (76, 96, 112), e_ns=0.9, e_ew=0.95)
        jaw = G.superellipsoid([0, ycn - 52, c7 + 122], (55, 55, 48), e_ns=0.9, e_ew=0.9)
        legs = []
        zh = hz - 0.30 * T
        for sx in (-1, 1):
            h0 = np.array([sx * 88, float(body.yc(zh)) + 5, zh])
            legs.append(G.capsule_between(h0, h0 + np.array([sx * 18, -40, -360]), 92, 66))
        base = G.concat([torso, neck, head, jaw] + legs)
        zs_ = c7 - 0.10 * T - 15
        ycs = float(body.yc(zs_))
        arms = []
        for sx in (-1, 1):
            sh = np.array([sx * 182, ycs + 5, zs_])
            el = sh + np.array([sx * 118, -12, -240])
            wr = el + np.array([sx * 52, -70, -225])
            arms += [G.superellipsoid(sh, (56, 58, 58), e_ns=0.9, e_ew=0.9),
                     G.capsule_between(sh, el, 50, 40), G.capsule_between(el, wr, 40, 31),
                     G.superellipsoid(wr + np.array([sx * 6, -6, -40]), (24, 32, 48), e_ns=0.8, e_ew=0.8)]
        out.append(Part(f"mannequin@t{tin:g}", G.concat([base] + arms), "clay", "mannequin", torso=tin,
                        label=f"Mannequin, {tin:g} in torso (A-pose)"))
    return out


# ============================================================================================ belt B
def belt_b_parts(params: dict, size: str | None = None) -> tuple[list, dict]:
    CO, HC = _hc()
    pl = pelvis(params)
    B = HC.B
    size = size or B.size_for(pl["circ_in"])
    L = float(B.wing_len(size))
    beta = np.radians(B.beta(size))
    lw2 = B.lumbar_w / 2 + 20.0                        # lumbar shell 190 wide (pad 150 + 20 each side)
    half = B.lumbar_w / 2 + L                          # padded half length along the body
    rp, hz = pl["ring_pt"], pl["hz"]
    n = 220
    s_all = np.linspace(-half, half, n)
    C = np.array([rp(s, 1.0) for s in s_all])
    outw = _unit(np.array([rp(s * (1 + 10.0 / pl["half_circ"]), 11.0) - rp(s, 1.0) for s in s_all]))
    sabs = np.abs(s_all)
    frac = np.clip((sabs - B.lumbar_w / 2) / L, 0, 1)
    fh, hh = zip(*B.wing_h)
    h = np.where(sabs <= lw2, 160.0, np.interp(frac, fh, hh))
    h = np.convolve(np.pad(h, 4, mode="edge"), np.ones(9) / 9, mode="valid")
    t = np.interp(sabs, [0, 60, lw2, lw2 + 30, half - 40, half], [30.0, 28.0, 22.0, 19.0, 17.0, 11.0])
    bet = np.interp(sabs, [0, lw2, lw2 + 40, half], [0.0, 0.0, beta, beta])
    upv = _unit(np.cos(bet)[:, None] * np.array([0, 0, 1.0]) - np.sin(bet)[:, None] * outw)
    mid = C + outw * (t / 2)[:, None]
    zc = 0.0                                             # belt centred on the crest datum (pivot height)
    shell = G.sweep(mid, G.rounded_rect(1.0, 1.0, nexp=2.3, n=56), up=upv, scale=np.stack([t, h], -1))
    # check which side the profile x maps to (sweep frame S = up x T)
    _, Sm, _ = G.frames_along(mid, upv)
    sgn = float(np.sign(np.mean(np.einsum("ij,ij->i", Sm, outw))))
    parts = [Part("beltB_shell", shell, "harness", "suspension", modes=SUSP,
                  label=f"Hipbelt B ({size}): cone-cut wings {B.beta(size):.0f} deg, 330D shell")]
    # bound top / bottom edges
    bind = []
    for sgn_u in (1, -1):
        e = mid + upv * (sgn_u * (h / 2 - 1.5))[:, None]
        bind.append(G.tube(smooth_line(e, 4.0, 3.0), 3.0, n=10))
    # tip ends: vertical binding at each tip
    for k in (0, -1):
        e = np.array([mid[k] + upv[k] * v for v in np.linspace(-h[k] / 2, h[k] / 2, 16)])
        bind.append(G.tube(e, 3.0, n=10))
    parts.append(Part("beltB_binding", G.concat(bind), "trim", "suspension", modes=SUSP, label="Bound edges"))
    # spacer-mesh body face, inset 9 mm top / bottom
    face = G.ribbon(C + outw * 0.4, 1.0, 1.4, -outw, step=4.0)
    fpath = C - outw * 0.2
    face = G.sweep(fpath, G.rounded_rect(1.0, 1.0, nexp=6, n=32), up=upv, scale=np.stack([np.full(n, 2.0), h - 18], -1))
    parts.append(Part("beltB_face", face, "spacer", "suspension", modes=SUSP, label="Spacer-mesh face (grip print)"))
    # stitch line: perforated crest-relief zone outline on the outer face (subtle quilting lines every 45 mm)
    q = []
    for s0 in np.arange(lw2 + 30, half - 40, 45.0):
        for sg in (1, -1):
            k = int(np.argmin(np.abs(s_all - sg * s0)))
            e = np.array([mid[k] + Sm[k] * sgn * (t[k] / 2 + 0.3) + upv[k] * v
                          for v in np.linspace(-h[k] / 2 + 12, h[k] / 2 - 12, 10)])
            q.append(G.tube(e, 0.7, n=6))
    parts.append(Part("beltB_quilt", G.concat(q), "trim", "suspension", modes=SUSP))

    def on_face(s, v, lift=0.0):
        """Point on the OUTER face at arc s (mm, signed), v mm up the belt from its centre line, + lift outward."""
        k = np.interp(s, s_all, np.arange(n))
        i0 = int(np.clip(np.floor(k), 0, n - 2))
        f = k - i0
        lerp = lambda A: A[i0] * (1 - f) + A[i0 + 1] * f  # noqa: E731
        o = _unit(lerp(outw))
        u = _unit(lerp(upv))
        P = lerp(C) + o * (lerp(t[:, None])[0] + lift) + u * v
        tg = _unit(lerp(np.gradient(C, axis=0)))
        return P, o, u, tg
    info = {"size": size, "wing_len": L, "beta_deg": B.beta(size), "circ_in": round(pl["circ_in"], 1), "lw2": lw2,
            "half": half, "on_face": on_face, "s_all": s_all, "h": h, "t": t}

    # ---- centre plate + Ti pivot (behind the lumbar)
    pv = pl["pv"]
    back = rp(0.0, 1.0 + 30.0)
    hw = [_block([0, (pv[1] + back[1]) / 2, hz], (96, max(abs(pv[1] - back[1]), 6) + 2, 74), e=0.25)]
    parts.append(Part("beltB_centre_plate", G.concat(hw), "printed_cf", "suspension", modes=SUSP,
                      label="Centre plate PA66-GF30 (fixed wing joint) on the Ti pivot"))
    # ---- front: 50 mm buckle + 2:1 pulls (25 mm webbing, D-ring at each tip, heavy ladder lock each side)
    web, hard, alu = [], [], []
    front = rp(pl["half_circ"] - 0.5, 16.0)
    fb = [rp(sx * (pl["half_circ"] - 30.0), 12.0) for sx in (-1, 1)]
    hard.append(_block(front + [12.0, -3.0, 0.0], (46, 13, 40), e=0.3))               # female
    hard.append(_block(front + [-16.0, -3.0, 0.0], (34, 9, 34), e=0.35))              # male
    hard.append(_block(front + [-1.0, -6.0, 0.0], (10, 8, 22), e=0.4))                # release tabs
    for sx in (-1, 1):
        s_tip = sx * (half - 6)
        Ptip, o, u, tg = on_face(s_tip, 0.0, 2.0)
        # D-ring on the tip
        d = [Ptip + tg * sx * (-4) + u * v + o * (2.0 + 6 * np.sin(np.pi * (v + 16) / 32)) for v in np.linspace(-16, 16, 12)]
        dr = np.vstack([d, [Ptip + tg * sx * (-4) + u * 16 + o * 1.5, Ptip + tg * sx * (-4) - u * 16 + o * 1.5]])
        alu.append(G.tube(G.catmull_rom(np.array(d + [d[0]]), 4), 2.2, n=8))
        # two legs from the tip round the front to the lock, 14 mm above / below the centre line
        lock = rp(sx * (pl["half_circ"] - 62.0), 9.0)
        ss_f = np.linspace(abs(s_tip) + 4, pl["half_circ"] - 70, 30) * sx
        for dz in (12.0, -12.0):
            off = 6.0 + 3.0 * (dz < 0)
            path = np.array([rp(sv, off, hz + dz) for sv in ss_f])
            path = np.vstack([Ptip + u * dz + o * 1.5, path, lock + [0, 0, dz * 0.5]])
            path = smooth_line(path, 4.0, 6.0)
            sp_ = np.linspace(ss_f[0], ss_f[-1], len(path))
            nrm = _unit(np.array([rp(sv, 10.0, hz) - rp(sv, 0.0, hz) for sv in sp_]))
            web.append(G.ribbon(path, 25.0, 1.6, nrm, step=4.0))
        hard.append(ladder_lock(lock + [0, -4.0, 0], np.array([0, -1.0, 0]), np.array([sx * 1.0, 0, 0])))
        # 50 mm tab lock -> buckle
        web.append(G.ribbon(np.array([lock + [0, -2, 0], fb[(sx + 1) // 2] + [0, -2, 0]]), 38.0, 1.8,
                            np.array([[0, -1.0, 0]] * 2), step=4.0))
        # pull tail hanging forward / down
        tail = np.array([lock + [sx * 6, -6, -4], lock + [sx * 16, -16, -28], lock + [sx * 24, -18, -62]])
        web.append(G.ribbon(G.catmull_rom(tail, 8), 25.0, 1.6, np.array([[0, -1.0, 0.2]] * 17), step=4.0))
        # stabilizer: wing top near the root -> frame anchor
        Ps, o2, u2, _ = on_face(sx * (lw2 + 25), 0.0, 0.0)
        top = Ps + u2 * (h[int(np.argmin(np.abs(s_all - sx * (lw2 + 25))))] / 2 - 10)
        anc = np.array(pl["hp"]["hip_stabilizer_anchor_R"], float) * np.array([sx, 1, 1])
        sp = np.array([top, 0.5 * (top + anc) + o2 * 8 + [0, 0, 10], anc + [0, -4, 6]])
        web.append(G.ribbon(G.catmull_rom(sp, 8), 20.0, 1.8, np.array([o2] * 17), step=4.0))
        hard.append(ladder_lock(0.5 * (top + anc) + o2 * 12 + [0, 0, 10], o2, _unit(anc - top)))
    parts.append(Part("beltB_webbing", G.concat(web), "webbing", "suspension", modes=SUSP,
                      label="2:1 pulls (25 mm), 50 mm buckle tabs, stabilizers"))
    parts.append(Part("beltB_hardware", G.concat(hard), "hardware", "suspension", modes=SUSP,
                      label="50 mm side-release + 2 heavy ladder locks (ladder_lock_25mm_heavy)"))
    parts.append(Part("beltB_drings", G.concat(alu), "aluminium", "suspension", modes=SUSP,
                      label="25 mm aluminium D-rings (d_ring_25mm_aluminium)"))
    return parts, info


# ============================================================================================ belt pockets / holster
def belt_pocket_parts(info: dict) -> list:
    CO, HC = _hc()
    hl = CO.hip_layout(info["size"])
    on_face = info["on_face"]
    lw = 75.0                                              # pad half width (wing root at s = 75)
    parts = []
    # ---- IMP-5 left pocket (s < 0), x from the wing root
    x0, x1 = hl["L"]["x"]
    ss = -(lw + np.linspace(x0, x1, 60))
    hp_ = np.array([on_face(s, 0.0)[0] for s in ss])
    fr = [on_face(s, 0.0) for s in ss]
    hgt = np.interp(np.linspace(0, 1, 60), [0, 1], [hl["L"]["face"]["h_root"], hl["L"]["face"]["h_tip"]])
    u01 = np.linspace(0, 1, 60)
    bul = 3.0 + 26.0 * G.bump(u01, 0.35)
    path = np.array([f[0] + f[1] * (bul[i] / 2 - 0.5) for i, f in enumerate(fr)])
    ups = np.array([f[2] for f in fr])
    pk = G.sweep(path, G.rounded_rect(1.0, 1.0, nexp=2.6, n=40), up=ups, scale=np.stack([bul, hgt], -1))
    # zip along the top + slider + cord pull at the front end; gusset seam piping round the face
    ztop = np.array([f[0] + f[1] * (bul[i] * 0.62) + f[2] * (hgt[i] / 2 - 9) for i, f in enumerate(fr)])
    zips = [G.tube(smooth_line(ztop, 3.0, 3.0), 1.9, n=8)]
    pip = []
    for sg in (1, -1):
        e = np.array([f[0] + f[1] * (bul[i] * 0.5) + f[2] * sg * (hgt[i] / 2 - 2) for i, f in enumerate(fr)])
        pip.append(G.tube(smooth_line(e, 3.0, 3.0), 1.6, n=8))
    P_end, o, u, tg = fr[-8]
    sl = ztop[-8] + o * 3.0
    zips.append(_block(sl, (20, 10, 7), e=0.35, R=_frame(o, tg)))
    pull = np.array([sl + o * 2, sl - u * 22 + o * 6, sl - u * 46 + o * 8])
    zips.append(G.tube(G.catmull_rom(pull, 6), 1.5, n=6))
    zips.append(G.capsule_between(sl - u * 40 + o * 8, sl - u * 64 + o * 9, 4.2))
    parts += [Part("beltB_pocket_L", pk, "body", "suspension", modes=SUSP,
                   label=f"IMP-5 hipbelt pocket L, cut to the {info['size']} wing outline ({hl['L']['volume_L']:.2f} L)"),
              Part("beltB_pocket_L_trim", G.concat(pip), "trim", "suspension", modes=SUSP),
              Part("beltB_pocket_L_zip", G.concat(zips), "hardware", "suspension", modes=SUSP, label="#8 coil zip")]
    if hl["R"]:      # XL / XXL only
        pass
    # ---- IMP-3 bottle holster, right wing, behind the crest
    h0, h1 = hl["holster_x"]
    sc = lw + 0.5 * (h0 + h1)
    Pc, o, u, tg = on_face(sc, 0.0, 0.0)
    k = int(np.argmin(np.abs(info["s_all"] - sc)))
    top_v = info["h"][k] / 2
    Hs = CO.HOLSTER
    bw, bh = Hs["back"]
    # back panel: conformal over the wing, then hanging straight below the wing's bottom edge
    sv = np.linspace(sc - bw / 2, sc + bw / 2, 16)
    vv = np.linspace(top_v, top_v - bh, 24)
    Bot = np.zeros((16, 24, 3))
    for i, s in enumerate(sv):
        Pi, oi, ui, _ = on_face(s, 0.0, 1.2)
        kk = int(np.argmin(np.abs(info["s_all"] - s)))
        hb_ = info["h"][kk] / 2
        for j, v in enumerate(vv):
            if v >= -hb_:
                Bot[i, j] = Pi + ui * v
            else:
                Bot[i, j] = Pi + ui * (-hb_) + np.array([0, 0, 1.0]) * (v + hb_) + oi * 0.0
    nrm = _unit(np.cross(np.gradient(Bot, axis=0), np.gradient(Bot, axis=1)))
    if np.mean(np.einsum("ijk,k->ij", nrm, o)) < 0:
        nrm = -nrm
    Uu = np.linspace(0, bw, 16)[:, None] * np.ones((1, 24)) / G.TILE_MM
    Vv = np.ones((16, 1)) * vv[None, :] / G.TILE_MM
    panel = _slab(Bot, Bot + nrm * 2.4, Uu, Vv)
    bd = Hs["bottle_d"] / 2
    axis_base = Bot[8, 12] + nrm[8, 12] * (2.4 + bd + 3.5)
    z_bot = float(Bot[8, -1][2]) + 6.0
    axis_xy = axis_base[:2]
    bottle = G.superellipsoid([axis_xy[0], axis_xy[1], z_bot + 105.0], (bd, bd, 105.0), e_ns=0.12, e_ew=1.0, nu=48, nv=24)
    neck = G.superellipsoid([axis_xy[0], axis_xy[1], z_bot + 214.0], (29.0, 29.0, 12.0), e_ns=0.2, e_ew=1.0, nu=40, nv=12)
    loop = G.tube(np.array([[axis_xy[0] + 16 * np.cos(a), axis_xy[1], z_bot + 228 + 12 * np.sin(a)]
                            for a in np.linspace(0, np.pi, 12)]), 2.6, n=8)
    sleeve = G.superellipsoid([axis_xy[0], axis_xy[1], z_bot + 70.0], (bd + 3.2, bd + 3.2, 74.0), e_ns=0.1, e_ew=1.0,
                              nu=48, nv=24)
    band = G.tube(np.array([[axis_xy[0] + (bd + 3.6) * np.cos(a), axis_xy[1] + (bd + 3.6) * np.sin(a), z_bot + 142]
                            for a in np.linspace(0, 2 * np.pi, 49)]), 3.0, n=8)
    clock = _block([axis_xy[0] + o[0] * (bd + 8), axis_xy[1] + o[1] * (bd + 8), z_bot + 136], (12, 9, 18), e=0.35)
    hooks = [g_hook(Pc + u * (top_v - 18) + o * 4.5, o, u), g_hook(Pc - u * (top_v - 18) + o * 4.5, o, u)]
    parts += [Part("beltB_holster_back", panel, "body", "suspension", modes=SUSP, label="IMP-3 holster back panel"),
              Part("beltB_holster_mesh", sleeve, "spacer", "suspension", modes=SUSP, label="IMP-3 power-mesh holster"),
              Part("beltB_holster_band", G.concat([band]), "trim", "suspension", modes=SUSP),
              Part("beltB_bottle", G.concat([bottle]), "hdpe", "suspension", modes=SUSP, label="1 L bottle"),
              Part("beltB_bottle_cap", G.concat([neck, loop, clock]), "hardware", "suspension", modes=SUSP),
              Part("beltB_holster_hooks", G.concat(hooks), "aluminium", "suspension", modes=SUSP,
                   label="2 G-hooks to tabs on the wing (the lower one is the lower tie)")]
    return parts


# ============================================================================================ bag-side additions
def _strap_runs(pack, torso=19.0):
    """Front runs of the two shoulder straps (mesh of shoulder_straps@t19): centre line top -> bottom, outward
    normals and across-strap vectors, per side."""
    sp = next(p for p in pack.parts if p.name == f"shoulder_straps@t{torso:g}")
    V = np.asarray(sp.mesh.vertices)
    VN = _vnormals(sp.mesh)
    out = {}
    for sx in (-1, 1):
        sel = (V[:, 0] * sx > 60) & (VN[:, 1] < -0.55)          # strap vertices facing forward (outer face)
        Wf, Nf = V[sel], VN[sel]
        zs = np.arange(Wf[:, 2].max() - 8, Wf[:, 2].min() + 8, -8.0)
        cen, fr, nn_ = [], [], []
        for z in zs:
            m = np.abs(Wf[:, 2] - z) < 5
            if m.sum() < 4:
                continue
            fr.append(Wf[m].mean(0))
            nn_.append(Nf[m].mean(0))
            cen.append(Wf[m].mean(0) - _unit(Nf[m].mean(0)) * 5.0)
        from scipy.ndimage import gaussian_filter1d
        cen = gaussian_filter1d(np.array(cen), 1.5, axis=0, mode="nearest")
        fr = gaussian_filter1d(np.array(fr), 1.5, axis=0, mode="nearest")
        tdir = _unit(np.gradient(fr, axis=0))
        nn_ = gaussian_filter1d(np.array(nn_), 1.5, axis=0, mode="nearest")
        nrm = _unit(nn_ - np.einsum("ij,ij->i", nn_, tdir)[:, None] * tdir)
        side = _unit(np.cross(nrm, tdir))
        out[sx] = {"front": fr, "t": tdir, "n": nrm, "w": side,
                   "s": np.r_[0, np.cumsum(np.linalg.norm(np.diff(fr, axis=0), axis=1))]}
    return out


def _at(run, s):
    i = int(np.clip(np.searchsorted(run["s"], s), 1, len(run["s"]) - 1))
    return run["front"][i], run["t"][i], run["n"][i], run["w"][i]


def bag_side_parts(pack, params: dict) -> list:
    CO, HC = _hc()
    BC, CO2 = _concept()
    c = CO2.make()
    S = Skin(sim_skin())
    a_of = lambda z: float(c.a([min(max(z, BC.Z0), c.z_c)])[0])            # noqa: E731
    yf_of = lambda z: float(BC.y_frame([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    yb_of = lambda z: float(c.y_front([min(max(z, BC.Z0), c.z_c)])[0])     # noqa: E731
    parts = []
    # ---- IMP-1: 85 mm spotter in the padded sleeve under the LEFT wing; the wing is re-laid over the sleeve
    tg = _tripod_axis(S, a_of, yf_of, yb_of, sx=-1, u=0.48, R=55.0)
    tg = dict(tg, z0=165.0, z1=600.0)
    w, hem, bar, st, hw = _wing(S, -1, a_of, yf_of, yb_of, tg)
    ex = (-120, 200, 0)
    parts += [Part("corrie_wing_L", G.concat([w, hem]), "tpu", "bag", modes=BAGM, explode=ex, floats=True,
                   label="Left wing M-01L over the IMP-1 scope sleeve"),
              Part("corrie_wing_bar_L", bar, "camo", "bag", modes=BAGM, explode=ex, floats=True),
              Part("corrie_wing_straps_L", G.concat(st), "webbing", "bag", modes=BAGM, explode=ex, floats=True),
              Part("corrie_wing_hw_L", G.concat(hw), "aluminium", "bag", modes=BAGM, explode=ex, floats=True)]
    x, y = tg["x"], tg["y"]
    lift = 70.0                                     # scope drawn up 70 mm out of the sleeve, to show it
    zb = 172.0 + lift
    sleeve = G.superellipsoid([x, y, 380.0], (53.0, 53.0, 213.0), e_ns=0.08, e_ew=1.0, nu=48, nv=24)
    mouth = G.tube(np.array([[x + 54.0 * np.cos(a), y + 54.0 * np.sin(a), 592.0] for a in np.linspace(0, 2 * np.pi, 61)]),
                   3.2, n=8)
    cl = _block([x - 50.0, y + 30.0, 600.0], (12, 9, 18), e=0.35)
    scope = [G.superellipsoid([x, y, zb + 55], (47.0, 47.0, 55.0), e_ns=0.15, e_ew=1.0, nu=48, nv=16),   # objective
             G.capsule_between([x, y, zb + 100], [x, y, zb + 300], 40.0, 37.0),                       # body
             G.superellipsoid([x, y, zb + 250], (41.5, 41.5, 30.0), e_ns=0.2, e_ew=1.0, nu=48, nv=12)]  # focus ring
    ep0 = np.array([x, y, zb + 296.0])
    ep1 = ep0 + _unit(np.array([0.0, 0.6, 0.8])) * 92.0
    eye = [G.capsule_between(ep0, ep1, 24.0, 21.0), G.capsule_between(ep1 - _unit(ep1 - ep0) * 6, ep1 + _unit(ep1 - ep0) * 18,
                                                                       23.0)]
    parts += [Part("imp1_sleeve", sleeve, "body", "bag", modes=BAGM, floats=True,
                   label="IMP-1 padded scope sleeve (330D over 3 mm XLPE), left wing"),
              Part("imp1_sleeve_mouth", G.concat([mouth]), "trim", "bag", modes=BAGM, floats=True),
              Part("imp1_cordlock", cl, "hardware", "bag", modes=BAGM, floats=True),
              Part("imp1_scope_armour", G.concat(scope), "fitting", "bag", modes=BAGM, floats=True,
                   label="85 mm angled spotter (drawn up 70 mm to show it)"),
              Part("imp1_scope_eyepiece", G.concat(eye), "hardware", "bag", modes=BAGM, floats=True)]
    # ---- IMP-2: hose port on B-03R at z 700 and the hose up over the right strap to a bite valve
    P0, n0 = S.on([a_of(700.0), yf_of(700.0) + 20.0, 700.0], 1.0)
    P0, n0 = P0[0], n0[0]
    port = patch(S, P0, 40, 60, lift=1.4, thick=2.2)
    runs = _strap_runs(pack)
    R = runs[1]
    top_i = 0
    Ptop = R["front"][top_i]
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
    parts += [Part("imp2_port", port, "hypalon", "bag", modes=BAGM, floats=True, label="IMP-2 bound hose port, B-03R z 700"),
              Part("imp2_hose@t19", G.concat([G.tube(hose, 4.6, n=12)] + clips), "hardware", "suspension", torso=19.0,
                   modes=("pack",), label="Drinking hose over the right strap"),
              Part("imp2_valve@t19", G.concat(valve), "hypalon", "suspension", torso=19.0, modes=("pack",))]
    # ---- IMP-6: phone pocket on the LEFT strap front, conformal to the strap over its last 175 mm
    Lr = runs[-1]
    sp_ = CO.STRAP_POCKET
    s1 = float(Lr["s"][-1]) - 4.0
    s0 = s1 - sp_["h"]
    ssg = np.linspace(s0, s1, 30)
    ww = np.linspace(-sp_["w"] / 2, sp_["w"] / 2, 14)
    F_ = np.array([[np.interp(v, Lr["s"], Lr["front"][:, k]) for k in range(3)] for v in ssg])
    N_ = _unit(np.array([[np.interp(v, Lr["s"], Lr["n"][:, k]) for k in range(3)] for v in ssg]))
    W_ = _unit(np.array([[np.interp(v, Lr["s"], Lr["w"][:, k]) for k in range(3)] for v in ssg]))
    bu = G.bump(np.linspace(0, 1, len(ww)), 0.3)[:, None] * G.bump(np.linspace(0, 1, len(ssg)), 0.25)[None, :]
    Bot = F_[None, :, :] + ww[:, None, None] * W_[None, :, :] + N_[None, :, :] * 1.2
    Top = Bot + N_[None, :, :] * (1.5 + 9.0 * bu)[..., None]
    Uu = (ww[:, None] - ww[0]) * np.ones((1, len(ssg))) / G.TILE_MM
    Vv = np.ones((len(ww), 1)) * (ssg - s0)[None, :] / G.TILE_MM
    face = _slab(Bot, Top, Uu, Vv)
    BotB = F_[None, :, :] + (ww * 1.06)[:, None, None] * W_[None, :, :] + N_[None, :, :] * 0.6
    back = _slab(BotB, BotB + N_[None, :, :] * 1.6, Uu, Vv)
    tn, tw, tt = N_[0], W_[0], _unit(F_[1] - F_[0])
    topc = F_[0] + tn * 6.0
    phone = _block(topc - tt * 4.0, (74, 18, 8), e=0.15, R=np.column_stack([tw, tt, tn]))
    cord = G.tube(np.array([F_[0] + tn * (2 + 8 * np.cos(a)) + tw * (sp_["w"] / 2) * np.sin(a) for a in
                            np.linspace(-np.pi / 2, np.pi / 2, 15)]), 1.6, n=6)
    lock = _block(F_[2] + tw * (sp_["w"] / 2 + 5) + tn * 5.0, (10, 16, 9), e=0.35, R=np.column_stack([tw, tt, tn]))
    hooks = []          # the 2 G-hook wraps sit behind the strap (not visible from the front)
    parts += [Part("imp6_back@t19", back, "body", "suspension", torso=19.0, modes=("pack",),
                   label="IMP-6 phone pocket back (330D)"),
              Part("imp6_mesh@t19", face, "spacer", "suspension", torso=19.0, modes=("pack",),
                   label="IMP-6 stretch-mesh phone pocket, left strap (160 mm phone)"),
              Part("imp6_phone@t19", G.concat([phone]), "fitting", "suspension", torso=19.0, modes=("pack",)),
              Part("imp6_cord@t19", G.concat([cord]), "trim", "suspension", torso=19.0, modes=("pack",)),
              Part("imp6_hw@t19", G.concat([lock] + hooks), "aluminium", "suspension", torso=19.0, modes=("pack",))]
    # ---- IMP-8: cam cup at the foot of the right wing (aft corner, z 35-150)
    cc = S.on([a_of(95.0), yb_of(95.0) - 40.0, 92.0], 0.0)[0][0]
    cup = patch(S, cc, 62, 112, lift=1.5, thick=13.0)
    base = patch(S, cc + np.array([0, 0, -50.0]), 66, 24, lift=14.0, thick=2.4)
    parts += [Part("imp8_cam_cup", cup, "body", "bag", modes=BAGM, floats=True, label="IMP-8 bow cam cup"),
              Part("imp8_cam_cup_base", base, "hypalon", "bag", modes=BAGM, floats=True)]
    # ---- IMP-4: zipped kill-kit pocket on the inside of the OPEN door (variant full)
    parts += door_pocket_parts(S, CO2)
    return parts


def door_pocket_parts(S, CO2) -> list:
    """Map door-flat (x, s) -> the open door's lining surface (the same per-vertex fold _door_open applies)."""
    from .corrie import _door_open, seam_chains
    door_m = S.piece == "B-02door"
    H = CO2.DOOR
    ch = seam_chains(S.F, S.piece)
    _, lin, _ = _door_open(S, door_m, H, ch)
    used = np.unique(S.F[door_m])
    x0 = S.x0[used]
    s = H["z_hinge"] - x0[:, 2]
    X = np.column_stack([x0[:, 0], s])
    Vl = np.asarray(lin.vertices)
    Nl = _vnormals(lin)
    fV, fN = LinearNDInterpolator(X, Vl), LinearNDInterpolator(X, Nl)
    nV = NearestNDInterpolator(X, Vl)
    D = CO2.DOOR_POCKET
    s0, s1 = H["z_hinge"] - D["z"][1], H["z_hinge"] - D["z"][0]
    nu, nv = 24, 30
    us = np.linspace(-D["w"] / 2, D["w"] / 2, nu + 1)
    vs = np.linspace(s0, s1, nv + 1)
    UU, VV = np.meshgrid(us, vs, indexing="ij")
    q = np.column_stack([UU.ravel(), VV.ravel()])
    P = fV(q)
    bad = ~np.isfinite(P).all(1)
    P[bad] = nV(q[bad])
    Nn = fN(q)
    Nn[~np.isfinite(Nn).all(1)] = np.array([0, 0, 1.0])
    Nn = _unit(Nn)
    P, Nn = P.reshape(nu + 1, nv + 1, 3), Nn.reshape(nu + 1, nv + 1, 3)
    bu = G.bump(np.linspace(0, 1, nu + 1), 0.3)[:, None] * G.bump(np.linspace(0, 1, nv + 1), 0.3)[None, :]
    Bot = P + Nn * 1.0
    Top = P + Nn * (2.0 + 26.0 * bu)[..., None]
    Uu = (UU - UU.min()) / G.TILE_MM
    Vv = (VV - VV.min()) / G.TILE_MM
    pocket = _slab(Bot, Top, Uu, Vv)
    # zip along the edge nearest the hinge (top of the pocket on the closed door), blaze cord pull
    j = 2
    zl = Top[:, j] + Nn[:, j] * 0.8
    zt = [G.tube(smooth_line(zl[2:-2], 3.0, 2.0), 1.5, n=8)]
    sl = zl[nu - 4]
    tdir = _unit(zl[nu - 3] - zl[nu - 5])
    zt.append(_block(sl + Nn[nu - 4, j] * 2.5, (16, 9, 6), e=0.35, R=_frame(Nn[nu - 4, j], tdir)))
    dn = _unit(P[nu - 4, j + 6] - P[nu - 4, j])
    pull = [G.capsule_between(sl + Nn[nu - 4, j] * 5 + dn * 10, sl + Nn[nu - 4, j] * 7 + dn * 38, 4.0)]
    edge = []
    for line in (Top[0], Top[-1], Top[:, -1]):
        edge.append(G.tube(smooth_line(line, 3.0, 2.0), 1.4, n=6))
    return [Part("imp4_door_pocket", pocket, "body", "bag", modes=BAGM, floats=True, variant="full",
                 label="IMP-4 zipped kill-kit / first-aid pocket inside the door (200 x 280, 60 mm bellows)"),
            Part("imp4_zip", G.concat(zt), "hardware", "bag", modes=BAGM, floats=True, variant="full"),
            Part("imp4_pull", G.concat(pull), "blaze", "bag", modes=BAGM, floats=True, variant="full",
                 label="Blaze cord pull (findable with bloody gloves)"),
            Part("imp4_edges", G.concat(edge), "trim", "bag", modes=BAGM, floats=True, variant="full")]


# ============================================================================================ the B.1 pack
BELT_DROP = ("hipbelt", "hipbelt_pockets", "hipbelt_shards", "hipbelt_webbing", "hipbelt_hardware")
WING_L_DROP = ("corrie_wing_L", "corrie_wing_bar_L", "corrie_wing_straps_L", "corrie_wing_hw_L")


def corrie_b1_pack(params: dict, size: str | None = None):
    pack = corrie_pack(params)
    keep = [p for p in pack.parts if p.name not in BELT_DROP and p.name not in WING_L_DROP]
    bparts, info = belt_b_parts(params, size)
    keep = [p for p in keep if not p.name.startswith("mannequin@")] + mannequin_apose(params)
    pack.parts = keep + bparts + belt_pocket_parts(info) + bag_side_parts(pack, params)
    pack.metrics["bag_type"] = "corrie_b1"
    pack.metrics["belt_b"] = {k: v for k, v in info.items() if k in ("size", "wing_len", "beta_deg", "circ_in")}
    return pack
