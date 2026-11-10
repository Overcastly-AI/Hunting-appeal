"""Team B LEAN: FELL, the lightest bag system that still meets the fixed list (bag design competition 2026-11-10).

    python designs/pack_5200/bag_comp/lean/fell.py            # mass table, CORRIE comparison, build numbers

FELL (a bare upland hillside; original name) = CORRIE's cloth-sim-validated rev B box shell (same collar seam, same
85 L sewn volume, same frame interface) with:
* roll-top as the main opening; ONE straight #10 coil zip (540 mm, z 110-650, one slider) in the aft centre seam
  for meat-strap and low-gear access, instead of the 1.25 m horseshoe door with two sliders;
* no side wings: W1-W3 (frozen haul wraps; geometry.yaml says their carry-mode job is compression) compress the bag;
* light fabrics from the cited records: ULTRAGrid 210D gussets / aft face / hem, 70D ripstop collar, ULTRA 200X
  bottom (fabric_swap_evidence.md O-3 / O-4 / O-5; each carries its gate, listed in RISKS);
* 8 webbing hard points (4 in the frame-side corner seams, 4 in the aft corner seams, z 260 / 490) that take
  MODULAR add-ons with the HAUL-family G-hook: glass pod (spotter sleeve), side strap pair (tripod / poles / jacket),
  lid pod (2.7 L), strap pod (snacks / GPS). An add-on only goes on when the loadout needs it.

Masses: cut area x record gsm (huntkit.materials) through the concept library's own metric (bag_concepts.metrics),
so FELL and CORRIE are booked by the same code. Every ASSUMPTION is marked here and in analysis/bag_comp_lean.md.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(ROOT / "designs" / "pack_5200")):
    if p not in sys.path:
        sys.path.insert(0, p)

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
import corrie as CO  # noqa: E402
from bag_concepts import SA_FLAT, Z0, _chevron, _seam  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import rect_panel  # noqa: E402

NAME = "FELL"
TEAM = "B"

# ---- fabrics (records in data/materials; gates in fabric_swap_evidence.md)
UG = "ultragrid_210d_uhmwpe_ripstop"      # 132 gsm, Taber 1100 (O-4: proceed after the owner sees a swatch)
R70 = "nylon_ripstop_70d"                 # 92 gsm, tear 51.6 / 37.4 N (O-3: proceed)
U200 = "challenge_ultra_200"              # ULTRA 200X 133 gsm (O-5: proceed after PT-3 + 50 mm strip test)
CAMO = "polyester_ht_630d_printable"      # owner camo, wear-zone accents (O-6: stays 630D in wear zones)
MESH = "power_mesh_nylon_spandex"

WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")          # 18 g/m
LADDER = MAT.load("ladder_lock_25mm").require("mass_g")            # 4 g
ZIP10_GM = MAT.load("coil_zipper_10").require("mass_g_m")          # 20 g/m
ZIP5_GM = MAT.load("coil_zipper_5").require("mass_g_m")            # 10 g/m
SHOCK_GM = MAT.load("shock_cord_3mm").require("mass_g_m")          # 6 g/m
CORDLOCK = MAT.load("cord_lock_spring").require("mass_g")          # 2.5 g
XLPE_RHO = MAT.load("xlpe_foam").require("density_kg_m3")          # 33 kg/m3
G_HOOK = W.G_HOOK_G                     # 4 g ASSUMPTION (HAUL family, as CORRIE)
SLIDER10_G = BC.SLIDER_G                # 6 g ASSUMPTION (build_geometry rule, as CORRIE)
SLIDER5_G = CO.SLIDER5_G                # 3 g ASSUMPTION (loadout_study.md)
CORD_PULL_G = CO.CORD_PULL_G            # 1.5 g ASSUMPTION

ZIP = {"z_lo": 110.0, "z_hi": 650.0, "sliders": 1}       # DECISION: same z span as CORRIE's door (IM1-IM3 reach)
HARD_Z = (260.0, 490.0)                                  # hard-point loops, same heights as CORRIE's wing-strap loops
LOOP_M = 0.08                                            # 25 mm loop caught in a seam (as CORRIE, corrie.py)


DEPTH = {"d_bot": 165.0, "d_nom": 262.0, "z_c": 736.3}   # DECISION: CORRIE rev B x 0.97 in depth (see below)


def make():
    """The shell: CORRIE's rev B box (frame interface, width, collar seam z 736.3 and fill line unchanged), 3 % less
    deep (bottom 170 -> 165, shoulder nominal 270 -> 262 mm). Why: FELL's first coarse cloth sim at 15 in on the exact
    rev B depth stuffed to 89.7 L (the 70D collar is softer than Robic and bulges more), over the 85 +/- 3 L rule; the
    body below the collar seam is 62.5 L, so -3 % depth takes ~1.9 L off. It also moves the load ~4 mm forward."""
    c = BC.Concept(key="corrie", name=NAME, kind="box", d_bot=DEPTH["d_bot"], d_nom=DEPTH["d_nom"],
                   tagline="Box body, roll-top, straight centre zip, modular add-ons",
                   access="roll-top + straight #10 centre zip z 110-650 on the aft face")
    c.z_c = DEPTH["z_c"]
    return c


def _mat(p, mid):
    p.material_id = mid
    return p


# =====================================================================================================================
# Body
# =====================================================================================================================
def build(c=None) -> BC.Build:
    c = c or make()
    B1 = BC.frame_panel(c)                                           # ULTRA 200 (unchanged, frame interface)
    G = _mat(BC.gusset(c), UG)
    BOT = _mat(BC.box_bottom(c), U200)
    FR, FL = BC.front_face(c, split_x=0.0, name="aft face half", pid="B-02", mat=UG)
    FR.piece_id, FL.piece_id = "B-02R", "B-02L"
    pieces = [(B1, "shell"), (G, "shell"), (BOT, "shell"), (FR, "shell"), (FL, "shell")]
    seams = [
        _seam(B1.edge("right"), G.edge("frame").reversed(), "B-01 | gusset R (2 hard-point loops in it)", "seared"),
        _seam(B1.edge("left").reversed(), G.edge("frame").reversed(), "B-01 | gusset L (2 hard-point loops in it)",
              "seared"),
        _seam(FR.edge("outer"), G.edge("aft"), "aft half R | gusset R (2 hard-point loops in it)", "seared"),
        _seam(FL.edge("outer").reversed(), G.edge("aft"), "aft half L | gusset L (2 hard-point loops in it)", "seared"),
        _seam(FR.edge("centre"), FL.edge("centre").reversed(), "aft centre seam (#10 zip z 110-650 in it)", "zip"),
        _seam(B1.edge("bottom"), BOT.edge("bottom"), "bottom | B-01", "ring", "seared"),
        _seam([FL.edge("bottom"), FR.edge("bottom")], BOT.edge("top").reversed(), "bottom | aft halves", "seared"),
        _seam(G.edge("bottom"), BOT.edge("right"), "bottom | gusset R", "seared"),
        _seam(G.edge("bottom"), BOT.edge("left").reversed(), "bottom | gusset L", "seared"),
    ]
    b = BC.Build(c, pieces, seams, [], {"kind": "boxed", "n": 8}, [], extra={})
    tops = [B1.edge("top"), G.edge("top"), FR.edge("top"), FL.edge("top"), G.edge("top")]
    W._add_collar(b, c, tops)
    for p, g in b.pieces:                                            # collar fabrics (B-06f ULTRA 200 stays: D6)
        if p.piece_id == "B-06":
            _mat(p, R70)
        elif p.piece_id == "B-07":
            _mat(p, UG)
    b.seams = [(s, (set(t) - {"bound"}) | {"seared"} if "bound" in t else t) for s, t in b.seams]   # B-1 rule
    b.pieces.append((BC.boxed_swell(), "swell"))
    # centre zip: one straight #10 coil run, ONE slider parked at the top under a camo garage, cord pull
    L = ZIP["z_hi"] - ZIP["z_lo"]
    b.zips.append({"name": "aft centre zip #10, 1 slider", "length_mm": L, "corners": 0,
                   "z": (ZIP["z_lo"], ZIP["z_hi"]), "where": "aft centre seam",
                   "mass_g": ZIP10_GM * (L + 60) / 1000 + ZIP["sliders"] * SLIDER10_G})
    gar = rect_panel("zip garage (camo)", 40, 60, 0.0, seam_allowance_mm=SA_FLAT, material_id=CAMO, piece_id="SH-07")
    b.pieces.append((gar, "accent"))
    b.appliques.append(gar)
    W.add_hw(b, "zip cord pull (3 mm Dyneema + rubber sleeve)", CORD_PULL_G, 0)
    # camo: a V-notched kick band (sides 70 mm, centre 45 mm: stays under the zip's lower stop at z 110)
    w = 2 * BC.A_BOT
    d0 = float(c.depth([Z0])[0])
    for p in (_chevron("kick band, aft (camo, V-notch)", w, 70, 45, "SH-01a"),
              rect_panel("kick band, side (camo)", d0, 70, 0.0, seam_allowance_mm=SA_FLAT, material_id=CAMO,
                         quantity=2, piece_id="SH-01b")):
        b.pieces.append((p, "accent"))
        b.appliques.append(p)
    # 8 hard-point loops (4 frame-corner seams, 4 aft-corner seams) for the add-ons
    W.add_hw(b, f"8 hard-point loops: 25 mm webbing {LOOP_M} m each, caught in the corner seams", 8 * LOOP_M * WEB25, 8)
    b.extra["zip_mm"] = L
    return b


# =====================================================================================================================
# Fixed bag-side pockets kept from CORRIE B.2 (same function), lighter where a record allows
# =====================================================================================================================
def fixed_pockets(c=None) -> list:
    c = c or make()
    bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    out = []
    # IMP-2 hydration sleeve: same geometry and hanging, tube 100D Robic -> 70D (no load: it hangs a 2 kg bladder)
    h = dict(bp["IMP-2"])
    tube = [p for p in h["pieces"] if p.piece_id == "B-09c"][0]
    d_g = BC.piece_mass_g(tube) * (1 - MAT.load(R70).require("areal_density_gsm") / MAT.load(tube.material_id).require(
        "areal_density_gsm"))
    h2 = dict(h, id="IMP-2L", name="hydration sleeve (CORRIE IMP-2 geometry) in 70D",
              mass_g=round(h["mass_g"] - d_g, 1), fabric_g=round(h["fabric_g"] - d_g, 1))
    out.append(h2)
    out.append(dict(bp["IMP-8"], name="cam / tripod-foot cup (CORRIE IMP-8, unchanged): bow cam and tripod feet"))
    return out


def fly_g(b) -> dict:
    """Rain fly F-01 scaled with the outer shell it covers (CORRIE's G-2 rule) + the F-02 base pocket."""
    pan = CO._panels()
    fly = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-01"))
    f02 = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-02"))
    ids = ("B-03", "B-02R", "B-02L", "B-05")
    a = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in ids) / 1e6
    return {"outer_m2": round(a, 3), "fly_g": round(fly * a / CO.SPINE_OUTER_M2, 1), "pocket_g": f02,
            "total_g": round(fly * a / CO.SPINE_OUTER_M2 + f02, 1)}


# =====================================================================================================================
# Modular add-ons (HAUL-family G-hooks to the 8 hard-point loops, the roll clips or the shoulder strap)
# =====================================================================================================================
_P = CO._P
_imp = CO._imp


def addons() -> dict:
    out = {}
    # A1 GLASS POD (left side): CORRIE's IMP-1 sleeve made free-standing on its own small back panel, so it hooks on
    # and off and doubles as the left-side compression panel when fitted.
    S = CO.SCOPE_SLEEVE
    xlpe = 0.300 * 0.420 * 0.003 * XLPE_RHO * 1000.0
    pcs = [_P("A1-a", "glass pod back panel (hooks to 4 loops)", 200.0, 450.0, UG),
           _P("A1-b", "glass pod sleeve face (2 box pleats at the base)", S["w"], S["h"], R70),
           _P("A1-d", "glass pod leading-edge bar (camo)", 25.0, 450.0, CAMO)]
    out["A1"] = _imp("A1", "glass pod: padded spotter sleeve, left side", "left gusset, z 150-600",
                     pcs, [("XLPE 3 mm 300 x 420 (xlpe_foam)", round(xlpe, 1)),
                           ("top cinch 0.5 m shock cord + cord lock", 0.5 * SHOCK_GM + CORDLOCK),
                           ("4 straps 25 mm x 0.12 m + 4 G-hooks; 2 ladder locks on the aft pair",
                            4 * (0.12 * WEB25 + G_HOOK) + 2 * LADDER)],
                     seam_m=2 * (200 + 450) / 1000 + 2 * S["h"] / 1000 + 2 * (S["w"] + S["h"]) / 1000, tacks=4,
                     extra_h=0.3,
                     attach=("Back panel 200 x 450 ULTRAGrid, hemmed; sleeve face sewn to it on two straight lines "
                             "160 mm apart (CORRIE IMP-1 geometry). The XLPE lies on the back panel under the sleeve, edge-stitched "
                             "through the back panel, so no liner facing is needed (the sleeve face is the cover). Four 25 mm straps with G-hooks "
                             "hook the left frame-corner and aft-corner loops at z 260 / 490; the aft pair have ladder "
                             "locks, so the pod cinches like a wing."),
                     interior_mm=(430, 160, 150))
    # A2 SIDE STRAP PAIR (right side; a second pair is the left side when the pod is off): tripod, poles, jacket
    out["A2"] = _imp("A2", "side strap pair (tripod / poles / jacket), right side", "right gusset, loops z 260 / 490",
                     [], [("2 straps 25 mm x 0.45 m, G-hook one end, ladder lock + 60 mm tail the other",
                           2 * (0.45 * WEB25 + G_HOOK + LADDER))], seam_m=0.0, tacks=4, extra_h=0.1,
                     attach=("Each strap hooks the frame-corner loop, runs aft across the gusset and the load, and "
                             "cinches at the aft-corner loop. Tripod feet sit in the cam / tripod cup at the foot of the "
                             "gusset."))
    # A3 LID POD: CORRIE B.2's 2.7 L pouch, same straps; ULTRAGrid top, 70D base and boxing, #5 coil zip
    P = CO.POUCH_B2
    pcs = [_P("A3-a", "lid pod top", P["L"], P["W"], UG), _P("A3-b", "lid pod base", P["L"], P["W"], R70),
           _P("A3-c", "lid pod boxing strip", 2 * (P["L"] + P["W"]), P["H"], R70),
           _P("A3-d", "lid pod pull tab (camo, folded loop)", 25.0, 120.0, CAMO)]
    zl = P["L"] - 20.0
    out["A3"] = _imp("A3", "lid pod 2.7 L (optional)", "on the closed roll", pcs,
                     [(f"#5 coil zip {zl:.0f} mm + 60 mm tails", ZIP5_GM * (zl + 60) / 1000), ("#5 slider", SLIDER5_G),
                      ("cord pull", CORD_PULL_G),
                      ("4 straps 25 mm x 0.12 m + 4 G-hooks (2 rear hem loops, 2 front roll clips)",
                       4 * (0.12 * WEB25 + G_HOOK))],
                     seam_m=2 * 2 * (P["L"] + P["W"]) / 1000 + P["H"] / 1000, zips=1, zip_m=zl / 1000, tacks=4,
                     extra_h=0.5, interior_mm=CO.pouch_interior_mm(P), volume_L=round(CO.pouch_volume_L(P), 2),
                     attach="As CORRIE B.2's pouch (corrie_body.md section 3): 2 rear straps to the frame-side hem loops, "
                            "2 front straps to the roll clips. Flip it back to open the roll; unhook 4 to remove.")
    # A4 STRAP POD (right J-strap): fixes CORRIE's S-L snack miss; GPS on the sheep load
    sp = {"w": 120.0, "h": 190.0, "gusset": 50.0}   # interior 183 x 114 x 48 = 1.0 L: snacks + GPS
    pcs = [_P("A4-a", "strap pod face (power mesh)", sp["w"], sp["h"], MESH),
           _P("A4-b", "strap pod back + bellows (one strip)", sp["w"] + 2 * sp["gusset"], sp["h"] + sp["gusset"], R70)]
    out["A4"] = _imp("A4", "strap pod (snacks / GPS), right J-strap", "right shoulder strap, front face", pcs,
                     [("2 wrap straps 25 mm x 0.15 m + 2 G-hooks", 0.30 * WEB25 + 2 * G_HOOK),
                      ("top cinch 0.30 m shock cord + cord lock", 0.30 * SHOCK_GM + CORDLOCK)],
                     seam_m=2 * (sp["w"] + 2 * sp["h"]) / 1000, tacks=4, extra_h=0.2,
                     interior_mm=(sp["h"] - 7, sp["w"] - 6, sp["gusset"] - 2),
                     attach=("Mesh face boxed onto a 70D back with a 50 mm bellows (straight seams, 2 pivots); two "
                             "25 mm wrap straps with G-hooks go round the right J-strap below the hose clip. No "
                             "hook-and-loop: shock-cord top cinch."))
    return out


CONFIGS = {   # which add-ons go on, per loadout (DECISION; the loadout check below confirms each)
    "day": ("A2", "A4"),
    "elk6": ("A1", "A2", "A4"),
    "sheep8": ("A1", "A2", "A3", "A4"),
    "max": ("A1", "A2", "A3", "A4"),
}


# =====================================================================================================================
# CORRIE B.2 bag system, booked by the same code (the comparison baseline)
# =====================================================================================================================
def corrie_bag_system(c=None) -> dict:
    """CORRIE B.2: body group (corrie.build, B.2) + bag pockets IMP-1, IMP-2, IMP-4, IMP-8 + rain fly F-01 (re-cut G-2)
    + fly pocket F-02. Belt pockets / holster / belt and IMP-6 (sewn to the harness; the same part on both bags) are
    out (belt-independent bag system). W1-W3, IM1-IM3, B-11..B-24 interface parts are on both packs and out."""
    c = c or CO.make()
    b = CO.build(c, True, spec="B.2")
    body = BC.metrics(b)["mass_g"]
    bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    pan = CO._panels()
    fly = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-01"))
    a_co = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in CO.OUTER_IDS) / 1e6
    fly_c = fly * a_co / CO.SPINE_OUTER_M2
    f02 = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-02"))
    rows = [("body group (corrie.build B.2: shell, collar, swells, wings, pouch, camo, zips, hardware)", body["total"]),
            ("IMP-1 scope sleeve", bp["IMP-1"]["mass_g"]), ("IMP-2 hydration sleeve", bp["IMP-2"]["mass_g"]),
            ("IMP-4 door pocket", bp["IMP-4"]["mass_g"]), ("IMP-8 cam cup", bp["IMP-8"]["mass_g"]),
            ("rain fly F-01 re-cut for the box (G-2)", fly_c), ("fly pocket F-02", f02)]
    m = BC.metrics(b)
    hrs = m["hours_total"] + sum(bp[k]["hours"] for k in ("IMP-1", "IMP-2", "IMP-4", "IMP-8"))
    pcs = m["cut_pieces"] + sum(sum(p.quantity for p in bp[k]["pieces"]) for k in ("IMP-1", "IMP-2", "IMP-4", "IMP-8"))
    return {"rows": [(n, round(g, 1)) for n, g in rows], "total_g": round(sum(g for _, g in rows), 1),
            "body": body, "hours": round(hrs, 1), "pieces": pcs, "zip_mm": round(m["zip_length_m"] * 1000, 0),
            "curved_seams": m["curved_seams"]}


H1_PACK_M = 3943.0   # RULES.md: CORRIE B.2 on the H1 frame at belt M


def system(config="max", c=None) -> dict:
    c = c or make()
    b = build(c)
    m = BC.metrics(b)
    fx = fixed_pockets(c)
    fl = fly_g(b)
    ad = addons()
    on = [ad[k] for k in CONFIGS[config]]
    rows = [("body group (shell, collar, swells, zip, camo, hard points)", m["mass_g"]["total"])]
    rows += [(d["name"], d["mass_g"]) for d in fx]
    rows += [("rain fly F-01 scaled to the shell + F-02 pocket", fl["total_g"])]
    rows += [(f"{d['id']} {d['name']}", d["mass_g"]) for d in on]
    tot = sum(g for _, g in rows)
    pieces = m["cut_pieces"] + sum(sum(p.quantity for p in d["pieces"]) for d in fx + on) + 2   # +2 fly + pocket
    hours = m["hours_total"] + sum(d["hours"] for d in fx + on)
    zip_mm = m["zip_length_m"] * 1000 + (CO.POUCH_B2["L"] - 20.0 if "A3" in CONFIGS[config] else 0.0)
    return {"config": config, "rows": [(n, round(g, 1)) for n, g in rows], "total_g": round(tot, 1),
            "body_metrics": {k: m[k] for k in ("cut_pieces", "seam_length_m", "curved_seams", "zip_length_m",
                                               "hours_total", "pivots", "ring_seams")},
            "body_mass": m["mass_g"], "pieces": pieces, "hours": round(hours, 1), "zip_mm": round(zip_mm, 0),
            "curved_seams": m["curved_seams"], "fly": fl}


def comparison() -> dict:
    cor = corrie_bag_system()
    out = {"corrie_b2": cor, "configs": {}}
    for k in CONFIGS:
        s = system(k)
        out["configs"][k] = {"total_g": s["total_g"], "vs_corrie_g": round(s["total_g"] - cor["total_g"], 1),
                             "pack_M_on_H1_g": round(H1_PACK_M - cor["total_g"] + s["total_g"], 1)}
    out["max"] = system("max")
    return out


def volumes() -> dict:
    """Volume: the shell is CORRIE rev B's, so the flat-panel rule and the converged cloth-sim volumes carry over;
    FELL's own coarse sims (fell_clothsim.py) re-measure them with its fabrics and split aft face."""
    v = BC.volumes(make())
    return {k: (float(x) if isinstance(x, (np.floating, float)) else x) for k, x in v.items()}


def _j(o):
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.integer):
        return int(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    cmp = comparison()
    print(json.dumps({k: v for k, v in cmp.items() if k != "max"}, indent=1, default=_j))
    for n, g in cmp["max"]["rows"]:
        print(f"  {g:7.1f}  {n}")
    print("max", cmp["max"]["total_g"], cmp["max"]["body_mass"], cmp["max"]["body_metrics"], cmp["max"]["pieces"],
          cmp["max"]["hours"], cmp["max"]["zip_mm"], cmp["max"]["fly"])
    for k, d in addons().items():
        print(k, d["mass_g"], d["hours"])
    print(volumes())
