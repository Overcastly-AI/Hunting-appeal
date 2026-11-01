"""Render the 2026 pack-market comparison chart.

Data = published manufacturer / retailer / review figures, sourced in
docs/research/pack_market_2026.md (comparison table). Run:
    python docs/research/pack_market_chart.py
Writes outputs/screens/20261101_research_1.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[2] / "outputs/screens/20261101_research_1.png"

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
CARBON, ALU, OURS = "#2a78d6", "#eb6834", "#0b0b0b"   # validated categorical slots 1-2 + ink

# (label, volume cu in incl. lid where sold with one, total system lb, frame family, label offset)
SYSTEMS = [
    ("SG Sky 5900 + Krux", 5900, 5.09, "carbon", (-8, -13)),
    ("SG Sky 5900 + Xcurve", 5900, 5.28, "carbon", (8, 2)),
    ("SG Terminus 7000 (integrated)", 7000, 3.94, "carbon", (-10, 8)),
    ("Exo K4 5000", 5658, 5.81, "carbon", (8, -10)),
    ("Exo K4 3600", 4268, 5.50, "carbon", (6, 9)),
    ("KUIU Icon 6 3500", 3500, 5.09, "carbon", (6, -12)),
    ("KUIU Icon 6 4500", 5000, 5.89, "carbon", (-8, 8)),
    ("KUIU Icon 6 6000", 6700, 6.15, "carbon", (8, -4)),
    ("Kifaru ARK + Absaroka", 6580, 6.25, "carbon", (8, 6)),
    ("Akek Alpha 3200", 3200, 5.69, "carbon", (6, 6)),
    ("MR Beartooth 85", 5095, 6.20, "alu", (-8, 6)),
    ("MR Metcalf 100", 6100, 6.10, "alu", (8, -9)),
    ("Seek Outside Unaweep 6300", 6300, 3.69, "alu", (-8, 0)),
    ("Sitka Mtn Hauler 6200", 6200, 6.40, "alu", (8, 4)),
    ("Eberlestock Brute 6500", 6500, 6.81, "alu", (8, 0)),
]
OURS_V2 = ("Our v2 (rejected)", 5707, 6.64)

# frame + harness + hipbelt (+ shelf where integral), lb
SUSP = [
    ("KUIU Pro frame + suspension (S/M)", 2.49, "carbon"),
    ("Stone Glacier Krux (M belt)", 2.44, "carbon"),
    ("Seek Outside Revolution 24 in", 2.56, "alu"),
    ("Exo K4 frame system", 2.94, "carbon"),
    ("Stone Glacier Xcurve (M belt)", 3.06, "carbon"),
    ("Kifaru ARK (advertised)", 3.10, "carbon"),
    ("Our v2: frame+lock+belt+harness+back+shelf", 4.12, "ours"),
]
COL = {"carbon": CARBON, "alu": ALU, "ours": OURS}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 6.6), dpi=110,
                           gridspec_kw={"width_ratios": [1.45, 1]}, facecolor=SURF)
for ax in (a, b):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

# Panel A
a.axhspan(4.9, 5.5, xmin=0, xmax=1, color="#2a78d6", alpha=0.07, lw=0)
a.text(7550, 5.47, "recommended target band 4.9-5.5 lb", color=INK2, fontsize=8, va="top", ha="right")
a.grid(True, color=GRID, lw=0.8); a.set_axisbelow(True)
for name, v, w, fam, (dx, dy) in SYSTEMS:
    a.scatter(v, w, s=64, color=COL[fam], edgecolor=SURF, linewidth=2, zorder=3)
    a.annotate(name, (v, w), xytext=(dx, dy), textcoords="offset points", fontsize=7.6,
               color=INK, ha="left" if dx > 0 else "right", va="center")
a.scatter(OURS_V2[1], OURS_V2[2], s=150, marker="*", color=OURS, edgecolor=SURF, lw=1.5, zorder=4)
a.annotate(OURS_V2[0] + " 6.64 lb", (OURS_V2[1], OURS_V2[2]), xytext=(-10, -10),
           textcoords="offset points", fontsize=8, fontweight="bold", ha="right", color=INK)
a.scatter(5700, 5.2, s=150, marker="*", facecolor="none", edgecolor=OURS, lw=1.4, zorder=4)
a.annotate("Next-gen target", (5700, 5.2), xytext=(10, -2), textcoords="offset points",
           fontsize=8, fontweight="bold", color=INK, va="center")
a.set_xlim(2900, 7600); a.set_ylim(3.4, 7.1)
a.set_xlabel("Volume, cu in (bag + lid where sold with one)")
a.set_ylabel("Complete system weight, lb (frame + suspension + bag)")
a.set_title("A. Complete pack systems: volume vs weight", loc="left", fontsize=11, color=INK, fontweight="bold")
h = [plt.Line2D([], [], marker="o", ls="", color=CARBON, label="carbon stays / sheet"),
     plt.Line2D([], [], marker="o", ls="", color=ALU, label="aluminium (or composite, not carbon)"),
     plt.Line2D([], [], marker="*", ls="", color=OURS, ms=11, label="our pack")]
a.legend(handles=h, loc="upper left", frameon=False, fontsize=8)

# Panel B
names = [n for n, _, _ in SUSP][::-1]; vals = [v for _, v, _ in SUSP][::-1]
cols = [COL[f] for _, _, f in SUSP][::-1]
b.barh(range(len(vals)), vals, color=cols, height=0.55, edgecolor=SURF, linewidth=2)
for i, v in enumerate(vals):
    b.text(v + 0.05, i, f"{v:.2f} lb", va="center", fontsize=8.5, color=INK)
b.set_yticks(range(len(vals))); b.set_yticklabels(names, fontsize=8)
b.set_xlim(0, 4.9); b.grid(True, axis="x", color=GRID, lw=0.8); b.set_axisbelow(True)
b.set_xlabel("lb")
b.set_title("B. Frame + suspension weight (no bag)", loc="left", fontsize=11, color=INK, fontweight="bold")

fig.suptitle("Premium framed hunting packs, Nov 2026: our rejected v2 is ~1.5 lb heavier than the class it targets",
             x=0.01, ha="left", fontsize=12.5, color=INK, fontweight="bold")
fig.text(0.01, 0.01, "Sources: manufacturer pages and reviews cited in docs/research/pack_market_2026.md. "
         "\nRated loads: almost all claim 150+ lb (Seek Outside 200+); KUIU Icon 6, Mystery Ranch, Kifaru publish none. "
         "Figures as published; brand weights are not on a common scale.", fontsize=7.4, color=MUTED)
fig.tight_layout(rect=(0, 0.05, 1, 0.95))
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, facecolor=SURF)
print(OUT, OUT.stat().st_size)
