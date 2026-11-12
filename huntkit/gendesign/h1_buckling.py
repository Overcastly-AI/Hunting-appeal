"""BL-027: H1 branch / mid-bar Euler buckling on the CORRIE F cloth-sim loads.

    python -m huntkit.gendesign.h1_buckling --run        # every solve this ticket needs (cached in outputs/h1_buckling)
    python -m huntkit.gendesign.h1_buckling              # cached results -> md / json / png

What it does (ticket docs/backlog/BL-027-h1-buckling-simloads.md):
1. Is the load real? For the governing sim sets and the governing beam sets, the factored compression in the mid
   bar and the upper branches is split, exactly (linear superposition on the same voxel solve), into the load groups
   that make it: the sim's hinge-pin and IM3-hook lateral pulls, the rest of the sim bag force, BL-021's force /
   moment closure at the payload CG (under-strap pins + hook/hinge couple), the meat-strap cinch loop, the beam-case
   remainder (side-hill tilt) and the crown interface (bushings + pawl). The closure leftovers (force, all three
   moment components) and the hinge / hook lateral pulls of every CORRIE F run (coarse, fine, rev 0 / rev 1) are
   listed so the reader can see whether the sideways load is a mapping artefact or in the sim itself.
2. Sizing: H1-G0.55 (BL-024) plus a grow-only offset of the mid bar and the upper branches (H1's own SDF shift,
   frame_h1.assemble re-imposes every keep-out), stepped until team A's Euler rule (frame_h1.buckling) is >= 1.0 on
   the governing sim case and on the beam; every rev C body check re-run on the chosen body (fatigue on fine_sm8 /
   fine / beam, strength, creep, the z 234 joint, keep-outs, mass).
3. frame_cg_recheck.region_label names the lower sleeve band (z 160-240) for what it is; the new
   frame_cg_recheck.governing_region names the region that holds the governing (top 1 %) voxels.
4. If it passes: H1 print files from the chosen body (frame_h1.print_mesh / export_print), the 28 mm IM3 cheek,
   one closed shell per flat half.

Shared modules are not edited except frame_cg_recheck (ticket task 3). Units N, mm, g.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import pickle
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_buckling.json"
DOC = ANALYSIS / "h1_buckling.md"
OUT = REPO / "outputs" / "h1_buckling"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261112_BL027_"

BUCKLE_REQ = 1.0            # team A rule: P_cr >= 1.5 x factored compression <=> margin >= 1
BUCKLE_GOAL_ABUSE = 1.2     # ticket: >= 1.2 on the hipbelt-off abuse case if cheap
FAT_REQ = 1.15              # BL-024 goal kept (ticket: keep fatigue >= 1.15)
STR_REQ = 1.4
ALPHA = 0.55                # BL-024 adopted body H1-G0.55
MEMBERS = ("mid bar (x -115..115) all", "branch upper (z 330-495) L", "branch upper (z 330-495) R",
           "branch lower (z 165-330) L", "branch lower (z 165-330) R")

ASSUMPTIONS = {
    "SIM_BODY": ("As BL-021 / BL-024: the sim's 1 g frame-side forces scaled by g x load / 68 kg, closed on the payload "
                 "weight at the sim CG (force -> 4 under-strap pins, sagittal moment -> hook / hinge couple).",
                 "T9 loaded CG + frame strain gauges at the stays, the mid bar and the lumbar struts in the T1 carry "
                 "test."),
    "FLOOR_SPAN": ("The hinge-pin lateral pull (the bag floor spanning pin to pin like a hammock, 62-208 N a side at "
                   "1 g in the meat case over every converged CORRIE F run) is taken as real: the sim pins the bag at both "
                   "hinge nodes, and the real bag floor is cut to the same width.",
                   "T2 meat test: a load pin (or strain-gauged hinge pin) at one stay foot, lateral component, "
                   "23 in torso, 68 kg meat."),
    "EULER_RULE": ("Team A's Euler rule unchanged (frame_comp_A.member_buckling: pinned-pinned K 1, the member's "
                   "voxel area at the cut as a solid round section, E_xy x 0.6 hot x 0.7 creep, margin = P_cr / "
                   "(1.5 x factored compression)). Stays and the mid-bar junctions give some end fixity, so K 1 is "
                   "conservative.",
                   "Optional: a linear eigenvalue (buckling) run of the voxel body under the governing set, or a "
                   "printed-frame side-squeeze test (T1 rig, 2 x 1.5 x the factored load at the stay feet)."),
    "PAHT_FAT": ("PAHT-CF fatigue_1e5_ratio 0.30 (record ASSUMPTION).", "CA-1 coupon test."),
    "CINCH_STATIC": ("As BL-021 / BL-024: the meat-strap cinch is a static preload (fatigue on the static-carry set "
                     "without the cinch loop).", "MT-1 strap tension readout over a 10 min loaded walk."),
    "MESH": ("2 mm voxel grid (the FI99 rule, KEEP 1.02 and the cut areas are calibrated on it); a member area is a "
             "whole number of 4 mm2 voxel faces, so growth is judged on the cut area actually rastered.",
             "Slicer cross-section of the printed mid bar / upper branches against the rastered areas."),
}


def _np_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _cache(name: str, fn, refresh: bool = False):
    p = OUT / name
    if p.exists() and not refresh:
        return pickle.loads(p.read_bytes())
    v = fn()
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps(v))
    return v


# ======================================================================================= member forces
def member_masks(fields: dict) -> dict:
    """The cut layers of team A's Euler rule (frame_h1.buckling): member -> (mask over fields' solid elements, axis,
    area mm2, length mm, P_cr N)."""
    from . import frame_comp_A as A
    from . import frame_h1 as H1
    m = A.MATS["paht_rec"]
    E = m.E_xy * m.E_hot * 0.7
    c = H1.base()
    idx, cen = fields["idx"], fields["cen"]
    grp = c["grp"][idx]
    out = {}
    for name, (gname, ax, cc, L) in A.BUCKLE_CUTS.items():
        lay = (grp == A.GROUPS.index(gname)) & (np.abs(cen[:, ax] - (cc + H1.H / 2)) <= H1.H / 2 + 1e-6)
        sides = {"all": lay} if ax == 0 else {"L": lay & (cen[:, 0] < 0), "R": lay & (cen[:, 0] > 0)}
        for sd, msk in sides.items():
            A_ = float(msk.sum() * H1.H * H1.H)
            r = math.sqrt(A_ / math.pi)
            out[f"{name} {sd}"] = (msk, ax, A_, L, math.pi ** 2 * E * (math.pi * r ** 4 / 4) / L ** 2)
    return out


def member_axial(fields: dict) -> dict:
    """member -> {"N": factored axial force per solved set (N, + tension), "A", "L", "Pcr"}; same sum as
    frame_h1.buckling (stress normal to the cut x voxel face area)."""
    from . import frame_h1 as H1
    out = {}
    for nm, (msk, ax, A_, L, pcr) in member_masks(fields).items():
        N = np.array([float(S[msk, ax].astype(float).sum() * H1.H * H1.H) for S in fields["stress"]])
        out[nm] = {"N": N, "A_mm2": A_, "L_mm": L, "Pcr_n": pcr}
    return out


def by_case(ax: dict, meta: list) -> dict:
    """Least Euler margin per load case (over members and sets of that case) and the member that sets it."""
    out = {}
    for case in sorted({mt["case"] for mt in meta}):
        sel = np.array([mt["case"] == case for mt in meta])
        sub = {k: dict(v, N=np.asarray(v["N"])[sel]) for k, v in ax.items()}
        mg = margins_from_axial(sub, [mt for mt, s_ in zip(meta, sel) if s_])
        ok = {k: v for k, v in mg.items() if v["margin"] is not None}
        if ok:
            k = min(ok, key=lambda k_: ok[k_]["margin"])
            out[case] = {"margin": ok[k]["margin"], "member": k, "set": ok[k]["set"]}
    return out


def mirrored(ax: dict) -> dict:
    """The sim loads are not left / right symmetric and a side-hill can lean either way: each branch's P_cr against
    the worst compression of its mirror partner (the body is symmetric up to the 2 mm raster)."""
    out = {}
    for lev in ("branch lower (z 165-330)", "branch upper (z 330-495)"):
        L, R_ = ax[f"{lev} L"], ax[f"{lev} R"]
        pl, pr = -float(np.min(L["N"])), -float(np.min(R_["N"]))
        m = []
        if pr > 0:
            m.append(L["Pcr_n"] / (1.5 * pr))
        if pl > 0:
            m.append(R_["Pcr_n"] / (1.5 * pl))
        out[lev] = round(min(m), 3) if m else None
    return out


def margins_from_axial(ax: dict, meta: list) -> dict:
    """member -> margin, governing set, compression (frame_h1.buckling's rule, from member_axial)."""
    out = {}
    for nm, v in ax.items():
        k = int(np.argmin(v["N"]))
        P = -float(v["N"][k])
        out[nm] = {"A_mm2": v["A_mm2"], "Pcr_n": round(v["Pcr_n"], 1), "P_factored_n": round(P, 1),
                   "set": meta[k]["set"], "margin": round(v["Pcr_n"] / (1.5 * P), 3) if P > 0 else None}
    return out


# ======================================================================================= task 1: where the load comes from
def _record_build(kit: str, basis: str, alt: bool = False) -> tuple:
    """Rebuild h1_sleeve.build_sets(kit, basis) in OUT/rebuild (h1_sleeve's cache untouched) while recording what
    BL-021's mapping (im3_body_simloads.sim_nodal_1g) puts on each beam node: the sim part (g-scaled), the cinch
    part (fixed), the closure (pins + couple). Returns (sets, records keyed '<run>|<case>')."""
    from . import h1_sleeve as S
    from . import im3_body_simloads as B
    rec: dict = {}
    orig = B.sim_nodal_1g

    def wrapped(model, ff, total_kg):
        gp, fx, resid = orig(model, ff, total_kg)
        last = copy.deepcopy(B.sim_nodal_1g.last)   # sim_nodal_1g sets .last on the module name (= wrapped)
        nodes = model["nodes"]
        pins = [B._stay_node(model, sd, z) for z in B.US_Z for sd in (1.0, -1.0)]
        hi = [B._stay_node(model, sd, B.EYE_STATION) for sd in (1.0, -1.0)]
        lo = [B._stay_node(model, sd, 60.0) for sd in (1.0, -1.0)]
        clo: dict = {}
        for n in pins:
            clo[n] = clo.get(n, np.zeros(3)) + np.asarray(last["resid_force_n"]) / len(pins)
        for n in hi:
            clo[n] = clo.get(n, np.zeros(3)) + np.array([0.0, last["couple_n"] / 2.0, 0.0])
        for n in lo:
            clo[n] = clo.get(n, np.zeros(3)) + np.array([0.0, -last["couple_n"] / 2.0, 0.0])
        rec[f"{ff['run']}|{ff['case']}"] = {
            "gp": {n: np.asarray(v, float) for n, v in gp.items()}, "fx": {n: np.asarray(v, float) for n, v in fx.items()},
            "closure": clo, "xyz": {n: np.asarray(nodes[n], float) for n in set(gp) | set(fx) | set(clo)},
            "last": last, "total_kg": total_kg}
        return gp, fx, resid
    wrapped.last = None
    o_out = S.OUT
    S.OUT = OUT / "rebuild"
    B.sim_nodal_1g = wrapped
    try:
        p = S.OUT / "sets" / f"{kit}.{basis}{'.alt' if alt else ''}.pkl"
        if p.exists():
            p.unlink()                         # force the build so the mapping is recorded
        sets = S.build_sets(kit, basis, alt=alt)
    finally:
        S.OUT = o_out
        B.sim_nodal_1g = orig
    return sets, rec


def rebuilt(kit: str, basis: str, alt: bool = False) -> tuple:
    return _cache(f"rebuild_{kit}.{basis}{'.alt' if alt else ''}.pkl", lambda: _record_build(kit, basis, alt))


GROUPS = ("hinge-pin lateral (sim, x at z 60)", "IM3-hook lateral (sim, x at z 520)", "other sim lateral (x)",
          "sim bag force y / z", "closure: under-strap pins + hook / hinge couple", "meat-strap cinch loop",
          "beam-case part x (tilt, downhill bias, beam bag)", "beam-case part y / z and body side",
          "crown interface (bushings + pawl)")
GROUP_SHORT = ("hinge squeeze", "hook squeeze", "other sim x", "sim y/z", "closure", "cinch", "beam x", "beam y/z",
               "crown")


def _tilt(case: str) -> float:
    from huntkit.fea import load_standard as LS
    for c in LS.ls1_envelope("C")["crown_bar"]:
        if c.name == case:
            return float(c.lateral_tilt_deg)
    return 0.0


def set_run(key: str, basis: str) -> tuple:
    """('<run>|<case>', alt) of a sim set key such as 'S_meat@a_L_fine_sm8_alt_20:hipbelt_off_abuse|20'."""
    from . import h1_sleeve as S
    tag, rest = key.split(":", 1)
    sc = tag.split("@")[0]
    case = {"S_fill": "fill", "S_meat": "meat"}.get(sc)
    if case is None:
        return None, False
    alt = "_alt_" in tag
    t = float(rest.split("|")[-1])
    st = S.sim_torso(t, alt)
    return f"{S.BASES[basis][st][case]}|{case}", alt


def split_set(ls, rec: dict | None, basis: str) -> dict:
    """Split one LoadSet into the GROUPS (each a LoadSet with the same factor); the groups add up to ``ls``
    exactly. ``rec`` = the recorded mapping of the set's sim run (None for a beam set)."""
    from huntkit.gendesign.frame_topopt import LoadSet
    parts = {g: [] for g in GROUPS}
    s = ls.g * ls.kg / 68.0
    ct = math.cos(math.radians(_tilt(ls.case)))
    cyc = ".cyc" in ls.key or "_cyc_" in ls.key
    for p, v, side in ls.items:
        v = np.asarray(v, float)
        p = np.asarray(p, float)
        sim = np.zeros(3)
        clo = np.zeros(3)
        fix = np.zeros(3)
        if rec is not None and side != "body":
            for n, xyz in rec["xyz"].items():
                if np.linalg.norm(xyz - p) < 1e-6:
                    sim = sim + s * ct * rec["gp"].get(n, np.zeros(3))
                    clo = clo + s * ct * rec["closure"].get(n, np.zeros(3))
                    # BL-021 / BL-024 (CINCH_STATIC): the cinch loop is left out of the static-carry set unless the
                    # cinch is cycled (h1_sleeve._env passes sim_ff[2] = not cycled)
                    if cyc or ls.case != "static_carry":
                        fix = fix + rec["fx"].get(n, np.zeros(3))
        body = sim - clo
        rest = v.copy()
        rest[:3] -= sim + fix
        ex = np.array([1.0, 0.0, 0.0])
        lat = body * ex
        g_lat = GROUPS[0] if p[2] <= 75.0 else (GROUPS[1] if p[2] >= 500.0 else GROUPS[2])
        for gname, f3 in ((g_lat, lat), (GROUPS[3], body - lat), (GROUPS[4], clo), (GROUPS[5], fix)):
            if np.abs(f3).max() > 0:
                parts[gname].append((p, np.r_[f3, 0.0, 0.0, 0.0], side))
        if side == "body":
            parts[GROUPS[7]].append((p, rest, side))
        else:
            rx = np.zeros(6)
            rx[0] = rest[0]
            ryz = rest - rx
            if np.abs(rx).max() > 0:
                parts[GROUPS[6]].append((p, rx, side))
            if np.abs(ryz).max() > 0:
                parts[GROUPS[7]].append((p, ryz, side))
    # sensitivity (not part of the sum): the cinch loop's push on the inboard face nodes (|x| < 100: mid bar, branch
    # and pan nodes) carried by the spreader to the two stays instead, by the lever rule (force and moment kept)
    stay_p = [np.asarray(p, float) for p, _, sd in ls.items if sd != "body" and abs(abs(p[0]) - 115.0) < 1.0]
    moved = []
    for p, v, side in parts[GROUPS[5]]:
        if abs(p[0]) >= 100.0 or not stay_p:
            moved.append((p, v, side))
            continue
        for sx in (1.0, -1.0):
            cand = [q for q in stay_p if q[0] * sx > 0]
            q = min(cand, key=lambda q_: abs(q_[2] - p[2]))
            w = (115.0 + sx * p[0]) / 230.0
            moved.append((q, w * np.asarray(v, float), side))
    out = {}
    for i, gname in enumerate(GROUPS + ("cinch via the stays (sensitivity)",)):
        if i == len(GROUPS):
            out[gname] = LoadSet(key=f"G{i}{ls.key.split(':')[0]}:{ls.key.split(':', 1)[1]}#{i}", case=ls.case,
                                 torso=ls.torso, factor=ls.factor, g=ls.g, kg=ls.kg, items=moved, bushings=[],
                                 pawl=np.zeros(3))
            continue
        crown = gname == GROUPS[8]
        out[gname] = LoadSet(key=f"G{i}{ls.key.split(':')[0]}:{ls.key.split(':', 1)[1]}#{i}", case=ls.case,
                             torso=ls.torso, factor=ls.factor, g=ls.g, kg=ls.kg,
                             items=[] if crown else parts[gname], bushings=list(ls.bushings) if crown else [],
                             pawl=np.asarray(ls.pawl, float).copy() if crown else np.zeros(3))
    return out


def decompose(solid: np.ndarray, targets: list, basis_of: dict, recs: dict) -> dict:
    """Member axial force of each target set and of each of its load groups (one factorization). ``targets``: the
    LoadSets; ``basis_of[key]`` = sim basis or 'beam'; ``recs``: '<run>|<case>' -> recorded mapping."""
    from . import frame_h1 as H1
    from . import h1_sleeve as S
    sets = []
    for ls in targets:
        rk, _ = set_run(ls.key, basis_of[ls.key]) if basis_of[ls.key] != "beam" else (None, False)
        g = split_set(ls, recs.get(rk) if rk else None, basis_of[ls.key])
        tg = f"T{len(sets)}"
        full = copy.copy(ls)
        full.key = f"{tg}:full"
        sets.append(full)
        for i, gs in enumerate(g.values()):
            gs = copy.copy(gs)
            gs.key = f"{tg}:g{i}"
            sets.append(gs)
    # one tag for all: solve_fields_w groups by tag only for the exclusions, which this does not use
    for s_ in sets:
        s_.key = "D:" + s_.key.replace(":", "/")
    f = S.solve_fields_w(H1.base()["dom"], solid, sets)
    ax = member_axial(f)
    out = {}
    n_g = len(GROUPS) + 2
    for j, ls in enumerate(targets):
        rows = {}
        for nm, v in ax.items():
            Nf = float(v["N"][j * n_g])
            Ng = [float(x) for x in v["N"][j * n_g + 1:j * n_g + 1 + len(GROUPS)]]
            Nmv = float(v["N"][(j + 1) * n_g - 1])
            rows[nm] = {"N_full": Nf, "N_groups": dict(zip(GROUPS, Ng)), "sum_check": Nf - sum(Ng),
                        "N_cinch_via_stays": Nf - Ng[5] + Nmv,
                        "A_mm2": v["A_mm2"], "Pcr_n": v["Pcr_n"]}
        out[ls.key] = {"basis": basis_of[ls.key], "case": ls.case, "torso": ls.torso, "factor": ls.factor,
                       "members": rows}
    return out


def body_solid(d_mid: float = 0.0, d_up: float = 0.0, d_low: float = 0.0, alpha: float = ALPHA) -> np.ndarray:
    """H1-G<alpha> (BL-024) with a grow-only offset of ``d_mid`` mm on the mid bar and ``d_up`` / ``d_low`` mm on the
    upper / lower inboard branches (frame_comp_A member groups), on H1's SDF shift: frame_h1.assemble re-imposes
    every keep-out, fairlead, pad, the joint bosses and holes."""
    from . import frame_comp_A as A
    from . import frame_h1 as H1
    from . import h1_sleeve as S
    sh = S.alpha_shift(alpha).copy()
    if d_mid or d_up or d_low:
        c = H1.base()
        grp, z = c["grp"], c["cen"][:, 2]
        sh[grp == A.GROUPS.index("mid")] += d_mid
        br = grp == A.GROUPS.index("branch")
        sh[br & (z >= 330.0)] += d_up
        sh[br & (z < 330.0)] += d_low
    return S.grown_solid(sh)


def axial_eval(name: str, solid: np.ndarray, basis: str, refresh: bool = False) -> dict:
    """Member axial forces on every kit set of ``basis`` (h1_sleeve.kit_sets: kits S/M/L, nearest + other-neighbour
    sim torso), with the margins; cached as OUT/axial_<name>.<basis>.pkl."""
    from . import h1_sleeve as S
    from . import frame_comp_d as D
    from . import frame_h1 as H1

    def run():
        t0 = time.time()
        sets = S.kit_sets(basis)
        f = S.solve_fields_w(H1.base()["dom"], solid, sets)
        ax = member_axial(f)
        return {"meta": f["meta"], "axial": {k: {kk: vv for kk, vv in v.items()} for k, v in ax.items()},
                "margins": margins_from_axial(ax, f["meta"]), "raster_g": D.mass_g(solid, H1.H, 1060.0),
                "seconds": round(time.time() - t0)}
    return _cache(f"axial_{name}.{basis}.pkl", run, refresh)


def lateral_survey() -> list:
    """Hinge-pin and IM3-hook lateral pulls on the frame (1 g, N, + = inboard) in every CORRIE F run on disk, fill and
    meat cases: is the squeeze in the sim itself (all meshes, rev 0 / rev 1) or only in BL-021's mapping?"""
    from . import im3_body_simloads as B
    rows = []
    for rj in sorted(B.SIMDIR.glob("*/results.json")):
        r = json.loads(rj.read_text())
        for case in ("fill", "meat"):
            c = r.get("cases", {}).get(case)
            if not c:
                continue
            a = c.get("attachments", {})
            if "hinge_R" not in a:
                continue
            # force_xyz_n is the force on the bag; the frame gets minus it. Inboard = -x on R, +x on L.
            hR, hL = (np.asarray(a[f"hinge_{s}"]["force_xyz_n"], float) for s in "RL")
            rows.append({"run": rj.parent.name, "case": case, "h_mm": float(r["mesh"]["h_mm"]),
                         "converged": bool(c.get("converged")),
                         "guys_off": "goff" in rj.parent.name,
                         "hinge_in_R": float(hR[0]), "hinge_in_L": float(-hL[0]),
                         "hinge_up_R": float(-hR[2]), "hinge_up_L": float(-hL[2])})
    return rows


def closure_table(recs: dict) -> list:
    """BL-021's closure per sim run: the force left over after the sim's frame-side forces (put on the 4 under-strap
    pins), the sagittal moment closed by the hook / hinge couple, and the two moments the closure leaves open (N mm)."""
    out = []
    for k, r in sorted(recs.items()):
        L = r["last"]
        out.append({"run": k, "weight_n": float(L["weight_n"]), "resid_force_n": [float(v) for v in L["resid_force_n"]],
                    "resid_share": float(np.linalg.norm(L["resid_force_n"]) / L["weight_n"]),
                    "couple_n": float(L["couple_n"]), "moment_fix_nmm": [float(v) for v in L["moment_fix_nmm"]],
                    "open_moment_nmm": [float(L["moment_fix_nmm"][1]), float(L["moment_fix_nmm"][2])]})
    return out


T1_SIM = ("S_meat@a_L_fine_sm8_alt_20:hipbelt_off_abuse|20", "S_meat@a_L_fine_sm8_23:hipbelt_off_abuse|23",
          "S_fill@a_L_fine_sm8_23:hipbelt_off_abuse|23", "S_meat@a_L_fine_sm8_23:side_hill_torsion|23",
          "S_meat@a_L_fine_sm8_23:static_carry|23")
T1_BEAM = ("C@a_L_beam_23:single_stay_setdown|23", "C@a_L_beam_20:hipbelt_off_abuse|20",
           "C@a_L_beam_23:side_hill_torsion|23", "C_im3@a_L_beam_23:static_carry|23")


def task1(solid: np.ndarray | None = None, name: str = "g055", refresh: bool = False) -> dict:
    """Load-group decomposition of the governing sim and beam sets on body ``solid`` (default H1-G0.55)."""
    from . import h1_sleeve as S

    def run():
        sol = body_solid() if solid is None else solid
        recs, sets = {}, {}
        for alt in (False, True):
            ss, rr = rebuilt("a_L", "fine_sm8", alt)
            recs.update(rr)
            sets.update({s.key: s for s in ss})
        for s in S.build_sets("a_L", "beam"):
            sets[s.key] = s
        keys = [k for k in T1_SIM + T1_BEAM]
        targets = [sets[k] for k in keys]
        basis_of = {k: ("beam" if k.startswith("C") else "fine_sm8") for k in keys}
        dec = decompose(sol, targets, basis_of, recs)
        return {"decomposition": dec, "closure": closure_table(recs), "survey": lateral_survey()}
    return _cache(f"task1_{name}.pkl", run, refresh)


# ======================================================================================= task 2: sizing
CANDIDATES = [            # (d_mid, d_up) mm on H1-G0.55's shift; areas jump in whole 4 mm2 voxel faces
    (0.6, 1.4), (0.8, 1.6), (1.0, 1.8), (1.5, 2.0), (0.6, 2.5), (1.0, 2.5),
]


def cand_name(d_mid: float, d_up: float) -> str:
    return f"m{d_mid:g}_u{d_up:g}"


def sizing(cands=CANDIDATES, basis: str = "fine_sm8", log=print) -> dict:
    """Team A's Euler margins of H1-G0.55 + member growth on every kit set of ``basis`` (cached per candidate)."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    g0 = D.mass_g(body_solid(), H1.H, 1060.0)
    out = {}
    for dm, du in cands:
        nm = cand_name(dm, du)
        s = body_solid(dm, du)
        r = axial_eval(nm, s, basis)
        r["added_g"] = r["raster_g"] - g0
        out[nm] = r
        if log:
            mg = {k: v["margin"] for k, v in r["margins"].items()}
            log(f"[{time.strftime('%H:%M:%S')}] {nm} {basis}: +{r['added_g']:.1f} g, min "
                f"{min(v for v in mg.values() if v is not None):.3f} {json.dumps(mg)}")
    return out


BASES_CHECK = ("fine_sm8", "fine", "beam", "fine_sm8.cyc")


def full_check(name: str, solid: np.ndarray, bases=BASES_CHECK, log=print) -> dict:
    """Every BL-024 body check on ``solid``, per basis: H1's FI99 rule (strength, fatigue, creep per kit and
    setting, h1_sleeve.evaluate), team A's Euler margins, the z 234 joint (frame_h1.joint_check); keep-outs once.
    Cached as OUT/check_<name>.json."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    from . import h1_sleeve as S
    p = OUT / f"check_{name}.json"
    res = json.loads(p.read_text()) if p.exists() else {"name": name}
    for b in bases:
        if b in res:
            continue
        t0 = time.time()
        basis, cyc = (b.split(".")[0], b.endswith(".cyc"))
        sets = S.kit_sets(basis, cycled=cyc)
        f = S.solve_fields_w(H1.base()["dom"], solid, sets)
        r = S.evaluate(f)
        ax = member_axial(f)
        jc = H1.joint_check(f)
        res[b] = {"min": r["min"], "per_kit": S.per_kit({"per_setting": S.per_setting(r["per_tag"])}),
                  "governing_tag": r["governing_tag"], "top_regions": r["top_regions"],
                  "buckling": margins_from_axial(ax, f["meta"]),
                  "joint_strength": float(jc["min_strength"]), "joint_fatigue": float(jc["min_fatigue"]),
                  "seconds": round(time.time() - t0)}
        res[b]["buckling_min"] = min(v["margin"] for v in res[b]["buckling"].values() if v["margin"] is not None)
        res[b]["buckling_by_case"] = by_case(ax, f["meta"])
        res[b]["buckling_mirrored"] = mirrored(ax)
        if b == bases[0]:
            # governing-voxel region of the governing fatigue set (frame_cg_recheck.governing_region, task 3)
            from . import frame_cg_recheck as R
            k = next(i for i, mt in enumerate(f["meta"]) if mt["set"] == r["per_tag"][r["governing_tag"]]["fatigue_set"])
            fi = D.fi_material(f["stress"][k].astype(float), D.MATERIALS[H1.MAT])
            gr = R.governing_region(f["cen"], fi, f["ex"][r["governing_tag"]])
            res["governing_region"] = {"set": f["meta"][k]["set"], **gr,
                                       "peak_where": r["per_tag"][r["governing_tag"]].get("peak_xyz")}
        del f
        res["raster_g"] = D.mass_g(solid, H1.H, 1060.0)
        OUT.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, default=_np_default))
        if log:
            log(f"[{time.strftime('%H:%M:%S')}] check {name} {b}: {json.dumps(res[b]['min'])} buckling "
                f"{res[b]['buckling_min']:.3f} joint {res[b]['joint_strength']:.2f}/{res[b]['joint_fatigue']:.2f} "
                f"({res[b]['seconds']} s)")
    if "keepouts" not in res:
        res["keepouts"] = H1.keepouts(solid)
        p.write_text(json.dumps(res, default=_np_default))
    return res


# ======================================================================================= task 4: print files
IM3_HALF_Z = 14.0          # BL-021 (im3_body_simloads.md 2.1, loadpath_verification.md 4.1): IM3 cheek 28 x 8 mm
IM3_HOLE_PRINT_D = 7.0     # ASSUMPTION HOLE_REAM: printed 7.0, reamed to the 7.2 mm UHMWPE sleeve OD (as bores 17.4 -> 18.0)


def im3_cheek_mask(half_z: float = IM3_HALF_Z) -> np.ndarray:
    """Voxels (H1 grid) of the two IM3 fairleads (bag_attach geometry, stations im3_L / im3_R at z 520) with the
    cheek half-height ``half_z`` along the stay; keep-outs (passive void, joint holes) removed."""
    from . import bag_attach as BA
    from . import frame_h1 as H1
    from .frame_branch import _sleeve_y, stay_radius
    from .spreader import SCALE
    c = H1.base()
    cen = c["cen"]
    out = np.zeros(cen.shape[0], bool)
    near = np.where((np.abs(cen[:, 2] - 520.0) < half_z + 6.0) & (np.abs(np.abs(cen[:, 0]) - 115.0) < 30.0))[0]
    old = BA.HALF_Z
    BA.HALF_Z = float(half_z)
    try:
        for st in BA.stations():
            if st["name"] != "im3":
                continue
            r = float(stay_radius(st["z"], SCALE))
            y0 = float(np.asarray(_sleeve_y(st["z"]), float))
            p = cen[near]
            loc = np.c_[p[:, 0] - st["x"], p[:, 1] - y0, p[:, 2] - st["z"]]
            out[near[BA.fairlead_local(loc, r) <= 0.0]] = True
    finally:
        BA.HALF_Z = old
    return out & ~c["dom"].passive_void & ~c["holes"]


def im3_holes() -> list:
    """(centre xyz, half length along x, radius) of the two IM3 eye holes, for the exact print cut."""
    from . import bag_attach as BA
    from .frame_branch import _sleeve_y, stay_radius
    from .spreader import SCALE
    out = []
    for st in BA.stations():
        if st["name"] != "im3":
            continue
        r = float(stay_radius(st["z"], SCALE))
        y0 = float(np.asarray(_sleeve_y(st["z"]), float))
        out.append((np.array([st["x"], y0 + r + BA.HOLE_PROUD, st["z"]]), BA.THROAT / 2.0 + BA.CHEEK + 0.5,
                    IM3_HOLE_PRINT_D / 2.0))
    return out


def final_solid(d_mid: float, d_up: float) -> np.ndarray:
    """The release body: H1-G0.55 + member growth + the 28 mm IM3 cheeks."""
    return body_solid(d_mid, d_up) | im3_cheek_mask()


def clean_shell(mesh) -> tuple:
    """Keep the largest connected shell; return (mesh, dropped [(faces, volume mm3)]). Refuses to drop more than
    1 cm3 (that would be a real part, not a loose island or a boolean sliver)."""
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh, []
    parts = sorted(parts, key=lambda p: -abs(p.volume))
    dropped = [(int(len(p.faces)), float(abs(p.volume))) for p in parts[1:]]
    clean_shell.where = [[round(float(v), 1) for v in p.bounds.mean(axis=0)] for p in parts[1:]]
    if sum(v for _, v in dropped) > 1000.0:
        raise RuntimeError(f"clean_shell: would drop {dropped}")
    return parts[0], dropped


def export_print(d_mid: float, d_up: float, log=print) -> dict:
    """H1 print files from the release body (frame_h1.print_mesh + an exact IM3 eye-hole cut), split at z 234,
    each half one closed shell, laid flat; written to designs/pack_5200/print/frame_h1/."""
    import manifold3d as m3d
    from . import frame_h1 as H1
    from .frame_topopt import split_mesh
    from .surface import _from_manifold, _to_manifold
    solid = final_solid(d_mid, d_up)
    mesh = H1.print_mesh(solid, log=log)
    man = _to_manifold(mesh)
    for c_, half, r in im3_holes():
        cyl = m3d.Manifold.cylinder(2 * half, r, r, 64, center=True)
        cyl = cyl.transform(np.array([[0.0, 0, 1, c_[0]], [0, 1, 0, c_[1]], [-1, 0, 0, c_[2]]]))   # z axis -> x axis
        man = man - cyl
    mesh = _from_manifold(man)
    mesh, drop_a = clean_shell(mesh)
    H1.PRINT_DIR.mkdir(parents=True, exist_ok=True)
    mesh.export(H1.PRINT_DIR / "h1_assembled.stl")
    info = {"d_mid": d_mid, "d_up": d_up, "im3_half_z": IM3_HALF_Z,
            "assembled": {"faces": len(mesh.faces), "volume_cm3": round(mesh.volume / 1000, 2),
                          "g": round(mesh.volume * 1.06e-3, 1), "watertight": bool(mesh.is_watertight),
                          "shells": len(mesh.split(only_watertight=False)), "dropped": drop_a}}
    lo, hi = split_mesh(mesh, H1.JOINT.z)
    for nm, m in (("lower", lo), ("upper", hi)):
        m, drop = clean_shell(m)
        where = list(getattr(clean_shell, "where", [])) if drop else []
        f = H1.lay_flat(m)
        f.export(H1.PRINT_DIR / f"h1_{nm}_flat.stl")
        f.export(H1.PRINT_DIR / f"h1_{nm}_flat.3mf")
        info[nm] = {"faces": len(f.faces), "volume_cm3": round(f.volume / 1000, 2), "g": round(f.volume * 1.06e-3, 1),
                    "footprint_mm": [round(v, 1) for v in f.extents], "watertight": bool(f.is_watertight),
                    "shells": len(f.split(only_watertight=False)), "dropped": drop, "dropped_centre_frame_mm": where,
                    "print_h": round(f.volume / 8.0 / 3600.0 * 1.08, 1),
                    "fits_h2s_340x320x340": bool(sorted(f.extents)[-1] <= 340 and sorted(f.extents)[-2] <= 320)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "print_info.json").write_text(json.dumps(info, indent=1, default=_np_default))
    if log:
        log(json.dumps(info, default=_np_default))
    return info


# ======================================================================================= results / report
CHOSEN = (1.0, 2.5)        # d_mid, d_up (sizing table): least mass with every member >= 1.0 and its mirror >= 1.0


def member_mass(solid: np.ndarray) -> dict:
    """Printed mass (2 mm raster, 1.06 g/cm3) per frame_comp_A member family, g."""
    from . import frame_comp_A as A
    from . import frame_h1 as H1
    grp = H1.base()["grp"][solid]
    out = {g: round(float((grp == i).sum()) * H1.H ** 3 * 1.06e-3, 1) for i, g in enumerate(A.GROUPS)}
    out["other (pivot boss, pads, bosses, passive)"] = round(float((grp < 0).sum()) * H1.H ** 3 * 1.06e-3, 1)
    return out


def compute() -> dict:
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    from . import crown_diet as CD
    res = {"date": "2026-11-12", "targets": {"buckling": BUCKLE_REQ, "buckling_abuse_goal": BUCKLE_GOAL_ABUSE,
                                             "fatigue": FAT_REQ, "strength": STR_REQ},
           "assumptions": ASSUMPTIONS, "baseline": {}, "baseline_by_case": {}, "baseline_mirrored": {}}
    for b in ("fine_sm8", "fine", "beam"):
        a = _cache(f"axial_g055.{b}.pkl", lambda: None)
        res["baseline"][b] = a["margins"]
        res["baseline_by_case"][b] = by_case(a["axial"], a["meta"])
        res["baseline_mirrored"][b] = mirrored(a["axial"])
    t1 = task1()
    res["task1"] = t1
    # sizing table
    s0 = body_solid()
    g_h1 = D.mass_g(CD._h1_solid(), H1.H, 1060.0)
    g0 = D.mass_g(s0, H1.H, 1060.0)
    rows = []
    for p in sorted(OUT.glob("axial_m*_u*.fine_sm8.pkl")):
        nm = p.name[len("axial_"):-len(".fine_sm8.pkl")]
        dm, du = (float(x[1:]) for x in nm.split("_"))
        a = pickle.loads(p.read_bytes())
        mg = a["margins"]
        rows.append({"name": nm, "d_mid": dm, "d_up": du, "added_g": a["raster_g"] - g0,
                     "areas": {k: v["A_mm2"] for k, v in mg.items()}, "margins": {k: v["margin"] for k, v in mg.items()},
                     "min": min(v["margin"] for v in mg.values() if v["margin"] is not None),
                     "mirrored": mirrored(a["axial"]), "by_case": by_case(a["axial"], a["meta"])})
    res["sizing"] = sorted(rows, key=lambda r: r["added_g"])
    # chosen body (with the 28 mm IM3 cheek)
    dm, du = CHOSEN
    name = f"{cand_name(dm, du)}_im3"
    ck = json.loads((OUT / f"check_{name}.json").read_text())
    sol = final_solid(dm, du)
    sim = [ck[b] for b in ("fine_sm8", "fine")]
    ko = ck["keepouts"]
    present = {k: float(v) for k, v in ko.items() if k.endswith("present")}
    empty = {k: float(v) for k, v in ko.items() if k.endswith("empty")}
    cheek_g = float((im3_cheek_mask() & ~body_solid(dm, du)).sum()) * H1.H ** 3 * 1.06e-3
    fmin = min(c["min"]["fatigue"] for c in sim)
    smin = min(ck[b]["min"]["strength"] for b in BASES_CHECK)
    c = {"name": f"H1-G0.55-B{dm:g}/{du:g}", "d_mid": dm, "d_up": du, "body_raster_g": ck["raster_g"],
         "added_vs_g055_g": ck["raster_g"] - g0, "added_vs_h1_g": ck["raster_g"] - g_h1, "h1_raster_g": g_h1,
         "g055_raster_g": g0, "im3_cheek_added_g": cheek_g,
         "members_added_g": ck["raster_g"] - g0 - cheek_g,
         "buckling": {b: ck[b]["buckling"] for b in BASES_CHECK if b in ck},
         "buckling_by_case": {b: ck[b]["buckling_by_case"] for b in BASES_CHECK if b in ck},
         "buckling_mirrored": {b: ck[b]["buckling_mirrored"] for b in BASES_CHECK if b in ck},
         "buckling_min_sim": min(c_["buckling_min"] for c_ in sim), "buckling_min_beam": ck["beam"]["buckling_min"],
         "mirrored_min": min(v for b in ("fine_sm8", "fine", "beam") for v in ck[b]["buckling_mirrored"].values()
                             if v is not None),
         "abuse_margin_sim": min(ck[b]["buckling_by_case"]["hipbelt_off_abuse"]["margin"] for b in ("fine_sm8", "fine")),
         "fatigue_min_sim": fmin, "fatigue_beam": ck["beam"]["min"]["fatigue"],
         "fatigue_cinch_cycled": ck["fine_sm8.cyc"]["min"]["fatigue"], "strength_min": smin,
         "creep_min": min(ck[b]["min"]["creep"] for b in ("fine_sm8", "fine", "beam")),
         "per_kit": {b: ck[b]["per_kit"] for b in BASES_CHECK},
         "joint": {b: [ck[b]["joint_strength"], ck[b]["joint_fatigue"]] for b in BASES_CHECK},
         "keepouts": ko, "keepouts_present": present, "keepouts_empty": empty,
         "governing_region": ck.get("governing_region"),
         "member_mass_g": member_mass(sol), "member_mass_g055_g": member_mass(s0),
         "ca1_flip": 0.30 / fmin, "print_h_est": 27.0 * ck["raster_g"] / 757.7}
    c["passes"] = bool(c["buckling_min_sim"] >= BUCKLE_REQ and c["buckling_min_beam"] >= BUCKLE_REQ
                       and c["mirrored_min"] >= BUCKLE_REQ and fmin >= FAT_REQ and smin >= STR_REQ
                       and all(v >= 0.999 for v in present.values()) and all(v >= 0.999 for v in empty.values())
                       and ko.get("outside envelope (voxels)", 0) == 0)
    res["chosen"] = c
    try:
        res["ledger_h1_body_g"] = json.loads((ANALYSIS / "frame_mass_h1.json").read_text())["h1"]["body_g"]
    except Exception:
        res["ledger_h1_body_g"] = None
    pi = OUT / "print_info.json"
    res["print"] = json.loads(pi.read_text()) if pi.exists() else None
    return res


INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C_COMP, C_TENS, C_BASE, C_ADD, C_CHEEK = "#eb6834", "#2a78d6", "#b9b8b2", "#eb6834", "#2a78d6"


def _shrink(path: Path):
    from .weight_c import shrink
    shrink(path, 1_500_000)


def plot_decomposition(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dec = res["task1"]["decomposition"]
    panels = [("S_meat@a_L_fine_sm8_alt_20:hipbelt_off_abuse|20", "mid bar (x -115..115) all",
               "Mid bar, hipbelt-off abuse\nsim 19 in run, kit L at 20 in, meat"),
              ("S_meat@a_L_fine_sm8_23:side_hill_torsion|23", "branch upper (z 330-495) R",
               "Upper branch R, side-hill\nsim 23 in (sm8), meat"),
              ("C@a_L_beam_23:single_stay_setdown|23", "branch upper (z 330-495) R",
               "Upper branch R, single-stay set-down\nbeam loads (the beam's governing set)")]
    fig, axs = plt.subplots(1, 3, figsize=(15, 6.6), sharey=True)
    labels = list(GROUP_SHORT)
    for ax, (k, mem, title) in zip(axs, panels):
        m = dec[k]["members"][mem]
        vals = list(m["N_groups"].values())
        y = np.arange(len(vals))[::-1]
        ax.barh(y, vals, color=[C_COMP if v < 0 else C_TENS for v in vals], height=0.62, edgecolor="white", lw=2)
        ax.axvline(0, color=INK2, lw=1)
        ax.axvline(m["N_full"], color=INK, lw=2, ls="--")
        ax.text(m["N_full"], -0.55, f" total {m['N_full']:.0f} N", color=INK, fontsize=10, va="center",
                fontweight="bold")
        if abs(m["N_cinch_via_stays"] - m["N_full"]) > 1:
            ax.axvline(m["N_cinch_via_stays"], color=INK2, lw=1.5, ls=":")
            ax.text(m["N_cinch_via_stays"], len(vals) - 0.45, f" cinch via stays {m['N_cinch_via_stays']:.0f} N",
                    color=INK2, fontsize=9, va="bottom")
        for yy, v in zip(y, vals):
            if abs(v) >= 20:
                ax.text(v, yy, f" {v:.0f} " if v > 0 else f"{v:.0f} ", va="center", ha="left" if v > 0 else "right",
                        fontsize=9, color=INK2)
        ax.set_title(title, fontsize=11, color=INK, loc="left", pad=18)
        ax.set_yticks(np.arange(len(vals))[::-1])
        ax.set_yticklabels(labels, fontsize=10)
        ax.grid(axis="x", color=GRID)
        ax.set_axisbelow(True)
        ax.set_xlabel("member axial force at the cut, factored, N  (- = compression)", fontsize=9, color=INK2)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        lim = max(abs(v) for v in vals + [m["N_full"]]) * 1.35
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-1.0, len(vals) - 0.1)
    fig.suptitle("BL-027 what compresses the members: the meat-strap cinch loop and the crown, not the sideways "
                 "squeeze (H1-G0.55)", fontsize=13, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=110)
    plt.close(fig)
    _shrink(path)
    return str(path)


def plot_sizing(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = res["sizing"]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    mid = "mid bar (x -115..115) all"
    up = "branch upper (z 330-495) R"
    x = [r["added_g"] for r in rows]
    ax.plot(x, [r["margins"][mid] for r in rows], "o", ms=9, color=C_TENS, label="mid bar (hipbelt-off abuse)")
    ax.plot(x, [r["margins"][up] for r in rows], "s", ms=9, color=C_COMP, label="upper branch R (side-hill)")
    ax.plot(x, [min(v for v in r["mirrored"].values() if v) for r in rows], "^", ms=8, color="#6250d6",
            label="branches, mirrored side-hill")
    base = res["baseline"]["fine_sm8"]
    ax.plot([0], [base[mid]["margin"]], "o", ms=9, color=C_TENS, mfc="white")
    ax.plot([0], [base[up]["margin"]], "s", ms=9, color=C_COMP, mfc="white")
    ax.annotate("H1-G0.55", (0, base[mid]["margin"]), xytext=(6, -14), textcoords="offset points", fontsize=9,
                color=INK2)
    for r in rows:
        ax.annotate(f"mid +{r['d_mid']:g} / br +{r['d_up']:g} mm", (r["added_g"], r["min"]), xytext=(5, -16),
                    textcoords="offset points", fontsize=8, color=INK2)
    c = res["chosen"]
    ax.axvline(c["members_added_g"], color=INK2, lw=1, ls=":")
    ax.text(c["members_added_g"], 0.32, " chosen", color=INK2, fontsize=9)
    ax.axhline(BUCKLE_REQ, color=INK, lw=1.5)
    ax.axhline(BUCKLE_GOAL_ABUSE, color=INK2, lw=1, ls="--")
    ax.text(0.2, BUCKLE_REQ + 0.02, "required 1.0", fontsize=9, color=INK)
    ax.text(0.2, BUCKLE_GOAL_ABUSE + 0.02, "abuse goal 1.2", fontsize=9, color=INK2)
    ax.set_xlabel("added printed mass over H1-G0.55, g (2 mm raster)")
    ax.set_ylabel("Euler margin, sim loads fine_sm8 (team A rule)")
    ax.set_title("Sizing: stiffer bars draw more load, so the branches need more area than the hand estimate",
                 loc="left", fontsize=12, color=INK)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax.set_ylim(0.3, max(1.8, ax.get_ylim()[1]))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    _shrink(path)
    return str(path)


def plot_body(res: dict, path: Path) -> str:
    """Front (bag side) and side views of the chosen body: H1-G0.55 grey, BL-027 growth orange, 28 mm IM3 cheek blue."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import frame_h1 as H1
    c = res["chosen"]
    cen = H1.base()["cen"]
    s0 = body_solid()
    s1 = body_solid(c["d_mid"], c["d_up"])
    ch = im3_cheek_mask() & ~s1
    add = s1 & ~s0
    fig, axs = plt.subplots(1, 2, figsize=(13, 8.4), gridspec_kw={"width_ratios": [2.2, 1]})
    for ax, (i, j, xl) in zip(axs, ((0, 2, "x mm (right +)"), (1, 2, "y mm (aft, toward the bag +)"))):
        for m, col, sz, lab in ((s0, C_BASE, 2.0, f"H1-G0.55 ({c['g055_raster_g']:.0f} g)"),
                                (add, C_ADD, 3.0, f"BL-027 growth (+{c['members_added_g']:.1f} g)"),
                                (ch, C_CHEEK, 3.0, f"IM3 cheek 18 -> 28 mm (+{c['im3_cheek_added_g']:.1f} g)")):
            p = cen[m]
            order = np.argsort(p[:, 1] if i == 0 else -p[:, 0])
            ax.scatter(p[order, i], p[order, j], s=sz, c=col, lw=0, label=lab)
        ax.set_aspect("equal")
        ax.set_xlabel(xl)
        ax.set_ylabel("z mm")
        ax.grid(color=GRID, lw=0.5)
        ax.set_axisbelow(True)
    axs[0].legend(loc="upper center", markerscale=5, frameon=False, fontsize=10, ncol=1)
    axs[0].set_title("Front view (from the bag)", loc="left", fontsize=11)
    axs[1].set_title("Side view", loc="left", fontsize=11)
    b = c["buckling"]["fine_sm8"]
    fig.suptitle(f"{c['name']}: mid bar A {b['mid bar (x -115..115) all']['A_mm2']:.0f} mm2, upper branches "
                 f"{b['branch upper (z 330-495) L']['A_mm2']:.0f} / {b['branch upper (z 330-495) R']['A_mm2']:.0f} mm2; "
                 f"Euler min {c['buckling_min_sim']:.2f} sim / {c['buckling_min_beam']:.2f} beam, fatigue "
                 f"{c['fatigue_min_sim']:.3f}", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=100)
    plt.close(fig)
    _shrink(path)
    return str(path)


def plot_print(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from . import frame_h1 as H1
    fig = plt.figure(figsize=(13, 7))
    for k, nm in enumerate(("lower", "upper")):
        m = trimesh.load(H1.PRINT_DIR / f"h1_{nm}_flat.stl")
        m = m.simplify_quadric_decimation(face_count=20000) if hasattr(m, "simplify_quadric_decimation") else m
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        tri = m.vertices[m.faces]
        n = m.face_normals
        shade = 0.35 + 0.6 * np.clip(n @ np.array([0.3, -0.5, 0.8]) / 1.0, 0, 1)
        pc = Poly3DCollection(tri, facecolors=np.c_[shade[:, None] * np.array([[0.36, 0.36, 0.34]]) + 0.25,
                                                     np.ones(len(shade))].clip(0, 1), linewidths=0)
        ax.add_collection3d(pc)
        e = m.extents
        ax.set_xlim(0, max(e))
        ax.set_ylim(0, max(e))
        ax.set_zlim(0, max(e) * 0.6)
        ax.view_init(elev=55, azim=-70)
        ax.set_box_aspect((1, 1, 0.6))
        info = res["print"][nm]
        ax.set_title(f"h1_{nm}_flat: {info['g']:.0f} g, {info['shells']} shell, footprint "
                     f"{info['footprint_mm'][0]:.0f} x {info['footprint_mm'][1]:.0f} x {info['footprint_mm'][2]:.0f} mm",
                     fontsize=10, loc="left")
        ax.set_axis_off()
    fig.suptitle("BL-027 H1 print halves as laid on the plate (wearer face down)", fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    _shrink(path)
    return str(path)


def _lbf(n):
    return f"{n / 4.44822:.0f} lbf"


def _oz(g):
    return f"{g / 28.3495:.2f} oz"


SHORT = {"mid bar (x -115..115) all": "mid bar", "branch upper (z 330-495) L": "upper branch L",
         "branch upper (z 330-495) R": "upper branch R", "branch lower (z 165-330) L": "lower branch L",
         "branch lower (z 165-330) R": "lower branch R"}


def write_md(res: dict, shots: list) -> str:
    c = res["chosen"]
    t1 = res["task1"]
    dec = t1["decomposition"]
    base = res["baseline"]
    L = []
    a = L.append
    a("# BL-027 H1 branch / mid-bar buckling on the cloth-sim loads\n")
    a("Generated by `python -m huntkit.gendesign.h1_buckling` (data `h1_buckling.json`). Date 2026-11-12. Body: BL-024's "
      "H1-G0.55. Rule: team A's Euler check as BL-021 / BL-024 ran it (`frame_h1.buckling`: K 1, the member's voxel area "
      "at one cut as a solid round bar, E_xy x 0.6 hot x 0.7 creep, **margin = P_cr / (1.5 x factored compression) >= 1**). "
      "Loads: HA-LS-1 rev C on the CORRIE F rev 1 fine sim (bases fine_sm8 / fine, BL-024) and on the beam basis, every crown "
      "kit S / M / L at every setting. Units N, mm, g (lbf, oz alongside).\n")
    # ---------------- summary
    mk = "mid bar (x -115..115) all"
    up = "branch upper (z 330-495) R"
    dm = dec["S_meat@a_L_fine_sm8_alt_20:hipbelt_off_abuse|20"]["members"][mk]
    du = dec["S_meat@a_L_fine_sm8_23:side_hill_torsion|23"]["members"][up]
    G = GROUPS
    sv = [r for r in t1["survey"] if r["converged"] and not r["guys_off"]]
    rng = {cs: (min(min(r["hinge_in_R"], r["hinge_in_L"]) for r in sv if r["case"] == cs),
                max(max(r["hinge_in_R"], r["hinge_in_L"]) for r in sv if r["case"] == cs)) for cs in ("meat", "fill")}
    hk = [v for k_, ff in json.loads((REPO / "outputs" / "h1_sleeve" / "sim_forces.json").read_text()).items()
          if k_.endswith("|meat") for v in (-ff["forces"]["hook_im520_R"]["f"][0], ff["forces"]["hook_im520_L"]["f"][0])]
    a("## Summary\n")
    a(f"- **Reproduced:** H1-G0.55 on fine_sm8 gives **{base['fine_sm8'][mk]['margin']:.3f}** (mid bar, "
      f"{base['fine_sm8'][mk]['set']}) and {base['fine_sm8'][up]['margin']:.3f} (upper branch R, "
      f"{base['fine_sm8'][up]['set']}); beam {min(v['margin'] for v in base['beam'].values() if v['margin']):.3f}. "
      "Same as BL-024 (0.44 / 0.72 / 1.27).")
    a(f"- **The sideways squeeze is real, but it is not what buckles the members.** The hinge pins pull the stay feet "
      f"inboard by {rng['meat'][0]:.0f}-{rng['meat'][1]:.0f} N a side at 1 g in every converged meat run (coarse and fine, "
      f"rev 0 and rev 1; the bag floor spans pin to pin), and the IM3 hooks by {min(hk):.0f}-{max(hk):.0f} N (fine meat runs). Split exactly by superposition on the same voxel solve, the "
      f"squeeze gives the mid bar **{dm['N_groups'][G[0]] + dm['N_groups'][G[1]]:+.0f} N** of its "
      f"{dm['N_full']:.0f} N (it slightly unloads it) and the upper branch R {du['N_groups'][G[0]] + du['N_groups'][G[1]]:+.0f} N "
      f"of {du['N_full']:.0f} N.")
    a(f"- **What does compress them is the meat-strap cinch loop** (6 x 150 N cinch: the meat pushes the spreader forward "
      f"onto the bar and branch nodes, the straps pull the stays aft): **{dm['N_groups'][G[5]]:.0f} N** on the mid bar and "
      f"**{du['N_groups'][G[5]]:.0f} N** on the upper branch R, plus the crown interface in hipbelt-off "
      f"({dm['N_groups'][G[8]]:.0f} N on the mid bar). The beam basis has no cinch loop in its bag cases, which is "
      f"why it reads 1.27 and the sim 0.44.")
    a(f"- **BL-021's closure is not the cause:** the leftover force is 10-15 % of the payload weight, almost all "
      f"vertical, and the closure (pins + couple) *relieves* the mid bar ({dm['N_groups'][G[4]]:+.0f} N). The two moments "
      f"it leaves open are 3-12 N m. **The mapping choice that matters is the spreader:** BL-021 puts each spreader-"
      f"contact node force on the nearest frame face node (no plate spreading). If the spreader carried the cinch push "
      f"to the stays instead, the mid bar would see {dm['N_cinch_via_stays']:.0f} N (not {dm['N_full']:.0f}) and the "
      f"upper branch R {du['N_cinch_via_stays']:.0f} N (not {du['N_full']:.0f}). The real Sandwich v2 bears on the bar "
      f"and branches through bonded pucks, so the truth is in between; the sizing below uses the mapping as it is "
      f"(upper bound), ASSUMPTION SPREADER_MAP.")
    b = c["buckling"]["fine_sm8"]
    a(f"- **Fix (task 2): {c['name']}** = H1-G0.55 + grow-only offset +{c['d_mid']:g} mm on the mid bar and "
      f"+{c['d_up']:g} mm on the upper branches (H1's SDF shift, keep-outs re-imposed): mid bar A "
      f"{base['fine_sm8'][mk]['A_mm2']:.0f} -> {b[mk]['A_mm2']:.0f} mm2, upper branches "
      f"{base['fine_sm8'][up]['A_mm2']:.0f} -> {b['branch upper (z 330-495) L']['A_mm2']:.0f} / {b[up]['A_mm2']:.0f} mm2. "
      f"**+{c['members_added_g']:.1f} g ({_oz(c['members_added_g'])})** per frame for the members, against the "
      f"ticket's hand estimate of +17 g: the stiffer bars draw more load (upper branch R 426 -> "
      f"{b[up]['P_factored_n']:.0f} N factored), and thickening the mid bar alone pushes load into the "
      f"branches (sizing table).")
    a(f"- **Result:** Euler min **{c['buckling_min_sim']:.2f} sim** / **{c['buckling_min_beam']:.2f} beam**, mirrored "
      f"side-hill {c['mirrored_min']:.2f}, hipbelt-off abuse **{c['abuse_margin_sim']:.2f}** (goal 1.2 met). Fatigue "
      f"**{c['fatigue_min_sim']:.3f}** sim (goal 1.15), {c['fatigue_beam']:.3f} beam, strength {c['strength_min']:.2f}, "
      f"creep {c['creep_min']:.2f}; z 234 joint {c['joint']['fine_sm8'][0]:.2f} / {c['joint']['fine_sm8'][1]:.2f} sim, "
      f"{c['joint']['beam'][0]:.2f} / {c['joint']['beam'][1]:.2f} beam; every keep-out held. "
      f"**{'PASS' if c['passes'] else 'FAIL'}.**")
    a(f"- **Body mass:** {c['body_raster_g']:.1f} g ({_oz(c['body_raster_g'])}) raster = H1 {c['h1_raster_g']:.1f} + "
      f"BL-024 {c['g055_raster_g'] - c['h1_raster_g']:.1f} + BL-027 members {c['members_added_g']:.1f} + 28 mm IM3 cheeks "
      f"{c['im3_cheek_added_g']:.1f} g; **+{c['added_vs_h1_g']:.1f} g ({_oz(c['added_vs_h1_g'])}) over the H1 the ledger "
      f"books ({res['ledger_h1_body_g']} g)**. The ledger row (`frame_mass_h1.json`) is not changed here.")
    a(f"- **Fatigue still rests on CINCH_STATIC:** with the cinch cycled the body is {c['fatigue_cinch_cycled']:.3f} "
      "(BL-024 0.751); MT-1 must still settle it before R1, as BL-024 said.")
    if res.get("print"):
        p = res["print"]
        a(f"- **Print files (task 4) written** to `designs/pack_5200/print/frame_h1/`: lower {p['lower']['g']:.0f} g, "
          f"upper {p['upper']['g']:.0f} g, each **one closed shell** (dropped: lower {len(p['lower']['dropped'])}, "
          f"upper {len(p['upper']['dropped'])}, assembled {len(p['assembled']['dropped'])} loose pieces), with the 28 mm IM3 "
          "cheeks and an exact eye hole.")
    a(f"- **Label (task 3):** `frame_cg_recheck.region_label` now calls z 160-240 of the stay \"lower sleeve z 160-240 "
      f"(branch / strut root)\" instead of \"crown bore wall\"; the new `frame_cg_recheck.governing_region` names the region "
      f"that holds the top 1 % voxels. On this body: **{c['governing_region']['region']}** "
      f"({100 * c['governing_region']['share']:.0f} % of the top 1 %), peak voxel in \"{c['governing_region']['peak_region']}\".\n")
    # ---------------- 1 reproduction
    a("## 1. The rule on H1-G0.55 (reproduction)\n")
    a("| member | A mm2 | P_cr N | sim fine_sm8: P N / margin / set | sim fine: margin | beam: P N / margin / set |")
    a("|---|---|---|---|---|---|")
    for k in MEMBERS:
        s8, fi, be = base["fine_sm8"][k], base["fine"][k], base["beam"][k]
        bm = "tension in every set" if be["margin"] is None else f"{be['P_factored_n']:.0f} / **{be['margin']:.2f}** / `{be['set']}`"
        a(f"| {SHORT[k]} | {s8['A_mm2']:.0f} | {s8['Pcr_n']:.0f} | {s8['P_factored_n']:.0f} ({_lbf(s8['P_factored_n'])}) / "
          f"**{s8['margin']:.2f}** / `{s8['set']}` | {fi['margin']:.2f} | {bm} |")
    a("")
    a("Least margin per load case (sim fine_sm8): " + ", ".join(
        f"{k} {v['margin']:.2f} ({SHORT[v['member']]})" for k, v in res["baseline_by_case"]["fine_sm8"].items()) + ".\n")
    # ---------------- 2 load real
    a("## 2. Is the load real? (task 1)\n")
    a("### 2.1 The sideways pulls are in the sim itself\n")
    a("Frame-side lateral force at the hinge pins (1 g, + = toward the frame centre), every CORRIE F run on disk, "
      "read straight from each run's `results.json` (no BL-021 mapping in between):\n")
    a("| run | case | cloth h mm | converged | hinge R in N | hinge L in N |")
    a("|---|---|---|---|---|---|")
    for r in t1["survey"]:
        if r["guys_off"]:
            continue
        a(f"| {r['run']} | {r['case']} | {r['h_mm']:.0f} | {'yes' if r['converged'] else 'no'} | {r['hinge_in_R']:.0f} | "
          f"{r['hinge_in_L']:.0f} |")
    a("\nGuys-off runs (retired, BL-025) left out. The pull is there in every mesh and revision, bigger with meat "
      f"({rng['meat'][0]:.0f}-{rng['meat'][1]:.0f} N) than with fill ({rng['fill'][0]:.0f}-{rng['fill'][1]:.0f} N): the bag floor spans the 246 mm between the pins and hangs the load like a "
      "hammock. It is self-balanced (net x <= 4 N), so it is not a closure leak. ASSUMPTION FLOOR_SPAN.\n")
    a("### 2.2 BL-021's closure at the payload CG\n")
    a("| sim run | leftover force x / y / z N (to the 4 under-strap pins) | share of weight | couple N (hooks / hinges) | open moments My / Mz N m |")
    a("|---|---|---|---|---|")
    for r in t1["closure"]:
        f = r["resid_force_n"]
        a(f"| {r['run']} | {f[0]:.1f} / {f[1]:.1f} / {f[2]:.1f} | {100 * r['resid_share']:.0f} % | {r['couple_n']:.0f} | "
          f"{r['open_moment_nmm'][0] / 1e3:.1f} / {r['open_moment_nmm'][1] / 1e3:.1f} |")
    a("\nThe leftover (the bag weight the sim carries through the under-straps, wraps and fabric not rebuilt as "
      "anchors) is mostly vertical and split evenly between the four pins, so it adds no squeeze. The roll and yaw "
      "moments are left open and reacted by the harness / crown; they are 3-12 N m against the 92-128 N m sagittal "
      "moment the couple closes.\n")
    a("### 2.3 Where the compression comes from, member by member\n")
    a("Each set split into load groups (each solved on the same voxel body; the groups add up to the full set to "
      "1e-5 N). Factored member force at the Euler cut, N (- = compression).\n")
    a("| set | member | full | " + " | ".join(GROUP_SHORT) + " | cinch via stays |")
    a("|---|---|---|" + "---|" * len(GROUP_SHORT) + "---|")
    for k, v in dec.items():
        for mem in (mk, up, "branch upper (z 330-495) L"):
            m = v["members"][mem]
            a(f"| `{k}` | {SHORT[mem]} | **{m['N_full']:.0f}** | " + " | ".join(f"{x:.0f}" for x in m["N_groups"].values())
              + f" | {m['N_cinch_via_stays']:.0f} |")
    a("\nGroups: *hinge squeeze* / *hook squeeze* = the sim's lateral (x) force at the hinge pins (z 60) / IM3 hooks "
      "(z 520); *other sim x* = every other lateral sim force (contact on the stays, guys); *sim y/z* = the rest of the "
      "sim bag force (hooks and hinges vertical / fore-aft, spreader and frame contact, strap pulls of the meat "
      "overturning); *closure* = BL-021's under-strap pins + couple; *cinch* = the meat-strap cinch loop (fixed part: "
      "the spreader push it causes on the face nodes + the strap pulls at the IM anchors); *beam x / beam y/z* = the "
      "beam case's own part (side-hill tilt, downhill bias, harness reactions on the body side); *crown* = bushing and "
      "pawl forces from the crown model (shoulders and lifters). *Cinch via stays* = the full set with the cinch push on "
      "the inboard face nodes moved to the two stays by the lever rule (a spreader that spans stay to stay).\n")
    a("**Reading:** the beam sets compress the upper branch in set-down only (-241 N; its hipbelt-off and static "
      "carry sets put both the mid bar and branches in tension). The sim sets add the cinch loop, which on its own "
      "compresses the mid bar by about 140 N and each upper branch by about 155-240 N, and the hinge squeeze, which "
      "loads the upper branches by about 55-80 N. The cinch loop is a real preload (rev C holds 150 N per strap end "
      "in every set); how much of it reaches the inboard members depends on how the spreader shares it between the "
      "stays and the pucks on the bar / branches, which BL-021's nearest-node mapping does not model (upper bound).\n")
    # ---------------- 3 sizing
    a("## 3. Sizing (task 2)\n")
    a("Grow-only offset on H1-G0.55's SDF shift (`body_solid`): +d_mid on the mid-bar member family, +d_up on the "
      "inboard branches above z 330 (frame_comp_A groups); frame_h1.assemble re-imposes keep-outs, fairleads, pads, "
      "bosses and holes. Areas move in whole 4 mm2 voxel faces (ASSUMPTION MESH). Every kit set of fine_sm8:\n")
    a("| mid + / branch + mm | added g | mid bar A / margin | upper L A / margin | upper R A / margin | lower L / R margin | mirrored upper | min |")
    a("|---|---|---|---|---|---|---|---|")
    a(f"| 0 / 0 (H1-G0.55) | 0.0 | {base['fine_sm8'][mk]['A_mm2']:.0f} / {base['fine_sm8'][mk]['margin']:.2f} | "
      f"{base['fine_sm8']['branch upper (z 330-495) L']['A_mm2']:.0f} / {base['fine_sm8']['branch upper (z 330-495) L']['margin']:.2f} | "
      f"{base['fine_sm8'][up]['A_mm2']:.0f} / {base['fine_sm8'][up]['margin']:.2f} | "
      f"{base['fine_sm8']['branch lower (z 165-330) L']['margin']:.2f} / {base['fine_sm8']['branch lower (z 165-330) R']['margin']:.2f} | "
      f"{res['baseline_mirrored']['fine_sm8']['branch upper (z 330-495)']:.2f} | "
      f"{min(v['margin'] for v in base['fine_sm8'].values()):.2f} |")
    for r in res["sizing"]:
        ar, mg = r["areas"], r["margins"]
        a(f"| {r['d_mid']:g} / {r['d_up']:g} | {r['added_g']:.1f} | {ar[mk]:.0f} / {mg[mk]:.2f} | "
          f"{ar['branch upper (z 330-495) L']:.0f} / {mg['branch upper (z 330-495) L']:.2f} | {ar[up]:.0f} / {mg[up]:.2f} | "
          f"{mg['branch lower (z 165-330) L']:.2f} / {mg['branch lower (z 165-330) R']:.2f} | "
          f"{r['mirrored']['branch upper (z 330-495)']:.2f} | **{r['min']:.2f}** |")
    a("\n- The mid bar passes from A 128 mm2 (+1.0 mm); +0.6 / +0.8 mm raster to 112 mm2 and stop at 0.99-1.02.")
    a("- The upper branch R draws load as it stiffens (factored 426 N at A 108, about 500 N at 128) and more again when "
      "the mid bar is stiffened (+1.5 mm on the bar takes it back to 0.73). It needs A 152-160 mm2 (+2.5 mm).")
    a("- +1.0 / +2.2 would raster to 132 / 140 mm2 (left / right): the mirrored side-hill would rest on 132 mm2, so it "
      "was not taken. **Chosen: +1.0 / +2.5**, the least mass with every member and its mirror >= 1.0 and the "
      "abuse case >= 1.2.\n")
    # ---------------- 4 chosen
    a(f"## 4. {c['name']}: every check (with the 28 mm IM3 cheeks)\n")
    a("| basis | Euler min (member) | hipbelt-off abuse | mirrored branches | fatigue | strength | creep | joint strength / fatigue |")
    a("|---|---|---|---|---|---|---|---|")
    for bb in BASES_CHECK:
        bk = c["buckling"][bb]
        km = min((k for k in bk if bk[k]["margin"] is not None), key=lambda k: bk[k]["margin"])
        ab = c["buckling_by_case"][bb].get("hipbelt_off_abuse")
        mir = min(v for v in c["buckling_mirrored"][bb].values() if v is not None)
        ck = json.loads((OUT / f"check_{cand_name(c['d_mid'], c['d_up'])}_im3.json").read_text())[bb]
        lab = {"fine_sm8": "sim fine_sm8 (governing)", "fine": "sim fine (BL-021 runs)", "beam": "beam rev C",
               "fine_sm8.cyc": "sim fine_sm8, cinch cycled (bound)"}[bb]
        abt = f"{ab['margin']:.2f}" if ab else "no member in compression"
        a(f"| {lab} | **{bk[km]['margin']:.2f}** ({SHORT[km]}) | {abt} | {mir:.2f} | "
          f"**{ck['min']['fatigue']:.3f}** | {ck['min']['strength']:.2f} | {ck['min']['creep']:.2f} | "
          f"{c['joint'][bb][0]:.2f} / {c['joint'][bb][1]:.2f} |")
    a("\nFatigue per crown kit (worst setting): " + "; ".join(
        f"{bb}: " + ", ".join(f"{k} {v['fatigue']:.3f}" for k, v in c["per_kit"][bb].items())
        for bb in ("fine_sm8", "beam")) + ".\n")
    a("Euler margins per member, sim fine_sm8:\n")
    a("| member | A mm2 | P_cr N | factored P N | margin | set |")
    a("|---|---|---|---|---|---|")
    for k in MEMBERS:
        v = c["buckling"]["fine_sm8"][k]
        a(f"| {SHORT[k]} | {v['A_mm2']:.0f} | {v['Pcr_n']:.0f} | {v['P_factored_n']:.0f} ({_lbf(v['P_factored_n'])}) | "
          f"{v['margin']:.2f} | `{v['set']}` |")
    a("\nKeep-outs (fraction of each fixed interface present / bore empty): " + ", ".join(
        f"{k} {v:.3f}" for k, v in {**c["keepouts_present"], **c["keepouts_empty"]}.items())
      + f"; outside envelope {c['keepouts'].get('outside envelope (voxels)')} voxels; boss clear of the spreader clip "
        f"{c['keepouts'].get('boss clear of spreader clip')}.\n")
    a("### 4.1 Mass of each load-path member (2 mm raster, PAHT-CF 1.06 g/cm3)\n")
    a("| member family | H1-G0.55 g | chosen g | change g |")
    a("|---|---|---|---|")
    for k, v in c["member_mass_g"].items():
        v0 = c["member_mass_g055_g"].get(k, 0.0)
        a(f"| {k} | {v0:.1f} | {v:.1f} | {v - v0:+.1f} |")
    a(f"| **body** | **{c['g055_raster_g']:.1f}** | **{c['body_raster_g']:.1f}** | **{c['body_raster_g'] - c['g055_raster_g']:+.1f}** |")
    a("\nFamilies by nearest member (frame_comp_A.group_of); the IM3 cheek growth sits in 'top' / 'sleeve'.\n")
    a("### 4.2 Mass reductions that keep the margins (not applied; each needs its own run)\n")
    a(f"1. **Settle the spreader share (biggest lever).** If a plate run of Sandwich v2 (spreader.py's plate on the H1 "
      f"supports, with the cinch preload) shows the stays take most of the cinch push, the sim compression falls toward "
      f"the *cinch via stays* column (mid bar {dm['N_cinch_via_stays']:.0f} N, upper branch R {du['N_cinch_via_stays']:.0f} N), "
      f"H1-G0.55 would pass as it is and the {c['members_added_g']:.0f} g could come back off.")
    a("2. **Taper the growth.** A pinned-pinned column needs its stiffness most in the middle; growing only the middle "
      "60 % of each member should keep most of P_cr for about 60 % of the added mass (hand estimate, not run: "
      "roughly -8 g). Needs the cut rule changed to the member's least section (it is one cut today).")
    a("3. **Credit end fixity.** The mid bar and branches run into the stays and the bar junction; K 0.8 would raise every "
      "P_cr by 1.56 x. Only with an eigenvalue run of the voxel body or the T1 squeeze test (ASSUMPTION EULER_RULE).\n")
    # ---------------- 5 label
    gr = c["governing_region"]
    a("## 5. Region label (task 3)\n")
    a("`frame_cg_recheck.region_label` called every stay voxel above z 160 \"crown bore wall\". Between z 160 and 240 "
      "the sleeve holds no crown leg at the long settings (leg bottom z 247-374), and the peak voxel BL-021 reported "
      "(x -103, y -9, z 167) sits on the inboard face 6-7 mm from the lower-branch and lumbar-strut roots. Fixed: that band "
      "is now \"stay L/R lower sleeve z 160-240 (branch / strut root)\"; z 240-470 stays \"crown bore wall\" (h1_sleeve.region "
      "maps both as before; tests pass). The margin is an FI99 over the body, so a single peak voxel does not say where "
      "the governing voxels are: the new `governing_region(cen, fi, ex)` counts the top 1 % by region. "
      f"On {c['name']}, governing set `{gr['set']}`: " + ", ".join(f"{k} {100 * v:.0f} %" for k, v in gr["shares"].items())
      + f"; peak voxel \"{gr['peak_region']}\". `frame_comp_d.evaluate` still reports the peak voxel's label in its "
      "`where` (shared module, not edited: see the report).\n")
    # ---------------- 6 print
    a("## 6. Print files (task 4)\n")
    if res.get("print"):
        p = res["print"]
        a("Written to `designs/pack_5200/print/frame_h1/` from the chosen body (`h1_buckling.export_print`: "
          "frame_h1.print_mesh, then the IM3 eye holes cut exactly at 7.0 mm (ream 7.2), split at z 234, the largest "
          "shell of each part kept, laid flat):\n")
        a("| file | g | footprint mm | shells | watertight | dropped pieces (faces, mm3) | print h |")
        a("|---|---|---|---|---|---|---|")
        for k, fn in (("lower", "h1_lower_flat.stl / .3mf"), ("upper", "h1_upper_flat.stl / .3mf"),
                      ("assembled", "h1_assembled.stl")):
            q = p[k]
            fp = " x ".join(f"{v:.0f}" for v in q.get("footprint_mm", [])) or "frame coordinates"
            a(f"| {fn} | {q['g']:.1f} | {fp} | {q['shells']} | {q['watertight']} | "
              f"{', '.join(f'({f_}, {v:.1f})' for f_, v in q['dropped']) or 'none'} | {q.get('print_h', '')} |")
        big = [(v, w) for (f_, v), w in zip(p["lower"]["dropped"], p["lower"].get("dropped_centre_frame_mm", []))
               if v > 1.0]
        a("")
        for v, w in big:
            a(f"- The lower half's dropped piece ({v / 1000:.2f} cm3, {v * 1.06e-3:.1f} g, centred at frame x {w[0]:.0f}, "
              f"y {w[1]:.0f}, z {w[2]:.0f}) is the loose island BL-015 found, beside the right inboard bolt boss: "
              "in the assembled body it joins the rest only through material above z 234, so the split leaves it "
              "loose in the lower half. In the dry joint it could only rest against the upper half and carries "
              "nothing; it is left out of the print (the 2 mm analysis raster counts it, 0.6 g, conservative for "
              "mass, negligible for stiffness).")
        a("- The assembled body's dropped pieces are boolean slivers of zero volume (BL-015's sliver defect).\n")
    else:
        a("Not written (the body does not pass).\n")
    # ---------------- 7 assumptions
    a("## 7. Assumptions\n")
    allA = dict(ASSUMPTIONS)
    allA["SPREADER_MAP"] = ("BL-021 maps each spreader-contact node force (and the cinch share of it) to the nearest "
                            "frame face node, so the bar and branch nodes take the push under them with no plate "
                            "spreading to the stays (upper bound for the inboard members).",
                            "A Sandwich v2 plate run (huntkit/gendesign/spreader.py) on the H1 supports with the meat "
                            "cinch, reporting the reaction split stays / pucks; or puck load cells in the T2 meat test.")
    allA["HOLE_REAM"] = ("IM3 eye holes printed 7.0 mm and reamed to the 7.2 mm UHMWPE sleeve OD (the bores' 17.4 -> 18.0 "
                         "practice).", "First article: sleeve press-in force by hand, no cracking at the cheek.")
    for k, (txt, test) in allA.items():
        a(f"- ASSUMPTION {k}: {txt} Settled by: {test}")
    a("\n## 8. Screens\n")
    for s in shots:
        a(f"- `{Path(s).relative_to(REPO)}`")
    return "\n".join(L) + "\n"


def report(log=print) -> dict:
    res = compute()
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [plot_decomposition(res, SCREENS / f"{SHOT}1.png"), plot_sizing(res, SCREENS / f"{SHOT}2.png"),
             plot_body(res, SCREENS / f"{SHOT}3.png")]
    if res.get("print"):
        shots.append(plot_print(res, SCREENS / f"{SHOT}4.png"))
    res["screens"] = shots
    slim = copy.deepcopy(res)
    RESULTS.write_text(json.dumps(slim, indent=1, default=_np_default))
    DOC.write_text(write_md(res, shots))
    if log:
        log(f"wrote {DOC} and {RESULTS}; screens {shots}")
    return res


def run_all(log=print):
    task1()
    sizing(log=log)
    dm, du = CHOSEN
    full_check(f"{cand_name(dm, du)}_im3", final_solid(dm, du), log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true", help="run every missing solve (cached)")
    ap.add_argument("--export", action="store_true", help="write the print files for the chosen body")
    a = ap.parse_args(argv)
    if a.run:
        run_all()
    if a.export:
        export_print(*CHOSEN)
    report()


if __name__ == "__main__":
    main()
