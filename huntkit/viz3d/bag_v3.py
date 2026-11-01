"""Pack 5200 v3 'SPINE' bag for the 3D model: teardrop roll-top lofted from geometry.yaml.

Reads ``bag.profile`` (stations ``[z, half_width_x, y_frame_side, depth_y]`` for the FULL 85.2 L
state and ``stations_rolled`` for the daily rolled-down state), ``bag.diagonal`` (zip line and
stretch band), ``bag.rolltop``, ``haul_wraps``, ``side_pockets``, ``meat_harness`` (v3.1; ``load_shelf``
for legacy geometry) and ``lid``.

Every ring is the mixed superellipse used by designs/pack_5200/build_geometry.py (outer half
exponent ``n_out``, frame half ``n_frm``), so the mesh volume reproduces the computed volume.
Surface features (band, shards, pockets, straps) are placed with :class:`TeardropSurface`, a
(u, z) parametrisation of the bag skin: u = arc length (mm) from the outer-face centre line,
positive toward the wearer's RIGHT (+x).

Part variants (viewer toggles): ``rolled`` (default display), ``full`` (collar unrolled to the
fill line: the counted 85.2 L) and ``lid`` (optional accessory).
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from . import geom as G

BAGM = ("pack", "pack_haul")
HAULM = ("pack_haul", "frame_haul")


class TeardropSurface:
    """Bag skin from profile stations. Rings resampled to M equal arc steps starting at the
    outer-face centre and running toward +x (wearer's right), round the frame side and back."""

    def __init__(self, stations, n_out, n_frm, M=480):
        st = np.asarray(stations, float)
        self.z, self.a, self.yf, self.d = st[:, 0], st[:, 1], st[:, 2], st[:, 3]
        self.n_out, self.n_frm, self.M = n_out, n_frm, M
        K = len(st)
        self.T = np.zeros((K, M + 1, 3))
        self.P = np.zeros(K)
        self.Lo = np.zeros(K)
        th = np.pi / 2 - np.linspace(0, 2 * np.pi, 4000, endpoint=False)   # from the outer centre toward +x
        for k in range(K):
            pts = self.ring_theta(k, th)
            seg = np.linalg.norm(np.diff(np.vstack([pts, pts[:1]]), axis=0), axis=1)
            s = np.r_[0, np.cumsum(seg)]
            self.P[k] = s[-1]
            sj = np.linspace(0, s[-1], M + 1)
            pc = np.vstack([pts, pts[:1]])
            self.T[k] = np.stack([np.interp(sj, s, pc[:, i]) for i in range(3)], -1)
            # outer half: theta in [0, pi]  <=> th from pi/2 down to 0 and from pi/2 up to pi
            o = np.sin(th) >= 0
            self.Lo[k] = float(np.sum(seg[o]))

    def ring_theta(self, k, th):
        a, b = self.a[k], self.d[k] / 2
        yc = self.yf[k] + b
        c, s = np.cos(th), np.sin(th)
        n = np.where(s >= 0, self.n_out, self.n_frm)
        return np.column_stack([a * np.sign(c) * np.abs(c) ** (2 / n), yc + b * np.sign(s) * np.abs(s) ** (2 / n),
                                np.full(len(th), self.z[k])])

    # ------------------------------------------------------------------ queries
    def _k(self, z):
        return np.interp(z, self.z, np.arange(len(self.z)))

    def perim(self, z):
        return np.interp(z, self.z, self.P)

    def outer_half(self, z):
        return np.interp(z, self.z, self.Lo)

    def frame_half(self, z):
        return self.perim(z) - self.outer_half(z)

    def center(self, z):
        return np.stack([np.zeros_like(np.asarray(z, float)), np.interp(z, self.z, self.yf + self.d / 2),
                         np.asarray(z, float)], -1)

    def pt(self, u, z):
        u, z = np.broadcast_arrays(np.asarray(u, float), np.asarray(z, float))
        kf = np.clip(self._k(z), 0, len(self.z) - 1 - 1e-9)
        k0 = np.floor(kf).astype(int)
        wk = kf - k0
        phi = np.mod(u / self.perim(z), 1.0) * self.M
        j0 = np.floor(phi).astype(int)
        wj = phi - j0
        j1 = np.minimum(j0 + 1, self.M)

        def at(k):
            return self.T[k, j0] * (1 - wj)[..., None] + self.T[k, j1] * wj[..., None]
        return at(k0) * (1 - wk)[..., None] + at(np.minimum(k0 + 1, len(self.z) - 1)) * wk[..., None]

    def nrm(self, u, z, h=1.0):
        a = self.pt(np.asarray(u, float) + h, z) - self.pt(np.asarray(u, float) - h, z)
        b = self.pt(u, np.asarray(z, float) + h) - self.pt(u, np.asarray(z, float) - h)
        n = np.cross(b, a)
        n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12
        p = self.pt(u, z)
        out = p - self.center(np.broadcast_to(np.asarray(z, float), p.shape[:-1]))
        out[..., 2] = 0
        return n * np.sign(np.sum(n * out, axis=-1, keepdims=True) + 1e-12)

    def u_of(self, p):
        """Arc position u (mm) of a 3D point on (or near) the skin."""
        p = np.asarray(p, float)
        kf = self._k(p[2])
        k = int(round(kf))
        j = int(np.argmin(np.linalg.norm(self.T[k, :-1, :2] - p[:2], axis=1)))
        u = j / self.M * self.perim(p[2])
        return u if u <= self.perim(p[2]) / 2 else u - self.perim(p[2])

    def seams_u(self, z, f_out, f_frm):
        """u of the face seams (+/-) and of the frame-panel seams (+/-) at height z."""
        lo, lb = self.outer_half(z), self.frame_half(z)
        return (0.5 - f_out) * lo, lo / 2 + f_frm * lb

    # ------------------------------------------------------------------ meshes
    def body_mesh(self, r_bottom=25.0, n_round=6):
        rings = [self.T[k, :-1] for k in range(len(self.z))]
        # rounded bottom edge: rings over the first r_bottom mm, pulled in toward the ring centre
        zb = self.z[0]
        new = []
        for i in range(n_round):
            ph = np.pi / 2 * i / n_round
            ins = r_bottom * (1 - np.sin(ph))
            zz = zb + r_bottom * (1 - np.cos(ph))
            p = self.pt(np.linspace(0, self.perim(zz), self.M, endpoint=False), np.full(self.M, zz))
            cc = self.center(zz)
            R = p - cc
            rad = np.linalg.norm(R[:, :2], axis=1, keepdims=True)
            R[:, :2] *= np.clip(rad - ins, 1, None) / rad
            new.append(cc + R)
        keep = [r for r, z in zip(rings, self.z) if z > zb + r_bottom + 1e-6]
        return G.loft(np.array(new + keep), cap_start=True, cap_end=True)


def _shard(surf, poly, thick, lift=0.5, max_edge=10.0):
    return G.conformal_plate(poly, lambda u, z: surf.pt(u, z), lambda u, z: surf.nrm(u, z),
                             thick=thick, lift=lift, max_edge=max_edge)


def build_teardrop_bag(p, g, hp, Part, crown_info, tubes, metrics, block, ribbon_on, mx):
    """Returns (parts, extras). extras: lid_vol, side_pocket_vol, pull."""
    bag_g = g["bag"]
    prof = bag_g["profile"]
    n_out, n_frm = prof["n_out"], prof["n_frm"]
    full = TeardropSurface(prof["stations"], n_out, n_frm)
    roll = TeardropSurface(prof.get("stations_rolled") or prof["stations"], n_out, n_frm)
    seams = bag_g.get("seams", {})
    f_out = seams.get("face_side_fraction_of_outer_half_arc", 0.17)
    f_frm = seams.get("gore_fraction_of_frame_half_arc", 0.12)
    pull = float(p["haul_pullback_y"] or bag_g.get("haul_mode_pullback_y_max", 250.0))
    HAUL = (0.0, pull, 0.0)
    rt_cfg = bag_g.get("rolltop", {})
    BE = (0.0, 260.0, 0.0)
    sh_t = p["shard_thick"]
    parts = []
    z0 = float(full.z[0])
    z_top, z_roll = float(full.z[-1]), float(roll.z[-1])

    # ------------------------------------------------------------------ body (rolled = display, full = counted)
    body_r = roll.body_mesh()
    body_f = full.body_mesh()
    vol_f = G.volume_mm3(body_f) / 1e6
    vol_r = G.volume_mm3(body_r) / 1e6
    from .params import CU_IN_TO_L
    metrics.update({"bag_volume_l": vol_f, "bag_volume_cu_in": vol_f / CU_IN_TO_L,
                    "bag_volume_rolled_l": vol_r,
                    "target_volume_l": p["target_volume_l"],
                    "volume_error_pct": 100 * (vol_f / p["target_volume_l"] - 1),
                    "design_volume_l": (g.get("volumes") or {}).get("main_bag_L"),
                    "bag_dims_mm": [float(bag_g["width_x"]), float(bag_g["height_z"]), float(bag_g["depth_y"])],
                    "bag_type": "teardrop_rolltop"})
    parts.append(Part("bag_body", body_r, "body", "bag", modes=BAGM, explode=BE, haul=HAUL, variant="rolled",
                      label=f"Main bag, rolled down ({vol_r:.0f} L)"))
    parts.append(Part("bag_body_full", body_f, "body", "bag", modes=BAGM, explode=BE, haul=HAUL, variant="full",
                      label=f"Main bag, collar unrolled to the fill line ({vol_f:.1f} L)"))

    # ------------------------------------------------------------------ bottom skin (500D) + seam piping
    zz = np.linspace(z0 + 0.5, z0 + 45, 6)
    rings = []
    for z in zz:
        uu = np.linspace(0, full.perim(z), 160, endpoint=False)
        rings.append(full.pt(uu, z) + full.nrm(uu, z) * 1.3)
    c0 = full.center(z0)
    base = np.array(rings)
    bottom = G.loft(np.vstack([[(base[0] - c0) * 0.985 + c0 + [0, 0, -0.9]], base]), cap_start=True, cap_end=True)
    parts.append(Part("bag_bottom", bottom, "tpu", "bag", modes=BAGM, explode=(0, 260, -40), haul=HAUL,
                      label="Bottom wrap (500D)"))
    pip = []
    z_dome = z_roll - float(rt_cfg.get("dome_mm", 180.0))
    zs_seam = np.linspace(z0 + 40, z_dome, 60)
    for sgn in (-1, 1):                                  # face/gore seams only (frame seams are hidden)
        us = np.array([full.seams_u(z, f_out, f_frm)[0] for z in zs_seam]) * sgn
        P = full.pt(us, zs_seam) + full.nrm(us, zs_seam) * 0.9
        pip.append(G.tube(P, 1.8, n=10, tile=G.TILE_MM))
    parts.append(Part("bag_trim", G.concat(pip), "trim", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="Seam piping (face/gore/frame seams)"))

    # ------------------------------------------------------------------ SPINE: diagonal stretch band + zip
    dg = bag_g["diagonal"]
    zip3 = np.asarray(dg["zip_line_3d"], float)
    low3 = np.asarray(dg["band_lower_edge_3d"], float)
    zip_uz = np.array([[full.u_of(q), q[2]] for q in zip3])
    low_uz = np.array([[full.u_of(q), q[2]] for q in low3])
    band_poly = Polygon(np.vstack([zip_uz, low_uz[::-1]])).buffer(0)
    band = _shard(full, band_poly, 3.2, lift=0.4, max_edge=12)
    parts.append(Part("diagonal_band", band, "harness", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="SPINE stretch band (overload / bow cam / pole pocket)"))
    # camo binding along the band mouth (sits over the zip) + slider pulls at both ends
    zl = G.catmull_rom(zip_uz, 6)
    Pm = full.pt(zl[:, 0], zl[:, 1])
    Nm = full.nrm(zl[:, 0], zl[:, 1])
    binding = G.ribbon(Pm + Nm * 4.2, 20.0, 3.0, Nm, step=6)
    # ------------------------------------------------------------------ camo accents
    shards = [binding]
    for sgn in (-1, 1):                                   # lower corners, wrapping face -> gore
        us = full.seams_u(z0 + 60, f_out, f_frm)[0]
        poly = Polygon([(us - 135, z0 + 2), (us + 80, z0 + 2), (us + 105, z0 + 55), (us + 40, z0 + 120),
                        (us - 40, z0 + 175), (us - 135, z0 + 120)])
        if sgn < 0:
            poly = Polygon([(-x, y) for x, y in poly.exterior.coords])
        shards.append(_shard(full, poly, sh_t, max_edge=10))
    # cam cup: the band's closed lower end, reinforced; merges visually with the right lower-corner camo
    u_cup, z_cup = zip_uz[0]
    from shapely.geometry import box as _box
    cup = _box(u_cup - 260, z0 + 60, u_cup + 60, z_cup - 55).intersection(band_poly.buffer(4)).buffer(0)
    if not cup.is_empty:
        shards.append(_shard(full, cup, sh_t, lift=3.8, max_edge=8))
    parts.append(Part("bag_shards", G.concat(shards), "camo", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="Camo: band mouth binding, lower corners, cam cup"))
    pulls = []
    for q, nn in ((Pm[2], Nm[2]), (Pm[-3], Nm[-3])):
        pulls.append(block(q + nn * 9, (10, 10, 22), e=0.5))
    parts.append(Part("zip_pulls", G.concat(pulls), "hardware", "bag", modes=BAGM, explode=BE, haul=HAUL,
                      label="Diagonal zip sliders (2)"))

    # ------------------------------------------------------------------ rain-fly pocket + lash tabs + bag-frame link
    extras = []                                           # rain fly lives in a base pocket (zip on the bottom's aft edge)
    for sgn in (-1, 1):
        for zt_ in (600.0,):
            uc = sgn * full.outer_half(zt_) / 2
            extras.append(_shard(full, Polygon([(uc - 11, zt_ - 18), (uc + 11, zt_ - 18), (uc + 11, zt_ + 18),
                                                (uc - 11, zt_ + 18)]), 2.2, max_edge=8))
    parts.append(Part("bag_boot_tabs", G.concat(extras), "tpu", "bag", modes=BAGM, explode=(0, 300, 0), haul=HAUL,
                      label="Hypalon lash tabs / muzzle keepers"))
    link = []
    for s in (-1, 1):
        for z_ in (60.0, 330.0):
            link.append(block([s * 112, float(np.interp(z_, full.z, full.yf)) - 4, z_], (16, 8, 26), e=0.4))
    parts.append(Part("bag_link", G.concat(link), "hardware", "bag", modes=("pack",), explode=BE,
                      label="Bag-frame link: hinge pins + toggles (LINK family)"))

    # ------------------------------------------------------------------ floating side pockets
    spg = g["side_pockets"]
    swb, swt, sph, bell = spg["face_bottom_w"], spg["face_top_w"], spg["height"], spg["bellows"]
    spz0 = spg["position"]["z_bottom"]
    pockets = []
    for s in (-1, 1):
        def surf(a_, b_, s=s):
            z = spz0 + sph * b_
            w = swb + (swt - swb) * b_
            uc = s * full.outer_half(z) / 2
            return full.pt(uc + (a_ - 0.5) * w, z)

        def nrm(a_, b_, s=s):
            z = spz0 + sph * b_
            w = swb + (swt - swb) * b_
            uc = s * full.outer_half(z) / 2
            return full.nrm(uc + (a_ - 0.5) * w, z)
        th = lambda a_, b_: 4.0 + 0.75 * bell * G.bump(a_, 0.55) * G.bump(0.04 + 0.92 * b_, 0.45) * (1 - 0.25 * b_)  # noqa: E731
        pockets.append(G.patch_shell(surf, nrm, (0, 1), (0, 1), th, inset=2.0, nu=36, nv=40))
        uu = np.linspace(0, 1, 36)
        rim = surf(uu, np.ones_like(uu)) + nrm(uu, np.ones_like(uu)) * (th(uu, np.ones_like(uu)) + 1)[:, None]
        pockets.append(G.tube(rim, 3.0, n=10, tile=G.TILE_MM))
    side_pocket_vol = G.volume_mm3(pockets[0]) / 1e6
    parts.append(Part("side_pockets", G.concat(pockets), "pocket", "bag", modes=BAGM, explode=(0, 260, 0), haul=HAUL,
                      label="Floating side pockets (wraps run underneath)"))

    # ------------------------------------------------------------------ roll-top (rolled + full)
    rt = bag_g.get("rolltop", {})
    r_roll = float(rt.get("roll_diameter_mm", 50.0)) / 2

    def rolltop(S, zt, name, variant, lab):
        k = len(S.z) - 1
        a_t = float(S.a[k])
        yc = float(S.yf[k] + S.d[k] / 2)
        zr = zt - r_roll + 6
        roll_ = G.capsule_between([-(a_t - 6), yc, zr], [a_t - 6, yc, zr], r_roll, r_roll, n=36)
        straps, bk = [], []
        zc = zt - float(rt.get("clip_z_below_fill_line_mm", 230.0))
        for s in (-1, 1):
            zs_ = np.linspace(zr - 8, zc, 14)
            us = s * S.outer_half(zs_) / 2 - s * 18
            P = S.pt(us, zs_) + S.nrm(us, zs_) * 2.4
            P[0] = [s * (a_t - 4), yc, zr]
            straps.append(G.ribbon(P, 25.0, 2.2, S.nrm(us, zs_), step=6))
            bk.append(block(P[-1] + S.nrm(us[-1:], zs_[-1:])[0] * 3.5, (14, 8, 34), e=0.35))
        return [Part(name, roll_, "camo", "bag", modes=BAGM, explode=BE, haul=HAUL, variant=variant, label=lab),
                Part(name + "_straps", G.concat(straps + bk), "webbing", "bag", modes=BAGM, explode=BE, haul=HAUL,
                     variant=variant, label="Roll-top clips (ROLL family)")]
    parts += rolltop(roll, z_roll, "rolltop", "rolled", "Roll-top, rolled down (camo hem band)")
    parts += rolltop(full, z_top, "rolltop_full", "full", "Roll-top at the 85.2 L fill line")

    # ------------------------------------------------------------------ optional lid / hip pack (accessory)
    lg = g["lid"]
    lw_, ld_ = lg["footprint"]
    lh, lr = lg["height"], lg["corner_radius"]
    lz0 = z_roll - 6
    lyc = float(roll.yf[-1] + roll.d[-1] / 2) + 10
    zs_l, ins = [], []
    for k in range(8):
        ph_ = np.pi / 2 * k / 7
        zs_l.append(lz0 + 12 * (1 - np.cos(ph_)))
        ins.append(12 * (1 - np.sin(ph_)))
    for k in range(10, -1, -1):
        ph_ = np.pi / 2 * k / 10
        zs_l.append(lz0 + lh - 30 * (1 - np.cos(ph_)))
        ins.append(30 * (1 - np.sin(ph_)))
    lrings = []
    for z, i in zip(zs_l, ins):
        pp, _ = G.outline_xz(lw_, ld_, lyc - ld_ / 2, lr, lr, inset=i, n_arc=12, n_edge=20)
        lrings.append(np.column_stack([pp[:, 0], pp[:, 1], np.full(len(pp), z)]))
    lid = G.loft(np.array(lrings), cap_start=True, cap_end=True)
    lid_vol = G.volume_mm3(lid) / 1e6
    parts.append(Part("lid", lid, "body", "accessory", modes=BAGM, explode=(0, 280, 190), haul=HAUL, variant="lid",
                      label="Optional lid / hip pack (accessory, short fixed straps)"))

    # ------------------------------------------------------------------ v3.1: NO SHELF (owner). Legacy geometry still draws the lip
    sg = g.get("load_shelf")
    shz, shy = 50.0, 14.0                      # quarter rests in the V at the bag-bottom hinge pins, against the frame
    if sg:
        sw_, sd_ = sg["floor_w_x"], sg["floor_d_y"]
        shz, shy = sg["z"], sg["y_from"]
        from shapely.geometry import box
        spoly = box(-sw_ / 2, 0, sw_ / 2, sd_).buffer(-14).buffer(14, quad_segs=10)
        shelf = G.plate(spoly, [0, shy, shz + 3], [1, 0, 0], [0, 1, 0], 5.0, tile=G.TILE_MM)
        parts.append(Part("load_shelf", shelf, "tpu", "shelf", explode=(0, 60, -90),
                          label=f"Fold-down shelf lip {sw_:.0f} x {sd_:.0f}"))

    # ------------------------------------------------------------------ quarter proxy (haul modes)
    q = p["quarter"]
    qz0, qy0 = shz + 6.5, shy + 6
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
                      label="Bone-in elk hindquarter proxy in a game bag (no shelf: rests in the V, strapped to the frame)"))
    parts.append(Part("quarter_bone", bone, "bone", "haul", modes=HAULM, explode=QE))
    qinfo = np.array(qinfo)

    def q_half(z):
        return float(np.interp(z, qinfo[:, 0], qinfo[:, 1])) if qinfo[0, 0] <= z <= qinfo[-1, 0] else 0.0

    # internal meat harness (v3.1): IM1-IM3 hook to the frame stubs and cam the quarter / game bags tight against the
    # frame. Inside the bag in carry mode (hidden); shown in the haul modes routed stub-to-stub round the load.
    mh = g.get("meat_harness") or {}
    if mh:
        ims, imh = [], []
        for st_ in mh["straps"]:
            aR = np.array(hp[st_["anchors"][0]], float)
            zm = float(np.clip(st_["z"], qinfo[0, 0] + 5, qinfo[-1, 0] - 5))
            a_ = np.interp(zm, qinfo[:, 0], qinfo[:, 1]); b_ = np.interp(zm, qinfo[:, 0], qinfo[:, 2])
            c_ = np.interp(zm, qinfo[:, 0], qinfo[:, 3])
            th_ = np.linspace(0.0, np.pi, 50)
            cth, sth = np.cos(th_), np.sin(th_)
            qp = np.column_stack([(a_ + 3.5) * np.sign(cth) * np.abs(cth) ** (2 / 2.3), c_ + (b_ + 3.5) * np.abs(sth) ** (2 / 2.3),
                                  np.full(50, st_["z"])])
            qp = qp[qp[:, 1] > aR[1] + 15]
            Pq = np.vstack([[[aR[0] + 6, aR[1], st_["z"]]], qp, [[-aR[0] - 6, aR[1], st_["z"]]]])
            nq = Pq - np.column_stack([np.zeros(len(Pq)), np.full(len(Pq), c_), Pq[:, 2]])
            ims.append(ribbon_on(Pq, nq, 38.0, 2.6, smooth=False))
            for sgn in (-1, 1):                                       # sliding-gate hooks at both stub eyes
                imh.append(block([sgn * (aR[0] + 4), aR[1] + 22, st_["z"]], (10, 16, 40), e=0.5))
            k = int(len(qp) * 0.25)                                    # cam on the wearer's-right leg
            imh.append(block(qp[k] + (qp[k] - [0, c_, st_["z"]]) / max(np.linalg.norm(qp[k][:2] - [0, c_]), 1) * 6,
                             (12, 18, 46), e=0.35))
        parts.append(Part("meat_straps", G.concat(ims), "meat_strap", "haul", modes=HAULM, explode=QE,
                          label="Internal meat harness IM1-IM3 (38 mm, MEAT family): stub-to-stub round the load"))
        parts.append(Part("meat_hardware", G.concat(imh), "titanium", "haul", modes=HAULM, explode=QE,
                          label="MEAT hooks + cams"))

    # ------------------------------------------------------------------ haul wraps (= compression)
    wraps = g.get("haul_wraps") or []

    def wrap_path(S, zR, zL, ayR, ayL, dy=0.0, meat=False):
        """Frame anchor R -> bag frame corner R -> round the outer face (rising from zR to zL, a helix
        when the anchors differ) -> frame corner L -> anchor L. In meat mode the bag is dy aft and the
        strap runs past the quarter's sides."""
        zm = (zR + zL) / 2
        u_fc = S.outer_half(zm) / 2 + f_frm * S.frame_half(zm) * 0.6
        us = np.linspace(u_fc, -u_fc, 90)
        zs = np.linspace(zR, zL, 90)
        Pw = S.pt(us, zs) + S.nrm(us, zs) * 2.6 + np.array([0, dy, 0])
        Nw = S.nrm(us, zs)
        head, tail, hn, tn = [], [], [], []
        for s, lst, nl, z, ay, end in ((1, head, hn, zR, ayR, Pw[0]), (-1, tail, tn, zL, ayL, Pw[-1])):
            lst.append([s * 123.0, ay, z]); nl.append([s, 0, 0.0])
            if meat:
                for y in np.linspace(ay + 40, end[1] - 30, 6):
                    lst.append([s * max(q_half(z) + 4, abs(end[0])), y, z]); nl.append([s, 0, 0.0])
        P = np.vstack([head, Pw, tail[::-1]])
        Nn = np.vstack([hn, Nw, tn[::-1]])
        return P, Nn

    def hooks(zR, zL, ayR, ayL):
        return [block([115.0 + 16, ayR + 6, zR], (8, 14, 30), e=0.4),        # ladder lock (right anchor)
                block([-115.0 - 16, ayL + 6, zL], (10, 10, 34), e=0.6)]        # G-hook (left anchor)

    def anchor_of(w, side):
        name = w.get(f"anchor_{side}") or w.get("anchor", "")
        if name in hp:
            return float(hp[name][1]), float(hp[name][2])
        return -5.0, float(w.get(f"z_{side}_at_19in", w["z_at_19in"]))
    fixed = [w for w in wraps if not str(w.get("anchor_R", w.get("anchor", ""))).startswith("crown")]
    crown_w = [w for w in wraps if str(w.get("anchor_R", w.get("anchor", ""))).startswith("crown")]
    W_c, W_h, HW = [], [], []
    for w in fixed:
        (ayR, zR), (ayL, zL) = anchor_of(w, "R"), anchor_of(w, "L")
        P, Nn = wrap_path(roll, zR, zL, ayR, ayL)
        W_c.append(G.ribbon(P, 25.0, 2.4, Nn, step=8))
        P, Nn = wrap_path(roll, zR, zL, ayR, ayL, dy=pull, meat=True)
        W_h.append(G.ribbon(P, 25.0, 2.4, Nn, step=8))
        HW += hooks(zR, zL, ayR, ayL)
    parts.append(Part("compression_straps", G.concat(W_c), "webbing", "bag", modes=("pack",), explode=(0, 300, 0),
                      label="Haul wraps W1/W2 = compression, angled with the SPINE (HAUL family)"))
    parts.append(Part("haul_wraps_meat", G.concat(W_h), "webbing", "haul", modes=("pack_haul",), explode=(0, 120, 0),
                      label="Haul wraps around meat + pulled-back bag"))
    parts.append(Part("buckles", G.concat(HW), "titanium", "bag", modes=BAGM, explode=(0, 0, 0),
                      label="G-hooks (left) + ladder locks (right) at the frame anchors"))
    for tin, cs in crown_info.items():
        for w in crown_w:
            z = float(cs["crown_top_z"])
            ay = float(cs["lifter_anchor_R"][1])
            S = roll if z < z_roll - 60 else full
            P, Nn = wrap_path(S, z, z, ay, ay)
            parts.append(Part(f"crown_wrap@t{tin:g}", G.concat([G.ribbon(P, 25.0, 2.4, Nn, step=8)] + hooks(z, z, ay, ay)),
                              "webbing", "bag", torso=tin, modes=("pack",), explode=(0, 300, 0),
                              label="Haul wrap W3 on the crown top bar"))
            P, Nn = wrap_path(S, z, z, ay, ay, dy=pull, meat=True)
            parts.append(Part(f"crown_wrap_meat@t{tin:g}", G.ribbon(P, 25.0, 2.4, Nn, step=8), "webbing", "haul",
                              torso=tin, modes=("pack_haul",), explode=(0, 120, 0)))
    # frame-only: W1/W2 round the quarter's aft face, anchor to anchor
    wf = []
    for w in fixed:
        (ayR, zR), (ayL, zL) = anchor_of(w, "R"), anchor_of(w, "L")
        zl_ = (zR + zL) / 2
        zq = np.clip(zl_, qinfo[0, 0] + 5, qinfo[-1, 0] - 5)
        a_ = np.interp(zq, qinfo[:, 0], qinfo[:, 1])
        b_ = np.interp(zq, qinfo[:, 0], qinfo[:, 2])
        c_ = np.interp(zq, qinfo[:, 0], qinfo[:, 3])
        th_ = np.linspace(0.0, np.pi, 50)
        cth, sth = np.cos(th_), np.sin(th_)
        qx = (a_ + 3) * np.sign(cth) * np.abs(cth) ** (2 / 2.3)
        qy = c_ + (b_ + 3) * np.abs(sth) ** (2 / 2.3)
        qz = zR + (zL - zR) * th_ / np.pi
        qp = np.column_stack([qx, qy, qz])
        keep = qp[:, 1] > max(ayR, ayL) + 20
        Pq = np.vstack([[[123.0, ayR, zR]], qp[keep], [[-123.0, ayL, zL]]])
        nq = Pq - np.column_stack([np.zeros(len(Pq)), np.full(len(Pq), c_), Pq[:, 2]])
        wf.append(ribbon_on(Pq, nq, 25.0, 2.6, smooth=False))
    parts.append(Part("wing_straps_frame", G.concat(wf), "webbing", "haul", modes=("frame_haul",), explode=QE,
                      label="Haul wraps around the quarter (frame-only)"))
    return parts, {"lid_vol": lid_vol, "side_pocket_vol": side_pocket_vol, "pull": pull}
