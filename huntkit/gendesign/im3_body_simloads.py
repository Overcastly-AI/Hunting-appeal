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
    "PAHT_FAT": ("PAHT CF fatigue_1e5_ratio 0.30 (record ASSUMPTION, no published data).",
                 "CA-1 coupon test (TEST_PLAN): the flip points in section 5 say what each part needs."),
    "SIM_BODY": ("Bag cases on the body: the sim's 1 g frame-side forces scaled by g x load / 68 kg; side-hill "
                 "keeps the beam's lateral and downhill part, the upright part is replaced by the sim x cos 25 deg.",
                 "T9 loaded CG + frame strain gauges at the stays z 450-550 in the T1 carry test."),
    "SETDOWN_BEAM": ("The single-stay set-down keeps the beam's lumped bag masses (inertia relief through one "
                     "foot); it does not enter fatigue.", "T5 drop / set-down test."),
    "STRAP_REACT": ("Meat case in the sim: the meat-face push (strap cinch + overturning) is reacted at the six "
                    "IM anchors as aft pulls (150 N cinch each + the overturning share per level), and the 30 % "
                    "of the meat weight the straps carry goes down equally at the six anchors.",
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
        pm = PackModel(load_scenario(str(S.scenario_path(torso))), fine=fine, verbose=False)
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
    for t in sim.terms:
        nm = str(getattr(t, "name", ""))
        if nm.startswith("contact_"):
            r = t(x, hess=False)
            g = np.asarray(r[1] if isinstance(r, tuple) else r).reshape(-1, 3)
            fb = -g                          # force on the bag nodes
            m = np.linalg.norm(fb, axis=1) > 1e-6
            if not m.any():
                continue
            F = fb[m].sum(0)
            w = np.linalg.norm(fb[m], axis=1)
            cen = (x[m] * w[:, None]).sum(0) / w.sum()
            out[nm] = {"xyz": [float(v) for v in cen], "f": [-float(v) for v in F], "kind": "contact",
                       "z_lo": float(x[m, 2].min()), "z_hi": float(x[m, 2].max()),
                       "node_f": [[float(v) for v in xx] + [-float(v) for v in ff] for xx, ff in zip(x[m], fb[m])]}
    meat = rj["cases"][case].get("meat") or {}
    return {"run": run, "torso": torso, "case": case, "h_mm": float(rj["mesh"]["h_mm"]),
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


def eye_fea(half_z: float, cheek: float, loads: dict, h: float = 1.0) -> dict:
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
        added = float((yoke & ~stay).sum() * h ** 3 * pa["rho"] / 1e6)
    finally:
        BA.HALF_Z, BA.CHEEK = old
    return {"half_z": half_z, "cheek": cheek, "h": h, "added_g": added, "n_elem": int(solid.sum()), "loads": out}


SWEEP_DEG = (0.0, 15.0, 30.0, 45.0, 60.0, 80.5)     # pull angle aft of straight down (80.5 = rev C IM3 vector)


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


# runs used (outputs/clothsim/corrie_f/<run>, meat case unless named); F_PR15_fine_meat_BL021 is this ticket's
# fine (h 25 mm) run of CORRIE F 15 in meat (corrie_f_sim scenario cf_PR15, own runner, nothing else written)
RUNS = {"15c": ("F_PR15", 15), "15f": ("F_PR15_fine_meat_BL021", 15), "19c": ("F_PR19", 19), "23c": ("F_PR23", 23)}
SIMFORCES = OUT / "sim_frame_forces.json"
CANDIDATES = ((12.5, 8.0), (13.5, 8.0), (14.0, 8.0), (15.0, 8.0), (16.0, 8.0), (13.5, 9.0), (13.5, 10.0),
              (12.5, 10.0), (15.0, 9.0), (14.0, 10.0))


def sim_forces(refresh: bool = False) -> dict:
    """Frame-side 1 g forces of the four runs (meat; fill too for the coarse runs), cached in OUT."""
    if SIMFORCES.exists() and not refresh:
        return json.loads(SIMFORCES.read_text())
    res = {}
    for key, (run, t) in RUNS.items():
        for case in (("meat",) if key == "15f" else ("fill", "meat")):
            res[f"{run}|{case}"] = frame_forces_from_run(run, t, case)
    OUT.mkdir(parents=True, exist_ok=True)
    SIMFORCES.write_text(json.dumps(res, default=float))
    return res


def eye_hooks(sf: dict) -> dict:
    """1 g IM3 hook vectors per run and side (meat case), from the frame forces."""
    out = {}
    for key, (run, _t) in RUNS.items():
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
    if cinch > 0:
        dn = float(m.get("to_strap_anchors_n", 0.0)) / 6.0
        for z, o in zip(IM_Z, ot):
            for sd in (1.0, -1.0):
                add(gp, _stay_node(model, sd, z), [0.0, o / 2.0, -dn])
                add(fx, _stay_node(model, sd, z), [0.0, cinch, 0.0])
    tot = sum(gp.values()) + (sum(fx.values()) if fx else 0.0)
    resid = np.array([0.0, 0.0, -total_kg * G_ACC]) - tot
    pins = [_stay_node(model, sd, z) for z in US_Z for sd in (1.0, -1.0)]
    for nid in pins:
        add(gp, nid, resid / len(pins))
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
        ff, kg = simp
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
        for k, v in fixed.items():
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


TORSO_RUN = {15: "F_PR15", 19: "F_PR19", 23: "F_PR23"}


def sim_env(torso: float, sf: dict, cases=("fill", "meat"), fine15: bool = True) -> dict:
    """Rev C envelope for one torso with the bag cases on the sim forces: one scenario per sim case (tags S_fill /
    S_meat; the couple variants no longer apply). At 15 in the
    meat case uses this ticket's fine run (``fine15``). The beam's non-bag cases (set-down, meat straps, tall, overload)
    ride in the first scenario."""
    from huntkit.fea import load_standard as LS
    env0 = LS.ls1_envelope("C")
    env = {}
    ti = int(round(torso))
    for cn in cases:
        run = RUNS["15f"][0] if (fine15 and ti == 15 and cn == "meat") else TORSO_RUN[ti]
        ff = sf[f"{run}|{cn}"]
        lst = []
        for c in env0["crown_bar"]:
            if c.name in BAG_CASES:
                c = copy.copy(c)
                c.params = {**c.params, "sim_ff": (ff, sim_total_kg(run, cn))}
                lst.append(c)
        if cn == cases[0]:          # the beam's non-bag cases ride in the first scenario (each tag needs a carry set)
            lst += [c for c in env0["crown_bar"] if c.name not in BAG_CASES]
        env[f"sim_{cn}"] = lst
    return env


def sim_sets(runner, torsos=(15.0, 19.0, 23.0), sf: dict | None = None, **kw) -> list:
    """LoadSets on the sim bag loads. ``runner(torso)`` runs the caller's beam_runs for one torso (it reads
    ls1_envelope and TAGS at call time, both swapped here) and returns its LoadSets."""
    from huntkit.fea import load_standard as LS
    from huntkit.gendesign import rev_c_verification as RV
    sf = sf or sim_forces()
    oe = LS.ls1_envelope
    sets = []
    _install_sim_loads()
    RV.TAGS.update({"sim_fill": "S_fill", "sim_meat": "S_meat"})
    try:
        for t in torsos:
            env = sim_env(t, sf, **kw)
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
