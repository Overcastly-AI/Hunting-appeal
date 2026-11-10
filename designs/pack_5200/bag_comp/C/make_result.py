"""Collect TAILGATE's numbers (tailgate.py), cloth sims (outputs/clothsim/bagC_tg_PR*), loadout check
(outputs/bag_comp_C/loadout_C.json) and screenshots into designs/pack_5200/bag_comp/C/result.json, and print the
tables used in designs/pack_5200/analysis/bag_comp_C.md.

    python designs/pack_5200/bag_comp/C/make_result.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import tailgate as TG  # noqa: E402

SIM = ROOT / "outputs" / "clothsim"
SCREENS = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "outputs" / "screens").glob("20261110_bagC_*.png"))
CORRIE_C = {"fill": {"15": 191.3, "19": 172.4, "23": 131.2}, "meat": {"15": 184.4, "19": 167.2, "23": 134.1}}


def sims():
    out = {}
    for t in (15, 19, 23):
        r = json.loads((SIM / f"bagC_tg_PR{t}" / "results.json").read_text())
        row = {}
        for c in ("packed", "fill", "meat"):
            x = r["cases"][c]
            v = x["volume"]
            row[c] = {"converged": x["converged"], "rounding_mm": x.get("contact_rounding_mm"),
                      "residual_n": x["solve"][-1]["residual_n"] if x["solve"] else None,
                      "closed_L": v["closed_L"], "cg_contents": v["contents_cg_mm"],
                      "cg_ext": v.get("cg_with_external_mm") or v["contents_cg_mm"],
                      "critical": x["seam_critical"]["seam"], "crit_n_mm": x["seam_critical"]["max_n_mm"],
                      "crit_sf": x["seam_critical"]["sf"]}
        out[str(t)] = row
    return out


def main():
    n = TG.numbers()
    S = sims()
    on = json.loads((SIM / "bagC_tg_PR15" / "results.json").read_text())
    off = json.loads((SIM / "bagC_tg_PR15_nostraps" / "results.json").read_text())
    hoop = TG.hoop_check(on, off)
    lo = json.loads((ROOT / "outputs" / "bag_comp_C" / "loadout_C.json").read_text())["cases"]
    misses = {k: lo[f"{k}_rifle_M"]["hourly_misses"] for k in ("day", "elk6", "sheep8")}
    misses_all = {k: v["hourly_misses"] for k, v in lo.items() if not k.endswith("_meat")}
    cg_fill = {t: round(S[t]["fill"]["cg_ext"][1], 1) for t in S}
    cg_meat = {t: round(S[t]["meat"]["cg_ext"][1], 1) for t in S}
    vol = round(sum(S[t]["fill"]["closed_L"] for t in S) / 3, 1)
    res = {
        "team": "C (OPEN)",
        "name": "TAILGATE",
        "one_line": ("Full-face lid hinged at the floor seam: the whole aft face drops like a tailgate (floor to z 650, "
                     "full width); 3 lid straps at the IM heights close the lid before the #10 zip does (the sim puts <= 0.45 "
                     "N/mm on the zip, SF 79); roll-top, pouch and the whole frame interface as CORRIE B.2."),
        "bag_system_g": n["bag_system"]["total_g"],
        "pack_mass_M_g": n["pack_mass_M_g"],
        "corrie_b2_bag_system_g_used": n["corrie_b2_bag_system"]["total_g"],
        "mass_note": ("bag_system = body group (bag_concepts.metrics: shell, collar, swells, accents, straps, pouch, zips, "
                      "hardware) + bag pockets IMP-1/2/4/8 (+ IMP-C1 strap sleeve for TAILGATE) + fly F-01 scaled to "
                      "the outer shell. CORRIE B.2 by the same definition: "
                      f"{n['corrie_b2_bag_system']['total_g']} g; pack_mass_M_g = 3943 - that + TAILGATE's."),
        "volume_L": vol,
        "volume_note": ("cloth-sim closed volume, fill case, mean of 15/19/23 in (the flat-panel rule gives "
                        f"{n['volume_L_rule']} L for this box, as CORRIE rev B); pouch 2.7 L not counted"),
        "fill_height_in": n["fill_height_in"],
        "pieces": n["pieces"], "curved_seams": n["curved_seams"], "zip_mm_total": n["zip_mm_total"],
        "beginner_hours": n["beginner_hours"],
        "cg_fill_mm": cg_fill, "cg_meat_mm": cg_meat, "cg_method": "clothsim",
        "cg_note": ("mass-weighted CG y incl. the 1 kg pouch and the 85 mm spotter, coarse h 40 runs "
                    "bagC_tg_PR{15,19,23}; reported at contact rounding 3-6 mm, read +4 mm for the rounding bias "
                    "(corrie_body.md 11.4)"),
        "access_misses": {k: len(v) for k, v in misses.items()},
        "access_miss_items_M": misses,
        "features": [
            "Tailgate lid: one 330D panel, the whole aft face, hinged on a sewn floor seam (no zip at the floor)",
            "Opening 0.229 m2 vs CORRIE's door 0.153 m2; clear width 286/314/353 mm at IM1/IM2/IM3, 254 mm at the floor, no sill",
            "#10 coil inverted-U zip (1.59 m) in the aft corner seams, 2 sliders parked closed under a top-right camo garage, zip feet in 500D boots",
            "Lid straps H1-H3 at z 190/330/520 (the IM heights), gusset loop to gusset loop over the zip: cinch first, zip second, so the slider never clamps a full bag",
            "Camo storm flaps over both zip legs frame the lid (owner camo as the accent edge); 330D flap on the top run",
            "No wings: 2 side straps a side (tripod right with the IMP-8 cup, pad/decoy left), IMP-1 spotter sleeve sewn to the left gusset",
            "IMP-4 kill kit on the inside of the lid: it comes to you when the lid drops",
            "IMP-C1 snack/GPS stretch sleeve on the right J-strap: snacks reachable pack-on on every belt size",
            "Roll-top, 2.7 L pouch, hood B-19, B-20/B-22, IM1-IM3, hinge pins, B-24 float, US1/US2, fly: CORRIE B.2 unchanged",
        ],
        "risks": [
            "Heavier than CORRIE B.2 by %.0f g (bag system), mostly the 0.33 m longer zip, the lid straps and the flaps" %
            (n["bag_system"]["total_g"] - n["corrie_b2_bag_system"]["total_g"]),
            "15 in meat CG %.1f mm vs 190 (margin %.1f before, %.1f after the +4 mm rounding bias): as marginal as CORRIE" %
            (cg_meat["15"], 190 - cg_meat["15"], 186 - cg_meat["15"]),
            "To open the lid, 3 G-hooks must be unhooked first (side carry stays put); a user who zips first and cinches second loads the zip",
            "Zip legs sit on the box's aft corners, the most abraded line in brush: covered by the flaps, but a flap that rides up exposes the coil",
            "The cloth sim models the zip as a closed seam and the R60 top corners as square; the lid straps are anchored on the frame plane, not on the gusset loops",
            "With the lid down on a mannequin or a slope, the lid hangs into dirt / blood: needs the user habit of laying the pack frame-down first",
            "Sheep 8-day: the 2nd 1 L bottle still rides in the bag (one holster)",
            "Zip crosswise strength is a record ESTIMATE (900 N/in); get the YKK sheet. Patent search for a floor-hinged lid not done",
        ],
        "screenshots": SCREENS,
        "hoop": hoop,
        "sims": S,
        "access_misses_all_belts": misses_all,
    }
    (HERE / "result.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: v for k, v in res.items() if k not in ("sims", "hoop", "access_misses_all_belts")}, indent=1,
                     default=float))
    print(json.dumps(hoop, indent=1, default=float))
    for t, row in S.items():
        for c, x in row.items():
            print(t, c, x)


if __name__ == "__main__":
    main()
