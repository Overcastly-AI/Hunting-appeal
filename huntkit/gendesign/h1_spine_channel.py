"""BL-046: the H1 spine channel and pawl housing for the OD 20 spine tube + 6 mm rack, and where the spine axis sits.

Why (BL-045, ``crown_and_fairlead_checks.md`` Found, not fixed): the printed spine channel (40.2 x 18.3 mm through the
pawl housing) was sized for the old 30 x 3 mm plate spine. The crown now carries an OD 20 carbon spine tube with a
6 mm PA66-GF30 rack (frame.yaml ``spine_section`` od 20, ``print/crown_rack_*.stl`` 6 x 20 mm), which does not fit.
And the frame model hangs the spine in the legs' plane while the printed channel put it 15.85 mm fore.

What it does
1. **Channel and housing** (``channel_section`` / ``housing_section``, extruded along the crown axis): tube + rack +
   the pawl's swing zone, with a stated running clearance; one closed housing round it from z 496 to the old housing
   top; a bay at the bottom for the moving pulley guide B at each kit's top setting. ``add_channel`` puts them on the
   print mesh (``frame_h1.print_mesh`` calls it), ``voxel_channel`` on the 2 mm FEA body.
2. **Spine axis decision**: the yoke slides past the housing's fore face (geometry.yaml yoke anchors y -38.5..-42.3),
   so the fore face cannot move toward the wearer. Tube + rack + pawl zone + walls from that face put the tube axis
   in the legs' plane: the print now agrees with the model (``axis_decision``).
3. **The clamp still has an offset**: the crown top bar is 25 mm AFT of the legs' plane (geometry.yaml
   ``top_bar_aft_offset_mm``; corner dog-legs), which the beam model also leaves out. ``real_crown`` adds the top-bar
   sweep and the clamp's offset member to a beam model; the clamp bond, its webs, the body and buckling are re-run
   on it (``crown_spine_clamp`` with ``real_crown``; ``body_check``).
4. **Slice check** of the exported STL through the channel at every crown kit S/M/L and every 0.5 in torso setting
   (``check_stl_channel``).

Record: designs/pack_5200/analysis/h1_spine_channel.md (+ .json). Run:
    python -m huntkit.gendesign.h1_spine_channel --export   # print files with the new channel (h1_buckling.export_print)
    python -m huntkit.gendesign.h1_spine_channel --body     # body checks (4 bases, both load models; ~20 min)
    python -m huntkit.gendesign.h1_spine_channel            # checks, figures, md / json
Units mm, N, MPa, g.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_spine_channel.json"
DOC = ANALYSIS / "h1_spine_channel.md"
PRINT_DIR = PACK / "print" / "frame_h1"
OUT = REPO / "outputs" / "h1_spine_channel"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL046_"
RHO_G_MM3 = 1.06e-3                # PAHT-CF printed density (frame_h1 / h1_buckling)

# ------------------------------------------------------------------------------------------ spine, rack, pawl
SPINE_OD = 20.0                    # frame.yaml spine_section od (crown spine tube, rack bonded on)
RACK_T = 6.0                       # print/crown_rack_fdm_pacf.stl extents 230 x 6 x 20 (base 4 + teeth 2)
RACK_W = 20.0                      # rack width (geometry.yaml crown_retention.lock rack_width_mm 20)
PAWL_W = 16.0                      # print/crown_pawl_fdm_pacf.stl width (FDM tier; the Ti pawl is 12)
PAWL_ZONE = 9.3                    # ASSUMPTION PAWL-ZONE: the pawl's swing zone fore of the rack tooth tips, kept from
#                                    the printed channel it worked in (18.3 deep = 3 plate + 6 rack + 9.3 pawl zone)
RUN_CLEAR = 1.0                    # ASSUMPTION RUN-CLEAR: running clearance (radial on the tube, each side of the rack)
#                                    = FDM hole tolerance 0.3 + tube OD tolerance 0.1 + grit / ice 0.6
PAWL_SIDE_CLEAR = 1.0              # pawl width 16 in a 22 mm channel: 3 mm a side (pivot pin through the side walls)

# ------------------------------------------------------------------------------------------ housing
HOUSING_FORE_Y_AT_PAWL = -38.8     # today's housing fore face (H1 STL sections z 508-532, y min -38.8); ASSUMPTION
#                                    YOKE-PATH: it may not move toward the wearer (the yoke passes it)
HOUSING_HALF_W = 24.82             # crown_spine_clamp.PAWL_HOUSING_HALF_W (B-25 mitre clearance; kept)
HOUSING_TOP_Z = 535.62             # crown_spine_clamp: housing top z (PAWL_HOUSING_UP 15.62 above the pawl line; kept)
HOUSING_BOT_Z = 496.0              # the upper bar's underside at x 0 (H1 STL slices: body at |x| < 14 from z 496)
HOUSING_AFT_Y_AT_PAWL = 8.0        # aft face at the pawl line; envelope y_hi(520) 9.19 (frame_topopt, already -1 mm)
HOUSING_R = 3.0                    # outer corner radius
PAWL_Z = 520.0                     # crown_diet.PAWL_Z / pack5200 pawl_z
MIN_WALL = 2.0                     # frame_topopt: min wall FDM 2 mm

# moving pulley guide B on the spine bottom (print/pulley_guide_moving_*.stl, printables.webbing_guide 'moving')
GUIDE_B_W = 39.0                   # 25 mm webbing: slot 27 + 2 x 4 walls + 2 x 2 fillet buffer
GUIDE_B_T = 8.0                    # extrusion
GUIDE_B_CLEAR = 1.0
# ASSUMPTION GUIDE-B: guide B hangs from the tube's bottom end, centred on the tube axis, width across x. At each kit's
# top setting the tube end is 15.8 mm below the pawl line (crown_diet.size_spine_mm), inside the housing, so the guide
# enters it from below: the channel carries a bay (x +-20.5, 10 mm deep) up to the highest tube end + 1 mm.

ASSUMPTIONS = {
    "PAWL-ZONE": ("The pawl's swing zone is 9.3 mm deep fore of the rack's tooth tips, the room it had in the printed "
                  "channel (18.3 = 3 plate + 6 rack + 9.3); the pawl pivots on a 4 mm pin through the side walls.",
                  "Pawl dry fit on the first print: pawl fully lifted (2 mm tooth depth + 0.5) clears the fore wall."),
    "RUN-CLEAR": ("1.0 mm running clearance on the tube (radial) and each side of the rack: FDM hole tolerance 0.3 + "
                  "tube OD tolerance 0.1 + 0.6 for grit and ice.",
                  "Slide the bonded spine + rack through the printed housing by hand over the full travel, dry and "
                  "with grit, before bonding the clamp."),
    "RACK-SADDLE": ("The flat rack sits on the tube's fore face on a filled-adhesive saddle (MMA with glass beads), so "
                    "the moving envelope is the tube plus a 20 x 16 mm block from the tube axis to the tooth tips.",
                    "Bond trial on a spine offcut; the rack's base must seat flat."),
    "YOKE-PATH": ("The housing's fore face stays at today's y -38.8 (at the pawl line): the yoke on the spine passes "
                  "it at S 16.8-18 in and M 17.5-18.3 in (geometry.yaml yoke anchors y -38.5..-42.3).",
                  "Crown dry fit at kit S 18 in: the yoke slides past the housing."),
    "GUIDE-B": ("Moving pulley guide B hangs from the tube's lower end, centred on the tube axis, its 39 mm across x; "
                "at each kit's top setting it enters the housing from below (tube end 15.8 mm below the pawl line).",
                "Crown dry fit at each kit's top setting."),
    "TOP-BAR-AFT": ("The crown top bar runs 25 mm aft of the legs' plane at x 0 (geometry.yaml "
                    "top_bar_aft_offset_mm, corner dog-legs from x 103 to the leg); the beam model's top bar lies in "
                    "the legs' plane. real_crown moves the top bar and models the dog-legs as straight members from "
                    "the leg top to x 95 (the existing split node).",
                    "T6 coupon of the clamp fitting on the real offset; crown dry fit."),
    "CLAMP-OFFSET": ("The clamp's T-fitting spans the 25 mm from the top-bar axis to the spine axis as a solid "
                     "machined block (saddle, socket and two webs); modelled as a 25 mm 7075 beam with the webs' "
                     "section.", "T6 coupon of the fitting."),
}


# ================================================================================== axis and settings
def _env():
    from .frame_topopt import load_envelope
    return load_envelope()


def axis_y(z) -> np.ndarray:
    """Spine axis y at height z: the legs' plane line (frame_topopt.Envelope.sleeve_y, = the model's spine line)."""
    return np.asarray(_env().sleeve_y(z), float)


def axis_slope() -> float:
    return float(_env().axis_slope)


def settings() -> list[dict]:
    """Every crown kit S/M/L at every 0.5 in torso setting of its range: tube top (bar centre), tube bottom, pawl
    line position on the tube, yoke height (s 150)."""
    from . import crown_diet as CD
    uz = CD.geom()["uz"]
    out = []
    for k, (lo, hi) in CD.SIZES.items():
        L = CD.size_spine_mm(k)
        rack = CD.size_rack_mm(k)
        for t in np.arange(lo, hi + 1e-6, 0.5):
            zt = CD.crown_top_z(float(t))
            zb = zt - L * uz
            s_pawl = (zt - PAWL_Z) / uz
            out.append({"kit": k, "torso_in": float(t), "top_z": zt, "bottom_z": round(zb, 2),
                        "s_pawl_mm": round(s_pawl, 1), "spine_mm": round(L, 1), "rack_mm": round(rack, 1),
                        # ASSUMPTION RACK-POS: the rack is bonded flush with the tube's lower end
                        "pawl_on_rack": bool(L - rack <= s_pawl <= L - 8.0),
                        "pawl_to_tube_end_mm": round(L - s_pawl, 1),
                        "yoke_z": round(zt - 150.0 * uz, 1),
                        "in_housing_z": [round(max(zb, HOUSING_BOT_Z), 2), round(min(zt, HOUSING_TOP_Z), 2)]})
    return out


# ================================================================================== 2D sections (y relative to the axis)
def channel_dims() -> dict:
    """Channel cross-section relative to the spine axis (x across, y_rel fore - / aft +)."""
    r = SPINE_OD / 2.0
    half_x = max(r, RACK_W / 2.0, PAWL_W / 2.0 + PAWL_SIDE_CLEAR) + RUN_CLEAR
    tips = -(r + RACK_T)                        # rack tooth tips (fore)
    return {"half_x": half_x, "aft_r": r + RUN_CLEAR, "rack_tips_rel": tips, "fore_rel": tips - PAWL_ZONE,
            "depth": (r + RUN_CLEAR) - (tips - PAWL_ZONE), "width": 2 * half_x}


def housing_dims() -> dict:
    y0 = float(axis_y(PAWL_Z))
    c = channel_dims()
    fore_rel = HOUSING_FORE_Y_AT_PAWL - y0
    aft_rel = HOUSING_AFT_Y_AT_PAWL - y0
    return {"fore_rel": fore_rel, "aft_rel": aft_rel, "half_w": HOUSING_HALF_W,
            "fore_wall": c["fore_rel"] - fore_rel, "aft_wall": aft_rel - c["aft_r"], "side_wall": HOUSING_HALF_W - c["half_x"],
            "z": [HOUSING_BOT_Z, HOUSING_TOP_Z]}


def guide_bay() -> dict:
    """The bay for guide B at the housing bottom (x +-, y_rel range, top z along the axis)."""
    top = max(s["bottom_z"] for s in settings()) + 1.0
    return {"half_x": GUIDE_B_W / 2 + GUIDE_B_CLEAR, "y_rel": [-(GUIDE_B_T / 2 + GUIDE_B_CLEAR), GUIDE_B_T / 2 + GUIDE_B_CLEAR],
            "z_top": round(top, 2)}


def channel_section():
    """shapely polygon of the channel (relative to the axis)."""
    from shapely.geometry import Point, box
    c = channel_dims()
    return box(-c["half_x"], c["fore_rel"], c["half_x"], 0.0).union(Point(0, 0).buffer(c["aft_r"], 96))


def housing_section():
    from shapely.geometry import box
    h = housing_dims()
    return box(-h["half_w"], h["fore_rel"], h["half_w"], h["aft_rel"]).buffer(-HOUSING_R).buffer(HOUSING_R, 16)


def moving_envelope():
    """What slides in the channel: the tube and the rack on its saddle (relative to the axis), no clearance."""
    from shapely.geometry import Point, box
    r = SPINE_OD / 2.0
    return Point(0, 0).buffer(r, 96).union(box(-RACK_W / 2, -(r + RACK_T), RACK_W / 2, 0.0))


def pawl_zone():
    from shapely.geometry import box
    c = channel_dims()
    return box(-PAWL_W / 2, c["fore_rel"], PAWL_W / 2, c["rack_tips_rel"])


# ================================================================================== print mesh
def _prism(poly, z0: float, z1: float):
    """manifold3d prism of a shapely polygon (relative to the axis), sheared so every horizontal section at z sits on
    the spine axis axis_y(z)."""
    import manifold3d as m3d
    from shapely.geometry.polygon import orient
    pts = np.asarray(orient(poly, 1.0).exterior.coords)[:-1]       # counter-clockwise (manifold3d fill rule)
    cs = m3d.CrossSection([pts.tolist()])
    m = m3d.Manifold.extrude(cs, z1 - z0).translate((0.0, 0.0, z0))
    s = axis_slope()
    y_at0 = float(axis_y(0.0))
    M = np.array([[1.0, 0, 0, 0], [0, 1.0, s, y_at0], [0, 0, 1.0, 0]])     # y += y_axis(z)
    return m.transform(M)


def add_channel(man, stats: dict | None = None):
    """Housing ring (outer section, z 496 - housing top) unioned on, then the channel (z 470-560) and the guide-B bay
    cut. Returns the manifold."""
    from shapely.geometry import box
    v0 = man.volume()
    h = housing_dims()
    man = man + _prism(housing_section(), h["z"][0], h["z"][1])
    v1 = man.volume()
    man = man - _prism(channel_section(), 470.0, 560.0)
    b = guide_bay()
    man = man - _prism(box(-b["half_x"], b["y_rel"][0], b["half_x"], b["y_rel"][1]), 470.0, b["z_top"])
    v2 = man.volume()
    if stats is not None:
        stats.update({"body_mm3": v0, "housing_added_mm3": v1 - v0, "cut_mm3": v1 - v2, "net_mm3": v2 - v0,
                      "net_g": (v2 - v0) * RHO_G_MM3})
    return man


# ================================================================================== voxel body (FEA)
def voxel_channel(solid: np.ndarray, cen: np.ndarray | None = None) -> tuple:
    """The same housing / channel / bay on the 2 mm voxel body. Returns (new solid, voxel counts)."""
    from shapely import contains_xy
    from shapely.geometry import box
    if cen is None:
        from . import frame_h1 as H1
        cen = H1.base()["cen"]
    x, y, z = cen.T
    yr = y - axis_y(z)
    h = housing_dims()
    near = (np.abs(x) < 30.0) & (z > 460.0) & (z < 570.0)
    ring = np.zeros(len(solid), bool)
    ring[near] = contains_xy(housing_section(), x[near], yr[near]) & (z[near] >= h["z"][0]) & (z[near] <= h["z"][1])
    ch = np.zeros(len(solid), bool)
    ch[near] = contains_xy(channel_section(), x[near], yr[near])
    b = guide_bay()
    bay = np.zeros(len(solid), bool)
    bay[near] = contains_xy(box(-b["half_x"], b["y_rel"][0], b["half_x"], b["y_rel"][1]), x[near], yr[near]) & \
        (z[near] <= b["z_top"])
    new = (solid | ring) & ~ch & ~bay
    return new, {"added": int((new & ~solid).sum()), "removed": int((solid & ~new).sum()),
                 "channel": int(ch.sum()), "ring": int(ring.sum())}


# ================================================================================== spine axis decision
def axis_decision() -> dict:
    """Where the tube axis can sit: from the fixed housing fore face (YOKE-PATH), wall, pawl zone, rack, tube."""
    c = channel_dims()
    y_fore = HOUSING_FORE_Y_AT_PAWL
    y_axis_max_fore = y_fore + MIN_WALL - c["fore_rel"]          # most fore axis with a min wall: the stack from the face
    y_leg = float(axis_y(PAWL_Z))
    h = housing_dims()
    return {"housing_fore_y": y_fore, "stack_fore_of_axis_mm": round(-c["fore_rel"], 2),
            "axis_y_most_fore_mm": round(y_axis_max_fore, 2), "legs_plane_y_mm": round(y_leg, 2),
            "printed_bl045_axis_y_mm": -25.65, "printed_bl045_fore_of_legs_mm": 15.85,
            "chosen_axis_y_mm": round(y_leg, 2), "chosen_offset_from_legs_mm": 0.0,
            "fore_wall_mm": round(h["fore_wall"], 2), "aft_wall_mm": round(h["aft_wall"], 2),
            "side_wall_mm": round(h["side_wall"], 2),
            "printed_axis_possible": bool(-25.65 >= y_axis_max_fore - 1e-6),
            "why": "the stack (pawl zone + rack + tube + clearance) puts the most-fore axis at "
                   f"{y_axis_max_fore:.1f} with a {MIN_WALL:.0f} mm fore wall; the printed BL-045 axis (-25.65) would "
                   "need the fore face 15.9 mm further toward the wearer, where the yoke passes. The legs' plane "
                   f"({y_leg:.2f}) leaves a {h['fore_wall']:.1f} mm fore wall and a {h['aft_wall']:.1f} mm aft wall "
                   "inside the bag envelope, and is where the beam model already has the spine."}


# ================================================================================== beam model: the real crown
TOP_BAR_AFT_MM = 25.0              # geometry.yaml frame.members_topology.crown.top_bar_aft_offset_mm (asserted in tests)
CLAMP_WEB_T = 2.5                  # clamp fitting webs (two, 7075), thickness; sized in crown_spine_clamp.web_check
CLAMP_WEB_H = 21.2                 # web height = the saddle OD (18 + 2 x (0.8 bond + 0.8 wall))
CLAMP_WEB_GAP = 23.2               # webs at the socket OD's sides (crown_spine_clamp socket_od_mm)


def clamp_section(t: float = CLAMP_WEB_T):
    """The clamp fitting between the bar and the spine as two 7075 webs (local y along x, local z along z)."""
    from huntkit.fea.sections import generic
    h, d = CLAMP_WEB_H, CLAMP_WEB_GAP - t
    A = 2 * t * h
    I_strong = 2 * t * h ** 3 / 12.0                     # bending in the y-z plane (moment about x)
    I_weak = 2 * (h * t ** 3 / 12.0 + h * t * (d / 2) ** 2)
    J = 2 * h * t ** 3 / 3.0 + 4 * (d / 2) ** 2 * h * t * 0.0   # open webs (no closed cell credited)
    return generic(A, I_weak, I_strong, J, ymax=CLAMP_WEB_GAP / 2, zmax=h / 2)


def _clamp_material():
    from huntkit.materials import load
    m = load("alu_7075_t6")
    return {"id": "alu_7075_t6_clamp", "youngs_modulus_mpa": float(m.require("youngs_modulus_mpa")),
            "shear_modulus_mpa": float(m.require("shear_modulus_mpa")), "poisson": float(m.get("poisson", 0.33)),
            "design_allowable_mpa": float(m.require("yield_strength_sbasis_mpa")), "density_kg_m3": 0.0}


def real_crown(model: dict, top_bar_aft: float = TOP_BAR_AFT_MM, spine_fore: float = 0.0) -> dict:
    """The beam model with the crown as built: every top-bar node inside the corners (TB*, |x| < leg x) moved
    ``top_bar_aft`` aft (+y), so the corner members become the dog-legs; the spine hangs from a clamp member TB1 ->
    SPC (SPC = the spine's top on the spine axis, ``spine_fore`` fore of the legs' plane; BL-046: 0) and every spine
    node moves with it; the pawl link gets a matching node on the upper bar (UBP, rigid arm from UB1) if the spine is
    off the legs' plane. Mass is unchanged (the clamp is booked in the hardware rows). Returns a new model dict."""
    m = copy.deepcopy(model)
    n = m["nodes"]
    xl = max(abs(v[0]) for k, v in n.items() if k in ("CLtop", "CRtop"))
    tb1 = np.array(n["TB1"], float)
    for k in list(n):
        if k.startswith("TB") and abs(n[k][0]) < xl - 1e-6:
            n[k] = [n[k][0], n[k][1] + top_bar_aft, n[k][2]]
    for k in list(n):
        if k.startswith("SP"):
            n[k] = [n[k][0], n[k][1] - spine_fore, n[k][2]]
    n["SPC"] = [float(tb1[0]), float(tb1[1] - spine_fore), float(tb1[2])]
    first = next(q for q in m["members"] if q["group"] == "crown_spine" and q["nodes"][0] == "TB1")
    i = m["members"].index(first)
    other = first["nodes"][1]
    clamp = {"id": "TB1-SPC", "nodes": ["TB1", "SPC"], "section": clamp_section(), "material": _clamp_material(),
             "group": "spine_clamp", "ref": [0.0, 0.0, 1.0]}
    sp = {**first, "id": f"SPC-{other}", "nodes": ["SPC", other]}
    m["members"][i:i + 1] = [clamp, sp]
    if abs(spine_fore) > 1e-9:
        pl = next((q for q in m["links"] if q["id"] == "pawl"), None)
        if pl is not None:
            ub = np.array(n[pl["nodes"][0]], float)
            n["UBP"] = [float(ub[0]), float(ub[1] - spine_fore), float(ub[2])]
            m["members"].append({"id": f"{pl['nodes'][0]}-UBP", "nodes": [pl["nodes"][0], "UBP"],
                                 "section": clamp_section(8.0), "material": _clamp_material(), "group": "pawl_arm",
                                 "ref": [0.0, 0.0, 1.0]})
            pl["nodes"] = ["UBP", pl["nodes"][1]]
    m["real_crown"] = {"top_bar_aft_mm": top_bar_aft, "spine_fore_mm": spine_fore}
    return m


@contextlib.contextmanager
def real_crown_models():
    """Inside: every crown_diet.build (the beam model of the crown-kit records, the H1 body load sets and the clamp
    loads) returns ``real_crown`` of its model."""
    from . import crown_diet as CD
    orig = CD.build

    def build(spec, t, posts: bool = False):
        return real_crown(orig(spec, t, posts=posts))
    CD.build = build
    try:
        yield
    finally:
        CD.build = orig


# ================================================================================== STL slice check
MESH_TOL = 0.05                    # h1_fairleads.EYE_MESH_TOL: the export's simplify tolerance (frame_h1.SIMPLIFY_MM 0.04)
GUIDE_B_H = 18.0                   # guide B profile height (printables.webbing_guide 'moving': base -6 .. top 12)


def _body_section(mesh, z: float):
    """Body section at z as a shapely geometry (even-odd of the section loops), y relative to the spine axis."""
    from shapely import affinity
    from shapely.geometry import Polygon
    s = mesh.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    P = Polygon()
    if s is not None:
        for e in s.discrete:
            if len(e) >= 3:
                P = P.symmetric_difference(Polygon(e[:, :2]).buffer(0))
    return affinity.translate(P, 0.0, -float(axis_y(z)))


def _wall(P, x0, y0, x1, y1) -> float:
    from shapely.geometry import LineString
    g = P.intersection(LineString([(x0, y0), (x1, y1)]))
    return 0.0 if g.is_empty else float(g.length)


def slice_channel(mesh, z: float) -> dict:
    """One slice: clearance of the tube + rack to the body, pawl zone empty, wall thicknesses (y relative to axis)."""
    from shapely.geometry import box
    P = _body_section(mesh, z)
    win = P.intersection(box(-40, -60, 40, 40))
    M = moving_envelope()
    c = channel_dims()
    h = housing_dims()
    clear = 99.0 if win.is_empty else (float(win.distance(M)) if not win.intersects(M) else 0.0)
    pz = pawl_zone().buffer(-MESH_TOL)
    out = {"z": round(float(z), 2), "clear_mm": round(clear, 3),
           "tube_rack_clear": bool(clear >= RUN_CLEAR - MESH_TOL),
           "pawl_zone_empty": bool(not win.intersects(pz)),
           "fore_wall_mm": round(_wall(win, 0.0, c["fore_rel"] - 0.01, 0.0, -60.0), 2),
           "aft_wall_mm": round(_wall(win, 0.0, c["aft_r"] + 0.01, 0.0, 40.0), 2),
           "side_wall_R_mm": round(_wall(win, c["half_x"] + 0.01, -8.0, 40.0, -8.0), 2),
           "side_wall_L_mm": round(_wall(win, -c["half_x"] - 0.01, -8.0, -40.0, -8.0), 2),
           "in_housing": bool(h["z"][0] + 0.5 <= z <= h["z"][1] - 0.5)}
    out["pass"] = out["tube_rack_clear"] and out["pawl_zone_empty"]
    return out


def guide_b_clear(mesh, s: dict) -> dict:
    """Guide B (39 x 8 mm, GUIDE_B_H tall, hanging from the tube end) at one setting: slices through its height."""
    from shapely.geometry import box
    g = box(-GUIDE_B_W / 2, -GUIDE_B_T / 2, GUIDE_B_W / 2, GUIDE_B_T / 2)
    zs = np.arange(s["bottom_z"] - GUIDE_B_H, s["bottom_z"] + 1e-6, 1.0)
    worst = 99.0
    for z in zs:
        P = _body_section(mesh, z).intersection(box(-40, -60, 40, 40))
        d = 0.0 if P.intersects(g) else float(P.distance(g)) if not P.is_empty else 99.0
        worst = min(worst, d)
    return {"clear_mm": round(worst, 3), "pass": bool(worst >= GUIDE_B_CLEAR - MESH_TOL)}


def check_stl_channel(path_or_mesh, step: float = 0.5) -> dict:
    """Slice check of the spine channel on an H1 STL (frame coordinates): every 0.5 mm from 6 mm below the housing to
    6 mm above it; then per crown kit and 0.5 in torso setting, the slices the tube passes (its bottom up) and guide B.
    Returns {'slices': [...], 'settings': [...], 'min': {...}, 'all_pass'}."""
    import trimesh
    mesh = trimesh.load(path_or_mesh) if isinstance(path_or_mesh, (str, Path)) else path_or_mesh
    h = housing_dims()
    zs = np.arange(h["z"][0] - 6.0, h["z"][1] + 6.0 + 1e-6, step)
    sl = [slice_channel(mesh, z) for z in zs]
    sets = []
    for s in settings():
        mine = [q for q in sl if q["z"] >= s["bottom_z"]]
        gb = guide_b_clear(mesh, s) if s["bottom_z"] - GUIDE_B_H < h["z"][1] and s["bottom_z"] > h["z"][0] - GUIDE_B_H - 6 \
            else {"clear_mm": None, "pass": True, "note": "guide B below the housing"}
        sets.append({"kit": s["kit"], "torso_in": s["torso_in"], "bottom_z": s["bottom_z"],
                     "slices": len(mine), "min_clear_mm": min(q["clear_mm"] for q in mine),
                     "pawl_zone_empty": all(q["pawl_zone_empty"] for q in mine), "pawl_on_rack": s["pawl_on_rack"],
                     "guide_b": gb,
                     "pass": bool(all(q["pass"] for q in mine) and gb["pass"] and s["pawl_on_rack"])})
    inh = [q for q in sl if q["in_housing"]]
    mn = {"clear_mm": min(q["clear_mm"] for q in sl),
          "fore_wall_mm": min(q["fore_wall_mm"] for q in inh), "aft_wall_mm": min(q["aft_wall_mm"] for q in inh),
          "side_wall_mm": min(min(q["side_wall_R_mm"], q["side_wall_L_mm"]) for q in inh)}
    mn["walls_ok"] = bool(min(mn["fore_wall_mm"], mn["aft_wall_mm"], mn["side_wall_mm"]) >= MIN_WALL)
    return {"slices": sl, "settings": sets, "min": mn,
            "all_pass": bool(all(q["pass"] for q in sl) and all(s["pass"] for s in sets) and mn["walls_ok"])}


# ================================================================================== body checks (voxel FEA)
BODY_CHECK = "m1_u2.5_im3_bl046"            # h1_buckling.full_check cache name, loads as recorded (BL-045 basis)
BODY_CHECK_REAL = "m1_u2.5_im3_bl046_real"  # same body, loads from the real crown (real_crown_models)
BODY_CHECK_BL045 = "m1_u2.5_im3_bl045"      # BL-045's record (h1_fairleads.BODY_CHECK_BL042 after BL-045)


def body_solid() -> tuple:
    """The voxel body as printed after BL-046: BL-027's release body, BL-042/045 fairlead clearances
    (h1_fairleads.voxel_as_printed), then this housing / channel / bay. Returns (solid, counts)."""
    from . import h1_buckling as B
    from . import h1_fairleads as HF
    s0 = B.final_solid(*B.CHOSEN)
    s1, _ = HF.voxel_as_printed(s0)
    return voxel_channel(s1)


@contextlib.contextmanager
def _real_caches():
    """Redirect the beam / load-set caches of crown_diet and h1_sleeve while the real crown is installed."""
    import shutil
    from . import crown_diet as CD
    from . import h1_sleeve as S
    o_cd, o_s = CD.OUT, S.OUT
    n_cd, n_s = OUT / "crown_diet_real", OUT / "h1_sleeve_real"
    n_cd.mkdir(parents=True, exist_ok=True)
    (n_s / "sets").mkdir(parents=True, exist_ok=True)
    for f in o_cd.glob("geometry_leg*.yaml"):
        if not (n_cd / f.name).exists():
            shutil.copy(f, n_cd / f.name)
    CD.OUT, S.OUT = n_cd, n_s
    try:
        yield
    finally:
        CD.OUT, S.OUT = o_cd, o_s


def body_check(real: bool, log=print) -> dict:
    """h1_buckling.full_check (4 bases: strength, fatigue, creep per kit and setting, member buckling, z 234 joint) on
    the BL-046 body; ``real``: on load sets from the real crown (top bar 25 mm aft, clamp member)."""
    from . import h1_buckling as B
    solid, _ = body_solid()
    if not real:
        return B.full_check(BODY_CHECK, solid, log=log)
    with real_crown_models(), _real_caches():
        return B.full_check(BODY_CHECK_REAL, solid, log=log)


# ================================================================================== record
BEFORE_STL_NOTE = "git HEAD designs/pack_5200/print/frame_h1/h1_assembled.stl (BL-045 export)"


def before_stl() -> Path:
    """BL-045's H1 STL from git HEAD (scratch copy in OUT)."""
    import subprocess
    p = OUT / "h1_assembled_bl045.stl"
    if not p.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:designs/pack_5200/print/frame_h1/h1_assembled.stl"],
                              check=True, capture_output=True).stdout
        p.write_bytes(data)
    return p


def _body_rows(chk: dict) -> dict:
    from . import h1_buckling as B
    return {b: {**{k: round(float(v), 3) for k, v in chk[b]["min"].items()}, "buckling": round(chk[b]["buckling_min"], 3),
                "buckling_member": min((v["margin"], k) for k, v in chk[b]["buckling"].items() if v["margin"] is not None)[1],
                "joint_s": round(chk[b]["joint_strength"], 3), "joint_f": round(chk[b]["joint_fatigue"], 3)}
            for b in B.BASES_CHECK if b in chk}


def compute(log=print) -> dict:
    import trimesh
    from . import crown_spine_clamp as CSC
    from . import h1_buckling as B
    from . import h1_fairleads as HF
    after = trimesh.load(PRINT_DIR / "h1_assembled.stl")
    chk = check_stl_channel(after)
    chk_before = check_stl_channel(before_stl())
    info = json.loads((B.OUT / "print_info.json").read_text())
    before_g = round(trimesh.load(before_stl()).volume * RHO_G_MM3, 1)
    halves = {}
    for nm in ("lower", "upper"):
        m = trimesh.load(PRINT_DIR / f"h1_{nm}_flat.stl")
        halves[nm] = {"g": round(m.volume * RHO_G_MM3, 1), "watertight": bool(m.is_watertight),
                      "shells": len(m.split(only_watertight=False)), "extents_mm": [round(v, 1) for v in m.extents]}
    rows = CSC.joint_loads(real=True)
    clamp = CSC.size_clamp(rows)
    rows_model = CSC.joint_loads(real=False)
    st = info["fairleads_bl042"]["spine_channel_bl046"]
    body = {"bl045": _body_rows(json.loads((B.OUT / f"check_{BODY_CHECK_BL045}.json").read_text())),
            "loads_as_recorded": _body_rows(json.loads((B.OUT / f"check_{BODY_CHECK}.json").read_text())),
            "loads_real_crown": _body_rows(json.loads((B.OUT / f"check_{BODY_CHECK_REAL}.json").read_text()))}
    solid, cnt = body_solid()
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    res = {"date": "2026-11-13", "ticket": "BL-046",
           "channel": channel_dims(), "housing": housing_dims(), "guide_bay": guide_bay(), "axis": axis_decision(),
           "settings": settings(),
           "stl_check": {"min": chk["min"], "all_pass": chk["all_pass"], "settings": chk["settings"],
                         "slices_checked": len(chk["slices"]),
                         "slices": [{k: q[k] for k in ("z", "clear_mm", "fore_wall_mm", "aft_wall_mm", "side_wall_R_mm",
                                                       "pass")} for q in chk["slices"]]},
           "stl_check_before": {"min": chk_before["min"], "all_pass": chk_before["all_pass"],
                                "settings_pass": sum(s["pass"] for s in chk_before["settings"]),
                                "slices_fail": sum(not q["pass"] for q in chk_before["slices"]),
                                "source": BEFORE_STL_NOTE},
           "fairleads_check_all_pass": bool(HF.check_stl(after)["all_pass"]),
           "print": {"assembled_g": round(after.volume * RHO_G_MM3, 1), "assembled_g_before": before_g,
                     "watertight": bool(after.is_watertight), "shells": len(after.split(only_watertight=False)),
                     "halves": halves, "export": {k: info[k] for k in ("assembled", "lower", "upper")}},
           "mass": {"channel_net_g": round(st["net_g"], 2), "housing_added_g": round(st["housing_added_mm3"] * RHO_G_MM3, 2),
                    "channel_cut_g": round(st["cut_mm3"] * RHO_G_MM3, 2), "clamp_g": clamp["mass_g"],
                    "clamp_booked_g": clamp["mass_booked_g"], "clamp_bl045_g": 10.4,
                    "voxel_body_g": round(D.mass_g(solid, H1.H, 1060.0), 1), "voxel_counts": cnt,
                    "basis": "channel: print-mesh volume with / without add_channel x 1.06 g/cm3 (pre-simplify); clamp: "
                             "crown_spine_clamp.size_clamp (real crown)"},
           "clamp": clamp, "clamp_loads_model_basis": CSC._load_summary(rows_model),
           "clamp_published": {k: getattr(CSC, k) for k in ("SPINE_CLAMP_HALF_X", "SPINE_CLAMP_COLLAR", "SPINE_AXIS_FORE_MM",
                                                             "SPINE_CLAMP_MASS_G", "PAWL_HOUSING_UP", "PAWL_HOUSING_HALF_W",
                                                             "BODY_TOP_Z_IN_B25_BAND", "B25_RUN_EXTRA_PER_SIDE_MM",
                                                             "B25_CUT_CHANGE_MM")},
           "interfaces": CSC.h1_crown_interfaces(), "spine_axis": CSC.spine_axis(),
           "b25": CSC.b25_clearances(clamp, CSC.h1_crown_interfaces()),
           "body": body, "assumptions": ASSUMPTIONS}
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
