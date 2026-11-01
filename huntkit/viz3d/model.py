"""Parametric 3D model of the 5200 cu in hunting pack (all geometry PLACEHOLDER, see params.py).

    from huntkit.viz3d.model import build_pack
    pack = build_pack(load_params("designs/pack_5200/spec.yaml"))
    pack.parts      # list[Part]: named meshes with material key, group, torso tag, explode/haul offsets
    pack.metrics    # volumes, masses, FEA summary

The carbon frame is swept along the node chains of huntkit.fea.frames.build_frame, so the FEA
model and the render are the same geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from . import geom as G
from .params import CU_IN_TO_L, DEFAULT_PARAMS, deep_merge

IN = 25.4


@dataclass
class Part:
    name: str
    mesh: trimesh.Trimesh
    material: str
    group: str
    torso: float | None = None
    explode: tuple = (0.0, 0.0, 0.0)     # mm, FEA frame
    haul: tuple = (0.0, 0.0, 0.0)        # extra offset in haul mode (mm)
    label: str = ""
    colors: np.ndarray | None = None     # optional per-vertex RGBA (FEA overlay)


@dataclass
class PackModel:
    parts: list
    metrics: dict
    params: dict
    frame_model: dict
    extras: dict = field(default_factory=dict)

    def part(self, name):
        return next(p for p in self.parts if p.name == name)


# ============================================================================ frame
def frame_model(p: dict, torso_in: float | None = None) -> dict:
    from huntkit.fea import frames
    t = torso_in if torso_in is not None else p["default_torso_in"]
    if p.get("frame_yaml"):
        return frames.build_frame_from_yaml(p["frame_yaml"], torso_in=t)
    return frames.carbon_variant(**{**p["frame"], "torso_in": t})


def _sec_dims(sec):
    d = getattr(sec, "dims", None) or (sec if isinstance(sec, dict) else {})
    return d


def _member_profile(sec, n=28):
    d = _sec_dims(sec)
    if "od" in d:
        return G.circle(d["od"] / 2, n), d["od"] / 2
    w, h = d.get("w", 12.7), d.get("h", 12.7)
    return G.rounded_rect(w, h, nexp=6, n=n), max(w, h) / 2


def _chains(model, group):
    """Ordered node chains of a member group (stays / cross-bars / braces)."""
    mem = [m for m in model["members"] if m["group"] == group]
    if not mem:
        return []
    adj = {}
    for m in mem:
        a, b = m["nodes"]
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    used, chains = set(), []
    ends = [n for n, v in adj.items() if len(v) == 1] or [mem[0]["nodes"][0]]
    for start in ends:
        if start in used:
            continue
        chain, prev, cur = [start], None, start
        used.add(start)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in used]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            chain.append(cur)
            used.add(cur)
        chains.append(np.array([model["nodes"][n] for n in chain], float))
    return chains, mem[0]


def build_frame_parts(fm: dict, p: dict) -> tuple[list[Part], dict]:
    fp = fm["params"]
    parts, info = [], {}
    stay_meshes, bar_meshes = [], []
    for grp in ("stay_left", "stay_right"):
        res = _chains(fm, grp)
        if not res:
            continue
        chains, m0 = res
        prof, r = _member_profile(m0["section"])
        info["stay_r"] = r
        for P in chains:
            P = P[np.argsort(P[:, 2])]
            if fp.get("stay_style", "curved") == "curved":
                P = G.catmull_rom(P, 6)
            else:
                P = G.resample(P, 4.0)
            stay_meshes.append(G.sweep(P, prof, tile=40.0, up=np.array([0, -1.0, 0]) if "od" not in _sec_dims(m0["section"]) else None))
    for grp in ("top_bar", "lumbar_bar", "mid_bar", "brace"):
        res = _chains(fm, grp)
        if not res:
            continue
        chains, m0 = res
        prof, r = _member_profile(m0["section"])
        for P in chains:
            bar_meshes.append(G.sweep(G.resample(P, 4.0), prof, tile=40.0))
    parts.append(Part("frame_stays", G.concat(stay_meshes), "carbon", "frame", label="Carbon stays"))
    parts.append(Part("frame_crossbars", G.concat(bar_meshes), "carbon", "frame", label="Cross-bars"))
    info["tube_meshes"] = stay_meshes + bar_meshes

    # bonded hub fittings (sockets / through-sleeves) at every hub node
    r = info.get("stay_r", 6.35)
    fit = []
    nodes = fm["nodes"]
    for hub in fm.get("hubs", []):
        c = np.array(nodes[hub["node"]])
        tag = hub["node"][:2]
        i = int(hub["node"][2:])
        lo = np.array(nodes.get(f"{tag}{max(i - 1, 0)}", c))
        hi = np.array(nodes.get(f"{tag}{i + 1}", c))
        ax = hi - lo
        ax = ax / (np.linalg.norm(ax) + 1e-9)
        if hub.get("foot"):
            fit.append(G.capsule_between(c + ax * 18, c - ax * 2, r + 1.8, r + 2.4))
            continue
        L = 22.0
        fit.append(G.tube([c - ax * L, c + ax * L], r + 1.6, n=28, tile=40.0))
        # socket toward the cross-bar
        other = np.array([0.0, c[1], c[2]]) - c
        other[1] = 0
        other = other / (np.linalg.norm(other) + 1e-9)
        fit.append(G.tube([c, c + other * 30], r + 1.6, n=28, tile=40.0))
    if fit:
        parts.append(Part("frame_hubs", G.concat(fit), "fitting", "frame", label="Bonded hub fittings"))

    # carbon hub plates: lumbar plate (wearer side) + top corner gussets
    pl = p["frame_plates"]
    t = pl["thick"]
    hz = fp["hip_z"]
    from huntkit.fea.frames import _stay_point
    xl, yl = _stay_point(hz, 1, fp)
    w = 2 * xl + 26
    hgt = pl["lumbar_h"]
    outline = box(-w / 2, -hgt / 2, w / 2, hgt / 2).buffer(-14).buffer(14, quad_segs=16)
    holes = []
    for cx in (-w * 0.27, 0.0, w * 0.27):
        holes.append(box(cx - w * 0.09, -hgt * 0.22, cx + w * 0.09, hgt * 0.22).buffer(8, quad_segs=12))
    lumbar_poly = outline.difference(unary_union(holes))
    y_face = yl - r - t / 2 - 0.3
    plates = [G.plate(lumbar_poly, [0, y_face, hz], [1, 0, 0], [0, 0, 1], t)]
    info["lumbar_plate_face_y"] = y_face - t / 2
    H = fp["height"]
    for side in (-1, 1):
        xt, yt = _stay_point(H, side, fp)
        xb, yb = _stay_point(H - 60, side, fp)
        down = np.array([xb - xt, yb - yt, -60.0])
        down /= np.linalg.norm(down)
        inward = np.array([-side, 0.0, 0.0])
        leg = pl["corner_leg"]
        tri = Polygon([(-8, 8), (leg, 8), (-8, -leg - 8)]).buffer(10, quad_segs=12)
        tri = tri.difference(Point(leg * 0.28, -leg * 0.28).buffer(9, quad_segs=16))
        ez = np.cross(inward, -down)       # plate normal
        if ez[1] > 0:
            ez = -ez
        origin = np.array([xt, yt, H]) + np.array([0, -(r + t / 2 + 0.3), 0])
        m = G.plate(tri, origin, inward, -down, t)
        plates.append(m)
    parts.append(Part("frame_plates", G.concat(plates), "carbon", "frame", label="Carbon hub plates"))
    return parts, info


# ============================================================================ bag shape
class BagShape:
    """Tapered rounded box: superellipse rings (flatter back) with rounded bottom/top edges.
    ``zeta`` in [-1, 0] bottom edge round, [0, 1] straight walls, [1, 2] top round."""

    def __init__(self, bp: dict, y_back, depth_scale: float = 1.0):
        self.bp = bp
        self.y_back = y_back
        self.k = depth_scale
        self.z0 = bp["z_bottom"]
        self.z1 = bp["z_bottom"] + bp["height"]
        self.zc0 = self.z0 + bp["r_bottom"]
        self.zc1 = self.z1 - bp["r_top"]

    def ab(self, z):
        bp = self.bp
        s = np.clip((z - self.z0) / (self.z1 - self.z0), 0, 1)
        a = bp["a_bottom"] + (bp["a_top"] - bp["a_bottom"]) * s + bp["a_bulge"] * np.sin(np.pi * s)
        b = (bp["b_bottom"] + (bp["b_top"] - bp["b_bottom"]) * s + bp["b_bulge"] * np.sin(np.pi * s ** 0.8)) * self.k
        return a, b

    def ring(self, zeta):
        zeta = np.asarray(zeta, float)
        bp = self.bp
        z = np.where(zeta < 0, self.zc0 + bp["r_bottom"] * np.sin(zeta * np.pi / 2),
                     np.where(zeta > 1, self.zc1 + bp["r_top"] * np.sin((zeta - 1) * np.pi / 2),
                              self.zc0 + (self.zc1 - self.zc0) * zeta))
        shrink = np.where(zeta < 0, bp["r_bottom"] * (1 - np.cos(zeta * np.pi / 2)),
                          np.where(zeta > 1, bp["r_top"] * (1 - np.cos((zeta - 1) * np.pi / 2)), 0.0))
        zr = np.clip(z, self.zc0, self.zc1)
        a, b = self.ab(zr)
        yb = self.y_back(zr)
        return z, a - shrink, b - shrink, yb + b          # centre y keeps the back on the frame

    def surface(self, zeta, theta):
        z, a, b, yc = self.ring(zeta)
        c, s = np.cos(theta), np.sin(theta)
        nexp = np.where(s >= 0, self.bp["n_front"], self.bp["n_back"])
        x = a * np.sign(c) * np.abs(c) ** (2 / nexp)
        y = yc + b * np.sign(s) * np.abs(s) ** (2 / nexp)
        return np.stack([x, y, np.broadcast_to(z, np.shape(x))], -1)

    def normal(self, zeta, theta, h=1e-3):
        dz = self.surface(zeta + h, theta) - self.surface(zeta - h, theta)
        dt = self.surface(zeta, theta + h) - self.surface(zeta, theta - h)
        n = np.cross(dt, dz)
        n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
        z, a, b, yc = self.ring(zeta)
        p = self.surface(zeta, theta)
        out = p - np.stack([np.zeros_like(p[..., 0]), np.broadcast_to(yc, p[..., 0].shape), p[..., 2]], -1)
        sgn = np.sign(np.sum(n * out, axis=-1, keepdims=True))
        return n * np.where(sgn == 0, 1, sgn)

    def zeta_of_z(self, z):
        return (np.asarray(z, float) - self.zc0) / (self.zc1 - self.zc0)

    def mesh(self, rings=72, segments=96):
        nb, nt = 8, 14
        nc = max(rings - nb - nt, 8)
        zs = np.concatenate([np.linspace(-1, 0, nb, endpoint=False), np.linspace(0, 1, nc, endpoint=False),
                             np.linspace(1, 2, nt)])
        th = np.linspace(0, 2 * np.pi, segments, endpoint=False)
        Z, TH = np.meshgrid(zs, th, indexing="ij")
        V = self.surface(Z, TH)
        zb, _, _, ycb = self.ring(np.array(-1.0))
        zt, _, _, yct = self.ring(np.array(2.0))
        return G.loft(V, pole_start=[0, float(ycb), float(zb)], pole_end=[0, float(yct), float(zt)])


def make_bag(p, y_back):
    bp = p["bag"]
    target = p["target_volume_l"] * 1e6
    k = 1.0
    if bp.get("solve_depth", True):
        lo, hi = 0.3, 3.0
        for _ in range(40):
            k = 0.5 * (lo + hi)
            v = G.volume_mm3(BagShape(bp, y_back, k).mesh(bp["rings"], bp["segments"]))
            lo, hi = (k, hi) if v < target else (lo, k)
    shape = BagShape(bp, y_back, k)
    return shape, shape.mesh(bp["rings"], bp["segments"])


# ============================================================================ mannequin
class Body:
    """Clay mannequin torso (widths fixed, lengths scale with torso length T = C7 - iliac crest)."""
    # (z as fraction of T above the iliac crest, half-width a, half-depth b) - PLACEHOLDER anthropometry
    RINGS = [(-0.44, 120, 85), (-0.40, 150, 100), (-0.30, 172, 110), (-0.15, 176, 110), (0.0, 163, 100),
             (0.15, 145, 92), (0.32, 150, 98), (0.50, 166, 110), (0.68, 176, 112), (0.82, 181, 104),
             (0.92, 176, 90), (0.975, 150, 72), (1.01, 92, 56), (1.035, 58, 50)]

    def __init__(self, T, hip_z, back_y0=-46.0):
        self.T, self.hz, self.by0 = T, hip_z, back_y0
        self.c7 = hip_z + T

    def y_back(self, z):
        z = np.asarray(z, float)
        y = self.by0 - 13 * np.exp(-((z - (self.hz + 40)) / 110) ** 2)
        y = y + np.clip((self.hz - 40) - z, 0, None) * 0.25
        return y

    def ab(self, z):
        f = (np.asarray(z, float) - self.hz) / self.T
        fs, a, b = zip(*self.RINGS)
        return np.interp(f, fs, a), np.interp(f, fs, b)

    def yc(self, z):
        a, b = self.ab(z)
        return self.y_back(z) - b

    def front_y(self, x, z, n=2.4):
        a, b = self.ab(z)
        u = np.clip(np.abs(x) / a, 0, 0.999)
        return self.yc(z) - b * (1 - u ** n) ** (1 / n)

    def back_y(self, x, z, n=3.0):
        a, b = self.ab(z)
        u = np.clip(np.abs(x) / a, 0, 0.999)
        return self.yc(z) + b * (1 - u ** n) ** (1 / n)

    def meshes(self):
        T, hz, c7 = self.T, self.hz, self.c7
        fs = np.array([r[0] for r in self.RINGS])
        zs = hz + T * np.concatenate([np.linspace(fs[0], fs[-1], 46)])
        rings = []
        for z in zs:
            a, b = self.ab(z)
            rings.append(G.superellipse_ring(a, b, 2.4, 3.0, M=72, cy=float(self.yc(z)), z=z))
        rings = np.array(rings)
        # rings run +y = back; the generic ring has +y as "front" exponent: swap so the flatter
        # exponent sits on the back (+y side faces the pack)
        z0 = zs[0]
        torso = G.loft(rings, pole_start=[0, float(self.yc(z0)), z0 - 18], cap_end=True)
        ycn = float(self.yc(c7)) + 8
        neck = G.capsule_between([0, ycn, c7 - 30], [0, ycn - 6, c7 + 95], 50, 46)
        head = G.superellipsoid([0, ycn - 22, c7 + 185], (76, 96, 112), e_ns=0.9, e_ew=0.95)
        jaw = G.superellipsoid([0, ycn - 50, c7 + 120], (55, 55, 48), e_ns=0.9, e_ew=0.9)
        zs_ = c7 - 45
        ycs = float(self.yc(zs_))
        arms = []
        for s in (-1, 1):
            sh = np.array([s * 180, ycs, zs_ - 5])
            el = sh + np.array([s * 30, 18, -285])
            wr = el + np.array([s * 6, -215, -95])
            arms += [G.superellipsoid(sh, (56, 58, 56), e_ns=0.9, e_ew=0.9),
                     G.capsule_between(sh, el, 50, 40), G.capsule_between(el, wr, 40, 31)]
        legs = []
        zh = hz - 0.30 * T
        for s in (-1, 1):
            h0 = np.array([s * 88, float(self.yc(zh)) + 5, zh])
            legs.append(G.capsule_between(h0, h0 + np.array([s * 18, -40, -360]), 92, 66))
        return G.concat([torso, neck, head, jaw] + arms + legs)


# ============================================================================ helpers
def _ribbon_on(points, normals, width, thick, step=5.0):
    P = G.catmull_rom(np.asarray(points, float), 10)
    Nn = G._interp_rows(np.asarray(normals, float), len(P))
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    return G.ribbon(P, width, thick, Nn, step=step)


def _block(center, size, R=None, e=0.25):
    return G.superellipsoid(center, np.asarray(size, float) / 2, e_ns=e, e_ew=e, nu=24, nv=12, R=R)


def _frame_basis(d):
    d = np.asarray(d, float) / np.linalg.norm(d)
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0, 0])
    x = np.cross(up, d)
    x /= np.linalg.norm(x)
    z = np.cross(d, x)
    return np.stack([x, d, z], 1)        # columns: local x, y(=d), z


# ============================================================================ main builder
def build_pack(params: dict | None = None) -> PackModel:
    p = deep_merge(DEFAULT_PARAMS, params or {})
    if p.get("frame_yaml") == "auto":
        p["frame_yaml"] = None
    fm = frame_model(p)
    fp = fm["params"]
    from huntkit.fea.frames import _stay_point
    parts, metrics = [], {"placeholder": bool(p.get("placeholder", True)), "warnings": list(fm["warnings"])}

    fparts, finfo = build_frame_parts(fm, p)
    parts += fparts
    r = finfo.get("stay_r", 6.35)
    H = fp["height"]
    hz = fp["hip_z"]

    def stay_y(z):
        z = np.asarray(z, float)
        return np.vectorize(lambda zz: _stay_point(float(np.clip(zz, 0, H)), 1, fp)[1])(z)

    # ---------------------------------------------------------------- bag
    bp = p["bag"]
    gap = bp["gap_to_frame"]
    shape, bag_mesh = make_bag(p, lambda z: stay_y(z) + r + gap)
    vol_l = G.volume_mm3(bag_mesh) / 1e6
    metrics.update({"bag_volume_l": vol_l, "bag_volume_cu_in": vol_l / CU_IN_TO_L,
                    "target_volume_l": p["target_volume_l"],
                    "volume_error_pct": 100 * (vol_l / p["target_volume_l"] - 1),
                    "bag_depth_scale": shape.k})
    za, zb_ = shape.z0, shape.z1
    a_mid, b_mid = shape.ab((za + zb_) / 2)
    metrics["bag_dims_mm"] = {"height": bp["height"], "width_max": float(2 * a_mid),
                              "depth_max": float(2 * max(shape.ab(z)[1] for z in np.linspace(za, zb_, 30)))}
    B = (0.0, 260.0, 0.0)                    # bag explode vector
    HAUL = (0.0, p["quarter"]["depth"] + 25.0, 0.0)
    parts.append(Part("bag_body", bag_mesh, "body", "bag", explode=B, haul=HAUL, label="Main bag"))

    # abrasion base (trim colour) - lower rounded edge, slightly proud
    zs = np.linspace(-1, 0.10, 14)
    th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    Z, TH = np.meshgrid(zs, th, indexing="ij")
    Vb = shape.surface(Z, TH) + shape.normal(Z, TH) * 1.6
    zb0, _, _, ycb = shape.ring(np.array(-1.0))
    base = G.loft(Vb, pole_start=[0, float(ycb), float(zb0) - 1.6], cap_end=True)
    parts.append(Part("bag_base", base, "trim_fabric", "bag", explode=(0, 260, -40), haul=HAUL, label="Abrasion base"))

    # piping on the four vertical corners + bottom ring
    pip = []
    for t0 in (np.pi / 4, 3 * np.pi / 4, -np.pi / 4 - 0.05, -3 * np.pi / 4 + 0.05):
        zz = np.linspace(-0.6, 1.95, 90)
        P = shape.surface(zz, np.full_like(zz, t0)) + shape.normal(zz, np.full_like(zz, t0)) * 1.0
        pip.append(G.tube(P, 2.6, n=10, tile=G.TILE_MM))
    parts.append(Part("bag_piping", G.concat(pip), "trim_fabric", "bag", explode=B, haul=HAUL))

    # ---------------------------------------------------------------- lid
    lp = p["lid"]
    zt = shape.zc1
    a_t, b_t = shape.ab(zt)
    yct = float(stay_y(zt) + r + gap + b_t)
    zl0 = shape.z1 - lp["overlap"]
    zl1 = zl0 + lp["height"]
    rl = lp["radius"]
    rings = []
    for f in np.linspace(-1, 1, 40):
        phi = f * np.pi / 2
        zc = (zl0 + zl1) / 2
        z = zc + (lp["height"] / 2) * np.sin(phi)
        sh = rl * (1 - np.cos(phi)) * 0.9
        a = a_t + lp["overhang_x"] - sh
        b = b_t + lp["overhang_front"] / 2 - sh
        rings.append(G.superellipse_ring(a, b, 3.0, 4.0, M=96, cy=yct + lp["overhang_front"] / 2 - 4, z=z))
    rings = np.array(rings)
    lid = G.loft(rings, cap_start=True, cap_end=True)
    lid_vol = G.volume_mm3(lid) / 1e6
    LID_E = (0.0, 280.0, 190.0)
    parts.append(Part("lid", lid, "camo", "bag", explode=LID_E, haul=HAUL, label="Top lid (camo accent)"))
    # lid seam binding + front zip
    k_mid = len(rings) // 2
    seam = rings[k_mid].copy()
    nrm = seam - np.array([0, yct + lp["overhang_front"] / 2 - 4, seam[0, 2]])
    nrm[:, 2] = 0
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    seam = np.vstack([seam + nrm * 0.6, (seam + nrm * 0.6)[:1]])
    lid_trim = [G.tube(seam, 3.2, n=10, tile=G.TILE_MM, caps=False)]
    ring_low = rings[8]
    nrm_l = ring_low - np.array([0, yct, ring_low[0, 2]])
    nrm_l[:, 2] = 0
    nrm_l /= np.linalg.norm(nrm_l, axis=1, keepdims=True)
    front = [i for i in range(len(ring_low)) if np.arctan2(ring_low[i, 1] - yct, ring_low[i, 0]) > 0.35 and
             np.arctan2(ring_low[i, 1] - yct, ring_low[i, 0]) < np.pi - 0.35]
    zip_pts = ring_low[front] + nrm_l[front] * 1.2
    zip_pts = zip_pts[np.argsort(zip_pts[:, 0])]
    lid_trim.append(G.ribbon(zip_pts, 9.0, 3.0, nrm_l[front][np.argsort(ring_low[front][:, 0])], step=4))
    zp = zip_pts[-3]
    lid_trim.append(_block(zp + np.array([0, 6, -14]), (10, 5, 26), e=0.4))
    parts.append(Part("lid_trim", G.concat(lid_trim), "trim_fabric", "bag", explode=LID_E, haul=HAUL))

    # ---------------------------------------------------------------- side pockets (camo)
    sp = p["side_pocket"]
    zeta_lo, zeta_hi = shape.zeta_of_z(za + sp["z"][0]), shape.zeta_of_z(za + sp["z"][1])

    def pocket_thick(s, t):
        return 3.0 + sp["thick"] * G.bump(s, 0.45) * G.bump(0.08 + 0.84 * t, 0.35) * (1.0 - 0.25 * t)

    pockets = {}
    for side, th0 in ((1, 0.0), (-1, np.pi)):
        t_lo, t_hi = sp["theta"]
        rng = (th0 + t_lo, th0 + t_hi) if side > 0 else (th0 - t_hi, th0 - t_lo)

        def surf(u, v, th_rng=rng):
            return shape.surface(v, u)

        def nrm(u, v):
            return shape.normal(v, u)
        m = G.patch_shell(surf, nrm, rng, (zeta_lo, zeta_hi), pocket_thick, inset=3.0, nu=44, nv=36)
        name = "side_pocket_R" if side > 0 else "side_pocket_L"
        # FEA x+ = wearer's right
        parts.append(Part(name, m, "camo", "bag", explode=(side * 150.0, 260.0, 0.0), haul=HAUL,
                          label="Side pocket (camo accent)"))
        pockets[side] = (rng, (zeta_lo, zeta_hi))
    side_pocket_vol = 2 * (G.volume_mm3(parts[-1].mesh)) / 1e6

    def pocket_offset(theta, zeta):
        """Pocket thickness at a bag-surface point (0 outside the pockets)."""
        out = np.zeros(np.broadcast(theta, zeta).shape)
        for side, (rng, zr) in pockets.items():
            th = np.mod(theta - rng[0], 2 * np.pi) / (rng[1] - rng[0])
            tz = (zeta - zr[0]) / (zr[1] - zr[0])
            inside = (th >= 0) & (th <= 1) & (tz >= 0) & (tz <= 1)
            out = np.where(inside, pocket_thick(np.clip(th, 0, 1), np.clip(tz, 0, 1)), out)
        return out

    # ---------------------------------------------------------------- front stretch pocket
    fpk = p["front_pocket"]
    th_h = fpk["theta_half"]
    m = G.patch_shell(lambda u, v: shape.surface(v, u), lambda u, v: shape.normal(v, u),
                      (np.pi / 2 - th_h, np.pi / 2 + th_h),
                      (shape.zeta_of_z(za + fpk["z"][0]), shape.zeta_of_z(za + fpk["z"][1])),
                      lambda s, t: 2.5 + fpk["thick"] * G.bump(s, 0.5) * G.bump(0.1 + 0.9 * t, 0.4),
                      inset=2.0, nu=40, nv=40)
    parts.append(Part("front_pocket", m, "stretch_mesh", "bag", explode=(0, 420.0, 0), haul=HAUL,
                      label="Front stretch pocket"))
    # binding on the front pocket top edge
    tt = np.linspace(np.pi / 2 - th_h, np.pi / 2 + th_h, 50)
    ze = np.full_like(tt, shape.zeta_of_z(za + fpk["z"][1]))
    edge_t = 2.5 + fpk["thick"] * G.bump((tt - tt[0]) / (tt[-1] - tt[0]), 0.5) * G.bump(np.array(1.0), 0.4)
    Pe = shape.surface(ze, tt) + shape.normal(ze, tt) * (edge_t[:, None] + 0.5)
    bind = G.tube(Pe, 3.0, n=10, tile=G.TILE_MM)

    # ---------------------------------------------------------------- compression straps + zip
    cp = p["compression"]
    straps = [bind]
    buckles = []
    for side in (1, -1):
        for zc in cp["z"]:
            zeta = shape.zeta_of_z(za + zc)
            t_lo, t_hi = cp["theta"]
            tt = np.linspace(t_lo, t_hi, 70)
            if side < 0:
                tt = np.pi - tt
            ze = np.full_like(tt, zeta)
            off = pocket_offset(np.mod(tt, 2 * np.pi), ze) + cp["thick"] / 2 + 0.8
            P = shape.surface(ze, tt) + shape.normal(ze, tt) * off[:, None]
            Nn = shape.normal(ze, tt)
            straps.append(G.ribbon(P, cp["width"], cp["thick"], Nn, step=5))
            # ladder-lock buckle near the front end
            k = int(len(tt) * 0.86)
            d = P[k + 1] - P[k - 1]
            Rb = _frame_basis(d)
            nb = Nn[k]
            buckles.append(G.superellipsoid(P[k] + nb * 2.5, (cp["width"] / 2 + 4, 14, 3.5), 0.3, 0.3, nu=24, nv=12,
                                            R=np.stack([np.cross(d / np.linalg.norm(d), nb), d / np.linalg.norm(d), nb], 1)))
    # full-length side zip (wearer's right, front corner)
    zz = np.linspace(-0.55, 1.6, 120)
    tz = np.full_like(zz, 0.98)
    Pz = shape.surface(zz, tz) + shape.normal(zz, tz) * 1.4
    straps.append(G.ribbon(Pz, 9.0, 2.6, shape.normal(zz, tz), step=4))
    buckles.append(_block(Pz[-6] + shape.normal(zz[-6], tz[-6]) * 5 + np.array([0, 0, -16]), (6, 6, 30), e=0.4))
    parts.append(Part("compression_straps", G.concat(straps), "webbing", "bag", explode=(0, 300.0, 0), haul=HAUL,
                      label="Compression straps + side zip"))
    parts.append(Part("buckles", G.concat(buckles), "hardware", "bag", explode=(0, 300.0, 0), haul=HAUL))

    # ---------------------------------------------------------------- load shelf + haul load
    sh = p["shelf"]
    zs_ = fp["shelf_z"]
    xs, ys = _stay_point(zs_, 1, fp)
    shelf_poly = box(-(xs + 14), 0, xs + 14, sh["depth"]).buffer(-18).buffer(18, quad_segs=12)
    shelf_poly = shelf_poly.difference(unary_union([box(-xs * 0.55 + i * xs * 0.55 - 22, sh["depth"] * 0.35,
                                                        -xs * 0.55 + i * xs * 0.55 + 22, sh["depth"] * 0.72)
                                                    .buffer(10, quad_segs=10) for i in range(3)]))
    shelf = G.plate(shelf_poly, [0, ys - 4, zs_ + sh["thick"] / 2], [1, 0, 0], [0, 1, 0], sh["thick"])
    hinge = G.tube([[-(xs + 10), ys, zs_ + 4], [xs + 10, ys, zs_ + 4]], 7.0, n=20, tile=40.0)
    parts.append(Part("load_shelf", G.concat([shelf, hinge]), "shelf", "shelf", explode=(0, 60.0, -80.0),
                      label="Load (meat) shelf"))

    q = p["quarter"]
    qz0 = zs_ + sh["thick"] + 1
    y_q0 = float(stay_y(qz0 + 200)) + r + 8
    qrings = []
    for f in np.linspace(0, 1, 34):
        z = qz0 + q["height"] * f
        taper = 1 - 0.42 * f ** 1.4
        bulge = 1 + 0.12 * np.sin(np.pi * min(f * 1.6, 1))
        rr = 1 - (1 - np.sqrt(max(1 - ((f - 0.5) / 0.5) ** 8, 0))) if 0 < f < 1 else 0.6
        a = q["width"] / 2 * taper * bulge * rr
        b = q["depth"] / 2 * (1 - 0.25 * f) * bulge * rr
        qrings.append(G.superellipse_ring(max(a, 20), max(b, 15), 2.3, 3.2, M=64, cy=y_q0 + q["depth"] / 2, z=z))
    quarter = G.loft(np.array(qrings), cap_start=True, cap_end=True)
    qtop = qz0 + q["height"]
    bone_c = np.array([18, y_q0 + q["depth"] * 0.45, qtop - 40])
    bone = G.concat([G.capsule_between(bone_c, bone_c + [6, 4, 120], 21, 19),
                     G.superellipsoid(bone_c + [6, 4, 132], (30, 26, 24), 0.8, 0.8)])
    QE = (0.0, 110.0, 0.0)
    parts.append(Part("quarter_proxy", quarter, "game_bag", "haul", explode=QE,
                      label="Bone-in elk hindquarter proxy (in game bag)"))
    parts.append(Part("quarter_bone", bone, "bone", "haul", explode=QE))
    hauls = []
    cy = y_q0 + q["depth"] / 2
    for zc in (fp["shelf_strap_z"], fp["lash_z"]):
        xsz, ysz = _stay_point(zc, 1, fp)
        rq = qrings[int(np.argmin([abs(rr[0, 2] - zc) for rr in qrings]))]
        ang = np.mod(np.arctan2(rq[:, 1] - cy, rq[:, 0]) + 0.3, 2 * np.pi) - 0.3
        sel = (ang > -0.12) & (ang < np.pi + 0.12)
        pts = rq[sel][np.argsort(ang[sel])]
        nr = pts - np.array([0, cy, zc])
        nr[:, 2] = 0
        nr /= np.linalg.norm(nr, axis=1, keepdims=True)
        pts = pts + nr * 3.0
        path = np.vstack([[xsz + r + 2, ysz + 4, zc], pts, [-(xsz + r + 2), ysz + 4, zc]])
        nrm = np.vstack([[1, 0.3, 0], nr, [-1, 0.3, 0]])
        hauls.append(G.ribbon(path, 38.0, 2.6, nrm / np.linalg.norm(nrm, axis=1, keepdims=True), step=5))
    parts.append(Part("haul_straps", G.concat(hauls), "webbing", "haul", explode=QE, label="Load lashing straps"))

    # ---------------------------------------------------------------- body reference + hipbelt
    T0 = p["default_torso_in"] * IN
    body0 = Body(T0, hz)
    # set the body back so the hipbelt (thickness hb) lands on the lumbar plate
    hbp = p["hipbelt"]
    plate_face = finfo.get("lumbar_plate_face_y", float(stay_y(hz)) - r - 3)
    body_back0 = plate_face - 2.0 - hbp["thick"]
    shift = body_back0 - float(body0.y_back(hz))
    BY0 = body0.by0 + shift
    body0 = Body(T0, hz, BY0)
    a_ic, b_ic = body0.ab(hz)
    yc_p = float(body0.yc(hz))
    end = np.deg2rad(hbp["end_deg"])
    phis = np.linspace(-end, end, 160)

    def pelvis_pt(phi, off, z=hz):
        # phi = 0 at the back centre (+y), positive toward the wearer's right (+x)
        x = (a_ic + off) * np.sign(np.sin(phi)) * np.abs(np.sin(phi)) ** (2 / 2.6)
        y = yc_p + (b_ic + off) * np.sign(np.cos(phi)) * np.abs(np.cos(phi)) ** (2 / (3.0 if np.cos(phi) > 0 else 2.4))
        return np.array([x, y, z])

    t_belt = hbp["thick"]
    hdeg = np.abs(np.rad2deg(phis))
    h_belt = np.interp(hdeg, [0, 30, 110, hbp["end_deg"]], [hbp["height_center"], hbp["height_center"],
                                                            hbp["height_wing"], hbp["height_end"]])
    th_belt = np.interp(hdeg, [0, 100, hbp["end_deg"]], [t_belt, t_belt * 0.85, t_belt * 0.6])
    path = np.array([pelvis_pt(f, th / 2 + 1.0) for f, th in zip(phis, th_belt)])
    outw = np.array([pelvis_pt(f, 10) - pelvis_pt(f, 0) for f in phis])
    outw /= np.linalg.norm(outw, axis=1, keepdims=True)
    tilt = np.abs(np.sin(phis))[:, None] * 0.22
    upv = np.array([0, 0, 1.0]) - outw * tilt
    upv /= np.linalg.norm(upv, axis=1, keepdims=True)
    belt_prof = G.rounded_rect(1.0, 1.0, nexp=3.2, n=36)
    # sweep: profile x -> S = up x T (horizontal, outward or inward); y -> up
    belt = G.sweep(path, belt_prof, up=upv, scale=np.stack([th_belt, h_belt], -1), tile=G.TILE_MM)
    HB_E = (0.0, -230.0, -110.0)
    parts.append(Part("hipbelt", belt, "harness", "suspension", explode=HB_E, label="Hipbelt"))
    # S direction sign: check it points outward at phi = 90 deg
    Tm, Sm, Nm = G.frames_along(path, upv)
    sgn = np.sign(np.dot(Sm[len(path) * 3 // 4], outw[len(path) * 3 // 4]))
    wings = []
    for lo, hi in [(hbp["wing_deg"][0], hbp["wing_deg"][1]), (-hbp["wing_deg"][1], -hbp["wing_deg"][0])]:
        sel = (np.rad2deg(phis) >= lo) & (np.rad2deg(phis) <= hi)
        n = sel.sum()
        prof = G.rounded_rect(1.6, 1.0, nexp=4, n=36)
        wings.append(G.sweep(path[sel], prof, up=upv[sel],
                             scale=np.stack([np.ones(n), h_belt[sel] - 16], -1),
                             offset=np.stack([sgn * (th_belt[sel] / 2 + 0.5), np.zeros(n)], -1), tile=G.TILE_MM))
    parts.append(Part("hipbelt_wings", G.concat(wings), "camo", "suspension", explode=HB_E,
                      label="Hipbelt wings (camo accent)"))
    hpk = []
    for lo, hi in [(hbp["pocket_deg"][0], hbp["pocket_deg"][1]), (-hbp["pocket_deg"][1], -hbp["pocket_deg"][0])]:
        sel = (np.rad2deg(phis) >= lo) & (np.rad2deg(phis) <= hi)
        n = sel.sum()
        s = np.linspace(0, 1, n)
        bul = 4 + 24 * G.bump(s, 0.4)
        prof = G.rounded_rect(1.0, 1.0, nexp=3.0, n=36)
        hpk.append(G.sweep(path[sel], prof, up=upv[sel], scale=np.stack([bul, np.full(n, 74.0)], -1),
                           offset=np.stack([sgn * (th_belt[sel] / 2 + bul / 2 - 1), np.full(n, -6.0)], -1),
                           tile=G.TILE_MM))
    parts.append(Part("hipbelt_pockets", G.concat(hpk), "body", "suspension", explode=HB_E, label="Hipbelt pockets"))
    # front webbing + buckle
    eL, eR = path[0], path[-1]
    front_y = yc_p - b_ic - 20
    web = np.array([eL, [eL[0] * 0.55, front_y + 12, hz], [0, front_y, hz], [eR[0] * 0.55, front_y + 12, hz], eR])
    wn = np.array([[-1, -0.3, 0], [-0.4, -1, 0], [0, -1, 0], [0.4, -1, 0], [1, -0.3, 0]], float)
    hbw = [_ribbon_on(web, wn, 25.0, 2.4)]
    hbw.append(G.superellipsoid([0, front_y - 6, hz], (24, 8, 15), 0.3, 0.3, nu=24, nv=12))
    parts.append(Part("hipbelt_buckle", G.concat(hbw), "hardware", "suspension", explode=HB_E))

    # back pad (spacer mesh) between frame and upper back, and lumbar pad strip
    z_bp0, z_bp1 = hz + hbp["height_center"] / 2 + 15, min(hz + 15 * IN - 120, H - 140)
    xw = float(_stay_point(z_bp0, 1, fp)[0]) - r - 4

    def bp_surf(u, v):
        return np.stack([u, stay_y(v) - r - 1.5, v], -1)

    def bp_n(u, v):
        return np.broadcast_to(np.array([0, -1.0, 0]), np.shape(u) + (3,))

    def bp_thick(s, t):
        z = z_bp0 + (z_bp1 - z_bp0) * t
        gap_ = (stay_y(z) - r - 1.5) - body0.y_back(z)
        return np.clip(gap_ - 1.0, 4, None) * (0.35 + 0.65 * G.bump(s, 0.3) * G.bump(t, 0.25))
    pad = G.patch_shell(bp_surf, bp_n, (-xw, xw), (z_bp0, z_bp1), bp_thick, inset=2.0, nu=30, nv=40)
    parts.append(Part("back_pad", pad, "spacer", "suspension", explode=(0, -120.0, 0), label="Back pad (spacer mesh)"))

    # ---------------------------------------------------------------- per-torso harness + mannequin
    hp = p["harness"]
    torso_info = {}
    for tin in p["torsos_in"]:
        T = tin * IN
        body = Body(T, hz, BY0)
        fmt = frame_model(p, tin)
        szy = fmt["params"]["shoulder_z"]
        c7 = body.c7
        torso_info[tin] = {"shoulder_z": szy, "warnings": fmt["warnings"], "c7_z": c7}
        tag = f"@t{tin:g}"
        # yoke between frame and back at the shoulder anchor
        yb = float(body.y_back(szy))
        yf = float(stay_y(szy)) - r
        ycy = (yb + yf) / 2
        yoke = G.superellipsoid([0, ycy, szy], (110, max((yf - yb) / 2, 8), 52), 0.35, 0.35, nu=40, nv=16)
        HE = (0.0, -300.0, 60.0)
        parts.append(Part(f"yoke{tag}", yoke, "harness", "suspension", torso=tin, explode=HE, label="Harness yoke"))
        # shoulder straps
        th = hp["thick"]
        straps, webs, lifters, hw = [], [], [], []
        for s in (-1, 1):
            pts, nrm = [], []

            def add(x, z, where, extra=0.0):
                if where == "back":
                    y = float(body.back_y(x, z)) + th / 2 + 1 + extra
                    n = np.array([0, 1.0, 0])
                elif where == "front":
                    y = float(body.front_y(x, z)) - th / 2 - 1 - extra
                    n = np.array([0.15 * s, -1.0, 0])
                pts.append([x, y, z])
                nrm.append(n)
            add(s * 52, szy, "back", extra=(yf - yb) - 2)     # on the yoke face
            add(s * 66, szy + 0.45 * (c7 - 30 - szy), "back")
            add(s * 80, c7 - 30, "back")
            # over the trapezius (sagittal arc at |x| ~ 92)
            ytop_b = float(body.back_y(92, c7 - 40))
            ytop_f = float(body.front_y(92, c7 - 60))
            for f in np.linspace(0.12, 0.88, 6):
                y = ytop_b + (ytop_f - ytop_b) * f
                z = c7 - 2 + th / 2 + 1 - 95 * (f - 0.5) ** 2 * 1.4
                pts.append([s * (88 + 6 * f), y, z])
                n = np.array([0, np.cos(np.pi * f) * 0.9, np.sin(np.pi * f) + 0.2])
                nrm.append(n / np.linalg.norm(n))
            for x, dz in ((98, 70), (102, 125), (114, 195), (134, 265), (152, 320)):
                add(s * x, c7 - dz, "front")
            P = G.catmull_rom(np.array(pts), 12)
            Nn = G._interp_rows(np.array(nrm), len(P))
            Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
            n = len(P)
            w = np.interp(np.linspace(0, 1, n), [0, 0.15, 0.7, 1], [hp["width"] * 0.85, hp["width"], hp["width"] * 0.92, hp["width"] * 0.72])
            tk = np.interp(np.linspace(0, 1, n), [0, 0.1, 0.8, 1], [th * 0.7, th, th, th * 0.6])
            straps.append(G.sweep(P, G.rounded_rect(1.0, 1.0, nexp=3.0, n=32), up=Nn,
                                  scale=np.stack([w, tk], -1), tile=G.TILE_MM))
            # lower webbing to the hipbelt side
            end_p = P[-1]
            hb_side = pelvis_pt(s * np.deg2rad(98), t_belt + 2, hz + 30)
            mid = (end_p + hb_side) / 2 + np.array([s * 18, -10, 0])
            webs.append(_ribbon_on([end_p - [0, 2, 8], mid, hb_side], [[0.2 * s, -1, 0], [s, -0.6, 0], [s, -0.2, 0]], 20, 2.2))
            # load lifter: frame top corner -> strap just ahead of the shoulder
            xt, yt = _stay_point(H, s, fp)
            top = np.array([xt, yt - r - 2, H - 14])
            k = int(n * 0.40)
            tgt = P[k] + Nn[k] * (tk[k] / 2)
            d = tgt - top
            ln = np.cross(d, [1.0, 0, 0])
            ln /= np.linalg.norm(ln)
            if ln[2] < 0:
                ln = -ln
            lifters.append(G.ribbon(np.array([top, top + d * 0.5, tgt]), 20.0, 2.2, ln, step=5))
            c = top + d * 0.72
            dd = d / np.linalg.norm(d)
            hw.append(G.superellipsoid(c + ln * 2.5, (13, 14, 3.5), 0.3, 0.3, nu=20, nv=10,
                                       R=np.stack([np.cross(dd, ln), dd, ln], 1)))
            torso_info[tin][f"lifter_angle_deg_{'R' if s > 0 else 'L'}"] = float(
                abs(np.degrees(np.arctan2(d[2], np.hypot(d[0], d[1])))))
        parts.append(Part(f"shoulder_straps{tag}", G.concat(straps), "harness", "suspension", torso=tin,
                          explode=HE, label="Shoulder harness"))
        parts.append(Part(f"harness_webbing{tag}", G.concat(webs), "webbing", "suspension", torso=tin, explode=HE))
        parts.append(Part(f"load_lifters{tag}", G.concat(lifters), "webbing", "suspension", torso=tin,
                          explode=(0.0, -160.0, 120.0), label="Load lifters"))
        # sternum strap
        zst = c7 - hp["sternum_drop"]
        xs_ = 72
        yL = float(body.front_y(xs_, zst)) - th - 1
        yM = float(body.front_y(0, zst)) - 8
        st = _ribbon_on([[-xs_ - 20, yL + 4, zst], [-30, min(yM, yL) - 2, zst], [30, min(yM, yL) - 2, zst],
                         [xs_ + 20, yL + 4, zst]], [[-0.2, -1, 0], [0, -1, 0], [0, -1, 0], [0.2, -1, 0]], 18, 2.2)
        hw.append(G.superellipsoid([0, min(yM, yL) - 7, zst], (19, 6, 12), 0.3, 0.3, nu=20, nv=10))
        parts.append(Part(f"sternum_strap{tag}", st, "webbing", "suspension", torso=tin,
                          explode=(0.0, -340.0, 60.0), label="Sternum strap"))
        parts.append(Part(f"harness_hardware{tag}", G.concat(hw), "hardware", "suspension", torso=tin, explode=HE))
        if p["mannequin"].get("enabled", True):
            parts.append(Part(f"mannequin{tag}", body.meshes(), "clay", "mannequin", torso=tin,
                              label=f"Mannequin, {tin:g} in torso"))

    # ---------------------------------------------------------------- FEA overlay
    fea = None
    if p["fea"].get("enabled", True):
        fea = fea_overlay(fm, finfo["tube_meshes"])
        if fea is not None:
            parts.append(Part("frame_fea", fea["mesh"], "fea", "fea", colors=fea["colors"],
                              label="Frame utilization (FEA)"))
            metrics["fea"] = {k: v for k, v in fea.items() if k not in ("mesh", "colors")}

    # ---------------------------------------------------------------- metrics
    metrics["lid_volume_l"] = lid_vol
    metrics["side_pockets_volume_l"] = side_pocket_vol
    metrics["torsos"] = torso_info
    metrics.update(mass_estimate(parts, fm))
    for tin, ti in torso_info.items():
        metrics["warnings"] += ti["warnings"]
    metrics["warnings"] = list(dict.fromkeys(metrics["warnings"]))
    return PackModel(parts=parts, metrics=metrics, params=p, frame_model=fm,
                     extras={"bag_shape": shape})


# ============================================================================ FEA overlay
UTIL_STOPS = [(0.0, (26, 152, 80)), (0.5, (145, 207, 96)), (0.75, (254, 224, 139)),
              (1.0, (244, 109, 67)), (1.5, (165, 0, 38))]


def util_color(u):
    u = np.clip(np.asarray(u, float), 0, UTIL_STOPS[-1][0])
    xs = [s[0] for s in UTIL_STOPS]
    cols = np.array([s[1] for s in UTIL_STOPS], float)
    return np.stack([np.interp(u, xs, cols[:, k]) for k in range(3)], -1)


def fea_overlay(fm: dict, tube_meshes: list) -> dict | None:
    """Envelope utilization (required SF / member SF, max over the standard load cases) mapped
    onto the frame tube meshes as vertex colours. Returns None if huntkit.fea can't run."""
    try:
        from huntkit.fea.analysis import run_study, summarize
        study = run_study(fm, label="viz3d")
    except Exception as e:  # noqa: BLE001
        print(f"[viz3d] FEA overlay skipped: {e!r}")
        return None
    util, gov = {}, {}
    for cname, res in study["results"].items():
        req = res.meta.get("required_sf", 2.0)
        for m in res.members:
            u = req / m["sf"] if m["sf"] > 0 else np.inf
            if u > util.get(m["id"], -1):
                util[m["id"]] = float(u)
                gov[m["id"]] = cname
    segs = np.array([[fm["nodes"][m["nodes"][0]], fm["nodes"][m["nodes"][1]]] for m in fm["members"]])
    uarr = np.array([util.get(m["id"], 0.0) for m in fm["members"]])
    mesh = G.concat(tube_meshes)
    V = mesh.vertices
    a, b = segs[:, 0], segs[:, 1]
    ab = b - a
    t = np.clip(np.einsum("vmk,mk->vm", V[:, None, :] - a[None], ab) / np.einsum("mk,mk->m", ab, ab)[None], 0, 1)
    d = np.linalg.norm(V[:, None, :] - (a[None] + t[..., None] * ab[None]), axis=2)
    near = np.argmin(d, axis=1)
    rgb = util_color(uarr[near])
    colors = np.concatenate([rgb, np.full((len(V), 1), 255.0)], 1).astype(np.uint8)
    rows = summarize(study)
    crit = max(util, key=util.get)
    return {"mesh": mesh, "colors": colors, "max_utilization": float(max(util.values())),
            "critical_member": crit, "critical_case": gov[crit],
            "min_sf_by_case": {r["case"]: round(float(r["min_sf"]), 3) for r in rows},
            "required_sf_by_case": {r["case"]: r["required_sf"] for r in rows},
            "pass_all": bool(all(r["pass"] for r in rows)),
            "section": str(_sec_dims(fm["members"][0]["section"]))}


# ============================================================================ mass estimate
_GSM_FALLBACK = {"cordura_500d_nylon66": 255, "power_mesh_nylon_spandex": 170, "spacer_mesh_3d": 380,
                 "hypalon_coated_nylon": 1000}


def _gsm(mid):
    try:
        from huntkit.materials import load
        v = load(mid).props.get("areal_density_gsm")
        if v:
            return float(v)
    except Exception:  # noqa: BLE001
        pass
    return float(_GSM_FALLBACK.get(mid, 250))


def mass_estimate(parts: list, fm: dict) -> dict:
    """Rough total mass (g). ASSUMPTIONs: seam/reinforcement factor 1.25 on shell fabric; padded
    parts = shell + spacer on half the closed area each, plus EVA 45C foam at 60 % of the
    enclosed volume; hardware allowance 160 g; load shelf 140 g. Frame from huntkit.fea."""
    try:
        from huntkit.materials import load
        foam_rho = float(load("eva_foam_45c").props.get("density_kg_m3", 110))
    except Exception:  # noqa: BLE001
        foam_rho = 110.0
    shell = _gsm("cordura_500d_nylon66")
    mesh_gsm = _gsm("power_mesh_nylon_spandex")
    spacer = _gsm("spacer_mesh_3d")
    soft, rows = 0.0, {}
    default_t = None
    for prt in parts:
        if prt.torso is not None:
            default_t = default_t or prt.torso
    for prt in parts:
        if prt.torso is not None and prt.torso != _mid_torso(parts):
            continue
        A = prt.mesh.area / 1e6           # m^2 (closed surface)
        g = 0.0
        if prt.name in ("bag_body", "lid"):
            g = A * shell * 1.25
        elif prt.name.startswith("side_pocket"):
            g = A / 2 * shell * 1.25
        elif prt.name == "front_pocket":
            g = A / 2 * mesh_gsm * 1.2
        elif prt.name in ("hipbelt",) or prt.name.startswith("shoulder_straps") or prt.name.startswith("yoke"):
            g = A / 2 * (shell + spacer) + G.volume_mm3(prt.mesh) * 1e-9 * foam_rho * 1e3 * 0.6
        elif prt.name == "back_pad":
            g = A / 2 * (spacer + shell)
        elif prt.name in ("compression_straps", "haul_straps") or prt.name.startswith(("harness_webbing", "load_lifters", "sternum_strap")):
            g = prt.mesh.area / (2 * 25.0) * 1e-3 * 18.0   # length (area / 2w) x 18 g/m (25 mm webbing)
        if g:
            rows[prt.name.split("@")[0]] = round(g, 1)
            soft += g
    hw = fm.get("hardware") or {}
    frame_g = float(hw.get("total_g", 0.0))
    plates = next((p for p in parts if p.name == "frame_plates"), None)
    plate_g = G.volume_mm3(plates.mesh) * 1550e-6 if plates is not None else 0.0
    # ASSUMPTION allowances: buckles/ladder-locks 160 g, load shelf 140 g, hipbelt HDPE
    # stiffener 120 g, zips + binding + labels 180 g, bag liner (210D ripstop) on the bag area
    liner = next((p.mesh.area / 1e6 * _gsm("robic_210d_ripstop") for p in parts if p.name == "bag_body"), 0.0)
    allowance = 160.0 + 140.0 + 120.0 + 180.0 + liner
    total = frame_g + plate_g + soft + allowance
    return {"frame_mass_g": frame_g + plate_g, "frame_tubes_g": float(hw.get("tubes_g", 0.0)),
            "frame_hubs_g": float(hw.get("hubs_g", 0.0)), "frame_plates_g": plate_g,
            "soft_goods_g": soft, "soft_goods_rows_g": rows, "allowances_g": allowance,
            "total_mass_g": total}


def _mid_torso(parts):
    ts = sorted({p.torso for p in parts if p.torso is not None})
    return ts[len(ts) // 2] if ts else None
