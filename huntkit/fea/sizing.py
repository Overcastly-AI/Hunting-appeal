"""Carbon pack-frame sizing sweep over buyable stock.

Design variables
- stay section: round roll-wrapped OD 16-25 mm or rectangular (lateral w x fore-aft h) tube,
- layup family (inner -> outer, angles from the tube axis):
    "RW0"  : woven 0/90 wrap, UD 0 core, woven 0/90 wrap   (standard off-the-shelf roll-wrapped)
    "RW45" : woven +-45 wrap, UD 0 core, woven +-45 wrap   (torsion-grade roll-wrapped, stock/custom)
    "UD90" : [90, +45, -45, 0_k] T700 UD                   ("[0/+-45/0] with a 90 wrap", custom)
  with the UD core ply count k setting the wall (0.8-2.0 mm),
- cross-bar section (round, same family choice), X-brace option, adhesive system.

Constraints (each must be >= 1 as a margin): for torso 15/19/23 in and all pack_standard cases,
member SF / required, buckling / 3.0, bond average SF / required, bond Volkersen peak SF /
required, fatigue (CFRP FI at 1.2 g <= 0.5, bond avg shear at 1.2 g <= 30 % lap shear).
Objective: total frame mass = tubes + hubs/sockets/sleeves/inserts + adhesive (frames.hardware_mass).
"""
from __future__ import annotations

import itertools
import time

import numpy as np

from .analysis import run_study
from .frames import build_frame
from .sections import composite_rect_tube, composite_tube

UD = "cfrp_t700_ud_epoxy_ply"
WV = "cfrp_t300_3k_woven_epoxy_ply"
UD_T, WV_T = 0.125, 0.22

# ASSUMPTION: adhesive shear moduli are not in the material records.
ADHESIVES = {
    "epoxy": {"adhesive": "adhesive_epoxy_toughened_2part", "adhesive_G_mpa": 800.0, "adhesive_t_mm": 0.3},
    "mma": {"adhesive": "adhesive_methacrylate_ma", "adhesive_G_mpa": 300.0, "adhesive_t_mm": 0.5},
}

# Base topology for the real frame (fixes from the placeholder study)
BASE = {
    "name": "pack5200_carbon",
    "height": 640.0,             # reaches a 23 in torso: yoke at 90 + 584 - 50 = 624 mm
    "width_top": 190.0,
    "width_bottom": 260.0,
    "stay_style": "straight",    # straight off-the-shelf tubes, lumbar curve in the foam
    "top_sweep": 15.0,
    "hip_z": 90.0,
    "mid_bar_z": 330.0,
    "anchors_at_nodes": True,
    "material": None,
}


def layup(family: str, k: int):
    if family == "RW0":
        return [(0, WV)] + [(0, UD)] * k + [(0, WV)]
    if family == "RW45":
        return [(45, WV)] + [(0, UD)] * k + [(45, WV)]
    if family == "UD90":
        return [(90, UD), (45, UD), (-45, UD)] + [(0, UD)] * k
    raise ValueError(family)


def wall(family: str, k: int) -> float:
    return {"RW0": 2 * WV_T, "RW45": 2 * WV_T, "UD90": 3 * UD_T}[family] + k * UD_T


def k_for_walls(family, walls=(0.8, 1.0, 1.25, 1.5, 2.0)):
    out = []
    for w in walls:
        k = int(round((w - wall(family, 0)) / UD_T))
        if k >= 1 and k not in out:
            out.append(k)
    return out


def section_spec(shape, family, k):
    """YAML-friendly spec dict (frames/_sec builds the Section)."""
    lay = [{"angle": a, "material": m} for a, m in layup(family, k)]
    if shape[0] == "round":
        return {"type": "composite_tube", "od": shape[1], "layup": lay}
    return {"type": "composite_rect_tube", "w": shape[1], "h": shape[2], "layup": lay}


def make_section(spec):
    s = dict(spec)
    typ = s.pop("type")
    lay = [(d["angle"], d["material"]) for d in s.pop("layup")]
    if typ == "composite_tube":
        return composite_tube(s["od"], lay)
    return composite_rect_tube(s["w"], s["h"], lay)


def params_for(c: dict) -> dict:
    p = dict(BASE)
    p["section"] = make_section(c["stay"])
    p["crossbar_section"] = make_section(c["bar"])
    if c.get("brace"):
        p["xbrace"] = c["brace"]
        p["brace_section"] = make_section(c["brace_sec"])
    adh = ADHESIVES[c["adhesive"]]
    st = c.get("sleeve_t", 1.0)
    p["joint"] = {**adh, "overlap_mm": c.get("overlap", 30.0), "through_overlap_mm": c.get("through_overlap", 40.0),
                  "sleeve_t_mm": st}
    p["hardware"] = {"sleeve_t_mm": st}
    return p


def evaluate(c: dict, torsos=(15, 19, 23)) -> dict:
    """Run every case at every torso setting; return margins (>= 1 passes) and mass."""
    worst = {"margin": np.inf}
    per_check = {}
    stay_margin = np.inf
    mass = None
    for t in torsos:
        fm = build_frame({**params_for(c), "torso_in": t})
        mass = fm["hardware"]
        st = run_study(fm)
        checks = []
        for name, r in st["results"].items():
            req = r.meta["required_sf"]
            checks.append((r.min_sf / req, f"{name}: member {r.critical_member['id']}", "member"))
            stay_margin = min(stay_margin, min(m["sf"] for m in r.members if m["group"].startswith("stay")) / req)
            if r.buckling_factors:
                checks.append((r.buckling_sf / 3.0, f"{name}: buckling", "buckling"))
                stay_margin = min(stay_margin, r.buckling_sf / 3.0)
            for jj in st["joints"][name]:
                checks.append((jj["sf_avg"] / req, f"{name}: bond avg {jj['joint']}/{jj['kind']}", "bond_avg"))
                checks.append((jj["sf_peak"] / req, f"{name}: bond peak {jj['joint']}/{jj['kind']}", "bond_peak"))
        f = st["fatigue"]
        for m in f["members"]:
            checks.append((m.get("sf", m.get("life", np.inf) / f["cfg"]["cycles_required"]),
                           f"fatigue member {m['member']}", "fatigue"))
        for jj in f["joints"]:
            checks.append((jj["sf"], f"fatigue bond {jj['joint']}", "fatigue"))
        for mrg, what, kind in checks:
            case = what.split(":")[0]
            per_check[(case, t)] = min(per_check.get((case, t), np.inf), mrg)
            per_check[kind] = min(per_check.get(kind, np.inf), mrg)
            if mrg < worst["margin"]:
                worst = {"margin": mrg, "what": what, "torso": t}
    return {"cand": c, "margin": worst["margin"], "governing": worst, "per_check": per_check,
            "stay_margin": stay_margin, "mass_g": mass["total_g"], "tubes_g": mass["tubes_g"],
            "hubs_g": mass["hubs_g"], "feasible": worst["margin"] >= 1.0, "label": label(c)}


def _eval_quick(c):
    return evaluate(c, (19,))


def _eval_full(c):
    return evaluate(c, (15, 19, 23))


def _map(fn, items, procs):
    if procs <= 1:
        return [fn(x) for x in items]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(procs) as pool:
        return pool.map(fn, items, chunksize=1)


def label(c: dict) -> str:
    def s(spec):
        fam = _family_of(spec)
        k = sum(1 for d in spec["layup"] if d["material"] == UD and d["angle"] == 0)
        geo = f"{spec['od']:g}" if "od" in spec else f"{spec['w']:g}x{spec['h']:g}"
        return f"{geo} {fam} k{k} ({_wall(spec):.2f})"
    out = f"stay {s(c['stay'])} | bar {s(c['bar'])}"
    if c.get("brace"):
        out += f" | X-{c['brace']} {s(c['brace_sec'])}"
    return out + f" | {c['adhesive']} | sleeve {c.get('sleeve_t', 1.0):g}"


def _family_of(spec):
    first = spec["layup"][0]
    if first["material"] == WV:
        return "RW45" if first["angle"] == 45 else "RW0"
    return "UD90"


def _wall(spec):
    return sum(WV_T if d["material"] == WV else UD_T for d in spec["layup"])


def stay_options():
    rounds = [("round", od) for od in (16, 18, 20, 22, 25)]
    rects = [("rect", 12.7, 25.4), ("rect", 15.9, 25.4), ("rect", 19.0, 25.4)]
    for shape in rounds + rects:
        for fam in ("RW0", "RW45", "UD90"):
            for k in k_for_walls(fam):
                yield section_spec(shape, fam, k)


def bar_options():
    for od in (16, 18, 20, 22, 25):
        for fam in ("RW45", "UD90"):
            for k in k_for_walls(fam, (0.8, 1.0, 1.25, 1.5)):
                yield section_spec(("round", od), fam, k)


def sweep(log=print, procs: int = 3, stage1_keep: int = 8, stage3_keep: int = 14) -> dict:
    """Staged search (quick checks at 19 in torso, full 15/19/23 in check at the end).

    1. stays (all shapes/families/walls) with a stiff reference cross-bar -> stay member margin;
    2a. cross-bars for the lightest passing stays (no brace, MMA);
    2b. X-brace and adhesive variants on the best stay/bar pairs;
    3. full 3-torso check of the lightest feasible and the Pareto set.
    """
    t0 = time.time()
    ref_bar = section_spec(("round", 22), "RW45", 6)
    c1 = [{"stay": st, "bar": ref_bar, "adhesive": "mma"} for st in stay_options()]
    s1 = _map(_eval_quick, c1, procs)
    log(f"stage 1: {len(s1)} stay options, {time.time() - t0:.0f} s")
    ok = sorted([e for e in s1 if e["stay_margin"] >= 1.0], key=lambda e: e["tubes_g"])
    best_stays = _diverse(ok, stage1_keep)

    c2 = [{"stay": e["cand"]["stay"], "bar": bar, "adhesive": "mma"}
          for e in best_stays for bar in bar_options()]
    s2a = _map(_eval_quick, c2, procs)
    log(f"stage 2a: {len(s2a)} stay/bar pairs, {time.time() - t0:.0f} s")
    # best few bars per stay by (feasible, mass) else by margin
    pairs = []
    for e in best_stays:
        mine = [x for x in s2a if x["cand"]["stay"] == e["cand"]["stay"]]
        f = sorted([x for x in mine if x["margin"] >= 1.0], key=lambda x: x["mass_g"])
        pairs += f[:2] if f else sorted(mine, key=lambda x: -x["margin"])[:2]
    brace_sec = section_spec(("round", 12.7), "RW45", 3)
    c3 = []
    for e in pairs:
        for br, adh, slv in itertools.product([None, "lower", "both"], ADHESIVES, (1.0, 2.0)):
            if br is None and adh == "mma" and slv == 1.0:
                continue
            c = {**e["cand"], "adhesive": adh, "sleeve_t": slv}
            if br:
                c.update(brace=br, brace_sec=brace_sec)
            c3.append(c)
    s2b = _map(_eval_quick, c3, procs)
    s2 = s2a + s2b
    log(f"stage 2b: {len(s2b)} brace/adhesive variants, {time.time() - t0:.0f} s")
    feas = sorted([e for e in s2 if e["margin"] >= 1.0], key=lambda e: e["mass_g"])
    pick, seen = [], set()
    for e in feas[:stage3_keep] + pareto(s2):
        if e["label"] not in seen:
            seen.add(e["label"])
            pick.append(e["cand"])
    s3 = _map(_eval_full, pick, procs)
    log(f"stage 3: {len(s3)} full 15/19/23 in checks, {time.time() - t0:.0f} s")
    return {"stage1": s1, "stage2": s2, "stage3": s3}


def _diverse(evals, n):
    """Lightest feasible per (shape-type, family) first, then fill by mass."""
    out, seen = [], set()
    for e in evals:
        key = ("od" in e["cand"]["stay"], _family_of(e["cand"]["stay"]))
        if key not in seen:
            out.append(e)
            seen.add(key)
    for e in evals:
        if len(out) >= n:
            break
        if e not in out:
            out.append(e)
    return out[:n]


def pareto(evals):
    """Non-dominated set: lower mass and higher margin."""
    pts = sorted(evals, key=lambda e: (e["mass_g"], -e["margin"]))
    out, best = [], -np.inf
    for e in pts:
        if e["margin"] > best + 1e-9:
            out.append(e)
            best = e["margin"]
    return out


# ============================================================================ deliverables
STOCK_NOTE = {
    "RW0": "standard roll-wrapped stock (twill 0/90 outer + UD core), e.g. Rock West / DragonPlate catalogue",
    "RW45": "roll-wrapped, +-45 twill wraps over a UD core (special-order wrap from the same vendors)",
    "UD90": "custom roll-wrapped T700 layup [90/+45/-45/0_k] (quote from a tube roller)",
}


def recommend(evals, prefer_stock_within: float = 0.05):
    """Lightest feasible design; a standard-stock (RW0) design within 5 % mass wins."""
    feas = sorted([e for e in evals if e["feasible"]], key=lambda e: e["mass_g"])
    if not feas:
        return None
    best = feas[0]
    for e in feas:
        if e["mass_g"] > best["mass_g"] * (1 + prefer_stock_within):
            break
        fams = {_family_of(e["cand"]["stay"]), _family_of(e["cand"]["bar"])}
        if fams == {"RW0"}:
            return e
    return best


def _spec_desc(spec):
    geo = f"OD {spec['od']:g} mm round" if "od" in spec else f"{spec['w']:g} x {spec['h']:g} mm rectangular"
    fam = _family_of(spec)
    k = sum(1 for d in spec["layup"] if d["material"] == UD and d["angle"] == 0)
    lay = {"RW0": f"[twill 0/90 / UD 0 x{k} / twill 0/90]", "RW45": f"[twill +-45 / UD 0 x{k} / twill +-45]",
           "UD90": f"[90 / +45 / -45 / 0 x{k}] T700"}[fam]
    return geo, _wall(spec), lay, fam


def stock_list(model: dict, cand: dict) -> list[dict]:
    p = model["params"]
    mem = model["members"]
    jt = p["joint"]
    stay_spec, bar_spec = cand["stay"], cand["bar"]
    stay_size = stay_spec.get("od", stay_spec.get("w"))
    bar_size = bar_spec.get("od", bar_spec.get("h"))
    slv = jt.get("sleeve_t_mm", 1.0)
    clear = stay_size / 2 + slv + 7.0   # stay centre -> crossbar tube end (inside the socket)

    def length(group):
        return sum(np.linalg.norm(np.subtract(model["nodes"][m["nodes"][1]], model["nodes"][m["nodes"][0]]))
                   for m in mem if m["group"] == group)
    rows = []
    geo, w, lay, fam = _spec_desc(stay_spec)
    rows.append({"part": "stay (L, R)", "qty": 2, "section": geo, "wall_mm": round(w, 3), "layup": lay,
                 "family": fam, "centreline_mm": round(length("stay_left"), 1),
                 "cut_length_mm": round(length("stay_left") - (bar_size / 2 + slv + 7.0), 1)})
    geo, w, lay, fam = _spec_desc(bar_spec)
    for g in ("top_bar", "mid_bar", "lumbar_bar"):
        L = length(g)
        if L:
            rows.append({"part": g.replace("_", " "), "qty": 1, "section": geo, "wall_mm": round(w, 3),
                         "layup": lay, "family": fam, "centreline_mm": round(L, 1),
                         "cut_length_mm": round(L - 2 * clear, 1)})
    if cand.get("brace"):
        geo, w, lay, fam = _spec_desc(cand["brace_sec"])
        bl = [np.linalg.norm(np.subtract(model["nodes"][m["nodes"][1]], model["nodes"][m["nodes"][0]]))
              for m in mem if m["group"] == "brace"]
        rows.append({"part": f"X-brace diagonal ({cand['brace']})", "qty": len(bl), "section": geo,
                     "wall_mm": round(w, 3), "layup": lay, "family": fam, "centreline_mm": round(max(bl), 1),
                     "cut_length_mm": round(max(bl) - 2 * clear, 1)})
    return rows


def joint_design(cand: dict) -> dict:
    adh = ADHESIVES[cand["adhesive"]]
    return {
        "adhesive": adh["adhesive"],
        "bondline_mm": adh["adhesive_t_mm"],
        "bondline_control": f"{adh['adhesive_t_mm']:g} mm glass beads (1-2 % by weight) or wire shims",
        "adhesive_shear_modulus_mpa_ASSUMPTION": adh["adhesive_G_mpa"],
        "socket_overlap_mm": cand.get("overlap", 30.0),
        "through_sleeve_overlap_mm": cand.get("through_overlap", 40.0),
        "sleeve_material": "alu_7075_t6, hard-anodised",
        "sleeve_wall_mm": cand.get("sleeve_t", 1.0),
        "sleeve_ends": "taper the sleeve wall to ~0.3 mm over the last 8 mm and chamfer the lip "
                       "(lowers the Volkersen peak; not credited in the analysis)",
        "galvanic": "never bare Al on carbon: anodise + glass-bead bondline (or 1 E-glass ply) everywhere",
        "hubs": {
            "corner_L/R (top)": "7075 corner fitting: socket for the stay top + socket for the top bar, "
                                "load-lifter eyelet insert; 2 x 2 mm CF 0/90 web plates bonded either side",
            "mid_hub_L/R": "7075 through-sleeve on the stay + socket for the mid bar; shelf-strap anchor "
                           "eye on the hub (anchors at nodes)",
            "lumbar_hub_L/R": "7075 through-sleeve on the stay + socket for the lumbar bar; hipbelt "
                              "pivot/attachment plate bolts to the hub",
            "foot_L/R": "7075 hollow insert bonded 25 mm into the stay bottom with the load-shelf pivot boss "
                        "(insert_al_7075_bonded class)",
        },
    }


def _yaml_section(spec):
    return {**{k: v for k, v in spec.items() if k != "layup"},
            "layup": [{"angle": d["angle"], "material": d["material"]} for d in spec["layup"]]}


def write_frame_yaml(e: dict, path, model: dict, extra: dict | None = None):
    import yaml
    c = e["cand"]
    p = params_for(c)
    frame = {k: v for k, v in p.items() if k not in ("section", "crossbar_section", "brace_section")}
    frame["section"] = _yaml_section(c["stay"])
    frame["crossbar_section"] = _yaml_section(c["bar"])
    if c.get("brace"):
        frame["brace_section"] = _yaml_section(c["brace_sec"])
    frame["torso_in"] = 19.0
    frame["stay_ref"] = [1.0, 0.0, 0.0]
    frame["crossbar_ref"] = [0.0, 0.0, 1.0]
    frame["n_bag"] = 5
    frame["yoke_drop"] = 50.0
    doc = {
        "schema": "huntkit.frame/v1",
        "design": "pack_5200",
        "description": "Recommended carbon frame from huntkit.fea.sizing (straight roll-wrapped stays, "
                       "bonded 7075 hubs). 'frame' maps 1:1 to huntkit.fea.frames.build_frame params; "
                       "units mm. Torso is adjustable 15-23 in: override torso_in.",
        "frame": frame,
        "torso_range_in": [15, 23],
        "stock": stock_list(model, c),
        "joints": joint_design(c),
        "mass_g": {"tubes": round(e["tubes_g"], 1), "hubs_fittings_adhesive": round(e["hubs_g"], 1),
                   "total": round(e["mass_g"], 1)},
        "results": {"min_margin": round(float(e["margin"]), 3), "governing": e["governing"]["what"],
                    "governing_torso_in": e["governing"]["torso"],
                    "margin_by_check": {k: round(float(v), 3) for k, v in e["per_check"].items()
                                        if isinstance(k, str)}},
        "source": "huntkit/fea/sizing.py; designs/pack_5200/analysis/frame_sizing.md",
    }
    if extra:
        doc.update(extra)
    header = ("# Pack 5200 carbon frame - generated by `python -m huntkit.fea.cli size`.\n"
              "# Read with huntkit.fea.frames.load_frame_params / build_frame_from_yaml.\n")
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(header + yaml.safe_dump(_plain(doc), sort_keys=False, allow_unicode=True, width=100))


def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


# ---------------------------------------------------------------------------- plots
def plot_pareto(sw: dict, rec: dict | None, png, phone: bool = True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s2, s3 = sw["stage2"], sw["stage3"]
    fig, ax = plt.subplots(figsize=(6.0, 7.2) if phone else (8, 5.5), dpi=150)
    ax.axvspan(450, 700, color="#e9e9e9", zorder=0, lw=0)
    ax.text(575, 0.06, "premium frame\nbenchmark\n450-700 g", ha="center", va="bottom", fontsize=8,
            color="#555555", transform=ax.get_xaxis_transform())
    ax.axhline(1.0, color="#555555", lw=1, ls="--")
    ax.text(ax.get_xlim()[0] if False else 0.99, 1.0, "requirement (all checks)", ha="right", va="bottom",
            fontsize=8, color="#555555", transform=ax.get_yaxis_transform())
    x2 = [e["mass_g"] for e in s2]
    y2 = [min(e["margin"], 3.0) for e in s2]
    ax.scatter(x2, y2, s=10, color="#b9c7d6", label="screened at 19 in torso", zorder=2, lw=0)
    x3 = [e["mass_g"] for e in s3]
    y3 = [min(e["margin"], 3.0) for e in s3]
    ax.scatter(x3, y3, s=26, color="#2a6fb0", label="full check 15/19/23 in", zorder=3,
               edgecolors="white", linewidths=1)
    par = pareto(s3)
    ax.plot([e["mass_g"] for e in par], [min(e["margin"], 3) for e in par], color="#2a6fb0", lw=2,
            zorder=3, label="Pareto front (full check)")
    if rec:
        ax.scatter([rec["mass_g"]], [rec["margin"]], s=120, facecolors="none", edgecolors="#222222",
                   linewidths=2, zorder=4)
        ax.annotate(f"recommended\n{rec['mass_g']:.0f} g, margin {rec['margin']:.2f}",
                    (rec["mass_g"], rec["margin"]), xytext=(18, -34), textcoords="offset points",
                    fontsize=9, color="#222222", arrowprops=dict(arrowstyle="-", color="#222222", lw=1))
    ax.set_xlabel("frame mass incl. hubs, sleeves, inserts, adhesive (g)", fontsize=9)
    ax.set_ylabel("min margin = min over all checks of SF / required SF", fontsize=9)
    ax.set_title("Carbon frame sizing: mass vs. min safety margin", fontsize=11, loc="left")
    ax.tick_params(labelsize=8)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#eeeeee", lw=0.8)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def plot_case_margins(e_full_results: dict, png):
    """Bar chart of the governing margin per load case for 15/19/23 in torso."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cases = [c for c in e_full_results["cases"]]
    torsos = e_full_results["torsos"]
    colors = {15: "#9cc0e0", 19: "#4a8ac4", 23: "#1d4f80"}
    fig, ax = plt.subplots(figsize=(6.0, 7.2), dpi=150)
    yy = np.arange(len(cases))
    h = 0.26
    for i, t in enumerate(torsos):
        vals = [min(e_full_results["margin"][(c, t)], 4.0) for c in cases]
        ax.barh(yy + (i - 1) * h, vals, height=h - 0.03, color=colors.get(t, "#4a8ac4"), label=f"{t:g} in torso")
    ax.axvline(1.0, color="#333333", lw=1, ls="--")
    ax.set_yticks(yy)
    ax.set_yticklabels([c.replace("_", " ") for c in cases], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("min margin (SF / required, incl. bonds & buckling); capped at 4", fontsize=9)
    ax.set_title("Recommended frame: margin per load case", fontsize=11, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)


def plot_worst_case(res, png, title):
    """Phone-format: deformed shape (top) + utilisation (bottom) for one Result."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import colors as mcolors
    from .report import CMAP, DEFORMED, INK, MUTED, _elastic_u, _elem_util, _setup3d
    fig = plt.figure(figsize=(6.0, 9.0), dpi=150)
    ax = fig.add_subplot(2, 1, 1, projection="3d")
    ue = _elastic_u(res)
    dmax = np.linalg.norm(ue, axis=1).max()
    sc = 0.08 * np.ptp(res.coords[:, 2]) / dmax if dmax > 0 else 1
    d = res.coords + sc * ue
    for el in res.elements:
        ax.plot(*res.coords[[el.n1, el.n2]].T, color=MUTED, lw=1, ls=(0, (2, 2)))
        ax.plot(*d[[el.n1, el.n2]].T, color=DEFORMED, lw=2.2)
    _setup3d(ax, res.coords)
    ax.set_title(f"Deformed (x{sc:.0f}), max elastic {dmax:.1f} mm", fontsize=9, color=INK)
    ax2 = fig.add_subplot(2, 1, 2, projection="3d")
    u = _elem_util(res)
    vmax = max(1.0, float(u.max()))
    norm = mcolors.Normalize(0, vmax)
    for k, el in enumerate(res.elements):
        ax2.plot(*res.coords[[el.n1, el.n2]].T, color=CMAP(norm(u[k])), lw=3, solid_capstyle="round")
    k = int(np.argmax(u))
    ax2.scatter(*res.coords[[res.elements[k].n1, res.elements[k].n2]].mean(0), s=50, facecolors="none",
                edgecolors=INK, linewidths=1.2)
    _setup3d(ax2, res.coords)
    ax2.set_title(f"Utilisation (required SF / SF), max {u.max():.2f} (circle)", fontsize=9, color=INK)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
    cax = fig.add_axes([0.2, 0.05, 0.6, 0.012])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.ax.tick_params(labelsize=7)
    fig.suptitle(title, fontsize=10, color=INK)
    fig.subplots_adjust(left=0.0, right=1.0, top=0.93, bottom=0.08, hspace=0.12)
    fig.savefig(png)
    plt.close(fig)


# ---------------------------------------------------------------------------- markdown + files
def _fmt_check(k):
    return k.replace("_", " ")


def deliver(sw: dict, design_dir="designs/pack_5200", screens_dir="outputs/screens", date="20261101",
            log=print) -> dict:
    import shutil
    from pathlib import Path
    from .load_cases import pack_standard
    design_dir, screens_dir = Path(design_dir), Path(screens_dir)
    adir = design_dir / "analysis"
    adir.mkdir(parents=True, exist_ok=True)
    screens_dir.mkdir(parents=True, exist_ok=True)
    s3 = sorted(sw["stage3"], key=lambda e: e["mass_g"])
    rec = recommend(s3)
    if rec is None:
        raise RuntimeError("no feasible design in the sweep")
    c = rec["cand"]
    model19 = build_frame({**params_for(c), "torso_in": 19})
    write_frame_yaml(rec, design_dir / "frame.yaml", model19)

    # worst case result for plots
    gov = rec["governing"]
    gcase = gov["what"].split(":")[0]
    cases = {lc.name: lc for lc in pack_standard()}
    if gcase not in cases:
        gcase = "meat_shelf_heavy_low"
    fm = build_frame({**params_for(c), "torso_in": gov["torso"]})
    res = cases[gcase].run(fm)
    png1 = adir / "frame_sizing_worst_case.png"
    plot_worst_case(res, png1, f"Recommended frame, worst case: {gcase} ({gov['torso']:g} in torso)")
    png2 = adir / "frame_sizing_pareto.png"
    plot_pareto(sw, rec, png2)
    png3 = adir / "frame_sizing_case_margins.png"
    names = list(cases) + ["fatigue"]
    plot_case_margins({"cases": names, "torsos": (15, 19, 23),
                       "margin": {(n, t): rec["per_check"].get((n, t), np.inf) for n in names
                                  for t in (15, 19, 23)}}, png3)
    shots = []
    for i, p in enumerate((png1, png2, png3), start=1):
        dst = screens_dir / f"{date}_frame_{i}.png"
        shutil.copyfile(p, dst)
        shots.append(dst)

    # full per-case report at 19 in for the record
    from .analysis import run_study
    from .report import report as write_report
    study = run_study(model19, label="Recommended carbon frame, 19 in torso")
    write_report(study, adir / "frame_sizing_cases_19in.md", title="Recommended carbon frame - all load cases (19 in torso)")

    md = _sizing_md(sw, rec, model19, gcase, png1, png2, png3)
    (adir / "frame_sizing.md").write_text(md)
    log(f"wrote {adir / 'frame_sizing.md'}, {design_dir / 'frame.yaml'}, screens {[str(s) for s in shots]}")
    return {"recommended": rec, "screens": shots, "md": adir / "frame_sizing.md"}


def _sizing_md(sw, rec, model, gcase, png1, png2, png3) -> str:
    c = rec["cand"]
    s3 = sorted(sw["stage3"], key=lambda e: e["mass_g"])
    par = pareto(s3)
    hw = model["hardware"]
    G2OZ, G2LB = 1 / 28.3495, 1 / 453.592
    L = ["# Pack 5200 - carbon frame sizing", "",
         "Owner: structural-fea-engineer. Generated by `python -m huntkit.fea.cli size` "
         "(`huntkit/fea/sizing.py`). Frame parameters: `designs/pack_5200/frame.yaml`.", "",
         "## Result", "",
         f"**Recommended frame: {rec['mass_g']:.0f} g ({rec['mass_g'] * G2OZ:.1f} oz, {rec['mass_g'] * G2LB:.2f} lb)** "
         f"including hubs, sleeves, inserts and adhesive (tubes {rec['tubes_g']:.0f} g + hardware "
         f"{rec['hubs_g']:.0f} g). Premium hunting-pack frames are about 450-700 g (1-1.5 lb) for the frame "
         f"alone, so this lands "
         + ("below" if rec["mass_g"] < 450 else "inside" if rec["mass_g"] <= 700 else "above")
         + " that band.", "",
         f"- Design: {rec['label']}",
         f"- Min margin over every check, case and torso setting: **{rec['margin']:.2f}** "
         f"(governing: {rec['governing']['what']} at {rec['governing']['torso']:g} in torso).",
         "- Passes all 7 load cases at 15, 19 and 23 in torso: members SF >= 2.0 (overload 1.5), "
         "buckling >= 3.0, bonded joints >= 2.0 (overload 1.5) on the Volkersen PEAK shear, fatigue "
         ">= 1e5 cycles at 1.2 g.", "",
         "| check | min margin (all cases, all torsos) |", "|---|---|"]
    for k in ("member", "buckling", "bond_avg", "bond_peak", "fatigue"):
        L.append(f"| {_fmt_check(k)} | {rec['per_check'].get(k, np.inf):.2f} |")
    L += ["", f"![margins per case]({png3.name})", "",
          f"![worst case]({png1.name})", "",
          f"Worst case shown: `{gcase}`. Full per-case tables and plots at 19 in: "
          "[frame_sizing_cases_19in.md](frame_sizing_cases_19in.md).", "",
          "## Topology changes from the placeholder study", "",
          "1. Frame height 560 -> **640 mm** (25.2 in): yoke at hip_z + torso - 50 mm = 624 mm for a 23 in "
          "torso, so 15-23 in is reachable on one frame with a sliding yoke (no telescoping extension).",
          "2. **Straight stays** (one off-the-shelf tube per side, foot to top). The lumbar curve goes into the "
          "lumbar pad foam. This removes the bonded elbows that governed the segmented placeholder.",
          "3. **Mid cross-bar at z = 330 mm with hubs**. The meat-shelf straps anchor on the mid hubs, lashing "
          "and load lifters on the top corner hubs, and the shelf pivots in the bonded foot inserts. Shelf and "
          "lash loads now enter at nodes rather than mid-span (placeholder meat-shelf SF went 0.68 -> >2).",
          "4. Hubs = hard-anodised 7075 sockets/through-sleeves + CF 0/90 web plates, bonded.", "",
          "## Recommended stock (buy list)", "",
          "| part | qty | section | wall mm | layup (inner -> outer) | centreline mm | cut length mm | source |",
          "|---|---|---|---|---|---|---|---|"]
    for r in stock_list(model, c):
        L.append(f"| {r['part']} | {r['qty']} | {r['section']} | {r['wall_mm']:.2f} | {r['layup']} | "
                 f"{r['centreline_mm']:.0f} | {r['cut_length_mm']:.0f} | {STOCK_NOTE[r['family']]} |")
    jd = joint_design(c)
    L += ["", "Cut lengths assume the tube ends sit 7 mm + sleeve wall beyond the stay surface inside the "
          "sockets; cut 5 mm long and trim at dry fit. Buy 1 m (or 48 in) lengths: 2 for the stays, 1 for "
          "the cross-bars.", "",
          "## Joint design", "",
          f"- Adhesive: `{jd['adhesive']}`, bondline {jd['bondline_mm']:g} mm ({jd['bondline_control']}).",
          f"- Sockets (cross-bar ends, stay tops): {jd['socket_overlap_mm']:g} mm overlap; through-sleeves on the "
          f"stays at the lumbar and mid hubs: {jd['through_sleeve_overlap_mm']:g} mm.",
          f"- Sleeves/sockets: {jd['sleeve_material']}, wall {jd['sleeve_wall_mm']:g} mm. {jd['sleeve_ends']}.",
          f"- {jd['galvanic']}."]
    for k, v in jd["hubs"].items():
        L.append(f"- **{k}**: {v}")
    L += ["- Metal inserts: 2 x 7075 foot inserts (shelf pivots), load-lifter eyelets in the corner hubs, "
          "hipbelt pivot plate bolted to the lumbar hubs, shelf-strap eyes on the mid hubs "
          "(`insert_al_7075_bonded` class; pull-test 5 samples).", "",
          "Mass breakdown of the recommended frame (g):", "",
          "| item | g |", "|---|---|", f"| tubes | {hw['tubes_g']:.1f} |"]
    for it in hw["items"]:
        L.append(f"| {it['hub']} (metal + plate {it['metal_and_plate_g']:.1f}, adhesive {it['adhesive_g']:.1f}) "
                 f"| {it['total_g']:.1f} |")
    L += [f"| **total** | **{hw['total_g']:.1f}** |", "",
          "## Sizing sweep", "",
          "Design variables: stay section (round OD 16/18/20/22/25 mm; rectangular 12.7x25.4, 15.9x25.4, "
          "19x25.4 mm with the deep side fore-aft), layup family (RW0 = stock twill 0/90 + UD core; RW45 = "
          "twill +-45 wraps + UD core; UD90 = [90/+45/-45/0_k]) with wall 0.8-2.0 mm, cross-bar section "
          "(round 16-25 mm, RW45/UD90), X-brace (none / lower / both), adhesive (toughened epoxy 0.3 mm or "
          "methacrylate 0.5 mm) and sleeve wall (1 or 2 mm). Staged search: stays screened at 19 in, "
          "cross-bars and joint options around the lightest passing stays, then a full 15/19/23 in check.", "",
          f"Evaluated: {len(sw['stage1'])} stay options, {len(sw['stage2'])} combinations at 19 in, "
          f"{len(s3)} full checks.", "",
          f"![pareto]({png2.name})", "",
          "### Pareto set (full 15/19/23 in check)", "",
          "| mass g | min margin | feasible | governing check | design |", "|---|---|---|---|---|"]
    for e in par:
        L.append(f"| {e['mass_g']:.0f} | {e['margin']:.2f} | {'yes' if e['feasible'] else 'no'} | "
                 f"{e['governing']['what']} ({e['governing']['torso']:g} in) | {e['label']} |")
    L += ["", "### Lightest full-check designs", "",
          "| mass g | min margin | feasible | governing check | design |", "|---|---|---|---|---|"]
    for e in s3[:15]:
        L.append(f"| {e['mass_g']:.0f} | {e['margin']:.2f} | {'yes' if e['feasible'] else 'no'} | "
                 f"{e['governing']['what']} ({e['governing']['torso']:g} in) | {e['label']} |")
    L += ["", "## Assumptions and caveats", "",
          "- ASSUMPTION: load cases, body springs and knockdowns as in `huntkit/fea/load_cases.py` and "
          "`composite.py` (hot/wet 0.8, impact 0.65 on compression, Tsai-Wu first-ply failure).",
          "- ASSUMPTION: adhesive shear moduli (epoxy 800 MPa, methacrylate 300 MPa) are not in the "
          "material records. The Volkersen peak scales with sqrt(G/t_bond), so this needs a supplier TDS "
          "value or a test.",
          "- ASSUMPTION: hub/fitting masses use a parametric estimate (7075 sockets with 1-2 mm wall, two "
          "2 mm CF web plates per hub, hollow foot inserts, adhesive with 1.5x fillet). Machined hub "
          "geometry will move the hardware mass by +/-30 %.",
          "- Ply data come from the T700 UD and T300 woven prepreg records. Vendor roll-wrapped tubes "
          "vary: get the vendor's layup and check it with `composite_tube`. Do 3-point-bend coupons per batch.",
          "- Not modelled: hub/fitting stresses (design the hubs to the joint loads in "
          "frame_sizing_cases_19in.md), local crushing at clamps, peel at socket lips, framesheet "
          "(a thin CF framesheet shear-buckles at a few MPa and gives little torsion stiffness, so the "
          "X-brace option was used instead), and the yoke slider track.",
          "- A 640 mm frame on a 15 in torso stands about 220 mm above the yoke. Check head clearance when "
          "looking up; the pack-designer may prefer a 600 mm frame with a 40 mm extension for long torsos.", "",
          "## Reproduce", "", "```", "python -m huntkit.fea.cli size        # ~10 min, 3 processes", "```", ""]
    return "\n".join(L)
