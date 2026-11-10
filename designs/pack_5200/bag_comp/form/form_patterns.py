"""CHERT flat-pattern sheet: the developed shell pieces (form.flat_pieces), sewing line + 12 mm seam allowance, the
owner camo at true scale (380 mm repeat) on the camo pieces, notches at the facet creases and the fang line.

    python designs/pack_5200/bag_comp/form/form_patterns.py      # -> outputs/screens/20261110_bagE_6.png (+ SVG in outputs/bag_comp_form)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import form as F  # noqa: E402

ROOT = F.ROOT
SCREENS = ROOT / "outputs" / "screens"
OUTD = ROOT / "outputs" / "bag_comp_form"
REPEAT_MM = 380.0      # owner_base accent repeat (huntkit/viz3d README)


def camo_image():
    from huntkit.viz3d.textures import owner_base_camo
    im, tag = owner_base_camo(1024)
    return np.asarray(im.convert("RGB")), tag


def sheet(path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly
    from shapely.geometry import Polygon
    c = F.make()
    fp = F.flat_pieces(c)
    camo, tag = camo_image()
    sa = F.BC.SA_BODY
    solid_col = "#5d6450"
    layout = [("B-01", "B-01 frame panel\nULTRA 200, cut 1", False),
              ("B-03", "B-03 side gusset\n330D, cut 2 (mirror)\n+ SH-F fang (camo)", "fang"),
              ("B-02u", "B-02u blade U\ncamo 630D, cut 1\n(fold at the creases)", True),
              ("B-02door", "B-02door door\n330D, cut 1", False),
              ("B-02h", "B-02h hinge band\n330D, cut 1", False),
              ("B-05", "B-05 floor (hexagon)\n500D, cut 1", False)]
    fig, ax = plt.subplots(figsize=(16, 10), dpi=100)
    x_off = 0.0
    for pid, lab, cm in layout:
        P = np.asarray(fp[pid]["outline"], float)
        P = P - P.min(0)
        if P[:, 1].max() < P[:, 0].max() and pid not in ("B-05", "B-02h"):
            P = P[:, ::-1]
        P = P - P.min(0)
        P[:, 0] += x_off + sa
        P[:, 1] += sa
        poly = Polygon(P)
        cut = np.asarray(poly.buffer(sa, join_style=2).exterior.coords)
        ax.add_patch(MPoly(cut, closed=True, fill=False, ec="#222", lw=1.0, ls="--"))
        if cm is True:
            patch = MPoly(P, closed=True, fc="none", ec="#111", lw=1.4)
            ax.add_patch(patch)
            x0, y0 = P.min(0)
            w, h = P.max(0) - P.min(0)
            nx, ny = int(np.ceil(w / REPEAT_MM)) + 1, int(np.ceil(h / REPEAT_MM)) + 1
            for i in range(nx):
                for j in range(ny):
                    im = ax.imshow(camo, extent=[x0 + i * REPEAT_MM, x0 + (i + 1) * REPEAT_MM, y0 + j * REPEAT_MM,
                                                 y0 + (j + 1) * REPEAT_MM], zorder=1, interpolation="bilinear")
                    im.set_clip_path(patch)
        else:
            ax.add_patch(MPoly(P, closed=True, fc=solid_col, ec="#111", lw=1.4, alpha=0.95))
        if cm == "fang":
            fl = np.asarray(fp["B-03"]["fang"], float)
            Q = np.asarray(fp[pid]["outline"], float)
            mn = Q.min(0)
            fl = fl - mn
            if (np.asarray(fp[pid]["outline"]) - mn)[:, 1].max() < (np.asarray(fp[pid]["outline"]) - mn)[:, 0].max():
                fl = fl[:, ::-1]
            fl[:, 0] += x_off + sa
            fl[:, 1] += sa
            gpoly = Polygon(P)
            # camo below the fang line: the part of the gusset on the floor side of the line
            far = np.array([fl[-1] + (fl[-1] - fl[0]) * 3, fl[0] - (fl[-1] - fl[0]) * 3])
            nrm = np.array([-(fl[-1] - fl[0])[1], (fl[-1] - fl[0])[0]])
            nrm = nrm / np.linalg.norm(nrm)
            for sgn in (1, -1):
                half = Polygon(np.vstack([far, far[::-1] + sgn * nrm * 3000]))
                part = gpoly.intersection(half)
                if not part.is_empty and part.area < gpoly.area / 2:
                    fang = part
            FP = np.asarray(fang.exterior.coords)
            patch = MPoly(FP, closed=True, fc="none", ec="#111", lw=1.2)
            ax.add_patch(patch)
            x0, y0 = FP.min(0)
            im = ax.imshow(camo, extent=[x0, x0 + REPEAT_MM, y0, y0 + REPEAT_MM], zorder=2)
            im.set_clip_path(patch)
            ax.plot(fl[:, 0], fl[:, 1], color="#111", lw=1.2, ls="-.", zorder=3)
        w, h = P.max(0) - P.min(0)
        ax.text(P[:, 0].mean(), P[:, 1].max() + sa + 22, lab, ha="center", va="bottom", fontsize=9.5, zorder=4)
        ax.text(P[:, 0].mean(), P[:, 1].min() - sa - 18,
                f"{w:.0f} x {h:.0f} mm ({w / 25.4:.1f} x {h / 25.4:.1f} in)", ha="center", va="top", fontsize=8.5, color="#333")
        x_off = P[:, 0].max() + sa + 70
    ax.plot([0, 500], [-120, -120], color="k", lw=3)
    ax.text(250, -140, "500 mm (19.7 in)", ha="center", va="top", fontsize=9)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlim(-40, x_off)
    ax.set_ylim(-200, 1250)
    ax.axis("off")
    ax.set_title("CHERT (Team E FORM): developed shell pieces at true scale. Solid line = sewing line, dashed = 12 mm cut "
                 "line;\nowner camo at its 380 mm repeat on the camo pieces. Seams all straight; 2 R 55 door corners "
                 f"(as CORRIE). Camo: {tag}", fontsize=11, loc="left")
    path = Path(path or SCREENS / "20261110_bagE_6.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100, bbox_inches="tight", facecolor="white")
    OUTD.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTD / "chert_pattern_sheet.svg", bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    print(sheet())
