"""Parametric 3D model of Pack 5200, driven by designs/pack_5200/geometry.yaml.

    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.model import build_pack
    pack = build_pack(load_params("designs/pack_5200/spec.yaml"))
    pack.parts      # list[Part]: named meshes, material key, group, torso tag, modes, explode/haul offsets
    pack.metrics    # volumes (from the meshes), masses, FEA summary, lifter angles

Frame hard points, crown settings, bag/lid/pocket/shelf/wing/hipbelt/harness sizes come from
geometry.yaml (pack-designer). Tube sizes come from frame.yaml (FEA agent) when present, else the
PLACEHOLDERS in params.py. The FEA colour overlay is swept along the huntkit.fea model members, so
what is coloured is exactly what was analysed.

Display modes (``Part.modes``): "pack" (carry), "pack_haul" (bag pulled back, meat bay loaded),
"frame" (frame only), "frame_haul" (frame-only haul with a quarter).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh
from shapely.affinity import scale as sh_scale
from shapely.affinity import translate as sh_translate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from . import geom as G
from .params import CU_IN_TO_L, DEFAULT_PARAMS, deep_merge, load_geometry

IN = 25.4
ALL = ("pack", "pack_haul", "frame", "frame_haul")
BAGM = ("pack", "pack_haul")
HAULM = ("pack_haul", "frame_haul")


@dataclass
class Part:
    name: str
    mesh: trimesh.Trimesh
    material: str
    group: str
    torso: float | None = None
    modes: tuple = ALL
    explode: tuple = (0.0, 0.0, 0.0)     # mm, FCS
    haul: tuple = (0.0, 0.0, 0.0)        # extra offset in pack_haul mode (mm)
    label: str = ""
    colors: np.ndarray | None = None     # optional per-vertex RGBA (FEA overlay)


@dataclass
class PackModel:
    parts: list
    metrics: dict
    params: dict
    geometry: dict
    frame_model: dict | None = None
    extras: dict = field(default_factory=dict)

    def part(self, name):
        return next(p for p in self.parts if p.name == name)


def _u(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _mx(p, side):
    p = np.array(p, float)
    p[0] *= side
    return p


def _block(center, size, R=None, e=0.25):
    return G.superellipsoid(center, np.asarray(size, float) / 2, e_ns=e, e_ew=e, nu=24, nv=12, R=R)


def _basis(d, n):
    """3x3 with columns (side, d, n) for orienting small hardware blocks."""
    d = _u(d)
    n = _u(np.asarray(n, float) - d * np.dot(n, d))
    return np.stack([np.cross(d, n), d, n], 1)


def _ribbon_on(points, normals, width, thick, step=8.0, smooth=True):
    P = np.asarray(points, float)
    if smooth and len(P) > 2:
        P = G.catmull_rom(P, 10)
    Nn = G._interp_rows(np.asarray(normals, float), len(P))
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    return G.ribbon(P, width, thick, Nn, step=step)


# ============================================================================ tube sizes
def _tube_sizes(p):
    t = dict(p["frame_tubes"])
    src = "placeholder (frame.yaml pending)"
    if p.get("frame_yaml"):
        try:
            from huntkit.fea.frames import load_frame_params
            fpp = load_frame_params(p["frame_yaml"])
            for key, prm in (("stay_od", "section"), ("bar_od", "crossbar_section")):
                s = fpp.get(prm)
                d = getattr(s, "dims", None) or {}
                if "od" in d:
                    t[key] = float(d["od"])
                elif "w" in d:
                    t[key] = float(max(d["w"], d["h"]))
            t["crown_leg_od"] = min(t["crown_leg_od"], t["stay_od"] - 3.0)
            src = "frame.yaml"
        except Exception as e:  # noqa: BLE001
            src = f"placeholder (frame.yaml unreadable: {e!r})"
    return t, src


# ============================================================================ body (mannequin)
class Body:
    """Clay mannequin. Lengths scale with torso T (C7 - iliac crest); widths fixed.
    PLACEHOLDER anthropometry (roughly a 50th-percentile adult)."""
    RINGS = [(-0.44, 120, 85), (-0.40, 150, 100), (-0.30, 172, 110), (-0.15, 176, 110), (0.0, 163, 100),
             (0.15, 145, 92), (0.32, 150, 98), (0.50, 166, 110), (0.68, 176, 112), (0.82, 181, 104),
             (0.86, 180, 100), (0.90, 168, 90), (0.925, 135, 76), (0.945, 95, 62), (0.98, 62, 54), (1.03, 55, 50)]

    def __init__(self, T, hip_z, back_upper=-61.0, back_hip=-76.0):
        self.T, self.hz = T, hip_z
        self.c7 = hip_z + T
        self.bu = back_upper
        self.dl = back_hip - back_upper

    def y_back(self, z):
        z = np.asarray(z, float)
        y = self.bu + self.dl * np.exp(-((z - (self.hz + 20)) / 120) ** 2)
        return y + np.clip((self.hz - 40) - z, 0, None) * 0.3

    def ab(self, z):
        f = (np.asarray(z, float) - self.hz) / self.T
        fs, a, b = zip(*self.RINGS)
        return np.interp(f, fs, a), np.interp(f, fs, b)

    def yc(self, z):
        return self.y_back(z) - self.ab(z)[1]

    def front_y(self, x, z, n=2.4):
        a, b = self.ab(z)
        u = np.clip(np.abs(x) / a, 0, 0.999)
        return self.yc(z) - b * (1 - u ** n) ** (1 / n)

    def back_y(self, x, z, n=3.0):
        a, b = self.ab(z)
        u = np.clip(np.abs(x) / a, 0, 0.999)
        return self.yc(z) + b * (1 - u ** n) ** (1 / n)

    def top_z(self, x):
        """Top of the shoulder line at lateral |x| (where the ring half-width equals |x|)."""
        fs, a, _ = zip(*self.RINGS)
        k = int(np.argmax(np.array(fs) >= 0.82))
        fa, aa = np.array(fs[k:]), np.array(a[k:])
        return self.hz + self.T * float(np.interp(-abs(x), -aa, fa))

    def meshes(self):
        T, hz, c7 = self.T, self.hz, self.c7
        fs = np.array([r[0] for r in self.RINGS])
        zs = hz + T * np.linspace(fs[0], fs[-1], 48)
        rings = []
        for z in zs:
            a, b = self.ab(z)
            # superellipse_ring: +y half uses n_front -> that is the BACK here (flatter, 3.0)
            rings.append(G.superellipse_ring(a, b, 3.0, 2.4, M=56, cy=float(self.yc(z)), z=z))
        torso = G.loft(np.array(rings), pole_start=[0, float(self.yc(zs[0])), zs[0] - 16], cap_end=True)
        ycn = float(self.yc(c7)) + 10
        neck = G.capsule_between([0, ycn, c7 - 30], [0, ycn - 8, c7 + 95], 50, 46)
        head = G.superellipsoid([0, ycn - 24, c7 + 185], (76, 96, 112), e_ns=0.9, e_ew=0.95)
        jaw = G.superellipsoid([0, ycn - 52, c7 + 122], (55, 55, 48), e_ns=0.9, e_ew=0.9)
        zs_ = c7 - 0.10 * T - 15
        ycs = float(self.yc(zs_))
        arms = []
        for s in (-1, 1):
            sh = np.array([s * 182, ycs + 5, zs_])
            el = sh + np.array([s * 70, -25, -265])
            wr = el + np.array([s * 6, -150, -190])
            arms += [G.superellipsoid(sh, (56, 58, 58), e_ns=0.9, e_ew=0.9),
                     G.capsule_between(sh, el, 50, 40), G.capsule_between(el, wr, 40, 31)]
        legs = []
        zh = hz - 0.30 * T
        for s in (-1, 1):
            h0 = np.array([s * 88, float(self.yc(zh)) + 5, zh])
            legs.append(G.capsule_between(h0, h0 + np.array([s * 18, -40, -360]), 92, 66))
        return G.concat([torso, neck, head, jaw] + arms + legs)


# ============================================================================ main builder
def build_pack(params: dict | None = None) -> PackModel:
    p = deep_merge(DEFAULT_PARAMS, params or {})
    if p.get("frame_yaml") == "auto":
        p["frame_yaml"] = None
    g = load_geometry(p)
    fr, bag_g = g["frame"], g["bag"]
    hp = fr["hard_points"]
    topo = fr["members_topology"]
    tubes, tube_src = _tube_sizes(p)
    metrics = {"tube_sizes": tubes, "tube_size_source": tube_src, "warnings": []}
    parts: list[Part] = []
    rs = tubes["stay_od"] / 2
    rb = tubes["bar_od"] / 2
    rl = tubes["crown_leg_od"] / 2

    FOOT, ELB, TOP = (np.array(hp[k], float) for k in ("stay_foot_R", "lumbar_elbow_R", "stay_top_crown_socket_R"))
    cr = topo["crown"]
    uy, uz = cr["axis_unit_vector_yz"]
    U = np.array([0.0, uy, uz])

    def y_axis(z):                       # upper-stay / crown axis
        return TOP[1] + (z - TOP[2]) * uy / uz

    def stay_y(z):
        z = np.asarray(z, float)
        return np.where(z <= ELB[2], FOOT[1] + (ELB[1] - FOOT[1]) * z / ELB[2], y_axis(z))

    # ------------------------------------------------------------------ fixed frame
    stays, bars, fits = [], [], []
    for s in (-1, 1):
        f, e, t = _mx(FOOT, s), _mx(ELB, s), _mx(TOP, s)
        stays.append(G.tube(G.resample([f, e], 5.0), rs, n=24, tile=40.0))
        stays.append(G.tube(G.resample([e, t], 5.0), rs, n=24, tile=40.0))
        d1, d2 = _u(f - e), _u(t - e)
        fits.append(G.tube([e + d1 * 34, e], rs + 1.8, n=24, tile=40.0))
        fits.append(G.tube([e, e + d2 * 34], rs + 1.8, n=24, tile=40.0))
        fits.append(G.superellipsoid(e, (rs + 2.6,) * 3, 0.9, 0.9, nu=28, nv=14))
        fits.append(G.tube([t - U * 16, t + U * 2], rs + 1.6, n=24, tile=40.0))           # bushing collar
        up = _u(e - f)
        fits.append(G.capsule_between(f + up * 42, f - up * 6, rs + 2.8, rs + 3.4))         # foot boot
        piv = _mx(hp["shelf_pivot_R"], s)
        fits.append(G.tube([piv - [s * 4, 0, 0], piv + [s * 10, 0, 0]], 6.5, n=20, tile=40.0))
    for key in ("mid_bar", "upper_bar"):
        a, b = np.array(topo[key]["from"], float), np.array(topo[key]["to"], float)
        bars.append(G.tube(G.resample([a, b], 5.0), rb, n=28, tile=40.0))
        for nd in (a, b):
            side = np.sign(nd[0])
            dz = U if nd[2] > ELB[2] else _u(ELB - FOOT)
            fits.append(G.tube([nd - dz * 24, nd + dz * 24], rs + 1.8, n=24, tile=40.0))
            fits.append(G.tube([nd, nd + np.array([-side * 30, 0, 0])], rb + 1.8, n=28, tile=40.0))
    latch = np.array(hp.get("rack_lock_pawl_upper_bar") or hp.get("index_latch_upper_bar")
                     or [0.0, topo["upper_bar"]["from"][1] - 14, topo["upper_bar"]["from"][2]], float)
    fits.append(_block(latch + [0, -4, 0], (44, 20, 36), e=0.3))
    parts.append(Part("frame_stays", G.concat(stays), "carbon", "frame", label="Carbon stays (segmented)"))
    parts.append(Part("frame_bars", G.concat(bars), "carbon", "frame", label="Mid + upper cross-bars"))
    parts.append(Part("frame_fittings", G.concat(fits), "fitting", "frame",
                      label="Bonded elbows, sleeves, foot boots, index latch"))

    # lumbar plate (pm45 shear web) + Ti hipbelt pivot + lower strap anchors
    lp = topo["lumbar_plate"]
    x0, x1 = lp["x_range"]
    z0, z1 = lp["z_range"]
    tpl = p["lumbar_plate_t"]
    poly = Polygon([(x0, z0 + 18), (x0 + 22, z0), (x1 - 22, z0), (x1, z0 + 18), (x1, z1 - 12), (x1 - 16, z1),
                    (x0 + 16, z1), (x0, z1 - 12)])
    holes = [Polygon([(-92, 70), (-36, 70), (-36, 150), (-66, 172)]), Polygon([(92, 70), (36, 70), (36, 150), (66, 172)])]
    poly = poly.difference(unary_union([h.buffer(4, join_style=2) for h in holes]))
    y_pl = float(ELB[1]) - rs - tpl / 2 - 0.4
    parts.append(Part("lumbar_plate", G.plate(poly, [0, y_pl, 0], [1, 0, 0], [0, 0, 1], tpl, tile=40.0), "carbon",
                      "frame", label="Carbon lumbar plate (torsion box)"))
    pv = np.array(hp["hipbelt_pivot"], float)
    ti = [G.tube([[0, y_pl - tpl / 2, pv[2]], [0, pv[1], pv[2]]], 17.0, n=24, tile=40.0),
          G.tube([[0, pv[1] + 2, pv[2]], [0, pv[1] - 5, pv[2]]], 21.0, n=24, tile=40.0)]
    for s in (-1, 1):
        a = _mx(hp["shoulder_strap_lower_anchor_R"], s)
        ti.append(_block(a + [0, 2, 0], (16, 8, 22), e=0.5))
        hs = _mx(hp["hip_stabilizer_anchor_R"], s)
        ti.append(_block(hs + [0, -4, 0], (14, 8, 18), e=0.5))
    parts.append(Part("ti_hardware", G.concat(ti), "titanium", "frame", label="Ti hipbelt pivot + anchors"))

    # ------------------------------------------------------------------ crown per torso
    settings = fr["crown_settings"]

    def crown_for(tin):
        return min(settings, key=lambda c: abs(c["torso_in"] - tin))

    crown_info = {}
    for tin in p["torsos_in"]:
        cs = crown_for(tin)
        tag = f"@t{tin:g}"
        top = cs["crown_top_z"]
        yt = y_axis(top)
        legs, cfit = [], []
        for s in (-1, 1):
            pt = np.array([s * cr["legs_x"][1], yt, top])
            legs.append(G.tube(G.resample([pt - U * cr["leg_length_along_axis"], pt], 6.0), rl, n=28, tile=40.0))
            cfit.append(_block(pt + U * 2, (rl * 2 + 9, rl * 2 + 9, rl * 2 + 12), e=0.35))
            la = _mx(cs["lifter_anchor_R"], s)
            cfit.append(G.superellipsoid(la + [0, -rb - 3, -2], (6, 5, 9), 0.6, 0.6, nu=16, nv=10))
        legs.append(G.tube(G.resample([[-cr["legs_x"][1], yt, top], [cr["legs_x"][1], yt, top]], 5.0), rb, n=28, tile=40.0))
        # centre spine (carries the yoke and the lock rack) and the yoke plate
        sw, st = p["spine_w"], p["spine_t"]
        L = 300.0
        spoly = Polygon([(-sw / 2, 0), (sw / 2, 0), (sw / 2, L - 20), (0, L), (-sw / 2, L - 20)])
        spoly = spoly.difference(unary_union([Point(0, d).buffer(5, quad_segs=8) for d in (14.0, L - 30)]))
        nrm_w = np.array([0, -uz, uy])
        org = np.array([0, yt, top]) + nrm_w * (rb + st / 2 + 0.5)
        spine = G.plate(spoly, org, [1, 0, 0], -U, st, tile=40.0)
        rack_c = org + nrm_w * (st / 2 + 1.5) - U * (L * 0.5)
        cfit.append(G.superellipsoid(rack_c, (7, 1.6, L * 0.38), 0.15, 0.3, nu=16, nv=12,
                                     R=np.stack([[1, 0, 0], nrm_w, U], 1)))
        ya = np.array(cs["yoke_anchor"], float)
        ypoly = Polygon([(-108, -18), (-84, -46), (84, -46), (108, -18), (96, 34), (42, 50), (-42, 50), (-96, 34)])
        yoke_plate = G.plate(ypoly, ya, [1, 0, 0], U, p["yoke_plate_t"], tile=40.0)
        parts.append(Part(f"crown{tag}", G.concat(legs + [spine, yoke_plate]), "carbon", "frame", torso=tin,
                          label=f"Telescoping crown ({tin:g} in setting)"))
        parts.append(Part(f"crown_fittings{tag}", G.concat(cfit), "fitting", "frame", torso=tin))
        # extension posts + orange flag sleeve (haul modes)
        post = []
        ph = ((topo.get("extension_posts_accessory") or fr.get("extension_posts_accessory") or {})
              .get("length_mm", 220.0))
        for s in (-1, 1):
            pt = np.array([s * cr["legs_x"][1], yt, top])
            post.append(G.tube([pt + U * 4, pt + U * ph], tubes["post_od"] / 2, n=24, tile=40.0))
        tb = np.array([0, yt, top]) + U * ph
        post.append(G.tube([tb - [cr["legs_x"][1] + 4, 0, 0], tb + [cr["legs_x"][1] + 4, 0, 0]],
                           tubes["post_od"] / 2, n=24, tile=40.0))
        parts.append(Part(f"extension_posts{tag}", G.concat(post), "carbon", "haul", torso=tin, modes=HAULM,
                          label="Extension posts (tall loads)"))
        flag = G.concat([G.tube([tb - [95, 0, 0], tb + [95, 0, 0]], tubes["post_od"] / 2 + 4, n=24, tile=G.TILE_MM),
                         G.plate(Polygon([(-95, 0), (95, 0), (95, -150), (0, -120), (-95, -150)]),
                                 tb + [0, 0, -tubes["post_od"] / 2], [1, 0, 0], [0, 0, 1], 2.0, tile=G.TILE_MM)])
        parts.append(Part(f"orange_flag{tag}", flag, "blaze", "haul", torso=tin, modes=HAULM, label="Orange flag sleeve"))
        crown_info[tin] = cs

    # ------------------------------------------------------------------ main bag
    W, Hb, D = float(bag_g["width_x"]), float(bag_g["height_z"]), float(bag_g["depth_y"])
    Rb = float(bag_g["bottom_corner_radius"])
    org_b = bag_g["origin_carry_mode"]
    by0, bz0 = float(org_b["y_frame_side_panel"]), float(org_b["z_bottom"])
    by1, bz1 = by0 + D, bz0 + Hb
    re_ = p["bag_edge_radius"]
    pull = float(p["haul_pullback_y"] or bag_g.get("haul_mode_pullback_y_max", 250.0))
    HAUL = (0.0, pull, 0.0)
    bag = G.soft_box(W, Hb, bz0, by0, D, Rb, p["bag_top_radius"], r_edge=re_)
    vol_l = G.volume_mm3(bag) / 1e6
    metrics.update({"bag_volume_l": vol_l, "bag_volume_cu_in": vol_l / CU_IN_TO_L,
                    "target_volume_l": p["target_volume_l"],
                    "volume_error_pct": 100 * (vol_l / p["target_volume_l"] - 1),
                    "design_volume_l": (g.get("volumes") or {}).get("main_bag_L"),
                    "bag_dims_mm": [W, Hb, D]})
    BE = (0.0, 260.0, 0.0)
    parts.append(Part("bag_body", bag, "body", "bag", modes=BAGM, explode=BE, haul=HAUL, label="Main bag"))

    # gusset band: right-side outline from the bottom centre, by arc length
    o_pts, o_nrm = G.outline_xz(W, Hb, bz0, Rb, p["bag_top_radius"], inset=0.0, n_arc=60, n_edge=80)
    i_mid = int(np.argmin(np.abs(o_pts[: len(o_pts) // 4, 0])))
    seq = np.r_[np.arange(i_mid, len(o_pts)), np.arange(0, i_mid)]
    P2, N2 = o_pts[seq], o_nrm[seq]
    sarc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P2, axis=0), axis=1))]
    half = int(np.argmax(P2[:, 1] >= bz1 - 1e-6))
    s_r, P_r, N_r = sarc[: half + 1], P2[: half + 1], N2[: half + 1]
    s_corner0 = W / 2 - Rb                      # bottom edge from the centre to the corner arc

    def band(side, s, y, lift=0.0):
        s = np.asarray(s, float)
        x = np.interp(s, s_r, P_r[:, 0])
        z = np.interp(s, s_r, P_r[:, 1])
        nx = np.interp(s, s_r, N_r[:, 0])
        nz = np.interp(s, s_r, N_r[:, 1])
        n = np.stack([side * nx, np.zeros_like(nx), nz], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        P = np.stack([side * x, np.broadcast_to(y, x.shape), z], -1)
        return P + n * lift, n

    def s_at_z(z):                              # right side wall, above the corner arc
        return s_corner0 + Rb * np.pi / 2 + (np.asarray(z, float) - (bz0 + Rb))

    # bottom (TPU 840D): band over the bottom edge + both corner arcs
    s_end = s_corner0 + Rb * np.pi / 2 + 12
    bottom = []
    for s in (-1, 1):
        poly_b = box(0, by0 + re_, s_end, by1 - re_)
        bottom.append(G.conformal_plate(poly_b, lambda u, v, s=s: band(s, u, v)[0], lambda u, v, s=s: band(s, u, v)[1],
                                        thick=1.0, lift=0.3, max_edge=14))
    parts.append(Part("bag_bottom", G.concat(bottom), "tpu", "bag", modes=BAGM, explode=(0, 260, -40), haul=HAUL,
                      label="Bottom (TPU 840D)"))
    # seam piping (frame-side and outer-face panel edges) + full-length right side zip garage
    pip = []
    for yy, sgn_y in ((by0 + 2.9, -1), (by1 - 2.9, 1)):
        pp, nn = G.outline_xz(W, Hb, bz0, Rb, p["bag_top_radius"], inset=2.9, n_arc=16, n_edge=30)
        ring = np.column_stack([pp[:, 0] + nn[:, 0] * 2.4, np.full(len(pp), yy + sgn_y * 2.4), pp[:, 1] + nn[:, 1] * 2.4])
        pip.append(G.tube(np.vstack([ring, ring[:1]]), 2.6, n=10, tile=G.TILE_MM, caps=False))
    sz = np.linspace(s_at_z(bz0 + Rb + 30), s_at_z(bz1 - 8), 120)
    Pz, Nz = band(1, sz, by0 + 160, lift=1.2)
    pip.append(G.ribbon(Pz, 20.0, 2.6, Nz, step=8))
    parts.append(Part("bag_trim", G.concat(pip), "trim", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="Piping + side zip garage"))

    # ------------------------------------------------------------------ side pockets (bellowed)
    spg = g["side_pockets"]
    swb, swt, sph, bell = spg["face_bottom_w"], spg["face_top_w"], spg["height"], spg["bellows"]
    spz0, spy = spg["position"]["z_bottom"], spg["position"]["y_center"]

    def sp_w(v):
        return swb + (swt - swb) * v

    def sp_thick(s, t):
        return 3.0 + bell * G.bump(s, 0.32) * G.bump(0.05 + 0.9 * t, 0.28) * (1 - 0.22 * t)

    def pocket_off(y, z):
        v = (np.asarray(z, float) - spz0) / sph
        u = (np.asarray(y, float) - spy) / sp_w(np.clip(v, 0, 1)) + 0.5
        inside = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        return np.where(inside, sp_thick(np.clip(u, 0, 1), np.clip(v, 0, 1)), 0.0)

    pockets, pshards = [], []
    sh_t = p["shard_thick"]
    SH04 = Polygon([(0, 0), (175, 0), (175, 120), (60, 200), (0, 160)])
    for s in (-1, 1):
        xs = s * W / 2

        def surf(u, v, xs=xs):
            return np.stack([np.full(np.shape(u), xs), spy + (u - 0.5) * sp_w(v), spz0 + sph * v], -1)

        def nrm(u, v, s=s):
            return np.broadcast_to(np.array([s, 0, 0.0]), np.shape(u) + (3,))
        pockets.append(G.patch_shell(surf, nrm, (0, 1), (0, 1), sp_thick, inset=2.0, nu=40, nv=44))
        uu = np.linspace(0, 1, 40)
        rim = surf(uu, np.ones_like(uu)) + np.array([s, 0, 0]) * (sp_thick(uu, np.ones_like(uu)) + 1)[:, None]
        pockets.append(G.tube(rim, 3.2, n=10, tile=G.TILE_MM))
        clip = Polygon([(spy - swb / 2 + 8, spz0 + 6), (spy + swb / 2 - 8, spz0 + 6),
                        (spy + swt / 2 - 8, spz0 + sph - 10), (spy - swt / 2 + 8, spz0 + sph - 10)])
        sh4 = sh_translate(SH04, spy + swb / 2 - 175 - 8, spz0 + 6).intersection(clip)

        def sh_surf(y, z, s=s, xs=xs):
            v = (z - spz0) / sph
            u = (y - spy) / sp_w(v) + 0.5
            return np.stack([xs + s * sp_thick(u, v), y, z], -1)

        def sh_nrm(y, z, s=s, f=sh_surf):
            h = 0.5
            a = f(y + h, z) - f(y - h, z)
            b = f(y, z + h) - f(y, z - h)
            n = np.cross(a, b)
            n /= np.linalg.norm(n, axis=-1, keepdims=True)
            return n * np.sign(n[..., :1] * s)
        pshards.append(G.conformal_plate(sh4, sh_surf, sh_nrm, thick=sh_t, lift=0.4, max_edge=10))
    parts.append(Part("side_pockets", G.concat(pockets), "pocket", "bag", modes=BAGM, explode=(0, 260, 0), haul=HAUL,
                      label="Bellowed side pockets (2 x 3.99 L)"))
    side_pocket_vol = G.volume_mm3(pockets[0]) / 1e6

    # ------------------------------------------------------------------ camo shards on the bag
    shards = list(pshards)
    face_clip = Polygon(G.outline_xz(W, Hb, bz0, Rb, p["bag_top_radius"], inset=re_ + 1)[0])

    def face_surf(x, z):
        return np.stack([x, np.full(np.shape(x), by1), z], -1)

    def face_n(x, z):
        return np.broadcast_to(np.array([0, 1.0, 0]), np.shape(x) + (3,))
    SH02 = Polygon([(0, 0), (90, 0), (260, 300), (250, 430), (170, 430), (0, 120)])
    sh2 = sh_translate(SH02, -W / 2 + 80, bz1 - 430 - 6).intersection(face_clip)
    shards.append(G.conformal_plate(sh2, face_surf, face_n, thick=sh_t, lift=0.4, max_edge=40))
    SH01 = Polygon([(0, 0), (230, 0), (300, 70), (210, 150), (95, 260), (0, 190)])
    wrap = 120.0
    for s in (-1, 1):
        # outer-face part: px >= wrap -> x = s * (W/2 + wrap - px)
        fpart = SH01.intersection(box(wrap, -1, 400, 400))
        fpart = sh_translate(fpart, -(W / 2 + wrap), bz0)
        fpart = sh_scale(fpart, xfact=-s, yfact=1, origin=(0, 0))
        fpart = fpart.intersection(face_clip)
        if not fpart.is_empty:
            shards.append(G.conformal_plate(fpart, face_surf, face_n, thick=sh_t, lift=0.4, max_edge=20))
        # gusset part: px < wrap -> y = by1 - wrap + px ; arc length from the corner start
        gpart = SH01.intersection(box(-1, -1, wrap - re_ - 1, 400))
        if not gpart.is_empty:
            shards.append(G.conformal_plate(
                gpart, lambda px, pz, s=s: band(s, s_corner0 + pz, by1 - wrap + px, 0)[0],
                lambda px, pz, s=s: band(s, s_corner0 + pz, by1 - wrap + px, 0)[1],
                thick=sh_t, lift=0.4, max_edge=10))
    parts.append(Part("bag_shards", G.concat(shards), "camo", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="Camo shard reinforcements SH-01/02/04"))

    # bow / cam boot (TPU) low on the outer face + Hypalon lash tabs
    def boot_surf(u, v):
        return np.stack([u, np.full(np.shape(u), by1), v], -1)
    boot = G.patch_shell(boot_surf, face_n, (-110, 110), (bz0 + 20, bz0 + 170),
                         lambda s, t: 2 + 12 * G.bump(s, 0.25) * np.clip(t * 1.4, 0, 1) ** 0.5 * G.bump(0.5 + 0.5 * t, 0.2),
                         inset=1.5, nu=30, nv=24)
    tabs = []
    for (tx, tz) in ((-40, 470), (40, 560), (110, 660), (150, 760), (-150, 760), (-150, 470)):
        tabs.append(_block([tx, by1 + 2.0 + sh_t, tz], (26, 4.0, 12), e=0.2))
    parts.append(Part("bag_boot_tabs", G.concat([boot] + tabs), "tpu", "bag", modes=BAGM, explode=(0, 300, 0),
                      haul=HAUL, label="Bow/cam boot + Hypalon lash tabs"))

    # ------------------------------------------------------------------ compression straps (25 mm, 3 per side)
    straps, buckles = [], []
    for zc in p["compression_z"]:
        in_boot = abs(zc - (bz0 + 95)) < 75
        for s in (-1, 1):
            yy = np.linspace(by0 + 14, by1 - re_, 40)
            off = pocket_off(yy, zc) + 2.0
            side_pts = np.column_stack([s * (W / 2 + off), yy, np.full_like(yy, zc)])
            side_n = np.tile([s, 0, 0.0], (len(yy), 1))
            ang = np.linspace(0, np.pi / 2, 6)
            corner = np.column_stack([s * (W / 2 - re_ + (re_ + 2) * np.cos(ang)), by1 - re_ + (re_ + 2) * np.sin(ang),
                                      np.full_like(ang, zc)])
            corner_n = np.column_stack([s * np.cos(ang), np.sin(ang), np.zeros_like(ang)])
            xx = np.linspace(W / 2 - re_, 22, 30)
            face_pts = np.column_stack([s * xx, np.full_like(xx, by1 + 2.0 + sh_t + (13 if in_boot else 0)),
                                        np.full_like(xx, zc)])
            P = np.vstack([side_pts, corner[1:-1], face_pts])
            Nn = np.vstack([side_n, corner_n[1:-1], np.tile([0, 1, 0.0], (len(xx), 1))])
            straps.append(G.ribbon(P, 25.0, 2.4, Nn, step=8))
        yb = by1 + 5.5 + sh_t + (13 if in_boot else 0)
        buckles.append(G.superellipsoid([0, yb, zc], (26, 5, 16), 0.3, 0.3, nu=24, nv=12))
    parts.append(Part("compression_straps", G.concat(straps), "webbing", "bag", modes=BAGM, explode=(0, 300, 0),
                      haul=HAUL, label="Compression straps (3 x 25 mm per side)"))
    parts.append(Part("buckles", G.concat(buckles), "hardware", "bag", modes=BAGM, explode=(0, 300, 0), haul=HAUL))

    # ------------------------------------------------------------------ lid
    lg = g["lid"]
    lw_, ld_ = lg["footprint"]
    lh, lr = lg["height"], lg["corner_radius"]
    lz0, lyc = lg["position"]["z_bottom"], lg["position"]["y_center"]
    ler = p["lid_edge_radius"]
    zs_l, ins = [], []
    for k in range(8):
        ph_ = np.pi / 2 * k / 7
        zs_l.append(lz0 + 10 * (1 - np.cos(ph_)))
        ins.append(10 * (1 - np.sin(ph_)))
    for t in np.linspace(0, 1, 6)[1:-1]:
        zs_l.append(lz0 + 10 + (lh - 10 - ler) * t)
        ins.append(0.0)
    for k in range(10, -1, -1):
        ph_ = np.pi / 2 * k / 10
        zs_l.append(lz0 + lh - ler * (1 - np.cos(ph_)))
        ins.append(ler * (1 - np.sin(ph_)))
    rings = []
    for z, i in zip(zs_l, ins):
        pp, _ = G.outline_xz(lw_, ld_, lyc - ld_ / 2, lr, lr, inset=i, n_arc=12, n_edge=20)
        rings.append(np.column_stack([pp[:, 0], pp[:, 1], np.full(len(pp), z)]))
    lid = G.loft(np.array(rings), cap_start=True, cap_end=True)
    lid_vol = G.volume_mm3(lid) / 1e6
    LE = (0.0, 280.0, 190.0)
    parts.append(Part("lid", lid, "body", "bag", modes=BAGM, explode=LE, haul=HAUL, label="Lid (8.3 L)"))
    top_clip = Polygon(G.outline_xz(lw_, ld_, lyc - ld_ / 2, lr, lr, inset=ler + 2)[0])
    SH03 = Polygon([(0, 0), (150, 0), (300, 90), (300, 200), (120, 200), (0, 90)])
    sh3 = sh_translate(SH03, -150, lyc - 100).intersection(top_clip)
    lid_sh = G.conformal_plate(sh3, lambda x, y: np.stack([x, y, np.full(np.shape(x), lz0 + lh)], -1),
                               lambda x, y: np.broadcast_to(np.array([0, 0, 1.0]), np.shape(x) + (3,)),
                               thick=sh_t, lift=0.3, max_edge=40)
    parts.append(Part("lid_shard", lid_sh, "camo", "bag", modes=BAGM, explode=LE, haul=HAUL, label="Lid shard SH-03"))
    ltrim = []
    pp, nn = G.outline_xz(lw_, ld_, lyc - ld_ / 2, lr, lr, inset=0)
    ring = np.column_stack([pp[:, 0] + nn[:, 0] * 1.5, pp[:, 1] + nn[:, 1] * 1.5, np.full(len(pp), lz0 + 10)])
    ltrim.append(G.tube(np.vstack([ring, ring[:1]]), 2.8, n=10, tile=G.TILE_MM, caps=False))
    zx = np.linspace(-150 + lr, 150 - lr, 30)
    ltrim.append(G.ribbon(np.column_stack([zx, np.full_like(zx, lyc + ld_ / 2 + 1.3), np.full_like(zx, lz0 + 40)]),
                          9.0, 2.6, np.array([0, 1.0, 0]), step=8))
    ltrim.append(_block([95, lyc + ld_ / 2 + 5, lz0 + 30], (8, 5, 26), e=0.4))
    for s in (-1, 1):   # lid straps down to the bag outer face
        zz = np.linspace(lz0 + lh - ler, lz0 - 90, 10)
        ltrim.append(G.ribbon(np.column_stack([np.full_like(zz, s * 95), np.full_like(zz, lyc + ld_ / 2 + 1.4), zz]),
                              20.0, 2.2, np.array([0, 1.0, 0]), step=8))
    parts.append(Part("lid_trim", G.concat(ltrim), "trim", "bag", modes=BAGM, explode=LE, haul=HAUL))

    # ------------------------------------------------------------------ load shelf
    sg = g["load_shelf"]
    sw_, sd_ = sg["floor_w_x"], sg["floor_d_y"]
    shz, shy = sg["z"], sg["y_from"]
    spoly = box(-sw_ / 2, 0, sw_ / 2, sd_).buffer(-14).buffer(14, quad_segs=10)
    shelf = G.plate(spoly, [0, shy, shz + 3], [1, 0, 0], [0, 1, 0], 6.0, tile=G.TILE_MM)
    parts.append(Part("load_shelf", shelf, "tpu", "shelf", explode=(0, 60, -90), label="Load (meat) shelf 270 x 260"))

    # ------------------------------------------------------------------ haul: quarter + straps + load wings
    q = p["quarter"]
    qz0 = shz + 6.5
    qy0 = shy + 6
    qyc = qy0 + q["depth"] / 2
    qrings, qinfo = [], []
    for f in np.linspace(0, 1, 36):
        z = qz0 + q["height"] * f
        taper = 1 - 0.45 * f ** 1.3
        bul = 1 + 0.10 * np.sin(np.pi * min(f * 1.6, 1))
        rr = np.sqrt(max(1 - ((f - 0.5) / 0.5) ** 10, 0.05))
        a = max(q["width"] / 2 * taper * bul * rr, 18)
        b = max(q["depth"] / 2 * (1 - 0.25 * f) * bul * rr, 14)
        cyy = qyc - (q["depth"] / 2 - b)
        qrings.append(G.superellipse_ring(a, b, 2.3, 3.4, M=64, cy=cyy, z=z))
        qinfo.append((z, a, b, cyy))
    quarter = G.loft(np.array(qrings), cap_start=True, cap_end=True)
    qtop = qz0 + q["height"]
    bc = np.array([14, qyc - 20, qtop - 30])
    bone = G.concat([G.capsule_between(bc, bc + [4, 6, 110], 20, 17),
                     G.superellipsoid(bc + [4, 6, 124], (28, 24, 22), 0.8, 0.8)])
    QE = (0.0, 120.0, 0.0)
    parts.append(Part("quarter_proxy", quarter, "game_bag", "haul", modes=HAULM, explode=QE,
                      label="Bone-in elk hindquarter proxy in a game bag"))
    parts.append(Part("quarter_bone", bone, "bone", "haul", modes=HAULM, explode=QE))
    qinfo = np.array(qinfo)

    def q_x(y, z):
        a = np.interp(z, qinfo[:, 0], qinfo[:, 1])
        b = np.interp(z, qinfo[:, 0], qinfo[:, 2])
        c = np.interp(z, qinfo[:, 0], qinfo[:, 3])
        u = np.clip(np.abs(y - c) / b, 0, 0.999)
        n = np.where(y > c, 2.3, 3.4)
        return a * (1 - u ** n) ** (1 / n)

    # shelf straps: aft shelf corners -> shelf_strap_anchor_fixed (mid-bar node), over the quarter sides
    ss = []
    anc = np.array(hp["shelf_strap_anchor_fixed_R"], float)
    for s in (-1, 1):
        a0 = np.array([s * (sw_ / 2 - 18), shy + sd_ - 14, shz + 7])
        a1 = _mx(anc, s)
        pts, nr = [a0], [[s * 0.3, 1, 0.4]]
        for t in np.linspace(0.12, 0.9, 9):
            y = a0[1] + (a1[1] - a0[1]) * t
            z = a0[2] + (a1[2] - a0[2]) * t
            x = max(float(q_x(y, z)) + 2.5, abs(a0[0] + (a1[0] - a0[0]) * t))
            pts.append([s * x, y, z])
            nr.append([s, 0, 0])
        pts.append(a1 + [s * (rb + 2), 0, 0])
        nr.append([s, 0, 0])
        ss.append(_ribbon_on(pts, nr, 38.0, 2.4, smooth=False))
    parts.append(Part("shelf_straps", G.concat(ss), "webbing", "haul", modes=HAULM, explode=QE,
                      label="Shelf straps (38 mm)"))

    # load wings: tapered TPU panels hinged on the stay lash points, wrapping the load
    wg = g["load_wings"]
    wx = q["width"] / 2 + 8
    wz0, wz1 = 40.0, 40.0 + wg["length"]
    wings, wstr_bag, wstr_frame = [], [], []
    for s in (-1, 1):
        def wsurf(u, v, s=s):
            z = wz0 + (wz1 - wz0) * v
            yspan = wg["root_w"] + (wg["tip_w"] - wg["root_w"]) * v
            return np.stack([np.full(np.shape(u), s * wx), -4 + yspan * u, z], -1)

        def wn(u, v, s=s):
            return np.broadcast_to(np.array([s, 0, 0.0]), np.shape(u) + (3,))
        wings.append(G.patch_shell(wsurf, wn, (0, 1), (0, 1),
                                   lambda a, b: 1.5 + 2.5 * G.bump(a, 0.05) * G.bump(b, 0.05), inset=1.5, nu=16, nv=30))
        for zl in (80.0, 250.0, 420.0):
            la = _mx(hp[f"load_wing_lash_z{int(zl)}_R"], s)
            wings.append(G.ribbon(np.array([la + [s * (rs + 1), 0, 0], [s * (wx + 2), la[1] + 6, zl]]), 30.0, 3.0,
                                  np.array([0, -1.0, 0]), step=4))
            v = (zl - wz0) / (wz1 - wz0)
            ytip = -4 + wg["root_w"] + (wg["tip_w"] - wg["root_w"]) * v
            # (a) bag pulled back: along the bag side to the outer face
            yy = np.linspace(ytip - 10, by1 + pull - re_, 40)
            ramp = np.clip((yy - ytip) / (by0 + pull - ytip), 0, 1)
            xo = np.where(yy < by0 + pull, wx + 3 + (W / 2 + 2 - wx - 3) * ramp,
                          W / 2 + pocket_off(yy - pull, zl) + 3.5)
            pts = np.column_stack([s * xo, yy, np.full_like(yy, zl)])
            ang = np.linspace(0, np.pi / 2, 6)[1:-1]
            cor = np.column_stack([s * (W / 2 - re_ + (re_ + 3.5) * np.cos(ang)), by1 + pull - re_ + (re_ + 3.5) * np.sin(ang),
                                   np.full_like(ang, zl)])
            xx = np.linspace(W / 2 - re_, 26, 20)
            face = np.column_stack([s * xx, np.full_like(xx, by1 + pull + 4.5 + sh_t), np.full_like(xx, zl)])
            Pw = np.vstack([pts, cor, face])
            Nw = np.vstack([np.tile([s, 0, 0.0], (len(pts), 1)), np.column_stack([s * np.cos(ang), np.sin(ang), 0 * ang]),
                            np.tile([0, 1, 0.0], (len(xx), 1))])
            wstr_bag.append(G.ribbon(Pw, 38.0, 2.6, Nw, step=8))
            if s > 0:
                wstr_bag.append(_block([0, by1 + pull + 8 + sh_t, zl], (40, 6, 24), e=0.3))
                # (b) frame-only: around the quarter's aft face, wing to wing
                zq = np.clip(zl, qinfo[0, 0] + 5, qinfo[-1, 0] - 5)
                a_ = np.interp(zq, qinfo[:, 0], qinfo[:, 1])
                b_ = np.interp(zq, qinfo[:, 0], qinfo[:, 2])
                c_ = np.interp(zq, qinfo[:, 0], qinfo[:, 3])
                th_ = np.linspace(0.0, np.pi, 50)
                cth, sth = np.cos(th_), np.sin(th_)
                qx = (a_ + 3) * np.sign(cth) * np.abs(cth) ** (2 / 2.3)
                qy = c_ + (b_ + 3) * np.abs(sth) ** (2 / 2.3)
                qp = np.column_stack([qx, qy, np.full_like(qx, zl)])
                qp = qp[qp[:, 1] > ytip - 5]
                Pq = np.vstack([[[wx + 3, ytip - 10, zl]], qp, [[-(wx + 3), ytip - 10, zl]]])
                nq = Pq - np.array([0, c_, zl])
                nq[:, 2] = 0
                wstr_frame.append(_ribbon_on(Pq, nq, 38.0, 2.6, smooth=False))
    parts.append(Part("load_wings", G.concat(wings), "tpu", "haul", modes=HAULM, explode=(0, 40, 0),
                      label="Load wings (TPU 840D, frame-mounted)"))
    parts.append(Part("wing_straps_bag", G.concat(wstr_bag), "webbing", "haul", modes=("pack_haul",),
                      explode=(0, 120, 0), label="Wing straps around meat + bag"))
    parts.append(Part("wing_straps_frame", G.concat(wstr_frame), "webbing", "haul", modes=("frame_haul",),
                      explode=QE, label="Wing straps around the quarter"))

    # ------------------------------------------------------------------ hipbelt (size M) on the Ti pivot
    hb = p["hipbelt"]
    hbg = g["hipbelt"]
    hz = float(pv[2])
    tb_ = hb["thick"]
    body_hip_back = pv[1] - 8.0 - tb_                 # centre plate 8 mm + belt
    T0 = p["default_torso_in"] * IN
    body0 = Body(T0, hz, back_hip=body_hip_back)
    body0 = Body(T0, hz, back_hip=body_hip_back + (body_hip_back - float(body0.y_back(hz))))
    BU, BH = body0.bu, body0.bu + body0.dl
    a_ic, b_ic = (float(v) for v in body0.ab(hz))
    yc_p = float(body0.yc(hz))

    def pelvis_pt(phi, off, z=hz):
        sphi, cphi = np.sin(phi), np.cos(phi)
        x = (a_ic + off) * np.sign(sphi) * np.abs(sphi) ** (2 / 2.6)
        ne = 3.0 if cphi > 0 else 2.4
        y = yc_p + (b_ic + off) * np.sign(cphi) * np.abs(cphi) ** (2 / ne)
        return np.array([x, y, z])

    half_len = hbg["lumbar_centre_w"] / 2 + hbg["wing_length_mm"][hb["size"]]
    phs = np.linspace(0, np.pi, 600)
    pts_ = np.array([pelvis_pt(f, tb_ / 2) for f in phs])
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts_, axis=0), axis=1))]
    end = float(np.interp(half_len, arc, phs))
    phis = np.linspace(-end, end, 180)
    hdeg = np.abs(phis) / end
    h_belt = np.interp(hdeg, [0, 0.25, 0.75, 1.0], [hb["height_center"], hb["height_center"], hb["height_wing"],
                                                     hb["height_tip"]])
    th_belt = np.interp(hdeg, [0, 0.6, 1.0], [tb_, tb_ * 0.85, tb_ * 0.65])
    path = np.array([pelvis_pt(f, t / 2 + 1.0) for f, t in zip(phis, th_belt)])
    outw = np.array([pelvis_pt(f, 10) - pelvis_pt(f, 0) for f in phis])
    outw /= np.linalg.norm(outw, axis=1, keepdims=True)
    upv = np.array([0, 0, 1.0]) - outw * (np.abs(np.sin(phis))[:, None] * 0.2)
    upv /= np.linalg.norm(upv, axis=1, keepdims=True)
    belt = G.sweep(path, G.rounded_rect(1.0, 1.0, nexp=3.2, n=36), up=upv, scale=np.stack([th_belt, h_belt], -1))
    HBE = (0.0, -230.0, -110.0)
    _, Sm, _ = G.frames_along(path, upv)
    sgn = np.sign(np.dot(Sm[len(path) * 3 // 4], outw[len(path) * 3 // 4]))
    arc_b = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    hpk = []
    for side in (-1, 1):
        if side > 0:
            lo, hi = arc_b[-1] - 140 - 185, arc_b[-1] - 140 + 5
        else:
            lo, hi = 140 - 5, 140 + 185
        sel = (arc_b >= lo) & (arc_b <= hi)
        n = int(sel.sum())
        sp_ = np.linspace(0, 1, n)
        bul = 3 + 30 * G.bump(sp_, 0.35)
        hpk.append(G.sweep(path[sel], G.rounded_rect(1.0, 1.0, nexp=3.0, n=36), up=upv[sel],
                           scale=np.stack([bul, np.full(n, 92.0)], -1),
                           offset=np.stack([sgn * (th_belt[sel] / 2 + bul / 2 - 1.5), np.full(n, -3.0)], -1)))
    parts.append(Part("hipbelt", belt, "harness", "suspension", explode=HBE, label="Hipbelt (M) on Ti pivot"))
    parts.append(Part("hipbelt_pockets", G.concat(hpk), "body", "suspension", explode=HBE,
                      label="Hipbelt pockets (2 x 0.97 L)"))

    # SH-05 wing-tip shards: px along the belt toward the tip, pz up the belt face
    SH05 = Polygon([(0, 0), (110, 0), (140, 45), (110, 95), (0, 95), (25, 45)])

    def _along(a, arr):
        return np.stack([np.interp(a, arc_b, arr[:, k]) for k in range(arr.shape[1])], -1)
    sh5 = []
    for side in (-1, 1):
        def a_of(px, side=side):
            a = arc_b[-1] - 140 + px if side > 0 else 140 - px
            return np.clip(a, 0, arc_b[-1])

        def bsurf(px, pz, a_of=a_of):
            a = a_of(px)
            hh = np.interp(a, arc_b, h_belt)
            zz = np.clip(pz - 47.5, -hh / 2 + 2, hh / 2 - 2)
            return (_along(a, path) + _along(a, Sm) * sgn * (np.interp(a, arc_b, th_belt) / 2)[..., None]
                    + _along(a, upv) * zz[..., None])

        def bn(px, pz, a_of=a_of):
            return _along(a_of(px), Sm) * sgn
        sh5.append(G.conformal_plate(SH05.buffer(-1.5, join_style=2), bsurf, bn, thick=sh_t, lift=0.4, max_edge=8))
    parts.append(Part("hipbelt_shards", G.concat(sh5), "camo", "suspension", explode=HBE,
                      label="Wing-tip shards SH-05"))

    # centre plate (PA66-GF30) on the pivot, front 50 mm webbing + buckle, stabilizers
    belt_back = yc_p + b_ic + tb_
    hw = [_block([0, (pv[1] + belt_back) / 2, hz], (90, abs(pv[1] - belt_back) + 4, 70), e=0.3)]
    eL, eR = path[0], path[-1]
    fy = yc_p - b_ic - 18
    web = np.array([eL, [eL[0] * 0.55, fy + 14, hz], [0, fy, hz], [eR[0] * 0.55, fy + 14, hz], eR])
    wn_ = np.array([[-1, -0.3, 0], [-0.4, -1, 0], [0, -1, 0], [0.4, -1, 0], [1, -0.3, 0]], float)
    hw_web = [_ribbon_on(web, wn_, 50.0, 2.6)]
    hw.append(G.superellipsoid([0, fy - 6, hz], (32, 8, 26), 0.3, 0.3, nu=24, nv=12))
    for s in (-1, 1):
        k = int(len(path) * (0.5 + s * 0.17))
        top_p = path[k] + upv[k] * (h_belt[k] / 2 - 15) + outw[k] * (th_belt[k] / 2 + 2)
        anc_s = _mx(hp["hip_stabilizer_anchor_R"], s) + [s * 4, -6, 0]
        mid = (top_p + anc_s) / 2 + outw[k] * 10
        hw_web.append(_ribbon_on([top_p, mid, anc_s], [outw[k], outw[k], [s, -0.3, 0]], 20.0, 2.2))
    parts.append(Part("hipbelt_webbing", G.concat(hw_web), "webbing", "suspension", explode=HBE))
    parts.append(Part("hipbelt_hardware", G.concat(hw), "hardware", "suspension", explode=HBE))

    # back panel: spacer-mesh pillow between the fixed stays and the upper back (below the lowest yoke)
    zp0 = hz + hb["height_center"] / 2 + 12
    zp1 = min(c["yoke_anchor"][2] for c in settings) - 60
    xw = TOP[0] - rs - 3

    def bp_surf(u, v):
        return np.stack([u, stay_y(v) - rs - 1.5, v], -1)

    def bp_n(u, v):
        return np.broadcast_to(np.array([0, -1.0, 0]), np.shape(u) + (3,))

    def bp_thick(s_, t_):
        z = zp0 + (zp1 - zp0) * t_
        gap = (stay_y(z) - rs - 1.5) - body0.y_back(z)
        return np.clip(gap - 1.0, 4, None) * (0.3 + 0.7 * G.bump(s_, 0.25) * G.bump(t_, 0.2))
    pad = G.patch_shell(bp_surf, bp_n, (-xw, xw), (zp0, zp1), bp_thick, inset=2.0, nu=30, nv=30)
    parts.append(Part("back_panel", pad, "spacer", "suspension", explode=(0, -120.0, 0), label="Back panel (spacer mesh)"))

    # ------------------------------------------------------------------ harness + mannequin per torso
    hg = g["harness"]
    th = p["harness"]["thick"]
    torso_info = {}
    for tin in p["torsos_in"]:
        cs = crown_info[tin]
        T = tin * IN
        body = Body(T, hz, BU, BH)
        c7 = body.c7
        tag = f"@t{tin:g}"
        ya = np.array(cs["yoke_anchor"], float)
        yb = float(body.y_back(ya[2]))
        yf = ya[1] - p["yoke_plate_t"] / 2
        yoke = G.superellipsoid([0, (yb + yf) / 2, ya[2]], (112, max((yf - yb) / 2, 6), 54), 0.35, 0.35, nu=40, nv=16)
        HE = (0.0, -300.0, 60.0)
        straps, webs, lifters, hwr = [], [], [], []
        lifter_angles = []
        for s in (-1, 1):
            la = _mx(cs["lifter_anchor_R"], s)
            y_lift = la[1] - 140.0                   # DESIGN 5.1: lifter point 140 mm forward of the anchor
            pts, nrm = [], []
            pts.append([s * 46, (yb + yf) / 2 - 2, ya[2] - 10]); nrm.append([0, 1, 0])
            z_mid = ya[2] + 0.5 * (c7 - 40 - ya[2])
            pts.append([s * 62, float(body.back_y(62, z_mid)) + th / 2 + 1, z_mid]); nrm.append([0, 1, 0.1])
            ztop = body.top_z(92)
            yb_t = float(body.back_y(88, ztop - 30))
            yf_t = float(body.front_y(92, ztop - 45))
            pts.append([s * 80, yb_t + th / 2, ztop - 30]); nrm.append([0, 0.8, 0.6])
            for f in np.linspace(0.2, 0.8, 5):
                y = yb_t + (yf_t - yb_t) * f
                z = ztop + th / 2 + 1 - 90 * max(f - 0.3, 0) ** 2
                pts.append([s * (88 + 6 * f), y, z])
                nrm.append([0, 0.5 * np.cos(np.pi * f), 1])
            for x, dz in ((97, 95), (104, 150), (116, 215), (134, 280), (150, 330)):
                z = c7 - dz * T / 483
                pts.append([s * x, float(body.front_y(x, z)) - th / 2 - 1, z])
                nrm.append([0.15 * s, -1, 0])
            P = G.catmull_rom(np.array(pts), 12)
            arcp = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            Nn = G._interp_rows(np.array(nrm, float), len(P))
            Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
            keep = arcp <= hg["padded_length"]
            P, Nn, arcp = P[keep], Nn[keep], arcp[keep]
            tt = arcp / arcp[-1]
            w = np.interp(tt, [0, 0.12, 1], [hg["width_top"] * 0.85, hg["width_top"], hg["width_bottom"]])
            tk = np.interp(tt, [0, 0.08, 0.85, 1], [th * 0.6, th, th, th * 0.6])
            straps.append(G.sweep(P, G.rounded_rect(1.0, 1.0, nexp=3.0, n=32), up=Nn, scale=np.stack([w, tk], -1)))
            # lower webbing: strap end -> around the ribcage -> lower anchor on the lumbar plate
            e_ = P[-1]
            anc = _mx(hp["shoulder_strap_lower_anchor_R"], s)
            zm = (e_[2] + anc[2]) / 2 + 40
            am = float(body.ab(zm)[0])
            side_p = [s * (am + 12), float(body.yc(zm)) + 10, zm]
            behind = [s * (a_ic + 6), yc_p + b_ic * 0.55, anc[2] + 75]
            webs.append(_ribbon_on([e_ - [0, 2, 10], side_p, behind, anc + [0, -3, 8]],
                                   [[0.3 * s, -1, 0], [s, 0, 0], [s, 0.6, 0], [0.3 * s, -1, 0]], 20, 2.2))
            # load lifter: crown top-bar anchor -> strap top surface near y_lift
            k = int(np.argmin(np.abs(P[:, 1] - y_lift) + 1e3 * (P[:, 2] < ztop - 60)))
            tgt = P[k] + Nn[k] * (tk[k] / 2 + 0.5)
            d = tgt - la
            ln = _u(np.cross(d, [1.0, 0, 0]))
            if ln[2] < 0:
                ln = -ln
            lifters.append(G.ribbon(np.array([la + [0, -rb, 0], la + d * 0.5, tgt]), 22.0, 2.2, ln, step=8))
            dd = _u(d)
            hwr.append(G.superellipsoid(la + d * 0.7 + ln * 2.5, (13, 15, 3.5), 0.3, 0.3, nu=20, nv=10, R=_basis(dd, ln)))
            lifter_angles.append(float(np.degrees(np.arctan2(abs(d[2]), np.hypot(d[0], d[1])))))
        zst = c7 - p["harness"]["sternum_drop"] * T / 483
        xs_ = 75
        yL = float(body.front_y(xs_, zst)) - th - 1
        ym = min(float(body.front_y(0, zst)) - 8, yL)
        st = _ribbon_on([[-xs_ - 18, yL + 4, zst], [-30, ym - 2, zst], [30, ym - 2, zst], [xs_ + 18, yL + 4, zst]],
                        [[-0.2, -1, 0], [0, -1, 0], [0, -1, 0], [0.2, -1, 0]], 20, 2.2)
        hwr.append(G.superellipsoid([0, ym - 7, zst], (20, 6, 13), 0.3, 0.3, nu=20, nv=10))
        parts.append(Part(f"yoke_pad{tag}", yoke, "harness", "suspension", torso=tin, explode=HE, label="Yoke pad"))
        parts.append(Part(f"shoulder_straps{tag}", G.concat(straps), "harness", "suspension", torso=tin, explode=HE,
                          label="J-strap harness"))
        parts.append(Part(f"harness_webbing{tag}", G.concat(webs + [st]), "webbing", "suspension", torso=tin,
                          explode=HE))
        parts.append(Part(f"load_lifters{tag}", G.concat(lifters), "webbing", "suspension", torso=tin,
                          explode=(0.0, -160.0, 120.0), label="Load lifters"))
        parts.append(Part(f"harness_hardware{tag}", G.concat(hwr), "hardware", "suspension", torso=tin, explode=HE))
        if p["mannequin"].get("enabled", True):
            parts.append(Part(f"mannequin{tag}", body.meshes(), "clay", "mannequin", torso=tin,
                              label=f"Mannequin, {tin:g} in torso"))
        torso_info[tin] = {"crown_top_z": cs["crown_top_z"], "yoke_z": cs["yoke_anchor"][2], "c7_z": c7,
                           "lifter_angle_design_deg": cs["lifter_angle_deg"],
                           "lifter_angle_model_deg": float(np.mean(lifter_angles))}

    # ------------------------------------------------------------------ FEA overlay
    fm = None
    if p["fea"].get("enabled", True):
        fea, fm = fea_overlay(p, tubes, g)
        if fea is not None:
            parts.append(Part("frame_fea", fea["mesh"], "fea", "fea", colors=fea["colors"],
                              label="Frame utilization (FEA)"))
            metrics["fea"] = {k: v for k, v in fea.items() if k not in ("mesh", "colors")}

    # ------------------------------------------------------------------ metrics
    vols = g.get("volumes") or {}
    metrics["lid_volume_l"] = lid_vol
    metrics["lid_design_l"] = vols.get("lid_main_L", 0) + vols.get("lid_underlid_L", 0)
    metrics["side_pocket_volume_l_each"] = side_pocket_vol
    metrics["torsos"] = torso_info
    metrics["haul_pullback_mm"] = pull
    wb = g.get("weight") or {}
    alloc = next((v for k, v in (wb.get("groups_g") or {}).items() if k.startswith("frame")), None)
    frame_g, frame_src = alloc, "pack-designer allocation (geometry.yaml weight budget)"
    if fm is not None and p.get("frame_yaml") and fm.get("hardware"):
        frame_g = float(fm["hardware"]["total_g"])
        frame_src = "huntkit.fea frame.yaml model (tubes + hubs)"
    total = wb.get("total_g")
    if total is not None and alloc is not None and frame_g is not None:
        total = total - alloc + frame_g
    metrics.update({"frame_mass_g": frame_g, "frame_mass_source": frame_src, "total_mass_g": total,
                    "total_mass_source": "geometry.yaml weight budget (frame line = FEA mass when frame.yaml exists)"})
    return PackModel(parts=parts, metrics=metrics, params=p, geometry=g, frame_model=fm)


# ============================================================================ FEA overlay
UTIL_STOPS = [(0.0, (26, 152, 80)), (0.5, (145, 207, 96)), (0.75, (254, 224, 139)),
              (1.0, (244, 109, 67)), (1.5, (165, 0, 38))]


def util_color(u):
    u = np.clip(np.asarray(u, float), 0, UTIL_STOPS[-1][0])
    xs = [s[0] for s in UTIL_STOPS]
    cols = np.array([s[1] for s in UTIL_STOPS], float)
    return np.stack([np.interp(u, xs, cols[:, k]) for k in range(3)], -1)


def fea_frame_model(p, tubes, g):
    """frame.yaml model if present; else the closest huntkit.fea.frames.build_frame approximation
    of geometry.yaml (segmented stays, mid bar, frame top at the default-torso crown top)."""
    from huntkit.fea import frames
    t = p["default_torso_in"]
    if p.get("frame_yaml"):
        return frames.build_frame_from_yaml(p["frame_yaml"], torso_in=t), "frame.yaml"
    from huntkit.fea.materials_bridge import CARBON_CANDIDATES, first_available
    from huntkit.fea.sections import composite_tube
    fr = g["frame"]
    hp = fr["hard_points"]
    cs = min(fr["crown_settings"], key=lambda c: abs(c["torso_in"] - t))
    sec = composite_tube(tubes["stay_od"], "[0,±45,0,90]s", first_available(CARBON_CANDIDATES), ply_t=0.10)
    prm = {"name": "viz3d approximation of geometry.yaml", "section": sec, "material": None,
           "stay_style": "segmented", "height": float(cs["crown_top_z"]),
           "width_bottom": 2 * hp["stay_foot_R"][0], "width_top": 2 * hp["stay_top_crown_socket_R"][0] - 2,
           "lumbar_z": hp["lumbar_elbow_R"][2], "lumbar_depth": -hp["lumbar_elbow_R"][1], "lumbar_width": 1e3,
           "top_sweep": 0.0, "hip_z": hp["hipbelt_pivot"][2], "shelf_z": hp["shelf_pivot_R"][2],
           "mid_bar_z": 330.0, "shelf_strap_z": 330.0, "lash_z": 420.0, "torso_in": t, "bonded": True}
    return frames.build_frame(prm), "approximation of geometry.yaml (frame.yaml pending)"


def fea_overlay(p, tubes, g):
    """Envelope utilization (required SF / member SF, max over the standard load cases), on tube
    meshes swept along the FEA model's own members (so the colours sit on the analysed geometry)."""
    try:
        from huntkit.fea.analysis import run_study, summarize
        fm, src = fea_frame_model(p, tubes, g)
        study = run_study(fm, label="viz3d")
    except Exception as e:  # noqa: BLE001
        print(f"[viz3d] FEA overlay skipped: {e!r}")
        return None, None
    util, gov = {}, {}
    for cname, res in study["results"].items():
        req = res.meta.get("required_sf", 2.0)
        for m in res.members:
            u = req / m["sf"] if m["sf"] > 0 else np.inf
            if u > util.get(m["id"], -1):
                util[m["id"]] = float(u)
                gov[m["id"]] = cname
    meshes, cols = [], []
    for m in fm["members"]:
        a, b = (np.array(fm["nodes"][n], float) for n in m["nodes"])
        d = getattr(m["section"], "dims", None) or {}
        r = (d.get("od") or max(d.get("w", 12.7), d.get("h", 12.7))) / 2 + 0.6
        mesh = G.tube(G.resample([a, b], 6.0), r, n=24, tile=40.0, caps=False)
        meshes.append(mesh)
        rgb = util_color(np.full(len(mesh.vertices), util.get(m["id"], 0.0)))
        cols.append(np.column_stack([rgb, np.full(len(rgb), 255.0)]))
    rows = summarize(study)
    crit = max(util, key=util.get)
    return {"mesh": G.concat(meshes), "colors": np.vstack(cols).astype(np.uint8), "source": src,
            "max_utilization": float(max(util.values())), "critical_member": crit,
            "critical_case": gov[crit],
            "min_sf_by_case": {r["case"]: round(float(r["min_sf"]), 3) for r in rows},
            "required_sf_by_case": {r["case"]: r["required_sf"] for r in rows},
            "pass_all": bool(all(r["pass"] for r in rows))}, fm
