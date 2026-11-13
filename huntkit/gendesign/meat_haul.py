"""Required meat-haul modes on the branch frame.

A. Bag on. Meat stays in the bag. IM1–IM3 cinch it against the carbon spreader.
B. Bag off. The bag is unclipped. A quarter sits on the spreader and the same three
   straps hook eye-to-eye on the cleats.
C. Float (owner 2026-11-06, replaces the hinge swing). The meat goes on the frame as in B; the bag hangs upright
   behind it on two B-24 stand-off links clipped to the IM3 eyes, at a 120 / 170 / 220 mm gap.

Run: python -m huntkit.gendesign.meat_haul
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from huntkit.fea.load_cases import LoadCase
from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.gendesign.bag_attach import (
    BARTACK_N,
    HOOK_N,
    _NODE_STATION,
    _frame_model,
    _save,
)
from huntkit.materials import load

DATE = "20261101"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
G = 9.80665
MU = 0.4                         # wet game bag on the spreader, geometry.yaml
QUARTER_KG = 36.0                # R-08, one bone-in quarter
RATED_KG = 68.0
CAM_N = 1100.0                   # ASSUMPTION, DESIGN.md §4.5, 38 mm metal cam (BL-051 note: CORRIE F's 25 mm cam
#                                  carries the same 1100 N, data/materials cam_25mm_al slip_load_n, also unproven)
WEB_N = 20016.0                  # poly_webbing_38mm record
# Under-straps. The belly is how far the cradle hangs below the straight line
# between the stays. A deeper belly keeps the cam tension down.
US1_Z = 95.0
US2_Z = 142.0
BELLY_MM = 70.0
HALF_SPAN_MM = 115.0             # LEGACY (BL-051 note): the stay x, where US1 / US2 stood until BL-049. On the lanes each
#                                  strap has its own half span (lane_half_span: US1 70, US2 165 = spans 140 / 330), so
#                                  the real leg angles are US1 45 deg / US2 23 deg, not _theta()'s 31.3. _theta() is
#                                  kept because the 720 N envelope row of the frame lug check, the cradle FEA and this
#                                  module's bag-on resolution were booked at it; the lane rows are h1_lanes.lug_loads
#                                  'cradle_lane' / 'cradle_lane_b50' (us_route.cradle_span) and h1_crown.body_lane.
#                                  Bag-on: this module books the bag-on under-strap tension at the cradle angle too;
#                                  on the real bag-on path the legs are 81-89 deg, so the booked tension is about 1.9 x
#                                  the path tension (us_route.json cradle_span bag_on_path used_over_path): conservative,
#                                  kept.
# Of the bag-floor vertical, this fraction moves onto the two under-straps.
# The rest stays on the hinge pins. ASSUMPTION.
CRADLE_SHARE = 0.55
US1_FRACTION = 0.60              # lower strap takes the greater share
DETACH_S = 52                    # attachment phase 2026-11-05 (attach_system.PROCEDURES bag_off): 34 + cams + hood lift

# Float mode (owner 2026-11-06, concept A of analysis/meat_carry_alternatives.md; replaces the hinge swing).
# The bag comes off its pins, the meat sits on the frame exactly as in the bag-off haul (cradle + IM1-IM3), and the
# bag hangs upright behind it on two stand-off links B-24 hooked on the IM3 captive eyes. Gap = how far the bag
# moves aft of its carry position = loop distance from the link's hook bed (the T3 hook bed sits on the loop).
FLOAT_GAPS_MM = (120.0, 170.0, 220.0)    # owner 2026-11-06: keep all three (boned and bone-in meat)
FLOAT_VIEW_GAP_MM = 170.0                # the 3D view and the default loop for a bone-in quarter
FLOAT_GEAR_KG = 12.0                     # ASSUMPTION: camp/kill gear left in the bag on a meat trip (design case)
FLOAT_MEAT_KG = QUARTER_KG               # meat on the frame: the cradle case of the bag-off haul (R-08 quarter)
FLOAT_BAG_ENVELOPE_KG = RATED_KG - QUARTER_KG   # misuse envelope for the link parts: the rest of the 68 kg rating in the bag
LINK_ANGLE_DEG = 30.0                    # ASSUMPTION: link 30 deg above horizontal carrying ALL the bag weight (no W1-W3
                                         # friction credited): worst plausible hang
LINK_FACTOR = 3.0                        # HA-LS-1 C5: 2.0 g x 1.5
LINK = {"id": "B-24", "w_mm": 38.0, "hook_fold_mm": 45.0, "loop_fold_mm": 50.0, "loop_open_mm": 25.0,
        "tail_mm": 20.0, "hook_g": 14.0, "thread_g": 1.0}   # hook = the rated bag hook (attach_system HOOK_RATED_G, ASSUMPTION)
BAG_FACE_Y = 19.3                        # geometry.yaml bag.origin_carry_mode.y_frame_side_panel (bag frame face, carry)
BAG_CG_FROM_FACE = 148.2 - 19.3          # geometry.yaml bag.cg_uniform_fill y minus the face: uniform-fill gear CG
FLOAT_CG_LIMIT = 190.0                   # HA-LS-1 rev C meat cases (load_standard.md)
HOOK_RATED_LINK_N = 2200.0               # the link hook is the rated bag hook (attach_system.HOOK_RATED_N, PT-1)


def link_cut_mm() -> float:
    """Cut length of one B-24 link: hook fold + reach to the last loop + tail + one fold per loop, rounded up to 5 mm."""
    raw = LINK["hook_fold_mm"] + max(FLOAT_GAPS_MM) + LINK["tail_mm"] + len(FLOAT_GAPS_MM) * LINK["loop_fold_mm"]
    return float(5.0 * np.ceil(raw / 5.0))


def float_link_parts_g() -> dict:
    """Mass of the two B-24 stand-off links, g. Shared with designs/pack_5200/build_geometry.py (own weight group)."""
    gm = float(load("poly_webbing_38mm").require("mass_g_m"))
    return {"38 mm webbing, 2 x " + f"{link_cut_mm():.0f} mm": 2 * link_cut_mm() / 1000.0 * gm,
            "rated 38 mm hooks (2), same part as the bag hooks": 2 * LINK["hook_g"],
            "thread (box-X + loop box-X)": 2 * LINK["thread_g"]}


def link_tension(bag_kg: float, factored: bool = True) -> float:
    """Tension in one link when the two links carry the whole bag at LINK_ANGLE_DEG above horizontal."""
    t = bag_kg * G / (2.0 * np.sin(np.radians(LINK_ANGLE_DEG)))
    return float(t * (LINK_FACTOR if factored else 1.0))


def float_lever(gap: float, meat_kg: float, bag_kg: float) -> dict:
    """Load CG aft of the stay plane for meat on the frame (a slab filling the gap) and the bag hung upright behind it.
    Lever arithmetic (analysis/meat_carry_alternatives.md section 3 A), not a cloth sim."""
    meat_y = BAG_FACE_Y + gap / 2.0
    bag_y = BAG_FACE_Y + gap + BAG_CG_FROM_FACE
    cg = (meat_kg * meat_y + bag_kg * bag_y) / (meat_kg + bag_kg)
    bag_max = meat_kg * (FLOAT_CG_LIMIT - meat_y) / (bag_y - FLOAT_CG_LIMIT) if bag_y > FLOAT_CG_LIMIT else float("inf")
    return {"gap_mm": gap, "meat_y": meat_y, "bag_y": bag_y, "cg_mm": cg,
            "moment_nm": (meat_kg + bag_kg) * G * cg / 1000.0, "bag_max_kg_at_190": bag_max}


def swing_lever(meat_kg: float, bag_kg: float, angle_deg: float = 28.5) -> float:
    """The retired swing for comparison: meat CG 110 mm (the old bay ASSUMPTION), bag uniform-fill CG rotated about z 60."""
    a = np.radians(angle_deg)
    dy, dz = BAG_CG_FROM_FACE, 592.5 - 60.0
    y = BAG_FACE_Y + dy * np.cos(a) + dz * np.sin(a)
    return float((meat_kg * 110.0 + bag_kg * y) / (meat_kg + bag_kg))


def _stations(case: LoadCase) -> dict:
    """Factored force on the heavier side of each fairlead."""
    raw = case._loads(_frame_model())
    best: dict[str, dict] = {}
    factor = float(case.required_sf)
    for nid, name in _NODE_STATION.items():
        if nid not in raw:
            continue
        v = np.asarray(raw[nid][:3], float) * factor
        n = float(np.linalg.norm(v))
        row = {"n": n, "fy": float(v[1]), "fz": float(v[2]), "node": nid}
        if name not in best or n > best[name]["n"]:
            best[name] = row
    return best


def _scale(sf: float, checked_n: float, new_n: float) -> float:
    return float(sf) * float(checked_n) / max(float(new_n), 1.0)


def _theta() -> float:
    """LEGACY leg angle (stay x half span, see HALF_SPAN_MM); the lane angles are ``theta_lane``."""
    return float(np.arctan(BELLY_MM / HALF_SPAN_MM))


def lane_half_span(name: str) -> float:
    """BL-051: half span of under-strap ``name`` on its lane (h1_lanes.LANE_X: US1 70, US2 165 mm)."""
    from .h1_lanes import LANE_X
    return float(LANE_X[name])


def theta_lane(name: str, belly: float = BELLY_MM) -> float:
    """BL-051: leg angle of under-strap ``name`` on its lane, atan(belly / lane half span)."""
    return float(np.arctan(belly / lane_half_span(name)))


def cradle_tension(vertical_n: float) -> float:
    """Strap tension for a cradle whose two side legs rise at ``_theta``."""
    return float(vertical_n) / (2.0 * np.sin(_theta()))


def _pair(vertical_n: float, basis: dict) -> dict:
    """US1 and US2 anchor forces. ``vertical_n`` is the factored load in the cradle."""
    out = {}
    for name, frac in (("us1", US1_FRACTION), ("us2", 1.0 - US1_FRACTION)):
        t = cradle_tension(vertical_n * frac)
        th = _theta()
        n = t
        out[name] = {
            "n": n, "fy": float(t * np.cos(th)), "fz": float(-t * np.sin(th)),
            "vertical_n": float(vertical_n * frac), "tension_n": t,
            "sf": _scale(basis["sf"], basis["force_n"], n),
            "sf_fatigue": _scale(basis["sf_fatigue"], basis["force_n"], n),
            "from": basis.get("station", "cradle"),
        }
    return out


def _shift_hinge(row: dict, keep: float, basis: dict) -> dict:
    """Leave ``keep`` of the hinge's vertical force on the pin. Rescale from the hinge FEA."""
    fy, fz = float(row["fy"]), float(row["fz"]) * keep
    n = float(np.hypot(fy, fz))
    out = dict(row)
    out.update({"n": n, "fy": fy, "fz": fz,
                "sf": _scale(basis["sf"], basis["force_n"], n),
                "sf_fatigue": _scale(basis["sf_fatigue"], basis["force_n"], n)})
    return out


def _friction_leg(weight_n: float, n_straps: int) -> float:
    """Tension in one strap leg so μ times the strap's normal force holds ``weight_n``.

    A strap hooked eye-to-eye has two legs and squeezes with about 2 T. Geometry.yaml
    uses this for the 141 N figure (5 straps).
    """
    return weight_n / (MU * n_straps * 2.0)


def spreader_bearing_face() -> dict:
    """The bearing face in every mode (CONTRACTS.md §6): Sandwich v2, BP-06 rev C, 7 mm core (owner 2026-11-06).

    Numbers are the real-support check in analysis/spreader.md (spreader_results.json, 2 mm grid): first-ply SF
    under the factored HA-LS-1 C5 meat + bone (factor on the load, so the requirement is SF >= 1), fatigue SF at
    the 1.6 g walking peak, peak skin pressure, and the largest factored deflection."""
    r = json.loads((ANALYSIS / "spreader_results.json").read_text())["chosen"]
    return {"sf": float(r["sf_fpf"]), "sf_fatigue": float(r["sf_fatigue"]),
            "sf_sandwich": float(r["sandwich_sf_min"]), "peak_kpa": float(r["skin_peak_kpa"]),
            "defl_mm": float(r["w_fact_max"]), "name": r["name"], "mass_g": float(r["mass_g"])}


def analyse(cradle_fea: dict | None = None) -> dict:
    """Load paths and safety factors for bag-on, the wedge, and bag-off."""
    branch = json.loads((ANALYSIS / "generative_branch_results.json").read_text())
    fair = json.loads((ANALYSIS / "bag_attachment_results.json").read_text())
    fine = [r for r in fair["fea"] if abs(r["h_mm"] - fair["h_mm"]) < 1e-6]
    hinge = next(r for r in fine if r["station"] == "hinge")
    im3 = next(r for r in fine if r["station"] == "im3")
    sheet = spreader_bearing_face()

    # Bag on is the HA-LS-1 meat resolution already used to size the cleats.
    bag_on_nodes = fair["governing"]

    def mixed(nodes):
        rows = {}
        for name, force in nodes.items():
            n = force["n"]
            if name == "hinge":
                src, sf, fat, fn = hinge, hinge["sf"], hinge["sf_fatigue"], hinge["force_n"]
            else:
                src, sf, fat, fn = im3, im3["sf"], im3["sf_fatigue"], im3["force_n"]
            rows[name] = {"n": n, "fy": force.get("fy", 0.0), "fz": force.get("fz", 0.0),
                          "sf": _scale(sf, fn, n), "sf_fatigue": _scale(fat, fn, n),
                          "from": src["station"]}
        return rows

    bag_on = mixed({k: {"n": v["n"], "fy": v["fy"], "fz": v["fz"]} for k, v in bag_on_nodes.items()})
    # The published FEA is exactly these forces. Use it directly where we have it,
    # and scale IM1/IM2 from IM3 (same cleat, aft direction, lower force).
    for name, src in (("hinge", hinge), ("im3", im3)):
        bag_on[name]["sf"] = src["sf"]
        bag_on[name]["sf_fatigue"] = src["sf_fatigue"]

    # Under-straps take part of the floor vertical off the hinge pins.
    # Bag-off has no floor: the cradle carries the quarter and the IM straps only cinch.
    us_basis = cradle_fea if cradle_fea else hinge
    if "force_n" not in us_basis:
        us_basis = {**us_basis, "force_n": us_basis.get("requested_n", us_basis["n"]),
                    "station": "us1"}

    def with_cradle(nodes, cradle_vertical, keep_hinge):
        out = {k: dict(v) for k, v in nodes.items() if k != "hinge"}
        if "hinge" in nodes and keep_hinge > 0:
            out["hinge"] = _shift_hinge(nodes["hinge"], keep_hinge, hinge)
        out.update(_pair(cradle_vertical, us_basis))
        return out

    floor_on = 2.0 * abs(bag_on["hinge"]["fz"])
    bag_on = with_cradle(bag_on, CRADLE_SHARE * floor_on, 1.0 - CRADLE_SHARE)

    walk = QUARTER_KG * G * 1.6
    leg3 = _friction_leg(walk, 3)
    leg5 = _friction_leg(walk, 5)
    # Strength case for the bare frame: 1.5 on the 1.6 g walking peak.
    w_off = walk * 1.5
    cinch = 150.0 * 1.5
    off_c = mixed({
        "im1": {"n": cinch, "fy": cinch, "fz": 0.0},
        "im2": {"n": cinch, "fy": cinch, "fz": 0.0},
        "im3": {"n": cinch, "fy": cinch, "fz": 0.0},
    })
    off_c.update(_pair(w_off, us_basis))

    # Float: the meat path is the bag-off haul (same cradle, same IM cinch); the bag hangs on the two B-24 links at the
    # IM3 eyes, so each IM3 eye carries its meat-strap leg plus one link (aft and down at LINK_ANGLE_DEG).
    def float_nodes(bag_kg):
        t = link_tension(bag_kg)
        a = np.radians(LINK_ANGLE_DEG)
        im3 = {"n": 0.0, "fy": cinch + t * np.cos(a), "fz": -t * np.sin(a)}
        im3["n"] = float(np.hypot(im3["fy"], im3["fz"]))
        rows = mixed({"im1": {"n": cinch, "fy": cinch, "fz": 0.0}, "im2": {"n": cinch, "fy": cinch, "fz": 0.0},
                      "im3": im3})
        rows.update(_pair(w_off, us_basis))
        return rows, t
    float_c, t_link = float_nodes(FLOAT_GEAR_KG)
    float_env, t_link_env = float_nodes(FLOAT_BAG_ENVELOPE_KG)

    web = float(load("poly_webbing_38mm").require("breaking_strength_n"))
    assert abs(web - WEB_N) < 1.0

    def pack(name, required, nodes, note, strap_n):
        cleat_fat = min(float(r["sf_fatigue"]) for r in nodes.values())
        cleat_sf = min(float(r["sf"]) for r in nodes.values())
        hinge_n = nodes.get("hinge", {}).get("n", strap_n)
        return {
            "name": name, "required": required, "viable": bool(cleat_sf >= 1.0 and cleat_fat >= 1.0),
            "nodes": nodes, "note": note,
            "cleat_sf": cleat_sf, "cleat_fatigue": cleat_fat,
            "hook_sf": HOOK_N / strap_n, "cam_sf": CAM_N / strap_n,
            "bartack_sf": BARTACK_N / max(hinge_n, strap_n),
            "web_sf": web / strap_n, "hook_n": strap_n,
            "sheet_sf": sheet["sf"], "sheet_fatigue_sf": sheet["sf_fatigue"],
            "sheet_peak_kpa": sheet["peak_kpa"], "sheet_defl_mm": sheet["defl_mm"],
            "frame_sf": branch["cases"]["meat_straps"],
        }

    # Hook sees the strap. Bag-on governing strap demand is the published 605 N
    # (2 × 303 N service leg). Bag-off and float use the factored hand cinch on the meat hooks; the float link has
    # its own rated hook (modes['float']['link']).
    modes = {
        "bag_on": pack(
            "Bag on, meat inside", True, bag_on,
            "Meat in the bag, cinched by IM1–IM3 against the spreader. Vertical load into the hinge pins.",
            max(605.0, max(bag_on[k]["n"] for k in ("im1", "im2", "im3"))),
        ),
        "float": pack(
            "Float: bag hung behind the meat", True, float_c,
            "Bag off its pins, hung upright on two B-24 stand-off links at the IM3 eyes. Meat in the cradle, IM1-IM3 over it.",
            cinch,
        ),
        "bag_off": pack(
            "Bag off, bare frame", True, off_c,
            "Quarter in the under-strap cradle, cinched to the spreader by IM1–IM3.",
            cinch,
        ),
    }
    for key, vertical in (
        ("bag_on", CRADLE_SHARE * floor_on),
        ("float", w_off),
        ("bag_off", w_off),
    ):
        t = max(modes[key]["nodes"]["us1"]["tension_n"], modes[key]["nodes"]["us2"]["tension_n"])
        modes[key]["cradle_tension_n"] = t
        modes[key]["cradle_cam_sf"] = CAM_N / t
        modes[key]["cradle_web_sf"] = web / t
        modes[key]["cradle_vertical_n"] = vertical
        modes[key]["viable"] = bool(modes[key]["viable"] and modes[key]["cradle_cam_sf"] >= 1.0)
    modes["cradle"] = {
        "us1_z": US1_Z, "us2_z": US2_Z, "belly_mm": BELLY_MM,
        "theta_deg": float(np.degrees(_theta())),
        "share": CRADLE_SHARE, "us1_fraction": US1_FRACTION,
        "detach_s": DETACH_S,
        "basis": "cradle_fea" if cradle_fea else "hinge_scaled",
    }
    fl = modes["float"]
    fl["gaps_mm"] = list(FLOAT_GAPS_MM)
    fl["view_gap_mm"] = FLOAT_VIEW_GAP_MM
    fl["gear_kg"], fl["meat_kg"], fl["bag_envelope_kg"] = FLOAT_GEAR_KG, FLOAT_MEAT_KG, FLOAT_BAG_ENVELOPE_KG
    fl["link"] = {"id": LINK["id"], "cut_mm": link_cut_mm(), "angle_deg": LINK_ANGLE_DEG,
                  "tension_1g_n": link_tension(FLOAT_GEAR_KG, factored=False), "tension_factored_n": t_link,
                  "tension_envelope_factored_n": t_link_env, "hook_rated_n": float(HOOK_RATED_LINK_N),
                  "hook_sf": float(HOOK_RATED_LINK_N / t_link), "hook_sf_envelope": float(HOOK_RATED_LINK_N / t_link_env),
                  "mass_g": float(sum(float_link_parts_g().values())), "parts_g": float_link_parts_g()}
    # Direct FE of the IM3 eye under the float vectors (float_fea.py, 2026-11-06) replaces the force-scaled factors,
    # and the US1 fatigue sets the float meat limit on the frame. Kept optional so analyse() runs before the solve.
    direct = ANALYSIS / "float_fea_results.json"
    if direct.exists():
        fe = json.loads(direct.read_text())
        for rows, key in ((float_c, "design"), (float_env, "misuse")):
            r = fe["im3"][key]
            rows["im3"].update({"sf": float(r["sf"]), "sf_fatigue": float(r["sf_fatigue"]),
                                "sf_creep": float(r["sf_creep"]), "from": "im3 float direct FE"})
        fl["cleat_sf"] = min(float(r["sf"]) for r in float_c.values())
        fl["cleat_fatigue"] = min(float(r["sf_fatigue"]) for r in float_c.values())
        fl["im3_direct"] = {"design_sf": fe["im3"]["design"]["sf"], "design_fatigue": fe["im3"]["design"]["sf_fatigue"],
                            "misuse_sf": fe["im3"]["misuse"]["sf"], "misuse_fatigue": fe["im3"]["misuse"]["sf_fatigue"],
                            "bag_on_1415_sf": fe["bag_on_1415"]["sf"], "inside_envelope": fe["im3_inside_envelope"]}
        fl["meat_limit_kg"] = float(fe["us1"]["limit_kg"])
        fl["meat_limit_lb"] = float(fe["us1"]["limit_lb"])
    fl["im3_eye_n"] = float_c["im3"]["n"]
    fl["im3_eye_envelope_n"] = float_env["im3"]["n"]
    fl["nodes_envelope"] = float_env
    fl["lever"] = [float_lever(g_, FLOAT_MEAT_KG, FLOAT_GEAR_KG) for g_ in FLOAT_GAPS_MM]
    fl["lever_rated"] = [float_lever(g_, RATED_KG - FLOAT_GEAR_KG, FLOAT_GEAR_KG) for g_ in FLOAT_GAPS_MM]
    fl["swing_cg_mm"] = swing_lever(FLOAT_MEAT_KG, FLOAT_GEAR_KG)
    fl["swing_cg_rated_mm"] = swing_lever(RATED_KG - FLOAT_GEAR_KG, FLOAT_GEAR_KG)
    fl["cg_limit_mm"] = FLOAT_CG_LIMIT
    fl["viable"] = bool(fl["viable"] and all(r["cg_mm"] <= FLOAT_CG_LIMIT + 1e-6 for r in fl["lever"]))
    # heavier meat on the frame (the rest of the rating minus the gear): cradle numbers for the structural hand-off
    heavy = (RATED_KG - FLOAT_GEAR_KG) / QUARTER_KG
    us1 = float_c["us1"]
    fl["heavy_meat"] = {"meat_kg": RATED_KG - FLOAT_GEAR_KG, "us1_n": us1["n"] * heavy,
                        "us1_sf": us1["sf"] / heavy, "us1_sf_fatigue": us1["sf_fatigue"] / heavy,
                        "cam_sf": CAM_N / (us1["tension_n"] * heavy)}
    modes["bag_off"]["leg_walk_im_n"] = leg3
    modes["bag_off"]["leg_walk_with_wraps_n"] = leg5
    modes["bag_off"]["leg_factored_n"] = leg3 * 1.5
    modes["bag_off"]["walk_n"] = walk
    modes["bag_on"]["frame_sf"] = branch["cases"]["meat_straps"]
    # Bag-off cleat forces are inside the meat_straps envelope, so the frame SF stands.
    modes["bag_off"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["float"]["frame_sf"] = branch["cases"]["meat_straps"]
    modes["sheet"] = dict(sheet)
    web_m = load("poly_webbing_38mm")              # B.2 booking (see cradle_parts_g); CORRIE F costs its own 25 mm parts
    pa = load("pa12_cf_fdm_paht")
    parts = cradle_parts_g(cradle_fea)
    plastic = parts["printed anchors (4)"]
    filament = plastic * 1.08 * float(pa.require("print_cost_usd_per_g"))
    modes["cradle"]["mass_g"] = float(sum(parts.values()))
    modes["cradle"]["parts_g"] = parts
    modes["cradle"]["cost_usd"] = filament * 1.15 + 4 * 2.50 + 2 * 4.00 + 1.10 * float(web_m.cost_usd["value"]) + 2 * 0.40
    return modes


def cradle_parts_g(cradle_fea: dict | None = None) -> dict:
    """Mass list of the two 38 mm under-straps (cradle), g. Shared with designs/pack_5200/build_geometry.py.
    Anchor mass from cradle_fea.json (``added_g``) when given; pins/sleeves as bag_attach; cam 22 g ASSUMPTION.
    BL-051 note: this is the CORRIE B.2 / 2026-11-01 booking (38 mm straps, 38 mm cams, 1.10 m), i.e. the ledger's
    B.2 baseline that strap_arch.today_parts reads by name. The adopted CORRIE F books its own 25 mm under-straps
    (strap_arch rec 'US-cams' on cam_25mm_al, 25 mm webbing at the us_route.json strap_lengths cut lengths) and
    removes these rows ('REMOVED (B.2): under-straps ...'). Do not rename or re-mass these rows to 25 mm here: that
    would move the B.2 baseline every roll-up step is measured from."""
    if cradle_fea is None:
        f = ANALYSIS / "cradle_fea.json"
        cradle_fea = json.loads(f.read_text()) if f.exists() else {}
    web_m = load("poly_webbing_38mm")
    anchor_g = float((cradle_fea or {}).get("added_g", 6.2))
    return {
        "printed anchors (4)": 4 * anchor_g,
        "7075 pins (4)": 4 * 2.41,
        "UHMWPE sleeves (4)": 4 * 0.29,
        "38 mm cams (2)": 2 * 22.0,
        # BL-034 (orchestrator): the backstop behind each cam is the stainless 25 mm tri-glide (triglide_25mm record
        # stainless_alt: 11 g, 3.75 kN break) so a cam slip cannot lengthen the cradle; was 2 x 3.0 g nylon ASSUMPTION
        "tri-glide keepers (2)": 2 * float(load("triglide_25mm").require("stainless_alt_mass_g")),
        "38 mm webbing, 1.10 m": 1.10 * float(web_m.require("mass_g_m")),
        "bag-floor channels": 8.0,
    }


def _draw(mode_key: str, modes: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Circle, Polygon
    from .render import _style
    _style()
    m = modes[mode_key]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 6.6))
    ink, frame, sheet, meat, strap, bag, rail = (
        "#0b0b0b", "#3c3d40", "#2a78d6", "#8d4e3c", "#eb6834", "#c6b59a", "#b7b6b1")

    def side(ax):
        ax.set_xlim(-70, 280)
        ax.set_ylim(-20, 620)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("Side  ·  wearer to the left", loc="left", fontsize=11)
        # wearer
        ax.plot([-40, -40], [0, 560], color="#d0c8bc", lw=10, solid_capstyle="round")
        ax.text(-48, 300, "wearer", rotation=90, va="center", ha="center", fontsize=8, color="#8a847c")
        # rails on the wearer face of the stays
        ax.plot([-14, -14], [40, 460], color=rail, lw=7, solid_capstyle="round", zorder=2)
        # stay
        ax.plot([0, 0], [0, 540], color=frame, lw=9, solid_capstyle="round", zorder=3)
        # spreader, bag side of the stay
        ax.plot([10, 10], [70, 500], color=sheet, lw=4, solid_capstyle="butt", zorder=4)
        ax.text(16, 80, "spreader", color=sheet, fontsize=8)
        for z, lab in ((60, "hinge"), (95, "US1"), (142, "US2"), (190, "IM1"), (330, "IM2"), (520, "IM3")):
            ax.add_patch(Circle((0, z), 6, facecolor="#6a6b6e", edgecolor=ink, lw=0.4, zorder=5))
            ax.text(-8, z, lab, ha="right", va="center", fontsize=7.5, color=ink)
        # cradle: aft and down from US1 and US2, under the floor
        ax.plot([0, 55, 120], [95, 25, 25], color="#1baf7a", lw=2.4, zorder=6)
        ax.plot([0, 70, 140], [142, 55, 55], color="#1baf7a", lw=2.4, zorder=6)
        ax.text(125, 18, "under-straps", color="#1baf7a", fontsize=8)
        if mode_key == "bag_on":
            bag_x = [18, 18, 250, 200, 18]
            bag_z = [40, 760, 700, 40, 40]
            ax.add_patch(Polygon(list(zip(bag_x, bag_z)), closed=True, facecolor=bag,
                                 edgecolor=ink, lw=0.8, alpha=0.9, zorder=1))
            ax.add_patch(FancyBboxPatch((22, 90), 130, 520, boxstyle="round,pad=0,rounding_size=18",
                                         facecolor=meat, edgecolor="none", alpha=0.9, zorder=2))
            ax.text(80, 360, "meat\nin the bag", color="#fcfcfb", fontsize=9, ha="center", va="center")
            for z in (190, 330, 520):
                ax.annotate("", xy=(14, z), xytext=(150, z + 30),
                            arrowprops=dict(arrowstyle="-", color=strap, lw=2.0), zorder=6)
        elif mode_key == "float":
            g_ = m["view_gap_mm"]
            # bag upright, translated aft by the gap; hung on the B-24 link at IM3
            ax.add_patch(Polygon([(18 + g_, 40), (18 + g_, 760), (250 + g_ * 0.2, 700), (200 + g_ * 0.2, 40)],
                                 closed=True, facecolor=bag, edgecolor=ink, lw=0.8, alpha=0.9, zorder=1))
            ax.add_patch(FancyBboxPatch((14, 100), g_ - 6, 430, boxstyle="round,pad=0,rounding_size=16",
                                         facecolor=meat, edgecolor="none", alpha=0.95, zorder=2))
            ax.text(14 + g_ / 2, 320, "meat on\nthe frame", color="#fcfcfb", fontsize=9, ha="center", va="center")
            ax.plot([6, 18 + g_], [520, 520], color="#c27a1a", lw=4, zorder=7)
            ax.text(20, 540, f"B-24 link, gap {g_:.0f}", color="#c27a1a", fontsize=8, zorder=7)
            for z in (190, 330):
                ax.plot([8, g_ + 8, 8], [z - 6, z + 30, z + 6], color=strap, lw=2.0, zorder=6)
        else:
            ax.add_patch(FancyBboxPatch((14, 100), 120, 430, boxstyle="round,pad=0,rounding_size=16",
                                         facecolor=meat, edgecolor="none", alpha=0.95, zorder=2))
            ax.text(70, 320, "quarter\non the\nspreader", color="#fcfcfb", fontsize=9, ha="center", va="center")
            for z in (190, 330, 520):
                ax.plot([8, 130, 8], [z - 6, z + 36, z + 6], color=strap, lw=2.0, zorder=6)
            ax.text(150, 400, "IM straps\neye to eye", color=strap, fontsize=8)

    def face(ax):
        ax.set_xlim(-180, 180)
        ax.set_ylim(-20, 620)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title("From the bag side", loc="left", fontsize=11)
        for x in (-115, 115):
            ax.plot([x, x], [0, 540], color=frame, lw=10, solid_capstyle="round", zorder=3)
        ax.add_patch(FancyBboxPatch((-100, 80), 200, 400, boxstyle="round,pad=0,rounding_size=6",
                                     facecolor=sheet, edgecolor="none", alpha=0.35, zorder=1))
        ax.text(0, 100, "spreader", color=sheet, fontsize=8, ha="center")
        if mode_key == "bag_off":
            ax.add_patch(FancyBboxPatch((-70, 140), 140, 340, boxstyle="round,pad=0,rounding_size=20",
                                         facecolor=meat, edgecolor="none", zorder=2))
        elif mode_key == "float":
            ax.add_patch(FancyBboxPatch((-70, 140), 140, 340, boxstyle="round,pad=0,rounding_size=20",
                                         facecolor=meat, edgecolor="none", zorder=2))
            for x in (-115, 115):
                ax.plot(x, 520, "s", color="#c27a1a", ms=9, zorder=6)
            ax.text(0, 548, "B-24 links on the IM3 eyes", color="#c27a1a", fontsize=8, ha="center")
        else:
            ax.add_patch(FancyBboxPatch((-90, 110), 180, 400, boxstyle="round,pad=0,rounding_size=16",
                                         facecolor=meat, edgecolor="none", alpha=0.85, zorder=2))
        for z, lab, col in ((95, "US1", "#1baf7a"), (142, "US2", "#1baf7a"),
                            (190, "IM1", strap), (330, "IM2", strap), (520, "IM3", strap)):
            ax.plot([-115, 115], [z, z], color=col, lw=3.0, zorder=4)
            ax.plot(-115, z, "o", color="#6a6b6e", ms=6, zorder=5)
            ax.plot(115, z, "o", color="#6a6b6e", ms=6, zorder=5)
            ax.text(122, z, lab, va="center", fontsize=8, color=ink)
        if mode_key == "bag_on":
            ax.plot([-115, 115], [60, 60], color="#6a6b6e", lw=2.0, zorder=4)
            ax.text(122, 60, "hinge", va="center", fontsize=8, color=ink)

    side(axes[0])
    face(axes[1])
    sf = m["cleat_fatigue"]
    fig.suptitle(
        f"{m['name']}   ·   anchor fatigue SF {sf:.2f}   ·   cradle cam SF {m['cradle_cam_sf']:.2f}",
        x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.text(0.02, 0.02, m["note"], fontsize=8, color="#52514e")
    names = {"bag_on": f"{DATE}_attach_9_cradle_bag_on.png",
             "float": "20261106_attach_6_float.png",
             "bag_off": f"{DATE}_attach_10_cradle_bag_off.png"}
    return _save(fig, names[mode_key])


def write(modes: dict, screens: list[str]) -> str:
    b, w, o = modes["bag_on"], modes["float"], modes["bag_off"]

    def row(nodes):
        lines = ["| station | force N | strength SF | fatigue SF |", "|---|---:|---:|---:|"]
        for name in ("hinge", "us1", "us2", "im1", "im2", "im3"):
            if name not in nodes:
                continue
            r = nodes[name]
            lines.append(f"| {name} | {r['n']:.0f} | {r['sf']:.2f} | {r['sf_fatigue']:.2f} |")
        return "\n".join(lines)

    lever_rows = "\n".join(
        f"| {r['gap_mm']:.0f} | {r['cg_mm']:.0f} | {q['cg_mm']:.0f} | {r['bag_max_kg_at_190']:.0f} kg |"
        for r, q in zip(w["lever"], w["lever_rated"]))
    text = f"""# Meat haul, three modes required

Owner, 2026-11-01: bag-on and bag-off are requirements. Owner, 2026-11-06: the hinge swing ("between" mode) is
replaced by the float (C): meat on the frame, bag hung upright behind it on two stand-off links. The eight B-01 swells
are accepted.
IM1 stays a meat anchor only, for now. The hook proof test is still open.
Code: `huntkit/gendesign/meat_haul.py`.

The bearing face in every mode is the **Sandwich v2 spreader** (BP-06 rev C: 200 g twill carbon skins on 7 mm
ROHACELL 110, 7.44 mm, 242 × 318 mm, z 112–430; owner 2026-11-06, `rev_c_verification.md`) on the bag side of the
stays. Two **38 mm under-straps** also run under the bag, from fairleads at z {US1_Z:.0f} and
z {US2_Z:.0f}. With the bag on they cinch the floor up to the frame, and the bag shell shares
the vertical load with the hinge pins. With the bag off they are the cradle, so the quarter
does not hang on friction alone. IM1–IM3 still cinch the meat against the spreader.

Each strap is a sewn eye on the left pin, under the floor, and a 38 mm cam on the right pin.
A stainless tri-glide (11 g, 3.75 kN break, `triglide_25mm` record) sits behind the cam so a slip
cannot lengthen the cradle. The belly under the
anchor line is specified at **{BELLY_MM:.0f} mm**, which keeps the side legs at
**{modes['cradle']['theta_deg']:.0f}°** and the cam inside its assumed slip rating.
25 mm webbing was set aside: its ladder lock slips at 300 N and its side-release breaks at
450 N, both under the factored cradle tension.

Spreader, from the real-support check in `spreader.md` (HA-LS-1 C5 meat plus a bone end, 20 % of 68 kg on a
22 mm patch, factored 2.0 g × 1.5, 2 mm grid): first-ply SF **{b['sheet_sf']:.2f}** (≥ 1.0, factor on the load),
fatigue SF **{b['sheet_fatigue_sf']:.2f}** at the 1.6 g walking peak, peak skin pressure **{b['sheet_peak_kpa']:.1f} kPa**,
largest factored deflection **{b['sheet_defl_mm']:.1f} mm**. A 36 kg quarter is inside that check (the C5 case is 68 kg).

Of the bag-floor vertical, **{CRADLE_SHARE:.0%}** moves onto the under-straps and the rest stays
on the hinge pins (ASSUMPTION). The lower strap takes {US1_FRACTION:.0%} of that cradle load.

## A. Bag on (required)

Meat stays in the bag. IM1–IM3 hook to the cleat eyes and cam the meat against the spreader.
The two under-straps run through open channels in the bag floor and are cammed tight, so the
floor is a sling between the hinge pins and the cradle anchors.

Load path: meat → bag floor → under-straps and hinge pins for the vertical share. IM straps →
cleats for the cinch and the overturning. Face pressure → spreader → stay rails.

Branch-frame SF on `meat_straps` is **{b['frame_sf']:.2f}**. Under-strap tension **{b['cradle_tension_n']:.0f} N**,
cam SF **{b['cradle_cam_sf']:.2f}**, webbing SF **{b['cradle_web_sf']:.0f}**.

{row(b['nodes'])}

Hook and cam on the IM straps are checked against the larger of the factored IM force and the
published 605 N strap demand. Hook SF **{b['hook_sf']:.2f}**. IM-cam SF **{b['cam_sf']:.2f}**.
The under-strap cam is the line above, not this one. Bartack SF **{b['bartack_sf']:.2f}**.

## B. Bag off (required)

The bag comes off. The two under-straps stay on the frame and become the cradle. The quarter
sits in them. IM1–IM3 still hook eye-to-eye and cam the meat against the spreader so it cannot
tip off the cradle. Friction is only a reserve. μ 0.4 and the old 141 N leg (five straps) are
the reserve numbers, not the design path.

### Procedure (gloves, about {DETACH_S} s, limit 2 min)

The full step list with seconds is in `analysis/bag_attachment.md` section 7 (attachment phase, 2026-11-05).

1. Lift the crown-hood tab and ease the top of the bag about 10 cm aft so the hood clears the bar. The top guys come with the hood.
2. Unhook the four bag hooks (IM3, then IM2, both sides). IM1 has no bag hook.
3. Pop the two under-strap cams and lift the bag floor out of the open channels. The straps stay on their pins.
4. Pull the two tethered hinge pins at z 60.
5. Lift the bag clear.
6. Set the quarter in the cradle, bone toward the spreader. Cam the two under-straps until the belly is about {BELLY_MM:.0f} mm.
7. Hook IM1–IM3 eye-to-eye over the meat and cam them. A hock can sit on IM1.

Walking peak of 36 kg is **{o['walk_n']:.0f} N**. The strength check is 1.5 times that,
**{o['cradle_vertical_n']:.0f} N**, all of it in the cradle. Lower strap tension
**{o['nodes']['us1']['tension_n']:.0f} N**. Cam SF **{o['cradle_cam_sf']:.2f}**.
The IM cinch used here is the 150 N hand tension times 1.5, **{o['hook_n']:.0f} N** per leg.
Hook SF on that cinch **{o['hook_sf']:.2f}**.

{row(o['nodes'])}

The cradle anchors are the same fairlead as the hinge, on the solid lower stay. Their fatigue
SF is scaled from the fine-mesh solve of the governing cradle vector when that solve is on file,
and from the hinge solve otherwise (`{modes['cradle']['basis']}`).

To put the bag back: pins in, floor channels over the cradle straps, cams tight, bag hooks on, then drop the
crown hood over the top bar. About 60 s (`bag_attachment.md` section 7).

## C. Float: meat on the frame, bag hung behind it (required; owner 2026-11-06)

Replaces the old "between" mode, where the bag pivoted about 28.5° on the z 60 hinge pins. Research
(`docs/research/meat_carry_mechanisms.md`): none of the nine leading packs pivots the bag on a pin; they translate it
aft or lay it back over meat that is already fixed to the frame. Concept and comparison:
`analysis/meat_carry_alternatives.md`.

The bag comes off its pins as in B. The meat goes on the frame exactly as in B: in the two under-strap cradles, IM1–IM3
eye to eye over it. Two **{w['link']['id']} stand-off links** (38 mm webbing, a rated hook at the frame end, three sewn
loops) hook on the IM3 captive eyes. The bag stands upright behind the meat and its two T3 bag hooks clip into the loop
that touches: gap **{' / '.join(f'{g_:.0f}' for g_ in w['gaps_mm'])} mm** ({' / '.join(f'{g_ / 25.4:.1f}' for g_ in w['gaps_mm'])} in).
W1–W3 close round bag and meat. Nothing rotates; the hinge pins are pulled and stay tethered to the bag.

Design case: {w['meat_kg']:.0f} kg of meat on the frame (the cradle case of B) plus {w['gear_kg']:.0f} kg of gear in the
bag (ASSUMPTION). The meat path is B's, so its numbers are B's. The IM3 eyes also carry the links: all the bag's weight
on the two links at {w['link']['angle_deg']:.0f}° above horizontal (no W1–W3 friction credited), factored × 3.0:
**{w['link']['tension_factored_n']:.0f} N per link** ({w['link']['tension_1g_n']:.0f} N at 1 g). Link hook SF
**{w['link']['hook_sf']:.2f}** on the {w['link']['hook_rated_n']:.0f} N rated hook.
Misuse envelope for the link parts: the rest of the 68 kg rating ({w['bag_envelope_kg']:.0f} kg) in the bag:
**{w['link']['tension_envelope_factored_n']:.0f} N per link**, hook SF {w['link']['hook_sf_envelope']:.2f}; IM3 eye
**{w['im3_eye_envelope_n']:.0f} N** (design case {w['im3_eye_n']:.0f} N).

{row(w['nodes'])}

Minimum cleat fatigue SF **{w['cleat_fatigue']:.2f}** (design case); IM3 cleat fatigue on the envelope
**{w['nodes_envelope']['im3']['sf_fatigue']:.2f}** (direct FE with the float force direction, `float_fea.md`; strength
{w['nodes_envelope']['im3']['sf']:.2f}). The printed IM3 cheek at the 1415 N bag-on hook case: SF
{w.get('im3_direct', {}).get('bag_on_1415_sf', float('nan')):.2f}; the float envelope is inside it. Under-strap tension
**{w['cradle_tension_n']:.0f} N**, cam SF **{w['cradle_cam_sf']:.2f}**.

Load CG aft of the stay plane (lever sum, `meat_haul.float_lever`; rev C meat case {w['cg_limit_mm']:.0f} mm):

| gap mm | {w['meat_kg']:.0f} kg meat + {w['gear_kg']:.0f} kg gear | {68 - w['gear_kg']:.0f} kg meat + {w['gear_kg']:.0f} kg gear | heaviest bag that keeps {w['meat_kg']:.0f} kg of meat at ≤ {w['cg_limit_mm']:.0f} mm |
|---:|---:|---:|---:|
{lever_rows}

The retired swing gave {w['swing_cg_mm']:.0f} mm and {w['swing_cg_rated_mm']:.0f} mm for the same two loads.
**Use the smallest loop that fits the meat.** In float the bag holds gear, not meat: more meat goes in the bag in
mode A (rated 68 kg) or on the frame in B.

Heavier meat on the frame (the full {w['heavy_meat']['meat_kg']:.0f} kg with the gear in the bag) is NOT in the design
case: on B's no-friction rule the lower under-strap would see {w['heavy_meat']['us1_n']:.0f} N, strength SF
{w['heavy_meat']['us1_sf']:.2f}, fatigue SF **{w['heavy_meat']['us1_sf_fatigue']:.2f}**, cam SF
{w['heavy_meat']['cam_sf']:.2f}. Friction is not credited (no sourced coefficient, no measured clamp force):
**float meat limit on the frame {w.get('meat_limit_kg', 0):.0f} kg ({w.get('meat_limit_lb', 0):.0f} lb)**, set by US1
fatigue at the 70 mm belly. Direct FE of the IM3 eye and the US1 anchor: `analysis/float_fea.md`.

W1–W3 reach: at the 220 mm gap they need about the carry path + 2 × 220 mm; the haul paths in `geometry.yaml`
(1190 / 1262 / 1468 mm) cover 1010 / 1082 / 1288 mm.

Procedure (gloves): `analysis/bag_attachment.md` section 7, "Float mode".

## What is still open

- Meat-strap hook and cam ratings are assumptions (hook 1500 N, cam slip 1100 N). Proof-test five of each to 830 N before the first sewn bag. The under-strap cam is in this test.
- The four BAG hooks (IM2/IM3) are a rated part since 2026-11-05 (>= 2200 N, proof PT-1, `bag_attachment.md` section 3); the 830 N test no longer covers them.
- IM1 does not get a bag clip yet. It is a meat anchor only until the owner says otherwise.

## Mass and cost of the under-straps

| part | g |
|---|---:|
"""
    for name, grams in modes["cradle"]["parts_g"].items():
        text += f"| {name} | {grams:.1f} |\n"
    text += f"| **added** | **{modes['cradle']['mass_g']:.0f}** |\n\n"
    text += (f"About **${modes['cradle']['cost_usd']:.0f}** on top of the fairlead set. "
             f"Detach time now **{DETACH_S} s** with the crown hood (attachment phase); the two cam pops are about 6 s of that. "
             f"Pack with the cradle is the previous 2979 g plus this added mass.\n\n")
    text += "## Screenshots\n\n"
    for s in screens:
        text += f"- `{s}`\n"
    path = ANALYSIS / "meat_haul_modes.md"
    path.write_text(text)
    return str(path)


def plot_anchor_closeup() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.bag_attach import SCALE, _march
    from huntkit.gendesign.frame_branch import frame_sdf
    from huntkit.gendesign.frame_render import autocrop, raster
    from huntkit.gendesign.render import _style
    _style()
    lo = np.array([70.0, -28.0, 40.0])
    hi = np.array([160.0, 48.0, 175.0])
    mesh = _march(lambda p: frame_sdf(p, SCALE), lo, hi, 0.85)
    fig = plt.figure(figsize=(10.4, 4.6))
    views = (("bag side", 14, -70), ("side", 8, 8), ("above the two anchors", 64, -36))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster([(mesh, (0.32, 0.33, 0.36))], el, az, size=420, spec=0.18)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Under-strap anchors at z 95 and z 142, above the hinge pin",
                 x=0.02, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    return _save(fig, f"{DATE}_attach_8_cradle_anchors.png")


def plot_cradle_fea(row: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from huntkit.gendesign.render import _style
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.6))
    ax = axes[0]
    names = ["strength", "fatigue"]
    vals = [row["sf"], row["sf_fatigue"]]
    ax.barh(names, vals, color=["#1baf7a" if v >= 1 else "#d6342a" for v in vals])
    ax.axvline(1.0, color="#0b0b0b", ls="--", lw=1)
    ax.set_xlabel("safety factor")
    ax.set_title(f"Cradle anchor  ·  {row['requested_n']:.0f} N  ·  {row['h_mm']:.0f} mm mesh",
                 loc="left", fontweight="bold")
    slab = row["slab"]
    finite = np.isfinite(slab)
    show = np.where(finite, slab, np.nan)
    vals_fi = show[finite]
    vmax = float(np.percentile(vals_fi, 99)) if vals_fi.size else 1.0
    im = axes[1].imshow(show.T, origin="lower", cmap="magma", vmin=0, vmax=max(0.25, vmax))
    axes[1].set_title("Failure index through one cheek", loc="left", fontsize=11)
    axes[1].set_xlabel("y, toward the bag")
    axes[1].set_ylabel("z, up the stay")
    fig.colorbar(im, ax=axes[1], fraction=0.046, pad=0.04).set_label("failure index")
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_11_cradle_fea.png")


def emit(log=print):
    from huntkit.gendesign.bag_attach import _fatigue_sf, _creep_sf, _paht, solve_fairlead
    from huntkit.gendesign.frame_branch import stay_radius
    walk = QUARTER_KG * G * 1.6
    us1_v = US1_FRACTION * walk * 1.5
    tension = cradle_tension(us1_v)
    th = _theta()
    force = np.array([tension * np.cos(th), -tension * np.sin(th)])
    radius = float(stay_radius(US1_Z, 1.05))
    log(f"FEA cradle anchor, stay r {radius:.1f} mm, tension {tension:.0f} N")
    row = solve_fairlead(radius, force, h=1.0, label="us1 1.00 mm")
    pa = _paht()
    row["sf_fatigue"] = _fatigue_sf(row["fi99"], 1.6 * 1.5, pa["fat"])
    row["sf_creep"] = _creep_sf(row["fi99"], 1.6 * 1.5, pa["rupture"])
    row["station"] = "us1"
    row["force_n"] = row["requested_n"]
    log(f"  FI99 {row['fi99']:.3f}  SF {row['sf']:.2f}  fat {row['sf_fatigue']:.2f}  "
        f"applied {row['applied_n']:.0f}/{row['requested_n']:.0f}")
    basis = {k: row[k] for k in ("sf", "sf_fatigue", "force_n", "station", "added_g", "fi99", "h_mm")}
    (ANALYSIS / "cradle_fea.json").write_text(json.dumps(basis, indent=2))
    modes = analyse(basis)
    for key in ("bag_on", "float", "bag_off"):
        m = modes[key]
        log(f"  {key}: cleat fat {m['cleat_fatigue']:.2f}  hook {m['hook_sf']:.2f}  "
            f"cam {m['cradle_cam_sf']:.2f}  viable {m['viable']}")
    screens = [
        plot_anchor_closeup(),
        _draw("bag_on", modes),
        _draw("bag_off", modes),
        plot_cradle_fea(row),
    ]
    screens.insert(2, _draw("float", modes))
    path = write(modes, screens)
    out = {k: {kk: vv for kk, vv in modes[k].items() if kk != "nodes"} | {"nodes": modes[k]["nodes"]}
           for k in ("bag_on", "float", "bag_off")}
    out["sheet_sf"] = modes["sheet"]["sf"]
    out["screens"] = screens
    (ANALYSIS / "meat_haul_modes.json").write_text(json.dumps(out, indent=2, default=float))
    log(path)
    return out


def docs_only(log=print) -> str:
    """Rewrite meat_haul_modes.md / .json from the cradle FEA on file (cradle_fea.json) without re-solving it."""
    basis = json.loads((ANALYSIS / "cradle_fea.json").read_text())
    modes = analyse(basis)
    old = json.loads((ANALYSIS / "meat_haul_modes.json").read_text())
    screens = []
    for s_ in old["screens"]:                      # the mode drawings are cheap: redraw them; FEA plots stay as filed
        if "attach_6_" in s_:
            s_ = _draw("float", modes)
        elif "attach_9_" in s_:
            s_ = _draw("bag_on", modes)
        elif "attach_10_" in s_:
            s_ = _draw("bag_off", modes)
        screens.append(str(Path(s_).resolve().relative_to(REPO_ROOT)) if Path(s_).is_absolute() else s_)
    for f in (REPO_ROOT / "docs" / "screens" / "20261101_attach_6_between.png",
              REPO_ROOT / "outputs" / "screens" / "20261101_attach_6_between.png"):
        f.unlink(missing_ok=True)                  # the swing drawing is retired with the mode
    path = write(modes, screens)
    out = {k: {kk: vv for kk, vv in modes[k].items() if kk != "nodes"} | {"nodes": modes[k]["nodes"]}
           for k in ("bag_on", "float", "bag_off")}
    out["sheet_sf"] = modes["sheet"]["sf"]
    out["screens"] = screens
    (ANALYSIS / "meat_haul_modes.json").write_text(json.dumps(out, indent=2, default=float))
    log(path)
    return path


if __name__ == "__main__":
    import sys
    docs_only() if "--docs-only" in sys.argv else emit()
