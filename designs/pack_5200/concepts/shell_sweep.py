"""BL-009: bag shape sweep for CG margin and a cleaner silhouette (pack-designer, 2026-11-10).

    python designs/pack_5200/concepts/shell_sweep.py list                    # shells, rule volume, z_c, heights
    python designs/pack_5200/concepts/shell_sweep.py run S03 --torso 15      # one coarse sim (packed, fill, meat)
    python designs/pack_5200/concepts/shell_sweep.py sweep --torso 15        # every shell not yet in the results
    python designs/pack_5200/concepts/shell_sweep.py r28 S03 --torso 15      # R-28 head clearance from a finished run
    python designs/pack_5200/concepts/shell_sweep.py plot                    # CG vs depth PNG (screens)
    python designs/pack_5200/concepts/shell_sweep.py dims S09                # flat piece dimensions of one shell

What it is: a parametric BOX-family shell (planar facets, straight seams; the only curved seam stays CORRIE's
horseshoe door U, which is out of scope here) run through the cloth sim with CORRIE's own loader. huntkit is not
edited: ``huntkit.clothsim.corrie_bag.load_corrie_patterns`` builds its pieces from ``corrie.make()``, so ``install``
swaps ``corrie.make`` for this file's shell at run time (the same mechanism team B used for FELL). Fabrics, pieces,
door, hinge band, B-22 guys, hood, pouch and scope loads are CORRIE rev B.2's (scenarios ``corrie_PR{15,19,23}c``).

Shell parameters (all mm, FCS: y aft of the stay datum, z up from the hip datum; ``bag_concepts`` conventions):
* ``d_bot``  depth at the base (z 35), frame face to aft face;
* ``d_sh``   depth at the shoulder crease (z 631.2, after the 30 mm head setback);
* ``d_col``  depth at the collar seam = the length of the side gusset's top edge ("gusset length"): < d_sh tapers the
             gusset above the shoulder crease so the top of the bag narrows front-to-back;
* ``a_bot``  base half-width (CORRIE 136.2; owner limit 197 = 15.5 in overall);
* ``a_top``  half-width at the collar seam (width taper toward the roll; 196.8 = no taper);
* ``z_c``    height of the collar seam; ``None`` = solved so the rule volume hits ``RULE_TARGET_L``.
The half-width runs linearly a_bot -> 196.8 (z 35 -> 631.2) -> a_top (collar seam). The aft face is two planes (one
crease at z 631.2). Every piece is a flat panel; the sim develops them with ~0 strain.

Volume rule used for the 85 L +/-3 check: the SIMULATED closed volume of the fill case (68 kg, collar closed flat at the
fill line), as team B used for FELL. The concept integrator's rule volume under-counts a box (corrie_body.md, rev B);
the ratio sim / rule on CORRIE rev B is 88.07 / 75.87 = 1.161 (corrie_PR15c), used ONLY to pre-size z_c
(ASSUMPTION RATIO-1, settled by each row's simulated volume, which is what the table reports).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _p in (str(ROOT), str(HERE), str(HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402

SCEN_DIR = HERE / "shell_sweep_scenarios"
RESULTS = SCEN_DIR / "shell_sweep_results.json"
OUT = ROOT / "outputs" / "clothsim" / "shell_sweep"
SCREENS = ROOT / "outputs" / "screens"
PREFIX = "20261111_BL009_"

A_MAX = float(BC.A_MAX)                    # 196.8 mm: 15.5 in overall, owner freeze
Z0, Z_SH = float(BC.Z0), float(BC.Z_SH)
DOME_H = float(BC.DOME_H)                  # 319.8: collar seam to fill line (CORRIE / SPINE collar)
RATIO_SIM_RULE = 88.07 / 75.868            # ASSUMPTION RATIO-1: corrie_PR15c fill closed_L / corrie rule volume
SIM_TARGET_L = 86.0                        # DECISION: aim the sim fill volume 1 L above 85, 2 L inside the +3 L edge
RULE_TARGET_L = SIM_TARGET_L / RATIO_SIM_RULE
VOL_BAND = (82.0, 88.0)                    # owner freeze 85 L +/- 3 (RULES.md item 9)

# Goal (BL-009): 15 in meat CG <= 176 and fill CG <= 190 as simulated (mass-weighted incl. pouch + scope)
GOAL = {"meat": 176.0, "fill": 190.0}
REV_C = {"meat": 190.0, "fill": 205.0}     # HA-LS-1 rev C limits
ROUNDING_BIAS_MM = 4.0                     # corrie_body.md 11.4: a case reported at rounding > 0 reads up to +4 mm

# Frame-interface heights that must land on laminate / below the collar seam (bag_attachment.md, corrie.py)
B22 = {"x": CO.B22_X, "z": CO.B22_Z, "w": 50.0, "h": 60.0}      # guy corner tab, 50 x 60, centre x 149, z 695
LADDER = (545.0, float(BC.LADDER_TOP))                           # B-20 hood ladders, frame side, x +/-60
DOOR_TOP = float(CO.DOOR["z_hinge"])                             # 650
TAB_CLEAR_MM = 10.0                                              # ASSUMPTION: >= 10 mm from a seam line to a tab


@dataclass(frozen=True)
class ShellParams:
    name: str
    d_bot: float
    d_sh: float
    d_col: float
    a_bot: float
    a_top: float = A_MAX
    z_c: float | None = None
    note: str = ""


class Shell(BC.Concept):
    """BC.Concept with the BL-009 envelope. Only ``a`` and ``y_front`` change; the frame face (``y_frame``: stay
    line + 20 mm gap + 30 mm setback Z-fold), the dome law and the integrator are the concept library's."""

    p: ShellParams = None

    def a(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        p = self.p
        zc = self.z_c if self.z_c else 1000.0
        low = np.interp(z, [Z0, Z_SH], [p.a_bot, A_MAX])
        high = A_MAX + (p.a_top - A_MAX) * np.clip((z - Z_SH) / max(zc - Z_SH, 1.0), 0, 1)
        return np.where(z <= Z_SH, low, high)

    def y_front(self, z):
        """Aft face: plane 1 from (z 35, depth d_bot) to (z 631.2, depth d_sh); plane 2 from there to (z_c, d_col)."""
        z = np.atleast_1d(np.asarray(z, float))
        p = self.p
        zc = self.z_c if self.z_c else 1000.0
        yf0, yfs, yfc = (float(BC.y_frame([v])[0]) for v in (Z0, Z_SH, zc))
        y0, y1, y2 = yf0 + p.d_bot, yfs + p.d_sh, yfc + p.d_col
        low = y0 + (y1 - y0) * (z - Z0) / (Z_SH - Z0)
        high = y1 + (y2 - y1) * np.clip((z - Z_SH) / max(zc - Z_SH, 1.0), 0, 1)
        return np.where(z <= Z_SH, low, high)


def make_shell(p: ShellParams) -> Shell:
    c = Shell(key="corrie", name=p.name, kind="box", d_bot=p.d_bot, d_nom=p.d_sh + BC.SETBACK, a_bot=p.a_bot,
              tagline="BL-009 sweep shell", access="as CORRIE")
    c.p = p
    if p.z_c is not None:
        c.z_c = float(p.z_c)
    else:                        # bisection on z_c for the rule target (the envelope above Z_SH depends on z_c)
        lo, hi = Z_SH + 20.0, 1400.0
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            c.z_c = mid
            lo, hi = (mid, hi) if c.volume_L() < RULE_TARGET_L else (lo, mid)
        c.z_c = round(0.5 * (lo + hi), 1)
    return c


# ---------------------------------------------------------------------------------------------------------- the sweep
# S00 is CORRIE rev B exactly (control: must reproduce corrie_PR15c); S01 is FELL's depth on CORRIE's fabrics (team B's
# shell isolated from its fabric swap). Every other z_c is solved for the volume target; each keeps z_c >= 736.3 so the
# B-22 tabs (z 665-725) stay below the collar seam.
SHELLS = {p.name: p for p in [
    ShellParams("S00", 170, 240, 240, 136.18, A_MAX, 736.3, "CORRIE rev B (control)"),
    ShellParams("S01", 165, 232, 232, 136.18, A_MAX, 736.3, "FELL depths (CORRIE x 0.97) on CORRIE fabrics, z_c 736.3"),
    ShellParams("S02", 165, 215, 215, 170, A_MAX, None, "wider base, -25 mm upper depth"),
    ShellParams("S03", 160, 210, 210, 170, A_MAX, None, "wider base, -30 mm"),
    ShellParams("S04", 150, 195, 195, 170, A_MAX, None, "wider base, -45 mm (tall)"),
    ShellParams("S05", 155, 205, 205, A_MAX, A_MAX, None, "full-width box (no base taper)"),
    ShellParams("S06", 160, 210, 210, 136.18, A_MAX, None, "-30 mm on CORRIE's narrow base"),
    ShellParams("S07", 160, 210, 210, A_MAX, 175, None, "full-width base, width taper to 175 at the roll"),
    ShellParams("S08", 160, 210, 210, A_MAX, 155, None, "full-width base, width taper to 155"),
    ShellParams("S09", 160, 210, 180, A_MAX, 175, None, "width + gusset taper (gusset top 180)"),
    ShellParams("S10", 175, 215, 160, A_MAX, 175, None, "deeper base, strong gusset taper (160)"),
    ShellParams("S11", 185, 185, 185, A_MAX, A_MAX, None, "uniform 185 deep slab, full width"),
    ShellParams("S12", 210, 190, 170, A_MAX, 175, None, "wedge: deep base, shallow top"),
    ShellParams("S13", 140, 210, 210, A_MAX, A_MAX, None, "shallow base, deep shoulder, full width"),
    # Round 2 (after S00-S13): wide-base shells came out 88.8-89.7 L simulated (the full-width flat faces bulge more:
    # sim / rule 1.20-1.21, not CORRIE's 1.161), and every extra mm of height cost CG. So: collar seam fixed low at
    # z 745 (B-22 tab 20 mm clear) and depth sized for ~86 L at the round-1 wide-shell ratio 1.205.
    ShellParams("S14", 150, 200, 200, A_MAX, A_MAX, 745.0, "R2: full-width box, z_c 745"),
    ShellParams("S15", 160, 205, 195, A_MAX, 180, 745.0, "R2: full width, taper 180, gusset top 195, z_c 745"),
    ShellParams("S16", 155, 205, 205, 175, A_MAX, 745.0, "R2: base 350 wide, z_c 745"),
    ShellParams("S17", 155, 205, 205, A_MAX, 175, 745.0, "R2: full width, taper 175, z_c 745"),
]}


def install(p: ShellParams, dome_h: float | None = None):
    """CORRIE's loader builds this shell (corrie.make swapped; restore with ``uninstall``). ``dome_h`` < 319.8 =
    the collar rolled down (render load states only): the B-06 tube is cut that much above the collar seam."""
    if not hasattr(CO, "_make_orig"):
        CO._make_orig = CO.make

    def _mk(rev=None, _p=p):
        c = make_shell(_p)
        if dome_h is not None:
            c.dome_h = float(dome_h)
        return c
    CO.make = _mk


def uninstall():
    if hasattr(CO, "_make_orig"):
        CO.make = CO._make_orig


def geometry(p: ShellParams) -> dict:
    c = make_shell(p)
    zc = float(c.z_c)
    a695 = float(c.a([B22["z"]])[0])
    tab_lo, tab_hi = B22["z"] - B22["h"] / 2, B22["z"] + B22["h"] / 2
    return {"z_c": zc, "z_fill": zc + DOME_H, "fill_height_in": (zc + DOME_H - Z0) / 25.4,
            "rule_L": round(c.volume_L(), 2), "rule_cg_y": round(float(c.cg()[0]), 1),
            "rule_cg_z": round(float(c.cg()[1]), 1), "pred_sim_L": round(c.volume_L() * RATIO_SIM_RULE, 1),
            "depth_max": round(float(max(c.depth(np.linspace(Z0, zc, 200)))), 1),
            "width_max_mm": round(2 * float(max(c.a(np.linspace(Z0, zc, 200)))), 1),
            # frame interface (task 4)
            "b22_below_collar_mm": round(zc - tab_hi, 1), "b22_above_door_mm": round(tab_lo - DOOR_TOP, 1),
            "b22_corner_clear_mm": round(a695 - (B22["x"] + B22["w"] / 2), 1),
            "ladder_on_laminate": True,   # B-01 (ULTRA) to z_c; above z_c B-06f is ULTRA (bag_concepts.frame_collar)
            "ladder_top_on": "B-01" if zc >= LADDER[1] else "B-06f (ULTRA collar quarter)"}


def interface_ok(g: dict) -> bool:
    return (g["b22_below_collar_mm"] >= TAB_CLEAR_MM and g["b22_above_door_mm"] >= TAB_CLEAR_MM
            and g["b22_corner_clear_mm"] >= TAB_CLEAR_MM)


# ---------------------------------------------------------------------------------------------------------- running
def scenario(torso: int) -> Path:
    return SCEN_DIR / f"ss_PR{torso}.yaml"


def run_dir(name: str, torso: int, tag: str = "") -> Path:
    return OUT / f"{name}_PR{torso}{tag}"


def run(name: str, torso: int, cases="packed,fill,meat", fine=False, tag=""):
    import os
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    p = SHELLS[name]
    install(p)
    try:
        from huntkit.clothsim import cli
        a = argparse.Namespace(scenario=str(scenario(torso)), time_cap=None, out=str(run_dir(name, torso, tag)),
                               fine=fine, cases=cases, verbose=False, no_render=True, no_sweep=True, screens=None,
                               date=None)
        cli.cmd_run(a)
    finally:
        uninstall()
    row = extract(name, torso, tag)
    if not fine:
        store(row)
    return row


def _x_profile(case: dict) -> dict:
    """Silhouette numbers from the loaded profile (50 mm z bands: z, y_min, y_max, x_min, x_max). The closed-flat
    collar (sim: closed at the fill line, no roll) is the same on every shell, so the "mushroom" is read on the body:
    * ``mushroom_mm``: widest half-width in the shoulder / upper body (z 585-735) minus the mid-body half-width
      (z 235-335 mean): how much the top balloons sideways over the waist of the bag;
    * ``aft_top_mm``: furthest aft point at z 585-785 (top of the bag leaning / bulging away from the back);
    * ``lean_mm``: aft_top minus the furthest aft point at z 235-335 (how much the top overhangs the middle)."""
    P = np.asarray(case["profile"]["depth_by_z"], float)
    hw = 0.5 * (P[:, 4] - P[:, 3])
    up = (P[:, 0] >= 585.0) & (P[:, 0] <= 735.0)
    mid = (P[:, 0] >= 235.0) & (P[:, 0] <= 335.0)
    top = (P[:, 0] >= 585.0) & (P[:, 0] <= 785.0)
    aft_top = float(P[top, 2].max())
    return {"half_width_upper": round(float(hw[up].max()), 1), "half_width_mid": round(float(hw[mid].mean()), 1),
            "mushroom_mm": round(float(hw[up].max() - hw[mid].mean()), 1), "aft_top_mm": round(aft_top, 1),
            "lean_mm": round(aft_top - float(P[mid, 2].max()), 1), "top_z": case["profile"]["top_z_mm"]}


def extract(name: str, torso: int, tag: str = "") -> dict:
    r = json.loads((run_dir(name, torso, tag) / "results.json").read_text())
    p = SHELLS[name]
    row = {"shell": name, "torso": torso, "tag": tag, "params": asdict(p), "geometry": geometry(p),
           "mesh_h": r["mesh"]["h_mm"], "seconds": round(r["seconds"]), "cases": {}}
    for cn, c in r["cases"].items():
        v = c["volume"]
        cg = v.get("cg_with_external_mm", v["contents_cg_mm"])
        pcs = c["pieces"]
        gus = [pcs[k]["wrinkle_area_pct"] for k in ("B-03R", "B-03L") if k in pcs]
        sc = c["seam_critical"]
        last = c["solve"][-1]
        row["cases"][cn] = {
            "converged": bool(c["converged"]), "rounding_mm": c.get("contact_rounding_mm"),
            "residual_n": last.get("residual_n"), "closed_L": round(v["closed_L"], 2),
            "closed_cu_in": v["closed_cu_in"], "cg_y": cg[1], "cg_z": cg[2], "cg_x": cg[0],
            "contents_cg_y": v["contents_cg_mm"][1],
            "warp_max_pct": max(q["warp_max_pct"] for q in pcs.values()),
            "weft_max_pct": max(q["weft_max_pct"] for q in pcs.values()),
            "e_max_pct": max(q["e_max_pct"] for q in pcs.values()),
            "gusset_wrinkle_pct": round(max(gus), 1) if gus else None,
            "seam": sc["seam"], "seam_n_mm": sc["max_n_mm"], "seam_sf": sc["sf"],
            "silhouette": _x_profile(c), "wall_profile": c["profile"]["depth_by_z"]}
    return row


def load_results() -> dict:
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else {"rows": {}}


def reextract():
    """Re-read every stored row from its results.json (after a metric change)."""
    d = load_results()
    for k, r in list(d["rows"].items()):
        new = extract(r["shell"], r["torso"], r["tag"])
        for extra in ("r28",):
            if extra in r:
                new[extra] = r[extra]
        d["rows"][k] = new
    RESULTS.write_text(json.dumps(d, indent=1, default=float))


def store(row: dict):
    d = load_results()
    d["rows"][f"{row['shell']}_PR{row['torso']}{row['tag']}"] = row
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(d, indent=1, default=float))


def usable(row: dict, case: str) -> bool:
    c = row["cases"].get(case)
    return bool(c and c["converged"])


def meets_goal(row: dict) -> dict:
    """Goal check per BL-009 (15 in): meat <= 176, fill <= 190 as simulated, both converged, volume in band."""
    f, m = row["cases"].get("fill"), row["cases"].get("meat")
    ok_v = bool(f and VOL_BAND[0] <= f["closed_L"] <= VOL_BAND[1])
    return {"converged": usable(row, "fill") and usable(row, "meat"),
            "meat": bool(m and m["cg_y"] <= GOAL["meat"]), "fill": bool(f and f["cg_y"] <= GOAL["fill"]),
            "volume": ok_v, "interface": interface_ok(row["geometry"])}


# ---------------------------------------------------------------------------------------------------------- R-28
def r28(name: str, torso: int, tag: str = "") -> dict:
    """R-28 head clearance with the simulated wall: drafted fore face of THIS shell's mesh minus the loaded fore face
    (attach_system.wall_move logic, with the drafted face taken from this shell instead of SPINE's)."""
    from huntkit.clothsim.pack import PackModel, load_scenario
    from huntkit.gendesign.attach_system import r28_loaded
    p = SHELLS[name]
    install(p)
    try:
        pm = PackModel(load_scenario(str(scenario(torso))), verbose=False)
    finally:
        uninstall()
    X = pm.mesh.X0
    drafted = {}
    for z in np.arange(pm.c["Z0"], X[:, 2].max(), 50.0):     # same binning as clothsim.report / attach_system
        s_ = np.abs(X[:, 2] - z) < 25
        if s_.sum() > 3:
            drafted[int(round(z))] = float(X[s_, 1].min())
    r = json.loads((run_dir(name, torso, tag) / "results.json").read_text())
    out = {}
    for cn in ("fill", "meat"):
        move = []
        for row in r["cases"][cn]["profile"]["depth_by_z"]:
            z = int(round(row[0]))
            if z in drafted:
                move.append((float(row[0]), float(drafted[z] - row[1])))
        out[cn] = r28_loaded(torso, move)
    return out


# ---------------------------------------------------------------------------------------------------------- dims
def flat_dims(name: str) -> dict:
    """Flat (developed) piece outlines of a shell, net of seam allowance: bounding box and edge lengths, mm."""
    from huntkit.clothsim import corrie_bag as CB
    install(SHELLS[name])
    try:
        pat = CB.load_corrie_patterns(verbose=False)
    finally:
        uninstall()
    out = {}
    for pid, pc in pat["pieces"].items():
        if pc["kind"] == "dev":
            V2 = np.asarray(pc["V2"])
            ext = V2.max(0) - V2.min(0)
            edges = {nm: round(float(np.linalg.norm(np.diff(P2, axis=0), axis=1).sum()), 1) for nm, P2, _ in pc["edges"]}
            out[pid] = {"bbox_mm": [round(float(ext[0]), 1), round(float(ext[1]), 1)], "edges_mm": edges,
                        "develop_strain_p99_pct": round(float(pc["strain_p99"]), 3)}
        elif pc["kind"] == "floor":
            P = np.vstack([e[1] for e in pc["edges"]])
            ext = P.max(0) - P.min(0)
            out[pid] = {"bbox_mm": [round(float(ext[0]), 1), round(float(ext[1]), 1)]}
        else:
            out[pid] = {"bottom_perimeter_mm": round(float(pc["perimeter"]), 1),
                        "height_to_fill_mm": round(float(pc["height_to_fill"]), 1)}
    return out


# ---------------------------------------------------------------------------------------------------------- renders
# Task 5: three load states of the chosen shell, 19 in (the render torso of every CORRIE / competition render), fine
# mesh h 25. RENDER-ONLY sims (not used for any number in the sweep):
# * the collar is shortened to ``dome_h`` above the collar seam: the rolled-down roll-top (the sim cannot roll);
# * contents are the polytropic gas (corrie scenarios) at the state's volume plus a Janssen gear fill of the state's
#   mass; W1-W3 are cinched with a long take-up (``wrap_takeup``: the owner pulls the wraps / wings in until they
#   bite) instead of the 3 % cinch compliance, so a part-full bag is drawn in toward the frame as it is on the hill.
#   The wings, roll and pouch are placed geometry (huntkit/viz3d/corrie.py), as for every CORRIE render.
# ASSUMPTION RS-1: day ~12 L / 6 kg, 6-day ~45 L / 22 kg (loadouts.yaml day / elk6 order of magnitude), full = the
# packed case (0.5 kPa, 85 L class). Settled by: photographs of the prototype packed to the three loadouts.
RENDER_SHELL = "S15"            # the chosen shell (analysis/shell_sweep.md section 4)
RENDER_STATES = {
    "day": {"label": "Day load (~12 L, roll fully down, wraps cinched)", "dome_h": 70.0,
            "case": {"p0_kpa": 0.5, "contents_L": 12.0, "fill_kg": 6.0, "fill_model": "janssen", "wraps": True},
            "wrap_takeup": 0.45},
    "sixday": {"label": "6-day load (~45 L, roll down to the body, wraps cinched)", "dome_h": 90.0,
               "case": {"p0_kpa": 0.5, "contents_L": 45.0, "fill_kg": 22.0, "fill_model": "janssen", "wraps": True},
               "wrap_takeup": 0.30},
    "full": {"label": "Full (85 L class, packed 0.5 kPa, roll at the fill line)", "dome_h": None,
             "case": {"p0_kpa": 0.5, "wraps": False}, "wrap_takeup": None},
}
RENDER_DIR = ROOT / "outputs" / "clothsim" / "shell_sweep_render"
PACK3D = ROOT / "outputs" / "pack3d_bl009"


def run_render_state(state: str, name: str | None = None, torso: int = 19, fine: bool = True) -> dict:
    import os
    import pickle
    import time
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    from huntkit.clothsim.pack import PackModel, load_scenario, run_case
    from huntkit.clothsim.report import summarize
    name = name or RENDER_SHELL
    st = RENDER_STATES[state]
    install(SHELLS[name], st["dome_h"])
    t0 = time.time()
    try:
        pm = PackModel(load_scenario(str(scenario(torso))), fine=fine, verbose=False)
    finally:
        uninstall()
    if st["wrap_takeup"]:
        for cb in pm.cables.values():
            if cb.kind == "wrap":
                pre = cb.meta["pretension_n"]
                cb.EA = pre / st["wrap_takeup"]
                cb.L0 = cb.meta["L_init"] / (1.0 + pre / cb.EA)
    case = dict(st["case"])
    x, sim, infos = run_case(pm, case)
    r = summarize(pm, state, case, x, sim, infos)
    out = RENDER_DIR / f"{name}_PR{torso}{'_fine' if fine else ''}"
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / f"x_{state}.npy", x)
    m = pm.mesh
    uv = np.zeros((m.n, 2))
    for p in m.pieces:
        uv[p.gid] = p.xy
    sk = {"X": x, "X0": m.X0.copy(), "tris": m.tris.copy(), "piece": pm.piece_of_tri.copy(), "uv": uv}
    (out / f"skin_{state}.pkl").write_bytes(pickle.dumps(sk))
    info = {"state": state, "shell": name, "torso": torso, "h_mm": pm.h, "converged": bool(r["converged"]),
            "residual_n": infos[-1].residual_n, "rounding_mm": r.get("contact_rounding_mm"),
            "closed_L": r["volume"]["closed_L"], "top_z": r["profile"]["top_z_mm"], "seconds": round(time.time() - t0),
            "stages": [i.reason for i in infos]}
    (out / f"info_{state}.json").write_text(json.dumps(info, indent=1, default=float))
    print(json.dumps(info, indent=1, default=float))
    return info


SHOT_VIEW = {"view": {"az": -38, "el": 10, "zoom": 1.0, "box": [-330, -260, -260, 330, 520, 1400]},
             "state": {"mannequin": True, "lid": True}}


def render_model(state: str, name: str | None = None, torso: int = 19) -> Path:
    """GLB of CORRIE B.2's render scene (frame, harness, belt B, display form, wings, door, roll, pouch) on THIS
    shell's drape for one load state. huntkit.viz3d is imported, not edited: corrie.make is swapped (install) and the
    module-level ``sim_skin`` is pointed at this state's drape for the duration of the build."""
    import pickle
    from huntkit.viz3d import corrie as VC
    from huntkit.viz3d import corrie_b1 as VB1
    from huntkit.viz3d import corrie_b2 as VB2
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    name = name or RENDER_SHELL
    st = RENDER_STATES[state]
    sk = pickle.loads((RENDER_DIR / f"{name}_PR{torso}_fine" / f"skin_{state}.pkl").read_bytes())
    saved = {m: m.sim_skin for m in (VC, VB1, VB2)}
    for m in saved:
        m.sim_skin = lambda *a, _sk=sk, **k: _sk
    install(SHELLS[name], st["dome_h"])
    try:
        p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
        pack = VB2.corrie_b2_pack(p)
    finally:
        uninstall()
        for m, f in saved.items():
            m.sim_skin = f
    PACK3D.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, PACK3D / f"{name}_{state}.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m.get("torsos", {}).items()}
    build_html(glb, manifest(pack), m, info, PACK3D / f"{name}_{state}_viewer.html", title=f"BL-009 {name} {state}")
    shots = {f"bl009_{state}": dict(SHOT_VIEW, caption=f"BL-009 shell {name}: {st['label']}",
                                    sub="Same camera for all three load states; 19 in torso, display form, CORRIE B.2 fittings")}
    (PACK3D / f"shots_{state}.json").write_text(json.dumps(shots, indent=1))
    return glb


# ---------------------------------------------------------------------------------------------------------- table
CHOSEN = "S15"      # DECISION (analysis/shell_sweep.md section 4)


def table_md(torsos=(15,)) -> str:
    """The sweep table for shell_sweep.md, straight from the stored rows."""
    d = load_results()["rows"]
    h = ("| Shell | Torso | d_bot / d_sh / d_col | base / top width | z_c (fill height) | Case | Converged (rounding) | "
         "Closed L (cu in) | CG y / z mm | warp / weft % | gusset wrinkle % | worst seam N/mm (SF) | "
         "mushroom / lean mm |\n|" + "---|" * 13)
    out = [h]
    for k, r in d.items():
        if r["torso"] not in torsos or r["tag"]:
            continue
        p, g = r["params"], r["geometry"]
        for cn in ("fill", "meat"):
            c = r["cases"][cn]
            conv = f"yes ({c['rounding_mm']:g} mm)" if c["converged"] else f"NO (res {c['residual_n']:.2f} N)"
            sil = c["silhouette"]
            out.append(f"| {r['shell']} | {r['torso']} | {p['d_bot']:.0f} / {p['d_sh']:.0f} / {p['d_col']:.0f} | "
                       f"{2 * p['a_bot']:.0f} / {2 * p['a_top']:.0f} | {g['z_c']:.1f} ({g['fill_height_in']:.1f} in) | "
                       f"{cn} | {conv} | {c['closed_L']:.1f} ({c['closed_cu_in']:.0f}) | {c['cg_y']:.1f} / "
                       f"{c['cg_z']:.0f} | {c['warp_max_pct']:.1f} / {c['weft_max_pct']:.1f} | "
                       f"{c['gusset_wrinkle_pct']:.0f} | {c['seam_n_mm']:.2f} {c['seam'].replace(' | ', '/')} ({c['seam_sf']:.0f}) | "
                       f"{sil['mushroom_mm']:.0f} / {sil['lean_mm']:.0f} |")
    return "\n".join(out)


def mark_chosen():
    d = load_results()
    g = meets_goal(d["rows"][f"{CHOSEN}_PR15"])
    d["chosen"] = CHOSEN
    d["chosen_meets_goal"] = bool(g["meat"] and g["fill"])
    RESULTS.write_text(json.dumps(d, indent=1, default=float))
    return g


# ---------------------------------------------------------------------------------------------------------- plot
def plot(path: Path | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = load_results()["rows"]
    rows = [r for k, r in d.items() if r["torso"] == 15 and not r["tag"]]
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.8), dpi=110)
    zcs = [r["geometry"]["z_c"] for r in rows]
    norm = matplotlib.colors.Normalize(min(zcs), max(zcs))
    cmap = matplotlib.colormaps["viridis"]
    for ax, case in zip(axs, ("meat", "fill")):
        for r in rows:
            c = r["cases"].get(case)
            if not c:
                continue
            x = r["geometry"]["depth_max"]
            col = cmap(norm(r["geometry"]["z_c"]))
            inband = VOL_BAND[0] <= r["cases"]["fill"]["closed_L"] <= VOL_BAND[1]
            if inband:
                ax.scatter([x], [c["cg_y"]], s=70, marker="o", facecolor=col if c["converged"] else "none",
                           edgecolor="k", zorder=3)
            else:
                ax.scatter([x], [c["cg_y"]], s=45, marker="x", color=col, zorder=3)
            ax.annotate(f"{r['shell']} ({r['cases']['fill']['closed_L']:.0f} L)", (x, c["cg_y"]),
                        textcoords="offset points", xytext=(5, 3), fontsize=7)
        ax.axhline(GOAL[case], color="#c0392b", lw=1.2, ls="--", label=f"BL-009 goal {GOAL[case]:.0f} mm")
        ax.axhline(REV_C[case], color="#555", lw=1.0, ls=":", label=f"rev C limit {REV_C[case]:.0f} mm")
        ax.set_xlabel("max shell depth as drafted (mm)")
        ax.set_ylabel(f"{case} CG y incl. pouch + scope (mm aft)")
        ax.set_title(f"15 in torso, {case} case (68 kg), coarse h 40 mm")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")
    sm = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=axs, shrink=0.85, label="collar seam height z_c (mm): taller = higher CG")
    fig.suptitle("BL-009 shell sweep: loaded CG vs depth. Filled circle = converged and 82-88 L simulated; "
                 "x = volume out of band", fontsize=10)
    path = path or SCREENS / f"{PREFIX}1.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------------------------- CLI
def _cmd_list():
    for n, p in SHELLS.items():
        g = geometry(p)
        print(f"{n}: z_c {g['z_c']:.1f} fill {g['fill_height_in']:.1f} in, rule {g['rule_L']:.1f} L "
              f"(pred sim {g['pred_sim_L']:.1f}), rule CG y {g['rule_cg_y']}, z {g['rule_cg_z']}, depth max "
              f"{g['depth_max']}, B-22 below collar {g['b22_below_collar_mm']}, corner {g['b22_corner_clear_mm']}  "
              f"{p.note}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "run", "sweep", "r28", "plot", "dims", "render-sim", "render-model",
                                    "reextract", "table", "choose"])
    ap.add_argument("shell", nargs="?")
    ap.add_argument("--torso", type=int, default=15)
    ap.add_argument("--cases", default="packed,fill,meat")
    ap.add_argument("--fine", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--state", default="full")
    ap.add_argument("--coarse", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        _cmd_list()
    elif a.cmd == "run":
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("wall_profile",)}
                          for k, v in run(a.shell, a.torso, a.cases, a.fine, a.tag)["cases"].items()}, indent=1))
    elif a.cmd == "sweep":
        done = load_results()["rows"]
        for n in SHELLS:
            if f"{n}_PR{a.torso}" not in done:
                print("=== ", n, flush=True)
                run(n, a.torso, a.cases)
    elif a.cmd == "r28":
        res = r28(a.shell, a.torso, a.tag)
        d = load_results()
        k = f"{a.shell}_PR{a.torso}{a.tag}"
        if k in d["rows"]:
            d["rows"][k]["r28"] = res
            RESULTS.write_text(json.dumps(d, indent=1, default=float))
        print(json.dumps(res, indent=1, default=float))
    elif a.cmd == "plot":
        print(plot())
    elif a.cmd == "dims":
        print(json.dumps(flat_dims(a.shell), indent=1))
    elif a.cmd == "render-sim":
        run_render_state(a.state, a.shell, a.torso if a.torso != 15 else 19, fine=not a.coarse)
    elif a.cmd == "render-model":
        print(render_model(a.state, a.shell))
    elif a.cmd == "reextract":
        reextract()
    elif a.cmd == "table":
        print(table_md(tuple(int(t) for t in (a.shell or "15").split(","))))
    elif a.cmd == "choose":
        print(mark_chosen())


if __name__ == "__main__":
    main()
