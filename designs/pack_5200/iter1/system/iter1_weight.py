"""Iteration 1, system weight track (BL-062): everything but the frame body and its pins / hardware.

Pareto of the after-tests base mass (belt M, crown kit M) by function, the lighter alternative per item, and three
coherent options scored on the owner's rubric (docs/RUBRIC.md: strong is a gate, then lighter, then looks).

Every gram comes from the roll-up rows (``weight_rollup_v2.scenario_rows``, which are ledger rows plus the gated
steps), ``build_geometry`` panels, or a material record. Every number that is not one of those is an ASSUMPTION named
in ``ASSUMPTIONS`` with the test that settles it. Research behind the new materials: docs/research/weight_iter1.md.

Proposals only: no released pattern, ledger config or roll-up step is changed here.

    python designs/pack_5200/iter1/system/iter1_weight.py            # writes .json, .md, screenshots
    python designs/pack_5200/iter1/system/iter1_weight.py --check    # prints the answer, writes nothing
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parents[1]
ROOT = PACK.parents[1]
for p in (str(PACK), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from huntkit.materials import load  # noqa: E402

LB, OZ = 453.592, 28.3495
SIZE = "M"
USD_PER_EUR = 1.09            # ASSUMPTION FX (same rate as the repo's hardware records)
DOC = HERE / "iter1_weight.md"
RESULT = HERE / "iter1_weight.json"
SCREENS = ROOT / "outputs" / "screens"
SHOT_PREFIX = "20261124_iter1_weight_"
OWN_CODE = "designs/pack_5200/iter1/system/iter1_weight.py"


# =====================================================================================================================
# inputs
# =====================================================================================================================
def _R():
    import weight_rollup_v2 as R
    return R


def _WP():
    import weight_push as WP
    return WP


@functools.lru_cache(maxsize=None)
def rows(scen: str, cfg: str = "base") -> tuple:
    """Roll-up rows of scenario P (proven now) or A (after tests), one weight configuration, belt M."""
    R = _R()
    with contextlib.chdir(ROOT):              # the roll-up's sources read repo-relative paths
        return tuple(dict(r) for r in R.cfg_rows(R.scenario_rows(scen, SIZE), cfg))


def total(scen: str, cfg: str = "base") -> float:
    return round(sum(r["g"] for r in rows(scen, cfg)), 1)


def frame_g(scen: str) -> float:
    return round(sum(r["g"] for r in rows(scen) if r["system"] == "frame"), 1)


@functools.lru_cache(maxsize=None)
def panels() -> dict:
    """build_geometry panels by piece id (the source the ledger's back-panel and J-strap rows are computed from)."""
    import build_geometry as BG
    with contextlib.chdir(ROOT):
        return {p["id"]: p for p in BG.build()[1]["panels"]}


def rec(mid: str):
    return load(mid)


def gsm(mid: str) -> float:
    return float(rec(mid).require("areal_density_gsm"))


def usd_m2(mid: str) -> float:
    """Record price per m2: USD per yard over the record roll width (the bag_weight_plan basis)."""
    m = rec(mid)
    c = m.cost_usd
    assert c and c["per"] == "yd", mid
    return c["value"] / (0.9144 * m.require("roll_width_mm") / 1000.0)


def row_g(scen: str, pattern: str, system: str | None = None) -> float:
    rx = re.compile(pattern)
    return round(sum(r["g"] for r in rows(scen) if rx.search(r["name"]) and (system is None or r["system"] == system)), 2)


# =====================================================================================================================
# 1. Pareto: functional items (every non-frame base row lands in exactly one)
# =====================================================================================================================
# (item id, label, system, regex on the row name); first match wins within a system. scope "frame" = the frame track.
RULES = [
    ("frame_hw", "fairleads, fairlead / hinge pins and sleeves (frame track)", "attachment",
     r"printed fairleads|7075 pins|UHMWPE sleeves|fairlead pins|hinge pins|US1 fairlead pins"),
    ("back_panel", "back panel: mesh, rail foam, backer strip, sleeves, upper pad", "back", r"back panel|BL-005|K-1"),
    ("spreader", "back spreader, Sandwich v2 (structural)", "back", r"spreader"),
    ("belt_padseat", "lumbar pad seat", "belt", r"pad seat|C-4|BL-006 f"),
    ("belt_loadpath", "belt plate, hub, latch, doublers (rev C load path)", "belt", r"load path|C-1\+C-2"),
    ("imp5", "IMP-5L hipbelt pocket", "belt", r"IMP-5L"),
    ("belt_closure", "belt 50 mm closure, 2:1 pull, stabilizers", "belt",
     r"50 mm|stabiliz|2:1|D-ring|lock legs|tail keepers|BL-006 b"),
    ("belt_trims", "belt trims: camo shards, rifle tabs, holster tabs, grip", "belt", r"SH-05|rifle tabs|IMP-3|grip"),
    ("belt_padding", "belt wings + lumbar: foams, stiffener, mesh faces, shells", "belt", r"."),
    ("imp6", "IMP-6 shoulder-strap phone pocket", "harness", r"IMP-6"),
    ("yoke", "yoke plate + cover (rev C fix C-7)", "harness", r"yoke"),
    ("j_straps", "J-straps: shell, mesh face, foams", "harness", r"J-strap"),
    ("lifters_sternum", "load lifters + sternum", "harness", r"lifter|sternum"),
    ("door_zip", "D2 door zip #10 + 2 sliders + cord pulls", "bag_shell", r"door zip|door sliders|cord pulls"),
    ("rolltop", "roll-top: collars, hem, HDPE strip, clips", "bag_shell", r"B-06|B-07|roll-top"),
    ("carry", "bow / rifle / tripod carry parts", "bag_shell", r"bow riser|B-11|muzzle|hard-point"),
    ("shell_panels", "shell panels: B-01, gussets, door, hinge band, floor, camo blade + kick bands", "bag_shell", r"."),
    ("rolltop", "roll-top: collars, hem, HDPE strip, clips", "straps_compression", r"roll|RTM"),
    ("haul_wraps", "haul wraps W1-W3: webbing, rated hooks, heavy ladder locks, keepers", "straps_compression",
     r"W-|W1|W3|haul|A-2|S9"),
    ("wings", "side wings (deleted in after tests)", "straps_compression", r"wing|M-01|SH-06"),
    ("carry", "bow / rifle / tripod carry parts", "straps_compression", r"B-26|tripod"),
    ("us_cradle", "under-strap cradle US1/US2: webbing, cams, backstops, anchors", "straps_meat", r"(?<!IM/)\bUS"),
    ("im_straps", "internal meat straps IM1-IM3: webbing, cams, hooks, eyes, ports", "straps_meat", r"."),
    ("hood", "crown hood (deleted in after tests)", "attachment", r"hood|B-19|B-20"),
    ("guys", "port guys, B-25 bridle, B-22 tabs, guy hardware", "attachment", r"guy|B-22|B-25|B-27|GBL"),
    ("bag_hooks", "bag hooks 38 mm, IM3 carabiners, IM2 hooks / tongues, sleeves, keepers", "attachment",
     r"bag hooks|hook sleeves|carabiner|IM2|T2 tongues|B-23|elastic keepers"),
    ("attach_soft", "bag-side spreaders B-17 / B-18, swells B-13x, eyes, bag-side straps, thread", "attachment", r"."),
    ("fp", "FP-L/R hip-reach pockets", "bag_pockets", r"FP-L"),
    ("imp2", "IMP-2 hydration sleeve", "bag_pockets", r"IMP-2"),
    ("imp4", "IMP-4 door kill-kit pocket", "bag_pockets", r"IMP-4"),
    ("small_carry", "IMP-8 bow cam cup + E-5 pole quiver", "bag_pockets", r"IMP-8|E-5"),
    ("fly_pocket", "F-02 fly base pocket", "fly", r"."),
    ("thread_labels", "thread + labels (misc)", "misc", r"."),
]
LABEL = {}
for _i, _l, _s, _x in RULES:
    LABEL.setdefault(_i, _l)
SCOPE_FRAME = {"frame_hw", "spreader"}     # spreader: structural part owned by structural-fea-engineer (R-3)


_PREFIX = re.compile(r"^(REMOVED[^:]*: |[^:]*kept until [^:]*: )")   # roll-up bookkeeping prefixes (P_F restore rows)


def classify(row: dict) -> str:
    if row["system"] == "frame":
        return "frame"
    name = _PREFIX.sub("", row["name"])
    for item, _lab, sysname, rx in RULES:
        if row["system"] == sysname and re.search(rx, name):
            return item
    return "other_" + row["system"]


def items(scen: str) -> dict:
    out: dict = {}
    for r in rows(scen):
        k = classify(r)
        out[k] = out.get(k, 0.0) + r["g"]
    return {k: round(v, 1) for k, v in out.items()}


# =====================================================================================================================
# 2. levers (each one computed from rows / panels / records; status says where it comes from)
# =====================================================================================================================
MESH_LIGHT_GSM = 230.0     # ASSUMPTION MESH-230 (Extremtextil art. 73068, secondary; record pending), research 3.2
MESH_MID_GSM = 320.0       # ASSUMPTION MESH-320 (Extremtextil art. 70807 category listing; page title says 390)
MESH_LIGHT_EUR_M, MESH_LIGHT_ROLL_M = 12.90, 1.6     # research 3.2 (secondary)
MESH_MID_EUR_M, MESH_MID_ROLL_M = 19.90, 1.6         # roll width ASSUMPTION (not on the listing)
TI_TRIGLIDE_G = 4.0        # ASSUMPTION TI-TG (Brautigam 1 in Ti tri-glide, secondary; no rating published)
TI_TRIGLIDE_USD = 12.0     # ASSUMPTION TI-TG-COST (price not found)
SS_TRIGLIDE_EUR = 3.10     # triglide_25mm record source (Extremtextil art. 70460, incl. VAT)
DYNEEMA_G_M, DYNEEMA_N, DYNEEMA_EUR_M = 10.2, 11768.0, 2.90   # Extremtextil Dyneema thin 25 mm (fetched), research 3.3
LOOP_M = 0.08              # hard-point loop length, CORRIE F row '4 hard-point loops: 25 mm webbing 0.08 m each'
TAB_M = 0.06               # ASSUMPTION TAB-L: a toggle tab on a clip-on pocket, 25 mm webbing x 60 mm


def _poly_g_m() -> float:
    return float(rec("poly_webbing_25mm").require("mass_g_m"))


def loop_g() -> float:
    return _poly_g_m() * LOOP_M


def tab_g() -> float:
    return float(rec("pom_toggle").require("mass_g")) + _poly_g_m() * TAB_M


def mesh_light() -> dict:
    """N1: BP-01 back mesh, BP-03 crown pad face and HS-J2 J-strap faces from the 380 gsm estimate to 230 gsm."""
    P = panels()
    pieces = {k: P[k]["mass_g_total"] for k in ("BP-01", "BP-03", "HS-J2")}
    g0 = sum(pieces.values())
    area = g0 / gsm("spacer_mesh_3d")
    new_usd = MESH_LIGHT_EUR_M * USD_PER_EUR / MESH_LIGHT_ROLL_M
    f = 1 - MESH_LIGHT_GSM / gsm("spacer_mesh_3d")
    return {"pieces_g": pieces, "delta_g": -g0 * f, "cost_usd": area * (new_usd - usd_m2("spacer_mesh_3d")),
            "split": {"back_panel": -(pieces["BP-01"] + pieces["BP-03"]) * f, "j_straps": -pieces["HS-J2"] * f}}


def mesh_belt() -> dict:
    """N2: belt wing and lumbar mesh faces 380 -> 320 gsm (the hip contact faces keep a heavier mesh)."""
    g0 = row_g("A", r"spacer_mesh_3d", "belt")
    area = g0 / gsm("spacer_mesh_3d")
    new_usd = MESH_MID_EUR_M * USD_PER_EUR / MESH_MID_ROLL_M
    return {"pieces_g": {"belt faces": g0}, "delta_g": -g0 * (1 - MESH_MID_GSM / gsm("spacer_mesh_3d")),
            "cost_usd": area * (new_usd - usd_m2("spacer_mesh_3d"))}


def ti_backstops() -> dict:
    """N3: the two US stainless tri-glide backstops (orchestrator 2026-11-13, gate US-BS) in titanium."""
    ss = float(rec("triglide_25mm").require("stainless_alt_mass_g"))
    return {"n": 2, "ss_g": ss, "ti_g": TI_TRIGLIDE_G, "delta_g": 2 * (TI_TRIGLIDE_G - ss),
            "cost_usd": 2 * (TI_TRIGLIDE_USD - SS_TRIGLIDE_EUR * USD_PER_EUR)}


def fabric_swap(g0: float, old: str, new: str) -> dict:
    area = g0 / gsm(old)
    return {"g0": g0, "area_m2": area, "delta_g": -g0 * (1 - gsm(new) / gsm(old)),
            "cost_usd": area * (usd_m2(new) - usd_m2(old))}


def collar_frame_side() -> dict:
    """N4: B-06f frame-side collar ULTRA 200X -> 70D ripstop (the collar B-06 is already 70D)."""
    return fabric_swap(row_g("A", r"^CORRIE F: B-06f"), "challenge_ultra_200", "nylon_ripstop_70d")


def sleeves_70d() -> dict:
    """N5: back-panel rail sleeves BP-05 (pair) and crown pad back BP-07 Robic 210D -> 70D ripstop."""
    P = panels()
    g0 = P["BP-05"]["mass_g_total"] + P["BP-07"]["mass_g_total"]
    return fabric_swap(g0, "robic_210d_ripstop", "nylon_ripstop_70d")


def wraps_dyneema() -> dict:
    """N6: haul-wrap webbing W1-W3 (as cut for carry, BL-031, A-2 tails) 25 mm polyester -> thin Dyneema 25 mm."""
    g0 = row_g("A", r"W-web|A-2|W1-W3 cut for carry", "straps_compression")
    length = g0 / _poly_g_m()
    return {"length_m": length, "g0": g0, "delta_g": length * (DYNEEMA_G_M - _poly_g_m()),
            "cost_usd": length * (DYNEEMA_EUR_M * USD_PER_EUR - rec("poly_webbing_25mm").cost_usd["value"]),
            "web_break_n": DYNEEMA_N}


def shells_ultragrid() -> dict:
    """N7: J-strap shells (HS-J1) and belt wing / lumbar shells 330D CORDURA -> ULTRAGrid 210D (the bag body cloth)."""
    gj, gb = panels()["HS-J1"]["mass_g_total"], row_g("A", r"shell \(cordura_330d", "belt")
    out = fabric_swap(gj + gb, "cordura_330d_nylon66", "ultragrid_210d_uhmwpe_ripstop")
    f = out["delta_g"] / (gj + gb)
    out["split"] = {"j_straps": gj * f, "belt_padding": gb * f}
    return out


def modular(item: str, n_points: int = 2) -> dict:
    """M-x: a sewn pocket becomes a clip-on module shipped in the box. Base keeps n webbing loops; the module carries
    n POM-toggle tabs. Base saves the pocket minus the loops; as hunted pays loops + tabs."""
    g = items("A")[item]
    return {"pocket_g": g, "base_delta_g": -g + n_points * loop_g(),
            "as_hunted_delta_g": n_points * (loop_g() + tab_g()),
            "cost_usd": n_points * (rec("pom_toggle").cost_usd["value"]
                                    + (LOOP_M + TAB_M) * rec("poly_webbing_25mm").cost_usd["value"])}


def levers() -> list:
    WP = _WP()
    m1, m2, ti, col, slv, dy, sh = (mesh_light(), mesh_belt(), ti_backstops(), collar_frame_side(), sleeves_70d(),
                                    wraps_dyneema(), shells_ultragrid())
    z8, cams = WP.door_zip8(), WP.cams_to_ladders()
    cam_usd = rec("cam_25mm_al").cost_usd["value"] - rec("ladder_lock_25mm_heavy").cost_usd["value"]
    L = []

    def add(**k):
        k.setdefault("as_hunted_delta_g", k["base_delta_g"])
        k["base_delta_g"] = round(k["base_delta_g"], 1)
        k["as_hunted_delta_g"] = round(k["as_hunted_delta_g"], 1)
        k["cost_usd"] = round(k["cost_usd"], 2)
        L.append(k)

    add(key="N1", item="back_panel + j_straps", status="new", risk="medium",
        change="spacer mesh 380 -> 230 g/m2 on the back panel BP-01, crown pad face BP-03 and J-strap faces HS-J2",
        base_delta_g=m1["delta_g"], cost_usd=m1["cost_usd"],
        strength="no load path (body-contact face); no HA-LS-1 row or bag load point touches it",
        durability="thinner (3.0 vs 4.5 mm) face: less air gap, faster wear where the pack rubs. The record's own note "
                   "says the mesh abrades in 1-2 seasons at the hip, so the hip faces are left out (N2)",
        test="MESH-1 Martindale (ASTM D4966) both meshes to 20 000 rev + MESH-2 3-tester 2 h sweat carry at 30 kg "
             "(BP-3 back-pressure strips under the rails); fallback today's mesh",
        look="none visible from outside (wearer face); finer texture on the back panel",
        records=["spacer_mesh_3d_230 (3 mm, 230 g/m2): gsm, thickness, compression, abrasion, roll width, price"],
        source="build_geometry panels BP-01/BP-03/HS-J2 x (1 - 230/380); research 3.2",
        split={k: round(v, 1) for k, v in m1["split"].items()})
    add(key="N2", item="belt_padding", status="new", risk="low",
        change="belt wing and lumbar mesh faces 380 -> 320 g/m2 (hip faces keep a dense mesh)",
        base_delta_g=m2["delta_g"], cost_usd=m2["cost_usd"],
        strength="no load path (face fabric)",
        durability="320 g/m2 is a 3 mm inelastic mesh sold for backpacks; hip abrasion is the risk",
        test="MESH-1 (same lot) + HB-1 hipbelt pressure / hold with the 3 mm face; fallback today's mesh",
        look="none visible",
        records=["spacer_mesh_3d_320 (3 mm inelastic): gsm (listing 320 vs page title 390), abrasion, roll width"],
        source="ledger belt rows 'spacer_mesh_3d' x (1 - 320/380); research 3.2")
    add(key="N3", item="us_cradle", status="new", risk="medium",
        change="US1/US2 tri-glide backstops stainless 11 g -> titanium 4 g (2)",
        base_delta_g=ti["delta_g"], cost_usd=ti["cost_usd"],
        strength="the US rows are governed by the 25 mm cam (1100 N slip, margin 1.53 on 720 N) and the box-X "
                 "(4.43); the backstop is not credited in any SF row. It must still stop a slipping cam: same US-BS "
                 "gate as the stainless part. Ti-6Al-4V (record) is stronger than 304 per section",
        durability="titanium does not corrode; webbing wear on a thinner bar edge unknown",
        test="US-BS run on the Ti tri-glide (cam slipped to the backstop, 1080 N hold, dry / wet / -20 C, 5 samples) "
             "+ weigh 5; fallback stainless",
        look="none (inside the cradle)",
        records=["triglide_25mm_ti: mass (4 g secondary), bar section, rated hold"],
        source="triglide_25mm record stainless_alt_mass_g; research 3.4")
    add(key="N4", item="rolltop", status="new", risk="medium",
        change="frame-side roll-top collar B-06f ULTRA 200X -> 70D ripstop (the aft collar B-06 is already 70D)",
        base_delta_g=col["delta_g"], cost_usd=col["cost_usd"],
        strength="no load point: the roll-top clips RT / RTM sit on the hem B-07 and the gusset B-03, not on B-06f",
        durability="B-06f rides against the crown top bar and the B-25 bridle when rolled: 70D (Martindale >10 000) "
                   "against ULTRA's Taber 4400 is a real abrasion step down",
        test="AB-2 crown-bar rub: a rolled 70D collar on a bar offcut with the bridle, 5 000 cycles of the pack's "
             "pitch swing, no hole; fallback ULTRA 200X",
        look="better: 70D comes in the solid house colours (ULTRA has few colours, record ir_notes)",
        records=[], source="corrie_f row B-06f x (1 - 92/133); records")
    add(key="N5", item="back_panel", status="new", risk="low",
        change="rail sleeves BP-05 (pair) and crown pad back BP-07: Robic 210D -> 70D ripstop",
        base_delta_g=slv["delta_g"], cost_usd=slv["cost_usd"],
        strength="no rated load: the sleeve holds the rail foam and the carbon backer on the stay line",
        durability="the sleeve back sits between the backer strip and the stay; carbon-edge chafe on 70D is the risk",
        test="SLV-1: sleeve on the backer strip edge, 10 000 rub cycles at the rev C skin pressure, no wear-through; "
             "fallback 210D",
        look="none (hidden)", records=[], source="build_geometry panels BP-05/BP-07 x (1 - 92/140); records")
    add(key="N6", item="haul_wraps", status="new", risk="high",
        change="haul-wrap webbing W1-W3 (cut for carry) polyester 18 g/m -> thin Dyneema 25 mm 10.2 g/m",
        base_delta_g=dy["delta_g"], cost_usd=dy["cost_usd"],
        strength=f"webbing break {dy['web_break_n']:.0f} N vs 225 N factored (S9): x{dy['web_break_n'] / 225:.0f}; "
                 "box-X 3186 N is the thread path (unchanged); the governing part is the heavy ladder lock slip "
                 "(490 N ASSUMPTION on polyester): unknown on 0.7 mm UHMWPE, which the maker says suits buckles only "
                 "in limited use. Gate before booking",
        durability="UHMWPE creeps under constant load and is slick in a ladder lock; it twists; cuts need a hot knife",
        test="LL-D: 5 heavy ladder locks on the Dyneema webbing, 338 N proof (W-PULL) dry / wet / -20 C, slip < 5 mm; "
             "W-box pull to 338 N on a 0.7 mm specimen; fallback polyester",
        look="black only (Dyneema dyes poorly); thinner, slightly sheened straps on the outside of the bag",
        records=["dyneema_webbing_25mm_thin: g/m, break, ladder-lock slip (Extremtextil art. 72979)"],
        source="corrie_f W-web / A-2 / BL-031 rows / 18 g/m x (10.2 - 18) g/m; research 3.3")
    add(key="N7", item="j_straps + belt_padding", status="new", risk="medium",
        change="J-strap shells HS-J1 and belt wing / lumbar shells: 330D CORDURA -> ULTRAGrid 210D (the bag-body cloth)",
        base_delta_g=sh["delta_g"], cost_usd=sh["cost_usd"],
        strength="the strap and belt shells carry part of the strap and wing tension; ULTRAGrid's grab (1300 / 1100 N) "
                 "is above 330D's (1000 / 800 N), but both are record ESTIMATEs / ASSUMPTIONs, so a seam pull decides",
        durability="Taber 1100 vs 330D 800 (records): level or better; UHMWPE grid yarns need tighter SPI and bartacks",
        test="SH-1 strap-to-yoke and wing-root seam pulls on ULTRAGrid (1.5 x the HS-1 strap load), plus the owner "
             "swatch already gated for the bag body (A_fab); fallback 330D",
        look="grid lines visible on straps and belt; matches the bag body (one cloth language)",
        records=[], source="build_geometry HS-J1 + ledger belt shell rows x (1 - 132/180); records",
        split={k: round(v, 1) for k, v in sh["split"].items()})
    add(key="G-3", item="door_zip", status="BL-037 option", risk="low",
        change="door chain #10 -> #8 coil (sliders unchanged)", base_delta_g=z8["delta_g"],
        cost_usd=z8["length_m"] * (rec("coil_zipper_8").cost_usd["value"] - rec("coil_zipper_10").cost_usd["value"]),
        strength="door zip unloaded (SF 78 on #10, about 61 on #8; weight_push G-3)",
        durability="#8 under gloved hands and grit; leaders use #10 on the main zip",
        test="PT-7 door zip proof on #8 + slider_8 record", look="slightly narrower zip line",
        records=["slider_8 (#8 slider mass and pull)"], source="weight_push.door_zip8()")
    for key, item, what, req in (("M1", "fp", "FP-L/R hip-reach pockets", "not frozen, not a DESIGN requirement; the "
                                  "E-5 pole quiver (R-20) moves from FP-R's pleat to the gusset so pole carry stays in base"),
                                 ("M2", "imp4", "IMP-4 door kill-kit pocket", "not frozen, not a DESIGN requirement"),
                                 ("M3", "imp6", "IMP-6 phone pocket (clips to the J-strap)", "not frozen, not a DESIGN requirement"),
                                 ("M4", "imp2", "IMP-2 hydration sleeve (hangs on 2 loops above IM3)",
                                  "DESIGN requirement R-19: met by a shipped add-on (SG sells it separately)"),
                                 ("M5", "imp5", "IMP-5L hipbelt pocket (removable, as KUIU)",
                                  "DESIGN requirement (hipbelt pockets): met by a shipped add-on")):
        n = 4 if key == "M1" else 2
        md = modular(item, n)
        add(key=key, item=item, status="modular (owner)", risk="low",
            change=f"{what}: sewn -> clip-on module shipped in the box ({n} loops on the pack, {n} toggle tabs on the module)",
            base_delta_g=md["base_delta_g"], as_hunted_delta_g=md["as_hunted_delta_g"], cost_usd=md["cost_usd"],
            strength="no load path", durability="a toggle can be lost; spare toggle in the box",
            test="MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first",
            look="cleaner base silhouette without the pocket; visible empty loops", records=[],
            source=f"roll-up item '{item}' + {n} x loop (poly_webbing_25mm x {LOOP_M} m) / tab (pom_toggle + "
                   f"{TAB_M} m webbing, ASSUMPTION TAB-L)", owner_rule=req)
    add(key="O-cams", item="im_straps + us_cradle", status="BL-037 owner option", risk="medium",
        change="IM1-IM3 and US1/US2 aluminium cams -> heavy 25 mm ladder locks", base_delta_g=cams["delta_g"],
        cost_usd=-cams["n"] * cam_usd,
        strength="IM / US hardware margin moves from the cam (1100 N, 1.82 / 1.53) to the ladder-lock slip (490 N "
                 "ASSUMPTION): 490 / 720 = 0.68 on the US rows, BELOW 1.0. Fails the gate unless a rated lock is "
                 "found; listed for completeness only",
        durability="-", test="MT-1..3 with ladder locks", look="none", records=[],
        source="weight_push.cams_to_ladders()", owner_rule="changes 'aluminium cams' (DECISIONS)")
    add(key="O-slider", item="door_zip", status="BL-037 owner option", risk="low",
        change="D2 door with one slider instead of two", base_delta_g=-WP.SLIDER_CORD_G,
        cost_usd=-rec("slider_10").cost_usd["value"], strength="no load path", durability="-",
        test="owner decision", look="none", records=[], source="weight_push ASSUMPTION SLIDER-CORD",
        owner_rule="door opens from one side only (no top peek)")
    return L


# =====================================================================================================================
# 3. strength gate: bag load points (mfg_corrie_f_rev3 load_points), before / after per lever
# =====================================================================================================================
@functools.lru_cache(maxsize=None)
def load_points() -> tuple:
    import mfg_corrie_f_rev3 as M
    with contextlib.chdir(ROOT):
        return tuple(M.load_points(M.build_ctx()))


AFFECTS = {   # lever -> (load-point regex, effect); effect "unchanged" or a function(row) -> (sf, hardware margin)
    "N3": (r"^US", "unchanged"),
    "N6": (r"^W", "pending"),
    "O-cams": (r"^(IM\d end loop|IM cam|US cam|US\d sewn)", "ladder"),
}


def strength_table() -> dict:
    lp = load_points()
    base = [r for r in lp if r["sf"]]
    out = {"min_sf": min(r["sf"] for r in base), "min_point": min(base, key=lambda r: r["sf"])["point"],
           "n_points": len(lp), "levers": {}}
    ll = float(rec("ladder_lock_25mm_heavy").require("slip_load_n"))
    for key, (rx, eff) in AFFECTS.items():
        hit = [r for r in base if re.search(rx, r["point"])]
        rows_ = []
        for r in hit:
            after_hw = r["hardware_margin"]
            if eff == "ladder":
                after_hw = round(ll / r["load_n"], 2)
            rows_.append({"point": r["point"], "load_n": r["load_n"], "sf": r["sf"], "hw_before": r["hardware_margin"],
                          "hw_after": after_hw if eff != "pending" else None, "effect": eff})
        uniq = {(x["point"], x["sf"], x["hw_before"], x["hw_after"]): x for x in rows_}
        worst = min((x["hw_after"] for x in uniq.values() if x["hw_after"] is not None), default=None)
        out["levers"][key] = {"rows": list(uniq.values()),
                              "verdict": ("FAIL" if worst is not None and worst < 1.0 else
                                          "PENDING test" if eff == "pending" else "PASS")}
    return out


# =====================================================================================================================
# 4. options and the rubric
# =====================================================================================================================
OPTIONS = {
    "A": {"name": "Same look, lighter hidden materials",
          "keys": ["N1", "N2", "N3", "N4", "N5"],
          "idea": "change only what the hunter does not see or that matches the house colours: body-face mesh, "
                  "backstops, sleeves, frame-side collar"},
    "B": {"name": "Modular: A + lighter base, pockets as shipped add-ons",
          "keys": ["N1", "N2", "N3", "N4", "N5", "M1", "M2", "M3"],
          "idea": "A, plus the three unfrozen, non-required pockets become clip-on modules in the box (SG / Exo / "
                  "KUIU practice); base drops, as hunted rises"},
    "C": {"name": "Aggressive: B + Dyneema wraps, ULTRAGrid straps / belt, #8 door, required pockets modular",
          "keys": ["N1", "N2", "N3", "N4", "N5", "M1", "M2", "M3", "N6", "N7", "G-3", "M4", "M5", "O-slider"],
          "idea": "every lever that keeps the strength gate on paper; O-cams is left out because it fails the gate"},
}


def option_table() -> dict:
    lv = {x["key"]: x for x in levers()}
    st = strength_table()
    A_base, A_hunt, P_base = total("A"), total("A", "as_hunted"), total("P")
    tgt = _R().TARGET_G
    out = {}
    for k, o in OPTIONS.items():
        sel = [lv[i] for i in o["keys"]]
        db = round(sum(x["base_delta_g"] for x in sel), 1)
        dh = round(sum(x["as_hunted_delta_g"] for x in sel), 1)
        new_only = round(sum(x["base_delta_g"] for x in sel if x["status"] == "new"), 1)
        mod = round(sum(x["base_delta_g"] for x in sel if x["status"].startswith("modular")), 1)
        gates = {i: st["levers"][i]["verdict"] for i in o["keys"] if i in st["levers"]}
        pend = [i for i, v in gates.items() if v.startswith("PENDING")]
        strong = ("FAIL" if "FAIL" in gates.values() else
                  f"PASS on paper; {', '.join(pend)} pending its slip test" if pend else
                  "PASS on paper (each lever gated by its test)")
        lk: dict = {}
        for x in sel:
            if x["look"] not in ("none", "none visible", "none (hidden)", "none (inside the cradle)"):
                lk.setdefault(x["look"], []).append(x["key"])
        looks = [f"{'/'.join(v)}: {t}" for t, v in lk.items()]
        out[k] = {**o, "base_delta_g": db, "as_hunted_delta_g": dh, "material_delta_g": round(db - mod, 1),
                  "modular_delta_g": mod, "new_material_g": new_only,
                  "modular_as_hunted_g": round(sum(x["as_hunted_delta_g"] for x in sel
                                                   if x["status"].startswith("modular")), 1),
                  "after_tests_base_g": round(A_base + db, 1), "after_tests_as_hunted_g": round(A_hunt + dh, 1),
                  "proven_now_base_g": round(P_base + mod, 1),
                  "gap_to_target_g": round(A_base + db - tgt, 1),
                  "cost_usd": round(sum(x["cost_usd"] for x in sel), 2),
                  "risk_max": max((x["risk"] for x in sel), key=["low", "medium", "high"].index),
                  "strong": strong, "looks": looks,
                  "tests": sorted({x["test"].split(" ")[0].rstrip(":") for x in sel})}
    return out


RECOMMENDED = "A"


# =====================================================================================================================
# 5. Pareto with the best lever per item
# =====================================================================================================================
NO_LEVER = {
    "spreader": "structural, owner decision Sandwich v2 at FPF 1.25 / fatigue 1.09 (R-3); structural-fea-engineer",
    "shell_panels": "already ULTRAGrid / ULTRA 200X / HyperD 300 in after tests; the only lighter Challenge cloth "
                    "(ULTRA 100X, 122 g/m2) is a louder PET laminate only 8 % lighter (research 3.1); DCF breaks quiet",
    "belt_loadpath": "rev C fixes C-1..3 (7075 plate) (R-6); structural",
    "yoke": "rev C fix C-7 (R-6)",
    "lifters_sternum": "already cut to length (BL-031) and side-release (H-2); Al ladder locks 5.8-9.2 g gain <= 1 g, unrated",
    "belt_closure": "50 mm buckle and 2:1 already re-booked (C8, BL-006 b); heavy lock legs are the HB-7 slip parts",
    "bag_hooks": "rated 38 mm hooks (2200 N) and EN 12275 carabiners: no lighter rated part found (research 3.4)",
    "guys": "small parts at the 1.36 minimum (B-25 bridle tab): not touched",
    "attach_soft": "load spreaders on rated rows (B-17 1.93, hinge 2.31)",
    "im_straps": "25 mm already (A_imus); the 38 mm eyes are captive in the print (R-1); aluminium cams owner-fixed "
                 "(O-cams fails the gate: ladder-lock slip 490 N < 720 N)",
    "thread_labels": "thread is an ASSUMPTION 3 % line; weigh prototype 1 first",
    "belt_padseat": "pad backer is a rev C fix (C-4); cord tie already in A_f",
    "carry": "owner-frozen bow carry and DESIGN rifle carry",
    "small_carry": "IMP-8 owner-frozen (bow), E-5 DESIGN R-20",
    "belt_trims": "small; camo shards already HyperD 300 (G-2)",
    "frame_hw": "frame track",
}


def pareto(n: int = 15) -> list:
    a, p = items("A"), items("P")
    lv = levers()
    out = []
    for k, g in sorted(a.items(), key=lambda t: -t[1]):
        if k in ("frame",) or k in SCOPE_FRAME - {"spreader"} or g <= 0.05:
            continue
        verdicts = strength_table()["levers"]
        mine = [x for x in lv if k in x["item"].split(" + ") and verdicts.get(x["key"], {}).get("verdict") != "FAIL"]

        def on_item(x):
            return x.get("split", {}).get(k, x["base_delta_g"])
        best = min(mine, key=on_item) if mine else None
        out.append({"item": k, "label": LABEL.get(k, k), "after_tests_g": g, "proven_now_g": p.get(k, 0.0),
                    "best": best["key"] if best else None,
                    "best_change": best["change"] if best else NO_LEVER.get(k, "-"),
                    "best_status": best["status"] if best else "-",
                    "best_delta_g": round(on_item(best), 1) if best else 0.0,
                    "all_levers": [x["key"] for x in mine]})
        if len(out) == n:
            break
    return out


# =====================================================================================================================
# 6. screenshots
# =====================================================================================================================
def plot_waterfall(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    opts = option_table()
    P, A = total("P"), total("A")
    tgt = _R().TARGET_G
    lv = {x["key"]: x for x in levers()}
    bars = [("proven now\n(today)", P, None, "#4f6b4a")]
    bars.append(("gated tests\n(A steps)", A - P, P, "#b0793a"))
    bars.append(("after tests", A, None, "#4f6b4a"))
    prev, prev_keys = A, []
    cols = {"A": "#5b6f8f", "B": "#7a5b8f", "C": "#8f5b5b"}
    for k in ("A", "B", "C"):
        add_keys = [i for i in OPTIONS[k]["keys"] if i not in prev_keys]
        d = sum(lv[i]["base_delta_g"] for i in add_keys)
        bars.append((f"+ option {k}\nlevers", d, prev, cols[k]))
        prev = prev + d
        bars.append((f"option {k}", prev, None, cols[k]))
        prev_keys = OPTIONS[k]["keys"]
    fig, ax = plt.subplots(figsize=(9.6, 6.0), dpi=110)
    lo = 2800
    for i, (lab, v, start, c) in enumerate(bars):
        if start is None:
            ax.bar(i, v - lo, bottom=lo, color=c, width=0.7)
            ax.text(i, v + 12, f"{v:.0f} g\n{v / LB:.2f} lb", ha="center", va="bottom", fontsize=9)
        else:
            ax.bar(i, v, bottom=start, color=c, alpha=0.55, width=0.7)
            ax.text(i, max(start, start + v) + 12, f"{v:+.0f} g", ha="center", va="bottom", fontsize=9)
    ax.axhline(tgt, color="#333", ls="--", lw=1)
    ax.text(3.0, tgt + 8, f"target 6.6 lb ({tgt:.0f} g)", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(bars)))
    ax.set_xticklabels([b[0] for b in bars], fontsize=8.5)
    ax.set_ylim(lo, P + 160)
    ax.set_ylabel("base mass, belt M, crown kit M (g)")
    ax.set_title("BL-062 iteration 1, system weight (frame excluded from the levers)\n"
                 "as-hunted change vs after tests: "
                 + ", ".join(f"{k} {opts[k]['as_hunted_delta_g']:+.0f} g" for k in "ABC")
                 + " (B and C move pockets to add-ons)", fontsize=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_pareto(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pr = pareto()
    fig, ax = plt.subplots(figsize=(9.6, 8.4), dpi=110)
    y = range(len(pr))[::-1]
    for yi, r in zip(y, pr):
        g, d = r["after_tests_g"], r["best_delta_g"]
        ax.barh(yi, g + d, color="#4f6b4a")
        if d:
            ax.barh(yi, -d, left=g + d, color="#d9a441")
        ax.text(g + 4, yi, f"{g:.0f} g" + (f"  ({r['best']} {d:+.0f})" if d else "  (no lever)"), va="center", fontsize=8.5)
    ax.set_yticks(list(y))
    import textwrap
    ax.set_yticklabels([textwrap.fill(r["label"], 40) for r in pr], fontsize=8)
    ax.set_xlabel("after-tests base mass (g); gold = best lighter alternative that keeps the strength gate")
    ax.set_title("Top 15 non-frame mass items (belt M) and the best lever on each", fontsize=10.5)
    ax.set_xlim(0, max(r["after_tests_g"] for r in pr) * 1.45)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


# =====================================================================================================================
# 7. report
# =====================================================================================================================
ASSUMPTIONS = [
    ("MESH-230", "a 3 mm, 230 g/m2 spacer mesh exists at the listed weight and wears acceptably on the back and straps "
     "(secondary listing; no record)", "materials record + MESH-1 / MESH-2"),
    ("MESH-320", "the 3 mm inelastic mesh is 320 g/m2 (category listing) not 390 (page title)", "weigh a 1 m swatch"),
    ("TI-TG", "a 25 mm Ti tri-glide weighs 4 g (secondary) and holds a slipped cam like the stainless part", "weigh 5 + US-BS on Ti"),
    ("TI-TG-COST", "USD 12 each (price not found)", "quote"),
    ("TAB-L", "a clip-on pocket's toggle tab is 25 mm webbing x 60 mm + one POM toggle", "pattern-maker draft"),
    ("FX", f"USD {USD_PER_EUR} per EUR", "-"),
    ("MESH-ROLL", "the 320 g/m2 mesh roll is 1.6 m wide (not on the listing)", "supplier"),
]


def _lb(g):
    return f"{g / LB:.2f} lb"


def _oz(g):
    return f"{g / OZ:+.1f} oz"


def compute() -> dict:
    a, p = items("A"), items("P")
    return {"date": "2026-11-24", "ticket": "BL-062", "code": OWN_CODE, "size": SIZE,
            "totals": {"proven_now_base_g": total("P"), "after_tests_base_g": total("A"),
                       "after_tests_as_hunted_g": total("A", "as_hunted"),
                       "frame_proven_now_g": frame_g("P"), "frame_after_tests_g": frame_g("A"),
                       "non_frame_after_tests_g": round(total("A") - frame_g("A"), 1),
                       "target_g": round(_R().TARGET_G, 1)},
            "items_after_tests": a, "items_proven_now": p, "pareto": pareto(), "levers": levers(),
            "strength": strength_table(), "options": option_table(), "recommended": RECOMMENDED,
            "assumptions": ASSUMPTIONS}


def _j(o):
    if isinstance(o, float):
        return round(o, 2)
    if isinstance(o, dict):
        return {k: _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    return o


def report(res: dict, shots: list) -> str:
    t, O, lv = res["totals"], res["options"], {x["key"]: x for x in res["levers"]}
    st = res["strength"]
    L = []
    w = L.append
    w("# Iteration 1, system weight: options (BL-062)\n")
    w(f"Owner: pack-designer. Date: {res['date']}. Code: `{OWN_CODE}` (tests `tests/test_iter1_weight.py`); numbers: "
      "`iter1_weight.json`. Research: `docs/research/weight_iter1.md`. Base configuration, belt M, crown kit M, as the "
      "roll-up (`analysis/weight_rollup_v2.md`). **Generated: re-run the code rather than quoting this file after any "
      "change.** Proposals only: no released pattern, ledger config or roll-up step is changed.\n")
    w("Scope: everything except the frame body and its pins and hardware (the structural track is working the frame). "
      "The spreader is listed but not touched (structural part, owner decision).\n")
    w("## 0. Answer\n")
    w(f"- Today: proven now **{t['proven_now_base_g']:.1f} g ({_lb(t['proven_now_base_g'])})**; after the gated tests "
      f"**{t['after_tests_base_g']:.1f} g ({_lb(t['after_tests_base_g'])})**. Of that, the frame is "
      f"{t['frame_after_tests_g']:.1f} g and everything in this ticket's scope is **{t['non_frame_after_tests_g']:.1f} g**.")
    w(f"- In scope we are already level with the leaders (research section 2): back panel + spreader + belt + harness "
      f"after tests {a_sus(res):.0f} g against KUIU ICON 6's belt + harness + hip pouches at about 1052 g (inference). The bag side is lighter than "
      "SG / Exo bags. The 6.6 lb gap is the frame body, so these options can only shave it.")
    for k in ("A", "B", "C"):
        o = O[k]
        w(f"- **Option {k}, {o['name']}:** base **{o['base_delta_g']:+.1f} g ({_oz(o['base_delta_g'])})** -> after "
          f"tests {o['after_tests_base_g']:.1f} g ({_lb(o['after_tests_base_g'])}); as hunted "
          f"{o['as_hunted_delta_g']:+.1f} g; cost {o['cost_usd']:+.2f} USD a pack; worst risk {o['risk_max']}; strong: "
          f"{o['strong']}. Still {o['gap_to_target_g']:.0f} g over 6.6 lb.")
    w(f"- **Recommendation: option {res['recommended']}.** It is the only package whose grams are real (not a "
      "reporting move), it changes nothing the hunter sees except a better-matched collar colour, and every lever has "
      "a known fallback. Take B's pocket moves only if the owner wants the base headline; they cost grams as hunted.")
    w("- Proven now does not move for any material lever: each is gated by a test with today's part as the fallback "
      f"(BL-014 rule). The modular moves are an owner decision with no test; adopted, they move proven now as well "
      f"(B: {O['B']['proven_now_base_g']:.1f} g, C: {O['C']['proven_now_base_g']:.1f} g).")
    w("")
    w("## 1. Pareto: top 15 non-frame items (after tests, base, belt M)\n")
    w("| # | item | after tests g | proven now g | best lighter alternative (keeps the strength gate) | g |")
    w("|---:|---|---:|---:|---|---:|")
    for i, r in enumerate(res["pareto"], 1):
        bt = f"{r['best']}: {r['best_change']}" if r["best"] else f"none: {r['best_change']}"
        w(f"| {i} | {r['label']} | {r['after_tests_g']:.1f} | {r['proven_now_g']:.1f} | {bt} | "
          f"{r['best_delta_g']:+.1f} |")
    w("")
    w("Items come from the roll-up rows by a fixed rule list (`RULES`); every non-frame row lands in exactly one item "
      "(tested). Proven-now masses differ where a gated step (A) already changes the item: wings, hood, 38 -> 25 mm "
      "IM/US, fabric swaps, BL-037 picks.\n")
    w("## 2. Levers\n")
    w("| key | status | change | base g | as hunted g | cost USD | risk | strength | durability | test that retires "
      "the risk | look | records needed |")
    w("|---|---|---|---:|---:|---:|---|---|---|---|---|---|")
    for x in res["levers"]:
        w(f"| {x['key']} | {x['status']} | {x['change']} | {x['base_delta_g']:+.1f} | {x['as_hunted_delta_g']:+.1f} | "
          f"{x['cost_usd']:+.2f} | {x['risk']} | {x['strength']} | {x['durability']} | {x['test']} | {x['look']} | "
          f"{'; '.join(x['records']) or '-'} |")
    w("")
    w("Status: **new** = not in any earlier ticket; **BL-037 option / owner option** = listed in `weight_push.md`, not "
      "picked, repeated here only so the packages are complete (none of BL-037's 119 g of picks is re-proposed); "
      "**modular** = a sewn feature becomes a clip-on module shipped in the box (owner decision).\n")
    w("## 3. Strength gate (bag load points, `mfg_corrie_f_rev3.load_points`)\n")
    w(f"Baseline: {st['n_points']} load points, min SF **{st['min_sf']}** at {st['min_point']} (rubric baseline 1.36). "
      "No lever touches the B-25 bridle, the hinge eye, the IM3 tongue or the B-17 tab. Rows a lever touches:\n")
    w("| lever | load point | factored N | SF (sewn) | hardware margin before | after | verdict |")
    w("|---|---|---:|---:|---:|---:|---|")
    for k, v in st["levers"].items():
        for r in v["rows"]:
            w(f"| {k} | {r['point']} | {r['load_n']:.0f} | {r['sf']} | {r['hw_before']} | "
              f"{r['hw_after'] if r['hw_after'] is not None else 'test'} | {v['verdict']} |")
    w("")
    w("- N3: the backstop is not a credited part of any row; the cam governs (1.53) before and after.")
    w("- N6: the box-X and the webbing (x52 on 225 N) pass; the ladder-lock slip on 0.7 mm UHMWPE is unknown, so the "
      "verdict is PENDING LL-D with polyester as the fallback.")
    w("- O-cams fails (US rows 490 / 720 N = 0.68 on the ASSUMPTION slip): kept out of every option.")
    w("- Hipbelt and harness structure (plates, webbing, lock legs) is untouched by every option. N7 changes the strap "
      "and wing shell cloth, gated by SH-1 seam pulls; HA-LS-1 frame rows are out of scope and unchanged.\n")
    w("## 4. Options scored on the rubric\n")
    w("| | A | B | C |")
    w("|---|---|---|---|")
    w("| levers | " + " | ".join(", ".join(O[k]["keys"]) for k in "ABC") + " |")
    w("| **1 strong (gate)** | " + " | ".join(O[k]["strong"] for k in "ABC") + " |")
    w("| **2 lighter, base g** | " + " | ".join(f"{O[k]['base_delta_g']:+.1f} ({_oz(O[k]['base_delta_g'])})" for k in "ABC") + " |")
    w("| of which materials / modular | " + " | ".join(f"{O[k]['material_delta_g']:+.1f} / {O[k]['modular_delta_g']:+.1f}" for k in "ABC") + " |")
    w("| after tests, base | " + " | ".join(f"{O[k]['after_tests_base_g']:.1f} ({_lb(O[k]['after_tests_base_g'])})" for k in "ABC") + " |")
    w("| as hunted change | " + " | ".join(f"{O[k]['as_hunted_delta_g']:+.1f}" for k in "ABC") + " |")
    w("| gap to 6.6 lb | " + " | ".join(f"{O[k]['gap_to_target_g']:.0f}" for k in "ABC") + " |")
    w("| cost per pack (USD) | " + " | ".join(f"{O[k]['cost_usd']:+.2f}" for k in "ABC") + " |")
    w("| worst durability risk | " + " | ".join(O[k]["risk_max"] for k in "ABC") + " |")
    w("| **3 looks** (visible changes) | " + " | ".join("; ".join(O[k]["looks"]) or "none" for k in "ABC") + " |")
    w("| physical tests | " + " | ".join(", ".join(O[k]["tests"]) for k in "ABC") + " |")
    w("")
    w("Looks is listed, not scored: the rubric scores it on renders with a design-reviewer pass, and none of A's "
      "changes is visible on a render. B's empty loops and C's black Dyneema wraps and grid-line straps need A/B "
      "renders before the owner picks.\n")
    w(f"**Recommendation: option {res['recommended']}** ({O['A']['base_delta_g']:+.1f} g base, all real mass, "
      f"{O['A']['cost_usd']:+.2f} USD). Reasons: (1) it passes the strength gate with no load point touched except N3's "
      "uncredited backstop; (2) its grams survive the as-hunted view, while B's and C's pocket moves add "
      f"{O['B']['modular_as_hunted_g']:+.1f} / {O['C']['modular_as_hunted_g']:+.1f} g as hunted (loops and toggles) "
      "for the base they take off; (3) no visible change except a collar that can now match the house colour. N6 (Dyneema "
      "wraps) and N7 (ULTRAGrid straps / belt) are worth testing in the same lot. If LL-D and SH-1 pass, they add "
      f"{lv['N6']['base_delta_g'] + lv['N7']['base_delta_g']:+.1f} g with no feature loss.\n")
    w("## 5. Honest reading against the target\n")
    w(f"Even option C leaves {O['C']['gap_to_target_g']:.0f} g over 6.6 lb after every test passes. The frame body "
      f"({t['frame_after_tests_g']:.0f} g after tests, against KUIU's 388 g frame) is the lever, as BL-037 found. "
      "Outside the frame there is no architecture lever left that keeps the owner-frozen features: meat straps, "
      "under-straps, bow carry, the fly pocket and the quiet fabrics are where the remaining non-frame mass sits, and "
      "the leaders carry the same functions in their frame weights.\n")
    w("## 6. Assumptions that govern\n")
    for k, txt, test in res["assumptions"]:
        w(f"- ASSUMPTION {k}: {txt}. Settled by: {test}.")
    w("")
    w("## 7. Screenshots\n")
    for s in shots:
        w(f"- `{s}`")
    w("")
    return "\n".join(L)


def a_sus(res: dict) -> float:
    a = res["items_after_tests"]
    return sum(v for k, v in a.items() if k in ("back_panel", "spreader", "belt_padseat", "belt_loadpath", "imp5",
                                                 "belt_closure", "belt_trims", "belt_padding", "imp6", "yoke",
                                                 "j_straps", "lifters_sternum"))


def write() -> dict:
    res = compute()
    shots = [plot_waterfall(SCREENS / f"{SHOT_PREFIX}1.png"), plot_pareto(SCREENS / f"{SHOT_PREFIX}2.png")]
    rel = [str(s.relative_to(ROOT)) for s in shots]
    res["screenshots"] = rel
    RESULT.write_text(json.dumps(_j(res), indent=1))
    DOC.write_text(report(res, rel))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="print the answer, write nothing")
    a = ap.parse_args(argv)
    res = compute() if a.check else write()
    print(json.dumps(_j({"totals": res["totals"], "options": {k: {kk: v[kk] for kk in (
        "base_delta_g", "as_hunted_delta_g", "after_tests_base_g", "cost_usd", "strong")} for k, v in res["options"].items()},
        "min_sf": res["strength"]["min_sf"]}), indent=1))


if __name__ == "__main__":
    main()
