"""BL-011 CORRIE F in the cloth sim (huntkit.clothsim): pattern loader, scenarios, runner, extraction, R-28.

    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py scenarios               # write cf_PR{15,19,23}.yaml
    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py run F --torso 15         # one coarse sim (fill, meat)
    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py run F0 --torso 23        # S15 without the top setback
    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py fine --torso 19          # one fine drape (packed)
    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py table                    # stored rows

huntkit is not edited. The scenario keeps ``bag: corrie``; ``install`` swaps, for the duration of a run:
* ``corrie.make`` -> ``corrie_f.make(setback)`` (shell S15 + the BL-011 top setback), as BL-009 / BL-004 swapped S15 in;
* ``bag_concepts.y_frame`` -> the shell's own frame face (the setback is a second Z-fold in B-01);
* ``corrie_bag.load_corrie_patterns`` -> a wrapper that books the floor B-05 in ULTRA 200X (team B's floor), which the
  sim's fabric table models directly. ULTRAGrid and 70D have no sim model: as team B did (fell_clothsim.py), they are
  the nearest modelled fabric scaled by the record ratios through the scenario's ``panels`` keys.
The door is modelled closed (a sewn seam) on CORRIE's piece layout for both door options (ASSUMPTION DOOR-SIM: a
closed coil zip carries <= 0.45 N/mm, team C's sim, so the cut line of a closed door does not move the CG; settled by
the 15 in plumb-line CG test on the chosen door's prototype).

Variants: ``F`` = CORRIE F (setback corrie_f.TOP_SETBACK_MM); ``F0`` = the same with no setback (S15's frame face), to
size the setback for R-28 at 23 in. Attachment = BL-004 REC (no hood, no IM2 hooks, guys toggled round the bar), the
scenario keys attach_diet used. External loads (add-ons on): the top pouch with 1 kg of goods on the closed roll and
the 85 mm spotter in the scope pod on the left gusset, hung from the hard points z 420 / 640. The tripod (under W1/W2)
and the hip-reach pocket contents are not in the sim, as for CORRIE B.2 (the pockets sit forward: leaving them out is
conservative for the CG).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
CONCEPTS = HERE.parent
ROOT = CONCEPTS.parents[2]
for _p in (str(ROOT), str(CONCEPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import corrie_f as F  # noqa: E402

RESULTS = HERE / "corrie_f_sim_results.json"
OUT = ROOT / "outputs" / "clothsim" / "corrie_f"
TORSOS = (15, 19, 23)
LIMIT = {"meat": 190.0, "fill": 205.0}       # HA-LS-1 rev C (load_standard.md 4.2)
BIAS_MM = 4.0                                # corrie_body.md 11.4 / BL-002: +4 mm at 6 mm rounding, scaled by the stage
VARIANTS = {"F": None, "F0": 0.0, "Fr0": 30.0}   # setback mm (None = corrie_f.TOP_SETBACK_MM, the current rev)
#   Fr0 = CORRIE F rev 0 (BL-011: 30 mm setback, guys at the bar ends x +/-100). F = the current rev (rev 1, BL-022:
#   corrie_f.TOP_SETBACK_MM, guys at corrie_f.GUY_X). "S<mm>" (e.g. S40) = rev 1 with that top setback (step search).
GUYS = {"F": "rev", "F0": 100.0, "Fr0": 100.0}       # guy bar-end x (mm); "rev" = corrie_f.GUY_X; S<mm> -> "rev"
GUY_X_REV0 = 100.0                                   # BL-004 / BL-011: the guys' crown end at x +/-100 (corrie_PR{t})


def setback_of(variant: str):
    """Top setback (mm) for a variant name: VARIANTS, or 'S<mm>' (BL-022 step search)."""
    if variant in VARIANTS:
        return VARIANTS[variant]
    if variant.startswith("S") and variant[1:].replace(".", "", 1).isdigit():
        return float(variant[1:])
    raise KeyError(variant)


def guys_of(variant: str, guys=None):
    """Guy setting for a run: ``guys`` 'off' (misuse: not toggled on) or a bar-end x; else the variant's own."""
    if guys is not None:
        return guys
    g = GUYS.get(variant, "rev")
    return F.GUY_X if g == "rev" else g

# fabric models (team B, fell_clothsim.py docstring; record ratios)
UG_SCALE = {"k_warp_scale": 1.30, "k_weft_scale": 1.375, "areal_kg_mm2_scale": 0.733}   # ULTRAGrid on the 330D model
R70_SCALE = {"k_warp_scale": 0.44, "k_weft_scale": 0.387, "areal_kg_mm2_scale": 0.736}  # 70D on the Robic model
CAMO_SCALE = {"areal_kg_mm2_scale": round(290.0 / 180.0, 3)}   # D2 blade U, 630D printable on the 330D model (mass
#                                                               only; stiffness kept: ASSUMPTION CAMO-K, no record)


def bias(rounding_mm) -> float:
    """BL-002 rule: the rounding bias scales with the stage (+4 mm at 6 mm rounding)."""
    return BIAS_MM * float(rounding_mm or 0.0) / 6.0


def externals() -> list:
    ad = F.addons()
    top = ("top_pouch", "top_pouch_straps") if "top_pouch" in ad else ("crown_lid", "crown_straps")   # BL-029 rev 3
    pouch_kg = 1.0 + (ad[top[0]]["mass_g"] + ad[top[1]]["mass_g"]) / 1000.0
    import corrie_loadout as CL
    spot = CL.load_yaml()["items"]["spotter_85"]["mass_g"] / 1000.0
    pod_kg = spot + ad["scope_pod"]["mass_g"] / 1000.0
    return [{"label": "top_pouch_1kg", "kg": round(pouch_kg, 3), "piece": "B-06", "top_mm": 15.0,
             "offset_mm": [0.0, 0.0, 75.0]},
            {"label": "scope85_scope_pod_left_gusset", "kg": round(pod_kg, 3), "piece": "B-03L",
             "z": list(F.SCOPE_POD_Z), "seams": [["B-01", 0.5], ["B-02u", 0.5]], "offset_mm": [-83.0, 0.0, 0.0]}]


def _gsuffix(guys) -> str:
    if guys is None or guys == GUY_X_REV0:
        return ""
    return "_goff" if guys == "off" else f"_gx{int(round(float(guys)))}"


def scenario_path(torso: int, guys=None, smooth=None) -> Path:
    sm = "" if smooth is None else f"_sm{int(round(float(smooth)))}"
    return HERE / f"cf_PR{torso}{_gsuffix(guys)}{sm}.yaml"


def guy_ties(torso: int, guys) -> list:
    """BL-022: the guys' tie list with the crown end moved to x +/-``guys`` (same bar face y and z), or [] when off."""
    if guys == "off":
        return []
    from huntkit.clothsim.pack import load_scenario
    base = load_scenario(str(ROOT / "huntkit" / "clothsim" / "scenarios" / f"corrie_PR{torso}c.yaml"))
    out = []
    for t in base["attachments"]["ties"]["list"]:
        t = dict(t)
        a = list(t["anchor"])
        a[0] = float(np.sign(a[0])) * float(guys)
        t["anchor"] = a
        out.append(t)
    return out


# BL-028: the 6-day load for the guy path, as shell_sweep.RENDER_STATES["sixday"] (ASSUMPTION RS-1: about 45 L / 22 kg,
# loadouts.yaml elk6 order of magnitude), add-ons on. The sim cannot roll the collar down: the unfilled top stays as
# soft cloth over 45 L of contents with the wraps cinched (closed volume follows the contents' gas law).
SIXDAY = {"p0_kpa": 0.5, "contents_L": 45.0, "fill_kg": 22.0, "fill_model": "janssen", "wraps": True}


def write_scenarios(guys=None, smooth=None) -> list:
    out = []
    ext = externals()
    for t in TORSOS:
        att = {"pocket": {"enabled": False}, "hooks": {"stations": [520]}}
        if _gsuffix(guys):
            att["ties"] = {"list": guy_ties(t, guys)}
        body = {"extends": f"../../../../huntkit/clothsim/scenarios/corrie_PR{t}c.yaml", "name": f"corrie_f_PR{t}{_gsuffix(guys)}",
                "attachments": att,
                "panels": {"B-03": dict(UG_SCALE), "B-02h": dict(UG_SCALE), "B-02door": dict(UG_SCALE),
                           "B-02u": dict(CAMO_SCALE), "B-06": dict(R70_SCALE)},
                "cases": {"fill": {"external": ext}, "meat": {"external": ext}, "sixday": dict(SIXDAY, external=ext)}}
        if smooth is not None:   # BL-022: a retry with a wider first contact rounding (then stepped down to 0)
            body["contact"] = {"smooth_mm": float(smooth),
                               "smooth_continuation": [v for v in (6.0, 4.0, 3.0, 2.0, 1.0, 0.0) if v < float(smooth)]}
        head = (f"# BL-011 CORRIE F at {t} in (generated by corrie_f_sim.py; do not edit). corrie_PR{t}c (6 mm rounding +\n"
                "# continuation) with BL-004 REC attachment (no hood, IM3 hooks only, guys round the bar), team B fabrics\n"
                "# (ULTRAGrid / 70D scaled models, ULTRA 200X floor set by the loader), shell S15 + top setback swapped in at\n"
                "# run time, add-ons on: top pouch 1 kg on the roll, 85 mm spotter in the scope pod on the left gusset.\n")
        if _gsuffix(guys):
            head += (f"# BL-022: guys {'OFF (misuse: not toggled on)' if guys == 'off' else f'crown end at x +/-{float(guys):.0f}'}"
                     ".\n")
        p = scenario_path(t, guys, smooth)
        p.write_text(head + yaml.safe_dump(body, sort_keys=False))
        out.append(p)
    return out


# ------------------------------------------------------------------------------------------------- install
_SAVED = {}


def install(setback: float | None = None):
    import bag_concepts as BC
    import corrie as CO
    from huntkit.clothsim import corrie_bag as CB
    c = F.make(setback)
    if not _SAVED:
        _SAVED.update(make=CO.make, yf=BC.y_frame, load=CB.load_corrie_patterns)
    CO.make = lambda rev=None, _c=c: _c
    BC.y_frame = c.frame_y
    orig = _SAVED["load"]

    def load(verbose=True):
        pat = orig(verbose)
        pat["pieces"]["B-05"]["material_id"] = "challenge_ultra_200"
        pat["pieces"]["B-05"]["name"] = "bottom (ULTRA 200X)"
        pat["release"] = "concept: designs/pack_5200/concepts/corrie_f.py (CORRIE F, BL-011)"
        return pat
    CB.load_corrie_patterns = load
    return c


def uninstall():
    if not _SAVED:
        return
    import bag_concepts as BC
    import corrie as CO
    from huntkit.clothsim import corrie_bag as CB
    CO.make, BC.y_frame, CB.load_corrie_patterns = _SAVED["make"], _SAVED["yf"], _SAVED["load"]
    if "att" in _SAVED:
        from huntkit.clothsim.pack import PackModel
        PackModel._attachments = _SAVED.pop("att")


# ------------------------------------------------------------------------------------------------- BL-028 routing
# The scenario's ``ties`` draw each guy as one straight leg from B-22 to the bar. BL-028 re-routes the guy through
# frictionless eyelets on the cloth (huntkit Cable via nodes) so the sim's strap follows its real path round the bag
# corner, or through a guide loop. Swapped in at run time like the shell (huntkit not edited): after PackModel builds
# its attachments, TG_R / TG_L get ``[bag end] + vias + [bar anchor]`` and a rest length from that drafted path (same
# fixed-length rule as the straight tie: snug at the drafted shape, pretension 30 N).
ROUTE = {}      # {"name": str, "R": {"vias": [node ids], "b22": node id or None}, "L": {...}} for the next run


def route_spec(name: str, torso: int) -> dict:
    """Via nodes for a named routing at ``torso`` (fine mesh): see corrie_f.ROUTES."""
    return F.route_spec(name, torso)


def _install_route():
    from huntkit.clothsim.pack import PackModel
    if not ROUTE or "att" in _SAVED:
        return
    orig = PackModel._attachments
    _SAVED["att"] = orig

    def att(self):
        orig(self)
        X = self.mesh.X0
        for s in ("R", "L"):
            cb = self.cables.get(f"TG_{s}")
            r = ROUTE.get(s)
            if cb is None or not r:
                continue
            pre = float(cb.meta["pretension_n"])
            for nm, chain in r.get("internal", {}).items():     # internal ties: bag node to bag node, no frame end
                ci = dataclasses.replace(cb, name=nm, nodes=np.asarray([int(k) for k in chain]),
                                         fixed=np.full((len(chain), 3), np.nan), meta=dict(cb.meta))
                L = ci.length(X)
                ci.L0 = L / (1.0 + pre / ci.EA)
                ci.meta.update(L_init=L, route=ROUTE.get("name"), internal=True)
                self.cables[nm] = ci
            if r.get("off"):                                    # the external guy deleted by this routing
                del self.cables[f"TG_{s}"]
                continue
            for nm, e in r.get("extra", {}).items():           # BL-029: a second frame-anchored cable (e.g. the port guy)
                ce = dataclasses.replace(cb, name=nm, nodes=np.asarray([int(k) for k in e["nodes"]] + [-1]),
                                         fixed=np.vstack([np.full((len(e["nodes"]), 3), np.nan), [e["anchor"]]]),
                                         meta=dict(cb.meta))
                _set_rest(self, ce, float(e.get("pretension_n", pre)), e.get("mode", "elastic"))
                ce.meta.update(route=ROUTE.get("name"), extra=True)
                self.cables[nm] = ce
            head = int(r["b22"]) if r.get("b22") is not None else int(cb.nodes[0])
            nodes = [head] + [int(k) for k in r.get("vias", [])] + [-1]
            fixed = np.full((len(nodes), 3), np.nan)
            fixed[-1] = r["anchor"] if r.get("anchor") is not None else cb.fixed[-1]
            cb.nodes, cb.fixed = np.asarray(nodes), fixed
            _set_rest(self, cb, float(r.get("pretension_n", pre)), r.get("mode", "elastic"))
            cb.meta.update(route=ROUTE.get("name"), vias=[int(k) for k in r.get("vias", [])], b22_node=head)
    PackModel._attachments = att


def _set_rest(pm, cb, pre: float, mode: str):
    """Rest length of a routed cable on the drafted mesh, as pack._attachments sets a tie: ``elastic`` = snug at the
    drafted shape (fixed length); ``cinched`` (BL-029 crown straps, ladder lock) = soft cinch compliance
    (attachments.cinch_strain), re-cinched to ``pre`` on the loaded bag by run_case."""
    from huntkit.clothsim.fabric import webbing
    L = cb.length(pm.mesh.X0)
    if mode == "cinched":
        eps = float(pm.scen["attachments"].get("cinch_strain", 0.03))
        cb.EA = min(webbing(cb.material_id)["EA_n"], pre / eps)
        cb.meta["EA_eff_n"] = cb.EA
    cb.L0 = L / (1.0 + pre / cb.EA)
    cb.meta.update(L_init=L, pretension_n=pre, mode=mode)


REV_DIRS = {"Fr0": "F_r0"}     # BL-025: run folders carry the CORRIE F revision; "F" -> F_r<corrie_f.REVISION>
RENDER_DRAPE_TAG = "_fine"     # packed-only fine drape for the renders (huntkit/viz3d/corrie_f.py reads F_PR{t}_fine)


def run_dir(variant: str, torso: int, tag: str = "") -> Path:
    """Run folder. BL-025: CORRIE F load runs are stored per revision, ``F_r0_PR{t}{tag}`` (rev 0, BL-011: guys at the
    bar ends x +/-100) and ``F_r1_PR{t}{tag}`` (rev 1, BL-022: guys at corrie_f.GUY_X), because BL-022's rev 1 runs had
    overwritten the rev 0 folders of the same name. Other variants (F0, S<mm>) keep their own prefix. The packed render
    drape (tag "_fine") keeps its legacy name F_PR{t}_fine for the viz3d reader (F_r0_PR{t}_fine links to it)."""
    if variant == "F" and tag == RENDER_DRAPE_TAG:
        return OUT / f"F_PR{torso}{tag}"
    pre = f"F_r{F.REVISION}" if variant == "F" else REV_DIRS.get(variant, variant)
    return OUT / f"{pre}_PR{torso}{tag}"


def run(variant: str, torso: int, cases="fill,meat", fine=False, tag="", guys=None, smooth=None, route=None) -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    g = guys_of(variant, guys)
    write_scenarios(g, smooth)
    ROUTE.clear()
    if route:                                   # BL-028: guy routing through eyelets (fine mesh only)
        assert fine, "BL-028 routes carry fine-mesh node ids"
        ROUTE.update(route_spec(route, torso), name=route)
    install(setback_of(variant))
    _install_route()
    try:
        from huntkit.clothsim import cli
        a = argparse.Namespace(scenario=str(scenario_path(torso, g, smooth)), time_cap=None, out=str(run_dir(variant, torso, tag)),
                               fine=fine, cases=cases, verbose=False, no_render=True, no_sweep=True, screens=None, date=None)
        cli.cmd_run(a)
    finally:
        uninstall()
    if fine and not ({"fill", "meat"} & set(cases.split(","))):
        return {"fine": str(run_dir(variant, torso, tag))}
    row = extract(variant, torso, tag)
    row["guys"] = g
    if route:
        row["route"] = {"name": route, **{s: ROUTE[s] for s in ("R", "L") if s in ROUTE}}
    ROUTE.clear()
    store(row)
    return row


# ------------------------------------------------------------------------------------------------- extraction
GROUPS = ("hinge_R", "hinge_L", "doubler_R", "doubler_L", "hook_im520_R", "hook_im520_L", "TG_R", "TG_L", "TI_R", "TI_L", "TP_R", "TP_L",
          "under_strap_US1", "under_strap_US2", "W1", "W2", "W3")


def drafted_face(variant: str, torso: int, fine: bool = False) -> dict:
    """Drafted frame-side face of THIS shell's sim mesh per 50 mm z band (attach_diet._drafted binning). ``fine``
    (BL-022) bins the fine mesh, so a fine run's move is measured from its own drafted mesh."""
    from huntkit.clothsim.pack import PackModel, load_scenario
    install(setback_of(variant))
    try:
        pm = PackModel(load_scenario(str(scenario_path(torso))), fine=fine, verbose=False)
    finally:
        uninstall()
    X = pm.mesh.X0
    d = {}
    for z in np.arange(pm.c["Z0"], X[:, 2].max(), 50.0):
        s_ = np.abs(X[:, 2] - z) < 25
        if s_.sum() > 3:
            d[int(round(z))] = float(X[s_, 1].min())
    return d


def r28(variant: str, torso: int, r: dict, fine: bool = False) -> dict:
    """R-28 head clearance on the simulated wall, with the method fix (attach_system.r28_loaded ``design_face`` =
    this shell's own drafted face, so the wall is the loaded face). No hood (BL-004 REC). Also the old (as-coded)
    reading, for the record."""
    from huntkit.gendesign.attach_system import r28_loaded
    dr = drafted_face(variant, torso, fine)
    face = sorted((float(z), y) for z, y in dr.items())
    out = {}
    for cn in ("fill", "meat"):
        move = [(float(w[0]), float(dr[int(round(w[0]))] - w[1])) for w in r["cases"][cn]["profile"]["depth_by_z"]
                if int(round(w[0])) in dr]
        res = r28_loaded(torso, move, hood=False, design_face=face)
        old = r28_loaded(torso, move, hood=False)
        zt = res["top_z"]
        res["wall_toward_head_above_bar_mm"] = round(max([m[1] for m in move if m[0] - 25 >= zt], default=0.0), 1)
        res["as_coded_deg"] = old["worst_contact_deg"]
        res["loaded_face_above_bar"] = [(float(w[0]), round(float(w[1]), 1)) for w in r["cases"][cn]["profile"]["depth_by_z"]
                                        if w[0] - 25 >= zt]
        out[cn] = res
    return out


def extract(variant: str, torso: int, tag: str = "") -> dict:
    r = json.loads((run_dir(variant, torso, tag) / "results.json").read_text())
    fine = float(r["mesh"]["h_mm"]) < 40.0
    row = {"variant": variant, "torso": torso, "tag": tag, "setback_mm": F.make(setback_of(variant)).setback,
           "seconds": round(r["seconds"]), "mesh_h": r["mesh"]["h_mm"], "cases": {}}
    for cn, c in r["cases"].items():
        v = c["volume"]
        cg = v.get("cg_with_external_mm", v["contents_cg_mm"])
        att = c["attachments"]
        rnd = c.get("contact_rounding_mm")
        row["cases"][cn] = {
            "converged": bool(c["converged"]), "rounding_mm": rnd, "residual_n": c["solve"][-1].get("residual_n"),
            "closed_L": round(v["closed_L"], 2), "closed_cu_in": v["closed_cu_in"],
            "cg_y": round(float(cg[1]), 1), "cg_z": round(float(cg[2]), 1), "cg_x": round(float(cg[0]), 1),
            "contents_cg_y": round(float(v["contents_cg_mm"][1]), 1),
            "cg_y_biased": round(float(cg[1]) + bias(rnd), 1),
            "loads_1g": {k: round(float(att[k]["tension_n"]), 1) for k in GROUPS if k in att},
            "seam": c["seam_critical"]["seam"], "seam_n_mm": c["seam_critical"]["max_n_mm"],
            "seam_sf": c["seam_critical"]["sf"], "aft_depth": c["profile"]["max_depth_aft_mm"],
            "e_max_pct": max(q["e_max_pct"] for q in c["pieces"].values()),
            "profile": c["profile"]["depth_by_z"]}
    if "fill" in r["cases"] and "meat" in r["cases"]:
        row["r28"] = r28(variant, torso, r, fine)
    return row


def load_results() -> dict:
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else {"rows": {}}


def store(row: dict):
    d = load_results()
    d["rows"][f"{row['variant']}_PR{row['torso']}{row['tag']}"] = row
    RESULTS.write_text(json.dumps(d, indent=1, default=float))


def get(variant: str, torso: int) -> dict | None:
    return load_results()["rows"].get(f"{variant}_PR{torso}")


def table() -> list:
    out = []
    for k, r in load_results()["rows"].items():
        for cn in ("fill", "meat"):
            c = r["cases"].get(cn)
            if not c:
                continue
            rr = r.get("r28", {}).get(cn, {})
            out.append({"run": k, "case": cn, "conv": c["converged"], "rounding": c["rounding_mm"], "L": c["closed_L"],
                        "cg_y": c["cg_y"], "cg_y_biased": c["cg_y_biased"], "cg_z": c["cg_z"],
                        "limit": LIMIT[cn], "im3_max_n": max(c["loads_1g"].get("hook_im520_R", 0), c["loads_1g"].get("hook_im520_L", 0)),
                        "seam_n_mm": c["seam_n_mm"], "seam_sf": c["seam_sf"], "r28_deg": rr.get("worst_contact_deg"),
                        "r28_as_coded_deg": rr.get("as_coded_deg"), "r28_pass": rr.get("pass")})
    return out


SWEEP = HERE / "corrie_f_r28_sweep.json"
SWEEP_ALLOW = (3.0, 6.0, 9.0, 12.0, 20.0)
SWEEP_ROWS = ("Fr0_PR23", "F_PR23", "Fr0_PR23_fineFM", "F_PR15_fineFM", "F_PR19_fineFM", "F_PR23_fineFM")


def r28_sweep(rows=SWEEP_ROWS, allows=SWEEP_ALLOW) -> dict:
    """BL-022 (review B3): R-28 against the wall allowance ``attach_system.R28_ALLOW`` (fabric thickness + mesh
    scatter, 3 mm as coded) from the STORED rows (profile = loaded face), so a run directory is not needed. A row
    whose result does not move as the allowance grows is not governed by the bag wall (the bare bar / back pad set
    the first contact). Written to corrie_f_r28_sweep.json."""
    from huntkit.gendesign import attach_system as AS
    st = load_results()["rows"]
    old = AS.R28_ALLOW
    out = {"allow_mm": list(allows), "as_coded_allow_mm": old, "rows": {}}
    try:
        for k in rows:
            r0 = st[k]
            fine = float(r0["mesh_h"]) < 40.0
            r = {"cases": {cn: {"profile": {"depth_by_z": r0["cases"][cn]["profile"]}} for cn in ("fill", "meat")}}
            row = {}
            for al in allows:
                AS.R28_ALLOW = al
                x = r28(r0["variant"], r0["torso"], r, fine)
                row[f"{al:g}"] = {cn: {"deg": x[cn]["worst_contact_deg"], "gap30_mm": x[cn]["worst_gap_30_mm"]}
                                  for cn in ("fill", "meat")}
            out["rows"][k] = row
    finally:
        AS.R28_ALLOW = old
    SWEEP.write_text(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scenarios", "run", "fine", "finerun", "table", "reextract", "r28sweep"])
    ap.add_argument("variant", nargs="?", default="F")
    ap.add_argument("--torso", type=int, default=15)
    ap.add_argument("--cases", default="fill,meat")
    ap.add_argument("--tag", default="")
    ap.add_argument("--guys", default=None, help="'off' or a bar-end x in mm (BL-022)")
    ap.add_argument("--smooth", type=float, default=None, help="first contact rounding, mm (retry of a stalled run)")
    ap.add_argument("--route", default=None, help="BL-028 guy routing (corrie_f.ROUTES), fine runs only; tag _<route>")
    a = ap.parse_args(argv)
    gz = None if a.guys is None else (a.guys if a.guys == "off" else float(a.guys))
    if a.cmd == "scenarios":
        print(write_scenarios())
    elif a.cmd == "run":
        row = run(a.variant, a.torso, a.cases, tag=a.tag, guys=gz, smooth=a.smooth)
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "profile"} for k, v in row["cases"].items()}, indent=1))
        print(json.dumps({k: {kk: row["r28"][k][kk] for kk in ("worst_contact_deg", "as_coded_deg", "pass",
                                                                "wall_toward_head_above_bar_mm")} for k in row.get("r28", {})}))
    elif a.cmd == "fine":
        print(run(a.variant, a.torso, "packed", fine=True, tag="_fine"))
    elif a.cmd == "finerun":   # BL-022: fine mesh (h 25) fill / meat with CG, loads and R-28 on the fine mesh
        rt = f"_{a.route}" if a.route else ""
        row = run(a.variant, a.torso, a.cases, fine=True, tag="_fineFM" + rt + a.tag, guys=gz, smooth=a.smooth, route=a.route)
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "profile"} for k, v in row["cases"].items()}, indent=1))
        print(json.dumps({k: {kk: row["r28"][k][kk] for kk in ("worst_contact_deg", "worst_gap_30_mm", "pass",
                                                                "wall_toward_head_above_bar_mm")} for k in row.get("r28", {})}))
    elif a.cmd == "reextract":
        st = store(extract(a.variant, a.torso))
        print(st)
    elif a.cmd == "r28sweep":
        print(json.dumps(r28_sweep(), indent=1))
    elif a.cmd == "table":
        for t in table():
            print(t)


if __name__ == "__main__":
    main()
