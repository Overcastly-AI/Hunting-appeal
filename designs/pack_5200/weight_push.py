"""BL-037 weight push: the last 220 g after tests (pack-designer, 2026-11-13).

    python designs/pack_5200/weight_push.py            # print the lever list and the pick
    python designs/pack_5200/weight_push.py --write    # also write analysis/weight_push.{md,json} + 2 PNGs

What it does (ticket ``docs/backlog/BL-037-weight-push.md``):

1. **Lever list.** The after-tests pack (``weight_rollup_v2``, class A, belt M, base) by system and on BL-008's
   frame-side / bag-side split, against the leaders' published per-function figures (cited research docs).
2. **Candidates.** Every lever the ticket names plus the ones found here, each with grams computed from a record or
   another module's code, risk, test gate, effect on the owner rules (DECISIONS.md) and on build hours.
3. **Pick.** The lowest-risk set, every rev C factor kept. Each pick names its paper check (run here or in the module
   that owns the part) or a physical gate (``tests_physical/TEST_PLAN.md``, BL-037 section).
4. **Implement.** The picks are a new after-tests step ``A_bl037`` in ``weight_rollup_v2`` (rows from
   ``picked_rows``). They are all gated by a named test with the present part as the fallback, so by BL-014's rule
   (roll-up section 1) they are class A and the proven-now ledger (``huntkit.mass.ledger``) does not change.

No mass is typed here except the ASSUMPTION constants below (each with the test that settles it). Units g, mm.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ANALYSIS = HERE / "analysis"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from huntkit.mass import ledger as L  # noqa: E402
from huntkit.materials import load  # noqa: E402

import weight_rollup_v2 as W  # noqa: E402

LB, OZ = W.LB, W.OZ
STEP = "A_bl037"
DOC = ANALYSIS / "weight_push.md"
RESULT = ANALYSIS / "weight_push_results.json"
SCREENS = ROOT / "outputs" / "screens"
PREFIX = "20261113_BL037_"
DOC_SCREEN = ROOT / "docs" / "screens" / "20261113_BL037_1.png"
TICKET_G = 220.0                      # ticket: find >= 220 g after tests

# ---- ASSUMPTION constants (each settled by the named test) -----------------------------------------------------------
SLIDER_CORD_G = 15.0      # ASSUMPTION SLIDER-CORD: YKK #10 CN slider body with the door cord pull in place of the
#                           metal tab; the slider_10 record notes say 12-15 g (no weight published); upper end taken.
#                           Settled by weighing 5 on receipt (test SL-1).
LABEL_PRINTED_G = 1.0     # ASSUMPTION LABEL: one heat-transfer printed label on the liner face in place of the woven
#                           label set (geometry.yaml labels_g 8 g, itself an ASSUMPTION). Settled by weighing (SL-1).
# J-strap outline (build_geometry.build_panels.strap(): padded length 440, width 72 -> 58 mm, quantity 2); the foam
# pieces carry no seam allowance, so the foam area is the trapezoid. Cross-checked against geometry.yaml harness_J.
HS_L, HS_WT, HS_WB, HS_SA = 440.0, 72.0, 58.0, 10.0
HS_FOAM_T = 5.0           # HS-J3 load foam 5 mm (build_geometry)

# ---- records ----------------------------------------------------------------------------------------------------------
REC = {k: load(k) for k in ("eva_foam_45c", "eva_foam_perforated", "xlpe_foam_l200", "spacer_mesh_3d",
                            "cordura_330d_nylon66", "polyester_ht_630d_printable", "polyester_300d_printable",
                            "fidlock_magnetic_buckle_25mm", "buckle_side_release_25mm", "slider_10", "coil_zipper_10",
                            "coil_zipper_8", "ti_6al_4v", "sst_304_annealed", "cam_25mm_al", "ladder_lock_25mm_heavy")}


def _p(rec: str, prop: str) -> float:
    return float(REC[rec].require(prop))


# =====================================================================================================================
# 1. lever list: where we are heaviest per function
# =====================================================================================================================
def baseline_rows(size: str = "M") -> list:
    """The after-tests pack before BL-037 (roll-up class A rows without this ticket's step)."""
    return [r for r in W.scenario_rows("A", size) if r["step"] != STEP]


def baseline_total(size: str = "M", cfg: str = "base") -> float:
    return W.cfg_total(baseline_rows(size), cfg)


# BL-008's split (weight_configs_proposal.md section 5): the leaders SG and Exo count the meat carry in the frame
# weight. Frame side = FR + TA + BK + HN + BB + IM + US; bag side = shell, pockets, compression, attachment, fly pocket
# (attachment on the bag side: BL-008 ASSUMPTION); IMP-5L hip pocket, thread and labels unsplit.
FRAME_SIDE = ("frame", "back", "belt", "harness", "straps_meat")
BAG_SIDE_8 = ("bag_shell", "bag_pockets", "pouch", "fly", "straps_compression", "attachment")

# Leader figures per function, each from a cited research doc (the URL is on the line there).
LEADER_FN = [   # (function, our systems or row key, leader, published g, source)
    ("frame side (frame, back, belt, harness, meat carry)", "frame_side", "Stone Glacier Krux, M belt", 1247.0,
     "docs/research/published_weight_definitions.md 2.1 (Gearfool Krux)"),
    ("frame side (frame, back, belt, harness, meat carry)", "frame_side", "Exo K4 frame system", 1332.0,
     "docs/research/published_weight_definitions.md 2.1 (Exo K4 frame)"),
    ("frame side (frame, back, belt, harness, meat carry)", "frame_side", "Kifaru ARK, M belt", 1400.0,
     "docs/research/published_weight_definitions.md 2.1 (goHunt ARK)"),
    ("bag side (shell, pockets, compression, attachment)", "bag_side", "Stone Glacier Sky 5900 bag", 1026.0,
     "docs/research/published_weight_definitions.md 2.1 (SG Sky 5900)"),
    ("bag side (shell, pockets, compression, attachment)", "bag_side", "Exo K4 5000 bag only", 1077.0,
     "docs/research/published_weight_definitions.md 2.1 (Exo K4 5000, 'Bag Only: 2lb, 6oz')"),
    ("bag side (shell, pockets, compression, attachment)", "bag_side", "KUIU ICON 6 6000 bag", 1350.0,
     "docs/research/published_weight_definitions.md 2.1 (KUIU whitepaper)"),
    ("hipbelt", "belt", "Stone Glacier 3-piece belt", 363.0, "docs/research/hipbelt_fit.md 3 (SG 3-Piece Belt)"),
    ("load spreader / cross stays", "spreader", "Seek Outside 7075 cross stays (pair)", 113.0,
     "docs/research/spreader_research.md (Seek Outside Revolution, fetched)"),
    ("frame structure (stays, crown, torso adjust; no belt, harness, back)", "frame", "KUIU ICON 6 frame, tall",
     388.0, "docs/research/bag_attachment_research.md (KUIU ICON 6: 13.7 oz tall)"),
]


def _spreader_g(rows: list) -> float:
    return sum(r["g"] for r in rows if r["system"] == "back" and r["name"].startswith("back-system spreader"))


def system_table(size: str = "M") -> dict:
    """After-tests base by system, BL-008 split and the per-function comparison."""
    rows = W.cfg_rows(baseline_rows(size), "base")
    bs = L.by_system(rows)
    hip = sum(r["g"] for r in rows if r["system"] == "belt" and "IMP-5L" in r["name"])
    groups = {"frame_side": sum(bs.get(s, 0.0) for s in FRAME_SIDE) - hip,
              "bag_side": sum(bs.get(s, 0.0) for s in BAG_SIDE_8),
              "unsplit": bs.get("misc", 0.0) + hip, "spreader": _spreader_g(rows)}
    for s in bs:
        groups.setdefault(s, bs[s])
    fn = []
    for func, key, leader, g, src in LEADER_FN:
        ours = groups[key]
        fn.append({"function": func, "ours_key": key, "ours_g": round(ours, 1), "leader": leader, "leader_g": g,
                   "over_g": round(ours - g, 1), "ratio": round(ours / g, 2), "source": src})
    worst = {}
    for f in fn:   # per function: the excess over the lightest leader
        if f["function"] not in worst or f["leader_g"] < worst[f["function"]]["leader_g"]:
            worst[f["function"]] = f
    ranked = sorted(worst.values(), key=lambda f: -f["ratio"])
    return {"by_system": {k: round(v, 1) for k, v in sorted(bs.items(), key=lambda kv: -kv[1])},
            "groups": {k: round(v, 1) for k, v in groups.items()}, "functions": fn,
            "ranked_vs_lightest": [{"function": f["function"], "ratio": f["ratio"], "over_g": f["over_g"],
                                    "leader": f["leader"]} for f in ranked],
            "total_base_g": round(sum(bs.values()), 1)}


# =====================================================================================================================
# 2. candidate levers (grams from records or from the owning module's code)
# =====================================================================================================================
def _HD():
    return W._HD()


def _combo(keys: tuple):
    """hipbelt_diet design with the given items applied on belt B (same rule as hipbelt_diet.package_design)."""
    from dataclasses import replace
    HD = _HD()
    d = HD.B
    for k in keys:
        if k not in HD.DESIGNS:
            continue
        v = HD.DESIGNS[k]()
        for fld in ("stiff_t", "stiff_tip_gap", "wing_foam", "crest_foam", "lumbar_foam", "lumbar_taper_tan"):
            if getattr(v, fld) != getattr(HD.B, fld):
                d = replace(d, **{fld: getattr(v, fld)})
    return d


BELT_PICK = ("d2", "d4", "d3", "c3")      # on top of the BL-006 package (a2, b, c2, e, f1, f2); c3 replaces c2


@functools.lru_cache(maxsize=None)
def belt_check() -> dict:
    """hipbelt_diet's fit model (16 ANSUR II forms) on the BL-006 package and on the package with BL-037's belt items;
    gates as BL-006: worst wing peak <= belt B, worst hold >= belt B; lumbar watched against 48.6 kPa."""
    HD = _HD()
    pk = tuple(HD.PACKAGE)
    new = tuple(k for k in pk if k != "c2") + BELT_PICK
    out = {}
    for name, keys in (("package", pk), ("package + BL-037", new)):
        r = HD.evaluate(_combo(keys))
        r.pop("rows")
        out[name] = {k: round(float(v), 3) for k, v in r.items()}
    p = out["package + BL-037"]
    out["limits"] = {"worst_wing_kpa": HD.WING_WORST_LIMIT, "worst_hold": HD.HOLD_WORST_LIMIT,
                     "lumbar_watch_kpa": HD.LUMBAR_WATCH}
    out["passes"] = (p["worst_wing_kpa"] <= HD.WING_WORST_LIMIT + 1e-9 and p["worst_hold"] >= HD.HOLD_WORST_LIMIT - 1e-9
                     and p["worst_lumbar_kpa"] <= HD.LUMBAR_WATCH)
    return out


def belt_items(size: str = "M") -> dict:
    HD = _HD()
    return {"d2": HD._mass_delta("d2", size), "d4": HD._mass_delta("d4", size), "d3": HD._mass_delta("d3", size),
            "c3_vs_c2": HD._mass_delta("c3", size) - HD._mass_delta("c2", size)}


def back_strip() -> dict:
    """BL-005 sandwich strip with a 2 mm ROHACELL 71 core (row b_swR71c2_70) in place of the 3 mm core (recommended
    b_swR71c3_70): back_system2.mass_delta_g on both; the pass flags are back_system2's own rows
    (back_system_integration.md section 4: skin 13.49 kPa <= 13.8, strip SF 1.89 / fatigue 4.42, air 14.5 / 8.6 / 5.1 mm)."""
    from huntkit.gendesign import back_system2 as BS2
    new, rec = "b_swR71c2_70", BS2.RECOMMENDED
    g_new = BS2.mass_delta_g(BS2._variant(new))["total"]
    g_rec = BS2.mass_delta_g(BS2._variant(rec))["total"]
    return {"key": new, "recommended": rec, "delta_g": g_new - g_rec}


def strap_area_mm2(sa: float = 0.0) -> float:
    """One J-strap piece: the trapezoid, plus a seam allowance band (perimeter x sa + pi sa^2) for the fabric pieces."""
    a = HS_L * (HS_WT + HS_WB) / 2.0
    if not sa:
        return a
    side = math.hypot(HS_L, (HS_WT - HS_WB) / 2.0)
    per = 2 * side + HS_WT + HS_WB
    return a + per * sa + math.pi * sa * sa


def j_strap_breakdown() -> dict:
    """The J-strap pair as build_geometry books it (2 x shell 330D + spacer mesh face + EVA 45C 5 mm load foam +
    perforated EVA 5 mm comfort foam), and the BL-037 load-foam swap to XLPE L200 5 mm (record)."""
    af, aw = strap_area_mm2() * 1e-6, strap_area_mm2(HS_SA) * 1e-6
    t = HS_FOAM_T * 1e-3
    shell = 2 * aw * _p("cordura_330d_nylon66", "areal_density_gsm")
    mesh = 2 * aw * _p("spacer_mesh_3d", "areal_density_gsm")
    load_eva = 2 * af * t * _p("eva_foam_45c", "density_kg_m3") * 1000
    comfort = 2 * af * t * _p("eva_foam_perforated", "density_kg_m3") * 1000
    load_xlpe = 2 * af * t * _p("xlpe_foam_l200", "density_kg_m3") * 1000
    return {"shell_g": shell, "mesh_g": mesh, "load_foam_eva_g": load_eva, "comfort_g": comfort,
            "total_g": shell + mesh + load_eva + comfort, "load_foam_xlpe_g": load_xlpe,
            "delta_g": load_xlpe - load_eva,
            "booked_g": W.misc_thread()["soft_goods_g"]["harness_J"]}


def sternum() -> dict:
    f, s = _p("fidlock_magnetic_buckle_25mm", "mass_g"), _p("buckle_side_release_25mm", "mass_g")
    return {"fidlock_g": f, "side_release_g": s, "delta_g": s - f,
            "fidlock_break_n": _p("fidlock_magnetic_buckle_25mm", "breaking_strength_n"),
            "side_release_break_n": _p("buckle_side_release_25mm", "breaking_strength_n")}


def door_sliders() -> dict:
    g10 = _p("slider_10", "mass_g")
    return {"slider_g": g10, "cord_pull_g": SLIDER_CORD_G, "n": 2, "delta_g": 2 * (SLIDER_CORD_G - g10),
            "one_slider_delta_g": -g10}


def _row(rows: list, prefix: str, system: str | None = None) -> float:
    return sum(r["g"] for r in rows if r["name"].startswith(prefix) and (system is None or r["system"] == system))


def camo_swap(size: str = "M") -> dict:
    """Camo accents from polyester_ht_630d_printable (290 gsm, ESTIMATE record) to polyester_300d_printable (HyperD 300,
    133 gsm, datasheet): the D2 blade U B-02u, the slider garage SH-07 and the belt wing-tip shards SH-05. The kick
    bands SH-01b stay 630D (ground abrasion)."""
    # SH-05 from the ledger (not the roll-up: the roll-up calls this function to build its A_bl037 step)
    led = L.parts(L.DEFAULT_CONFIG, size)
    f = 1.0 - _p("polyester_300d_printable", "areal_density_gsm") / _p("polyester_ht_630d_printable", "areal_density_gsm")
    with W.rev():
        bag = L.adopted_bag_rows(size)
    pieces = {"B-02u": _row(bag, "B-02u"), "SH-07": _row(bag, "SH-07"),
              "SH-05": sum(r["g"] for r in led if r["system"] == "belt" and "SH-05" in r["name"])}
    return {"pieces_g": {k: round(v, 2) for k, v in pieces.items()}, "factor": f,
            "delta_g": -f * sum(pieces.values()), "kept_630d": ["SH-01b kick bands"]}


def bushings() -> dict:
    from huntkit.gendesign import crown_diet as CD
    return {"delta_g": CD.bushing_g(16.0, 1.0, 50.0) - CD.bushing_g(16.0, 1.0, 70.0),
            "ring_crush_sf": 1.67, "source": "crown_diet.md (e): ring crush 2.33 -> 1.67, bearing 12.6"}


def labels() -> dict:
    lg = W.misc_thread()["labels_g"]
    return {"booked_g": lg, "printed_g": LABEL_PRINTED_G, "delta_g": LABEL_PRINTED_G - lg}


def ti_joint_hardware() -> dict:
    """Option: the z 234 joint's A2 washers and nuts in Ti 6Al-4V (density ratio of the records)."""
    j = json.loads((ANALYSIS / "frame_mass_h1.json").read_text())["h1"]["joint_hardware_g"]
    steel = sum(v for k, v in j.items() if "A2" in k)
    f = 1.0 - _p("ti_6al_4v", "density_kg_m3") / _p("sst_304_annealed", "density_kg_m3")
    return {"a2_g": steel, "delta_g": -f * steel}


def door_zip8() -> dict:
    """Option: door chain #10 -> #8 (record g/m), sliders unchanged (no #8 slider record: materials-engineer)."""
    with W.rev():
        z = next(r for r in L.adopted_bag_rows("M") if "door zip" in r["name"])
    from bag_concepts import SLIDER_G
    length_m = (z["g"] - 2 * SLIDER_G) / _p("coil_zipper_10", "mass_g_m")
    return {"length_m": length_m, "delta_g": -length_m * (_p("coil_zipper_10", "mass_g_m") - _p("coil_zipper_8", "mass_g_m")),
            "crosswise_10_n": float(REC["coil_zipper_10"].get("crosswise_strength_n")),
            "crosswise_8_n": float(REC["coil_zipper_8"].get("crosswise_strength_n"))}


def cams_to_ladders() -> dict:
    """Owner-rule option: the five Al cams (IM1-IM3, US1/US2) -> heavy 25 mm ladder locks (records)."""
    c, l_ = _p("cam_25mm_al", "mass_g"), _p("ladder_lock_25mm_heavy", "mass_g")
    return {"n": 5, "delta_g": 5 * (l_ - c)}


def release_cord() -> dict:
    from huntkit.gendesign import crown_diet as CD
    return {"delta_g": -(CD.TORSO_ADJUST_ROW_G - CD.WEBBING_G_M * CD.PULLEY_WEB_M - CD.CAM_G)}


# ---- frame-side levers that need the structural record --------------------------------------------------------------
F1_RUN = "bl037_h1a0_m1_u2.5_im3"     # outputs/h1_buckling/check_<name>.json (h1_buckling.full_check, run here)


def spreader_share() -> dict:
    """The 'spreader load-share, about 22 g' lever (BL-027 4.2 item 1), re-read from BL-027's own decomposition
    (analysis/h1_buckling.json task1, H1-G0.55 body): the margins if every cinch push reached the stays, set by set."""
    d = json.loads((ANALYSIS / "h1_buckling.json").read_text())
    dec, ch = d["task1"]["decomposition"], d["chosen"]
    rows = []
    for key, v in dec.items():
        for m, r in v["members"].items():
            if r["N_cinch_via_stays"] < 0:
                rows.append({"set": key, "member": m, "N_full": round(r["N_full"], 1),
                             "N_via_stays": round(r["N_cinch_via_stays"], 1),
                             "margin_via_stays": round(r["Pcr_n"] / (1.5 * -r["N_cinch_via_stays"]), 3)})
    worst_mid = min((x for x in rows if x["member"].startswith("mid bar")), key=lambda x: x["margin_via_stays"])
    mm, m0 = ch["member_mass_g"], ch["member_mass_g055_g"]
    return {"rows": rows, "worst_mid_bar": worst_mid,
            "members_added_g": ch["members_added_g"],
            "branch_growth_g": mm["branch"] - m0["branch"], "mid_growth_g": mm["mid"] - m0["mid"],
            "upper_only_saving_g": -(mm["branch"] - m0["branch"]),
            "verdict": ("the mid bar needs its growth whatever the spreader does: the fill hipbelt-off abuse set (no cinch) "
                        f"gives {worst_mid['margin_via_stays']:.2f} on the H1-G0.55 mid bar"
                        if worst_mid["margin_via_stays"] < 1.0 else "mid bar passes via the stays")}


def ca1_check(results: dict | None = None) -> dict:
    """CA-1 at 0.40: what it buys on H1 as adopted. Run here: the BL-027 members on plain H1 (the BL-024 G0.55 growth
    taken off, 28 mm IM3 cheeks kept), every rev C body check (h1_buckling.full_check). Fatigue scales with the ratio
    (FI99 margin is linear in the allowable), so the 0.40 margin = 0.30 margin x 0.40 / 0.30; buckling, strength and
    creep do not move with CA-1."""
    if results is None:
        p = ROOT / "outputs" / "h1_buckling" / f"check_{F1_RUN}.json"
        results = json.loads(p.read_text()) if p.exists() else None
    if results is None:
        # a fresh session has no outputs/: keep the record written when the run was made
        return json.loads(RESULT.read_text())["ca1"] if RESULT.exists() else {"available": False}
    ch = json.loads((ANALYSIS / "h1_buckling.json").read_text())["chosen"]
    k = 0.40 / 0.30
    out = {"available": True, "body_g": results["raster_g"], "delta_g": results["raster_g"] - ch["body_raster_g"],
           "bases": {}}
    for b in ("fine_sm8", "fine", "beam", "fine_sm8.cyc"):
        if b in results:
            r = results[b]
            out["bases"][b] = {"strength": round(r["min"]["strength"], 3), "fatigue_030": round(r["min"]["fatigue"], 3),
                               "fatigue_040": round(r["min"]["fatigue"] * k, 3), "creep": round(r["min"]["creep"], 3),
                               "buckling": r["buckling_min"], "mirrored": r["buckling_mirrored"],
                               "joint": [round(r["joint_strength"], 2), round(r["joint_fatigue"], 2)]}
    bk = [v["buckling"] for v in out["bases"].values()]
    mir = [x for v in out["bases"].values() for x in v["mirrored"].values() if x is not None]
    out["buckling_min"] = min(bk) if bk else None
    out["mirrored_min"] = min(mir) if mir else None
    out["passes_buckling"] = bool(bk) and min(bk) >= 1.0 and min(mir) >= 1.0
    out["sizing"] = ca1_sizing(ch["body_raster_g"])
    return out


F1_SIZING = ((1.4, 3.5),)   # member re-growth tried on plain H1 (h1_buckling.body_solid alpha 0), fine_sm8


def ca1_sizing(chosen_g: float) -> list:
    """Member re-growth on the F-1 body (fine_sm8 axial runs, h1_buckling.axial_eval, cached in outputs/h1_buckling)."""
    import pickle
    from huntkit.gendesign import h1_buckling as B
    out = []
    for dm, du in F1_SIZING:
        p = ROOT / "outputs" / "h1_buckling" / f"axial_bl037_a0_m{dm:g}_u{du:g}_im3.fine_sm8.pkl"
        if not p.exists():
            continue
        r = pickle.loads(p.read_bytes())
        m = {k: v["margin"] for k, v in r["margins"].items()}
        mir = B.mirrored(r["axial"])
        lo = min([x for x in m.values() if x is not None] + [x for x in mir.values() if x is not None])
        out.append({"d_mid": dm, "d_up": du, "raster_g": round(float(r["raster_g"]), 2),
                    "delta_g": round(float(r["raster_g"]) - chosen_g, 2), "margins": m, "mirrored": mir,
                    "min": round(lo, 3), "passes_buckling_fine_sm8": lo >= 1.0})
    return out


def c17_under_ca1() -> dict:
    """Option: BL-017's OD 17 legs come back only with CA-1 >= 0.40 (retired at 0.30, body fatigue 0.97-0.99)."""
    return {"delta_g": W.crown("(a)+(d2)+(c17 bore 19)") - W.crown("(a)+(d2)")}


def cheek_risk() -> dict:
    hb = L.h1_body_update()
    return {"standalone_g": W.cheek_g(), "booked_g": hb["im3_cheek_28_g"], "risk_g": W.cheek_g() - hb["im3_cheek_28_g"]}


# =====================================================================================================================
# the lever table
# =====================================================================================================================
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
REQUIRED = {"IMP-2": "hydration (DESIGN requirement)", "IMP-5L": "hipbelt pockets (DESIGN requirement)",
            "E-5": "trekking pole / tripod carry (DESIGN requirement)", "B-11 lash": "rifle carry (DESIGN requirement)",
            "IMP-8": "bow carry (owner-frozen)", "US-": "under-straps (owner-frozen)"}


def levers(size: str = "M", ca1: dict | None = None) -> list:
    """Every candidate: key, system, change, g (base, belt M; negative saves), status (pick / option / owner /
    rejected / risk), risk, gate, check, owner-rule effect, build-hours effect, source."""
    bi, j, st, ds, cm = belt_items(size), j_strap_breakdown(), sternum(), door_sliders(), camo_swap(size)
    bk, bu, lb_ = back_strip(), bushings(), labels()
    sp, c17, ti, z8 = spreader_share(), c17_under_ca1(), ti_joint_hardware(), door_zip8()
    cams, rc, ck = cams_to_ladders(), release_cord(), cheek_risk()
    ca1 = ca1 if ca1 is not None else ca1_check()
    bc = belt_check()
    hours0 = "0 (same pieces and ops; a material or bought-part swap)"
    L_ = []

    def add(**k):
        k.setdefault("hours", hours0)
        k["g"] = None if k.get("g") is None else round(float(k["g"]), 1)
        L_.append(k)

    # ---- picks (class A: each gated by a named test, the present part is the fallback) -------------------------------
    p = bc["package + BL-037"]
    add(key="B-1", system="belt", status="pick", risk="low",
        change="wing load foam + lumbar firm foam EVA 45C 6 mm -> XLPE L200 6 mm (BL-006 d2 + d4, the 'belt-foam reserve')",
        g=bi["d2"] + bi["d4"], gate="HB-1 (3 testers) + CS-1 compression set of L200 at 50 % for 22 h",
        check=f"hipbelt fit model, 16 ANSUR II forms, package + BL-037: worst wing {p['worst_wing_kpa']} kPa (limit "
              f"{bc['limits']['worst_wing_kpa']}), worst hold {p['worst_hold']} (>= {bc['limits']['worst_hold']}), lumbar "
              f"worst {p['worst_lumbar_kpa']} (watch {bc['limits']['lumbar_watch_kpa']}): PASS",
        owner="none", source="hipbelt_diet._mass_delta('d2'/'d4'); xlpe_foam_l200 record (datasheet)")
    add(key="B-2", system="belt", status="pick", risk="medium",
        change="wing stiffener HDPE 0.75 -> 0.5 mm (BL-006 c3 in place of c2)", g=bi["c3_vs_c2"],
        gate="HB-D2 wing roll-over, built at 0.5 and 0.75 mm side by side; keep the thinner that passes",
        check="same fit-model run (c3 in the package): PASS; 0.5 mm keeps 12.5 % of 1.0 mm's bending stiffness, which "
              "the model cannot judge (hence the gate)",
        owner="none", source="hipbelt_diet._mass_delta('c3') - _mass_delta('c2')")
    add(key="B-3", system="belt", status="pick", risk="low", change="wing comfort foam EVA 30C 5 -> 4 mm (BL-006 d3)",
        g=bi["d3"], gate="HB-1", check="same fit-model run: PASS", owner="none",
        source="hipbelt_diet._mass_delta('d3')")
    add(key="K-1", system="back", status="pick", risk="low",
        change="BL-005 backer strip core ROHACELL 71 3 mm -> 2 mm (row b_swR71c2_70)", g=bk["delta_g"],
        gate="BP-1 three-point bend coupon at the 2 mm core + BP-2 (already planned for the strip)",
        check="back_system2 row b_swR71c2_70: skin 13.49 kPa (<= 13.8), strip SF 1.89 factored, fatigue 4.42, air "
              "walk / factored / lean 14.5 / 8.6 / 5.1 mm, gutter 110: PASS (back_system_integration.md 4)",
        owner="none", source="back_system2.mass_delta_g (both rows)")
    add(key="H-1", system="harness", status="pick", risk="medium",
        change="J-strap load foam EVA 45C 5 mm -> XLPE L200 5 mm (comfort layer, shell and mesh unchanged)",
        g=j["delta_g"],
        gate="HS-1 shoulder pressure strips (kit D FSRs) at 30 kg and 68 kg, 3 testers, against today's EVA strap on "
             "the other shoulder; + CS-1 compression set",
        check="no paper model of shoulder pressure exists in huntkit (stated, not run); the belt model shows XLPE L200 "
              "lowering peaks as a load layer (BL-006 d2), the same record",
        owner="none", source="j_strap_breakdown(): build_geometry strap outline x eva_foam_45c / xlpe_foam_l200 density")
    add(key="H-2", system="harness", status="pick", risk="low",
        change="sternum buckle Fidlock 25 mm magnetic -> 25 mm side-release (records)", g=st["delta_g"],
        gate="ST-1 gloved one-hand sternum clip-on, 10 tries (R-06 fit trial session); fallback the Fidlock",
        check=f"side-release break {st['side_release_break_n']:.0f} N vs Fidlock {st['fidlock_break_n']:.0f} N "
              "(stronger); the sternum is not on an HA-LS-1 load path",
        owner="QUICK hardware family (build_geometry) loses its magnetic sternum; quiet rule unaffected (both click)",
        source="fidlock_magnetic_buckle_25mm, buckle_side_release_25mm records")
    add(key="G-1", system="bag_shell", status="pick", risk="low",
        change="D2 door sliders: #10 slider body with the door cord pull in place of the metal tab (2)", g=ds["delta_g"],
        gate="SL-1 weigh 5 sliders on receipt; gloved open / close x 20", check="mass only (the door zip is unloaded: "
        "strap_arch 0.45 N/mm vs 35.4 N/mm crosswise); quieter (record: a bare metal pull taps the body)",
        owner="none (quiet rule helped)", source=f"slider_10 record {ds['slider_g']} g; ASSUMPTION SLIDER-CORD {SLIDER_CORD_G} g")
    add(key="G-2", system="bag_shell + belt", status="pick", risk="medium",
        change="camo accents 630D printable -> HyperD 300 printable on B-02u blades, SH-07 garage, SH-05 belt shards "
               "(kick bands SH-01b stay 630D)", g=cm["delta_g"],
        gate="AB-1: Martindale (ASTM D4966) both fabrics to 8000 rev + a brush-drag strip on the blade edge; owner "
             "print swatch of the camo on HyperD 300; fallback 630D",
        check="the zip is sewn to the blade but carries no load (SF 78 on the #10 chain); HyperD 300 seam 42-52 lbf "
              "(record) is above any blade load; 630D record is an ESTIMATE",
        owner="camo stays an accent (rule unchanged); colour match to be judged on the swatch",
        source="polyester_300d_printable / polyester_ht_630d_printable gsm x corrie_f rows")
    add(key="F-3", system="frame", status="pick", risk="low", change="crown UHMWPE bushings 70 -> 50 mm (crown_diet (e))",
        g=bu["delta_g"], gate="BU-1 slide trial: kit change and pawl travel with 50 mm bushings (L/D 2.8), 20 cycles "
        "gloved; fallback 70 mm", check=f"crown_diet (e): ring crush SF {bu['ring_crush_sf']} (from 2.33), bearing 12.6; "
        "beam loads unchanged; the voxel body spreads each bushing force over 40 mm, so the body is unchanged",
        owner="none (crown kits unchanged)", source="crown_diet.bushing_g (pack5200.hardware_mass formula)")
    add(key="X-1", system="misc", status="pick", risk="low", change="woven label set -> one printed label on the liner",
        g=lb_["delta_g"], gate="SL-1 weigh the label set", check="mass only; both masses are ASSUMPTIONs",
        owner="none", source=f"geometry.yaml labels_g {lb_['booked_g']} g (ASSUMPTION); ASSUMPTION LABEL {LABEL_PRINTED_G} g",
        hours="-0.1 h (one heat press instead of three sewn labels; ASSUMPTION)")

    # ---- frame-side options that need more than a paper check ------------------------------------------------------
    if ca1.get("available"):
        cb = ca1["bases"]
        f040 = min(v["fatigue_040"] for k, v in cb.items() if not k.endswith(".cyc"))
        cyc = cb.get("fine_sm8.cyc", {}).get("fatigue_040")
        sz = ca1.get("sizing") or []
        net = max((s["delta_g"] for s in sz), default=None)       # the lightest re-grown body tried (an upper bound)
        sz_txt = "; ".join(f"re-grown mid +{s['d_mid']:g} / upper +{s['d_up']:g} mm: {s['delta_g']:+.1f} g, min "
                           f"{s['min']:.3f} ({'pass' if s['passes_buckling_fine_sm8'] else 'fails: the load moves to the lower branches'})"
                           for s in sz)
        add(key="F-1", system="frame", status="option", risk="high",
            change="CA-1 >= 0.40: take BL-024's G0.55 growth off (BL-027 members and 28 mm cheeks kept, members re-grown)",
            g=net if net is not None else ca1["delta_g"],
            gate="CA-1 at 0.40 AND MT-1 shows the cinch static (cycled bound below) AND a converged member re-sizing",
            check=(f"run here (h1_buckling.full_check, 4 bases) on plain H1 + BL-027 members: {ca1['delta_g']:+.1f} g gross, "
                   f"fatigue at 0.40 {f040:.2f} static, {cyc if cyc is not None else 'n/a'} cinch cycled (fails if MT-1 "
                   f"shows cycling); Euler buckling {ca1['buckling_min']:.3f} (mirrored {ca1['mirrored_min']:.3f}) < 1.0: "
                   f"FAILS as it stands. {sz_txt}. So the net is at most the figure shown, not -50 to -70 g"),
            owner="none", source=f"outputs/h1_buckling/check_{F1_RUN}.json and axial_bl037_a0_*.pkl (this ticket)")
    add(key="F-2", system="frame", status="option", risk="high",
        change="spreader load share: take the BL-027 upper-branch growth off (the mid-bar growth must stay)",
        g=sp["upper_only_saving_g"],
        gate="SPREADER_MAP: a Sandwich v2 plate run on the H1 supports with the cinch preload, then puck load cells / "
             "branch strain gauges in the T2 meat test",
        check=sp["verdict"] + f"; so at most the upper-branch {-sp['upper_only_saving_g']:.1f} g of the "
              f"{sp['members_added_g']:.1f} g comes back, and only if the plate run shows the share",
        owner="none", source="analysis/h1_buckling.json task1 decomposition + chosen member masses")
    add(key="F-4", system="frame", status="option", risk="medium",
        change="z 234 joint: A2 washers and nuts -> Ti 6Al-4V (8 washers, 4 nuts)", g=ti["delta_g"],
        gate="needs Ti washer / nut records (materials-engineer) and a joint re-check (frame_h1.joint_check, bearing on "
             "PAHT); anti-seize for Ti on Ti", check="not run (no record)", owner="none",
        source="frame_mass_h1.json joint_hardware_g x (1 - rho Ti / rho A2) (ti_6al_4v, sst_304 records)")
    add(key="F-5", system="frame", status="option", risk="high",
        change="frame print parameters: sparse (gyroid) infill inside thick low-stress regions of the H1 body",
        g=None, gate="new coupon series (CA-1 style) at the chosen infill, then the whole body FEA with the reduced "
        "stiffness and allowables", check="not estimable without coupons; the booked body is solid raster x 1060 "
        "kg/m3 (record) and the roll-up already bands it +-5 %; weighing the printed halves settles the booking, it is "
        "not a lever", owner="none", source="pa12_cf_fdm_paht record; weight_rollup_v2 section 6")
    add(key="F-6", system="frame", status="option", risk="high",
        change="stays: BL-017 OD 17 x 7 crown legs in a 19 mm bore (retired at 0.30) back with CA-1 >= 0.40",
        g=c17["delta_g"], gate="CA-1 >= 0.40 and a body re-run with F-1 (not stacked here)",
        check="retired: body fatigue 0.97-0.99 on the sim loads at 0.30 (BL-021 (4)); x 1.33 at 0.40 if CA-1 passes; "
              "not re-run with F-1", owner="none", source="crown_diet.option_mass via weight_rollup_v2.crown")
    add(key="G-3", system="bag_shell", status="option", risk="low",
        change="door chain #10 -> #8 coil (sliders unchanged until a #8 slider record exists)", g=z8["delta_g"],
        gate="needs a slider_8 record (materials-engineer) and PT-7 door zip proof on #8",
        check=f"#8 crosswise {z8['crosswise_8_n']:.0f} N vs #10 {z8['crosswise_10_n']:.0f} N (records, ESTIMATE); the "
              "door zip is unloaded (SF 78 on #10, about 61 on #8)", owner="none",
        source="coil_zipper_10 / coil_zipper_8 records x door zip length")

    # ---- owner options (feature or owner-rule changes; listed, not adopted) ------------------------------------------
    fc = W.feature_costs(size)
    for c in fc["candidates"]:
        req = REQUIRED.get(c["item"])
        add(key="O-" + c["item"].replace(" lash", ""), system="feature", status="owner", risk="low",
            change=f"move to an add-on: {c['what']}", g=-c["g"], gate="owner decision",
            check="no structural effect", owner=req or "feature loss (not frozen, not a DESIGN requirement)",
            source="weight_rollup_v2.feature_costs (CORRIE F base rows)", hours=_feature_hours(c["item"]))
    add(key="O-cams", system="straps_meat", status="owner", risk="medium",
        change="IM1-IM3 and US1/US2 aluminium cams -> heavy 25 mm ladder locks", g=cams["delta_g"],
        gate="owner decision (aluminium cams are owner-fixed) + MT-1..3 with ladder locks",
        check="ladder_lock_25mm_heavy mass is an ASSUMPTION in its record", owner="changes 'aluminium cams' (DECISIONS)",
        source="cam_25mm_al, ladder_lock_25mm_heavy records")
    add(key="O-cord", system="frame", status="owner", risk="low",
        change="drop the torso release cord + toggle (adjust with the pack off)", g=rc["delta_g"],
        gate="owner decision", check="no structural effect (crown_diet section 7)", owner="no on-body lengthening",
        source="crown_diet.TORSO_ADJUST_ROW_G - webbing - cam")
    add(key="O-slider", system="bag_shell", status="owner", risk="low",
        change="D2 door with one slider instead of two (on top of G-1)", g=-SLIDER_CORD_G,
        gate="owner decision", check="no structural effect", owner="door opens from one side only (no top peek)",
        source="ASSUMPTION SLIDER-CORD")

    # ---- rejected --------------------------------------------------------------------------------------------------
    for key, system, change, why in (
            ("R-1", "straps_meat", "IM fairlead eyes 38 -> 25 mm webbing",
             "the eyes are captive in the printed fairlead slots (released H1 print) and take the 38 mm bag hooks"),
            ("R-2", "bag_shell", "roll-top HDPE strip thinner", "already 0.8 mm (bag_concepts.HDPE_T)"),
            ("R-3", "back", "lighter spreader core", "Sandwich v2 is at FPF 1.25 / fatigue 1.09 / sandwich 1.11 "
             "(owner decision, 7 mm core); no lighter row passes"),
            ("R-4", "bag", "DCF hybrid / laminates on the shell", "crinkle: breaks the quiet rule (owner-frozen)"),
            ("R-5", "harness + back", "lighter spacer mesh on straps and back", "no lighter breathable spacer record; "
             "ask the materials-engineer for one (back mesh 67.6 g, strap faces 29.7 g)"),
            ("R-6", "harness + belt", "yoke plate / 7075 belt plate thinner", "both are rev C fixes (C-7, C-1..3)"),
            ("R-7", "frame", "fixed torso", "retired: fatigue below 1.0 on the sim loads; owner keeps three crown kits")):
        add(key=key, system=system, status="rejected", risk="-", change=change, g=None, gate="-", check=why,
            owner="-", source="-", hours="-")
    add(key="RISK-cheek", system="frame", status="risk", risk="-",
        change="28 mm IM3 cheek booking: stand-alone fairlead volume vs the raster share", g=ck["risk_g"],
        gate="weigh the two printed halves against the slicer", check="adds up to this much; never saves",
        owner="-", source="weight_rollup_v2.cheek_g - ledger.h1_body_update im3_cheek_28_g", hours="-")
    return L_


def _feature_hours(item: str) -> str:
    """Beginner hours of the ops that build a feature (build_effort_rev3.json, op names containing its id)."""
    ops = json.loads((ANALYSIS / "build_effort_rev3.json").read_text())["ops"]
    needle = {"FP-L/R": "FP-", "B-11 lash": "B-11"}.get(item, item)
    h = sum(o["hours"] for o in ops if needle in o["op"])
    return f"-{h:.1f} h (build_effort_rev3 ops naming {needle})" if h else "not in the bag op list"


def picks(lv: list) -> list:
    return [x for x in lv if x["status"] == "pick"]


def picked_rows(size: str = "M") -> list:
    """Roll-up rows (ledger schema) of the BL-037 picks, step ``A_bl037``. Each pick at its own system."""
    bi, j, st, ds = belt_items(size), j_strap_breakdown(), sternum(), door_sliders()
    cm, bk, bu, lb_ = camo_swap(size), back_strip(), bushings(), labels()
    f = cm["factor"]
    src = "weight_push (BL-037): "
    rows = [
        W._r("belt", "BL-037 B-1: wing load foam EVA 45C -> XLPE L200 6 mm (BL-006 d2)", bi["d2"], "base",
             src + "hipbelt_diet._mass_delta('d2')", STEP),
        W._r("belt", "BL-037 B-1: lumbar firm foam EVA 45C -> XLPE L200 6 mm (BL-006 d4)", bi["d4"], "base",
             src + "hipbelt_diet._mass_delta('d4')", STEP),
        W._r("belt", "BL-037 B-2: wing stiffener 0.75 -> 0.5 mm (c3 in place of c2)", bi["c3_vs_c2"], "base",
             src + "hipbelt_diet._mass_delta('c3') - ('c2')", STEP),
        W._r("belt", "BL-037 B-3: wing comfort foam EVA 30C 5 -> 4 mm (BL-006 d3)", bi["d3"], "base",
             src + "hipbelt_diet._mass_delta('d3')", STEP),
        W._r("back", "BL-037 K-1: backer strip core R71 3 -> 2 mm (b_swR71c2_70)", bk["delta_g"], "base",
             src + "back_system2.mass_delta_g", STEP),
        W._r("harness", "BL-037 H-1: J-strap load foam EVA 45C -> XLPE L200 5 mm (pair)", j["delta_g"], "base",
             src + "build_geometry J-strap outline x foam records", STEP),
        W._r("harness", "BL-037 H-2: sternum Fidlock -> 25 mm side-release", st["delta_g"], "base",
             src + "fidlock / buckle_side_release_25mm records", STEP),
        W._r("bag_shell", "BL-037 G-1: D2 door sliders with cord pulls (2)", ds["delta_g"], "base",
             src + "slider_10 record - ASSUMPTION SLIDER-CORD", STEP),
        W._r("bag_shell", "BL-037 G-2: B-02u + SH-07 camo 630D -> HyperD 300",
             -f * (cm["pieces_g"]["B-02u"] + cm["pieces_g"]["SH-07"]), "base", src + "gsm ratio of the records", STEP),
        W._r("belt", "BL-037 G-2: SH-05 belt camo shards 630D -> HyperD 300", -f * cm["pieces_g"]["SH-05"], "base",
             src + "gsm ratio of the records", STEP),
        W._r("frame", "BL-037 F-3: crown bushings 70 -> 50 mm", bu["delta_g"], "base", src + "crown_diet.bushing_g", STEP),
        W._r("misc", "BL-037 X-1: printed label in place of the woven set", lb_["delta_g"], "base",
             src + "geometry.yaml labels_g - ASSUMPTION LABEL", STEP),
    ]
    return rows


# =====================================================================================================================
# 3. the pick and whether it reaches the target
# =====================================================================================================================
def summary(lv: list, size: str = "M") -> dict:
    before = baseline_total(size)
    pk = picks(lv)
    pick_g = sum(x["g"] for x in pk)
    by_risk = {r: round(sum(x["g"] for x in pk if x["risk"] == r), 1) for r in ("low", "medium", "high")}
    after = before + pick_g
    gap_before = before - W.TARGET_G
    gap_after = after - W.TARGET_G
    opt = [x for x in lv if x["status"] == "option" and x["g"] is not None and x["g"] < 0]
    own = [x for x in lv if x["status"] == "owner" and x["g"] is not None and x["g"] < 0]
    free = sorted([x for x in own if x["owner"].startswith("feature loss")], key=lambda x: x["g"])
    acc, take = 0.0, []
    for x in free:            # lowest-risk route to the target after the picks: features nobody froze, largest first
        if after + acc <= W.TARGET_G:
            break
        acc += x["g"]
        take.append(x["key"])
    risk = sum(x["g"] for x in lv if x["status"] == "risk")
    left = after + acc - W.TARGET_G
    # single further items (an owner-rule / requirement change, or a frame option) that would close what is left
    closers = sorted([{"key": x["key"], "g": x["g"], "status": x["status"], "owner": x["owner"],
                       "margin_g": round(-x["g"] - left, 1), "with_cheek_risk_margin_g": round(-x["g"] - left - risk, 1)}
                      for x in opt + own if x["key"] not in take and -x["g"] >= left and "owner-frozen" not in x["owner"]], key=lambda c: -c["g"])
    return {"left_after_owner_route_g": round(left, 1), "closers": closers,"before_g": round(before, 1), "picks_g": round(pick_g, 1), "picks_by_risk": by_risk,
            "after_g": round(after, 1), "after_lb": round(after / LB, 2), "target_g": round(W.TARGET_G, 1),
            "gap_before_g": round(gap_before, 1), "gap_after_g": round(gap_after, 1),
            "ticket_g": TICKET_G, "met": -pick_g >= TICKET_G,
            "options_g": round(sum(x["g"] for x in opt), 1),
            "options_gross_note": "F-1 fails buckling as run; F-6 needs F-1; each needs CA-1 >= 0.40",
            "owner_free_features": [x["key"] for x in free], "owner_free_g": round(sum(x["g"] for x in free), 1),
            "owner_route_take": take, "owner_route_g": round(acc, 1),
            "owner_route_after_g": round(after + acc, 1), "owner_route_reaches": after + acc <= W.TARGET_G,
            "cheek_risk_g": round(risk, 1)}


# =====================================================================================================================
# plots
# =====================================================================================================================
COL = {"low": "#4f6b4a", "medium": "#b0793a", "high": "#9a3b3b", "owner": "#5b6f8f", "total": "#333333"}


def plot_waterfall(path: Path, lv: list, sm: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    bars = [("after tests before BL-037\n(roll-up v2, base, belt M)", sm["before_g"], "total", 0.0)]
    run = sm["before_g"]
    for x in sorted(picks(lv), key=lambda x: (RISK_ORDER[x["risk"]], x["g"])):
        bars.append((f"{x['key']} {x['change'][:46]}", x["g"], x["risk"], run))
        run += x["g"]
    bars.append(("= AFTER TESTS with the BL-037 picks", run, "total", 0.0))
    for x in [y for y in lv if y["status"] == "option" and y["g"] is not None and y["g"] < 0 and y["key"] in ("F-1", "F-2", "F-6")]:
        bars.append((f"option {x['key']} {x['change'][:40]}", x["g"], "high", run))
        run += x["g"]
    for k in sm["owner_route_take"]:
        x = next(y for y in lv if y["key"] == k)
        bars.append((f"owner {x['key']}: {x['change'][19:62]}", x["g"], "owner", run))
        run += x["g"]
    bars.append(("= only if CA-1 >= 0.40, MT-1 and the re-runs pass\nAND the owner moves these 3 features", run, "total", 0.0))
    fig, ax = plt.subplots(figsize=(8.6, 10.5), dpi=100)
    n = len(bars)
    for i, (t, d, k, b) in enumerate(bars):
        y = n - 1 - i
        if k == "total":
            ax.barh(y, d, color=COL["total"], height=0.7)
            ax.text(d + 4, y, f"{d:.0f} g  {d / LB:.2f} lb", va="center", fontsize=9, fontweight="bold")
        else:
            lo, w = (b + d, -d) if d < 0 else (b, d)
            ax.barh(y, w, left=lo, color=COL[k], height=0.6, alpha=0.95 if k != "high" else 0.55,
                    hatch="//" if k == "high" else None)
            ax.text(b + 4, y, f"{d:+.1f}", va="center", fontsize=8)
        ax.text(2895, y, t, va="center", ha="right", fontsize=7.4)
    ax.axvline(W.TARGET_G, color="#b22222", lw=1.6, ls="--")
    ax.text(W.TARGET_G + 3, -1.4, f"6.6 lb target {W.TARGET_G:.0f} g", color="#b22222", fontsize=8)
    ax.set_xlim(2900, sm["before_g"] + 60)
    ax.set_ylim(-1.8, n)
    ax.set_yticks([])
    ax.set_xlabel("pack mass, base configuration, belt M (g)")
    fig.suptitle(f"BL-037 weight push: {sm['before_g']:.0f} -> {sm['after_g']:.0f} g after tests "
                 f"({-sm['picks_g']:.0f} g picked, ticket {TICKET_G:.0f} g)\nhatched = options that need CA-1 / more "
                 "runs; blue = owner feature moves (not adopted)", x=0.02, ha="left", fontsize=10.5, fontweight="bold")
    ax.legend(handles=[Patch(color=COL["low"], label="pick, low risk"), Patch(color=COL["medium"], label="pick, medium risk"),
                       Patch(color=COL["high"], alpha=0.55, hatch="//", label="option, high risk (not picked)"),
                       Patch(color=COL["owner"], label="owner feature move (not adopted)")],
              loc="upper center", bbox_to_anchor=(0.45, -0.05), ncol=2, fontsize=8, frameon=False)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def plot_table(path: Path, lv: list, sm: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    show = [x for x in lv if x["status"] in ("pick", "option", "owner", "risk")]
    show.sort(key=lambda x: (["pick", "option", "owner", "risk"].index(x["status"]),
                             RISK_ORDER.get(x["risk"], 3), x["g"] if x["g"] is not None else 0))
    cells, colors = [], []
    for x in show:
        g = "-" if x["g"] is None else f"{x['g']:+.1f}"
        cells.append([x["key"], x["status"], x["risk"], g, x["change"][:60], x["gate"][:46]])
        colors.append({"pick": "#e3ece1", "option": "#f3e3e3", "owner": "#e1e6ef", "risk": "#f5f0dc"}[x["status"]])
    fig, ax = plt.subplots(figsize=(8.6, 0.235 * len(cells) + 0.9), dpi=100)
    ax.axis("off")
    t = ax.table(cellText=cells, colLabels=["key", "status", "risk", "g", "change", "gate"], loc="upper left",
                 cellLoc="left", colWidths=[0.07, 0.07, 0.07, 0.07, 0.43, 0.33])
    t.auto_set_font_size(False)
    t.set_fontsize(6.6)
    t.scale(1, 1.18)
    for i, c in enumerate(colors):
        for j in range(6):
            t[i + 1, j].set_facecolor(c)
    ax.set_title(f"BL-037 lever table (base, belt M): picks {sm['picks_g']:+.1f} g "
                 f"(low {sm['picks_by_risk']['low']:+.1f}, medium {sm['picks_by_risk']['medium']:+.1f}); "
                 f"gap to 6.6 lb after picks {sm['gap_after_g']:.0f} g", fontsize=9, loc="left", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


# =====================================================================================================================
# report
# =====================================================================================================================
def compute(size: str = "M") -> dict:
    ca1 = ca1_check()
    lv = levers(size, ca1)
    sm = summary(lv, size)
    return {"date": "2026-11-13", "ticket": "BL-037", "size": size, "systems": system_table(size), "levers": lv,
            "summary": sm, "belt_check": belt_check(), "j_strap": j_strap_breakdown(), "camo": camo_swap(size),
            "spreader_share": {k: v for k, v in spreader_share().items() if k != "rows"},
            "spreader_share_rows": spreader_share()["rows"], "ca1": ca1, "back": back_strip(),
            "door_sliders": door_sliders(), "cheek": cheek_risk()}


def _lb(g):
    return f"{g / LB:.2f} lb"


def report(res: dict, shots: list) -> str:
    sm, sy, lv = res["summary"], res["systems"], res["levers"]
    out = []
    a = out.append
    a("# BL-037 weight push: the last 220 g after tests\n")
    a("Owner: pack-designer. Date: 2026-11-13. Code: `designs/pack_5200/weight_push.py` (tests "
      "`tests/test_weight_push.py`); numbers: `analysis/weight_push_results.json`. Every mass is a ledger / roll-up row, "
      "a record, another module's code, or an ASSUMPTION named below. Base configuration, belt M, crown kit M, as the "
      "roll-up. **Do not quote these numbers after the code changes: re-run it.**\n")
    a("## 0. Answer\n")
    a(f"- **After tests before BL-037: {sm['before_g']:.1f} g ({_lb(sm['before_g'])}); 6.6 lb is "
      f"{sm['gap_before_g']:.1f} g away.**")
    a(f"- **Picked (low and medium risk, every rev C factor kept): {sm['picks_g']:+.1f} g** (low {sm['picks_by_risk']['low']:+.1f}, "
      f"medium {sm['picks_by_risk']['medium']:+.1f}). After tests with the picks: **{sm['after_g']:.1f} g ({_lb(sm['after_g'])})**, "
      f"still **{sm['gap_after_g']:.1f} g** over 6.6 lb.")
    a(f"- **Target not met: {-sm['picks_g']:.0f} g found against the ticket's {sm['ticket_g']:.0f} g.** No combination of "
      "checked, gated technical levers reaches it. The frame-side levers the backlog counted on are smaller than booked: "
      "the spreader load share returns at most the upper-branch growth (the mid bar fails in a fill case whatever the "
      "spreader does), and CA-1 at 0.40 does not give -70 g on H1 as adopted (section 3).")
    if sm["owner_route_take"]:
        a(f"- The lowest-risk route to 6.6 lb from here is an owner choice: move {', '.join(sm['owner_route_take'])} to "
          f"add-ons ({sm['owner_route_g']:+.1f} g) on top of the picks: {sm['owner_route_after_g']:.1f} g "
          f"({'reaches' if sm['owner_route_reaches'] else 'still misses'} 6.6 lb). These are features, not frozen and "
          "not DESIGN requirements; listed, not adopted.")
    else:
        a(f"- Even every feature that is neither frozen nor a DESIGN requirement ({sm['owner_free_g']:+.1f} g) does not "
          "close it.")
    if sm["closers"]:
        a(f"- The {sm['left_after_owner_route_g']:.1f} g left after that is closed by any one of: " + "; ".join(
            f"{c['key']} ({c['g']:+.1f} g, {c['status']}: {c['owner']}; margin {c['margin_g']:+.1f} g, "
            f"{c['with_cheek_risk_margin_g']:+.1f} g if the cheek risk lands)" for c in sm["closers"])
          + ". Every one is an owner-rule or DESIGN-requirement change, or a frame option that needs CA-1 >= 0.40 and a "
            "re-run (F-1 fails buckling as run).")
    a(f"- Open booking risk: the 28 mm IM3 cheek may weigh up to {sm['cheek_risk_g']:+.1f} g more than booked (adds only).")
    a("- The picks are a new after-tests step `A_bl037` in the roll-up (`weight_rollup_v2.md`, regenerated). Each is "
      "gated by a named test with today's part as the fallback, so proven now and the ledger are unchanged (BL-014 rule).\n")
    a("## 1. Lever list: where we are heaviest per function (after tests before BL-037, base)\n")
    a("| system | g |\n|---|---:|")
    for k, v in sy["by_system"].items():
        a(f"| {k} | {v:.1f} |")
    g = sy["groups"]
    a(f"\nBL-008 split (`weight_configs_proposal.md` section 5): frame side {g['frame_side']:.1f} g, bag side "
      f"{g['bag_side']:.1f} g, unsplit (thread, labels, IMP-5L) {g['unsplit']:.1f} g.\n")
    a("| function | ours g | leader | leader g | over g | ratio | source |\n|---|---:|---|---:|---:|---:|---|")
    for f in sy["functions"]:
        a(f"| {f['function']} | {f['ours_g']:.1f} | {f['leader']} | {f['leader_g']:.0f} | {f['over_g']:+.0f} | "
          f"{f['ratio']:.2f} | {f['source']} |")
    a("\nRanked against the lightest leader per function: " + "; ".join(
        f"{r['function']} x{r['ratio']:.2f} ({r['over_g']:+.0f} g vs {r['leader']})" for r in sy["ranked_vs_lightest"]) + ".")
    a("\nReading: after tests the bag side is lighter than the leaders' bags (0.74-0.77 x SG / Exo; attachment booked "
      "on the bag side as BL-008 did), so the bag is not where the grams are; the excess is the frame "
      "structure (printed body, carbon crown with three kits, Ti pivot mount), the back system and the belt. The frame "
      "structure is about 2.8 x a carbon-stay frame. Those parts are fixed by the owner rules (adjustable torso with "
      "three crown kits) and by rev C margins that sit near 1.0 (buckling 1.22, fatigue 1.175, spreader fatigue 1.09), "
      "so the levers left there are gated by physical tests (CA-1, MT-1, SPREADER_MAP).\n")
    a("## 2. Candidates\n")
    a("Status: **pick** (implemented as `A_bl037`), **option** (needs a run, a record or a passing test first; not "
      "booked), **owner** (a feature or owner-rule change; listed, not adopted), **rejected**, **risk** (can only add). "
      "g: base, belt M, negative saves.\n")
    a("| key | system | status | risk | change | g | gate | check | owner rules | build hours | source |")
    a("|---|---|---|---|---|---:|---|---|---|---|---|")
    for x in lv:
        gg = "-" if x["g"] is None else f"{x['g']:+.1f}"
        a(f"| {x['key']} | {x['system']} | {x['status']} | {x['risk']} | {x['change']} | {gg} | {x['gate']} | "
          f"{x['check']} | {x['owner']} | {x['hours']} | {x['source']} |")
    a("")
    a("## 3. The items the ticket named\n")
    sp = res["spreader_share"]
    a(f"- **Spreader load share (about 22 g):** BL-027's +{sp['members_added_g']:.1f} g is the mid bar "
      f"(+{sp['mid_growth_g']:.1f} g) and the upper branches (+{sp['branch_growth_g']:.1f} g). Re-reading BL-027's "
      f"own decomposition: {sp['verdict']} (set `{sp['worst_mid_bar']['set']}`, compression "
      f"{-sp['worst_mid_bar']['N_via_stays']:.0f} N factored). So a spreader share can return at most the "
      f"upper-branch {sp['branch_growth_g']:.1f} g, and only after a plate run shows it (option F-2). BL-027's '22 g "
      "could come back off' is not right (Found, not fixed: the sentence is in h1_buckling.md 4.2).")
    c = res["ca1"]
    if c.get("available"):
        cb = c["bases"]
        a(f"- **CA-1 at 0.40 (the -70 g lever):** the -50 to -70 g came from team A's unconverged estimate on the older "
          f"body (frame_comp_A). On H1 as adopted, the only growth a better fatigue ratio can release is BL-024's G0.55 "
          f"offset. Run here: BL-027 members + 28 mm cheeks on plain H1, {c['body_g']:.1f} g ({c['delta_g']:+.1f} g). "
          f"Fatigue at 0.30 / 0.40: fine_sm8 {cb['fine_sm8']['fatigue_030']:.3f} / {cb['fine_sm8']['fatigue_040']:.3f}, "
          + (f"cinch cycled {cb['fine_sm8.cyc']['fatigue_030']:.3f} / {cb['fine_sm8.cyc']['fatigue_040']:.3f}, " if 'fine_sm8.cyc' in cb else "")
          + f"strength {min(v['strength'] for v in cb.values()):.2f}, creep {min(v['creep'] for v in cb.values()):.2f}; "
          f"**Euler buckling {c['buckling_min']:.3f}, mirrored {c['mirrored_min']:.3f}: fails** (BL-024's lower-body "
          "offset was carrying part of the member load; not split here). One re-growth step (fine_sm8 axial run): "
          + ("; ".join(f"mid +{s['d_mid']:g} / upper +{s['d_up']:g} mm, {s['raster_g']:.1f} g ({s['delta_g']:+.1f} g), "
                       f"buckling min {s['min']:.3f} on {min((k for k, v in s['margins'].items() if v is not None), key=lambda k: s['margins'][k])}"
                       for s in c.get("sizing", [])) or "not run")
          + ". So the net is under 10 g and still not converged, and it needs CA-1 >= 0.40 and MT-1 static (cinch cycled "
          f"{cb.get('fine_sm8.cyc', {}).get('fatigue_040', float('nan')):.3f} at 0.40). Option F-1, not picked. The "
          "TEST_PLAN line 'CA-1 at 0.40: body about -50 to -70 g' is corrected there.")
    a(f"- **28 mm cheek booking:** up to {res['cheek']['risk_g']:+.1f} g unbooked (stand-alone fairlead volume "
      f"{res['cheek']['standalone_g']:.1f} g vs {res['cheek']['booked_g']:.1f} g in the raster); weigh the printed halves.")
    a("- **Harness and belt foam / fabric:** B-1, B-3 (belt foam), B-2 (stiffener), H-1 (strap foam) picked; strap and "
      "back meshes have no lighter record (R-5); the yoke and belt plates are rev C fixes (R-6).")
    a("- **Frame print parameters:** not a lever without coupons (F-5); the booked body is a solid raster at the record "
      "density, banded +-5 % in the roll-up; weighing the printed halves settles the booking.")
    a("- **Stays:** the OD 17 crown legs come back only with CA-1 >= 0.40 and a re-run (F-6); fixed torso stays retired.")
    a("- **Lighter primary fabrics:** the shell swaps are already in after tests (BL-011); DCF breaks the quiet rule (R-4); "
      "the camo accents are the remaining fabric lever (G-2).\n")
    j = res["j_strap"]
    a("## 4. Checks run for the picks\n")
    b = res["belt_check"]
    a(f"- **Belt (B-1, B-2, B-3):** hipbelt fit model, 16 ANSUR II forms, one combined run. Package (BL-006): "
      f"{json.dumps(b['package'])}. Package + BL-037: {json.dumps(b['package + BL-037'])}. Limits {json.dumps(b['limits'])}. "
      f"**{'PASS' if b['passes'] else 'FAIL'}.** The belt is outside every HA-LS-1 load path except the plate and webbing, "
      "which do not change.")
    a(f"- **Back (K-1):** back_system2 row `{res['back']['key']}` passes every BL-005 gate; {res['back']['delta_g']:+.1f} g "
      f"against `{res['back']['recommended']}`. Spreader unchanged (FPF 1.25, fatigue 1.09).")
    a(f"- **J-strap (H-1):** the pair as booked: shell {j['shell_g']:.1f} + mesh {j['mesh_g']:.1f} + load foam "
      f"{j['load_foam_eva_g']:.1f} + comfort {j['comfort_g']:.1f} = {j['total_g']:.1f} g (geometry.yaml {j['booked_g']:.1f} g). "
      f"XLPE L200 load foam {j['load_foam_xlpe_g']:.1f} g. No shoulder-pressure model exists: physical gate HS-1.")
    a("- **Frame (F-3):** crown_diet (e) check, ring crush 1.67. **No frame body change is picked**, so H1's rev C "
      "results (buckling 1.22, fatigue 1.175, strength 1.58) stand; the H1 print files are unchanged.")
    a("- **Bag (G-1, G-2):** no load path; the door zip is unloaded (SF 78). Mass and look gates only.\n")
    a("## 5. Effect on the owner rules (DECISIONS.md)\n")
    a("Adjustable torso with three crown kits: kept. No wings, no hood: kept (nothing added back). Rev 3 top, 25 mm crown "
      "straps, aluminium cams: kept (the cam swap is listed as an owner option only). Quiet bag: kept (G-1 quieter; no "
      "hook-and-loop, coil zips). Camo as accents: kept (G-2 changes the base cloth under the print). Internal meat "
      "straps, under-straps pin to pin, bow and rifle carry, rain fly pocket, 85 L, width: untouched.\n")
    a("## 6. Build hours\n")
    a("Every pick is a material or bought-part swap on the same pieces and operations: build hours unchanged "
      "(ASSUMPTION; X-1 saves about 0.1 h). Owner feature moves save the hours listed in section 2 "
      "(build_effort_rev3 op names).\n")
    a("## 7. Assumptions that govern\n")
    a(f"- ASSUMPTION SLIDER-CORD: a #10 slider body with the cord pull weighs {SLIDER_CORD_G} g (record notes 12-15 g). "
      "Settled by SL-1 (weigh 5).")
    a(f"- ASSUMPTION LABEL: one printed label {LABEL_PRINTED_G} g in place of the 8 g woven set (both ASSUMPTIONs). SL-1.")
    a("- ASSUMPTION XLPE-SHOULDER: XLPE L200 5 mm under the perforated EVA comfort layer carries the shoulder load "
      "without bottoming at 68 kg (no model). Settled by HS-1 (pressure strips, 3 testers) + CS-1.")
    a("- ASSUMPTION XLPE-SET: L200 compression set 12 % (datasheet) holds after a season of sweat and heat. CS-1 "
      "(50 % for 22 h at 40 C, recovery 24 h).")
    a("- ASSUMPTION HYPERD-ABRASION: HyperD 300 (Martindale > 8000, datasheet) wears at least as well as the 630D ESTIMATE "
      "record on the blades. AB-1.")
    a("- ASSUMPTION BUSHING-LD: L/D 2.8 slides without binding (crown_diet). BU-1.")
    a("- Every BL-006, BL-005 and roll-up ASSUMPTION the picks rest on stays as written there.\n")
    a("## 8. Physical gates added (TEST_PLAN.md, BL-037 section)\n")
    a("HS-1 shoulder pressure (H-1), CS-1 XLPE compression set (B-1, H-1), AB-1 HyperD 300 abrasion + print swatch (G-2), "
      "SL-1 weigh sliders and labels (G-1, X-1), ST-1 gloved sternum (H-2), BU-1 bushing slide (F-3); HB-1 and HB-D2 "
      "extended to the XLPE belt and the 0.5 mm stiffener; BP-1 run at the 2 mm core (K-1).\n")
    a("## 9. Screenshots\n")
    for s in shots:
        a(f"- `{s}`")
    return "\n".join(out) + "\n"


def _j(o):
    if isinstance(o, dict):
        return {str(k): _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    if hasattr(o, "item"):
        return o.item()
    return o


def write() -> dict:
    res = compute()
    lv, sm = res["levers"], res["summary"]
    s1 = plot_waterfall(SCREENS / f"{PREFIX}1.png", lv, sm)
    s2 = plot_table(SCREENS / f"{PREFIX}2.png", lv, sm)
    DOC_SCREEN.parent.mkdir(parents=True, exist_ok=True)
    DOC_SCREEN.write_bytes(s1.read_bytes())
    shots = [str(p.relative_to(ROOT)) for p in (s1, s2, DOC_SCREEN)]
    res["screens"] = shots
    RESULT.write_text(json.dumps(_j(res), indent=1))
    DOC.write_text(report(res, shots))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    res = write() if a.write else compute()
    sm = res["summary"]
    for x in res["levers"]:
        g = "-" if x["g"] is None else f"{x['g']:+7.1f}"
        print(f"{x['key']:10s} {x['status']:8s} {x['risk']:6s} {g:>8s}  {x['change'][:80]}")
    print(json.dumps(sm, indent=1))


if __name__ == "__main__":
    main()
