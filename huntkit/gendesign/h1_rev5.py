"""BL-053: H1 frame fixes from the fifth review (B-1 printability, M-1 cradle direction, M-2 nut traps, M-3 belly,
M-4 gauge pass values, M-5 pin retention, M-6 strap wrap).

    python -m huntkit.gendesign.h1_rev5 --fea      # lane lugs on the print submodel, 3D cradle loads (one job)
    python -m huntkit.gendesign.h1_rev5            # report: analysis/h1_rev5.md / .json, print_settings.json, screens

Units mm, N, MPa, g. Frame coordinates: x lateral (+ = R side), y towards the bag, z up. Every lug number is on the
R station (L mirrors).

**Submodel.** BL-049..051 checked the lane lugs on a stay STUB (circle or the print's stay section, fixed at +/-22 mm,
no lower branch). Here each lane lug is cut out of the PRINT (``print/frame_h1/h1_assembled.stl``, sliced every voxel
layer, even-odd fill) inside a box that reaches >= 25 mm past the lug on every side, with the BL-053 fixes added as
voxels, solid voxels on the box faces fixed. The US2 joint face (|x| SPLIT_X) is a 1-voxel gap except the two bolt
shanks (the dry butt joint carries no tension; conservative). Loads and rules as ``h1_lanes.lug_fea`` (the
``fairlead_fea`` rule): the pin's y-z force as bearing on the hole band in both cheeks, the pin-axis (x) force as the
eye's edge on the inner face of the cheek it moves towards, FI99 per region with the layer normal = frame y.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
PRINT = PACK / "print" / "frame_h1"
RESULTS = ANALYSIS / "h1_rev5.json"
DOC = ANALYSIS / "h1_rev5.md"
OUT = REPO / "outputs" / "h1_rev5"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL053_"
STAY_X = 115.0

FAT_GOAL = 1.15                    # BL-021 scatter goal (h1_lanes.FAT_GOAL)
STRENGTH_GOAL = 1.5                # ticket item 4
BELLY_DESIGN = 40.0                # ticket item 4: the cradle passes down to a 40 mm belly
E_TI = 110000.0                    # Ti-6Al-4V bolts in the US2 joint (h1 frame_h1.TI E)
G_CRADLE = 2.4                     # cradle rows' g_times_req (1.6 g x 1.5, h1_lanes.US_CRADLE_N basis)


def _U():
    """designs/pack_5200/us_route.py as a module."""
    import importlib
    if str(PACK) not in sys.path:
        sys.path.insert(0, str(PACK))
    return importlib.import_module("us_route")


def _mesh(path: Path | None = None):
    import trimesh
    return trimesh.load(path or PRINT / "h1_assembled.stl", force="mesh")


# ============================================================================================ voxel submodel
def voxelize(mesh, lo, hi, h: float = 1.0) -> tuple:
    """Element-centre occupancy of ``mesh`` in the box [lo, hi] (frame), one z section per voxel layer, even-odd fill
    of the section loops (holes kept). Returns (Grid, solid bool per element, element centres)."""
    from matplotlib.path import Path as MPath
    from .fem import Grid
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    n = np.maximum(np.round((hi - lo) / h).astype(int), 4)
    g = Grid(tuple(int(v) for v in n), h, x0=lo)
    c = g.elem_centers()
    solid = np.zeros(len(c), bool)
    zc = lo[2] + h * (np.arange(n[2]) + 0.5)
    for k, z in enumerate(zc):
        sel = np.where(np.isclose(c[:, 2], z))[0]
        s = mesh.section(plane_origin=[0.0, 0.0, float(z) + 1e-4], plane_normal=[0.0, 0.0, 1.0])
        if s is None:
            continue
        inside = np.zeros(sel.size, int)
        pts = c[sel, :2]
        for d in s.discrete:
            P = np.asarray(d)[:, :2]
            bb = (P.min(axis=0), P.max(axis=0))
            if bb[1][0] < lo[0] or bb[0][0] > hi[0] or bb[1][1] < lo[1] or bb[0][1] > hi[1]:
                continue
            inside += MPath(P).contains_points(pts)
        solid[sel] = (inside % 2) == 1
    return g, solid, c


def station(name: str) -> dict:
    from . import h1_fairleads as HF
    return next(q for q in HF.placed() if q["name"] == name and q["side"] == "R")


BOX = {"us1": {"lo": (34.0, -50.0, 58.0), "hi": (140.0, 32.0, 132.0)},
       "us2": {"lo": (100.0, -40.0, 104.0), "hi": (190.0, 36.0, 182.0)}}
# The boxes reach >= 25 mm past the lug arm / fairlead on every side (US1 includes the hinge fairlead and the lower
# branch it sits on; US2 the clevis). ASSUMPTION SUB-BC: solid cut by the box faces is fixed there (as the stub's end
# caps); the box-size sensitivity is run in ``box_sensitivity``.


def regions(name: str, c: np.ndarray, p: dict) -> dict:
    """Region masks on element centres c (frame): 'fairlead' (the yoke: cheeks + floor within the cheek z span),
    'root' (the arm's first 6 mm off the stay surface, lane side, and the stay under it), 'arm' (between),
    'web' (below the fairlead, down to the lower branch: US1 only), each within 22 mm of the pin in z."""
    g = p["geom"]
    hx = g.throat / 2.0 + g.cheek
    sgn = 1.0 if p["x"] > STAY_X else -1.0
    zr = c[:, 2] - p["z"]
    yl = c[:, 1] - p["yc"]
    near_z = np.abs(zr) <= 22.0
    fair = (np.abs(c[:, 0] - p["x"]) <= hx + 1.0) & (zr >= -g.half_z - 1.0) & (zr <= g.z_top + 1.0) & \
           (yl >= -12.0)
    ds = (c[:, 0] - STAY_X) * sgn                       # distance from the stay axis towards the lane
    root = near_z & (ds >= p["stay_r"] - 3.0) & (ds <= p["stay_r"] + 6.0) & (yl >= -16.0) & (yl <= 16.0)
    span = abs(p["x"] - STAY_X) - hx
    arm = near_z & (ds > p["stay_r"] + 6.0) & (ds < span) & (yl >= -16.0) & ~fair
    out = {"fairlead": fair, "root": root & ~fair, "arm": arm}
    if name == "us1":
        out["web"] = (np.abs(c[:, 0] - p["x"]) <= hx + 6.0) & (zr >= -16.0) & (zr <= 12.0) & (yl < -12.0) & \
                     (yl >= -32.0)
    return out


def sub_fea(name: str, loads: dict, extra=None, h: float = 1.0, box: dict | None = None, mesh=None,
            split_gap: bool = True, field: str | None = None) -> dict:
    """FEA of lane lug ``name`` cut from the print (see the module docstring). ``loads`` {label: [Fx, Fy, Fz]} on the
    R pin (frame, factored); ``extra(c, p, solid)`` -> bool mask of voxels to add (the BL-053 fixes); ``field`` keeps one
    load's element FI and stresses for figures and the gauge read-out."""
    from . import bag_attach as BA
    from . import h1_bedfit as BF
    from .fem import ke_h8
    from .frame_topopt import NU, ReducedSystem, element_stress, layer_failure_index
    pa = BA._paht()
    p = station(name)
    b = box or BOX[name]
    m = mesh if mesh is not None else _mesh()
    g, solid, c = voxelize(m, b["lo"], b["hi"], h)
    if extra is not None:
        add = extra(c, p, solid) & ~solid
        solid |= add
    else:
        add = np.zeros(len(c), bool)
    bolt = np.zeros(len(c), bool)
    joint = np.zeros(len(c), bool)
    if name == "us2" and split_gap:
        # dry butt joint at SPLIT_X: a one-voxel gap except the bolt shanks; the Ti bolts (in their holes, tail to head
        # face) at E_Ti / E_PAHT stiffness. The PAHT within 4 mm of a bolt axis near the face is the joint's own
        # bearing (h1_bedfit.joint_check): reported as 'joint', not in the lug regions.
        jb = BF.JOINT
        gap = np.abs(c[:, 0] - BF.SPLIT_X) <= 0.5 * h + 1e-6
        for (yb, zb) in BF.bolt_axes(p):
            rb = np.hypot(c[:, 1] - yb, c[:, 2] - zb)
            gap &= rb > jb.hole_d / 2.0
            bolt |= (rb <= 2.5) & (c[:, 0] >= jb.tail_x) & (c[:, 0] <= jb.head_face)
            joint |= (rb <= 4.0 + h) & (np.abs(c[:, 0] - BF.SPLIT_X) <= 3.0)
        solid &= ~gap
        solid |= bolt
    geom = p["geom"]
    y_pin, z_pin = p["y_pin"], p["z"]
    nc = g.node_coords()
    radial = np.c_[nc[:, 1] - y_pin, nc[:, 2] - z_pin]
    rr = np.linalg.norm(radial, axis=1)
    xl = nc[:, 0] - p["x"]
    hole_r = 0.5 * geom.hole_d
    band = (rr > hole_r - 0.35 * h) & (rr < hole_r + 1.2 * h)
    band &= np.abs(xl) >= geom.throat / 2.0 - 0.3
    band &= np.abs(xl) <= geom.throat / 2.0 + geom.cheek + 0.6 * h
    in_solid = np.zeros(g.nn, bool)
    in_solid[np.unique(g.enodes[solid])] = True
    band &= in_solid
    lo, hi = np.asarray(b["lo"], float), np.asarray(b["hi"], float)
    on_face = np.zeros(g.nn, bool)
    for d in range(3):
        on_face |= np.isclose(nc[:, d], lo[d]) | np.isclose(nc[:, d], hi[d])
    fixed_n = on_face & in_solid
    fixed = np.repeat(fixed_n, 3)
    names = list(loads)
    F = np.zeros((g.ndof, len(names)))
    for k, nm in enumerate(names):
        f3 = np.asarray(loads[nm], float)
        fyz = f3[1:]
        mag = float(np.linalg.norm(fyz))
        if mag > 1e-9:
            dvec = fyz / mag
            idx = np.where(band & (radial @ dvec > 0.15 * hole_r))[0]
            if idx.size < 6:
                idx = np.where(band)[0]
            w = np.maximum(radial[idx] @ dvec, 0.0)
            w = w / w.sum() if w.sum() > 0 else np.ones(idx.size) / idx.size
            F[3 * idx + 1, k] += mag * w * dvec[0]
            F[3 * idx + 2, k] += mag * w * dvec[1]
        if abs(f3[0]) > 1e-9:
            side = 1.0 if f3[0] > 0 else -1.0
            x_in = p["x"] + side * geom.throat / 2.0
            face = np.where((np.abs(nc[:, 0] - x_in) <= 0.6 * h) & (rr >= hole_r) & (rr <= geom.hole_d) & in_solid)[0]
            F[3 * face, k] += f3[0] / max(face.size, 1)
    F[fixed] = 0.0
    KE = ke_h8(h, 1.0, NU)
    rs = ReducedSystem(g, solid, fixed, KE)
    wts = np.where(bolt[rs.ae], E_TI / pa["E"], 1.0)
    U = rs.solve(rs.assemble(wts), F) / pa["E"]
    # statistics exclude elements within 5 mm of a fixed box face and the loaded voxels' first layer
    eidx = np.where(solid)[0]
    ce = c[eidx]
    far = np.ones(len(ce), bool)
    for d in range(3):
        far &= (ce[:, d] > lo[d] + 5.0) & (ce[:, d] < hi[d] - 5.0)
    keep = far & ~bolt[eidx] & ~joint[eidx]
    regs = {k: v[eidx] & keep for k, v in regions(name, c, p).items()}
    if add.any():
        regs["fix"] = add[eidx] & keep
    if joint.any():
        regs["joint"] = joint[eidx] & ~bolt[eidx] & far
    regs = {k: v for k, v in regs.items() if v.sum() >= 30}
    out = {}
    for k, nm in enumerate(names):
        _, S = element_stress(g, U[:, k], solid, pa["E"])
        fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
        row = {"force_n": round(float(np.linalg.norm(loads[nm])), 1), "vec_n": [round(float(v), 1) for v in loads[nm]]}
        for rn, msk in regs.items():
            fu = fi[msk]
            j = int(np.argmax(fu))
            row[rn] = {"fi99": float(np.percentile(fu, 99)), "fi_max": float(fu.max()),
                       "peak_xyz": [round(float(v), 1) for v in ce[msk][j]]}
        gov = max((r for r in regs if r != "joint"), key=lambda r: row[r]["fi99"])
        row["gov_region"] = gov
        row["fi99_gov"] = row[gov]["fi99"]
        out[nm] = row
        if field == nm:
            out["_field"] = {"cen": ce, "fi": fi, "S": S, "load": nm, "regs": regs}
    added = float((add & solid).sum() * h ** 3 * pa["rho"] / 1e6)
    return {"name": name, "h": h, "box": {k: list(v) for k, v in b.items()}, "n_elem": int(solid.sum()),
            "added_g": round(added, 2), "regions": {k: int(v.sum()) for k, v in regs.items()}, "loads": out}


def sf_row(fi: float, g_times_req: float = G_CRADLE) -> dict:
    from . import bag_attach as BA
    pa = BA._paht()
    return {"strength": round(1.0 / fi, 2), "fatigue": round(BA._fatigue_sf(fi, g_times_req, pa["fat"]), 2),
            "creep": round(BA._creep_sf(fi, g_times_req, pa["rupture"]), 2)}


# ============================================================================================ BL-053 fixes (M-3)
# US1: the web onto the lower branch (BL-049 proposal 2). The lower branch runs diagonally under the US1 fairlead
# (x 98 at z 88 to x 43 at z 104, wearer side). Over the US1 fairlead + arm footprint every y-gap of up to WEB_GAP_MAX
# between the fairlead / arm block and the branch below is filled, so the web never stands proud of either.
US1_WEB = {"dx_in": 6.0, "dx_out": 4.0, "z": (-9.0, 11.0), "y": (-36.0, 6.0), "gap_max": 20.0}
# US2: the inner cheek (|x| 147-155, the body side of the clevis joint) carries the inboard leg's pull along the pin.
# Cheek grown to +/- half_z (z span of the joint blocks, 14.5), and a buttress on its inboard face: a wedge from the
# cheek top (y_tip - top_drop) sloping down to the arm top over ``len`` mm, the cheek's grown z span, its top edge
# rounded (the strap's lip for the inboard leg, M-6).
US2_BUTTRESS = {"half_z": 14.0, "len": 16.0, "top_drop": 0.0, "end_y": "floor"}
US1_BUTTRESS = {"half_z": 12.0, "len": 16.0, "top_drop": 0.0, "end_y": "floor"}   # same build, US1's inner cheek
#                                  (|x| 52-60); half_z 12 keeps the cheek 5 mm under the spreader sheet edge (z 112)
# US1 block (sweep in h1_rev5.json 'us1_sweep'): the convex hull of the lug block and the lower branch under it, |x|
# 40-104 (to 2 mm short of the stay surface), y yc - 38 .. yc + 4 (below the stay's bag face, so nothing new under
# the spreader sheet), z pin - 9 .. pin + 15 (above the hinge cheek top z 87 at x >= 95 by 3 mm).
US1_HULL = {"x": (40.0, 104.0), "y": (-38.0, 4.0), "z": (-9.0, 15.0)}
# Root flares (fillets in z) where the arm meets the stay, outboard of the stay surface only (the spreader sheet ends
# at x 121, h1_lanes.ARM note), so the US2 notch in the sheet is untouched: z span +/- ``half_z_root`` at the stay
# surface tapering to the arm's own span ``len`` mm out.
US2_FLARE = {"half_z_root": 22.0, "len": 16.0}
US1_FLARE = None
SLOT_HALF = 6.0                    # M-5: the buttress leaves a 12 mm slot about the pin axis for the pin tail + clip


def _shape(c: np.ndarray) -> tuple:
    return tuple(len(np.unique(np.round(c[:, d], 4))) for d in range(3))


def us1_web_mask(c: np.ndarray, p: dict, solid: np.ndarray, prm: dict | None = None) -> np.ndarray:
    """US1 web: close every y-gap <= gap_max between solid below and solid above inside the fairlead + arm footprint
    (x from the inner cheek's outer face - dx_in to the stay surface, z pin + z, y yc + y)."""
    q = prm or US1_WEB
    from .fem import Grid  # noqa: F401  (shape convention: Fortran order, x fastest)
    sh = _shape(c)
    occ = solid.reshape(sh, order="F").copy()
    cc = c.reshape(sh + (3,), order="F")
    g = p["geom"]
    hx = g.throat / 2.0 + g.cheek
    x0 = p["x"] - hx - q["dx_in"]
    x1 = STAY_X - p["stay_r"] + q["dx_out"]
    zr = (p["z"] + q["z"][0], p["z"] + q["z"][1])
    yr = (p["yc"] + q["y"][0], p["yc"] + q["y"][1])
    xs, ys, zs = cc[:, 0, 0, 0], cc[0, :, 0, 1], cc[0, 0, :, 2]
    ix = np.where((xs >= x0) & (xs <= x1))[0]
    iy = np.where((ys >= yr[0]) & (ys <= yr[1]))[0]
    iz = np.where((zs >= zr[0]) & (zs <= zr[1]))[0]
    add = np.zeros(sh, bool)
    h = float(ys[1] - ys[0])
    nmax = int(round(q["gap_max"] / h))
    for i in ix:
        for k in iz:
            col = occ[i, iy, k]
            s = np.where(col)[0]
            if s.size < 2:
                continue
            d = np.diff(s)
            for a in np.where((d > 1) & (d - 1 <= nmax))[0]:
                add[i, iy[s[a] + 1:s[a + 1]], k] = True
    return add.reshape(-1, order="F")


def us2_buttress_hulls(p: dict, prm: dict | None = None) -> list:
    """Convex point sets (frame coordinates) of the inner-cheek growth and buttress of lane station p (either side):
    the inner cheek grown from +/- the fairlead's own z reach to +/- half_z (two pieces, above and below), and two
    wedges on its inboard face (z beyond +/- SLOT_HALF of the pin) from the cheek top sloping down to the arm top /
    floor over ``len`` mm. Nothing new within +/- SLOT_HALF of the pin axis: the pin's tail and its retainer clip
    (M-5) need that slot, and the printed pin hole is never touched."""
    q = prm or US2_BUTTRESS
    if q is None:
        return []
    g = p["geom"]
    s = p["sign"]
    xi = abs(p["x"]) - g.throat / 2.0 - 0.017          # inner cheek's throat face |x| (just inside: no coplanar faces)
    xo = abs(p["x"]) - g.throat / 2.0 - g.cheek + 0.013   # its inboard face
    y0 = p["yc"] - 6.0                                 # into the arm (arm top at y_floor, bottom yc - 8..-11)
    yt = p["y_tip"] - q["top_drop"] - 0.023
    ye = (p["y_floor"] if q["end_y"] == "floor" else float(q["end_y"])) - 0.033
    out = []
    for sz in (1.0, -1.0):
        za = p["z"] + sz * (min(g.half_z, g.z_top) - 0.5)
        zb = p["z"] + sz * q["half_z"]
        cheek = [(x, y, z) for x in (xo, xi) for y in (y0, yt) for z in (za, zb)]
        zs = p["z"] + sz * SLOT_HALF
        wedge = [(x, y, z) for (x, y) in ((xo + 0.5, y0), (xo + 0.5, yt), (xo - q["len"], y0), (xo - q["len"], ye))
                 for z in (zs, zb)]
        for pts in (cheek, wedge):
            P = np.asarray(pts, float)
            P[:, 0] *= s
            out.append(P)
    return out


def hull_mask(c: np.ndarray, hulls: list) -> np.ndarray:
    from scipy.spatial import Delaunay
    m = np.zeros(len(c), bool)
    for P in hulls:
        lo, hi = P.min(axis=0) - 1e-6, P.max(axis=0) + 1e-6
        sel = np.where(np.all((c >= lo) & (c <= hi), axis=1))[0]
        if sel.size:
            m[sel] |= Delaunay(P).find_simplex(c[sel]) >= 0
    return m


def flare_hulls(p: dict, prm: dict | None) -> list:
    """Convex point set of the arm-root flare of station p: at the stay surface (- 2 mm into the stay) the z span is
    +/- half_z_root about the arm's z centre, ``len`` mm out it is the arm's own span; y over the arm's own depth."""
    if prm is None:
        return []
    from . import h1_lanes as LN
    a = LN.arm_sections(p)
    r = a["root"]
    zc = 0.5 * (r["z"][0] + r["z"][1])
    hz = 0.5 * (r["z"][1] - r["z"][0])
    s = 1.0 if p["x"] > p["sign"] * STAY_X else -1.0      # towards the lane
    xs = p["sign"] * STAY_X + s * (p["stay_r"] - 2.0)
    xe = p["sign"] * STAY_X + s * (p["stay_r"] + prm["len"])
    y0, y1 = r["y"][0] + 1.0, r["y"][1] - 1.0
    pts = [(xs, y, zc + sz * prm["half_z_root"]) for y in (y0, y1) for sz in (-1.0, 1.0)]
    pts += [(xe, y, zc + sz * hz) for y in (y0, y1) for sz in (-1.0, 1.0)]
    return [np.asarray(pts, float)]


def fix_mask(name: str, hull: dict | None = None, buttress: dict | None = None, flare: dict | None = None,
             defaults: bool = True):
    """extra(c, p, solid) for sub_fea: the BL-053 fixes of lane ``name`` (``defaults``: the chosen parameters for
    every argument left None; False: only the ones given)."""
    if defaults:
        hull = hull if hull is not None else (US1_HULL if name == "us1" else None)
        buttress = buttress if buttress is not None else (US1_BUTTRESS if name == "us1" else US2_BUTTRESS)
        flare = flare if flare is not None else (US1_FLARE if name == "us1" else US2_FLARE)

    def f(c, p, solid):
        m = np.zeros(len(c), bool)
        if hull:
            m |= region_hull_mask(c, p, solid, hull)
        if buttress:
            hm = hull_mask(c, us2_buttress_hulls(p, buttress))
            g = p["geom"]
            thr = np.abs(c[:, 0] - p["x"]) < g.throat / 2.0           # keep the throat and the pin hole open
            hole = (np.hypot(c[:, 1] - p["y_pin"], c[:, 2] - p["z"]) < g.hole_d / 2.0) & \
                (np.abs(c[:, 0] - p["x"]) <= g.throat / 2.0 + g.cheek + 0.5)
            m |= hm & ~thr & ~hole
        if flare:
            m |= hull_mask(c, flare_hulls(p, flare))
        return m
    return f


def region_hull_mask(c: np.ndarray, p: dict, solid: np.ndarray, prm: dict) -> np.ndarray:
    """Fill the convex hull of the solid inside a box about station p (x0..x1 frame |x|, y yc + y, z pin + z): the
    US1 lug block and the lower branch under it become one convex block (no re-entrant corner between them)."""
    from scipy.spatial import ConvexHull, Delaunay
    s = p["sign"]
    ax = np.abs(c[:, 0]) * (np.sign(c[:, 0]) == s)
    box = (ax >= prm["x"][0]) & (ax <= prm["x"][1]) & \
          (c[:, 1] >= p["yc"] + prm["y"][0]) & (c[:, 1] <= p["yc"] + prm["y"][1]) & \
          (c[:, 2] >= p["z"] + prm["z"][0]) & (c[:, 2] <= p["z"] + prm["z"][1])
    pts = c[box & solid]
    if len(pts) < 10:
        return np.zeros(len(c), bool)
    H = pts[ConvexHull(pts).vertices]
    m = np.zeros(len(c), bool)
    sel = np.where(box)[0]
    m[sel] = Delaunay(H).find_simplex(c[sel]) >= 0
    return m


# ============================================================================================ print (manifold)
FIXES = True                       # frame_h1.print_mesh adds the BL-053 lug fixes (False = the BL-051 print)
FLOOR_LIP_R = 3.0                  # M-6: the US1 throat floor's lower end (the bag-on strap wraps it), r 3


def _hull(points):
    import manifold3d as m3d
    P = np.asarray(points, float)
    return m3d.Manifold.batch_hull([m3d.Manifold.cube((1e-3, 1e-3, 1e-3)).translate(tuple(q)) for q in P])


def _box_m(lo, hi):
    import manifold3d as m3d
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3d.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def _cyl_x(xa, xb, y, z, d, seg=64):
    import manifold3d as m3d
    lo, hi = min(xa, xb), max(xa, xb)
    return m3d.Manifold.cylinder(hi - lo, d / 2.0, d / 2.0, seg).rotate((0.0, 90.0, 0.0)).translate((lo, y, z))


def add_fixes(man, log=print, stats: dict | None = None):
    """Union the BL-053 lug fixes onto the print body (after h1_fairleads.add_fairleads): US1 block (hull of the lug
    block and the branch under it, US1_HULL), inner-cheek growth + buttress (US1_BUTTRESS / US2_BUTTRESS), US2 root
    flare (US2_FLARE); then the pin holes through the grown cheeks re-cut at the printed size and the US1 throat
    floor's lower end rounded (FLOOR_LIP_R). Both sides. The new pieces never reach the pin hole or the throat.""" 
    from . import h1_fairleads as HF
    v0 = man.volume()
    per = {}
    for p in HF.placed():
        if not p.get("lane"):
            continue
        name = p["name"]
        va = man.volume()
        if name == "us1" and US1_HULL:
            q = US1_HULL
            xa, xb = sorted((p["sign"] * q["x"][0], p["sign"] * q["x"][1]))
            box = _box_m((xa, p["yc"] + q["y"][0], p["z"] + q["z"][0]), (xb, p["yc"] + q["y"][1], p["z"] + q["z"][1]))
            part = man ^ box
            if part.volume() > 1.0:
                hl = part.hull()
                cen = np.mean(np.asarray(hl.bounding_box(), float).reshape(2, 3), axis=0)
                # 0.1 % smaller about its centre: the hull's faces lie on the body's own convex faces, and coplanar
                # booleans leave slivers that an STL round trip turns into non-manifold edges
                hl = hl.translate(tuple(-cen)).scale((0.999, 0.999, 0.999)).translate(tuple(cen))
                man = man + (hl ^ box)
        bq = US1_BUTTRESS if name == "us1" else US2_BUTTRESS
        for P in us2_buttress_hulls(p, bq):
            man = man + _hull(P)
        fl = US1_FLARE if name == "us1" else US2_FLARE
        for P in flare_hulls(p, fl):
            man = man + _hull(P)
        g = p["geom"]
        if name == "us1" and FLOOR_LIP_R > 0.0:
            r = FLOOR_LIP_R
            z0 = p["z"] - g.half_z
            xa, xb = p["x"] - g.throat / 2.0 - 0.5, p["x"] + g.throat / 2.0 + 0.5
            # the throat floor's top as printed (the fairlead solid's floor sits about 1 mm over placed() y_floor)
            probe = man ^ _box_m((p["x"] - g.throat / 2.0 + 1.0, p["y_floor"] - 4.0, z0 + 1.0),
                                 (p["x"] + g.throat / 2.0 - 1.0, p["y_floor"] + 4.0, z0 + 2.0))
            y1 = float(probe.bounding_box()[4]) if probe.volume() > 0.1 else p["y_floor"]
            sq = _box_m((xa, y1 - r, z0 - 0.5), (xb, y1 + 0.5, z0 + r))
            man = man - (sq - _cyl_x(xa - 0.5, xb + 0.5, y1 - r, z0 + r, 2 * r))
        per[f"{name}_{p['side']}"] = round((man.volume() - va) * 1.06e-3, 2)
    if stats is not None:
        stats.update({"added_g": round((man.volume() - v0) * 1.06e-3, 2), "per_station_g": per})
    if log:
        log(f"  BL-053 lug fixes: +{(man.volume() - v0) * 1.06e-3:.1f} g {per}")
    return man


# ============================================================================================ B-1 print plan
PAHT_RHO = 1.06e-3                 # g / mm3 (pa12_cf_fdm_paht print density, h1_lanes.RHO_G_MM3)
VOL_RATE = 8.0                     # mm3/s: the print README's volume / 8 mm3/s print-time rule (h1_buckling print_h)
TIME_OVERHEAD = 1.08               # h1_buckling.export_print print_h factor (travel, layer changes)
TREE_FILL = 0.12                   # ASSUMPTION TREE-FILL: tree support material per mm3 of the column it spans
#                                    (branches + trunks, PAHT-CF, 45 deg threshold); settled by the slicer preview
INTERFACE_MM = 0.6                 # 3 interface layers x 0.2 mm, dense, under every supported down face
OVERHANG_DEG = 45.0                # support threshold
SPLIT_Z = 234.0                    # frame_h1.JOINT.z: lower / upper half split


def _label(P: np.ndarray) -> np.ndarray:
    """Frame-region label of points: 'lug' (a fairlead with its root, or a lane lug arm / BL-053 block: within the
    station's cheek box +/- 4 mm, or between the stay and a lane fairlead within 22 mm of the pin in z), 'stay' (the
    rest within 13 mm of a stay axis |x| 115, any z), 'clevis' (|x| > SPLIT_X at US2), 'other' (hub, branches,
    crown corners, pawl housing). 'stay' and 'lug' are the fatigue-critical faces of the ticket."""
    from . import h1_bedfit as BF
    from . import h1_fairleads as HF
    lab = np.full(len(P), "other", dtype=object)
    ax = np.abs(P[:, 0])
    lab[np.abs(ax - STAY_X) <= 13.0] = "stay"
    for p in HF.placed():
        if p["side"] != "R":
            continue
        g = p["geom"]
        hx = g.throat / 2.0 + g.cheek + 4.0
        zr = P[:, 2] - p["z"]
        box = (np.abs(ax - abs(p["x"])) <= hx) & (zr >= -g.half_z - 4.0) & (zr <= max(g.z_top, 14.0) + 4.0)
        if p.get("lane"):
            lo, hi = sorted((abs(p["x"]), STAY_X))
            box |= (ax >= lo - 6.0) & (ax <= hi) & (np.abs(zr) <= 22.0)
        lab[box] = "lug"
    lab[(ax > BF.SPLIT_X) & (np.abs(P[:, 2] - 142.0) <= 20.0)] = "clevis"
    return lab


def occupancy(mesh, lo, hi, h: float = 1.0) -> tuple:
    """Light voxel occupancy (no FE grid): bool (nx, ny, nz) of cell centres inside ``mesh`` (z sections, even-odd)
    and the centre coordinates (nx, ny, nz, 3) as float32."""
    from matplotlib.path import Path as MPath
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    n = np.maximum(np.round((hi - lo) / h).astype(int), 1)
    ax = [lo[k] + h * (np.arange(n[k]) + 0.5) for k in range(3)]
    X, Y = np.meshgrid(ax[0], ax[1], indexing="ij")
    pts = np.c_[X.ravel(), Y.ravel()]
    S = np.zeros(tuple(n), bool)
    for k, z in enumerate(ax[2]):
        sec = mesh.section(plane_origin=[0.0, 0.0, float(z) + 1e-4], plane_normal=[0.0, 0.0, 1.0])
        if sec is None:
            continue
        inside = np.zeros(len(pts), np.int16)
        for d in sec.discrete:
            inside += MPath(np.asarray(d)[:, :2]).contains_points(pts)
        S[:, :, k] = ((inside % 2) == 1).reshape(n[0], n[1])
    C = np.stack(np.meshgrid(*[a.astype(np.float32) for a in ax], indexing="ij"), axis=-1)
    return S, C


def support_map(mesh, up: float = 1.0, h: float = 1.0, pad: float = 2.0, keep=None, zlim=None) -> dict:
    """Voxel print analysis of a part laid with its layers normal to frame y (the FEA's layer direction), built along
    +y (``up`` 1: wearer face on the plate, the BL-051 print) or -y (``up`` -1: bag face on the plate). A voxel needs
    support when no solid voxel of the layer below lies within one voxel sideways (45 deg at h = 1 mm) and it is not
    on the plate. Returns plate contact, supported down area per region, the support column volume (to the plate or
    the part below), and the contact points (frame)."""
    lo, hi = mesh.bounds[0] - pad, mesh.bounds[1] + pad
    if zlim is not None:                # one half of the frame: frame z range (the split face prints vertical)
        lo, hi = lo.copy(), hi.copy()
        lo[2], hi[2] = max(lo[2], zlim[0]), min(hi[2], zlim[1])
    S, C = occupancy(mesh, lo, hi, h)
    if keep is not None:
        S &= keep(C)
    sh = S.shape
    if up < 0:
        S = S[:, ::-1, :]
        C = C[:, ::-1, :]
    from scipy import ndimage
    below = np.zeros_like(S)
    below[:, 1:, :] = S[:, :-1, :]
    near_below = ndimage.binary_dilation(below, structure=np.ones((3, 1, 3), bool))
    any_below = np.cumsum(S, axis=1) - S > 0          # solid somewhere below in the column
    first = np.argmax(S.any(axis=(0, 2)))             # first layer with material = the plate
    layer = np.arange(sh[1])[None, :, None]
    on_plate = S & (layer == first)
    unsup = S & ~near_below & ~on_plate
    down = S & ~below & ~on_plate                     # every down-facing cell off the plate (support or bridge)
    # column from each unsupported cell down to the solid below it (or to the plate)
    idx = np.argwhere(unsup)
    col = np.zeros(len(idx))
    for n, (i, j, k) in enumerate(idx):
        sol = np.where(S[i, :j, k])[0]
        col[n] = (j - (sol[-1] + 1)) if sol.size else (j - first)
    P = C[unsup]
    lab = _label(P)
    area = h * h
    res = {"build": "+y (wearer face down)" if up > 0 else "-y (bag face down)",
           "plate_contact_mm2": round(float(on_plate.sum()) * area, 0),
           "footprint_mm2": round(float(S.any(axis=1).sum()) * area, 0),
           "down_cells_mm2": round(float(down.sum()) * area, 0),
           "supported_mm2": round(float(unsup.sum()) * area, 0),
           "supported_by_region_mm2": {k: round(float((lab == k).sum()) * area, 0) for k in
                                       ("stay", "lug", "clevis", "other")},
           "support_column_mm3": round(float(col.sum()) * h ** 3, 0),
           "part_mm3": round(float(S.sum()) * h ** 3, 0),
           "max_column_mm": round(float(col.max()) if col.size else 0.0, 1)}
    res["support_g"] = round((res["support_column_mm3"] * TREE_FILL + res["supported_mm2"] * INTERFACE_MM) * PAHT_RHO, 1)
    res["_pts"] = P
    res["_lab"] = lab
    res["_col"] = col
    return res


# ============================================================================================ M-1 / M-3 lug check
BOXES = {"us1": {"lo": (-6.0, -56.0, 46.0), "hi": (140.0, 32.0, 146.0)},     # to the lumbar hub (box sensitivity:
         "us2": {"lo": (80.0, -50.0, 90.0), "hi": (192.0, 40.0, 196.0)}}     # the smaller BOX reads US1 less severe)
DESIGN_DY_MAX = 50.0               # ASSUMPTION QUARTER-CONTACT: design rows dy 0 / 50; dy 95 is reported as sensitivity


def lug_loads_3d(name: str) -> dict:
    """{label: {'vec', 'g_times_req', 'family'}} on the R pin: every us_route.cradle_3d row (2.4), the bag-on rows of
    h1_lanes.lug_loads (3.0, with their +/-10 deg fleet), and the BL-051 lane rows (legs in the y-z plane, kept for
    comparison)."""
    from . import h1_lanes as LN
    cd = _U().cradle_3d()
    out = {}
    for k, v in cd["rows"].items():
        if v["strap"] == name:
            fam = "cradle3d" if v["dy_mm"] <= DESIGN_DY_MAX else "cradle3d_dy95"
            out["c3d|" + k.split("|", 1)[1]] = {"vec": v["vec_n"], "g_times_req": G_CRADLE, "family": fam}
    for k, v in LN.lug_loads(name).items():
        if k.startswith("bagon"):
            out[k] = {**v, "family": "bagon"}
        elif k in ("cradle_lane", "cradle_lane_b50"):
            out[k] = {**v, "family": "bl051_yz"}
    return out


def lug_check(name: str, mesh=None, extra=None, tag: str = "print", field: str | None = None) -> dict:
    """sub_fea of lane ``name`` on the print (``extra`` None: the BL-053 print as exported) under lug_loads_3d; SFs per
    row (strength, fatigue at 1.6 g on the row's own g_times_req, creep) and per family the worst."""
    L = lug_loads_3d(name)
    f = sub_fea(name, {k: v["vec"] for k, v in L.items()}, extra=extra, box=BOXES[name], mesh=mesh, field=field)
    rows = {}
    for k, v in f["loads"].items():
        if k.startswith("_"):
            continue
        gr = L[k]["g_times_req"]
        rows[k] = {"family": L[k]["family"], "force_n": v["force_n"], "vec_n": v["vec_n"], "g_times_req": gr,
                   **sf_row(v["fi99_gov"], gr), "region": v["gov_region"], "peak_xyz": v[v["gov_region"]]["peak_xyz"],
                   "regions_fi99": {r: round(v[r]["fi99"], 3) for r in f["regions"]}}
    fams = {}
    for k, r in rows.items():
        fam = r["family"]
        b = k.split("|")[1] if k.startswith("c3d|") else "-"
        key = f"{fam}|{b}"
        if key not in fams or r["fatigue"] < fams[key]["fatigue"]:
            fams[key] = {"load": k, "force_n": r["force_n"], "strength": r["strength"], "fatigue": r["fatigue"],
                         "region": r["region"], "peak_xyz": r["peak_xyz"]}
        smin = min(q["strength"] for kk, q in rows.items() if q["family"] == fam and
                   (kk.split("|")[1] if kk.startswith("c3d|") else "-") == b)
        fams[key]["strength_min"] = smin
    design = [r for r in rows.values() if r["family"] in ("cradle3d", "bagon")]
    out = {"tag": tag, "n_elem": f["n_elem"], "added_g": f["added_g"], "box": f["box"], "rows": rows,
           "families": dict(sorted(fams.items())),
           "design_min": {"strength": min(r["strength"] for r in design), "fatigue": min(r["fatigue"] for r in design)}}
    if field and "_field" in f["loads"]:
        out["_field"] = f["loads"]["_field"]
    return out


# ============================================================================================ M-2 / M-6 joint
STRAP_W = 25.0


def wrap_rows(wrap: dict) -> dict:
    """The US2 strap's wrap over the joint blocks' lip (us_route.strap_wrap, bag-on, factored 3.0) as forces on the
    CLEVIS: the share of the 25 mm strap (centred on the pin x) that lies outboard of the joint face, applied at the
    lip contact, at the centre of that share."""
    from . import h1_bedfit as BF
    p = station("us2")
    x0, x1 = p["x"] - STRAP_W / 2.0, p["x"] + STRAP_W / 2.0
    share = (x1 - BF.SPLIT_X) / (x1 - x0)
    xc = 0.5 * (BF.SPLIT_X + x1)
    out = {}
    for r in wrap["rows"]:
        if r["strap"] != "us2" or r["bearing_n"] <= 0.0:
            continue
        yz = np.asarray(r["bearing_yz_n"], float) * share
        c = np.mean(np.asarray(r["contact_yz"], float), axis=0)
        out[f"wrap|{r['torso']}"] = {"vec": [0.0, float(yz[0]), float(yz[1])], "g_times_req": 3.0, "direct": True,
                                     "at": [xc, float(c[0]), float(c[1])], "clevis_share": round(share, 3)}
    return out


def joint(wrap: dict) -> dict:
    """h1_bedfit.joint_check on the BL-053 joint (bolts at dz 7, hex traps) under every US2 row of lug_loads_3d plus
    the strap-wrap rows: outer-cheek share 0.6 (ASSUMPTION CLEVIS-SHARE) and 1.0 (sensitivity)."""
    from . import h1_bedfit as BF
    L = {k: {kk: v[kk] for kk in ("vec", "g_times_req")} for k, v in lug_loads_3d("us2").items()}
    W = wrap_rows(wrap)
    out = {"trap_walls": BF.trap_walls(), "wrap_rows": W}
    for sh in (BF.CHEEK_SHARE, 1.0):
        jc = BF.joint_check(share=sh, loads={**L, **W})
        fam = {}
        for k, r in jc["rows"].items():
            f = "wrap" if k.startswith("wrap") else ("c3d" if k.startswith("c3d") else k.split("|")[0])
            if f not in fam or r["min_fatigue"] < fam[f]["min_fatigue"]:
                fam[f] = {"load": k, "min_sf": r["min_sf"], "min_fatigue": r["min_fatigue"],
                          "force_on_clevis_n": r["force_on_clevis_n"],
                          "check_s": min(r["sf"], key=r["sf"].get), "check_f": min(r["fatigue"], key=r["fatigue"].get)}
        sm = min(r["min_sf"] for r in jc["rows"].values())
        out[f"share_{sh:g}"] = {"worst_strength": jc["worst_strength"], "worst_fatigue": jc["worst_fatigue"],
                               "families": fam, "min_sf_all_rows": sm, "net_section": jc["net_section"],
                               "capacities_n": jc["capacities_n"]}
    return out


# ============================================================================================ M-4 gauge pass values
GAUGE_OFF = 3.0                    # gauge centre 3 mm off the stay surface along the arm, bag face (kit text, BL-052)
GAUGE_TOL = 1.5                    # +/- placement tolerance (mm) used for the band
MT1_STEPS = (240.0, 480.0, 720.0)  # MT-1 cradle pull steps per pin (kit), plus the governing factored row
T1_STEPS_LB = (0.0, 150.0, 300.0)  # T1 carry steps (kit)
DESIGN_LB = 150.0                  # load_standard design load 150 lb (68 kg): the bag-on rows' basis


def gauge_site(name: str, mesh=None) -> dict:
    """Gauge point on the R arm root's bag face: x = stay axis -/+ (stay_r + GAUGE_OFF) towards the lane, z = the arm's
    z centre at the root, y = the print's bag-face surface there (max y of the section)."""
    from . import h1_lanes as LN
    m = mesh if mesh is not None else _mesh()
    p = station(name)
    a = LN.arm_sections(p)["root"]
    zc = 0.5 * (a["z"][0] + a["z"][1])
    s = 1.0 if p["x"] > STAY_X else -1.0
    xg = STAY_X + s * (p["stay_r"] + GAUGE_OFF)
    sec = m.section(plane_origin=[0.0, 0.0, zc], plane_normal=[0.0, 0.0, 1.0])
    ys = []
    for d in sec.discrete:
        P = np.asarray(d)
        Q = np.vstack([np.linspace(P[i], P[i + 1], 30) for i in range(len(P) - 1)])
        k = np.abs(Q[:, 0] - xg) < 0.3
        if k.any():
            ys.append(Q[k, 1].max())
    return {"x": round(xg, 2), "y": round(float(max(ys)), 2), "z": round(zc, 2), "axis": "x (along the arm)",
            "face": "bag face (+y)", "station": name}


def gauge_values(log=print) -> dict:
    """Model stress along the gauge axis (sigma_xx, MPa; strain = sigma / E_xy) at each gauge site per load step, with
    a band = min / max over the voxels within GAUGE_TOL of the site (placement tolerance) in the surface layer.
    MT-1cr and CLEVIS-SHARE on the governing 3D cradle vectors; T1 on the bag-on drape row scaled to the carry steps
    (local pin load only: ASSUMPTION GAUGE-LOCAL)."""
    from . import bag_attach as BA
    E = BA._paht()["E"]
    m = _mesh()
    L = {n: lug_loads_3d(n) for n in ("us1", "us2")}
    chk = json.loads((OUT / "lugs.json").read_text()) if (OUT / "lugs.json").exists() else None
    out = {"E_xy_mpa": E, "sites": {}, "tests": {}}
    unit = {}
    for n in ("us1", "us2"):
        site = gauge_site(n, m)
        out["sites"][n] = site
        if chk:
            fam = chk[n]["print"]["families"]["cradle3d|b40"]
            gov = fam["load"]
        else:
            gov = "c3d|b40|dy50|out" if n == "us1" else "c3d|b40|dy50|in"
        cases = {"cradle_gov": gov, "bagon": "bagon_drape"}
        if n == "us2":
            cases["clevis_share"] = "c3d|b40|dy95|out"          # pure y-z leg (wide load): the outer cheek's case
        for lab, k in cases.items():
            v = np.asarray(L[n][k]["vec"], float)
            u = v / np.linalg.norm(v)
            f = sub_fea(n, {"unit": (1000.0 * u).tolist()}, box=BOXES[n], mesh=m, field="unit")
            fd = f["loads"]["_field"]
            cen, S = fd["cen"], fd["S"]
            d = np.linalg.norm(cen - np.array([site["x"], site["y"] - 0.5, site["z"]]), axis=1)
            near = d <= GAUGE_TOL + 0.5
            if not near.any():
                near = d <= d.min() + 0.5
            j = int(np.argmin(d))
            sx = S[:, 0] / 1000.0                            # MPa per N
            unit[(n, lab)] = {"load": k, "unit": u.round(4).tolist(), "mpa_per_n": float(sx[j]),
                              "band_mpa_per_n": [float(sx[near].min()), float(sx[near].max())]}
            if log:
                log(f"  gauge {n} {lab}: {unit[(n, lab)]}")

    def steps(n, lab, Fs, basis):
        q = unit[(n, lab)]
        rows = []
        for F in Fs:
            s = q["mpa_per_n"] * F
            lo, hi = (q["band_mpa_per_n"][0] * F, q["band_mpa_per_n"][1] * F)
            lim = max(abs(s), abs(lo), abs(hi))
            rows.append({"pin_load_n": round(F, 1), "sigma_mpa": round(s, 2), "band_mpa": [round(lo, 2), round(hi, 2)],
                         "microstrain": round(s / E * 1e6, 0),
                         "pass_if_abs_microstrain_at_most": round(lim * 1.15 / E * 1e6, 0)})
        return {"pull_unit_vector_frame_R": q["unit"], "row": q["load"], "basis": basis, "steps": rows}
    for n in ("us1", "us2"):
        Fg = float(np.linalg.norm(L[n][unit[(n, "cradle_gov")]["load"]]["vec"]))
        out["tests"][f"MT-1cr|{n}"] = steps(n, "cradle_gov", list(MT1_STEPS) + [Fg],
                                            "pin load along the governing 3D cradle leg (40 mm belly, 53 kg float limit,"
                                            " factored 1.6 g x 1.5); last step = the factored row")
        Tb = float(np.linalg.norm(L[n]["bagon_drape"]["vec"]))     # factored 3.0 at the 150 lb design load
        Fs = [Tb / 3.0 * lb / DESIGN_LB for lb in T1_STEPS_LB]
        out["tests"][f"T1|{n}"] = steps(n, "bagon", Fs, "T1 carry: bag-on cam-tight strap (drape path) at 1 g, "
                                        "scaled to the carry load (0 / 150 / 300 lb); local pin load only")
    Fg = float(np.linalg.norm(L["us2"][unit[("us2", "cradle_gov")]["load"]]["vec"]))
    cs = out["tests"]["CLEVIS-SHARE|us2_inboard"] = steps("us2", "cradle_gov", [Fg, Fg * 1.6 / G_CRADLE],
                                                       "CLEVIS-SHARE A: governing inboard leg; static proof = factored "
                                                       "row, cycle peak = x 1.6 / 2.4 (1e5 cycles, R 0.1)")
    cs["eye_bears_on"] = "inner (body) cheek: PTFE shim between the eye and the inner cheek's throat face"
    Fo = float(np.linalg.norm(L["us2"]["c3d|b40|dy95|out"]["vec"]))
    cb = out["tests"]["CLEVIS-SHARE|us2_yz"] = steps("us2", "clevis_share", [Fo, Fo * 1.6 / G_CRADLE],
                                                    "CLEVIS-SHARE B: the leg with no lateral part (a load as wide as "
                                                    "the span), contact 95 mm aft: all of it in y-z, the clevis's "
                                                    "share-1.0 case; static proof = factored row, cycle peak x 1.6 / 2.4")
    cb["eye_bears_on"] = "outer (clevis) cheek, PTFE shim between the eye and the outer cheek (share 1.0 case)"
    return out


# ============================================================================================ M-5 pin retention
CLIP_HOLE_D = 1.3                  # cross hole for a 1.2 mm wire hitch-pin (R-) clip
CLIP_EDGE = 2.5                    # cross-hole centre beyond the cheek's outer face (clip wire clears the face)
TAIL_BEYOND_HOLE = 2.0
HEAD_D, HEAD_T = 8.0, 1.5          # turned head (as bag_attach's 7075 pin head)
TETHER_HOLE_D = 1.6                # in the head end, for the 1.5 mm Dyneema pull / tether loop
RETAINER = {
    "part": "hitch-pin (R-) clip, 302 / 18-8 stainless, 1.2 mm wire, for 4.8-6.4 mm (3/16-1/4 in) pins",
    "source": "https://www.mcmaster.com/products/hitch-pin-clips/ (secondary: catalogue page not fetched; any "
              "18-8 R-clip in that size range)",
    "mass_g": 0.6,                 # ASSUMPTION CLIP-MASS: 1.2 mm wire, about 55 mm of wire at 7.9 g/cm3 = 0.5 g
    "tether": "1.5 mm Dyneema (UHMWPE) cord, 120 mm, through the pin head's 1.6 mm hole and the clip's eye, "
              "larks-head round the stay beside the fairlead: pin and clip stay on the frame when pulled",
    "tether_g": 0.2,               # ASSUMPTION: 1.5 mm Dyneema about 1.5 g/m x 0.12 m
}


def pins() -> dict:
    """M-5: one retention scheme for all 12 fairlead pins: a headed pin (head outboard) through both cheeks, a 1.3 mm
    cross hole CLIP_EDGE beyond the far cheek's outer face, a stainless R-clip in it, pin and clip on one Dyneema
    tether. Pin length per station = cheek-to-cheek span + head + tail. The pin's bending span is unchanged (head and
    clip sit outside the cheeks). Pin bending checks at the new cradle rows (y-z part only: the x part bears on the
    cheek through the eye, not on the pin)."""
    from . import bag_attach as BA
    from . import h1_fairleads as HF
    from . import h1_lanes as LN
    out = {"scheme": "headed pin, R-clip through a cross hole on the far side, pin + clip on one tether",
           "retainer": RETAINER, "stations": {}}
    for p in HF.placed():
        if p["side"] != "R":
            continue
        g = p["geom"]
        span = g.throat + 2 * g.cheek
        tail = CLIP_EDGE + CLIP_HOLE_D / 2.0 + TAIL_BEYOND_HOLE
        L = span + tail
        mat = LN.HINGE_PIN_MATERIAL if p["name"] == "hinge" else "alu_7075_t6"
        from huntkit.materials import load
        rho = float(load(mat).require("density_kg_m3"))
        m = (math.pi / 4 * g.pin_d ** 2 * L + math.pi / 4 * HEAD_D ** 2 * HEAD_T) * rho * 1e-6
        far = "inboard (towards x 0; the buttress leaves a 12 mm slot)" if p.get("lane") else "inboard"
        row = {"material": mat, "pin_d_mm": g.pin_d, "span_mm": span, "shank_mm": round(L, 1),
               "head_mm": [HEAD_D, HEAD_T], "cross_hole": {"d_mm": CLIP_HOLE_D, "from_far_cheek_face_mm": CLIP_EDGE},
               "head_side": "outboard", "clip_side": far, "pin_g": round(m, 2),
               "set_g": round(m + RETAINER["mass_g"] + RETAINER["tether_g"], 2), "qty": 2,
               "removed_at_bag_off": p["name"] == "hinge"}
        if p["name"] in ("us1", "us2"):
            Ls = lug_loads_3d(p["name"])
            yz = {k: float(np.hypot(v["vec"][1], v["vec"][2])) for k, v in Ls.items() if v["family"] == "cradle3d"}
            yz95 = {k: float(np.hypot(v["vec"][1], v["vec"][2])) for k, v in Ls.items()
                    if v["family"] == "cradle3d_dy95"}
            F = max(yz.values())
            pc = LN.pin_check(F, g.throat, g.cheek, g.pin_d, mat, G_CRADLE)
            pc95 = LN.pin_check(max(yz95.values()), g.throat, g.cheek, g.pin_d, mat, G_CRADLE)
            row["bending"] = {"design_yz_n": round(F, 1), "sf_yield": round(pc["sf_yield"], 2),
                              "sf_fatigue": round(pc["sf_fatigue"], 2), "dy95_yz_n": round(max(yz95.values()), 1),
                              "dy95_sf_yield": round(pc95["sf_yield"], 2), "dy95_sf_fatigue": round(pc95["sf_fatigue"], 2)}
        if p["name"] == "hinge":
            hp = LN.pin_check(LN.HINGE_ROW_N, g.throat, g.cheek, g.pin_d, mat, LN.PIN_G_TIMES_REQ)
            row["bending"] = {"row_n": LN.HINGE_ROW_N, "sf_yield": round(hp["sf_yield"], 2),
                              "sf_fatigue": round(hp["sf_fatigue"], 2)}
        out["stations"][p["name"]] = row
    # the clip: double shear of the 1.2 mm wire against a walking pin (axial pull limited by the eye's friction; the
    # eye's axial load bears on the cheek, not the pin)
    from huntkit.materials import load as _l
    try:
        su = float(_l("ss_304").require("ultimate_strength_mpa"))
        src = "data/materials ss_304"
    except Exception:
        su = 515.0                 # ASSUMPTION CLIP-UTS: annealed 18-8 minimum (ASTM A240 304, 515 MPa)
        src = "ASSUMPTION CLIP-UTS (ASTM A240 304 minimum 515 MPa)"
    out["clip_double_shear_n"] = round(2 * math.pi / 4 * 1.2 ** 2 * 0.6 * su, 0)
    out["clip_uts_source"] = src
    out["mass"] = {"pins_g": round(sum(2 * r["pin_g"] for r in out["stations"].values()), 2),
                   "clips_tethers_g": round(12 * (RETAINER["mass_g"] + RETAINER["tether_g"]), 2)}
    out["booked_before"] = "bag_attach: 7075 pins 36 mm shank + 8 mm head (no retainer); Ti hinge 5 x 44"
    out["test"] = {"id": "PIN-RET", "steps": [
        "(a) every pin in, clip seated: a 50 N push on the pin's tail along its axis (spring scale) moves it < 0.5 mm",
        "(b) after the T9 walk and the MT-1cr / CLEVIS-SHARE cycles: every pin home, every clip fully seated, "
        "no wire wear groove deeper than 0.1 mm",
        "(c) bag-off: each hinge pin out and back in by hand, gloved, clip off and on, <= 8 s each"]}
    return out


# ============================================================================================ print settings (B-1)
def print_settings(pp: dict) -> dict:
    """The data BL-054 turns into the print README: orientation, supports, blockers, filament and time per file."""
    def row(key, part_g=None):
        r = pp[key]
        g_part = part_g if part_g is not None else r["part_mm3"] * PAHT_RHO
        sup = r["support_g"]
        sup_hi = round((r["support_column_mm3"] * 0.25 + r["supported_mm2"] * INTERFACE_MM) * PAHT_RHO, 1)
        t = (r["part_mm3"] + r["support_column_mm3"] * TREE_FILL + r["supported_mm2"] * INTERFACE_MM) / VOL_RATE \
            / 3600.0 * TIME_OVERHEAD
        return {"plate_contact_mm2": r["plate_contact_mm2"], "supported_down_area_mm2": r["supported_mm2"],
                "supported_by_region_mm2": r["supported_by_region_mm2"], "part_g": round(g_part, 1),
                "support_g_est": sup, "support_g_high": sup_hi,
                "filament_g_est": round(g_part + sup, 0), "filament_g_high": round(g_part + sup_hi, 0),
                "print_h_est": round(t, 1), "max_support_column_mm": r["max_column_mm"]}
    files = {
        "h1_lower_flat.stl": row("lower|+1"), "h1_upper_flat.stl": row("upper|+1"),
        "us2_clevis_R.stl / us2_clevis_L.stl": {**row("us2_clevis_R(print coords, z up)|+1"),
                                                "supports": "none (prints flat: 97 % of the footprint on the plate)"},
        "test_pieces/us_route_stay_R.stl": row("us_route_stay_R|+1"),
        "test_pieces/hefit_hinge_fairlead_R.stl": row("hefit_hinge_fairlead_R|+1"),
        "test_pieces/im3ec_cheek_R.stl": row("im3ec_cheek_R|+1")}
    return {
        "ticket": "BL-053 (fifth review B-1)", "source": "huntkit/gendesign/h1_rev5.py print_settings / support_map",
        "orientation": {
            "all_files": "as exported: the STL's z is the build direction (frame y up: wearer face down, bag face up). "
                         "Do not rotate or flip on the plate: the FEA assumes the layers normal to frame y",
            "why_not_flipped": "bag face down needs as much support (lower 13 859 vs 11 164 mm2, upper 19 915 vs 18 044 "
                               "mm2 supported area) and puts the support scars on the stays' bag faces and the fairlead "
                               "tips (eye bearing, HE fit) instead of the wearer faces",
            "test_pieces": "print every test piece exactly like the frame (same orientation, same supports) so it "
                           "carries the frame's surfaces and scars"},
        "supports": {
            "type": "tree supports from the build plate only ('on build plate only'), auto, threshold 45 deg",
            "material": "PAHT-CF itself (single nozzle H2S), no breakaway material",
            "top_z_distance_mm": [0.2, 0.25], "interface_layers": 3, "interface_spacing_mm": 0.2,
            "xy_distance_mm": 0.6, "brim_mm": 8.0,
            "blockers": ["every pin hole and fairlead throat (12 stations)", "both z 234 joint bores, counterbores "
                         "and nut traps", "the two US2 clevis bolt holes, counterbores and hex nut traps (body side)",
                         "the 18 mm stay sleeve bores", "the pawl bore and the spine channel"],
            "note": "a slicer that auto-supports everything puts supports inside the bores: paint blockers first"},
        "files": files,
        "scars": {
            "where": "support contact lands on wearer-facing (-y) surfaces only: the stays' wearer faces "
                     f"({pp['lower|+1']['supported_by_region_mm2']['stay']:.0f} + "
                     f"{pp['upper|+1']['supported_by_region_mm2']['stay']:.0f} mm2) and the undersides of the lugs, "
                     "fairlead roots and lane blocks; the lugs' governing spots (US1 outer cheek / floor corner, US2 "
                     "arm root bag face, hinge inboard cheek corner) face up or sideways and carry no scar",
            "fatigue_critical": True,
            "finish": "sand the support witness on the stays' wearer faces and the lug undersides flat with 240 then "
                      "400 grit, removing at most 0.2 mm (SAND-ALLOW); deburr every bore edge",
            "allowance": SAND_ALLOW},
        "time_rule": f"(part + support volume) / {VOL_RATE:g} mm3/s x {TIME_OVERHEAD} (h1_buckling print_h rule)",
        "assumptions": ["TREE-FILL", "SAND-ALLOW", "SCAR-KD"]}


SAND_ALLOW = {"max_removed_mm": 0.2, "stay_depth_mm": 18.0,
              "section_modulus_loss": round(1 - (1 - 0.2 / 18.0) ** 2, 3),
              "note": "0.2 mm off one face of an 18 mm deep stay (ASSUMPTION: rectangular-equivalent) costs about "
                      "2.2 % of its bending section modulus; the body's fatigue minimum on the sim bases (1.258, "
                      "h1_crown) becomes about 1.23"}


# ============================================================================================ mass, compute, report
BL051_ASSEMBLED_G = 996.6          # h1_crown.json mass.assembled_g (the print this ticket starts from)


def mass_rows(export: dict, pn: dict) -> dict:
    """Print delta against BL-051 (export info), the lug-fix share of it, and the pin-retention delta against what the
    ledger books (7075 pins: bag_attach pin volume, 36 mm + an 8 x 3 mm head, x 10; Ti hinge pins 5 x 44, x 2)."""
    from huntkit.materials import load
    rho_al = float(load("alu_7075_t6").require("density_kg_m3"))
    rho_ti = float(load("ti_6al_4v").require("density_kg_m3"))
    old_al = (math.pi * 2.5 ** 2 * 36.0 + math.pi * 4.0 ** 2 * 3.0) * rho_al * 1e-6
    old_ti = math.pi * 2.5 ** 2 * 44.0 * rho_ti * 1e-6
    booked = 10 * old_al + 2 * old_ti
    new_pins = pn["mass"]["pins_g"]
    a = export["assembled"]["g"]
    fx = export.get("fairleads_bl042", {}).get("lug_fixes_bl053", {})
    return {"assembled_g": a, "assembled_bl051_g": BL051_ASSEMBLED_G, "print_delta_g": round(a - BL051_ASSEMBLED_G, 1),
            "lower_g": export["lower"]["g"], "upper_g": export["upper"]["g"],
            "clevis_g": {k: export[k]["g"] for k in ("us2_clevis_R", "us2_clevis_L") if k in export},
            "lug_fixes_g": fx.get("added_g"), "lug_fixes_per_station_g": fx.get("per_station_g"),
            "pins_booked_g": round(booked, 2), "pins_new_g": new_pins,
            "clips_tethers_g": pn["mass"]["clips_tethers_g"],
            "retention_delta_g": round(new_pins + pn["mass"]["clips_tethers_g"] - booked, 2)}


ASSUMPTIONS = [
    ("QUARTER-CONTACT", "The under-strap meets the quarter 0-50 mm aft of the pin line (taut strap on the front edge "
     "against the spreader; a rounder bottom further aft): the design rows. 95 mm (half the quarter proxy's 190 mm "
     "depth) is run as a sensitivity.", "MT-1cr with a >= 50 kg quarter-shaped load: photograph the strap contact line "
     "from the side and measure its distance aft of the pin line."),
    ("QUARTER-WIDTH", "The load in the cradle is the 280 mm wide R-08 quarter proxy (huntkit/viz3d/params.py): US1's "
     "legs run outboard to its edges, US2's straight down at its edge; a narrow load takes both legs inboard to x 0.",
     "MT-1cr: legs' lateral direction at each pin, narrow (boned bag) and wide (bone-in) loads."),
    ("BELLY-40", "The cradle is designed down to a 40 mm belly at the 53 kg float limit; flatter is not credited. A "
     "hand can reach it (5th-percentile male one-arm pull 178-199 N, FAA HFDS Ch. 14 Exh. 14.5.2.1; a strong user, "
     "both hands or a braced foot pull more), so no strength cap on the hand is used.",
     "MT-1cr: cam each strap as hard as a strong user can, gloved, with the 53 kg load: belly measured >= 40 mm."),
    ("SUB-BC", "The print submodel is fixed where its box cuts the frame (US1: x -6..140 incl. the lumbar hub; US2: "
     "x 80..192); the smaller boxes gave LESS severe US1 numbers (sensitivity in the record).",
     "Strain gauges at the arm roots in MT-1cr (gauge table): measured <= the pass line."),
    ("CLEVIS-SHARE", "Outer cheek's share of the pin's y-z load 0.6 (1.0 as sensitivity); the inboard leg's x pull "
     "bears on the INNER (body) cheek and loads no clevis bolt.", "CLEVIS-SHARE A and B (gauge table)."),
    ("GAUGE-LOCAL", "T1 gauge values carry only the local bag-on pin load (the submodel has no global stay stress); "
     "the T1 pass line is advisory, MT-1cr and CLEVIS-SHARE (pin loads only) are the gates.",
     "Record T1 anyway; compare with the whole-body model when it is re-run on the BL-053 body."),
    ("TREE-FILL", "Tree supports use 12 % of the column volume they span (+ 3 dense 0.2 mm interface layers); high "
     "estimate 25 %.", "Bambu Studio plate preview of each file with the README's support settings: filament and time."),
    ("SAND-ALLOW", "Sanding the support witness off the stays' wearer faces removes <= 0.2 mm (about 2.2 % of the stay's "
     "bending section modulus).", "Caliper the stay depth at 5 points before / after sanding on the first article."),
    ("SCAR-KD", "Support witness sanded flat costs no more fatigue strength than the 2.2 % section loss.",
     "CA-1: add 2 XY bars printed over tree supports and sanded as the README says, against 2 printed flat."),
    ("WRAP-TENSION", "The strap's wrap over its own lug carries the bag-on cam-tight tension (US1 444 N, US2 296 N, "
     "factored 3.0) on the recorded meat drapes; the eye is necked to 18 mm in the throat.",
     "FIT-US: inspect the lip and strap for fuzz or whitening after the crank cycles."),
    ("CLIP-MASS", "R-clip 0.6 g, tether 0.2 g each.", "Weigh one set."),
    ("BODY-NOT-RERUN", "The whole-body check (h1_buckling.full_check) was not re-run on the BL-053 body: the fixes are "
     "local lug blocks (+56 g) away from the governing body regions (lumbar struts, stay L lower sleeve z 160-240).",
     "Re-run h1_crown --body on the BL-053 print body (heavy job, about an hour) before P1."),
]


def compute(log=print) -> dict:
    """Everything except the heavy re-runs, from the caches in outputs/h1_rev5 (lugs.json, gauges.json,
    printplan.json, joint.json, wrap.json, export_info.json); re-runs the missing ones."""
    import trimesh
    from . import h1_bedfit as BF
    from . import h1_lanes as LN
    OUT.mkdir(parents=True, exist_ok=True)
    U = _U()
    res = {"ticket": "BL-053", "date": "2026-11-13"}
    res["cradle_3d"] = U.cradle_3d()
    lp = OUT / "lugs.json"
    if not lp.exists():
        ref = OUT / "bl051_assembled.stl"          # the BL-051 print (git show <BL-051 commit>:.../h1_assembled.stl)
        lugs = {}
        for n in ("us1", "us2"):
            lugs[n] = {"print": lug_check(n)}
            if ref.exists():
                lugs[n]["bl051_print"] = lug_check(n, mesh=_mesh(ref), tag="bl051_print")
        lp.write_text(json.dumps({n: {t: {k: v for k, v in d.items() if not k.startswith("_")} for t, d in r.items()}
                                  for n, r in lugs.items()}, default=float))
    lugs = json.loads(lp.read_text())
    res["lugs"] = {n: {t: {k: v[k] for k in ("families", "design_min", "box")} for t, v in d.items()}
                   for n, d in lugs.items()}
    m = trimesh.load(PRINT / "h1_assembled.stl")
    wp = OUT / "wrap.json"
    if not wp.exists():
        wp.write_text(json.dumps(U.strap_wrap(m), default=float))
    res["strap_wrap"] = json.loads(wp.read_text())
    jp = OUT / "joint.json"
    if not jp.exists():
        jp.write_text(json.dumps(joint(res["strap_wrap"]), default=float))
    res["joint"] = json.loads(jp.read_text())
    gp = OUT / "gauges.json"
    if not gp.exists():
        gp.write_text(json.dumps(gauge_values(log=log), default=float))
    res["gauges"] = json.loads(gp.read_text())
    res["pins"] = pins()
    pp = json.loads((OUT / "printplan.json").read_text())
    res["print_plan"] = pp
    res["print_settings"] = print_settings(pp)
    ex = json.loads((OUT / "export_info.json").read_text())
    res["export"] = {k: ex[k] for k in ("assembled", "lower", "upper", "us2_clevis_R", "us2_clevis_L") if k in ex}
    res["mass"] = mass_rows(ex, res["pins"])
    res["slices"] = {"lanes": LN.slice_checks(), "joint": BF.joint_slices()}
    from . import h1_crown as C
    res["slices"]["crown"] = C.crown_continuity()
    res["bed"] = {nm: BF.bed_check(PRINT / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    res["trap_walls"] = BF.trap_walls()
    res["fixes"] = {"US1_HULL": US1_HULL, "US1_BUTTRESS": US1_BUTTRESS, "US2_BUTTRESS": US2_BUTTRESS,
                    "US2_FLARE": US2_FLARE, "SLOT_HALF": SLOT_HALF, "FLOOR_LIP_R": FLOOR_LIP_R, "BLOCK_LIP_R": BF.LIP_R,
                    "joint": {"dz": BF.JOINT.dz, "hex_trap": BF.JOINT.hex_trap}}
    res["assumptions"] = [{"id": a, "text": t, "settled_by": s} for a, t, s in ASSUMPTIONS]
    return res


# ============================================================================================ figures
def _save(fig, path: Path) -> str:
    SCREENS.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    from PIL import Image
    im = Image.open(path)
    if path.stat().st_size > 1.5e6:
        im.convert("P", palette=Image.ADAPTIVE).save(path, optimize=True)
    return str(path.relative_to(REPO))


def plot_lugs(res: dict, path: Path) -> str:
    """FI of the governing 40 mm row on each lug: BL-051 print (left) against the BL-053 print (right), elements
    within 1.5 mm of the section through the peak, in the plane square to the pin axis... shown as x-z (US1) / x-y."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    before = _mesh(Path(str(OUT / "bl051_assembled.stl"))) if (OUT / "bl051_assembled.stl").exists() else None
    fig, axs = plt.subplots(2, 2, figsize=(12, 9.5))
    for i, n in enumerate(("us1", "us2")):
        for j, (tag, mesh) in enumerate((("BL-051 print", before), ("BL-053 print", None))):
            ax = axs[i, j]
            if tag.startswith("BL-051") and mesh is None:
                ax.axis("off")
                continue
            key = "bl051_print" if j == 0 else "print"
            fam = res["lugs"][n][key]["families"]["cradle3d|b40"]
            L = lug_loads_3d(n)
            f = sub_fea(n, {"gov": L[fam["load"]]["vec"]}, box=BOXES[n], mesh=mesh, field="gov")
            fd = f["loads"]["_field"]
            cen, fi = fd["cen"], fd["fi"]
            pk = fam["peak_xyz"]
            sel = np.abs(cen[:, 2] - pk[2]) <= 0.6
            sc = ax.scatter(cen[sel, 0], cen[sel, 1], c=fi[sel], s=9, marker="s", cmap="inferno", vmin=0,
                            vmax=0.9, linewidths=0)
            ax.plot(pk[0], pk[1], "c+", ms=14, mew=2)
            ax.set_aspect("equal")
            ax.set_xlim(BOXES[n]["lo"][0] + 20 if n == "us1" else 105, 190 if n == "us2" else 125)
            ax.set_ylim(-45, 30)
            ax.set_title(f"{n.upper()} {tag}: {fam['load']} ({fam['force_n']:.0f} N)\nstrength {fam['strength_min']}"
                         f"  fatigue {fam['fatigue']} (goal 1.15)  section z {pk[2]:.0f}", fontsize=10)
            ax.set_xlabel("frame x mm")
            ax.set_ylabel("frame y mm (bag +)")
            ax.grid(alpha=0.25)
    fig.colorbar(sc, ax=axs, shrink=0.6, label="failure index (factored row; fatigue SF = 0.45 / FI)")
    fig.suptitle("BL-053 lane lugs on the print, 3D cradle leg at a 40 mm belly (53 kg float limit)", fontsize=12)
    return _save(fig, path)


def plot_belly(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, n in zip(axs, ("us1", "us2")):
        for key, col, lab in (("bl051_print", "#b0413e", "BL-051 print"), ("print", "#1f6f8b", "BL-053 print")):
            if key not in res["lugs"][n]:
                continue
            fam = res["lugs"][n][key]["families"]
            for fk, ls, sub in (("cradle3d", "-", "contact 0-50 mm aft"), ("cradle3d_dy95", "--", "95 mm aft (sens.)")):
                b = [40, 50, 60, 70]
                y = [fam[f"{fk}|b{v}"]["fatigue"] for v in b]
                ax.plot(b, y, ls, color=col, marker="o", label=f"{lab}, {sub}")
        ax.axhline(1.15, color="k", lw=1)
        ax.axhline(1.0, color="k", lw=0.6, ls=":")
        ax.text(70, 1.17, "goal 1.15", ha="right", fontsize=9)
        ax.set_xlabel("cradle belly mm (below the pin line)")
        ax.set_ylabel("fatigue SF (1e5 x 1.6 g)")
        ax.set_title(f"{n.upper()} lug: fatigue against belly")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    return _save(fig, path)


def plot_support(path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"stay": "#d1495b", "lug": "#edae49", "clevis": "#00798c", "other": "#8d99ae"}
    fig, axs = plt.subplots(1, 2, figsize=(12, 8))
    for ax, nm in zip(axs, ("lower", "upper")):
        f = OUT / f"supp_{nm}_+1.npz"
        if not f.exists():
            ax.axis("off")
            continue
        d = np.load(f)
        P, lab, col = d["pts"], d["lab"], d["col"]
        for k, c in cols.items():
            s = lab == k
            ax.scatter(P[s, 0], P[s, 2], s=1.2, c=c, label=f"{k} ({s.sum()} mm2)")
        ax.set_aspect("equal")
        ax.set_title(f"{nm} half, wearer face down: where tree supports touch\n(frame x-z, seen from the wearer side)")
        ax.set_xlabel("frame x mm")
        ax.set_ylabel("frame z mm")
        ax.legend(markerscale=8, fontsize=8, loc="upper right")
        ax.grid(alpha=0.25)
    return _save(fig, path)


def plot_joint(path: Path) -> str:
    """US2 joint: section across the traps (|x| 147, hex slot) and at the washer slot (|x| 150.5), new print."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    from . import h1_bedfit as BF
    m = _mesh()
    p = station("us2")
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.8))
    for ax, xx, tt in ((axs[0], 147.5, "hex slot |x| 147.5: nut held by its flats (8.2 AF)"),
                       (axs[1], 150.5, "washer slot |x| 150.5 (10.4)")):
        s = m.section(plane_origin=[xx, 0, 0], plane_normal=[1, 0, 0])
        for d in s.discrete:
            d = np.asarray(d)
            if np.abs(d[:, 2] - p["z"]).min() < 30:
                ax.add_patch(MP(d[:, 1:], closed=True, fc="#cfd8dc", ec="k", lw=0.7))
        for (y, z) in BF.bolt_axes(p):
            ax.plot(y, z, "r+", ms=10)
        ax.set_xlim(-20, 30)
        ax.set_ylim(p["z"] - 22, p["z"] + 22)
        ax.set_aspect("equal")
        ax.set_title(tt, fontsize=10)
        ax.set_xlabel("frame y mm")
        ax.set_ylabel("frame z mm")
        ax.grid(alpha=0.3)
    tw = BF.trap_walls()
    axs[2].axis("off")
    axs[2].text(0, 0.95, "US2 clevis joint (BL-053, M-2)", fontsize=12, weight="bold", va="top")
    axs[2].text(0, 0.82, f"bolt axes z pin +/- {BF.JOINT.dz:g} (was 8)\n"
                f"walls to block faces: washer {tw['washer_slot']['outer_wall_mm']} mm,\n"
                f"  hex {tw['hex_slot']['outer_wall_mm']} mm (rule >= 2)\n"
                f"between traps: {tw['washer_slot']['between_traps_mm']} mm\n"
                f"nut held by flats: {tw['nut_held_by_flats']}\n"
                f"lower aft lip r {BF.LIP_R:g} mm (strap wrap, M-6)", fontsize=10, va="top", family="monospace")
    return _save(fig, path)


def figures(res: dict) -> list:
    shots = []
    for k, fn in ((1, lambda pth: plot_lugs(res, pth)), (2, lambda pth: plot_belly(res, pth)),
                  (3, plot_support), (4, plot_joint)):
        try:
            shots.append(fn(SCREENS / f"{SHOT}{k}.png"))
        except Exception as e:  # pragma: no cover
            print(f"figure {k} failed: {e}")
    return shots


# ============================================================================================ record
SETTINGS_JSON = PRINT / "print_settings_bl053.json"


def _oz(g):
    return f"{g / 28.3495:.2f} oz"


def write_md(res: dict, shots: list) -> str:
    L = []
    a = L.append
    lg = res["lugs"]
    jt = res["joint"]
    ms = res["mass"]
    ps = res["print_settings"]
    cd = res["cradle_3d"]

    def fam(n, key, f):
        return lg[n][key]["families"][f]
    a("# H1 frame fixes from the fifth review (BL-053)\n")
    a("structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-053-frame-review5.md`, findings "
      "`review_20261113_fifth.md` (B-1, M-1..M-6). Code `huntkit/gendesign/h1_rev5.py` (`python -m "
      "huntkit.gendesign.h1_rev5 --fea` then the report with no flag), `designs/pack_5200/us_route.py` (`cradle_3d`, "
      "`strap_wrap`), joint `h1_bedfit` (dz 7, `trap_solid`, `trap_walls`, `lip_round_cut`), print hook "
      "`frame_h1.print_mesh` -> `h1_rev5.add_fixes`; tests `tests/test_h1_rev5.py`. Results `h1_rev5.json`; print "
      "data for BL-054 `print/frame_h1/print_settings_bl053.json`. Units mm, N, MPa, g (imperial in brackets).\n")
    a("## Summary\n")
    u1, u2 = lg["us1"]["print"]["design_min"], lg["us2"]["print"]["design_min"]
    b1, b2 = lg["us1"]["bl051_print"]["design_min"], lg["us2"]["bl051_print"]["design_min"]
    a(f"- **M-1 cradle direction:** the cradle is now a 3D string (`us_route.cradle_3d`): legs from each pin to the "
      f"quarter's lowest front edge, inboard to x 0 for a narrow load, outboard to the edge of the 280 mm R-08 quarter "
      f"proxy for a wide one, contact 0 / 50 mm aft (95 mm as sensitivity), bellies 40-70 mm at the 53 kg float limit "
      f"(V per strap US1 {cd['vertical_n']['us1']} N, US2 {cd['vertical_n']['us2']} N, factored 1.6 g x 1.5). The leg's "
      f"pull along the pin is V x_lane / (2 belly): at 40 mm US2 **1029 N inboard** onto the INNER (body) cheek, US1 "
      f"655 N. Checked on a submodel cut from the print itself (lower branch, hub, clevis, Ti bolts in; the stub model "
      f"left the branch out) with the eye-edge-on-the-cheek rule that failed the hinge before BL-049.")
    a(f"- **The BL-051 print fails it:** at a 40 mm belly US1 strength {b1['strength']} / fatigue {b1['fatigue']} (the "
      f"fairlead's merge into the lower branch), US2 {b2['strength']} / {b2['fatigue']} (inner cheek root). At the old "
      f"60 mm minimum: US1 {fam('us1', 'bl051_print', 'cradle3d|b60')['fatigue']}, US2 "
      f"{fam('us2', 'bl051_print', 'cradle3d|b60')['fatigue']}.")
    a(f"- **M-3 fix (applied, re-exported):** US1: the lug block and the lower branch under it filled to their convex "
      f"hull (BL-049 proposal 2, the arm onto the branch) and the inner cheek grown to +/-12 with a buttress; US2: inner "
      f"cheek grown to +/-14 with a buttress, root flared to +/-22 mm over 16 mm at the stay. Both buttresses leave a "
      f"12 mm slot about the pin axis for the pin tail and its clip. **On the new print, every design row down to a "
      f"40 mm belly: US1 strength {u1['strength']} / fatigue {u1['fatigue']}, US2 {u2['strength']} / {u2['fatigue']}** "
      f"(goal 1.5 / 1.15; contact 95 mm aft: US1 {fam('us1', 'print', 'cradle3d_dy95|b40')['fatigue']}, US2 "
      f"{fam('us2', 'print', 'cradle3d_dy95|b40')['fatigue']}). The belly stops being a safety rule; the card can stay "
      f"as advice (BL-054). **Mass +{ms['print_delta_g']} g print** ({_oz(ms['print_delta_g'])}; fixes "
      f"{ms['lug_fixes_g']} g: US1 {ms['lug_fixes_per_station_g']['us1_R']} g, US2 {ms['lug_fixes_per_station_g']['us2_R']}"
      f" g a side).")
    s6, s10 = jt["share_0.6"], jt["share_1"]
    a(f"- **M-2 nut traps:** two-step trap as at z 234 (washer slot 10.4 x 1.2 mm, then an 8.2 AF hex slot that holds "
      f"the nut by its flats), bolt axes moved to z pin +/- 7: walls {res['trap_walls']['min_wall_mm']} mm (>= 2). "
      f"Joint on every row incl. the 3D cradle and the strap wrap: share 0.6 strength "
      f"{s6['families']['c3d']['min_sf']} / fatigue {s6['families']['c3d']['min_fatigue']} (3D rows); share 1.0 "
      f"{s10['families']['c3d']['min_sf']} / {s10['families']['c3d']['min_fatigue']}. The BL-051 lane rows (legs in "
      f"the y-z plane, a direction the lane geometry cannot produce) still read {s10['worst_fatigue']['fatigue']} at "
      f"share 1.0; they are kept for comparison only.")
    w = res["strap_wrap"]["worst"]
    a(f"- **M-6 strap route:** each strap now laid over its own print (`us_route.strap_wrap`): US2 wraps the joint "
      f"blocks' lower aft edge by up to {w['us2']['wrap_deg']} deg, {w['us2']['bearing_n']} N on the lip (bag-on 296 N "
      f"factored), now a 3 mm radius ({w['us2']['lip_pressure_mpa']} MPa line pressure); US1 clears its own floor end "
      f"once that is rounded r 3 (wrap {w['us1']['wrap_deg']} deg). The clevis share of the wrap is in the joint check "
      f"(fatigue >= {s10['families']['wrap']['min_fatigue']}). Strap clearance to hinge / HE re-run on the new print: "
      f"US1 {res.get('clearance', {}).get('worst_clear_mm', {}).get('us1', '-')} / US2 "
      f"{res.get('clearance', {}).get('worst_clear_mm', {}).get('us2', '-')} mm (>= 10).")
    a(f"- **M-4 gauges:** model root stress (MPa) and microstrain with a placement band and a numeric pass line per "
      f"gauge, load step and test (section 4); CLEVIS-SHARE raised to the governing 3D rows (A: inboard leg, proof "
      f"{res['gauges']['tests']['CLEVIS-SHARE|us2_inboard']['steps'][0]['pin_load_n']} N; B: the clevis's share-1.0 "
      f"leg, proof {res['gauges']['tests']['CLEVIS-SHARE|us2_yz']['steps'][0]['pin_load_n']} N).")
    pn = res["pins"]
    a(f"- **M-5 pins:** one scheme on all 12 stations: headed pin (head outboard), R-clip in a 1.3 mm cross hole 2.5 mm "
      f"past the far cheek, pin and clip on one Dyneema tether; hinge Ti 5 x {pn['stations']['hinge']['shank_mm']}, "
      f"the others 7075 5 x {pn['stations']['us1']['shank_mm']}; test PIN-RET. Mass +{ms['retention_delta_g']} g "
      f"against what the ledger books.")
    lo, up = ps["files"]["h1_lower_flat.stl"], ps["files"]["h1_upper_flat.stl"]
    a(f"- **B-1 printability:** orientation kept (layer normal = frame y, wearer face down); tree supports from the "
      f"plate in PAHT-CF, 3 interface layers, top gap 0.2-0.25 mm, blockers in every bore and trap. Lower half "
      f"{lo['part_g']} g + {lo['support_g_est']} g support (high {lo['support_g_high']} g), about {lo['print_h_est']} h; "
      f"upper {up['part_g']} g + {up['support_g_est']} g (high {up['support_g_high']} g), about {up['print_h_est']} h. "
      f"Support scars land on fatigue-critical faces (the stays' wearer faces and the lug undersides): sand to "
      f"<= 0.2 mm (2.2 % of the stay section modulus; body sim-basis fatigue 1.258 -> about 1.23) and add 2 XY bars "
      f"printed over supports to CA-1 (SCAR-KD). Data for BL-054: `print/frame_h1/print_settings_bl053.json`.")
    a(f"- **Finish:** re-exported (assembled {ms['assembled_g']} g, lower {ms['lower_g']} g, upper {ms['upper_g']} g, "
      f"clevises {list(ms['clevis_g'].values())[0]} g each), every slice check passes, both halves still fit the H2S bed "
      f"with the brim (lower spare {res['bed']['lower']['spare_mm']} mm). Ledger row BL053. The whole-body check was "
      f"not re-run (ASSUMPTION BODY-NOT-RERUN).\n")
    a("## 1. The cradle as a 3D string (M-1)\n")
    a("In the plane through the two pins that touches the quarter's lowest front edge, a taut strap is two straight "
      "legs from each pin to that edge; a rounded or wide bottom only makes the legs steeper, so the straight V is the "
      "flattest (highest-tension) case for a given drop. Vertical equilibrium per strap: V = 2 T belly / |leg|. The "
      "lateral pull T dx / |leg| = V dx / (2 belly) does not depend on the contact's aft distance dy; dy adds only to "
      "the y-z part. Leg vector on the R pin (x + outboard, y + aft, z + up), tension factored as the 720 N row was "
      "(1.6 g x 1.5), from `us_route.cradle_3d`:\n")
    a("| strap | belly mm | legs | dy mm | vector N | tension N | below horizontal deg |")
    a("|---|---:|---|---:|---|---:|---:|")
    for k, v in cd["rows"].items():
        if v["belly_mm"] in (40.0, 60.0) and v["dy_mm"] in (0.0, 50.0, 95.0):
            a(f"| {v['strap']} | {v['belly_mm']:g} | {v['legs']} | {v['dy_mm']:g} | {v['vec_n']} | {v['tension_n']} | "
              f"{v['leg_below_horizontal_deg']} |")
    a("\n'in' = a narrow load the strap meets at x 0 (legs inboard); 'out' = the 280 mm quarter, wider than the US1 span "
      "(legs outboard to its edge at x 140) and as wide as US2's edge (legs straight down there). MT-1cr must pull "
      "along these vectors (section 4), not along the BL-051 y-z leg.\n")
    a("## 2. Lugs on the print, before and after (M-1, M-3)\n")
    a("Submodel (`sub_fea`): the print sliced into 1 mm voxels inside a box (US1 x -6..140, y -56..32, z 46..146, the "
      "lumbar hub and the lower branch in; US2 x 80..192, y -50..40, z 90..196, the clevis in), solid cut by the box "
      "fixed, the US2 joint face a 1-voxel gap except the Ti bolts (E 110 GPa); the pin's y-z force as bearing on the "
      "hole band of both cheeks, its x force as the eye's edge on the inner face of the cheek it moves towards; FI99 "
      "per region (fairlead, root, arm, US1 web, the BL-053 additions), layer normal frame y; elements within 5 mm of "
      "the box and the US2 joint's own bearing zone (checked by `joint_check`) left out of the statistics. Box "
      "sensitivity (US1): a box ending at x 34 read the BL-051 US1 at 0.63 instead of 0.54, so the large box is kept.\n")
    a("| lug | print | belly | strength (min) | fatigue | governing row | region | peak (frame) |")
    a("|---|---|---:|---:|---:|---|---|---|")
    for n in ("us1", "us2"):
        for key, lab in (("bl051_print", "BL-051"), ("print", "BL-053")):
            for b in (40, 50, 60, 70):
                f = fam(n, key, f"cradle3d|b{b}")
                a(f"| {n} | {lab} | {b} | {f['strength_min']} | {f['fatigue']} | {f['load']} ({f['force_n']} N) | "
                  f"{f['region']} | {f['peak_xyz']} |")
            f = fam(n, key, "cradle3d_dy95|b40")
            a(f"| {n} | {lab} | 40, dy 95 (sens.) | {f['strength_min']} | {f['fatigue']} | {f['load']} | {f['region']} | "
              f"{f['peak_xyz']} |")
            f = fam(n, key, "bagon|-")
            a(f"| {n} | {lab} | bag-on (3.0) | {f['strength_min']} | {f['fatigue']} | {f['load']} | {f['region']} | "
              f"{f['peak_xyz']} |")
    a("\nRequirement (ticket): strength >= 1.5, fatigue >= 1.15 (1e5 x 1.6 g on the factored row / 2.4) down to a "
      "40 mm belly. **Met on the BL-053 print for every design row; the dy 95 sensitivity sits at 1.15-1.16.** The "
      "fixes, in `h1_rev5` (US1_HULL, US1_BUTTRESS, US2_BUTTRESS, US2_FLARE, SLOT_HALF), are unioned onto the print by "
      "`add_fixes` and the FEA above runs on the exported STL with nothing added. Why each: US1's aft and outboard "
      "pull bent the fairlead block against the small merge with the lower branch (peak at the merge, x 70, y -14.5); "
      "filling the gap to the hull turns the block and the branch into one section and the column fill alone (tried) "
      "only moved the notch. The inner cheeks carry the inboard pull out of plane at their floor corner (same "
      "mechanism as the hinge): growing them in z and propping their inboard face takes that corner down. US2's root "
      "then governed at the stay; the flare (outboard of the stay surface, clear of the spreader sheet edge at x 121) "
      "lifts it.\n")
    a("Fairlead pins at the new rows (y-z part bends the pin; the x part goes to the cheek through the eye): see "
      "section 5.\n")
    a("## 3. US2 clevis joint and the strap wrap (M-2, M-6)\n")
    tw = res["trap_walls"]
    a(f"Trap (`h1_bedfit.trap_solid`, as the z 234 joint): washer slot {BF_slot()} mm wide over |x| 149.8-151 (washer "
      f"1 mm + 0.2), then an 8.2 AF hex slot (nut 8 AF, corners 9.24: it cannot turn) over |x| 145.8-149.8, both open to "
      f"the wearer face for the nut to slide in. Bolt axes at z pin +/- 7: walls washer slot {tw['washer_slot']['outer_wall_mm']} "
      f"mm, hex slot {tw['hex_slot']['outer_wall_mm']} mm, between the traps {tw['washer_slot']['between_traps_mm']} mm "
      f"(rule >= 2: {tw['pass_2mm']}). Slice check of the new STL (`joint_slices`): "
      f"{res['slices']['joint']['pass']}.\n")
    a("| share | family | worst row | force on clevis N | strength | fatigue | check |")
    a("|---:|---|---|---|---:|---:|---|")
    for sk in ("share_0.6", "share_1"):
        for fk, f in jt[sk]["families"].items():
            a(f"| {sk.split('_')[1]} | {fk} | {f['load']} | {f['force_on_clevis_n']} | {f['min_sf']} | {f['min_fatigue']}"
              f" | {f['check_s']} / {f['check_f']} |")
    a("\n'c3d' = every 3D cradle row incl. dy 95 (the worst is the y-z 'out' leg, the clevis's own case); "
      "'cradle_lane*' = the BL-051 y-z rows, kept for comparison (no lane geometry produces them). 'wrap' = the strap's "
      "bearing on the block lip, clevis share of the 25 mm strap outboard of the joint face, applied at the lip.\n")
    a("Strap wrap (`us_route.strap_wrap`, R side, bag-on cam-tight, the recorded 'now' meat drapes):\n")
    a("| torso | strap | wrap deg | bearing N (y, z) | on the print at (y, z) | lip r mm |")
    a("|---:|---|---:|---|---|---:|")
    for r in res["strap_wrap"]["rows"]:
        a(f"| {r['torso']} | {r['strap']} | {r['wrap_deg']} | {r['bearing_n']} {r['bearing_yz_n']} | "
          f"{r['contact_yz'][:2]} | {r['lip_r_mm']} |")
    a("\nOn the BL-051 print the same model gives US2 up to 38 deg / 193 N on the sharp (r 1.5) block edge and US1 "
      "3.9 deg / 30 N on its floor end. The lip is a wear point: FIT-US must inspect strap and lip for fuzz or "
      "whitening after the crank cycles (BL-054 kit text).\n")
    a("## 4. Gauge pass values (M-4)\n")
    g = res["gauges"]
    a(f"Gauge sites (R side, bag face, gauge axis along the arm, centre 3 mm off the stay surface): US1 at "
      f"{[g['sites']['us1'][k] for k in ('x', 'y', 'z')]}, US2 at {[g['sites']['us2'][k] for k in ('x', 'y', 'z')]}. "
      f"Model sigma_xx on the BL-053 print; band = min / max within +/- 1.5 mm of the site; E_xy {g['E_xy_mpa']:g} MPa. "
      f"**Pass if the measured |microstrain| is at most the pass line** (band extreme x 1.15). Pull along the unit "
      f"vector given (frame, R pin; mirror x for L).\n")
    a("| test | gauge | pull unit vector | pin load N | sigma MPa | band MPa | microstrain | pass if abs <= |")
    a("|---|---|---|---:|---:|---|---:|---:|")
    for tk, t in g["tests"].items():
        for st in t["steps"]:
            a(f"| {tk.split('|')[0]} {tk.split('|')[1] if 'CLEVIS' in tk else ''} | {tk.split('|')[1][:3]} | "
              f"{t['pull_unit_vector_frame_R']} | {st['pin_load_n']} | {st['sigma_mpa']} | {st['band_mpa']} | "
              f"{st['microstrain']:g} | {st['pass_if_abs_microstrain_at_most']:g} |")
    a("\nMT-1cr: pull each pin along its governing 3D leg (US1: outboard, aft, down, the wide quarter; US2: inboard, "
      "aft, down) at 240 / 480 / 720 N and the factored row. CLEVIS-SHARE A: the inboard leg, the eye on the INNER "
      "(body) cheek with the PTFE shim there, proof at the factored row, 1e5 cycles at x 1.6 / 2.4 (R 0.1). "
      "CLEVIS-SHARE B: the y-z leg with the eye on the OUTER (clevis) cheek (the share-1.0 case). The US1 arm-root "
      "gauge now reads little (the BL-053 block carries the pin load into the branch; < 4 MPa at the factored row): "
      "keep it as a check that the block works, and if a second gauge is fitted put it on the US1 outer cheek's "
      "outboard face at its floor (the governing spot, x 80-88, z 98-104). T1 values are local only (GAUGE-LOCAL).\n")
    a("## 5. Pin retention (M-5)\n")
    a(f"Scheme: {pn['scheme']}. Retainer: {pn['retainer']['part']}; source {pn['retainer']['source']}; tether: "
      f"{pn['retainer']['tether']}. Clip wire double shear {pn['clip_double_shear_n']:g} N ({pn['clip_uts_source']}); "
      f"the eye's pull along the pin bears on the cheek, not the pin, so the clip only stops a pin that walks. An R-clip "
      f"is spring-held round the pin (it does not unscrew or back out in vibration); PIN-RET (b) checks it after the "
      f"walk and the cycle tests.\n")
    a("| station | material | shank mm (span + tail) | head | clip side | pin g | set g (pin + clip + tether) | "
      "out at bag-off | pin bending yield / fatigue |")
    a("|---|---|---:|---|---|---:|---:|---|---|")
    for n, r in pn["stations"].items():
        bd = r.get("bending", {})
        bs = f"{bd.get('sf_yield', '-')} / {bd.get('sf_fatigue', '-')}"
        if "dy95_sf_yield" in bd:
            bs += f" (dy 95: {bd['dy95_sf_yield']} / {bd['dy95_sf_fatigue']})"
        a(f"| {n} (x2) | {r['material']} | {r['shank_mm']} | {r['head_mm'][0]:g} x {r['head_mm'][1]:g} | "
          f"{r['clip_side']} | {r['pin_g']} | {r['set_g']} | {r['removed_at_bag_off']} | {bs} |")
    a("\nThe US1 7075 pin reads 0.97 in fatigue only on the dy 95 sensitivity row; a Ti pin there (+1.0 g each) would "
      "clear it (owner option, not applied). Test PIN-RET:\n")
    for s_ in pn["test"]["steps"]:
        a(f"- {s_}")
    a("")
    a("## 6. Printability (B-1)\n")
    a("Each part voxelised (1 mm) in its print orientation; a voxel needs support when nothing of the layer below lies "
      "within one voxel sideways (45 deg). Plate contact, supported down area by region, support column to the plate "
      "or the part below (`support_map`).\n")
    a("| file (as exported) | plate contact mm2 | supported mm2 (stay / lug / other) | part g | support g (est / high) "
      "| print h (est) |")
    a("|---|---:|---|---:|---|---:|")
    for k, f in ps["files"].items():
        r = f["supported_by_region_mm2"]
        a(f"| {k} | {f['plate_contact_mm2']:g} | {f['supported_down_area_mm2']:g} ({r['stay']:g} / {r['lug']:g} / "
          f"{r['other']:g}) | {f['part_g']} | {f['support_g_est']} / {f['support_g_high']} | {f['print_h_est']} |")
    pp = res["print_plan"]
    a(f"\nFlipped (bag face down) for comparison: lower supported {pp['lower|-1']['supported_mm2']:g} mm2 (stay "
      f"{pp['lower|-1']['supported_by_region_mm2']['stay']:g}), upper {pp['upper|-1']['supported_mm2']:g} mm2 (stay "
      f"{pp['upper|-1']['supported_by_region_mm2']['stay']:g}): no less support, and the scars move to the stays' bag "
      f"faces and the fairlead tips (eye bearing, HE fit). **Chosen: as exported, wearer face down, for every file**, "
      f"test pieces included (they must carry the frame's surfaces). Settings: {ps['supports']['type']}; "
      f"{ps['supports']['material']}; top Z {ps['supports']['top_z_distance_mm']} mm; "
      f"{ps['supports']['interface_layers']} interface layers; blockers: {'; '.join(ps['supports']['blockers'])}.\n")
    a(f"**Scars on fatigue-critical faces: yes.** {ps['scars']['where']}. Finish: {ps['scars']['finish']}. "
      f"{SAND_ALLOW['note']}. CA-1 gets 2 XY bars printed over tree supports and sanded the same way (SCAR-KD).\n")
    a("## 7. Checks on the re-exported print\n")
    sl = res["slices"]
    a(f"- `h1_lanes.slice_checks`: fairleads {sl['lanes'].get('fairleads_pass')}, spine channel "
      f"{sl['lanes'].get('channel', {}).get('pass')}, pawl {sl['lanes'].get('pawl', {}).get('pass')}, test pieces "
      f"{sl['lanes'].get('pieces_pass')}.")
    a(f"- `h1_bedfit.joint_slices` (US2 holes, traps open to the wearer face, joint face closed): {sl['joint']['pass']}.")
    a(f"- `h1_crown.crown_continuity`: {sl['crown'].get('pass')}.")
    a(f"- Bed (H2S 340 x 320, 8 mm brim): lower {res['bed']['lower']['extents_mm']} spare "
      f"{res['bed']['lower']['spare_mm']}; upper {res['bed']['upper']['extents_mm']} spare {res['bed']['upper']['spare_mm']}.")
    cl = res.get("clearance")
    if cl:
        a(f"- Strap clearance to hinge / HE / other US on the 12 drape rows (`us_route.run_layout('now')`): US1 "
          f"{cl['worst_clear_mm']['us1']} / US2 {cl['worst_clear_mm']['us2']} mm (>= 10: {cl['pass']}).")
    a("- Every file a closed single shell (`h1_buckling.export_print` asserts it).\n")
    a("## 8. Mass\n")
    a("| item | g | oz |")
    a("|---|---:|---:|")
    a(f"| print, assembled BL-053 {ms['assembled_g']} - BL-051 {ms['assembled_bl051_g']} | +{ms['print_delta_g']} | "
      f"+{ms['print_delta_g'] / 28.3495:.2f} |")
    for k, v in ms["lug_fixes_per_station_g"].items():
        a(f"| of which lug fixes {k} | {v} | {v / 28.3495:.2f} |")
    a(f"| pin retention: 12 pins as now specified {ms['pins_new_g']} + 12 clips and tethers {ms['clips_tethers_g']} - "
      f"pins booked {ms['pins_booked_g']} | +{ms['retention_delta_g']} | +{ms['retention_delta_g'] / 28.3495:.2f} |")
    a(f"\nLedger row BL053 (`huntkit/mass/ledger.py`, from this json; H1 configs). Printed body now lower "
      f"{ms['lower_g']} g, upper {ms['upper_g']} g, clevises {list(ms['clevis_g'].values())[0]} g each.\n")
    a("**Mass reductions that keep the SF (not applied):** (1) US1 block: it is the full convex hull of the lug block "
      "and the branch (about 15 g a side of the 21 g); a web only under the fairlead floor, pocketed in z, is the "
      "obvious trim, but the column-fill variant that tried it moved the notch to the branch (fatigue 0.56), so any "
      "trim needs a smooth fillet and a re-run (`lug_check` with `extra`); (2) US2 has 0.35 of fatigue margin at the "
      "design rows (1.50) but the dy 95 sensitivity sits at 1.15: the flare is the only removable item, worth about "
      "1 g; (3) 7075 pins for the hinge are not possible (BL-049).\n")
    a("## 9. Assumptions\n")
    for x in res["assumptions"]:
        a(f"- ASSUMPTION {x['id']}: {x['text']} Settled by: {x['settled_by']}")
    a("- ASSUMPTION Carried: CLEVIS-DRY, CLEVIS-PRINT, HEAD-BEAR, CLEVIS-FACE (h1_crown.md / h1_bedfit.md); US-FLEET, "
      "DRAPE-US (us_route.json); FI99-RULE (h1_lanes.md).\n")
    a("## 10. Owner decisions\n")
    a(f"- Accept +{ms['print_delta_g']} g of print (US1 block and buttresses, US2 buttress and flare) for a cradle that "
      f"needs no minimum belly. The alternative, keeping the BL-051 print and the 60 mm belly rule, does not hold on "
      f"the 3D model either (BL-051 print at 60 mm: US1 {fam('us1', 'bl051_print', 'cradle3d|b60')['fatigue']}, US2 "
      f"{fam('us2', 'bl051_print', 'cradle3d|b60')['fatigue']}, goal 1.15) and the belly cannot be held by feel.")
    a("- Accept sanded support scars on the stays' wearer faces (about 2 % section) pending CA-1's over-support bars.")
    a("- US1 pins in Ti for the dy 95 sensitivity (+2 g), or keep 7075.\n")
    a("## 11. Screenshots\n")
    for s_ in shots:
        a(f"- `{s_}`")
    return "\n".join(L) + "\n"


def BF_slot() -> str:
    from . import h1_bedfit as BF
    return f"{BF.JOINT.slot_w:g}"


def report(log=print) -> dict:
    res = json.loads((OUT / "compute.json").read_text()) if (OUT / "compute.json").exists() else compute(log=log)
    cp = OUT / "clearance.json"
    if cp.exists():
        res["clearance"] = json.loads(cp.read_text())
    shots = sorted(str(p.relative_to(REPO)) for p in SCREENS.glob(f"{SHOT}*.png"))
    if not shots:
        shots = figures(res)
    keep = {k: v for k, v in res.items() if k != "print_plan"}
    keep["print_plan"] = {k: {kk: vv for kk, vv in v.items()} for k, v in res["print_plan"].items()}
    keep["screenshots"] = shots
    RESULTS.write_text(json.dumps(keep, indent=1, default=float))
    SETTINGS_JSON.write_text(json.dumps(res["print_settings"], indent=1, default=float))
    DOC.write_text(write_md(res, shots))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fea", action="store_true", help="re-run the lug submodels, gauges and joint (outputs/h1_rev5)")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.fea:
        for f in ("lugs.json", "gauges.json", "joint.json", "wrap.json"):
            (OUT / f).unlink(missing_ok=True)
        r = compute()
        (OUT / "compute.json").write_text(json.dumps(r, indent=1, default=float))
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
