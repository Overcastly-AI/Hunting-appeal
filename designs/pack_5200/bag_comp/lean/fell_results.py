"""Collect FELL's numbers into result.json (Team B LEAN). Run after fell_clothsim.py and the renders.

    python designs/pack_5200/bag_comp/lean/fell_results.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import fell as F  # noqa: E402

SIM = ROOT / "outputs" / "clothsim"
TORSOS = (15, 19, 23)
SCREENS = [f"outputs/screens/20261110_bagB_{i}.png" for i in range(1, 6)]


def sims() -> dict:
    out = {}
    for t in TORSOS:
        d = json.loads((SIM / f"fell_PR{t}" / "results.json").read_text())
        row = {}
        for c in ("packed", "fill", "meat"):
            r = d["cases"][c]
            v = r["volume"]
            row[c] = {"converged": bool(r["converged"]), "rounding_mm": r.get("contact_rounding_mm"),
                      "closed_L": round(v["closed_L"], 1), "contents_cg_mm": [round(x, 1) for x in v["contents_cg_mm"]],
                      "cg_with_external_mm": [round(x, 1) for x in v.get("cg_with_external_mm", v["contents_cg_mm"])],
                      "e_max_pct": round(max(p["e_max_pct"] for p in r["pieces"].values()), 1),
                      "seam": r["seam_critical"]["seam"], "seam_n_mm": round(r["seam_critical"]["max_n_mm"], 2),
                      "seam_sf": round(r["seam_critical"]["sf"], 1)}
        out[t] = row
    return out


def corrie_sims() -> dict:
    out = {}
    for t in TORSOS:
        d = json.loads((SIM / f"corrie_PR{t}c" / "results.json").read_text())
        out[t] = {c: {"closed_L": round(d["cases"][c]["volume"]["closed_L"], 1),
                      "cg_with_external_mm": [round(x, 1) for x in d["cases"][c]["volume"].get(
                          "cg_with_external_mm", d["cases"][c]["volume"]["contents_cg_mm"])],
                      "rounding_mm": d["cases"][c].get("contact_rounding_mm")} for c in ("fill", "meat")}
    return out


def loadout(s: dict) -> dict:
    """FELL loadout check with FELL's own sim peel and volume (corrie_loadout's model, zones from fell_loadout)."""
    import corrie_loadout as CL
    import fell_loadout as FL
    CL.SIM_FILL_L = tuple(s[t]["fill"]["closed_L"] for t in TORSOS)
    CL.SIM_FILL_CG = {t: s[t]["fill"]["contents_cg_mm"][1] for t in TORSOS}
    CL.SIM_MEAT_CG = {t: s[t]["meat"]["contents_cg_mm"][1] for t in TORSOS}
    mk = CL.CO.make
    CL.CO.make = lambda *a, **k: F.make()          # the column model on FELL's (3 % shallower) shell
    CL.G = CL.corrie_geom()
    CL.CO.make = mk
    CL._MEAT_PEEL.clear()
    res = FL.run()
    (ROOT / "outputs" / "loadout" / "fell_loadout_results.json").write_text(json.dumps(res, indent=1, default=CL._json))
    worst = max(v["cg_y_rev_c_15in"] for k, v in res.items() if not k.endswith("_meat"))
    worst_m = max(v["cg_y_rev_c_15in"] for k, v in res.items() if k.endswith("_meat"))
    return {"misses_M": FL.misses(res, "M"), "misses_S": FL.misses(res, "S"), "misses_XL": FL.misses(res, "XL"),
            "worst_loadout_cg_15in": worst, "worst_packout_cg_15in": worst_m,
            "geometry": {"v_sewn_L": CL.G["v_sewn"], "bulge": round(CL.G["kb"], 3)}}


def main():
    s = sims()
    cmp = F.comparison()
    mx = cmp["max"]
    cor = cmp["corrie_b2"]
    lo = loadout(s)
    vol = float(np.mean([s[t]["fill"]["closed_L"] for t in TORSOS]))
    v = F.volumes()
    res = {
        "team": "B",
        "name": "FELL (LEAN)",
        "one_line": ("CORRIE's sim-proven box shell, 3 % shallower, in ULTRAGrid / 70D / ULTRA 200X: roll-top first, one "
                     "straight 540 mm #10 zip, W1-W3 as compression, and G-hook add-on pods on 8 seam hard points "
                     "that only go on when the loadout needs them."),
        "bag_system_g": mx["total_g"],
        "bag_system_g_by_config": {k: cv["total_g"] for k, cv in cmp["configs"].items()},
        "corrie_b2_bag_system_g": cor["total_g"],
        "pack_mass_M_g": round(F.H1_PACK_M - cor["total_g"] + mx["total_g"], 1),
        "pack_mass_M_note": (f"3943 - {cor['total_g']} (CORRIE B.2 bag system, same code: body group + IMP-1/2/4/8 + "
                             f"re-cut fly + fly pocket) + {mx['total_g']} (FELL, max config: all 4 add-ons). Day config "
                             f"{cmp['configs']['day']['pack_M_on_H1_g']} g."),
        "volume_L": round(vol, 1),
        "volume_note": "cloth sim fill case (68 kg), mean of 15/19/23 in; lid pod 2.7 L extra, not counted",
        "fill_height_in": v["fill_height_in"],
        "pieces": mx["pieces"],
        "curved_seams": mx["curved_seams"],
        "zip_mm_total": mx["zip_mm"],
        "beginner_hours": mx["hours"],
        "cg_fill_mm": {str(t): s[t]["fill"]["cg_with_external_mm"][1] for t in TORSOS},
        "cg_meat_mm": {str(t): s[t]["meat"]["cg_with_external_mm"][1] for t in TORSOS},
        "cg_method": "clothsim",
        "cg_note": ("coarse (h 40 mm) cloth sims fell_PR15/19/23 on corrie_PR*c settings, with the 1 kg lid pod on the "
                    "roll and the 85 mm spotter on the left side (mass-weighted CG incl. both). Rounding stage per "
                    "case in analysis/bag_comp_lean.md; add <= 4 mm for rounding bias."),
        "access_misses": {k: len(m["all"]) for k, m in lo["misses_M"].items()},
        "access_misses_detail_M": lo["misses_M"],
        "features": [
            "Roll-top main closure (70D collar, ULTRAGrid hem, ULTRA 200 frame-side strip under the hood ladders)",
            "One straight #10 coil zip, 540 mm, z 110-650 in the aft centre seam: IM1-IM3 and low gear; 1 slider, camo garage",
            "No wings: W1/W2 haul wraps do the carry compression (their documented carry-mode job); unhook to open the zip",
            "8 hard-point webbing loops in the corner seams (z 260 / 490) for G-hook add-ons",
            "A1 glass pod: padded 85 mm spotter sleeve on its own panel, cinches like a wing (left)",
            "A2 side strap pair: tripod / poles / jacket, tripod feet in the cam cup (right)",
            "A3 lid pod 2.7 L on the roll (optional)",
            "A4 strap pod (snacks / GPS) on the right J-strap: fixes CORRIE's S-L snack miss",
            "Hydration sleeve (CORRIE IMP-2 geometry, 70D) + hose ports; cam / tripod-foot cup; fly in the base pocket",
            "Owner camo: V-notch kick band, pod leading-edge bar, zip garage, lid-pod tab, strap-pod binding",
            "Frame interface unchanged (hood B-19, B-20, B-22, IM hooks, hinge pins, B-24, US1/US2, IM1-IM3, fairleads)"],
        "risks": [
            "Fabric gates: ULTRAGrid needs the owner's swatch approval (visible grid); ULTRA 200X floor needs PT-3 + a "
            "50 mm strip test (strip strength unpublished); 70D collar: weigh the Robic stock first",
            "Durability: ULTRAGrid only matches 330D on abrasion (Taber 1100 vs ~950-1070) and is ~55-60 % of 500D; "
            "the 70D collar tears at 37-52 N; this is a lighter, not a tougher, bag",
            "Noise: ULTRA 200X floor is a film laminate (quietness 2/5 in the record); the floor rarely brushes "
            "vegetation, but it can crinkle when set down or packed",
            "Access: a straight slit opens narrower than CORRIE's horseshoe, and W1/W2 must be unhooked to open it "
            "(two G-hooks); no door pocket: the kill kit packs mid-aft behind the zip (packing rule)",
            "Modules only save weight if they stay home; with every add-on fitted FELL saves 133 g, not the 271 g of the day config",
            "Sheep 8-day: 1 hourly miss (2nd bottle) and glassing misses (poles, beanie, first aid light) because "
            "there is no door pocket and the side straps are full",
            "G-hook add-ons can be lost in the field; spare G-hooks are cheap but are one more thing",
            "Coarse-mesh CG (h 40 mm); 3 % shallower shell not yet checked against the hood / B-20 fit on a prototype"],
        "screenshots": SCREENS,
        "sims": {str(t): s[t] for t in TORSOS},
        "corrie_sims": {str(t): x for t, x in corrie_sims().items()},
        "loadout": lo,
    }
    (HERE / "result.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("bag_system_g", "bag_system_g_by_config", "corrie_b2_bag_system_g",
                                          "pack_mass_M_g", "volume_L", "fill_height_in", "pieces", "curved_seams",
                                          "zip_mm_total", "beginner_hours", "cg_fill_mm", "cg_meat_mm",
                                          "access_misses")}, indent=1, default=float))
    print(json.dumps(res["sims"], indent=0, default=float)[:3000])
    print(lo)


if __name__ == "__main__":
    main()
