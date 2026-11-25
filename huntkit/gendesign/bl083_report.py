"""BL-083 driver: concept D (D83 and D83-L) with real joints, the hip-offset sweep, the B81 lever row (B81-L), the
ranking against H1c, and the record ``designs/pack_5200/iter2/frame_d/bl083.{json,md}`` with STL / DXF / screens.

Run: ``python -m huntkit.gendesign.bl083_report run`` (about 30 min on 4 cores cold: every stage in its own process,
then ``assemble``; ``stage <D83|D83-L|sweep|B81-L|B81-Lb>`` runs one, cached in outputs/bl083/stage_*.json).
``... md`` re-writes the Markdown and the screens from the stored JSON.
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl081_report as BR
from huntkit.gendesign import bl083_concept_d as D
from huntkit.gendesign import bl083_parts as DP

ITEMS = {**BR.ITEMS, "1": "Global model with real joints (members, buckling, crush sleeves)",
         "P": "Hip pan (tray + spine + strut): plate, holes, bolts, Ti mount, lumbar push",
         "4": "Spreader on the D supports (stays + mid bar; no rungs)"}
VARIANTS = {
    "D83": {"pan_t": ".100"},
    "D83-L": {"pan_t": ".100", "tees": "bands"},
}
DOUBLED = "t1000_d049"


def _global_rows(g) -> list[dict]:
    rows = []
    for k, v in g["strength"].items():
        rows.append({"item": "1", "row": f"{k}: member strength (beam, all cases)", "kind": "strength", "value": v["sf"],
                     "allow": v["required"], "margin": v["margin"], "basis": f"{v['member']} {v['case']}"})
    rows.append({"item": "1", "row": "frame buckling eigenvalue / (1.5 x case factor)", "kind": "strength",
                 "value": g["buckling"]["eigen"], "allow": None, "margin": g["buckling"]["margin"],
                 "basis": g["buckling"]["case"]})
    return rows


def check_d(name: str, cfg: dict, log=print, spreader=True) -> dict:
    t0 = time.time()
    cfg = D.cfg_d(**cfg)
    log(f"[{name}] global model, 3 torsos")
    g = D.evaluate_global(cfg, log=log)
    log(f"[{name}] pan forces")
    pf = D.evaluate_pan_forces(cfg)
    rows = _global_rows(g)
    rows = [r for r in rows if not r["row"].startswith("pan ")]      # pan strips are reported in item P with Kt
    with D._as_b81():
        rows += BL.hole_rows(g, cfg) + BL.foot_rows(g, cfg) + BL.bushing_rows(g, cfg) + D.clamp_rows(g, cfg) + \
            BL.fairlead_rows(g, cfg)
        tors = {"Nm_deg": BQ.torsion_stiffness(cfg), **BQ.torsion_reference()}
    rows += D.lumbar_crush_rows(g, cfg) + D.pan_rows(g, pf, cfg)
    tors["vs_h1"] = tors["Nm_deg"] / tors["h1_Nm_deg"]
    sp = None
    if spreader:
        log(f"[{name}] spreader on the D supports")
        try:
            sp = BL.spreader_b({**cfg, "rung_z": (-100.0, -100.0), "gusset_t": -50.0}, h=4.0)
            rows += [{**r, "basis": r["basis"].replace("B81 supports", "D supports (stays + mid bar)")}
                     for r in BL.spreader_rows(sp)]
        except Exception as e:   # pragma: no cover
            sp = {"error": repr(e)}
    strong = [r for r in rows if r.get("margin") is not None and r["kind"] != "info"]
    gov = min(strong, key=lambda r: r["margin"])
    return {"name": name, "cfg": cfg, "rows": rows, "min_margin": round(float(gov["margin"]), 3), "governing": gov["row"],
            "strong_pass": bool(gov["margin"] >= 1.0),
            "fatigue_min": round(min(r["margin"] for r in strong if r["kind"] == "fatigue"), 3),
            "margins_table": margins_table(rows),
            "global": {"strength": g["strength"], "buckling": g["buckling"], "deflection_t1": g["deflection"],
                       "links_factored": {k: v for k, v in g["links"].items() if k.startswith(("pb_", "tee_", "pawl"))}},
            "torsion": tors, "spreader": sp, "seconds": round(time.time() - t0, 1),
            "_g": g}


def margins_table(rows):
    tab = []
    for it in ITEMS:
        rs = [r for r in rows if r["item"] == it and r.get("margin") is not None]
        for kind in ("strength", "fatigue", "joint"):
            ks = [r for r in rs if r["kind"] == kind]
            if ks:
                w = min(ks, key=lambda r: r["margin"])
                tab.append({"item": it, "kind": kind, "margin": round(float(w["margin"]), 3), "row": w["row"]})
    return tab


# ----------------------------------------------------------------------------- B81 lever row
def _b81l_stations(cfg):
    out = []
    for s in D._B81_STATIONS(cfg):
        if s["group"] == "stay" and "gusset bolt" in s["name"]:
            s = {**s, "tube": DOUBLED, "name": s["name"] + " (doubled wall)"}
        out.append(s)
    return out


def check_b81l(log=print, stay="t1000_049", name="B81-L") -> dict:
    """B81 with hose-band tees, 1 x .049 stays and a bonded 7/8 x .049 internal doubler at z 90-160 (the gusset-bolt
    holes; ASSUMPTION DOUBLER-EQ: the doubled wall as one 2.49 mm wall in the solid unit cases), all other rows on the
    BL-081 basis. Comparison row only."""
    t0 = time.time()
    if DOUBLED not in BQ.STOCK:
        BQ.STOCK[DOUBLED] = {"desc": '1" x .049" + 7/8" x .049" bonded internal doubler (equivalent 1 x .098 wall)',
                             "od": BQ.IN, "t": 2 * 0.049 * BQ.IN, "usd": 0.0, "len_in": 12, "src": DP.DOUBLER["src"]}
    cfg = {**BQ.CFG0, "stay": stay, "tees": "bands", "band_n": 2, "band_T_upper": D.CFG_D["band_T_upper"]}
    log(f"[{name}] global model")
    with D._as_b81(builder=D._B81_BUILD, stations_fn=_b81l_stations, role=D._B81_ROLE):
        g = BQ.evaluate_global(cfg, log=log)
        rows = _global_rows(g)
        for f in (BL.hole_rows, BL.gusset_rows, BL.bolt_rows, BL.crush_rows, BL.hip_rows, BL.foot_rows, BL.bushing_rows,
                  D.clamp_rows, BL.fairlead_rows):
            rows += f(g, cfg)
    strong = [r for r in rows if r.get("margin") is not None and r["kind"] != "info"]
    gov = min(strong, key=lambda r: r["margin"])
    rec = json.loads(BQ.REC_JSON.read_text())
    bill = DP.b81_lever_bill(cfg, rec["mass"], rec["cost"], thin_stays=(stay == "t1000_049"))
    return {"name": name, "cfg": {k: v for k, v in cfg.items()}, "rows": rows, "min_margin": round(float(gov["margin"]), 3),
            "governing": gov["row"], "strong_pass": bool(gov["margin"] >= 1.0),
            "fatigue_min": round(min(r["margin"] for r in strong if r["kind"] == "fatigue"), 3),
            "margins_table": margins_table(rows), "bill": bill, "seconds": round(time.time() - t0, 1),
            "global": {"strength": g["strength"], "buckling": g["buckling"]}}


# ----------------------------------------------------------------------------- hip offset sweep
def offset_sweep(base: dict, d_list=(0.0, 15.0, 30.0), log=print) -> list[dict]:
    """Pin (and mount seat, pad seat) moved aft by d: pan walls shorter, hip torque V x (67 - d); the belt pad stack
    must grow by d (EVA 45C, 150 x 150, record density 110 kg/m3) or the frame moves d toward the back. Global margins
    (pan roles, buckling) on torsos 15 / 23 in, the pan tray mass from the flat pattern."""
    from huntkit.materials import load
    rho_eva = float(load("eva_foam_45c").require("density_kg_m3")) * 1e-6     # g/mm3
    out = []
    for d in d_list:
        cfg = D.cfg_d(**{**base, "pin_aft": d})
        g = D.evaluate_global(cfg, torsos=(15.0, 23.0), log=lambda *a: None)
        pf = D.evaluate_pan_forces(cfg, torsos=(15.0, 23.0))
        pan = {k: min(r["sf"] / r["req"] for r in pf[k]) for k in ("wall", "face", "spine")}
        ft = DP.flat_tray(cfg)
        tray_g = ft["area_mm2"] * ft["dims"]["t"] * D.AL5052["rho"]
        bolt = max(v["F"] for k, v in g["links"].items() if k.startswith("pb_") and "|" not in k)
        out.append({"pin_aft_mm": d, "offset_to_stay_mm": round(D.geom(cfg)["yline"](120.0) - D.geom(cfg)["pin_y"], 1),
                    "pan_wall_margin": round(pan["wall"], 3), "pan_face_margin": round(pan["face"], 3),
                    "stays_margin": round(g["strength"]["stays"]["margin"], 3),
                    "buckling_margin": round(g["buckling"]["margin"], 3), "pan_bolt_F_n": round(bolt, 0),
                    "tray_g": round(tray_g, 1), "eva_pad_g": round(150 * 150 * d * rho_eva, 1),
                    "net_g": round(tray_g + 150 * 150 * d * rho_eva, 1)})
        log(f"  offset d {d:g}: {out[-1]}")
    return out


# ----------------------------------------------------------------------------- coupons
def coupons(v: dict) -> list[dict]:
    g = v["_g"]
    pb = max(v2["F"] for k, v2 in g["links"].items() if k.startswith("pb_") and "|" not in k)
    hp = g["hip_pin"]
    Vf = max(abs(r["F"][2]) for r in hp)
    Vw = max(abs(r["walk"][2]) for r in hp if r["walk"] is not None)
    from huntkit.gendesign import hipbelt_structure as HS
    H = HS.load_sets()["C2"].H
    tee = max(abs(np.asarray(g["links"][k]["vec"])[2]) for k in g["links"] if k.startswith("tee_"))
    bands = v["cfg"].get("tees") == "bands"
    return [
        {"id": "FB-1", "what": f"bend coupon: 5052-H32 {v['cfg']['pan_t']} strip 25 x 120 with one SendCutSend 90 deg bend (same "
         "order as the pan), dye check the outside of the bend", "pass": "no crack or orange peel deeper than 0.05 mm at 10x; bend angle 90 +/- 1 deg",
         "settles": "ASSUMPTION SCS-RADIUS (r = t), AL5052-MIN (mill cert)", "usd": 0.0},
        {"id": "BB-D", "what": f"pan bolt bearing: 5052 {v['cfg']['pan_t']} strip (12 mm edge) + M5 + crush sleeve through a 1 in stay "
         "offcut, pulled fore-aft on the rig (come-along + crane scale), n 3",
         "pass": f"hole elongation <= 0.2 mm at {pb:.0f} N (largest factored pan-bolt force) and ultimate >= {1.5 * pb:.0f} N",
         "settles": "ASSUMPTIONS BRG-5052, KT-PIN, GAP-K", "usd": 2.0},
        {"id": "HP-D", "what": "hip pan proof: the formed tray + spine + strut on two stay offcuts (pan bolts and rod torqued), "
         f"Ti mount fitted; load the pin with V {Vf:.0f} N + H {H:.0f} N through a lever, hold 2 min",
         "pass": f"no permanent set > 0.2 mm at the pin, no hole elongation, no bend cracking; then 1e4 cycles 0 -> {Vw:.0f} N "
                 "(walk V) with no crack (dye check)", "settles": "MOUNT-SPIDER, grillage plate model, pan rows", "usd": 0.0},
        {"id": "KF-D", "what": "lateral-hole stay fatigue: 1 in stay offcut with an M5 crush-sleeved hole ALONG x (neutral axis of "
         "fore-aft bending), 4-point bending fore-aft on the T5 crank rig, R 0.1, n 3",
         "pass": "no crack (dye check) after 1e5 cycles at 1.2 x the walk bore stress of the worst pan-bolt station",
         "settles": "Yahr mean curve, Kf = Kt (lateral hole), BJ-NOCREDIT", "usd": 1.0},
        {"id": "CL-1" if not bands else "CL-B", "what": "clamp slip on a stay offcut, wet: " + (
            "6061 half-shells + 2 x 9 mm W4 hose bands at 4.0 N m" if bands else "half-shells + 1 x 1/4 backers + 2 x M5 A2"),
         "pass": f"minimum wet slip load >= {max(1000.5, tee) * 1.2:.0f} N; " + (
             "band tension by strain (or 24 h torque-loss) >= 0.8 x 1212 N" if bands else "no tube dent > 0.1 mm"),
         "settles": "MU 0.15 wet, EMBED / BAND", "usd": 6.0},
        {"id": "CF-1", "what": "foot cup crush (BL-081, unchanged)", "pass": "no crack at 4.0 kN", "settles": "COMP-Z, PAD",
         "usd": 1.5},
        {"id": "T1-D", "what": "frame T1 / torsion check on the built frame (load_standard 5.2)",
         "pass": f"crown elastic deflection at 150 lb, 19 in within +/-30 % of {g['deflection']['19']['crown_elastic_mm']:.1f} mm",
         "settles": "GAP-K, grillage stiffness, strut", "usd": 0.0},
    ]


# ----------------------------------------------------------------------------- run
STAGES = ("D83", "D83-L", "sweep", "B81-L", "B81-Lb")


def _stage_path(name):
    return D.CACHE / f"stage_{name}.json"


def stage(name: str, log=print) -> dict:
    """One stage of the record in its own process (the solid-FE caches of BL-081 grow to ~14 GB if every stage runs in
    one process); the result is stored in outputs/bl083/stage_<name>.json and picked up by ``assemble``."""
    D.CACHE.mkdir(parents=True, exist_ok=True)
    if name in VARIANTS:
        v = check_d(name, VARIANTS[name], log=log, spreader=(name == "D83"))
        cfg = v["cfg"]
        log(f"[{name}] parts, STL, DXF")
        v["parts"] = DP.export(cfg, log=log)
        v["mass"] = DP.mass_table(cfg, v["parts"]["printed"])
        v["cost"] = DP.cost_table(cfg, v["mass"], local_metal=(name != "D83"))
        v["cut_list"] = DP.cut_list(cfg)
        v["flat"] = {"tray": {k: DP.flat_tray(cfg)[k] for k in ("bbox", "area_mm2", "hole_to_bend_min_mm", "n_bends")},
                     "spine": {k: DP.flat_spine(cfg)[k] for k in ("bbox", "area_mm2", "hole_to_bend_min_mm", "n_bends")},
                     "bend": DP.bend(D.geom(cfg)["t"])}
        v["coupons"] = coupons(v)
        v["proving"] = DP.proving(cfg)
        (D.CACHE / f"global_plot_{name}.json").write_text(json.dumps(BR._js({"util": v["_g"]["members_util"]})))
        v.pop("_g")
        out = v
    elif name == "sweep":
        out = {"rows": offset_sweep(VARIANTS["D83"], log=log)}
    elif name == "B81-L":
        out = check_b81l(log=log)
    elif name == "B81-Lb":
        out = check_b81l(log=log, stay="t1000_065", name="B81-Lb")
    else:
        raise KeyError(name)
    _stage_path(name).write_text(json.dumps(BR._js(out)))
    return out


def assemble(log=print) -> dict:
    rec = {"ticket": "BL-083", "date": D.DATE, "variants": {}, "scs": D.SCS, "al5052": D.AL5052,
           "sn_5052_smax_r0_1e5": round(D.sn_5052_smax_r0(), 1), "band": D.BAND}
    st = {}
    for n in STAGES:
        p = _stage_path(n)
        if not p.exists():
            raise FileNotFoundError(f"run python -m huntkit.gendesign.bl083_report stage {n} first")
        st[n] = json.loads(p.read_text())
    rec["variants"] = {n: st[n] for n in VARIANTS}
    rec["offset_sweep"] = st["sweep"]["rows"]
    rec["b81_levers"] = st["B81-L"]
    rec["b81_levers_065"] = st["B81-Lb"]
    b81 = json.loads(BQ.REC_JSON.read_text())
    rec["baselines"] = baselines(b81)
    rec["ranking"] = rank(rec)
    rec["seconds_by_stage"] = {n: st[n].get("seconds") for n in STAGES}
    D.OUTDIR.mkdir(parents=True, exist_ok=True)
    write_md(rec)
    rec["screens"] = screens(rec)
    D.REC_JSON.write_text(json.dumps(BR._js(rec), indent=1))
    return rec


def run(log=print) -> dict:
    """Every stage in a fresh subprocess, then assemble."""
    import subprocess
    for n in STAGES:
        subprocess.run([sys.executable, "-m", "huntkit.gendesign.bl083_report", "stage", n], check=True)
    return assemble(log=log)


def baselines(b81) -> dict:
    from huntkit.gendesign.bl080_metal_frame import H1, H1C
    return {"H1": {"body_g": H1["body_g"], "usd": H1["usd"], "strong": "retired (PAHT lug rows open, BL-077)"},
            "H1c": {"body_g": H1C["body_g"], "usd": H1C["usd"],
                    "strong": "FAIL: two joints below goal (BL-077 / orchestrator brief)"},
            "B81": {"body_g": b81["mass"]["body_g"], "usd": b81["cost"]["per_frame_usd"], "min_margin": b81["min_margin"],
                    "strong": f"PASS {b81['min_margin']:.2f}"}}


def rank(rec) -> list[dict]:
    """Rubric order: Strong gate, then the USD 150 cap, then body mass. Candidates: H1c, B81-L, D83, D83-L (B81 as
    reference)."""
    cands = []
    b = rec["baselines"]
    cands.append({"option": "H1c", "strong_pass": False, "min_margin": None, "usd": b["H1c"]["usd"], "body_g": b["H1c"]["body_g"],
                  "note": b["H1c"]["strong"]})
    for key in ("b81_levers", "b81_levers_065"):
        L = rec[key]
        cands.append({"option": L["name"], "strong_pass": L["strong_pass"], "min_margin": L["min_margin"],
                      "usd": L["bill"]["per_frame_usd"], "body_g": L["bill"]["body_g"], "note": L["governing"]})
    for n, v in rec["variants"].items():
        cands.append({"option": n, "strong_pass": v["strong_pass"], "min_margin": v["min_margin"],
                      "usd": v["cost"]["per_frame_usd"], "body_g": v["mass"]["body_g"], "note": v["governing"]})
    cands.append({"option": "B81 (reference)", "strong_pass": True, "min_margin": b["B81"]["min_margin"],
                  "usd": b["B81"]["usd"], "body_g": b["B81"]["body_g"], "note": "BL-081"})
    key = lambda c: (not c["strong_pass"], c["usd"] > 150.0, c["body_g"])   # noqa: E731
    out = sorted(cands, key=key)
    for i, c in enumerate(out):
        c["rank"] = i + 1
        c["in_cap"] = c["usd"] <= 150.0
    return out


# ----------------------------------------------------------------------------- markdown
def _f(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}"


def write_md(rec: dict) -> None:
    v0, v1, L = rec["variants"]["D83"], rec["variants"]["D83-L"], rec["b81_levers"]
    b = rec["baselines"]
    w = []
    a = w.append
    a("# BL-083: concept D with real joints (D83), hip-offset study, B81 lever row\n")
    a("Owner: structural-fea-engineer, 2026-11-25. Code: `huntkit/gendesign/bl083_concept_d.py` (model, pan rows), "
      "`bl083_parts.py` (flat patterns, DXF, STL, bill), `bl083_report.py` (this record). The BL-081 global and local "
      "checks (`bl081_concept_b`, `bl081_local`, `huntkit/fea/tube_solid.py`) run unchanged on D by swapping the builder "
      "and station list in for the call. Numbers: [bl083.json](bl083.json). Tests: `tests/test_bl083_concept_d.py`. "
      "Units mm, N, MPa, g, USD (imperial in brackets).\n")
    a("## 0. Answer\n")
    a(f"- **D83 is strong: min margin {v0['min_margin']:.2f}** ({v0['governing']}); fatigue minimum {v0['fatigue_min']:.2f}. "
      f"Same basis as BL-081 (Yahr / Goodman, Kf = Kt from tube_solid, no preload credit, wet mu 0.15, crush sleeves, "
      f"PAHT in bearing / compression only).")
    a(f"- **But D does not beat H1c on mass, and no D variant meets the USD 150 cap.** D83 body "
      f"**{v0['mass']['body_g']:.0f} g ({v0['mass']['body_g'] / 453.6:.2f} lb)**, USD **{v0['cost']['per_frame_usd']:.2f}**; "
      f"D83-L (hose-band tees, local metal; .049 stays were tried and fail the upper tee at 0.67) {v1['mass']['body_g']:.0f} g, USD {v1['cost']['per_frame_usd']:.2f}, "
      f"strong {'PASS' if v1['strong_pass'] else 'FAIL'} {v1['min_margin']:.2f}. H1c is {b['H1c']['body_g']:.1f} g / USD {b['H1c']['usd']:.2f}; "
      f"the 1300 g stretch goal is out of reach for any metal-stay variant checked here.")
    a(f"- **Why D is heavy and dear:** SendCutSend does not bend 6061-T6 (their page), so the formed pan is 5052-H32, "
      f"whose minimum yield (159 MPa) is 0.66 x 6061's. On real joints a 2 mm pan was not enough: the Ti mount couple "
      f"needs a formed spine channel, the face needs .100 in for the lumbar push, and the open tray let the frame sway "
      f"(global buckling 0.99) until a strut on an M5 rod tied the walls at z 155. The pan set is "
      f"{v0['mass']['lumbar_g']:.0f} g and USD {v0['cost']['pan_usd']:.0f} at qty 1 (SCS price ASSUMPTION; band "
      f"USD {v0['cost']['pan_band_usd'][0]:.0f}-{v0['cost']['pan_band_usd'][1]:.0f}); the rest of the frame (stays, tees, "
      f"bars, foot, printed parts) is B81's and already costs about USD 136.")
    a(f"- **Hip pivot offset:** the belt sets it (pin through belt B's centre plate, pad seated on the pan face). D keeps the "
      f"BL-055 / 056 Ti mount and its 21 mm stand-off on a pan face at y -48.55, so the hipbelt interface is unchanged; the "
      f"67 mm to the stay line is carried as in-plane bending of the pan walls. Moving the pin aft (section 5) saves "
      f"little pan and costs belt pad EVA: the offset is not worth changing.")
    a(f"- **B81 levers as briefed** (B81-L, comparison row): {L['bill']['body_g']:.0f} g ({L['bill']['d_mass_g']:+.0f} g), USD "
      f"{L['bill']['per_frame_usd']:.2f} ({L['bill']['d_cost_usd']:+.2f}), strong {'PASS' if L['strong_pass'] else 'FAIL'} "
      f"{L['min_margin']:.2f} ({L['governing']}).\n")
    a("## 1. Ranking (rubric order: Strong gate, USD 150 cap, body mass)\n")
    a("| rank | option | Strong | min margin | USD / frame | in cap | body g (lb) | governing / note |")
    a("|---:|---|---|---:|---:|---|---:|---|")
    for c in rec["ranking"]:
        a(f"| {c['rank']} | {c['option']} | {'PASS' if c['strong_pass'] else 'FAIL'} | {_f(c['min_margin'])} | {c['usd']:.2f} | "
          f"{'yes' if c['in_cap'] else 'no'} | {c['body_g']:.0f} ({c['body_g'] / 453.6:.2f}) | {c['note'][:70]} |")
    over = {c["option"]: c["usd"] - 150.0 for c in rec["ranking"]}
    a(f"\nNo option passes both gates. Among the strong options (all over the cap) the rubric's next axis is mass, so "
      f"D83-L ranks first; on cost B81-Lb is USD {over['B81-Lb']:.2f} over the cap and D83-L USD {over['D83-L']:.2f} over. "
      f"The best three: section 9.\n")
    for name, v in (("D83", v0), ("D83-L", v1)):
        a(f"## 2{'a' if name == 'D83' else 'b'}. {name} margins (minimum per check item and kind)\n")
        a("| # | check | kind | margin | governing row |")
        a("|---|---|---|---:|---|")
        for t in v["margins_table"]:
            a(f"| {t['item']} | {ITEMS.get(t['item'], '')[:48]} | {t['kind']} | {t['margin']:.2f} | {t['row'][:90]} |")
        a("")
    a("Every row with its value, allowable and basis is in `bl083.json` `variants.<name>.rows`. Margin = allowable / "
      "value with the case factor in the forces (walk = static carry x 1.6 g, 1e5 cycles, R 0).\n")
    a("## 3. What D83 is\n")
    c = v0["cfg"]
    a(f"- **Stays, bars, tees, foot, crown bushings: B81** (1 x .065 stays, 1 x .065 upper bar, 3/4 x .035 mid bar, "
      f"6061 half-shell clamp tees, printed foot cups). Only the lumbar / hip node changes.")
    a(f"- **Hip pan tray:** 5052-H32 {c['pan_t']} in ({D.SHEET_T[c['pan_t']]:.2f} mm), SendCutSend laser-cut + 4 bends: face "
      f"x +/-102.3 (OML) z 50-190 with its body side at y -48.55 (the BL-055 boss face: Ti mount, pin stand-off 21 mm, belt "
      f"B pad seat 190 x 150 and the 25 mm top return for the Hypalon sleeve all unchanged), walls aft along the stays' "
      f"inboard faces (z 78-190, beside the stay z 78-170 so the IM1 loop wraps the stay above), return flanges top 25 / "
      f"bottom 20 mm. Flat {v0['flat']['tray']['bbox'][0]:.0f} x {v0['flat']['tray']['bbox'][1]:.0f} mm, hole-to-bend "
      f"{v0['flat']['tray']['hole_to_bend_min_mm']} mm (>= 6.0, half the 0.472 in die).")
    a(f"- **Mount spine:** 5052-H32 {c['spine_t']} channel, web {c['spine_w']:g} mm, legs {c['spine_leg']:g} mm aft, z 50.5-189.5 "
      f"behind the face, clamped by the 8 Ti-mount screws (all BL-055 positions now land) and 4 screws near the flanges. "
      f"It carries the mount couple (V x 21 mm + pad offset) as beam bending to the flanges.")
    a(f"- **Pan bolts:** per side M5 A2 at z 85 along x through wall + stay (crush sleeve); at z 155 an M5 A2 threaded rod "
      f"runs through both stays and a 3/4 x .035 spacer tube between the walls (the lumbar strut). The stay holes are "
      f"lateral, on the neutral axis of the stays' fore-aft bending (solid-FE Kt on the neutral axis 0.43 vs 3.12 on the "
      f"extreme fibre, BL-081).")
    a(f"- **Global stiffness:** torsion {v0['torsion']['Nm_deg']:.1f} N m/deg = {v0['torsion']['vs_h1']:.1f} x H1 (B81 19.9). "
      f"T1 crown elastic deflection at 150 lb: " + ", ".join(
          f"{k} in {v0['global']['deflection_t1'][k]['crown_elastic_mm']:.1f} mm" for k in ("15", "19", "23")) + " (band +/-30 %).\n")
    a("Design path (each step forced by a failing row on the BL-081 basis):\n")
    a("| step | change | row it fixed |")
    a("|---|---|---|")
    a("| 1 | 5052 .080 tray, Ti mount on the face only | face strip at the mount: SF 0.99 at 1 g (mount couple into a 2 mm plate) |")
    a("| 2 | + spine channel (web 64, legs 25) | face strips at the mount; spine margin > 3 |")
    a("| 3 | .080 -> .100 tray | face out of plane under the lumbar pad push 0.89 -> 1.31; wall at the z 155 bolt 0.95 -> 1.02 |")
    a("| 4 | + strut on an M5 rod at z 155 | global buckling 0.99 -> 1.51 (side-hill): the open tray let the stays yaw / sway "
      "against the pan through wall out-of-plane bending |")
    a("| 5 | spine 50 -> 64 mm, spine screws z 62 / 178 | SendCutSend hole-to-bend rule (>= 1/2 die width) |\n")
    a("## 4. Mass and cost (D83)\n")
    a("| item | g |")
    a("|---|---:|")
    for k, x in v0["mass"]["rows"].items():
        a(f"| {k} | {x:.1f} |")
    a(f"| **body** | **{v0['mass']['body_g']:.1f}** |")
    a(f"| Ti mount fixings (8 x M5 x 16 A2 + nuts) | {v0['mass']['hip_hw_g']:.1f} |\n")
    a("| line | USD | source |")
    a("|---|---:|---|")
    for l in v0["cost"]["lines"]:
        a(f"| {l['item']} | {l['usd']:.2f} | {l['source'][:160]} |")
    a(f"| **per frame** | **{v0['cost']['per_frame_usd']:.2f}** | cap 150 |\n")
    a(f"SendCutSend method (cited, price ASSUMPTION SCS-PRICE): {D.SCS['pricing']}. {D.SCS['bend_rules']}. "
      f"{D.SCS['no_6061_bend']}. Price rule in `bl083_concept_d.scs_price`: the cited qty-1 cut-only example scaled by "
      f"sqrt(area), USD 0.25 per pierce over 8, the cited bending premium (USD 17.98) for the first bend and half of it "
      f"for each further bend. Pan band USD {v0['cost']['pan_band_usd'][0]:.0f} (cut-only + USD 6 per bend) to "
      f"{v0['cost']['pan_band_usd'][1]:.0f}. Even at zero pan cost the frame is USD "
      f"{v0['cost']['per_frame_usd'] - v0['cost']['pan_usd']:.0f}: the cap is lost in the B81 hardware, not only in the pan.\n")
    a(f"D83-L: body {v1['mass']['body_g']:.1f} g, USD {v1['cost']['per_frame_usd']:.2f} (rows in the JSON).\n")
    a("## 5. Hip pivot offset (free variable)\n")
    a("What the belt needs (`hipbelt_fit.md` 4.1, `hipbelt_structural.md` 4, `concepts/corrie.py pad_seat`): the Ti pin at "
      "x 0, z 120 through belt B's centre plate (roll +/-8 deg), a D36 POM thrust face for the lumbar push, and a pan face "
      "z 50-190, >= 190 mm wide, for the pad seat (EVA rails either side of a 70 mm channel, HDPE backer, 25 mm top "
      "return). The pin's fore-aft position is fixed by the body, not the frame: moving it aft by d moves the pad seat aft "
      "by d, so the pad stack must grow by d (or the whole frame and bag move d toward the back, which the spreader / back-"
      "panel clearance would have to absorb). D83 keeps d = 0.\n")
    a("| pin aft d (mm) | pin to stay line (mm) | pan walls | pan face | stays | buckling | pan bolt F (N) | tray g | belt EVA + g | tray + EVA g |")
    a("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in rec["offset_sweep"]:
        a(f"| {s['pin_aft_mm']:g} | {s['offset_to_stay_mm']:.1f} | {s['pan_wall_margin']:.2f} | {s['pan_face_margin']:.2f} | "
          f"{s['stays_margin']:.2f} | {s['buckling_margin']:.2f} | {s['pan_bolt_F_n']:.0f} | {s['tray_g']:.0f} | "
          f"{s['eva_pad_g']:.0f} | {s['net_g']:.0f} |")
    a("\n(15 / 23 in torsos, global rows only.) Shortening the offset lowers the pan-bolt force and lifts the stays, but the "
      "shorter walls lose margin (the bolt couple then works on a squat wall whose aft strip at the z 155 bolt carries it in "
      "bending: 0.92 at d 15, 0.41 at d 30 in the grillage), the tray saves only 13 g per 15 mm while the belt pad gains "
      "37 g, and the belt's fit moves. With the pan the 67 mm offset is carried in the walls' own plane, so the BL-055 / 056 "
      "mount and its offset stay (d = 0).\n")
    a("## 6. B81 lever row (comparison only)\n")
    a(f"B81 + hose-band tees (2 x 9 mm W4 per tee, ASSUMPTION BAND) + 1 x .049 stays with a bonded 7/8 x .049 internal "
      f"doubler at z 90-160 (the gusset-bolt holes; solid-FE unit cases on the doubled wall, ASSUMPTION DOUBLER-EQ) + "
      f"metal bought locally. Strong {'PASS' if L['strong_pass'] else 'FAIL'}: min {L['min_margin']:.2f} ({L['governing']}), "
      f"fatigue min {L['fatigue_min']:.2f}.\n")
    a("| delta | g |")
    a("|---|---:|")
    for k, x in L["bill"]["mass_rows"].items():
        a(f"| {k} | {x:+.1f} |")
    a(f"| **B81-L body** | **{L['bill']['body_g']:.1f}** |\n")
    a("| delta | USD |")
    a("|---|---:|")
    for r in L["bill"]["cost_rows"]:
        a(f"| {r['item']} | {r['usd']:+.2f} |")
    a(f"| **B81-L per frame** | **{L['bill']['per_frame_usd']:.2f}** |\n")
    a("| # | kind | margin | governing row |")
    a("|---|---|---:|---|")
    for t in L["margins_table"]:
        a(f"| {t['item']} | {t['kind']} | {t['margin']:.2f} | {t['row'][:90]} |")
    a("")
    Lb = rec["b81_levers_065"]
    a(f"**B81-Lb** (the levers that survive: hose-band tees + local metal, 1 x .065 stays kept): body "
      f"{Lb['bill']['body_g']:.1f} g ({Lb['bill']['d_mass_g']:+.1f}), USD {Lb['bill']['per_frame_usd']:.2f} "
      f"({Lb['bill']['d_cost_usd']:+.2f}), strong {'PASS' if Lb['strong_pass'] else 'FAIL'} {Lb['min_margin']:.2f} "
      f"({Lb['governing']}).\n")
    a("| # | kind | margin | governing row |")
    a("|---|---|---:|---|")
    for t in Lb["margins_table"]:
        a(f"| {t['item']} | {t['kind']} | {t['margin']:.2f} | {t['row'][:90]} |")
    a("")
    a("## 7. Cut list (D83)\n")
    a("| part | stock | qty | length mm | holes | jig |")
    a("|---|---|---:|---:|---|---|")
    for r in v0["cut_list"]:
        a(f"| {r['part']} | {r['stock']} | {r['qty']} | {_f(r['length_mm'], 1)} | {r['holes']} | {r['jig']} |")
    a("\nFlat patterns: `designs/pack_5200/iter2/frame_d/cut/hip_pan_tray_5052_flat.dxf`, `hip_pan_spine_5052_flat.dxf` "
      "(layers CUT / BEND / NOTE; check r and K in the SendCutSend bending calculator before ordering). Solids: "
      "`cut/hip_pan_tray.stl`, `hip_pan_spine.stl`, `lumbar_strut.stl`. Printed (PAHT-CF, B81 parts minus the saddle plugs): "
      "`print/`. Jigs: `jigs/jig_stay_d83.stl` (z 60 / 85 / 155 lateral holes), `jig_upper_bar_half.stl`.\n")
    a("## 8. Coupons and proof tests (D83, pass lines)\n")
    a("| id | what | pass | settles | USD |")
    a("|---|---|---|---|---:|")
    for cp in v0["coupons"]:
        a(f"| {cp['id']} | {cp['what']} | {cp['pass']} | {cp['settles']} | {cp['usd']:.2f} |")
    a(f"\nProving total USD {v0['proving']['total_usd']:.2f} (cap 150).\n")
    a("## 9. Best three across H1c, B81-L and D\n")
    top = [c for c in rec["ranking"] if c["option"] != "B81 (reference)"][:3]
    for i, c in enumerate(top):
        a(f"{i + 1}. **{c['option']}**: Strong {'PASS' if c['strong_pass'] else 'FAIL'}"
          f"{' ' + _f(c['min_margin']) if c['min_margin'] else ''}, USD {c['usd']:.2f} ({'in' if c['in_cap'] else 'over'} cap), "
          f"{c['body_g']:.0f} g.")
    a("\nNone passes Strong and the cap together. The strong options are all over USD 150 and 200-450 g heavier than "
      "H1c; H1c is the lightest but fails two joint rows. B81-Lb is the cheapest strong frame (USD 6.76 over the cap, "
      "411 g over H1c); D83-L is the lightest strong frame (270 g over H1c) but USD 92.54 over the cap, almost all of it "
      "the SendCutSend pan at qty 1. Decision for the orchestrator / owner: lift the cap by about USD 7 and take B81-Lb, "
      "or fix H1c's two joints, or take D83-L if a pan quote (or a batch of frames) brings the pan under about USD 33 (D83-L without the pan is USD 116.69).\n")
    a("## 10. Assumptions (each with the test that settles it)\n")
    for s in ASSUMPTIONS:
        a(f"- {s}")
    a("")
    D.REC_MD.write_text("\n".join(w))


ASSUMPTIONS = [
    "ASSUMPTION AL5052-MIN: 5052-H32 design yield 159 / UTS 214 MPa (ASTM B209 minimums as quoted; SendCutSend typical 193 / 228). Mill cert with the order; FB-1.",
    "ASSUMPTION SN-5052-SCALE: 5052 R 0 fatigue at 1e5 = Yahr 6061 curve shape scaled to the 5052 endurance 117 MPa (5e8, Protolabs data sheet), Goodman on 214: 191.0 MPa. HP-D cycles.",
    "ASSUMPTION BRG-5052: bearing yield 1.5 x min yield at e/D 2. BB-D.",
    "ASSUMPTION KT-PIN: pin-loaded wall hole Kt 3 on the net section. BB-D, HP-D cycles.",
    "ASSUMPTION SCS-RADIUS: inside bend radius r = t, K 0.42 (SendCutSend fixes both per thickness). Their bending calculator at order; FB-1.",
    "ASSUMPTION SCS-PRICE: no live quote; price from the cited pricing page examples (method in scs_price). Quote at order.",
    "ASSUMPTION MOUNT-SPIDER: the D50 Ti base + spine web rigid within r 25 in the grillage. HP-D.",
    "ASSUMPTION grillage: the pan as strips + shear diagonals (pack5200 method); local stresses near bolts are hand-checked. HP-D.",
    "ASSUMPTION GAP-K (BL-081): pan bolt stiffness = half the two-plate Huth value (single shear). T1-D.",
    "ASSUMPTION H-PIN (BL-081): the lumbar push on the pin bounds the face (the as-designed path is the pad seat on the face, modelled with the lumbar_pad springs on the face). HP-D.",
    "ASSUMPTION BAND / BAND-BREAK (levers): 9 mm W4 band at 4.0 N m = 1212 N, retention 0.8, break >= 2 x install, 12 g, USD 1.50. CL-B.",
    "ASSUMPTION DOUBLER-EQ / DOUBLER-BOND (B81-L): bonded internal 7/8 x .049 doubler, the hole region as one 2.49 mm wall. KF-1 on a doubled offcut.",
    "ASSUMPTION LOCAL-METAL: local supplier at the Speedy list price, no shipping. Quote.",
    "ASSUMPTION ROD-PRICE: M5 A2 threaded rod 1 m share USD 3 per strut.",
    "BL-081 / BL-082 assumptions carried unchanged (CLAMP-K, CLAMP-UNIFORM, EMBED, FIT, FRET-50, CINCH-ANGLE, PAD / DROP-MASS / COMP-Z, Yahr / Goodman / Kf = Kt, BJ-NOCREDIT, CRUSH-SLEEVE, wet mu 0.15).",
    "The spreader check on D uses `bl081_local.spreader_b` with the rungs moved off the sheet and the gusset lands disabled: supports = stays + mid bar.",
]


# ----------------------------------------------------------------------------- screens
def _shrink(p, limit=1_500_000):
    from PIL import Image
    if p.stat().st_size > limit:
        im = Image.open(p)
        im = im.convert("P", palette=Image.ADAPTIVE, colors=256)
        im.save(p, optimize=True)


def screens(rec) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import trimesh
    BQ.SCREENS.mkdir(parents=True, exist_ok=True)
    files = []
    v0 = rec["variants"]["D83"]
    cfg = v0["cfg"]
    m = D.build(cfg, 19.0)
    nodes = m["nodes"]
    # 1 render (3D): tubes as cylinders + pan solids
    fig = plt.figure(figsize=(11, 9), dpi=110)
    for k, (el, az, ttl) in enumerate(((18, -125, "three-quarter from the body side (left)"), (12, -50, "three-quarter from the body side (right)"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        for name, col in (("hip_pan_tray", "#8a9aa8"), ("hip_pan_spine", "#5d6d7a"), ("lumbar_strut", "#b0b8c0")):
            tm = trimesh.load(DP.CUT / f"{name}.stl")
            tm.fix_normals()
            v_, f_ = trimesh.remesh.subdivide_to_size(tm.vertices, tm.faces, max_edge=8.0)
            tm = trimesh.Trimesh(v_, f_)
            ax.add_collection3d(Poly3DCollection(tm.vertices[tm.faces], facecolors=col, edgecolors=col, linewidths=0.2,
                                                 alpha=1.0, shade=True, lightsource=matplotlib.colors.LightSource(315, 45)))
        for mm in m["members"]:
            g = mm["group"]
            if not (g.startswith(("stay", "mid_bar", "upper_bar", "crown_leg", "crown_top_bar", "crown_spine")) or g == "hip_pivot"):
                continue
            a_, b_ = mm["nodes"]
            pa, pb = np.array(nodes[a_]), np.array(nodes[b_])
            od = 25.4 if g.startswith(("stay", "upper_bar")) else (19.05 if g == "mid_bar" else 16.0)
            col = "#3b4a3a" if g.startswith(("stay", "mid_bar", "upper_bar")) else ("#222222" if g.startswith("crown") else "#c0a060")
            cyl = trimesh.creation.cylinder(radius=od / 2, segment=np.array([pa, pb]), sections=16)
            ax.add_collection3d(Poly3DCollection(cyl.vertices[cyl.faces], facecolors=col, edgecolors=col, linewidths=0,
                                                 shade=True, lightsource=matplotlib.colors.LightSource(315, 45)))
        ax.set_xlim(-140, 140); ax.set_ylim(-140, 140); ax.set_zlim(-10, 630)
        ax.set_box_aspect((280, 280, 640), zoom=1.1)
        ax.view_init(el, az)
        ax.set_axis_off()
        ax.set_title(ttl, fontsize=10)
    fig.suptitle(f"BL-083 D83: 6061 tube stays (B81 upper frame) + formed 5052-H32 hip pan (tray .100 + spine + strut)\n"
                 f"body {v0['mass']['body_g']:.0f} g, USD {v0['cost']['per_frame_usd']:.0f}, min margin {v0['min_margin']:.2f}; "
                 f"Ti mount on the pan face at y -48.55 (belt interface unchanged)", fontsize=10)
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=0.9, wspace=0.0)
    p = BQ.SCREENS / f"{D.SHOT}1.png"
    fig.savefig(p)
    plt.close(fig)
    _shrink(p)
    files.append(p)
    # 2 utilisation map (back view + pan close-up)
    gp = json.loads((D.CACHE / "global_plot_D83.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(11, 8), dpi=100, gridspec_kw={"width_ratios": [1, 1.3]})
    norm = colors.Normalize(0, 1.0)
    cmap = matplotlib.colormaps["RdYlGn_r"]
    for ax, (h, vv, xl, yl, ttl) in zip(axs, ((0, 2, (-170, 170), (-20, 620), "back view (x-z), all members"),
                                              (1, 2, (-60, 20), (40, 200), "side view (y-z): pan wall + face + spine"))):
        for mm in m["members"]:
            if mm.get("type") == "truss" or mm["group"] in ("lumbar_plate", "pan_bolt_arm", "mount_spider"):
                continue
            a_, b_ = mm["nodes"]
            pa, pb = np.array(nodes[a_]), np.array(nodes[b_])
            u = gp["util"].get(mm["id"])
            c_ = cmap(norm(u)) if u is not None else (0.7, 0.7, 0.7, 1)
            ax.plot([pa[h], pb[h]], [pa[vv], pb[vv]], color=c_, lw=3 if u is not None else 1, solid_capstyle="round")
        ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("x (mm)" if h == 0 else "y aft (mm)"); ax.set_ylabel("z (mm)")
    marks = {"pan bolt z85": (115, 85, "z85 pan bolt"), "strut z155": (0, 155, "strut"), "upper tee": (115, 520, "upper tee"),
             "mid tee": (115, 330, "z 330"), "foot": (115, 0, "foot cup"), "Ti mount": (0, 120, "Ti mount"),
             "pan wall": (-101, 140, "pan wall"), "pan face": (-60, 120, "face")}
    for k, (x, z, key) in marks.items():
        rs = [r for r in v0["rows"] if key in r["row"] and r.get("margin")]
        if rs:
            mg = min(r["margin"] for r in rs)
            axs[0].scatter([x], [z], s=150, color=cmap(norm(1 / mg)), edgecolor="k", zorder=5)
            axs[0].annotate(f"{k}\n{mg:.2f}", (x, z), xytext=(6, 4), textcoords="offset points", fontsize=8)
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=axs, shrink=0.6,
                 label="utilisation = 1 / margin (lines: beam / grillage strength; dots: local min)")
    fig.suptitle(f"BL-083 D83 utilisation, HA-LS-1 rev C (14 case sets x 3 torsos): min margin {v0['min_margin']:.2f}\n"
                 f"{v0['governing'][:95]}", fontsize=10)
    p = BQ.SCREENS / f"{D.SHOT}2.png"
    fig.savefig(p)
    plt.close(fig)
    _shrink(p)
    files.append(p)
    # 3 flat patterns
    ft, fs = DP.flat_tray(cfg), DP.flat_spine(cfg)
    fig, axs = plt.subplots(1, 2, figsize=(12, 6.5), dpi=100, gridspec_kw={"width_ratios": [2.4, 1]})
    for ax, fp, ttl in ((axs[0], ft, f"hip pan tray, 5052-H32 {cfg['pan_t']} in, 4 bends"),
                        (axs[1], fs, f"mount spine, 5052-H32 {cfg['spine_t']} in, 2 bends")):
        xs, ys = zip(*(fp["outline"] + [fp["outline"][0]]))
        ax.fill(xs, ys, color="#dfe6ec")
        ax.plot(xs, ys, color="k", lw=1.2)
        for x, y, d in fp["holes"]:
            ax.add_patch(plt.Circle((x, y), d / 2, fill=False, color="k", lw=0.8))
        for a_, b_, lab in fp["bends"]:
            ax.plot([a_[0], b_[0]], [a_[1], b_[1]], "r--", lw=1)
        ax.set_aspect("equal")
        ax.set_title(f"{ttl}\nflat {fp['bbox'][0]:.0f} x {fp['bbox'][1]:.0f} mm ({fp['bbox'][0] / 25.4:.1f} x "
                     f"{fp['bbox'][1] / 25.4:.1f} in), hole-to-bend min {fp['hole_to_bend_min_mm']} mm", fontsize=9)
        ax.grid(alpha=0.25)
        ax.set_xlabel("mm")
    fig.suptitle("BL-083 flat patterns for SendCutSend (DXF: frame_d/cut/*.dxf; red dashed = bend lines, r = t ASSUMPTION)",
                 fontsize=10)
    fig.tight_layout()
    p = BQ.SCREENS / f"{D.SHOT}3.png"
    fig.savefig(p)
    plt.close(fig)
    _shrink(p)
    files.append(p)
    # 4 mass / cost bars
    rk = {c["option"]: c for c in rec["ranking"]}
    order = ["H1c", "B81 (reference)", "B81-L", "B81-Lb", "D83", "D83-L"]
    labs = ["H1c", "B81", "B81-L\n(.049+dblr)", "B81-Lb\n(bands)", "D83", "D83-L"]
    ms = [rk[o]["body_g"] for o in order]
    us = [rk[o]["usd"] for o in order]
    ok = [rk[o]["strong_pass"] for o in order]
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.5), dpi=100)
    cols = ["#c0504d" if not s else "#4f81bd" for s in ok]
    axs[0].bar(labs, ms, color=cols)
    axs[0].axhline(rec["baselines"]["H1c"]["body_g"], color="k", ls="--", lw=1)
    axs[0].axhline(1300, color="g", ls=":", lw=1.5)
    axs[0].text(5.4, 1300, "1300 g goal", ha="right", va="bottom", fontsize=8, color="g")
    axs[0].set_ylabel("frame body mass (g)")
    for i, x in enumerate(ms):
        axs[0].text(i, x + 15, f"{x:.0f}", ha="center", fontsize=9)
    axs[1].bar(labs, us, color=cols)
    axs[1].axhline(150, color="g", ls=":", lw=1.5)
    axs[1].text(5.4, 150, "USD 150 cap", ha="right", va="bottom", fontsize=8, color="g")
    axs[1].set_ylabel("materials per frame (USD)")
    for i, x in enumerate(us):
        axs[1].text(i, x + 3, f"{x:.0f}", ha="center", fontsize=9)
    for ax in axs:
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("BL-083 mass and cost (blue = Strong PASS, red = FAIL; dashed = H1c mass)", fontsize=11)
    fig.tight_layout()
    p = BQ.SCREENS / f"{D.SHOT}4.png"
    fig.savefig(p)
    plt.close(fig)
    _shrink(p)
    files.append(p)
    return [str(f) for f in files]


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "run"
    if arg == "run":
        run()
    elif arg == "stage":
        stage(sys.argv[2])
    elif arg == "assemble":
        assemble()
    elif arg == "md":
        r = json.loads(D.REC_JSON.read_text())
        write_md(r)
        r["screens"] = screens(r)
        D.REC_JSON.write_text(json.dumps(BR._js(r), indent=1))
