"""Team D MODULE: CACHE, a modular bag system for the 5200 pack on the H1 frame (bag competition 2026-11-10).

    python designs/pack_5200/bag_comp/D/cache.py            # numbers + result.json

Idea in one line: a light shell (CORRIE rev B's proven frame-side shell, no wings, no roll-top hardware) carries three
removable roll-top modules and two hook-on side pods; the frame-zone module ("SWAP slab") is sized to the IM1-IM3
meat straps, so on a meat trip it is emptied and goes back in as the wipeable meat liner, and the meat rides exactly
where IM1-IM3 hold it, against B-01.

Everything here is study code in the team folder. CORRIE files are only imported and read (RULES.md rule 2).
Write-up: designs/pack_5200/analysis/bag_comp_D.md. Research: docs/research/bag_comp_D.md.

Mass method = CORRIE's (bag_concepts.metrics: cut area incl. seam allowance x record gsm, zips by record g/m,
hardware by record or a stated ASSUMPTION). bag_system_g = bag + pockets + lid + compression + modules + pods + fly,
belt- and harness-independent; the fixed frame interface (hood, ladders, guys, hooks, tabs, IM straps and ports,
under-straps, B-24 links, fairleads, bow riser carry) is common to every team and is left out on both sides.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(CONCEPTS), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import rect_panel  # noqa: E402

NAME = "CACHE"
TEAM = "D"

# ---------------------------------------------------------------- records (each from data/materials/)
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")            # 18 g/m
SR25 = MAT.load("buckle_side_release_25mm").require("mass_g")        # 9 g
LADDER = MAT.load("ladder_lock_25mm").require("mass_g")              # 4 g
CORDLOCK = MAT.load("cord_lock_spring").require("mass_g")            # 2.5 g
DYN3 = MAT.load("dyneema_cord_3mm").require("mass_g_m")
SHOCK = MAT.load("shock_cord_3mm").require("mass_g_m")                # 6 g/m
ZIP5 = MAT.load("coil_zipper_5").require("mass_g_m")                  # 10 g/m
ZIP8 = MAT.load("coil_zipper_8").require("mass_g_m")                  # 15 g/m
XLPE_RHO = MAT.load("xlpe_foam").require("density_kg_m3")
G_HOOK = W.G_HOOK_G                                                   # 4 g ASSUMPTION (HAUL family, as CORRIE)
SLIDER5_G = 2.5                                                       # ASSUMPTION: #5 coil slider
SLIDER8_G = CO.SLIDER8_G                                              # 4.0 g ASSUMPTION (bag_weight_plan.md)
CORD_PULL_G = CO.CORD_PULL_G                                          # 1.5 g ASSUMPTION (corrie.py)
SA = 8.0                                                              # flat-work seam allowance (as corrie SA_P)

SIL = "silicone_coated_poly_ripstop_40d"     # 45 gsm: record notes "removable, washable meat-shelf liner"
N70 = "nylon_ripstop_70d"                    # 92 gsm, the SWAP slab's frame face and floor (bone / brush wear)
R100 = "robic_100d_ripstop"
C330 = "cordura_330d_nylon66"
CAMO = "polyester_ht_630d_printable"

# ---------------------------------------------------------------- CORRIE B.2 baseline, same accounting
CORRIE_ROLLTOP_HW_G = W.ROLLTOP_HW_G         # 48.5 g, geometry.yaml (common item, not in CORRIE's body metric)
KEEPER_LOOPS_G = 8.6                         # geometry.yaml "6 haul-wrap keeper loops" (both designs keep them)
WRAPS_G = 84.1 + 24.0                        # geometry.yaml haul wraps W1-W3 webbing + G-hooks/ladders
FLY_SPINE_G = 52.6 + 15.8                    # geometry.yaml rain fly rows (fly + pocket; elastic, zip, tether)
FLY_SPINE_OUTER_M2 = CO.SPINE_OUTER_M2


def corrie_b2_system() -> dict:
    """CORRIE B.2's bag system by this file's definition (belt M; belt-independent items only)."""
    c = CO.make()
    b = CO.build(c, True, spec="B.2")
    body = BC.metrics(b)["mass_g"]["total"]
    bp = {d["id"]: d["mass_g"] for d in CO.bag_pockets(c, spec="B.2")}
    rows = {r[0][:4]: r[1] for r in CO.b2_rows(c, b, "B.2")}
    a2 = rows["A-2 "]
    g2 = rows["G-2 "]
    items = [
        ("body group (shell, collar, swells, accents, wings, pouch, door zip, wing/pouch hardware)", body),
        ("roll-top hardware (HDPE strip, 2 SR, webbing; common row)", CORRIE_ROLLTOP_HW_G),
        ("haul-wrap keeper loops", KEEPER_LOOPS_G),
        ("IMP-1 scope sleeve", bp["IMP-1"]), ("IMP-2 hydration sleeve", bp["IMP-2"]),
        ("IMP-4 door pocket", bp["IMP-4"]), ("IMP-8 cam cup", bp["IMP-8"]),
        ("haul wraps W1-W3 (compression), A-2 tails", WRAPS_G + a2),
        ("rain fly F-01 re-cut for the box shell (G-2)", FLY_SPINE_G + g2),
    ]
    return {"items": [(n, round(g, 1)) for n, g in items], "total_g": round(sum(g for _, g in items), 1),
            "excluded": "IMP-6 (shoulder strap), IMP-3 / IMP-5 (belt), fixed frame interface"}


# ---------------------------------------------------------------- the shell
DRAWCORD = {"channel_h": 40.0, "cord_m": 1.45}   # ASSUMPTION: channel strip height; cord = collar perimeter 1.27 m + tails
LID = {"L": 280.0, "W": 190.0, "H": 60.0}         # DECISION: CORRIE B.2 pouch box (2.7 L); covers the cinched mouth (~150 mm)
POD_PANEL = {"w": 200.0, "h": 450.0}             # same footprint as CORRIE's wing M-01 (same 4 loops)


def shell():
    """CORRIE rev B box shell + horseshoe door (B.2 seams), minus the wings and the roll-top hem / HDPE / hardware,
    plus a drawcord channel, 2 more attachment loops per side for the pods and the lid's front strap loops.
    The lid module replaces the CORRIE pouch (it is booked with the modules)."""
    c = CO.make()
    b = CO.build(c, True, spec="B.2")
    drop_ids = {"M-01", "SH-06", "B-07", "B-07s", "L-21", "L-22", "L-23", "SH-08"}
    b.pieces = [(p, g) for p, g in b.pieces if p.piece_id not in drop_ids]
    b.appliques = [p for p in b.appliques if p.piece_id not in drop_ids]
    b.seams = [s for s in b.seams if not s[0].name.startswith(("wing", "pouch", "boxing", "hem"))]
    b.zips = [z for z in b.zips if not z["name"].startswith("pouch")]
    b.extra["hardware"] = [h for h in b.extra["hardware"] if h[0].startswith("door")]
    b.extra["bartacks"] = 12 - 8 - 4               # door garages keep theirs; wing (8) and pouch (4) tacks go
    per = b.extra["collar_perimeter_mm"]
    ch = rect_panel("drawcord channel (folded, 100D)", per + 20, 2 * DRAWCORD["channel_h"], 0.0, seam_allowance_mm=SA,
                    material_id=R100, piece_id="D-07")
    b.pieces.append((ch, "collar"))
    b.seams.append(W.vseam("drawcord channel | collar top (ring)", per, 0.0, "ring"))
    W.add_hw(b, "drawcord: 3 mm Dyneema 1.45 m + spring cord lock + cord pull", DRAWCORD["cord_m"] * DYN3 + CORDLOCK
             + CORD_PULL_G, 0)
    # pod loops: CORRIE's 4 aft-corner wing-strap loops stay (their webbing was booked inside the wing strap rows),
    # plus 4 loops in the B-01 | gusset seams where the wing roots were: 8 x 25 mm x 80 mm, sewn in the seam (no tack)
    W.add_hw(b, "pod loops: 8 x 25 mm webbing 0.08 m in the B-01|gusset and aft-corner seams", 8 * 0.08 * WEB25, 0)
    # lid strap anchors: 2 rear loops on B-06f (frame-side collar) + 2 front loops in the aft corner seams at z 736
    W.add_hw(b, "lid anchors: 4 x 25 mm webbing 0.08 m (2 on B-06f, 2 at the collar seam aft corners)", 4 * 0.08 * WEB25, 4)
    # accent: the camo bar moves from the wings to the door garages' level as a 25 mm top band on the hinge band
    bar = BC._accent_rect("hinge-band top bar (camo)", 25, 2 * BC.A_MAX - 60, "SH-09")
    b.pieces.append((bar, "accent"))
    b.appliques.append(bar)
    return c, b


# ---------------------------------------------------------------- modules (roll-top boxes, straight seams only)
def _box_module(mid, name, W_, D_, H_, fab, face_fab=None, roll=120.0, closure="roll"):
    """A flat-sided box: one tube panel (perimeter x (H + roll), one side seam) + a boxed floor (4 straight seams,
    4 pivots). Optional heavier frame face: the tube's frame-face span and the floor cut from ``face_fab``.
    Returns the pieces, hardware and a seam/hour row."""
    per = 2 * (W_ + D_)
    pcs = []
    if face_fab:
        pcs.append(rect_panel(f"{name} tube (sides + aft)", per - W_, H_ + roll, 0.0, seam_allowance_mm=SA,
                              material_id=fab, piece_id=f"{mid}-a"))
        pcs.append(rect_panel(f"{name} frame face", W_, H_ + roll, 0.0, seam_allowance_mm=SA, material_id=face_fab,
                              piece_id=f"{mid}-b"))
        pcs.append(rect_panel(f"{name} floor", W_, D_, 0.0, seam_allowance_mm=SA, material_id=face_fab, piece_id=f"{mid}-c"))
        seams = [("tube side seams x2", 2 * (H_ + roll)), ("floor ring", per)]
    else:
        pcs.append(rect_panel(f"{name} tube", per, H_ + roll, 0.0, seam_allowance_mm=SA, material_id=fab, piece_id=f"{mid}-a"))
        pcs.append(rect_panel(f"{name} floor", W_, D_, 0.0, seam_allowance_mm=SA, material_id=fab, piece_id=f"{mid}-c"))
        seams = [("tube side seam", H_ + roll), ("floor ring", per)]
    hw = []
    if closure == "roll":
        hdpe = rect_panel(f"{name} roll stiffener (HDPE, x2 faces)", W_, 20.0, 0.0, seam_allowance_mm=0.0,
                          material_id="hdpe_sheet", quantity=2, piece_id=f"{mid}-s")
        pcs.append(hdpe)
        # DECISION (weight): no side-release buckle; the rolled HDPE edge folds once and a G-hook on a 0.15 m tail
        # hooks the module's own hang loop (quiet, gloved, one part)
        hw.append((f"{name}: roll keeper 25 mm 0.15 m + G-hook", 0.15 * WEB25 + G_HOOK))
        seams.append(("roll hem (folded, catches the HDPE)", per))
    hw.append((f"{name}: grab / hang loop 25 mm 0.12 m (colour-coded tab)", 0.12 * WEB25))
    vol = W_ * D_ * H_ / 1e6
    return {"id": mid, "name": name, "dims_mm": (W_, D_, H_), "vol_L": round(vol, 1), "pieces": pcs, "hw": hw,
            "seams": seams}


def modules() -> list:
    """The three shipped modules + the lid module. Dims DECISION (fit inside the rev B section: width 2a 340-394 mm,
    depth 170 floor -> 270 mm; IM1-IM3 run z 150-540 on B-01, bag_concepts STATIONS)."""
    swap = _box_module("MS", "SWAP slab (sleep kit / meat liner)", 330.0, 110.0, 560.0, SIL, face_fab=N70, roll=100.0)
    swap["role"] = ("frame zone under IM1-IM3. Camp: sleep bag + pad + puffy, the IM straps cinch it flat (internal "
                    "compression). Meat: emptied (the sleep kit moves aft), back in as the liner, boned meat in game "
                    "bags inside it, IM1-IM3 over it. Wipeable silpoly / 70D (record: blood rinses off)")
    camp = _box_module("MC", "CAMP module (clothing, food, stove)", 250.0, 160.0, 430.0, SIL, roll=100.0)
    camp["role"] = "aft zone, above the floor, behind the door: the day-to-day module"
    kill = _box_module("MK", "KILL module (knife, saw, game bags, first aid)", 260.0, 90.0, 280.0, SIL, roll=0.0,
                       closure="zip")
    kill["role"] = "rides in the door's lower half on 2 G-hook tabs; first thing out at the kill site"
    # kill module is a zip clamshell: #5 zip 3 sides of the face (L = 2 x 260 + 240 - corner allowance), 1 slider
    zl = 2 * 280.0 + 260.0 - 40.0
    kill["hw"].append(("KILL: #5 coil zip 0.78 m + slider + cord pull", zl / 1000 * ZIP5 + SLIDER5_G + CORD_PULL_G))
    kill["hw"].append(("KILL: 2 x 25 mm 0.10 m tabs + 2 G-hooks to the door loops", 2 * (0.10 * WEB25 + G_HOOK)))
    kill["zip_mm"] = zl
    kill["seams"].append(("zip set-in", zl))
    # lid module: CORRIE B.2 pouch construction (330D solid top, 100D base + boxing), larger footprint, lower box
    P = LID
    lid = {"id": "ML", "name": "LID module (snacks, gloves, headlamp, GPS)", "dims_mm": (P["L"], P["W"], P["H"]),
           "vol_L": round(P["L"] * P["W"] * P["H"] * 0.85 / 1e6, 2),
           "pieces": [rect_panel("lid top (body solid)", P["L"], P["W"], 0.0, seam_allowance_mm=SA, material_id=C330,
                                 piece_id="ML-a"),
                      rect_panel("lid base", P["L"], P["W"], 0.0, seam_allowance_mm=SA, material_id=R100, piece_id="ML-b"),
                      rect_panel("lid boxing strip", 2 * (P["L"] + P["W"]), P["H"], 0.0, seam_allowance_mm=SA,
                                 material_id=R100, piece_id="ML-c"),
                      rect_panel("lid pull tab (camo, folded)", 25.0, 120.0, 0.0, seam_allowance_mm=SA, material_id=CAMO,
                                 piece_id="ML-d")],
           "hw": [("LID: #8 zip on the aft long edge + slider + pull", ZIP8 * (P["L"] - 20 + 60) / 1000 + SLIDER8_G
                   + CORD_PULL_G),
                  ("LID: 2 rear straps 0.12 m + G-hooks, 2 front straps 0.35 m + ladder locks + G-hooks (cinch the "
                   "collar = top compression)", 2 * (0.12 * WEB25 + G_HOOK) + 2 * (0.30 * WEB25 + LADDER + G_HOOK))],
           "seams": [("lid top | boxing (ring)", 2 * (P["L"] + P["W"])), ("lid base | boxing (ring)", 2 * (P["L"] + P["W"]))],
           "zip_mm": P["L"] - 20, "role": "on the cinched collar; replaces CORRIE's top pouch AND the roll-top's job "
                                          "of closing the top (fly covers it in rain)"}
    return [swap, camp, kill, lid]


def pods() -> list:
    """Hook-on side pods: same 200 x 450 footprint and the same 4 loops a side as CORRIE's wings, so the pods ARE the
    wings when wanted and stay home when not."""
    out = []
    # optics pod (left): no back panel. The IMP-1 sleeve (B.2: 100D face, 3 mm XLPE) becomes a stand-alone tube whose
    # back is the left gusset (330D, the bag's own wear face); 4 fixed tabs hook it to the 4 loops a side
    s = CO.SCOPE_SLEEVE
    pcs = [rect_panel("optics pod face", s["w"], s["h"], 0.0, seam_allowance_mm=SA, material_id=R100, piece_id="PO-b"),
           rect_panel("optics pod back (gusset side, 100D)", 200.0, s["h"], 0.0, seam_allowance_mm=SA, material_id=R100,
                      piece_id="PO-a"),
           rect_panel("optics pod camo edge bar", 25, s["h"], 0.0, seam_allowance_mm=SA, material_id=CAMO,
                      piece_id="PO-c")]
    foam_g = 0.300 * 0.420 * 0.003 * XLPE_RHO * 1000
    hw = [("XLPE 3 mm liner 300 x 420", foam_g),
          ("2 fixed frame-edge tabs 25 mm 0.06 m + G-hook", 2 * (0.06 * WEB25 + G_HOOK)),
          ("2 aft cinch straps 25 mm 0.40 m + G-hook + ladder lock (hold pad / poles over the pod)",
           2 * (0.40 * WEB25 + G_HOOK + LADDER)),
          ("top shock cord 0.5 m + cord lock", 0.5 * SHOCK + CORDLOCK)]
    out.append({"id": "PO", "name": "optics pod (left)", "pieces": pcs, "hw": hw,
                "seams": [("tube side seams x2 + floor + hem", 2 * 430 + 200 + 530)], "vol_L": 5.0,
                "role": "85 mm spotter in a padded tube; 4 G-hooks on, 4 off; its 2 aft straps also hold a sit pad / poles"})
    # tripod kit (right): no panel. A foot cup caught on 2 loops + 2 cinch straps across the gusset; the tripod,
    # poles or rain jacket lie on the gusset itself (330D, the bag's wear face)
    pcs = [rect_panel("tripod foot cup (folded, 330D)", 130, 160, 0.0, seam_allowance_mm=SA, material_id=C330,
                      piece_id="PT-b"),
           rect_panel("tripod strap camo sleeve", 25, 120, 0.0, seam_allowance_mm=SA, material_id=CAMO, piece_id="PT-c")]
    hw = [("cup: 2 tabs 25 mm 0.06 m + G-hooks", 2 * (0.06 * WEB25 + G_HOOK)),
          ("2 cinch straps 25 mm 0.40 m + G-hook + ladder lock", 2 * (0.40 * WEB25 + G_HOOK + LADDER))]
    out.append({"id": "PT", "name": "tripod kit (right)", "pieces": pcs, "hw": hw,
                "seams": [("cup sides + hem", 2 * 160 + 130)], "vol_L": 6.0,
                "role": "tripod + head, poles, rain jacket on the right gusset under 2 straps; foot in the cup"})
    return out


STRAP_POCKET_R = {"w": 120.0, "h": 200.0, "gusset": 40.0}   # DECISION: interior ~180 x 105 x 40 takes the snack stack


def strap_pocket_r() -> dict:
    """SNACK pocket on the right J-strap (mirror of CORRIE's IMP-6, gusseted): fixes the S-L snacks miss. Harness-
    mounted, but it is this entry's addition, so it is booked in bag_system_g (honest)."""
    P = STRAP_POCKET_R
    pcs = [rect_panel("snack pocket mesh face", P["w"], P["h"], 0.0, seam_allowance_mm=SA,
                      material_id="power_mesh_nylon_spandex", piece_id="SP-a"),
           rect_panel("snack pocket gusset (330D)", 2 * P["h"] + P["w"], P["gusset"], 0.0, seam_allowance_mm=SA,
                      material_id=C330, piece_id="SP-b"),
           rect_panel("snack pocket back (330D)", P["w"], P["h"], 0.0, seam_allowance_mm=SA, material_id=C330,
                      piece_id="SP-c")]
    hw = [("top shock cord 0.25 m + cord lock", 0.25 * SHOCK + CORDLOCK)]
    return {"id": "SP", "name": "snack pocket, right shoulder strap", "pieces": pcs, "hw": hw,
            "seams": [("gusset | face", 2 * P["h"] + P["w"]), ("gusset | back", 2 * P["h"] + P["w"]),
                      ("strap bartack lines", 2 * P["h"])], "vol_L": round(0.18 * 0.105 * 0.04 * 1000, 2),
            "role": "snacks (150 x 100 x 35) reachable pack-on on every belt size"}


def part_mass(d) -> float:
    return sum(BC.piece_mass_g(p) for p in d["pieces"]) + sum(g for _, g in d["hw"])


H = BC.HOURS


def part_hours(d) -> float:
    n_cut = sum(p.quantity for p in d["pieces"])
    L = sum(L_ for _, L_ in d["seams"]) / 1000
    h = n_cut * H["cut_piece"] + L * H["straight_m"] + len(d["hw"]) * H["bartack"]
    if d.get("zip_mm"):
        h += H["zip_fixed"] + d["zip_mm"] / 1000 * H["zip_m"]
    if any("floor ring" in n for n, _ in d["seams"]):
        h += 4 * H["pivot"]
    return h


# ---------------------------------------------------------------- the system
def system() -> dict:
    c, b = shell()
    m = BC.metrics(b)
    mods = modules()
    pds = pods() + [strap_pocket_r()]
    c2 = corrie_b2_system()
    bp = {d["id"]: d["mass_g"] for d in CO.bag_pockets(c, spec="B.2")}
    rows = [("shell (CORRIE rev B body + door, no wings, drawcord collar, pod / lid loops)", m["mass_g"]["total"]),
            ("haul-wrap keeper loops", KEEPER_LOOPS_G),
            ("IMP-2 hydration sleeve (kept, hung on B-06f)", bp["IMP-2"]), ("IMP-8 cam cup (kept)", bp["IMP-8"])]
    rows += [(f"{d['id']} {d['name']}", part_mass(d)) for d in mods]
    rows += [(f"{d['id']} {d['name']}", part_mass(d)) for d in pds]
    rows += [("haul wraps W1-W3 (compression), A-2 tails", c2["items"][7][1]),
             ("rain fly F-01 (same box shell as CORRIE B.2)", c2["items"][8][1])]
    total = sum(g for _, g in rows)
    hours = m["hours_total"] + sum(part_hours(d) for d in mods + pds) + 1.7 + 0.8   # IMP-2 1.7 h, IMP-8 0.8 h (corrie_body 11.1)
    pieces = m["cut_pieces"] + sum(p.quantity for d in mods + pds for p in d["pieces"])
    zip_mm = m["zip_length_m"] * 1000 + sum(d.get("zip_mm", 0.0) for d in mods)
    v = BC.volumes(c)
    return {"shell_metrics": {k: m[k] for k in ("cut_pieces", "curved_seams", "zip_length_m", "hours_total", "mass_g")},
            "rows": [(n, round(g, 1)) for n, g in rows], "bag_system_g": round(total, 1),
            "corrie_b2": c2, "delta_vs_corrie_g": round(total - c2["total_g"], 1),
            "modules": [{k: d[k] for k in ("id", "name", "dims_mm", "vol_L", "role")} | {"mass_g": round(part_mass(d), 1),
                        "hours": round(part_hours(d), 2)} for d in mods],
            "pods": [{k: d[k] for k in ("id", "name", "vol_L", "role")} | {"mass_g": round(part_mass(d), 1),
                     "hours": round(part_hours(d), 2)} for d in pds],
            "pieces": int(pieces), "curved_seams": int(m["curved_seams"]), "zip_mm_total": round(zip_mm, 0),
            "beginner_hours": round(hours, 1), "volume": v,
            "fill_height_in": v["fill_height_in"]}


def strip_down() -> dict:
    """What the hunter can leave home (mass of each removable part), and the minimum carried set."""
    s = system()
    removable = {d["id"]: d["mass_g"] for d in s["modules"] + s["pods"]}
    return {"removable_g": removable, "day_hunt_min_g": round(s["bag_system_g"] - removable["MS"] - removable["MC"]
                                                              - removable["PO"], 1)}


H1_PACK_G = 3943.0     # RULES.md: CORRIE B.2 at belt M on the H1 frame (frame_comp_verdict.md)


def pack_mass_M(s=None) -> float:
    s = s or system()
    return round(H1_PACK_G - s["corrie_b2"]["total_g"] + s["bag_system_g"], 1)


if __name__ == "__main__":
    s = system()
    for n, g in s["rows"]:
        print(f"{g:8.1f}  {n}")
    print("CACHE bag system", s["bag_system_g"], "g; CORRIE B.2 same metric", s["corrie_b2"]["total_g"], "g; delta",
          s["delta_vs_corrie_g"], "; pack M on H1", pack_mass_M(s))
    print(json.dumps({k: s[k] for k in ("modules", "pods", "pieces", "curved_seams", "zip_mm_total", "beginner_hours",
                                        "fill_height_in")}, indent=1, default=float))
    print(strip_down())
    print(s["corrie_b2"])
