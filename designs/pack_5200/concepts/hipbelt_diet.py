"""BL-006 hipbelt B diet (pack-designer, 2026-11-10).

Goal (docs/backlog/BL-006-hipbelt-diet.md): keep belt B's pressure and slip results and bring belt B to <= 490 g at
belt M in BASE configuration (stretch 470 g). Reject any change that makes the worst-case wing peak exceed belt B's
56.5 kPa or the worst hold fall below 0.64 (both over the 16 ANSUR II hip forms).

Sources (called, never copied)
------------------------------
* masses: ``huntkit.mass.ledger`` (BL-001), config ``corrie_b2_h1_c`` (CORRIE B.2 on H1 + package C: the 7075 plate
  package C-1..C-3 and the CFRP pad backer C-4 fix are adopted), system ``belt``;
* base / as-hunted: owner decision DECISIONS 2026-11-10 on ``analysis/weight_configs_proposal.md``: the IMP-3 bottle
  holster is an add-on outside base. Its two 25 mm wing tabs are bartacked to the wing, so they stay in base (this
  splits the proposal's ASSUMPTION row);
* pressure / slip: ``huntkit.gendesign.hipbelt.study`` on ``hipbelt_concepts.B`` and variants of it (same 16 forms);
* structural margins on file: ``analysis/hipbelt_structural_results.json`` and ``weight_c_structural_results.json``;
* hardware and material masses: ``data/materials`` records via ``huntkit.materials.load``.

Nothing in ``hipbelt.py``, ``hipbelt_structure.py``, ``hipbelt_concepts.py``, ``corrie.py`` or the ledger is edited.

    python designs/pack_5200/concepts/hipbelt_diet.py            # print the summary
    python designs/pack_5200/concepts/hipbelt_diet.py --write    # also write analysis/hipbelt_diet.md + the screenshot
"""
from __future__ import annotations

import functools
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
for _p in (ROOT, HERE, HERE.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import corrie as C  # noqa: E402
import hipbelt_concepts as HC  # noqa: E402
from huntkit.gendesign import hipbelt as hb  # noqa: E402
from huntkit.gendesign.hipbelt import FoamLayer as F  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402
from huntkit.materials import load  # noqa: E402

ANALYSIS = HERE.parent / "analysis"
DOC = ANALYSIS / "hipbelt_diet.md"
SCREEN = ROOT / "outputs" / "screens" / "20261110_BL006_1.png"   # orchestrator's prefix for 2026-11-10
CONFIG = "corrie_b2_h1_c"
SIZE = "M"
TARGET_G, STRETCH_G = 490.0, 470.0
OZ, LB = 28.3495, 453.592

B = HC.B
_RES = json.loads((HERE / "hipbelt_results.json").read_text())["summary"]["B"]
WING_WORST_LIMIT = _RES["worst_peak_wing_kpa"]          # 56.5 kPa, belt B as published (hipbelt_fit.md)
HOLD_WORST_LIMIT = _RES["worst_hold"]                    # 0.64
LUMBAR_WATCH = hb.P_HIP_PEAK_KPA                         # 48.6 kPa criterion; belt B worst 45.4 (watch, not a gate)

WEB25 = load("poly_webbing_25mm").require("mass_g_m")
WEB50 = load("nylon_webbing_50mm").require("mass_g_m")
LADDER = load("ladder_lock_25mm").require("mass_g")
BUCKLE50 = load("buckle_side_release_50mm")
BUCKLE38 = load("buckle_side_release_38mm")
CORD2 = load("dyneema_cord_2mm").require("mass_g_m")
CORDLOCK = load("cord_lock_spring").require("mass_g")
GSM_1000D = load("cordura_1000d_nylon66").require("areal_density_gsm")
GSM_HYP = load("hypalon_coated_nylon").require("areal_density_gsm")
RHO_HDPE = load("hdpe_sheet").require("density_kg_m3")
E_EVA45 = load("eva_foam_45c").require("compression_25pct_kpa") / 0.25
E_XLPE = load("xlpe_foam_l200").require("compression_25pct_kpa") / 0.25
RHO_EVA45 = load("eva_foam_45c").require("density_kg_m3")
RHO_XLPE = load("xlpe_foam_l200").require("density_kg_m3")

# ---- closure geometry (a). Each number is an ASSUMPTION unless a source is named.
CLOTHING_MM = 40.0          # ASSUMPTION: belt worn over two base layers, about 2 pi x 6 mm on the circumference
LOCK_FROM_FRONT_MM = 62.0   # lock / anchor station from the front centre (huntkit/viz3d/corrie_b1.py layout)
ANCHOR_MM = 60.0            # 25 mm anchor end: box-X 40 mm (hipbelt_structure.tab_check box_l) + 20 mm fold
DRING_TAB_MM = 110.0        # D-ring tab: 25 mm doubled round the ring, box-X 40 + 15 mm each leg (tab_check)
RING_WRAP_MM = 15.0         # ASSUMPTION: webbing round the 4 mm D-ring section
LOCK_WRAP_MM = 30.0         # ASSUMPTION: webbing through the heavy ladder lock (50 mm long body, record)
TAIL_MIN_MM = 150.0         # gloved pull tail at the size's largest circumference (weight pass A-2 basis)
BUCKLE_TAB_MM = 140.0       # ASSUMPTION: 50 mm webbing doubled round each buckle bar, 2 x 60 + 20 mm fold
BOOKED_50_M = 0.9           # build_geometry.py hipbelt row (C0 1:1 belt strap), carried into belt B's ledger row
BOOKED_25_M = 0.6           # hipbelt_concepts.belt_bom "2:1 pull: 25 mm poly webbing +0.6 m"
STAB_25_M = 0.8             # build_geometry.py: hip stabilizers 2 x 400 mm poly 25 mm + 2 ladder locks

# ---- stiffener (c)
PERF_PHI = 0.30             # ASSUMPTION: open-area fraction of a punched 10 mm hole pattern (staggered, 17 mm pitch)
# ASSUMPTION: in-plane modulus of a perforated sheet ~ (1 - phi)^2 of solid (ligament-efficiency class estimate); the
# model takes the hoop stiffness E t, so the perforated sheet is modelled as an equivalent solid of t (1 - phi)^2.

# ---- pad seat (f)
CORD_TIE_M = 0.45           # ASSUMPTION: 2 mm cord round the pan's bottom edge (0.40 m strap path + knot)


# =====================================================================================================================
# ledger
# =====================================================================================================================
def holster_split() -> dict:
    """IMP-3 holster: what comes off with the holster (add-on) and the two wing tabs that stay sewn to the belt."""
    h = C.holster()
    tabs = next(g for n, g in h["hardware"] if n.startswith("2 wing tabs"))
    return {"total_g": h["mass_g"], "tabs_g": round(tabs, 2), "addon_g": round(h["mass_g"] - tabs, 2)}


JOBS = {   # id prefix -> job (what the part does)
    "belt:SH-05": "owner camo accent on the wing tips (owner-frozen look)",
    "belt:rifle_tabs": "rifle-boot tabs both wings + belt trims (rifle carry requirement)",
    "belt:50_mm_belt_webbing": "closure: 50 mm strap + buckle (C0 1:1 booking), stabilizer straps + 2 ladder locks",
    "belt:belt_b_wing_shell": "wing outer shell; carries the wing tension T (HDPE floats)",
    "belt:belt_b_wing_face": "wing body face (spacer mesh, unprinted until HB-2)",
    "belt:belt_b_wing_load_foam": "wing load layer (sets the pressure spread)",
    "belt:belt_b_wing_comfort_foam": "wing comfort layer",
    "belt:belt_b_wing_crest_relief": "crest-relief zone (90 mm over the crest)",
    "belt:belt_b_wing_stiffener": "wing stiffener: hoop stiffness, spreads load over the height, stops roll-over",
    "belt:belt_b_lumbar_shell": "lumbar pad shell",
    "belt:belt_b_lumbar_face": "lumbar pad face",
    "belt:belt_b_lumbar_foam_1": "lumbar bearing foam, firm (takes the lumbar push H)",
    "belt:belt_b_lumbar_foam_2": "lumbar bearing foam, soft",
    "belt:belt_b_lumbar_terraced": "removable terraced wedge (fills the lumbar hollow)",
    "belt:belt_b_2_1_pull_25": "2:1 pull webbing (anchor, legs, D-ring tabs, tail)",
    "belt:belt_b_2_1_pull_2": "2:1 D-rings at the wing tips",
    "belt:belt_b_silicone": "grip print (booked out in B.2)",
    "belt:belt_b_cant_snap": "cant snap deleted (credit)",
    "belt:belt_b_correction_d_rings": "D-ring record correction",
    "belt:belt_b_correction_grip": "grip print out (B.2 A-1)",
    "belt:belt_b_correction_2_1_lock": "2:1 lock legs, heavy ladder locks",
    "belt:IMP-5L": "hip pocket, left wing (sewn)",
    "belt:IMP-3": "1 L bottle holster on G-hooks (add-on; its 2 wing tabs stay)",
    "belt:belt_b_load_path_6061": "centre plate (bow-tie): wing tension across the back, pivot seat",
    "belt:belt_b_load_path_pa66": "hub bushing on the Ti pin",
    "belt:belt_b_load_path_pivot_latch": "pivot latch (tool-free swap)",
    "belt:belt_b_load_path_1000d_root": "stitched-ear root doublers",
    "belt:belt_b_load_path_1000d_tip": "D-ring tab doublers",
    "belt:belt_b_load_path_ear_saddle": "ear saddle-stitch thread",
    "belt:belt_b_load_path_pom": "thrust washer",
    "belt:lumbar_pad_seat_2_eva": "pad-seat standoff rails (set the 4.5 mm channel depth play)",
    "belt:lumbar_pad_seat_hdpe_1_0": "pad backer (spreads H onto the pan; C-4: CFRP 0.8 below)",
    "belt:lumbar_pad_seat_hdpe_0_5": "slip liner in the channel (also isolates CFRP from the aluminium spine)",
    "belt:lumbar_pad_seat_hypalon": "pad retention, top: sleeve over the pan's top flange",
    "belt:lumbar_pad_seat_25_mm": "pad retention, bottom: 25 mm strap + ladder lock",
    "belt:C-1": "package C plate: 7075-T6 1.2, D28 hub, 2 holes (credit)",
    "belt:C-4": "package C fix: pad backer HDPE 1.0 -> CFRP 0.8",
}


def _job(rid: str) -> str:
    for k, v in JOBS.items():
        if rid.startswith(k):
            return v
    raise KeyError(f"no job for ledger row {rid}")


def _sf(group: str, item: str) -> dict:
    """{case: SF/req} of one hipbelt_structural summary item."""
    s = json.loads((ANALYSIS / "hipbelt_structural_results.json").read_text())["summary"]
    return {r["case"]: r["sf_over_req"] for r in s if r["group"] == group and r["item"] == item}


def _margin(rid: str) -> str:
    """Margin on file for a load-path row (min SF/req over the cases, with its source)."""
    wc = json.loads((ANALYSIS / "weight_c_structural_results.json").read_text())

    def mn(d, src):
        k = min(d, key=d.get)
        return f"{d[k]:.2f} ({k}; {src})"
    hs = "hipbelt_structural_results.json"
    if rid.startswith(("belt:belt_b_load_path_6061", "belt:C-1", "belt:belt_b_load_path_pa66")):
        return f"{wc['C1_C2']['package_min_sf']:.2f} (walk, package C plate; weight_c_structural_results.json)"
    if rid.startswith(("belt:belt_b_load_path_1000d_root", "belt:belt_b_load_path_ear")):
        return mn(_sf("Wing joint", "ear: thread per hole"), hs + " ear thread")
    if rid.startswith("belt:belt_b_load_path_1000d_tip"):
        return mn(_sf("2:1 pull", "D-ring tab box-X (tex 135)"), hs + " tab box-X")
    if rid.startswith("belt:belt_b_2_1_pull_25"):
        tab = json.loads((ANALYSIS / hs).read_text())["tab"]
        return f"{tab['webbing_25']['sf']:.1f} (C2, webbing break / lock leg; {hs} tab)"
    if rid.startswith("belt:belt_b_2_1_pull_2") or rid.startswith("belt:belt_b_correction_d_rings"):
        return mn(_sf("2:1 pull", "D-ring 25 mm Al"), hs)
    if rid.startswith("belt:belt_b_correction_2_1_lock"):
        return mn(_sf("2:1 pull", "heavy ladder lock slip"), hs + " slip, test-qualified")
    if rid.startswith("belt:50_mm_belt_webbing"):
        return mn(_sf("2:1 pull", "50 mm buckle"), hs + " buckle; stabilizers: no load case on file")
    if rid.startswith("belt:belt_b_2_1_pull_25"):
        tab = json.loads((ANALYSIS / hs).read_text())["tab"]
        return f"{tab['webbing_25']['sf']:.1f} (C2, webbing break / lock leg; {hs} tab)"
    if rid.startswith("belt:belt_b_wing_stiffener"):
        return "floats: no net tension (hipbelt_structural.md section 5); fit lever only"
    if rid.startswith("belt:belt_b_wing_load_foam"):
        return "pressure model only (no structural case)"
    if rid.startswith("belt:C-4") or rid.startswith("belt:lumbar_pad_seat_hdpe_1_0"):
        r = wc["C4"]["rows"]["cfrp_plate_quasi_iso_0.8"]
        return f"{r['min_sf']:.2f} (walk, CFRP 0.8 backer; weight_c_structural_results.json C4)"
    if rid.startswith("belt:belt_b_load_path_pom"):
        return "18.9 (thrust face; hipbelt_structural.md section 4)"
    return "n/a"


def ledger_table(size: str = SIZE) -> list[dict]:
    """Belt B part by part from the ledger, with job, load-path flag, base/add-on and margin on file."""
    hs = holster_split()
    out = []
    for r in L.parts(CONFIG, size):
        if r["system"] != "belt":
            continue
        row = {"id": r["id"], "name": r["name"], "g": r["g"], "load_path": r["load_path"], "job": _job(r["id"]),
               "config": "base", "margin": _margin(r["id"]) if r["load_path"] or r["id"].startswith("belt:C-4") else ""}
        if r["id"] == "belt:IMP-3":
            row["config"] = f"add-on {hs['addon_g']:.1f} g / base {hs['tabs_g']:.1f} g (wing tabs)"
        out.append(row)
    return out


def belt_masses(size: str = SIZE) -> dict:
    """Ledger belt system and its base / as-hunted split (as-hunted = base + holster)."""
    full = L.by_system(CONFIG, size)["belt"]
    hs = holster_split()
    return {"ledger_belt_g": full, "base_g": round(full - hs["addon_g"], 1), "as_hunted_g": full,
            "holster_addon_g": hs["addon_g"], "pack_total_g": L.total(CONFIG, size)}


# =====================================================================================================================
# pressure model
# =====================================================================================================================
@functools.lru_cache(maxsize=1)
def forms():
    return tuple(HC.all_forms())


def evaluate(design) -> dict:
    """Belt B's published summary metrics over the 16 forms, same rounding as hipbelt_concepts.summarise()."""
    rows = [hb.study(design, f) for f in forms()]
    w = [r["peak_wing_kpa"] for r in rows]
    h = [r["hold_margin_at_allow"] for r in rows]
    return {"worst_wing_kpa": max(w), "median_wing_kpa": float(np.median(w)),
            "worst_lumbar_kpa": max(r["peak_lumbar_kpa"] for r in rows),
            "median_lumbar_kpa": float(np.median([r["peak_lumbar_kpa"] for r in rows])),
            "median_hold": float(np.median(h)), "worst_hold": min(h),
            "min_asis_clear_mm": min(r["asis_clear_mm"] for r in rows),
            "median_T_req_n": float(np.median([r["T_req_n"] for r in rows])), "rows": rows}


@functools.lru_cache(maxsize=None)
def _eval_cached(key: str) -> dict:
    return evaluate(DESIGNS[key]())


def baseline() -> dict:
    return _eval_cached("B")


# =====================================================================================================================
# mass helpers
# =====================================================================================================================
def _form_for(size):
    lo, hi = HC.SIZES_B[size]
    band = int(round((lo + hi) / 2 / 2) * 2)
    return hb.hip_form("male", band)


def hdpe_mass_g(design, size: str = SIZE, phi: float = 0.0) -> float:
    """Both wing stiffeners: the developed wing outline from the root inset to (tip - inset - soft-tip gap), inset
    top and bottom, x t x rho (hdpe_sheet record), x (1 - phi). belt_bom() ignores the soft-tip gap; this does not."""
    Tt, Bt, _ = hb.wing_flat(design, _form_for(size), size)
    x_end = float(0.5 * (Tt[-1, 0] + Bt[-1, 0])) - design.stiff_inset - design.stiff_tip_gap
    xs = np.linspace(design.stiff_inset, x_end, 400)
    h = np.interp(xs, Tt[:, 0], Tt[:, 1]) - np.interp(xs, Bt[:, 0], Bt[:, 1]) - 2 * design.stiff_inset
    area = float(np.trapezoid(np.clip(h, 0, None), xs)) if hasattr(np, "trapezoid") else float(np.trapz(np.clip(h, 0, None), xs))
    return 2 * area * design.stiff_t * 1e-9 * RHO_HDPE * 1000 * (1 - phi)


def bom_soft_g(design, size: str = SIZE) -> float:
    """belt_bom soft goods of a variant, booked with belt B's key so the hardware deltas stay belt B's."""
    return HC.belt_bom(replace(design, key="B"), size)["soft_g"]


def wedge(size: str = SIZE) -> dict:
    bom = HC.belt_bom(B, size)
    row = next(r for r in bom["pieces"] if r["piece"].startswith("lumbar terraced wedge"))
    t = round(max(B.taper(s) for s in B.sizes) * B.lumbar_h / 3, 1)
    return {"area_mm2": row["area_mm2"], "t_mm": t, "mass_g": row["mass_g"]}


def closure(size: str = SIZE) -> dict:
    """Webbing that belt B's 2:1 routing really needs (anchor on the buckle half -> D-ring on the wing tip -> back
    through the lock on the buckle half -> tail), against what the ledger books (0.9 m 50 mm + 0.6 m 25 mm)."""
    lo, hi = HC.SIZES_B[size]
    s_tip = B.lumbar_w / 2 + B.wing_len(size)
    c_max = hi * hb.IN + CLOTHING_MM
    c_min = lo * hb.IN + CLOTHING_MM
    leg_max = c_max / 2 - s_tip - LOCK_FROM_FRONT_MM
    leg_min = c_min / 2 - s_tip - LOCK_FROM_FRONT_MM
    per_side = ANCHOR_MM + 2 * leg_max + RING_WRAP_MM + LOCK_WRAP_MM + TAIL_MIN_MM + DRING_TAB_MM
    need25 = 2 * per_side / 1000
    need50 = 2 * BUCKLE_TAB_MM / 1000
    booked = BOOKED_50_M * WEB50 + BOOKED_25_M * WEB25
    new = need50 * WEB50 + need25 * WEB25
    return {"size": size, "leg_max_mm": round(leg_max, 0), "leg_min_mm": round(leg_min, 0),
            "tail_at_min_mm": round(TAIL_MIN_MM + 2 * (leg_max - leg_min), 0),
            "need_25_m": round(need25, 3), "need_50_m": round(need50, 3),
            "booked_g": round(booked, 1), "new_g": round(new, 1), "delta_g": round(new - booked, 1)}


def front_strap_kpa(width_mm: float) -> dict:
    """Pressure under the unpadded front strap: line load T_req x kappa over the strap width, at the sharpest
    curvature between the wing tip and the front centre (belt B's T_req per form). Watch item: the fit model does not
    model the front strap, the abdomen is soft tissue, and webbing bridges sharp curvature."""
    vals = []
    for r, f in zip(baseline()["rows"], forms()):
        sec = hb.section(f)
        s_tip = B.lumbar_w / 2 + B.wing_len(r["size"])
        k = float(sec.kappa[sec.s > s_tip].max())
        vals.append(r["T_req_n"] * k / width_mm * 1000)
    return {"width_mm": width_mm, "median_kpa": round(float(np.median(vals)), 0), "worst_kpa": round(max(vals), 0)}


def stabilizers_g() -> float:
    return round(STAB_25_M * WEB25 + 2 * LADDER, 1)


def pad_seat_moves() -> dict:
    ps = dict(C.pad_seat()["rows"])
    strap = next(g for n, g in ps.items() if n.startswith("25 mm bottom strap"))
    sleeve = next(g for n, g in ps.items() if n.startswith("Hypalon top sleeve"))
    w, h = C.PAD_SEAT["sleeve"]
    return {"strap_g": strap, "cord_g": round(CORD_TIE_M * CORD2 + CORDLOCK, 1),
            "sleeve_g": sleeve, "sleeve_1000d_g": round(w * h * 1e-6 * GSM_1000D, 1),
            "check_hyp_g": round(w * h * 1e-6 * GSM_HYP, 1)}


def wedge_taper_factor(p_kpa: float | None = None) -> float:
    """ASSUMPTION: a softer wedge loses taper in proportion to its extra compression under the lumbar pressure:
    (1 - p/E_xlpe) / (1 - p/E_eva45), secant moduli from the records, p = belt B's worst lumbar peak."""
    p = baseline()["worst_lumbar_kpa"] if p_kpa is None else p_kpa
    return (1 - p / E_XLPE) / (1 - p / E_EVA45)


# =====================================================================================================================
# variants
# =====================================================================================================================
def _wing_load(mat, t):
    return dict(wing_foam=(F(mat, t), B.wing_foam[1]), crest_foam=(F(mat, t), B.crest_foam[1]))


DESIGNS = {
    "B": lambda: B,
    "c1": lambda: replace(B, stiff_tip_gap=B.stiff_tip_gap + 20.0),
    "c2": lambda: replace(B, stiff_t=0.75),
    "c3": lambda: replace(B, stiff_t=0.5),
    "c4": lambda: replace(B, stiff_t=1.0 * (1 - PERF_PHI) ** 2),
    "d1": lambda: replace(B, **_wing_load("eva_foam_45c", B.wing_foam[0].t - 1.0)),
    "d2": lambda: replace(B, **_wing_load("xlpe_foam_l200", 6.0)),
    "d3": lambda: replace(B, wing_foam=(B.wing_foam[0], F("eva_foam_30c", B.wing_foam[1].t - 1.0))),
    "d4": lambda: replace(B, lumbar_foam=(F("xlpe_foam_l200", 6.0), B.lumbar_foam[1])),
    "d5": lambda: replace(B, lumbar_taper_tan={k: v * wedge_taper_factor() for k, v in HC.TAPER_B.items()}),
}


def _mass_delta(key: str, size: str = SIZE) -> float:
    """Base-configuration grams of one item at a belt size (negative = saving)."""
    if key == "a1":
        return BUCKLE38.require("mass_g") - BUCKLE50.require("mass_g")
    if key == "a2":
        return closure(size)["delta_g"]
    if key == "b":
        return -stabilizers_g()
    if key in ("c1", "c2", "c3"):
        return hdpe_mass_g(DESIGNS[key](), size) - hdpe_mass_g(B, size)
    if key == "c4":
        return hdpe_mass_g(B, size, PERF_PHI) - hdpe_mass_g(B, size)
    if key in ("d1", "d2", "d3", "d4"):
        return bom_soft_g(DESIGNS[key](), size) - bom_soft_g(B, size)
    if key == "d5":
        w = wedge(size)
        return w["area_mm2"] * w["t_mm"] * 1e-9 * (RHO_XLPE - RHO_EVA45) * 1000
    if key == "e":
        return -holster_split()["addon_g"]
    if key == "f1":
        p = pad_seat_moves()
        return p["cord_g"] - p["strap_g"]
    if key == "f2":
        p = pad_seat_moves()
        return p["sleeve_1000d_g"] - p["sleeve_g"]
    raise KeyError(key)


ITEMS = [   # key, task, change, load path?, test that gates it
    ("a1", "a", "50 mm side-release buckle -> 38 mm (record buckle_side_release_38mm)", True, "-"),
    ("a2", "a", "closure booked as belt B routes it: 0.9 m of 50 mm strap (C0 1:1 relic) -> two 140 mm 50 mm buckle "
     "tabs; 25 mm 2:1 webbing re-booked from the routing geometry", True, "HB-7 (lock slip, already planned)"),
    ("b", "b", "delete both stabilizer straps (2 x 400 mm 25 mm + 2 ladder locks); frame anchor pads stay", False,
     "HB-D1 side-hill stability, stabilizers slack vs cinched"),
    ("c1", "c", "HDPE stiffener ends 20 mm earlier (soft tip 25 -> 45 mm)", False, "HB-1"),
    ("c2", "c", "HDPE stiffener 1.0 -> 0.75 mm", False, "HB-D2 wing roll-over + HB-1"),
    ("c3", "c", "HDPE stiffener 1.0 -> 0.5 mm", False, "HB-D2 + HB-1"),
    ("c4", "c", f"HDPE stiffener 1.0 mm perforated, {PERF_PHI:.0%} open (punched holes)", False, "HB-D2 + HB-1"),
    ("d1", "d", "wing load foam EVA 45C 6 -> 5 mm", False, "HB-1"),
    ("d2", "d", "wing load foam EVA 45C 6 mm -> XLPE L200 6 mm", False, "HB-1 + compression-set check"),
    ("d3", "d", "wing comfort foam EVA 30C 5 -> 4 mm", False, "HB-1"),
    ("d4", "d", "lumbar firm foam EVA 45C 6 mm -> XLPE L200 6 mm", False, "HB-1"),
    ("d5", "d", "lumbar terraced wedge EVA 45C -> XLPE L200 (taper loss modelled)", False, "HB-1"),
    ("e", "e", "IMP-3 bottle holster to an add-on (owner decision 2026-11-10); its 2 wing tabs stay", False, "-"),
    ("f1", "f", "pad-seat bottom strap 25 mm + ladder lock -> 2 mm Dyneema cord tie + cord lock", False,
     "HB-D3 pad-seat retention"),
    ("f2", "f", "pad-seat top sleeve Hypalon -> 1000D Cordura (same 190 x 40)", False, "HB-D3"),
]

# Package choice (DECISION, pack-designer): among passing items, one stiffener option and one wing-foam option.
#  c2 over c3/c4: same model result; 0.75 mm keeps 42 % of 1.0 mm's bending stiffness (t^3) against 12.5 % at 0.5 mm,
#  and needs no punching (c4 ~ same grams, extra labour). Foam (d): none taken. The package meets the stretch without
#  them; d2 + d4 pass the model and are the next lever, but they change the belt's feel, which the model cannot judge.
PACKAGE = ("a2", "b", "c2", "e", "f1", "f2")
UNGATED = ("a2", "e", "f1", "f2")       # the package without the items that need a new prototype test (b, c2)
NEXT_LEVER = ("d2", "d4")


def package_design():
    d = B
    for k in PACKAGE:
        if k in ("c1", "c2", "c3", "c4", "d1", "d2", "d3", "d4", "d5"):
            v = DESIGNS[k]()
            for fld in ("stiff_t", "stiff_tip_gap", "wing_foam", "crest_foam", "lumbar_foam", "lumbar_taper_tan"):
                if getattr(v, fld) != getattr(B, fld):
                    d = replace(d, **{fld: getattr(v, fld)})
    return d


def verdict(key: str, ev: dict | None) -> tuple[str, str]:
    if key == "a1":
        sf = BUCKLE38.require("breaking_strength_n") / _c2_T()
        return "REJECT", f"buckle record {BUCKLE38.require('breaking_strength_n'):.0f} N vs C2 T {_c2_T():.0f} N: SF/req {sf:.2f}"
    if ev is None:
        return "PASS", "no effect on the fit model (part not in it)"
    bad = []
    if ev["worst_wing_kpa"] > WING_WORST_LIMIT + 1e-9:
        bad.append(f"worst wing {ev['worst_wing_kpa']:.1f} > {WING_WORST_LIMIT}")
    if ev["worst_hold"] < HOLD_WORST_LIMIT - 1e-9:
        bad.append(f"worst hold {ev['worst_hold']:.2f} < {HOLD_WORST_LIMIT}")
    if bad:
        return "REJECT", "; ".join(bad)
    note = ""
    if ev["worst_lumbar_kpa"] > baseline()["worst_lumbar_kpa"] + 0.5:
        note = f"lumbar worst {ev['worst_lumbar_kpa']:.1f} kPa (B {baseline()['worst_lumbar_kpa']:.1f}; criterion {LUMBAR_WATCH})"
    return "PASS", note or "within belt B's results"


def _c2_T() -> float:
    from huntkit.gendesign import hipbelt_structure as HS
    return HS.load_sets()["C2"].T


@functools.lru_cache(maxsize=1)
def study() -> dict:
    base_ev = baseline()
    items = []
    for key, task, change, lp, gate in ITEMS:
        ev = _eval_cached(key) if key in DESIGNS else None
        v, why = verdict(key, ev)
        row = {"key": key, "task": task, "change": change, "load_path": lp, "gate": gate, "g": round(_mass_delta(key), 1),
               "verdict": v, "why": why, "in_package": key in PACKAGE}
        if ev:
            row.update({k: ev[k] for k in ("worst_wing_kpa", "median_wing_kpa", "worst_lumbar_kpa", "median_hold",
                                           "worst_hold", "min_asis_clear_mm")})
        else:
            row.update({k: base_ev[k] for k in ("worst_wing_kpa", "median_wing_kpa", "worst_lumbar_kpa", "median_hold",
                                                "worst_hold", "min_asis_clear_mm")})
        items.append(row)
    pk_ev = evaluate(package_design())
    bm = belt_masses(SIZE)
    saved = round(sum(r["g"] for r in items if r["in_package"]), 1)
    phys = round(sum(r["g"] for r in items if r["in_package"] and r["key"] != "e"), 1)
    per_size = {}
    for s in C.BELT_SIZES:
        m = belt_masses(s)
        d = sum(_mass_delta(k, s) for k in PACKAGE)
        dp = sum(_mass_delta(k, s) for k in PACKAGE if k != "e")
        per_size[s] = {"base_today_g": m["base_g"], "as_hunted_today_g": m["as_hunted_g"],
                       "base_pkg_g": round(m["base_g"] + dp, 1),
                       "as_hunted_pkg_g": round(m["as_hunted_g"] + dp, 1), "base_delta_g": round(d, 1)}
    pkg = {"items": PACKAGE, "delta_g": saved, "physical_delta_g": phys,
           "base_g": round(bm["base_g"] + phys, 1), "as_hunted_g": round(bm["as_hunted_g"] + phys, 1),
           "pack_base_delta_g": saved, "eval": {k: v for k, v in pk_ev.items() if k != "rows"},
           "verdict": verdict("pkg", pk_ev),
           "ungated_base_g": round(bm["base_g"] + sum(r["g"] for r in items if r["key"] in UNGATED and r["key"] != "e"), 1),
           "next_lever_g": round(sum(r["g"] for r in items if r["key"] in NEXT_LEVER), 1)}
    return {"masses": bm, "baseline": {k: v for k, v in base_ev.items() if k != "rows"}, "items": items,
            "package": pkg, "per_size": per_size, "closure": {s: closure(s) for s in C.BELT_SIZES},
            "front_strap": [front_strap_kpa(w) for w in (25.0, 38.0, 50.0)], "pad_seat": pad_seat_moves(),
            "wedge_taper_factor": round(wedge_taper_factor(), 3), "hdpe_B_g": round(hdpe_mass_g(B), 1),
            "holster": holster_split(), "stabilizers_g": stabilizers_g()}


# =====================================================================================================================
# figure
# =====================================================================================================================
def chart(path: Path = SCREEN) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    st = study()
    rows = st["items"]
    base = st["baseline"]
    INK, MUTED, GRID = "#0b0b0b", "#6b6a66", "#e4e3df"
    COL = {"pkg": "#2a78d6", "pass": "#a9a8a2", "rej": "#c8402a"}
    labels = [f"{r['key']}  {r['change'][:58]}{'...' if len(r['change']) > 58 else ''}" for r in rows]
    col = [COL["rej"] if r["verdict"] == "REJECT" else COL["pkg"] if r["in_package"] else COL["pass"] for r in rows]
    y = np.arange(len(rows))[::-1]
    fig, axs = plt.subplots(1, 3, figsize=(15, 8.2), gridspec_kw={"width_ratios": [2.2, 1, 1]}, sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axs:
        ax.set_facecolor("#fcfcfb")
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=9)
    ax = axs[0]
    g = [-r["g"] for r in rows]
    ax.barh(y, g, color=col, height=0.62)
    for yi, gi in zip(y, g):
        ax.text(gi + (0.6 if gi >= 0 else -0.6), yi, f"{gi:+.1f}", va="center", ha="left" if gi >= 0 else "right",
                fontsize=9, color=INK)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(y, labels, fontsize=9, color=INK)
    ax.set_xlabel("grams saved in base, belt M (negative = adds)", color=MUTED)
    ax.set_xlim(min(g) - 8, max(g) + 10)
    ax = axs[1]
    dw = [r["worst_wing_kpa"] - base["worst_wing_kpa"] for r in rows]
    ax.scatter(dw, y, s=60, color=col, zorder=3, edgecolors="#fcfcfb", linewidths=2)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel(f"worst wing peak change, kPa\n(B {base['worst_wing_kpa']}; reject if > 0)", color=MUTED)
    lim = max(1.0, max(abs(v) for v in dw) * 1.3)
    ax.set_xlim(-lim, lim)
    for yi, v in zip(y, dw):
        if abs(v) >= 0.05:
            ax.text(v, yi + 0.3, f"{v:+.1f}", ha="center", fontsize=8, color=INK)
    ax = axs[2]
    dh = [r["worst_hold"] - base["worst_hold"] for r in rows]
    ax.scatter(dh, y, s=60, color=col, zorder=3, edgecolors="#fcfcfb", linewidths=2)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel(f"worst hold change\n(B {base['worst_hold']:.2f}; reject if < 0)", color=MUTED)
    lim = max(0.02, max(abs(v) for v in dh) * 1.3)
    ax.set_xlim(-lim, lim)
    for yi, v in zip(y, dh):
        if abs(v) >= 0.005:
            ax.text(v, yi + 0.3, f"{v:+.2f}", ha="center", fontsize=8, color=INK)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=COL["pkg"], label="in the recommended package"),
                        Patch(color=COL["pass"], label="passes, not taken"),
                        Patch(color=COL["rej"], label="rejected")], loc="lower center", ncol=3, frameon=False,
               fontsize=10)
    pk = st["package"]
    m = st["masses"]
    fig.suptitle(f"BL-006 hipbelt B diet, belt M: base {m['base_g']:.0f} g -> {pk['base_g']:.0f} g "
                 f"(target {TARGET_G:.0f}, stretch {STRETCH_G:.0f}); as hunted {m['as_hunted_g']:.0f} -> "
                 f"{pk['as_hunted_g']:.0f} g.  Package: worst wing {pk['eval']['worst_wing_kpa']} kPa, "
                 f"hold {pk['eval']['median_hold']:.2f} / {pk['eval']['worst_hold']:.2f}",
                 fontsize=12, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    if path.stat().st_size > 1_500_000:
        from PIL import Image
        Image.open(path).convert("P", palette=Image.ADAPTIVE).save(path, optimize=True)
    return path


# =====================================================================================================================
# report
# =====================================================================================================================
def _lboz(g):
    lb = int(abs(g) // LB)
    oz = (abs(g) - lb * LB) / OZ
    return f"{'-' if g < 0 else ''}{lb} lb {oz:.1f} oz" if lb else f"{g / OZ:.1f} oz"


def report() -> str:
    st = study()
    m, b, pk = st["masses"], st["baseline"], st["package"]
    out = []
    w = out.append
    w("# BL-006 Hipbelt B diet\n")
    w("Owner: pack-designer, 2026-11-10. **Status: proposal. No released file, no shared module and no `corrie.py` row "
      "was changed.** Generated by `designs/pack_5200/concepts/hipbelt_diet.py --write` (every number below comes from "
      "that code; tests `tests/test_hipbelt_diet.py`). Masses from `huntkit/mass/ledger.py`, config "
      f"`{CONFIG}` (CORRIE B.2 on H1 with package C: the 7075 plate package and the CFRP pad backer are in). Pressure "
      "and slip from `huntkit/gendesign/hipbelt.py` over the 16 ANSUR II hip forms. Units: g, kPa, N; imperial in "
      "brackets.\n")
    w("## 0. Summary\n")
    hit = pk["base_g"] <= TARGET_G
    w(f"- **Belt B at belt M today (ledger): {m['as_hunted_g']:.1f} g as hunted, {m['base_g']:.1f} g base** "
      f"({_lboz(m['base_g'])}). The ticket's 559 g is the B.1 booking before package C; the ledger figure with C and "
      "the B.2 grip-print deletion is the honest start.")
    w(f"- **Recommended package {', '.join(PACKAGE)}: base {pk['base_g']:.1f} g ({_lboz(pk['base_g'])}), as hunted "
      f"{pk['as_hunted_g']:.1f} g ({_lboz(pk['as_hunted_g'])}).** Target 490 g: **{'met' if hit else 'NOT met'}**; "
      f"stretch 470 g: **{'met' if pk['base_g'] <= STRETCH_G else 'not met'}**.")
    w(f"- Of the {-pk['delta_g']:.1f} g out of base, **{-pk['physical_delta_g']:.1f} g is real mass off the belt** and "
      f"{holster_split()['addon_g']:.1f} g is the holster moving to the as-hunted line (owner decision; the hunter "
      f"carries it all the same). Already counted in today's base {m['base_g']:.1f} g.")
    w(f"- **Without the two gated items** (b stabilizers, c2 stiffener) the package is base {pk['ungated_base_g']:.1f} g: "
      f"target met, stretch {'met' if pk['ungated_base_g'] <= STRETCH_G else 'missed by ' + format(pk['ungated_base_g'] - STRETCH_G, '.1f') + ' g'}. "
      f"The next lever, if a test fails, is the foam pair d2 + d4 (XLPE L200 load and lumbar layers, "
      f"{pk['next_lever_g']:+.1f} g), which passes the model and lowers the median wing peak.")
    e = pk["eval"]
    w(f"- **Fit results kept:** package worst wing peak {e['worst_wing_kpa']} kPa (B {b['worst_wing_kpa']}), median "
      f"{e['median_wing_kpa']} (B {b['median_wing_kpa']}); lumbar worst {e['worst_lumbar_kpa']} (B "
      f"{b['worst_lumbar_kpa']}); hold {e['median_hold']:.3f} / {e['worst_hold']:.2f} median / worst (B "
      f"{b['median_hold']:.3f} / {b['worst_hold']:.2f}); padded tip to ASIS worst {e['min_asis_clear_mm']:.0f} mm "
      f"(B {b['min_asis_clear_mm']:.0f}).")
    a2 = next(r for r in st["items"] if r["key"] == "a2")
    w(f"- The biggest single saving ({-a2['g']:.1f} g) is a **booking error, not a design change**: the ledger still "
      "carries the old belt's 0.9 m of 50 mm strap, but belt B's 2:1 runs on 25 mm legs from the buckle half to the "
      "wing-tip D-ring. The 50 mm webbing is only two short buckle tabs. The 25 mm webbing was under-booked at the "
      "same time (section 3a).")
    w("- **Rejected:** the 38 mm buckle (record break 900 N, below the 1000 N C2 wing tension: SF/req 0.90). Items "
      "that fail the pressure gates are listed in section 2.")
    w("- **Gated:** the stabilizer deletion (b) and the 0.75 mm stiffener (c2) change things the fit model does not "
      "see (pivot roll control, wing roll-over). Each has a short prototype test (section 6) and stays reversible on "
      "the first prototype.\n")
    w("Reproduction first (acceptance): the same code on belt B gives worst wing peak "
      f"**{b['worst_wing_kpa']} kPa**, median {b['median_wing_kpa']}, lumbar worst {b['worst_lumbar_kpa']}, hold "
      f"**{b['median_hold']:.3f} / {b['worst_hold']:.2f}** (published 56.5 / 50.8 / 45.4 / 0.72 / 0.64, "
      "`hipbelt_results.json` summary B). Test `test_reproduces_belt_b`.\n")
    w("Screenshot: `outputs/screens/20261110_BL006_1.png` (grams saved per item against the worst wing-peak and "
      "worst-hold change).\n")

    w("## 1. Belt B part by part (ledger, belt M)\n")
    w("| Ledger id | Part | g | Job | Load path | Config | Margin on file (min SF/req) |")
    w("|---|---|---:|---|---|---|---|")
    for r in ledger_table():
        w(f"| `{r['id']}` | {r['name']} | {r['g']:.1f} | {r['job']} | {'yes' if r['load_path'] else ''} | "
          f"{r['config']} | {r['margin']} |")
    w(f"| | **belt system (ledger)** | **{m['ledger_belt_g']:.1f}** | | | as hunted | |")
    w(f"| | **base (holster add-on {m['holster_addon_g']:.1f} g out)** | **{m['base_g']:.1f}** | | | base | |\n")
    w("Notes: the ledger books the soft-goods load foam and the HDPE as load path; neither carries a rev C case (the "
      "HDPE floats, `hipbelt_structural.md` section 5), so their only gate is the pressure model. The stabilizers sit "
      "in the 50 mm webbing row; no load case on file uses them.\n")

    w("## 2. Each change against belt B (16 ANSUR II forms)\n")
    w(f"Gates: worst wing peak <= {WING_WORST_LIMIT} kPa and worst hold >= {HOLD_WORST_LIMIT} (ticket). Lumbar worst "
      f"is watched against belt B's {b['worst_lumbar_kpa']} kPa and the {LUMBAR_WATCH} kPa criterion. Grams are base "
      "configuration at belt M (negative saves).\n")
    w("| # | Change | g | Wing peak median / worst kPa | Lumbar worst | Hold median / worst | ASIS worst mm | "
      "Verdict | Why | Package | Gate test |")
    w("|---|---|---:|---|---:|---|---:|---|---|---|---|")
    w(f"| B | belt B as is | 0 | {b['median_wing_kpa']} / {b['worst_wing_kpa']} | {b['worst_lumbar_kpa']} | "
      f"{b['median_hold']:.3f} / {b['worst_hold']:.2f} | {b['min_asis_clear_mm']:.0f} | | | | |")
    for r in st["items"]:
        w(f"| {r['key']} | {r['change']} | {r['g']:+.1f} | {r['median_wing_kpa']:.1f} / {r['worst_wing_kpa']} | "
          f"{r['worst_lumbar_kpa']} | {r['median_hold']:.3f} / {r['worst_hold']:.2f} | {r['min_asis_clear_mm']:.0f} | "
          f"**{r['verdict']}** | {r['why']} | {'yes' if r['in_package'] else ''} | {r['gate']} |")
    w(f"| **pkg** | **package {', '.join(PACKAGE)} (one combined model run)** | **{pk['delta_g']:+.1f}** | "
      f"{e['median_wing_kpa']} / {e['worst_wing_kpa']} | {e['worst_lumbar_kpa']} | {e['median_hold']:.3f} / "
      f"{e['worst_hold']:.2f} | {e['min_asis_clear_mm']:.0f} | **{pk['verdict'][0]}** | {pk['verdict'][1]} | | |\n")
    w("Items without a model effect (a2, b, e, f1, f2) carry belt B's numbers: the parts are not in the fit model.\n")

    w("## 3. Item notes\n")
    cl = st["closure"]
    w("### 3a. Front closure\n")
    w(f"- **a1, 38 mm buckle: REJECT.** `buckle_side_release_38mm` breaks at {BUCKLE38.require('breaking_strength_n'):.0f} N "
      f"(estimate record). Rev C C2 puts T = {_c2_T():.0f} N through the buckle (`hipbelt_structure.load_sets`), so "
      f"SF/req {BUCKLE38.require('breaking_strength_n') / _c2_T():.2f}; the 50 mm buckle is 1.50. It would save "
      f"{BUCKLE50.require('mass_g') - BUCKLE38.require('mass_g'):.0f} g. Only a 38 mm buckle with a tested break "
      "of at least 1000 N could come back (materials-engineer).")
    w(f"- **a2, book the closure as belt B builds it.** Routing (hipbelt_structural.md section 5): anchor on the buckle "
      "half, round the D-ring on the wing tip, back through the heavy ladder lock on the buckle half, then the tail. "
      "So the only 50 mm webbing is two buckle tabs. Webbing actually needed per size (clothing +"
      f"{CLOTHING_MM:.0f} mm on the circumference, lock {LOCK_FROM_FRONT_MM:.0f} mm from the front centre, anchor "
      f"{ANCHOR_MM:.0f} mm, D-ring tab {DRING_TAB_MM:.0f} mm, tail >= {TAIL_MIN_MM:.0f} mm at the largest waist):\n")
    w("| Size | Leg at max / min waist mm | Tail at min waist mm | 25 mm needed m | 50 mm needed m | Booked g | Needed g | Delta g |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for s, c in cl.items():
        w(f"| {s} | {c['leg_max_mm']:.0f} / {c['leg_min_mm']:.0f} | {c['tail_at_min_mm']:.0f} | {c['need_25_m']:.2f} | "
          f"{c['need_50_m']:.2f} | {c['booked_g']:.1f} | {c['new_g']:.1f} | {c['delta_g']:+.1f} |")
    w(f"\n  The booked 0.6 m of 25 mm is about half of what the 2:1 needs ({cl['M']['need_25_m']:.2f} m at M), so this "
      "row also corrects an under-booking. Net it still saves, because 0.9 m of 50 mm strap goes.")
    fs = st["front_strap"]
    w("- **Comfort of a narrower front strap.** Belt B's front is the 2:1's two 25 mm legs side by side (50 mm), not a "
      "single strap. Line pressure T_req x curvature / width at the sharpest curvature between the wing tip and the "
      f"front centre: 50 mm {fs[2]['median_kpa']:.0f} / {fs[2]['worst_kpa']:.0f} kPa (median / worst), 38 mm "
      f"{fs[1]['median_kpa']:.0f} / {fs[1]['worst_kpa']:.0f}, one 25 mm width (legs stacked) {fs[0]['median_kpa']:.0f}"
      f" / {fs[0]['worst_kpa']:.0f}. A narrower front strap raises it in proportion (38 mm: x"
      f"{50 / 38:.2f}). Build rule kept: **the two legs run side by side, never stacked**. The figure is a watch item "
      "only: the fit model has no front strap, the abdomen is soft and webbing bridges the sharpest curvature; HB-1 "
      "should put a sensor just in front of the wing tip.\n")
    w("### 3b. Stabilizer straps\n")
    w(f"- **b, delete both ({st['stabilizers_g']:.1f} g).** With belt B the wing is stitched to the plate (fixed "
      "joint, the cone is in the pattern), the plate is held on the Ti pin in x, z and pitch, the lumbar pad bears on "
      "the frame, and the only intended freedom is roll +/-8 deg on the pin. A stabilizer pulling the wing root "
      "toward the lower stay (z 60) about 100 mm off the pin can only resist that roll, which is the motion the pivot "
      "is there to allow. No rev C case, no frame model spring and no fit-model term uses the stabilizers, so the "
      "pressure and hold numbers do not move. What it can lose: damping of belt roll on a side-hill. Gate **HB-D1**. "
      "The printed anchor pads on the frame stay, so the straps can be refitted without a frame change.\n")
    w("### 3c. Wing stiffener\n")
    w(f"- Booked HDPE 41.0 g; the developed outline gives {st['hdpe_B_g']:.1f} g (belt_bom ignores the 15 mm soft-tip "
      "gap; deltas here use the developed figure on both sides). The model is insensitive to thickness (hoop stiffness "
      "is a small share against the foam), as `hipbelt_fit.md` section 3.2 found. The fit model cannot see wing "
      "roll-over, which goes as t^3: 0.75 mm keeps 42 % of the bending stiffness, 0.5 mm 12.5 %, the perforated sheet "
      "an estimated ~49 % (ASSUMPTION) at more labour.")
    w("- **c1 (shorter)** moves the HDPE end 20 mm further behind the ASIS (the padded tip, which sets the ASIS "
      "result, does not move) but shrinks the pocket room on the stiffened zone by 20 mm (IMP-5 is already short at "
      "M). Not taken.")
    w("- **c2 0.75 mm taken**, gated by **HB-D2** (wing roll-over).\n")
    w("### 3d. Foam\n")
    w(f"- Code note: `hipbelt_concepts.B` inherits C0's wing stack EVA 45C 6 + EVA 30C 5; `hipbelt_fit.md` section 4.1 "
      "says 45C 5 + 30C 6. The ledger books the code (load foam 30.1 g), so the variants start from the code.")
    w(f"- d5 models the softer wedge as a taper loss: x{st['wedge_taper_factor']:.3f} (records: EVA 45C secant "
      f"{E_EVA45:.0f} kPa, XLPE L200 {E_XLPE:.0f} kPa, at belt B's worst lumbar peak). ASSUMPTION; HB-1 settles it.")
    w("- XLPE L200 (Minicel class) has a lower compression set (12 %) than EVA 45C (15 %) in the records, so creep is "
      "not the objection; stiffness is. d2 and d4 pass and even lower the peaks (a softer layer spreads the load), d5 "
      "fails on hold (the wedge loses its taper), d1 and d3 pass but save little.")
    w("- **No foam change is in the package (DECISION).** The package meets the stretch without them, and a 2.5x softer "
      "load layer changes how firm the belt feels under 68 kg, which the linear Winkler model cannot judge (strains "
      "near 30 % at the peaks, past the record's 25 % secant point). d2 + d4 are the reserve: build one prototype "
      "wing pair in XLPE for HB-1 if b or c2 fails its test.\n")
    hsp = st["holster"]
    w("### 3e. Bottle holster\n")
    w(f"- Holster {hsp['total_g']:.1f} g = add-on {hsp['addon_g']:.1f} g (tube, base, back, straps, G-hooks, cinch) + "
      f"{hsp['tabs_g']:.1f} g of wing tabs bartacked to the shell, which stay in base. It is outside the fit model "
      "(hipbelt_fit.md section 7: under 2 % of the hip load). Moves base, not the as-hunted mass.\n")
    ps = st["pad_seat"]
    w("### 3f. Pad seat\n")
    w(f"- Pad seat today: rails 10.2, backer (CFRP 0.8 after C-4) 35.3, slip liner 4.7, sleeve {ps['sleeve_g']}, "
      f"bottom strap {ps['strap_g']} g. The backer, rails and liner set the channel depth play and the C-4 margins "
      "(load path in effect): untouched. The liner also keeps the CFRP backer off the aluminium spine (galvanic "
      "couple), a second reason to keep it.")
    w(f"- **f1** bottom retention: 25 mm strap + ladder lock {ps['strap_g']} g -> 2 mm Dyneema cord {CORD_TIE_M} m "
      f"+ spring cord lock {ps['cord_g']} g. The pad is pressed onto the pan by the lumbar push in every carry case; "
      "the bottom tie only keeps it in place with the belt off. **f2** top sleeve Hypalon "
      f"({GSM_HYP:.0f} g/m2) -> 1000D Cordura ({GSM_1000D:.0f} g/m2, already in the belt BOM), {ps['sleeve_1000d_g']} g; "
      "hot-cut edges. Gate **HB-D3**.\n")

    w("## 4. Recommended package and the two weights\n")
    w("| Size | Base today g | Base with package g | As hunted today g | As hunted with package g |")
    w("|---|---:|---:|---:|---:|")
    for s, v in st["per_size"].items():
        w(f"| {s} | {v['base_today_g']:.1f} | **{v['base_pkg_g']:.1f}** | {v['as_hunted_today_g']:.1f} | "
          f"{v['as_hunted_pkg_g']:.1f} |")
    w(f"\nBelt M: **base {pk['base_g']:.1f} g ({_lboz(pk['base_g'])}), as hunted {pk['as_hunted_g']:.1f} g "
      f"({_lboz(pk['as_hunted_g'])})**; target {TARGET_G:.0f} g {'met' if hit else 'NOT met'} by "
      f"{TARGET_G - pk['base_g']:.1f} g, stretch {STRETCH_G:.0f} g "
      f"{'met' if pk['base_g'] <= STRETCH_G else 'missed'} by {abs(STRETCH_G - pk['base_g']):.1f} g. "
      f"Benchmark: Stone Glacier 3-piece belt 363 g (`docs/research/hipbelt_fit.md` section 3), which has no pockets, "
      "no pad seat and no pivot hardware.\n")
    w(f"Whole pack (belt M, {CONFIG}): {m['pack_total_g']:.1f} g booked today; the package takes "
      f"{-pk['physical_delta_g']:.1f} g of real mass off and moves {holster_split()['addon_g']:.1f} g to the "
      "as-hunted line. The pack-level base figure belongs to BL-013 (roll-up), not here.\n")

    w("## 5. Load-path changes for BL-010\n")
    w("| Row | Part | Change | Factored load to confirm | Margin on file | What to check |")
    w("|---|---|---|---|---|---|")
    w(f"| BL006-1 | 50 mm buckle tabs (a2) | 0.9 m strap -> 2 x 140 mm 50 mm nylon tabs doubled round the buckle bars; "
      "the 25 mm anchor box-X and the lock tab are bartacked onto them | T C2 1000 N per side through the tab "
      "(`hipbelt_structure.load_sets`) | buckle 1.50; anchor box-X not checked on the buckle side | box-X of the 25 mm "
      "anchor and the lock tab onto the 50 mm tab (tex 135), tab round the buckle bar |")
    w("| BL006-2 | 25 mm 2:1 webbing (a2) | length re-booked only; same webbing, routing, lock and D-ring | as hipbelt_structural.md section 5 | "
      f"lock slip 1.15 (test-qualified), webbing {json.loads((ANALYSIS / 'hipbelt_structural_results.json').read_text())['tab']['webbing_25']['sf']:.1f} | "
      "no new check; confirm the lock leg uses the routed length (no change expected) |")
    w("| BL006-3 | stabilizer straps (b) | deleted | none on file (no case uses them) | n/a | confirm no rev C "
      "case or frame spring depends on the hip_stabilizer_anchor pads; side-hill roll is a fit test (HB-D1), not strength |")
    w("| BL006-4 | wing stiffener HDPE 1.0 -> 0.75 mm (c2) | floats, carries no net tension | n/a | floats: no "
      "creep path (section 5) | confirm the D-ring tab check does not credit the HDPE (it does not: shell + 1000D) |\n")
    w("Rejected, for the record: 38 mm buckle (a1), SF/req 0.90 at C2 on the record value.\n")

    w("## 6. Assumptions and the tests that settle them\n")
    w(f"- ASSUMPTION closure geometry: clothing +{CLOTHING_MM:.0f} mm, lock station {LOCK_FROM_FRONT_MM:.0f} mm, "
      f"anchor {ANCHOR_MM:.0f} mm, ring wrap {RING_WRAP_MM:.0f}, lock wrap {LOCK_WRAP_MM:.0f}, buckle tab "
      f"{BUCKLE_TAB_MM:.0f} mm each. Settled by cutting the first prototype's webbing to these lengths and fitting it "
      "on the smallest and largest tester of each size (cut list check, no new test ID).")
    w("- ASSUMPTION stabilizers carry no needed function with the fixed joint and pivot. **HB-D1:** 68 kg sandbag, "
      "20 min side-hill traverse (about 25 deg) and a 10 min step-down set, stabilizers cinched vs fully slack, same "
      "tester, belt tension set to T_req with the luggage scale. Pass: belt creep within HB-3's 15 mm both ways and "
      "no tester-reported roll or sway difference. Fail: refit the straps (+22 g).")
    w("- ASSUMPTION a 0.75 mm HDPE keeps the wing from rolling over at the crest. **HB-D2:** one wing with 0.75 mm, "
      "one with 1.0 mm on the same belt, 68 kg, 30 min hike; mark the crest line on both wings and photograph the top "
      "edge at the crest every 10 min. Pass: top-edge fold under 10 mm and creep within HB-3, equal to the 1.0 mm "
      "side; plus HB-1 pressure within 10 % of the 1.0 mm side. Fail: back to 1.0 mm.")
    w(f"- ASSUMPTION perforated-sheet stiffness (1 - phi)^2, phi {PERF_PHI}: only used for c4 (not taken).")
    w("- ASSUMPTION a softer wedge loses taper by its extra compression (d5). HB-1 settles it if d5 is ever taken.")
    w("- ASSUMPTION the pad-seat bottom tie carries no carry load. **HB-D3:** with the belt on the frame, swing the "
      "pack off and set it down 20 times, then hang the pack by the belt from the lumbar pad for 1 min with 10 kg in "
      "the bag. Pass: the pad stays seated, the cord lock holds, the sleeve does not fray at the flange edge.")
    w("- The fit model's own assumptions (mu 0.30, tissue column, 2:1 efficiency 0.85) are unchanged and listed in "
      "`hipbelt_fit.md` section 11.\n")

    w("## 7. Found, not fixed\n")
    w("- `hipbelt_fit.md` section 4.1 gives belt B's wing stack as EVA 45C 5 + EVA 30C 6; `hipbelt_concepts.B` (and so "
      "the ledger) uses 45C 6 + 30C 5. One of them should be corrected (owner of hipbelt_concepts).")
    w(f"- `hipbelt_concepts.belt_bom` books the HDPE without the soft-tip gap: 41.0 g booked vs {st['hdpe_B_g']:.1f} g "
      "developed.")
    w("- The ledger's belt row `50 mm belt webbing 0.9 m ...` is the C0 1:1 booking; the 2:1's 25 mm webbing is "
      "under-booked by about half. BL-013 / the ledger owner should take section 3a's numbers once the owner agrees.")
    w(f"- Front-strap pressure over the anterior hip ({fs[2]['median_kpa']:.0f}-{fs[2]['worst_kpa']:.0f} kPa on the "
      "crude line-load estimate) is above the 48.6 kPa criterion and is not in the fit model. HB-1 should measure "
      "just in front of the wing tip.")
    return "\n".join(out) + "\n"


def write():
    DOC.write_text(report())
    return chart()


if __name__ == "__main__":
    s = study()
    print(json.dumps({"masses": s["masses"], "baseline": s["baseline"], "package": s["package"]}, indent=1))
    for r in s["items"]:
        print(f"{r['key']:3s} {r['g']:+6.1f} g  wing {r['median_wing_kpa']:5.1f}/{r['worst_wing_kpa']:5.1f}  "
              f"lumbar {r['worst_lumbar_kpa']:5.1f}  hold {r['median_hold']:.3f}/{r['worst_hold']:.2f}  "
              f"{r['verdict']:6s} {r['why']}")
    if "--write" in sys.argv:
        print(write(), DOC)
