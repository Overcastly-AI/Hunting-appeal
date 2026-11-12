"""BL-024: H1 printed body, sleeve and crown-leg seat redesign for fatigue margin on the cloth-sim loads.

    python -m huntkit.gendesign.h1_sleeve            # cached solver results -> md / json / png
    python -m huntkit.gendesign.h1_sleeve --run      # run any missing body solves (about 1-2 min each, 2 cores; all cached)

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


# ======================================================================================= 4. trials
LINER = {"material": "6061-T6 aluminium tube 20 x 1 mm (bore printed 20.0, reamed)", "od": 20.0, "t": 1.0,
         "E": 68900.0, "rho": 2.70e-3, "z0": 160.0, "z1": 544.0}      # E, rho: data/materials/metals 6061-T6
E_PAHT = 3860.0                                                       # frame_comp_d.MATERIALS paht_fdm E
LEG_EXTRA_MM = 127.0      # crown_diet: deepest leg bottom z 298 in every kit -> H1's 15 in depth z 171


def kit_sets(basis: str, kits=("a_S", "a_M", "a_L"), alt: bool = True, cycled: bool = False,
             leg_extra: float = 0.0) -> list:
    sets = []
    for k in kits:
        sets += build_sets(k, basis, cycled=cycled, leg_extra=leg_extra)
        if alt and basis != "beam" and not cycled:
            sets += build_sets(k, basis, alt=True, leg_extra=leg_extra)
    return sets


def liner_weights(solid: np.ndarray, lin: dict = LINER) -> tuple:
    """(element weights, liner mask, added g per frame) for a bonded liner tube in both bores (ASSUMPTION LINER)."""
    from . import frame_fixed as FF
    from . import frame_h1 as H1
    c = H1.base()
    cen = c["cen"]
    r = FF._stay_r(cen)
    z = cen[:, 2]
    ring = solid & (r >= 9.0) & (r < 11.0) & (z >= lin["z0"]) & (z <= lin["z1"]) & (np.abs(cen[:, 0]) > 60)
    ro, ri = lin["od"] / 2, lin["od"] / 2 - lin["t"]
    I_tube = np.pi / 4 * (ro ** 4 - ri ** 4)
    I_ring = np.pi / 4 * (11.0 ** 4 - 9.0 ** 4)
    w = np.ones(c["dom"].grid.ne)
    w[ring] = lin["E"] * I_tube / (E_PAHT * I_ring)
    L = lin["z1"] - lin["z0"]
    added = 2 * L * (np.pi * (ro ** 2 - ri ** 2) * lin["rho"] - np.pi * (10.0 ** 2 - 9.0 ** 2) * 1.06e-3)
    return w, ring, float(added), float(w[ring][0]) if ring.any() else 1.0


def h1_shift() -> np.ndarray:
    from . import frame_h1 as H1
    return np.load(H1.OUT / "h1_shift.npz")["shift"].astype(float)


def grown_solid(shift: np.ndarray) -> np.ndarray:
    from . import crown_diet as CD
    from . import frame_h1 as H1
    return H1.assemble(shift) | CD._h1_solid()


def grow_study(name: str = "grow", basis: str = "fine_sm8", iters: int = 5, target: float = FAT_REQ * 1.02,
               zmax: float | None = None, log=print) -> list:
    """Grow-only fully-stressed offset (frame_comp_d.offset_step, H1's tool and settings) from H1's shift, driven by
    the per-voxel utilisation on every kit setting of ``basis`` (cinch static), until the body fatigue reaches
    FAT_REQ. ``zmax``: growth only below this z (the rest keeps H1's surface). Each iterate cached."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    from . import crown_diet as CD
    c = H1.base()
    dom = c["dom"]
    sets = kit_sets(basis)
    shift = h1_shift()
    base_g = D.mass_g(CD._h1_solid(), H1.H, 1060.0)
    hist = []
    zc = c["cen"][:, 2]
    for it in range(iters + 1):
        sp = OUT / f"shift_{name}_{it}.npz"
        if sp.exists():
            shift = np.load(sp)["shift"]
        else:
            np.savez_compressed(sp, shift=shift)
        solid = grown_solid(shift)
        r = body_eval(f"{name}_{it}", solid, sets, keep_util=True,
                      extra={"added_g": D.mass_g(solid, H1.H, 1060.0) - base_g, "it": it, "zmax": zmax}, log=log)
        hist.append(r)
        if r["min"]["fatigue"] >= FAT_REQ or it == iters:
            break
        nsp = OUT / f"shift_{name}_{it + 1}.npz"
        if nsp.exists():
            continue
        util = np.load(OUT / f"util_{name}_{it}.npz")["util"].astype(float)
        new = D.offset_step(dom, c["sdf0"], solid, util, shift, target, grow_only=True)
        if zmax is not None:
            new[zc > zmax] = shift[zc > zmax]
        np.savez_compressed(nsp, shift=new)
        shift = new
    return hist


def alpha_shift(alpha: float, name: str = "grow", step: int = 1) -> np.ndarray:
    """H1 shift + alpha x (the grow study's step ``step`` - H1): the same growth pattern scaled down, to find the
    least added mass that still passes."""
    s0 = h1_shift()
    s1 = np.load(OUT / f"shift_{name}_{step}.npz")["shift"]
    return s0 + float(alpha) * (s1 - s0)


def alpha_eval(alpha: float, basis: str = "fine_sm8", log=print, keep_util: bool = False) -> dict:
    from . import crown_diet as CD
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    solid = grown_solid(alpha_shift(alpha))
    base_g = D.mass_g(CD._h1_solid(), H1.H, 1060.0)
    return body_eval(f"grow_a{alpha:g}.{basis}", solid, kit_sets(basis), keep_util=keep_util,
                     extra={"added_g": D.mass_g(solid, H1.H, 1060.0) - base_g, "alpha": alpha}, log=log)


# ======================================================================================= 5. report
def _load(name: str) -> dict | None:
    p = OUT / f"body_{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def per_kit(d: dict) -> dict:
    """Per crown kit: worst fatigue / strength / creep over its settings (nearest sim torso and the other
    neighbour), and the setting that governs."""
    out = {}
    for k, v in d["per_setting"].items():
        lab, t = k.split("|")
        kit = lab[:3] if lab.startswith("a_") else lab.split("_")[0]
        o = out.setdefault(kit, {"fatigue": 9e9, "strength": 9e9, "creep": 9e9, "settings": {}})
        o["settings"][t] = min(o["settings"].get(t, 9e9), v["fatigue"])
        for kk in ("fatigue", "strength", "creep"):
            if v[kk] < o[kk]:
                o[kk] = v[kk]
                if kk == "fatigue":
                    o["fatigue_at"] = f"{t} in" + (" (other-neighbour sim)" if "_alt" in lab else "")
    return out


TRIALS = [
    ("h1__kits.fine_sm8", "H1 as released (crown kits S/M/L)", "-"),
    ("trial_leg127.fine_sm8", "bore side: crown legs +127 mm (more leg in the stay)", "bore"),
    ("trial_liner_al.fine_sm8", "bore side: bonded 6061 liner 20 x 1 mm, z 160-544", "bore"),
    ("grow_a0.3.fine_sm8", "load path: lower-body growth x 0.30", "path"),
    ("grow_a0.45.fine_sm8", "load path: lower-body growth x 0.45", "path"),
    ("grow_a0.55.fine_sm8", "load path: lower-body growth x 0.55", "path"),
    ("grow_a0.6.fine_sm8", "load path: lower-body growth x 0.60", "path"),
    ("grow_1", "load path: full grow step (x 1.0)", "path"),
]


def compute() -> dict:
    from . import crown_diet as CD
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    sf = sim_forces()
    rep = _load("h1__h1.fine")
    sc, lab, t = tag_key(rep["governing_tag"])
    res = {"date": "2026-11-12", "targets": {"fatigue": FAT_REQ, "strength": STR_REQ},
           "forces": hook_summary(sf),
           "reproduce": {"fatigue": rep["min"]["fatigue"], "strength": rep["min"]["strength"], "tag": rep["governing_tag"],
                         "torso": int(t), "per_setting": rep["per_setting"],
                         "bl021_label": "stay L sleeve (crown bore wall)", "peak_xyz": rep["per_tag"][rep["governing_tag"]]["peak_xyz"]},
           "location": {k: _load(n)["top_regions"] for k, n in (("fine", "h1__h1.fine"), ("fine_sm8", "h1__h1.fine_sm8"),
                                                                  ("fine_cyc", "h1__h1.fine.cyc"), ("beam_kits", "h1__kits.beam"))},
           "baseline": {}, "trials": [], "assumptions": ASSUMPTIONS}
    res["location"]["top_regions"] = res["location"]["fine_sm8"]
    for b, n in (("fine", "h1__kits.fine"), ("fine_sm8", "h1__kits.fine_sm8"), ("fine_sm8_cyc", "h1__kits.fine_sm8.cyc"),
                 ("beam", "h1__kits.beam"), ("h1_fine", "h1__h1.fine"), ("h1_fine_sm8", "h1__h1.fine_sm8")):
        d = _load(n)
        res["baseline"][b] = {"min": d["min"], "per_kit": per_kit(d) if "kits" in n else None,
                              "per_setting": d["per_setting"], "buckling_min": d["buckling_min"],
                              "joint": [d.get("joint_strength"), d.get("joint_fatigue")], "raster_g": d["raster_g"]}
    for n, label, kind in TRIALS:
        d = _load(n)
        if d is None:
            continue
        lp = d["top_regions"].get("lumbar struts / pan", {})
        res["trials"].append({"name": n, "label": label, "kind": kind, "added_g": float(d.get("added_g") or 0.0),
                              "fatigue": d["min"]["fatigue"], "strength": d["min"]["strength"], "creep": d["min"]["creep"],
                              "per_kit": {k: v["fatigue"] for k, v in per_kit(d).items()},
                              "lumbar_p99": lp.get("fatigue_p99_region"), "buckling_min": d["buckling_min"],
                              "top_shares": {k: v["share_top"] for k, v in d["top_regions"].items() if v["n_top"]}})
    # recommended: the least-mass passing growth
    ok = [t_ for t_ in res["trials"] if t_["kind"] == "path" and t_["fatigue"] >= FAT_REQ and t_["name"].startswith("grow_a")]
    best = min(ok, key=lambda t_: t_["added_g"]) if ok else None
    if best:
        a = _load(best["name"])["alpha"]
        fine, cyc, beam = (_load(f"grow_a{a:g}.{b}") for b in ("fine", "fine_sm8.cyc", "beam"))
        sm8 = _load(best["name"])
        fmin = min(sm8["min"]["fatigue"], fine["min"]["fatigue"])
        smin = min(sm8["min"]["strength"], fine["min"]["strength"], cyc["min"]["strength"], beam["min"]["strength"])
        mass = sm8["raster_g"]
        res["recommended"] = {
            "name": f"H1-G{a:g}", "alpha": a, "added_g": sm8["added_g"], "body_raster_g": mass,
            "fatigue_min_sim": fmin, "fatigue_fine": fine["min"]["fatigue"], "fatigue_fine_sm8": sm8["min"]["fatigue"],
            "fatigue_beam": beam["min"]["fatigue"], "fatigue_cinch_cycled": cyc["min"]["fatigue"],
            "strength_min": smin, "creep_min": min(sm8["min"]["creep"], fine["min"]["creep"], beam["min"]["creep"]),
            "per_kit": {"fine_sm8": per_kit(sm8), "fine": per_kit(fine), "beam": per_kit(beam), "cyc": per_kit(cyc)},
            "buckling_min_sim": min(sm8["buckling_min"], fine["buckling_min"]), "buckling_min_beam": beam["buckling_min"],
            "joint_sim": [sm8.get("joint_strength"), sm8.get("joint_fatigue")],
            "joint_beam": [beam.get("joint_strength"), beam.get("joint_fatigue")],
            "ca1_flip": PAHT_FAT / fmin, "ca1_flip_beam": PAHT_FAT / beam["min"]["fatigue"],
            "print_h": PRINT_H * mass / BASE_RASTER_G, "passes": bool(fmin >= FAT_REQ and smin >= STR_REQ),
            "lumbar_p99": sm8["top_regions"]["lumbar struts / pan"]["fatigue_p99_region"],
            "added_by_region": added_by_region(a)}
        full = _load("grow_a1.fine_sm8.cyc")
        if full:
            res["recommended"]["full_step_cyc"] = {"added_g": full["added_g"], "fatigue": full["min"]["fatigue"]}
    res["ca1_h1"] = {"sim_fine_sm8": PAHT_FAT / res["baseline"]["fine_sm8"]["min"]["fatigue"],
                     "beam": PAHT_FAT / res["baseline"]["beam"]["min"]["fatigue"]}
    return res


PRINT_H = 27.0            # frame_h1.md section 7: H1 body print time about 27 h on the H2S (both halves)
BASE_RASTER_G = 757.7     # H1 body raster mass (frame_h1 / ledger basis), the 27 h reference
# ASSUMPTION PRINT_TIME: print time scales with printed mass (same walls / infill rule as H1)


def added_by_region(alpha: float) -> dict:
    from . import crown_diet as CD
    from . import frame_h1 as H1
    c = H1.base()
    add = grown_solid(alpha_shift(alpha)) & ~CD._h1_solid()
    cnt = Counter(region(p) for p in c["cen"][add])
    lower = int((c["cen"][add][:, 2] < 234.0).sum())
    out = {k: round(v * H1.H ** 3 * 1.06e-3, 1) for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])}
    out["_lower_half_share"] = round(lower / max(int(add.sum()), 1), 3)
    return out


def top_voxels(name: str, solid: np.ndarray, weights=None) -> dict:
    """Centres of the 1 % most-utilised voxels of the governing set (kit L, 23 in, meat, fine_sm8, static carry) on
    ``solid``; cached as OUT/top_<name>.npz."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    p = OUT / f"top_{name}.npz"
    if not p.exists():
        sets = [s for s in build_sets("a_L", "fine_sm8") if s.torso == 23.0 and s.key.startswith("S_meat")]
        f = solve_fields_w(H1.base()["dom"], solid, sets, weights)
        k = next(i for i, mt in enumerate(f["meta"]) if mt["case"] == "static_carry")
        fi = D.fi_material(f["stress"][k].astype(float), D.MATERIALS[H1.MAT])
        ex = f["ex"][f["meta"][k]["scenario"]]
        top = (~ex) & (fi >= np.percentile(fi[~ex], 99))
        np.savez_compressed(p, xyz=f["cen"][top], fi=fi[top])
    z = np.load(p)
    return {"xyz": z["xyz"], "fi": z["fi"]}


REG_COLORS = {"lumbar struts / pan": "#2a78d6", "hip-pivot boss": "#eb6834", "stay sleeve z 160-240": "#1baf7a",
              "stay below the sleeve": "#eda100", "stay sleeve z 240-470": "#e87ba4", "stay top z 470-544": "#6250d6",
              "inboard branch": "#008300", "mid bar / upper bar": "#e34948", "stay foot": "#52514e"}


def _body_views(ax2, solid, c, alpha=0.06):
    cen = c["cen"][solid]
    sub = cen[:: 3]
    ax2[0].scatter(sub[:, 0], sub[:, 2], s=1, c="#b9b8b3", alpha=alpha * 4, lw=0)
    ax2[1].scatter(sub[:, 1], sub[:, 2], s=1, c="#b9b8b3", alpha=alpha * 4, lw=0)
    for a, xl in zip(ax2, ("x mm (wearer's right +)", "y mm (aft, toward the bag +)")):
        a.set_aspect("equal")
        a.set_xlabel(xl, fontsize=10)
        a.set_ylabel("z mm", fontsize=10)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.tick_params(labelsize=9)


def plot_location(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import crown_diet as CD
    from . import frame_h1 as H1
    c = H1.base()
    s0 = CD._h1_solid()
    tv = top_voxels("h1", s0)
    fig, ax = plt.subplots(1, 2, figsize=(11, 8.2), gridspec_kw={"width_ratios": [2.2, 1]}, facecolor="#fcfcfb")
    _body_views(ax, s0, c)
    regs = np.array([region(p) for p in tv["xyz"]])
    shares = res["location"]["fine_sm8"]
    for rg, col in REG_COLORS.items():
        m = regs == rg
        if not m.any():
            continue
        lab = f"{rg}: {100 * shares.get(rg, {}).get('share_top', 0):.0f} %"
        ax[0].scatter(tv["xyz"][m, 0], tv["xyz"][m, 2], s=7, c=col, lw=0, label=lab)
        ax[1].scatter(tv["xyz"][m, 1], tv["xyz"][m, 2], s=7, c=col, lw=0)
    ax[0].axhspan(240, 544, xmin=0, xmax=1, color="#cde2fb", alpha=0.25, lw=0)
    ax[0].text(0, 395, "crown bore z 240-544:\nalmost none of the top 1 %", ha="center", fontsize=10, color="#0b0b0b")
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=9.5, frameon=False, markerscale=2.5)
    rep = res["reproduce"]
    fig.suptitle(f"BL-024: where H1's fatigue margin comes from (23 in meat, kit L, sim fine_sm8)\n"
                 f"The 1 % most-utilised voxels set the FI99 margin ({res['baseline']['fine_sm8']['min']['fatigue']:.3f};"
                 f" BL-021 basis {rep['fatigue']:.3f}). They sit low, not at the crown bore.", fontsize=12, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=90, facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(path)


def plot_added(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import crown_diet as CD
    from . import frame_h1 as H1
    rc = res["recommended"]
    c = H1.base()
    s0 = CD._h1_solid()
    add = grown_solid(alpha_shift(rc["alpha"])) & ~s0
    fig, ax = plt.subplots(1, 2, figsize=(11, 8.2), gridspec_kw={"width_ratios": [2.2, 1]}, facecolor="#fcfcfb")
    _body_views(ax, s0, c)
    p = c["cen"][add]
    ax[0].scatter(p[:, 0], p[:, 2], s=6, c="#eb6834", lw=0, label=f"added PAHT-CF, +{rc['added_g']:.1f} g per frame")
    ax[1].scatter(p[:, 1], p[:, 2], s=6, c="#eb6834", lw=0)
    ax[0].axhline(234, color="#52514e", lw=1, ls="--")
    ax[0].text(150, 238, "z 234 split", fontsize=9, ha="right", color="#52514e")
    ab = rc["added_by_region"]
    txt = "\n".join(f"{k}: {v:.1f} g" for k, v in ab.items() if not k.startswith("_"))
    fig.text(0.53, 0.55, "Added per region:\n" + txt, fontsize=9.5, va="center", color="#0b0b0b")
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=10, frameon=False, markerscale=2.5)
    fig.suptitle(f"BL-024 recommended body {rc['name']}: H1 + grow-only offset where the sim loads need it\n"
                 f"Fatigue {rc['fatigue_min_sim']:.3f} on the sim loads (all kits), strength {rc['strength_min']:.2f}, "
                 f"{100 * ab['_lower_half_share']:.0f} % of the new material in the lower print half",
                 fontsize=12, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=90, facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(path)


def plot_trials(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tr = res["trials"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 6.8), gridspec_kw={"width_ratios": [1.35, 1]}, facecolor="#fcfcfb")
    col = {"-": "#52514e", "bore": "#2a78d6", "path": "#eb6834"}
    y = np.arange(len(tr))[::-1]
    for yi, t in zip(y, tr):
        ax[0].barh(yi, t["fatigue"], height=0.55, color=col[t["kind"]])
        ax[0].text(t["fatigue"] + 0.01, yi, f"{t['fatigue']:.3f}  (+{t['added_g']:.0f} g)", va="center", fontsize=9.5,
                   color="#0b0b0b")
    ax[0].set_yticks(y, [t["label"] for t in tr], fontsize=9.5)
    ax[0].axvline(FAT_REQ, color="#0b0b0b", lw=1.2, ls="--")
    ax[0].axvline(1.0, color="#52514e", lw=0.8, ls=":")
    ax[0].text(FAT_REQ, len(tr) - 0.3, " goal 1.15", fontsize=9.5)
    ax[0].set_xlim(0.8, 1.55)
    ax[0].set_xlabel("min body fatigue margin, every kit and setting (sim fine_sm8, cinch static)", fontsize=10)
    ax[0].set_title("Options tried", fontsize=12, loc="left")
    # per kit: H1 vs recommended on every basis
    rc = res.get("recommended")
    kits = ("a_S", "a_M", "a_L")
    bases = [("fine_sm8", "sim fine_sm8"), ("fine", "sim fine (BL-021)"), ("beam", "beam rev C"), ("cyc", "sim, cinch cycled")]
    h1b = {"fine_sm8": res["baseline"]["fine_sm8"]["per_kit"], "fine": res["baseline"]["fine"]["per_kit"],
           "beam": res["baseline"]["beam"]["per_kit"], "cyc": res["baseline"]["fine_sm8_cyc"]["per_kit"]}
    cols = ("#2a78d6", "#1baf7a", "#eda100", "#e87ba4")
    for i, ((b, lab), cc) in enumerate(zip(bases, cols)):
        xs = np.arange(3) + (i - 1.5) * 0.18
        ax[1].scatter(xs, [h1b[b][k]["fatigue"] for k in kits], s=40, facecolors="none", edgecolors=cc, lw=1.5)
        if rc:
            ax[1].scatter(xs, [rc["per_kit"][b][k]["fatigue"] for k in kits], s=46, c=cc, label=lab)
            for x0, k in zip(xs, kits):
                ax[1].plot([x0, x0], [h1b[b][k]["fatigue"], rc["per_kit"][b][k]["fatigue"]], color=cc, lw=1)
    ax[1].axhline(FAT_REQ, color="#0b0b0b", lw=1.2, ls="--")
    ax[1].axhline(1.0, color="#52514e", lw=0.8, ls=":")
    ax[1].set_xticks(range(3), ["kit S", "kit M", "kit L"])
    ax[1].set_ylabel("body fatigue margin (worst setting)", fontsize=10)
    ax[1].set_title("Per kit: H1 (open) -> recommended (filled)", fontsize=12, loc="left")
    ax[1].legend(fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2)
    for a in ax:
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.suptitle("BL-024: bore-side changes do not reach 1.15; adding PAHT-CF low on the body does", fontsize=13,
                 x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=90, facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(path)


def footprint(solid: np.ndarray) -> dict:
    """Lay-flat footprint of the two print halves from the voxels (frame y -> print z, as frame_h1.lay_flat), to
    compare with H1's on the H2S (340 x 320 x 340 mm)."""
    from . import frame_h1 as H1
    cen = H1.base()["cen"][solid]
    out = {}
    for nm, m in (("lower", cen[:, 2] < 234.0), ("upper", cen[:, 2] >= 234.0)):
        p = cen[m]
        ext = p.max(0) - p.min(0) + H1.H
        out[nm] = [round(float(ext[0]), 1), round(float(ext[2]), 1), round(float(ext[1]), 1)]
    out["fits_h2s"] = all(sorted(v)[::-1][0] <= 340 and sorted(v)[::-1][1] <= 340 and sorted(v)[::-1][2] <= 320
                          for k, v in out.items() if k in ("lower", "upper"))
    return out


def _f(v, n=3):
    return "-" if v is None else f"{v:.{n}f}"


def _g(g):
    return f"{g:.1f} g ({g / 28.3495:.2f} oz)"


def write_md(res: dict) -> str:
    rep, b, rc = res["reproduce"], res["baseline"], res.get("recommended")
    fz = res["forces"]
    L = []
    L.append("# BL-024 H1 body: sleeve and crown-leg seat redesign for fatigue margin on the sim loads\n")
    L.append("Generated by `python -m huntkit.gendesign.h1_sleeve` (data `h1_sleeve.json`). Date 2026-11-12. Rev C "
             "(HA-LS-1): fatigue 1e5 cycles 0 -> 1.6 g, strength at the factored load, PAHT-CF fatigue ratio 0.30 "
             "(ASSUMPTION PAHT_FAT). BL-024 goal: **fatigue >= 1.15 on the sim loads at every torso and crown kit, "
             "strength >= 1.4**, least added mass, printable on the H2S. Units N, mm, g (oz / lbf alongside).\n")
    L.append("## Summary\n")
    t_sm8 = b["fine_sm8"]["min"]["fatigue"]
    L.append(f"- **Reproduced BL-021:** H1 (one 15-23 in crown) on BL-021's fine sim loads, cinch static: fatigue "
             f"**{rep['fatigue']:.3f}** at 23 in, meat case, labelled \"{rep['bl021_label']}\" (peak voxel "
             f"x {rep['peak_xyz'][0]:.0f}, y {rep['peak_xyz'][1]:.0f}, z {rep['peak_xyz'][2]:.0f} mm).")
    loc = res["location"]["fine_sm8"]
    L.append(f"- **The label is misleading.** `region_label` calls every stay voxel above z 160 \"crown bore wall\". "
             f"The margin is a 99th percentile over the whole body; the 1 % most-utilised voxels of the governing set "
             f"sit in the **lumbar struts / pan ({100 * loc['lumbar struts / pan']['share_top']:.0f} %)**, the "
             f"**stay sleeve's bottom z 160-240 ({100 * loc['stay sleeve z 160-240']['share_top']:.0f} %, empty of leg "
             f"at 23 in)**, the hip-pivot boss ({100 * loc['hip-pivot boss']['share_top']:.0f} %) and the stay below the "
             f"sleeve ({100 * loc['stay below the sleeve']['share_top']:.0f} %); the crown bore z 240-544 holds "
             f"{100 * (loc['stay sleeve z 240-470']['share_top'] + loc['stay top z 470-544']['share_top']):.1f} %. "
             f"On the beam loads the same set is mostly the sleeve bottom; on the sim loads (hinge pins at z 60, hooks "
             f"at z 520, the meat push) it is the lower body.")
    L.append(f"- **New basis (BL-025, `{SM8}`, IM3 L {fz[SM8]['im3_L_n']:.1f} N):** H1 with the crown kits S/M/L "
             f"falls to **{t_sm8:.3f}** (BL-021 run {b['fine']['min']['fatigue']:.3f}); every kit is between "
             f"{min(v['fatigue'] for v in b['fine_sm8']['per_kit'].values()):.3f} and "
             f"{max(v['fatigue'] for v in b['fine_sm8']['per_kit'].values()):.3f} on the sim loads.")
    tr = {t["name"]: t for t in res["trials"]}
    lg, ln = tr.get("trial_leg127.fine_sm8"), tr.get("trial_liner_al.fine_sm8")
    L.append(f"- **Bore-side changes do not reach 1.15:** legs +127 mm (more leg in the stay) "
             f"{_f(lg and lg['fatigue'])} (+{lg['added_g']:.0f} g); a bonded 6061 liner z 160-544 "
             f"{_f(ln and ln['fatigue'])} (+{ln['added_g']:.0f} g), after which the lumbar struts hold "
             f"{100 * ln['top_shares'].get('lumbar struts / pan', 0):.0f} % of the top voxels.")
    if rc:
        L.append(f"- **Recommended {rc['name']}: H1 + a grow-only offset of the lower body (H1's own fully-stressed "
                 f"tool, scaled to the least mass that passes): +{_g(rc['added_g'])} per frame.** Fatigue on the sim "
                 f"loads **{rc['fatigue_min_sim']:.3f}** (fine_sm8 {rc['fatigue_fine_sm8']:.3f}, fine "
                 f"{rc['fatigue_fine']:.3f}), beam {rc['fatigue_beam']:.3f}, strength {rc['strength_min']:.2f}, creep "
                 f"{rc['creep_min']:.2f}. {100 * rc['added_by_region']['_lower_half_share']:.0f} % of the new material "
                 f"is in the lower print half. **Goal met on the governing basis (cinch static).**")
        L.append(f"- **CINCH_STATIC changes the answer.** If the meat-strap cinch cycles with the walking g, H1 is "
                 f"{b['fine_sm8_cyc']['min']['fatigue']:.3f} and {rc['name']} is **{rc['fatigue_cinch_cycled']:.3f}** "
                 f"(fails 1.0); the full grow step (+{rc['full_step_cyc']['added_g']:.1f} g) gives "
                 f"{rc['full_step_cyc']['fatigue']:.3f}. Nothing light passes that bound: MT-1 must settle it before R1.")
        L.append(f"- **CA-1 flip point:** {rc['name']} **{rc['ca1_flip']:.3f}** on the sim loads (beam "
                 f"{rc['ca1_flip_beam']:.3f}); H1 as released {res['ca1_h1']['sim_fine_sm8']:.3f} sim / "
                 f"{res['ca1_h1']['beam']:.3f} beam. CA-1 must show >= {rc['ca1_flip']:.3f} (<= 0.30 on record).")
        L.append(f"- **Also found (not part of this ticket, not fixed):** on the sim loads H1's branch / mid-bar "
                 f"Euler check (team A rule, margin >= 1) is **{b['fine_sm8']['buckling_min']:.2f}** (mid bar x -115..115, "
                 f"hipbelt-off abuse, 23 in meat; branch upper R 0.71, side-hill). BL-021 printed 0.43 without flagging "
                 f"it. Beam basis {b['beam']['buckling_min']:.2f}. {rc['name']} gives {rc['buckling_min_sim']:.2f} "
                 f"(the full grow step 0.67): the growth does not reach the mid bar. "
                 f"See section 7.")
    L.append("")
    L.append("## 1. Load bases\n")
    L.append("Frame-side 1 g forces rebuilt from the saved CORRIE F rev 1 node positions (BL-021 reader; contact on the "
             "kept stage, BL-025). Guys at x +/-52 (rev 1). Fill and meat are separate scenarios.\n")
    L.append("| run (meat) | IM3 R / L N (leg sum) | hinge R / L N | CG y / z mm | total kg |")
    L.append("|---|---|---|---|---|")
    for run, v in fz.items():
        L.append(f"| `{run}` | {v['im3_R_n']:.1f} / {v['im3_L_n']:.1f} ({v['im3_L_n'] / 4.448:.0f} lbf L) | "
                 f"{v['hinge_R_n']:.1f} / {v['hinge_L_n']:.1f} | {v['cg_mm'][1]:.1f} / {v['cg_mm'][2]:.1f} | {v['total_kg']:.2f} |")
    L.append(f"\nBases: **fine** = BL-021's (15 / 19 / 23 in `F_r1_PR*_fineFM`); **fine_sm8** = the same with the 23 in "
             f"meat case from `{SM8}` (DECISIONS 2026-11-12: the higher of the two fine 23 in runs; fill stays "
             f"`F_r1_PR23_fineFM`, the sm8 run has no fill case). Crown kits S 15-18, M 17.5-20.5, L 20-23 in with "
             f"today's 16 x 8 legs (crown_diet a_S / a_M / a_L); IM3 cheek 28 mm is a fairlead change outside the voxel "
             f"body's FI population (the fairlead zones are restored hard points). Settings between simulated torsos "
             f"use the nearest sim and the other neighbour (ASSUMPTION SIM_TORSO).\n")
    L.append("## 2. Reproduction and where the margin comes from\n")
    L.append("| body / basis | 15 in | 19 in | 23 in | min fatigue | strength | creep |")
    L.append("|---|---|---|---|---|---|---|")
    for k, lab in (("h1_fine", "H1 one crown, sim fine (BL-021 reproduced)"), ("h1_fine_sm8", "H1 one crown, sim fine_sm8")):
        ps = b[k]["per_setting"]
        vals = [next(v["fatigue"] for kk, v in ps.items() if kk.endswith(f"|{t}")) for t in (15, 19, 23)]
        L.append(f"| {lab} | {vals[0]:.3f} | {vals[1]:.3f} | {vals[2]:.3f} | **{b[k]['min']['fatigue']:.3f}** | "
                 f"{b[k]['min']['strength']:.2f} | {b[k]['min']['creep']:.2f} |")
    L.append("\nThe top 1 % of the governing static-carry set (23 in, meat), by region. `p99 region` = the region's own "
             "99th-percentile fatigue margin (a local measure, stricter than the body FI99; used to check that a change "
             "lowers stress rather than dilutes the population).\n")
    L.append("| region | share of top 1 %: sim fine | sim fine_sm8 | sim, cinch cycled | beam | p99 region (fine_sm8) |")
    L.append("|---|---|---|---|---|---|")
    for rg in REGIONS:
        row = [res["location"][k].get(rg, {}) for k in ("fine", "fine_sm8", "fine_cyc", "beam_kits")]
        if all(r.get("n_top", 0) == 0 for r in row):
            continue
        L.append(f"| {rg} | " + " | ".join(f"{100 * r.get('share_top', 0):.0f} %" for r in row) +
                 f" | {_f(row[1].get('fatigue_p99_region'))} |")
    L.append("\nWhy the bore-side fixes cannot work: at 23 in the leg bottom is at z 374, so the low sleeve "
             "(z 160-240) is empty of carbon in every kit's top setting, and the lumbar struts, pan and hip boss carry "
             "the sim's bag load (hinge pins at z 60, hooks at z 520, meat push) to the hip pivot whatever the crown "
             "does. BL-021's sleeve-wall trials helped only through the z 160-240 band.\n")
    L.append("## 3. Options tried (sim fine_sm8, cinch static, every kit setting)\n")
    L.append("| option | added g per frame | min fatigue | kit S / M / L | strength | lumbar p99 | buckling | top-1 % shares |")
    L.append("|---|---|---|---|---|---|---|---|")
    for t in res["trials"]:
        pk = t["per_kit"]
        sh = ", ".join(f"{k.split(' ')[0]} {100 * v:.0f}" for k, v in sorted(t["top_shares"].items(), key=lambda kv: -kv[1])[:3])
        L.append(f"| {t['label']} | {t['added_g']:+.1f} | **{t['fatigue']:.3f}** | "
                 f"{pk.get('a_S', 0):.3f} / {pk.get('a_M', 0):.3f} / {pk.get('a_L', 0):.3f} | {t['strength']:.2f} | "
                 f"{_f(t['lumbar_p99'])} | {t['buckling_min']:.2f} | {sh} |")
    L.append("\n- **Longer crown legs** (ticket idea: keep more leg in the stay): at the top setting of every kit the "
             "leg bottom only moves from z 374 to 247, still above the governing band; the extra leg stiffness draws "
             "load and the margin drops slightly. Rejected.")
    L.append("- **Bonded liner** (ASSUMPTION LINER): helps the z 160-240 band, nothing below it; +75 g for +0.10. A "
             "second bushing or a longer bushing seat changes only how the leg loads the bore above z 374, which is "
             "not in the governing population (0-2 %): not run separately for that reason. Rejected.")
    L.append("- **Moving the hot spot by where the bushing bears:** the bushing forces at 23 in static carry are "
             "50-95 N (factored); the governing population is not under them. No lever.")
    L.append("- **Load-path growth:** H1's own grow-only fully-stressed offset (frame_comp_d.offset_step, 6 mm "
             "max-filter, cube-root growth, at most 3 mm per step, keep-outs and passive voids re-imposed, "
             "frame_h1.assemble) from H1's shift, driven by the per-voxel utilisation of every kit setting on "
             "fine_sm8 at target 1.15 x 1.02. One step (+38.8 g) gives 1.33; the step is then scaled (alpha) to find "
             "the least mass that passes. The lumbar p99 rises with it, so the gain is a stress reduction, not "
             "dilution of the percentile.\n")
    if rc:
        L.append(f"## 4. Recommended body {rc['name']}, every rev C set, per kit\n")
        L.append(f"Body {_g(rc['body_raster_g'])} raster (H1 {_g(BASE_RASTER_G)}), **+{_g(rc['added_g'])}**. "
                 f"Where the material goes: " + ", ".join(f"{k} {v:.1f} g" for k, v in rc["added_by_region"].items()
                                                          if not k.startswith("_")) + ".\n")
        L.append("| kit | basis | settings (worst of nearest / other sim) | worst | H1 worst | strength | creep |")
        L.append("|---|---|---|---|---|---|---|")
        hb = {"fine_sm8": b["fine_sm8"]["per_kit"], "fine": b["fine"]["per_kit"], "beam": b["beam"]["per_kit"],
              "cyc": b["fine_sm8_cyc"]["per_kit"]}
        bl = {"fine_sm8": "sim fine_sm8 (governing)", "fine": "sim fine (BL-021 run)", "beam": "beam rev C",
              "cyc": "sim fine_sm8, cinch cycled (bound)"}
        for kit in ("a_S", "a_M", "a_L"):
            for bs in ("fine_sm8", "fine", "beam", "cyc"):
                v = rc["per_kit"][bs][kit]
                st = ", ".join(f"{t} in {f:.3f}" for t, f in sorted(v["settings"].items(), key=lambda kv: float(kv[0])))
                L.append(f"| {KIT_LABEL[kit]} | {bl[bs]} | {st} | **{v['fatigue']:.3f}** | {hb[bs][kit]['fatigue']:.3f} | "
                         f"{v['strength']:.2f} | {v['creep']:.2f} |")
        L.append(f"\nOther rev C checks on the same solves: z 234 joint strength / fatigue {_f(rc['joint_sim'][0], 2)} / "
                 f"{_f(rc['joint_sim'][1], 2)} sim, {_f(rc['joint_beam'][0], 2)} / {_f(rc['joint_beam'][1], 2)} beam "
                 f"(H1 {_f(b['fine_sm8']['joint'][0], 2)} / {_f(b['fine_sm8']['joint'][1], 2)} sim); branch / mid-bar "
                 f"buckling {rc['buckling_min_sim']:.2f} sim (H1 {b['fine_sm8']['buckling_min']:.2f}), "
                 f"{rc['buckling_min_beam']:.2f} beam (H1 {b['beam']['buckling_min']:.2f}).\n")
        fp = rc.get("footprint", {})
        L.append("## 5. Build\n")
        L.append(f"- Print: two halves as H1 (split z 234, laid flat, face down), PAHT-CF on the H2S. Voxel footprint "
                 f"lower {fp.get('lower')} mm, upper {fp.get('upper')} mm (x, z, thickness), H1 lower "
                 f"{fp.get('h1_lower')} / upper {fp.get('h1_upper')}; fits 340 x 320 x 340: **{fp.get('fits_h2s')}**.")
        L.append(f"- Print time about **{rc['print_h']:.1f} h** (H1 27 h; ASSUMPTION PRINT_TIME: scales with mass).")
        L.append("- No new hardware, no change to any interface: bores, bushing seats, pawl / rack, spreader clips, "
                 "IM fairleads (restored hard points; the IM3 cheek stays BL-021's 28 mm, whose envelope 562.3 N covers the "
                 "sm8 run's 561.8 N), back rails, pads and the z 234 joint bosses "
                 "are the H1 keep-outs and are re-imposed by `frame_h1.assemble`. Same build steps as "
                 "`print/frame_h1/README.md`.")
        L.append("- **Print files not updated** (task 4): the body passes the fatigue goal only with the cinch static, "
                 "and the sim-load buckling in section 7 is open. When both are settled: `frame_h1.print_mesh` / "
                 "`export_print` on `h1_sleeve.grown_solid(h1_sleeve.alpha_shift(" + f"{rc['alpha']:g}" + "))`.\n")
        L.append("## 6. CA-1 flip point\n")
        L.append("| body | fatigue (basis) | CA-1 flip ratio (0.30 / margin) |")
        L.append("|---|---|---|")
        L.append(f"| {rc['name']} (recommended) | {rc['fatigue_min_sim']:.3f} (sim, cinch static) | **{rc['ca1_flip']:.3f}** |")
        L.append(f"| {rc['name']} | {rc['fatigue_beam']:.3f} (beam) | {rc['ca1_flip_beam']:.3f} |")
        L.append(f"| {rc['name']} | {rc['fatigue_cinch_cycled']:.3f} (sim, cinch cycled) | {PAHT_FAT / rc['fatigue_cinch_cycled']:.3f} |")
        L.append(f"| H1 as released | {b['fine_sm8']['min']['fatigue']:.3f} (sim fine_sm8) | {res['ca1_h1']['sim_fine_sm8']:.3f} |")
        L.append(f"| H1 as released | {b['beam']['min']['fatigue']:.3f} (beam) | {res['ca1_h1']['beam']:.3f} |\n")
    L.append("## 7. Found, not fixed: branch / mid-bar buckling on the sim loads\n")
    L.append(f"Team A's Euler rule (K 1, E x 0.6 hot x 0.7 creep, P_cr >= 1.5 x factored compression), evaluated on "
             f"the same solves: H1 **{b['fine_sm8']['buckling_min']:.2f}** on the sim loads (mid bar x -115..115, "
             f"A 72 mm2, L 230, P_cr 125 N against 188 N factored, hipbelt-off abuse at 23 in meat; branch upper R "
             f"0.71, side-hill 23 in meat), **{b['beam']['buckling_min']:.2f}** on the beam loads. BL-021 printed 0.43 "
             f"and did not flag it. Hand sizing (P_cr ~ A^2): the mid bar needs A >= 72 / sqrt(0.44) = 108 mm2 "
             f"(r_eq 5.9 mm, about +9 g) and the upper branches about 128 mm2 (+8 g a pair), before the stiffer bars "
             f"draw more load. Not part of BL-024; it needs its own ticket and a check that the sim's lateral load on "
             f"the stays (spreader contact net, IM strap pulls) is real.\n")
    L.append("## 8. Assumptions\n")
    for k, (txt, test) in res["assumptions"].items():
        L.append(f"- ASSUMPTION {k}: {txt} Settled by: {test}")
    L.append("- ASSUMPTION PRINT_TIME: print time scales with printed mass from H1's 27 h. Settled by: slicer estimate "
             "of the new halves.")
    L.append("- ASSUMPTION MESH: the body grid is H1's 2 mm voxel (the FI99 rule and KEEP 1.02 are calibrated on it); "
             "no finer body grid was run. Settled by: a 1.0 mm sub-model of the lumbar struts (or T1 strain gauges).\n")
    L.append("## 9. Screens\n")
    for s in res.get("screens", []):
        L.append(f"- `{Path(s).relative_to(REPO)}`")
    return "\n".join(L) + "\n"


def run_all(log=print):
    """Every solve behind the report (each cached in OUT; about 45 min on 2 cores from scratch)."""
    from . import crown_diet as CD
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    s0 = CD._h1_solid()
    for basis in ("fine", "fine_sm8"):                         # reproduction (one crown) + new basis
        for cyc in (False, True):
            body_eval(f"h1__h1.{basis}{'.cyc' if cyc else ''}", s0, build_sets("h1", basis, cycled=cyc),
                      keep_util=not cyc, log=log)
    body_eval("h1__kits.fine_sm8", s0, kit_sets("fine_sm8"), log=log)
    body_eval("h1__kits.fine", s0, kit_sets("fine"), log=log)
    body_eval("h1__kits.fine_sm8.cyc", s0, kit_sets("fine_sm8", cycled=True), log=log)
    body_eval("h1__kits.beam", s0, kit_sets("beam"), log=log)
    body_eval("trial_leg127.fine_sm8", s0, kit_sets("fine_sm8", leg_extra=LEG_EXTRA_MM),
              extra={"added_g": 2 * LEG_EXTRA_MM * 0.1025}, log=log)    # 0.1025 g/mm: crown_diet leg table
    w, ring, add, wl = liner_weights(s0)
    body_eval("trial_liner_al.fine_sm8", s0, kit_sets("fine_sm8"), weights=w, excl=ring,
              extra={"added_g": add, "E_weight": wl}, log=log)
    grow_study("grow", iters=5, log=log)
    for a in (0.3, 0.45, 0.55, 0.6):
        alpha_eval(a, log=log, keep_util=(a == 0.55))
    a = 0.55
    solid = grown_solid(alpha_shift(a))
    ex = {"added_g": D.mass_g(solid, H1.H, 1060.0) - D.mass_g(s0, H1.H, 1060.0), "alpha": a}
    body_eval(f"grow_a{a:g}.fine", solid, kit_sets("fine"), extra=ex, log=log)
    body_eval(f"grow_a{a:g}.fine_sm8.cyc", solid, kit_sets("fine_sm8", cycled=True), extra=ex, log=log)
    body_eval(f"grow_a{a:g}.beam", solid, kit_sets("beam"), extra=ex, log=log)
    s1 = grown_solid(alpha_shift(1.0))
    body_eval("grow_a1.fine_sm8.cyc", s1, kit_sets("fine_sm8", cycled=True),
              extra={"added_g": D.mass_g(s1, H1.H, 1060.0) - D.mass_g(s0, H1.H, 1060.0), "alpha": 1.0}, log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true", help="run any missing body solves (long)")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    if a.run:
        run_all()
    res = compute()
    from . import crown_diet as CD
    if res.get("recommended"):
        fp = footprint(grown_solid(alpha_shift(res["recommended"]["alpha"])))
        f0 = footprint(CD._h1_solid())
        fp.update(h1_lower=f0["lower"], h1_upper=f0["upper"])
        res["recommended"]["footprint"] = fp
    if not a.no_plots:
        SCREENS.mkdir(parents=True, exist_ok=True)
        res["screens"] = [plot_location(res, SCREENS / f"{SHOT}1.png"), plot_trials(res, SCREENS / f"{SHOT}2.png")]
        if res.get("recommended"):
            res["screens"].append(plot_added(res, SCREENS / f"{SHOT}3.png"))
    RESULTS.write_text(json.dumps(res, indent=1, default=_np_default))
    DOC.write_text(write_md(res))
    print(DOC)


if __name__ == "__main__":
    main()
