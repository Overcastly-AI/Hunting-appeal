"""BL-047 (2): the pawl on the H1 print: pivot bore, cheek bosses, fore-wall window, and a low-profile pawl that fits.

Found by BL-046: the H1 print has no pivot bore (PRODUCTION.md op 2 reams one), and the FDM pawl
(``printables.spring_pawl``) stands 14 mm (spring tang) / 13.5 mm (cord eye) off its tooth face against the 9.3 mm swing
zone. A window alone does not fix it: swung to release (``PAWL_LIFT_DEG``), the old pawl's eye reaches 17.9 mm, 4.9 mm
proud of the housing's fore face where the yoke passes (ASSUMPTION YOKE-PATH, BL-046). So:

* **Low-profile pawl** (``lp_profile``): same 4 mm pivot, same two teeth, same 32 mm arm, arm 7.5 high, spring tang cut
  to 10.5, cord hole moved into the arm end, hub flattened 0.6 mm above the tooth face behind the pivot (the old hub
  dips 1 mm below the tooth face, onto the rack's tooth tips). Swept to release it stays 11.8 mm off the tooth face:
  inside the housing's fore face (12.99) with 0.5 mm to spare. FDM 16 mm wide (PAHT-CF) and SLM 12 mm (Ti) files.
* **Pivot bore** through both side walls (cheeks), 4 mm fore of the rack's tooth tips, 20 mm below the pawl line
  (teeth centred on z 520): printed 7.6, reamed 8.0 for the 304 sleeve (PRODUCTION.md op 2).
* **Cheek bosses** to z 491.5 under the bore (the housing starts at z 496; 4 mm of wall under the 8 mm bore).
* **Fore-wall window**: the swept pawl + 0.5 mm, opened through the fore wall over the pawl's width + 1 mm a side;
  the release cord leaves through it.

``add_pawl(man)`` is called by ``frame_h1.print_mesh`` after the BL-046 channel; ``check_stl_pawl`` slices the exported
STL through the full pawl rotation. Units mm, N.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PRINT_DIR = REPO / "designs" / "pack_5200" / "print" / "frame_h1"

PIVOT_D_PIN = 4.1            # printables.spring_pawl pivot hole (4 mm pin, slip)
PIVOT_PX, PIVOT_PY = 4.0, 4.0   # pivot in pawl coordinates (printables.spring_pawl)
TEETH_PX = 24.0              # centre of the two teeth (px 20..28)
ARM_H = 7.5                  # LP arm height off the tooth face (old 8)
TANG = (8.0, 12.0, 10.5)     # LP spring tang px 8..12 up to py 10.5 (old 14)
CORD_HOLE = (29.0, 3.75, 2.6)   # LP cord hole (px, py, d): in the arm end (old eye at (30, 10) r 3.5, to py 13.5)
HUB_FLAT_PY = 0.6            # LP hub / arm behind the pivot flattened to py >= 0.6 (old hub to py -1.0)
PAWL_LIFT_DEG = 10.0         # ASSUMPTION PAWL-LIFT: release swing; the teeth clear the rack tips by 0.5 mm at 7.9 deg
FACE_CLEAR = 0.5             # swept pawl to printed material
BORE_PRINT_D = 7.6           # printed, reamed to 8.0 (PRODUCTION.md op 2: 304 sleeve OD 8.0 / ID 4.2 / 8 long)
BORE_REAM_D = 8.0
BOSS_Z_LO = 491.5            # cheek boss bottom: 4.0 mm of wall under the reamed bore at z 500 (bore bottom 496)
BOSS_Y_REL = (-28.99, -11.0)   # boss fore-aft extent relative to the spine axis (fore face .. behind the bore)
WINDOW_HALF_X = None         # set from the pawl width (FDM 16) + 1 mm a side in window_section()

ASSUMPTIONS = {
    "PAWL-LIFT": ("The release cord swings the pawl 10 deg about its pin (7.9 deg lifts the nearer tooth tip 0.5 mm clear "
                  "of the rack tips, + 2 deg).", "Pawl dry fit in the first print: pull the cord to the stop, rack slides."),
    "PAWL-PLACE": ("Pivot 20 mm below the teeth (pawl line z 520 -> pin z 500), pin 4 mm fore of the rack tooth tips "
                   "(printables.spring_pawl pin at (4, 4) with the tooth face 0.15 mm above the rack tips).",
                   "Pawl dry fit: teeth seat in the rack with the pin in its sleeves."),
    "PAWL-SPRING": ("The LP pawl's spring is a 0.5 mm music-wire torsion spring on the pin beside the pawl (3 mm a side in "
                    "the 22 mm channel), one leg on the 10.5 mm tang, the other on the window's lower edge; the old "
                    "14 mm tang does not fit the housing.", "Pawl dry fit + 100 release cycles by hand."),
    "PAWL-FDM-STRENGTH": ("The LP pawl keeps the teeth, the pin and a 7.5 mm arm (old 8): the rack check (printables."
                          "rack_check, rating 5328 N) is on the teeth and is unchanged; the arm only carries the spring.",
                          "Rack/pawl pull test in the test kit (unchanged)."),
}


# ================================================================================== pawl
def lp_profile():
    """Low-profile pawl profile (shapely, pawl coordinates: px along the rack, py off the tooth face)."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    arm = box(0, 0, 32, ARM_H)
    hub = Point(PIVOT_PX, PIVOT_PY).buffer(5.0, 48)
    teeth = []
    pitch, depth, top, run = 4.0, 2.0, 1.4, 2.0 * np.tan(np.radians(20))
    for i in range(2):
        a = 20 + i * pitch
        bot = pitch - top - 2 * run
        teeth.append(Polygon([(a, 0), (a + bot / 2, 0), (a + bot / 2 + run, -depth + 0.15),
                              (a + bot / 2 + run + top, -depth + 0.15), (a + bot / 2 + 2 * run + top, 0),
                              (a + pitch, 0)]).buffer(0.01))
    tang = box(TANG[0], ARM_H - 0.5, TANG[1], TANG[2])
    body = unary_union([arm, hub, tang] + teeth)
    body = body.difference(box(-2, -3, PIVOT_PX + 0.5, HUB_FLAT_PY))        # flat behind / under the pivot
    body = body.difference(box(PIVOT_PX + 0.5, -3, 10.0, 0.0))              # hub front: no lower than the tooth face
    body = body.difference(Point(PIVOT_PX, PIVOT_PY).buffer(PIVOT_D_PIN / 2, 32))
    body = body.difference(Point(CORD_HOLE[0], CORD_HOLE[1]).buffer(CORD_HOLE[2] / 2, 24))
    body = body.buffer(0.3, 8).buffer(-0.3, 8)
    if body.geom_type != "Polygon":
        body = max(body.geoms, key=lambda g: g.area)
    return body


def old_profile():
    """printables.spring_pawl's profile (for the before / after comparison)."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    arm = box(0, 0, 32, 8)
    hub = Point(4, 4).buffer(5.0, 48)
    eye = Point(30, 10).buffer(3.5, 32).union(box(26.5, 6, 33.5, 10))
    tang = box(8, 8, 12, 14)
    return unary_union([arm, hub, eye, tang])


def rotated(poly, deg: float):
    from shapely import affinity
    return affinity.rotate(poly, deg, origin=(PIVOT_PX, PIVOT_PY))


def swept(poly, deg_max: float = PAWL_LIFT_DEG, n: int = 21):
    from shapely.ops import unary_union
    return unary_union([rotated(poly, d) for d in np.linspace(0.0, deg_max, n)])


def max_py(poly, deg_max: float = PAWL_LIFT_DEG) -> float:
    return float(swept(poly, deg_max).bounds[3])


def lift_at_teeth(deg: float) -> float:
    """Rise of the nearer tooth tip (px 21) at a swing of ``deg``."""
    p = np.array([21.0 - PIVOT_PX, -1.85 - PIVOT_PY])
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return float(c * p[1] + s * p[0] - p[1])


# ================================================================================== placement (housing coords)
def frame_place() -> dict:
    """Pawl coordinates -> (y_rel to the spine axis, z): py fore of the tooth face, px up the crown axis."""
    from . import h1_spine_channel as SC
    c = SC.channel_dims()
    tips = c["rack_tips_rel"]                      # rack tooth tips, y_rel (fore -)
    face = tips - 0.15                             # pawl tooth face when engaged
    z_piv = SC.PAWL_Z - (TEETH_PX - PIVOT_PX)
    return {"face_y_rel": face, "z_pivot": z_piv, "pivot_y_rel": face - PIVOT_PY,
            "housing_fore_rel": SC.housing_dims()["fore_rel"], "channel_fore_rel": c["fore_rel"],
            "zone_py": face - c["fore_rel"], "face_py": face - SC.housing_dims()["fore_rel"]}


def to_yz(poly):
    """Pawl-coordinate polygon -> (y_rel, z) polygon in the housing plane."""
    from shapely import affinity
    P = frame_place()
    # (px, py) -> (y_rel, z) = (face - py, z_piv + (px - PIVOT_PX))
    return affinity.affine_transform(poly, [0.0, -1.0, 1.0, 0.0, P["face_y_rel"], P["z_pivot"] - PIVOT_PX])


def window_section(width: float = 16.0):
    """(y_rel, z) window through the fore wall: the swept LP pawl + clearance, where it passes the channel's fore face,
    run out through the wall."""
    from shapely.geometry import box
    P = frame_place()
    sw = to_yz(swept(lp_profile())).buffer(FACE_CLEAR, 8)
    beyond = sw.intersection(box(-80, 400, P["channel_fore_rel"] + 0.01, 600))
    if beyond.is_empty:
        return None, width / 2 + 1.0
    z0, z1 = beyond.bounds[1], beyond.bounds[3]
    win = box(P["housing_fore_rel"] - 6.0, z0, P["channel_fore_rel"] + 0.5, z1)
    return win, width / 2 + 1.0


def _prism_x(poly_yz, x0: float, x1: float):
    """manifold3d solid: (y_rel, z) polygon extruded along x from x0 to x1, y sheared onto the spine axis."""
    import manifold3d as m3d
    from shapely.geometry.polygon import orient
    from . import h1_spine_channel as SC
    pts = np.asarray(orient(poly_yz, 1.0).exterior.coords)[:-1]
    cs = m3d.CrossSection([pts.tolist()])
    m = m3d.Manifold.extrude(cs, x1 - x0).translate((0.0, 0.0, x0))     # (a=y_rel, b=z, c=x)
    s = SC.axis_slope()
    y0 = float(SC.axis_y(0.0))
    M = np.array([[0.0, 0, 1.0, 0], [1.0, s, 0, y0], [0, 1.0, 0, 0]])     # x=c, y=a + s b + y0, z=b
    return m.transform(M)


def bore_solid(d: float = BORE_PRINT_D, half_x: float = 30.0):
    from shapely.geometry import Point
    P = frame_place()
    return _prism_x(Point(P["pivot_y_rel"], P["z_pivot"]).buffer(d / 2, 64), -half_x, half_x)


def boss_solids():
    from shapely.geometry import box
    from . import h1_spine_channel as SC
    from . import h1_spine_channel as _sc
    P = frame_place()
    hw = SC.HOUSING_HALF_W
    xin = SC.channel_dims()["half_x"]
    sec = box(BOSS_Y_REL[0], BOSS_Z_LO, BOSS_Y_REL[1], P["z_pivot"] + 8.0).buffer(-1.0).buffer(1.0, 8)
    return [_prism_x(sec, xin, hw), _prism_x(sec, -hw, -xin)], _sc


def add_pawl(man, stats: dict | None = None):
    """Cheek bosses on, then the pivot bore and the fore-wall window cut. Returns the manifold."""
    v0 = man.volume()
    bosses, _ = boss_solids()
    for b in bosses:
        man = man + b
    v1 = man.volume()
    man = man - bore_solid()
    win, hx = window_section()
    if win is not None:
        man = man - _prism_x(win, -hx, hx)
    v2 = man.volume()
    if stats is not None:
        stats.update({"boss_mm3": v1 - v0, "cut_mm3": v1 - v2, "net_mm3": v2 - v0, "net_g": (v2 - v0) * 1.06e-3})
    return man


# ================================================================================== STL checks
def check_stl_pawl(path_or_mesh, width: float = 16.0, step_deg: float = 1.0) -> dict:
    """Slice the exported STL: (1) x planes across the pawl's width, every ``step_deg`` of the swing 0 -> PAWL_LIFT_DEG:
    least distance from the LP pawl section to printed material (>= FACE_CLEAR - 0.05 simplify tolerance) and the
    pawl never past the housing's fore face; (2) x planes through each cheek: the pivot bore is a clear hole of at least
    the printed diameter and the wall round it >= 2 mm; (3) the old pawl through the same swing for comparison."""
    import trimesh
    from . import h1_fairleads as HF
    from shapely.geometry import Point
    mesh = path_or_mesh if not isinstance(path_or_mesh, (str, Path)) else trimesh.load(str(path_or_mesh))
    P = frame_place()
    xs = np.arange(-width / 2 + 0.5, width / 2 - 0.5 + 1e-9, 2.5)
    secs = {float(x): HF._xplane(mesh, float(x)) for x in xs}
    rows = []
    from . import h1_spine_channel as SC

    def shift(poly, z):          # sheared axis: y_rel -> absolute y at the section
        from shapely import affinity
        s = SC.axis_slope()
        return affinity.affine_transform(poly, [1.0, s, 0.0, 1.0, float(SC.axis_y(0.0)), 0.0])
    for deg in np.arange(0.0, PAWL_LIFT_DEG + 1e-9, step_deg):
        for nm, prof in (("lp", lp_profile()), ("old", old_profile())):
            pg = shift(to_yz(rotated(prof, float(deg))), 0.0)
            d = min(float(pg.distance(S)) if not pg.intersects(S) else -float(pg.intersection(S).area)
                    for S in secs.values())
            rows.append({"deg": float(deg), "pawl": nm, "min_dist_mm": round(d, 3),
                         "max_py": round(float(rotated(prof, float(deg)).bounds[3]), 2)})
    lp = [r for r in rows if r["pawl"] == "lp"]
    old = [r for r in rows if r["pawl"] == "old"]
    # bore in the cheeks
    from . import h1_spine_channel as SC2
    cin, hw = SC2.channel_dims()["half_x"], SC2.HOUSING_HALF_W
    bores = []
    yc = float(SC.axis_y(P["z_pivot"])) + P["pivot_y_rel"]
    for x in (-(cin + hw) / 2, -(cin + 1.0), -(hw - 1.0), (cin + 1.0), (cin + hw) / 2, (hw - 1.0)):
        S = HF._xplane(mesh, float(x))
        hole = Point(yc, P["z_pivot"]).buffer(BORE_PRINT_D / 2 - 0.1, 64)
        ring = Point(yc, P["z_pivot"]).buffer(BORE_PRINT_D / 2 + 2.0, 64).difference(
            Point(yc, P["z_pivot"]).buffer(BORE_PRINT_D / 2 + 0.1, 64))
        bores.append({"x": round(float(x), 2), "bore_clear": bool(hole.intersection(S).area < 1e-3),
                      "wall_2mm_full": round(float(ring.intersection(S).area / ring.area), 3)})
    res = {"swing_deg": PAWL_LIFT_DEG, "lp_min_dist_mm": min(r["min_dist_mm"] for r in lp),
           "old_min_dist_mm": min(r["min_dist_mm"] for r in old), "rows": rows, "bores": bores,
           "lp_max_py": max_py(lp_profile()), "old_max_py": max_py(old_profile()),
           "face_py": round(P["face_py"], 2), "zone_py": round(P["zone_py"], 2),
           "lift_at_teeth_mm": round(lift_at_teeth(PAWL_LIFT_DEG), 2)}
    res["pass"] = bool(res["lp_min_dist_mm"] >= FACE_CLEAR - 0.05 - 0.05 and all(b["bore_clear"] for b in bores)
                       and all(b["wall_2mm_full"] > 0.97 for b in bores) and res["lp_max_py"] < res["face_py"])
    return res


# ================================================================================== strength
def pawl_force() -> dict:
    """Largest factored pawl force (y, z) over the real-crown beam rows of the three crown kits (crown_diet
    crown_margins torso_adjust, as BL-046 recorded the pawl cheek)."""
    from . import crown_diet as CD
    from . import h1_spine_channel as SC
    best = None
    for kit in ("a_S", "a_M", "a_L"):
        with SC.real_crown_models(), SC._real_caches():
            _, rows = CD.load_beam(CD.specs()[kit], log=None)
        m = CD.crown_margins(rows)
        for tg in ("C", "C_im3"):
            f = m[tg]["_torso_adjust"]["pawl_cheek_force"]
            v = np.asarray(f["factored_yz"], float)
            if best is None or np.linalg.norm(v) > np.linalg.norm(best[0]):
                best = (v, f"{kit} {tg}:{f['set']}")
    return {"factored_yz": best[0].tolist(), "set": best[1], "n": float(np.linalg.norm(best[0]))}


def cheek_strength(force_yz=None) -> dict:
    """The cheek as built: frame_production.cheek_check's voxel FE with the H1 cheek's own geometry: 13.8 mm wall
    (8 mm 304 sleeve credited only), bore 9.0 mm from the fore face (window above it), 8.5 mm above the boss bottom,
    the root taken at the housing top only (conservative: the side wall's joint to the upper bar below and the aft
    wall are not credited). Also the record's 8 / 8 cheek for comparison."""
    from . import frame_production as FP
    from . import h1_spine_channel as SC
    if force_yz is None:
        force_yz = pawl_force()["factored_yz"]
    P = frame_place()
    e_fore = P["pivot_y_rel"] - SC.housing_dims()["fore_rel"]
    e_bot = P["z_pivot"] - BOSS_Z_LO
    h_top = SC.HOUSING_TOP_Z - P["z_pivot"]
    depth = SC.housing_dims()["aft_rel"] - SC.housing_dims()["fore_rel"]
    orig = FP._cheek_geometry

    def geo(thick_mm, hole_d, h=1.0):
        from huntkit.gendesign.fem import Grid
        ny, nz = int(round(depth / h)), int(round((e_bot + h_top) / h))
        nx = max(2, int(round(thick_mm / h)))
        g = Grid((nx, ny, nz), h, x0=np.array([0.0, 0.0, 0.0]))
        c = g.elem_centers()
        cy, cz = e_fore, h_top                # root (z' = 0) at the housing top; z' runs down
        r = np.hypot(c[:, 1] - cy, c[:, 2] - cz)
        return g, r >= hole_d / 2, cy, cz
    f = np.asarray(force_yz, float)
    f_flip = np.array([0.0, -f[1], -f[2]])     # y' = fore distance (y_rel - fore face): fore load -> -y'; z' down
    FP._cheek_geometry = geo
    try:
        built = FP.cheek_check(f_flip, BORE_REAM_D, 8.0, True, pin_d=4.2)
    finally:
        FP._cheek_geometry = orig
    rec = FP.cheek_check(f, BORE_REAM_D, 8.0, True, pin_d=4.2)
    for r in (built, rec):
        r.pop("map", None)
    return {"force_yz": [float(v) for v in f], "built": {**built, "sf_fi": 1.0 / max(built["fi99"], 1e-9)},
            "record_8x8": {**rec, "sf_fi": 1.0 / max(rec["fi99"], 1e-9)},
            "edges_mm": {"fore": round(e_fore, 2), "bottom": round(e_bot, 2), "to_housing_top": round(h_top, 2)}}


# ================================================================================== pawl print files
def export_pawls(out_dir: Path = PRINT_DIR) -> dict:
    """LP pawl STL / 3MF: FDM PAHT-CF 16 mm wide, SLM Ti 12 mm wide."""
    from .printables import extrude
    out = {}
    for nm, w, rho in (("crown_pawl_lp_fdm_pacf", 16.0, 1.06e-3), ("crown_pawl_lp_slm", 12.0, 4.43e-3)):
        m = extrude(lp_profile(), w)
        m.export(out_dir / f"{nm}.stl")
        try:
            m.export(out_dir / f"{nm}.3mf")
        except Exception:      # pragma: no cover
            pass
        out[nm] = {"width_mm": w, "g": round(m.volume * rho, 2), "watertight": bool(m.is_watertight),
                   "extents_mm": [round(v, 2) for v in m.extents]}
    return out
