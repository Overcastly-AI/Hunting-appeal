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


# Revisions. A (2026-11-07): flat-panel rule volume 85.2 L (collar seam solved). The cloth sim (2026-11-08,
# huntkit/clothsim/corrie_bag.py, scenarios corrie_PR15/19/23) showed a box of flat panels stuffs to ~97 L (fill) /
# ~102 L (packed) because the flat faces bulge, against 86-87 L for SPINE, and pushes the 15 in meat-case CG to 198 mm
# (rev C basis 190). B (2026-11-08, DEFAULT): same collar seam (z 736.3), depth scaled x 0.894 (bottom 190 -> 170,
# shoulder nominal 302 -> 270 mm) so the SEWN (simulated) volume matches SPINE's sewn volume. The flat-panel rule
# volume of rev B is then ~76 L: for a box, the rule under-counts the stuffed bag (R-01's +/-5 % assumption does not
# hold for flat panels).
REVS = {"A": {"d_bot": BC.D_BOT, "d_nom": BC.D_MAX, "z_c": None},
        "B": {"d_bot": 170.0, "d_nom": 270.0, "z_c": 736.3}}
REV = "B"


def make(rev: str | None = None) -> BC.Concept:
    r = REVS[rev or REV]
    c = BC.Concept(key=SLUG, name=NAME, kind="box", d_bot=r["d_bot"], d_nom=r["d_nom"],
                   tagline="Box body, side compression wings, horseshoe door, roll-top, top pouch",
                   access="roll-top + horseshoe #10 door on the aft face z 110-650 + 4 L top pouch")
    if r["z_c"] is None:
        c.solve()
    else:
        c.z_c = r["z_c"]
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


# =====================================================================================================================
# Rev B.1 (2026-11-09): integration of DECISIONS 2026-11-09 ("Owner delegated the open choices"):
# pockets IMP-1, -2, -3, -4, -5, -6, -8 (loadout_study.md section 6) + hipbelt B (hipbelt_fit.md) as CORRIE's belt.
# Concept level: pieces are huntkit.patterns Pieces with finished (seam-line) dims; masses = cut area x record gsm +
# hardware records (data/materials) or the ASSUMPTIONs named here. Straight seams only; the hipbelt pocket faces follow
# the cone-cut wing outline, whose bow over a pocket span is < 2 mm (sewn straight, see hip_pockets()).
# =====================================================================================================================
SA_P = 8.0                                          # flat-work seam allowance on pocket pieces (as bag_concepts SA_FLAT)
CORD2_GM = MAT.load("dyneema_cord_2mm").require("mass_g_m")          # 2.5 g/m
CORDLOCK_G = MAT.load("cord_lock_spring").require("mass_g")          # 2.5 g
ZIP5_GM = MAT.load("coil_zipper_5").require("mass_g_m")              # 10 g/m
SLIDER5_G = 3.0          # ASSUMPTION (loadout_study.md section 8, #5 slider)
XLPE_RHO = MAT.load("xlpe_foam").require("density_kg_m3")            # 33 kg/m3 (generic record)
HYP_GSM = MAT.load("hypalon_coated_nylon").require("areal_density_gsm")
LADDER_HEAVY_G = MAT.load("ladder_lock_25mm_heavy").require("mass_g")   # 7 g, materials-engineer 2026-11-09 (64e431c)
DRING_G = MAT.load("d_ring_25mm_aluminium").require("mass_g")           # 6 g, same commit
GRIP_GSM = float(MAT.load("silicone_grip_print").get("areal_density_g_m2"))   # 46 g/m2, same commit
SHOCK_NOTE = "no shock-cord record: 2 mm Dyneema cord mass used as the proxy (ASSUMPTION, same g/m)"


def _P(pid, name, w, h, mid, qty=1, sa=SA_P):
    return rect_panel(name, w, h, 0.0, seam_allowance_mm=sa, material_id=mid, quantity=qty, piece_id=pid)


def _imp(id_, name, where, pieces, hw, seam_m, attach, zips=0, zip_m=0.0, tacks=0, extra_h=0.0, **kw):
    """One adopted improvement: pieces (huntkit Pieces), hardware [(item, g)], beginner hours (BC.HOURS model)."""
    H = BC.HOURS
    fab = sum(BC.piece_mass_g(p) for p in pieces)
    hwg = sum(g for _, g in hw)
    hours = (sum(p.quantity for p in pieces) * H["cut_piece"] + seam_m * H["straight_m"] + zips * H["zip_fixed"]
             + zip_m * H["zip_m"] + tacks * H["bartack"] + extra_h)
    return dict(id=id_, name=name, where=where, pieces=pieces, hardware=hw, fabric_g=round(fab, 1), hardware_g=round(hwg, 1),
                mass_g=round(fab + hwg, 1), hours=round(hours, 2), seam_m=seam_m, attach=attach, **kw)


# ---- the bag-side pockets (size-independent)
SCOPE_SLEEVE = {"w": 330.0, "h": 430.0, "lines_apart": 160.0, "z": (165.0, 595.0)}   # DECISION (section 5b of the doc)
HYDRO = {"w": 250.0, "h": 430.0, "z": (545.0, 975.0), "port": (40.0, 60.0), "port_z": 700.0}
DOOR_POCKET = {"w": 200.0, "h": 280.0, "bellows": 60.0, "z": (350.0, 630.0), "zip": 180.0}
STRAP_POCKET = {"w": 90.0, "h": 175.0, "stretch_depth": 18.0}   # ASSUMPTION: power-mesh face stretches to 18 mm
CAM_CUP = {"w": 130.0, "h": 160.0, "base": (60.0, 100.0)}
HOLSTER = {"mesh": (290.0, 240.0), "base": 95.0, "back": (105.0, 210.0), "bottle_d": 89.0}


def door_width(z: float, c: BC.Concept | None = None) -> float:
    c = c or make()
    return 2 * (float(c.a([z])[0]) - DOOR["inset"])


def bag_pockets(c: BC.Concept | None = None) -> list:
    c = c or make()
    out = []
    # IMP-1 scope sleeve inside the left wing M-01L
    S = SCOPE_SLEEVE
    sl = [_P("IMP1-a", "scope sleeve panel (bag side)", S["w"], S["h"], "cordura_330d_nylon66"),
          _P("IMP1-b", "scope sleeve liner facing", S["w"] - 30, S["h"] - 10, "robic_100d_ripstop")]
    xlpe = 0.300 * 0.420 * 0.003 * XLPE_RHO * 1000.0
    perim = S["w"] + S["lines_apart"]
    out.append(_imp(
        "IMP-1", "padded scope sleeve inside the left wing", "M-01L inside face, z 165-595",
        sl, [("XLPE 3 mm liner 300 x 420 (xlpe_foam density)", round(xlpe, 1)),
             ("top cinch: 3 mm shock cord 0.5 m + cord lock (" + SHOCK_NOTE + ")", 0.5 * CORD2_GM + CORDLOCK_G)],
        seam_m=2 * S["h"] / 1000 + S["w"] / 1000 + 2 * (S["w"] + S["h"]) / 1000, tacks=2, extra_h=0.3,
        attach=("Sleeve panel (330D, XLPE 300 x 420 sandwiched under a 100D facing, edge-stitched) sewn to the wing's inside "
                "face on two straight vertical lines 160 mm apart (20 mm in from each wing edge), before the wing is hemmed. "
                "Bottom: the 170 mm excess folds into two 85 mm box pleats caught in the wing's bottom hem (straight). Top: "
                "3 mm shock-cord channel with a cord lock. The XLPE faces the bag (scope cannot touch the gusset or hardware)."),
        perimeter_mm=perim, fits={"spotter_85 (110 x 150 section, perimeter needed ~410 mm + 5 %)": perim >= 1.05 * math.pi * (110 + 150) / 2,
                                  "spotter_85 length 372 <= 430": 372 <= S["h"]}))
    # IMP-2 hydration sleeve, hung above IM3
    Hh = HYDRO
    pieces = [_P("B-09c", "hydration sleeve (folded tube, one side seam)", 2 * Hh["w"], Hh["h"], "robic_100d_ripstop", sa=10.0),
              rect_panel("hose port binding (Hypalon, slot 12 x 40)", Hh["port"][0], Hh["port"][1], 0.0, seam_allowance_mm=0.0,
                         material_id="hypalon_coated_nylon", quantity=2, piece_id="B-09p")]
    out.append(_imp(
        "IMP-2", "hydration sleeve above IM3 + 2 hose ports (R-19)", "inside, on B-01 / B-06f, z 545-975",
        pieces, [("hang tab 25 mm webbing 0.10 m on B-06f + G-hook on the sleeve", 0.10 * WEB25 + G_HOOK),
                 ("2 bottom keepers: 25 mm webbing 0.06 m tabs on B-01 at z 560 + 2 mm Dyneema loops 0.15 m", 0.12 * WEB25 + 0.30 * CORD2_GM)],
        seam_m=(Hh["h"] + Hh["w"]) / 1000 + 2 * 0.2, tacks=3, extra_h=0.4,
        attach=("Tube 250 x 430 (100D, one side seam, closed bottom) hangs by a G-hook from a 25 mm tab bartacked on the B-06f "
                "frame-side collar strip at x 0, z 985 (flat-work, before the collar ring). Bottom corners are held by 2 mm Dyneema "
                "loops to two webbing tabs on B-01 at z 560, x +/-100 (above the IM3 strap, z 520 +/- 19). Its bottom, z 545, "
                "stays clear of IM3, so the meat straps and their ports are untouched. Hose ports: two 12 x 40 mm bound slots "
                "(Hypalon frames, 40 x 60) in the B-03 gussets at z 700, 20 mm aft of the frame-side seam, both sides (R-19), "
                "above the wing tops (z 600) and below the collar seam (z 736). Roll rule: with a bladder in, the roll closes at or "
                "above z 990 (ASSUMPTION)."),
        bladder_centre_z=Hh["z"][0] + 200.0 + 10.0))
    # IMP-4 kill-kit / first-aid pocket inside the door
    D = DOOR_POCKET
    w_lo = door_width(D["z"][0], c)
    margin = (w_lo - D["w"]) / 2
    pieces = [_P("IMP4-a", "door pocket face", D["w"], D["h"], "robic_100d_ripstop"),
              _P("IMP4-b", "door pocket bellows (bottom + 2 sides, one strip)", D["w"] + 2 * D["h"], D["bellows"], "robic_100d_ripstop")]
    out.append(_imp(
        "IMP-4", "zipped kill-kit / first-aid pocket inside the top-hinged door", "B-02door inside face, z 350-630",
        pieces, [("#5 coil zip 0.18 m + 0.03 m tails", ZIP5_GM * (D["zip"] + 30) / 1000), ("#5 slider", SLIDER5_G),
                 ("cord pull (3 mm Dyneema + rubber sleeve)", CORD_PULL_G)],
        seam_m=2 * (D["w"] + 2 * D["h"]) / 1000, zips=1, zip_m=D["zip"] / 1000, extra_h=0.2,
        attach=(f"Sewn flat to the door's inside face before the door zip goes in (manufacturing step order). Door width at z 350 "
                f"is {w_lo:.0f} mm, so the 200 mm face leaves {margin:.0f} mm each side to the zip line (zip SA 10 mm). The bellows "
                "strip runs bottom + both sides (straight, two pivots); the #5 zip runs along the top edge under a 15 mm "
                "fold-over lip. With the door opened upward the pocket lies face-up, so nothing spills when unzipped."),
        interior_mm=(D["w"] - 8, D["h"] - 8, D["bellows"] - 2), door_width_at_bottom_mm=round(w_lo, 0),
        loadout_proposal_note="loadout_study.md proposed 300 x 340; the door is only 249-304 mm wide at z 350-650, so it shrank"))
    # IMP-6 shoulder-strap phone pocket
    Sp = STRAP_POCKET
    pieces = [_P("IMP6-a", "phone pocket face (power mesh)", Sp["w"], Sp["h"], "power_mesh_nylon_spandex"),
              _P("IMP6-b", "phone pocket back", Sp["w"], Sp["h"], "cordura_330d_nylon66")]
    out.append(_imp(
        "IMP-6", "shoulder-strap phone pocket (160 mm phone)", "left J-strap, front face, top 120 mm below the yoke",
        pieces, [("2 wrap straps 25 mm x 0.15 m + 2 G-hooks (HAUL family)", 0.30 * WEB25 + 2 * G_HOOK),
                 ("top cinch 0.25 m 3 mm shock cord + cord lock (" + SHOCK_NOTE + ")", 0.25 * CORD2_GM + CORDLOCK_G)],
        seam_m=2 * (Sp["w"] + Sp["h"]) / 1000, tacks=4, extra_h=0.1,
        attach=("Mesh face over a 330D back, sewn on 3 sides (straight), top edge in a shock-cord channel with a cord lock (quiet, "
                "no hook-and-loop). Two 25 mm wrap straps sewn across the back hook round the strap with G-hooks, so it moves "
                "to either strap and comes off. The J-strap is 72 -> 58 mm wide (geometry.yaml harness); the 90 mm pocket "
                "overhangs ~13 mm a side at the mounting height."),
        interior_mm=(Sp["h"] - 7, Sp["w"] - 6, Sp["stretch_depth"])))
    # IMP-8 bow cam cup at the foot of the right wing
    Cc = CAM_CUP
    pieces = [_P("IMP8-a", "cam cup body (folded, 2 side seams)", Cc["w"], Cc["h"], "cordura_330d_nylon66"),
              rect_panel("cam cup base (Hypalon)", Cc["base"][0], Cc["base"][1], 0.0, seam_allowance_mm=0.0,
                         material_id="hypalon_coated_nylon", piece_id="IMP8-b")]
    out.append(_imp(
        "IMP-8", "bow cam / limb cup at the foot of the right wing", "B-03R | B-05 aft corner, below M-01R (z 35-150)",
        pieces, [], seam_m=0.5, tacks=2, extra_h=0.1,
        attach=("Cup body folded in half (65 x 160 finished pocket, two straight side seams), the Hypalon base stitched across "
                "the bottom fold as the wear face; the cup's back edge is caught in the B-03R | B-05 bound seam at the aft corner, "
                "below the wing (z 35-150), so the lower cam sits in it while the riser rides the B-11 loops. Restores SPINE SH-04's "
                "function.")))
    return out


# ---- belt B on CORRIE (per size) and the belt-side pockets IMP-3, IMP-5
BELT_SIZES = ("S", "M", "L", "XL", "XXL")
HIP_ROOT_CLEAR = 30.0      # hipbelt_concepts.pocket_room(): stabilizer strap + wing joint
HIP_TIP_CLEAR = 35.0       # stiffener inset 10 + soft-tip gap 15 + 10 (same)
HIP_POCKET_MIN = 80.0      # DECISION: a pocket shorter than 80 mm (interior < 65) is not worth a zip
HIP_GUSSET = 55.0          # finished gusset width (as HP-02 today)
HIP_EDGE = 10.0            # pocket face inset from the wing's bound edge


def _hb():
    import hipbelt_concepts as HC   # noqa: E402 (designs/pack_5200/concepts)
    from huntkit.gendesign import hipbelt as hb  # noqa: E402
    return HC, hb


def _wing_outline(size):
    HC, hb = _hb()
    lo, hi = HC.SIZES_B[size]
    band = int(round((lo + hi) / 2 / 2) * 2)
    form = hb.hip_form("male", band)
    T, Bt, _ = hb.wing_flat(HC.B, form, size)
    return T, Bt, form


def _face(T, Bt, x0, x1, inset=HIP_EDGE, knots=()):
    """Pocket face polygon = the developed wing outline between x0 and x1, inset from the bound edges."""
    from shapely.geometry import Polygon, box
    poly = Polygon([tuple(p) for p in Bt] + [tuple(p) for p in T[::-1]])
    f = poly.intersection(box(x0, -500, x1, 500)).buffer(-inset, join_style=2)
    xs = np.linspace(x0 + inset, x1 - inset, 40)
    top = np.interp(xs, T[:, 0], T[:, 1]) - inset
    bot = np.interp(xs, Bt[:, 0], Bt[:, 1]) + inset

    def bow(y):
        """Max deviation from straight runs, with a pivot at the crest-zone height station (B.wing_h knot at 45 % of
        the wing, if it falls inside the pocket): bag_concepts' rule, a kink is a pivot, a bow > 5 mm is a curve."""
        kn = [xs[0]] + [k for k in knots if xs[0] < k < xs[-1]] + [xs[-1]]
        yk = np.interp(kn, xs, y)
        return float(np.max(np.abs(y - np.interp(xs, kn, yk))))
    return f, {"len": x1 - x0 - 2 * inset, "h_root": float(top[0] - bot[0]), "h_tip": float(top[-1] - bot[-1]),
               "h_mean": float(np.mean(top - bot)), "bow_top_mm": round(bow(top), 2), "bow_bot_mm": round(bow(bot), 2)}


def _hip_pocket(size, side, x0, x1, T, Bt):
    from huntkit.patterns import Piece
    HC, _ = _hb()
    knots = [f * float(T[-1, 0]) for f, _h in HC.B.wing_h[1:-1]]
    f, m = _face(T, Bt, x0, x1, knots=knots)
    m["pivots"] = len([k for k in knots if x0 + HIP_EDGE < k < x1 - HIP_EDGE])
    m["straight"] = max(m["bow_top_mm"], m["bow_bot_mm"]) <= BC.CURVE_SAGITTA
    face = Piece(f"hipbelt pocket face {side} ({size})", list(f.exterior.coords)[:-1], seam_allowance_mm=SA_P,
                 material_id="cordura_330d_nylon66", piece_id=f"HP-01{side}-{size}", size=size)
    g_len = m["len"] + m["h_root"] + m["h_tip"]
    gus = _P(f"HP-02{side}-{size}", f"hipbelt pocket gusset {side} ({size})", g_len, HIP_GUSSET, "cordura_330d_nylon66")
    zip_len = m["len"] + 20.0
    hw = [(f"#8 coil zip {zip_len:.0f} mm", ZIP8_GM * zip_len / 1000), ("#8 slider", SLIDER8_G), ("cord pull", CORD_PULL_G)]
    interior = (round(m["len"] - 15, 0), round(m["h_mean"] - 18, 0), HIP_GUSSET - 5)   # loadout_study.md rule
    vol = interior[0] * interior[1] * interior[2] / 1e6
    return _imp(f"IMP-5{side}", f"hipbelt pocket {side}, size {size}", f"belt B wing {side}, x {x0:.0f}-{x1:.0f} from the root",
                [face, gus], hw, seam_m=(2 * g_len + m["len"]) / 1000, zips=1, zip_m=zip_len / 1000, extra_h=0.1,
                attach=("Face cut to the developed (cone-cut) wing outline 10 mm inside the binding; gusset sewn round bottom "
                        "and ends; #8 zip along the top. The pocket assembly is sewn to the wing shell HB-W1 (flat-work, before "
                        "the foam goes in), its top and bottom caught in the wing binding. Clear of the 30 mm root zone and of "
                        "the soft tip / 2:1 D-ring."),
                x=(x0, x1), face=m, interior_mm=interior, volume_L=round(vol, 2))


def hip_layout(size: str) -> dict:
    """Left wing: one pocket over the whole room. Right wing: the IMP-3 bottle holster on the stiffened zone behind the
    crest (DECISIONS 2026-11-09), then a pocket in what is left in front of it, if >= HIP_POCKET_MIN."""
    HC, hb = _hb()
    T, Bt, form = _wing_outline(size)
    L = float(HC.B.wing_len(size))
    sec = hb.section(form)
    crest = float(sec.s_crest - HC.B.lumbar_w / 2)
    x0, x1 = HIP_ROOT_CLEAR, L - HIP_TIP_CLEAR
    hw_ = HOLSTER["back"][0]
    # holster: starts at the root clearance. "Behind the crest" is read as the BOTTLE AXIS behind the crest; the
    # 105 mm back panel runs past the crest on S (by 30 mm) and M (by 6 mm) because their wings are short (flagged
    # for fit test HB-1: the back panel is soft and sits on the outer shell, the crest-relief foam is on the body face)
    h0 = x0
    h1 = h0 + hw_
    out = {"size": size, "wing_len_mm": L, "crest_from_root_mm": round(crest, 0), "room": (x0, x1),
           "holster_x": (h0, h1), "holster_axis_behind_crest": (h0 + h1) / 2 <= crest,
           "holster_axis_vs_crest_mm": round((h0 + h1) / 2 - crest, 0),
           "holster_back_past_crest_mm": round(max(0.0, h1 - crest), 0)}
    out["L"] = _hip_pocket(size, "L", x0, x1, T, Bt)
    r0 = h1 + 10.0
    out["R"] = _hip_pocket(size, "R", r0, x1, T, Bt) if x1 - r0 >= HIP_POCKET_MIN else None
    out["R_room_mm"] = round(x1 - r0, 0)
    return out


def holster() -> dict:
    Hs = HOLSTER
    pieces = [_P("IMP3-a", "bottle holster tube (power mesh, one side seam)", *Hs["mesh"], "power_mesh_nylon_spandex"),
              _P("IMP3-b", "holster base (boxed into the tube)", Hs["base"], Hs["base"], "cordura_330d_nylon66"),
              _P("IMP3-c", "holster back panel", *Hs["back"], "cordura_330d_nylon66")]
    return _imp("IMP-3", "1 L bottle holster on belt B, right wing, behind the crest", "belt B right wing, stiffened zone",
                pieces, [("2 wing tabs 25 mm x 0.06 m (bartacked to HB-W1 shell)", 0.12 * WEB25),
                         ("2 holster straps 25 mm x 0.09 m + 2 G-hooks", 0.18 * WEB25 + 2 * G_HOOK),
                         ("top cinch 0.4 m 3 mm shock cord + cord lock (" + SHOCK_NOTE + ")", 0.4 * CORD2_GM + CORDLOCK_G)],
                seam_m=(Hs["mesh"][1] + 4 * Hs["base"] + 2 * sum(Hs["back"])) / 1000, tacks=6, extra_h=0.3,
                attach=("Two 25 mm tabs are bartacked to the right wing shell HB-W1 in flat-work, through the shell only, inside the "
                        "HDPE stiffened zone: one 20 mm below the top edge, one 20 mm above the bottom edge. The holster back "
                        "carries two 25 mm straps with G-hooks that hook the tabs. The lower hook is the 'lower tie' hipbelt_fit.md "
                        "section 7 asks for: the two hooks make a couple, so the 1.2 kg bottle cannot roll the wing down and out. "
                        "The bottle sits upright; the 210 mm back hangs ~60 mm below the wing's bottom edge (wing 145-150 mm)."),
                interior_mm=(230, 95, 95))


def belt_b(size: str) -> dict:
    """Belt B body on CORRIE, per size: hipbelt_concepts.belt_bom with the 2026-11-09 records swapped in
    (D-ring 6 g x 2 instead of 5 g x 2; grip print 46 g/m2 x printed face area instead of 5 g) and the 2:1 lock legs
    (2 x ladder_lock_25mm_heavy) added. The grip print is BOOKED in mass but not CREDITED in friction (HB-2)."""
    HC, hb = _hb()
    bom = HC.belt_bom(HC.B, size)
    face = 2 * next(r["area_mm2"] for r in bom["pieces"] if r["piece"] == "wing face") + \
        next(r["area_mm2"] for r in bom["pieces"] if r["piece"] == "lumbar face")
    grip = GRIP_GSM * face / 1e6
    corr = [("D-rings: record 2 x 6 g replaces 2 x 5 g ASSUMPTION", 2 * DRING_G - 10.0),
            (f"grip print: record 46 g/m2 x {face / 1e6:.3f} m2 replaces 5 g ASSUMPTION", grip - 5.0),
            ("2:1 lock legs: 2 x ladder_lock_25mm_heavy (ITW Superloc class)", 2 * LADDER_HEAVY_G)]
    total = bom["total_g"] + sum(g for _, g in corr)
    return {"size": size, "bom_total_g": bom["total_g"], "corrections": [(n, round(g, 1)) for n, g in corr],
            "body_g": round(total, 1), "wing_len_mm": round(float(HC.B.wing_len(size)), 0)}


# ---- weight table
SPINE_TOTAL_G = 3495.6          # geometry.yaml weight.total_g (released SPINE, belt M)
SPINE_SIDE_POCKETS_G = 60.3     # geometry.yaml weight.rows "floating side pockets x2"
SPINE_B09_G = 10.9              # panels.yaml B-09 mass_g_total (inside the main-bag fabric row)
BELT_C0_BODY_G = 165.0          # hipbelt_results.json bom.C0.total_g (current belt body, same method as belt B)
HP_TODAY_G = 8.0 + 10.7 + 0.4 * ZIP8_GM   # panels.yaml HP-01 + HP-02 mass_g_total + 0.4 m #8 zip (build_geometry row)
SPINE_BODY_G = 333.2           # SPINE bag-body group, corrie_body.md section 4 (bag_concepts.spine_build, same metric)
BELT_LOADPATH_G = 110.4         # hipbelt_structural.md section 0, size M (plate 94.6 + doublers 14.3 + thread + washer)
BELT_PAD_IF_G = 10.0            # ASSUMPTION (hipbelt_structural.md): pad bears on the frame lumbar pan, interface parts
TARGET_G = 2994.0               # ~6.6 lb published target (owner), 6.6 x 453.6


def weight_table(size: str = "M", c: BC.Concept | None = None) -> dict:
    c = c or make()
    body = BC.metrics(build(c, True))["mass_g"]["total"]
    spine_body = SPINE_BODY_G
    bp = {d["id"]: d for d in bag_pockets(c)}
    hl = hip_layout(size)
    hol = holster()
    bb = belt_b(size)
    hip_p = hl["L"]["mass_g"] + (hl["R"]["mass_g"] if hl["R"] else 0.0)
    rows = [
        ("SPINE released pack (belt M)", SPINE_TOTAL_G, "geometry.yaml weight.total_g"),
        ("CORRIE body group vs SPINE body group", body - spine_body, "corrie.build() vs bag_concepts.spine_build(), same metric"),
        ("SPINE floating side pockets (CORRIE has wings instead)", -SPINE_SIDE_POCKETS_G,
         "geometry.yaml row; CORRECTION: the rev B 3725 g total still carried them"),
        ("SPINE B-09 hydration sleeve (replaced by IMP-2)", -SPINE_B09_G, "panels.yaml B-09"),
        ("IMP-2 hydration sleeve + ports", bp["IMP-2"]["mass_g"], "corrie.bag_pockets()"),
        ("IMP-1 scope sleeve", bp["IMP-1"]["mass_g"], "corrie.bag_pockets()"),
        ("IMP-4 door pocket", bp["IMP-4"]["mass_g"], "corrie.bag_pockets()"),
        ("IMP-6 strap phone pocket", bp["IMP-6"]["mass_g"], "corrie.bag_pockets()"),
        ("IMP-8 cam cup", bp["IMP-8"]["mass_g"], "corrie.bag_pockets()"),
        (f"hipbelt body: current -> belt B ({size})", bb["body_g"] - BELT_C0_BODY_G, "hipbelt_concepts.belt_bom + 2026-11-09 records"),
        (f"hipbelt pockets: HP-01/02 today -> IMP-5 ({size}, {'2' if hl['R'] else '1'} pockets)", hip_p - HP_TODAY_G,
         "panels.yaml HP-01/02 + zip row; corrie.hip_layout()"),
        ("IMP-3 bottle holster", hol["mass_g"], "corrie.holster()"),
        ("belt B load path: 6061 bow-tie centre plate + hub + latch, root/tip doublers, thrust washer (110.4 g) "
         "replacing the 45 g PA66 plate + latch (the 6 g cant snap is already out above)", BELT_LOADPATH_G - 45.0,
         "hipbelt_structural.md section 0 (structural-fea-engineer 2026-11-09)"),
        ("frame-side lumbar pad interface", BELT_PAD_IF_G, "ASSUMPTION ~10 g, hipbelt_structural.md section 0"),
    ]
    tot = sum(r[1] for r in rows)
    return {"size": size, "rows": [(n, round(g, 1), s) for n, g, s in rows], "total_g": round(tot, 1),
            "total_lb": round(tot / 453.592, 2), "vs_spine_g": round(tot - SPINE_TOTAL_G, 1),
            "vs_target_g": round(tot - TARGET_G, 1), "rev_b_total_g": round(SPINE_TOTAL_G + body - spine_body, 1)}


def integration(c: BC.Concept | None = None) -> dict:
    c = c or make()
    bp = bag_pockets(c)
    hips = {s: hip_layout(s) for s in BELT_SIZES}
    belts = {s: belt_b(s) for s in BELT_SIZES}
    wt = {s: weight_table(s, c) for s in BELT_SIZES}
    strip = lambda d: {k: v for k, v in d.items() if k != "pieces"} | {"pieces": [  # noqa: E731
        {"id": p.piece_id, "name": p.name, "material": p.material_id, "qty": p.quantity,
         "seam_bbox_mm": [round(v, 1) for v in np.ptp(np.asarray(p.outline), axis=0)], "cut_area_mm2": round(p.area_mm2, 0),
         "mass_g": round(BC.piece_mass_g(p), 1)} for p in d["pieces"]]}
    hp = {}
    for s, h in hips.items():
        hp[s] = {k: (strip(v) if isinstance(v, dict) and "pieces" in v else v) for k, v in h.items()}
    return {"bag_pockets": [strip(d) for d in bp], "holster": strip(holster()), "hip": hp, "belt_b": belts, "weight": wt}


def numbers(rev: str | None = None):
    c = make(rev)
    v = BC.volumes(c)
    opt, naive = build(c, True), build(make(rev), False)
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
