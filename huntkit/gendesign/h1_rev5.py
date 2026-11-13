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
US2_FLARE = {"half_z_root": 22.0, "len": 10.0}
US1_FLARE = None


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
    """Convex point sets (frame coordinates) of the US2 inner-cheek growth and buttress for station p (either side)."""
    q = prm or US2_BUTTRESS
    if q is None:
        return []
    g = p["geom"]
    s = p["sign"]
    xi = abs(p["x"]) - g.throat / 2.0                  # inner cheek's throat face |x|
    xo = xi - g.cheek                                  # its inboard face
    y0 = p["yc"] - 6.0                                 # into the arm (arm top at y_floor, bottom yc - 8..-11)
    yt = p["y_tip"] - q["top_drop"]
    ye = p["y_floor"] if q["end_y"] == "floor" else float(q["end_y"])
    z0, z1 = p["z"] - q["half_z"], p["z"] + q["half_z"]
    cheek = [(x, y, z) for x in (xo, xi) for y in (y0, yt) for z in (z0, z1)]
    wedge = [(x, y, z) for (x, y) in ((xo + 0.5, y0), (xo + 0.5, yt), (xo - q["len"], y0), (xo - q["len"], ye))
             for z in (z0, z1)]
    out = []
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
            hole = np.hypot(c[:, 1] - p["y_pin"], c[:, 2] - p["z"]) < g.hole_d / 2.0
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
