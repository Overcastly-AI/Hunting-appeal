"""Renders of CORRIE on the 19 in frame + mannequin (same painter, light and colourway as the concept sheets).

    python designs/pack_5200/concepts/corrie_render.py      # ~3 min, writes outputs/screens/20261107_corrie_<n>.png

1 3/4 rear  2 side  3 door open (interior, IM1-IM3)  4 wings cinched on a tripod  5 top pouch close-up
6 float meat mode (bag hung 170 mm aft on the B-24 links, quarter in the cradle)  7 pieces + numbers sheet
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
import render_concepts as R  # noqa: E402
import render_wide as RW  # noqa: E402

ROOT = HERE.parents[2]
DATE = "20261107"
OUT = R.SCREENS
FLOAT_GAP = 170.0
FLOAT_PARTS = ["quarter_float_g170", "quarter_bone_float_g170", "meat_straps_float_g170", "meat_hardware_float_g170",
               "cradle_straps_float_g170", "float_links_g170", "float_link_hooks_g170", "haul_wraps_meat_g170",
               "crown_wrap_meat_full_g170@t19", "crown_hood_open@t19"]
BONE = R._rgb("#cfc6b0")


def load_parts():
    from huntkit.viz3d.model import build_pack
    from huntkit.viz3d.params import load_params
    pk = build_pack(load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml")))
    by = {p.name: p for p in pk.parts}
    carry = [R._soup(by[n], 18000 if n in ("frame_generative", "mannequin@t19") else 6000) for n in R.CONTEXT if n in by]
    float_ctx = [R._soup(by[n], 18000 if n in ("frame_generative", "mannequin@t19") else 6000)
                 for n in R.CONTEXT if n in by and n not in ("under_straps", "crown_hood@t19")]
    float_ctx += [R._soup(by[n], 8000) for n in FLOAT_PARTS if n in by]
    return carry, float_ctx


# ============================================================================ bag soups
def colour(c, b, C, p, frame, s, L, zipdist):
    x, y, z = p
    if frame:
        return C["frame_panel"]
    if zipdist is not None:
        dd, _ = zipdist[0].query(p)
        if dd < 7.0:
            return C["zip"]
    if z > c.z_fill - 4:
        return R.camo_at(C, s, z)
    d = float(c.depth([min(z, c.z_c)])[0])
    a = float(c.a([min(z, c.z_c)])[0])
    on_face = (s > d + 2) and (s < L - d - 2) and z < c.z_c + 1
    zr = z - BC.Z0
    if zr < 70 + (70 * (1 - abs(x) / max(a, 1)) if on_face else 0):
        return R.camo_at(C, s, z)
    if on_face and abs(abs(x) - (a - CO.DOOR["inset"])) < 22 and CO.DOOR["z_hinge"] - 55 < z < CO.DOOR["z_hinge"] + 5:
        return R.camo_at(C, s, z)          # zip garages
    if on_face and abs(abs(x) - CO.B22_X) < 25 and abs(z - CO.B22_Z) < 30:
        return C["hypalon"]                # B-22 guy tabs on the hinge band
    return C["body"]


def door_paths(c):
    H = CO.DOOR
    zz = np.linspace(H["z_lo"] + H["r"], H["z_hinge"], 120)
    pts = []
    for sg in (1, -1):
        pts.append(np.column_stack([sg * (c.a(zz) - H["inset"]), c.y_front(zz) + 0.5, zz]))
    x_c = float(c.a([H["z_lo"] + H["r"]])[0]) - H["inset"] - H["r"]
    th = np.linspace(0, np.pi / 2, 30)
    for sg in (1, -1):
        x = sg * (x_c + H["r"] * np.sin(th))
        zc = H["z_lo"] + H["r"] - H["r"] * np.cos(th)
        pts.append(np.column_stack([x, c.y_front(zc) + 0.5, zc]))
    xb = np.linspace(-x_c, x_c, 60)
    pts.append(np.column_stack([xb, np.full(60, float(c.y_front([H["z_lo"]])[0]) + 0.5), np.full(60, H["z_lo"])]))
    return pts


def in_door(c, p):
    x, y, z = p
    H = CO.DOOR
    if not (H["z_lo"] < z < H["z_hinge"]):
        return False
    if abs(y - float(c.y_front([z])[0])) > 6:
        return False
    a = float(c.a([z])[0]) - H["inset"]
    if abs(x) > a:
        return False
    if z < H["z_lo"] + H["r"] and abs(x) > a - H["r"]:
        dx = abs(x) - (a - H["r"])
        dz = (H["z_lo"] + H["r"]) - z
        return dx * dx + dz * dz < H["r"] ** 2
    return True


def orient_outward(c, soup):
    Q = soup["quad"]
    cen = Q.mean(1)
    yc = np.array([float(BC.y_frame([z])[0]) + float(c.depth([min(z, c.z_c)])[0]) / 2 for z in cen[:, 2]])
    radial = cen - np.column_stack([np.zeros(len(cen)), yc, cen[:, 2]])
    n = np.cross(Q[:, 2] - Q[:, 0], Q[:, 3] - Q[:, 1])
    flip = np.einsum("ij,ij->i", n, radial) < 0
    Q[flip] = Q[flip][:, ::-1]
    soup["quad"] = Q
    return soup


def wing_soup(c, C, tripod=False):
    out = []
    yf = lambda z: float(BC.y_frame([z])[0])           # noqa: E731
    z0, z1 = 150.0, 600.0
    for sg in (1, -1):
        bulge = tripod and sg == 1
        ytri = None

        def fn(u, v, sg=sg, bulge=bulge):
            z = z0 + v * (z1 - z0)
            yy = yf(z) + 12 + 200 * u
            xa = float(c.a([z])[0]) + 7
            if bulge:
                yt = yf(z) + 115
                xa += 40 * max(0.0, 1 - ((yy - yt) / 70) ** 2) ** 0.5
            return np.array([sg * xa, yy, z])
        Q = RW._grid_quads(fn, 12, 36)
        cols = []
        for q in Q:
            edge = np.max(q[:, 1]) - yf(q[0][2]) > 12 + 185
            cols.append(R.camo_at(C, q[0][1] * 3, q[0][2]) if edge else C["harness"] * 1.15)
        out.append(RW._soup(Q, cols))
        for zs in (260.0, 490.0):          # 2 straps: wing aft edge -> loop in the aft corner seam
            a = float(c.a([zs])[0])
            ye = yf(zs) + 212
            yb = float(c.y_front([zs])[0])
            P0 = np.array([sg * (a + 9), ye - 20, zs])
            P1 = np.array([sg * (a + 4), yb - 2, zs])
            out.append(RW._soup([[P0, P1, P1 + [0, 0, 25], P0 + [0, 0, 25]]], C["webbing"]))
            out.append(RW._soup([[P0 + [0, -12, -3], P0 + [0, 6, -3], P0 + [0, 6, 28], P0 + [0, -12, 28]]], C["metal"]))
    if tripod:
        a = float(c.a([400])[0])
        for dy, dz in ((-14, 0), (14, 0), (0, 22)):
            xa = a + 30
            yt = yf(400) + 115 + dy
            Q = RW._grid_quads(lambda u, v, xa=xa, yt=yt: np.array([xa + 11 * np.cos(2 * np.pi * u),
                                                                    yt + 11 * np.sin(2 * np.pi * u), 90 + 760 * v]), 16, 6)
            out.append(RW._soup(Q, C["hardware"]))
        head = RW._grid_quads(lambda u, v: np.array([a + 30 + 30 * (u - .5), yf(850) + 115 + 30 * (v - .5), 862]), 2, 2)
        out.append(RW._soup(head, C["hardware"]))
    return out


def pouch_soup(c, C):
    P = CO.POUCH
    z0 = c.z_fill + 22 + 18                         # sits on the closed roll (roll centre z_fill + 22, r 30, squashed)
    y0 = float(BC.y_frame([c.z_fill])[0]) + BC.D_TOP / 2 - P["W"] / 2 + 15   # centred on the roll, 15 mm aft
    x0 = -P["L"] / 2
    L_, W_, H_ = P["L"], P["W"], P["H"]
    faces = [  # (origin, u-vector, v-vector, camo?)
        ((x0, y0, z0 + H_), (L_, 0, 0), (0, W_, 0), True),          # top (camo)
        ((x0, y0, z0), (0, W_, 0), (L_, 0, 0), False),               # base
        ((x0, y0, z0), (L_, 0, 0), (0, 0, H_), False),               # frame side
        ((x0, y0 + W_, z0), (0, 0, H_), (L_, 0, 0), False),          # aft side (zip)
        ((x0, y0, z0), (0, 0, H_), (0, W_, 0), False),               # left end
        ((x0 + L_, y0, z0), (0, W_, 0), (0, 0, H_), False),          # right end
    ]
    out = []
    for o, u, v, camo in faces:
        o, u, v = (np.asarray(t, float) for t in (o, u, v))
        Q = RW._grid_quads(lambda a, bb, o=o, u=u, v=v: o + a * u + bb * v, 16, 10)
        cols = [R.camo_at(C, q.mean(0)[0] + 900, q.mean(0)[1] * 1.0) if camo else C["body"] for q in Q]
        out.append(RW._soup(Q, cols))
    ya = y0 + P["W"] + 1
    zz = z0 + P["H"] * 0.82
    xs = np.linspace(-150, 150, 40)
    out.append(RW._soup([[[xs[i], ya, zz], [xs[i + 1], ya, zz], [xs[i + 1], ya, zz + 7], [xs[i], ya, zz + 7]]
                         for i in range(39)], C["zip"]))
    pull = np.array([[150, ya + 1, zz - 30], [158, ya + 1, zz - 30], [158, ya + 1, zz + 4], [150, ya + 1, zz + 4]])
    out.append(RW._soup([pull], C["trim"]))
    for sx in (-1, 1):   # front G-hook straps to the roll clips, rear straps to the frame-side hem
        A = np.array([sx * 120, ya, z0 + 10])
        B = np.array([sx * 150, ya + 25, z0 - 40])
        out.append(RW._soup([[A, B, B + [0, 0, 25], A + [0, 0, 25]]], C["webbing"]))
    return out


def guy_soups(c, C, dy=0.0):
    out = []
    for sg in (1, -1):
        A = np.array([sg * 95, 21.7, 702.6 + 8])
        B = np.array([sg * CO.B22_X, float(c.y_front([CO.B22_Z])[0]) + 2 + dy, CO.B22_Z])
        out.append(RW._soup([[A, B, B + [0, 0, 22], A + [0, 0, 22]]], C["webbing"]))
    return out


def bag_soups(c, b, C, door_open=False, tripod=False, inside=False):
    b.extra["zip3d"] = door_paths(c)
    R.COLOUR_HOOK[CO.SLUG] = colour
    body = R.concept_soup(c, b, C)
    body[0] = orient_outward(c, body[0])
    if door_open:
        Q, col = body[0]["quad"], body[0]["col"]
        keep = np.array([not in_door(c, q.mean(0)) for q in Q])
        door_Q = Q[~keep]
        body[0] = {"quad": Q[keep], "col": col[keep], "inside": True}
        zh = CO.DOOR["z_hinge"]
        yh = float(c.y_front([zh])[0])
        th = np.radians(105)
        rel = door_Q - np.array([0, yh, zh])
        rot = np.stack([rel[..., 0], rel[..., 1] * np.cos(th) - rel[..., 2] * np.sin(th),
                        rel[..., 1] * np.sin(th) + rel[..., 2] * np.cos(th)], -1) + np.array([0, yh, zh])
        body.append(RW._soup(rot, C["body"] * 0.95))
        for zs in (BC.STATIONS["im1"], BC.STATIONS["im2"], BC.STATIONS["im3"]):   # IM1-IM3 inside, bone webbing
            yfz = float(BC.y_frame([zs])[0]) + 22
            out = [[[-120, yfz, zs - 19], [120, yfz, zs - 19], [120, yfz, zs + 19], [-120, yfz, zs + 19]]]
            body.append(RW._soup(out, BONE))
            for sx in (-1, 1):
                body.append(RW._soup([[[sx * 112, yfz + 2, zs - 12], [sx * 132, yfz + 2, zs - 12],
                                       [sx * 132, yfz + 2, zs + 12], [sx * 112, yfz + 2, zs + 12]]], C["metal"]))
    body += wing_soup(c, C, tripod)
    body += pouch_soup(c, C)
    body += guy_soups(c, C)
    return body


def shift(soups, dy):
    out = []
    for s in soups:
        t = dict(s)
        t["quad"] = s["quad"] + np.array([0, dy, 0])
        out.append(t)
    return out


# ============================================================================ painter with interior lining
LINING = np.array([0.20, 0.21, 0.19])


def render(ax, soups, view, xlim=None, ylim=None):
    """R.render, plus: faces of an 'inside' soup that face away from the camera are drawn as the dark lining."""
    from matplotlib.collections import PolyCollection
    d = view / np.linalg.norm(view)
    r = np.cross([0, 0, 1.0], d)
    r /= np.linalg.norm(r)
    up = np.cross(d, r)
    Qs, Cs, Ins = [], [], []
    for s in soups:
        Qs.append(s["quad"])
        Cs.append(s["col"])
        Ins.append(np.full(len(s["quad"]), bool(s.get("inside", False))))
    Q, Cc, IN = np.concatenate(Qs), np.concatenate(Cs), np.concatenate(Ins)
    nrm = np.cross(Q[:, 2] - Q[:, 0], Q[:, 3] - Q[:, 1])
    nn = np.linalg.norm(nrm, axis=1)
    ok = nn > 1e-9
    Q, Cc, IN, nrm, nn = Q[ok], Cc[ok], IN[ok], nrm[ok], nn[ok]
    nrm /= nn[:, None]
    back = (nrm @ d) < 0
    Cc = Cc.copy()
    Cc[IN & back] = LINING
    L = R.LIGHT / np.linalg.norm(R.LIGHT)
    shade = 0.38 + 0.42 * np.abs(nrm @ L) + 0.25 * np.abs(nrm @ d)
    col = np.clip(Cc * shade[:, None], 0, 1)
    uv = np.stack([Q @ r, Q @ up], -1)
    o = np.argsort((Q @ d).mean(1))
    ax.add_collection(PolyCollection(uv[o], facecolors=col[o], edgecolors=col[o], linewidths=0.15))
    ax.set_aspect("equal")
    if xlim is None:
        allp = uv.reshape(-1, 2)
        xlim = (allp[:, 0].min() - 20, allp[:, 0].max() + 20)
        ylim = (allp[:, 1].min() - 20, allp[:, 1].max() + 20)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")


def shot(path, soups, view, title, caption, lims=None, size=(12, 13)):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=size, dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.86])
    if lims is None:
        lims = R.frame_extent(soups, view)
    render(ax, soups, view, *lims)
    import textwrap
    fig.text(0.02, 0.965, title, fontsize=26, weight="bold", color="#222", va="top")
    fig.text(0.02, 0.925, "\n".join(textwrap.wrap(caption, 80)), fontsize=15, color="#333", va="top")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    R._shrink(path)


def fit(soups, view, aspect=12 / 13 * 0.96 / 0.86, padx=200, pady=120):
    """Limits around the given (bag) soups with the figure's aspect, so the bag fills the frame."""
    (x0, x1), (y0, y1) = R.frame_extent(soups, view)
    x0, x1, y0, y1 = x0 - padx, x1 + padx, y0 - pady, y1 + pady
    w, h = x1 - x0, y1 - y0
    if w / h < aspect:
        cx = 0.5 * (x0 + x1)
        w = h * aspect
        x0, x1 = cx - w / 2, cx + w / 2
    else:
        cy = 0.5 * (y0 + y1)
        h = w / aspect
        y0, y1 = cy - h / 2, cy + h / 2
    return (x0, x1), (y0, y1)


def extent_of(soups, view, pad=60):
    (x0, x1), (y0, y1) = R.frame_extent(soups, view)
    return (x0 - pad, x1 + pad), (y0 - pad, y1 + pad)


def numbers_sheet(path, c, b, m, v, extra):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 10), dpi=100)
    fig.patch.set_facecolor("#f4f3ef")
    ax = fig.add_axes([0.01, 0.05, 0.55, 0.82])
    R.draw_flats(ax, b)
    fig.text(0.015, 0.955, f"{CO.NAME}: body pieces to scale and the numbers", fontsize=24, weight="bold", color="#222")
    fig.text(0.015, 0.91, "seam line filled, cut line dashed; pouch, wings and camo accents included", fontsize=14,
             color="#333")
    lines = [
        f"Main bag {v['volume_L']:.1f} L / {v['volume_cu_in']:.0f} cu in (to the fill line)",
        f"Top pouch {b.extra['pouch_L']:.1f} L / {b.extra['pouch_L'] * 1e3 / 16.387:.0f} cu in (not counted)",
        f"Fill height {v['fill_height_in']:.1f} in; width 15.5 in; depth {v['max_depth_in']:.1f} in",
        f"Bag-body group {m['mass_g']['total']:.0f} g ({extra['delta']:+.0f} g vs SPINE)",
        f"Pack {extra['pack_g']:.0f} g ({extra['pack_g'] / 453.592:.2f} lb)",
        f"Naive merge was {extra['naive']:.0f} g: saved {extra['naive'] - m['mass_g']['total']:.0f} g",
        f"Pieces {m['cut_pieces']}, seams {m['seam_length_m']:.1f} m, curved {m['curved_seams']}",
        f"Zips: door #10 {extra['door_mm']:.0f} mm, pouch #8 300 mm",
        f"Beginner hours {m['hours_total']:.0f} h (ASSUMPTION model)",
        f"Uniform-fill CG y {v['cg_y']:.0f} / z {v['cg_z']:.0f} mm",
        f"Est. loaded CG {extra['cg_est']} mm (15/19/23 in)",
    ]
    for i, t in enumerate(lines):
        fig.text(0.58, 0.85 - i * 0.06, t, fontsize=15, color="#222")
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    R._shrink(path)


def main():
    c, b, naive, m, mn, v = CO.numbers()
    C = R.colours()
    carry, float_ctx = load_parts()
    ctx = [R.soup_from_tri(t, C) for t in carry]
    fctx = [R.soup_from_tri(t, C) for t in float_ctx]
    base = bag_soups(c, b, C)
    lims34 = fit(base, R.VIEWS["q34"], padx=260, pady=160)
    limsS = fit(base, R.VIEWS["side"], padx=330, pady=160)
    files = []
    f = OUT / f"{DATE}_corrie_1.png"
    shot(f, base + ctx, R.VIEWS["q34"], f"{CO.NAME}: 3/4 rear",
         "box body, side compression wings, horseshoe door on the aft face, roll-top, 4 L top pouch; 19 in torso",
         lims34)
    files.append(f)
    f = OUT / f"{DATE}_corrie_2.png"
    shot(f, base + ctx, R.VIEWS["side"], f"{CO.NAME}: side (wearer's right)",
         "wing (2 straps) over the side panel; guys from the crown hood to B-22 at z 695 on the hinge band", limsS)
    files.append(f)
    opened = bag_soups(c, b, C, door_open=True)
    f = OUT / f"{DATE}_corrie_3.png"
    shot(f, opened + ctx, np.array([0.45, 1.0, 0.30]), f"{CO.NAME}: door open",
         "door hinged at z 650 swings up; IM1 (z 190), IM2 (z 330), IM3 (z 520) and the floor reachable; wings stay cinched",
         fit(opened, np.array([0.45, 1.0, 0.30]), padx=200, pady=120))
    files.append(f)
    tri = bag_soups(c, b, C, tripod=True)
    f = OUT / f"{DATE}_corrie_4.png"
    shot(f, tri + ctx, np.array([1.0, 0.75, 0.30]), f"{CO.NAME}: wing cinched on a tripod",
         "tripod legs under the right wing, 2 G-hook straps to loops in the aft corner seam; the door zip stays clear",
         fit(tri, np.array([1.0, 0.75, 0.30]), padx=200, pady=120))
    files.append(f)
    pv = np.array([0.55, 1.0, 0.9])
    ps = pouch_soup(c, C)
    (x0, x1), (y0, y1) = R.frame_extent(ps, pv)
    cx, cy, half = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * max(x1 - x0, y1 - y0) + 180
    f = OUT / f"{DATE}_corrie_5.png"
    shot(f, base + ctx, pv, f"{CO.NAME}: top pouch",
         "4.0 L boxed pouch on the closed roll: #8 zip on the aft edge with a glove pull, 2 rear + 2 front G-hook straps",
         fit(ps, pv, padx=260, pady=200))
    files.append(f)
    fl = shift(bag_soups(c, b, C), FLOAT_GAP)
    f = OUT / f"{DATE}_corrie_6.png"
    shot(f, fl + fctx, R.VIEWS["side"], f"{CO.NAME}: float meat mode",
         "quarter in the US1/US2 cradle under IM1-IM3; bag hung upright 170 mm aft on the B-24 links (T3); W1-W3 round both",
         fit(fl + [R.soup_from_tri(t, C) for t in float_ctx if "quarter" in t["name"]], R.VIEWS["side"], padx=300, pady=150))
    files.append(f)
    est = CO.cloth_sim_estimate(v["cg_y"])
    pack = BC.PACK_TOTAL_G + m["mass_g"]["total"] - 333.2
    f = OUT / f"{DATE}_corrie_7.png"
    numbers_sheet(f, c, b, m, v, {"delta": m["mass_g"]["total"] - 333.2, "pack_g": pack, "naive": mn["mass_g"]["total"],
                                  "door_mm": b.extra["zip_door_mm"],
                                  "cg_est": "/".join(f"{int(x)}" for x in est["fill_est_mm"].values())})
    files.append(f)
    for n in (1, 3, 4, 6):
        shutil.copy2(OUT / f"{DATE}_corrie_{n}.png", R.DOCS / f"{DATE}_corrie_{n}.png")
    for f in files:
        print("PNG", f, f"{f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
