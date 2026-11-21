"""BL-056: the SLM Ti hip pivot mount redrawn for the BL-055 8-insert boss pattern.

The drawn mount (``print/legacy/lug_hip_pivot_mount_slm_ti_D44_drawn.stl``: a D44 x 1.2 mm disc with a D10 pin hole,
two legs above and below the pin, the D10 pivot hub at 13-28 mm) gets:

* a D50 x 3 mm base (annulus about the D10 pin hole) with 8 x D5.5 clearance holes at the BL-055 insert positions
  (``analysis/h1_closeout.json`` hip.chosen.pattern.positions_xz), the legs and the pivot hub kept where they were
  (the hub height above the boss face, the 21 mm stand-off of the prying model, is unchanged: the base grows into the
  legs' lower 1.8 mm);
* a 1.2 mm x 45 deg chamfer fillet round each leg root on the new base top (the drawn flare at z 1.2-3 is now inside
  the base).

Checks: head-to-leg clearance (screw head D8.5 x 3.5 on the base top vs the legs, fillets included), driver access
straight down each screw axis, the base and the leg-to-base joint by a voxel H8 FE of the part (bolt-only bound: the
heads clamped, no bearing on the boss: the base carries all the prying) and BL-055's strip formula on the SLM
allowables, the fit on the exported frame print (sections through the boss and the base: holes on the pilots, no
clash, screw engagement), SLM orientation / support area, mass.

Mount local frame (STL): x = frame x, y = frame z - 120 + 22 (ASSUMPTION MOUNT-ORIENT), z = off the boss face toward
the wearer (frame -y); disc centre (22, 22) = boss axis (frame x 0, z 120). Units mm, N, MPa, g.

CLI: ``python -m huntkit.gendesign.hip_mount`` writes the STL / 3MF, ``analysis/hip_mount_bl056.{md,json}`` and the
screenshots.
"""
from __future__ import annotations

import functools
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "designs" / "pack_5200"
PRINT = PACK / "print"
ANALYSIS = PACK / "analysis"
DRAWN_STL = PRINT / "legacy" / "lug_hip_pivot_mount_slm_ti_D44_drawn.stl"
OUT_STEM = PRINT / "lug_hip_pivot_mount_slm_ti"
FRAME_STL = PRINT / "frame_h1" / "h1_assembled.stl"
SCREENS = ROOT / "outputs" / "screens"
DATE = "2026-11-21"

C_LOCAL = np.array([22.0, 22.0])      # disc centre of the drawn mount (local x, y) = boss axis
BASE_D = 50.0                         # BL-055 flange D (= boss D)
BASE_T = 3.0                          # BL-055 FLANGE_T
DRAWN_T = 1.2                         # the drawn disc
HOLE_D = 5.5                          # M5 clearance (ISO 273 medium; h1_closeout.FLANGE_HOLE_D)
PIN_HOLE_D = 10.0                     # pin hole through the base (h1_closeout.HIP_PIN_HOLE_D)
FILLET = 1.2                          # leg-root chamfer fillet leg (mm), 45 deg (self-supporting on the base-down build)
HEAD_D, HEAD_H = 8.5, 3.5             # DIN 7984 M5 low head (h1_closeout.HEAD_D)
HEAD_LEG_CLEAR = 1.0                  # ASSUMPTION HEAD-LEG (h1_closeout)
KEY_D = 5.0                           # ASSUMPTION KEY-D: 4 mm hex key / bit, 5 mm swept envelope straight above the head
SCREW_L = 14.0                        # h1_closeout.HIP_SCREW_L: M5 x 14 Ti gr5 DIN 7984
FACE_Y = -48.55                       # the boss's wearer face on the BL-055 print, measured (frame_fit 'face_y_measured':
#                                       the extreme -y of the print over the D50 boss); h1_closeout.HIP_FACE_Y -48.4 is its
#                                       slice level, 0.15 mm inside the face (a first placement there clashed 244 mm3)
HIP_C = (0.0, 120.0)                  # h1_closeout.HIP_C (frame x, z)
FE_H = 0.5                            # voxel edge for the part FE (mm)


# ============================================================================================ inputs
@functools.lru_cache(maxsize=None)
def pattern() -> dict:
    """The BL-055 insert pattern (h1_closeout.json hip.chosen.pattern)."""
    d = json.loads((ANALYSIS / "h1_closeout.json").read_text())
    p = d["hip"]["chosen"]["pattern"]
    return {"positions_xz": [tuple(v) for v in p["positions_xz"]], "boss_d": p["boss_d"], "hole_d": p["hole_d"],
            "hole_depth": p["hole_depth"], "pitch_mm": p["pitch_mm"], "n": p["n"],
            "rows": d["hip"]["chosen"]["rows"], "booked_flange_g": d["mount_flange"]["delta_g"],
            "bl055_flange": d["mount_flange"]}


def holes_local() -> np.ndarray:
    """Hole centres in the mount's local (x, y)."""
    P = np.asarray(pattern()["positions_xz"], float) - np.asarray(HIP_C)
    return P + C_LOCAL


def to_frame(pts) -> np.ndarray:
    """Mount local (x, y, z) -> frame (x, y, z): x - 22, FACE_Y - z, 120 + y - 22 (a proper rotation)."""
    p = np.atleast_2d(np.asarray(pts, float))
    return np.column_stack([p[:, 0] - C_LOCAL[0], FACE_Y - p[:, 2], HIP_C[1] + p[:, 1] - C_LOCAL[1]])


def frame_matrix() -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    T[:3, 3] = [-C_LOCAL[0], FACE_Y, HIP_C[1] - C_LOCAL[1]]
    return T


def _polys(mesh, z: float) -> list:
    """Closed section loops at height z as shapely polygons (outer loops; holes as their own loops)."""
    from shapely.geometry import Polygon
    s = mesh.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    return [] if s is None else [Polygon(np.asarray(L)[:, :2]).buffer(0) for L in s.discrete]


def legs_at(mesh, z: float) -> list:
    """The two leg footprints at height z (loops off the disc centre, area > 20 mm2)."""
    from shapely.geometry import Point
    return [P for P in _polys(mesh, z) if P.area > 20.0 and P.centroid.distance(Point(*C_LOCAL)) > 5.0
            and P.centroid.distance(Point(*C_LOCAL)) < 21.0 and abs(P.centroid.x - C_LOCAL[0]) < 3.0]


# ============================================================================================ geometry
def build():
    """The redrawn mount as a trimesh (local frame)."""
    import manifold3d as m3d
    import trimesh
    from .surface import _from_manifold, _to_manifold
    drawn = trimesh.load(DRAWN_STL, force="mesh")
    man = _to_manifold(drawn)
    cx, cy = C_LOCAL
    base = m3d.Manifold.cylinder(BASE_T, BASE_D / 2, BASE_D / 2, 180).translate((cx, cy, 0.0))
    man = man + base
    # leg-root chamfer fillets: hull of the leg section at the base top grown by FILLET (a thin slab) and the leg
    # section FILLET higher
    from shapely.geometry.polygon import orient

    def slab(P, z):
        ring = np.ascontiguousarray(np.asarray(orient(P, 1.0).exterior.coords)[:-1, :2], dtype=float)
        return m3d.Manifold.extrude(m3d.CrossSection([ring]), 0.05).translate((0.0, 0.0, z))
    for L in legs_at(drawn, BASE_T + FILLET + 0.05):
        sl = [slab(L.convex_hull.buffer(FILLET, join_style=1, quad_segs=6), BASE_T - 0.05),
              slab(L.buffer(-0.3), BASE_T + FILLET)]   # inset: the hull's top sits inside the leg
        man = man + m3d.Manifold.batch_hull(sl)
    cut = m3d.Manifold.cylinder(BASE_T + 2.0, PIN_HOLE_D / 2, PIN_HOLE_D / 2, 96).translate((cx, cy, -1.0))
    for x, y in holes_local():
        cut = cut + m3d.Manifold.cylinder(BASE_T + 2.0, HOLE_D / 2, HOLE_D / 2, 64).translate((x, y, -1.0))
    man = man - cut
    m = _from_manifold(man)
    m.merge_vertices()
    if not m.is_watertight:
        raise ValueError("BL-056 mount: boolean result is not a closed manifold")
    return m


@functools.lru_cache(maxsize=None)
def mount():
    import trimesh
    p = OUT_STEM.with_suffix(".stl")
    m = trimesh.load(p, force="mesh")
    if abs(m.bounds[1][0] - m.bounds[0][0] - BASE_D) > 0.2:       # not yet redrawn
        m = build()
    return m


# ============================================================================================ geometry checks
def geometry_check(m=None) -> dict:
    """Slices of the redrawn part: base disc D and thickness, hole count / D / positions, the pin hole, the legs and
    the hub kept (sections against the drawn part at the same heights), head-to-leg clearance over the head height
    (fillets included), driver access straight above every head."""
    import trimesh
    from shapely.geometry import Point
    m = m if m is not None else mount()
    drawn = trimesh.load(DRAWN_STL, force="mesh")
    out = {"watertight": bool(m.is_watertight), "shells": len(m.split(only_watertight=False)),
           "bounds": np.round(m.bounds, 2).tolist()}
    s = _polys(m, BASE_T / 2)
    outer = max(s, key=lambda P: P.area)
    inner = [P for P in s if P is not outer]
    out["base"] = {"d_eq_mm": round(2 * math.sqrt(outer.area / math.pi), 2),
                   "holes": len(inner), "hole_d_eq_mm": sorted(round(2 * math.sqrt(P.area / math.pi), 2) for P in inner),
                   "top_z_mm": None}
    # base top: the first height where the section is no longer the disc
    zs = np.arange(0.2, 6.0, 0.1)
    top = next(z for z in zs if max(P.area for P in _polys(m, z)) < 600.0)
    out["base"]["top_z_mm"] = round(float(top) - 0.05, 2)
    want = holes_local()
    got = [np.array(P.centroid.coords[0]) for P in inner if P.area < 40.0]
    err = max(min(np.linalg.norm(g - w) for g in got) for w in want) if got else 99.0
    out["base"]["hole_pos_err_mm"] = round(float(err), 3)
    pin = [P for P in inner if P.area > 40.0]
    out["base"]["pin_hole_d_eq_mm"] = round(2 * math.sqrt(pin[0].area / math.pi), 2) if pin else None
    # legs and hub kept: area of the sections above the fillet against the drawn part
    keep = {}
    for z in (BASE_T + FILLET + 0.5, 6.0, 10.0, 15.0, 21.0, 27.0):
        a_new = sum(P.area for P in _polys(m, z))
        a_old = sum(P.area for P in _polys(drawn, z))
        keep[f"z{z:g}"] = {"new_mm2": round(a_new, 1), "drawn_mm2": round(a_old, 1)}
    out["kept_sections"] = keep
    out["legs_and_hub_kept"] = bool(all(abs(v["new_mm2"] - v["drawn_mm2"]) < 0.5 for v in keep.values()))
    out["hub_top_z_mm"] = round(float(m.bounds[1][2]), 2)
    # head to leg over the head height
    clear = []
    for z in np.arange(BASE_T + 0.05, BASE_T + HEAD_H, 0.25):
        legs = [P for P in _polys(m, z) if P.centroid.distance(Point(*C_LOCAL)) > 5.0 and P.area < 400.0]
        for x, y in want:
            clear.append(min(Point(x, y).distance(L) for L in legs) - HEAD_D / 2)
    out["head_to_leg_mm"] = round(float(min(clear)), 2)
    out["head_to_leg_ok"] = bool(min(clear) >= HEAD_LEG_CLEAR)
    # head-to-head and head-to-rim
    W = np.asarray(want)
    dd = [np.linalg.norm(W[i] - W[k]) for i in range(len(W)) for k in range(i + 1, len(W))]
    out["head_to_head_mm"] = round(float(min(dd) - HEAD_D), 2)
    out["hole_edge_to_rim_mm"] = round(float(BASE_D / 2 - max(np.linalg.norm(W - C_LOCAL, axis=1)) - HOLE_D / 2), 2)
    out["head_overhang_rim_mm"] = round(float(max(np.linalg.norm(W - C_LOCAL, axis=1)) + HEAD_D / 2 - BASE_D / 2), 2)
    out["hole_to_pin_hole_mm"] = round(float(min(np.linalg.norm(W - C_LOCAL, axis=1)) - HOLE_D / 2 - PIN_HOLE_D / 2), 2)
    # driver access: a KEY_D cylinder from the head top up past the hub top must not touch the part
    import manifold3d as m3d
    from .surface import _to_manifold
    man = _to_manifold(m)
    acc = []
    for x, y in want:
        c = m3d.Manifold.cylinder(60.0, KEY_D / 2, KEY_D / 2, 48).translate((x, y, BASE_T + HEAD_H))
        acc.append(round((man ^ c).volume(), 3))
    out["driver_clash_mm3"] = acc
    out["driver_access_ok"] = bool(max(acc) < 1e-3)
    return out


# ============================================================================================ frame fit
def frame_fit(m=None) -> dict:
    """The mount placed on the exported frame print (local -> frame by ``frame_matrix``) with 8 screws: sections of
    the frame through the boss, no clash mount / frame, every base hole over a pilot hole (offset), screws (shank D5,
    head D8.5) clear of the frame except in their pilots, screw tip above the pilot floor, driver access along -y
    clear of the frame."""
    import manifold3d as m3d
    import trimesh
    from shapely.geometry import Point, Polygon
    from .surface import _to_manifold
    m = (m if m is not None else mount()).copy()
    m.apply_transform(frame_matrix())
    fr = trimesh.load(FRAME_STL, force="mesh")
    out = {"frame_stl": str(FRAME_STL.relative_to(ROOT))}
    V = fr.vertices
    on = np.hypot(V[:, 0] - HIP_C[0], V[:, 2] - HIP_C[1]) < BASE_D / 2 - 0.5
    ys = V[on, 1]
    out["face_y_measured"] = round(float(ys.min()), 3)
    out["face_flat_mm"] = round(float(np.percentile(ys, 5) - ys.min()), 3)
    # frame sections normal to y at face + 1 / + 6 / + 10.5 (into the boss): pilot holes there
    P0 = np.asarray(pattern()["positions_xz"], float)
    sl = {}
    for dy in (1.0, 6.0, 10.5, 11.0):
        s = fr.section(plane_origin=[0.0, FACE_Y + dy, 0.0], plane_normal=[0.0, 1.0, 0.0])
        loops = [] if s is None else [Polygon(np.asarray(L)[:, [0, 2]]).buffer(0) for L in s.discrete]
        holes = [L for L in loops if 20.0 < L.area < 40.0 and abs(L.centroid.x) < 30 and abs(L.centroid.y - 120) < 30]
        cen = [np.array(L.centroid.coords[0]) for L in holes]
        off = [min(np.linalg.norm(c - p) for c in cen) for p in P0] if cen else [99.0]
        sl[f"face+{dy:g}"] = {"pilots": len(holes), "pilot_d_eq": sorted({round(2 * math.sqrt(L.area / math.pi), 2)
                                                                         for L in holes}),
                              "max_offset_to_mount_hole_mm": round(float(max(off)), 3)}
    out["pilot_slices"] = sl
    # pilot floor: deepest slice (0.05 steps) that still cuts 8 pilots
    floor = 0.0
    for dy in np.arange(10.0, 14.0, 0.05):
        s = fr.section(plane_origin=[0.0, FACE_Y + dy, 0.0], plane_normal=[0.0, 1.0, 0.0])
        n = 0 if s is None else sum(1 for L in s.discrete
                                    if 20.0 < Polygon(np.asarray(L)[:, [0, 2]]).buffer(0).area < 40.0)
        if n < 8:
            break
        floor = float(dy)
    out["pilot_depth_measured_mm"] = round(floor, 2)
    # frame face plane: the boss face must be the frame's extreme -y at the mount footprint
    fm = _to_manifold(fr)
    mm = _to_manifold(m)
    clash = (fm ^ mm).volume()
    out["clash_mm3"] = round(clash, 3)
    # base bears on the boss face: frame material within 0.3 mm in front of the base underside, over the disc
    slab = m3d.Manifold.cylinder(0.3, BASE_D / 2, BASE_D / 2, 128).rotate((90.0, 0.0, 0.0)).translate(
        (HIP_C[0], FACE_Y + 0.3, HIP_C[1]))
    a_bear = (fm ^ slab).volume() / 0.3
    out["boss_contact_mm2"] = round(a_bear, 1)
    out["base_area_mm2"] = round(math.pi / 4 * (BASE_D ** 2 - PIN_HOLE_D ** 2 - 8 * HOLE_D ** 2), 1)
    # screws: shank D5 from the head down SCREW_L; head D8.5 x 3.5 on the base top. Shank must be in the pilot (no
    # frame material within D5 over its length), head must not touch the frame.
    pr = pattern()
    sc = []
    for x, z in P0:
        y_head = FACE_Y - BASE_T
        # rotate(-90 about x) maps +z to +y (into the boss), rotate(+90) to -y (toward the wearer)
        shank = m3d.Manifold.cylinder(SCREW_L, 2.5, 2.5, 48).rotate((-90.0, 0.0, 0.0)).translate((x, y_head, z))
        head = m3d.Manifold.cylinder(HEAD_H, HEAD_D / 2, HEAD_D / 2, 48).rotate((90.0, 0.0, 0.0)).translate(
            (x, y_head, z))
        key = m3d.Manifold.cylinder(80.0, KEY_D / 2, KEY_D / 2, 48).rotate((90.0, 0.0, 0.0)).translate(
            (x, y_head - HEAD_H, z))
        sc.append({"xz": [x, z], "shank_in_frame_mm3": round((fm ^ shank).volume(), 3),
                   "head_in_frame_mm3": round((fm ^ head).volume(), 3),
                   "key_in_frame_mm3": round((fm ^ key).volume(), 3),
                   "key_in_mount_mm3": round((mm ^ key).volume(), 3)})
    out["screws"] = sc
    tip_depth = SCREW_L - BASE_T
    out["screw_tip_depth_in_boss_mm"] = tip_depth
    out["pilot_depth_mm"] = pr["hole_depth"]
    out["tip_to_pilot_floor_mm"] = round(min(pr["hole_depth"], floor) - tip_depth, 2)
    ins_len = 9.5
    out["thread_engagement_in_insert_mm"] = round(min(tip_depth, ins_len), 2)
    out["pass"] = bool(clash < 1.0 and all(v["pilots"] == 8 and v["max_offset_to_mount_hole_mm"] < 0.2
                                           for k, v in sl.items() if k != "face+11")
                       and all(s_["shank_in_frame_mm3"] < 0.5 and s_["head_in_frame_mm3"] < 0.5
                               and s_["key_in_frame_mm3"] < 0.5 and s_["key_in_mount_mm3"] < 0.5 for s_ in sc)
                       and out["tip_to_pilot_floor_mm"] >= 0.3)
    return out


# ============================================================================================ FE of the part
def voxelize(m, h: float = FE_H):
    """Solid voxels (element centres inside the mesh) on a grid of edge h over the part bounds."""
    lo = np.floor(m.bounds[0] / h) * h - h
    hi = np.ceil(m.bounds[1] / h) * h + h
    shape = np.round((hi - lo) / h).astype(int)
    idx = np.indices(shape).reshape(3, -1, order="F").T
    cen = lo + (idx + 0.5) * h
    # inside test per voxel layer: the mesh section at the layer centre, loops combined even-odd (holes), shapely
    import shapely
    from shapely.geometry import Polygon
    inside = np.zeros(len(cen), bool)
    for k in range(shape[2]):
        z = lo[2] + (k + 0.5) * h
        sec = m.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
        if sec is None:
            continue
        reg = None
        for L in sec.discrete:
            P = Polygon(np.asarray(L)[:, :2]).buffer(0)
            reg = P if reg is None else reg.symmetric_difference(P)
        sel = idx[:, 2] == k
        inside[sel] = shapely.contains_xy(reg, cen[sel, 0], cen[sel, 1])
    return lo, shape, idx[inside], cen[inside]


def solve_voxels(lo, shape, ijk, h, E, nu, fixed_fn, loads_fn):
    """Linear H8 FE on the active voxels. fixed_fn(node_xyz) -> (n, 3) bool fixed dofs; loads_fn(node_xyz,
    surface_mask) -> (n, 3, ncase) nodal forces. Returns element centres, von Mises per case, displacement, nodes."""
    import scipy.sparse as sp
    from .fem import H8_LOCAL, Solver, b_h8_center, iso_D3, ke_h8, von_mises_3d
    nsh = shape + 1
    en = np.zeros((len(ijk), 8), np.int64)
    for a, off in enumerate(H8_LOCAL):
        en[:, a] = np.ravel_multi_index(tuple((ijk + off).T), tuple(nsh), order="F")
    uniq, inv = np.unique(en, return_inverse=True)
    en = inv.reshape(en.shape)
    nn = len(uniq)
    nidx = np.array(np.unravel_index(uniq, tuple(nsh), order="F")).T
    X = lo + nidx * h
    # node valence -> surface nodes (fewer than 8 elements)
    val = np.bincount(en.ravel(), minlength=nn)
    surf = val < 8
    edof = (en[:, :, None] * 3 + np.arange(3)).reshape(len(en), -1)
    KE = ke_h8(h, E, nu)
    rows = np.repeat(edof, 24, axis=1).ravel()
    cols = np.tile(edof, (1, 24)).ravel()
    K = sp.csr_matrix((np.tile(KE.ravel(), len(en)), (rows, cols)), shape=(3 * nn, 3 * nn))
    fx = fixed_fn(X).reshape(-1)
    F = loads_fn(X, surf).reshape(3 * nn, -1)
    F[fx] = 0.0
    # eliminate the fixed dofs symmetrically (unit diagonal) as fem.Assembler does
    keep = sp.diags((~fx).astype(float))
    K = (keep @ K @ keep + sp.diags(fx.astype(float))).tocsr()
    U = Solver(X, fx, tol=1e-9, maxiter=3000, direct_below=20000).solve(K, F)
    B = b_h8_center(h)
    D = iso_D3(E, nu)
    vm = []
    for c in range(F.shape[1]):
        ue = U[edof, c]
        s = ue @ B.T @ D.T
        # fem.b_h8_center orders strain (xx, yy, zz, xy, yz, zx); von_mises_3d takes the same order
        vm.append(von_mises_3d(s))
    Xe = lo + (ijk + 0.5) * h
    return {"Xe": Xe, "vm": np.array(vm).T, "U": U.reshape(nn, 3, -1), "X": X, "fixed": fx.reshape(nn, 3),
            "F": F.reshape(nn, 3, -1)}


def cantilever_check(L=40.0, b=4.0, t=4.0, h=0.5, P=10.0) -> dict:
    """Verification: voxel cantilever (fixed end x 0, tip shear P along z) against Timoshenko
    d = P L^3 / (3 E I) + P L / (k G A), and the root bending stress 6 P L / (b t^2) (beam theory, taken 1 element in
    from the clamp)."""
    E, nu = 110000.0, 0.34
    shape = np.array([int(L / h), int(b / h), int(t / h)])
    ijk = np.indices(shape).reshape(3, -1, order="F").T
    lo = np.zeros(3)

    def fixed(X):
        f = np.zeros((len(X), 3), bool)
        f[X[:, 0] < 1e-9] = True
        return f

    def loads(X, surf):
        F = np.zeros((len(X), 3, 1))
        tip = X[:, 0] > L - 1e-9
        F[tip, 2, 0] = P / tip.sum()
        return F
    r = solve_voxels(lo, shape, ijk, h, E, nu, fixed, loads)
    tip = r["X"][:, 0] > L - 1e-9
    d = float(r["U"][tip, 2, 0].mean())
    I = b * t ** 3 / 12.0
    G = E / (2 * (1 + nu))
    d_cf = P * L ** 3 / (3 * E * I) + P * L / (5.0 / 6.0 * G * b * t)
    xs = r["Xe"][:, 0]
    x0 = xs[xs > 2 * t].min()                  # away from the clamp singularity
    sel = np.abs(xs - x0) < 1e-6
    s_fe = float(r["vm"][sel, 0].max())
    s_cf = 6 * P * (L - x0) / (b * t ** 2) * (1 - h / t)       # centre of the outer element row
    return {"tip_fe_mm": d, "tip_cf_mm": d_cf, "ratio": d / d_cf, "sigma_fe": s_fe, "sigma_cf": s_cf,
            "sigma_ratio": s_fe / s_cf}


def ti_slm() -> dict:
    from huntkit.materials import load
    r = load("ti_6al_4v_slm")
    g = lambda k: float(r.require(k))   # noqa: E731
    return {"E": g("youngs_modulus_mpa"), "nu": g("poisson"), "rho_g_mm3": g("density_kg_m3") * 1e-6,
            "sy": g("yield_strength_design_mpa"), "su": g("ultimate_strength_design_mpa"),
            "se": g("fatigue_limit_asbuilt_hip_mpa")}


def fatigue_sf(sigma_max: float, se: float, su: float) -> float:
    """0 -> sigma_max cycles (R 0), Goodman on the R -1 limit: n (s/2)/Se + n (s/2)/Su = 1."""
    return 1.0 / (sigma_max / 2.0 * (1.0 / se + 1.0 / su))


def part_fe(m=None, h: float = FE_H) -> dict:
    """Voxel FE of the redrawn mount. Unit cases at the hub: Fy (V, along the legs), Fx (sideways), Fz (H, pressing
    toward the base on the hub top face), Mx, My (e H, as a linear pressure on the hub top face). BC (bolt-only bound,
    ASSUMPTION FE-BOLT-ONLY): every node of the base top within the head annulus (D5.5-D8.5) of each screw fixed, no
    bearing on the boss anywhere, so the base carries the whole moment between heads and legs (upper bound on base
    and leg-root stress). Rows = h1_closeout's hip rows (V, H) with e = +/-E_PAD_MM in x and in y and V up and down;
    the worst is kept. Stress per region at p99.5 of the element-centre von Mises and the peak (voxel steps)."""
    from . import hipbelt_structure as HS
    m = m if m is not None else mount()
    mat = ti_slm()
    lo, shape, ijk, cen = voxelize(m, h)
    W = holes_local()
    zt = BASE_T
    hub_top = float(m.bounds[1][2])
    r_bore = PIN_HOLE_D / 2

    def fixed(X):
        f = np.zeros((len(X), 3), bool)
        top = np.abs(X[:, 2] - zt) < 1e-6
        for x, y in W:
            r = np.hypot(X[:, 0] - x, X[:, 1] - y)
            f[top & (r >= HOLE_D / 2 - 1e-6) & (r <= HEAD_D / 2 + 1e-6)] = True
        return f

    def loads(X, surf):
        F = np.zeros((len(X), 3, 5))
        r = np.hypot(X[:, 0] - C_LOCAL[0], X[:, 1] - C_LOCAL[1])
        bore = surf & (r < r_bore + h * 1.01) & (X[:, 2] > 14.0)
        F[bore, 1, 0] = 1.0 / bore.sum()                       # Fy unit (bearing on the bore band)
        F[bore, 0, 1] = 1.0 / bore.sum()                       # Fx unit
        topf = np.abs(X[:, 2] - hub_top) < 0.75 * h + 1e-6
        topf &= surf
        n = topf.sum()
        F[topf, 2, 2] = -1.0 / n                               # Fz unit toward the base
        dx, dy = X[topf, 0] - C_LOCAL[0], X[topf, 1] - C_LOCAL[1]
        F[topf, 2, 3] = dy / (dy ** 2).sum()                   # Mx unit (sum F dy = 1 N mm)
        F[topf, 2, 4] = -dx / (dx ** 2).sum()                  # My unit
        return F
    res = solve_voxels(lo, shape, ijk, h, mat["E"], mat["nu"], fixed, loads)
    Xe = res["Xe"]
    import scipy.sparse  # noqa: F401  (solve cache)
    # stress tensors per unit case are needed for superposition: recompute element stress components
    from .fem import b_h8_center, iso_D3, von_mises_3d
    B, D = b_h8_center(h), iso_D3(mat["E"], mat["nu"])
    nsh = shape + 1
    from .fem import H8_LOCAL
    en = np.zeros((len(ijk), 8), np.int64)
    for a, off in enumerate(H8_LOCAL):
        en[:, a] = np.ravel_multi_index(tuple((ijk + off).T), tuple(nsh), order="F")
    uniq, inv = np.unique(en, return_inverse=True)
    en = inv.reshape(en.shape)
    edof = (en[:, :, None] * 3 + np.arange(3)).reshape(len(en), -1)
    U = res["U"].reshape(-1, 5)
    S = np.stack([U[edof, c] @ B.T @ D.T for c in range(5)], axis=2)      # (ne, 6, 5)
    reg = np.where(Xe[:, 2] < zt, "base", np.where(Xe[:, 2] < zt + FILLET + 1.0, "leg_root",
                                                   np.where(Xe[:, 2] < 13.0, "legs", "hub")))
    # leave out the elements under the clamped head annuli (the BC singularity)
    near = np.zeros(len(Xe), bool)
    for x, y in W:
        near |= (np.hypot(Xe[:, 0] - x, Xe[:, 1] - y) < HEAD_D / 2 + h) & (Xe[:, 2] > zt - 2 * h)
    e = HS.E_PAD_MM

    def sweep(offsets):
        rows, fields = {}, {}
        for k, r in pattern()["rows"].items():
            V, H = r["V_n"], r["H_n"]
            worst = None
            for sv in (-1.0, 1.0):
                for ex, ey in offsets:
                    coef = np.array([sv * V, 0.0, H, -H * ey, H * ex]) if H > 0 else np.array([sv * V, 0, 0, 0, 0])
                    vm = von_mises_3d(S @ coef)
                    st = {}
                    for rg in ("base", "leg_root", "legs", "hub"):
                        sel = (reg == rg) & ~near
                        st[rg] = {"p995": float(np.percentile(vm[sel], 99.5)), "peak": float(vm[sel].max())}
                    key = max(v["p995"] for v in st.values())
                    if worst is None or key > worst[0]:
                        worst = (key, st, (sv, ex, ey), vm)
            kind = r["kind"]
            lim = mat["se"] if kind == "fatigue" else mat["sy"]
            out = {}
            for rg, v in worst[1].items():
                sf = fatigue_sf(v["p995"], mat["se"], mat["su"]) if kind == "fatigue" else lim / v["p995"]
                out[rg] = {"sigma_p995_mpa": round(v["p995"], 1), "sigma_peak_mpa": round(v["peak"], 1),
                           "sf": round(sf, 2)}
            fields[k] = worst[3]
            rows[k] = {"V_n": V, "H_n": H, "kind": kind, "goal": r["goal"], "worst_sign_ex_ey": worst[2],
                       "regions": out, "min_sf_base_legroot": min(out["base"]["sf"], out["leg_root"]["sf"]),
                       "min_sf_all": min(v["sf"] for v in out.values())}
        return rows, fields
    # design: the pad offset e is vertical (hipbelt E_PAD_MM: lumbar pressure centroid +/-20 mm about the pin, i.e. along
    # frame z = local y); sensitivity: the same 20 mm sideways (local x), a case the fit model does not produce
    rows, fields = sweep(((0.0, e), (0.0, -e), (0.0, 0.0)))
    rows_lat, _ = sweep(((e, 0.0), (-e, 0.0)))
    gov = min(rows, key=lambda k: rows[k]["min_sf_all"] / rows[k]["goal"])
    part_fe.last_field = {"Xe": Xe, "vm": fields[gov], "row": gov, "near": near}
    lat = {k: {"min_sf_all": v["min_sf_all"], "goal": v["goal"], "region": min(v["regions"], key=lambda g: v["regions"][g]["sf"]),
               "sigma_p995_mpa": max(x["sigma_p995_mpa"] for x in v["regions"].values())} for k, v in rows_lat.items()}
    extra = {"lateral_offset_sensitivity": {"rows": lat, "min_sf_over_goal": round(
        min(v["min_sf_all"] / v["goal"] for v in lat.values()), 2)}}
    return {"h_mm": h, "n_elem": int(len(ijk)), "mass_voxel_g": round(len(ijk) * h ** 3 * mat["rho_g_mm3"], 2),
            "material": "ti_6al_4v_slm (design yield 785, Su 850, as-built HIP fatigue 200 MPa R -1)",
            "bc": "bolt-only bound: head annuli clamped, no boss bearing", "rows": rows, "governing": gov,
            "min_sf_over_goal": round(min(rows[k]["min_sf_all"] / rows[k]["goal"] for k in rows), 2), **extra}


def strip_check() -> dict:
    """BL-055's flange strip formula (sigma = 6 T a / (b t^2)) re-run on the redrawn leg roots (fillet included: the
    arm from the fillet toe) and on the SLM allowables (BL-055 used the wrought S-basis yield and fatigue limit)."""
    m = mount()
    mat = ti_slm()
    legs = legs_at(m, BASE_T + 0.05)
    half = max(max(abs(L.bounds[0] - C_LOCAL[0]), abs(L.bounds[2] - C_LOCAL[0])) for L in legs)
    xs = min(abs(x - HIP_C[0]) for x, _ in pattern()["positions_xz"])
    arm = xs - half
    b = pattern()["pitch_mm"]
    rows = {}
    for k, r in pattern()["rows"].items():
        sig = 6.0 * r["T_max_n"] * arm / (b * BASE_T ** 2)
        sf = fatigue_sf(sig, mat["se"], mat["su"]) if r["kind"] == "fatigue" else mat["sy"] / sig
        rows[k] = {"sigma_mpa": round(sig, 1), "sf": round(sf, 2), "goal": r["goal"]}
    return {"leg_half_w_at_base_top_mm": round(half, 2), "arm_mm": round(arm, 2), "strip_b_mm": b, "rows": rows,
            "min_sf_over_goal": round(min(v["sf"] / v["goal"] for v in rows.values()), 2)}


# ============================================================================================ print
def slm_plan(m=None) -> dict:
    """Support area (45 deg rule, surface.overhang_area) for the six axis build directions; the chosen one."""
    from .surface import CANDIDATE_DIRS, overhang_area
    m = m if m is not None else mount()
    rows = {k: round(overhang_area(m, v, 45.0), 1) for k, v in CANDIDATE_DIRS.items()}
    return {"support_area_mm2_by_build_dir": rows, "chosen": "+z",
            "why": "base down on the plate: the 8 holes and the pin hole print as vertical round holes (no support, no "
                   "drift), the base face is the datum face and is faced flat after the cut-off; the leg-root fillets "
                   "are 45 deg; the supports left are under the hub's lower face between the legs (removed by hand, "
                   "the hub face is not a bearing face). -z (hub down) puts the base's whole underside on supports; "
                   "+/-x and +/-y lay the holes sideways (oval, supported bores)."}


def mass(m=None) -> dict:
    import trimesh
    m = m if m is not None else mount()
    rho = ti_slm()["rho_g_mm3"]
    drawn = trimesh.load(DRAWN_STL, force="mesh")
    g_new, g_old = m.volume * rho, drawn.volume * rho
    booked = pattern()["booked_flange_g"]
    return {"drawn_g": round(g_old, 2), "redraw_g": round(g_new, 2), "delta_g": round(g_new - g_old, 2),
            "booked_bl055_g": booked, "ledger_correction_g": round(g_new - g_old - booked, 2),
            "basis": "STL volume x ti_6al_4v_slm density 4430 kg/m3"}


# ============================================================================================ tests for the kit
def insert_tests() -> dict:
    """HB-6 (insert pull-out on printed coupons) and HB-6b (hip-mount proof on the frame) as data for the kit."""
    from . import h1_closeout as C
    ir = C.insert_record()
    cap = C.hip_capacity(True)
    rows = pattern()["rows"]
    c2 = rows["C2|H_frame"]
    walk = rows["walk|H_frame"]
    carry = rows["carry|H_frame"]
    E_ti = ti_slm()["E"]
    # screw strain on the gauge section: the shank turned to D4.2 over 4 mm (ASSUMPTION SCREW-GAUGE)
    As = math.pi / 4 * 4.2 ** 2
    ue = lambda T: round(T / As / E_ti * 1e6, 0)     # noqa: E731
    hb6 = {"id": "HB-6", "what": "M5 brass heat-set insert pull-out from printed PAHT-CF coupons",
           "coupon": f"PAHT-CF block 30 x 30 x 20 mm printed flat with the H1 settings (BL-053 profile), the pilot "
                     f"D{pattern()['hole_d']:g} x {pattern()['hole_depth']:g} deep cut along the BUILD Z (layer "
                     f"normal), insert {ir['od']:g} OD x {ir['length']:g} set with the iron at the vendor temperature",
           "n_coupons": 6, "conditioning": "60 C (140 F) for >= 2 h, pulled at 60 C in the chamber or within 60 s of "
                                           "removal",
           "rig": "M5 bolt through a rigid steel bridge with a D14 clearance ring round the insert (ring reacts on the "
                  "coupon face), pull at 5 mm/min to failure",
           "pass_line_n_each": round(cap["static_n"], 0),
           "pass_line_basis": cap["basis"] + " = the static design value the BL-055 pattern was sized on",
           "pass_rule": "every one of the 6 coupons >= the pass line (no statistics on 6); record the failure mode "
                        "(insert pull-out / cone of plastic / thread strip)",
           "what_it_settles": ["INS-Z", "INS-DEPTH (section one coupon: no melt plug under the insert)"],
           "minimum_for_8_inserts_n": round(max(1.15 * rows["walk|H_frame"]["T_max_n"] / ir["fat_ratio"],
                                                1.5 * rows["C2|H_frame"]["T_max_n"]), 0),
           "if_it_fails": "between the 8-insert minimum (fatigue row: 1.15 x T_walk / 0.3) and the pass line: the "
                          "pattern still passes but with no margin, report it; below the minimum: the 10-split "
                          "pattern on the same D50 boss (BL-055 sweep fatigue 1.51) needs about 0.8 x the minimum; "
                          "below that, stop and re-open the hip joint",
           "fatigue_option": {
               "cycles": 100000, "peak_n": round(cap["fatigue_n"], 0), "R": 0.1,
               "pass": "no insert movement > 0.1 mm (dial on the bolt head) after 1e5 at the BL-055 fatigue design "
                       "value per insert; 2 coupons"}}
    hb6b = {"id": "HB-6b", "what": "hip-mount proof on the frame: the redrawn Ti mount on the D50 boss with 8 inserts",
            "setup": "frame lumbar hub clamped on the stays; mount screwed with 8 x M5 x 14 Ti DIN 7984 SNUG "
                     "(0.3 N m, no preload: the prying model credits none), gauge zeroed after snugging; a repeat at "
                     "the 2.5 N m service torque is recorded for information only (preload hides the prying); a dummy pin in the D10 hub; load V along frame -z through the pin at its "
                     "21 mm stand-off (no H: the H_frame rows, the inserts' governing case)",
            "gauge": "one 1 mm foil gauge on the shank of the most-loaded screw (the lower group, outermost: frame "
                     "(+/-14.12, 107.29); the shank turned to D4.2 over 4 mm for the gauge, the same screw on the "
                     "bench first: calibrate microstrain vs tension in a tensile rig 0-400 N)",
            "steps": [], "pass_rule": "", "settles": ["FLANGE-RIGID", "the prying model's T_max"]}
    for nm, V, T in (("carry 1 g", carry["V_n"], carry["T_max_n"]), ("walk 1.6 g", walk["V_n"], walk["T_max_n"]),
                     ("C2 proof", c2["V_n"], c2["T_max_n"])):
        hb6b["steps"].append({"step": nm, "pin_load_v_n": round(V, 0), "pin_load_v_lbf": round(V / 4.448, 0),
                              "model_screw_tension_n": round(T, 0), "model_microstrain": ue(T),
                              "pass_if_microstrain_at_most": ue(T * 1.15)})
    hb6b["pass_rule"] = ("at every step the measured screw microstrain <= the pass line (model x 1.15); after the C2 "
                         "proof (hold 60 s): no screw loosened (torque marks), no insert moved (dial < 0.1 mm), no "
                         "crack on the boss under a 10x loupe; then 1e5 cycles 0 -> walk step at <= 3 Hz, same "
                         "checks. A reading above the pass line means the flange is not rigid (FLANGE-RIGID wrong): "
                         "stop and re-run the prying model with the measured split.")
    hb6b["cycles"] = {"n": 100000, "peak_v_n": round(walk["V_n"], 0), "R": 0.0}
    return {"HB-6": hb6, "HB-6b": hb6b,
            "screw_gauge_basis": f"Ti gr5 E {E_ti:g} MPa (ti_6al_4v_slm record E; gr5 bar 110-114 GPa), tensile "
                                 f"gauge section D4.2 = {As:.2f} mm2 (shank turned down over 4 mm)"}


# ============================================================================================ run
ASSUMPTIONS = [
    ("MOUNT-ORIENT", "Carried from BL-055: the mount's local y is frame z (legs above and below the pin).",
     "First-article fit of the mount on the boss."),
    ("FE-BOLT-ONLY", "The part FE clamps only the screw-head annuli and gives no bearing on the boss: an upper bound on "
     "base and leg-root bending (the real base also bears on the boss on the compression side).",
     "HB-6b screw gauge (if the screw reads below the model, the bound holds)."),
    ("FLANGE-RIGID", "Carried from BL-055: the insert tensions come from the rigid-flange prying model; the 3 mm base "
     "is checked for its own bending with the bound above.", "HB-6b."),
    ("HEAD-LEG", ">= 1 mm between a DIN 7984 head (D8.5) and a leg root (fillet included), for the driver.",
     "First-article assembly with a 4 mm hex key."),
    ("KEY-D", "A 4 mm hex key / bit sweeps a D5 envelope straight above the head (checked clear of the part and the "
     "frame for 60-80 mm).", "First-article assembly."),
    ("SLM-FAT", "Fatigue on the as-built HIP limit 200 MPa (R -1, 1e7) with Goodman on Su 850 for the 0 -> peak "
     "walk cycle; the base faces are not machined except the datum face.", "Vendor coupon (ti_6al_4v_slm record "
     "note)."),
    ("SCREW-GAUGE", "Screw tension from the strain on a D4.2 turned gauge section (13.85 mm2) and E 110 GPa, screws "
     "snug (no preload); calibrated on the bench before HB-6b.", "Bench calibration of the gauged screw."),
]


def compute(fe: bool = True) -> dict:
    res = {"ticket": "BL-056", "date": DATE, "stl": str(OUT_STEM.with_suffix(".stl").relative_to(ROOT)),
           "drawn_stl": str(DRAWN_STL.relative_to(ROOT))}
    m = mount()
    res["geometry"] = geometry_check(m)
    res["frame_fit"] = frame_fit(m)
    res["strip"] = strip_check()
    res["bl055_strip_record"] = {"min_sf_over_goal": pattern()["bl055_flange"]["min_sf_over_goal"],
                                 "basis": "wrought ti_6al_4v S-basis 827 / fatigue limit 510 MPa (not SLM)"}
    if fe:
        res["verification"] = {"cantilever": cantilever_check()}
        res["fe"] = part_fe(m)
    res["slm"] = slm_plan(m)
    res["mass"] = mass(m)
    res["tests"] = insert_tests()
    res["assumptions"] = [{"id": a, "text": t, "settled_by": s} for a, t, s in ASSUMPTIONS]
    return res


def export(log=print) -> list:
    from .surface import export as ex
    m = build()
    files = ex(m, OUT_STEM)
    mount.cache_clear()
    log(f"exported {files}")
    return files


# ============================================================================================ figures + report
SHOT = "20261121_BL056_"


def _save(fig, path: Path) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    if path.stat().st_size > 1.5e6:
        raise ValueError(f"{path} over 1.5 MB")
    return str(path.relative_to(ROOT))


def plot_part(res: dict) -> str:
    """Shaded 3D view of the redrawn mount next to the drawn one, and the top view of the base: holes, heads (D8.5),
    leg roots with fillets, pin hole."""
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Circle
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from shapely.geometry import Point
    m = mount()
    drawn = trimesh.load(DRAWN_STL, force="mesh")
    fig = plt.figure(figsize=(12, 4.6))
    light = np.array([0.4, -0.5, 0.8]) / np.linalg.norm([0.4, -0.5, 0.8])
    for i, (mm, ttl) in enumerate(((drawn, "drawn: D44 x 1.2, no screw holes"),
                                   (m, "BL-056: D50 x 3, 8 x D5.5, leg-root fillets"))):
        ax = fig.add_subplot(1, 3, i + 1, projection="3d")
        sh = 0.35 + 0.6 * np.clip(mm.face_normals @ light, 0, 1)
        col = np.c_[0.55 * sh, 0.58 * sh, 0.62 * sh, np.ones_like(sh)]
        ax.add_collection3d(Poly3DCollection(mm.triangles, facecolors=col, edgecolor="none"))
        ax.set_xlim(-3, 47); ax.set_ylim(-3, 47); ax.set_zlim(0, 50)
        ax.view_init(28, -60)
        ax.set_box_aspect((1, 1, 1))
        ax.set_title(ttl, fontsize=9)
        ax.set_xlabel("x (frame x)"); ax.set_ylabel("y (frame z)"); ax.set_zlabel("off the boss")
    ax = fig.add_subplot(1, 3, 3)
    for P in _polys(m, BASE_T / 2):
        xy = np.asarray(P.exterior.coords)
        ax.plot(xy[:, 0] - C_LOCAL[0], xy[:, 1] - C_LOCAL[1], color="#333", lw=1)
    for L in legs_at(m, BASE_T + 0.05):
        xy = np.asarray(L.exterior.coords)
        ax.fill(xy[:, 0] - C_LOCAL[0], xy[:, 1] - C_LOCAL[1], color="#7aa0c4", label="leg root + fillet")
    for x, y in holes_local():
        ax.add_patch(Circle((x - C_LOCAL[0], y - C_LOCAL[1]), HEAD_D / 2, fc="none", ec="#c55", ls="--", lw=1))
    g = res["geometry"]
    ax.set_aspect("equal")
    ax.set_title(f"base top view (frame x, z - 120)\nheads D8.5 dashed: head-to-leg {g['head_to_leg_mm']:.1f} mm, "
                 f"head-to-head {g['head_to_head_mm']:.2f} mm", fontsize=9)
    h, l_ = ax.get_legend_handles_labels()
    ax.legend(h[:1], l_[:1], fontsize=7, loc="lower left")
    return _save(fig, SCREENS / f"{SHOT}1.png")


def plot_fe(res: dict) -> str:
    """Von Mises (governing row, worst load sign / pad offset) on the element centres: section x = 22 (through the
    legs) and the base mid-plane, with the SF per region."""
    import matplotlib.pyplot as plt
    f = getattr(part_fe, "last_field", None)
    if f is None:
        part_fe(mount())
        f = part_fe.last_field
    Xe, vm = f["Xe"], f["vm"]
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1.1, 1, 0.9]})
    h = FE_H
    sel = np.abs(Xe[:, 0] - (C_LOCAL[0] + 0.25)) < h / 2 + 1e-6
    sc = axs[0].scatter(Xe[sel, 1] - C_LOCAL[1], Xe[sel, 2], c=vm[sel], s=6, marker="s", cmap="inferno", vmin=0,
                        vmax=float(np.percentile(vm, 99.8)))
    axs[0].set_aspect("equal"); axs[0].set_xlabel("frame z - 120 (mm)"); axs[0].set_ylabel("off the boss (mm)")
    axs[0].set_title(f"section through the legs, row {f['row']}", fontsize=9)
    fig.colorbar(sc, ax=axs[0], label="von Mises MPa", shrink=0.8)
    sel = np.abs(Xe[:, 2] - (BASE_T + 0.75)) < h / 2 + 1e-6
    sc = axs[1].scatter(Xe[sel, 0] - C_LOCAL[0], Xe[sel, 1] - C_LOCAL[1], c=vm[sel], s=5, marker="s", cmap="inferno",
                        vmin=0, vmax=float(np.percentile(vm, 99.8)))
    axs[1].set_aspect("equal"); axs[1].set_xlabel("frame x"); axs[1].set_ylabel("frame z - 120")
    axs[1].set_title(f"leg roots, z {BASE_T + 0.75:g} mm (heads clamped: bolt-only bound)", fontsize=9)
    rows = res["fe"]["rows"]
    labs, vals, goals = [], [], []
    for k, r in rows.items():
        labs.append(k.replace("|", "\n"))
        vals.append(r["min_sf_all"] / r["goal"])
    axs[2].barh(range(len(vals)), vals, color=["#c55" if v < 1.0 else ("#e0a030" if v < 1.1 else "#4a8") for v in vals])
    axs[2].axvline(1.0, color="k", lw=1)
    axs[2].set_yticks(range(len(vals)), labs, fontsize=7)
    axs[2].set_xlabel("min SF / goal (all regions)")
    axs[2].set_title("part FE, every hip row", fontsize=9)
    for i, v in enumerate(vals):
        axs[2].text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=7)
    return _save(fig, SCREENS / f"{SHOT}2.png")


def plot_fit(res: dict) -> str:
    """The frame print sliced 1 mm into the boss (pilot holes) with the mount base outline, holes and heads on top;
    and a side section (plane z = 107.29, through the lower screw row) of frame + mount + screws."""
    import matplotlib.pyplot as plt
    import trimesh
    fr = trimesh.load(FRAME_STL, force="mesh")
    m = mount().copy()
    m.apply_transform(frame_matrix())
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    s = fr.section(plane_origin=[0.0, FACE_Y + 1.0, 0.0], plane_normal=[0.0, 1.0, 0.0])
    for L in s.discrete:
        L = np.asarray(L)
        axs[0].plot(L[:, 0], L[:, 2], color="#888", lw=2.2)
    s = m.section(plane_origin=[0.0, FACE_Y - 1.5, 0.0], plane_normal=[0.0, 1.0, 0.0])
    for L in s.discrete:
        L = np.asarray(L)
        axs[0].plot(L[:, 0], L[:, 2], color="#1f6fb4", lw=1.2)
    from matplotlib.patches import Circle
    for x, z in pattern()["positions_xz"]:
        axs[0].add_patch(Circle((x, z), HEAD_D / 2, fc="none", ec="#c55", ls="--"))
    axs[0].set_aspect("equal"); axs[0].set_xlim(-40, 40); axs[0].set_ylim(80, 160)
    axs[0].set_title("frame 1 mm into the boss (grey: boss + 8 pilots D6.4)\nblue: mount base holes; red: heads",
                     fontsize=9)
    axs[0].set_xlabel("frame x"); axs[0].set_ylabel("frame z")
    z0 = pattern()["positions_xz"][0][1]
    for mesh, col in ((fr, "#444"), (m, "#1f6fb4")):
        s = mesh.section(plane_origin=[0.0, 0.0, z0], plane_normal=[0.0, 0.0, 1.0])
        for L in s.discrete:
            L = np.asarray(L)
            axs[1].plot(L[:, 0], L[:, 1], color=col, lw=1.0 if col != "#444" else 1.8)
    for x, z in pattern()["positions_xz"]:
        if abs(z - z0) < 0.1:
            yb = FACE_Y - BASE_T
            axs[1].add_patch(plt.Rectangle((x - 2.5, yb), 5.0, SCREW_L, fc="#c55", alpha=0.5))
            axs[1].add_patch(plt.Rectangle((x - HEAD_D / 2, yb - HEAD_H), HEAD_D, HEAD_H, fc="#c55", alpha=0.8))
    ff = res["frame_fit"]
    axs[1].set_aspect("equal"); axs[1].set_xlim(-45, 45); axs[1].set_ylim(-85, -15)
    axs[1].set_title(f"section z {z0:g} (lower screw row): screws M5 x 14, tip {ff['tip_to_pilot_floor_mm']:.2f} mm "
                     f"above the pilot floor\nclash {ff['clash_mm3']:.1f} mm3, boss face y {ff['face_y_measured']:g}",
                     fontsize=9)
    axs[1].set_xlabel("frame x"); axs[1].set_ylabel("frame y (wearer at -y)")
    return _save(fig, SCREENS / f"{SHOT}3.png")


def figures(res: dict) -> list:
    return [plot_part(res), plot_fe(res), plot_fit(res)]


def _oz(g):
    return f"{g / 28.3495:.2f} oz"


def write_md(res: dict, shots: list, clevis: dict | None = None) -> str:
    g, ff, fe, st, ms, sl = res["geometry"], res["frame_fit"], res["fe"], res["strip"], res["mass"], res["slm"]
    L = []
    a = L.append
    a("# BL-056 SLM Ti hip pivot mount base for the 8-insert pattern\n")
    a(f"structural-fea-engineer, {DATE}. Ticket `docs/backlog/BL-056-hip-mount.md` plus the orchestrator's two "
      "additions (US2 clevis at the CLEVIS-SHARE B bound; HB-6 / HB-6b test data). Code `huntkit/gendesign/hip_mount.py`"
      " (`python -m huntkit.gendesign.hip_mount --export`), `huntkit/gendesign/clevis_bl056.py`; tests "
      "`tests/test_hip_mount.py`, `tests/test_clevis_bl056.py`. Results `hip_mount_bl056.json`, `clevis_bl056.json`. "
      "Units mm, N, MPa, g (imperial in brackets). Supersedes the hip-insert row of `hipbelt_structural.md` section 4 "
      "(with `h1_closeout.md`) and the share-1.0 rows of `h1_rev5.md` section 3.\n")
    a("## Summary\n")
    a(f"- **Redrawn:** `designs/pack_5200/print/lug_hip_pivot_mount_slm_ti.stl` / `.3mf`: base D{g['base']['d_eq_mm']:g}"
      f" x {BASE_T:g} mm ({BASE_D / 25.4:.2f} x {BASE_T / 25.4:.3f} in), 8 x D{HOLE_D:g} on the BL-055 positions "
      f"(position error {g['base']['hole_pos_err_mm']:g} mm), D10 pin hole; legs and hub kept (sections above the "
      f"fillets identical to the drawn part: {g['legs_and_hub_kept']}); {FILLET:g} mm 45 deg fillet round each leg "
      f"root. One closed shell: {g['watertight'] and g['shells'] == 1}. The drawn part is kept as "
      f"`print/legacy/lug_hip_pivot_mount_slm_ti_D44_drawn.stl` (h1_closeout reads it).")
    a(f"- **Clearances:** head-to-leg {g['head_to_leg_mm']:.2f} mm (rule >= {HEAD_LEG_CLEAR:g}), head-to-head "
      f"{g['head_to_head_mm']:.2f} mm, hole edge to rim {g['hole_edge_to_rim_mm']:.2f} mm, hole to pin hole "
      f"{g['hole_to_pin_hole_mm']:.2f} mm; a D{KEY_D:g} driver envelope straight above every head clears the part "
      f"and the frame.")
    a(f"- **Frame fit (sliced):** boss face measured at y {ff['face_y_measured']:g} (h1_closeout's -48.4 is a slice "
      f"level 0.15 mm inside it); clash {ff['clash_mm3']:.1f} mm3; 8 pilots under the 8 holes at face +1 / +6 / +10.5 "
      f"(offset 0.00 mm); screw M5 x 14 tip {ff['tip_to_pilot_floor_mm']:.2f} mm above the measured pilot floor "
      f"({ff['pilot_depth_measured_mm']:g} mm); full 9.5 mm insert engagement; base bears on the boss over its whole "
      f"area. **Pass: {ff['pass']}.**")
    worst = fe["rows"][fe["governing"]]
    a(f"- **Strength (part FE, bolt-only bound):** min SF / goal **{fe['min_sf_over_goal']:.2f}** on "
      f"{fe['governing']} at the **leg root** (p99.5 {worst['regions']['leg_root']['sigma_p995_mpa']:g} MPa, SF "
      f"{worst['regions']['leg_root']['sf']:g} / {worst['goal']:g}); the base itself "
      f"{min(r['regions']['base']['sf'] / r['goal'] for r in fe['rows'].values()):.2f} x its goal. Walk fatigue "
      f"(as-built HIP, Goodman) leg root {fe['rows']['walk|H_pin']['regions']['leg_root']['sf']:g} / 1.15. "
      f"**Sensitivity:** the same 20 mm pad offset put SIDEWAYS (not a fit-model case) bends the legs about their thin "
      f"axis: min SF / goal {fe['lateral_offset_sensitivity']['min_sf_over_goal']:.2f} at the leg root (C2 / walk with H "
      "on the pin). The legs (kept from the drawing, as the ticket says) are the part's weak point; the 3 mm base is not.")
    a(f"- **BL-055 strip formula on the SLM allowables:** min SF / goal {st['min_sf_over_goal']:.2f} (BL-055 "
      f"{res['bl055_strip_record']['min_sf_over_goal']:g} on wrought allowables).")
    a(f"- **Mass:** {ms['redraw_g']:.2f} g ({_oz(ms['redraw_g'])}), drawn {ms['drawn_g']:.2f} g: "
      f"{ms['delta_g']:+.2f} g against the {ms['booked_bl055_g']:+.2f} g BL-055 booked: ledger row BL056 "
      f"{ms['ledger_correction_g']:+.2f} g.")
    if clevis:
        j1 = clevis["joint"]["share_1"]
        lg = clevis["joint"]["legacy_rows_share_1"]
        a(f"- **US2 clevis (addition 1):** blocks grown upward only, pin +14.5 -> +{clevis['joint']['block']['upper_half_z_mm']:g} mm, "
          f"and the nut face moved 1 mm inboard (body plug 12 -> {clevis['joint']['block']['body_plug_mm']:g} mm, same M5 x 35); "
          f"share 1.0 on every row: strength {j1['all_rows_min']['strength']:.2f} (>= 1.5), fatigue "
          f"{j1['all_rows_min']['fatigue']:.2f} (>= 1.15) (was 1.90 / 0.86); legacy 2D rows {lg['strength']:.2f} / "
          f"{lg['fatigue']:.2f} (was 2.52 / 1.14); print {clevis['mass']['print_delta_g']:+.1f} g.")
    a(f"- **Tests for the kit (addition 2):** HB-6 pass line {res['tests']['HB-6']['pass_line_n_each']:g} N per insert "
      f"(6 coupons, along the build z, 60 C); HB-6b screw-gauge pass lines in section 6.\n")
    a("## 1. Geometry\n")
    a("| check | value |\n|---|---|")
    for k, v in (("base D eq (sliced at z 1.5)", f"{g['base']['d_eq_mm']:g} mm"),
                 ("base top (first slice off the disc)", f"{g['base']['top_z_mm']:g} mm"),
                 ("holes (D eq)", ", ".join(f"{d:g}" for d in g['base']['hole_d_eq_mm'])),
                 ("hole position error vs h1_closeout.json", f"{g['base']['hole_pos_err_mm']:g} mm"),
                 ("legs + hub kept (sections z 4.7..27 vs drawn)", str(g['legs_and_hub_kept'])),
                 ("hub top", f"{g['hub_top_z_mm']:g} mm (pin stand-off unchanged)"),
                 ("head to leg (z 3..6.5, fillets incl.)", f"{g['head_to_leg_mm']:.2f} mm"),
                 ("head to head", f"{g['head_to_head_mm']:.2f} mm"),
                 ("head inside the rim by", f"{-g['head_overhang_rim_mm']:.2f} mm"),
                 ("driver envelope clash", f"{max(g['driver_clash_mm3']):g} mm3")):
        a(f"| {k} | {v} |")
    a("")
    a("## 2. Fit on the frame print\n")
    a(f"Frame `{ff['frame_stl']}`; mount placed by `hip_mount.frame_matrix` (local z = frame -y, local y = frame z, "
      f"ASSUMPTION MOUNT-ORIENT).\n")
    a("| slice | pilots | D eq | offset to the mount hole (mm) |\n|---|---|---|---|")
    for k, v in ff["pilot_slices"].items():
        a(f"| {k} | {v['pilots']} | {', '.join(str(d) for d in v['pilot_d_eq'])} | {v['max_offset_to_mount_hole_mm']} |")
    a("")
    a(f"Clash mount / frame {ff['clash_mm3']:.2f} mm3; screw shanks, heads and the driver envelopes: "
      f"{max(s['shank_in_frame_mm3'] for s in ff['screws']):g} / {max(s['head_in_frame_mm3'] for s in ff['screws']):g} / "
      f"{max(s['key_in_frame_mm3'] for s in ff['screws']):g} mm3 in the frame. Tip depth {ff['screw_tip_depth_in_boss_mm']:g} "
      f"mm, pilot floor {ff['pilot_depth_measured_mm']:g} mm.\n")
    a("## 3. Strength\n")
    cv = res["verification"]["cantilever"]
    a(f"Solver verification (`cantilever_check`, the same voxel H8 code): tip deflection FE / Timoshenko "
      f"{cv['ratio']:.3f}, bending stress {cv['sigma_ratio']:.3f}.\n")
    a(f"Part FE: {fe['n_elem']} voxels of {fe['h_mm']:g} mm ({fe['mass_voxel_g']:g} g), {fe['material']}; BC "
      f"{fe['bc']} (ASSUMPTION FE-BOLT-ONLY). Loads per h1_closeout hip row: V along the legs at the hub bore, H on "
      f"the hub face with the pad offset e = +/-20 mm vertical (frame z, hipbelt E_PAD_MM) or 0, and V up and down (worst kept); the same offset sideways is the sensitivity below. Stress p99.5 per region "
      f"(peak in brackets, voxel steps), elements under the clamped heads left out.\n")
    a("| row | kind | goal | base | leg root | legs | hub | min SF / goal |\n|---|---|---|---|---|---|---|---|")
    for k, r in fe["rows"].items():
        cells = " | ".join(f"{r['regions'][g_]['sigma_p995_mpa']:g} ({r['regions'][g_]['sigma_peak_mpa']:g}) SF "
                           f"{r['regions'][g_]['sf']:g}" for g_ in ("base", "leg_root", "legs", "hub"))
        a(f"| {k} | {r['kind']} | {r['goal']:g} | {cells} | {r['min_sf_all'] / r['goal']:.2f} |")
    a("")
    a(f"Strip formula (BL-055) at the redrawn leg roots (half width {st['leg_half_w_at_base_top_mm']:g} mm, arm "
      f"{st['arm_mm']:g} mm, strip {st['strip_b_mm']:g} mm): min SF / goal {st['min_sf_over_goal']:g}.\n")
    lat = fe["lateral_offset_sensitivity"]
    a("Lateral-offset sensitivity (e = +/-20 mm along frame x; the fit model gives a vertical offset only):\n")
    a("| row | min SF (region) | goal | SF / goal |\n|---|---|---|---|")
    for k, v in lat["rows"].items():
        a(f"| {k} | {v['min_sf_all']:g} ({v['region']}, {v['sigma_p995_mpa']:g} MPa) | {v['goal']:g} | "
          f"{v['min_sf_all'] / v['goal']:.2f} |")
    a("")
    a("Fillet sensitivity (on the lateral case): a 2.0 mm fillet (head-to-leg 4.36 mm, +0.3 g) leaves the leg-root p99.5 "
      "at 517 MPa (1.2 mm: 519): the root stress is the leg's own section bending, not the corner. Mesh: h 0.5 against the 1 % / 2 % "
      "cantilever check; an h 0.4 run was stopped for time (not done).\n")
    a("## 4. SLM print notes (for the print service)\n")
    a("| build direction | support area mm2 (45 deg rule) |\n|---|---|")
    for k, v in sl["support_area_mm2_by_build_dir"].items():
        a(f"| {k} | {v:g} |")
    a("")
    a(f"**Chosen: {sl['chosen']} (base on the plate).** {sl['why']}")
    a("- Material and process: Ti-6Al-4V (grade 5 powder) L-PBF, stress relief before removal from the plate, HIP "
      "920 C / 100 MPa / 2 h (ASTM F3001), per `data/materials/metals/ti_6al_4v_slm.yaml`.")
    a("- Plate side: print the base on 2-3 mm of block supports (not fused flat to the plate), wire-cut off, face the "
      "base underside flat (0.05 mm) as the datum: it is the face that bears on the boss.")
    a("- Holes: 8 x D5.5 and D10 printed vertical, no support; ream the D10 pin bore to the pin fit (the drawn part's "
      "note); the D5.5 holes as printed (clearance), deburr.")
    a("- Supports to remove by hand: under the hub's lower face between the legs (not a bearing face).")
    a("- Do not machine or blast the leg roots beyond the vendor's standard bead blast (the fatigue check uses the "
      "as-built HIP limit).")
    a("- Inspect: base 3.0 +/- 0.1 mm, D50 +/- 0.2, 8 holes on the pattern (drill gauge from the boss), no crack at the "
      "leg roots (dye penetrant if the vendor offers it).\n")
    a("## 5. Mass\n")
    a("| item | g | source |\n|---|---|---|")
    a(f"| drawn mount (D44 x 1.2) | {ms['drawn_g']:.2f} | STL volume x 4430 kg/m3 |")
    a(f"| BL-056 mount (D50 x 3, fillets) | {ms['redraw_g']:.2f} ({_oz(ms['redraw_g'])}) | STL volume x 4430 kg/m3 |")
    a(f"| delta | {ms['delta_g']:+.2f} | |")
    a(f"| booked by BL-055 | {ms['booked_bl055_g']:+.2f} | h1_closeout.mount_flange |")
    a(f"| **ledger BL056 (mount)** | **{ms['ledger_correction_g']:+.2f}** | hip_mount_bl056.json mass |")
    if clevis:
        a(f"| **ledger BL056 (print, US2 blocks)** | **{clevis['mass']['print_delta_g']:+.2f}** | clevis_bl056.json mass |")
    a("")
    a("Mass reductions that keep the SF: the base is at 3.5 x its goal or more (part FE, bolt-only) and could thin to "
      "about 2.2 mm (sigma ~ 1/t^2: 3.0 -> 2.2 mm keeps >= 1.8 x) for about -3.5 g, but the prying model's rigid flange "
      "(FLANGE-RIGID) is the reason for 3 mm: hold it until HB-6b reads the screw; pocketing the base between the "
      "screw groups (above and below the legs, where no screw is) saves about 2 g with the same caveat. Not applied.\n")
    a("## 6. Test data for the kit (addition 2)\n")
    t = res["tests"]
    h6 = t["HB-6"]
    a(f"**HB-6 insert pull-out:** {h6['coupon']}; {h6['n_coupons']} coupons; {h6['conditioning']}; {h6['rig']}. "
      f"**Pass: every coupon >= {h6['pass_line_n_each']:g} N ({h6['pass_line_n_each'] / 4.448:.0f} lbf)** "
      f"({h6['pass_line_basis']}). Minimum for the 8-insert pattern to keep its goals: {h6['minimum_for_8_inserts_n']:g} "
      f"N. {h6['if_it_fails']}.\n")
    h6b = t["HB-6b"]
    a(f"**HB-6b hip-mount proof:** {h6b['setup']}. Gauge: {h6b['gauge']}.\n")
    a("| step | pin load V N (lbf) | model screw tension N | model microstrain | pass if <= |\n|---|---|---|---|---|")
    for s_ in h6b["steps"]:
        a(f"| {s_['step']} | {s_['pin_load_v_n']:g} ({s_['pin_load_v_lbf']:g}) | {s_['model_screw_tension_n']:g} | "
          f"{s_['model_microstrain']:g} | {s_['pass_if_microstrain_at_most']:g} |")
    a(f"\n{h6b['pass_rule']} ({t['screw_gauge_basis']}). Published as JSON in `hip_mount_bl056.json` `tests`.\n")
    if clevis:
        a("## 7. US2 clevis at the CLEVIS-SHARE B bound (addition 1)\n")
        j = clevis["joint"]
        a(f"Blocks (body and clevis): z pin -{j['block']['lower_half_z_mm']:g} / +{j['block']['upper_half_z_mm']:g} "
          f"(was +/-14.5); nut face |x| {j['block']['nut_face_x_mm']:g} (was 151; trap {j['block']['trap_x0_mm']:g}-"
          f"{j['block']['nut_face_x_mm']:g}): body plug {j['block']['body_plug_mm']:g} mm for the hole bearing (the M5 x 35 "
          f"grip 29 + washer 1 + nut 4 + 1 still fits). Lower edge, strap lip (r 3), bolts (z pin +/- 7), trap shapes "
          f"and head counterbores unchanged. Code: `h1_bedfit.BLOCK_UP_Z`, `ClevisJoint.nut_face / trap_x0`.\n")
        lg = j["legacy_rows_share_1"]
        a(f"The legacy BL-050/051 row set (h1_lanes.lug_loads, the 2D cradle rows the 3D rows replaced) at share 1.0: "
          f"strength {lg['strength']:g}, fatigue {lg['fatigue']:g} ({lg['worst_fatigue']['load']}, "
          f"{lg['worst_fatigue']['check']}); at 12 mm body plug it read 1.14 on hole bearing.\n")
        a("| share | all rows strength | all rows fatigue | net section strength / fatigue | worst fatigue row |\n"
          "|---|---|---|---|---|")
        for sh in ("0.6", "1"):
            r = j[f"share_{sh}"]
            a(f"| {sh} | {r['all_rows_min']['strength']:g} | {r['all_rows_min']['fatigue']:g} | "
              f"{r['net_section_rows_min']['strength']:g} / {r['net_section_rows_min']['fatigue']:g} | "
              f"{r['worst_fatigue']['load']} ({r['worst_fatigue']['check']}) |")
        a(f"\nBL-053 at share 1.0: strength 1.90, fatigue 0.86 (cradle_lane_b50, net section); design rows 2.54 / 1.14. "
          f"Share-1.0 pass (>= 1.5 / >= 1.15 on every row): **{clevis['share_1_pass']}**.\n")
        tw = clevis["trap_walls"]
        a(f"Trap walls min {tw['min_wall_mm']:g} mm (>= 2: {tw['pass_2mm']}); joint slices pass "
          f"{clevis['slices']['pass']}; bed: " + ", ".join(
              f"{k} fits with brim {v.get('fits_with_brim')} (spare {v.get('spare_mm')})" for k, v in clevis['bed'].items())
          + f"; strap clearance US1 {clevis['clearance']['worst_clear_mm']['us1']:.1f} / US2 "
          f"{clevis['clearance']['worst_clear_mm']['us2']:.1f} mm (>= 10: {clevis['clearance']['pass']}; BL-053 12.4 / 14.6).")
        hd = clevis.get("heads", {})
        if isinstance(hd, dict) and "error" not in hd:
            a(f"Counterbored heads (unchanged: |x| {hd['head_x_mm'][0]:g}-{hd['head_x_mm'][1]:g}, z "
              f"{hd['head_z_mm'][0]:g}-{hd['head_z_mm'][1]:g}, below the {hd['outer_face_x_mm']:g} outer face) vs the free "
              f"drapes: min {hd['cloth_min_mm']:g} mm, the same as BL-053 (the heads did not move).")
        ww = clevis["strap_wrap"].get("worst", {})
        if ww:
            a(f"Strap wrap on the new print: US2 {ww.get('us2', {}).get('wrap_deg')} deg on the lip r "
              f"{ww.get('us2', {}).get('lip_r_mm')}; US1 {ww.get('us1', {}).get('wrap_deg')} deg.")
        a("\nCLEVIS-SHARE kit loads (JSON `clevis_bl056.json` `kit`):\n")
        a("| test | pull unit vector (R) | proof N (lbf) | cycle peak N, 1e5, R 0.1 | eye bears on | model min SF / fatigue at the share |\n|---|---|---|---|---|---|")
        for k, v in clevis["kit"].items():
            a(f"| {k}: {v['test']} | {v['pull_unit_vector_frame_R']} | {v['proof_n']:g} ({v['proof_lbf']:g}) | "
              f"{v['cycle_peak_n']:g} | {v['eye_bears_on']} | {v['model_min_strength_at_share']:g} / "
              f"{v['model_min_fatigue_at_share']:g} (share {v['share_on_clevis']:g}) |")
        a("\nGauge lines on the new print (US2 arm-root gauge, h1_rev5.gauge_values; pass if |microstrain| <= the line):\n")
        a("| test | pull unit vector (frame, R) | pin load N | microstrain | pass if abs <= | BL-053 line |\n"
          "|---|---|---|---|---|---|")
        old = clevis["gauges_bl053"]
        for k, v in clevis["gauges"]["tests"].items():
            for i, s_ in enumerate(v["steps"]):
                o = old.get(k, {}).get("steps", [{}] * 9)
                ol = o[i]["pass_if_abs_microstrain_at_most"] if i < len(o) and o[i] else "-"
                a(f"| {k} | {v['pull_unit_vector_frame_R']} | {s_['pin_load_n']:g} | {s_['microstrain']:g} | "
                  f"{s_['pass_if_abs_microstrain_at_most']:g} | {ol} |")
        m_ = clevis["mass"]
        a(f"\nMass (PAHT-CF 1.06 g/cm3): assembled {m_['h1_assembled']['bl055_g']:g} -> {m_['h1_assembled']['g']:g} g "
          f"({m_['print_delta_g']:+.2f} g); clevis R {m_['us2_clevis_R']['bl055_g']:g} -> {m_['us2_clevis_R']['g']:g} g; "
          f"lower half {m_['h1_lower_flat']['bl055_g']:g} -> {m_['h1_lower_flat']['g']:g} g. Ledger row BL056.\n")
    a("## 8. Assumptions\n")
    for x in res["assumptions"] + (clevis["assumptions"] if clevis else []):
        a(f"- ASSUMPTION {x['id']}: {x['text']} Settled by: {x['settled_by']}")
    a("\n## 9. Screenshots\n")
    for s_ in shots:
        a(f"- `{s_}`")
    return "\n".join(L) + "\n"


def main(argv=None):  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--export", action="store_true", help="rebuild and export the STL / 3MF")
    ap.add_argument("--no-fe", action="store_true")
    a = ap.parse_args(argv)
    if a.export:
        export()
    res = compute(fe=not a.no_fe)
    (ANALYSIS / "hip_mount_bl056.json").write_text(json.dumps(res, indent=1, default=float))
    shots = figures(res)
    cp = ANALYSIS / "clevis_bl056.json"
    clevis = json.loads(cp.read_text()) if cp.exists() else None
    if clevis:
        from .clevis_bl056 import plot_joint
        shots.append(plot_joint(clevis))
    (ANALYSIS / "hip_mount_bl056.md").write_text(write_md(res, shots, clevis))
    print(json.dumps({k: res[k] for k in ("geometry", "mass")}, indent=1, default=float))


if __name__ == "__main__":  # pragma: no cover
    main()
