"""Screenshots for frame_cg_recheck.md: utilization at the worst offset, and SF vs CG offset."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from .frame_cg_recheck import CODE, SCREENS

# reference palette (dataviz skill references/palette.md), categorical slots in fixed order
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("blue_seq", ["#e8f1fc", "#9cc3f0", "#2a78d6", "#0d3f7f"])
CRIT = "#e34948"


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=10)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def plot_sf_vs_offset(ctx, path: Path, offsets=(150, 180, 205, 223, 250)) -> str:
    names = {"static_carry": "C1 static", "drop_2p5g": "C2 stumble", "side_hill_torsion": "C3 side-hill",
             "single_stay_setdown": "C4 set-down", "hipbelt_off_abuse": "C8 hipbelt off", "meat_straps": "C5 meat",
             "tall_load": "C6 tall", "tall_load_posts": "C6p posts", "overload_haul": "C7 overload"}
    body = lambda c: [ctx["body"][f"s{e:g}"]["cases"][c]["sf"] for e in offsets]
    crown = lambda k: [ctx["crown"][f"s{e:g}"][k]["sf"] for e in offsets]
    panels = [
        ("Printed body: bag-carry cases", [(names[c], body(c)) for c in
          ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "hipbelt_off_abuse")]),
        ("Printed body: meat and tall loads", [(names[c], body(c)) for c in
          ("meat_straps", "tall_load", "tall_load_posts", "overload_haul")]),
        ("Carbon crown as built (beam model)", [("spine", crown("crown_spine")), ("legs", crown("crown_leg")),
                                                 ("top bar", crown("crown_top_bar")),
                                                 ("corner bond peak", crown("corner_bond_peak"))]),
    ]
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.6), dpi=90, sharey=True, facecolor=SURF)
    for ax, (title, series) in zip(axs, panels):
        _style(ax)
        for e, lab in ((150, "rev B meat"), (180, "rev B bag"), (205, "envelope"), (223, "as-is")):
            ax.axvline(e, color=GRID, lw=1, zorder=0)
            ax.text(e, 3.75, lab, rotation=90, fontsize=8, color=INK2, ha="right", va="top")
        handles = []
        for i, (lab, y) in enumerate(series):
            h, = ax.plot(offsets, y, color=SERIES[i], lw=2, marker="o", ms=6, mec=SURF, mew=1.5, label=lab)
            handles.append(h)
            ax.annotate(lab, (offsets[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=9, color=INK2)
        ax.axhline(1.0, color=CRIT, lw=1.2, ls="--")
        ax.set_title(title, color=INK, fontsize=12, loc="left")
        ax.set_xlabel("load CG aft of frame axis, mm", color=INK2, fontsize=10)
        ax.set_xlim(offsets[0] - 5, offsets[-1] + 60)
        ax.set_ylim(0.6, 3.8)
        ax.legend(handles=handles, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.14),
                  ncol=3, labelcolor=INK2)
    axs[0].text(152, 0.93, "pass line: SF / required = 1.0", color=INK2, fontsize=9, va="top")
    axs[0].set_ylabel("margin = SF / required (worst torso)", color=INK2, fontsize=10)
    fig.suptitle("Production frame vs load CG offset (every case at the offset, CG z 550). "
                 "The printed body passes; the crown as built does not past about 200 mm", color=INK, fontsize=12,
                 x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)
    return str(path)


def plot_utilization(ctx, tag: str, path: Path, title: str) -> str:
    """Envelope of the element failure index over every case and torso of scenario ``tag``, divided by the
    case factor already in the load (FI on the factored load: 1.0 = at the allowable)."""
    fi = ctx["_env"][tag]
    c = ctx["_centers"]
    show = fi > 0.05
    order = np.argsort(fi[show])
    cs, f = c[show][order], fi[show][order]
    fig, axs = plt.subplots(1, 2, figsize=(10, 7.5), dpi=100, facecolor=SURF,
                            gridspec_kw={"width_ratios": [3.2, 1.3]})
    vmax = max(1.0, float(np.percentile(f, 99.9)))
    for ax, (i, j, lab) in zip(axs, ((0, 2, "front view (x, z) mm"), (1, 2, "side view (y, z) mm, + y = toward bag"))):
        ax.set_facecolor(SURF)
        sc = ax.scatter(cs[:, i], cs[:, j], c=np.minimum(f, vmax), cmap=SEQ, vmin=0, vmax=vmax, s=3, lw=0)
        hot = f >= 1.0
        if hot.any():
            ax.scatter(cs[hot, i], cs[hot, j], c=CRIT, s=6, lw=0)
        ax.set_aspect("equal")
        ax.set_xlabel(lab, color=INK2, fontsize=10)
        ax.tick_params(colors=INK2, labelsize=9)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    gov = ctx["body"][tag]
    gx = gov["cases"][gov["governing"].split("|")[0]]["peak_xyz"]
    axs[0].scatter([gx[0]], [gx[2]], s=180, facecolors="none", edgecolors=INK, lw=1.5)
    axs[0].annotate(f"governing: {gov['governing']} in\n{gov['where']}\nmargin {gov['sf_min']:.2f}",
                    (gx[0], gx[2]), xytext=(15, -40), textcoords="offset points", fontsize=9, color=INK,
                    arrowprops={"arrowstyle": "-", "color": INK2})
    cb = fig.colorbar(sc, ax=axs, fraction=0.03, pad=0.02)
    cb.set_label("failure index on the factored load (envelope of all cases and torsos)\nred = single elements over 1.0, above the FI99 rule (load-patch / strut-end peaks)",
                 color=INK2, fontsize=9)
    cb.ax.tick_params(colors=INK2, labelsize=9)
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, ha="left")
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)
    return str(path)


def write_screens(ctx, date="20261105") -> list[str]:
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = [plot_utilization(ctx, "c", SCREENS / f"{date}_cgrecheck_1.png",
                            "Utilization at the worst offset: bag as-is 223 mm on every case (CG z 550), printed branch body"),
           plot_sf_vs_offset(ctx, SCREENS / f"{date}_cgrecheck_2.png"),
           plot_utilization(ctx, "b", SCREENS / f"{date}_cgrecheck_3.png",
                            "Utilization at the cloth-sim envelope (bag 205 mm @ z 550, meat 175, tall 185)")]
    return out
