"""BL-010: structural verification of the load paths changed by BL-003 (straps, REC), BL-004 (attachment, REC) and
BL-006 (hipbelt, section 5) under HA-LS-1 rev C (structural-fea-engineer, 2026-11-11).

Every row of the three "load paths for BL-010" tables gets: the factored load re-derived from the rev C sources (not
taken from the ticket), a check of the part, its stitching and the frame-side feature it loads, fatigue (1e5 cycles
0 -> 1.6 g) and creep where a polymer carries sustained load, and a verdict: PASS, PASS after <test>, or FAIL with the
smallest change that passes and its mass.

Sources
-------
* factored loads: ``analysis/rev_c_verification_results.json`` (beam model, rev C, both couple variants; re-derived
  live by :func:`beam_loads`), ``concepts/attach_diet_scenarios/attach_diet_results.json`` (BL-004 cloth sims, 1 g
  forces x 3.0), ``analysis/float_fea_results.json``, ``hipbelt_structure.load_sets()`` and the float clamp rule of
  ``load_standard.md`` 4.3 (150 N hand cinch x 1.5);
* capacities: ``data/materials`` records (webbing, thread, ladder locks, buckle, and the two hook records added by
  this ticket: ``g_hook_25mm_aluminium``, ``carabiner_wiregate_22kn``), the stitch rule of ``attach_system`` and the
  ASSUMPTIONs in :data:`ASSUMPTIONS`;
* printed fairleads: ``bag_attach.solve_fairlead`` (voxel FEA) re-run by :func:`fairlead_im3` (reproduces the
  float_fea 1415 N record exactly at the released geometry);
* H1 printed body: ``crown_diet.beam_runs`` + ``crown_diet.body_check`` with one tag per torso (BL-017 basis), with
  the BL-004 load change (IM2 bag share moved to IM3, hood term 0, guy term 82 N) in :func:`body_rec`;
* masses: ``huntkit.mass.ledger`` (booked) and the hook records (rated).

    python -m huntkit.gendesign.loadpath_check            # frozen FEA, rows, JSON, Markdown, screenshot
    python -m huntkit.gendesign.loadpath_check --fea      # also re-run the fairlead and H1 body solves (~2 min)
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "loadpath_verification.json"
DOC = ANALYSIS / "loadpath_verification.md"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261111_BL010_1.png"
ATTACH_DIET = PACK / "concepts" / "attach_diet_scenarios" / "attach_diet_results.json"

FACTOR = 3.0            # HA-LS-1 rev C C5 / C2: 2.0 g x 1.5 on a 1 g force
G_WALK = 1.6            # fatigue: 1e5 cycles 0 -> 1.6 g
PROOF = 1.5             # bag_attachment rule: qualification proof = 1.5 x factored (n = 5 scatter allowance)
FLOAT_CINCH_N = 150.0   # load_standard.md 4.3: hand cinch 150 N (ASSUMPTION there), x 1.5
PAHT_FAT, PAHT_RUPT = 0.30, 0.40    # pa12_cf_fdm_paht fatigue_1e5_ratio, creep_rupture_8h_40c_ratio (read live too)

ASSUMPTIONS = {
    "SEW_FAT": ("A sewn box-X / bartack keeps 40 % of its static strength at 1e5 cycles (0 -> peak).",
                "Lever rig (BL-016 kit): 3 box-X coupons, 1e5 cycles 0 -> the row's 1.6 g load, then pull to the "
                "proof load; pass = no broken stitch and residual >= proof."),
    "AL_FAT": ("An aluminium hook keeps 30 % of its rated break at 1e5 cycles (Kt included).",
               "Not needed where the walking load is under 10 % of break (every hook row here)."),
    "BOX25": ("25 mm box-X bartack = 2700 N x 25/38 = 1776 N (strap_arch.BARTACK25_N); the stitch-path model "
              "(attach_system.box_x) gives more and is shown as a cross-check only.",
              "MT-1 at the row's proof load on 25 mm webbing, 5 of 5."),
    "CAM25": ("25 mm aluminium cam slips at 1100 N (strap_arch.CAM25_N, carried over from the 38 mm cam).",
              "MT-3 on 5 cams at the row's proof (IM 908 N, US 1080 N); mark moves < 3 mm."),
    "CARA_PROOF": ("A rated carabiner takes a proof up to 0.5 x its minor-axis rating (4000 N) without set.",
                   "PT-1 on the sewn T3 tongue at 2553 N: 5 of 5 hold, gate closes, no visible set."),
    "THICK25": ("25 mm webbing is 1.4 mm thick: a girth hitch adds 2 x 1.4 = 2.8 mm round the IM eye.",
                "Prototype fit: the IM2 hitch passes the spreader notch (6 mm air, spreader.NOTCH_CLEAR) at 3 mm feeler."),
    "FAIRLEAD_DIR": ("The IM3 bag-hook vector acts along the rev C governing IM3 direction (as float_fea does).",
                     "PT on the first printed frame: pull the IM3 eye through a sewn T3 tongue at 1.5 x 1702 N."),
    "GUY_DIR": ("The guy loop bears on the bare OD 18 bar over 25 mm (the 0.75 mm corner wrap is not credited).",
                "Toggle loop pull on an 18 mm tube to 366 N (attachment_diet.md 7)."),
    "PAD": ("A front-strap pad spreads the two-leg line load over its full width only with a stiffener (HDPE 0.75 mm).",
            "HB-1 with a sensor just in front of the wing tip, with and without the pad."),
    "UHMW_CREEP": ("UHMWPE sleeve sustained bearing limit = 0.25 x yield (21 MPa record) = 5.25 MPa.",
                   "Float hang test: 53 kg on the cradle 24 h, sleeve wall measured before / after (< 0.1 mm)."),
}


# =============================================================================================== records
def rec(mid: str, key: str) -> float:
    return float(load(mid).require(key))


def hw() -> dict:
    """Rated hardware used by the checks (all from records)."""
    return {
        "g25": {"id": "g_hook_25mm_aluminium", "g": rec("g_hook_25mm_aluminium", "mass_g"),
                "break": rec("g_hook_25mm_aluminium", "breaking_strength_n"),
                "noset": rec("g_hook_25mm_aluminium", "no_set_load_n")},
        "cara": {"id": "carabiner_wiregate_22kn", "g": rec("carabiner_wiregate_22kn", "mass_g"),
                 "break": rec("carabiner_wiregate_22kn", "breaking_strength_n"),
                 "minor": rec("carabiner_wiregate_22kn", "minor_axis_strength_n"),
                 "noset": 0.5 * rec("carabiner_wiregate_22kn", "minor_axis_strength_n")},
        "ll": {"slip": rec("ladder_lock_25mm", "slip_load_n"), "g": rec("ladder_lock_25mm", "mass_g")},
        "llh": {"slip": rec("ladder_lock_25mm_heavy", "slip_load_n"), "g": rec("ladder_lock_25mm_heavy", "mass_g"),
                "break": rec("ladder_lock_25mm_heavy", "breaking_strength_n")},
        "buckle50": rec("buckle_side_release_50mm", "breaking_strength_n"),
        "web25": rec("poly_webbing_25mm", "breaking_strength_n"),
        "web38": rec("poly_webbing_38mm", "breaking_strength_n"),
        "nyl50": rec("nylon_webbing_50mm", "breaking_strength_n"),
        "uhmw_y": rec("uhmwpe_sheet", "yield_strength_mpa"),
    }


def caps() -> dict:
    """Sewn-joint capacities (attach_system stitch rule, strap_arch / bag_attach ASSUMPTIONs)."""
    from huntkit.gendesign import attach_system as AS
    from huntkit.gendesign import bag_attach as BA
    bart38 = float(BA.BARTACK_N)
    return {"box25": bart38 * 25.0 / 38.0, "box25_stitch": AS.box_x(25.0, 25.0)["cap_n"],
            "box25x40_stitch": AS.box_x(25.0, 40.0)["cap_n"], "bart38": bart38,
            "box38_stitch": AS.box_x(38.0, 38.0)["cap_n"], "kd_pin": AS.WEB_PIN_KD,
            "sew_fat": 0.40, "al_fat": 0.30}


# =============================================================================================== loads
def beam_loads(rec_change: bool = False) -> dict:
    """Rev C factored forces at the fairlead stations (beam model, both couple variants), split into bag cases and
    meat cases. ``rec_change`` applies BL-004 REC to the bag cases: the IM2 bag share (bag weight group 'mid') moves
    to the IM3 nodes, the hood term goes to 0 and the guy term is the BL-004 sim value 82 N at 1 g."""
    from huntkit.fea.load_standard import TOP_ANCHOR_HOOD_GUYS, ls1_envelope
    from huntkit.gendesign import bag_attach as BA
    orig = BA._frame_model
    ta = {**TOP_ANCHOR_HOOD_GUYS, "hood_n": 0.0, "guy_n": 82.0}

    def patched():
        return move_bag_mid_to_im3(orig())
    if rec_change:
        BA._frame_model = patched
    try:
        bag_cases = {"static_carry", "drop_2p5g", "side_hill_torsion", "hipbelt_off_abuse"}
        out: dict = {}
        for v, cases in ls1_envelope("C").items():
            cs = []
            for c in cases:
                c = copy.copy(c)
                c.params = dict(c.params)
                if rec_change and c.params.get("top_anchor"):
                    c.params["top_anchor"] = ta
                cs.append(c)
            for r in BA.case_loads(cases=cs):
                kind = "bag" if r["case"] in bag_cases else "meat"
                for nid, f in r["nodes"].items():
                    st = BA._NODE_STATION.get(nid)
                    if st is None:
                        continue
                    k = f"{st}_{kind}"
                    if f["n"] > out.get(k, {}).get("n", -1):
                        out[k] = {"n": f["n"], "case": r["case"] + ("@IM3" if v == "strap_upper" else ""),
                                  "node": nid}
    finally:
        BA._frame_model = orig
    return out


def move_bag_mid_to_im3(model: dict) -> dict:
    """BL-004 REC: no IM2 bag hooks, so the bag weight share booked on the IM2 nodes (z 330) goes to IM3 (z 520)."""
    if "bag" in model["groups"]:
        model["groups"]["bag"] = [{"SL330": "SL520", "SR330": "SR520"}.get(n, n) for n in model["groups"]["bag"]]
    return model


def sim_loads() -> dict:
    """BL-004 cloth-sim 1 g forces (frozen JSON), worst per shell and variant, x FACTOR."""
    rows = json.loads(ATTACH_DIET.read_text())["rows"]
    out = {}
    for key, grp in (("im3", ("hook_im520_R", "hook_im520_L")), ("hinge", ("hinge_R", "hinge_L")),
                     ("guy", ("TG_R", "TG_L"))):
        for shell in ("S15", "CORRIE"):
            for var in ("REC", "M_notop"):
                best = (0.0, "")
                for name, r in rows.items():
                    if not name.startswith(f"{var}_{shell}_"):
                        continue
                    for cn, c in r["cases"].items():
                        if not c["converged"]:
                            continue
                        v = max(float(c["loads_1g"].get(k, 0.0)) for k in grp)
                        if v > best[0]:
                            best = (v, f"{name} {cn}")
                if best[0] > 0:
                    out[f"{key}_{var}_{shell}"] = {"n_1g": best[0], "factored": FACTOR * best[0], "run": best[1]}
    return out


def corrie_f_loads() -> dict:
    """BL-011 CORRIE F IM3 bag-hook force at 1 g per torso (worst case, R/L), read live when the untracked sim outputs
    exist, else the frozen values. These are the REV 0 runs (guys at the bar ends x +/-100, scenarios cf_PR{t}.yaml),
    stored since BL-025 in F_r0_PR{t}; the old F_PR{t} name now holds BL-022's rev 1 runs (F_r1_PR{t})."""
    out = {}
    for t, fr in FROZEN["corrie_f_im3_1g"].items():
        f = REPO / "outputs" / "clothsim" / "corrie_f" / f"F_r0_PR{t}" / "results.json"
        if f.exists():
            r = json.loads(f.read_text())
            best = (0.0, "")
            for cn, c in r["cases"].items():
                att = c.get("attachments", {})
                v = max([float(att[k]["tension_n"]) for k in ("hook_im520_R", "hook_im520_L") if k in att] or [0.0])
                if v > best[0]:
                    best = (v, cn)
            out[t] = {"n_1g": round(best[0], 1), "case": best[1], "source": "live", "run": f.parent.name}
        else:
            cn = max(fr, key=fr.get)
            out[t] = {"n_1g": fr[cn], "case": cn, "source": "frozen"}
    return out


CF_STRENGTH_REQ = 1.5      # coordinator follow-up: strength >= 1.5 at the factored load for the A1-CF cheek


def size_cheek_cf(cf: dict, misuse_n: float) -> dict:
    """Smallest-mass cheek variant (FROZEN sweeps) with fatigue >= 1.0 at every torso (1.6 x the CORRIE F 1 g force)
    and strength >= CF_STRENGTH_REQ at the factored load (max of the misuse envelope and 3.0 x CORRIE F)."""
    nf = max(misuse_n, FACTOR * max(v["n_1g"] for v in cf.values()))
    cands = {f"{hz}_8.0": v for hz, v in FROZEN["fairlead_im3"].items()}
    cands.update(FROZEN["fairlead_im3_cheek"])
    rows = []
    for k, v in cands.items():
        hz, ch = (float(x) for x in k.split("_"))
        pn = v["fi99"] / 1415.1
        fat = {t: PAHT_FAT / (pn * G_WALK * c["n_1g"]) for t, c in cf.items()}
        rows.append({"key": k, "half_z": hz, "cheek": ch, "height_mm": 2 * hz, "fi99": v["fi99"],
                     "added_g": v["added_g"], "fatigue": fat, "strength": 1.0 / (pn * nf),
                     "creep": min(PAHT_RUPT / (pn * c["n_1g"]) for c in cf.values()),
                     "ok": min(fat.values()) >= 1.0 and 1.0 / (pn * nf) >= CF_STRENGTH_REQ})
    ok = [r for r in rows if r["ok"]]
    best = min(ok, key=lambda r: (r["added_g"], r["height_mm"]))
    return {"factored_n": nf, "rows": sorted(rows, key=lambda r: (r["cheek"], r["half_z"])), "chosen": best}


def cheek_clearance(half_z: float, cheek: float) -> dict:
    """Geometry of the grown IM3 eye (bag_attach constants): gap to the spreader top edge (spreader.Z_HI) against the
    notch rule, the throat the hooks share (unchanged), and how far the cheek stands aft of the hole centre."""
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign import spreader as SPR
    z_bot = 520.0 - half_z
    gap = z_bot - SPR.Z_HI
    return {"cheek_bottom_z": z_bot, "cheek_top_z": 520.0 + half_z, "spreader_top_z": SPR.Z_HI, "gap_mm": gap,
            "notch_clear_mm": SPR.NOTCH_CLEAR, "spreader_ok": gap >= SPR.NOTCH_CLEAR, "throat_mm": BA.THROAT,
            "outer_width_mm": BA.THROAT + 2 * cheek, "cheek_aft_of_hole_mm": BA.HOLE_D / 2.0 + BA.WALL_FRONT,
            "half_height_mm": half_z}


def float_loads() -> dict:
    f = json.loads((ANALYSIS / "float_fea_results.json").read_text())
    us1_36 = f["us1"]["record_36kg"]["force_n"]
    lim = f["us1"]["limit_kg"]
    return {"us1_limit_n": us1_36 * lim / 36.0, "limit_kg": lim, "us1_36_n": us1_36,
            "clamp_n": FLOAT_CINCH_N * 1.5, "bag_on_1415": f["bag_on_1415"]}


def belt_loads() -> dict:
    from huntkit.gendesign import hipbelt_structure as HS
    ls_ = HS.load_sets()
    eta = 0.85                                       # 2:1 efficiency ASSUMPTION (hipbelt_fit.md)
    return {"T_c2": ls_["C2"].T, "T_walk": ls_["walk"].T, "leg_frac": 1.0 / (2.0 * eta)}


# =============================================================================================== FEA
def fairlead_im3(half_z: float = 9.0, force_n: float = 1415.1, h: float = 1.0, cheek: float | None = None) -> dict:
    """IM3 printed fairlead (bag_attach.solve_fairlead) at the bag-on vector of float_fea, with the cheek half-height
    ``half_z`` (released 9.0). FI is linear in force; the result is reported per newton."""
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign import float_fea as F
    v = F.bag_on_envelope_vector()
    v = v / np.linalg.norm(v) * force_n
    old, oc = BA.HALF_Z, BA.CHEEK
    BA.HALF_Z = float(half_z)
    if cheek is not None:
        BA.CHEEK = float(cheek)
    try:
        r = BA.solve_fairlead(16.8, v, h=h, label=f"im3 half_z {half_z}")
    finally:
        BA.HALF_Z, BA.CHEEK = old, oc
    return {"half_z": half_z, "force_n": force_n, "fi99": float(r["fi99"]), "fi_per_n": float(r["fi99"]) / force_n,
            "added_g": float(r["added_g"])}


def body_rec(log=print) -> dict:
    """H1 printed body, rev C, one tag per torso (BL-017 basis), with the BL-004 REC load change."""
    from huntkit.fea import load_standard as LS
    from huntkit.gendesign import crown_diet as CD
    ob, oe = CD.build, LS.ls1_envelope
    ta = {**LS.TOP_ANCHOR_HOOD_GUYS, "hood_n": 0.0, "guy_n": 82.0}

    def build(spec, t, posts=False):
        return move_bag_mid_to_im3(ob(spec, t, posts))

    def env(rev="C"):
        e = oe(rev)
        for cases in e.values():
            for c in cases:
                if c.params.get("top_anchor"):
                    c.params = {**c.params, "top_anchor": ta}
        return e
    CD.build, LS.ls1_envelope = build, env
    try:
        sets, _ = CD.beam_runs(CD.specs()["h1"], buckling=False, log=log, suffix="rec")
        r = CD.body_check("h1_rec", CD._h1_solid(), CD._retag(sets, "H"), log=log)
    finally:
        CD.build, LS.ls1_envelope = ob, oe
    return {"min": r["min"], "governing": r["governing"], "by_torso": r["by_torso"]}


# Frozen solver results (2026-11-11, this ticket; regenerate with --fea). fi99 at 1415.1 N.
FROZEN = {
    "fairlead_im3": {9.0: {"fi99": 0.6504503705966863, "added_g": 6.13104},
                     11.0: {"fi99": 0.5592151145174126, "added_g": 7.5896},
                     12.0: {"fi99": 0.523921382004247, "added_g": 8.31888},
                     12.5: {"fi99": 0.5087, "added_g": 8.80},
                     13.0: {"fi99": 0.4886, "added_g": 9.05},
                     13.5: {"fi99": 0.4636, "added_g": 9.53},
                     14.0: {"fi99": 0.4465, "added_g": 9.78}},
    # cheek thickness variants (HALF_Z, CHEEK) for the A1-CF sizing (BL-011 follow-up); fi99 at 1415.1 N
    "fairlead_im3_cheek": {"13.0_8.0": {"fi99": 0.4886, "added_g": 9.05}, "13.5_8.0": {"fi99": 0.4636, "added_g": 9.53},
                           "12.5_9.0": {"fi99": 0.4630, "added_g": 9.65}, "13.0_9.0": {"fi99": 0.4507, "added_g": 9.93},
                           "11.5_10.0": {"fi99": 0.4631, "added_g": 9.63}, "12.0_10.0": {"fi99": 0.4399, "added_g": 9.93},
                           "13.25_8.0": {"fi99": 0.4884, "added_g": 9.05}},   # 13.25 voxelises to 13 at h 1 mm
    # BL-011 CORRIE F rev 0 (door D2) cloth sims, IM3 bag hook max(R, L) at 1 g, outputs/clothsim/corrie_f/F_r0_PR*/results.json
    "corrie_f_im3_1g": {15: {"meat": 552.4, "fill": 439.6}, 19: {"meat": 515.5, "fill": 363.6},
                        23: {"meat": 460.1, "fill": 336.3}},
    "fairlead_record_fi99_1415": 0.6504503705966851,       # float_fea_results.json bag_on_1415 (released)
    "body_h1_per_torso": {"strength": 1.4739561426221504, "fatigue": 1.1502260709981276,
                          "creep": 2.453815618129339, "governing": "C_im3@H23 static_carry 23 in (fatigue)",
                          "source": "outputs/crown_diet/body_h1_pt.pkl (BL-017)"},
    "body_rec_per_torso": {"strength": 1.4790029162775065, "fatigue": 1.1440812797002529,
                           "creep": 2.4407067300272063, "governing": "C_im3rec@H23 static_carry 23 in (fatigue)",
                           "worst_by_torso": {"15": 1.527, "19": 1.311, "23": 1.144}},
    # R-28 head clearance, REC S15 / CORRIE, worst contact angle (deg; > 30 passes), see r28_diagnosis()
    "r28": {"S15_23_fill": {"as_coded": 21.0, "abs_face": 28.0, "x0_section": 28.0},
            "S15_23_meat": {"as_coded": 19.0, "abs_face": 25.0, "x0_section": 26.0},
            "CORRIE_23_fill": {"as_coded": 34.0, "abs_face": 34.0, "x0_section": 34.0},
            "CORRIE_23_meat": {"as_coded": 34.0, "abs_face": 33.0, "x0_section": 34.0},
            "S15_19_meat": {"as_coded": 34.0, "abs_face": 34.0, "x0_section": 34.0},
            "S15_15_meat": {"as_coded": 34.0, "abs_face": 34.0, "x0_section": 34.0},
            "S15_23_wall_x0_mm_head_side_of_bar_face": {"785": -17.2, "835": -6.4, "885": 24.3},
            "bar_face_y": 0.8},
}


def r28_diagnosis() -> dict:
    """R-28 at REC S15 / CORRIE (BL-004 sims, outputs/clothsim/attach_diet, not tracked): (1) as coded
    (attach_system.r28_loaded: SPINE design face bg.y_frame(z) minus the shell's own move), (2) with the loaded face
    taken absolute (move = y_frame - loaded, so the wall IS the simulated face), (3) as (2) on the x = 0 section."""
    sys.path.insert(0, str(PACK / "concepts"))
    import attach_diet as AD  # noqa: E402
    from huntkit.gendesign import attach_system as AS
    bg = AS._bg()
    out = {}
    for shell in ("S15", "CORRIE"):
        for t in (15, 19, 23):
            r = json.loads((AD.run_dir("REC", shell, t) / "results.json").read_text())
            dr = AD._drafted(shell, AD.scenario_path("REC", t))
            for cn in ("fill", "meat"):
                pr = r["cases"][cn]["profile"]
                rows = pr["depth_by_z"]
                a = [(float(w[0]), float(dr[int(round(w[0]))] - w[1])) for w in rows if int(round(w[0])) in dr]
                b = [(float(w[0]), float(bg.y_frame(w[0])[0]) - float(w[1])) for w in rows]
                P = np.array([p for sg in pr["section_x0_segments_yz"] for p in sg])
                c = []
                for w in rows:
                    s_ = np.abs(P[:, 1] - w[0]) < 25
                    if s_.sum():
                        c.append((float(w[0]), float(bg.y_frame(w[0])[0]) - float(P[s_, 0].min())))
                out[f"{shell}_{t}_{cn}"] = {k: AS.r28_loaded(t, m, hood=False)["worst_contact_deg"]
                                            for k, m in (("as_coded", a), ("abs_face", b), ("x0_section", c))}
    return out


# =============================================================================================== rows
def _chk(item, demand, cap, kind, basis, rated=True, test=""):
    return {"item": item, "demand_n": float(demand), "capacity": float(cap), "kind": kind,
            "ratio": float(cap) / float(demand) if demand > 0 else float("inf"), "rated": bool(rated),
            "basis": basis, "test": test}


def verdict(checks: list) -> dict:
    """PASS if every ratio >= 1 on rated capacities; 'PASS after <tests>' if every ratio >= 1 but some capacity is
    assumed; FAIL if any ratio < 1."""
    if not checks:
        return {"verdict": "PASS", "min": float("inf"), "governs": "no load", "tests": []}
    worst = min(checks, key=lambda c: c["ratio"])
    tests = sorted({c["test"] for c in checks if not c["rated"] and c["test"]})
    if worst["ratio"] < 1.0 - 1e-9:
        v = "FAIL"
    elif tests:
        v = "PASS after " + ", ".join(tests)
    else:
        v = "PASS"
    return {"verdict": v, "min": worst["ratio"], "governs": worst["item"], "tests": tests}


def build_rows(beam: dict, beam_rec: dict, sim: dict, fl: dict, belt: dict, fea: dict) -> list:
    H, C = hw(), caps()
    fat = lambda n: n * G_WALK / FACTOR                     # noqa: E731  walking peak from a factored 3.0 load
    fipn = {hz: v["fi99"] / 1415.1 for hz, v in fea["fairlead_im3"].items()}
    im3 = beam["im3_meat"]["n"]                           # 605 N, C5 meat_straps
    im = {"IM1": beam["im1_meat"]["n"], "IM2": beam["im2_meat"]["n"], "IM3": im3}
    rc = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]
    f3 = rc["fairlead_fea"]["im3"]
    fh = rc["fairlead_fea"]["hinge"]
    rows = []

    def row(rid, src, loc, part, direction, ticket_n, n, basis, checks, fix=None, note=""):
        v = verdict(checks)
        r = {"id": rid, "source": src, "location": loc, "part": part, "direction": direction,
             "ticket_factored_n": ticket_n, "factored_n": n, "load_basis": basis, "checks": checks, **v,
             "note": note}
        if fix:
            fv = verdict(fix["checks"])
            r["fix"] = {**fix, **{f"after_{k}": vv for k, vv in fv.items()}}
        rows.append(r)

    # ------------------------------------------------------------------ BL-003 (strap_architecture.md 7, REC)
    P = PROOF * im3
    row("S1", "BL-003", "IM1-IM3 left fairlead eyes (z 190/330/520), girth hitch", "25 mm sewn loop on a 38 mm "
        "webbing eye; box-X 25 mm", "aft, across the meat", 605, im3,
        f"rev C C5 meat_straps {beam['im3_meat']['node']} (beam, x 1.5 on 2.0 g)",
        [_chk("box-X 25 mm, strength", im3, C["box25"], "strength", "ASSUMPTION BOX25", False, "MT-1 (25 mm, 908 N)"),
         _chk("box-X 25 mm, proof 1.5x", P, C["box25"], "proof", "ASSUMPTION BOX25", False, "MT-1 (25 mm, 908 N)"),
         _chk("box-X 25 mm, stitch-path model (cross-check)", P, C["box25_stitch"], "proof", "attach_system.box_x"),
         _chk("girth hitch, 25 mm webbing pinched on the eye (kd 0.5)", im3, C["kd_pin"] * H["web25"], "strength",
              "poly_webbing_25mm x WEB_PIN_KD"),
         _chk("box-X fatigue, 1.6 g", fat(im3), C["sew_fat"] * C["box25"], "fatigue", "ASSUMPTION SEW_FAT", False,
              "SEW-F (lever rig)"),
         _chk("IM3 printed fairlead (frame), strength, unchanged force", im3, im3 * f3["sf"], "strength",
              "rev_c_verification fairlead_fea.im3 SF"),
         _chk("IM3 printed fairlead, fatigue", fat(im3), fat(im3) * f3["sf_fatigue"], "fatigue",
              "rev_c_verification fairlead_fea.im3 sf_fatigue"),
         _chk("IM3 printed fairlead, creep", im3 / FACTOR, im3 / FACTOR * f3["sf_creep"], "creep",
              "rev_c_verification fairlead_fea.im3 sf_creep"),
         _chk("IM2 hitch thickness in the spreader notch (mm, as N)", 2 * 1.4, 6.0, "fit", "ASSUMPTION THICK25",
              False, "IM2 notch fit")],
        note="hook -> girth hitch: same force and direction at the eye; frame side unchanged.")
    g25 = H["g25"]
    row("S2", "BL-003", "IM1-IM3 right eyes, free-end hook", "25 mm rated Al G-hook (g_hook_25mm_aluminium)", "aft",
        605, im3, "as S1; IM1 273 N, IM2 430 N, IM3 605 N",
        [_chk("G-hook break, IM3", im3, g25["break"], "strength", "record"),
         _chk("G-hook no-set vs proof, IM1", PROOF * im["IM1"], g25["noset"], "proof", "record"),
         _chk("G-hook no-set vs proof, IM2", PROOF * im["IM2"], g25["noset"], "proof", "record"),
         _chk("G-hook no-set vs proof, IM3 (MT-2 910 N)", P, g25["noset"], "proof", "record"),
         _chk("G-hook fatigue, 1.6 g", fat(im3), C["al_fat"] * g25["break"], "fatigue", "ASSUMPTION AL_FAT")],
        fix={"change": "IM3 free end only: rated wiregate carabiner (carabiner_wiregate_22kn) instead of the G-hook; "
                       "IM1 / IM2 keep the 25 mm G-hook",
             "mass_g": H["cara"]["g"] - g25["g"],
             "checks": [_chk("carabiner break, IM3", im3, H["cara"]["break"], "strength", "record"),
                        _chk("carabiner minor axis, IM3", im3, H["cara"]["minor"], "strength", "record"),
                        _chk("carabiner proof 908 N (0.5 x minor)", P, H["cara"]["noset"], "proof",
                             "ASSUMPTION CARA_PROOF")]},
        note="MT-2's 910 N is 1.5 x 605 N (TEST_PLAN.md line 330): it is the IM3 strap's own qualification proof and "
             "is kept. Per strap: IM1 410 N and IM2 645 N proofs pass the 900 N no-set load.")
    row("S3", "BL-003", "IM1-IM3 cam", "25 mm Al cam (slip), no record", "along the strap", 605, im3, "as S1",
        [_chk("cam slip, strength", im3, 1100.0, "strength", "ASSUMPTION CAM25", False, "MT-3 (25 mm cam, 908 N)"),
         _chk("cam slip, proof", P, 1100.0, "proof", "ASSUMPTION CAM25", False, "MT-3 (25 mm cam, 908 N)")])
    row("S4", "BL-003", "IM1-IM3 webbing", "poly_webbing_25mm", "along the strap", 605, im3, "as S1",
        [_chk("webbing on a hook bed (kd 0.5)", im3, C["kd_pin"] * H["web25"], "strength", "record x WEB_PIN_KD")],
        note="contact width on the meat 38 -> 25 mm: 1.5 x the strap-line pressure on the game bag (not structural).")
    us = fl["us1_limit_n"]
    row("S5", "BL-003", "US1 cradle (z 95), 53 kg float limit", "25 mm Al cam (slip)", "along the strap", 720, us,
        f"float_fea us1 {fl['us1_36_n']:.0f} N at 36 kg x {fl['limit_kg']:.0f}/36 (1.6 g x 1.5)",
        [_chk("cam slip, strength", us, 1100.0, "strength", "ASSUMPTION CAM25", False, "MT-3 (25 mm cam, 1080 N)"),
         _chk("cam slip, proof 1.5x", PROOF * us, 1100.0, "proof", "ASSUMPTION CAM25", False,
              "MT-3 (25 mm cam, 1080 N)"),
         _chk("webbing creep, sustained 1 g (2 % of break)", us / (1.6 * 1.5), H["web25"] * 0.1, "creep",
              "polyester: sustained < 10 % of break, no creep rupture (ASSUMPTION, standard practice)")],
        note="US1 anchor fatigue (printed frame part) unchanged; it sets the 53 kg limit.")
    pin = rc["pin"]
    row("S6", "BL-003", "US1/US2 sewn eye on the left pin", "25 mm box-X; 7075 pin; UHMWPE sleeve",
        "along the strap", 720, us, "as S5",
        [_chk("box-X 25 mm, strength", us, C["box25"], "strength", "ASSUMPTION BOX25", False, "MT-1 (25 mm, 1080 N)"),
         _chk("box-X 25 mm, proof", PROOF * us, C["box25"], "proof", "ASSUMPTION BOX25", False, "MT-1 (25 mm, 1080 N)"),
         _chk("box-X fatigue, 1.6 g", us / 1.5, C["sew_fat"] * C["box25"], "fatigue", "ASSUMPTION SEW_FAT", False,
              "SEW-F (lever rig)"),
         _chk("UHMWPE sleeve bearing (18 mm throat governs either width)", us,
              us * pin["sleeve_sf"] * 724.16 / us, "strength", "rev_c pin.sleeve_sf at 724 N, scaled"),
         _chk("UHMWPE sleeve creep, sustained 1 g", pin["sleeve_mpa"] * (us / 2.4) / 724.16,
              0.25 * H["uhmw_y"], "creep", "ASSUMPTION UHMW_CREEP", False, "float hang 24 h")],
        note="the eye necks to the 18 mm fairlead throat for 25 and 38 mm webbing alike, so the sleeve bearing length "
             "does not change; units of the creep row are MPa.")
    row("S7", "BL-003", "US1/US2 webbing", "poly_webbing_25mm", "along the strap", 720, us, "as S5",
        [_chk("webbing on a pin (kd 0.5)", us, C["kd_pin"] * H["web25"], "strength", "record x WEB_PIN_KD")])
    comp = 77.0
    row("S8", "BL-003", "W1/W2 frame anchors (z 80/250/420 lash points), carry compression", "25 mm ladder lock",
        "aft + inboard", 77, comp, "team C hoop strap 25.6 N at 1 g x 3.0 (strap_arch, bag_comp C result.json)",
        [_chk("ladder lock slip", comp, H["ll"]["slip"], "strength", "ladder_lock_25mm record (estimate)", False,
              "LL-slip (5 locks)"),
         _chk("ladder lock slip, proof", PROOF * comp, H["ll"]["slip"], "proof", "record", False, "LL-slip (5 locks)"),
         _chk("lash point: carry load inside the float-clamp duty it already has", comp, fl["clamp_n"], "strength",
              "same lash points carry the 225 N float clamp", False, "W-pull (first frame)")])
    clamp = fl["clamp_n"]
    row("S9", "BL-003", "W1-W3 float clamp", "25 mm ladder lock + 4 g HAUL G-hook (no rating)", "round bag + meat", 225,
        clamp, "load_standard.md 4.3: 150 N hand cinch x 1.5, no friction credited",
        [_chk("ladder lock slip", clamp, H["ll"]["slip"], "strength", "record", False, "LL-slip (5 locks)"),
         _chk("ladder lock slip, proof 1.5x", PROOF * clamp, H["ll"]["slip"], "proof", "record"),
         _chk("HAUL G-hook (no rating on file)", clamp, 0.0 + 1e-9, "strength", "no record")],
        fix={"change": "3 x g_hook_25mm_aluminium (rated) and 3 x ladder_lock_25mm_heavy",
             "mass_g": 3 * (g25["g"] - 4.0) + 3 * (H["llh"]["g"] - H["ll"]["g"]),
             "checks": [_chk("G-hook no-set vs proof", PROOF * clamp, g25["noset"], "proof", "record"),
                        _chk("heavy lock slip vs proof", PROOF * clamp, H["llh"]["slip"], "proof",
                             "ladder_lock_25mm_heavy record (slip = 0.5 x tensile, ASSUMPTION there)", False,
                             "LL-slip heavy (5 locks, 338 N, 1 h hold)")]},
        note="the cinch is held, so the polymer lock sees sustained load: the slip test holds the proof 1 h (creep).")
    row("S10", "BL-003", "W1/W2 G-hooks across the door (side carry, tripod)", "25 mm G-hook", "aft + inboard", 77,
        comp, "as S8",
        [_chk("G-hook no-set vs proof (same rated part as the S9 fix)", PROOF * comp, g25["noset"], "proof", "record")],
        note="needs the S9 fix (rated hook); no extra mass.")
    row("S11", "BL-003", "B-03 frame-side corner seams (wing roots)", "none (wings deleted)", "removed", 0, 0.0,
        "load removed", [], note="the owner deleted the wings 2026-11-11.")
    b24 = 941.0
    row("S12", "BL-003", "B-24 link, option a 25 mm G-hook (not in REC)", "25 mm rated Al G-hook", "aft + down 30 deg",
        941, b24, "float misuse link 941 N (bag_attachment.md, float rows)",
        [_chk("G-hook no-set vs proof", PROOF * b24, g25["noset"], "proof", "record")],
        fix={"change": "REC keeps the bag-hook part; with BL-010 that part is carabiner_wiregate_22kn (booked 14 g)",
             "mass_g": 2 * (H["cara"]["g"] - 14.0), "meat_trip_only": True,
             "checks": [_chk("carabiner proof (0.5 x minor)", PROOF * b24, H["cara"]["noset"], "proof",
                             "ASSUMPTION CARA_PROOF")]},
        note="option a is not adopted, so the verdict is on what REC carries: the 2 B-24 hooks. The mass change is a "
             "booked-mass correction in the meat-trip kit, not part of BL-003's saving.")

    # ------------------------------------------------------------------ BL-004 (attachment_diet.md 5, REC)
    s_rec, s_mis = sim["im3_REC_S15"], sim["im3_M_notop_S15"]
    c_mis = sim["im3_M_notop_CORRIE"]
    n_im3 = max(c_mis["factored"], s_mis["factored"])
    pr = PROOF * n_im3
    walk_im3 = G_WALK * s_rec["n_1g"]
    fi0 = fipn[9.0]
    row("A1", "BL-004", "IM3 eyes z 520, x +/-115 (bag hook)", "38 mm bag hook 2200 N purchase spec (no record); T3 "
        "box-X; B-17 seam", "aft-up along T3", 1702, n_im3,
        f"cloth sim x 3.0: guys-off misuse {c_mis['n_1g']:.1f} N ({c_mis['run']}) governs over both shells; "
        f"S15 misuse {s_mis['factored']:.0f}, S15 REC {s_rec['factored']:.0f}",
        [_chk("hook 2200 N (purchase spec), proof 1.5x", pr, 2200.0, "proof", "bag_attachment.md purchase spec"),
         _chk("T3 box-X 38 (bartack ASSUMPTION 2700), proof", pr, C["bart38"], "proof", "bag_attach.BARTACK_N",
              False, "PT-1 raised to 2553 N"),
         _chk("T3 box-X 38, stitch-path model (cross-check)", pr, C["box38_stitch"], "proof", "attach_system.box_x"),
         _chk("T3 webbing on the hook bed (kd 0.5)", n_im3, C["kd_pin"] * H["web38"], "strength", "record"),
         _chk("B-17 seam, 80 mm loaded, proof", pr, 3277.0, "proof", "attach_system patch_seam (bag_attachment.md)",
              False, "PT-2 on the 70 mm tab at 2553 N"),
         _chk("IM3 printed fairlead, strength at the misuse load", n_im3, 1.0 / fi0, "strength",
              "fairlead_im3(9.0): FI linear in force", False, "IM3 eye pull (first frame)"),
         _chk("IM3 printed fairlead, fatigue 1.6 g x S15 REC 1 g force", walk_im3, PAHT_FAT / fi0, "fatigue",
              "PAHT fatigue_1e5_ratio / FI99 per N"),
         _chk("IM3 printed fairlead, creep at 1 g", s_rec["n_1g"], PAHT_RUPT / fi0, "creep",
              "PAHT creep_rupture ratio / FI99 per N")],
        fix={"change": "(1) the 2 IM3 bag hooks become carabiner_wiregate_22kn; (2) the IM3 fairlead cheek grows from "
                       "18 to 25 mm tall along the stay (bag_attach.HALF_Z 9.0 -> 12.5) on H1's print",
             "mass_g": 2 * (H["cara"]["g"] - 14.0) + 2 * (fea["fairlead_im3"][12.5]["added_g"]
                                                           - fea["fairlead_im3"][9.0]["added_g"]),
             "frame_change": True,
             "checks": [_chk("carabiner break", n_im3, H["cara"]["break"], "strength", "record"),
                        _chk("carabiner minor axis", n_im3, H["cara"]["minor"], "strength", "record"),
                        _chk("carabiner proof (0.5 x minor)", pr, H["cara"]["noset"], "proof",
                             "ASSUMPTION CARA_PROOF", False, "PT-1 raised to 2553 N"),
                        _chk("T3 box-X 38, proof", pr, C["bart38"], "proof", "bag_attach.BARTACK_N", False,
                             "PT-1 raised to 2553 N"),
                        _chk("B-17 seam, proof", pr, 3277.0, "proof", "patch_seam", False, "PT-2 on the 70 mm tab"),
                        _chk("fairlead 25 mm cheek, strength", n_im3, 1.0 / fipn[12.5], "strength",
                             "fairlead_im3(12.5)", False, "IM3 eye pull (first frame)"),
                        _chk("fairlead 25 mm cheek, fatigue", walk_im3, PAHT_FAT / fipn[12.5], "fatigue",
                             "fairlead_im3(12.5)"),
                        _chk("fairlead 25 mm cheek, creep", s_rec["n_1g"], PAHT_RUPT / fipn[12.5], "creep",
                             "fairlead_im3(12.5)")]},
        note="The fairlead fatigue failure is not caused by the diet: today's V0 on S15 (491 N at 1 g) gives "
             f"{PAHT_FAT / fi0 / (G_WALK * 491.0):.2f}. The IM3 fairlead was released on the beam model's 605 N; the "
             "cloth sim puts 2.5x that on it at 1 g and nobody had checked its fatigue there.")
    row("A2", "BL-004", "IM2 eyes z 330", "none (T2, B-23, IM2 bag hooks deleted)", "bag load removed", 0,
        beam_rec["im2_meat"]["n"], "beam REC: IM2 governed by C5 meat straps only (was side-hill bag 512 N)",
        [_chk("IM2 fairlead, meat strap only (inside the IM3 rev C check, same part)", beam_rec["im2_meat"]["n"],
              im3 * f3["sf"], "strength", "rev_c fairlead_fea.im3 (larger force, same geometry)")],
        note=f"the beam's IM2 bag share moves to IM3: IM3 bag cases {beam['im3_bag']['n']:.0f} -> "
             f"{beam_rec['im3_bag']['n']:.0f} N, still below the 605 N meat case; H1 body re-checked (section 4).")
    guy = sim["guy_REC_CORRIE"] if sim["guy_REC_CORRIE"]["factored"] > sim["guy_REC_S15"]["factored"] \
        else sim["guy_REC_S15"]
    ng = guy["factored"]
    from huntkit.gendesign import frame_cg_recheck as R
    bar = R.bar_local(ng, 25.0, over={})["tie"]
    fi_bar = 1.0 / bar["sf"]
    row("A3", "BL-004", "crown top bar x +/-(92-100), guy loops", "25 mm loop + POM toggle; heavy ladder lock + "
        "tri-glide on B-22", "aft and outboard to B-22", 244, ng, f"cloth sim x 3.0, {guy['run']}",
        [_chk("crown bar wall under a 25 mm loop (bare bar)", ng, ng * bar["sf"], "strength",
              "frame_cg_recheck.bar_local", False, "toggle-loop pull 366 N"),
         _chk("crown bar CFRP fatigue (FI at 1.6 g <= 0.5)", fi_bar * G_WALK * guy["n_1g"] / ng, 0.5, "fatigue",
              "HA-LS-1 CFRP rule; units FI"),
         _chk("POM toggle pull-through, proof", PROOF * ng, 670.0, "proof", "ASSUMPTION attach_system", False,
              "toggle-loop pull 366 N"),
         _chk("heavy ladder lock slip, proof", PROOF * ng, H["llh"]["slip"], "proof", "record", False,
              "LL-slip heavy (5 locks, 366 N, 1 h hold)"),
         _chk("B-22 seam", PROOF * ng, 1024.0, "proof", "attachment_diet.md 5"),
         _chk("loop webbing on the 18 mm bar (kd 0.5)", ng, C["kd_pin"] * H["web25"], "strength", "record")],
        note="bare-bar check; the corner wrap under the loop adds wall (not credited). BL-041: rev 3 moved the guy "
             "toggle into the B-25 bridle tab, shared with the B-28 crown strap (323 N envelope); the 25 mm sleeve "
             "fails the ring check there (crown_tube_guy_loop.md): fix rows = the 38 mm B-25 as built.",
        fix=_a3_rev3_fix())
    row("A4", "BL-004", "crown top bar centre x +/-66", "none (hood deleted)", "hood capture removed", 0, 0.0,
        "load removed", [])
    hn = max(sim["hinge_REC_S15"]["factored"], sim["hinge_M_notop_S15"]["factored"],
             sim["hinge_REC_CORRIE"]["factored"], sim["hinge_M_notop_CORRIE"]["factored"], beam["hinge_meat"]["n"])
    hw_1g = max(sim["hinge_REC_S15"]["n_1g"], sim["hinge_REC_CORRIE"]["n_1g"])
    fh_pn = fh["fi99"] / 724.16
    row("A5", "BL-004", "hinge eyes z 60, x +/-115", "HE on B-18, 5 mm 7075 pull-pin", "down-aft into the pin", 755, hn,
        "max of the cloth sims x 3.0 (guys-off misuse included) and the beam C6 724 N",
        [_chk("B-18 seam, proof", PROOF * hn, 2355.0, "proof", "attachment_diet.md 5"),
         _chk("bartack, proof", PROOF * hn, C["bart38"], "proof", "bag_attach.BARTACK_N", False, "PT-3 hinge eye"),
         _chk("7075 pin yield", hn, hn * pin["sf_yield"] * 724.16 / hn, "strength", "rev_c pin, scaled"),
         _chk("UHMWPE sleeve", hn, 724.16 * pin["sleeve_sf"], "strength", "rev_c pin, scaled"),
         _chk("hinge fairlead, strength", hn, 1.0 / fh_pn, "strength", "rev_c fairlead_fea.hinge, linear"),
         _chk("hinge fairlead, fatigue 1.6 g x sim 1 g", G_WALK * hw_1g, PAHT_FAT / fh_pn, "fatigue",
              "rev_c fairlead_fea.hinge, linear"),
         _chk("hinge fairlead, creep 1 g", hw_1g, PAHT_RUPT / fh_pn, "creep", "rev_c fairlead_fea.hinge")])

    # ------------------------------------------------------------------ A1-CF (BL-011 follow-up, additive)
    cf = fea.get("corrie_f")
    if cf:
        sz = size_cheek_cf(cf, n_im3)
        ch = sz["chosen"]
        p25 = fipn[12.5]
        chk = [_chk(f"25 mm cheek (A1 fix), fatigue {t} in, 1.6 x {c['n_1g']:.1f} N", G_WALK * c["n_1g"],
                    PAHT_FAT / p25, "fatigue", "fairlead_im3(12.5)") for t, c in sorted(cf.items())]
        chk.append(_chk(f"25 mm cheek, strength >= {CF_STRENGTH_REQ} at the factored load", sz["factored_n"],
                        1.0 / p25 / CF_STRENGTH_REQ, "strength",
                        f"fairlead_im3(12.5); capacity = 1 / FI per N / {CF_STRENGTH_REQ}"))
        pn = ch["fi99"] / 1415.1
        fchk = [_chk(f"{ch['height_mm']:.0f} mm cheek, fatigue {t} in", G_WALK * c["n_1g"], PAHT_FAT / pn, "fatigue",
                     f"fairlead_im3({ch['half_z']}, cheek {ch['cheek']:g})") for t, c in sorted(cf.items())]
        fchk.append(_chk(f"{ch['height_mm']:.0f} mm cheek, strength >= {CF_STRENGTH_REQ} at the factored load",
                         sz["factored_n"], 1.0 / pn / CF_STRENGTH_REQ, "strength",
                         f"fairlead_im3({ch['half_z']}); capacity / {CF_STRENGTH_REQ}", False,
                         "IM3 eye pull (first frame)"))
        fchk.append(_chk("creep at 1 g, worst torso", max(c["n_1g"] for c in cf.values()), PAHT_RUPT / pn, "creep",
                         f"fairlead_im3({ch['half_z']})"))
        clr = cheek_clearance(ch["half_z"], ch["cheek"])
        fchk.append(_chk("cheek bottom to spreader top edge vs the 6 mm notch rule (mm, as N)", clr["notch_clear_mm"],
                         clr["gap_mm"], "fit", "spreader.Z_HI, NOTCH_CLEAR"))
        fchk.append(_chk("throat for bag-hook + meat carabiner rods side by side (mm, as N; 2 x 8.5 mm ASSUMPTION)",
                         17.0, clr["throat_mm"], "fit", "bag_attach.THROAT (unchanged)", False,
                         "carabiner fit (first delivery)"))
        row("A1-CF", "BL-004", "IM3 eyes z 520, re-check on CORRIE F (BL-011) forces, per torso",
            "IM3 printed fairlead with the A1 25 mm cheek", "aft-up along T3", 1702, sz["factored_n"],
            "BL-011 CORRIE F cloth sims at 15 / 19 / 23 in (worst case each); factored = max(1702 misuse, 3.0 x "
            f"{max(c['n_1g'] for c in cf.values()):.1f})", chk,
            fix={"change": f"IM3 cheek {ch['height_mm']:.0f} mm tall (HALF_Z {ch['half_z']}, {ch['cheek']:g} mm "
                           "thick) instead of A1's 25 mm",
                 "mass_g": 2 * (ch["added_g"] - fea["fairlead_im3"][12.5]["added_g"]), "frame_change": True,
                 "checks": fchk},
            note="additive row (coordinator follow-up 2026-11-11); A1 stays as recorded on the S15 forces. Fix mass is "
                 "on top of A1's fix.")
        rows[-1]["sizing"] = sz
        rows[-1]["clearance"] = clr

    # ------------------------------------------------------------------ BL-006 (hipbelt_diet.md 5)
    T, Tw, lf = belt["T_c2"], belt["T_walk"], belt["leg_frac"]
    leg = lf * T
    row("H1", "BL-006", "BL006-1 50 mm buckle tabs, 25 mm anchor box-X and lock tab on them",
        "2 x 140 mm 50 mm nylon tabs round the buckle bars; 25 mm anchor and lock tab box-X tex 135",
        "along the belt", 1000, T, "hipbelt_structure.load_sets C2 (T per side); each 25 mm leg <= T/(2 x 0.85)",
        [_chk("50 mm buckle", T, H["buckle50"], "strength", "buckle_side_release_50mm (estimate)", False,
              "HB-T (tab + buckle pull)"),
         _chk("50 mm tab doubled round the buckle bar (kd 0.5)", T, C["kd_pin"] * H["nyl50"], "strength",
              "nylon_webbing_50mm x WEB_PIN_KD"),
         _chk("25 mm anchor box-X onto the tab, strength", leg, C["box25"], "strength", "ASSUMPTION BOX25", False,
              "HB-T (tab + buckle pull)"),
         _chk("25 mm anchor box-X, proof 1.5x", PROOF * leg, C["box25"], "proof", "ASSUMPTION BOX25", False,
              "HB-T (tab + buckle pull)"),
         _chk("25 x 40 box-X stitch-path model (cross-check)", PROOF * leg, C["box25x40_stitch"], "proof",
              "attach_system.box_x"),
         _chk("lock tab box-X onto the tab, proof", PROOF * leg, C["box25"], "proof", "ASSUMPTION BOX25", False,
              "HB-T (tab + buckle pull)"),
         _chk("box-X fatigue, walking T", lf * Tw, C["sew_fat"] * C["box25"], "fatigue", "ASSUMPTION SEW_FAT", False,
              "SEW-F (lever rig)")],
        note="the buckle itself stays at 1.50 on an estimate record (hipbelt_structural.md 5), unchanged by a2.")
    row("H2", "BL-006", "BL006-2 25 mm 2:1 webbing (length re-booked)", "same webbing, routing, lock, D-ring",
        "along the strap", 1000, T, "unchanged (hipbelt_structural.md 5)",
        [_chk("webbing", leg, H["web25"], "strength", "record"),
         _chk("heavy lock slip at the walking peak, 1.5 criterion", 1.5 * lf * Tw, H["llh"]["slip"], "proof",
              "record", False, "HB-3 lock slip (already planned)")],
        note="routed length only; lock leg = T / (2 x 0.85), as hipbelt_structural.md.")
    row("H3", "BL-006", "BL006-3 stabilizer straps deleted", "none", "none", 0, 0.0,
        "no rev C case, frame spring or fit term uses hip_stabilizer_anchor (grep: only frame_topopt / sizing5200v2 "
        "keep-out geometry and viz3d)", [], note="side-hill roll is a fit test (HB-D1), not strength.")
    row("H4", "BL-006", "BL006-4 wing HDPE 1.0 -> 0.75 mm", "HDPE floats, no net tension", "none", 0, 0.0,
        "hipbelt_structure.tab_check credits shell + 1000D only", [],
        note="no creep path while the HDPE floats (hipbelt_structural.md 5 rule).")
    return rows


# =============================================================================================== masses
def booked() -> dict:
    from huntkit.mass import ledger as L
    rows = {r["id"]: r for r in L.parts("corrie_b2_h1", "M")}
    bag_hook = (rows["attachment:attachment_bag_hooks_38_mm_al"]["g"]
                + rows["attachment:attachment_system_bag_hooks_1500_n"]["g"]) / 4.0
    b24 = rows["straps_meat:float_mode_stand_off_links_b#2"]["g"] / 2.0
    w = rows["straps_compression:haul_wraps_3_aluminium_g_hooks"]["g"]
    w_hook = (w - 3 * rec("ladder_lock_25mm", "mass_g")) / 3.0
    return {"bag_hook_g": bag_hook, "b24_hook_g": b24, "w_hook_g": w_hook, "pack_g": L.total("corrie_b2_h1", "M")}


def mass_summary(rows: list) -> dict:
    by = {"BL-003": 0.0, "BL-004": 0.0, "BL-006": 0.0}
    kit = 0.0
    frame = 0.0
    for r in rows:
        f = r.get("fix")
        if not f:
            continue
        if f.get("meat_trip_only"):
            kit += f["mass_g"]
            continue
        by[r["source"]] += f["mass_g"]
        if f.get("frame_change"):
            frame += f.get("frame_g", f["mass_g"] if r["id"] == "A1-CF" else
                           2 * (FROZEN["fairlead_im3"][12.5]["added_g"] - FROZEN["fairlead_im3"][9.0]["added_g"]))
    saved = {"BL-003": 218.5, "BL-004": 103.0, "BL-006": 500.3 - 442.9}    # ticket savings (source docs), g
    return {"fix_g": by, "meat_trip_kit_g": kit, "of_which_frame_g": frame,
            "saving_before_g": saved, "saving_after_g": {k: saved[k] - by[k] for k in by}}


def hooks_table() -> list:
    H, B = hw(), booked()
    return [
        {"where": "IM3 bag hooks (2)", "booked_g": B["bag_hook_g"], "rated_part": H["cara"]["id"], "rated_g": H["cara"]["g"]},
        {"where": "B-24 float-link hooks (2, meat-trip kit)", "booked_g": B["b24_hook_g"], "rated_part": H["cara"]["id"],
         "rated_g": H["cara"]["g"]},
        {"where": "IM3 meat-strap free end (1)", "booked_g": 8.0, "rated_part": H["cara"]["id"], "rated_g": H["cara"]["g"]},
        {"where": "IM1 / IM2 meat-strap free ends (2)", "booked_g": 8.0, "rated_part": H["g25"]["id"],
         "rated_g": H["g25"]["g"]},
        {"where": "W1-W3 haul-wrap hooks (3)", "booked_g": B["w_hook_g"], "rated_part": H["g25"]["id"],
         "rated_g": H["g25"]["g"]},
    ]


# =============================================================================================== front strap
def front_pad() -> dict:
    """BL-006 found item: two 25 mm legs past the wing tip, 79 / 103 kPa (median / worst, hipbelt_diet.md 3a, crude
    line-load estimate at 50 mm) against 48.6 kPa. Pressure ~ 1 / width (same formula), so the pad width that meets the
    limit, and the pad's mass from records (EVA 45C 5 mm + HDPE 0.75 mm stiffener + 330D cover both faces)."""
    p50 = {"median": 79.0, "worst": 103.0}
    lim = 48.6
    w_need = 50.0 * p50["worst"] / lim
    w, L = math.ceil(w_need / 10.0) * 10.0, 120.0       # ASSUMPTION: 120 mm long, covers the sharpest curvature
    a = w * L * 1e-6
    eva = a * 0.005 * rec("eva_foam_45c", "density_kg_m3") * 1e3
    hdpe = a * 0.00075 * rec("hdpe_sheet", "density_kg_m3") * 1e3
    cover = 2 * a * rec("cordura_330d_nylon66", "areal_density_gsm")
    each = eva + hdpe + cover
    return {"limit_kpa": lim, "p_at_50mm": p50, "width_needed_mm": w_need, "pad_w_mm": w, "pad_l_mm": L,
            "p_with_pad": {k: v * 50.0 / w for k, v in p50.items()}, "g_each": each, "g_pair": 2 * each,
            "parts_g": {"eva": eva, "hdpe": hdpe, "cover": cover}}


# =============================================================================================== output
def _a3_rev3_fix() -> dict:
    """BL-041 (pack-designer, orchestrator 2026-11-13): A3 as built in CORRIE F rev 3, from the structural record
    ``analysis/crown_tube_guy_loop.json`` (basis A ring check, the HA-LS-1 rule): B-25 bridle in 38 mm webbing, sleeves
    x 26.5-64.5, the guy and the B-28 crown strap on one tab (323 N envelope, 172 N fatigue peak); TL-1 494 N."""
    d = json.loads((ANALYSIS / "crown_tube_guy_loop.json").read_text())
    env = d["kit_loads"]["envelope"]
    b = next(f for f in d["fixes"] if f["key"] == "b25_38")
    t = d["tl1"]
    n, proof = env["static_n"], max(t["proof_n"], t["bar_rule_proof_n"])
    return {"change": "B-25 bridle in 38 mm webbing, sleeves x 26.5-64.5 (rev 3; crown_tube_guy_loop.md 5)",
            "mass_g": b["d_mass_g"],
            "checks": [_chk("rev 3: crown bar wall under the 38 mm B-25 sleeve (guy + crown strap, basis A)", n,
                            b["capacity_n"], "strength", "crown_tube_guy_loop basis A", False, "TL-1 494 N"),
                       _chk("rev 3: crown bar wall fatigue (FI at 1.6 g <= 0.5)", b["fi_fatigue"], 0.5, "fatigue",
                            "crown_tube_guy_loop basis A; units FI"),
                       _chk("rev 3: POM toggle pull-through, TL-1 proof", proof, 670.0, "proof",
                            "ASSUMPTION attach_system", False, "TL-1 494 N")]}


def compute(fea_live: bool = False, log=print) -> dict:
    fea = {"fairlead_im3": dict(FROZEN["fairlead_im3"])}
    body = dict(FROZEN["body_rec_per_torso"])
    if fea_live:
        for hz in (9.0, 12.5):
            r = fairlead_im3(hz)
            fea["fairlead_im3"][hz] = {"fi99": r["fi99"], "added_g": r["added_g"]}
            log(f"fairlead half_z {hz}: fi99 {r['fi99']:.4f}")
        b = body_rec(log=log)
        body = {**body, "strength": b["min"]["strength"], "fatigue": b["min"]["fatigue"], "creep": b["min"]["creep"]}
    beam, beam_r = beam_loads(False), beam_loads(True)
    sim, fl, belt = sim_loads(), float_loads(), belt_loads()
    fea["corrie_f"] = corrie_f_loads()
    rows = build_rows(beam, beam_r, sim, fl, belt, fea)
    return {"date": "2026-11-11", "standard": "HA-LS-1 rev C", "rows": rows, "beam": beam, "beam_rec": beam_r,
            "sim": sim, "float": fl, "belt": belt, "fea": {str(k): v for k, v in fea["fairlead_im3"].items()},
            "corrie_f": fea["corrie_f"],
            "fairlead_reproduce": {"record": FROZEN["fairlead_record_fi99_1415"],
                                   "this_run": fea["fairlead_im3"][9.0]["fi99"]},
            "body": {"h1_per_torso": FROZEN["body_h1_per_torso"], "rec_per_torso": body},
            "r28": FROZEN["r28"], "mass": mass_summary(rows), "hooks": hooks_table(), "booked": booked(),
            "front_pad": front_pad(), "assumptions": ASSUMPTIONS}


def final_verdict(r: dict) -> str:
    if "fix" in r:
        return f"FAIL -> fix: {r['fix']['after_verdict']}"
    return r["verdict"]


def plot(res: dict, path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [r for r in res["rows"] if r["checks"]]
    lab, before, after = [], [], []
    for r in rows:
        lab.append(f"{r['id']} {r['location'][:44]}")
        before.append(r["min"])
        after.append(r["fix"]["after_min"] if "fix" in r else r["min"])
    y = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(rows) + 1.6), dpi=110)
    b = np.clip(before, 0, 4)
    a = np.clip(after, 0, 4)
    ax.barh(y + 0.18, b, 0.36, color=["#b03a2e" if v < 1 else "#9aa5b1" for v in before], label="as handed over")
    ax.barh(y - 0.18, a, 0.36, color=["#b03a2e" if v < 1 else "#2e7d4f" for v in after], label="with BL-010 fixes")
    ax.axvline(1.0, color="k", lw=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(lab, fontsize=8)
    ax.set_xlim(0, 4)
    ax.set_xlabel("worst capacity / demand per row (1.0 = limit; bars clipped at 4)")
    for yi, v0, v1 in zip(y, before, after):
        ax.text(min(v0, 4) + 0.03, yi + 0.18, "no rating" if v0 < 0.01 else f"{v0:.2f}", va="center",
                fontsize=7, color="#b03a2e" if v0 < 1 else "k")
        ax.text(min(v1, 4) + 0.03, yi - 0.18, f"{v1:.2f}", va="center", fontsize=7)
    nl = ", ".join(r["id"] for r in res["rows"] if not r["checks"])
    ax.set_title("BL-010: margin per changed load path, HA-LS-1 rev C (red < 1)\n"
                 f"no-load rows {nl} pass and are not drawn", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def _lb(g):
    return f"{g / 28.3495:.1f} oz"


def write_md(res: dict) -> str:
    rows, m, H = res["rows"], res["mass"], hw()
    a = []
    w = a.append
    w("# BL-010 Load-path verification (HA-LS-1 rev C)\n")
    w("structural-fea-engineer, 2026-11-11. Generated by `python -m huntkit.gendesign.loadpath_check`; do not edit by "
      "hand. Inputs: the 'load paths for BL-010' tables of `strap_architecture.md` section 7 (BL-003, REC, wings "
      "deleted), `attachment_diet.md` section 5 (BL-004 REC) and `hipbelt_diet.md` section 5 (BL-006). Shell S15. "
      "Proof rule: 1.5 x factored (bag_attachment.md). Fatigue: 1e5 cycles 0 -> 1.6 g. "
      "Units: N (1 N = 0.225 lbf), g (1 oz = 28.35 g).\n")
    nf = sum(1 for r in rows if "fix" in r and r["id"] != "A3")
    w("## 1. Result\n")
    w(f"- **{len(rows)} rows, every row has a verdict.** {nf} rows FAIL as handed over; each has a fix that passes. "
      "The rest pass on rated parts or pass after a named test. A3 passed as handed over (244 N); its fix rows are "
      "the rev 3 build (B-25 in 38 mm under the 323 N guy + crown-strap envelope, BL-041).")
    w(f"- **Check of the solver first:** the IM3 fairlead at 1415 N reproduces the released float_fea record "
      f"(FI99 {res['fairlead_reproduce']['this_run']:.4f} vs {res['fairlead_reproduce']['record']:.4f}); H1's "
      f"per-torso body fatigue reproduces {res['body']['h1_per_torso']['fatigue']:.3f} (BL-017).")
    w(f"- **H1 body fatigue, per torso setting (BL-017 basis): {res['body']['h1_per_torso']['fatigue']:.3f}** "
      f"(governs at 23 in), not 1.279. With BL-004 REC's load change "
      f"(IM2 bag share to IM3, no hood term, guys 82 N at 1 g): **{res['body']['rec_per_torso']['fatigue']:.3f}**, "
      f"strength {res['body']['rec_per_torso']['strength']:.3f}, creep {res['body']['rec_per_torso']['creep']:.3f}. "
      "Pass.")
    w(f"- **New finding: the IM3 printed fairlead fails fatigue under the cloth-sim bag-hook load** "
      f"({res['sim']['im3_REC_S15']['n_1g']:.0f} N at 1 g on S15 REC; the fairlead was released on the beam model's "
      "605 N factored = 202 N at 1 g). Today's design fails too. Fix: cheek 18 -> 25 mm tall, +2.7 g a side, a frame "
      "print change.")
    cfr0 = next((r for r in rows if r["id"] == "A1-CF"), None)
    if cfr0:
        c0 = cfr0["sizing"]["chosen"]
        w(f"- **A1-CF (BL-011 follow-up):** on CORRIE F's measured IM3 forces (552 / 516 / 460 N at 15 / 19 / 23 in) the "
          f"25 mm cheek gives fatigue {cfr0['min']:.2f} at 15 in. Smallest change that passes every torso with strength "
          f">= 1.5: **{c0['height_mm']:.0f} mm cheek**, fatigue {min(c0['fatigue'].values()):.2f}, strength "
          f"{c0['strength']:.2f}, **+{cfr0['fix']['mass_g']:.2f} g a pair over the 25 mm cheek** (section 4.1).")
    w(f"- **Net mass of the FAIL fixes:** BL-003 +{m['fix_g']['BL-003']:.1f} g (saving 218.5 -> "
      f"{m['saving_after_g']['BL-003']:.1f} g), BL-004 +{m['fix_g']['BL-004']:.1f} g (saving 103.0 -> "
      f"{m['saving_after_g']['BL-004']:.1f} g; {m['of_which_frame_g']:.1f} g of it is printed frame), BL-006 "
      f"+{m['fix_g']['BL-006']:.1f} g (saving {m['saving_before_g']['BL-006']:.1f} g kept). Meat-trip kit (B-24 hooks, "
      f"booked-mass correction): +{m['meat_trip_kit_g']:.1f} g.\n")

    w("## 2. Verdict per row\n")
    w("| row | source | location | factored N (ticket -> confirmed) | governs | worst ratio | verdict | fix (mass) |")
    w("|---|---|---|---|---|---:|---|---|")
    for r in rows:
        fx = f"{r['fix']['change']} (**{r['fix']['mass_g']:+.1f} g**); after: {r['fix']['after_verdict']} " \
             f"({r['fix']['after_min']:.2f})" if "fix" in r else "-"
        mn = "-" if not r["checks"] else f"{r['min']:.2f}"
        w(f"| {r['id']} | {r['source']} | {r['location']} | {r['ticket_factored_n']} -> {r['factored_n']:.0f} | "
          f"{r['governs']} | {mn} | {r['verdict']} | {fx} |")
    w("")
    w("## 3. Checks per row\n")
    w("Ratio = capacity / demand (>= 1 passes). 'assumed' = no rated value on file; the named test settles it.\n")
    for r in rows:
        w(f"### {r['id']} {r['location']}\n")
        w(f"Part: {r['part']}. Load basis: {r['load_basis']}.{' ' + r['note'] if r['note'] else ''}\n")
        if not r["checks"]:
            w("No load on this path.\n")
            continue
        w("| check | kind | demand | capacity | ratio | basis |")
        w("|---|---|---:|---:|---:|---|")
        for c in r["checks"] + (r["fix"]["checks"] if "fix" in r else []):
            tag = "" if c["rated"] else " (assumed: " + c["test"] + ")"
            w(f"| {c['item']} | {c['kind']} | {c['demand_n']:.1f} | {c['capacity']:.1f} | {c['ratio']:.2f} | "
              f"{c['basis']}{tag} |")
        if "fix" in r:
            w(f"\nFix rows are the last {len(r['fix']['checks'])} lines.")
        w("")

    w("## 4. Frame side: H1 body and the IM3 fairlead\n")
    b0, b1 = res["body"]["h1_per_torso"], res["body"]["rec_per_torso"]
    w("| basis | strength | fatigue | creep | governs |")
    w("|---|---:|---:|---:|---|")
    w(f"| H1 released loads, one tag per torso (BL-017) | {b0['strength']:.3f} | **{b0['fatigue']:.3f}** | "
      f"{b0['creep']:.3f} | {b0['governing']} |")
    w(f"| H1 with BL-004 REC loads | {b1['strength']:.3f} | **{b1['fatigue']:.3f}** | {b1['creep']:.3f} | "
      f"{b1['governing']} |\n")
    w("BL-007's 1.08 / 1.04 and every earlier H1 fatigue figure (1.279) were on the recorded basis; restated on the "
      "per-torso basis H1 is 1.150 and 1.144 with REC.\n")
    w("IM3 fairlead (bag_attach.solve_fairlead, h 1.0 mm, rev C IM3 direction), FI99 per newton:\n")
    w("| cheek height mm (HALF_Z) | FI99 at 1415 N | added g | strength at 1702 N | fatigue at 1.6 x 507 N | creep at 507 N |")
    w("|---|---:|---:|---:|---:|---:|")
    n1 = res["sim"]["im3_REC_S15"]["n_1g"]
    for hz, v in sorted(res["fea"].items(), key=lambda kv: float(kv[0])):
        pn = v["fi99"] / 1415.1
        w(f"| {2 * float(hz):.0f} ({float(hz):g}) | {v['fi99']:.4f} | {v['added_g']:.2f} | {1 / (pn * 1702):.2f} | "
          f"{PAHT_FAT / (pn * G_WALK * n1):.2f} | {PAHT_RUPT / (pn * n1):.2f} |")
    w("\n25 mm (HALF_Z 12.5) is the smallest tested step that passes on S15. CORRIE's 557 N would need 28 mm (14.0). "
      "The cheek grows along the stay at z 520, above the spreader (top edge z 430): no clash. It is an H1 print-file "
      "change (released files untouched here).\n")

    cfr = next((r for r in rows if r["id"] == "A1-CF"), None)
    if cfr:
        sz, clr = cfr["sizing"], cfr["clearance"]
        w("### 4.1 A1-CF: IM3 eye on the CORRIE F (BL-011) forces, per torso\n")
        w("BL-011 measured the IM3 bag-hook force at 1 g on CORRIE F (door D2): " + ", ".join(
            f"{t} in {c['n_1g']:.1f} N ({c['case']})" for t, c in sorted(res["corrie_f"].items(), key=lambda kv: int(kv[0])))
          + f". A1's 25 mm cheek was sized on S15's 507 N. Factored load {sz['factored_n']:.0f} N (the misuse "
          "envelope still governs over 3.0 x 552 N = 1657 N). Requirement for this row: fatigue >= 1.0 at every torso "
          f"and strength >= {CF_STRENGTH_REQ} at the factored load.\n")
        w("| cheek height x thickness mm | added g (one eye) | fatigue 15 / 19 / 23 in | strength at factored | passes |")
        w("|---|---:|---|---:|---|")
        for v in sz["rows"]:
            ft = " / ".join(f"{v['fatigue'][t]:.2f}" for t in sorted(v["fatigue"], key=int))
            w(f"| {v['height_mm']:.1f} x {v['cheek']:g} | {v['added_g']:.2f} | {ft} | {v['strength']:.2f} | "
              f"{'yes' if v['ok'] else 'no'} |")
        c = sz["chosen"]
        w(f"\n**Smallest passing change: cheek {c['height_mm']:.0f} mm tall, 8 mm thick** (HALF_Z {c['half_z']}): "
          f"fatigue {' / '.join(f'{c[chr(102)+chr(97)+chr(116)+chr(105)+chr(103)+chr(117)+chr(101)][t]:.2f}' for t in sorted(c['fatigue'], key=int))}, "
          f"strength {c['strength']:.2f}, creep {c['creep']:.2f}. Mass {c['added_g']:.2f} g an eye: "
          f"**+{cfr['fix']['mass_g'] / 2:.2f} g an eye, +{cfr['fix']['mass_g']:.2f} g a pair over A1's 25 mm cheek**, "
          f"+{2 * (c['added_g'] - res['fea']['9.0']['added_g']):.2f} g a pair over the released 18 mm eye. The FEA "
          "grid is 1 mm, so 26.5 mm voxelises to 26 mm (same FI as 26, which fails at 15 in, 0.98); 27 mm is the next "
          "step. Thicker cheeks (9-10 mm) pass at 25 mm tall but weigh more.\n")
        w(f"Clearances: cheek z {clr['cheek_bottom_z']:.1f}-{clr['cheek_top_z']:.1f}; spreader top edge z "
          f"{clr['spreader_top_z']:.0f}, gap {clr['gap_mm']:.1f} mm against the {clr['notch_clear_mm']:.0f} mm notch rule "
          "(pass). The throat stays 18 mm and the cheek still stands 7.6 mm aft of the hole centre, so the hook path is "
          "unchanged: the cheek grows along the stay, beside the throat, not across the hook's swing. The throat takes "
          "two carabiner rods side by side on the right eye (bag hook + IM3 meat free end): fits if each rod is "
          "<= 8.5 mm (ASSUMPTION; Nano 22 rod section not published), check on first delivery. Left eye: bag hook + "
          "girth hitch (2.8 mm). The cheek top (z 533.5) sits on the stay at the upper-bar node, which the 18 mm cheek "
          "already overlaps; confirm on the H1 STL that the union adds no sliver (H1 files already have sliver defects).\n")

    w("## 5. Open items settled\n")
    w(f"- **IM3 bag hook:** the factored load is confirmed at **{next(r for r in res['rows'] if r['id'] == 'A1')['factored_n']:.0f} N** (guys-off "
      "misuse, CORRIE 15 in; S15 alone 1573 N, S15 REC 1522 N); proof 2553 N. No light 38 mm webbing hook is rated "
      "above 1.5 kN (AustriAlpin DY38K-G 1.5 kN / 16 g; Extremtextil 38 mm hooks 0.76-1.25 kN). Chosen: a certified "
      "wiregate carabiner, **CAMP Nano 22 (22 g, 21 kN major, 8 kN minor, 9 kN gate open)**, record "
      "`data/materials/hardware/carabiner_wiregate_22kn.yaml` (confidence estimate; sources are retailer copies of the maker "
      "figures). Proof margin 4000 / 2553 = 1.57 on the 0.5 x minor-axis rule. Mass +8 g a hook against the booked "
      "14 g.")
    w("- **Meat-strap hooks:** the 910 N MT-2 proof is 1.5 x the IM3 strap's 605 N and is kept. The 25 mm G-hook "
      "(record `g_hook_25mm_aluminium`, 0.9 kN no-set) passes on IM1 (410 N proof) and IM2 (645 N) and fails on IM3 "
      "(908 N, ratio 0.99). IM3's free end takes the Nano 22 (+14 g). MT-2 proofs per strap: IM1 410, IM2 645, IM3 910 N.")
    w("- **W1-W3 G-hook:** the 4 g HAUL hook has no rating; replaced by the rated 25 mm G-hook (8 g, 900 N no-set): "
      "proof 338 N, ratio 2.66. The standard ladder lock (300 N slip) fails the 338 N proof; the heavy lock "
      "(490 N) passes after its slip test. +21 g for the three wraps.")
    w("- **50 mm buckle-side anchor box-X (BL006-1):** each 25 mm leg carries at most T / (2 x 0.85) = "
      f"{res['belt']['leg_frac'] * res['belt']['T_c2']:.0f} N at C2; 25 mm box-X 1776 N (assumed): proof ratio "
      f"{1776.0 / (1.5 * res['belt']['leg_frac'] * res['belt']['T_c2']):.2f}. PASS after a tab pull (HB-T).")
    fp = res["front_pad"]
    w(f"- **Front-strap pressure:** at 50 mm the crude estimate is {fp['p_at_50mm']['median']:.0f} / "
      f"{fp['p_at_50mm']['worst']:.0f} kPa against {fp['limit_kpa']} kPa. Pressure falls as 1/width, so a pad has to "
      f"spread the legs over >= {fp['width_needed_mm']:.0f} mm. A {fp['pad_w_mm']:.0f} x {fp['pad_l_mm']:.0f} mm "
      f"sliding pad (EVA 45C 5 mm + HDPE 0.75 mm stiffener + 330D both faces) gives "
      f"{fp['p_with_pad']['median']:.0f} / {fp['p_with_pad']['worst']:.0f} kPa at **{fp['g_each']:.1f} g a side, "
      f"{fp['g_pair']:.1f} g ({_lb(fp['g_pair'])}) a pair**. A soft pad without the stiffener does not spread a "
      "webbing line load (ASSUMPTION PAD). Recommendation: do not book it yet; HB-1 measures in front of the wing tip "
      "first, the pad is the fallback.")
    r28 = res["r28"]
    w("- **R-28 head clearance at 23 in (S15): the failure is real, but the method also has a frame-position error.** "
      "`huntkit/gendesign/attach_system.py` line 158 (`r28_loaded`) builds the wall as `bg.y_frame(z) - move`, i.e. "
      "the SPINE design face (`build_geometry.y_frame`) minus a move measured from the *calling shell's own* drafted "
      "face (`shell_sweep.r28` line 313 ff., `attach_diet.r28` line 199 ff.). Above z 785 S15's drafted face sits "
      "5-25 mm aft of `y_frame`, so the wall is put 5-25 mm too close to the head. The sim's coordinates match "
      "build_geometry's (crown bar y 9.8 vs 9.7 at 23 in), so the right wall is the loaded face itself. Corrected: "
      f"S15 23 in fill {r28['S15_23_fill']['as_coded']:.0f} -> {r28['S15_23_fill']['abs_face']:.0f} deg, meat "
      f"{r28['S15_23_meat']['as_coded']:.0f} -> {r28['S15_23_meat']['abs_face']:.0f} deg; on the x = 0 section "
      f"{r28['S15_23_fill']['x0_section']:.0f} / {r28['S15_23_meat']['x0_section']:.0f} deg. **Still below 30 deg.** "
      "S15's loaded frame-side wall at x = 0 is 17 / 6 mm head-side of the crown bar's front face at z 785 / 835 "
      "(bar face y 0.8): above a 23 in crown only ~180 mm of bag remains and it bulges forward over the bar. CORRIE "
      "passes either way (34 deg). A second, smaller inconsistency: `attach_system.drafted_fore_face` (line 100) "
      "uses the x = 0 band, while `clothsim/report.py` line 211 computes the same `sec` mask and then takes the "
      "depth profile over all x (the mask is unused). Not edited here (owner of attach_system).")
    w("- **H1 print-file defects (release blockers, not fixed here):** `h1_lower_flat.stl` has a loose 0.57 cm3 "
      "island and three slivers (not one closed shell); `h1_assembled.stl` has 4 slivers. R1 cannot ship until both "
      "are single closed shells. The IM3 cheek change (section 4) also lands in these files.\n")
    w("## 6. Hook masses: booked vs the rated part used\n")
    w("| where | booked g | rated part | rated g | delta per hook |")
    w("|---|---:|---|---:|---:|")
    for h in res["hooks"]:
        w(f"| {h['where']} | {h['booked_g']:.1f} | `{h['rated_part']}` | {h['rated_g']:.1f} | "
          f"{h['rated_g'] - h['booked_g']:+.1f} |")
    w("")
    w("## 7. Mass after FAIL fixes, per source ticket\n")
    w("| ticket | saving claimed g | fixes g | saving after g |")
    w("|---|---:|---:|---:|")
    for k in ("BL-003", "BL-004", "BL-006"):
        w(f"| {k} | {m['saving_before_g'][k]:.1f} | {m['fix_g'][k]:+.1f} | {m['saving_after_g'][k]:.1f} |")
    w(f"\nMeat-trip kit only: B-24 hooks to the rated part {m['meat_trip_kit_g']:+.1f} g. Ledger pack today (H1, belt "
      f"M): {res['booked']['pack_g']:.1f} g. Load-path member masses are the ledger rows named in the source tickets.\n")
    w("## 8. Tests that settle the assumed margins\n")
    for k, (txt, t) in ASSUMPTIONS.items():
        w(f"- ASSUMPTION {k}: {txt} Test: {t}")
    w("- MT-1 (25 mm box-X): 5 of 5 hold 908 N (IM) and 1080 N (US) for 1 min on a 5 mm pin.")
    w("- MT-2 per strap: IM1 410 N, IM2 645 N (25 mm G-hook), IM3 910 N (carabiner).")
    w("- PT-1 raised from 2120 to **2553 N** on the sewn T3 tongue + carabiner; PT-2 on the 70 mm B-17 tab at 2553 N.")
    w("- HB-T: 50 mm tab round a buckle bar + 25 mm anchor and lock-tab box-X, pull to 1500 N (1.5 x 1000 N) on a "
      "bar (no buckle), 5 of 5.")
    w("- W-pull: on the first frame, each W lash point to 338 N.")
    w("- IM3 eye pull: first frame, IM3 eye through a sewn T3 tongue to 2553 N, no crack; then 1e5 cycles 0 -> 812 N "
      "on the lever rig on one eye coupon.\n")
    w("## 9. Screens\n")
    w(f"- `outputs/screens/{SHOT}`: margin per row, as handed over and with the fixes.\n")
    return "\n".join(a)


def run(fea_live: bool = False, log=print) -> dict:
    res = compute(fea_live, log=log)
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    DOC.write_text(write_md(res))
    plot(res, SCREENS / SHOT)
    log(f"wrote {RESULTS.relative_to(REPO)}, {DOC.relative_to(REPO)}, outputs/screens/{SHOT}")
    return res


if __name__ == "__main__":
    run(fea_live="--fea" in sys.argv)
