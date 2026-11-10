"""Write designs/pack_5200/bag_comp/form/result.json (RULES.md schema) from the CHERT computations:
form_numbers.json (form.py), loadout.json (form_loadout.py) and the cloth sims (form_sim.cg_table).

    python designs/pack_5200/bag_comp/form/form_result.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import form_sim as FS  # noqa: E402

H1_PACK_G = 3943.0          # RULES.md: CORRIE B.2 pack at belt M on the H1 frame
SCREENS = [f"outputs/screens/20261110_bagE_{n}.png" for n in range(1, 7)]


def main():
    n = json.loads((HERE / "form_numbers.json").read_text())
    lo = json.loads((HERE / "loadout.json").read_text())
    t = FS.cg_table()
    sys_g = n["mass"]["bag_system_g"]
    corrie_g = n["mass"]["corrie_bag_system_g"]
    vols = [v for k, v in t["volume_L"].items() if k.startswith("fill_")]
    method = "clothsim" if len(t["fill"]) == 3 and len(t["meat"]) == 3 else "estimate"
    r = {
        "team": "E",
        "name": "CHERT",
        "one_line": "Chamfer-blade box: tapered camo blades cut the two aft corners and carry the door zip in their seam, "
                    "so panel line = camo break = door; solid two-tone body, roll-top, CORRIE B.2 wings/pouch/pockets",
        "bag_system_g": sys_g,
        "corrie_b2_bag_system_g": corrie_g,
        "corrie_b2_bag_system_basis": "corrie.build() body group 533.1 + IMP-1/2/4/6/8 + fly F-01 x G-2 shell ratio "
                                      "(form.corrie_parts_g)",
        "pack_mass_M_g": round(H1_PACK_G - corrie_g + sys_g, 1),
        "volume_L": round(sum(vols) / len(vols), 1) if vols else n["rule_volume_L"],
        "volume_basis": "cloth-sim fill case, closed to the fill line, mean of 15/19/23 in (pouch, wings, pockets not "
                        "counted); design-rule volume " + f"{n['rule_volume_L']} L",
        "fill_height_in": n["fill_height_in"],
        "pieces": n["build"]["pieces"],
        "curved_seams": n["build"]["curved_seams"],
        "zip_mm_total": n["build"]["zip_mm_total"],
        "beginner_hours": n["build"]["beginner_hours"],
        "cg_fill_mm": t["fill"],
        "cg_meat_mm": t["meat"],
        "cg_method": method,
        "cg_notes": {"rounding_mm": t["rounding_mm"], "converged": t["converged"], "cg_z_mm": t["cg_z"],
                     "limits": "HA-LS-1 rev C: fill <= 205, meat <= 190 (y, mm, mass-weighted with 1 kg pouch + 85 mm "
                               "spotter); rounding > 0 reads up to +4 mm (corrie_body.md 11.4)"},
        "access_misses": lo["misses_M"],
        "access_misses_detail_M": {k: v["fails"] for k, v in lo["by_size"]["M"].items()},
        "features": [
            "Chamfer blades: the two aft vertical corners cut by a camo facet tapering 60 x 55 mm (floor) to 32 x 26 mm "
            "(collar seam); one camo U piece (blades + kick strip), creased not seamed",
            "Door zip in the blade | aft-face seam (#10 coil, 2 sliders, 1.23 m): the camo break, the panel line and the "
            "door are one line; door = the whole aft face z 110-650",
            "Fang insets (camo) low on each gusset, one straight seam, joining the blades into a wrap-round lower corner",
            "Two-tone solid blocking: olive faces, dark collar + hinge band + roll, camo only on the outline (disruptive "
            "edge placement, docs/research/bag_comp_form.md)",
            "Hexagon boxed floor carries the chamfer into the base",
            "IMP-6R right-strap snack / GPS stretch pocket (fixes the snack miss on S-L belts)",
            "CORRIE B.2 kept: roll-top, 2.7 L pouch, wings with tripod right and scope sleeve left, hipbelt pockets, "
            "holster, hydration sleeve, door pocket, frame interface, rain fly",
            "Uniform-fill CG 0.7 mm forward of CORRIE at a taller body (chamfers remove aft-corner volume)",
        ],
        "risks": [
            "15 in meat CG 187.4 mm (limit 190, margin 2.6; reported at 1 mm contact rounding, so <= ~188 raw): tighter "
            "than CORRIE's 184.4 because the body is 36 mm taller to hold 85 L after the chamfers; prototype plumb CG "
            "check at 15 in with 30 kg on IM1-IM3 is mandatory",
            "Door is narrower at the bottom: 163 mm at z 110 vs CORRIE 198 mm (wider at the top: 320 vs 304 mm)",
            "The #10 door zip sits on a fold (blade | door seam at the chamfer crease): untested; it needs the loaded zip "
            "test and a sewing jig/notches so a beginner sets the zip straight before the facet folds",
            "Camo blade U and fangs in 630D printable (290 g/m2) are stiffer and heavier than 330D; the sim models them as "
            "330D (ASSUMPTION). The U-shaped cut wastes its centre on the marker unless the fangs and tabs nest there",
            "Mass +17.6 g vs CORRIE B.2: shell +4.8 g (taller body, 630D camo blade U + fangs replacing the kick appliques), collar -3.2, door zip -0.5, fly -0.4, and the 17 g IMP-6R snack pocket (ASSUMPTION mass)",
            "Access at belt M: sheep 8-day still misses bottle #2 (hourly) and beanie/gloves + poles at glassing (they "
            "end up above the z 650 door hinge in the taller body); day hunt kill kit is the CORRIE packing-order artifact",
            "Fill line 41.6 in above the floor (CORRIE 40.2): roll-top 36 mm higher, check prone/head-tilt clearance",
            "Wings, pouch, roll, tripod and pockets are placed render geometry on the simulated body (as CORRIE); "
            "the float-mode render bakes the 170 mm shift because the Cycles port does not apply it",
            "Name CHERT and the chamfer-zip construction got a short search only, not a trademark or FTO clearance",
        ],
        "screenshots": SCREENS,
    }
    (HERE / "result.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
