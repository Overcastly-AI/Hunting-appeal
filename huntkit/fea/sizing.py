"""Carbon pack-frame sizing sweep over buyable stock.

Design variables
- stay section: round roll-wrapped OD 16-25 mm or rectangular (lateral w x fore-aft h) tube,
- layup family (inner -> outer, angles from the tube axis):
    "RW0"  : woven 0/90 wrap, UD 0 core, woven 0/90 wrap   (standard off-the-shelf roll-wrapped)
    "RW45" : woven +-45 wrap, UD 0 core, woven +-45 wrap   (torsion-grade roll-wrapped, stock/custom)
    "UD90" : [90, +45, -45, 0_k] T700 UD                   ("[0/+-45/0] with a 90 wrap", custom)
  with the UD core ply count k setting the wall (0.8-2.0 mm),
- cross-bar section (round, same family choice), X-brace option, adhesive system.

Constraints (each must be >= 1 as a margin): for torso 15/19/23 in and all pack_standard cases,
member SF / required, buckling / 3.0, bond average SF / required, bond Volkersen peak SF /
required, fatigue (CFRP FI at 1.2 g <= 0.5, bond avg shear at 1.2 g <= 30 % lap shear).
Objective: total frame mass = tubes + hubs/sockets/sleeves/inserts + adhesive (frames.hardware_mass).
"""
from __future__ import annotations

import itertools
import time

import numpy as np

from .analysis import run_study
from .frames import build_frame
from .sections import composite_rect_tube, composite_tube

UD = "cfrp_t700_ud_epoxy_ply"
WV = "cfrp_t300_3k_woven_epoxy_ply"
UD_T, WV_T = 0.125, 0.22

# ASSUMPTION: adhesive shear moduli are not in the material records.
ADHESIVES = {
    "epoxy": {"adhesive": "adhesive_epoxy_toughened_2part", "adhesive_G_mpa": 800.0, "adhesive_t_mm": 0.3},
    "mma": {"adhesive": "adhesive_methacrylate_ma", "adhesive_G_mpa": 300.0, "adhesive_t_mm": 0.5},
}

# Base topology for the real frame (fixes from the placeholder study)
BASE = {
    "name": "pack5200_carbon",
    "height": 640.0,             # reaches a 23 in torso: yoke at 90 + 584 - 50 = 624 mm
    "width_top": 190.0,
    "width_bottom": 260.0,
    "stay_style": "straight",    # straight off-the-shelf tubes, lumbar curve in the foam
    "top_sweep": 15.0,
    "hip_z": 90.0,
    "mid_bar_z": 330.0,
    "anchors_at_nodes": True,
    "material": None,
}


def layup(family: str, k: int):
    if family == "RW0":
        return [(0, WV)] + [(0, UD)] * k + [(0, WV)]
    if family == "RW45":
        return [(45, WV)] + [(0, UD)] * k + [(45, WV)]
    if family == "UD90":
        return [(90, UD), (45, UD), (-45, UD)] + [(0, UD)] * k
    raise ValueError(family)


def wall(family: str, k: int) -> float:
    return {"RW0": 2 * WV_T, "RW45": 2 * WV_T, "UD90": 3 * UD_T}[family] + k * UD_T


def k_for_walls(family, walls=(0.8, 1.0, 1.25, 1.5, 2.0)):
    out = []
    for w in walls:
        k = int(round((w - wall(family, 0)) / UD_T))
        if k >= 1 and k not in out:
            out.append(k)
    return out


def section_spec(shape, family, k):
    """YAML-friendly spec dict (frames/_sec builds the Section)."""
    lay = [{"angle": a, "material": m} for a, m in layup(family, k)]
    if shape[0] == "round":
        return {"type": "composite_tube", "od": shape[1], "layup": lay}
    return {"type": "composite_rect_tube", "w": shape[1], "h": shape[2], "layup": lay}


def make_section(spec):
    s = dict(spec)
    typ = s.pop("type")
    lay = [(d["angle"], d["material"]) for d in s.pop("layup")]
    if typ == "composite_tube":
        return composite_tube(s["od"], lay)
    return composite_rect_tube(s["w"], s["h"], lay)


def params_for(c: dict) -> dict:
    p = dict(BASE)
    p["section"] = make_section(c["stay"])
    p["crossbar_section"] = make_section(c["bar"])
    if c.get("brace"):
        p["xbrace"] = c["brace"]
        p["brace_section"] = make_section(c["brace_sec"])
    adh = ADHESIVES[c["adhesive"]]
    p["joint"] = {**adh, "overlap_mm": c.get("overlap", 30.0), "through_overlap_mm": c.get("through_overlap", 40.0)}
    return p


def evaluate(c: dict, torsos=(15, 19, 23), stop_below: float | None = None) -> dict:
    """Run every case at every torso setting; return margins (>= 1 passes) and mass."""
    worst = {"margin": np.inf}
    per_case = {}
    mass = None
    for t in torsos:
        fm = build_frame({**params_for(c), "torso_in": t})
        mass = fm["hardware"]
        st = run_study(fm)
        checks = []
        for name, r in st["results"].items():
            req = r.meta["required_sf"]
            checks.append((r.min_sf / req, f"{name}: member {r.critical_member['id']}", name))
            if r.buckling_factors:
                checks.append((r.buckling_sf / 3.0, f"{name}: buckling", name))
            for j in st["joints"][name]:
                checks.append((j["sf_avg"] / req, f"{name}: bond avg {j['joint']}/{j['kind']}", name))
                checks.append((j["sf_peak"] / req, f"{name}: bond peak {j['joint']}/{j['kind']}", name))
        f = st["fatigue"]
        for m in f["members"]:
            checks.append((m.get("sf", m.get("life", np.inf) / f["cfg"]["cycles_required"]),
                           f"fatigue member {m['member']}", "fatigue"))
        for j in f["joints"]:
            checks.append((j["sf"], f"fatigue bond {j['joint']}", "fatigue"))
        for mrg, what, case in checks:
            key = (case, t)
            per_case[key] = min(per_case.get(key, np.inf), mrg)
            if mrg < worst["margin"]:
                worst = {"margin": mrg, "what": what, "torso": t}
        if stop_below is not None and worst["margin"] < stop_below:
            break
    return {"cand": c, "margin": worst["margin"], "governing": worst, "per_case": per_case,
            "mass_g": mass["total_g"], "tubes_g": mass["tubes_g"], "hubs_g": mass["hubs_g"],
            "feasible": worst["margin"] >= 1.0}


def label(c: dict) -> str:
    def s(spec):
        fam = _family_of(spec)
        k = sum(1 for d in spec["layup"] if d["material"] == UD and d["angle"] == 0)
        geo = f"{spec['od']:g}" if "od" in spec else f"{spec['w']:g}x{spec['h']:g}"
        return f"{geo} {fam} k{k} ({_wall(spec):.2f})"
    out = f"stay {s(c['stay'])} | bar {s(c['bar'])}"
    if c.get("brace"):
        out += f" | X-{c['brace']} {s(c['brace_sec'])}"
    return out + f" | {c['adhesive']}"


def _family_of(spec):
    first = spec["layup"][0]
    if first["material"] == WV:
        return "RW45" if first["angle"] == 45 else "RW0"
    return "UD90"


def _wall(spec):
    return sum(WV_T if d["material"] == WV else UD_T for d in spec["layup"])


def stay_options():
    rounds = [("round", od) for od in (16, 18, 20, 22, 25)]
    rects = [("rect", 12.7, 25.4), ("rect", 15.9, 25.4), ("rect", 19.0, 25.4)]
    for shape in rounds + rects:
        for fam in ("RW0", "RW45", "UD90"):
            for k in k_for_walls(fam):
                yield section_spec(shape, fam, k)


def bar_options():
    for od in (16, 18, 20, 22, 25):
        for fam in ("RW45", "UD90"):
            for k in k_for_walls(fam, (0.8, 1.0, 1.25, 1.5)):
                yield section_spec(("round", od), fam, k)


def sweep(log=print, quick_torso=(19,), stage1_keep=8, stage2_keep=12) -> dict:
    """Staged search. Stage 1: stays with a stiff reference cross-bar. Stage 2: cross-bars,
    braces, adhesive around the best stays. Stage 3: full 15/19/23 in check of the best."""
    t0 = time.time()
    ref_bar = section_spec(("round", 22), "RW45", 6)
    s1 = []
    for st in stay_options():
        c = {"stay": st, "bar": ref_bar, "adhesive": "mma"}
        e = evaluate(c, quick_torso)
        # rank stays by their own member margins only (joints / bars are sized next)
        stay_m = min(v for (case, _), v in e["per_case"].items()) if False else e["margin"]
        e["stay_margin"] = _member_margin(c, quick_torso)
        s1.append(e)
    log(f"stage 1: {len(s1)} stay options in {time.time() - t0:.0f} s")
    ok = [e for e in s1 if e["stay_margin"] >= 1.0]
    ok.sort(key=lambda e: e["tubes_g"])
    best_stays = _diverse(ok, stage1_keep)

    s2 = []
    braces = [None, "lower", "both"]
    brace_sec = section_spec(("round", 12.7), "RW45", 3)
    for e1, bar, br, adh in itertools.product(best_stays, list(bar_options()), braces, ADHESIVES):
        c = {"stay": e1["cand"]["stay"], "bar": bar, "adhesive": adh}
        if br:
            c.update(brace=br, brace_sec=brace_sec)
        s2.append(evaluate(c, quick_torso, stop_below=None))
    log(f"stage 2: {len(s2)} combinations, {time.time() - t0:.0f} s")
    s2.sort(key=lambda e: e["mass_g"])
    feas = [e for e in s2 if e["margin"] >= 1.0]
    cand3 = feas[:stage2_keep] + pareto(s2)[:stage2_keep]
    seen, s3 = set(), []
    for e in cand3:
        key = label(e["cand"])
        if key in seen:
            continue
        seen.add(key)
        s3.append(evaluate(e["cand"], (15, 19, 23)))
    log(f"stage 3: {len(s3)} full checks, {time.time() - t0:.0f} s")
    return {"stage1": s1, "stage2": s2, "stage3": s3}


def _member_margin(c, torsos):
    """Stay+bar member/buckling margin only (ignores joints & fatigue)."""
    m = np.inf
    for t in torsos:
        st = run_study(build_frame({**params_for(c), "torso_in": t}))
        for name, r in st["results"].items():
            req = r.meta["required_sf"]
            stays = [mm["sf"] for mm in r.members if mm["group"].startswith("stay")]
            m = min(m, min(stays) / req)
            if r.buckling_factors:
                m = min(m, r.buckling_sf / 3.0)
    return m


def _diverse(evals, n):
    """Lightest feasible per (shape-type, family) first, then fill by mass."""
    out, seen = [], set()
    for e in evals:
        key = ("od" in e["cand"]["stay"], _family_of(e["cand"]["stay"]))
        if key not in seen:
            out.append(e)
            seen.add(key)
    for e in evals:
        if len(out) >= n:
            break
        if e not in out:
            out.append(e)
    return out[:n]


def pareto(evals):
    """Non-dominated set: lower mass and higher margin."""
    pts = sorted(evals, key=lambda e: (e["mass_g"], -e["margin"]))
    out, best = [], -np.inf
    for e in pts:
        if e["margin"] > best + 1e-9:
            out.append(e)
            best = e["margin"]
    return out
