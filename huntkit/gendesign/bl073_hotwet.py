"""BL-073: close the review-8 frame findings on the PPA-CF H1-P frame (designs/pack_5200/analysis/
review_20261125_eighth.md).

What this module adds to ``bl070_h1p`` (which keeps the BL-070 machinery: layer rule, whole-body check, export path):

* **Hot/wet basis (B-2, M-1, M-8).** ``basis()``: the B-basis tolerance factor for the TDS sample size (``k_factor``,
  noncentral t), the 40 C hot ratio for wet PPA-CF (``hot_ratio``: Fiberlogy PPA-CF15 strength-temperature data read
  through the wet Tg drop), and the conditioned x hot modulus. The material is ``bl070_h1p.materials()['ppa_hw']``.
* **Hip mount (B-1, M-2).** ``hip_plate()``: no nut traps. The D50 boss is grown to a flat back 22 mm behind the
  mount face; a 2 mm 6061-T6 bearing ring under the 8 nuts spreads the load (Hetenyi beam on an elastic foundation);
  torque, preload scatter, creep relaxation and cold loss are computed; bolt length gives >= 2 threads proud.
  ``add_hip_plate`` is the export hook (replaces ``bl070_h1p.add_hip_through``).
* **Re-tune (B-2).** ``export_step_hw``: the BL-070 export-space design step on the ``ppa_hw`` utilisation.
* **Sensitivity (M-1).** ``tornado()``: single-assumption variations, each with the coupon line that retires it.
* **Coupons (M-3, M-4, M-7, M-8).** ``coupons_hw()``: register rows written to ``bl070_h1p.json`` under new keys.
* **Printability (M-5, M-6).** ``pads()``: sacrificial printed standoff pads with a snap-off neck under both halves;
  ``spool_plan()``: one planned filament change per half at the least-stressed layer inside the spool window.

Units N, mm, MPa, g. Run: ``python -m huntkit.gendesign.bl073_hotwet [base | step <prev> <name> <u_lo> <u_hi> | final
<name> | report]``.
"""
from __future__ import annotations

import contextlib
import json
import math
import time
from pathlib import Path

import numpy as np

from . import bl070_h1p as P
from . import frame_iter1 as FI

REPO = P.REPO
OUT = REPO / "outputs" / "bl073"
SCREENS = P.SCREENS
SHOT = "20261125_bl073_"
MAT = "ppa_hw"

# ================================================================================================ basis
FIBERLOGY_T = (20.0, 40.0, 60.0)          # Polymers 18(12):1422 (2026), PPA-CF15 (record source)
FIBERLOGY_UTS = (64.5, 55.7, 44.4)        # MPa
FIBERLOGY_E = (2.437, 2.166, 1.489)       # GPa
FIBERLOGY_TG = 60.5
TG_DRY = 85.0                             # Bambu TDS (DSC)
WATER_SAT_PCT = 1.30                      # Bambu TDS, 25 C / 55 % RH (composite)
MATRIX_FRAC = 0.8                         # ASSUMPTION MATRIX-FRAC: 20 wt % fibre (Bambu does not publish it)
# Tg drop per wt % water, and the basis the water % is on (PA66 is unfilled: matrix; ForTii MX51 is a filled grade
# and its 3.4 % is the compound's uptake: composite, compared with the Bambu TDS 1.30 % as published)
TG_DROP_PER_PCT = {"PA66 (Wetzel 2023, DSC)": ((58.0 - 24.0) / 3.0, "matrix"),          # 11.3 C per wt %
                   "ForTii PPA (Envalior)": ((155.0 - 65.0) / 3.4, "composite")}        # 26.5 C per wt %
T_HOT = 40.0                              # the hot condition of every frame record (modulus_40c_wet, creep 8 h 40 C)
T_ROOM = 23.0


def k_factor(n: int, p: float = 0.90, conf: float = 0.95) -> float:
    """One-sided normal tolerance factor (B-basis: 90 % coverage, 95 % confidence): k = t'_{conf}(n-1, z_p sqrt n) /
    sqrt n (noncentral t). n 5 3.4066, n 6 3.0063, n 10 2.3546 (CMH-17-1G Vol 1 8.3.4.3 table; NIST e-Handbook
    7.2.6.3)."""
    from scipy import stats
    return float(stats.nct.ppf(conf, n - 1, stats.norm.ppf(p) * math.sqrt(n)) / math.sqrt(n))


def _uts_f(t: float) -> float:
    """Fiberlogy PPA-CF15 UTS at temperature t (linear between the points, linear extrapolation below 20 C)."""
    T, U = FIBERLOGY_T, FIBERLOGY_UTS
    if t <= T[1]:
        return U[0] + (U[1] - U[0]) / (T[1] - T[0]) * (t - T[0])
    return U[1] + (U[2] - U[1]) / (T[2] - T[1]) * (t - T[1])


def hot_ratio() -> dict:
    """Strength ratio of WET PPA-CF at 40 C to wet at 23 C. Three readings, the lowest is taken:
    (a) the Fiberlogy PPA-CF15 UTS ratio 40 C / 20 C, dry (0.864);
    (b, c) the Fiberlogy curve read at the same distance below Tg: the wet Bambu Tg = 85 - drop x water, with the drop
    per wt % from PA66 (11.3 C, on the matrix water 1.30 / 0.8) or a filled PPA (ForTii, 26.5 C, on the compound
    water 1.30 %).
    The wet ratio 0.73 (Raise3D conditioned at 23 C) already holds the room-temperature wet loss, so only the extra
    loss from 23 to 40 C is taken here."""
    out = {"fiberlogy_40_20_dry": round(FIBERLOGY_UTS[1] / FIBERLOGY_UTS[0], 3)}
    for lab, (d, on) in TG_DROP_PER_PCT.items():
        w = WATER_SAT_PCT / MATRIX_FRAC if on == "matrix" else WATER_SAT_PCT
        tg_w = TG_DRY - d * w
        t23 = FIBERLOGY_TG - (tg_w - T_ROOM)
        t40 = FIBERLOGY_TG - (tg_w - T_HOT)
        out[lab] = {"drop_c_per_pct": round(d, 1), "water_basis": on, "water_pct": round(w, 3),
                    "tg_wet_c": round(tg_w, 1),
                    "ratio": round(_uts_f(t40) / _uts_f(t23), 3)}
    lo = min([out["fiberlogy_40_20_dry"]] + [v["ratio"] for k, v in out.items() if isinstance(v, dict)])
    out["chosen"] = math.floor(lo * 100) / 100          # rounded down to 0.01
    out["modulus_hot"] = round(FIBERLOGY_E[1] / FIBERLOGY_E[0], 3)
    return out


def basis() -> dict:
    """The BL-069 design basis against the BL-073 hot/wet basis (record values)."""
    r = P.ppa_record()
    k5 = k_factor(5)
    old_z = r["knock"] * r["s_z_design"]
    new_z = r["knock_hw"] * r["s_z_b"]
    return {"k_n5": round(k5, 4), "k_n6": round(k_factor(6), 4), "k_n10": round(k_factor(10), 4),
            "s_z_b": round(57.0 - k5 * 5.0, 2), "s_xy_b": round(168.0 - k5 * 4.0, 2),
            "hot": hot_ratio(), "wet": r["wet"], "knock_hw": r["knock_hw"],
            "z_knocked_bl069": round(old_z, 2), "z_knocked_hw": round(new_z, 2),
            "tau_il_hw": round(0.6 * new_z, 2), "xy_knocked_hw": round(r["knock_hw"] * r["s_xy_b"], 1),
            "z_scale_vs_bl069": round(new_z / old_z, 4),
            "xy_scale_vs_bl069": round(r["knock_hw"] * r["s_xy_b"] / (r["knock"] * r["s_xy"]), 4),
            "E_hot_hw": r["E_hot_hw"], "E_hot_bl069": r["E_hot"], "e_buckle_hw": round(P.e_buckle(MAT), 1),
            "raise3d_cond_z_vs_hw_23c": round(r["s_z_b"] * r["wet"], 2)}


# ================================================================================================ hip mount (B-1, M-2)
# Geometry. The D50 boss (h1_closeout.HIP_CHOSEN: 8 positions on r 19, two groups of 4 about +/-x) is grown from the
# wearer face to a FLAT BACK BOSS_DEPTH behind it; anything of the lumbar body standing aft of that flat inside
# SPOT_D is cut off (spot face). M5 clearance holes D5.5 go straight through; NO nut traps. A 6061-T6 bearing ring
# (RING_OD / RING_ID x RING_T, 8 holes D5.5) sits on the flat; the 8 nuts bear on the ring.
BOSS_DEPTH = 22.0          # mount face -> flat back (the lumbar struts reach y -24.3 inside r 25; flat at y -26.4)
SPOT_D = 49.0              # spot face: ring OD 47 + 2 x 1 mm
RING_OD, RING_ID, RING_T = 47.0, 24.0, 2.0
HOLE_D = 5.5
FLANGE_T = 3.0             # hip_mount.BASE_T (the BL-056 redraw; the D44 x 1.2 drawn mount is not the print file)
NUT_M, NUT_DW = 4.0, 6.9   # DIN 934 A2 M5: m 4.0 (frame_h1.JOINT.nut_t); bearing face dw min 6.9 (ISO 4032 / DIN 934)
PITCH = 0.8                # M5 coarse
SCREW_LS = (20.0, 25.0, 30.0, 35.0, 40.0)   # DIN 7984 M5 stock lengths
MIN_PROTRUDE_THREADS = 2.0
TORQUE_NM = 0.6            # BL-073 hip nut torque (see hip_plate: creep cap at the low nut factor)
K_NOM, K_LO, K_HI = 0.20, 0.14, 0.26   # nut factor: 0.2 typical, scatter 0.14-0.26 (Bossard / Machine Design, cited)
CREEP_LONG = 0.5           # ASSUMPTION CREEP-LONG: PPA-CF layer-normal creep modulus after years at 40 C wet = 0.5 x
#                            short-term (record has 0.85 at 8 h only; no long-term curve published)
CTE_Z = 60e-6              # ASSUMPTION CTE-Z: PPA-CF across the layers, 1/K (not in the Bambu TDS)
CTE_TI, CTE_AL = 8.6e-6, 23e-6
T_COLD = -20.0
TI_MM_G = math.pi / 4 * 4.5 ** 2 * 4.43e-3      # g per mm of M5 Ti shank (d 4.5 mean, rho 4.43)


def _alu() -> dict:
    from huntkit.materials import load
    a = load("alu_6061_t6")
    return {"E": float(a.require("youngs_modulus_mpa")), "fy": float(a.require("yield_strength_sbasis_mpa")),
            "rho": float(a.require("density_kg_m3")) * 1e-6}


def screw_length(boss_depth: float = BOSS_DEPTH) -> dict:
    """Shortest stock DIN 7984 length with >= 2 threads (1.6 mm) proud of the nut: flange 3 + boss + ring + nut."""
    stack = FLANGE_T + boss_depth + RING_T + NUT_M
    L = next(v for v in SCREW_LS if v - stack >= MIN_PROTRUDE_THREADS * PITCH - 1e-9)
    return {"stack_mm": stack, "screw_l_mm": L, "protrusion_mm": round(L - stack, 2),
            "protrusion_threads": round((L - stack) / PITCH, 2), "bl070_l_mm": 20.0, "bl070_protrusion_mm":
            round(20.0 - (FLANGE_T + P.NUT_SEAT_DEPTH + NUT_M), 2)}


def hetenyi(t: float = RING_T, E_found: float = 4300.0, depth: float = BOSS_DEPTH) -> dict:
    """Ring on the boss as a beam on a Winkler foundation (Hetenyi): k0 = E_found / depth (MPa/mm), beta =
    (3 k0 / (E_al t^3))^0.25; one nut load P gives a peak pressure P beta / (2 b) under it; the group of 4 at the
    arc pitch adds f(beta s) = exp(-beta s)(cos + sin) from each neighbour (inner bolt: 2 at s, 1 at 2 s)."""
    al = _alu()
    k0 = E_found / depth
    beta = (3.0 * k0 / (al["E"] * t ** 3)) ** 0.25
    s = 19.0 * math.radians(28.0)                     # arc pitch of the split pattern (step 28 deg on r 19)
    f = lambda x: math.exp(-beta * x) * (math.cos(beta * x) + math.sin(beta * x))   # noqa: E731
    G = 1.0 + 2 * f(s) + f(2 * s)
    b = (RING_OD - RING_ID) / 2.0
    return {"k0": round(k0, 1), "beta": round(beta, 4), "group_factor": round(G, 3), "b": b,
            "mpa_per_n": beta * G / (2.0 * b), "char_len_mm": round(1 / beta, 2)}


def hip_plate(mat: str = MAT) -> dict:
    """B-1: the hip through-bolt joint on a real bearing geometry (no traps), on the hot/wet allowable.
    Rows (per bolt, the BL-055 tipping model T from h1_closeout.hip_check, H on the pin and on the frame):
    - strength: bearing pressure under the ring at (max preload + T_C2) <= knock x Z;
    - fatigue: 0.30 x allowable / pressure at T_walk (0 -> peak, no preload credit for the cyclic part);
    - creep: 0.55 x allowable / pressure at max(max preload, T_carry);
    - Ti screw (0.7 UTS, 0.25 UTS fatigue); nut face on the ring (6061-T6 S-basis yield); ring shear-out.
    Bearing pressure = the Hetenyi peak at the cold (stiffest) foundation, or the uniform ring average, the larger.
    Preload: T = K F d with K 0.14-0.26; relaxation by series springs (Ti screw, PPA boss at hot/wet x CREEP_LONG);
    cold loss from the CTE mismatch."""
    from . import frame_h1 as H1
    from . import h1_closeout as C
    m = P.materials()[mat]
    r = P.ppa_record()
    al = _alu()
    allow = m["knock"] * m["s_z"]
    hip = P.hip_inserts(mat)
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    # T per row (the tipping model does not depend on the fastener): take them from the abs_z run
    C_rows = C.hip_check(pat, True)["rows"]
    ring_a = math.pi / 4 * (RING_OD ** 2 - RING_ID ** 2) - 8 * math.pi / 4 * HOLE_D ** 2
    het = hetenyi(E_found=r["E_z"] * 1.25)          # cold foundation (modulus_minus20c 1.25): the most peaked
    p_per_n = max(het["mpa_per_n"], 8.0 / ring_a)
    d = 5.0
    F = {k: TORQUE_NM / (kk * d * 1e-3) for k, kk in (("nom", K_NOM), ("max", K_LO), ("min", K_HI))}
    ti_t, ti_f = 0.7 * H1.TI["uts"] * H1.TI["As"], 0.25 * H1.TI["uts"] * H1.TI["As"]
    a_dw = math.pi / 4 * (NUT_DW ** 2 - HOLE_D ** 2)
    rows = {}
    for k, v in C_rows.items():
        T, kind = v["T_max_n"], v["kind"]
        if kind == "strength":
            p_ = p_per_n * (F["max"] + T)
            sf = min(allow / p_, ti_t / (F["max"] + T), al["fy"] / ((F["max"] + T) / a_dw))
        elif kind == "fatigue":
            sf = min(m["fat"] * allow / (p_per_n * T), ti_f / T)
            p_ = p_per_n * T
        else:
            p_ = p_per_n * max(F["max"], T)
            sf = m["rup"] * allow / p_
        rows[k] = {"T_max_n": T, "kind": kind, "pressure_mpa": round(p_, 2), "sf": round(sf, 2), "goal": v["goal"]}
    gov = {kd: min(q["sf"] for q in rows.values() if q["kind"] == kd) for kd in ("strength", "fatigue", "creep")}
    # preload relaxation and cold loss (per bolt)
    grip = FLANGE_T + BOSS_DEPTH + RING_T
    kb = H1.TI["E"] * H1.TI["As"] / (grip + 0.8 * d)                 # + 0.4 d head + 0.4 d nut (VDI 2230 style)
    a_m = ring_a / 8.0
    E_hw = r["E_z"] * r["E_hot_hw"]
    km0 = E_hw * a_m / BOSS_DEPTH
    kmt = km0 * CREEP_LONG
    resid = (1 / kb + 1 / km0) / (1 / kb + 1 / kmt)
    km_cold = r["E_z"] * 1.25 * a_m / BOSS_DEPTH
    k_ser_cold = 1 / (1 / kb + 1 / km_cold)
    dT = 23.0 - T_COLD
    shrink = ((CTE_Z - CTE_TI) * BOSS_DEPTH + (CTE_AL - CTE_TI) * RING_T) * dT
    cold_loss = shrink * k_ser_cold
    walk = max(q["T_max_n"] for q in rows.values() if q["kind"] == "fatigue")
    c2 = max(q["T_max_n"] for q in rows.values() if q["kind"] == "strength")
    sl = screw_length()
    ring_g = ring_a * RING_T * al["rho"]
    hw = {"screws_extra_g": round(8 * (sl["screw_l_mm"] - 20.0) * TI_MM_G, 2), "ring_g": round(ring_g, 2),
          "keeper_g": 3.58}       # hip_parts(): printed PPA-CF nut keeper 48.5 / 24 x 3 (2 pockets)
    return {"mat": mat, "allow_mpa": round(allow, 2), "hetenyi": het, "ring_area_mm2": round(ring_a, 1),
            "pressure_mpa_per_kn": round(p_per_n * 1e3, 2), "torque_nm": TORQUE_NM,
            "preload_n": {k: round(v, 0) for k, v in F.items()},
            "nut_factor": {"nominal": K_NOM, "range": [K_LO, K_HI]},
            "rows": rows, "min_sf": gov,
            "pass": all(q["sf"] >= q["goal"] for q in rows.values()),
            "relaxation": {"kb_n_mm": round(kb), "km0_n_mm": round(km0), "creep_long_ratio": CREEP_LONG,
                           "residual_fraction": round(resid, 3),
                           "residual_preload_min_n": round(F["min"] * resid, 0),
                           "walk_bolt_tension_n": walk, "c2_bolt_tension_n": c2,
                           "closed_at_walk": bool(F["min"] * resid > walk)},
            "cold": {"dT": dT, "shrink_mm": round(shrink, 4), "k_series_n_mm": round(k_ser_cold),
                     "preload_loss_n": round(cold_loss, 0), "slack_at_minus20": bool(cold_loss >= F["max"])},
            "screw": sl, "hardware_g": hw,
            "webs": {"between_holes_mm": round(pat["pitch_mm"] - HOLE_D, 2),
                     "hole_to_boss_edge_mm": round(50.0 / 2 - 19.0 - HOLE_D / 2, 2),
                     "ring_outer_ligament_mm": round(RING_OD / 2 - 19.0 - HOLE_D / 2, 2),
                     "ring_inner_ligament_mm": round(19.0 - HOLE_D / 2 - RING_ID / 2, 2), "traps": 0},
            "hardware": f"8 x Ti gr5 M5 x {sl['screw_l_mm']:g} DIN 7984 + 8 x A2 M5 DIN 934 nuts (Loctite 243) on one "
                        f"6061-T6 bearing ring {RING_OD:g} / {RING_ID:g} x {RING_T:g} mm (8 holes D{HOLE_D:g} on r 19, "
                        f"the mount pattern) and a printed PPA-CF nut keeper (3 mm, holds the nuts while the screws are "
                        f"turned from the mount side) replace 8 x M5 x 9.5 brass inserts + 8 x M5 x 12; torque "
                        f"{TORQUE_NM} N m",
            "hip_rows_source": "h1_closeout.hip_check T (BL-055 tipping model, FLANGE-RIGID)",
            "bl070_dw_ring_check": {"a_dw_mm2": round(a_dw, 1),
                                    "fatigue_on_dw_bl069_basis": round(0.30 * 0.73 * 45 * a_dw / walk, 2),
                                    "fatigue_on_dw_hw": round(m["fat"] * allow * a_dw / walk, 2)}}


def add_hip_plate(man, log=print, stats: dict | None = None):
    """Export hook (replaces bl070_h1p.add_hip_through): the D50 boss from the wearer face to a flat back BOSS_DEPTH
    behind it, spot face SPOT_D aft of the flat, 8 x D5.5 through holes, no traps."""
    from . import h1_closeout as C
    from . import h1_rev5 as R5
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    cx, cz = C.HIP_C
    D = C.HIP_CHOSEN[2]
    probe = man ^ R5._box_m((cx - 10.0, -80.0, cz - 10.0), (cx + 10.0, -20.0, cz + 10.0))
    y_face = float(probe.bounding_box()[1])
    y0 = y_face - 0.05
    v0 = man.volume()
    y_back = y_face + BOSS_DEPTH
    man = man + C._cyl_y(cx, cz, y0, y_back, D)
    v1 = man.volume()
    man = man - C._cyl_y(cx, cz, y_back, y_back + 40.0, SPOT_D)
    v2 = man.volume()
    for x, z in pat["positions_xz"]:
        man = man - C._cyl_y(x, z, y0 - 1.0, y_back + 1.0, HOLE_D, 48)
    v3 = man.volume()
    st = {"y_face": round(y0, 3), "y_back": round(y_back, 3), "boss_added_mm3": round(v1 - v0, 1),
          "spot_face_cut_mm3": round(v1 - v2, 1), "holes_cut_mm3": round(v2 - v3, 1),
          "pattern": pat["positions_xz"], "traps": 0}
    if stats is not None:
        stats.update(st)
    if log:
        log(f"  BL-073 hip boss D{D:g} to a flat back {BOSS_DEPTH} mm deep, spot face D{SPOT_D:g}, 8 x D{HOLE_D} "
            f"through holes, no traps")
    return man


# z 234 joint (B-2 re-tune): on the hot/wet basis the BL-070 joint reads fatigue 0.78 (boss bending + prying, its
# interlayer xy term). Moving the bolts toward the stay mid-plane cuts that term (joint_var: g1 cut sections, every
# rev C set): outboard (16.4, 10) -> (18.5, 6), inboard (-19, 5) -> (-19, 5.5). Same hardware (M5 x 45 Ti, washers,
# DIN 934 nuts), bosses inside frame_h1.boss_envelope, bore ligaments >= the 3.6 mm floor (frame_h1.bore_continuity).
JOINT_XY = ((18.5, 6.0), (-19.0, 5.5))
JOINT_XY_BL070 = ((16.4, 10.0), (-19.0, 5.0))


@contextlib.contextmanager
def plate_hook():
    """The BL-073 hip boss and the z 234 bolt positions, for the export and the checks."""
    from . import frame_h1 as H1
    saved = (P.add_hip_through, H1.JOINT.xy)
    try:
        P.add_hip_through = add_hip_plate
        H1.JOINT.xy = JOINT_XY
        yield
    finally:
        P.add_hip_through, H1.JOINT.xy = saved


# ================================================================================================ hip ring + nut keeper
KEEPER_T = 3.0             # printed PPA-CF nut keeper (holds the 8 nuts while the screws are torqued from the mount side)
KEEPER_AF = 8.2            # DIN 934 M5 s 8.0 + 0.2 play
KEEPER_OD = SPOT_D - 0.5   # the keeper fills the spot face (the ring is 47)


def hip_parts(out_dir: Path | None = None) -> dict:
    """The bearing ring (DXF for laser / waterjet cutting + STL for review) and the nut keeper (STL, print flat).
    Positions in the ring's own frame: x = frame x, y = frame z - 120 (the boss axis), seen from the bag side."""
    import ezdxf
    import manifold3d as m3d
    import trimesh
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    from . import h1_closeout as C
    d = out_dir or P.STL_DIR
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    pos = [(x - C.HIP_C[0], z - C.HIP_C[1]) for x, z in pat["positions_xz"]]
    doc = ezdxf.new("R2010")
    doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    msp.add_circle((0, 0), RING_OD / 2)
    msp.add_circle((0, 0), RING_ID / 2)
    for x, y in pos:
        msp.add_circle((x, y), HOLE_D / 2)
    msp.add_text(f"BL-073 hip bearing ring 6061-T6 {RING_T:g} mm, OD {RING_OD:g} ID {RING_ID:g}, 8 x D{HOLE_D:g}",
                 dxfattribs={"height": 2.0}).set_placement((-RING_OD / 2, -RING_OD / 2 - 6))
    doc.saveas(d / "hip_bearing_ring.dxf")
    ring = (m3d.Manifold.cylinder(RING_T, RING_OD / 2, RING_OD / 2, 128)
            - m3d.Manifold.cylinder(RING_T + 2, RING_ID / 2, RING_ID / 2, 96).translate((0, 0, -1)))
    for x, y in pos:
        ring = ring - m3d.Manifold.cylinder(RING_T + 2, HOLE_D / 2, HOLE_D / 2, 48).translate((x, y, -1))
    # keeper: the ring outline less one pocket per group = the union of its 4 hexes (flats facing the neighbour)
    import math as _m
    hexes = []
    for x, y in pos:
        a0 = _m.atan2(y, x)
        R = KEEPER_AF / _m.sqrt(3)
        hexes.append(Polygon([(x + R * _m.cos(a0 + _m.pi / 6 + k * _m.pi / 3),
                               y + R * _m.sin(a0 + _m.pi / 2 + k * _m.pi / 3)) for k in range(6)]))
    from shapely.geometry import LineString
    chans = [LineString(pos[:4]).buffer(3.0), LineString(pos[4:]).buffer(3.0)]   # one pocket per group of 4
    pockets = unary_union(hexes + chans)
    outline = Point(0, 0).buffer(KEEPER_OD / 2, 128).difference(Point(0, 0).buffer(RING_ID / 2, 96)).difference(pockets)
    polys = list(getattr(outline, "geoms", [outline]))
    keeper = None
    for pg in polys:
        cs = m3d.CrossSection([list(pg.exterior.coords)[:-1]] + [list(h.coords)[:-1] for h in pg.interiors],
                              m3d.FillRule.EvenOdd)
        k_ = m3d.Manifold.extrude(cs, KEEPER_T)
        keeper = k_ if keeper is None else keeper + k_
    out = {}
    for nm, man in (("hip_bearing_ring", ring), ("hip_nut_keeper", keeper)):
        mm = man.to_mesh()
        tm = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=True)
        tm.export(d / f"{nm}.stl")
        out[nm] = {"volume_mm3": round(float(man.volume()), 1), "watertight": bool(tm.is_watertight)}
    al = _alu()
    out["hip_bearing_ring"]["g"] = round(out["hip_bearing_ring"]["volume_mm3"] * al["rho"], 2)
    out["hip_nut_keeper"]["g"] = round(out["hip_nut_keeper"]["volume_mm3"] * P.RHO_PPA, 2)
    out["keeper_pockets"] = len(list(getattr(pockets, "geoms", [pockets])))
    out["keeper_min_wall_mm"] = round(min(KEEPER_OD / 2 - max(_m.hypot(x, y) for x, y in pos) - KEEPER_AF / 2,
                                          min(_m.hypot(x, y) for x, y in pos) - KEEPER_AF / 2 - RING_ID / 2), 2)
    out["files"] = [str((d / f).relative_to(REPO)) for f in ("hip_bearing_ring.dxf", "hip_bearing_ring.stl",
                                                             "hip_nut_keeper.stl")]
    return out


# ================================================================================================ design loop (B-2)
LOOP_BASES = P.LOOP_BASES


def raster_of(name: str) -> np.ndarray:
    for d in (OUT, P.OUT):
        q = d / f"{name}_solid.npz"
        if q.exists():
            return np.load(q)["solid"]
    raise FileNotFoundError(name)


def util_hw(name: str, bases=LOOP_BASES, key: str = "util") -> np.ndarray:
    return P.util_field(name, MAT, bases, key=key)


def export_step_hw(prev: str, name: str, u_lo: float, u_hi: float, n_thin: int = 1, grow: bool = True,
                   log=print, orient: bool = False) -> dict:
    """bl070_h1p.export_step on the ppa_hw utilisation, with the BL-073 hip boss (add_hip_plate). ``prev`` is a
    checked export raster (OUT or bl070 OUT). The checked raster is saved OUT/<name>_solid.npz; check cached in
    bl070 OUT as check_<name>_ppa_hw.json (+ util files)."""
    import trimesh
    OUT.mkdir(parents=True, exist_ok=True)
    ps = raster_of(prev)
    u = util_hw(prev)
    d, _r0, add = P.resize_step(ps, u, 0.0, u_hi, grow=grow, thin=False)
    d, rem, _a = P.resize_step(d, u, u_lo, 99.0, grow=False, thin=n_thin > 0, keep=add)
    for _ in range(max(n_thin - 1, 0)):
        d, r2, _a = P.resize_step(d, u, u_lo, 99.0, grow=False, thin=True, keep=add)
        rem |= r2
    fused = []
    with plate_hook():
        for _ in range(4):
            try:
                info = P.export(d, log=None)
                break
            except RuntimeError as e:
                pts = P.pinch_points(P.STL_DIR / "h1_assembled.stl")
                if not pts:
                    raise
                cen = FI._base()["cen"]
                for q in pts:
                    f = (np.linalg.norm(cen - q, axis=1) < 3.5) & P.allowed_add()
                    d = d | f
                    fused.append({"at_mm": [round(float(v), 1) for v in q], "voxels": int(f.sum())})
        np.savez_compressed(OUT / f"{name}_design.npz", solid=d)
        rr, rinfo = P.reraster()
        np.savez_compressed(OUT / f"{name}_solid.npz", solid=rr)
        (OUT / f"{name}_export_info.json").write_text(json.dumps(info, default=FI._jd, indent=1))
        res = P.check_body(name, rr, bases=P.BASES, mat=MAT, log=log, orient=orient)
    m = trimesh.load(P.STL_DIR / "h1_assembled.stl", force="mesh")
    res["step"] = {"prev": prev, "u_lo": u_lo, "u_hi": u_hi, "grow": grow, "n_thin": n_thin, "basis": MAT,
                   "pinches_fused": fused, "removed": int(rem.sum()), "added": int(add.sum()),
                   "body_g_ppa": round(m.volume * P.RHO_PPA, 1), "lower_g": round(info["lower"]["g_ppa"], 1)
                   if "g_ppa" in info.get("lower", {}) else None,
                   "design_not_in_export": int((d & ~rr).sum()), "export_not_in_design": int((rr & ~d).sum())}
    (P.OUT / f"check_{name}_{MAT}.json").write_text(json.dumps(res, default=FI._jd))
    if log:
        sm = P.summary(res)
        log(f"  {name}: body {res['step']['body_g_ppa']} g, R1 {sm['cinch_cycled']['fatigue']:.3f}, joint fat "
            f"{min(sm['static_cinch']['joint_fatigue'], sm['cinch_cycled']['joint_fatigue']):.3f}, static fat "
            f"{sm['static_cinch']['fatigue']:.3f}, strength {sm['static_cinch']['strength']:.3f}")
    return res


# ================================================================================================ printability (M-5, M-6)
PAD_FOOT_D, PAD_FOOT_T = 24.0, 0.6      # mouse-ear foot on the plate (brim-like, peeled off)
PAD_COL_D = 12.0                         # column
PAD_NECK_D0, PAD_NECK_D1, PAD_NECK_H = 6.0, 3.0, 1.6   # snap-off neck: cone D6 -> D3 into the part (0.6 mm overlap)
PAD_MAX_H = 40.0                         # no pad taller than this (a slender column wobbles)
PAD_MIN_SEP = 60.0                       # mm between pads and from the existing plate contact
LAYER_H = 0.30                           # ASSUMPTION LAYER-H: Bambu Studio "0.30 mm Standard" for the 0.6 nozzle
SPOOL_NET_G = 750.0                      # Bambu PPA-CF: 0.75 kg net only (record source, 2026-11-25)
SPOOL_RESERVE_G = 60.0                   # ASSUMPTION SPOOL-RESERVE: purge + net-weight tolerance kept on each spool


def underside(flat, h: float = 2.0) -> dict:
    """Height map of the part's underside (lowest downward-facing point per h x h cell) of a laid-flat half."""
    c = flat.triangles_center
    dn = flat.face_normals[:, 2] < -0.3
    ij = np.floor(c[dn, :2] / h).astype(int)
    z = c[dn, 2]
    cells: dict = {}
    for (i, j), zz in zip(map(tuple, ij), z):
        if zz < cells.get((i, j), 9e9):
            cells[(i, j)] = zz
    return {"h": h, "cells": cells}


def pad_sites(flat, n_max: int = 6) -> list:
    """Farthest-point choice of pad sites on the underside: cells 1 < z <= PAD_MAX_H whose 3 x 3 neighbourhood is
    underside too (a column can meet it), each >= PAD_MIN_SEP from the plate contact and from the other pads, the
    farthest first, until none is left or n_max."""
    U = underside(flat)
    h, cells = U["h"], U["cells"]
    on = np.array([[(i + 0.5) * h, (j + 0.5) * h] for (i, j), z in cells.items() if z < 0.3]).reshape(-1, 2)
    cand = []
    for (i, j), z in cells.items():
        if not (1.0 < z <= PAD_MAX_H):
            continue
        nb = [cells.get((i + a, j + b)) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if any(v is None for v in nb) or max(nb) - min(nb) > 3.0:
            continue
        cand.append(((i + 0.5) * h, (j + 0.5) * h, float(max(nb))))
    cand = np.array(cand)
    sites = []
    ref = on.copy()
    for _ in range(n_max):
        if len(cand) == 0:
            break
        d = np.min(np.linalg.norm(cand[:, None, :2] - ref[None, :, :], axis=2), axis=1) if len(ref) else \
            np.full(len(cand), 1e9)
        k = int(np.argmax(d))
        if d[k] < PAD_MIN_SEP:
            break
        sites.append([round(float(v), 1) for v in cand[k]])
        ref = np.vstack([ref, cand[k, :2]])
    return sites


def pad_mesh(x: float, y: float, z_top: float):
    """One sacrificial pad: foot disc, column, snap-off neck fused 0.6 mm into the part."""
    import manifold3d as m3d
    foot = m3d.Manifold.cylinder(PAD_FOOT_T, PAD_FOOT_D / 2, PAD_FOOT_D / 2, 64)
    zc = max(z_top - PAD_NECK_H + 0.6, PAD_FOOT_T + 0.5)
    col = m3d.Manifold.cylinder(zc, PAD_COL_D / 2, PAD_COL_D / 2, 48)
    neck = m3d.Manifold.cylinder(PAD_NECK_H, PAD_NECK_D0 / 2, PAD_NECK_D1 / 2, 32).translate((0.0, 0.0, zc))
    return (foot + col + neck).translate((x, y, 0.0))


def print_files(stl_dir: Path | None = None, log=print) -> dict:
    """h1_<half>_flat_print.stl = the flat half + its pads (the file to slice); the clean flat files are unchanged.
    Plate contact before / after, pad filament."""
    import manifold3d as m3d
    import trimesh
    d = stl_dir or P.STL_DIR
    out = {}
    for nm in ("lower", "upper"):
        f = trimesh.load(d / f"h1_{nm}_flat.stl", force="mesh")
        sites = pad_sites(f)
        part = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(f.vertices, np.float32),
                                     tri_verts=np.asarray(f.faces, np.uint32)))
        pads = None
        for x, y, z in sites:
            p_ = pad_mesh(x, y, z)
            pads = p_ if pads is None else pads + p_
        allm = part + pads if pads is not None else part
        mm = allm.to_mesh()
        tm = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=True)
        tm.export(d / f"h1_{nm}_flat_print.stl")
        pad_v = float(allm.volume() - part.volume())
        out[nm] = {"sites_xyz_mm": sites, "n_pads": len(sites),
                   "plate_contact_part_mm2": round(P.flat_contact_mm2(f), 0),
                   "plate_contact_with_pads_mm2": round(P.flat_contact_mm2(tm), 0),
                   "pad_g": round(pad_v * P.RHO_PPA, 1), "watertight": bool(tm.is_watertight),
                   "contact_span_mm": None}
        on = tm.triangles_center[(tm.triangles_center[:, 2] < 0.05) & (tm.face_normals[:, 2] < -0.99)]
        if len(on):
            out[nm]["contact_span_mm"] = [round(float(v), 0) for v in (on[:, :2].max(0) - on[:, :2].min(0))]
        out[nm]["part_extent_mm"] = [round(float(v), 0) for v in f.extents[:2]]
        if log:
            log(f"  {nm}: {len(sites)} pads, contact {out[nm]['plate_contact_part_mm2']} -> "
                f"{out[nm]['plate_contact_with_pads_mm2']} mm2, +{out[nm]['pad_g']} g")
    return out


def layer_profile(flat, dz: float = LAYER_H) -> dict:
    """Cross-section area per print layer of a laid-flat half (z = print height = frame y - y_min)."""
    zs = np.arange(dz / 2, flat.bounds[1][2], dz)
    secs = flat.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(zs))
    area = np.array([s.area if s is not None else 0.0 for s in secs])
    return {"z": zs, "area": area}


def spool_plan(name: str, prfiles: dict, log=print) -> dict:
    """M-6: one planned filament change per half (Bambu Studio 'change filament' / pause at a layer: the H2S cannot
    auto-refill PPA-CF, it is not AMS compatible). Window: the layer where spool 1 has used <= 750 - reserve (part
    + support high bound + pads, cumulated with height; supports booked low for the upper bound) and spool 2 can
    finish the rest. In the window, the layer plane (frame y = y_min + z) with the least interlayer-shear
    utilisation is chosen: max and p99 of the cinch-cycled fatigue utilisation and of the strength envelope over
    the voxels whose centre is within 1 mm of the plane, per half."""
    import trimesh
    cen = FI._base()["cen"]
    sol = raster_of(name)
    fat = np.zeros(len(cen))
    env = np.zeros(len(cen))
    for b in P.BASES:
        z_ = np.load(P.OUT / f"util_{name}_{MAT}_{b}.npz")
        fat[z_["idx"]] = np.maximum(fat[z_["idx"]], z_["fat_u"])
        env[z_["idx"]] = np.maximum(env[z_["idx"]], z_["env"])
    out = {}
    for nm in ("lower", "upper"):
        f = trimesh.load(P.STL_DIR / f"h1_{nm}_flat.stl", force="mesh")
        lp = layer_profile(f)
        part_cum = np.cumsum(lp["area"] * LAYER_H) * P.RHO_PPA * P.WASTE
        pr = prfiles.get(nm, {})
        pinfo = PRINT_INFO.get(nm, {})
        sup_g = pinfo.get("support_g_ppa_high", 0.0) * P.WASTE
        pad_g = pr.get("pad_g", 0.0) * P.WASTE
        total = part_cum[-1] + sup_g + pad_g
        cap = SPOOL_NET_G - SPOOL_RESERVE_G
        # spool-1 use at layer z: lower bound = part only; upper bound = part + all support + pads
        lo_use = part_cum
        hi_use = part_cum + sup_g + pad_g
        ok = (hi_use <= cap) & (total - lo_use <= cap)
        half = (cen[:, 2] < P.SPLIT_Z) if nm == "lower" else (cen[:, 2] >= P.SPLIT_Z)
        sel = sol & half
        ymin = float(cen[sel, 1].min()) - FI.H / 2
        rows = []
        for k in np.where(ok)[0]:
            y = ymin + lp["z"][k]
            pl = sel & (np.abs(cen[:, 1] - y) <= 1.0)
            if pl.sum() < 10:
                continue
            rows.append({"print_z_mm": round(float(lp["z"][k]), 2), "layer": int(k + 1), "frame_y_mm": round(y, 2),
                         "spool1_g_range": [round(float(lo_use[k]), 0), round(float(hi_use[k]), 0)],
                         "fat_u_max": round(float(fat[pl].max()), 3), "fat_u_p99": round(float(np.percentile(fat[pl], 99)), 3),
                         "env_max": round(float(env[pl].max()), 3)})
        best = min(rows, key=lambda r: (r["fat_u_max"], r["env_max"])) if rows else None
        prof = [{"frame_y_mm": round(ymin + float(z), 1), "fat_u_max": round(float(fat[sel & (np.abs(cen[:, 1] - (ymin + z)) <= 1.0)].max()), 3)
                 if (sel & (np.abs(cen[:, 1] - (ymin + z)) <= 1.0)).any() else 0.0}
                for z in lp["z"][::7]]
        out[nm] = {"filament_total_g": round(float(total), 0), "spools": round(float(total) / SPOOL_NET_G, 2),
                   "window_print_z_mm": [rows[0]["print_z_mm"], rows[-1]["print_z_mm"]] if rows else None,
                   "swap": best, "global_fat_u_max_half": round(float(fat[sel].max()), 3),
                   "profile": prof}
        if log and best:
            log(f"  {nm}: swap at print z {best['print_z_mm']} mm (layer {best['layer']}), frame y "
                f"{best['frame_y_mm']}, layer-plane fatigue util max {best['fat_u_max']} (half max "
                f"{out[nm]['global_fat_u_max_half']})")
    return out


PRINT_INFO: dict = {}


# ================================================================================================ sensitivity (M-1)
def tornado(M: dict, share_il: dict, joint_e: dict | None = None) -> list:
    """Single-assumption variations on the governing rows. ``M``: row -> margin on the ppa_hw basis; ``share_il``:
    row -> share of the margin carried by the interlayer-shear terms (body rows: the top-1 % term shares; the z 234
    boss bending row: 1.0, its xy term governs; bearing rows 0). Each variation scales a row as
    margin / sum(share_t x (allowable_t / allowable_t,new)). ``joint_e``: z 234 joint fatigue at E_hot 0.50 (re-run).
    Returns rows {variation, source, retired_by, rows: {row: new margin}}."""
    fat = {k for k in M if "fatigue" in k or k == "R1"}
    zrows = {k for k in M if k not in ("buckling",)}
    var = [
        ("fatigue ratio 0.25 (was 0.30)", "low end of the PA12-CF15 range the record cites (Sofia 0.25-0.32)",
         "CA-1-HW (SBS shear fatigue at 40 C, conditioned)", lambda k: 0.25 / 0.30 if k in fat else 1.0),
        ("interlayer shear 0.55 x Z (was 0.6)", "no PPA source for 0.6 (INTERLAYER-0.6)", "CA-3-HW SBS",
         lambda k: 1.0 / (share_il.get(k, 0.0) * 0.6 / 0.55 + 1.0 - share_il.get(k, 0.0))),
        ("hot 40 C ratio 0.82 (was 0.85)", "ForTii Tg drop on the matrix water (the harshest Tg reading)",
         "CA-3-HW (Z and SBS at 40 C)", lambda k: 0.82 / 0.85 if k in zrows else 1.0),
        ("wet loss on Z = conditioned modulus ratio 0.66 (was the XY strength ratio 0.73)",
         "Raise3D E 7800 / Bambu 11800: a matrix-dominated ratio", "CA-3-HW (conditioned vs dry Z)",
         lambda k: 1.0 / (share_il.get(k + "|z", share_il.get(k, 0.0)) * 0.73 / 0.66 + 1.0
                          - share_il.get(k + "|z", share_il.get(k, 0.0)))),
        ("design Z on n 6 coupons, k 3.01 (was the TDS n 5, k 3.41)", "the owner's batch at n 6", "CA-3-HW at n 10",
         lambda k: (57 - 3.0063 * 5) / (57 - 3.4066 * 5) if k in zrows and k not in ("clevis fatigue (share 0.6)",) else 1.0),
        ("hot/wet modulus 0.50 (was 0.5876)", "a further 15 % modulus loss", "CA-4-HW (E at 40 C conditioned)",
         lambda k: 0.50 / 0.5876 if k == "buckling" else (joint_e.get(k, M[k]) / M[k] if joint_e and k in joint_e else 1.0)),
    ]
    out = []
    for lab, src, ret, f in var:
        out.append({"variation": lab, "source": src, "retired_by": ret,
                    "rows": {k: round(v * f(k), 3) for k, v in M.items()}})
    return out


def plot_tornado(M: dict, tor: list, path: Path, title: str) -> str:
    """Margin bars: base and the single-assumption variations per governing row (phone readable)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = list(M)
    fig, ax = plt.subplots(figsize=(8.0, 9.5), dpi=110)
    y = np.arange(len(rows))[::-1]
    for i, k in enumerate(rows):
        vals = [t["rows"][k] for t in tor]
        lo, hi = min(vals + [M[k]]), max(vals + [M[k]])
        ax.plot([lo, hi], [y[i], y[i]], color="#9aa3ad", lw=6, solid_capstyle="butt", zorder=1)
        for t, v in zip(tor, vals):
            if v < M[k] - 1e-6:
                ax.plot(v, y[i], "|", color="#c0392b", ms=14, mew=2, zorder=2)
        ax.plot(M[k], y[i], "o", color="#1f5fbf", ms=8, zorder=3)
        ax.text(min(max(hi, M[k]), 2.9) + 0.04, y[i], f"{M[k]:.2f} (worst {lo:.2f})", va="center", fontsize=8)
    ax.axvline(1.0, color="#c0392b", lw=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(rows, fontsize=8.5)
    ax.set_xlim(0.5, 3.3)
    ax.set_xlabel("margin on the hot/wet B-basis (1.0 = at the allowable; dot = design, red ticks = one worse assumption)")
    ax.set_title(title, fontsize=10)
    leg = "\n".join(f"{i + 1}. {t['variation']} -> {t['retired_by']}" for i, t in enumerate(tor))
    fig.text(0.02, 0.01, leg, fontsize=6.8, va="bottom")
    fig.subplots_adjust(left=0.33, bottom=0.2, top=0.93, right=0.97)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    P.shrink_png(Path(path))
    return str(path)


# ================================================================================================ coupons (M-3, M-4, M-7, M-8)
SBS_G = {"L": 24.0, "w": 8.0, "t": 4.0, "span": 16.0}      # ASTM D2344: L 6t, w 2t, span 4t
ISO1A_MM3 = 170.0 * 10.0 * 4.0 + 2 * 45.0 * 10.0 * 4.0       # ~1A bar volume (gauge 10 wide, shoulders 20 wide)
FLEX_MM3 = 80.0 * 10.0 * 4.0
T4B_J = 68.0 * 9.81 * 0.050                                  # HA-LS-1 T4b: 68 kg dropped 50 mm onto one foot
SALT_RH_50C = 74.4                                           # NaCl saturated, 50 C (Greenspan, J. Res. NBS 81A, 1977)


def layer_time_s(flat, rate_mm3_s: float = 8.0, k: float = 1.08) -> dict:
    """Median / 10th percentile layer time of a laid-flat half by the BL-053 volume-rate rule."""
    lp = layer_profile(flat)
    t = lp["area"] * LAYER_H / rate_mm3_s * k
    t = t[t > 0]
    return {"median_s": round(float(np.median(t)), 0), "p10_s": round(float(np.percentile(t, 10)), 0),
            "layers": int(len(t))}


def coupons_hw(M: dict, b: dict, lt: dict) -> list:
    """Register rows for the hot/wet basis (written to bl070_h1p.json 'coupons_bl073'; the BL-070 'coupons' rows stay
    as they were). ``M``: governing margins on ppa_hw; ``b``: basis(); ``lt``: layer_time_s of each half."""
    zk = b["z_knocked_hw"]
    tau = b["tau_il_hw"]
    k10 = b["k_n10"]
    m_fat = min(M["R1"], M["z 234 joint fatigue"], M["US2 lug fatigue"] / 1.15,
                M["US2 clevis fatigue (share 0.6)"] / 1.15, M["hip mount fatigue"] / 1.15)
    m_z = min(M["R1"], M["z 234 joint fatigue"])
    s_des = 0.30 * tau / m_fat
    s_test = 1.15 * s_des
    p_sbs = s_test * SBS_G["w"] * SBS_G["t"] / 0.75
    need_z = zk / m_z
    lt_med = min(v["median_s"] for v in lt.values())
    cond = (f"conditioned to constant mass at 50 C over saturated NaCl ({SALT_RH_50C} % RH, Greenspan 1977; above the "
            f"TDS 55 % RH, so conservative): weigh daily, done when the mass changes < 0.1 % in 24 h (ISO 62 "
            f"practice); record the uptake against the TDS 1.30 %")
    block = (f"cut from a solid block printed on the H2S with the frame profile beside a dummy tower sized so every "
             f"layer takes >= {lt_med:.0f} s (the median layer time of a frame half by the BL-053 rule, "
             f"LAYER-H 0.3 mm); log the layer time of each batch from the slicer preview")
    return [
        {"id": "CA-1-HW", "replaces": "CA-1-PPA (review 8 M-3)",
         "what": "short-beam-shear FATIGUE (the governing interlayer mode, shear_xy): ASTM D2344 bars "
                 f"{SBS_G['L']:g} x {SBS_G['w']:g} x {SBS_G['t']:g}, span {SBS_G['span']:g}, mid-plane on a layer "
                 f"interface, {block}; {cond}; tested at 40 +/- 2 C, R 0.1, <= 5 Hz",
         "coupons": "6 SBS fatigue + 3 SBS static from the same block (+ 6 Z-tension R 0.1 bars kept from CA-1-PPA "
                    "for the layer-normal share)",
         "load": f"Smax (shear) = 1.15 x {s_des:.2f} = {s_test:.2f} MPa, i.e. peak load {p_sbs:.0f} N "
                 f"({p_sbs / 4.448:.0f} lbf) on the SBS jig (tau = 0.75 P / (b h)); {s_des:.2f} MPa = 0.30 x "
                 f"interlayer {tau:.2f} MPa / governing fatigue margin {m_fat:.3f}",
         "pass": "all 6 run out to 1e5 cycles at 1.15 x Smax (life factor by load: the 1.15 load factor on a "
                 "Basquin slope of about 10 is about a factor 4 on life, review 8 M-3); the 3 static SBS >= the "
                 "CA-3-HW SBS line",
         "settles": "FAT-PPA (0.30) in the governing shear mode, hot/wet",
         "margin_tied": f"min(R1 {M['R1']:.3f}, joint {M['z 234 joint fatigue']:.3f}, lug / 1.15, clevis(0.6) / 1.15, "
                        f"hip / 1.15) = {m_fat:.3f}",
         "smax_design_mpa": round(s_des, 3), "smax_test_mpa": round(s_test, 3), "peak_load_n": round(p_sbs, 0)},
        {"id": "CA-3-HW", "replaces": "CA-3-PPA (review 8 B-2, M-4, M-6)",
         "what": f"Z tensile (ISO 527-2 1A, standing, tied in threes) and SBS (ASTM D2344), {block}; hot/wet set "
                 f"{cond}, tested at 40 +/- 2 C; dry set as printed (sealed, tested within 24 h at 23 C); plus 6 "
                 "SBS with a planned 20 min pause at the mid-plane layer (the spool-change layer, M-6)",
         "coupons": "hot/wet: 10 Z + 10 SBS; dry: 6 Z + 6 SBS; pause-layer: 6 SBS (hot/wet)",
         "statistic": f"B-basis = mean - k SD, k {k10:.3f} at n 10 (one-sided 90/95 normal tolerance factor, "
                      "CMH-17-1G Vol 1 8.3.4.3 / NIST e-Handbook 7.2.6.3)",
         "pass": f"(a) hot/wet Z B-basis >= {need_z:.1f} MPa (= {zk:.2f} / {m_z:.3f}, the interlayer-governed rows "
                 f"R1 and z 234 joint fatigue); (b) hot/wet SBS B-basis >= {0.6 * need_z:.1f} MPa (0.6 x (a)); (c) "
                 f"pause-layer SBS mean >= 0.9 x the no-pause hot/wet SBS mean and its B-basis >= (b); (d) for the "
                 f"record: uptake, hot/wet / dry Z (booked 0.73 x 0.85 = {b['knock_hw']:.3f} on the B-basis)",
         "settles": "WET-PPA 0.73, HOT-40 0.85, B-basis Z 39.97, INTERLAYER-0.6, the pause layer",
         "if_below": f"with a measured hot/wet B-basis Z_m: R1 = {M['R1']:.3f} x Z_m / {zk:.2f}, z 234 joint fatigue = "
                     f"{M['z 234 joint fatigue']:.3f} x Z_m / {zk:.2f} (LINEAR-Z); below {need_z:.1f} MPa hold the "
                     "build and grow the hot spot by the shortfall",
         "need_z_mpa": round(need_z, 2), "need_sbs_mpa": round(0.6 * need_z, 2)},
        {"id": "CA-4-HW", "replaces": "CA-4-PPA (review 8 M-8, m-8)",
         "what": f"ISO 178 3-point bend, XY bars 80 x 10 x 4: 23 C dry; 40 C {cond.split(':')[0]}; 60 C dry",
         "coupons": "5 per condition",
         "pass": f"(a) modulus, mean of 5: E(40 C conditioned) / E(23 C dry) >= {M['_e_need']:.2f} (the governing "
                 f"need: buckling {M['buckling']:.2f} at the booked 0.588 and the z 234 joint contact stiffness, "
                 f"re-run at E_hot 0.50 in the tornado); (b) flexural strength at 60 C dry, mean - 3.41 SD (n 5) >= "
                 f"{0.688 * 208:.0f} MPa (hot ratio 60 / 20 C 0.688, Fiberlogy; for the record, no row rests on it)",
         "settles": "modulus_40c_wet_hw 0.588 (E-SCALE), modulus_60c 0.75"},
        {"id": "T4b-PPA-COLD", "replaces": "adds to HA-LS-1 T4b on P1 (review 8 M-7)",
         "what": "the PPA frame's own T4b set-down after >= 4 h at -20 C (chest freezer; frame + bag, no load in the "
                 "freezer), loaded to 68 kg and dropped within 10 min of removal, at the end of the P1 sequence "
                 "before T2u",
         "coupons": "P1, 5 drops per foot",
         "load": f"68 kg (150 lb) from 50 mm (2 in) onto one stay foot: {T4B_J:.0f} J per drop",
         "pass": "HA-LS-1 T4b pass rule, and no crack along a layer (10x loupe on both stay feet, the hip boss and "
                 "the z 234 bosses)",
         "settles": "COLD on the frame (T4b energy, both halves)"},
        {"id": "T4c-PPA-COLD", "replaces": "adds a temperature to HA-LS-1 T4c on P1",
         "what": "HA-LS-1 T4c empty-pack drops (48 in, 6 orientations incl. crown top and side) after >= 4 h at "
                 "-20 C, each drop within 5 min of removal (re-soak 30 min between drops)",
         "coupons": "P1", "pass": "HA-LS-1 T4c pass rule; no crack at the crown corners, pawl housing, upper bar",
         "settles": "COLD on the upper half / crown"},
        {"id": "T4c-PPA-HW", "replaces": "T4c-PPA (review 8 M-7)",
         "what": "-20 C drop of printed stay coupons (H1-P lower stay z 0-240, R side, cut from the lower-half "
                 "file) with a steel slug pinned through the hinge eye",
         "coupons": "5 PPA-CF + 1 PAHT-CF control (was 3 + 1)",
         "load": f"2.8 kg slug from 1.22 m (48 in): {2.8 * 9.81 * 1.22:.0f} J = the T4b set-down energy "
                 f"({T4B_J:.0f} J), foot first then side-on",
         "pass": "no crack or whitening (10x loupe, dye penetrant), then 3-point bend at 1.5 x the C4 stay moment "
                 "without a crack; 5 / 5 shows R 0.55 at C 0.95 only (0.05^(1/5)), which is why T4b-PPA-COLD on "
                 "the frame is added",
         "settles": "COLD on the stay foot at the T4b energy"},
        {"id": "T4c-PPA-CROWN", "replaces": "new (review 8 M-7)",
         "what": "-20 C drop of a crown-corner coupon cut from the upper-half file (crown corner, pawl housing, "
                 "120 mm of upper bar) with a 2.0 kg slug through the crown bore",
         "coupons": "3 PPA-CF + 1 PAHT-CF control",
         "load": f"1.22 m crown-corner first then side-on: {2.0 * 9.81 * 1.22:.0f} J (half the empty pack, as T4c)",
         "pass": "no crack or whitening; pawl still locks on the rack",
         "settles": "COLD on the upper half"},
    ]


# ================================================================================================ M-2 hot-spot check, figures
def hotspot(name: str, mat: str = MAT, basis: str = "fine_sm8.cyc") -> dict:
    """Review 8 M-2 metric on the cached utilisation: within 9 mm of the 8 bolt axes at y -40..-26, the max
    fatigue utilisation and the voxels over 1.0 (the FI99 rule drops the top 1 %, so this local read is added)."""
    from . import h1_closeout as C
    cen = FI._base()["cen"]
    z = np.load(P.OUT / f"util_{name}_{mat}_{basis}.npz")
    c = cen[z["idx"]]
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    near = np.zeros(len(c), bool)
    for x, zz in pat["positions_xz"]:
        near |= np.hypot(c[:, 0] - x, c[:, 2] - zz) <= 9.0
    near &= (c[:, 1] >= -40.0) & (c[:, 1] <= -26.0)
    u = z["fat_u"][near]
    j = int(np.argmax(u))
    boss = (np.hypot(c[:, 0] - C.HIP_C[0], c[:, 2] - C.HIP_C[1]) <= 35.0)
    top = z["fat_u"] >= np.percentile(z["fat_u"][z["fat_u"] > 0], 99)
    return {"name": name, "mat": mat, "basis": basis, "max": round(float(u.max()), 3),
            "voxels_over_1": int((u > 1.0).sum()), "at_mm": [round(float(v), 1) for v in c[near][j]],
            "n_voxels": int(near.sum()), "top1pct_within_35mm_of_boss": int((top & boss).sum()),
            "top1pct_total": int(top.sum())}


def _ysec(mesh, y: float):
    from shapely.geometry import LineString, Polygon
    from shapely.ops import polygonize, unary_union
    s = mesh.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if s is None:
        return Polygon()
    return _evenodd([LineString(L[:, [0, 2]]) for L in s.discrete])


def _evenodd(lines):
    """Even-odd fill of closed section loops (polygonize also returns the holes as faces: use the shells only)."""
    from shapely.geometry import Polygon
    from shapely.ops import polygonize, unary_union
    out = Polygon()
    for p in polygonize(unary_union(lines)):
        out = out.symmetric_difference(Polygon(p.exterior))
    return out


def plot_boss_section(old_stl: Path, new_stl: Path, path: Path, hs_old: dict, hs_new: dict, hp: dict) -> str:
    """Hip-boss sections normal to y (the layer plane) at y -34 (review 8) and through the side (x = 18.44):
    BL-070 H1-P (hex traps) against BL-073 (through holes + bearing ring)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Circle, Rectangle
    from shapely.geometry import LineString
    fig, axs = plt.subplots(2, 2, figsize=(9.0, 9.0), dpi=100)
    for col, (lab, f, hs) in enumerate((("BL-070 H1-P: 8 hex traps", old_stl, hs_old),
                                        ("BL-073 H1-P: through holes, no traps", new_stl, hs_new))):
        m = trimesh.load(f, force="mesh")
        ax = axs[0, col]
        poly = _ysec(m, -34.0)
        for g in getattr(poly, "geoms", [poly]):
            if g.is_empty:
                continue
            x, z = g.exterior.xy
            ax.fill(x, z, color="#b9c4d0", lw=0)
            for h in g.interiors:
                hx, hz = h.xy
                ax.fill(hx, hz, color="white", lw=0.6, ec="#c0392b")
        ax.add_patch(Circle((0, 120), 25, fill=False, ls="--", lw=0.8, ec="#555"))
        ax.set_xlim(-34, 34)
        ax.set_ylim(86, 154)
        ax.set_aspect("equal")
        ax.set_title(f"{lab}\nsection at y -34 (layer plane), fatigue util max {hs['max']:.2f}, "
                     f"{hs['voxels_over_1']} vox > 1", fontsize=8.5)
        ax.set_xlabel("x mm")
        ax.set_ylabel("z mm")
        # side section: plane x = 18.44 (through the +x bolt group)
        ax = axs[1, col]
        s = m.section(plane_origin=[18.44, 0, 0], plane_normal=[1, 0, 0])
        if s is not None:
            pp = _evenodd([LineString(L[:, [1, 2]]) for L in s.discrete])
            for g in getattr(pp, "geoms", [pp]):
                if g.is_empty:
                    continue
                x, z = g.exterior.xy
                ax.fill(x, z, color="#b9c4d0", lw=0)
                for h in g.interiors:
                    hx, hz = h.xy
                    ax.fill(hx, hz, color="white", lw=0.6, ec="#c0392b")
        if col == 1:
            yb = -48.45 + BOSS_DEPTH
            ax.add_patch(Rectangle((yb, 120 - RING_OD / 2), RING_T, RING_OD, color="#7f8c8d"))
            for zz in (115.4, 124.6):
                ax.add_patch(Rectangle((yb + RING_T, zz - 4.0), NUT_M, 8.0, color="#34495e"))
                ax.plot([-48.45 - FLANGE_T, yb + RING_T + NUT_M + hp["screw"]["protrusion_mm"]], [zz, zz],
                        color="#2c3e50", lw=2.2)
            ax.add_patch(Rectangle((-48.45 - FLANGE_T, 120 - 25), FLANGE_T, 50, color="#95a5a6"))
            ax.text(-33, 93, f"6061 ring {RING_T:g} mm + nut keeper\nM5 x {hp['screw']['screw_l_mm']:g}, "
                    f"{hp['screw']['protrusion_threads']:.0f} threads proud\n{TORQUE_NM} N m", fontsize=7.5)
        ax.set_xlim(-56, -10)
        ax.set_ylim(90, 152)
        ax.set_aspect("equal")
        ax.set_title("side section at x 18.4 (bolt group), wearer face left", fontsize=8.5)
        ax.set_xlabel("y mm (print z up = right)")
        ax.set_ylabel("z mm")
    fig.suptitle("BL-073 M-2 / B-1: hip boss. Left BL-070 traps (merged pairs, 0.99 mm webs); right: through holes "
                 f"(webs {hp['webs']['between_holes_mm']} mm) + bearing ring", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    P.shrink_png(Path(path))
    return str(path)


def plot_plate_contact(stl_dir: Path, pf: dict, path: Path) -> str:
    """Underside height map of each laid-flat half with the plate contact (black) and the pad feet (orange)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Circle
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 5.6), dpi=100)
    for ax, nm in zip(axs, ("lower", "upper")):
        f = trimesh.load(stl_dir / f"h1_{nm}_flat.stl", force="mesh")
        U = underside(f)
        h = U["h"]
        ij = np.array(list(U["cells"].keys()))
        zz = np.array(list(U["cells"].values()))
        sc = ax.scatter((ij[:, 0] + 0.5) * h, (ij[:, 1] + 0.5) * h, c=np.clip(zz, 0, 45), s=2.2, marker="s",
                        cmap="viridis", vmin=0, vmax=45, linewidths=0)
        on = zz < 0.3
        ax.scatter((ij[on, 0] + 0.5) * h, (ij[on, 1] + 0.5) * h, c="k", s=3, marker="s", linewidths=0)
        for x, y, z in pf[nm]["sites_xyz_mm"]:
            ax.add_patch(Circle((x, y), PAD_FOOT_D / 2, color="#eb6834", alpha=0.85))
            ax.text(x + 13, y, f"{z:.0f}", fontsize=7)
        ax.add_patch(plt.Rectangle((0, 0), 340, 320, fill=False, ls="--", ec="#888"))
        ax.set_aspect("equal")
        ax.set_xlim(-15, 345)
        ax.set_ylim(-15, 325)
        ax.set_title(f"{nm} half: plate contact {pf[nm]['plate_contact_part_mm2']:.0f} -> "
                     f"{pf[nm]['plate_contact_with_pads_mm2']:.0f} mm2 with {pf[nm]['n_pads']} pads "
                     f"(+{pf[nm]['pad_g']:.0f} g)", fontsize=9)
    cb = fig.colorbar(sc, ax=axs, shrink=0.8)
    cb.set_label("underside height above the plate, mm (black = on the plate)")
    fig.suptitle("BL-073 M-5: sacrificial pads (orange, D24 foot, D12 column, snap-off neck D3; label = height mm). "
                 "Dashed: H2S 340 x 320 plate", fontsize=9.5)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    P.shrink_png(Path(path))
    return str(path)


# ================================================================================================ record
FINAL = "p1"               # set by the design loop (OUT/run_*.log); the lightest step with R1 and joint >= 1.0
BEFORE = "g1"              # BL-070 H1-P, re-checked on the hot/wet basis (no geometry change)
ROWMAP = [  # (BL-070 row name, short key)
    ("strength (min of 3 static bases)", "strength"), ("fatigue, static carry", "static carry fatigue"),
    ("fatigue, cinch-cycled (R1)", "R1"), ("creep (static / cinch-cycled, min)", "creep"),
    ("z 234 joint strength", "z 234 joint strength"), ("z 234 joint fatigue", "z 234 joint fatigue"),
    ("US2 lug strength", "US2 lug strength"), ("US2 lug fatigue", "US2 lug fatigue"),
    ("US2 clevis joint strength (share 1.0)", "US2 clevis strength (share 1.0)"),
    ("US2 clevis joint fatigue (share 1.0)", "US2 clevis fatigue (share 1.0)"),
    ("hip mount strength (through_bolt)", "hip mount strength"), ("hip mount fatigue (through_bolt)", "hip mount fatigue"),
    ("hip mount creep (through_bolt)", "hip mount creep"), ("lash pulls W1 / W2 (BL-068, p99)", "lash"),
    ("buckling, eigen, frame crown held", "buckling"),
    ("buckling, eigen, set-down (foot + crown held)", "buckling set-down"),
    ("buckling, eigen, members (stay tops free)", "buckling members")]


def margins_of(name: str, lug: dict, clev: dict, hip: dict, lash_r: dict, eig: dict) -> dict:
    """Short-key margins of a checked body on the ppa_hw basis."""
    sm = P.summary(json.loads((P.OUT / f"check_{name}_{MAT}.json").read_text()))
    s, c = sm["static_cinch"], sm["cinch_cycled"]
    return {"strength": s["strength"], "static carry fatigue": s["fatigue"], "R1": c["fatigue"],
            "creep": min(s["creep"], c["creep"]),
            "z 234 joint strength": min(s["joint_strength"], c["joint_strength"]),
            "z 234 joint fatigue": min(s["joint_fatigue"], c["joint_fatigue"]),
            "US2 lug strength": lug["design_min"]["strength"], "US2 lug fatigue": lug["design_min"]["fatigue"],
            "US2 clevis strength (share 1.0)": clev["share_1"]["all_rows_min"]["strength"],
            "US2 clevis fatigue (share 1.0)": clev["share_1"]["all_rows_min"]["fatigue"],
            "US2 clevis fatigue (share 0.6)": clev["share_0.6"]["all_rows_min"]["fatigue"],
            "hip mount strength": hip["min_sf"]["strength"], "hip mount fatigue": hip["min_sf"]["fatigue"],
            "hip mount creep": hip["min_sf"]["creep"], "lash": lash_r["states"]["after"]["margin_p99"],
            "buckling": eig["frame_crown_held"], "buckling set-down": eig["setdown"],
            "buckling members": eig["members"]}


GOAL = {"US2 lug strength": 1.5, "US2 lug fatigue": 1.15, "US2 clevis strength (share 1.0)": 1.5,
        "US2 clevis fatigue (share 1.0)": 1.15, "US2 clevis fatigue (share 0.6)": 1.15, "hip mount strength": 1.5,
        "hip mount fatigue": 1.15, "hip mount creep": 1.5}


def eig_scaled(eig_json: dict, mat_from: str = "ppa_design") -> dict:
    """BL-065 eigen margins re-read at the hot/wet buckling modulus (the voxel solve is linear in E: BL-070 showed
    PAHT -> PPA scales to the digit)."""
    f = P.e_buckle(MAT) / P.e_buckle(mat_from)
    e = eig_json["fine_sm8"]
    return {"frame_crown_held": e["frame_crown_held"] * f, "setdown": e["setdown_foot_and_crown_held"] * f,
            "members": e["members_unbraced_min"] * f, "scale": round(f, 4), "solved": False}


ASSUMPTIONS_BL073 = [
    ("B-BASIS-N5", "The Bambu TDS +/- values are standard deviations of an ISO 527 set of n = 5 (the ISO 527-1 minimum; "
     "the TDS gives no n): B-basis k 3.4066.", "CA-3-HW at n 10 (k 2.355)"),
    ("HOT-40", "Hot ratio of wet PPA-CF at 40 C = 0.85, the lowest of the Fiberlogy 40 / 20 C UTS ratio (0.864) and "
     "its Tg-shift readings (0.852-0.886) with the wet Tg 51-67 C.", "CA-3-HW at 40 C"),
    ("MATRIX-FRAC", "20 wt % carbon fibre (matrix fraction 0.8) for the water-in-matrix reading.", "not governing "
     "(the composite-basis reading is lower and taken)"),
    ("E-HW", "Hot/wet modulus = Raise3D conditioned / Bambu dry 0.661 x Fiberlogy E 40 / 20 C 0.889 = 0.5876 (was 0.85).",
     "CA-4-HW"),
    ("BEARING-RING", "Hip nut load spread by the 2 mm 6061 ring as a beam on a Winkler foundation (k0 = E_z / boss "
     "depth, cold E_z x 1.25), group of 4 at the 28 deg pitch; the larger of that peak and the ring average.",
     "HB-6b hip-mount proof on the first H1-P frame"),
    ("K-NUT", "Nut factor 0.20, scatter 0.14-0.26, for the Ti screw in an A2 nut with Loctite 243; the creep row uses "
     "the high preload (K 0.14), the closure check the low one (K 0.26).", "HB-6b paint marks"),
    ("CREEP-LONG", "Long-term layer-normal creep modulus of the boss at 40 C wet = 0.5 x short term (no curve "
     "published; 8 h is 0.85).", "HB-6b re-torque check after T5"),
    ("CTE-Z", "PPA-CF across the layers 60e-6 / K (not in the TDS): at -20 C the hip nuts lose their preload; no row "
     "credits preload, Loctite 243 holds the nuts.", "T4b-PPA-COLD paint marks"),
    ("LAYER-H", "0.30 mm layers (Bambu Studio 0.6 nozzle standard) for the layer-time and the swap layer.",
     "slicer preview"),
    ("SPOOL-RESERVE", "60 g of each 750 g spool kept back for purge and net-weight tolerance.", "first article"),
    ("PAD", "Sacrificial pads (D24 x 0.6 foot, D12 column, D6 -> D3 neck fused 0.6 mm into the part) hold the "
     "far ends of each half on the plate and snap off; the neck scar is sanded.", "first-article upper half"),
    ("JOINT-XY", "z 234 bolts moved to (18.5, 6) / (-19, 5.5) local: checked on the BL-070 g1 cut sections for the "
     "choice, then on the exported body.", "the checks on the export; CA-5 z 234 stub coupons"),
]


def margin_rows(Mx: dict, gate: dict | None = None) -> list:
    out = []
    for nm, k in ROWMAP:
        if k not in Mx:
            continue
        g = GOAL.get(k, 1.0)
        v = float(Mx[k])
        r = {"name": nm, "value": round(v, 3), "goal": g, "basis": "BL-073 hot/wet B-basis (ppa_hw)",
             "pass": bool(v >= g - 1e-9)}
        if gate and k in gate and not r["pass"]:
            r["gated_by"] = gate[k]
        out.append(r)
    return out


def plot_margin_bars(M0: dict, Mb: dict, Ma: dict, tor: list, path: Path) -> str:
    """Margin / goal: BL-070 as booked (BL-069 basis), BL-070 g1 on the hot/wet basis, BL-073 H1-P on the hot/wet
    basis; red ticks = the single worse assumptions on the BL-073 rows."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = [k for k in Ma if k in Mb]
    fig, ax = plt.subplots(figsize=(8.4, 11.0), dpi=100)
    y = np.arange(len(keys))[::-1]
    h = 0.26
    cols = ("#9aa3ad", "#e0a030", "#1f5fbf")
    labs = ("BL-070 H1-P as booked (BL-069 basis)", "BL-070 H1-P on the hot/wet basis", "BL-073 H1-P (hot/wet)")
    for i, (src, c, lab) in enumerate(zip((M0, Mb, Ma), cols, labs)):
        v = [min(src.get(k, np.nan) / GOAL.get(k, 1.0), 3.0) if src.get(k) is not None else np.nan for k in keys]
        ax.barh(y + (1 - i) * h, v, h, color=c, label=lab)
        for yy, vv, k in zip(y, v, keys):
            if src.get(k) is not None and np.isfinite(vv):
                ax.text(vv + 0.02, yy + (1 - i) * h, f"{src[k]:.2f}", va="center", fontsize=6.5, color=c)
    for t in tor:
        for yy, k in zip(y, keys):
            v = t["rows"].get(k)
            if v is not None and v < Ma[k] - 1e-6:
                ax.plot(v / GOAL.get(k, 1.0), yy - h, "|", color="#c0392b", ms=9, mew=1.6)
    ax.axvline(1.0, color="#c0392b", lw=1.3)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{k} (goal {GOAL.get(k, 1.0):g})" for k in keys], fontsize=7.8)
    ax.set_xlim(0, 3.3)
    ax.set_xlabel("margin / goal (clipped at 3; labels = margin). Red ticks: one worse assumption (tornado)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.05), ncol=1, fontsize=8)
    ax.set_title("BL-073: HA-LS-1 rows before / after on the hot/wet B-basis\n(Z 39.97 x 0.73 wet x 0.85 hot = "
                 "24.8 MPa; BL-069 booked 32.85)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    P.shrink_png(Path(path))
    return str(path)


def joint_e_ratio(e_hot: float = 0.50) -> float:
    """z 234 joint fatigue at E_hot 0.50 over E_hot 0.5876, on the g1 cut sections with JOINT_XY (min over bases)."""
    import pickle
    from dataclasses import replace
    from . import frame_h1 as H1
    secs = pickle.load(open(OUT / "secs_g1.pkl", "rb"))
    j = replace(H1.JOINT, xy=JOINT_XY)
    vals = []
    for eh in (P.ppa_record()["E_hot_hw"], e_hot):
        with P.material(MAT):
            H1.PAHT["E_hot"] = eh
            vals.append(min(H1.joint_check(None, j, secs=s)["min_fatigue"] for s in secs.values()))
    return vals[1] / vals[0]


def report(final: str = FINAL, log=print) -> dict:
    import shutil
    import trimesh
    rec = json.loads(P.REC_JSON.read_text())
    if "h1p_bl070" not in rec:
        rec["h1p_bl070"] = json.loads(json.dumps(rec["h1p"]))
    b = basis()
    hip = hip_plate()
    hip_bl070 = P.hip_inserts(MAT)["through_bolt"]
    itf = json.loads((OUT / "itf_g1_hw.json").read_text())
    clev = itf["clevis"]
    # before: BL-070 g1 on the hot/wet basis
    eig0 = json.loads((P.OUT / "eigen_h1p.json").read_text())
    Mb = margins_of(BEFORE, itf["lug"], clev, hip_bl070, itf["lash"], eig_scaled(eig0))
    # after
    rr = raster_of(final)
    m = trimesh.load(P.STL_DIR / "h1_assembled.stl", force="mesh")
    chk_raster, _ = P.reraster()
    if not np.array_equal(chk_raster, rr):
        raise RuntimeError(f"the STLs in {P.STL_DIR} are not the checked {final} export")
    lug = P.us2_lug(mesh=m, mat=MAT, tag=final)
    la = P.lash(rr, mat=MAT, tag=final)
    ep = OUT / f"eigen_{final}.json"
    if ep.exists():
        ej = json.loads(ep.read_text())["fine_sm8"]
        eig = {"frame_crown_held": ej["frame_crown_held"], "setdown": ej["setdown_foot_and_crown_held"],
               "members": ej["members_unbraced_min"], "solved": True}
    else:
        eig = eig_scaled(eig0)
    Ma = margins_of(final, lug, clev, hip, la, eig)
    # BL-070 as booked (BL-069 basis)
    old = {r["name"]: r["value"] for r in rec["h1p_bl070"]["rows"]}
    M0 = {k: old[nm] for nm, k in ROWMAP if nm in old}
    M0["US2 clevis fatigue (share 0.6)"] = rec["h1_ppa"]["us2_clevis"]["share_0.6"]["all_rows_min"]["fatigue"]
    # tornado
    ck = json.loads((P.OUT / f"check_{final}_{MAT}.json").read_text())
    sh_c = ck["fine_sm8.cyc"]["fatigue_top1pct_term_share"]
    sh_s = ck["fine_sm8"]["fatigue_top1pct_term_share"]
    il = {"R1": sh_c["shear_xy"] + sh_c["shear_yz"], "static carry fatigue": sh_s["shear_xy"] + sh_s["shear_yz"],
          "strength": sh_s["shear_xy"] + sh_s["shear_yz"], "creep": sh_s["shear_xy"] + sh_s["shear_yz"],
          "z 234 joint fatigue": 1.0, "z 234 joint strength": 1.0, "US2 lug fatigue": 1.0, "US2 lug strength": 1.0,
          "R1|z": 1 - sh_c["in_plane"], "static carry fatigue|z": 1 - sh_s["in_plane"],
          "strength|z": 1 - sh_s["in_plane"], "creep|z": 1 - sh_s["in_plane"],
          "US2 clevis fatigue (share 0.6)|z": 1.0, "US2 clevis fatigue (share 1.0)|z": 1.0,
          "US2 clevis strength (share 1.0)|z": 1.0, "hip mount fatigue|z": 1.0, "hip mount strength|z": 1.0,
          "hip mount creep|z": 1.0}
    jr = joint_e_ratio()
    gov_keys = ["R1", "z 234 joint fatigue", "static carry fatigue", "strength", "z 234 joint strength",
                "US2 lug fatigue", "US2 clevis fatigue (share 0.6)", "US2 clevis fatigue (share 1.0)",
                "hip mount fatigue", "hip mount creep", "buckling"]
    Mg = {k: Ma[k] for k in gov_keys}
    tor = tornado(Mg, il, joint_e={"z 234 joint fatigue": Ma["z 234 joint fatigue"] * jr})
    # printability
    fl = {n: trimesh.load(P.STL_DIR / f"h1_{n}_flat.stl", force="mesh") for n in ("lower", "upper")}
    pr = P.printability(m, fl)
    PRINT_INFO.clear()
    PRINT_INFO.update(pr)
    pf = print_files()
    sp = spool_plan(final, pf, log=log)
    lt = {n: layer_time_s(fl[n]) for n in fl}
    hs = {"h1_ppa_design": hotspot("h1", "ppa_design"), "bl070_g1_ppa_design": hotspot("g1", "ppa_design"),
          "bl070_g1_hw": hotspot("g1", MAT), "bl073_hw": hotspot(final, MAT)}
    e_need = max(P.ppa_record()["E_hot_hw"] / min(Ma["buckling"], Ma["buckling members"]), 0.50)
    cps = coupons_hw({**Ma, "_e_need": e_need}, b, lt)
    # mass
    body = round(m.volume * P.RHO_PPA, 1)
    parts = hip_parts()
    hw_delta = hip["hardware_g"]["screws_extra_g"] + parts["hip_bearing_ring"]["g"] + parts["hip_nut_keeper"]["g"]
    mass = {"body_g": body, "bl070_body_g": rec["h1p_bl070"]["body_g"],
            "body_delta_vs_bl070_g": round(body - rec["h1p_bl070"]["body_g"], 1),
            "body_delta_vs_paht_h1_g": round(body - P.PAHT_BODY_G, 1),
            "hip_hardware_delta_vs_bl070_g": round(hw_delta, 1),
            "frame_delta_vs_bl070_g": round(body - rec["h1p_bl070"]["body_g"] + hw_delta, 1),
            "pads_filament_g": {n: pf[n]["pad_g"] for n in pf}}
    # gates for rows that miss their goal on the hot/wet basis
    gate = {"US2 lug fatigue": "CLEVIS-SHARE B lug proof (kit) + CA-1-HW; >= 1.0 on hot/wet, goal 1.15 is the BL-021 "
                               "scatter goal: see OPEN",
            "US2 clevis fatigue (share 1.0)": "CLEVIS-SHARE B (kit): the measured outer-cheek share must be <= the "
                                              "share at which the row reads 1.15; design share 0.6 reads "
                                              f"{Ma['US2 clevis fatigue (share 0.6)']:.2f}"}
    rows_new = margin_rows(Ma, gate)
    # screenshots
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [plot_margin_bars(M0, Mb, Ma, tor, SCREENS / f"{SHOT}1.png"),
             plot_boss_section(OUT / "bl070_g1_stl" / "h1_assembled.stl", P.STL_DIR / "h1_assembled.stl",
                               SCREENS / f"{SHOT}2.png", hs["bl070_g1_hw"], hs["bl073_hw"], hip),
             plot_plate_contact(P.STL_DIR, pf, SCREENS / f"{SHOT}3.png"),
             plot_tornado(Mg, tor, SCREENS / f"{SHOT}4.png",
                          "BL-073 M-1: single-assumption tornado on the governing rows (hot/wet B-basis)")]
    # released raster for the tests (review 8 m-3)
    np.savez_compressed(P.STL_DIR / "h1p_checked_raster.npz", solid=rr)
    # ---------------------------------------------------------------- record (keys added, none renamed)
    h = rec["h1p"]
    sm = P.summary(ck)
    steps = [s for s in h.get("steps", []) if s.get("basis") != MAT]
    for p_ in sorted(P.OUT.glob(f"check_*_{MAT}.json"), key=lambda q: q.stat().st_mtime):
        d = json.loads(p_.read_text())
        if "step" in d and d["step"].get("basis") == MAT:
            s2 = P.summary(d)
            steps.append({"name": d["name"], **d["step"], "geometry": "export re-raster (BL-073 hip boss, z 234 "
                          "bolts moved)", "cyc": s2["cinch_cycled"]["fatigue"],
                          "static_fatigue": s2["static_cinch"]["fatigue"], "strength": s2["static_cinch"]["strength"],
                          "joint_fatigue": min(s2["static_cinch"]["joint_fatigue"], s2["cinch_cycled"]["joint_fatigue"])})
    einfo = json.loads((OUT / f"{final}_export_info.json").read_text())
    h.update({"checked_on": "exported STL re-rastered on the H1 2 mm grid (bl058_frame.body_stl rule); BL-073 "
                            "hot/wet B-basis (materials ppa_hw)",
              "final_iter": final, "steps": steps, "body_g": body,
              "delta_vs_paht_h1_g": round(body - P.PAHT_BODY_G, 1),
              "delta_vs_h1_ppa_g": round(body - rec["h1_ppa"]["body_g"], 1), "summary": sm, "rows": rows_new,
              "rows_by_name": {r["name"]: r for r in rows_new},
              "fatigue_top1pct_term_share": sh_c, "print": pr, "export": einfo,
              "voxels": {"exported_raster": int(rr.sum())},
              "eigen": {"fine_sm8": {"frame_crown_held": eig["frame_crown_held"],
                                     "setdown_foot_and_crown_held": eig["setdown"],
                                     "members_unbraced_min": eig["members"], "solved": eig.get("solved", False)},
                        "E_buckle_mpa": round(P.e_buckle(MAT), 1),
                        "layer_normal_bound_factor": h.get("eigen", {}).get("layer_normal_bound_factor", 0.364)},
              "hip_mount": {"nut_seat_depth_mm": BOSS_DEPTH + RING_T, "bearing_ring_mm2": hip["ring_area_mm2"],
                            "bearing_n": round(hip["allow_mpa"] / (hip["pressure_mpa_per_kn"] / 1e3), 1),
                            "rows": hip["rows"], "min_sf": hip["min_sf"], "pass": hip["pass"],
                            "hardware": hip["hardware"], "torque_nm": hip["torque_nm"],
                            "preload_n": hip["preload_n"], "screw": hip["screw"],
                            "ring": {"material": "6061-T6 (data/materials/metals/alu_6061_t6.yaml)", "od_mm": RING_OD,
                                     "id_mm": RING_ID, "t_mm": RING_T, "holes": "8 x D5.5 on r 19 (HIP_CHOSEN)",
                                     "g": hip["hardware_g"]["ring_g"]},
                            "boss": {"depth_mm": BOSS_DEPTH, "flat_back": True, "spot_face_d_mm": SPOT_D,
                                     "holes_d_mm": HOLE_D, "traps": 0},
                            "relaxation": hip["relaxation"], "cold": hip["cold"], "webs": hip["webs"]},
              "z234_joint_xy": {"bl073": JOINT_XY, "bl070": JOINT_XY_BL070}})
    rec["bl073"] = {"ticket": "BL-073", "date": "2026-11-25", "review": "designs/pack_5200/analysis/review_20261125_eighth.md",
                    "basis": b, "material_key": MAT, "materials_ppa_hw": P.materials()[MAT],
                    "margins_bl070_booked": M0, "margins_bl070_on_hw": Mb, "margins_bl073_hw": Ma,
                    "tornado": tor, "tornado_shares": il, "joint_e050_ratio": round(jr, 4),
                    "hip_plate": hip, "hip_parts": parts, "hip_bl070_dw_on_hw": hip_bl070, "hotspot": hs,
                    "print_files": pf, "spool_plan": sp, "layer_time": lt, "mass": mass,
                    "eigen": {**eig, "note": "BL-065 eigen re-solved on the final export" if eig.get("solved") else
                              "BL-070 g1 eigen x E ratio (voxel solve linear in E); final export not re-solved"},
                    "lug": lug["design_min"], "lash_p99": la["states"]["after"]["margin_p99"],
                    "clevis": {k: clev[k]["all_rows_min"] for k in ("share_0.6", "share_1")}}
    rec["coupons_bl073"] = cps
    # review 8 m-4: the BL-070 CA-3-PPA 'if below' band, corrected in place (the row itself stays as recorded)
    ob = {q["name"]: q["value"] for q in rec["h1p_bl070"]["rows"]}
    fix = {c["id"]: c for c in P.coupons(ob["fatigue, cinch-cycled (R1)"], ob["fatigue, static carry"],
                                         ob["strength (min of 3 static bases)"], ob["buckling, eigen, frame crown held"],
                                         ob["z 234 joint fatigue"])}
    for c in rec["coupons"]:
        if c["id"] == "CA-3-PPA":
            c["if_below"] = fix["CA-3-PPA"]["if_below"]
    _, rinfo = P.reraster()
    rec["bl073"]["reraster"] = {k: rinfo[k] for k in ("stl_voxels", "run_voxels", "pads_added") if k in rinfo}
    rec["assumptions_bl073"] = [{"id": a, "text": t, "settled_by": s_} for a, t, s_ in ASSUMPTIONS_BL073]
    rec["screenshots_bl073"] = [str(Path(q).relative_to(REPO)) for q in shots]
    P.REC_JSON.write_text(json.dumps(rec, default=FI._jd, indent=1))
    P.write_md(json.loads(P.REC_JSON.read_text()))
    write_md_section(json.loads(P.REC_JSON.read_text()))
    if log:
        log(f"record {P.REC_JSON}")
    return rec


def _oz(g: float) -> str:
    return f"{g / 28.3495:+.1f} oz"


def write_md_section(rec: dict) -> str:
    """Insert the BL-073 section after the first paragraph of bl070_h1p.md (the BL-070 sections stay below it)."""
    x = rec["bl073"]
    b, hp, ms = x["basis"], x["hip_plate"], x["mass"]
    M0, Mb, Ma = x["margins_bl070_booked"], x["margins_bl070_on_hw"], x["margins_bl073_hw"]
    hb = b["hot"]
    L = ["## BL-073 (review 8 close-out): hot/wet basis, hip bearing ring, no traps, re-tune, coupons, printability", "",
         "Code `huntkit/gendesign/bl073_hotwet.py`, tests `tests/test_bl073_hotwet.py`. Everything in this section is on "
         "the **hot/wet B-basis** (`bl070_h1p.materials()['ppa_hw']`). The BL-070 sections below keep the BL-069 "
         "basis for the record; the H1-P rows in the first table are now BL-073's.", "",
         "### Design basis (B-2, M-1, M-8)", "",
         "| quantity | BL-069 (BL-070 record) | **BL-073** | source |", "|---|---:|---:|---|",
         f"| design Z (dry) | 45 MPa = 57 - 2.4 SD (no source) | **{b['s_z_b']} MPa** = 57 - {b['k_n5']} x 5 | B-basis "
         f"k for n 5 (ISO 527-1 minimum; TDS gives no n), noncentral t; CMH-17-1G 8.3.4.3, NIST 7.2.6.3 |",
         f"| design XY (dry) | 168 MPa (mean) | **{b['s_xy_b']} MPa** = 168 - {b['k_n5']} x 4 | same |",
         f"| wet (23 C) | 0.73 | 0.73 | Raise3D conditioned 122 / Bambu dry 168 |",
         f"| hot 40 C, wet | none (0.73 was called hot/wet) | **{hb['chosen']}** | min of Fiberlogy 40/20 C "
         f"{hb['fiberlogy_40_20_dry']}, Tg-shift {hb['ForTii PPA (Envalior)']['ratio']} (wet Tg "
         f"{hb['ForTii PPA (Envalior)']['tg_wet_c']} C, ForTii PPA 26.5 C per %) and "
         f"{hb['PA66 (Wetzel 2023, DSC)']['ratio']} (wet Tg {hb['PA66 (Wetzel 2023, DSC)']['tg_wet_c']} C, PA66 11.3 C per %) |",
         f"| knocked Z / interlayer shear | 32.85 / 19.7 MPa | **{b['z_knocked_hw']} / {b['tau_il_hw']} MPa** "
         f"(x {b['z_scale_vs_bl069']}) | 0.73 x {hb['chosen']} = {b['knock_hw']} |",
         f"| knocked XY | 122.6 MPa | **{b['xy_knocked_hw']} MPa** | |",
         f"| E hot/wet / E dry | 0.85 (contradicted the record) | **{b['E_hot_hw']}** = 0.661 x {hb['modulus_hot']} | "
         f"Raise3D E 7800 / 11800; Fiberlogy E 40/20 C |",
         f"| buckling modulus | 8526 MPa | **{b['e_buckle_hw']:.0f} MPa** | x creep 0.85 |", "",
         f"Raise3D's measured conditioned Z (30.2 MPa, 23 C) now sits ABOVE the 23 C wet design value "
         f"({b['raise3d_cond_z_vs_hw_23c']} MPa); the BL-069 note that it 'sits at' the design Z was wrong (8 % below) "
         "and is corrected in the YAML.", "",
         "### Margins before / after (all hot/wet except the first column)", "",
         "| row | goal | BL-070 as booked (BL-069 basis) | BL-070 H1-P on hot/wet | **BL-073 H1-P** |",
         "|---|---:|---:|---:|---:|"]
    for k in Ma:
        g = GOAL.get(k, 1.0)
        a0 = M0.get(k)
        L.append(f"| {k} | {g:g} | {a0 if a0 is not None else '-'} | {Mb.get(k, float('nan')):.3f} | "
                 f"**{Ma[k]:.3f}**{'' if Ma[k] >= g - 1e-9 else ' (below goal)'} |")
    rr_ = x.get("reraster", {})
    L += ["", f"Buckling: {x['eigen']['note']}.", "",
          f"How the rows were computed (review 8 m-1, m-2): the body rows (strength, fatigue, creep, z 234 joint, lash) "
          f"on the exported assembled STL re-rastered by the BL-058 `body_stl` rule, which adds "
          f"{rr_.get('pads_added', '-')} pad voxels to the {rr_.get('stl_voxels', '-')} STL voxels (the same rule "
          "as the PAHT baseline); the US2 lug on its 1 mm submodel of the exported mesh; the clevis rows from the "
          "unchanged clevis (BL-056 joint rows); the hip rows are hand calculations (BL-055 tipping model) with the "
          "local hot-spot read below added.", "",
          "### Mass", "",
          "| item | g | change vs BL-070 H1-P |", "|---|---:|---:|",
          f"| printed body (halves + US2 clevises), PPA-CF | **{ms['body_g']}** ({ms['body_g'] / 453.6:.2f} lb) | "
          f"{ms['body_delta_vs_bl070_g']:+.1f} g ({_oz(ms['body_delta_vs_bl070_g'])}) |",
          f"| hip hardware: 6061 ring + printed nut keeper + M5 x {hp['screw']['screw_l_mm']:g} for x 20 | "
          f"{ms['hip_hardware_delta_vs_bl070_g']:.1f} | {ms['hip_hardware_delta_vs_bl070_g']:+.1f} g |",
          f"| **frame total change** | | **{ms['frame_delta_vs_bl070_g']:+.1f} g ({_oz(ms['frame_delta_vs_bl070_g'])})** |",
          f"| vs PAHT-CF H1 (1069.3 g body) | | {ms['body_delta_vs_paht_h1_g']:+.1f} g body |",
          f"| sacrificial pads (filament only, snapped off) | lower {ms['pads_filament_g']['lower']}, upper "
          f"{ms['pads_filament_g']['upper']} | not in the frame |", ""]
    L += ["### Hip mount (B-1, M-2)", "",
          f"- **No nut traps.** The D50 boss is solid from the mount face to a flat back {BOSS_DEPTH:g} mm behind it "
          f"(spot face D{SPOT_D:g}); 8 x D{HOLE_D:g} through holes on the BL-055 positions. Webs between holes "
          f"{hp['webs']['between_holes_mm']} mm (6 lines at 0.6), hole to boss edge {hp['webs']['hole_to_boss_edge_mm']} mm, "
          "no side-wall breakout (the holes sit inside the solid D50 cylinder over the full depth).",
          f"- **Bearing ring** 6061-T6 {RING_OD:g} / {RING_ID:g} x {RING_T:g} mm ({RING_OD / 25.4:.2f} x {RING_T / 25.4:.3f} in), "
          f"8 holes D{HOLE_D:g} on r 19, {hp['hardware_g']['ring_g']} g, laser or waterjet cut. Nuts bear on the ring; "
          f"the ring bears on the PPA over {hp['ring_area_mm2']:.0f} mm2. Bearing read as a beam on an elastic "
          f"foundation (Hetenyi; cold boss, beta {hp['hetenyi']['beta']} /mm, group factor "
          f"{hp['hetenyi']['group_factor']}): {hp['pressure_mpa_per_kn']} MPa per kN of bolt force.",
          f"- **Nut keeper:** printed PPA-CF, {KEEPER_T:g} mm, two pockets (each the union of 4 hexes {KEEPER_AF} AF, "
          f"flats radial); it sits on the ring around the nuts so the screws can be turned from the mount side with "
          f"the 3 mm hex bit (an 8 mm spanner does not fit between nuts 9.2 mm apart). Non-structural; min wall "
          f"{x['hip_parts']['keeper_min_wall_mm']} mm. Files: " + ", ".join(f"`{q}`" for q in x["hip_parts"]["files"]) + ".",
          f"- **Screw:** Ti gr5 M5 x {hp['screw']['screw_l_mm']:g} DIN 7984: stack {hp['screw']['stack_mm']:g} mm (flange 3 "
          f"+ boss {BOSS_DEPTH:g} + ring {RING_T:g} + nut 4), {hp['screw']['protrusion_mm']} mm = "
          f"{hp['screw']['protrusion_threads']:.0f} threads proud (BL-070: 0).",
          f"- **Torque {hp['torque_nm']} N m ({hp['torque_nm'] / 0.112985:.1f} in lbf)**, star order, twice, Loctite 243. "
          f"Preload T = K F d, K 0.20 (0.14-0.26): {hp['preload_n']['nom']:.0f} N nominal, "
          f"{hp['preload_n']['min']:.0f}-{hp['preload_n']['max']:.0f} N. The creep row is set by the high end.",
          f"- **Relaxation (hot/wet):** Ti screw {hp['relaxation']['kb_n_mm']} N/mm in series with the boss "
          f"{hp['relaxation']['km0_n_mm']} N/mm at E_z x 0.5876; at CREEP-LONG 0.5 the preload keeps "
          f"{hp['relaxation']['residual_fraction'] * 100:.0f} %: {hp['relaxation']['residual_preload_min_n']:.0f} N at "
          f"the low end, above the walk bolt tension {hp['relaxation']['walk_bolt_tension_n']} N (joint stays closed).",
          f"- **Cold:** at -20 C the boss shrinks {hp['cold']['shrink_mm']} mm more than the screw (CTE-Z): "
          f"{hp['cold']['preload_loss_n']:.0f} N, so the preload is gone at -20 C. No row credits preload (the BL-055 "
          "tipping model is preload-free); Loctite 243 keeps the nuts; T4b-PPA-COLD checks the paint marks.",
          "", "| row | T per bolt N | pressure MPa | SF | goal |", "|---|---:|---:|---:|---:|"]
    for k, r in hp["rows"].items():
        L.append(f"| {k} ({r['kind']}) | {r['T_max_n']} | {r['pressure_mpa']} | {r['sf']} | {r['goal']} |")
    L += ["", f"The BL-070 trap seat on the nut face (dw 6.9, 13.6 mm2) reads fatigue "
          f"{hp['bl070_dw_ring_check']['fatigue_on_dw_bl069_basis']} on the BL-069 basis (review 8: 1.06) and "
          f"{hp['bl070_dw_ring_check']['fatigue_on_dw_hw']} on hot/wet.", ""]
    hs = x["hotspot"]
    L += ["**Hot-spot check with the holes in the geometry (M-2)**, review 8 metric: max cinch-cycled fatigue "
          "utilisation within 9 mm of the 8 bolt axes at y -40..-26 (2 mm raster of the exported STL):", "",
          "| body | basis | max | voxels > 1 | top-1 % within 35 mm of the boss |", "|---|---|---:|---:|---:|"]
    for k, v in hs.items():
        L.append(f"| {k} | {v['mat']} | {v['max']} | {v['voxels_over_1']} | {v['top1pct_within_35mm_of_boss']} / "
                 f"{v['top1pct_total']} |")
    L += ["", "### z 234 joint (re-tune)", "",
          f"Bolts moved toward the stay mid-plane: outboard {JOINT_XY_BL070[0]} -> {JOINT_XY[0]}, inboard "
          f"{JOINT_XY_BL070[1]} -> {JOINT_XY[1]} (local mm). That cuts the boss-bending interlayer term; the plug "
          "shear-out now governs. Same hardware (M5 x 45 Ti, washers, DIN 934 nuts); bosses inside the BL-058 "
          "envelope, bore ligaments >= 3.6 mm.", "",
          "### Sensitivity (M-1): one worse assumption at a time", "",
          "| variation | source | retired by | " + " | ".join(next(iter(x["tornado"]))["rows"].keys()) + " |",
          "|---|---|---|" + "---:|" * len(next(iter(x["tornado"]))["rows"])]
    for t in x["tornado"]:
        L.append(f"| {t['variation']} | {t['source']} | {t['retired_by']} | " +
                 " | ".join(f"{v:.2f}" for v in t["rows"].values()) + " |")
    L += ["", "No single variation in the list is covered by margin on every row: each one is **retired by the "
          "coupon named** before the frame is built (the coupon lines below are set on these margins). The 2.4 SD "
          "factor is gone (B-basis k by n).", "",
          "### Coupons (register rows, `coupons_bl073` in the JSON; the BL-070 `coupons` rows stay for the record)", "",
          "| id | replaces | what | load | pass | settles |", "|---|---|---|---|---|---|"]
    for c in rec["coupons_bl073"]:
        L.append(f"| {c['id']} | {c['replaces']} | {c['what']}; {c['coupons']} | {c.get('load', '')} | "
                 f"{c['pass']}{'; ' + c['statistic'] if c.get('statistic') else ''} | {c['settles']} |")
    pf, sp = x["print_files"], x["spool_plan"]
    L += ["", "### Printability (M-5, M-6, m-5, m-6)", "",
          "| half | plate contact part only mm2 | with pads mm2 | pads | pad filament g | filament total g | "
          "0.75 kg spools | planned change at print z (layer) | layer-plane fatigue util there (half max) |",
          "|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for n in ("lower", "upper"):
        s_ = sp[n]["swap"] or {}
        L.append(f"| {n} | {pf[n]['plate_contact_part_mm2']:.0f} | {pf[n]['plate_contact_with_pads_mm2']:.0f} | "
                 f"{pf[n]['n_pads']} | {pf[n]['pad_g']} | {sp[n]['filament_total_g']:.0f} | {sp[n]['spools']} | "
                 f"{s_.get('print_z_mm')} mm ({s_.get('layer')}) | {s_.get('fat_u_max')} ({sp[n]['global_fat_u_max_half']}) |")
    L += ["", "- **Pads (M-5):** print `h1p/h1_<half>_flat_print.stl` (part + pads); the clean `h1_<half>_flat.stl` "
          "stay as the geometry of record. Each pad is a D24 x 0.6 mm foot (a mouse ear), a D12 column and a D6 -> D3 "
          "neck fused 0.6 mm into the part: snap or nip it off with flush cutters and sand the scar. Pads sit at the "
          "far ends (farthest-point choice >= 60 mm apart), so each half is held at both ends. Print a **first-article "
          "upper half** before any coupon spool is opened.",
          "- **Spool (M-6):** Bambu PPA-CF is sold only as 0.75 kg (cardboard spool rated 145 C) and is not AMS "
          "compatible, so auto-refill is out. Each half needs just over one spool: put ONE planned filament change "
          "(Bambu Studio: preview, layer slider, 'Add pause' / 'Change filament' at that layer) at the layer in the "
          "table. That layer plane is chosen as the least-stressed plane inside the window where spool 1 still has "
          f"{SPOOL_RESERVE_G:.0f} g left and spool 2 can finish. Swap within 10 minutes (chamber stays at 65 C); "
          "CA-3-HW tests a 20 minute pause layer.",
          "- **Dryer (m-5):** 120 C x 10 h is under the 145 C rating of Bambu's cardboard spool (retailer copy of the "
          "Bambu listing); feed from a dry box with a hygrometer reading < 20 % RH for the whole print.",
          f"- **Spool count (m-6):** halves {sp['lower']['filament_total_g']:.0f} + {sp['upper']['filament_total_g']:.0f} g "
          "plus the BL-073 coupons (CA-1/3/4-HW, T4c-PPA-HW / CROWN: estimate 700-900 g with blocks and towers): "
          "**book 5 spools** (3.75 kg).", ""]
    L += ["### ASSUMPTIONS (BL-073)", ""]
    for a in rec["assumptions_bl073"]:
        L.append(f"- ASSUMPTION {a['id']}: {a['text']} Settled by: {a['settled_by']}.")
    L += ["", "### Screenshots", ""] + [f"- `{q}`" for q in rec["screenshots_bl073"]] + [""]
    md = P.REC_MD.read_text()
    head, _, rest = md.partition("\n## ")
    P.REC_MD.write_text(head.rstrip() + "\n\n" + "\n".join(L) + "\n## " + rest)
    return str(P.REC_MD)


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else "report"
    if cmd == "step":
        export_step_hw(a[1], a[2], float(a[3]), float(a[4]), n_thin=int(a[5]) if len(a) > 5 else 1)
    elif cmd == "report":
        report(a[1] if len(a) > 1 else FINAL)
    elif cmd == "eigen":
        nm = a[1] if len(a) > 1 else FINAL
        r = P.eigen(nm, raster_of(nm), bases=("fine_sm8",), setdown=True, mat=MAT)
        (OUT / f"eigen_{nm}.json").write_text(json.dumps(r, default=FI._jd, indent=1))
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
