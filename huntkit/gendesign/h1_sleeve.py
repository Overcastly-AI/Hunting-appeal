"""BL-024: H1 printed body, sleeve and crown-leg seat redesign for fatigue margin on the cloth-sim loads.

    python -m huntkit.gendesign.h1_sleeve            # cached solver results -> md / json / png
    python -m huntkit.gendesign.h1_sleeve --run      # run any missing body solves (about 1 min each, 2 cores)

What it does (ticket docs/backlog/BL-024-h1-sleeve-redesign.md):
1. Reproduces BL-021's H1 body check on the fine cloth-sim loads (1.001, 23 in meat, "stay L sleeve (crown bore
   wall)") and finds WHERE the FI99 actually comes from: the 1 % most-utilised voxels of the governing set, by region.
2. Two sim bases (BL-025, DECISIONS 2026-11-12): ``fine`` = BL-021's fine rev 1 runs (23 in meat F_r1_PR23_fineFM,
   IM3 L 522 N) and ``fine_sm8`` = the same with the 23 in meat case from F_r1_PR23_fineFM_sm8 (IM3 L 561.8 N, hinges
   +6.5 %), the higher of the two fine 23 in meat runs. Contact fields from the kept stage (BL-025 reader).
3. Every crown kit (S 15-18, M 17.5-20.5, L 20-23 in, today's 16 x 8 legs; crown_diet specs a_S / a_M / a_L) at each
   of its settings; the sim run of the nearest simulated torso (15 / 19 / 23), and the other neighbour as a check.
4. Trial changes: bore side (longer crown-leg engagement, bonded sleeve liner), and the load-path fix the location
   study points to (grow-only fully-stressed offset of the lower body with H1's own tool, frame_comp_d.offset_step).
5. Rev C on the beam loads and the sim loads per torso and kit, cinch static and cycled (ASSUMPTION CINCH_STATIC),
   strength, creep, branch buckling, the z 234 joint, keep-outs, mass, CA-1 flip point.

Shared modules are not edited (load placement swapped in for the duration of a call, as BL-021 does).
Units: N, mm, g, MPa.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import os
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_sleeve.json"
DOC = ANALYSIS / "h1_sleeve.md"
OUT = REPO / "outputs" / "h1_sleeve"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261112_BL024_"

FAT_REQ = 1.15             # BL-024 goal: fatigue >= 1.15 on the sim loads at every torso and crown kit
STR_REQ = 1.4              # BL-024 goal: strength >= 1.4
FAT_G = 1.6                # rev C fatigue: 1e5 cycles 0 -> 1.6 g
PAHT_FAT = 0.30            # ASSUMPTION PAHT_FAT (record): fatigue_1e5_ratio of PAHT-CF; CA-1 settles it

RUNS = {15: "F_r1_PR15_fineFM", 19: "F_r1_PR19_fineFM", 23: "F_r1_PR23_fineFM"}
SM8 = "F_r1_PR23_fineFM_sm8"          # BL-025: the higher of the two fine 23 in meat runs (meat case only)
BASES = {
    # basis -> sim torso -> {case: run}
    "fine": {t: {"fill": r, "meat": r} for t, r in RUNS.items()},
    "fine_sm8": {**{t: {"fill": r, "meat": r} for t, r in RUNS.items()}, 23: {"fill": RUNS[23], "meat": SM8}},
}
SIM_TORSOS = (15, 19, 23)
KITS = {"h1": (15.0, 19.0, 23.0), "a_S": (15.0, 18.0), "a_M": (17.5, 19.0, 20.5), "a_L": (20.0, 23.0)}
KIT_LABEL = {"h1": "H1 15-23 (one crown)", "a_S": "kit S 15-18", "a_M": "kit M 17.5-20.5", "a_L": "kit L 20-23"}

ASSUMPTIONS = {
    "SIM_TORSO": ("A crown-kit setting between the simulated torsos (15 / 19 / 23 in) takes the bag forces of the "
                  "nearest simulated torso (17.5, 18, 20, 20.5 -> 19 in); the other neighbour is run as a check and "
                  "the worse of the two is reported. The crown (legs, bushings, top bar) is the kit's own at the "
                  "setting's torso.",
                  "A CORRIE F fine meat run at 18 and 20.5 in (corrie_f_sim.py finerun F --torso 18 / 20.5)."),
    "SIM_BODY": ("As BL-021 (im3_body_simloads ASSUMPTION SIM_BODY): the sim's 1 g frame-side forces scaled by "
                 "g x load / 68 kg, closed on the payload weight at the sim CG.",
                 "T9 loaded CG + frame strain gauges at the stays and the lumbar struts in the T1 carry test."),
    "CINCH_STATIC": ("As BL-021: the meat-strap cinch is a static preload, in every strength and creep set but not in "
                     "the static-carry set that gives fatigue; the cycled bound is reported beside it.",
                     "MT-1 strap tension readout over a 10 min loaded walk in the T2 meat test."),
    "PAHT_FAT": ("PAHT-CF fatigue_1e5_ratio 0.30 (record ASSUMPTION).", "CA-1 coupon test (flip point in section 6)."),
    "FI99": ("The body margin is H1's FI99 rule (99th percentile of the failure index over the non-load-patch "
             "voxels, 2 mm grid, frame_comp_d.evaluate). A change that adds material is credited only through the "
             "stresses it lowers; the governing region's own percentile is reported beside it so the body number "
             "is not raised by diluting the population.",
             "T1 frame strain gauges at the lumbar struts / stay feet (z 100-200) against the voxel model's strain."),
    "LINER": ("Sleeve liner trial: a bonded tube in the bore is modelled as the bore ring r 9-11 mm with its Young's "
              "modulus scaled so the ring's bending stiffness EI equals the tube's (6061-T6 20 x 1 mm; voxel ring "
              "I from the 2 mm grid). Bond assumed perfect; the liner's own stress is not part of the body FI.",
              "Only needed if a liner is adopted: a bonded-liner coupon (push-out) and a stay 3-point bend."),
    "LEG_ENGAGE": ("Longer-leg trial: each kit's legs are lengthened so that at the kit's lowest setting the leg "
                   "bottom sits at H1's 15 in depth (z 171): +127 mm each (crown_diet deepest leg bottom z 298).",
                   "Only needed if adopted: crown legs FPF re-run (crown_diet.crown_margins) at the new length."),
}


def _np_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ======================================================================================= 1. sim frame forces
FORCES = OUT / "sim_forces.json"


def sim_forces(refresh: bool = False) -> dict:
    """1 g frame-side forces of every run the bases use (BL-021's reader, contact on the kept stage per BL-025),
    keyed '<run>|<case>'. Cached in OUT."""
    from . import im3_body_simloads as B
    if FORCES.exists() and not refresh:
        return json.loads(FORCES.read_text())
    out = {}
    for basis in BASES.values():
        for t, cases in basis.items():
            for case, run in cases.items():
                k = f"{run}|{case}"
                if k not in out:
                    out[k] = B.frame_forces_from_run(run, t, case)
                    out[k]["total_kg"] = B.sim_total_kg(run, case)
    OUT.mkdir(parents=True, exist_ok=True)
    FORCES.write_text(json.dumps(out, default=_np_default))
    return out


def hook_summary(sf: dict) -> dict:
    """IM3 hook and hinge leg sums per run (meat), to show what the two 23 in bases differ by."""
    out = {}
    for k, ff in sf.items():
        if not k.endswith("|meat"):
            continue
        f = ff["forces"]
        out[k.split("|")[0]] = {
            "im3_R_n": f["hook_im520_R"]["leg_sum_n"], "im3_L_n": f["hook_im520_L"]["leg_sum_n"],
            "hinge_R_n": float(np.linalg.norm(f["hinge_R"]["f"])), "hinge_L_n": float(np.linalg.norm(f["hinge_L"]["f"])),
            "cg_mm": ff["cg_mm"], "total_kg": ff["total_kg"]}
    return out


# ======================================================================================= 2. load sets
def sim_torso(t: float, alt: bool = False) -> int:
    """Nearest simulated torso (ASSUMPTION SIM_TORSO); ``alt`` = the other neighbour for a setting in between."""
    d = sorted(SIM_TORSOS, key=lambda s: (abs(s - t), -s))
    if not alt or any(abs(t - s) < 1e-6 for s in SIM_TORSOS):
        return d[0]
    lo = max(s for s in SIM_TORSOS if s < t)
    hi = min(s for s in SIM_TORSOS if s > t)
    return hi if d[0] == lo else lo


def _env(ffs: dict, cycled: bool) -> dict:
    """Rev C envelope with the bag cases on the sim forces (BL-021 sim_env, both cases given explicitly)."""
    from huntkit.fea import load_standard as LS
    from . import im3_body_simloads as B
    env0 = LS.ls1_envelope("C")
    env = {}
    for i, (cn, (ff, kg)) in enumerate(ffs.items()):
        lst = []
        for c in env0["crown_bar"]:
            if c.name in B.BAG_CASES:
                c = copy.copy(c)
                # BL-021's flag: True = the cinch loop is left out of static carry (cinch static)
                c.params = {**c.params, "sim_ff": (ff, kg, not cycled)}
                lst.append(c)
        if i == 0:
            lst += [c for c in env0["crown_bar"] if c.name not in B.BAG_CASES]
        env[f"sim_{cn}"] = lst
    return env


def spec_for(kit: str, leg_extra: float = 0.0):
    from . import crown_diet as CD
    sp = CD.specs()[kit]
    if leg_extra:
        sp = dataclasses.replace(sp, name=f"{kit}_leg{leg_extra:+g}", leg_mm=round(sp.leg_mm + leg_extra, 1))
    return sp


def build_sets(kit: str, basis: str, cycled: bool = False, alt: bool = False, leg_extra: float = 0.0,
               sf: dict | None = None) -> list:
    """Per-setting-tagged LoadSets for crown ``kit`` on sim ``basis`` (or 'beam'). Tag: S_fill / S_meat (sim) or
    C / C_im3 (beam) @ '<kit>.<basis>[.alt].<torso>'. Cached (pickle) in OUT/sets."""
    from huntkit.fea import load_standard as LS
    from . import crown_diet as CD
    from . import im3_body_simloads as B
    from . import rev_c_verification as RV
    sp = spec_for(kit, leg_extra)
    tagb = f"{sp.name}.{basis}{'.cyc' if cycled else ''}{'.alt' if alt else ''}."
    p = OUT / "sets" / f"{tagb}pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    sets = []
    if basis == "beam":
        sets = CD._retag(CD.load_beam(sp, log=None)[0], tagb.replace(".", "_"))
    else:
        sf = sf or sim_forces()
        oe = LS.ls1_envelope
        RV.TAGS.update({"sim_fill": "S_fill", "sim_meat": "S_meat"})
        try:
            for t in KITS[kit]:
                st = sim_torso(t, alt)
                if alt and st == sim_torso(t):
                    continue
                ffs = {cn: (sf[f"{run}|{cn}"], sf[f"{run}|{cn}"]["total_kg"]) for cn, run in BASES[basis][st].items()}
                env = _env(ffs, cycled)
                B._install_sim_loads()
                LS.ls1_envelope = lambda rev="C", _e=env: _e
                try:
                    s_t = CD.beam_runs(dataclasses.replace(sp, torsos=(t,)), buckling=False, log=None)[0]
                finally:
                    LS.ls1_envelope = oe
                    B._uninstall_sim_loads()
                sets += s_t
        finally:
            LS.ls1_envelope = oe
            for k in ("sim_fill", "sim_meat"):
                RV.TAGS.pop(k, None)
        sets = CD._retag(sets, tagb.replace(".", "_"))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps(sets))
    return sets


# ======================================================================================= 3. body solve
def solve_fields_w(dom, solid, sets, weights: np.ndarray | None = None) -> dict:
    """frame_comp_d.solve_fields with a per-element stiffness weight (1 = PAHT-CF; >1 = a stiffer insert such as a
    bonded liner). Same exclusions (clamp / load-patch elements per scenario tag), same stress recovery."""
    from . import frame_comp_d as D
    from . import frame_topopt as ft
    if weights is None:
        return D.solve_fields(dom, solid, sets, log=None)
    t0 = time.time()
    g = dom.grid
    idx = np.where(solid)[0]
    _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    clamp = np.zeros(g.nn, bool)
    clamp[np.where(fixed[0::3])[0]] = True
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(g.h, 1.0, ft.NU))
    K = rs.assemble(np.asarray(weights, float)[rs.ae] if len(weights) == g.ne else np.asarray(weights, float))
    K.sort_indices()
    import pypardiso
    solver = pypardiso.PyPardisoSolver(mtype=2)
    solver.factorize(K)
    tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
    stress, ex_all, meta = [], {}, []
    for tg in tags:
        tsets = [s for s in sets if s.key.split(":")[0] == tg]
        F, _ = ft.assemble_loads(dom, tsets, solid_mask=solid)
        Ur = solver.solve(K, np.ascontiguousarray(F[rs.free])).reshape(rs.free.size, -1)
        U = np.zeros((g.ndof, len(tsets)))
        U[rs.free] = Ur
        Fn = np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2))
        ex_all[tg] = (clamp | (Fn > 0))[g.enodes].any(axis=1)[idx]
        for k, s in enumerate(tsets):
            _, S = ft.element_stress(g, U[:, k], solid, 1.0)
            stress.append(S.astype(np.float32))
            meta.append({"set": s.key, "scenario": tg, "case": s.case, "torso": s.torso, "factor": s.factor})
    try:
        solver.free_memory(everything=True)
    except Exception:
        pass
    return {"stress": stress, "meta": meta, "ex": ex_all, "idx": idx, "cen": g.elem_centers()[idx],
            "sections": {}, "seconds": time.time() - t0}


REGIONS = ("lumbar struts / pan", "hip-pivot boss", "stay foot", "stay below the sleeve", "stay sleeve z 160-240",
           "stay sleeve z 240-470", "stay top z 470-544", "inboard branch", "mid bar / upper bar")


def region(p) -> str:
    """Region of a voxel centre (finer than frame_cg_recheck.region_label, which calls every stay voxel above z 160
    'crown bore wall')."""
    from . import frame_cg_recheck as R
    lab = R.region_label(p)
    z = float(p[2])
    if "sleeve" in lab and "below" not in lab:
        return "stay sleeve z 160-240" if z < 240 else ("stay sleeve z 240-470" if z <= 470 else "stay top z 470-544")
    if "below the sleeve" in lab:
        return "stay below the sleeve"
    if lab in ("upper bar / pawl housing", "mid bar z 330"):
        return "mid bar / upper bar"
    return lab


def evaluate(fields: dict, excl_mask: np.ndarray | None = None) -> dict:
    """H1's rule (frame_comp_d.evaluate, PAHT-CF layer rule) plus, per scenario tag, the static-carry fatigue and
    where the top 1 % of the governing set sits. ``excl_mask`` (per solid element) is left out of the FI
    population (a liner's voxels)."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    if excl_mask is not None:
        fields = dict(fields)
        fields["ex"] = {k: v | excl_mask for k, v in fields["ex"].items()}
    ev = D.evaluate(fields, H1.MAT)
    m = D.MATERIALS[H1.MAT]
    per = {}
    for r in ev["rows"]:
        o = per.setdefault(r["scenario"], {"strength": 9e9, "fatigue": 9e9, "creep": 9e9})
        if r["sf"] < o["strength"]:
            o["strength"], o["strength_case"], o["strength_where"] = r["sf"], r["case"], r["where"]
        if r["case"] == "static_carry":
            fi1 = r["fi99"] / r["factor"]
            o["fatigue"] = min(o["fatigue"], m["fat"] / (fi1 * FAT_G))
            o["creep"] = min(o["creep"], m["rup"] / fi1)
            o["fatigue_set"] = r["set"]
            o["peak_xyz"] = r["peak_xyz"]
    # governing fatigue set: where its top 1 % sits
    gtag = min(per, key=lambda k: per[k]["fatigue"])
    k_set = next(i for i, mt in enumerate(fields["meta"]) if mt["set"] == per[gtag]["fatigue_set"])
    fi = D.fi_material(fields["stress"][k_set].astype(float), m)
    ex = fields["ex"][gtag]
    fi99 = float(np.percentile(fi[~ex], 99))
    top = (~ex) & (fi >= fi99)
    cen = fields["cen"]
    regs = np.array([region(p) for p in cen[top]])
    cnt = Counter(regs.tolist())
    # local percentile: each region's own 99th percentile (within the region, non-excluded)
    allreg = np.array([region(p) for p in cen])
    factor = fields["meta"][k_set]["factor"]
    loc = {}
    for rg in REGIONS:
        sel = (allreg == rg) & ~ex
        if sel.sum() >= 50:
            loc[rg] = {"n_top": int(cnt.get(rg, 0)), "share_top": float(cnt.get(rg, 0) / max(top.sum(), 1)),
                       "fatigue_p99_region": float(m["fat"] / (np.percentile(fi[sel], 99) / factor * FAT_G)),
                       "fatigue_peak_region": float(m["fat"] / (fi[sel].max() / factor * FAT_G))}
    return {"ev": ev, "per_tag": per, "governing_tag": gtag, "min": ev["min"], "top_regions": loc,
            "n_top": int(top.sum()), "util": ev["util"]}


def tag_key(tag: str) -> tuple:
    """'S_meat@a_L_fine_sm8_23' -> (scenario, kit/basis label, torso)."""
    sc, rest = tag.split("@", 1)
    lab, t = rest.rsplit("_", 1)
    return sc, lab, float(t)


def per_setting(per_tag: dict) -> dict:
    """min over the scenario tags of each (label, torso)."""
    out = {}
    for tg, v in per_tag.items():
        _, lab, t = tag_key(tg)
        o = out.setdefault(f"{lab}|{t:g}", {"strength": 9e9, "fatigue": 9e9, "creep": 9e9})
        for k in ("strength", "fatigue", "creep"):
            if v[k] < o[k]:
                o[k] = v[k]
                if k == "fatigue":
                    o["fatigue_tag"] = tg
    return out


def body_eval(name: str, solid: np.ndarray, sets: list, weights=None, excl=None, extra: dict | None = None,
              log=print, keep_util: bool = False) -> dict:
    """Solve + evaluate one body on ``sets``; cached as OUT/body_<name>.json (util as .npz when asked)."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    p = OUT / f"body_{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    t0 = time.time()
    c = H1.base()
    f = solve_fields_w(c["dom"], solid, sets, weights)
    r = evaluate(f, None if excl is None else excl[f["idx"]])
    bk = H1.buckling(f)
    out = {"name": name, "raster_g": D.mass_g(solid, H1.H, 1060.0), "min": r["min"],
           "per_tag": r["per_tag"], "per_setting": per_setting(r["per_tag"]), "governing_tag": r["governing_tag"],
           "top_regions": r["top_regions"], "n_top": r["n_top"],
           "buckling_min": float(min(v["margin"] for v in bk.values() if v["margin"] is not None)),
           "seconds": round(time.time() - t0), **(extra or {})}
    try:
        jc = H1.joint_check(f)
        out["joint_strength"], out["joint_fatigue"] = float(jc["min_strength"]), float(jc["min_fatigue"])
    except Exception as e:          # joint sections need the z 234 cut; report and carry on
        out["joint_error"] = repr(e)
    if keep_util:
        np.savez_compressed(OUT / f"util_{name}.npz", util=np.asarray(r["util"], np.float32), idx=f["idx"])
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, default=_np_default))
    if log:
        log(f"[{time.strftime('%H:%M:%S')}] body {name}: {out['raster_g']:.1f} g, min {json.dumps(out['min'], default=float)}"
            f" gov {out['governing_tag']} ({out['seconds']} s)")
    return out
