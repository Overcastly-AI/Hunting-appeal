"""BL-042: complete fairleads on the H1 print files, a hinge fairlead the bag's eye can pass, and a geometric check
on the exported STL itself.

    python -m huntkit.gendesign.h1_fairleads --fea      # cheek / pin checks, legacy vs BL-042 hinge (cached)
    python -m huntkit.gendesign.h1_fairleads --export   # print files (h1_buckling.export_print) + test pieces
    python -m huntkit.gendesign.h1_fairleads            # slice check of the STLs, figures, md / json

Why (review_20261113_rev3_third.md):
- Z-2: the H1 voxel model stops at the bag envelope (frame_topopt.Y_HI_GRID 16 mm, ``passive_void``), so every fairlead
  in the H1 print files was cut off at y 15.46: no front wall, no pin hole, a solid throat. ``frame_h1.keepouts``
  counted only the voxels inside the envelope and reported 1.000.
- Z-1: the hinge fairlead left 1.9 mm between the pin and the throat floor for a 3-ply (4.5 mm) webbing eye, and its
  18 mm throat had zero clearance on the 18 mm neck.

What it does:
1. ``add_fairleads``: every fairlead (``bag_attach.stations``: hinge, US1, US2, IM1, IM2, IM3, both sides) is meshed
   exactly from ``bag_attach.fairlead_local`` with its station geometry (``station_geom``: hinge = ``HINGE_GEOM``,
   IM3 = the BL-021 28 mm cheek, the rest the 2026-11-01 fairlead), unioned onto the smooth body, then the throat
   (rounded-corner prism from the floor up) and the pin hole (printed 7.0, reamed 7.2) are cut exactly.
   ``frame_h1.print_mesh`` calls it, so every H1 export carries complete fairleads.
2. ``check_stl``: slices an STL through each pin axis (plane z = station) and through each cheek (plane x = cheek
   middle) and measures hole, throat, floor gap, cheek, front wall and cheek height against the design; for the
   hinge it also tests the 3-ply eye envelope (a rectangle neck_max x 4.5 mm under the pin) against the section.
3. ``fairlead_fea``: the fairlead FEA of ``bag_attach.solve_fairlead`` (same mesh, load rule, FI99 rule) with a
   lateral push on the cheek's inner face (im3_body_simloads.eye_fea's rule), for the rev C governing hinge force
   and the CORRIE F rev 1 sim hinge-pin vectors; legacy vs BL-042 geometry. ``pin_bending``: 5 mm 7075 pin across
   the wider throat.
4. Standalone test pieces (HE-FIT hinge fairlead, IM3-EC cheek) cut from the fixed print mesh.

Units mm, N, MPa, g.
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
RESULTS = ANALYSIS / "h1_fairleads.json"
DOC = ANALYSIS / "h1_fairleads.md"
PRINT_DIR = PACK / "print" / "frame_h1"
PIECES_DIR = PRINT_DIR / "test_pieces"
OUT = REPO / "outputs" / "h1_fairleads"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL042_"
RHO_G_MM3 = 1.06e-3          # PAHT-CF printed density (frame_h1 / h1_buckling: volume x 1.06 g/cm3)

HOLE_PRINT_D = 7.0           # h1_buckling.IM3_HOLE_PRINT_D (ASSUMPTION HOLE_REAM): printed 7.0, reamed to 7.2
THROAT_FILLET = 1.0          # ASSUMPTION: 1 mm fillet left in the throat's floor corners (cut profile radius)
MESH_H = 0.25                # marching-cubes cell for the exact fairlead solids, mm
# tolerances of the STL check: facets of the 96-segment holes and 0.25 mm marching cubes, Taubin-smoothed body
EYE_MESH_TOL = 0.05          # BL-045: the eye-stack test polygon is shrunk by the export's simplify tolerance (0.04 mm,
#                              frame_h1.SIMPLIFY_MM): a floor 0.01 mm proud after simplify is mesh noise, not a print
#                              error (the 1.0 mm HE-GAP-MARGIN is the print tolerance)
TOL = {"hole_d": 0.15, "hole_c": 0.3, "throat": 0.2, "wall": 0.3, "cheek": 0.3, "half_z": 0.5, "floor": 0.3}

STAY_AX_60 = 6.0             # ASSUMPTION STAY-AX: the H1 stay at z 40-80 is 11-16 mm across the pin axis (STL slices,
#                              h1_fairleads.md 3), narrower than the 18.7 mm stay_radius circle; sensitivity run
G_WALK = 1.6                 # HA-LS-1 rev C fatigue: 1e5 cycles 0 -> 1.6 g
FACTOR = 3.0                 # rev C: 2.0 g x 1.5 on a 1 g force (the sim vectors are 1 g)


# ======================================================================================= geometry
def station_geom(name: str):
    """Print geometry of a fairlead station: hinge = BL-042 HINGE_GEOM; IM1-IM3 / US1-US2 = BL-045 eye_geom (the hinge's
    eye clearance and saddle on the station's stay; IM3 keeps the BL-021 28 mm cheek)."""
    from . import bag_attach as BA
    from .h1_buckling import IM3_HALF_Z
    if name == "hinge":
        return BA.HINGE_GEOM
    if name in BA.IMUS_STATIONS:          # BL-045: every IM / US pin carries a webbing eye -> the hinge's clearance
        return BA.eye_geom(name)
    raise KeyError(name)


def bl042_geom_of(name: str):
    """The geometry BL-042 printed (before BL-045): hinge = HINGE_GEOM, IM3 = 28 mm cheek, others 2026-11-01."""
    from . import bag_attach as BA
    from .h1_buckling import IM3_HALF_Z
    if name == "hinge":
        return BA.HINGE_GEOM
    if name == "im3":
        return dataclasses.replace(BA.legacy_geom(), half_z=IM3_HALF_Z)
    return BA.legacy_geom()


def eye_envelope(name: str) -> dict:
    """The eye envelope the slice check holds a station to (hinge: BL-042; IM / US: BL-045)."""
    from . import bag_attach as BA
    return BA.HINGE_EYE_ENVELOPE if name == "hinge" else BA.imus_eye_envelope(name)


def placed(geom_of=station_geom) -> list:
    """Every fairlead in frame coordinates: station, stay centre y (frame_branch._sleeve_y) and radius
    (stay_radius(z, SCALE)), pin centre y, floor y, tip y. Same placement as bag_attach.attachment_field."""
    from . import bag_attach as BA
    from .frame_branch import _sleeve_y, stay_radius
    out = []
    for st in BA.stations():
        g = geom_of(st["name"])
        r = float(stay_radius(st["z"], BA.SCALE))
        yc = float(np.asarray(_sleeve_y(st["z"]), float))
        out.append({**st, "geom": g, "stay_r": r, "yc": yc, "y_pin": yc + r + g.hole_proud,
                    "y_floor": yc + r + g.floor_proud, "y_tip": yc + r + g.tip_proud})
    return out


def _fairlead_solid(p: dict):
    """Exact (0.25 mm marching cubes) fairlead of station ``p`` as a manifold in frame coordinates, its pin hole at
    the printed diameter."""
    from skimage.measure import marching_cubes
    import trimesh
    from . import bag_attach as BA
    from .surface import _to_manifold
    # the hole here is 1 mm under the printed size, so the exact 96-gon cut (_pin_hole) alone makes the bore surface
    # (two coincident cylinders leave slivers that an STL round trip turns into non-manifold edges)
    g0 = p["geom"]
    g = dataclasses.replace(g0, hole_d=HOLE_PRINT_D - 1.0,
                            wall_front=g0.wall_front + (g0.hole_d - (HOLE_PRINT_D - 1.0)) / 2.0)   # same tip
    r = p["stay_r"]
    hx = g.throat / 2 + g.cheek + 1.5
    # grid offset off the design planes: a zero level exactly on grid nodes gives degenerate triangles that an STL
    # round trip turns into non-manifold edges
    lo = np.array([-hx, r - g.embed - 1.5, -g.half_z - 1.5]) - np.array([0.0917, 0.0533, 0.0771])
    hi = np.array([hx, r + g.tip_proud + 1.5, g.half_z + 1.5])
    n = np.ceil((hi - lo) / MESH_H).astype(int) + 1
    ax = [lo[k] + MESH_H * np.arange(n[k]) for k in range(3)]
    X, Y, Z = np.meshgrid(*ax, indexing="ij")
    f = BA.fairlead_local(np.c_[X.ravel(), Y.ravel(), Z.ravel()], r, g).reshape(X.shape)
    f = np.pad(f, 1, constant_values=10.0)
    v, fc, _, _ = marching_cubes(f, 0.0, spacing=(MESH_H,) * 3)
    v = v - MESH_H + lo + np.array([p["x"], p["yc"], p["z"]])
    m = trimesh.Trimesh(v, fc, process=True)
    if m.volume < 0:
        m.invert()
    return _to_manifold(m)


THROAT_OVERCUT = 0.5         # the throat prism reaches 0.5 mm into the cheeks and the root; the fairlead solid is
#                              subtracted from it, so its faces (not the prism's) bound the throat: no coplanar faces


def _throat_cut(p: dict, fillet: float = THROAT_FILLET):
    """The throat prism: |x - xs| < throat / 2 (+ overcut), from the floor (- overcut) up past the tip, z within the
    cheeks + 4 mm, bottom corners rounded ``fillet`` (hull of four z cylinders). add_fairleads subtracts the fairlead
    solid from it before cutting, so only the voxel stub in the throat goes."""
    import manifold3d as m3d
    g = p["geom"]
    hz = g.half_z + 4.0
    y0, y1 = p["y_floor"] - THROAT_OVERCUT, p["y_tip"] + 15.0
    xa = p["x"] - g.throat / 2 - THROAT_OVERCUT + fillet
    xb = p["x"] + g.throat / 2 + THROAT_OVERCUT - fillet
    cyl = []
    for xx in (xa, xb):
        for yy in (y0 + fillet, y1):
            cyl.append(m3d.Manifold.cylinder(2 * hz, fillet, fillet, 32, center=True).translate((xx, yy, p["z"])))
    return m3d.Manifold.batch_hull(cyl)


def _pin_hole(p: dict, d: float = HOLE_PRINT_D):
    import manifold3d as m3d
    g = p["geom"]
    L = g.throat + 2 * g.cheek + 1.0
    c = m3d.Manifold.cylinder(L, d / 2, d / 2, 96, center=True)
    # z axis -> x axis, centred on the pin
    return c.transform(np.array([[0.0, 0, 1, p["x"]], [0, 1, 0, p["y_pin"]], [-1, 0, 0, p["z"]]]))


def add_fairleads(man, log=print, stats: dict | None = None):
    """Union every exact fairlead onto the body manifold, then cut each throat and pin hole. ``stats`` (optional dict)
    gets the volume (mm3) each step adds or removes per station, and the body volume the throat cuts take out of
    the voxel body (the clipped stubs inside the envelope)."""
    P = placed()
    v0 = man.volume()
    body = man
    sols = [_fairlead_solid(p) for p in P]
    for fs in sols:
        man = man + fs
    v1 = man.volume()
    per = {}
    for p, fs in zip(P, sols):
        cut = _throat_cut(p) - fs          # clear the voxel stub in the throat, keep the fairlead's own fillets
        per[p["id"]] = {"throat_cut_from_body_mm3": round((body ^ cut).volume(), 1)}
        man = man - cut
    v2 = man.volume()
    for p in P:
        man = man - _pin_hole(p)
    v3 = man.volume()
    if stats is not None:
        stats.update({"body_mm3": v0, "fairleads_added_mm3": v1 - v0, "throats_cut_mm3": v1 - v2,
                      "holes_cut_mm3": v2 - v3, "net_mm3": v3 - v0, "net_g": (v3 - v0) * RHO_G_MM3,
                      "per_station": per})
    if log:
        log(f"  fairleads: +{(v1 - v0) * RHO_G_MM3:.1f} g solids, -{(v1 - v2) * RHO_G_MM3:.1f} g throats, "
            f"-{(v2 - v3) * RHO_G_MM3:.1f} g holes, net {(v3 - v0) * RHO_G_MM3:+.1f} g")
    return man


def voxel_as_printed(solid: np.ndarray) -> tuple:
    """The H1 voxel body (2 mm) with the BL-042 print changes applied inside the envelope: each throat cleared above
    its floor (voxel centres in the throat prism and outside the fairlead's own field), each pin hole emptied, the
    hinge saddle added (hinge fields <= 0, inside the envelope, keep-outs respected). Returns (solid, counts)."""
    from . import bag_attach as BA
    from . import frame_h1 as H1
    c = H1.base()
    dom, cen = c["dom"], c["cen"]
    out = solid.copy()
    cnt = {}
    for p in placed():
        g = p["geom"]
        loc = cen - np.array([p["x"], p["yc"], p["z"]])
        near = np.where((np.abs(loc[:, 0]) < g.throat / 2 + g.cheek + 4) & (np.abs(loc[:, 2]) < g.half_z + 6))[0]
        L = loc[near]
        fld = BA.fairlead_local(L, p["stay_r"], dataclasses.replace(g, hole_d=HOLE_PRINT_D))
        thr = (np.abs(L[:, 0]) < g.throat / 2) & (L[:, 1] > p["stay_r"] + g.floor_proud) & \
              (np.abs(L[:, 2]) < g.half_z + 4.0) & (fld > 0.0)
        hole = (np.hypot(L[:, 1] - (p["stay_r"] + g.hole_proud), L[:, 2]) < HOLE_PRINT_D / 2) & \
               (np.abs(L[:, 0]) <= g.throat / 2 + g.cheek + 0.5)
        rm = near[thr | hole]
        add = near[(fld <= 0.0)] if g.chamfer_w is not None else near[:0]      # saddles (hinge; BL-045 IM / US)
        add = add[~dom.passive_void[add] & ~c["holes"][add]]
        cnt[p["id"]] = {"removed": int(out[rm].sum()), "added": int((~out[add]).sum())}
        out[rm] = False
        out[add] = True
    return out, cnt


# ======================================================================================= STL slice check
def _section(mesh, origin, normal, to2d):
    """Shapely (multi)polygon of the mesh section on a plane; ``to2d`` maps world -> plane coords (4x4)."""
    from shapely.geometry import MultiPolygon, Polygon
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return MultiPolygon()
    T = np.asarray(to2d, float)
    out = None
    for loop in s.discrete:                      # closed loops of a watertight mesh; even-odd rule = nesting
        if len(loop) < 4:
            continue
        q = loop @ T[:3, :3].T + T[:3, 3]
        pg = Polygon(q[:, :2]).buffer(0)
        if pg.is_empty:
            continue
        out = pg if out is None else out.symmetric_difference(pg)
    return out if out is not None else MultiPolygon()


def _zplane(mesh, z):
    T = np.eye(4)
    T[2, 3] = -z
    return _section(mesh, [0, 0, z], [0, 0, 1], T)          # coords (x, y)


def _xplane(mesh, x):
    T = np.array([[0.0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -x], [0, 0, 0, 1]])
    return _section(mesh, [x, 0, 0], [1, 0, 0], T)          # coords (y, z)


def _runs(geom, axis: int, at: float, lo: float, hi: float) -> list:
    """Material intervals (absolute coordinates, sorted) along a line in the section's 2D coords: ``axis`` 0 = a line
    of constant v = ``at`` running in u from lo to hi; 1 = constant u = ``at`` running in v."""
    from shapely.geometry import LineString
    ln = LineString([(lo, at), (hi, at)] if axis == 0 else [(at, lo), (at, hi)])
    it = ln.intersection(geom)
    out = []
    for g in getattr(it, "geoms", [it]):
        if g.is_empty or g.geom_type != "LineString":
            continue
        c = np.asarray(g.coords)[:, axis]
        out.append((float(c.min()), float(c.max())))
    return sorted(out)


def _void_around(runs, t, lo, hi):
    """(start, end) of the empty interval containing t, within [lo, hi]; (t, t) if t is in material."""
    for a, b in runs:
        if a <= t <= b:
            return (t, t)
        if b < t:
            lo = max(lo, b)
        if a > t:
            hi = min(hi, a)
    return lo, hi


def check_station(mesh, p: dict, eye: dict | None = None) -> dict:
    """Measure one fairlead on the mesh against its design. Plane z = zs holds the pin axis: along x = cheek middle
    the hole (vertical void round y_pin) and the front wall; along y lines the throat width; along x lines in the
    throat the floor under the pin. Plane x = cheek middle: the hole ring and the cheek height along the stay."""
    from shapely.geometry import Point, Polygon
    g = p["geom"]
    xs, zs, yp = p["x"], p["z"], p["y_pin"]
    R = HOLE_PRINT_D / 2
    S = _zplane(mesh, zs)
    out = {"id": p["id"], "z": zs, "x": xs}
    ylo, yhi = p["yc"] - 30.0, p["y_tip"] + 15.0
    # floor: top of the material under the pin's underside, at the throat centre (|dx| <= 2) and across the neck
    def floor_at(dx):
        under = [bb for aa, bb in _runs(S, 1, xs + dx, ylo, yhi) if aa < yp - g.pin_d / 2]
        return max(under) if under else ylo
    floor = max(floor_at(dx) for dx in np.linspace(-2.0, 2.0, 5))
    out["floor_y"] = round(floor, 2)
    out["floor_y_design"] = round(p["y_floor"], 2)
    out["gap_under_pin"] = round(yp - g.pin_d / 2 - floor, 2)
    out["gap_under_pin_design"] = round(g.gap_under_pin, 2)
    # throat: the void containing xs, along x lines from the pin's underside to the tip (above the floor fillets)
    ws = []
    for yy in np.linspace(yp - g.pin_d / 2, p["y_tip"] - 0.3, 8):
        a, b = _void_around(_runs(S, 0, yy, xs - 40, xs + 40), xs, xs - 40, xs + 40)
        ws.append(b - a)
    out["throat_min_w"] = round(min(ws), 2)
    out["throat_design"] = g.throat
    out["throat_open"] = bool(min(ws) >= g.throat - TOL["throat"])
    cheeks = {}
    for s in (-1.0, 1.0):
        xm = xs + s * (g.throat / 2 + g.cheek / 2)
        rr = _runs(S, 1, xm, ylo, yhi)
        a, b = _void_around(rr, yp, ylo, yhi)
        front = [(c0, c1) for c0, c1 in rr if c0 >= b - 1e-6]
        wall = (front[0][1] - front[0][0]) if (front and b > a) else 0.0
        yw = yp + R + 0.5 * g.wall_front                       # a line through the front wall
        ck = [(c0, c1) for c0, c1 in _runs(S, 0, yw, xs - 40, xs + 40) if c0 - 1e-6 <= xm <= c1 + 1e-6]
        thick = (ck[0][1] - ck[0][0]) if ck else 0.0
        if ck:      # a cheek merged with body material outboard counts only to its design face
            thick = min(ck[0][1], xs + s * (g.throat / 2 + g.cheek) if s > 0 else 1e9) - \
                max(ck[0][0], xs + s * (g.throat / 2 + g.cheek) if s < 0 else -1e9)
        X = _xplane(mesh, xm)
        ring_d, ring_c = 0.0, None
        for poly in getattr(X, "geoms", [X]):
            for hole in getattr(poly, "interiors", []):
                hp = Polygon(hole)
                if hp.contains(Point(yp, zs)):
                    ring_d = 2 * math.sqrt(hp.area / math.pi)
                    ring_c = (hp.centroid.x, hp.centroid.y)
        hz = [(c0, c1) for c0, c1 in _runs(X, 1, yw, zs - 40, zs + 40) if c0 <= zs <= c1]
        height = (hz[0][1] - hz[0][0]) if hz else 0.0
        cheeks["in" if s * np.sign(xs) < 0 else "out"] = {
            "hole_vertical_mm": round(b - a, 2), "hole_centre_y": round(0.5 * (a + b), 2),
            "hole_ring_d_mm": round(ring_d, 2),
            "hole_ring_centre_err_mm": round(math.hypot(ring_c[0] - yp, ring_c[1] - zs), 2) if ring_c else None,
            "front_wall_mm": round(wall, 2), "cheek_thick_mm": round(thick, 2), "cheek_height_mm": round(height, 2)}
    out["cheeks"] = cheeks
    out["design"] = {"hole_print_d": HOLE_PRINT_D, "wall_front": g.wall_front, "cheek": g.cheek,
                     "cheek_height": 2 * g.half_z, "y_pin": round(yp, 2), "y_tip": round(p["y_tip"], 2)}
    ok = out["throat_open"] and abs(floor - p["y_floor"]) <= TOL["floor"] + 0.5 and \
        out["gap_under_pin"] >= g.gap_under_pin - TOL["floor"]
    for c in cheeks.values():
        ok &= c["hole_vertical_mm"] >= HOLE_PRINT_D - TOL["hole_d"]
        ok &= abs(c["hole_centre_y"] - yp) <= TOL["hole_c"]
        ok &= c["hole_ring_d_mm"] >= HOLE_PRINT_D - TOL["hole_d"]
        ok &= c["hole_ring_centre_err_mm"] is not None and c["hole_ring_centre_err_mm"] <= TOL["hole_c"]
        ok &= c["front_wall_mm"] >= g.wall_front - TOL["wall"]
        ok &= c["cheek_thick_mm"] >= g.cheek - TOL["cheek"]
        ok &= c["cheek_height_mm"] >= 2 * g.half_z - TOL["half_z"]
    out["pass"] = bool(ok)
    if eye:
        # the eye's stay-side ply stack under the pin (stepped: 3 plies in the middle, 2 out to the widest neck), plus
        # the margin, directly under the pin in plane z = zs: no material may lie inside it
        e = eye_polygon(xs, yp - g.pin_d / 2, eye, margin=True).buffer(-EYE_MESH_TOL)
        out["eye_overlap_mm2"] = round(float(S.intersection(e).area), 4)
        out["eye_fits"] = bool(out["eye_overlap_mm2"] < 1e-3)
        out["eye_gap_min_by_step"] = [[hw, t, round(yp - g.pin_d / 2 - max(floor_at(d) for d in np.linspace(-hw, hw, 9)), 2)]
                                      for hw, t in eye["eye_section_steps_mm"]]
        out["pass"] = out["pass"] and out["eye_fits"]
    return out


def eye_polygon(xc: float, y_top: float, eye: dict, margin: bool = True):
    """The eye's stay-side ply stack (stepped by ``eye_section_steps_mm``) hanging under ``y_top`` (the pin's underside),
    thickened by ``eye_margin_mm`` when ``margin``."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    m = eye["eye_margin_mm"] if margin else 0.0
    return unary_union([box(xc - hw, y_top - t - m, xc + hw, y_top) for hw, t in eye["eye_section_steps_mm"]])


def check_stl(path_or_mesh, eye: bool = True, geom_of=station_geom) -> dict:
    """Slice check of every fairlead on an H1 STL (frame coordinates) against ``geom_of`` (default: the BL-042 print
    geometry). Returns {station id: measurements, 'all_pass'}."""
    import trimesh
    from . import bag_attach as BA
    mesh = trimesh.load(path_or_mesh) if isinstance(path_or_mesh, (str, Path)) else path_or_mesh
    res = {}
    for p in placed(geom_of):
        env = None
        if eye and p["name"] == "hinge":
            env = BA.HINGE_EYE_ENVELOPE
        elif eye and p["name"] in BA.IMUS_STATIONS and p["geom"].chamfer_w is not None:   # BL-045 eye stations
            env = BA.imus_eye_envelope(p["name"])
        res[p["id"]] = check_station(mesh, p, env)
    res["all_pass"] = all(v["pass"] for k, v in res.items() if isinstance(v, dict))
    return res


# ======================================================================================= FEA
def fairlead_fea(geom, stay_r: float, loads: dict, h: float = 1.0, stay_ax: float | None = None,
                 bore_r: float | None = None) -> dict:
    """bag_attach.solve_fairlead's model (stay stub + fairlead_local, bearing on the hole half facing the force,
    fixed end caps, PAHT layer FI, FI99 over the yoke away from the caps) with ``geom`` and several 3D loads
    (name -> [fx, fy, fz] N, x = pin axis): the x part pushes the inner face of the cheek it pulls toward
    (im3_body_simloads.eye_fea's rule). One factorisation. Returns per load FI99, FI max, SF = 1 / FI99.
    ``stay_ax`` (optional): the stay as an ellipse, half-width ``stay_ax`` across the pin axis and ``stay_r`` toward the
    bag (the H1 stay at z 60 is narrower than the stay_radius circle); None = the circle (solve_fairlead)."""
    from . import bag_attach as BA
    from .fem import Grid, ke_h8
    from .frame_topopt import NU, ReducedSystem, element_stress, layer_failure_index
    pa = BA._paht()
    y_hole = stay_r + geom.hole_proud
    xext = max(20.0, geom.throat / 2 + geom.cheek + 3.0)
    zext = max(22.0, geom.half_z + 8.0)
    lo = np.array([-xext, -(stay_r + 4.0), -zext])
    hi = np.array([xext, stay_r + geom.tip_proud + 4.0, zext])
    n = np.maximum(np.round((hi - lo) / h).astype(int), 6)
    g = Grid(tuple(int(v) for v in n), h, x0=lo)
    c = g.elem_centers()
    ax_ = stay_ax or stay_r
    stay = (np.hypot(c[:, 0] / ax_, c[:, 1] / stay_r) <= 1.0) & (np.abs(c[:, 2]) <= zext - 1.0)
    if bore_r:          # BL-045: the crown-leg bore of the sleeve stations (IM1-IM3) is empty
        stay &= np.hypot(c[:, 0], c[:, 1]) >= bore_r
    yoke = BA.fairlead_local(c, stay_r, geom) <= 0.0
    solid = stay | yoke
    nc = g.node_coords()
    radial = np.c_[nc[:, 1] - y_hole, nc[:, 2]]
    rr = np.linalg.norm(radial, axis=1)
    band = (rr > geom.hole_d / 2.0 - 0.35 * h) & (rr < geom.hole_d / 2.0 + 0.9 * h)
    band &= np.abs(nc[:, 0]) >= geom.throat / 2.0 - 0.3
    band &= np.abs(nc[:, 0]) <= geom.throat / 2.0 + geom.cheek + 0.6 * h
    end = (np.abs(nc[:, 2]) >= zext - 2.5) & (np.hypot(nc[:, 0] / (ax_ + h), nc[:, 1] / (stay_r + h)) <= 1.0)
    fixed = np.zeros(g.ndof, bool)
    ids = np.where(end)[0]
    for d in range(3):
        fixed[3 * ids + d] = True
    in_solid = np.unique(g.enodes[solid])
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
            x_in = side * geom.throat / 2.0
            rf = np.hypot(nc[:, 1] - y_hole, nc[:, 2])
            face = np.where((np.abs(nc[:, 0] - x_in) <= 0.6 * h) & (rf >= geom.hole_d / 2.0) & (rf <= geom.hole_d))[0]
            face = face[np.isin(face, in_solid)]
            F[3 * face, k] += f3[0] / max(face.size, 1)
    F[fixed] = 0.0
    KE = ke_h8(h, 1.0, NU)
    rs = ReducedSystem(g, solid, fixed, KE)
    U = rs.solve(rs.assemble(np.full(rs.ae.size, 1.0)), F) / pa["E"]
    out, use, cc = {}, None, None
    for k, nm in enumerate(names):
        eidx, S = element_stress(g, U[:, k], solid, pa["E"])
        fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
        if use is None:
            cc = c[eidx]
            use = (BA.fairlead_local(cc, stay_r, geom) <= h) & (np.abs(cc[:, 2]) < zext - 6.0)
        fu = fi[use]
        fi99 = float(np.percentile(fu, 99))
        out[nm] = {"force_n": float(np.linalg.norm(loads[nm])), "fi99": fi99, "fi_max": float(fu.max()),
                   "sf": 1.0 / max(fi99, 1e-9), "peak_xyz": [round(float(v), 1) for v in cc[use][int(np.argmax(fu))]],
                   "applied_n": float(np.linalg.norm([F[0::3, k].sum(), F[1::3, k].sum(), F[2::3, k].sum()]))}
    added = float((yoke & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    return {"h": h, "stay_r": stay_r, "geom": dataclasses.asdict(geom), "added_g": added, "n_elem": int(solid.sum()),
            "loads": out}


def pin_bending(force_n: float, throat: float, cheek: float, pin_d: float, g_times_req: float,
                surface_k: float = 0.9) -> dict:
    """5 mm 7075-T6 pin across the throat: the eye load spread over the throat width, reacted at the cheek centres
    (simply supported; clevis-pin practice, conservative against the sleeve's inner-edge peaking).
    M = F (2 L - b) / 8, L = throat + cheek, b = throat. Yield on the S-basis; fatigue at 1.6 g (0 -> max, R 0) on a
    Goodman line from the record's rotating-beam limit x ``surface_k`` (ASSUMPTION PIN-KS, machined) and the UTS."""
    from huntkit.materials import load
    al = load("alu_7075_t6")
    sy = float(al.require("yield_strength_sbasis_mpa"))
    su = float(al.require("ultimate_strength_mpa"))
    se = float(al.require("fatigue_limit_mpa")) * surface_k
    L, b = throat + cheek, throat
    Z = math.pi * pin_d ** 3 / 32.0
    M = force_n * (2 * L - b) / 8.0
    s = M / Z
    s_walk = s * G_WALK / g_times_req
    smax_allow = 2.0 / (1.0 / se + 1.0 / su)        # R = 0: sa = sm = smax / 2 on the Goodman line
    return {"M_nmm": M, "sigma_mpa": s, "sf_yield": sy / s, "sigma_walk_mpa": s_walk,
            "goodman_smax_r0_mpa": smax_allow, "sf_fatigue": smax_allow / s_walk}


def hinge_loads() -> dict:
    """Hinge-pin loads: rev C governing factored vector (rev_c_verification_results.json, beam model) and the CORRIE F
    rev 1 sim hinge-pin vectors at 1 g (im3_body_simloads.SIMFORCES1, meat and fill, both sides; R side mirrored to
    the frame's +x station so the lateral pull is inboard = toward -x)."""
    rc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["hinge"]
    out = {"revC": {"vec": [0.0, rc["fy"], rc["fz"]], "g_times_req": rc["g_times_req"], "case": rc["case"]}}
    p = REPO / "outputs" / "im3_body_simloads" / "sim_frame_forces_rev1.json"
    sims = {}
    if p.exists():
        d = json.loads(p.read_text())
        for run, v in d.items():
            for side in "RL":
                f = np.asarray(v["forces"][f"hinge_{side}"]["f"], float)
                if side == "L":
                    f[0] = -f[0]            # mirror onto the +x (R) station
                sims[f"{run}|{side}"] = f.tolist()
    out["sim_1g"] = sims
    return out


def fea_study(h: float = 1.0, log=print) -> dict:
    """Legacy vs BL-042 hinge fairlead: cheek FI99 at the rev C factored vector, and at every sim vector (strength at
    x 3.0, fatigue at 1.6 g, creep at 1 g) + the lateral push; pin bending; IM3 28 mm cheek re-run at rev C."""
    from . import bag_attach as BA
    from .frame_branch import stay_radius
    pa = BA._paht()
    L = hinge_loads()
    r60 = float(stay_radius(60.0, BA.SCALE))
    loads = {"revC": L["revC"]["vec"]}
    for k, v in L["sim_1g"].items():
        loads[k] = (1000.0 * np.asarray(v) / np.linalg.norm(v)).tolist()       # unit-free 1000 N directions
    res = {"loads": L, "h": h, "stay_ax_sensitivity_mm": STAY_AX_60}
    for tag, geom, ax in (("legacy", BA.legacy_geom(), None), ("bl042", BA.HINGE_GEOM, None),
                          ("legacy_ellipse", BA.legacy_geom(), STAY_AX_60), ("bl042_ellipse", BA.HINGE_GEOM, STAY_AX_60)):
        OUT.mkdir(parents=True, exist_ok=True)
        cp = OUT / f"fea_hinge_{tag}_{h:g}.json"
        if cp.exists() and json.loads(cp.read_text())["geom"] == dataclasses.asdict(geom):
            r = json.loads(cp.read_text())
        else:
            r = fairlead_fea(geom, r60, loads, h=h, stay_ax=ax)
            cp.write_text(json.dumps(r))
        rc = r["loads"]["revC"]
        row = {"added_g": r["added_g"], "revC_force_n": rc["force_n"], "revC_sf": rc["sf"],
               "revC_fatigue": BA._fatigue_sf(rc["fi99"], L["revC"]["g_times_req"], pa["fat"]),
               "revC_creep": BA._creep_sf(rc["fi99"], L["revC"]["g_times_req"], pa["rupture"])}
        worst = None
        for k, v in L["sim_1g"].items():
            mag = float(np.linalg.norm(v))
            fpn = r["loads"][k]["fi99"] / 1000.0
            s = {"f1g_n": mag, "strength": 1.0 / (fpn * FACTOR * mag), "fatigue": pa["fat"] / (fpn * G_WALK * mag),
                 "creep": pa["rupture"] / (fpn * mag)}
            if worst is None or s["fatigue"] < worst[1]["fatigue"]:
                worst = (k, s)
        row["sim_worst"] = {"run": worst[0], **worst[1]} if worst else None
        g = geom
        row["pin_revC"] = pin_bending(rc["force_n"], g.throat, g.cheek, g.pin_d, L["revC"]["g_times_req"])
        if L["sim_1g"]:
            fmax = max(float(np.linalg.norm(v)) for v in L["sim_1g"].values())
            row["pin_sim"] = pin_bending(FACTOR * fmax, g.throat, g.cheek, g.pin_d, FACTOR)
        res[tag] = row
        if log:
            log(f"  hinge {tag}: revC SF {row['revC_sf']:.2f} fat {row['revC_fatigue']:.2f}; sim worst "
                f"{row['sim_worst']}")
    # IM3 28 mm cheek at its rev C governing force (rev_c_verification gov_c.im3), geometry unchanged by BL-042
    rc3 = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["im3"]
    cp = OUT / f"fea_im3_{h:g}.json"
    g3 = station_geom("im3")
    if cp.exists() and json.loads(cp.read_text())["geom"] == dataclasses.asdict(g3) and \
            json.loads(cp.read_text()).get("bore_r") == BA.SLEEVE_BORE_R_REAM:        # BL-045: cache keyed on geometry
        r3 = json.loads(cp.read_text())
    else:
        r3 = fairlead_fea(g3, float(stay_radius(520.0, BA.SCALE)), {"revC": [rc3["fx"], rc3["fy"], rc3["fz"]]}, h=h,
                          bore_r=BA.SLEEVE_BORE_R_REAM)
        r3["bore_r"] = BA.SLEEVE_BORE_R_REAM
        cp.write_text(json.dumps(r3))
    v3 = r3["loads"]["revC"]
    res["im3_28"] = {"force_n": v3["force_n"], "sf": v3["sf"],
                     "fatigue": BA._fatigue_sf(v3["fi99"], rc3["g_times_req"], pa["fat"])}
    return res


# ======================================================================================= test pieces
PIECES = {"hinge": ("hefit_hinge_fairlead_R", 80.0, "HE-FIT: z 60 R hinge fairlead, 80 mm stay segment"),
          "im3": ("im3ec_cheek_R", 120.0, "IM3-EC: z 520 R IM3 eye, 28 mm cheek, 120 mm stay segment")}


def export_pieces(mesh=None, log=print) -> dict:
    """Standalone test pieces cut from the fixed print mesh (frame coordinates kept; one closed shell each):
    the R hinge fairlead (80 mm of stay) and the R IM3 eye (120 mm of stay). Laid flat like the frame halves."""
    import trimesh
    import manifold3d as m3d
    from . import frame_h1 as H1
    from .h1_buckling import clean_shell
    from .surface import _from_manifold, _to_manifold
    mesh = mesh if mesh is not None else trimesh.load(PRINT_DIR / "h1_assembled.stl")
    man = _to_manifold(mesh)
    PIECES_DIR.mkdir(parents=True, exist_ok=True)
    info = {}
    for p in placed():
        if p["name"] not in PIECES or p["side"] != "R":
            continue
        nm, L, what = PIECES[p["name"]]
        g = p["geom"]
        hx = g.throat / 2 + g.cheek + 6.0
        b = m3d.Manifold.cube((2 * hx, 80.0, L), center=True).translate((p["x"], p["yc"], p["z"]))
        piece, dropped = clean_shell(_from_manifold((man ^ b).simplify(0.04)))
        flat = H1.lay_flat(piece)
        piece.export(PIECES_DIR / f"{nm}_frame_coords.stl")
        flat.export(PIECES_DIR / f"{nm}.stl")
        flat.export(PIECES_DIR / f"{nm}.3mf")
        for fn in (f"{nm}_frame_coords.stl", f"{nm}.stl"):
            if not trimesh.load(PIECES_DIR / fn).is_watertight:
                raise RuntimeError(f"{fn}: not watertight after an STL round trip")
        info[p["name"]] = {"file": f"print/frame_h1/test_pieces/{nm}.stl", "what": what,
                           "g": round(piece.volume * RHO_G_MM3, 1), "watertight": bool(piece.is_watertight),
                           "shells": len(piece.split(only_watertight=False)), "dropped": dropped,
                           "extents_mm": [round(v, 1) for v in flat.extents]}
        if log:
            log(f"  piece {nm}: {info[p['name']]}")
    return info


# ======================================================================================= figures
def plot_slices(mesh, path: Path, title: str, stations=("hinge", "us1", "us2", "im1", "im2", "im3"),
                side: str = "R", geom_of=station_geom) -> str:
    """Per station: plane z = zs (pin axis, x-y) and plane x = outboard cheek middle (y-z); design outline dashed,
    pin and (hinge) the 3-ply eye envelope drawn."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    from . import bag_attach as BA
    P = {p["name"]: p for p in placed(geom_of) if p["side"] == side}
    n = len(stations)
    fig, axs = plt.subplots(2, n, figsize=(2.6 * n, 6.4), dpi=110)
    ink, mat = "#1d1d1f", "#8a8f98"
    for j, nm in enumerate(stations):
        p = P[nm]
        g = p["geom"]
        S = _zplane(mesh, p["z"])
        xm = p["x"] + (g.throat / 2 + g.cheek / 2)
        X = _xplane(mesh, xm)
        for ax, G, (cx, cy), lab in ((axs[0, j], S, (p["x"], p["y_pin"]), "z"), (axs[1, j], X, (p["y_pin"], p["z"]), "x")):
            for poly in getattr(G, "geoms", [G]):
                if poly.is_empty:
                    continue
                xx, yy = poly.exterior.xy
                ax.fill(xx, yy, color=mat, lw=0.4, ec=ink)
                for hole in poly.interiors:
                    hx_, hy_ = hole.xy
                    ax.fill(hx_, hy_, color="white", lw=0.4, ec=ink)
            ax.set_aspect("equal")
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.25, lw=0.4)
        a0 = axs[0, j]
        # design outline in the z plane: cheeks, floor, pin
        for s in (-1, 1):
            x0 = p["x"] + s * g.throat / 2
            x1 = p["x"] + s * (g.throat / 2 + g.cheek)
            a0.add_patch(Rectangle((min(x0, x1), p["y_floor"]), abs(x1 - x0), p["y_tip"] - p["y_floor"], fill=False,
                                   ls="--", lw=0.8, ec="#c0392b"))
        a0.plot([p["x"] - g.throat / 2, p["x"] + g.throat / 2], [p["y_floor"]] * 2, ls="--", lw=0.8, c="#c0392b")
        a0.add_patch(Rectangle((p["x"] - (g.throat / 2 + g.cheek), p["y_pin"] - g.pin_d / 2), g.throat + 2 * g.cheek,
                               g.pin_d, color="#2e86de", alpha=0.8, lw=0))
        if nm == "hinge":
            ep = eye_polygon(p["x"], p["y_pin"] - g.pin_d / 2, BA.HINGE_EYE_ENVELOPE, margin=False)
            a0.fill(*ep.exterior.xy, color="#f39c12", alpha=0.6, lw=0)
        a0.set_xlim(p["x"] - 24, p["x"] + 24)
        a0.set_ylim(p["yc"] - 6, p["y_tip"] + 5)
        a0.axhline(15.46, c="#7f8c8d", lw=0.6, ls=":")
        a0.set_title(f"{nm} z {p['z']:.0f}: plane z (pin axis)", fontsize=7)
        a0.set_xlabel("x mm", fontsize=6)
        a0.set_ylabel("y mm (bag +)", fontsize=6)
        a1 = axs[1, j]
        a1.add_patch(Circle((p["y_pin"], p["z"]), g.pin_d / 2, color="#2e86de", alpha=0.8, lw=0))
        a1.add_patch(Circle((p["y_pin"], p["z"]), HOLE_PRINT_D / 2, fill=False, ls="--", lw=0.8, ec="#c0392b"))
        a1.add_patch(Rectangle((p["y_floor"] - 2.0, p["z"] - g.half_z), p["y_tip"] - p["y_floor"] + 2.0, 2 * g.half_z,
                               fill=False, ls="--", lw=0.8, ec="#c0392b"))
        a1.set_xlim(p["yc"] - 6, p["y_tip"] + 5)
        a1.set_ylim(p["z"] - g.half_z - 10, p["z"] + g.half_z + 10)
        a1.set_title(f"plane x {xm:.1f} (outboard cheek)", fontsize=7)
        a1.set_xlabel("y mm (bag +)", fontsize=6)
        a1.set_ylabel("z mm", fontsize=6)
    fig.suptitle(title, fontsize=9, x=0.01, ha="left")
    fig.text(0.01, 0.005, "grey = STL section; red dashed = design (cheeks, floor, hole, cheek height); blue = 5 mm pin; "
             "orange = the eye's ply stack under the pin (hinge); dotted = old clip line y 15.46",
             fontsize=6.5, ha="left")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


def plot_hinge_detail(before, after, path: Path) -> str:
    """Hinge (z 60, R) close-up, before / after, plane z through the pin axis, with the eye envelope."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    from . import bag_attach as BA
    p_new = [p for p in placed() if p["id"] == "hinge_R"][0]
    p_old = [p for p in placed(lambda n: BA.legacy_geom()) if p["id"] == "hinge_R"][0]
    fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.6), dpi=130)
    for ax, mesh, p, lab in ((axs[0], before, p_old, "BEFORE (H1 print files at 7dabc6c)"), (axs[1], after, p_new, "AFTER (BL-042)")):
        g = p["geom"]
        S = _zplane(mesh, p["z"])
        for poly in getattr(S, "geoms", [S]):
            if poly.is_empty:
                continue
            xx, yy = poly.exterior.xy
            ax.fill(xx, yy, color="#8a8f98", lw=0.5, ec="#1d1d1f")
            for hole in poly.interiors:
                hx_, hy_ = hole.xy
                ax.fill(hx_, hy_, color="white", lw=0.5, ec="#1d1d1f")
        ax.add_patch(Rectangle((p["x"] - (g.throat / 2 + g.cheek), p["y_pin"] - g.pin_d / 2), g.throat + 2 * g.cheek,
                               g.pin_d, color="#2e86de", alpha=0.85, lw=0))
        e = BA.HINGE_EYE_ENVELOPE
        ep = eye_polygon(p["x"], p["y_pin"] - g.pin_d / 2, e, margin=False)
        ax.fill(*ep.exterior.xy, color="#f39c12", alpha=0.6, lw=0)
        em = eye_polygon(p["x"], p["y_pin"] - g.pin_d / 2, e, margin=True)
        ax.plot(*em.exterior.xy, color="#d35400", lw=0.8, ls="--")
        ax.axhline(15.46, c="#7f8c8d", lw=0.7, ls=":")
        ax.set_xlim(p["x"] - 22, p["x"] + 22)
        ax.set_ylim(p["yc"] + 2, p["yc"] + p["stay_r"] + 21)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25, lw=0.4)
        ax.set_title(f"{lab}\nthroat design {g.throat:g} mm, gap under pin design {g.gap_under_pin:.1f} mm", fontsize=8)
        ax.set_xlabel("x mm (pin axis)", fontsize=7)
        ax.set_ylabel("y mm (toward the bag)", fontsize=7)
        ax.tick_params(labelsize=7)
    fig.suptitle("Hinge fairlead z 60 R, STL section through the pin axis. Blue: 5 mm pin.\nOrange: the eye's ply "
                 "stack under the pin (3 plies, 4.5 mm, in the middle; 2 plies out to the 19 mm max neck). "
                 "Dashed: + 1 mm margin. Dotted: old clip line y 15.46", fontsize=8, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


# ======================================================================================= run / report
BEFORE_STL = OUT / "h1_assembled_before_bl042.stl"     # git HEAD 7dabc6c copy of the released-candidate STL
BODY_CHECK = "m1_u2.5_im3"                               # h1_buckling.full_check name of the release body
BODY_CHECK_BL042 = "m1_u2.5_im3_bl045"     # BL-045: as printed with the IM / US eye saddles too


def before_stl() -> Path:
    """The pre-BL-042 H1 STL (git show 7dabc6c, the commit that filed BL-042), cached in OUT."""
    import subprocess
    if not BEFORE_STL.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        blob = subprocess.run(["git", "-C", str(REPO), "show",
                               "7dabc6c:designs/pack_5200/print/frame_h1/h1_assembled.stl"],
                              check=True, capture_output=True).stdout
        BEFORE_STL.write_bytes(blob)
    return BEFORE_STL


def legacy_geom_of(name: str):
    """What the pre-BL-042 files claimed: 2026-11-01 fairleads, IM3 28 mm."""
    from . import bag_attach as BA
    return station_geom(name) if name == "im3" else BA.legacy_geom()


def body_recheck(log=print) -> dict:
    """The rev C body checks (h1_buckling.full_check, 4 bases) on the voxel body as printed after BL-042
    (voxel_as_printed: throat stubs cleared, pin holes emptied, hinge saddle added inside the envelope)."""
    from . import h1_buckling as B
    solid = B.final_solid(*B.CHOSEN)
    s2, cnt = voxel_as_printed(solid)
    new = B.full_check(BODY_CHECK_BL042, s2, log=log)
    old = B.full_check(BODY_CHECK, solid, log=log)
    rows = {}
    for b in B.BASES_CHECK:
        rows[b] = {"before": {**old[b]["min"], "buckling": old[b]["buckling_min"], "joint_s": old[b]["joint_strength"],
                              "joint_f": old[b]["joint_fatigue"]},
                   "after": {**new[b]["min"], "buckling": new[b]["buckling_min"], "joint_s": new[b]["joint_strength"],
                             "joint_f": new[b]["joint_fatigue"]}}
    return {"voxels": cnt, "raster_g_before": old["raster_g"], "raster_g_after": new["raster_g"], "bases": rows}


def compute(log=print) -> dict:
    import trimesh
    from . import bag_attach as BA
    info = json.loads((REPO / "outputs" / "h1_buckling" / "print_info.json").read_text())
    after = trimesh.load(PRINT_DIR / "h1_assembled.stl")
    before = trimesh.load(before_stl())
    chk_after = check_stl(after)
    chk_before = check_stl(before, geom_of=legacy_geom_of)
    halves = {}
    for nm in ("lower", "upper"):
        m = trimesh.load(PRINT_DIR / f"h1_{nm}_flat.stl")
        halves[nm] = {"g": round(m.volume * RHO_G_MM3, 1), "watertight": bool(m.is_watertight),
                      "shells": len(m.split(only_watertight=False)), "extents_mm": [round(v, 1) for v in m.extents]}
    pieces = export_pieces(after, log=log)
    for nm in pieces:
        fn = PIECES_DIR / f"{PIECES[nm][0]}_frame_coords.stl"
        pm = trimesh.load(fn)
        p = [q for q in placed() if q["name"] == nm and q["side"] == "R"][0]
        pieces[nm]["slice_check"] = check_station(pm, p, BA.HINGE_EYE_ENVELOPE if nm == "hinge" else None)
    fea = fea_study(log=log)
    body = body_recheck(log=log)
    fl = info["fairleads_bl042"]
    res = {"date": "2026-11-13", "ticket": "BL-042",
           "hinge_geom": dataclasses.asdict(BA.HINGE_GEOM), "legacy_geom": dataclasses.asdict(BA.legacy_geom()),
           "hinge_eye_envelope": BA.HINGE_EYE_ENVELOPE,
           "check_before": chk_before, "check_after": chk_after,
           "assembled": {"g_before": round(before.volume * RHO_G_MM3, 1), "g_after": round(after.volume * RHO_G_MM3, 1),
                         "watertight": bool(after.is_watertight), "shells": len(after.split(only_watertight=False)),
                         "bounds_y_max_before": round(float(before.bounds[1][1]), 2),
                         "bounds_y_max_after": round(float(after.bounds[1][1]), 2)},
           "halves": halves, "export_info": info,
           "mass": {"net_g": round(fl["net_g"], 2), "solids_g": round(fl["fairleads_added_mm3"] * RHO_G_MM3, 2),
                    "throats_g": round(-fl["throats_cut_mm3"] * RHO_G_MM3, 2),
                    "holes_g": round(-fl["holes_cut_mm3"] * RHO_G_MM3, 2),
                    "basis": "print_mesh volume before / after h1_fairleads.add_fairleads x 1.06 g/cm3 (pre-simplify)"},
           "pieces": pieces, "fea": fea, "body": body}
    RESULTS.write_text(json.dumps(res, indent=1, default=_np))
    return res


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def figures(res: dict) -> list:
    import trimesh
    SCREENS.mkdir(parents=True, exist_ok=True)
    before = trimesh.load(before_stl())
    after = trimesh.load(PRINT_DIR / "h1_assembled.stl")
    shots = [plot_hinge_detail(before, after, SCREENS / f"{SHOT}1.png"),
             plot_slices(before, SCREENS / f"{SHOT}2.png",
                         "BEFORE: H1 print STL (7dabc6c) sliced at every fairlead, R side: clipped at y 15.46, no holes, "
                         "solid throats", geom_of=legacy_geom_of),
             plot_slices(after, SCREENS / f"{SHOT}3.png",
                         "AFTER (BL-042): every fairlead complete; hinge saddle, 20 mm throat, 5.5 mm under the pin; "
                         "IM3 28 mm cheek")]
    return shots


def _in(mm: float) -> str:
    return f"{mm / 25.4:.2f} in"


def _oz(g: float) -> str:
    return f"{g / 28.3495:.2f} oz"


def write_md(res: dict, shots: list) -> str:
    from . import bag_attach as BA
    hg, lg, e = res["hinge_geom"], res["legacy_geom"], res["hinge_eye_envelope"]
    fe, cb, ca = res["fea"], res["check_before"], res["check_after"]
    L = []
    a = L.append
    a("# H1 fairleads: complete on the print files, and a hinge the eye can pass (BL-042)\n")
    a("Date 2026-11-13. Ticket `docs/backlog/BL-042-h1-fairleads.md`, findings Z-1 / Z-2 of "
      "`review_20261113_rev3_third.md`. Code `huntkit/gendesign/h1_fairleads.py` (`python -m huntkit.gendesign."
      "h1_fairleads`), geometry `huntkit/gendesign/bag_attach.py` (`HINGE_GEOM`, `HINGE_EYE_ENVELOPE`), export "
      "`frame_h1.print_mesh` / `h1_buckling.export_print`, tests `tests/test_h1_fairleads.py`. Results "
      "`h1_fairleads.json`.\n")
    a("## Summary\n")
    a(f"- **Z-2 fixed and checked on the STL itself.** Before: every one of the 12 fairleads in "
      f"`print/frame_h1/h1_assembled.stl` was cut off at y {res['assembled']['bounds_y_max_before']:.2f} (the voxel "
      f"envelope): no front wall, no pin hole, a solid throat at the hinge, IM1 and IM2. After: all 12 are whole "
      f"(bounds y max {res['assembled']['bounds_y_max_after']:.1f} mm). Slicing the exported STL through every pin "
      f"axis and every cheek: before **{sum(1 for k, v in cb.items() if isinstance(v, dict) and v['pass'])} / 12 pass**, "
      f"after **{sum(1 for k, v in ca.items() if isinstance(v, dict) and v['pass'])} / 12 pass**.")
    h = ca["hinge_R"]
    a(f"- **Z-1 fixed.** Hinge fairlead (z 60): gap under the pin {lg['hole_proud'] - lg['pin_d'] / 2 - lg['floor_proud']:.1f}"
      f" -> **{h['gap_under_pin']:.2f} mm** measured on the STL (3-ply eye 4.5 mm + 1.0 mm margin; "
      f"{_in(h['gap_under_pin'])}); throat {lg['throat']:g} -> **{h['throat_min_w']:.1f} mm** measured (18 mm neck, "
      f"19 mm worst case, 1.0 mm clear; {_in(h['throat_min_w'])}). The eye's ply stack plus margin overlaps the "
      f"section by {h['eye_overlap_mm2']:.3f} mm2 (before: {cb['hinge_R']['eye_overlap_mm2']:.1f} mm2).")
    b, n = fe["legacy"], fe["bl042"]
    a(f"- **Cheek strength kept and raised.** Rev C governing hinge load ({b['revC_force_n']:.0f} N factored, "
      f"{fe['loads']['revC']['case']}): 1/FI99 {b['revC_sf']:.2f} -> **{n['revC_sf']:.2f}**, fatigue "
      f"{b['revC_fatigue']:.2f} -> **{n['revC_fatigue']:.2f}**. On the CORRIE F sim hinge-pin vectors with their "
      f"sideways pull (never checked before): fatigue {b['sim_worst']['fatigue']:.2f} (fails) -> "
      f"**{n['sim_worst']['fatigue']:.2f}**, strength {b['sim_worst']['strength']:.2f} -> "
      f"**{n['sim_worst']['strength']:.2f}**. The fix that does it is a saddle: the hinge fairlead's root and cheeks "
      f"now wrap the stay down to its centreline (45 deg underside outboard of the stay).")
    m = res["mass"]
    a(f"- **Mass.** The completed fairleads add **{m['net_g']:+.1f} g ({_oz(m['net_g'])})** to the printed body "
      f"(mesh {res['assembled']['g_before']:.1f} -> {res['assembled']['g_after']:.1f} g). The 2 mm raster never held "
      f"them above y 16, so this mass was never booked (ledger C1 removed the fairleads as 'inside the raster'). "
      f"Booked now as ledger row **H1F** (H1 configs only).")
    a(f"- **Body checks re-run** on the voxel body as printed (throat stubs cleared, holes emptied, hinge saddle "
      f"added): every rev C basis moves by at most "
      f"{max(abs(v['after'][k] - v['before'][k]) for v in res['body']['bases'].values() for k in ('strength', 'fatigue', 'creep', 'buckling')):.3f}"
      f" (section 5).")
    a(f"- **Test pieces** for HE-FIT and IM3-EC are cut from the fixed mesh (`print/frame_h1/test_pieces/`), and the "
      f"test kit points at them.\n")

    a("## 1. What was wrong (Z-2), measured on the old STL\n")
    a("`frame_topopt.build_domain` voids everything above `env.y_hi(z)` (grid top `Y_HI_GRID` 16 mm). The fairleads "
      "stand 14-17 mm proud of the stay, so most of each one is outside the voxel model. `frame_h1.assemble` restores "
      "them as hard points and then re-applies the void; `print_mesh` meshed what was left and never added them back. "
      "`frame_h1.keepouts` counted fairlead voxels only inside the envelope, so it read 1.000.\n")
    a("Slice check of the old file (plane z through each pin axis, plane x through each cheek), right side, against "
      "the geometry that file claimed (2026-11-01 fairleads, 28 mm IM3 cheek):\n")
    a("| station | floor y / design | gap under pin mm | throat clear mm | hole (vertical) mm | front wall mm | cheek height mm | pass |")
    a("|---|---|---:|---:|---:|---:|---:|---|")
    for k in ("hinge_R", "us1_R", "us2_R", "im1_R", "im2_R", "im3_R"):
        v = cb[k]
        c = v["cheeks"]["out"]
        a(f"| {k} z {v['z']:.0f} | {v['floor_y']:.2f} / {v['floor_y_design']:.2f} | {v['gap_under_pin']:.2f} | "
          f"{v['throat_min_w']:.1f} | {c['hole_vertical_mm']:.1f} (open to the bag) | {c['front_wall_mm']:.1f} | "
          f"{c['cheek_height_mm']:.1f} | {'yes' if v['pass'] else '**no**'} |")
    a("\nA hole 'vertical' of 25-28 mm means no material above the pin at all: the hole is an open slot. A throat of "
      "0 mm is a solid throat. The left side reads the same (`h1_fairleads.json` `check_before`).\n")

    a("## 2. The fix in the export\n")
    a("`frame_h1.print_mesh` now calls `h1_fairleads.add_fairleads` after the body's exact features:\n")
    a(f"1. each fairlead is meshed from `bag_attach.fairlead_local` with its station geometry (0.25 mm marching "
      f"cubes, off-grid so no face sits on a node) and unioned onto the smooth body;")
    a("2. each throat is cleared: a prism from the floor up past the tip, minus the fairlead itself, so the voxel "
      "stub goes and the fairlead's own fillets stay;")
    a(f"3. each pin hole is cut exactly, Ø{HOLE_PRINT_D:g} printed (reamed to {BA.HOLE_D:g} for the UHMWPE sleeve, "
      "ASSUMPTION HOLE_REAM as the IM3 eyes and the bores).")
    a("\n`h1_buckling.export_print` now also reloads every written STL (as a slicer does: vertices merged) and refuses "
      "a file that is not closed. The IM3-only hole cut there is gone (print_mesh cuts all 12).\n")
    a("| file | g | lb | watertight | shells | footprint mm |")
    a("|---|---:|---:|---|---:|---|")
    a(f"| h1_assembled.stl | {res['assembled']['g_after']:.1f} | {res['assembled']['g_after'] / 453.59:.2f} | "
      f"{res['assembled']['watertight']} | {res['assembled']['shells']} | |")
    for nm, v in res["halves"].items():
        a(f"| h1_{nm}_flat.stl | {v['g']:.1f} | {v['g'] / 453.59:.2f} | {v['watertight']} | {v['shells']} | "
          f"{' x '.join(f'{x:.0f}' for x in v['extents_mm'])} |")
    a("")
    a("Slice check of the new file (design = the BL-042 geometry), right side; the left side passes the same:\n")
    a("| station | floor y / design | gap under pin mm (design) | throat mm (design) | hole ring Ø mm | centre err mm | front wall mm | cheek mm | cheek height mm | pass |")
    a("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for k in ("hinge_R", "us1_R", "us2_R", "im1_R", "im2_R", "im3_R"):
        v = ca[k]
        c = v["cheeks"]["out"]
        a(f"| {k} z {v['z']:.0f} | {v['floor_y']:.2f} / {v['floor_y_design']:.2f} | {v['gap_under_pin']:.2f} "
          f"({v['gap_under_pin_design']:.2f}) | {v['throat_min_w']:.1f} ({v['throat_design']:g}) | "
          f"{c['hole_ring_d_mm']:.2f} | {c['hole_ring_centre_err_mm']:.2f} | {c['front_wall_mm']:.2f} | "
          f"{c['cheek_thick_mm']:.2f} | {c['cheek_height_mm']:.1f} | {'yes' if v['pass'] else '**no**'} |")
    a(f"\nThe IM3 cheeks are **28 mm** tall (BL-021) on both sides. Hinge eye check by step "
      f"(half-width mm, plies' thickness mm, clear gap mm): {ca['hinge_R']['eye_gap_min_by_step']}.\n")
    a("The check (`check_stl`, tolerances `TOL`): hole ring Ø >= 7.0 - 0.15 and centred within 0.3 in plane x; the "
      "vertical void at the pin >= 6.85 and centred; front wall >= design - 0.3; cheek thickness >= design - 0.3; "
      "cheek height >= design - 0.5; throat clear >= design - 0.2 from the pin's underside to the tip; floor within "
      "0.8 of design and gap >= design - 0.3 at the throat centre; for the hinge, no material inside the eye's ply "
      "stack + 1 mm margin. A test clips a correct body at y 15.46 and asserts the check fails.\n")
    a("`frame_h1.keepouts` no longer reports 'fairleads present'. It reports the voxel stub fraction under its real "
      "name and runs `check_stl` on the print STL.\n")

    a("## 3. Hinge fairlead geometry (Z-1)\n")
    a("The eye is the neck: op 4.05 folds each long edge of the 38 mm webbing 10 mm in, so under the pin the eye "
      "is 3 plies over the middle 2 mm and 2 plies out to the 18 mm edge (HE-T 1.5 mm a ply). The stay-side ply "
      "passes between the pin and the throat floor.\n")
    a("| | 2026-11-01 | BL-042 hinge |")
    a("|---|---:|---:|")
    for k, lab in (("throat", "throat mm"), ("cheek", "cheek thickness mm"), ("half_z", "cheek half-height mm"),
                   ("hole_proud", "pin centre above stay surface mm"), ("floor_proud", "throat floor above stay surface mm"),
                   ("embed", "root depth into the stay mm"), ("chamfer_w", "45 deg underside from |x| mm")):
        a(f"| {lab} | {lg[k] if lg[k] is not None else '-'} | {hg[k] if hg[k] is not None else '-'} |")
    a(f"| gap under the pin mm | {lg['hole_proud'] - lg['pin_d'] / 2 - lg['floor_proud']:.2f} | "
      f"{hg['hole_proud'] - hg['pin_d'] / 2 - hg['floor_proud']:.2f} |")
    a(f"| tip above stay surface mm | {lg['hole_proud'] + lg['hole_d'] / 2 + lg['wall_front']:.1f} | "
      f"{hg['hole_proud'] + hg['hole_d'] / 2 + hg['wall_front']:.1f} |")
    a("")
    a("**The bag must meet `bag_attach.HINGE_EYE_ENVELOPE`** (import it; the module constants `THROAT`, `HOLE_PROUD`, "
      "`HALF_Z` stay the voxel analysis envelope; BL-045 gives the IM / US pins `imus_eye_envelope`):\n")
    a("```")
    for k, v in e.items():
        a(f"{k}: {v}")
    a("```\n")
    a(f"For the HE section model this moves the pin {hg['hole_proud'] - lg['hole_proud']:.1f} mm further from the stay "
      f"(toward B-01); the cheek half-height (9 mm) is unchanged, so `cheek_lo = pin_z - 9` holds.\n")
    a("**Why a saddle.** Raising the pin alone (same root) lengthens the lever on the root: the first try (pin up, floor "
      "down 1 mm) fell to 1/FI99 1.35 on rev C. The sweep (`OUT/sweep*.json`, 1 mm voxels, rev C + 12 sim vectors) "
      "showed the critical spot is where the fairlead's root meets the stay (a 2 mm embed on a narrow stay), not the "
      "cheek: thicker cheeks (8 -> 12 mm) changed nothing, taller cheeks helped but move the cheek bottom into the bag's "
      "box, and taking the root down to the stay centreline fixed it. A 45 deg underside from |x| 9 mm keeps it "
      "printable face-down.\n")

    a("## 4. Cheek and pin checks (rev C and sim loads)\n")
    a("`fairlead_fea` is `bag_attach.solve_fairlead` (same mesh, load rule, end caps, PAHT layer FI, FI99 over the "
      "yoke), with the sideways part of a load pushing the cheek's inner face (im3_body_simloads.eye_fea's rule). With "
      "the 2026-11-01 geometry and the rev C load it reproduces the rev C record exactly (test). 1 mm voxels.\n")
    a("| hinge fairlead | rev C 1/FI99 | rev C fatigue | rev C creep | sim strength | sim fatigue | sim creep | worst sim run |")
    a("|---|---:|---:|---:|---:|---:|---:|---|")
    for tag, lab in (("legacy", "2026-11-01, stay circle r 9.35"), ("bl042", "BL-042, stay circle"),
                     ("legacy_ellipse", f"2026-11-01, stay ellipse {fe['stay_ax_sensitivity_mm']:g} x 9.35"),
                     ("bl042_ellipse", f"BL-042, stay ellipse {fe['stay_ax_sensitivity_mm']:g} x 9.35")):
        v = fe[tag]
        s = v["sim_worst"]
        a(f"| {lab} | {v['revC_sf']:.2f} | {v['revC_fatigue']:.2f} | {v['revC_creep']:.2f} | {s['strength']:.2f} | "
          f"{s['fatigue']:.2f} | {s['creep']:.2f} | {s['run']} ({s['f1g_n']:.0f} N at 1 g) |")
    a("\nRequirements: 1/FI99 >= 1.0 on the factored load (HA-LS-1 rev C), fatigue >= 1.0 (rev C) and >= 1.15 on the "
      "sim loads (BL-021 / BL-024 goal). Sim loads: the 12 CORRIE F rev 1 hinge-pin vectors (fill and meat, 3 torsos, "
      "coarse and fine, both sides mirrored onto one cheek), x 3.0 for strength, x 1.6 for fatigue, x 1.0 for creep "
      "(ASSUMPTION SIM_BODY of BL-021). The 2026-11-01 hinge **fails fatigue on the sim loads (0.79)**: their sideways "
      "pull (the bag floor spanning pin to pin, up to 196 N at 1 g) was never run on the hinge cheek.\n")
    for tag in ("legacy", "bl042"):
        pr, ps = fe[tag]["pin_revC"], fe[tag].get("pin_sim")
        a(f"- Pin bending ({tag}, 5 mm 7075-T6, span throat + cheek, load spread over the throat): rev C "
          f"{pr['sigma_mpa']:.0f} MPa, yield SF {pr['sf_yield']:.2f} (S-basis 462), fatigue SF {pr['sf_fatigue']:.2f} "
          f"(Goodman R 0 from the record's 159 MPa x 0.9 surface)" +
          (f"; sim {ps['sigma_mpa']:.0f} MPa, yield {ps['sf_yield']:.2f}, fatigue {ps['sf_fatigue']:.2f}." if ps else "."))
    a(f"- IM3 28 mm cheek (geometry unchanged), rev C governing IM3 force {fe['im3_28']['force_n']:.0f} N: 1/FI99 "
      f"{fe['im3_28']['sf']:.2f}, fatigue {fe['im3_28']['fatigue']:.2f}. BL-021's sim-load eye check "
      f"(`im3_body_simloads`) is on the same geometry and is not affected.\n")

    a("## 5. Did any structural check depend on the clipped geometry?\n")
    a("- **Fairlead cheek / pin checks** (rev C record, BL-021, BL-024, BL-027): no. They mesh `fairlead_local` whole on "
      "a stay stub; they never used the print mesh. They did use the 2026-11-01 hinge geometry, now replaced: re-run "
      "in section 4.")
    a("- **Body checks** (42 rev C sets x 4 bases, Euler buckling, z 234 joint): they run on the 2 mm voxel body, which "
      "holds the fairlead stubs below y 16. The print now clears the throat stubs (up to "
      f"{max(v['throat_cut_from_body_mm3'] for v in res['export_info']['fairleads_bl042']['per_station'].values()) / 1000:.2f}"
      " cm3 a station) and adds the hinge saddle, so the body was re-run as printed (`voxel_as_printed`, "
      f"{sum(v['removed'] for v in res['body']['voxels'].values())} voxels out, "
      f"{sum(v['added'] for v in res['body']['voxels'].values())} in):\n")
    a("| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after | joint S / F after |")
    a("|---|---|---|---|---|---|")
    for bb, v in res["body"]["bases"].items():
        a(f"| {bb} | {v['before']['strength']:.3f} / {v['after']['strength']:.3f} | {v['before']['fatigue']:.3f} / "
          f"{v['after']['fatigue']:.3f} | {v['before']['creep']:.3f} / {v['after']['creep']:.3f} | "
          f"{v['before']['buckling']:.3f} / {v['after']['buckling']:.3f} | {v['after']['joint_s']:.2f} / "
          f"{v['after']['joint_f']:.2f} |")
    a("\n`fine_sm8.cyc` fatigue was below 1 before this ticket (BL-024 cinch-cycled set, R1 hold for MT-1); BL-042 "
      "does not change that.\n")
    a("- **Mass records:** the 2 mm raster masses (h1_buckling.json 800.7 g) are unchanged; the fairlead mass outside "
      "the raster is the new ledger row H1F.\n")

    a("## 6. Mass\n")
    a(f"| step | g | oz |")
    a("|---|---:|---:|")
    for k, lab in (("solids_g", "12 fairlead solids (union, net of what the body already held)"),
                   ("throats_g", "throats cleared"), ("holes_g", "12 pin holes"), ("net_g", "**net, ledger H1F**")):
        a(f"| {lab} | {m[k]:+.1f} | {m[k] / 28.3495:+.2f} |")
    a(f"\nBasis: {m['basis']}. Ledger: `huntkit/mass/ledger.py` H1F (H1 configs), source `h1_fairleads.json`.\n")
    a("**BL-045 (2026-11-13): the 10 IM / US fairleads now carry the hinge's eye clearance** (`bag_attach.eye_geom`, "
      "`imus_eye_envelope`): each pin carries a webbing eye (IME 38 mm at IM1-IM3, the US 25 mm eye / cam anchor at "
      "US1-US2), so the 1.9 mm gap and 18 mm throat of the 2026-11-01 shape could not take a necked eye. Gap 5.5 mm, "
      "throat 20 mm, saddle (to the stay centreline at US1 / US2; on the crown sleeve at IM1-IM3 the root stops 1 mm "
      "above the 18 mm bore). The mass above includes them; the per-station checks are in "
      "`crown_and_fairlead_checks.md` (BL-045).\n")
    a("**Mass reduction that keeps the SF (not applied):** the IM1 / IM2 eye fairleads have 1/FI99 above 5 at their "
      "rev C loads (BL-045 table); a thinner cheek there needs a per-station check against the sim loads too.\n")

    a("**Print note.** Since BL-045 all 12 fairleads are saddles with a 45 deg underside outboard of |x| 9 mm "
      "(printable face-down without supports); the IM1-IM3 roots stop above the crown bore.\n")
    a("## 7. Test pieces (HE-FIT, IM3-EC)\n")
    for k, v in res["pieces"].items():
        a(f"- `{v['file']}` (+ `.3mf`, + `_frame_coords.stl`): {v['what']}; {v['g']:.1f} g; watertight {v['watertight']}, "
          f"{v['shells']} shell; slice check {'passes' if v['slice_check']['pass'] else 'FAILS'}.")
    a("\n`designs/pack_5200/physical_test_kit.py` (HE-FIT, IM3-EC, run order) now names these files. The released "
      "guide `outputs/release/test_kit/guides/G2.md` still says 'from the H1 STL' until the kit is re-released.\n")

    a("## 8. Assumptions\n")
    for k, v in (
        ("HE-T", "webbing ply 1.5 mm (patterns_corrie_f_rev3.HE_T). Settled by a caliper on the bought roll."),
        ("HE-GAP-MARGIN", "1.0 mm over the eye's ply stack under the pin (print tolerance, webbing scatter, the eye "
                          "riding round the pin). Settled by HE-FIT: a 3-ply eye slides round the pin by hand."),
        ("HE-NECK-TOL", "folded neck 18 +-1 mm; throat 20 leaves 1 mm on the widest neck. Settled by measuring 5 sewn "
                        "necks, and by HE-FIT."),
        ("HOLE_REAM", "eyes printed 7.0, reamed 7.2 (as the bores). Settled at first article: sleeve press-in by hand, "
                      "no cracking."),
        ("STAY-AX", f"the H1 stay at the hinge is narrower than the stay_radius circle; ellipse half-width "
                    f"{fe['stay_ax_sensitivity_mm']:g} mm as a sensitivity (both results tabled). Settled by the "
                    "first-article T1-T5 tests with the hinge loaded."),
        ("SIM_BODY", "BL-021's scaling of the sim's 1 g frame forces (x 3.0 / 1.6 / 1.0). Settled by T9 and the frame "
                     "strain gauges."),
        ("PIN-KS", "pin fatigue: rotating-beam 159 MPa x 0.9 machined surface, Goodman to R 0. Settled by a supplier "
                   "fatigue figure or a pin bend-fatigue test on the CA-1 rig."),
        ("THROAT-Z", "the throat is cleared to the cheek ends + 4 mm along the stay; the eye legs leave toward the bag "
                     "inside that. Settled by HE-FIT."),
    ):
        a(f"- ASSUMPTION {k}: {v}")
    a("")
    a("## 9. Screenshots\n")
    for s in shots:
        a(f"- `{Path(s).relative_to(REPO)}`")
    a("")
    DOC.write_text("\n".join(L))
    return str(DOC)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fea", action="store_true", help="hinge / IM3 cheek and pin checks only")
    ap.add_argument("--export", action="store_true", help="print files (h1_buckling.export_print) first")
    a = ap.parse_args(argv)
    if a.fea:
        print(json.dumps({k: v for k, v in fea_study().items() if k != "loads"}, indent=1, default=_np))
        return
    if a.export:
        from . import h1_buckling as B
        B.export_print(*B.CHOSEN)
    res = compute()
    shots = figures(res)
    print(write_md(res, shots))
    print("SCREENSHOTS:\n" + "\n".join(shots))


if __name__ == "__main__":
    main()
