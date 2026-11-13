"""HA-LS-1 rev C production verification (owner 2026-11-06; designs/pack_5200/analysis/rev_c_verification.md).

The full production check of the Pack 5200 frame under the rev C load standard, on the parts as released:

- printed body: the socket-free PAHT-CF branch body (``spreader_layout.raster(None, 2.0)``), 2 mm voxels, FI99 rule
  (``frame_production.verify_solid``), loads from the v2 beam model of frame.yaml at torso 15 / 19 / 23 in;
- carbon crown WITH the rev C fix (frame.yaml: spine +1, legs +2, top bar +1 inner UD plies, 0.8 mm corner
  bondline), plus the as-built crown for comparison (beam model only);
- corner-bond fatigue (not run before): crown-corner bond shear at 0 -> 1.6 g bag carry <= 0.3 x lap shear;
- torso adjust: toothed rack + pawl, printed pawl cheek (304 bushing), 3:1 pulley;
- attachments: fairleads (printed cheek FE at the rev C governing loads), hinge pin, bag hooks (2200 N rated),
  meat-strap hooks, hinge bartack, lifters, the crown hood / guy bar wall, the >= 25 mm tie rule;
- spreader: Sandwich v2 with the 7 mm ROHACELL 110 core (BP-06 rev C) on the real supports, meat CG 190 mm.

Every rev C case set is enveloped: the 9 cases with the bag couple on the crown top bar (tag ``C``) and the 5 bag
cases with the couple on the IM3 hooks (tag ``C_im3``); the worse governs. The engine is
``huntkit.gendesign.frame_cg_recheck`` (same beam extraction, voxel solve, crown checks), run on the rev C cases.

Run: ``python -m huntkit.gendesign.rev_c_verification``   (about 20-30 min on 4 cores)
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

from . import frame_cg_recheck as R
from . import frame_topopt as ft

ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
SCREENS = REPO_ROOT / "outputs" / "screens"
RESULTS = ANALYSIS / "rev_c_verification_results.json"
DOC = ANALYSIS / "rev_c_verification.md"
DATE = "2026-11-06"
SHOT = "20261106_revc"
TORSOS = R.TORSOS
TAGS = {"crown_bar": "C", "strap_upper": "C_im3"}
BOND_FAT_RATIO = 0.3        # HA-LS-1 fatigue rule: bond shear <= 0.3 x lap shear at the 1.6 g walking peak
G_WALK = 1.6
BAG_HOOK_N = 2200.0         # bag_attachment.md section 3: one rated part >= 2200 N at all four bag-hook points
MEAT_HOOK_N = 1500.0        # meat-strap hooks (bag_attachment.md section 3; bag_attach.HOOK_N)


def rel(p) -> str:
    return str(Path(p).resolve().relative_to(REPO_ROOT))


# ============================================================================ beam model
def beam_runs(torsos=TORSOS, over: dict | None = None, buckling: bool = True, suffix: str = "", log=print):
    """Every rev C case set x torso on the beam model of frame.yaml (production crown unless ``over``).
    The top bar is split at x +/-95 so the hood ears sit on nodes. Returns (LoadSets, crown rows)."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import TABLE, ls1_envelope
    over = over or {}
    env = ls1_envelope("C")
    sets, rows = [], []
    for t in torsos:
        fm = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=False, **over),
                             95.0)
        fmp = None
        for variant, cases in env.items():
            tag = TAGS[variant] + suffix
            for c in cases:
                c = copy.copy(c)
                c.params = dict(c.params)
                c.buckling = buckling and variant == "crown_bar" and c.kind != "setdown"
                m = fm
                if c.name == "tall_load_posts":
                    fmp = fmp or R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t),
                                                                       extension_posts=True, **over), 95.0)
                    m = fmp
                res = c.run(m)
                ls = ft._extract(res, m, c, t, TABLE)
                ls.key = f"{tag}:{ls.key}"
                sets.append(ls)
                rows.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": float(c.required_sf),
                             "g": float(c.g_factor), **R._crown_rows(res, m, c)})
        if log:
            log(f"  [rev C{suffix}] beam model torso {t} in")
    return sets, rows


def corner_bond_fatigue(rows: list, tag: str) -> dict:
    """HA-LS-1 fatigue rule on the crown-corner bonds: shear at 0 -> 1.6 g x 68 kg (bag carry, C1 load path)
    <= 0.3 x the hot/wet lap shear. ``_crown_rows`` gives, per run, the average-shear SF / factor and the raw
    Volkersen-peak SF at the limit load; static carry is at 1 g, so the 1.6 g SF is 0.3 x SF_1g / 1.6.
    Reported on the average shear (the rule as written) and on the elastic peak (conservative: no yield
    redistribution is credited in high-cycle fatigue). The meat case at 1.6 g is an information row."""
    out = {}
    for case, g0 in (("static_carry", 1.0), ("meat_straps", 2.0)):
        vals = []
        for r in rows:
            if r["scenario"] != tag or r["case"] != case or "crown_corner" not in r["joints"]:
                continue
            a, p, mem = r["joints"]["crown_corner"]
            avg_raw = a * r["factor"]                  # SF of the average shear at the case limit load
            k = BOND_FAT_RATIO * g0 / G_WALK
            vals.append({"set": f"{case}|{r['torso']:g}", "sf_avg": avg_raw * k, "sf_peak": p * k, "member": mem})
        if vals:
            out[case] = {"avg": min(vals, key=lambda v: v["sf_avg"]), "peak": min(vals, key=lambda v: v["sf_peak"])}
    return out


# ============================================================================ attachments
def attachments(fine_h: float = 1.0, log=print) -> dict:
    """Fairleads, pin, hooks and bartack at the rev C governing loads (both couple variants), next to the rev B
    record (``bag_attach.case_loads()``); crown-bar wall under the hood and a guy; the >= 25 mm tie rule."""
    from huntkit.fea.load_standard import TIE_WEBBING_MIN_MM, ls1_envelope, tie_bearing_ok
    from . import bag_attach as BA
    from .frame_branch import stay_radius
    env = ls1_envelope("C")
    rows_c = BA.case_loads(cases=env["crown_bar"])
    rows_i = BA.case_loads(cases=env["strap_upper"])
    for r in rows_i:
        r["case"] = r["case"] + "@IM3"
    gov_c = BA.governing(rows_c + rows_i)
    gov_b = BA.governing(BA.case_loads(rev="B"))
    host = {"hinge": float(stay_radius(60.0, BA.SCALE)), "im3": float(stay_radius(520.0, BA.SCALE))}
    pa = BA._paht()
    fea = {}
    for key in ("hinge", "im3"):
        g_ = gov_c[key]
        t0 = time.time()
        # BL-045: the cheek is solved on the geometry the print carries (h1_fairleads.station_geom): the BL-042
        # hinge (saddle, pin 10.1 mm up, 20 mm throat) and the BL-045 IM3 eye fairlead (28 mm cheek). Before BL-045
        # this ran the 2026-11-01 module constants for both, so the record kept the replaced hinge's 2.97.
        # BL-045 also gives IM3 the eye clearance (saddle root stopping 1 mm above the crown bore), so the cheek is
        # solved with h1_fairleads.fairlead_fea (solve_fairlead's model, plus the empty bore on the sleeve stations).
        from .h1_fairleads import fairlead_fea, station_geom
        gm = station_geom(key)
        bore = None if key == "hinge" else BA.SLEEVE_BORE_R_REAM
        fr = fairlead_fea(gm, host[key], {"revC": [g_.get("fx", 0.0), g_["fy"], g_["fz"]]}, h=fine_h, bore_r=bore)
        rr = fr["loads"]["revC"]
        row = {"sf": rr["sf"], "fi99": rr["fi99"], "fi_max": rr["fi_max"], "added_g": fr["added_g"], "h": fine_h}
        row.update(station=key, case=g_["case"], force_n=g_["n"], g_times_req=g_["g_times_req"],
                   geometry=("BL-042 HINGE_GEOM" if key == "hinge" else "BL-045 eye_geom('im3'), 28 mm cheek, bore empty"),
                   sf_fatigue=BA._fatigue_sf(row["fi99"], g_["g_times_req"], pa["fat"]),
                   sf_creep=BA._creep_sf(row["fi99"], g_["g_times_req"], pa["rupture"]))
        fea[key] = row
        if log:
            log(f"  fairlead {key}: {g_['n']:.0f} N ({g_['case']}) SF {row['sf']:.2f} fatigue {row['sf_fatigue']:.2f} "
                f"({time.time() - t0:.0f} s)")
    pin = BA.pin_check(gov_c["hinge"]["n"], gov_c["hinge"]["g_times_req"])
    # hooks: bag hooks carry the bag couple (bag cases, IM2 / IM3 eyes); meat-strap hooks carry the strap pulls
    bag_cases = {"static_carry", "drop_2p5g", "side_hill_torsion", "hipbelt_off_abuse"}
    bag_f, meat_f = [], []
    for r in rows_c + rows_i:
        base = r["case"].split("@")[0]
        for nid, f in r.get("nodes", {}).items():
            st = BA._NODE_STATION.get(nid)
            if st in ("im2", "im3") and base in bag_cases:
                bag_f.append((f["n"], r["case"], nid))
            if st in ("im1", "im2", "im3") and base not in bag_cases:
                meat_f.append((f["n"], r["case"], nid))
    bmax, mmax = max(bag_f), max(meat_f)
    from huntkit.fea.load_standard import TOP_ANCHOR_HOOD_GUYS as TA
    f5 = 2.0 * 1.5                                          # C5 g x factor
    hood_f = f5 * TA["hood_n"]
    guy_f = f5 * TA["guy_n"]
    bar_hood = R.bar_local(hood_f, 25.0, pocket_line_n_mm=hood_f / (2 * TA["hood_half_span_mm"]), over={})["pocket"]
    bar_hood["F_n"] = hood_f
    bar_guy = R.bar_local(guy_f, 30.0, over={})["tie"]
    ties = {f"{w:g}": {"sf": R.bar_local(210.0, w, over={})["tie"]["sf"], "allowed": tie_bearing_ok(w)}
            for w in (20.0, 25.0, 38.0)}
    lif = BA.lifter_and_hip()
    return {"gov_c": {k: {kk: vv for kk, vv in v.items() if kk != "group"} for k, v in gov_c.items()},
            "gov_b": {k: {kk: vv for kk, vv in v.items() if kk != "group"} for k, v in gov_b.items()},
            "fairlead_fea": fea, "pin": pin,
            "bag_hook": {"n": bmax[0], "case": bmax[1], "node": bmax[2], "rated_n": BAG_HOOK_N, "sf": BAG_HOOK_N / bmax[0]},
            "meat_hook": {"n": mmax[0], "case": mmax[1], "node": mmax[2], "rated_n": MEAT_HOOK_N,
                          "sf": MEAT_HOOK_N / mmax[0]},
            "bartack": {"n": gov_c["hinge"]["n"], "rated_n": BA.BARTACK_N, "sf": BA.BARTACK_N / gov_c["hinge"]["n"]},
            "lifter": {"webbing_sf": lif["webbing_sf"], "ladder_sf": lif["ladder_sf"],
                       "ladder_sf_abuse": lif["ladder_sf_abuse"]},
            "bar_hood_line": bar_hood, "bar_guy_30mm": bar_guy, "tie_rule_mm": TIE_WEBBING_MIN_MM,
            "tie_210n": ties}


# ============================================================================ spreader
def spreader_check(log=print) -> dict:
    """Sandwich v2, 7 mm core (BP-06 rev C), at the rev C meat CG (``spreader.MEAT_CG_MM`` = 190): the release
    procedure (4 mm grid + 24 mm bone grid, then 2 mm at the named positions; the worse governs), and the 6 mm
    part at rev C for comparison (2 mm, named positions)."""
    from . import spreader as S
    opts = {o.key: o for o in S.options()}
    opt = opts[S.PRODUCTION_KEY]
    t0 = time.time()
    ch = S.evaluate(opt, h=4.0, step=24.0, keep_fields=True)
    fine = S.evaluate(opt, h=2.0, step=None)
    c6 = S.evaluate(opts["sw110c6d"], h=2.0, step=None)
    from .spreader_layout import sandwich_recheck
    lean = sandwich_recheck(key=opt.key)            # lumbar-pan skin reference (spreader_layout.md re-check)
    if log:
        log(f"  spreader {opt.key}: {time.time() - t0:.0f} s")
    mesh = {"4 mm": {k: ch.get(k) for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min", "clear_fact_min")},
            "2 mm": {k: fine.get(k) for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min", "clear_fact_min")}}
    for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min"):
        ch[k] = min(ch[k], fine[k])
    ch["checks"]["fpf"] = ch["sf_fpf"] >= 1.0
    ch["checks"]["fatigue"] = ch["sf_fatigue"] >= 1.0
    ch["checks"]["sandwich_local"] = ch["sandwich_sf_min"] >= 1.0
    ch["passes"] = all(ch["checks"].values())
    ch["passes_sheet"] = all(v for k, v in ch["checks"].items() if k != "skin_pressure")
    return {"opt": opt, "chosen": ch, "fine": fine, "c6": c6, "lean": lean, "mesh_check": mesh,
            "meat_cg_mm": S.MEAT_CG_MM, "rail": S.RAIL_DESIGN}


def write_spreader_files(sp: dict, log=print) -> dict:
    """Cut DXF, clip DXF (slot depth follows the 7.44 mm sheet), 1:1 drawing + PNG screen, and the updated
    spreader_results.json (the rev B record is kept under ``rev_b_record``)."""
    from . import spreader as S
    from . import spreader_report as SR
    opt, ch = sp["opt"], sp["chosen"]
    t = opt.lam.thickness
    dxf = SR.CUT / "spreader_v2_cut.dxf"
    S.write_dxf(opt, dxf)
    clips = SR.write_clip_files(t)
    clip = SR.clip_check(ch, t)
    dr = SR.write_drawing(opt, ch, clips, date=DATE.replace("-", ""), screen=SCREENS / f"{SHOT}_2.png")
    cost = SR.cost_table(opt, ch)
    path = ANALYSIS / "spreader_results.json"
    old = json.loads(path.read_text())
    keep = {k: old[k] for k in ("date", "chosen_key", "chosen", "mesh_check", "clip", "clip_mass_g", "cost",
                                 "cost_total_usd", "saved_g", "files", "doc") if k in old}
    if "rev_b_record" in old:
        keep = old["rev_b_record"]
    strip = {k: v for k, v in SR._strip(ch).items() if k != "rows"}
    old_clip_t = 6.0 + 2 * 0.22
    new = {**old,
           "date": SHOT.split("_")[0], "standard": "HA-LS-1 rev C (meat CG 190 mm)", "part_rev": S.PART_REV,
           "back_rail": getattr(S.RAIL_DESIGN, "key", str(S.RAIL_DESIGN)),
           "chosen_key": opt.key, "chosen": strip, "chosen_rows": SR._strip(ch)["rows"],
           "mesh_check": sp["mesh_check"], "clip": clip, "clip_mass_g": clips["mass_g"],
           "clip_slot_depth_change_mm": float(t - old_clip_t),
           "cost": cost, "cost_total_usd": float(sum(c["usd"] for c in cost)),
           "saved_g": float(old["old_part_g"] - ch["mass_g"]),
           "files": {**old.get("files", {}),
                     "water-jet / CNC cut file (DXF, mm, layers CUT / MARK / TEXT)": rel(dxf),
                     "clip profile (DXF, extrude 10 mm)": clips["dxf"],
                     "dimensioned drawing, 1:1 on A3 (PDF)": dr["pdf"]},
           "open_items": [{"item": "walking skin pressure over the two back rails exceeds 14 kPa at the rev C meat CG",
                           "value_kpa": float(ch["skin_peak_kpa"]), "limit_kpa": float(S.PEAK_KPA),
                           "owner": "pack-designer (back panel / rails); not a sheet check, not part of HA-LS-1",
                           "source": "analysis/frame_cg_recheck.md section 5, rev_c_verification.md"}]
           if ch["skin_peak_kpa"] > S.PEAK_KPA else [],
           "rev_b_record": keep}
    new["screens"] = [s for s in old.get("screens", [])]
    path.write_text(json.dumps(new, indent=1, default=SR._json_default))
    if log:
        log(f"  wrote {rel(path)}, {rel(dxf)}, {clips['dxf']}, {dr['pdf']}")
    return {"dxf": rel(dxf), "clip_dxf": clips["dxf"], "pdf": dr["pdf"], "png": dr["png"], "clip": clip,
            "clip_mass_g": clips["mass_g"], "cost_usd": new["cost_total_usd"], "t_mm": t}


# ============================================================================ masses
def mass_table(body_g: float) -> dict:
    """Load-path members (g). Crown from frame.yaml via the beam model's hardware mass, as built and fixed."""
    from huntkit.fea.frames import build_frame_from_yaml
    fixed = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)["hardware"]["items"]
    built = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0, **R.rev_b_crown())["hardware"]["items"]
    rows = {}
    for k in ("tubes: crown_leg", "tubes: crown_top_bar", "tubes: crown_spine", "adhesive (incl. lumbar-plate bond)"):
        rows[k] = {"rev_b": float(built.get(k, 0.0)), "rev_c": float(fixed.get(k, 0.0))}
    fx = R.fix_mass_total()
    return {"printed_body_g": float(body_g), "crown_beam_model": rows, "crown_fix_g": fx,
            "crown_fix_beam_delta_g": float(sum(v["rev_c"] - v["rev_b"] for v in rows.values()))}


FRAME_MASS = ANALYSIS / "frame_mass_production.json"


def write_frame_mass(body_g: float, path: Path = FRAME_MASS) -> dict:
    """Frame-mass record the weight budget reads (designs/pack_5200/build_geometry.py, frame row).

    The printed body is booked from the PRODUCTION raster (the socket-free print body, 2 mm, ``solid_mass_g``), not
    from the 1.05-scale study body in generative_branch_results.json (774 g). The non-body frame items keep the
    generative_branch_results.json basis (frame_g - body_g - the retired QI sheet + M4 sets, spreader_results.json
    old_part_g). The crown gets the rev C fix (+22.0 g, frame_cg_recheck.fix_mass_total)."""
    gb = json.loads((ANALYSIS / "generative_branch_results.json").read_text())
    sp = json.loads((ANALYSIS / "spreader_results.json").read_text())
    old_sheet = float(sp["old_part_g"])
    non_body = float(gb["frame_g"]) - float(gb["body_g"]) - old_sheet
    fix = R.fix_mass_total()
    rec = {"date": DATE, "standard": "HA-LS-1 rev C",
           "printed_body_g": round(float(body_g), 1),
           "printed_body_basis": "spreader_layout.raster(None, 2.0) + frame_branch.solid_mass_g: the socket-free "
                                 "production print body (designs/pack_5200/print/frame/)",
           "study_body_g_superseded": round(float(gb["body_g"]), 1),
           "non_body_g": round(non_body, 1),
           "non_body_basis": f"generative_branch_results.json frame_g {gb['frame_g']:.1f} - body_g {gb['body_g']:.1f} - "
                             f"retired QI sheet + M4 sets {old_sheet:.1f} (spreader_results.json old_part_g): carbon "
                             "crown as built, rack + pawl + guides, bushings, Ti hip-pivot mount, pawl bushings, inserts",
           "crown_fix_g": round(float(fix["total"]), 1),
           "crown_fix_lines_g": {k: round(float(v), 2) for k, v in fix.items() if k != "total"},
           "frame_g": round(float(body_g) + non_body + float(fix["total"]), 1)}
    path.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


# ============================================================================ driver
def run(log=print, spreader: bool = True, attach: bool = True, write_files: bool = True) -> dict:
    from .frame_branch import solid_mass_g
    from .spreader_layout import raster
    t0 = time.time()
    sets, rows = beam_runs(log=log)
    _, rows_ab = beam_runs(over=R.rev_b_crown(), buckling=False, suffix="_asbuilt", log=log)
    log("raster production body (socket-free branch, 2 mm)")
    dom, solid = raster(None, 2.0)
    body_g = solid_mass_g(solid, 2.0)
    secs = {s.key for s in sets if s.case in ("drop_2p5g", "side_hill_torsion", "meat_straps", "hipbelt_off_abuse",
                                               "overload_haul")}
    vr = R.verify_sets(dom, solid, sets, keep_env=tuple(TAGS.values()), sections=secs, log=log)
    tags = list(TAGS.values())
    body = {tg: R.summarize_body(vr["rows"], tg, vr["fat_ratio"], vr["creep_ratio"]) for tg in tags}
    crown = {tg: R.crown_summary(rows + rows_ab, tg) for tg in tags + [t + "_asbuilt" for t in tags]}
    bond_fat = {tg: corner_bond_fatigue(rows + rows_ab, tg) for tg in tags + [t + "_asbuilt" for t in tags]}
    ta = R.torso_adjust(rows, tags=tags)
    cheek = {tg: R.pawl_cheek(v["pawl_cheek_force"]["factored_yz"]) for tg, v in ta.items()}
    sj = R.segment_joint(vr["rows"])
    ctx = {"date": DATE, "standard": "HA-LS-1 rev C", "body_g": body_g, "body": body, "crown": crown,
           "corner_bond_fatigue": bond_fat, "torso_adjust": ta, "pawl_cheek": cheek, "segment_joint": sj,
           "body_rows": vr["rows"], "crown_rows": rows + rows_ab, "solve_s": vr["seconds"],
           "mass": mass_table(body_g)}
    ctx["_env"], ctx["_centers"] = vr["env"], vr["centers"]
    del dom, solid, vr
    if attach:
        log("attachments")
        ctx["attachments"] = attachments(log=log)
    if spreader:
        log("spreader (7 mm core, meat CG 190)")
        sp = spreader_check(log=log)
        ctx["spreader"] = {"key": sp["opt"].key, "meat_cg_mm": sp["meat_cg_mm"], "mesh_check": sp["mesh_check"],
                           "rail": getattr(sp["rail"], "key", str(sp["rail"])),
                           "chosen": {k: v for k, v in sp["chosen"].items() if not k.startswith("_") and k != "rows"},
                           "c6": {k: v for k, v in sp["c6"].items() if k != "rows"}, "lean_recheck": sp["lean"]}
        if write_files:
            ctx["spreader_files"] = write_spreader_files(sp, log=log)
    ctx["summary"] = summary_rows(ctx)
    ctx["seconds"] = time.time() - t0
    return ctx


def _min_case(body: dict) -> tuple:
    c = min(body["cases"].items(), key=lambda kv: kv[1]["sf"])
    return c[0], c[1]


def summary_rows(ctx: dict) -> list[dict]:
    """One row per checked item: margin = SF / requirement (pass >= 1.0), with the governing set."""
    out = []

    def add(part, check, val, where, basis, req=1.0):
        if val is None:
            return
        out.append({"part": part, "check": check, "margin": float(val) / req, "where": where, "basis": basis})

    for tg, lab in (("C", "couple on crown bar"), ("C_im3", "couple on IM3 hooks")):
        b = ctx["body"][tg]
        add("printed body", f"strength, {lab}", b["sf_min"], f"{b['governing']}, {b['where']}", "1/FI99, factored")
        add("printed body", f"fatigue, {lab}", b["sf_fatigue"], b["fatigue_set"], "C1 at 1.6 g, PAHT 0.3")
        add("printed body", f"creep-rupture, {lab}", b["sf_creep"], b["fatigue_set"], "C1 at 1 g, 40 C 8 h, 0.4")
    for tg, lab in (("C", "crown bar"), ("C_im3", "IM3")):
        cs = ctx["crown"][tg]
        for k, nm in (("crown_spine", "spine FPF"), ("crown_leg", "legs FPF"), ("crown_top_bar", "top bar FPF"),
                      ("corner_bond_avg", "corner bond average"), ("corner_bond_peak", "corner bond Volkersen peak"),
                      ("leg_ring_crush", "leg ring crush"), ("bushing_bearing", "bushing bearing"),
                      ("fatigue", "member fatigue (FI <= 0.5 at 1.6 g)"), ("buckling", "buckling (>= 1.5 x factor)")):
            if k in cs:
                add("carbon crown (fixed)", f"{nm}, {lab}", cs[k]["sf"], cs[k]["set"], "beam model, knocked down")
        bf = ctx["corner_bond_fatigue"][tg].get("static_carry")
        if bf:
            add("carbon crown (fixed)", f"corner-bond fatigue, average, {lab}", bf["avg"]["sf_avg"], bf["avg"]["set"],
                "tau(1.6 g) <= 0.3 x lap shear")
            add("carbon crown (fixed)", f"corner-bond fatigue, Volkersen peak, {lab}", bf["peak"]["sf_peak"],
                bf["peak"]["set"], "peak tau(1.6 g) <= 0.3 x lap shear")
    for tg in ("C", "C_im3"):
        ta, ch = ctx["torso_adjust"][tg], ctx["pawl_cheek"][tg]
        add("torso adjust", f"rack ({tg})", ta["rack_worst"]["rack_sf"], ta["rack_worst"]["set"], "5328 N / factored axial")
        add("torso adjust", f"pawl cheek, 304 bushing ({tg})", ch["sf_fi"], ta["pawl_cheek_force"]["set"], "1/FI99")
        add("torso adjust", f"cam hold, walking ({tg})", ta["cam_hold_sf_walk"], "static carry x 1.6", "700 N slip")
    sj = ctx.get("segment_joint") or []
    if sj:
        w = min(sj, key=lambda r: r["pullout_sf"])
        add("printed body", "segment joint dowel pull-out (z 234)", w["pullout_sf"], w["set"], "MMA 6 MPa hot/wet")
    a = ctx.get("attachments")
    if a:
        for k in ("hinge", "im3"):
            f = a["fairlead_fea"][k]
            add("attachments", f"fairlead {k} cheek strength", f["sf"], f["case"], "1/FI99, 1 mm mesh")
            add("attachments", f"fairlead {k} cheek fatigue", f["sf_fatigue"], f["case"], "1.6 g, PAHT 0.3")
        add("attachments", "hinge pin 7075 shear yield", a["pin"]["sf_yield"], a["gov_c"]["hinge"]["case"], "factored")
        add("attachments", "hinge UHMWPE sleeve bearing", a["pin"]["sleeve_sf"], a["gov_c"]["hinge"]["case"], "factored")
        add("attachments", "bag hooks (2200 N rated)", a["bag_hook"]["sf"], a["bag_hook"]["case"], "rated / factored")
        add("attachments", "meat-strap hooks (1500 N)", a["meat_hook"]["sf"], a["meat_hook"]["case"], "rated / factored")
        add("attachments", "hinge-eye bartack", a["bartack"]["sf"], a["gov_c"]["hinge"]["case"], "2700 N / factored")
        add("attachments", "crown bar wall under the hood", a["bar_hood_line"]["sf"],
            f"C5 {a['bar_hood_line']['F_n']:.0f} N factored", "ring, FPF")
        add("attachments", "crown bar wall under a guy (30 mm)", a["bar_guy_30mm"]["sf"],
            f"C5 {a['bar_guy_30mm']['F_n']:.0f} N factored", "ring, FPF")
        add("attachments", "crown bar wall, 210 N tie on 25 mm webbing", a["tie_210n"]["25"]["sf"], "generic tie",
            ">= 25 mm rule")
    sp = ctx.get("spreader")
    if sp:
        c = sp["chosen"]
        add("spreader 7 mm core", "first-ply failure", c["sf_fpf"], c["fpf_where"], "factored meat + bone")
        add("spreader 7 mm core", "fatigue (FI <= 0.5 at 1.6 g)", c["sf_fatigue"], c["fpf_where"], "walking")
        add("spreader 7 mm core", "sandwich local (core shear, wrinkling, crush)", c["sandwich_sf_min"], "bone patch",
            "factored")
        add("spreader 7 mm core", "no bottoming: walking air / 3 mm mesh", c["clear_walk_min"] / 3.0, "walking", "air >= 3 mm")
        add("spreader 7 mm core", "skin pressure over the rails (comfort, <= 14 kPa)", 14.0 / c["skin_peak_kpa"],
            f"{c['skin_peak_kpa']:.2f} kPa, {c.get('skin_where', '')}", f"rail {sp.get('rail', '')}, Golriz 2017")
    return out


def save(ctx: dict, path: Path = RESULTS) -> Path:
    pub = {k: v for k, v in ctx.items() if not k.startswith("_")}
    path.write_text(json.dumps(R._jsonable(pub), indent=1, default=str))
    return path


# ============================================================================ screens
ABBR = {"printed body": "body", "carbon crown (fixed)": "crown", "torso adjust": "torso adj.",
        "attachments": "attach.", "spreader 7 mm core": "spreader"}

def plot_summary(ctx: dict, path: Path | None = None) -> str:
    """Rev C margin summary: one bar per check (worst of both couple variants), pass line at 1.0."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import save as save_fig
    path = path or SCREENS / f"{SHOT}_1.png"
    rows = ctx["summary"]
    # worst of the two couple variants per check
    best = {}
    for r in rows:
        k = (r["part"], r["check"].replace(", couple on crown bar", "").replace(", couple on IM3 hooks", "")
             .replace(", crown bar", "").replace(", IM3", "").replace(" (C)", "").replace(" (C_im3)", ""))
        if k not in best or r["margin"] < best[k]["margin"]:
            best[k] = {**r, "label": f"{ABBR[r['part']]}: {k[1]}"}
    items = sorted(best.values(), key=lambda r: (["printed body", "carbon crown (fixed)", "torso adjust",
                                                   "attachments", "spreader 7 mm core"].index(r["part"]), r["margin"]))
    cols = {"printed body": "#2a78d6", "carbon crown (fixed)": "#1baf7a", "torso adjust": "#7a5fd6",
            "attachments": "#eda100", "spreader 7 mm core": "#eb6834"}
    fig, ax = plt.subplots(figsize=(8.0, 0.30 * len(items) + 1.6))
    y = np.arange(len(items))[::-1]
    vals = np.array([min(r["margin"], 4.0) for r in items])
    ax.barh(y, vals, color=[cols[r["part"]] for r in items], height=0.7)
    for yi, r, v in zip(y, items, vals):
        ax.text(v + 0.04, yi, f"{r['margin']:.2f}" + (" >" if r["margin"] > 4.0 else ""), va="center", fontsize=7.5)
    ax.set_yticks(y)
    ax.set_yticklabels([r["label"] for r in items], fontsize=7.5)
    ax.axvline(1.0, color="#b03a2e", lw=1.5)
    ax.text(1.02, y[0] + 0.9, "required 1.0", color="#b03a2e", fontsize=8)
    ax.set_xlim(0, 4.4)
    ax.set_xlabel("margin = SF / requirement (worst of crown-bar and IM3 couple, all torsos)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=p) for p, c in cols.items()], fontsize=7, loc="upper right")
    ax.set_title("HA-LS-1 rev C production check: bag 205 @ z 550, meat 190, tall 185, hood + guys", fontsize=9.5)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    save_fig(fig, path)
    return rel(path)


# ============================================================================ document
def _f(v, n=2):
    return "–" if v is None else f"{v:.{n}f}"


def write_doc(ctx: dict, screens: list) -> str:
    from huntkit.fea.load_standard import TOP_ANCHOR_HOOD_GUYS as TA, revision
    Rc = revision("C")
    b, bi = ctx["body"]["C"], ctx["body"]["C_im3"]
    cr, ci = ctx["crown"]["C"], ctx["crown"]["C_im3"]
    ca, cai = ctx["crown"]["C_asbuilt"], ctx["crown"]["C_im3_asbuilt"]
    L = []
    a = L.append
    a("# HA-LS-1 rev C production verification")
    a("")
    a(f"Owner: structural-fea-engineer, {DATE}. Standard: **HA-LS-1 rev C** ([load_standard.md](load_standard.md) §4.2, "
      "owner decision 2026-11-06 in `docs/DECISIONS.md`). Code: `huntkit/gendesign/rev_c_verification.py` "
      "(engine: `frame_cg_recheck.py`). Results: [rev_c_verification_results.json](rev_c_verification_results.json). "
      "Tests: `tests/test_load_standard_rev_c.py`, `tests/test_rev_c_verification.py`.")
    a("")
    a("```")
    a("python -m huntkit.gendesign.rev_c_verification      # about 25 min on 4 cores")
    a("```")
    a("")
    a(f"Rev C inputs: bag cases (C1–C4, C8) **{Rc['bag_cg_mm']:g} mm** aft at CG z **{Rc['bag_cg_z_mm']:g}**; meat "
      f"cases (C5, C7) **{Rc['meat_cg_mm']:g} mm**; tall cases (C6, C6p) **{Rc['tall_cg_mm']:g} mm**; bag couple on the "
      "crown top bar **and** on the IM3 hooks (worse governs); crown hood 52.5 N/g + 2 guys 34.6 N/g each in C5 / C7; "
      "ties on the bar ≥ 25 mm webbing. Parts as released: socket-free PAHT-CF branch body, carbon crown **with the "
      "rev C fix** (frame.yaml), Sandwich v2 spreader with the **7 mm** core (BP-06 rev C).")
    a("")
    a("## Summary: every load-path part, rev C, worst torso")
    a("")
    a("Margin = SF / requirement; pass ≥ 1.00. Each row is the worse of the crown-bar and the IM3 couple variant unless "
      "the check says which.")
    a("")
    a("| part | check | margin | governing set / location | basis | pass |")
    a("|---|---|---:|---|---|---|")
    for r in ctx["summary"]:
        a(f"| {r['part']} | {r['check']} | **{r['margin']:.2f}** | {r['where']} | {r['basis']} | "
          f"{'yes' if r['margin'] >= 1.0 else '**NO**'} |")
    fails = [r for r in ctx["summary"] if r["margin"] < 1.0]
    a("")
    if fails:
        a("**Fails:** " + "; ".join(f"{r['part']} {r['check']} {r['margin']:.2f}" for r in fails) + ".")
    else:
        a("**Every HA-LS-1 rev C check passes** on the released parts.")
    sp = ctx.get("spreader")
    if sp:
        c = sp["chosen"]
        a("")
        if c["skin_peak_kpa"] <= 14.0:
            a(f"Comfort (not HA-LS-1): walking **skin pressure over the back rails {c['skin_peak_kpa']:.2f} kPa** at the "
              f"190 mm meat CG, against the 14 kPa limit (Golriz 2017), with the released rails (`spreader.RAIL_DESIGN` "
              f"= `back_rail.released()`, {sp.get('rail', '')}: 120 mm L200 rails on 80 mm 1 mm-twill backers, "
              "pack-designer D-32). It agrees with the pack-designer's 13.77 kPa (named positions, 2 mm); the 24 mm bone grid "
              f"finds the worst at {c.get('skin_where', '')}. With the old 100 mm rails it was 15.5 kPa. Margin to the limit is small (1 %).")
        else:
            a(f"Not part of HA-LS-1, flagged: walking **skin pressure over the back rails {c['skin_peak_kpa']:.1f} kPa** "
              "against the 14 kPa comfort limit (Golriz 2017) at the 190 mm meat CG. **Owner: pack-designer**.")
    a("")
    a("## 1. Printed body (2 mm voxels, FI99), min margin per case")
    a("")
    a("| case | factor | couple on crown bar | couple on IM3 | location (crown bar) |")
    a("|---|---:|---:|---:|---|")
    for n in R.ORDER:
        x = b["cases"].get(n)
        y = bi["cases"].get(n)
        if not x:
            continue
        a(f"| {R.CODE[n]} {n} | {x['factor']:g} | {x['sf']:.2f} ({x['torso']:g}) | "
          f"{_f(y['sf']) + ' (' + format(y['torso'], 'g') + ')' if y else '–'} | {x['where']} |")
    a(f"| fatigue (C1 at 1.6 g) | | {b['sf_fatigue']:.2f} | {bi['sf_fatigue']:.2f} | |")
    a(f"| creep-rupture (C1 at 1 g, 40 °C) | | {b['sf_creep']:.2f} | {bi['sf_creep']:.2f} | |")
    if b.get("sf_fatigue_meat_info"):
        a(f"| info: fatigue with the meat at 1.6 g | | {b['sf_fatigue_meat_info']:.2f} | | |")
    a("")
    a(f"Printed body mass on the 2 mm raster: **{ctx['body_g']:.0f} g**.")
    sj = ctx.get("segment_joint") or []
    if sj:
        w = min(sj, key=lambda r: r["pullout_sf"])
        a(f"Segment joint at z 234 (2 × 5 mm dowels per flange, 35 mm embed): worst pull-out SF {w['pullout_sf']:.2f} "
          f"({w['set']}).")
    a("")
    a("## 2. Carbon crown with the rev C fix (beam model)")
    a("")
    a("| check | fixed, crown bar | fixed, IM3 | as built, crown bar | as built, IM3 |")
    a("|---|---:|---:|---:|---:|")
    for k, nm in (("crown_spine", "spine FPF"), ("crown_leg", "legs FPF"), ("crown_top_bar", "top bar FPF"),
                  ("corner_bond_avg", "corner bond average"), ("corner_bond_peak", "corner bond Volkersen peak"),
                  ("leg_ring_crush", "leg ring crush"), ("bushing_bearing", "UHMWPE bushing bearing"),
                  ("fatigue", "member fatigue"), ("buckling", "buckling")):
        a(f"| {nm} | " + " | ".join(
            (f"{d[k]['sf']:.2f} ({d[k]['set']})" if k in d else "–") for d in (cr, ci, ca, cai)) + " |")
    a("")
    a("### 2.1 Corner-bond fatigue (new)")
    a("")
    a("HA-LS-1 fatigue rule for bonds: shear at 0 → 1.6 g × 68 kg ≤ 0.3 × lap shear (MMA on CFRP, × 0.8 hot/wet). "
      "From the C1 load path (1 g), SF_fat = 0.3 × SF(1 g) / 1.6. The rule names the shear, not which one; both "
      "are reported. The elastic Volkersen peak is the conservative reading (no yield redistribution in high-cycle "
      "fatigue).")
    a("")
    a("| crown | variant | average: SF (set) | Volkersen peak: SF (set) | info: meat at 1.6 g, peak |")
    a("|---|---|---:|---:|---:|")
    for tg, crown_lab, var in (("C", "fixed (0.8 mm)", "crown bar"), ("C_im3", "fixed (0.8 mm)", "IM3"),
                               ("C_asbuilt", "as built (0.5 mm)", "crown bar"), ("C_im3_asbuilt", "as built (0.5 mm)", "IM3")):
        bf = ctx["corner_bond_fatigue"][tg]
        sc = bf.get("static_carry")
        mt = bf.get("meat_straps")
        if not sc:
            continue
        a(f"| {crown_lab} | {var} | {sc['avg']['sf_avg']:.2f} ({sc['avg']['set']}) | {sc['peak']['sf_peak']:.2f} "
          f"({sc['peak']['set']}) | {(_f(mt['peak']['sf_peak']) if mt else '–')} |")
    a("")
    a("## 3. Torso adjust")
    a("")
    a("| | crown bar | IM3 |")
    a("|---|---:|---:|")
    t1, t2 = ctx["torso_adjust"]["C"], ctx["torso_adjust"]["C_im3"]
    p1, p2 = ctx["pawl_cheek"]["C"], ctx["pawl_cheek"]["C_im3"]
    a(f"| rack SF (5328 N) | {t1['rack_worst']['rack_sf']:.2f} ({t1['rack_worst']['set']}) | "
      f"{t2['rack_worst']['rack_sf']:.2f} ({t2['rack_worst']['set']}) |")
    a(f"| factored pawl force y / z, N | {t1['pawl_cheek_force']['factored_yz'][1]:.0f} / "
      f"{t1['pawl_cheek_force']['factored_yz'][2]:.0f} | {t2['pawl_cheek_force']['factored_yz'][1]:.0f} / "
      f"{t2['pawl_cheek_force']['factored_yz'][2]:.0f} |")
    a(f"| pawl cheek (304 bushing) 1 / FI99 | {p1['sf_fi']:.2f} | {p2['sf_fi']:.2f} |")
    a(f"| static-carry crown axial, N (1 g) | {t1['static_carry_crown_n']:.0f} | {t2['static_carry_crown_n']:.0f} |")
    a(f"| tail pull to shorten while worn, N | {t1['pulley_static']['tail_hoist_n']:.0f} | "
      f"{t2['pulley_static']['tail_hoist_n']:.0f} |")
    a(f"| cam hold SF walking / hipbelt off | {t1['cam_hold_sf_walk']:.0f} / {t1['cam_hold_sf_hipbelt_off']:.1f} | "
      f"{t2['cam_hold_sf_walk']:.0f} / {t2['cam_hold_sf_hipbelt_off']:.1f} |")
    a(f"| tail pull to hoist, hipbelt off, N | {t1['pulley_hipbelt_off']['tail_hoist_n']:.0f} | "
      f"{t2['pulley_hipbelt_off']['tail_hoist_n']:.0f} |")
    a("")
    a("The hipbelt-off hoist pull stays above the ASSUMPTION 200 N one-hand limit: keep the instruction not to adjust "
      "the torso with the hipbelt off.")
    at = ctx.get("attachments")
    if at:
        a("")
        a("## 4. Attachments")
        a("")
        a("Governing factored force per fairlead (both couple variants; `@IM3` = the IM3 couple variant), against the "
          "rev B record (`bag_attachment_results.json`):")
        a("")
        a("| fairlead | rev B N (case) | rev C N (case) |")
        a("|---|---:|---:|")
        for k in ("hinge", "im1", "im2", "im3"):
            gb, gc = at["gov_b"][k], at["gov_c"][k]
            a(f"| {k} | {gb['n']:.0f} ({gb['case']}) | {gc['n']:.0f} ({gc['case']}) |")
        a("")
        a("| part | load N | SF | rule |")
        a("|---|---:|---:|---|")
        for k in ("hinge", "im3"):
            f = at["fairlead_fea"][k]
            a(f"| fairlead {k}, printed cheek (1 mm voxels) | {f['force_n']:.0f} | {f['sf']:.2f} (fatigue "
              f"{f['sf_fatigue']:.2f}, creep {f['sf_creep']:.2f}) | 1 / FI99 ≥ 1 |")
        a(f"| hinge pin 5 mm 7075, double shear | {at['gov_c']['hinge']['n']:.0f} | {at['pin']['sf_yield']:.1f} | yield |")
        a(f"| hinge UHMWPE sleeve bearing | {at['gov_c']['hinge']['n']:.0f} | {at['pin']['sleeve_sf']:.2f} | yield |")
        a(f"| bag hooks, rated 2200 N ({at['bag_hook']['case']}, {at['bag_hook']['node']}) | {at['bag_hook']['n']:.0f} | "
          f"{at['bag_hook']['sf']:.2f} | rated ≥ factored |")
        a(f"| meat-strap hooks 1500 N ({at['meat_hook']['case']}, {at['meat_hook']['node']}) | {at['meat_hook']['n']:.0f} | "
          f"{at['meat_hook']['sf']:.2f} | rated ≥ factored |")
        a(f"| hinge-eye bartack 2700 N | {at['bartack']['n']:.0f} | {at['bartack']['sf']:.2f} | |")
        hq = at["bar_hood_line"]
        a(f"| crown bar wall under the hood lip ({hq['F_n']:.0f} N over {hq['F_n'] / hq['q_n_mm']:.0f} mm, "
          f"{hq['q_n_mm']:.2f} N/mm) | {hq['F_n']:.0f} | {hq['sf']:.2f} | ring FPF |")
        a(f"| crown bar wall under a guy through the hood ear (30 mm) | {at['bar_guy_30mm']['F_n']:.0f} | "
          f"{at['bar_guy_30mm']['sf']:.2f} | ring FPF |")
        for w, v in at["tie_210n"].items():
            a(f"| generic tie 210 N on {w} mm webbing | 210 | {v['sf']:.2f} | {'allowed' if v['allowed'] else '**not allowed** (< 25 mm)'} |")
        a(f"| lifters: webbing / ladder lock / ladder hipbelt-off | | {at['lifter']['webbing_sf']:.1f} / "
          f"{at['lifter']['ladder_sf']:.1f} / {at['lifter']['ladder_sf_abuse']:.1f} | |")
        a("")
        a("- The bag hooks are checked on the bag cases (C1–C3, C8) at the IM2 / IM3 eyes, including the IM3 couple "
          "variant; the meat-strap hooks on the meat and tall cases. The cloth-sim hood-off hook load (T0 472 N × 3.0 "
          "= 1415 N, bag_attachment.md §3) does not depend on the standard and stays SF 1.55.")
        a("- ASSUMPTION: the fairlead loads come from the beam model's default frame (`bag_attach._frame_model`), the "
          "same basis as the rev B attachment record.")
    if sp:
        c, c6 = sp["chosen"], sp["c6"]
        f = ctx.get("spreader_files", {})
        a("")
        a("## 5. Spreader, Sandwich v2 with the 7 mm core (BP-06 rev C)")
        a("")
        a(f"Meat CG {sp['meat_cg_mm']:g} mm (`spreader.MEAT_CG_MM`, from the load standard). Release procedure: 4 mm "
          "grid with a 24 mm bone grid, then 2 mm at the named positions; the worse governs.")
        a("")
        a("| check | 7 mm core (production) | 6 mm core at rev C (2 mm, named) | rule |")
        a("|---|---:|---:|---|")
        a(f"| first-ply SF | {c['sf_fpf']:.2f} ({c['fpf_where']}) | {c6['sf_fpf']:.2f} | ≥ 1.0 factored |")
        a(f"| fatigue SF | {c['sf_fatigue']:.2f} | {c6['sf_fatigue']:.2f} | FI ≤ 0.5 at 1.6 g |")
        a(f"| sandwich local SF | {c['sandwich_sf_min']:.2f} | {_f(c6.get('sandwich_sf_min'))} | ≥ 1.0 |")
        a(f"| air walking / factored, mm | {c['clear_walk_min']:.1f} / {c['clear_fact_min']:.1f} | "
          f"{c6['clear_walk_min']:.1f} / {c6['clear_fact_min']:.1f} | ≥ 3 / ≥ 0 |")
        a(f"| info: factored lean-torso air, gutter-bulge skin model, mm | {c['clear_fact_lean_min']:.1f} | "
          f"{c6['clear_fact_lean_min']:.1f} | sensitivity |")
        ln = sp.get("lean_recheck")
        if ln:
            a(f"| factored lean-torso air with the lumbar-pan skin reference, mm | **{ln['clear_fact_lean_min']:.1f}** | "
              "– | ≥ 0 (spreader_layout.md re-check method) |")
        a(f"| skin pressure, kPa (comfort, not HA-LS-1; released 120 mm rails) | {c['skin_peak_kpa']:.2f} | "
          f"{c6['skin_peak_kpa']:.2f} | ≤ 14 |")
        a(f"| mass installed, g | {c['mass_g']:.1f} | {c6['mass_g']:.1f} | |")
        a("")
        if f:
            a(f"Sheet {f['t_mm']:.2f} mm (7 mm core + 2 × 0.22 mm skins). Clip slot depth +{f['t_mm'] - 6.44:.1f} mm "
              f"(`spreader_v2_clip.dxf`, regenerated for the 7.44 mm sheet), clip SF {f['clip']['sf']:.1f}. Files: "
              f"`{f['dxf']}`, `{f['clip_dxf']}`, `{f['pdf']}`. Cost about ${f['cost_usd']:.0f}.")
        a("")
        a("`spreader._SKIN_CACHE` bug fixed: the key now includes the meat force, so a changed meat load is never served "
          "a stale skin pressure (regression test `test_spreader_skin_cache_keys_on_meat_load`).")
    m = ctx["mass"]
    a("")
    a("## 6. Masses of the load-path members")
    a("")
    a("| member | g | basis |")
    a("|---|---:|---|")
    a(f"| printed branch body (2 mm raster, socket-free) | {m['printed_body_g']:.0f} | `solid_mass_g` here |")
    for k, v in m["crown_beam_model"].items():
        a(f"| {k.replace('tubes: ', 'crown ')} | {v['rev_b']:.1f} → **{v['rev_c']:.1f}** | beam model hardware mass, frame.yaml |")
    fx = m["crown_fix_g"]
    a(f"| crown fix, booked | **+{fx['total']:.1f}** | spine {fx['spine']:.1f} + legs {fx['legs']:.1f} + bar "
      f"{fx['top_bar']:.1f} + bondline {fx.get('corner_bondline', 0):.1f} (`frame_cg_recheck.fix_mass_total`) |")
    if sp:
        a(f"| Sandwich v2 spreader, installed, 7 mm core | {sp['chosen']['mass_g']:.1f} | {sp['c6']['mass_g']:.1f} with the 6 mm core |")
    a("")
    a("- No mass cut is recommended now. The governing margins are the body under the IM3 couple (fatigue) and the "
      "spreader's notch-root FPF; thinning either loses the pass.")
    a("- Possible later cut: if test T9 measures a bag CG ≤ 190 mm, re-run this check at the measured CG before "
      "dropping one leg ply (about −7 g).")
    a("")
    a("## 7. Assumptions")
    a("")
    for s in ("ASSUMPTION: the beam model supplies the load path into the printed body and the crown forces, as in every "
              "production check (frame_cg_recheck.md §8).",
              "ASSUMPTION: the IM3 couple variant puts the whole bag couple top on the IM3 anchors; reality lies between "
              "the two variants, and rev C takes the worse.",
              "ASSUMPTION: hood and guy loads are added on top of the full meat load in the beam model (conservative "
              "for the crown, slightly favourable for the stays: the aft pull offsets the meat push).",
              "ASSUMPTION: guy aft run 305 mm at every torso (314 mm free length at 19 in), as in frame_cg_recheck.md §5.1.",
              "ASSUMPTION: the hood lip is centred on the bar (x ±66); it floats ±9 mm between the legs, which moves a "
              "symmetric line load by less than a node spacing.",
              "ASSUMPTION: the beam model's crown top bar carries the +1 ply; the printed mid bar line is unchanged "
              "(frame.yaml `top_bar_section`). The 0.8 mm bondline applies to the two crown corners only "
              "(`crown_joint`). The fix study of 2026-11-05 applied both to the mid bar / every joint as well.",
              "ASSUMPTION: corner-bond fatigue uses the hot/wet lap shear (× 0.8) as the static reference.",
              "ASSUMPTION: the spreader face load is linear in the meat CG (frame_smooth.meat_normal_n); bone 20 % of "
              "68 kg, part of the meat."):
        a(f"- {s}")
    a("")
    a("## Screenshots")
    a("")
    for s in screens:
        a(f"- `{s}`")
    DOC.write_text("\n".join(L) + "\n")
    return rel(DOC)


def refresh_spreader(log=print) -> dict:
    """Re-run only the spreader part (e.g. after a back-rail change) and rewrite the record, chart and doc. The
    frame, crown, torso-adjust and attachment results do not depend on the rail and are kept."""
    ctx = json.loads(RESULTS.read_text())
    sp = spreader_check(log=log)
    ctx["spreader"] = {"key": sp["opt"].key, "meat_cg_mm": sp["meat_cg_mm"], "mesh_check": sp["mesh_check"],
                       "rail": getattr(sp["rail"], "key", str(sp["rail"])),
                       "chosen": {k: v for k, v in sp["chosen"].items() if not k.startswith("_") and k != "rows"},
                       "c6": {k: v for k, v in sp["c6"].items() if k != "rows"}, "lean_recheck": sp["lean"]}
    ctx["spreader_files"] = write_spreader_files(sp, log=log)
    ctx["summary"] = summary_rows(ctx)
    ctx["screens"] = [plot_summary(ctx), ctx["spreader_files"]["png"]]
    save(ctx)
    write_doc(ctx, ctx["screens"])
    return ctx


def refresh_attachments(log=print) -> dict:
    """BL-045: re-run only the attachment part (fairlead cheeks on the as-printed geometry, pin, hooks, bartack, bar
    wall) and rewrite the record, chart and doc. The body, crown, torso-adjust and spreader results do not depend on
    the fairlead geometry (the fairlead cheek / pin checks mesh fairlead_local on a stay stub) and are kept."""
    ctx = json.loads(RESULTS.read_text())
    old = ctx["attachments"].get("bl045_previous_sf") or \
        {k: ctx["attachments"]["fairlead_fea"][k]["sf"] for k in ("hinge", "im3")}     # keep the pre-BL-045 values
    ctx["attachments"] = attachments(log=log)
    ctx["attachments"]["bl045_previous_sf"] = old
    ctx["summary"] = summary_rows(ctx)
    ctx["screens"] = [plot_summary(ctx)] + [s for s in ctx.get("screens", [])[1:]]
    save(ctx)
    write_doc(ctx, ctx["screens"])
    return ctx


def main(log=print):
    ctx = run(log=log)
    ctx["frame_mass"] = write_frame_mass(ctx["body_g"])
    screens = [plot_summary(ctx)]
    if ctx.get("spreader_files"):
        screens.append(ctx["spreader_files"]["png"])
    ctx["screens"] = screens
    save(ctx)
    doc = write_doc(ctx, screens)
    log(f"wrote {doc}")
    return ctx


if __name__ == "__main__":
    main()
