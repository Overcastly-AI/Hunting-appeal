"""CORRIE: the owner's pick (2026-11-07, DECISIONS commit 92e60f6): concept 13 MANTLE (side compression wings) +
the HATCH horseshoe (U) zip door + roll-top + a top pouch for loose goods. Engineered concept, the step before a
pattern release. Study code: the released SPINE files are only read.

    python designs/pack_5200/concepts/corrie.py        # numbers (naive merge vs optimised), seam check

Write-up: designs/pack_5200/analysis/corrie_body.md. Renders: corrie_render.py.

Name: CORRIE (a glacial cirque; original, no brand uses it for a pack that we found in the research).

Key decisions (each traced in the write-up):
* Door on the AFT face (the only face the wings do not cover). Wing straps hook to webbing loops sewn INTO the aft
  corner seams, outboard of the door zip (zip inset 45 mm), so the wings stay cinched while the door opens.
* Door z 110 -> 650, hinge at the top (U opens down one side, across the bottom, up the other). #10 coil, two sliders
  parking in fabric garages at the two upper ends, 3 mm cord pulls in rubber sleeves (quiet, gloved).
* Guy tabs B-22 move from z 752 (SPINE face) to z 695 on the hinge band (the box collar seam is z 736; the 50 x 60 tab
  spans z 665-725, 11 mm clear of the collar seam and 15 mm clear of the door top).
* Top pouch: removable 4.0 L boxed pouch riding on the closed roll, one straight #8 zip on its aft edge, 2 rear
  straps to the frame-side hem + 2 front G-hooks to the roll clips (all HAUL family).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
from bag_concepts import SA_BODY, SA_FLAT, Z0, _accent_rect, _chevron, _seam  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import rect_panel  # noqa: E402

NAME = "CORRIE"
SLUG = "corrie"
DOOR = {"inset": 45.0, "z_lo": 110.0, "z_hinge": 650.0, "r": 60.0}   # DECISION (this file docstring)
B22_Z = 695.0           # guy corner tabs on the hinge band (were z 752 on SPINE's B-02d)
B22_X = 149.0           # unchanged x (bag_attachment.md section 1)
POUCH = {"L": 320.0, "W": 210.0, "H": 70.0}                         # ASSUMPTION: outer box, mm
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")
LADDER = MAT.load("ladder_lock_25mm").require("mass_g")
G_HOOK = W.G_HOOK_G      # 4 g ASSUMPTION (HAUL family)
FIDLOCK = MAT.load("fidlock_magnetic_buckle_25mm").require("mass_g")   # 15 g
ZIP8_GM = MAT.load("coil_zipper_8").require("mass_g_m")             # 15 g/m
SLIDER8_G = 4.0          # ASSUMPTION (bag_weight_plan.md: #8 slider 4.0 g)
CORD_PULL_G = 1.5        # ASSUMPTION: 3 mm Dyneema loop 120 mm + rubber sleeve, per slider


def make() -> BC.Concept:
    c = BC.Concept(key=SLUG, name=NAME, kind="box",
                   tagline="Box body, side compression wings, horseshoe door, roll-top, top pouch",
                   access="roll-top + horseshoe #10 door on the aft face z 110-650 + 4 L top pouch")
    c.solve()
    return c


def pouch_volume_L(P=POUCH) -> float:
    """Boxed pouch, ASSUMPTION 15 % loss for rounded stuffed corners."""
    return P["L"] * P["W"] * P["H"] * 0.85 / 1e6


def build(c: BC.Concept, optimised=True) -> BC.Build:
    """``optimised=False`` = the naive merge (MANTLE wings as drawn + HATCH door + the current 4.9 L optional lid with
    4 magnetic buckles), the baseline for the savings table."""
    b, per = W.box_body(c)
    # aft face -> U-surround + door + hinge band (HATCH construction, CORRIE door geometry)
    b.pieces = [(p, g) for p, g in b.pieces if p.piece_id != "B-02"]
    b.seams = [s for s in b.seams if not s[0].name.startswith(("aft face", "bottom | aft"))]
    sur, door, band, L_zip = BC.hatch_face(c, DOOR)
    G = next(p for p, _ in b.pieces if p.piece_id == "B-03")
    BOT = next(p for p, _ in b.pieces if p.piece_id == "B-05")
    b.pieces += [(sur, "shell"), (door, "shell"), (band, "shell")]
    b.seams += [
        _seam([sur.edge("outer_right"), band.edge("right")], G.edge("aft"), "aft face R | gusset R (wing-strap loops in it)",
              "bound"),
        _seam([sur.edge("outer_left").reversed(), band.edge("left").reversed()], G.edge("aft"),
              "aft face L | gusset L (wing-strap loops in it)", "bound"),
        _seam(sur.edge("bottom"), BOT.edge("top").reversed(), "bottom | U-surround", "bound"),
        _seam(door.edge("zip"), sur.edge("zip").reversed(), "horseshoe door | surround (#10 zip)", "zip"),
        _seam([sur.edge("top_left").reversed(), door.edge("hinge").reversed(), sur.edge("top_right").reversed()],
              band.edge("bottom"), "surround tops + door hinge | hinge band", "bound"),
    ]
    b.zips.append({"name": "horseshoe door zip #10, 2 sliders", "length_mm": L_zip, "corners": 2,
                   "z": (DOOR["z_lo"], DOOR["z_hinge"]), "where": "door | U-surround"})
    b.extra["zip_door_mm"] = L_zip
    b.extra["bartacks"] = b.extra.get("bartacks", 0)
    W.add_hw(b, "door: 2 cord pulls (3 mm Dyneema + rubber sleeve)", 2 * CORD_PULL_G, 0)
    gar = rect_panel("door zip garage (camo)", 40, 60, 0.0, seam_allowance_mm=SA_FLAT,
                     material_id="polyester_ht_630d_printable", quantity=2, piece_id="SH-07")
    b.pieces.append((gar, "accent"))
    b.appliques.append(gar)
    # ---- wings
    if optimised:
        wing = rect_panel("side compression wing (hemmed edges)", 200, 450, 0.0,
                          seam_allowance_mm={"default": SA_FLAT, "left": SA_BODY}, material_id="cordura_330d_nylon66",
                          quantity=2, piece_id="M-01")
        b.pieces.append((wing, "wing"))
        b.seams.append(_seam(wing.edge("left"), wing.edge("left"), "wing root | B-01 / gusset seam (x2)", "bound"))
        b.seams.append(_seam(wing.edge("left"), wing.edge("left"), "wing root, second side", "bound"))
        for e in ("bottom", "right", "top"):
            b.seams.append(W.vseam(f"wing hem {e} (x2)", 2 * wing.edge_length(e), 0.0, "flat"))
        bar = _accent_rect("wing leading-edge bar (camo)", 25, 450, "SH-06", qty=2)
        b.pieces.append((bar, "accent"))
        b.appliques.append(bar)
        for i in range(4):   # 2 straps per wing: 25 mm 0.22 m, G-hook on the wing, loop in the corner seam
            W.add_hw(b, f"wing strap {i + 1}: 25 mm 0.22 m + G-hook + ladder lock + seam loop 0.08 m",
                     0.30 * WEB25 + G_HOOK + LADDER, 2)
    else:
        for side in ("R", "L"):
            from huntkit.patterns import tapered_panel
            wp = tapered_panel(f"side compression wing {side}", 230, 250, 700, seam_allowance_mm=SA_FLAT,
                               material_id="cordura_330d_nylon66", piece_id="M-0x")
            b.pieces.append((wp, "wing"))
            b.seams.append(_seam(wp.edge("left"), wp.edge("left"), f"wing {side} root", "bound"))
            bind = _accent_rect(f"wing {side} edge binding (camo)", 32, 700 + 250 + 230, "SH-06")
            b.pieces.append((bind, "accent"))
            b.appliques.append(bind)
            for i in range(3):
                W.add_hw(b, f"wing {side} strap {i + 1}", 0.30 * WEB25 + G_HOOK + LADDER, 2)
    # ---- camo: chevron kick plate (wear line), roll-top hem band
    W.accents_common(b, c, per)
    # ---- top pouch
    if optimised:
        P = POUCH
        top = rect_panel("pouch top (camo)", P["L"], P["W"], 0.0, seam_allowance_mm=SA_FLAT,
                         material_id="polyester_ht_630d_printable", piece_id="L-21")
        base = rect_panel("pouch base", P["L"], P["W"], 0.0, seam_allowance_mm=SA_FLAT,
                          material_id="cordura_330d_nylon66", piece_id="L-22")
        box = rect_panel("pouch boxing strip", 2 * (P["L"] + P["W"]), P["H"], 0.0, seam_allowance_mm=SA_FLAT,
                         material_id="cordura_330d_nylon66", piece_id="L-23")
        b.pieces += [(top, "pouch"), (base, "pouch"), (box, "pouch")]
        b.appliques.append(top)
        b.seams += [_seam([top.edge(e) for e in ("bottom", "right", "top", "left")], box.edge("top"),
                          "pouch top | boxing strip (#8 zip on the aft long side)", "ring"),
                    _seam([base.edge(e) for e in ("bottom", "right", "top", "left")], box.edge("bottom"),
                          "pouch base | boxing strip", "ring"),
                    _seam(box.edge("left"), box.edge("right").reversed(), "boxing strip end")]
        # zip on the aft long edge: a straight run of the top | boxing seam, 300 mm, one slider + cord pull, garage
        b.zips.append({"name": "pouch zip #8, 1 slider", "length_mm": 300.0, "corners": 0, "z": (0, 0),
                       "where": "pouch aft edge", "mass_g": ZIP8_GM * (300.0 + 60) / 1000 + SLIDER8_G})
        W.add_hw(b, "pouch: 4 x 25 mm 0.12 m straps + 4 G-hooks (2 rear to the hem loops, 2 front to the roll clips)",
                 4 * (0.12 * WEB25 + G_HOOK), 4)
        W.add_hw(b, "pouch zip cord pull", CORD_PULL_G, 0)
        b.extra["pouch_L"] = round(pouch_volume_L(), 2)
    else:   # the current optional lid L-01..L-03 (4.9 L, 141.2 g with 4 magnetic buckles; geometry.yaml)
        W.add_hw(b, "current optional lid / hip pack (4.9 L, geometry.yaml lid_accessory_g)", 141.2, 0)
        b.extra["pouch_L"] = 4.89
    b.extra["b22_z"] = B22_Z
    b.extra["optimised"] = optimised
    # no centre zip in CORRIE (the door replaces it)
    return b


def door_reach(c: BC.Concept) -> dict:
    """What the door opening reaches (z range, clear width at IM1-IM3 and at the floor)."""
    out = {}
    for nm, z in BC.STATIONS.items():
        w = 2 * (float(c.a([z])[0]) - DOOR["inset"])
        inside = DOOR["z_lo"] <= z <= DOOR["z_hinge"]
        out[nm] = {"z": z, "clear_width_mm": round(w, 0) if inside else 0.0, "through_door": inside}
    out["floor"] = {"z": DOOR["z_lo"], "clear_width_mm": round(2 * (BC.A_BOT - DOOR["inset"]) - 2 * DOOR["r"] * 0.3, 0),
                    "note": "door sill 75 mm above the floor (z 35)"}
    return out


def guy_check(c: BC.Concept) -> dict:
    """B-22 on the hinge band: clearances to the collar seam and the door top; guy angle from the hood ear."""
    tab_h = 60.0
    hood_ear = np.array([95.0, 21.7, 702.6])        # 19 in hood ear (bag_attachment.md: ears x +/-95, bar z 702.6)
    tab = np.array([B22_X, float(c.y_front([B22_Z])[0]), B22_Z])
    old = np.array([B22_X, float(BC.y_frame([752.0])[0]) + 290.0, 752.0])
    ang = lambda v: math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))  # noqa: E731
    return {"collar_seam_z": c.z_c, "tab_top_z": B22_Z + tab_h / 2, "clear_to_collar_seam_mm": round(c.z_c - B22_Z - tab_h / 2, 1),
            "clear_to_door_top_mm": round(B22_Z - tab_h / 2 - DOOR["z_hinge"], 1),
            "guy_len_mm": round(float(np.linalg.norm(tab - hood_ear)), 0),
            "guy_rise_deg": round(ang(tab - hood_ear), 1), "spine_guy_rise_deg": round(ang(old - hood_ear), 1)}


def cloth_sim_estimate(geo_cg_y: float) -> dict:
    """Cloth sim NOT run on this body (the sim loads the v3.1 release pieces by id; a box-body loader is a hand-off).
    Estimate: SPINE's simulated fill-case CG minus its geometric CG (the peel the hood + guys do not remove) added
    to CORRIE's geometric CG. SPINE: sim 189 / 179 / 170 mm at 15 / 19 / 23 in (bag_attachment.md PR runs), geometric
    148.2 mm (geometry.yaml). ASSUMPTION: the same peel per torso; the shorter box (collar seam 45 mm lower) peels
    less, so this is conservative."""
    sim_spine = {15: 189.0, 19: 179.0, 23: 170.0}
    meat_spine = {15: 181.0, 19: 174.0, 23: 166.0}
    peel = {t: v - 148.2 for t, v in sim_spine.items()}
    fill = {t: round(geo_cg_y + p, 0) for t, p in peel.items()}
    meat = {t: round(meat_spine[t] + (geo_cg_y - 148.2), 0) for t in meat_spine}
    return {"fill_est_mm": fill, "meat_est_mm": meat, "rev_c_bag_mm": 205.0, "rev_c_meat_mm": 190.0,
            "inside_rev_c": all(v <= 205 for v in fill.values()) and all(v <= 190 for v in meat.values())}


def pouch_cg_shift(c, kg=1.0, rated=68.0):
    """CG shift of the rated load if the pouch carries ``kg`` (ASSUMPTION 1 kg of loose goods) at its centre."""
    zc = c.z_fill + 22 + 18 + POUCH["H"] / 2       # seated on the closed roll (as corrie_render.pouch_soup)
    yc = float(BC.y_frame([c.z_fill])[0]) + BC.D_TOP / 2 + 15
    return {"pouch_centre_y": round(yc, 0), "pouch_centre_z": round(zc, 0), "kg": kg, "rated_kg": rated, "zc": zc, "yc": yc}


def numbers():
    c = make()
    v = BC.volumes(c)
    opt, naive = build(c, True), build(make(), False)
    m, mn = BC.metrics(opt), BC.metrics(naive)
    return c, opt, naive, m, mn, v


if __name__ == "__main__":
    import json
    c, opt, naive, m, mn, v = numbers()
    print("volume", v["volume_L"], "pouch", opt.extra["pouch_L"], "fill in", v["fill_height_in"], "CG", v["cg_y"], v["cg_z"])
    print("optimised", m["mass_g"], m["cut_pieces"], m["seam_length_m"], m["curved_seams"], m["zip_length_m"], m["hours_total"])
    print("naive", mn["mass_g"], mn["cut_pieces"], mn["hours_total"])
    print(json.dumps(door_reach(c)), json.dumps(guy_check(c)), json.dumps(cloth_sim_estimate(v["cg_y"])))
    from huntkit.patterns import check_seams
    real = [s for s, t in opt.seams if "flat" not in t and s.a[0].piece is not s.b[0].piece]
    print(check_seams(real, tol_mm=1.0) or check_seams(real, tol_mm=1.0))
