"""BL-076: four items BL-074 left open on the PPA-CF H1-P frame (docs/DECISIONS.md 2026-11-25).

1. **Hip bearing plates (ring edge distance).** The BL-073 ring (6061-T6 47 / 24 x 2 mm, 8 x D5.5 on r 19) had a
   1.75 mm hole-to-OD ligament, under the laser-cut guide of 1.5-2 x t (SendCutSend 6061 page, read 2026-11-25). In
   the D49 spot face the outer ligament can never pass 2.75 mm, so t <= 2.75 / 1.5 = 1.83 mm: the .063 in (1.60 mm)
   stock gauge. The plate is checked as a Kirchhoff plate on a Winkler foundation (``huntkit.fea.plate_grid``,
   unilateral springs k0 = E_z' / boss depth, the nuts as rigid punches): bearing on the PPA, plate bending (S-basis
   yield), plate fatigue (Goodman), punching, hole bearing and tear-out. ``search()`` runs the options lightest first
   (one ring, two arc plates with several inner radii, two gauges) and every torque step, and picks the lightest
   that passes every row; ``bl073_hotwet`` takes the chosen geometry (RING_*) and torque (TORQUE_NM).
2. **Open items.** ``open_items()`` writes the 'Open items' section of bl070_h1p.md from the record (the US2 lug row's
   ``gated_by`` points to it).
3. **SHARE-GAUGE.** ``share_gauge()``: the US2 arm-root gauge on the H1-P mesh read with the pin load on the inner
   cheek only (share 0) and on the outer cheek only (share 1) (``h1_rev5.sub_fea(cheek=...)``). The reading is linear
   in the share but does NOT go through zero (u0 / u1 = r, about 0.43), so 'share = u / u1' over-reads; the share is
   (u - u0) / (u1 - u0).
4. **Spools.** ``spool_count()`` reads the BL-074 count from ``outputs/release/frame_h1p_ppa/spool_plan.csv``.

Units N, mm, MPa, g. Run: ``python -m huntkit.gendesign.bl076 [report | gauge]``.
"""
from __future__ import annotations

import csv
import functools
import json
import math
from pathlib import Path

import numpy as np

from . import bl070_h1p as P
from . import bl073_hotwet as B

REPO = P.REPO
OUT = REPO / "outputs" / "bl076"
SCREENS = P.SCREENS
SHOT = "20261125_bl076_"
SPOOL_CSV = REPO / "outputs" / "release" / "frame_h1p_ppa" / "spool_plan.csv"

# ------------------------------------------------------------------------------------------------ laser-cut limits
LASER = {
    "service": "SendCutSend laser cut 6061-T6",
    "url": "https://sendcutsend.com/materials/6061-aluminum",
    "read": "2026-11-25",
    "gauges_in": (0.040, 0.063, 0.080, 0.100, 0.125, 0.187, 0.250),     # the thin end of the 12 listed (.040-.750)
    "gauges_mm": (1.02, 1.60, 2.03, 2.54, 3.18, 4.75, 6.35),
    "tol_mm": 0.127,                                                      # +/- .005 in, every thickness
    "edge_factor": (1.5, 2.0),            # "keep holes and cutouts 1.5-2x material thickness away from edges"
    "hole_min_factor": 1.0,               # "design holes no smaller than material thickness"
    "min_part_in": (0.25, 0.375),         # smallest part for the instant quote
}
SPOT_CLEAR = 0.30          # radial clearance of the plates to the D49 spot face wall (keeper: 0.25 found in BL-075)
NUT_RIGID_R = 4.0          # DIN 934 M5 nut as a rigid punch: radius = s / 2 = 4.0 (ASSUMPTION NUT-RIGID)
DW = 6.9                   # nut bearing face dw min (ISO 4032 / DIN 934): the load ring 5.5 - 6.9 (the smallest)
FE_H = 0.20                # plate grid for the checks (mesh study in the record: 0.25 .. 0.10)
FE_H_SEARCH = 0.25
SE_6061 = None             # read from the record (fatigue_limit_mpa, R.R. Moore 5e8, fully reversed)
GOALS = {"strength": 1.5, "fatigue": 1.15, "creep": 1.5}
CLOSE_MARGIN = 1.3         # ASSUMPTION CLOSE-1.3: low-end preload after long-term creep >= 1.3 x the walk bolt tension


def _al() -> dict:
    from huntkit.materials import load
    a = load("alu_6061_t6")
    q = lambda k: float(a.require(k))          # noqa: E731
    return {"E": q("youngs_modulus_mpa"), "nu": q("poisson"), "fy": q("yield_strength_sbasis_mpa"),
            "fu": q("ultimate_strength_sbasis_mpa"), "se": q("fatigue_limit_mpa"), "rho": q("density_kg_m3") * 1e-6}


@functools.lru_cache(maxsize=None)
def bolt_xy() -> tuple:
    """The 8 hole centres in the ring frame (x = frame x, y = frame z - 120), two groups of 4 (h1_closeout)."""
    from . import h1_closeout as C
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    return tuple((float(x - C.HIP_C[0]), float(z - C.HIP_C[1])) for x, z in pat["positions_xz"])


R_BOLT = 19.0


# ------------------------------------------------------------------------------------------------ geometry
def _sector(r_i: float, r_o: float, a0: float, a1: float, n: int = 241):
    from shapely.geometry import Polygon
    a = np.radians(np.linspace(a0, a1, n))
    pts = list(zip(r_o * np.cos(a), r_o * np.sin(a))) + list(zip(r_i * np.cos(a[::-1]), r_i * np.sin(a[::-1])))
    return Polygon(pts)


def group_spans() -> list[tuple[float, float]]:
    """(first, last) hole angle of each group of 4, degrees, counter-clockwise."""
    out = []
    xy = bolt_xy()
    for grp in (xy[:4], xy[4:]):
        a = np.unwrap([math.atan2(y, x) for x, y in grp])
        mid = math.degrees(a.mean())
        d = np.degrees(a) - mid
        out.append((mid + d.min(), mid + d.max()))
    return out


def outline(d: dict):
    """Plate outline (shapely, ring frame) of a design {layout 'ring' | 'arcs', r_o, r_i, end_lig, fillet}."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    if d["layout"] == "ring":
        g = Point(0, 0).buffer(d["r_o"], 256).difference(Point(0, 0).buffer(d["r_i"], 256))
    else:
        de = math.degrees(math.asin((B.HOLE_D / 2 + d["end_lig"]) / R_BOLT))
        g = unary_union([_sector(d["r_i"], d["r_o"], a0 - de, a1 + de) for a0, a1 in group_spans()])
        f = d.get("fillet", 1.5)
        g = g.buffer(-f, 64).buffer(f, 64)
    for x, y in bolt_xy():
        g = g.difference(Point(x, y).buffer(B.HOLE_D / 2, 64))
    return g


def ligaments(d: dict) -> dict:
    out = {"outer_mm": round(d["r_o"] - R_BOLT - B.HOLE_D / 2, 3), "inner_mm": round(R_BOLT - B.HOLE_D / 2 - d["r_i"], 3)}
    if d["layout"] == "arcs":
        out["end_mm"] = d["end_lig"]
    out["between_holes_mm"] = round(min(math.dist(a, b) for i, a in enumerate(bolt_xy()) for b in bolt_xy()[:i])
                                    - B.HOLE_D, 3)
    out["min_mm"] = min(out.values())
    return out


def laser_rules(d: dict) -> dict:
    lg = ligaments(d)
    t = d["t"]
    stock = any(abs(t - g) < 0.005 for g in LASER["gauges_mm"])
    fits = d["r_o"] <= B.SPOT_D / 2 - SPOT_CLEAR + 1e-9
    return {"stock_gauge": stock, "fits_spot_face": fits, "edge_min_over_t": round(lg["min_mm"] / t, 3),
            "edge_ok_1p5t": lg["min_mm"] >= LASER["edge_factor"][0] * t - 1e-9,
            "edge_ok_2t": lg["min_mm"] >= LASER["edge_factor"][1] * t - 1e-9,
            "edge_min_at_tol_mm": round(lg["min_mm"] - LASER["tol_mm"], 3),
            "hole_ok": B.HOLE_D >= LASER["hole_min_factor"] * t,
            "ok": stock and fits and lg["min_mm"] >= LASER["edge_factor"][0] * t - 1e-9 and B.HOLE_D >= t}


def mass_g(d: dict) -> float:
    return round(outline(d).area * d["t"] * _al()["rho"], 2)


# ------------------------------------------------------------------------------------------------ plate on a foundation
def foundations() -> dict:
    """Winkler k0 = E_z' / boss depth (BL-073 BEARING-RING): cold (stiffest, the most peaked bearing), hot/wet short
    term and hot/wet long term (x CREEP_LONG: the softest, the most plate bending)."""
    r = P.ppa_record()
    return {"cold": r["E_z"] * 1.25 / B.BOSS_DEPTH, "hw": r["E_z"] * r["E_hot_hw"] / B.BOSS_DEPTH,
            "hw_long": r["E_z"] * r["E_hot_hw"] * B.CREEP_LONG / B.BOSS_DEPTH}


def _model(geom, t: float, k0: float, h: float, rigid: bool = True, unilateral: bool = True):
    from shapely import vectorized
    from huntkit.fea.plate_grid import GridPlate, Spring, iso_D
    al = _al()
    x0, y0, x1, y1 = geom.bounds
    nx, ny = int(math.ceil((x1 - x0) / h)) + 1, int(math.ceil((y1 - y0) / h)) + 1
    pl = GridPlate(x0 - h / 2, y0 - h / 2, nx, ny, h, iso_D(al["E"], t, al["nu"]))
    xy = pl.elem_xy()
    act = vectorized.contains(geom, xy[..., 0], xy[..., 1])
    pl.active = act
    rig = np.zeros_like(act)
    for x, y in bolt_xy():
        rig |= np.hypot(xy[..., 0] - x, xy[..., 1] - y) <= NUT_RIGID_R
    rig &= act
    if rigid:
        pl.D = pl.D.copy()
        pl.D[rig] *= 1.0e3
    trib = np.zeros(pl.nn)
    np.add.at(trib, pl.enodes[act].ravel(), h * h / 4.0)
    nodes = np.nonzero(trib)[0]
    for n in nodes:
        pl.springs.append(Spring(int(n), k0 * trib[n], unilateral=unilateral))
    return pl, act, rig, trib, nodes


def _loadvec(pl, F) -> np.ndarray:
    q = np.zeros((pl.nx, pl.ny))
    for (x, y), f in zip(bolt_xy(), F):
        if f:
            q += pl.patch_pressure(x, y, DW, f, sub=4)
    return pl.load_vector(q_elem=q)


def _vm(M: np.ndarray, t: float) -> np.ndarray:
    Mx, My, Mxy = M[..., 0], M[..., 1], M[..., 2]
    return (6.0 / t ** 2 * np.sqrt(np.maximum(Mx ** 2 + My ** 2 - Mx * My + 3 * Mxy ** 2, 0.0))).max(axis=-1)


def plate_solve(d: dict, F, k0: float, h: float = FE_H, rigid: bool = True, unilateral: bool = True) -> dict:
    """One solve: per-bolt loads F (8,), foundation k0. Returns peak bearing pressure on the PPA, peak von Mises in
    the plate outside the rigid nut punches, reaction check, contact fraction, and the fields."""
    geom = outline(d)
    pl, act, rig, trib, nodes = _model(geom, d["t"], k0, h, rigid, unilateral)
    r = pl.solve(_loadvec(pl, F))
    p = r["spring_force"] / trib[nodes]
    M = pl.moments(r["u"])
    if rigid:
        M[rig] = 0.0
    vm = _vm(M, d["t"])
    i = np.unravel_index(int(np.argmax(vm)), vm.shape)
    j = int(np.argmax(p))
    return {"p_max": float(p.max()), "sig_max": float(vm.max()), "reaction_n": float(r["spring_force"].sum()),
            "load_n": float(np.sum(F)), "contact": float(np.mean(r["active"])), "iters": r["iters"],
            "sig_at": [round(float(v), 2) for v in pl.elem_xy()[i]],
            "p_at": [round(float(v), 2) for v in pl.node_xy()[nodes[j]]],
            "_p": p, "_vm": vm, "_xy": pl.node_xy()[nodes], "_exy": pl.elem_xy(), "_act": act, "_M": M}


@functools.lru_cache(maxsize=None)
def _unit(key: tuple, h: float) -> dict:
    """Linear (bilateral) unit responses of a design: all 8 bolts at 1 N and one end bolt at 1 N, for every
    foundation. Superposed for the load cases; the combined field is checked for contact (p >= 0) everywhere."""
    d = dict(key)
    out = {}
    end = [0.0] * 8
    end[0] = 1.0
    for fn, k0 in foundations().items():
        a = plate_solve(d, [1.0] * 8, k0, h, unilateral=False)
        e = plate_solve(d, end, k0, h, unilateral=False)
        out[fn] = {"p_all": a["_p"], "p_end": e["_p"], "M_all": a["_M"], "M_end": e["_M"]}
    return out


def _key(d: dict) -> tuple:
    return tuple(sorted((k, v) for k, v in d.items() if k in ("layout", "r_o", "r_i", "end_lig", "fillet", "t")))


def preload(torque: float) -> dict:
    d = 5.0
    return {k: torque / (kk * d * 1e-3) for k, kk in (("nom", B.K_NOM), ("max", B.K_LO), ("min", B.K_HI))}


@functools.lru_cache(maxsize=None)
def bolt_rows() -> dict:
    """Per-bolt tension T and lateral force per row (BL-055 tipping model, h1_closeout.hip_check)."""
    from . import h1_closeout as C
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    rows = C.hip_check(pat, True)["rows"]
    n = pat["n"]
    return {k: {"T": float(v["T_max_n"]), "kind": v["kind"], "goal": v["goal"],
                "V_bolt": float(math.hypot(v.get("V_n", 0.0), v.get("H_n", 0.0)) / n)} for k, v in rows.items()}


def checks(d: dict, torque: float, h: float = FE_H) -> dict:
    """Every row of the plate at one torque (linear superposition of the unit responses)."""
    al = _al()
    m = P.materials()[B.MAT]
    allow = m["knock"] * m["s_z"]
    U = _unit(_key(d), h)
    F = preload(torque)
    rows = bolt_rows()
    t = d["t"]

    def field(fn, f_all, f_end, kind):
        u = U[fn]
        return f_all * u[f"{kind}_all"] + f_end * u[f"{kind}_end"]

    # bearing on the PPA (cold foundation: the most peaked), as BL-073 rows
    pc = U["cold"]["p_all"].max()                      # MPa per N per bolt, all bolts loaded alike
    bear = {}
    for k, v in rows.items():
        T, kind = v["T"], v["kind"]
        if kind == "strength":
            p_ = pc * (F["max"] + T)
            sf = allow / p_
        elif kind == "fatigue":
            p_ = pc * T
            sf = m["fat"] * allow / p_
        else:
            p_ = pc * max(F["max"], T)
            sf = m["rup"] * allow / p_
        bear[k] = {"T_n": round(T, 1), "kind": kind, "pressure_mpa": round(p_, 2), "sf": round(sf, 2), "goal": v["goal"]}
    # plate bending (every foundation; all bolts at F + T, and F on all + T on the end bolt only)
    c2 = max(v["T"] for v in rows.values() if v["kind"] == "strength")
    walk = max(v["T"] for v in rows.values() if v["kind"] == "fatigue")
    sig, pmin = {}, np.inf
    for fn in U:
        s1 = _vm(field(fn, F["max"] + c2, 0.0, "M"), t).max()
        s2 = _vm(field(fn, F["max"], c2, "M"), t).max()
        sig[fn] = round(float(max(s1, s2)), 1)
        pmin = min(pmin, float(field(fn, F["max"], c2, "p").min()), float(field(fn, F["max"] + c2, 0.0, "p").min()))
    s_str = max(sig.values())
    # plate fatigue: walk on top of the high preload (Goodman, R.R. Moore Se, S-basis Fu), both walk patterns
    fat = []
    for fn in U:
        for fa, fe in ((walk, 0.0), (0.0, walk)):
            smax = _vm(field(fn, F["max"] + fa, fe, "M"), t).max()
            smin = _vm(field(fn, F["max"], 0.0, "M"), t).max()
            sa = abs(_vm(field(fn, fa, fe, "M"), t)).max() / 2.0
            sm = max(smax, smin) - sa
            fat.append(1.0 / (sa / al["se"] + sm / al["fu"]))
    # punching (nut through the plate), hole bearing and tear-out of the outer ligament by the bolt's lateral force
    v_lat = max(v["V_bolt"] for v in rows.values() if v["kind"] == "strength")
    lg = ligaments(d)
    tau_y = al["fy"] / math.sqrt(3.0)
    punch = (F["max"] + c2) / (math.pi * DW * t)
    tear = v_lat / (2.0 * t * min(lg["outer_mm"], lg.get("end_mm", 99.0), lg["inner_mm"]))
    hole_b = v_lat / (5.0 * t)
    a_dw = math.pi / 4 * (DW ** 2 - B.HOLE_D ** 2)
    out = {"torque_nm": torque, "preload_n": {k: round(v, 0) for k, v in F.items()},
           "p_per_n_cold": float(pc), "bearing": bear,
           "bearing_min": {kd: min(q["sf"] for q in bear.values() if q["kind"] == kd) for kd in GOALS},
           "bending_mpa": sig, "bending_sf": round(al["fy"] / s_str, 2),
           "plate_fatigue_sf": round(float(min(fat)), 2),
           "punch_sf": round(tau_y / punch, 2), "tearout_sf": round(tau_y / tear, 2),
           "hole_bearing_sf": round(al["fy"] / hole_b, 2),
           "nut_face_sf": round(al["fy"] / ((F["max"] + c2) / a_dw), 2),
           "lateral_per_bolt_n": round(v_lat, 1), "c2_t_n": c2, "walk_t_n": walk,
           "min_contact_pressure_mpa": round(pmin, 3),
           "residual_preload_min_n": round(F["min"] * relax_fraction(d), 0),
           "closed_at_walk": bool(F["min"] * relax_fraction(d) >= CLOSE_MARGIN * walk)}
    out["pass"] = bool(all(out["bearing_min"][k] >= g for k, g in GOALS.items()) and out["bending_sf"] >= GOALS["strength"]
                       and out["plate_fatigue_sf"] >= GOALS["fatigue"] and out["punch_sf"] >= GOALS["strength"]
                       and out["tearout_sf"] >= GOALS["strength"] and out["hole_bearing_sf"] >= GOALS["strength"]
                       and out["nut_face_sf"] >= GOALS["strength"] and out["closed_at_walk"] and pmin >= 0.0)
    return out


def relax_fraction(d: dict) -> float:
    """Preload kept after long-term creep of the boss (BL-073 series springs; the plate area barely changes it)."""
    from . import frame_h1 as H1
    r = P.ppa_record()
    grip = B.FLANGE_T + B.BOSS_DEPTH + d["t"]
    kb = H1.TI["E"] * H1.TI["As"] / (grip + 0.8 * 5.0)
    a_m = outline(d).area / 8.0
    km0 = r["E_z"] * r["E_hot_hw"] * a_m / B.BOSS_DEPTH
    kmt = km0 * B.CREEP_LONG
    return (1 / kb + 1 / km0) / (1 / kb + 1 / kmt)


# ------------------------------------------------------------------------------------------------ the options
TORQUES = (0.60, 0.55, 0.50, 0.45, 0.40, 0.35)      # the Wera 7440 sets 0.3-1.2 N m; 0.30 leaves no closure margin


def options() -> list[dict]:
    """Lightest-first candidates that fit the D49 spot face (no frame change)."""
    r_o = B.SPOT_D / 2 - SPOT_CLEAR
    out = [{"name": "BL-073 ring 47/24 x 2.03 (as ordered)", "layout": "ring", "r_o": 23.5, "r_i": 12.0, "t": 2.03}]
    for t in (1.02, 1.60):
        out.append({"name": f"one ring {2 * r_o:g}/24 x {t:g}", "layout": "ring", "r_o": r_o, "r_i": 12.0, "t": t})
        for r_i in (12.0, 12.5, 13.0, 13.4, 13.8):
            el = LASER["edge_factor"][0] * t
            out.append({"name": f"two arc plates r {r_i:g}-{r_o:g} x {t:g}", "layout": "arcs", "r_o": r_o, "r_i": r_i,
                        "end_lig": round(el, 2), "fillet": 1.5, "t": t})
    return out


def search(h: float = FE_H_SEARCH) -> list[dict]:
    """Every option: mass, laser rules, and the highest torque step at which every row passes (None: none passes)."""
    res = []
    for d in options():
        lr = laser_rules(d)
        best = None
        for tq in TORQUES:
            c = checks(d, tq, h)
            if c["pass"]:
                best = c
                break
        res.append({"design": d, "g": mass_g(d), "laser": lr, "torque_nm": best["torque_nm"] if best else None,
                    "check": best or checks(d, min(TORQUES), h), "ok": bool(lr["ok"] and best is not None)})
    return res


def choose(res: list[dict] | None = None) -> dict:
    """Lightest option that passes on the search grid AND on the check grid (FE_H) at its torque."""
    res = res or search()
    for r in sorted((r for r in res if r["ok"]), key=lambda r: (r["g"], -r["torque_nm"])):
        if checks(r["design"], r["torque_nm"], FE_H)["pass"] and study_ok(r["design"], r["torque_nm"]):
            return r
    raise RuntimeError("no hip plate option passes")


def design() -> dict:
    """The design bl073_hotwet carries (RING_* constants)."""
    d = {"layout": B.RING_LAYOUT, "r_o": B.RING_OD / 2, "r_i": B.RING_ID / 2, "t": B.RING_T}
    if B.RING_LAYOUT == "arcs":
        d.update(end_lig=B.RING_END_LIG, fillet=B.RING_FILLET)
    return d


STUDY_H = (0.25, 0.2, 0.15, 0.12)


@functools.lru_cache(maxsize=None)
def _study(key: tuple, torque: float) -> tuple:
    return tuple(mesh_study(dict(key), torque, STUDY_H))


def study_ok(d: dict, torque: float) -> bool:
    """The bending and creep rows hold on every grid of the mesh study (the rigid-punch edge peak moves with h)."""
    m = P.materials()[B.MAT]
    allow = m["knock"] * m["s_z"]
    ms = _study(_key(d), torque)
    return bool(min(_al()["fy"] / q["sig_max_hwlong"] for q in ms) >= GOALS["strength"]
                and min(m["rup"] * allow / q["p_max_cold_fmax"] for q in ms) >= GOALS["creep"])


def ring_fe_for_hip_plate() -> dict:
    """What bl073_hotwet.hip_plate needs: the FE bearing pressure per N per bolt (cold) and the plate checks at the
    design torque."""
    c = checks(design(), B.TORQUE_NM)
    return {"p_per_n": c["p_per_n_cold"], "checks": c, "design": design(), "mass_g": mass_g(design()),
            "laser": laser_rules(design()), "ligaments": ligaments(design())}


def mesh_study(d: dict, torque: float, hs=(0.25, 0.2, 0.15, 0.12)) -> list[dict]:
    """Non-linear (unilateral) solves at the governing loads: peak bearing (cold, F_max) and peak plate stress
    (softest foundation, F_max + T_C2 on all bolts) against the grid."""
    F = preload(torque)
    c2 = max(v["T"] for v in bolt_rows().values() if v["kind"] == "strength")
    fd = foundations()
    out = []
    for h in hs:
        a = plate_solve(d, [F["max"]] * 8, fd["cold"], h)
        b = plate_solve(d, [F["max"] + c2] * 8, fd["hw_long"], h)
        out.append({"h": h, "p_max_cold_fmax": round(a["p_max"], 2), "sig_max_hwlong": round(b["sig_max"], 1),
                    "sig_at": b["sig_at"], "reaction_err": round(a["reaction_n"] / a["load_n"] - 1, 4),
                    "contact": round(b["contact"], 3)})
    return out


# ------------------------------------------------------------------------------------------------ SHARE-GAUGE (item 3)
def share_gauge(force: bool = False) -> dict:
    """US2 arm-root gauge (h1_rev5.gauge_site) on the exported H1-P mesh, loading B direction: sigma_xx per N with
    the pin load on both cheeks (as BL-056), on the inner cheek only (share 0) and on the outer cheek only (share 1).
    Cached in outputs/bl076/share_gauge.json (3 voxel solves, ~75 s)."""
    p = OUT / "share_gauge.json"
    if p.exists() and not force:
        return json.loads(p.read_text())
    import trimesh
    from . import h1_rev5 as R
    m = trimesh.load(P.STL_DIR / "h1_assembled.stl", force="mesh")
    site = R.gauge_site("us2", m)
    kit = json.loads((REPO / "designs/pack_5200/analysis/clevis_bl056.json").read_text())["kit"]["B"]
    u = np.asarray(kit["pull_unit_vector_frame_R"], float)
    st = R.station("us2")
    g = st["geom"]
    out = {"site": site, "unit": u.tolist(), "box": R.BOXES["us2"], "mesh": str((P.STL_DIR / "h1_assembled.stl").relative_to(REPO)),
           "cheek_x": {"inner": st["x"] - (g.throat / 2 + g.cheek / 2), "outer": st["x"] + (g.throat / 2 + g.cheek / 2)},
           "read": {}}
    for ch in (None, "inner", "outer"):
        f = R.sub_fea("us2", {"unit": (1000.0 * u).tolist()}, box=R.BOXES["us2"], mesh=m, field="unit", cheek=ch)
        fd = f["loads"]["_field"]
        cen, S = fd["cen"], fd["S"]
        dd = np.linalg.norm(cen - np.array([site["x"], site["y"] - 0.5, site["z"]]), axis=1)
        near = dd <= R.GAUGE_TOL + 0.5
        j = int(np.argmin(dd))
        out["read"][str(ch or "both")] = {"mpa_per_n": float(S[j, 0] / 1000.0), "near_mpa_per_n": (S[near, 0] / 1000.0).tolist()}
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    return out


def share_line(g: dict, share_max: float) -> dict:
    """Gauge algebra. Reading u(s) = (1 - s) u0 + s u1 (linear: one elastic body, the share only moves the load
    between two points on the same pin axis). r = u0 / u1. Share = (u - u0) / (u1 - u0); the BL-074 rule
    'share = u / u1' reads s + (1 - s) r. Without a share-0 reading the pass line is u / u1 <= r + s_max (1 - r)
    with r the smallest in the placement band (the conservative end)."""
    rd = g["read"]
    r = rd["inner"]["mpa_per_n"] / rd["outer"]["mpa_per_n"]
    ri = np.asarray(rd["inner"]["near_mpa_per_n"]) / np.asarray(rd["outer"]["near_mpa_per_n"])
    lin = (rd["inner"]["mpa_per_n"] + rd["outer"]["mpa_per_n"]) / 2.0 / rd["both"]["mpa_per_n"]
    xs = g["site"]["x"]
    lev = (g["cheek_x"]["inner"] - xs) / (g["cheek_x"]["outer"] - xs)
    r_lo = float(ri.min())
    return {"r_point": round(r, 3), "r_band": [round(float(ri.min()), 3), round(float(ri.max()), 3)],
            "r_beam": round(lev, 3), "superposition_check": round(lin, 4),
            "linear": True, "proportional": False,
            "bl074_rule_reads_at_s_max": round(share_max + (1 - share_max) * r, 3),
            "bl074_rule_reads_at_design_0p6": round(0.6 + 0.4 * r, 3),
            "share_max": share_max,
            "pass_line_with_u0": f"(u - u0) / (u1 - u0) <= {share_max:g}",
            "pass_ratio_no_u0": math.floor((r_lo + share_max * (1 - r_lo)) * 100) / 100.0,
            "u0_over_u1_expected": [round(float(ri.min()), 2), round(float(ri.max()), 2)],
            "share_per_ratio": round(1 / (1 - r), 2)}


# ------------------------------------------------------------------------------------------------ spools (item 4)
def spool_count(path: Path = SPOOL_CSV) -> dict:
    """BL-074 spool count from the build output: every row is a spool; the spools used by nothing but the frame's
    upper half drop out when the first-article upper half becomes the frame's upper half."""
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    up = [r for r in rows if all(u.strip().startswith("frame upper half") for u in r["uses"].split(";"))]
    return {"spools": len(rows), "spools_fa_as_frame": len(rows) - len(up), "upper_only": [int(r["spool"]) for r in up],
            "source": str(path.relative_to(REPO))}


# ------------------------------------------------------------------------------------------------ open items (item 2)
def open_items(rec: dict) -> list[dict]:
    """Every open item on H1-P, from the record: rows below their goal (gated_by), the BL-076 items, and the
    assumptions BL-076 adds, each with what closes it."""
    h = rec["h1p"]
    x = rec.get("bl076", {})
    out = []
    for r in h["rows"]:
        if not r.get("pass") and r.get("gated_by"):
            out.append({"id": f"ROW: {r['name']}", "state": f"{r['value']:g} vs goal {r['goal']:g}",
                        "why": r["gated_by"], "closes": _closer(r["name"], rec)})
    if x:
        sg = x.get("share_gauge", {})
        out.append({"id": "SHARE-GAUGE", "state": "corrected (BL-076)", "why": (
            f"the arm-root gauge reads {sg.get('r_point', 0):.2f} of the share-1 reading at share 0 (it is not "
            "proportional to the share)"), "closes": (
            f"CLEVIS-SHARE-B-PPA with the share-0 reading u0: share = (u - u0) / (u1 - u0) <= {sg.get('share_max', 0):g}; "
            f"u0 / u1 should read {sg.get('u0_over_u1_expected', ['?', '?'])[0]}-{sg.get('u0_over_u1_expected', ['?', '?'])[1]} "
            "(else the gauge is off its site)")})
        out.append({"id": "HIP-PLATES", "state": "laser-cut order", "why": (
            f"two 6061-T6 arc plates {x['plates']['t_mm']:g} mm replace the ring; torque {x['torque_nm']:g} N m"),
            "closes": "SendCutSend instant quote with hip_bearing_ring.dxf passes its checks; HB-6b on the first frame "
                      "(paint marks, re-torque check after T5)"})
        sp = x.get("spools", {})
        out.append({"id": "SPOOLS", "state": f"{sp.get('spools', '?')} booked", "why": (
            f"{sp.get('spools_fa_as_frame', '?')} if the first-article upper half becomes the frame's upper half"),
            "closes": "orchestrator / owner call (DECISIONS 2026-11-25), then the FA flatness and dimension checks"})
        for a in x.get("assumptions", []):
            out.append({"id": f"ASSUMPTION {a['id']}", "state": "open", "why": a["text"], "closes": a["settled_by"]})
    return out


def _closer(name: str, rec: dict) -> str:
    if name.startswith("US2 lug fatigue"):
        lug = rec["bl073"]["lug"]["fatigue"]
        return (f"US2-LUG-PPA: the conditioned lug piece at 40 C on loading B x {math.ceil(round(1.15 / lug * 100, 6)) / 100:g} "
                f"(= goal 1.15 / {lug:g}), proof + 1e5 cycles, no crack, feeler < 0.05 mm; and CA-1-HW (SBS fatigue "
                "run-outs at 40 C): the row then stands on the test, not the scatter goal")
    if name.startswith("US2 clevis joint fatigue"):
        return "CLEVIS-SHARE-B-PPA: measured outer-cheek share <= the BL-074 line (else metal clevis hole sleeves)"
    return "see the row's gated_by"


ASSUMPTIONS = [
    ("NUT-RIGID", "The DIN 934 M5 nut is a rigid punch of radius s / 2 = 4.0 mm on the plate; the load enters on "
     "the dw ring 5.5-6.9 mm. A softer nut or a smaller contact lowers the plate peak.", "HB-6b paint marks on the first "
     "frame; no plate dishing visible after T5 (straight edge across the plate)"),
    ("WINKLER-PLATE", "The boss under the plates is a Winkler foundation k0 = E_z' / 22 mm (cold x 1.25, hot/wet, hot/wet "
     "long term x 0.5), springs act in compression only; the plates as Kirchhoff plates (ACM grid, plate_grid). "
     "Peak plate stress at the rigid-punch edge grows slowly with the grid (mesh study in the record); the check "
     "uses the h 0.20 mm peak and the study's largest value.", "HB-6b hip-mount proof with the plates"),
    ("TORQUE-045", "Hip nut torque 0.45 N m (was 0.6): the plate model reads the bearing peak 1.33 x the BL-073 "
     "Hetenyi value, so the high-end preload (K 0.14) must come down for the creep row; at the low end (K 0.26) and "
     "after long-term creep the joint still stays closed at the walk bolt tension.", "HB-6b re-torque check after T5"),
    ("CLOSE-1.3", "The hip joint counts as closed when the low-end preload (K 0.26) after long-term creep is >= 1.3 x "
     "the walk bolt tension; this sets the lowest torque step (0.35 N m reads 1.2).", "HB-6b re-torque check after T5"),
    ("SHARE-LIN", "The US2 arm-root reading is linear in the outer-cheek share (one elastic body, load moved along the "
     "pin axis); it is not proportional: u(0) / u(1) = r from the H1-P voxel model.", "CLEVIS-SHARE-B-PPA reading u0"),
]


# ------------------------------------------------------------------------------------------------ record + md
def update_record(log=print) -> dict:
    """Add the 'bl076' key and refresh the hip values the build reads (keys kept, values updated; the BL-073 values
    are kept under bl076.before)."""
    rec = json.loads(P.REC_JSON.read_text())
    x73 = rec["bl073"]
    before = {"hip_plate": x73["hip_plate"], "hip_parts": x73["hip_parts"],
              "rows": {r["name"]: r["value"] for r in rec["h1p"]["rows"] if r["name"].startswith("hip mount")},
              "ring": rec["h1p"]["hip_mount"]["ring"], "torque_nm": rec["h1p"]["hip_mount"]["torque_nm"]}
    if "bl076" in rec and "before" in rec["bl076"]:
        before = rec["bl076"]["before"]
    res = search()
    ch = choose(res)
    d = design()
    if _key(ch["design"]) != _key(d) or abs(ch["torque_nm"] - B.TORQUE_NM) > 1e-9:
        raise RuntimeError(f"bl073_hotwet RING_* / TORQUE_NM {d} {B.TORQUE_NM} are not the lightest passing option {ch}")
    old = options()[0]
    c_old = checks(old, before["torque_nm"])
    hip = B.hip_plate()
    parts = B.hip_parts()
    ms = list(_study(_key(d), B.TORQUE_NM))
    sig_study = max(q["sig_max_hwlong"] for q in ms)
    g = share_gauge()
    share_max = math.floor(round(x73["clevis"]["share_1"]["fatigue"] / B.GOAL["US2 clevis fatigue (share 1.0)"] * 100, 6)) / 100
    sl = share_line(g, share_max)
    sp = spool_count()
    al = _al()
    # hip rows (HA-LS-1) and the BL-073 margins: the live design values
    hm_rows = {"hip mount strength (through_bolt)": hip["min_sf"]["strength"],
               "hip mount fatigue (through_bolt)": hip["min_sf"]["fatigue"],
               "hip mount creep (through_bolt)": hip["min_sf"]["creep"]}
    for r in rec["h1p"]["rows"]:
        if r["name"] in hm_rows:
            r["value"] = hm_rows[r["name"]]
            r["pass"] = bool(r["value"] >= r["goal"])
            r["basis"] = r.get("basis", "") if "BL-076" in r.get("basis", "") else (r.get("basis", "") + "; BL-076 plates").lstrip("; ")
        if r["name"].startswith("US2 lug fatigue") and r.get("gated_by"):
            r["gated_by"] = r["gated_by"].replace("see OPEN", "see OPEN (bl070_h1p.md 'Open items')") \
                if "Open items" not in r["gated_by"] else r["gated_by"]
    rec["h1p"]["rows_by_name"] = {r["name"]: r for r in rec["h1p"]["rows"]}
    Ma = x73["margins_bl073_hw"]
    Ma["hip mount strength"], Ma["hip mount fatigue"], Ma["hip mount creep"] = (hip["min_sf"]["strength"],
                                                                                 hip["min_sf"]["fatigue"], hip["min_sf"]["creep"])
    gov = list(x73["tornado"][0]["rows"])
    x73["tornado"] = B.tornado({k: Ma[k] for k in gov}, x73["tornado_shares"],
                               joint_e={"z 234 joint fatigue": Ma["z 234 joint fatigue"] * x73["joint_e050_ratio"]})
    x73["hip_plate"] = hip
    x73["hip_parts"] = parts
    hw_delta = hip["hardware_g"]["screws_extra_g"] + parts["hip_bearing_ring"]["g"] + parts["hip_nut_keeper"]["g"]
    x73["mass"]["hip_hardware_delta_vs_bl070_g"] = round(hw_delta, 1)
    x73["mass"]["frame_delta_vs_bl070_g"] = round(x73["mass"]["body_delta_vs_bl070_g"] + hw_delta, 1)
    hmj = rec["h1p"]["hip_mount"]
    hmj.update({"bearing_ring_mm2": hip["ring_area_mm2"],
                "bearing_n": round(hip["allow_mpa"] / (hip["pressure_mpa_per_kn"] / 1e3), 1),
                "nut_seat_depth_mm": B.BOSS_DEPTH + B.RING_T,
                "rows": hip["rows"], "min_sf": hip["min_sf"], "pass": hip["pass"], "hardware": hip["hardware"],
                "torque_nm": hip["torque_nm"], "preload_n": hip["preload_n"], "screw": hip["screw"],
                "relaxation": hip["relaxation"], "cold": hip["cold"], "webs": hip["webs"]})
    hmj["ring"].update({"od_mm": B.RING_OD, "id_mm": B.RING_ID, "t_mm": B.RING_T, "g": hip["hardware_g"]["ring_g"],
                        "layout": B.RING_LAYOUT, "pieces": 2 if B.RING_LAYOUT == "arcs" else 1,
                        "stock": f"6061-T6 .063 in ({B.RING_T:g} mm) sheet",
                        "holes": "8 x D5.5 on r 19 (HIP_CHOSEN), 4 per plate",
                        "outline": f"two arc plates r {B.RING_ID / 2:g}-{B.RING_OD / 2:g}, ends {B.RING_END_LIG:g} mm "
                                   f"past the end holes, R{B.RING_FILLET:g} corners"})
    rec["bl071_requests"]["hip_torque_nm"] = hip["torque_nm"]
    rec["bl071_requests"]["hip_preload_n"] = hip["preload_n"]
    rec["bl071_requests"]["hip_screw"] = hip["screw"]
    x = {"ticket": "BL-076", "date": "2026-11-25", "before": before,
         "laser": {k: (list(v) if isinstance(v, tuple) else v) for k, v in LASER.items()},
         "options": [{"name": r["design"]["name"], "design": {k: v for k, v in r["design"].items() if k != "name"},
                      "g": r["g"], "laser_ok": r["laser"]["ok"], "edge_min_over_t": r["laser"]["edge_min_over_t"],
                      "torque_nm": r["torque_nm"], "ok": r["ok"],
                      "study_ok": bool(study_ok(r["design"], r["torque_nm"])) if r["ok"] else None,
                      "rows": {k: r["check"][k] for k in ("bearing_min", "bending_sf", "plate_fatigue_sf", "punch_sf",
                                                          "tearout_sf", "hole_bearing_sf", "closed_at_walk")},
                      "rows_at_torque": r["check"]["torque_nm"]} for r in res],
         "bl073_ring_on_plate_model": {"torque_nm": before["torque_nm"], "bearing_min": c_old["bearing_min"],
                                       "bending_sf": c_old["bending_sf"], "edge_min_over_t": laser_rules(old)["edge_min_over_t"]},
         "chosen": ch["design"]["name"], "torque_nm": B.TORQUE_NM,
         "plates": {"layout": B.RING_LAYOUT, "t_mm": B.RING_T, "t_in": 0.063, "r_o_mm": B.RING_OD / 2,
                    "r_i_mm": B.RING_ID / 2, "end_lig_mm": B.RING_END_LIG, "fillet_mm": B.RING_FILLET,
                    "area_mm2": round(outline(d).area, 1), "g_pair": mass_g(d), "ligaments": ligaments(d),
                    "laser": laser_rules(d)},
         "checks": hip["ring_checks"], "mesh_study": ms,
         "bending_sf_study_max": round(al["fy"] / sig_study, 2),
         "hetenyi_mpa_per_kn": hip["hetenyi"]["mpa_per_n"] * 1e3,
         "mass": {"ring_bl073_g": before["hip_parts"]["hip_bearing_ring"]["g"],
                  "plates_g": parts["hip_bearing_ring"]["g"],
                  "delta_g": round(parts["hip_bearing_ring"]["g"] - before["hip_parts"]["hip_bearing_ring"]["g"], 2),
                  "screws_delta_g": round(hip["hardware_g"]["screws_extra_g"] - before["hip_plate"]["hardware_g"]["screws_extra_g"], 2)},
         "share_gauge": {**sl, "read": {k: v["mpa_per_n"] for k, v in g["read"].items()}, "site": g["site"],
                         "cheek_x": g["cheek_x"], "mesh": g["mesh"]},
         "spools": sp,
         "assumptions": [{"id": a, "text": t, "settled_by": s} for a, t, s in ASSUMPTIONS]}
    rec["bl076"] = x
    P.REC_JSON.write_text(json.dumps(rec, default=_jd, indent=1))
    if log:
        log(f"bl076: {ch['design']['name']} at {B.TORQUE_NM} N m, {x['mass']['plates_g']} g (ring {x['mass']['ring_bl073_g']} g)")
    return rec


def _jd(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def md_section(rec: dict) -> list[str]:
    x = rec["bl076"]
    pl, ck, sg, sp = x["plates"], x["checks"], x["share_gauge"], x["spools"]
    bf = x["before"]
    L = ["## BL-076: hip bearing plates (edge distance), open items, SHARE-GAUGE, spool count", "",
         "Code `huntkit/gendesign/bl076.py`, tests `tests/test_bl076.py`. Date 2026-11-25. Record: `bl076` in the JSON; "
         "the hip values the build reads (`h1p.hip_mount`, `bl073.hip_plate`, `bl073.hip_parts`) now carry the plates; "
         "the BL-073 values are kept under `bl076.before`.", "",
         "### 1. Hip bearing plates (was the 47 / 24 x 2 ring)", "",
         f"Laser-cut limits ({x['laser']['service']}, {x['laser']['url']}, read {x['laser']['read']}): 6061-T6 in "
         f"{', '.join(f'{g:.3f}' for g in x['laser']['gauges_in'])} in (and up to .750); +/- .005 in "
         f"({x['laser']['tol_mm']} mm); holes no smaller than t; holes and cut-outs 1.5-2 x t from an edge; smallest "
         f"part .25 x .375 in. In the D49 spot face the outer ligament is at most {B.SPOT_D / 2 - R_BOLT - B.HOLE_D / 2:g} mm, "
         f"so t <= {(B.SPOT_D / 2 - R_BOLT - B.HOLE_D / 2) / 1.5:.2f} mm: the .063 in (1.60 mm) gauge is the "
         "only stock that can meet the guide without a frame change.", "",
         "The plate is checked as a Kirchhoff plate on a Winkler foundation (`huntkit.fea.plate_grid`, unilateral "
         "springs, the nuts as rigid punches), which replaces the BL-073 1D Hetenyi read. On the same model the BL-073 "
         f"ring at {x['bl073_ring_on_plate_model']['torque_nm']:g} N m reads bearing creep "
         f"{x['bl073_ring_on_plate_model']['bearing_min']['creep']:.2f}, bending {x['bl073_ring_on_plate_model']['bending_sf']:.2f} "
         "(its long free spans between the bolt groups bend as the boss creeps), so the ring was not only an edge-"
         "distance problem.", "",
         "| option | g | min edge / t | laser guide | torque that passes (h 0.25) | bearing creep | bending | verdict |",
         "|---|---:|---:|---|---:|---:|---:|---|"]
    for o in sorted(x["options"], key=lambda q: q["g"]):
        L.append(f"| {o['name']} | {o['g']:.2f} | {o['edge_min_over_t']:.2f} | {'ok' if o['laser_ok'] else 'FAILS'} | "
                 f"{o['torque_nm'] if o['torque_nm'] else 'none'} | {o['rows']['bearing_min']['creep']:.2f} | "
                 f"{o['rows']['bending_sf']:.2f} | {'**chosen**' if o['name'] == x['chosen'] else (('passes' if o.get('study_ok') else 'fails the mesh study') if o['ok'] else 'no')} |")
    L += ["", "(Rows read on the h 0.25 mm search grid at the torque in column 5, or at 0.35 N m where none passes; an "
          "option is taken only if it also passes on every grid of the mesh study, h 0.25-0.12.) Not taken: individual washers or "
          "plates per bolt pair (each nut then carries its own short plate: the end-plate effect of the arcs at every "
          "nut, more bearing peak, more parts); enlarging the spot face (frame re-export and R1 / hip re-check for a "
          "part that now fits).", "",
          f"**Chosen: {x['chosen']}** (`h1p/hip_bearing_ring.dxf`, two plates on one sheet; `h1p/hip_bearing_ring.stl`): "
          f"6061-T6 .063 in ({pl['t_mm']:g} mm), each plate an annular arc r {pl['r_i_mm']:g}-{pl['r_o_mm']:g} mm "
          f"({2 * pl['r_i_mm']:g} / {2 * pl['r_o_mm']:g} mm), ends {pl['end_lig_mm']:g} mm past the end holes, R{pl['fillet_mm']:g} "
          f"corners, 4 x D5.5 on r 19. Ligaments: outer {pl['ligaments']['outer_mm']:g} ({pl['ligaments']['outer_mm'] / pl['t_mm']:.2f} t), "
          f"inner {pl['ligaments']['inner_mm']:g} ({pl['ligaments']['inner_mm'] / pl['t_mm']:.2f} t), end {pl['ligaments']['end_mm']:g} "
          f"({pl['ligaments']['end_mm'] / pl['t_mm']:.2f} t): the 1.5 x t end of the guide (at the -.005 in tolerance the outer "
          f"ligament is {pl['laser']['edge_min_at_tol_mm']:g} mm). Radial clearance to the D49 spot face {SPOT_CLEAR} mm. "
          f"**{x['mass']['plates_g']:g} g for the pair vs {x['mass']['ring_bl073_g']:g} g ({x['mass']['delta_g']:+g} g, "
          f"{x['mass']['delta_g'] / 28.3495:+.2f} oz)**; the screws stay M5 x 35 (stack {B.FLANGE_T + B.BOSS_DEPTH + B.RING_T + B.NUT_M:g} mm, "
          f"{rec['h1p']['hip_mount']['screw']['protrusion_mm']:g} mm proud).", "",
          f"**Torque {x['torque_nm']:g} N m ({x['torque_nm'] / 0.112985:.1f} in lbf)**, was {bf['torque_nm']:g}: the highest 0.05 step "
          f"at which every row passes (preload {ck['preload_n']['min']:.0f}-{ck['preload_n']['max']:.0f} N at K 0.26-0.14); "
          f"the joint stays closed at the walk bolt tension after long-term creep. Still inside the Wera 7440 range (0.3-1.2 N m).", "",
          "| row | load per bolt | SF | goal |", "|---|---|---:|---:|"]
    gl = GOALS
    for kd in ("strength", "fatigue", "creep"):
        L.append(f"| bearing on the PPA, {kd} (plate FE, cold foundation) | BL-073 rows | {ck['bearing_min'][kd]:.2f} | {gl[kd]:g} |")
    L += [f"| plate bending, S-basis yield {_al()['fy']:g} MPa (worst foundation, all bolts F_max + T_C2 or one end bolt + T_C2) | "
          f"{ck['preload_n']['max']:.0f} + {ck['c2_t_n']:.0f} N | {ck['bending_sf']:.2f} (mesh-study max: {x['bending_sf_study_max']:.2f}) | 1.5 |",
          f"| plate fatigue, Goodman (Se {_al()['se']:g}, Fu {_al()['fu']:g} MPa), walk on the high preload | +{ck['walk_t_n']:.0f} N | {ck['plate_fatigue_sf']:.2f} | 1.15 |",
          f"| punching (nut through the plate, dw {DW}) | {ck['preload_n']['max'] + ck['c2_t_n']:.0f} N | {ck['punch_sf']:.2f} | 1.5 |",
          f"| tear-out of the smallest ligament by the bolt's lateral force (all of it into the plate) | {ck['lateral_per_bolt_n']:.0f} N | {ck['tearout_sf']:.2f} | 1.5 |",
          f"| hole bearing (M5 on the plate) | {ck['lateral_per_bolt_n']:.0f} N | {ck['hole_bearing_sf']:.2f} | 1.5 |",
          f"| nut face on the plate | {ck['preload_n']['max'] + ck['c2_t_n']:.0f} N | {ck['nut_face_sf']:.2f} | 1.5 |", "",
          "Hip rows in the JSON (HA-LS-1 table below, `h1p.rows`): " + ", ".join(
              f"{k.replace(' (through_bolt)', '')} {bf['rows'][k]:g} -> **{rec['h1p']['rows_by_name'][k]['value']:g}**"
              for k in bf["rows"]) + " (goals 1.5 / 1.15 / 1.5): all hold.", "",
          "Mesh study (non-linear contact, chosen plates at the design torque):", "",
          "| grid h mm | bearing peak, cold, F_max (MPa) | plate peak, hot/wet long term, F_max + T_C2 (MPa) | at (x, y) | reaction error |",
          "|---:|---:|---:|---|---:|"]
    for q in x["mesh_study"]:
        L.append(f"| {q['h']} | {q['p_max_cold_fmax']} | {q['sig_max_hwlong']} | {q['sig_at']} | {q['reaction_err']:+.4f} |")
    L += ["", "The plate peak sits at the rigid-punch edge between the two middle nuts and creeps up with the grid "
          "(a rigid-inclusion edge); the check takes the largest value of the study.", "",
          "### 3. SHARE-GAUGE", "",
          f"The US2 gauge (arm root, bag face, x {sg['site']['x']:g}) was read on the exported H1-P mesh with loading B's pin "
          f"load on the inner cheek only and on the outer cheek only (`h1_rev5.sub_fea(cheek=...)`): "
          f"{sg['read']['inner'] * 1e3:.2f} and {sg['read']['outer'] * 1e3:.2f} MPa per kN; both cheeks "
          f"{sg['read']['both'] * 1e3:.2f} (the mean of the two to {abs(sg['superposition_check'] - 1) * 100:.1f} %). The reading is "
          f"**linear** in the share but **not proportional**: at share 0 it reads r = {sg['r_point']:.2f} of the share-1 reading "
          f"(placement band {sg['r_band'][0]:.2f}-{sg['r_band'][1]:.2f}; a beam read on the lever arms gives {sg['r_beam']:.2f}). "
          f"The BL-074 rule share = u / u1 reads s + (1 - s) r: the design share 0.6 would read {sg['bl074_rule_reads_at_design_0p6']:.2f} and "
          f"the line {sg['share_max']:g} would read {sg['bl074_rule_reads_at_s_max']:.2f}, so it over-reads (safe, but it fails a "
          "sound clevis).", "",
          f"**Corrected:** add reading 0 (shim on the INNER cheek, share 0) = u0; share = (u - u0) / (u1 - u0); pass "
          f"<= **{sg['share_max']:g}** (unchanged in share terms). u0 / u1 must read {sg['u0_over_u1_expected'][0]:g}-"
          f"{sg['u0_over_u1_expected'][1]:g}, else the gauge is off its site. Without u0 the pass line in gauge terms is "
          f"**u / u1 <= {sg['pass_ratio_no_u0']:g}** (r at the low end of the band). One unit of u / u1 is "
          f"{sg['share_per_ratio']:g} units of share, so gauge scatter counts {sg['share_per_ratio']:g} x.", "",
          "### 4. Spools", "",
          f"From `{sp['source']}` (BL-074 build output): **{sp['spools']} spools**; **{sp['spools_fa_as_frame']}** if the "
          f"first-article upper half becomes the frame's upper half (spools {', '.join(map(str, sp['upper_only']))} then drop "
          "out; orchestrator call, DECISIONS 2026-11-25). The BL-073 printability line below now reads this file.", ""]
    L += ["### 2. Open items", "", "The 'Open items' section below (generated by `open_items()`) is what the US2 lug "
          "row's 'see OPEN' points to; the row's `gated_by` now names it.", ""]
    L += ["### ASSUMPTIONS (BL-076)", ""] + [f"- ASSUMPTION {a['id']}: {a['text']} Settled by: {a['settled_by']}." for a in x["assumptions"]]
    L += ["", "### Screenshots", ""] + [f"- `{q}`" for q in x.get("screenshots", [])] + [""]
    return L


def open_md(rec: dict) -> list[str]:
    L = ["## Open items", "",
         "Generated by `huntkit/gendesign/bl076.py open_items()` from the record: every H1-P row below its goal (its "
         "`gated_by` points here as 'see OPEN'), the BL-076 items and their assumptions, with what closes each.", "",
         "| item | state | why | closed by |", "|---|---|---|---|"]
    for o in open_items(rec):
        L.append(f"| {o['id']} | {o['state']} | {o['why']} | {o['closes']} |")
    return L + [""]


def write_md(rec: dict | None = None) -> str:
    rec = rec or json.loads(P.REC_JSON.read_text())
    P.write_md(rec)
    B.write_md_section(rec)
    md = P.REC_MD.read_text()
    head, _, rest = md.partition("\n## ")
    P.REC_MD.write_text(head.rstrip() + "\n\n" + "\n".join(md_section(rec) + open_md(rec)) + "\n## " + rest)
    return str(P.REC_MD)


# ------------------------------------------------------------------------------------------------ screenshot
def plot_plates(rec: dict, path: Path) -> str:
    """The new plates against the BL-073 ring in the D49 spot face, with the plate stress field."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, PathPatch
    from matplotlib.path import Path as MPath
    x = rec["bl076"]
    d_new, d_old = design(), options()[0]

    def patch(g, **kw):
        polys = list(getattr(g, "geoms", [g]))
        verts, codes = [], []
        for pg in polys:
            for ring in [pg.exterior] + list(pg.interiors):
                c = np.asarray(ring.coords)
                verts += c.tolist()
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        return PathPatch(MPath(verts, codes), **kw)

    fig, ax = plt.subplots(1, 2, figsize=(11, 5.6), dpi=110)
    for a, d, lab in ((ax[0], d_old, f"BL-073 ring 47/24 x 2.03, {x['mass']['ring_bl073_g']:g} g\nouter ligament 1.75 mm = 0.86 t (guide 1.5-2 t)"),
                      (ax[1], d_new, f"BL-076: 2 arc plates .063 in (1.6 mm), {x['mass']['plates_g']:g} g\n"
                                     f"ligaments {x['plates']['ligaments']['outer_mm']:g} / {x['plates']['ligaments']['inner_mm']:g} / "
                                     f"{x['plates']['ligaments']['end_mm']:g} mm >= 1.5 t")):
        a.add_patch(Circle((0, 0), B.SPOT_D / 2, fc="#efe6d6", ec="#6b5b3e", lw=1.5, label="D49 spot face (PPA boss)"))
        a.add_patch(patch(outline(d), fc="#9aa3ad", ec="k", lw=0.8, label="6061 plate"))
        for (bx, by) in bolt_xy():
            a.add_patch(Circle((bx, by), NUT_RIGID_R, fc="none", ec="#1f5fa8", lw=0.8, ls="--"))
        a.set_xlim(-27, 27)
        a.set_ylim(-27, 27)
        a.set_aspect("equal")
        a.set_title(lab, fontsize=9.5)
        a.set_xlabel("frame x (mm)")
    ax[0].set_ylabel("frame z - 120 (mm), seen from the bag side")
    # stress field on the new plates (hot/wet long term, F_max + T_C2)
    ck = x["checks"]
    F = ck["preload_n"]["max"] + ck["c2_t_n"]
    s = plate_solve(d_new, [F] * 8, foundations()["hw_long"], 0.2)
    vm = np.where(s["_act"], s["_vm"], np.nan)
    exy = s["_exy"]
    im = ax[1].pcolormesh(exy[..., 0], exy[..., 1], vm, cmap="viridis", shading="nearest", vmin=0, vmax=_al()["fy"] / 1.5)
    ax[1].add_patch(patch(outline(d_new), fc="none", ec="k", lw=0.9))
    for (bx, by) in bolt_xy():
        ax[1].add_patch(Circle((bx, by), NUT_RIGID_R, fc="#d9a441", ec="#7a5a10", lw=0.6, alpha=0.85))
    ax[1].text(0, -25.5, "gold: A2 nuts (rigid punch); colour: plate stress, F_max + T_C2, hot/wet boss",
               ha="center", fontsize=7.5)
    cb = fig.colorbar(im, ax=ax[1], fraction=0.046, pad=0.03)
    cb.set_label("plate von Mises, MPa (scale top = S-basis yield / 1.5)", fontsize=8)
    ax[0].legend(loc="lower center", fontsize=7.5, framealpha=0.9)
    fig.suptitle(f"H1-P hip bearing: ring -> two arc plates, torque {x['before']['torque_nm']:g} -> {x['torque_nm']:g} N m. "
                 f"Bearing creep {x['bl073_ring_on_plate_model']['bearing_min']['creep']:.2f} -> {ck['bearing_min']['creep']:.2f}, "
                 f"bending {x['bl073_ring_on_plate_model']['bending_sf']:.2f} -> {ck['bending_sf']:.2f} (goals 1.5)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def report(log=print) -> dict:
    rec = update_record(log=log)
    SCREENS.mkdir(parents=True, exist_ok=True)
    shot = plot_plates(rec, SCREENS / f"{SHOT}1.png")
    rec["bl076"]["screenshots"] = [str(Path(shot).relative_to(REPO))]
    P.REC_JSON.write_text(json.dumps(rec, default=_jd, indent=1))
    write_md(rec)
    return rec


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    cmd = a[0] if a else "report"
    if cmd == "gauge":
        print(json.dumps(share_gauge(force=True)["read"].keys().__repr__()))
    elif cmd == "report":
        report()
    elif cmd == "search":
        for r in search():
            print(r["design"]["name"], r["g"], r["laser"]["ok"], r["torque_nm"], r["check"]["bearing_min"], r["check"]["bending_sf"])
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
