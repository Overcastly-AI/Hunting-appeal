"""Team A EVOLVE: assemble designs/pack_5200/bag_comp/A/result.json from the code and the run outputs.

    python designs/pack_5200/bag_comp/A/make_result.py

Sources: evolve.system() (mass, pieces, seams, zips, hours, volume rule), the CORRIE E cloth sims
outputs/clothsim/bagA_evolve_PR{15,19,23}/results.json (sewn volume, mass-weighted CG with the pouch + spotter, seam
forces), evolve_loadout.run() (access misses on every loadout x belt size).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evolve as E  # noqa: E402

SIM = E.ROOT / "outputs" / "clothsim"
H1_PACK_M_G = 3943.0            # RULES.md: CORRIE B.2 on H1 at belt M (~3943 g)
SCREENS = [f"outputs/screens/20261110_bagA_{n}.png" for n in range(1, 6)]


def sims():
    out = {}
    for t in (15, 19, 23):
        f = SIM / f"bagA_evolve_PR{t}" / "results.json"
        r = json.loads(f.read_text())["cases"]
        out[str(t)] = {k: {"converged": v["converged"], "closed_L": v["volume"]["closed_L"],
                           "cg_y": (v["volume"].get("cg_with_external_mm") or v["volume"]["contents_cg_mm"])[1],
                           "cg_z": (v["volume"].get("cg_with_external_mm") or v["volume"]["contents_cg_mm"])[2],
                           "rounding_mm": v.get("contact_rounding_mm"), "residual_n": v["solve"][-1]["residual_n"],
                           "seam": v["seam_critical"]["seam"], "seam_n_mm": v["seam_critical"]["max_n_mm"],
                           "seam_sf": v["seam_critical"]["sf"],
                           "side_floor_seam_n_mm": max((s["max_n_mm"] for k, s in v["seams"].items()
                                                        if k.startswith("B-03") and "B-05" in k), default=None)}
                       for k, v in r.items()}
    return out


def corrie_sims():
    out = {}
    for t in (15, 19, 23):
        r = json.loads((SIM / f"corrie_PR{t}c" / "results.json").read_text())["cases"]
        out[str(t)] = {k: {"closed_L": v["volume"]["closed_L"],
                           "cg_y": (v["volume"].get("cg_with_external_mm") or v["volume"]["contents_cg_mm"])[1],
                           "seam": v["seam_critical"]["seam"], "seam_n_mm": v["seam_critical"]["max_n_mm"],
                           "side_floor_seam_n_mm": max((s["max_n_mm"] for k, s in v["seams"].items()
                                                        if k.startswith("B-03") and "B-05" in k), default=None)}
                       for k, v in r.items() if k in ("fill", "meat")}
    return out


def main():
    import evolve_loadout as LO
    s = E.system()
    sm = sims()
    lo = LO.run()
    miss = LO.summarize_misses(lo)
    n_miss = {k: sum(len(v) for v in per.values()) for k, per in miss.items()}
    e = s["corrie_e"]
    vol = s["volume"]
    fill_L = [sm[t]["fill"]["closed_L"] for t in sm]
    res = {
        "team": "A",
        "name": E.NAME,
        "one_line": "CORRIE evolved: rounded aft corners, shoulder taper, wider base, one-layer camo tub base, "
                    "forward hip-reach pockets on the wings and a pole quiver; zero access misses on every belt",
        "bag_system_g": e["bag_system_g"],
        "pack_mass_M_g": round(H1_PACK_M_G - s["corrie_b2"]["bag_system_g"] + e["bag_system_g"], 1),
        "pack_mass_basis": f"3943 - {s['corrie_b2']['bag_system_g']} (CORRIE B.2 bag system, same code: body build + "
                           f"IMP-1/2/4/8 + fly) + {e['bag_system_g']}",
        "corrie_b2_bag_system_g": s["corrie_b2"]["bag_system_g"],
        "volume_L": round(sum(fill_L) / len(fill_L), 1),
        "volume_basis": "cloth sim, fill case (68 kg), mean of 15/19/23 in, main bag to the fill line; pouch 2.7 L "
                        "and the hip-reach pockets NOT counted; per torso " + ", ".join(f"{x:.1f}" for x in fill_L),
        "fill_height_in": vol["fill_height_in"],
        "pieces": e["pieces"],
        "curved_seams": e["curved_seams"],
        "zip_mm_total": e["zip_mm"],
        "beginner_hours": e["hours"],
        "cg_fill_mm": {t: round(sm[t]["fill"]["cg_y"], 1) for t in sm},
        "cg_meat_mm": {t: round(sm[t]["meat"]["cg_y"], 1) for t in sm},
        "cg_method": "clothsim",
        "cg_converged": {t: {k: sm[t][k]["converged"] for k in ("fill", "meat")} for t in sm},
        "access_misses": n_miss,
        "access_miss_detail": miss,
        "features": [
            "E-1 rounded aft corners R 40: the door wraps the corners, clear width 294/311/334 mm at IM1/IM2/IM3 "
            "(CORRIE 214/242/281)",
            "E-2 shoulder taper 394 -> 370 mm into the roll",
            "E-3 camo tub wall (60 mm, printed 500D) replaces the two-layer chevron kick plate and lifts the "
            "side | floor seam off the bulge corner",
            "E-4 hip-reach pockets on both wings (power mesh, camo mouth band): snacks + GPS left, 2nd bottle right",
            "E-5 pole quiver: boot in the right pocket's pleat + shock-cord grip loop",
            "E-7 wider base (320 mm) keeps the collar at z 736.3",
            "kept from CORRIE B.2: horseshoe #10 door, side compression wings, 2.7 L pouch, IMP-1/2/4/8, frame "
            "interface unchanged",
        ],
        "risks": [],
        "screenshots": SCREENS,
    }
    (HERE / "result.json").write_text(json.dumps(res, indent=1, default=float))
    (HERE / "result_detail.json").write_text(json.dumps({"system": s, "sims": sm, "corrie_sims": corrie_sims(),
                                                        "loadout_cg_worst": lo["loadout_cg_worst"],
                                                        "loadout_geometry": lo["geometry"],
                                                        "all_fails": lo.get("all_fails")}, indent=1, default=float))
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
