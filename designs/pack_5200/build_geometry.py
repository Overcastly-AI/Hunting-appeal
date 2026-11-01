"""Pack 5200: compute geometry, volumes, bill of panels, weight budget and concept sketch.

Owner: pack-designer. Source of truth for the numbers in DESIGN.md. Run from repo root:

    python designs/pack_5200/build_geometry.py

Writes (all regenerated, do not hand-edit):
    designs/pack_5200/geometry.yaml
    designs/pack_5200/panels.yaml
    outputs/screens/20261101_packconcept_1.png

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
from huntkit.patterns import (Piece, box_bag, cubic_inches, litres, panel_volume, rect_panel,
                              tapered_panel)

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
SCREEN = ROOT / "outputs" / "screens" / "20261101_packconcept_1.png"
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
PITCH = 12.7                    # index-rack pitch (0.5 in)
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
    hp["index_latch_upper_bar"] = r3((0.0, y_on_axis(520.0) - 14.0, 520.0))
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
                          "note": "cross tube 10 mm below stay tops; carries index latch housing"},
            "crown": {"legs_x": [-115.0, 115.0], "leg_length_along_axis": CROWN_LEG,
                      "axis_unit_vector_yz": [round(float(u_axis[0]), 4), round(float(u_axis[1]), 4)],
                      "top_bar": "cross tube joining leg tops; lifter anchors at x=+/-70; bag top buckles at x=+/-70; extension-post sockets at leg tops",
                      "spine": "cfrp_plate_quasi_iso 3 mm centre spine, top bar down 300 mm; carries the yoke and the index rack (holes at 12.7 mm pitch)",
                      "travel_mm": round(TORSO_IN[1] * IN - TORSO_IN[0] * IN, 1),
                      "positions": len(settings)},
            "extension_posts_accessory": {"length_mm": 220.0,
                                          "note": "two plug-in posts + bar on crown top for tall loads / antlers / orange flag"},
        },
        "hard_points": hp,
        "crown_settings": settings,
        "fea_handoff_notes": [
            "Torso 23 in needs yoke z=654; crown puts it there with the top bar at z=804 (FEA demo warned frame >= 634 mm).",
            "Single-stay set-down failed at the lumbar bar in the demo: replace the lumbar tube with the pm45 lumbar plate (closed torsion box).",
            "Meat-shelf heavy-low failed at mid-stay: shelf straps now anchor at the mid-bar node (z=330), not mid-span.",
            "Bonded elbow peel (Volkersen) was the critical bond: elbow fitting should be a sleeve in shear with >= 25 mm overlap each side, no peel.",
            "No holes in carbon tubes: index rack is a separate plate on the crown spine; all pins go through bonded Ti/Al inserts.",
            "Crown legs: check bending at the stay socket in tall_load with min overlap 150 mm.",
        ],
    }


# ============================================================================ 2. BAG + VOLUMES
BAG_W, BAG_D, BAG_R = 340.0, 320.0, 60.0
BAG_Z0 = 35.0           # bag bottom sits on the shelf
BAG_Y0 = 20.0           # frame-side panel plane in carry mode
COLLAR_H = 150.0


def solve_bag_height():
    lo, hi = 500.0, 1000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        v = litres(box_bag(BAG_W, mid, BAG_D, BAG_R).volume_mm3())
        lo, hi = (mid, hi) if v < TARGET_L else (lo, mid)
    h = round((lo + hi) / 2)  # whole mm for the pattern
    return h


# ============================================================================ 3. PANELS
def shard(name, pts, **kw):
    return Piece(name, outline=pts, grain=90.0, seam_allowance_mm=8.0, **kw)


def build_panels(H):
    P = []   # (piece, zone, notes, sub_assembly, mass_kind)
    side_len = None

    def add(p, zone, sub, notes="", kind="fabric", thickness_mm=None):
        P.append({"piece": p, "zone": zone, "sub": sub, "notes": notes, "kind": kind,
                  "t": thickness_mm})

    bag = box_bag(BAG_W, H, BAG_D, BAG_R, seam_allowance_mm=12.0)
    f = bag.pieces
    side_len = f["front"].edge_length("right")
    fr = f["front"]; fr.name = "bag frame-side panel"; fr.piece_id = "B-01"; fr.material_id = "tpu_coated_nylon_840d"
    add(fr, "meat contact / frame side", "main bag", "box_bag 'front'. Webbing ladders + 6 frame-attach tabs sewn on before assembly")
    ou = f["back"]; ou.name = "bag outer face panel"; ou.piece_id = "B-02"; ou.material_id = "cordura_500d_nylon66"
    add(ou, "outer face (solid colour)", "main bag", "box_bag 'back'. Carries shards SH-01/SH-02, bow pocket, compression anchors")
    sl = f["side_left"]; sl.name = "side gusset left"; sl.piece_id = "B-03"; sl.material_id = "cordura_500d_nylon66"
    add(sl, "side", "main bag", "side pocket P-01 and compression ladder sewn on flat first")
    zw = BAG_D / 2
    for pid, nm in (("B-04a", "side gusset right, fore strip (zip)"), ("B-04b", "side gusset right, aft strip (zip)")):
        add(rect_panel(nm, zw, side_len, 0.0, seam_allowance_mm={"default": 12.0}, material_id="cordura_500d_nylon66", piece_id=pid),
            "side, full-length zip", "main bag", "right gusset split on its centreline for the full-length #10 coil zip (zip SA 10 mm)")
    bt = f["bottom"]; bt.name = "bag bottom"; bt.piece_id = "B-05"; bt.material_id = "tpu_coated_nylon_840d"
    add(bt, "bottom (abrasion, blood)", "main bag", "2 drain grommets (8 mm) at front corners")
    perim = 2 * (BAG_W + BAG_D)
    add(rect_panel("extension collar", perim, COLLAR_H, 0.0, seam_allowance_mm=12.0, material_id="robic_210d_ripstop", piece_id="B-06"),
        "collar", "main bag", "one back seam; drawcord channel B-07 on top edge")
    ch = rect_panel("collar drawcord channel", perim, 50.0, 0.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop", piece_id="B-07")
    add(ch, "collar", "main bag", "fold lengthwise, 3 mm Dyneema cord + cord lock")
    add(rect_panel("side-zip garage/storm flap", 45.0, side_len, 0.0, seam_allowance_mm=10.0, material_id="cordura_330d_nylon66", piece_id="B-08"),
        "side zip", "main bag", "quiet: covers coil, parks the slider in a garage at the top")
    add(rect_panel("hydration sleeve", 260.0, 450.0, 0.0, seam_allowance_mm=10.0, material_id="robic_100d_ripstop", piece_id="B-09"),
        "interior", "main bag", "sewn into frame-side panel side seams; hose port both sides")
    add(rect_panel("frame-attach tab", 50.0, 70.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon", piece_id="B-10", quantity=8),
        "frame side", "main bag", "raw-edge Hypalon (does not fray); 4 low, 2 mid, 2 top")
    add(rect_panel("lash/daisy tab", 30.0, 50.0, 0.0, seam_allowance_mm=0.0, material_id="hypalon_coated_nylon", piece_id="B-11", quantity=12),
        "outer face + lid", "main bag", "laser-cut slot 25x5 mm; antler/cape lashing, no daisy-chain snag loops")
    add(rect_panel("bow-limb / cam pocket", 220.0, 150.0, {"bl": 30, "br": 30}, seam_allowance_mm=10.0, material_id="tpu_coated_nylon_840d", piece_id="B-12"),
        "outer face low", "main bag", "open-top boot; bow riser held by two 25 mm straps")

    # ---- camo accent shards: functional double-layer abrasion overlays (angular seams)
    shard_mat = "polyester_ht_630d_printable"
    add(shard("lower-corner shard (wraps corner)",
              [(0, 0), (230, 0), (300, 70), (210, 150), (95, 260), (0, 190)],
              material_id=shard_mat, piece_id="SH-01", quantity=1, mirror=True),
        "abrasion: bag lower corners (set-down, rock, deadfall)", "accents",
        "wraps 120 mm onto side gusset; bottom edge caught in the bottom seam")
    add(shard("outer-face diagonal lash shard",
              [(0, 0), (90, 0), (260, 300), (250, 430), (170, 430), (0, 120)],
              material_id=shard_mat, piece_id="SH-02", quantity=1),
        "abrasion: antler/bow/rifle rub zone, upper outer face", "accents",
        "lash tabs B-11 sewn through shard + base (double layer where loads enter)")
    add(shard("lid top shard", [(0, 0), (150, 0), (300, 90), (300, 200), (120, 200), (0, 90)],
              material_id=shard_mat, piece_id="SH-03", quantity=1),
        "abrasion: lid top (pack thrown down, rock contact)", "accents", "")
    add(shard("side-pocket face shard", [(0, 0), (175, 0), (175, 120), (60, 200), (0, 160)],
              material_id=shard_mat, piece_id="SH-04", quantity=1, mirror=True),
        "abrasion: side-pocket faces (brush)", "accents", "")
    add(shard("hipbelt wing-tip shard", [(0, 0), (110, 0), (140, 45), (110, 95), (0, 95), (25, 45)],
              material_id=shard_mat, piece_id="SH-05", quantity=1, mirror=True),
        "abrasion: hipbelt wing tips (arm swing, brush)", "accents", "same shape all sizes (sits at wing tip)")

    # ---- lid
    lid_top = rect_panel("lid top", 320.0, 280.0, 50.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop", piece_id="L-01")
    add(lid_top, "lid", "lid", "shard SH-03 overlaid; 2 lash tabs")
    add(rect_panel("lid underside", 320.0, 280.0, 50.0, seam_allowance_mm=10.0, material_id="tpu_coated_nylon_840d", piece_id="L-02"),
        "lid underside (sits on wet load)", "lid", "carries under-lid pocket and its #5 zip")
    add(rect_panel("lid gusset", lid_top.edge_length("bottom") + lid_top.edge_length("right") * 2 + lid_top.edge_length("top"), 80.0, 0.0,
                   seam_allowance_mm=10.0, material_id="cordura_330d_nylon66", piece_id="L-03"),
        "lid", "lid", "one strip, ends join at the rear; #8 AquaGuard zip on the front 300 mm")
    add(rect_panel("under-lid pocket face", 260.0, 200.0, 20.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop", piece_id="L-04"),
        "lid", "lid", "flat pocket for licence/tags; key clip")
    add(rect_panel("orange flag sleeve", 300.0, 120.0, 0.0, seam_allowance_mm=10.0, material_id="robic_210d_ripstop", piece_id="L-05"),
        "safety", "lid", "ASSUMPTION: blaze-orange colourway of robic_210d; stows in lid, slides over crown top bar/extension posts")

    # ---- side pockets (x2)
    sp = tapered_panel("side pocket face", 190.0, 160.0, 380.0, material_id="ultragrid_210d_uhmwpe_ripstop", piece_id="P-01", quantity=1, mirror=True, seam_allowance_mm=10.0)
    add(sp, "side pockets", "pockets", "tripod/trekking-pole/water bottle; 3 mm shock-cord top hem; drain eyelet")
    sp_g = sp.edge_length("left") + sp.edge_length("bottom") + sp.edge_length("right")
    add(rect_panel("side pocket gusset", sp_g, 60.0, 0.0, seam_allowance_mm=10.0, material_id="ultragrid_210d_uhmwpe_ripstop", piece_id="P-02", quantity=2),
        "side pockets", "pockets", "U-strip; bellows 60 mm")

    # ---- hipbelt pockets (x2)
    hpf = tapered_panel("hipbelt pocket face", 180.0, 140.0, 110.0, material_id="cordura_500d_nylon66", piece_id="HP-01", quantity=1, mirror=True, seam_allowance_mm=8.0)
    add(hpf, "hipbelt pockets", "hipbelt", "#8 coil zip along top; rangefinder fits")
    hpg = hpf.edge_length("left") + hpf.edge_length("bottom") + hpf.edge_length("right")
    add(rect_panel("hipbelt pocket gusset", hpg, 55.0, 0.0, seam_allowance_mm=8.0, material_id="cordura_500d_nylon66", piece_id="HP-02", quantity=2),
        "hipbelt pockets", "hipbelt", "")

    # ---- load shelf + load wings
    add(rect_panel("load shelf floor", 270.0, 260.0, {"tl": 30, "tr": 30}, seam_allowance_mm=12.0, material_id="tpu_coated_nylon_840d", piece_id="S-01", quantity=2),
        "meat shelf", "shelf", "two layers sandwiching a 1.5 mm HDPE stiffener (S-05); grommets at aft corners for shelf straps; 2 drain grommets")
    add(rect_panel("shelf liner sleeve (removable)", 270.0, 620.0, 0.0, seam_allowance_mm=10.0, material_id="silicone_coated_poly_ripstop_40d", piece_id="S-02"),
        "meat shelf", "shelf", "washable U-sleeve over shelf + frame-side panel; breathable game bags go inside")
    lw = tapered_panel("load wing (frame-mounted)", 180.0, 120.0, 430.0, material_id="tpu_coated_nylon_840d", piece_id="S-03", quantity=2, mirror=True, seam_allowance_mm=12.0)
    add(lw, "meat haul wings", "shelf", "double layer; 3 x 38 mm poly straps each; wraps quarters in frame-only mode and the bag in carry mode")
    add(rect_panel("stay guard sleeve", 90.0, 300.0, 0.0, seam_allowance_mm=10.0, material_id="tpu_coated_nylon_840d", piece_id="S-04", quantity=2),
        "frame", "shelf", "protects lower stays from rock/knife cuts; quiet against brush")
    add(rect_panel("shelf stiffener (cut, not sewn)", 250.0, 240.0, 20.0, seam_allowance_mm=0.0, material_id="hdpe_sheet", piece_id="S-05"),
        "meat shelf", "shelf", "1.5 mm HDPE", kind="sheet", thickness_mm=1.5)

    # ---- hipbelt (size M shown; grade table in panels.yaml)
    wing_len = HIPBELT_WINGS["M"]
    for pid, nm, mat, kind, t, notes in (
            ("H-01", "hipbelt wing outer shell", "cordura_500d_nylon66", "fabric", None, "tpu_coated_nylon_840d binding strip on bottom edge"),
            ("H-02", "hipbelt wing body face", "spacer_mesh_3d", "fabric", None, ""),
            ("H-03", "hipbelt wing load foam", "eva_foam_45c", "foam", 6.0, "die-cut (outsource); inset 8 mm"),
            ("H-04", "hipbelt wing comfort foam", "eva_foam_30c", "foam", 6.0, "die-cut (outsource); inset 6 mm"),
            ("H-05", "hipbelt wing stiffener", "hdpe_sheet", "sheet", 1.5, "1.5 mm HDPE, rounded corners; transfers load to iliac crest")):
        sa = 10.0 if kind == "fabric" else 0.0
        inset = {"H-03": 8.0, "H-04": 6.0, "H-05": 12.0}.get(pid, 0.0)
        p = tapered_panel(nm, 140.0 - 2 * inset, 95.0 - 2 * inset, wing_len - inset, material_id=mat, piece_id=pid,
                          quantity=1, mirror=True, seam_allowance_mm=sa)
        add(p, "hipbelt wings (graded S-XL)", "hipbelt", notes, kind=kind, thickness_mm=t)
    for pid, nm, mat, kind, t in (("H-06", "lumbar pad shell", "cordura_500d_nylon66", "fabric", None),
                                  ("H-07", "lumbar pad face", "spacer_mesh_3d", "fabric", None),
                                  ("H-08", "lumbar pad foam", "eva_foam_30c", "foam", 8.0)):
        add(rect_panel(nm, 160.0, 140.0, 25.0, material_id=mat, piece_id=pid, seam_allowance_mm=10.0 if kind == "fabric" else 0.0),
            "hipbelt centre", "hipbelt", "centre plate slots onto the Ti hipbelt pivot", kind=kind, thickness_mm=t)

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
        for pid, nm, mat, kind, t in ((f"HS-{alt}1", f"{alt}-strap shell", "cordura_500d_nylon66", "fabric", None),
                                      (f"HS-{alt}2", f"{alt}-strap face", "spacer_mesh_3d", "fabric", None),
                                      (f"HS-{alt}3", f"{alt}-strap load foam", "eva_foam_45c", "foam", 6.0),
                                      (f"HS-{alt}4", f"{alt}-strap comfort foam", "eva_foam_perforated", "foam", 6.0)):
            p = Piece(nm, outline=strap(nm, s_curve), material_id=mat, piece_id=pid, quantity=1, mirror=True,
                      seam_allowance_mm=10.0 if kind == "fabric" else 0.0)
            add(p, f"shoulder harness ({'J unisex, default' if alt == 'J' else 'S curved, alternate for narrower/curvier chests'})",
                f"harness_{alt}", "sternum rail (POM) sewn into inner edge", kind=kind, thickness_mm=t)
    add(rect_panel("yoke cover", 260.0, 120.0, 30.0, material_id="cordura_500d_nylon66", piece_id="HS-05", quantity=2, seam_allowance_mm=10.0),
        "yoke", "harness_common", "sandwich over the yoke plate; quick-connect for J/S straps")

    # ---- back panels
    for pid, nm, w, h, mat, kind, t in (("BP-01", "lower back panel face", 240.0, 320.0, "spacer_mesh_3d", "fabric", None),
                                        ("BP-02", "lower back panel foam", 220.0, 300.0, "xlpe_foam", "foam", 8.0),
                                        ("BP-03", "upper back pad face (on crown)", 220.0, 200.0, "spacer_mesh_3d", "fabric", None),
                                        ("BP-04", "upper back pad foam", 200.0, 180.0, "xlpe_foam", "foam", 8.0),
                                        ("BP-05", "back panel shell", 240.0, 320.0, "cordura_330d_nylon66", "fabric", None)):
        add(rect_panel(nm, w, h, 30.0, material_id=mat, piece_id=pid, seam_allowance_mm=10.0 if kind == "fabric" else 0.0),
            "back panel", "back_panel", "perforated foam channels; wraps stays with 6 tabs", kind=kind, thickness_mm=t)

    # ---- rifle carry
    add(tapered_panel("rifle butt boot body", 300.0, 260.0, 200.0, material_id="cordura_500d_nylon66", piece_id="R-01", seam_allowance_mm=10.0),
        "rifle carry", "carry", "rolled into a cone; mounts to left hipbelt wing")
    add(rect_panel("rifle boot bottom", 100.0, 60.0, 30.0, material_id="tpu_coated_nylon_840d", piece_id="R-02", seam_allowance_mm=10.0),
        "rifle carry", "carry", "drain eyelet")
    return P, bag, side_len


HIPBELT_SIZES = {"S": (26, 30), "M": (30, 34), "L": (34, 38), "XL": (38, 42)}  # hip circ. at iliac crest, in
HIPBELT_PAD_FRACTION = 0.72  # ASSUMPTION: padded length (wings+centre) = 72 % of hip circumference
LUMBAR_CENTRE = 140.0
HIPBELT_WINGS = {k: round((HIPBELT_PAD_FRACTION * (sum(v) / 2) * IN - LUMBAR_CENTRE) / 2)
                 for k, v in HIPBELT_SIZES.items()}


# ============================================================================ 4. MASSES
def piece_mass(rec):
    p = rec["piece"]
    m = MAT.load(p.material_id)
    a_m2 = p.area_mm2 / 1e6  # cut-line area (what you buy)
    qty = p.quantity * (2 if p.mirror else 1)
    if rec["kind"] == "fabric":
        return a_m2 * m.require("areal_density_gsm") * qty
    rho = m.require("density_kg_m3")
    return a_m2 * (rec["t"] / 1000.0) * rho * 1000.0 * qty


def hw(id_, n=1, length_m=None):
    m = MAT.load(id_)
    if length_m is not None:
        return m.require("mass_g_m") * length_m
    return m.require("mass_g") * n


def weight_budget(P, H):
    sub_mass = {}
    for rec in P:
        sub_mass.setdefault(rec["sub"], 0.0)
        sub_mass[rec["sub"]] += piece_mass(rec)
    side_zip = (H + 60) / 1000
    rows = []

    def row(group, item, g, basis):
        rows.append({"group": group, "item": item, "mass_g": round(g, 1), "basis": basis})

    # Frame: allocation pending FEA sizing (ASSUMPTION)
    for item, g in (("stays (2 lower + 2 upper tubes)", 130), ("crown: legs, top bar, spine/index rack", 120),
                    ("mid + upper cross bars", 40), ("lumbar plate (pm45)", 60),
                    ("bonded nodes, elbows, sockets, adhesive", 90),
                    ("Ti/Al inserts, hipbelt pivot pin, index latch", 50),
                    ("foot boots + shelf pivots, UHMWPE bushings", 35)):
        row("frame (allocation, FEA to confirm)", item, g, "ASSUMPTION: allocation; tube sizes by structural-fea-engineer")
    row("main bag", "fabric panels (B-*, incl. collar, tabs, bow pocket)", sub_mass["main bag"], "computed: cut area x gsm")
    row("main bag", "#10 coil full side zip + 2 sliders", hw("coil_zipper_10", length_m=side_zip) + 12, "coil_zipper_10 g/m; sliders 6 g ea ASSUMPTION")
    row("main bag", "collar cord + cord lock", hw("dyneema_cord_3mm", length_m=1.6) + hw("cord_lock_spring", 1), "records")
    row("accents", "camo shards SH-01..05 (overlay mass)", sub_mass["accents"], "computed")
    row("lid", "lid panels", sub_mass["lid"], "computed")
    row("lid", "#8 AquaGuard + #5 coil zips, 4x25 mm buckles, Fidlock", hw("aquaguard_zipper_8", length_m=0.32) + hw("coil_zipper_5", length_m=0.26)
        + hw("buckle_side_release_25mm", 4) + hw("fidlock_magnetic_buckle_25mm", 1) + hw("poly_webbing_25mm", length_m=1.6), "records")
    row("pockets", "side pockets x2", sub_mass["pockets"], "computed")
    row("hipbelt (M)", "wings, lumbar pad, hipbelt pockets", sub_mass["hipbelt"], "computed (foams = area x t x rho)")
    row("hipbelt (M)", "50 mm webbing + buckle, 2 #8 pocket zips, stabilizer straps", hw("nylon_webbing_50mm", length_m=0.9) + hw("buckle_side_release_50mm", 1)
        + hw("coil_zipper_8", length_m=0.4) + hw("poly_webbing_25mm", length_m=0.8) + 2 * hw("ladder_lock_25mm"), "records")
    row("hipbelt (M)", "centre plate + pivot latch (pa66_gf30 / POM)", 45, "ASSUMPTION")
    row("harness", "J-straps (default set)", sub_mass["harness_J"], "computed")
    row("harness", "yoke cover + yoke plate (cfrp 1.5 mm, 260x120)", sub_mass["harness_common"] + 0.26 * 0.12 * 1.5e-3 * 1550 * 1000, "computed; plate rho cfrp_plate_quasi_iso")
    row("harness", "load lifters 38 mm poly + ladders, sternum Fidlock + POM rails", hw("poly_webbing_38mm", length_m=0.9) + 4 * hw("ladder_lock_25mm")
        + hw("fidlock_magnetic_buckle_25mm") + 12 + hw("poly_webbing_25mm", length_m=1.2), "records; rails 12 g ASSUMPTION")
    row("back panel", "lower + upper pads", sub_mass["back_panel"], "computed")
    row("load shelf", "shelf floor, stiffener, liner, load wings, stay guards", sub_mass["shelf"], "computed")
    row("load shelf", "shelf + wing straps 38 mm poly, ladders, grommets", hw("poly_webbing_38mm", length_m=4.4) + 10 * hw("ladder_lock_25mm") + 10, "records; grommets ASSUMPTION")
    row("compression", "6 side compression straps 25 mm + 6 buckles", hw("poly_webbing_25mm", length_m=3.6) + 6 * hw("buckle_side_release_25mm"), "records")
    row("misc", "thread (~3 % of soft goods) + labels", 0.03 * sum(v for k, v in sub_mass.items() if k != "carry") + 10, "ASSUMPTION")
    tot = sum(r["mass_g"] for r in rows)
    carry = sub_mass["carry"] + hw("poly_webbing_25mm", length_m=0.6) + hw("ladder_lock_25mm")
    groups = {}
    for r in rows:
        groups[r["group"]] = round(groups.get(r["group"], 0) + r["mass_g"], 1)
    return rows, groups, round(tot, 1), round(carry, 1)


# ============================================================================ 5. SMALL VOLUMES
def small_volumes():
    lid = rect_panel("lid", 320.0, 280.0, 50.0)
    under = rect_panel("ul", 260.0, 200.0, 20.0)
    sp = tapered_panel("sp", 190.0, 160.0, 380.0)
    hp = tapered_panel("hp", 180.0, 140.0, 110.0)
    return {
        "lid_main_L": round(litres(panel_volume(lid, 80.0)), 2),
        "lid_underlid_L": round(litres(panel_volume(under, 25.0)), 2),
        "side_pocket_each_L": round(litres(panel_volume(sp, 60.0)), 2),
        "hipbelt_pocket_each_L": round(litres(panel_volume(hp, 55.0)), 2),
        "collar_L": round(litres(BAG_W * BAG_D * COLLAR_H), 2),
        "meat_shelf_bay_L": round(litres(270 * 250 * 600), 1),
    }


# ============================================================================ 6. WRITE + PLOT
def main():
    H = solve_bag_height()
    bag = box_bag(BAG_W, H, BAG_D, BAG_R)
    v_mm3 = bag.volume_mm3()
    vols = small_volumes()
    P, _, side_len = build_panels(H)
    rows, groups, total, carry = weight_budget(P, H)
    topo = frame_topology()

    geom = {
        "meta": {"design": "Pack 5200", "owner": "pack-designer", "generated_by": "designs/pack_5200/build_geometry.py",
                 "date": "2026-11-01", "units": "mm, L, g"},
        "frame": topo,
        "bag": {
            "type": "box bag (huntkit.patterns.box_bag): front=frame-side panel, back=outer face, 2 side gussets, bottom",
            "width_x": BAG_W, "height_z": H, "depth_y": BAG_D, "bottom_corner_radius": BAG_R,
            "origin_carry_mode": {"x_center": 0.0, "y_frame_side_panel": BAG_Y0, "z_bottom": BAG_Z0},
            "haul_mode_pullback_y_max": 250.0,
            "side_zip": {"side": "right (x+)", "type": "coil_zipper_10", "length_mm": round(side_len + 60)},
            "extension_collar_height": COLLAR_H,
        },
        "volumes": {
            "method": "geometric: front-panel seam-line area (huntkit Piece.seam_area_mm2) x gusset width, via BoxBag.volume_mm3()",
            "main_bag_L": round(litres(v_mm3), 2), "main_bag_cu_in": round(cubic_inches(v_mm3)),
            "main_bag_analytic_check_L": round(litres(bag.analytic_volume_mm3()), 2),
            "counted_in_5200": "main bag only (to the collar seam). Collar, lid and pockets are NOT counted",
            **vols,
            "total_with_lid_pockets_collar_L": round(litres(v_mm3) + vols["lid_main_L"] + vols["lid_underlid_L"]
                                                     + 2 * vols["side_pocket_each_L"] + 2 * vols["hipbelt_pocket_each_L"]
                                                     + vols["collar_L"], 1),
        },
        "lid": {"footprint": [320.0, 280.0], "height": 80.0, "corner_radius": 50.0,
                "position": {"z_bottom": BAG_Z0 + H, "y_center": BAG_Y0 + BAG_D / 2 + 10}},
        "side_pockets": {"face_bottom_w": 190.0, "face_top_w": 160.0, "height": 380.0, "bellows": 60.0,
                         "position": {"x": [-BAG_W / 2, BAG_W / 2], "z_bottom": 70.0, "y_center": BAG_Y0 + BAG_D / 2}},
        "load_shelf": {"floor_w_x": 270.0, "floor_d_y": 260.0, "z": 25.0, "y_from": 8.0,
                       "straps": "aft shelf corners -> shelf_strap_anchor_fixed (z=330) and crown top bar"},
        "load_wings": {"root_w": 180.0, "tip_w": 120.0, "length": 430.0, "mount": "load_wing_lash_z80/250/420 on each stay"},
        "hipbelt": {"sizes_hip_circ_in": HIPBELT_SIZES, "wing_length_mm": HIPBELT_WINGS, "lumbar_centre_w": LUMBAR_CENTRE,
                    "pivot": "hipbelt_pivot hard point; free roll +/-8 deg with elastomer centring; wing cant 0/5/10 deg (3-position)"},
        "harness": {"padded_length": 440.0, "width_top": 72.0, "width_bottom": 58.0,
                    "options": ["J (unisex default)", "S (curved, 35 mm lateral offset)"],
                    "sternum_rail_travel": 120.0},
        "weight": {"groups_g": groups, "total_g": total, "total_lb": round(total / 453.592, 2),
                   "rifle_boot_optional_g": carry},
    }
    (HERE / "geometry.yaml").write_text("# GENERATED by build_geometry.py - do not hand-edit\n" + yaml.safe_dump(geom, sort_keys=False, width=110, default_flow_style=None))

    plist = []
    for rec in P:
        p = rec["piece"]
        x0, y0, x1, y1 = p.bounds(cut=False)
        plist.append({"id": p.piece_id, "name": p.name, "sub_assembly": rec["sub"], "material_id": p.material_id,
                      "approx_size_mm": [round(x1 - x0), round(y1 - y0)],
                      "qty": p.quantity, "mirror_pair": p.mirror,
                      "total_pieces": p.quantity * (2 if p.mirror else 1),
                      "seam_allowance_mm": p.seam_allowance_mm if not isinstance(p.seam_allowance_mm, dict) else p.seam_allowance_mm.get("default"),
                      "thickness_mm": rec["t"], "zone": rec["zone"],
                      "cut_area_m2_each": round(p.area_mm2 / 1e6, 4), "mass_g_total": round(piece_mass(rec), 1),
                      "notes": rec["notes"]})
    grade = {"hipbelt_wings": {"rule": "length grades; root/tip widths constant (140/95 mm)",
                               "wing_length_mm_by_size": HIPBELT_WINGS,
                               "hip_circumference_in": HIPBELT_SIZES,
                               "pieces": ["H-01", "H-02", "H-03", "H-04", "H-05"]},
             "everything_else": "one size (universal frame and bag)"}
    pan = {"meta": {"design": "Pack 5200", "generated_by": "designs/pack_5200/build_geometry.py",
                    "note": "approx_size = seam-line bounding box (mm). Pattern-maker drafts true shapes in huntkit.patterns. "
                            "Hipbelt pieces shown at size M.",
                    "piece_count_total": sum(x["total_pieces"] for x in plist)},
           "grading": grade, "panels": plist,
           "webbing_cut_list": [
               {"use": "hipbelt strap", "material_id": "nylon_webbing_50mm", "length_mm": 900, "qty": 1},
               {"use": "load lifters", "material_id": "poly_webbing_38mm", "length_mm": 450, "qty": 2},
               {"use": "shelf straps", "material_id": "poly_webbing_38mm", "length_mm": 900, "qty": 2},
               {"use": "load-wing straps", "material_id": "poly_webbing_38mm", "length_mm": 433, "qty": 6},
               {"use": "side compression", "material_id": "poly_webbing_25mm", "length_mm": 600, "qty": 6},
               {"use": "lid straps", "material_id": "poly_webbing_25mm", "length_mm": 400, "qty": 4},
               {"use": "hip stabilizers", "material_id": "poly_webbing_25mm", "length_mm": 400, "qty": 2},
               {"use": "sternum + bag-top attach", "material_id": "poly_webbing_25mm", "length_mm": 300, "qty": 4},
               {"use": "bow/rifle straps", "material_id": "poly_webbing_25mm", "length_mm": 300, "qty": 2}]}
    (HERE / "panels.yaml").write_text("# GENERATED by build_geometry.py - do not hand-edit\n" + yaml.safe_dump(pan, sort_keys=False, width=110, default_flow_style=None))

    plot(H, topo, geom)
    print(f"bag H = {H} mm ({H / IN:.1f} in); main bag {litres(v_mm3):.2f} L = {cubic_inches(v_mm3):.0f} cu in")
    print("small volumes:", vols)
    print("weight groups:", groups)
    print(f"total {total:.0f} g = {total / 453.592:.2f} lb ; rifle boot {carry} g")
    print("pieces:", pan["meta"]["piece_count_total"], "hipbelt wings:", HIPBELT_WINGS)
    for s in topo["crown_settings"][::4]:
        print(s)
    for r in rows:
        print(r)


def plot(H, topo, geom):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Polygon as MPoly

    SOLID = "#4b4f3a"; SOLID_L = "#6b6f55"
    CAMO = ["#ae9d6c", "#8b8148", "#c6b497", "#313120"]  # owner base palette (DECISIONS.md)
    FR = "#1a1a1a"; DIM = "#b03a2e"
    fig, axs = plt.subplots(1, 3, figsize=(16, 9.2), dpi=100,
                            gridspec_kw={"width_ratios": [1, 1.15, 1]})
    fig.suptitle("Pack 5200 concept: 85.2 L meat-hauler, carbon frame with telescoping torso crown  (FCS mm; in)",
                 fontsize=13, weight="bold")
    s = topo["crown_settings"]
    smin, smid, smax = s[0], s[len(s) // 2], s[-1]
    z_bag_top = BAG_Z0 + H

    def dim(ax, p0, p1, text, off=(0, 0), rot=0):
        ax.annotate("", p0, p1, arrowprops=dict(arrowstyle="<->", color=DIM, lw=1))
        mx, my = (p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1]
        ax.text(mx, my, text, color=DIM, fontsize=8.5, ha="center", va="center", rotation=rot,
                bbox=dict(fc="white", ec="none", pad=0.5))

    def camo_patch(ax, pts, k=0):
        ax.add_patch(MPoly(pts, closed=True, fc=CAMO[k % 4], ec=CAMO[3], lw=1.0, hatch="//" if k % 2 else "\\\\", alpha=0.95))

    # ---------------- BACK view (from behind; x to the right = wearer's right)
    ax = axs[0]
    ax.set_title("BACK view (outer face, camo shards)", fontsize=11)
    W = BAG_W
    ax.add_patch(FancyBboxPatch((-W / 2, BAG_Z0), W, H, boxstyle="round,pad=0,rounding_size=50", fc=SOLID, ec=FR, lw=1.5))
    ax.add_patch(FancyBboxPatch((-160, z_bag_top), 320, 80, boxstyle="round,pad=0,rounding_size=30", fc=SOLID_L, ec=FR, lw=1.2))
    camo_patch(ax, [(-W / 2, BAG_Z0 + 10), (-W / 2 + 200, BAG_Z0), (-W / 2 + 250, BAG_Z0 + 70), (-W / 2 + 160, BAG_Z0 + 150), (-W / 2 + 60, BAG_Z0 + 250), (-W / 2, BAG_Z0 + 190)], 0)
    camo_patch(ax, [(W / 2, BAG_Z0 + 10), (W / 2 - 200, BAG_Z0), (W / 2 - 250, BAG_Z0 + 70), (W / 2 - 160, BAG_Z0 + 150), (W / 2 - 60, BAG_Z0 + 250), (W / 2, BAG_Z0 + 190)], 1)
    z2 = BAG_Z0 + 380
    camo_patch(ax, [(-60, z2), (30, z2), (W / 2, z2 + 280), (W / 2, z2 + 400), (W / 2 - 60, z2 + 400), (-60, z2 + 120)], 2)
    camo_patch(ax, [(-150, z_bag_top), (0, z_bag_top), (150, z_bag_top + 50), (150, z_bag_top + 80), (-30, z_bag_top + 80), (-150, z_bag_top + 40)], 3)
    for zc in (180, 400, 620):
        ax.plot([-W / 2 - 18, W / 2 + 18], [zc, zc], color="#222", lw=2.2)
    ax.add_patch(plt.Rectangle((-110, BAG_Z0 + 20), 220, 150, fc="#2e3124", ec=FR, lw=1))
    ax.text(0, BAG_Z0 + 95, "bow/cam boot", color="w", ha="center", fontsize=8)
    for sx in (-1, 1):
        ax.add_patch(plt.Rectangle((sx * W / 2 - (40 if sx > 0 else 0) + (0 if sx > 0 else -0), 70), 40 * sx * 0 + 40, 380, fc=SOLID_L, ec=FR, lw=0.8, alpha=0.0))
        ax.add_patch(MPoly([(sx * W / 2, 70), (sx * (W / 2 + 30), 70), (sx * (W / 2 + 30), 450), (sx * W / 2, 450)], fc=SOLID_L, ec=FR, lw=0.9))
        ax.add_patch(MPoly([(sx * 170, 130), (sx * 330, 110), (sx * 345, 175), (sx * 175, 200)], fc=SOLID, ec=FR, lw=1, alpha=0.9, ls="--"))
    ax.plot([-115, -115, 115, 115], [smax["crown_top_z"] - 60, smax["crown_top_z"], smax["crown_top_z"], smax["crown_top_z"] - 60], color=FR, lw=1.2, ls=":")
    dim(ax, (-W / 2, -40), (W / 2, -40), f"{W:.0f} ({W / IN:.1f} in)")
    dim(ax, (-W / 2 - 75, BAG_Z0), (-W / 2 - 75, z_bag_top), f"{H} ({H / IN:.1f} in)", rot=90)
    dim(ax, (W / 2 + 75, BAG_Z0), (W / 2 + 75, z_bag_top + 80), f"{H + 80:.0f} w/ lid", rot=90)
    ax.text(0, -110, "shards = owner-camo double-layer overlays at corners,\nlash/rub zone, lid; 25 mm compression x3 per side",
            ha="center", fontsize=8.5)
    ax.text(W / 2 + 35, 260, "side\npocket", fontsize=7.5, rotation=90, va="center")
    ax.text(-W / 2 - 10, 150, "hipbelt\n(dashed)", fontsize=7.5, ha="right")

    # ---------------- SIDE view (from wearer's right; y aft to the right)
    ax = axs[1]
    ax.set_title("SIDE view (frame, crown range, meat-haul mode)", fontsize=11)
    ys = [FOOT[1], ELBOW[1], STAY_TOP[1]]; zs = [FOOT[2], ELBOW[2], STAY_TOP[2]]
    ax.add_patch(FancyBboxPatch((BAG_Y0, BAG_Z0), BAG_D, H, boxstyle="round,pad=0,rounding_size=40", fc=SOLID, ec=FR, lw=1.3, alpha=0.9))
    ax.add_patch(FancyBboxPatch((BAG_Y0 + 250, BAG_Z0), BAG_D, H, boxstyle="round,pad=0,rounding_size=40", fc="none", ec=SOLID, lw=1.3, ls="--"))
    ax.text(BAG_Y0 + 250 + BAG_D / 2, BAG_Z0 + H + 25, "bag pulled back 250 = meat bay", ha="center", fontsize=8, color=SOLID)
    ax.add_patch(plt.Rectangle((BAG_Y0 + 10, z_bag_top), 300, 80, fc=SOLID_L, ec=FR, lw=1))
    ax.add_patch(MPoly([(BAG_Y0 + 60, 70), (BAG_Y0 + 260, 70), (BAG_Y0 + 245, 450), (BAG_Y0 + 75, 450)], fc=SOLID_L, ec=FR, lw=0.8))
    camo_patch(ax, [(BAG_Y0 + 140, 70), (BAG_Y0 + 255, 70), (BAG_Y0 + 250, 190), (BAG_Y0 + 175, 270), (BAG_Y0 + 140, 230)], 0)
    camo_patch(ax, [(BAG_Y0 + BAG_D - 120, BAG_Z0), (BAG_Y0 + BAG_D, BAG_Z0), (BAG_Y0 + BAG_D, BAG_Z0 + 190)], 1)
    ax.add_patch(plt.Rectangle((8, 18), 270, 14, fc="#222", ec=FR))
    ax.text(BAG_Y0 + 250 + BAG_D / 2, 400, "MEAT BAY\n(quarters in\ngame bags)", ha="center", fontsize=9, color=SOLID, weight="bold")
    ax.text(140, 0, "load shelf 270x260", ha="center", fontsize=8, va="top")
    ax.plot([270, 105], [25, 330], color="#7a5", lw=2)
    ax.text(200, 200, "shelf strap", color="#4a7", fontsize=8, rotation=-62)
    ax.plot(ys, zs, color=FR, lw=4, solid_capstyle="round")
    for st, ls, lab in ((smin, ":", "15 in"), (smid, "--", "19 in"), (smax, "-", "23 in")):
        zt = st["crown_top_z"]; yt = y_on_axis(zt)
        zb = zt - CROWN_LEG
        ax.plot([y_on_axis(zb), yt], [zb, zt], color="#555", lw=2.4, ls=ls)
        ax.plot([yt - 15], [zt], "s", color=FR, ms=6)
        yk = st["yoke_anchor"]
        ax.plot([yk[1]], [yk[2]], "o", color=DIM, ms=6)
        # lifter
        ax.plot([yt - 15, yt - 155], [zt, yk[2] + YOKE_DROP - 20], color="#a67c00", lw=1.5, ls=ls)
        ax.text(yt - 175, zt + 8, f"{lab}: top z={zt:.0f}, lifter {st['lifter_angle_deg']:.0f}°", fontsize=7.5, va="bottom", ha="right")
    hp = topo["hard_points"]
    ax.plot([hp["hipbelt_pivot"][1]], [hp["hipbelt_pivot"][2]], "D", color="#1f5fa0", ms=8)
    ax.text(-150, 30, "hipbelt pivot z=120", ha="center", fontsize=8, color="#1f5fa0")
    ax.plot([hp["shelf_strap_anchor_fixed_R"][1]], [330], "^", color="#4a7", ms=8)
    ax.add_patch(MPoly([(-40, 60), (-130, 70), (-140, 170), (-45, 180)], fc="#1f5fa0", alpha=0.25, ec="#1f5fa0"))
    ax.text(-95, 120, "hip\nbelt", ha="center", fontsize=7.5, color="#1f5fa0")
    yk2 = smid["yoke_anchor"][2]
    ax.plot([-45, -110, -170, -185, -170, -60], [yk2, yk2 + 40, yk2 + 10, yk2 - 120, 230, 115], color="#666", lw=7, alpha=0.35, solid_capstyle="round")
    ax.text(-195, 380, "shoulder\nstrap", fontsize=7.5, ha="right", color="#555")
    dim(ax, (BAG_Y0, -45), (BAG_Y0 + BAG_D, -45), f"{BAG_D:.0f} ({BAG_D / IN:.1f} in)")
    dim(ax, (-480, smin["crown_top_z"]), (-480, smax["crown_top_z"]), f"crown travel {smax['crown_top_z'] - smin['crown_top_z']:.0f} (8 in)\n17 pin positions, 0.5 in", rot=90, off=(-30, 0))
    dim(ax, (-560, 0), (-560, smax["crown_top_z"]), f"frame 0-{smax['crown_top_z']:.0f} ({smax['crown_top_z'] / IN:.1f} in) max", rot=90)
    ax.text(-150, -120, "<- wearer        y aft ->", fontsize=8.5)

    # ---------------- FRONT view (wearer side, frame + harness; viewer's left = wearer's right)
    ax = axs[2]
    ax.set_title("FRONT view (wearer side: frame topology, harness)", fontsize=11)

    def X(x):  # mirror so the view is as seen from the front
        return -x
    stay = [(FOOT[0], 0), (ELBOW[0], ELBOW[2]), (STAY_TOP[0], STAY_TOP[2])]
    for sx in (-1, 1):
        ax.plot([X(sx * p[0]) for p in stay], [p[1] for p in stay], color=FR, lw=4)
        zt = smid["crown_top_z"]
        ax.plot([X(sx * 115)] * 2, [zt - CROWN_LEG, zt], color="#555", lw=2.4, ls="--")
    ax.add_patch(plt.Rectangle((-125, 50), 250, 140, fc="#333", ec=FR, alpha=0.5))
    ax.text(0, 70, "lumbar plate (pm45)", ha="center", color="w", fontsize=7.5)
    for z, lab in ((330, "mid bar z=330"), (520, "upper bar + index latch z=520")):
        ax.plot([-115, 115], [z, z], color=FR, lw=3)
        ax.text(0, z + 12, lab, ha="center", fontsize=7.5)
    zt = smid["crown_top_z"]
    ax.plot([-115, 115], [zt, zt], color="#555", lw=3, ls="--")
    ax.add_patch(plt.Rectangle((-18, zt - 300), 36, 300, fc="#888", ec=FR, alpha=0.6))
    for k in range(17):
        ax.plot([0], [zt - 300 + 25 + k * PITCH], ".", color="k", ms=2.5)
    yk = smid["yoke_anchor"][2]
    ax.add_patch(plt.Rectangle((-130, yk - 30), 260, 60, fc="#a9a9a9", ec=FR, alpha=0.8))
    ax.text(140, yk, "yoke on crown\n(19 in shown)", ha="left", va="center", fontsize=7.5)
    for sx in (-1, 1):
        xs = [sx * 70, sx * 95, sx * 120, sx * 125]
        zs_ = [yk, yk - 120, yk - 300, 130]
        ax.plot(xs, zs_, color="#666", lw=12, alpha=0.45, solid_capstyle="round")
        ax.plot([sx * 70, sx * 75], [zt, yk + 25], color="#a67c00", lw=1.6)
    for sx in (-1, 1):
        ax.add_patch(MPoly([(sx * 70, 60), (sx * 290, 75), (sx * 300, 165), (sx * 70, 190)], fc="#1f5fa0", alpha=0.25, ec="#1f5fa0"))
        camo_patch(ax, [(sx * 230, 75), (sx * 290, 75), (sx * 305, 120), (sx * 290, 165), (sx * 230, 165), (sx * 245, 120)], 1 if sx > 0 else 0)
    ax.plot([0], [120], "D", color="#1f5fa0", ms=8)
    for name in ("shelf_pivot", "shelf_strap_anchor_fixed", "load_wing_lash_z80", "load_wing_lash_z250", "load_wing_lash_z420", "hip_stabilizer_anchor"):
        for side in ("R", "L"):
            p = hp[f"{name}_{side}"]
            ax.plot([X(p[0])], [p[2]], "o", mfc="none", mec=DIM, ms=6)
    ax.text(0, -60, "o = hard points (shelf pivot, shelf-strap, load-wing lash, hip stabilizer)\n"
                   "hipbelt S-XL swap on the Ti pivot (diamond); J or S straps on the yoke",
            ha="center", fontsize=8)
    dim(ax, (X(135), -20), (X(-135), -20), "270 c-c at feet")
    dim(ax, (X(115), 455), (X(-115), 455), "230 c-c upper (parallel)")
    dim(ax, (330, 0), (330, 120), "120", rot=90)

    for a in axs:
        a.set_aspect("equal"); a.axis("off")
    axs[0].set_xlim(-300, 300); axs[0].set_ylim(-150, 980)
    axs[1].set_xlim(-610, 640); axs[1].set_ylim(-150, 980)
    axs[2].set_xlim(-330, 360); axs[2].set_ylim(-110, 980)
    w = geom["weight"]
    fig.text(0.5, 0.015,
             f"Main bag {geom['volumes']['main_bag_L']} L ({geom['volumes']['main_bag_cu_in']} cu in, computed)  |  lid {geom['volumes']['lid_main_L'] + geom['volumes']['lid_underlid_L']:.1f} L, "
             f"side pockets 2x{geom['volumes']['side_pocket_each_L']} L, hipbelt pockets 2x{geom['volumes']['hipbelt_pocket_each_L']} L, collar +{geom['volumes']['collar_L']} L (not counted)  |  "
             f"weight budget {w['total_g']:.0f} g ({w['total_lb']} lb)  |  torso 15-23 in, hipbelt S-XL, 150 lb rated",
             ha="center", fontsize=9.5, bbox=dict(fc="#f3efe3", ec="#999"))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.06, wspace=0.02)
    SCREEN.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SCREEN, dpi=100)
    plt.close(fig)


if __name__ == "__main__":
    main()
