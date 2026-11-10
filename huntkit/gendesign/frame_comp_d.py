"""Frame competition, team D (SERVICE): the branch body printed by an industrial powder-bed service.

Record: designs/pack_5200/analysis/frame_comp_d.md, research docs/research/frame_comp_d.md, results
designs/pack_5200/frame_comp/D/. Rules: designs/pack_5200/frame_comp/RULES.md.

Method (same engine and load path as the rev C release check, ``rev_c_verification``):
- every HA-LS-1 rev C set (27 crown-bar + 15 IM3-couple sets, torsos 15/19/23) from the frame.yaml beam model
  (``rev_c_verification.beam_runs``), applied to the 2 mm voxel body (``spreader_layout.raster``);
- the voxel stresses do not depend on E (the loads are applied forces), so one solve per geometry gives the stress
  field and any material's failure index is evaluated on it;
- failure rules: PAHT-CF FDM keeps the release rule (``frame_topopt.layer_failure_index``, layer normal y);
  isotropic powder-bed nylon (MJF PA11 / PA12) uses von Mises / (knock x strength); SLS PA12-CF uses an
  orthotropic Tsai-Hill in the frame plane (fibres along the recoater = frame z) plus through-thickness checks;
- FI99 rule, fatigue and creep from C1 exactly as ``frame_cg_recheck.summarize_body``;
- re-sizing for the service material: fully-stressed SDF offset. Where the smoothed utilisation U > 1/target the
  surface moves out by r (U^(1/3) - 1) (round section in bending), where U is low it moves in (capped at 0.3 r, as
  weight_c C-9), functional surfaces (bores, sleeves, pawl, pivot, pads, spine channel) never move in.
New code lives only here (RULES.md rule 2).
"""
from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

TEAM_DIR = REPO_ROOT / "designs" / "pack_5200" / "frame_comp" / "D"
SCRATCH = REPO_ROOT / "outputs" / "frame_comp_d"
FAT_G = 1.6

# ------------------------------------------------------------------------------------------------ materials
# Every number traces to docs/research/frame_comp_d.md (URL per property) or is an ASSUMPTION listed there.
AVANZINI = {  # Avanzini et al., Int J Fatigue 2022, MJF PA12 smooth specimens, R ~ 0.05, 5 Hz, RT
    "A": 44.0, "B": -0.034, "T106": 1.84, "uts_test": 50.9,
    "url": "https://iris.unibs.it/bitstream/11379/556537/1/PA12%20fatigue%20-%20IJF%20-%20Revision01%20-%2020220405%20-%20IRIS.pdf"}


def basquin_smax(N: float, A: float = AVANZINI["A"], B: float = AVANZINI["B"]) -> float:
    """Mean Smax (MPa) at N cycles, Avanzini 2022 eq. (5)."""
    return A * N ** B


def fatigue_lower_bound(N: float = 1e5) -> float:
    """Lower confidence limit: mean / sqrt(T) with T = UCL/LCL scatter index (Avanzini Tab. 2)."""
    return basquin_smax(N) / np.sqrt(AVANZINI["T106"])


MATERIALS = {
    "paht_fdm": {"label": "PAHT-CF FDM (today)", "rule": "layer", "rho": 1060.0, "E": 3860.0, "s_xy": 88.0,
                 "s_z": 47.0, "knock": 0.8, "fat": 0.30, "rup": 0.40, "usd_g": None},
    # MJF PA12: datasheet 48 MPa XY = Z (HP), fatigue ratio from the Avanzini lower bound at 1e5 / 48
    "pa12_mjf": {"label": "MJF PA12 (HP 3D HR)", "rule": "iso", "rho": 1010.0, "E": 1700.0, "s": 48.0,
                 "knock": 0.8, "fat": None, "rup": 0.35, "usd_g": 0.275},
    # MJF PA11: 52 XY / 50 Z (HP TDS, JLC3DP page); design on 50 isotropic; PA12 fatigue data used in absolute
    # MPa (ASSUMPTION: Salazar 2014 found SLS PA11 >= PA12 in fatigue, so the PA12 curve is conservative)
    "pa11_mjf": {"label": "MJF PA11 (HP 3D HR)", "rule": "iso", "rho": 1050.0, "E": 1800.0, "s": 50.0,
                 "knock": 0.8, "fat": None, "rup": 0.35, "usd_g": 0.30},
    # SLS PA12-CF (Protolabs sheet 85 x / 55 y / 45 z). Recoat x = frame z (stays), y = frame x, build z = frame y
    "pa12cf_sls": {"label": "SLS PA12-CF (Protolabs class)", "rule": "ortho", "rho": 1100.0, "E": 7900.0,
                   "X": 85.0, "Y": 55.0, "Z": 45.0, "S": 30.0, "knock": 0.8, "fat": 0.30, "rup": 0.40,
                   "usd_g": 0.60},
}
for _k in ("pa12_mjf", "pa11_mjf"):
    MATERIALS[_k]["fat"] = round(fatigue_lower_bound(1e5) / MATERIALS[_k]["s"], 3)


# ------------------------------------------------------------------------------------------------ failure rules
def fi_iso(S: np.ndarray, s: float, knock: float) -> np.ndarray:
    """von Mises / (knock s). S columns: sxx, syy, szz, txy, tyz, tzx."""
    sx, sy, sz, txy, tyz, tzx = (S[:, i] for i in range(6))
    vm = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + tyz ** 2 + tzx ** 2))
    return vm / (knock * s)


def fi_ortho(S: np.ndarray, X: float, Y: float, Z: float, Ssh: float, knock: float) -> np.ndarray:
    """SLS PA12-CF laid flat: Tsai-Hill in the frame plane (1 = frame z, X; 2 = frame x, Y; shear tzx, Ssh),
    through-thickness (frame y) normal / Z and interlayer shear (txy, tyz) / (0.6 Z)."""
    s1, s2, t12 = S[:, 2], S[:, 0], S[:, 5]
    th = np.sqrt(np.maximum((s1 / X) ** 2 - s1 * s2 / X ** 2 + (s2 / Y) ** 2 + (t12 / Ssh) ** 2, 0.0))
    tn = np.abs(S[:, 1]) / Z
    tl = np.maximum(np.abs(S[:, 3]), np.abs(S[:, 4])) / (0.6 * Z)
    return np.maximum.reduce([th, tn, tl]) / knock


def fi_material(S: np.ndarray, m: dict) -> np.ndarray:
    from . import frame_topopt as ft
    if m["rule"] == "iso":
        return fi_iso(S, m["s"], m["knock"])
    if m["rule"] == "ortho":
        return fi_ortho(S, m["X"], m["Y"], m["Z"], m["S"], m["knock"])
    return ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, m["s_xy"], m["s_z"], m["knock"])


# ------------------------------------------------------------------------------------------------ loads + solve
def load_sets(cache: Path = SCRATCH / "revc_sets.pkl", log=print):
    """rev C load sets (both couple variants), cached (the beam model does not depend on the body material)."""
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    from . import rev_c_verification as V
    sets, rows = V.beam_runs(buckling=False, log=log)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps((sets, rows)))
    return sets, rows


def solve_fields(dom, solid, sets, sections: bool = False, log=print) -> dict:
    """One factorization; element stresses (float32) per set, exclusion mask (clamp / load-patch elements, as
    verify_sets), optional z 234 section resultants."""
    from . import frame_topopt as ft
    t0 = time.time()
    g = dom.grid
    idx = np.where(solid)[0]
    _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    clamp = np.zeros(g.nn, bool)
    clamp[np.where(fixed[0::3])[0]] = True
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(g.h, 1.0, ft.NU))
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    K.sort_indices()
    import pypardiso
    solver = pypardiso.PyPardisoSolver(mtype=2)
    solver.factorize(K)
    tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
    stress, ex_all, meta, secs = [], {}, [], {}
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
            if sections:
                secs[s.key] = ft.section_resultants(dom, solid, U[:, k], 234.0, E=1.0)
        if log:
            log(f"    voxel [{tg}] {len(tsets)} sets, {time.time() - t0:.0f} s")
    try:
        solver.free_memory(everything=True)
    except Exception:
        pass
    return {"stress": stress, "meta": meta, "ex": ex_all, "idx": idx, "cen": g.elem_centers()[idx],
            "sections": secs, "seconds": time.time() - t0}


def evaluate(fields: dict, mat: str) -> dict:
    """Rows per set (FI99 rule) + body margins (strength, fatigue, creep per couple variant) + per-voxel
    utilisation (max of strength FI, fatigue FI at 1.6 g / ratio, creep FI at 1 g / ratio)."""
    from . import frame_cg_recheck as R
    m = MATERIALS[mat]
    rows = []
    n = fields["idx"].size
    env, fat, rup = np.zeros(n), np.zeros(n), np.zeros(n)
    exu = np.zeros(n, bool)
    for S, mt in zip(fields["stress"], fields["meta"]):
        ex = fields["ex"][mt["scenario"]]
        exu |= ex
        fi = fi_material(S.astype(float), m)
        ok = fi[~ex]
        fi99 = float(np.percentile(ok, 99))
        pk = np.where(~ex)[0][np.argmax(ok)]
        rows.append({**mt, "fi99": fi99, "sf": 1.0 / max(fi99, 1e-9),
                     "where": R.region_label(fields["cen"][pk]), "peak_xyz": [float(v) for v in fields["cen"][pk]]})
        fz = np.where(ex, 0.0, fi)
        env = np.maximum(env, fz)
        if mt["case"] == "static_carry":
            fat = np.maximum(fat, fz * (FAT_G / mt["factor"]) / m["fat"])
            rup = np.maximum(rup, fz / mt["factor"] / m["rup"])
    body = {}
    for tg in dict.fromkeys(r["scenario"] for r in rows):
        b = R.summarize_body(rows, tg, m["fat"], m["rup"])
        body[tg] = {"strength": b["sf_min"], "governing": b["governing"], "where": b["where"],
                    "fatigue": b["sf_fatigue"], "creep": b["sf_creep"], "fatigue_set": b.get("fatigue_set"),
                    "cases": {c: round(v["sf"], 3) for c, v in b["cases"].items()}}
    mins = {k: min(v[k] for v in body.values()) for k in ("strength", "fatigue", "creep")}
    gov = min(body.items(), key=lambda kv: min(kv[1]["strength"], kv[1]["fatigue"], kv[1]["creep"]))
    return {"material": mat, "rows": rows, "body": body, "min": mins,
            "governing": f"{gov[0]}:{gov[1]['governing']}" if gov[1]["strength"] <= min(gov[1]["fatigue"], gov[1]["creep"])
            else f"{gov[0]}:{gov[1]['fatigue_set']} (fatigue)",
            "util": np.maximum.reduce([env, fat, rup]), "env": env, "fat": fat, "ex": exu}


# ------------------------------------------------------------------------------------------------ resizing
R_FRAC = 0.30        # never remove more than 30 % of the local radius (weight_c C-9 rule)
SMOOTH_MM = 6.0      # ASSUMPTION: utilisation max-filtered over 6 mm before the offset
U_LO = 0.45          # ASSUMPTION: thin only where the smoothed utilisation is below 0.45 x the target level


def _keep_mask(dom):
    from scipy import ndimage
    g = dom.grid
    keep = np.zeros(g.ne, bool)
    for k, msk in dom.masks.items():
        if k.startswith(("sleeve_", "bore_")) or k in ("pawl", "pivot", "pads", "spine_channel"):
            keep |= np.asarray(msk, bool)
    return g.from_array(ndimage.binary_dilation(g.to_array(keep), iterations=2))


def offset_step(dom, sdf0, solid, util, shift, target: float = 1.04, grow_only: bool = False, u_lo: float = U_LO):
    """One fully-stressed update of the cumulative surface shift (mm, + = outward)."""
    from scipy import ndimage
    g = dom.grid
    U = np.zeros(g.ne)
    U[np.where(solid)[0]] = util * target
    r = max(1, int(round(SMOOTH_MM / g.h)))
    Us = g.from_array(ndimage.maximum_filter(g.to_array(U), size=2 * r + 1))
    depth = g.from_array(ndimage.maximum_filter(g.to_array(np.maximum(-sdf0, 0.0)),
                                                size=2 * int(round(10.0 / g.h)) + 1))
    rad = np.maximum(depth, g.h)
    grow = np.where(Us > 1.0, rad * (np.cbrt(np.maximum(Us, 1.0)) - 1.0), 0.0)
    thin = np.where((Us < u_lo) & (Us > 0), rad * (1.0 - np.cbrt(Us / u_lo)) * 0.5, 0.0)
    if grow_only:
        thin[:] = 0.0
    new = shift + np.minimum(grow, 3.0) - thin           # at most 3 mm outward per step
    new = np.maximum(new, -R_FRAC * rad)
    new[_KEEP_CACHE.setdefault(id(dom), _keep_mask(dom)) & (new < 0)] = 0.0
    new[dom.passive_solid | dom.passive_void] = 0.0
    return new


_KEEP_CACHE: dict = {}


def solid_from_shift(dom, sdf0, shift):
    from . import frame_production as prod
    solid = ((sdf0 - shift) <= 0.0) | dom.passive_solid
    solid &= ~dom.passive_void
    return prod._largest_with_pivot(dom, solid)


def mass_g(solid, h: float, rho: float) -> float:
    return float(solid.sum() * h ** 3 * rho / 1e6)


def torsion_k(dom, solid, sets, E: float) -> float:
    from . import frame_topopt as ft
    return float(ft.stiffness_tests(dom, solid, E=E, sets=sets)["torsion_Nm_per_deg"])


FAT_KEEP = 1.02      # ASSUMPTION (as weight_c C9_FAT_KEEP): keep >= 2 % margin for 2 mm voxel / FI99 noise


def resize(mat: str, iters: int = 4, target: float = 1.04, log=print, u_lo: float = U_LO) -> dict:
    """Fully-stressed re-sizing of the branch body for ``mat``. Returns the history and the last passing body."""
    from .spreader import SCALE
    from .spreader_layout import frame_sdf_layout, raster
    sets, _ = load_sets(log=log)
    dom, solid0 = raster(None, 2.0)
    sdf0 = frame_sdf_layout(dom.grid.elem_centers(), None, SCALE)
    shift = np.zeros(dom.grid.ne)
    solid = solid0
    hist, best = [], None
    rho = MATERIALS[mat]["rho"]
    for it in range(iters + 1):
        f = solve_fields(dom, solid, sets, log=None)
        ev = evaluate(f, mat)
        rec = {"iter": it, "body_g": mass_g(solid, 2.0, rho), "min": ev["min"], "governing": ev["governing"],
               "n_vox": int(solid.sum())}
        hist.append(rec)
        if log:
            log(f"  [{mat}] it {it}: {rec['body_g']:.0f} g, strength {ev['min']['strength']:.3f}, fatigue "
                f"{ev['min']['fatigue']:.3f}, creep {ev['min']['creep']:.3f}")
        ok = min(ev["min"].values()) >= FAT_KEEP
        if ok and (best is None or rec["body_g"] < best["body_g"]):
            best = {**rec, "shift": shift.copy(), "solid": solid.copy(), "eval": ev}
        if it == iters:
            break
        shift = offset_step(dom, sdf0, solid, ev["util"], shift, target, grow_only=False, u_lo=u_lo)
        solid = solid_from_shift(dom, sdf0, shift)
    return {"material": mat, "history": hist, "best": best, "dom": dom, "solid0": solid0, "sdf0": sdf0, "sets": sets}


# ------------------------------------------------------------------------------------------------ joints
JOINT = {"bolts_per_stay": 2, "d_mm": 5.0, "lap_t_mm": 11.0, "bearing_ratio": 1.0, "lever_mm": 24.0}


def split_joint(sections: dict, mat: str, meta: list) -> dict:
    """Bolted half-lap across z 234 (the build volume forces the split, 370 x 276 x 360 mm MJF): per stay
    2 x M5 through-bolts, 11 mm lap leg. Bolt force = the release flange force |N|/2 + M/24 (same rule as the
    dowel joint, frame_cg_recheck.segment_joint) + shear / 2; PA bearing capacity = ratio x knock x s x d x t
    (ASSUMPTION ratio 1.0, coupon J1). Fatigue: C1 x 1.6/2.0 against fat x capacity."""
    m = MATERIALS[mat]
    s = m.get("s", m.get("Y", 50.0))
    cap = JOINT["bearing_ratio"] * m["knock"] * s * JOINT["d_mm"] * JOINT["lap_t_mm"]
    fac = {r["set"]: r for r in meta}
    worst, worst_f = (9e9, None), (9e9, None)
    for key, sec in sections.items():
        for side, r in sec.items():
            M = float(np.hypot(r["Mx"], r["My"]))
            F = abs(r["N"]) / 2 + M / JOINT["lever_mm"] + float(np.hypot(r["Vx"], r["Vy"])) / 2
            sf = cap / max(F, 1e-9)
            if sf < worst[0]:
                worst = (sf, f"{key} {side}")
            mt = fac.get(key)
            if mt and mt["case"] == "static_carry":
                sff = m["fat"] * cap / max(F * FAT_G / mt["factor"], 1e-9)
                if sff < worst_f[0]:
                    worst_f = (sff, f"{key} {side}")
    from .frame_production import cheek_check
    # pawl cheek: release factored pawl force (rev_c_verification.md section 3), isotropic -> s_xy = s_z = s
    pawl = cheek_check((0.0, 2156.0, 850.0), 8.0, 8.0, True, pin_d=4.2, s_xy=s, s_z=s, knock=m["knock"], E=m["E"])
    pawl12 = cheek_check((0.0, 2156.0, 850.0), 8.0, 12.0, True, pin_d=4.2, s_xy=s, s_z=s, knock=m["knock"], E=m["E"])
    return {"bolt_bearing_cap_n": cap, "joint_sf": worst[0], "joint_set": worst[1], "joint_fatigue_sf": worst_f[0],
            "joint_fatigue_set": worst_f[1], "pawl_cheek_8mm_sf": 1.0 / pawl["fi99"],
            "pawl_cheek_12mm_sf": 1.0 / pawl12["fi99"]}


def joint_design(sections: dict, mat: str, meta: list, n_rows: int = 2, per_row: int = 2, pitch: float = 40.0,
                 t: float = 14.0, d: float = 5.0) -> dict:
    """Bolted half-lap across z 234, per stay ``n_rows`` x ``per_row`` bolts, rows ``pitch`` apart along z (the
    bending moment is a bolt-row couple M / pitch), lap leg ``t``. Bolt force = (|N| / n_rows + M / pitch) / per_row
    + V / (n_rows per_row), conservative sum. PA bearing capacity knock x s x d x t (ASSUMPTION ratio 1.0, D-J1).
    Fatigue at 1.6 g from C1 against fat x capacity."""
    m = MATERIALS[mat]
    s = m.get("s", m.get("Y", 50.0))
    cap = m["knock"] * s * d * t
    fac = {r["set"]: r for r in meta}
    w, wf = (9e9, None), (9e9, None)
    for key, sec in sections.items():
        for side, r in sec.items():
            M = float(np.hypot(r["Mx"], r["My"]))
            F = (abs(r["N"]) / n_rows + M / pitch) / per_row + float(np.hypot(r["Vx"], r["Vy"])) / (n_rows * per_row)
            if cap / F < w[0]:
                w = (cap / F, f"{key} {side}", F)
            mt = fac.get(key)
            if mt and mt["case"] == "static_carry":
                ff = m["fat"] * cap / max(F * FAT_G / mt["factor"], 1e-9)
                if ff < wf[0]:
                    wf = (ff, f"{key} {side}")
    return {"rows": n_rows, "per_row": per_row, "pitch": pitch, "t": t, "d": d, "cap_n": cap, "sf": w[0],
            "set": w[1], "bolt_n": w[2], "sf_fatigue": wf[0], "fatigue_set": wf[1]}


# ------------------------------------------------------------------------------------------------ cost
def service_cost(body_g: float, mat: str) -> dict:
    """USD per frame at 1 / 10 / 100. Print at the JLC3DP per-gram rate (no quantity break published:
    ASSUMPTION the same rate at 10; 100 at -15 % (ASSUMPTION, volume quote)), + shipping ASSUMPTION $30 / order
    split over the units, + today's non-printed frame hardware (PRODUCTION.md unit cost minus filament, machine,
    reprint and dowels) + bolts/inserts for the split joint $4 (ASSUMPTION)."""
    usd_g = MATERIALS[mat]["usd_g"]
    hardware = 427.0 - 71.1 - 10.7 - 27.4 - 4.5 - 207.2 + 4.0   # frame without spreader, hardware only
    out = {}
    for q, disc in ((1, 1.0), (10, 1.0), (100, 0.85)):
        out[str(q)] = round(body_g * usd_g * disc + 30.0 / q + hardware + 207.2, 0)
    out["_basis"] = {"print_usd_g": usd_g, "hardware_usd": round(hardware, 1), "spreader_usd": 207.2}
    return out


# ------------------------------------------------------------------------------------------------ main study
BASE = {"frame_g": 1063.0, "body_g": 823.0, "spreader_g": 162.3, "fps_g": 1225.0, "corrie_m": 3964.5}
# NOTE: frame_plus_spreader 1225 is the RULES baseline (1063 + 162 rounded in PRODUCTION.md)


def run(log=print, iters: int = 4) -> dict:
    from .spreader_layout import raster
    t0 = time.time()
    sets, _ = load_sets(log=log)
    dom, solid0 = raster(None, 2.0)
    f0 = solve_fields(dom, solid0, sets, log=log)
    same = {k: {kk: vv for kk, vv in evaluate(f0, k).items() if kk in ("min", "governing", "body")}
            for k in MATERIALS}
    for k in MATERIALS:
        same[k]["body_g"] = mass_g(solid0, 2.0, MATERIALS[k]["rho"])
    k_base = torsion_k(dom, solid0, sets, MATERIALS["paht_fdm"]["E"])
    if log:
        for k, v in same.items():
            log(f"  same geometry {k}: {v['body_g']:.0f} g {v['min']}")
    out = {"date": "2026-11-10", "same_geometry": same, "torsion_base_nm_deg": k_base, "resized": {}}
    for mat in ("pa11_mjf", "pa12_mjf"):
        rz = resize(mat, iters=iters, log=log)
        b = rz["best"]
        entry = {"history": rz["history"]}
        if b is not None:
            fs = solve_fields(dom, b["solid"], sets, sections=True, log=None)
            entry.update({"body_g": b["body_g"], "min": b["min"], "governing": b["governing"],
                          "body": b["eval"]["body"],
                          "torsion_rel": torsion_k(dom, b["solid"], sets, MATERIALS[mat]["E"]) / k_base,
                          "joint": split_joint(fs["sections"], mat, fs["meta"]),
                          "added_g": mass_g(b["solid"] & ~solid0, 2.0, MATERIALS[mat]["rho"]),
                          "removed_g": mass_g(solid0 & ~b["solid"], 2.0, MATERIALS[mat]["rho"])})
            np.savez_compressed(SCRATCH / f"{mat}_best.npz", solid=b["solid"], util=b["eval"]["util"],
                                shift=b["shift"])
        out["resized"][mat] = entry
    out["seconds"] = time.time() - t0
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "study.json").write_text(json.dumps(out, indent=1, default=float))
    return out


if __name__ == "__main__":
    run()


def run2(log=print, mats=("pa11_mjf", "paht_fdm"), iters: int = 6, u_lo: float = 0.70) -> dict:
    """Second pass: deeper thinning (u_lo 0.70) for the chosen service material and, as the fair control, the
    same tool on today's PAHT-CF (so the gain from re-sizing is not booked as a gain from the material)."""
    from .spreader_layout import raster
    sets, _ = load_sets(log=log)
    dom, solid0 = raster(None, 2.0)
    k_base = torsion_k(dom, solid0, sets, MATERIALS["paht_fdm"]["E"])
    out = {"u_lo": u_lo, "iters": iters, "resized": {}}
    for mat in mats:
        rz = resize(mat, iters=iters, log=log, u_lo=u_lo)
        b = rz["best"]
        entry = {"history": rz["history"]}
        if b is not None:
            fs = solve_fields(dom, b["solid"], sets, sections=True, log=None)
            joints = [joint_design(fs["sections"], mat, fs["meta"], nr, pr, pitch, t)
                      for nr, pr, pitch, t in ((1, 2, 24.0, 11.0), (2, 2, 40.0, 14.0), (2, 2, 50.0, 16.0),
                                               (3, 2, 30.0, 16.0), (2, 3, 50.0, 16.0))]
            entry.update({"body_g": b["body_g"], "min": b["min"], "governing": b["governing"],
                          "body": b["eval"]["body"],
                          "torsion_rel": torsion_k(dom, b["solid"], sets, MATERIALS[mat]["E"]) / k_base,
                          "joints": joints, "pawl": split_joint(fs["sections"], mat, fs["meta"]),
                          "added_g": mass_g(b["solid"] & ~solid0, 2.0, MATERIALS[mat]["rho"]),
                          "removed_g": mass_g(solid0 & ~b["solid"], 2.0, MATERIALS[mat]["rho"])})
            np.savez_compressed(SCRATCH / f"{mat}_run2_best.npz", solid=b["solid"], util=b["eval"]["util"],
                                shift=b["shift"])
        out["resized"][mat] = entry
        (SCRATCH / "study2.json").write_text(json.dumps(out, indent=1, default=float))
    return out
