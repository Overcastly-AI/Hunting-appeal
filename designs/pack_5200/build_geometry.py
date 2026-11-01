"""Pack 5200: compute geometry, volumes, bill of panels, weight budget and concept sketch.

Owner: pack-designer. Source of truth for the numbers in DESIGN.md. Run from repo root:

    python designs/pack_5200/build_geometry.py

Writes (all regenerated, do not hand-edit):
    designs/pack_5200/geometry.yaml
    designs/pack_5200/panels.yaml
    outputs/screens/20261101_packv3_concept.png

v3 "SPINE" (2026-11-01): the v2 box bag was rejected (too boxy/dated). The bag is now a tall,
tapered, domed TEARDROP roll-top lofted from mixed-superellipse rings, with its volume integrated
exactly from that shape and its body panels developed (gore method) from the 3D surface. The frame
topology (section 1) is unchanged from v2 and is the FEA engineer's hard-point contract.

Frame coordinate system (FCS) is the same as huntkit.fea.frames: x lateral (+ = wearer's right),
y aft (+ = away from the wearer's back, toward the bag), z up, origin = midpoint between the two
stay-foot centreline points. Units mm.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import yaml

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from huntkit import materials as MAT
from huntkit.patterns import (Piece, cubic_inches, develop_ruled_surface, litres, panel_volume, rect_panel,
                              tapered_panel)

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
SCREEN = ROOT / "outputs" / "screens" / "20261101_packv3_concept.png"  # v3 SPINE (v2 sketch: _packconcept_2.png)
IN = 25.4
TARGET_L = 85.2  # spec.yaml: 5200 cu in main bag

# ============================================================================ 1. FRAME TOPOLOGY
# Segmented carbon stays (straight bought tubes + bonded elbow), parallel upper segments so the
# crown legs can telescope in them. Numbers are TOPOLOGY requirements; tube sizes = FEA engineer.
FOOT = (135.0, 0.0, 0.0)        # stay foot centreline (x = +/-)
ELBOW = (115.0, -25.0, 130.0)   # lumbar apex: bonded elbow (stays bulge toward the wearer)
STAY_TOP = (115.0, -10.0, 530.0)  # top of fixed stay = crown socket (UHMWPE bushing)
Z_IC = 120.0                    # iliac-crest datum = hipbelt pivot height
YOKE_DROP = 50.0                # ASSUMPTION (same as FEA): yoke anchor 50 mm below C7
LIFTER_ABOVE_YOKE = 150.0       # crown top bar (lifter anchors) sits 150 mm above the yoke
CROWN_LEG = 430.0               # crown leg length along axis
MIN_OVERLAP = 150.0             # requirement: >= 150 mm leg insertion at max extension
RACK_PITCH = 4.0                # toothed-rack pitch for the positive lock (0.16 in) - see crown_retention()
PULLEY_MA = 3                   # 3:1 webbing pulley (adjuster)
SPINE_LEN = 300.0               # crown centre spine length below the top bar
PULLEY_FIXED_Z = 190.0          # fixed guide rings on the top edge of the lumbar plate
TORSO_IN = (15.0, 23.0)

u_axis = np.subtract(STAY_TOP, ELBOW)[1:]
u_axis = u_axis / np.linalg.norm(u_axis)  # (y, z) unit vector of the upper stays / crown


def y_on_axis(z: float) -> float:
    return ELBOW[1] + (z - ELBOW[2]) * u_axis[0] / u_axis[1]


def stay_xyz(z: float) -> tuple[float, float, float]:
    """Stay centreline at height z (right stay; mirror x for left)."""
    if z <= ELBOW[2]:
        t = z / ELBOW[2]
        return tuple(float(a + (b - a) * t) for a, b in zip(FOOT, ELBOW))
    return (ELBOW[0], y_on_axis(z), z)


def r3(p):
    return [round(float(v), 1) for v in p]


def crown_settings():
    rows = []
    n = int(round((TORSO_IN[1] - TORSO_IN[0]) / 0.5))
    for i in range(n + 1):
        t_in = TORSO_IN[0] + 0.5 * i
        yoke_z = Z_IC + t_in * IN - YOKE_DROP
        top_z = yoke_z + LIFTER_ABOVE_YOKE
        leg_bottom = top_z - CROWN_LEG
        overlap = STAY_TOP[2] - leg_bottom
        c7_z = yoke_z + YOKE_DROP
        # lifter angle: shoulder-strap lifter point 20 mm below C7 and 140 mm forward of the
        # anchor (ASSUMPTION: back panel ~35 mm + trapezius/clavicle offset ~105 mm)
        strap = (-140.0 + y_on_axis(top_z) - 15.0, c7_z - 20.0)
        anchor = (y_on_axis(top_z) - 15.0, top_z)
        ang = math.degrees(math.atan2(anchor[1] - strap[1], anchor[0] - strap[0]))
        rows.append({"index": i, "torso_in": t_in, "torso_mm": round(t_in * IN, 1),
                     "yoke_anchor": r3((0, y_on_axis(yoke_z) - 30, yoke_z)),
                     "lifter_anchor_R": r3((70, y_on_axis(top_z) - 15, top_z)),
                     "crown_top_z": round(top_z, 1), "leg_overlap_mm": round(overlap, 1),
                     "lifter_angle_deg": round(ang, 1)})
    return rows


def crown_retention():
    """Trade study numbers for holding the telescoping crown. Positive = extension (crown pushed UP
    out of the stays: the shoulders lift the yoke while the frame + load hang below it)."""
    g = 9.81
    shoulder_share = 0.20                      # huntkit.fea.load_cases hip_share = 0.80
    cases = {
        "drop_2p5g_extension": {"load_n": 0.20 * 68 * g * 2.5, "sf": 2.0,
                                "basis": "68 kg x 2.5 g x 20 % shoulder share (spec drop case)"},
        "overload_extension": {"load_n": 0.20 * 91 * g * 1.5, "sf": 1.5,
                               "basis": "91 kg x 1.5 g x 20 % (FEA overload_haul case)"},
        "hipbelt_off_abuse_extension": {"load_n": 1.0 * 68 * g * 1.5, "sf": 1.0,
                                        "basis": "ASSUMPTION abuse: hipbelt unbuckled (creek crossing), 68 kg x 1.5 g, 100 % on shoulders; no slip, no damage"},
        "tall_load_compression": {"load_n": -0.40 * 68 * g * 2.5, "sf": 2.0,
                                  "basis": "ASSUMPTION: 40 % of 68 kg lashed to crown/extension posts x 2.5 g pushes the crown DOWN"},
    }
    for c in cases.values():
        c["load_n"] = round(c["load_n"], 0)
        c["required_n"] = round(abs(c["load_n"]) * c["sf"], 0)
    ext = max(c["required_n"] for c in cases.values() if c["load_n"] > 0)
    comp = max(c["required_n"] for c in cases.values() if c["load_n"] < 0)
    ll = MAT.load("ladder_lock_25mm").require("slip_load_n")
    fid = MAT.load("fidlock_magnetic_buckle_25mm").require("breaking_strength_n")
    cam_slip = 700.0   # ASSUMPTION: 25 mm metal cam buckle on heavyweight poly webbing; no DB record yet
    mu, wraps = 0.10, 2  # UHMWPE-lined guides, 180 deg wrap each
    capstan = math.exp(mu * math.pi) ** wraps
    tail_for_ext = ext / PULLEY_MA / capstan
    walk_tail = shoulder_share * 68 * g / PULLEY_MA / capstan
    # rack tooth shear: 2 engaged teeth, 20 mm wide, root = pitch/2, PA66-GF30 conditioned
    su = MAT.load("pa66_gf30").require("ultimate_strength_mpa") if MAT.load("pa66_gf30").get("ultimate_strength_mpa") else 185.0
    tau = 0.6 * su * 0.6     # shear ~0.6 Su, x0.6 conditioned (moisture) knock-down: ASSUMPTION
    rack_cap = 2 * 20.0 * (RACK_PITCH / 2) * tau
    options = [
        {"option": "Pulley 3:1 + ladder lock only", "hold_n": round(ll * PULLEY_MA * capstan),
         "source": f"ladder_lock_25mm slip_load_n={ll:g} (estimate) x MA x capstan {capstan:.2f}",
         "creep": "poor: webbing walks through ladder locks under cyclic gait loads", "ice_mud": "fair", "mass_g": 35,
         "two_way": False, "beginner": "easy", "verdict": "reject as sole retention (holds once, creeps)"},
        {"option": "Pulley 3:1 + cam buckle only", "hold_n": round(cam_slip * PULLEY_MA * capstan),
         "source": "cam slip 700 N ASSUMPTION (no DB record; materials-engineer to add)",
         "creep": "fair: cam teeth hold, but webbing creep/stretch over a day of hauling", "ice_mud": "fair-poor (iced cam teeth)",
         "mass_g": 45, "two_way": False, "beginner": "easy", "verdict": "good ADJUSTER; one-way, so not a lock"},
        {"option": "Cam-lever friction collars x2 (seatpost QR)", "hold_n": 1600,
         "source": "ASSUMPTION ~800 N per QR at rated torque with carbon paste; ~50 % when wet/iced",
         "creep": "good dry; slips wet/icy", "ice_mud": "poor (friction-only, grit in the sliding fit)", "mass_g": 70,
         "two_way": True, "beginner": "hard (slotted bonded Al sockets, clamp-crush risk on carbon legs)",
         "verdict": "reject: friction-only and levers sit behind the shoulder blades (not adjustable while worn)"},
        {"option": "Fidlock/Austrialpin-style hard-lock buckle in the pulley line", "hold_n": fid,
         "source": f"fidlock_magnetic_buckle_25mm breaking_strength_n={fid:g}",
         "creep": "n/a: locks the buckle, not the webbing position", "ice_mud": "good", "mass_g": 15, "two_way": False,
         "beginner": "easy", "verdict": "reject: does not fix position; strength below need"},
        {"option": "Two-way toothed rack + spring pawl (PA66-GF30 rack, Ti pawl)", "hold_n": round(rack_cap),
         "source": f"2 teeth x 20 mm x {RACK_PITCH / 2:g} mm root x tau {tau:.0f} MPa (pa66_gf30, conditioned ASSUMPTION)",
         "creep": "none (positive)", "ice_mud": "good: open teeth self-clear; pawl snaps in under its spring", "mass_g": 50,
         "two_way": True, "beginner": "medium (rack waterjet/3D-printed outsourced; screw-on)",
         "verdict": "CHOSEN as the positive lock"},
    ]
    return {
        "concept": ("Pulley-tensioned telescoping crown: a 3:1 webbing pulley (25 mm poly webbing, UHMWPE-lined guides, "
                    "metal cam buckle) sets crown height continuously, while worn. A two-way toothed rack + spring pawl "
                    "is the positive lock: pull the release toggle (left shoulder strap) to lift the pawl, pull the tail "
                    "to shorten / ease the cam and shrug to lengthen, let go and the pawl drops into the nearest tooth."),
        "sign_convention": "extension = crown pushed up out of the stays; compression = pushed down",
        "load_cases": cases,
        "required_capacity_n": {"extension": ext, "compression": comp,
                                "note": "lock (rack+pawl) must hold BOTH with zero slip; ultimate >= 1.5 x these"},
        "pulley": {"mechanical_advantage": PULLEY_MA, "guide_friction_mu": mu, "capstan_factor": round(capstan, 2),
                   "routing": "dead end on crown spine bottom -> fixed guide A (lumbar plate top, z 190) -> moving guide B (crown spine bottom) -> fixed guide C -> cam buckle at the lumbar plate right corner (alt. left)",
                   "tail_tension_while_walking_n": round(walk_tail, 1),
                   "tail_tension_to_hold_extension_requirement_n": round(tail_for_ext, 0),
                   "tail_travel_mm": round(PULLEY_MA * (TORSO_IN[1] - TORSO_IN[0]) * IN),
                   "role": "adjuster; carries load only while the pawl is released"},
        "lock": {"type": "two-way toothed rack + spring pawl", "rack_material": "pa66_gf30", "pawl_material": "ti_6al_4v",
                 "pitch_mm": RACK_PITCH, "engaged_teeth": 2, "rack_width_mm": 20.0,
                 "capacity_n": round(rack_cap), "sf_vs_requirement": round(rack_cap / max(ext, comp), 2),
                 "resolution_mm": RACK_PITCH, "release": "Dyneema 2 mm cord to a toggle on the left shoulder strap"},
        "options": options,
    }


def frame_topology():
    settings = crown_settings()
    hp = {}

    def both(name, p):
        hp[name + "_R"] = r3(p)
        hp[name + "_L"] = r3((-p[0], p[1], p[2]))

    both("stay_foot", FOOT)
    both("lumbar_elbow", ELBOW)
    both("stay_top_crown_socket", STAY_TOP)
    both("shelf_pivot", (FOOT[0], 8.0, 25.0))
    both("hip_stabilizer_anchor", (stay_xyz(60)[0] - 5, stay_xyz(60)[1] - 12, 60.0))
    both("shoulder_strap_lower_anchor", (stay_xyz(110)[0], stay_xyz(110)[1] - 15, 110.0))
    x330 = stay_xyz(330)
    both("mid_bar_node", x330)
    both("shelf_strap_anchor_fixed", (x330[0], x330[1] + 12, 330.0))
    for z in (80.0, 250.0, 420.0):
        s = stay_xyz(z)
        both(f"load_wing_lash_z{int(z)}", (s[0], s[1] + 12, z))
    both("bag_anchor_low", (stay_xyz(60)[0], stay_xyz(60)[1] + 12, 60.0))
    both("bag_anchor_mid", (x330[0], x330[1] + 12, 330.0))
    hp["hipbelt_pivot"] = r3((0.0, stay_xyz(Z_IC)[1] - 25.0, Z_IC))
    hp["rack_lock_pawl_upper_bar"] = r3((0.0, y_on_axis(520.0) - 14.0, 520.0))
    hp["pulley_fixed_guide_A"] = r3((-18.0, stay_xyz(PULLEY_FIXED_Z)[1] - 12.0, PULLEY_FIXED_Z))
    hp["pulley_fixed_guide_C"] = r3((18.0, stay_xyz(PULLEY_FIXED_Z)[1] - 12.0, PULLEY_FIXED_Z))
    hp["pulley_cam_buckle_R"] = r3((stay_xyz(150)[0] - 10.0, stay_xyz(150)[1] - 20.0, 150.0))
    hp["pulley_cam_buckle_L_alt"] = r3((-(stay_xyz(150)[0] - 10.0), stay_xyz(150)[1] - 20.0, 150.0))
    hp["upper_bar_node_R"] = r3(stay_xyz(520.0))
    hp["upper_bar_node_L"] = r3((-stay_xyz(520)[0], stay_xyz(520)[1], 520.0))
    return {
        "coordinate_system": {
            "name": "FCS (frame coordinate system), identical to huntkit.fea.frames",
            "origin": "midpoint between left and right stay-foot centreline points",
            "x": "lateral, + toward the WEARER'S RIGHT",
            "y": "fore-aft, + AFT (away from the wearer's back, toward the bag)",
            "z": "up (wearer standing erect)",
            "units": "mm",
        },
        "datums": {"iliac_crest_z": Z_IC,
                   "yoke_drop_below_C7_mm": YOKE_DROP,
                   "torso_definition": "C7 vertebra to top of iliac crest, measured along the spine"},
        "members_topology": {
            "stay_lower_R": {"from": r3(FOOT), "to": r3(ELBOW), "note": "straight tube, bonded into foot boot and elbow"},
            "stay_upper_R": {"from": r3(ELBOW), "to": r3(STAY_TOP), "note": "straight tube; bore receives crown leg (UHMWPE bushings at top and at z~380)"},
            "stay_lower_L": {"mirror_of": "stay_lower_R"},
            "stay_upper_L": {"mirror_of": "stay_upper_R"},
            "lumbar_plate": {"z_range": [50.0, 190.0], "x_range": [-125.0, 125.0],
                             "note": "cfrp_plate_pm45 shear web bonded across both stays (closes the torsion box; carries hipbelt pivot)"},
            "mid_bar": {"from": r3((-x330[0], x330[1], 330)), "to": r3(x330),
                        "note": "cross tube; shelf-strap and bag-mid anchors sit AT its nodes (no mid-span loads)"},
            "upper_bar": {"from": r3((-115, y_on_axis(520), 520)), "to": r3((115, y_on_axis(520), 520)),
                          "note": "cross tube 10 mm below stay tops; carries the rack-lock pawl housing (release toggle cord to the left shoulder strap)"},
            "crown": {"legs_x": [-115.0, 115.0], "leg_length_along_axis": CROWN_LEG,
                      "axis_unit_vector_yz": [round(float(u_axis[0]), 4), round(float(u_axis[1]), 4)],
                      "top_bar": "cross tube joining leg tops; lifter anchors at x=+/-70; bag top buckles at x=+/-70; extension-post sockets at leg tops",
                      "spine": f"cfrp_plate_quasi_iso 3 mm centre spine, top bar down {SPINE_LEN:.0f} mm; carries the yoke, the pa66_gf30 toothed rack ({RACK_PITCH:g} mm pitch, bonded + screwed into plate inserts) and the moving pulley guide B at its bottom end",
                      "retention": "3:1 webbing pulley (adjust, continuous, while worn) + two-way toothed-rack/pawl positive lock; see crown_retention",
                      "travel_mm": round(TORSO_IN[1] * IN - TORSO_IN[0] * IN, 1),
                      "positions": "continuous (lock resolution 4 mm); table lists 0.5 in reference settings"},
            "extension_posts_accessory": {"length_mm": 220.0,
                                          "note": "ACCESSORY (owner 2026-11-01): two plug-in posts + bar, LASH/FLAG POINTS ONLY (antlers, tall loads, orange flag). Load lifters NEVER move to the posts; they stay on the crown top bar at every setting (IP: Mystery Ranch US 10,952,523). Sockets in the crown top bar stay on every frame; not in base weight"},
        },
        "hard_points": hp,
        "crown_settings": settings,
        "crown_retention": crown_retention(),
        "fea_handoff_notes": [
            "Torso 23 in needs yoke z=654; crown puts it there with the top bar at z=804 (FEA demo warned frame >= 634 mm).",
            "Single-stay set-down failed at the lumbar bar in the demo: replace the lumbar tube with the pm45 lumbar plate (closed torsion box).",
            "Meat-shelf heavy-low failed at mid-stay: shelf straps now anchor at the mid-bar node (z=330), not mid-span.",
            "Bonded elbow peel (Volkersen) was the critical bond: elbow fitting should be a sleeve in shear with >= 25 mm overlap each side, no peel.",
            "No holes in carbon tubes: the toothed rack is a PA66-GF30 strip on the crown spine plate; all fasteners go through bonded Ti/Al inserts in plates.",
            "Crown retention load to resist (see crown_retention.required_capacity_n): extension 1001 N, compression 1334 N, applied at the pawl on the upper bar (z 520) and reacted by the crown spine.",
            "Crown legs: check bending at the stay socket in tall_load with min overlap 150 mm.",
        ],
    }



# ============================================================================ 2. BAG v3: TEARDROP ROLL-TOP
# Research basis: docs/research/pack_market_2026.md §5 (silhouette), §7.3 (bag), §8 Direction A.
# The bag is a loft of mixed superellipse rings stacked along z. Each ring has
#   half-width a(t), depth d(t) and a frame-side face at y_f(z) (follows the stay axis);
#   outer (aft) half exponent N_OUT (rounded), frame half exponent N_FRM (flat on the frame).
# t = 0..1 runs from the bag bottom to the FILL LINE (roll-top closed with 3 rolls).
BAG_Z0 = 35.0            # bag bottom sits on the shelf lip at the stay feet (v2 datum kept)
FRAME_GAP = 20.0         # frame-side face this far aft of the stay centreline (stay r 12.5 + 7.5 clearance)
N_OUT, N_FRM = 2.5, 5.0  # ring exponents: outer half rounded, frame half flat
T_PEAK = 0.60            # fullest section: shoulder blades (research §7.3)
HALF_W_CTRL = [(0.00, 128.0), (0.10, 136.0), (0.32, 160.0), (0.60, 185.0), (0.82, 181.0), (0.94, 168.0), (1.00, 150.0)]
DEPTH_CTRL = [(0.00, 178.0), (0.12, 200.0), (0.35, 240.0), (T_PEAK, 264.0)]
D_TOP = 62.0             # closed roll (3 turns of 210D + HDPE stiffener) ~ 60 mm thick
T_COLLAR = 0.70          # body/collar seam: below = shaped gores, above = straight roll-top collar
CLOSURE_MM = 150.0       # 3 rolls x 50 mm: collar fabric consumed by the closure, NOT counted as volume
COLLAR_HEM = 25.0        # stiffener hem above the closure
N_STATIONS = 81
RING_M = 1440
# panel split of each ring by arc fraction of its half (side gores take the rounded corners)
F_SIDE_OUT, F_SIDE_FRM = 0.17, 0.12
# diagonal signature (zip line + stretch band): right hip -> left shoulder
ZIP_T_LO = 0.20          # zip starts at the RIGHT face seam at this t
ZIP_DZ_TOP = 150.0       # zip ends at the LEFT face seam this far below the collar seam (below the rolled dome)
BAND_H = 170.0           # stretch band hangs this far (vertically) below the zip line
HAUL_PULLBACK = 250.0    # meat-mode pull-back, same as v2 (R-09)


def _pchip(ctrl):
    from scipy.interpolate import PchipInterpolator
    t, v = zip(*ctrl)
    return PchipInterpolator(t, v)


_AW = _pchip(HALF_W_CTRL)
_DR = _pchip(DEPTH_CTRL)


def half_width(t):
    return np.asarray(_AW(np.clip(t, 0, 1)), float)


def depth(t):
    t = np.asarray(t, float)
    rise = _DR(np.clip(t, 0, T_PEAK))
    u = np.clip((t - T_PEAK) / (1 - T_PEAK), 0, 1)
    dome = D_TOP + (DEPTH_CTRL[-1][1] - D_TOP) * np.sqrt(np.clip(1 - u ** 2, 0, 1))
    return np.where(t <= T_PEAK, rise, dome)


def y_frame(z):
    z = np.atleast_1d(np.asarray(z, float))
    return np.array([stay_xyz(float(zz))[1] for zz in z]) + FRAME_GAP


def _F(n):
    return math.gamma(1 + 1 / n) ** 2 / math.gamma(1 + 2 / n)


def ring_area(t):
    """Exact mixed-superellipse area: each half is 2 a b F(n), b = d/2."""
    return half_width(t) * depth(t) * (_F(N_OUT) + _F(N_FRM))


def bag_volume_mm3(Hf, t1=1.0, n=4001):
    t = np.linspace(0, t1, n)
    return float(np.trapezoid(ring_area(t), t * Hf))


def solve_fill_height():
    lo, hi = 600.0, 2000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if litres(bag_volume_mm3(mid)) < TARGET_L else (lo, mid)
    return float(round((lo + hi) / 2))   # whole mm


def ring_xy(t, Hf, M=RING_M):
    """Ring at fraction t: theta 0..pi = outer (aft) half from the wearer's RIGHT (+x) over to the
    left; pi..2pi = frame half back to the right. Returns (M,3) points and z."""
    z = BAG_Z0 + t * Hf
    a, d = float(half_width(t)), float(depth(t))
    b = d / 2
    yc = float(y_frame(z)[0]) + b
    th = np.linspace(0, 2 * np.pi, M, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    n = np.where(s >= 0, N_OUT, N_FRM)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = yc + b * np.sign(s) * np.abs(s) ** (2 / n)
    return np.column_stack([x, y, np.full(M, z)]), z


def ring_seams(P):
    """Arc positions of the 4 seams on a ring (outer half = first M/2 points)."""
    M = len(P)
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    Lo, Ltot = s[M // 2], s[-1]
    Lb = Ltot - Lo
    return {"s": s, "Lo": Lo, "Lb": Lb, "Ltot": Ltot,
            "face_R": F_SIDE_OUT * Lo, "face_L": (1 - F_SIDE_OUT) * Lo,
            "frm_L": Lo + F_SIDE_FRM * Lb, "frm_R": Lo + (1 - F_SIDE_FRM) * Lb}


def point_at_s(P, s_arr, sq):
    sq = np.mod(sq, s_arr[-1])
    Pc = np.vstack([P, P[:1]])
    return np.stack([np.interp(sq, s_arr, Pc[:, k]) for k in range(3)], -1)


def outer_point_at_x(t, Hf, x):
    """Point on the OUTER half of ring t with lateral coordinate x (|x| < a)."""
    z = BAG_Z0 + t * Hf
    a, d = float(half_width(t)), float(depth(t))
    b = d / 2
    yc = float(y_frame(z)[0]) + b
    u = np.clip(np.abs(np.asarray(x, float)) / a, 0, 1)
    return np.stack([np.asarray(x, float), yc + b * (1 - u ** N_OUT) ** (1 / N_OUT), np.full(np.shape(x), z)], -1)


def build_stations(Hf):
    rows = []
    for t in np.linspace(0, 1, N_STATIONS):
        z = BAG_Z0 + t * Hf
        rows.append([round(float(z), 2), round(float(half_width(t)), 2), round(float(y_frame(z)[0]), 2),
                     round(float(depth(t)), 2)])
    return rows


ROLLED_DOME_MM = 140.0   # rolled-down state: dome starts this far below the collar seam
ROLLED_TOP_ABOVE = 40.0  # ... and the closed roll sits this far above it


def rolled_profile(Hf, n=61):
    """Daily-carry state: collar rolled down onto the body. Same rings as the full bag up to
    z_r = collar seam - ROLLED_DOME_MM, then the roll pulls the top into a dome (depth -> D_TOP,
    width -> 88 %) that ends ROLLED_TOP_ABOVE above the collar seam. Returns stations + volume."""
    zc = BAG_Z0 + T_COLLAR * Hf
    zr, zt = zc - ROLLED_DOME_MM, zc + ROLLED_TOP_ABOVE
    tr = (zr - BAG_Z0) / Hf
    rows, A, Z = [], [], []
    for z in np.r_[np.linspace(BAG_Z0, zr, n)[:-1], np.linspace(zr, zt, 21)]:
        if z <= zr:
            t = (z - BAG_Z0) / Hf
            a, d = float(half_width(t)), float(depth(t))
        else:
            u = (z - zr) / (zt - zr)
            a = float(half_width(tr)) * (1 - 0.12 * u ** 2)
            d = D_TOP + (float(depth(tr)) - D_TOP) * math.sqrt(max(1 - u ** 2, 0.0))
        rows.append([round(float(z), 2), round(a, 2), round(float(y_frame(z)[0]), 2), round(d, 2)])
        A.append(a * d * (_F(N_OUT) + _F(N_FRM)))
        Z.append(z)
    return rows, float(np.trapezoid(A, Z))


def mesh_check_volume(Hf, n=241, M=720):
    """Independent check: polygon (shoelace) area of the discretised rings, trapezoid in z."""
    A, Z = [], []
    for t in np.linspace(0, 1, n):
        P, z = ring_xy(t, Hf, M)
        x, y = P[:, 0], P[:, 1]
        A.append(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
        Z.append(z)
    return float(np.trapezoid(A, Z))


def bag_cg(Hf, n=201, M=720):
    """Uniform-fill centroid (y, z) for the FEA bag-load placement."""
    V = Sy = Sz = 0.0
    dz = Hf / (n - 1)
    for t in np.linspace(0, 1, n):
        P, z = ring_xy(t, Hf, M)
        x, y = P[:, 0], P[:, 1]
        cross = x * np.roll(y, -1) - np.roll(x, -1) * y
        A = 0.5 * cross.sum()
        cy = ((y + np.roll(y, -1)) * cross).sum() / (6 * A)
        w = abs(A) * dz
        V += w; Sy += w * cy; Sz += w * z
    return Sy / V, Sz / V


# ---------------------------------------------------------------- gore patterns from the 3D shape
def gore_panel(Hf, t0, t1, s_from, s_to, n=60):
    """Flat pattern of the surface strip between two seam positions (functions ring -> arc s),
    from t0 to t1. Pattern v = true length of the panel's centre line; half-widths = half the
    true cross-arc. Returns outline edges (bottom, right, top, left in pattern coords: right =
    the s_from side) plus 3D seam curves and the seam-length mismatch (ease) per side."""
    ts = np.linspace(t0, t1, n)
    mids, seamA, seamB, widths = [], [], [], []
    for t in ts:
        P, _ = ring_xy(t, Hf)
        sm = ring_seams(P)
        sa, sb = s_from(sm), s_to(sm)
        if sb < sa:
            sb += sm["Ltot"]
        widths.append(sb - sa)
        mids.append(point_at_s(P, sm["s"], (sa + sb) / 2))
        seamA.append(point_at_s(P, sm["s"], sa))
        seamB.append(point_at_s(P, sm["s"], sb))
    mids, seamA, seamB, widths = map(np.asarray, (mids, seamA, seamB, widths))
    v = np.r_[0, np.cumsum(np.linalg.norm(np.diff(mids, axis=0), axis=1))]
    right = np.column_stack([widths / 2, v])
    left = np.column_stack([-widths / 2, v])
    L3 = lambda Q: float(np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1)))  # noqa: E731
    L2 = lambda Q: float(np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1)))  # noqa: E731
    ease = {"seam_from_3d_mm": round(L3(seamA), 1), "seam_from_pattern_mm": round(L2(right), 1),
            "seam_to_3d_mm": round(L3(seamB), 1), "seam_to_pattern_mm": round(L2(left), 1)}
    return {"right": right, "left": left, "v": v, "w": widths, "ts": ts, "seamA": seamA, "seamB": seamB,
            "mids": mids, "ease": ease}


def gore_piece(name, g, **kw):
    R, L = g["right"], g["left"]
    edges = [("bottom", [tuple(L[0]), tuple(R[0])]),
             ("right", [tuple(p) for p in R]),
             ("top", [tuple(R[-1]), tuple(L[-1])]),
             ("left", [tuple(p) for p in L[::-1]])]
    return Piece.from_edges(name, edges, **kw)


def diagonal(Hf):
    """Zip line + stretch band in the x-z projection of the outer face, then mapped to 3D."""
    t_c = T_COLLAR
    z_c = BAG_Z0 + t_c * Hf
    z_lo = BAG_Z0 + ZIP_T_LO * Hf
    z_hi = z_c - ZIP_DZ_TOP

    def face_seam_x(z, side):
        t = (z - BAG_Z0) / Hf
        P, _ = ring_xy(t, Hf)
        sm = ring_seams(P)
        return float(point_at_s(P, sm["s"], sm["face_R" if side > 0 else "face_L"])[0])
    xR, xL = face_seam_x(z_lo, 1), face_seam_x(z_hi, -1)

    def x_zip(z):
        return xR + (xL - xR) * (np.asarray(z, float) - z_lo) / (z_hi - z_lo)
    zz = np.linspace(z_lo, z_hi, 60)
    zip3 = np.array([outer_point_at_x((z - BAG_Z0) / Hf, Hf, x_zip(z)) for z in zz])
    # band lower edge: zip line shifted down BAND_H, clipped to the face seams
    zb = zz - BAND_H
    xb = []
    for z, x in zip(zb, x_zip(zz)):
        xb.append(float(np.clip(x, face_seam_x(z, -1), face_seam_x(z, 1))))
    band3 = np.array([outer_point_at_x((z - BAG_Z0) / Hf, Hf, x) for z, x in zip(zb, xb)])
    L = float(np.sum(np.linalg.norm(np.diff(zip3, axis=0), axis=1)))
    ang = math.degrees(math.atan2(abs(xR - xL), z_hi - z_lo))
    return {"z_lo": z_lo, "z_hi": z_hi, "x_R": xR, "x_L": xL, "zip3": zip3, "band3": band3,
            "zip_len": L, "angle_from_vertical_deg": ang, "x_zip": x_zip, "z_collar": z_c,
            "band_lower_xz": np.column_stack([xb, zb])}


# ============================================================================ 3. PANELS
def shard(name, pts, **kw):
    return Piece(name, outline=pts, grain=90.0, seam_allowance_mm=8.0, **kw)


def build_panels(Hf, diag):
    from shapely.geometry import LineString, Polygon as SPoly
    from shapely.ops import split
    P = []   # (piece, zone, notes, sub_assembly, mass_kind)
    info = {}

    def add(p, zone, sub, notes="", kind="fabric", thickness_mm=None):
        P.append({"piece": p, "zone": zone, "sub": sub, "notes": notes, "kind": kind, "t": thickness_mm})

    tc = T_COLLAR
    # ---- body gores (developed from the 3D teardrop, gore method)
    g_frm = gore_panel(Hf, 0.0, tc, lambda m: m["frm_L"], lambda m: m["frm_R"])
    g_face = gore_panel(Hf, 0.0, tc, lambda m: m["face_R"], lambda m: m["face_L"])
    g_side = gore_panel(Hf, 0.0, tc, lambda m: m["frm_R"] - m["Ltot"], lambda m: m["face_R"])
    info["gores"] = {"frame_side": g_frm["ease"], "outer_face": g_face["ease"], "side_gore": g_side["ease"]}
    fr = gore_piece("bag frame-side panel", g_frm, grain=90.0, seam_allowance_mm=12.0, material_id="challenge_ultra_200",
                    piece_id="B-01", quantity=1)
    add(fr, "frame side / meat contact (laminate on the HIDDEN face only)", "main bag",
        "gore from the 3D teardrop; follows the stay S-curve. 6 Hypalon frame-link tabs + hydration sleeve sewn flat first")
    # outer face split along the diagonal zip line (pattern coords: u = +right of centre, v = centre-line length)
    face_poly = SPoly(np.vstack([g_face["right"], g_face["left"][::-1]]))
    # zip line in pattern coords: at each zip z, u = arc from the face centre (+ toward the wearer's right)
    zu, zv = [], []
    for p3 in diag["zip3"]:
        t = (p3[2] - BAG_Z0) / Hf
        Pq, _ = ring_xy(t, Hf)
        sm = ring_seams(Pq)
        k = int(np.argmin(np.linalg.norm(Pq[: RING_M // 2] - p3, axis=1)))
        s_mid = (sm["face_R"] + sm["face_L"]) / 2
        zu.append(s_mid - sm["s"][k])
        zv.append(float(np.interp(t, g_face["ts"], g_face["v"])))
    zl = np.column_stack([zu, zv])
    ext = np.vstack([zl[0] + (zl[0] - zl[1]) * 40, zl, zl[-1] + (zl[-1] - zl[-2]) * 40])
    halves = sorted(split(face_poly, LineString(ext)).geoms, key=lambda g: -g.centroid.x)
    info["zip_pattern_line"] = zl
    names = (("B-02a", "outer face, upper-right (above the diagonal zip)"),
             ("B-02b", "outer face, lower-left (below the diagonal zip; carries the stretch band + fly pocket)"))
    for (pid, nm), poly in zip(names, halves[:2]):
        pts = list(poly.exterior.coords)[:-1]
        add(Piece(nm, outline=pts, grain=90.0, seam_allowance_mm=12.0, material_id="cordura_330d_nylon66",
                  piece_id=pid, quantity=1),
            "outer face (solid colour)", "main bag",
            "gore from the 3D teardrop, split on the diagonal zip line (zip SA 10 mm)")
    add(gore_piece("side gore", g_side, grain=90.0, seam_allowance_mm=12.0, material_id="cordura_330d_nylon66",
                   piece_id="B-03", quantity=2, mirror=True),
        "sides (rounded corners of the teardrop)", "main bag",
        "floating side pocket, roll-top clip, hose port and lash tabs sewn flat first")
    # bottom: the t=0 ring, flat
    P0, _ = ring_xy(0.0, Hf, 240)
    add(Piece("bag bottom", outline=[(float(x), float(y)) for x, y in P0[:, :2]], grain=90.0, seam_allowance_mm=12.0,
              material_id="cordura_500d_nylon66", piece_id="B-05"),
        "bottom (abrasion)", "main bag", "flat teardrop oval; 2 drain grommets (8 mm) at the frame-side corners")
    # roll-top collar: straight tube = ring perimeter at the collar seam
    Pc, zc = ring_xy(tc, Hf)
    perim = ring_seams(Pc)["Ltot"]
    collar_h = (1 - tc) * Hf + CLOSURE_MM + COLLAR_HEM
    info["collar"] = {"perimeter_mm": round(perim, 1), "fabric_height_mm": round(collar_h, 1), "z_seam": round(zc, 1)}
    add(rect_panel("roll-top collar", perim, collar_h, 0.0, seam_allowance_mm=12.0, material_id="robic_100d_ripstop",
                   piece_id="B-06"),
        "roll-top", "main bag", f"one back seam; fill line {CLOSURE_MM:.0f} mm below the hem (3 rolls x 50 mm)")
    add(rect_panel("roll-top stiffener hem", perim, 2 * COLLAR_HEM + 20, 0.0, seam_allowance_mm=10.0,
                   material_id="cordura_330d_nylon66", piece_id="B-07"),
        "roll-top", "main bag", "folded hem housing a 0.8 x 20 mm HDPE strip (B-07s): clean roll, no flop; camo SH-03 overlay")
    add(rect_panel("diagonal zip storm strip", 30.0, diag["zip_len"] + 40, 0.0, seam_allowance_mm=8.0,
                   material_id="cordura_330d_nylon66", piece_id="B-08"),
        "diagonal zip", "main bag", "under-zip backing; the stretch band mouth is the storm flap (quiet, no garage needed)")
    add(rect_panel("hydration sleeve", 250.0, 430.0, 0.0, seam_allowance_mm=10.0, material_id="robic_100d_ripstop",
                   piece_id="B-09"),
        "interior", "main bag", "sewn to B-01; hose ports at the collar seam BOTH sides")
    add(rect_panel("frame-link tab", 50.0, 70.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon",
                   piece_id="B-10", quantity=6),
        "frame side", "main bag", "raw-edge Hypalon, laser-cut toggle slot: 2 hinge (bottom), 2 mid (z 330), 2 top (crown)")
    add(rect_panel("lash tab", 30.0, 50.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon",
                   piece_id="B-11", quantity=8),
        "side gores + face", "main bag", "laser-cut slot 25 x 5 mm; antler/cape lashing, rifle muzzle keepers both sides")

    # ---- diagonal stretch band (overload / bow-cam / quiver pocket): ruled surface, developed
    dev = develop_ruled_surface(diag["zip3"], diag["band3"], n=60)
    info["band_develop"] = {"max_strain": round(float(dev.max_strain), 4), "len_zip_edge_mm": round(dev.length_a_3d, 1),
                            "len_lower_edge_mm": round(dev.length_b_3d, 1)}
    band = dev.to_piece("diagonal stretch band", grain=0.0, seam_allowance_mm=10.0,
                        material_id="poly_spandex_stretch_woven_printable", piece_id="D-01")
    add(band, "signature: overload / bow-cam / pole pocket", "main bag",
        "mouth = upper edge along the zip (camo binding SH-B), lower edge + right end sewn to B-02b; "
        "cut 6 % short across (stretch 40 %) so it hugs flat when empty")

    # ---- camo accents (owner base camo on 630D printable): only where it wears
    shard_mat = "polyester_ht_630d_printable"
    add(shard("lower-corner shard (wraps the bottom corner)", [(0, 0), (200, 0), (250, 50), (170, 115), (70, 180), (0, 140)],
              material_id=shard_mat, piece_id="SH-01", quantity=2, mirror=True),
        "abrasion: lower corners (set-down, rock, deadfall)", "accents", "bottom edge caught in the bottom seam")
    add(rect_panel("band mouth binding (camo)", 32.0, dev.length_a_3d + 40, 0.0, seam_allowance_mm=0.0,
                   material_id=shard_mat, piece_id="SH-02"),
        "signature line: band mouth over the zip", "accents", "bias-cut 32 mm binding folded to 16 mm; it is the storm flap edge")
    add(shard("cam-cup shard", [(0, 0), (150, 0), (170, 70), (110, 150), (0, 120)], material_id=shard_mat,
              piece_id="SH-04", quantity=1),
        "abrasion: band lower end (bow cam, rifle butt, set-down)", "accents", "")
    add(rect_panel("roll-top band (camo)", perim * 0.5, 60.0, 0.0, seam_allowance_mm=0.0, material_id=shard_mat,
                   piece_id="SH-03"),
        "abrasion: roll-top (grab point, thrown down)", "accents", "overlay on B-07, outer face half only")
    add(shard("hipbelt wing-tip shard", [(0, 0), (110, 0), (140, 45), (110, 95), (0, 95), (25, 45)],
              material_id=shard_mat, piece_id="SH-05", quantity=2, mirror=True),
        "abrasion: hipbelt wing tips (arm swing, brush)", "accents", "same shape all sizes (sits at wing tip)")

    # ---- integrated rain fly (base pocket)
    fly_area = info_fly_area(Hf)
    side = math.sqrt(fly_area)
    add(rect_panel("rain fly (fitted, elastic hem)", side, side, 0.0, seam_allowance_mm=0.0,
                   material_id="silicone_coated_poly_ripstop_40d", piece_id="F-01"),
        "weather", "fly", f"pattern = covered bag surface x 1.12 ({fly_area / 1e6:.2f} m2); tethered in its base pocket")
    add(rect_panel("fly pocket", 190.0, 140.0, 20.0, seam_allowance_mm=10.0, material_id="cordura_330d_nylon66",
                   piece_id="F-02"),
        "weather", "fly", "BASE pocket under B-05, #5 coil zip along the bottom's aft edge (fly deploys upward over the bag); holds fly + orange flag sleeve")
    add(rect_panel("orange flag sleeve", 300.0, 120.0, 0.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop",
                   piece_id="F-03"),
        "safety", "fly", "ASSUMPTION: blaze-orange colourway of robic_210d; slides over the crown top bar / accessory posts")

    # ---- floating side pockets (x2): own back panel, haul wraps pass UNDER them
    sp = tapered_panel("side pocket face", 170.0, 150.0, 360.0, material_id="ultragrid_210d_uhmwpe_ripstop",
                       piece_id="P-01", quantity=2, mirror=True, seam_allowance_mm=10.0)
    add(sp, "side pockets", "pockets", "tripod / trekking poles / bottle; 3 mm shock-cord hem; drain eyelet")
    sp_g = sp.edge_length("left") + sp.edge_length("bottom") + sp.edge_length("right")
    add(rect_panel("side pocket gusset", sp_g, 50.0, 0.0, seam_allowance_mm=10.0, material_id="ultragrid_210d_uhmwpe_ripstop",
                   piece_id="P-02", quantity=2),
        "side pockets", "pockets", "U-strip; bellows 50 mm")
    add(tapered_panel("side pocket floating back", 170.0, 150.0, 360.0, material_id="robic_100d_ripstop",
                      piece_id="P-03", quantity=2, mirror=True, seam_allowance_mm=10.0),
        "side pockets", "pockets", "sewn to the side gore on its frame-side edge + bottom only; wraps run between it and the gore "
                                   "so cinching the bag never crushes the pocket (fixes P5)")

    # ---- hipbelt pockets (x2)
    hpf = tapered_panel("hipbelt pocket face", 180.0, 140.0, 110.0, material_id="cordura_330d_nylon66", piece_id="HP-01",
                        quantity=2, mirror=True, seam_allowance_mm=8.0)
    add(hpf, "hipbelt pockets", "hipbelt", "#8 coil zip along top; rangefinder fits; 330D (not stretch: fixes the thin-pocket complaint)")
    hpg = hpf.edge_length("left") + hpf.edge_length("bottom") + hpf.edge_length("right")
    add(rect_panel("hipbelt pocket gusset", hpg, 55.0, 0.0, seam_allowance_mm=8.0, material_id="cordura_330d_nylon66",
                   piece_id="HP-02", quantity=2), "hipbelt pockets", "hipbelt", "")

    # ---- load shelf LIP (light, fold-down) - replaces the v2 shelf + load wings
    add(rect_panel("shelf lip skin", SHELF_W, SHELF_D, {"tl": 30, "tr": 30}, seam_allowance_mm=10.0, material_id="challenge_ultra_200",
                   piece_id="S-01", quantity=2),
        "meat shelf lip", "shelf", "two layers around the HDPE stiffener; hinges on the shelf pivots; folds flat under the bag in carry mode")
    add(rect_panel("shelf lip stiffener (cut, not sewn)", SHELF_W - 20, SHELF_D - 20, 20.0, seam_allowance_mm=0.0,
                   material_id="hdpe_sheet", piece_id="S-05"),
        "meat shelf lip", "shelf", f"{SHELF_HDPE_T} mm HDPE", kind="sheet", thickness_mm=SHELF_HDPE_T)

    # ---- hipbelt (size M shown; grade table in panels.yaml)
    wing_len = HIPBELT_WINGS["M"]
    for pid, nm, mat, kind, t, notes in (
            ("H-01", "hipbelt wing outer shell", "cordura_330d_nylon66", "fabric", None, "binding on bottom edge"),
            ("H-02", "hipbelt wing body face", "spacer_mesh_3d", "fabric", None, ""),
            ("H-03", "hipbelt wing load foam", "eva_foam_45c", "foam", 6.0, "die-cut (outsource); inset 8 mm"),
            ("H-04", "hipbelt wing comfort foam", "eva_foam_30c", "foam", 5.0, "die-cut (outsource); inset 6 mm"),
            ("H-05", "hipbelt wing stiffener", "hdpe_sheet", "sheet", 1.0, "1.0 mm HDPE, rounded corners; carries load to the iliac crest")):
        sa = 10.0 if kind == "fabric" else 0.0
        inset = {"H-03": 8.0, "H-04": 6.0, "H-05": 12.0}.get(pid, 0.0)
        p = tapered_panel(nm, 140.0 - 2 * inset, 95.0 - 2 * inset, wing_len - inset, material_id=mat, piece_id=pid,
                          quantity=2, mirror=True, seam_allowance_mm=sa)
        add(p, "hipbelt wings (graded S-XL)", "hipbelt", notes, kind=kind, thickness_mm=t)
    for pid, nm, mat, kind, t in (("H-06", "lumbar pad shell", "cordura_330d_nylon66", "fabric", None),
                                  ("H-07", "lumbar pad face (grippy)", "spacer_mesh_3d", "fabric", None),
                                  ("H-08", "lumbar pad foam, stage 1", "eva_foam_45c", "foam", 8.0),
                                  ("H-09", "lumbar stage-2 wedge insert (removable)", "eva_foam_45c", "foam", 8.0)):
        w_, h_ = (160.0, 140.0) if pid != "H-09" else (130.0, 90.0)
        add(rect_panel(nm, w_, h_, 25.0, material_id=mat, piece_id=pid, seam_allowance_mm=10.0 if kind == "fabric" else 0.0),
            "hipbelt centre: FIRM 2-stage lumbar (fixes the soft-lumbar complaint, P1)", "hipbelt",
            "stage 2 wedge slides into a sleeve behind stage 1 for > 65 lb loads", kind=kind, thickness_mm=t)

    # ---- shoulder harness: J-strap (default) + S-strap (curved, alternate)
    def strap(name, s_curve):
        L, wt, wb = 440.0, 72.0, 58.0
        n = 12
        left, right = [], []
        for i in range(n + 1):
            z = L * i / n
            w = wt + (wb - wt) * i / n
            off = (35.0 * math.sin(math.pi * i / n) if s_curve else 18.0 * math.sin(math.pi * i / n * 0.5))
            left.append((off - w / 2, z)); right.append((off + w / 2, z))
        return left + right[::-1]
    for alt, s_curve in (("J", False), ("S", True)):
        for pid, nm, mat, kind, t in ((f"HS-{alt}1", f"{alt}-strap shell", "cordura_330d_nylon66", "fabric", None),
                                      (f"HS-{alt}2", f"{alt}-strap face", "spacer_mesh_3d", "fabric", None),
                                      (f"HS-{alt}3", f"{alt}-strap load foam", "eva_foam_45c", "foam", 5.0),
                                      (f"HS-{alt}4", f"{alt}-strap comfort foam", "eva_foam_perforated", "foam", 5.0)):
            p = Piece(nm, outline=strap(nm, s_curve), material_id=mat, piece_id=pid, quantity=2, mirror=True,
                      seam_allowance_mm=10.0 if kind == "fabric" else 0.0)
            add(p, f"shoulder harness ({'J unisex, default' if alt == 'J' else 'S curved, alternate'})",
                f"harness_{alt}", "sternum rail (POM) sewn into inner edge", kind=kind, thickness_mm=t)
    add(rect_panel("yoke cover", 260.0, 120.0, 30.0, material_id="cordura_330d_nylon66", piece_id="HS-05", quantity=2,
                   seam_allowance_mm=10.0), "yoke", "harness_common", "sandwich over the yoke plate; quick-connect for J/S straps")

    # ---- back panels
    for pid, nm, w, h, mat, kind, t in (("BP-01", "lower back panel face", 230.0, 300.0, "spacer_mesh_3d", "fabric", None),
                                        ("BP-02", "lower back panel foam", 210.0, 280.0, "xlpe_foam", "foam", 6.0),
                                        ("BP-03", "upper back pad face (on crown)", 210.0, 180.0, "spacer_mesh_3d", "fabric", None),
                                        ("BP-04", "upper back pad foam", 190.0, 160.0, "xlpe_foam", "foam", 6.0),
                                        ("BP-05", "back panel shell", 230.0, 300.0, "robic_210d_ripstop", "fabric", None)):
        add(rect_panel(nm, w, h, 30.0, material_id=mat, piece_id=pid, seam_allowance_mm=10.0 if kind == "fabric" else 0.0),
            "back panel", "back_panel", "perforated foam channels; wraps stays with 6 tabs", kind=kind, thickness_mm=t)

    # ---- rifle carry (optional, either side)
    add(tapered_panel("rifle butt boot body", 300.0, 260.0, 200.0, material_id="cordura_500d_nylon66", piece_id="R-01",
                      seam_allowance_mm=10.0), "rifle carry", "carry", "rolled into a cone; clips to EITHER hipbelt wing")
    add(rect_panel("rifle-boot mount tab", 40.0, 60.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon",
                   piece_id="R-03", quantity=4),
        "rifle carry mounts", "hipbelt", "2 per hipbelt wing (both sides); muzzle keepers = lash tabs B-11 on both gores")
    add(rect_panel("rifle boot bottom", 100.0, 60.0, 30.0, material_id="tpu_coated_nylon_840d", piece_id="R-02",
                   seam_allowance_mm=10.0), "rifle carry", "carry", "drain eyelet")

    # ---- optional stable lid / hip pack (ACCESSORY, not in base)
    add(rect_panel("lid top", 300.0, 240.0, 50.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop", piece_id="L-01"),
        "lid accessory", "lid", "camo shard optional")
    add(rect_panel("lid underside", 300.0, 240.0, 50.0, seam_allowance_mm=10.0, material_id="cordura_330d_nylon66", piece_id="L-02"),
        "lid accessory", "lid", "")
    lid_top = rect_panel("lt", 300.0, 240.0, 50.0)
    add(rect_panel("lid gusset", lid_top.seam_perimeter_mm, 70.0, 0.0, seam_allowance_mm=10.0,
                   material_id="cordura_330d_nylon66", piece_id="L-03"),
        "lid accessory", "lid", "#8 AquaGuard zip across the front 260 mm")
    return P, info


SHELF_W, SHELF_D, SHELF_HDPE_T = 260.0, 200.0, 1.0
HIPBELT_SIZES = {"S": (26, 30), "M": (30, 34), "L": (34, 38), "XL": (38, 42)}  # hip circ. at iliac crest, in
HIPBELT_PAD_FRACTION = 0.72  # ASSUMPTION: padded length (wings+centre) = 72 % of hip circumference
LUMBAR_CENTRE = 140.0
HIPBELT_WINGS = {k: round((HIPBELT_PAD_FRACTION * (sum(v) / 2) * IN - LUMBAR_CENTRE) / 2)
                 for k, v in HIPBELT_SIZES.items()}
_HF = {}


def surface_area(Hf, t0=0.0, t1=1.0, n=161, seams=None):
    """Lateral surface area of the teardrop between t0 and t1 (sum of ring perimeters x slant)."""
    A = 0.0
    prev = None
    for t in np.linspace(t0, t1, n):
        P, z = ring_xy(t, Hf, 360)
        if prev is not None:
            dP = np.linalg.norm(P - prev, axis=1)
            seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
            A += float(np.sum(seg * dP))
        prev = P
    return A


def info_fly_area(Hf):
    """Fly covers the outer half + side gores + top dome (not the frame-side panel), +12 % fit/hem."""
    return 0.80 * surface_area(Hf) * 1.12


# ============================================================================ 4. MASSES
def piece_mass(rec):
    p = rec["piece"]
    m = MAT.load(p.material_id)
    a_m2 = p.area_mm2 / 1e6  # cut-line area (what you buy)
    qty = p.quantity          # contract: quantity = TOTAL pieces (mirror pairs included)
    if rec["kind"] == "fabric":
        return a_m2 * m.require("areal_density_gsm") * qty
    rho = m.require("density_kg_m3")
    return a_m2 * (rec["t"] / 1000.0) * rho * 1000.0 * qty


def hw(id_, n=1, length_m=None):
    m = MAT.load(id_)
    if length_m is not None:
        return m.require("mass_g_m") * length_m
    return m.require("mass_g") * n


YOKE_OUTLINE = [(-108, -18), (-84, -46), (84, -46), (108, -18), (96, 34), (42, 50), (-42, 50), (-96, 34)]
YOKE_AREA_MM2 = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(YOKE_OUTLINE, YOKE_OUTLINE[1:] + YOKE_OUTLINE[:1])))
FRAME_ALLOCATION_G = 650.0   # orchestrator: use 650 g until frame.yaml is re-sized (target 550-700 g)


def haul_wraps(Hf, topo):
    """3 frame-anchored wraps: compression in carry mode, meat sling in haul mode (one strap set).
    W1/W2 climb from a low RIGHT anchor to a higher LEFT anchor, parallel in sense to the SPINE zip
    (right hip -> left shoulder): angled bands instead of the dated horizontal strap stack (research §5)."""
    hp = topo["hard_points"]
    cs19 = min(topo["crown_settings"], key=lambda c: abs(c["torso_in"] - 19.0))
    crown = [115.0, cs19["lifter_anchor_R"][1], cs19["crown_top_z"]]
    spec = [("W1", "load_wing_lash_z80_R", hp["load_wing_lash_z80_R"], "load_wing_lash_z250_L", hp["load_wing_lash_z250_L"]),
            ("W2", "load_wing_lash_z250_R", hp["load_wing_lash_z250_R"], "load_wing_lash_z420_L", hp["load_wing_lash_z420_L"]),
            ("W3", "crown top bar R (moves with torso)", crown, "crown top bar L (moves with torso)", [-crown[0]] + crown[1:])]
    out = []
    for wid, nR, aR, nL, aL in spec:
        z = (aR[2] + aL[2]) / 2
        t = (z - BAG_Z0) / Hf
        P, _ = ring_xy(t, Hf)
        sm = ring_seams(P)
        outer = sm["Lo"] + 2 * F_SIDE_FRM * sm["Lb"]     # around both sides + the face
        rise = abs(aL[2] - aR[2])
        path = math.hypot(outer, rise)                    # helical run over the face
        gap = abs(float(y_frame(aR[2])[0]) - aR[1]) + abs(float(y_frame(aL[2])[0]) - aL[1])
        carry = path + gap
        haul = carry + 2 * HAUL_PULLBACK + 120.0          # + the pulled-back gap both sides (meat girth)
        out.append({"id": wid, "anchor_R": nR, "anchor_L": nL, "z_R_at_19in": round(aR[2], 1),
                    "z_L_at_19in": round(aL[2], 1), "z_at_19in": round(z, 1),
                    "anchor": nR, "hardware": "ladder lock at R anchor, aluminium G-hook at L anchor (HAUL family)",
                    "carry_path_mm": round(carry), "haul_path_mm": round(haul), "cut_length_mm": round(haul + 250)})
    return out


def weight_budget(P, Hf, diag, wraps, info):
    sub_mass = {}
    for rec in P:
        sub_mass.setdefault(rec["sub"], 0.0)
        sub_mass[rec["sub"]] += piece_mass(rec)
    rows = []

    def row(group, item, g, basis):
        rows.append({"group": group, "item": item, "mass_g": round(g, 1), "basis": basis})

    row("frame (allocation, FEA re-sizing)", "carbon frame: stays, crown + post sockets, bars, lumbar plate, nodes, inserts, feet",
        FRAME_ALLOCATION_G, "ASSUMPTION: allocation 650 g (leader-calibrated standard, target 550-700 g); frame.yaml governs when re-sized")
    row("torso adjust", "toothed rack PA66-GF30 + Ti pawl, spring, POM housing, release cord + toggle", 50,
        "computed rack 27 g (pa66_gf30 rho) + ASSUMPTION 23 g pawl/housing (v2)")
    row("torso adjust", "3:1 pulley: 25 mm poly webbing 1.4 m, 3 UHMWPE-lined guides, metal cam buckle",
        hw("poly_webbing_25mm", length_m=1.4) + 9 + 12, "records; guides 3 g ea, cam 12 g ASSUMPTION (v2)")
    row("main bag", "fabric panels (B-*, D-01, collar, tabs)", sub_mass["main bag"], "computed: cut area x gsm")
    row("main bag", "#10 coil diagonal zip + 2 sliders", hw("coil_zipper_10", length_m=(diag["zip_len"] + 60) / 1000) + 12,
        "coil_zipper_10 g/m; sliders 6 g ea ASSUMPTION")
    perim = info["collar"]["perimeter_mm"]
    row("main bag", "roll-top: HDPE 0.8 x 20 mm strip, 2 x 25 mm side-release (ROLL family), 2 x 0.35 m webbing",
        0.8e-3 * 0.020 * perim / 1000 * MAT.load("hdpe_sheet").require("density_kg_m3") * 1000
        + hw("buckle_side_release_25mm", 2) + hw("poly_webbing_25mm", length_m=0.7), "records")
    row("main bag", "bag-frame link: 4 POM toggles on 25 mm webbing 4 x 0.15 m (3-slot Hypalon tabs set the length); 2 hinge quick-pins",
        4 * 3 + hw("poly_webbing_25mm", length_m=0.6) + 2 * 4, "records; toggles 3 g, quick-pins 4 g ASSUMPTION")
    row("main bag", "6 haul-wrap keeper loops (25 mm webbing x 80 mm, sewn into the gore seams)",
        hw("poly_webbing_25mm", length_m=0.48), "records")
    row("accents", "camo SH-01..05 (overlay mass)", sub_mass["accents"], "computed")
    row("rain fly", "fly + fly pocket + flag sleeve", sub_mass["fly"], "computed")
    row("rain fly", "fly elastic hem 3.0 m, #5 pocket zip + slider, tether", 3.0 * 3 + hw("coil_zipper_5", length_m=0.18) + 3 + 2,
        "elastic 3 g/m ASSUMPTION (no record); records")
    row("pockets", "floating side pockets x2", sub_mass["pockets"] + 2 * hw("cord_lock_spring") + hw("dyneema_cord_2mm", length_m=0.8),
        "computed + records")
    row("hipbelt (M)", "wings, 2-stage lumbar, hipbelt pockets, rifle tabs", sub_mass["hipbelt"], "computed (foams = area x t x rho)")
    row("hipbelt (M)", "50 mm webbing + buckle (HIP family), 2 #8 pocket zips, stabilizer straps",
        hw("nylon_webbing_50mm", length_m=0.9) + hw("buckle_side_release_50mm", 1) + hw("coil_zipper_8", length_m=0.4)
        + hw("poly_webbing_25mm", length_m=0.8) + 2 * hw("ladder_lock_25mm"), "records")
    row("hipbelt (M)", "centre plate + pivot latch (pa66_gf30 / POM)", 45, "ASSUMPTION (v2)")
    row("harness", "J-straps (default set)", sub_mass["harness_J"], "computed")
    row("harness", f"yoke cover + shaped yoke plate (cfrp 1.5 mm, {YOKE_AREA_MM2 / 1e6:.4f} m2)",
        sub_mass["harness_common"] + YOKE_AREA_MM2 / 1e6 * 1.5e-3 * 1550 * 1000,
        "computed: yoke outline YOKE_OUTLINE (same polygon as huntkit.viz3d) x 1.5 mm x 1550 kg/m3 (cfrp_plate_quasi_iso)")
    row("harness", "load lifters 25 mm poly + ladders, sternum Fidlock (QUICK family) + POM rails",
        hw("poly_webbing_25mm", length_m=0.9) + 2 * hw("ladder_lock_25mm") + hw("fidlock_magnetic_buckle_25mm") + 12
        + hw("poly_webbing_25mm", length_m=0.8), "records; rails 12 g ASSUMPTION")
    row("back panel", "lower + upper pads", sub_mass["back_panel"], "computed")
    row("load shelf lip", "lip skins + HDPE stiffener", sub_mass["shelf"], "computed")
    row("load shelf lip", "2 shelf straps 25 mm x 0.8 m + 2 metal cam buckles (SHELF family) + 2 drain grommets",
        hw("poly_webbing_25mm", length_m=1.6) + 2 * 12 + 2 * 1.5, "records; cam 12 g ASSUMPTION (v2), grommet 1.5 g ASSUMPTION")
    wrap_len = sum(w["cut_length_mm"] for w in wraps) / 1000
    row("haul wraps (= compression)", f"3 frame-anchored wraps, 25 mm coyote poly webbing {wrap_len:.2f} m",
        hw("poly_webbing_25mm", length_m=wrap_len), "records; lengths from the 3D teardrop (haul_wraps)")
    row("haul wraps (= compression)", "3 aluminium G-hooks (HAUL family) + 3 ladder locks", 3 * 4 + 3 * hw("ladder_lock_25mm"),
        "G-hook 4 g ASSUMPTION (no record); ladder lock record")
    row("misc", "thread (~3 % of soft goods) + labels", 0.03 * sum(v for k, v in sub_mass.items() if k not in ("carry", "lid")) + 8,
        "ASSUMPTION")
    tot = sum(r["mass_g"] for r in rows)
    carry = sub_mass["carry"] + hw("poly_webbing_25mm", length_m=0.6) + hw("ladder_lock_25mm")
    lid = sub_mass["lid"] + hw("aquaguard_zipper_8", length_m=0.26) + 4 * hw("fidlock_magnetic_buckle_25mm") \
        + hw("poly_webbing_25mm", length_m=1.4) + hw("buckle_side_release_25mm")
    groups = {}
    for r in rows:
        groups[r["group"]] = round(groups.get(r["group"], 0) + r["mass_g"], 1)
    return rows, groups, round(tot, 1), round(carry, 1), round(lid, 1)


# ============================================================================ 5. SMALL VOLUMES
def small_volumes(Hf):
    lid = rect_panel("lid", 300.0, 240.0, 50.0)
    sp = tapered_panel("sp", 170.0, 150.0, 360.0)
    hp = tapered_panel("hp", 180.0, 140.0, 110.0)
    body = litres(bag_volume_mm3(Hf, T_COLLAR))
    return {
        "body_to_collar_seam_L": round(body, 2),
        "lid_accessory_L": round(litres(panel_volume(lid, 70.0)), 2),
        "side_pocket_each_L": round(litres(panel_volume(sp, 50.0)), 2),
        "hipbelt_pocket_each_L": round(litres(panel_volume(hp, 55.0)), 2),
        "diagonal_band_pocket_L": None,   # filled in main(): developed area x 40 mm stretch loft (ASSUMPTION)
        "meat_bay_L": round(litres(SHELF_W * HAUL_PULLBACK * 600), 1),
    }


# ============================================================================ 6. WRITE + PLOT
HARDWARE_FAMILIES = [
    {"family": "HIP", "function": "hipbelt closure", "hardware": "50 mm side-release (the only 50 mm buckle)", "qty": 1,
     "feel": "biggest buckle, at the waist"},
    {"family": "ROLL", "function": "roll-top closure", "hardware": "25 mm side-release, black", "qty": 2,
     "feel": "the only plastic squeeze-buckles on the bag, high on the side gores"},
    {"family": "HAUL", "function": "3 haul wraps (= compression in carry mode, meat sling in haul mode)",
     "hardware": "aluminium G-hook at the left frame anchor + ladder lock at the right anchor, coyote webbing",
     "qty": 3, "feel": "metal hook, no squeeze; webbing colour differs from everything else"},
    {"family": "LINK", "function": "bag to frame (meat-mode release)", "hardware": "POM toggle through a 3-slot Hypalon tab (4; slot = length setting) + 2 bottom hinge quick-pins",
     "qty": 6, "feel": "toggle-and-slot, impossible to confuse with a buckle"},
    {"family": "SHELF", "function": "shelf-lip straps (bone-in quarter)", "hardware": "25 mm metal cam buckle", "qty": 2,
     "feel": "lever cam, low on the frame"},
    {"family": "QUICK", "function": "sternum strap, accessory lid", "hardware": "Fidlock-type magnetic 25 mm", "qty": "1 (+4 lid)",
     "feel": "magnetic snap, one-handed, silent"},
    {"family": "TRIM", "function": "lifters, stabilizers, harness", "hardware": "25 mm ladder locks", "qty": 6,
     "feel": "on the harness only"},
]


def _py(o):
    """numpy scalars/arrays -> plain Python for yaml.safe_dump."""
    if isinstance(o, dict):
        return {k: _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if isinstance(o, np.ndarray):
        return _py(o.tolist())
    if isinstance(o, np.generic):
        return o.item()
    return o


def main():
    hp_changes = HERE / "analysis" / "frame_hardpoint_changes.yaml"
    if hp_changes.exists():
        print(f"NOTE: {hp_changes} exists: reconcile frame hard points before release")
    Hf = solve_fill_height()
    _HF["Hf"] = Hf
    v_mm3 = bag_volume_mm3(Hf)
    v_chk = mesh_check_volume(Hf)
    diag = diagonal(Hf)
    topo = frame_topology()
    wraps = haul_wraps(Hf, topo)
    vols = small_volumes(Hf)
    P, info = build_panels(Hf, diag)
    band_piece = next(r["piece"] for r in P if r["piece"].piece_id == "D-01")
    vols["diagonal_band_pocket_L"] = round(litres(band_piece.seam_area_mm2 * 40.0), 2)  # ASSUMPTION 40 mm mean stretch loft
    rows, groups, total, carry, lid_g = weight_budget(P, Hf, diag, wraps, info)
    cg_y, cg_z = bag_cg(Hf)
    z_top = BAG_Z0 + Hf
    stations = build_stations(Hf)
    a_max = max(s[1] for s in stations)
    d_max = max(s[3] for s in stations)
    zc = BAG_Z0 + T_COLLAR * Hf
    rolled_rows, v_rolled = rolled_profile(Hf)
    vols["rolled_down_L"] = round(litres(v_rolled), 2)

    geom = {
        "meta": {"design": "Pack 5200", "version": "v3 SPINE (teardrop roll-top)", "owner": "pack-designer",
                 "generated_by": "designs/pack_5200/build_geometry.py", "date": "2026-11-01", "units": "mm, L, g",
                 "research": "docs/research/pack_market_2026.md (Direction A 'Spine')"},
        "frame": topo,
        "bag": {
            "type": "teardrop_rolltop",
            "description": ("loft of mixed superellipse rings (outer half n_out, frame half n_frm) along z; frame-side face "
                            "follows the stay axis; tapered in front view, teardrop in side view, domed roll-top closure"),
            # v2-compatible keys (envelope)
            "width_x": round(2 * a_max, 1), "height_z": Hf, "depth_y": round(d_max, 1), "bottom_corner_radius": 25.0,
            "origin_carry_mode": {"x_center": 0.0, "y_frame_side_panel": round(float(y_frame(BAG_Z0)[0]), 1), "z_bottom": BAG_Z0},
            "haul_mode_pullback_y_max": HAUL_PULLBACK,
            "profile": {
                "columns": ["z", "half_width_x", "y_frame_side", "depth_y"],
                "n_out": N_OUT, "n_frm": N_FRM,
                "ring": "x = a sgn(c)|c|^(2/n), y = y_frame + d/2 + (d/2) sgn(s)|s|^(2/n); n = n_out for s>=0 (aft half), n_frm for s<0",
                "t_collar": T_COLLAR, "z_collar_seam": round(zc, 1), "z_fill_line": round(z_top, 1),
                "stations": stations,
                "stations_rolled": rolled_rows,
                "rolled_note": ("daily-carry state: collar rolled down onto the body (dome formed by the roll); same "
                                "columns. The full 'stations' state is the counted 85.2 L"),
            },
            "seams": {"face_side_fraction_of_outer_half_arc": F_SIDE_OUT, "gore_fraction_of_frame_half_arc": F_SIDE_FRM,
                      "panels": "B-01 frame side | B-03 side gores (L/R) | B-02a/b outer face split by the diagonal zip | B-05 bottom | B-06 collar"},
            "rolltop": {"closure": "3 rolls, ends clip DOWN to the side gores (ROLL family): pulls the top into a dome",
                        "closure_allowance_mm": CLOSURE_MM, "roll_diameter_mm": 50.0,
                        "clip_z_below_fill_line_mm": 230.0, "collar": info["collar"],
                        "dome_mm": ROLLED_DOME_MM + ROLLED_TOP_ABOVE,
                        "rolled_down_volume_L": round(vols["rolled_down_L"], 1)},
            "diagonal": {
                "concept": "SPINE line: one #10 coil zip from the right hip to the left shoulder (ambidextrous access) "
                           "under the mouth of a full-length stretch band (overload / bow-cam / pole pocket)",
                "zip_start_right": [round(diag["x_R"], 1), round(float(diag["zip3"][0][1]), 1), round(diag["z_lo"], 1)],
                "zip_end_left": [round(diag["x_L"], 1), round(float(diag["zip3"][-1][1]), 1), round(diag["z_hi"], 1)],
                "zip_length_mm": round(diag["zip_len"], 1),
                "angle_from_vertical_deg": round(diag["angle_from_vertical_deg"], 1),
                "band_drop_mm": BAND_H,
                "zip_line_3d": [[round(float(v), 1) for v in p] for p in diag["zip3"][::4]],
                "band_lower_edge_3d": [[round(float(v), 1) for v in p] for p in diag["band3"][::4]],
                "band_develop": info["band_develop"],
            },
            "gore_seam_check": info["gores"],
            "side_zip": {"side": "NONE: replaced by the diagonal zip (one zip, reachable from either side)", "qty": 0},
            "cg_uniform_fill": {"y": round(cg_y, 1), "z": round(cg_z, 1),
                                "note": "for the FEA bag placement (v2 was y 180); full 85.2 L, uniform density"},
            "height_note": "one bag height (owner); roll-top gives the range from rolled-down to full",
        },
        "volumes": {
            "method": ("geometric: exact mixed-superellipse ring area a*d*(F(n_out)+F(n_frm)), F(n)=G(1+1/n)^2/G(1+2/n), "
                       "integrated over z from the bag bottom to the fill line (roll-top closed with 3 rolls)"),
            "main_bag_L": round(litres(v_mm3), 2), "main_bag_cu_in": round(cubic_inches(v_mm3)),
            "main_bag_polygon_check_L": round(litres(v_chk), 2),
            "counted_in_5200": ("main bag to the FILL LINE with the roll-top closed by 3 rolls (150 mm of collar fabric "
                                "is closure, not volume). Lid, pockets, band pocket and meat bay are NOT counted"),
            **vols,
            "total_with_pockets_L": round(litres(v_mm3) + 2 * vols["side_pocket_each_L"] + 2 * vols["hipbelt_pocket_each_L"]
                                          + vols["diagonal_band_pocket_L"], 1),
        },
        "lid": {"accessory": True, "footprint": [300.0, 240.0], "height": 70.0, "corner_radius": 50.0,
                "position": {"z_bottom": round(rolled_rows[-1][0] - 6, 1), "y_center": round(rolled_rows[-1][2] + D_TOP / 2 + 10, 1),
                             "note": "sits on the closed roll in the rolled-down (daily) state"},
                "attachment": "2 SHORT fixed rear tabs to the frame-side hem + 2 front Fidlocks to the roll-top clips: no long straps, no flop",
                "converts_to": "hip pack (stowed 25 mm waist strap)", "mass_g": lid_g},
        "side_pockets": {"type": "floating (own back panel; haul wraps run underneath)", "face_bottom_w": 170.0,
                         "face_top_w": 150.0, "height": 360.0, "bellows": 50.0,
                         "position": {"z_bottom": 90.0, "y_center_fraction_of_depth": 0.55}},
        "load_shelf": {"type": "fold-down lip (bone-in quarters); boned meat rides in the haul-wrap sling",
                       "floor_w_x": SHELF_W, "floor_d_y": SHELF_D, "z": 25.0, "y_from": 8.0, "hdpe_t_mm": SHELF_HDPE_T,
                       "straps": "aft lip corners -> shelf_strap_anchor_fixed (z=330), SHELF-family cam buckles"},
        "haul_wraps": wraps,
        "hardware_families": HARDWARE_FAMILIES,
        "hipbelt": {"sizes_hip_circ_in": HIPBELT_SIZES, "wing_length_mm": HIPBELT_WINGS, "lumbar_centre_w": LUMBAR_CENTRE,
                    "lumbar": "2-stage: EVA 45C stage 1 + removable EVA 45C wedge (stage 2)",
                    "pivot": "hipbelt_pivot hard point; free roll +/-8 deg with elastomer centring; wing cant 0/5/10 deg (3-position)"},
        "harness": {"padded_length": 440.0, "width_top": 72.0, "width_bottom": 58.0,
                    "options": ["J (unisex default)", "S (curved, 35 mm lateral offset)"], "sternum_rail_travel": 120.0},
        "weight": {"groups_g": groups, "total_g": total, "total_lb": round(total / 453.592, 2), "target_g": 2268,
                   "rifle_boot_optional_g": carry, "lid_accessory_g": lid_g, "extension_posts_accessory_g": 60,
                   "excluded_from_base": ["rifle boot (switchable, either side)", "lid / hip pack accessory",
                                          "extension posts accessory (ASSUMPTION ~60 g)"],
                   "rows": rows},
    }
    (HERE / "geometry.yaml").write_text("# GENERATED by build_geometry.py - do not hand-edit\n"
                                        + yaml.safe_dump(_py(geom), sort_keys=False, width=110, default_flow_style=None))

    plist = []
    for rec in P:
        p = rec["piece"]
        x0, y0, x1, y1 = p.bounds(cut=False)
        plist.append({"id": p.piece_id, "name": p.name, "sub_assembly": rec["sub"], "material_id": p.material_id,
                      "approx_size_mm": [round(x1 - x0), round(y1 - y0)],
                      "qty_total": p.quantity, "mirror_pair": p.mirror,
                      "seam_allowance_mm": p.seam_allowance_mm if not isinstance(p.seam_allowance_mm, dict) else p.seam_allowance_mm.get("default"),
                      "thickness_mm": rec["t"], "zone": rec["zone"],
                      "cut_area_m2_each": round(p.area_mm2 / 1e6, 4), "mass_g_total": round(piece_mass(rec), 1),
                      "notes": rec["notes"],
                      "seam_line_mm": [[round(float(x), 1), round(float(y), 1)] for x, y in p.outline]
                      if p.piece_id in ("B-01", "B-02a", "B-02b", "B-03", "D-01") else None})
    grade = {"hipbelt_wings": {"rule": "length grades; root/tip widths constant (140/95 mm)",
                               "wing_length_mm_by_size": HIPBELT_WINGS, "hip_circumference_in": HIPBELT_SIZES,
                               "pieces": ["H-01", "H-02", "H-03", "H-04", "H-05"]},
             "everything_else": "one size (universal frame and bag)"}
    wrap_cut = [{"use": f"haul wrap {w['id']} ({w['anchor']})", "material_id": "poly_webbing_25mm",
                 "colour": "coyote (HAUL family)", "length_mm": w["cut_length_mm"], "qty": 1} for w in wraps]
    pan = {"meta": {"design": "Pack 5200 v3 SPINE", "generated_by": "designs/pack_5200/build_geometry.py",
                    "note": ("approx_size = seam-line bounding box (mm). Body gores B-01/02a/02b/03 are DEVELOPED from the 3D "
                             "teardrop (gore method: pattern height = true centre-line length, widths = true cross-arcs); "
                             "seam_line_mm carries their true outlines. D-01 is develop_ruled_surface between the zip line and "
                             "the band's lower edge. qty_total counts mirror pairs (contract). Hipbelt pieces at size M."),
                    "piece_count_total": sum(x["qty_total"] for x in plist),
                    "gore_seam_check_mm": info["gores"], "band_develop": info["band_develop"]},
           "grading": grade, "panels": plist,
           "webbing_cut_list": wrap_cut + [
               {"use": "hipbelt strap", "material_id": "nylon_webbing_50mm", "length_mm": 900, "qty": 1},
               {"use": "load lifters", "material_id": "poly_webbing_25mm", "length_mm": 450, "qty": 2},
               {"use": "shelf-lip straps", "material_id": "poly_webbing_25mm", "length_mm": 800, "qty": 2},
               {"use": "roll-top clips", "material_id": "poly_webbing_25mm", "length_mm": 350, "qty": 2},
               {"use": "bag-frame link (toggles)", "material_id": "poly_webbing_25mm", "length_mm": 150, "qty": 4},
               {"use": "haul-wrap keeper loops", "material_id": "poly_webbing_25mm", "length_mm": 80, "qty": 6},
               {"use": "hip stabilizers", "material_id": "poly_webbing_25mm", "length_mm": 400, "qty": 2},
               {"use": "sternum", "material_id": "poly_webbing_25mm", "length_mm": 400, "qty": 2},
               {"use": "crown 3:1 pulley", "material_id": "poly_webbing_25mm", "length_mm": 1400, "qty": 1}]}
    (HERE / "panels.yaml").write_text("# GENERATED by build_geometry.py - do not hand-edit\n"
                                      + yaml.safe_dump(_py(pan), sort_keys=False, width=110, default_flow_style=None))
    plot(Hf, topo, geom, diag, P)
    print(f"fill height Hf = {Hf:.0f} mm ({Hf / IN:.1f} in); collar seam z {zc:.0f}; top z {z_top:.0f}")
    print(f"main bag {litres(v_mm3):.2f} L = {cubic_inches(v_mm3):.0f} cu in (polygon check {litres(v_chk):.2f} L)")
    print(f"max width {2 * a_max:.0f} mm ({2 * a_max / IN:.1f} in), max depth {d_max:.0f} mm ({d_max / IN:.1f} in)")
    print("diag:", {k: round(v, 1) for k, v in diag.items() if isinstance(v, float)}, info["band_develop"])
    print("gores:", info["gores"])
    print("small volumes:", vols)
    print("wraps:", wraps)
    print("cg:", round(cg_y, 1), round(cg_z, 1))
    print("weight groups:", groups)
    print(f"total {total:.0f} g = {total / 453.592:.2f} lb ; rifle boot {carry} g ; lid {lid_g} g")
    print("pieces:", pan["meta"]["piece_count_total"])


def plot(Hf, topo, geom, diag, P):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly

    SOLID = "#59604a"; SOLID_L = "#767d63"; SOLID_D = "#3c4132"
    CAMO = ["#ae9d6c", "#8b8148", "#c6b497", "#313120"]
    FR = "#1a1a1a"; DIM = "#b03a2e"; ZIP = "#d35400"; HAUL = "#a0804a"
    fig, axs = plt.subplots(1, 3, figsize=(16, 9.6), dpi=100, gridspec_kw={"width_ratios": [660, 1180, 660]})
    fig.suptitle("Pack 5200 v3 'SPINE': teardrop roll-top, diagonal zip + stretch band, frame-anchored haul wraps "
                 "(FCS mm; in)", fontsize=13, weight="bold")
    st = np.array(geom["bag"]["profile"]["stations"])
    z, a, yf, d = st[:, 0], st[:, 1], st[:, 2], st[:, 3]
    zc = geom["bag"]["profile"]["z_collar_seam"]
    z_top = z[-1]
    cs = topo["crown_settings"]
    c19 = min(cs, key=lambda c: abs(c["torso_in"] - 19))
    wraps = geom["haul_wraps"]

    def dim(ax, p0, p1, text, off=(0, 0), rot=0, fs=8.5):
        ax.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", color=DIM, lw=1))
        mx, my = (p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1]
        ax.text(mx, my, text, color=DIM, fontsize=fs, ha="center", va="center", rotation=rot,
                bbox=dict(fc="white", ec="none", pad=0.5))

    def camo(ax, pts, k=0, alpha=0.95):
        ax.add_patch(MPoly(pts, closed=True, fc=CAMO[k % 4], ec=CAMO[3], lw=0.9, hatch="//" if k % 2 else "\\\\", alpha=alpha))

    def a_at(zz):
        return np.interp(zz, z, a)

    def mm_in(v):
        return f"{v:.0f} ({v / IN:.1f} in)"

    # ---------------- FRONT view = the bag's outer face (seen from behind the wearer; x right = wearer's right)
    ax = axs[0]
    ax.set_title("FRONT (outer face): taper + SPINE diagonal", fontsize=11)
    rs = np.array(geom["bag"]["profile"]["stations_rolled"])
    zr_, ar_, yr_, dr_ = rs[:, 0], rs[:, 1], rs[:, 2], rs[:, 3]
    z_roll = zr_[-1]
    outline = np.vstack([np.column_stack([a, z]), np.column_stack([-a[::-1], z[::-1]])])
    outline_r = np.vstack([np.column_stack([ar_, zr_]), np.column_stack([-ar_[::-1], zr_[::-1]])])
    ax.add_patch(MPoly(outline, closed=True, fc="none", ec=SOLID, lw=1.2, ls="--"))
    ax.text(0, z_top + 30, f"full: collar unrolled to the fill line = {geom['volumes']['main_bag_L']:.1f} L",
            ha="center", fontsize=7.8, color=SOLID)
    ax.add_patch(MPoly(outline_r, closed=True, fc=SOLID, ec=FR, lw=1.6))
    # face seams (projected x of the face/gore seams)
    seam_x = []
    for zz in z:
        t = (zz - BAG_Z0) / Hf
        Pq, _ = ring_xy(min(t, 1.0), Hf, 720)
        sm = ring_seams(Pq)
        seam_x.append([point_at_s(Pq, sm["s"], sm["face_R"])[0], point_at_s(Pq, sm["s"], sm["face_L"])[0]])
    seam_x = np.array(seam_x)
    m = z <= zc - ROLLED_DOME_MM
    ax.plot(seam_x[m, 0], z[m], color=SOLID_D, lw=0.9); ax.plot(seam_x[m, 1], z[m], color=SOLID_D, lw=0.9)
    # stretch band (between zip line and band lower edge)
    zl = diag["zip3"]; bl = diag["band3"]
    band = np.vstack([zl[:, [0, 2]], bl[::-1][:, [0, 2]]])
    ax.add_patch(MPoly(band, closed=True, fc=SOLID_L, ec=FR, lw=1.0, alpha=0.95))
    ax.plot(zl[:, 0], zl[:, 2], color=CAMO[1], lw=5.5, solid_capstyle="butt")       # camo mouth binding
    ax.plot(zl[:, 0], zl[:, 2], color=ZIP, lw=1.4, ls=(0, (5, 3)))                     # zip under it
    # cam cup (lower right end of the band) + lower corners
    zr = diag["z_lo"]
    camo(ax, [(seam_x[0, 0] - 5, zr - BAND_H - 10), (diag["x_R"] - 70, zr - BAND_H + 5), (diag["x_R"] - 55, zr - BAND_H + 80),
              (diag["x_R"] + 2, zr - 30)], 2)
    for sx in (-1, 1):
        camo(ax, [(sx * a_at(BAG_Z0), BAG_Z0), (sx * (a_at(BAG_Z0) - 120), BAG_Z0), (sx * (a_at(BAG_Z0) - 70), BAG_Z0 + 60),
                  (sx * a_at(BAG_Z0 + 170), BAG_Z0 + 170)], 0 if sx > 0 else 1)
    # fly pocket (low left)
    ax.text(0, BAG_Z0 - 22, "rain fly in base pocket", fontsize=7.2, ha="center", va="top", color=SOLID_D)
    # haul wraps (19 in)
    for w in wraps:
        zR, zL = w["z_R_at_19in"], w["z_L_at_19in"]
        ax.plot([-a_at(zL) - 6, a_at(zR) + 6], [zL, zR], color=HAUL, lw=3.2, alpha=0.95)
        ax.text(a_at(zR) + 12, zR, w["id"], fontsize=7.5, va="center", color=HAUL)
    # roll-top (rolled-down state) + clips down to the side gores
    rw = ar_[-1]
    ax.add_patch(MPoly([(-rw - 10, z_roll - 30), (rw + 10, z_roll - 30), (rw + 10, z_roll + 18), (-rw - 10, z_roll + 18)],
                       closed=True, fc=SOLID_D, ec=FR, lw=1.0))
    camo(ax, [(-rw, z_roll - 16), (rw, z_roll - 16), (rw, z_roll + 6), (-rw, z_roll + 6)], 3, alpha=0.85)
    zclip = z_roll - 230
    for sx in (-1, 1):
        ax.plot([sx * (rw + 8), sx * (a_at(zclip) + 4)], [z_roll - 5, zclip], color=FR, lw=2.2)
        ax.plot([sx * (a_at(zclip) + 4)], [zclip], "s", color=FR, ms=6)
    ax.text(0, z_roll + 45, "roll-top, ends clip down (ROLL)", ha="center", fontsize=7.5)
    # side pockets peeking out
    for sx in (-1, 1):
        zz = np.linspace(90, 450, 20)
        ax.fill_betweenx(zz, sx * a_at(zz), sx * (a_at(zz) + 18), color=SOLID_L, ec=FR, lw=0.6)
    dim(ax, (-a[0], -40), (a[0], -40), mm_in(2 * a[0]) + " bottom")
    k = int(np.argmax(a))
    dim(ax, (-a[k], z[k]), (a[k], z[k]), mm_in(2 * a[k]) + " max", off=(0, 22))
    dim(ax, (-a.max() - 70, BAG_Z0), (-a.max() - 70, z_roll + 18), f"rolled down {mm_in(z_roll + 18 - BAG_Z0)}", rot=90)
    dim(ax, (a.max() + 70, BAG_Z0), (a.max() + 70, z_top), f"full {mm_in(Hf)}", rot=90)
    ax.text(0, -125, f"SPINE: one #10 zip, right hip -> left shoulder\n({diag['angle_from_vertical_deg']:.0f} deg, "
                     f"{diag['zip_len']:.0f} mm) under the mouth of a stretch band\n(overload / bow cam / poles). "
                     "Camo only on wear zones.", ha="center", fontsize=8.0)

    # ---------------- SIDE view (from the wearer's right; y aft to the right)
    ax = axs[1]
    ax.set_title("SIDE: teardrop, load close to the back; haul mode dashed", fontsize=11)
    prof = np.vstack([np.column_stack([yf, z]), np.column_stack([(yf + d)[::-1], z[::-1]])])
    prof_r = np.vstack([np.column_stack([yr_, zr_]), np.column_stack([(yr_ + dr_)[::-1], zr_[::-1]])])
    ax.add_patch(MPoly(prof, closed=True, fc="none", ec=SOLID, lw=1.2, ls="--"))
    ax.add_patch(MPoly(prof_r, closed=True, fc=SOLID, ec=FR, lw=1.6, alpha=0.95))
    ax.add_patch(plt.Circle((yr_[-1] + dr_[-1] / 2, z_roll - 6), 26, fc=SOLID_D, ec=FR))
    prof_h = prof_r + np.array([HAUL_PULLBACK, 0])
    ax.add_patch(MPoly(prof_h, closed=True, fc="none", ec="#7a5c2e", lw=1.2, ls=(0, (3, 2))))
    ax.text(yr_[0] + HAUL_PULLBACK + 250, z_roll + 70, "haul mode: bag hinges back 250 on its\nbottom pins; meat rides in the wrap sling",
            ha="center", fontsize=7.8, color="#7a5c2e")
    dim(ax, (yr_[0], -95), (yr_[0] + HAUL_PULLBACK, -95), "meat bay 250 (9.8 in)", fs=7.8)
    ax.text(yr_[-1] + 150, z_top - 20, "full 85.2 L (collar unrolled)", fontsize=7.5, color=SOLID)
    ax.text(yr_[-1] - 20, z_roll + 60, f"rolled down\n{geom['bag']['rolltop']['rolled_down_volume_L']:.0f} L", fontsize=7.5)
    # side pocket + band bulge on the outer face
    zz = np.linspace(90, 450, 20)
    ypc = np.interp(zz, z, yf + 0.55 * d)
    ax.fill_betweenx(zz, ypc - 80, ypc + 80, color=SOLID_L, ec=FR, lw=0.7)
    ax.text(float(ypc.mean()), 270, "floating\nside pocket", ha="center", fontsize=7.5)
    # frame
    ys = [FOOT[1], ELBOW[1], STAY_TOP[1]]; zs = [FOOT[2], ELBOW[2], STAY_TOP[2]]
    ax.plot(ys, zs, color=FR, lw=4, solid_capstyle="round")
    for st_, ls, lab in ((cs[0], ":", "15 in"), (c19, "--", "19 in"), (cs[-1], "-", "23 in")):
        zt = st_["crown_top_z"]; yt = y_on_axis(zt)
        ax.plot([y_on_axis(zt - CROWN_LEG), yt], [zt - CROWN_LEG, zt], color="#555", lw=2.2, ls=ls)
        ax.plot([yt - 15], [zt], "s", color=FR, ms=5)
        ax.text(yt - 30, zt, f"crown {lab}", fontsize=7, ha="right", va="center")
    # shelf lip + hipbelt + harness hint
    ax.add_patch(plt.Rectangle((8, 18), SHELF_D, 12, fc="#222", ec=FR))
    ax.text(8 + SHELF_D / 2, -5, f"shelf lip {SHELF_W:.0f}x{SHELF_D:.0f}", ha="center", fontsize=7.5, va="top")
    ax.add_patch(MPoly([(-40, 60), (-130, 70), (-140, 170), (-45, 180)], fc="#1f5fa0", alpha=0.25, ec="#1f5fa0"))
    yk = c19["yoke_anchor"][2]
    ax.plot([-45, -110, -170, -185, -170, -60], [yk, yk + 40, yk + 10, yk - 120, 230, 115], color="#666", lw=7, alpha=0.35,
            solid_capstyle="round")
    # wraps (side view: anchor -> bag)
    for w in wraps:       # side view from the wearer's right: R anchor -> rising toward the far (left) side
        zR, zL = w["z_R_at_19in"], w["z_L_at_19in"]
        yb = float(np.interp((zR + zL) / 2, z, yf + d))
        ax.plot([-5, yb], [zR, (zR + zL) / 2], color=HAUL, lw=2.4)
    # CG
    cg = geom["bag"]["cg_uniform_fill"]
    ax.plot([cg["y"]], [cg["z"]], marker="o", ms=9, mfc="w", mec=FR)
    ax.text(cg["y"] + 14, cg["z"] + 18, f"CG y {cg['y']:.0f} (v2 180)", fontsize=7.5)
    kmax = int(np.argmax(d))
    dim(ax, (yf[kmax], z[kmax] + 30), (yf[kmax] + d[kmax], z[kmax] + 30), mm_in(d[kmax]) + " max")
    dim(ax, (yf[0], -40), (yf[0] + d[0], -40), mm_in(d[0]))
    dim(ax, (-430, 0), (-430, z_top), f"stay foot -> fill line {mm_in(z_top)}", rot=90)
    dim(ax, (-360, 0), (-360, c19["crown_top_z"]), f"frame top @19 in {mm_in(c19['crown_top_z'])}", rot=90)
    ax.text(-300, -150, "<- wearer        y aft ->", fontsize=8.5)

    # ---------------- BACK view (wearer side)
    ax = axs[2]
    ax.set_title("BACK (wearer side): frame, harness, wraps", fontsize=11)
    ax.add_patch(MPoly(np.column_stack([-outline_r[:, 0], outline_r[:, 1]]), closed=True, fc=SOLID_D, ec=FR, lw=1.2, alpha=0.55))
    stay = [(FOOT[0], 0), (ELBOW[0], ELBOW[2]), (STAY_TOP[0], STAY_TOP[2])]
    for sx in (-1, 1):
        ax.plot([sx * p[0] for p in stay], [p[1] for p in stay], color=FR, lw=4)
        ax.plot([sx * 115] * 2, [c19["crown_top_z"] - CROWN_LEG, c19["crown_top_z"]], color="#555", lw=2.4, ls="--")
    ax.plot([-115, 115], [c19["crown_top_z"]] * 2, color="#555", lw=3)
    ax.add_patch(plt.Rectangle((-125, 50), 250, 140, fc="#333", ec=FR, alpha=0.6))
    ax.text(0, 70, "lumbar plate", ha="center", color="w", fontsize=7.5)
    for zb_, lab in ((330, "mid bar"), (520, "upper bar + pawl")):
        ax.plot([-115, 115], [zb_, zb_], color=FR, lw=3)
        ax.text(0, zb_ + 12, lab, ha="center", fontsize=7.5)
    yk = c19["yoke_anchor"][2]
    ax.add_patch(plt.Rectangle((-130, yk - 30), 260, 60, fc="#a9a9a9", ec=FR, alpha=0.85))
    for sx in (-1, 1):
        ax.plot([sx * 70, sx * 95, sx * 120, sx * 125], [yk, yk - 120, yk - 300, 130], color="#666", lw=12, alpha=0.5,
                solid_capstyle="round")
        ax.plot([sx * 70, sx * 75], [c19["crown_top_z"], yk + 25], color="#a67c00", lw=1.6)
        ax.add_patch(MPoly([(sx * 70, 60), (sx * 290, 75), (sx * 300, 165), (sx * 70, 190)], fc="#1f5fa0", alpha=0.25, ec="#1f5fa0"))
        camo(ax, [(sx * 230, 75), (sx * 290, 75), (sx * 305, 120), (sx * 290, 165), (sx * 230, 165), (sx * 245, 120)], 1)
    for w in wraps:       # back view: viewer's right = wearer's LEFT (x mirrored)
        zR, zL = w["z_R_at_19in"], w["z_L_at_19in"]
        ax.plot([-a_at(zR) - 6, -115], [zR, zR], color=HAUL, lw=3); ax.plot([115, a_at(zL) + 6], [zL, zL], color=HAUL, lw=3)
        ax.plot([115], [zL], "o", color="#888", ms=7, mec=FR)        # G-hook (wearer's left)
        ax.plot([-115], [zR], "s", color="#222", ms=6)                # ladder lock (wearer's right)
    ax.text(0, -60, "Haul wraps anchor on the frame (o = G-hook, square = ladder lock);\n"
                    "they ARE the compression in carry mode and the meat sling in haul mode.\n"
                    "Lifters stay on the crown at every setting (posts = lash/flag only).", ha="center", fontsize=8)
    for a_ in axs:
        a_.set_aspect("equal"); a_.axis("off")
    axs[0].set_xlim(-330, 330); axs[0].set_ylim(-170, z_top + 80)
    axs[1].set_xlim(-480, 700); axs[1].set_ylim(-170, z_top + 80)
    axs[2].set_xlim(-330, 330); axs[2].set_ylim(-170, z_top + 80)
    vol = geom["volumes"]; w = geom["weight"]
    fig.text(0.5, 0.012,
             f"Main bag {vol['main_bag_L']} L ({vol['main_bag_cu_in']} cu in) computed to the roll-top fill line  |  "
             f"rolled down {vol['rolled_down_L']:.0f} L  |  side pockets 2x{vol['side_pocket_each_L']} L, band pocket "
             f"~{vol['diagonal_band_pocket_L']} L, meat bay ~{vol['meat_bay_L']} L (not counted)  |  "
             f"base {w['total_g']:.0f} g ({w['total_lb']} lb; target 2268 g / 5.0 lb, frame 650 g allocation)",
             ha="center", fontsize=9.3, bbox=dict(fc="#f3efe3", ec="#999"))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.91, bottom=0.05, wspace=0.02)
    SCREEN.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SCREEN, dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    main()
