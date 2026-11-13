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


def channel_mask(cen: np.ndarray) -> np.ndarray:
    """Voxels (centres ``cen``) inside the BL-046 channel section over the housing's height (frame_h1.keepouts)."""
    from shapely import contains_xy
    x, y, z = np.asarray(cen, float).T
    h = housing_dims()
    out = np.zeros(len(x), bool)
    near = (np.abs(x) < 30.0) & (z >= h["z"][0]) & (z <= h["z"][1])
    out[near] = contains_xy(channel_section(), x[near], y[near] - axis_y(z[near]))
    return out


def housing_ring_mask(cen: np.ndarray) -> np.ndarray:
    """Voxels (centres ``cen``) of the BL-046 housing ring (housing section minus the channel, housing heights):
    the pawl interface for frame_h1.keepouts (BL-047 re-base of the domain's old plate-channel 'pawl' mask)."""
    from shapely import contains_xy
    x, y, z = np.asarray(cen, float).T
    h = housing_dims()
    out = np.zeros(len(x), bool)
    near = (np.abs(x) < 30.0) & (z >= h["z"][0]) & (z <= h["z"][1])
    yr = y[near] - axis_y(z[near])
    out[near] = contains_xy(housing_section(), x[near], yr) & ~contains_xy(channel_section(), x[near], yr)
    return out


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
CLAMP_WEB_T = 2.0                  # clamp fitting webs (two, 7075), thickness; sized in crown_spine_clamp.web_check
#                                    (BL-047: 2.5 -> 2.0, every margin holds; analysis/crown_gnl.md section 6)
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


def _fore_wall(win, z: float, c: dict) -> float:
    """Fore wall thickness on the centre line; inside the BL-047 pawl window's height, beside the window (|x| = its
    half width + 1 mm, the lesser side): the window is the intended opening for the pawl's swing and its cord."""
    try:
        from .h1_pawl import window_section
        w, hx = window_section()
    except Exception:          # pragma: no cover
        w, hx = None, 0.0
    if w is not None and w.bounds[1] - 0.5 <= z <= w.bounds[3] + 0.5:
        return min(_wall(win, sx * (hx + 1.0), c["fore_rel"] - 0.01, sx * (hx + 1.0), -60.0) for sx in (-1.0, 1.0))
    return _wall(win, 0.0, c["fore_rel"] - 0.01, 0.0, -60.0)


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
           "fore_wall_mm": round(_fore_wall(win, z, c), 2),
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
    """Slice check of the spine channel on an H1 STL (frame coordinates): every 0.5 mm from 6 mm below the lowest guide
    B (kit S 15 in, tube end z 428) to 6 mm above the housing; then per crown kit and 0.5 in torso setting, the slices the tube passes (its bottom up) and guide B.
    Returns {'slices': [...], 'settings': [...], 'min': {...}, 'all_pass'}."""
    import trimesh
    mesh = trimesh.load(path_or_mesh) if isinstance(path_or_mesh, (str, Path)) else path_or_mesh
    h = housing_dims()
    # from below the lowest guide B (kit S 15 in) to 6 mm above the housing: the tube's whole path through the body
    z0 = min(s["bottom_z"] for s in settings()) - GUIDE_B_H - 6.0
    zs = np.arange(math.floor(z0), h["z"][1] + 6.0 + 1e-6, step)
    sl = [slice_channel(mesh, z) for z in zs]
    sets = []
    for s in settings():
        mine = [q for q in sl if q["z"] >= s["bottom_z"]]
        gb = guide_b_clear(mesh, s)
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
BEFORE_REV = "370bc8f"                     # the BL-045 commit (its H1 export, the plate channel)
BEFORE_STL_NOTE = f"git {BEFORE_REV} designs/pack_5200/print/frame_h1/h1_assembled.stl (BL-045 export)"


def before_stl() -> Path:
    """BL-045's H1 STL from git (commit BEFORE_REV; scratch copy in OUT)."""
    import subprocess
    p = OUT / f"h1_assembled_{BEFORE_REV}.stl"
    if not p.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(["git", "-C", str(REPO), "show", f"{BEFORE_REV}:designs/pack_5200/print/frame_h1/h1_assembled.stl"],
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


# ================================================================================== stale records (ticket item 3)
def refresh_records(log=print) -> dict:
    """``frame_h1_results.json`` (H1 verify, 2026-11-10) and ``frame_fixed_results.json`` (BL-007 study) still carried
    BL-042's stale 'fairleads present' key. Their keep-outs are re-run here on each record's own stored body (the
    keep-out functions as they are now: voxel fairlead stubs, the print-STL fairlead check, the BL-046 channel); the
    FEA numbers in them are left as dated (no solve is repeated: those bodies are superseded studies)."""
    from . import frame_fixed as FF
    from . import frame_h1 as H1
    note = ("keepouts re-run 2026-11-13 (BL-046, h1_spine_channel.refresh_records) on the record's stored body; "
            "FEA numbers as of the record's date")
    out = {}
    p = H1.RESULT
    d = json.loads(p.read_text())
    sol = np.load(H1.OUT / "h1_final.npz")["solid"]
    d["keepouts"] = H1.keepouts(sol)
    d["keepouts_note"] = note
    p.write_text(json.dumps(d, indent=1, default=float))
    out["frame_h1_results"] = d["keepouts"]
    p = FF.RESULT
    d = json.loads(p.read_text())
    sols = {"a": np.load(H1.OUT / "h1_final.npz")["solid"], "c": np.load(FF.OUT / "c_solid.npz")["solid"]}
    sols["b"] = sols["c"]
    for v in ("a", "c", "b"):
        dom = FF.fixed_domain("a" if v == "a" else "c")
        ko = FF.keepouts_fixed(dom, sols[v])
        d["variants"][v]["body"]["keepouts"] = ko
        d["variants"][v]["body"]["keepouts_note"] = note
        out[f"frame_fixed_{v}"] = ko
    p.write_text(json.dumps(d, indent=1, default=float))
    if log:
        log(json.dumps(out, default=float)[:600])
    return out


# ================================================================================== crown records on the real crown
def crown_compare() -> dict:
    """crown_diet.crown_margins (crown legs, top bar, spine, corner bonds, bushings, rack, pawl cheek, frame buckling)
    on the beam rows as recorded (crown_diet caches) and on the real crown (the rows ``body_check(real=True)`` made)."""
    from . import crown_diet as CD
    out = {}
    for kit in ("a_S", "a_M", "a_L"):
        sp = CD.specs()[kit]
        _, rows0 = CD.load_beam(sp, log=None)
        with real_crown_models(), _real_caches():
            _, rows1 = CD.load_beam(sp, log=None)
        m0, m1 = CD.crown_margins(rows0), CD.crown_margins(rows1)
        out[kit] = {"recorded": m0["min"], "real": m1["min"], "recorded_min": m0["min_all"], "real_min": m1["min_all"]}
    return out


# ================================================================================== figures
def _sec_polys(mesh, z):
    P = _body_section(mesh, z)
    from shapely.geometry import box
    return P.intersection(box(-45, -50, 45, 35))


def _draw(ax, geom, **kw):
    from shapely.geometry import MultiPolygon, Polygon
    gs = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    for g in gs:
        if not isinstance(g, Polygon) or g.is_empty:
            continue
        x, y = g.exterior.xy
        ax.fill(x, y, **kw)
        for r in g.interiors:
            xi, yi = r.xy
            ax.fill(xi, yi, color="white", lw=0)
    return MultiPolygon


def plot_sections(before, after, path: Path) -> str:
    """Before (BL-045 STL) / after (BL-046 STL) at the pawl line: the body, the tube + rack, the pawl zone."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10, 6.2), dpi=110)
    y0 = float(axis_y(PAWL_Z))
    for ax, mesh, title in ((axs[0], before, "BL-045 print (plate channel)"), (axs[1], after, "BL-046 print (tube channel)")):
        _draw(ax, _sec_polys(mesh, PAWL_Z), color="#9aa3ad", lw=0)
        mv = moving_envelope()
        x, y = mv.exterior.xy
        ax.fill(x, y, color="#c0392b", alpha=0.55, lw=0)
        ax.plot(x, y, color="#7b241c", lw=1.2)
        x, y = pawl_zone().exterior.xy
        ax.fill(x, y, color="#f1c40f", alpha=0.45, lw=0)
        ax.axhline(0.0, color="k", lw=0.6, ls=":")
        ax.axhline(TOP_BAR_AFT_MM, color="#2e86c1", lw=1.4, ls="--")
        ax.text(-43, TOP_BAR_AFT_MM + 1.0, "top bar axis (25 mm aft, z 600+)", fontsize=8.5, color="#2e86c1")
        ax.text(-43, 1.0, "legs' plane = spine axis", fontsize=8.5)
        ax.set_xlim(-45, 45)
        ax.set_ylim(-50, 35)
        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("x across the frame, mm")
        ax.grid(alpha=0.25)
    axs[0].set_ylabel(f"y from the spine axis, mm (wearer up; axis at frame y {y0:.1f})")
    axs[0].text(-43, -46, "OD 20 tube + 6 mm rack (red)\noverlaps the body: does not fit", fontsize=9, color="#7b241c")
    c = channel_dims()
    h = housing_dims()
    axs[1].text(-43, -46, f"channel {c['width']:.0f} x {c['depth']:.1f} mm, clearance {RUN_CLEAR:.0f} mm\n"
                f"walls fore {h['fore_wall']:.1f} / aft {h['aft_wall']:.1f} / side {h['side_wall']:.1f} mm",
                fontsize=9, color="#1d4d1d")
    fig.suptitle(f"H1 section at the pawl line z {PAWL_Z:.0f} (sliced from the exported STLs); yellow = pawl swing",
                 fontsize=11)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def buckling_mode(model: dict, case_name: str = "hipbelt_off_abuse") -> tuple:
    """First eigen-buckling mode of ``case_name`` on a beam model (huntkit.fea.frame.buckling_factors re-run with
    eigenvectors). Returns (Result, lambda, {node: mode translation})."""
    import scipy.sparse.linalg as spla
    import huntkit.fea.frame as F
    from huntkit.fea.load_standard import ls1_envelope
    got = {}
    orig = F.buckling_factors

    def bf(K, Kg, free, n_modes=3):
        mu, v = spla.eigsh(-Kg[free][:, free].tocsc(), k=6, M=K[free][:, free].tocsc(), which="LA")
        i = int(np.argmax(mu))
        phi = np.zeros(K.shape[0])
        phi[free] = v[:, i]
        got["phi"], got["lam"] = phi, float(1.0 / mu[i])
        return [got["lam"]]
    case = copy.copy(next(c for c in ls1_envelope("C")["crown_bar"] if c.name == case_name))
    case.params = dict(case.params)
    case.buckling = True
    F.buckling_factors = bf
    try:
        res = case.run(model)
    finally:
        F.buckling_factors = orig
    U = got["phi"].reshape(-1, 6)[:, :3]
    U = U / np.abs(U).max()
    return res, got["lam"] / (1.5 * case.required_sf), {nid: U[i] for i, nid in enumerate(res.node_ids[: res.n_user_nodes])}


def plot_real_crown(path: Path) -> str:
    """Kit S 18 in, hipbelt_off_abuse: first buckling mode of the beam model as recorded and of the real crown (top bar
    25 mm aft, clamp member), front and side views, and the corner dog-leg forces."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import crown_diet as CD
    m0 = CD.build(CD.specs()["a_S"], 18.0)
    fig, axs = plt.subplots(1, 4, figsize=(12, 6.6), dpi=100, gridspec_kw={"width_ratios": [1.6, 0.6, 1.6, 0.6]})
    for k, (m, lab) in enumerate(((m0, "beam model (bar in the legs' plane)"), (real_crown(m0), "real crown (bar 25 mm aft)"))):
        res, marg, U = buckling_mode(m)
        n = m["nodes"]
        dl = next(q for q in res.members if q["id"].startswith("CLtop-"))["end_forces"][0][0]
        for v, (i, j) in enumerate(((0, 2), (1, 2))):
            ax = axs[2 * k + v]
            for q in m["members"]:
                a, b = q["nodes"]
                pa, pb = np.asarray(n[a], float), np.asarray(n[b], float)
                col = "#c0392b" if q["group"] == "spine_clamp" else "#7f8c8d"
                ax.plot([pa[i], pb[i]], [pa[j], pb[j]], color=col, lw=1.0)
                if a in U and b in U:
                    da, db = pa + 60.0 * U[a], pb + 60.0 * U[b]
                    ax.plot([da[i], db[i]], [da[j], db[j]], color="#e67e22", lw=1.0)
            ax.set_aspect("equal")
            ax.grid(alpha=0.25)
            ax.set_xlabel("x, mm" if i == 0 else "y, mm")
            if v == 0:
                ax.set_title(f"{lab}\nbuckling margin {marg:.2f}; dog-leg axial {dl:+.0f} N", fontsize=10)
                ax.set_ylabel("z, mm")
    fig.suptitle("Kit S 18 in, hipbelt_off_abuse: first buckling mode (orange, 60 mm max), front and side views. "
                 "Grey = frame; red = spine clamp", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_margins(res: dict, path: Path) -> str:
    """Margins (pass >= 1): clamp bonds and webs on the real crown; the H1 body per basis, BL-045 / BL-046 (loads as
    recorded) / BL-046 (real crown)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = res["clamp"]["margins"]
    cl = [("socket avg", c["socket"]["avg"]["sf"]), ("socket peak", c["socket"]["peak"]["sf"]),
          ("socket fatigue", c["socket"]["fat_avg"]["sf"]), ("saddle avg", c["saddle"]["avg"]["sf"]),
          ("saddle peak", c["saddle"]["peak"]["sf"]), ("saddle peak +V*", c["saddle_with_shear"]["peak"]["sf"]),
          ("socket bending", c["socket_bending"]["sf_yield"]), ("webs yield", c["webs"]["sf_yield"]),
          ("webs fatigue", c["webs"]["sf_fatigue_kt2"])]
    fig, axs = plt.subplots(1, 2, figsize=(11, 6.4), dpi=105, gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axs[0]
    v = [q[1] for q in cl]
    ax.barh([q[0] for q in cl], v, color=["#27ae60" if x >= 1 else "#c0392b" for x in v])
    for i, x in enumerate(v):
        ax.text(min(x, 4.6) + 0.05, i, f"{x:.2f}", va="center", fontsize=9)
    ax.axvline(1.0, color="k", lw=1)
    ax.set_xlim(0, 5)
    ax.invert_yaxis()
    ax.set_title("Spine clamp (real crown)\n* transverse shear in the bond: T6 coupon", fontsize=10)
    ax = axs[1]
    bases = ["fine_sm8", "fine", "beam", "fine_sm8.cyc"]
    fams = [("strength", "strength"), ("fatigue", "fatigue"), ("buckling", "buckling")]
    runs = [("bl045", "BL-045", "#95a5a6"), ("loads_as_recorded", "BL-046 body", "#2e86c1"),
            ("loads_real_crown", "BL-046 body, real crown", "#8e44ad")]
    labels, ypos = [], 0
    for b in bases:
        for fk, fl in fams:
            for k, (rk, rl, col) in enumerate(runs):
                val = res["body"].get(rk, {}).get(b, {}).get(fk)
                if val is None:
                    continue
                ax.barh(ypos + k * 0.27, val, height=0.25, color=col, label=rl if (b, fk) == ("fine_sm8", "strength") else None)
                ax.text(val + 0.02, ypos + k * 0.27, f"{val:.2f}", va="center", fontsize=7)
            labels.append((ypos + 0.27, f"{b} {fl}"))
            ypos += 1
    ax.set_yticks([q[0] for q in labels])
    ax.set_yticklabels([q[1] for q in labels], fontsize=8)
    ax.axvline(1.0, color="k", lw=1)
    ax.set_xlim(0, 3.0)
    ax.invert_yaxis()
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title("H1 body margins (pass >= 1; cinch-cycled fatigue is MT-1's open bound)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def figures(res: dict) -> list:
    import trimesh
    SCREENS.mkdir(parents=True, exist_ok=True)
    before, after = trimesh.load(before_stl()), trimesh.load(PRINT_DIR / "h1_assembled.stl")
    shots = [plot_sections(before, after, SCREENS / f"{SHOT}1.png"), plot_real_crown(SCREENS / f"{SHOT}2.png"),
             plot_margins(res, SCREENS / f"{SHOT}3.png")]
    return shots


# ================================================================================== record
def _lb(g: float) -> str:
    return f"{g / 28.3495:.2f} oz"


def write_doc(res: dict, shots: list | None = None) -> str:
    c, h, ax, cl = res["channel"], res["housing"], res["axis"], res["clamp"]
    st, m, b = res["stl_check"], res["mass"], res["body"]
    mg = cl["margins"]
    L = []
    a = L.append
    a("# BL-046 H1 spine channel and spine offset\n")
    a("Generated by `python -m huntkit.gendesign.h1_spine_channel` (data `h1_spine_channel.json`). Date "
      f"{res['date']}. Units mm, N, g (in, lbf, oz alongside). Loads and factors: HA-LS-1 rev C "
      "(`load_standard.md`), unchanged.\n")
    a("## Summary\n")
    a(f"- **Channel re-made for the OD 20 spine tube + 6 mm rack** (`add_channel`, called by `frame_h1.print_mesh`): "
      f"{c['width']:.0f} x {c['depth']:.1f} mm (was 40.2 x 18.3 for the 30 x 3 plate): tube r 10 + "
      f"{RUN_CLEAR:.0f} mm running clearance aft, rack 6 + pawl swing {PAWL_ZONE} fore, {c['width']:.0f} mm wide for the "
      f"20 mm rack and the 16 mm pawl. Housing z {h['z'][0]:.0f}-{h['z'][1]:.2f} (top and half-width kept, so B-25's "
      f"BL-045 clearances to it stand); walls fore {h['fore_wall']:.1f}, aft {h['aft_wall']:.1f}, side "
      f"{h['side_wall']:.1f} mm (>= {MIN_WALL:.0f}).")
    a(f"- **Slice check on the exported STL** (`check_stl_channel`, {st['slices_checked']} slices at 0.5 mm, every crown "
      f"kit S/M/L at every 0.5 in setting = {len(st['settings'])} settings, guide B at the top settings): "
      f"**{'PASS' if st['all_pass'] else 'FAIL'}**. Least clearance tube + rack to the body {st['min']['clear_mm']:.2f} mm "
      f"(>= {RUN_CLEAR - MESH_TOL:.2f}), walls fore {st['min']['fore_wall_mm']:.1f} / aft {st['min']['aft_wall_mm']:.1f} / "
      f"side {st['min']['side_wall_mm']:.1f} mm. The same check on BL-045's STL fails "
      f"{res['stl_check_before']['slices_fail']} slices and passes {res['stl_check_before']['settings_pass']} of 21 "
      "settings (it is the check that catches the old channel).")
    a(f"- **Print files closed:** assembled {res['print']['assembled_g']:.1f} g (BL-045 {res['print']['assembled_g_before']:.1f}), "
      f"watertight {res['print']['watertight']}, {res['print']['shells']} shell; lower "
      f"{res['print']['halves']['lower']['g']:.1f} g / upper {res['print']['halves']['upper']['g']:.1f} g, each one closed "
      f"shell; every fairlead still passes `h1_fairleads.check_stl` ({res['fairleads_check_all_pass']}).")
    a(f"- **Spine offset decided: the spine sits in the legs' plane**, where the beam model has it; the print now agrees "
      f"(STL axis y {res['spine_axis']['spine_axis_y_at_pawl_mm']:.2f} vs model {res['spine_axis']['model_spine_y_at_pawl_mm']:.2f}). "
      f"BL-045's 15.85 mm fore cannot hold tube + rack + pawl in front of the yoke path ({ax['why']}).")
    a(f"- **But the clamp still spans 25 mm.** The crown top bar is 25 mm *aft* of the legs' plane "
      "(geometry.yaml `top_bar_aft_offset_mm`, the corner dog-legs), which neither BL-045 nor the beam model carried. "
      "`real_crown` adds the dog-legs and a 25 mm clamp member to the beam model; the clamp, the H1 body and buckling are "
      "re-run on it. The roughly 12 N m BL-045 estimated becomes the real crown's own load path: factored spine-top "
      f"moment {cl['loads_max_factored']['spine_M_max_nm']:.1f} N m (BL-045 model 55.1, the offset member now carries the "
      f"rest), bar torsion jump {cl['loads_max_factored']['bar_T_jump_max_nm']:.1f} N m.")
    a(f"- **Clamp on the real crown passes** (7075 T-fitting, saddle {cl['saddle_len_mm']:.0f} / socket {cl['socket_len_mm']:.0f} mm, "
      f"two {mg['webs']['web_t_mm']} mm webs): socket avg / peak / fatigue {mg['socket']['avg']['sf']:.2f} / "
      f"{mg['socket']['peak']['sf']:.2f} / {mg['socket']['fat_avg']['sf']:.2f}; saddle {mg['saddle']['avg']['sf']:.2f} / "
      f"{mg['saddle']['peak']['sf']:.2f} / {mg['saddle']['fat_avg']['sf']:.2f}; webs yield {mg['webs']['sf_yield']:.2f}, "
      f"fatigue {mg['webs']['sf_fatigue_kt2']:.2f}; socket bending {mg['socket_bending']['sf_yield']:.2f}. With the "
      f"transverse shear added to the saddle bond the peak is **{mg['saddle_with_shear']['peak']['sf']:.2f}** (BL-045 0.78): "
      "the T6 coupon must cover it, as before.")
    a(f"- **Mass:** clamp {m['clamp_g']:.1f} g (BL-045 {m['clamp_bl045_g']}, booked {m['clamp_booked_g']}) = "
      f"**{m['clamp_g'] - m['clamp_booked_g']:+.1f} g** in every config; channel + housing **{m['channel_net_g']:+.1f} g** "
      f"(housing +{m['housing_added_g']:.1f}, channel and bay -{m['channel_cut_g']:.1f}) on the H1 configs. Booked as "
      f"ledger correction BL046: **{m['clamp_g'] - m['clamp_booked_g'] + m['channel_net_g']:+.1f} g "
      f"({_lb(m['clamp_g'] - m['clamp_booked_g'] + m['channel_net_g'])})** on `corrie_b2_h1_v2`.")
    rr = b.get("loads_real_crown", {})
    rec = b.get("loads_as_recorded", {})
    if rr and rec:
        worst = min(((v["fatigue"], k) for k, v in rr.items() if k != "fine_sm8.cyc"))
        bk = min(((v["buckling"], k) for k, v in rr.items() if k != "fine_sm8.cyc"))
        a(f"- **Body (all four R1 bases):** on the real crown the least fatigue is {worst[0]:.3f} ({worst[1]}), "
          f"buckling {bk[0]:.3f} ({bk[1]}), strength {min(v['strength'] for v in rr.values()):.2f}; BL-045 "
          f"{min(v['fatigue'] for k, v in b['bl045'].items() if k != 'fine_sm8.cyc'):.3f} / "
          f"{min(v['buckling'] for k, v in b['bl045'].items() if k != 'fine_sm8.cyc'):.3f}. "
          f"Cinch-cycled bound: fatigue {rr['fine_sm8.cyc']['fatigue']:.3f}, buckling {rr['fine_sm8.cyc']['buckling']:.3f} "
          f"(BL-045 {b['bl045']['fine_sm8.cyc']['fatigue']:.3f} / {b['bl045']['fine_sm8.cyc']['buckling']:.3f}). "
          "Table in section 5.")
    if "crown" in res:
        cr = res["crown"]
        rb = min((v["real"]["buckling"]["sf"], k, v["real"]["buckling"]["set"]) for k, v in cr.items())
        r0 = min((v["recorded"]["buckling"]["sf"], k) for k, v in cr.items())
        a(f"- **Not held: crown frame buckling on the real crown.** The beam model's eigen-buckling margin "
          f"(P_cr / (1.5 x factored)) falls from {r0[0]:.2f} (model, kit {r0[1]}) to **{rb[0]:.2f}** (kit {rb[1]}, "
          f"{rb[2]}); only hipbelt_off_abuse drops (every other case within 0.1 of the model). Mechanism: with the "
          "top bar 25 mm aft, the lifter springs (TB0 / TB2) pull the bar fore and each 32 mm corner dog-leg carries "
          "about 408 N compression (model: 12 N tension); its P-delta softens a global sway mode (stay feet "
          "fore-aft, antisymmetric) of the frame hanging on the shoulder and lifter springs. This is the top bar's "
          "offset (geometry since v3.1), not the channel: it exists with or without BL-046. Every crown member, "
          "bond and the H1 body still pass on the real crown (section 5). See OWNER DECISIONS / next step.")
    a("")
    a("## 1. Channel and housing\n")
    a("| item | value | source |\n|---|---:|---|")
    a(f"| spine tube OD | {SPINE_OD:.0f} | frame.yaml spine_section |")
    a(f"| rack thickness x width | {RACK_T:.0f} x {RACK_W:.0f} | print/crown_rack_fdm_pacf.stl (test) |")
    a(f"| pawl width (FDM) | {PAWL_W:.0f} | print/crown_pawl_fdm_pacf.stl (test) |")
    a(f"| running clearance (radial / each side) | {RUN_CLEAR:.1f} | ASSUMPTION RUN-CLEAR |")
    a(f"| pawl swing zone fore of the tooth tips | {PAWL_ZONE} | ASSUMPTION PAWL-ZONE |")
    a(f"| channel width x depth | {c['width']:.1f} x {c['depth']:.2f} ({c['width'] / 25.4:.2f} x {c['depth'] / 25.4:.2f} in) | channel_dims |")
    a(f"| housing y from the axis (fore / aft) | {h['fore_rel']:.2f} / {h['aft_rel']:.2f} | fore face kept (YOKE-PATH), aft in the bag envelope |")
    a(f"| housing z | {h['z'][0]:.1f} - {h['z'][1]:.2f} | upper bar underside to BL-045's housing top |")
    a(f"| walls fore / aft / side | {h['fore_wall']:.2f} / {h['aft_wall']:.2f} / {h['side_wall']:.2f} | >= {MIN_WALL:.0f} (FDM min wall) |")
    gb = res["guide_bay"]
    a(f"| guide B bay (x half, top z) | {gb['half_x']:.1f}, z {gb['z_top']:.2f} | ASSUMPTION GUIDE-B |")
    a("")
    a("## 2. Slice check on the exported STL\n")
    zs = [q["z"] for q in st["slices"]]
    a(f"`check_stl_channel(print/frame_h1/h1_assembled.stl)`: body sections every 0.5 mm from z {min(zs):.0f} (below the "
      f"lowest guide B, kit S 15 in) to z {max(zs):.1f} (above the housing), y taken from the spine axis at each z (the legs lean). Per slice: the tube + rack envelope's "
      f"clearance to the body (>= {RUN_CLEAR} - {MESH_TOL} simplify tolerance), the pawl zone empty, walls. Per setting: "
      "the slices the tube passes, the pawl on the rack, and guide B's 39 x 8 x 18 mm block below the tube end.\n")
    a("| kit | torso in | tube bottom z | slices | least clearance mm | pawl zone empty | pawl on rack | guide B clear mm | pass |")
    a("|---|---:|---:|---:|---:|---|---|---:|---|")
    for s in st["settings"]:
        g = s["guide_b"]["clear_mm"]
        a(f"| {s['kit']} | {s['torso_in']:g} | {s['bottom_z']:.1f} | {s['slices']} | {s['min_clear_mm']:.2f} | "
          f"{s['pawl_zone_empty']} | {s['pawl_on_rack']} | {'-' if g is None else f'{g:.2f}'} | {s['pass']} |")
    a("")
    a(f"Before (BL-045 STL, {res['stl_check_before']['source']}): least clearance "
      f"{res['stl_check_before']['min']['clear_mm']:.2f} mm, {res['stl_check_before']['slices_fail']} slices fail.\n")
    ko = res.get("keepouts_bl046", {})
    if ko:
        a("Voxel keep-outs on the BL-046 body (`frame_h1.keepouts`, read in the body check): new channel empty "
          f"{ko.get('spine channel BL-046 (tube + rack, h1_spine_channel) empty')}; 'pawl present' "
          f"{ko.get('pawl present'):.2f}, 'spine_channel empty' {ko.get('spine_channel empty'):.2f} and 'outside envelope' "
          f"{ko.get('outside envelope (voxels)')} voxels are the voxel domain's OLD plate-channel masks (x +-19, y -33..-17): "
          "the new housing fills the old slot and the new channel cuts the old pawl cheeks. They are not bag-envelope "
          "violations (the housing's aft face is inside y_hi, test `test_housing_walls_and_envelope`).\n")
    a("## 3. Where the spine axis sits\n")
    a("| quantity | y at the pawl line (mm) |\n|---|---:|")
    a(f"| housing fore face (kept: the yoke passes it) | {ax['housing_fore_y']:.2f} |")
    a(f"| most-fore tube axis with a {MIN_WALL:.0f} mm fore wall | {ax['axis_y_most_fore_mm']:.2f} |")
    a(f"| BL-045 printed axis (channel centre) | {ax['printed_bl045_axis_y_mm']:.2f} |")
    a(f"| legs' plane = beam model spine = **chosen axis** | **{ax['chosen_axis_y_mm']:.2f}** |")
    a(f"| STL tube axis after BL-046 (aft face - 11) | {res['spine_axis']['spine_axis_y_at_pawl_mm']:.2f} |")
    a(f"| crown top bar axis (legs' plane + 25 aft) | {ax['legs_plane_y_mm'] + TOP_BAR_AFT_MM:.2f} |")
    a("")
    a("The stack fore of the tube axis (tube r + rack + pawl zone = "
      f"{ax['stack_fore_of_axis_mm']:.1f} mm) plus a wall does not fit between the fixed fore face and BL-045's axis, so "
      "the axis goes to the legs' plane. The spine is then 25 mm fore of the top bar, carried by the clamp's webs.\n")
    a("## 4. Spine clamp on the real crown\n")
    a("`crown_spine_clamp.joint_loads(real=True)`: the crown_diet beam model of each kit at both ends of its range with "
      "`real_crown` (top-bar nodes inside the corners moved 25 mm aft, the corners becoming the dog-legs; the spine's top "
      "SPC in the legs' plane joined to TB1 by a 25 mm 7075 member with the two webs' section), every rev C set, both "
      "couple variants. Hand check (test): a pull P along the spine gives P at the spine's top with no moment, and "
      "P x 25 mm at TB1.\n")
    lm, l0 = cl["loads_max_factored"], res["clamp_loads_model_basis"]
    a("| factored load | BL-045 model (spine on TB1) | real crown |\n|---|---:|---:|")
    for k, lab in (("spine_N_max_n", "spine axial N"), ("spine_V_max_n", "spine shear N"), ("spine_M_max_nm", "spine moment N m"),
                   ("bar_T_jump_max_nm", "bar torsion jump N m"), ("bar_M_jump_max_nm", "bar bending jump N m")):
        a(f"| {lab} | {l0[k]} | {lm[k]} |")
    a("")
    a("| check | margin | set |\n|---|---:|---|")
    for k, lab in (("socket", "socket bond"), ("saddle", "saddle bond"), ("socket_with_shear", "socket + transverse shear"),
                   ("saddle_with_shear", "saddle + transverse shear")):
        for q in ("avg", "peak", "fat_avg", "fat_peak"):
            a(f"| {lab} {q} | {mg[k][q]['sf']:.2f} | {mg[k][q]['set']} |")
    a(f"| socket bending yield / fatigue | {mg['socket_bending']['sf_yield']:.2f} / {mg['socket_bending']['sf_fatigue_kt2']:.2f} | max set |")
    a(f"| webs yield / fatigue (Kt 2) | {mg['webs']['sf_yield']:.2f} / {mg['webs']['sf_fatigue_kt2']:.2f} | {mg['webs']['set']} |")
    a("")
    a(f"Clamp: saddle {cl['saddle_len_mm']:.0f} mm, socket {cl['socket_len_mm']:.0f} mm, collar {cl['collar_below_bar_underside_mm']} "
      f"mm below the bar's underside (BL-045 12.8: the spine now clears the bar, so the socket starts at its centre "
      f"height), spine {cl['spine_axis_offset_fore_mm']:.2f} mm fore of the bar, {cl['mass_g']:.1f} g ({_lb(cl['mass_g'])}).\n")
    bw = res["b25"]
    a(f"B-25 on it: band to clamp {bw['band_to_clamp_x_mm']} mm, every kit ok {bw['all_ok']}; the run reaches the spine "
      f"{bw['run_plan_mm']['spine_axis_fore_of_bar_mm']:.1f} mm fore of the bar, plan run {bw['run_plan_mm']['run_real_mm']} mm "
      f"(BL-043 drew {bw['run_plan_mm']['run_bl043_mm']}): **cut +{bw['run_plan_mm']['cut_change_mm']} mm** (BL-045 +34.1). "
      "Published in `crown_spine_clamp` (constants); corrie_f picks them up on its next run (BL-044's files, not edited here).\n")
    a("## 5. H1 body, all R1 bases\n")
    a("`h1_buckling.full_check` on the BL-046 voxel body (`body_solid`: BL-027 release body, BL-042/045 fairlead "
      "clearances, this housing / channel / bay). 'As recorded' = the load sets as BL-045 ran them; 'real crown' = sets "
      "rebuilt with `real_crown_models` (cached apart). Margins: FI99 strength / fatigue (1.6 g, PAHT 0.30) / creep per "
      "kit and setting, Euler margin P_cr / (1.5 x factored), z 234 joint.\n")
    a("| basis | run | strength | fatigue | creep | buckling (member) | joint s / f |\n|---|---|---:|---:|---:|---|---|")
    for bs in ("fine_sm8", "fine", "beam", "fine_sm8.cyc"):
        for rk, rl in (("bl045", "BL-045"), ("loads_as_recorded", "BL-046, loads as recorded"),
                       ("loads_real_crown", "BL-046, real crown")):
            v = b.get(rk, {}).get(bs)
            if v:
                a(f"| {bs} | {rl} | {v['strength']:.3f} | {v['fatigue']:.3f} | {v['creep']:.3f} | {v['buckling']:.3f} "
                  f"({v['buckling_member']}) | {v['joint_s']:.2f} / {v['joint_f']:.2f} |")
    a("")
    if "crown" in res:
        a("Crown members on the beam model (`crown_diet.crown_margins`, least over both couple variants):\n")
        a("| kit | recorded min | real crown min | real: top bar | spine | corner bond peak | frame buckling |")
        a("|---|---:|---:|---:|---:|---:|---:|")
        for k, v in res["crown"].items():
            r = v["real"]
            g = lambda q: f"{r[q]['sf']:.2f}" if q in r else "-"  # noqa: E731
            a(f"| {k} | {v['recorded_min']:.3f} | {v['real_min']:.3f} | {g('crown_top_bar')} | {g('crown_spine')} | "
              f"{g('corner_bond_peak')} | {g('buckling')} |")
        a("")
    a("The frame-buckling drop on the real crown is a linear eigen check with dead loads and the model's body "
      "springs. A strap is a tension-only follower, and the corner wrap is a bonded lug, not a straight OD 18 tube, "
      "so the check is probably conservative, but nothing here proves it. It needs its own ticket: a geometric "
      "non-linear run of hipbelt_off_abuse on the real crown with follower lifter / shoulder loads, and the T1(c) "
      "hipbelt-off frame test (PRODUCTION.md) watched for sway. The design fix if it is real is to bring the top "
      "bar into the legs' plane (the clamp offset goes too) or to stiffen the corner wraps. ASSUMPTION "
      "TOP-BAR-AFT governs.\n")
    a("## 6. Mass\n")
    a("| item | g | oz | source |\n|---|---:|---:|---|")
    a(f"| spine clamp as sized | {m['clamp_g']:.1f} | {m['clamp_g'] / 28.3495:.2f} | size_clamp (real crown) |")
    a(f"| booked before | {m['clamp_booked_g']:.1f} | {m['clamp_booked_g'] / 28.3495:.2f} | pack5200.HW |")
    a(f"| housing added | {m['housing_added_g']:+.1f} | {m['housing_added_g'] / 28.3495:+.2f} | print mesh |")
    a(f"| channel + bay cut | {-m['channel_cut_g']:+.1f} | {-m['channel_cut_g'] / 28.3495:+.2f} | print mesh |")
    a(f"| **BL046 correction (H1 configs)** | **{m['clamp_g'] - m['clamp_booked_g'] + m['channel_net_g']:+.1f}** | "
      f"{(m['clamp_g'] - m['clamp_booked_g'] + m['channel_net_g']) / 28.3495:+.2f} | huntkit.mass.ledger BL046 |")
    a(f"| voxel body (FEA) | {m['voxel_body_g']:.1f} | {m['voxel_body_g'] / 28.3495:.2f} | 2 mm raster |")
    a("")
    a("Mass reductions that keep the margins (not applied): clamp webs 2.5 -> 2.0 mm (yield 1.81, fatigue 2.37 by "
      "`web_check`) saves about 1.5 g; the housing's aft wall (7+ mm where the envelope allows) could thin to 3 mm, about "
      "3 g, after the crown dry fit settles YOKE-PATH and GUIDE-B.\n")
    a("## 7. Records re-run\n")
    a("`frame_h1_results.json` and `frame_fixed_results.json`: keep-outs re-run on each record's stored body "
      "(`refresh_records`); the 'fairleads present' key is gone (voxel stubs + the print-STL fairlead check + the "
      "BL-046 channel). Their FEA numbers are left as dated: both are superseded studies.\n")
    a("## 8. Assumptions\n")
    for k, (t, s) in ASSUMPTIONS.items():
        a(f"- ASSUMPTION {k}: {t} Settled by: {s}")
    a("")
    a("## 9. Found, not fixed\n")
    a("- **Pawl pivot and the pawl's tang / cord eye.** Neither the BL-045 nor the BL-046 H1 print has the pawl's pivot "
      "bore through the housing side walls (no 8 mm hole in x-sections at |x| 14 / 18 / 22, z 495-540), though "
      "`print/frame/PRODUCTION.md` op 2 says \"ream each cheek to 8.0 mm\". And the FDM pawl (`printables.spring_pawl`: "
      "arm 8 + hub r 5, spring tang to 14 mm and cord eye to 13.5 mm off the tooth face) is deeper than the 9.3 mm swing "
      f"zone kept from BL-045 (ASSUMPTION PAWL-ZONE): the tang and the eye need a window in the fore wall "
      f"({h['fore_wall']:.1f} mm). Both need the pawl's pivot position fixed on the rack line; a ticket of its own.")
    if "crown" in res:
        a(f"- **Crown frame buckling on the real crown** (section 5): {min(v['real']['buckling']['sf'] for v in res['crown'].values()):.2f}"
          f"-{max(v['real']['buckling']['sf'] for v in res['crown'].values()):.2f} in hipbelt_off_abuse on the linear beam check.")
    a("")
    if shots:
        a("## Screenshots\n")
        for s in shots:
            a(f"- `{Path(s).relative_to(REPO)}`")
        a("")
    DOC.write_text("\n".join(L))
    return str(DOC)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", action="store_true", help="re-export the H1 print files (h1_buckling.export_print)")
    ap.add_argument("--body", choices=("recorded", "real", "both"), help="run the body checks (heavy)")
    ap.add_argument("--records", action="store_true", help="re-run the keep-outs of frame_h1 / frame_fixed records")
    a = ap.parse_args(argv)
    if a.export:
        from . import h1_buckling as B
        B.export_print(*B.CHOSEN)
    if a.body in ("recorded", "both"):
        body_check(False)
    if a.body in ("real", "both"):
        body_check(True)
    if a.records:
        refresh_records()
    if a.export or a.body or a.records:
        return
    res = compute()
    res["crown"] = crown_compare()
    res["keepouts_bl046"] = json.loads((__import__("huntkit.gendesign.h1_buckling", fromlist=["OUT"]).OUT /
                                        f"check_{BODY_CHECK}.json").read_text()).get("keepouts", {})
    RESULTS.write_text(json.dumps(res, indent=1, default=_np))
    shots = figures(res)
    print(write_doc(res, shots))
    print("\n".join(shots))


if __name__ == "__main__":
    main()
