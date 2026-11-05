"""Bag-top anchor study (pack-designer, 2026-11-05): compare cloth-sim runs and draw the screenshots.

Reads outputs/clothsim/<scenario>/results.json for the baseline and the study scenarios
(huntkit/clothsim/scenarios/pack5200_v31_tab_doubler.yaml, pack5200_v31_anchor_*.yaml), prints the comparison
table used in analysis/bag_top_anchor.md and writes:
  outputs/screens/20261105_bagtop_1.png  side profile (x = 0 section), baseline vs candidates, fill + meat
  outputs/screens/20261105_bagtop_2.png  attachment detail: where the anchors, IM3 tab and hinge doubler sit
  outputs/clothsim/bagtop_compare.json   the numbers

    python designs/pack_5200/bag_top_anchor.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUT = REPO / "outputs" / "clothsim"
SCREENS = REPO / "outputs" / "screens"
HA_LS_1 = {"meat": 150.0, "fill": 180.0}          # load_standard.md C5 / C1 CG aft
RUNS = [("baseline", "pack5200_v31_baseline", "phase-1 bag (no top anchor)"),
        ("T0", "pack5200_v31_tab_doubler", "IM3 tab + hinge doubler only"),
        ("A", "pack5200_v31_anchor_A_crownbar", "crown-bar tie, z 703 (19 in), fixed length"),
        ("B", "pack5200_v31_anchor_B_bar_guys", "A + top guys forward to the bar ends"),
        ("F", "pack5200_v31_anchor_F_lash_guys", "A + diagonal guys down to the z 420 lash points"),
        ("C", "pack5200_v31_anchor_C_collar", "tie at the collar seam, z 775"),
        ("D", "pack5200_v31_anchor_D_low15", "crown-bar tie at 15 in (z 601)"),
        ("E", "pack5200_v31_anchor_E_soft", "as A, cinched (soft) 80 N"),
        ("G", "pack5200_v31_anchor_G_stiff_forward", "A + forward guys, fixed length (stiff)"),
        ("H", "pack5200_v31_anchor_H_stiff_diagonal", "A + diagonal guys to z 420, fixed length (stiff)")]
CROWN_TOP_Z = {"D": 601.0}         # crown top bar z per run; default 702.6 (19 in)
MEAT_KG, GEAR_KG = 30.0, 38.0


def load():
    out = {}
    for key, name, label in RUNS:
        f = OUT / name / "results.json"
        if f.exists():
            out[key] = {"name": name, "label": label, "r": json.loads(f.read_text())}
    return out


_DRAFT = {}


def drafted_fore_face() -> dict:
    """x = 0 fore-face y of the DRAFTED bag (mesh X0) per 50 mm z band, same binning as report.summarize."""
    if not _DRAFT:
        from huntkit.clothsim.pack import PackModel, load_scenario
        pm = PackModel(load_scenario(), verbose=False)
        X = pm.mesh.X0
        sec = np.abs(X[:, 0]) < 0.6 * pm.h
        for z in np.arange(pm.c["Z0"], X[:, 2].max(), 50.0):
            s_ = sec & (np.abs(X[:, 2] - z) < 25)
            if s_.sum() > 0:
                _DRAFT[int(round(z))] = float(X[s_, 1].min())
    return _DRAFT


def head_intrusion(c: dict, z_top: float = 702.6) -> tuple:
    """Largest forward move (toward the wearer's head) of the frame-side wall at x = 0 ABOVE the crown top bar
    (the only part of the bag the head reaches in extension, DESIGN.md 4.7), loaded vs drafted, mm (+ = toward the
    head). Compare with the 30 deg-extension gap of the head-clearance check (6.8 mm at 23 in, p50 male)."""
    d = drafted_fore_face()
    best = (0.0, None)
    for row in c["profile"]["depth_by_z"]:
        z = int(round(row[0]))
        if z - 25 >= z_top and z in d:
            v = d[z] - row[1]
            if v > best[0]:
                best = (v, z)
    return best


def metrics(r: dict, case: str, key: str = "") -> dict:
    c = r["cases"][case]
    zt = CROWN_TOP_Z.get(key, 702.6)
    att = c["attachments"]
    im3 = [att[k]["tension_n"] for k in ("hook_im520_R", "hook_im520_L") if k in att]
    hin = [att[k] for k in ("hinge_R", "hinge_L") if k in att]
    hf = max(h["tension_n"] for h in hin)
    dbl = max(h.get("doubler_mm", 0) or 0 for h in hin)
    seam = c["seams"]["B-01 | B-05"]
    ties = {k: v["tension_n"] for k, v in att.items() if v["kind"] == "tie" and "." not in k}
    cg = c["volume"]["contents_cg_mm"]
    m = {"cg_y": cg[1], "cg_z": cg[2], "aft_depth": c["profile"]["max_depth_aft_mm"], "top_z": c["profile"]["top_z_mm"],
         "im3_max": max(im3), "hinge_max": hf,
         "hinge_line_n_mm": hf / dbl if dbl else seam["max_incl_ends_attachments_n_mm"],
         "hinge_line_basis": f"eye force / {dbl:.0f} mm doubler" if dbl else "sim node peak (one node)",
         "seam_b01_b05_n_mm": seam["max_n_mm"], "volume_L": c["volume"]["closed_L"],
         "body_L": c["volume"]["body_below_collar_seam_L"], "ties_n": ties, "converged": c["converged"],
         "residual_n": c["solve"][-1]["residual_n"],
         "fore_face_y": {int(row[0]): row[1] for row in c["profile"]["depth_by_z"]},
         "head_intrusion_mm": head_intrusion(c, zt)[0], "head_intrusion_z": head_intrusion(c, zt)[1],
         "crown_contact_n": c["contact"].get("contact_crown", {}).get("force_total_n")}
    if case == "meat":
        # supplementary: meat at its HA-LS-1 CG (cinched to the spreader, does not follow the bag) + gear at the
        # bag's volume centroid
        m["mixed_cg_y"] = (MEAT_KG * HA_LS_1["meat"] + GEAR_KG * cg[1]) / (MEAT_KG + GEAR_KG)
    return m


def table(runs) -> str:
    lines = []
    for case in ("fill", "meat"):
        lines += [f"**{case}** (HA-LS-1 assumes CG {HA_LS_1[case]:.0f} mm)", "",
                  "| run | concept | CG aft mm | aft depth mm | top z | IM3 hook N | hinge eye N | hinge seam N/mm | "
                  "top anchors N | wall toward head above crown mm | volume L |", "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
        for k, v in runs.items():
            m = metrics(v["r"], case, k)
            ties = ", ".join(f"{a} {t:.0f}" for a, t in m["ties_n"].items()) or "-"
            lines.append(f"| {k} | {v['label']} | {m['cg_y']:.0f} | {m['aft_depth']:.0f} | {m['top_z']:.0f} | "
                         f"{m['im3_max']:.0f} | {m['hinge_max']:.0f} | {m['hinge_line_n_mm']:.1f} | {ties} | "
                         f"{m['head_intrusion_mm']:.0f} (z {m['head_intrusion_z']}) | {m['volume_L']:.1f} |")
        lines.append("")
    return "\n".join(lines)


def frame_side(ax):
    """Frame (printed body at x ~ +/-115, STL samples), spreader and crown as a side outline (y aft, z up)."""
    from huntkit.clothsim.pack import frame_clouds
    cl = frame_clouds()
    P = cl["frame_p"]
    s = np.abs(np.abs(P[:, 0]) - 115) < 12
    ax.scatter(P[s, 1], P[s, 2], s=0.3, c="#8a8f96", alpha=0.35, lw=0)
    S = cl["spreader_p"]
    ss = np.abs(S[:, 0]) < 10
    ax.scatter(S[ss, 1], S[ss, 2], s=0.6, c="#1d1f22", lw=0)
    # crown leg (axis [-0.0189, 0.9998] from the stay top) and top bar (OD 18, 25 mm aft of the leg axis)
    z = np.array([530.0, 702.6])
    y = -10.0 + (z - 530.0) * (-0.0189 / 0.9998)
    ax.plot(y, z, color="#8a8f96", lw=6, alpha=0.6, solid_capstyle="butt")
    ax.add_patch(__import__("matplotlib").patches.Circle((11.7, 702.6), 9.0, color="#5b6068"))


def section(c):
    segs = c["profile"]["section_x0_segments_yz"]
    return [np.asarray(sg) for sg in segs]


def plot_profiles(runs, path, keys=("baseline", "A", "B")):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {"baseline": "#b03a2e", "T0": "#9aa0a6", "A": "#2e6fb0", "B": "#6aa84f", "C": "#7a4fb0", "D": "#c27c0e",
            "E": "#5aa0a0", "F": "#d1495b", "G": "#1e8a4c", "H": "#888888"}
    fig, axs = plt.subplots(1, 2, figsize=(11, 8.2), sharey=True)
    for ax, case in zip(axs, ("fill", "meat")):
        frame_side(ax)
        for k in keys:
            if k not in runs:
                continue
            c = runs[k]["r"]["cases"][case]
            for i, sg in enumerate(section(c)):
                ax.plot(sg[:, 0], sg[:, 1], color=cols[k], lw=1.6, label=f"{k}: {runs[k]['label']}" if i == 0 else None)
            cg = c["volume"]["contents_cg_mm"]
            ax.plot(cg[1], cg[2], "o", ms=9, mfc=cols[k], mec="white", mew=1.5)
            ax.annotate(f"CG {cg[1]:.0f}", (cg[1], cg[2]), xytext=(8, -4 + 12 * keys.index(k)), textcoords="offset points",
                        color=cols[k], fontsize=10, fontweight="bold")
            for nm, a in c["attachments"].items():
                if a["kind"] == "tie" and "." not in nm and nm.endswith("_R"):
                    pass
        ax.axvline(HA_LS_1[case], color="#444", ls="--", lw=1)
        ax.text(HA_LS_1[case] + 4, 60, f"HA-LS-1 {HA_LS_1[case]:.0f} mm", fontsize=9, color="#444", rotation=90)
        ax.axvline(180, color="#1e8a4c", ls=":", lw=1)
        ax.set_title(f"'{case}' case: 68 kg, x = 0 section", fontsize=12)
        ax.set_xlabel("y, mm aft of the frame (FCS)")
        ax.set_xlim(-60, 520)
        ax.set_ylim(-80, 1130)
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
    axs[0].set_ylabel("z, mm")
    axs[0].legend(loc="upper right", fontsize=8.5, frameon=True)
    fig.suptitle("Bag top anchor study: side profile before / after (dots = load CG)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    from huntkit.clothsim.report import shrink_png
    shrink_png(path)


def plot_detail(path):
    """Schematic of the frame side of the bag: where the candidate anchors and the two specified load spreaders sit."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(REPO / "designs" / "pack_5200"))
    import build_geometry as BG
    T = BG.BAGTOP
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 8.5), gridspec_kw={"width_ratios": [1.6, 1]})
    # --- left: B-01 frame-side view (looking forward at the bag's frame face), x right, z up
    a1.add_patch(mp.Rectangle((-150, 35), 300, 746, fc="#e9e4d8", ec="#6b6252", lw=1.2))
    a1.add_patch(mp.Rectangle((-150, 781), 300, 320, fc="#f3f1ec", ec="#6b6252", lw=1, ls="--"))
    for zs in (560, 631.2):
        a1.plot([-150, 150], [zs, zs], color="#6b6252", lw=0.8, ls=":")
    a1.add_patch(mp.Rectangle((-121, 112), 242, 318, fc="#2b2e33", alpha=0.18, ec="#2b2e33"))
    a1.text(0, 270, "spreader\n(behind B-01)", ha="center", fontsize=8, color="#2b2e33")
    for sx in (1, -1):
        # IM3 hook tab B-17, centred on the hook strap bartack (x 115, z 450)
        a1.add_patch(mp.Rectangle((sx * 115 - T["im3_tab_w"] / 2, 450 - T["im3_tab_h"] / 2), T["im3_tab_w"], T["im3_tab_h"],
                                  fc="#c27c0e", alpha=0.8, ec="k"))
        a1.plot([sx * 115, sx * 115], [450, 520], color="#7a5a20", lw=5)
        a1.plot(sx * 115, 520, "o", ms=9, mfc="#444", mec="k")
        # hinge-eye doubler B-18 on the B-01 | B-05 seam
        a1.add_patch(mp.Rectangle((sx * 115 - T["hinge_dbl_w"] / 2, 35), T["hinge_dbl_w"], T["hinge_dbl_h"],
                                  fc="#b03a2e", alpha=0.8, ec="k"))
        a1.plot(sx * 115, 60, "o", ms=9, mfc="#444", mec="k")
        # candidate anchors: A (z 703 at 19 in; slides 601-779 with the torso), C (z 775)
        a1.plot([sx * 70] * 2, [601, 779], color="#2e6fb0", lw=7, alpha=0.35, solid_capstyle="butt")
        a1.plot(sx * 70, 702.6, "s", ms=11, mfc="#2e6fb0", mec="k")
        a1.plot(sx * 70, 775, "D", ms=9, mfc="#7a4fb0", mec="k")
    a1.plot([-70, 70], [702.6, 702.6], color="#5b6068", lw=4, alpha=0.6)
    L = dict(fontsize=8.5, ha="left", va="center")
    R = dict(fontsize=8.5, ha="right", va="center")
    arr = dict(arrowstyle="-", lw=0.7)
    a1.annotate("crown top bar (19 in)", (0, 702.6), (175, 690), color="#3a3d42", arrowprops={**arr, "color": "#3a3d42"}, **L)
    a1.annotate("A: crown-bar tie x \u00b170;\nslides z 601-779 with the crown", (-70, 650), (-175, 650),
                color="#2e6fb0", arrowprops={**arr, "color": "#2e6fb0"}, **R)
    a1.annotate("C: z 775 (needs a new\nfixed anchor at 19 in)", (-70, 775), (-175, 790), color="#7a4fb0",
                arrowprops={**arr, "color": "#7a4fb0"}, **R)
    a1.annotate("IM3 eye z 520", (115, 520), (175, 540), color="#333", arrowprops={**arr, "color": "#333"}, **L)
    a1.annotate(f"B-17 IM3 hook tab\n{T['im3_tab_w']:.0f} x {T['im3_tab_h']:.0f} Hypalon,\n"
                f"{T['im3_tab_stitch_mm']:.0f} mm stitch line", (150, 430), (175, 430), color="#7a5a20",
                arrowprops={**arr, "color": "#7a5a20"}, **L)
    a1.annotate(f"B-18 hinge-eye doubler\n{T['hinge_dbl_w']:.0f} x {T['hinge_dbl_h']:.0f} Hypalon,\n"
                f"{T['hinge_dbl_seam_mm']:.0f} mm of B-01|B-05 seam", (150, 55), (175, 110), color="#b03a2e",
                arrowprops={**arr, "color": "#b03a2e"}, **L)
    a1.annotate("hinge pin z 60", (-115, 60), (-175, 110), color="#333", arrowprops={**arr, "color": "#333"}, **R)
    a1.annotate("setback seam z 560", (-150, 560), (-175, 560), color="#6b6252", arrowprops={**arr, "color": "#6b6252"}, **R)
    a1.annotate("shoulder seam z 631", (-150, 631), (-175, 610), color="#6b6252", arrowprops={**arr, "color": "#6b6252"}, **R)
    a1.text(-175, 940, "collar B-06\n(rolled)", color="#6b6252", **R)
    a1.set_xlim(-330, 330)
    a1.set_aspect("equal")
    a1.set_title("Frame side of the bag (B-01), seen from the frame", fontsize=11)
    a1.set_xlabel("x, mm (+ = wearer's right)")
    a1.set_ylabel("z, mm")
    # --- right: side view of the anchor directions
    frame_side(a2)
    a2.add_patch(mp.Polygon([[19, 35], [19, 560], [49, 631], [49, 781], [49, 1101], [330, 1101], [339, 600], [300, 35]],
                            closed=True, fc="#e9e4d8", ec="#6b6252", alpha=0.7))
    a2.annotate("", xy=(20.7, 702.6), xytext=(48, 702.6), arrowprops=dict(arrowstyle="-|>", color="#2e6fb0", lw=2.5))
    a2.text(60, 690, "A: tie to the bar, horizontal", color="#2e6fb0", fontsize=8.5)
    a2.annotate("", xy=(20.7, 702.6), xytext=(293, 752), arrowprops=dict(arrowstyle="-|>", color="#1e8a4c", lw=2.5))
    a2.text(150, 760, "B/G: top guy from the aft upper\ncorner to the bar end", color="#1e8a4c", fontsize=8.5)
    a2.annotate("", xy=(20.7, 775), xytext=(48, 775), arrowprops=dict(arrowstyle="-|>", color="#7a4fb0", lw=2.5))
    a2.text(60, 800, "C: tie at the collar seam", color="#7a4fb0", fontsize=8.5)
    a2.annotate("", xy=(14, 520), xytext=(19, 450), arrowprops=dict(arrowstyle="-|>", color="#7a5a20", lw=2.5))
    a2.text(30, 470, "IM3 hook (tab B-17)", color="#7a5a20", fontsize=8.5)
    a2.set_xlim(-60, 400)
    a2.set_ylim(0, 1110)
    a2.set_aspect("equal")
    a2.set_title("Side view: anchor directions (drafted bag)", fontsize=11)
    a2.set_xlabel("y, mm aft")
    fig.suptitle("Bag-top anchor candidates + specified load spreaders (not final hardware)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    from huntkit.clothsim.report import shrink_png
    shrink_png(path)


def main():
    runs = load()
    print(table(runs))
    comp = {k: {"scenario": v["name"], "label": v["label"],
                "fill": metrics(v["r"], "fill", k), "meat": metrics(v["r"], "meat", k)} for k, v in runs.items()}
    (OUT / "bagtop_compare.json").write_text(json.dumps(comp, indent=1, default=float))
    SCREENS.mkdir(parents=True, exist_ok=True)
    best = [k for k in ("baseline", "A", "G", "C") if k in runs]
    plot_profiles(runs, SCREENS / "20261105_bagtop_1.png", keys=tuple(best))
    plot_detail(SCREENS / "20261105_bagtop_2.png")
    print("PNG", SCREENS / "20261105_bagtop_1.png", SCREENS / "20261105_bagtop_2.png")


if __name__ == "__main__":
    main()
