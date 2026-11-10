"""Write designs/pack_5200/bag_comp/D/result.json (RULES.md section 5) from the CACHE model, the cloth-sim runs
(outputs/clothsim/bagD_cache_PR{15,19,23}/results.json) and the loadout check.

    python designs/pack_5200/bag_comp/D/result.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

import cache as C  # noqa: E402
import cache_loadout as LO  # noqa: E402

SIM = ROOT / "outputs" / "clothsim"
SCREENS = [f"outputs/screens/20261110_bagD_{n}.png" for n in range(1, 6)]


def sim_cg() -> dict:
    out = {"fill": {}, "meat": {}, "volume_L": {}, "runs": {}}
    for t in (15, 19, 23):
        d = json.loads((SIM / f"bagD_cache_PR{t}" / "results.json").read_text())
        for case in ("fill", "meat"):
            r = d["cases"][case]
            v = r["volume"]
            out[case][str(t)] = round(float(v["cg_with_external_mm"][1]), 1)
            out["runs"][f"{t}_{case}"] = {"converged": r["converged"], "rounding_mm": r.get("contact_rounding_mm"),
                                          "closed_L": v["closed_L"], "cg_mm": v["cg_with_external_mm"],
                                          "residual_n": r["solve"][-1]["residual_n"],
                                          "seam": r["seam_critical"]["seam"],
                                          "seam_n_mm": round(r["seam_critical"]["max_n_mm"], 2),
                                          "seam_sf": round(r["seam_critical"]["sf"], 1)}
        out["volume_L"][str(t)] = d["cases"]["fill"]["volume"]["closed_L"]
    return out


def build() -> dict:
    s = C.system()
    cg = sim_cg()
    lo = LO.run()
    miss = LO.misses(lo, "M")
    vol = round(sum(cg["volume_L"].values()) / 3, 1)
    return {
        "team": "D",
        "name": C.NAME,
        "one_line": ("Light CORRIE-derived shell with a drawcord collar under a lid; three removable roll-top modules "
                     "and two hook-on side pods; the frame-zone SWAP slab carries the sleep kit and becomes the "
                     "wipeable meat liner under IM1-IM3 on a pack-out."),
        "bag_system_g": s["bag_system_g"],
        "pack_mass_M_g": C.pack_mass_M(s),
        "corrie_b2_bag_system_g_used": s["corrie_b2"]["total_g"],
        "pack_mass_note": (f"3943 - {s['corrie_b2']['total_g']} + {s['bag_system_g']} (CORRIE B.2 counted by the same "
                           "metric in cache.corrie_b2_system(): body group, roll-top hardware, keeper loops, IMP-1/2/4/8, "
                           "haul wraps, fly; IMP-6/IMP-3/IMP-5 and the fixed interface are out on both sides)"),
        "bag_system_without_modules_g": round(s["bag_system_g"] - sum(m["mass_g"] for m in s["modules"]
                                                                      if m["id"] in ("MS", "MC", "MK")), 1),
        "volume_L": vol,
        "volume_note": ("cloth-sim closed volume of the fill case, mean of 15/19/23 in (CORRIE rev B shell, 85.2 L "
                        "design number by the same R-01 basis as CORRIE); modules hold "
                        + " + ".join(f"{m['vol_L']}" for m in s["modules"] if m["id"] != "ML") + " L inside it; the "
                        "LID module (2.7 L) and the pods ride outside and are not counted"),
        "fill_height_in": s["fill_height_in"],
        "pieces": s["pieces"],
        "curved_seams": s["curved_seams"],
        "zip_mm_total": s["zip_mm_total"],
        "beginner_hours": s["beginner_hours"],
        "cg_fill_mm": cg["fill"],
        "cg_meat_mm": cg["meat"],
        "cg_method": "clothsim",
        "cg_note": ("mass-weighted CG y incl. the lid module (1.08 kg) and the optics pod with an 85 mm spotter "
                    "(1.99 kg), coarse h 40 mm, all 6 cases converged; read +<=4 mm for the contact-rounding bias"),
        "access_misses": {k: len(v) for k, v in miss.items()},
        "access_miss_items": miss,
        "features": [
            "SWAP slab module: sleep kit in camp, emptied and re-used as the wipeable meat liner under IM1-IM3",
            "IM1-IM3 double as internal compression: they cinch the modules flat against the frame on small loads",
            "Modules slide out through CORRIE's #10 horseshoe door like drawers (CAMP), KILL module at the sill",
            "Drawcord collar + LID module (2.7 L) replace the roll-top; LID front straps are the top compression",
            "Optics pod (85 mm spotter) and tripod kit hook on with G-hooks to the old wing loops; leave them home",
            "SP snack pocket on the right shoulder strap: snacks reachable pack-on on every belt size",
            "Quiet: modules close by roll + G-hook (no buckle clack), no hook-and-loop, coil zips only",
            "Frame interface, IM straps, under-straps, hood, guys, hinge eyes, fly pocket: unchanged from CORRIE",
        ],
        "risks": [
            f"Heavier than CORRIE B.2 by {s['delta_vs_corrie_g']} g as counted (the 3 modules are "
            f"{round(sum(m['mass_g'] for m in s['modules'] if m['id'] in ('MS', 'MC', 'MK')), 1)} g); lighter only "
            "if the hunter leaves stuff sacks home",
            "Shell = CORRIE rev B shell: the cloth sim is effectively a re-run, not a new body; 15 in meat CG margin "
            "is 7.9 mm (>= 3.9 mm with the rounding bias)",
            "No roll-top: the cinched collar is not waterproof; relies on the lid, the fly and the dry-bag modules",
            "Module walls and corners cost usable volume (fill efficiency 0.90 -> 0.86 ASSUMPTION)",
            "Silpoly modules on bone ends / brush: no abrasion data; SWAP frame face + floor in 70D (test MOD-2)",
            "Sheep loadout: GPS (S-L belts) and the 2nd bottle still miss pack-on access; rain shell rides in the bag",
            "Kill-site sequencing: the sleep kit has to go somewhere while the slab becomes the liner (aft column)",
            "Snack pocket and lid straps were not drawn in every render; the pod cinch straps are drawn simplified",
        ],
        "screenshots": SCREENS,
    }


if __name__ == "__main__":
    r = build()
    (HERE / "result.json").write_text(json.dumps(r, indent=1))
    print(json.dumps({k: r[k] for k in r if k not in ("features", "risks")}, indent=1))
