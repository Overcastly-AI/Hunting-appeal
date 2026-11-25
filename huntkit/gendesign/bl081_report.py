"""BL-081 driver: runs every check of frame_concepts.md section 8 on the B81 detail design, writes
``designs/pack_5200/iter2/frame_b/bl081.{json,md}``, the STLs / jigs, the cut list, the coupon list and the screenshots.

Run: ``python -m huntkit.gendesign.bl081_report run`` (about 15 min on 4 cores, most of it the solid FE unit cases,
cached in outputs/bl081/). ``... md`` re-writes the Markdown and the screens from the stored JSON.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl081_parts as BP

ITEMS = {
    "1": "Global model with real joints (members, buckling, gussets, bolts, crush sleeves, saddle plugs)",
    "2": "Lumbar rungs at their bolt holes (solid FE Kt, pin-loaded, Kf = Kt)",
    "3": "Stays: gusset-bolt holes and the crown-leg bushing stations",
    "4": "Load path without a lumbar pan (spreader.evaluate on the B81 supports)",
    "5": "Upper / mid tee clamps: slip, ovalisation and leg clearance, pawl 1001 / 1334 N",
    "6": "Hip post (two angles) and its ties to the rungs",
    "7": "Foot cups: hinge pin, US1, set-down, drop",
    "8": "IM1-IM3 anchors and the 8 fairleads on metal",
    "9": "150 N static-cinch cycles",
}


def coupons(rows: list[dict], glob: dict, cfg: dict) -> list[dict]:
    """Coupon / proof list with pass lines (forces from this record)."""
    TP = BQ.tube_props()
    tee = max(abs(np.asarray(glob["links"][k]["vec"])[2]) for k in glob["links"] if k.startswith("tee_"))
    lb = max(v["F"] for k, v in glob["links"].items() if k.startswith(("lb_", "lc_")) and "|" not in k)
    tie = max(abs(np.asarray(glob["links"][k]["vec"])[1]) for k in glob["links"] if k.startswith("tie_") and "|" not in k)
    fat_min = min(r["margin"] for r in rows if r["kind"] == "fatigue" and r["margin"] is not None)
    out = [
        {"id": "CL-1", "what": "clamp slip: 6061 half-shells + 1 x 1/4 backers + 2 x M5 A2 on a 120 mm offcut of 1 x .065, "
         "bare tube; dry / wet / wet after 24 h at 40 C under preload / -15 C, n 5 each (BL-082 spec, tube record)",
         "pass": f"minimum wet slip load >= {max(1000.5, tee) * 1.2:.0f} N at the upper-tee torque (1.2 x the larger of "
                 f"the pawl half-load 1000.5 N and the factored tee force {tee:.0f} N); no tube dent > 0.1 mm",
         "settles": "ASSUMPTIONS MU (0.15 wet), EMBED (retention 0.9), CLAMP-UNIFORM", "usd": 6.0},
        {"id": "BB-1", "what": "bolt bearing: 1 x .065 offcut, M5 + crush sleeve between two .090 gusset strips, pulled "
         "along the tube on the rig (come-along + crane scale), n 3",
         "pass": f"hole elongation <= 0.2 mm at {lb:.0f} N (largest factored gusset-bolt force) and ultimate >= "
                 f"{1.5 * lb:.0f} N", "settles": "bearing allowable at e/D 2, GAP-K joint stiffness", "usd": 3.0},
        {"id": "HB-P", "what": "hip post proof: Ti mount on the two post angles, ties to two rung offcuts held in the "
         "gusset plates on the rig; load the pin with V 1630 N (+ H 1239 N) through a lever, hold 2 min",
         "pass": "no permanent set > 0.2 mm at the pin, no hole elongation, tie spacers undamaged; then 1e4 cycles 0 -> 870 N "
                 "(walk V) with no crack (dye check)", "settles": "BRACKET-EQUIV, tie / post hand checks", "usd": 0.0},
        {"id": "OV-1", "what": "fit-up: upper tee torqued on the stay top with the crown leg and bushing inside; pull the "
         "leg with a spring scale; then hang 1415 N aft on a 25 mm loop under the tee",
         "pass": "leg slide force <= 20 N at full torque and under the loop load; feeler gauge >= 0.3 mm radial at the "
                 "bushing mouth", "settles": "ASSUMPTION FIT (bushing bore = leg + 1.0 mm), CLAMP-UNIFORM", "usd": 0.0},
        {"id": "KF-1", "what": f"notched tube fatigue (BL-082 rule: B fatigue margin {fat_min:.2f} < 1.2): 1 x .065 "
         "offcuts with an M5 crush-sleeved through-bolt, 4-point bending on the T5 crank rig, R 0.1, n 3",
         "pass": "no crack (dye check) after 1e5 cycles at 1.2 x the walk bore stress of the worst stay hole "
                 "(nominal 49 MPa x 1.2 at the hole fibre)", "settles": "Yahr mean curve, Kf = Kt, BJ-NOCREDIT", "usd": 2.0},
        {"id": "CF-1", "what": "foot cup crush: printed cup + 38 x 38 foot plate + TPU pad in the vise / on the rig",
         "pass": "no crack at 4.0 kN (2 x C4 2001 N); record crush load (T4c estimate 17.9 kN ends in local crush)",
         "settles": "ASSUMPTIONS COMP-Z, PAD, DROP-MASS", "usd": 1.5},
        {"id": "SC-1", "what": "static-cinch: 150 N x 1e4 cycles (T5 rig) on a webbing loop under a tee on a stay offcut",
         "pass": "no slip mark movement, re-torque angle < 10 deg (preload retention >= 0.9)",
         "settles": "FRET-50, CINCH-ANGLE, EMBED", "usd": 0.0},
        {"id": "PL-1", "what": "saddle plug: printed plug in a rung offcut pressed on a stay offcut sideways",
         "pass": f">= {1.5 * max(v['F'] for k, v in glob['links'].items() if k.startswith('plug_') and '|' not in k):.0f} N "
                 "without crack (1.5 x the largest factored plug force)", "settles": "PLUG-K, BEAR-PAHT", "usd": 0.5},
    ]
    return out


def margins_table(rows: list[dict], glob: dict) -> list[dict]:
    """Minimum margin per check item and kind."""
    tab = []
    for it in ITEMS:
        rs = [r for r in rows if r["item"] == it and r.get("margin") is not None]
        if not rs:
            continue
        for kind in ("strength", "fatigue", "joint", "creep"):
            ks = [r for r in rs if r["kind"] == kind]
            if ks:
                w = min(ks, key=lambda r: r["margin"])
                tab.append({"item": it, "kind": kind, "margin": round(float(w["margin"]), 3), "row": w["row"]})
    return tab


def run(log=print) -> dict:
    t0 = time.time()
    cfg = dict(BQ.CFG0)
    log("global model (flexible joints), 3 torsos")
    g = BQ.evaluate_global(cfg, log=log)
    log("global model (rigid joints, BL-080 assumption), 3 torsos")
    gr = BQ.evaluate_global(cfg, rigid=True, log=log)
    rows = []
    for k, v in g["strength"].items():
        rows.append({"item": "1", "row": f"{k}: member strength (beam, all cases)", "kind": "strength",
                     "value": v["sf"], "allow": v["required"], "margin": v["margin"],
                     "basis": f"{v['member']} {v['case']}, S-basis yield 241 MPa"})
    rows.append({"item": "1", "row": "frame buckling eigenvalue / (1.5 x case factor)", "kind": "strength",
                 "value": g["buckling"]["eigen"], "allow": None, "margin": g["buckling"]["margin"],
                 "basis": g["buckling"]["case"]})
    log("local checks")
    for f in (BL.hole_rows, BL.gusset_rows, BL.bolt_rows, BL.crush_rows, BL.hip_rows, BL.foot_rows, BL.bushing_rows,
              BL.clamp_rows, BL.fairlead_rows):
        rows += f(g, cfg)
    log("spreader.evaluate on the B81 supports")
    try:
        sp = BL.spreader_b(cfg, h=4.0)
    except Exception as e:   # pragma: no cover
        sp = {"error": repr(e)}
    if "error" not in sp:
        rows += BL.spreader_rows(sp)
    tors = {"b81_Nm_deg": BQ.torsion_stiffness(cfg), "b81_rigid_Nm_deg": BQ.torsion_stiffness(cfg, rigid=True),
            **BQ.torsion_reference()}
    tors["vs_h1"] = tors["b81_Nm_deg"] / tors["h1_Nm_deg"]
    log("parts, mass, cost")
    parts = BP.export(cfg, log=log)
    mass = BP.mass_table(cfg, parts["printed"])
    cost = BP.cost_table(cfg, mass)
    prov = BP.proving(cfg, parts["jigs"])
    tab = margins_table(rows, g)
    strong = [r for r in rows if r.get("margin") is not None and r["kind"] != "info"]
    gov = min(strong, key=lambda r: r["margin"])
    rec = {
        "ticket": "BL-081", "date": BQ.DATE, "design": "B81 (concept B detail design)", "cfg": cfg,
        "basis": {"standard": "HA-LS-1 rev C ls1_envelope, torsos 15 / 19 / 23 in",
                  "fatigue": f"BL-082 Yahr mean curve + Goodman (Su 290), R 0 smooth S_max(1e5) "
                             f"{BQ.fat_allow_local(1.0):.1f} MPa, Kf = Kt (q 1), no preload credit",
                  "friction": "BL-082 wet: Al/Al 0.15, PAHT 0.15",
                  "paht": "BL-077 hot/wet B-basis: Z 19.66, interlayer shear 11.35, fatigue 0.30, creep 0.40"},
        "min_margin": round(float(gov["margin"]), 3), "governing": gov["row"],
        "strong_pass": bool(gov["margin"] >= 1.0),
        "fatigue_min": round(min(r["margin"] for r in strong if r["kind"] == "fatigue"), 3),
        "margins_table": tab, "rows": rows,
        "global": {"strength": g["strength"], "buckling": g["buckling"], "deflection_t1": g["deflection"],
                   "rigid_joints": {"strength": gr["strength"], "buckling": gr["buckling"],
                                    "deflection_t1": gr["deflection"]},
                   "links_factored": {k: v for k, v in g["links"].items()}},
        "torsion": tors, "spreader": sp, "parts": parts, "cut_list": BP.cut_list(cfg), "mass": mass, "cost": cost,
        "proving": prov, "coupons": coupons(rows, g, cfg),
        "hole_kt": {k: BL.hole_units(k)["meta"] for k in {cfg["stay"], cfg["ctube"], cfg["ubar"]}},
        "bl082_used": ["alu_6061_t6 sn_fit_*, fatigue_smax_*, notch_sensitivity_design_ratio, anodize knockdown",
                       "alu_6061_t6_drawn_tube friction, ring crush / hoop, shipping"],
        "seconds": round(time.time() - t0, 1),
    }
    BQ.OUTDIR.mkdir(parents=True, exist_ok=True)
    BQ.REC_JSON.write_text(json.dumps(_js(rec), indent=1))
    _save_global_for_plots(g)
    write_md(rec)
    screens(rec, g)
    return rec


def _js(x):
    if isinstance(x, dict):
        return {str(k): _js(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_js(v) for v in x]
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def _save_global_for_plots(g):
    BQ.CACHE.mkdir(parents=True, exist_ok=True)
    (BQ.CACHE / "global_plot.json").write_text(json.dumps(_js({"util": g["members_util"], "disp": g.get("_disp", {})})))


# ============================================================================ screens
def screens(rec, g=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    BQ.SCREENS.mkdir(parents=True, exist_ok=True)
    gp = json.loads((BQ.CACHE / "global_plot.json").read_text())
    m = BQ.build(rec["cfg"], 15.0)
    nodes = m["nodes"]
    files = []
    # 1 deformed shape (drop case, 15 in, x 5)
    key = next((k for k in gp["disp"] if k.startswith("drop_2p5g|crown_bar|15")), next(iter(gp["disp"])))
    U = {k: np.asarray(v, float) for k, v in gp["disp"][key].items()}
    # remove the rigid-body part (the frame floats on the body springs): least-squares u = t + w x r on the frame nodes
    ks = [k for k in U if k in nodes and (k.startswith(("S", "R", "G")) and not k.startswith("SP"))]
    A, bvec = [], []
    for k in ks:
        r = np.asarray(nodes[k], float)
        for i in range(3):
            row = np.zeros(6)
            row[i] = 1.0
            e = np.zeros(3)
            e[i] = 1.0
            row[3:] = np.cross(r, e)          # (w x r)_i = w . (r x e_i)
            A.append(row)
            bvec.append(U[k][i])
    sol = np.linalg.lstsq(np.array(A), np.array(bvec), rcond=None)[0]
    U = {k: v - (sol[:3] + np.cross(sol[3:], np.asarray(nodes[k], float))) for k, v in U.items() if k in nodes}
    sc = 30.0
    fig = plt.figure(figsize=(9, 7), dpi=110)
    for i, (az, el, ttl) in enumerate(((-90, 0, "side (y-z)"), (0, 0, "back (x-z)"))):
        ax = fig.add_subplot(1, 2, i + 1)
        for mm in m["members"]:
            if mm["group"] in ("lumbar_plate", "lumbar_plate_shear") or mm.get("type") == "truss":
                continue
            a, b = mm["nodes"]
            pa, pb = np.array(nodes[a]), np.array(nodes[b])
            ua, ub = np.array(U.get(a, [0, 0, 0])), np.array(U.get(b, [0, 0, 0]))
            h, v = (1, 2) if i == 0 else (0, 2)
            ax.plot([pa[h], pb[h]], [pa[v], pb[v]], color="0.75", lw=1)
            ax.plot([pa[h] + sc * ua[h], pb[h] + sc * ub[h]], [pa[v] + sc * ua[v], pb[v] + sc * ub[v]],
                    color="#1f6fb4", lw=1.6)
        ax.set_aspect("equal")
        ax.set_title(ttl, fontsize=11)
        ax.set_xlabel("y aft (mm)" if i == 0 else "x (mm)")
        ax.set_ylabel("z (mm)")
        ax.grid(alpha=0.3)
    fig.suptitle(f"BL-081 B81: elastic deformed shape (rigid-body motion on the body springs removed), C2 stumble "
                 f"2.0 g x 1.5, torso 15 in, x{sc:g}; grey = undeformed\n"
                 f"T1 prediction at 150 lb, 19 in: crown {rec['global']['deflection_t1']['19']['crown_elastic_mm']:.1f} mm "
                 f"elastic (band +/-30 %)", fontsize=10)
    p = BQ.SCREENS / f"{BQ.SHOT}1.png"
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    files.append(p)
    # 2 utilisation map
    fig, ax = plt.subplots(figsize=(7, 9), dpi=110)
    norm = colors.Normalize(0, 1.0)
    cmap = matplotlib.colormaps["RdYlGn_r"]
    for mm in m["members"]:
        if mm["group"] in ("lumbar_plate", "lumbar_plate_shear") or mm.get("type") == "truss":
            continue
        a, b = mm["nodes"]
        pa, pb = np.array(nodes[a]), np.array(nodes[b])
        u = gp["util"].get(mm["id"])
        c = cmap(norm(u)) if u is not None else (0.6, 0.6, 0.6, 1)
        ax.plot([pa[0], pb[0]], [pa[2], pb[2]], color=c, lw=4 if u is not None else 1.5, solid_capstyle="round")
    # local check markers
    marks = {"stay z135": (115, 135), "stay z105": (115, 105), "rung tie": (22, 150), "rung end": (90, 90),
             "upper tee": (115, 520), "mid tee": (115, 330), "foot": (115, 0), "hip post": (0, 120)}
    loc = {"stay z135": "stay z135", "stay z105": "stay z105", "rung tie": "tie bolt", "rung end": "gusset bolt",
           "upper tee": "upper tee", "mid tee": "z 330", "foot": "foot cup", "hip post": "front leg"}
    for k, (x, z) in marks.items():
        rs = [r for r in rec["rows"] if loc[k] in r["row"] and r.get("margin")]
        if rs:
            mg = min(r["margin"] for r in rs)
            ax.scatter([x], [z], s=160, color=cmap(norm(1 / mg)), edgecolor="k", zorder=5)
            ax.annotate(f"{k}\n{mg:.2f}", (x, z), xytext=(8, 4), textcoords="offset points", fontsize=8)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=ax, shrink=0.6, label="utilisation = 1 / margin (members: beam strength; dots: local min)")
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("z (mm)")
    ax.set_title(f"BL-081 B81 utilisation, all HA-LS-1 rev C cases\nmin margin {rec['min_margin']:.2f}: "
                 f"{rec['governing'][:60]}", fontsize=10)
    fig.tight_layout()
    p = BQ.SCREENS / f"{BQ.SHOT}2.png"
    fig.savefig(p)
    plt.close(fig)
    files.append(p)
    # 3 printed parts detail
    import trimesh
    names = [("foot_cup_R", "foot cup (pin cheek in compression)"), ("rung_saddle_plug_R", "rung saddle plug"),
             ("bar_socket_upper_R", "upper bar socket (bears on shells)"), ("im1_collar_R", "IM1 collar"),
             ("stay_top_collar_R", "stay-top collar")]
    fig = plt.figure(figsize=(10, 7), dpi=100)
    for i, (n, ttl) in enumerate(names):
        ax = fig.add_subplot(2, 3, i + 1, projection="3d")
        tm = trimesh.load(BP.PRINT / f"{n}.stl")
        v = tm.vertices - tm.vertices.mean(axis=0)
        ax.plot_trisurf(v[:, 0], v[:, 1], v[:, 2], triangles=tm.faces, color="#556b2f", edgecolor="none",
                        linewidth=0, alpha=0.95, shade=True)
        r = np.abs(v).max()
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r, r)
        ax.set_title(f"{ttl}\n{tm.volume * BQ.RHO_PAHT:.1f} g PAHT", fontsize=8)
        ax.set_axis_off()
        ax.view_init(22, -55)
    ax = fig.add_subplot(2, 3, 6)
    ax.axis("off")
    ax.text(0, 0.95, "Printed parts carry no preload (BL-082).\nLoad paths are 6061 or bolts;\nPAHT only in "
            "bearing / compression:\n- foot cup cheek: pin bearing\n- saddle plug: fore-aft bearing\n- bar socket: bar "
            "end on the shells\n- collars: rest on metal\nTee clamps: 6061 half-shells\n(1-1/4 x .125, sawn) + 1 x 1/4 "
            "backers", va="top", fontsize=9)
    fig.suptitle("BL-081 B81 printed PAHT-CF parts (STL in designs/pack_5200/iter2/frame_b/print)", fontsize=11)
    fig.tight_layout()
    p = BQ.SCREENS / f"{BQ.SHOT}3.png"
    fig.savefig(p)
    plt.close(fig)
    files.append(p)
    # 4 margins table
    tab = rec["margins_table"]
    fig, ax = plt.subplots(figsize=(11, 0.42 * len(tab) + 2.0), dpi=100)
    ax.axis("off")
    cells = [[t["item"], t["kind"], f"{t['margin']:.2f}", t["row"][:78]] for t in tab]
    tb = ax.table(cellText=cells, colLabels=["#", "kind", "margin", "governing row"], loc="center",
                  colWidths=[0.04, 0.09, 0.08, 0.79], cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8.5)
    tb.scale(1, 1.35)
    for (i, j), c in tb.get_celld().items():
        if i > 0 and j == 2:
            mg = tab[i - 1]["margin"]
            c.set_facecolor("#f4b6b6" if mg < 1.0 else ("#fde9a9" if mg < 1.2 else "#cde8c4"))
    ax.set_title(f"BL-081 B81 margins (min {rec['min_margin']:.2f}, fatigue min {rec['fatigue_min']:.2f}); "
                 f"body {rec['mass']['body_g']:.0f} g, USD {rec['cost']['per_frame_usd']:.2f} / frame", fontsize=10)
    fig.tight_layout()
    p = BQ.SCREENS / f"{BQ.SHOT}4.png"
    fig.savefig(p)
    plt.close(fig)
    files.append(p)
    return [str(f) for f in files]


# ============================================================================ markdown
def write_md(rec: dict) -> None:
    from huntkit.gendesign.bl080_metal_frame import H1, H1C
    L = []
    w = L.append
    c = rec["cfg"]
    m, co = rec["mass"], rec["cost"]
    w("# BL-081: concept B detail checks (B81)\n")
    w("Owner: structural-fea-engineer, 2026-11-25. Source: `designs/pack_5200/iter2/frame_concepts.md` section 8, "
      "`huntkit/gendesign/bl080_metal_frame.py` (not edited). Code: `huntkit/gendesign/bl081_concept_b.py` (model), "
      "`bl081_local.py` (local checks), `bl081_parts.py` (STL, cut list, bill), `bl081_report.py` (this record); solid "
      "submodel `huntkit/fea/tube_solid.py`. Numbers: [bl081.json](bl081.json). Tests: `tests/test_bl081_concept_b.py`, "
      "`tests/test_tube_solid.py`. Units mm, N, MPa, g, USD (imperial in brackets).\n")
    w("## 0. Answer\n")
    w(f"- **Strong: {'PASS' if rec['strong_pass'] else 'FAIL'}, min margin {rec['min_margin']:.2f}** "
      f"({rec['governing']}); fatigue minimum {rec['fatigue_min']:.2f} on the BL-082 basis (Yahr mean curve, Goodman, "
      "Kf = Kt, no preload credit). Every row of section 8 is checked on real joints; nothing is rigid or idealised "
      "except where an ASSUMPTION says so.")
    w(f"- **It is not the BL-080 concept B any more.** The first-order B passed only because its joints were rigid "
      "and its printed tees carried everything for free. On the honest basis three of its joints could not be made "
      "to work, so B81 changes them (section 2): twin lumbar rungs (z 85 / 155) instead of one cross tube; a hip post "
      "of two angles tied to both rungs instead of a bracket bolted through one tube; 6061 half-shell clamps instead "
      "of printed clamp tees; 1 x .065 tube for stays, rungs and upper bar; crush sleeves in every through-bolt.")
    w(f"- **Mass {m['body_g']:.0f} g ({m['body_g'] / 453.6:.2f} lb) body**, {m['vs_bl080_b_g']:+.0f} g against the BL-080 "
      f"booking (1013.3 g), {m['frame_delta_vs_h1_g']:+.0f} g vs H1 and {m['frame_delta_vs_h1c_g']:+.0f} g vs H1c "
      "(frame body + hip fixings).")
    w(f"- **Cost USD {co['per_frame_usd']:.2f} per frame: {'inside' if co['within_cap'] else 'OVER'} the USD 150 cap** "
      f"(proving USD {rec['proving']['total_usd']:.2f}).")
    w("- Recommendation to the orchestrator: B81 is the first version of B that is strong on an honest basis, but it "
      "loses the rubric's mass axis to H1c and misses the cost cap; see section 7 for the levers and the decision.\n")
    w("## 1. Margins (minimum per check item and kind)\n")
    w("| # | check | kind | margin | governing row |\n|---|---|---|---:|---|")
    for t in rec["margins_table"]:
        w(f"| {t['item']} | {ITEMS[t['item']].split(' (')[0]} | {t['kind']} | {t['margin']:.2f} | {t['row']} |")
    w("\nEvery row with its value, allowable and basis is in `bl081.json` `rows`. Margin = allowable / value with the "
      "case factor in the forces (factored = x case factor; walk = static carry x 1.6 g, 1e5 cycles, R 0).\n")
    w("## 2. What B81 is (and why each change)\n")
    w("| node | BL-080 B (first order) | B81 | why |\n|---|---|---|---|")
    w("| lumbar | 1 x .049 cross tube z 120, printed tees bolted to stays, Ti mount on a 20 x 3 tube stand-in | twin 1 x "
      ".065 rungs z 85 / 155; per side a pair of .090 6061 gussets (front / back), 2 stay bolts z 105 / 135, 2 bolts per "
      "rung end x 90 / 62; a printed saddle plug in each rung end takes the fore-aft load in bearing | the hip pin is "
      "67 mm in front of the tube line (V x 67 = 110 N m factored); a single 1 in tube can only take that as torsion "
      "through bolt couples across 24 mm, which failed bearing (0.95) and fatigue (0.49); two rungs turn it into "
      "axial tie forces. Thin plates cannot carry fore-aft shear out of plane, hence the plug |")
    w("| hip | 2 x 1-1/2 angle bracket (not modelled) | hip post: two 1-1/2 x 1/8 angles 90 mm, front legs = Ti mount face "
      "(6 of the 8 BL-055 positions, through-bolted), stems aft; 4 x M5 ties at (+/-30, z 85 / 155) through 3/4 x .035 "
      "spacers and crush-sleeved rungs; 1 x 1/8 backer strips behind the front legs at the ties | the post carries "
      "the torque as bending (2 x 32.4e3 mm4), the ties as axial load |")
    w("| upper / mid tees | printed split tees, metal-backed, mu 0.2 | two half-shells sawn from 1-1/4 x .125 6061 "
      "tube (bore 1 in), 1 x 1/4 backers, 2 x M5 A2 beside the stay (2.6 kN mid, 2.0 kN upper); printed bar socket "
      "bears on the shells | BL-082: no printed part under preload, mu 0.15 wet; a 1/8 backer bends to 0.26; the "
      "conforming shells keep the bore round (leg clearance) |")
    w("| tubes | 1 x .049 stays / cross tube / upper bar | 1 x .065 (Speedy p-4588: cheaper per inch than .049) | "
      "stay gusset-bolt holes 0.86 and rung tie holes 0.93 in fatigue with .049 on the BL-082 basis |")
    w("| through-bolts | M5, preload on the bare tube | M5 + 5/16 x .035 crush sleeve in every tube | BL-082 CRUSH-SLEEVE: "
      "2.6 kN over 20 mm is 4.2 x the collapse load |")
    w("| foot | printed cup | printed cup + 38 x 38 x 1/8 6061 foot plate + 6 mm TPU pad; 5 mm 7075 hinge pull-pin z 60 "
      "(BL-041) with the outer cheek in bearing | set-down and drop on metal |")
    w("| fairleads / IM | printed cleats | webbing loops round the stay at z 60 (pin), 190, 330, 520, located by printed "
      "collars that rest on metal | PAHT in compression only |\n")
    w("## 3. Global model with real joints (item 1)\n")
    gl = rec["global"]
    w("Bolts are Huth (1986) springs (x 0.5, ASSUMPTION GAP-K) held at both ends, so a bolt through a tube passes a couple "
      "about both axes normal to it (2 k R^2); gusset bolts carry no axial load (plates out of plane), the saddle plugs "
      "do; clamp tees are 2e4 N/mm / 2e8 N mm/rad links (ASSUMPTION CLAMP-K); the hip pin sits at its 21 mm stand-off.\n")
    w("| | B81 joints | same geometry, rigid joints |\n|---|---:|---:|")
    for k in gl["strength"]:
        r = gl["rigid_joints"]["strength"].get(k)
        w(f"| {k} strength margin | {gl['strength'][k]['margin']:.2f} | {r['margin'] if r else float('nan'):.2f} |")
    w(f"| buckling margin (eigen) | {gl['buckling']['margin']:.2f} ({gl['buckling']['eigen']:.2f}) | "
      f"{gl['rigid_joints']['buckling']['margin']:.2f} |")
    for t in ("15", "19", "23"):
        d = gl["deflection_t1"][t]
        r_ = gl["rigid_joints"]["deflection_t1"][t]
        w(f"| T1 crown elastic deflection, 150 lb, {t} in (mm) | **{d['crown_elastic_mm']:.1f}** (band {d['band_lo']:.1f}-"
          f"{d['band_hi']:.1f}) | {r_['crown_elastic_mm']:.1f} |")
        w(f"| crown vs hip pin incl. rotation on the body springs, {t} in (mm) | {d['crown_rel_hip_y_mm']:.1f} | "
          f"{r_['crown_rel_hip_y_mm']:.1f} |")
    tr = rec["torsion"]
    w(f"\nTorsion stiffness (record test: hip clamped, +/- F at the stay tops): B81 **{tr['b81_Nm_deg']:.1f} N m/deg** "
      f"(rigid joints {tr['b81_rigid_Nm_deg']:.1f}); tube frame {tr['tube_Nm_deg']:.2f}, H1 {tr['h1_Nm_deg']:.2f} "
      f"({tr['h1_basis']}): **{tr['vs_h1']:.1f} x H1**.\n")
    w("T1 prediction = the elastic number: crown-top fore-aft deflection relative to the lumbar block (stays z 90-150 "
      "taken as a rigid body). On the rig read the crown and the lumbar gauges (load_standard 5.2) plus a second lumbar "
      "gauge 60 mm higher for the lumbar rotation, and compare crown - (lumbar + rotation x lever) with the band. The "
      "crown-vs-pin number includes the frame rotating on the body springs (shoulder straps), which the rig's straps "
      "set, not the frame.\n")
    w("## 4. Holes, bushings, clamps (items 2, 3, 5)\n")
    for k, v in rec["hole_kt"].items():
        kt = v["kt_gross"]
        w(f"- Solid FE hole Kt, {k} with D5.3 through-hole (gross): tension {kt['tension']:.2f}, bending with the hole on "
          f"the extreme fibre {kt['bending_hole_on_extreme_fibre']:.2f}, on the neutral axis "
          f"{kt['bending_hole_on_neutral_axis']:.2f}, torsion (on tau) {kt['torsion_on_tau']:.2f}, pin bearing along / "
          f"across the tube {kt['bearing_axial_on_sigma_br']:.2f} / {kt['bearing_circ_on_sigma_br']:.2f} (on P/dt).")
    w("- The hole rows superpose 12 unit fields (6 section forces, 4 pin-bearing directions, 2 washer / spacer "
      "patches) with the actual section and bolt forces of every case: the bore peak is the real pin-loaded Kt peak, "
      "and Kf = Kt (BL-082).")
    w("- Bushing and clamp rows take the hoop (ring) stress of the solid model, so the submodel's own beam bending is "
      "not double-counted, and combine it with the global stay stress (VM, opposite signs).\n")
    w("## 5. Spreader without a lumbar pan (item 4)\n")
    sp = rec["spreader"]
    if "error" in sp:
        w(f"spreader.evaluate failed: {sp['error']} (open item).\n")
    else:
        w(f"`spreader.evaluate({sp['sheet']}, h {sp['h']:g})` with the B81 supports patched in (round stays, rungs z 85 / "
          f"155 and the mid bar as beams, gusset plates as lands, clips z 166 / 260 / 400): first-ply SF "
          f"{sp['sf_fpf']:.2f}, fatigue {sp['sf_fatigue']:.2f}, sandwich local {sp.get('sandwich_sf_min') or float('nan'):.2f}, "
          f"walk clearance {sp['clear_walk_min']:.1f} mm, factored clearance {sp['clear_fact_min']:.1f} mm, skin peak "
          f"{sp['skin_peak_kpa']:.1f} kPa (limit 14), checks {sp['checks']}.\n")
    w("## 6. Mass and cost\n")
    w("| item | g |\n|---|---:|")
    for k, v in m["rows"].items():
        w(f"| {k} | {v:.1f} |")
    w(f"| **body** | **{m['body_g']:.1f}** |\n| Ti mount fixings (6 x M5 x 16 A2 + nuts) | {m['hip_hw_g']:.1f} |\n")
    w("| line | USD | source |\n|---|---:|---|")
    for l in co["lines"]:
        w(f"| {l['item']} | {l['usd']:.2f} | {l['source']} |")
    w(f"| **per frame** | **{co['per_frame_usd']:.2f}** | cap 150 |\n")
    w("Proving: " + "; ".join(f"{l['item']} {l['usd']:.2f}" for l in rec["proving"]["lines"])
      + f" = USD {rec['proving']['total_usd']:.2f} (cap 150).\n")
    w("Cut list (`bl081.json` `cut_list`):\n")
    w("| part | stock | qty | length mm | holes | jig |\n|---|---|---:|---:|---|---|")
    for r in rec["cut_list"]:
        w(f"| {r['part']} | {r['stock']} | {r['qty']} | {r['length_mm'] if r['length_mm'] else '-'} | {r['holes']} | {r['jig']} |")
    w("\n## 7. Mass and cost: where B81 stands and the levers\n")
    w(f"- B81 is {m['body_g'] - H1C['body_g']:+.0f} g against H1c ({H1C['body_g']} g) and {m['body_g'] - H1['body_g']:+.0f} g "
      f"against H1. The BL-080 1013 g relied on rigid printed joints; the metal that makes the joints honest "
      f"(gussets, half-shells, 1/4 backers, post, sleeves, 36 bolts) is about {m['body_g'] - 1013:.0f} g.")
    w("- Lighter levers that keep the margins (not taken, each needs its own check): hose-band clamps on the half-shells "
      "instead of 1/4 backers and bolts (about -150 g, needs CL-1); .049 stays with an internal 7/8 x .049 doubler only "
      "at z 95-145 (about -60 g); Ti screws (-130 g, about +USD 90: over cap); a skeletonised foot cup (-50 g).")
    w(f"- Cost levers: pick up the metal at a local supplier (-USD {BQ.tube_props()['ship_base']:.0f} shipping); share the "
      "M5 50-pack over two frames; the cap itself is an orchestrator ASSUMPTION the owner may override.")
    w("- Decision for the orchestrator: (a) accept B81 as the strong-but-heavy metal reference and run the lighter "
      "levers as BL-083, or (b) go back to H1c / concept D (formed pan: the pan carries the hip torque as a plate, "
      "which is the load path B lacks).\n")
    w("## 8. Coupons and proof tests (pass lines)\n")
    w("| id | what | pass | settles | USD |\n|---|---|---|---|---:|")
    for k in rec["coupons"]:
        w(f"| {k['id']} | {k['what']} | {k['pass']} | {k['settles']} | {k['usd']:.2f} |")
    w("\n## 9. Parts and files\n")
    w("Printed (PAHT-CF, solid, STL per side): " + ", ".join(
        f"{n} {v['mass_g_each']:.1f} g x {v['count']}" for n, v in rec["parts"]["printed"].items())
      + ". Jigs (PLA): " + ", ".join(rec["parts"]["jigs"]) + ". All STL watertight: "
      + str(all(v["watertight"] for v in list(rec["parts"]["printed"].values()) + list(rec["parts"]["jigs"].values()))) + ".\n")
    w("For the manufacturing-engineer (parts-list deltas, do not edit their files here): remove the printed lumbar / mid / "
      "upper tees and their 1/8 backers; add 4 .090 gussets, 2 post angles, 2 tie strips, 4 half-shell sets "
      "(1-1/4 x .125), 8 x 1/4 backers, 18 crush sleeves, 4 tie spacers, 4 saddle plugs, 2 IM1 collars, 2 foot plates, "
      "2 TPU pads; 36 x M5 A2 (lengths in `bl081_parts.BOLTS`); stock 1 x .065 instead of 1 x .049. The BL-077 / BL-079 "
      "kit generators would need the same deltas for the coupon kit (CL-1, BB-1, KF-1, PL-1 pieces).\n")
    w("## 10. Assumptions (each with the test that settles it)\n")
    for a in ASSUMPTIONS:
        w(f"- ASSUMPTION {a}")
    BQ.REC_MD.write_text("\n".join(L) + "\n")


ASSUMPTIONS = [
    "GAP-K: Huth fastener stiffness x 0.5 for the shim / fit gap. Settled by BB-1 (load-displacement).",
    "CLAMP-K: clamp tees as 2e4 N/mm and 2e8 N mm/rad links. Settled by OV-1 / CL-1 (stiffness), T1 deflection.",
    "GUSSET-J: gusset pair torsion as differential in-plane plate bending, GJ = 6 E I_p d^2 / L^2. Settled by HB-P.",
    "PLUG-K: saddle plug 3e4 N/mm in compression, no tension. Settled by PL-1.",
    "BRACKET-EQUIV: the post's front legs between the mount and the ties use the 2-angle section. Settled by HB-P.",
    "RADIAL-HOLE: holes modelled radial in the solid submodel (< 5 % edge-angle difference at d/D 0.21).",
    "CLAMP-UNIFORM: conforming 6061 half-shells give uniform pressure over +/- 86.5 deg (1.5 mm kerf gaps). OV-1, CL-1.",
    "EMBED: preload retention 0.9 in the all-metal clamp stack (no PAHT in the preload path). CL-1 wet after 24 h at 40 C.",
    "FIT: crown bushing bore = leg OD + 1.0 mm (0.5 mm radial), >= 0.3 mm must remain. OV-1.",
    "FRET-50: cyclic tangential load <= 0.5 x slip capacity gives no fretting. SC-1.",
    "CINCH-ANGLE: 30 % of the 150 N cinch acts along the stay. SC-1.",
    "PAD / DROP-MASS / COMP-Z: T4c drop estimate (1.6 kg rigid, 6 mm TPU pad, PAHT crush 2.4 x Z tension). CF-1, T4c.",
    "SHELL-PRICE, FLAT14-PRICE, SLEEVE-PRICE, SHIP-BASE: prices without a read listing. Quotes at order.",
    "H-PIN: the lumbar push H (1239 N C2, 661 N walk) on the hip pin (BL-055 bound) for the mount tipping rows.",
    "Hinge eye between the outer cup cheek and the stay wall, load spread over 18 mm (BL-041 eye). Fit-up trial.",
    "BL-082 (used as recorded): Yahr mean curve + Goodman (Su 290) R 0 S_max(1e5) 190.9 MPa (Goodman chosen over "
    "Gerber because the curve is a mean curve with no scatter factor; Gerber would give about +25 %), Kf = Kt, "
    "BJ-NOCREDIT, ANODISE-FAT (holes and clamp zones left bare: no knock-down applied), CRUSH-SLEEVE, wet friction "
    "0.15, ring crush / hoop limits. KF-1 settles the fatigue basis because the fatigue minimum is under 1.2.",
]


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        r = run()
        print("min margin", r["min_margin"], r["governing"])
    elif cmd == "md":
        rec = json.loads(BQ.REC_JSON.read_text())
        write_md(rec)
        print(screens(rec))
