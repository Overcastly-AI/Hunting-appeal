"""BL-049: hinge fairlead for the sims' inboard-up eye force, and the US stations moved to their own lanes on frame lugs.

    python -m huntkit.gendesign.h1_lanes --fea       # hinge + lug cheek FEA, pin sizing (cached in outputs/h1_lanes)
    python -m huntkit.gendesign.h1_lanes --body      # H1 body checks (4 bases + the bag-off cradle) on the lanes body
    python -m huntkit.gendesign.h1_lanes --export    # print files (h1_buckling.export_print) + US test piece
    python -m huntkit.gendesign.h1_lanes             # slice checks, figures, md / json from the cached results

Ticket docs/backlog/BL-049-hinge-and-us-lanes.md:

1. **Hinge fairlead** (z 60). Every CORRIE F rev 3 fine sim row pulls the hinge eye inboard and up
   (``analysis/hinge_eye_vectors.json``). The sideways part is taken by the eye's edge pushing the inboard cheek's inner
   face (h1_fairleads.fairlead_fea rule), so the corner where that cheek meets the throat floor is the critical spot,
   and BL-047's m-1 relief groove (1 mm deep, beside each cheek) was cut right there. ``bag_attach.HINGE_GEOM`` is now
   the BL-049 hinge: cheeks 10 mm thick, reaching 27 mm up the stay above the pin (9 below, unchanged: the HE box sits
   under them), and the throat floor lowered 1 mm over the whole throat (gap under the pin 5.5 -> 6.5) in place of
   the groove. Checked at the bag's single hinge row, ``HINGE_ROW_N`` 1019 N factored, in every sim direction and in
   the rev C direction. Pin: 5 mm Ti-6Al-4V (was 7075-T6), yield at 1019 N, fatigue on the 2.4 g basis.
2. **US lanes.** BL-048 (``designs/pack_5200/us_route.py``, ``analysis/us_route.json`` station_move) moved US1 to an
   inboard lane at x +/-70 and US2 to an outboard lane at x +/-165. Each US fairlead (BL-045 ``eye_geom``, the
   ``imus_eye_envelope`` kept: pin, floor and tip heights as before) now stands on a printed **lug arm** from the stay.
   ``h1_fairleads.placed`` puts the US stations at the lane x; ``add_lugs`` unions the arms; the old US fairlead stubs
   on the stays are taken out of the voxel body (``strip_old_us``).
3. Body checks: h1_buckling.full_check (strength, fatigue, creep per kit and setting, member buckling, z 234 joint)
   on the lanes body, with every sim set's under-strap pin load moved to its lane (force + the moment of the offset at
   the stay node, ``lane_sets``), plus the bag-off cradle (720 N factored at each US pin) as its own sets.

Units mm, N, MPa, g. Frame coordinates: x lateral (R side +), y towards the bag, z up from the stay feet.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_lanes.json"
DOC = ANALYSIS / "h1_lanes.md"
OUT = REPO / "outputs" / "h1_lanes"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL049_"
RHO_G_MM3 = 1.06e-3

# ---------------------------------------------------------------------------------------------------- published
# The moved US stations (BL-048 us_route.json station_move 'lanes_wide', checked there on the 15 / 19 / 23 in meat
# drapes). For BL-050 (pack-designer): import these, do not re-derive them. x is the pin's lateral position (mirror
# for L), z the pin height; the pin centre / floor / tip heights in y are the station's imus_eye_envelope values,
# measured from the stay surface at that z as before (us_route stations y_pin / y_floor / y_tip).
STAY_X = 115.0
US1_X, US1_Z = 70.0, 95.0          # inboard lane, 45 mm inboard of the stay axis
US2_X, US2_Z = 165.0, 142.0        # outboard lane, 50 mm outboard of the stay axis
LANE_X = {"us1": US1_X, "us2": US2_X}
LANE_Z = {"us1": US1_Z, "us2": US2_Z}
CHANNEL_ENTRY_X = {"us1": US1_X, "us2": US2_X}     # us_route 'lanes_wide': the B-16 channel ends at the lane x
LANES = True                       # h1_fairleads.placed / frame_h1.print_mesh read this (False = BL-048 print)

# Lug arms (frame side of each US fairlead's floor): a tapered bar from the stay to the lane fairlead, its top at the
# fairlead floor. Section at the stay ('root', |x - stay| <= stay radius) and at the fairlead's inner cheek face
# ('tip'), linear in between (hull): underside y relative to the stay centre yc at the station, z span relative to
# the pin. US1's arm starts 5 mm above the US1 cheek bottom so it clears the BL-049 hinge cheek top (z 60 + 27 = 87)
# by 3 mm; US2's root stays inside the spreader sheet's US2 notch (z 127-157, spreader.NOTCH_CLEAR).
ARM = {"us1": {"root": {"y_lo": -13.0, "z": (-5.0, 11.0), "top": "stay"}, "tip": {"y_lo": -10.0, "z": (-5.0, 11.0)}},
       "us2": {"root": {"y_lo": -11.0, "z": (-15.0, 15.0), "top": "stay"}, "tip": {"y_lo": -8.0, "z": (-9.0, 9.0)}}}
# US1: z 90-106 (3 mm over the hinge cheek top z 87; 6 mm under the spreader sheet's bottom edge z 112, which spans
# x +/-121 and sits on the stays' bag face). Root top at the stay's bag face ('stay'), so the arm never stands proud
# of the stay where the sheet or its clips bear. US2 root z 127-157 = the sheet's US2 notch (spreader.NOTCH_CLEAR).
ARM_FILLET = 3.0                   # rounded arm edges (hull of z cylinders), print look and no knife edges
# BL-050: I-section arms. Outboard of the root (the arm's first ``root_keep`` mm off the stay surface stays solid, it
# governs) to ``tip_keep`` mm short of the fairlead, each arm is pocketed from both z faces down to a ``web`` mm web,
# leaving ``flange`` mm flanges at the arm's top (bag side) and bottom (wearer side). An arm dict with an 'isect' key
# is pocketed (in_arm, arm_solid); ARM_ISECT says which arms are (set by the BL-050 lug FEA, h1_bedfit.isect_study).
ISECT = {"web": 3.0, "flange": 3.0, "root_keep": 6.0, "tip_keep": 2.0}
ARM_ISECT = {"us1": False, "us2": False}

# ---------------------------------------------------------------------------------------------------- loads
HINGE_ROW_N = 1019.0               # bl047_frame_items.HINGE_ROW_N (= mfg_corrie_f_rev3.HINGE_N), factored, per side
HINGE_FACTOR = 3.0                 # the row's own basis: 3.0 x the worst 1 g sim hinge eye (attach_system C5 / C2)
G_WALK = 1.6                       # HA-LS-1 rev C fatigue peak
PIN_G_TIMES_REQ = 2.4              # ticket: the pin's yield and fatigue at 2.4 g (1.6 g x 1.5): fatigue peak
#                                    1019 x 1.6 / 2.4 = 679 N (the bag's corrie_f_body 24.4 basis), stricter than 543 N
FAT_GOAL = 1.15                    # BL-021 scatter goal
US_BAG_ON_N = {"us1": 444.4, "us2": 296.3}   # us_route.tensions(): meat_haul bag_on, factored (3.0)
US_CRADLE_N = 720.0                # loadpath_verification S5-S7, 53 kg float limit, factored 1.6 g x 1.5 (bl045_checks)
FLEET_DEG = 10.0                   # us_route ASSUMPTION US-FLEET: up to 10 deg out of the stay plane at the eye


# ======================================================================================= geometry
def lane_x(name: str, sign: float) -> float:
    return sign * LANE_X[name]


def arm_sections(p: dict, arm: dict | None = None) -> dict:
    """Frame-coordinate sections of station ``p``'s lug arm: {'root': box over x stay axis .. stay surface,
    'tip': box over x fairlead inner face .. fairlead centre}, each {'x', 'y', 'z'} (p from h1_fairleads.placed)."""
    a = arm or ARM[p["name"]]
    sgn = 1.0 if p["x"] > p["sign"] * STAY_X else -1.0
    xs = p["sign"] * STAY_X
    hx = p["geom"].throat / 2 + p["geom"].cheek
    out = {}
    for key, (x0, x1) in (("root", (xs, xs + sgn * p["stay_r"])), ("tip", (p["x"] - sgn * hx, p["x"]))):
        q = a[key]
        top = p["yc"] + p["stay_r"] - 0.137 if q.get("top") == "stay" else p["y_floor"]   # 0.137: off the body surface
        out[key] = {"x": tuple(sorted((x0, x1))), "y": (p["yc"] + q["y_lo"], top),
                    "z": (p["z"] + q["z"][0], p["z"] + q["z"][1])}
    return out


def arm_box(p: dict, arm: dict | None = None) -> dict:
    """Bounding box of the arm (frame coordinates)."""
    s = arm_sections(p, arm)
    return {k: (min(s["root"][k][0], s["tip"][k][0]), max(s["root"][k][1], s["tip"][k][1])) for k in ("x", "y", "z")}


def arm_of(name: str) -> dict:
    """The arm dict as built: ARM[name], with ISECT under 'isect' where ARM_ISECT says so."""
    a = dict(ARM[name])
    if ARM_ISECT.get(name):
        a["isect"] = dict(ISECT)
    return a


def _pocket_span(p: dict, a: dict) -> tuple:
    """|x - stay axis| range of the pockets: (stay_r + root_keep, fairlead inner face - tip_keep)."""
    q = a["isect"]
    s1 = abs(p["x"] - p["sign"] * STAY_X) - (p["geom"].throat / 2 + p["geom"].cheek)
    return p["stay_r"] + q["root_keep"], s1 - q["tip_keep"]


def in_arm(pts: np.ndarray, p: dict, arm: dict | None = None) -> np.ndarray:
    """Points (frame coordinates) inside the tapered arm of station ``p`` (less the I-section pockets when the arm
    dict carries 'isect')."""
    arm = arm if arm is not None else arm_of(p["name"]) if p["name"] in ARM else None
    s = arm_sections(p, arm)
    xs = p["sign"] * STAY_X
    d = np.abs(pts[:, 0] - xs)
    s0, s1 = p["stay_r"], abs(p["x"] - xs) - (p["geom"].throat / 2 + p["geom"].cheek)
    t = np.clip((d - s0) / max(s1 - s0, 1e-6), 0.0, 1.0)
    r, q = s["root"], s["tip"]
    ylo = r["y"][0] + t * (q["y"][0] - r["y"][0])
    yhi = r["y"][1] + t * (q["y"][1] - r["y"][1])
    zlo = r["z"][0] + t * (q["z"][0] - r["z"][0])
    zhi = r["z"][1] + t * (q["z"][1] - r["z"][1])
    on = (np.sign(pts[:, 0] - xs) == np.sign(p["x"] - xs)) & (d <= abs(p["x"] - xs))
    inside = on & (pts[:, 1] >= ylo) & (pts[:, 1] <= yhi) & (pts[:, 2] >= zlo) & (pts[:, 2] <= zhi)
    if arm is not None and arm.get("isect"):
        q = arm["isect"]
        da, db = _pocket_span(p, arm)
        zc = 0.5 * (zlo + zhi)
        pocket = (d >= da) & (d <= db) & (pts[:, 1] > ylo + q["flange"]) & (pts[:, 1] < yhi - q["flange"])
        if q.get("kind", "I") == "box":       # closed box: a sealed core, walls 'web' thick on both z faces
            pocket &= np.abs(pts[:, 2] - zc) < 0.5 * (zhi - zlo) - q["web"]
        else:                                 # I: pockets open to both z faces, a 'web' mm web on the mid plane
            pocket &= np.abs(pts[:, 2] - zc) > q["web"] / 2.0
        inside &= ~pocket
    return inside


def pocket_solid(p: dict, arm: dict | None = None):
    """The two I-section pockets of station ``p``'s arm as one manifold (None if the arm is solid): hull of the
    pocket sections at the two ends of the span (the arm tapers linearly), each run 1 mm past the arm's z faces."""
    import manifold3d as m3d
    a = arm if arm is not None else arm_of(p["name"])
    if not a.get("isect"):
        return None
    q = a["isect"]
    s = arm_sections(p, a)
    xs = p["sign"] * STAY_X
    sgn = 1.0 if p["x"] > xs else -1.0
    s0, s1 = p["stay_r"], abs(p["x"] - xs) - (p["geom"].throat / 2 + p["geom"].cheek)
    da, db = _pocket_span(p, a)
    out = None
    for side in (-1.0, 1.0):
        pts = []
        for dd in (da, db):
            t = min(max((dd - s0) / max(s1 - s0, 1e-6), 0.0), 1.0)
            r, tp = s["root"], s["tip"]
            ylo = r["y"][0] + t * (tp["y"][0] - r["y"][0]) + q["flange"]
            yhi = r["y"][1] + t * (tp["y"][1] - r["y"][1]) - q["flange"]
            zlo = r["z"][0] + t * (tp["z"][0] - r["z"][0])
            zhi = r["z"][1] + t * (tp["z"][1] - r["z"][1])
            zc = 0.5 * (zlo + zhi)
            za, zb = (zc + q["web"] / 2.0, zhi + 1.0) if side > 0 else (zlo - 1.0, zc - q["web"] / 2.0)
            for yy in (ylo, yhi):
                for zz in (za, zb):
                    pts.append(m3d.Manifold.cube((0.01, 0.01, 0.01)).translate((xs + sgn * dd, yy, zz)))
        h = m3d.Manifold.batch_hull(pts)
        out = h if out is None else out + h
    return out


def arm_solid(p: dict):
    """The lug arm as a manifold: hull of z cylinders (r ARM_FILLET) at the x-y corners of its root and tip sections
    (linear taper, rounded edges). The stay and the fairlead root cover its ends."""
    import manifold3d as m3d
    r = ARM_FILLET
    cyl = []
    for b in arm_sections(p).values():
        L = b["z"][1] - b["z"][0]
        zc = 0.5 * (b["z"][0] + b["z"][1])
        for xx in (b["x"][0] + r, b["x"][1] - r):
            for yy in (b["y"][0] + r, b["y"][1] - r):
                cyl.append(m3d.Manifold.cylinder(L, r, r, 32, center=True).translate((xx, yy, zc)))
    return m3d.Manifold.batch_hull(cyl)


def add_lugs(man, log=print, stats: dict | None = None):
    """Union the lug arms of the lane stations onto the body (before h1_fairleads.add_fairleads cuts the throats)."""
    from . import h1_fairleads as HF
    v0 = man.volume()
    for p in HF.placed():
        if p.get("lane"):
            arm = arm_solid(p)
            pk = pocket_solid(p)
            man = man + (arm - pk if pk is not None else arm)
    if stats is not None:
        stats.update({"arms_mm3": man.volume() - v0, "arms_g": (man.volume() - v0) * RHO_G_MM3})
    if log:
        log(f"  lug arms (BL-049): +{(man.volume() - v0) * RHO_G_MM3:.1f} g")
    return man


def old_us_stations() -> list:
    """The US stations where BL-045 printed them (on the stays, x +/-115)."""
    from . import h1_fairleads as HF
    return [p for p in HF.placed(lanes=False) if p["name"] in LANE_X]


def strip_old_us(solid: np.ndarray, log=None) -> tuple:
    """Voxel body (H1 2 mm grid) without the US1 / US2 fairlead stubs on the stays: voxels inside the old station's
    fairlead field and outside the stay (radius + 1 voxel) go, keep-outs untouched. Returns (solid, removed count)."""
    from . import bag_attach as BA
    from . import frame_h1 as H1
    c = H1.base()
    cen = c["cen"]
    out = solid.copy()
    n = 0
    for p in old_us_stations():
        g = p["geom"]
        loc = cen - np.array([p["x"], p["yc"], p["z"]])
        near = np.where((np.abs(loc[:, 0]) < g.throat / 2 + g.cheek + 6) & (np.abs(loc[:, 2]) < g.half_z + 6))[0]
        L = loc[near]
        # the BL-045 saddle and the 2026-11-01 stub both: any voxel above the stay surface within the fairlead's x-z
        # footprint (+2 mm, the voxel blend), and every voxel inside the field
        # inside the BL-045 saddle field (voxel_as_printed added it) or the 2026-11-01 fairlead field (the topology
        # optimisation's keep-in, frame_topopt hard points), and outside the stay circle + 1 mm
        fld = np.minimum(BA.fairlead_local(L, p["stay_r"], g), BA.fairlead_local(L, p["stay_r"], BA.legacy_geom()))
        outside = np.hypot(L[:, 0], L[:, 1]) > p["stay_r"] + 1.0
        # and the stub's throat (the voxel body filled it; the print cleared it with the throat prism): everything
        # over the stay within the old fairlead's footprint, from the legacy root up
        lg = BA.legacy_geom()
        foot = (np.abs(L[:, 0]) <= lg.throat / 2 + lg.cheek + 1.0) & (np.abs(L[:, 2]) <= g.half_z + 1.0) & \
               (L[:, 1] >= p["stay_r"] - lg.embed)
        rm = near[((fld <= 0.0) | foot) & outside]
        rm = rm[~c["dom"].passive_void[rm] & ~c["holes"][rm]]
        n += int(out[rm].sum())
        out[rm] = False
        if CROWN_RESTORE:                    # BL-051: the stay section bridged back over the strip zone
            back = rm[_crown_bridge(solid, cen, rm, H1.H)]
            n -= int(out[back].size)
            out[back] = True
    if log:
        log(f"  old US stubs removed: {n} voxels ({n * H1.H ** 3 * RHO_G_MM3:.1f} g)")
    return out, n


# BL-051: ``strip_old_us`` took the stay's own bag-face crown with the stub. The 'outside' rule above keeps only the
# stay CIRCLE (r 8.96-9.19, top y = yc + r + 1 = 7.3 at US2), but the H1 body's stay is fuller than that circle on the
# bag face (crown top y 10.0 at z 127, 11.8 at z 160, 9.8 at z 110), so the print came out 2-4 mm low over the old
# stub sites (US2 z 131-152, US1 z 86-104; at US2 z 138-146 the release body itself already lacked it: the old stub's
# throat). With CROWN_RESTORE the stay section is bridged across each strip zone: every voxel of the zone is set solid
# where the body is solid at the same (x, y) on the reference z planes each side of that station's strip zone (the stay section
# each side, intersected: never fuller than the leaner side), whatever the stub left there. False = the BL-049/050
# print. ``strip_old_us``'s count is then the net voxels removed.
CROWN_RESTORE = True
CROWN_REF_VOX = (2, 3, 4)          # reference planes 4-8 mm beyond each end of the zone (all intersected): the raw
#                                    release body still carries the old stub's edge blend (y 11 at z 103-107 over
#                                    US1) one voxel out, which a +/-1 voxel bridge copied into a 1.5 mm hump


def _crown_bridge(solid: np.ndarray, cen: np.ndarray, rm: np.ndarray, h: float) -> np.ndarray:
    """Mask over ``rm`` (voxel indices of one station's strip zone): True where the body ``solid`` is solid at the same
    (x, y) on every reference plane CROWN_REF_VOX voxels below the zone's lowest z and above its highest z (the stay
    prism bridged over it, never fuller than the leanest reference section)."""
    if len(rm) == 0:
        return np.zeros(0, bool)
    key = np.floor(cen / h).astype(np.int64)        # centres sit at odd mm on the 2 mm grid: floor, never round
    k0 = key.min(axis=0)
    span = key.max(axis=0) - k0 + 1
    lin = lambda k: ((k[:, 0] - k0[0]) * span[1] + (k[:, 1] - k0[1])) * span[2] + (k[:, 2] - k0[2])
    solid_lin = np.sort(lin(key[solid]))
    kz = key[rm, 2]
    out = np.ones(len(rm), bool)
    for dz in [kz.min() - k for k in CROWN_REF_VOX] + [kz.max() + k for k in CROWN_REF_VOX]:
        q = key[rm].copy()
        q[:, 2] = dz
        lq = lin(q)
        i = np.clip(np.searchsorted(solid_lin, lq), 0, len(solid_lin) - 1)
        out &= solid_lin[i] == lq
    return out


def voxel_lugs(solid: np.ndarray) -> tuple:
    """Voxel body with the lug arms and the lane fairleads' roots (the part inside the voxel envelope) added, and the
    hinge's BL-049 section (h1_fairleads.voxel_as_printed already applies the placed geometry)."""
    from . import bag_attach as BA
    from . import frame_h1 as H1
    from . import h1_fairleads as HF
    c = H1.base()
    cen = c["cen"]
    out = solid.copy()
    n = 0
    for p in HF.placed():
        if not p.get("lane"):
            continue
        inb = in_arm(cen, p)
        loc = cen - np.array([p["x"], p["yc"], p["z"]])
        fl = BA.fairlead_local(loc, p["stay_r"], p["geom"]) <= 0.0
        add = (inb | fl) & ~c["dom"].passive_void & ~c["holes"]
        n += int((add & ~out).sum())
        out |= add
    return out, n


# ======================================================================================= cheek / lug FEA
def _local_station(geom, stay_r: float, xoff: float) -> dict:
    """A placed()-like station in lug_fea's local frame (stay axis at x 0, stay centre y 0, pin z 0, R side)."""
    return {"name": "local", "sign": 1.0, "x": xoff, "yc": 0.0, "z": 0.0, "stay_r": stay_r, "geom": geom,
            "y_floor": stay_r + geom.floor_proud}


def lug_fea(geom, stay_r: float, xoff: float, arm: dict | None, loads: dict, h: float = 1.0,
            relief: bool = False, field: str | None = None, stay_poly: list | None = None, extra=None) -> dict:
    """Voxel FEA of a fairlead standing ``xoff`` from the stay axis on an arm (h1_fairleads.fairlead_fea's model,
    rules and load application; ``xoff`` 0 and ``arm`` None = that model exactly). Local axes: x along the pin
    (+ = towards the lane), y towards the bag, z along the stay; the stay stub (circle r ``stay_r``) is fixed at its
    end caps. ``arm``: {'y_lo', 'z': (lo, hi)} relative to the stay centre / pin. Per load: FI99 over the whole
    'use' region (the record's rule) and per region: 'fairlead' (|x - xoff| <= throat/2 + cheek), 'arm' (between the
    stay surface + 3 mm and the fairlead) and 'root' (the arm's first 6 mm off the stay surface)."""
    from . import bag_attach as BA
    from .fem import Grid, ke_h8
    from .frame_topopt import NU, ReducedSystem, element_stress, layer_failure_index
    pa = BA._paht()
    y_hole = stay_r + geom.hole_proud
    hx = geom.throat / 2.0 + geom.cheek
    zt = max(geom.half_z, geom.z_top)
    zext = max(22.0, zt + 8.0)
    xa, xb = min(-(stay_r + 4.0), xoff - hx - 3.0), max(stay_r + 4.0, xoff + hx + 3.0)
    if xoff == 0.0:
        xa, xb = -max(20.0, hx + 3.0), max(20.0, hx + 3.0)
    lo = np.array([xa, -(stay_r + 4.0), -zext])
    hi = np.array([xb, stay_r + geom.tip_proud + 4.0, zext])
    if stay_poly is not None:            # room for the real stay section (BL-051)
        sp_ = np.asarray(stay_poly, float)
        lo[:2] = np.minimum(lo[:2], sp_.min(axis=0) - 2.0)
        hi[:2] = np.maximum(hi[:2], sp_.max(axis=0) + 2.0)
    n = np.maximum(np.round((hi - lo) / h).astype(int), 6)
    g = Grid(tuple(int(v) for v in n), h, x0=lo)
    c = g.elem_centers()
    stay_xy = np.hypot(c[:, 0], c[:, 1]) <= stay_r
    if stay_poly is not None:            # BL-051: the stay's real section (crown included) in place of the circle
        from matplotlib.path import Path as _MPath
        stay_xy |= _MPath(np.asarray(stay_poly, float)).contains_points(c[:, :2])
    stay = stay_xy & (np.abs(c[:, 2]) <= zext - 1.0)
    cl = c - np.array([xoff, 0.0, 0.0])
    fl_f = BA.fairlead_local(cl, stay_r, geom)
    yoke = fl_f <= 0.0
    armm = np.zeros(len(c), bool)
    if arm is not None:
        st = dict(_local_station(geom, stay_r, xoff), sign=1.0 if xoff > 0 else -1.0)
        st["sign"] = 1.0                     # stay axis at x 0 (STAY_X offset removed below)
        cs = c + np.array([STAY_X, 0.0, 0.0])
        st["x"] = STAY_X + xoff
        armm = in_arm(cs, st, arm)
        if extra is not None:            # BL-053: extra lug solid (inner-cheek buttress), frame-like coords as in_arm
            armm |= extra(cs, st)
    solid = stay | yoke | armm
    if relief:          # BL-047's m-1 relief groove (bl047_frame_items.relief_solid) as voids, both cheeks
        from .bl047_frame_items import RELIEF_DEPTH, RELIEF_INTO_CHEEK, RELIEF_UP, RELIEF_W
        yf = stay_r + geom.floor_proud
        ax_c = np.abs(cl[:, 0])
        rel = (ax_c >= geom.throat / 2.0 - RELIEF_W) & (ax_c <= geom.throat / 2.0 + RELIEF_INTO_CHEEK) & \
              (c[:, 1] >= yf - RELIEF_DEPTH) & (c[:, 1] <= yf + RELIEF_UP) & \
              (c[:, 2] >= -geom.half_z - 1.0) & (c[:, 2] <= geom.z_top + 1.0)
        solid &= ~rel
    nc = g.node_coords()
    radial = np.c_[nc[:, 1] - y_hole, nc[:, 2]]
    rr = np.linalg.norm(radial, axis=1)
    xl = nc[:, 0] - xoff
    band = (rr > geom.hole_d / 2.0 - 0.35 * h) & (rr < geom.hole_d / 2.0 + 0.9 * h)
    band &= np.abs(xl) >= geom.throat / 2.0 - 0.3
    band &= np.abs(xl) <= geom.throat / 2.0 + geom.cheek + 0.6 * h
    end_xy = np.hypot(nc[:, 0], nc[:, 1]) <= stay_r + h
    if stay_poly is not None:
        from matplotlib.path import Path as _MPath
        from shapely.geometry import Polygon as _Pg
        big = np.asarray(_Pg(np.asarray(stay_poly, float)).buffer(h).exterior.coords)
        end_xy |= _MPath(big).contains_points(nc[:, :2])
    end = (np.abs(nc[:, 2]) >= zext - 2.5) & end_xy
    fixed = np.zeros(g.ndof, bool)
    ids = np.where(end)[0]
    for d in range(3):
        fixed[3 * ids + d] = True
    in_solid = np.unique(g.enodes[solid])
    band &= np.isin(np.arange(g.nn), in_solid)
    names = list(loads)
    F = np.zeros((g.ndof, len(names)))
    for k, nm in enumerate(names):
        f3 = np.asarray(loads[nm], float)
        fyz = f3[1:]
        mag = float(np.linalg.norm(fyz))
        if mag > 1e-9:
            d = fyz / mag
            idx = np.where(band & (radial @ d > 0.15 * geom.hole_d / 2.0))[0]
            if idx.size < 6:
                idx = np.where(band)[0]
            w = np.maximum(radial[idx] @ d, 0.0)
            w = w / w.sum() if w.sum() > 0 else np.ones(idx.size) / idx.size
            F[3 * idx + 1, k] += mag * w * d[0]
            F[3 * idx + 2, k] += mag * w * d[1]
        if abs(f3[0]) > 1e-9:
            side = 1.0 if f3[0] > 0 else -1.0
            x_in = xoff + side * geom.throat / 2.0
            rf = np.hypot(nc[:, 1] - y_hole, nc[:, 2])
            face = np.where((np.abs(nc[:, 0] - x_in) <= 0.6 * h) & (rf >= geom.hole_d / 2.0) & (rf <= geom.hole_d))[0]
            face = face[np.isin(face, in_solid)]
            F[3 * face, k] += f3[0] / max(face.size, 1)
    F[fixed] = 0.0
    KE = ke_h8(h, 1.0, NU)
    rs = ReducedSystem(g, solid, fixed, KE)
    U = rs.solve(rs.assemble(np.full(rs.ae.size, 1.0)), F) / pa["E"]
    out, regs = {}, None
    for k, nm in enumerate(names):
        eidx, S = element_stress(g, U[:, k], solid, pa["E"])
        fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
        if regs is None:
            cc = c[eidx]
            ccl = cc - np.array([xoff, 0.0, 0.0])
            away = np.abs(cc[:, 2]) < zext - 6.0
            near_f = BA.fairlead_local(ccl, stay_r, geom) <= h
            rs_ = np.hypot(cc[:, 0], cc[:, 1])
            arm_e = armm[eidx]
            between = (np.abs(ccl[:, 0]) > hx) & (np.sign(cc[:, 0] - 0.0) == np.sign(xoff or 1.0))
            regs = {"use": (near_f | arm_e) & away,
                    "fairlead": near_f & (np.abs(ccl[:, 0]) <= hx + h) & away}
            if arm is not None:
                regs["arm"] = arm_e & between & (rs_ > stay_r + 3.0) & away
                regs["root"] = (arm_e | near_f) & (rs_ <= stay_r + 6.0) & (rs_ > stay_r - 3.0) & away & \
                               (np.sign(cc[:, 0]) == np.sign(xoff))
            regs = {k_: v for k_, v in regs.items() if v.sum() >= 30}
        row = {"force_n": float(np.linalg.norm(loads[nm])),
               "applied_n": float(np.linalg.norm([F[0::3, k].sum(), F[1::3, k].sum(), F[2::3, k].sum()]))}
        for rn, m in regs.items():
            fu = fi[m]
            row[rn] = {"fi99": float(np.percentile(fu, 99)), "fi_max": float(fu.max()),
                       "peak_xyz": [round(float(v), 1) for v in c[eidx][m][int(np.argmax(fu))]]}
        row["fi99"] = row["use"]["fi99"]
        row["fi99_gov"] = max(v["fi99"] for kk, v in row.items() if isinstance(v, dict))
        row["sf"] = 1.0 / max(row["fi99"], 1e-9)
        out[nm] = row
        if field == nm:         # element centres, FI and displacement magnitude (for the figures)
            un = np.linalg.norm(U[:, k].reshape(-1, 3), axis=1)
            out["_field"] = {"cen": c[eidx], "fi": fi, "u_elem": un[g.enodes[eidx]].mean(axis=1), "load": nm}
    added = float(((yoke | armm) & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    return {"h": h, "stay_r": stay_r, "xoff": xoff, "arm": arm, "geom": dataclasses.asdict(geom), "added_g": added,
            "n_elem": int(solid.sum()), "regions": {k: int(v.sum()) for k, v in (regs or {}).items()}, "loads": out}


def _cached(tag: str, fn, key: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{tag}.json"
    k = json.loads(json.dumps(key, default=float))
    if p.exists():
        d = json.loads(p.read_text())
        if d.get("key") == k:
            return d
    d = fn()
    d["key"] = k
    p.write_text(json.dumps(d, default=float))
    return d


# ---------------------------------------------------------------------------------------------------- hinge
def hinge_directions() -> dict:
    """Unit force directions on the frame at the hinge pin: the 12 rev 3 fine sim rows (hinge_eye_vectors.json, L rows
    mirrored onto the R station: inboard = -x) and the rev C governing beam vector (rev_c_verification gov_c)."""
    d = json.loads((ANALYSIS / "hinge_eye_vectors.json").read_text())
    out = {}
    for r in d["rows"]:
        u = np.asarray(r["unit"], float)
        if r["side"] == "L":
            u[0] = -u[0]
        out[f"{r['torso']}|{r['case']}|{r['side']}"] = u.tolist()
    rc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["hinge"]
    v = np.array([rc.get("fx", 0.0), rc["fy"], rc["fz"]], float)
    out["revC"] = (v / np.linalg.norm(v)).tolist()
    return out


def hinge_rows(fea: dict) -> dict:
    """SFs at the 1019 N row from a unit-direction FEA run (loads were 1000 N): strength at 1019 N; fatigue at the
    1.6 g peak on the row's 3.0 basis (543 N) and on the 2.4 g basis (679 N); creep at 1 g (340 N)."""
    from . import bag_attach as BA
    pa = BA._paht()
    rows = {}
    for k, v in fea["loads"].items():
        fpn = v["fi99"] / v["force_n"]
        fpn_g = v["fi99_gov"] / v["force_n"]
        F1 = HINGE_ROW_N / HINGE_FACTOR
        rows[k] = {"strength": 1.0 / (fpn * HINGE_ROW_N), "fatigue": pa["fat"] / (fpn * G_WALK * F1),
                   "fatigue_2p4": pa["fat"] / (fpn * HINGE_ROW_N * G_WALK / PIN_G_TIMES_REQ),
                   "creep": pa["rupture"] / (fpn * F1),
                   "fatigue_fimax": pa["fat"] / (v["use"]["fi_max"] / v["force_n"] * G_WALK * F1),
                   "fatigue_gov_region": pa["fat"] / (fpn_g * G_WALK * F1),
                   "peak_xyz": v["use"]["peak_xyz"]}
    sims = {k: r for k, r in rows.items() if k != "revC"}
    worst = min(sims, key=lambda k: sims[k]["fatigue"])
    return {"rows": rows, "sim_worst": worst, "sim": {k: round(v, 3) for k, v in sims[worst].items() if k != "peak_xyz"},
            "revC": {k: round(v, 3) for k, v in rows["revC"].items() if k != "peak_xyz"}}


def hinge_study(h: float = 1.0, log=print) -> dict:
    """BL-047 print (BL-042 hinge + the relief groove), the BL-042 hinge without the groove, and the BL-049 hinge, in
    every sim direction and the rev C direction at the 1019 N row; a 0.75 mm mesh check on the governing directions.
    The stay is the stay_radius circle; ASSUMPTION STAY-AX (6 mm half-width ellipse) as a sensitivity."""
    from . import bag_attach as BA
    from .frame_branch import stay_radius
    r60 = float(stay_radius(60.0, BA.SCALE))
    dirs = hinge_directions()
    loads = {k: (1000.0 * np.asarray(v)).tolist() for k, v in dirs.items()}
    cands = {"bl047_print": (BA.HINGE_GEOM_BL042, True), "bl042_no_relief": (BA.HINGE_GEOM_BL042, False),
             "bl049": (BA.HINGE_GEOM, False)}
    res = {"directions": dirs, "h": h}
    for tag, (geom, rel) in cands.items():
        f = _cached(f"hinge_{tag}_{h:g}", lambda: lug_fea(geom, r60, 0.0, None, loads, h=h, relief=rel),
                    {"geom": dataclasses.asdict(geom), "relief": rel, "loads": loads, "h": h})
        res[tag] = {"added_g": f["added_g"], **hinge_rows(f)}
        if log:
            log(f"  hinge {tag}: sim worst {res[tag]['sim_worst']} {res[tag]['sim']}; revC {res[tag]['revC']}")
    # sensitivity: 0.75 mm voxels on the governing directions
    gov = [res["bl049"]["sim_worst"], res["bl047_print"]["sim_worst"], "revC"]
    l2 = {k: loads[k] for k in dict.fromkeys(gov)}
    for tag in ("bl047_print", "bl049"):
        geom, rel = cands[tag]
        f = _cached(f"hinge_{tag}_0.75", lambda: lug_fea(geom, r60, 0.0, None, l2, h=0.75, relief=rel),
                    {"geom": dataclasses.asdict(geom), "relief": rel, "loads": l2, "h": 0.75})
        res[f"{tag}_h0.75"] = hinge_rows(f)
    # ASSUMPTION STAY-AX sensitivity (BL-042): the stay at z 60 as a 6 mm half-width ellipse across the pin axis
    from . import h1_fairleads as HF
    f = _cached("hinge_bl049_ellipse_1", lambda: HF.fairlead_fea(BA.HINGE_GEOM, r60, loads, h=1.0, stay_ax=HF.STAY_AX_60),
                {"geom": dataclasses.asdict(BA.HINGE_GEOM), "loads": loads, "stay_ax": HF.STAY_AX_60})
    for v in f["loads"].values():
        v.setdefault("use", {"fi99": v["fi99"], "fi_max": v["fi_max"], "peak_xyz": v["peak_xyz"]})
        v.setdefault("fi99_gov", v["fi99"])
    res["bl049_ellipse"] = hinge_rows(f)
    return res


def pin_check(force_n: float, throat: float, cheek: float, pin_d: float, material: str,
              g_times_req: float, surface_k: float = 0.9) -> dict:
    """h1_fairleads.pin_bending for any pin material record (S-basis yield, fatigue limit x ``surface_k``, Goodman to
    R 0 on the UTS). M = F (2 L - b) / 8, L = throat + cheek, b = throat; fatigue peak = F x 1.6 / ``g_times_req``."""
    from huntkit.materials import load
    m = load(material)
    sy = float(m.get("yield_strength_sbasis_mpa") or m.require("yield_strength_mpa"))
    su = float(m.require("ultimate_strength_mpa"))          # as h1_fairleads.pin_bending (Goodman on the typical UTS)
    se = float(m.require("fatigue_limit_mpa")) * surface_k
    L, b = throat + cheek, throat
    Z = math.pi * pin_d ** 3 / 32.0
    M = force_n * (2 * L - b) / 8.0
    s = M / Z
    s_walk = s * G_WALK / g_times_req
    smax = 2.0 / (1.0 / se + 1.0 / su)
    rho = float(m.require("density_kg_m3"))
    length = throat + 2 * cheek + 4.0          # + 2 mm a side for the head / clip groove (ASSUMPTION PIN-L)
    return {"material": material, "pin_d_mm": pin_d, "span_mm": L, "M_nmm": M, "sigma_mpa": s, "sy_mpa": sy,
            "sf_yield": sy / s, "sigma_walk_mpa": s_walk, "goodman_smax_r0_mpa": smax, "sf_fatigue": smax / s_walk,
            "length_mm": length, "mass_g": math.pi / 4 * pin_d ** 2 * length * rho * 1e-6}


def hinge_pin() -> dict:
    """The single hinge-pin check at the 1019 N row: yield at 1019 N, fatigue on the 2.4 g basis (679 N peak) and,
    for reference, on the row's own 3.0 basis (543 N). 7075-T6 (as BL-047) against Ti-6Al-4V, BL-042 and BL-049
    spans."""
    from . import bag_attach as BA
    out = {}
    for tag, g in (("bl042", BA.HINGE_GEOM_BL042), ("bl049", BA.HINGE_GEOM)):
        for mat in ("alu_7075_t6", "ti_6al_4v"):
            a = pin_check(HINGE_ROW_N, g.throat, g.cheek, g.pin_d, mat, PIN_G_TIMES_REQ)
            b = pin_check(HINGE_ROW_N, g.throat, g.cheek, g.pin_d, mat, HINGE_FACTOR)
            out[f"{tag}|{mat}"] = {**{k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items()},
                                   "sf_fatigue_3p0_basis": round(b["sf_fatigue"], 2)}
    out["chosen"] = "bl049|ti_6al_4v"
    return out


HINGE_PIN_MATERIAL = "ti_6al_4v"   # BL-049: 5 mm Ti-6Al-4V pin (ground, h8), 7075-T6 fails fatigue at 2.4 g
HINGE_PIN_D = 5.0


# ---------------------------------------------------------------------------------------------------- lugs
def lug_loads(name: str) -> dict:
    """Frame-side force vectors (R station, x + outboard) on a lane pin, N factored, with their g_times_req:
    bag-off cradle 720 N aft and down at meat_haul._theta (+/- the US-FLEET lateral); bag-on cam-tight tension along
    the strap: straight down, down and 30 deg towards the wearer, and the drape's first path segment off the pin
    (us_route.json lanes_wide, R side, worst y share), each +/- the fleet."""
    from . import meat_haul as MH
    th = MH._theta()
    s10 = math.sin(math.radians(FLEET_DEG))
    c10 = math.cos(math.radians(FLEET_DEG))
    out = {}
    base = {"cradle": (US_CRADLE_N, [0.0, math.cos(th), -math.sin(th)], 2.4)}
    T = US_BAG_ON_N[name]
    base["bagon_down"] = (T, [0.0, 0.0, -1.0], 3.0)
    base["bagon_fore30"] = (T, [0.0, -0.5, -math.sqrt(3) / 2], 3.0)
    ur = json.loads((ANALYSIS / "us_route.json").read_text())
    rows = [r for r in ur["layouts"]["lanes_wide"]["rows"] if r["side"] == "R" and r["strap"] == name]
    best = None
    for r in rows:
        P = np.asarray(r["path"], float)
        k = int(np.argmax(np.linalg.norm(P - P[0], axis=1) >= 12.0))
        u = (P[k] - P[0]) / np.linalg.norm(P[k] - P[0])
        u[0] = 0.0
        u /= np.linalg.norm(u)
        if best is None or abs(u[1]) > abs(best[1]):
            best = u
    base["bagon_drape"] = (T, best.tolist(), 3.0)
    # BL-051 (BL-050 B us_route.json cradle_span): the cradle on the lane. Each strap's legs leave its pin at its own
    # angle, atan(belly / lane half span) (US2 23 deg at the 70 mm design belly, not meat_haul's 31.3 deg from the
    # stay x), at the 53 kg float-limit tension on the same factored basis as US_CRADLE_N (1.6 g x 1.5): the design
    # belly 70 mm, and a 50 mm belly (a harder cinch: US2 860 N, flatter still).
    cs = ur.get("cradle_span")
    if cs:
        half = cs["half_span_mm"][name]
        for key, belly, Tn in (("cradle_lane", cs["belly_mm"], cs["at_float_limit"][name]["tension_n"]),
                               ("cradle_lane_b50", 50.0, cs["sensitivity"]["belly_50"][name])):
            a = math.atan2(belly, half)
            base[key] = (float(Tn), [0.0, math.cos(a), -math.sin(a)], 2.4)
    for k, (F, u, gr) in base.items():
        u = np.asarray(u, float)
        out[k] = {"vec": (F * u).tolist(), "g_times_req": gr}
        for sgn, lab in ((1.0, "out"), (-1.0, "in")):
            v = c10 * u + np.array([sgn * s10, 0.0, 0.0])
            out[f"{k}|fleet_{lab}"] = {"vec": (F * v / np.linalg.norm(v)).tolist(), "g_times_req": gr}
    return out


def lug_geom_inputs(name: str) -> dict:
    from . import h1_fairleads as HF
    p = next(q for q in HF.placed() if q["name"] == name and q["side"] == "R")
    return {"p": p, "xoff": p["x"] - STAY_X, "arm": arm_of(name)}


def lug_study(h: float = 1.0, log=print, arms: dict | None = None, stay_polys: dict | None = None) -> dict:
    """Strength / fatigue / creep of each lane lug (fairlead + arm + stay root) under lug_loads; the governing region
    of each load (FI99 per region) and the record's whole-yoke FI99. ``arms`` overrides ARM (sizing sweeps).
    ``stay_polys`` (BL-051): {name: local (x, y) polygon of the stay section} in place of the stay circle (own cache)."""
    from . import bag_attach as BA
    pa = BA._paht()
    res = {}
    for name in LANE_X:
        gi = lug_geom_inputs(name)
        p = gi["p"]
        arm = (arms or {}).get(name, gi["arm"])
        L = lug_loads(name)
        loads = {k: v["vec"] for k, v in L.items()}
        geom = p["geom"]
        q = arm.get("isect")                  # BL-050: own cache per pocketed arm variant
        tag = f"lug_{name}_{h:g}" + (f"_{q.get('kind', 'I')}_w{q['web']:g}_f{q['flange']:g}" if q else "")
        sp = (stay_polys or {}).get(name)
        key = {"geom": dataclasses.asdict(geom), "stay_r": p["stay_r"], "xoff": gi["xoff"], "arm": arm, "loads": loads,
               "h": h}
        if sp is not None:
            tag += "_crown"
            key["stay_poly"] = [[round(float(a), 3), round(float(b), 3)] for a, b in sp]
        f = _cached(tag, lambda: lug_fea(geom, p["stay_r"], gi["xoff"], arm, loads, h=h, stay_poly=key.get("stay_poly")),
                    key)
        rows = {}
        for k, v in f["loads"].items():
            gr = L[k]["g_times_req"]
            regs = {rn: {"sf": round(1.0 / v[rn]["fi99"], 2),
                         "fatigue": round(BA._fatigue_sf(v[rn]["fi99"], gr, pa["fat"]), 2),
                         "creep": round(BA._creep_sf(v[rn]["fi99"], gr, pa["rupture"]), 2),
                         "peak_xyz": v[rn]["peak_xyz"]}
                    for rn in ("use", "fairlead", "arm", "root") if rn in v}
            gov = min(regs, key=lambda r: regs[r]["fatigue"])
            rows[k] = {"force_n": round(v["force_n"], 1), "g_times_req": gr, "regions": regs, "governing_region": gov,
                       "sf": min(r["sf"] for r in regs.values()), "fatigue": min(r["fatigue"] for r in regs.values()),
                       "creep": min(r["creep"] for r in regs.values())}
        worst_s = min(rows, key=lambda k: rows[k]["sf"])
        worst_f = min(rows, key=lambda k: rows[k]["fatigue"])
        pin = pin_check(max(US_CRADLE_N, US_BAG_ON_N[name]), geom.throat, geom.cheek, geom.pin_d, "alu_7075_t6", 2.4)
        res[name] = {"lane_x": LANE_X[name], "z": LANE_Z[name], "xoff": gi["xoff"], "arm": arm,
                     "added_g_model": round(f["added_g"], 2), "rows": rows,
                     "worst_strength": {"load": worst_s, "sf": rows[worst_s]["sf"]},
                     "worst_fatigue": {"load": worst_f, "fatigue": rows[worst_f]["fatigue"]},
                     "min_creep": min(r["creep"] for r in rows.values()),
                     "pin_7075_cradle": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in pin.items()}}
        if log:
            log(f"  lug {name}: strength {rows[worst_s]['sf']} ({worst_s}), fatigue {rows[worst_f]['fatigue']} "
                f"({worst_f}, {rows[worst_f]['governing_region']})")
    return res


# ======================================================================================= body checks
BODY_CHECK = "m1_u2.5_im3_bl049_lanes"       # h1_buckling.full_check cache name (real crown, lane loads)
BODY_BEFORE = "m1_u2.5_im3_bl046_real"        # the record it is compared with (BL-046 body, real crown)
US_NODE_Z = {"us1": 90.0, "us2": 130.0}       # the beam model's stay nodes the under-strap pins map to
#                                               (im3_body_simloads._stay_node(US_Z = 95 / 142) -> S*90 / S*130)
LANE_CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "hipbelt_off_abuse")   # im3_body_simloads.BAG_CASES


def body_solid() -> tuple:
    """The voxel body as printed after BL-049: BL-046's body (h1_spine_channel.body_solid: release body, fairlead
    clearances at the placed stations, channel), the old US stubs stripped, the lug arms and lane fairlead roots in."""
    from . import h1_spine_channel as SC
    s, _ = SC.body_solid()
    s, n_strip = strip_old_us(s)
    s, n_add = voxel_lugs(s)
    return s, {"stripped": n_strip, "added": n_add}


def lane_items(items: list) -> tuple:
    """A load set's items with every under-strap pin load moved to its lane: the force stays at the stay node (patch)
    and gains the moment of the lateral offset, M = (x_lane - x_node, 0, 0) x F. Returns (items, n moved)."""
    out, n = [], 0
    for p, v, side in items:
        p = np.asarray(p, float)
        v = np.asarray(v, float).copy()
        for name, zn in US_NODE_Z.items():
            if side == "bag" and abs(abs(p[0]) - STAY_X) < 1.0 and abs(p[2] - zn) < 1.0:
                dx = np.sign(p[0]) * LANE_X[name] - p[0]
                v[3:] += np.cross(np.array([dx, 0.0, 0.0]), v[:3])
                n += 1
        out.append((p, v, side))
    return out, n


def lane_kit_sets(orig):
    """Wrap h1_sleeve.kit_sets: sim-basis sets of the bag cases get lane_items (beam sets carry no under-strap pin
    load: their z 90 / 130 node loads are the meat-strap cinch reactions)."""
    def f(basis, *a, **k):
        sets = orig(basis, *a, **k)
        if basis == "beam":
            return sets
        out = []
        for s in sets:
            if s.case in LANE_CASES:
                items, n = lane_items(s.items)
                s = dataclasses.replace(s, items=items)
            out.append(s)
        return out
    return f


def cradle_sets(fleet: bool = True, per_strap: dict | None = None, tag: str = "lanes") -> list:
    """Bag-off float cradle on the lanes: each of the four US pins pulls US_CRADLE_N / 2.4 at 1 g (factor 2.4 = 1.6 g x
    1.5, so the strength row is 720 N a pin and the fatigue row 480 N), aft and down at meat_haul._theta, at the stay
    node with the lane moment; the hip-pivot clamp reacts. As 'static_carry' so h1_sleeve.evaluate also gives its
    fatigue. ``fleet``: a second set with the US-FLEET 10 deg inboard pull."""
    from . import meat_haul as MH
    from .frame_topopt import LoadSet
    th = MH._theta()
    F1 = US_CRADLE_N / 2.4
    # BL-051: ``per_strap`` {name: (factored N, leg angle rad)} replaces 720 N at meat_haul._theta for each strap
    ps = per_strap or {nm: (US_CRADLE_N, th) for nm in US_NODE_Z}
    sets = []
    for fl, lat in (("dir", 0.0), ("fleet", math.sin(math.radians(FLEET_DEG)))):
        if fl == "fleet" and not fleet:
            continue
        items = []
        for name, zn in US_NODE_Z.items():
            Fs, ths = ps[name][0] / 2.4, ps[name][1]
            for sx in (1.0, -1.0):
                u = np.array([-sx * lat, math.cos(ths), -math.sin(ths)])
                u /= np.linalg.norm(u)
                yn = -1.7 if name == "us1" else -2.5            # the beam nodes' y (h1_sleeve sets)
                items.append((np.array([sx * STAY_X, yn, zn]), np.r_[Fs * u, 0.0, 0.0, 0.0], "bag"))
        items, _ = lane_items(items)
        # the meat bears forward on the frame face between the straps (meat_straps' face rule): the aft pull of the
        # straps is reacted there, not at the hip pivot; equal shares on the stay face nodes z 60-155, each side
        fy = sum(float(v[1]) for _, v, _ in items)
        face = [(-1.1, 60.0), (-1.7, 90.0), (-2.3, 120.0), (-2.5, 130.0), (-2.9, 155.0)]
        for sx in (1.0, -1.0):
            for yn, zn in face:
                items.append((np.array([sx * STAY_X, yn, zn]), np.r_[0.0, -fy / (2 * len(face)), 0.0, 0.0, 0.0, 0.0],
                              "bag"))
        sets.append(LoadSet(key=f"U_cradle@{tag}_{fl}_0:static_carry|0", case="static_carry", torso=0.0, factor=2.4,
                            g=1.6, kg=53.0, items=items, bushings=[], pawl=np.zeros(3)))
    return sets


def body_check(log=print) -> dict:
    """h1_buckling.full_check on the BL-049 body with the lane loads (real crown, BL-046's caches), and the cradle
    sets (h1_sleeve.body_eval). Cached in outputs/h1_buckling/check_<BODY_CHECK>.json and outputs/h1_lanes."""
    from . import h1_buckling as B
    from . import h1_sleeve as S
    from . import h1_spine_channel as SC
    solid, info = body_solid()
    orig = S.kit_sets
    with SC.real_crown_models(), SC._real_caches():
        S.kit_sets = lane_kit_sets(orig)
        try:
            chk = B.full_check(BODY_CHECK, solid, log=log)
        finally:
            S.kit_sets = orig
    s_stay = SC.body_solid()[0]
    o_out = S.OUT
    S.OUT = OUT
    try:
        cr = S.body_eval("cradle_lanes", solid, cradle_sets(), log=log)
        cr0 = S.body_eval("cradle_stay", s_stay, cradle_sets_on_stay(), log=log)
    finally:
        S.OUT = o_out
    return {"check": chk, "cradle": cr, "cradle_on_stay": cr0, "voxels": info}


def cradle_sets_on_stay() -> list:
    """The same cradle sets with the pins on the stays (the BL-045 print): the reference for the lane moment."""
    sets = cradle_sets()
    out = []
    for s in sets:
        items = [(p, np.r_[v[:3], 0.0, 0.0, 0.0], sd) for p, v, sd in s.items]     # the lane moments taken out
        out.append(dataclasses.replace(s, items=items, key=s.key.replace("lanes_", "stay_")))
    return out


# ======================================================================================= print, pieces, bed
BED_MM = (340.0, 320.0)            # Bambu H2S bed (print/frame_h1/README.md 'fits the H2S bed')
BRIM_MM = 8.0                      # README section 1 step 5
BL047_PRINT_G = {"assembled": 886.2, "lower": 342.7, "upper": 543.5}   # crown_gnl.json mass (the BL-047 export)


def bed_fit(path: Path, bed=BED_MM, brim: float = BRIM_MM) -> dict:
    """Smallest bounding rectangle of a flat half's plate footprint over rotations in the bed plane (0.5 deg steps),
    with and without the brim, against the bed."""
    import trimesh
    from scipy.spatial import ConvexHull
    m = trimesh.load(path)
    P = m.vertices[:, :2]
    H = P[ConvexHull(P).vertices]
    best = None
    for th in np.radians(np.arange(0.0, 180.0, 0.5)):
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        Q = H @ R.T
        w, h = float(np.ptp(Q[:, 0])), float(np.ptp(Q[:, 1]))
        w, h = max(w, h), min(w, h)
        over = max(w - bed[0], h - bed[1])
        if best is None or over < best["over_mm"]:
            best = {"deg": round(math.degrees(th), 1), "w_mm": round(w, 1), "h_mm": round(h, 1), "over_mm": round(over, 1)}
    best["fits"] = bool(best["over_mm"] <= 0.0)
    best["fits_with_brim"] = bool(best["over_mm"] + 2 * brim <= 0.0)
    best["extents_mm"] = [round(float(v), 1) for v in m.extents]
    return best


def slice_checks(path=None) -> dict:
    """The print STL's slice checks: 12 fairleads with their eye stacks (h1_fairleads.check_stl), the spine channel
    over the full crown travel (h1_spine_channel.check_stl_channel), the pawl swing (h1_pawl.check_stl_pawl)."""
    import trimesh
    from . import h1_fairleads as HF
    from . import h1_pawl as PW
    from . import h1_spine_channel as SC
    m = trimesh.load(path or HF.PRINT_DIR / "h1_assembled.stl")
    fl = HF.check_stl(m)
    ch = SC.check_stl_channel(m)
    pw = PW.check_stl_pawl(m)
    rows = {k: {"pass": v["pass"], "gap_under_pin": v["gap_under_pin"], "throat": v["throat_min_w"],
                "eye_fits": v.get("eye_fits"), "x": v["x"],
                "cheek_mm": min(c["cheek_thick_mm"] for c in v["cheeks"].values()),
                "cheek_height_mm": min(c["cheek_height_mm"] for c in v["cheeks"].values())}
            for k, v in fl.items() if isinstance(v, dict)}
    # the test pieces, sliced the same way (frame-coordinate copies)
    from . import bag_attach as BA
    pcs = {}
    P = {q["id"]: q for q in HF.placed()}
    for fn, ids in (("us_route_stay_R", ("hinge_R", "us1_R", "us2_R")), ("hefit_hinge_fairlead_R", ("hinge_R",)),
                    ("im3ec_cheek_R", ("im3_R",))):
        f = HF.PIECES_DIR / f"{fn}_frame_coords.stl"
        if not f.exists():
            continue
        pm = trimesh.load(f)
        for i in ids:
            q = P[i]
            env = BA.HINGE_EYE_ENVELOPE if q["name"] == "hinge" else BA.imus_eye_envelope(q["name"])
            r = HF.check_station(pm, q, env)
            pcs[f"{fn}|{i}"] = {"pass": r["pass"], "gap_under_pin": r["gap_under_pin"], "throat": r["throat_min_w"],
                                "eye_fits": r.get("eye_fits"), "watertight": bool(pm.is_watertight)}
    return {"fairleads": rows, "fairleads_pass": fl["all_pass"], "channel": {"min": ch["min"], "pass": ch["all_pass"]},
            "pawl": {k: v for k, v in pw.items() if not isinstance(v, (list, dict))}, "pieces": pcs,
            "pieces_pass": all(v["pass"] and v["watertight"] for v in pcs.values())}


# ======================================================================================= record
def _f(v, n=2):
    return f"{v:.{n}f}"


def _oz(g):
    return f"{g / 28.3495:.2f} oz"


def compute(log=print) -> dict:
    """Everything from the caches (FEA, body checks, export) and the files on disk -> analysis/h1_lanes.json."""
    from . import bag_attach as BA
    from . import h1_fairleads as HF
    hs = hinge_study(log=None)
    pin = hinge_pin()
    lugs = lug_study(log=None)
    ex = json.loads((OUT / "export_info.json").read_text())
    PD = HF.PRINT_DIR
    bed = {nm: bed_fit(PD / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    sc = slice_checks()
    body = {}
    p = REPO / "outputs" / "h1_buckling" / f"check_{BODY_CHECK}.json"
    if p.exists():
        new = json.loads(p.read_text())
        old = json.loads((REPO / "outputs" / "h1_buckling" / f"check_{BODY_BEFORE}.json").read_text())
        for b in ("fine_sm8", "fine", "beam", "fine_sm8.cyc"):
            if b in new and b in old:
                body[b] = {t: {"strength": round(float(d[b]["min"]["strength"]), 3),
                               "fatigue": round(float(d[b]["min"]["fatigue"]), 3),
                               "creep": round(float(d[b]["min"]["creep"]), 3),
                               "buckling": round(float(d[b]["buckling_min"]), 3),
                               "joint_s": round(float(d[b]["joint_strength"]), 2),
                               "joint_f": round(float(d[b]["joint_fatigue"]), 2)} for t, d in (("before", old), ("after", new))}
        body["raster_g"] = {"before": old.get("raster_g"), "after": new.get("raster_g")}
    q = OUT / "body_extra.json"
    if q.exists():
        e = json.loads(q.read_text())
        body["cradle"] = {t: {k: e[t][k] for k in ("min", "buckling_min", "joint_strength", "joint_fatigue")
                              if k in e[t]} for t in ("cradle", "cradle_on_stay")}
        body["voxels"] = e["voxels"]
    ur = json.loads((ANALYSIS / "us_route.json").read_text())
    urs = {n: {"layout": L_["layout"], "worst_clear_mm": L_["worst_clear_mm"], "pass": L_["pass"]}
           for n, L_ in ur["layouts"].items()}
    he = json.loads((OUT / "he_check.json").read_text()) if (OUT / "he_check.json").exists() else None
    pieces = json.loads((OUT / "pieces_hf.json").read_text()) if (OUT / "pieces_hf.json").exists() else {}
    a_new = ex["assembled"]["g"]
    arms_g = ex["fairleads_bl042"]["lugs_bl049"]["arms_g"]
    led = None
    try:
        from huntkit.mass import ledger as LG
        import re as _re             # BL-051: the row is 'attachment: 7075 pins (<n>)' (n = 12 since BL-051, 8 before)
        row = [r for r in LG.parts("corrie_b2_h1_v2", "M")
               if _re.fullmatch(r"attachment: 7075 pins \(\d+\)", r["name"])][0]
        led = row["g"] / float(_re.search(r"\((\d+)\)", row["name"]).group(1))
    except Exception:            # pragma: no cover
        led = 19.3 / 8.0
    ch = pin[pin["chosen"]]
    mass = {"assembled_g": a_new, "assembled_bl047_g": BL047_PRINT_G["assembled"],
            "lower_g": ex["lower"]["g"], "upper_g": ex["upper"]["g"],
            "delta_print_g": round(a_new - BL047_PRINT_G["assembled"], 1), "lug_arms_g": round(arms_g, 2),
            "print_rest_g": round(a_new - BL047_PRINT_G["assembled"] - arms_g, 2),
            "hinge_pin_g": ch["mass_g"], "pin_booked_g": round(led, 3),
            "hinge_pins_delta_g": round(2 * (ch["mass_g"] - led), 2)}
    mass["total_frame_delta_g"] = round(mass["delta_print_g"] + mass["hinge_pins_delta_g"], 1)
    res = {"date": "2026-11-13", "ticket": "BL-049",
           "published": {"US1_X": US1_X, "US1_Z": US1_Z, "US2_X": US2_X, "US2_Z": US2_Z, "STAY_X": STAY_X,
                         "CHANNEL_ENTRY_X": CHANNEL_ENTRY_X, "HINGE_PIN_MATERIAL": HINGE_PIN_MATERIAL,
                         "HINGE_PIN_D": HINGE_PIN_D, "hinge_eye_envelope": BA.HINGE_EYE_ENVELOPE,
                         "us_eye_envelope": {n: BA.imus_eye_envelope(n) for n in LANE_X}},
           "hinge": {"geom_bl042": dataclasses.asdict(BA.HINGE_GEOM_BL042), "geom_bl049": dataclasses.asdict(BA.HINGE_GEOM),
                     "study": {k: v for k, v in hs.items() if k != "directions"}, "pin": pin},
           "lugs": lugs, "arms": ARM, "export": ex, "bed": bed, "slice_checks": sc, "body": body,
           "us_route": {"layouts": urs, "test_piece": ur.get("test_piece"), "station_move": ur.get("station_move")},
           "he_check": he, "pieces": pieces, "mass": mass}
    res = {"superseded_by": json.loads(RESULTS.read_text()).get("superseded_by") if RESULTS.exists() else None, **res}
    RESULTS.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
    if log:
        log(f"  wrote {RESULTS.relative_to(REPO)}")
    return res


# ======================================================================================= figures
def _fill(ax, geom, fc, ec="#1d1d1f", lw=0.5, alpha=1.0):
    for poly in getattr(geom, "geoms", [geom]):
        if poly.is_empty or poly.geom_type != "Polygon":
            continue
        ax.fill(*poly.exterior.xy, fc=fc, ec=ec, lw=lw, alpha=alpha)
        for h in poly.interiors:
            ax.fill(*h.xy, fc="white", ec=ec, lw=lw * 0.8)


def plot_hinge(res: dict, before_stl: Path, path: Path) -> str:
    """Hinge before (BL-047 print) / after (BL-049): section on the pin axis (plane z 60) and through the inboard
    cheek (plane x), and the fatigue SF per sim direction at the 1019 N row."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from . import bag_attach as BA
    from . import h1_fairleads as HF
    fig = plt.figure(figsize=(13.0, 7.2), dpi=100)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 1.5])
    for row, (lab, stl, g) in enumerate((("BL-047 print", before_stl, BA.HINGE_GEOM_BL042),
                                         ("BL-049", HF.PRINT_DIR / "h1_assembled.stl", BA.HINGE_GEOM))):
        m = trimesh.load(stl)
        p = next(q for q in HF.placed() if q["id"] == "hinge_R")
        S = HF._zplane(m, 60.0)
        ax = fig.add_subplot(gs[row, 0])
        _fill(ax, S, "#9aa3ad")
        ax.add_patch(plt.Circle((p["x"], p["y_pin"]), 2.5, color="#2e86de"))
        e = HF.eye_polygon(p["x"], p["y_pin"] - 2.5, BA.HINGE_EYE_ENVELOPE if row else
                           dict(BA.HINGE_EYE_ENVELOPE, eye_margin_mm=1.0), margin=False)
        ax.fill(*e.exterior.xy, color="#f39c12", alpha=0.7, lw=0)
        ax.set_xlim(p["x"] - 26, p["x"] + 26)
        ax.set_ylim(-14, 30)
        ax.set_aspect("equal")
        ax.set_title(f"{lab}: hinge R, plane z 60 (pin axis)\nfloor {g.floor_proud:.1f} above the stay, gap "
                     f"{g.gap_under_pin:.1f} mm, cheek {g.cheek:.0f} mm", fontsize=8.5, loc="left")
        ax.set_xlabel("x mm", fontsize=7)
        ax.set_ylabel("y mm (to the bag)", fontsize=7)
        ax.tick_params(labelsize=7)
        X = HF._xplane(m, p["x"] - (g.throat / 2 + g.cheek / 2))
        ax = fig.add_subplot(gs[row, 1])
        _fill(ax, X, "#9aa3ad")
        ax.add_patch(plt.Circle((p["y_pin"], 60.0), 3.5, fill=False, ec="#c0392b", lw=1))
        ax.axhline(60 + g.z_top, c="#27ae60", ls=":", lw=1)
        ax.axhline(60 - g.half_z, c="#27ae60", ls=":", lw=1)
        ax.set_xlim(-16, 32)
        ax.set_ylim(30, 112)
        ax.set_aspect("equal")
        ax.set_title(f"inboard cheek, plane x {p['x'] - (g.throat / 2 + g.cheek / 2):.0f}\ncheek z "
                     f"{60 - g.half_z:.0f}-{60 + g.z_top:.0f} (dotted)", fontsize=8.5, loc="left")
        ax.set_xlabel("y mm", fontsize=7)
        ax.set_ylabel("z mm", fontsize=7)
        ax.tick_params(labelsize=7)
    ax = fig.add_subplot(gs[:, 2])
    st = res["hinge"]["study"]
    keys = [k for k in st["bl049"]["rows"] if k != "revC"]
    y = np.arange(len(keys) + 1)
    for off, tag, col in ((-0.27, "bl047_print", "#c0392b"), (0.0, "bl042_no_relief", "#e5a50a"), (0.27, "bl049", "#2c7a4b")):
        vals = [st[tag]["rows"][k]["fatigue"] for k in keys] + [st[tag]["rows"]["revC"]["fatigue"]]
        ax.barh(y + off, vals, height=0.26, color=col, label={"bl047_print": "BL-047 print (BL-042 hinge + relief groove)",
                                                               "bl042_no_relief": "BL-042 hinge, no groove",
                                                               "bl049": "BL-049 hinge"}[tag])
    ax.axvline(1.0, c="#1d1d1f", lw=1)
    ax.axvline(FAT_GOAL, c="#1d1d1f", lw=1, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([k.replace("|", " ") for k in keys] + ["rev C (beam)"], fontsize=7.5)
    ax.set_xlabel("fatigue SF at the 1019 N row (1e5 x 1.6 g, PAHT-CF FI99), 1 mm voxels", fontsize=8)
    ax.set_xlim(0, 4.0)
    ax.legend(fontsize=7.5, loc="center right")
    ax.set_title("Hinge cheek fatigue per sim pull direction (inboard + up)\nrequired 1.0 (solid), goal 1.15 (dashed)",
                 fontsize=9, loc="left")
    fig.suptitle("BL-049: the hinge fairlead grown for the sims' inboard-up eye pull (cheeks 10 mm, 27 mm up the stay, "
                 "floor 1 mm lower, no groove)", fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


def plot_lugs(res: dict, path: Path) -> str:
    """Lug FEA utilisation (fatigue FI / allowable on the governing cradle pull) on the pin-height section and the
    deflected stay-lug-fairlead outline, US1 and US2."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import bag_attach as BA
    pa = BA._paht()
    fig, axs = plt.subplots(1, 2, figsize=(13.0, 5.6), dpi=100)
    for ax, name in zip(axs, ("us1", "us2")):
        gi = lug_geom_inputs(name)
        p = gi["p"]
        L = lug_loads(name)
        k = res["lugs"][name]["worst_fatigue"]["load"]
        f = lug_fea(p["geom"], p["stay_r"], gi["xoff"], gi["arm"], {k: L[k]["vec"]}, h=1.0, field=k)
        fd = f["loads"]["_field"]
        gr = L[k]["g_times_req"]
        util = fd["fi"] * G_WALK / gr / pa["fat"]            # fatigue utilisation (1 = SF 1.0)
        c = fd["cen"]
        sel = np.abs(c[:, 2] - 0.5) <= 0.5                    # the element layer through the pin height
        sc = ax.scatter(c[sel, 0] + STAY_X, c[sel, 1] + p["yc"], c=np.clip(util[sel], 0, 1.2), s=9, marker="s",
                        cmap="viridis", vmin=0, vmax=1.2)
        u = fd["u_elem"][sel]
        ax.set_aspect("equal")
        ax.set_xlabel("frame x mm (R side)")
        ax.set_ylabel("frame y mm (to the bag)")
        r = res["lugs"][name]
        ax.set_title(f"{name.upper()} lug at x {LANE_X[name]:.0f}, z {LANE_Z[name]:.0f}: {k}\n"
                     f"fatigue SF {r['worst_fatigue']['fatigue']:.2f} (stub model, junction), strength "
                     f"{r['worst_strength']['sf']:.2f}; max deflection {u.max():.2f} mm at {L[k]['vec'] and np.linalg.norm(L[k]['vec']):.0f} N",
                     fontsize=8.5, loc="left")
        plt.colorbar(sc, ax=ax, fraction=0.035, label="fatigue utilisation (FI / allowable)")
    fig.suptitle("BL-049: US lane lugs, voxel FEA on a fixed stay stub (pin-height section). Cradle 720 N factored, "
                 "1.6 g / 2.4 g fatigue", fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


def plot_print(res: dict, path: Path) -> str:
    """The lower half seen from the bag (x-z silhouette of the print) with the lanes, and its plate footprint on the
    H2S bed at the best rotation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Rectangle
    from . import h1_fairleads as HF
    m = trimesh.load(HF.PRINT_DIR / "h1_assembled.stl")
    fig, axs = plt.subplots(1, 2, figsize=(13.5, 6.4), dpi=100, gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axs[0]
    v = m.vertices
    f = m.faces[(v[m.faces][:, :, 2] < 240).all(axis=1)]
    tri = v[f][:, :, [0, 2]]
    from matplotlib.collections import PolyCollection
    ax.add_collection(PolyCollection(tri, facecolor="#8a8f98", edgecolor="none"))
    for p in HF.placed():
        if p["z"] > 200:
            continue
        g = p["geom"]
        col = {"hinge": "#7f8c8d", "us1": "#2980b9", "us2": "#8e44ad"}.get(p["name"], "#bbb")
        hx = g.throat / 2 + g.cheek
        ax.add_patch(Rectangle((p["x"] - hx, p["z"] - g.half_z), 2 * hx, g.half_z + g.z_top, fill=False, ec=col, lw=1.2))
        if p["side"] == "R":
            ax.text(p["x"] + hx + 2, p["z"], p["name"], fontsize=8, color=col, va="center")
    ax.set_xlim(-200, 200)
    ax.set_ylim(-5, 240)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x mm")
    ax.set_ylabel("frame z mm")
    ax.set_title(f"Lower half from the bag side: US1 lugs at x +/-{US1_X:.0f}, US2 at x +/-{US2_X:.0f}\n"
                 f"assembled {res['mass']['assembled_g']:.1f} g (BL-047 {res['mass']['assembled_bl047_g']:.1f} g, "
                 f"{res['mass']['delta_print_g']:+.1f} g; lug arms {res['mass']['lug_arms_g']:.1f} g)", fontsize=9, loc="left")
    ax = axs[1]
    mf = trimesh.load(HF.PRINT_DIR / "h1_lower_flat.stl")
    b = res["bed"]["lower"]
    th = math.radians(b["deg"])
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    P = mf.vertices[mf.faces][:, :, :2] @ R.T
    P -= P.reshape(-1, 2).min(axis=0)
    ax.add_collection(PolyCollection(P, facecolor="#8a8f98", edgecolor="none"))
    w, h = P.reshape(-1, 2).max(axis=0)
    ax.add_patch(Rectangle((0, 0), BED_MM[0] if w >= h else BED_MM[1], BED_MM[1] if w >= h else BED_MM[0], fill=False,
                           ec="#c0392b", lw=1.5, ls="--"))
    ax.set_xlim(-10, max(w, 345) + 10)
    ax.set_ylim(-10, max(h, 345) + 10)
    ax.set_aspect("equal")
    ax.set_title(f"Lower half on the H2S bed (340 x 320, red dashed), best rotation {b['deg']:.1f} deg:\n"
                 f"{b['w_mm']:.1f} x {b['h_mm']:.1f} mm, {'FITS' if b['fits'] else 'DOES NOT FIT'} "
                 f"({'+' if b['over_mm'] > 0 else ''}{b['over_mm']:.1f} mm; brim 8 mm not counted)", fontsize=9, loc="left")
    fig.suptitle("BL-049 print: the lanes on lug arms. The US2 lugs make the lower half 367 mm wide", fontsize=10.5,
                 x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


# ======================================================================================= markdown
ASSUMPTIONS = [
    ("HINGE-ROW", "The hinge eye's factored row is 1019 N (bl047_frame_items.HINGE_ROW_N, 3.0 x the 1 g sim eye); the "
     "fairlead fatigue is judged at 1.6 / 3.0 of it (543 N, the load standard's walking peak) and also shown on the "
     "pin's 2.4 g basis (679 N).", "SEW-F HE rows and the T2 meat test with a load pin at one stay foot (FLOOR_SPAN)."),
    ("FI99-RULE", "Cheek and lug strength / fatigue use the record's FI99 rule (99th percentile of the PAHT-CF layer "
     "failure index over the fairlead / lug, 1 mm voxels). The single hottest voxel is lower (BL-049 hinge: 0.56 on "
     "the governing direction, BL-047 print 0.33): a 1 mm voxel corner is not a real fillet, but it is not proven "
     "either.", "HE-FIT re-cut piece pulled to 1.6 x 340 N inboard-up for 1e5 cycles on the CA-1 rig (or CA-1 "
     "coupons with the cheek-root corner)."),
    ("STAY-STUB", "The lug FEA fixes a stay stub (+/-22-23 mm) at its ends and leaves out the lower branch the US1 arm "
     "merges into: its junction numbers are a lower bound. The whole-body check carries the lane moment at the stay "
     "node.", "Strain gauge at the US2 arm root in the T1 carry test; MT-1 cradle pull on the first article."),
    ("LANE-MOMENT", "In the body check each under-strap pin load stays on its stay node and gains the moment of the "
     "lateral lane offset (beam sets carry no under-strap load; their z 90 / 130 node loads are the meat-strap "
     "reactions).", "Same as STAY-STUB."),
    ("PIN-KS", "Hinge pin fatigue: rotating-beam limit x 0.9 (machined / ground), Goodman to R 0 on the UTS, as "
     "h1_fairleads.pin_bending.", "Supplier fatigue figure for the Ti-6Al-4V pin stock."),
    ("PIN-L", "Hinge pin length = throat + 2 cheeks + 4 mm (head / clip groove), 44 mm.", "The bought pin."),
    ("SUPPORTS", "The lug arms' undersides overhang (cantilevers off the stay, layer normal y): tree supports under the "
     "four arms; the rest of the body prints as before.", "First article: slicer preview and the arm underside finish."),
    ("SHEET-CLEAR", "The US1 arm (z 90-106) stays 6 mm under the spreader sheet's z 112 edge; the US2 arm root (z "
     "127-157) fills the sheet's US2 notch, which kept NOTCH_CLEAR 6 mm round the old fairlead.", "Spreader dry fit "
     "on the first article (the notch may be trimmed; the spreader is not re-cut here)."),
]


def _reg_min(lug: dict, region: str) -> float:
    return min(r["regions"][region]["fatigue"] for r in lug["rows"].values() if region in r["regions"])


SUPERSEDED_NOTE = (
    "> **SUPERSEDED (2026-11-13) for the print, the bed fit and the US2 lug: see `h1_bedfit.md` (BL-050 A: bolt-on US2 "
    "outer clevis, the halves fit the H2S bed) and `h1_crown.md` (BL-051: the stay crown that `strip_old_us` cut away "
    "over the old US1 / US2 stub sites is restored; lug FEA on the real stay section; body re-checked).** The hinge "
    "fairlead, hinge pin and lane positions below still stand. Print masses, bed footprints, slice checks and the "
    "body numbers in this file are the BL-049 print (lower half 367.5 mm wide, crown cut): do not build from them.\n")


def write_md(res: dict, shots: list) -> str:
    from . import bag_attach as BA
    h = res["hinge"]["study"]
    pin = res["hinge"]["pin"]
    g0, g1 = BA.HINGE_GEOM_BL042, BA.HINGE_GEOM
    m = res["mass"]
    L = res["lugs"]
    w = []
    a = w.append
    a("# H1 hinge for the inboard-up pull, and the US stations on lane lugs (BL-049)\n")
    a(SUPERSEDED_NOTE)
    a("structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-049-hinge-and-us-lanes.md`. Code "
      "`huntkit/gendesign/h1_lanes.py` (`python -m huntkit.gendesign.h1_lanes --fea | --body | --export`), geometry "
      "`bag_attach.HINGE_GEOM` (BL-049) and `h1_fairleads.placed` (lanes), print `frame_h1.print_mesh`; tests "
      "`tests/test_h1_lanes.py`. Results `h1_lanes.json`. Units mm, N, g (imperial in brackets).\n")
    a("## Summary\n")
    s49, s47 = h["bl049"], h["bl047_print"]
    a(f"- **Hinge fairlead: fatigue in the sims' inboard-up direction {s47['sim']['fatigue']:.2f} -> "
      f"{s49['sim']['fatigue']:.2f} at the 1019 N row** (goal 1.15, worst row {s49['sim_worst'].replace('|', ' ')}, unit "
      f"(0.917, 0.034, 0.397)); 0.75 mm voxels {h['bl049_h0.75']['sim']['fatigue']:.2f}. Strength "
      f"{s49['sim']['strength']:.2f}, creep {s49['sim']['creep']:.2f}; on the pin's 2.4 g basis "
      f"{s49['sim']['fatigue_2p4']:.2f}. Rev C direction: strength {s49['revC']['strength']:.2f}, fatigue "
      f"{s49['revC']['fatigue']:.2f}. The ticket's 0.86 (BL-047) left out BL-047's own relief groove: the "
      f"print as it was reads **{s47['sim']['fatigue']:.2f}** (no groove {h['bl042_no_relief']['sim']['fatigue']:.2f}).")
    a(f"- **What changed:** cheeks {g0.cheek:.0f} -> **{g1.cheek:.0f} mm**, reaching **{g1.z_top:.0f} mm up the stay** "
      f"above the pin (was {g0.half_z:.0f}; below the pin unchanged at {g1.half_z:.0f}, so the HE box keeps its 5 mm); "
      f"throat floor lowered 1 mm over the whole throat ({g0.floor_proud:.1f} -> {g1.floor_proud:.1f} mm above the "
      f"stay; gap under the pin {g0.gap_under_pin:.1f} -> **{g1.gap_under_pin:.1f} mm**) in place of BL-047's relief "
      f"groove, which sat at the hot corner. Pin centre, throat (20) and tip unchanged.")
    c = pin[pin["chosen"]]
    o = pin["bl049|alu_7075_t6"]
    a(f"- **Hinge pin: one check load, 1019 N.** 5 mm 7075-T6 fails it (yield {o['sf_yield']:.2f}, fatigue "
      f"{o['sf_fatigue']:.2f} on the 2.4 g basis; BL-042 span {pin['bl042|alu_7075_t6']['sf_fatigue']:.2f}). "
      f"**5 mm Ti-6Al-4V, {c['length_mm']:.0f} mm long: yield {c['sf_yield']:.2f}, fatigue {c['sf_fatigue']:.2f}** "
      f"(3.0 basis {c['sf_fatigue_3p0_basis']:.2f}), {c['mass_g']:.1f} g a pin. The eye, sleeve and hole stay 5 / 7.2.")
    a(f"- **US lanes on lugs:** US1 at x +/-{US1_X:.0f}, z {US1_Z:.0f} (inboard), US2 at x +/-{US2_X:.0f}, z "
      f"{US2_Z:.0f} (outboard), each fairlead (BL-045 eye geometry, `imus_eye_envelope` unchanged) on a tapered printed "
      f"arm from the stay. Lug FEA (stub model, conservative): US1 strength {L['us1']['worst_strength']['sf']:.2f}, "
      f"fatigue {L['us1']['worst_fatigue']['fatigue']:.2f}; US2 {L['us2']['worst_strength']['sf']:.2f} / "
      f"{L['us2']['worst_fatigue']['fatigue']:.2f} (governing: the bag-off cradle at the arm-stay junction). Bag-on "
      f"(444 / 296 N) passes with margin.")
    b = res["bed"]["lower"]
    a(f"- **Print re-exported**, slice checks pass (12 / 12 fairleads with eye stacks, spine channel, pawl swing). "
      f"**But the lower half is now {b['extents_mm'][0]:.0f} mm wide and does not fit the H2S bed** (best rotation "
      f"{b['w_mm']:.0f} x {b['h_mm']:.0f} mm against 340 x 320, before the 8 mm brim). See owner decisions.")
    a(f"- **Mass:** printed body {m['assembled_bl047_g']:.1f} -> **{m['assembled_g']:.1f} g ({m['delta_print_g']:+.1f} g, "
      f"{m['delta_print_g'] / 28.3495:+.2f} oz)**: lug arms {m['lug_arms_g']:+.1f} g, the rest (hinge growth, lane "
      f"fairleads, old US stubs out) {m['print_rest_g']:+.1f} g; Ti hinge pins {m['hinge_pins_delta_g']:+.2f} g. Ledger "
      f"rows BL049.")
    a("")
    a("## 1. Hinge: what the sims pull, and where it bites\n")
    a("The 12 rev 3 fine sim rows (`hinge_eye_vectors.json`) all pull the frame's hinge pin inboard (0.47-0.92 of the "
      "force) and up. The sideways part is carried by the eye's edge on the inboard cheek's inner face "
      "(`fairlead_fea` rule), so the critical spot is the corner where that cheek meets the throat floor "
      "(peak at x -9.5..-10.5 from the throat centre, 1 mm above the floor). BL-047's m-1 relief groove (1 mm deep, "
      "1.5 mm wide, along each cheek) was cut exactly there.\n")
    a("| hinge (1 mm voxels, unit directions scaled to 1019 N) | sim worst row | strength | fatigue | fatigue 2.4 g basis | creep | hottest voxel fatigue | rev C strength / fatigue |")
    a("|---|---|---:|---:|---:|---:|---:|---|")
    for tag, lab in (("bl047_print", "BL-047 print (BL-042 hinge + groove)"), ("bl042_no_relief", "BL-042 hinge, no groove"),
                     ("bl049", "**BL-049**")):
        r = h[tag]
        a(f"| {lab} | {r['sim_worst'].replace('|', ' ')} | {r['sim']['strength']:.2f} | {r['sim']['fatigue']:.2f} | "
          f"{r['sim']['fatigue_2p4']:.2f} | {r['sim']['creep']:.2f} | {r['sim']['fatigue_fimax']:.2f} | "
          f"{r['revC']['strength']:.2f} / {r['revC']['fatigue']:.2f} |")
    if "bl049_ellipse" in h:
        r = h["bl049_ellipse"]
        a(f"| bl049, stay as a 6 mm ellipse (STAY-AX) | {r['sim_worst'].replace('|', ' ')} | {r['sim']['strength']:.2f} | "
          f"{r['sim']['fatigue']:.2f} | {r['sim']['fatigue_2p4']:.2f} | {r['sim']['creep']:.2f} | "
          f"{r['sim']['fatigue_fimax']:.2f} | {r['revC']['strength']:.2f} / {r['revC']['fatigue']:.2f} |")
    for tag in ("bl047_print", "bl049"):
        r = h[f"{tag}_h0.75"]
        a(f"| {tag}, 0.75 mm voxels | {r['sim_worst'].replace('|', ' ')} | {r['sim']['strength']:.2f} | {r['sim']['fatigue']:.2f} | "
          f"{r['sim']['fatigue_2p4']:.2f} | {r['sim']['creep']:.2f} | {r['sim']['fatigue_fimax']:.2f} | "
          f"{r['revC']['strength']:.2f} / {r['revC']['fatigue']:.2f} |")
    a("")
    a("Requirement: strength >= 1.0 on the factored row, fatigue >= 1.0 (goal 1.15, BL-021 scatter), creep >= 1.0. "
      "Fatigue: 1e5 x 1.6 g on the 1 g force (1019 / 3.0 = 340 N; 543 N peak). The groove is mesh-sensitive (a notch; "
      "0.62 at 1 mm, 0.49 at 0.75 mm); the BL-049 hinge is not (1.30 / 1.27).\n")
    a("**Sweep (1 mm voxels, all 12 rows; `outputs/h1_lanes`):** thicker cheeks alone barely help (8 -> 12 mm: 0.81 "
      "-> 0.88), height helps (cheek +/-13 symmetric: 1.17), but the cheek cannot grow down (the HE box sits 5 mm "
      "under it). Lowering the floor 1 mm in place of the groove costs a little lever (0.81 -> 0.67 at the old height) "
      "and removes the notch; with the cheek 27 mm up and 10 mm thick it reaches 1.30.\n")
    a("**What the bag must meet (import `bag_attach.HINGE_EYE_ENVELOPE`):** gap under the pin "
      f"{g1.gap_under_pin:.1f} mm (was {g0.gap_under_pin:.1f}: 1 mm more at the throat centre; the HE-FIT worst corner "
      "goes 0.68 -> 1.09 mm at a 1.6 mm ply, corrie_f_body 24.6), floor "
      f"{g1.floor_proud:.1f} mm above the stay surface, cheek reach below the pin {g1.half_z:.0f} mm (unchanged; "
      f"`cheek_half_z_mm`), new keys `cheek_up_mm` {g1.z_top:.0f} and `cheek_thickness_mm` {g1.cheek:.0f} (outer "
      f"faces at +/-{g1.throat / 2 + g1.cheek:.0f} mm from the stay: 2 mm more a side). Pin centre, throat and tip "
      "heights unchanged.\n")
    he = res.get("he_check")
    if he:
        a(f"Bag-side HE check on the re-cut HE-FIT piece (`he_stl_check` via `bl047_frame_items.he_check`): pass "
          f"{he['as_written']['pass']}; worst under-pin clearance {he['as_written']['worst_under_pin_clear_mm']:.2f} mm, "
          f"at the 0.15 mm print tolerance {he['tol_0p15']['worst_under_pin_clear_mm']:.2f} mm (>= 0.5: "
          f"{he['tol_0p15']['meets_0p5_everywhere']}), box top to cheek {he['as_written']['min_box_top_to_cheek_mm']:.2f} "
          "mm.\n")
    a("### Hinge pin, one number\n")
    a("| pin | span mm | M N mm | sigma MPa | yield SF | fatigue SF (2.4 g: 679 N) | fatigue SF (3.0: 543 N) | g |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    for k, v in pin.items():
        if k == "chosen":
            continue
        a(f"| {k.replace('|', ', ')} | {v['span_mm']:.0f} | {v['M_nmm']:.0f} | {v['sigma_mpa']:.0f} | {v['sf_yield']:.2f} | "
          f"{v['sf_fatigue']:.2f} | {v['sf_fatigue_3p0_basis']:.2f} | {v['mass_g']:.2f} |")
    a("\nM = F (2L - b) / 8 (load spread over the throat, reacted at the cheek centres). **Chosen: 5 mm Ti-6Al-4V** "
      "(record `ti_6al_4v`: S-basis yield 827 MPa, fatigue limit 510 MPa x 0.9). The 7075 pin fails at 1019 N on both "
      "spans; a 6 mm 7075 pin would need a bigger hole, sleeve and eye envelope.\n")
    a("## 2. US lanes on lug arms\n")
    a(f"Stations (published in `h1_lanes`, for BL-050): `US1_X` {US1_X:.0f}, `US1_Z` {US1_Z:.0f}; `US2_X` {US2_X:.0f}, "
      f"`US2_Z` {US2_Z:.0f} (mirror x for L); B-16 channel ends at the lane x (`CHANNEL_ENTRY_X`). The pin, floor and tip "
      "heights in y are the station's `imus_eye_envelope` values above the stay surface at that z, as before.\n")
    a("| arm | root section (at the stay) | tip section (at the fairlead) |")
    a("|---|---|---|")
    for n, v in ARM.items():
        a(f"| {n} | y from yc {v['root']['y_lo']:+.0f} to the stay's bag face, z {v['root']['z'][0]:+.0f} / "
          f"{v['root']['z'][1]:+.0f} | y from yc {v['tip']['y_lo']:+.0f} to the fairlead floor, z "
          f"{v['tip']['z'][0]:+.0f} / {v['tip']['z'][1]:+.0f} |")
    a("\nLinear taper (hull), 3 mm edge radius. US1 runs at z 90-106: 3 mm over the BL-049 hinge cheek top (z 87), 6 mm "
      "under the spreader sheet's bottom edge (z 112); its underside merges into the lower branch at x 74-93. US2's "
      "root (z 127-157) fills the spreader's US2 notch.\n")
    a("**Loads** (frame side, factored): bag-off cradle 720 N at 2.4 (1.6 g x 1.5; fatigue at 480 N), aft and down at "
      "the cradle angle; bag-on cam-tight US1 444 N / US2 296 N at 3.0, straight down, down + 30 deg towards the wearer "
      "and along the drape's first path segment off the pin; each also +/-10 deg out of plane (US-FLEET).\n")
    a("| lug | load | strength | fatigue | creep | governing region |")
    a("|---|---|---:|---:|---:|---|")
    for n, v in L.items():
        for k in ("cradle", "cradle|fleet_in", "cradle|fleet_out", "bagon_down", "bagon_fore30", "bagon_drape"):
            r = v["rows"][k]
            a(f"| {n} | {k.replace('|', ' ')} ({r['force_n']:.0f} N) | {r['sf']:.2f} | {r['fatigue']:.2f} | {r['creep']:.2f} | "
              f"{r['governing_region']} |")
    a("\nRegions: FI99 over the fairlead, over the arm, and over the arm's first 6 mm off the stay ('root'); the "
      "record's whole-yoke FI99 is higher. The stub leaves out the lower branch (US1) and the frame beyond +/-22 mm "
      "(ASSUMPTION STAY-STUB), so 'root' is a lower bound; "
      f"**US1 {_reg_min(L['us1'], 'root'):.2f} at the root is below 1.0 on this model** (US2 "
      f"{_reg_min(L['us2'], 'root'):.2f}); on the arm itself US1 reads {_reg_min(L['us1'], 'arm'):.2f} and US2 "
      f"{_reg_min(L['us2'], 'arm'):.2f}, the fairleads {_reg_min(L['us1'], 'fairlead'):.2f} / "
      f"{_reg_min(L['us2'], 'fairlead'):.2f}. On the whole voxel body (the branch in, section 3) the US1 junction "
      "governs the cradle at fatigue " + (f"{res['body']['cradle']['cradle']['min']['fatigue']:.2f}"
                                          if res.get('body', {}).get('cradle') else "n/a") +
      ". Fairlead pins (5 mm 7075) at the 720 N cradle: yield "
      f"{L['us1']['pin_7075_cradle']['sf_yield']:.2f}, fatigue {L['us1']['pin_7075_cradle']['sf_fatigue']:.2f}.\n")
    a("## 3. Body checks on the lanes body\n")
    body = res.get("body", {})
    if body:
        a("h1_buckling.full_check on the voxel body as printed (BL-046 body + the old US stubs stripped + the lug "
          "arms in), loads from the real crown (BL-046 `_real`), the sim sets' under-strap loads moved to the lanes "
          "(ASSUMPTION LANE-MOMENT). Before = `check_m1_u2.5_im3_bl046_real`.\n")
        a("| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after | joint S / F after |")
        a("|---|---|---|---|---|---|")
        for bb in ("fine_sm8", "fine", "beam", "fine_sm8.cyc"):
            if bb in body:
                x, y = body[bb]["before"], body[bb]["after"]
                a(f"| {bb} | {x['strength']:.3f} / {y['strength']:.3f} | {x['fatigue']:.3f} / {y['fatigue']:.3f} | "
                  f"{x['creep']:.3f} / {y['creep']:.3f} | {x['buckling']:.3f} / {y['buckling']:.3f} | "
                  f"{y['joint_s']:.2f} / {y['joint_f']:.2f} |")
        if "cradle" in body:
            cl, cs = body["cradle"]["cradle"], body["cradle"]["cradle_on_stay"]
            a(f"\nBag-off cradle as its own sets (720 N at each of the four US pins, aft and down, +/-10 deg fleet; "
              f"the aft pull reacted by the meat bearing on the stay faces z 60-155, the rest at the hip pivot; never "
              f"part of the body record before; governing spot: the US1 arm root on the stay, z 107): on the lanes strength {cl['min']['strength']:.2f}, fatigue "
              f"{cl['min']['fatigue']:.2f}, buckling {cl['buckling_min']:.2f}; same loads on the stays (BL-045 print) "
              f"{cs['min']['strength']:.2f} / {cs['min']['fatigue']:.2f} / {cs['buckling_min']:.2f}.\n")
        a("`fine_sm8.cyc` fatigue stays below 1 (BL-024 cinch-cycled set, R1 hold for MT-1), as before this ticket.\n")
    a("## 4. Print files and checks\n")
    ex = res["export"]
    a("| file | g | watertight | shells | footprint mm | bed (best rotation) |")
    a("|---|---:|---|---:|---|---|")
    a(f"| h1_assembled.stl | {ex['assembled']['g']:.1f} | {ex['assembled']['watertight']} | {ex['assembled']['shells']} | | |")
    for nm in ("lower", "upper"):
        e, bb = ex[nm], res["bed"][nm]
        a(f"| h1_{nm}_flat.stl | {e['g']:.1f} | {e['watertight']} | {e['shells']} | "
          f"{' x '.join(f'{v:.0f}' for v in e['footprint_mm'])} | {bb['w_mm']:.0f} x {bb['h_mm']:.0f} at {bb['deg']:.0f} deg: "
          f"{'fits' if bb['fits'] else '**does not fit**'} (brim {'fits' if bb['fits_with_brim'] else 'does not fit'}) |")
    sc = res["slice_checks"]
    a(f"\nSlice checks on `h1_assembled.stl`: fairleads {sum(v['pass'] for v in sc['fairleads'].values())} / "
      f"{len(sc['fairleads'])} pass (eye stacks included); spine channel pass {sc['channel']['pass']} (clear "
      f"{sc['channel']['min']['clear_mm']:.2f} mm, fore wall {sc['channel']['min']['fore_wall_mm']:.2f}); pawl pass "
      f"{sc['pawl']['pass']} (low-profile pawl min {sc['pawl']['lp_min_dist_mm']:.2f} mm over its {sc['pawl']['swing_deg']:.0f} "
      "deg swing). Test pieces sliced the same way: "
      f"{sum(v['pass'] for v in sc.get('pieces', {}).values())} / {len(sc.get('pieces', {}))} stations pass "
      f"({', '.join(sc.get('pieces', {}))}).\n")
    a("| station | x | gap under pin | throat | cheek | cheek height | eye fits | pass |")
    a("|---|---:|---:|---:|---:|---:|---|---|")
    for k, v in sorted(sc["fairleads"].items()):
        a(f"| {k} | {v['x']:.0f} | {v['gap_under_pin']:.2f} | {v['throat']:.1f} | {v['cheek_mm']:.2f} | "
          f"{v['cheek_height_mm']:.1f} | {v['eye_fits']} | {v['pass']} |")
    ur = res["us_route"]
    a("\n'now' = the print with the bag's B-16 channel ends where the pattern has them today (x +/-95): fails, as "
      "BL-048 found; 'print_lanes' = the same print with the channel ends at the lane x (BL-048 'lanes_wide', for "
      "BL-050): passes. 'lanes' / 'lanes_wide' are BL-048's layouts recomputed off the BL-049 hinge (2 mm wider "
      "cheeks), kept as sensitivities.\n")
    a("\n**us_route re-run on this STL** (`designs/pack_5200/us_route.py`, the strap ribbon against the sliced print "
      "on the 15 / 19 / 23 in meat drapes, >= 10 mm required):\n")
    a("| layout | US1 x | US2 x | channel entry | worst clear US1 / US2 mm | pass |")
    a("|---|---:|---:|---|---|---|")
    for n, v in ur["layouts"].items():
        lay = v["layout"]
        a(f"| {n} | {lay['us1']:.1f} | {lay['us2']:.1f} | {lay['entry']['us1']:.0f} / {lay['entry']['us2']:.0f} | "
          f"{v['worst_clear_mm']['us1']:.1f} / {v['worst_clear_mm']['us2']:.1f} | {v['pass']} |")
    tp = ur.get("test_piece") or {}
    if tp:
        a(f"\nTest piece `{tp.get('file')}`: R stay z {tp['z'][0]:.0f}-{tp['z'][1]:.0f}, x {tp['x'][0]:.0f}-"
          f"{tp['x'][1]:.0f} (hinge, US1 lug, US2 lug), {tp['g']:.1f} g, watertight {tp['watertight']}, "
          f"{tp['shells']} shell. HE-FIT (`hefit_hinge_fairlead_R`) and IM3-EC re-cut from the new print too.\n")
    a("## 5. Mass\n")
    a("| item | g | oz |")
    a("|---|---:|---:|")
    for k, lab in (("lug_arms_g", "lug arms (4)"), ("print_rest_g", "hinge growth, lane fairleads, old US stubs out, no groove"),
                   ("delta_print_g", "**printed body, net**"), ("hinge_pins_delta_g", "Ti hinge pins (2) vs 7075 as booked"),
                   ("total_frame_delta_g", "**frame, net**")):
        a(f"| {lab} | {m[k]:+.1f} | {m[k] / 28.3495:+.2f} |")
    a(f"\nPrinted body {m['assembled_g']:.1f} g ({m['assembled_g'] / 453.592:.2f} lb): lower {m['lower_g']:.1f}, upper "
      f"{m['upper_g']:.1f}. Ledger rows BL049 (`huntkit/mass/ledger.py`, source this json).\n")
    a("**Mass reductions that keep the SF (not applied):** (1) the lug arms as I-sections (3 mm webs, flanges top and "
      f"bottom): the arm region has margin (US1 {_reg_min(L['us1'], 'arm'):.2f}, US2 {_reg_min(L['us2'], 'arm'):.2f}), "
      "the root does not, so only outboard of the root, about "
      "-15 g for four arms (estimate, needs the lug FEA re-run); (2) the US1 arm onto the lower branch it already "
      "touches (a short web down to the branch instead of the full-depth root), which also lifts its root SF.\n")
    a("## 6. Assumptions\n")
    for k, t, s in ASSUMPTIONS:
        a(f"- ASSUMPTION {k}: {t} Settled by: {s}")
    a("- Also carried: HE-T, HE-GAP-MARGIN, HE-NECK-TOL, HOLE_REAM, STAY-AX, SIM_BODY, THROAT-Z (h1_fairleads.md 8); "
      "US-FLEET, US-TOPO, DRAPE-US (us_route.json).\n")
    a("## 7. Screenshots\n")
    for s in shots:
        a(f"- `{Path(s).relative_to(REPO)}`")
    DOC.write_text("\n".join(w) + "\n")
    return str(DOC)


def report(log=print) -> dict:
    res = compute(log=log)
    before = Path(OUT / "h1_assembled_bl047.stl")
    if not before.exists():
        import subprocess
        before.write_bytes(subprocess.run(["git", "-C", str(REPO), "show",
                                           "HEAD:designs/pack_5200/print/frame_h1/h1_assembled.stl"],
                                          check=True, capture_output=True).stdout)
    shots = [plot_hinge(res, before, SCREENS / f"{SHOT}1.png"), plot_lugs(res, SCREENS / f"{SHOT}2.png"),
             plot_print(res, SCREENS / f"{SHOT}3.png")]
    for s in (SCREENS / "20261113_BL049_us_1.png", SCREENS / "20261113_BL049_us_2.png"):
        if s.exists():
            shots.append(str(s))
    write_md(res, shots)
    if log:
        log(f"  wrote {DOC.relative_to(REPO)}; screens {shots}")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fea", action="store_true")
    ap.add_argument("--body", action="store_true")
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args(argv)
    if a.fea:
        hinge_study()
        lug_study()
        print(json.dumps(hinge_pin(), indent=1, default=float))
    if a.body:
        r = body_check()
        (OUT / "body_extra.json").write_text(json.dumps({k: r[k] for k in ("cradle", "cradle_on_stay", "voxels")},
                                                         default=float))
    if a.export:
        from . import h1_buckling as B
        from . import h1_fairleads as HF
        info = B.export_print(*B.CHOSEN)
        (OUT / "export_info.json").write_text(json.dumps(info, indent=1, default=str))
        (OUT / "pieces_hf.json").write_text(json.dumps(HF.export_pieces(), indent=1, default=float))
    if not (a.fea or a.body or a.export):
        report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
