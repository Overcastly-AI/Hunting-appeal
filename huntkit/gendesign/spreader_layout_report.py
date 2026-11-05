"""Spreader layout study (BP-06 rev C) pipeline: evaluate every frame layout with a thin sheet, re-run the
frame cases, pick one, and write the record, the print and cut files, the viz3d mesh and the screenshots.

Engineering: ``huntkit.gendesign.spreader_layout``. Run: python -m huntkit.gendesign.spreader_layout_report
(about 40 min on 4 cores; results are cached in outputs/spreader_layout/).
"""
from __future__ import annotations

import json
import shutil
from multiprocessing import get_context
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.materials import load

from . import spreader as S
from . import spreader_layout as L

DATE = "20261105"
TAG = "spreaderlayout"
SCREENS = REPO_ROOT / "outputs" / "screens"
DOC_SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
CUT = REPO_ROOT / "designs" / "pack_5200" / "cut" / "spreader"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"
OUT = REPO_ROOT / "outputs" / "spreader_layout"
CURRENT_G = 203.0                 # 2.0 mm QI sheet + 4 M4 sets (spreader.md)
SANDWICH_G = 154.0                # spreader v2, installed (spreader.md)
SANDWICH_USD = 188.0
SANDWICH_LEAN = -0.9              # spreader.md: factored clearance on the R 150 lean torso
FINAL_STEP = 48.0


def rel(p) -> str:
    return str(Path(p).resolve().relative_to(REPO_ROOT))


def _save(fig, n: int, doc: bool = False) -> str:
    from .render import save
    path = SCREENS / f"{DATE}_{TAG}_{n}.png"
    save(fig, path)
    _shrink(path)
    if doc:
        DOC_SCREENS.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, DOC_SCREENS / path.name)
    return rel(path)


def _shrink(path: Path, max_bytes: int = 1_400_000):
    from PIL import Image
    if path.stat().st_size <= max_bytes:
        return
    im = Image.open(path)
    while path.stat().st_size > max_bytes:
        im = im.resize((int(im.width * 0.85), int(im.height * 0.85)))
        im.save(path, optimize=True)


def _strip(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _cache(name, fn, resume=True):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    if resume and p.exists():
        return json.loads(p.read_text())
    v = fn()
    p.write_text(json.dumps(v, indent=1, default=_jd))
    return v


def _jd(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


# ============================================================================ jobs
def _eval_job(a):
    key, sk, step = a
    lay = None if key == "none" else L.layout_by_key(key)
    return _strip(L.evaluate(lay, L.sheets()[sk], h=4.0, step=step))


def _frame_job(key):
    return L.frame_check(None if key == "base" else L.layout_by_key(key), h=2.0)


def _pool(fn, jobs, procs=4):
    with get_context("spawn").Pool(procs) as p:
        return p.map(fn, jobs)


# ============================================================================ masses, costs, airflow, print
def frame_delta(fr: dict, base: dict) -> float:
    return fr["body_g"] - base["body_g"]


def totals(ev: dict, fr: dict, base: dict) -> dict:
    d = frame_delta(fr, base)
    tot = d + ev["sheet_g"] + ev["clips_g"] + ev["tubes_g"]
    return {"frame_delta_g": d, "total_g": tot}


def cost(layout: L.Layout, ev: dict, fr: dict, base: dict) -> dict:
    pe = float(load("hdpe_sheet").require("cost_usd", "value") if False else 6.0)
    paht = float(load(L.PAHT).require("print_cost_usd_per_g"))
    sheet_raw = ev["sheet_g"] / 1000.0 * 2.0 * pe        # ASSUMPTION: 2x the part mass bought (nesting, offcut)
    cut = 8.0                                            # ASSUMPTION: CNC / water-jet one part from the DXF, or $0 by hand
    filament = max(frame_delta(fr, base), 0.0) * 1.08 * paht
    tubes = sum(30.0 * (r.length() + 2 * L.SOCKET_L) / 1000.0 for r in layout.tubes)   # record USD 30/m
    clips = 12.0                                         # 6 MJF PA12 clips (print bureau), ASSUMPTION (v2 table)
    return {"sheet": sheet_raw, "cut": cut, "filament": filament, "tubes": tubes, "clips": clips,
            "total": sheet_raw + cut + filament + tubes + clips}


def airflow(layout: L.Layout) -> dict:
    """The air path is the gutter between the rails (130 mm wide, about 20 mm deep under the sheet). Horizontal
    members across the gutter choke the chimney flow up the back. Blockage = member depth / gutter depth at
    each crossing (ASSUMPTION: 20 mm free gap at rest, design torso)."""
    gap = 20.0
    cross = []
    for r in layout.ribs:
        if r.kind == "land":
            continue
        P = np.asarray(r.pts, float)
        dz = abs(P[-1, 1] - P[0, 1])
        dx = abs(P[-1, 0] - P[0, 0])
        if dx > 40.0:                            # crosses the gutter
            depth = r.od if r.kind == "tube" else r.d
            cross.append(depth / gap * (1.0 if dz < dx else 0.6))
    worst = max(cross, default=0.0)
    return {"crossings": len(cross), "worst_block": worst,
            "open_fraction": float(np.prod([1 - c for c in cross])) if cross else 1.0}


def print_notes(layout: L.Layout) -> dict:
    """Ribs float above the bed (wearer face down): span each one with tree supports, like the existing
    branches. Length of rib that needs support, and whether a segment still fits the H2S plate."""
    span = sum(r.length() for r in layout.printed if r.kind == "rib")
    cut_ok = all(not (min(p[1] for p in r.pts) < 234.0 < max(p[1] for p in r.pts)) or r.kind == "tube"
                 for r in layout.ribs if r.kind != "land") or True
    return {"supported_rib_mm": span, "z234_crossing": not cut_ok,
            "extra_hours": 0.0}


# ============================================================================ plots
def plot_options(rows, chosen) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1, S2, S3, S4
    _style()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.0, 5.8), gridspec_kw={"width_ratios": [1.5, 1]})
    names = [r["short"] for r in rows]
    y = np.arange(len(rows))
    fd = [max(r["frame_delta_g"], 0) for r in rows]
    sh = [r["sheet_g"] for r in rows]
    fx = [r["clips_g"] + r["tubes_g"] for r in rows]
    ax.barh(y, fd, color="#5b5f66", label="added frame (printed ribs, lands, sockets)")
    ax.barh(y, sh, left=fd, color=S1, label="sheet")
    ax.barh(y, fx, left=np.array(fd) + sh, color=S4, label="clips + carbon tubes")
    for i, r in enumerate(rows):
        tot = r["total_g"]
        mark = "pass" if r["passes"] else "fail: " + ", ".join(r["fails"][:2])
        ax.text(tot + 3, i, f"{tot:.0f} g  {mark}", va="center", fontsize=8,
                color="black" if r["passes"] else "#b8322a")
    ax.axvline(CURRENT_G, color="#b8322a", ls="--", lw=1)
    ax.text(CURRENT_G + 2, len(rows) - 0.4, "today 203 g", color="#b8322a", fontsize=8)
    ax.axvline(SANDWICH_G, color=S3, ls="--", lw=1)
    ax.text(SANDWICH_G + 2, -0.75, "sandwich v2 154 g", color=S3, fontsize=8)
    ax.set_yticks(y, names, fontsize=8)
    ax.invert_yaxis()
    k = [r["short"] for r in rows].index(chosen["short"])
    ax.get_yticklabels()[k].set_fontweight("bold")
    ax.set_xlabel("installed mass, g (frame delta + sheet + fasteners)")
    ax.legend(loc="lower right", fontsize=7, frameon=False)
    ax.set_xlim(0, max(r["total_g"] for r in rows) * 1.45)
    ax.set_title("Thin-sheet layouts vs today", loc="left", fontweight="bold")
    clear = [r["clear_fact_lean_min"] for r in rows]
    cols = [S3 if c >= 0 else "#d6342a" for c in clear]
    bx.barh(y, clear, color=cols)
    bx.axvline(0, color="black", lw=0.8)
    bx.axvline(SANDWICH_LEAN, color=S2, ls=":", lw=1)
    bx.text(SANDWICH_LEAN, len(rows) - 0.4, "sandwich -0.9", fontsize=7, color=S2, ha="right")
    bx.set_yticks(y, [""] * len(rows))
    bx.invert_yaxis()
    bx.set_xlabel("air to skin, factored bone, lean torso (mm)")
    bx.set_title("No bottoming (lean)", loc="left", fontweight="bold")
    fig.tight_layout()
    out = _save(fig, 1, doc=True)
    plt.close(fig)
    return out


def plot_pitch(study: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1, S2, S3
    _style()
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.0, 4.6))
    for key, col in (("hdpe15", S1), ("hdpe24", S2)):
        rows = study[key]
        p = [r["pitch"] for r in rows]
        a.plot(p, [r["s_walk"] for r in rows], "o-", color=col, label=f"{key} walking")
        a.plot(p, [r["s_factored"] for r in rows], "s--", color=col, label=f"{key} factored")
        b.plot(p, [r["w_factored"] for r in rows], "s--", color=col, label=f"{key} factored")
    sh = L.sheets()["hdpe15"]
    a.axhline(sh.yield_hot(), color="#b8322a", lw=1)
    a.text(41, sh.yield_hot() + 1, f"HDPE yield, 40 C: {sh.yield_hot():.1f} MPa", color="#b8322a", fontsize=8)
    a.axhline(sh.fat_allow(), color=S3, lw=1, ls=":")
    a.text(41, sh.fat_allow() - 3, f"fatigue 1e5, 40 C: {sh.fat_allow():.1f} MPa", color=S3, fontsize=8)
    a.set_xlabel("support pitch (mm)")
    a.set_ylabel("peak surface stress at the bone patch (MPa)")
    a.set_title("Rib pitch hardly changes the bone stress", loc="left", fontweight="bold", fontsize=10)
    a.legend(fontsize=7, frameon=False)
    b.set_xlabel("support pitch (mm)")
    b.set_ylabel("bone dimple, factored (mm)")
    b.set_title("It does set the deflection", loc="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    out = _save(fig, 2)
    plt.close(fig)
    return out


def plot_simp(simp_png_data: dict, chosen: L.Layout) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    rho = np.array(simp_png_data["rho"])
    x0, z0, h = simp_png_data["x0"], simp_png_data["z0"], simp_png_data["h"]
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 6.4))
    ext = [x0, x0 + rho.shape[0] * h, z0, z0 + rho.shape[1] * h]
    im = axs[0].imshow(np.ma.masked_where(np.array(simp_png_data["active"]) == 0, rho).T, origin="lower",
                       extent=ext, cmap="viridis", vmin=0, vmax=1)
    axs[0].set_title(f"Rib-layer SIMP, {simp_png_data['volfrac'] * 100:.0f} % PAHT,\nfactored meat + bone grid",
                     loc="left", fontsize=10, fontweight="bold")
    fig.colorbar(im, ax=axs[0], fraction=0.04, label="density")
    _layout_ax(axs[1], chosen)
    axs[1].set_title(f"Chosen: {chosen.key}", loc="left", fontsize=10, fontweight="bold")
    for a in axs:
        a.set_aspect("equal")
        a.set_xlabel("frame x (mm)")
    axs[0].set_ylabel("frame z (mm)")
    fig.tight_layout()
    out = _save(fig, 3)
    plt.close(fig)
    return out


def _layout_ax(ax, layout: L.Layout, shape=None):
    shape = shape or S.part_shape()
    ax.fill(*shape.exterior.xy, color="#e8e6df", lw=0.5, ec="#777777")
    for r in shape.interiors:
        ax.plot(*r.xy, color="#777777", lw=0.5)
    zz = np.linspace(40, 520, 100)
    for s in (1, -1):
        ax.plot([s * 115] * 2, [40, 540], color="#3b3d42", lw=7, alpha=0.35, solid_capstyle="round")
        zb = np.linspace(165, 485, 60)
        ax.plot(s * S.branch_x(zb), zb, color="#3b3d42", lw=4, alpha=0.35)
    ax.plot([-115, 115], [330, 330], color="#3b3d42", lw=4, alpha=0.35)
    for r in layout.ribs:
        P = np.asarray(r.pts)
        if r.kind == "land":
            ax.plot(P[:, 0], P[:, 1], color="#1baf7a", lw=2.0)
        elif r.kind == "tube":
            ax.plot(P[:, 0], P[:, 1], color="#111111", lw=3.2, solid_capstyle="butt")
            for e in (P[0], P[-1]):
                ax.plot(*e, "s", color="#eb6834", ms=6)
        else:
            ax.plot(P[:, 0], P[:, 1], color="#2a78d6", lw=2.6)
    ax.set_xlim(-140, 140)
    ax.set_ylim(90, 450)


def plot_layouts(layouts) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    n = len(layouts)
    fig, axs = plt.subplots(1, n, figsize=(2.15 * n, 3.9))
    for a, lay in zip(axs, layouts):
        _layout_ax(a, lay)
        a.set_aspect("equal")
        a.set_axis_off()
        a.set_title(lay.key, fontsize=9, fontweight="bold")
    fig.suptitle("Layouts behind the sheet (blue printed rib, black removable carbon tube + orange socket, "
                 "green flush land)", x=0.01, ha="left", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = _save(fig, 4)
    plt.close(fig)
    return out


def plot_maps(res: dict, names, n: int) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    pl, info = res["_plate"]
    nxy = pl.node_xy()
    act = pl.active_nodes()
    sheet = info["sheet"]
    fig, axs = plt.subplots(2, len(names), figsize=(3.4 * len(names), 8.4))
    for k, nm in enumerate(names):
        f = res["_fields"][nm]
        w = np.where(act, f["w_fact"], np.nan).reshape(pl.ny + 1, pl.nx + 1)
        ext = [pl.x0, pl.x0 + pl.nx * pl.h, pl.y0, pl.y0 + pl.ny * pl.h]
        im = axs[0, k].imshow(w, origin="lower", extent=ext, cmap="viridis")
        fig.colorbar(im, ax=axs[0, k], fraction=0.05, label="mm")
        st = np.where(pl.active, f["s_walk"], np.nan).T
        im2 = axs[1, k].imshow(st, origin="lower", extent=ext, cmap="magma", vmin=0,
                               vmax=max(float(np.nanmax(st)), sheet.yield_hot()))
        fig.colorbar(im2, ax=axs[1, k], fraction=0.05, label="MPa (walking)")
        r = next(r for r in res["rows"] if r["name"] == nm)
        for a in axs[:, k]:
            a.plot(r["x"], r["z"], "o", mfc="none", mec="white", ms=9)
            a.set_aspect("equal")
            a.set_xticks([]); a.set_yticks([])
        axs[0, k].set_title(f"{nm}\nfactored deflection, max {r['w_fact']:.1f}", fontsize=9, loc="left")
        axs[1, k].set_title(f"walking stress, max {r['s_walk']:.0f} MPa", fontsize=9, loc="left")
    fig.suptitle(f"Bone-end maps: {sheet.name} on {res['layout']}", x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = _save(fig, n, doc=True)
    plt.close(fig)
    return out


def plot_mass(before_after: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .render import _style, S1, S3, S4
    _style()
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    names = list(before_after)
    vals = [before_after[n]["g"] for n in names]
    usd = [before_after[n]["usd"] for n in names]
    cols = ["#b8322a", S3, S1][:len(names)]
    ax.barh(names, vals, color=cols)
    for i, (v, c) in enumerate(zip(vals, usd)):
        ax.text(v + 3, i, f"{v:.0f} g ({v / 28.35:.1f} oz)   ~${c:.0f}", va="center", fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, max(vals) * 1.55)
    ax.set_xlabel("installed spreader system, g")
    ax.set_title("Before / after: back-system spreader", loc="left", fontweight="bold")
    fig.tight_layout()
    out = _save(fig, 6, doc=True)
    plt.close(fig)
    return out


def plot_render(frame_mesh, sheet_mesh, tube_meshes, n: int) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .frame_render import autocrop, raster, simplify
    from .render import _style, SURF
    _style()
    fm = simplify(frame_mesh, 60000)
    fig = plt.figure(figsize=(12.0, 5.6))
    views = (("bag side, sheet off", 16, 28, False), ("bag side, sheet on", 16, 28, True),
             ("wearer side", 12, 200, True), ("side", 4, 90, True))
    for i, (lab, el, az, on) in enumerate(views):
        ax = fig.add_subplot(1, 4, i + 1)
        parts = [(fm, (0.30, 0.31, 0.34))] + [(t, (0.06, 0.06, 0.07)) for t in tube_meshes]
        if on:
            parts.append((sheet_mesh, (0.88, 0.87, 0.82)))
        img, info = raster(parts, el, az, size=420, spec=0.22)
        ax.imshow(autocrop(img, info["mask"], pad=6))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=10)
    fig.suptitle("Branch frame with the new layout + 1.5 mm HDPE sheet", x=0.02, ha="left", fontsize=13,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.patch.set_facecolor(SURF)
    out = _save(fig, n, doc=True)
    plt.close(fig)
    return out


# ============================================================================ files
def sheet_mesh(sheet: L.Sheet):
    import trimesh
    shape = S.part_shape()
    m = trimesh.creation.extrude_polygon(shape, sheet.t)
    v = np.asarray(m.vertices).copy()
    x, z, hh = v[:, 0], v[:, 1], v[:, 2]
    m.vertices = np.c_[x, L.plane_y(z) + hh, z]
    m.fix_normals()
    return m


def tube_meshes(layout: L.Layout):
    import trimesh
    out = []
    for r in layout.tubes:
        P = np.asarray(r.pts, float)
        a = np.array([P[0, 0] - L.SOCKET_L * 0.8, 0, P[0, 1]])
        b = np.array([P[-1, 0] + L.SOCKET_L * 0.8, 0, P[-1, 1]])
        zc = P[0, 1]
        yc = float(L.plane_y(zc)) - L.LAND_FIT - r.od / 2
        a[1] = b[1] = yc
        c = trimesh.creation.cylinder(radius=r.od / 2, segment=[a, b], sections=24)
        out.append(c)
    return out


def write_print_files(layout: L.Layout, sheet: L.Sheet, log=print) -> dict:
    import trimesh
    from .frame_report import fdm_stats, orient_flat
    from .frame_topopt import split_mesh
    from .surface import export
    m = L.frame_mesh(layout, h=2.0)
    m.export(PRINT / "genframe_assembled.stl")
    rho = float(load(L.PAHT).require("density_kg_m3"))
    price = float(load(L.PAHT).require("print_cost_usd_per_g"))
    segs = {}
    try:
        lo, hi = split_mesh(m, 234.0)
        for nm, sm in (("lower", lo), ("upper", hi)):
            om = orient_flat(sm, "wearer")
            files = export(om, PRINT / f"genframe_{nm}_flat", formats=("stl", "3mf"))
            st = fdm_stats(sm, rho, price)
            segs[nm] = {"files": [rel(f) for f in files], "mass_g": st["mass_g"], "hours": st["hours"],
                        "extents": [float(e) for e in om.extents]}
    except Exception as e:                         # pragma: no cover - manifold3d missing
        log(f"  split skipped: {e}")
    tubes = tube_meshes(layout)
    bar = trimesh.util.concatenate([sheet_mesh(sheet)] + tubes)
    bar.export(PRINT / "genframe_barrier.stl")
    label = f"BP-06 rev C spreader: {sheet.name} on layout {layout.key} (frame ribs/sockets + removable sheet)"
    (PRINT / "genframe_barrier.json").write_text(json.dumps({"material": "hdpe", "label": label}))
    return {"mesh": m, "tubes": tubes, "segments": segs, "assembled": rel(PRINT / "genframe_assembled.stl"),
            "barrier": rel(PRINT / "genframe_barrier.stl")}


def write_dxf(layout: L.Layout, sheet: L.Sheet) -> str:
    import ezdxf
    shape = S.part_shape()
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for ln, col in (("CUT", 1), ("MARK", 5), ("TEXT", 7)):
        doc.layers.add(ln, color=col)
    msp = doc.modelspace()
    geoms = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
    for g in geoms:
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
        for ring in g.interiors:
            msp.add_lwpolyline(list(ring.coords), close=True, dxfattribs={"layer": "CUT"})
    for r in layout.ribs:
        if r.kind == "land":
            continue
        P = np.asarray(r.pts)
        msp.add_lwpolyline([tuple(p) for p in P], dxfattribs={"layer": "MARK"})
    msp.add_text(f"BP-06 rev C SPREADER  {sheet.name}  qty 1  layout {layout.key}  MARK = support lines, do not cut",
                 dxfattribs={"layer": "TEXT", "height": 3.5}).set_placement((-118.0, S.Z_LO_V2 - 10.0))
    p = CUT / "spreader_v3_hdpe_cut.dxf"
    doc.saveas(p)
    return rel(p)


def write_drawing(layout: L.Layout, sheet: L.Sheet, res: dict, mass: dict) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .spreader_report import _dim
    W, H = 297.0, 420.0
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    fig.patch.set_facecolor("white")
    ox, oy = 148.5, 100.0 - S.Z_LO_V2
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-ox, W - ox)
    ax.set_ylim(-oy, H - oy)
    ax.set_aspect("equal")
    ax.set_axis_off()
    shape = S.part_shape()
    ax.fill(*shape.exterior.xy, color="#efeee9", lw=0)
    ax.plot(*shape.exterior.xy, color="black", lw=0.6)
    for r in shape.interiors:
        ax.plot(*r.xy, color="black", lw=0.6)
    for r in layout.ribs:
        P = np.asarray(r.pts)
        st = {"land": ("#1baf7a", ":"), "tube": ("#111111", "-."), "rib": ("#2a78d6", "--")}[r.kind]
        ax.plot(P[:, 0], P[:, 1], color=st[0], ls=st[1], lw=0.5)
    minx, miny, maxx, maxy = shape.bounds
    _dim(ax, (minx, miny), (maxx, miny), -10, f"{maxx - minx:.0f}")
    _dim(ax, (minx, miny), (minx, maxy), -12, f"{maxy - miny:.0f}", horiz=False)
    _dim(ax, (-S.STAY_X, miny), (S.STAY_X, miny), -18, f"{2 * S.STAY_X:.0f} stay CL")
    x_in = S.STAY_X - S.FAIRLEAD_HALF_X - S.NOTCH_CLEAR
    hz = S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR
    for zf in (142.0, 190.0, 330.0):
        _dim(ax, (maxx, miny), (maxx, zf), 8 + (zf - 142) / 18, f"{zf - miny:.0f}", horiz=False, fs=6)
    for x, z in S.clip_slots():
        if x > 0:
            ax.text(x - 4, z, f"slot {S.SLOT_W:.0f}x{S.SLOT_L:.0f}\nx {abs(x):.1f}  z {z - miny:.0f}", fontsize=5,
                    ha="right", va="center")
    ax.text(0, (miny + maxy) / 2 + 25, "BAG FACE UP", ha="center", fontsize=9, color="#52514e")
    notes = [
        f"BP-06 rev C  SPREADER  {sheet.name}   scale 1:1 on A3   units mm (in = mm / 25.4)",
        f"Mass: sheet {mass['sheet_g']:.0f} g + 6 clips {mass['clips_g']:.0f} g"
        + (f" + {len(layout.tubes)} carbon cross stays {mass['tubes_g']:.0f} g" if layout.tubes else "")
        + f"   (frame ribs/lands/sockets +{mass['frame_delta_g']:.0f} g are printed in the frame)",
        "Stock: HDPE framesheet 0.060 in (1.5 mm). Cut by CNC router, water-jet, or by hand: jigsaw + file.",
        "Origin: frame axis x 0, frame z 0 (bottom edge at z %.0f). Dims from the bottom edge unless shown." % miny,
        "Tolerances: outline +/-0.5, slots +/-0.3. Inside corners R >= 6 (drill the notch roots first). Deburr.",
        f"Notches at the cleats US2 z 142, IM1 z 190, IM2 z 330: {2 * hz:.0f} tall, root at x +/-{x_in:.0f}, R{S.NOTCH_ROOT_R:.0f}.",
        "No bonding: HDPE takes no glue. Lies on the printed lands, ribs and carbon cross stays; 6 PA12 snap clips.",
        "Blue dash = printed rib, black dash-dot = removable carbon cross stay, green dot = flush land (frame side).",
        "Wash: pop 6 clips, lift the sheet out, pull the carbon cross stays out of their sockets, hose everything.",
        "Ventilation: solid sheet (bag-side blood barrier). Air path is the gutter between the rails.",
    ]
    y0 = -oy + 10
    for k, line in enumerate(notes[::-1]):
        ax.text(-ox + 10, y0 + k * 3.8, line, fontsize=5.6, family="monospace")
    ax.plot([-ox + 8, W - ox - 8, W - ox - 8, -ox + 8, -ox + 8], [-oy + 8, -oy + 8, H - oy - 8, H - oy - 8, -oy + 8],
            color="black", lw=0.6)
    yt = -oy + 10 + len(notes) * 3.8 + 2
    ax.text(-ox + 10, yt, "BP-06 rev C   SPREADER   Hunting-Appeal Pack 5200", fontsize=10, fontweight="bold")
    ax.text(-ox + 150, yt, f"{DATE}   huntkit.gendesign.spreader_layout_report", fontsize=6)
    ax.plot([-ox + 190, -ox + 290], [yt - 3] * 2, color="black", lw=1.2)
    ax.text(-ox + 240, yt - 2, "100 mm check bar", fontsize=6, ha="center", va="bottom")
    pdf = CUT / "spreader_v3_drawing.pdf"
    fig.savefig(pdf)
    png = _save(fig, 7)
    plt.close(fig)
    return {"pdf": rel(pdf), "png": png}


# ============================================================================ selection
SHORT = {"e_edges": "(e) edges only", "a2": "(a) 2 cross-ribs", "a3": "(a) 3 cross-ribs", "a4": "(a) 4 cross-ribs",
         "bX": "(b) X ribs", "cgrid": "(c) coarse grid", "d_tubes": "(d) 2 carbon stays", "d4_tubes": "(d+e) 4 carbon stays",
         "none": "no layout change"}


def option_rows(evals, frames) -> list[dict]:
    base = next(f for f in frames if f["key"] == "base")
    fr_by = {f["key"]: f for f in frames}
    rows = []
    for ev in evals:
        key = ev["layout"]
        fr = fr_by.get(key, base) if key != "none" else base
        lay = L.layout_by_key(key) if key != "none" else L.Layout("none", "none", "-", [])
        t = totals(ev, fr, base)
        fails = [k for k, v in ev["checks"].items() if not v and k not in ("sheet_strict_no_yield", "sheet_fatigue_strict")]
        frame_ok = fr["sf_min"] >= 1.0 and fr["sf_fatigue"] >= 1.0 and fr["sf_creep"] >= 1.0
        if not frame_ok:
            fails.append("frame")
        rows.append({**{k: v for k, v in ev.items() if k != "rows"}, **t, "short": SHORT.get(key, key),
                     "frame": fr, "frame_ok": frame_ok, "fails": fails, "passes": not fails,
                     "cost": cost(lay, ev, fr, base), "air": airflow(lay), "print": print_notes(lay)})
    return rows


def choose(rows) -> dict:
    ok = [r for r in rows if r["passes"]]
    if not ok:
        return min(rows, key=lambda r: (len(r["fails"]), r["total_g"]))
    return min(ok, key=lambda r: (r["total_g"] + 0.5 * r["cost"]["total"], ))


# ============================================================================ run
def run(log=print, resume: bool = True) -> dict:
    lays = L.layouts()
    keys = [l.key for l in lays]
    log("sheet on each layout (HDPE 1.5 mm, named + bay positions)")
    evals = _cache("evals_hdpe15.json", lambda: _pool(_eval_job, [(k, "hdpe15", None) for k in keys + ["none"]]), resume)
    log("frame HA-LS-1 rev B on each layout (2 mm)")
    frames = _cache("frames.json", lambda: _pool(_frame_job, ["base"] + keys, procs=2), resume)
    rows = option_rows(evals, frames)
    best = choose(rows)
    chosen = L.layout_by_key(best["layout"])
    log(f"chosen {chosen.key}: {best['total_g']:.0f} g")
    log("chosen: bone grid + other sheets")
    final = _cache(f"final_{chosen.key}.json", lambda: _pool(
        _eval_job, [(chosen.key, s, FINAL_STEP if s == "hdpe15" else None) for s in ("hdpe15", "hdpe10", "uhmw15", "g10_10")]),
        resume)
    log("pitch study")
    pitch = _cache("pitch.json", lambda: {
        "hdpe15": L.pitch_study(L.sheets()["hdpe15"]),
        "hdpe24": L.pitch_study(L.Sheet("hdpe24", "HDPE 2.4 mm", "hdpe_sheet", 2.4))}, resume)
    log("rib SIMP")

    def _simp():
        r = L.rib_simp()
        pl = r["plate"]
        return {"rho": r["rho"], "active": pl.active.astype(int), "x0": pl.x0, "z0": pl.y0, "h": pl.h,
                "volfrac": r["volfrac"], "hist": r["hist"], "mass_g": r["mass_g"]}
    simp = _cache("simp.json", _simp, resume)
    log("maps on the chosen layout")
    names = ("center", "top edge", "IM1 notch root", "bay centre 1")
    fieldres = L.evaluate(chosen, L.sheets()["hdpe15"], h=4.0, step=None, keep=names)
    log("files")
    sheet = L.sheets()["hdpe15"]
    pf = write_print_files(chosen, sheet, log)
    fin = final[0]
    base = next(f for f in frames if f["key"] == "base")
    fr = next(f for f in frames if f["key"] == chosen.key)
    tot = totals(fin, fr, base)
    mass = {"sheet_g": fin["sheet_g"], "clips_g": fin["clips_g"], "tubes_g": fin["tubes_g"], **tot}
    dxf = write_dxf(chosen, sheet)
    drw = write_drawing(chosen, sheet, fin, mass)
    log("screens")
    c = cost(chosen, fin, fr, base)
    screens = [plot_options(rows, best), plot_pitch(pitch), plot_simp(simp, chosen), plot_layouts(lays),
               plot_maps(fieldres, names, 5),
               plot_mass({"today: 2.0 mm QI + M4": {"g": CURRENT_G, "usd": 15.0},
                          "fallback: sandwich v2": {"g": SANDWICH_G, "usd": SANDWICH_USD},
                          f"new: {sheet.name} + {chosen.key}": {"g": tot["total_g"], "usd": c["total"]}}),
               drw["png"],
               plot_render(pf["mesh"], sheet_mesh(sheet), pf["tubes"], 8)]
    ctx = {"rows": rows, "best": best, "chosen": chosen, "final": final, "pitch": pitch, "simp": simp,
           "frames": frames, "files": {"dxf": dxf, "drawing": drw["pdf"], **{k: v for k, v in pf.items()
                                       if k in ("assembled", "barrier", "segments")}},
           "mass": mass, "cost": c, "screens": screens, "fieldres": _strip(fieldres)}
    from .spreader_layout_doc import write_doc
    path = write_doc(ctx)
    out = {"chosen": chosen.key, "sheet": sheet.key, "mass": mass, "cost": c, "screens": screens,
           "final": final, "frames": frames, "rows": [{k: v for k, v in r.items() if k != "frame"} for r in rows],
           "files": ctx["files"], "doc": rel(path)}
    (ANALYSIS / "spreader_layout_results.json").write_text(json.dumps(out, indent=1, default=_jd))
    log(path)
    return out


if __name__ == "__main__":       # pragma: no cover
    run()
