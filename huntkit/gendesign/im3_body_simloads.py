"""BL-021: the IM3 eye and the H1 frame body on the cloth-sim loads, with margin for scatter.

    python -m huntkit.gendesign.im3_body_simloads            # frozen solver results -> md / json / png
    python -m huntkit.gendesign.im3_body_simloads --fea      # re-run the eye FEA (h 1.0 / 0.8 / 0.7 mm)
    python -m huntkit.gendesign.im3_body_simloads --body     # re-run the H1 body check on the sim loads

What it does (ticket docs/backlog/BL-021-im3-and-body-on-sim-loads.md):
1. The IM3 bag-hook force **vector** per side from CORRIE F's 15 in meat case, coarse (h 40) and fine (h 25) cloth
   mesh. The sim reports a hook's tension as the scalar sum of its bridle legs; the vector is rebuilt here from the
   saved node positions (each leg: T x unit(bag node - eye)), and the leg sum is checked against the report.
2. That vector plus the rev C IM3 meat-strap force on the same eye (vector sum, both at full value) on the printed
   fairlead FEA, with the load applied in its own direction (bag_attach.solve_fairlead's contact patch rule, plus
   the lateral part on the cheek's inner face). One factorisation per grid serves every load direction. Mesh study
   at h 1.0 / 0.8 / 0.7 mm; the design FI is the largest of the three (see ``converged``).
3. The H1 body check (crown_diet.body_check, BL-017 per-torso basis) with the bag cases' loads taken from the
   cloth sim (hinge pins, IM3 hooks, guys, spreader / frame / crown contact, under-straps, wraps) in place of the
   beam bag weight split and couple.
4. BL-007 (a) / (c) and BL-017 (c17, OD 17 legs) restated per torso, on the beam and on the sim loads.
5. CA-1 flip points (fatigue ratio at which each part reaches 1.0) for the final body and cheek.

Shared modules are not edited: the beam load placement and the fairlead geometry are swapped in for the duration
of a call and restored (as loadpath_check / corrie_f_sim do). Units: N, mm, g, MPa.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "im3_body_simloads.json"
DOC = ANALYSIS / "im3_body_simloads.md"
SIMDIR = REPO / "outputs" / "clothsim" / "corrie_f"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261111_BL021_"
OUT = REPO / "outputs" / "im3_body_simloads"

G_WALK = 1.6               # fatigue: 1e5 cycles 0 -> 1.6 g (HA-LS-1 rev C)
FACTOR = 3.0               # rev C C5 / C2: 2.0 g x 1.5 on a 1 g force
FAT_REQ = 1.15             # BL-021 target: fatigue >= 1.15 on the sim loads (covers input scatter)
STR_REQ = 1.5              # BL-021: strength >= 1.5 at the factored load
EYE_STATION = 520.0
GRIDS = (1.0, 0.8, 0.7)    # BL-014: h 0.5 ran out of memory; stay >= 0.7

ASSUMPTIONS = {
    "STAY_LOCAL": ("The stay is vertical at z 520, so the sim's global (x, y, z) force is the fairlead's local (pin, "
                   "aft, up) force, as bag_attach / float_fea / loadpath_check use it.",
                   "H1 STL: stay tangent at z 520 within 5 deg of vertical (read off the print file before R1)."),
    "COMBINE": ("Worst rev C combination on one eye: the sim bag-hook vector and the rev C C5 IM3 meat-strap vector "
                "both at full value and added as vectors. This counts the meat weight twice (the sim hangs all of "
                "it on the bag, rev C puts 30 % of it and the overturning on the straps): an upper bound.",
                "IM3 eye pull with both carabiners in the throat, the strap pulled aft and the hook pulled down at "
                "the same time (first frame)."),
    "LATERAL": ("The lateral (pin-axis) part of the hook pull bears on the inner face of one cheek, spread over "
                "the face within one hole diameter of the hole centre.",
                "Same eye pull as COMBINE, with the hook 10 deg off the stay plane."),
    "DIR_SCATTER": ("The combined hook + strap pull on the eye may sit up to 10 deg further aft than computed (the 18 sim "
                    "hook vectors spread 2-8 deg aft; the strap angle at the eye is rev C's, not measured). The cheek "
                    "must keep fatigue >= 1.15 at the computed angle + 10 deg.",
                    "IM3 eye pull test with the strap led aft at the measured hunting angle (first frame), or a "
                    "protractor reading of the strap and hook angles in the T2 meat test."),
    "PAHT_FAT": ("PAHT CF fatigue_1e5_ratio 0.30 (record ASSUMPTION, no published data).",
                 "CA-1 coupon test (TEST_PLAN): the flip points in section 5 say what each part needs."),
    "SIM_BODY": ("Bag cases on the body: the sim's 1 g frame-side forces scaled by g x load / 68 kg; side-hill "
                 "keeps the beam's lateral and downhill part, the upright part is replaced by the sim x cos 25 deg. "
                 "The set is closed on the payload weight at the sim's CG: the force left over (under-straps, W "
                 "straps, doublers and fabric the extraction does not map: 67-96 N, 10-14 % of the weight) goes to "
                 "the four under-strap pins, and the sagittal moment left over to a fore-aft couple between the IM3 "
                 "hook and hinge nodes (-38 to +201 N).",
                 "T9 loaded CG + frame strain gauges at the stays z 450-550 in the T1 carry test."),
    "CINCH_STATIC": ("The meat straps' cinch (rev C 150 N per strap, the sim's meat-face push) is a static preload "
                     "set at the kill site: it is in every strength and creep set but does not cycle with the "
                     "walking g, so it is left out of the static-carry set that gives fatigue. The bound with the "
                     "cinch cycling is reported beside it.",
                     "MT-1 strap tension readout over a 10 min loaded walk in the T2 meat test (amplitude of the "
                     "strap tension against its mean)."),
    "SETDOWN_BEAM": ("The single-stay set-down keeps the beam's lumped bag masses (inertia relief through one "
                     "foot); it does not enter fatigue.", "T5 drop / set-down test."),
    "STRAP_REACT": ("Meat case in the sim: the meat-face push is reacted at the six IM anchors: the overturning "
                    "share per level and 30 % of the meat weight as in rev C, and the cinch loop (the spreader push "
                    "it causes) by strap pulls at the three levels that balance that push in force AND moment (the "
                    "meat bundle is in equilibrium), as near an equal split as that allows. The sim's push sits low "
                    "(z 220-230), so the cinch goes almost all to IM1 (z 190).",
                    "MT-1 strap tension readout in the T2 meat test."),
}


def _paht() -> dict:
    from huntkit.gendesign import bag_attach as BA
    return BA._paht()


# ======================================================================================= 1. sim hook vectors
def _sim_install():
    sys.path.insert(0, str(PACK / "concepts" / "corrie_f_sim"))
    sys.path.insert(0, str(PACK / "concepts"))
    import corrie_f_sim as S
    return S


def frame_forces_from_run(run: str, torso: int, case: str = "meat", fine: bool | None = None) -> dict:
    """Frame-side 1 g forces of one CORRIE F sim (outputs/clothsim/corrie_f/<run>), rebuilt from the saved node
    positions: every cable with a fixed anchor (hooks, guys, under-straps, wraps) gives T x unit(bag node - anchor)
    at its anchor; the hinge pins and the three contact fields give minus their force on the bag. Checks the leg
    sums against the run's own report."""
    S = _sim_install()
    from huntkit.clothsim.pack import PackModel, load_scenario
    rd = SIMDIR / run
    rj = json.loads((rd / "results.json").read_text())
    if fine is None:
        fine = float(rj["mesh"]["h_mm"]) < 40.0
    S.install(None)
    try:
        scen = Path(rj.get("scenario_file") or S.scenario_path(torso))      # the run's own scenario (rev 0 or rev 1)
        pm = PackModel(load_scenario(str(scen)), fine=fine, verbose=False)
        cdef = dict(pm.scen["cases"][case])
        if cdef.get("contents_L") == "auto":
            cdef["contents_L"] = rj["cases"][case]["inputs"]["contents_L"]
        sim = pm.build_sim(cdef, cinched=True)
    finally:
        S.uninstall()
    x = np.load(rd / f"x_{case}.npy")
    rep = rj["cases"][case]["attachments"]
    anchors: dict = {}
    groups: dict = {}
    for name, c in pm.cables.items():
        if c.kind == "hinge":
            continue
        P = c.points(x)
        T = c.tension(x)
        if T <= 1e-9:
            continue
        for i in np.where(c.nodes < 0)[0]:
            j = i + 1 if i + 1 < len(P) else i - 1
            u = P[j] - P[i]
            u = u / max(np.linalg.norm(u), 1e-9)
            key = name.split(".")[0]
            a = anchors.setdefault(key, {"xyz": [float(v) for v in P[i]], "f": np.zeros(3), "kind": c.kind})
            a["f"] = a["f"] + T * u
        groups.setdefault(name.split(".")[0], 0.0)
        groups[name.split(".")[0]] += T
    # cinched straps were re-set on the loaded shape in the run; their report is the reference
    out = {}
    for k, a in anchors.items():
        f = a["f"]
        if a["kind"] in ("wrap", "under_strap", "roll_clip") and k in rep and groups[k] > 0:
            f = f * float(rep[k]["tension_n"]) / groups[k]
        out[k] = {"xyz": a["xyz"], "f": [float(v) for v in f], "kind": a["kind"],
                  "leg_sum_n": float(rep.get(k, {}).get("tension_n", groups[k])), "rebuilt_sum_n": float(groups[k])}
    for side in "RL":
        h = rep[f"hinge_{side}"]
        hn = pm.hinge_nodes[0 if side == "R" else 1]
        out[f"hinge_{side}"] = {"xyz": [float(v) for v in pm.mesh.X0[hn]], "f": [-float(v) for v in h["force_xyz_n"]],
                                "kind": "hinge"}
    sig = rj["cases"][case].get("contact_rounding_mm")
    sig = float(pm.scen["contact"].get("smooth_mm", 0.0) or 0.0) if sig is None else float(sig)
    from huntkit.clothsim.pack import FieldContact
    for t in sim.terms:
        nm = str(getattr(t, "name", ""))
        if isinstance(t, FieldContact) and nm.startswith("contact_"):
            # the run reports its LAST contact-rounding stage: evaluate the contact on that same field
            k = nm[len("contact_"):]
            if k in pm.fields_raw:
                t.f = pm.fields_raw[k] if sig <= 0 else pm.fields_raw[k].smoothed(sig)
        if nm.startswith("contact_"):
            idx, fb = t.forces(x)            # force on the bag nodes (the run's report uses the same call)
            idx, fb = np.asarray(idx), np.asarray(fb, float).reshape(-1, 3)
            if idx.size == 0:
                continue
            xm = x[idx]
            F = fb.sum(0)
            w = np.linalg.norm(fb, axis=1)
            cen = (xm * w[:, None]).sum(0) / max(w.sum(), 1e-12)
            out[nm] = {"xyz": [float(v) for v in cen], "f": [-float(v) for v in F], "kind": "contact",
                       "z_lo": float(xm[:, 2].min()), "z_hi": float(xm[:, 2].max()),
                       "node_f": [[float(v) for v in xx] + [-float(v) for v in ff] for xx, ff in zip(xm, fb)]}
    meat = rj["cases"][case].get("meat") or {}
    rep_c = rj["cases"][case].get("contact", {})
    for nm in list(out):
        if nm.startswith("contact_") and nm in rep_c:
            out[nm]["report_force_n"] = rep_c[nm]["force_n"]
    vol = rj["cases"][case]["volume"]
    cgm = vol.get("cg_with_external_mm", vol.get("contents_cg_mm"))
    return {"run": run, "contact_rounding_mm": sig, "cg_mm": [float(v) for v in cgm] if cgm else None, "scenario": rj.get("scenario", ""), "torso": torso, "case": case, "h_mm": float(rj["mesh"]["h_mm"]),
            "converged": bool(rj["cases"][case]["converged"]), "forces": out,
            "meat": {k: meat[k] for k in ("P_n", "face_n", "overturning_pull_n", "to_strap_anchors_n") if k in meat}}


def hook_vectors(ff: dict) -> dict:
    out = {}
    for side in "RL":
        a = ff["forces"][f"hook_im520_{side}"]
        f = np.asarray(a["f"])
        out[side] = {"vec": [round(float(v), 1) for v in f], "mag": round(float(np.linalg.norm(f)), 1),
                     "leg_sum": round(a["leg_sum_n"], 1), "rebuilt_sum": round(a["rebuilt_sum_n"], 1),
                     "aft_of_down_deg": round(float(np.degrees(np.arctan2(f[1], -f[2]))), 1),
                     "lateral_deg": round(float(np.degrees(np.arctan2(abs(f[0]), np.hypot(f[1], f[2])))), 1)}
    return out


def strap_vector_1g() -> np.ndarray:
    """Rev C C5 IM3 meat-strap force at the eye, per 1 g (rev_c_verification gov_c.im3 / g_times_req)."""
    rc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["im3"]
    return np.array([rc["fx"], rc["fy"], rc["fz"]], float) / float(rc["g_times_req"])


def misuse_1g() -> float:
    """BL-010 IM3 misuse envelope at 1 g (guys-off, CORRIE 15 in): factored 1702.2 N / 3.0."""
    from huntkit.gendesign import loadpath_check as LP
    s = LP.sim_loads()
    return max(v["n_1g"] for k, v in s.items() if k.startswith("im3_"))


# ======================================================================================= 2. eye FEA
def _cheek_inner_nodes(nc, y_hole, side, h):
    from huntkit.gendesign import bag_attach as BA
    x_in = side * BA.THROAT / 2.0
    r = np.hypot(nc[:, 1] - y_hole, nc[:, 2])
    return np.where((np.abs(nc[:, 0] - x_in) <= 0.6 * h) & (r >= BA.HOLE_D / 2.0) & (r <= BA.HOLE_D))[0]


def eye_fea(half_z: float, cheek: float, loads: dict, h: float = 1.0, field: bool = False) -> dict:
    """Printed IM3 fairlead (bag_attach geometry with HALF_Z / CHEEK swapped in) under each 3D force in ``loads``
    (name -> [fx, fy, fz] N, x = pin axis, y = aft toward the bag, z = up the stay). The (y, z) part goes on the
    bearing half of the hole facing it (solve_fairlead's rule); the x part on the inner face of the cheek it
    pushes. One factorisation, one RHS per load. Returns FI99 / FI max per load (FI is linear in the force for a
    fixed direction) and the added mass."""
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign.fem import Grid, ke_h8
    from huntkit.gendesign.frame_topopt import NU, ReducedSystem, element_stress, layer_failure_index
    pa = _paht()
    old = BA.HALF_Z, BA.CHEEK
    BA.HALF_Z, BA.CHEEK = float(half_z), float(cheek)
    try:
        stay_r = 16.8
        y_hole = stay_r + BA.HOLE_PROUD
        zext = max(22.0, half_z + 8.0)
        xext = max(20.0, BA.THROAT / 2 + cheek + 3.0)       # solve_fairlead's box (x +-20) where it fits
        lo = np.array([-xext, -(stay_r + 4.0), -zext])
        hi = np.array([xext, stay_r + BA.HOLE_PROUD + BA.HOLE_D / 2.0 + BA.WALL_FRONT + 4.0, zext])
        n = np.maximum(np.round((hi - lo) / h).astype(int), 6)
        g = Grid(tuple(int(v) for v in n), h, x0=lo)
        c = g.elem_centers()
        stay = (np.hypot(c[:, 0], c[:, 1]) <= stay_r) & (np.abs(c[:, 2]) <= zext - 1.0)
        yoke = BA.fairlead_local(c, stay_r) <= 0.0
        solid = stay | yoke
        nc = g.node_coords()
        radial = np.c_[nc[:, 1] - y_hole, nc[:, 2]]
        rr = np.linalg.norm(radial, axis=1)
        band = (rr > BA.HOLE_D / 2.0 - 0.35 * h) & (rr < BA.HOLE_D / 2.0 + 0.9 * h)
        band &= np.abs(nc[:, 0]) >= BA.THROAT / 2.0 - 0.3
        band &= np.abs(nc[:, 0]) <= BA.THROAT / 2.0 + cheek + 0.6 * h
        end = (np.abs(nc[:, 2]) >= zext - 2.5) & (np.hypot(nc[:, 0], nc[:, 1]) <= stay_r + h)
        fixed = np.zeros(g.ndof, bool)
        ids = np.where(end)[0]
        for d in range(3):
            fixed[3 * ids + d] = True
        names = list(loads)
        F = np.zeros((g.ndof, len(names)))
        for k, nm in enumerate(names):
            f3 = np.asarray(loads[nm], float)
            fyz = f3[1:]
            mag = float(np.linalg.norm(fyz))
            if mag > 1e-9:
                d = fyz / mag
                idx = np.where(band & (radial @ d > 0.15 * BA.HOLE_D / 2.0))[0]
                if idx.size < 6:
                    idx = np.where(band)[0]
                w = np.maximum(radial[idx] @ d, 0.0)
                w = w / w.sum() if w.sum() > 0 else np.ones(idx.size) / idx.size
                F[3 * idx + 1, k] += mag * w * d[0]
                F[3 * idx + 2, k] += mag * w * d[1]
            if abs(f3[0]) > 1e-9:
                side = 1.0 if f3[0] > 0 else -1.0
                # the hook in the throat pushes the cheek on the side it pulls toward: its inner face
                face = _cheek_inner_nodes(nc, y_hole, side, h)
                face = face[np.isin(face, np.unique(g.enodes[solid]))]
                F[3 * face, k] += f3[0] / max(face.size, 1)
        F[fixed] = 0.0
        KE = ke_h8(h, 1.0, NU)
        rs = ReducedSystem(g, solid, fixed, KE)
        U = rs.solve(rs.assemble(np.full(rs.ae.size, 1.0)), F) / pa["E"]
        cc = None
        out = {}
        for k, nm in enumerate(names):
            eidx, S = element_stress(g, U[:, k], solid, pa["E"])
            fi = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, pa["s_xy"], pa["s_z"], pa["knock"])
            if cc is None:
                cc = c[eidx]
                use = (BA.fairlead_local(cc, stay_r) <= h) & (np.abs(cc[:, 2]) < zext - 6.0)
                if int(use.sum()) < 12:
                    use = np.abs(cc[:, 2]) < zext - 6.0
            mag = float(np.linalg.norm(loads[nm]))
            fu = fi[use]
            out[nm] = {"force_n": mag, "fi99": float(np.percentile(fu, 99)), "fi_max": float(fu.max()),
                       "fi99_per_n": float(np.percentile(fu, 99)) / mag, "fi_max_per_n": float(fu.max()) / mag,
                       "peak_xyz": [float(v) for v in cc[use][int(np.argmax(fu))]],
                       "applied_n": float(np.linalg.norm([F[0::3, k].sum(), F[1::3, k].sum(), F[2::3, k].sum()]))}
            if field and k == 0:
                fld = {"xyz": cc.tolist(), "fi": fi.tolist(), "load": nm}
        added = float((yoke & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    finally:
        BA.HALF_Z, BA.CHEEK = old
    r = {"half_z": half_z, "cheek": cheek, "h": h, "added_g": added, "n_elem": int(solid.sum()), "loads": out}
    if field:
        r["field"] = fld
    return r


SWEEP_DEG = (0.0, 15.0, 30.0, 45.0, 60.0, 80.5)     # pull angle aft of straight down (80.5 = rev C IM3 vector)
DIR_SCATTER_DEG = 10.0     # ASSUMPTION DIR_SCATTER: the combined pull may sit this much further aft than computed


def eye_directions(hooks: dict, strap: np.ndarray, misuse_n: float) -> dict:
    """Unit-free load directions (1000 N each) for the eye FEA. ``hooks``: name -> 1 g vector (x, y, z)."""
    out = {}
    for nm, v in hooks.items():
        v = np.asarray(v, float)
        out[f"hook_{nm}"] = v
        out[f"combo_{nm}"] = v + strap
    gov = max(hooks, key=lambda k: np.linalg.norm(np.asarray(hooks[k]) + strap))
    u = np.asarray(hooks[gov], float) / np.linalg.norm(hooks[gov])
    out["misuse_combo"] = misuse_n * u + strap
    out["strap"] = strap
    for a in SWEEP_DEG:
        r = np.radians(a)
        out[f"dir_{a:g}"] = np.array([0.0, np.sin(r), -np.cos(r)])
    return {k: (1000.0 * np.asarray(v) / np.linalg.norm(v)).tolist() for k, v in out.items()}, gov


def eye_cached(half_z: float, cheek: float, h: float, dirs: dict, tag: str = "") -> dict:
    """eye_fea with an on-disk cache per (half_z, cheek, h, tag) under outputs/im3_body_simloads/ (saved as it goes)."""
    p = OUT / f"eye_{half_z:g}_{cheek:g}_{h:g}{tag}.json"
    if p.exists():
        d = json.loads(p.read_text())
        if set(d["loads"]) >= set(dirs):
            return d
    d = eye_fea(half_z, cheek, dirs, h=h)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))
    return d


def eye_margins(fi_pn: dict, hooks: dict, strap: np.ndarray, misuse_n: float, gov: str) -> dict:
    """Margins from FI99 per newton per direction (``fi_pn``: load name -> FI99 / N).
    fatigue = PAHT fat / (FI/N x 1.6 x |F_1g|); creep = rupture / (FI/N x |F_1g|); strength = 1 / (FI/N x F_fact)."""
    pa = _paht()
    out = {}
    for nm, v in hooks.items():
        c = np.linalg.norm(np.asarray(v) + strap)
        hk = np.linalg.norm(v)
        out[nm] = {"combo_1g_n": float(c), "hook_1g_n": float(hk),
                   "fatigue": pa["fat"] / (fi_pn[f"combo_{nm}"] * G_WALK * c),
                   "fatigue_hook_only": pa["fat"] / (fi_pn[f"hook_{nm}"] * G_WALK * hk),
                   "creep": pa["rupture"] / (fi_pn[f"combo_{nm}"] * c),
                   "strength": 1.0 / (fi_pn[f"combo_{nm}"] * FACTOR * c)}
    mc = misuse_n * np.asarray(hooks[gov]) / np.linalg.norm(hooks[gov]) + strap
    out["misuse"] = {"factored_n": float(FACTOR * np.linalg.norm(mc)),
                     "strength": 1.0 / (fi_pn["misuse_combo"] * FACTOR * np.linalg.norm(mc))}
    return out


# Runs used (outputs/clothsim/corrie_f/<run>). Two CORRIE F revisions, same 30 mm top setback:
# * rev 0 (BL-011, guys round the bar ends x +/-100; scenarios cf_PR{t}.yaml): coarse F_PR{15,19,23} as they stood at
#   2026-11-11 21:55 and this ticket's fine (h 25) 15 in meat run F_PR15_fine_meat_BL021. BL-022 later re-ran the coarse
#   folders on rev 1, so the rev 0 coarse forces exist only in the frozen cache OUT/sim_frame_forces.json (extracted
#   from the node positions before they were overwritten).
# * rev 1 (BL-022, guys at x +/-52; scenarios cf_PR{t}_gx52.yaml, BL-022's runs, read only): coarse F_PR{15,19,23}
#   and fine F_PR{15,19,23}_fineFM (fill + meat). Rev 1 is corrie_f.REVISION, the current design.
RUNS = {"15c": ("F_PR15", 15), "15f": ("F_PR15_fine_meat_BL021", 15), "19c": ("F_PR19", 19), "23c": ("F_PR23", 23)}
RUNS1 = {"15c1": ("F_PR15", 15), "19c1": ("F_PR19", 19), "23c1": ("F_PR23", 23),
         "15f1": ("F_PR15_fineFM", 15), "19f1": ("F_PR19_fineFM", 19), "23f1": ("F_PR23_fineFM", 23)}
SIMFORCES = OUT / "sim_frame_forces.json"           # rev 0 (frozen)
SIMFORCES1 = OUT / "sim_frame_forces_rev1.json"     # rev 1
CANDIDATES = ((12.5, 8.0), (13.5, 8.0), (14.0, 8.0), (15.0, 8.0), (16.0, 8.0), (13.5, 9.0), (13.5, 10.0),
              (12.5, 10.0), (15.0, 9.0), (14.0, 10.0))


def sim_forces(refresh: bool = False, rev: int = 0) -> dict:
    """Frame-side 1 g forces (meat; fill too except the rev 0 fine run), cached in OUT. Rev 0 is frozen (its
    coarse node files were overwritten by BL-022's rev 1 runs): refresh only rebuilds rev 1."""
    path, runs = (SIMFORCES, RUNS) if rev == 0 else (SIMFORCES1, RUNS1)
    if path.exists() and not (refresh and rev == 1):
        return json.loads(path.read_text())
    res = {}
    for key, (run, t) in runs.items():
        for case in (("meat",) if key == "15f" else ("fill", "meat")):
            res[f"{run}|{case}"] = frame_forces_from_run(run, t, case)
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, default=float))
    return res


def eye_hooks(sf: dict, runs: dict = RUNS) -> dict:
    """1 g IM3 hook vectors per run and side (meat case), from the frame forces."""
    out = {}
    for key, (run, _t) in runs.items():
        ff = sf[f"{run}|meat"]
        for side in "RL":
            out[f"{key}{side}"] = ff["forces"][f"hook_im520_{side}"]["f"]
    return out


def eye_study(cands=CANDIDATES, grids=GRIDS, log=print) -> dict:
    """Every candidate cheek at every grid, every load direction; results cached per (cheek, grid)."""
    sf = sim_forces()
    hooks = eye_hooks(sf)
    dirs, gov = eye_directions(hooks, strap_vector_1g(), misuse_1g())
    out = {}
    for hz, ch in cands:
        for h in grids:
            r = eye_cached(hz, ch, h, dirs)
            out[f"{hz:g}_{ch:g}_{h:g}"] = r
            if log:
                log(f"eye {2 * hz:g} x {ch:g} mm h {h:g}: added {r['added_g']:.2f} g, "
                    f"FI99/kN combo_15fL {1000 * r['loads']['combo_15fL']['fi99_per_n']:.4f}")
    return {"dirs": dirs, "gov": gov, "runs": out}


# ======================================================================================= 3. H1 body on sim loads
BAG_CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "hipbelt_off_abuse")
US_Z = (95.0, 142.0)          # under-strap frame pins (bag_attach stations us1 / us2): the sim-force residual goes here
IM_Z = (190.0, 330.0, 520.0)


def _nearest(model: dict, xyz, pool=None) -> str:
    nodes = model["nodes"]
    ids = list(pool) if pool else [n for n in nodes if n != "HP"]
    P = np.array([nodes[n] for n in ids], float)
    return ids[int(np.argmin(np.linalg.norm(P - np.asarray(xyz, float), axis=1)))]


def _stay_node(model: dict, side: float, z: float) -> str:
    pool = [n for n in model["nodes"] if n.startswith("SL" if side < 0 else "SR") and n[2:].replace(".", "").isdigit()]
    return _nearest(model, [side * 115.0, 0.0, z], pool)


def sim_nodal_1g(model: dict, ff: dict, total_kg: float) -> tuple:
    """Frame-side sim forces at 1 g mapped to the beam model's nodes. Returns (g_part, fixed_part, residual):
    node -> [fx, fy, fz] N. ``g_part`` scales with the case g; ``fixed_part`` is the meat-strap cinch loop, which
    does not (rev C holds the 150 N cinch fixed too).
    Hooks -> S*520, hinges -> S*60, guys -> nearest crown top-bar node, contact fields node by node to the nearest
    face node (spreader) / any node (frame, crown). The spreader's lateral (x) contact components are internal to
    the clipped spreader panel: only their net goes to the frame, split over the face nodes. Meat case: the
    meat-face push is reacted at the six IM anchors (ASSUMPTION STRAP_REACT); its cinch share (6 x 150 N) and the
    matching share of the spreader contact form the fixed part. Whatever is left of the bag weight (under-straps,
    wraps, fabric, solver residual) goes on the four under-strap pins so the set balances ``total_kg`` x g."""
    from huntkit.fea.frame import G_ACC
    gp: dict = {}
    fx: dict = {}

    def add(d, nid, f):
        d[nid] = d.get(nid, np.zeros(3)) + np.asarray(f, float)
    face = set(model["groups"]["meat_face"])
    m = ff.get("meat") or {}
    ot = list(m.get("overturning_pull_n") or [0.0, 0.0, 0.0])
    cinch = (float(m["face_n"]) - sum(ot)) / 6.0 if m.get("face_n") else 0.0
    for k, a in ff["forces"].items():
        f = np.asarray(a["f"], float)
        if k.startswith("hook_im520_"):
            add(gp, _stay_node(model, 1.0 if k.endswith("R") else -1.0, EYE_STATION), f)
        elif k.startswith("hinge_"):
            add(gp, _stay_node(model, 1.0 if k.endswith("R") else -1.0, 60.0), f)
        elif k.startswith("TG_"):
            add(gp, _nearest(model, a["xyz"], [n for n in model["nodes"] if n.startswith("TB")]), f)
        elif k == "contact_spreader":
            nf = np.array([r[3:] for r in a["node_f"]], float)
            fy_tot = float(nf[:, 1].sum())
            frac = min(6.0 * cinch / abs(fy_tot), 1.0) if (cinch > 0 and abs(fy_tot) > 1e-6) else 0.0
            ids = [_nearest(model, r[:3], face) for r in a["node_f"]]
            for nid, v in zip(ids, nf):
                add(gp, nid, [0.0, (1.0 - frac) * v[1], v[2]])
                add(fx, nid, [0.0, frac * v[1], 0.0])
            for nid in ids:
                add(gp, nid, [float(nf[:, 0].sum()) / len(ids), 0.0, 0.0])
        elif k.startswith("contact_"):
            for row in a["node_f"]:
                add(gp, _nearest(model, row[:3]), row[3:])
        elif a["kind"] in ("under_strap", "wrap", "tie"):
            add(gp, _nearest(model, a["xyz"]), f)
    nodes = model["nodes"]

    def moment(d):
        return sum((np.cross(np.asarray(nodes[k], float), np.asarray(v, float)) for k, v in d.items()), np.zeros(3))
    if cinch > 0:
        dn = float(m.get("to_strap_anchors_n", 0.0)) / 6.0
        for z, o in zip(IM_Z, ot):
            for sd in (1.0, -1.0):
                add(gp, _stay_node(model, sd, z), [0.0, o / 2.0, -dn])
        # cinch loop (ASSUMPTION STRAP_REACT): the strap pulls at the three IM levels balance the share of the
        # spreader push moved to ``fx`` in force AND moment (the meat bundle is in equilibrium), as close to an
        # equal split as the two equations allow, no level pushing
        from scipy.optimize import lsq_linear
        Fs = sum((np.asarray(v) for v in fx.values()), np.zeros(3))
        Ms = moment(fx)
        zs = np.array([float(nodes[_stay_node(model, 1.0, z)][2]) for z in IM_Z])
        ys = np.array([float(nodes[_stay_node(model, 1.0, z)][1]) for z in IM_Z])
        Ytot, Mx_t = -Fs[1], -Ms[0]               # the anchors must give +Ytot and Mx = -Ms_x (Mx = -z Fy)
        W = 1e3
        A = np.vstack([W * np.ones(3), W * (-zs), np.eye(3)])
        bvec = np.r_[W * Ytot, W * Mx_t, np.full(3, Ytot / 3.0)]
        c = lsq_linear(A, bvec, bounds=(0.0, np.inf)).x
        for z, ci in zip(IM_Z, c):
            for sd in (1.0, -1.0):
                add(fx, _stay_node(model, sd, z), [0.0, ci / 2.0, 0.0])
        info_cinch = {"level_n": c.tolist(), "net_f": (sum((np.asarray(v) for v in fx.values()), np.zeros(3))).tolist(),
                      "net_m": moment(fx).tolist()}
    else:
        info_cinch = None
    # balance: the frame-side set must carry the payload weight at the sim's CG (force and sagittal moment).
    # Force residual -> the four under-strap pins; the sagittal moment left -> a fore-aft couple between the IM3
    # hook nodes (z 520) and the hinge nodes (z 60), i.e. on the bag's two main attachments
    Wv = np.array([0.0, 0.0, -total_kg * G_ACC])
    tot = sum(gp.values()) + sum((np.asarray(v) for v in fx.values()), np.zeros(3))
    resid = Wv - tot
    pins = [_stay_node(model, sd, z) for z in US_Z for sd in (1.0, -1.0)]
    for nid in pins:
        add(gp, nid, resid / len(pins))
    cg = ff.get("cg_mm")
    couple = 0.0
    dM = np.zeros(3)
    if cg is not None:
        Mt = np.cross(np.asarray(cg, float), Wv)
        dM = Mt - moment(gp) - moment(fx)
        hi = [_stay_node(model, sd, EYE_STATION) for sd in (1.0, -1.0)]
        lo = [_stay_node(model, sd, 60.0) for sd in (1.0, -1.0)]
        zh = np.mean([nodes[n][2] for n in hi])
        zl = np.mean([nodes[n][2] for n in lo])
        couple = float(-dM[0] / (zh - zl))      # +couple aft at the hooks, forward at the hinges
        for n in hi:
            add(gp, n, [0.0, couple / 2.0, 0.0])
        for n in lo:
            add(gp, n, [0.0, -couple / 2.0, 0.0])
    sim_nodal_1g.last = {"resid_force_n": resid.tolist(), "moment_fix_nmm": dM.tolist(), "couple_n": couple,
                         "weight_n": float(-Wv[2]), "cinch": info_cinch}
    return ({k: v.tolist() for k, v in gp.items()}, {k: v.tolist() for k, v in fx.items()}, resid.tolist())


def sim_total_kg(run: str, case: str) -> float:
    r = json.loads((SIMDIR / run / "results.json").read_text())["cases"][case]
    v = r["volume"]
    return float(v.get("mass_with_external_kg") or (68.0 + sum(e["kg"] for e in r["inputs"].get("external", []))))


_ORIG_LOADS = None
_NOD_CACHE: dict = {}


def _install_sim_loads():
    """Swap LoadCase._loads so a bag case carrying params['sim_ff'] = (sim frame forces, total kg) gets
    beam(case) - cos(tilt) x beam(upright) + s cos(tilt) x sim, s = g x load / 68 (ASSUMPTION SIM_BODY). The sim
    forces are mapped onto whatever frame model the case runs on (H1, BL-007 fixed, BL-017 legs)."""
    global _ORIG_LOADS
    from huntkit.fea import load_cases as LC
    if _ORIG_LOADS is not None:
        return
    _ORIG_LOADS = LC.LoadCase._loads

    def loads(self, model):
        simp = self.params.get("sim_ff")
        if not simp or self.placement != "bag":
            return _ORIG_LOADS(self, model)
        ff, kg = simp[0], simp[1]
        cyc = len(simp) > 2 and simp[2]
        ck = (id(model), ff["run"], ff["case"])
        if ck not in _NOD_CACHE:
            _NOD_CACHE[ck] = sim_nodal_1g(model, ff, kg)[:2]
        sim, fixed = _NOD_CACHE[ck]
        p0 = {k: v for k, v in self.params.items() if k != "sim_ff"}
        full_c = copy.copy(self)
        full_c.params = p0
        full = _ORIG_LOADS(full_c, model)
        up = copy.copy(self)
        up.params = {k: v for k, v in p0.items() if k not in ("downhill_bias",)}
        up.lateral_tilt_deg = 0.0
        up.cg_z_mm = None
        upright = _ORIG_LOADS(up, model)
        ct = float(np.cos(np.radians(self.lateral_tilt_deg)))
        s = self.g_factor * self.load_kg / 68.0
        out = {k: np.array(v, float) for k, v in full.items()}
        for k, v in upright.items():
            out[k] = out.get(k, np.zeros(6)) - ct * np.asarray(v, float)
        for k, v in sim.items():
            a = out.get(k, np.zeros(6))
            a[:3] += s * ct * np.asarray(v, float)
            out[k] = a
        for k, v in (fixed.items() if not (cyc and self.name == "static_carry") else ()):
            a = out.get(k, np.zeros(6))
            a[:3] += np.asarray(v, float)
            out[k] = a
        return out
    LC.LoadCase._loads = loads


def _uninstall_sim_loads():
    global _ORIG_LOADS
    from huntkit.fea import load_cases as LC
    if _ORIG_LOADS is not None:
        LC.LoadCase._loads = _ORIG_LOADS
        _ORIG_LOADS = None
    _NOD_CACHE.clear()


CYCLIC_ONLY = False      # True: the meat-strap cinch loop (a static preload) is left out of the static-carry set


def sim_env(torso: float, sf: dict, runs: dict, cases=("fill", "meat")) -> dict:
    """Rev C envelope for one torso with the bag cases on the sim forces of ``runs[torso]``: one scenario per sim
    case (tags S_fill / S_meat; the beam's two couple variants no longer apply). The beam's non-bag cases
    (set-down, meat straps, tall, overload) ride in the first scenario."""
    from huntkit.fea import load_standard as LS
    env0 = LS.ls1_envelope("C")
    env = {}
    run = runs[int(round(torso))]
    for cn in cases:
        ff = sf[f"{run}|{cn}"]
        lst = []
        for c in env0["crown_bar"]:
            if c.name in BAG_CASES:
                c = copy.copy(c)
                c.params = {**c.params, "sim_ff": (ff, sim_total_kg(run, cn), CYCLIC_ONLY)}
                lst.append(c)
        if cn == cases[0]:
            lst += [c for c in env0["crown_bar"] if c.name not in BAG_CASES]
        env[f"sim_{cn}"] = lst
    return env


def sim_sets(runner, torsos=(15.0, 19.0, 23.0), sf: dict | None = None, runs: dict | None = None, **kw) -> list:
    """LoadSets on the sim bag loads. ``runner(torso)`` runs the caller's beam_runs for one torso (it reads
    ls1_envelope and TAGS at call time, both swapped here) and returns its LoadSets."""
    from huntkit.fea import load_standard as LS
    from huntkit.gendesign import rev_c_verification as RV
    sf = sf or sim_forces(rev=1)
    runs = runs or SIM_BASES["rev1_fine"]
    oe = LS.ls1_envelope
    sets = []
    _install_sim_loads()
    RV.TAGS.update({"sim_fill": "S_fill", "sim_meat": "S_meat"})
    try:
        for t in torsos:
            env = sim_env(t, sf, runs, **kw)
            LS.ls1_envelope = lambda rev="C", _e=env: _e
            sets += runner(t)
            LS.ls1_envelope = oe
    finally:
        LS.ls1_envelope = oe
        _uninstall_sim_loads()
        for k in ("sim_fill", "sim_meat"):
            RV.TAGS.pop(k, None)
    return sets


def h1_runner(spec_name: str = "h1"):
    import dataclasses
    from huntkit.gendesign import crown_diet as CD
    sp = CD.specs()[spec_name]

    def run(t):
        return CD.beam_runs(dataclasses.replace(sp, torsos=(t,)), buckling=False, log=None)[0]
    return run, sp.torsos


def fixed_runner():
    from huntkit.gendesign import frame_fixed as FF

    def run(t):
        return FF.beam_runs("fixed", torsos=(t,), buckling=False, log=None)[0]
    return run, FF.TORSOS


def spec_runner(spec_name: str):
    return h1_runner(spec_name)


# ======================================================================================= 3b. body solves
def body_eval(name: str, dom_kind: str, solid: np.ndarray, sets: list, log=print) -> dict:
    """H1's rev C body checks (crown_diet.body_check) on the H1 domain (``dom_kind`` 'h1') or a BL-007 fixed-crown
    domain ('a' / 'c'). Fatigue / creep come from the static-carry sets (by_torso); strength from every set."""
    from huntkit.gendesign import frame_comp_d as D
    from huntkit.gendesign import frame_fixed as FF
    from huntkit.gendesign import frame_h1 as H1
    c = H1.base()
    dom = c["dom"] if dom_kind == "h1" else FF.fixed_domain(dom_kind)
    f, ev = FF._eval(dom, solid, sets)
    bk = H1.buckling(f)
    jc = H1.joint_check(f)
    bt = H1.by_torso(ev)
    out = {"name": name, "raster_g": float(D.mass_g(solid, H1.H, 1060.0)), "min": ev["min"],
           "governing": ev["governing"], "by_torso": bt,
           "buckling_min": float(min(v["margin"] for v in bk.values() if v["margin"] is not None)),
           "joint_strength": float(jc["min_strength"]), "joint_fatigue": float(jc["min_fatigue"])}
    # per torso: min over the scenarios of that torso
    per_t: dict = {}
    for k, v in bt.items():
        t = k.split("|")[1]
        o = per_t.setdefault(t, {"strength": 9e9, "fatigue": 9e9, "creep": 9e9})
        for kk in ("strength", "fatigue", "creep"):
            if v[kk] < o[kk]:
                o[kk] = v[kk]
                if kk == "fatigue":
                    o["fatigue_gov"] = f"{k}: {v['gov']}"
    out["per_torso"] = per_t
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / f"util_{name}.npz", util=np.asarray(ev["util"], np.float32))
    # where the governing fatigue sits (static carry, worst torso): location label of the worst row
    worst = None
    for r in ev["rows"]:
        if r["case"] == "static_carry":
            fat = D.MATERIALS[H1.MAT]["fat"] / (r["fi99"] / r["factor"] * D.FAT_G)
            if worst is None or fat < worst[0]:
                worst = (fat, r["scenario"], r["torso"], r["where"])
    out["fatigue_where"] = {"margin": worst[0], "scenario": worst[1], "torso": worst[2], "where": worst[3]}
    if log:
        log(f"body {name}: {json.dumps(out['min'], default=float)} per torso "
            f"{ {t: round(v['fatigue'], 3) for t, v in per_t.items()} } at {worst[3]}")
    return out


def _body_cached(name: str, fn) -> dict:
    p = OUT / f"body_{name}.json"
    if p.exists():
        return json.loads(p.read_text())
    d = fn()
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, default=float))
    return d


def sim_sets_for(kind: str, rev_runs: dict, sf: dict, label: str) -> list:
    """Per-torso-tagged LoadSets on the sim loads for frame ``kind`` ('h1', 'c17b19', 'fixed'), each torso's bag
    cases from ``rev_runs`` (torso -> run folder) and ``sf`` (frame forces)."""
    from huntkit.gendesign import crown_diet as CD
    runner, torsos = (fixed_runner() if kind == "fixed" else h1_runner(kind))
    sets = []
    for t in torsos:
        sets += sim_sets(runner, torsos=(float(t),), sf=sf, runs=rev_runs)
    return CD._retag(sets, label)


def beam_sets_for(kind: str, label: str) -> list:
    """Per-torso-tagged rev C beam LoadSets (both couple variants) for frame ``kind``, from the BL-017 / BL-007 caches."""
    from huntkit.gendesign import crown_diet as CD
    if kind == "fixed":
        from huntkit.gendesign import frame_fixed as FF
        sets, _ = FF.load_beam("fixed", log=None)
    else:
        sets, _ = CD.load_beam(CD.specs()[kind], log=None)
    return CD._retag(sets, label)


def solids() -> dict:
    """Bodies: H1 (frame_h1), BL-017 c17 bore 19 (crown_diet.bore_open_solid(9.5)), BL-007 (a) = H1 on the
    fixed-crown domain, BL-007 (c) = frame_fixed c_solid."""
    from huntkit.gendesign import crown_diet as CD
    from huntkit.gendesign import frame_fixed as FF
    h1 = CD._h1_solid()
    return {"h1": ("h1", h1), "c17b19": ("h1", CD.bore_open_solid(9.5)[0]), "bl007a": ("a", h1),
            "bl007c": ("c", np.load(FF.OUT / "c_solid.npz")["solid"])}


FRAME_KIND = {"h1": "h1", "c17b19": "c17b19", "bl007a": "fixed", "bl007c": "fixed"}
SIM_BASES = {
    # name -> torso -> run (both cases fill + meat from that run)
    "rev1_fine": {15: "F_PR15_fineFM", 19: "F_PR19_fineFM", 23: "F_PR23_fineFM"},
    "rev1_coarse": {15: "F_PR15", 19: "F_PR19", 23: "F_PR23"},
}


def body_study(bodies=("h1", "c17b19", "bl007a", "bl007c"), bases=("beam", "rev1_fine", "rev1_coarse"),
               log=print) -> dict:
    """Every (body, load basis) pair, cached per pair under OUT (saved as it goes). 'beam' = rev C beam bag loads,
    per-torso tags (BL-017 basis); the others the sim loads."""
    sf1 = sim_forces(rev=1)
    sol = solids()
    out = {}
    for b in bodies:
        dk, solid = sol[b]
        for base in bases:
            nm = f"{b}__{base}"
            if base == "beam":
                fn = lambda b=b, dk=dk, solid=solid, nm=nm: body_eval(nm, dk, solid, beam_sets_for(FRAME_KIND[b], "B"),
                                                                     log=log)
            else:
                def fn(b=b, dk=dk, solid=solid, nm=nm, base=base):
                    global CYCLIC_ONLY
                    CYCLIC_ONLY = base.endswith("_cyc")
                    try:
                        sets = sim_sets_for(FRAME_KIND[b], SIM_BASES[base.replace("_cyc", "")], sf1, "S")
                    finally:
                        CYCLIC_ONLY = False
                    return body_eval(nm, dk, solid, sets, log=log)
            out[nm] = _body_cached(nm, fn)
    return out


# ======================================================================================= 2b. eye on every hook
FINAL_CANDS = ((12.5, 8.0), (13.5, 8.0), (14.0, 8.0), (15.0, 8.0))


def all_hooks() -> dict:
    """Every 1 g IM3 hook vector (meat case): rev 0 keys '15cR' ... '15fL', rev 1 keys '15c1R' ... '23f1L'."""
    h = eye_hooks(sim_forces(rev=0), RUNS)
    h.update(eye_hooks(sim_forces(rev=1), RUNS1))
    return h


def eye_study_rev1(cands=FINAL_CANDS, grids=GRIDS, log=print) -> dict:
    """The rev 1 hook directions (and their combos with the strap) on the final candidates, cached with tag
    '_rev1' (the rev 0 directions are in the untagged cache files)."""
    hooks1 = eye_hooks(sim_forces(rev=1), RUNS1)
    dirs, gov = eye_directions(hooks1, strap_vector_1g(), misuse_1g())
    out = {}
    for hz, ch in cands:
        for h in grids:
            r = eye_cached(hz, ch, h, dirs, tag="_rev1")
            out[f"{hz:g}_{ch:g}_{h:g}"] = r
            if log:
                log(f"eye rev1 {2 * hz:g} x {ch:g} mm h {h:g}: n_elem {r['n_elem']}")
    return {"dirs": dirs, "gov": gov, "runs": out}


# ======================================================================================= 3c. crown top bar with the rev 1 guys
def split_bar_at(model: dict, x_abs: float) -> dict:
    """Insert top-bar nodes TBL<x> / TBR<x> at x = -/+ ``x_abs`` in whichever top-bar member spans it (the guys'
    bridle sleeves, rev 1 x +/-52, sit inside TB0-TB1 / TB1-TB2, which frame_cg_recheck.split_top_bar can't split)."""
    m = copy.deepcopy(model)
    nodes = m["nodes"]
    for tag, s in (("L", -1.0), ("R", 1.0)):
        xt = s * x_abs
        for mem in list(m["members"]):
            if mem.get("group") != "crown_top_bar":
                continue
            a, b = mem["nodes"]
            pa, pb = np.array(nodes[a], float), np.array(nodes[b], float)
            lo, hi = sorted((pa[0], pb[0]))
            if not (lo + 1.0 < xt < hi - 1.0):
                continue
            f = (xt - pa[0]) / (pb[0] - pa[0])
            nid = f"TB{tag}{int(round(x_abs))}"
            nodes[nid] = list(map(float, pa + f * (pb - pa)))
            i = m["members"].index(mem)
            m1 = {**mem, "id": f"{a}-{nid}", "nodes": [a, nid]}
            m2 = {**mem, "id": f"{nid}-{b}", "nodes": [nid, b]}
            m["members"][i:i + 1] = [m1, m2]
            for j in m.get("joints", []):
                j["members"] = [m1["id"] if q == mem["id"] else q for q in j["members"]]
            break
    return m


def top_bar_check(guy_x: float = 52.0, log=print) -> dict:
    """Crown top bar (and the other crown members) on the rev 1 sim loads, H1 at 15 / 19 / 23 in: the beam rev C
    cases with the bag cases from the fine rev 1 sims, the guys applied at bar nodes split in at x +/-``guy_x``
    (their sim anchors), the lifter reactions at the model's lifter nodes (TB0 / TB2) as in every crown check.
    Strength = member FPF margin at the factored load; fatigue = CFRP FI <= 0.5 at 1.6 g (frame_cg_recheck rule).
    Also the beam basis (no guys) for comparison."""
    from huntkit.gendesign import crown_diet as CD
    from huntkit.gendesign import frame_cg_recheck as R
    sp = CD.specs()["h1"]
    ob = CD.build

    def build(spec, t, posts=False):
        return split_bar_at(ob(spec, t, posts), guy_x)
    import dataclasses
    sf1 = sim_forces(rev=1)
    out = {}
    CD.build = build
    try:
        rows = []
        for t in sp.torsos:
            rows += sim_sets(lambda tt: CD.beam_runs(dataclasses.replace(sp, torsos=(tt,)), buckling=False,
                                                     log=None)[1], torsos=(float(t),), sf=sf1,
                             runs=SIM_BASES["rev1_fine"])
    finally:
        CD.build = ob
    _, beam_rows = CD.load_beam(sp, log=None)

    def summarize(rows, tags):
        res = {}
        for tg in tags:
            rs = [r for r in rows if r["scenario"] == tg]
            st = min(((r["members"]["crown_top_bar"][0], f"{r['case']}|{r['torso']:g}", r["members"]["crown_top_bar"][1])
                      for r in rs if "crown_top_bar" in r["members"]), default=None)
            fat = min(((0.5 * r["members"]["crown_top_bar"][0] * r["factor"] / G_WALK, f"static_carry|{r['torso']:g}")
                       for r in rs if r["case"] == "static_carry" and "crown_top_bar" in r["members"]), default=None)
            cs = R.crown_summary(rows, tg)
            res[tg] = {"top_bar_strength": st[0], "top_bar_strength_set": st[1], "member": st[2],
                       "top_bar_fatigue": fat[0], "top_bar_fatigue_set": fat[1],
                       "crown_min": {k: round(float(v["sf"]), 3) for k, v in cs.items() if isinstance(v, dict) and "sf" in v}}
        return res
    out["sim_rev1_fine"] = summarize(rows, ("S_fill", "S_meat"))
    out["beam"] = summarize(beam_rows, ("C", "C_im3"))
    # the guy forces used (1 g, per torso and case)
    gl = {}
    for t, run in SIM_BASES["rev1_fine"].items():
        for cn in ("fill", "meat"):
            ff = sf1[f"{run}|{cn}"]["forces"]
            gl[f"{t}_{cn}"] = {k: round(float(np.linalg.norm(ff[k]["f"])), 1) for k in ff if k.startswith("TG_")}
    out["guy_1g_n"] = gl
    out["guy_x"] = guy_x
    if log:
        log(json.dumps(out, default=float)[:800])
    return out


# ======================================================================================= 4. assembly of results
def _eye_fi(hz: float, ch: float, h: float) -> dict:
    """FI99 per newton per load name at one (cheek, grid): rev 0 cache (untagged) merged with the rev 1 cache."""
    out = {}
    for tag in ("", "_rev1"):
        p = OUT / f"eye_{hz:g}_{ch:g}_{h:g}{tag}.json"
        if p.exists():
            d = json.loads(p.read_text())
            for k, v in d["loads"].items():
                kk = k if tag == "" or not k.startswith(("misuse", "strap", "dir_")) else f"{k}_r1"
                out[kk] = v["fi99_per_n"]
            out["_added_g"] = d["added_g"]
            out["_n_elem"] = d["n_elem"]
    return out


def eye_summary(cands=FINAL_CANDS, grids=GRIDS) -> dict:
    """Margins of every candidate at every grid on every hook (rev 0 + rev 1, coarse + fine, R + L), the design
    value (FI = largest of the three grids, i.e. the smallest margin), and the sensitivities."""
    pa = _paht()
    hooks = all_hooks()
    strap = strap_vector_1g()
    mis = misuse_1g()
    out = {"hooks": {}, "strap_1g": strap.tolist(), "misuse_1g_n": mis, "cands": {}}
    for k, v in hooks.items():
        v = np.asarray(v)
        out["hooks"][k] = {"vec": [round(float(x), 1) for x in v], "mag": round(float(np.linalg.norm(v)), 1),
                           "aft_of_down_deg": round(float(np.degrees(np.arctan2(v[1], -v[2]))), 1),
                           "lateral_deg": round(float(np.degrees(np.arctan2(abs(v[0]), np.hypot(v[1], v[2])))), 1),
                           "combo_mag": round(float(np.linalg.norm(v + strap)), 1)}
    for hz, ch in cands:
        per = {}
        for h in grids:
            fi = _eye_fi(hz, ch, h)
            if not all(f"combo_{k}" in fi for k in hooks):
                continue
            rows = {}
            for k, v in hooks.items():
                v = np.asarray(v)
                c = float(np.linalg.norm(v + strap))
                hk = float(np.linalg.norm(v))
                rows[k] = {"fatigue": pa["fat"] / (fi[f"combo_{k}"] * G_WALK * c),
                           "fatigue_hook_only": pa["fat"] / (fi[f"hook_{k}"] * G_WALK * hk),
                           "creep": pa["rupture"] / (fi[f"combo_{k}"] * c),
                           "strength": 1.0 / (fi[f"combo_{k}"] * FACTOR * c)}
            ms = []
            for sfx, hk in (("", RUNS), ("_r1", RUNS1)):
                hh = {k: hooks[k] for k in hooks if any(k[:-1] == r for r in hk)}
                gov = max(hh, key=lambda k: np.linalg.norm(np.asarray(hh[k]) + strap))
                mc = mis * np.asarray(hh[gov]) / np.linalg.norm(hh[gov]) + strap
                ms.append(1.0 / (fi[f"misuse_combo{sfx}"] * FACTOR * np.linalg.norm(mc)))
            sweep = {a: fi[f"dir_{a:g}"] for a in SWEEP_DEG}
            per[f"{h:g}"] = {"rows": rows, "misuse_strength": float(min(ms)), "added_g": fi["_added_g"],
                             "n_elem": fi["_n_elem"], "sweep_fi_per_kn": {f"{a:g}": 1e3 * v for a, v in sweep.items()},
                             "strap_fi_per_kn": 1e3 * fi["strap"]}
        if len(per) < len(grids):
            continue
        hk = list(hooks)
        des = {}
        for m in ("fatigue", "fatigue_hook_only", "creep", "strength"):
            vals = {k: min(per[g]["rows"][k][m] for g in per) for k in hk}
            gk = min(vals, key=vals.get)
            des[m] = {"value": vals[gk], "hook": gk,
                      "grid": min(per, key=lambda g, gk=gk, m=m: per[g]["rows"][gk][m])}
        des["misuse_strength"] = {"value": min(per[g]["misuse_strength"] for g in per)}
        gk = des["fatigue"]["hook"]
        mesh = {g: per[g]["rows"][gk]["fatigue"] for g in per}
        # direction: margin of the governing combo magnitude if it pulled at each sweep angle (design grid max FI)
        cmag = float(np.linalg.norm(np.asarray(hooks[gk]) + strap))
        dir_sens = {a: pa["fat"] / (max(per[g]["sweep_fi_per_kn"][f"{a:g}"] for g in per) / 1e3 * G_WALK * cmag)
                    for a in SWEEP_DEG}
        # direction scatter (ASSUMPTION DIR_SCATTER): the governing combo pulled DIR_SCATTER_DEG further aft, by the
        # ratio of the in-plane sweep FIs (design grid = largest FI) at the two angles
        cv = np.asarray(hooks[gk]) + strap
        th = float(np.degrees(np.arctan2(cv[1], -cv[2])))
        sw_a = np.array(SWEEP_DEG)
        sw_f = np.array([max(per[g]["sweep_fi_per_kn"][f"{a:g}"] for g in per) for a in SWEEP_DEG])
        fi_th, fi_th2 = np.interp(th, sw_a, sw_f), np.interp(th + DIR_SCATTER_DEG, sw_a, sw_f)
        dir_plus = des["fatigue"]["value"] * fi_th / fi_th2
        fine = [k for k in hk if k[2] == "f"]
        coarse = [k for k in hk if k[2] == "c"]
        sens = {"mesh_fatigue_by_grid": mesh,
                "mesh_spread_pct": 100 * (max(mesh.values()) - min(mesh.values())) / min(mesh.values()),
                "direction_fatigue_by_aft_deg": {f"{a:g}": v for a, v in dir_sens.items()},
                "fatigue_coarse_cloth_only": min(min(per[g]["rows"][k]["fatigue"] for g in per) for k in coarse),
                "fatigue_fine_cloth_only": min(min(per[g]["rows"][k]["fatigue"] for g in per) for k in fine),
                "fatigue_rev0_only": min(min(per[g]["rows"][k]["fatigue"] for g in per) for k in hk
                                         if k[:-1] in RUNS),
                "fatigue_rev1_only": min(min(per[g]["rows"][k]["fatigue"] for g in per) for k in hk
                                         if k[:-1] in RUNS1),
                "fatigue_hook_only": des["fatigue_hook_only"]["value"],
                "hook_force_at_fatigue_1p0_n": des["fatigue"]["value"] * cmag,
                "governing_combo_1g_n": cmag, "governing_combo_aft_deg": th,
                "fatigue_dir_plus_scatter": float(dir_plus)}
        lp = __import__("huntkit.gendesign.loadpath_check", fromlist=["x"])
        out["cands"][f"{hz:g}_{ch:g}"] = {
            "half_z": hz, "cheek": ch, "height_mm": 2 * hz, "per_grid": per, "design": des, "sensitivity": sens,
            "added_g_h1": per["1"]["added_g"], "pair_delta_vs_27mm_g": None,
            "clearance": lp.cheek_clearance(hz, ch),
            "ca1_flip_ratio": pa["fat"] / des["fatigue"]["value"],
            "pass": bool(des["fatigue"]["value"] >= FAT_REQ and dir_plus >= FAT_REQ and des["strength"]["value"] >= STR_REQ
                         and des["misuse_strength"]["value"] >= STR_REQ and des["creep"]["value"] >= 1.0)}
    base = out["cands"].get("13.5_8")
    for v in out["cands"].values():
        if base:
            v["pair_delta_vs_27mm_g"] = 2 * (v["added_g_h1"] - base["added_g_h1"])
    ok = [k for k, v in out["cands"].items() if v["pass"]]
    out["chosen"] = min(ok, key=lambda k: out["cands"][k]["added_g_h1"]) if ok else None
    return out


def body_summary(study: dict) -> dict:
    pa = _paht()
    out = {}
    for nm, v in study.items():
        b, base = nm.split("__")
        out.setdefault(b, {})[base] = {"min": v["min"], "per_torso": v["per_torso"], "raster_g": v["raster_g"],
                                       "by_torso": v["by_torso"],
                                       "fatigue_where": v["fatigue_where"], "joint_fatigue": v["joint_fatigue"],
                                       "buckling_min": v["buckling_min"],
                                       "ca1_flip_ratio": pa["fat"] / v["min"]["fatigue"]}
    return out


def compute(log=print) -> dict:
    sf0, sf1 = sim_forces(rev=0), sim_forces(rev=1)
    hv = {}
    for sf, runs, rev in ((sf0, RUNS, 0), (sf1, RUNS1, 1)):
        for key, (run, t) in runs.items():
            ff = sf[f"{run}|meat"]
            hv[key] = {"run": run, "rev": rev, "torso": t, "h_mm": ff["h_mm"], "converged": ff["converged"],
                       **hook_vectors(ff)}
    eye = eye_summary()
    study = {}
    for p in sorted(OUT.glob("body_*.json")):
        if not p.stem.startswith("body_h1fix_"):
            study[p.stem[5:]] = json.loads(p.read_text())
    body = body_summary(study)
    if "c17b19" in body and "beam" not in body["c17b19"]:
        # BL-017 ran this exact basis (per-torso tags, crown_diet_results body 'c17b19'): taken from its record
        v = json.loads((ANALYSIS / "crown_diet_results.json").read_text())["body"]["c17b19"]
        pt = {}
        for k, x in v["by_torso"].items():
            t = k.split("|")[1]
            o = pt.setdefault(t, {"strength": 9e9, "fatigue": 9e9, "creep": 9e9})
            for kk in o:
                o[kk] = min(o[kk], x[kk])
        body["c17b19"]["beam"] = {"min": v["min"], "per_torso": pt, "by_torso": v["by_torso"], "raster_g": v["raster_g"],
                                  "fatigue_where": {"torso": 23.0, "where": str(v["governing"]), "scenario": ""},
                                  "joint_fatigue": v.get("joint_fatigue"), "buckling_min": v.get("buckling_min"),
                                  "ca1_flip_ratio": _paht()["fat"] / v["min"]["fatigue"],
                                  "source": "crown_diet_results.json body c17b19 (BL-017, same basis)"}
    extra = {}
    for nm in ("misuse_eye", "top_bar"):
        p = OUT / f"{nm}.json"
        if p.exists():
            extra[nm] = json.loads(p.read_text())
    if (OUT / "misuse_goff.json").exists():
        extra["misuse_goff"] = misuse_goff()
    fixes = {p.stem[5:].split("__")[0]: json.loads(p.read_text()) for p in sorted(OUT.glob("body_h1fix_*.json"))}
    extra["fix"] = {k: {"min": v["min"], "per_torso": v["per_torso"], "added_g_one_frame": v.get("added_g_one_frame"),
                        "fatigue_where": v["fatigue_where"]} for k, v in fixes.items()}
    return {**extra, "date": "2026-11-12", "ticket": "BL-021", "assumptions": ASSUMPTIONS,
            "requirements": {"fatigue": FAT_REQ, "strength": STR_REQ, "g_walk": G_WALK, "factor": FACTOR},
            "hook_vectors": hv, "eye": eye, "body": body}


# ======================================================================================= 5. figures
def plot_eye(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = res["eye"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.6), dpi=110)
    ks = sorted(e["cands"], key=lambda k: e["cands"][k]["height_mm"])
    x = np.arange(len(ks))
    for i, g in enumerate(GRIDS):
        y = [min(r["fatigue"] for r in e["cands"][k]["per_grid"][f"{g:g}"]["rows"].values()) for k in ks]
        ax[0].plot(x, y, "o-", color=("#1f5f8b", "#4f8fbf", "#8fbfdf")[i], label=f"FEA grid h {g:g} mm")
    ax[0].axhline(FAT_REQ, color="#b03030", ls="--", lw=1.2, label=f"target {FAT_REQ}")
    ax[0].axhline(1.0, color="#777", ls=":", lw=1)
    ax[0].set_xticks(x, [f"{e['cands'][k]['height_mm']:g} mm\n{e['cands'][k]['pair_delta_vs_27mm_g']:+.1f} g/pair"
                         for k in ks], fontsize=8)
    ax[0].set_ylabel("fatigue margin (worst hook + strap, 1.6 g)")
    ax[0].set_title("IM3 cheek height vs fatigue (8 mm thick)", fontsize=10)
    if e["chosen"]:
        ax[0].axvline(ks.index(e["chosen"]), color="#2a7a2a", lw=6, alpha=0.15)
    ax[0].legend(fontsize=7, loc="lower right")
    ch = e["cands"][e["chosen"] or ks[-1]]
    ds = ch["sensitivity"]["direction_fatigue_by_aft_deg"]
    ax[1].plot([float(a) for a in ds], list(ds.values()), "s-", color="#1f5f8b")
    ax[1].axhline(FAT_REQ, color="#b03030", ls="--", lw=1.2)
    ax[1].axhline(1.0, color="#777", ls=":", lw=1)
    angs = [h["aft_of_down_deg"] for h in e["hooks"].values()]
    ax[1].axvspan(min(angs), max(angs), color="#2a7a2a", alpha=0.15, label="cloth-sim hook directions")
    ax[1].set_xlabel("pull angle aft of straight down (deg)")
    ax[1].set_ylabel("fatigue margin at the governing force")
    ax[1].set_title(f"{ch['height_mm']:g} mm cheek: load-direction sensitivity", fontsize=10)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_body(res: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b = res["body"]
    names = {"h1": "H1", "c17b19": "BL-017 c17", "bl007a": "BL-007 (a)", "bl007c": "BL-007 (c)"}
    bases = [("beam", "beam bag loads", "#999999"), ("rev1_fine_cyc", "cloth sim fine, cinch static", "#1f5f8b"),
             ("rev1_fine", "cloth sim fine, cinch cycled (bound)", "#c9a227")]
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=110)
    labels, xs = [], []
    i = 0
    for k in names:
        if k not in b:
            continue
        for t in ("15", "19", "23"):
            for j, (bs, lab, col) in enumerate(bases):
                if bs in b[k] and t in b[k][bs]["per_torso"]:
                    v = b[k][bs]["per_torso"][t]["fatigue"]
                    ax.bar(i + (j - 1) * 0.27, v, 0.26, color=col, label=lab if (k == "h1" and t == "15") else None)
            labels.append(f"{names[k]}\n{t} in")
            xs.append(i)
            i += 1
        i += 0.5
    ax.axhline(FAT_REQ, color="#b03030", ls="--", lw=1.2, label=f"BL-021 target {FAT_REQ}")
    ax.axhline(1.0, color="#333", ls=":", lw=1, label="rev C 1.0")
    ax.set_xticks(xs, labels, fontsize=7)
    ax.set_ylabel("body fatigue margin (1e5 x 1.6 g, PAHT 0.30)")
    ax.set_title("Frame body fatigue per torso: beam bag loads vs cloth-sim loads", fontsize=10)
    ax.set_ylim(0.6, max(2.0, ax.get_ylim()[1]))
    ax.legend(fontsize=7, ncol=3, loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_eye_field(res: dict, path: Path, h: float = 0.8) -> str:
    """FI99 field of the chosen cheek under the governing 1.6 g combo (hook + strap): the cheek seen from the side
    (max FI through the thickness) and from above. Saved as a utilization picture (FI x 1.6 g / PAHT fat ratio)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = res["eye"]
    ch = e["cands"][e["chosen"]]
    gk = ch["design"]["fatigue"]["hook"]
    v = np.asarray(all_hooks()[gk]) + strap_vector_1g()
    pa = _paht()
    r = eye_fea(ch["half_z"], ch["cheek"], {"gov": (G_WALK * v).tolist()}, h=h, field=True)
    X = np.asarray(r["field"]["xyz"])
    U = np.asarray(r["field"]["fi"]) / pa["fat"]           # fatigue utilisation (1 / margin)
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.6), dpi=110)
    for a, (i, j, ttl) in zip(ax, ((1, 2, "side view (y aft, z up the stay)"), (0, 1, "top view (x pin axis, y aft)"))):
        ki = np.round((X[:, i] - X[:, i].min()) / h).astype(int)
        kj = np.round((X[:, j] - X[:, j].min()) / h).astype(int)
        img = np.full((kj.max() + 1, ki.max() + 1), np.nan)
        np.fmax.at(img, (kj, ki), U)
        sc = a.imshow(img, origin="lower", cmap="inferno", vmin=0, vmax=1.0, interpolation="nearest",
                      extent=(X[:, i].min() - h / 2, X[:, i].max() + h / 2, X[:, j].min() - h / 2, X[:, j].max() + h / 2))
        a.set_aspect("equal")
        a.set_title(ttl, fontsize=9)
        a.set_xlabel("mm")
    fig.colorbar(sc, ax=ax, label="fatigue utilisation (1 = fails 1e5 cycles)")
    fig.suptitle(f"IM3 eye, {ch['height_mm']:g} mm cheek, governing hook {gk} + strap at 1.6 g "
                 f"(h {h:g} mm; peak {U.max():.2f}, p99 {np.percentile(U, 99):.2f})", fontsize=10)
    fig.savefig(path)
    plt.close(fig)
    return str(path)


# ======================================================================================= 6. record
def _lb(n):
    return f"{n / 4.44822:.0f} lbf"


def write_md(res: dict) -> str:
    L = []
    w = L.append
    e, b, hv = res["eye"], res["body"], res["hook_vectors"]
    ch = e["cands"].get(e["chosen"]) if e["chosen"] else None
    w("# BL-021 IM3 eye and frame body on the cloth-sim loads\n")
    w("Generated by `python -m huntkit.gendesign.im3_body_simloads` (data: `im3_body_simloads.json`). Date "
      f"{res['date']}. Rev C (HA-LS-1, `load_standard.md`): fatigue 1e5 cycles at 0 to {G_WALK} g, strength at the "
      f"factored load ({FACTOR:g} x the 1 g force), PAHT-CF fatigue ratio 0.30 (ASSUMPTION PAHT_FAT). BL-021 targets: "
      f"**fatigue >= {FAT_REQ}** on the sim loads (to cover input scatter), cheek strength >= {STR_REQ}. "
      "Units N, mm, g (lbf / oz alongside).\n")
    w("## Summary\n")
    w(res["summary_md"])
    w("\n## 1. IM3 hook force vectors from the cloth sim (meat case, 1 g)\n")
    w("Rebuilt from the saved node positions: each bridle leg gives T x unit(bag node - eye); the sum is the hook "
      "vector. x = pin axis (+ = right), y = aft toward the bag, z = up. `leg sum` is the run's own scalar report "
      "(sum of leg tensions; it is larger than the vector when the legs fan out).\n")
    w("| run | rev | mesh h | side | vector (x, y, z) N | magnitude N | leg sum N | aft of down | lateral |")
    w("|---|---|---|---|---|---|---|---|---|")
    for k, v in hv.items():
        for s in "RL":
            h = v[s]
            w(f"| {v['run']} | {v['rev']} | {v['h_mm']:g} | {s} | ({h['vec'][0]:.0f}, {h['vec'][1]:.0f}, "
              f"{h['vec'][2]:.0f}) | {h['mag']:.0f} ({_lb(h['mag'])}) | {h['leg_sum']:.0f} | "
              f"{h['aft_of_down_deg']:.1f} deg | {h['lateral_deg']:.1f} deg |")
    w("\n" + res["coarse_fine_md"])
    w("\n## 2. IM3 eye (printed fairlead) on the sim vectors + the IM3 meat strap\n")
    w(f"Strap vector (rev C C5 IM3 strap, per 1 g): ({e['strap_1g'][0]:.0f}, {e['strap_1g'][1]:.0f}, "
      f"{e['strap_1g'][2]:.0f}) N, {np.linalg.norm(e['strap_1g']):.0f} N. Worst combination (ASSUMPTION COMBINE): "
      "hook vector + strap vector, both at full value, on the same eye. Misuse (BL-010 guys-off envelope "
      f"{e['misuse_1g_n']:.0f} N at 1 g, in the governing hook's direction) + strap checked for strength.\n")
    w("Mesh study: every load direction at h 1.0 / 0.8 / 0.7 mm (h 0.5 runs out of memory, BL-014). The FI99 does "
      "not move monotonically with h (voxel steps of the 7.2 mm hole and the cheek edges); the spread between the "
      "three grids is the mesh scatter, and the **design value takes the largest FI of the three grids** "
      "(smallest margin). Converged is judged as: the three grids within +-10 % of each other, no trend with h.\n")
    w("| cheek (tall x thick) | added g (h 1.0) | pair vs 27 mm | fatigue h1.0 / 0.8 / 0.7 | design fatigue | "
      "hook-only fatigue | strength | misuse strength | creep | CA-1 flip | pass |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in sorted(e["cands"], key=lambda k: e["cands"][k]["height_mm"]):
        c = e["cands"][k]
        d = c["design"]
        mg = " / ".join(f"{min(r['fatigue'] for r in c['per_grid'][f'{g:g}']['rows'].values()):.3f}" for g in GRIDS)
        w(f"| {c['height_mm']:g} x {c['cheek']:g} mm | {c['added_g_h1']:.2f} | {c['pair_delta_vs_27mm_g']:+.2f} g | "
          f"{mg} | **{d['fatigue']['value']:.3f}** ({d['fatigue']['hook']}) | {d['fatigue_hook_only']['value']:.3f} | "
          f"{d['strength']['value']:.2f} | {d['misuse_strength']['value']:.2f} | {d['creep']['value']:.2f} | "
          f"{c['ca1_flip_ratio']:.3f} | {'yes' if c['pass'] else 'no'} |")
    if ch:
        s = ch["sensitivity"]
        w(f"\n### 2.1 Chosen: {ch['height_mm']:g} mm tall x {ch['cheek']:g} mm thick cheek, each margin with its "
          "sensitivity\n")
        w(f"- **Fatigue {ch['design']['fatigue']['value']:.3f}** (target {FAT_REQ}); governing hook "
          f"{ch['design']['fatigue']['hook']} + strap = {s['governing_combo_1g_n']:.0f} N at 1 g "
          f"({_lb(s['governing_combo_1g_n'])}). The eye reaches 1.0 at {s['hook_force_at_fatigue_1p0_n']:.0f} N "
          f"combined (1 g basis).")
        w(f"- Mesh (FEA): {' / '.join(f'{v:.3f}' for v in s['mesh_fatigue_by_grid'].values())} at h 1.0 / 0.8 / "
          f"0.7 mm on the governing hook, spread {s['mesh_spread_pct']:.1f} %.")
        w(f"- Cloth mesh: coarse-only hooks {s['fatigue_coarse_cloth_only']:.3f}, fine-only hooks "
          f"{s['fatigue_fine_cloth_only']:.3f}.")
        w(f"- CORRIE F revision: rev 0 hooks {s['fatigue_rev0_only']:.3f}, rev 1 hooks {s['fatigue_rev1_only']:.3f}.")
        w(f"- Load combination: hook alone {s['fatigue_hook_only']:.3f}; hook + strap {ch['design']['fatigue']['value']:.3f}.")
        w("- Load direction (governing force at other pull angles, same FEA): " + ", ".join(
            f"{a} deg {v:.3f}" for a, v in s["direction_fatigue_by_aft_deg"].items())
          + f". The sim hooks pull {min(h['aft_of_down_deg'] for h in e['hooks'].values()):.0f} to "
          f"{max(h['aft_of_down_deg'] for h in e['hooks'].values()):.0f} deg aft of straight down.")
        cl = ch["clearance"]
        w(f"- Strength {ch['design']['strength']['value']:.2f} (factored hook + strap), misuse + strap "
          f"{ch['design']['misuse_strength']['value']:.2f}, creep {ch['design']['creep']['value']:.2f}.")
        w(f"- Mass: {ch['added_g_h1']:.2f} g per eye at h 1.0 (the ledger's basis), "
          f"{ch['pair_delta_vs_27mm_g']:+.2f} g a pair over the adopted 27 mm.")
        w(f"- Clearances: cheek z {cl['cheek_bottom_z']:g} to {cl['cheek_top_z']:g}; {cl['gap_mm']:.1f} mm above "
          f"the spreader top edge (z {cl['spreader_top_z']:g}, rule >= {cl['notch_clear_mm']:g}); throat "
          f"{cl['throat_mm']:g} mm unchanged (both carabiners / the hook and strap share it as today); outer width "
          f"{cl['outer_width_mm']:g} mm; stands {cl['cheek_aft_of_hole_mm']:g} mm aft of the hole centre as today.")
    mis = res.get("misuse_eye")
    if mis:
        g = res["misuse_goff"]
        w("\n### 2.2 Guys-off misuse (BL-022 request)\n")
        w("BL-022's two converged guys-off runs disagree: coarse `F_PR15_goff_sm8` puts "
          f"{g['F_PR15_goff_sm8']['hooks']['L']['leg_sum']:.0f} N on the left IM3 hook at 1 g (vector "
          f"{tuple(round(v) for v in g['F_PR15_goff_sm8']['hooks']['L']['vec'])} N, "
          f"{-g['F_PR15_goff_sm8']['hooks']['L']['aft_of_down_deg']:.0f} deg forward of straight down), fine "
          f"`F_PR15_fineFM_goff_sm8` {g['F_PR15_fineFM_goff_sm8']['hooks']['L']['leg_sum']:.0f} N. Not settled here (it is a "
          "cloth-sim question); as asked, the eye is checked at the worst one: the coarse vector at its leg sum x 3.0 = "
          f"**{mis['factored_n']:.0f} N factored**, alone and with the rev C strap (x 3.0) on the same eye. Strength = "
          "1 / FI99, worst of h 1.0 / 0.8 / 0.7 mm.\n")
        w("| cheek | hook alone h 1.0 / 0.8 / 0.7 | hook alone (design) | hook + strap (design) |")
        w("|---|---|---|---|")
        for k, v in mis["cands"].items():
            w(f"| {2 * float(k.split('_')[0]):g} x 8 mm | {' / '.join(format(v['per_grid'][x]['goff'], '.2f') for x in ('1', '0.8', '0.7'))} | "
              f"**{v['strength']['goff']:.2f}** | {v['strength']['goff_strap']:.2f} |")
        w("\nRev C asks >= 1.0 at the factored load: both cheeks pass with margin. The coordinator's 1.5 cheek target is "
          "met by 28 mm for the hook alone (1.57) and by neither for the stacked hook + full strap upper bound (1.45 / "
          "1.36), which counts the meat twice. The B-17 seam (3277 N) and the carabiner minor-axis proof (4000 N) stay "
          "above 2911 N (BL-022).\n")
    w("\n## 3. H1 body on the cloth-sim loads, per torso setting\n")
    w(res["body_method_md"])
    w(res["body_table_md"])
    w(res["body_text_md"])
    tb = res.get("top_bar")
    if tb:
        w("\n### 3.2 Crown top bar with the rev 1 guy bridle at x +/-52 (BL-022 request)\n")
        w("H1 beam model (rev C cases, torsos 15 / 19 / 23) with the bag cases from the fine rev 1 sims; the top bar is "
          "split at x +/-52 so the guy forces from the sim (1 g: " + ", ".join(
              f"{k.replace('_', ' in ')} {max(v.values()):.0f} N" for k, v in tb["guy_1g_n"].items()) +
          ") load the bar at the bridle sleeves, combined in the same sets with the lifter reactions (the model's "
          "lifter nodes TB0 / TB2, x +/-70) and every other bag load. Strength = member first-ply margin at the "
          "factored load; fatigue = CFRP FI <= 0.5 at 1.6 g (frame_cg_recheck rule).\n")
        w("| basis | scenario | top-bar strength (set, member) | top-bar fatigue | crown spine | crown legs | corner bond peak |")
        w("|---|---|---|---|---|---|---|")
        for bs, lab in (("sim_rev1_fine", "sim rev 1 fine, guys at x +/-52"), ("beam", "beam (rev C, no guys)")):
            for tg, v in tb[bs].items():
                cm = v["crown_min"]
                w(f"| {lab} | {tg} | **{v['top_bar_strength']:.2f}** ({v['top_bar_strength_set']}, {v['member']}) | "
                  f"{v['top_bar_fatigue']:.2f} | {cm.get('crown_spine', float('nan')):.2f} | {cm.get('crown_leg', float('nan')):.2f} | "
                  f"{cm.get('corner_bond_peak', float('nan')):.2f} |")
        w("\nThe inboard guys raise the bar's local bending (BL-022: 69.9 MPa against 27.9 MPa at 312 N factored, a "
          "hand fixed-fixed check), but the bar's governing case stays the hipbelt-off abuse through the lifters, and "
          "its first-ply margin on the sim loads (1.36) is above the beam basis's (1.25, which carries the whole bag "
          "couple on the crown). Fatigue is far from governing (4.7). Note: the model's lifter reactions sit at x "
          "+/-70, the lifters at x +/-105 (BL-022): with the lifter further out, the bar span between lifter and guy "
          "loads grows; at 4.7 fatigue and 1.36 strength the bar has room for it, to be confirmed in the T1 bar strain "
          "gauge.\n")
    w("\n## 4. Addendum: BL-007 (a) / (c) and BL-017 (c17, OD 17 legs, bore 19) restated per torso\n")
    w(res["addendum_md"])
    w("\n## 5. CA-1 flip points\n")
    w("The PAHT-CF fatigue ratio (1e5 cycles, of static strength) at which each part's fatigue margin reaches 1.0: "
      "flip = 0.30 / margin. CA-1 (coupon test) must show a ratio at or above the flip point of every part that "
      "ships.\n")
    w(res["flip_md"])
    w("\n## 6. Assumptions\n")
    for k, (a, t) in ASSUMPTIONS.items():
        w(f"- ASSUMPTION {k}: {a} Settled by: {t}")
    w("\n## 7. Screens\n")
    for p in res.get("screens", []):
        w(f"- `{Path(p).relative_to(REPO)}`")
    return "\n".join(L) + "\n"


BODY_NAMES = {"h1": "H1 (as released)", "c17b19": "BL-017 (c17): OD 17 x 7 UD legs, crown bore 19",
              "bl007a": "BL-007 (a): fixed crown, H1 body", "bl007c": "BL-007 (c): fixed crown, stays re-sized"}
BASE_NAMES = {"beam": "beam bag loads (rev C weight split + couple)",
              "rev1_fine_cyc": "**cloth sim rev 1, fine (h 25); cinch preload static**",
              "rev1_coarse_cyc": "cloth sim rev 1, coarse (h 40); cinch preload static",
              "rev1_fine": "cloth sim rev 1, fine; cinch preload cycled with g (bound)",
              "rev1_coarse": "cloth sim rev 1, coarse; cinch preload cycled with g (bound)"}
BASE_ORDER = ("beam", "rev1_fine_cyc", "rev1_coarse_cyc", "rev1_fine", "rev1_coarse")


def coarse_fine_md(hv: dict) -> str:
    L = ["Coarse (h 40 mm) vs fine (h 25 mm) cloth mesh, hook magnitude at 1 g (meat):", "",
         "| torso | rev | side | coarse N | fine N | fine / coarse |", "|---|---|---|---|---|---|"]
    pairs = [("15c", "15f", 0, 15), ("15c1", "15f1", 1, 15), ("19c1", "19f1", 1, 19), ("23c1", "23f1", 1, 23)]
    rat = []
    for c, f, rev, t in pairs:
        for s in "RL":
            a, b = hv[c][s]["mag"], hv[f][s]["mag"]
            rat.append(b / a)
            L.append(f"| {t} in | {rev} | {s} | {a:.0f} | {b:.0f} | {b / a:.3f} |")
    hi = max(max(hv[k]["R"]["mag"], hv[k]["L"]["mag"]) for k in hv)
    lr = [abs(hv[k]["L"]["mag"] - hv[k]["R"]["mag"]) / max(hv[k]["L"]["mag"], hv[k]["R"]["mag"]) for k in hv]
    L += ["", f"Fine / coarse ranges {min(rat):.2f} to {max(rat):.2f} per hook: the fine mesh moves load between the "
          "two hooks (and the hinge pins) rather than adding it. The highest single hook is "
          f"{hi:.0f} N ({_lb(hi)}) at 1 g. Left vs right differ by up to {100 * max(lr):.0f} % in one run "
          f"(median {100 * float(np.median(lr)):.0f} %), so the eye is sized on the worse side of every run. The hook "
          "pulls 2 to 8 deg aft of straight down and up to 10 deg sideways (the lateral part loads the inner face of "
          "one cheek and is in the FEA)."]
    return "\n".join(L)


def body_tables(res: dict) -> tuple:
    b = res["body"]
    L = ["| body | load basis | torso 15 in | 19 in | 23 in | min strength | min creep | governing (fatigue) |",
         "|---|---|---|---|---|---|---|---|"]
    for k in BODY_NAMES:
        if k not in b:
            continue
        for bs in BASE_ORDER:
            if bs not in b[k]:
                continue
            v = b[k][bs]
            pt = v["per_torso"]
            cells = " | ".join(f"{pt[t]['fatigue']:.3f}" if t in pt else "-" for t in ("15", "19", "23"))
            fw = v["fatigue_where"]
            L.append(f"| {BODY_NAMES[k]} | {BASE_NAMES[bs]} | {cells} | {v['min']['strength']:.2f} | "
                     f"{v['min']['creep']:.2f} | {fw['torso']:g} in, {fw['where']} |")
    return "\n".join(L)


RECORDED = {  # single-tag (recorded-basis) body fatigue as each ticket published it
    "bl007a": ("frame_fixed_results.json", "a"), "bl007c": ("frame_fixed_results.json", "c"),
    "c17b19": ("crown_diet_results.json", "c17b19_recorded_basis"), "h1": ("crown_diet_results.json", "h1_recorded_basis")}


def recorded_fatigue(k: str) -> float:
    f, key = RECORDED[k]
    d = json.loads((ANALYSIS / f).read_text())
    return float(d["variants"][key]["body"]["min"]["fatigue"] if f.startswith("frame_fixed") else d["body"][key]["min"]["fatigue"])


def narrative(res: dict) -> dict:
    e, b, hv = res["eye"], res["body"], res["hook_vectors"]
    ch = e["cands"].get(e["chosen"]) if e["chosen"] else None
    base27 = e["cands"].get("13.5_8")
    out = {"coarse_fine_md": coarse_fine_md(hv), "body_table_md": body_tables(res)}
    out["body_method_md"] = (
        "The H1 voxel body (frame_h1 solid, D's solver, FI99 rule, crown_diet.body_check) with the rev C bag cases "
        "(static carry, 2.5 g drop, side-hill torsion, hipbelt-off abuse) re-loaded from the cloth sim: per torso, "
        "the sim's frame-side forces at 1 g (both IM3 hooks as vectors at the z 520 stay nodes, both hinge pins at "
        "z 60, the guys at the crown top bar, the spreader / frame / crown contact node by node, under-straps and "
        "wraps at their anchors, the meat-face push reacted at the six IM anchors; ASSUMPTION STRAP_REACT), scaled by "
        "g x load / 68 kg (ASSUMPTION SIM_BOX below: SIM_BODY). Whatever the sim does not put on a frame node (fabric "
        "self-weight, solver residual) goes to the four under-strap pins so each set carries the full bag weight. "
        "Fill and meat are separate scenarios (tags S_fill / S_meat); the non-bag rev C cases (set-down, meat straps, "
        "tall load, overload) are unchanged. Every torso is its own tag (BL-017's like-for-like basis). Fatigue and "
        "creep come from the static-carry sets (1.6 g / factor), strength from every set.\n\n"
        "The beam basis (rev C weight split and the bag couple on the crown bar or on the IM3 hooks) is re-run on the "
        "same per-torso tags as the check of the method: it must reproduce BL-017's H1 per-torso body (fatigue 1.150)."
        "\n").replace("SIM_BOX below: ", "")
    # body text
    T = []
    if "h1" in b:
        hb, hs = b["h1"].get("beam"), b["h1"].get("rev1_fine_cyc")
        hc = b["h1"].get("rev1_coarse_cyc")
        hp = b["h1"].get("rev1_fine")
        if hb and hs:
            T.append(f"\n**H1 on the sim loads (fine): fatigue {hs['min']['fatigue']:.3f}, strength "
                     f"{hs['min']['strength']:.2f}, creep {hs['min']['creep']:.2f}** (beam basis {hb['min']['fatigue']:.3f} / "
                     f"{hb['min']['strength']:.2f} / {hb['min']['creep']:.2f}). Per torso fatigue on the sim: " +
                     ", ".join(f"{t} in {v['fatigue']:.3f}" for t, v in sorted(hs["per_torso"].items())) +
                     f". Governing: {hs['fatigue_where']['where']} at {hs['fatigue_where']['torso']:g} in "
                     f"({hs['fatigue_where']['scenario']}). z 234 joint fatigue {hs['joint_fatigue']:.2f}, branch "
                     f"buckling {hs['buckling_min']:.2f}.")
        if hc and hs:
            T.append(f"Cloth-mesh sensitivity: coarse sim loads give fatigue {hc['min']['fatigue']:.3f} "
                     f"(fine {hs['min']['fatigue']:.3f}).")
        if hp and hs:
            T.append(f"Cinch-preload sensitivity (ASSUMPTION CINCH_STATIC): if the meat straps' cinch loop cycled with "
                     f"the walking g instead of sitting as a static preload, H1's fatigue would be "
                     f"{hp['min']['fatigue']:.3f} (strength {hp['min']['strength']:.2f}, creep {hp['min']['creep']:.2f} with "
                     "the preload in every set).")
    out["body_text_md"] = "\n".join(T) + "\n" + res.get("body_fix_md", "")
    # addendum
    A = ["| body | recorded (one tag per couple) | beam, per torso: 15 / 19 / 23 in | sim fine (cinch static), per torso: 15 / 19 / 23 in | min on sim | sim, cinch cycled (bound) |",
         "|---|---|---|---|---|---|"]
    for k in ("bl007a", "bl007c", "c17b19"):
        if k not in b:
            continue
        cells = []
        for bs in ("beam", "rev1_fine_cyc"):
            v = b[k].get(bs)
            cells.append(" / ".join(f"{v['per_torso'][t]['fatigue']:.3f}" for t in ("15", "19", "23")
                                    if t in v["per_torso"]) if v else "not run")
        mn = b[k]["rev1_fine_cyc"]["min"]["fatigue"] if "rev1_fine_cyc" in b[k] else float("nan")
        bd = b[k]["rev1_fine"]["min"]["fatigue"] if "rev1_fine" in b[k] else float("nan")
        A.append(f"| {BODY_NAMES[k]} | {recorded_fatigue(k):.3f} | {cells[0]} | {cells[1]} | {mn:.3f} | {bd:.3f} |")
    out["addendum_md"] = "\n".join(A) + "\n" + res.get("addendum_text_md", "")
    # flips
    F = ["| part | fatigue margin (basis) | CA-1 flip ratio |", "|---|---|---|"]
    if ch:
        F.append(f"| IM3 cheek {ch['height_mm']:g} x {ch['cheek']:g} mm (recommended) | {ch['design']['fatigue']['value']:.3f} "
                 f"(sim hook + strap, worst grid) | **{ch['ca1_flip_ratio']:.3f}** |")
    if base27:
        F.append(f"| IM3 cheek 27 x 8 mm (adopted today) | {base27['design']['fatigue']['value']:.3f} | "
                 f"{base27['ca1_flip_ratio']:.3f} |")
    for k in BODY_NAMES:
        for bs in ("rev1_fine_cyc", "beam"):
            if k in b and bs in b[k]:
                F.append(f"| {BODY_NAMES[k]} body | {b[k][bs]['min']['fatigue']:.3f} ({BASE_NAMES[bs]}) | "
                         f"{b[k][bs]['ca1_flip_ratio']:.3f} |")
    out["flip_md"] = "\n".join(F) + "\n" + res.get("flip_text_md", "")
    out["summary_md"] = res.get("summary_text_md", "")
    return out


def fix_text(res: dict) -> dict:
    """The H1 sleeve-wall trials (fix_study) as a table and the smallest passing one."""
    fx = res.get("fix") or {}
    if not fx:
        return {"body_fix_md": ""}
    L = ["\n### 3.1 Smallest local fix tried: grow the stay sleeve's outer wall\n",
         "Trials on the governing basis (fine sim, cinch static), smallest first: the outer radius of both stays' "
         "sleeves grown from 13.4 mm over a z band (spreader-clip sections and voids kept). Not an optimised shape: a "
         "first sizing for the print team.\n",
         "| trial (z band, outer r) | added g per frame | fatigue 15 / 19 / 23 in | min fatigue | strength | creep |",
         "|---|---|---|---|---|---|"]
    best = None
    for k, v in fx.items():
        _, z0, z1, ro = k.split("_")
        pt = v["per_torso"]
        L.append(f"| z {z0}-{z1}, r {ro} mm | {v['added_g_one_frame']:.1f} | "
                 f"{' / '.join(format(pt[t]['fatigue'], '.3f') for t in ('15', '19', '23'))} | "
                 f"{v['min']['fatigue']:.3f} | {v['min']['strength']:.2f} | {v['min']['creep']:.2f} |")
        if v["min"]["fatigue"] >= FAT_REQ and (best is None or v["added_g_one_frame"] < best[1]["added_g_one_frame"]):
            best = (k, v, z0, z1, ro)
    if best is None:
        L.append("\n**The 1.15 target cannot be reached by a small local fix.** Growing the sleeve wall outward barely "
                 "moves the governing FI99 (it sits in the crown bore wall, where the carbon leg bears on the bushing "
                 "seat, and is driven by the leg's couple, not by the stay's outer section): +18 g gives +0.010, the "
                 "whole sleeve at +2 mm (+74 g) +0.069, +4 mm (+191 g) +0.130 and still 1.131. H1 passes rev C on "
                 "the sim loads (fatigue 1.001 >= 1.0) but with no margin for scatter, and the result moves from 1.29 "
                 "(coarse sim) to 1.00 (fine sim). What to do is in the report: settle the governing inputs (meat-case "
                 "load split, cinch) with the T1 / T2 strain gauges before re-sizing the sleeve, and treat a bore-side "
                 "change (longer or stiffer bushing seat, the 0.30 PAHT ratio from CA-1) as the design route, not wall "
                 "mass.")
    out = {"body_fix_md": "\n".join(L) + "\n"}
    if best:
        k, v, z0, z1, ro = best
        out["fix_best"] = {"key": k, "text": f"grow both stay sleeves to r {ro} mm over z {z0}-{z1}: +{v['added_g_one_frame']:.1f} g "
                           f"per frame, H1 fatigue {v['min']['fatigue']:.3f} on the sim loads."}
    else:
        worst = max(fx.values(), key=lambda v: v["min"]["fatigue"])
        out["fix_best"] = {"key": None, "text": f"none of the sleeve-wall trials reached {FAT_REQ} (best "
                           f"{worst['min']['fatigue']:.3f} at +{worst['added_g_one_frame']:.1f} g); see 3.1."}
    return out


def judgement(res: dict) -> dict:
    """Data-driven text for the summary, the body fix, the misuse / top-bar sections and the addendum."""
    e, b = res["eye"], res["body"]
    ch = e["cands"][e["chosen"]] if e["chosen"] else None
    c27 = e["cands"].get("13.5_8")
    mis = res.get("misuse_eye")
    tb = res.get("top_bar")
    fx = res.get("fix", {})
    h = b.get("h1", {})
    hs, hb, hc, hp = (h.get(k) for k in ("rev1_fine_cyc", "beam", "rev1_coarse_cyc", "rev1_fine"))
    S = []
    hk = res["hook_vectors"]
    f15 = max(hk["15f1"]["R"]["leg_sum"], hk["15f1"]["L"]["leg_sum"])
    S.append(f"- **IM3 hook force (task 1):** fine 15 in meat, rev 1: {f15:.0f} N leg sum ({hk['15f1']['L']['mag']:.0f} N as a "
             f"vector, {hk['15f1']['L']['aft_of_down_deg']:.0f} deg aft, {hk['15f1']['L']['lateral_deg']:.0f} deg sideways); "
             f"coarse {max(hk['15c1']['R']['leg_sum'], hk['15c1']['L']['leg_sum']):.0f} N. Rev 0 fine (this ticket's run) "
             f"{max(hk['15f']['R']['leg_sum'], hk['15f']['L']['leg_sum']):.0f} N. All 18 hook vectors (2 revs, 2 meshes, 3 torsos, "
             "R/L) go into the eye check.")
    if ch and c27:
        S.append(f"- **IM3 eye (task 2):** the adopted 27 mm cheek reaches fatigue {c27['design']['fatigue']['value']:.3f} on the "
                 f"worst hook + strap vector, but {c27['sensitivity']['fatigue_dir_plus_scatter']:.3f} if the pull sits 10 deg "
                 f"further aft. **Recommended: {ch['height_mm']:g} mm tall x {ch['cheek']:g} mm thick "
                 f"({ch['pair_delta_vs_27mm_g']:+.2f} g a pair over 27 mm): fatigue {ch['design']['fatigue']['value']:.3f}** "
                 f"(worst of h 1.0 / 0.8 / 0.7 mm, all hooks; {ch['sensitivity']['fatigue_dir_plus_scatter']:.3f} with +10 deg), "
                 f"strength {ch['design']['strength']['value']:.2f}, creep {ch['design']['creep']['value']:.2f}, CA-1 flip "
                 f"{ch['ca1_flip_ratio']:.3f}. Spreader gap {ch['clearance']['gap_mm']:.1f} mm (rule >= 6).")
    if mis:
        m27, m28 = mis["cands"].get("13.5_8"), mis["cands"].get("14_8")
        S.append(f"- **Guys-off misuse (BL-022 basis {mis['factored_n']:.0f} N factored):** printed eye strength "
                 f"{m28['strength']['goff']:.2f} (28 mm) / {m27['strength']['goff']:.2f} (27 mm) for the hook alone; "
                 f"{m28['strength']['goff_strap']:.2f} / {m27['strength']['goff_strap']:.2f} with the rev C strap at full "
                 "value on the same eye. Rev C asks >= 1.0 at the factored load: pass; the 1.5 cheek target is met by "
                 "28 mm for the hook alone and missed (1.45) only for the stacked upper bound.")
    if tb:
        t = tb["sim_rev1_fine"]
        tmin = min(t.values(), key=lambda v: v["top_bar_strength"])
        fmin = min(v["top_bar_fatigue"] for v in t.values())
        bmin = min(v["top_bar_strength"] for v in tb["beam"].values())
        S.append(f"- **Crown top bar with the rev 1 guys at x +/-52 (BL-022 request):** strength {tmin['top_bar_strength']:.2f} "
                 f"({tmin['top_bar_strength_set']}, member {tmin['member']}), fatigue {fmin:.2f} (CFRP FI <= 0.5 at "
                 f"1.6 g), against {bmin:.2f} on the beam basis. The guys do not govern the bar: the hipbelt-off abuse case "
                 "through the lifters does, as before.")
    if hs and hb:
        S.append(f"- **H1 body on the sim loads (task 3):** strength {hs['min']['strength']:.2f}, **fatigue "
                 f"{hs['min']['fatigue']:.3f}** (fine sim, 23 in meat; fill {min(v['fatigue'] for k, v in hs['by_torso'].items() if 'fill' in k):.2f}), "
                 f"creep {hs['min']['creep']:.2f}. Beam basis {hb['min']['fatigue']:.3f}. Coarse sim {hc['min']['fatigue']:.3f}"
                 f". **{'Below' if hs['min']['fatigue'] < FAT_REQ else 'At or above'} the {FAT_REQ} target.**" if hc else "")
    if fx:
        best = res.get("fix_best")
        if best:
            S.append(f"- **Body fix:** {best['text']}")
    ad = []
    for k in ("bl007a", "bl007c", "c17b19"):
        if k in b and "rev1_fine_cyc" in b[k]:
            ad.append(f"{BODY_NAMES[k].split(':')[0]} {b[k]['beam']['min']['fatigue']:.3f} beam / "
                      f"{b[k]['rev1_fine_cyc']['min']['fatigue']:.3f} sim")
    if ad:
        S.append("- **Restated per torso (task 4):** " + "; ".join(ad) + ". None reaches 1.15 on the sim loads.")
    return {"summary_text_md": "\n".join(x for x in S if x)}


def _write(res: dict):
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    DOC.write_text(write_md(res))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true", help="run any missing eye / body solves (long)")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    if a.run:
        eye_study_rev1()
        body_study()
    res = compute()
    res.update(fix_text(res))
    res.update(judgement(res))
    res.update(narrative(res))
    if not a.no_plots:
        SCREENS.mkdir(parents=True, exist_ok=True)
        res["screens"] = [plot_eye(res, SCREENS / f"{SHOT}1.png"), plot_body(res, SCREENS / f"{SHOT}2.png")]
        if res["eye"]["chosen"]:
            res["screens"].append(plot_eye_field(res, SCREENS / f"{SHOT}3.png"))
    _write(res)
    print(DOC)



# ======================================================================================= 2c. guys-off misuse (BL-022)
MISUSE_RUN = "F_PR15_goff_sm8"         # BL-022: coarse, 8 mm start, converged; IM3 970.4 N leg sum at 1 g (governs)
MISUSE_FINE_RUN = "F_PR15_fineFM_goff_sm8"


def misuse_goff() -> dict:
    """Guys-off IM3 hook vectors (meat, 15 in), cached by the extraction (OUT/misuse_goff.json)."""
    return json.loads((OUT / "misuse_goff.json").read_text())


def misuse_dirs() -> tuple:
    """Load directions for the guys-off eye check: the governing coarse hook at its leg-sum magnitude (BL-022's
    2911 N factored basis), alone and with the rev C strap (both factored x 3)."""
    g = misuse_goff()[MISUSE_RUN]["hooks"]
    side = max("RL", key=lambda s: g[s]["leg_sum"])
    v = np.asarray(g[side]["vec"], float)
    F = FACTOR * g[side]["leg_sum"] * v / np.linalg.norm(v)
    loads = {"goff": F.tolist(), "goff_strap": (F + FACTOR * strap_vector_1g()).tolist()}
    return loads, side, float(g[side]["leg_sum"])


def misuse_eye(cands=((13.5, 8.0), (14.0, 8.0)), grids=GRIDS, log=print) -> dict:
    loads, side, leg = misuse_dirs()
    out = {"side": side, "leg_sum_1g_n": leg, "factored_n": FACTOR * leg, "loads_n": loads, "cands": {}}
    for hz, ch in cands:
        per = {}
        for h in grids:
            r = eye_cached(hz, ch, h, loads, tag="_goff")
            per[f"{h:g}"] = {k: 1.0 / v["fi99"] for k, v in r["loads"].items()}
        out["cands"][f"{hz:g}_{ch:g}"] = {"per_grid": per,
                                          "strength": {k: min(per[g][k] for g in per) for k in loads}}
        if log:
            log(f"misuse eye {2 * hz:g} mm: {out['cands'][f'{hz:g}_{ch:g}']['strength']}")
    return out


# ======================================================================================= 3d. local fix trials (H1)
def sleeve_wrap_solid(z0: float, z1: float, r_out: float = 15.5) -> tuple:
    """H1 solid with the stay sleeve's outer wall grown to ``r_out`` (from H1's 13.4 mm) between z ``z0`` and ``z1``
    on both stays, outside the passive voids and the spreader-clip sections (clips are not re-made). Returns
    (solid, added g)."""
    from huntkit.gendesign import crown_diet as CD
    from huntkit.gendesign import frame_fixed as FF
    from huntkit.gendesign import frame_h1 as H1
    from huntkit.gendesign.spreader import CLIP_Z
    c = H1.base()
    dom = c["dom"]
    cen = c["cen"]
    s = CD._h1_solid().copy()
    r = FF._stay_r(cen)
    z = cen[:, 2]
    clip = np.zeros(len(z), bool)
    for zz in CLIP_Z:
        clip |= np.abs(z - zz) <= 6.0
    add = (r > 13.0) & (r <= r_out) & (z >= z0) & (z <= z1) & ~dom.passive_void & ~s & ~clip & (np.abs(cen[:, 0]) > 60)
    s |= add
    return s, float(add.sum() * H1.H ** 3 * 1.06e-3)


FIX_TRIALS = ((400.0, 544.0, 15.5), (300.0, 544.0, 15.5), (160.0, 544.0, 15.5), (160.0, 544.0, 17.5))


def fix_study(trials=FIX_TRIALS, log=print) -> dict:
    """H1 + a grown sleeve wall (sleeve_wrap_solid) on the governing basis (sim rev 1 fine, cinch static), smallest
    first; stops at the first trial reaching FAT_REQ. Cached per trial."""
    global CYCLIC_ONLY
    out = {}
    sets = None
    for z0, z1, ro in trials:
        nm = f"h1fix_{z0:g}_{z1:g}_{ro:g}"
        p = OUT / f"body_{nm}__rev1_fine_cyc.json"
        if p.exists():
            d = json.loads(p.read_text())
        else:
            if sets is None:
                CYCLIC_ONLY = True
                try:
                    sets = sim_sets_for("h1", SIM_BASES["rev1_fine"], sim_forces(rev=1), "S")
                finally:
                    CYCLIC_ONLY = False
            solid, g = sleeve_wrap_solid(z0, z1, ro)
            d = body_eval(nm, "h1", solid, sets, log=log)
            d["added_g_one_frame"] = g
            p.write_text(json.dumps(d, default=float))
        out[nm] = d
        if d["min"]["fatigue"] >= FAT_REQ:
            break
    return out


if __name__ == "__main__":
    main()
