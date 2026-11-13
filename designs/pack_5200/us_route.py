"""BL-048 N-1: the under-straps' REAL path in bag-on meat carry, checked on the cloth-sim drapes and the sliced print.

    python designs/pack_5200/us_route.py            # model, write analysis/us_route.json + screenshots + the US test piece

Fourth review N-1: ASSUMPTION US-ROUTE (``imus_stl_check.us_cradle_theta``) took each under-strap off its pin on the
straight line to its B-16 floor channel. That line runs 19-78 mm inside the loaded bag, so it is not a path a strap
can take. This module replaces it, as BL-028 / BL-029 did for the guys:

1. **Real path.** On the CORRIE F rev 3 fine meat drapes (``F_r1_PR{15,19,23}_fineFM_over_port`` / ``x_meat``; every
   crown-kit end maps to one of these torsos, h1_sleeve ASSUMPTION SIM_TORSO, and the fairleads are on the fixed stays,
   so a kit or torso change moves only the bag) the strap is a taut string (``corrie_f.taut_path``) from its pin
   (``h1_fairleads.placed``) to its channel entry on the floor (B-16 on F-02: x +/-95 at 48 / 104 mm from the frame
   seam, ``corrie_f.us_channels``), kept outside the cloth and outside the stays. Cam-tight tension = the bag-on case
   of ``huntkit.gendesign.meat_haul`` (US1 444 N, US2 296 N, factored).
2. **Contact.** The strap as a 25 mm ribbon (2 x the webbing ply thick) against the print, by slicing
   ``print/frame_h1/h1_assembled.stl`` in x planes every 1 mm into an occupancy grid (signed distance by EDT), each
   cell labelled hinge fairlead / US1 fairlead / US2 fairlead / stay, plus the HE (eye, legs, box) from the pattern
   (``patterns_corrie_f_rev3.he_geometry``) on B-01. A section model at the stay then lays the strap over what it
   meets (a string over the obstacles' bag-side envelope) and gives the bearing load on each from the turning angles.
3. **Bag-side guide.** Every guide on B-01 has to take the strap from its throat exit to a lane clear of the
   fairlead below. The lateral shift that needs, against the height available, is computed for an outboard
   (x >= 140) and an inboard lane, at 0 and 10 mm clearance; so is the fold a webbing guide needs to turn in plane.
4. **US station move.** If no guide clears: the US stations each get their own lane (lugs off the stay), checked the
   same way on the drapes (the printed US fairleads masked out of the grid, the moved ones added as boxes).
5. **US test piece.** The R stay z 40-160 with the hinge, US1 and US2 fairleads, cut from the print (as BL-042 cut the
   HE-FIT piece), so HE-FIT step 0 needs no full frame. Written into the test kit (``print/`` is BL-047's).

Units mm, N. Frame coordinates: x lateral, y towards the bag, z up.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PRINT = HERE / "print" / "frame_h1" / "h1_assembled.stl"
OUT_JSON = HERE / "analysis" / "us_route.json"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261113_BL050B_us"                   # BL-050 B re-run (A: 20261113_BL050_us, BL-049: 20261113_BL049_us)
KIT_PIECES = HERE / "print" / "frame_h1" / "test_pieces"   # BL-049: re-cut on the moved stations (was the kit folder)
US_PIECE = "us_route_stay_R"
TORSOS = (15, 19, 23)
RUN = "F_r1_PR{t}_fineFM_over_port"          # rev 3 = corrie_f.REV3_ROUTE on the rev 1 shell (corrie_f.sim_rev)
CASE = "meat"
STRAP_W = 25.0                                # US / USA webbing (imus_stl_check.eye_spec)
CLEAR_REQ = 10.0                              # BL-048 / N-1: strap >= 10 mm off the HE and every fairlead it passes
CHANNEL_X = 95.0                              # BL-048 drawing: B-16 across F-02 (190 mm), ends +/-95 (layout
#                                               'old_channel'); since BL-050 B the pattern ends at the lane x ('now')
FLEET_MAX_DEG = 10.0                          # ASSUMPTION US-FLEET: the necked eye (18-19 mm in a 20 mm throat) takes
#   a pull up to 10 deg out of the stay's y-z plane before an edge loads a cheek (the IM3 sim hook forces reach 10 deg
#   lateral and were accepted, imus_stl_check); settled by HE-FIT step 0 (pull the US box 10 deg sideways, no cheek
#   contact on the neck edge)
GRID = {"x": (40.0, 200.0), "y": (-32.0, 52.0), "z": (18.0, 178.0), "h": 1.0}
LABELS = ("stay", "hinge", "us1", "us2", "he")


def _H():
    from huntkit.gendesign import h1_fairleads as H
    return H


def _F():
    import corrie_f as F
    return F


def _P():
    import patterns_corrie_f_rev3 as P
    return P


def tensions() -> dict:
    """Cam-tight under-strap tension in bag-on meat carry (factored, meat_haul bag_on)."""
    from huntkit.gendesign import meat_haul as M
    nodes = M.analyse()["bag_on"]["nodes"]
    return {k: round(float(nodes[k]["tension_n"]), 1) for k in ("us1", "us2")}


def stations(side: str = "R") -> dict:
    return {p["name"]: p for p in _H().placed() if p["side"] == side and p["name"] in ("hinge", "us1", "us2")}


def fairlead_box(p: dict, x: float | None = None, pad: float = 0.0) -> dict:
    """Envelope of a printed fairlead (cheeks + saddle, proud of the stay): x throat/2 + cheek, z +/- half_z, y from
    the stay's bag-side surface to the cheek tips."""
    g = p["geom"]
    x0 = p["x"] if x is None else x
    hx = g.throat / 2 + g.cheek
    return {"x": (x0 - hx - pad, x0 + hx + pad), "z": (p["z"] - g.half_z - pad, p["z"] + g.z_top + pad),
            "y": (p["yc"] + p["stay_r"] - 0.5, p["y_tip"] + pad)}


# ------------------------------------------------------------------------------------------------ the HE on B-01
def he_shapes() -> dict:
    """The hinge eye on the R hinge pin in frame coordinates (design corner, patterns_corrie_f_rev3.he_geometry):
    eye + legs (19 mm neck) and the 34 x 7 box (box_gap..box_top above the floor seam, on B-01's frame face, 4 plies:
    two 3-ply legs' ends and the main ply) as y-z polygons with their x half-widths."""
    from shapely.geometry import Point, Polygon
    P = _P()
    g = P.he_geometry()
    p = stations()["hinge"]
    yc, zp = p["yc"], p["z"]
    z_seam = zp - g["pin_z"]                            # the floor seam line under the loaded pin
    t = g["t"]
    face = yc + g["face_y"]                             # B-01 at the box
    box_z = (z_seam + g["box_gap"], z_seam + g["box_top"])
    eye = Point(p["y_pin"], zp).buffer(2.5 + 3 * t, 48)
    legs = Polygon([(face - 3 * t, box_z[1]), (face, box_z[1]), (p["y_pin"] + g["r_c"] + t / 2, zp),
                    (p["y_pin"] - g["r_c"] - t / 2, zp)])
    box = Polygon([(face - 4 * t, box_z[0]), (face, box_z[0]), (face, box_z[1]), (face - 4 * t, box_z[1])])
    return {"eye_legs": (eye.union(legs).convex_hull, (P.HE_NECK_W + P.HE_NECK_TOL) / 2),
            "box": (box, P.HE_BOX[0] / 2), "x": p["x"], "z_seam": round(z_seam, 2), "box_z": [round(v, 2) for v in box_z],
            "b01_y": round(face, 2)}


# ------------------------------------------------------------------------------------------------ occupancy grid
def _axes():
    h = GRID["h"]
    return [np.arange(GRID[k][0], GRID[k][1] + 1e-9, h) for k in ("x", "y", "z")]


def occupancy(mesh=None, mask_us: bool = False, extra_boxes=()) -> dict:
    """Label grid of the R side (x > 0) from x-plane slices of the print: 0 free, 1 stay, 2 hinge fairlead, 3 US1,
    4 US2, 5 HE. ``mask_us`` clears the printed US1 / US2 fairleads (stay kept: a moved-station layout);
    ``extra_boxes`` = [(label, box)] fairlead / lug envelopes added."""
    import shapely
    import trimesh
    from shapely.geometry import box as sbox
    mesh = mesh if mesh is not None else trimesh.load(PRINT)
    H = _H()
    xs, ys, zs = _axes()
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    occ = np.zeros((len(xs), len(ys), len(zs)), np.uint8)
    st = stations()
    boxes = {n: fairlead_box(st[n], pad=1.5) for n in ("hinge", "us1", "us2")}
    for i, x in enumerate(xs):
        S = H._xplane(mesh, float(x))
        if S is None or S.is_empty:
            continue
        inside = shapely.contains_xy(S, Y, Z)
        lab = np.where(inside, 1, 0).astype(np.uint8)
        for k, n in enumerate(("hinge", "us1", "us2")):
            b = boxes[n]
            if not (b["x"][0] <= x <= b["x"][1]):
                continue
            ystay = st[n]["yc"] + st[n]["stay_r"] + 0.3
            m = inside & (Z >= b["z"][0]) & (Z <= b["z"][1]) & (Y > ystay)
            lab[m] = 0 if (mask_us and n != "hinge") else 2 + k
        occ[i] = lab
    he = he_shapes()
    for key in ("eye_legs", "box"):
        poly, hx = he[key]
        inside = shapely.contains_xy(poly, Y, Z)
        sel = np.abs(xs - he["x"]) <= hx
        occ[sel] = np.where(inside[None], 5, occ[sel])
    for lab_, b in extra_boxes:
        sx = (xs >= b["x"][0]) & (xs <= b["x"][1])
        sy = (ys >= b["y"][0]) & (ys <= b["y"][1])
        sz = (zs >= b["z"][0]) & (zs <= b["z"][1])
        occ[np.ix_(sx, sy, sz)] = lab_
    return {"occ": occ, "axes": (xs, ys, zs), "mask_us": mask_us, "n_extra": len(extra_boxes)}


def sdf(grid: dict, labels) -> np.ndarray:
    """Signed distance (mm, + outside) to the union of the given labels."""
    from scipy.ndimage import distance_transform_edt
    h = GRID["h"]
    m = np.isin(grid["occ"], labels)
    if not m.any():
        return np.full(m.shape, 1e3)
    return (distance_transform_edt(~m) - distance_transform_edt(m)) * h


def _lookup(field: np.ndarray, grid: dict, pts: np.ndarray) -> np.ndarray:
    from scipy.ndimage import map_coordinates
    xs, ys, zs = grid["axes"]
    h = GRID["h"]
    q = np.vstack([(pts[:, 0] - xs[0]) / h, (pts[:, 1] - ys[0]) / h, (pts[:, 2] - zs[0]) / h])
    return map_coordinates(field, q, order=1, mode="nearest")


def symmetry_check(mesh=None) -> dict:
    """The model works on the R side and mirrors x for L: max symmetric difference of x-plane slices at the
    stations' cheek middles (mm2)."""
    import trimesh
    mesh = mesh if mesh is not None else trimesh.load(PRINT)
    H = _H()
    out = {}
    for x in (100.0, 115.0, 130.0, 150.0):
        a, b = H._xplane(mesh, x), H._xplane(mesh, -x)
        if a is None or b is None:
            continue
        from shapely.geometry import box as sbox
        win = sbox(5, 20, 50, 175)                     # bag side of the stays (the wearer side carries the
        #                                                  hipbelt features and is not where the straps run)
        out[f"x{x:g}"] = round(float(a.intersection(win).symmetric_difference(b.intersection(win)).area), 2)
    return out


# ------------------------------------------------------------------------------------------------ the strap path
def _floor_map(torso: int):
    """Drafted floor (z 35 plane) -> loaded position, by barycentric weights on the drafted triangles."""
    F = _F()
    m = F.fine_mesh(torso)
    X0, T = m["X0"], m["tris"]
    flat = np.abs(X0[:, 2] - 35.0) < 0.5
    tf = T[flat[T].all(axis=1)]
    return X0, tf


def map_floor(torso: int, X, x: float, y: float) -> np.ndarray:
    X0, tf = _floor_map(torso)
    a, b, c = X0[tf[:, 0], :2], X0[tf[:, 1], :2], X0[tf[:, 2], :2]
    p = np.array([x, y])
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    u = 1 - v - w
    ok = (u >= -1e-6) & (v >= -1e-6) & (w >= -1e-6)
    if not ok.any():
        raise ValueError(f"({x}, {y}) is off the drafted floor")
    k = int(np.argmax(ok))
    return u[k] * X[tf[k, 0]] + v[k] * X[tf[k, 1]] + w[k] * X[tf[k, 2]]


def floor_seam_y(torso: int) -> float:
    X0, tf = _floor_map(torso)
    n = np.unique(tf)
    return float(X0[n, 1].min())


def channel_entry(torso: int, X, name: str, side: str, x_entry: float = CHANNEL_X) -> np.ndarray:
    F = _F()
    st = F.us_channels()["stations_mm"][0 if name == "us1" else 1]
    sx = 1 if side == "R" else -1
    return map_floor(torso, X, sx * x_entry, floor_seam_y(torso) + st)


def stays(side: str) -> list:
    """The stay as a tube obstacle for the string (frame x +/-115, centre y yc, radius at z 60-160)."""
    st = stations(side)
    p = st["us1"]
    xs = p.get("stay_x", p["x"])                     # BL-049: the US stations may stand on lane lugs off the stay
    yc = np.mean([q["yc"] for q in st.values()])
    r = max(q["stay_r"] for q in st.values())
    return [(np.array([xs, yc, 0.0]), np.array([xs, yc, 220.0]), r)]


def strap_path(torso: int, X, name: str, side: str = "R", pin=None, x_entry: float = CHANNEL_X):
    """Taut strap from the pin to the channel entry, outside the cloth and the stay (corrie_f.taut_path)."""
    F = _F()
    m = F.fine_mesh(torso)
    surf = F.ClothSurface(X, m["tris"])
    st = stations(side)[name]
    sx = 1 if side == "R" else -1
    A = np.array(pin if pin is not None else (st["x"], st["y_pin"], st["z"]), float)
    B = channel_entry(torso, X, name, side, x_entry)
    W = np.array([0.5 * (A[0] + B[0]), -45.0, min(A[2], B[2]) - 40.0])
    P = F.taut_path(surf, A, B, W, stays(side), n=120, iters=6000)
    return P, surf, A, B


def ribbon(P, surf, w: float = STRAP_W, t: float = 3.0, nw: int = 11) -> np.ndarray:
    """Points of the strap ribbon: width square to the path in the cloth's tangent plane, both faces (+/- t/2)."""
    u = np.gradient(P, axis=0)
    u /= np.maximum(np.linalg.norm(u, axis=1), 1e-9)[:, None]
    nr = surf.closest(P)[1]
    wd = np.cross(nr, u)
    wd /= np.maximum(np.linalg.norm(wd, axis=1), 1e-9)[:, None]
    out = [P + k * wd + s * nr for k in np.linspace(-w / 2, w / 2, nw) for s in (-t / 2, t / 2)]
    return np.vstack(out)


def clearances(R: np.ndarray, grid: dict, fields: dict, side: str, own=None) -> dict:
    """Min signed distance from the ribbon to each obstacle (R side grid; L mirrored)."""
    Q = R.copy()
    if side == "L":
        Q[:, 0] = -Q[:, 0]
    xs, ys, zs = grid["axes"]
    keep = (Q[:, 0] >= xs[0]) & (Q[:, 0] <= xs[-1]) & (Q[:, 2] >= zs[0]) & (Q[:, 2] <= zs[-1])
    Q = Q[keep]
    out = {}
    for k, f in fields.items():
        if k == own:
            continue
        out[k] = round(float(_lookup(f, grid, Q).min()), 1) if len(Q) else None
    return out


def trace(P, zs=(150, 142, 135, 130, 120, 110, 104, 95, 90, 86, 80, 75, 69, 65, 60, 55, 51, 45, 39)) -> dict:
    """Strap centre x and y where the path crosses each z (on its way down the frame face)."""
    out = {}
    for z in zs:
        i = np.where((P[:-1, 2] - z) * (P[1:, 2] - z) <= 0)[0]
        if len(i):
            j = i[0]
            f = (z - P[j, 2]) / (P[j + 1, 2] - P[j, 2] + 1e-12)
            q = P[j] + f * (P[j + 1] - P[j])
            out[f"z{z}"] = [round(float(q[0]), 1), round(float(q[1]), 1)]
    return out


def floor_corner(P) -> dict:
    """Where the strap turns under the floor: the last point of its descent down the frame face (y within 8 mm of
    the pin's) before it heads into the bag under the floor."""
    near = np.where(P[:, 1] <= P[0, 1] + 8.0)[0]
    k = int(near[np.argmin(P[near, 2])])
    return {"y": round(float(P[k, 1]), 1), "z": round(float(P[k, 2]), 1), "index": k}


# ------------------------------------------------------------------------------------------------ section model
def section_bearing(grid: dict, xc: float, pin: dict, corner_yz, T: float, w: float = STRAP_W, own: int = 0) -> dict:
    """At the stay: the strap is a string from its pin to the floor corner, laid over the bag-side (max y) envelope
    of everything under its 25 mm footprint (x xc +/- w/2). Returns the envelope, the string (upper convex hull) and
    the bearing on each obstacle = T x the turning at each hull vertex, booked to the obstacle under that vertex."""
    xs, ys, zs = grid["axes"]
    sel = (xs >= xc - w / 2) & (xs <= xc + w / 2)
    occ = grid["occ"][sel]
    z0, z1 = corner_yz[1], pin["z"] - 3.0
    env = []
    for k, z in enumerate(zs):
        if not (z0 <= z <= z1):
            continue
        col = occ[:, :, k]
        hit = (col > 1) & (col != own)                   # fairleads and HE (not the strap's own fairlead; the stay
        #                                                  is under the cloth anyway)
        if not hit.any():
            continue
        jy = np.where(hit.any(axis=0))[0].max()
        cj = col[:, jy]
        lab = int(cj[(cj > 1) & (cj != own)][0])
        env.append((float(ys[jy]) + GRID["h"] / 2, float(z), lab))
    A = (pin["y_pin"], pin["z"])
    B = (float(corner_yz[0]), float(corner_yz[1]))
    pts = [A] + [(y, z) for y, z, _ in env] + [B]
    labs = [0] + [l for _, _, l in env] + [0]
    # upper hull in +y going down in z: keep points not below the chord (monotone chain on z descending)
    order = np.argsort([-p[1] for p in pts], kind="stable")
    hull = []
    for i in order:
        p = pts[i]
        while len(hull) >= 2:
            (y1, z1_), (y2, z2_) = pts[hull[-2]], pts[hull[-1]]
            cross = (y2 - y1) * (p[1] - z1_) - (z2_ - z1_) * (p[0] - y1)
            if cross <= 0:        # the middle point is not on the +y side of the chord: drop it
                hull.pop()
            else:
                break
        hull.append(int(i))
    H = [pts[i] for i in hull]
    bearing = {}
    turn_tot = 0.0
    for a, b, c, i in zip(H[:-2], H[1:-1], H[2:], hull[1:-1]):
        u1 = np.subtract(b, a)
        u2 = np.subtract(c, b)
        u1, u2 = u1 / np.linalg.norm(u1), u2 / np.linalg.norm(u2)
        f = T * np.linalg.norm(u2 - u1)
        turn_tot += math.degrees(math.acos(np.clip(u1 @ u2, -1, 1)))
        nm = LABELS[labs[i] - 1] if labs[i] else "-"
        bearing[nm] = bearing.get(nm, 0.0) + f
    lift = max((y for y, _, _ in env), default=None)
    return {"envelope": env, "hull": [[round(y, 2), round(z, 2)] for y, z in H],
            "bearing_n": {k: round(v, 0) for k, v in bearing.items()}, "turn_deg": round(turn_tot, 1),
            "obstacle_top_y": None if lift is None else round(lift, 1),
            "touches": sorted({LABELS[l - 1] for _, _, l in env})}


# ------------------------------------------------------------------------------------------------ bag-side guide
def guide_feasibility() -> dict:
    """What a guide on B-01 must do. The strap leaves its pin inside the throat (centre at the stay x, the eye pulled
    in the stay's y-z plane), at the cheeks' lower edge. To pass the fairlead (and HE) below with ``c`` clearance it
    must be in a lane centred >= throat/2 + cheek + c + w/2 off the stay line by the top of that obstacle + c. The
    in-plane turn that takes (lower bound: a zero-radius kink, width projection ignored) and the room a 45 deg fold
    guide needs (one webbing width) are compared with what there is."""
    st = stations()
    P = _P()
    he = he_shapes()
    g = st["hinge"]["geom"]
    rows = []
    blocks = {"us1": ("hinge fairlead + HE eye", st["hinge"]["z"] + g.z_top, st["us1"]["z"] - g.half_z),
              "us2": ("US1 fairlead (+ its eye and box hanging below)", st["us1"]["z"] + g.half_z, st["us2"]["z"] - g.half_z)}
    for name, (what, z_top, z_exit) in blocks.items():
        for c in (0.0, CLEAR_REQ):
            dz = z_exit - (z_top + c)
            dx = g.throat / 2 + g.cheek + c + STRAP_W / 2
            phi = 90.0 if dz <= 0 else math.degrees(math.atan2(dx, dz))
            rows.append({"strap": name, "passes": what, "clear_mm": c, "exit_z": z_exit, "block_top_z": z_top,
                         "height_available_mm": round(dz, 1), "lateral_shift_mm": round(dx, 1),
                         "in_plane_turn_deg": round(phi, 1), "fleet_allowed_deg": FLEET_MAX_DEG,
                         "fold_room_needed_mm": STRAP_W + c, "fold_fits": dz >= STRAP_W,
                         "ok": phi <= FLEET_MAX_DEG or dz >= STRAP_W + c})
    # the eye and box alone: straight down they reach this far below the pin (imus_stl_check.box_distance + box)
    import imus_stl_check as I
    sp = I.eye_spec("us1", "L")
    reach = I.box_distance(sp, P.HE_T) + sp["box_len"]
    return {"rows": rows, "us_eye_box_reach_mm": round(reach, 1),
            "us1_box_bottom_z_straight_down": round(st["us1"]["z"] - reach, 1),
            "hinge_cheek_top_z": st["hinge"]["z"] + g.z_top, "he_box_z": he["box_z"],
            "any_ok": any(r["ok"] for r in rows if r["clear_mm"] == CLEAR_REQ),
            "standoff_y_needed": round(st["hinge"]["y_tip"] + CLEAR_REQ + 3.0, 1)}


# ------------------------------------------------------------------------------------------------ layouts
def lane_offset(c: float = CLEAR_REQ) -> float:
    """Centre-to-centre lane spacing so a strap clears the neighbouring fairlead by ``c``."""
    g = stations()["hinge"]["geom"]
    return g.throat / 2 + g.cheek + c + STRAP_W / 2


def layouts() -> dict:
    """Station layouts checked on the drapes. ``now`` = the print. ``lanes`` = BL-048's proposal for BL-047: the hinge
    stays on the stay (x 115); US1 (z 95, under the spreader's z 112 bottom edge) on an inboard lug, US2 (z 142,
    beside the spreader, which spans x +/-121 from z 112) on an outboard lug, each one lane (lane_offset) off the stay
    line, channel ends at the lane x."""
    st = stations()
    x0 = st["us1"].get("stay_x", st["us1"]["x"])
    d = lane_offset()
    # BL-050 B: 'now' = the pins where the print has them and the bag's channel ends where the PATTERN draws them
    # (corrie_f.us_channels end_x_mm: the lane x since BL-050 B); 'old_channel' = the BL-048 drawing (ends +/-95, the
    # evidence for the move); 'print_lanes' = the print with the channel ends at the lane x (BL-049 / BL-050 A)
    xu1, xu2 = abs(st["us1"]["x"]), abs(st["us2"]["x"])
    ends = _F().us_channels()["end_x_mm"]
    return {"now": {"us1": xu1, "us2": xu2, "entry": {"us1": ends["us1"], "us2": ends["us2"]}},
            "old_channel": {"us1": xu1, "us2": xu2, "entry": {"us1": CHANNEL_X, "us2": CHANNEL_X}},
            "print_lanes": {"us1": xu1, "us2": xu2, "entry": {"us1": xu1, "us2": xu2}},
            "lanes": {"us1": round(x0 - d, 1), "us2": round(x0 + d, 1),
                      "entry": {"us1": round(x0 - d, 1), "us2": round(x0 + d, 1)}},
            "lanes_old_channel": {"us1": round(x0 - d, 1), "us2": round(x0 + d, 1),
                                  "entry": {"us1": CHANNEL_X, "us2": CHANNEL_X}},
            "lanes_wide": {"us1": round(x0 - d - LANE_MARGIN["us1"], 1), "us2": round(x0 + d + LANE_MARGIN["us2"], 1),
                           "entry": {"us1": round(x0 - d - LANE_MARGIN["us1"], 1),
                                     "us2": round(x0 + d + LANE_MARGIN["us2"], 1)}}}


RECOMMENDED = "now"                  # BL-050 B: the pattern (channel ends at the lane x) on the print (BL-049: "print_lanes")
LANE_MARGIN = {"us1": 4.5, "us2": 9.5}      # BL-048: added to the bare lane offset after the first drape check: the
#   outer floor draws inboard under load (the drafted x 155.5 channel entry lands at x 143-152 on the drapes), so the
#   US2 strap drifts towards the hinge as it descends (5.6 mm worst at 19 in L on the bare lane); US1 had 10.2 mm.
#   US1 x 70, US2 x 165 are the values checked (us_route.json 'lanes_wide')


def lug_boxes(lay: dict) -> list:
    """Envelopes of the moved US fairleads and their lug arms (frame side of the fairlead floor) for the grid."""
    st = stations()
    out = []
    for k, n in ((3, "us1"), (4, "us2")):
        p = st[n]
        x = lay[n]
        b = fairlead_box(p, x=x)
        out.append((k, b))
        lo, hi = sorted((p["x"], x))
        out.append((k, {"x": (lo, hi), "z": b["z"], "y": (p["yc"] - 8.0, p["y_floor"])}))
    return out


def run_layout(name: str, mesh, drapes: dict, T: dict) -> dict:
    lay = layouts()[name]
    moved = name not in ("now", "old_channel", "print_lanes")      # those run on the print as it is
    grid = occupancy(mesh, mask_us=moved, extra_boxes=lug_boxes(lay) if moved else ())
    fields = {"hinge": sdf(grid, [2]), "us1": sdf(grid, [3]), "us2": sdf(grid, [4]), "he": sdf(grid, [5]),
              "stay": sdf(grid, [1])}
    st = stations()
    rows = []
    for t, X in drapes.items():
        for side in ("R", "L"):
            sx = 1 if side == "R" else -1
            for n in ("us1", "us2"):
                p = st[n]
                pin = (sx * lay[n], p["y_pin"], p["z"])
                P, surf, A, B = strap_path(t, X, n, side, pin=pin, x_entry=lay["entry"][n])
                R = ribbon(P, surf)
                cl = clearances(R, grid, fields, side, own=n)
                fc = floor_corner(P)
                r = {"torso": t, "side": side, "strap": n, "pin_x": round(pin[0], 1),
                     "length_mm": round(float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()), 1),
                     "trace": trace(P), "corner": {k: fc[k] for k in ("y", "z")}, "clear_mm": cl,
                     "entry": [round(float(v), 1) for v in B]}
                gate = [cl[k] for k in ("hinge", "he", "us1" if n == "us2" else None) if k and cl.get(k) is not None]
                r["min_clear_mm"] = round(min(gate), 1)
                r["pass"] = r["min_clear_mm"] >= CLEAR_REQ
                if side == "R":
                    pr = dict(p, x=lay[n])                 # (pin x on this layout)
                    tr = trace(P)
                    r["section"] = section_bearing(grid, abs(tr["z60"][0]) if "z60" in tr else abs(pin[0]), pr,
                                                   (fc["y"], fc["z"]), T[n], own=3 if n == "us1" else 4)
                if True:
                    r["path"] = [[round(float(v), 1) for v in q] for q in P[::3]]
                rows.append(r)
    worst = {n: min(r["min_clear_mm"] for r in rows if r["strap"] == n) for n in ("us1", "us2")}
    return {"layout": lay, "rows": rows, "worst_clear_mm": worst, "pass": all(r["pass"] for r in rows)}


def corner_keepers(res: dict) -> dict:
    """The bag-side part of the station move, rated. With the US stations on their lanes the strap runs straight down
    B-01 from its pin to the floor corner; on the floor it must reach its B-16 channel. Two ways:
    (a) the B-16 channel ends moved to the lane x (US1: shortened to +/-lane; US2: run past F-02 onto B-05) - the
        checked case ('lanes_wide' enters the channel at the lane x);
    (b) F-02's channels kept (+/-95) and a 25 mm keeper loop at the floor corner at the lane x holds the strap there:
        it turns on the floor towards the channel end, and the keeper takes the turn. Load = T x |u_out - u_in|
        (u_in straight down B-01, u_out along the floor from the corner to the channel end, drafted floor),
        on a box-X 21 x 25 (the USA box, capacity 3186 N, corrie_f_body 23.10)."""
    F = _F()
    st = F.us_channels()["stations_mm"]
    T = res["tension_n"]
    lay = res["layouts"][RECOMMENDED]["layout"]
    cap = 3186.0
    out = {}
    for n, y in (("us1", st[0]), ("us2", st[1])):
        dx = abs(lay[n]) - CHANNEL_X
        u_in = np.array([0.0, 0.0, -1.0])
        v = np.array([-np.sign(dx) * abs(dx), y, 0.0])
        u_out = v / np.linalg.norm(v)
        f = float(T[n] * np.linalg.norm(u_out - u_in))
        lat = float(T[n] * abs(u_out[0]))
        out[n] = {"lane_x": lay[n], "channel_end_x": CHANNEL_X, "turn_on_floor_deg": round(math.degrees(math.atan2(abs(dx), y)), 1),
                  "keeper_load_n": round(f, 0), "keeper_lateral_n": round(lat, 0), "box": "box-X 21 x 25 (USA box)",
                  "capacity_n": cap, "sf": round(cap / f, 2)}
    out["choice"] = ("(a) channel ends at the lane x: no concentrated load on the floor; US2's channel then runs past "
                     "F-02 onto B-05 (seam-sealed stitch line). (b) is the fallback if the floor must not be stitched.")
    return out


def strap_lengths(res: dict) -> dict:
    """Is each US strap long enough for its REAL bag-on path? Pin-to-pin need = the modelled path L (pin -> channel
    entry) + the channel between the entries + path R, less the USA cam's reach below the right pin; available = the
    strap's cut less its sewn eye (2 x US_EYE) and a gloved grip (TAIL_GRIP) past the cam. Worst drape per strap.
    BL-050 B: US1 and US2 have their own cuts (pattern webbing 'US' / 'US2', corrie_f.US_CUT_MM)."""
    P = _P()
    F = _F()
    web = {x["id"]: x for x in P.build("today").webbing}
    cuts = {"us1": float(web["US"]["length_mm"]), "us2": float(web["US2"]["length_mm"])}
    reach = P.USA_CUT / 2.0 - P.USA_PIN_LOOP / 2.0                # cam bar from the pin, USA folded dog-bone
    avail = {n: c - 2 * P.US_EYE - F.TAIL_GRIP_MM for n, c in cuts.items()}
    out = {"cut_mm": cuts, "usa_reach_mm": round(reach, 1), "available_mm": {n: round(v, 1) for n, v in avail.items()},
           "layouts": {}}
    for name, L in res["layouts"].items():
        row = {}
        for n in ("us1", "us2"):
            need = 0.0
            for t in TORSOS:
                rr = [r for r in L["rows"] if r["torso"] == t and r["strap"] == n]
                span = abs(rr[0]["entry"][0]) + abs(rr[1]["entry"][0])
                need = max(need, sum(r["length_mm"] for r in rr) + span - reach)
            row[n] = {"need_mm": round(need, 1), "short_by_mm": round(max(0.0, need - avail[n]), 1),
                      "grip_left_mm": round(avail[n] - need + F.TAIL_GRIP_MM, 1),
                      "cut_needed_mm": float(5 * math.ceil((need + 2 * P.US_EYE + F.TAIL_GRIP_MM) / 5.0))}
        out["layouts"][name] = row
    now = out["layouts"].get("now")
    if now:
        out["now_ok"] = all(now[n]["short_by_mm"] == 0.0 for n in ("us1", "us2"))
    return out


# ------------------------------------------------------------------------------------------------ bag-off cradle
CRADLE_BELLY_SENS = (50.0, 70.0, 90.0)   # belly sensitivity (meat_haul.BELLY_MM 70 is the design value)


def cradle_span(belly: float | None = None) -> dict:
    """BL-050 B: the bag-off cradle (huntkit.gendesign.meat_haul) re-run on the lane span. meat_haul models each strap
    as two straight legs from its pins (half span HALF_SPAN_MM = 115, the stay x) to a belly BELLY_MM below the pin
    line: T = V / (2 sin theta), theta = atan(belly / half span). On the lanes each strap has its own half span (US1
    70, US2 165, h1_bedfit published), so the legs (and the tension) differ by strap. Same vertical shares as
    meat_haul (CRADLE_SHARE, US1_FRACTION) and the same factored loads (bag-off / float: 36 kg x 1.6 g x 1.5; the
    float heavy-meat case 56 kg). The frame's US lug check (h1_lanes.lug_loads, h1_bedfit joint) uses US_CRADLE_N
    720 N at meat_haul._theta (31.3 deg): compared here. meat_haul.py itself is a shared frame-side module (not edited
    in BL-050 B): its HALF_SPAN_MM is the old stay x (found, not fixed)."""
    from huntkit.gendesign import meat_haul as M
    from huntkit.gendesign import h1_lanes as LN
    belly = M.BELLY_MM if belly is None else float(belly)
    pub = json.loads(_F().H1_PUBLISHED.read_text())["published"]
    half = {"us1": float(pub["US1_X"]), "us2": float(pub["US2_X"])}
    modes = M.analyse()
    cam = float(_MAT("cam_25mm_al").require("slip_load_n"))
    web25 = float(_MAT("poly_webbing_25mm").require("breaking_strength_n"))
    out = {"belly_mm": belly, "half_span_mm": half, "meat_haul_half_span_mm": M.HALF_SPAN_MM,
           "meat_haul_theta_deg": round(math.degrees(M._theta()), 1), "cam_slip_n": cam, "web25_break_n": web25,
           "lug_check_n": LN.US_CRADLE_N, "modes": {}}
    for mode in ("bag_off", "float", "bag_on"):
        nodes = modes[mode]["nodes"]
        row = {}
        for n in ("us1", "us2"):
            V = float(nodes[n]["vertical_n"])
            th = math.atan2(belly, half[n])
            T = V / (2.0 * math.sin(th))
            row[n] = {"vertical_n": round(V, 1), "theta_deg": round(math.degrees(th), 1), "tension_n": round(T, 1),
                      "tension_meat_haul_n": round(float(nodes[n]["tension_n"]), 1),
                      "force_on_pin_yz": [round(T * math.cos(th), 1), round(-T * math.sin(th), 1)],
                      "cam_sf": round(cam / T, 2), "web_sf": round(web25 / T, 2)}
        row["max_tension_n"] = max(row[n]["tension_n"] for n in ("us1", "us2"))
        out["modes"][mode] = row
    heavy = (M.RATED_KG - M.FLOAT_GEAR_KG) / M.QUARTER_KG       # meat_haul float heavy-meat case (56 kg)
    lim = float(modes["float"].get("meat_limit_kg", 53.0)) / M.QUARTER_KG   # the frame's float meat limit (53 kg)
    fl = out["modes"]["float"]
    out["float_heavy"] = {n: {"meat_kg": round(M.RATED_KG - M.FLOAT_GEAR_KG, 1),
                              "tension_n": round(fl[n]["tension_n"] * heavy, 1),
                              "cam_sf": round(cam / (fl[n]["tension_n"] * heavy), 2)} for n in ("us1", "us2")}
    out["at_float_limit"] = {n: {"meat_kg": round(lim * M.QUARTER_KG, 1), "tension_n": round(fl[n]["tension_n"] * lim, 1)}
                             for n in ("us1", "us2")}
    worst = max(v["tension_n"] for v in out["at_float_limit"].values())
    out["lug_check_covers"] = bool(worst <= LN.US_CRADLE_N + 0.5)
    out["lug_check_ratio"] = round(worst / LN.US_CRADLE_N, 3)
    out["path_mm"] = {n: round(2.0 * math.hypot(half[n], belly), 1) for n in ("us1", "us2")}
    return out


# BL-053 (fifth review M-1): the cradle as a 3D string. Each strap runs pin -> under the quarter -> pin. In the plane
# through the two pins (frame x) that touches the quarter's lowest front edge, a taut strap is two straight legs from
# each pin to that edge: the flattest legs (highest tension) any convex quarter bottom with that drop can give, because
# a rounded or wide bottom only makes the legs steeper. Leg vector on the R pin, frame axes (x + outboard, y + aft
# towards the bag, z + up): (-dx, dy, -belly) with dx the lateral run to the contact (the pin's lane x for a narrow
# load that meets the strap at x 0, inboard; for a quarter WIDER than the span the legs run OUTBOARD to its edges),
# dy the contact line's distance aft of the pin, belly the drop. Vertical equilibrium: V = 2 T belly / |leg|, so
# T = V |leg| / (2 belly) and the leg's lateral pull T dx / |leg| = V dx / (2 belly) does not depend on dy.
CRADLE3D_BELLY = (40.0, 50.0, 60.0, 70.0)   # BL-053: design down to a 40 mm belly (ticket item 4)
CRADLE3D_DY = (0.0, 50.0, 95.0)             # ASSUMPTION QUARTER-CONTACT: the strap meets the quarter 0 mm (taut strap on
#                                             the front edge against the spreader) to 95 mm (half the 190 mm depth of the
#                                             quarter proxy, a round bottom) aft of the pin line
QUARTER_W_MAX = 280.0                       # ASSUMPTION QUARTER-WIDTH: the R-08 quarter proxy (huntkit/viz3d/params.py
#                                             'quarter' 280 x 190 x 620 mm); legs run outboard where it is wider than the span


def cradle_3d(bellies=CRADLE3D_BELLY, dys=CRADLE3D_DY, w_max: float = QUARTER_W_MAX) -> dict:
    """BL-053: per strap, per belly, per contact dy, the leg unit vector on the R pin and the tension at the 53 kg
    float limit, factored as US_CRADLE_N (1.6 g x 1.5). 'in': a narrow load (legs run inboard to x 0, the lane half
    span); 'out': a load wider than the span (legs run outboard to the load's edge, w_max / 2 - lane x; for US2 this
    is 0 at w_max 280). V per strap from cradle_span's float-limit row (the meat_haul shares)."""
    cs = cradle_span()
    out = {"bellies_mm": list(bellies), "dy_mm": list(dys), "quarter_w_max_mm": w_max, "rows": {}, "vertical_n": {}}
    for n in ("us1", "us2"):
        half = cs["half_span_mm"][n]
        th = math.atan2(cs["belly_mm"], half)
        V = 2.0 * cs["at_float_limit"][n]["tension_n"] * math.sin(th)
        out["vertical_n"][n] = round(V, 1)
        for b in bellies:
            for dy in dys:
                for lab, dx, sx in (("in", half, -1.0), ("out", max(w_max / 2.0 - half, 0.0), 1.0)):
                    v = np.array([sx * dx, dy, -b])
                    L = float(np.linalg.norm(v))
                    T = V * L / (2.0 * b)
                    out["rows"][f"{n}|b{b:g}|dy{dy:g}|{lab}"] = {
                        "strap": n, "belly_mm": b, "dy_mm": dy, "legs": lab, "unit": (v / L).round(4).tolist(),
                        "tension_n": round(T, 1), "vec_n": (T * v / L).round(1).tolist(),
                        "lateral_n": round(T * dx / L, 1), "leg_below_horizontal_deg": round(math.degrees(math.asin(b / L)), 1)}
    return out


def cradle_record() -> dict:
    rec = cradle_span()
    rec["sensitivity"] = {f"belly_{b:.0f}": {n: cradle_span(b)["at_float_limit"][n]["tension_n"] for n in ("us1", "us2")}
                          for b in CRADLE_BELLY_SENS}
    return rec


def bag_on_legs(res: dict) -> dict:
    """BL-050 B: the bag-on case on the REAL path. meat_haul books bag-on with the cradle's theta (31.3 deg legs); on the
    drapes the strap leaves its pin straight down B-01 to the floor corner ('now' rows), so its legs stand near vertical
    and T = V / (2 sin phi) with phi the steepest-shallow leg (pin -> floor corner) over the drapes. Compared with the
    meat_haul tension us_route and the lug check use (us_route.tensions)."""
    from huntkit.gendesign import meat_haul as M
    V = {n: float(M.analyse()["bag_on"]["nodes"][n]["vertical_n"]) for n in ("us1", "us2")}
    T0 = tensions()
    out = {}
    for n in ("us1", "us2"):
        angs = []
        for r in res["layouts"]["now"]["rows"]:
            if r["strap"] != n:
                continue
            P = np.asarray(r["path"], float)
            c = r["corner"]
            k = int(np.argmin(np.abs(P[:, 2] - c["z"]) + np.abs(P[:, 1] - c["y"])))
            v = P[k] - P[0]
            angs.append(math.degrees(math.atan2(-v[2], math.hypot(v[0], v[1]))))
        phi = min(angs)
        T = V[n] / (2.0 * math.sin(math.radians(phi)))
        out[n] = {"leg_deg_min": round(phi, 1), "leg_deg_max": round(max(angs), 1), "vertical_n": round(V[n], 1),
                  "tension_n": round(T, 1), "tension_used_n": T0[n], "used_over_path": round(T0[n] / T, 2)}
    return out


def _MAT(rid: str):
    from huntkit.materials import load
    return load(rid)


# ------------------------------------------------------------------------------------------------ clevis heads
def head_clearance(drapes: dict | None = None, res: dict | None = None) -> dict:
    """BL-050 B (ASSUMPTION HEAD-PROUD, h1_bedfit): the US2 clevis bolt heads stand proud of the clevis's outer face
    (|x| head_face + washer .. + head_h, radius head_d / 2, on the bolt axes y yc + dy, z pin +/- dz). Distance from
    the heads to the bag cloth on every rev 3 fine drape (15 / 19 / 23 in, fill and meat; kit ends map to these
    torsos, SIM_TORSO) and to the US2 strap ribbon on the 'now' layout, both sides."""
    from huntkit.gendesign import h1_bedfit as BF
    F = _F()
    j = BF.JOINT
    p = stations()["us2"]
    x0, x1 = j.head_x if hasattr(j, "head_x") else (j.head_face + j.washer_t, j.head_face + j.washer_t + j.head_h)
    #                                                   BL-051: heads in a counterbore, below the clevis outer face
    yc, zc = p["yc"] + j.dy, p["z"]
    r = j.head_d / 2
    heads = [(zc + dz) for dz in (-j.dz, j.dz)]

    def dist(Q):                                        # signed distance from points to the two head cylinders (R side)
        ax_ = np.maximum.reduce([x0 - Q[:, 0], np.zeros(len(Q)), Q[:, 0] - x1])
        best = np.full(len(Q), np.inf)
        for zh in heads:
            rad = np.hypot(Q[:, 1] - yc, Q[:, 2] - zh) - r
            inside = (rad < 0) & (ax_ == 0)
            d = np.where(inside, np.maximum(rad, -np.minimum(Q[:, 0] - x0, x1 - Q[:, 0])),
                         np.hypot(np.maximum(rad, 0), ax_))
            best = np.minimum(best, d)
        return best
    out = {"head_x_mm": [round(x0, 1), round(x1, 1)], "head_y_mm": round(yc, 2), "head_z_mm": heads,
           "head_d_mm": j.head_d, "pack_half_width_mm": 394.0 / 2, "rows": [],
           "method": "cloth = the drape's surface sampled 7 x 7 per triangle (ClothSurface.S); distance to the head "
                     "cylinders, < 0 = the free drape passes through a head (the sim has no frame outboard of the stays, "
                     "so the cloth would tent over it)"}
    face_rows = []
    for t in TORSOS:
        m = F.fine_mesh(t)
        for case in ("fill", "meat"):
            X = (drapes or {}).get((t, case))
            if X is None:
                X = F.drape(RUN.format(t=t), case)
            if X is None:
                continue
            S = F.ClothSurface(X, m["tris"]).S
            for side, sx in (("R", 1.0), ("L", -1.0)):
                Q = S.copy()
                Q[:, 0] *= sx
                near = (Q[:, 0] > x0 - 40) & (np.abs(Q[:, 2] - zc) < 60)
                d = dist(Q[near]) if near.any() else np.array([np.inf])
                k = int(np.argmin(d))
                q = Q[near][k] if near.any() else None
                out["rows"].append({"torso": t, "case": case, "side": side, "cloth_mm": round(float(d[k]), 1),
                                    "at": [round(float(v), 1) for v in q] if q is not None else None})
                if hasattr(j, "outer_face") and near.any():     # BL-051: the clevis's outer slab (cheek x 8 mm deep)
                    lo = np.array([j.outer_face - 8.0, p["yc"] - 9.8, zc - 14.5])
                    hi = np.array([j.outer_face, p["y_tip"], zc + 14.5])
                    Qn = Q[near]
                    dv = np.maximum(np.maximum(lo - Qn, Qn - hi), 0.0)
                    din = np.minimum(Qn - lo, hi - Qn).min(axis=1)
                    df = np.where((dv == 0).all(axis=1), -din, np.linalg.norm(dv, axis=1))
                    kf = int(np.argmin(df))
                    face_rows.append({"torso": t, "case": case, "side": side, "face_mm": round(float(df[kf]), 1),
                                      "at": [round(float(v), 1) for v in Qn[kf]]})
    out["cloth_min_mm"] = min(r_["cloth_mm"] for r_ in out["rows"]) if out["rows"] else None
    # BL-051: the heads no longer stand proud; the nearest frame surface there is the clevis's flat outer face
    # (|x| outer_face, the US2 outer cheek's face): its clearance to the cloth on the same drapes
    of = getattr(j, "outer_face", None)
    if of is not None:
        out["outer_face_x_mm"] = of
        out["head_recess_mm"] = round(of - x1, 2)
        out["face_rows"] = face_rows
        out["face_min_mm"] = min(r_["face_mm"] for r_ in face_rows) if face_rows else None
    if res is not None:
        strap = []
        for r_ in res["layouts"]["now"]["rows"]:
            if r_["strap"] != "us2":
                continue
            P = np.asarray(r_["path"], float)
            sx = 1.0 if r_["side"] == "R" else -1.0
            Q = P.copy()
            Q[:, 0] *= sx
            dd = dist(Q).min() - STRAP_W / 2
            strap.append(round(float(dd), 1))
        out["strap_min_mm"] = min(strap) if strap else None
        out["strap_note"] = "centre-line distance less half the 25 mm width (a lower bound on the gap)"
    return out


HINGE_JSON = HERE / "analysis" / "hinge_eye_vectors.json"
HINGE_ROW_N = 1019.0          # bag-on hinge row, factored (mfg_corrie_f_rev3.HINGE_N; load_standard rev C)


def hinge_vectors(write: bool = True) -> dict:
    """BL-048 (orchestrator, for BL-047): the hinge eye force VECTOR on the frame from the rev 3 fine sims (the drapes
    used above), 15 / 19 / 23 in, fill and meat, both sides. The sim's report books the pin's force ON THE BAG
    (clothsim Pins.forces = -k (x - p)); the frame gets minus that (as im3_body_simloads.frame_forces_from_run).
    Frame axes: x lateral (+ = the R side's outboard), y towards the bag, z up. Per row: the 1 g vector (N), its
    unit vector, the angle in the stay's y-z plane (theta = atan2(fz, fy), 0 = straight into the bag, -90 = down), the
    inboard angle out of that plane, and the vector scaled to the bag's 1019 N factored row."""
    rows = []
    for t in TORSOS:
        d = json.loads((ROOT / "outputs" / "clothsim" / "corrie_f" / RUN.format(t=t) / "results.json").read_text())
        for case in ("fill", "meat"):
            att = d["cases"][case]["attachments"]
            for side, sx in (("R", 1.0), ("L", -1.0)):
                f = -np.asarray(att[f"hinge_{side}"]["force_xyz_n"], float)       # on the frame
                n = float(np.linalg.norm(f))
                u = f / n
                rows.append({"torso": t, "case": case, "side": side, "f_1g_n": [round(float(v), 1) for v in f],
                             "n_1g": round(n, 1), "unit": [round(float(v), 3) for v in u],
                             "inboard_share": round(float(-sx * u[0]), 3), "up_share": round(float(u[2]), 3),
                             "theta_yz_deg": round(math.degrees(math.atan2(f[2], f[1])), 1),
                             "inboard_deg": round(math.degrees(math.atan2(-sx * f[0], math.hypot(f[1], f[2]))), 1),
                             "at_1019_n": [round(float(v) * HINGE_ROW_N, 1) for v in u]})
    worst_in = max(rows, key=lambda r: (r["inboard_share"], r["up_share"]))
    worst_up = max(rows, key=lambda r: r["up_share"])
    out = {"source": "outputs/clothsim/corrie_f/" + RUN + "/results.json (rev 3 fine, cases fill / meat)",
           "convention": "force ON THE FRAME (minus the clothsim report's pin force on the bag); x + = R outboard, "
                         "y + = towards the bag, z + = up; unit vectors are 1 g sim directions",
           "hinge_row_n": HINGE_ROW_N, "rows": rows,
           "worst_inboard": worst_in, "worst_up": worst_up,
           "all_inboard_up": all(r["inboard_share"] > 0 and r["up_share"] > 0 for r in rows),
           "note": "the 1 g sim includes the cinched under-straps (straight cables, DRAPE-US) and the IM / guy / crown "
                   "straps; the hinge then takes the floor's lateral spread and is pulled up by the cinch. The rev C "
                   "governing hinge vector (beam model) is the other direction BL-047 checks."}
    if write:
        HINGE_JSON.write_text(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------------ test piece
def export_test_piece(mesh=None, out_dir: Path = KIT_PIECES) -> dict:
    """US test piece: the R stay z 40-160 with the hinge, US1 and US2 fairleads, cut from the print (frame
    coordinates kept, and laid flat for printing), as h1_fairleads.export_pieces cut HE-FIT / IM3-EC."""
    import trimesh
    import manifold3d as m3d
    from huntkit.gendesign import frame_h1 as H1
    from huntkit.gendesign.h1_buckling import clean_shell
    from huntkit.gendesign.surface import _from_manifold, _to_manifold
    mesh = mesh if mesh is not None else trimesh.load(PRINT)
    st = stations()
    p = st["us1"]
    hx = p["geom"].throat / 2 + p["geom"].cheek + 6.0
    zlo, zhi = 40.0, 160.0
    man = _to_manifold(mesh)
    # BL-049: x spans every station in the piece (the lane lugs stand 45 / 50 mm off the stay)
    xa = min(q["x"] - (q["geom"].throat / 2 + q["geom"].cheek) for q in st.values()) - 6.0
    xb = max(q["x"] + (q["geom"].throat / 2 + q["geom"].cheek) for q in st.values()) + 6.0
    b = m3d.Manifold.cube((xb - xa, 80.0, zhi - zlo), center=True).translate((0.5 * (xa + xb), p["yc"],
                                                                                0.5 * (zlo + zhi)))
    piece, dropped = clean_shell(_from_manifold((man ^ b).simplify(0.04)))
    # BL-050: the US2 outer clevis is its own printed piece (h1_bedfit): the frame-coordinate copy is the piece as
    # assembled (the slice checks read it); the print file is the stay piece without it (bolt us2_clevis_R from the
    # frame print folder onto it, as on the frame)
    from huntkit.gendesign import h1_buckling as HB
    printed = piece
    if HB.US2_CLEVIS:
        from huntkit.gendesign import h1_bedfit as BF
        cut = _to_manifold(piece)
        for q in BF.us2_stations():
            if q["side"] == "R":
                cut = cut - BF.split_box(q)
        printed, _ = clean_shell(_from_manifold(cut))
    flat = H1.lay_flat(printed)
    out_dir.mkdir(parents=True, exist_ok=True)
    piece.export(out_dir / f"{US_PIECE}_frame_coords.stl")
    flat.export(out_dir / f"{US_PIECE}.stl")
    flat.export(out_dir / f"{US_PIECE}.3mf")
    wt = all(trimesh.load(out_dir / fn).is_watertight for fn in (f"{US_PIECE}_frame_coords.stl", f"{US_PIECE}.stl"))
    rho = _H().RHO_G_MM3
    return {"file": str((out_dir / f"{US_PIECE}.stl").relative_to(ROOT)), "z": [zlo, zhi],
            "x": [round(xa, 1), round(xb, 1)], "g": round(printed.volume * rho, 1),
            "g_as_assembled": round(piece.volume * rho, 1), "bolt_on": "us2_clevis_R" if printed is not piece else None,
            "watertight": bool(wt), "shells": len(piece.split(only_watertight=False)), "dropped": dropped,
            "extents_mm": [round(v, 1) for v in flat.extents],
            "fairleads": sorted(n for n in st if zlo < st[n]["z"] < zhi)}


# ------------------------------------------------------------------------------------------------ run
def model(write: bool = True, piece: bool = True) -> dict:
    import trimesh
    F = _F()
    mesh = trimesh.load(PRINT)
    T = tensions()
    drapes = {}
    for t in TORSOS:
        X = F.drape(RUN.format(t=t), CASE)
        if X is None:
            raise FileNotFoundError(f"{RUN.format(t=t)} not on disk: corrie_f_sim.py finerun F --torso {t} --route over_port")
        drapes[t] = X
    import hashlib
    res = {"print": {"file": str(PRINT.relative_to(ROOT)), "md5": hashlib.md5(PRINT.read_bytes()).hexdigest()},
           "tension_n": T, "runs": {t: RUN.format(t=t) + "/x_" + CASE for t in TORSOS},
           "stations": {n: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in p.items() if k != "geom"}
                        for n, p in stations().items()},
           "he": {k: v for k, v in he_shapes().items() if k in ("z_seam", "box_z", "b01_y")},
           "symmetry_mm2": symmetry_check(mesh), "guide": guide_feasibility(), "lane_offset_mm": round(lane_offset(), 1)}
    res["layouts"] = {n: run_layout(n, mesh, drapes, T) for n in layouts()}
    res["us_route_dropped"] = True
    res["recommended"] = RECOMMENDED
    rec = res["layouts"][RECOMMENDED]
    sx0 = stations()["us1"].get("stay_x", 115.0)
    res["station_move"] = {"us1": {"x": rec["layout"]["us1"], "z": stations()["us1"]["z"], "offset_from_stay_mm":
                                   round(sx0 - rec["layout"]["us1"], 1), "side": "inboard"},
                           "us2": {"x": rec["layout"]["us2"], "z": stations()["us2"]["z"], "offset_from_stay_mm":
                                   round(rec["layout"]["us2"] - sx0, 1), "side": "outboard"},
                           "channel_entry_x": rec["layout"]["entry"], "pass": rec["pass"],
                           "worst_clear_mm": rec["worst_clear_mm"]}
    res["corner_keepers"] = corner_keepers(res)
    res["strap_lengths"] = strap_lengths(res)
    res["cradle_span"] = cradle_record()
    res["cradle_span"]["bag_on_path"] = bag_on_legs(res)
    res["clevis_heads"] = head_clearance({(t, CASE): X for t, X in drapes.items()}, res)
    if piece:
        res["test_piece"] = export_test_piece(mesh)
    elif OUT_JSON.exists():                 # BL-050 B: print/ belongs to the frame tickets; keep their piece record
        res["test_piece"] = json.loads(OUT_JSON.read_text()).get("test_piece")
    res["assumptions"] = [
        "US-TOPO: the strap lies on B-01's frame face between the bag and the frame; where a fairlead or the HE stands "
        "proud of its line it rides over it (the bag face gives, the strap is the tension member); settled by HE-FIT "
        "step 0 on the US test piece and by FIT-US on P1",
        "US-FLEET: an eye in its 20 mm throat takes <= 10 deg out of the stay plane; settled by HE-FIT step 0",
        "SIM_TORSO (h1_sleeve): every crown-kit end maps to the 15 / 19 / 23 in drape; the fairleads are on the fixed "
        "stays, so a kit or torso change moves only the bag",
        "DRAPE-US: the meat drapes were simulated with straight under-strap cables (pin to floor band); a re-run "
        "with the strap routed through eyelets on this path was not done; it settles whether the floor shape moves the "
        "lane clearances (14 / 17.7 mm against 10)",
        "DRAPE-TENT: the drapes have no fairleads in the frame contact (B-01 is not tented by the cheek tips there); the "
        "lane check measures the strap ribbon against the print in 3D, so a tent can only lift the strap away from it",
    ]
    if write:
        OUT_JSON.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    return res


def figures(res: dict) -> list:
    """1: the strap now (side section at the stay over the print + HE, and the front trace on B-01 at 15 in);
    2: the lane layout for BL-047 (front view, all torsos) with clearances."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import trimesh
    H = _H()
    SCREENS.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load(PRINT)
    st = stations()
    out = []
    now = res["layouts"]["old_channel" if "old_channel" in res["layouts"] else "now"]   # BL-050 B: the BL-048 drawing
    fig, axs = plt.subplots(1, 3, figsize=(15, 6.2), gridspec_kw={"width_ratios": [1.0, 1.0, 1.25]})
    for ax, n in zip(axs[:2], ("us1", "us2")):
        r = next(q for q in now["rows"] if q["torso"] == 15 and q["side"] == "R" and q["strap"] == n)
        S = H._xplane(mesh, 112.0)
        for poly in getattr(S, "geoms", [S]):
            xx, yy = poly.exterior.xy
            ax.fill(xx, yy, fc="#9aa3ad", ec="#33393f", lw=0.6)
            for h in poly.interiors:
                ax.fill(*h.xy, fc="white", ec="#33393f", lw=0.4)
        he = he_shapes()
        for key, col in (("eye_legs", "#e67e22"), ("box", "#d35400")):
            ax.fill(*he[key][0].exterior.xy, fc=col, alpha=0.75, ec=col)
        sec = r["section"]
        hy, hz = zip(*sec["hull"])
        ax.plot(hy, hz, "-", c="#c0392b", lw=3.0, label=f"strap at {res['tension_n'][n]:.0f} N, laid over (model)")
        ax.plot([st[n]["y_pin"], st[n]["y_pin"] + 120 * math.cos(math.radians(-50.9 if n == 'us1' else -45.6))],
                [st[n]["z"], st[n]["z"] + 120 * math.sin(math.radians(-50.9 if n == 'us1' else -45.6))], "--", c="#7f8c8d",
                lw=1.2, label="US-ROUTE (dropped): runs inside the bag")
        P = np.array(r["path"])
        ax.plot(P[:, 1], P[:, 2], ":", c="#2c3e50", lw=1.4, label="taut path on the 15 in drape (no fairleads)")
        ax.axvline(he["b01_y"], c="#16a085", lw=1.0, ls="-.", label="B-01 plane (panel offset 20)")
        txt = ", ".join(f"{k} {v:.0f} N" for k, v in sec["bearing_n"].items())
        ax.set_title(f"{n.upper()} R, side section x 112 (15 in, meat)\ntouches: {', '.join(sec['touches'])}\n"
                     f"bearing: {txt}", fontsize=9, loc="left")
        ax.set_xlim(-25, 75)
        ax.set_ylim(20, 165)
        ax.set_aspect("equal")
        ax.set_xlabel("frame y (mm, to the bag)")
        ax.legend(fontsize=7, loc="upper right")
    axs[0].set_ylabel("frame z (mm)")
    ax = axs[2]
    for n, col in (("hinge", "#7f8c8d"), ("us1", "#2980b9"), ("us2", "#8e44ad")):
        b = fairlead_box(st[n])
        ax.add_patch(Rectangle((b["x"][0], b["z"][0]), b["x"][1] - b["x"][0], b["z"][1] - b["z"][0], fc=col, alpha=0.5))
        ax.text(b["x"][1] + 1, b["z"][1] - 4, n, fontsize=8)
    he = res["he"]
    ax.add_patch(Rectangle((115 - 17, he["box_z"][0]), 34, he["box_z"][1] - he["box_z"][0], fc="#d35400", alpha=0.7))
    ax.text(133, he["box_z"][0], "HE box", fontsize=8)
    for r in now["rows"]:
        if r["side"] != "R":
            continue
        P = np.array([v for k, v in sorted(r["trace"].items(), key=lambda kv: -int(kv[0][1:]))])
        zz = [int(k[1:]) for k in sorted(r["trace"], key=lambda k: -int(k[1:]))]
        col = "#2980b9" if r["strap"] == "us1" else "#8e44ad"
        for s in (-1, 1):
            ax.plot(P[:, 0] + s * STRAP_W / 2, zz, "-", c=col, lw=0.8, alpha=0.6)
    ax.set_xlim(60, 180)
    ax.set_ylim(25, 165)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)")
    ax.set_title("Front view of the R stay: the strap edges (25 mm) on B-01,\n15 / 19 / 23 in drapes, over the hinge "
                 "fairlead and HE box", fontsize=9, loc="left")
    fig.suptitle("BL-048 channel drawing (ends x +/-95) on the BL-050 print: the strap is pulled inboard off its lane "
                 "towards the hinge fairlead and the HE (evidence for the BL-050 B channel move)", fontsize=10.5, x=0.01,
                 ha="left")
    fig.tight_layout()
    p1 = SCREENS / f"{SHOT}_1.png"
    fig.savefig(p1, dpi=85)
    plt.close(fig)
    out.append(p1)

    lay = res["layouts"][res["recommended"]]
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    S = H._zplane(mesh, 60.0)
    ax.add_patch(Rectangle((st["hinge"]["x"] - 9.4, 0), 18.8, 175, fc="#bdc3c7", alpha=0.5))
    ax.text(st["hinge"]["x"] - 8, 168, "stay", fontsize=8)
    b = fairlead_box(st["hinge"])
    ax.add_patch(Rectangle((b["x"][0], b["z"][0]), b["x"][1] - b["x"][0], b["z"][1] - b["z"][0], fc="#7f8c8d", alpha=0.7))
    ax.text(b["x"][1] + 2, b["z"][0] + 4, "hinge\n(BL-049)", fontsize=8)
    ax.add_patch(Rectangle((115 - 17, he["box_z"][0]), 34, he["box_z"][1] - he["box_z"][0], fc="#d35400", alpha=0.7))
    for k, bx in lug_boxes(lay["layout"]):
        col = "#2980b9" if k == 3 else "#8e44ad"
        ax.add_patch(Rectangle((bx["x"][0], bx["z"][0]), bx["x"][1] - bx["x"][0], bx["z"][1] - bx["z"][0], fc=col,
                               alpha=0.45, ec=col))
    for n, col in (("us1", "#2980b9"), ("us2", "#8e44ad")):
        for r in lay["rows"]:
            if r["side"] != "R" or r["strap"] != n:
                continue
            ks = sorted(r["trace"], key=lambda k: -int(k[1:]))
            xs_ = np.array([r["trace"][k][0] for k in ks])
            zz = [int(k[1:]) for k in ks]
            for s in (-1, 1):
                ax.plot(xs_ + s * STRAP_W / 2, zz, "-", c=col, lw=1.0)
        w = lay["worst_clear_mm"][n]
        ax.text(lay["layout"][n] - 12, st[n]["z"] + 12, f"{n.upper()} lane x {lay['layout'][n]:.1f}\nworst clear {w:.1f} mm",
                fontsize=8.5, color=col)
    ax.axvline(121, c="#27ae60", ls=":", lw=1)
    ax.text(122, 170, "spreader edge x 121 (z >= 112)", fontsize=7.5, color="#27ae60")
    hd = res.get("clevis_heads")
    if hd:                                          # BL-050 B: the US2 clevis bolt heads (h1_bedfit JOINT)
        for zh in hd["head_z_mm"]:
            ax.add_patch(Rectangle((hd["head_x_mm"][0], zh - hd["head_d_mm"] / 2), hd["head_x_mm"][1] - hd["head_x_mm"][0],
                                   hd["head_d_mm"], fc="#2c3e50", ec="#2c3e50"))
        ax.text(hd["head_x_mm"][1] + 1, hd["head_z_mm"][1] + 6, "clevis\nbolt heads", fontsize=7.5, color="#2c3e50")
    ax.set_xlim(40, 200)
    ax.set_ylim(20, 185)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm), R side; L mirrored")
    ax.set_ylabel("frame z (mm)")
    ok = "PASS" if lay["pass"] else "FAIL"
    ax.set_title(f"BL-050 print + BL-050 B pattern ({res['recommended']}: B-16 / B-16b channel ends at x +/-"
                 f"{lay['layout']['entry']['us1']:.0f} / {lay['layout']['entry']['us2']:.0f}): each strap clear of the "
                 f"hinge fairlead, HE\nand the other US fairlead by >= {CLEAR_REQ:.0f} mm; strap edges on the 15 / 19 / 23 "
                 f"in meat drapes: {ok}", fontsize=9.5, loc="left")
    fig.tight_layout()
    p2 = SCREENS / f"{SHOT}_2.png"
    fig.savefig(p2, dpi=90)
    plt.close(fig)
    out.append(p2)
    if "clevis_heads" in res:
        out.append(figure_heads(res))
    return out


def figure_heads(res: dict):
    """BL-050 B: (a) the floor in plan with the B-16 / B-16b channels at the lane x and the straps' floor run on the
    drapes; (b) the free drape cloth near the US2 clevis bolt heads (side section at the heads), every torso and case."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    F = _F()
    uc = F.us_channels()
    hd = res["clevis_heads"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.45, 1.0]})
    half = 393.64 / 2
    d0 = uc["floor_depth_mm"]
    a1.add_patch(Rectangle((-half, 0), 2 * half, d0, fc="#ecf0f1", ec="#34495e", lw=1.2))
    a1.text(-half + 4, d0 - 10, "B-05 floor (frame edge at the bottom)", fontsize=8)
    W2, H2 = F.F02_WH
    a1.add_patch(Rectangle((-W2 / 2, (d0 - H2) / 2), W2, H2, fc="#d6eaf8", ec="#2980b9", lw=1.0, ls="--"))
    a1.text(-W2 / 2 + 3, (d0 + H2) / 2 - 9, "F-02 fly pocket", fontsize=8, color="#2980b9")
    for k, (n, col) in enumerate((("us1", "#2980b9"), ("us2", "#8e44ad"))):
        e, yc = uc["end_x_mm"][n], uc["stations_mm"][k]
        a1.add_patch(Rectangle((-e, yc - uc["width_mm"] / 2), 2 * e, uc["width_mm"], fc=col, alpha=0.35, ec=col))
        a1.text(-e + 2, yc + uc["width_mm"] / 2 + 2, f"{F.US_CHANNEL_IDS[n]} ({n.upper()}): ends x +/-{e:.0f}, "
                f"{2 * e:.0f} mm", fontsize=8, color=col)
        for sx in (-1, 1):
            a1.annotate("", xy=(sx * e, yc), xytext=(sx * e, -18), arrowprops=dict(arrowstyle="->", color=col, lw=1.5))
    a1.text(0, -30, "the straps come straight down B-01 from their pins (lane x) and turn into their channel at the floor "
                    "corner", ha="center", fontsize=8)
    a1.set_xlim(-half - 15, half + 15)
    a1.set_ylim(-40, d0 + 12)
    a1.set_aspect("equal")
    a1.set_xlabel("x across the floor (mm)")
    a1.set_ylabel("from the frame edge (mm)")
    a1.set_title("BL-050 B: floor channels at the US lane x (B-16 on F-02; B-16b across F-02, its tails\nstitched "
                 "through B-05 and seam-sealed inside)", fontsize=9.5, loc="left")
    cols = {15: "#e67e22", 19: "#27ae60", 23: "#2c3e50"}
    for r in hd["rows"]:
        if r["at"] is None:
            continue
        mk = "o" if r["case"] == "meat" else "^"
        a2.plot(r["at"][1], r["at"][2], mk, ms=7, mfc=cols[r["torso"]] if r["side"] == "L" else "none",
                mec=cols[r["torso"]], label=f"{r['torso']} in {r['case']} {r['side']}: {r['cloth_mm']:+.1f} mm")
    for zh in hd["head_z_mm"]:
        a2.add_patch(Circle((hd["head_y_mm"], zh), hd["head_d_mm"] / 2, fc="#7f8c8d", ec="#2c3e50"))
    a2.text(hd["head_y_mm"] - 14, hd["head_z_mm"][1] + 7, "bolt heads (x "
            f"{hd['head_x_mm'][0]:.0f}-{hd['head_x_mm'][1]:.1f})", fontsize=8)
    a2.set_xlim(-30, 30)
    a2.set_ylim(118, 168)
    a2.set_aspect("equal")
    a2.set_xlabel("frame y (mm, to the bag)")
    a2.set_ylabel("frame z (mm)")
    a2.legend(fontsize=6.5, loc="lower right", ncol=1, title="nearest cloth point (filled = L)", title_fontsize=7)
    a2.set_title(f"US2 clevis bolt heads vs the free rev 3 drapes:\nworst {hd['cloth_min_mm']:+.1f} mm "
                 "(< 0: the cloth would rest on a head)", fontsize=9.5, loc="left")
    fig.tight_layout()
    p3 = SCREENS / f"{SHOT}_3.png"
    fig.savefig(p3, dpi=90)
    plt.close(fig)
    return p3


def derive() -> dict:
    """Re-derive the cheap keys (keepers, strap lengths) on the stored model without re-running the paths."""
    res = json.loads(OUT_JSON.read_text())
    res["corner_keepers"] = corner_keepers(res)
    res["strap_lengths"] = strap_lengths(res)
    res["cradle_span"] = cradle_record()
    res["cradle_span"]["bag_on_path"] = bag_on_legs(res)
    res["clevis_heads"] = head_clearance(None, res)
    OUT_JSON.write_text(json.dumps(res, indent=1))
    return res


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--hinge" in argv:
        h = hinge_vectors()
        for r in h["rows"]:
            print(r["torso"], r["case"], r["side"], r["f_1g_n"], r["n_1g"], "theta", r["theta_yz_deg"], "inboard", r["inboard_deg"])
        print("worst inboard", h["worst_inboard"]["unit"], "all inboard-up", h["all_inboard_up"])
        return 0
    if "--derive" in argv:
        res = derive()
        print(json.dumps({k: res[k] for k in ("corner_keepers", "strap_lengths")}, indent=1))
        if "--figures" in argv:
            for p in figures(res):
                print("screen:", p)
        return 0
    res = model(piece="--no-piece" not in argv)
    for n, L in res["layouts"].items():
        print(n, "worst clear", L["worst_clear_mm"], "pass", L["pass"])
        for r in L["rows"]:
            if r["side"] == "R" and r["torso"] == 15:
                print("  ", r["strap"], r["clear_mm"], r.get("section", {}).get("bearing_n"), r["trace"].get("z60"))
    print("guide any_ok", res["guide"]["any_ok"])
    for r in res["guide"]["rows"]:
        print("  ", r)
    print("piece", res.get("test_piece"))
    for p in figures(res):
        print("screen:", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
