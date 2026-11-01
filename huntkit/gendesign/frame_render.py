"""Phone-readable renders for the printed whole-frame study (z-buffer software rasterizer, matplotlib).

Product views (front 3/4, back, side, on the pack), a utilization map, the segment layout on the build
plate, the mass/stiffness comparison chart and the optimization evolution. Colors: dataviz palette
(render.py constants) with a sequential blue -> amber -> red utilization ramp.
"""
from __future__ import annotations

import numpy as np

from .render import GRID, INK, INK2, S1, S2, S3, S4, SURF, _style, plt, save

BODY_COL = (0.34, 0.35, 0.38)
ROD_COL = (0.08, 0.08, 0.09)
TUBE_COL = (0.12, 0.12, 0.13)


def simplify(mesh, target=80000):
    try:
        import fast_simplification
        import trimesh
        if len(mesh.faces) > target:
            v, f = fast_simplification.simplify(np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces),
                                                1 - target / len(mesh.faces))
            return trimesh.Trimesh(v, f, process=False)
    except ImportError:
        pass
    return mesh


def _cam(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    Rz = np.array([[np.cos(a), np.sin(a), 0], [-np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.sin(e), np.cos(e)], [0, -np.cos(e), np.sin(e)]])
    return Rx @ Rz


def raster(meshes, elev=20, azim=-55, size=900, bg=SURF, light=(0.35, 0.55, 0.8), center=None, scale=None,
           spec=0.25):
    """meshes: list of (trimesh, rgb (3,) or per-face (nf, 3)). Flat shading + specular glint + silhouette."""
    import matplotlib.colors as mc
    R = _cam(elev, azim)
    allV = np.vstack([np.asarray(m.vertices) for m, _ in meshes])
    c = allV.mean(0) if center is None else np.asarray(center)
    P_all = (allV - c) @ R.T
    s = scale or 0.9 * size / (2 * np.abs(P_all[:, :2]).max())
    zb = np.full((size, size), -np.inf)
    img = np.ones((size, size, 3)) * np.array(mc.to_rgb(bg))
    L = np.asarray(light, float); L /= np.linalg.norm(L)
    H = L + np.array([0, 0, 1.0]); H /= np.linalg.norm(H)
    for m, col in meshes:
        V = (np.asarray(m.vertices) - c) @ R.T
        F = np.asarray(m.faces)
        X = V[:, 0] * s + size / 2
        Y = size / 2 - V[:, 1] * s
        Z = V[:, 2]
        n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.25 + 0.65 * np.clip(n @ L, 0, 1)
        glint = spec * np.clip(n @ H, 0, 1) ** 24
        cols = np.broadcast_to(np.asarray(col, float), (len(F), 3)) if np.ndim(col) == 1 else np.asarray(col)
        fc = np.clip(cols * shade[:, None] + glint[:, None], 0, 1)
        vis = np.where(n[:, 2] > -1e-6)[0]
        for k in vis:
            i0, i1, i2 = F[k]
            xs = (X[i0], X[i1], X[i2]); ys = (Y[i0], Y[i1], Y[i2])
            xmin, xmax = int(max(min(xs), 0)), int(min(max(xs) + 1, size - 1))
            ymin, ymax = int(max(min(ys), 0)), int(min(max(ys) + 1, size - 1))
            if xmax < xmin or ymax < ymin:
                continue
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
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
            img[ymin:ymax + 1, xmin:xmax + 1][upd] = fc[k]
    from scipy import ndimage
    fg = np.isfinite(zb)
    edge = fg & ~ndimage.binary_erosion(fg)
    img[edge] *= 0.45
    return img, {"center": c, "scale": s, "mask": fg}


def autocrop(img, mask, pad=12):
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return img
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, img.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, img.shape[1])
    return img[y0:y1, x0:x1]


def util_colors(u):
    """Sequential ramp for utilization 0..1+ (blue -> teal -> amber -> red)."""
    import matplotlib.colors as mc
    cmap = mc.LinearSegmentedColormap.from_list("u", ["#2a78d6", "#1baf7a", "#eda100", "#d6342a"])
    return cmap(np.clip(u, 0, 1))[:, :3], cmap


def product_card(body, rods, path, title, subtitle, views=(("front 3/4 (bag side)", 18, 35),
                                                           ("back (wearer side)", 8, 180 + 0),
                                                           ("side", 5, 90))):
    _style()
    fig = plt.figure(figsize=(12, 9.2))
    fig.suptitle(title, x=0.03, ha="left", fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.03, 0.925, subtitle, fontsize=11.5, color=INK2, ha="left")
    meshes = [(simplify(body), BODY_COL)] + ([(rods, ROD_COL)] if rods is not None else [])
    w = 1.0 / len(views)
    for i, (lab, el, az) in enumerate(views):
        img, info = raster(meshes, el, az, size=1000)
        img = autocrop(img, info["mask"])
        ax = fig.add_axes([i * w + 0.005, 0.02, w - 0.01, 0.86])
        ax.imshow(img); ax.set_axis_off()
        ax.set_title(lab, fontsize=12, color=INK2, loc="left")
    return save(fig, path)


def utilization_card(body, face_u, path, title, subtitle, views=(("bag side", 15, 30), ("wearer side", 10, 200))):
    _style()
    fig = plt.figure(figsize=(12, 9.5))
    fig.suptitle(title, x=0.03, ha="left", fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.03, 0.925, subtitle, fontsize=11.5, color=INK2, ha="left")
    cols, cmap = util_colors(face_u)
    for i, (lab, el, az) in enumerate(views):
        img, info = raster([(body, cols)], el, az, size=1000, spec=0.08)
        img = autocrop(img, info["mask"])
        ax = fig.add_axes([i * 0.45 + 0.01, 0.04, 0.44, 0.85])
        ax.imshow(img); ax.set_axis_off(); ax.set_title(lab, fontsize=12, color=INK2, loc="left")
    cax = fig.add_axes([0.92, 0.18, 0.022, 0.6])
    import matplotlib as mpl
    cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=mpl.colors.Normalize(0, 1))
    cb.set_label("utilization = factored stress / allowable", color=INK2)
    return save(fig, path)


def evolution_card(frames, path, title):
    """frames: list of (label, img). Grid of optimization snapshots."""
    _style()
    n = len(frames)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    fig = plt.figure(figsize=(12, 4.6 * rows + 0.9))
    fig.suptitle(title, x=0.03, ha="left", fontsize=17, fontweight="bold")
    for i, (lab, img) in enumerate(frames):
        ax = fig.add_subplot(rows, cols, i + 1)
        ax.imshow(img); ax.set_axis_off(); ax.set_title(lab, fontsize=11, color=INK2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01, wspace=0.02, hspace=0.12)
    return save(fig, path)


def comparison_chart(rows, tube_g, path, title):
    """rows: dicts label, frame_g, torsion_rel, carry_rel, passes, color_key. Two horizontal bar panels."""
    _style()
    rows = sorted(rows, key=lambda r: r["frame_g"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 1.1 + 0.62 * len(rows)), sharey=True,
                                 gridspec_kw={"width_ratios": [1.25, 1]})
    y = np.arange(len(rows))
    lab = [r["label"] for r in rows]
    colmap = {"plastic": S2, "hybrid": S1, "metal": INK2, "tube": S3}
    cols = [colmap.get(r.get("kind", "plastic"), S2) for r in rows]
    a1.barh(y, [r["frame_g"] for r in rows], color=cols, height=0.62)
    a1.axvline(tube_g, color=S3, lw=1.6, ls="--")
    a1.text(tube_g, len(rows) - 0.35, f" tube frame {tube_g:.0f} g", color=S3, fontsize=10, va="bottom")
    for yi, r in zip(y, rows):
        a1.text(r["frame_g"], yi, f" {r['frame_g']:.0f} g" + ("" if r.get("passes", True) else "  (fails)"),
                va="center", fontsize=10, color=INK)
    a1.set_yticks(y); a1.set_yticklabels(lab, fontsize=10.5)
    a1.set_xlabel("whole frame mass at the HA-LS-1 margins (g)")
    a1.set_xlim(0, max(r["frame_g"] for r in rows) * 1.28)
    a2.barh(y, [100 * r["torsion_rel"] for r in rows], color=cols, height=0.62)
    a2.axvline(80, color=S4, lw=1.6, ls="--")
    a2.axvline(100, color=S3, lw=1.0, ls=":")
    a2.text(80, -0.9, " -20 % feel limit", color=S4, fontsize=10)
    a2.set_xlabel("torsional stiffness vs tube frame (%)")
    a2.set_xlim(0, max(140, max(100 * r["torsion_rel"] for r in rows) * 1.15))
    for a in (a1, a2):
        a.grid(axis="x", color=GRID, lw=0.6); a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.suptitle(title, x=0.02, ha="left", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return save(fig, path)


def plate_card(parts, path, title, plate=(340.0, 320.0), notes=()):
    """parts: list of (mesh oriented on the plate at its XY placement, label). Top view + iso."""
    import trimesh
    _style()
    T = trimesh.transformations.translation_matrix
    bed = trimesh.creation.box((plate[0], plate[1], 1.0), transform=T((plate[0] / 2, plate[1] / 2, -0.6)))
    fig = plt.figure(figsize=(12, 7.8))
    fig.suptitle(title, x=0.03, ha="left", fontsize=17, fontweight="bold", y=0.975)
    n = len(parts)
    for i, (m, lab) in enumerate(parts):
        img, info = raster([(simplify(m, 60000), BODY_COL), (bed, (0.80, 0.80, 0.77))], 55, -60, size=800, spec=0.1)
        img = autocrop(img, info["mask"])
        ax = fig.add_axes([i / n + 0.005, 0.12, 1 / n - 0.01, 0.76])
        ax.imshow(img); ax.set_axis_off(); ax.set_title(lab, fontsize=11.5, color=INK2, loc="left")
    for k, t in enumerate(notes):
        fig.text(0.03, 0.08 - 0.03 * k, t, fontsize=11, color=INK)
    return save(fig, path)
