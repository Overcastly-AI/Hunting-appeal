"""Team E FORM, bag design competition (designs/pack_5200/bag_comp/RULES.md): **CHERT**.

A styling-led main bag for the 5200 pack on the H1 frame. Name: chert, the flint-family stone that knaps
into facets (original: no pack brand found under it; 'Knap' was dropped because a 'Knap Sacks' backpack trademark
exists; docs/research/bag_comp_form.md).

The idea in one line: the bag's two aft vertical corners are cut off by a 45-degree-ish **chamfer blade** that tapers
from 60 mm at the floor to 32 mm at the collar seam. The blades are the owner's camo, the rest of the bag is solid, and
the door zip runs in the blade | aft-face seam, so **the panel line, the camo break and the door are one line**.

Construction (all seams straight on the flat pattern except the two R 55 door corners, same as CORRIE):

* B-01   frame-side panel, ULTRA 200 (unchanged frame interface: hinge eyes/B-18, IM ports, B-17/B-23, B-20, B-22 on B-02h)
* B-03   side gusset x2 (330D solid) with a camo **fang** inset SH-F (lower-front triangle, one straight seam)
* B-02u  **blade U**: both chamfer blades + the 75 mm kick strip under the door, one camo piece (630D printable),
         creased (not seamed) at the facet lines; the inner edge carries the #10 door zip
* B-02door door (330D solid), the whole aft face z 110 -> 650, legs on the creases, R 55 bottom corners
* B-02h  hinge band (330D solid), guy tabs B-22 at x +/-149, z 695 (as CORRIE)
* B-05   floor, 500D, a hexagon (the boxed gusset carries the chamfers into the base)
* B-06 / B-06f / B-07 roll-top collar, as CORRIE B.2
* wings M-01, pouch L-21..23, pockets IMP-1..8, fly: CORRIE B.2 carried over (they meet the access rule), wings get
  the camo bar SH-06 as before.

Every number below is from CORRIE (designs/pack_5200/concepts/corrie.py, the measured baseline), a material record,
a calculation in this file, or an ASSUMPTION stated next to it.

    python designs/pack_5200/bag_comp/form/form.py          # envelope, volume, CG, mass, metrics -> stdout + form_numbers.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACK = ROOT / "designs" / "pack_5200"
for p in (str(ROOT), str(PACK), str(PACK / "concepts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit import materials as MAT  # noqa: E402

NAME = "CHERT"
TEAM = "E"

# ------------------------------------------------------------------------- envelope (DECISIONS of this entry)
A_BOT = 130.0       # half-width at the floor (CORRIE 136.2): DECISION, a slightly stronger V taper in rear view
D_BOT = 170.0       # depth at the floor, as CORRIE rev B (cloth-sim proven CG)
D_NOM = 270.0       # nominal depth at the shoulder crease, as CORRIE rev B
CH_BOT = (60.0, 55.0)   # chamfer blade (cx across, cy deep) at the floor: DECISION (door width at z 110 stays >= 160 mm)
CH_TOP = (32.0, 26.0)   # at the collar seam: DECISION (blade tapers to a point-like stripe)
DOOR = {"z_lo": 110.0, "z_hinge": 650.0, "r": 55.0, "inset": 45.0}   # inset only feeds CORRIE helper code; the real
#                                                                     door edge is the blade crease (inset = cx(z))
B22_X, B22_Z = CO.B22_X, CO.B22_Z
FANG = {"z_frame": 60.0, "z_aft": 260.0}   # SH-F camo inset on the gusset: line from the frame edge at z 60 to the
#                                            blade edge at z 260 (DECISION; below the wing, z 150 at its frame end)
TARGET_SIM_L = 86.0    # what the sewn bag should stuff to (85 +/- 3 L rule); see rule_target_L()
CAMO = "polyester_ht_630d_printable"
STRAP_SNACK_G = 17.0   # ASSUMPTION: IMP-6 11.1 g (90 x 175 face) x face-area ratio 1.47 = 16.3 g, booked 17 g with the bellows (form_loadout.SNACK)
SOLID = "cordura_330d_nylon66"


class Knap(BC.Concept):
    """CORRIE-family box envelope with tapered chamfered aft corners. Body below the collar seam is exact (planar
    facets); above it the stuffed collar follows the shared dome law (bag_concepts.dome_section, calibrated on SPINE)."""

    def a(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        return np.interp(z, [BC.Z0, BC.Z_SH], [self.a_bot, BC.A_MAX])

    def ch(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        t = np.clip((z - BC.Z0) / max(self.z_c - BC.Z0, 1.0), 0, 1)
        return CH_BOT[0] + (CH_TOP[0] - CH_BOT[0]) * t, CH_BOT[1] + (CH_TOP[1] - CH_BOT[1]) * t

    def area(self, z):
        cx, cy = self.ch(z)
        return 2 * self.a(z) * self.depth(z) - cx * cy

    def ring2d(self, z, M=None):
        a = float(self.a([z])[0])
        yf = float(BC.y_frame([z])[0])
        d = float(self.depth([z])[0])
        cx, cy = (float(v[0]) for v in self.ch([z]))
        return np.array([[-a, yf], [a, yf], [a, yf + d - cy], [a - cx, yf + d], [-(a - cx), yf + d], [-a, yf + d - cy]])

    def profile(self, z_c=None, n_body=240, n_dome=80):
        z_c = self.z_c if z_c is None else z_c
        old = self.z_c
        self.z_c = z_c
        zb = np.unique(np.r_[np.linspace(BC.Z0, z_c, n_body), BC.Z_SB, BC.Z_SH])
        zb = zb[zb <= z_c]
        k = self.area(zb) / (2 * self.a(zb) * self.depth(zb))
        rows = [np.column_stack([zb, self.a(zb), BC.y_frame(zb), self.depth(zb), k])]
        a_c, d_c, k_c = float(self.a([z_c])[0]), float(self.depth([z_c])[0]), float(k[-1])
        zd = np.linspace(z_c, z_c + self.dome_h, n_dome)[1:]
        a, d, kk = BC.dome_section((zd - z_c) / self.dome_h, a_c, d_c, k_c)
        rows.append(np.column_stack([zd, a, BC.y_frame(zd), d, kk * BC.DOME_CAL]))
        self.z_c = old
        return np.vstack(rows)

    def cg(self, n=161):
        """Uniform-fill centroid (y, z): chamfered polygon below the collar seam, scaled dome section above it."""
        st = self.profile()
        zs = np.linspace(st[0, 0], st[-1, 0], n)
        V = Sy = Sz = 0.0
        for z in zs:
            if z <= self.z_c:
                P = self.ring2d(z)
                A, cy = BC.poly_area_centroid(P)
            else:
                a, yf, d, kk = (float(np.interp(z, st[:, 0], st[:, j])) for j in (1, 2, 3, 4))
                A, cy = 2 * a * d * kk, yf + 0.5 * d
            V += A
            Sy += A * cy
            Sz += A * z
        return Sy / V, Sz / V


_CORRIE_MAKE = CO.make     # kept: other CHERT scripts point CO.make at CHERT inside their own process


def corrie_ref():
    return _CORRIE_MAKE()


# Pilot cloth sim (2026-11-10, 19 in, h 40, scenario corrie_PR19c with CHERT's pieces, collar seam z 738.0): the rule
# volume 73.81 L stuffed to 82.5 L in the fill case (86.0 L packed). The chamfers bulge less than CORRIE's box corners
# (CORRIE: 75.87 -> 88.4 L), so the calibration uses CHERT's own ratio. Pilot kept in outputs/clothsim/chert_pilot.
PILOT = {"rule_L": 73.81, "fill_L": 82.5}


def rule_target_L() -> float:
    """Design-rule volume that should stuff to TARGET_SIM_L (fill case), by the pilot run's sim / rule ratio.
    ASSUMPTION: the ratio holds for a ~4 % taller body (checked by the final runs)."""
    return TARGET_SIM_L / (PILOT["fill_L"] / PILOT["rule_L"])


def make() -> Knap:
    c = Knap(key="knap", name=NAME, kind="box", a_bot=A_BOT, d_bot=D_BOT, d_nom=D_NOM,
             tagline="Chamfer-blade box: camo blades on the aft corners carry the door zip; roll-top, wings, pouch",
             access="roll-top + #10 door zip in the blade | aft-face seams, z 110-650, + 2.7 L pouch")
    target = rule_target_L()
    lo, hi = BC.Z_SH + 1.0, 1200.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        c.z_c = mid
        lo, hi = (mid, hi) if c.volume_L(mid) < target else (lo, mid)
    c.z_c = round(0.5 * (lo + hi), 1)
    return c


# ------------------------------------------------------------------------- surface for the cloth sim
US = 600.0
G1, G2 = 0.25, 1.0 / 3.0      # q fractions: gusset 0..G1, blade G1..G2, aft face G2..1-G2, blade, gusset; frame 1..2


class KnapSurface:
    """(U, z) -> xyz on the chamfered box, q = U / 600 as huntkit/clothsim/corrie_bag.BoxSurface (q 1.5 = frame-face
    centre). Planar facets, so every region develops with ~0 strain."""

    def __init__(self, c: Knap):
        self.c = c

    def env(self, z):
        z = np.clip(np.asarray(z, float), BC.Z0, self.c.z_c)
        cx, cy = self.c.ch(z)
        return self.c.a(z), BC.y_frame(z), self.c.depth(z), cx, cy

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        q = np.mod(uv[:, 0] / US, 2.0)
        a, yf, d, cx, cy = self.env(uv[:, 1])
        x, y = np.zeros_like(q), np.zeros_like(q)
        segs = [  # (q0, q1, start(x, y), end(x, y)) as functions of the envelope
            (0.0, G1, (a, yf), (a, yf + d - cy)),
            (G1, G2, (a, yf + d - cy), (a - cx, yf + d)),
            (G2, 1 - G2, (a - cx, yf + d), (-(a - cx), yf + d)),
            (1 - G2, 1 - G1, (-(a - cx), yf + d), (-a, yf + d - cy)),
            (1 - G1, 1.0, (-a, yf + d - cy), (-a, yf)),
            (1.0, 2.0, (-a, yf), (a, yf)),
        ]
        for q0, q1, (xa, ya), (xb, yb) in segs:
            m = (q >= q0) & (q < q1) if q1 < 2.0 else (q >= q0)
            t = (q[m] - q0) / (q1 - q0)
            xa_, ya_ = np.broadcast_to(xa, q.shape)[m], np.broadcast_to(ya, q.shape)[m]
            xb_, yb_ = np.broadcast_to(xb, q.shape)[m], np.broadcast_to(yb, q.shape)[m]
            x[m] = xa_ + (xb_ - xa_) * t
            y[m] = ya_ + (yb_ - ya_) * t
        return np.column_stack([x, y, uv[:, 1]])

    def u_aft(self, x, z):
        a = float(self.c.a([min(z, self.c.z_c)])[0])
        cx = float(self.c.ch([min(z, self.c.z_c)])[0][0])
        w = a - cx
        return US * (G2 + (1 - 2 * G2) * (w - x) / (2 * w))


def door_uv(S: KnapSurface, step=3.0):
    """Door zip in (U, z), CCW on the door: down the LEFT leg (U = 400, the left blade crease), R 55 corner, across
    the bottom at z 110, R 55 corner, up the RIGHT leg (U = 200)."""
    H = DOOR
    zl, zh, r = H["z_lo"], H["z_hinge"], H["r"]
    uL, uR = US * (1 - G2), US * G2
    # corner radius in U units at the corner height (aft face is linear in x)
    w = float(S.c.a([zl + r])[0] - S.c.ch([zl + r])[0][0])
    rU = r * (US * (1 - 2 * G2)) / (2 * w)
    pts = [(uL, z) for z in np.linspace(zh, zl + r, 40)]
    th = np.linspace(0, np.pi / 2, 14)
    pts += [(uL - rU + rU * np.cos(t), zl + r - r * np.sin(t)) for t in th[1:]]
    pts += [(uR + rU - rU * np.cos(t), zl + r - r * np.sin(t)) for t in th[::-1][:-1]]
    pts += [(uR, z) for z in np.linspace(zl + r, zh, 40)]
    out = [pts[0]]
    for p, q in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.ceil(np.hypot(q[0] - p[0], q[1] - p[1]) / step)))
        out += [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n) for k in range(1, n + 1)]
    return out


def _line(a, b, step=4.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
    return [tuple(a + (b - a) * i / n) for i in range(n + 1)]


def regions(c: Knap):
    """Sewn-piece regions in (U, z): {pid: [(edge name, [uv...]), ...]} (closed rings)."""
    S = KnapSurface(c)
    z0, zc, zh = BC.Z0, c.z_c, DOOR["z_hinge"]
    du = door_uv(S)
    u1, u2, u3, u4 = US * G1, US * G2, US * (1 - G2), US * (1 - G1)

    def rect(ua, ub, za, zb):
        return [("bottom", _line((ua, za), (ub, za))), ("right", _line((ub, za), (ub, zb))),
                ("top", _line((ub, zb), (ua, zb))), ("left", _line((ua, zb), (ua, za)))]
    return S, {
        "B-01": rect(US, 2 * US, z0, zc),
        "B-03": rect(0.0, u1, z0, zc),
        "B-02h": rect(u2, u3, zh, zc),
        "B-02door": [("hinge", _line(du[-1], du[0])), ("zip", du)],
        "B-02u": [("bottom", _line((u1, z0), (u4, z0))), ("outer_left", _line((u4, z0), (u4, zc))),
                  ("top_left", _line((u4, zc), (u3, zc))), ("blade_left", _line((u3, zc), du[0])),
                  ("zip", du[::-1][::-1]), ("blade_right", _line(du[-1], (u2, zc))),
                  ("top_right", _line((u2, zc), (u1, zc))), ("outer_right", _line((u1, zc), (u1, z0)))],
    }


# ------------------------------------------------------------------------- flat patterns + mass
def flat_pieces(c: Knap, spacing=20.0):
    """Develop each shell region: {pid: {"outline": (n,2) flat mm, "area_m2", "strain_p99", "fm"}}. The fang split
    line is mapped onto the gusset flat too."""
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    S, R = regions(c)
    out = {}
    for pid, edges in R.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        sp = 9.0 if pid == "B-02u" else spacing
        fm = develop_region(S, poly, spacing=sp, boundary_spacing=4.5 if pid == "B-02u" else 8.0, boundary_weight=100.0)
        uvb = np.array(ring + [ring[0]], float)
        flat = np.asarray(fm.map_uv(uvb))
        A = abs(Polygon(flat).area) / 1e6
        out[pid] = {"outline": flat, "area_m2": A, "strain_p99": fm.strain_stats()["p99_pct"], "fm": fm,
                    "edges": [(n, np.asarray(fm.map_uv(np.asarray(p, float)))) for n, p in edges]}
    # fang line on the gusset: from (frame edge, z 60) to (blade edge, z 260)
    fl = np.array([[0.0, FANG["z_frame"]], [US * G1, FANG["z_aft"]]])
    fl = np.vstack([fl[0] + (fl[1] - fl[0]) * t for t in np.linspace(0, 1, 30)])
    out["B-03"]["fang"] = np.asarray(out["B-03"]["fm"].map_uv(fl))
    # floor hexagon (exact: planar)
    a0, yf0, d0, cx0, cy0 = (float(np.asarray(v).ravel()[0]) for v in S.env([BC.Z0]))
    hexa = np.array([[-a0, 0], [a0, 0], [a0, d0 - cy0], [a0 - cx0, d0], [-(a0 - cx0), d0], [-a0, d0 - cy0]])
    out["B-05"] = {"outline": hexa, "area_m2": abs(Polygon(hexa).area) / 1e6, "strain_p99": 0.0}
    return out


def _gsm(mid):
    return MAT.load(mid).require("areal_density_gsm")


def _sa_area(outline, sa):
    from shapely.geometry import Polygon
    return Polygon(outline).buffer(sa, join_style=2).area / 1e6


def shell_mass(c: Knap, fp=None) -> dict:
    """Cut mass (outline + seam allowance) of the KNAP shell pieces, by the same records CORRIE uses."""
    from shapely.geometry import Polygon
    fp = fp or flat_pieces(c)
    sa = BC.SA_BODY
    rows = {}
    rows["B-01 frame-side panel (ULTRA 200)"] = _sa_area(fp["B-01"]["outline"], sa) * _gsm("challenge_ultra_200")
    # gusset with the camo fang inset: split the flat outline along the fang line
    g = Polygon(fp["B-03"]["outline"])
    fl = fp["B-03"]["fang"]
    low = Polygon(np.vstack([fl, [[fl[-1, 0] + 400, fl[-1, 1] - 400], [fl[0, 0] - 400, fl[0, 1] - 400]]])).buffer(0)
    fang = g.intersection(low)
    if fang.area > g.area / 2:      # orientation guard: the fang is the small part
        fang = g.difference(low)
    fang_cut = fang.buffer(sa, join_style=2).area / 1e6
    gus_cut = g.difference(fang).buffer(sa, join_style=2).area / 1e6
    rows["B-03 side gusset x2 (330D solid)"] = 2 * gus_cut * _gsm(SOLID)
    rows["SH-F gusset fang inset x2 (camo 630D)"] = 2 * fang_cut * _gsm(CAMO)
    rows["B-02u blade U (camo 630D)"] = _sa_area(fp["B-02u"]["outline"], sa) * _gsm(CAMO)
    rows["B-02door door (330D)"] = _sa_area(fp["B-02door"]["outline"], sa) * _gsm(SOLID)
    rows["B-02h hinge band (330D)"] = _sa_area(fp["B-02h"]["outline"], sa) * _gsm(SOLID)
    rows["B-05 hexagon floor (500D)"] = _sa_area(fp["B-05"]["outline"], sa) * _gsm("cordura_500d_nylon66")
    return {"rows": {k: round(v, 1) for k, v in rows.items()}, "total_g": round(sum(rows.values()), 1),
            "fang_area_m2": round(fang.area / 1e6, 4), "fang_seam_mm": round(float(np.linalg.norm(fl[-1] - fl[0])), 1)}


def collar_perimeter(c, z):
    P = c.ring2d(z)
    return float(np.sum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)))


def corrie_parts_g():
    """CORRIE B.2 build masses per piece group (corrie.build + bag_concepts.metrics), and the bag-system total."""
    c = corrie_ref()
    b = CO.build(c)
    m = BC.metrics(b)
    per = {p.piece_id: BC.piece_mass_g(p) for p, _ in b.pieces}
    bp = {d["id"]: d["mass_g"] for d in CO.bag_pockets(c)}
    fly_base = sum(r["mass_g_total"] for k, r in CO._panels().items() if k.startswith("F-01"))
    a_co = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in CO.OUTER_IDS) / 1e6
    fly = fly_base * a_co / CO.SPINE_OUTER_M2
    system = m["mass_g"]["total"] + sum(bp[k] for k in ("IMP-1", "IMP-2", "IMP-4", "IMP-6", "IMP-8")) + fly
    return {"build": b, "metrics": m, "per_piece_g": per, "pockets_g": bp, "fly_g": fly, "fly_base_g": fly_base,
            "outer_m2": a_co, "bag_system_g": round(system, 1), "c": c}


def knap_mass(c: Knap, fp=None, cr=None) -> dict:
    """KNAP bag system = CORRIE B.2 bag system with the shell, accents and collar re-computed for KNAP.
    Removed vs CORRIE: B-01, B-03, B-05, B-02u, B-02door, B-02h, SH-01a/b kick plates (the blade U is the kick plate),
    collar pieces re-scaled by perimeter x height. Added: KNAP shell incl. SH-F fangs. Door zip re-measured."""
    cr = cr or corrie_parts_g()
    fp = fp or flat_pieces(c)
    sm = shell_mass(c, fp)
    per = cr["per_piece_g"]
    gone = ["B-01", "B-03", "B-05", "B-02u", "B-02door", "B-02h", "SH-01a", "SH-01b"]
    removed = sum(per[k] for k in gone)
    # collar: B-06 / B-06f / B-07 / B-07s scale with the ring perimeter at the collar seam (height unchanged)
    cc = cr["c"]
    p_corrie = 2 * float(cc.a([cc.z_c])[0]) * 2 + 2 * float(cc.depth([cc.z_c])[0])
    p_knap = collar_perimeter(c, c.z_c)
    collar_ids = ("B-06", "B-06f", "B-07", "B-07s")
    collar_g = sum(per[k] for k in collar_ids)
    collar_delta = collar_g * (p_knap / p_corrie - 1.0)
    # door zip: #10 coil, length = the door | U seam on the developed door
    zip_len = door_zip_len(fp)
    zip10 = MAT.load("coil_zipper_10").require("mass_g_m")
    zip_delta = zip10 * (zip_len - cr["build"].extra["zip_door_mm"]) / 1000.0
    # fly scales with the outer shell (same G-2 rule as CORRIE)
    sa = BC.SA_BODY
    outer_cut_knap = sum(_sa_area(fp[k]["outline"], sa) * (2 if k == "B-03" else 1)
                         for k in ("B-03", "B-02u", "B-02door", "B-02h", "B-05"))   # cut areas, CORRIE's basis
    fly_knap = cr["fly_base_g"] * outer_cut_knap / CO.SPINE_OUTER_M2
    system = cr["bag_system_g"] + STRAP_SNACK_G - removed + sm["total_g"] + collar_delta + zip_delta + (fly_knap - cr["fly_g"])
    rows = [("CORRIE B.2 bag system (body group + IMP-1/2/4/6/8 + fly)", cr["bag_system_g"]),
            ("- CORRIE shell B-01/B-03x2/B-05/B-02u/door/B-02h + SH-01a/b kick plates", -removed),
            ("+ CHERT shell incl. camo blade U and SH-F fangs (developed flat pieces + 12 mm SA)", sm["total_g"]),
            (f"collar B-06/B-06f/B-07/B-07s x perimeter {p_knap:.0f}/{p_corrie:.0f} mm", collar_delta),
            (f"#10 door zip {zip_len:.0f} vs {cr['build'].extra['zip_door_mm']:.0f} mm", zip_delta),
            ("IMP-6R right-strap snack / GPS pocket (CHERT, form_loadout.SNACK)", STRAP_SNACK_G),
            ("rain fly re-scaled to the CHERT outer shell (G-2 rule)", fly_knap - cr["fly_g"])]
    return {"rows": [(n, round(g, 1)) for n, g in rows], "bag_system_g": round(system, 1), "shell": sm,
            "corrie_bag_system_g": cr["bag_system_g"], "zip_door_mm": round(zip_len, 1),
            "collar_perimeter_mm": round(p_knap, 1)}


def door_zip_len(fp) -> float:
    for n, P in fp["B-02door"]["edges"]:
        if n == "zip":
            return float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
    raise KeyError("zip")


def chamfer_floor_m(c: Knap) -> float:
    cx, cy = (float(v[0]) for v in c.ch([BC.Z0]))
    return math.hypot(cx, cy) / 1000.0


def door_width(c: Knap, z: float) -> float:
    return 2 * float(c.a([z])[0] - c.ch([z])[0][0])


def build_metrics(c: Knap, fp, km, cr=None) -> dict:
    """Build simplicity in CORRIE's own metric (bag_concepts.HOURS), as deltas on CORRIE B.2's measured build.
    Pieces: + 2 fangs (SH-F); - SH-01a, - SH-01b x2 (kick appliques gone, the blade U is the kick plate).
    Seams: + 2 fang seams (straight), + 2 blade | gusset seams replace CORRIE's 2 aft-corner seams (same count);
    + the 2 blade | hinge-band vertical seams (z 650 -> collar) replace CORRIE's horizontal surround tops (same count),
    floor gets 2 more edges (hexagon): + 2 short straight seams; applique edge: the kick plates' 1.2 m less."""
    cr = cr or corrie_parts_g()
    m = cr["metrics"]
    H = BC.HOURS
    b = cr["build"]
    app_kick = sum(BC._perim(p) * p.quantity for p in b.appliques if p.piece_id in ("SH-01a", "SH-01b")) / 1000
    fang_m = 2 * km["shell"]["fang_seam_mm"] / 1000
    zip_corrie = b.extra["zip_door_mm"]
    d_hours = {
        "cutting": (2 - 3) * H["cut_piece"],
        "straight seams": (fang_m + 2 * chamfer_floor_m(c)) * H["straight_m"],   # fangs + 2 floor chamfer edges
        "pivots": 4 * H["pivot"],                        # 4 hexagon floor corners more than the rectangle
        "camo applique": -app_kick * H["applique_m"],
        "zips": (km["zip_door_mm"] - zip_corrie) / 1000 * H["zip_m"],
    }
    hours = m["hours_total"] + sum(d_hours.values())
    return {"pieces": m["cut_pieces"] + 2 - 3, "curved_seams": m["curved_seams"],
            "zip_mm_total": round(m["zip_length_m"] * 1000 + km["zip_door_mm"] - zip_corrie, 0),
            "beginner_hours": round(hours, 1), "delta_hours": {k: round(v, 2) for k, v in d_hours.items()},
            "corrie": {"pieces": m["cut_pieces"], "curved_seams": m["curved_seams"], "hours": m["hours_total"],
                       "zip_mm": m["zip_length_m"] * 1000},
            "applique_kick_m": round(app_kick, 2)}


def numbers() -> dict:
    c = make()
    cr = corrie_parts_g()
    cc = cr["c"]
    fp = flat_pieces(c)
    km = knap_mass(c, fp, cr)
    bm = build_metrics(c, fp, km, cr)
    yc, zc = c.cg()
    yc0, zc0 = cc.cg()
    zz = np.linspace(BC.Z0, c.z_c, 200)
    out = {
        "name": NAME, "z_collar": c.z_c, "z_fill": round(c.z_fill, 1), "fill_height_mm": round(c.z_fill - BC.Z0, 1),
        "fill_height_in": round((c.z_fill - BC.Z0) / 25.4, 1), "rule_volume_L": round(c.volume_L(), 2),
        "rule_target_L": round(rule_target_L(), 2), "corrie_rule_volume_L": round(cc.volume_L(), 2),
        "width_max_mm": round(2 * float(c.a(zz).max()), 1), "depth_max_mm": round(float(c.depth(zz).max()), 1),
        "uniform_cg": [round(yc, 1), round(zc, 1)], "corrie_uniform_cg": [round(yc0, 1), round(zc0, 1)],
        "door_width_mm": {str(int(z)): round(door_width(c, z), 0) for z in (110, 300, 500, 650)},
        "corrie_door_width_mm": {str(int(z)): round(CO.door_width(z, cc), 0) for z in (110, 300, 500, 650)},
        "strain_p99_pct": {k: round(v["strain_p99"], 3) for k, v in fp.items()},
        "piece_area_m2": {k: round(v["area_m2"], 4) for k, v in fp.items()},
        "mass": km, "build": bm,
    }
    return out


if __name__ == "__main__":
    n = numbers()
    (HERE / "form_numbers.json").write_text(json.dumps(n, indent=1, default=float))
    print(json.dumps({k: v for k, v in n.items() if k not in ("mass",)}, indent=1, default=float))
    for r in n["mass"]["rows"]:
        print(f"  {r[1]:8.1f}  {r[0]}")
    print("bag system g", n["mass"]["bag_system_g"], "CORRIE", n["mass"]["corrie_bag_system_g"])
