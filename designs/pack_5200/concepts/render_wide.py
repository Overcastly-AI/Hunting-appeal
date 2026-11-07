"""Render and score ALL bag-body concepts (1-5 from bag_concepts, 6-13 from bag_concepts_wide).

    python designs/pack_5200/concepts/render_wide.py              # ~6 min: metrics, JSON, every PNG
    python designs/pack_5200/concepts/render_wide.py --no-render

PNGs (phone-readable, <= 1.5 MB) in outputs/screens/:
  20261107_bagalt_1..5   concept sheets 1-5 (re-scored across all 13)
  20261107_bagalt_6, _7  the first comparison (5 concepts) and its hours chart, as before
  20261107_bagalt_8..15  concept sheets 6-13
  20261107_bagalt_16, 17 gallery sheets (concepts 1-7, 8-13) with a one-line pitch each
  20261107_bagalt_18     score table, all 13
  20261107_bagalt_19     beginner hours, all 13
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
import render_concepts as R  # noqa: E402

ORDER = ["spine", "slab", "twin", "wrap", "hatch", "spire", "cradle", "duo", "gulp", "maw", "cairn", "wisp", "mantle"]
CNUM = {k: i + 1 for i, k in enumerate(ORDER)}
PNG = {"spine": 1, "slab": 2, "twin": 3, "wrap": 4, "hatch": 5, "spire": 8, "cradle": 9, "duo": 10, "gulp": 11,
       "maw": 12, "cairn": 13, "wisp": 14, "mantle": 15}
PITCH = {"spine": "Released teardrop: diagonal zip under a stretch band, gores and cone swells",
         "slab": "Tapered flat-panel box, one straight centre zip, nothing curved",
         "twin": "Box with a zip in each corner seam and a flat stretch pocket",
         "wrap": "SPINE look from one wrap panel; diagonal zip cut straight on the flat",
         "hatch": "Box with a horseshoe-zip door under the roll-top",
         **{k: v["pitch"] for k, v in W.WIDE.items()}}
NOTES = {  # look / feature notes for the score table (judgement, see analysis/bag_alternatives.md)
    "spine": "slim teardrop; band pocket; best look",
    "slab": "boxy; no overload pocket",
    "twin": "boxy; stretch pocket; 2 zips",
    "wrap": "SPINE-like; band pocket",
    "hatch": "boxy; full view; long zip",
    "spire": "torpedo; tall 47 in; CG closest",
    "cradle": "modular drybags; open sides",
    "duo": "sleep zone + door; divider",
    "gulp": "9 L stretch pocket; side zip",
    "maw": "duffel opening; no roll-top",
    "cairn": "6 L summit-pack lid",
    "wisp": "UL minimal; no zip at all",
    "mantle": "side wings; heavy",
}
SCREENS = R.SCREENS
DOCS = R.DOCS
RESULTS = HERE / "concepts_results.json"


# ============================================================================ study
def run_all():
    out, builds = R.run_study()          # 1-5 (writes the JSON; overwritten below with all 13)
    rows = out["rows"]
    for c in W.all_wide():
        b = W.build(c)
        rows[c.key] = {"metrics": BC.metrics(b), "volumes": W.volumes(c), "tagline": c.tagline, "access": c.access,
                       "pitch": PITCH[c.key], "interface_changes": W.INTERFACE_CHANGES[c.key],
                       "extra": {k: v for k, v in b.extra.items() if k in ("collar_perimeter_mm", "pocket_L", "lid_L",
                                                                            "common_delta_g", "hardware")}}
        builds[c.key] = b
    sc = BC.score(rows)
    base = rows["spine"]["metrics"]["mass_g"]["total"]
    for k in rows:
        rows[k]["score"] = sc[k]
        rows[k]["mass_delta_g"] = round(rows[k]["metrics"]["mass_g"]["total"] - base, 1)
        rows[k]["pack_g"] = round(BC.PACK_TOTAL_G + rows[k]["mass_delta_g"], 1)
        rows[k]["number"] = CNUM[k]
        rows[k].setdefault("pitch", PITCH[k])
        rows[k].setdefault("interface_changes", "none")
        rows[k]["note"] = NOTES[k]
    out["rows"] = {k: rows[k] for k in ORDER}
    out["order"] = ORDER
    RESULTS.write_text(json.dumps(out, indent=1, default=R._np))
    return out, builds


# ============================================================================ colours + extra meshes
def _q(s, L):
    return s / max(L, 1e-6)


def colour_wide(c, b, C, p, frame, s, L, zipdist):
    x, y, z = p
    if frame:
        return C["frame_panel"]
    zr = z - BC.Z0
    if zipdist is not None:
        tree, P = zipdist
        dd, i = tree.query(p)
        if dd < 7.0:
            return C["zip"]
        near_zip = dd
    else:
        near_zip = 1e9
    if c.dome_h > 0 and z > c.z_fill - 4:
        return R.camo_at(C, s, z)
    q = _q(s, L)
    if c.kind == "box":
        d = float(c.depth([min(z, c.z_c)])[0])
        a = float(c.a([min(z, c.z_c)])[0])
        on_face = (s > d + 2) and (s < L - d - 2) and z < c.z_c + 1
        if zr < 70 + (70 * (1 - abs(x) / max(a, 1)) if on_face else 0):
            return R.camo_at(C, s, z)
        if c.key == "mantle" and on_face and -57 < x < -7 and 120 < z < 680:
            return R.camo_at(C, s, z)
        if c.key == "maw" and z > c.z_c - 90 and abs(abs(x) - a) < 120 and on_face:
            return R.camo_at(C, s, z)
        return C["body"]
    if zr < 80:
        return R.camo_at(C, s, z)
    if c.key == "spire" and near_zip < 26 and x < 0:
        return R.camo_at(C, s, z)
    if c.key == "duo" and near_zip < 24 and z < 330:
        return R.camo_at(C, s, z)
    if c.key == "gulp" and 0.18 < q < 0.82 and 80 < z < 630:
        return R.camo_at(C, s, z) if z > 612 else C["band"]
    return C["body"]


def _grid_quads(fn, nu, nv):
    """fn(u, v) -> xyz for u, v in [0, 1]; returns quads (nu x nv)."""
    u = np.linspace(0, 1, nu + 1)
    v = np.linspace(0, 1, nv + 1)
    P = np.array([[fn(uu, vv) for vv in v] for uu in u])
    Q = []
    for i in range(nu):
        for j in range(nv):
            Q.append([P[i, j], P[i + 1, j], P[i + 1, j + 1], P[i, j + 1]])
    return np.array(Q)


def _cyl_x(x0, x1, yc, zc, r, nx=24, nt=40):
    return _grid_quads(lambda u, v: np.array([x0 + (x1 - x0) * u, yc + r * np.cos(2 * np.pi * v),
                                              zc + r * np.sin(2 * np.pi * v)]), nx, nt)


def _disk_x(x, yc, zc, r, nt=40):
    th = np.linspace(0, 2 * np.pi, nt + 1)
    return np.array([[[x, yc, zc], [x, yc + r * np.cos(th[j]), zc + r * np.sin(th[j])],
                      [x, yc + r * np.cos(th[j + 1]), zc + r * np.sin(th[j + 1])], [x, yc, zc]] for j in range(nt)])


def _soup(Q, col):
    Q = np.asarray(Q)
    col = np.asarray(col)
    if col.ndim == 1:
        col = np.repeat(col[None], len(Q), 0)
    return {"quad": Q, "col": col}


def cradle_soup(c, b, C):
    soups = []
    top = c.z_c
    a_of = lambda z: float(c.a([min(z, BC.Z_SH)])[0])          # noqa: E731
    yf = lambda z: float(BC.y_frame([z])[0])                   # noqa: E731
    back = _grid_quads(lambda u, v: np.array([(-1 + 2 * u) * a_of(BC.Z0 + v * (top - BC.Z0)),
                                              yf(BC.Z0 + v * (top - BC.Z0)) - 1, BC.Z0 + v * (top - BC.Z0)]), 20, 60)
    soups.append(_soup(back, C["frame_panel"]))
    for sg in (1, -1):
        wing = _grid_quads(lambda u, v, sg=sg: np.array([sg * (a_of(BC.Z0 + 30 + v * (top - 90 - BC.Z0)) + 2),
                                                         yf(BC.Z0 + 30 + v * (top - 90 - BC.Z0)) + 130 * u,
                                                         BC.Z0 + 30 + v * (top - 90 - BC.Z0)]), 6, 40)
        cols = [R.camo_at(C, q[0][1] * 3, q[0][2]) if q[:, 1].max() - yf(q[0][2]) > 112 else C["body"] for q in wing]
        soups.append(_soup(wing, cols))
    cup = _grid_quads(lambda u, v: np.array([(-1 + 2 * u) * BC.A_BOT, yf(BC.Z0) + 160 * v, BC.Z0 - 2]), 10, 6)
    soups.append(_soup(cup, C["bottom"]))
    lip = _grid_quads(lambda u, v: np.array([(-1 + 2 * u) * BC.A_BOT, yf(BC.Z0) + 160, BC.Z0 + 80 * v]), 10, 4)
    soups.append(_soup(lip, [R.camo_at(C, q[0][0] + 300, q[0][2]) for q in lip]))
    for D, zc in c.stack():
        yc = yf(zc) + D / 2 + 3
        x0 = -BC.A_MAX + 3                     # drybag body + 55 mm rolled end stay inside 15.5 in
        x1 = x0 + W.CRADLE_L
        soups.append(_soup(_cyl_x(x0, x1, yc, zc, D / 2), C["body"]))
        soups.append(_soup(_disk_x(x0, yc, zc, D / 2), C["body"] * 0.9))
        roll = _cyl_x(x1, x1 + 55, yc, zc, D / 2 * 0.55, 6, 30)
        soups.append(_soup(roll, [R.camo_at(C, q[0][1] * 2, q[0][2] * 2) for q in roll]))
        soups.append(_soup(_disk_x(x1 + 55, yc, zc, D / 2 * 0.55), C["trim"]))
        for xs in (-110, 90):
            soups.append(_soup(_cyl_x(xs, xs + 25, yc, zc, D / 2 + 2.5, 1, 40), C["webbing"]))
    return soups


def cairn_extra(c, b, C):
    from huntkit.viz3d import geom as G
    yc = float(BC.y_frame([c.z_fill])[0]) + 95
    m = G.superellipsoid([0, yc, c.z_fill + 70], [205, 150, 48], e_ns=0.5, e_ew=0.6)
    tri = m.vertices[m.faces]
    cen = tri.mean(1)
    cols = np.array([R.camo_at(C, cc[0] + 500, cc[1] * 2) if cc[2] > c.z_fill + 78 else C["body"] for cc in cen])
    out = [{"quad": np.concatenate([tri, tri[:, 2:3]], 1), "col": cols}]
    # lid zip line round the gusset top
    th = np.linspace(0, 2 * np.pi, 120)
    ring = np.column_stack([206 * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** 0.6, yc + 151 * np.sign(np.sin(th)) *
                            np.abs(np.sin(th)) ** 0.6, np.full(120, c.z_fill + 80)])
    out.append(_soup([[ring[i], ring[i + 1], ring[i + 1] + [0, 0, 6], ring[i] + [0, 0, 6]] for i in range(119)],
                     C["zip"]))
    return out


def mantle_extra(c, b, C):
    out = []
    yf = lambda z: float(BC.y_frame([z])[0])                   # noqa: E731
    z0, z1 = 80.0, 780.0
    for sg in (1, -1):
        def fn(u, v, sg=sg):
            z = z0 + v * (z1 - z0)
            w = 230 + 20 * v
            return np.array([sg * (float(c.a([min(z, c.z_c)])[0]) + 7), yf(z) + 12 + w * u, z])
        Q = _grid_quads(fn, 10, 40)
        cols = []
        for q in Q:
            u_edge = np.max(q[:, 1]) - yf(q[0][2]) > 12 + 215
            cols.append(R.camo_at(C, q[0][1] * 3, q[0][2]) if (u_edge or q[0][2] < z0 + 20 or q[0][2] > z1 - 30)
                        else C["body"] * 0.93)
        out.append(_soup(Q, cols))
        for zs in (240.0, 450.0, 660.0):
            a = float(c.a([zs])[0])
            yb = float(c.y_front([zs])[0])
            ya = yf(zs) + 12 + 240
            P0 = np.array([sg * (a + 8), ya, zs])
            P1 = np.array([sg * (a + 8), yb + 3, zs])
            P2 = np.array([sg * (a - 70), yb + 3, zs])
            for A_, B_ in ((P0, P1), (P1, P2)):
                out.append(_soup([[A_, B_, B_ + [0, 0, 25], A_ + [0, 0, 25]]], C["webbing"]))
    return out


R.COLOUR_HOOK.update({k: colour_wide for k in W.WIDE if k != "cradle"})
R.CUSTOM_SOUP["cradle"] = cradle_soup
R.EXTRA_SOUPS.update({"cairn": cairn_extra, "mantle": mantle_extra})


# ============================================================================ sheets
def gallery(out, renders, keys, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    n = len(keys)
    cols = 4 if n > 6 else 3
    rows = int(np.ceil(n / cols))
    fig = plt.figure(figsize=(16, 6.2 * rows + 0.9), dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    fig.text(0.012, 1 - 0.45 / (6.2 * rows + 0.9), title, fontsize=22, weight="bold", color="#222", va="top")
    H = 6.2 * rows + 0.9
    for i, k in enumerate(keys):
        r_, c_ = divmod(i, cols)
        x0 = c_ / cols
        y0 = 1 - (0.9 + (r_ + 1) * 6.2) / H
        ax = fig.add_axes([x0 + 0.005, y0 + 1.25 / H, 1 / cols - 0.01, 4.35 / H])
        ax.imshow(plt.imread(renders[k]))
        ax.axis("off")
        row = out["rows"][k]
        m, v = row["metrics"], row["volumes"]
        fig.text(x0 + 0.5 / cols, y0 + 6.05 / H, f"{CNUM[k]}  {m['name']}", ha="center", va="top", fontsize=19,
                 weight="bold", color="#222")
        import textwrap
        fig.text(x0 + 0.5 / cols, y0 + 1.15 / H, "\n".join(textwrap.wrap(row["pitch"], 40 if cols == 4 else 52)),
                 ha="center", va="top", fontsize=12.5, color="#333")
        fig.text(x0 + 0.5 / cols, y0 + 0.42 / H,
                 f"{v['volume_L']:.1f} L  {v['fill_height_in']:.1f} in tall  {row['mass_delta_g']:+.0f} g  "
                 f"{m['hours_total']:.0f} h", ha="center", va="top", fontsize=12, color="#555")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    R._shrink(path)


def score_table(out, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hdr = ["#", "concept", "L", "fill in", "mass Δ g", "pieces", "curved", "zips (mm)", "hours", "access",
           "CG y/z mm", "look / feature", "score"]
    cells = []
    rows = out["rows"]
    for k in ORDER:
        r = rows[k]
        m, v, s = r["metrics"], r["volumes"], r["score"]
        z = f"{m['zips']} ({m['zip_length_m'] * 1000:.0f})" if m["zips"] else "0"
        cells.append([str(CNUM[k]), m["name"], f"{v['volume_L']:.1f}", f"{v['fill_height_in']:.1f}",
                      f"{r['mass_delta_g']:+.0f}", str(m["cut_pieces"]), str(m["curved_seams"]), z,
                      f"{m['hours_total']:.0f}", f"{s['access']:.1f}", f"{v['cg_y']:.0f}/{v['cg_z']:.0f}", r["note"],
                      f"{s['weighted']:.2f}"])
    fig = plt.figure(figsize=(16, 9.6), dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    fig.text(0.012, 0.965, "All 13 bag bodies: same frame interface, 85 L, 15.5 in wide", fontsize=21, weight="bold",
             color="#222")
    fig.text(0.012, 0.925, "score = build 0.35, mass 0.15, access 0.15, carry 0.15, durability 0.10, look 0.10 "
             "(hours are an ASSUMPTION model; access / durability / look are judgements)", fontsize=12, color="#444")
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.88])
    ax.axis("off")
    t = ax.table(cellText=cells, colLabels=hdr, loc="upper center", cellLoc="center",
                 colWidths=[0.03, 0.08, 0.05, 0.05, 0.07, 0.05, 0.05, 0.08, 0.05, 0.055, 0.08, 0.22, 0.055])
    t.auto_set_font_size(False)
    t.set_fontsize(13.5)
    t.scale(1, 3.3)
    for (ri, ci), cell in t.get_celld().items():
        cell.set_edgecolor("#bbb")
        if ri == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#e2e0d8")
        elif ri % 2 == 0:
            cell.set_facecolor("#fbfaf7")
        if ci == 11 and ri > 0:
            cell.set_text_props(ha="left")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    R._shrink(path)


def hours_all(out, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = {"curved seams + swells": ("curved seams", "swells"),
              "straight seams, pivots, rings": ("straight seams", "pivots", "ring seams", "darts"),
              "zips + hardware": ("zips", "hardware bartacks"), "cutting + camo": ("cutting", "camo applique")}
    pal = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    rows = out["rows"]
    fig, ax = plt.subplots(figsize=(14, 9), dpi=100)
    ys = np.arange(len(ORDER))[::-1]
    for y, k in zip(ys, ORDER):
        h = rows[k]["metrics"]["hours"]
        left = 0.0
        for (g, keys), col in zip(groups.items(), pal):
            w = sum(h.get(kk, 0.0) for kk in keys)
            ax.barh(y, w, left=left, color=col, height=0.62, edgecolor="white", linewidth=2,
                    label=g if y == ys[0] else None)
            left += w
        ax.text(left + 0.3, y, f"{left:.0f} h", va="center", fontsize=13, color="#222")
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{CNUM[k]} {rows[k]['metrics']['name']}" for k in ORDER], fontsize=14)
    ax.set_xlabel("estimated beginner sewing hours, bag body (ASSUMPTION rates)", fontsize=13)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#e5e5e5")
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=12, frameon=False)
    ax.set_title("Sewing effort, all 13 concepts", fontsize=17, loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    R._shrink(path)


def render_everything(out, builds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C = R.colours()
    ctx, spine = R.load_context()
    bags = {"spine": [R.soup_from_tri(t, C) for t in spine]}
    for k in ORDER[1:]:
        bags[k] = R.concept_soup(builds[k].concept, builds[k], C)
    ctx_soups = [R.soup_from_tri(t, C) for t in ctx]
    allsoups = [s for k in ORDER for s in bags[k]] + ctx_soups
    lims = {v: R.frame_extent(allsoups, R.VIEWS[v]) for v in R.VIEWS}
    R.NUM.update(CNUM)
    files, renders = [], {}
    for k in ORDER:
        p = SCREENS / f"{R.DATE}_bagalt_{PNG[k]}.png"
        R.concept_sheet(k, out["rows"][k], builds[k], bags[k], ctx, C, lims, p)
        files.append(p)
        fig = plt.figure(figsize=(4, 5.6), dpi=110)
        ax = fig.add_axes([0, 0, 1, 1])
        R.render(ax, bags[k] + ctx_soups, R.VIEWS["q34"], *lims["q34"])
        rp = SCREENS / f"_tmp_bagalt_{k}.png"
        fig.savefig(rp, facecolor="#f4f3ef")
        plt.close(fig)
        renders[k] = rp
    # the first 5-concept comparison and hours chart, regenerated with the re-scored numbers
    first = {"rows": {k: out["rows"][k] for k in R.ORDER}}
    R.comparison_sheet(first, renders, SCREENS / f"{R.DATE}_bagalt_6.png")
    R.hours_chart(first, SCREENS / f"{R.DATE}_bagalt_7.png")
    g1 = SCREENS / f"{R.DATE}_bagalt_16.png"
    g2 = SCREENS / f"{R.DATE}_bagalt_17.png"
    gallery(out, renders, ORDER[:7], g1, "Bag bodies 1-7 (same frame, 85 L, 15.5 in wide; 3/4 rear view)")
    gallery(out, renders, ORDER[7:], g2, "Bag bodies 8-13 (same frame, 85 L, 15.5 in wide; 3/4 rear view)")
    t = SCREENS / f"{R.DATE}_bagalt_18.png"
    score_table(out, t)
    h = SCREENS / f"{R.DATE}_bagalt_19.png"
    hours_all(out, h)
    for rp in renders.values():
        rp.unlink()
    files += [SCREENS / f"{R.DATE}_bagalt_6.png", SCREENS / f"{R.DATE}_bagalt_7.png", g1, g2, t, h]
    for n in (16, 17, 18, 9, 13):
        shutil.copy2(SCREENS / f"{R.DATE}_bagalt_{n}.png", DOCS / f"{R.DATE}_bagalt_{n}.png")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    out, builds = run_all()
    for k in ORDER:
        r = out["rows"][k]
        print(f"{CNUM[k]:2d} {k:7s} {r['volumes']['volume_L']:6.2f} L {r['volumes']['fill_height_in']:5.1f} in "
              f"{r['mass_delta_g']:+6.1f} g pcs {r['metrics']['cut_pieces']} curved {r['metrics']['curved_seams']} "
              f"h {r['metrics']['hours_total']} score {r['score']['weighted']}")
    if not a.no_render:
        for f in render_everything(out, builds):
            print("PNG", f, f"{f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
