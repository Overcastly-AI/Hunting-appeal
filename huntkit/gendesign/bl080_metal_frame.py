"""BL-080: metal-stay frame concepts with printed joints (architecture study, first-order checks).

Why: the all-printed PAHT-CF frames are fatigue-limited in-plane on the honest hot/wet B-basis (BL-077 / BL-079);
PPA-CF H1-P is over the cost cap (docs/RUBRIC.md 1b). This module scores four metal-stay concepts on the rubric:
Strong (gate) -> cost cap -> mass vs H1c (1404.7 g) and H1 (1069.3 g) -> looks (judged on the concept sheet).

Method (first order, not a release check):
- The HA-LS-1 rev C beam model of the pack frame (``huntkit.fea.pack5200`` + ``load_standard.ls1_envelope``: 9
  crown-bar cases + 5 IM3-couple cases, torsos 15 / 19 / 23 in) is reused unchanged. Each concept is the same
  topology with its own stay / bar / lumbar sections and materials, set after ``build`` (the shared code is not
  edited; ``pack5200.hardware_mass`` assumes composite sections, so it is bypassed for the call and mass is booked
  here from geometry). The crown (OD 16 carbon legs, top bar, spine, rack / pawl, bushings) carries over from
  ``frame.yaml`` and is not re-checked here.
- Metal strength: member von Mises vs the MMPDS S-basis yield of the record (``materials_bridge.yield_of``),
  margin = SF / case factor. Buckling: frame eigenvalue / (1.5 x case factor) (HA-LS-1 "other rules").
- Metal fatigue (HA-LS-1: 1e5 cycles at 0 -> 1.6 g x 68 kg, Basquin, Kt): sigma(1.6 g) from the static-carry runs
  (both couple variants); allowable max stress at R 0 from Basquin through 0.9 Su at 1e3 and the record fatigue
  limit at 5e8 (``fatigue.basquin``), Goodman on the notched mean: sigma_allow = 2 S(1e5) / (Kt (1 + S(1e5)/Su)).
  Kt 2 everywhere (clamp edges, fretting; the HA-LS-1 rule), Kt 3 where a through-hole is drilled (ASSUMPTION
  KT-HOLE, Peterson transverse hole in a tube in bending, rounded up).
- Printed PAHT-CF parts loaded in bending (concept A and C hubs) use the BL-077 honest hot/wet B-basis: XY 43.14 MPa
  static, fatigue 0.30 x that at 1e5 (record ``fatigue_1e5_ratio``), modulus x 0.587 (BL-077 ASSUMPTION E-WET).
- Joint forces (pan / hub to stay, bars to stay, crown bushings) are read from the solved model and factored by
  the case factor; bearing and slip are hand calcs on them.

Units N, mm, MPa, g, USD. Run: ``python -m huntkit.gendesign.bl080_metal_frame [run | plots]``.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FRAME_YAML = REPO / "designs" / "pack_5200" / "frame.yaml"
ITER2 = REPO / "designs" / "pack_5200" / "iter2"
REC_JSON = ITER2 / "frame_concepts.json"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261125_bl080_"

TORSOS = (15.0, 19.0, 23.0)
G_WALK = 1.6                     # HA-LS-1 fatigue: 0 -> 1.6 g x 68 kg, 1e5 cycles
N_FAT = 1e5
KT_CLAMP = 2.0                   # HA-LS-1 metal rule
KT_HOLE = 3.0                    # ASSUMPTION KT-HOLE
HOLE_ZONE_Z = 160.0              # through-holes in a stay only below the crown-leg travel (leg bottom z >= 171)

# ----------------------------------------------------------------------------- baselines (BL-077 record)
H1 = {"body_g": 1069.3, "hip_hw_g": 28.8, "usd": 138.52, "label": "H1 (retired, PAHT)"}
H1C = {"body_g": 1404.7, "hip_hw_g": 48.2, "usd": 164.59, "label": "H1c (PAHT reshape, A2)"}
CAP_USD = 150.0
PROVE_CAP_USD = 150.0

# ----------------------------------------------------------------------------- stock (cited, docs/research/20261125_metal_stay_frames.md)
IN = 25.4
STOCK = {
    "t750_035": {"desc": '3/4" OD x .035" 6061-T6 drawn tube', "od": 0.750 * IN, "t": 0.035 * IN,
                 "usd": 19.96, "len_in": 48, "src": "Speedy Metals pc-4563 (48 in USD 19.96)"},
    "t875_035": {"desc": '7/8" OD x .035" 6061-T6 drawn tube', "od": 0.875 * IN, "t": 0.035 * IN,
                 "usd": 34.39, "len_in": 72, "src": "Zoro Select 6 ft USD 34.39 (search listing)"},
    "t875_049": {"desc": '7/8" OD x .049" 6061-T6 drawn tube', "od": 0.875 * IN, "t": 0.049 * IN,
                 "usd": 30.00, "len_in": 48, "src": "Speedy Metals p-4568 (48 in USD 30.00)"},
    "t875_065": {"desc": '7/8" OD x .065" 6061-T6 drawn tube', "od": 0.875 * IN, "t": 0.065 * IN,
                 "usd": 38.88, "len_in": 48, "src": "Speedy Metals p-4569 (48 in USD 38.88)"},
    "t1000_049": {"desc": '1" OD x .049" 6061-T6 drawn tube', "od": 1.000 * IN, "t": 0.049 * IN,
                  "usd": 34.56, "len_in": 48, "src": "Speedy Metals p-4586 (48 in USD 34.56)"},
    "f7075_1x1_4": {"desc": '1" x 1/4" 7075-T6 flat bar', "w": 1.0 * IN, "t": 0.25 * IN,
                    "usd": 0.56 * 48, "len_in": 48,
                    "src": "ASSUMPTION FLAT-PRICE: Speedy 1/2 x 1 in 7075 base USD 1.11/in x area ratio 0.5 = USD 0.56/in"},
    "f7075_1x3_16": {"desc": '1" x 3/16" 7075-T6 flat bar', "w": 1.0 * IN, "t": 0.1875 * IN,
                     "usd": 0.42 * 48, "len_in": 48,
                     "src": "ASSUMPTION FLAT-PRICE: Speedy 1/2 x 1 in 7075 base USD 1.11/in x area ratio 0.375 = "
                            "USD 0.42/in (no cited 3/16 listing)"},
}
STAY_OPTIONS = ("t875_035", "t875_049", "t875_065", "t1000_049")
FLAT_OPTIONS = ("f7075_1x3_16", "f7075_1x1_4")
UBAR_OPTIONS = ("t750_035", "t875_049", "t875_065", "t1000_049")
CROSS_OPTIONS = ("t875_049", "t875_065", "t1000_049")
PAN_OPTIONS = ((0.063 * IN, 0.0), (0.063 * IN, 0.063 * IN), (0.063 * IN, 0.125 * IN), (0.125 * IN, 0.0))
# Fixed-length prices (USD) by length in inches, Speedy Metals product pages read 2026-11-25 (STOCK src); the 7/8 x .035
# tube is the Zoro 6 ft listing only. 7075 flat bar: ASSUMPTION FLAT-PRICE by the inch.
PRICE_LENGTHS = {
    "t750_035": {12: 8.32, 24: 12.47, 36: 16.63, 48: 19.96, 72: 24.95},
    "t875_035": {72: 34.39},
    "t875_049": {12: 12.50, 24: 18.75, 36: 25.00, 48: 30.00, 72: 37.50},
    "t875_065": {12: 16.20, 24: 24.30, 36: 32.40, 48: 38.88, 72: 48.60},
    "t1000_049": {12: 14.40, 24: 21.60, 36: 28.80, 48: 34.56, 72: 43.20},
}
KERF_MM = 15.0                   # per cut: kerf + squaring (ASSUMPTION)


def buy(key: str, pieces_mm: list[float]) -> tuple[float, str]:
    """Cheapest set of fixed lengths that yields the pieces (first-fit decreasing on at most 3 sticks)."""
    if key not in PRICE_LENGTHS:
        L = sum(pieces_mm) / IN + 2
        return STOCK[key]["usd"] * max(1.0, L / STOCK[key]["len_in"]), "ASSUMPTION by the inch"
    table = PRICE_LENGTHS[key]
    best = None
    lengths = sorted(table)
    import itertools
    for n in (1, 2, 3):
        for combo in itertools.combinations_with_replacement(lengths, n):
            sticks = [l * IN for l in combo]
            free = sorted(sticks, reverse=True)
            ok = True
            for pc in sorted(pieces_mm, reverse=True):
                for i, f in enumerate(free):
                    if f >= pc + KERF_MM:
                        free[i] -= pc + KERF_MM
                        break
                else:
                    ok = False
                    break
            if ok:
                usd = sum(table[l] for l in combo)
                if best is None or usd < best[0]:
                    best = (usd, " + ".join(f"{l} in" for l in combo))
    return best


RHO = {"alu_6061_t6": 2.70e-3, "alu_7075_t6": 2.81e-3, "paht": 1.06e-3, "steel": 7.93e-3}   # g/mm3 (records)
PAHT_USD_G = 0.08                # record cost_usd 80 / kg
SUPPORT_X = 1.10                 # BL-053 support estimate (bl077 cost table)
BOLT_USD = 0.84 + 0.10           # Zoro A2 M5 x 35 50-pk USD 41.79 + A2 nut (BL-077 cost lines)
M4_USD = 0.50                    # ASSUMPTION M4 A2 set (shop price)
SCS_ORDER_USD = 29.0             # SendCutSend order minimum (third-party reports, as booked in BL-077)

# PAHT honest hot/wet basis (data/materials/polymers/pa12_cf_fdm_paht.yaml, BL-077)
PAHT_XY_HW = 43.14
PAHT_FAT = 0.30
PAHT_E_HW = 3860.0 * 0.587
PAHT_BEARING_HW = 19.66          # Z hot/wet B-basis used as the conservative bearing allowable (ASSUMPTION BEAR-PAHT)


def _mat_dict(E, nu, allow, mid):
    return {"id": mid, "youngs_modulus_mpa": E, "shear_modulus_mpa": E / (2 * (1 + nu)), "poisson": nu,
            "design_allowable_mpa": allow, "density_kg_m3": 0.0}


PAHT_MAT = _mat_dict(PAHT_E_HW, 0.35, PAHT_XY_HW, "paht_cf_hotwet")
SOFT_MAT = _mat_dict(1000.0, 0.3, 1e9, "back_panel_soft")    # ASSUMPTION SOFT-PANEL: HDPE-like back sheet, not structure


def _bolt_g(d, L):
    """Socket-head screw + nut mass from geometry (steel 7.93 g/cm3; head 1.7 d x d)."""
    head = math.pi * (0.85 * d) ** 2 * d
    shank = math.pi * (d / 2) ** 2 * L
    nut = 0.8 * d * (math.sqrt(3) / 2 * (1.6 * d) ** 2 - math.pi * (d / 2) ** 2 * 0.8)
    return (head + shank * 0.92 + nut) * RHO["steel"]


# ----------------------------------------------------------------------------- concepts
CONCEPTS = {
    "A": {
        "name": "A  Flat-bar twin stays + printed hub",
        "short": "7075 flat-bar stays, PAHT hub + crown sleeves",
        "stay": "f7075_1x3_16", "stay_mat": "alu_7075_t6", "bar": "t750_035",
        "lumbar": {"kind": "paht", "t": 8.0, "flange": 15.0},
        "printed_sleeves": True,
        "story": "Classic internal-frame stays (Kifaru-style flat bar, hand-bent to the back) on a printed lower hub "
                 "that carries the Ti hip mount; the crown legs ride in printed sleeves clamped to the bars.",
    },
    "B": {
        "name": "B  Tube ladder (perimeter) + printed corners",
        "short": "6061 tube stays + lumbar cross tube, printed tees",
        "stay": None, "stay_mat": "alu_6061_t6", "bar": "t750_035",
        "lumbar": {"kind": "cross_tube", "tube": "t875_049"},
        "printed_sleeves": False,
        "story": "Straight 6061 tubes (two stays, a lumbar cross tube at z 120, mid and upper bars) joined by printed "
                 "tees that are through-bolted below the crown-leg travel and clamped above it; the Ti hip mount bolts "
                 "to two hand-cut 6061 angle brackets through-bolted to the cross tube. Every part is cut by hand from "
                 "stock with printed drill jigs: no laser order, no bending. A bent U (bending service) could replace "
                 "the two lower tees; not booked."
    },
    "C": {
        "name": "C  Hybrid: H1 printed lower hub + metal stays",
        "short": "H1 lower half re-cut for 6061 tubes, tube bars",
        "stay": None, "stay_mat": "alu_6061_t6", "bar": "t750_035",
        "lumbar": {"kind": "paht", "t": 10.0, "flange": 20.0},
        "printed_sleeves": False,
        "story": "Keeps the H1 lower half (hip boss, US1 lugs, hinge fairleads) re-cut with through-bores; 6061 tube "
                 "stays run foot to crown, the upper half is replaced by tube bars and printed tees.",
    },
    "D": {
        "name": "D  Tube stays + formed 6061 hip pan (own idea)",
        "short": "6061 tube stays, laser-cut + bent 6061 pan, printed parts in bearing only",
        "stay": None, "stay_mat": "alu_6061_t6", "bar": "t750_035",
        "lumbar": {"kind": "metal_pan", "mat": "alu_6061_t6", "t": 0.063 * IN, "flange": 20.0, "flange_kt": 2.0},
        "printed_sleeves": False,
        "story": "6061 tube stays (crown legs telescope inside, as the v2 frame), a laser-cut and press-brake-formed "
                 "6061 .063 in hat pan with a .125 in doubler under the mount (SendCutSend; no holes within 25 mm of "
                 "the bends) carries the Ti hip mount and bolts through the stays below the leg travel; tube bars "
                 "clamp on with metal-backed printed tees. Every printed part is in bearing or clamped.",
    },
}


# ----------------------------------------------------------------------------- sections
def stay_section(key):
    from huntkit.fea.sections import flat_bar, tube_round
    s = STOCK[key]
    return flat_bar(s["w"], s["t"]) if key.startswith("f") else tube_round(s["od"], s["t"])


def tube_sec(key):
    from huntkit.fea.sections import tube_round
    s = STOCK[key]
    return tube_round(s["od"], s["t"])


def section_area(key):
    s = STOCK[key]
    if key.startswith("f"):
        return s["w"] * s["t"]
    di = s["od"] - 2 * s["t"]
    return math.pi * (s["od"] ** 2 - di ** 2) / 4


# ----------------------------------------------------------------------------- model
def build_model(c: dict, torso: float) -> dict:
    """The pack5200 beam model with the concept's sections and materials (crown carries over from frame.yaml)."""
    import huntkit.fea.pack5200 as P5
    from huntkit.fea.frames import load_frame_params
    from huntkit.fea.sections import generic, tube_round

    p = load_frame_params(FRAME_YAML)
    lum = c["lumbar"]
    bar = tube_sec(c["bar"])
    p.update({"torso_in": float(torso), "stay_section": stay_section(c["stay"]), "bar_section": bar,
              "upper_bar_section": tube_sec(c.get("ubar", c["bar"])), "lumbar_plate_material": "alu_6061_t6",
              "lumbar_plate_t": float(lum.get("t", 2.0)), "lumbar_flange_mm": float(lum.get("flange", 0.0)),
              "lumbar_padup_t_mm": float(lum.get("padup", 0.0))})
    if c["stay"].startswith("f"):
        # the flat bar has no bore: the crown legs ride in printed sleeves on it (bushing links kept)
        p["stay_section"] = stay_section(c["stay"])
    saved = P5.hardware_mass
    P5.hardware_mass = lambda m: {}
    try:
        m = P5.build(p)
    finally:
        P5.hardware_mass = saved
    for mem in m["members"]:
        g = mem["group"]
        if mem["material"] is None and g.startswith("stay"):
            mem["material"] = c["stay_mat"]
        elif mem["material"] is None and g in ("mid_bar", "upper_bar"):
            mem["material"] = "alu_6061_t6"
    if lum["kind"] == "paht":
        _replace_plate(m, PAHT_MAT)
    elif lum["kind"] == "cross_tube":
        _replace_plate(m, SOFT_MAT)
        for mem in m["members"]:
            if mem["group"] in ("lumbar_plate", "lumbar_plate_shear"):
                mem["no_kg"] = True          # the soft panel is not structure: keep it out of the buckling solve
        ct = tube_sec(lum["tube"])
        for mem in m["members"]:
            if mem["group"] == "lumbar_plate" and mem["id"].startswith("plh2"):
                mem.update({"section": ct, "material": "alu_6061_t6", "group": "lumbar_cross_tube"})
            if mem["id"].startswith("pivot_doubler"):
                mem.update({"section": generic(1.0, 1.0, 1.0, 1.0), "material": SOFT_MAT, "no_kg": True})
            if mem["id"] == "pivot_boss":
                # 6061 hip bracket from the cross tube to the Ti mount (ASSUMPTION BRACKET: 40 x 6 mm channel equiv.)
                mem.update({"section": tube_round(20.0, 3.0), "material": "alu_6061_t6", "group": "hip_bracket"})
    return m


def _replace_plate(m, mat):
    """Swap the lumbar grillage material, keeping the shear-diagonal equivalence (A_d ~ G / E)."""
    from huntkit.fea.sections import generic
    old = None
    for mem in m["members"]:
        if mem["group"] == "lumbar_plate":
            old = old or mem["material"]
            mem["material"] = mat
    for mem in m["members"]:
        if mem["group"] == "lumbar_plate_shear":
            dm = mem["material"]
            ratio = (mat["shear_modulus_mpa"] / mat["youngs_modulus_mpa"]) / (dm["shear_modulus_mpa"] / dm["youngs_modulus_mpa"])
            sec = mem["section"]
            mem["section"] = generic(sec.A * ratio, 1.0, 1.0, 1.0)
            mem["material"] = {**dm, "youngs_modulus_mpa": mat["youngs_modulus_mpa"],
                               "shear_modulus_mpa": mat["shear_modulus_mpa"]}


# ----------------------------------------------------------------------------- fatigue
def metal_fatigue_allow(mat_id: str, kt: float) -> float:
    """Allowable max stress (R 0, 1e5 cycles) with Kt on the notched stress, Goodman on the mean (S-basis Su)."""
    from huntkit.fea.fatigue import basquin
    from huntkit.fea.materials_bridge import get_material
    mt = get_material(mat_id)
    su = float(mt.get("ultimate_strength_sbasis_mpa") or mt.require("ultimate_strength_mpa"))
    se = float(mt.require("fatigue_limit_mpa")) * su / float(mt.require("ultimate_strength_mpa"))
    s = float(basquin(su, se, Ne=5e8).stress_amplitude(N_FAT))
    return 2 * s / (kt * (1 + s / su))


def _zmid(res, mem_id):
    idx = {n: i for i, n in enumerate(res.node_ids)}
    for m in res.model["members"]:
        if m["id"] == mem_id:
            a, b = m["nodes"]
            return 0.5 * (res.coords[idx[a]][2] + res.coords[idx[b]][2])
    return np.nan


def _mid(mat):
    if mat is None:
        return None
    if isinstance(mat, str):
        return mat
    if isinstance(mat, dict):
        return mat.get("id")
    return getattr(mat, "id", None)


def _role(group: str) -> str | None:
    if group.startswith("stay"):
        return "stays"
    if group in ("mid_bar", "upper_bar"):
        return "bars"
    if group in ("lumbar_plate", "lumbar_cross_tube", "hip_bracket"):
        return "hub"
    return None


def _bushing_forces(res, m):
    """Factored-free bushing link forces |F_xy| per link (N) from the solved displacements."""
    U = res.displacements
    out = {}
    for ln in m["links"]:
        if ln["id"].startswith("bush"):
            a, b = ln["nodes"]
            d = np.asarray(U[b][:2]) - np.asarray(U[a][:2])
            k = np.asarray(ln["k"][:2], float)
            out[ln["id"]] = float(np.linalg.norm(k * d))
    return out


def _end_force_at(res, mem_id, node_id):
    """Force and moment (6,) exerted BY the member ON the node, global axes."""
    mi = next(i for i, m in enumerate(res.members) if m["id"] == mem_id)
    ni = res.node_ids.index(node_id)
    for e in res.members[mi]["elements"]:
        el = res.elements[e]
        R = el.T[:3, :3]
        if el.n1 == ni:
            f = res.elem_forces[e, 0]
            return np.r_[R.T @ f[:3], R.T @ f[3:]]
        if el.n2 == ni:
            f = -res.elem_forces[e, 1]
            return np.r_[R.T @ f[:3], R.T @ f[3:]]
    return np.zeros(6)


def _joint_forces(res, m):
    """Hub-to-stay resultant per side (force, and moment about the side's z 120 stay point, from every grillage
    member meeting the stay nodes) and the bar-end forces at the stays."""
    out = {}
    idx = {n: i for i, n in enumerate(res.node_ids)}
    for tag in ("L", "R"):
        F = np.zeros(3)
        M = np.zeros(3)
        c0 = res.coords[idx[f"S{tag}120"]]
        for mem in m["members"]:
            if mem["group"] in ("lumbar_plate", "lumbar_cross_tube", "lumbar_plate_shear"):
                for nd in mem["nodes"]:
                    if nd.startswith(f"S{tag}"):
                        f6 = _end_force_at(res, mem["id"], nd)
                        F += f6[:3]
                        M += f6[3:] + np.cross(res.coords[idx[nd]] - c0, f6[:3])
        out[f"hub_{tag}_force_n"] = float(np.linalg.norm(F))
        out[f"hub_{tag}_moment_nmm"] = float(np.linalg.norm(M))
        for g, z in (("mid_bar", 330.0), ("upper_bar", 520.0)):
            nd = f"S{tag}{z:g}"
            for mem in m["members"]:
                if mem["group"] == g and nd in mem["nodes"]:
                    f = _end_force_at(res, mem["id"], nd)
                    out[f"{g}_{tag}_axial_n"] = float(abs(f[0]))
                    out[f"{g}_{tag}_shear_n"] = float(np.hypot(f[1], f[2]))
    return out


def evaluate(c: dict, torsos=TORSOS) -> dict:
    """All HA-LS-1 rev C case sets at each torso: metal / hub strength, buckling, fatigue, joint and bushing forces."""
    from huntkit.fea.load_standard import ls1_envelope
    from huntkit.fea.materials_bridge import get_material, yield_of
    env = ls1_envelope()
    rows = {"strength": {}, "buckling": [], "fatigue": {}, "joints": {}, "bushing_n": 0.0, "crown_info": np.inf}
    fat_sig = {}
    for t in torsos:
        m = build_model(c, t)
        for var, cases in env.items():
            for case in cases:
                if case.name == "tall_load_posts":
                    continue
                r = case.run(m)
                req = float(r.meta["required_sf"])
                for mm in r.members:
                    role = _role(mm["group"])
                    if _mid(mm["material"]) == SOFT_MAT["id"]:
                        role = None
                    if role is None:
                        if mm["group"].startswith("crown"):
                            rows["crown_info"] = min(rows["crown_info"], mm["sf"] / req)
                        continue
                    key = role
                    marg = mm["sf"] / req
                    cur = rows["strength"].get(key)
                    if cur is None or marg < cur["margin"]:
                        rows["strength"][key] = {"margin": float(marg), "case": case.name, "variant": var,
                                                 "torso_in": t, "member": mm["id"], "sf": float(mm["sf"]),
                                                 "required": req}
                    if case.name == "static_carry":
                        sig = float(mm["von_mises"]) * G_WALK
                        k = (role, mm["id"])
                        if sig > fat_sig.get(k, (0, None))[0]:
                            fat_sig[k] = (sig, (var, t), mm["group"], _zmid(r, mm["id"]),
                                          _mid(mm["material"]))
                bf = r.buckling_sf
                if np.isfinite(bf):
                    rows["buckling"].append({"margin": float(bf / (1.5 * req)), "case": case.name, "variant": var,
                                             "torso_in": t, "eigen": float(bf)})
                jf = _joint_forces(r, m)
                for k, v in jf.items():
                    v = v * req
                    if v > rows["joints"].get(k, {"value": 0})["value"]:
                        rows["joints"][k] = {"value": float(v), "case": case.name, "torso_in": t, "factored": req}
                bf_ = _bushing_forces(r, m)
                rows["bushing_n"] = max(rows["bushing_n"], max(bf_.values()) * req if bf_ else 0.0)
    # fatigue margins per role
    for (role, mid), (sig, where, group, z, mat) in fat_sig.items():
        if role == "hub" and c["lumbar"]["kind"] == "paht":
            allow, basis = PAHT_FAT * PAHT_XY_HW, "PAHT hot/wet B 43.14 x 0.30"
        else:
            mat = mat or ("alu_6061_t6")
            if role == "stays":
                kt = KT_HOLE if (z <= HOLE_ZONE_Z and not c["stay"].startswith("f")) else KT_CLAMP
            elif role == "hub":
                kt = KT_HOLE                     # pan: bolt and lightening holes; cross tube: through-bolted tees
                if c["lumbar"].get("flange_kt") and mid.startswith(("plh0", "plh4")):
                    kt = c["lumbar"]["flange_kt"]  # DECISION D-FLANGE: no holes within 25 mm of the flange bends
            else:
                kt = KT_HOLE if role == "bars" else KT_CLAMP   # bars: through-bolted to the tees
            allow, basis = metal_fatigue_allow(mat, kt), f"{mat} Basquin 1e5 R0 Kt {kt:g}"
        marg = allow / sig if sig > 0 else np.inf
        cur = rows["fatigue"].get(role)
        if cur is None or marg < cur["margin"]:
            rows["fatigue"][role] = {"margin": float(marg), "sigma_max_mpa": float(sig), "allow_mpa": float(allow),
                                     "member": mid, "z_mm": float(z), "basis": basis, "variant": where[0],
                                     "torso_in": where[1]}
    rows["buckling"] = min(rows["buckling"], key=lambda d: d["margin"]) if rows["buckling"] else None
    rows["crown_info"] = float(rows["crown_info"])
    rows["checks"] = hand_checks(c, rows)
    rows["min_margin"] = min(v["margin"] for v in _all_rows(rows))
    rows["governing"] = min(_all_rows(rows), key=lambda v: v["margin"])["label"]
    return rows


# ----------------------------------------------------------------------------- hand checks on the model forces
def hand_checks(c: dict, rows: dict) -> list[dict]:
    """Joint bearing / slip / printed-sleeve rows (first order). Forces are already x case factor."""
    out = []
    j = rows["joints"]
    hub_f = max(j.get("hub_L_force_n", {"value": 0})["value"], j.get("hub_R_force_n", {"value": 0})["value"])
    hub_m = max(j.get("hub_L_moment_nmm", {"value": 0})["value"], j.get("hub_R_moment_nmm", {"value": 0})["value"])
    lum = c["lumbar"]
    if lum["kind"] in ("metal_pan", "cross_tube"):
        st = STOCK[c["stay"]]
        d, n, s = 5.0, 2, 70.0                     # 2 x M5 per side, 70 mm pitch (z 70 / 140)
        f_bolt = hub_f / n + hub_m / s             # direct + couple (couple taken by the pair)
        bear = f_bolt / (2 * d * st["t"])          # double bearing through both tube walls
        out.append({"label": "hub-to-stay bolt bearing in 6061 tube (2 x M5 / side)", "value_mpa": bear,
                    "allow_mpa": 386.0 * 0.9, "margin": 386.0 * 0.9 / bear,
                    "basis": "bearing yield 386 MPa at e/D 2 (AA typical, cited) x 0.9 for e/D 1.5 (ASSUMPTION BRG-ED)",
                    "force_n": f_bolt})
        tau = f_bolt / (2 * math.pi * (0.8 * d) ** 2 / 4)
        out.append({"label": "hub-to-stay bolt shear (A2-70, double shear)", "value_mpa": tau, "allow_mpa": 0.6 * 450,
                    "margin": 0.6 * 450 / tau, "basis": "A2-70 yield 450 MPa x 0.6 on the minor-diameter area"})
    if lum["kind"] == "paht":
        # stay-in-printed-bore bearing at the hub (the hub carries the stays in clamp/bearing)
        w = STOCK[c["stay"]].get("od") or STOCK[c["stay"]]["w"]
        bear = hub_f / (w * 120.0)
        out.append({"label": "stay bearing on the printed hub bore (120 mm land)", "value_mpa": bear,
                    "allow_mpa": PAHT_BEARING_HW, "margin": PAHT_BEARING_HW / bear,
                    "basis": "PAHT Z hot/wet B 19.66 MPa (ASSUMPTION BEAR-PAHT)"})
    # bar-end tees: through-bolt (B, C below z 160 none) or metal-backed clamp; slip check at mu 0.2
    for g in ("mid_bar", "upper_bar"):
        sh = max(j.get(f"{g}_L_shear_n", {"value": 0})["value"], j.get(f"{g}_R_shear_n", {"value": 0})["value"])
        ax = max(j.get(f"{g}_L_axial_n", {"value": 0})["value"], j.get(f"{g}_R_axial_n", {"value": 0})["value"])
        f = math.hypot(sh, ax)
        clamp_n = 2 * 2.6e3                      # 2 x M5 A2 at 0.45 x proof preload, ASSUMPTION CLAMP-PRELOAD
        cap = 0.2 * 2 * clamp_n                  # two friction faces (tee halves), mu 0.2 Al/Al wet, ASSUMPTION MU
        out.append({"label": f"{g} tee clamp slip on the stay (2 x M5 metal-backed)", "value_n": f, "allow_n": cap,
                    "margin": cap / f if f > 0 else np.inf,
                    "basis": "mu 0.2 x 2 faces x 2 x 2.6 kN (ASSUMPTIONS MU, CLAMP-PRELOAD; coupon CL-1)"})
    if c.get("printed_sleeves"):
        # crown-leg bushing load on a printed sleeve: ring bending 0.318 F R (point load), wall 3 mm, 40 mm long
        F = rows["bushing_n"]
        R, tw, L = 9.0 + 1.5, 3.0, 40.0
        sig = 6 * 0.318 * F * R / (L * tw ** 2)
        sig_f = sig / 1.5 * (G_WALK / 2.0)       # ASSUMPTION: walking bushing load = limit / 1.5 x 1.6/2.0
        out.append({"label": "printed crown sleeve ring bending (static)", "value_mpa": sig, "allow_mpa": PAHT_XY_HW,
                    "margin": PAHT_XY_HW / sig, "basis": "Roark point-load ring 0.318 F R, PAHT XY hot/wet"})
        out.append({"label": "printed crown sleeve ring bending (fatigue)", "value_mpa": sig_f,
                    "allow_mpa": PAHT_FAT * PAHT_XY_HW, "margin": PAHT_FAT * PAHT_XY_HW / sig_f,
                    "basis": "0.30 x 43.14 MPa"})
    return out


def _all_rows(rows):
    for k, v in rows["strength"].items():
        yield {"label": f"strength {k} ({v['case']}, {v['torso_in']:g} in)", "margin": v["margin"]}
    for k, v in rows["fatigue"].items():
        yield {"label": f"fatigue {k} ({v['basis']})", "margin": v["margin"]}
    if rows["buckling"]:
        b = rows["buckling"]
        yield {"label": f"buckling ({b['case']}, {b['torso_in']:g} in)", "margin": b["margin"]}
    for h in rows.get("checks", []):
        yield {"label": h["label"], "margin": h["margin"]}


# ----------------------------------------------------------------------------- mass and cost
# Printed interface parts (PAHT-CF), ASSUMPTION PRINT-MASS: volumes estimated from the H1 hard-point features they
# replace (fairleads, lugs, cheeks, pawl housing); +-30 % until modelled. US2 clevises reuse the BL-050 part (15.7 g).
PRINTED = {
    "A": {"lower hub (hip boss, struts, foot sockets, US1 lugs, hinge fairleads)": None,
          "crown sleeves on the bars x 2 (bore 18, 3 mm wall, z 330-530)": 2 * 38.0,
          "mid / upper bar nodes x 4 (IM2 / IM3 cheeks)": 4 * 22.0, "pawl housing + spine guide": 30.0,
          "lash clips z 250 / 420 x 4": 4 * 6.0, "US2 clevis x 2 (BL-050 part)": 2 * 15.7},
    "B": {"foot cups x 2 (hinge fairlead z 60, US1 lug, stabilizer anchor)": 2 * 45.0,
          "lumbar tees x 2 (cross tube to stay, IM1 z 190 fairlead)": 2 * 22.0,
          "mid-bar tees x 2 (IM2 / bag-mid fairlead)": 2 * 25.0,
          "upper tees + stay-top collars x 2 (IM3 cheeks, bushing seat)": 2 * 35.0,
          "pawl housing + spine guide": 30.0, "lash clips z 250 / 420 x 4": 4 * 6.0,
          "lumbar pad-seat spacers x 2": 2 * 10.0, "US2 clevis x 2 (BL-050 part)": 2 * 15.7},
    "C": {"H1 lower half re-cut with D22.4 through-bores (h1_lower_flat 494.6 g - 2 bores)": 494.6 - 2 * 30.0,
          "mid-bar tees x 2": 2 * 25.0, "upper tees + stay-top collars x 2": 2 * 35.0,
          "pawl housing + spine guide": 30.0, "lash clips z 250 / 420 x 4": 4 * 6.0,
          "US2 clevis x 2 (BL-050 part)": 2 * 15.7},
    "D": {"foot cups x 2 (hinge fairlead z 60, US1 lug, stabilizer anchor)": 2 * 45.0,
          "pan saddles x 2 (tube cradle, IM1 z 190 fairlead)": 2 * 18.0,
          "mid-bar tees x 2 (IM2 / bag-mid fairlead)": 2 * 25.0,
          "upper tees + stay-top collars x 2 (IM3 cheeks, bushing seat)": 2 * 35.0,
          "pawl housing + spine guide": 30.0, "lash clips z 250 / 420 x 4": 4 * 6.0,
          "US2 clevis x 2 (BL-050 part)": 2 * 15.7},
}
BOLTS = {   # (count, d, L) per concept: joints that carry load; the Ti hip-mount screws are booked as hip hardware
    "A": [(4, 5, 30), (8, 4, 20), (4, 4, 16)],
    "B": [(2, 5, 30), (4, 5, 30), (8, 4, 25), (2, 4, 20), (4, 4, 16)],
    "C": [(8, 4, 25), (2, 4, 20), (4, 4, 16), (2, 5, 30)],
    "D": [(2, 5, 30), (4, 5, 30), (8, 4, 25), (2, 4, 20), (4, 4, 16)],
}
FLAT_BACKER_G = 4 * 40.0 * 25.4 * 3.175 * RHO["alu_6061_t6"]     # 4 x 40 mm of 1 x 1/8 in 6061 flat, hand cut
METAL_BACKERS_G = {"A": 0.0, "B": FLAT_BACKER_G, "C": FLAT_BACKER_G, "D": 4 * 6.0}   # D: laser-cut in the pan order
ANGLE_AREA = (2 * 1.5 * IN - 0.125 * IN) * 0.125 * IN                # 1-1/2 x 1-1/2 x 1/8 in angle, mm2


def mass_table(key: str, c: dict) -> dict:
    rows = {}
    stay_len = 540.0                                             # z 0 -> 530 + 10 mm into the foot cup
    a = section_area(c["stay"])
    rows["stays x 2 (" + STOCK[c["stay"]]["desc"] + ")"] = 2 * stay_len * a * RHO[c["stay_mat"]]
    rows["mid bar (" + STOCK[c["bar"]]["desc"] + ", 220 mm)"] = 220.0 * section_area(c["bar"]) * RHO["alu_6061_t6"]
    ub = c.get("ubar", c["bar"])
    rows["upper bar (" + STOCK[ub]["desc"] + ", 220 mm)"] = 220.0 * section_area(ub) * RHO["alu_6061_t6"]
    lum = c["lumbar"]
    if lum["kind"] == "metal_pan":
        area = 250.0 * 140.0 + 2 * 250.0 * lum["flange"] + 2 * 140.0 * 12.0   # face + return flanges + stay lands
        rows[f"formed 6061 {lum['t'] / IN:.3f} in hip pan, 30 % lightening (ASSUMPTION PAN-CUTOUT)"] = area * lum["t"] * RHO["alu_6061_t6"] * 0.70
        if lum.get("padup"):
            rows[f"6061 {lum['padup'] / IN:.3f} in hip doubler 60 x 140 mm, riveted / bolted under the Ti mount"] = 60 * 140 * lum["padup"] * RHO["alu_6061_t6"]
    elif lum["kind"] == "cross_tube":
        rows["lumbar cross tube (" + STOCK[lum["tube"]]["desc"] + ", 220 mm)"] = 220.0 * section_area(lum["tube"]) * RHO["alu_6061_t6"]
        rows["6061 hip bracket: 2 x 60 mm of 1-1/2 x 1-1/2 x 1/8 in angle, 20 % lightening (ASSUMPTION)"] = 2 * 60.0 * ANGLE_AREA * RHO["alu_6061_t6"] * 0.8
    elif key == "A":
        area = 250.0 * 140.0 + 2 * 250.0 * lum["flange"]
        PRINTED["A"]["lower hub (hip boss, struts, foot sockets, US1 lugs, hinge fairleads)"] = area * lum["t"] * RHO["paht"] * 0.80
    for k, v in PRINTED[key].items():
        rows["printed: " + k] = float(v)
    if not c["stay"].startswith("f"):
        st = STOCK[c["stay"]]
        bore = st["od"] - 2 * st["t"]
        # crown kit carries over, but its 4 UHMWPE bushings (2 x stay top, 2 x leg end, 70 mm each, H1 bore 18) grow
        # with the new bore: booked here so the comparison is honest (uhmwpe_sheet density 935 kg/m3)
        rows["crown bushing growth (4 x 70 mm UHMWPE, bore 18 -> %.1f mm)" % bore] = (
            4 * 70.0 * math.pi / 4 * ((bore ** 2 - 16.0 ** 2) - (18.0 ** 2 - 16.0 ** 2)) * 0.935e-3)
    rows["6061 clamp backers (4)"] = METAL_BACKERS_G[key]
    rows["joint screws + nuts (A2)"] = sum(n * _bolt_g(d, L) for n, d, L in BOLTS[key])
    total = sum(rows.values())
    printed = sum(v for k, v in rows.items() if k.startswith("printed"))
    return {"rows": {k: round(float(v), 1) for k, v in rows.items()}, "body_g": round(total, 1),
            "printed_g": round(printed, 1), "hip_hw_g": round(hip_hw_g(key), 1),
            "frame_delta_vs_h1_g": round(total + hip_hw_g(key) - H1["body_g"] - H1["hip_hw_g"], 1),
            "frame_delta_vs_h1c_g": round(total + hip_hw_g(key) - H1C["body_g"] - H1C["hip_hw_g"], 1)}


def hip_hw_g(key):
    """Ti hip-mount fixings: A / C keep the H1 printed boss (inserts + screws, BL-077 28.8 g); B / D bolt the mount
    to metal with 8 x M5 x 12 A2 + nuts (no inserts, no arc plates)."""
    return 28.8 if key in ("A", "C") else 8 * _bolt_g(5, 12)


def cost_table(key: str, c: dict, mass: dict) -> dict:
    lines = []
    pieces = {}
    stay_len = 540.0
    pieces.setdefault(c["stay"], []).extend([stay_len, stay_len])
    pieces.setdefault(c["bar"], []).append(220.0)
    pieces.setdefault(c.get("ubar", c["bar"]), []).append(220.0)
    lum = c["lumbar"]
    if lum["kind"] == "cross_tube":
        pieces.setdefault(lum["tube"], []).append(220.0)
    for k, pcs in pieces.items():
        usd, how = buy(k, pcs)
        lines.append((f"{STOCK[k]['desc']}: {len(pcs)} piece(s) {', '.join(f'{p:.0f}' for p in pcs)} mm, buy {how}",
                      usd, STOCK[k]["src"] + "; fixed-length price table PRICE_LENGTHS"))
    if lum["kind"] == "metal_pan":
        lines.append((f"SendCutSend 6061 {lum['t'] / IN:.3f} in pan cut + 2 bends + 4 clamp backers"
                      + (f" + {lum['padup'] / IN:.3f} in doubler" if lum.get("padup") else "") + " (one order)",
                      45.0 + (8.0 if lum.get("padup") else 0.0) + (10.0 if lum["t"] > 0.1 * IN else 0.0),
                      "ASSUMPTION PAN-PRICE: no published bend price; order minimum USD 29 (BL-077 booking) + bends; +8 doubler, +10 for .125 in"))
    elif lum["kind"] == "cross_tube":
        lines.append(("6061-T6 1-1/2 x 1-1/2 x 1/8 in angle, 18 in (hip bracket, hand cut + drilled on a printed jig)",
                      4.92, "Speedy Metals p-2183 18 in USD 4.92 (search snippet, secondary)"))
        lines.append(("6061 1/8 x 1 in flat, 18 in (4 clamp backers, hand cut)", 3.25,
                      "Speedy Metals p-2225 18 in USD 3.25 (search snippet, secondary)"))
    elif key == "C":
        lines.append(("6061 1/8 x 1 in flat, 18 in (4 clamp backers, hand cut)", 3.25,
                      "Speedy Metals p-2225 18 in USD 3.25 (search snippet, secondary)"))
    pr = mass["printed_g"] * SUPPORT_X * PAHT_USD_G
    lines.append((f"PAHT-CF filament {mass['printed_g']:.0f} g x 1.10 support", pr, "record USD 80/kg; BL-053 support x1.10"))
    nb5 = sum(n for n, d, L in BOLTS[key] if d == 5)
    nb4 = sum(n for n, d, L in BOLTS[key] if d == 4)
    lines.append((f"A2 screws + nuts ({nb5} x M5, {nb4} x M4)", nb5 * BOLT_USD + nb4 * M4_USD,
                  "Zoro A2 M5 x 35 50-pk USD 41.79 (BL-077); M4 ASSUMPTION USD 0.50"))
    lines.append(("threadlocker share", 0.90, "BL-077 LOC-SHARE"))
    lines.append(("shipping (metal order), ASSUMPTION SHIP", 12.0, "ASSUMPTION: Speedy UPS ground, small parcel"))
    tot = sum(v for _, v, _ in lines)
    return {"lines": [{"item": a, "usd": round(float(b), 2), "source": s} for a, b, s in lines],
            "per_frame_usd": round(tot, 2), "within_cap": bool(tot <= CAP_USD)}


PROVING = {   # first-frame proving items beyond the frame itself (cap USD 150); tools each <= USD 50
    "common": [
               ("CL-1 clamp-slip + BB-1 bolt-bearing coupons: printed tees / saddles (60 g PAHT)", 60 * 0.08 * 1.1, "record"),
               ("tubing cutter to 1-1/8 in (new tool)", 15.0, "ASSUMPTION TOOL-PRICE (hardware-store class)"),
               ("deburr tool + 5.2 / 4.2 mm cobalt bits (new tools)", 14.0, "ASSUMPTION TOOL-PRICE")],
    "A": [("flat-bar bending jig (plywood + printed formers)", 8.0, "ASSUMPTION"),
          ("PAHT hub coupons (beyond the BL-079 G0 set)", 20.0, "ASSUMPTION")],
    "B": [("bending-service quote option for a U (not booked)", 0.0, "Xometry instant quote (no price cited)")],
    "C": [],
    "D": [],
}


def proving_cost(key, stay=None):
    spare = []
    if stay in PRICE_LENGTHS and 24 in PRICE_LENGTHS[stay]:
        spare = [(f"spare stay tube for coupons and a fit-up trial (24 in, {STOCK[stay]['desc']})",
                  PRICE_LENGTHS[stay][24], STOCK[stay]["src"] + "; 24 in price")]
    elif stay:
        spare = [("spare stay bar for coupons (24 in)", STOCK[stay]["usd"] / 2, STOCK[stay]["src"])]
    lines = spare + PROVING["common"] + PROVING[key]
    return {"lines": [{"item": a, "usd": round(b, 2), "source": s} for a, b, s in lines],
            "total_usd": round(sum(b for _, b, _ in lines), 2),
            "note": "the BL-079 PAHT coupons (USD 59.01, session G0) are already booked and also serve the printed parts"}


# ----------------------------------------------------------------------------- sizing + scoring
def _rows_of(r, roles, extra=()):
    vals = [v["margin"] for k, v in r["strength"].items() if k in roles]
    vals += [v["margin"] for k, v in r["fatigue"].items() if k in roles]
    vals += [h["margin"] for h in r["checks"] if any(e in h["label"] for e in extra)]
    return min(vals) if vals else np.inf


def size_concept(key: str, c: dict, log=print, torsos=(15.0, 23.0)) -> tuple[dict, dict]:
    """Coordinate sizing, lightest first, each part on its own rows: stays (strength, fatigue, buckling), upper bar
    (bars strength / fatigue, upper tee slip), hub (pan / cross tube strength, fatigue, hub bolts). Parts that are
    printed (A, C hubs) are not sized here (see ``hub_thickness_needed``). Sizing runs torsos 15 / 23; the final
    record re-runs 15 / 19 / 23."""
    cc = copy.deepcopy(c)
    log_rows = []
    cc["ubar"] = UBAR_OPTIONS[-1]
    if cc["lumbar"]["kind"] == "cross_tube":
        cc["lumbar"]["tube"] = CROSS_OPTIONS[-1]
    if cc["lumbar"]["kind"] == "metal_pan":
        cc["lumbar"]["t"], cc["lumbar"]["padup"] = PAN_OPTIONS[-1]

    def pick(label, options, setter, roles, extra=(), buck=False):
        best = None
        for opt in options:
            trial = copy.deepcopy(cc)
            setter(trial, opt)
            r = evaluate(trial, torsos=torsos)
            mg = _rows_of(r, roles, extra)
            if buck and r["buckling"]:
                mg = min(mg, r["buckling"]["margin"])
            log_rows.append({"part": label, "option": str(opt), "margin": round(float(mg), 3)})
            log(f"  {key} {label} {opt}: {mg:.2f}")
            if best is None or mg > best[1]:
                best = (opt, mg)
            if mg >= 1.0:
                return opt
        return best[0]          # none passes: keep the strongest and report it

    stay_opts = FLAT_OPTIONS if cc["stay"] and cc["stay"].startswith("f") else sorted(STAY_OPTIONS, key=section_area)
    cc["stay"] = stay_opts[-1]
    cc["stay"] = pick("stay", stay_opts, lambda t, o: t.__setitem__("stay", o), ("stays",), buck=True)
    cc["ubar"] = pick("upper bar", sorted(UBAR_OPTIONS, key=section_area), lambda t, o: t.__setitem__("ubar", o),
                      ("bars",), extra=("upper_bar tee",))
    if cc["lumbar"]["kind"] == "cross_tube":
        cc["lumbar"]["tube"] = pick("cross tube", sorted(CROSS_OPTIONS, key=section_area),
                                    lambda t, o: t["lumbar"].__setitem__("tube", o), ("hub",), extra=("hub-to-stay",))
    if cc["lumbar"]["kind"] == "metal_pan":
        tp = pick("pan (t, doubler)", PAN_OPTIONS,
                  lambda t, o: t["lumbar"].update({"t": o[0], "padup": o[1]}), ("hub",), extra=("hub-to-stay",))
        cc["lumbar"]["t"], cc["lumbar"]["padup"] = tp
    r = evaluate(cc)
    r["sizing_log"] = log_rows
    return cc, r


def hub_thickness_needed(c: dict, ts=(8, 10, 12, 14, 16, 20, 24)) -> dict:
    """PAHT hub: thinnest equivalent solid pan that passes hub strength + fatigue (first order)."""
    for t in ts:
        cc = copy.deepcopy(c)
        cc["lumbar"]["t"] = float(t)
        r = evaluate(cc, torsos=(15.0, 23.0))
        hub = min(r["strength"]["hub"]["margin"], r["fatigue"]["hub"]["margin"])
        if hub >= 1.0:
            area = 250.0 * 140.0 + 2 * 250.0 * cc["lumbar"]["flange"]
            return {"t_mm": t, "hub_margin": hub, "hub_g": round(area * t * RHO["paht"] * 0.80, 1)}
    return {"t_mm": None, "note": f"no thickness up to {ts[-1]} mm passes"}


def run(log=print) -> dict:
    out = {"ticket": "BL-080", "date": "2026-11-25", "standard": "HA-LS-1 rev C (ls1_envelope, torsos 15/19/23)",
           "baselines": {"H1": H1, "H1c": H1C, "cap_usd": CAP_USD}, "concepts": {}}
    for key, c in CONCEPTS.items():
        log(f"concept {key}")
        cc, r = size_concept(key, c, log)
        mass = mass_table(key, cc)
        cost = cost_table(key, cc, mass)
        entry = {"name": c["name"], "short": c["short"], "story": c["story"], "stay": cc["stay"],
                 "stay_desc": STOCK[cc["stay"]]["desc"], "bar_desc": STOCK[cc["bar"]]["desc"], "ubar": cc.get("ubar"),
                 "lumbar": cc["lumbar"], "checks": _jsonable(r), "mass": mass, "cost": cost,
                 "proving": proving_cost(key, cc["stay"])}
        if cc["lumbar"]["kind"] == "paht":
            entry["hub_needed"] = hub_thickness_needed(cc)
        entry["strong_pass"] = bool(r["min_margin"] >= 1.0)
        out["concepts"][key] = entry
    ITER2.mkdir(parents=True, exist_ok=True)
    REC_JSON.write_text(json.dumps(out, indent=1))
    return finalize()


def finalize() -> dict:
    """Ranking and pick from the stored record (no re-solve): mass and cost re-booked from the stored sizes; RUBRIC
    order; the pick is the first concept that passes Strong and the cap (owner may override)."""
    out = json.loads(REC_JSON.read_text())
    for k, e in out["concepts"].items():
        cc = {**CONCEPTS[k], "stay": e["stay"], "lumbar": e["lumbar"]}
        if e.get("ubar"):
            cc["ubar"] = e["ubar"]
        e["mass"] = mass_table(k, cc)
        e["cost"] = cost_table(k, cc, e["mass"])
        e["proving"] = proving_cost(k, e["stay"])
    out["ranking"] = rank(out["concepts"])
    top = out["ranking"][0]
    out["pick"] = top["concept"] if (top["strong"] and top["within_cap"]) else None
    REC_JSON.write_text(json.dumps(out, indent=1))
    return out


def rank(concepts: dict) -> list[dict]:
    """RUBRIC order: Strong gate -> cost cap -> mass (body, lighter first). Looks are judged on the sheet."""
    rows = []
    for k, e in concepts.items():
        rows.append({"concept": k, "strong": e["strong_pass"], "min_margin": round(e["checks"]["min_margin"], 3),
                     "within_cap": e["cost"]["within_cap"], "usd": e["cost"]["per_frame_usd"],
                     "body_g": e["mass"]["body_g"]})
    rows.sort(key=lambda d: (not d["strong"], not d["within_cap"], d["body_g"]))
    for i, d in enumerate(rows, 1):
        d["rank"] = i
    return rows


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return float(x)
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def update_one(key: str, log=print) -> dict:
    """Re-size one concept and write it into the stored record (then re-rank)."""
    out = json.loads(REC_JSON.read_text())
    c = CONCEPTS[key]
    cc, r = size_concept(key, c, log)
    mass = mass_table(key, cc)
    entry = {"name": c["name"], "short": c["short"], "story": c["story"], "stay": cc["stay"],
             "stay_desc": STOCK[cc["stay"]]["desc"], "bar_desc": STOCK[cc["bar"]]["desc"], "ubar": cc.get("ubar"),
             "lumbar": cc["lumbar"], "checks": _jsonable(r), "mass": mass, "cost": cost_table(key, cc, mass),
             "proving": proving_cost(key, cc["stay"])}
    if cc["lumbar"]["kind"] == "paht":
        entry["hub_needed"] = hub_thickness_needed(cc)
    entry["strong_pass"] = bool(r["min_margin"] >= 1.0)
    out["concepts"][key] = entry
    REC_JSON.write_text(json.dumps(out, indent=1))
    return finalize()


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        res = run()
        for d in res["ranking"]:
            print(d)
    elif cmd == "one":
        update_one(sys.argv[2])
    elif cmd == "plots":
        from .bl080_plots import main as _plots
        _plots()
