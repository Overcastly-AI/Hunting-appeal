"""BL-085 driver: the B85 frame (B81 with the BL-085 upper / mid tees) on the full HA-LS-1 rev C envelope incl. C6p,
the tee rows on the Yahr design S-N curve with fretting and preload scatter, the BL-081 local rows re-run on the B85
global model, mass / cost (cited), the comparison with H1c / B81 / B81-Lb / D83-L, coupons, screens and the record
``designs/pack_5200/iter2/frame_b85/bl085.{json,md}``.

Run: ``python -m huntkit.gendesign.bl085_report run`` (about 15 min on 4 cores; stages cached in outputs/bl085/),
``... md`` re-writes the Markdown and screens from the stored JSON.
"""
from __future__ import annotations

import contextlib
import json
import math
import sys
import time

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl081_report as BR
from huntkit.gendesign import bl085_global as G85
from huntkit.gendesign import bl085_parts as P85
from huntkit.gendesign import bl085_tee as T

OUTDIR = P85.OUTDIR
REC_JSON = OUTDIR / "bl085.json"
REC_MD = OUTDIR / "bl085.md"
CACHE = G85.CACHE
SCREENS = BQ.SCREENS
SHOT = "20261125_bl085_"
DATE = "2026-11-25"
CFG_B85 = {"mid_tee": "saddle"}
ITEMS = {**BR.ITEMS, "5": "Upper / mid tees (BL-085: two-pair clamp under a real free end; pinned saddle)",
         "G": "Global model, full envelope incl. C6p"}


# ----------------------------------------------------------------------------- BL-081 machinery on the B85 model
@contextlib.contextmanager
def _b85_model():
    """Swap the B85 builder (mid tee = pinned saddle, ``bl085_global.SADDLE_K``) into bl081_concept_b and make C6p
    visible to its evaluate_global (BL-081 skips the case by name; the copy here is renamed, its loads are unchanged)."""
    import copy as _copy

    from huntkit.fea import load_standard as LS
    b_old, env_old = BQ.build, LS.ls1_envelope

    def build85(cfg=None, torso=19.0, rigid=False):
        m = b_old(cfg, torso, rigid)
        if not rigid and (cfg or {}).get("mid_tee") == "saddle":
            for ln in m["links"]:
                if ln["id"] in ("tee_L330", "tee_R330"):
                    ln["k"] = list(G85.SADDLE_K)
        return m

    def env(rev=None):
        out = {}
        for k, cases in env_old(rev).items():
            lst = []
            for c in cases:
                if c.name == "tall_load_posts":
                    c = _copy.copy(c)
                    c.name = "tall_load_posts_c6p"
                lst.append(c)
            out[k] = lst
        return out
    BQ.build, LS.ls1_envelope = build85, env
    try:
        yield
    finally:
        BQ.build, LS.ls1_envelope = b_old, env_old


def global_b81_format(log=print) -> dict:
    p = CACHE / "global_b81fmt_b85.json"
    if p.exists():
        return json.loads(p.read_text())
    with _b85_model():
        g = BQ.evaluate_global({**BQ.CFG0, **CFG_B85}, log=log)
    g.pop("_disp", None)
    p.write_text(json.dumps(BR._js(g)))
    return json.loads(p.read_text())


# ----------------------------------------------------------------------------- corrected bushing rows (finding F1)
def bushing_rows_85(g: dict, g85: dict, cfg: dict) -> list[dict]:
    """BL-081 bushing rows take the stay beam stress as Fy / sf (the stress at the case's LIMIT load, not x the case
    factor) and then treat it as factored (/ 3 x 1.6 for the walk): low by the factor 1.5 (finding F1). Here: factored
    stay stress = Fy / (stays margin), walk = the meat / carry walk stress at z 330 from the B85 global (the leg-end
    bushing travels z 171-374), polymer contact (UHMWPE) on the design curve as the mid saddle."""
    U = BL.bushing_units(BQ.CFG0["stay"], BQ.CFG0["bush_len"], BQ.CFG0["bush_contact_deg"])
    ld = T.tee_loads(g85, 330.0)
    ldu = T.tee_loads(g85, 520.0)
    walk = {}
    for rec in g["walk"].get("_links", []):
        for k in ("bush_low_L", "bush_low_R", "bush_top_L", "bush_top_R"):
            walk[k] = max(walk.get(k, 0.0), float(np.linalg.norm(np.asarray(rec["links"][k])[:2])))
    rows = []
    s_fact = BQ.FY_6061 / g85["strength"]["stays"]["margin"]
    for where, keys, sbf, sbw, lab in (
            ("mid", ("bush_low_L", "bush_low_R"), s_fact, ld["beam_walk"], "leg-end bushing (z 171-374)"),
            ("end", ("bush_top_L", "bush_top_R"), ldu["beam_fact"], ldu["beam_walk"], "stay-top bushing (z 475-545)")):
        F = max(g["links"][k]["F"] for k in keys)
        Fw = max(walk[k] for k in keys)
        sh = U[where]["hoop_peak"] * F / 1000.0
        vm = math.sqrt(sbf ** 2 + sh ** 2 + sbf * sh)
        rows.append({"item": "3", "row": f"stay at the {lab}: static (ring + beam), corrected beam stress", "kind": "strength",
                     "value": vm, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / vm,
                     "basis": f"bushing {F:.0f} N factored -> hoop {sh:.0f} MPa; stay beam {sbf:.0f} MPa factored (BL-081 "
                              f"used Fy / sf, 1.5 x low)"})
        shw = U[where]["hoop_peak"] * Fw / 1000.0
        # gated on the BL-081 basis (mean curve, Kt 2 at the bushing end), corrected beam stress
        sf = math.sqrt((2 * sbw) ** 2 + shw ** 2 + 2 * sbw * shw)
        fa = BQ.fat_allow_local(1.0)
        rows.append({"item": "3", "row": f"stay at the {lab}: fatigue (BL-081 basis, corrected beam stress)", "kind": "fatigue",
                     "value": sf, "allow": fa, "margin": fa / sf,
                     "basis": f"walk {Fw:.0f} N -> hoop {shw:.0f} MPa, Kt 2 x beam walk {sbw:.0f} MPa (B85 global); mean curve"})
        smax = T.CFG85["kt_saddle"] * sbw + shw
        Sa = T.allowable_sa("poly", T.CFG85)
        mg = T.goodman_margin(smax / 2, smax / 2, Sa)
        rows.append({"item": "3", "row": f"stay at the {lab}: fatigue on the design curve + polymer contact (sensitivity)",
                     "kind": "info", "value": 1 / mg, "allow": 1.0, "margin": mg,
                     "basis": f"R 0 walk Kt {T.CFG85['kt_saddle']} x {sbw:.0f} + hoop {shw:.0f} MPa; Sa {Sa:.1f}; not gated "
                              "(non-tee row); KF-S runs with the leg + bushing inside to settle it"})
        ov = U[where]["oval_diam_mm"] * F / 1000.0
        rows.append({"item": "3", "row": f"{lab}: bore ovalisation at limit vs leg clearance", "kind": "joint", "value": ov,
                     "allow": 2 * BQ.CFG0["leg_clear_mm"], "margin": 2 * BQ.CFG0["leg_clear_mm"] / max(ov, 1e-9),
                     "basis": "n = 2 diametral change (BL-081 method)"})
    return rows


def global_rows(g85: dict) -> list[dict]:
    rows = []
    for k, v in g85["strength"].items():
        rows.append({"item": "G", "row": f"{k}: member strength (beam, all cases incl. C6p)", "kind": "strength",
                     "value": v["sf"], "allow": v["required"], "margin": v["margin"], "basis": f"{v['member']} {v['case']}"})
    b = g85["buckling"]
    rows.append({"item": "G", "row": "frame buckling eigenvalue / (1.5 x case factor), incl. C6p", "kind": "strength",
                 "value": b["eigen"], "allow": None, "margin": b["margin"], "basis": b["case"]})
    return rows


def design_curve_sensitivity(rows: list[dict]) -> list[dict]:
    """Non-tee metal fatigue rows of the BL-081 basis (Yahr MEAN curve, Goodman R 0, allow 190.9) re-scaled to the
    design curve (R 0 S_max 114.3): margin x 114.3 / 190.9. Reported, not gated (the brief scopes the design curve to
    the tees; the frame-wide basis is the orchestrator's call)."""
    b = T.sn_basis()
    sa_d = b["design"]
    smax_d = 2 * sa_d * 290 / (290 + sa_d)
    out = []
    for r in rows:
        if r["kind"] == "fatigue" and r.get("allow") and abs(r["allow"] - BQ.fat_allow_local(1.0)) < 0.5:
            out.append({"row": r["row"], "mean_margin": r["margin"], "design_margin": r["margin"] * smax_d / r["allow"]})
    return sorted(out, key=lambda x: x["design_margin"])


# ----------------------------------------------------------------------------- comparison
def comparison(mass, cost) -> list[dict]:
    from huntkit.gendesign.bl080_metal_frame import H1C
    b81 = json.loads(BQ.REC_JSON.read_text())
    d = json.loads((BQ.REPO / "designs/pack_5200/iter2/frame_d/bl083.json").read_text())
    Lb, DL = d["b81_levers_065"], d["variants"]["D83-L"]
    ship = round(P85.SHIP_ZONE8 * P85.FUEL, 2)
    return [
        {"option": "H1c", "body_g": H1C["body_g"], "usd": H1C["usd"], "strong": "FAIL",
         "note": "two PAHT joints below goal (BL-077)"},
        {"option": "B81", "body_g": b81["mass"]["body_g"], "usd": b81["cost"]["per_frame_usd"], "strong": "FAIL",
         "note": "as-built upper tee 0.65 static / 0.67 fatigue (review 9 B1); mid tee unchecked (M1)"},
        {"option": "B81-Lb", "body_g": Lb["bill"]["body_g"], "usd": round(Lb["bill"]["per_frame_usd"] + 18.0, 2), "strong": "FAIL",
         "note": "B1-B3 + band tee has no geometry (B2); USD incl. the SHIP-BASE 18 it dropped (M6); doubler leak M7 "
                 "fixed in bl083_report.check_b81l (stored bl083.json not regenerated): stay z135 gusset-bolt fatigue 1.05, "
                 "not 1.48"},
        {"option": "D83-L", "body_g": DL["mass"]["body_g"], "usd": round(DL["cost"]["per_frame_usd"] + 18.0, 2), "strong": "FAIL",
         "note": "shares B81-Lb tees (B1-B3); USD 92 over cap before shipping: dropped from play"},
        {"option": "B85 (this record)", "body_g": mass["body_g"], "usd": cost["per_frame_usd"], "strong": None,
         "note": f"shipping booked at FedEx zone 8 + fuel (USD {ship})"},
    ]


# ----------------------------------------------------------------------------- coupons (new joint)
def coupons(rec: dict) -> list[dict]:
    c = T.CFG85
    up = {r["row"]: r for r in rec["rows"] if r.get("tee") == "upper"}
    g85 = json.loads((CACHE / "global_b85.json").read_text())
    ld = T.tee_loads(g85, 520.0)
    ldm = T.tee_loads(g85, 330.0)
    R = 12.7
    F_req = max(fz + mz / R for fz, mz, _ in ld["slip_u_terms"])
    F_req = max(F_req, T.PAWL_ROWS[0][0])
    lo = 1 - c["scatter"]
    t_lo, t_hi = c["torque_nm"] * lo, c["torque_nm"] * (1 + c["scatter"])
    return [
        {"id": "CL-T", "what": f"upper-tee slip, WET, at the LOW scatter torque {t_lo:.2f} N m on all 4 bolts: 300 mm offcut of the "
         f"545 mm stay, 15 mm free end above 100 mm shells from Speedy p-4573, 3/16 backers; (a) pull along the stay, (b) twist "
         "about the stay with a 300 mm lever on the bar stub; n 5; also dry, and wet after 24 h at 40 C",
         "pass": f"(a) every wet axial slip load >= {1.2 * F_req:.0f} N and (b) every wet torque slip >= {1.2 * F_req * R / 1000:.1f} N m "
                 f"(1.2 x the factored demand {F_req:.0f} N / {F_req * R / 1000:.1f} N m, side hill C3 incl. C6p); no tube dent > 0.1 mm",
         "settles": "MU 0.15 wet, EMBED 0.9, K 0.2 at the low limit, SHELL-FIT", "usd": 0.0},
        {"id": "KF-T", "what": f"upper-tee fatigue (review 9 B4): same coupon at the HIGH scatter torque {t_hi:.2f} N m, clamped 75 mm "
         "below the shells; on the T5 crank rig cycle 0 -> 1.2 x walk: bar couple "
         f"{1.2 * ld['w_mxy'] / 1000:.1f} N m, bar push {1.2 * ld['w_fy']:.0f} N, IM3 loop {1.2 * T.IM3_F / 3 * 1.6:.0f} N; "
         "R 0, n 3, 2e5 cycles (2 x life)",
         "pass": "no crack (dye penetrant under and beside both shell edges and at the free end), no fretting debris track "
                 "> 0.5 mm wide, re-torque check: >= 80 % of the set torque to move the bolts",
         "settles": "design curve + fretting 0.6 (FRET-METAL), CLAMP-UNIFORM / SHELL-FIT, Kt 2", "usd": 0.0},
        {"id": "KF-S", "what": "mid-saddle fatigue: 400 mm stay offcut in 4-point bending on the T5 rig with the printed saddle + "
         "a crown-leg offcut and its UHMWPE leg-end bushing inside under the saddle (covers the bushing row too) + "
         f"band at {c['band_torque_nm']} N m in the constant-moment span; R 0.1, S_max at the saddle {1.2 * ldm['beam_walk']:.0f} MPa "
         f"(1.2 x the walk {ldm['beam_walk']:.0f} MPa, M {1.2 * ldm['beam_walk'] * 686 / 1000:.0f} N m), n 3, 2e5 cycles",
         "pass": "no crack at the saddle edges (dye penetrant); saddle not cracked", "settles": "SADDLE-KT 1.15, FRET-POLY 0.85",
         "usd": 0.0},
        {"id": "BS-T", "what": "upper bar end in double shear: bar stub + 2 bolts + spacers between the two upper backers, held as in "
         f"the tee; load the bar as a cantilever to the factored couple {ld['mxy'] / 1000:.0f} N m, hold 2 min, then to failure",
         "pass": f"no permanent set > 0.2 mm at the bar tip after {ld['mxy'] / 1000:.0f} N m; ultimate >= {1.5 * ld['mxy'] / 1000:.0f} N m",
         "settles": "bar-wall bearing at e/D 1.9, bolt double shear, backer bending (M8 metal path)", "usd": 0.0},
        {"id": "OV-2", "what": "fit-up on the built frame: (a) torque the upper tees to the high limit with leg + bushing inside, "
         "pull the leg with a spring scale; (b) set the crown to the 15 in torso and gauge the stay-top collar to the crown corner; "
         "(c) ID of the p-4573 shells vs the stay OD with calipers before sawing",
         "pass": "(a) leg slide <= 20 N, feeler >= 0.3 mm radial at the bushing mouth; (b) >= 5 mm clear (else shorten the stay "
                 "extension and re-run with the measured free end); (c) shell ID - stay OD <= 0.35 mm",
         "settles": "FIT, CROWN-CLEAR, SHELL-FIT", "usd": 0.0},
        {"id": "SD-1", "what": "mid saddle pull-off: socket + bar stub on a stay offcut, pull the bar away from the stay",
         "pass": f">= {1.5 * ldm['fx']:.0f} N (1.5 x factored bar axial) without crack; band not slipping on the saddle",
         "settles": "saddle socket geometry, PAHT bearing", "usd": 0.0},
    ]


# ----------------------------------------------------------------------------- run
def analyse_frame(log=print) -> dict:
    """Stage 1 (own process): global passes + the BL-081 local rows on the B85 model + corrected bushing rows."""
    g85 = G85.cached("b85", CFG_B85, log=log)
    log("BL-081-format global on the B85 model (C6p included)")
    g = global_b81_format(log=log)
    cfg = {**BQ.CFG0, **CFG_B85}
    rows = global_rows(g85)
    rows += BL.hole_rows(g, cfg) + BL.gusset_rows(g, cfg) + BL.bolt_rows(g, cfg) + BL.crush_rows(g, cfg) + \
        BL.hip_rows(g, cfg) + BL.foot_rows(g, cfg) + BL.fairlead_rows(g, cfg)
    log("bushing rows (corrected)")
    rows += bushing_rows_85(g, g85, cfg)
    b81 = json.loads(BQ.REC_JSON.read_text())
    rows += [{**r, "basis": r["basis"] + " (B81 record; the spreader supports are unchanged)"} for r in b81["rows"] if r["item"] == "4"]
    return {"rows": rows, "members_util": g.get("members_util", {})}


def analyse_tee(log=print) -> dict:
    """Stage 2 (own process): the tee rows (solid FE), anodised case, preload sweep, B1 control."""
    g85 = G85.cached("b85", CFG_B85, log=log)
    tee = T.upper_tee_rows(g85) + T.mid_tee_rows(g85)
    anod = T.upper_tee_rows(g85, {"finish": "anodised"}) + T.mid_tee_rows(g85, {"finish": "anodised"})
    sweep = T.preload_sweep(g85)
    log("B81 as-built control (review 9 B1)")
    ctrl = T.b81_asbuilt_check(g85)
    T.release()
    return {"tee": tee, "anodised_tee_fatigue": {r["row"]: r["margin"] for r in anod if r["kind"] == "fatigue"},
            "preload_sweep": sweep, "b81_asbuilt": ctrl}


def analyse(log=print) -> dict:
    import subprocess
    t0 = time.time()
    for st in ("frame", "tee"):
        p = CACHE / f"stage_{st}.json"
        if not p.exists():
            subprocess.run([sys.executable, "-m", "huntkit.gendesign.bl085_report", "stage", st], check=True)
    fr = json.loads((CACHE / "stage_frame.json").read_text())
    te = json.loads((CACHE / "stage_tee.json").read_text())
    g85 = G85.cached("b85", CFG_B85, log=log)
    rows = fr["rows"] + te["tee"]
    strong = [r for r in rows if r.get("margin") is not None and r["kind"] != "info"]
    gov = min(strong, key=lambda r: r["margin"])
    tee_min = min((r for r in te["tee"] if r.get("margin") is not None), key=lambda r: r["margin"])
    return {"rows": rows, "min_margin": gov["margin"], "governing": gov["row"], "tee_min": tee_min["margin"],
            "tee_governing": tee_min["row"], "strong_pass": bool(gov["margin"] >= 1.0),
            "anodised_tee_fatigue": te["anodised_tee_fatigue"], "preload_sweep": te["preload_sweep"],
            "b81_asbuilt": te["b81_asbuilt"], "design_curve_sensitivity": design_curve_sensitivity(rows),
            "global": {"strength": g85["strength"], "buckling": g85["buckling"], "c6p": g85["c6p"],
                       "b81_c6p": json.loads((CACHE / "global_b81.json").read_text())["c6p"]
                       if (CACHE / "global_b81.json").exists() else None},
            "members_util": fr["members_util"], "seconds": round(time.time() - t0, 1)}


def run(log=print) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    pa = CACHE / "analysis.json"
    if pa.exists():
        an = json.loads(pa.read_text())
    else:
        an = BR._js(analyse(log=log))
        pa.write_text(json.dumps(an))
    log("parts, mass, cost")
    printed = P85.export(log=log)
    mass = P85.mass_table(printed)
    cost = P85.cost_table(mass, ship_zone=8)
    cost5 = P85.cost_table(mass, ship_zone=5)
    rec = {"ticket": "BL-085", "date": DATE, "design": "B85 = B81 + BL-085 tees", "cfg": T.CFG85,
           "basis": {"sn": T.sn_basis(), "fret_metal": T.CFG85["fret_metal"], "fret_poly": T.CFG85["fret_poly"],
                     "scatter": T.CFG85["scatter"], "finish": T.CFG85["finish"]},
           **{k: v for k, v in an.items() if k != "members_util"},
           "margins_table": margins_table(an["rows"]), "interference": P85.interference_check(),
           "printed": printed, "cut_list": P85.cut_list(), "mass": mass, "cost": cost, "cost_zone5": cost5,
           "proving": P85.proving()}
    rec["comparison"] = comparison(mass, cost)
    rec["comparison"][-1]["strong"] = "PASS" if rec["strong_pass"] else "FAIL"
    rec["coupons"] = coupons(rec)
    rec["cap_pass"] = cost["within_cap"]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (CACHE / "util.json").write_text(json.dumps(an.get("members_util", {})))
    rec["screens"] = screens(rec)
    REC_JSON.write_text(json.dumps(BR._js(rec), indent=1))
    write_md(rec)
    return rec


def margins_table(rows):
    tab = []
    for it in ITEMS:
        rs = [r for r in rows if r["item"] == it and r.get("margin") is not None and r["kind"] != "info"]
        for kind in ("strength", "fatigue", "joint", "creep"):
            ks = [r for r in rs if r["kind"] == kind]
            if ks:
                w = min(ks, key=lambda r: r["margin"])
                tab.append({"item": it, "kind": kind, "margin": round(float(w["margin"]), 3), "row": w["row"]})
    return tab


def preload_window(sweep) -> tuple:
    """Preload per bolt (N) where min(slip, static, fatigue) crosses 1.0, linear between sweep points."""
    xs = [x["Fb"] for x in sweep]
    ys = [min(x["slip"], x["static"], x["fatigue"]) for x in sweep]
    lo = hi = None
    for i in range(len(xs) - 1):
        a, b = ys[i] - 1, ys[i + 1] - 1
        if a < 0 <= b and lo is None:
            lo = xs[i] + (xs[i + 1] - xs[i]) * (-a) / (b - a)
        if a >= 0 > b:
            hi = xs[i] + (xs[i + 1] - xs[i]) * a / (a - b)
    return lo, hi


# ----------------------------------------------------------------------------- screens
def _render_joint(ax, title):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    mp = P85.metal_parts()
    parts = [(mp["stay"], "#b8bec6"), (mp["shells"], "#257de0"), (mp["bar"], "#9aa3ad")]
    parts += [(b, "#f47230") for b in mp["backers"]]
    parts += [(b, "#333333") for b in mp["bolts"]]
    parts += [(P85.stay_top_collar_85(), "#00a888"), (P85.bar_saddle_plug(), "#00a888")]
    for m, col in parts:
        tm = P85.BP.to_trimesh(m)
        tri = tm.vertices[tm.faces]
        n = tm.face_normals
        shade = 0.55 + 0.45 * np.clip(n @ np.array([0.4, -0.6, 0.7]) / 1.0, 0, 1)
        import matplotlib.colors as mc
        base = np.array(mc.to_rgb(col))
        fc = np.clip(base[None, :] * shade[:, None], 0, 1)
        pc = Poly3DCollection(tri, facecolors=fc, edgecolors="none", linewidths=0, zsort="max")
        ax.add_collection3d(pc)
    ax.set_xlim(40, 160)
    ax.set_ylim(-60, 60)
    ax.set_zlim(410, 560)
    ax.set_box_aspect((120, 120, 150))
    ax.view_init(elev=18, azim=-62)
    ax.set_axis_off()
    ax.set_title(title, fontsize=12)


def screens(rec) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    blue, orange, green, red, grey = "#257de0", "#f47230", "#0aac23", "#d03b3b", "#666666"
    # 1 joint render + labels
    fig = plt.figure(figsize=(9, 10), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    _render_joint(ax, "B85 upper tee (right side), z 410-560 mm")
    notes = ["stay 1 x .065, 545 mm: 15 mm bare tube above the shells (free end, B1)",
             "blue: 100 mm half-shells, 1-1/4 x .120 6061 (z 430-530)",
             "orange: 2 pairs of 3/16 x 1 backers, 4 x M5 at 1.5 N m (+/-30 % ok)",
             "bar end: 2 x M5 in double shear + crush sleeves (metal path, M8)",
             "green: printed stay-top collar (5 mm gap) + bar saddle plug",
             "mid tee (not shown): printed pinned saddle + 9 mm band, no metal clamp"]
    fig.text(0.04, 0.02, "\n".join(notes), fontsize=10.5, va="bottom", color="#191919")
    p = SCREENS / f"{SHOT}1.png"
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    out.append(str(p.relative_to(BQ.REPO)))
    # 2 utilisation: tee rows at the scatter limits + preload window
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 11), dpi=110, gridspec_kw={"height_ratios": [1.25, 1]})
    sel = [r for r in rec["rows"] if r.get("tee") in ("upper", "mid") and r.get("margin") is not None]
    sel += [r for r in rec["rows"] if r["item"] == "3" and "bushing" in r["row"] and r.get("margin") is not None]
    sel = [r for r in sel if r["kind"] != "info"]
    seen, rows = set(), []
    for r in sorted(sel, key=lambda r: r["margin"]):
        if r["row"] not in seen:
            seen.add(r["row"])
            rows.append(r)
    rows = rows[:14][::-1]
    labels = [r["row"].replace("upper tee: ", "U: ").replace("mid tee (pinned saddle): ", "M: ")[:62] for r in rows]
    vals = [min(r["margin"], 4.0) for r in rows]
    cols = [green if v >= 1.0 else red for v in vals]
    a1.barh(range(len(rows)), vals, color=cols, height=0.6)
    a1.axvline(1.0, color="#191919", lw=1.2)
    a1.set_yticks(range(len(rows)))
    a1.set_yticklabels(labels, fontsize=8.5)
    for i, v in enumerate(vals):
        a1.text(v + 0.03, i, f"{rows[i]['margin']:.2f}", va="center", fontsize=8.5, color="#191919")
    a1.set_xlabel("margin (allowable / value); 1.0 = goal")
    a1.set_title(f"B85 tee + bushing rows, lowest 14 (design S-N + fretting, preload +/-30 %)\n"
                 f"frame min {rec['min_margin']:.2f}: upper-tee wall at limit, +30 % preload", fontsize=10.5)
    a1.spines[["top", "right"]].set_visible(False)
    sw = rec["preload_sweep"]
    f = [s["factor"] * T.CFG85["Fb_nom"] for s in sw]
    for k, col, lab in (("slip", blue, "slip (needs high preload)"), ("static", orange, "wall static (needs low)"),
                        ("fatigue", "#6a4ce2", "wall fatigue, design + fretting")):
        a2.plot(f, [s[k] for s in sw], color=col, lw=2, marker="o", ms=5, label=lab)
    a2.axhline(1.0, color="#191919", lw=1)
    lo, hi = T.CFG85["Fb_nom"] * (1 - T.CFG85["scatter"]), T.CFG85["Fb_nom"] * (1 + T.CFG85["scatter"])
    a2.axvspan(lo, hi, color=green, alpha=0.12, label="+/-30 % scatter band")
    a2.set_xlabel("preload per M5 bolt (N); 4 bolts per tee")
    a2.set_ylabel("margin")
    a2.set_ylim(0.6, 3.0)
    a2.legend(fontsize=9, frameon=False, loc="upper center")
    wl, wh = preload_window(sw)
    a2.set_title(f"Upper-tee preload window: all rows >= 1 from {wl:.0f} to {wh:.0f} N per bolt\n"
                 f"(nominal {T.CFG85['Fb_nom']:.0f} N = {T.CFG85['torque_nm']} N m; green band = +/-30 %)", fontsize=10.5)
    a2.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = SCREENS / f"{SHOT}2.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p.relative_to(BQ.REPO)))
    # 3 mass / cost comparison
    comp = rec["comparison"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 6.5), dpi=110, sharey=True)
    names = [c["option"].replace(" (this record)", "") for c in comp][::-1]
    ms = [c["body_g"] for c in comp][::-1]
    us = [c["usd"] for c in comp][::-1]
    st = [c["strong"] for c in comp][::-1]
    cc = [green if s == "PASS" else grey for s in st]
    a1.barh(names, ms, color=cc, height=0.6)
    for i, v in enumerate(ms):
        a1.text(v + 20, i, f"{v:.0f} g ({v / 453.6:.2f} lb)", va="center", fontsize=9)
    a1.set_xlim(0, 2700)
    a1.set_xlabel("frame body mass (g)")
    a1.set_title("Mass (green = Strong PASS, grey = FAIL)", fontsize=10.5)
    a2.barh(names, us, color=[green if (s == "PASS" and u <= 150) else (orange if s == "PASS" else grey) for s, u in zip(st, us)], height=0.6)
    a2.axvline(150, color=red, lw=1.5)
    a2.text(153, -0.45, "cap USD 150", color=red, fontsize=9)
    for i, v in enumerate(us):
        a2.text(v + 3, i, f"USD {v:.0f}", va="center", fontsize=9)
    a2.set_xlim(0, 300)
    a2.set_xlabel("landed USD per frame (incl. shipping)")
    a2.set_title("Cost (orange = strong but over cap)", fontsize=10.5)
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"BL-085: B85 {rec['mass']['body_g']:.0f} g, USD {rec['cost']['per_frame_usd']:.2f} (zone 8 shipping), "
                 f"USD {rec['cost_zone5']['per_frame_usd']:.2f} (zone 5)", fontsize=11)
    fig.tight_layout()
    p = SCREENS / f"{SHOT}3.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p.relative_to(BQ.REPO)))
    for s in out:
        import os
        assert os.path.getsize(BQ.REPO / s) < 1.5e6, s
    return out


# ----------------------------------------------------------------------------- markdown
def _f(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def write_md(rec: dict) -> None:
    w = []
    a = w.append
    c = rec["cfg"]
    m, co, c5 = rec["mass"], rec["cost"], rec["cost_zone5"]
    up = {r["row"]: r for r in rec["rows"] if r.get("tee") == "upper"}
    mid = {r["row"]: r for r in rec["rows"] if r.get("tee") == "mid"}
    ctrl = rec["b81_asbuilt"]
    a("# BL-085: preload-tolerant upper and mid tees for the aluminium ladder (B85)\n")
    a(f"Owner: structural-fea-engineer, {DATE}. Answers review 9 (`designs/pack_5200/analysis/review_20261125_ninth.md`) "
      "B1-B4, M1, M2, M5, M6, M7, M8. Code: `huntkit/gendesign/bl085_global.py` (full envelope incl. C6p, stay forces at the "
      "tees), `bl085_tee.py` (tee design, solid FE, design S-N), `bl085_parts.py` (STL, mass, cost), `bl085_report.py` (this "
      "record). BL-077 / 079 / 081 / 083 files and the kit generators are not edited. Numbers: [bl085.json](bl085.json). "
      "Tests: `tests/test_bl085_tees.py`. Units mm, N, MPa, g, USD (imperial in brackets).\n")
    a("## 0. Answer\n")
    wl, wh = preload_window(rec["preload_sweep"])
    a(f"- **Strong (tees, on the review's basis): {'PASS' if rec['tee_min'] >= 1 else 'FAIL'}.** Lowest tee row {rec['tee_min']:.2f} ({rec['tee_governing']}). "
      f"Frame minimum over every row {rec['min_margin']:.2f} ({rec['governing']}). Every tee row is on the as-built geometry "
      "(real free end, no part collision: interference volumes 0), on the Yahr **design** curve with a fretting allowance, at "
      "both preload scatter limits (+/-30 %), with C6p in the envelope.")
    a(f"- **Mass {m['body_g']:.0f} g ({m['body_g'] / 453.6:.2f} lb) body**, {m['vs_b81_g']:+.0f} g vs B81.")
    a(f"- **Cost USD {co['per_frame_usd']:.2f} per frame landed (FedEx zone 8 + fuel), USD {c5['per_frame_usd']:.2f} at zone 5.** "
      f"{'Inside' if co['within_cap'] else 'Over'} the USD 150 cap at the conservative zone; "
      f"{'inside' if c5['within_cap'] else 'over'} at zone 5. Price sources: tube, flat, sheet and shell stock read on the "
      "Speedy pages 2026-11-25; screws, bands and angle from search snippets (secondary); crush-sleeve stock still the "
      "BL-082 USD 3 ASSUMPTION; shipping from a secondary FedEx Ground Economy table because Speedy publishes no rates. "
      "**Get the Speedy checkout shipping quote before calling the cap.**")
    a(f"- **Verdict:** B85 {'passes' if rec['strong_pass'] else 'FAILS'} Strong; it passes the USD 150 cap only if shipping to the owner is <= USD "
      f"{150 - (co['per_frame_usd'] - co['lines'][-1]['usd']):.2f} (FedEx zone 5 or nearer does at the booked +20 % fuel; "
      "zones 6-8 do not). "
      "It is the cheapest strong option found.")
    a("- **Not gated but reported:** on the design curve the BL-081 non-tee fatigue rows (gusset-bolt holes, rung ties, hip "
      "post) drop to 0.6-0.9 (section 6). The brief scoped the design curve to the tees; applying it frame-wide is an "
      "orchestrator decision and would fail every B-family frame (KF-1 coupons decide).")
    a("- **D83 is out of play** (USD 260 landed, the pan alone USD 126): no 5052 record or z85 edge fix was made (review M3 / M4 "
      "stay open for D83 only).\n")
    a("## 1. The new tees\n")
    a("| | B81 / B81-Lb (review 9) | B85 (this record) | review item |")
    a("|---|---|---|---|")
    a("| stay length | 530 mm; 50 mm shell z 495-545 overhangs the end by 15 mm and collides with the collar | **545 mm**; shells z 430-530, "
      "**15 mm bare tube above**, collar z 535-548 (5 mm gap) | B1 |")
    a(f"| upper clamp | 2 x M5 at 2000 N on 50 mm shells | **100 mm shells, 2 backer pairs (3/16 x 1), 4 x M5 at {c['Fb_nom']:.0f} N "
      f"({c['torque_nm']} N m)** | B1, B3 |")
    a("| bar to tee | printed socket, M5 bearing in PAHT | **2 x M5 in double shear through the upper backers, 1/8 in spacers, "
      "crush sleeves in the bar**; printed plug in compression only | M8 |")
    a("| mid tee | metal clamp at the stay's worst beam stress (fatigue 1.00, unchecked) | **pinned printed saddle + 9 mm band, no "
      "metal clamp**; carries bar axial only | M1 |")
    a("| fatigue basis | Yahr mean, no fretting | **Yahr design curve (71.1 MPa at 1e5) x fretting 0.6 metal / 0.85 polymer** | B4 |")
    a(f"| preload | one value, window -16 / +6 % | **every row at -30 / 0 / +30 %; every row >= 1 from {wl:.0f} to {wh:.0f} N "
      f"per bolt ({100 * (wl / c['Fb_nom'] - 1):+.0f} / {100 * (wh / c['Fb_nom'] - 1):+.0f} %)** | B3 |")
    a("| envelope | C6p skipped | **C6p included** (stays 1.767 -> 1.743, as review 9) | M2 |")
    a("| finish | not specified, switch not wired | **stays, shells, backers bare 6061 (no anodise)**; anodised case reported | M5 |\n")
    a("Why each choice: the global run (section 3) puts the stay's walk beam stress at **72.6 MPa at z 330** (meat walk) and "
      "only **9.7 MPa at z 520**. At z 330 a metal clamp edge (Kt 2, fretting 0.6, design curve) fails whatever the preload, "
      "so the mid tee carries no moment and has no metal on the stay; the frame loses <= 2.5 % on any member row by it (bars 1.32 -> 1.29). At "
      "z 520 the beam stress is low, so a clamp works if its preload hoop stays moderate: the 100 mm shells roughly halve the hoop per "
      "newton of the 50 mm B81 shells, and the friction need is set by the side-hill torque about the stay (12.6 N m), not by "
      "the pawl. The end effect is gone with 15 mm of tube above the shells (solid FE: hoop per kN 23.4 at 15 mm vs 26.7 flush "
      "vs 23.3 continuous; couple 68.5 / 99.0 / 65.8).\n")
    a("## 2. Tee rows (all; margin = allowable / value)\n")
    a("| tee | row | kind | margin | basis |")
    a("|---|---|---|---:|---|")
    for r in rec["rows"]:
        if r.get("tee"):
            a(f"| {r['tee']} | {r['row']} | {r['kind']} | {_f(r['margin'])} | {r['basis'][:230]} |")
    a("")
    a("Anodised (Type II, ANODISE-FAT 0.7) fatigue margins: " + "; ".join(
        f"{k}: {v:.2f}" for k, v in rec["anodised_tee_fatigue"].items()) + ". The mid saddle fails anodised, so **the stays "
      "must stay bare** (cut list note; wax for squeak), consistent with the alu_6061_t6 record's ANODISE-FAT note.\n")
    a("Preload window (upper tee, nominal margins vs preload per bolt):\n")
    a("| N per bolt | slip | wall static | wall fatigue (design + fretting) |")
    a("|---:|---:|---:|---:|")
    for s in rec["preload_sweep"]:
        a(f"| {s['Fb']:.0f} | {s['slip']:.2f} | {s['static']:.2f} | {s['fatigue']:.2f} |")
    a(f"\nB1 control on this code (B81 shell on 35 mm of tube at the free end, 2 x 2000 N, BL-081 load basis): static "
      f"{ctrl['static_margin']:.2f}, fatigue mean {ctrl['fatigue_mean']:.2f}, design + fretting {ctrl['fatigue_design_fret']:.2f} "
      f"(review 9: 0.65 / 0.67).\n")
    a("## 3. Frame margins (minimum per check item and kind, B85 model, envelope incl. C6p)\n")
    a("| # | check | kind | margin | governing row |")
    a("|---|---|---|---:|---|")
    for t in rec["margins_table"]:
        a(f"| {t['item']} | {ITEMS.get(t['item'], '').split(' (')[0]} | {t['kind']} | {t['margin']:.2f} | {t['row'][:100]} |")
    gl = rec["global"]
    a(f"\nGlobal (B85): stays {gl['strength']['stays']['margin']:.3f} ({gl['strength']['stays']['case']}), bars "
      f"{gl['strength']['bars']['margin']:.3f}, buckling {gl['buckling']['margin']:.2f}. C6p governs the stays (1.743; review 9 "
      "found the same). Non-tee rows are on the BL-081 basis (mean curve) except the bushing rows, which are corrected (F1).\n")
    a("## 4. Mass and cost\n")
    a("| item | g |")
    a("|---|---:|")
    for k, v in m["rows"].items():
        a(f"| {k} | {v:.1f} |")
    a(f"| **body** | **{m['body_g']:.1f}** ({m['body_g'] / 453.6:.2f} lb) |\n")
    a("| line | USD | source |")
    a("|---|---:|---|")
    for l in co["lines"]:
        a(f"| {l['item']} | {l['usd']:.2f} | {l['source'][:200]} |")
    a(f"| **per frame (zone 8)** | **{co['per_frame_usd']:.2f}** | cap 150 |")
    a(f"| per frame (zone 5) | {c5['per_frame_usd']:.2f} | |\n")
    a(f"Proving (new joint coupons, first frame): USD {rec['proving']['total_usd']:.2f}; no new tool over USD 50 (a 1-3/8 in tubing "
      "cutter USD 15; torque is set with the existing hanging scale on a marked 50 mm hex-key lever: 30 N = 1.5 N m).\n")
    a("Comparison (Strong on the review-9 basis; USD landed with shipping):\n")
    a("| option | Strong | body g (lb) | USD | note |")
    a("|---|---|---:|---:|---|")
    for cc in rec["comparison"]:
        a(f"| {cc['option']} | {cc['strong']} | {cc['body_g']:.0f} ({cc['body_g'] / 453.6:.2f}) | {cc['usd']:.2f} | {cc['note']} |")
    a("")
    a("## 5. Coupons for the new joint (pass lines)\n")
    a("| id | what | pass | settles |")
    a("|---|---|---|---|")
    for cp in rec["coupons"]:
        a(f"| {cp['id']} | {cp['what']} | {cp['pass']} | {cp['settles']} |")
    a("\nOrder: OV-2 (c) before sawing the shells; CL-T and BS-T before the first frame is assembled; KF-T and KF-S in "
      "parallel with BL-081 KF-1 on the T5 rig. **No build pack until KF-T and KF-S pass.**\n")
    a("## 6. Findings beyond review 9, and the design-curve sensitivity\n")
    a("- **F1 (BL-081 code, not edited):** `bl081_local.clamp_rows` and `bushing_rows` take the stay beam stress as Fy / sf, which "
      "is the stress at the case's LIMIT load, and then treat it as factored (walk = / 3 x 1.6). For the governing meat / "
      "tall cases that is 1.5 x low. It also uses the worst stay stress in the frame at the upper tee (91 MPa vs 20-89 MPa "
      "real at z 520, 9.7 MPa walk). BL-085 reads the stay forces at the tees from the global model (`bl085_global`) and "
      "corrects the bushing rows.")
    a("- **F2:** the BL-081 tee clamp bolts are M5 x 45 for a 44.5 mm grip (shell OD + two 1/4 backers): no thread for the nut. "
      "B85 uses M5 x 50 on a 41.3 mm grip.")
    a("- **F3:** Speedy lists no 1-1/4 x .125 tube; its 1-1/4 x .120 (p-4573) has a 1.010 in bore. B85 books that stock, bounds "
      "the unconformed fit by a crown-bearing (cos) jaw field in every row (SHELL-FIT), and adds the shell bending to close the "
      "0.13 mm gap. The BL-081 SHELL-PRICE (USD 15) is replaced by the read price.")
    a("- **F4:** the BL-081 fatigue walk was the bag carry only; the meat walk (meat_straps x 1.6 / 2.0) gives 7 x higher stay "
      "stress at z 330 and is the mission load. B85 takes the envelope (ASSUMPTION WALK-ENV).\n")
    a("Non-tee metal fatigue rows re-scaled to the design curve (not gated):\n")
    a("| row | mean basis | design curve |")
    a("|---|---:|---:|")
    for s in rec["design_curve_sensitivity"][:10]:
        a(f"| {s['row']} | {s['mean_margin']:.2f} | {s['design_margin']:.2f} |")
    a("")
    a("## 7. Parts and files\n")
    for k, v in rec["printed"].items():
        a(f"- printed `{v['file']}` (+ `_L`): {v['mass_g_each']} g x {v['count']}, watertight {v['watertight']}")
    a(f"- interference check (manifold boolean): {rec['interference']}")
    a("- cut list: `bl085.json` `cut_list` (stays 545 mm, NO hole above z 160; shells 100 mm from p-4573; backers 4 x 80 + "
      "4 x 55 of 3/16 x 1; 8 spacer washers 1/8 x 1 x 14; 4 extra crush sleeves in the upper bar).")
    a("- finish note for the cut list: **stays, shells, backers bare 6061, no anodise; wax the stays.** Galvanic: A4 screws and "
      "the stainless band on bare 6061 are a mild couple (wet); grease the screw shanks (tef-gel class) at assembly.\n")
    a("## 8. Assumptions (each with the test that settles it)\n")
    for s in [
        "ASSUMPTION FRET-METAL 0.6: fretting knock-down on the allowable at a metal clamp edge (middle of the 0.5-0.7 range "
        "review 9 quotes), on top of Kt 2 on the beam stress. KF-T.",
        "ASSUMPTION FRET-POLY 0.85 and SADDLE-KT 1.15: PAHT saddle / UHMWPE bushing on bare 6061, no metal-on-metal slip. KF-S.",
        "ASSUMPTION SCATTER +/-30 %: torque-controlled M5 (+/-25 %) plus K uncertainty; set with the hanging scale on a 50 mm "
        "lever. CL-T measures K-and-mu together at the low limit.",
        "ASSUMPTION WALK-ENV: fatigue walk = envelope of static carry x 1.6 and meat_straps x 1.6 / 2.0.",
        "ASSUMPTION SADDLE-K: mid tee link stiff across the stay, 200 N/mm along it, rotations free. SD-1, T1 deflection.",
        "ASSUMPTION GEOM-85: the global model keeps the B81 nodes (stay 530, tees 520 / 330, IM3 at 520); the 15 mm stay "
        "extension and the IM3 loop on the shells (z 466-494) are local changes. T1 deflection band.",
        "ASSUMPTION SHELL-FIT: p-4573 shells (ID 1.010) conform under preload; bounded by the crown-bearing field. OV-2 (c), CL-T.",
        "ASSUMPTION CROWN-CLEAR: the stay-top collar 15 mm higher still clears the crown corner at the 15 in torso. OV-2 (b).",
        "ASSUMPTION SCREW-LEN: all M5 lengths at the 35 mm A4 each price. Quote at order.",
        "ASSUMPTION FUEL-20: +20 % on the FedEx Ground Economy list for fuel / residential. Speedy checkout quote.",
        "Carried from BL-081 / BL-082: MU 0.15 wet, EMBED 0.9, CLAMP-K, GAP-K, crush sleeves, PAHT hot/wet basis.",
    ]:
        a(f"- {s}")
    a("\n## 9. Screens\n")
    for s in rec["screens"]:
        a(f"- `{s}`")
    REC_MD.write_text("\n".join(w) + "\n")


if __name__ == "__main__":     # pragma: no cover
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        run()
    elif cmd == "stage":
        CACHE.mkdir(parents=True, exist_ok=True)
        fn = {"frame": analyse_frame, "tee": analyse_tee}[sys.argv[2]]
        (CACHE / f"stage_{sys.argv[2]}.json").write_text(json.dumps(BR._js(fn())))
    elif cmd == "md":
        rec = json.loads(REC_JSON.read_text())
        rec["screens"] = screens(rec)
        write_md(rec)
