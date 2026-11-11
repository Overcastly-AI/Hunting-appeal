"""BL-004: bag-to-frame attachment diet (pack-designer, 2026-11-11).

    python designs/pack_5200/concepts/attach_diet.py inventory                 # task 1: parts, loads per rev C case, margins
    python designs/pack_5200/concepts/attach_diet.py scenarios                 # write the scenario YAMLs
    python designs/pack_5200/concepts/attach_diet.py run REC --shell S15 --torso 15   # one coarse sim (packed, fill, meat)
    python designs/pack_5200/concepts/attach_diet.py queue                     # every planned run not yet stored, one at a time
    python designs/pack_5200/concepts/attach_diet.py table                     # CG / anchor-load / R-28 table from the stored runs
    python designs/pack_5200/concepts/attach_diet.py mass                      # attachment mass per variant (ledger based)
    python designs/pack_5200/concepts/attach_diet.py times                     # bag-off / bag-on / float seconds per variant
    python designs/pack_5200/concepts/attach_diet.py loadpaths                 # changed load paths of the recommendation (BL-010)
    python designs/pack_5200/concepts/attach_diet.py plot                      # outputs/screens/20261111_BL004_{1,2}.png

What it does
------------
* Every attachment mass is read from ``huntkit.mass.ledger`` (system ``attachment``, config ``corrie_b2_h1``, belt M);
  a variant is the ledger rows minus the deleted parts (a share of a ledger row when the row books several identical
  parts) plus new parts from material records or a named ASSUMPTION. No total is typed.
* Each variant is a small scenario override on CORRIE's converged scenarios ``corrie_PR{15,19,23}c`` (6 mm contact
  rounding + continuation, pouch, spotter). The S15 shell (BL-009, adopted 2026-11-11) is swapped in at run time by
  ``shell_sweep.install`` exactly as BL-009 did, so the same scenario file serves both shells. huntkit/clothsim and
  attach_system.py are not edited.
* The sim knows only geometry: a sewn webbing eye on a pin and a hook on an eye are the same elastic 38 mm leg, so
  trial (d) shares the sim of the variant it modifies (stated in the table as "sim of").

Variants (ticket trials)
------------------------
* ``V0``      today: CORRIE B.2 joint (hinge eyes on pull-pins, IM2 + IM3 rated hooks, crown hood on its ladders, guys).
* ``A_hinge`` (a) hinge eyes deleted: the bag floor is held by the under-strap channels only.
* ``A_im3``   (a) IM3 bag hooks deleted: bottom + IM2 + top only.
* ``C_im2``   (c) IM2 bag hooks deleted (T2, B-23, 2 hooks); IM3 hooks and hinge pins kept.
* ``B_guys``  (b) hood + ladders + tongues deleted; each guy's bar end is a 25 mm webbing loop round the crown top bar
              closed by a POM toggle (the hood-tongue toggle part), so the guy keeps its set length on the bag.
* ``B_loops`` (b) the ticket's example: two webbing loops over the bar at x +/-60 from B-01 (fixed length) + the guys.
* ``D_loops`` (d) the IM3 rated hooks become sewn eyes on the IM3 pins (on ``REC``): sim of REC.
* ``REC``     recommended: C_im2 + B_guys + B-17 trimmed 110 -> 70 mm tall (its 80 mm loaded seam unchanged).
* ``M_notop`` misuse of REC: the guys are not toggled on (no top anchor at all). Sizes the IM3 hook (as T0 did).
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _p in (str(ROOT), str(HERE), str(HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import shell_sweep as SS  # noqa: E402

SCEN_DIR = HERE / "attach_diet_scenarios"
RESULTS = SCEN_DIR / "attach_diet_results.json"
OUT = ROOT / "outputs" / "clothsim" / "attach_diet"
SCREENS = ROOT / "outputs" / "screens"
PREFIX = "20261111_BL004_"
CORRIE_SCEN = ROOT / "huntkit" / "clothsim" / "scenarios"
SHELLS = ("CORRIE", "S15")
TORSOS = (15, 19, 23)
LIMIT = {"meat": 190.0, "fill": 205.0}           # HA-LS-1 rev C bag CG (load_standard.md 4.2)
TODAY_MEAT_15 = 184.4                            # ticket: corrie_PR15c meat CG (stored run, read back in today_ref())
TARGET_G, STRETCH_G = 220.0, 200.0               # ticket goal / stretch for the ledger attachment system
FACTOR = 3.0                                     # HA-LS-1 C5 / C2: 2.0 g x 1.5 on the 1 g simulated force (attach_system)
BAG_OFF_LIMIT_S = 120.0                          # R-08

# ---------------------------------------------------------------------------------------------- variants (sim side)
TIE_ANCHOR_X = 100.0     # the guys' crown end in every CORRIE scenario: [+/-100, bar face y, bar z] (unchanged)
LOOP_X = 60.0            # B_loops: loop centre x on bare bar (clear of the corner-wrap step at x 77)


def _base(torso: int) -> dict:
    from huntkit.clothsim.pack import load_scenario
    return load_scenario(str(CORRIE_SCEN / f"corrie_PR{torso}c.yaml"))


def overrides(variant: str, torso: int) -> dict:
    """Scenario override (merged onto corrie_PR{torso}c) for one variant."""
    b = _base(torso)["attachments"]
    no_pocket = {"pocket": {"enabled": False}}
    if variant in ("V0",):
        return {}
    if variant == "A_hinge":
        # the eye on the pin is the only hinge term (pack.build_sim Pins); 0.01 N/mm = no pin (kept > 0 for the solver)
        return {"attachments": {"hinge": {"pin_stiffness_n_mm": 0.01}}}
    if variant == "A_im3":
        return {"attachments": {"hooks": {"stations": [330]}}}
    if variant == "C_im2":
        return {"attachments": {"hooks": {"stations": [520]}}}
    if variant == "B_guys":
        return {"attachments": dict(no_pocket)}
    if variant == "B_loops":
        bar_z, ay = float(b["pocket"]["bar_z"]), float(b["pocket"]["anchor_y"])
        loops = [{"id": f"CT_{s}", "pieces": ["B-01", "B-06"], "at": [sx * LOOP_X, bar_z],
                  "anchor": [sx * LOOP_X, ay, bar_z], "mode": "elastic", "pretension_n": 30.0}
                 for s, sx in (("R", 1.0), ("L", -1.0))]
        return {"attachments": {**no_pocket, "ties": {"list": copy.deepcopy(b["ties"]["list"]) + loops}}}
    if variant in ("REC", "D_loops"):
        return {"attachments": {**no_pocket, "hooks": {"stations": [520]}}}
    if variant == "M_notop":
        return {"attachments": {**no_pocket, "hooks": {"stations": [520]}, "ties": {"list": []}}}
    raise KeyError(variant)


VARIANTS = {
    "V0": {"trial": "today", "label": "today: hood + ladders + guys, IM2 + IM3 hooks, hinge", "sim_of": None},
    "A_hinge": {"trial": "a", "label": "(a) no hinge eyes: floor held by the under-strap channels", "sim_of": None},
    "A_im3": {"trial": "a", "label": "(a) no IM3 bag hooks (hinge, IM2, top)", "sim_of": None},
    "C_im2": {"trial": "c", "label": "(c) no IM2 bag hooks (hinge, IM3, hood + guys)", "sim_of": None},
    "B_guys": {"trial": "b", "label": "(b) no hood or ladders: guys toggled round the bar", "sim_of": None},
    "B_loops": {"trial": "b", "label": "(b) two bar loops at x +/-60 + guys, no hood", "sim_of": None},
    "D_loops": {"trial": "d", "label": "(d) IM3 hooks -> sewn eyes on the IM3 pins (on REC)", "sim_of": "REC"},
    "REC": {"trial": "rec", "label": "REC: (c) + (b) guys-only top + B-17 trim", "sim_of": None},
    "M_notop": {"trial": "misuse", "label": "misuse of REC: guys not toggled on (no top anchor)", "sim_of": None},
}
# planned runs: every variant at 15 in on both shells; REC at every torso; the bar-anchor variants at 23 in
# (the only torso where the hood carries load). One sim at a time (RULES 10).
PLAN = ([(v, s, 15) for v in VARIANTS if VARIANTS[v]["sim_of"] is None for s in SHELLS]
        + [(v, s, t) for v in ("V0", "REC") for s in SHELLS for t in (19, 23)]
        + [(v, s, 23) for v in ("B_guys", "B_loops") for s in SHELLS])


def scenario_path(variant: str, torso: int) -> Path:
    return SCEN_DIR / f"ad_{variant}_PR{torso}.yaml"


def write_scenarios() -> list:
    SCEN_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for v, meta in VARIANTS.items():
        if meta["sim_of"]:
            continue
        for t in TORSOS:
            body = {"extends": f"../../../../huntkit/clothsim/scenarios/corrie_PR{t}c.yaml",
                    "name": f"attach_diet_{v}_PR{t}"}
            body.update(overrides(v, t))
            head = (f"# BL-004 attachment diet, variant {v} at {t} in: {meta['label']}.\n"
                    f"# corrie_PR{t}c unchanged except the keys below. Shell S15 is swapped in at run time by\n"
                    f"# designs/pack_5200/concepts/attach_diet.py (shell_sweep.install), so this file serves CORRIE and S15.\n")
            p = scenario_path(v, t)
            p.write_text(head + yaml.safe_dump(body, sort_keys=False))
            out.append(p)
    return out


def run_dir(variant: str, shell: str, torso: int) -> Path:
    return OUT / f"{variant}_{shell}_PR{torso}"


def run(variant: str, shell: str, torso: int, cases="packed,fill,meat") -> dict:
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    write_scenarios()
    if shell == "S15":
        SS.install(SS.SHELLS["S15"])
    else:
        SS.uninstall()
    try:
        from huntkit.clothsim import cli
        a = argparse.Namespace(scenario=str(scenario_path(variant, torso)), time_cap=None,
                               out=str(run_dir(variant, shell, torso)), fine=False, cases=cases, verbose=False,
                               no_render=True, no_sweep=True, screens=None, date=None)
        cli.cmd_run(a)
    finally:
        SS.uninstall()
    row = extract(variant, shell, torso)
    store(row)
    return row


# ---------------------------------------------------------------------------------------------- extraction
GROUPS = ("hinge_R", "hinge_L", "doubler_R", "doubler_L", "hook_im330_R", "hook_im330_L", "hook_im520_R",
          "hook_im520_L", "TG_R", "TG_L", "CT_R", "CT_L", "pocket", "under_strap_US1", "under_strap_US2", "W1", "W2", "W3")


def _drafted(shell: str, scen: Path) -> dict:
    from huntkit.clothsim.pack import PackModel, load_scenario
    if shell == "S15":
        SS.install(SS.SHELLS["S15"])
    try:
        pm = PackModel(load_scenario(str(scen)), verbose=False)
    finally:
        SS.uninstall()
    X = pm.mesh.X0
    d = {}
    for z in np.arange(pm.c["Z0"], X[:, 2].max(), 50.0):      # same binning as shell_sweep.r28 / clothsim.report
        s_ = np.abs(X[:, 2] - z) < 25
        if s_.sum() > 3:
            d[int(round(z))] = float(X[s_, 1].min())
    return d


def r28(variant: str, shell: str, torso: int, r: dict) -> dict:
    """R-28 with the simulated wall (shell_sweep.r28 method; attach_system.r28_loaded head model). The hood term
    (+1 mm in front of the bar, +4 mm over it) is applied only when the variant keeps the hood."""
    from huntkit.gendesign.attach_system import r28_loaded
    hood = bool(overrides(variant, torso).get("attachments", {}).get("pocket", {}).get("enabled", True))
    dr = _drafted(shell, scenario_path(variant, torso))
    out = {}
    for cn in ("fill", "meat"):
        move = [(float(row[0]), float(dr[int(round(row[0]))] - row[1]))
                for row in r["cases"][cn]["profile"]["depth_by_z"] if int(round(row[0])) in dr]
        res = r28_loaded(torso, move, hood=hood)
        zt = res["top_z"]
        res["wall_toward_head_above_bar_mm"] = round(max([m[1] for m in move if m[0] - 25 >= zt], default=0.0), 1)
        res["hood"] = hood
        out[cn] = res
    return out


def extract(variant: str, shell: str, torso: int) -> dict:
    r = json.loads((run_dir(variant, shell, torso) / "results.json").read_text())
    row = {"variant": variant, "shell": shell, "torso": torso, "seconds": round(r["seconds"]),
           "mesh_h": r["mesh"]["h_mm"], "cases": {}}
    for cn in ("fill", "meat"):
        c = r["cases"][cn]
        v = c["volume"]
        cg = v.get("cg_with_external_mm", v["contents_cg_mm"])
        att = c["attachments"]
        loads = {k: round(float(att[k]["tension_n"]), 1) for k in GROUPS if k in att}
        row["cases"][cn] = {
            "converged": bool(c["converged"]), "rounding_mm": c.get("contact_rounding_mm"),
            "residual_n": c["solve"][-1].get("residual_n"), "closed_L": round(v["closed_L"], 2),
            "cg_y": round(float(cg[1]), 1), "cg_z": round(float(cg[2]), 1), "loads_1g": loads,
            "crown_contact_n": round(float(c["contact"].get("contact_crown", {}).get("force_total_n") or 0.0), 1),
            "seam": c["seam_critical"]["seam"], "seam_n_mm": c["seam_critical"]["max_n_mm"],
            "seam_sf": c["seam_critical"]["sf"], "aft_depth": c["profile"]["max_depth_aft_mm"],
            "profile": c["profile"]["depth_by_z"]}
    row["r28"] = r28(variant, shell, torso, r)
    return row


def load_results() -> dict:
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else {"rows": {}}


def store(row: dict):
    d = load_results()
    d["rows"][f"{row['variant']}_{row['shell']}_PR{row['torso']}"] = row
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(d, indent=1, default=float))


def get(variant: str, shell: str, torso: int) -> dict | None:
    v = VARIANTS[variant]["sim_of"] or variant
    return load_results()["rows"].get(f"{v}_{shell}_PR{torso}")


def today_ref() -> dict:
    """The stored converged runs the ticket and BL-009 quote as 'today' (CORRIE corrie_PR15c; S15 shell_sweep)."""
    out = {}
    for t in TORSOS:
        f = ROOT / "outputs" / "clothsim" / f"corrie_PR{t}c" / "results.json"
        if f.exists():
            c = json.loads(f.read_text())["cases"]
            out[f"CORRIE_PR{t}"] = {cn: c[cn]["volume"].get("cg_with_external_mm", c[cn]["volume"]["contents_cg_mm"])[1]
                                    for cn in ("fill", "meat")}
    ss = SS.load_results()["rows"]
    for t in TORSOS:
        k = f"S15_PR{t}"
        if k in ss:
            out[f"S15_PR{t}"] = {cn: ss[k]["cases"][cn]["cg_y"] for cn in ("fill", "meat")}
    return out


# ---------------------------------------------------------------------------------------------- mass (ledger)
CONFIG, SIZE = "corrie_b2_h1", "M"


def ledger_rows() -> list:
    from huntkit.mass import ledger as L
    return [r for r in L.parts(CONFIG, SIZE) if r["system"] == "attachment"]


def _row(rows, needle: str) -> dict:
    hit = [r for r in rows if needle in r["name"]]
    if len(hit) != 1:
        raise KeyError(f"{needle!r}: {len(hit)} ledger rows")
    return hit[0]


def _mat(mid: str, key: str) -> float:
    from huntkit.materials import load
    return float(load(mid).require(key))


# per-part masses derived from ledger rows (identical parts booked together) or records
def unit_masses(rows=None) -> dict:
    rows = rows or ledger_rows()
    g = lambda n: float(_row(rows, n)["g"])  # noqa: E731
    hyp = _mat("hypalon_coated_nylon", "areal_density_gsm") * 1e-6        # g / mm2
    b17, b18 = 90.0 * 110.0, 90.0 * 45.0                                  # bag_attachment.md section 5 cut sizes
    spreaders = g("bag-side load spreaders")
    return {
        # 4 bag hooks: the 1500 N part (36.0 / 4) + the rated upgrade (20.0 / 4) = 14 g each (attach_system HOOK_RATED_G)
        "bag_hook": (g("bag hooks, 38 mm Al") + g("bag hooks 1500 N -> 2200 N")) / 4.0,
        "tpu_sleeve": g("TPU hook sleeves") / 4.0,
        "tongue_38": g("bag-side straps") / 4.0,                 # T2 x2 + T3 x2, 38 mm x 160
        "b23_pair": g("IM2 tongue backings B-23"),
        "keeper": g("attachment: elastic keepers") / 6.0,         # bag_attach._mass_budget: 6 x 0.6 g
        "fairlead": g("printed fairleads (8)") / 8.0,
        "pin": g("7075 pins (8)") / 8.0,
        "sleeve": g("UHMWPE sleeves (8)") / 8.0,
        "swell_patch": g("B-01 swell patches") / 8.0,
        "swell_b13x": g("B-13x boxed fairlead swell") / 8.0,
        "b17_pair": spreaders * b17 / (b17 + b18),               # the row is B-17 + B-18 by cut area x gsm
        "b18_pair": spreaders * b18 / (b17 + b18),
        "hyp_g_mm2": hyp,
        "web25_g_mm": _mat("poly_webbing_25mm", "mass_g_m") / 1000.0,
        "web38_g_mm": _mat("poly_webbing_38mm", "mass_g_m") / 1000.0,
        "hood_family": sum(g(n) for n in ("crown hood B-19", "lip stiffener B-19s", "hood lining B-19L",
                                          "hood ladder strips B-20", "hood tongues x2 + POM", "hood grab tab")),
        "hood_tongues": g("hood tongues x2 + POM"),
    }


# New parts (ASSUMPTIONs named; settled on the first sewn joint by weighing)
TOGGLE_G = 3.0           # attach_system.TOGGLE_G: the existing hood-tongue POM toggle (ASSUMPTION there)
TOGGLE_N = 670.0         # attach_system.TOGGLE_N: bending pull-through (ASSUMPTION there)
BAR_LOOP_MM = 170.0      # ASSUMPTION: 25 mm webbing for the bar wrap (pi x ~20 mm OD incl. webbing = 63) + 2 x 40 mm
                         # toggle-loop / sewn eye + 30 mm toggle pocket; settled by the first sewn guy
B17_TRIM_MM = 40.0       # B-17 110 -> 70 mm tall: box-X 38 + double rows at 3 / 9 mm + 7 mm edge each side = 70
PIN_TETHER_G = 0.5       # ASSUMPTION: Dyneema cord pull loop on a pin (as on the hinge pins)
LOOP_LADDER_G = 4.0      # ladder_lock_25mm record mass (read in mass_table, named here for the B_loops note)


def mass_changes(variant: str, u: dict | None = None) -> list:
    """[(part, delta g, basis)] of a variant against the ledger attachment system (CORRIE B.2 on H1, belt M)."""
    u = u or unit_masses()
    ch = []
    w25, w38 = u["web25_g_mm"], u["web38_g_mm"]

    def im2_hooks():
        ch.extend([("IM2 bag hooks x2 (rated 38 mm)", -2 * u["bag_hook"], "ledger hook rows / 4"),
                   ("IM2 TPU hook sleeves x2", -2 * u["tpu_sleeve"], "ledger row / 4"),
                   ("T2 tongues x2 (38 mm x 160)", -2 * u["tongue_38"], "ledger 'bag-side straps' / 4"),
                   ("B-23 IM2 tongue backings x2", -u["b23_pair"], "ledger row"),
                   ("elastic keepers for the IM2 hooks x2", -2 * u["keeper"], "ledger row / 6")])

    def guys_only():
        ch.append(("hood B-19 + B-19s + B-19L + ladders B-20 + tongues/toggles + grab tab", -u["hood_family"],
                   "ledger rows"))
        ch.append(("guy bar loops x2: 25 mm webbing x 170 mm + POM toggle", 2 * (BAR_LOOP_MM * w25 + TOGGLE_G),
                   "poly_webbing_25mm record; toggle ASSUMPTION (attach_system.TOGGLE_G)"))

    if variant == "V0":
        return []
    if variant == "A_hinge":
        ch.extend([("hinge fairleads x2", -2 * u["fairlead"], "ledger row / 8 (frame re-raster needed to bank it)"),
                   ("hinge pins + sleeves x2", -2 * (u["pin"] + u["sleeve"]), "ledger rows / 8"),
                   ("hinge eyes HE x2 (38 mm x 150)", -2 * 150.0 * w38, "poly_webbing_38mm record"),
                   ("B-18 hinge doublers (pair)", -u["b18_pair"], "ledger spreader row, B-18 share by area"),
                   ("hinge swells (patch + B-13x) x2", -2 * (u["swell_patch"] + u["swell_b13x"]), "ledger rows / 8")])
    elif variant == "A_im3":
        ch.extend([("IM3 bag hooks x2", -2 * u["bag_hook"], "ledger hook rows / 4"),
                   ("IM3 TPU hook sleeves x2", -2 * u["tpu_sleeve"], "ledger row / 4"),
                   ("T3 tongues x2", -2 * u["tongue_38"], "ledger row / 4"),
                   ("B-17 IM3 tabs (pair)", -u["b17_pair"], "ledger spreader row, B-17 share by area"),
                   ("elastic keepers for the IM3 hooks x2", -2 * u["keeper"], "ledger row / 6")])
    elif variant == "C_im2":
        im2_hooks()
    elif variant == "B_guys":
        guys_only()
    elif variant == "B_loops":
        ch.append(("hood B-19 + B-19s + B-19L + ladders B-20 + tongues/toggles + grab tab", -u["hood_family"],
                   "ledger rows"))
        ch.append(("guy bar loops x2 (as B_guys)", 2 * (BAR_LOOP_MM * w25 + TOGGLE_G), "as B_guys"))
        # a bar loop must follow the torso (crown 601-804 mm): a 25 mm strap from a B-01 tab over the bar back to a
        # ladder lock (same parts as a guy end), 300 mm cut + ladder lock + tab 25 x 70
        ch.append(("bar loops CT x2: 25 mm x 300 + ladder lock + 25 x 70 tab + toggle",
                   2 * (300.0 * w25 + _mat("ladder_lock_25mm", "mass_g") + 70.0 * w25 + TOGGLE_G),
                   "poly_webbing_25mm + ladder_lock_25mm records; toggle ASSUMPTION"))
    elif variant in ("REC", "D_loops"):
        im2_hooks()
        guys_only()
        ch.append(("B-17 trimmed 110 -> 70 mm tall (pair)", -2 * 90.0 * B17_TRIM_MM * u["hyp_g_mm2"],
                   "hypalon_coated_nylon record, cut area"))
        if variant == "D_loops":
            ch.extend([("IM3 bag hooks x2 -> sewn eyes", -2 * u["bag_hook"], "ledger hook rows / 4"),
                       ("IM3 TPU sleeves x2", -2 * u["tpu_sleeve"], "ledger row / 4"),
                       ("IM3 keepers x2", -2 * u["keeper"], "ledger row / 6"),
                       ("pull-cord tethers on the IM3 pins x2", 2 * PIN_TETHER_G, "ASSUMPTION PIN_TETHER_G")])
    elif variant == "M_notop":
        return mass_changes("REC", u)
    return [(n, round(g, 2), b) for n, g, b in ch]


def mass_table() -> dict:
    rows = ledger_rows()
    base = round(sum(r["g"] for r in rows), 1)
    u = unit_masses(rows)
    out = {"basis": f"huntkit.mass.ledger system 'attachment', {CONFIG}, belt {SIZE}", "today_g": base, "variants": {}}
    for v in VARIANTS:
        ch = mass_changes(v, u)
        tot = round(base + sum(c[1] for c in ch), 1)
        # moves outside the attachment system (kept honest: D moves a hook onto the B-24 link, straps_meat)
        other = []
        if v == "D_loops":
            other.append(("B-24 link: a second rated hook per link (bag end), straps_meat", round(2 * u["bag_hook"], 1),
                          "ledger hook rows / 4"))
        out["variants"][v] = {"changes": ch, "attachment_g": tot, "delta_g": round(tot - base, 1),
                              "other_systems": other,
                              "net_pack_delta_g": round(tot - base + sum(o[1] for o in other), 1),
                              "meets_220": tot <= TARGET_G, "meets_200": tot <= STRETCH_G}
    return out


# ---------------------------------------------------------------------------------------------- procedures (R-08)
# Unit times: attach_system.PROCEDURES (hook 4 s, tethered pin 4 s, hood lift/drop 3 s, cams 12 s, clear 10 s) and
# the BL-003 REC additions (strap_arch.procedures: W1-W3 off 12 s, IM free ends out 21 s; on: 3 x (port + hook) + W).
TOGGLE_OFF_S = 4         # ASSUMPTION: a POM toggle out of its loop = one hook (4 s, gloved); timed on the prototype
TOGGLE_ON_S = 5          # ASSUMPTION: wrap the bar + push the toggle through its loop, gloved
EYE_SWAP_S = 20          # ASSUMPTION (D): move the IM3 strap's girth hitch to the frame eye and pin it, per side


def _sa():
    import strap_arch as SA
    return SA


def procedures(variant: str) -> dict:
    SA = _sa()
    H = SA.HOOK_S
    rec = SA.procedures()["rec"]
    w_off = dict(rec["bag_off"])["W1-W3 off"]
    im_out = dict(rec["bag_off"])["IM free ends out (3)"]
    on_extra = [t for n, t in rec["bag_on"] if n != "attach_system bag_on"]
    hooks = {"V0": 4, "A_hinge": 4, "A_im3": 2, "C_im2": 2, "B_guys": 4, "B_loops": 4, "REC": 2, "D_loops": 0,
             "M_notop": 2}[variant]
    hood = variant in ("V0", "A_hinge", "A_im3", "C_im2")
    hinge = variant != "A_hinge"
    n_tog = {"B_guys": 2, "B_loops": 4, "REC": 2, "D_loops": 2, "M_notop": 2}.get(variant, 0)
    off = [("Unhook W1-W3 at their G-hooks (BL-003).", w_off), ("Set the pack down on its back pad.", 3)]
    if hood:
        off.append(("Lift the hood tab and ease the bag top aft so the hood clears the bar (guys come with it).", 3))
    if n_tog:
        off.append((f"Pull the {n_tog} POM toggle(s) out of their loops at the crown bar; the guys stay on the bag.",
                    n_tog * TOGGLE_OFF_S))
    if hooks:
        off.append((f"Unclip the {hooks} bag hook(s) ({'IM3, then IM2' if hooks == 4 else 'IM3'}); hang each on its keeper.",
                    hooks * H))
    if variant == "D_loops":
        off.append(("IM3, each side: pull the pin, slide the bag's T3 eye off, move the IM3 strap's girth hitch to the "
                    "frame eye and pin it (tethered).", 2 * (H + EYE_SWAP_S)))
    off.append(("Unhook the 3 IM free ends and pull them out through the B-12 ports (BL-003).", im_out))
    off.append(("Pop the two under-strap cams; slide the floor channels off the straps.", 12))
    if hinge:
        off.append(("Pull the two hinge pins (tethered to the bag eyes).", 8))
    off.append(("Lift the bag clear.", 10))
    on = [("Stand the bag behind the frame, B-01 toward it.", 10)]
    if hinge:
        on.append(("Tip the bag onto the z 60 fairleads; pin both hinge eyes.", 12))
    on.append(("Lay US1/US2 in the floor channels and cam.", 12))
    if hooks:
        on.append((f"Clip the {hooks} bag hook(s) on the eyes, bottom up.", hooks * H))
    if variant == "D_loops":
        on.append(("IM3, each side: pull the pin, take the frame eye off, put the T3 eye on, girth-hitch the IM3 "
                    "strap onto it, pin.", 2 * (H + EYE_SWAP_S)))
    if hood:
        on.append(("Lift the hood, press the bag top to the crown, let go; snug the guys.", 3 + 6))
    if n_tog:
        on.append((f"Wrap each guy loop over the crown bar and push its toggle through ({n_tog}); check the guys are "
                   "snug (length was set once on the packed bag; do not crank).", n_tog * TOGGLE_ON_S + 6))
    on.append(("Feed the 3 IM free ends in through the ports, hook, cam flat; W1-W3 on and snug (BL-003).", sum(on_extra)))
    tot = lambda st: int(round(sum(t for _, t in st)))  # noqa: E731
    fl = [("Bag off (above).", tot(off)), ("Cradle, cam to a 70 mm belly.", SA.CRADLE_S),
          ("IM free ends on the right eyes over the meat, cam.", 3 * (SA.IM_STRAP_S - H)),
          ("Take the B-24 pair out of the kill kit.", SA.KIT_S),
          ("Hook a B-24 link on each IM3 eye.", SA.LINK_S),
          ("Hang the bag: clip each T3 hook into the loop that touches." if variant != "D_loops" else
           "Hang the bag: clip each B-24's second hook into the T3 eye.", SA.HANG_S),
          ("Close W1-W3 round bag and meat.", SA.WRAP_S)]
    return {"bag_off": off, "bag_on": on, "float": fl,
            "seconds": {"bag_off": tot(off), "bag_on": tot(on), "float": tot(fl)},
            "r08_pass": tot(off) <= BAG_OFF_LIMIT_S}


# ---------------------------------------------------------------------------------------------- task 1: inventory
def _station_case_loads() -> dict:
    """Beam-model factored load at each fairlead eye (max L/R), every rev C case of both couple variants
    (rev_c_verification.attachments method)."""
    from huntkit.fea.load_standard import ls1_envelope
    from huntkit.gendesign import bag_attach as BA
    env = ls1_envelope("C")
    out = {}
    for var, tag in (("crown_bar", ""), ("strap_upper", "@IM3")):
        for r in BA.case_loads(cases=env[var]):
            st = {}
            for nid, f in r["nodes"].items():
                s = BA._NODE_STATION.get(nid)
                if s:
                    st[s] = max(st.get(s, 0.0), round(f["n"], 0))
            out[r["case"] + tag] = st
    return out


def inventory() -> dict:
    """Every ledger attachment row with its station, its governing factored load per rev C case (beam model at the
    frame eye; cloth sim x 3.0 for the bag-side and top parts), capacity and margin (= capacity / factored load; the
    factored load already carries the case's required SF, so >= 1.0 passes and >= 2.0 is over twice the need)."""
    AS = json.loads((ROOT / "designs/pack_5200/analysis/attach_system_results.json").read_text())
    RC = json.loads((ROOT / "designs/pack_5200/analysis/rev_c_verification_results.json").read_text())["attachments"]
    sp = {p["id"]: p for p in AS["parts"]}
    st = _station_case_loads()
    rows = ledger_rows()
    fa, pin = RC["fairlead_fea"], RC["pin"]
    # station per ledger row; margin source
    M = {
        "bag-side load spreaders": ("IM3 tab B-17 / hinge doubler B-18", "im3+hinge",
                                    min(sp["B-17"]["sf"], sp["B-18"]["sf"]), "B-17 seam 3277 N / 1415; B-18 3277 / 1019"),
        "printed fairleads (8)": ("hinge, IM1, IM2, IM3 cleats (x2)", "all", min(fa["hinge"]["sf_fatigue"], fa["im3"]["sf_fatigue"]),
                                  "rev C: hinge cheek fatigue 1.67 governs (strength 2.97, im3 3.60)"),
        "7075 pins (8)": ("pins in every fairlead", "all", pin["sf_yield"], "double shear at 724 N (hinge)"),
        "UHMWPE sleeves (8)": ("pin sleeves", "all", pin["sleeve_sf"], "bearing at 724 N"),
        "bag hooks, 38 mm Al": ("IM2 + IM3 bag hooks (base mass of the rated part)", "im2+im3",
                                min(RC["bag_hook"]["sf"], sp["T3"]["sf"]), "same part as the rated-hook row"),
        "bag hooks 1500 N -> 2200 N": ("IM2 + IM3 bag hooks, rated 2200 N", "im2+im3",
                                       min(RC["bag_hook"]["sf"], sp["T3"]["sf"]),
                                       "IM3 cloth-sim hood-off 1415 N -> 1.55; beam IM2 512 N -> 4.30"),
        "TPU hook sleeves": ("quiet sleeves on the 4 bag hooks", "none", None, "no load (noise)"),
        "webbing eyes, net of old stubs": ("captive eyes on the 8 pins (net)", "all", sp["HE"]["sf"], "HE eye 2.31 (B-18 seam)"),
        "bag-side straps": ("T2 / T3 tongues", "im2+im3", min(sp["T2"]["sf"], sp["T3"]["sf"]), "T3 hook governs 1.55; T2 5.45"),
        "B-01 swell patches": ("swell plies over the cleats", "none", None, "no load (cleat clearance)"),
        "attachment: elastic keepers": ("hook keepers", "none", None, "no load (noise)"),
        "lifter tri-glide keepers": ("lifter tail keepers (lifter, not the joint)", "none", None, "backup only (lifter slip SF 4.2)"),
        "crown hood B-19": ("crown hood shell", "top", sp["B-19"]["sf"], "lip on bar 5407 N / 381"),
        "lip stiffener B-19s": ("hood lip stiffener", "top", sp["B-19"]["sf"], "part of the hood lip"),
        "hood lining B-19L": ("hood lining (XLPE)", "none", None, "no load (quiet)"),
        "hood ladder strips B-20": ("hood ladders", "top", sp["B-20"]["sf"], "rung 315 N / 79"),
        "hood tongues x2 + POM": ("hood tongues + toggles", "top", sp["HT"]["sf"], "toggle 670 N / 79"),
        "hood grab tab": ("hood grab tab", "none", None, "no load (handling)"),
        "top side guys x2": ("top side guys", "top", sp["TG"]["sf"], "ladder lock slip 300 N / 112"),
        "guy ladder locks + tri-glides": ("guy ladder locks + keepers + tabs", "top", sp["TG"]["sf"], "ladder lock slip"),
        "guy corner tabs B-22": ("guy corner tabs", "top", sp["B-22"]["sf"], "seam 1024 N / 112"),
        "guy tail elastic keepers": ("guy tail keepers", "none", None, "no load"),
        "IM2 tongue backings B-23": ("IM2 tongue backing", "im2", sp["B-23"]["sf"], "tear-out 3628 N / 403"),
        "thread (box-X + perimeters)": ("thread", "all", None, "inside the parts above"),
        "B-13x boxed fairlead swell": ("boxed swells over the 8 cleats", "none", None, "no load (cleat clearance)"),
    }
    out = []
    for r in rows:
        key = next((k for k in M if k in r["name"]), None)
        if key is None:
            raise KeyError(r["name"])
        what, stn, sf, basis = M[key]
        per_case = {}
        for case, s in st.items():
            if stn == "none":
                continue
            if stn == "top":
                continue
            vals = [s.get(x, 0.0) for x in (stn.replace("+", " ").split() if stn != "all" else ("hinge", "im1", "im2", "im3"))]
            if max(vals, default=0) > 0:
                per_case[case] = max(vals)
        out.append({"ledger_id": r["id"], "name": r["name"], "g": r["g"], "what": what, "station": stn,
                    "load_path": r["load_path"], "per_case_factored_n": per_case,
                    "margin": None if sf is None else round(float(sf), 2), "basis": basis,
                    "no_load": stn == "none", "over_2x": sf is not None and sf >= 2.0})
    # top parts: rev C applies them in C5 / C7 only (hood 52.5 N/g, 2 guys 34.6 N/g each; load_standard rev C)
    top_cases = {"meat_straps": 3.0, "overload_haul": 1.6}
    for o in out:
        if o["station"] == "top":
            o["per_case_factored_n"] = {c: round(f * (52.5 if "hood" in o["what"] else 34.6), 0) for c, f in top_cases.items()}
    return {"rows": out, "station_cases": st, "total_g": round(sum(o["g"] for o in out), 1)}


# ---------------------------------------------------------------------------------------------- tables
def _cell(v, shell, t, cn, k="cg_y"):
    r = get(v, shell, t)
    if not r:
        return None
    return r["cases"][cn].get(k)


def table_cg() -> list:
    """One line per (variant, shell, torso) stored: fill / meat CG, convergence stage, peak anchor loads, R-28."""
    d = load_results()["rows"]
    lines = []
    for key in sorted(d, key=lambda k: (list(VARIANTS).index(d[k]["variant"]), d[k]["shell"], d[k]["torso"])):
        r = d[key]
        f, m = r["cases"]["fill"], r["cases"]["meat"]
        L = {}
        for cn in ("fill", "meat"):
            for k_, val in r["cases"][cn]["loads_1g"].items():
                L[k_] = max(L.get(k_, 0.0), val)
        pk = lambda a, b: max(L.get(a, 0.0), L.get(b, 0.0))  # noqa: E731
        lines.append({"key": key, "variant": r["variant"], "shell": r["shell"], "torso": r["torso"],
                      "fill_cg": f["cg_y"], "meat_cg": m["cg_y"],
                      "fill_conv": f["converged"], "fill_round": f["rounding_mm"], "meat_conv": m["converged"],
                      "meat_round": m["rounding_mm"], "fill_L": f["closed_L"],
                      "hinge": pk("hinge_R", "hinge_L"), "im2": pk("hook_im330_R", "hook_im330_L"),
                      "im3": pk("hook_im520_R", "hook_im520_L"), "guy": pk("TG_R", "TG_L"),
                      "loop": pk("CT_R", "CT_L"), "pocket": L.get("pocket", 0.0),
                      "r28_fill": r["r28"]["fill"]["worst_contact_deg"], "r28_meat": r["r28"]["meat"]["worst_contact_deg"],
                      "r28_pass": r["r28"]["fill"]["pass"] and r["r28"]["meat"]["pass"],
                      "wall_head": max(r["r28"]["fill"]["wall_toward_head_above_bar_mm"],
                                       r["r28"]["meat"]["wall_toward_head_above_bar_mm"])})
    return lines


def table_md() -> str:
    h = ("| variant | shell | torso | fill CG mm (conv, rounding) | meat CG mm (conv, rounding) | fill L | hinge N | IM2 hook N | "
         "IM3 hook N | guy N | bar loop N | hood N | R-28 first contact deg fill / meat | wall to head above bar mm |\n"
         "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    out = [h]
    cv = lambda c, s: f"{'yes' if c else 'NO'}, {s:g} mm" if s is not None else ("yes" if c else "NO")  # noqa: E731
    for l_ in table_cg():
        out.append(f"| {l_['variant']} | {l_['shell']} | {l_['torso']} | {l_['fill_cg']:.1f} ({cv(l_['fill_conv'], l_['fill_round'])}) | "
                   f"{l_['meat_cg']:.1f} ({cv(l_['meat_conv'], l_['meat_round'])}) | {l_['fill_L']:.1f} | {l_['hinge']:.0f} | "
                   f"{l_['im2']:.0f} | {l_['im3']:.0f} | {l_['guy']:.0f} | {l_['loop']:.0f} | {l_['pocket']:.0f} | "
                   f"{l_['r28_fill']:.0f} / {l_['r28_meat']:.0f} {'pass' if l_['r28_pass'] else 'FAIL'} | {l_['wall_head']:.0f} |")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- load paths (task 4)
def peak_1g(variant: str, group_pair: tuple, torsos=TORSOS, shells=SHELLS) -> tuple:
    best = (0.0, None)
    for s in shells:
        for t in torsos:
            r = get(variant, s, t)
            if not r:
                continue
            for cn in ("fill", "meat"):
                for g_ in group_pair:
                    v = r["cases"][cn]["loads_1g"].get(g_, 0.0)
                    if v > best[0]:
                        best = (v, f"{s} {t} in {cn}")
    return best


def load_paths() -> list:
    """Changed load paths of REC for BL-010: location, direction, factored N, part, rated N. Factored = 3.0 x the
    worst 1 g cloth-sim force over both shells and the torsos run (REC, and the M_notop misuse for the IM3 hook)."""
    RC = json.loads((ROOT / "designs/pack_5200/analysis/rev_c_verification_results.json").read_text())["attachments"]
    im3, w3 = peak_1g("REC", ("hook_im520_R", "hook_im520_L"))
    im3m, wm = peak_1g("M_notop", ("hook_im520_R", "hook_im520_L"))
    im3_0, w0 = peak_1g("V0", ("hook_im520_R", "hook_im520_L"))
    guy, wg = peak_1g("REC", ("TG_R", "TG_L"))
    guy0, wg0 = peak_1g("V0", ("TG_R", "TG_L"))
    hin, wh = peak_1g("REC", ("hinge_R", "hinge_L"))
    hin0, wh0 = peak_1g("V0", ("hinge_R", "hinge_L"))
    beam_im2 = RC["gov_c"]["im2"]
    return [
        {"location": "IM3 eyes z 520, x +/-115 (bag hook on T3 / B-17)", "direction": "aft and up along the tongue, from the B-17 bridle to the eye",
         "factored_n": round(FACTOR * max(im3, im3m)), "basis": f"3.0 x max(REC {im3:.0f} N [{w3}], guys-off misuse {im3m:.0f} N [{wm}]); today V0 {im3_0:.0f} N [{w0}]",
         "part": "rated 38 mm bag hook (PT-1), T3 tongue box-X, B-17 seam (80 mm loaded, tab trimmed to 70 mm tall)",
         "rated_n": "hook 2200 (purchase requirement); B-17 seam 3277; box-X 5256"},
        {"location": "IM2 eyes z 330, x +/-115", "direction": "bag load removed (no bag hook); meat strap IM2 unchanged",
         "factored_n": 0, "basis": f"beam model still books the bag-case 'strap_mid' share here: {beam_im2['n']:.0f} N "
         f"({beam_im2['case']}, {beam_im2['node']}); BL-010 must move that share to the IM3 / hinge nodes",
         "part": "none (T2, B-23, IM2 bag hooks deleted)", "rated_n": "-"},
        {"location": "crown top bar, x +/-(92-100), on the corner-wrap zone next to the leg", "direction":
         "aft and outboard toward the B-22 tab (x +/-149, z 695); up-aft at 23 in, down-aft at 15 in",
         "factored_n": round(FACTOR * guy), "basis": f"3.0 x REC guy {guy:.0f} N [{wg}]; today V0 guy {guy0:.0f} N [{wg0}] (through the hood ear)",
         "part": "guy bar loop: 25 mm webbing round the bar, POM toggle in a sewn loop; ladder lock + tri-glide at B-22",
         "rated_n": f"toggle {TOGGLE_N:.0f} (ASSUMPTION), ladder lock slip 300, B-22 seam 1024"},
        {"location": "crown top bar centre x +/-66", "direction": "hood capture removed",
         "factored_n": 0, "basis": "hood deleted; rev C's 52.5 N/g hood term in C5 / C7 can be dropped for REC",
         "part": "none", "rated_n": "-"},
        {"location": "hinge eyes z 60, x +/-115", "direction": "down and aft into the pin (unchanged path)",
         "factored_n": round(max(FACTOR * hin, RC["gov_c"]["hinge"]["n"])), "basis": f"max(3.0 x REC {hin:.0f} N [{wh}], beam {RC['gov_c']['hinge']['n']:.0f} N); today V0 sim {hin0:.0f} N [{wh0}]",
         "part": "HE eye on B-18, 5 mm 7075 pull-pin", "rated_n": "B-18 seam 2355 (HE governs), bartack 2700"},
    ]


# ---------------------------------------------------------------------------------------------- screenshots
def plot_cg_mass(path: Path | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mt = mass_table()
    vs = [v for v in VARIANTS if v != "M_notop"]
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 6.2), dpi=100, gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axs[0]
    cols = {"CORRIE": "#8a5a2b", "S15": "#2d6a4f"}
    y = np.arange(len(vs))
    for j, s in enumerate(SHELLS):
        for cn, mk in (("meat", "o"), ("fill", "s")):
            xs = [_cell(v, s, 15, cn) for v in vs]
            conv = [_cell(v, s, 15, cn, "converged") for v in vs]
            for yi, x, c in zip(y, xs, conv):
                if x is None:
                    continue
                ax.scatter([x], [yi + (j - 0.5) * 0.3], marker=mk, s=60, edgecolor=cols[s],
                           facecolor=cols[s] if c else "white", lw=1.5, zorder=3)
        ref = [_cell("V0", s, 15, "meat")]
        if ref[0] is not None:
            ax.axvline(ref[0], color=cols[s], lw=1, ls="--", alpha=0.7)
    ax.axvline(LIMIT["meat"], color="#c0392b", lw=1.4, ls=":")
    ax.text(LIMIT["meat"] + 0.5, len(vs) - 0.6, "rev C meat 190", color="#c0392b", fontsize=8)
    ax.axvline(LIMIT["fill"], color="#555", lw=1.2, ls=":")
    ax.text(LIMIT["fill"] + 0.5, len(vs) - 0.6, "rev C fill 205", color="#555", fontsize=8)
    ax.set_yticks(y)
    import textwrap
    ax.set_yticklabels([f"{v}\n" + "\n".join(textwrap.wrap(VARIANTS[v]["label"], 34)[:2]) for v in vs], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("load CG aft of the stay datum, mm (15 in torso, 68 kg, coarse h 40)")
    ax.set_title("15 in CG per variant: circle = meat, square = fill\nbrown = CORRIE, green = S15; open = not converged; "
                 "dashed = that shell's V0", fontsize=9)
    ax.grid(alpha=0.3)
    ax2 = axs[1]
    g = [mt["variants"][v]["attachment_g"] for v in vs]
    bars = ax2.barh(y, g, color=["#2d6a4f" if v == "REC" else "#9aa5ad" for v in vs])
    for b_, v_ in zip(bars, g):
        ax2.text(v_ + 3, b_.get_y() + b_.get_height() / 2, f"{v_:.0f} g ({v_ / 28.3495:.1f} oz)", va="center", fontsize=8)
    ax2.axvline(TARGET_G, color="#c0392b", ls="--", lw=1.2)
    ax2.axvline(STRETCH_G, color="#c0392b", ls=":", lw=1.0)
    ax2.text(TARGET_G + 2, -0.6, "goal 220", color="#c0392b", fontsize=8)
    ax2.text(STRETCH_G - 75, -0.6, "stretch 200", color="#c0392b", fontsize=8)
    ax2.set_yticks(y)
    ax2.set_yticklabels(vs, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlim(0, max(g) * 1.3)
    ax2.set_xlabel("attachment system mass, g (ledger, CORRIE B.2 on H1, belt M)")
    ax2.set_title(f"Attachment mass (today {mt['today_g']:.0f} g)", fontsize=9)
    fig.suptitle("BL-004 attachment diet: CG at 15 in and mass per variant", fontsize=11, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = path or SCREENS / f"{PREFIX}1.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_diagram(path: Path | None = None) -> Path:
    """Side view (x = 0 section, loaded S15 meat profile at 15 in) and frame-side view of the REC joint."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyBboxPatch
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 7.4), dpi=100, gridspec_kw={"width_ratios": [1, 1.15]})
    # ---- side view
    r = get("REC", "S15", 15)
    r0 = get("V0", "S15", 15)
    for rr, col, lab in ((r0, "#bbbbbb", "V0 loaded (meat, 15 in)"), (r, "#2d6a4f", "REC loaded (meat, 15 in)")):
        if rr:
            P = np.asarray(rr["cases"]["meat"]["profile"], float)
            a1.plot(P[:, 1], P[:, 0], color=col, lw=1.6, label=lab)
            a1.plot(P[:, 2], P[:, 0], color=col, lw=1.6)
    zs = np.linspace(0, 800, 50)
    a1.plot(np.zeros_like(zs), zs, color="#333", lw=3, label="stay (frame axis)")
    for t, zt in ((15, 601.0), (19, 702.6), (23, 804.2)):
        a1.add_patch(Circle((22.7 - 9, zt), 9, color="#333" if t == 15 else "#999", zorder=4))
        a1.text(-60, zt, f"bar {t} in", fontsize=7, va="center")
    for z, lab, keep in ((60, "hinge eye + pull-pin", True), (190, "IM1 (meat only)", None), (330, "IM2 bag hook DELETED", False),
                         (520, "IM3 rated hook on T3 / B-17 (70 mm)", True)):
        c = "#2d6a4f" if keep else ("#c0392b" if keep is False else "#888")
        a1.plot([0, 30], [z, z], color=c, lw=3)
        a1.text(36, z, lab, fontsize=8, color=c, va="center")
    a1.annotate("", xy=(22.7, 601), xytext=(205, 695), arrowprops=dict(arrowstyle="-", color="#1f6f9f", lw=2.2))
    a1.text(110, 668, "guy (side face, x 149 -> bar x 100)", color="#1f6f9f", fontsize=8, rotation=24)
    a1.text(30, 765, "hood + ladders DELETED", color="#c0392b", fontsize=8)
    a1.set_aspect("equal")
    a1.set_xlim(-90, 470)
    a1.set_ylim(-20, 1130)
    a1.set_xlabel("y aft of the stay datum, mm")
    a1.set_ylabel("z above the hip datum, mm")
    a1.legend(fontsize=7, loc="upper right")
    a1.set_title("Side view, x = 0 (S15 shell, 15 in, meat case)", fontsize=9)
    a1.grid(alpha=0.25)
    # ---- frame-side view (looking at B-01 from the wearer)
    W = 197.0
    a2.add_patch(FancyBboxPatch((-W, 35), 2 * W, 710, boxstyle="round,pad=0,rounding_size=12", fc="#e9efe9", ec="#2d6a4f", lw=1.2))
    for sx in (-1, 1):
        a2.plot([sx * 115, sx * 112], [40, 560], color="#555", lw=5, alpha=0.6)
        a2.plot([sx * 104, sx * 104], [560, 830], color="#555", lw=4, alpha=0.5)
        a2.add_patch(Circle((sx * 115, 60), 8, fc="#2d6a4f"))
        a2.add_patch(Circle((sx * 115, 190), 6, fc="#888"))
        a2.add_patch(Circle((sx * 115, 330), 6, fc="#888"))
        a2.plot([sx * 105, sx * 125], [320, 340], color="#c0392b", lw=2)
        a2.plot([sx * 105, sx * 125], [340, 320], color="#c0392b", lw=2)
        a2.add_patch(FancyBboxPatch((sx * 115 - 45, 415), 90, 70, boxstyle="round,pad=0,rounding_size=6", fc="#cfd8cf", ec="#2d6a4f"))
        a2.plot([sx * 115, sx * 115], [450, 520], color="#2d6a4f", lw=5)
        a2.add_patch(Circle((sx * 115, 520), 7, fc="#2d6a4f"))
        a2.add_patch(FancyBboxPatch((sx * 149 - 25, 665), 50, 60, boxstyle="round,pad=0,rounding_size=5", fc="#cfe0ea", ec="#1f6f9f"))
        a2.plot([sx * 149, sx * 96], [695, 601], color="#1f6f9f", lw=3)
        a2.add_patch(FancyBboxPatch((sx * 96 - 6, 593), 12, 16, boxstyle="round,pad=0,rounding_size=2", fc="#1f6f9f", ec="k", lw=0.5))
        a2.add_patch(FancyBboxPatch((sx * 60 - 20, 545), 40, 250, fc="none", ec="#c0392b", ls="--", lw=1))
    a2.plot([-104, 104], [601, 601], color="#333", lw=6)
    a2.text(0, 612, "crown top bar (15 in): bare, no hood", ha="center", fontsize=8)
    a2.text(0, 805, "B-20 ladders + B-19 hood: deleted", ha="center", fontsize=8, color="#c0392b")
    notes = [("z 60", "hinge: HE eye on B-18, tethered pull-pin (kept)"),
             ("z 330", "IM2: bag hook, T2, B-23 deleted; eye stays for meat strap IM2"),
             ("z 450-520", "IM3: rated hook on T3, B-17 90 x 70 (was 110)"),
             ("z 695", "B-22 + ladder lock: guy set once on the packed bag"),
             ("bar", "guy end: 25 mm loop round the bar, POM toggle")]
    for i, (z, t_) in enumerate(notes):
        a2.text(-W, -40 - 30 * i, f"{z}: {t_}", fontsize=8)
    a2.set_aspect("equal")
    a2.set_xlim(-230, 230)
    a2.set_ylim(-200, 860)
    a2.axis("off")
    a2.set_title("Frame side of the bag (wearer's view), REC", fontsize=9)
    mt = mass_table()["variants"]["REC"]
    fig.suptitle(f"BL-004 recommended attachment: {mt['attachment_g']:.0f} g (was {mass_table()['today_g']:.0f} g)",
                 fontsize=11, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = path or SCREENS / f"{PREFIX}2.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------------- CLI
def queue():
    done = load_results()["rows"]
    for v, s, t in PLAN:
        if f"{v}_{s}_PR{t}" in done:
            continue
        print(f"=== {v} {s} {t} in", flush=True)
        try:
            row = run(v, s, t)
            print(json.dumps({cn: {k: c[k] for k in ("converged", "rounding_mm", "cg_y", "closed_L")}
                              for cn, c in row["cases"].items()}), flush=True)
        except Exception as e:  # keep the queue going; the failure is reported
            print(f"FAILED {v} {s} {t}: {e!r}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["inventory", "scenarios", "run", "queue", "table", "mass", "times", "loadpaths",
                                    "plot", "reextract"])
    ap.add_argument("variant", nargs="?")
    ap.add_argument("--shell", default="S15")
    ap.add_argument("--torso", type=int, default=15)
    a = ap.parse_args(argv)
    if a.cmd == "inventory":
        print(json.dumps(inventory(), indent=1))
    elif a.cmd == "scenarios":
        print("\n".join(str(p) for p in write_scenarios()))
    elif a.cmd == "run":
        run(a.variant, a.shell, a.torso)
        print(table_md())
    elif a.cmd == "queue":
        queue()
    elif a.cmd == "table":
        print(table_md())
    elif a.cmd == "mass":
        print(json.dumps(mass_table(), indent=1))
    elif a.cmd == "times":
        print(json.dumps({v: procedures(v)["seconds"] for v in VARIANTS}, indent=1))
    elif a.cmd == "loadpaths":
        print(json.dumps(load_paths(), indent=1))
    elif a.cmd == "plot":
        print(plot_cg_mass())
        print(plot_diagram())
    elif a.cmd == "reextract":
        d = load_results()
        for k, r in list(d["rows"].items()):
            store(extract(r["variant"], r["shell"], r["torso"]))


if __name__ == "__main__":
    main()
