"""BL-038: the physical test kit (manufacturing-engineer, 2026-11-13).

    python designs/pack_5200/physical_test_kit.py             # update the register, TEST_PLAN section 5, write the kit
    python designs/pack_5200/physical_test_kit.py --check     # build everything in memory and print the checks only

Turns ``designs/pack_5200/tests_physical/TEST_PLAN.md`` into a kit the owner can follow:

1. ``test_register.csv``: adds the rows the plan's newer gates lack (BL-037 HS-1, CS-1, AB-1, SL-1, ST-1, BU-1; the
   T9 rev 3 items as T9-R3a..d; US-BS, PORT-1, GT-1, FRAY-1; MT-1c, the meat-strap cinch readout that frame release
   R1 waits on; B-28 slip as covered by LL-H) and patches the rows the BL-021/024/027/031/034/037 results moved (CA-1
   release level, IM3-EC 28 mm cheek, T9 crown straps 25 mm per kit, record prices). Idempotent.
2. TEST_PLAN.md section 5 (value ranking of the gram tests) is regenerated: CA-1 at 0.40 is worth 9.9 g (F-1, an
   option), not 60 g (BL-037).
3. ``outputs/release/test_kit/``: order of work (R1 frame release, then the bag, then the BL-037 gates, grouped by
   rig), shopping list (CSV + md, prices from material records or cited, long-lead flags), one beginner guide per
   test group, the results template the owner fills in, rig sketches, a PDF of the whole kit and phone screenshots
   ``outputs/screens/20261113_BL038_<n>.png``.

The results template is read back by ``huntkit.manufacturing.test_results`` (verdict per test, ASSUMPTION status,
release status).

Units: N, kg, mm, g internally; lb / in / oz shown next to them. The crane scale reads kg: kg on scale = N / 9.81.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

TP = HERE / "tests_physical"
REGISTER = TP / "test_register.csv"
TEST_PLAN = TP / "TEST_PLAN.md"
OUT = ROOT / "outputs" / "release" / "test_kit"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261113_BL038"
DATE = "2026-11-13"
G = 9.81                    # N per kg on the crane scale
LB_PER_N = 0.224809
USD_PER_EUR = 1.09          # ASSUMPTION, the material records' own conversion (cam_25mm_al, triglide_25mm notes)
OWNER_HOUR_USD = 15.0       # ASSUMPTION used only to rank (TEST_PLAN section 5)
MAT = ROOT / "data" / "materials"
AN = HERE / "analysis"


# ============================================================================ sources read at run time
def record(rid: str) -> dict:
    hits = list(MAT.glob(f"*/{rid}.yaml"))
    if not hits:
        raise KeyError(f"no material record {rid}")
    return yaml.safe_load(hits[0].read_text())


def rec_price(rid: str) -> float:
    return float(record(rid)["cost_usd"]["value"])


def _json(name: str) -> dict:
    return json.loads((AN / name).read_text())


def release_levels() -> dict:
    """CA-1 levels from the adopted results: H1-G0.55-B1/2.5 body (BL-027) and the 28 mm IM3 cheek (BL-021)."""
    hb = _json("h1_buckling.json")["chosen"]
    ims = _json("im3_body_simloads.json")["eye"]["cands"]
    rec_ratio = float(record("pa12_cf_fdm_paht")["properties"]["fatigue_1e5_ratio"])
    body = float(hb["ca1_flip"])
    cheek = float(ims["14_8"]["ca1_flip_ratio"])          # 28 x 8 mm cheek (half width 14)
    # BL-039: the cheek at its DIR_SCATTER angle (computed pull + 10 deg aft, the rule BL-021 sized it to) flips at
    # 0.30 / 1.174 = 0.2556, just above the body's 0.2553; it enters the governing flip (release unchanged at 0.276)
    cheek_dir = rec_ratio / float(ims["14_8"]["sensitivity"]["fatigue_dir_plus_scatter"])
    cyc = rec_ratio / float(hb["fatigue_cinch_cycled"])
    gov = max(body, cheek, cheek_dir)
    up = lambda x: math.ceil(round(x, 6) * 1000) / 1000  # noqa: E731  (round a release level up to 0.001)
    return {"record_ratio": rec_ratio, "flip_body": round(body, 4), "flip_cheek": round(cheek, 4),
            "flip_cheek_dir": round(cheek_dir, 4),
            "flip_gov": round(gov, 4), "release": up(gov + 0.02), "flip_cycled": round(cyc, 4),
            "release_cycled": up(cyc + 0.02), "fatigue_static": round(float(hb["fatigue_min_sim"]), 3),
            "fatigue_cycled": round(float(hb["fatigue_cinch_cycled"]), 3), **swing_rule(up(gov + 0.02))}


def swing_rule(release: float) -> dict:
    """BL-039 (``ca1_mt1c_confirm``): the MT-1c swing (peak-to-peak / mean) each CA-1 level covers under the
    flip + 0.02 rule, worst bracket k; and the swing that still keeps margin 1.0 at the release level."""
    import ca1_mt1c_confirm as CC
    i, k = CC.inputs(), min(CC.K_BRACKET)
    pct = lambda x: round(100 * x, 1)  # noqa: E731
    return {"swing_ok_release_pct": pct(CC.p_at_flip(i, release - CC.CUSHION, k)),
            "swing_ok_040_pct": pct(CC.p_at_flip(i, 0.40 - CC.CUSHION, k)),
            "swing_margin1_release_pct": pct(CC.p_at_flip(i, release, k))}


IM3_EC_MARGIN = 1.15       # CA1_fatigue_rig.md 6a / BL-023: the eye coupons run at >= 1.15 x the 1.6 g demand
FAT_G = 1.6                # HA-LS-1 rev C walking peak (load_standard.md)


def im3_ec_load() -> dict:
    """BL-039: IM3-EC coupon load from the 28 mm cheek's governing sim demand (BL-021, im3_body_simloads.json:
    worst hook + IM3 strap combination at 1 g, 15fL), replacing BL-010's 15 in IM3 force (552.4 N, 27 mm cheek)."""
    e = _json("im3_body_simloads.json")["eye"]["cands"]["14_8"]["sensitivity"]
    f1 = float(e["governing_combo_1g_n"])
    peak = round(IM3_EC_MARGIN * FAT_G * f1)
    return {"combo_1g_n": round(f1, 1), "aft_deg": round(float(e["governing_combo_aft_deg"]), 1),
            "demand_n": round(FAT_G * f1, 1), "peak_n": peak, "min_n": round(0.1 * peak),
            "link_n": round(peak / 4.0), "proof_n": 2553}


def ca1_forces(ratio: float, uts=88.0, area=40.0, lever=4.0) -> dict:
    """CA1_fatigue_rig.md section 3: S = ratio x 0.8 x UTS at R 0.1, nominal 40 mm2 XY gauge, 4:1 lever."""
    f = ratio * 0.8 * uts * area
    return {"S_MPa": round(ratio * 0.8 * uts, 1), "F_max_N": round(f), "F_min_N": round(0.1 * f),
            "link_N": round(f / lever)}


def lid_mass_g() -> float:
    """The sewn lid's booked mass, from the mass ledger (BL-001 rule)."""
    from huntkit.mass import ledger
    for r in ledger.adopted_bag_rows("M"):
        if "crown_lid" in r["name"]:
            return round(float(r["g"]), 1)
    raise KeyError("crown lid row not in ledger.adopted_bag_rows")


def weight_push() -> dict:
    return {x["key"]: x for x in _json("weight_push_results.json")["levers"]}


def crown_cut_mm() -> dict:
    """B-28 cut and longest path per kit (BL-031), from concepts/corrie_f.py."""
    sys.path.insert(0, str(HERE / "concepts"))
    try:
        import corrie_f as CF
        out = {}
        for k in ("S", "M", "L"):
            d = CF.crown_kit_straps(k)
            out[k] = {"cut_mm": round(float(d["cut_mm"]), 1), "longest_mm": round(float(d["path_max_mm"]), 1),
                      "spare_mm": round(float(d["spare_mm"]), 1), "path_limit_mm": round(float(d["path_limit_mm"]), 1),
                      "sixday_mid_mm": round(float(d["paths_mm"]["sixday"]["mid_torso"]), 1),
                      "torso_in": tuple(d["torso_in"])}
        return out
    except Exception:                                    # pragma: no cover - fall back to corrie_f_body.md 16.2
        return {"S": {"cut_mm": 1068.1, "longest_mm": 928.1, "spare_mm": 40.0, "path_limit_mm": 968.1,
                      "sixday_mid_mm": 543.3, "torso_in": (15.0, 18.0)},
                "M": {"cut_mm": 1006.9, "longest_mm": 866.9, "spare_mm": 40.0, "path_limit_mm": 906.9,
                      "sixday_mid_mm": 495.7, "torso_in": (17.5, 20.5)},
                "L": {"cut_mm": 948.0, "longest_mm": 808.0, "spare_mm": 40.0, "path_limit_mm": 848.0,
                      "sixday_mid_mm": 438.8, "torso_in": (20.0, 23.0)}}


# ============================================================================ register: new rows and patches
COLS = ["id", "status", "tier", "title", "defined_in", "what_it_proves", "gates", "grams_at_stake_g", "safety_at_stake",
        "specimen", "kit", "steps", "pass_fail", "cost_usd", "cost_basis", "hours_hands_on", "hours_machine", "phase",
        "run_order", "first_weekend", "notes", "g_per_usd_eq"]

WP = "designs/pack_5200/analysis/weight_push.md"
CFB = "designs/pack_5200/analysis/corrie_f_body.md"
REL = "outputs/release/pack5200_corrie_f_rev3/manufacturing/release_tests.csv"


BP1_COUPON_MM = (70.0, 200.0)   # register BP-1 specimen: one 70 x 200 mm coupon per core thickness
BP1_CORE_BUY_M2 = 0.02          # the shopping-list ROHACELL line (smallest sensible cut of a sheet)


def bp1_cost() -> dict:
    """BL-039: BP-1 sample cost. The 3 mm coupon is an offcut of the strip layup (no cost); the 2 mm (BL-037 K-1)
    coupon is its own layup: the ROHACELL line plus two 200 g twill skins at the woven-ply record price (the
    record's $/m2 is for the cured ply, resin included)."""
    w, l = BP1_COUPON_MM
    core = BP1_CORE_BUY_M2 * rec_price("rohacell_71_igf")
    skins_m2 = 2 * w * l / 1e6
    skins = skins_m2 * rec_price("cfrp_t300_3k_woven_epoxy_ply")
    return {"usd": round(core + skins, 2), "core_usd": round(core, 2), "skins_usd": round(skins, 2),
            "skins_m2": skins_m2,
            "basis": f"BL-039: 2 mm coupon layup = rohacell_71_igf {BP1_CORE_BUY_M2} m2 x ${rec_price('rohacell_71_igf'):.0f} "
                     f"+ 2 skins {w:.0f} x {l:.0f} mm cfrp_t300_3k_woven_epoxy_ply x ${rec_price('cfrp_t300_3k_woven_epoxy_ply'):.0f}/m2 "
                     "(records); 3 mm coupon = offcut of the strip layup"}


def tg_ss_usd() -> float:
    """Stainless 25 mm tri-glide: EUR 3.10 incl. 19 % VAT (triglide_25mm record source line) x 1.09 USD/EUR."""
    return round(3.10 / 1.19 * USD_PER_EUR, 2)


def new_rows(lv: dict, lid_g: float, cut: dict) -> list[dict]:
    wpd = weight_push()
    g = lambda k: abs(float(wpd[k]["g"]))  # noqa: E731
    s_path = cut["S"]["path_limit_mm"]          # BL-039: cut - 2 x 50 mm grip = longest + spare
    rows = [
        dict(id="MT-1c", status="ACTIVE", tier="safety",
             title="meat-strap cinch readout: does the IM cinch cycle with the walking g (CINCH_STATIC)",
             defined_in="designs/pack_5200/analysis/h1_buckling.md (CINCH_STATIC); designs/pack_5200/analysis/h1_sleeve.md; docs/DECISIONS.md 2026-11-12 BL-024 / BL-027 rows (R1 waits on MT-1)",
             what_it_proves="the IM strap cinch is a static preload, so H1's fatigue is the static-cinch value",
             gates=f"frame release R1: body fatigue {lv['fatigue_static']} with the cinch static, {lv['fatigue_cycled']} if it cycles fully; the measured swing sets the CA-1 level R1 needs (BL-039, designs/pack_5200/analysis/ca1_mt1c_confirm.md)",
             grams_at_stake_g="0", safety_at_stake=f"H1 body fatigue {lv['fatigue_static']} vs {lv['fatigue_cycled']}",
             specimen="P2 frame + sewn bag, 30 kg sand meat on IM1-IM3 cinched by hand as in the field; kit B 100 kg S-type cell + HX711 inline in the IM2 strap's free end (two snap shackles), logging to an SD card",
             kit="B+C",
             steps="cinch IM1-IM3 by hand as in the field and lock the cams; log the IM2 strap tension at 80 Hz; stage 1 on the stand: run the T5 crank 600 cycles (10 min, 0.4 -> 1.6 g) with the meat in; stage 2 after T1-T4 pass: a 10 min loaded walk on rough ground; for each stage compute the mean tension and the mean peak-to-peak swing per cycle / step; send the log",
             pass_fail=f"record the larger peak-to-peak swing / mean of the two stages (%). R1 needs: swing <= {lv['swing_ok_release_pct']} %: CA-1 at {lv['release']}; swing <= {lv['swing_ok_040_pct']:.0f} %: CA-1 also passed at 0.40; above: CA-1 at {lv['release_cycled']} (BL-039 table, ca1_mt1c_confirm.md section 2; replaces BL-038's 10 % pass bound, which keeps margin >= 1.0 only up to {lv['swing_margin1_release_pct']} % and without the 0.02 cushion)",
             cost_usd="15", cost_basis="ASSUMPTION SD-card logger + power bank $15 (cell and HX711 from kit B)",
             hours_hands_on="2", hours_machine="0.2", phase="4", run_order="62", first_weekend="N",
             notes="BL-038: added. The register's MT-1 is the box-X proof; the R1 hold named 'MT-1' in DECISIONS is this cinch readout (h1_buckling.md). Stage 1 replaces the walk for R1 (no person under an unreleased frame); stage 2 confirms",
             g_per_usd_eq=""),
        dict(id="US-BS", status="ACTIVE", tier="safety",
             title="US backstop: stainless tri-glide behind an open cam stops the cradle strap",
             defined_in=f"{REL}; data/materials/hardware/triglide_25mm.yaml (stainless alternative); docs/DECISIONS.md 2026-11-13 orchestrator row",
             what_it_proves="ASSUMPTION US-BS: a slipped US cam cannot lengthen the cradle; the stainless tri-glide holds the US proof",
             gates="US1/US2 backstop (bag release)", grams_at_stake_g="0",
             safety_at_stake="US proof 1080 N (S5-S7 720 N x 1.5)",
             specimen="3 x 25 mm poly webbing 600 mm, Al cam (the MT-3 cams, re-used) with the stainless 25 mm tri-glide threaded behind it as the op sequence",
             kit="A",
             steps="thread cam and stainless tri-glide as in the pack; paint-pen mark on the webbing at the tri-glide; hold the cam lever open with a zip tie so it cannot grip; pull slowly with the come-along to 110.1 kg (1080 N); hold 1 min; measure how far the mark moved",
             pass_fail="tri-glide stops the strap within 10 mm and holds 1080 N for 1 min, 3 of 3",
             cost_usd=f"{3 * tg_ss_usd():.2f}", cost_basis=f"triglide_25mm record stainless line EUR 3.10 incl. VAT -> USD {tg_ss_usd()} x 3; cams from MT-3",
             hours_hands_on="0.5", hours_machine="", phase="1", run_order="63", first_weekend="Y",
             notes="BL-038: added from release_tests.csv. Run after MT-3 on the same cams", g_per_usd_eq=""),
        dict(id="PORT-1", status="ACTIVE", tier="safety",
             title="B-27 guy port mock-up: hose, 100 N lap pull, gloved lock use",
             defined_in=f"{CFB} 13.8, 13.9; {REL}",
             what_it_proves="ASSUMPTION PORT_FACING_W 50 mm / PORT_TURN 6 mm: the lapped port keeps water out and stays shut under a guy pull",
             gates="B-27 construction (bag release)", grams_at_stake_g="0", safety_at_stake="water into the bag; port opening under load",
             specimen="300 x 300 mm B-01 (ULTRA 200) panel with one B-27 lapped slit and its B-27f facing sewn as op sequence, 25 mm guy webbing through it",
             kit="A+E",
             steps="clamp the panel over a plastic tub, outside face up, a dry paper towel in the tub; hang 5 kg (49 N) on the guy so it pulls at 45 deg through the port; hose from 1 m above for 1 min; check the towel; then pull the guy straight through the lap to 10.2 kg (100 N) on the crane scale and measure the lap gap; with winter gloves thread and adjust the guy ladder lock at the port 5 times",
             pass_fail="towel dry; lap gap <= 2 mm at 100 N (ASSUMPTION 'stays closed' = 2 mm); 5 of 5 gloved adjustments",
             cost_usd="0", cost_basis="bag fabric offcuts + kit A", hours_hands_on="1.5", hours_machine="", phase="1",
             run_order="64", first_weekend="Y", notes="BL-038: added from release_tests.csv / corrie_f_body 13.9", g_per_usd_eq=""),
        dict(id="GT-1", status="ACTIVE", tier="safety",
             title="capstan pull: guy webbing over the packed bag's corner (MU_WEB_FAB)",
             defined_in=f"{CFB} 13.2, 13.8, 13.9; {REL}",
             what_it_proves="ASSUMPTION MU_WEB_FAB 0.30 (band 0.20-0.40), webbing on the PU face fabric",
             gates="guy friction share in the CG runs (bag batch release)", grams_at_stake_g="0",
             safety_at_stake="friction share of the guy hold only", specimen="first sewn bag, packed full; a 25 mm guy webbing",
             kit="D+E",
             steps="lay the guy webbing over the packed bag's top corner; hang 5 kg (49 N) on one end; measure the wrap angle with phyphox (tilt of the free leg minus tilt of the hanging leg, in degrees); pull the other end slowly with the spring scale until the weight starts to rise; read the peak T; 3 pulls; mu = ln(T / 49) / (angle x pi / 180)",
             pass_fail="mu inside 0.20-0.40 on each pull (record the value); outside: tell the pack-designer (CG runs re-checked)",
             cost_usd="0", cost_basis="kit D spring scale", hours_hands_on="0.5", hours_machine="", phase="5",
             run_order="65", first_weekend="N", notes="BL-038: added. Needs the first sewn bag", g_per_usd_eq=""),
        dict(id="FRAY-1", status="ACTIVE", tier="safety",
             title="wash-swatch fray of the un-bound SSa2 body seam (rev 3 fabrics, as cut)",
             defined_in=f"{REL} (RD-17); designs/pack_5200/mfg_corrie_f_rev3.py ASSUMPTION NO-BIND; docs/DECISIONS.md 2026-11-13 orchestrator call (3)",
             what_it_proves="ASSUMPTION NO-BIND: SSa2 (12 mm allowance, turned, 2nd row at 6 mm) does not fray past the 2nd row without binding",
             gates="un-bound body seams (bag release)", grams_at_stake_g="0",
             safety_at_stake="seam durability (no seam capacity counts the binding)",
             specimen="6 SSa2 swatches 200 mm long, rotary-cut edges NOT seared (as the prototype cutting plan cuts them): ULTRA 200|330D, 330D|330D, 500D|330D, 630D printable|330D, HyperD 300|330D, 100D|330D; 301, 8 SPI, tex 90, Nm 110 round point",
             kit="E",
             steps="sew each swatch as op 3.07 (SSa2); wash with the WP-1 swatches: 3 normal cold cycles in a mesh bag with a towel, line dry; look at every edge with the loupe",
             pass_fail="no allowance frayed past the 2nd row on any swatch; a fail on one pairing: hot-knife that cut edge or bind that seam (20 mm grosgrain)",
             cost_usd="0", cost_basis="bag fabric offcuts", hours_hands_on="1.0", hours_machine="4.5", phase="1",
             run_order="66", first_weekend="Y", notes="BL-038: added; same wash load as WP-1 (WP-1 is the B.2 seared seam)", g_per_usd_eq=""),
        dict(id="B-28 slip", status="COVERED->LL-H", tier="safety",
             title="B-28 crown strap on its heavy ladder lock", defined_in=f"{CFB} 15.6, 16.2; {REL}",
             what_it_proves="covered by LL-H: same 25 mm heavy lock, 366 N proof above the 288 N envelope (BL-031 dropped the 20 mm gate)",
             gates="B-28 crown straps", grams_at_stake_g="0", safety_at_stake="slip margin 1.70 (record basis)",
             specimen="LL-H specimens (2 of the 5 threaded as a B-28 front lock on a hinge-band tab)", kit="A",
             steps="run LL-H", pass_fail="LL-H pass", cost_usd="0", cost_basis="LL-H", hours_hands_on="0",
             hours_machine="", phase="1", run_order="67", first_weekend="Y", notes="BL-038: alias row so the release list finds it", g_per_usd_eq=""),
        dict(id="T9-R3a", status="ACTIVE", tier="safety",
             title="T9 rev 3 (a): port guys hold the S-kit top, meat CG at 15 in",
             defined_in=f"{CFB} 14.5, 14.10; docs/DECISIONS.md 2026-11-13 BL-033 row (179.3 mm)",
             what_it_proves="ASSUMPTION LID-SIM and INT-1: the sewn lid and the inside port guys give the sim's CG",
             gates="CORRIE F rev 3 top as drawn (bag batch release)", grams_at_stake_g="0",
             safety_at_stake="15 in meat CG 179.3 mm sim vs rev C 190 mm",
             specimen="P2 frame, S crown kit (15 in), sewn rev 3 bag, port guys fitted, lid on with 1 kg inside",
             kit="C",
             steps="top packed full above the guys; 30 kg sand meat on IM1-IM3, fill to 68 kg; hang from the haul loop and plumb a line; hang from a pin through the hip pivot and plumb a second line; the CG is where the lines cross; measure its distance aft of the stay plane",
             pass_fail="meat CG <= 190 mm aft (record against 179.3 mm)", cost_usd="0", cost_basis="kit C",
             hours_hands_on="1.5", hours_machine="", phase="4", run_order="68", first_weekend="N",
             notes="BL-038: split out of T9 (was T9 rev 3 item a); sim value updated to BL-033's 179.3 mm", g_per_usd_eq=""),
        dict(id="T9-R3b", status="ACTIVE", tier="safety",
             title="T9 rev 3 (b): crown strap cinch force and retention (CROWN_PRE_N, MU_LID)",
             defined_in=f"{CFB} 14.9, 15.6", what_it_proves="ASSUMPTION CROWN_PRE_N 80 N hand cinch and MU_LID 0.20",
             gates="CORRIE F rev 3 crown straps (bag batch release)", grams_at_stake_g="0",
             safety_at_stake="T1 / T2 CG depends on the cinch",
             specimen="sewn rev 3 bag on P2, lid on, full top; 0-15 kg spring scale", kit="C+D",
             steps="hook the spring scale on each B-28 tail; pull to 8.2 kg (80 N) and lock; walk 30 min loaded (only after T1-T4 pass); read the tension again (pull the tail until it just moves); set the pack down hard from 0.5 m on its base; read again; check the lid is still seated",
             pass_fail="after the walk >= 40 N, or the lid still seated on the full top (report both values)",
             cost_usd="0", cost_basis="kit D spring scale", hours_hands_on="1.0", hours_machine="", phase="5",
             run_order="69", first_weekend="N", notes="BL-038: split out of T9 (item b)", g_per_usd_eq=""),
        dict(id="T9-R3c", status="ACTIVE", tier="safety",
             title="T9 rev 3 (c): crown strap free length (ROLL-PATH, TORSO-LIN)",
             defined_in=f"{CFB} 15.6, 16.2, 16.5",
             what_it_proves="ASSUMPTION ROLL-PATH: the cloth-pass rolled top gives the sewn bag's crown strap path",
             gates="B-28 cut per crown kit (bag batch release)", grams_at_stake_g="0",
             safety_at_stake=f"S kit cut {cut['S']['cut_mm']} mm against a {cut['S']['longest_mm']} mm sim path: 50 mm grip tail each end plus {cut['S']['spare_mm']:g} mm spare (BL-039, CROWN-SPARE)",
             specimen=f"sewn rev 3 bag on P2 with the S kit at its short end ({cut['S']['torso_in'][0]:g} in) packed full, collar standing; then the L kit at {0.5 * sum(cut['L']['torso_in']):g} in, 6-day load", kit="C",
             steps="cinch both crown straps; measure the strap path from the bar tab to the ladder lock along the strap with a tape (both straps); repeat at the L kit 6-day setting",
             pass_fail=f"S kit full: path <= {s_path} mm (cut {cut['S']['cut_mm']} - 2 x 50 mm grip tail; sim {cut['S']['longest_mm']} mm); L kit 6-day: record against the sim's {cut['L']['sixday_mid_mm']} mm",
             cost_usd="0", cost_basis="kit", hours_hands_on="0.7", hours_machine="", phase="4", run_order="70",
             first_weekend="N",
             notes=f"BL-038: split out of T9 (item c). BL-030's 1138 mm single 20 mm cut is replaced by BL-031's per-kit 25 mm cuts. BL-039 added {cut['S']['spare_mm']:g} mm spare to every kit (BL-031 had none: the S sim path {cut['S']['longest_mm']} mm equalled its limit); a path above {s_path} mm still means a longer S cut",
             g_per_usd_eq=""),
        dict(id="T9-R3d", status="ACTIVE", tier="function",
             title="T9 rev 3 (d): sewn lid mass and seat (LID_SLIDER5_G, LID_THREAD, LID-SEAT)",
             defined_in=f"{CFB} 14.9, 14.10; huntkit/mass/ledger.py adopted_bag_rows (crown lid)",
             what_it_proves="the sewn lid weighs what the ledger books and seats on the roll as drawn",
             gates="B-29 lid mass booking (bag batch release)", grams_at_stake_g="0", safety_at_stake="none",
             specimen="first sewn B-29 lid; 0.01 g pocket scale (lid fits on a 200 g scale)", kit="D",
             steps="weigh the lid alone 3 times; photograph it seated on the packed 6-day bag and the full bag, from the rear 3/4 and the side",
             pass_fail=f"lid {lid_g} g +/- 5 g (ledger); lid edge on the hinge-band seam, camo caps over the blades",
             cost_usd="0", cost_basis="kit D", hours_hands_on="0.3", hours_machine="", phase="5", run_order="71",
             first_weekend="N", notes="BL-038: split out of T9 (item d); mass from the ledger at run time", g_per_usd_eq=""),
        dict(id="SL-1", status="ACTIVE", tier="grams", title="weigh the cord-pull door sliders and the printed label; gloved door cycles",
             defined_in=f"{WP} 2 (G-1, X-1), 7 SLIDER-CORD, LABEL",
             what_it_proves="ASSUMPTION SLIDER-CORD 15.0 g and LABEL 1.0 g; the cord pull works gloved",
             gates=f"BL-037 G-1 (-{g('G-1')} g) and X-1 (-{g('X-1')} g)", grams_at_stake_g=f"{g('G-1') + g('X-1'):.1f}",
             safety_at_stake="none", specimen="5 YKK #10 coil slider bodies with a 3 mm cord pull each; the printed label; a 400 mm #10 coil door sample on 330D tabs with 2 sliders",
             kit="D",
             steps="fit the cord pull to each slider; weigh each on the 0.01 g scale; weigh the label; with winter gloves open and close the door sample 20 times",
             pass_fail="each slider with pull <= 15.0 g; label <= 1.0 g; 20 of 20 without a snag",
             cost_usd=f"{5 * rec_price('slider_10') + 0.4 * rec_price('coil_zipper_10') + rec_price('dyneema_cord_3mm') + 5:.2f}",
             cost_basis="slider_10 x 5, coil_zipper_10 0.4 m, dyneema_cord_3mm 1 m (records) + ASSUMPTION printed label $5",
             hours_hands_on="1.0", hours_machine="", phase="1", run_order="72", first_weekend="Y",
             notes="BL-038: added (BL-037). Sliders are LONG LEAD (Rockywoods sold out 2026-11-13)", g_per_usd_eq=""),
        dict(id="CS-1", status="ACTIVE", tier="grams", title="XLPE L200 compression set, 50 % for 22 h at 40 C",
             defined_in=f"{WP} 2 (B-1, H-1), 7 XLPE-SET; data/materials/foams/xlpe_foam_l200.yaml (12 %), eva_foam_45c.yaml (15 %)",
             what_it_proves="ASSUMPTION XLPE-SET: L200 keeps its thickness after sweat and heat",
             gates=f"BL-037 B-1 (-{g('B-1')} g) and H-1 (-{g('H-1')} g)", grams_at_stake_g=f"{g('B-1') + g('H-1'):.1f}",
             safety_at_stake="comfort", specimen="3 discs 30 mm diameter of XLPE L200 6 mm (belt) and 3 of 5 mm (straps)",
             kit="B+D",
             steps="measure each disc's thickness t0 with the caliper (light touch, 3 points, mean); put the discs between the two jig plates with 3.0 mm spacers (6 mm discs) or 2.5 mm spacers (5 mm discs); tighten until the plates sit on the spacers; 22 h in the 40 C box; take out, unclamp, let them recover 24 h on a flat table; measure tf the same way; set % = (t0 - tf) / t0 x 100",
             pass_fail="every disc set <= 15 % (the EVA 45C record value)",
             cost_usd=f"{0.25 * rec_price('xlpe_foam_l200') + 10:.2f}",
             cost_basis="xlpe_foam_l200 record x 0.25 m2 + ASSUMPTION jig $10 (2 Al plates, spacers, 4 M6 bolts)",
             hours_hands_on="1.0", hours_machine="46", phase="2", run_order="73", first_weekend="N",
             notes="BL-038: added (BL-037). Shares the CA-4 40 C box (ASTM D3575 style)", g_per_usd_eq=""),
        dict(id="AB-1", status="ACTIVE", tier="grams", title="HyperD 300 vs 630D printable: Martindale 8000 rev, brush drag, print swatch",
             defined_in=f"{WP} 2 (G-2), 7 HYPERD-ABRASION; data/materials/textiles/polyester_300d_printable.yaml",
             what_it_proves="ASSUMPTION HYPERD-ABRASION: HyperD 300 wears at least as well as the 630D on the blades; the camo prints well on it",
             gates=f"BL-037 G-2 (-{g('G-2')} g)", grams_at_stake_g=f"{g('G-2'):.1f}", safety_at_stake="durability of the camo accents",
             specimen="1 yd HyperD 300 printable with the owner's camo (custom print); a 630D printable offcut; 2 lab samples 300 x 300 mm",
             kit="D (lab)",
             steps="order the HyperD print (an 8 x 8 in swatch first if offered); send one 300 x 300 mm sample of each fabric to a textile lab for Martindale abrasion (ASTM D4966 or ISO 12947-2) to 8000 rev, end point a hole or 2 broken yarns; at home tape a 50 x 300 mm strip of each to a board and drag a stiff nylon brush loaded with 2 kg along 200 mm, 50 passes; look with the loupe; judge the printed camo in daylight at 1 m and 10 m",
             pass_fail="HyperD: no hole at 8000 rev; brush strip no worse than the 630D strip; owner OK on the print in writing",
             cost_usd=f"{(2 * 66 + 97) * USD_PER_EUR + rec_price('polyester_300d_printable'):.2f}",
             cost_basis="Measurlabs Martindale EUR 66 / sample x 2 + EUR 97 order fee (cited, ISO 12947-2) x 1.09 + polyester_300d_printable 1 yd (record)",
             hours_hands_on="1.5", hours_machine="", phase="2", run_order="74", first_weekend="N",
             notes="BL-038: added (BL-037). LONG LEAD: lab turnaround about 4 weeks after receipt; custom print lead time unknown", g_per_usd_eq=""),
        dict(id="HS-1", status="ACTIVE", tier="grams", title="shoulder pressure: XLPE L200 vs EVA 45C J-strap load foam",
             defined_in=f"{WP} 2 (H-1), 4, 7 XLPE-SHOULDER",
             what_it_proves="ASSUMPTION XLPE-SHOULDER: XLPE L200 5 mm under the comfort layer does not bottom at 68 kg",
             gates=f"BL-037 H-1 (-{g('H-1')} g)", grams_at_stake_g=f"{g('H-1'):.1f}", safety_at_stake="comfort",
             specimen="J-strap pair: left with XLPE L200 5 mm load foam, right with EVA 45C 5 mm (comfort layer, shell, mesh as drawn); 2 FSRs per strap",
             kit="D",
             steps="tape one FSR under each strap at the top of the shoulder and one 60 mm down the front; calibrate each FSR on the puck first; 30 kg in the pack, walk 20 min, read the peaks at 5, 10, 15 and 20 min; repeat at 68 kg; 3 testers; ask each tester if either strap felt a hard spot (bottoming); swap sides for the third tester",
             pass_fail="XLPE peak / EVA peak <= 1.10 at 30 kg and 68 kg on all 3 testers; no bottoming felt; CS-1 passed",
             cost_usd=f"{0.1 * rec_price('xlpe_foam_l200') + 0.1 * rec_price('eva_foam_45c'):.2f}",
             cost_basis="xlpe_foam_l200 + eva_foam_45c records x 0.1 m2 each (one extra strap of each)",
             hours_hands_on="3", hours_machine="", phase="5", run_order="75", first_weekend="N",
             notes="BL-038: added (BL-037). Walking with 68 kg waits for T1-T4 (frame released)", g_per_usd_eq=""),
        dict(id="ST-1", status="ACTIVE", tier="grams", title="gloved one-hand sternum clip-on, 25 mm side-release",
             defined_in=f"{WP} 2 (H-2)", what_it_proves="the side-release buckle works one-handed in winter gloves",
             gates=f"BL-037 H-2 (-{g('H-2')} g)", grams_at_stake_g=f"{g('H-2'):.1f}", safety_at_stake="none (not on an HA-LS-1 load path)",
             specimen="sternum strap with the 25 mm side-release buckle sewn on the harness", kit="E",
             steps="wear the loaded pack (15 kg); winter gloves on; clip the sternum buckle with one hand, 10 tries; time each",
             pass_fail="10 of 10 one-handed (record the times)",
             cost_usd=f"{2 * rec_price('buckle_side_release_25mm'):.2f}", cost_basis="buckle_side_release_25mm record x 2",
             hours_hands_on="0.3", hours_machine="", phase="5", run_order="76", first_weekend="N",
             notes="BL-038: added (BL-037); R-06 fit trial session", g_per_usd_eq=""),
        dict(id="BU-1", status="ACTIVE", tier="grams", title="50 mm crown bushings: kit change and pawl travel, gloved",
             defined_in=f"{WP} 2 (F-3), 7 BUSHING-LD; designs/pack_5200/analysis/crown_diet (e)",
             what_it_proves="ASSUMPTION BUSHING-LD: bushings at L/D 2.8 slide without binding",
             gates=f"BL-037 F-3 (-{g('F-3')} g)", grams_at_stake_g=f"{g('F-3'):.1f}",
             safety_at_stake="crown slip (ring crush SF 1.67 by analysis)",
             specimen="2 UHMWPE crown bushings cut 50 mm from the 70 mm stock, on P2", kit="C",
             steps="fit the 50 mm bushings; winter gloves on; change the crown kit S -> M -> L -> S and run the torso pawl through every stop, 20 cycles; note any stick",
             pass_fail="20 of 20 without binding (slides by hand, no tool); the pawl engages every stop",
             cost_usd="10", cost_basis="ASSUMPTION spare UHMWPE tube length $10 (uhmwpe_sheet record has no tube price)",
             hours_hands_on="1", hours_machine="", phase="4", run_order="77", first_weekend="N",
             notes="BL-038: added (BL-037); CR-1 session", g_per_usd_eq=""),
    ]
    return rows


def patches(lv: dict, lid_g: float) -> dict:
    """Changes to existing register rows: the later tickets moved their numbers."""
    wpd = weight_push()
    ec = im3_ec_load()
    f1 = abs(float(wpd["F-1"]["g"]))
    rel = lv["release"]
    return {
        "CA-1": dict(
            gates=f"H1 print release R1 (governing flip {lv['flip_gov']} + 0.02 = {rel}); 0.40 only feeds option F-1 (BL-037)",
            safety_at_stake=f"flip points: H1-G0.55-B1/2.5 body {lv['flip_body']} (fatigue {lv['fatigue_static']}, cinch static), IM3 28 mm cheek {lv['flip_cheek']} ({lv['flip_cheek_dir']} at DIR_SCATTER +10 deg); governing {lv['flip_gov']}; release needs ratio >= {rel}; if MT-1c shows the cinch cycling: flip {lv['flip_cycled']}, release {lv['release_cycled']}",
            steps=f"CA1_fatigue_rig.md 6: 3 XY + 2 Z static, then 3 XY at the release level {rel} (= governing flip {lv['flip_gov']} + 0.02) to 1e5, 2 Z at {rel}, then 3 XY at 0.40",
            pass_fail=f"3/3 run-outs to 1e5 at {rel}, stiffness loss <= 10 %, no crack; static XY >= 79.2 MPa, Z >= 42.3 MPa. R1 uses {rel} only if MT-1c's swing is <= {lv['swing_ok_release_pct']} %; up to {lv['swing_ok_040_pct']:.0f} % it needs the 0.40 pass; above, 3/3 at {lv['release_cycled']} (BL-039)",
            grams_at_stake_g=f"{f1}",
            notes=f"BL-038: release level from h1_buckling.json (BL-027 body flip) and im3_body_simloads.json (28 mm cheek), replacing the 0.310 placeholder (CA1_fatigue_rig.md 1 asked for this). Grams: BL-037 F-1 (-{f1} g, an option that also needs a buckling re-run), not -50..-70 g. Machine: 8 runs x 27.8 h. CT-B1 merged here"),
        "IM3-EC": dict(title=f"IM3 eye cycle coupons, 3 x 1e5 at >= 1.15 x {ec['demand_n']:.0f} N",
                       defined_in="designs/pack_5200/tests_physical/CA1_fatigue_rig.md §6a; designs/pack_5200/analysis/im3_body_simloads.md (28 mm cheek, governing hook + strap); designs/pack_5200/analysis/loadpath_verification.md §4.1, §8",
                       what_it_proves=f"the 28 mm IM3 cheek survives 1e5 walking cycles with a 15 % load margin on the BL-021 sim demand (1.6 x {ec['combo_1g_n']:.1f} N hook + strap, 15fL, {ec['aft_deg']:.0f} deg aft = {ec['demand_n']:.0f} N)",
                       safety_at_stake="IM3 eye fatigue 1.218 at 0.30 (28 mm cheek, BL-021; 1.174 at DIR_SCATTER)",
                       specimen="3 eye coupons: 120 mm stay segment round z 520 with the IM3 eye and the 28 mm cheek (BL-021), cut from the H1 STL, printed with the CA-1 bars",
                       steps=f"sewn T3 tongue + IM3 carabiner through the eye, led {ec['aft_deg']:.0f} deg aft of the stay axis, coupon clamped by the stay ends; lever rig at R 0.1: {ec['min_n']} -> {ec['peak_n']} N, 1 Hz, to 1e5; loupe check every 25,000; then pull to {ec['proof_n']} N on the pull bench",
                       pass_fail=f"3/3 run-outs to 1e5 at {ec['peak_n']} N, no crack at 10x; residual pull {ec['proof_n']} N with no crack",
                       notes=f"BL-038: cheek 27 -> 28 mm (BL-021 adopted). BL-039: load {ec['peak_n']} N from the BL-021 sim demand (was 1017 N = 1.15 x 1.6 x 552.4 N, BL-010's 15 in IM3 force, below today's demand)"),
        "T9": dict(title="loaded CG (+ 15 in, 30 kg meat check); CORRIE F rev 3 items in rows T9-R3a..d (BL-038 split)",
                   specimen="P2 frame + bag (rev C CG at 15 / 19 / 23 in); the rev 3 items are rows T9-R3a..d",
                   steps="68 kg fill and meat on IM1-IM3 at 15/19/23 in; hang from haul loop, then from a hip pin, plumb both lines; add 30 kg on IM1-IM3 at 15 in; then rows T9-R3a (port guys, S kit CG), T9-R3c (crown strap path) in the same session; T9-R3b (cinch after a walk) and T9-R3d (lid) after T1-T4",
                   pass_fail="bag CG <= 205 mm at z <= 590; meat <= 190; tall <= 185; rev 3 items: rows T9-R3a..d",
                   notes="corrie 11.4 plumb check and MOD-5 merged here; BL-038 split the rev 3 items (BL-030) into T9-R3a..d and moved the crown straps to BL-031's 25 mm per-kit cuts"),
        "LL-H": dict(gates="guy ladder locks on B-22 (BL-004 REC, A_att); W1-W3 float clamp locks; B-28 crown strap locks (the B-28 slip gate, BL-031)",
                     specimen="5 heavy ladder locks + tri-glides on 25 mm webbing (2 threaded as a B-28 front lock on a hinge-band tab)"),
        "MT-3": dict(cost_usd=f"{5 * rec_price('cam_25mm_al'):.2f}", cost_basis="cam_25mm_al record 25.50 x 5 (re-used for US-BS)",
                     notes="BL-038: price from the record (was ASSUMPTION $4). Cams LONG LEAD (both resellers out of stock 2026-11-13)"),
        "HB-7": dict(cost_usd=f"{5 * rec_price('ladder_lock_25mm_heavy') + 5 * rec_price('d_ring_25mm_aluminium'):.2f}",
                     cost_basis="ladder_lock_25mm_heavy 2.10 x 5 + d_ring_25mm_aluminium 1.85 x 5 (records)"),
        "MT-2": dict(notes="BL-038: in the kit the MT-2 carabiners are a separate lot of 5 from PT-1"),
        "HB-1": dict(gates="belt B fit (OD-HB1); BL-006 c2 (with HB-D2); front-strap pad (+42.9 g if it fails); BL-037 B-1 / B-3 (XLPE L200 wing load and lumbar foams, 4 mm wing comfort)",
                     pass_fail="every sensor <= 48.6 kPa (absolute pass, orchestrator call 2026-11-10); bony landmarks watched at 30 kPa; front-strap sensor <= 48.6 kPa without the pad; BL-037 build: wing worst <= 56.5 kPa, lumbar <= 48.6 kPa, hold not worse than belt B on the same testers",
                     grams_at_stake_g=f"{42.9 + abs(float(wpd['B-1']['g'])) + abs(float(wpd['B-3']['g'])):.1f}"),
        "HB-D2": dict(gates="BL-006 c2 (A_c2); BL-037 B-2 (0.5 mm stiffener)",
                      specimen="belt B wings side by side: 0.5 mm and 0.75 mm HDPE stiffener (and the 1.0 mm reference)",
                      pass_fail="the thinnest stiffener that passes the HB-D2 roll-over criterion is kept (0.5 mm keeps BL-037 B-2)",
                      grams_at_stake_g=f"{9.8 + abs(float(wpd['B-2']['g'])):.1f}"),
        "BP-1": dict(gates="BL-005 sandwich strip (A_back); BL-037 K-1 (2 mm ROHACELL 71 core)",
                     specimen="70 x 200 mm offcuts of the strip layup: 3 mm and 2 mm ROHACELL 71 core (2 mm: sand a 3 mm sheet or special order)",
                     grams_at_stake_g=f"{44.6 + abs(float(wpd['K-1']['g'])):.1f}",
                     cost_usd=f"{bp1_cost()['usd']:.2f}", cost_basis=bp1_cost()["basis"]),
        # BL-039: the crown hood B-19 left with BL-004 (owner 2026-11-12, DECISIONS); its guys' crown ends are toggle
        # loops proven by TL-1. Retired in the register's own format.
        "PT-4": dict(status="RETIRED", tier="-", what_it_proves="", gates="", grams_at_stake_g="", safety_at_stake="",
                     specimen="", kit="", steps="", pass_fail="", cost_usd="", cost_basis="", hours_hands_on="",
                     hours_machine="", phase="-", run_order="-", first_weekend="N", g_per_usd_eq="",
                     notes="BL-039: retired. Crown hood B-19 removed (BL-004; owner kept it removed 2026-11-12, "
                           "docs/DECISIONS.md); the guy crown ends are toggle loops, proven by TL-1"),
    }


def update_register(lv: dict, lid_g: float, cut: dict, write: bool = True) -> list[dict]:
    with open(REGISTER, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by = {r["id"]: r for r in rows}
    for rid, p in patches(lv, lid_g).items():
        by[rid].update(p)
    for nr in new_rows(lv, lid_g, cut):
        assert set(nr) == set(COLS), set(COLS) ^ set(nr)
        if nr["id"] in by:
            by[nr["id"]].update(nr)
        else:
            rows.append(nr)
            by[nr["id"]] = nr
    for r in rows:                                    # re-score every gram test on the same rule
        if r["tier"] == "grams" and r["status"].startswith("ACTIVE"):
            r["g_per_usd_eq"] = f"{score(float(r['grams_at_stake_g'] or 0), float(r['cost_usd'] or 0), float(r['hours_hands_on'] or 0)):.3f}"
    if write:
        with open(REGISTER, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\r\n")   # the register's own line ending
            w.writeheader()
            w.writerows(rows)
    return rows


def score(grams: float, usd: float, hours: float) -> float:
    return grams / (usd + hours * OWNER_HOUR_USD) if (usd + hours) > 0 else float("inf")


# ============================================================================ value ranking (TEST_PLAN section 5)
def ranking(reg: dict) -> list[dict]:
    """Every gram test, scored grams / (samples $ + hands-on h x $15). Grams = the bookings the test unlocks or keeps."""
    wpd = weight_push()
    gw = lambda k: abs(float(wpd[k]["g"]))  # noqa: E731
    items = [  # id, grams, what, booked?
        ("WP-3", 5.4, "protects A-2 (already in B.2)", True),
        ("WP-1", 36.4, "protects B-1 (already in B.2)", True),
        ("WP-5", 12.8, "protects B-10 (already in B.2)", True),
        ("WP-2", 6.2, "C-6 lash tabs", True),
        ("HB-5", 25.0, "package C plate; also a safety gate", True),
        ("RF-1", 7.2, "C-8 rails", True),
        ("FS-O5", 7.0, "C-5 floor (alternate set); needs PT-3 on ULTRA too", True),
        ("CA-1", gw("F-1"), "option F-1 only: CA-1 at 0.40 AND MT-1c static AND a buckling re-run (BL-037); not booked. "
                            "CA-1 stays the top safety gate", False),
        ("FT-S2", 101.6, "owner's wing removal (BL-023)", True),
        ("BP-1", 44.6 + gw("K-1"), "BL-005 strip with BP-2 (44.6) + BL-037 K-1 2 mm core", True),
        ("HB-D3", 12.6, "BL-006 f1 + f2", True),
        ("HB-D1", 22.4, "BL-006 b", True),
        ("HB-D2", 9.8 + gw("B-2"), "BL-006 c2 + BL-037 B-2 0.5 mm", True),
        ("HB-1", 42.9 + gw("B-1") + gw("B-3"), "front-strap pad (42.9) + BL-037 B-1, B-3 (with CS-1)", True),
        ("CS-1", gw("B-1") + gw("H-1"), "BL-037 B-1 + H-1 (with HB-1 / HS-1)", True),
        ("HS-1", gw("H-1"), "BL-037 H-1", True),
        ("AB-1", gw("G-2"), "BL-037 G-2 (Martindale lab fee dominates)", True),
        ("SL-1", gw("G-1") + gw("X-1"), "BL-037 G-1 + X-1", True),
        ("ST-1", gw("H-2"), "BL-037 H-2", True),
        ("BU-1", gw("F-3"), "BL-037 F-3", True),
    ]
    out = []
    for tid, g, what, booked in items:
        r = reg[tid]
        usd, h = float(r["cost_usd"] or 0), float(r["hours_hands_on"] or 0)
        out.append({"test": tid, "grams": round(g, 1), "usd": usd, "hours": h, "score": round(score(g, usd, h), 2),
                    "booked": booked, "note": what})
    out.sort(key=lambda d: -d["score"])
    for i, d in enumerate(out, 1):
        d["rank"] = i
    return out


def ranking_md(rk: list[dict]) -> str:
    L = ["## 5. Value ranking of the gram tests", "",
         "Re-scored by BL-038 (`designs/pack_5200/physical_test_kit.py`, 2026-11-13). Score = grams / (sample cost $ + hands-on "
         "hours x $15). ASSUMPTION: $15 per owner hour, used only to rank. Grams are the bookings each test unlocks or "
         "protects; where two tests gate one saving (BP-1 + BP-2, HB-1 + CS-1, HS-1 + CS-1) each carries the whole "
         "saving and both must pass.", "",
         "**CA-1 is no longer a 60 g test.** BL-037 (`analysis/weight_push.md` §3, option F-1) found that on H1 as "
         "adopted a 0.40 ratio releases at most 9.9 g net, and only with MT-1c showing the cinch static and a "
         "converged buckling re-size (Euler 0.965 as run). It is not booked. CA-1 keeps its place as the first "
         "safety gate of frame release R1.", "",
         "| rank | test | grams | samples $ | hands-on h | g per $-eq | booked | note |",
         "|---:|---|---:|---:|---:|---:|---|---|"]
    for d in rk:
        L.append(f"| {d['rank']} | {d['test']} | {d['grams']:.1f} | {d['usd']:.2f} | {d['hours']:g} | {d['score']:.2f} | "
                 f"{'yes' if d['booked'] else 'no (option)'} | {d['note']} |")
    L += ["", "BL-003 (a) (116.9 g) and BL-004 (103.0 g) are unlocked by the weekend-1 safety pulls (MT-1..3, PT-1, PT-2, "
          "LL-H) and TL-1; they are not ranked because those tests run anyway. Order of work: "
          "`outputs/release/test_kit/README.md` (BL-038).", "",
          "Grams are from `weight_pass_corrie.md` (package rows A-2, B-1, B-10, C-5, C-6, C-8), `weight_c_structural.md` "
          "(C-1+C-2+C-3 = 25.0 g), the BL-023 rows (`weight_rollup_v2.md`: FT-S2 101.6, BP 44.6, HB-D1 22.4, HB-D2 9.8, "
          "HB-D3 12.6, front-strap pad 42.9) and `analysis/weight_push_results.json` (BL-037 levers, read at run time). "
          "Sample cost and hours are the register's.", ""]
    return "\n".join(L)


def update_test_plan(rk: list[dict], lv: dict, write: bool = True) -> str:
    t = TEST_PLAN.read_text(encoding="utf-8")
    a, b = t.index("## 5. Value ranking"), t.index("## 6. Duplicates")
    t = t[:a] + ranking_md(rk) + "\n" + t[b:]
    if write:
        TEST_PLAN.write_text(t, encoding="utf-8")
    return t


# ============================================================================ releases, groups, order of work
RELEASES = [  # key, label, what it releases
    ("R1", "Frame release R1", "H1 print files released for load-carrying prints (DECISIONS BL-027: MT-1 cinch, CA-1, T1/T2 gauges; CA1 doc: with IM3-EC and CA-5)"),
    ("BAG-CUT", "Bag release, step 1: cut and sew", "every sewn load point and hardware item proven before the bag fabric is cut"),
    ("BAG-BATCH", "Bag release, step 2: batch", "first-article bag checks before more bags are cut (release_tests.csv)"),
    ("BL037", "BL-037 weight gates", "the -119.1 g A_bl037 picks (weight_push.md)"),
    ("CARRY", "Field release and the rest", "first loaded carry, meat haul, belt and comfort tests"),
]
REL_ORDER = {k: i for i, (k, _, _) in enumerate(RELEASES)}

TEST_RELEASE = {
    # R1
    "CA-1": "R1", "IM3-EC": "R1", "CA-5": "R1", "MT-1": "R1", "MT-1c": "R1", "IM3-EP": "R1", "W-PULL": "R1",
    "T9": "R1", "T1": "R1", "T2": "R1",
    # bag
    "MT-2": "BAG-CUT", "MT-3": "BAG-CUT", "US-BS": "BAG-CUT", "PT-1": "BAG-CUT", "PT-2": "BAG-CUT", "PT-3": "BAG-CUT",
    "PT-5": "BAG-CUT", "PT-6": "BAG-CUT", "LL-H": "BAG-CUT", "B-28 slip": "BAG-CUT", "PORT-1": "BAG-CUT",
    "FRAY-1": "BAG-CUT", "WP-1": "BAG-CUT", "TL-1": "BAG-CUT", "FS-O5": "BAG-CUT",
    "T9-R3a": "BAG-BATCH", "T9-R3b": "BAG-BATCH", "T9-R3c": "BAG-BATCH", "T9-R3d": "BAG-BATCH", "GT-1": "BAG-BATCH",
    "PT-7": "BAG-BATCH", "WP-2": "BAG-BATCH", "WP-3": "BAG-BATCH", "WP-4": "BAG-BATCH", "WP-5": "BAG-BATCH",
    # BL-037
    "HS-1": "BL037", "CS-1": "BL037", "AB-1": "BL037", "SL-1": "BL037", "ST-1": "BL037", "BU-1": "BL037",
    "HB-1": "BL037", "HB-D2": "BL037", "BP-1": "BL037",
}
# tests that also serve a second release (shown in the order of work and the results sheet)
ALSO = {"MT-1": "BAG-CUT", "BP-1": "CARRY", "HB-1": "CARRY", "HB-D2": "CARRY", "T9": "BAG-BATCH"}

GROUPS = [
    dict(id="G1", title="Order the long-lead parts, print and condition the coupons", when="week 1, day 1",
         rig="3D printer (frame profile), oven, conditioning box (kit D)", kits="B (filament), D",
         tests=["CA-1", "IM3-EC", "CA-5", "CA-3", "CA-4", "HB-6", "T7"], print_only=True,
         intro="Start here, today. The frame coupons need 7 days in the conditioning box before the lever rig can test "
               "them, so they set the pace for frame release R1. Order the long-lead parts the same day."),
    dict(id="G2", title="Pull bench weekend: hooks, cams, bartacks, ladder locks", when="weekend 1 (week 1)",
         rig="kit A pull bench (come-along, 300 kg crane scale, 5 mm pin fixture, bar clamps)", kits="A, D (caliper, loupe, pocket scale), E",
         tests=["MT-1", "PT-1", "MT-2", "MT-3", "US-BS", "PT-2", "PT-3", "PT-5", "PT-6", "LL-H", "B-28 slip", "PORT-1",
                "TL-1", "FS-O5", "HB-7", "WP-3", "SL-1"],
         intro="One bench, one weekend. MT-1 goes first because frame release R1 needs it; the rest are every sewn "
               "load point on the bag. After this weekend you may cut the bag (if G3's wash also passes)."),
    dict(id="G3", title="Wash and look: seams without binding", when="weekend 1, evenings",
         rig="washing machine, mesh laundry bag, 10x loupe", kits="E, D (loupe)", tests=["FRAY-1", "WP-1"],
         intro="Both swatch sets go in the same wash. Three cold cycles, line dry, then look at every edge."),
    dict(id="G4", title="Lever rig: frame coupons (weeks 2-5)", when="build weekend 2, then runs day and night",
         rig="kit B lever fatigue rig (CA1_fatigue_rig.md), 40 C box, 3-point bend fixture", kits="B, D",
         tests=["CA-1", "IM3-EC", "CA-5", "HB-6", "CA-3", "CA-4", "CS-1", "BP-1", "HB-5", "T6", "T7", "CA-2"],
         intro="Build the rig once; every frame coupon runs on it. CA-1 at the release level comes first: frame "
               "release R1 cannot happen without it. The 40 C box also runs CS-1 (BL-037) beside CA-4."),
    dict(id="G5", title="Bench session 2: fabric, belt and back coupons", when="any weekend while the lever rig runs (weeks 2-4)",
         rig="kit A pull bench + kit D", kits="A, D",
         tests=["WP-2", "AB-1", "HB-4", "HB-T", "PS-1", "BP-2", "HB-2"],          # PT-4 retired (BL-039)
         intro="Sewn and laminated coupons that do not need the frame. Send the AB-1 lab samples on the first day: "
               "the lab takes about 4 weeks."),
    dict(id="G6", title="First-article frames on the stand (P1 then P2)", when="after G4's CA-1, IM3-EC and CA-5 pass (about week 5-6)",
         rig="kit C frame test stand (hip log, shoulder bar, sand bags, T5 crank) + kit A scale and come-along", kits="C, A, B (load cell), D",
         tests=["IM3-EP", "W-PULL", "T9", "T9-R3a", "T9-R3c", "BP-3", "RF-1", "T1", "T3", "T2", "MT-1c", "CR-1", "BU-1",
                "SP-1", "T4a", "T4b", "T4c", "T5", "T5f", "T2u"],
         intro="Frame release R1 completes here: IM3-EP on P1, then T9, T1, T2 and MT-1c on P2. Nobody carries the "
               "frame until T1 to T4 have passed. T2u destroys P1 and is always last."),
    dict(id="G7", title="Complete pack: fit, field and first-article bag checks", when="after T1-T4 pass",
         rig="the complete pack, sand bags, spring scale, FSR strips, phone (phyphox)", kits="D, E",
         tests=["T9-R3b", "T9-R3d", "GT-1", "PT-7", "WP-4", "WP-5", "HS-1", "ST-1", "HB-1", "HB-D2", "HB-3", "HB-D1",
                "HB-D3", "FT-S2", "MH-1", "MH-2", "MH-3", "R28-1"],
         intro="The bag's batch release (T9-R3b/d, GT-1, PT-7) comes first in this session, then the BL-037 comfort "
               "gates, then the field tests."),
]


def group_of(tid: str) -> str:
    """Main group (the session where the test is RUN; G1 only prints coupons)."""
    for gr in GROUPS:
        if tid in gr["tests"] and not gr.get("print_only"):
            return gr["id"]
    for gr in GROUPS:
        if tid in gr["tests"]:
            return gr["id"]
    return ""


def order_of_work(reg: dict) -> list[dict]:
    out, seq = [], 0
    for gr in GROUPS:
        tests = sorted(gr["tests"], key=lambda t: (REL_ORDER[TEST_RELEASE.get(t, "CARRY")], gr["tests"].index(t)))
        if gr["id"] in ("G6",):          # the stand follows load_standard.md 5.3 order; keep the listed order
            tests = gr["tests"]
        for t in tests:
            r = reg[t]
            seq += 1
            rel = TEST_RELEASE.get(t, "CARRY")
            out.append({"seq": seq, "group": gr["id"], "test": t, "stage": "print + condition" if gr.get("print_only") else "run",
                        "release": rel, "also": ALSO.get(t, ""), "tier": r["tier"], "title": r["title"],
                        "hands_on_h": 0.0 if gr.get("print_only") else float(r["hours_hands_on"] or 0),
                        "machine_h": 0.0 if gr.get("print_only") else float(r["hours_machine"] or 0),
                        "status": r["status"]})
    return out


# ============================================================================ loads shown in the guides
def N(n):
    return {"N": n, "kg": n / G, "lb": n * LB_PER_N}


def loads(lv: dict) -> dict:
    c = ca1_forces(lv["release"])
    c4 = ca1_forces(0.40)
    cc = ca1_forces(lv["release_cycled"])
    ec = im3_ec_load()
    lb = lambda x: x / LB_PER_N  # noqa: E731  lb -> N
    return {
        "MT-1": [("IM loops (5)", 908), ("US loops (5)", 1080)],
        "MT-2": [("G-hooks (5)", 645), ("carabiners (5)", 910)],
        "MT-3": [("first hold", 908), ("second hold", 1080)],
        "US-BS": [("US proof, cam held open", 1080)],
        "PT-1": [("proof, 60 s", 2553)], "PT-2": [("proof, 60 s", 2553)], "PT-3": [("proof, 60 s", 1530)],
        "PT-5": [("10 cycles to", 170)], "PT-6": [("proof, 60 s", 1410)],
        "LL-H": [("dead load, 1 h", 366)], "B-28 slip": [("covered by LL-H", 366)],
        "HB-7": [("hold 1 min, no slip", 426), ("slip must be above", 490)],
        "PORT-1": [("guy at 45 deg during the hose", 49.05), ("lap pull", 100)],
        "GT-1": [("hanging weight", 49.05)],
        "CA-1": [(f"XY bar peak at the release level {lv['release']}", c["F_max_N"]),
                 ("XY bar valley (R 0.1)", c["F_min_N"]), ("load cell reads (4:1 lever)", c["link_N"]),
                 ("XY bar peak at 0.40", c4["F_max_N"]),
                 (f"XY bar peak at {lv['release_cycled']} (only if MT-1c's swing is over {lv['swing_ok_040_pct']:.0f} %)", cc["F_max_N"])],
        "IM3-EC": [(f"eye cycle peak (1.15 x {ec['demand_n']:.0f} N)", ec["peak_n"]), ("after run-out, proof pull", ec["proof_n"])],
        "CA-5": [("static mean must reach", 4400), ("lowest static", 3666), ("cycle force", 1543)],
        "CA-4": [("dead load at the lever end (4:1)", 282)],
        "IM3-EP": [("eye pull", 2553)],
        "T9": [("fill", 68 * G), ("meat check", 30 * G)], "T9-R3a": [("fill incl. 30 kg meat", 68 * G)],
        "T9-R3b": [("cinch", 80), ("after the walk, at least", 40)],
        "T1": [("(a)", lb(150)), ("(b)", lb(300)), ("(c) hipbelt off", lb(225))],
        "T2": [("meat / tall load", lb(300))], "T3": [("side-hill 25 deg", lb(240))], "T2u": [("ultimate, 30 s", lb(450))],
        "T4a": [("pack load, 20 drops at 2.0 g", lb(150))], "T5": [("dead load", lb(60)), ("peak", lb(240))],
        "CR-1": [("crown hang", 136 * G)], "SP-1": [("bone-end proof", 400)],
        "MT-1c": [("meat on IM1-IM3", 30 * G), ("pack fill", 68 * G)],
        "HS-1": [("pack, run 1", 30 * G), ("pack, run 2", 68 * G)], "ST-1": [("pack", 15 * G)],
        "T5f": [("float meat", 56 * G)],
    }


def load_table(rows) -> list[str]:
    L = ["| load | N | lb | kg on the scale |", "|---|---:|---:|---:|"]
    for lab, n in rows:
        d = N(n)
        L.append(f"| {lab} | {d['N']:.0f} | {d['lb']:.0f} | {d['kg']:.1f} |")
    return L


# ============================================================================ results template
def measures(lv: dict, lid_g: float, cut: dict) -> dict:
    """test -> list of (sample, quantity, unit, check, limit, settles). Tests not listed get one Y/N row."""
    y = "Y/N"
    s_path = cut["S"]["path_limit_mm"]          # BL-039: cut - 2 x 50 mm grip = longest + spare
    ec = im3_ec_load()

    def per(n, q, unit, chk, lim, settles="", pre="#"):
        return [(f"{pre}{i}", q, unit, chk, lim, settles) for i in range(1, n + 1)]

    m = {
        "MT-1": per(5, "held 92.6 kg (908 N) 1 min, no broken stitch", y, "yes", "Y", "BOX25", "IM#")
        + per(5, "held 110.1 kg (1080 N) 1 min, no broken stitch", y, "yes", "Y", "BOX25", "US#"),
        "MT-2": per(5, "G-hook held 65.7 kg (645 N) 1 min, gate closes", y, "yes", "Y", "", "G#")
        + per(5, "carabiner held 92.8 kg (910 N) 1 min, gate closes", y, "yes", "Y", "", "C#"),
        "MT-3": per(5, "mark moved at 92.6 kg (908 N)", "mm", "max", "3", "CAM-SLIP", "a#")
        + per(5, "mark moved at 110.1 kg (1080 N)", "mm", "max", "3", "CAM-SLIP", "b#"),
        "US-BS": per(3, "strap stopped within", "mm", "max", "10", "US-BS")
        + per(3, "held 110.1 kg (1080 N) 1 min", y, "yes", "Y", "US-BS", "h#"),
        "PT-1": per(5, "held 260.2 kg (2553 N) 60 s, gate closes, no set", y, "yes", "Y", "CARA-PROOF"),
        "PT-2": per(5, "held 260.2 kg (2553 N) 60 s, no stitch break, no tear", y, "yes", "Y"),
        "PT-3": per(5, "held 156 kg (1530 N) 60 s", y, "yes", "Y"),
        "PT-5": per(1, "total slip after 10 cycles to 17.3 kg", "mm", "max", "5"),
        "PT-6": per(5, "held 143.7 kg (1410 N) 60 s, no box-X break, gate closes", y, "yes", "Y"),
        "LL-H": per(5, "slip after 1 h at 37.3 kg (366 N)", "mm", "max", "5", "LL-SLIP; LL-H-5MM"),
        "HB-7": per(5, "no slip at 43.4 kg (426 N), 1 min", y, "yes", "Y", "HB7-426")
        + per(5, "slip load", "kg", "min", "50.0", "LL-SLIP", "s#"),
        "PORT-1": [("1", "towel dry after 1 min hose", y, "yes", "Y", "PORT_FACING_W; PORT_TURN"),
                   ("1", "lap gap at 10.2 kg (100 N)", "mm", "max", "2", "PORT_FACING_W; PORT_TURN"),
                   ("1", "gloved lock adjustments OK out of 5", "count", "min", "5", "GLOVE-T")],
        "GT-1": per(3, "mu = ln(T / 49 N) / wrap angle (rad)", "-", "band", "0.20..0.40", "MU_WEB_FAB"),
        "FRAY-1": [(p, "no fray past the 2nd row after 3 washes", y, "yes", "Y", "NO-BIND")
                   for p in ("ULTRA|330D", "330D|330D", "500D|330D", "630D|330D", "HyperD300|330D", "100D|330D")],
        "WP-1": [(p, "no fray past the 2nd row after 3 washes", y, "yes", "Y", "B-1 NO-BINDING")
                 for p in ("330D|330D", "330D|ULTRA", "500D|330D", "100D|ULTRA")],
        "CA-1": per(3, "static XY UTS", "MPa", "min", "79.2", "PAHT_UTS", "XY#")
        + per(2, "static Z UTS", "MPa", "min", "42.3", "PAHT_UTS", "Z#")
        + per(3, f"cycles at the release level {lv['release']} (run-out 100000)", "cycles", "min", "100000", "PAHT_FAT", "RXY#")
        + per(3, "stiffness loss at run-out", "%", "max", "10", "PAHT_FAT", "SXY#")
        + per(2, f"Z cycles at {lv['release']}", "cycles", "min", "100000", "PAHT_FAT", "RZ#"),
        "CA-1@0.40": per(3, "cycles at 0.40 (run-out 100000)", "cycles", "min", "100000", "F-1 OPTION", "XY#"),
        "IM3-EC": per(3, f"cycles at {ec['min_n']} -> {ec['peak_n']} N (run-out 100000)", "cycles", "min", "100000", "P_cheek")
        + per(3, "no crack at 10x and held 2553 N after", y, "yes", "Y", "P_cheek", "p#"),
        "CA-5": per(3, "static stub peak", "N", "min", "3666", "PRYING-1.25") +
        [("mean", "mean of the 3 static peaks", "N", "min", "4400", "PRYING-1.25"),
         ("cyc", "joint step after 1e5 cycles at 1543 N", "mm", "max", "0.1", "BOSS-BENDING"),
         ("cyc", "no crack at the boss root after 1e5 cycles", y, "yes", "Y", "BOSS-BENDING")],
        "CA-3": per(3, "Z strength after 48 h at 40 C water", "MPa", "min", "37.6", "FI-INTERLAYER", "Z#")
        + per(3, "short-beam interlayer shear", "MPa", "min", "22.6", "FI-INTERLAYER", "SB#"),
        "CA-4": per(2, "no rupture after 8 h at 40 C (282 N link)", y, "yes", "Y", "CREEP"),
        "MT-1c": [("stand", "mean cinch tension, T5 crank 600 cycles", "N", "record", "", "CINCH_STATIC"),
                  ("stand", "peak-to-peak swing / mean tension (sets the CA-1 level, ca1_mt1c_confirm.md)", "%", "record", "", "CINCH_STATIC; CINCH-SWING"),
                  ("walk", "mean cinch tension, 10 min walk", "N", "record", "", "CINCH_STATIC"),
                  ("walk", "peak-to-peak swing / mean tension (sets the CA-1 level, ca1_mt1c_confirm.md)", "%", "record", "", "CINCH_STATIC; CINCH-SWING")],
        "T9": [("15in", "meat CG aft of the stay plane", "mm", "max", "190", "REV-C-CG"),
               ("19in", "meat CG aft of the stay plane", "mm", "max", "190", "REV-C-CG"),
               ("23in", "meat CG aft of the stay plane", "mm", "max", "190", "REV-C-CG"),
               ("fill", "bag CG aft (uniform fill)", "mm", "max", "205", "REV-C-CG"),
               ("tall", "tall-load CG aft", "mm", "max", "185", "REV-C-CG")],
        "T9-R3a": [("S15", "meat CG aft, S kit, top full, lid + 1 kg (sim 179.3)", "mm", "max", "190", "LID-SIM; INT-1")],
        "T9-R3b": [("L", "left strap tension after the walk", "N", "record", "", "CROWN_PRE_N; MU_LID"),
                   ("R", "right strap tension after the walk", "N", "record", "", "CROWN_PRE_N; MU_LID"),
                   ("both", ">= 40 N after the walk OR lid still seated", y, "yes", "Y", "CROWN_PRE_N; MU_LID")],
        "T9-R3c": [("S-full-L", "crown strap path, S kit full", "mm", "max", f"{s_path}", "ROLL-PATH; TORSO-LIN"),
                   ("S-full-R", "crown strap path, S kit full", "mm", "max", f"{s_path}", "ROLL-PATH; TORSO-LIN"),
                   ("L-6day", f"crown strap path, L kit 6-day (sim {cut['L']['sixday_mid_mm']})", "mm", "record", "", "ROLL-PATH; TORSO-LIN")],
        "T9-R3d": [("lid", "sewn lid mass (ledger booking)", "g", "band", f"{lid_g - 5:.1f}..{lid_g + 5:.1f}", "LID_SLIDER5_G; LID_THREAD"),
                   ("lid", "lid seated as drawn (photo)", y, "yes", "Y", "LID-SEAT")],
        "SL-1": per(5, "slider + cord pull mass", "g", "max", "15.0", "SLIDER-CORD")
        + [("label", "printed label mass", "g", "max", "1.0", "LABEL"),
           ("door", "gloved open / close without a snag, out of 20", "count", "min", "20", "SLIDER-CORD")],
        "CS-1": per(3, "compression set, 6 mm disc", "%", "max", "15", "XLPE-SET", "6mm#")
        + per(3, "compression set, 5 mm disc", "%", "max", "15", "XLPE-SET", "5mm#"),
        "AB-1": [("lab", "HyperD 300: no hole at 8000 rev", y, "yes", "Y", "HYPERD-ABRASION"),
                 ("lab", "630D: rev at end point (reference)", "rev", "record", "", "HYPERD-ABRASION"),
                 ("brush", "HyperD strip no worse than 630D after 50 passes", y, "yes", "Y", "HYPERD-ABRASION"),
                 ("print", "owner OK on the camo print (in writing)", y, "yes", "Y", "HYPERD-ABRASION")],
        "HS-1": [(f"T{t}-{kg}kg", "XLPE peak / EVA peak", "-", "max", "1.10", "XLPE-SHOULDER")
                 for t in (1, 2, 3) for kg in (30, 68)]
        + per(3, "no bottoming felt", y, "yes", "Y", "XLPE-SHOULDER", "T"),
        "ST-1": [("1", "one-hand gloved clip-ons, out of 10", "count", "min", "10", "")],
        "BU-1": [("1", "gloved kit / pawl cycles without binding, out of 20", "count", "min", "20", "BUSHING-LD")],
        "HB-1": [(f"T{t}", q, "kPa", "max", lim, "B-1 XLPE BELT; FRONT-STRAP")
                 for t in (1, 2, 3) for q, lim in (("wing worst", "56.5"), ("lumbar worst", "48.6"), ("front strap", "48.6"))],
        "HB-D2": [("0.5mm", "0.5 mm wing passes roll-over", y, "yes", "Y", "B-2 0.5MM"),
                  ("0.75mm", "0.75 mm wing passes roll-over", y, "yes", "Y", "BL-006 C2")],
        "BP-1": [("3mm", "3 mm core strip passes BP-1", y, "yes", "Y", "BL-005 STRIP"),
                 ("2mm", "2 mm core strip passes BP-1 (SF >= 1 at the factored strip load)", y, "yes", "Y", "K-1 2MM CORE")],
    }
    return m


SETTLES_DEFAULT = {"T1": "HA-LS-1 T1", "T2": "HA-LS-1 T2", "IM3-EP": "P_cheek", "HB-6": "INSERT-PULL",
                   "TL-1": "GUY-TOGGLE", "FS-O5": "ULTRA-200X STRIP", "WP-3": "A-2 TAIL", "WP-5": "B-10 TPU TRIM",
                   "WP-2": "C-6 TPU TAB", "HB-5": "C-1..C-3 7075 PLATE", "RF-1": "C-8 RAIL", "BP-2": "BL-005 STRIP",
                   "FT-S2": "W1/W2 NO WINGS", "HB-D1": "BL-006 B", "HB-D3": "BL-006 F"}


def results_rows(reg: dict, ow: list[dict], lv: dict, lid_g: float, cut: dict) -> list[dict]:
    m = measures(lv, lid_g, cut)
    out = []
    seen = set()

    def add(tid, grp, rel, items):
        for i, (sample, q, unit, chk, lim, settles) in enumerate(items, 1):
            out.append({"row_id": f"{tid}-{i:02d}", "test_id": tid, "group": grp, "release": rel, "sample": sample,
                        "quantity": q, "unit": unit, "check": chk, "limit": lim, "measured": "", "date": "",
                        "photo": "", "notes": "", "settles": settles})

    for o in ow:
        t = o["test"]
        if o["stage"] != "run" or t in seen or reg[t]["status"].startswith("COVERED"):
            continue
        seen.add(t)
        rel = o["release"] + (f"; {o['also']}" if o["also"] else "")
        items = m.get(t) or [("1", f"passes the register criterion: {reg[t]['pass_fail'][:150]}", "Y/N", "yes", "Y",
                              SETTLES_DEFAULT.get(t, ""))]
        add(t, o["group"], rel, items)
        if t == "CA-1":
            add("CA-1@0.40", o["group"], "OPTION F-1", m["CA-1@0.40"])
    return out


# ============================================================================ shopping list
LINKS = {
    "crane": "https://www.fruugo.us/300-kg-660-lbs-digital-lcd-hanging-scale-mini-industrial-crane-scale-with-hook-and-tare-function/p-376963170",
    "hd-come": "https://homedepot.com/p/Big-Red-2-Ton-Come-Along-Cable-Puller-with-2-Hooks-TR8021/100594355",
    "hf-strap": "https://go.harborfreight.com/61303/",
    "pins": "https://www.zoro.com/zoro-select-dowel-pin-harden-stl-m5x22mm-pk50-dp5005022-050p1/i/G3163027",
    "lc": "https://www.makerfabs.com/s-type-load-cell-100kg-200kg-300kg-500kg-1.html",
    "hx": "https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html",
    "nano": "https://store.arduino.cc/products/arduino-nano-every",
    "motor": "https://www.ebay.com/itm/266938738081",
    "shackle": "https://betterboat.com/products/stainless-steel-swivel-snap-shackle",
    "dial": "https://www.penntoolco.com/igaging-digital-indicator-w-magnetic-base-set-34-101/",
    "caliper": "https://go.harborfreight.com/63586",
    "fsr": "https://www.adafruit.com/products/166",
    "phyphox": "https://apps.apple.com/app/phyphox/id1127319693",
    "pocket": "https://www.wardsci.com/us/en/product/NA5812762/united-scientific-digital-pocket-scales",
    "spring": "https://aio.lv/en/product--kern-r100150-s-w--12021676.md",
    "lab": "https://measurlabs.com/products/textile-abrasion-resistance-martindale",
}


def _l(item, qty, unit, usd_each, supplier, source, kit, tests, long_lead="", note=""):
    return {"kit": kit, "item": item, "qty": qty, "unit": unit, "unit_usd": round(usd_each, 2),
            "total_usd": round(qty * usd_each, 2), "supplier": supplier, "price_source": source, "tests": tests,
            "long_lead": long_lead, "note": note}


def shopping(reg: dict) -> list[dict]:
    rp = rec_price
    A = "ASSUMPTION (shop price, check at purchase)"
    L = [
        # --- kit A pull bench (TEST_PLAN 4.1)
        _l("crane scale 300 kg / 660 lb, 0.1 kg, tare", 1, "each", 59.00, "Fruugo US", LINKS["crane"], "A", "all pulls"),
        _l("come-along, 2 ton cable puller (Big Red TR8021)", 1, "each", 30.30, "Home Depot", LINKS["hd-come"], "A", "all pulls"),
        _l("ratchet straps 1-1/2 in x 10 ft, 4-pack", 1, "pack", 17.99, "Harbor Freight 61303", LINKS["hf-strap"], "A", "rigging (never above 151 kg)"),
        _l("hardened dowel pins M5 x 22, 50-pack", 1, "pack", 11.79, "Zoro", LINKS["pins"], "A", "pin fixture"),
        _l("anchors: 4x4 lag-screwed into studs (or tow hitch / tree)", 1, "set", 40.00, "lumber yard", A, "A", "bench"),
        _l("pin fixture: steel flat bar 40 x 6 x 300, M8 bolts", 1, "set", 20.00, "hardware store", A, "A", "bench"),
        _l("bar clamps: 2 pairs Al 150 x 25 x 10, M6 bolts, grit cloth", 1, "set", 15.00, "hardware store", A, "A", "PT-2, PT-3, FS-O5"),
        _l("safety: glasses, gloves, moving blanket, back-up sling", 1, "set", 20.00, "hardware store", A, "A", "all"),
        _l("calibration jug 20 L", 1, "each", 10.00, "hardware store", A, "A", "scale check"),
        # --- kit B lever rig (CA1_fatigue_rig.md 5, itemized)
        _l("S-type load cell 100 kg", 1, "each", 23.60, "Makerfabs", LINKS["lc"], "B", "CA-*, IM3-EC, MT-1c"),
        _l("HX711 load-cell amplifier (SparkFun)", 1, "each", 11.50, "SparkFun", LINKS["hx"], "B", "CA-*, MT-1c"),
        _l("Arduino Nano Every", 1, "each", 14.50 * USD_PER_EUR, "Arduino Store (EUR 14.50)", LINKS["nano"], "B", "CA-*, MT-1c, FSR strips"),
        _l("gear motor 12 V 60 W 60 rpm 8 N m worm (uxcell)", 1, "each", 54.99, "eBay", LINKS["motor"], "B", "CA-*"),
        _l("12 V 10 A power supply", 1, "each", 20.00, "electronics shop", A, "B", "CA-*"),
        _l("MOSFET switch, hall sensor + magnets, AS5600 encoder", 1, "set", 15.00, "electronics shop", A, "B", "CA-*"),
        _l("6061-T6 flat bar 40 x 10 x 600 (lever)", 1, "each", 18.00, "metal supplier", A, "B", "CA-*"),
        _l("2 x 608 bearings, M8 shoulder bolt, 2 rod ends, M8 rod", 1, "set", 25.00, "hardware store", A, "B", "CA-*"),
        _l("compression spring 10-12 N/mm, >= 350 N, washer cage", 1, "each", 10.00, "hardware store", A, "B", "CA-*"),
        _l("turnbuckle M8, Al grip plates 4 x 50 x 40 x 6, M6 bolts", 1, "set", 20.00, "hardware store", A, "B", "CA-*"),
        _l("plywood 18 mm + 2x4, screws (rig base)", 1, "set", 20.00, "lumber yard", A, "B", "CA-*"),
        _l("S-type load cell 200 kg (CA-5 static pulls)", 1, "each", 23.60, "Makerfabs (200 kg option)", LINKS["lc"], "B", "CA-5"),
        _l("40 C box: cooler + 60 W heater + thermostat", 1, "set", 35.00, "hardware store", A, "B", "CA-3, CA-4, CS-1"),
        _l("3-point bend fixture", 1, "set", 10.00, "hardware store", A, "B", "CA-3, BP-1"),
        _l("SD-card logger module + USB power bank (MT-1c, logs while the rig moves)", 1, "set", 15.00, "electronics shop", A, "B", "MT-1c"),
        # --- kit C frame stand (TEST_PLAN 4.3)
        _l("hip log (4x4 in closed-cell foam to ~36 in)", 1, "each", 10.00, "hardware store", A + " (load_standard.md 5.1)", "C", "T1-T5"),
        _l("shoulder bar", 1, "each", 10.00, "hardware store", A + " (load_standard.md 5.1)", "C", "T1-T5"),
        _l("snap shackle, 316 swivel (drop release)", 1, "each", 14.39, "Better Boat", LINKS["shackle"], "C", "T4a, MT-1c"),
        _l("sand tube bags 60 lb", 8, "each", 6.00, "hardware store", A, "C", "T1-T5, T9, MT-1c, T2u"),
        _l("rubber gym mat 10-20 mm", 1, "each", 30.00, "sports shop", A + " (load_standard.md 5.1)", "C", "T4"),
        _l("19 mm plywood sheet", 1, "each", 40.00, "lumber yard", A, "C", "T4c"),
        _l("T5 crank: 12 V wiper motor, supply, crank, bungee, counter", 1, "set", 70.00, "auto parts", A + " (load_standard.md 5.1)", "C", "T5, MT-1c"),
        _l("22 mm hardwood dowel", 1, "each", 5.00, "hardware store", A, "C", "SP-1"),
        # --- kit D measuring (TEST_PLAN 4.4 + BL-038)
        _l("dial indicator 0-1 in with magnetic base (iGaging 34-101)", 1, "set", 39.95, "Penn Tool", LINKS["dial"], "D", "CA-5, T1, T4b"),
        _l("digital caliper 6 in", 1, "each", 9.99, "Harbor Freight 63586", LINKS["caliper"], "D", "CA-*, CS-1"),
        _l("force-sensitive resistors (Adafruit 166)", 8, "each", 3.95, "Adafruit", LINKS["fsr"], "D", "HB-1, HS-1, RF-1, BP-3"),
        _l("10x loupe", 1, "each", 8.00, "hardware store", A, "D", "FRAY-1, WP-1, CA-*"),
        _l("conditioning box + magnesium nitrate", 1, "set", 15.00, "chemical supplier", A, "D", "CA coupons"),
        _l("pocket scale 200 g x 0.01 g", 1, "each", 13.30, "Ward's Science (United Scientific)", LINKS["pocket"], "D", "SL-1, T9-R3d"),
        _l("spring scale 15 kg (147 N), Kern R100150-S-W", 1, "each", 6.99 * USD_PER_EUR, "aio.lv (EUR 6.99)", LINKS["spring"], "D", "T9-R3b, GT-1"),
        _l("compression-set jig: 2 Al plates 100 x 100 x 6, 3.0 + 2.5 mm spacers, 4 M6", 1, "set", 10.00, "hardware store", A, "D", "CS-1"),
        _l("stiff nylon scrub brush + 2 kg weight", 1, "set", 5.00, "hardware store", A, "D", "AB-1"),
        _l("phyphox app", 1, "each", 0.00, "free", LINKS["phyphox"], "D", "HB-2, T4a, GT-1"),
        # --- specimens: bought hardware (records)
        _l("wiregate carabiner, CAMP Nano 22 class", 15, "each", rp("carabiner_wiregate_22kn"), "CAMP dealers (rack of 6)", "record carabiner_wiregate_22kn (cost is an ASSUMPTION there)", "S", "PT-1 (5), MT-2 (5), PT-6 (5)"),
        _l("G-hook 25 mm aluminium, AustriAlpin DY25K-G", 5, "each", rp("g_hook_25mm_aluminium"), "AustriAlpin / Extremtextil", "record g_hook_25mm_aluminium (cost ASSUMPTION there)", "S", "MT-2"),
        _l("cam buckle 25 mm aluminium (Austere type)", 5, "each", rp("cam_25mm_al"), "Ripstop by the Roll / Extremtextil", "record cam_25mm_al", "S", "MT-3, US-BS",
           "LONG LEAD: RBTR all variants sold out, Extremtextil stock problems (2026-11-13). Order now; buy the pack's 5 cams in the same order"),
        _l("tri-glide 25 mm stainless", 3, "each", tg_ss_usd(), "Extremtextil art. 70460", "record triglide_25mm (stainless line, EUR 3.10 incl. VAT)", "S", "US-BS"),
        _l("heavy ladder lock 25 mm (ITW Super Ladderloc)", 11, "each", rp("ladder_lock_25mm_heavy"), "Liberty Mountain 6-pack / Buckleguy", "record ladder_lock_25mm_heavy", "S", "LL-H (5), HB-7 (5), PT-5 (1)"),
        _l("tri-glide 25 mm nylon", 6, "each", rp("triglide_25mm"), "Extremtextil", "record triglide_25mm", "S", "LL-H (5), PT-5 (1)"),
        _l("D-ring 25 mm aluminium", 5, "each", rp("d_ring_25mm_aluminium"), "Extremtextil", "record d_ring_25mm_aluminium", "S", "HB-7"),
        _l("YKK #10 coil slider, metal (cord pull fitted)", 5, "each", rp("slider_10"), "Rockywoods; alt. Shelby Outdoor EU", "record slider_10", "S", "SL-1",
           "LONG LEAD: Rockywoods listed sold out (2026-11-13); Shelby Outdoor EU stocks the YKK 10C slider"),
        _l("#10 coil zipper chain", 0.4, "m", rp("coil_zipper_10"), "Ripstop by the Roll", "record coil_zipper_10", "S", "SL-1"),
        _l("Dyneema cord 3 mm (slider pulls)", 1, "m", rp("dyneema_cord_3mm"), "Ripstop by the Roll", "record dyneema_cord_3mm", "S", "SL-1"),
        _l("printed label (one, heat transfer)", 1, "each", 5.00, "label printer", A, "S", "SL-1"),
        _l("side-release buckle 25 mm", 2, "each", rp("buckle_side_release_25mm"), "Strapworks", "record buckle_side_release_25mm", "S", "ST-1"),
        _l("poly webbing 25 mm", 20, "m", rp("poly_webbing_25mm"), "Strapworks", "record poly_webbing_25mm", "S", "MT-1, MT-3, US-BS, LL-H, HB-7, PT-5, PT-6, PORT-1, GT-1"),
        _l("poly webbing 38 mm", 3, "m", rp("poly_webbing_38mm"), "Strapworks", "record poly_webbing_38mm", "S", "PT-6 links, WP-3"),
        _l("XLPE L200 foam 5 + 6 mm", 0.35, "m2", rp("xlpe_foam_l200"), "Foam By Mail", "record xlpe_foam_l200", "S", "CS-1 (0.25), HS-1 (0.1)", "", "minimum order not known"),
        _l("EVA 45C foam 5 mm", 0.1, "m2", rp("eva_foam_45c"), "Seattle Fabrics", "record eva_foam_45c", "S", "HS-1"),
        _l("HDPE sheet 0.5 mm (BL-037 stiffener wing)", 0.05, "kg", rp("hdpe_sheet"), "McMaster-Carr", "record hdpe_sheet", "S", "HB-D2", "", "a 300 x 300 mm sheet is about 0.045 kg; minimum order may cost more"),
        _l("ROHACELL 71 IG-F core for the 2 mm strip", 0.02, "m2", rp("rohacell_71_igf"), "Rock West Composites", "record rohacell_71_igf", "S", "BP-1",
           "LONG LEAD: 2 mm is not a stock sheet (3 mm thinnest, back_system_integration.md); sand a 3 mm offcut or special order"),
        _l("200 g 2x2 carbon twill + epoxy for the 2 mm BP-1 coupon skins", round(bp1_cost()["skins_m2"], 3), "m2",
           rec_price("cfrp_t300_3k_woven_epoxy_ply"), "left over from the spreader / strip layup (else any composites shop)",
           "record cfrp_t300_3k_woven_epoxy_ply (BL-039)", "S", "BP-1"),
        _l("HyperD 300 printable, custom camo print", 1, "yd", rp("polyester_300d_printable"), "Ripstop by the Roll (custom print, 1 yd min)", "record polyester_300d_printable", "S", "AB-1, FRAY-1",
           "LONG LEAD: custom print, lead time not published"),
        _l("Martindale abrasion test, accredited lab (2 samples + order fee)", 1, "order", (2 * 66 + 97) * USD_PER_EUR, "Measurlabs (EUR 66 / sample + EUR 97 fee)", LINKS["lab"], "S", "AB-1",
           "LONG LEAD: about 4 weeks after the samples arrive", "the listed price is the ISO 12947-2 Martindale method; ask for ASTM D4966 to 8000 rev"),
    ]
    itemized = {"PT-1", "MT-2", "MT-3", "US-BS", "HB-7", "PT-5", "LL-H", "SL-1", "ST-1", "MT-1", "PT-6", "CS-1", "HS-1",
                "AB-1", "MT-1c", "B-28 slip", "BP-1"}
    for tid, r in reg.items():
        if not r["status"].startswith(("ACTIVE", "PROPOSED")) or tid in itemized:
            continue
        c = float(r["cost_usd"] or 0)
        if c <= 0:
            continue
        if tid == "T2u":
            L.append(_l("sacrificial P1 frame (IM3-EP, W-PULL, then T2u)", 1, "each", c, "owner's print + parts",
                        "frame_h1.md 5 unit cost", "S", "IM3-EP, W-PULL, T2u", "print time: allow 2 weeks with P2"))
            continue
        L.append(_l(f"specimens for {tid}: {r['specimen'][:80]}", 1, "lot", c, "see register",
                    f"test_register.csv {tid}: {r['cost_basis'][:90]}", "S", tid))
    return L


# ============================================================================ writing the kit
def _w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _csv(path: Path, rows: list[dict], cols=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = cols or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def shopping_md(sh: list[dict]) -> str:
    tot = sum(x["total_usd"] for x in sh)
    by = {}
    for x in sh:
        by[x["kit"]] = by.get(x["kit"], 0) + x["total_usd"]
    names = {"A": "Kit A pull bench", "B": "Kit B lever rig", "C": "Kit C frame stand", "D": "Kit D measuring",
             "S": "Specimens and lab"}
    cited = sum(x["total_usd"] for x in sh if x["price_source"].startswith(("http", "record")))
    L = ["# Shopping list (BL-038)", "", f"Total **USD {tot:,.2f}**. Prices from material records, cited shop pages "
         f"(links), or marked ASSUMPTION (check at purchase). Cited or record-priced: USD {cited:,.2f}; ASSUMPTION: "
         f"USD {tot - cited:,.2f}. Prices checked 2026-11-10 (TEST_PLAN §4) and 2026-11-13.", "",
         "**Order these first (long lead):**", ""]
    for x in sh:
        if x["long_lead"]:
            L.append(f"- **{x['item']}** ({x['tests']}): {x['long_lead']}")
    L += ["", "| kit | USD |", "|---|---:|"]
    L += [f"| {names[k]} | {v:,.2f} |" for k, v in by.items()]
    L += [f"| **total** | **{tot:,.2f}** |", "",
          "Not in this list: the bag, harness and belt materials themselves (pack BOM, "
          "`outputs/release/pack5200_corrie_f_rev3/manufacturing/bom.csv`). Swatches are cut from that fabric order, "
          "so buy the bag fabric with the kit. You already own (kit E): washing machine, winter gloves, freezer, hose, "
          "tape, paint pen, phone.", ""]
    for k in names:
        rows = [x for x in sh if x["kit"] == k]
        L += [f"## {names[k]}", "", "| item | qty | USD | source | for |", "|---|---:|---:|---|---|"]
        for x in rows:
            src = x["price_source"]
            src = f"[{x['supplier']}]({src})" if src.startswith("http") else f"{x['supplier']}; {src}"
            flag = " **LONG LEAD**" if x["long_lead"] else ""
            L.append(f"| {x['item']}{flag} | {x['qty']:g} {x['unit']} | {x['total_usd']:.2f} | {src} | {x['tests']} |")
        L.append("")
    return "\n".join(L)


ASCII = {
    "G2": """```
ANCHOR 1 -- sling -- COME-ALONG -- CRANE SCALE -- PIN FIXTURE -- SAMPLE -- PIN / BAR CLAMP -- sling -- ANCHOR 2
(tow hitch, tree,    (2 ton)       (300 kg,       (5 mm hardened          (5 mm pin, or the
 lagged 4x4)                       on a board)     dowel pin)              bar clamps for swatches)

You stand HERE, to the side  -->   o    (never in line with the pull; blanket over the sample)

LL-H dead hang:  beam -- lock + webbing -- sand bags 37.3 kg, 50 mm above the floor
US-BS:           pin -- [open cam] -- [stainless tri-glide] -- webbing -- scale -- come-along
```""",
    "G4": """```
                 load cell (S-type 100 kg) in the drive link
   motor + crank --> rod --> [spring cage] --> [LC] --> lever end (480 mm from pivot)
                                                           |
   pivot (M8 shoulder bolt, 2 x 608) O---------------------+-------- lever 6061 40 x 10 x 600
                                     | 120 mm
                               upper grip
                               [coupon]       ratio 480 / 120 = 4
                               lower grip -- turnbuckle -- base

CS-1 jig:   [plate]  disc disc disc  [plate]   spacers 3.0 mm (6 mm discs) / 2.5 mm (5 mm discs)
            4 x M6 bolts, tighten until the plates sit on the spacers, then 22 h in the 40 C box
```""",
    "G6": """```
        crown top bar --- shoulder bar (straps ratcheted to carry ~20 %)
              |
        [ P2 frame + bag, sand bags inside ]
              |
        hip log (foam 4x4) on the stand        come-along + crane scale pull down for T1 / T2 / T3
              |
        T5 crank: wiper motor -- crank -- bungee -- bag   (0.4 -> 1.6 g)

MT-1c:  IM2 strap free end -- [snap shackle] -- [100 kg S cell] -- [snap shackle] -- cam
        HX711 + Nano + SD logger taped to the frame, 80 Hz
```""",
    "G7": """```
GT-1 capstan:   spring scale <-- guy webbing over the packed bag's top corner --> 5 kg hanging
                mu = ln(T / 49 N) / wrap angle (rad)

T9-R3b:         spring scale on each crown strap tail: pull to 8.2 kg (80 N), lock
```""",
    "G3": """```
mesh laundry bag + towel + all swatches  ->  normal cold cycle  ->  line dry  ->  x3  ->  loupe on every edge
```""",
    "G5": """```
FS-O5 strip:  bar clamp -- 50 mm strip, 200 mm between the clamps -- bar clamp      (pull to break)
AB-1 brush:   board + taped strip;  brush + 2 kg;  50 passes along 200 mm
```""",
    "G1": """```
dry the spool -> print (frame profile, same job as a frame half) -> anneal 90 C 6 h -> cool in the oven
-> conditioning box (saturated magnesium nitrate, ~53 % RH) 7 days -> lever rig (G4)
```""",
}

GROUP_SAFETY = {
    "G1": ["Hot oven and hot nozzle: gloves. Magnesium nitrate is an oxidizer and an irritant: gloves, keep it away from "
           "heat sources and children, label the box."],
    "G2": ["Stand to the side of the load line, never in line with it. Moving blanket over every sample above 50 kg.",
           "Safety glasses and gloves on. Nobody near the line while it is loaded.",
           "Ratchet straps never in the load line above 151 kg (1480 N, ASSUMPTION: a third of the 1000 lb label).",
           "Crane scale stop: 280 kg (2750 N). PT-1 and PT-2 at 260.2 kg are the heaviest pulls: come-along only.",
           "LL-H hangs a dead load: nobody under it, 50 mm off the floor so a slip ends on the floor.",
           "If anything fails: stop, photograph, write it down, send the sheet. Do not repair and continue."],
    "G3": ["Nothing loaded. Keep the hot knife off unless a swatch fails."],
    "G4": ["The crank and lever move for days: guard the crank with a box, keep hands out while it runs, unplug before "
           "touching a coupon.", "40 C box: thermostat set and checked with a thermometer before you leave it.",
           "CA-5 static pulls reach 4.4 kN at the stub: blanket over the rig, stand to the side."],
    "G5": ["Same bench rules as G2. FS-O5 strips break suddenly: blanket over the clamps."],
    "G6": ["Back-up sling under every load. Nobody under the load. T2u (P1, 204 kg) outdoors with a 3 m exclusion zone.",
           "Nobody carries the frame until T1, T3, T2 and T4 have passed. MT-1c stage 1 runs on the stand for that reason.",
           "T4c: -20 C parts are brittle; gloves and glasses."],
    "G7": ["Loaded walks: a second person nearby, flat ground first, stop at any crack noise. Float meat limit 53 kg "
           "(56 kg only after T5f)."],
}


def record_bullets(rows: list[dict]) -> list[str]:
    """Consecutive rows that ask the same thing collapse into one bullet with a row range."""
    how = {"yes": "type Y or N", "record": "type the value"}
    out, i = [], 0
    while i < len(rows):
        j = i
        key = lambda x: (x["test_id"], x["quantity"], x["unit"], x["check"], x["limit"])  # noqa: E731
        while j + 1 < len(rows) and key(rows[j + 1]) == key(rows[i]):
            j += 1
        a, b = rows[i], rows[j]
        ids = a["row_id"] if i == j else f"{a['row_id']} to {b['row_id']}"
        smp = a["sample"] if i == j else f"{a['sample']} to {b['sample']}"
        h = how.get(a["check"]) or {"max": f"{a['unit']}, pass if at most {a['limit']}",
                                    "min": f"{a['unit']}, pass if at least {a['limit']}",
                                    "band": f"{a['unit']}, pass if {a['limit'].replace('..', ' to ')}"}[a["check"]]
        if a["check"] == "record":
            h = f"type the value in {a['unit']}"
        out.append(f"- `{ids}` ({smp}): {a['quantity']}. {h[0].upper() + h[1:]}.")
        i = j + 1
    return out


PREP = {
    "G2": ["**Sew before the weekend (about 5 h, same machine, thread and needle as the pack):**", "",
           "1. MT-1: 10 loops of 25 mm poly webbing; fold each end into a 20 mm loop and close it with a 25 x 25 mm "
           "box-X, stitch 301, 7 SPI, bonded nylon tex 135, Nm 140 round-point needle.",
           "2. PT-2: 5 x T3 tongue on a 70 mm B-17 tab on a B-01 swatch about 200 x 200 mm (`bag_attachment.md` 5 T3).",
           "3. PT-3: 5 x HE eye on a B-18 + B-01 + B-05 seam swatch, no binding.",
           "4. PT-6: 5 B-24 links to the cut list (carabiner + 3 loops).",
           "5. US-BS: 3 x 600 mm of 25 mm webbing threaded through a cam with the stainless tri-glide behind it.",
           "6. LL-H: 5 x 25 mm webbing through a heavy ladder lock + nylon tri-glide; 2 of them on a hinge-band tab "
           "like the B-28 front lock.",
           "7. PORT-1: one 300 x 300 mm B-01 panel with a B-27 lapped slit and B-27f facing (op sequence).",
           "8. SL-1: a 400 mm #10 coil door sample on 330D tabs with 2 sliders; a 3 mm cord pull on each of 5 sliders.",
           "9. Label every sample with a paint pen: test ID and sample number (PT-2-1 ... PT-2-5).", ""],
    "G3": ["**Sew first:** the 6 FRAY-1 SSa2 swatches (rotary-cut, edges NOT seared) and the 4 WP-1 swatches (seared), "
           "200 mm each, as listed under each test below.", ""],
    "G5": ["**Make first:** the specimens listed under each test (register `specimen`). Ship the AB-1 lab samples on "
           "day 1.", ""],
    "G6": ["**Before:** CA-1 at the release level, IM3-EC and CA-5 have passed (G4), and MT-1 (G2). Print P1 and P2 "
           "from the released files, same spool and profile as the coupons. Sew the bag (G2 + G3 passed).", ""],
    "G7": ["**Before:** T1, T3, T2 and T4 have passed on P2 (G6). Then the pack may be carried.", ""],
    "G4": ["**Before:** the coupons have had their 7 days (G1). Build the rig (one weekend, `CA1_fatigue_rig.md` 4) "
           "and calibrate it with the 20 L jug.", ""],
}


def _ca1_steps(lv: dict) -> list[str]:
    c = ca1_forces(lv["release"])
    c4 = ca1_forces(0.40)
    return [
        "Calibrate: hang the 20.0 kg jug in place of the coupon; the cell must read 49 N. Write the reading.",
        "Static (5 bars): put the turnbuckle in place of the spring; clamp an XY bar 35 mm deep in each grip; turn "
        "the turnbuckle about 1 turn every 10 s until the bar breaks; peak cell force x 4 / smallest gauge area = "
        "strength in MPa. 3 XY bars, then 2 Z bars (CA1_fatigue_rig.md 6 step 1).",
        "UTS_meas = mean of the 3 XY strengths (cap 88 MPa). Work out your own peak: F_max = "
        f"{lv['release']} x 0.8 x UTS_meas x area (at 88 MPa and 40 mm2: {c['F_max_N']} N; the cell then reads "
        f"{c['link_N']} N). F_min = 0.1 x F_max.",
        "Set the crank throw and the turnbuckle so the cell swings between F_min / 4 and F_max / 4; check over 20 "
        "slow turns by hand before the motor runs.",
        f"Release level, 3 XY bars one at a time: run to 100,000 cycles (27.8 h at 1 Hz). The rig stops itself if "
        f"the bar breaks, its stiffness drops more than 10 % or the force drifts more than 5 %.",
        "After each run-out look at the gauge and fillets with the loupe; then pull that bar to failure (step 2): "
        "it must keep at least 0.9 x UTS_meas.",
        f"Then 2 Z bars at the release level ({lv['release']} x 0.8 x the Z strength).",
        f"Only if every release-level bar passed: 3 XY bars at 0.40 ({c4['F_max_N']} N peak at 88 MPa).",
        "2 of 3 at a level is inconclusive: run 3 more; a level passes only with 5 of 6.",
        "Send the rig's CSV log with the results sheet."]


GUIDE_STEPS: dict = {}


def guide_md(gr: dict, reg: dict, lv: dict, lds: dict, res: list[dict], ow: list[dict]) -> str:
    rel_name = {k: lab for k, lab, _ in RELEASES}
    L = [f"# {gr['id']}: {gr['title']}", "", f"**When:** {gr['when']}  ", f"**Rig:** {gr['rig']}  ",
         f"**Kits:** {gr['kits']}", "", gr["intro"], ""]
    seq = [o for o in ow if o["group"] == gr["id"]]
    hon = sum(o["hands_on_h"] for o in seq)
    mac = sum(o["machine_h"] for o in seq)
    if not gr.get("print_only"):
        L += [f"About **{hon:.1f} h** hands-on and **{mac:.0f} h** of machine time.", ""]
    L += ["## Safety (read before you start)", ""] + [f"- {s}" for s in GROUP_SAFETY[gr["id"]]] + [""]
    L += ["## Rig sketch", "", ASCII[gr["id"]], "", f"Picture: `sketches/{gr['id']}_rig.png`", ""]
    L += PREP.get(gr["id"], [])
    L += ["## Tests in this session, in order", "", "| # | test | releases |", "|---:|---|---|"]
    for i, o in enumerate(seq, 1):
        rr = rel_name[o["release"]] + (f" + {rel_name[o['also']]}" if o["also"] else "")
        L.append(f"| {i} | {o['test']} | {rr} |")
    L.append("")
    if gr.get("print_only"):
        L += ["## Print list (one job, same spool and profile as the frame)", "",
              "| coupon | for | count |", "|---|---|---:|",
              "| XY dog-bone bars 170 x 20 (gauge 10 x 4 x 60) | CA-1 | 12 + 2 spare |",
              "| Z bars 100 x 20 (gauge 10 x 6 x 30), standing | CA-1 | 4 + 1 spare |",
              "| Z bars + short-beam blocks 24 x 8 x 6 | CA-3 | 3 + 3 |",
              "| XY bars | CA-4 | 2 |",
              "| z 234 joint stub pairs (H1 bosses, traps) | CA-5 | 4 |",
              "| IM3 eye coupons, 120 mm stay at z 520, **28 mm cheek** | IM3-EC | 3 |",
              "| insert blocks (M5 heat-set) | HB-6 | 5 |",
              "| 150 mm H1 sleeve segment | T7 | 1 |", "",
              "Steps:", "",
              "1. Dry the spool. Print with the frame profile (`designs/pack_5200/print/frame_h1/README.md`): 0.6 mm "
              "hardened nozzle, 290 C, bed 100 C, 0.20 mm layers, 6 walls, 100 % infill.",
              "2. XY bars lie flat on their 10 mm face (4 mm is the print height), like the frame.",
              "3. Anneal 90 C for 6 h on a flat plate; cool in the oven.",
              "4. Into the conditioning box for **7 days** (23 C, about 53 % RH). Write the date on the box.",
              "5. Measure each bar's gauge width and thickness at 3 points with the caliper; write the smallest on the bar.",
              "", "## Order today (long lead)", "",
              "- 25 mm aluminium cams (MT-3, US-BS) and the pack's own 5: both resellers out of stock on 2026-11-13.",
              "- YKK #10 sliders (SL-1): Rockywoods sold out; Shelby Outdoor EU has them.",
              "- HyperD 300 custom camo print (AB-1, FRAY-1) and the Martindale lab booking (about 4 weeks).",
              "- 2 mm ROHACELL 71 (BP-1): not a stock sheet; sand a 3 mm offcut or special-order.",
              "- Everything else in `shopping_list.md`.", ""]
        return "\n".join(L)
    for i, o in enumerate(seq, 1):
        t = o["test"]
        r = reg[t]
        L += [f"## {i}. {t}: {r['title']}", "", f"**Why:** {r['gates']}  ", f"**Specimen:** {r['specimen']}", ""]
        if r["status"].startswith("COVERED"):
            L += [f"Nothing extra to run: {r['what_it_proves']}.", ""]
            continue
        if t in lds:
            L += load_table(lds[t]) + [""]
        if t == "CA-1":
            L += [f"Release level today: **{lv['release']}** (governing flip {lv['flip_gov']}: body "
                  f"{lv['flip_body']}, 28 mm IM3 cheek {lv['flip_cheek']}, {lv['flip_cheek_dir']} with the pull 10 deg "
                  f"further aft; + 0.02), the level in `CA1_fatigue_rig.md` section 1 (confirmed by BL-039, "
                  f"`analysis/ca1_mt1c_confirm.md`). It holds only if MT-1c finds the cinch static (swing <= "
                  f"{lv['swing_ok_release_pct']} %). Run the 0.40 bars too: they cover a swing up to "
                  f"{lv['swing_ok_040_pct']:.0f} %. Above that R1 needs {lv['release_cycled']} (0.40 does not cover it).", ""]
        steps = GUIDE_STEPS.get(t) or [s.strip() for s in r["steps"].split(";") if s.strip()]
        L += ["**Steps**", ""] + [f"{k}. {s[0].upper() + s[1:]}" for k, s in enumerate(steps, 1)] + [""]
        L += [f"**Pass:** {r['pass_fail']}", ""]
        mine = [x for x in res if x["test_id"] == t or (t == "CA-1" and x["test_id"] == "CA-1@0.40")]
        if mine:
            L += ["**Write in the results sheet** (`results_template.csv`, column `measured`):", ""]
            L += record_bullets(mine)
            L.append("")
        if r["notes"]:
            L += [f"Note: {r['notes']}", ""]
        L += [f"Defined in: {r['defined_in']}", ""]
    L += ["## After the session", "", "1. Fill `measured` and `date` for every row you ran; leave the rest empty.",
          "2. Photograph every failed or doubtful sample; put the photo number in `photo`.",
          "3. Send the sheet. The engineers read it back with `huntkit.manufacturing.test_results`.", ""]
    return "\n".join(L)


def readme_md(ow, sh, lv, rk, reg, res) -> str:
    tot = sum(x["total_usd"] for x in sh)
    rel_name = {k: lab for k, lab, _ in RELEASES}
    hon = sum(o["hands_on_h"] for o in ow)
    mac = sum(o["machine_h"] for o in ow)
    L = ["# Pack 5200 physical test kit (BL-038)", "",
         f"Manufacturing-engineer, {DATE}. Generated by `designs/pack_5200/physical_test_kit.py` from "
         "`designs/pack_5200/tests_physical/` (TEST_PLAN.md, test_register.csv, CA1_fatigue_rig.md). Re-run the "
         "script after the register changes; do not edit these files by hand.", "",
         "## Start here", "",
         "1. Read **G1** today: order the long-lead parts and print the frame coupons (they need 7 days).",
         "2. Buy the rest from `shopping_list.md` " f"(total **USD {tot:,.0f}**).",
         "3. Run the sessions G2 to G7 in order. Each guide is one session, written for a phone.",
         "4. Fill `results_template.csv` (columns `measured`, `date`, `photo`, `notes`) and send it after each session.", "",
         "## What gets released, in this order", ""]
    for k, lab, what in RELEASES:
        ts = [o["test"] for o in ow if o["release"] == k and o["stage"] == "run"]
        L += [f"**{lab}**: {what}.  ", f"Tests: {', '.join(dict.fromkeys(ts))}", ""]
    L += ["Frame release R1 needs, in order: CA-1 at the release level **" + str(lv["release"]) + "** (governing flip "
          f"{lv['flip_gov']} + 0.02, from the BL-027 body and the 28 mm IM3 cheek; confirmed by BL-039), IM3-EC and CA-5 on the coupons; MT-1 on "
          "the bench; then on the first frames IM3-EP and W-PULL (P1), T9, T1, T2 and MT-1c (P2). "
          f"MT-1c's measured cinch swing sets the CA-1 level R1 needs (BL-039): swing <= {lv['swing_ok_release_pct']} %: "
          f"{lv['release']}; up to {lv['swing_ok_040_pct']:.0f} %: the 0.40 pass as well; above: **{lv['release_cycled']}** "
          f"(H1's fatigue with the cinch fully cycling is {lv['fatigue_cycled']} against {lv['fatigue_static']} static).", "",
         "## Sessions", "", "| session | what | when | hands-on h | machine h |", "|---|---|---|---:|---:|"]
    for gr in GROUPS:
        seq = [o for o in ow if o["group"] == gr["id"]]
        L.append(f"| [{gr['id']}](guides/{gr['id']}.md) | {gr['title']} | {gr['when']} | "
                 f"{sum(o['hands_on_h'] for o in seq):.1f} | {sum(o['machine_h'] for o in seq):.0f} |")
    L += [f"| | **total** | | **{hon:.1f}** | **{mac:.0f}** |", "",
          "Hands-on and machine hours are the register's estimates (ASSUMPTION per row). The calendar is set by the "
          "lever rig (about 8 CA-1 runs, 3 IM3-EC, CA-5 and CA-3/CA-4 at 1 Hz, ~28 h each) and by the 4-week lab "
          "turnaround for AB-1.", "",
          "## Order of work", "", "Full list: `order_of_work.csv`. Inside each session the R1 tests run first, then "
          "the bag, then the BL-037 gates (tests that share a rig or a specimen batch stay together).", "",
          "| # | session | test | releases |", "|---:|---|---|---|"]
    for o in ow:
        rr = rel_name[o["release"]] + (f" + {rel_name[o['also']]}" if o["also"] else "")
        stage = " (print only)" if o["stage"] != "run" else ""
        L.append(f"| {o['seq']} | {o['group']} | {o['test']}{stage} | {rr} |")
    L += ["", "## Value of the gram tests (re-scored, TEST_PLAN §5)", "",
          "| rank | test | grams | g per $-eq | note |", "|---:|---|---:|---:|---|"]
    L += [f"| {d['rank']} | {d['test']} | {d['grams']:.1f} | {d['score']:.2f} | {d['note']} |" for d in rk]
    L += ["", "## Results sheet", "",
          f"`results_template.csv` has {len(res)} rows over {len({x['test_id'] for x in res})} tests. Each row says how "
          "it is judged (`check`: max, min, band, yes, record) against `limit`. Type numbers in the unit shown; type "
          "Y or N for yes/no rows. Do not change the other columns. Read back with:", "",
          "```", "python -m huntkit.manufacturing.test_results outputs/release/test_kit/results_template.csv --md report.md", "```", "",
          "It reports each test as PASS / FAIL / PARTIAL / OPEN, each release, and each ASSUMPTION as VERIFIED / "
          "FAILED / OPEN (`settles` column).", "",
          "## Files", "", "- `guides/G1.md` ... `guides/G7.md`: one session each", "- `shopping_list.md`, `shopping_list.csv`",
          "- `order_of_work.csv`", "- `results_template.csv`", "- `sketches/*.png`: rig sketches", "- `test_kit.pdf`: everything above in one PDF",
          "- `manifest.json`", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------- pictures
def sketches(outdir: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Circle

    outdir.mkdir(parents=True, exist_ok=True)
    paths = []

    def box(ax, x, y, w, h, txt, fc="#e8edf2", fs=9):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="#333", lw=1.2))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, wrap=True)

    def new(title, w=11, h=6.2):
        fig, ax = plt.subplots(figsize=(w, h), dpi=110)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 56)
        ax.axis("off")
        ax.set_title(title, fontsize=13, weight="bold", loc="left")
        return fig, ax

    def save(fig, name):
        p = outdir / name
        fig.savefig(p, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(p)

    # G2 pull bench
    fig, ax = new("G2 pull bench (kit A): pulls along the floor, you stand to the side")
    ax.plot([2, 98], [36, 36], color="#888", lw=2, zorder=0)
    for x, w, t, c in [(1, 9, "ANCHOR 1\ntow hitch /\nlagged 4x4", "#d9d2c3"), (13, 12, "COME-ALONG\n2 ton", "#e8edf2"),
                       (28, 12, "CRANE SCALE\n300 kg\non a board", "#ffe9a8"), (43, 11, "PIN FIXTURE\n5 mm pin", "#e8edf2"),
                       (57, 13, "SAMPLE\n(hook, loop,\nswatch)", "#cfe8cf"), (73, 12, "PIN or\nBAR CLAMPS", "#e8edf2"),
                       (88, 11, "ANCHOR 2", "#d9d2c3")]:
        box(ax, x, 30, w, 12, t, fc=c)
    ax.add_patch(Circle((63, 20), 2.2, fc="#c33"))
    ax.text(66, 20, "YOU: stand here, to the side.\nBlanket over the sample. Glasses + gloves.", va="center", fontsize=9)
    ax.text(2, 12, "Load slowly: one click a second. Stop at the target, hold, re-tension if it drops.\n"
                   "Scale stop 280 kg. Ratchet straps never above 151 kg.  kg on scale = N / 9.81", fontsize=9)
    box(ax, 2, 46, 30, 8, "LL-H: beam - lock + webbing - sand bags\n37.3 kg, 50 mm above the floor, 1 h", fc="#f2e1e1", fs=8)
    box(ax, 35, 46, 34, 8, "US-BS: pin - OPEN cam - stainless tri-glide\n- webbing - scale - come-along, 110.1 kg", fc="#f2e1e1", fs=8)
    box(ax, 72, 46, 26, 8, "PORT-1: panel over a tub, hose 1 min,\nguy at 45 deg (5 kg); lap pull 10.2 kg", fc="#f2e1e1", fs=8)
    save(fig, "G2_rig.png")

    # G4 lever rig
    fig, ax = new("G4 lever fatigue rig (kit B, CA1_fatigue_rig.md): 4:1 lever, soft spring = constant load")
    ax.plot([10, 90], [38, 38], color="#555", lw=8)
    ax.add_patch(Circle((22, 38), 1.8, fc="#333"))
    ax.text(22, 42, "pivot (2 x 608)", ha="center", fontsize=9)
    box(ax, 30, 18, 8, 14, "COUPON\n(gauge\n10 x 4)", fc="#cfe8cf", fs=8)
    ax.plot([34, 34], [32, 38], color="#333", lw=2)
    ax.plot([34, 34], [12, 18], color="#333", lw=2)
    box(ax, 28, 6, 12, 6, "turnbuckle -\nbase", fs=8)
    ax.text(26, 34, "120 mm", fontsize=8, ha="right")
    ax.text(60, 40, "480 mm", fontsize=8)
    box(ax, 80, 18, 10, 8, "LOAD CELL\n100 kg", fc="#ffe9a8", fs=8)
    box(ax, 80, 8, 10, 8, "SPRING\n10-12 N/mm", fs=8)
    box(ax, 80, -2, 10, 8, "MOTOR 60 rpm\n+ crank e", fs=8)
    ax.plot([85, 85], [6, 8], color="#333", lw=2)
    ax.plot([85, 85], [16, 18], color="#333", lw=2)
    ax.set_ylim(-4, 56)
    ax.plot([85, 85], [26, 38], color="#333", lw=2)
    box(ax, 2, 46, 40, 8, "CS-1 jig: plate | 3 discs | plate, spacers 3.0 / 2.5 mm,\n22 h at 40 C, recover 24 h", fc="#f2e1e1", fs=8)
    box(ax, 46, 46, 50, 8, "Calibrate: hang a 20.0 kg jug in place of the coupon:\nthe cell must read 49 N (196 N / 4)", fc="#f2e1e1", fs=8)
    save(fig, "G4_rig.png")

    # G6 frame stand + MT-1c
    fig, ax = new("G6 frame stand (kit C) and the MT-1c cinch readout")
    box(ax, 30, 44, 40, 6, "shoulder bar (straps ratcheted to ~20 %)", fs=9)
    box(ax, 36, 18, 28, 24, "P2 frame + bag\nsand bags inside\nmeat on IM1-IM3", fc="#cfe8cf")
    box(ax, 30, 10, 40, 6, "hip log (4x4 foam) on the stand", fs=9)
    box(ax, 74, 22, 22, 12, "MT-1c: IM2 free end -\nshackle - 100 kg cell -\nshackle - cam\nlog 80 Hz to SD", fc="#ffe9a8", fs=8)
    box(ax, 2, 22, 26, 12, "T5 crank: wiper motor,\nbungee, 0.4 -> 1.6 g\n(MT-1c stage 1: 600 cycles)", fs=8)
    ax.text(2, 3, "Back-up sling under the load. Nobody under it. T2u (P1) outdoors, 3 m exclusion zone, last.", fontsize=9)
    save(fig, "G6_rig.png")

    # G7 capstan + cinch
    fig, ax = new("G7 GT-1 capstan and T9-R3b crown-strap cinch")
    box(ax, 30, 14, 40, 22, "PACKED BAG\n(top corner)", fc="#cfe8cf")
    ax.plot([10, 32, 68, 85], [40, 37, 37, 18], color="#333", lw=3)
    box(ax, 2, 38, 14, 8, "SPRING SCALE\npull slowly", fc="#ffe9a8", fs=8)
    box(ax, 80, 8, 12, 8, "5 kg\nhanging", fs=8)
    ax.text(2, 4, "mu = ln(T / 49 N) / wrap angle in radians (angle from phyphox: tilt of each leg).  "
                  "Pass band 0.20-0.40.\nT9-R3b: scale on each crown-strap tail, pull to 8.2 kg (80 N), lock; read again "
                  "after a 30 min walk and a 0.5 m set-down.", fontsize=9)
    save(fig, "G7_rig.png")

    for gid, title, text in [("G1", "G1 coupons: print, anneal, condition", ASCII["G1"]),
                             ("G3", "G3 wash swatches", ASCII["G3"]), ("G5", "G5 bench session 2", ASCII["G5"])]:
        fig, ax = new(title, h=3.2)
        ax.set_ylim(0, 20)
        ax.text(1, 10, text.strip("`\n"), family="monospace", fontsize=8, va="center")
        save(fig, f"{gid}_rig.png")
    return paths


def charts(ow, sh, lv, rk, outdir: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paths = []
    colors = {"R1": "#2f5d8a", "BAG-CUT": "#4f8a3a", "BAG-BATCH": "#8ab26a", "BL037": "#c7882a", "CARRY": "#9a9a9a"}
    rel_name = {k: lab for k, lab, _ in RELEASES}

    # 1. order of work, one bar per test, grouped by session
    runs = [o for o in ow if o["stage"] == "run"]
    fig, ax = plt.subplots(figsize=(8.5, 13), dpi=100)
    y = 0
    yt, yl = [], []
    for gr in GROUPS:
        seq = [o for o in runs if o["group"] == gr["id"]]
        if not seq:
            continue
        y += 0.5
        ax.text(-0.2, y, f"{gr['id']}  {gr['title']}", fontsize=9, weight="bold", ha="left", va="center")
        y += 1.2
        for o in seq:
            ax.barh(y, 1, color=colors[o["release"]], left=0)
            if o["also"]:
                ax.barh(y, 0.25, color=colors[o["also"]], left=1.0)
            yt.append(y)
            yl.append(o["test"])
            y += 1
        y += 0.6
    ax.set_yticks(yt)
    ax.set_yticklabels(yl, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(-0.2, 1.5)
    ax.set_xticks([])
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax.legend(handles, [rel_name[k] for k in colors], loc="lower right", fontsize=8, frameon=False)
    ax.set_title(f"BL-038 order of work: {len(runs)} test runs in 6 sessions (colour = what it releases)",
                 fontsize=10, loc="left")
    p = outdir / "order_of_work.png"
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p)

    # 2. shopping card
    names = {"A": "Kit A pull bench", "B": "Kit B lever rig", "C": "Kit C frame stand", "D": "Kit D measuring",
             "S": "Specimens + lab"}
    by = {k: sum(x["total_usd"] for x in sh if x["kit"] == k) for k in names}
    tot = sum(by.values())
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 9), dpi=100, gridspec_kw={"height_ratios": [1, 1.3]})
    ks = list(names)
    a1.barh([names[k] for k in ks], [by[k] for k in ks], color="#2f5d8a")
    for i, k in enumerate(ks):
        a1.text(by[k] + 10, i, f"${by[k]:,.0f}", va="center", fontsize=9)
    a1.invert_yaxis()
    a1.set_title(f"Shopping list: USD {tot:,.0f} in all", fontsize=12, loc="left", weight="bold")
    a1.set_xlim(0, max(by.values()) * 1.25)
    for s in ("top", "right"):
        a1.spines[s].set_visible(False)
    a2.axis("off")
    ll = [x for x in sh if x["long_lead"]]
    import textwrap
    txt = "ORDER FIRST (long lead):\n\n" + "\n".join(
        f"- {x['item']}  ({x['tests']})\n" + textwrap.fill(x["long_lead"], 78, initial_indent="    ", subsequent_indent="    ")
        for x in ll)
    a2.text(0, 1, txt, va="top", fontsize=8.5, family="DejaVu Sans")
    p = outdir / "shopping.png"
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p)

    # 3. ranking + release rule card
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 6.5), dpi=100, gridspec_kw={"width_ratios": [1.4, 1]})
    rr = rk[:14]
    a1.barh([d["test"] for d in rr], [d["score"] for d in rr],
            color=["#9a9a9a" if not d["booked"] else "#c7882a" for d in rr])
    for i, d in enumerate(rr):
        a1.text(d["score"] + 0.03, i, f"{d['grams']:.0f} g", va="center", fontsize=8)
    a1.invert_yaxis()
    a1.set_title("Gram tests: grams per $-equivalent (re-scored)", fontsize=10, loc="left")
    for s in ("top", "right"):
        a1.spines[s].set_visible(False)
    a2.axis("off")
    ca = next(d for d in rk if d["test"] == "CA-1")
    a2.text(0, 1, "Frame release R1\n\n"
                  f"CA-1 release level: {lv['release']}\n  governing flip {lv['flip_gov']}\n  (body {lv['flip_body']}, 28 mm cheek\n  {lv['flip_cheek']} / {lv['flip_cheek_dir']} at +10 deg)\n  + 0.02\n\n"
                  f"MT-1c swing sets the level:\n  <= {lv['swing_ok_release_pct']} %: {lv['release']}\n  <= {lv['swing_ok_040_pct']:.0f} %: 0.40\n  above: {lv['release_cycled']}\n\n"
                  f"CA-1 at 0.40 is worth {ca['grams']:.1f} g\n(option F-1, not booked; was 60 g)\nrank {ca['rank']} of {len(rk)}",
            va="top", fontsize=10, family="DejaVu Sans")
    p = outdir / "ranking.png"
    fig.savefig(p, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    paths.append(p)
    return paths


def pdf(outdir: Path, md_files: list[Path], images: list[Path]) -> Path:
    """One PDF of the kit (README, shopping list, guides) through huntkit.manufacturing.techpack (non-strict)."""
    from huntkit.manufacturing import techpack as T

    def blocks_of(md: str) -> list:
        out, tab = [], []

        def flush():
            if tab:
                rows = [[re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", c).replace("**", "").replace("`", "").strip()
                         for c in r.strip().strip("|").split("|")] for r in tab if not re.match(r"^\|[-:| ]+\|$", r.strip())]
                n = max(len(r) for r in rows)
                rows = [r + [""] * (n - len(r)) for r in rows]
                out.append(T.table(rows, [250 / n] * n))
                tab.clear()

        code = False
        for line in md.splitlines():
            if line.startswith("```"):
                flush()
                code = not code
                continue
            if code:
                out.append(T.para(line.replace(" ", " ") or " "))
                continue
            if line.startswith("|"):
                tab.append(line)
                continue
            flush()
            if line.startswith("## ") or line.startswith("# "):
                out.append(T.h2(line.lstrip("# ")))
            elif line.strip():
                out.append(T.para(re.sub(r"[*`]", "", line)))
        flush()
        return out

    secs = []
    for f in md_files:
        txt = f.read_text(encoding="utf-8")
        title = txt.splitlines()[0].lstrip("# ")
        b = blocks_of("\n".join(txt.splitlines()[1:]))
        img = outdir / "sketches" / f"{f.stem}_rig.png"
        if img.exists():
            b.insert(0, T.image(img, 250, 120))
        secs.append(T.Section(title, b))
    secs.append(T.Section("Pictures", [T.image(p, 250, 165) for p in images]))
    tp = T.TechPack(title="Pack 5200 physical test kit", subtitle="BL-038: order of work, shopping list, guides",
                    date=DATE, footer="Hunting-appeal BL-038 test kit", cover=[["generated by", "designs/pack_5200/physical_test_kit.py"]],
                    sections=secs)
    return T.tech_pack(tp, outdir / "test_kit.pdf", strict=False)


def screenshots(pdf_path: Path, imgs: list[Path]) -> list[Path]:
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    from PIL import Image
    for i, src in enumerate(imgs, 1):
        dst = SCREENS / f"{SHOT}_{i}.png"
        im = Image.open(src).convert("RGB")
        if im.width > 1400:
            im = im.resize((1400, int(im.height * 1400 / im.width)))
        im.save(dst, optimize=True)
        out.append(dst)
    # a rasterized PDF page (a guide page, as the owner sees it)
    try:
        tmp = OUT / "preview"
        tmp.mkdir(exist_ok=True)
        subprocess.run(["pdftoppm", "-png", "-r", "80", "-f", "1", "-l", "4", str(pdf_path), str(tmp / "page")],
                       check=True, capture_output=True)
        pages = sorted(tmp.glob("page*.png"))
        if pages:
            dst = SCREENS / f"{SHOT}_{len(out) + 1}.png"
            shutil.copy(pages[min(1, len(pages) - 1)], dst)
            out.append(dst)
    except Exception:                                    # pragma: no cover
        pass
    for p in out:
        assert p.stat().st_size <= 1.5e6, p
    return out


# ============================================================================ checks and main
def checks(reg: dict, ow, sh, res, lv) -> list[str]:
    msgs = []
    must = ["HS-1", "CS-1", "AB-1", "SL-1", "ST-1", "BU-1", "T9-R3a", "T9-R3b", "T9-R3c", "T9-R3d", "US-BS", "PORT-1",
            "GT-1", "B-28 slip", "FRAY-1", "MT-1c"]
    miss = [t for t in must if t not in reg]
    msgs.append(f"register rows for the ticket's gates: {'all present' if not miss else 'MISSING ' + str(miss)}")
    rel = [r["id"] for r in csv.DictReader(open(ROOT / REL, encoding="utf-8"))]
    unreg = [t for t in rel if t not in reg and not t.startswith("ALT-")]
    msgs.append(f"release_tests.csv ids without a register row (ALT-* are alternate-set checks): {unreg or 'none'}")
    active = [t for t, r in reg.items() if r["status"].startswith(("ACTIVE", "PROPOSED"))]
    placed = {o["test"] for o in ow}
    msgs.append(f"active tests not in the order of work: {sorted(set(active) - placed) or 'none'}")
    first = {}
    for o in ow:
        if o["stage"] == "run":
            first.setdefault(o["release"], o["seq"])
    msgs.append(f"first run per release: {first}")
    msgs.append(f"CA-1 release level {lv['release']} (cycled {lv['release_cycled']})")
    msgs.append(f"shopping list {len(sh)} lines, USD {sum(x['total_usd'] for x in sh):,.2f}; long lead: "
                f"{sum(1 for x in sh if x['long_lead'])}")
    msgs.append(f"results template {len(res)} rows, {len({r['test_id'] for r in res})} tests")
    return msgs


def build(write: bool = True) -> dict:
    lv = release_levels()
    lid_g = lid_mass_g()
    cut = crown_cut_mm()
    rows = update_register(lv, lid_g, cut, write=write)
    reg = {r["id"]: r for r in rows}
    rk = ranking(reg)
    update_test_plan(rk, lv, write=write)
    ow = order_of_work(reg)
    res = results_rows(reg, ow, lv, lid_g, cut)
    sh = shopping(reg)
    out = {"levels": lv, "lid_g": lid_g, "cut": cut, "register": reg, "ranking": rk, "order": ow, "results": res,
           "shopping": sh, "checks": checks(reg, ow, sh, res, lv)}
    if not write:
        return out
    OUT.mkdir(parents=True, exist_ok=True)
    _csv(OUT / "order_of_work.csv", ow)
    _csv(OUT / "shopping_list.csv", sh)
    _w(OUT / "shopping_list.md", shopping_md(sh))
    from huntkit.manufacturing.test_results import COLUMNS
    _csv(OUT / "results_template.csv", res, COLUMNS)
    lds = loads(lv)
    GUIDE_STEPS["CA-1"] = _ca1_steps(lv)
    gfiles = []
    for gr in GROUPS:
        p = OUT / "guides" / f"{gr['id']}.md"
        _w(p, guide_md(gr, reg, lv, lds, res, ow))
        gfiles.append(p)
    _w(OUT / "README.md", readme_md(ow, sh, lv, rk, reg, res))
    sk = sketches(OUT / "sketches")
    ch = charts(ow, sh, lv, rk, OUT / "sketches")
    pp = pdf(OUT, [OUT / "README.md", OUT / "shopping_list.md"] + gfiles, ch)
    shots = screenshots(pp, [ch[0], ch[1], ch[2], sk[0], sk[1]])
    man = {"ticket": "BL-038", "date": DATE, "levels": lv, "lid_g": lid_g, "crown_cut": cut,
           "totals": {"usd": round(sum(x["total_usd"] for x in sh), 2),
                      "hands_on_h": round(sum(o["hands_on_h"] for o in ow), 1),
                      "machine_h": round(sum(o["machine_h"] for o in ow), 1),
                      "results_rows": len(res)},
           "files": sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file() and "preview" not in p.parts),
           "screens": [str(p.relative_to(ROOT)) for p in shots], "checks": out["checks"]}
    _w(OUT / "manifest.json", json.dumps(man, indent=1))
    out["screens"] = shots
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="build in memory, print the checks, write nothing")
    a = ap.parse_args(argv)
    out = build(write=not a.check)
    for m in out["checks"]:
        print("-", m)
    for p in out.get("screens", []):
        print("screen:", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
