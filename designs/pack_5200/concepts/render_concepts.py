"""Run the bag-body concept study and render it.

    python designs/pack_5200/concepts/render_concepts.py            # metrics + JSON + all PNGs (~3 min)
    python designs/pack_5200/concepts/render_concepts.py --no-render

Writes ``designs/pack_5200/concepts/concepts_results.json`` and phone-readable PNGs
``outputs/screens/20261107_bagalt_<n>.png`` (copies of the best in ``docs/screens/``).
Context (frame, crown, harness, hipbelt, mannequin at the 19 in torso) comes from ``huntkit.viz3d.model.build_pack``,
the same model as the released 3D viewer; SPINE is drawn from its released viz3d bag meshes (full state), the concepts
from ``bag_concepts`` rings. Side pockets, haul wraps, lid and bow carry are left out of every view (common to all).
One orthographic painter renderer, one light, one colorway, so the views compare like for like.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))
sys.path.insert(0, str(ROOT))

import bag_concepts as BC  # noqa: E402

DATE = "20261107"
SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
RESULTS = HERE / "concepts_results.json"
ORDER = ["spine", "slab", "twin", "wrap", "hatch"]
NUM = {"spine": 1, "slab": 2, "twin": 3, "wrap": 4, "hatch": 5}


# ============================================================================ study
def run_study():
    import patterns_v31 as P
    ps = P.build()
    rows, builds = {}, {}
    b = BC.spine_build(ps)
    rows["spine"] = {"metrics": BC.metrics(b), "volumes": BC.spine_volumes(), "tagline": b.concept.tagline,
                     "access": b.concept.access, "extra": b.extra}
    builds["spine"] = b
    for c in BC.all_concepts():
        b = BC.build_concept(c)
        rows[c.key] = {"metrics": BC.metrics(b), "volumes": BC.volumes(c), "tagline": c.tagline, "access": c.access,
                       "extra": {k: v for k, v in b.extra.items() if k not in ("surface", "split_uv")}}
        builds[c.key] = b
    sc = BC.score(rows)
    base_m = rows["spine"]["metrics"]["mass_g"]["total"]
    for k in rows:
        rows[k]["score"] = sc[k]
        rows[k]["mass_delta_g"] = round(rows[k]["metrics"]["mass_g"]["total"] - base_m, 1)
        rows[k]["pack_g"] = round(BC.PACK_TOTAL_G + rows[k]["mass_delta_g"], 1)
    out = {"date": DATE, "checks": {"spine_integrator": BC.spine_volume_check(), "dome_law_raw": BC.spine_dome_check(),
                                     "dome_cal": BC.DOME_CAL},
           "weights": BC.WEIGHTS, "hours_rates": BC.HOURS, "rows": rows}
    RESULTS.write_text(json.dumps(out, indent=1, default=_np))
    return out, builds


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


# ============================================================================ colours
def colours():
    from huntkit.viz3d import textures as TX
    from huntkit.viz3d.export import colorway
    cw = colorway({"colorway": "talus"})
    camo, src = TX.owner_base_camo(512)
    return {"body": _rgb(cw["body"]), "frame_panel": _rgb(cw["body"]) * 0.78, "trim": _rgb(cw["trim"]),
            "harness": _rgb(cw["harness"]), "zip": np.array([0.10, 0.10, 0.09]), "band": _rgb(cw["harness"]) * 1.1,
            "bottom": _rgb(cw["harness"]) * 0.9, "clay": _rgb("#cdc8be"), "printed_cf": _rgb("#2b2c2f"),
            "carbon": _rgb("#303236"), "webbing": _rgb("#3a3a33"), "hardware": _rgb("#222222"),
            "metal": _rgb("#9a9a9a"), "hypalon": _rgb("#2f302a"), "spacer": _rgb("#55574a"),
            "camo_img": np.asarray(camo, float) / 255.0, "camo_src": src, "name": cw["name"]}


def _rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def camo_at(C, u, v, rep=380.0):
    img = C["camo_img"]
    n = img.shape[0]
    i = (np.asarray(v) / rep * n).astype(int) % n
    j = (np.asarray(u) / rep * n).astype(int) % n
    return img[i, j]


# ============================================================================ context meshes (viz3d)
CONTEXT = ["frame_generative", "ti_hardware", "crown@t19", "crown_fittings@t19", "spreader_board", "fairlead_cleats",
           "cradle_fairleads", "hinge_pins", "captive_eyes", "crown_hood@t19", "hipbelt", "hipbelt_pockets",
           "hipbelt_shards", "hipbelt_webbing", "yoke_pad@t19", "shoulder_straps@t19", "harness_webbing@t19",
           "load_lifters@t19", "mannequin@t19", "under_straps", "tab_b17", "doublers_b18_b23", "hinge_eyes",
           "hook_tongues", "bag_hooks", "hood_ladders"]
SPINE_PARTS = ["bag_body_full", "bag_bottom", "bag_trim", "diagonal_band", "bag_shards", "zip_pulls", "rolltop_full",
               "rolltop_full_straps", "guy_tabs_b22_full", "top_guys_full@t19"]
MAT = {"printed_cf": "printed_cf", "carbon": "carbon", "carbon_matte": "carbon", "fitting": "hardware",
       "titanium": "metal", "aluminium": "metal", "webbing": "webbing", "hardware": "hardware", "hypalon": "hypalon",
       "harness": "harness", "body": "body", "camo": "camo", "clay": "clay", "tpu": "bottom", "trim": "trim",
       "spacer": "spacer", "xlpe": "hypalon"}


def load_context():
    from huntkit.viz3d.model import build_pack
    from huntkit.viz3d.params import load_params
    pk = build_pack(load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml")))
    by = {p.name: p for p in pk.parts}
    ctx, spine = [], []
    for nm in CONTEXT:
        if nm in by:
            ctx.append(_soup(by[nm], 18000 if nm in ("frame_generative", "mannequin@t19") else 6000))
    for nm in SPINE_PARTS:
        if nm in by:
            spine.append(_soup(by[nm], 40000))
    return ctx, spine


def _soup(part, max_faces):
    m = part.mesh
    if len(m.faces) > max_faces:
        try:
            m = m.simplify_quadric_decimation(face_count=max_faces)
        except Exception:  # noqa: BLE001
            idx = np.linspace(0, len(m.faces) - 1, max_faces).astype(int)
            m = m.submesh([idx], append=True)
    tri = m.vertices[m.faces]
    return {"tri": tri, "mat": MAT.get(part.material, "hardware"), "name": part.name}


# ============================================================================ concept meshes
COLOUR_HOOK = {}    # key -> fn(c, b, C, p, frame, s, L, zipdist) (render_wide.py registers the wider set)
EXTRA_SOUPS = {}    # key -> fn(c, b, C) -> [soups] (lids, wings, drybags)
CUSTOM_SOUP = {}    # key -> fn(c, b, C) -> [soups] replacing the loft (CRADLE)


def concept_soup(c: BC.Concept, b: BC.Build, C, M=200, nz=170):
    """Bag skin as quads with per-face colours from the concept's panel / accent / zip map."""
    if c.key in CUSTOM_SOUP:
        return CUSTOM_SOUP[c.key](c, b, C)
    zs = np.unique(np.r_[np.linspace(BC.Z0, c.z_fill, nz), BC.Z_SB, BC.Z_SH, c.z_c])
    R, F, S, L = [], [], [], []
    for z in zs:
        P, nf = c.ring(z, M=M)
        R.append(P)
        F.append(nf)
        out = P[nf:, :2]
        seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([P[nf - 1:nf, :2], out]), axis=0), axis=1))]
        s = np.r_[np.zeros(nf), seg[1:]]
        S.append(s)
        L.append(seg[-1])
    R = np.array(R)
    S = np.array(S)
    K, Mm = R.shape[:2]
    quads, cols = [], []
    zipdist = _zip_tree(c, b)
    for k in range(K - 1):
        for j in range(Mm):
            j2 = (j + 1) % Mm
            q = np.array([R[k, j], R[k, j2], R[k + 1, j2], R[k + 1, j]])
            cen = q.mean(0)
            frame = j < F[k] and j2 <= F[k]
            sc = 0.5 * (S[k, j] + S[k + 1, j])
            quads.append(q)
            fc = COLOUR_HOOK.get(c.key)
            cols.append(fc(c, b, C, cen, frame, sc, L[k], zipdist) if fc else
                        _face_colour(c, C, cen, frame, sc, L[k], zipdist))
    # bottom cap
    P0 = R[0]
    cen0 = P0.mean(0)
    for j in range(Mm):
        quads.append(np.array([cen0, P0[(j + 1) % Mm], P0[j], cen0]))
        cols.append(C["bottom"])
    if c.dome_h <= 0:      # closed top panel (MAW)
        P1 = R[-1]
        cen1 = P1.mean(0)
        for j in range(Mm):
            quads.append(np.array([cen1, P1[j], P1[(j + 1) % Mm], cen1]))
            cols.append(C["body"])
    soups = [{"quad": np.array(quads), "col": np.array(cols)}]
    if c.dome_h > 0:
        # closed roll at the fill line (camo hem band, as SPINE)
        a_f = float(np.interp(c.z_fill, *zip(*[(r[0], r[1]) for r in c.profile()])))
        yc = float(BC.y_frame([c.z_fill])[0]) + BC.D_TOP / 2
        soups.append(_roll(a_f + 40, yc, c.z_fill + 22, 30.0, C))
    if c.key in EXTRA_SOUPS:
        soups += EXTRA_SOUPS[c.key](c, b, C)
    return soups


def _zip_tree(c, b):
    from scipy.spatial import cKDTree
    pts = []
    if "zip3d" in b.extra:
        for P in b.extra["zip3d"]:
            P = np.asarray(P, float)
            if len(P) > 1:
                pts.append(np.vstack([np.linspace(P[i], P[i + 1], 6)[:-1] for i in range(len(P) - 1)] + [P[-1:]]))
        if not pts:
            return None
        P = np.vstack(pts)
        return cKDTree(P), P
    for z in b.zips:
        pts.append(_zip_path(c, b, z))
    if not pts:
        return None
    P = np.vstack(pts)
    return cKDTree(P), P


def _zip_path(c, b, z):
    if c.key == "slab":
        zz = np.linspace(140, 660, 200)
        return np.column_stack([np.zeros_like(zz), c.y_front(zz), zz])
    if c.key == "twin":
        zz = np.linspace(120, 700, 200)
        out = []
        for sgn in (1, -1):
            out.append(np.column_stack([sgn * c.a(zz), c.y_front(zz), zz]))
        return np.vstack(out[:1] if "R" in z["name"] else out[1:])
    if c.key == "hatch":
        H = BC.HATCH
        zz = np.linspace(H["z_lo"] + H["r"], H["z_hinge"], 120)
        pts = []
        for sgn in (1, -1):
            pts.append(np.column_stack([sgn * (c.a(zz) - H["inset"]), c.y_front(zz), zz]))
        x_c = float(c.a([H["z_lo"] + H["r"]])[0]) - H["inset"] - H["r"]
        th = np.linspace(0, np.pi / 2, 30)
        for sgn in (1, -1):
            x = sgn * (x_c + H["r"] * np.sin(th))
            zc = H["z_lo"] + H["r"] - H["r"] * np.cos(th)
            pts.append(np.column_stack([x, c.y_front(zc), zc]))
        xb = np.linspace(-x_c, x_c, 60)
        pts.append(np.column_stack([xb, np.full(60, float(c.y_front([H["z_lo"]])[0])), np.full(60, H["z_lo"])]))
        return np.vstack(pts)
    if c.key == "wrap":
        S = b.extra["surface"]
        uv = np.asarray(b.extra["split_uv"])
        uv = uv[uv[:, 0] >= BC.WRAP_ZIP["q_lo"] * BC.US - 1e-6]
        dense = np.vstack([np.linspace(uv[i], uv[i + 1], 6)[:-1] for i in range(len(uv) - 1)] + [uv[-1:]])
        return S(dense)
    raise KeyError(c.key)


def _face_colour(c, C, p, frame, s, L, zipdist):
    x, y, z = p
    if frame:
        return C["frame_panel"]
    a = float(c.a([min(z, c.z_c)])[0]) if z <= c.z_fill else 0.0
    zr = z - BC.Z0
    if zipdist is not None:
        tree, _ = zipdist
        dd, _ = tree.query(p)
        if dd < 7.0:
            return C["zip"]
    if z > c.z_fill - 4:
        return camo_at(C, s, z)
    if c.key in ("slab", "twin", "hatch"):
        d = float(c.depth([min(z, c.z_c)])[0])
        on_face = (s > d + 2) and (s < L - d - 2) and z < c.z_c + 1
        lim = 70 + (70 * (1 - abs(x) / max(a, 1)) if on_face else 0)
        if zr < lim:
            return camo_at(C, s, z)
        if c.key == "slab" and on_face and -56 < x < -7 and 120 < z < 680:
            return camo_at(C, s, z)
        if c.key == "twin" and on_face and 60 < z < 420 and abs(x) < a - 40:
            return camo_at(C, s, z) if z > 404 else C["band"]
        if c.key == "hatch" and on_face and abs(x) < 80 and 690 < z < 720:
            return camo_at(C, s, z)
        return C["body"]
    # wrap
    if zipdist is not None:
        tree, P = zipdist
        dd, i = tree.query(p)
        zp = P[i][2]
        if z < zp and dd < 100:
            return camo_at(C, s, z) if dd < 22 else C["band"]
    if zr < 60 + 90 * max(0, 1 - s / 160) or zr < 60 + 90 * max(0, 1 - (L - s) / 160):
        return camo_at(C, s, z)
    return C["body"]


def _roll(half_len, yc, zc, r, C, n=40, m=24):
    th = np.linspace(0, 2 * np.pi, m + 1)
    xs = np.linspace(-half_len, half_len, n)
    quads, cols = [], []
    for i in range(n - 1):
        for j in range(m):
            q = np.array([[xs[i], yc + r * np.cos(th[j]), zc + r * np.sin(th[j])],
                          [xs[i + 1], yc + r * np.cos(th[j]), zc + r * np.sin(th[j])],
                          [xs[i + 1], yc + r * np.cos(th[j + 1]), zc + r * np.sin(th[j + 1])],
                          [xs[i], yc + r * np.cos(th[j + 1]), zc + r * np.sin(th[j + 1])]])
            quads.append(q)
            cols.append(camo_at(C, xs[i] + 400, th[j] * 60))
    return {"quad": np.array(quads), "col": np.array(cols)}


def soup_from_tri(t, C):
    tri = t["tri"]
    if t["mat"] == "camo":
        cen = tri.mean(1)
        col = camo_at(C, cen[:, 0] + cen[:, 1], cen[:, 2])
    else:
        col = np.repeat(C[t["mat"]][None], len(tri), 0)
    return {"quad": np.concatenate([tri, tri[:, 2:3]], 1), "col": col}


# ============================================================================ renderer
VIEWS = {"q34": np.array([0.80, 1.05, 0.42]), "side": np.array([1.0, 0.0, 0.06])}
LIGHT = np.array([0.45, 0.75, 0.55])


def render(ax, soups, view, xlim=None, ylim=None):
    from matplotlib.collections import PolyCollection
    d = view / np.linalg.norm(view)
    up0 = np.array([0, 0, 1.0])
    r = np.cross(up0, d)
    r /= np.linalg.norm(r)
    up = np.cross(d, r)
    Q = np.concatenate([s["quad"] for s in soups])
    Cc = np.concatenate([s["col"] for s in soups])
    e1 = Q[:, 2] - Q[:, 0]
    e2 = Q[:, 3] - Q[:, 1]
    nrm = np.cross(e1, e2)
    nn = np.linalg.norm(nrm, axis=1)
    ok = nn > 1e-9
    Q, Cc, nrm, nn = Q[ok], Cc[ok], nrm[ok], nn[ok]
    nrm /= nn[:, None]
    L = LIGHT / np.linalg.norm(LIGHT)
    lam = np.abs(nrm @ L)
    head = np.abs(nrm @ d)
    shade = 0.38 + 0.42 * lam + 0.25 * head
    col = np.clip(Cc * shade[:, None], 0, 1)
    uv = np.stack([Q @ r, Q @ up], -1)
    depth = (Q @ d).mean(1)
    o = np.argsort(depth)
    pc = PolyCollection(uv[o], facecolors=col[o], edgecolors=col[o], linewidths=0.15, antialiased=True)
    ax.add_collection(pc)
    ax.set_aspect("equal")
    if xlim is None:
        allp = uv.reshape(-1, 2)
        xlim = (allp[:, 0].min() - 20, allp[:, 0].max() + 20)
        ylim = (allp[:, 1].min() - 20, allp[:, 1].max() + 20)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return xlim, ylim


def frame_extent(soups, view):
    d = view / np.linalg.norm(view)
    r = np.cross([0, 0, 1.0], d)
    r /= np.linalg.norm(r)
    up = np.cross(d, r)
    Q = np.concatenate([s["quad"].reshape(-1, 3) for s in soups])
    u, v = Q @ r, Q @ up
    return (u.min() - 30, u.max() + 30), (v.min() - 30, v.max() + 30)


# ============================================================================ flat pieces panel
MATCOL = {"challenge_ultra_200": "#6d7060", "cordura_330d_nylon66": "#a3a68f", "cordura_500d_nylon66": "#585a4c",
          "robic_100d_ripstop": "#c3c5b3", "hdpe_sheet": "#e8e8e0", "polyester_ht_630d_printable": "#ae9d6c",
          "poly_spandex_stretch_woven_printable": "#4f5a4d"}


def draw_flats(ax, b: BC.Build, title=True):
    from matplotlib.patches import Polygon as MP
    pieces = [(p, g) for p, g in b.pieces if g not in ("accent", "flat") and p.material_id != "hdpe_sheet"]
    pieces += [(p, g) for p, g in b.pieces if g in ("accent", "flat")]
    x0, y0, row_h, maxw = 0.0, 0.0, 0.0, 2300.0
    for p, g in pieces:
        cut = np.asarray(p.cut_polygon().exterior.coords)
        seam = np.asarray(p.seam_polygon().exterior.coords)
        mn, mx = cut.min(0), cut.max(0)
        w, h = mx - mn
        if w > h * 2.2 and w > 900:     # lay long strips (collar) flat as they come
            pass
        if x0 + w > maxw and x0 > 0:
            x0, y0, row_h = 0.0, y0 - row_h - 60, 0.0
        off = np.array([x0, y0 - h]) - mn
        ax.add_patch(MP(cut + off, closed=True, fc="none", ec="#444", lw=0.6, ls="--"))
        ax.add_patch(MP(seam + off, closed=True, fc=MATCOL.get(p.material_id, "#999"), ec="#222", lw=0.8))
        lab = (p.piece_id or "") + (f" x{p.quantity}" if p.quantity > 1 else "")
        cx, cy = (seam + off).mean(0)
        if w > 90 and h > 60:
            ax.text(cx, cy, lab, ha="center", va="center", fontsize=10, color="#111")
        x0 += w + 50
        row_h = max(row_h, h)
    ax.plot([0, 500], [y0 - row_h - 120] * 2, color="k", lw=3)
    ax.text(250, y0 - row_h - 110, "500 mm (19.7 in)", ha="center", va="bottom", fontsize=10)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")


# ============================================================================ sheets
def concept_sheet(key, row, b, soups_bag, ctx, C, lims, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    m, v, s = row["metrics"], row["volumes"], row["score"]
    fig = plt.figure(figsize=(16, 10), dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    a1 = fig.add_axes([0.0, 0.02, 0.36, 0.86])
    a2 = fig.add_axes([0.33, 0.02, 0.27, 0.86])
    a3 = fig.add_axes([0.61, 0.38, 0.38, 0.50])
    soups = soups_bag + [soup_from_tri(t, C) for t in ctx]
    render(a1, soups, VIEWS["q34"], *lims["q34"])
    render(a2, soups, VIEWS["side"], *lims["side"])
    a1.text(0.5, 0.01, "3/4 rear (bag side)", transform=a1.transAxes, ha="center", fontsize=13, color="#333")
    a2.text(0.5, 0.01, "side (wearer's right)", transform=a2.transAxes, ha="center", fontsize=13, color="#333")
    draw_flats(a3, b)
    a3.set_title("body pieces to scale (seam line filled, cut line dashed)", fontsize=12, color="#333")
    fig.text(0.015, 0.955, f"{NUM[key]}  {m['name']}" + ("  (released v3.1 baseline)" if key == "spine" else ""),
             fontsize=26, weight="bold", color="#222")
    fig.text(0.015, 0.915, row["tagline"], fontsize=15, color="#333")
    curved = f"{m['curved_seams']} curved ({m['curved_seam_length_m']:.1f} m)"
    lines = [
        f"Volume  {v['volume_L']:.1f} L / {v['volume_cu_in']:.0f} cu in (main bag to fill line)",
        f"Fill height  {v['fill_height_in']:.1f} in ({v['fill_height_mm']:.0f} mm)   depth max {v['max_depth_in']:.1f} in",
        f"Width  {v['width_max_in']:.1f} in    load CG  y {v['cg_y']:.0f} / z {v['cg_z']:.0f} mm",
        f"Pieces  {m['cut_pieces']}   seams {m['seam_length_m']:.1f} m, {curved}",
        f"Zips  {m['zips']} ({m['zip_length_m'] * 1000:.0f} mm #10)   swells: 8 {m['swells']['kind']}",
        f"Bag-body mass  {m['mass_g']['total']:.0f} g ({row['mass_delta_g']:+.0f} g vs SPINE)",
        f"Beginner hours  {m['hours_total']:.0f} h (ASSUMPTION model)",
        f"Weighted score  {s['weighted']:.2f} / 5",
    ]
    for i, t in enumerate(lines):
        fig.text(0.62, 0.33 - i * 0.038, t, fontsize=14, color="#222", weight="bold" if i == 7 else "normal")
    fig.text(0.62, 0.015, "Access: " + row["access"], fontsize=11, color="#444", wrap=True)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    _shrink(path)


def comparison_sheet(out, renders, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 9.5), dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    fig.text(0.015, 0.95, "Main-bag body: SPINE vs 4 alternatives (same frame, same 85.2 L, same 15.5 in width)",
             fontsize=21, weight="bold", color="#222")
    rows = out["rows"]
    for i, k in enumerate(ORDER):
        ax = fig.add_axes([i * 0.2, 0.30, 0.2, 0.62])
        img = plt.imread(renders[k])
        ax.imshow(img)
        ax.axis("off")
        r = rows[k]
        ax.set_title(f"{NUM[k]} {r['metrics']['name']}", fontsize=18, weight="bold", color="#222")
    cols = ["", "L", "fill in", "pieces", "seams m", "curved", "zip mm", "body g", "hours", "CG y/z", "score"]
    cells = []
    for k in ORDER:
        r = rows[k]
        m, v = r["metrics"], r["volumes"]
        cells.append([m["name"], f"{v['volume_L']:.1f}", f"{v['fill_height_in']:.1f}", f"{m['cut_pieces']}",
                      f"{m['seam_length_m']:.1f}", f"{m['curved_seams']}", f"{m['zip_length_m'] * 1000:.0f}",
                      f"{m['mass_g']['total']:.0f} ({r['mass_delta_g']:+.0f})", f"{m['hours_total']:.0f}",
                      f"{v['cg_y']:.0f}/{v['cg_z']:.0f}", f"{r['score']['weighted']:.2f}"])
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.26])
    ax.axis("off")
    t = ax.table(cellText=cells, colLabels=cols, loc="center", cellLoc="center")
    t.auto_set_font_size(False)
    t.set_fontsize(14)
    t.scale(1, 2.0)
    best = max(ORDER, key=lambda k: rows[k]["score"]["weighted"])
    for (ri, ci), cell in t.get_celld().items():
        cell.set_edgecolor("#bbb")
        if ri == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#e2e0d8")
        elif ORDER[ri - 1] == best:
            cell.set_facecolor("#dfe8d4")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    _shrink(path)


def hours_chart(out, path):
    """Horizontal stacked bars: beginner hours by operation group (default categorical palette, validated)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = {"curved seams + swells": ("curved seams", "swells"), "straight seams, pivots, rings": (
        "straight seams", "pivots", "ring seams", "darts"), "zips": ("zips",), "cutting + camo": ("cutting", "camo applique")}
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    rows = out["rows"]
    fig, ax = plt.subplots(figsize=(14, 6.5), dpi=100)
    fig.patch.set_facecolor("white")
    ys = np.arange(len(ORDER))[::-1]
    for y, k in zip(ys, ORDER):
        h = rows[k]["metrics"]["hours"]
        left = 0.0
        for (g, keys), c in zip(groups.items(), pal):
            w = sum(h[kk] for kk in keys)
            ax.barh(y, w, left=left, color=c, height=0.6, edgecolor="white", linewidth=2, label=g if y == ys[0] else None)
            left += w
        ax.text(left + 0.4, y, f"{left:.0f} h", va="center", fontsize=14, color="#222")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{NUM[k]} {rows[k]['metrics']['name']}" for k in ORDER], fontsize=15)
    ax.set_xlabel("estimated beginner sewing hours, main-bag body only (ASSUMPTION rates)", fontsize=13)
    ax.tick_params(axis="x", labelsize=12)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#e5e5e5")
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=12, frameon=False)
    ax.set_title("Where the build time goes: curves and cone swells dominate SPINE", fontsize=17, loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    _shrink(path)


def _shrink(path, max_bytes=1_500_000):
    from PIL import Image
    path = Path(path)
    if path.stat().st_size <= max_bytes:
        return
    im = Image.open(path).convert("RGB")
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
    if path.stat().st_size > max_bytes:
        im = im.resize((int(im.width * 0.8), int(im.height * 0.8)))
        im.quantize(colors=256).save(path, optimize=True)


def render_all(out, builds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C = colours()
    ctx, spine = load_context()
    bags = {"spine": [soup_from_tri(t, C) for t in spine]}
    for k in ORDER[1:]:
        bags[k] = concept_soup(builds[k].concept, builds[k], C)
    ctx_soups = [soup_from_tri(t, C) for t in ctx]
    allsoups = [s for k in ORDER for s in bags[k]] + ctx_soups
    lims = {v: frame_extent(allsoups, VIEWS[v]) for v in VIEWS}
    SCREENS.mkdir(parents=True, exist_ok=True)
    files, renders = [], {}
    for k in ORDER:
        p = SCREENS / f"{DATE}_bagalt_{NUM[k]}.png"
        concept_sheet(k, out["rows"][k], builds[k], bags[k], ctx, C, lims, p)
        files.append(p)
        # single 3/4 render for the comparison sheet
        fig = plt.figure(figsize=(4, 6.2), dpi=110)
        ax = fig.add_axes([0, 0, 1, 1])
        render(ax, bags[k] + ctx_soups, VIEWS["q34"], *lims["q34"])
        rp = SCREENS / f"_tmp_bagalt_{k}.png"
        fig.savefig(rp, facecolor="#f4f3ef")
        plt.close(fig)
        renders[k] = rp
    p6 = SCREENS / f"{DATE}_bagalt_6.png"
    comparison_sheet(out, renders, p6)
    p7 = SCREENS / f"{DATE}_bagalt_7.png"
    hours_chart(out, p7)
    for rp in renders.values():
        rp.unlink()
    files += [p6, p7]
    DOCS.mkdir(parents=True, exist_ok=True)
    for n in (6, 7, 4, 2):
        shutil.copy2(SCREENS / f"{DATE}_bagalt_{n}.png", DOCS / f"{DATE}_bagalt_{n}.png")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    out, builds = run_study()
    for k in ORDER:
        r = out["rows"][k]
        print(k, r["volumes"]["volume_L"], r["metrics"]["cut_pieces"], r["metrics"]["hours_total"],
              r["metrics"]["mass_g"]["total"], r["mass_delta_g"], r["score"])
    if not a.no_render:
        for f in render_all(out, builds):
            print("PNG", f, f"{f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
