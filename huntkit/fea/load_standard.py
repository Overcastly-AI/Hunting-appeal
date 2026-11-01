"""HA-LS-1: the calibrated Pack 5200 frame load standard ("match the leaders", owner 2026-11-01).

Full rationale, sources and the physical test plan are in designs/pack_5200/analysis/load_standard.md.
This module is the executable form: the load cases, the factor per case, and the acceptance rules the
sizing (huntkit.fea.sizing5200, standard="ls1") applies.

Structure (aerospace limit/ultimate logic, applied to a pack):
- LIMIT load = the largest load expected in service (rated 68 kg x a realistic g-factor).
  Requirement: no yield / no first-ply failure at FACTOR x limit, with the composite allowables
  still knocked down (hot/wet 0.8, impact 0.65 on compression; huntkit.fea.composite).
- ULTIMATE / no-collapse cases (overload, hipbelt-off abuse): factor 1.0 on the knocked-down
  first-ply failure (first-ply failure is well below collapse for these +-45 / UD tube laminates).
- Buckling: eigenvalue >= 1.5 x the case factor (2.25 on limit cases, 1.5 on ultimate cases).
- Bonded joints: AVERAGE shear >= the case factor; elastic Volkersen PEAK <= strength at limit load
  (factor 1.0): a toughened MMA/epoxy yields at the peak and redistributes (Hart-Smith), so the
  average governs ultimate; the joint coupon test (load_standard.md T6) has to confirm it.
- Fatigue: 1e5 cycles of 0 -> 1.6 g x 68 kg (bag carry), the walking peak measured by Rome et al.
  (a 50 lb load hits the wearer with ~80 lb on the downswing). This envelopes the old 1.2 g rule.

Old standard (v1, pack5200_cases): every dynamic case 2.5 g x SF 2.0 = 5.0 x rated on yield/FPF, Volkersen
peak >= 2.0, buckling >= 3.0. HA-LS-1 dynamic cases: 2.0 g x 1.5 = 3.0 x rated (static carry stays 2.0 x
rated, matching the 2x-rated static proof tests the leaders publish).
"""
from __future__ import annotations

from .load_cases import LoadCase, pack5200_cases

NAME = "HA-LS-1"
RATED_KG = 68.0            # 150 lb
OVERLOAD_KG = 91.0         # 200 lb
G_STUMBLE = 2.0            # stumble / drop-step limit factor (load_standard.md section 3)
G_WALK = 1.6               # walking peak (Rome et al.: 50 lb load -> ~80 lb peak force)
F_LIMIT = 1.5              # yield / first-ply factor on limit loads
F_STATIC = 2.0             # static carry factor (= the leaders' 2x-rated static proof)
F_ULT = 1.0                # ultimate / no-collapse cases
BUCKLING_OVER_FACTOR = 1.5     # buckling eigenvalue >= 1.5 x case factor
BOND_PEAK_FACTOR = 1.0         # Volkersen elastic peak <= strength at limit load
FATIGUE = {"g": G_WALK, "cycles_required": 1e5}

# name -> (g factor, required factor, load kg) ; placements as pack5200_cases
TABLE = {
    "static_carry":         (1.0, F_STATIC, RATED_KG),
    "drop_2p5g":            (G_STUMBLE, F_LIMIT, RATED_KG),     # renamed in reports: dynamic stumble
    "side_hill_torsion":    (G_WALK, F_LIMIT, RATED_KG),
    "single_stay_setdown":  (G_STUMBLE, F_LIMIT, RATED_KG),
    "meat_shelf_heavy_low": (G_STUMBLE, F_LIMIT, RATED_KG),
    "tall_load":            (G_STUMBLE, F_LIMIT, RATED_KG),
    "tall_load_posts":      (G_STUMBLE, F_LIMIT, RATED_KG),
    "overload_haul":        (G_WALK, F_ULT, OVERLOAD_KG),
    "hipbelt_off_abuse":    (1.5, F_ULT, RATED_KG),
}

DISPLAY = {
    "drop_2p5g": "stumble_2g",
}


def ls1_cases(cg_bag_mm: float = 180.0) -> list[LoadCase]:
    """pack5200_cases with the HA-LS-1 g-factors and required factors (case names kept so every
    consumer of the v1 names keeps working; ``drop_2p5g`` is the 2.0 g stumble case here)."""
    bag = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown")
    over = {}
    for n, (g, req, kg) in TABLE.items():
        over[n] = {"g_factor": g, "required_sf": req, "load_kg": kg}
        if n in bag:
            over[n]["cg_aft_mm"] = cg_bag_mm
    cases = pack5200_cases(**over)
    for c in cases:
        g, req, kg = TABLE[c.name]
        c.description = (f"[{NAME}] {kg:g} kg x {g:g} g, required factor {req:g}"
                         + (" (ultimate / no collapse)" if req == F_ULT else "") + ". " + DESC[c.name])
    return cases


DESC = {
    "static_carry": "Bag carry, CG 180 mm aft, hipbelt 80 % / shoulders 20 %.",
    "drop_2p5g": "Stumble / drop-step (dynamic limit), bag carry, CG 180 mm aft.",
    "side_hill_torsion": "Side-hill traverse: gravity tilted 25 deg, load 30 % biased downhill, downhill strap + "
                         "lifter slack (25 % stiffness) -> frame torsion. Walking peak factor.",
    "single_stay_setdown": "Loaded pack set down hard on ONE stay foot: impact + 0.2 friction, balanced by the load's "
                           "inertia (free-free).",
    "meat_shelf_heavy_low": "Meat on the load shelf between frame and bag, CG 120 mm aft, shelf tip strapped to the mid-bar "
                            "nodes. Primary mission.",
    "tall_load": "Bone-in quarter standing on the shelf, CG 250 mm aft, top lashed to the crown top bar.",
    "tall_load_posts": "Tall load lashed to the extension-post bar 220 mm above the crown (accessory fitted).",
    "overload_haul": "200 lb meat haul on the shelf at the walking peak: ultimate, no collapse.",
    "hipbelt_off_abuse": "Hipbelt unbuckled (creek crossing): 100 % on shoulders + lifters; no damage, no slip.",
}


def buckling_required(required_sf: float) -> float:
    return BUCKLING_OVER_FACTOR * required_sf


def describe() -> list[dict]:
    return [{"case": DISPLAY.get(n, n), "g": g, "factor": f, "load_kg": kg, "equivalent_x_rated": g * f * kg / RATED_KG}
            for n, (g, f, kg) in TABLE.items()]
