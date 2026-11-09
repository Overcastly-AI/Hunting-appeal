"""Package C structural gates of the CORRIE weight pass (structural-fea-engineer, 2026-11-09).

Owner approval: docs/DECISIONS.md 2026-11-09 "Owner: 'Yes' to the weight-pass recommendation" item (3).
Item definitions: designs/pack_5200/analysis/weight_pass_corrie.md section 3.3 (C-1..C-4, C-7, C-9).
Write-up: designs/pack_5200/analysis/weight_c_structural.md. Results: analysis/weight_c_structural_results.json.
Standard: HA-LS-1 rev C (``huntkit.fea.load_standard``). SF/req = capacity / factored demand; >= 1.0 passes.

Items:
* C-1  belt-B centre plate 6061-T6 1.5 -> 7075-T6 1.2 mm, with the forming route (cold slip-roll to a template, W-temper
       form + age, warm / creep-age form, flat + press-brake bends). Engine: ``hipbelt_structure`` (grillage on a Winkler
       foundation + membrane closed form), here with route allowables (forming residual stress as a Goodman mean
       stress, over-ageing knockdown, end-slope tolerance) and, for bent plates, the kink loads at each bend line.
* C-2  PA66 hub D36 x 12 -> D28 x 10 (grillage with the smaller rigid hub, bore bearing, thrust face).
* C-3  lightening holes in the bow-tie spine (x 30..55): net section + Heywood Kt on the grillage section moment.
* C-4  HDPE pad backer 1.0 -> 0.8 mm across the 70 mm channel: ACM plate (``huntkit.fea.plate_grid``) between the body
       foundation (pad stack + tissue) and the EVA rails, unilateral contact with the bow-tie spine (4.5 mm play).
* C-7  CFRP yoke plate 1.5 -> 1.2 mm: ACM plate with CLT D, Tsai-Wu first ply (knocked down), clamped on the crown
       spine, loads = the shoulder-harness reactions of the rev C beam model (every case x torso 15/19/23).
* C-9  printed body mass pass: utilisation-guided inward offset of the body SDF (low-stress ligaments only, never more
       than 30 % of the local radius), re-verified on the 2 mm voxel model under every rev C set (FI99 rule).
"""
from __future__ import annotations

import contextlib
import copy
import json
import math
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np

from huntkit.fea import load_standard as ls
from huntkit.materials import load

from . import hipbelt_structure as hs

REPO = Path(__file__).resolve().parents[2]
ANALYSIS = REPO / "designs" / "pack_5200" / "analysis"
OUT_JSON = ANALYSIS / "weight_c_structural_results.json"
C9_JSON = REPO / "outputs" / "weight_c" / "c9_body.json"
SCREENS = REPO / "outputs" / "screens"
DATE = "20261109"
G = 9.80665

BASE_CP = hs.CentrePlate()                       # released recommendation: 6061-T6 1.5 bow-tie, curved 14.6 deg
HALF_CHORD_MM = BASE_CP.half_w                   # 105 mm: plate half width, sets the end slope of the arc

# ---------------------------------------------------------------------------------------------- ASSUMPTIONS
SLOPE_TOL_DEG = {"template": 2.0, "heat_treat": 3.0, "brake": 1.0}
#   ASSUMPTION: end-slope tolerance after forming. Rolled to a template and re-rolled until it fits: +/-2 deg.
#   Solution-treated and quenched (W temper / O temper route): quench distortion, re-struck: +/-3 deg. Brake: +/-1 deg.
T73_FACTOR = 0.865        # ASSUMPTION: warm / creep-age formed 7075 behaves as T73: typical yield 435 vs 503 MPa (ASM)
T73_FAT = 0.95            # ASSUMPTION: over-aged 7xxx fatigue about 5 % below T6 at 1e5
BEND_FAT = 0.80           # ASSUMPTION: fatigue allowable on a cold press-brake bend line in 7075-T6 (R >= 5 t)
RESID_RELAX = 1.0         # ASSUMPTION: forming residual stress kept in full as a mean stress (no shake-down credit)
PIN_BEARING_FACTOR = 1.5  # ASSUMPTION: Al bearing yield = 1.5 x S-basis yield (e/D >= 2, MMPDS-style), pin hole reamed


# ============================================================================================== C-1 forming
def elastic_limit_radius(t: float, sy: float, E: float) -> float:
    """Radius below which a sheet takes a permanent set: R_e = E t / (2 sy)."""
    return E * t / (2.0 * sy)


def springback_final_radius(Ri: float, t: float, sy: float, E: float) -> float:
    """Elastic-perfectly-plastic rectangular section bent to Ri, then released (Gardiner / Hosford-Caddell):
    Ri / Rf = 4 x^3 - 3 x + 1, x = Ri sy / (E t). Returns inf when Ri >= R_e (no set)."""
    x = Ri * sy / (E * t)
    if x >= 0.5:
        return math.inf
    r = 4 * x ** 3 - 3 * x + 1
    return Ri / r


def forming_radius_for(Rf: float, t: float, sy: float, E: float) -> float:
    """Tool radius that springs back to Rf (bisection on the monotonic springback curve)."""
    lo, hi = 1e-3, elastic_limit_radius(t, sy, E) * (1 - 1e-9)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if springback_final_radius(mid, t, sy, E) < Rf:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def residual_surface_stress(Ri: float, t: float, sy: float, E: float) -> float:
    """Surface residual stress magnitude after springback (EPP): sy (0.5 - 0.5 (c/h)^2), c/h = 2 x.
    The concave face is left in tension, the convex face in compression (same magnitude)."""
    x = Ri * sy / (E * t)
    ch = min(2 * x, 1.0)
    return sy * (0.5 - 0.5 * ch ** 2)


def end_slope_deg(R: float, half_chord: float = HALF_CHORD_MM) -> float:
    return math.degrees(math.asin(min(half_chord / R, 1.0)))


def radius_for_slope(slope_deg: float, half_chord: float = HALF_CHORD_MM) -> float:
    return half_chord / math.sin(math.radians(slope_deg))


def forming_table(mid: str, t: float, slope_deg: float = BASE_CP.curve_deg) -> dict:
    """Cold slip-roll numbers for a plate: tool radius, strain, residual stress, and the final-radius scatter
    for a +/-5 % yield scatter at that tool radius (why a template and re-rolls are needed)."""
    m = load(mid)
    sy = float(m.require("yield_strength_mpa"))          # typical yield sets the forming, not the S-basis
    E = float(m.require("youngs_modulus_mpa"))
    Rf = radius_for_slope(slope_deg)
    Ri = forming_radius_for(Rf, t, sy, E)
    scat = [end_slope_deg(springback_final_radius(Ri, t, sy * f, E)) for f in (0.95, 1.05)]
    return {"material": mid, "t": t, "sy_typ": sy, "E": E, "R_final": Rf, "R_elastic_limit": elastic_limit_radius(t, sy, E),
            "R_tool": Ri, "outer_strain_pct": 100 * t / (2 * Ri + t), "elong_pct": float(m.get("elongation_pct", 0)),
            "plastic_strain_pct": 100 * (t / (2 * Ri) - sy / E), "residual_mpa": residual_surface_stress(Ri, t, sy, E),
            "slope_if_yield_x0.95_x1.05": scat, "hand_form_400mm_slope_deg":
                end_slope_deg(springback_final_radius(400.0, t, sy, E)) if 400.0 < elastic_limit_radius(t, sy, E) else 0.0}


@dataclass(frozen=True)
class Route:
    key: str
    name: str
    material: str
    static_factor: float = 1.0       # x S-basis yield
    fatigue_factor: float = 1.0      # x Basquin/Goodman amplitude
    residual: bool = False           # forming residual stress as a mean stress (cold roll)
    slope_tol: float = 0.0           # deg
    bends: tuple = ()                # ((x_mm, beta_deg), ...) per side; empty = smooth arc
    cost_usd: float = 0.0            # per plate, ASSUMPTION
    owner_can_do: bool = True
    note: str = ""


def routes(mid: str = "alu_7075_t6") -> dict[str, Route]:
    b = BASE_CP.curve_deg
    return {
        "cold_roll": Route("cold_roll", "cold slip-roll T6 to a template (re-roll until it fits)", mid, residual=True,
                           slope_tol=SLOPE_TOL_DEG["template"], cost_usd=0.0,
                           note="small plastic strain at this radius; springback is large and yield-sensitive"),
        "cold_roll_be": Route("cold_roll_be", "cold slip-roll T6, best estimate: the forming residual is compressive on "
                              "the convex (frame-side) face, which is the tension face at the hub-edge peak", mid,
                              slope_tol=SLOPE_TOL_DEG["template"], cost_usd=0.0),
        "w_temper": Route("w_temper", "solution-treat, form in W temper within 30 min, age 121 C 24 h (T62)", mid,
                          slope_tol=SLOPE_TOL_DEG["heat_treat"], cost_usd=25.0, owner_can_do=False,
                          note="heat-treat service; quench distortion, re-strike"),
        "creep_age": Route("creep_age", "clamp T6 over an over-bent form, 160-175 C 8-24 h (creep-age, T7x)", mid,
                           static_factor=T73_FACTOR, fatigue_factor=T73_FAT, slope_tol=SLOPE_TOL_DEG["template"],
                           cost_usd=5.0, note="kitchen-oven class; over-ages T6 toward T73"),
        "hot_form": Route("hot_form", "hot-form above 250 C", mid, static_factor=103.0 / 462.0, fatigue_factor=0.4,
                          slope_tol=SLOPE_TOL_DEG["template"], note="anneals toward O temper (yield ~103 MPa): reject"),
        "bend_1": Route("bend_1", "flat + 1 brake bend per side at the ear root (x 75)", mid,
                        slope_tol=SLOPE_TOL_DEG["brake"], bends=((75.0, b),)),
        "bend_2": Route("bend_2", "flat + 2 brake bends per side (x 50, 75)", mid, slope_tol=SLOPE_TOL_DEG["brake"],
                        bends=((50.0, b / 2), (75.0, b / 2))),
        "bend_3": Route("bend_3", "flat + 3 bump bends per side (x 37.5, 62.5, 87)", mid, slope_tol=SLOPE_TOL_DEG["brake"],
                        bends=((37.5, b / 3), (62.5, b / 3), (87.0, b / 3))),
    }


def route_allowables(cp: hs.CentrePlate, route: Route) -> dict:
    """Static and fatigue (R = 0, 1e5) allowables for the route, Goodman with the forming residual as mean stress."""
    from huntkit.fea.fatigue import sn_from_material
    mid = cp.material
    m = load(mid)
    su = float(m.require("ultimate_strength_mpa"))
    sy = float(m.get("yield_strength_sbasis_mpa") or m.require("yield_strength_mpa"))
    sa = float(sn_from_material(mid).stress_amplitude(1e5)) * route.fatigue_factor
    sr = 0.0
    if route.residual:
        ft_ = forming_table(mid, cp.t, cp.curve_deg)
        sr = RESID_RELAX * ft_["residual_mpa"]
    s_static = sy * route.static_factor
    su_r = su * route.static_factor
    sy_typ = float(m.require("yield_strength_mpa")) * route.static_factor
    fat = goodman_smax(sa, su_r, sr, sy_typ)
    fat = min(fat, s_static)
    return {"static": s_static, "fatigue": fat, "creep": s_static, "residual_mpa": sr, "sa_1e5": sa, "su": su_r}


def goodman_smax(sa: float, su: float, sr: float = 0.0, sy: float = math.inf) -> float:
    """Largest peak stress S of a 0 -> S cycle (R = 0) that meets Goodman at 1e5 with a residual mean stress sr that
    shakes down to sy - S where the first peak yields the surface: (S/2)/Sa + (S/2 + sr_eff)/Su = 1,
    sr_eff = clip(sy - S, 0, sr)."""
    def f(S):
        sr_eff = min(sr, max(sy - S, 0.0))
        return (S / 2) / sa + (S / 2 + sr_eff) / su - 1.0
    lo, hi = 0.0, 2 * su
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@contextlib.contextmanager
def _kinks(bends: tuple):
    """Patch hipbelt_structure.cp_model so it also applies the kink loads of a bent (faceted) plate: at each bend line x_b
    the plate tension T cos(theta_res) turns by beta_b, which presses the bend line toward the body with
    T cos(theta_res) sin(beta_b) per side, spread over the column by tributary height."""
    orig = hs.cp_model

    def model(cp, L, e_pad=0.0, theta_deg=hs.THETA_ROOT_DEG, **kw):
        mdl = orig(cp, L, e_pad=e_pad, theta_deg=theta_deg, **kw)
        th = math.radians(mdl["meta"]["theta"])
        nodes = mdl["nodes"]
        for side in (-1, 1):
            for xb, beta in bends:
                col = [n for n, p in nodes.items() if abs(p[0] - side * xb) < 1e-6]
                if not col:
                    raise ValueError(f"no grillage line at x = {xb}")
                zs = sorted(nodes[n][2] for n in col)
                trib = {}
                for n in col:
                    z = nodes[n][2]
                    i = zs.index(z)
                    trib[n] = (zs[min(i + 1, len(zs) - 1)] - zs[max(i - 1, 0)]) / 2
                s = sum(trib.values())
                F = L.T * math.cos(th) * math.sin(math.radians(beta))
                for n, w in trib.items():
                    v = mdl["loads"].setdefault(n, [0.0] * 6)
                    v[1] += -F * w / s
        return mdl
    hs.cp_model = model
    try:
        yield
    finally:
        hs.cp_model = orig


@contextlib.contextmanager
def _grid_x(extra: tuple):
    """Add grillage lines (e.g. the rim of a smaller hub, a bend line) to hipbelt_structure.X_BODY."""
    orig = hs.X_BODY
    hs.X_BODY = tuple(sorted(set(orig) | set(extra)))
    try:
        yield
    finally:
        hs.X_BODY = orig


def cp_eval(cp: hs.CentrePlate, route: Route | None = None, label: str = "") -> dict:
    """Centre plate check under a forming route: worst of the nominal end slope and +/- the route tolerance."""
    route = route or Route("as_is", "as analysed (no forming effects)", cp.material)
    al = route_allowables(cp, route)
    extra = tuple(x for x, _ in route.bends) + ((cp.hub_d / 2,) if cp.hub_d / 2 not in hs.X_BODY else ())
    worst = None
    slopes = sorted({cp.curve_deg, cp.curve_deg - route.slope_tol, cp.curve_deg + route.slope_tol})
    for c in slopes:
        cpc = replace(cp, curve_deg=c)
        scale = c / cp.curve_deg if cp.curve_deg else 1.0
        bends = tuple((x, b * scale) for x, b in route.bends)
        with _grid_x(extra), _kinks(bends):
            r = hs.cp_check(cpc)
        out = {}
        for k, v in r.items():
            s = v["sigma1_mpa"]
            if v["kind"] == "strength":
                allow, kt = al["static"], 1.0
            elif v["kind"] == "fatigue":
                allow, kt = al["fatigue"], hs.KT_FAT
            else:
                allow, kt = al["creep"], 1.0
            sf = allow / (kt * s)
            bend_sf = None
            if bends and v["kind"] == "fatigue":
                rows = v["_solve"]["rows"]
                xb = {abs(x) for x, _ in bends}
                on = [rw for rw in rows if any(abs(abs(rw["x0"][0]) - b) < 1e-6 or abs(abs(rw["x1"][0]) - b) < 1e-6
                                               for b in xb)]
                if on:
                    sb = max(rw["sigma1_mpa"] for rw in on) + v["sigma_membrane_mpa"]
                    bend_sf = allow * BEND_FAT / (kt * sb)
                    sf = min(sf, bend_sf)
            out[k] = {"sf": sf, "sigma": s, "bend": v["sigma_bend_mpa"], "membrane": v["sigma_membrane_mpa"],
                      "at": v["at"], "allow": allow, "kt": kt, "bend_line_sf": bend_sf, "slope": c,
                      "uy_max_mm": v["uy_max_mm"], "p_body_max_kpa": v["p_body_max_kpa"]}
        if worst is None:
            worst = out
        else:
            for k in out:
                if out[k]["sf"] < worst[k]["sf"]:
                    worst[k] = out[k]
    return {"label": label or route.key, "route": asdict(route), "allowables": al, "mass": cp.mass_g(),
            "cases": worst, "min_sf": min(v["sf"] for v in worst.values()),
            "governing": min(worst, key=lambda k: worst[k]["sf"])}


def arc_model_form_check(cp: hs.CentrePlate) -> dict:
    """How good is hipbelt_structure's 'shallow arc modelled flat with a reduced wing angle'? Replace the arc by 6 kinks
    (one per grillage line from the hub rim to the ear) carrying the arch normal load explicitly, nominal slope."""
    xs = (18.0, 25.0, 37.5, 50.0, 62.5, 75.0)
    seg = np.diff((0.0,) + xs + (cp.half_w,))
    w = seg[1:] / seg[1:].sum()
    bends = tuple((x, cp.curve_deg * wi) for x, wi in zip(xs, w))
    r = cp_eval(cp, Route("arc_kinks", "arc as 6 kinks (model-form check)", cp.material, bends=bends), "arc_kinks")
    for v in r["cases"].values():           # this is a model check, not a bend line: no bend knockdown
        v["sf"] = v["allow"] / (v["kt"] * v["sigma"])
    r["min_sf"] = min(v["sf"] for v in r["cases"].values())
    return r


def c1(log=print) -> dict:
    cp12 = replace(BASE_CP, material="alu_7075_t6", t=1.2)
    base = cp_eval(BASE_CP, Route("as_is", "6061-T6 1.5 as recorded", "alu_6061_t6"), "6061_1.5_record")
    base_roll = cp_eval(BASE_CP, routes("alu_6061_t6")["cold_roll"], "6061_1.5_cold_roll")
    base_be = cp_eval(BASE_CP, routes("alu_6061_t6")["cold_roll_be"], "6061_1.5_cold_roll_be")
    out = {"baseline_record": base, "baseline_cold_roll": base_roll, "baseline_cold_roll_be": base_be,
           "forming_6061_1.5": forming_table("alu_6061_t6", 1.5), "forming_7075_1.2": forming_table("alu_7075_t6", 1.2),
           "routes": {}}
    for k, r in routes().items():
        out["routes"][k] = cp_eval(cp12, r, k)
        if log:
            log(f"  C-1 {k}: min SF/req {out['routes'][k]['min_sf']:.2f} ({out['routes'][k]['governing']})")
    out["model_form_arc_6061"] = arc_model_form_check(BASE_CP)
    out["model_form_arc_7075"] = arc_model_form_check(cp12)
    out["mass_g"] = {"6061_1.5_plate": BASE_CP.mass_g()["plate_g"], "7075_1.2_plate": cp12.mass_g()["plate_g"],
                     "saved": BASE_CP.mass_g()["plate_g"] - cp12.mass_g()["plate_g"]}
    out["pin_hole"] = pin_hole_bearing([BASE_CP, cp12])
    return out


def pin_hole_bearing(cps) -> dict:
    """Ti pin (10 mm) bearing directly on the reamed plate hole (the stiff Al takes the pin load before the PA66 hub):
    V / (d t) vs 1.5 x S-basis yield (ASSUMPTION)."""
    L = hs.load_sets()
    out = {}
    for cp in cps:
        sy = cp.mat["static"]
        out[f"{cp.material}_{cp.t}"] = {k: {"bearing_mpa": L[k].V / (10.0 * cp.t),
                                            "sf": PIN_BEARING_FACTOR * sy / (L[k].V / (10.0 * cp.t))}
                                        for k in ("C2", "C1")}
    return out


# ============================================================================================== C-2 hub
def c2(cp_base: hs.CentrePlate = BASE_CP) -> dict:
    small = replace(cp_base, hub_d=28.0, hub_len=10.0)
    r_base = cp_eval(cp_base, label="hub_D36x12")
    r_small = cp_eval(small, label="hub_D28x10")
    piv_b = hs.pivot_check(cp_base, l_eng=12.0)
    piv_s = hs.pivot_check(small, l_eng=10.0)
    piv_sH = hs.pivot_check(small, l_eng=10.0, h_on_pivot=True)
    piv_bH = hs.pivot_check(cp_base, l_eng=12.0, h_on_pivot=True)
    pick = lambda p: {k: {"bore_sf": v["hub_bearing_sf"], "face_sf": v["face_sf"], "pin_sf": v["pin_sf"]}  # noqa: E731
                      for k, v in p.items()}
    return {"plate_D36": r_base, "plate_D28": r_small,
            "pivot_D36": pick(piv_b), "pivot_D28": pick(piv_s), "pivot_D36_H": pick(piv_bH), "pivot_D28_H": pick(piv_sH),
            "hub_g": {"D36x12": cp_base.mass_g()["hub_g"], "D28x10": small.mass_g()["hub_g"],
                      "saved": cp_base.mass_g()["hub_g"] - small.mass_g()["hub_g"]}}


# ============================================================================================== C-3 holes
def heywood_kt_net(d: float, D: float) -> float:
    """Net-section Kt, finite-width plate with a central hole in tension (Heywood): 2 + (1 - d/D)^3."""
    return 2.0 + (1.0 - d / D) ** 3


def _section_moment(sol: dict, x_cut: float, z_lim: float) -> float:
    """Total out-of-plane moment (N mm) carried by the x-strips that cross x = x_cut, |z| <= z_lim (linear in the member)."""
    model, res = sol["model"], sol["res"]
    M = 0.0
    for mi, mem in enumerate(model["members"]):
        if mem.get("dir") != "x" or mem["group"] == "rigid":
            continue
        p0 = np.array(model["nodes"][mem["nodes"][0]])
        p1 = np.array(model["nodes"][mem["nodes"][1]])
        if abs(p0[2]) > z_lim + 1e-6:
            continue
        lo, hi = sorted((p0[0], p1[0]))
        if not (lo <= x_cut <= hi) or hi - lo < 1e-9:
            continue
        els = res.members[mi]["elements"]
        M += max(abs(res.elem_forces[e, end][5]) for e in els for end in (0, 1))   # conservative: member max
    return M


def hole_check(cp: hs.CentrePlate, d: float, x_c: float = 42.5, route: Route | None = None) -> dict:
    """One lightening hole of diameter d per side, centred at (x_c, z 0) in the spine band (|z| <= spine_half_h).
    Net-section stress = out-of-plane bending (grillage section moment at x_c over the net width) + membrane
    (T cos theta on the net area + in-plane bending from the wing V share on the net I) ; fatigue with Heywood Kt_net."""
    route = route or Route("as_is", "", cp.material)
    al = route_allowables(cp, route)
    D = 2 * cp.spine_half_h
    out = {}
    with _grid_x(((cp.hub_d / 2,) if cp.hub_d / 2 not in hs.X_BODY else ())):
        for key, L in hs.load_sets().items():
            sol = hs.cp_solve(cp, L)
            Mo = _section_moment(sol, x_c, cp.spine_half_h)
            th = math.radians(hs.theta_residual(cp))
            V_w = hs.WING_V_SHARE * L.V
            ear = hs.StitchedEar()
            x_row = cp.half_w_body + (ear.row_x[1] - 75.0) * cp.ear_w / 30.0 * ear.first_row_share + \
                cp.half_w_body + (ear.row_x[0] - 75.0) * cp.ear_w / 30.0 * (1 - ear.first_row_share) - cp.half_w_body
            Mi = V_w * (x_row - x_c)
            dn = min(d, D - 1e-6)
            A_n = (D - dn) * cp.t
            I_n = cp.t * (D ** 3 - dn ** 3) / 12
            s_bend = 6 * Mo / ((D - dn) * cp.t ** 2)
            s_mem = L.T * math.cos(th) / A_n + Mi * (D / 2) / I_n
            tau = 1.5 * V_w / A_n
            s_m1 = s_mem / 2 + math.sqrt((s_mem / 2) ** 2 + tau ** 2)
            s = s_bend + s_m1
            kt = heywood_kt_net(dn, D) if d > 0 else hs.KT_FAT
            if L.kind == "strength":
                sf = al["static"] / s
            elif L.kind == "fatigue":
                sf = al["fatigue"] / (kt * s)
            else:
                sf = al["creep"] / s
            out[key] = {"sf": sf, "sigma_net": s, "kt": kt, "M_out": Mo, "M_in": Mi}
    rho = cp.mat["rho"] * 1e-6
    return {"d": d, "cases": out, "min_sf": min(v["sf"] for v in out.values()),
            "saved_g": 2 * math.pi / 4 * d ** 2 * cp.t * rho}


def c3(cps: dict | None = None, ds=(0, 10, 15, 20, 25, 28, 31)) -> dict:
    cps = cps or {"6061_1.5": (BASE_CP, None), "7075_1.2_cold_roll": (replace(BASE_CP, material="alu_7075_t6", t=1.2),
                                                                     routes()["cold_roll"])}
    out = {}
    for name, (cp, rt) in cps.items():
        rows = [hole_check(cp, d, route=rt) for d in ds]
        nominal = rows[0]["min_sf"]
        # plate-level SF without the hole (governs at the hub edge) for comparison
        out[name] = {"rows": rows, "no_hole_section_min_sf": nominal}
    return out


# ============================================================================================== C-4 pad backer
EVA_RAIL = ("eva_foam_45c", 6.0)
CHANNEL_W = 70.0          # corrie_body.md 11.2a
RAIL_W = 55.0
RAIL_H = 140.0
BACKER_W, BACKER_H = 190.0, 150.0
DEPTH_PLAY = 4.5          # corrie_body.md 11.2a: 4.5 mm depth play between the backer slip liner and the bow-tie
SPINE_ZONE = (CHANNEL_W / 2, 30.0)   # contact zone in the channel: |x| < 35, |z| <= 30 (bow-tie spine band)
HDPE_CREEP_E_RATIO = 0.35  # ASSUMPTION: HDPE 1000 h creep modulus / short-term modulus at ~5 MPa, 23-40 C
HDPE_HOT = 0.8             # ASSUMPTION: same hot knockdown as the belt polymers


def _foam_E(mid: str) -> float:
    from huntkit.gendesign import hipbelt as hb
    return hb._foam_E_kpa(mid) / 1000.0          # MPa


def body_k_lumbar() -> float:
    return hs.foundation_k()                     # B lumbar stack + 25 mm tissue, N/mm^3


@dataclass(frozen=True)
class Backer:
    material: str = "hdpe_sheet"
    t: float = 1.0
    E_ratio: float = 1.0          # creep modulus ratio (1 = short term)

    @property
    def E(self) -> float:
        m = load(self.material)
        E = float(m.get("flexural_modulus_mpa") or m.get("youngs_modulus_mpa"))
        return E * self.E_ratio

    @property
    def nu(self) -> float:
        return float(load(self.material).get("poisson", 0.35))

    def mass_g(self) -> float:
        return BACKER_W * BACKER_H * self.t * float(load(self.material).require("density_kg_m3")) * 1e-6


def backer_solve(bk: Backer, H: float, h: float = 2.5, contact: bool = True, k_body: float | None = None) -> dict:
    """Backer plate (x across, y = z up) between the body foundation and the EVA rails; w > 0 toward the frame.
    The body approaches by d0 (bisection to total force H): body pressure k_b (d0 - w), rails k_r w, unilateral contact
    with the bow-tie spine at w >= DEPTH_PLAY in the channel. Returns stresses, deflection and the contact force."""
    from huntkit.fea.plate_grid import GridPlate, Spring, iso_D
    k_b = k_body or body_k_lumbar()
    k_r = _foam_E(EVA_RAIL[0]) / EVA_RAIL[1]
    nx, ny = int(round(BACKER_W / h)), int(round(BACKER_H / h))
    pl = GridPlate(-BACKER_W / 2, -BACKER_H / 2, nx, ny, h, iso_D(bk.E, bk.t, bk.nu))
    xy = pl.node_xy()
    i = np.arange(pl.nn) % (nx + 1)
    j = np.arange(pl.nn) // (nx + 1)
    trib = h * h * np.where((i == 0) | (i == nx), 0.5, 1.0) * np.where((j == 0) | (j == ny), 0.5, 1.0)
    on_rail = (np.abs(xy[:, 0]) >= CHANNEL_W / 2) & (np.abs(xy[:, 0]) <= CHANNEL_W / 2 + RAIL_W) & \
              (np.abs(xy[:, 1]) <= RAIL_H / 2)
    zone = (np.abs(xy[:, 0]) < SPINE_ZONE[0]) & (np.abs(xy[:, 1]) <= SPINE_ZONE[1])
    for n in range(pl.nn):
        k = k_b * trib[n] + (k_r * trib[n] if on_rail[n] else 0.0)
        pl.springs.append(Spring(n, k, 0.0, None, unilateral=False, tag="found"))
    nfound = len(pl.springs)
    if contact:
        for n in np.nonzero(zone)[0]:
            pl.springs.append(Spring(int(n), 0.0, DEPTH_PLAY, None, unilateral=True, tag="spine"))
    unit = k_b * trib

    def run(d0):
        f = np.zeros(pl.ndof)
        f[0:pl.ndof_plate:3] = unit * d0
        r = pl.solve(f, k_pen=50.0)
        w = r["w"]
        p_body = k_b * (d0 - w)
        F_body = float((p_body * trib).sum())
        F_spine = float(r["spring_force"][nfound:].sum()) if contact else 0.0
        return r, w, p_body, F_body, F_spine
    lo, hi = 0.0, 4 * H / (k_b * BACKER_W * BACKER_H) + 50.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        r, w, pb, Fb, Fs = run(mid)
        if Fb < H:
            lo = mid
        else:
            hi = mid
        if abs(Fb - H) < 1e-3 * H:
            break
    M = pl.moments(r["u"])
    s = 6 * M / bk.t ** 2
    sx, sy, txy = s[..., 0], s[..., 1], s[..., 2]
    s1 = (sx + sy) / 2 + np.sqrt(((sx - sy) / 2) ** 2 + txy ** 2)
    s2 = (sx + sy) / 2 - np.sqrt(((sx - sy) / 2) ** 2 + txy ** 2)
    smax = float(np.max(np.maximum(np.abs(s1), np.abs(s2))))
    wc = w[(np.abs(xy[:, 0]) < CHANNEL_W / 2) & (np.abs(xy[:, 1]) <= RAIL_H / 2)]
    wr = w[on_rail]
    return {"t": bk.t, "material": bk.material, "E": bk.E, "H": H, "d0": mid, "F_body": Fb, "F_spine": Fs,
            "spine_share": Fs / H, "w_channel_max": float(wc.max()), "w_rail_mean": float(wr.mean()),
            "sag_rel_rails": float(wc.max() - wr.mean()), "sigma_max": smax,
            "p_body_min_kpa": float(pb.min() * 1000), "p_body_max_kpa": float(pb.max() * 1000),
            "_w": pl.w_grid(r["u"]), "_grid": (pl.x0, pl.y0, nx, ny, h)}


def backer_check(bk: Backer) -> dict:
    """C2 strength (short-term E), walking fatigue range (creep E: the sustained part has crept), carry creep (creep E)."""
    L = hs.load_sets()
    m = load(bk.material)
    is_hdpe = bk.material in ("hdpe_sheet", "uhmwpe_sheet")
    if is_hdpe:
        ys = float(m.require("yield_strength_mpa")) * HDPE_HOT
        fat, creep = hs.HDPE_FATIGUE_MPA, hs.HDPE_SUSTAINED_MPA
        er = HDPE_CREEP_E_RATIO
    else:
        mat = hs.cp_material(bk.material) if bk.material.startswith("alu") else None
        if mat:
            ys, fat, creep, er = mat["static"], mat["fatigue"] / hs.KT_FAT, mat["static"], 1.0
        else:                                   # CFRP plate (smeared record): first-ply ~ UTS x 0.8 x 0.65 (comp)
            uts = float(m.require("compressive_strength_mpa")) * 0.8 * 0.65
            ys, fat, creep, er = uts, 0.5 * uts, uts, 1.0
    c2 = backer_solve(bk, L["C2"].H)
    walk = backer_solve(replace(bk, E_ratio=er), L["walk"].H)
    carry = backer_solve(replace(bk, E_ratio=er), L["carry"].H)
    walk_st = backer_solve(bk, L["walk"].H)
    rows = {"C2": {"sigma": c2["sigma_max"], "allow": ys, "sf": ys / c2["sigma_max"]},
            "walk": {"sigma": walk_st["sigma_max"], "allow": fat, "sf": fat / walk_st["sigma_max"]},
            "carry": {"sigma": carry["sigma_max"], "allow": creep, "sf": creep / carry["sigma_max"]}}
    contact = {"carry_crept_w": carry["w_channel_max"], "walk_crept_w": walk["w_channel_max"],
               "walk_crept_spine_share": walk["spine_share"], "C2_spine_share": c2["spine_share"],
               "carry_spine_share": carry["spine_share"],
               "play_margin_walk": DEPTH_PLAY / max(walk["w_channel_max"], 1e-9)}
    func_ok = walk["spine_share"] <= 1e-3
    sf_min = min(v["sf"] for v in rows.values())
    return {"backer": asdict(bk), "mass_g": bk.mass_g(), "cases": rows, "contact": contact, "min_sf": sf_min,
            "functional_ok": func_ok, "pass": sf_min >= 1.0 and func_ok,
            "_fields": {"C2": c2, "walk": walk, "carry": carry}}


def c4() -> dict:
    cands = [Backer("hdpe_sheet", 0.8), Backer("hdpe_sheet", 1.0), Backer("hdpe_sheet", 1.5), Backer("hdpe_sheet", 2.0),
             Backer("hdpe_sheet", 2.5), Backer("hdpe_sheet", 3.0), Backer("alu_6061_t6", 0.5), Backer("alu_6061_t6", 0.8),
             Backer("cfrp_plate_quasi_iso", 0.5), Backer("cfrp_plate_quasi_iso", 0.8)]
    rows = {f"{b.material}_{b.t}": backer_check(b) for b in cands}
    return {"k_body": body_k_lumbar(), "k_rail": _foam_E(EVA_RAIL[0]) / EVA_RAIL[1], "rows": rows}


# ============================================================================================== C-7 yoke plate
YOKE_OUTLINE = [(-108, -18), (-84, -46), (84, -46), (108, -18), (96, 34), (42, 50), (-42, 50), (-96, 34)]
#   designs/pack_5200/build_geometry.py YOKE_OUTLINE (x across, v along the crown axis, origin at the yoke anchor)
SPINE_HALF_W = 23.0       # crown spine 46 mm wide (huntkit/viz3d/params.py spine_w): the yoke is clamped on it
STRAP_PIN = (46.0, -10.0)  # strap-top quick-connect (huntkit/viz3d/model.py: strap starts at x +/-46, z yoke - 10)
PIN_D = 6.0               # ASSUMPTION: Ti quick-connect pin 6 mm (DESIGN.md 5.3: webbing loop + Ti pin)
PIN_PATCH = 14.0          # ASSUMPTION: out-of-plane strap load enters over a 14 mm disc (pin + washer / clevis)
YOKE_PAD = (("eva_foam_45c", 10.0),)   # ASSUMPTION: yoke pad 10 mm EVA 45C
SCAP_TISSUE_MM = 15.0     # ASSUMPTION: soft tissue over the scapulae / upper back (lumbar 25, crest 12 in hipbelt.py)
YOKE_PLY = "cfrp_t700_ud_epoxy_ply"
YOKE_LAYUP = "[0/45/-45/90]s"          # ASSUMPTION: 8-ply QI; ply t = t / 8


def _poly_contains(poly, x, y):
    from matplotlib.path import Path as MPath
    return MPath(np.array(poly)).contains_points(np.c_[x, y])


def yoke_laminate(t: float):
    from huntkit.fea.composite import Laminate, Ply
    return Laminate.from_layup(YOKE_LAYUP, Ply.from_material(YOKE_PLY, t / 8))


def laminate_fi(lam, N: np.ndarray, M: np.ndarray, knockdown=None) -> np.ndarray:
    """Tsai-Wu FI for running loads N (..., 3) and moments M (..., 3) on a symmetric laminate (B = 0)."""
    from huntkit.fea.composite import DEFAULT_KNOCKDOWN, Q_matrix, T_eps, tsai_wu_fi_vec
    kd = DEFAULT_KNOCKDOWN if knockdown is None else knockdown
    shp = M.shape[:-1]
    Nf = np.broadcast_to(N, M.shape).reshape(-1, 3)
    Mf = M.reshape(-1, 3)
    e0 = Nf @ np.linalg.inv(lam.A).T
    kap = Mf @ np.linalg.inv(lam.D).T
    best = np.zeros(len(Mf))
    for i, (p, a) in enumerate(zip(lam.plies, lam.angles)):
        pk = p.knocked_down(kd)
        for zz in (lam.z[i], lam.z[i + 1]):
            sig = (Q_matrix(p) @ T_eps(a) @ (e0 + zz * kap).T).T
            best = np.maximum(best, tsai_wu_fi_vec(sig, pk))
    return best.reshape(shp)


def yoke_k_body() -> float:
    from huntkit.gendesign import hipbelt as hb
    return hb._k_stack(tuple(hb.FoamLayer(m, t) for m, t in YOKE_PAD), SCAP_TISSUE_MM)


def yoke_loads(torsos=(15, 19, 23), log=None) -> list[dict]:
    """Shoulder-harness reaction at the yoke node of the rev C beam model (frame.yaml), every case x torso, both
    couple variants, factored (x the case factor). Lifters anchor on the crown (DESIGN.md D-2), not on the yoke."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import ls1_envelope
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    out = []
    for t in torsos:
        fm = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=False), 95.0)
        sh = fm["groups"]["shoulder"]
        for variant, cases in ls1_envelope("C").items():
            for c in cases:
                if c.name == "tall_load_posts":
                    continue
                c = copy.copy(c)
                c.buckling = False
                res = c.run(fm)
                F = sum(np.asarray(res.reactions.get(n, np.zeros(6)))[:3] for n in sh)
                out.append({"case": c.name, "variant": variant, "torso": t, "factor": float(c.required_sf),
                            "g": float(c.g_factor) if hasattr(c, "g_factor") else None,
                            "F_1g_case": [float(v) for v in F]})
    return out


def yoke_plate(t: float, F: np.ndarray, factor: float, h: float = 2.0, pad_model: str = "winkler",
               k_body: float | None = None, side_split=(0.5, 0.5)) -> dict:
    """ACM plate of the yoke outline, w = +y (aft, toward the frame). Clamp: w = 0 on |x| <= 23 (crown spine, bonded +
    bolted). F = (Fx, Fy, Fz) on the frame at the yoke (case g, unfactored); x factor here.
    Fy < 0: the straps pull the yoke toward the body: two point loads at the strap pins (side_split).
    Fy > 0: the body pushes the yoke pad aft: Winkler body foundation (pad + tissue) driven to total Fy, or a uniform
    pressure bound. In-plane (Fx, Fz) goes to the pins (bearing) and as membrane running loads at the clamp line."""
    from huntkit.fea.plate_grid import GridPlate, Spring
    lam = yoke_laminate(t)
    xs = [p[0] for p in YOKE_OUTLINE]
    vs = [p[1] for p in YOKE_OUTLINE]
    x0, v0 = min(xs), min(vs)
    nx, ny = int(round((max(xs) - x0) / h)), int(round((max(vs) - v0) / h))
    pl = GridPlate(x0, v0, nx, ny, h, lam.D)
    ec = pl.elem_xy()
    pl.active = _poly_contains(YOKE_OUTLINE, ec[..., 0].ravel(), ec[..., 1].ravel()).reshape(nx, ny)
    pl._K0 = None
    xy = pl.node_xy()
    act_n = pl.active_nodes()
    clamp = act_n & (np.abs(xy[:, 0]) <= SPINE_HALF_W + 1e-6)
    pl.fix_w(np.nonzero(clamp)[0])
    for n in np.nonzero(clamp)[0]:                 # rotations on the spine face held too (bonded patch)
        pl.fixed.update((3 * int(n) + 1, 3 * int(n) + 2))
    Fx, Fy, Fz = (float(v) * factor for v in F)
    f = np.zeros(pl.ndof)
    if Fy < 0:
        q = np.zeros((nx, ny))
        for s, share in zip((-1, 1), side_split):
            q += pl.patch_pressure(s * STRAP_PIN[0], STRAP_PIN[1], PIN_PATCH, Fy * share)
        f = pl.load_vector(q_elem=q)
        r = pl.solve(f)
        d0 = None
    else:
        i = np.arange(pl.nn) % (nx + 1)
        j = np.arange(pl.nn) // (nx + 1)
        # tributary area of active elements per node
        trib = np.zeros(pl.nn)
        np.add.at(trib, pl.enodes[pl.active].ravel(), h * h / 4)
        free_n = act_n & ~clamp
        if pad_model == "uniform":
            A = float(pl.active.sum() * h * h)
            r = pl.solve(pl.load_vector(q_elem=np.full((nx, ny), Fy / A)))
            d0 = None
        else:
            kb = k_body or yoke_k_body()
            for n in np.nonzero(free_n)[0]:
                pl.springs.append(Spring(int(n), kb * trib[n], 0.0, None, unilateral=False))
            # body moves by d0 everywhere; on the clamp the plate does not move, so the body force there is kb d0 A_c
            unit = np.zeros(pl.ndof)
            unit[0:pl.ndof_plate:3] = np.where(free_n, kb * trib, 0.0)
            r1 = pl.solve(unit)
            w1 = r1["w"]
            F1 = float((kb * trib * (1.0 - np.where(free_n, w1, 0.0)))[act_n].sum())
            d0 = Fy / F1
            r = {"u": r1["u"] * d0, "w": w1 * d0}
    M = pl.moments(r["u"])                                 # (nx, ny, 4, 3)
    h_root = float(np.ptp(xy[act_n & (np.abs(np.abs(xy[:, 0]) - SPINE_HALF_W) < h / 2), 1])) or 90.0
    lever = STRAP_PIN[0] - SPINE_HALF_W
    side = max(side_split)
    Fz_s, Fx_s = Fz * side, abs(Fx)
    Nxy = Fz_s / h_root                                    # in-plane shear at the clamp line
    Nx_b = 6 * Fz_s * lever / h_root ** 2                  # in-plane bending of the root section (extreme fibre)
    Nx = Fx_s / h_root
    N_root = np.array([Nx + Nx_b, 0.0, Nxy])
    fi_b = laminate_fi(lam, np.zeros(3), M)
    fi = np.max(fi_b, axis=2)
    ij = np.unravel_index(np.argmax(fi), fi.shape)
    fi_comb = float(np.max(laminate_fi(lam, N_root, M[ij[0], ij[1]])))
    # pin: bearing, net tension, shear-out (record allowables x hot/wet 0.8)
    rec = load("cfrp_plate_quasi_iso")
    P_pin = math.hypot(Fz_s, Fx_s)
    brg = P_pin / (PIN_D * t)
    e_edge = STRAP_PIN[1] - min(vs)                        # to the bottom edge, along -v
    so = P_pin / (2 * e_edge * t)
    out = {"t": t, "F_factored": [Fx, Fy, Fz], "fi_bend_max": float(fi.max()), "fi_combined": fi_comb,
           "at_xy": [float(ec[ij][0]), float(ec[ij][1])], "w_max": float(np.max(np.abs(r["w"]))), "d0": d0,
           "pin_bearing_mpa": brg, "pin_bearing_sf": 0.8 * float(rec.require("bearing_strength_mpa")) / max(brg, 1e-9),
           "shear_out_mpa": so, "shear_out_sf": 0.8 * 0.5 * float(rec.require("ultimate_strength_mpa")) / max(so, 1e-9),
           "_fi": fi, "_w": pl.w_grid(r["u"]), "_grid": (pl.x0, pl.y0, nx, ny, h), "_active": pl.active}
    return out


def c7(ts=(1.5, 1.2), log=print) -> dict:
    loads = yoke_loads()
    res = {}
    for t in ts:
        rows = []
        for L in loads:
            F = np.array(L["F_1g_case"])
            if not np.any(np.abs(F) > 1e-6):
                continue
            kind = "ultimate" if L["factor"] <= 1.0 else "limit"
            split = (0.25, 0.75) if L["case"] == "side_hill_torsion" else (0.5, 0.5)   # downhill strap slack (C3)
            r = yoke_plate(t, F, L["factor"], side_split=split)
            row = {k: v for k, v in r.items() if not k.startswith("_")}
            row.update({"case": L["case"], "variant": L["variant"], "torso": L["torso"], "factor": L["factor"],
                        "kind": kind, "sf": 1.0 / max(r["fi_combined"], 1e-9)})
            if L["F_1g_case"][1] > 0:          # pad push: also the uniform-pressure bound
                u = yoke_plate(t, F, L["factor"], pad_model="uniform", side_split=split)
                row["sf_uniform_bound"] = 1.0 / max(u["fi_combined"], 1e-9)
                for kf in (0.5, 2.0):
                    s = yoke_plate(t, F, L["factor"], k_body=yoke_k_body() * kf, side_split=split)
                    row[f"sf_kbody_x{kf}"] = 1.0 / max(s["fi_combined"], 1e-9)
            rows.append(row)
        # fatigue: C1 static carry at 1.6 g (unfactored), FI <= 0.5
        fat = []
        for L in loads:
            if L["case"] != "static_carry":
                continue
            r = yoke_plate(t, np.array(L["F_1g_case"]) * ls.G_WALK, 1.0)
            fat.append({"variant": L["variant"], "torso": L["torso"], "fi": r["fi_combined"],
                        "sf": 0.5 / max(r["fi_combined"], 1e-9)})
        gov = min(rows, key=lambda r: min(r["sf"], r["pin_bearing_sf"], r["shear_out_sf"]))
        res[f"{t}"] = {"rows": rows, "fatigue": fat, "min_sf": min(r["sf"] for r in rows),
                       "min_sf_fatigue": min(f["sf"] for f in fat), "governing": f"{gov['case']}|{gov['torso']}",
                       "min_pin_sf": min(min(r["pin_bearing_sf"], r["shear_out_sf"]) for r in rows),
                       "mass_g": hs_poly_area() * t * 1550e-6}
        if log:
            log(f"  C-7 t {t}: strength {res[f'{t}']['min_sf']:.2f}, fatigue {res[f'{t}']['min_sf_fatigue']:.2f}")
    res["saved_g"] = res[f"{ts[0]}"]["mass_g"] - res[f"{ts[1]}"]["mass_g"]
    res["k_body"] = yoke_k_body()
    res["loads"] = loads
    return res


def hs_poly_area() -> float:
    P = YOKE_OUTLINE
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1])))


def thinnest_passing_yoke(ts=(1.5, 1.35, 1.2), log=None) -> dict:
    return c7(ts=ts, log=log)


# ============================================================================================== C-9 printed body
FAT_G = 1.6
U_LO, U_HI = 0.30, 0.55   # ASSUMPTION: full offset where the smoothed utilisation is below 0.30, none above 0.55
SMOOTH_MM = 8.0           # ASSUMPTION: utilisation max-filtered over 8 mm (protects the neighbours of a hot spot)
R_FRAC = 0.30             # never remove more than 30 % of the local radius (no ligament vanishes)


def _verify_fields(dom, solid, sets, material="pa12_cf_fdm_paht", log=print) -> dict:
    """Same FI99 rule as frame_cg_recheck.verify_sets, but returns per-voxel fields: strength envelope (max FI over
    every factored set), and the static-carry fatigue / creep utilisations (FI at 1.6 g / fatigue ratio; FI at 1 g /
    creep ratio). Rows per set as verify_sets."""
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    m = load(material)
    E = float(m.require("youngs_modulus_xy_mpa"))
    s_xy = float(m.require("tensile_strength_xy_mpa"))
    s_z = float(m.require("tensile_strength_z_mpa"))
    knock = float(m.get("env_knockdown_ratio", 0.8))
    fat_r = float(m.get("fatigue_1e5_ratio", 0.3))
    rup_r = float(m.get("creep_rupture_8h_40c_ratio", 0.4))
    t0 = time.time()
    g = dom.grid
    idx = np.where(solid)[0]
    cen = g.elem_centers()[idx]
    _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    clamp = np.zeros(g.nn, bool)
    clamp[np.where(fixed[0::3])[0]] = True
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(g.h, 1.0, ft.NU))
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    K.sort_indices()
    try:
        import pypardiso
        solver = pypardiso.PyPardisoSolver(mtype=2)
        solver.factorize(K)
        solve = lambda Fr: solver.solve(K, np.ascontiguousarray(Fr))  # noqa: E731
    except ImportError:                    # pragma: no cover
        import scipy.sparse as sps
        import scipy.sparse.linalg as spla
        lu = spla.splu((K + sps.triu(K, 1).T).tocsc())
        solve = lu.solve
        solver = None
    tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
    rows = []
    env = np.zeros(idx.size)
    fat = np.zeros(idx.size)
    exu = np.zeros(idx.size, bool)
    for tg in tags:
        tsets = [s for s in sets if s.key.split(":")[0] == tg]
        F, _ = ft.assemble_loads(dom, tsets, solid_mask=solid)
        Ur = solve(F[rs.free]).reshape(rs.free.size, -1)
        U = np.zeros((g.ndof, len(tsets)))
        U[rs.free] = Ur / E
        Fn = np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2))
        ex = (clamp | (Fn > 0))[g.enodes].any(axis=1)[idx]
        exu |= ex
        del F, Ur
        for k, s in enumerate(tsets):
            _, S = ft.element_stress(g, U[:, k], solid, E)
            fi = ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, s_xy, s_z, knock)
            ok = fi[~ex]
            fi99 = float(np.percentile(ok, 99))
            pk = np.where(~ex)[0][np.argmax(ok)]
            rows.append({"set": s.key, "scenario": tg, "case": s.case, "torso": s.torso, "factor": s.factor,
                         "fi99": fi99, "sf": 1.0 / max(fi99, 1e-9), "where": R.region_label(cen[pk]),
                         "peak_xyz": [float(v) for v in cen[pk]]})
            env = np.maximum(env, np.where(ex, 0.0, fi))
            if s.case == "static_carry":
                fat = np.maximum(fat, np.where(ex, 0.0, fi * (FAT_G / s.factor) / fat_r))
        del U
        if log:
            log(f"    voxel [{tg}] {len(tsets)} sets, {time.time() - t0:.0f} s")
    if solver is not None:
        try:
            solver.free_memory(everything=True)
        except Exception:
            pass
    return {"rows": rows, "env": env, "fat": fat, "ex": exu, "idx": idx, "fat_ratio": fat_r, "creep_ratio": rup_r,
            "seconds": time.time() - t0}


def body_margins(rows: list, fat_r: float = 0.3, rup_r: float = 0.4) -> dict:
    """Per scenario tag: strength (min SF over sets), fatigue and creep from the static-carry sets (summarize_body)."""
    from . import frame_cg_recheck as R
    out = {}
    for tg in dict.fromkeys(r["scenario"] for r in rows):
        b = R.summarize_body(rows, tg, fat_r, rup_r)
        out[tg] = {"strength": b["sf_min"], "governing": b["governing"], "where": b["where"],
                   "fatigue": b["sf_fatigue"], "creep": b["sf_creep"]}
    out["min"] = {k: min(v[k] for t, v in out.items() if t != "min") for k in ("strength", "fatigue", "creep")}
    return out


def offset_field(dom, solid, util: np.ndarray, delta_max: float) -> np.ndarray:
    """Inward offset (mm) per element: delta_max where the max-filtered utilisation is below U_LO, tapering to 0 at
    U_HI, capped at R_FRAC x the local radius (max of -sdf within 10 mm), 0 on passive elements."""
    from scipy import ndimage

    from . import spreader as S
    from .spreader_layout import frame_sdf_layout
    g = dom.grid
    U = np.zeros(g.ne)
    U[np.where(solid)[0]] = util
    U3 = g.to_array(U)
    r = max(1, int(round(SMOOTH_MM / g.h)))
    U3 = ndimage.maximum_filter(U3, size=2 * r + 1)
    Us = g.from_array(U3)
    ramp = np.clip((U_HI - Us) / (U_HI - U_LO), 0.0, 1.0)
    sdf = frame_sdf_layout(g.elem_centers(), None, S.SCALE)
    depth = g.from_array(ndimage.maximum_filter(g.to_array(np.maximum(-sdf, 0.0)), size=2 * int(round(10.0 / g.h)) + 1))
    d = np.minimum(delta_max * ramp, R_FRAC * depth)
    d[dom.passive_solid | dom.passive_void] = 0.0
    return d, sdf


def c9(deltas=(0.0, 0.75, 1.25, 1.75, 2.5), log=print, save: bool = True) -> dict:
    """Utilisation-guided inward offset of the production branch body; every candidate re-verified (rev C, FI99)."""
    from . import frame_production as prod
    from . import rev_c_verification as V
    from .frame_branch import solid_mass_g
    from .spreader_layout import raster
    t0 = time.time()
    sets, _ = V.beam_runs(buckling=False, log=None)
    dom, solid0 = raster(None, 2.0)
    base = _verify_fields(dom, solid0, sets, log=log)
    util0 = np.maximum(base["env"], base["fat"])
    cands = []
    for dm in deltas:
        if dm == 0.0:
            vr, solid = base, solid0
        else:
            d, sdf = offset_field(dom, solid0, util0, dm)
            solid = ((sdf + d) <= 0.0) | dom.passive_solid
            solid &= ~dom.passive_void
            solid = prod._largest_with_pivot(dom, solid)
            vr = _verify_fields(dom, solid, sets, log=log)
        mg = body_margins(vr["rows"], vr["fat_ratio"], vr["creep_ratio"])
        removed = solid0 & ~solid
        cen = dom.grid.elem_centers()[removed]
        from . import frame_cg_recheck as R
        regions = {}
        for p in cen:
            k = R.region_label(p)
            regions[k] = regions.get(k, 0) + 1
        vox_g = dom.grid.h ** 3 * 1060e-6
        cands.append({"delta_max_mm": dm, "body_g": solid_mass_g(solid, 2.0), "margins": mg,
                      "removed_g_by_region": {k: v * vox_g for k, v in sorted(regions.items(), key=lambda kv: -kv[1])},
                      "added_vox": int((solid & ~solid0).sum())})
        if log:
            log(f"  C-9 delta {dm}: body {cands[-1]['body_g']:.1f} g, strength {mg['min']['strength']:.3f}, "
                f"fatigue {mg['min']['fatigue']:.3f}, creep {mg['min']['creep']:.3f}  ({time.time() - t0:.0f} s)")
    out = {"date": DATE, "method": "inward SDF offset where max-filtered utilisation < U_HI, capped at 0.3 local radius",
           "params": {"U_LO": U_LO, "U_HI": U_HI, "SMOOTH_MM": SMOOTH_MM, "R_FRAC": R_FRAC},
           "candidates": cands, "seconds": time.time() - t0}
    base_g = cands[0]["body_g"]
    for c in cands:
        c["saved_g"] = base_g - c["body_g"]
    ok = [c for c in cands if c["margins"]["min"]["fatigue"] >= 1.0 and c["margins"]["min"]["strength"] >= 1.0
          and c["margins"]["min"]["creep"] >= 1.0]
    out["best"] = max(ok, key=lambda c: c["saved_g"]) if ok else None
    if save:
        C9_JSON.parent.mkdir(parents=True, exist_ok=True)
        C9_JSON.write_text(json.dumps(out, indent=1, default=float))
        np.savez_compressed(C9_JSON.with_suffix(".npz"), util=util0, idx=base["idx"])
    return out


# ============================================================================================== run all
def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [_strip(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def combined_plate() -> dict:
    """C-1 (7075-T6 1.2, cold-rolled to a template) + C-2 (hub D28 x 10) on one plate; C-3 held out (see c3)."""
    cp = replace(BASE_CP, material="alu_7075_t6", t=1.2, hub_d=28.0, hub_len=10.0)
    r = cp_eval(cp, routes()["cold_roll"], "C1+C2")
    r["saved_vs_base_g"] = BASE_CP.mass_g()["total_g"] - cp.mass_g()["total_g"]
    return r


def run(c9_result: dict | None = None, log=print, write: bool = True) -> dict:
    t0 = time.time()
    res = {"date": DATE, "standard": "HA-LS-1 rev C", "loads_belt": {k: asdict(v) for k, v in hs.load_sets().items()}}
    log("C-1 centre plate 7075")
    res["C1"] = c1(log=log)
    log("C-2 hub")
    res["C2"] = c2()
    log("C-3 holes")
    res["C3"] = c3()
    res["C1_C2"] = combined_plate()
    log("C-4 backer")
    res["C4"] = c4()
    log("C-7 yoke")
    res["C7"] = c7(ts=(1.5, 1.2), log=log)
    if c9_result is None and C9_JSON.exists():
        c9_result = json.loads(C9_JSON.read_text())
    res["C9"] = c9_result
    res["verdicts"] = verdicts(res)
    res["seconds"] = time.time() - t0
    if write:
        OUT_JSON.write_text(json.dumps(_strip(res), indent=1, default=float))
    return res


def verdicts(res: dict) -> list[dict]:
    """One row per item: verdict, real grams saved, governing margin, tests needed. Thresholds: SF/req >= 1.0 on every
    strength / fatigue / creep check, and the functional rules (C-4: the backer never touches the bow-tie spine)."""
    V = []
    c1r = res["C1"]["routes"]
    cr = c1r["cold_roll"]
    V.append({"id": "C-1", "item": "belt-B centre plate 7075-T6 1.2 mm", "saved_g": res["C1"]["mass_g"]["saved"],
              "route": "cold slip-roll T6 to a template", "min_sf": cr["min_sf"], "governing": cr["governing"],
              "verdict": "PASS" if cr["min_sf"] >= 1.0 else "FAIL",
              "tests": "HB-5 plate proof + 1e5 cycles on a 7075 plate; template check of the end slope (14.6 +/- 2 deg)"})
    p2 = res["C2"]
    m2 = min(min(v["sf"] for v in p2["plate_D28"]["cases"].values()),
             min(v["bore_sf"] for v in p2["pivot_D28"].values()))
    V.append({"id": "C-2", "item": "PA66 hub D36x12 -> D28x10", "saved_g": p2["hub_g"]["saved"], "min_sf": m2,
              "governing": "plate at the hub rim" if min(v["sf"] for v in p2["plate_D28"]["cases"].values()) <= m2
              else "hub bore bearing", "verdict": "PASS" if m2 >= 1.0 else "FAIL",
              "tests": "covered by HB-5 (hub on the Ti pin)"})
    c3r = res["C3"]["6061_1.5"]["rows"]
    tgt = min((r for r in c3r if r["saved_g"] >= 4.9), key=lambda r: r["d"], default=c3r[-1])
    best = max((r for r in c3r if r["min_sf"] >= 1.0 and r["d"] > 0), key=lambda r: r["saved_g"], default=None)
    V.append({"id": "C-3", "item": "lightening holes in the spine", "saved_g": best["saved_g"] if best else 0.0,
              "min_sf": tgt["min_sf"], "governing": f"net section, d {tgt['d']} mm for {tgt['saved_g']:.1f} g",
              "verdict": "PASS" if tgt["min_sf"] >= 1.0 else ("PARTIAL" if best else "FAIL"),
              "tests": "HB-5 with the holes"})
    r4 = res["C4"]["rows"]
    b08, b10 = r4["hdpe_sheet_0.8"], r4["hdpe_sheet_1.0"]
    V.append({"id": "C-4", "item": "HDPE pad backer 1.0 -> 0.8 mm", "saved_g": b10["mass_g"] - b08["mass_g"],
              "min_sf": b08["min_sf"], "governing": "see C4 rows", "verdict": "PASS" if b08["pass"] else "FAIL",
              "tests": "HB-1 fit + a sag check of the pad seat under 413 N held 8 h"})
    c7r = res["C7"]
    m7 = min(c7r["1.2"]["min_sf"], c7r["1.2"]["min_sf_fatigue"], c7r["1.2"]["min_pin_sf"])
    V.append({"id": "C-7", "item": "CFRP yoke plate 1.5 -> 1.2 mm", "saved_g": c7r["saved_g"], "min_sf": m7,
              "governing": c7r["1.2"]["governing"], "verdict": "PASS" if m7 >= 1.0 else "FAIL",
              "tests": "T1(c) hipbelt-off 225 lb hang with a dial on the yoke tip"})
    c9r = res.get("C9")
    if c9r:
        b = c9r.get("best")
        V.append({"id": "C-9", "item": "printed body mass pass", "saved_g": b["saved_g"] if b else 0.0,
                  "min_sf": min(b["margins"]["min"].values()) if b else None,
                  "governing": "fatigue C_im3 static carry" if b else "no passing candidate",
                  "verdict": "PASS" if b and b["saved_g"] > 1.0 else "FAIL",
                  "tests": "T5 cycle test (fatigue governs at about 1.0)"})
    return V


# ============================================================================================== figures
C_BASE, C_NEW, INK, INK2, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#fcfcfb"


def shrink(path: Path, limit: int = 1_500_000):
    if path.stat().st_size <= limit:
        return
    from PIL import Image
    im = Image.open(path)
    im = im.convert("P", palette=Image.ADAPTIVE, colors=128)
    im.save(path, optimize=True)


def figures(res: dict) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    paths = []
    # 1: governing SF/req per item, today vs package C
    rows = margin_rows(res)
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(rows) + 1.8), dpi=130, facecolor=SURF)
    ax.set_facecolor(SURF)
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        if r["base"] is not None:
            ax.barh(yi + 0.18, min(r["base"], 3.0), 0.34, color=C_BASE, edgecolor=SURF, linewidth=2)
            ax.text(min(r["base"], 3.0) + 0.03, yi + 0.18, f"{r['base']:.2f}", va="center", fontsize=8, color=INK2)
        ax.barh(yi - 0.18, min(r["new"], 3.0), 0.34, color=C_NEW, edgecolor=SURF, linewidth=2)
        ax.text(min(r["new"], 3.0) + 0.03, yi - 0.18, f"{r['new']:.2f}  {r['verdict']}", va="center", fontsize=8,
                color=INK, fontweight="bold")
    ax.axvline(1.0, color=INK, lw=1.2, ls="--")
    ax.text(1.0, len(rows) - 0.35, " required 1.0", fontsize=8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r['id']}  {r['label']}\n{r['check']}" for r in rows], fontsize=8, color=INK)
    ax.set_xlim(0, 3.3)
    ax.set_xlabel("SF / requirement (governing check; bars capped at 3.0)", fontsize=9, color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#e6e5e0", lw=0.6)
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=C_BASE, label="today (as released / recorded)"),
                       Patch(color=C_NEW, label="package C item")], loc="lower right", fontsize=8, frameon=False)
    ax.set_title("Weight package C: structural gates, HA-LS-1 rev C (worst case per item)", fontsize=10,
                 color=INK, loc="left")
    fig.tight_layout()
    p = SCREENS / f"{DATE}_weightC_1.png"
    fig.savefig(p, facecolor=SURF)
    plt.close(fig)
    shrink(p)
    paths.append(p)
    # 2: details: C-1 routes, C-4 backer sweep, C-9 mass vs fatigue
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.6), dpi=120, facecolor=SURF)
    ax = axs[0]
    rt = res["C1"]["routes"]
    keys = list(rt)
    vals = [rt[k]["min_sf"] for k in keys]
    ax.barh(np.arange(len(keys))[::-1], vals, 0.6, color=C_NEW, edgecolor=SURF, linewidth=2)
    for i, (k, v) in enumerate(zip(keys, vals)):
        ax.text(v + 0.03, len(keys) - 1 - i, f"{v:.2f}", va="center", fontsize=8, color=INK)
    ax.set_yticks(np.arange(len(keys))[::-1])
    ax.set_yticklabels(keys, fontsize=8)
    ax.axvline(1.0, color=INK, lw=1, ls="--")
    ax.set_title("C-1 7075-T6 1.2 bow-tie: min SF/req by forming route", fontsize=9, loc="left")
    ax = axs[1]
    r4 = res["C4"]["rows"]
    hd = [(v["backer"]["t"], v) for k, v in r4.items() if v["backer"]["material"] == "hdpe_sheet"]
    hd.sort(key=lambda kv: kv[0])
    ts = [t for t, _ in hd]
    ax.plot(ts, [v["min_sf"] for _, v in hd], "-o", color=C_BASE, lw=2, ms=6, label="min SF/req (stress)")
    ax.plot(ts, [v["contact"]["walk_crept_w"] / DEPTH_PLAY for _, v in hd], "-s", color=C_NEW, lw=2, ms=6,
            label="channel sag / 4.5 mm play (walk, crept)")
    ax.axhline(1.0, color=INK, lw=1, ls="--")
    ax.set_yscale("log")
    ax.set_xlabel("HDPE backer thickness, mm", fontsize=8)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("C-4 pad backer over the 70 mm channel", fontsize=9, loc="left")
    ax = axs[2]
    c9r = res.get("C9")
    if c9r:
        cs = c9r["candidates"]
        ax.plot([c["saved_g"] for c in cs], [c["margins"]["min"]["fatigue"] for c in cs], "-o", color=C_NEW, lw=2,
                ms=6, label="fatigue (governs)")
        ax.plot([c["saved_g"] for c in cs], [c["margins"]["min"]["strength"] for c in cs], "-s", color=C_BASE, lw=2,
                ms=6, label="strength")
        for c in cs:
            ax.annotate(f"{c['delta_max_mm']:g} mm", (c["saved_g"], c["margins"]["min"]["fatigue"]),
                        textcoords="offset points", xytext=(4, -10), fontsize=7, color=INK2)
        ax.axhline(1.0, color=INK, lw=1, ls="--")
        ax.set_xlabel("printed body grams removed", fontsize=8)
        ax.legend(fontsize=7, frameon=False)
    ax.set_title("C-9 printed body: offset depth vs margin", fontsize=9, loc="left")
    for a in axs:
        a.set_facecolor(SURF)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.tick_params(labelsize=8)
    fig.tight_layout()
    p = SCREENS / f"{DATE}_weightC_2.png"
    fig.savefig(p, facecolor=SURF)
    plt.close(fig)
    shrink(p)
    paths.append(p)
    return paths


def margin_rows(res: dict) -> list[dict]:
    """Governing SF/req per item: today vs the package C proposal (figure 1 and the doc table)."""
    V = {v["id"]: v for v in res["verdicts"]}
    c1r = res["C1"]
    rows = [{"id": "C-1", "label": "belt plate 7075-T6 1.2 (cold roll)", "check": "walking fatigue, hub edge",
             "base": c1r["baseline_record"]["min_sf"], "new": c1r["routes"]["cold_roll"]["min_sf"],
             "verdict": V["C-1"]["verdict"]}]
    c2r = res["C2"]
    rows.append({"id": "C-2", "label": "hub D28 x 10", "check": "plate at hub rim / bore bearing",
                 "base": min(c2r["plate_D36"]["min_sf"], min(v["bore_sf"] for v in c2r["pivot_D36"].values())),
                 "new": V["C-2"]["min_sf"], "verdict": V["C-2"]["verdict"]})
    rows.append({"id": "C-3", "label": "spine holes for 5 g", "check": "net section + Kt, walking",
                 "base": res["C3"]["6061_1.5"]["rows"][0]["min_sf"], "new": V["C-3"]["min_sf"],
                 "verdict": V["C-3"]["verdict"]})
    r4 = res["C4"]["rows"]
    rows.append({"id": "C-4", "label": "pad backer HDPE 0.8", "check": "creep stress over the channel",
                 "base": r4["hdpe_sheet_1.0"]["min_sf"], "new": r4["hdpe_sheet_0.8"]["min_sf"],
                 "verdict": V["C-4"]["verdict"]})
    c7r = res["C7"]
    rows.append({"id": "C-7", "label": "yoke plate CFRP 1.2", "check": "first ply, pad push (C8) / fatigue",
                 "base": min(c7r["1.5"]["min_sf"], c7r["1.5"]["min_sf_fatigue"]), "new": V["C-7"]["min_sf"],
                 "verdict": V["C-7"]["verdict"]})
    if "C-9" in V and V["C-9"]["min_sf"] is not None:
        c0 = res["C9"]["candidates"][0]["margins"]["min"]
        rows.append({"id": "C-9", "label": f"printed body -{V['C-9']['saved_g']:.0f} g", "check": "fatigue (C_im3 carry)",
                     "base": min(c0.values()), "new": V["C-9"]["min_sf"], "verdict": V["C-9"]["verdict"]})
    return rows


if __name__ == "__main__":       # pragma: no cover
    import sys
    if "--c9" in sys.argv:
        c9()
    r = run()
    figures(r)
