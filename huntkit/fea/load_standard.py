"""HA-LS-1: the calibrated Pack 5200 frame load standard ("match the leaders", owner 2026-11-01).

Full rationale, sources and the physical test plan are in designs/pack_5200/analysis/load_standard.md.
This module is the executable form: the load cases, the factor per case, and the acceptance rules the
sizing (huntkit.fea.sizing5200, standard="ls1") applies. Current revision: **C** (2026-11-06). ``rev="B"``
reproduces the records made before that date.

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
REVISION = "C"             # rev C 2026-11-06 (default): cloth-sim CG offsets, IM3 couple envelope, hood + guys
REVISION_B = "B"           # rev B 2026-11-01: no meat shelf; meat on the internal straps. Kept to reproduce records
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
    "meat_straps":          (G_STUMBLE, F_LIMIT, RATED_KG),     # rev B: replaces meat_shelf_heavy_low
    "tall_load":            (G_STUMBLE, F_LIMIT, RATED_KG),
    "tall_load_posts":      (G_STUMBLE, F_LIMIT, RATED_KG),
    "overload_haul":        (G_WALK, F_ULT, OVERLOAD_KG),
    "hipbelt_off_abuse":    (1.5, F_ULT, RATED_KG),
}

DISPLAY = {
    "drop_2p5g": "stumble_2g",
}
RETIRED = {"meat_shelf_heavy_low": "meat_straps"}     # rev A name -> rev B name


# rev B meat placements (load_standard.md section 4.1), matched to the pack-designer's v3.1 internal meat
# harness (geometry.yaml meat_harness): meat CG 150 mm aft of the frame (bag_on_rated basis), vertical mostly
# into the bag-bottom hinge pins (bag_anchor_low, z 60), overturning taken by the three straps IM1-IM3
# (meat_anchor_z190 / z330 / z520) in proportion to height, the rest as contact pressure on the frame face.
_MEAT_P = {"floor_share": 0.7, "pretension_n": 150.0, "face_z": (60.0, 330.0),
           "upper_groups": ("strap_lumbar", "strap_mid", "strap_upper"), "proportional": True}
MEAT = {
    "meat_straps":     {"placement": "meat_straps", "cg_aft_mm": 150.0, "params": dict(_MEAT_P)},
    # bone-in quarter standing on the bag floor: CG higher in the strap stack and lashed to the crown top bar too
    "tall_load":       {"placement": "meat_straps", "cg_aft_mm": 160.0,
                        "params": {**_MEAT_P, "upper_groups": ("strap_mid", "strap_upper", "lash")}},
    "tall_load_posts": {"placement": "meat_straps", "cg_aft_mm": 160.0,
                        "params": {**_MEAT_P, "upper_groups": ("strap_mid", "strap_upper", "lash_posts")}},
    "overload_haul":   {"placement": "meat_straps", "cg_aft_mm": 150.0, "params": dict(_MEAT_P)},
}


# ---------------------------------------------------------------------------------------------- revisions
# Rev C (owner 2026-11-06, docs/DECISIONS.md; load_standard.md section 4.2): CG offsets calibrated to the cloth
# simulator (analysis/cloth_sim.md, bag_top_anchor.md, bag_attachment.md) instead of the drafted bag shape.
# Factors, g-levels and every other rule are unchanged from rev B.
TOP_ANCHOR_HOOD_GUYS = {
    # crown hood + 2 fixed-length top side guys as released (bag_attachment.md section 2 and 2.5,
    # attach_system_results.json factored_n / 3.0 at C5, runs PR15/19/23). Per 1 g at 68 kg; scaled by g and by
    # load_kg / 68 in the case. Since 2026-11-06 (D-31) the hood lip bears on bare OD 18 bar over x -66 .. +66 only
    # (relieved clear of the crown corner wraps); the ears and guys stay at x +/-95.
    "kind": "hood_guys",
    "hood_n": 52.5,                 # total, aft, spread uniformly over the lip span (consistent nodal loads)
    "hood_half_span_mm": 66.0,      # ASSUMPTION: lip centred on the bar (it floats +/-9 mm between the legs)
    "guy_ear_x_mm": 95.0,
    "guy_n": 37.3,                  # each guy, from the hood ear at x +/-95 toward the bag top corner
    "guy_corner_xz": (149.0, 752.0),
    # ASSUMPTION (frame_cg_recheck.md section 5.1): fixed aft run of each guy, from the 314 mm free length at 19 in
    "guy_dy_mm": float((314.0 ** 2 - (149.0 - 95.0) ** 2 - (752.0 - 702.6) ** 2) ** 0.5),
}
TIE_WEBBING_MIN_MM = 25.0           # rev C: ties / guys bear on the crown bar over >= 25 mm of webbing (38 preferred)

REVISIONS = {
    "B": {"date": "2026-11-01", "bag_cg_mm": 180.0, "bag_cg_z_mm": None, "meat_cg_mm": 150.0,
          "tall_cg_mm": 160.0, "hipbelt_off_cg_mm": 180.0, "couple_tops": ("crown_bar",),
          "top_anchor": None, "tie_webbing_min_mm": None},
    "C": {"date": "2026-11-06", "bag_cg_mm": 205.0, "bag_cg_z_mm": 550.0, "meat_cg_mm": 190.0,
          "tall_cg_mm": 185.0, "hipbelt_off_cg_mm": 205.0, "couple_tops": ("crown_bar", "strap_upper"),
          "top_anchor": TOP_ANCHOR_HOOD_GUYS, "tie_webbing_min_mm": TIE_WEBBING_MIN_MM},
}
BAG_CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "hipbelt_off_abuse")
MEAT_CASES = ("meat_straps", "overload_haul")
TALL_CASES = ("tall_load", "tall_load_posts")
COUPLE_TOPS = {"crown_bar": None, "strap_upper": "strap_upper"}   # variant -> params["couple_top_group"]


def revision(rev: str | None = None) -> dict:
    """Parameters of one HA-LS-1 revision (default: the current one, rev C)."""
    rev = (rev or REVISION).upper()
    if rev not in REVISIONS:
        raise ValueError(f"unknown HA-LS-1 revision {rev!r}; known: {sorted(REVISIONS)}")
    return {"rev": rev, **REVISIONS[rev]}


def meat_cg_mm(rev: str | None = None) -> float:
    return float(revision(rev)["meat_cg_mm"])


def ls1_cases(cg_bag_mm: float | None = None, rev: str | None = None,
              couple_top: str = "crown_bar") -> list[LoadCase]:
    """pack5200_cases with the HA-LS-1 g-factors, required factors and meat placements.
    ``drop_2p5g`` is the 2.0 g stumble case; ``meat_straps`` replaces ``meat_shelf_heavy_low`` (no shelf).

    ``rev``: "C" (default, 2026-11-06) or "B" (2026-11-01, to reproduce the older records).
    ``cg_bag_mm``: override of the bag CG offset. Rev B applies it to C1-C4 only (C8 stays 180, as recorded);
    rev C applies it to all five bag cases.
    ``couple_top``: where the top of the bag CG couple acts on the bag cases: "crown_bar" (the crown top bar)
    or "strap_upper" (the IM3 hooks, z 520). Rev C requires BOTH; use ``ls1_envelope`` for the full set."""
    R = revision(rev)
    if couple_top not in COUPLE_TOPS:
        raise ValueError(f"couple_top must be one of {sorted(COUPLE_TOPS)}")
    if couple_top != "crown_bar" and couple_top not in R["couple_tops"]:
        raise ValueError(f"HA-LS-1 rev {R['rev']} has no {couple_top!r} couple variant")
    cg_bag = float(R["bag_cg_mm"] if cg_bag_mm is None else cg_bag_mm)
    bag4 = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown")
    over = {}
    for n, (g, req, kg) in TABLE.items():
        key = "meat_shelf_heavy_low" if n == "meat_straps" else n
        over[key] = {"g_factor": g, "required_sf": req, "load_kg": kg}
        if n in bag4:
            over[key]["cg_aft_mm"] = cg_bag
    cases = pack5200_cases(**over)
    for c in cases:
        if c.name == "meat_shelf_heavy_low":
            c.name = "meat_straps"
        if c.name in MEAT:
            m = MEAT[c.name]
            c.placement, c.cg_aft_mm, c.params = m["placement"], m["cg_aft_mm"], dict(m["params"])
    if R["rev"] != "B":
        for c in cases:
            if c.name in BAG_CASES:
                c.cg_aft_mm = cg_bag
                c.cg_z_mm = R["bag_cg_z_mm"]
                if COUPLE_TOPS[couple_top]:
                    c.params = {**c.params, "couple_top_group": COUPLE_TOPS[couple_top]}
            elif c.name in MEAT_CASES:
                c.cg_aft_mm = float(R["meat_cg_mm"])
                if R["top_anchor"]:
                    c.params = {**c.params, "top_anchor": dict(R["top_anchor"])}
            elif c.name in TALL_CASES:
                c.cg_aft_mm = float(R["tall_cg_mm"])
    desc = DESC if R["rev"] == "B" else _desc_c(R, couple_top)
    for c in cases:
        g, req, kg = TABLE[c.name]
        c.description = (f"[{NAME} rev {R['rev']}] {kg:g} kg x {g:g} g, required factor {req:g}"
                         + (" (ultimate / no collapse)" if req == F_ULT else "") + ". " + desc[c.name])
    return cases


def ls1_envelope(rev: str | None = None) -> dict[str, list[LoadCase]]:
    """Every case set a frame check must envelope under ``rev``. Rev C: the 9 cases with the bag couple on the
    crown top bar, plus the 5 bag cases with the couple on the IM3 hooks; the worse result governs.
    Rev B: the 9 cases (crown top bar) only."""
    R = revision(rev)
    out = {"crown_bar": ls1_cases(rev=R["rev"])}
    if "strap_upper" in R["couple_tops"]:
        out["strap_upper"] = [c for c in ls1_cases(rev=R["rev"], couple_top="strap_upper") if c.name in BAG_CASES]
    return out


def tie_bearing_ok(width_mm: float, rev: str | None = None) -> bool:
    """Rev C rule: a tie or guy that bears on the crown bar must do so over >= 25 mm of webbing (or a sleeve /
    pocket). Rev B has no such rule."""
    w = revision(rev)["tie_webbing_min_mm"]
    return True if w is None else float(width_mm) >= w - 1e-9


def _desc_c(R: dict, couple_top: str) -> dict:
    top = "the IM3 hooks (z 520)" if couple_top == "strap_upper" else "the crown top bar"
    bag = f"CG {R['bag_cg_mm']:g} mm aft at z {R['bag_cg_z_mm']:g}, couple top at {top}"
    return {
        "static_carry": f"Bag carry, {bag}, hipbelt 80 % / shoulders 20 %.",
        "drop_2p5g": f"Stumble / drop-step (dynamic limit), bag carry, {bag}.",
        "side_hill_torsion": f"Side-hill traverse: gravity tilted 25 deg, load 30 % biased downhill, lateral load at "
                             f"the CG height; downhill strap + lifter slack (25 % stiffness). {bag}.",
        "single_stay_setdown": "Loaded pack set down hard on ONE stay foot: impact + 0.2 friction, balanced by the "
                               "load's inertia (free-free).",
        "meat_straps": f"Meat inside the bag on the internal straps, CG {R['meat_cg_mm']:g} mm aft; face pressure + "
                       f"strap tension, plus the crown hood ({TOP_ANCHOR_HOOD_GUYS['hood_n']:g} N/g aft over x "
                       f"+/-{TOP_ANCHOR_HOOD_GUYS['hood_half_span_mm']:g}) and 2 top guys "
                       f"({TOP_ANCHOR_HOOD_GUYS['guy_n']:g} N/g each from x +/-{TOP_ANCHOR_HOOD_GUYS['guy_ear_x_mm']:g}). "
                       "Primary mission.",
        "tall_load": f"Bone-in quarter standing on the bag floor, cinched by the internal straps, CG "
                     f"{R['tall_cg_mm']:g} mm aft, top lashed to the crown top bar.",
        "tall_load_posts": "Tall load lashed to the extension-post bar 220 mm above the crown (accessory fitted); "
                           f"CG {R['tall_cg_mm']:g} mm aft; load lifters stay on the crown top bar.",
        "overload_haul": f"200 lb meat haul on the internal straps at the walking peak, CG {R['meat_cg_mm']:g} mm aft, "
                         "hood + guys scaled to 91 kg: ultimate, no collapse.",
        "hipbelt_off_abuse": f"Hipbelt unbuckled (creek crossing): 100 % on shoulders + lifters, {bag}; no damage, "
                             "no slip.",
    }


DESC = {
    "static_carry": "Bag carry, CG 180 mm aft, hipbelt 80 % / shoulders 20 %.",
    "drop_2p5g": "Stumble / drop-step (dynamic limit), bag carry, CG 180 mm aft.",
    "side_hill_torsion": "Side-hill traverse: gravity tilted 25 deg, load 30 % biased downhill, downhill strap + "
                         "lifter slack (25 % stiffness) -> frame torsion. Walking peak factor.",
    "single_stay_setdown": "Loaded pack set down hard on ONE stay foot: impact + 0.2 friction, balanced by the load's "
                           "inertia (free-free).",
    "meat_straps": "Meat (boned in game bags) inside the bag, cinched to the frame face by internal straps, CG 150 mm "
                   "aft; face pressure + strap tension (rev B, no shelf). Primary mission.",
    "tall_load": "Bone-in quarter standing on the bag floor, cinched by the internal straps, CG 160 mm aft, top "
                 "lashed to the crown top bar.",
    "tall_load_posts": "Tall load lashed to the extension-post bar 220 mm above the crown (accessory fitted); load "
                       "lifters stay on the crown top bar.",
    "overload_haul": "200 lb meat haul in the bag on the internal straps at the walking peak: ultimate, no collapse.",
    "hipbelt_off_abuse": "Hipbelt unbuckled (creek crossing): 100 % on shoulders + lifters; no damage, no slip.",
}


def buckling_required(required_sf: float) -> float:
    return BUCKLING_OVER_FACTOR * required_sf


def describe() -> list[dict]:
    return [{"case": DISPLAY.get(n, n), "g": g, "factor": f, "load_kg": kg, "equivalent_x_rated": g * f * kg / RATED_KG}
            for n, (g, f, kg) in TABLE.items()]
