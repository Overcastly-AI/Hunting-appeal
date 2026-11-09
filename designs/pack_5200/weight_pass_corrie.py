"""CORRIE B.1 whole-pack weight pass (pack-designer, 2026-11-09). The pass itself is computed on CORRIE B.1
(``corrie.weight_table(size, spec="B.1")``): every cut is defined against B.1. The owner said "Yes" (DECISIONS
2026-11-09): package A and package B without the held B-8 / B-9 are now CORRIE B.2, the default in concepts/corrie.py
(``corrie.SPECS``). The "after A+B" bar and the per-size table come from ``corrie.weight_table(size, spec="B.2")``;
package C is projected on top of that table (not applied: structural / test gates pending).

    python designs/pack_5200/weight_pass_corrie.py

Every gram comes from the existing weight tables, never typed in as a total:
  * corrie.weight_table(size, spec="B.1")      -> the 4000.4 g (belt M) CORRIE B.1 total this pass starts from;
  * corrie.weight_table(size, spec="B.2")      -> the applied A+B table (section 4a);
  * geometry.yaml weight.rows                  -> the shared frame / harness / attachment / meat-haul rows;
  * panels.yaml                                -> the released bill of panels (B-11, B-12, HP-01/02 ...);
  * corrie.build(), bag_pockets(), hip_layout(), holster(), belt_b(), pad_seat() -> the CORRIE-specific parts;
  * hipbelt_concepts.belt_bom, analysis/hipbelt_structural_results.json, back_rail_results.json,
    frame_mass_production.json, mass_cut_results.json -> parts and the frame / belt / rail candidates;
  * data/materials/ records (gsm, density, g/m, cost) and, for records that do not exist yet, bag_weight_plan.MISSING
    (flagged ASSUMPTION there).
The part-level breakdown is checked against weight_table(): the only balancing row is the booking reconciliation
between SPINE's design-panel rows and the cut-set body metric that weight_table subtracts (a few grams, reported).

Writes designs/pack_5200/analysis/weight_pass_corrie.md + weight_pass_corrie.json and
outputs/screens/20261109_weight_1.png (group Pareto vs benchmarks), _2.png (part Pareto), _3.png (waterfall).
"""
from __future__ import annotations

import functools
import json
import math
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (ROOT, HERE, HERE / "concepts"):
    sys.path.insert(0, str(p))

import bag_concepts as BC  # noqa: E402
import bag_weight_plan as BWP  # noqa: E402  (usd_m2, MISSING records)
import corrie as C  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import rect_panel  # noqa: E402

ANALYSIS = HERE / "analysis"
SCREENS = ROOT / "outputs" / "screens"
DATE = "20261109"
LB = 453.592
OZ = 28.3495
SIZE = "M"
BASE = "B.1"            # the spec every cut is defined against
APPLIED = "B.2"         # the spec that carries the owner-approved A + B (DECISIONS 2026-11-09)

GEO = yaml.safe_load((HERE / "geometry.yaml").read_text())
PANELS = {r["id"]: r for r in yaml.safe_load((HERE / "panels.yaml").read_text())["panels"]}


def _json(name):
    return json.loads((ANALYSIS / name).read_text())


def rec(mid, key):
    return float(MAT.load(mid).require(key))


WEB25 = rec("poly_webbing_25mm", "mass_g_m")
WEB25_USD = float(MAT.load("poly_webbing_25mm").cost_usd["value"])       # per m
G_HOOK_USD = 1.5        # ASSUMPTION (no G-hook record; HAUL family aluminium hook, distributor class)
BINDING_GM = 5.0        # ASSUMPTION, build_simplicity.md S-03 (grosgrain 20 mm, no record)
BINDING_USD_M = 0.50    # ASSUMPTION, build_simplicity.md S-03
S03_H_PER_M = 2.0 / 3.96   # build_simplicity.md S-03: -2.0 h for 3.96 m of body binding (beginner model)


# =====================================================================================================================
# 1. Mass breakdown: geometry.yaml rows (shared parts) + the CORRIE B.1 parts, reconciled to corrie.weight_table()
# =====================================================================================================================
GROUP_OF = {   # geometry.yaml weight group -> group used in this pass
    "frame (printed branch body + carbon crown)": "Frame (printed body + carbon crown)",
    "torso adjust (not in the frame line)": "Torso adjust",
    "back-system spreader (Sandwich v2, BP-06)": "Back system (spreader + back panel)",
    "back panel": "Back system (spreader + back panel)",
    "harness": "Harness (J-straps, yoke, lifters, sternum)",
    "hipbelt (M)": "Hipbelt B (body, load path, pad seat, pockets, holster)",
    "main bag": "Bag body (CORRIE shell, collar, wings, door, roll-top)",
    "accents": "Hipbelt B (body, load path, pad seat, pockets, holster)",   # only SH-05 (belt wing tips) survives
    "bag-side load spreaders": "Bag-to-frame attachment",
    "bag-to-frame attachment (fairleads)": "Bag-to-frame attachment",
    "bag-to-frame attachment system": "Bag-to-frame attachment",
    "under-straps US1/US2 (cradle)": "Meat haul + compression",
    "float-mode stand-off links B-24": "Meat haul + compression",
    "internal meat harness": "Meat haul + compression",
    "haul wraps (= compression)": "Meat haul + compression",
    "rain fly": "Rain fly (fly + base pocket)",
    "misc": "Thread + labels",
}
G_POUCH = "Top pouch (4.0 L)"
G_POCK = "Bag pockets (IMP-1, -2, -4, -6, -8)"
G_REC = "Booking reconciliation"


def _rolltop_split():
    """The SPINE roll-top row books the HDPE strip and the ROLL hardware together; CORRIE's body books its own
    B-07s strip, so only the hardware part of that row is kept (same formula as build_geometry.weight_budget)."""
    hw = 2 * rec("buckle_side_release_25mm", "mass_g") + 0.7 * WEB25
    return round(hw, 1)


def breakdown(size: str = SIZE) -> dict:
    wt = C.weight_table(size, spec=BASE)
    c = C.make()
    b = C.build(c, True, spec=BASE)
    parts = []

    def add(group, part, g, src, zone=""):
        parts.append({"group": group, "part": part, "g": round(float(g), 2), "source": src, "zone": zone})

    # ---- shared rows kept from geometry.yaml (released SPINE pack, belt M)
    hp_fab = PANELS["HP-01"]["mass_g_total"] + PANELS["HP-02"]["mass_g_total"]
    for r in GEO["weight"]["rows"]:
        grp, item, g = r["group"], r["item"], float(r["mass_g"])
        if grp == "main bag" and item.startswith("fabric panels"):
            add(GROUP_OF[grp], "B-11 lash tabs (Hypalon, bow riser + muzzle keepers), released", PANELS["B-11"]["mass_g_total"],
                "panels.yaml B-11 (the rest of this row is the SPINE body, replaced by CORRIE's)")
            continue
        if grp == "main bag" and "diagonal zip" in item:
            continue                                   # SPINE body, replaced (CORRIE has the door zip)
        if grp == "main bag" and item.startswith("roll-top"):
            add(GROUP_OF[grp], "roll-top ROLL hardware: 2 x 25 mm side-release + 2 x 0.35 m webbing", _rolltop_split(),
                "geometry.yaml roll-top row minus its HDPE strip (CORRIE books B-07s in the body)")
            continue
        if grp == "accents":
            add(GROUP_OF[grp], "SH-05 hipbelt wing-tip camo shards", PANELS["SH-05"]["mass_g_total"],
                "panels.yaml SH-05 (SH-01..04 are SPINE body accents, replaced)")
            continue
        if grp == "pockets":
            continue                                   # SPINE floating side pockets: CORRIE has wings
        if grp == "hipbelt (M)":
            if item.startswith("wings"):
                add(GROUP_OF[grp], "rifle tabs and belt trims not in belt_bom (released row - C0 body - HP-01/02)",
                    g - C.BELT_C0_BODY_G - hp_fab, "geometry.yaml hipbelt row - hipbelt_results C0 165.0 - panels HP-01/02")
            elif item.startswith("50 mm"):
                add(GROUP_OF[grp], "50 mm belt webbing 0.9 m + 50 mm buckle + stabilizer straps + 2 ladder locks",
                    g - 0.4 * rec("coil_zipper_8", "mass_g_m"), "geometry.yaml row minus the 0.4 m #8 zip (now in IMP-5)")
            continue                                   # the 45 g PA66 plate is replaced by the load-path parts below
        if grp.startswith("frame"):
            fm = _json("frame_mass_production.json")
            assert abs(fm["printed_body_g"] + fm["non_body_g"] + fm["crown_fix_g"] - g) < 0.2
            add(GROUP_OF[grp], "frame: PAHT-CF printed branch body (production raster)", fm["printed_body_g"],
                "analysis/frame_mass_production.json printed_body_g")
            add(GROUP_OF[grp], "frame: carbon crown as built, rack + pawl + guides, bushings, Ti hip-pivot mount, inserts",
                fm["non_body_g"], "analysis/frame_mass_production.json non_body_g")
            add(GROUP_OF[grp], "frame: rev C crown inner plies (fix)", fm["crown_fix_g"],
                "analysis/frame_mass_production.json crown_fix_g")
            continue
        short = grp.split(" (")[0].replace("bag-to-frame attachment", "attachment")
        add(GROUP_OF[grp], f"{short}: {item}", g, r["basis"] if isinstance(r["basis"], str) else "geometry.yaml")

    # ---- CORRIE body (corrie.build(), rev B): pieces, zips, hardware
    BODY = GROUP_OF["main bag"]
    for p, grp in b.pieces:
        g = BC.piece_mass_g(p)
        tgt = G_POUCH if grp == "pouch" else BODY
        add(tgt, f"{p.piece_id} {p.name} ({p.material_id}{', x' + str(p.quantity) if p.quantity > 1 else ''})", g,
            "corrie.build() piece: cut area x record gsm", zone=grp)
    for z in b.zips:
        add(G_POUCH if "pouch" in z["name"] else BODY, z["name"], BC.zip_mass_g(z), "corrie.build() zip (records + slider ASSUMPTION)")
    for n, g in b.extra["hardware"]:
        add(G_POUCH if n.startswith("pouch") else BODY, n, g, "corrie.build() hardware (records / G-hook ASSUMPTION)")

    # ---- B.1 bag pockets
    for d in C.bag_pockets(c, spec=BASE):
        add(G_POCK, f"{d['id']} {d['name']}", d["mass_g"], "corrie.bag_pockets()")

    # ---- hipbelt B (belt_b body per piece + corrections), IMP-5, IMP-3, load path, pad seat
    HC, _ = C._hb()
    bom = HC.belt_bom(HC.B, size)
    HB = GROUP_OF["hipbelt (M)"]
    for r in bom["pieces"]:
        add(HB, f"belt B {r['piece']} ({r['material']}, x{r['qty']})", r["mass_g"], "hipbelt_concepts.belt_bom")
    for r in bom["hardware_delta"]:
        add(HB, f"belt B {r['item']}", r["mass_g"], "hipbelt_concepts.belt_bom hardware_delta")
    for n, g in C.belt_b(size, spec=BASE)["corrections"]:
        add(HB, f"belt B correction: {n}", g, "corrie.belt_b() (2026-11-09 records)")
    hl = C.hip_layout(size)
    for side in ("L", "R"):
        if hl[side]:
            add(HB, f"IMP-5{side} hipbelt pocket ({size})", hl[side]["mass_g"], "corrie.hip_layout()")
    add(HB, "IMP-3 1 L bottle holster", C.holster()["mass_g"], "corrie.holster()")
    sm = _json("hipbelt_structural_results.json")["mass"]
    cp = sm["cp_breakdown"]
    for n, g in [("6061-T6 1.5 mm bow-tie centre plate", cp["plate_g"]), ("PA66 hub bushing", cp["hub_g"]),
                 ("pivot latch", cp["latch_g"]), ("1000D root doublers (stitched ear)", sm["root_doublers_1000d_g"]),
                 ("1000D tip doublers", sm["tip_doublers_1000d_g"]), ("ear saddle-stitch thread", sm["ear_thread_g"]),
                 ("POM thrust washer", sm["thrust_washer_pom_g"])]:
        add(HB, f"belt B load path: {n}", g, "analysis/hipbelt_structural_results.json mass")
    for n, g in C.pad_seat()["rows"]:
        add(HB, f"lumbar pad seat: {n}", g, "corrie.pad_seat()")

    tot = sum(p["g"] for p in parts)
    recon = wt["total_g"] - tot
    add(G_REC, "SPINE body as booked in geometry.yaml (design panels, zip, SH-01..04, roll-top HDPE) vs the cut-set "
        "body metric (333.2 g) that corrie.weight_table() subtracts", recon, "balance to corrie.weight_table()")
    groups = {}
    for p in parts:
        groups[p["group"]] = groups.get(p["group"], 0.0) + p["g"]
    groups = dict(sorted(((k, round(v, 1)) for k, v in groups.items()), key=lambda kv: -kv[1]))
    return {"size": size, "total_g": wt["total_g"], "weight_table": wt, "parts": parts, "groups": groups,
            "reconciliation_g": round(recon, 1), "body": b, "concept": c}


# =====================================================================================================================
# 2. Booking gaps: real mass that no table books (so the real pack is heavier than 4000 g)
# =====================================================================================================================
def _area(build, ids):
    return sum(p.area_mm2 * p.quantity for p, _ in build.pieces if p.piece_id in ids) / 1e6


@functools.lru_cache(maxsize=1)
def _spine_outer_area() -> float:
    """Outer shell (aft face B-02a..d, gores B-03, bottom B-05) of the released v3.1 cut set (~30 s to build)."""
    import patterns_v31 as P31
    return _area(BC.spine_build(P31.build()), ["B-02a", "B-02b", "B-02c", "B-02d", "B-03", "B-05"])


def booking_gaps(bd: dict) -> list:
    b, c = bd["body"], bd["concept"]
    m = BC.metrics(b)
    bound_m = sum(r["length_mm"] for r in m["seam_rows"] if "bound" in r["tags"]) / 1000
    a_sp = _spine_outer_area()
    a_co = _area(b, ["B-03", "B-02u", "B-02door", "B-02h", "B-05"])
    fly = sum(PANELS[k]["mass_g_total"] for k in PANELS if k.startswith("F-01"))
    return [
        {"id": "G-1", "what": f"grosgrain binding on CORRIE's {bound_m:.2f} m of bound body seams (never booked: SPINE's "
                              "3.96 m was not booked either)", "g": round(bound_m * BINDING_GM, 1),
         "basis": f"corrie.build() seam rows tagged 'bound' x {BINDING_GM} g/m (ASSUMPTION, build_simplicity S-03)",
         "bound_m": round(bound_m, 2)},
        {"id": "G-2", "what": f"rain fly re-cut for CORRIE's box shell (outer shell {a_co:.3f} m2 vs SPINE {a_sp:.3f} m2); "
                              "the table still carries SPINE's fly", "g": round(fly * (a_co / a_sp - 1), 1),
         "basis": "panels.yaml F-01 x outer-shell area ratio (ASSUMPTION: fly area scales with the shell it covers; "
                  "wing cover not included)"},
    ]


# =====================================================================================================================
# 3. Candidate cuts
# =====================================================================================================================
def _piece(b, pid):
    return next(p for p, _ in b.pieces if p.piece_id == pid)


def _swap(pieces, new_mid):
    """(grams saved, $ delta) for re-making ``pieces`` in ``new_mid`` (cut area unchanged)."""
    g = usd = 0.0
    for p in pieces:
        a = p.area_mm2 * p.quantity / 1e6
        old = BWP.gsm(p.material_id)
        new = BWP.gsm(new_mid)
        g += a * (old - new)
        u_new = BWP.MISSING[new_mid]["usd_m2"] if new_mid in BWP.MISSING else BWP.usd_m2(new_mid)
        usd += a * (u_new - BWP.usd_m2(p.material_id))
    return round(g, 1), round(usd, 2)


def pouch_mass(L=None, W=None, H=None, top="polyester_ht_630d_printable", body="cordura_330d_nylon66") -> dict:
    """The top pouch exactly as corrie.build() books it, with size and fabrics as parameters."""
    P = C.SPECS[BASE]["pouch"]
    L, W, H = L or P["L"], W or P["W"], H or P["H"]
    sa = BC.SA_FLAT
    pcs = [rect_panel("top", L, W, 0.0, seam_allowance_mm=sa, material_id=top),
           rect_panel("base", L, W, 0.0, seam_allowance_mm=sa, material_id=body),
           rect_panel("box", 2 * (L + W), H, 0.0, seam_allowance_mm=sa, material_id=body)]
    fab = sum(p.area_mm2 / 1e6 * BWP.gsm(p.material_id) for p in pcs)
    usd = sum(p.area_mm2 / 1e6 * BWP.usd_m2(p.material_id) for p in pcs)
    zip_l = 300.0 * L / P["L"]
    zp = C.ZIP8_GM * (zip_l + 60) / 1000 + C.SLIDER8_G
    hw = 4 * (0.12 * WEB25 + C.G_HOOK) + C.CORD_PULL_G
    return {"g": round(fab + zp + hw, 1), "fabric_usd": usd, "volume_L": round(L * W * H * 0.85 / 1e6, 2)}


def cuts(bd: dict) -> list:
    b, c = bd["body"], bd["concept"]
    bp = {d["id"]: d for d in C.bag_pockets(c, spec=BASE)}
    out = []

    def cut(id_, pkg, zone, change, g, usd, hours, dur, quiet, ip, load, conf, rec, g_booked=None, look="none",
            status="proposal"):
        out.append({"id": id_, "pkg": pkg, "zone": zone, "change": change, "g": round(g, 1),
                    "g_booked": round(g if g_booked is None else g_booked, 1), "usd": round(usd, 2),
                    "hours": round(hours, 2), "durability": dur, "quiet": quiet, "ip": ip, "look": look,
                    "load_path": load, "confidence": conf, "rec": rec, "status": status})

    # ---------------- A: no load path, durability or look impact
    grip = next(g for n, g in C.belt_b(SIZE, spec=BASE)["corrections"] if n.startswith("grip")) + 5.0
    cut("A-1", "A", "hipbelt B", "Ship belt B with an unprinted face until test HB-2 passes (DECISIONS 2026-11-09: grip "
        "face only after HB-2, not counted before). If HB-2 passes and the owner adopts it, the grams come back.", grip,
        -3.0, 0.0, "none", "none", "none", "no: friction is not credited before HB-2 (belt-B structural uses no grip)",
        "high", "YES")
    tails = 3 * 0.10
    cut("A-2", "A", "haul wraps W1-W3", "Wrap tail allowance 250 -> 150 mm (cut length = haul path + 150). The haul "
        "path, which sets the meat-mode girth, is unchanged.", tails * WEB25, -tails * WEB25_USD, 0.0,
        "none (tail only)", "none", "none", "touches the wrap, not its capacity: strap and box-X unchanged; ladder-lock "
        "needs a gloved tail, 150 mm is still a full hand (ASSUMPTION)", "medium", "YES")

    # ---------------- B: owner OK needed (look, feature detail or durability trade; no load path)
    g_m = booking_gaps(bd)[0]["bound_m"]
    cut("B-1", "B", "bag body seams", f"S-03 on CORRIE: drop grosgrain on the {g_m:.2f} m of bound body seams; second "
        "301 row 6 mm into the allowance, trim, hot-knife sear. Gate: 3-cycle wash swatch (R-12), no fray past row 2.",
        g_m * BINDING_GM, -g_m * BINDING_USD_M, -g_m * S03_H_PER_M,
        "ULTRA 200 laminate edge may fray; rougher inside where game bags rub", "none", "none",
        "no: no seam capacity counts the binding; HE/B-18 seam governed by the B-05 strip (SF 2.31, unchanged)",
        "medium", "YES (pending the wash swatch)", g_booked=0.0)
    sh03 = _piece(b, "SH-03")
    perim = sum(sh03.edge_length(n) for n in sh03.edge_names) / 1000
    cut("B-2", "B", "camo accent", "Delete the SH-03 camo band on the roll-top hem (hem stays body solid). Camo stays on "
        "the kick plates, wing bars, door garages and pouch top.", BC.piece_mass_g(sh03),
        -sh03.area_mm2 / 1e6 * BWP.usd_m2(sh03.material_id), -(BC.HOURS["cut_piece"] + perim * BC.HOURS["applique_m"]),
        "none (overlay only, no wear zone)", "none", "none", "no", "high", "YES", look="less camo at the top of the bag")
    base = pouch_mass()
    p100 = pouch_mass(body="robic_100d_ripstop")
    cut("B-3", "B", "top pouch", "Pouch base + boxing strip 330D Cordura -> 100D Robic (already in the BOM: collar, "
        "IMP-2, IMP-4). Top stays camo 630D.", base["g"] - p100["g"], p100["fabric_usd"] - base["fabric_usd"], 0.0,
        "tear 90/80 -> 45/40 N warp/weft (records); the pouch rides on the roll and comes off, but gets set on rock", "same (3)", "none",
        "no", "high", "YES")
    p330 = pouch_mass(top="cordura_330d_nylon66")
    cut("B-4", "B", "top pouch", "Pouch top camo 630D -> body-solid 330D; a camo pull tab marks it.",
        base["g"] - p330["g"], p330["fabric_usd"] - base["fabric_usd"], 0.0, "lower abrasion on the top face "
        "(Taber 1000 -> 800)", "same", "none", "no", "high", "owner (look)", look="the pouch top loses its camo panel")
    ps = pouch_mass(L=280.0, W=190.0, H=60.0)
    cut("B-5", "B", "top pouch", f"Pouch 320 x 210 x 70 -> 280 x 190 x 60 mm ({base['volume_L']} -> {ps['volume_L']} L). "
        "Loadout check: the snacks / GPS that miss on S-L ride in it, so it must still take 150 x 100 x 35 + a 160 mm GPS.",
        base["g"] - ps["g"], ps["fabric_usd"] - base["fabric_usd"], -0.1, "none", "none", "none", "no", "high",
        "owner (DECISIONS 2026-11-09 set 4 L)", look="smaller pouch")
    i1 = bp["IMP-1"]["pieces"][0]
    g, usd = _swap([i1], "robic_100d_ripstop")
    cut("B-6", "B", "IMP-1 scope sleeve", "Sleeve panel IMP1-a 330D -> 100D Robic (XLPE + facing kept). The panel sits "
        "under the wing, facing it, not the brush.", g, usd, 0.0, "tear 90/80 -> 45/40 N (records) on a panel the scope "
        "slides against", "same", "none", "no", "medium", "YES")
    i6 = 0.30 * WEB25 + 2 * C.G_HOOK
    cut("B-7", "B", "IMP-6 phone pocket", "Sew the phone pocket to the LEFT J-strap (bartacked through the strap binding) "
        "instead of 2 wrap straps + 2 G-hooks. Loses moving it to the right strap and taking it off.", i6,
        -(0.30 * WEB25_USD + 2 * G_HOOK_USD), -(4 * BC.HOURS["bartack"]) + 0.2, "none", "one less clinking hook pair",
        "none", "no (the strap carries it, ~0.3 kg)", "high", "owner (feature detail)")
    o4 = [_piece(b, k) for k in ("B-03", "B-02u", "B-02door", "B-02h", "M-01")]
    g, usd = _swap(o4, "ultragrid_210d_uhmwpe_ripstop")
    cut("B-8", "B", "body fabric (O-4 on CORRIE)", "Gussets, U-surround, door, hinge band, wings 330D -> 210D UHMWPE grid "
        "(O-4). Still ON HOLD: the record has no abrasion value, and the owner has not seen a swatch.", g, usd, 0.0,
        "tear 90/80 -> 180/160 N (records, better); abrasion unknown (no record value)", "same (3)", "none",
        "the wing roots and corner seams hold the wing-strap loops: tear goes up, so no SF falls; no seam check on file "
        "for the grid", "low (abrasion missing)", "hold: evidence still missing", look="visible grid on the solid colour",
        status="held O-4")
    g, usd = _swap([_piece(b, "B-06")], "nylon_ripstop_70d")
    cut("B-9", "B", "roll-top collar (O-3)", "Collar B-06 100D Robic -> 70D ripstop (O-3). Still ON HOLD: no 70D "
        "record (bag_weight_plan.MISSING, ASSUMPTION 70 gsm).", g, usd, 0.0, "tear 43 -> 35 N (ASSUMPTION)", "same",
        "none", "no (collar carries the roll, not the frame load)", "low (no record)", "hold: record missing",
        status="held O-3")
    hyp = [("B-12 strap ports x6", PANELS["B-12"]["cut_area_m2_each"] * PANELS["B-12"]["qty_total"]),
           ("IMP-2 hose-port frames x2", sum(p.area_mm2 * p.quantity for p in bp["IMP-2"]["pieces"]
                                            if p.material_id == "hypalon_coated_nylon") / 1e6),
           ("IMP-8 cam-cup base", sum(p.area_mm2 * p.quantity for p in bp["IMP-8"]["pieces"]
                                      if p.material_id == "hypalon_coated_nylon") / 1e6)]
    a_h = sum(a for _, a in hyp)
    d_gsm = rec("hypalon_coated_nylon", "areal_density_gsm") - rec("tpu_coated_nylon_840d", "areal_density_gsm")
    cut("B-10", "B", "trims", "Hypalon -> laser-cut TPU-coated 840D on the trims that carry no load: " +
        ", ".join(n for n, _ in hyp) + ". One sheet material with O-15 if that is taken.", a_h * d_gsm,
        a_h * (BWP.usd_m2("tpu_coated_nylon_840d") - BWP.usd_m2("hypalon_coated_nylon")), 0.0,
        "Taber 5000 -> 4000 (records)", "WORSE: quietness 4 -> 2 (records), stiff edge can tick on webbing", "none",
        "no: B-12 ports carry no load (build_simplicity S-02 note); hose ports and cam base are trims", "high",
        "owner (quiet trade, small grams)")

    # ---------------- C: load path; needs the structural-fea-engineer and / or a test
    hs = _json("hipbelt_structural_results.json")
    cpm = hs["mass"]["cp_breakdown"]
    g7075 = cpm["plate_g"] * (1 - (1.2 / 1.5) * rec("alu_7075_t6", "density_kg_m3") / rec("alu_6061_t6", "density_kg_m3"))
    cut("C-1", "C", "belt B centre plate", "Bow-tie 6061-T6 1.5 mm -> 7075-T6 1.2 mm (hipbelt_structural.md section 6.1). "
        "7075-T6 cannot be cold-rolled: form in O temper and age (service) or machine the arc.", g7075,
        (cpm["plate_g"] - g7075) / 1000 * float(MAT.load("alu_7075_t6").cost_usd["value"]) - cpm["plate_g"] / 1000 * float(MAT.load("alu_6061_t6").cost_usd["value"]) + 25.0, 0.0, "none", "none", "none",
        "YES: plate today SF/req C2 1.21, walking fatigue 1.20 (6061); the structural note's model gives 1.77 (fatigue) "
        "at 1.2 mm 7075, not yet checked in the FE", "medium", "C: structural-fea-engineer re-run + forming quote "
        "($25 ASSUMPTION heat-treat service)")
    hub = cpm["hub_g"] * (1 - ((28 ** 2 - 10.2 ** 2) * 10) / ((36 ** 2 - 10.2 ** 2) * 12))
    cut("C-2", "C", "belt B hub", "PA66 hub bushing D36 x 12 -> D28 x 10 (section 6.2).", hub, -0.1, 0.0, "none", "none",
        "none", "YES: hub-bore bearing, walking 1.66 with H on the pin, 5.3 without (the pad seat keeps H off)",
        "medium", "C: re-check bearing")
    cut("C-3", "C", "belt B centre plate", "Lightening holes in the bow-tie spine flanges, x 30-55 (section 6.3; -5 g is "
        "the structural note's estimate).", 5.0, 0.0, 0.0, "none", "none", "none",
        "YES: the spine carries the C2 peak (SF/req 1.21 today)", "low", "C: FE re-run")
    P = C.PAD_SEAT
    pad = P["backer"][0] * P["backer"][1] * 0.2 * 1e-9 * rec("hdpe_sheet", "density_kg_m3") * 1000
    cut("C-4", "C", "lumbar pad seat", "HDPE pad backer 1.0 -> 0.8 mm (corrie_body.md 11.2: the backer bridges the 70 mm "
        "channel).", pad, -0.05, 0.0, "none", "none", "none",
        "YES: the backer carries the lumbar push (413 N at 15 in, 1 g) across the 70 mm channel; NO SF on file", "medium",
        "C: structural-fea-engineer (plate bending over the channel) + HB-1 fit")
    b05 = _piece(b, "B-05")
    g, usd = _swap([b05], "challenge_ultra_200")
    cut("C-5", "C", "bag bottom (O-5)", "Bottom B-05 500D -> Challenge ULTRA 200 (O-5): the records now carry the "
        "evidence (Taber 1500 -> 2000, tear 130 -> 250 N, waterproof floor). ULTRA is already 4 CORRIE pieces, and 500D "
        "then stays only on B-16 floor channels and the rifle boot.", g, usd, 0.0, "BETTER (records)",
        "quietness 3 -> 2 on the floor (not brushed)", "none",
        "YES: the HE / B-18 bag-on seam is governed by the B-05 fabric strip, 2355 N, SF 2.31 on 500D; ULTRA's grab "
        "strength is not in its record -> PT-3 strip test", "medium", "YES if PT-3 holds (evidence for the held O-5)",
        look="stock ULTRA colour on the floor", status="held O-5: evidence brought")
    b11 = PANELS["B-11"]["mass_g_total"]
    cut("C-6", "C", "lash tabs (O-15)", "B-11 lash tabs Hypalon -> laser-cut TPU-coated 840D (O-15).",
        b11 * (1 - rec("tpu_coated_nylon_840d", "areal_density_gsm") / rec("hypalon_coated_nylon", "areal_density_gsm")),
        -0.14, 0.0, "Taber 5000 -> 4000", "quietness 4 -> 2 (records)", "none",
        "YES: 25 x 5 slot to the 450 N buckle class; no SF on file -> 5-sample slot pull test", "medium",
        "YES if the pull test holds (held O-15)", status="held O-15")
    yoke_a = 0.0182
    cut("C-7", "C", "harness yoke plate", "CFRP yoke plate 1.5 -> 1.2 mm (0.0182 m2, cfrp_plate_quasi_iso).",
        yoke_a * 0.3e-3 * rec("cfrp_plate_quasi_iso", "density_kg_m3") * 1000, -yoke_a * float(MAT.load("cfrp_plate_quasi_iso").cost_usd["value"]) * 0.3 / 1.5, 0.0,
        "none", "none", "none", "YES: the lifters and straps anchor here (T1(c), 102 kg on straps + lifters); NO SF on file "
        "(build_simplicity X-1 flag)", "low", "C: structural-fea-engineer")
    br = {r["rail"]["key"]: r for r in _json("back_rail_results.json")["rows"]}
    cut("C-8", "C", "back rails", "Stay rails 120 mm / 80 mm backer -> 130 mm / 70 mm backer (back_rail.md row r130_b70).",
        br["r120_b80"]["mass_g"] - br["r130_b70"]["mass_g"], br["r130_b70"]["cost_usd"] - br["r120_b80"]["cost_usd"], 0.0,
        "none", "none", "none", f"comfort: peak {br['r130_b70']['peak_kpa']:.2f} kPa vs {br['r120_b80']['peak_kpa']:.2f} "
        "today (limit 14, margin 1.008); air gutter 110 -> 100 mm and the rail edge moves onto the rib curve (x +/-180)",
        "medium", "C: fit test on 3 backs")
    fm = _json("frame_mass_production.json")
    cut("C-9", "C", "printed frame body", "Re-run the generative body against the rev C envelope with a mass objective "
        "(ASSUMPTION: 5 % of the 823 g body is removable from low-stress ligaments).", 0.05 * fm["printed_body_g"],
        0.0, 0.0, "none", "none", "none (original generative geometry)",
        "YES: printed body strength 1.51, fatigue 1.04 (IM3 couple, C_im3 static_carry|15), creep 2.23 (rev C "
        "verification). Fatigue governs at 1.04, so any cut must come from regions far from the upper bar / pawl housing",
        "low", "C: structural-fea-engineer (gendesign re-run), not run here")

    # ---------------- considered, not recommended (shown so the owner sees them)
    cut("X-1", "X", "door zip", "Door zip #10 -> #8 coil (O-13 precedent, owner said NO for the main zip).",
        1.3143 * (rec("coil_zipper_10", "mass_g_m") - rec("coil_zipper_8", "mass_g_m")) + 2 * (6.0 - C.SLIDER8_G),
        -1.3 * 1.0, 0.0, "#8 under a meat load with gloves", "none", "none", "no", "high", "NO")
    cut("X-2", "X", "door zip", "Door zip: one slider instead of two (O-14 precedent).", 6.0, -1.0, 0.0, "none", "none",
        "none", "no", "high", "NO (ambidextrous access)")
    cut("X-3", "X", "wing + pouch straps", "25 -> 20 mm webbing and hardware on wing and pouch straps (no 20 mm records; "
        "ASSUMPTION 14 g/m).", (4 * 0.30 + 4 * 0.12) * (WEB25 - 14.0), 0.0, 0.0, "smaller hardware with gloves", "none",
        "none", "wing straps compress the load; no rating on file", "low", "NO (breaks the 25 mm HAUL family, R-25)")
    cut("X-4", "X", "meat harness (O-1)", "Meat straps 3 -> 2 (drop IM1).", 72.1, -12.97, 0.0, "", "", "",
        "YES (IM3 hook SF 2.71 carries more)", "high (bag_weight_plan)", "NO (primary mission)")
    cut("X-5", "X", "meat harness (O-2)", "Meat straps 38 -> 25 mm.", 84.8, -0.92, 0.0, "", "", "",
        "YES (25 mm cam ratings too low for the cradle)", "high (bag_weight_plan)", "NO")
    cut("X-6", "X", "rain fly (O-7)", "Fly 40D -> 20D silpoly (owner-frozen fly in a base pocket).", 8.6, 1.89, 0.0,
        "tear 25 -> 15 N", "", "", "no", "low (no record)", "NO")
    return out


# =====================================================================================================================
# 4. Packages, interactions, "what it would take"
# =====================================================================================================================
S_ITEMS = [   # build_simplicity.md section 2 (mass per pack, as the manufacturing-engineer computed it)
    ("S-01", "one 38 mm rated hook for all 12 hooks", +30.0, "stronger everywhere; heavier"),
    ("S-15", "Robic 210D -> 330D on BP-05, BP-07, H-10 (one fabric fewer)", +7.5, "simpler buy; heavier"),
    ("S-08", "fly pocket zip #5 -> #8 (zip SKUs 3 -> 2)", +2.0, "gloves; heavier"),
    ("S-12 (CORRIE form)", "roll-top hem B-07 cut from camo 630D, SH-03 deleted: alternative to B-2", None, "see B-2"),
    ("S-03", "drop body binding (taken here as B-1)", None, "B-1"),
    ("S-02 / S-05 / S-07 / S-09 / S-10 / S-14 / S-03a", "bartacks, outsourced spreader, one webbing colour, seam allowances,"
     " jigs, one test bench, one thread", 0.0, "0 g (S-09 < +/-2 g)"),
]


def s12_corrie(bd) -> float:
    b = bd["body"]
    hem, band = _piece(b, "B-07"), _piece(b, "SH-03")
    alt = hem.area_mm2 / 1e6 * rec("polyester_ht_630d_printable", "areal_density_gsm")
    return round(BC.piece_mass_g(hem) + BC.piece_mass_g(band) - alt, 1)


def packages(bd: dict, cl: list) -> dict:
    total = bd["total_g"]
    gaps = booking_gaps(bd)
    real0 = total + sum(g["g"] for g in gaps)
    by = {k: [x for x in cl if x["pkg"] == k] for k in "ABC"}
    # owner 2026-11-09: package B without the held fabric swaps (B-8 / B-9): B = the B items corrie.SPECS["B.2"] applies
    held_b = [x for x in by["B"] if x["id"] not in C.SPECS[APPLIED]["items"]]
    by["B"] = [x for x in by["B"] if x["id"] in C.SPECS[APPLIED]["items"]]
    # B pouch items interact (B-3 fabric, B-4 top, B-5 size): the package takes the combined pouch, not the sum
    combo = pouch_mass(L=280.0, W=190.0, H=60.0, top="cordura_330d_nylon66", body="robic_100d_ripstop")
    pouch_sum = sum(x["g"] for x in by["B"] if x["id"] in ("B-3", "B-4", "B-5"))
    pouch_inter = round((pouch_mass()["g"] - combo["g"]) - pouch_sum, 1)
    # held items B-8 / B-9 are in B only if their evidence arrives: counted, and flagged
    steps, booked, real = [], total, real0
    for k in "ABC":
        gb = sum(x["g_booked"] for x in by[k]) + (pouch_inter if k == "B" else 0.0)
        gr = sum(x["g"] for x in by[k]) + (pouch_inter if k == "B" else 0.0)
        booked -= gb
        real -= gr
        steps.append({"pkg": k, "items": [x["id"] for x in by[k]], "saved_booked_g": round(gb, 1), "saved_real_g": round(gr, 1),
                      "usd": round(sum(x["usd"] for x in by[k]), 2), "hours": round(sum(x["hours"] for x in by[k]), 1),
                      "after_booked_g": round(booked, 1), "after_real_g": round(real, 1),
                      "vs_target_real_g": round(real - C.TARGET_G, 1)})
    # what it would take
    mc = _json("mass_cut_results.json")
    sp = next(r["mass_g"] for r in GEO["weight"]["rows"] if r["group"].startswith("back-system"))
    frame = next(r["mass_g"] for r in GEO["weight"]["rows"] if r["group"].startswith("frame"))
    bdg = {p["part"]: p["g"] for p in bd["parts"]}
    # T-2 / T-3 act on the applied B.2 pack (the chain below starts from the B.2 table): B.2 pouch and IMP-1 masses
    c2 = C.make()
    b2b = C.build(c2, True, spec=APPLIED)
    pouch_now = (sum(BC.piece_mass_g(p) for p, g in b2b.pieces if g == "pouch")
                 + sum(BC.zip_mass_g(z) for z in b2b.zips if "pouch" in z["name"])
                 + sum(g for n, g in b2b.extra["hardware"] if n.startswith("pouch")))
    imp1 = next(d["mass_g"] for d in C.bag_pockets(c2, spec=APPLIED) if d["id"] == "IMP-1")
    b2 = applied_b2(cl, steps)
    after_c = b2["sizes"][SIZE]["with_c_g"]      # B.2 table - C (the projection the owner publishes against)
    frame_back = frame + sp
    need = after_c - C.TARGET_G
    take = [
        {"id": "T-1", "what": "Lighter-frame variant: carbon-tube ladder (mass_cut.md winner: frame + 2 mm QI spreader "
                              f"{mc['frame_g']:.0f} g, rev B, SF/req {mc['sf_min']:.2f}, fatigue {mc['sf_fatigue']:.2f}) in "
                              f"place of the printed body + crown + Sandwich v2 ({frame_back:.0f} g). Owner rejected the look "
                              "on 2026-11-01 (must read as a generative print); predates rev C, the barrier rule and Sandwich "
                              "v2, so the saving is an UPPER bound",
         "g": round(frame_back - mc["frame_g"], 1)},
        {"id": "T-2", "what": "Count the top pouch (B.2: 2.7 L) as an accessory (as the market does with lids: SG lid sold "
                              "separately, Exo quotes with and without). Accounting only: the hunter still carries it",
         "g": round(pouch_now, 1)},
        {"id": "T-3", "what": "Drop IMP-1 scope sleeve (owner-frozen B.1 pocket)", "g": round(imp1, 1)},
        {"id": "T-4", "what": "Meat straps 3 -> 2 (O-1, rec NO)", "g": 72.1},
    ]
    t_all = after_c - sum(t["g"] for t in take)
    frame_needed = frame_back - need
    return {"start_booked_g": total, "gaps": gaps, "start_real_g": round(real0, 1), "steps": steps,
            "pouch_interaction_g": pouch_inter, "pouch_combo": combo, "take": take,
            "after_all_take_g": round(t_all, 1), "frame_plus_spreader_needed_g": round(frame_needed, 1),
            "frame_plus_spreader_now_g": round(frame_back, 1), "target_g": C.TARGET_G, "s12_corrie_g": s12_corrie(bd),
            "held_b": [{"id": x["id"], "g": x["g"], "status": x["status"]} for x in held_b],
            "b2": b2}


def applied_b2(cl: list, steps: list) -> dict:
    """CORRIE B.2 = A + B (owner 2026-11-09), booked by corrie.weight_table(size, spec="B.2") per belt size, and the
    package-C projection on top of it (C items are size-independent; the belt load path is size M for every size, as
    in weight_table). ``recon_vs_packages_g`` = B.2 table minus the package arithmetic (start real - A - B): the few
    grams the B.2 booking adds that the cut list did not (e.g. the B-4 camo pull tab)."""
    c = C.make()
    c_items = [x for x in cl if x["pkg"] == "C"]
    # package C as gated (weight_c_structural.md): corrie.package_c_rows(); C-5 / C-6 / C-8 still wait on PT-3, the
    # slot pull test and the 3-back rail fit, and are listed, not counted
    c_rows = C.package_c_rows()
    c_g = round(-sum(g for _, g, _ in c_rows), 1)
    pending = [x for x in c_items if x["id"] in ("C-5", "C-6", "C-8")]
    rows = {}
    for s_ in C.BELT_SIZES:
        w = C.weight_table(s_, c, spec=APPLIED)
        w1 = C.weight_table(s_, c, spec=BASE)
        rows[s_] = {"b1_g": w1["total_g"], "b2_g": w["total_g"], "b2_lb": round(w["total_g"] / LB, 2),
                    "b2_vs_b1_g": round(w["total_g"] - w1["total_g"], 1),
                    "with_c_g": round(w["total_g"] - c_g, 1), "with_c_lb": round((w["total_g"] - c_g) / LB, 2),
                    "with_c_vs_publish_g": round(w["total_g"] - c_g - C.PUBLISH_G, 1)}
    st = {x["pkg"]: x for x in steps}
    m = C.weight_table(SIZE, c, spec=APPLIED)
    return {"spec": APPLIED, "items": list(C.SPECS[APPLIED]["items"]), "sizes": rows, "rows_M": m["rows"],
            "c_items": ["C-1", "C-2", "C-3", "C-9", "C-4 fix", "C-7 fix"], "c_saving_g": c_g, "publish_g": C.PUBLISH_G,
            "c_rows": [(n, round(g, 1), s_) for n, g, s_ in c_rows], "c_gates": C.C_GATES,
            "c_pending": [{"id": x["id"], "g": x["g"], "gate": x["rec"]} for x in pending],
            "recon_vs_packages_g": round(m["total_g"] - st["B"]["after_real_g"], 1)}


# =====================================================================================================================
# 5. Benchmarks (cited; docs/research/pack_market_2026.md, hipbelt_fit.md, bag_attachment_research.md, + 2026-11-09)
# =====================================================================================================================
def lbz(lb, oz=0.0):
    return round(lb * LB + oz * OZ, 0)


BENCH = [
    # (our group key, label, grams, url)
    ("frame_susp", "SG Krux frame, M belt, harness (2 lb 12 oz)", lbz(2, 12),
     "https://www.gearfool.com/collections/gear/products/stone-glacier-krux-frame-1"),
    ("frame_susp", "Exo K4 frame system (2 lb 15 oz)", lbz(2, 15),
     "https://exomtngear.com/collections/k4-pack-systems/products/k4-frame-system"),
    ("frame_susp", "Seek Outside Revolution 24 in (2 lb 9 oz)", lbz(2, 9), "https://checkout.seekoutside.com/revolution-suspension-and-frame/"),
    ("frame_susp", "Kifaru ARK frame, M belt (3 lb 1.4 oz)", lbz(3, 1.4), "https://shop.gohunt.com/products/kifaru-ark-frame"),
    ("frame_only", "KUIU ICON 6 frame sheet only, Tall (13.7 oz)", lbz(0, 13.7),
     "https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper"),
    ("belt", "SG 3-piece belt (12.8 oz)", lbz(0, 12.8),
     "https://stoneglacier.com/collections/sg-products/products/sg-3-piece-belt"),
    ("bag", "SG Sky 5900 bag (2 lb 4 oz)", lbz(2, 4), "https://www.stoneglacier.com/products/sky-5900-xcurve-krux"),
    ("bag", "Exo K4 5000 bag (2 lb 6 oz)", lbz(2, 6), "https://exomtngear.com/4800"),
    ("lid", "Exo K4 lid (8.1 oz)", lbz(0, 8.1), "https://exomtngear.com/lid"),
    ("system", "SG Sky 5900 + Krux, M belt (5 lb 1.4 oz)", lbz(5, 1.4), "https://www.stoneglacier.com/products/sky-5900-xcurve-krux"),
    ("system", "Exo K4 5000 with lid (5 lb 13 oz)", lbz(5, 13), "https://exomtngear.com/4800"),
    ("system", "Mystery Ranch Sawtooth 65, MYSTERIUM (5 lb 4 oz)", lbz(5, 4),
     "https://www.huntinfool.com/articles/type/staff-articles/mystery-ranch-mysterium-sawtooth-65"),
    ("system", "KUIU ICON 6 6000 (6 lb 2.4 oz)", lbz(6, 2.4), "https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper"),
    ("system", "Mystery Ranch Beartooth 85, MYSTERIUM (6.2 lb)", round(6.2 * LB, 0), "https://www.mysteryranch.com/beartooth-85-mens-pack"),
    ("system", "Kifaru ARK + Absaroka (6 lb 4 oz)", lbz(6, 4), "https://gearjunkie.com/outdoor/hunt-fish/best-hunting-backpack"),
]
OUR_BENCH = {   # our groups that compare to each benchmark class
    "frame_susp": ["Frame (printed body + carbon crown)", "Torso adjust", "Back system (spreader + back panel)",
                   "Harness (J-straps, yoke, lifters, sternum)", "Hipbelt B (body, load path, pad seat, pockets, holster)"],
    "frame_only": ["Frame (printed body + carbon crown)"],
    "bag": ["Bag body (CORRIE shell, collar, wings, door, roll-top)", G_POCK, "Rain fly (fly + base pocket)"],
    "lid": [G_POUCH],
}


def bench_table(bd):
    g = bd["groups"]
    rows = []
    for key, groups in OUR_BENCH.items():
        ours = sum(g.get(k, 0.0) for k in groups)
        rows.append({"class": key, "ours_g": round(ours, 1), "groups": groups,
                     "bench": [(lab, gg, url) for k, lab, gg, url in BENCH if k == key]})
    hb = [p for p in bd["parts"] if p["group"].startswith("Hipbelt")]
    belt_only = sum(p["g"] for p in hb if not p["part"].startswith(("IMP-", "lumbar pad seat")))
    rows.append({"class": "belt", "ours_g": round(belt_only, 1), "groups": ["Hipbelt B without IMP-5, IMP-3, pad seat"],
                 "bench": [(lab, gg, url) for k, lab, gg, url in BENCH if k == "belt"]})
    rows.append({"class": "system", "ours_g": bd["total_g"], "groups": ["whole pack"],
                 "bench": [(lab, gg, url) for k, lab, gg, url in BENCH if k == "system"]})
    return rows


# =====================================================================================================================
# 6. Charts
# =====================================================================================================================
BLUE, ORANGE, AQUA, GREY, INK, INK2, SURF = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e", "#fcfcfb"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c2")
    ax.tick_params(colors=INK2, labelsize=10)
    ax.grid(axis="x", color="#e6e5e0", lw=0.8)
    ax.set_axisbelow(True)


def charts(bd, cl, pk, bench) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    files = []
    # 1 group Pareto + benchmark ticks
    g = {k: v for k, v in bd["groups"].items() if k != G_REC}
    names, vals = list(g)[::-1], list(g.values())[::-1]
    fig, ax = plt.subplots(figsize=(9, 7.6), dpi=110, facecolor=SURF)
    ax.set_facecolor(SURF)
    ax.barh(names, vals, color=BLUE, height=0.62, edgecolor=SURF, linewidth=2)
    cum = 0.0
    tot = sum(g.values())
    for i, (n, v) in enumerate(zip(names[::-1], vals[::-1])):
        cum += v
        ax.text(v + 12, len(names) - 1 - i, f"{v:.0f} g  ({cum / tot * 100:.0f} % cum.)", va="center", fontsize=9, color=INK2)
    _style(ax)
    ax.set_xlim(0, max(vals) * 1.45)
    ax.set_xlabel("grams, size M belt", color=INK2)
    ax.set_title(f"CORRIE B.1 mass by group: {bd['total_g']:.0f} g ({bd['total_g'] / LB:.2f} lb); target {C.TARGET_G:.0f} g",
                 color=INK, fontsize=12, loc="left")
    fr = next(r for r in bench if r["class"] == "frame_susp")
    txt = (f"Frame + suspension (frame, adjust, back, harness, belt): ours {fr['ours_g']:.0f} g\n" +
           "\n".join(f"  {lab}: {gg:.0f} g" for lab, gg, _ in fr["bench"]))
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    fig.text(0.02, 0.015, txt, ha="left", va="bottom", fontsize=9, color=INK2,
             bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#d9d8d2"))
    f = SCREENS / f"{DATE}_weight_1.png"
    fig.savefig(f, facecolor=SURF)
    plt.close(fig)
    files.append(f)
    # 2 part Pareto, top 25
    parts = sorted((p for p in bd["parts"] if p["group"] != G_REC), key=lambda p: -p["g"])[:25]
    fig, ax = plt.subplots(figsize=(9, 8.2), dpi=110, facecolor=SURF)
    ax.set_facecolor(SURF)
    lab = [(p["part"][:62] + ("..." if len(p["part"]) > 62 else "")) for p in parts][::-1]
    ax.barh(lab, [p["g"] for p in parts][::-1], color=BLUE, height=0.62, edgecolor=SURF, linewidth=2)
    for i, p in enumerate(parts[::-1]):
        ax.text(p["g"] + 8, i, f"{p['g']:.0f}", va="center", fontsize=8.5, color=INK2)
    _style(ax)
    ax.tick_params(axis="y", labelsize=8)
    share = sum(p["g"] for p in parts) / bd["total_g"] * 100
    ax.set_title(f"Top 25 parts = {share:.0f} % of the pack (of {sum(1 for p in bd['parts'] if p['group'] != G_REC)} booked parts)", color=INK,
                 fontsize=12, loc="left")
    ax.set_xlabel("grams", color=INK2)
    fig.tight_layout()
    f = SCREENS / f"{DATE}_weight_2.png"
    fig.savefig(f, facecolor=SURF)
    plt.close(fig)
    files.append(f)
    # 3 waterfall
    steps = [("Booked B.1\n(belt M)", pk["start_booked_g"], "total")]
    for gp in pk["gaps"]:
        steps.append((f"{gp['id']}\n{'binding' if gp['id'] == 'G-1' else 'fly'}", gp["g"], "up"))
    steps.append(("Real\nestimate", pk["start_real_g"], "total"))
    b2 = pk["b2"]
    for s in pk["steps"][:2]:
        steps.append((f"Pkg {s['pkg']}\n(applied)", -s["saved_real_g"], "down"))
    if abs(b2["recon_vs_packages_g"]) >= 0.05:
        steps.append(("B.2\nbooking", b2["recon_vs_packages_g"], "up" if b2["recon_vs_packages_g"] > 0 else "down"))
    steps.append((f"B.2 table\n(A+B, M)", b2["sizes"][SIZE]["b2_g"], "total"))
    steps.append(("Package C\n(gated, net)", -b2["c_saving_g"], "pending"))
    steps.append(("B.2 + C", b2["sizes"][SIZE]["with_c_g"], "total"))
    for t in pk["take"]:
        steps.append((t["id"], -t["g"], "take"))
    steps.append(("With\nT-1..T-4", pk["after_all_take_g"], "total"))
    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=110, facecolor=SURF)
    ax.set_facecolor(SURF)
    run = 0.0
    for i, (n, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, color=BLUE, width=0.66, edgecolor=SURF, linewidth=2)
            run = v
            ax.text(i, v + 25, f"{v:.0f}", ha="center", fontsize=9, color=INK)
        else:
            lo, hi = sorted((run, run + v))
            col = ORANGE if v > 0 else (AQUA if kind in ("down", "pending") else "#b9b8b1")
            h = max(hi - lo, 4.0)               # a few-gram step still shows as a sliver
            ax.bar(i, h, bottom=lo if v > 0 else hi - h, color=col, width=0.66,
                   edgecolor={"pending": INK2, "take": "#f4f3ef"}.get(kind, col), linewidth=1.0,
                   hatch={"take": "//", "pending": ".."}.get(kind), alpha=0.55 if kind == "pending" else 1.0)
            ax.text(i, hi + 25, f"{v:+.0f}", ha="center", fontsize=9, color=INK2)
            run += v
    ax.axhline(C.TARGET_G, color=INK2, ls="--", lw=1.2)
    ax.text(-0.4, C.TARGET_G + 20, f"target {C.TARGET_G:.0f} g (6.6 lb)", ha="left", fontsize=9, color=INK2)
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels([s[0] for s in steps], fontsize=8.5, color=INK2)
    ax.set_ylim(2400, max(pk["start_real_g"], pk["start_booked_g"]) + 200)
    ax.set_ylabel("grams (axis starts at 2400 g)", color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e6e5e0", lw=0.8)
    ax.set_axisbelow(True)
    ax.axhline(C.PUBLISH_G, color=AQUA, ls=":", lw=1.2)
    ax.text(len(steps) - 0.6, C.PUBLISH_G + 20, f"publish ~{C.PUBLISH_G:.0f} g (8.4 lb)", ha="right", fontsize=9,
            color=INK2)
    ax.set_title("CORRIE weight: B.1 -> B.2 (A + B applied, the corrie.py table) -> C projected (gated); "
                 "T items = owner calls", color=INK, fontsize=11, loc="left")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="total (from corrie.weight_table)"),
                       Patch(color=ORANGE, label="booking gap / booking detail (heavier)"),
                       Patch(color=AQUA, label="applied package"),
                       Patch(facecolor=AQUA, alpha=0.55, hatch="..", edgecolor=INK2, label="package C, pending gates"),
                       Patch(facecolor="#b9b8b1", hatch="//", label="feature / frame decision")],
              frameon=False, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    f = SCREENS / f"{DATE}_weight_3.png"
    fig.savefig(f, facecolor=SURF)
    plt.close(fig)
    files.append(f)
    for f in files:
        assert f.stat().st_size <= 1.5e6, f
    return files


# =====================================================================================================================
# 7. Report
# =====================================================================================================================
def _lb(g):
    return f"{g / LB:.2f} lb"


def report(bd, cl, pk, bench, files) -> str:
    L = []
    w = L.append
    st = {s["pkg"]: s for s in pk["steps"]}
    w("# CORRIE B.1: whole-pack weight pass\n")
    b2 = pk["b2"]
    bm = b2["sizes"][SIZE]
    w("Owner: pack-designer. Date 2026-11-09. The pass is computed on CORRIE **B.1** (`corrie.weight_table(size, "
      "spec=\"B.1\")`); every cut below is defined against B.1. **Owner decision 2026-11-09 (DECISIONS: \"Yes\" to the "
      "weight-pass recommendation): package A and package B without the held B-8 / B-9 are applied as CORRIE B.2, now "
      "the `corrie.py` default** (`corrie.SPECS`, flag `CORRIE_SPEC=B.1` / `spec=\"B.1\"` reproduces B.1). Package C is "
      "projected, not applied. Generated by `designs/pack_5200/weight_pass_corrie.py` from `corrie.weight_table()`, the "
      "`geometry.yaml` weight rows, `panels.yaml`, the analysis JSONs and the material records. Re-run it; do not "
      "hand-edit numbers. Tests: `tests/test_weight_pass_corrie.py`. No released SPINE file is changed.\n")
    w("## 0. Summary\n")
    w(f"- **Applied (CORRIE B.2, belt {SIZE}): {bm['b2_g']:.1f} g ({_lb(bm['b2_g'])})**, booked by "
      f"`corrie.weight_table('{SIZE}', spec='B.2')` with the binding and fly gaps G-1 / G-2 included. **Projected with "
      f"package C: {bm['with_c_g']:.0f} g ({_lb(bm['with_c_g'])})**, against the ~{b2['publish_g']:.0f} g (8.4 lb) the "
      "owner publishes (section 4a).")
    w(f"- Booked today (belt {SIZE}): **{bd['total_g']:.1f} g ({_lb(bd['total_g'])})**. Target **{C.TARGET_G:.0f} g "
      f"(6.6 lb)**, gap **{bd['total_g'] - C.TARGET_G:.0f} g**. The DECISIONS row of 2026-11-05 published 2976 g; "
      "`corrie.TARGET_G` (2994 g) is used here.")
    w(f"- Booking gaps found: **+{sum(g['g'] for g in pk['gaps']):.0f} g** of real mass no table books (body binding, "
      f"CORRIE-sized fly). Real estimate **{pk['start_real_g']:.0f} g**.")
    for k, nm in (("A", "no-regret, applied"), ("B", "owner OK, applied without B-8 / B-9"),
                  ("C", "needs FEA / tests, not applied")):
        s = st[k]
        w(f"- Package **{k}** ({nm}): **-{s['saved_real_g']:.0f} g** real (-{s['saved_booked_g']:.0f} g booked), "
          f"{s['usd']:+.2f} $/pack, {s['hours']:+.1f} beginner h -> **{s['after_real_g']:.0f} g "
          f"({_lb(s['after_real_g'])})**, {s['vs_target_real_g']:+.0f} g vs target (package arithmetic; the B.2 "
          "table is the booked number).")
    w(f"- **The 6.6 lb target is not reachable with CORRIE's features on the printed frame.** After A+B+C the pack is "
      f"about **{bm['with_c_g']:.0f} g ({_lb(bm['with_c_g'])})** (B.2 table - C). Even with every 'what it would take' "
      f"item (lighter frame, pouch as accessory, no scope sleeve, 2 meat straps) it is about "
      f"**{pk['after_all_take_g']:.0f} g**. To hit {C.TARGET_G:.0f} g with A+B+C and all features, frame + spreader "
      f"would have to weigh **{pk['frame_plus_spreader_needed_g']:.0f} g** (today {pk['frame_plus_spreader_now_g']:.0f} g).")
    w("- Recommendation (taken by the owner 2026-11-09): adopt A now, take B item by item, send C to the structural-fea-engineer, and **re-baseline the "
      f"published weight for CORRIE on the printed frame to about {b2['publish_g']:.0f} g "
      f"({b2['publish_g'] / LB:.1f} lb)**. Keep 6.6 lb (and 5.0 lb) as targets for a "
      "lighter-frame variant (section 6).\n")

    w("## 1. Mass breakdown (size M), ranked\n")
    w(f"The breakdown re-books every part and is checked against `corrie.weight_table('M')` = {bd['total_g']:.1f} g. The "
      f"one balancing row, **{bd['reconciliation_g']:+.1f} g**, is the difference between how SPINE's body is booked in "
      "`geometry.yaml` (design panels + diagonal zip + SH-01..04 + roll-top HDPE) and the cut-set body metric that "
      "`weight_table()` subtracts. Shared rows (frame, back system, harness, attachment, meat haul, fly, thread) are the "
      "released SPINE rows; CORRIE parts come from `corrie.py`.\n")
    w("### 1.1 By group (Pareto)\n")
    w("| # | Group | g | oz | % | cum % |")
    w("|---:|---|---:|---:|---:|---:|")
    cum = 0.0
    for i, (k, v) in enumerate(bd["groups"].items(), 1):
        cum += v
        w(f"| {i} | {k} | {v:.1f} | {v / OZ:.1f} | {v / bd['total_g'] * 100:.1f} | {cum / bd['total_g'] * 100:.1f} |")
    w(f"| | **Total** | **{bd['total_g']:.1f}** | **{bd['total_g'] / OZ:.1f}** | | |\n")
    w("### 1.2 By part: top 30 of the booked parts\n")
    w("| # | Part | Group | g | Source |")
    w("|---:|---|---|---:|---|")
    parts = sorted((p for p in bd["parts"] if p["group"] != G_REC), key=lambda p: -p["g"])
    cum = 0.0
    for i, p in enumerate(parts[:30], 1):
        cum += p["g"]
        w(f"| {i} | {p['part']} | {p['group'].split(' (')[0]} | {p['g']:.1f} | {p['source']} |")
    w(f"\nTop 30 = {cum:.0f} g ({cum / bd['total_g'] * 100:.0f} %). The full list ({len(parts)} parts + the "
      "reconciliation row) is in "
      "`analysis/weight_pass_corrie.json` (`parts`).\n")
    w("### 1.3 Benchmarks (cited)\n")
    w("Competitors publish system, frame-system, belt and bag numbers, not part lists; the classes below map our groups "
      "onto what they publish. Sources: `docs/research/pack_market_2026.md`, `hipbelt_fit.md`, "
      "`bag_attachment_research.md`, plus a 2026-11-09 search (Kifaru ARK by belt size; Mystery Ranch does not publish "
      "MYSTERIUM frame or belt masses, only systems).\n")
    w("| Class | Ours g | Benchmark | g | Ours minus benchmark | Source |")
    w("|---|---:|---|---:|---:|---|")
    for r in bench:
        for lab, gg, url in r["bench"]:
            w(f"| {r['class']} | {r['ours_g']:.0f} | {lab} | {gg:.0f} | {r['ours_g'] - gg:+.0f} | {url} |")
    w("\nClasses: frame_susp = frame + torso adjust + back system + harness + hipbelt group; frame_only = our frame line "
      "(printed body + crown; DECISIONS 2026-11-01 frame target 550-700 g); bag = body + pockets + fly (we also carry the "
      "attachment and meat systems the leaders fold into frame and bag); lid = our top pouch; belt = belt B body + load "
      "path, without pockets, holster and pad seat. **Read-out:** the bag side is at or under the leaders; the frame + "
      "suspension is roughly twice theirs. That is where the gap is.\n")

    w("## 2. Booking gaps (real grams no table books)\n")
    w("| Id | What | g | Basis |")
    w("|---|---|---:|---|")
    for gp in pk["gaps"]:
        w(f"| {gp['id']} | {gp['what']} | +{gp['g']:.1f} | {gp['basis']} |")
    w("\nNot a cut, but the real pack is heavier than 4000 g by about this much, and the target must be met by the real "
      "pack. Also noted, not booked: thread is the SPINE 3 % row (41.4 g), not re-scaled to CORRIE's heavier soft goods.\n")

    w("## 3. Candidate cuts\n")
    w("g = real grams saved (booked grams differ only for B-1, which removes unbooked binding). $ = material delta per "
      "pack from the records (`bag_weight_plan.usd_m2`; ASSUMPTION where no record). h = beginner hours "
      "(`bag_concepts.HOURS` model, rank not plan). Load path: the current SF / margin quoted from the repo's analyses; "
      "**no FEA was run in this pass**.\n")
    hdr = ("| Id | Zone | Change | g | $ | h | Durability | Quiet | IP | Look | Load path (SF, margin) | Confidence | Rec. |")
    for k, title in (("A", "Package A: no-regret"), ("B", "Package B: owner OK needed"),
                     ("C", "Package C: aggressive, needs the structural-fea-engineer and / or a test"),
                     ("X", "Considered and not recommended")):
        w(f"### 3.{'ABCX'.index(k) + 1} {title}\n")
        w(hdr)
        w("|---|---|---|---:|---:|---:|---|---|---|---|---|---|---|")
        for x in (x for x in cl if x["pkg"] == k):
            w(f"| {x['id']} | {x['zone']} | {x['change']} | {x['g']:.1f} | {x['usd']:+.2f} | {x['hours']:+.2f} | "
              f"{x['durability']} | {x['quiet']} | {x['ip']} | {x['look']} | {x['load_path']} | {x['confidence']} | "
              f"{x['rec']} |")
        w("")
    w(f"Pouch interaction: B-3, B-4 and B-5 together save {sum(x['g'] for x in cl if x['id'] in ('B-3', 'B-4', 'B-5')) + pk['pouch_interaction_g']:.1f} g, "
      f"not the sum of the three ({pk['pouch_interaction_g']:+.1f} g): the package uses the combined pouch "
      f"({pk['pouch_combo']['g']:.1f} g, {pk['pouch_combo']['volume_L']} L).\n")
    w("**Held fabric swaps (bag_weight_plan.md):** O-5 now has its evidence in the records (ULTRA 200 beats 500D on "
      "abrasion and tear); it is C-5 because the B-05 strip governs the HE / B-18 seam (PT-3). O-15 has a method (C-6). "
      "O-4 still lacks an abrasion value and O-3 / O-6 still lack records (`nylon_ripstop_70d`, "
      "`polyester_300d_printable`): no new evidence, they stay on hold (B-8, B-9 are counted in package B only if it "
      "arrives). O-6 on CORRIE would only touch the pouch top and the hem band, which B-2 / B-4 already remove.\n")
    w("**Build-simplicity S-items** (`build_simplicity.md` section 2) are mostly mass-neutral or heavier. If the owner "
      "takes them with this pass:\n")
    w("| S-item | Change | Mass g | Note |")
    w("|---|---|---:|---|")
    for sid, ch, g, note in S_ITEMS:
        gtxt = "see note" if g is None else f"{g:+.1f}"
        if sid.startswith("S-12"):
            gtxt = f"-{pk['s12_corrie_g']:.1f}"
        w(f"| {sid} | {ch} | {gtxt} | {note} |")
    w("\nS-12 on CORRIE (hem in camo 630D, SH-03 deleted) saves less than B-2 (hem solid, SH-03 deleted) and keeps the "
      "camo; pick one.\n")

    w("## 4. Packages\n")
    w("| Package | Items | Saved real g | Saved booked g | $ / pack | Beginner h | Pack after (real) | lb | vs 2994 g |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    w(f"| start | booked {bd['total_g']:.1f} + gaps | | | | | {pk['start_real_g']:.0f} | {pk['start_real_g'] / LB:.2f} | "
      f"{pk['start_real_g'] - C.TARGET_G:+.0f} |")
    for s in pk["steps"]:
        w(f"| {s['pkg']} | {', '.join(s['items'])} | {s['saved_real_g']:.1f} | {s['saved_booked_g']:.1f} | {s['usd']:+.2f} | "
          f"{s['hours']:+.1f} | {s['after_real_g']:.0f} | {s['after_real_g'] / LB:.2f} | {s['vs_target_real_g']:+.0f} |")
    w("\nWaterfall: `outputs/screens/20261109_weight_3.png`. Package B is the owner's: without the held B-8 / B-9 "
      f"({', '.join(f'{h['id']} {h['g']:.1f} g' for h in pk['held_b'])}, not counted until their evidence arrives).\n")
    w("### 4a. Applied: CORRIE B.2 (A + B), per belt size, and the package-C projection\n")
    w(f"Items applied in `corrie.py` (spec B.2): {', '.join(b2['items'])}. **Package C as gated** "
      "(`analysis/weight_c_structural.md`, `corrie.package_c_rows()`): "
      + "; ".join(f"{n} {g:+.1f} g" for n, g, _ in b2["c_rows"]) +
      f" = **{-b2['c_saving_g']:+.1f} g**, size-independent, projected as 'B.2 + C', not applied; gates: {b2['c_gates']}. "
      "Still pending and not counted: " + ", ".join(f"{p['id']} -{p['g']:.1f} g" for p in b2["c_pending"]) +
      " (PT-3 strip, slot pull test, 3-back rail fit). B.2 table minus the package "
      f"arithmetic (belt {SIZE}): {b2['recon_vs_packages_g']:+.1f} g (the B-4 camo pull tab the cut list did not "
      "book, and the pouch zip cut to L - 20 mm).\n")
    w("| Belt | B.1 g | **B.2 g** | B.2 lb | B.2 vs B.1 | B.2 + C (gated) g | lb | vs publish ~3800 g |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for s_, r in b2["sizes"].items():
        w(f"| {s_} | {r['b1_g']:.1f} | **{r['b2_g']:.1f}** | {r['b2_lb']:.2f} | {r['b2_vs_b1_g']:+.1f} | "
          f"{r['with_c_g']:.1f} | {r['with_c_lb']:.2f} | {r['with_c_vs_publish_g']:+.0f} |")
    w(f"\nB.2 rows that differ from B.1 (belt {SIZE}, `corrie.weight_table('{SIZE}', spec='B.2')`):\n")
    w("| Row | g |")
    w("|---|---:|")
    for n, g, _src in b2["rows_M"]:
        if n.startswith(("CORRIE body", "IMP-", "hipbelt body", "A-2", "B-10", "G-1", "G-2")):
            w(f"| {n} | {g:+.1f} |")
    w("")

    w("## 5. Why the target is out of reach, and what it would take\n")
    w("The 2994 g target dates from 2026-11-05, when the pack was 3030 g. Since then the owner and the gates added the "
      "crown-hood attachment (+136 g), the back-panel booking with the rail backers (+161 g), float links (+54 g), "
      "CORRIE's box body, wings, door and pouch, the B.1 pockets, belt B, its aluminium load path and the pad seat "
      f"({bd['weight_table']['vs_spine_g']:+.0f} g vs SPINE, `weight_table`). Those are frozen features or safety gates "
      "(history: DECISIONS 2026-11-05 / -06 rows). What is left to cut without touching them, packages A+B+C, is "
      f"{sum(s_['saved_real_g'] for s_ in pk['steps']):.0f} g, about "
      f"{sum(s_['saved_real_g'] for s_ in pk['steps']) / (pk['start_real_g'] - C.TARGET_G) * 100:.0f} % of the real gap.\n")
    w("| Id | What it would take | g |")
    w("|---|---|---:|")
    for t in pk["take"]:
        w(f"| {t['id']} | {t['what']} | -{t['g']:.1f} |")
    w(f"\nAfter A+B+C and T-1..T-4 together: about **{pk['after_all_take_g']:.0f} g** "
      f"({pk['after_all_take_g'] / LB:.2f} lb). Only the frame line moves the number by hundreds of grams; for 2994 g "
      f"with every CORRIE feature, frame + spreader must come in at about {pk['frame_plus_spreader_needed_g']:.0f} g.\n")

    w("## 6. Owner decisions (answered 2026-11-09: see DECISIONS; kept here as asked)\n")
    w(f"1. **Re-baseline the published weight** for CORRIE on the printed frame (recommend about "
      f"{math.ceil(st['C']['after_real_g'] / 50) * 50:.0f} g after A+B+C, or {math.ceil(st['A']['after_real_g'] / 50) * 50:.0f} g "
      "with A only), and keep 6.6 / 5.0 lb for a lighter-frame variant.")
    w("2. **Lighter-frame variant** (T-1): commission a rev C study from the structural-fea-engineer of a tube / hybrid "
      "frame that still reads as a generative print (printed nodes on carbon tubes). This is the only lever of the "
      "right size.")
    w("3. **Package B**, item by item: B-1 (binding, after a wash swatch), B-2 (SH-03 off) or S-12, B-3/B-4/B-5 "
      "(pouch fabric, top, 3 L), B-6 (scope panel 100D), B-7 (phone pocket sewn on), B-10 (TPU trims, louder).")
    w("4. **Accounting**: count the top pouch as an accessory in the published base weight (T-2), as Exo and SG do with "
      "lids? The fly stays in (owner 2026-11-01).")
    w("5. **Held swaps**: O-5 and O-15 go to their tests (PT-3 strip, slot pull); O-4, O-3, O-6 wait on the "
      "materials-engineer records.\n")
    w("Hand-offs: structural-fea-engineer C-1..C-4, C-7, C-9 (and T-1); materials-engineer records for "
      "`nylon_ripstop_70d`, `polyester_300d_printable`, the UltraGrid abrasion value, a lighter 3D spacer mesh, a "
      "20 mm webbing family (X-3), ULTRA 200 grab strength (C-5); manufacturing-engineer the B-1 wash swatch and the "
      "C-6 pull test.\n")
    w("## 7. Assumptions (new in this pass)\n")
    w(f"- ASSUMPTION: grosgrain binding {BINDING_GM} g/m, $ {BINDING_USD_M}/m (as build_simplicity S-03); S-03 hour rate "
      "scaled by length.")
    w("- ASSUMPTION: the CORRIE fly scales with the outer-shell area (G-2); wing cover not included.")
    w(f"- ASSUMPTION: G-hook $ {G_HOOK_USD}; 7075 forming / ageing service $25 (C-1); printed-body cut 5 % (C-9).")
    w("- ASSUMPTION: a 150 mm wrap tail is enough for a gloved pull (A-2); 20 mm webbing 14 g/m (X-3, not recommended).")
    w("- The belt-B load path is size M for every size (as `weight_table`).\n")
    w("## Screenshots\n")
    for f in files:
        w(f"- `{f.relative_to(ROOT)}`")
    return "\n".join(L) + "\n"


def run(write=True):
    bd = breakdown(SIZE)
    cl = cuts(bd)
    pk = packages(bd, cl)
    bench = bench_table(bd)
    files = charts(bd, cl, pk, bench) if write else []
    out = {"size": SIZE, "total_g": bd["total_g"], "groups": bd["groups"], "reconciliation_g": bd["reconciliation_g"],
           "parts": bd["parts"], "cuts": cl, "packages": {k: v for k, v in pk.items() if k != "pouch_combo"},
           "pouch_combo": pk["pouch_combo"], "benchmarks": bench, "target_g": C.TARGET_G,
           "screens": [str(f.relative_to(ROOT)) for f in files]}
    if write:
        (ANALYSIS / "weight_pass_corrie.json").write_text(json.dumps(out, indent=1, default=float))
        (ANALYSIS / "weight_pass_corrie.md").write_text(report(bd, cl, pk, bench, files))
    return out


if __name__ == "__main__":
    o = run()
    print("total", o["total_g"], "recon", o["reconciliation_g"])
    for s in o["packages"]["steps"]:
        print(s)
    print("after take", o["packages"]["after_all_take_g"], "frame+spreader needed", o["packages"]["frame_plus_spreader_needed_g"])
    print(o["screens"])
