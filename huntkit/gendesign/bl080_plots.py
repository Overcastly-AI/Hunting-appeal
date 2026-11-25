"""BL-080 concept sheet and cost / mass bars (phone-readable PNGs) from ``iter2/frame_concepts.json``.

Run: ``python -m huntkit.gendesign.bl080_plots`` (after ``bl080_metal_frame run``).
Colours (validated categorical slots 1-3, dataviz reference palette): metal blue, printed PAHT orange, carried-over
crown grey; every mark is also labelled in text (contrast WARN on orange / aqua obliges direct labels).
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from .bl080_metal_frame import H1, H1C, CAP_USD, REC_JSON, SCREENS, SHOT, STOCK  # noqa: E402

METAL, PRINT, CROWN, OK, BAD = "#257de0", "#f47230", "#9c9c9c", "#0aac23", "#ec4647"
INK, INK2, GRID = "#191919", "#666666", "#e6e6e6"
Z_TOP = 702.6          # crown top at 19 in (geometry.yaml crown_settings)
LEG_BOT = Z_TOP - 430.0


def _w(key):           # stay drawn width (mm, true scale)
    s = STOCK[key]
    return s.get("od") or s["w"]


def _front(ax, k, e):
    sw = _w(e["stay"])
    flat = e["stay"].startswith("f")
    # crown (carry-over)
    for x in (-115, 115):
        ax.add_patch(Rectangle((x - 8, LEG_BOT), 16, Z_TOP - LEG_BOT, color=CROWN, alpha=0.55, lw=0))
    ax.add_patch(Rectangle((-115, Z_TOP - 9), 230, 18, color=CROWN, alpha=0.55, lw=0))
    ax.add_patch(Rectangle((-10, Z_TOP - 300), 20, 300, color=CROWN, alpha=0.35, lw=0))
    # stays
    for x in (-115, 115):
        ax.add_patch(Rectangle((x - sw / 2, 0), sw, 530, color=METAL, lw=0, alpha=0.95))
        if flat:      # printed crown sleeves on the flat bars
            ax.add_patch(Rectangle((x + sw / 2, 330), 14, 200, color=PRINT, lw=0))
    # bars
    ub = STOCK[e.get("ubar") or "t750_035"]["od"]
    ax.add_patch(Rectangle((-115, 330 - 9.5), 230, 19.05, color=METAL, lw=0))
    ax.add_patch(Rectangle((-115, 520 - ub / 2), 230, ub, color=METAL, lw=0))
    # hub
    lum = e["lumbar"]
    if lum["kind"] == "paht":
        ax.add_patch(FancyBboxPatch((-125, 50), 250, 140, boxstyle="round,pad=0,rounding_size=30", color=PRINT, lw=0))
    elif lum["kind"] == "metal_pan":
        ax.add_patch(FancyBboxPatch((-125, 50), 250, 140, boxstyle="round,pad=0,rounding_size=30",
                                    fc="#cce3fd", ec=METAL, lw=3.0))
        for cx in (-62, 62):       # lightening cut-outs
            ax.add_patch(FancyBboxPatch((cx - 30, 85), 60, 70, boxstyle="round,pad=0,rounding_size=18",
                                        fc="white", ec=METAL, lw=1.2))
        if lum.get("padup"):
            ax.add_patch(Rectangle((-30, 50), 60, 140, fc=METAL, alpha=0.35, lw=0))
    else:
        ct = STOCK[lum["tube"]]["od"]
        ax.add_patch(Rectangle((-115, 120 - ct / 2), 230, ct, color=METAL, lw=0))
        ax.add_patch(Rectangle((-30, 95), 60, 50, fc="none", ec=METAL, lw=2))
    # Ti hip mount
    ax.add_patch(plt.Circle((0, 120), 25, color="#555555", lw=0))
    # printed nodes (tees, feet, pawl housing)
    if not flat:
        for x in (-115, 115):
            for zc, h in ((30, 60), (330, 36), (522, 40)):
                ax.add_patch(Rectangle((x - sw / 2 - 7, zc - h / 2), sw + 14, h, fc=PRINT, ec="white", lw=1))
            if lum["kind"] != "paht":
                ax.add_patch(Rectangle((x - sw / 2 - 5, 70), sw + 10, 100, fc=PRINT, ec="white", lw=1, alpha=0.9))
    else:
        for x in (-115, 115):
            for zc, h in ((330, 30), (520, 30)):
                ax.add_patch(Rectangle((x - sw / 2 - 6, zc - h / 2), sw + 12, h, fc=PRINT, ec="white", lw=1))
    ax.add_patch(Rectangle((-28, 505), 56, 34, fc=PRINT, ec="white", lw=1))
    ax.set_xlim(-165, 165)
    ax.set_ylim(-30, 760)
    ax.set_aspect("equal")
    ax.axis("off")


def _side(ax, e):
    flat = e["stay"].startswith("f")
    sw = 4.76 if flat else _w(e["stay"])
    ax.plot([0, -10], [0, 530], color=METAL, lw=max(2.0, sw / 3.2), solid_capstyle="butt")
    ax.plot([-10, -12], [LEG_BOT, Z_TOP], color=CROWN, lw=4, alpha=0.7)
    ax.plot([-12, 13], [Z_TOP, Z_TOP], color=CROWN, lw=4, alpha=0.7)
    lum = e["lumbar"]
    if lum["kind"] == "paht":
        ax.add_patch(Rectangle((-20 - lum["t"], 50), lum["t"] + 20, 140, color=PRINT, lw=0))
    elif lum["kind"] == "metal_pan":
        ax.plot([-2, -20, -20, -2], [50, 50, 190, 190], color=METAL, lw=2.2)
    else:
        ax.add_patch(plt.Circle((-2.5, 120), STOCK[lum["tube"]]["od"] / 2, color=METAL))
        ax.plot([-2.5, -45], [120, 120], color=METAL, lw=3)
    ax.add_patch(plt.Circle((-48, 120), 9, color="#555555"))
    ax.text(-60, 120, "hip\npivot", ha="right", va="center", fontsize=7, color=INK2)
    ax.text(30, 260, "bag\nside", ha="left", fontsize=7, color=INK2)
    ax.set_xlim(-110, 70)
    ax.set_ylim(-30, 760)
    ax.set_aspect("equal")
    ax.axis("off")


def concept_sheet(rec, png):
    import textwrap
    keys = list(rec["concepts"])
    fig = plt.figure(figsize=(12, 11), dpi=110)
    fig.patch.set_facecolor("white")
    fig.text(0.02, 0.975, "BL-080  Metal-stay frame concepts", fontsize=15, color=INK, fontweight="bold", va="top")
    fig.text(0.02, 0.948, "Front + side, true scale, crown at 19 in. Numbers: HA-LS-1 rev C first-order beam checks, "
             "body mass, materials per frame.", fontsize=9.5, color=INK2, va="top")
    pick = rec.get("pick")
    for i, k in enumerate(keys):
        e = rec["concepts"][k]
        col, row = i % 2, i // 2
        x0, y0 = 0.01 + col * 0.495, 0.50 - row * 0.44
        fig.text(x0 + 0.01, y0 + 0.415, e["name"], fontsize=11, color=INK, fontweight="bold", va="top")
        axf = fig.add_axes([x0, y0, 0.20, 0.38])
        axs = fig.add_axes([x0 + 0.19, y0, 0.07, 0.38])
        _front(axf, k, e)
        _side(axs, e)
        c = e["checks"]
        strong = e["strong_pass"]
        tx = fig.add_axes([x0 + 0.27, y0, 0.22, 0.38])
        tx.axis("off")
        yy = 0.97
        def put(t, color=INK, bold=False, size=8.8, gap=0.062):
            nonlocal yy
            for ln in textwrap.wrap(t, 34):
                tx.text(0, yy, ln, fontsize=size, color=color, va="top", fontweight="bold" if bold else "normal",
                        transform=tx.transAxes)
                yy -= gap
            yy -= 0.015
        put(f"Strong: {'PASS' if strong else 'FAIL'} (min {c['min_margin']:.2f})", OK if strong else BAD, True, 9.5)
        put("governs: " + c["governing"], INK2, size=8.2)
        put(f"Body {e['mass']['body_g']:.0f} g ({e['mass']['body_g'] / 453.6:.2f} lb)", bold=True)
        put(f"vs H1 {e['mass']['body_g'] - H1['body_g']:+.0f} g, vs H1c {e['mass']['body_g'] - H1C['body_g']:+.0f} g")
        put(f"USD {e['cost']['per_frame_usd']:.0f} per frame ({'within' if e['cost']['within_cap'] else 'OVER'} cap)",
            bold=True)
        put("Stays: " + e["stay_desc"], INK2, size=8.2)
        if pick == k:
            put("PICK (owner may override)", METAL, True, 10)
    leg = fig.add_axes([0.02, 0.005, 0.96, 0.04])
    leg.axis("off")
    for j, (c_, lab) in enumerate(((METAL, "aluminium (6061 / 7075)"), (PRINT, "printed PAHT-CF"),
                                   (CROWN, "crown kit (carried over)"), ("#555555", "Ti hip mount (kept)"))):
        leg.add_patch(Rectangle((0.01 + j * 0.24, 0.25), 0.02, 0.5, color=c_, transform=leg.transAxes))
        leg.text(0.035 + j * 0.24, 0.5, lab, va="center", fontsize=9.5, color=INK, transform=leg.transAxes)
    fig.savefig(png, dpi=110, facecolor="white")
    plt.close(fig)


def bars(rec, png):
    keys = list(rec["concepts"])
    labels = ["H1\n(retired)", "H1c"] + [f"{k}" for k in keys]
    mass = [H1["body_g"], H1C["body_g"]] + [rec["concepts"][k]["mass"]["body_g"] for k in keys]
    cost = [H1["usd"], H1C["usd"]] + [rec["concepts"][k]["cost"]["per_frame_usd"] for k in keys]
    strong = [False, False] + [rec["concepts"][k]["strong_pass"] for k in keys]
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.6), dpi=110)
    fig.suptitle("BL-080  Frame body mass and per-frame cost (Strong gate first)", x=0.02, ha="left",
                 fontsize=13.5, fontweight="bold", color=INK)
    for ax, vals, unit, title, cap in ((axs[0], mass, "g", "Frame body mass, g (lower is better)", None),
                                       (axs[1], cost, "USD", "Materials per frame, USD (cap 150)", CAP_USD)):
        cols = [CROWN, CROWN] + [METAL] * len(keys)
        b = ax.bar(range(len(vals)), vals, color=cols, width=0.62, edgecolor="white", linewidth=2)
        for i, (v, r) in enumerate(zip(vals, b)):
            ax.text(r.get_x() + r.get_width() / 2, v + max(vals) * 0.015, f"{v:.0f}", ha="center", fontsize=10,
                    color=INK)
            tag = "pass" if strong[i] else "fail"
            if i < 2:
                tag = "fails" if i == 0 else "2 open"
            ax.text(r.get_x() + r.get_width() / 2, max(vals) * 0.04, tag, ha="center", fontsize=8.5,
                    color="white", fontweight="bold")
        if cap:
            ax.axhline(cap, color=INK2, lw=1.2, ls="--")
            ax.text(-0.45, cap + 3, "cap USD 150", ha="left", fontsize=9, color=INK2)
        ax.set_xticks(range(len(vals)), labels, fontsize=10)
        ax.set_title(title, fontsize=11, loc="left", color=INK)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2)
    fig.text(0.02, 0.01, "Grey = printed PAHT baselines (BL-077). Bar label = HA-LS-1 first-order Strong result "
             "(H1c: two interfaces still open).", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(png, dpi=110, facecolor="white")
    plt.close(fig)


def margins(rec, png):
    """One row per check family, one dot per concept: the Strong gate at 1.0 (single axis, margin = capacity / need)."""
    keys = list(rec["concepts"])
    fams = [("strength", "stays"), ("strength", "bars"), ("strength", "hub"), ("fatigue", "stays"), ("fatigue", "bars"),
            ("fatigue", "hub"), ("buckling", None), ("checks", "printed crown sleeve ring bending (fatigue)"),
            ("checks", "upper_bar tee clamp slip"), ("checks", "hub-to-stay bolt bearing")]
    labels = ["strength: stays", "strength: bars", "strength: hip hub / pan", "fatigue: stays", "fatigue: bars",
              "fatigue: hip hub / pan", "buckling (1.5 x factor)", "printed crown sleeve (A)", "upper tee clamp slip",
              "hub bolt bearing in tube"]
    cols = {"A": "#ec4647", "B": METAL, "C": "#f2a600", "D": "#00b894"}
    marks = {"A": "X", "B": "o", "C": "s", "D": "D"}
    fig, ax = plt.subplots(figsize=(11, 7.0), dpi=110)
    for j, k in enumerate(keys):
        c = rec["concepts"][k]["checks"]
        for i, (fam, sub) in enumerate(fams):
            v = None
            if fam in ("strength", "fatigue"):
                v = c[fam].get(sub, {}).get("margin")
            elif fam == "buckling":
                v = c["buckling"]["margin"] if c["buckling"] else None
            else:
                hits = [h["margin"] for h in c["checks"] if h["label"].startswith(sub)]
                v = min(hits) if hits else None
            if v is None:
                continue
            ax.scatter(min(v, 3.0), i + (j - 1.5) * 0.16, s=70, color=cols[k], marker=marks[k], edgecolor="white",
                       linewidth=1.2, zorder=3, label=f"{k}" if i == 0 or (fam == "checks" and k == "A") else None)
    ax.axvline(1.0, color=INK, lw=1.4)
    ax.text(1.02, len(fams) - 0.55, "gate 1.0", fontsize=9, color=INK)
    ax.set_yticks(range(len(fams)), labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 3.05)
    ax.set_xlabel("margin = capacity / requirement (values above 3 drawn at 3)", fontsize=10, color=INK2)
    ax.grid(axis="x", color=GRID)
    ax.spines[["top", "right"]].set_visible(False)
    h, l = ax.get_legend_handles_labels()
    seen = {}
    for hh, ll in zip(h, l):
        seen.setdefault(ll, hh)
    ax.legend(seen.values(), [rec["concepts"][k]["name"][:46] for k in seen], loc="upper center", fontsize=9,
              frameon=False, ncol=2, bbox_to_anchor=(0.45, -0.12))
    ax.set_title("BL-080  HA-LS-1 rev C first-order margins by check (worst case and torso)", loc="left",
                 fontsize=12.5, fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(png, dpi=110, facecolor="white")
    plt.close(fig)


def main():
    rec = json.loads(REC_JSON.read_text())
    SCREENS.mkdir(parents=True, exist_ok=True)
    out = [SCREENS / f"{SHOT}1.png", SCREENS / f"{SHOT}2.png", SCREENS / f"{SHOT}3.png"]
    concept_sheet(rec, out[0])
    bars(rec, out[1])
    margins(rec, out[2])
    return out


if __name__ == "__main__":
    for p in main():
        print(p)
