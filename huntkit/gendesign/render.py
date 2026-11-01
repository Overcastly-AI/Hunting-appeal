"""Phone-readable PNG renders (matplotlib; the viz3d three.js pipeline needs Playwright + Chromium,
which this environment does not have). Palette: dataviz skill reference instance (slots 1-3)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d9d8d4"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TI_COL = (0.62, 0.64, 0.68)
FDM_COL = (0.36, 0.37, 0.40)


def _style():
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "text.color": INK,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.edgecolor": GRID, "font.size": 13, "axes.titlesize": 15})


def save(fig, path, max_mb=1.5):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for dpi in (110, 90, 72, 60):
        fig.savefig(path, dpi=dpi, facecolor=SURF)
        if path.stat().st_size <= max_mb * 1e6:
            break
    plt.close(fig)
    return str(path)


def _shade(mesh, base, light=(0.4, -0.6, 0.7)):
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    n = mesh.face_normals
    d = np.clip(n @ L, 0, 1)
    k = 0.35 + 0.65 * d
    return np.clip(np.outer(k, base), 0, 1)


def draw_mesh(ax, mesh, color=TI_COL, elev=22, azim=-55, extra=None):
    tris = mesh.triangles
    pc = Poly3DCollection(tris, facecolors=_shade(mesh, color), edgecolors="none", linewidths=0)
    ax.add_collection3d(pc)
    lo, hi = mesh.bounds
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2 * 1.05
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def lug_card(mesh_slm, mesh_fdm, title, lines, path):
    _style()
    fig = plt.figure(figsize=(9, 11))
    fig.suptitle(title, fontsize=17, fontweight="bold", x=0.04, ha="left", y=0.975)
    ax1 = draw_mesh(fig.add_axes([0.01, 0.43, 0.48, 0.48]), mesh_slm, TI_COL, 24, -55)
    ax2 = draw_mesh(fig.add_axes([0.51, 0.43, 0.48, 0.48]), mesh_slm, TI_COL, -20, 125)
    ax1.set_title("SLM Ti-6Al-4V (production)", color=INK2, fontsize=13)
    ax2.set_title("same part, opposite side", color=INK2, fontsize=13)
    if mesh_fdm is not None:
        ax3 = draw_mesh(fig.add_axes([0.02, 0.03, 0.42, 0.36]), mesh_fdm, FDM_COL, 24, -55)
        ax3.set_title("FDM PAHT-CF prototype (as printed)", color=INK2, fontsize=13)
    import textwrap
    tx = fig.add_axes([0.47, 0.03, 0.5, 0.38]); tx.set_axis_off()
    wrapped = []
    for ln in lines:
        ind = len(ln) - len(ln.lstrip())
        wrapped += textwrap.wrap(ln, 38, subsequent_indent=" " * (ind + 2)) or [""]
    tx.text(0, 1, "\n".join(wrapped), va="top", ha="left", fontsize=12.5, color=INK, family="DejaVu Sans",
            linespacing=1.45)
    return save(fig, path)


def plate_card(pp, solid, d, chk, rep, mass_g, base_g, path):
    _style()
    fig, ax = plt.subplots(figsize=(10, 8.2))
    ox = d["outline"]
    x, y = ox.exterior.xy
    ax.fill(x, y, color="#3a3a3c", zorder=1)
    for p in d["holes"]:
        hx, hy = p.exterior.xy
        ax.fill(hx, hy, color=SURF, zorder=2)
        ax.plot(hx, hy, color=S2, lw=1.6, zorder=3)
    ax.plot(x, y, color=S2, lw=1.6, zorder=3)
    for (cx, cy, dd, lab) in d["drills"]:
        ax.add_patch(plt.Circle((cx, cy), dd / 2, color=SURF, zorder=4))
    g = pp["grid"]
    z = g.to_array(pp["zones"]["band"]).T
    ax.contour(np.linspace(g.x0[0], g.x0[0] + g.shape[0] * g.h, g.shape[0]),
               np.linspace(g.x0[1], g.x0[1] + g.shape[1] * g.h, g.shape[1]), z, levels=[0.5],
               colors=[S1], linewidths=1.2, linestyles="--", zorder=5)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)"); ax.set_ylabel("frame z (mm)")
    ax.set_title(f"Lumbar plate cut pattern: {d['n_cutouts']} cut-outs, QI carbon {pp['t']:g} mm\n"
                 f"{mass_g:.0f} g vs {base_g:.0f} g solid ({100 * (1 - mass_g / base_g):.0f} % lighter)",
                 loc="left", fontsize=15)
    txt = (f"orange = water-jet CUT line   blue dashed = stay bond band (no cuts)\n"
           f"min web {rep['min_web_mm']:.0f} mm (rule >= 3t = {3 * pp['t']:.0f})   edge distance >= {3 * pp['t']:.0f} mm\n"
           f"Tsai-Wu FPF (membrane + bending) min SF/required = {chk['min_sf_combined']:.2f}   "
           f"web buckling {chk['min_sf_buckling']:.1f}")
    fig.text(0.03, 0.02, txt, fontsize=12, color=INK2, va="bottom")
    fig.subplots_adjust(bottom=0.2, top=0.88)
    return save(fig, path)


def layout_card(gs_full, gs_cur, variants, path, torso=19):
    _style()
    fig = plt.figure(figsize=(10, 12))
    fig.suptitle("Frame layout optimization (frame ground structure, all HA-LS-1 cases)", x=0.03, ha="left",
                 fontsize=15, fontweight="bold")
    for i, (gs, lab) in enumerate(((gs_cur, "current topology (LP-sized)"), (gs_full, "free ground structure"))):
        ax = fig.add_axes([0.03 + 0.48 * i, 0.38, 0.45, 0.52])
        d = gs[torso]
        P, a = d["P"], d["area"]
        amax = np.nanmax(a) if np.isfinite(np.nanmax(a)) else 1
        for k, (p, q, L) in enumerate(d["bars"]):
            if not np.isfinite(a[k]) or a[k] < 0.02 * amax:
                continue
            ax.plot([P[p, 0], P[q, 0]], [P[p, 2], P[q, 2]], color=S1 if i == 0 else S2,
                    lw=0.8 + 7 * a[k] / amax, solid_capstyle="round", alpha=0.9)
        ax.scatter(P[:, 0], P[:, 2], s=10, color=INK2, zorder=5)
        ax.set_aspect("equal"); ax.set_xlim(-190, 190)
        ax.set_title(f"{lab}\nideal mass {d['mass_g']:.0f} g (torso {torso} in)", fontsize=13, loc="left")
        ax.set_xlabel("x (mm)")
        if i == 0:
            ax.set_ylabel("z (mm)")
    ax = fig.add_axes([0.33, 0.06, 0.6, 0.25])
    names = [v["name"] for v in variants]
    vals = [v["lp_mass_g"] for v in variants]
    cols = [S1 if v["name"] == "current" else (S2 if v["name"] == "free ground structure" else S3) for v in variants]
    ax.barh(range(len(names)), vals, color=cols, height=0.6)
    for k, v in enumerate(vals):
        ax.text(v + 1, k, f"{v:.0f} g", va="center", fontsize=12, color=INK)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("ideal (plastic LP) tube mass, worst torso 15/19/23, g")
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return save(fig, path)


def mass_chart(rows, path, title):
    """rows: [(label, baseline_g, slm_g, fdm_g)]"""
    _style()
    fig, ax = plt.subplots(figsize=(9, 10))
    n = len(rows)
    y = np.arange(n)
    hgt = 0.26
    for k, (lab, col, idx) in enumerate((("7075 sleeves / solid plate (current)", S1, 1),
                                         ("generative: SLM Ti / cut carbon plate", S2, 2),
                                         ("FDM PAHT-CF prototype", S3, 3))):
        vals = [r[idx] if r[idx] is not None else 0 for r in rows]
        ax.barh(y + (k - 1) * (hgt + 0.03), vals, height=hgt, color=col, label=lab)
        for yy, v, r in zip(y, vals, rows):
            if r[idx] is not None:
                ax.text(v + 2, yy + (k - 1) * (hgt + 0.03), f"{v:.0f}", va="center", fontsize=11, color=INK)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("mass per frame set, g")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.0), frameon=False, fontsize=11.5, ncol=1)
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.suptitle(title, x=0.03, ha="left", fontsize=15, fontweight="bold")
    fig.subplots_adjust(left=0.25, right=0.95, top=0.82, bottom=0.07)
    return save(fig, path)


def build_plate(parts, path, plate=(340.0, 320.0), title="Build plate"):
    """parts: list of (mesh already oriented on z=0, label). Simple shelf packing, top + iso view."""
    _style()
    placed, overflow = [], []
    x = y = 6.0
    row_h = 0.0
    for m, lab in parts:
        w, d = m.extents[0], m.extents[1]
        if w > d and d > 0 and w > plate[0] - 12:
            pass
        if x + w > plate[0] - 6:
            x = 6.0; y += row_h + 6.0; row_h = 0.0
        if y + d > plate[1] - 6:
            overflow.append(lab)
            continue
        mm = m.copy(); mm.apply_translation([x - mm.bounds[0][0], y - mm.bounds[0][1], -mm.bounds[0][2]])
        placed.append((mm, lab))
        x += w + 6.0
        row_h = max(row_h, d)
    if overflow:
        title += f"  (+{len(overflow)} parts on a 2nd plate)"
    import trimesh
    fig = plt.figure(figsize=(10, 12.5))
    fig.suptitle(title, x=0.03, ha="left", fontsize=15, fontweight="bold")
    T = trimesh.transformations.translation_matrix
    bed = trimesh.util.concatenate([      # plate outline as a thin border (flat tops would vanish on a solid bed)
        trimesh.creation.box((plate[0], 2.0, 1.0), transform=T((plate[0] / 2, 1.0, 0.5))),
        trimesh.creation.box((plate[0], 2.0, 1.0), transform=T((plate[0] / 2, plate[1] - 1.0, 0.5))),
        trimesh.creation.box((2.0, plate[1], 1.0), transform=T((1.0, plate[1] / 2, 0.5))),
        trimesh.creation.box((2.0, plate[1], 1.0), transform=T((plate[0] - 1.0, plate[1] / 2, 0.5)))])
    parts_m = trimesh.util.concatenate([p[0] for p in placed])
    ax = fig.add_axes([0.03, 0.45, 0.94, 0.46])
    img = zbuffer_image(trimesh.util.concatenate([parts_m, bed]), FDM_COL, elev=90, azim=0, size=900,
                        light=(0.45, 0.5, 0.75), bg="#e9e8e4")
    ax.imshow(img); ax.set_axis_off()
    ax.set_title(f"top view, {plate[0]:.0f} x {plate[1]:.0f} mm build plate, {len(placed)} parts", loc="left", fontsize=12)
    ax3 = draw_mesh(fig.add_axes([0.02, 0.0, 0.96, 0.44]), trimesh.util.concatenate([parts_m, bed]), FDM_COL, 40, -60)
    return save(fig, path), placed


# ----------------------------------------------------------------------------- z-buffer renderer
def _subdivide_long(mesh, max_edge):
    import trimesh
    m = mesh
    for _ in range(6):
        if m.edges_unique_length.max() <= max_edge:
            break
        v, f = trimesh.remesh.subdivide_to_size(m.vertices, m.faces, max_edge=max_edge, max_iter=6)
        m = trimesh.Trimesh(v, f, process=False)
    return m


def zbuffer_image(mesh, color=TI_COL, elev=22, azim=-55, size=700, light=(0.35, 0.5, 0.8), bg=SURF):
    """Flat-shaded software rasterizer with a z-buffer (no painter's-algorithm artifacts)."""
    import matplotlib.colors as mc
    V = np.asarray(mesh.vertices, float) - mesh.bounds.mean(0)
    F = np.asarray(mesh.faces)
    e, a = np.radians(elev), np.radians(azim)
    # camera: rotate about z by -azim, then tilt by elev
    Rz = np.array([[np.cos(a), np.sin(a), 0], [-np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.sin(e), np.cos(e)], [0, -np.cos(e), np.sin(e)]])
    P = V @ Rz.T @ Rx.T             # x right, y up, z toward viewer
    s = 0.92 * size / (2 * np.abs(P[:, :2]).max())
    X = P[:, 0] * s + size / 2
    Y = size / 2 - P[:, 1] * s
    Z = P[:, 2]
    n = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    shade = 0.28 + 0.62 * np.clip(n @ L, 0, 1) + 0.18 * np.clip(n[:, 2], 0, 1) ** 8
    zb = np.full((size, size), -np.inf)
    img = np.ones((size, size, 3)) * np.array(mc.to_rgb(bg))
    base = np.array(color)
    vis = n[:, 2] > -1e-6
    for k in np.where(vis)[0]:
        i0, i1, i2 = F[k]
        xs = (X[i0], X[i1], X[i2]); ys = (Y[i0], Y[i1], Y[i2])
        xmin, xmax = int(max(min(xs), 0)), int(min(max(xs) + 1, size - 1))
        ymin, ymax = int(max(min(ys), 0)), int(min(max(ys) + 1, size - 1))
        if xmax < xmin or ymax < ymin:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-12:
            continue
        l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        l2 = 1 - l0 - l1
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not inside.any():
            continue
        z = l0 * Z[i0] + l1 * Z[i1] + l2 * Z[i2]
        sub = zb[ymin:ymax + 1, xmin:xmax + 1]
        upd = inside & (z > sub)
        sub[upd] = z[upd]
        img[ymin:ymax + 1, xmin:xmax + 1][upd] = np.clip(base * shade[k], 0, 1)
    # simple silhouette darkening
    from scipy import ndimage
    fg = np.isfinite(zb)
    edge = fg & ~ndimage.binary_erosion(fg)
    img[edge] = img[edge] * 0.55
    return img


def draw_mesh(ax, mesh, color=TI_COL, elev=22, azim=-55, extra=None):     # noqa: F811  (z-buffer version)
    try:
        import fast_simplification
        if len(mesh.faces) > 60000:
            v, f = fast_simplification.simplify(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces), 1 - 60000 / len(mesh.faces))
            import trimesh
            mesh = trimesh.Trimesh(v, f, process=False)
    except ImportError:
        pass
    img = zbuffer_image(mesh, color, elev, azim)
    if hasattr(ax, "set_zlim"):        # caller made a 3D axes: replace it with a 2D image axes
        fig = ax.figure
        pos = ax.get_position()
        title = ax.get_title()
        ax.remove()
        ax = fig.add_axes(pos)
        ax._zb_title = title
    ax.imshow(img, interpolation="lanczos")
    ax.set_axis_off()
    return ax
