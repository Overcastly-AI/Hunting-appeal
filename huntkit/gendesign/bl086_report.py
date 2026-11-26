"""BL-086 driver: B86 (B85 with the non-tee details reworked) on the full HA-LS-1 rev C envelope incl. C6p, every metal
fatigue row on the Yahr DESIGN S-N curve with the BL-085 fretting allowances, walk = bag-carry / meat-carry envelope;
mass, landed cost (FedEx zone 5 and 8), comparison with H1c / B85, coupons, screens and the record
``designs/pack_5200/iter2/frame_b86/bl086.{json,md}``.

Stages run in their own processes (the solid FE holds GBs): ``units`` (ring / saddle / bushing unit fields, one per
process), ``frame`` (global + local rows), ``tee`` (BL-085 tee rows re-run on the B86 global).
Run: ``python -m huntkit.gendesign.bl086_report run``; ``... md`` rewrites the Markdown and screens from the JSON.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl081_report as BR
from huntkit.gendesign import bl086_global as G
from huntkit.gendesign import bl086_local as L
from huntkit.gendesign import bl086_parts as P

CACHE = G.CACHE
OUTDIR = P.OUTDIR
REC_JSON = OUTDIR / "bl086.json"
REC_MD = OUTDIR / "bl086.md"
SCREENS = BQ.SCREENS
SHOT = "20261126_bl086_"
DATE = "2026-11-26"
CAP = 150.0
MASS_LIMIT = 2100.0
ITEMS = {**BR.ITEMS, "3": "Stays: gusset-bolt holes, rung plugs and the crown-leg bushing stations",
         "5": "Upper / mid tees (BL-085 details, re-run on the B86 global)",
         "6": "Hip post, front-leg doublers and the ties to the rungs",
         "G": "Global model, full envelope incl. C6p"}
UNIT_JOBS = [("ring", ("t1000_065", 50.0, 65.0)), ("ring", ("t1000_065", 20.0, 65.0)), ("ring", ("t1000_065", 26.0, 60.0)),
             ("ring", ("t1000_065", 25.0, 80.0)), ("saddle", ("t1000_065", 25.0, 80.0)), ("bush", ("t1000_065", 110.0, 30.0)),
             ("bush", ("t1000_065", 70.0, 30.0))]
# B85 non-tee rows on the design curve + walk envelope (BL-086 baseline run, before any change): the rows the
# orchestrator named and the others the frame-wide basis exposed
BASELINE_B85 = [("stay z135 gusset bolt (L)", 0.631), ("rung z155 x-30 hip tie bolt", 0.711),
                ("rung z85 x+30 hip tie bolt", 0.802), ("stay z105 gusset bolt (L)", 0.810),
                ("front angle leg: fatigue at the mount holes", 0.843),
                ("stay at the leg-end bushing (design + polymer contact, 70 mm)", 0.974)]


# ----------------------------------------------------------------------------- stages
def stage_units(job: str, args) -> None:
    if job == "ring":
        L.ring_unit(*args)
    elif job == "saddle":
        L.saddle_hole_units(*args)
    elif job == "bush":
        L.bush_units(*args)


def analyse_frame(log=print) -> dict:
    cfg = L.cfg86()
    g = G.cached("b86", cfg, log=log)
    rows = []
    for k, v in g["strength"].items():
        rows.append({"item": "G", "row": f"{k}: member strength (beam, all cases incl. C6p)", "kind": "strength",
                     "value": v["sf"], "allow": v["required"], "margin": v["margin"], "basis": f"{v['member']} {v['case']}"})
    b = g["buckling"]
    rows.append({"item": "G", "row": "frame buckling eigenvalue / (1.5 x case factor), incl. C6p", "kind": "strength",
                 "value": b["eigen"], "allow": None, "margin": b["margin"], "basis": b["case"]})
    rows += L.hole_rows_86(g, cfg)
    with L.design_curve():
        rows += BL.gusset_rows(g, cfg) + BL.bolt_rows(g, cfg) + BL.crush_rows(g, cfg) + BL.foot_rows(g, cfg)
        log("fairlead rows (solid FE clamp units)")
        rows += BL.fairlead_rows(g, cfg)
    rows += L.hip_rows_86(g, cfg) + L.tie_saddle_rows(g, cfg) + L.plug_rows(g, cfg) + L.bushing_rows_86(g, cfg)
    b81 = json.loads(BQ.REC_JSON.read_text())
    rows += [{**r, "basis": r["basis"] + " (B81 record; spreader supports unchanged)"} for r in b81["rows"] if r["item"] == "4"]
    for r in rows:
        if r["kind"] == "fatigue" and r.get("allow") and abs(r["allow"] - L.smax_r0(None)) < 0.5:
            r["basis"] += " [design curve]"
    return {"rows": rows, "members_util": g["members_util"], "global": {"strength": g["strength"], "buckling": g["buckling"],
                                                                         "c6p": g["c6p"], "deflection": g["deflection"]}}


def global85_format(log=print) -> dict:
    """BL-085-format global (tee links, stay forces at the tees, walk envelope) on the B86 model."""
    from huntkit.gendesign import bl085_global as G85
    p = CACHE / "global85fmt_b86.json"
    if p.exists():
        return json.loads(p.read_text())
    old = G85.build
    G85.build = lambda cfg, torso: G.build(cfg, torso)
    try:
        g = G85.evaluate(L.cfg86(), log=log)
    finally:
        G85.build = old
    p.write_text(json.dumps(g, default=float))
    return json.loads(p.read_text())


def analyse_tee(log=print) -> dict:
    from huntkit.gendesign import bl085_tee as T
    g = global85_format(log=log)
    tee = T.upper_tee_rows(g) + T.mid_tee_rows(g)
    sweep = T.preload_sweep(g)
    T.release()
    return {"tee": tee, "preload_sweep": sweep}


def _stage(name, *args):
    p = CACHE / f"stage_{name}.json"
    if not p.exists():
        subprocess.run([sys.executable, "-m", "huntkit.gendesign.bl086_report", "stage", name, *map(str, args)], check=True)
    return json.loads(p.read_text())


def analyse(log=print) -> dict:
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    for job, args in UNIT_JOBS:
        subprocess.run([sys.executable, "-m", "huntkit.gendesign.bl086_report", "unit", job, *map(str, args)], check=True)
    fr = _stage("frame")
    te = _stage("tee")
    rows = fr["rows"] + te["tee"]
    gated = [r for r in rows if r.get("margin") is not None and r["kind"] != "info"]
    gov = min(gated, key=lambda r: r["margin"])
    return {"rows": rows, "min_margin": gov["margin"], "governing": gov["row"], "strong_pass": bool(gov["margin"] >= 1.0),
            "preload_sweep": te["preload_sweep"], "global": fr["global"], "members_util": fr["members_util"],
            "bond_check": L.bond_check(), "seconds": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------- record pieces
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


def fixed_rows(rows) -> list[dict]:
    """The B85 failures on the design curve and what each became in B86."""
    def m(pred):
        rs = [r for r in rows if pred(r) and r.get("margin") is not None and r["kind"] != "info"]
        r = min(rs, key=lambda r: r["margin"])
        return r["margin"], r["row"]
    pairs = [
        ("stay z135 gusset bolt (L)", lambda r: r["row"].startswith("stay z95 gusset bolt") and r["kind"] == "fatigue",
         "holes moved to z 78 / 95 (out of the stay's bending peak)"),
        ("stay z105 gusset bolt (L)", lambda r: r["row"].startswith("stay z78 gusset bolt") and r["kind"] == "fatigue",
         "z 78 (15 MPa walk at the hole fibre)"),
        ("rung z155 x-30 hip tie bolt", lambda r: r["row"].startswith("upper rung under the printed tie saddle") and r["kind"] == "fatigue",
         "no hole: printed compression saddle (tie force is compression in every case)"),
        ("rung z85 x+30 hip tie bolt", lambda r: "hip tie bolt (saddle washer)" in r["row"] and r["kind"] == "fatigue",
         "printed 25 mm x +/-80 deg saddle washer behind the rung, snug bolt (6061 washer tried: edge fretting 0.94)"),
        ("front angle leg: fatigue at the mount holes", lambda r: r["row"] == "front angle leg: fatigue at the mount holes",
         "2 x 1 x 1/8 doubler strips under the Ti mount"),
        ("stay at the leg-end bushing (design + polymer contact, 70 mm)",
         lambda r: r["row"].startswith("stay at the leg-end bushing") and r["kind"] == "fatigue", "leg-end bushing 70 -> 110 mm"),
    ]
    out = []
    base = dict(BASELINE_B85)
    for name, pred, how in pairs:
        mg, row = m(pred)
        out.append({"b85_row": name, "b85_design": base[name], "b86_row": row, "b86": round(mg, 3), "fix": how})
    return out


def comparison(mass, cost, cost5, strong) -> list[dict]:
    from huntkit.gendesign.bl080_metal_frame import H1C
    b85 = json.loads((BQ.REPO / "designs/pack_5200/iter2/frame_b85/bl085.json").read_text())
    return [
        {"option": "H1c (PAHT)", "body_g": H1C["body_g"], "usd8": H1C["usd"], "usd5": None, "strong": "FAIL",
         "note": "two PAHT joints below goal (BL-077)"},
        {"option": "B85", "body_g": b85["mass"]["body_g"], "usd8": b85["cost"]["per_frame_usd"],
         "usd5": b85["cost_zone5"]["per_frame_usd"], "strong": "FAIL",
         "note": "design curve frame-wide: stay z135 0.63, rung ties 0.71 / 0.80, front leg 0.84, bushing 0.97"},
        {"option": "B86 (this record)", "body_g": mass["body_g"], "usd8": cost["per_frame_usd"], "usd5": cost5["per_frame_usd"],
         "strong": "PASS" if strong else "FAIL", "note": "every row on the design curve, walk envelope, C6p"},
    ]


def coupons(rec) -> list[dict]:
    rows = {r["row"]: r for r in rec["rows"]}

    def val(prefix, kind="fatigue"):
        return min((r for r in rec["rows"] if r["row"].startswith(prefix) and r["kind"] == kind), key=lambda r: r["margin"])
    ts = val("upper rung under the printed tie saddle")
    lt = val("rung z85 x-30 hip tie bolt (saddle washer)")
    pl = val("stay at the z 155 rung plug")
    return [
        {"id": "KF-TS", "what": "upper-tie saddle on a 300 mm 1 x .065 rung offcut in 4-point bending on the T5 rig (saddle in the "
         "constant-moment span, pushed by a post-leg offcut through a load cell at the tie force), R 0.1, 1.2 x walk: rung "
         f"S_max at the saddle {1.2 * ts['value'] / L.KT_POLY:.0f} MPa nominal + tie push 500 N, n 3, 2e5 cycles",
         "pass": "no crack at the saddle edges (dye penetrant); saddle not cracked or creeping > 0.3 mm (dial gauge)",
         "settles": "SADDLE-KT 1.15 / FRET-POLY 0.85 on the rung, TIE-SADDLE-K"},
        {"id": "KF-LT", "what": "lower-tie joint coupon: 300 mm rung offcut with the D5.3 hole, crush sleeve, coped 3/4 spacer, "
         "M5 snug at 0.5 N m + locknut and the printed 25 mm saddle washer + fender washer behind; 4-point bending at 1.2 x the walk rung moment with the tie pull "
         "500 N (1.2 x 417) cycled in phase, R 0.1, n 3, 2e5 cycles",
         "pass": "no crack at the bore or under the saddle-washer edges (dye penetrant), no fretting track > 0.5 mm",
         "settles": f"saddle-washer units ({lt['margin']:.2f} on the design curve), SADDLE-KT / FRET-POLY under the printed saddle, SNUG-LT (locknut holds)"},
        {"id": "KF-P", "what": "upper rung plug on a 400 mm stay offcut: 4-point bending at 1.2 x the stay walk stress at z 155 with the "
         "printed 50 mm plug head pressed on by 1.2 x 403 N in phase, R 0.1, n 3, 2e5 cycles",
         "pass": "no crack under or beside the plug head; head not cracked",
         "settles": f"plug ring units + SADDLE-KT ({pl['margin']:.2f})"},
        {"id": "KF-1 (B81, re-targeted)", "what": "stay hole coupon at z 95: as BL-081 KF-1 but with the gusset plates clamped as "
         "built (crush sleeve, 1.5 N m) and the walk stress at the hole fibre x 1.2 (26 -> 31 MPa nominal), R 0.1, n 3, 2e5",
         "pass": "no crack at the bores or at the plate contact line (dye penetrant)",
         "settles": "open-hole Kt on the design curve with no fretting knock-down at a crush-sleeved hole (ASSUMPTION FRET-HOLE)"},
        {"id": "FL-D", "what": "front-leg coupon: 90 mm angle offcut + doubler strip + 3 mount bolts, the leg strip loaded in bending "
         "by the Ti-mount couple on a lever, 1.2 x walk couple, R 0.1, 2e5 cycles; then static to the factored couple",
         "pass": "no crack at the mount holes of the leg or strip; no permanent set > 0.2 mm after the factored couple",
         "settles": "DOUBLER-SHARE (stiffness share, no composite action)"},
        {"id": "OV-3", "what": "fit-up: (a) both post stems notched clear of the rungs (feeler >= 0.5 mm); (b) upper-tie saddle snapped "
         "on (no rattle, no gap > 0.2 mm under a 50 N push); (c) plug head seated between the gusset "
         "plates (no plate lift > 0.1 mm); (d) leg-end bushing 110 mm slides the full torso travel without touching the z 95 "
         "crush sleeve",
         "pass": "all four", "settles": "geometry of the new details (STL interference check)"},
    ]


# ----------------------------------------------------------------------------- run
def run(log=print) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    pa = CACHE / "analysis.json"
    if pa.exists():
        an = json.loads(pa.read_text())
    else:
        an = BR._js(analyse(log=log))
        pa.write_text(json.dumps(an))
    printed = P.export(log=log)
    mass = P.mass_table(printed)
    cost = P.cost_table(mass, ship_zone=8)
    cost5 = P.cost_table(mass, ship_zone=5)
    rec = {"ticket": "BL-086", "date": DATE, "design": "B86 = B85 + BL-086 lumbar / tie / leg / bushing rework",
           "cfg": {k: v for k, v in L.cfg86().items()},
           "basis": {"sn_design_r0_smax_mpa": L.smax_r0(None), "fret_metal_r0_smax_mpa": L.smax_r0("metal"),
                     "fret_poly_r0_smax_mpa": L.smax_r0("poly"), "walk": "envelope: static_carry x 1.6, meat_straps x 1.6 / 2.0",
                     "c6p": True},
           **{k: v for k, v in an.items() if k != "members_util"},
           "margins_table": margins_table(an["rows"]), "fixed": fixed_rows(an["rows"]),
           "interference": P.interference_check(), "printed": printed, "cut_list": P.cut_list(), "mass": mass,
           "cost": cost, "cost_zone5": cost5}
    rec["comparison"] = comparison(mass, cost, cost5, rec["strong_pass"])
    rec["coupons"] = coupons(rec)
    rec["cap_pass_zone8"] = cost["within_cap"]
    rec["cap_pass_zone5"] = cost5["within_cap"]
    rec["mass_within_limit"] = mass["body_g"] <= MASS_LIMIT
    rec["stop_rule"] = stop_rule(rec)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rec["screens"] = screens(rec, an.get("members_util", {}))
    REC_JSON.write_text(json.dumps(BR._js(rec), indent=1))
    write_md(rec)
    return rec


def stop_rule(rec) -> str:
    ok_s, ok_m = rec["strong_pass"], rec["mass"]["body_g"] <= MASS_LIMIT * 1.0
    ok_c8, ok_c5 = rec["cost"]["within_cap"], rec["cost_zone5"]["within_cap"]
    if ok_s and ok_m and ok_c8 and ok_c5:
        return "MET: every row >= 1.0, <= 2.1 kg and <= USD 150 landed at zone 5 and zone 8"
    miss = []
    if not ok_s:
        miss.append(f"Strong (min {rec['min_margin']:.2f})")
    if not ok_m:
        miss.append(f"mass {rec['mass']['body_g']:.0f} g > {MASS_LIMIT:.0f} g")
    if not ok_c8:
        miss.append(f"cap at FedEx zone 8 (USD {rec['cost']['per_frame_usd']:.2f})")
    if not ok_c5:
        miss.append(f"cap at FedEx zone 5 (USD {rec['cost_zone5']['per_frame_usd']:.2f})")
    return "NOT MET: " + "; ".join(miss) + ". Per the stop rule this is the best result; no further iteration."


# ----------------------------------------------------------------------------- screens
def _save(fig, n, out):
    p = SCREENS / f"{SHOT}{n}.png"
    fig.savefig(p, dpi=110)
    import matplotlib.pyplot as plt
    plt.close(fig)
    import os
    assert os.path.getsize(p) < 1.5e6, p
    out.append(str(p.relative_to(BQ.REPO)))


def screens(rec, util) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = []
    blue, orange, green, red, grey, ink = "#257de0", "#f47230", "#0aac23", "#d03b3b", "#8a8f96", "#191919"
    # 1. changed details: front view (x-z) of the right lumbar node and post, and a side section (y-z) at the upper tie
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 8.6), gridspec_kw={"width_ratios": [1.35, 1]})
    a1.add_patch(Rectangle((115 - 12.7, 40), 25.4, 180, fc="#d9dde2", ec=ink, lw=1))                   # stay
    for z in (85, 155):
        a1.add_patch(Rectangle((-5, z - 12.7), 115 - 12.7 + 5, 25.4, fc="#d9dde2", ec=ink, lw=1))      # rungs
    a1.add_patch(Polygon([(115 - 19, P.GUSSET_Z[0]), (115 + 19, P.GUSSET_Z[0]), (115 + 19, P.GUSSET_Z[1]),
                          (50, P.GUSSET_Z[1]), (50, 155 - 12.7), (115 - 19, 155 - 12.7), (115 - 19, 85 + 12.7),
                          (50, 85 + 12.7), (50, 85 - 12.7), (115 - 19, 85 - 12.7)], closed=True, fc=blue, alpha=0.18,
                         ec=blue, lw=1.2))
    for z in (105, 135):
        a1.add_patch(Circle((115, z), 2.65, fc="white", ec=red, lw=1.5, ls="--"))
        a1.plot([110, 120], [z - 5, z + 5], color=red, lw=1.5)
    for z in rec["cfg"]["stay_bolt_z"]:
        a1.add_patch(Circle((115, z), 2.65, fc=green, ec=ink, lw=1))
    for x in (62, 90):
        for z in (85, 155):
            a1.add_patch(Circle((x, z), 2.65, fc=grey, ec=ink, lw=0.8))
    a1.add_patch(Rectangle((-38.1, 75), 76.2, 90, fc="none", ec=orange, lw=1.5))                         # post front legs
    a1.add_patch(Rectangle((1.5, 75), 25.4, 90, fc=orange, alpha=0.35, ec=orange))                       # doubler (one shown)
    a1.add_patch(Circle((30, 85), 2.65, fc=green, ec=ink))
    a1.add_patch(Rectangle((30 - 12.5, 85 - 12.7 - 4), 25, 4, fc=green, ec=ink))                           # saddle washer (behind)
    a1.add_patch(Circle((30, 155), 2.65, fc="white", ec=red, ls="--", lw=1.5))
    a1.plot([25, 35], [150, 160], color=red, lw=1.5)
    a1.add_patch(Rectangle((P.TIE_SADDLE_X[0], 155 - 13.5), P.TIE_SADDLE_X[1] - P.TIE_SADDLE_X[0], 27, fc="#00a888",
                           alpha=0.55, ec=ink))
    a1.add_patch(Rectangle((115 - 12.7 - 8, 155 - 25), 8, 50, fc="#00a888", alpha=0.55, ec=ink))         # plug head
    a1.add_patch(Rectangle((115 - 15, 50), 30, 16, fc="#cfcfcf", ec=ink, lw=0.8))                          # foot cup sleeve top
    a1.add_patch(Circle((115, 60), 2.65, fc=grey, ec=ink))
    a1.set_xlim(-45, 150)
    a1.set_ylim(40, 200)
    a1.set_aspect("equal")
    a1.set_title("Right lumbar node, front view (x-z, mm)", fontsize=11)
    a1.set_xlabel("x (mm)")
    a1.set_ylabel("z (mm)")
    notes = ["red dashed = B85 holes deleted: stay z105 / z135, upper-rung tie holes",
             f"green = B86 stay holes z {rec['cfg']['stay_bolt_z'][0]:g} / {rec['cfg']['stay_bolt_z'][1]:g} (15 / 26 MPa walk vs 54)",
             "teal = printed: upper-tie saddle (no hole), 50 mm plug head",
             "green bar = printed saddle washer behind the lower rung (snug bolt)",
             "orange = post legs + 1 x 1/8 doubler strip under the Ti mount",
             "blue = .090 gusset plate (spine z 68-170)"]
    a1.text(-43, 198, "\n".join(notes), fontsize=8.6, va="top", color=ink)
    # side section at x = 21 (upper tie): post leg, saddle, rung; and the lower tie
    yl = BQ.Y_MOUNT
    a2.add_patch(Rectangle((yl - 3.2, 70), 3.2, 100, fc=orange, alpha=0.5, ec=ink))                        # doubler (front)
    a2.add_patch(Rectangle((yl, 75), 3.175, 90, fc="#d9dde2", ec=ink))                                     # front leg
    for z in (85, 155):
        a2.add_patch(Circle((-10 * z / 530, z), 12.7, fc="#d9dde2", ec=ink))
    yr = -10 * 155 / 530
    a2.add_patch(Polygon([(yl + 3.4, 155 - 13.5), (yr - 2, 155 - 13.5), (yr - 6.4, 155 - 11), (yr - 12.7, 155),
                          (yr - 6.4, 155 + 11), (yr - 2, 155 + 13.5), (yl + 3.4, 155 + 13.5)], closed=True, fc="#00a888",
                         alpha=0.55, ec=ink))
    yr8 = -10 * 85 / 530
    a2.add_patch(Rectangle((yl + 3.2, 85 - 9.5), yr8 - 12.7 - yl - 3.2, 19, fc=grey, alpha=0.6, ec=ink))   # spacer
    a2.add_patch(Polygon([(yr8 + 12.7, 85 - 12), (yr8 + 16.5, 85 - 12), (yr8 + 16.5, 85 + 12), (yr8 + 12.7, 85 + 12)],
                         fc=green, ec=ink))
    a2.plot([yl - 6, yr8 + 19], [85, 85], color=ink, lw=2)
    a2.annotate("hip pin 3.2 mm\nfurther forward", (yl - 3, 120), (yl - 40, 128), fontsize=8.5, arrowprops=dict(arrowstyle="->"))
    a2.annotate("tie force: compression\n(783 N limit, 417 N walk)", (yr - 12, 155), (yr - 52, 185), fontsize=8.5,
                arrowprops=dict(arrowstyle="->"))
    a2.annotate("snug bolt + printed saddle\n(tension, 25 mm x 160 deg)", (yr8 + 16, 80), (yr8 - 30, 50), fontsize=8.5,
                arrowprops=dict(arrowstyle="->"))
    a2.set_xlim(-95, 30)
    a2.set_ylim(40, 200)
    a2.set_aspect("equal")
    a2.set_title("Hip ties, side section (y-z, forward = left)", fontsize=11)
    a2.set_xlabel("y (mm)")
    fig.suptitle("BL-086 changed details (B86)", fontsize=13)
    fig.tight_layout()
    _save(fig, 1, out)
    # 2. utilisation map: lowest 22 gated rows, B85 baseline marked
    rows = [r for r in rec["rows"] if r.get("margin") is not None and r["kind"] != "info"]
    seen, low = set(), []
    for r in sorted(rows, key=lambda r: r["margin"]):
        key = r["row"].replace(" L:", ":").replace(" R:", ":")
        if key not in seen:
            seen.add(key)
            low.append(r)
    low = low[:22][::-1]
    fig, ax = plt.subplots(figsize=(10, 11))
    vals = [min(r["margin"], 3.0) for r in low]
    cols = [green if r["margin"] >= 1.0 else red for r in low]
    ax.barh(range(len(low)), vals, color=cols, height=0.62)
    ax.axvline(1.0, color=ink, lw=1.2)
    for i, r in enumerate(low):
        ax.text(vals[i] + 0.02, i, f"{r['margin']:.2f} ({r['kind']})", va="center", fontsize=8.3)
    ax.set_yticks(range(len(low)))
    ax.set_yticklabels([r["row"][:66] for r in low], fontsize=7.9)
    ax.set_xlim(0, 3.3)
    ax.set_xlabel("margin = allowable / value (1.0 = goal); fatigue on the Yahr DESIGN curve")
    ax.set_title(f"B86: lowest 22 rows of {len(rows)} (walk envelope, C6p)\nframe min {rec['min_margin']:.2f}: "
                 f"{rec['governing'][:70]}", fontsize=10.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _save(fig, 2, out)
    # 3. before / after of the fixed rows + mass / cost comparison
    fig, (a0, a1_, a2_) = plt.subplots(1, 3, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    fx = rec["fixed"]
    yy = np.arange(len(fx))
    a0.barh(yy + 0.18, [f["b85_design"] for f in fx], height=0.34, color=grey, label="B85 (design curve)")
    a0.barh(yy - 0.18, [f["b86"] for f in fx], height=0.34, color=[green if f["b86"] >= 1 else red for f in fx], label="B86")
    a0.axvline(1.0, color=ink)
    a0.set_yticks(yy)
    import textwrap
    a0.set_yticklabels(["\n".join(textwrap.wrap(f["b85_row"], 26)) for f in fx], fontsize=8)
    for i, f in enumerate(fx):
        a0.text(f["b86"] + 0.03, i - 0.18, f"{f['b86']:.2f}", va="center", fontsize=8.5)
        a0.text(f["b85_design"] + 0.03, i + 0.18, f"{f['b85_design']:.2f}", va="center", fontsize=8.5, color="#555")
    a0.set_xlim(0, 2.6)
    a0.legend(fontsize=8.5, frameon=False, loc="lower right")
    a0.set_title("Rows that failed on B85 -> B86", fontsize=10.5)
    comp = rec["comparison"]
    names = [c["option"].replace(" (this record)", "") for c in comp]
    a1_.bar(names, [c["body_g"] for c in comp], color=[green if c["strong"] == "PASS" else grey for c in comp])
    a1_.axhline(MASS_LIMIT, color=red, lw=1.2)
    a1_.text(-0.4, MASS_LIMIT + 25, "2.1 kg limit", color=red, fontsize=8.5)
    for i, c in enumerate(comp):
        a1_.text(i, c["body_g"] + 30, f"{c['body_g']:.0f} g\n{c['body_g'] / 453.6:.2f} lb", ha="center", fontsize=8.5)
    a1_.set_ylim(0, 2600)
    a1_.set_title("Frame body mass (green = Strong PASS)", fontsize=10.5)
    x = np.arange(len(comp))
    u8 = [c["usd8"] for c in comp]
    u5 = [c["usd5"] if c["usd5"] is not None else np.nan for c in comp]
    a2_.bar(x - 0.2, u5, width=0.38, color="#6a4ce2", label="FedEx zone 5")
    a2_.bar(x + 0.2, u8, width=0.38, color=orange, label="zone 8 (H1c: as booked)")
    a2_.axhline(CAP, color=red, lw=1.2)
    a2_.text(-0.45, CAP + 3, "cap USD 150", color=red, fontsize=8.5)
    for i in range(len(comp)):
        if not np.isnan(u5[i]):
            a2_.text(i - 0.2, u5[i] + 2, f"{u5[i]:.0f}", ha="center", fontsize=8.5)
        a2_.text(i + 0.2, u8[i] + 2, f"{u8[i]:.0f}", ha="center", fontsize=8.5)
    a2_.set_xticks(x)
    a2_.set_xticklabels(names, fontsize=9)
    a2_.set_ylim(0, 200)
    a2_.legend(fontsize=8.5, frameon=False, loc="lower right")
    a2_.set_title("Landed USD per frame", fontsize=10.5)
    for a in (a0, a1_, a2_):
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"BL-086: B86 {rec['mass']['body_g']:.0f} g, USD {rec['cost_zone5']['per_frame_usd']:.2f} (zone 5) / "
                 f"{rec['cost']['per_frame_usd']:.2f} (zone 8); {rec['stop_rule'][:60]}", fontsize=10.5)
    fig.tight_layout()
    _save(fig, 3, out)
    return out


# ----------------------------------------------------------------------------- markdown
def write_md(rec: dict) -> None:
    w = []
    a = w.append
    m, co, c5 = rec["mass"], rec["cost"], rec["cost_zone5"]
    lb = m["body_g"] / 453.6
    a("# BL-086: B86, the non-tee details of the aluminium ladder on the design S-N curve\n")
    a(f"Owner: structural-fea-engineer, {DATE}. Last metal round (DECISIONS 2026-11-26: fatigue on the Yahr design curve "
      "frame-wide, fretting as in BL-085). Code: `huntkit/gendesign/bl086_global.py` (B86 model, walk envelope, C6p), "
      "`bl086_local.py` (rows), `bl086_parts.py` (STL, mass, cost), `bl086_report.py` (this record). BL-077 / 079 / 081 / 083 / "
      "085 code, the kit generators and `huntkit/manufacturing` are not edited. Numbers: [bl086.json](bl086.json). Tests: "
      "`tests/test_bl086_frame.py`. Units mm, N, MPa, g, USD (imperial in brackets).\n")
    a("## 0. Answer\n")
    a(f"- **Strong: {'PASS' if rec['strong_pass'] else 'FAIL'}.** Minimum margin over every gated row "
      f"{rec['min_margin']:.2f} ({rec['governing']}). Every metal fatigue row is on the design curve (R 0 S_max "
      f"{rec['basis']['sn_design_r0_smax_mpa']:.1f} MPa open; {rec['basis']['fret_metal_r0_smax_mpa']:.1f} at a metal contact "
      f"edge; {rec['basis']['fret_poly_r0_smax_mpa']:.1f} at a polymer contact), walk = bag-carry / meat-carry envelope, C6p in "
      "every envelope.")
    a(f"- **Mass {m['body_g']:.0f} g ({lb:.2f} lb) body**, {m['vs_b85_g']:+.0f} g vs B85 ({m['b85_body_g']:.0f} g); "
      f"limit about {MASS_LIMIT:.0f} g: {'inside' if m['body_g'] <= MASS_LIMIT else 'OVER'}.")
    a(f"- **Landed cost USD {c5['per_frame_usd']:.2f} at FedEx zone 5, USD {co['per_frame_usd']:.2f} at zone 8** (cap 150): "
      f"zone 5 {'PASS' if c5['within_cap'] else 'FAIL'}, zone 8 {'PASS' if co['within_cap'] else 'FAIL'}.")
    a(f"- **Stop rule: {rec['stop_rule']}**\n")
    a("## 1. What failed on B85 and what B86 does\n")
    a("| B85 row (design curve, walk envelope) | B85 | B86 fix | B86 row | B86 |")
    a("|---|---:|---|---|---:|")
    for f in rec["fixed"]:
        a(f"| {f['b85_row']} | {f['b85_design']:.2f} | {f['fix']} | {f['b86_row'][:90]} | {f['b86']:.2f} |")
    a("")
    a("Why these fixes (from the B86 global run):\n")
    a("- **The stays bend fore-aft, and B81 / B85 drilled the gusset bolts along y, so every stay hole sat on the extreme "
      "fibre.** The walk stress at the hole fibre is 54 MPa at z 135, 32 at z 105, 26 at z 95, 15 at z 78; above the lumbar "
      "node the stay runs a 70 MPa plateau from z 155 to z 380. An open hole (Kt 3.3-4.7) passes the design curve (R 0 S_max "
      "114 MPa) only below about 30 MPa, so the holes move to z 78 / 95. The hinge pin z 60 is 18 mm (3.4 D) from the new "
      "z 78 hole, on a different axis.")
    a("- **The rung's central span is a constant-moment zone** (two tie forces at x +/-30): 23 N m fore-aft at walk, 36 MPa at "
      "the hole fibre, plus the tie's bearing patch. No hole position along the rung helps. The tie force is one-signed: the "
      "post pushes the upper rung aft and pulls the lower rung forward in every case (the only reversal is 33 N in the "
      "single-stay set-down). So the upper tie becomes a printed compression saddle with no hole, and the lower tie keeps "
      "its bolt, with the nut-side patch spread by a printed saddle washer on a snug bolt (no preload credited; a 6061 "
      "saddle washer was tried first and its edge failed the metal-fretting row at 0.94).")
    a("- **A row B81 / B85 never checked:** the printed rung-end plug bears on the stay at z 155, right at the top of the "
      "node, at 69 MPa walk. With the B81 20 mm head it is about 0.95 on the design curve with polymer contact. B86 flares the "
      "upper plug head to 50 mm (25 mm wide, between the gusset plates), and the IM1 collar moves up to z 181-189.")
    a("- **Front leg:** two 1 x 1/8 doubler strips under the Ti mount, credited only by bending-stiffness share (no "
      "composite action). The strips put the hip pin 3.2 mm further forward. The global model carries that, and the "
      "tipping rows are scaled by (21 + 3.2) / 21.")
    a("- **Leg-end bushing 70 -> 110 mm** (it grows up the leg, so the leg tip is unchanged; it now spans z 171-414 over the "
      "torso range, 61 mm clear of the stay-top bushing). That lowers the hoop at the 73 MPa stay section. The B85 stay "
      "holes at z 105 / 135 would have blocked a longer bushing, and the z 95 hole does not.")
    bc = rec["bond_check"]
    a(f"- **Bonded sleeve doublers were studied and rejected.** A 1-1/4 x .120 sleeve bonded on the stay (Volkersen shear "
      f"lag, toughened epoxy G 700 MPa, 0.13 mm bondline) has a bond peak of {bc['tau_peak_walk_mpa']:.0f} MPa at walk and "
      f"{bc['tau_peak_factored_mpa']:.0f} MPa factored at the sleeve end. That is above any cited epoxy fatigue strength. "
      "Through-hole doublers in the stay's bending peak still carry the hole.\n")
    a("## 2. Minimum margin per check item and kind (B86, every row on the design curve)\n")
    a("| # | check | kind | margin | governing row |")
    a("|---|---|---|---:|---|")
    for t in rec["margins_table"]:
        a(f"| {t['item']} | {ITEMS.get(t['item'], '').split(' (')[0]} | {t['kind']} | {t['margin']:.2f} | {t['row'][:110]} |")
    gl = rec["global"]
    a(f"\nGlobal: stays {gl['strength']['stays']['margin']:.3f} ({gl['strength']['stays']['case']}), buckling "
      f"{gl['buckling']['margin']:.2f} ({gl['buckling']['case']}). C6p stays {gl['c6p'].get('stays', {}).get('margin', float('nan')):.3f}.\n")
    a("## 3. Every gated row\n")
    a("| item | row | kind | margin | basis |")
    a("|---|---|---|---:|---|")
    for r in sorted([r for r in rec["rows"] if r.get("margin") is not None], key=lambda r: (r["item"], r["margin"])):
        a(f"| {r['item']} | {r['row'][:100]} | {r['kind']} | {r['margin']:.2f} | {str(r['basis'])[:170]} |")
    a("")
    sw = rec["preload_sweep"]
    a("Upper-tee preload sweep (BL-085 detail, B86 loads): " + "; ".join(
        f"{s['factor']:.1f} x: slip {s['slip']:.2f} / static {s['static']:.2f} / fatigue {s['fatigue']:.2f}" for s in sw
        if s["factor"] in (0.7, 1.0, 1.3)) + ".\n")
    a("## 4. Mass and cost\n")
    a("| item | g |")
    a("|---|---:|")
    for k, v in m["rows"].items():
        a(f"| {k} | {v:.1f} |")
    a(f"| **body** | **{m['body_g']:.1f}** ({lb:.2f} lb) |\n")
    a("| line | USD | source |")
    a("|---|---:|---|")
    for l in co["lines"]:
        a(f"| {l['item']} | {l['usd']:.2f} | {l['source'][:190]} |")
    a(f"| **per frame, FedEx zone 8** | **{co['per_frame_usd']:.2f}** | cap 150 |")
    a(f"| **per frame, FedEx zone 5** | **{c5['per_frame_usd']:.2f}** | shipping line {c5['lines'][-1]['usd']:.2f} |\n")
    a("Comparison:\n")
    a("| option | Strong (design curve frame-wide) | body g (lb) | USD zone 5 | USD zone 8 | note |")
    a("|---|---|---:|---:|---:|---|")
    for c in rec["comparison"]:
        u5 = "-" if c["usd5"] is None else f"{c['usd5']:.2f}"
        a(f"| {c['option']} | {c['strong']} | {c['body_g']:.0f} ({c['body_g'] / 453.6:.2f}) | {u5} | {c['usd8']:.2f} | {c['note']} |")
    a("")
    a("## 5. Coupons for the new details (pass lines)\n")
    a("| id | what | pass | settles |")
    a("|---|---|---|---|")
    for cp in rec["coupons"]:
        a(f"| {cp['id']} | {cp['what']} | {cp['pass']} | {cp['settles']} |")
    a("\nThese run with BL-085 KF-T / KF-S / CL-T on the T5 rig. **No build pack until KF-T, KF-S, KF-TS, KF-LT and KF-P "
      "pass.** Proving material: offcuts of the frame order plus about USD 8 of extra tube (1 x .065 36 in, already in the "
      "BL-085 proving list). No new tool.\n")
    a("## 6. Parts and files\n")
    for k, v in rec["printed"].items():
        a(f"- printed `{v['file']}` (+ `_L`): {v['mass_g_each']} g x {v['count']}, watertight {v['watertight']}, bbox {v['bbox_mm']} mm")
    a(f"- interference (manifold boolean, mm3): {rec['interference']}")
    a("- cut list changes: `bl086.json` `cut_list`. Stays: holes z 78 / 95, none above z 100. Upper rung: no tie holes. "
      "Gussets: spine z 68-170. Post stems: notch at both rungs. Doubler strips; printed saddle washers on the lower ties.\n")
    a("## 7. Findings\n")
    a("- **F1:** the B81 / B85 hip-post angle stems (aft leg at x +/-34.8-38.1, reaching y -10.45) overlap both rung fronts "
      "(y -15.6) by 5.2 mm. The B81 geometry cannot be assembled as drawn. B86 notches both stems at the rungs (OV-3 a).")
    a("- **F2:** the printed foot-cup sleeve (to z 75) collided with the B81 gusset plates (from z 70). B86 cuts it to z 66.")
    a("- **F3:** no B81 / B85 row checked the stay side of the rung-end plug contact (now item 3 / 1 rows, KF-P).")
    a("- **F4:** the BL-081 / BL-085 non-tee hole rows were fed by the bag-carry walk only. On the envelope, the meat walk "
      "governs the z 85 rung rows and the tie spacer column.\n")
    a("## 8. Assumptions (each with the test that settles it)\n")
    for s in [
        "ASSUMPTION FRET-HOLE: an open, crush-sleeved bolt hole is checked with its solid-FE peak on the design curve and no "
        "extra fretting knock-down (the BL-085 basis put fretting at clamp and contact edges only). KF-1 (re-targeted) and "
        "KF-LT, with the plates clamped as built. Sensitivity: with the 0.6 metal-fretting factor also on the bolted holes, "
        "every hole row scales by 0.651 (stay z 95 1.09 -> 0.71, rung tie bore 1.14 -> 0.74, rung gusset holes 1.36 -> 0.89), "
        "so B86 then fails like every B-family frame; the coupons decide.",
        "ASSUMPTION SADDLE-KT 1.15 / FRET-POLY 0.85 (BL-085) for the upper-tie saddle, the rung plugs and the bushings. KF-TS, "
        "KF-P, KF-S.",
        "ASSUMPTION TIE-SADDLE-K: upper tie link 3e4 N/mm along the tie, 2e4 across in z, 100 N/mm along the rung (friction "
        "only). OV-3 (b), T1 deflection.",
        "ASSUMPTION SNUG-LT: the lower tie bolt is snug (0.5 N m) with a nylon-insert locknut; no preload is credited "
        "anywhere, so the printed saddle washer under it sees the tie pull in bearing only (a departure from the BL-082 'no "
        "printed part under preload' practice, which protects preload this joint does not rely on). KF-LT re-torque check.",
        "ASSUMPTION WASHER-PRICE: M5 x 15 fender washer USD 0.10 (as the BL-077 nut line).",
        "ASSUMPTION DOUBLER-SHARE: the doubler strips take their bending-stiffness share of the leg moment (net widths, t^3), "
        "no composite action. FL-D.",
        "ASSUMPTION BUSH-TRAVEL: the 110 mm leg-end bushing grows up the leg (tip unchanged) and stays 61 mm clear of the "
        "stay-top bushing at the 23 in torso. OV-3 (d).",
        "ASSUMPTION BOND (rejection only): toughened epoxy G 700 MPa, 0.13 mm bondline.",
        "Carried: BL-085 tee assumptions (FRET-METAL 0.6, SCATTER +/-30 %, SHELL-FIT, WALK-ENV, GEOM-85) and BL-081 / BL-082 "
        "(MU 0.15, GAP-K, crush sleeves, PAHT hot/wet basis, FUEL-20, SCREW-LEN).",
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
    elif cmd == "unit":
        job = sys.argv[2]
        args = (sys.argv[3], float(sys.argv[4]), float(sys.argv[5]))
        stage_units(job, args)
    elif cmd == "stage":
        CACHE.mkdir(parents=True, exist_ok=True)
        fn = {"frame": analyse_frame, "tee": analyse_tee}[sys.argv[2]]
        (CACHE / f"stage_{sys.argv[2]}.json").write_text(json.dumps(BR._js(fn())))
    elif cmd == "md":
        rec = json.loads(REC_JSON.read_text())
        rec["screens"] = screens(rec, {})
        REC_JSON.write_text(json.dumps(BR._js(rec), indent=1))
        write_md(rec)
