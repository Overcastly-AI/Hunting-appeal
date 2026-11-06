"""Production frame re-check at the cloth-sim load CG (designs/pack_5200/analysis/frame_cg_recheck.md).

The cloth simulator (analysis/cloth_sim.md, bag_top_anchor.md) puts the contents CG further aft than HA-LS-1 rev B
assumes (bag 180 mm, meat 150 mm). This module re-runs the PRODUCTION frame at several CG offsets:

- printed body: the socket-free PAHT-CF branch body (``spreader_layout.raster(None, 2.0)``, the body the release
  checks use, 2 mm voxels), every HA-LS-1 rev B case at torso 15 / 19 / 23 in, loads from the v2 beam model
  (``frame_topopt._extract``), same FI99 rule as ``frame_production.verify_solid``;
- carbon crown (legs, top bar, spine, corner joints, bushings) from the beam model (``huntkit.fea``);
- torso adjust: toothed rack + pawl (rack capacity, printed pawl cheek with the 304 bushing) and the 3:1 pulley;
- crown top-bar anchor loads (bag top ties / guys / a crown pocket);
- Sandwich v2 spreader (``spreader.evaluate``) with the meat face load scaled by the CG offset.

Offsets are applied through the existing LoadCase fields (``cg_aft_mm``) plus three additive options in
``huntkit.fea.load_cases`` (``cg_z_mm``, ``params.couple_top_group``, ``params.extra_nodal_1g``). HA-LS-1 itself is
not changed here; the rev C draft lives in the analysis doc.
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

from . import frame_topopt as ft

ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
SCREENS = REPO_ROOT / "outputs" / "screens"
OUT = REPO_ROOT / "outputs" / "frame_cg_recheck"
TORSOS = (15, 19, 23)

BAG_CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "hipbelt_off_abuse")
MEAT_CASES = ("meat_straps", "overload_haul")
TALL_CASES = ("tall_load", "tall_load_posts")
CODE = {"static_carry": "C1", "drop_2p5g": "C2", "side_hill_torsion": "C3", "single_stay_setdown": "C4",
        "meat_straps": "C5", "tall_load": "C6", "tall_load_posts": "C6p", "overload_haul": "C7",
        "hipbelt_off_abuse": "C8"}
ORDER = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "meat_straps", "tall_load",
         "tall_load_posts", "overload_haul", "hipbelt_off_abuse")

# rack / pawl / pulley (geometry.yaml frame.crown_retention, build_geometry.py)
RACK_CAPACITY_N = 5328.0
PULLEY_MU = 0.10                      # UHMWPE-lined guides (geometry.yaml)
PULLEY_WRAPS_RAD = (np.pi, np.pi, np.pi / 2)   # ASSUMPTION: A and B 180 deg, C a 90 deg redirect to the cam
CAM_SLIP_N = 700.0                    # ASSUMPTION carried from build_geometry.py (no DB record)
TAIL_PULL_LIMIT_N = 200.0             # ASSUMPTION: one-hand tail pull a wearer can apply while walking

# crown top-bar anchor (bag_top_anchor.md section 7): <= 70 N per side at 1 g
ANCHOR_N_1G = 70.0


@dataclass
class Scenario:
    tag: str
    label: str
    bag: float                  # C1-C4, C8 bag CG aft (mm)
    meat: float                 # C5, C7
    tall: float                 # C6, C6p
    cg_z: float | None = None   # contents CG height for the side-hill lateral moment (None = rev B node heights)
    couple_top: str | None = None   # None = crown top bar (rev B); "strap_upper" = IM3 anchors on the upper bar
    anchor: dict | None = None      # top-anchor extra loads on the meat case: {"where": "x70"|"x100"|"pocket", "elev": deg}
    cases: tuple = ORDER
    split_x: float = 100.0          # top-bar nodes inserted at +/- split_x (95 for the final hood + guys)
    anchor_cases: tuple = ("meat_straps",)

    def case_list(self):
        from huntkit.fea.load_standard import ls1_cases
        out = []
        for c in ls1_cases(self.bag):
            if c.name not in self.cases:
                continue
            if c.name in BAG_CASES:
                c.cg_aft_mm = float(self.bag)
                c.cg_z_mm = self.cg_z
                if self.couple_top:
                    c.params = {**c.params, "couple_top_group": self.couple_top}
            elif c.name in MEAT_CASES:
                c.cg_aft_mm = float(self.meat)
            elif c.name in TALL_CASES:
                c.cg_aft_mm = float(self.tall)
            if self.anchor and c.name in self.anchor_cases:
                c.params = {**c.params, "_anchor": dict(self.anchor)}
            out.append(c)
        return out


def scenarios() -> dict[str, Scenario]:
    """(a) rev B, (b) the cloth-sim envelope, (c) the bag as-is worst offset, plus sensitivities."""
    S = {
        "a": Scenario("a", "(a) HA-LS-1 rev B: bag 180, meat 150, tall 160", 180.0, 150.0, 160.0),
        # ASSUMPTION: C6/C6p take the same +25 mm as C5/C7 (the envelope gives none for them)
        "b": Scenario("b", "(b) envelope: bag 205 @ z 550, meat 175, tall 185", 205.0, 175.0, 185.0, 550.0),
        "c": Scenario("c", "(c) bag as-is: 223 mm on every case @ z 550", 223.0, 223.0, 223.0, 550.0),
        "b_im3": Scenario("b_im3", "(b) with the bag couple on the IM3 hooks (z 520) instead of the crown bar",
                          205.0, 175.0, 185.0, 550.0, couple_top="strap_upper", cases=BAG_CASES),
        "c_im3": Scenario("c_im3", "(c) with the bag couple on the IM3 hooks (z 520)", 223.0, 223.0, 223.0, 550.0,
                          couple_top="strap_upper", cases=BAG_CASES),
    }
    for where in ("x70", "x100", "pocket"):
        S[f"b_anc_{where}"] = Scenario(f"b_anc_{where}", f"(b) C5 + top anchor {where}, 70 N/side at 1 g, horizontal",
                                       205.0, 175.0, 185.0, 550.0, anchor={"where": where, "elev": 0.0},
                                       cases=("meat_straps",))
    return S


def sweep_scenarios(offsets=(150.0, 180.0, 205.0, 223.0, 250.0)) -> dict[str, Scenario]:
    """Every case at one common offset (for the SF vs CG plot), CG z 550, couple on the crown bar."""
    return {f"s{e:g}": Scenario(f"s{e:g}", f"sweep {e:g} mm", e, e, e, 550.0) for e in offsets}


# ============================================================================ beam model (crown, pawl, pulley)
def split_top_bar(model: dict, x_abs: float = 100.0) -> dict:
    """Insert top-bar nodes TBL100 / TBR100 at x = -/+ x_abs (between TB0/TB2 and the corners) so a tie or guy
    can load the bar there. Members and the corner joints are re-pointed. Returns a new model dict."""
    m = copy.deepcopy(model)
    nodes = m["nodes"]
    for tag, a, b, s in (("L", "CLtop", "TB0", -1.0), ("R", "TB2", "CRtop", 1.0)):
        mid_ = f"{a}-{b}"
        mem = next((q for q in m["members"] if q["id"] == mid_), None)
        if mem is None:
            continue
        pa, pb = np.array(nodes[a], float), np.array(nodes[b], float)
        f = (s * x_abs - pa[0]) / (pb[0] - pa[0])
        nid = f"TB{tag}{int(x_abs)}"
        nodes[nid] = list(map(float, pa + f * (pb - pa)))
        i = m["members"].index(mem)
        m1 = {**mem, "id": f"{a}-{nid}", "nodes": [a, nid]}
        m2 = {**mem, "id": f"{nid}-{b}", "nodes": [nid, b]}
        m["members"][i:i + 1] = [m1, m2]
        for j in m["joints"]:
            j["members"] = [(m1["id"] if a.startswith("C") else m2["id"]) if q == mid_ else q for q in j["members"]]
    return m


def anchor_loads_1g(model: dict, where: str, elev_deg: float = 0.0, n_side: float = ANCHOR_N_1G) -> dict:
    """Per-1 g nodal loads of the bag top-anchor on the crown top bar. The bar is pulled toward the bag
    (+y, aft) at ``elev_deg`` above horizontal (a tie or guy pulls the bag top forward; its reaction on the bar
    is aft). ``pocket`` = a crown pocket capturing the bar: the same total as a line load over x -100..+100."""
    d = np.array([0.0, np.cos(np.radians(elev_deg)), np.sin(np.radians(elev_deg))])
    if where == "x70":
        return {"TB0": n_side * d, "TB2": n_side * d}
    if where == "x100":
        return {"TBL100": n_side * d, "TBR100": n_side * d}
    if where == "pocket":
        trib = {"TBL100": 15.0, "TB0": 50.0, "TB1": 70.0, "TB2": 50.0, "TBR100": 15.0}   # mm, sums to 200
        q = 2 * n_side / 200.0
        return {k: q * L * d for k, L in trib.items()}
    if where == "hood_guys":
        return hood_guy_loads_1g(model)
    raise ValueError(where)


# Final attachment (bag_attachment.md section 1-2, attach_system_results.json factored_n, C5 factor 3.0):
HOOD_1G_N = 52.5            # crown hood capture, total, aft, distributed over x -95..+95
GUY_1G_N = 34.6             # each top side guy, from the hood ear at x +/-95 to the bag corner (+/-149, z 752)
GUY_CORNER = (149.0, 752.0)
GUY_FREE_MM = 314.0         # bag_attachment.md TG row: free length about 314 mm at 19 in
GUY_DY_MM = float(np.sqrt(GUY_FREE_MM ** 2 - (149.0 - 95.0) ** 2 - (752.0 - 702.6) ** 2))   # ASSUMPTION: fixed aft run


def hood_guy_loads_1g(model: dict) -> dict:
    """Hood: 52.5 N aft spread over x +/-95 by tributary length; guys: 34.6 N each at TB?95 toward the bag corner
    (+/-149, y_bar + GUY_DY_MM, 752). Needs the model split at x +/-95 (``split_top_bar(m, 95)``)."""
    nodes = model["nodes"]
    out = {}
    trib = {"TBL95": 12.5, "TB0": 47.5, "TB1": 70.0, "TB2": 47.5, "TBR95": 12.5}     # mm, sums to 190
    for k, L in trib.items():
        out[k] = np.array([0.0, HOOD_1G_N * L / 190.0, 0.0])
    for tag, s in (("L", -1.0), ("R", 1.0)):
        p = np.asarray(nodes[f"TB{tag}95"], float)
        d = np.array([s * GUY_CORNER[0], p[1] + GUY_DY_MM, GUY_CORNER[1]]) - p
        out[f"TB{tag}95"] = out.get(f"TB{tag}95", np.zeros(3)) + GUY_1G_N * d / np.linalg.norm(d)
    return out


def _crown_rows(res, model, case) -> dict:
    """Crown members, corner joints, bushings, pawl and harness reactions for one beam run (limit load)."""
    from huntkit.fea.joints import check_frame_joints
    from huntkit.fea.pack5200 import crown_checks
    req = float(case.required_sf)
    out = {"members": {}, "joints": {}, "bushings": {}}
    for m in res.members:
        g = m["group"]
        if g.startswith(("crown_leg", "crown_top_bar", "crown_spine", "ext_post")):
            key = "crown_leg" if g.startswith("crown_leg") else g
            sf = float(m["sf"]) / req
            if sf < out["members"].get(key, (np.inf,))[0]:
                out["members"][key] = (sf, m["id"])
    js = [j for j in model.get("joints", []) if j["id"].startswith(("crown_corner", "post_socket"))]
    for j in check_frame_joints(res, js):
        k = j["joint"].rsplit("_", 1)[0]
        a, p = float(j["sf_avg"]) / req, float(j["sf_peak"])          # HA-LS-1: peak >= 1.0 at limit
        old = out["joints"].get(k, (np.inf, np.inf, ""))
        out["joints"][k] = (min(old[0], a), min(old[1], p), j["member"] if a < old[0] else old[2])
    for cc in crown_checks(res, model):
        if cc.get("retention") or cc.get("info"):
            continue
        name = cc["check"]
        if "UHMWPE bushing bearing" in name or "leg ring crush" in name:
            k = "bushing_bearing" if "bearing" in name else "leg_ring_crush"
            out["bushings"][k] = min(out["bushings"].get(k, np.inf), float(cc["sf"]) / req)
    lf = res.meta.get("link_forces", {})
    out["pawl_n"] = [float(v) for v in np.asarray(lf.get("pawl", np.zeros(6)))[:3]]
    rx = res.reactions
    out["shoulder_n"] = [float(v) for v in np.asarray(rx.get("SP150", np.zeros(6)))[:3]]
    lif = np.zeros(3)
    for n in model["groups"].get("lifter", []):
        lif += np.asarray(rx.get(n, np.zeros(6)))[:3]
    out["lifter_n"] = [float(v) for v in lif]
    out["buckling"] = (float(res.buckling_sf) / (1.5 * req)) if getattr(res, "buckling_factors", None) else None
    return out


def beam_runs(sc: Scenario, torsos=TORSOS, buckling: bool = True, log=print, over: dict | None = None):
    """Solve the scenario on the beam model. Returns (LoadSets for the voxel body, crown rows).
    ``over``: frame.yaml param overrides (e.g. a thicker crown section) for the fix study."""
    over = over or {}
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import TABLE
    sets, rows = [], []
    for t in torsos:
        fm = split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=False, **over),
                           sc.split_x)
        fmp = None
        for c in sc.case_list():
            c = copy.copy(c)
            c.params = dict(c.params)
            anc = c.params.pop("_anchor", None)
            if anc:
                L1 = anchor_loads_1g(fm, anc["where"], anc["elev"])
                kgs = c.load_kg / 68.0                      # C7 (91 kg): anchor loads scale with the contents
                c.params["extra_nodal_1g"] = {k: list(kgs * np.asarray(v)) for k, v in L1.items()}
            c.buckling = buckling and c.kind != "setdown"
            m = fm
            if c.name == "tall_load_posts":
                fmp = fmp or split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=True,
                                                                     **over), sc.split_x)
                m = fmp
            res = c.run(m)
            ls = ft._extract(res, m, c, t, TABLE)
            ls.key = f"{sc.tag}:{ls.key}"
            sets.append(ls)
            rows.append({"scenario": sc.tag, "case": c.name, "torso": float(t), "factor": float(c.required_sf),
                         "g": float(c.g_factor), **_crown_rows(res, m, c)})
        if log:
            log(f"  [{sc.tag}] beam model torso {t} in: {len(sc.case_list())} cases")
    return sets, rows


# ============================================================================ printed body (voxel FE)
def region_label(p) -> str:
    x, y, z = (float(v) for v in p)
    if np.hypot(x, z - 120.0) < 40.0 and y < -25.0:
        return "hip-pivot boss"
    if z < 40.0:
        return "stay foot"
    if abs(x) > 95.0:
        side = "R" if x > 0 else "L"
        if z >= 160.0:
            return f"stay {side} sleeve (crown bore wall)" + (" at the top bushing" if z > 470 else "")
        return f"stay {side} below the sleeve"
    if z > 480.0:
        return "upper bar / pawl housing"
    if 300.0 < z < 360.0:
        return "mid bar z 330"
    if z < 200.0:
        return "lumbar struts / pan"
    return "inboard branch"


def verify_sets(dom, solid, sets, material: str = "pa12_cf_fdm_paht", keep_env=(), sections=(), log=print) -> dict:
    """``frame_production.verify_solid`` FI99 rule on many tagged load sets at once (one factorization).
    Exclusion of clamp / load-patch elements is the union over the sets that share a scenario tag, as
    verify_solid does over its 27 sets."""
    from huntkit.materials import load
    m = load(material)
    E = float(m.require("youngs_modulus_xy_mpa"))
    s_xy = float(m.require("tensile_strength_xy_mpa"))
    s_z = float(m.require("tensile_strength_z_mpa"))
    knock = float(m.get("env_knockdown_ratio", 0.8))
    t0 = time.time()
    g = dom.grid
    idx = np.where(solid)[0]
    cen = g.elem_centers()[idx]
    _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    clamp = np.zeros(g.nn, bool)
    clamp[np.where(fixed[0::3])[0]] = True
    # one factorization, solved per scenario tag (memory: <= 27 dense load columns at a time)
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(g.h, 1.0, ft.NU))
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    K.sort_indices()
    try:
        import pypardiso
        solver = pypardiso.PyPardisoSolver(mtype=2)
        solver.factorize(K)
        solve = lambda Fr: solver.solve(K, np.ascontiguousarray(Fr))
    except ImportError:                    # pragma: no cover
        import scipy.sparse as sps
        import scipy.sparse.linalg as spla
        lu = spla.splu((K + sps.triu(K, 1).T).tocsc())
        solve = lu.solve
    tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
    rows, env = [], {}
    for tg in tags:
        tsets = [s for s in sets if s.key.split(":")[0] == tg]
        F, _ = ft.assemble_loads(dom, tsets, solid_mask=solid)
        Ur = solve(F[rs.free]).reshape(rs.free.size, -1)
        U = np.zeros((g.ndof, len(tsets)))
        U[rs.free] = Ur / E
        Fn = np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2))
        ex = (clamp | (Fn > 0))[g.enodes].any(axis=1)[idx]
        del F, Ur
        for k, ls in enumerate(tsets):
            _, S = ft.element_stress(g, U[:, k], solid, E)
            fi = ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, s_xy, s_z, knock)
            ok = fi[~ex]
            fi99 = float(np.percentile(ok, 99))
            hot = np.where(~ex & (fi >= np.percentile(ok, 99.8)))[0]
            w = fi[hot]
            loc = (cen[hot] * w[:, None]).sum(0) / w.sum()
            pk = hot[np.argmax(fi[hot])]
            rows.append({"set": ls.key, "scenario": tg, "case": ls.case, "torso": ls.torso, "factor": ls.factor,
                         "fi99": fi99, "sf": 1.0 / max(fi99, 1e-9), "loc": [float(v) for v in loc],
                         "where": region_label(cen[pk]), "peak_xyz": [float(v) for v in cen[pk]]})
            if tg in keep_env:
                env[tg] = np.maximum(env.get(tg, np.zeros(idx.size)), np.where(ex, 0.0, fi))
            if ls.key in sections:
                rows[-1]["section_z234"] = ft.section_resultants(dom, solid, U[:, k], 234.0, E=E)
        del U
        if log:
            log(f"  voxel [{tg}] {len(tsets)} sets, {time.time() - t0:.0f} s")
    try:
        solver.free_memory(everything=True)
    except Exception:
        pass
    return {"rows": rows, "env": env, "centers": cen, "E": E, "material": material,
            "fat_ratio": float(m.get("fatigue_1e5_ratio", 0.3)),
            "creep_ratio": float(m.get("creep_rupture_8h_40c_ratio", 0.4)), "seconds": time.time() - t0}


def summarize_body(rows: list, tag: str, fat: float = 0.3, rup: float = 0.4) -> dict:
    """Per case min margin (FI99 rule, pass >= 1.0) with its torso and location; fatigue and creep from C1."""
    rs = [r for r in rows if r["scenario"] == tag]
    by = {}
    for r in rs:
        if r["case"] not in by or r["sf"] < by[r["case"]]["sf"]:
            by[r["case"]] = r
    out = {"cases": {c: {"sf": v["sf"], "torso": v["torso"], "where": v["where"], "peak_xyz": v["peak_xyz"],
                         "factor": v["factor"]} for c, v in by.items()}}
    if rs:
        gov = min(rs, key=lambda r: r["sf"])
        out.update({"sf_min": gov["sf"], "governing": f"{gov['case']}|{gov['torso']:g}", "where": gov["where"]})
    sc = [r for r in rs if r["case"] == "static_carry"]
    if sc:
        g = max(sc, key=lambda r: r["fi99"])
        fi_fat = g["fi99"] * (1.6 / g["factor"])
        out["sf_fatigue"] = fat / max(fi_fat, 1e-9)
        out["sf_creep"] = rup / max(g["fi99"] / g["factor"], 1e-9)
        out["fatigue_set"] = g["set"]
    mt = [r for r in rs if r["case"] == "meat_straps"]
    if mt:      # info: meat carried at the walking peak (rev B defines fatigue on the bag carry only)
        g = max(mt, key=lambda r: r["fi99"])
        out["sf_fatigue_meat_info"] = fat / max(g["fi99"] * (1.6 / (2.0 * 1.5)), 1e-9)
        out["sf_creep_meat_info"] = rup / max(g["fi99"] / (2.0 * 1.5), 1e-9)
    return out


# ============================================================================ segment joint (z 234 split)
def segment_joint(rows: list) -> list:
    """Dowel pull-out across the z 234 print split (production_frame.md: 2 x 5 mm dowels per flange, 35 mm embed,
    MMA 6 MPa hot/wet), flange force |N|/2 + M / 24 mm, from the voxel section resultants."""
    from .frame_production import pullout_sf
    out = []
    for r in rows:
        sec = r.get("section_z234")
        if not sec:
            continue
        for side, s in sec.items():
            M = float(np.hypot(s["Mx"], s["My"]))
            flange = abs(s["N"]) / 2 + M / 24.0
            out.append({"set": r["set"], "side": side, "N": s["N"], "M_nmm": M, "flange_n": flange,
                        "pullout_sf": pullout_sf(flange, 2, 5.0, 35.0)})
    return out


# ============================================================================ torso adjust
def pulley_tensions(F_crown: float) -> dict:
    """Euler-Eytelwein on the 3:1 routing (dead end - A - B(moving) - C - cam). Holding with the pawl released
    (friction helps) and hoisting (shortening under load, friction opposes)."""
    kA, kB, kC = (np.exp(PULLEY_MU * t) for t in PULLEY_WRAPS_RAD)
    hold = kC + kC * kB + kC * kB * kA            # F / T_tail (segments B-C, A-B, deadend-A)
    hoist = 1 / kC + 1 / (kC * kB) + 1 / (kC * kB * kA)
    T_hold = F_crown / hold
    T_hoist = F_crown / hoist
    return {"F_crown_n": F_crown, "tail_hold_n": T_hold, "tail_hoist_n": T_hoist,
            "max_segment_hold_n": T_hold * kC * kB * kA, "ratio_hold": hold, "ratio_hoist": hoist}


def torso_adjust(crown_rows: list, tags=("a", "b", "c", "b_im3", "c_im3")) -> dict:
    from huntkit.materials import load
    web = float(load("poly_webbing_25mm").require("breaking_strength_n"))
    out = {}
    for tg in tags:
        rs = [r for r in crown_rows if r["scenario"] == tg]
        if not rs:
            continue
        rack = []
        for r in rs:
            fz = r["pawl_n"][2]
            req = r["factor"]
            rack.append({"set": f"{r['case']}|{r['torso']:g}", "pawl_z_n": fz, "pawl_yz_n": float(np.hypot(*r["pawl_n"][1:])),
                         "factored_yz": [0.0, req * r["pawl_n"][1], req * r["pawl_n"][2]],
                         "rack_sf": RACK_CAPACITY_N / max(abs(fz) * req, 1e-9)})
        wr = min(rack, key=lambda q: q["rack_sf"])
        wc = max(rack, key=lambda q: np.hypot(*q["factored_yz"][1:]))
        # pulley: in-use loads (unfactored) on the worn carry cases; the pawl is released only to adjust
        sc = [r for r in rs if r["case"] == "static_carry"]
        F1 = max((abs(r["pawl_n"][2]) for r in sc), default=0.0)
        hb = [r for r in rs if r["case"] == "hipbelt_off_abuse"]
        Fh = max((abs(r["pawl_n"][2]) for r in hb), default=0.0) / 1.5    # 1 g, hipbelt off
        p1 = pulley_tensions(F1)
        p16 = pulley_tensions(F1 * 1.6)
        ph = pulley_tensions(Fh)
        lif = max((np.hypot(*r["lifter_n"][1:]) for r in sc), default=0.0)
        sh = max((np.hypot(*r["shoulder_n"][1:]) for r in sc), default=0.0)
        out[tg] = {"rack_worst": wr, "pawl_cheek_force": wc,
                   "static_carry_crown_n": F1, "hipbelt_off_crown_1g_n": Fh,
                   "lifter_static_n": lif, "shoulder_static_n": sh,
                   "pulley_static": p1, "pulley_walk_1p6g": p16, "pulley_hipbelt_off": ph,
                   "tail_hoist_ok": p1["tail_hoist_n"] <= TAIL_PULL_LIMIT_N,
                   "cam_hold_sf_walk": CAM_SLIP_N / max(p16["tail_hold_n"], 1e-9),
                   "webbing_sf_walk": web / max(p16["max_segment_hold_n"], 1e-9),
                   "cam_hold_sf_hipbelt_off": CAM_SLIP_N / max(ph["tail_hold_n"], 1e-9)}
    return out


def pawl_cheek(force_yz) -> dict:
    """The production pawl detail (304 bushing, hole 8 mm, cheek 8 mm) under a factored pawl force."""
    from .frame_production import cheek_check
    r = cheek_check(force_yz, 8.0, 8.0, True, pin_d=4.2)
    r.pop("map", None)
    return {"force_yz": [float(v) for v in force_yz], **r, "sf_fi": 1.0 / max(r["fi99"], 1e-9)}


# ============================================================================ crown summary
def crown_summary(crown_rows: list, tag: str) -> dict:
    rs = [r for r in crown_rows if r["scenario"] == tag]
    out = {}
    for key in ("crown_leg", "crown_top_bar", "crown_spine"):
        vals = [(r["members"][key][0], f"{r['case']}|{r['torso']:g}", r["members"][key][1]) for r in rs if key in r["members"]]
        if vals:
            v = min(vals)
            out[key] = {"sf": v[0], "set": v[1], "member": v[2]}
    vals = [(r["joints"]["crown_corner"][0], r["joints"]["crown_corner"][1], f"{r['case']}|{r['torso']:g}")
            for r in rs if "crown_corner" in r["joints"]]
    if vals:
        out["corner_bond_avg"] = {"sf": min(v[0] for v in vals), "set": min(vals)[2]}
        vp = min(vals, key=lambda v: v[1])
        out["corner_bond_peak"] = {"sf": vp[1], "set": vp[2]}
    for key in ("bushing_bearing", "leg_ring_crush"):
        vals = [(r["bushings"][key], f"{r['case']}|{r['torso']:g}") for r in rs if key in r["bushings"]]
        if vals:
            v = min(vals)
            out[key] = {"sf": v[0], "set": v[1]}
    # fatigue (HA-LS-1: CFRP FI <= 0.5 at 0 -> 1.6 g bag carry): from the static-carry member FPF at 1 g
    fat = []
    for r in rs:
        if r["case"] != "static_carry":
            continue
        for key, (m, mid) in r["members"].items():
            fat.append((0.5 / (1.6 / (m * r["factor"])), f"static_carry|{r['torso']:g}", key))
    if fat:
        v = min(fat)
        out["fatigue"] = {"sf": v[0], "set": v[1], "member": v[2]}
    bk = [(r["buckling"], f"{r['case']}|{r['torso']:g}") for r in rs if r.get("buckling") is not None]
    if bk:
        v = min(bk)
        out["buckling"] = {"sf": v[0], "set": v[1]}
    return out


def bar_local(n_point: float = 210.0, width_mm: float = 25.0, pocket_line_n_mm: float | None = None) -> dict:
    """Local ring crush of the crown top bar (OD 18 roll-wrapped) under a factored tie load bearing on a strap of
    ``width_mm`` (point-load ring, Roark 0.318 F R / L: conservative for a wrapped strap), and under a pocket
    line load (N/mm of bar)."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.pack5200 import _sec
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    sec = _sec(next(m for m in fm["members"] if m["group"] == "crown_top_bar")["section"])
    Rm = sec.dims["od"] / 2 - sec.dims["t"] / 2
    out = {}
    m_h = 0.318 * (n_point / width_mm) * Rm
    out["tie"] = {"F_n": n_point, "width_mm": width_mm, "m_hoop": m_h,
                  "sf": float(sec.laminate.first_ply_failure((0, -n_point / (2 * width_mm), 0), (0, m_h, 0))["sf"])}
    q = pocket_line_n_mm if pocket_line_n_mm is not None else 2 * n_point / 200.0
    m_q = 0.318 * q * Rm
    out["pocket"] = {"q_n_mm": q, "m_hoop": m_q,
                     "sf": float(sec.laminate.first_ply_failure((0, -q / 2, 0), (0, m_q, 0))["sf"])}
    out["section"] = {"od": sec.dims["od"], "t": sec.dims["t"]}
    return out


def anchor_beam_sweep(log=print) -> list:
    """Beam-only crown check of C5 (envelope 175 mm) with the top-anchor at x70 / x100 / pocket, elevations
    -20 / 0 / +20 deg, all torsos. Also the anchor alone (no meat load) to isolate its share."""
    rows = []
    for where in ("x70", "x100", "pocket"):
        for elev in (-20.0, 0.0, 20.0):
            sc = Scenario(f"anc_{where}_{elev:+g}", "", 205.0, 175.0, 185.0, 550.0,
                          anchor={"where": where, "elev": elev}, cases=("meat_straps",))
            _, cr = beam_runs(sc, buckling=False, log=None)
            for r in cr:
                r["where"], r["elev"] = where, elev
            rows += cr
    if log:
        log(f"  anchor sweep: {len(rows)} beam runs")
    return rows


# ============================================================================ spreader
def spreader_at(e_mm: float, h: float = 2.0, step=None, core_t: float | None = None) -> dict:
    """Sandwich v2 (spreader_results.json 'chosen', key sw110c6d) with the C5 overturning face load scaled by
    e / 150 (H = P e sum(lev)/sum(lev^2) is linear in e; frame_smooth.meat_normal_n). The bone stays 20 % of
    68 kg (part of the meat). Same h and positions as the release mesh check (2 mm, named positions)."""
    from . import frame_smooth as fs
    from . import spreader as S
    opt = {o.key: o for o in S.options()}["sw110c6d"]
    if core_t:          # candidate: thicker ROHACELL 110 core, same skins, doublers, tubes and clips
        import dataclasses
        opt = dataclasses.replace(opt, key=f"sw110c{core_t:g}d", lam=S.sandwich_lam("rohacell_110_igf", core_t),
                                  core_t=core_t)
    orig = fs.meat_normal_n
    scale = float(e_mm) / 150.0
    fs.meat_normal_n = lambda g_level=1.6, _o=orig, _s=scale: _o(g_level) * _s
    S._SKIN_CACHE.clear()          # the skin-pressure cache is keyed without the meat load: clear it per offset
    try:
        r = S.evaluate(opt, h=h, step=step)
    finally:
        fs.meat_normal_n = orig
        S._SKIN_CACHE.clear()
    keys = ("sf_fpf", "fpf_where", "sf_fatigue", "sandwich_sf_min", "clear_walk_min", "clear_fact_min",
            "clear_fact_lean_min", "skin_peak_kpa", "skin_meat_only_kpa", "w_fact_max", "meat_force_fact_n",
            "clip_lift_max_n", "passes", "checks")
    return {"e_mm": float(e_mm), "h": h, "core_t": float(core_t or 6.0), "mass_g": r.get("mass_g"),
            **{k: r.get(k) for k in keys}}


# ============================================================================ driver
def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def run(log=print, spreader: bool = True, sweep: bool = True, extra_sets=None) -> dict:
    from .spreader_layout import raster
    from .frame_branch import solid_mass_g
    S = scenarios()
    SW = sweep_scenarios() if sweep else {}
    all_sets, crown_rows = [], []
    for sc in list(S.values()) + list(SW.values()):
        s, c = beam_runs(sc, buckling=sc.tag in ("a", "b", "c"), log=log)
        all_sets += s
        crown_rows += c
    log("raster production body (socket-free branch, 2 mm)")
    dom, solid = raster(None, 2.0)
    body_g = solid_mass_g(solid, 2.0)
    secs = [s.key for s in all_sets if s.key.split(":")[0] in ("a", "b", "c") and
            s.case in ("drop_2p5g", "side_hill_torsion", "meat_straps", "hipbelt_off_abuse", "overload_haul")]
    vr = verify_sets(dom, solid, all_sets, keep_env=("a", "c", "b"), sections=set(secs), log=log)
    body = {tg: summarize_body(vr["rows"], tg, vr["fat_ratio"], vr["creep_ratio"]) for tg in list(S) + list(SW)}
    crown = {tg: crown_summary(crown_rows, tg) for tg in list(S) + list(SW)}
    ta = torso_adjust(crown_rows)
    cheek = {tg: pawl_cheek(v["pawl_cheek_force"]["factored_yz"]) for tg, v in ta.items()}
    anc = anchor_beam_sweep(log=log)
    loc = {"x70_tie": bar_local(210.0, 25.0), "x100_guy": bar_local(210.0, 20.0)}
    sj = segment_joint(vr["rows"])
    spr = {}
    if spreader:
        for e in (150.0, 175.0, 206.0, 223.0):
            log(f"  spreader at e {e:g} mm")
            spr[f"{e:g}"] = spreader_at(e)
    ctx = {"date": "2026-11-05", "body_g": body_g, "scenarios": {k: v.__dict__ for k, v in {**S, **SW}.items()},
           "body": body, "crown": crown, "torso_adjust": ta, "pawl_cheek": cheek, "anchor_rows": anc,
           "bar_local": loc, "segment_joint": sj, "spreader": spr, "body_rows": vr["rows"],
           "crown_rows": crown_rows, "solve_s": vr["seconds"]}
    ctx["_env"] = vr["env"]
    ctx["_centers"] = vr["centers"]
    return ctx


def save(ctx: dict, path: Path | None = None) -> Path:
    path = path or (ANALYSIS / "frame_cg_recheck_results.json")
    pub = {k: v for k, v in ctx.items() if not k.startswith("_")}
    path.write_text(json.dumps(_jsonable(pub), indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "fi_env.npz", centers=ctx["_centers"], **{k: v for k, v in ctx["_env"].items()})
    return path


# ============================================================================ minimum crown change (task 4)
UD = "cfrp_t700_ud_epoxy_ply"


def _frame_params() -> dict:
    import yaml
    return yaml.safe_load(ft.FRAME_YAML.read_text())["frame"]


def add_ud(section: dict, n: int) -> dict:
    """Same OD, ``n`` more 0 deg UD plies in the core (the wall grows inward: sleeves, bores and the spine
    channel in the printed body are unchanged)."""
    s = copy.deepcopy(section)
    lay = s["layup"]
    k = max(i for i, p in enumerate(lay) if p["material"] == UD)
    s["layup"] = lay[: k + 1] + [{"angle": 0, "material": UD} for _ in range(n)] + lay[k + 1:]
    return s


def ud_mass_g(section: dict, n: int, length_mm: float, qty: int = 1) -> float:
    """Mass of n UD plies laid inside the existing wall (mean diameter of the new plies)."""
    from huntkit.materials import load
    m = load(UD)
    tp = float(m.require("ply_thickness_mm"))
    rho = float(m.require("density_kg_m3"))
    from huntkit.fea.sections import from_spec
    t0 = from_spec(copy.deepcopy(section)).dims["t"]
    d_in = section["od"] - 2 * t0
    dm = d_in - n * tp
    return qty * np.pi * dm * n * tp * length_mm * rho * 1e-6


def fix_overrides(spine=0, leg=0, bar=0, overlap=None) -> dict:
    fp = _frame_params()
    over = {}
    if spine:
        over["spine_section"] = add_ud(fp["spine_section"], spine)
    if leg:
        over["leg_section"] = add_ud(fp["leg_section"], leg)
    if bar:
        over["bar_section"] = add_ud(fp["bar_section"], bar)     # beam model: also the (printed) mid bar line
    if overlap:
        over["joint"] = {**fp["joint"], "overlap_mm": float(overlap)}
    return over


def fix_mass_g(spine=0, leg=0, bar=0, overlap=None) -> dict:
    fp = _frame_params()
    out = {"spine": ud_mass_g(fp["spine_section"], spine, 300.0) if spine else 0.0,
           "legs": ud_mass_g(fp["leg_section"], leg, 430.0, 2) if leg else 0.0,
           "top_bar": ud_mass_g(fp["bar_section"], bar, 214.0) if bar else 0.0}
    if overlap:
        # corner wrap 0.75 mm QI CFRP over the 18 mm bar and 16 mm leg, extra length on both tubes, 2 corners
        w = (overlap - fp["joint"]["overlap_mm"])
        out["corner_wraps"] = 2 * 0.75 * np.pi * (18.0 + 16.0 + 1.5) * w * 1550.0 * 1e-6
    out["total"] = float(sum(out.values()))
    return out


def crown_pass(cs: dict) -> tuple[bool, float, str]:
    vals = []
    for k in ("crown_leg", "crown_top_bar", "crown_spine", "corner_bond_avg", "corner_bond_peak",
              "bushing_bearing", "leg_ring_crush", "fatigue"):
        if k in cs:
            vals.append((cs[k]["sf"], f"{k} {cs[k]['set']}"))
    worst = min(vals)
    return worst[0] >= 1.0, worst[0], worst[1]


def fix_study(cands=None, tags=("b", "c", "b_im3", "c_im3"), log=print) -> list:
    S = scenarios()
    cands = cands or [dict(), dict(spine=1), dict(spine=2), dict(spine=2, leg=1), dict(spine=2, leg=2),
                      dict(spine=2, leg=2, bar=1), dict(spine=2, leg=2, bar=1, overlap=40.0),
                      dict(spine=2, leg=3, bar=1, overlap=40.0), dict(spine=3, leg=3, bar=1, overlap=45.0)]
    rows = []
    for cd in cands:
        over = fix_overrides(**cd)
        per = {}
        for tg in tags:
            _, cr = beam_runs(S[tg], buckling=False, log=None, over=over)
            cs = crown_summary(cr, tg)
            ok, w, what = crown_pass(cs)
            per[tg] = {"pass": ok, "worst": w, "what": what, "crown": cs}
        row = {"change": cd, "mass": fix_mass_g(**cd), "per": per,
               "pass": all(v["pass"] for v in per.values())}
        rows.append(row)
        if log:
            log(f"  fix {cd}: +{row['mass']['total']:.1f} g  " +
                "  ".join(f"{tg} {v['worst']:.2f}" for tg, v in per.items()))
    return rows


FIX = {"spine": 1, "leg": 2, "bar": 1, "adhesive_t_mm": 0.8}


def fix_over(fix: dict = FIX) -> dict:
    o = fix_overrides(spine=fix["spine"], leg=fix["leg"], bar=fix["bar"])
    if fix.get("adhesive_t_mm"):
        o["joint"] = {**_frame_params()["joint"], "adhesive_t_mm": fix["adhesive_t_mm"]}
    return o


def fix_mass_total(fix: dict = FIX) -> dict:
    m = fix_mass_g(spine=fix["spine"], leg=fix["leg"], bar=fix["bar"])
    if fix.get("adhesive_t_mm"):
        fp = _frame_params()["joint"]
        # 2 corners x (bar end + leg end) x pi d L, extra bondline thickness, MMA 1.15 g/cm3 (frame.yaml adhesive)
        area = 2 * np.pi * (18.0 + 16.0) * fp["overlap_mm"]
        m["corner_bondline"] = area * (fix["adhesive_t_mm"] - fp["adhesive_t_mm"]) * 1.15e-3
    m["total"] = float(sum(v for k, v in m.items() if k != "total"))
    return m


def fix_recheck(tags=("a", "b", "c", "b_im3", "c_im3"), log=print) -> dict:
    """Crown + printed body with the minimum crown change (the stiffer crown changes the body loads a little)."""
    from .spreader_layout import raster
    S = scenarios()
    over = fix_over()
    sets, crown = [], {}
    for tg in tags:
        s, cr = beam_runs(S[tg], buckling=tg in ("a", "b", "c"), log=None, over=over)
        sets += s
        crown[tg] = crown_summary(cr, tg)
    dom, solid = raster(None, 2.0)
    vr = verify_sets(dom, solid, sets, log=log)
    body = {tg: summarize_body(vr["rows"], tg, vr["fat_ratio"], vr["creep_ratio"]) for tg in tags}
    return {"fix": FIX, "mass_g": fix_mass_total(), "crown": crown, "body": body,
            "pass": {tg: crown_pass(crown[tg])[0] and body[tg]["sf_min"] >= 1.0 for tg in tags}}


def anchor_summary(rows: list) -> list:
    out = []
    for where in ("x70", "x100", "pocket"):
        for elev in (-20.0, 0.0, 20.0):
            rs = [r for r in rows if r["where"] == where and r["elev"] == elev]
            if not rs:
                continue
            def mn(key, sub=None):
                v = [(r["members"][key][0] if sub is None else r["joints"]["crown_corner"][sub]) for r in rs
                     if (key in r["members"] if sub is None else "crown_corner" in r["joints"])]
                return float(min(v)) if v else None
            out.append({"where": where, "elev": elev, "top_bar": mn("crown_top_bar"), "leg": mn("crown_leg"),
                        "spine": mn("crown_spine"), "corner_avg": mn(None, 0), "corner_peak": mn(None, 1),
                        "pawl_z_max_n": float(max(abs(r["pawl_n"][2]) for r in rs))})
    return out



def final_attachment_check(log=print) -> dict:
    """The released top anchor (crown hood + 2 fixed guys, bag_attachment.md) on C5 / C7 at 175 and 190 mm
    (190 = the 15 in fill CG the orchestrator asked to cover on the meat cases), crown as built and with the fix,
    plus the printed body and the spreader at 190 mm."""
    from .spreader_layout import raster
    out = {"loads_1g": {"hood_total_n": HOOD_1G_N, "guy_each_n": GUY_1G_N, "guy_dy_mm": GUY_DY_MM},
           "crown": {}, "body": {}}
    sets = []
    for e in (175.0, 190.0):
        tag = f"hg{e:g}"
        sc = Scenario(tag, f"C5/C7 at {e:g} mm + crown hood + 2 guys", 205.0, e, 185.0, 550.0,
                      anchor={"where": "hood_guys", "elev": 0.0}, cases=("meat_straps", "overload_haul"),
                      split_x=95.0, anchor_cases=("meat_straps", "overload_haul"))
        for lab, over in (("as_built", {}), ("fix", fix_over())):
            s_, cr = beam_runs(sc, buckling=False, log=None, over=over)
            out["crown"][f"{tag}_{lab}"] = crown_summary(cr, tag)
            if lab == "as_built":
                sets += s_
        sc0 = Scenario(f"m{e:g}", f"C5/C7 at {e:g} mm, no top anchor", 205.0, e, 185.0, 550.0,
                       cases=("meat_straps", "overload_haul"))
        s_, cr = beam_runs(sc0, buckling=False, log=None)
        out["crown"][f"m{e:g}_as_built"] = crown_summary(cr, sc0.tag)
        sets += s_
    dom, solid = raster(None, 2.0)
    vr = verify_sets(dom, solid, sets, log=log)
    for tg in sorted({s.key.split(":")[0] for s in sets}):
        out["body"][tg] = summarize_body(vr["rows"], tg, vr["fat_ratio"], vr["creep_ratio"])
    out["bar_local"] = {"hood_line": bar_local(158.0, 25.0, pocket_line_n_mm=158.0 / 190.0)["pocket"],
                        "guy_via_hood_ear_30mm": bar_local(104.0, 30.0)["tie"]}
    out["spreader_190"] = spreader_at(190.0)
    out["spreader_181"] = spreader_at(181.0)
    return out
