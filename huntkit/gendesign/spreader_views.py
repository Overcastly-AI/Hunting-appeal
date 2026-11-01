"""Drawings of the 2.0 mm QI carbon spreader. Visuals only; the part is the one already specified.

Blank: 208 x 300 x 2.0 mm, cfrp_plate_quasi_iso, mass from that blank.
Placement: centered at frame z = 280 mm (z 130 to 430), bag side of the stays.
Clips: the four M4 fasteners from the clip-in sheet hardware, at the two meat anchors
the sheet actually covers (IM1 z 190, IM2 z 330). IM3 at z 520 is above the sheet.
No corner radius and no edge notches are in the record.

Run: python -m huntkit.gendesign.spreader_views
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.materials import load

from . import frame_production as prod
from .frame_render import autocrop, raster, simplify
from .frame_smooth import bone_factored_n

DATE = "20261101"
SCREENS = REPO_ROOT / "docs" / "screens"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"
W, H, T = 208.0, 300.0, 2.0          # mm, the specified blank
Z_CENTER = 280.0                     # same station as the existing barrier box
# stay centers are x = ±115. Sheet edge is at ±104, so the stay center is 11 mm outboard.
HOLE_INSET = 8.0
HOLE_D = 4.5                         # M4 clearance
HOLE_Z = (190.0, 330.0)              # IM1, IM2. IM3 at 520 is above the sheet.


def _save(fig, name: str) -> str:
    from .render import save
    path = SCREENS / name
    save(fig, path)
    art = Path("/opt/cursor/artifacts/prodframe")
    art.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, art / name)
    out = REPO_ROOT / "outputs" / "screens"
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, out / name)
    return str(path)


def sheet_mass_g(t_mm: float, rho: float) -> float:
    return W * H * t_mm * rho / 1e6


def navier_field(n: int = 81, nterm: int = 24):
    """Simply-supported plate, factored bone load, same series as frame_production.plate_patch."""
    qi = load("cfrp_plate_quasi_iso")
    E = float(qi.require("youngs_modulus_mpa"))
    nu = float(qi.require("poisson"))
    P = bone_factored_n()
    a, b, t = W, H, T
    D = E * t ** 3 / (12.0 * (1.0 - nu ** 2))
    side = min(22.0 * np.sqrt(np.pi) / 2.0, 0.45 * min(a, b))
    x1, x2 = a / 2 - side / 2, a / 2 + side / 2
    y1, y2 = b / 2 - side / 2, b / 2 + side / 2
    q = P / (side * side)
    ms = np.arange(1, nterm + 1)
    ns = np.arange(1, nterm + 1)
    m, nn = np.meshgrid(ms, ns, indexing="ij")
    ix = (a / (m * np.pi)) * (np.cos(m * np.pi * x1 / a) - np.cos(m * np.pi * x2 / a))
    iy = (b / (nn * np.pi)) * (np.cos(nn * np.pi * y1 / b) - np.cos(nn * np.pi * y2 / b))
    pmn = 4.0 * q / (a * b) * ix * iy
    lam = (m / a) ** 2 + (nn / b) ** 2
    Wm = pmn / (np.pi ** 4 * D * lam ** 2)
    xs = np.linspace(0.0, a, n)
    ys = np.linspace(0.0, b, n)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    sx = np.sin(m[:, :, None, None] * np.pi * X[None, None] / a) * np.sin(
        nn[:, :, None, None] * np.pi * Y[None, None] / b)
    w = (Wm[:, :, None, None] * sx).sum(axis=(0, 1))
    dxx = -(((m * np.pi / a) ** 2)[:, :, None, None] * Wm[:, :, None, None] * sx).sum(axis=(0, 1))
    dyy = -(((nn * np.pi / b) ** 2)[:, :, None, None] * Wm[:, :, None, None] * sx).sum(axis=(0, 1))
    Mx = -D * (dxx + nu * dyy)
    My = -D * (dyy + nu * dxx)
    sxm = 6.0 * Mx / t ** 2
    sym = 6.0 * My / t ** 2
    svm = np.sqrt(np.maximum(sxm ** 2 - sxm * sym + sym ** 2, 0.0))
    check = prod.plate_patch(a, b, t, E, nu, P, 22.0)
    return {"x": xs, "y": ys, "w": w, "svm": svm, "P": P, "side": side,
            "center_mm": float(w[n // 2, n // 2]), "max_mpa": float(svm.max()),
            "check_defl": check["defl_mm"], "check_stress": check["stress_mpa"],
            "E": E, "nu": nu}


def _dim_h(ax, x0, x1, y, text, tick=4.0):
    ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", color="black", lw=0.7))
    ax.plot([x0, x0], [y - tick, y + tick], color="black", lw=0.6)
    ax.plot([x1, x1], [y - tick, y + tick], color="black", lw=0.6)
    ax.text((x0 + x1) / 2, y + 1.5, text, ha="center", va="bottom", fontsize=8)


def _dim_v(ax, y0, y1, x, text, tick=4.0):
    ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", color="black", lw=0.7))
    ax.plot([x - tick, x + tick], [y0, y0], color="black", lw=0.6)
    ax.plot([x - tick, x + tick], [y1, y1], color="black", lw=0.6)
    ax.text(x - 2.0, (y0 + y1) / 2, text, ha="right", va="center", fontsize=8, rotation=90)


def drawing() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    from .render import _style
    _style()
    qi = load("cfrp_plate_quasi_iso")
    rho = float(qi.require("density_kg_m3"))
    mass = sheet_mass_g(T, rho)
    fig, ax = plt.subplots(figsize=(8.6, 11.2))
    ax.set_aspect("equal")
    # sheet, origin at the lower-left corner. Bag-side view, z up, x to the wearer's right.
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.4, ec="black"))
    # holes
    z0 = Z_CENTER - H / 2.0
    for zf in HOLE_Z:
        zl = zf - z0
        for x in (HOLE_INSET, W - HOLE_INSET):
            ax.add_patch(Circle((x, zl), HOLE_D / 2, fill=False, lw=0.9, ec="black"))
    _dim_h(ax, 0, W, -18, "208")
    _dim_v(ax, 0, H, -16, "300")
    _dim_v(ax, 0, HOLE_Z[0] - z0, W + 14, f"{HOLE_Z[0] - z0:.0f}")
    _dim_v(ax, HOLE_Z[0] - z0, HOLE_Z[1] - z0, W + 14, f"{HOLE_Z[1] - HOLE_Z[0]:.0f}")
    _dim_h(ax, HOLE_INSET, W - HOLE_INSET, H + 16, f"{W - 2 * HOLE_INSET:.0f}")
    ax.annotate("8 from edge", xy=(HOLE_INSET, H), xytext=(HOLE_INSET + 28, H + 34),
                fontsize=8, ha="left", arrowprops=dict(arrowstyle="-", color="black", lw=0.6))
    ax.text(W / 2, H / 2 + 18, "BP-06\nQI carbon spreader", ha="center", va="center", fontsize=11)
    ax.text(W / 2, 18, "4× Ø4.5  M4 clearance\nIM1 and IM2 only", ha="center", va="bottom", fontsize=8)
    note = (
        f"t = 2.0 mm    mass {mass:.0f} g\n"
        "Layup: quasi-isotropic 0 / ±45 / 90\n"
        f"cfrp_plate_quasi_iso    E {float(qi.require('youngs_modulus_mpa')):.0f} MPa\n"
        "    ν 0.30    ρ 1550 kg/m³\n"
        "Ply count is not in the record.\n"
        "Bought plate; the record's typical\n"
        "thickness is 3 mm, this blank is 2.0.\n"
        "Corners square. No radius specified.\n"
        "No edge notches. No fairlead cutouts\n"
        "are in the record.\n"
        f"Sheet in the frame: z {z0:.0f} to {z0 + H:.0f}.\n"
        "IM3 (z 520) is above this sheet.\n"
        "Long edges bear on the stays.\n"
        "Stay center is 11 mm outboard\n"
        "of each long edge."
    )
    ax.text(W + 22, 70, note, ha="left", va="bottom", fontsize=8, family="sans-serif",
            linespacing=1.35)
    ax.set_xlim(-40, W + 130)
    ax.set_ylim(-36, H + 46)
    ax.axis("off")
    ax.set_title("BP-06  spreader, bag side   mm", loc="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"{DATE}_spreader_1_drawing.png")


def _box(size, center, color_unused=None):
    import trimesh
    m = trimesh.creation.box(extents=size)
    m.apply_translation(center)
    return m


def _parts(exploded: bool):
    import trimesh
    frame = trimesh.load(PRINT / "genframe_assembled.stl", force="mesh")
    frame = simplify(frame, target=18000)
    z0 = Z_CENTER - H / 2.0
    # bag face of the stay is about y = +10. Sheet sits just bag-side of that.
    y_sheet = 12.0
    y_rail = -24.0
    y_mesh = -36.0
    if exploded:
        y_sheet += 26.0
        y_rail -= 22.0
        y_mesh -= 28.0
    sheet = _box((W, T, H), (0.0, y_sheet, Z_CENTER))
    rails = []
    for s in (1.0, -1.0):
        rails.append(_box((100.0, 10.0, 420.0), (s * 115.0, y_rail, 260.0)))
    mesh = _box((230.0, 4.5, 300.0), (0.0, y_mesh, Z_CENTER))
    frame_c = (0.16, 0.17, 0.18)
    sheet_c = (0.55, 0.62, 0.68)
    rail_c = (0.62, 0.58, 0.50)
    mesh_c = (0.78, 0.80, 0.74)
    return [(frame, frame_c), (sheet, sheet_c), (rails[0], rail_c), (rails[1], rail_c), (mesh, mesh_c)]


def installed() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, SURF
    _style()
    parts = _parts(False)
    fig = plt.figure(figsize=(11.2, 4.6))
    views = (("bag side", 16, 28), ("wearer side", 12, 200), ("side", 4, 90))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster(parts, el, az, size=420, spec=0.18)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Spreader on the branch frame   carbon sheet, XLPE rails, mesh",
                 x=0.02, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.patch.set_facecolor(SURF)
    return _save(fig, f"{DATE}_spreader_2_installed.png")


def exploded() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, SURF
    _style()
    parts = _parts(True)
    fig = plt.figure(figsize=(11.0, 5.2))
    views = (("bag side", 18, 24), ("side", 6, 86))
    for i, (lab, el, az) in enumerate(views):
        ax = fig.add_subplot(1, 2, i + 1)
        img, info = raster(parts, el, az, size=460, spec=0.16)
        ax.imshow(autocrop(img, info["mask"], pad=10))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Exploded stack, wearer to bag:  mesh  ·  XLPE rails  ·  frame  ·  2 mm spreader",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.patch.set_facecolor(SURF)
    return _save(fig, f"{DATE}_spreader_3_exploded.png")


def bone_plot(field) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 6.4))
    ext = [0, W, 0, H]
    im0 = axes[0].imshow(field["w"].T, origin="lower", extent=ext, cmap="magma", aspect="equal")
    im1 = axes[1].imshow(field["svm"].T, origin="lower", extent=ext, cmap="magma", aspect="equal")
    for ax in axes:
        side = field["side"]
        ax.add_patch(plt.Circle((W / 2, H / 2), 11.0, fill=False, ec="white", lw=0.8, ls="--"))
        ax.set_xlabel("x (mm)")
        ax.set_ylabel("z on the sheet (mm)")
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label="deflection toward the wearer (mm)")
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label="surface von Mises (MPa)")
    axes[0].set_title(f"center {field['center_mm']:.1f} mm", loc="left", fontsize=11)
    axes[1].set_title(f"peak {field['max_mpa']:.0f} MPa", loc="left", fontsize=11)
    fig.suptitle(f"Bone end, factored {field['P']:.0f} N on a 22 mm patch   simply supported 208 × 300 × 2.0",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, f"{DATE}_spreader_4_bone.png")


def rejected() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, SURF
    _style()
    specs = [
        ("UHMWPE 1.2 mm", 1.2, float(load("uhmwpe_sheet").require("density_kg_m3")),
         (0.72, 0.74, 0.70), "475 kPa on foam. Retired."),
        ("PAHT plate 4.0 mm", 4.0, float(load("pa12_cf_fdm_paht").require("density_kg_m3")),
         (0.25, 0.26, 0.28), "Passes comfort. Heavier than the carbon sheet."),
        ("6061-T6 2.0 mm", 2.0, float(load("alu_6061_t6").require("density_kg_m3")),
         (0.62, 0.64, 0.66), "Pressure is fine. The sheet yields."),
    ]
    fig = plt.figure(figsize=(11.0, 4.4))
    for i, (name, t, rho, col, why) in enumerate(specs):
        m = _box((W, max(t, 1.2), H), (0.0, 0.0, 0.0))
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster([(m, col)], 18, 32, size=380, spec=0.28)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(f"{name}\n{sheet_mass_g(t, rho):.0f} g\n{why}", fontsize=9)
    fig.suptitle("Same 208 × 300 outline. These three were not chosen.",
                 x=0.02, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.patch.set_facecolor(SURF)
    return _save(fig, f"{DATE}_spreader_5_rejected.png")


def main():
    field = navier_field()
    print(f"center {field['center_mm']:.2f} mm  check {field['check_defl']:.2f}  "
          f"peak {field['max_mpa']:.1f} MPa  check {field['check_stress']:.1f}")
    paths = [drawing(), installed(), exploded(), bone_plot(field), rejected()]
    for p in paths:
        print(p)
    return paths


if __name__ == "__main__":
    main()
