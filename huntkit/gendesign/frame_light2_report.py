"""Plots, concept YAML and the analysis doc for the lighter-frame study 2 (``frame_light2``).

``write_all(ctx)`` takes ``frame_light2.run()`` output. ``docs_only()`` rebuilds everything from the saved results
JSON (no FEA), except the deformed-shape plot, which needs the model (it re-solves one static case, ~2 s).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from . import frame_light2 as L

ORDER = ("NODE", "TENDON", "BRANCH", "SKIN")
COL = {"tubes": "#3b4a5a", "printed nodes + clips": "#c9772c", "carbon tendon wraps": "#1f1f1f",
       "bonds (MMA)": "#9aa7b1", "lumbar pan + pad-up": "#6b7f8e", "crown + torso adjust (unchanged)": "#a8b5a0",
       "Ti pivot mount + inserts": "#7e6aa8", "printed skin (non-structural)": "#e3b27a", "spreader": "#d9d9d9"}


def _save(fig, n: int, title_slug: str = "") -> str:
    L.SCREENS.mkdir(parents=True, exist_ok=True)
    path = L.SCREENS / f"{L.SHOT}_{n}.png"
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    _shrink(path)
    return str(path)


def _shrink(path: Path, limit: int = 1_500_000):
    from PIL import Image
    p = Path(path)
    while p.stat().st_size > limit:
        im = Image.open(p)
        im = im.resize((int(im.width * 0.85), int(im.height * 0.85)), Image.LANCZOS)
        im.save(p, optimize=True)


# ----------------------------------------------------------------------------- plots
def plot_mass(ctx) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [("Today: printed\nbranch body", {"printed body (PAHT-CF)": L.TODAY["printed_body_g"],
                                             "crown + torso adjust (unchanged)": L.TODAY["non_body_g"]
                                             + L.TODAY["crown_fix_g"], "spreader": L.TODAY["spreader_g"]})]
    for k in ORDER:
        c = ctx["concepts"][k]
        g = dict(c["mass"]["groups"])
        g["spreader"] = L.TODAY["spreader_g"]
        rows.append((k + ("\n(fails rev C)" if not c["summary"]["pass"] else ""), g))
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    keys = ["printed body (PAHT-CF)"] + list(COL)
    col = {**COL, "printed body (PAHT-CF)": "#b5651d"}
    for i, (lab, g) in enumerate(rows):
        x0 = 0.0
        for k in keys:
            v = g.get(k, 0.0)
            if v <= 0:
                continue
            ax.barh(i, v, left=x0, color=col[k], edgecolor="white", height=0.62)
            if v > 45:
                ax.text(x0 + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                        color="white" if k not in ("spreader", "printed skin (non-structural)",
                                                   "crown + torso adjust (unchanged)") else "black")
            x0 += v
        ax.text(x0 + 12, i, f"{x0:.0f} g", va="center", fontsize=9, fontweight="bold")
    ax.axvline(440, color="#b03030", ls="--", lw=1.2)
    ax.text(448, -0.42, "440 g: frame + spreader for a 6.6 lb pack", color="#b03030", fontsize=8,
            va="bottom")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("frame + spreader mass (g)")
    ax.set_xlim(0, 1400)
    handles = [plt.Rectangle((0, 0), 1, 1, color=col[k]) for k in keys]
    ax.legend(handles, keys, fontsize=7.5, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    ax.set_title("Lighter frame study 2: where the grams are (frame + Sandwich v2 spreader)", fontsize=11)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return _save(fig, 1)


FAMILY = [("member", "tube first-ply"), ("frame buckling", "frame buckling"), ("bond avg", "bond, average"),
          ("bond Volkersen", "bond, Volkersen peak"), ("crown", "crown (unchanged)"), ("lumbar pan", "lumbar pan"),
          ("foot boot", "foot boot"), ("stay-top collar", "stay-top collar"), ("stay ring", "stay ring"),
          ("hip node", "hip node"), ("stay clip", "stay clips"), ("torso adjust", "rack"), ("fatigue", "fatigue")]


def family_minima(summary) -> dict:
    out = {}
    for k, (v, where) in summary["checks"].items():
        for pre, lab in FAMILY:
            if k.startswith(pre):
                if lab not in out or v < out[lab][0]:
                    out[lab] = (v, k, where)
                break
    return out


def plot_utilization(ctx, best: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.8), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axs[0]
    labs = [lab for _, lab in FAMILY]
    width = 0.2
    for i, k in enumerate(ORDER[:3]):
        fm = family_minima(ctx["concepts"][k]["summary"])
        vals = [min(fm[l][0], 4.0) if l in fm else np.nan for l in labs]
        y = np.arange(len(labs)) + (i - 1) * width
        ax.barh(y, vals, height=width, label=k, color=("#c9772c", "#1f1f1f", "#5a7d5a")[i])
    ax.axvline(1.0, color="#b03030", lw=1.2)
    ax.set_yticks(range(len(labs)), labs, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 4.0)
    ax.set_xlabel("worst margin = SF / HA-LS-1 rev C requirement (clipped at 4)")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.set_title("Worst margin per check family (15/19/23 in, both couples)", fontsize=10)
    ax = axs[1]
    by = ctx["concepts"][best]["summary"]["by_case"]
    names = [k for k in by]
    vals = [by[k][0] for k in names]
    order = np.argsort(vals)
    cols = ["#b03030" if vals[i] < 1 else ("#d99a2b" if vals[i] < 1.25 else "#4f7f4f") for i in order]
    ax.barh(range(len(order)), [min(vals[i], 3) for i in order], color=cols)
    for j, i in enumerate(order):
        ax.text(min(vals[i], 3) + 0.03, j, f"{vals[i]:.2f}", va="center", fontsize=7.5)
    ax.set_yticks(range(len(order)), [names[i].replace("|crown_bar", "").replace("|strap_upper", " (IM3)")
                                      for i in order], fontsize=7.5)
    ax.invert_yaxis()
    ax.axvline(1.0, color="#b03030", lw=1.2)
    ax.set_xlim(0, 3.3)
    ax.set_title(f"{best}: worst margin per rev C case (all checks)", fontsize=10)
    for a in axs:
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    fig.tight_layout()
    return _save(fig, 2)


def plot_deformed(ctx, best: str) -> str:
    """Static carry (rev C, couple on the crown bar), 19 in: member utilisation colour + deformed shape x 5."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from huntkit.fea.load_standard import ls1_envelope
    cand = ctx["concepts"][best]["cand"]
    m = L.build(cand, 19.0)
    c = next(x for x in ls1_envelope("C")["crown_bar"] if x.name == "meat_straps")
    c.buckling = False
    res = c.run(m)
    req = c.required_sf
    U = res.u.reshape(-1, 6)[:, :3]
    idx = {n: i for i, n in enumerate(res.node_ids)}
    # free-free (inertia relief): remove the best-fit rigid-body motion so only the elastic deformation shows
    Pn = np.asarray(res.coords, float)
    c0 = Pn.mean(0)
    A_ = np.zeros((3 * len(Pn), 6))
    for k_, p_ in enumerate(Pn - c0):
        A_[3 * k_:3 * k_ + 3, :3] = np.eye(3)
        A_[3 * k_:3 * k_ + 3, 3:] = np.array([[0, p_[2], -p_[1]], [-p_[2], 0, p_[0]], [p_[1], -p_[0], 0]])
    sol = np.linalg.lstsq(A_, U.ravel(), rcond=None)[0]
    U = U - (A_ @ sol).reshape(-1, 3)
    util = {mm["id"]: req / mm["sf"] if mm["sf"] > 0 else 0 for mm in res.members}
    sc = 10.0
    fig, axs = plt.subplots(1, 2, figsize=(10, 7.4))
    cmap = matplotlib.colormaps["plasma"]
    for ax, (i, j, lab) in zip(axs, ((0, 2, "rear view (x-z)"), (1, 2, "side view (y-z), aft to the right"))):
        for md in m["members"]:
            if md["group"] == "lumbar_plate_shear":
                continue
            a, b = md["nodes"]
            p0, p1 = np.array(m["nodes"][a]), np.array(m["nodes"][b])
            ax.plot([p0[i], p1[i]], [p0[j], p1[j]], color="#cccccc", lw=1.0, zorder=1)
            d0, d1 = p0 + sc * U[idx[a]], p1 + sc * U[idx[b]]
            u = util.get(md["id"], 0.0)
            lw = 3.2 if not md["group"].startswith("lumbar") else 1.2
            if md["group"] == "lug_neck":
                lw = 6
            ax.plot([d0[i], d1[i]], [d0[j], d1[j]], color=cmap(min(u, 1.0)), lw=lw, zorder=2,
                    solid_capstyle="round")
        for n in ("SL0", "SR0", "SL330", "SR330", "SL520", "SR520", "SL530", "SR530", "HP"):
            p = np.array(m["nodes"][n]) + sc * U[idx[n]]
            ax.plot(p[i], p[j], "o", ms=9, mfc="#c9772c", mec="black", mew=0.6, zorder=3)
        ax.set_aspect("equal")
        ax.set_title(lab, fontsize=10)
        ax.grid(alpha=0.2)
        ax.set_xlabel("mm")
    sm = cm.ScalarMappable(cmap=cmap, norm=matplotlib.colors.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=axs, shrink=0.6, location="bottom", pad=0.08)
    cb.set_label("utilisation = factored stress / allowable (1 = limit), C5 meat 2.0 g x 1.5")
    fig.suptitle(f"{best} at 19 in, C5 meat case (rev C, CG 190 mm): elastic deformation x {sc:g} (rigid motion removed), orange = printed knuckles",
                 fontsize=10.5)
    return _save(fig, 3)


# ----------------------------------------------------------------------------- docs
BUILD_STEPS = {
    "common": [
        "Order tubes cut to length (stays, bars; crown tubes as today). Sand every bond zone 120 grit, wipe with IPA.",
        "Print the knuckles, foot nodes, collars, clips and hip node flat in PAHT-CF (dried 80 C 8-12 h), 6 walls, "
        "40 % gyroid; anneal per the TDS. Sand the sockets; flame-treat (quick pass of a propane torch) just before "
        "bonding (ASSUMPTION for the 4.0 MPa design value; T6 coupons check it).",
        "Make the T6 coupons from offcuts first (3 x each socket type), pull them to failure; do not bond the frame "
        "until the mean is >= 1.5 x the largest limit end force (load_standard.md T6).",
        "Print the bonding jig: a flat plywood board with printed V-cradles at the stay feet, z 330, z 520 and the "
        "stay tops, holding the stays parallel at x +/-115 and the knuckle axes square (jig files to follow).",
        "Dry-fit the whole ladder in the jig. Butter tube and socket with MMA (glass beads 0.5 mm), push in with a "
        "twist, wipe the fillet. No injection ports (patent design-around, research section 4). Cure 24 h.",
        "Bond the formed CF lumbar pan to the stays (as the v2 frame) and the hip node flange to the pan; heat-set the "
        "4 x M5 inserts in the hip node before bonding; fit the Ti mount.",
        "Fit the crown (legs into the stays on the UHMWPE bushings), rack, pawl and pulley exactly as today.",
    ],
    "wrap": [
        "TENDON wraps: 3 plies of 3k twill per joint (0/90, +-45, 0/90), cut as tapered fingers, wet out with "
        "laminating epoxy, laid from the knuckle 30 mm onto each tube (40 mm each side of the through-hubs), "
        "peel ply + shrink tape, cure, 65 C post-cure. The knuckle is the former: no foam, no mould.",
        "Light scuff and a satin clear coat over the wraps; the printed knuckle body stays visible between the "
        "fingers.",
    ],
    "skin": ["Print the skin panels (about 12, split at the knuckles), snap them over the tubes on printed ribs; "
             "no bond, removable for inspection."],
}


def concept_yaml(ctx) -> Path:
    import yaml
    out = {"schema": "huntkit.frame_light2/v1", "date": ctx["date"], "standard": ctx["standard"],
           "source": "huntkit/gendesign/frame_light2.py; designs/pack_5200/analysis/frame_light2.md",
           "printed_bond_design_mpa": L.TAU_PA_MPA, "concepts": {}}
    for k in ORDER:
        c = ctx["concepts"][k]
        cand = c["cand"]
        out["concepts"][k] = {
            "label": c["label"], "look": c["look"], "joint_mode": cand["joint_mode"],
            "stay": "OD %g %s k%d" % tuple(cand["stay"]), "mid_bar": "OD %g %s k%d" % tuple(cand["bar"]),
            "upper_bar": "OD %g %s k%d" % tuple(cand["ubar"]), "lumbar_pan_t_mm": cand["pan_t"],
            "branch": ("OD %g %s k%d" % tuple(cand["branch"]["sec"])) if cand.get("branch") else None,
            "skin_t_mm": cand.get("skin_t") or None,
            "frame_g": round(c["mass"]["frame_g"], 1), "frame_spreader_g": round(c["mass"]["frame_spreader_g"], 1),
            "mass_groups_g": {g: round(v, 1) for g, v in c["mass"]["groups"].items()},
            "min_strength_margin": round(c["summary"]["min_strength"][0], 3),
            "governing": f"{c['summary']['min_strength'][1]} @ {c['summary']['min_strength'][2]}",
            "min_fatigue_margin": round(c["summary"]["min_fatigue"][0], 3),
            "passes_rev_c": bool(c["summary"]["pass"]),
            "print_h": round(c["print_h"], 1), "cost_usd": round(c["cost"]["total"]),
            "printed_parts": c["n_printed_parts"],
            "stiffness": {k2: round(v, 2) for k2, v in c["stiffness"].items()},
            "pack_g": round(c["pack_g"]),
            "nodes": [{"name": n["name"], "qty": n["qty"], "g_each": round(n["g_each"], 1),
                       "wrap_g_each": round(n.get("wrap_g", 0.0), 1), "bond_g_each": round(n["bond_g"], 2)}
                      for n in c["mass"]["nodes"]],
        }
    L.CONCEPT_DIR.mkdir(parents=True, exist_ok=True)
    p = L.CONCEPT_DIR / "concepts.yaml"
    p.write_text("# Generated by huntkit/gendesign/frame_light2_report.py: do not hand-edit.\n"
                 + yaml.safe_dump(out, sort_keys=False, width=110))
    return p


def _f(v, n=2):
    return "n/a" if v is None else f"{v:.{n}f}"


def _lb(g):
    return g / 453.592


def recommend(ctx) -> str:
    ok = [k for k in ORDER if ctx["concepts"][k]["summary"]["pass"] and k != "SKIN"]
    return min(ok, key=lambda k: ctx["concepts"][k]["mass"]["frame_g"]) if ok else "TENDON"


def write_doc(ctx, shots: list[str]) -> Path:
    C = ctx["concepts"]
    best = recommend(ctx)
    b = C[best]
    lines = []
    A = lines.append
    A("# Lighter frame study 2: printed knuckles on carbon tubes (HA-LS-1 rev C)")
    A("")
    A("Owner: structural-fea-engineer, 2026-11-09. Owner approval: DECISIONS 2026-11-09 \"Owner: 'Yes' to the "
      "weight-pass recommendation\" item 4. Research: [light_frame_architectures.md]"
      "(../../../docs/research/light_frame_architectures.md). Code: `huntkit/gendesign/frame_light2.py` "
      "(+ `frame_light2_report.py`, `frame_light2_render.py`). Concepts: "
      "[`designs/pack_5200/frame_light2/concepts.yaml`](../frame_light2/concepts.yaml). Results: "
      "[`frame_light2_results.json`](../frame_light2/frame_light2_results.json). Tests: `tests/test_frame_light2.py`.")
    A("")
    A("```")
    A("python -m huntkit.gendesign.frame_light2        # sizing + all rev C checks, about 10 min on 4 cores")
    A("```")
    A("")
    A("## Summary")
    A("")
    pk = b["pack_g"]
    A(f"- **Recommendation: {best}** ({b['label'].split(': ')[1]}). Frame **{b['mass']['frame_g']:.0f} g**, frame + "
      f"spreader **{b['mass']['frame_spreader_g']:.0f} g** (today 1063 / 1225 g: "
      f"**-{L.TODAY['frame_g'] - b['mass']['frame_g']:.0f} g**). Every rev C check passes: worst strength margin "
      f"**{b['summary']['min_strength'][0]:.2f}** ({b['summary']['min_strength'][1]}), worst fatigue margin "
      f"**{b['summary']['min_fatigue'][0]:.2f}** ({b['summary']['min_fatigue'][1]}).")
    A(f"- **Achievable pack: about {pk:.0f} g ({_lb(pk):.2f} lb)** for CORRIE with every feature (weight pass A+B+C "
      f"3779 g with today's frame, minus the frame saving). **6.6 lb (2994 g) is not reachable** with these "
      f"interfaces: frame + spreader would have to be 440 g, and the parts that no concept touches already weigh "
      f"{sum(L.CROWN.values()) + sum(L.PIVOT.values()) + L.TODAY['spreader_g']:.0f} g (carbon crown, rack and pawl, "
      f"bushings, Ti pivot mount and inserts, Sandwich v2 spreader). With the stays, bars, pan and nodes on top, about "
      f"{b['mass']['frame_spreader_g']:.0f} g is the floor of this architecture.")
    n = C["NODE"]
    A(f"- **Tubes bonded straight into printed sockets (NODE) fail rev C**: the bond to printed polyamide is "
      f"weak (published 3.7-5.0 MPa, interface failure) and the soft socket concentrates shear at the lip. "
      f"Worst margin **{n['summary']['min_strength'][0]:.2f}** ({n['summary']['min_strength'][1]}, "
      f"{n['summary']['min_strength'][2]}). Every load-carrying product found (Robot Bike Co, Bastion, Burton) uses "
      f"metal lugs for this reason. The fix that keeps the printed look is TENDON: the print is the visible knuckle "
      f"and the former, and a carbon wrap carries the joint load, as on the v2 frame.")
    A("- **Owner decisions:** pick a concept (NODE is not offered: it fails); accept a stiffer frame than today's; "
      "approve the T6 coupon programme for the printed-knuckle bonds before any frame is bonded; and choose whether "
      "the published 6.6 lb target moves (summary, second bullet).")
    br = C["BRANCH"]
    A(f"- **BRANCH (the lattice look) fails frame buckling ({br['summary']['min_strength'][0]:.2f}, "
      f"{br['summary']['min_strength'][2]})** even with OD 18 branch tubes, and costs "
      f"+{br['mass']['frame_g'] - b['mass']['frame_g']:.0f} g over {best}: the branches push on the thin formed pan, "
      "and in-plane bracing does nothing for the out-of-plane bag loads (generative_design.md section 3 found the "
      "same). **SKIN** passes (it is TENDON underneath) and looks exactly like today's frame, for "
      f"+{C['SKIN']['mass']['frame_g'] - b['mass']['frame_g']:.0f} g: frame {C['SKIN']['mass']['frame_g']:.0f} g, "
      f"still {L.TODAY['frame_g'] - C['SKIN']['mass']['frame_g']:.0f} g under today.")
    A("- **Finding on today's frame (P-1):** the accessory extension-post socket at the crown corner has a Volkersen "
      "peak margin of **0.96** in C6p (posts fitted) with its 0.5 mm bondline, on today's frame too "
      "(`rev_c_verification_results.json` post_socket 0.957; the rev C summary table did not list this check). Giving "
      "it the crown corners' 0.8 mm bondline (glass beads) lifts it to 1.20 here. Applied in every concept; proposed "
      "for today's crown as well (no mass change).")
    t24 = 3779.0 - 462.3 - 3100.0
    A(f"- With the weight pass's accounting items T-2..T-4 as well (pouch as an accessory and the rest, about "
      f"{t24:.0f} g), the pack would be about **{pk - t24:.0f} g ({_lb(pk - t24):.2f} lb)**.")
    A("")
    A("## 1. Concepts")
    A("")
    A("All four keep the v2 tube topology the beam model already knows: two straight OD 20 stays with the carbon crown "
      "legs telescoping inside, mid bar z 330, upper bar z 520 (pawl), formed CF lumbar pan (the lumbar-pad seat, "
      "hipbelt decision 2026-11-09), Ti pivot mount on 4 x M5 inserts in a printed hip node, the carbon crown with "
      "the rev C fix, and the Sandwich v2 spreader. Every interface keeps its place (section 6).")
    A("")
    A("| concept | look | joints | stays / mid bar / upper bar / pan | frame g | frame + spreader g | worst strength | worst fatigue | pass |")
    A("|---|---|---|---|---:|---:|---:|---:|---|")
    for k in ORDER:
        c = C[k]
        cd = c["cand"]
        secs = "OD %g %s k%d" % tuple(cd["stay"]) + " / " + "OD %g %s k%d" % tuple(cd["bar"]) + " / " + \
            "OD %g %s k%d" % tuple(cd["ubar"]) + f" / {cd['pan_t']:g} mm"
        if cd.get("branch"):
            secs += " + branch OD %g %s k%d" % tuple(cd["branch"]["sec"])
        A(f"| **{k}** | {c['look']} | {'tube in printed socket' if cd['joint_mode'] == 'printed' else 'printed knuckle + carbon tendon wrap'} "
          f"| {secs} | {c['mass']['frame_g']:.0f} | {c['mass']['frame_spreader_g']:.0f} | "
          f"{c['summary']['min_strength'][0]:.2f} | {c['summary']['min_fatigue'][0]:.2f} | "
          f"{'yes' if c['summary']['pass'] else '**no**'} |")
    A(f"| today | printed PAHT-CF branch body + carbon crown | | | {L.TODAY['frame_g']:.0f} | "
      f"{L.TODAY['frame_spreader_g']:.0f} | 1.12 (crown legs, IM3; rev_c_verification) | 1.04 (printed body) | "
      f"yes (post socket 0.96, P-1) |")
    A("")
    A("Layup codes: RW0 = twill 0/90 + UD 0 core x k + twill; RW45 = +-45 twill wraps (huntkit.fea.sizing). SKIN has "
      "the TENDON structure; its skin is not credited, so its margins are TENDON's.")
    A("")
    A("## 2. Mass, by part group (g)")
    A("")
    groups = list(b["mass"]["groups"])
    A("| group | " + " | ".join(ORDER) + " |")
    A("|---|" + "---:|" * len(ORDER))
    for g in groups:
        A(f"| {g} | " + " | ".join(f"{C[k]['mass']['groups'].get(g, 0.0):.1f}" for k in ORDER) + " |")
    A("| **frame** | " + " | ".join(f"**{C[k]['mass']['frame_g']:.1f}**" for k in ORDER) + " |")
    A(f"| spreader (Sandwich v2, unchanged) | " + " | ".join(f"{L.TODAY['spreader_g']:.1f}" for _ in ORDER) + " |")
    A("| **frame + spreader** | " + " | ".join(f"**{C[k]['mass']['frame_spreader_g']:.1f}**" for k in ORDER) + " |")
    A("")
    A(f"Nodes of {best} (each):")
    A("")
    A("| part | qty | printed g | carbon wrap g | bond g |")
    A("|---|---:|---:|---:|---:|")
    for nd in b["mass"]["nodes"]:
        A(f"| {nd['name']} | {nd['qty']} | {nd['g_each']:.1f} | {nd.get('wrap_g', 0.0):.1f} | {nd['bond_g']:.2f} |")
    A("")
    A("Tubes: " + ", ".join(f"{k} {v:.1f} g" for k, v in b["mass"]["tubes"].items()) + ". Crown and torso adjust "
      "(unchanged): " + ", ".join(f"{k} {v:.1f}" for k, v in L.CROWN.items()) + ".")
    A("")
    A("## 3. Rev C strength, fatigue and joints")
    A("")
    A("Method: `huntkit.fea` beam model of each concept (`frame_light2.build`), every rev C case set from "
      "`ls1_envelope('C')` (9 cases with the bag couple on the crown bar, C6p on the posts model, plus the 5 bag cases "
      "with the couple on the IM3 hooks) at torso 15 / 19 / 23 in. Margin = SF / requirement, pass >= 1.00. The "
      "solver's closed-form verification is in `tests/` (cantilever, Euler, thin-wall torsion, Volkersen) and "
      "`tests/test_frame_light2.py` adds the checks below.")
    A("")
    A("Worst margin per check family:")
    A("")
    fam = {k: family_minima(C[k]["summary"]) for k in ORDER[:3]}
    A("| check | " + " | ".join(ORDER[:3]) + f" | where ({best}) |")
    A("|---|---:|---:|---:|---|")
    for _, lab in FAMILY:
        vals = [fam[k].get(lab) for k in ORDER[:3]]
        if all(v is None for v in vals):
            continue
        wb = fam[best].get(lab) if best in fam else None
        A(f"| {lab} | " + " | ".join(_f(v[0]) if v else "-" for v in vals) + " | "
          + (f"{wb[1]} @ {wb[2]}" if wb else "") + " |")
    A("")
    A(f"{best} by case (worst of torso, couple variant and every check):")
    A("")
    A("| case | worst margin | torso |")
    A("|---|---:|---:|")
    for k, (v, t) in sorted(b["summary"]["by_case"].items(), key=lambda kv: kv[1][0]):
        A(f"| {k.replace('|crown_bar', ' (couple on the crown bar)').replace('|strap_upper', ' (couple on IM3)')} | "
          f"{v:.2f} | {t:g} |")
    A("")
    A("Every check of " + best + ", sorted:")
    A("")
    A("| check | margin | where |")
    A("|---|---:|---|")
    for k, (v, where) in sorted(b["summary"]["checks"].items(), key=lambda kv: kv[1][0]):
        A(f"| {k} | {v:.2f} | {where} |" if v < 100 else f"| {k} | > 100 | {where} |")
    A("")
    A("Joint checks, how:")
    A("")
    A(f"- **Printed sockets (NODE)**: `huntkit.fea.joints.bond_check` with the printed wall as the outer adherend "
      f"(E t = 3860 MPa x {L.LUG['t']} mm), MMA G 300 MPa, 0.5 mm bondline, double lap at bar ends (printed spigot: "
      f"bond perimeter OD + ID). Allowable **{L.TAU_PA_MPA:.1f} MPa** (published 5.0 MPa dry PA12 x 0.8 hot/wet). The "
      f"node itself is a PAHT 'neck' member in the beam model (socket annulus, tube not credited) checked at 0.8 x 88 "
      f"MPa.")
    A("- **Carbon tendons (TENDON, BRANCH, SKIN)**: the v2 frame's carbon wrap joint (frame.yaml `joint`: 0.75 mm "
      "QI wrap, 30 mm on each tube, 40 mm through, MMA on CFRP 20 MPa x 0.8). The printed knuckle under it is the "
      "former; it is not credited.")
    A("- **Foot boot**: PAHT annulus at the boot mouth, ground lateral force x 40 mm + axial, 0.8 x 88 MPa.")
    A("- **Stay-top collar**: top bushing ring moment (120 deg land, `huntkit.fea.rings`) shared by the stay wall and a "
      "3 mm printed collar by E t^3; the collar hoop at the Z allowable 0.8 x 47 MPa; the stay by first-ply failure.")
    A("- **Hip node**: Ti mount on 4 x M5 heat-set inserts (pull-out 1500 N ASSUMPTION, as hipbelt_structural.md; "
      "pull-out test pending), pivot reaction + its moment over a 22 mm stand-off; printed flange 70 x 60 mm bonded "
      "to the pan at 4.0 MPa (flatwise stress read against lap shear: conservative).")
    A("- **Stay clips** (z 80 / 110 / 190 / 250 / 420 hard points): external load at the node on a 22 mm wide printed "
      "collar bond at 4.0 MPa.")
    A("- **Fatigue** (1e5 cycles at 0 -> 1.6 g x 68 kg, from the C1 static-carry solve): CFRP FI <= 0.5; PAHT <= 0.3 x "
      "the knocked-down strength; bonds <= 0.3 x dry lap shear; inserts 0.5 x pull-out (ASSUMPTION).")
    A("")
    A("## 4. Stiffness and load transfer")
    A("")
    A("Same two tests as `frame_topopt.tube_frame_stiffness` (hip pivot clamped; rev B static-carry load set for the "
      "carry deflection; +-100 N fore-aft at the stay tops for torsion), torso 19 in.")
    A("")
    A("| frame | stay-top aft deflection, static carry (mm) | torsion (N m/deg) | hip share, static carry |")
    A("|---|---:|---:|---:|")
    A(f"| today, printed branch body (production_frame_results.json, 4 mm voxels) | {L.TODAY['carry_dy_mm']:.1f} | "
      f"{L.TODAY['torsion_Nm_per_deg']:.2f} | 0.80 (same spring model) |")
    A(f"| v2 wrapped tube ladder (rejected look) | {L.V2_TUBE['carry_dy_mm']:.1f} | {L.V2_TUBE['torsion_Nm_per_deg']:.2f} | |")
    for k in ORDER:
        c = C[k]
        A(f"| {k} | {abs(c['stiffness']['carry_dy_mm']):.1f} | {c['stiffness']['torsion_Nm_per_deg']:.2f} | "
          f"{_f(c['summary'].get('hip_fraction_static'))} |")
    A("")
    A(f"Every tube concept is several times stiffer than today's printed body (torsion about "
      f"{b['stiffness']['torsion_Nm_per_deg'] / L.TODAY['torsion_Nm_per_deg']:.0f}x). Today's body was accepted at "
      f"0.15 of the tube frame's torsion (production_frame.md); the light frames go back to the tube frame's feel. The "
      f"hip/shoulder split is set by the hipbelt and harness springs, not the frame (80 % hips in every model): a "
      f"stiffer frame keeps the bag from swaying, it does not move load off the hips. The load lifters see less "
      f"crown sag. ASSUMPTION: PAHT at 40 C is not a stiffness issue here, because the knuckles are short; the tubes "
      f"carry the bending.")
    A("")
    A("## 5. Centre of gravity")
    A("")
    A("| frame | frame CG y (aft) mm | frame CG z mm | loaded-pack CG shift vs today (68 kg at 205 mm, z 550) |")
    A("|---|---:|---:|---|")
    A(f"| today (printed body centroid + crown) | {b['cg']['today_cg'][1]:.0f} | {b['cg']['today_cg'][2]:.0f} | |")
    for k in ORDER:
        c = C[k]
        sc = c["system_cg"]
        A(f"| {k} | {c['cg']['cg'][1]:.0f} | {c['cg']['cg'][2]:.0f} | {sc['dy_mm']:+.1f} mm aft, "
          f"{sc['dz_mm']:+.1f} mm up |")
    A("")
    A("The frame is about 1 % of the loaded mass, so its CG moves the loaded-pack CG by under 2 mm: no effect on the "
      "rev C load cases (bag 205 mm, meat 190 mm are content CGs). Empty, the lighter frame is less top-heavy than "
      "today's, because the printed body's mass was mostly in the stays and lumbar struts.")
    A("")
    A("## 6. Interfaces kept")
    A("")
    A("| interface | today | in the tube concepts |")
    A("|---|---|---|")
    A("| crown, top bar, lifters (US 10,952,523 guardrail) | carbon crown in printed sleeves | unchanged crown; legs "
      "telescope inside the carbon stays on the same UHMWPE bushings (v2); lifters stay on the crown top bar |")
    A("| torso adjust (rack + pawl + 3:1 pulley) | pawl housing on the printed upper bar | pawl housing printed on the "
      "upper carbon bar centre (as v2), rack on the spine unchanged |")
    A("| hipbelt B Ti pivot, 4 x M5 inserts | printed boss | printed hip node bonded to the pan; same 4 x M5 pattern |")
    A("| lumbar-pad seat | lumbar pan of the printed body | formed CF pan (v2), the pad bears on it |")
    A("| hinge pins z 60 (bag_anchor_low), under-strap pins US1/US2 | printed foot region | foot node bosses |")
    A("| IM1 z 190 / IM2 z 330 / IM3 z 520 fairleads, B-24 float-link eyes | printed body | IM1: stay clip; IM2, IM3 "
      "and B-24: knuckle seats (fairleads unchanged parts) |")
    A("| wing lash z 80 / 250 / 420, shoulder-strap lower anchor z 110, hip stabiliser z 60 | printed body | stay "
      "clips and foot node |")
    A("| hood, B-22 guys | crown | crown (unchanged) |")
    A("| spreader (Sandwich v2) | clips on the printed stays | clips on the carbon stays at the same x/z (ASSUMPTION: same "
      "support line, comfort result unchanged; re-run `spreader.evaluate` on the tube supports before release) |")
    A("")
    A("## 7. Print time, cost, build, patents")
    A("")
    A("| concept | printed parts | printed g | print h (H2S, 8 mm3/s) | material cost USD |")
    A("|---|---:|---:|---:|---:|")
    for k in ORDER:
        c = C[k]
        A(f"| {k} | {c['n_printed_parts']} | {c['mass']['printed_g']:.0f} | {c['print_h']:.1f} | "
          f"{c['cost']['total']:.0f} |")
    A("| today | 2 body halves + small parts | 823 | about 27 (generative_branch.md) | about 208 |")
    A("")
    A(f"{best} cost lines: " + "; ".join(f"{k} ${v:.0f}" for k, v in b["cost"]["lines"].items()) + ".")
    A("")
    A("Build steps (" + best + "):")
    A("")
    steps = BUILD_STEPS["common"] + (BUILD_STEPS["wrap"] if b["cand"]["joint_mode"] == "wrap" else [])
    for i, s in enumerate(steps, 1):
        A(f"{i}. {s}")
    A("")
    A("Patents (research section 4, not legal advice): the knuckles have **no adhesive injection ports or internal "
      "channels** (Divergent US 10,668,965 design-around); TENDON has no inner spigot (Divergent node/tube "
      "engagement family); crown and lifters unchanged (Mystery Ranch US 10,952,523 guardrail); a multi-part tube "
      "frame is outside KUIU's one-piece frame patents. Freedom-to-operate opinion before tooling.")
    A("")
    A("## 8. Mass reductions that keep the margins (not applied)")
    A("")
    tried = [t for t in b["tried"]]
    if tried:
        A("Greedy downsizing log (each step re-runs every rev C check at 15 / 19 / 23 in):")
        A("")
        A("| step | worst strength | worst fatigue | kept |")
        A("|---|---:|---:|---|")
        prev = None
        for t in tried:
            cd = t["cand"]
            lab = "v2 sections" if prev is None else ", ".join(
                f"{key} {cd[key] if not isinstance(cd[key], (list, tuple)) else 'OD %g %s k%d' % tuple(cd[key])}"
                for key in ("stay", "bar", "ubar", "pan_t") if cd[key] != prev[key]) or "(same)"
            A(f"| {lab} | {t['min_strength'][0]:.2f} ({t['min_strength'][1]}) | {t['min_fatigue'][0]:.2f} | "
              f"{'yes' if t['pass'] else 'no'} |")
            if t["pass"] or prev is None:
                prev = cd
        A("")
    A("- The crown (legs, top bar, spine, corner wraps, rack, bushings) is now the biggest single block. A lighter "
      "crown needs a new torso-adjust concept: out of scope here, and the rev C crown margins (legs 1.12-1.14) leave "
      "nothing to cut.")
    A("- The spreader (162 g) is set by the 14 kPa comfort limit with the 190 mm meat CG (rev_c_verification.md: 13.83 "
      "kPa). It does not get thinner.")
    A("- Printed clips: folding the z 250 / 420 lash points into webbing loops around the stays saves about 15 g; the "
      "owner's pack-designer would need to accept it.")
    A("")
    A("## 9. Assumptions")
    A("")
    for a in (
        f"ASSUMPTION: MMA on sanded, flame-treated PAHT-CF reaches 5.0 MPa dry (best published PA12 value), "
        f"{L.TAU_PA_MPA:.1f} MPa hot/wet. T6 coupons decide it.",
        "ASSUMPTION: the printed node neck is the socket annulus over 12 mm, tube not credited; real knuckles are "
        "filleted and thicker there (conservative).",
        "ASSUMPTION: generative root fingers and fillets add 30 % to each socket's printed volume; node features "
        "(fairlead seats, hinge-pin bosses, eyes) 2-6 g each.",
        "ASSUMPTION: TENDON wraps cover 60 % of the knuckle surface plus 30 / 40 mm on each tube with an 8 mm ply "
        "drop; the knuckle is not credited structurally.",
        "ASSUMPTION: M5 heat-set insert pull-out 1500 N in PAHT-CF (as hipbelt_structural.md); test pending.",
        "ASSUMPTION: the spreader keeps today's mass and comfort result on the tube supports.",
        "ASSUMPTION: tube price $30/m at 16 mm scaled with OD (cfrp_rollwrapped_tube record); print 8 mm3/s + 8 % "
        "waste + 0.15 h per part.",
        "ASSUMPTION: the CG comparison puts today's crown and hardware at z 560 and uses the printed body's STL "
        "centroid at uniform density.",
        "The PAHT fatigue ratio 0.3 and the creep values are the material record's study assumptions (no measured "
        "S-N curve for printed PAHT-CF).",
    ):
        A(f"- {a}")
    A("")
    A("## 10. Tests before release (HA-LS-1 section 5, added here)")
    A("")
    A("- **T6p printed-knuckle coupons**: 3 x each knuckle (foot, mid, upper, stay-top collar, hip node flange) bonded "
      "to tube offcuts exactly as the frame; pull to failure. For TENDON, also 3 x a wrapped knuckle. Pass as T6.")
    A("- **T6f fatigue coupon**: one wrapped mid knuckle cycled 0 -> 1.6 g end force for 1e5 cycles on the T5 rig.")
    A("- Then the frame tests T1-T5, T9 as written.")
    A("")
    A("## Screenshots")
    A("")
    for s in shots:
        A(f"- `{Path(s).relative_to(L.REPO_ROOT) if str(s).startswith(str(L.REPO_ROOT)) else s}`")
    A("")
    p = L.ANALYSIS / "frame_light2.md"
    p.write_text("\n".join(lines) + "\n")
    return p


def write_all(ctx, render: bool = True) -> dict:
    shots = [plot_mass(ctx), plot_utilization(ctx, recommend(ctx)), plot_deformed(ctx, recommend(ctx))]
    if not render:
        shots += [str(p) for p in sorted(L.SCREENS.glob(f"{L.SHOT}_[4-6].png"))]
    if render:
        try:
            from .frame_light2_render import render_all
            shots += render_all(ctx)
        except Exception as e:      # pragma: no cover - Blender is optional
            print("render skipped:", e)
    y = concept_yaml(ctx)
    d = write_doc(ctx, shots)
    return {"shots": shots, "yaml": str(y), "doc": str(d)}


def docs_only(render: bool = False) -> dict:
    ctx = json.loads(L.RESULTS.read_text())
    return write_all(ctx, render=render)
