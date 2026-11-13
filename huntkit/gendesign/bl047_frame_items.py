"""BL-047 frame-side items from the fourth bag review (review_20261113_rev3_fourth.md), added to BL-047 by the
orchestrator 2026-11-13:

* **m-1** ``hinge_relief``: the HE fold cleared the hinge throat-corner fillet by 0.19-0.29 mm on a 0.05 mm print
  tolerance. Frame-side relief: the throat floor relieved 1.0 mm deep within 1.5 mm of each cheek face (round-bottomed
  groove along the cheek, the corner fillet cut away), both hinge fairleads (z 60). ``frame_h1.print_mesh`` calls
  it after the fairleads. ``he_check`` re-runs the bag's ``he_stl_check`` on the re-exported HE-FIT piece, and again
  with the print tolerance at 0.15 mm (floor 0.10 mm higher than the check's 0.05).
* **M-A** ``tl1_recheck``: ``crown_tube_guy_loop.b25_topology_recheck`` on BL-046's geometry (spine in the legs'
  plane, 25.02 mm fore of the bar, collar 6.0): the B-25 run now leaves the mitre toward the spine 25 mm fore, so the
  drop / mitre pull on the sleeve turns fore-down instead of straight down (BL-045 modelled it straight down). The
  TL-1 proof load and pull vector are published (``TL1_PROOF_N``, ``TL1_PULL_UNIT``) for the bag kit.
* **M-C** ``hinge_one_number``: one hinge-row load for frame and bag: ``HINGE_ROW_N`` = 1019 N factored (the bag's
  row, attach_system.factored_loads: max(3.0 x the worst 1 g sim hinge eye, beam model)); the frame's fairlead and
  pin checks re-run on it in both load directions the frame has on file.

Record: designs/pack_5200/analysis/bl047_frame_items.json (and crown_gnl.md section 8). Units mm, N, MPa.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "bl047_frame_items.json"

# ---------------------------------------------------------------------------------------------------- m-1
RELIEF_W = 1.5               # review m-1 / corrie_f_body.md 23.2: within 1.5 mm of each cheek face
RELIEF_DEPTH = 1.0           # 1 mm below the throat floor
RELIEF_UP = 4.5              # up the cheek face: past the corner fillet (floor rises 3.5 mm in the last 0.5 mm)
RELIEF_INTO_CHEEK = 0.2      # the cut reaches 0.2 mm into the cheek face (no coplanar faces; 2.5 % of an 8 mm cheek)
PRINT_TOL_REVIEW = 0.15      # review m-1: 0.6 mm-nozzle PAHT-CF slot prints 0.1-0.2 mm off; he_stl_check assumes 0.05
HE_TOL_IN_CHECK = 0.05

# ---------------------------------------------------------------------------------------------------- M-C
HINGE_ROW_N = 1019.0         # factored, per side (= mfg_corrie_f_rev3.HINGE_N; attach_system_results.json factored_n)
HINGE_ROW_FACTOR = 3.0       # HA-LS-1 rev C C5 / C2: 2.0 g x 1.5 on the 1 g force

# ---------------------------------------------------------------------------------------------------- M-A (published)
TL1_PROOF_N = None           # filled from tl1_recheck() in the record; constants below are the published values
TL1_PULL_UNIT = None


def hinge_stations() -> list:
    from . import h1_fairleads as HF
    return [p for p in HF.placed() if p["name"] == "hinge"]


def relief_solid(p: dict):
    """The m-1 relief of one hinge fairlead (manifold3d): per cheek, a groove 1.5 mm wide along the cheek (z), its
    bottom 1.0 mm below the floor and rounded (r 0.75), open up the cheek face to floor + 4.5 mm."""
    import manifold3d as m3d
    g = p["geom"]
    hz = g.half_z + 1.0
    out = None
    r = RELIEF_W / 2.0
    for sx in (-1.0, 1.0):
        face = p["x"] + sx * g.throat / 2.0
        xi = face - sx * RELIEF_W                              # inboard edge of the relief
        xo = face + sx * RELIEF_INTO_CHEEK
        xa, xb = min(xi, xo), max(xi, xo)
        ybot = p["y_floor"] - RELIEF_DEPTH
        cyl = []
        for xx in (xa + r, xb - r if xb - r > xa + r else xa + r + 1e-3):
            for yy in (ybot + r, p["y_floor"] + RELIEF_UP):
                cyl.append(m3d.Manifold.cylinder(2 * hz, r, r, 32, center=True).translate((xx, yy, p["z"])))
        c = m3d.Manifold.batch_hull(cyl)
        out = c if out is None else out + c
    return out


def hinge_relief(man, stats: dict | None = None):
    v0 = man.volume()
    for p in hinge_stations():
        man = man - relief_solid(p)
    if stats is not None:
        stats.update({"cut_mm3": v0 - man.volume(), "g": -(v0 - man.volume()) * 1.06e-3})
    return man


def he_check() -> dict:
    """The bag's he_stl_check on the re-exported HE-FIT piece, as written (0.05 mm tolerance) and with the floor
    0.10 mm higher everywhere (0.15 mm print tolerance, review m-1)."""
    import importlib
    import sys
    for q in (str(REPO), str(PACK), str(PACK / "concepts")):
        if q not in sys.path:
            sys.path.insert(0, q)
    H = importlib.import_module("he_stl_check")
    res = H.check()
    extra = PRINT_TOL_REVIEW - HE_TOL_IN_CHECK
    up = res["under_pin"]
    out = {"as_written": {k: res[k] for k in ("worst_under_pin_clear_mm", "min_clear_off_corner_mm",
                                               "throat_clear_side_mm", "worst_loop_overlap_mm2",
                                               "min_box_top_to_cheek_mm", "pass")},
           "per_ply": {t: {"worst": v["worst"]["clear_mm"], "centred": v["centred_clear_mm"],
                           "off_corner": v["clear_off_corner_mm"], "where": v["worst"]["x_from_throat_cl"]}
                       for t, v in up.items()},
           "tol_0p15": {"worst_under_pin_clear_mm": round(res["worst_under_pin_clear_mm"] - extra, 3),
                        "throat_clear_side_mm": round(res["throat_clear_side_mm"] - extra / 2.0, 3)}}
    out["tol_0p15"]["meets_0p5_everywhere"] = bool(out["tol_0p15"]["worst_under_pin_clear_mm"] >= 0.5)
    return out


# ---------------------------------------------------------------------------------------------------- M-A
def run_vector() -> dict:
    """Direction of the B-25 run at the sleeve on BL-046's geometry (bar axis at y 0, z 0; x from the spine centre;
    y + aft): from the mitre centre (corrie_f.b25_topology, s down from the bar centre) to the spine-wrap tangent on the
    spine, which sits ``spine_fore_mm`` fore of the bar. The drop is short and flexible, so the sleeve sees the strip
    tension along this line (the mitre swings under the bar until the drop is in line with the run)."""
    from .crown_tube_guy_loop import _corrie
    C = _corrie()
    tp = C.b25_topology()
    xm = 0.5 * (tp["mitre"]["x"][0] + tp["mitre"]["x"][1])
    sm = 0.5 * (tp["mitre"]["s"][0] + tp["mitre"]["s"][1])
    xs = tp["run_x"][0]
    ss = 0.5 * (tp["run_s"][0] + tp["run_s"][1])
    d = np.array([xs - xm, -float(tp["spine_fore_mm"]), -(ss - sm)])
    # from the sleeve's exit (bar underside, x at the mitre centre) to the spine wrap: the drop + run line
    d_sleeve = np.array([xs - xm, -float(tp["spine_fore_mm"]), -(ss - C.BAR_OD / 2.0)])
    u = d_sleeve / np.linalg.norm(d_sleeve)
    return {"mitre_centre_x_s": [xm, sm], "spine_wrap_x_s": [xs, ss], "spine_fore_mm": tp["spine_fore_mm"],
            "collar_mm": tp["clamp_collar_mm"], "u_run": u.tolist(), "yz_share": float(math.hypot(u[1], u[2])),
            "plan_angle_fore_deg": float(math.degrees(math.atan2(-d[1], -d[0]))),
            "below_horizontal_deg": float(math.degrees(math.atan2(-u[2], math.hypot(u[0], u[1]))))}


def tl1_recheck() -> dict:
    """b25_topology_recheck's pull-vector sum with the run along ``run_vector`` (BL-045: straight down), the same
    capacity rows, the TL-1 proof and its pull vector (the governing run's resultant on the sleeve, in frame axes,
    the outboard x share included)."""
    from . import crown_tube_guy_loop as T
    base = T.b25_topology_recheck()
    rv = run_vector()
    u = np.asarray(rv["u_run"], float)
    gp = json.loads(T.GUY_PATHS.read_text())["rows"]
    cp = json.loads(T.CROWN_PATHS.read_text())["rows"]
    sl = T.sim_loads()
    runs = []
    for t in T.TORSO_SIMS:
        for case in ("fill", "meat"):
            g = gp.get(f"F_r1_PR{int(t)}_fineFM_port:{case}")
            c = cp.get(f"F_r1_PR{int(t)}_fineFM_over_port:{case}")
            r = sl["by_torso"][t]["rows"].get(case)
            if not (g and c and r):
                continue
            for side in ("R", "L"):
                ug = -np.asarray(g[side]["u_bag"], float)
                uc = -np.asarray(c[side]["u_bag"], float)
                xo = float(g[side]["outboard_share_at_bar"])
                Fg, Fc = r["guy"], r["crown"]
                T_ = Fg * max(xo, 0.0)
                v3 = Fg * ug + Fc * uc + T_ * u                                    # 3D on the sleeve
                v = np.array([v3[1], v3[2]])
                old = Fg * np.array([ug[1], ug[2]]) + Fc * np.array([uc[1], uc[2]]) + T_ * np.array([0.0, -1.0])
                runs.append({"torso": t, "case": case, "side": side, "ug": ug.tolist(), "uc": uc.tolist(), "Fg": Fg,
                             "Fc": Fc, "outboard_share": xo, "k_vector": float(np.linalg.norm(v)) / (Fg + Fc),
                             "k_vector_bl045": float(np.linalg.norm(old)) / (Fg + Fc), "v3_1g": v3.tolist(),
                             "scalar_1g_n": Fg + Fc})
    kv = max(r["k_vector"] for r in runs)
    gov = max(runs, key=lambda r: r["k_vector"])
    env = T.kit_loads()["envelope"]
    rc = T.section("rev_c")
    w = base["topology"]["on_bar"]["sleeve"]["width_mm"]
    kb = base["k_bound_max"]
    rows = {}
    for key, k in (("vector_bl046", kv), ("vector_bl045", base["k_vector_max"]), ("bound", kb)):
        e2 = dict(env, static_n=env["static_n"] * k, fatigue_peak_n=env["fatigue_peak_n"] * k, proof_n=env["proof_n"] * k)
        rows[key] = {"k": round(k, 4), **{kk: round(float(vv), 3) for kk, vv in T.check_row(rc, w, e2, "A").items()
                                          if kk != "basis"}}
    proof = round(max(T.PROOF * env["static_n"] * kv, env["static_n"] * kv / 0.654), 0)
    proof_bound = round(max(T.PROOF * env["static_n"] * kb, env["static_n"] * kb / 0.654), 0)
    v3 = np.asarray(gov["v3_1g"], float)
    pu = v3 / np.linalg.norm(v3)
    # frame axes: x outboard (+ toward the leg on that side), y aft (toward the bag), z up
    pull = {"unit_x_out_y_aft_z_up": [round(float(abs(pu[0])), 3), round(float(pu[1]), 3), round(float(pu[2]), 3)],
            "below_horizontal_deg": round(float(math.degrees(math.atan2(-pu[2], math.hypot(pu[0], pu[1])))), 1),
            "outboard_pct": round(float(100 * abs(pu[0])), 1), "aft_pct": round(float(100 * pu[1]), 1),
            "fore_component": bool(pu[1] < 0), "governing_run": {k: gov[k] for k in ("torso", "case", "side")}}
    ug = np.asarray(gov["ug"], float)
    proof_pub = max(proof, base["proof_tl1_n"])
    share_g = gov["Fg"] / (gov["Fg"] + gov["Fc"])
    pull["rig"] = {"guy_toggle_pull_n": round(proof_pub * share_g, 0),
                   "guy_unit_x_out_y_aft_z_up": [round(float(abs(ug[0])), 3), round(float(ug[1]), 3), round(float(ug[2]), 3)],
                   "guy_below_horizontal_deg": round(float(math.degrees(math.atan2(-ug[2], math.hypot(ug[0], ug[1])))), 1),
                   "guy_outboard_pct": round(100 * float(gov["outboard_share"]), 1),
                   "crown_strap_toggle_n": round(proof_pub * (1 - share_g), 0),
                   "run_spine_end": "anchored to a stub of the OD 20 spine tube 25.0 mm fore of the bar axis, the "
                                    "6.0 mm collar fitted (BL-046 geometry); the run then pulls fore-down by itself",
                   "fore_component_of_run_on_sleeve": round(float(-u[1]), 3)}
    ob = max(runs, key=lambda r: r["outboard_share"])         # the run that loads the drop hardest (pull B)
    ugb = np.asarray(ob["ug"], float)
    pull["rig_B_run_loaded"] = {
        "guy_toggle_pull_n": round(proof_pub * ob["Fg"] / (ob["Fg"] + ob["Fc"]), 0),
        "guy_unit_x_out_y_aft_z_up": [round(float(abs(ugb[0])), 3), round(float(ugb[1]), 3), round(float(ugb[2]), 3)],
        "guy_below_horizontal_deg": round(float(math.degrees(math.atan2(-ugb[2], math.hypot(ugb[0], ugb[1])))), 1),
        "guy_outboard_pct": round(100 * float(ob["outboard_share"]), 1),
        "crown_strap_toggle_n": round(proof_pub * ob["Fc"] / (ob["Fg"] + ob["Fc"]), 0),
        "k_vector": round(ob["k_vector"], 4), "run": {k: ob[k] for k in ("torso", "case", "side")}}
    return {"run_vector": rv, "k_vector_bl046": round(kv, 4), "k_vector_bl045": round(base["k_vector_max"], 4),
            "k_bound": round(kb, 4), "rows": rows, "proof_tl1_n": proof, "proof_tl1_bl045_n": base["proof_tl1_n"],
            "proof_bound_n": proof_bound, "pull": pull,
            "proof_publish_n": max(proof, base["proof_tl1_n"]),
            "note": "TL-1 proofs the bound or the vector? The bound (run in line with the guy) is not a physical pull "
                    "on BL-046's geometry (the run now heads fore, the guy aft); the proof is set on the larger of the "
                    "BL-046 vector and BL-045's published 497 N, so it never drops below the released value."}


# ---------------------------------------------------------------------------------------------------- M-C
def hinge_one_number() -> dict:
    """Frame hinge fairlead and pin at the bag's 1019 N row. The linear voxel FE of the fairlead (h1_fairleads.fea
    'bl042', the hinge geometry since BL-042) is scaled from each of its two load directions on file: rev C (beam
    model, 724 N factored, mostly down the stay) and the worst frame-side sim vector (F_PR15_fineFM meat L, 250 N at
    1 g, inboard and up). Fatigue on 1.6 g x 1019 / 3.0."""
    from . import h1_fairleads as HF
    d = json.loads((ANALYSIS / "h1_fairleads.json").read_text())
    f = d["fea"]["bl042"]
    g = HF.station_geom("hinge")
    F1g = HINGE_ROW_N / HINGE_ROW_FACTOR
    out = {"hinge_row_n": HINGE_ROW_N, "factor": HINGE_ROW_FACTOR, "f_1g_n": round(F1g, 1)}
    rc_f = f["revC_force_n"]
    out["revC_direction"] = {"force_on_file_n": round(rc_f, 1), "sf_strength": round(f["revC_sf"] * rc_f / HINGE_ROW_N, 2),
                             "sf_fatigue": round(f["revC_fatigue"] * (rc_f / 3.0) / F1g, 2),
                             "sf_creep": round(f["revC_creep"] * (rc_f / 3.0) / F1g, 2)}
    sw = f["sim_worst"]
    out["sim_direction"] = {"run": sw["run"], "f1g_on_file_n": round(sw["f1g_n"], 1),
                            "sf_strength": round(sw["strength"] * sw["f1g_n"] / F1g, 2),
                            "sf_fatigue": round(sw["fatigue"] * sw["f1g_n"] / F1g, 2),
                            "sf_creep": round(sw["creep"] * sw["f1g_n"] / F1g, 2)}
    pin = HF.pin_bending(HINGE_ROW_N, g.throat, g.cheek, g.pin_d, HINGE_ROW_FACTOR)
    out["pin_7075_5mm"] = {k: round(v, 2) for k, v in pin.items()}
    out["previous_basis"] = {"revC_n": round(rc_f, 1), "sim_x3_n": round(3.0 * sw["f1g_n"], 1)}
    return out


def compute(log=print) -> dict:
    out = {"hinge_one_number": hinge_one_number(), "tl1": tl1_recheck()}
    if log:
        log(json.dumps(out["hinge_one_number"], indent=1))
        log(json.dumps({k: v for k, v in out["tl1"].items() if k != "rows"}, indent=1))
    return out
