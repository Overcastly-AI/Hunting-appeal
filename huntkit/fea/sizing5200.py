"""Sizing of the Pack 5200 frame (pack-designer topology, huntkit.fea.pack5200) over buyable stock.

Checks per candidate, at torso 15 / 19 / 23 in (crown settings from geometry.yaml):
  pack5200_cases (7 standard + tall_load_posts + hipbelt_off_abuse) -> member SF / required,
  frame buckling / 3.0, bonded joints average AND Volkersen peak / required, crown (bushing
  bearing, ring crush of stay and leg at the bushings), lumbar plate (in-plane shear, shear
  buckling / 3.0, plate-to-stay bond avg + peak, pivot punching), fatigue (1.2 g).
Objective: frame mass (tubes + plates + hubs/sleeves/inserts/adhesive + crown lock hardware;
extension posts excluded as an accessory).
"""
from __future__ import annotations

import itertools
import time

import numpy as np

from .analysis import fatigue_screen, run_study
from .joints import check_frame_joints
from .load_cases import pack5200_cases
from .pack5200 import build, crown_checks, plate_checks
from .sizing import (ADHESIVES, UD, WV, _family_of, _map, _wall, k_for_walls, make_section, pareto,
                     section_spec)

LEG_ODS = (12.0, 14.0, 16.0, 18.0, 19.0, 20.0, 22.0)    # buyable roll-wrapped ODs (mm)
BAG_CASES = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown")
CG_BAG = 180.0   # geometry.yaml: bag frame-side panel at y 20 + depth 320 / 2


def cases():
    return pack5200_cases(**{n: {"cg_aft_mm": CG_BAG} for n in BAG_CASES})


def leg_for(stay_spec, family="RW45", k=4, min_gap=0.75):
    st = make_section(stay_spec)
    bore = st.dims["od"] - 2 * st.dims["t"]
    ods = [od for od in LEG_ODS if (bore - od) / 2 >= min_gap]
    if not ods:
        return None
    return section_spec(("round", max(ods)), family, k)


def params_for(c: dict) -> dict:
    adh = ADHESIVES[c["adhesive"]]
    st = c.get("sleeve_t", 1.0)
    return {
        "stay_section": make_section(c["stay"]), "leg_section": make_section(c["leg"]),
        "bar_section": make_section(c["bar"]), "lumbar_plate_material": c["plate"][0],
        "lumbar_plate_t": c["plate"][1],
        **({"spine_section": make_section(c["spine"])} if isinstance(c["spine"], dict)
           else {"spine_w": c["spine"][0], "spine_t": c["spine"][1]}),
        "bushing_len_mm": c.get("bushing_len", 40.0),
        "joint": {**adh, "overlap_mm": 30.0, "through_overlap_mm": 40.0, "sleeve_t_mm": st},
    }


def _desc(spec):
    geo = f"{spec['od']:g}" if "od" in spec else f"{spec['w']:g}x{spec['h']:g}"
    k = sum(1 for d in spec["layup"] if d["material"] == UD and d["angle"] == 0)
    return f"{geo} {_family_of(spec)} k{k} ({_wall(spec):.2f})"


def label(c):
    pl = "pm45" if "pm45" in c["plate"][0] else "QI"
    return (f"stay {_desc(c['stay'])} | leg {_desc(c['leg'])} | bars {_desc(c['bar'])} | "
            f"plate {pl} {c['plate'][1]:g} | spine {_spine(c['spine'])} | {c['adhesive']} | "
            f"sleeve {c.get('sleeve_t', 1.0):g} | bushing {c.get('bushing_len', 40.0):g}")


def _spine(sp):
    return f"tube {_desc(sp)}" if isinstance(sp, dict) else f"plate {sp[0]:g}x{sp[1]:g}"


def evaluate(c: dict, torsos=(15, 19, 23), keep_results: bool = False) -> dict:
    worst = {"margin": np.inf}
    per = {}
    retention = {"extension": 0.0, "compression": 0.0, "by_case": {}}
    stay_margin = np.inf
    mass = None
    kept = {}
    for t in torsos:
        p = params_for(c)
        fm = build({**p, "torso_in": t})
        fmp = build({**p, "torso_in": t, "extension_posts": True})
        mass = fm["hardware"]
        cs = cases()
        st = run_study(fm, [x for x in cs if x.name != "tall_load_posts"])
        stp = run_study(fmp, [x for x in cs if x.name == "tall_load_posts"])
        results = {**st["results"], **stp["results"]}
        joints = {**st["joints"], **stp["joints"]}
        if keep_results:
            kept[t] = {"results": results, "joints": joints, "model": fm, "model_posts": fmp,
                       "fatigue": st["fatigue"]}
        checks = []
        for name, r in results.items():
            req = r.meta["required_sf"]
            model = fmp if name == "tall_load_posts" else fm
            checks.append((r.min_sf / req, f"{name}: member {r.critical_member['id']}", "member"))
            sm = min(m["sf"] for m in r.members if m["group"].startswith(("stay", "crown_leg"))) / req
            stay_margin = min(stay_margin, sm)
            if r.buckling_factors:
                # buckling requirement 3.0 at the design SF 2.0, scaled for overload (1.5) / abuse (1.0)
                checks.append((r.buckling_sf / (3.0 * req / 2.0), f"{name}: buckling", "buckling"))
            for j in joints[name]:
                checks.append((j["sf_avg"] / req, f"{name}: bond avg {j['joint']}/{j['kind']}", "bond_avg"))
                checks.append((j["sf_peak"] / req, f"{name}: bond peak {j['joint']}/{j['kind']}", "bond_peak"))
            for cc in crown_checks(r, model):
                if cc.get("retention"):
                    v = cc["value"]
                    retention["by_case"][(name, t)] = v
                    if v > retention["extension"]:
                        retention["extension"] = v
                    if v < retention["compression"]:
                        retention["compression"] = v
                    continue
                if cc.get("info"):
                    continue
                checks.append((cc["sf"] / req, f"{name}: crown {cc['check']}", "crown"))
            for pc in plate_checks(r, model):
                div = 3.0 * req / 2.0 if pc.get("buckling") else req
                kind = "plate_buckling" if pc.get("buckling") else ("bond_peak" if "peak" in pc["check"] else "plate")
                checks.append((pc["sf"] / div, f"{name}: {pc['check']}", kind))
        f = st["fatigue"]
        for m in f["members"]:
            checks.append((m.get("sf", m.get("life", np.inf) / f["cfg"]["cycles_required"]),
                           f"fatigue member {m['member']}", "fatigue"))
        for j in f["joints"]:
            checks.append((j["sf"], f"fatigue bond {j['joint']}", "fatigue"))
        for mrg, what, kind in checks:
            case = what.split(":")[0]
            per[(case, t)] = min(per.get((case, t), np.inf), mrg)
            per[kind] = min(per.get(kind, np.inf), mrg)
            if mrg < worst["margin"]:
                worst = {"margin": float(mrg), "what": what, "torso": t}
    out = {"cand": c, "margin": worst["margin"], "governing": worst, "per_check": per,
           "stay_margin": stay_margin, "mass_g": mass["total_g"], "tubes_g": mass["tubes_g"],
           "hubs_g": mass["hubs_g"], "mass_items": mass["items"], "feasible": worst["margin"] >= 1.0,
           "label": label(c), "retention": retention}
    if keep_results:
        out["kept"] = kept
    return out


def _quick(c):
    return evaluate(c, (15, 23))


def _full(c):
    return evaluate(c, (15, 19, 23))


def stay_options():
    for od in (20.0, 22.0, 25.0):
        for fam in ("RW0", "RW45", "UD90"):
            for k in k_for_walls(fam, (0.8, 1.0, 1.25, 1.5, 2.0)):
                yield section_spec(("round", od), fam, k)


BASE = {"bar": section_spec(("round", 18), "RW45", 4), "plate": ("cfrp_plate_quasi_iso", 3.0),
        "spine": section_spec(("round", 18), "RW45", 4), "adhesive": "mma", "sleeve_t": 1.0,
        "bushing_len": 50.0}
SPINES = [(50.0, 5.0), section_spec(("round", 16), "RW45", 4), section_spec(("round", 18), "RW45", 4),
          section_spec(("round", 20), "RW45", 4)]


def sweep(log=print, procs=3, keep_a=6, keep_d=14):
    t0 = time.time()
    # A: stays + legs
    ca = []
    for st in stay_options():
        for lf, lk in (("RW45", 4), ("RW45", 8), ("UD90", 6), ("UD90", 10)):
            leg = leg_for(st, lf, lk)
            if leg is not None:
                ca.append({**BASE, "stay": st, "leg": leg})
    sa = _map(_quick, ca, procs)
    log(f"A: {len(sa)} stay/leg options, {time.time() - t0:.0f} s")
    ok = sorted([e for e in sa if e["stay_margin"] >= 1.0], key=lambda e: e["tubes_g"])
    seen, best = set(), []
    for e in ok:
        key = (e["cand"]["stay"]["od"], _family_of(e["cand"]["stay"]))
        if key in seen and len(best) >= 3:
            continue
        seen.add(key)
        best.append(e)
        if len(best) >= keep_a:
            break
    # B: plate x spine on the best stays
    cb = []
    for e in best:
        for plate, spine in itertools.product(
                [("cfrp_plate_pm45", 3.0), ("cfrp_plate_quasi_iso", 2.5), ("cfrp_plate_quasi_iso", 3.0),
                 ("cfrp_plate_quasi_iso", 4.0)], SPINES):
            cb.append({**e["cand"], "plate": plate, "spine": spine})
    sb = _map(_quick, cb, procs)
    log(f"B: {len(sb)} plate/spine variants, {time.time() - t0:.0f} s")
    # C: bars + joints around the best B per stay
    cc = []
    for e in best:
        mine = sorted([x for x in sb if x["cand"]["stay"] == e["cand"]["stay"]],
                      key=lambda x: (-(x["margin"] >= 1.0), x["mass_g"] if x["margin"] >= 1.0 else -x["margin"]))
        for x in mine[:2]:
            for bar, adh, slv, bl in itertools.product(
                    [section_spec(("round", od), "RW45", k) for od, k in ((16, 4), (18, 4), (20, 4))],
                    ("mma", "epoxy"), (1.0, 2.0), (50.0, 70.0)):
                cc.append({**x["cand"], "bar": bar, "adhesive": adh, "sleeve_t": slv, "bushing_len": bl})
    sc = _map(_quick, cc, procs)
    log(f"C: {len(sc)} bar/joint variants, {time.time() - t0:.0f} s")
    allq = sa + sb + sc
    feas = sorted([e for e in allq if e["margin"] >= 1.0], key=lambda e: e["mass_g"])
    pick, seen = [], set()
    for e in feas[:keep_d] + pareto(allq)[:keep_d]:
        if e["label"] not in seen:
            seen.add(e["label"])
            pick.append(e["cand"])
    sd = _map(_full, pick, procs)
    log(f"D: {len(sd)} full 15/19/23 in checks, {time.time() - t0:.0f} s")
    return {"stageA": sa, "stageB": sb, "stageC": sc, "stage2": allq, "stage3": sd, "stage1": sa}


# ============================================================================ deliverables
FRAME_BUDGET_G = 525.0
FRAME_REQ_MAX_G = 600.0     # DESIGN.md R-15


def recommend(evals):
    feas = sorted([e for e in evals if e["feasible"]], key=lambda e: e["mass_g"])
    if feas:
        return feas[0], True
    # nothing feasible: best margin among the lightest third, flagged
    return max(evals, key=lambda e: e["margin"]), False


def _yaml_sec(spec):
    return {**{k: v for k, v in spec.items() if k != "layup"},
            "layup": [{"angle": d["angle"], "material": d["material"]} for d in spec["layup"]]}


def stock_rows(e, model):
    from .sizing import _spec_desc, STOCK_NOTE
    c = e["cand"]
    n = model["nodes"]

    def dist(a, b):
        return float(np.linalg.norm(np.subtract(n[a], n[b])))
    rows = []

    def add(part, qty, spec, centre, cut):
        geo, w, lay, fam = _spec_desc(spec)
        rows.append({"part": part, "qty": qty, "section": geo, "wall_mm": round(w, 3), "layup": lay,
                     "source": STOCK_NOTE[fam], "centreline_mm": round(centre, 1), "cut_length_mm": round(cut, 1)})
    lo = dist("SL0", "SL130")
    up = dist("SL130", "SL530")
    add("lower stay (foot boot -> elbow sleeve)", 2, c["stay"], lo, lo - 15.0)
    add("upper stay (elbow sleeve -> stay-top collar)", 2, c["stay"], up, up - 15.0)
    add("crown leg (telescoping)", 2, c["leg"], 430.0, 430.0)
    span = dist("SL330", "SR330")
    stay_od = c["stay"]["od"]
    sl = c.get("sleeve_t", 1.0)
    for part in ("mid bar (z 330)", "upper bar (z 520, pawl housing)", "crown top bar"):
        add(part, 1, c["bar"], span, span - 2 * (stay_od / 2 + sl + 7.0))
    if isinstance(c["spine"], dict):
        add("crown spine tube (rack bonded on)", 1, c["spine"], 300.0, 300.0)
    return rows


def write_frame_yaml(e, path, model, crown_loads):
    import yaml
    from pathlib import Path
    c = e["cand"]
    p = params_for(c)
    frame = {"topology": "pack5200_crown", "name": "pack5200_frame",
             "geometry": "designs/pack_5200/geometry.yaml",
             "torso_in": 19.0, "haul_mode": False, "extension_posts": False,
             "stay_section": _yaml_sec(c["stay"]), "leg_section": _yaml_sec(c["leg"]),
             "bar_section": _yaml_sec(c["bar"]),
             "lumbar_plate_material": c["plate"][0], "lumbar_plate_t": c["plate"][1],
             "bushing_len_mm": c.get("bushing_len", 40.0), "joint": p["joint"]}
    if isinstance(c["spine"], dict):
        frame["spine_section"] = _yaml_sec(c["spine"])
    else:
        frame["spine_w"], frame["spine_t"] = c["spine"]
    doc = {
        "schema": "huntkit.frame/v1",
        "design": "pack_5200",
        "description": "Carbon frame sized by huntkit.fea.sizing5200 on the pack-designer topology "
                       "(geometry.yaml). 'frame' = params for huntkit.fea.frames.build_frame "
                       "(dispatches to huntkit.fea.pack5200.build); override torso_in (15-23) and "
                       "extension_posts. Units mm.",
        "frame": frame,
        "torso_range_in": [15, 23],
        "stock": stock_rows(e, model),
        "joints": _joint_design(c),
        "mass_g": {k: round(float(v), 1) for k, v in e["mass_items"].items()},
        "mass_total_g": round(e["mass_g"], 1),
        "mass_budget_g": FRAME_BUDGET_G,
        "crown_loads_fea": crown_loads,
        "results": {"feasible": bool(e["feasible"]), "min_margin": round(float(e["margin"]), 3),
                    "governing": e["governing"]["what"], "governing_torso_in": e["governing"]["torso"],
                    "margin_by_check": {k: round(float(v), 3) for k, v in e["per_check"].items()
                                        if isinstance(k, str)}},
        "source": "huntkit/fea/sizing5200.py; designs/pack_5200/analysis/frame_sizing.md",
    }
    Path(path).write_text("# Pack 5200 carbon frame - generated by `python -m huntkit.fea.cli size5200`.\n"
                          "# Read with huntkit.fea.frames.build_frame_from_yaml(path, torso_in=..).\n"
                          + yaml.safe_dump(_plain(doc), sort_keys=False, allow_unicode=True, width=100))


def _plain(x):
    from .sizing import _plain as pl
    return pl(x)


def _joint_design(c):
    from .sizing import ADHESIVES
    a = ADHESIVES[c["adhesive"]]
    return {
        "adhesive": a["adhesive"], "bondline_mm": a["adhesive_t_mm"],
        "bondline_control": f"{a['adhesive_t_mm']:g} mm glass beads or wire shims",
        "adhesive_shear_modulus_mpa_ASSUMPTION": a["adhesive_G_mpa"],
        "socket_overlap_mm": 30.0, "through_sleeve_overlap_mm": 40.0,
        "sleeves": f"7075-T6 hard-anodised, wall {c.get('sleeve_t', 1.0):g} mm, ends tapered to 0.3 mm over 8 mm",
        "elbow": "7075 elbow sleeve, 30 mm socket each side (shear, no peel), bonded",
        "foot_boot": "7075 boot bonded 25 mm over the stay foot, shelf-pivot boss + bumper",
        "mid_hub / upper_hub": "7075 through-sleeve 40 mm on the upper stay + 30 mm socket for the bar; CF gusset",
        "stay_top_collar": "7075 collar bonded over the stay top: crown-leg bushing seat (UHMWPE "
                           f"{c.get('bushing_len', 40.0):g} mm) - reinforces the stay ring against bushing load",
        "crown_corner": "7075 corner: socket for leg top + socket for top bar + extension-post socket",
        "lumbar_plate": f"{c['plate'][0]} {c['plate'][1]:g} mm bonded to both stays over z 50-190 (saddle fillet), "
                        "Ti pivot insert with 70 mm backing doubler",
        "galvanic": "no bare Al on carbon: anodise + glass-bead bondline / E-glass ply",
    }


def crown_load_summary(e) -> dict:
    by = e["retention"]["by_case"]
    pick = {}
    for (case, t), v in by.items():
        if case not in pick or abs(v) > abs(pick[case][0]):
            pick[case] = (v, t)
    return {
        "sign": "+ = crown pulled UP out of the stays (extension), - = pushed DOWN (compression)",
        "basis": "pawl link force, huntkit.fea.pack5200 (pulley assumed slack: the pawl takes everything)",
        "by_case_worst_torso": {k: {"force_n": round(float(v), 1), "torso_in": t} for k, (v, t) in pick.items()},
        "max_extension_n": round(float(e["retention"]["extension"]), 1),
        "max_compression_n": round(float(e["retention"]["compression"]), 1),
        "pack_designer_estimate_n": {"extension": 1001.0, "compression": 1334.0, "rack_rating_wet": 5328.0},
    }


def deliver(sw, design_dir="designs/pack_5200", screens_dir="outputs/screens", date="20261101", log=print):
    import shutil
    from pathlib import Path
    from .sizing import plot_case_margins, plot_pareto, plot_worst_case
    design_dir, screens_dir = Path(design_dir), Path(screens_dir)
    adir = design_dir / "analysis"
    adir.mkdir(parents=True, exist_ok=True)
    screens_dir.mkdir(parents=True, exist_ok=True)
    s3 = sorted(sw["stage3"], key=lambda e: e["mass_g"])
    rec, feasible = recommend(s3)
    full = evaluate(rec["cand"], (15, 19, 23), keep_results=True)
    c = rec["cand"]
    model19 = full["kept"][19]["model"]
    crown = crown_load_summary(full)
    write_frame_yaml(full, design_dir / "frame.yaml", model19, crown)
    import yaml
    (adir / "crown_loads.yaml").write_text("# FEA crown retention loads (huntkit.fea.sizing5200), for the pack-designer\n"
                                           + yaml.safe_dump(_plain(crown), sort_keys=False))
    gov = full["governing"]
    gcase = gov["what"].split(":")[0]
    kept = full["kept"][gov["torso"]]
    if gcase not in kept["results"]:
        gcase = "meat_shelf_heavy_low"
    res = kept["results"][gcase]
    png1 = adir / "frame_sizing_worst_case.png"
    plot_worst_case(res, png1, f"Pack 5200 frame, worst case: {gcase} ({gov['torso']:g} in torso)")
    png2 = adir / "frame_sizing_pareto.png"
    plot_pareto({"stage2": sw["stage2"], "stage3": s3}, rec if feasible else None, png2)
    png3 = adir / "frame_sizing_case_margins.png"
    names = list(kept["results"]) + ["fatigue"]
    plot_case_margins({"cases": names, "torsos": (15, 19, 23),
                       "margin": {(n, t): full["per_check"].get((n, t), np.inf) for n in names for t in (15, 19, 23)}},
                      png3)
    shots = []
    for i, pth in enumerate((png1, png2, png3), start=1):
        dst = screens_dir / f"{date}_frame_{i}.png"
        shutil.copyfile(pth, dst)
        shots.append(dst)
    from .analysis import run_study
    from .report import report as write_report
    st19 = {"label": "Pack 5200 frame, 19 in torso", "frame": model19, "results": full["kept"][19]["results"],
            "joints": full["kept"][19]["joints"], "fatigue": full["kept"][19]["fatigue"]}
    write_report(st19, adir / "frame_sizing_cases_19in.md", title="Pack 5200 frame - all load cases (19 in torso)")
    md = _md(sw, full, feasible, model19, crown, gcase, png1, png2, png3)
    (adir / "frame_sizing.md").write_text(md)
    log(f"wrote {adir / 'frame_sizing.md'}; screens {[str(s) for s in shots]}")
    return {"recommended": full, "feasible": feasible, "screens": shots}


def _md(sw, e, feasible, model, crown, gcase, png1, png2, png3):
    from .pack5200 import crown_checks, plate_checks
    c = e["cand"]
    s3 = sorted(sw["stage3"], key=lambda x: x["mass_g"])
    G2OZ = 1 / 28.3495
    m = e["mass_g"]
    vs = ("under" if m <= FRAME_BUDGET_G else "OVER") + f" the {FRAME_BUDGET_G:.0f} g allocation by {abs(m - FRAME_BUDGET_G):.0f} g"
    L = ["# Pack 5200 - carbon frame sizing (pack-designer topology)", "",
         "Owner: structural-fea-engineer. Model: `huntkit/fea/pack5200.py` built from "
         "`designs/pack_5200/geometry.yaml`. Sweep: `huntkit/fea/sizing5200.py` "
         "(`python -m huntkit.fea.cli size5200`). Frame parameters: `designs/pack_5200/frame.yaml`.", "",
         "## Result", ""]
    if feasible:
        L.append(f"**Lightest design that passes every check: {m:.0f} g ({m * G2OZ:.1f} oz, {m / 453.6:.2f} lb).** "
                 f"That is {vs}. The R-15 limit is 600 g, and the premium-frame benchmark is 450-700 g.")
    else:
        L.append(f"**No design in the sweep passes every check.** The best candidate weighs {m:.0f} g "
                 f"({m * G2OZ:.1f} oz), {vs}, with a min margin of {e['margin']:.2f}. See the governing checks "
                 "and recommendations below.")
    L += ["", f"- Design: {e['label']}",
          f"- Min margin (SF / required, all checks, torsos 15/19/23 in): **{e['margin']:.2f}**. Governing: "
          f"{e['governing']['what']} at {e['governing']['torso']:g} in.", "",
          "| check | min margin |", "|---|---|"]
    for k in ("member", "buckling", "bond_avg", "bond_peak", "crown", "plate", "plate_buckling", "fatigue"):
        if k in e["per_check"]:
            L.append(f"| {k.replace('_', ' ')} | {e['per_check'][k]:.2f} |")
    L += ["", "### Mass breakdown", "", "| item | g |", "|---|---|"]
    for k, v in e["mass_items"].items():
        L.append(f"| {k} | {v:.1f} |")
    L += [f"| **total (extension posts excluded)** | **{m:.1f}** |", "",
          f"![margins]({png3.name})", "", f"![worst case]({png1.name})", "",
          f"Worst case shown: `{gcase}`. Full per-case tables at 19 in: "
          "[frame_sizing_cases_19in.md](frame_sizing_cases_19in.md).", "",
          "## Crown retention (for the pulley / rack-and-pawl sizing)", "",
          "| case | pawl force N (+ extension / - compression) | torso in |", "|---|---|---|"]
    for k, v in crown["by_case_worst_torso"].items():
        L.append(f"| {k} | {v['force_n']:.0f} | {v['torso_in']:g} |")
    ext, comp = crown["max_extension_n"], crown["max_compression_n"]
    L += ["",
          f"- FEA max extension (crown pulled up) = **{ext:.0f} N**; the pack-designer estimate is 1001 N "
          "(hipbelt-off abuse). "
          + ("The FEA value is lower, so their estimate is conservative." if ext <= 1001 else
             "**The FEA value is HIGHER than their estimate. The pack-designer must raise the required hold.**"),
          f"- FEA max compression (crown pushed down) = **{abs(comp):.0f} N**; their estimate is 1334 N. "
          "The difference comes from load placement: here the tall load sits on the shelf and its top is lashed "
          "*horizontally* to the crown, while they assumed 40 % of the load hangs on the crown. "
          "Keep their 1334 N until a lashing test shows otherwise.",
          f"- Rack rating 5328 N (wet nylon) vs. max(1.5 x FEA, designer values): margin "
          f"{5328 / max(1.5 * ext, 1.5 * abs(comp), 1001, 1334):.1f}x.",
          "- No pin holes: the pawl/rack carries the vertical load. Its mount on the crown (rack bonded to "
          "the spine, pawl housing on the upper bar) is in the model as a link at z 520. Its mass (rack 22 g, "
          "pawl housing 14 g, pulley guides 8 g) is in the total.",
          "- Seatpost-style collar alternative (owner asked): see `crown_loads.yaml` and the case report for "
          "the clamp pressure vs. the crush limit of the leg."]
    # collar numbers at the worst extension case
    kept = e["kept"]
    worst = max(((n, t) for (n, t) in crown["by_case_worst_torso"].items()), key=lambda kv: abs(kv[1]["force_n"]))
    n_, info = worst
    r = kept[info["torso_in"]]["results"][n_]
    mdl = kept[info["torso_in"]]["model_posts" if n_ == "tall_load_posts" else "model"]
    for cc in crown_checks(r, mdl):
        if cc.get("info"):
            L.append(f"  - {cc['check']} at `{n_}`: required clamp force {cc['clamp_force_n']:.0f} N per leg, "
                     f"contact pressure {cc['value']:.2f} MPa vs. leg crush limit {cc['allow']:.1f} MPa "
                     f"(first-ply failure under external pressure, knocked down) -> SF {cc['sf']:.1f}.")
    L += ["", "### Telescoping crown checks at full extension (23 in)", "",
          "| case | check | value | SF |", "|---|---|---|---|"]
    for n_ in ("drop_2p5g", "side_hill_torsion", "tall_load_posts", "hipbelt_off_abuse", "overload_haul"):
        r = kept[23]["results"][n_]
        mdl = kept[23]["model_posts" if n_ == "tall_load_posts" else "model"]
        for cc in crown_checks(r, mdl):
            if cc.get("retention") or cc.get("info"):
                continue
            if "_R" in cc["check"]:
                continue
            L.append(f"| {n_} | {cc['check']} | {cc['value']:.1f} {cc['unit']} | {cc['sf']:.2f} |")
        legs = [mm for mm in r.members if mm["group"].startswith("crown_leg")]
        lm = min(legs, key=lambda x: x["sf"])
        L.append(f"| {n_} | crown leg bending at the stay-top bushing (min member SF) | {lm['id']} | {lm['sf']:.2f} |")
    L += ["", "### Lumbar plate checks (19 in)", "", "| case | check | value | SF |", "|---|---|---|---|"]
    for n_ in ("drop_2p5g", "side_hill_torsion", "single_stay_setdown", "tall_load"):
        r = kept[19]["results"][n_]
        for pc in plate_checks(r, kept[19]["model"]):
            L.append(f"| {n_} | {pc['check']} | {pc['value']:.1f} {pc['unit']} | {pc['sf']:.2f} |")
    L += ["", "## Stock list", "",
          "| part | qty | section | wall mm | layup (inner -> outer) | centreline mm | cut mm | source |",
          "|---|---|---|---|---|---|---|---|"]
    for row in stock_rows(e, model):
        L.append(f"| {row['part']} | {row['qty']} | {row['section']} | {row['wall_mm']:.2f} | {row['layup']} | "
                 f"{row['centreline_mm']:.0f} | {row['cut_length_mm']:.0f} | {row['source']} |")
    L += [f"| lumbar plate | 1 | 250 x 140 mm | {c['plate'][1]:g} | {c['plate'][0]} | - | - | CF plate stock |"]
    if not isinstance(c["spine"], dict):
        L.append(f"| crown spine plate | 1 | {c['spine'][0]:g} x 300 mm | {c['spine'][1]:g} | cfrp_plate_quasi_iso | - | - | CF plate stock |")
    L += ["", "## Joint design", ""]
    for k, v in _joint_design(c).items():
        L.append(f"- **{k}**: {v}")
    L += ["", "## Sizing sweep and Pareto front", "",
          "Stage A: stays (round 20/22/25 mm; RW0 / RW45 / UD90 families; walls 0.8-2.0 mm) with the largest "
          "buyable crown leg that fits the bore with a >= 0.75 mm bushing, 4 leg walls. Stage B: lumbar plate "
          "(pm45 3 mm, QI 2.5/3/4 mm) x spine (QI plate 50x5 or RW45 tube 16/18/20). Stage C: bars "
          "16/18/20 mm, MMA vs. epoxy, 1 vs. 2 mm sleeves, 50 vs. 70 mm bushings. Stages A-C were screened "
          "at 15 and 23 in torso; stage D re-ran the best and the Pareto set at 15/19/23 in.", "",
          f"Evaluated: {len(sw['stage2'])} screened, {len(s3)} full checks.", "",
          f"![pareto]({png2.name})", "",
          "| mass g | min margin | feasible | governing | design |", "|---|---|---|---|---|"]
    for x in pareto(s3):
        L.append(f"| {x['mass_g']:.0f} | {x['margin']:.2f} | {'yes' if x['feasible'] else 'no'} | "
                 f"{x['governing']['what']} ({x['governing']['torso']:g} in) | {x['label']} |")
    L += ["", "Lightest full-check designs:", "", "| mass g | min margin | governing | design |", "|---|---|---|---|"]
    for x in s3[:12]:
        L.append(f"| {x['mass_g']:.0f} | {x['margin']:.2f} | {x['governing']['what']} ({x['governing']['torso']:g} in) | {x['label']} |")
    L += ["", "## Assumptions and caveats", "",
          "- The load cases are in `huntkit/fea/load_cases.py` (`pack5200_cases`): the 7 standard cases, "
          "plus `tall_load_posts` (extension posts fitted) and `hipbelt_off_abuse` (68 kg x 1.5 g, all on the "
          "shoulders, SF 1.0). The required buckling factor is 3.0, scaled by required SF / 2.0 "
          "(overload 2.25, abuse 1.5).",
          "- ASSUMPTION: the bag is in carry mode with its CG 180 mm aft (geometry.yaml bag). Its weight "
          "splits 35 % shelf pivots, 25 % low tabs, 25 % mid-bar nodes and 15 % crown top-bar tabs. The "
          "aft-offset moment is a couple: top tabs pull aft, bottom tabs bear forward.",
          "- ASSUMPTION: body springs. Hipbelt is translational at the Ti pivot (free roll), 20 / 0 / 40 N/mm. "
          "Lumbar pad bearing is on the plate centre nodes, 30 N/mm total in y. Yoke 4 / 8 / 10, lifters "
          "0 / 6 / 3, with the hip share calibrated to 80 %.",
          "- ASSUMPTION: the lumbar plate is a grillage of flat-bar strips (J = w t^3 / 6, Hambly) plus "
          "equivalent shear diagonals (excluded from buckling). Its stresses are approximate (+/-30 %). "
          "Before release, check the plate with a shell model (`huntkit.fea.plate` covers only rectangular "
          "bending). Shear buckling uses an isotropic k_s formula.",
          "- ASSUMPTION: the crown bushings are radial springs of 2e4 N/mm, free to slide axially. The pawl is "
          "an axial spring with a 2e3 N/mm lateral guide. Ring crush at the bushings uses the diametral "
          "point-load ring moment 0.318 F R / L_bushing, which is conservative: the real contact is "
          "distributed. The stay top is credited with its bonded 7075 collar.",
          "- ASSUMPTION: adhesive shear moduli (MMA 300 MPa, epoxy 800 MPa) are not in the material "
          "records. The Volkersen peak scales with sqrt(G / t_bond).",
          "- ASSUMPTION: hardware masses (hubs, boots, pivot insert, rack/pawl, bushings) are parametric "
          "estimates (+/-30 %).",
          "- Not modelled: peel at socket lips, local hub stresses, the yoke plate (counted as harness), and "
          "the extension posts (accessory, not in base weight; checked in `tall_load_posts`).", ""]
    return "\n".join(L)
