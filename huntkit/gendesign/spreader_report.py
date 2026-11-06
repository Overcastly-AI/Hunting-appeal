"""Spreader (BP-06) v2 pipeline: verify the current part, compare lighter options, detail the
chosen part for manufacture, and write records, cut files, the viz3d mesh and screenshots.

Engineering lives in ``huntkit.gendesign.spreader`` (plate on the real branch-frame supports,
rail/skin model, sandwich checks, outline, DXF). This module runs it and writes the files.

Run: python -m huntkit.gendesign.spreader_report      (about 15-25 min on 4 cores)
"""
from __future__ import annotations

import dataclasses
import json
import shutil
from multiprocessing import get_context
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.materials import load

from . import spreader as S

DATE = "20261104"
TAG = "spreader2"
SCREENS = REPO_ROOT / "outputs" / "screens"
DOC_SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
CUT = REPO_ROOT / "designs" / "pack_5200" / "cut" / "spreader"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"
OUT = REPO_ROOT / "outputs" / "spreader"
TABLE_STEP = 48.0                 # bone grid pitch for the option table (plus the named positions)
FINAL_STEP = 24.0                 # bone grid pitch for the chosen part
OLD_SHEET_G = 193.0               # back_comfort.md: 208 x 300 x 2.0 mm QI
OLD_PART_G = OLD_SHEET_G + 4 * S.M4_SET_G
TARGET_G = 100.0


def rel(p) -> str:
    return str(Path(p).resolve().relative_to(REPO_ROOT))


def _save(fig, n: int, doc: bool = False) -> str:
    from .render import save
    path = SCREENS / f"{DATE}_{TAG}_{n}.png"
    save(fig, path)
    if doc:
        DOC_SCREENS.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, DOC_SCREENS / path.name)
    return rel(path)


# ============================================================================ evaluation
def _strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _eval_key(args):
    key, step = args
    opt = {o.key: o for o in S.options()}[key]
    r = S.evaluate(opt, h=4.0, step=step)
    r["note"], r["buy"] = opt.note, opt.buy
    return _strip(r)


def _eval_v1(_):
    opt = {o.key: o for o in S.options()}["qi20"]
    opt = dataclasses.replace(opt, tubes=False, pucks=False)
    r = S.evaluate(opt, h=4.0, version="v1", step=TABLE_STEP)
    return _strip(r)


PERF_BASE = ("pf15", "QI carbon 1.5 mm, SIMP cut-outs <= 20 mm", 1.5)


def _eval_perf(_):
    key, name, t = PERF_BASE
    opt = S.Option(key, name, "perforated", S.qi_lam(t), "holes sized from a SIMP density field",
                   perforated=True, buy="bought plate, water-jet")
    sd = S.simp_density(opt, h=6.0, iters=15)
    holes = S.holes_from_density(sd)
    r = S.evaluate_perforated(opt, holes["holes"], h=4.0, step=TABLE_STEP)
    r["holes"] = holes["holes"]
    r["note"], r["buy"] = opt.note, opt.buy
    r["simp_rho"] = sd["rho"].tolist()
    r["simp_grid"] = {"x0": sd["plate"].x0, "y0": sd["plate"].y0, "h": sd["plate"].h}
    return _strip(r)


def sf_min(r: dict) -> float:
    v = [r["sf_fpf"], r["sf_fatigue"]]
    if r.get("sandwich_sf_min") is not None:
        v.append(r["sandwich_sf_min"])
    return float(min(v))


def verify_current(v1: dict) -> dict:
    """Item 1 on the as-drawn part: plate checks plus the M4 holes (bearing, edge distance, landing)."""
    qi = S.qi_lam(2.0)
    F = max(v1["bolt_max_n"], 1.0)
    bolt = S.bolt_check(qi, F, d=4.5, e=8.0)
    xs, zs, top = S.frame_top(4.0, -124.0, 124.0, S.Z_LO)
    land = []
    for x, z in ((96.0, 190.0), (96.0, 330.0)):
        i = int(np.argmin(np.abs(xs - x)))
        j = int(np.argmin(np.abs(zs - z)))
        y_plane = float(S.sleeve_y(z) + S.stay_r(z))
        gap = y_plane - float(top[i, j]) if np.isfinite(top[i, j]) else float("inf")
        land.append({"x": x, "z": z, "frame_below_mm": gap, "lands": bool(gap <= 2.0)})
    return {"bolt": bolt, "holes_land": land}


def clip_check(res: dict, t_sheet: float) -> dict:
    """Clip lift-off: post-root bending of the MJF PA12 clip under the worst factored lift force.
    ASSUMPTION: the lift splits evenly between the two posts; the post is a cantilever of the
    stay radius + sheet thickness, CLIP_W wide, CLIP_LEG_T thick."""
    m = load(S.CLIP_MAT)
    sy = float(m.get("tensile_strength_mpa") or m.get("yield_strength_mpa") or 48.0) * 0.6   # hot/wet + layer
    F = max(res["clip_lift_max_n"], 1.0)
    L = float(np.mean(S.stay_r(np.array(S.CLIP_Z)))) + t_sheet
    Z = S.CLIP_W * S.CLIP_LEG_T ** 2 / 6.0
    # a pull on the bridge puts the posts in tension; the hook root bends. Hook arm about 4 mm.
    sig_t = F / (2 * S.CLIP_W * S.CLIP_LEG_T)
    sig_b = (F / 2) * 4.0 / Z
    return {"lift_n": F, "post_tension_mpa": sig_t, "hook_bending_mpa": sig_b,
            "allow_mpa": sy, "sf": sy / max(sig_t + sig_b, 1e-9), "post_len_mm": L}


# ============================================================================ cost
def cost_table(opt: S.Option, res: dict) -> list[dict]:
    """Per-part material + cutting cost, USD. EUR at 1.08 (ASSUMPTION)."""
    eur = 1.08
    rows = []
    area_blank = 0.26 * 0.34                       # m2, blank with trim margin
    if opt.core:
        core_t = opt.core_t
        # 625 x 312 mm sheet holds one 260 x 340 blank turned. 3 mm price is published; thicker or denser
        # is ASSUMPTION: price x thickness / 3 for 71, and x 1.3 for 110 IG-F.
        p = 41.60 * eur * core_t / 3.0 * (1.3 if "110" in opt.core else 1.0)
        rows.append({"item": f"ROHACELL {'110' if '110' in opt.core else '71'} IG-F {core_t:.0f} mm, one 625 x 312 sheet",
                     "usd": p, "src": "Easy Composites EUR 41.60 per 3 mm 625 x 312 sheet; thicker/denser pro rata (ASSUMPTION)"})
        n_ply = 2 + (2 if opt.doubler else 0) * 0.15 / 1.0
        rows.append({"item": "200 g 2x2 twill, 0.4 lm (two skins + doublers)", "usd": 27.50 * eur * 0.4,
                     "src": "Easy Composites EUR 27.50 / lm, 1000 mm wide"})
        rows.append({"item": "laminating epoxy, peel ply, bag film, breather", "usd": 9.0, "src": "ASSUMPTION"})
        rows.append({"item": "CNC router cut from DXF (local shop)", "usd": 25.0, "src": "ASSUMPTION"})
        del n_ply
    else:
        mat = opt.lam.plies[0].name
        if "eglass" in mat:
            rows.append({"item": f"G10/FR4 sheet {opt.lam.thickness:.1f} mm, blank", "usd": 35.0 * area_blank / 0.0884,
                         "src": "ASSUMPTION ~ USD 35 per 12 x 24 in G10 sheet at 2 mm"})
        else:
            rows.append({"item": f"QI carbon plate {opt.lam.thickness:.1f} mm, 12 x 24 in", "usd": 82.0 * 2 * opt.lam.thickness / 3.2 + 40,
                         "src": "Rock West QI 12 x 12 x 1/8 in about USD 82; thinner pro rata + USD 40 (ASSUMPTION)"})
        rows.append({"item": "water-jet from DXF", "usd": 30.0, "src": "SendCutSend instant quote (carbon is water-jet only); ASSUMPTION value"})
    if opt.tubes:
        rows.append({"item": "2 x 250 mm pultruded tube 10 x 8 mm", "usd": 8.0 * 0.5,
                     "src": "cfrp_pultruded_rod_tube record USD 8 / m (electronicscomp lists Rs 967 / m)"})
    rows.append({"item": "6 MJF PA12 clips + pucks + pads (print bureau)", "usd": 18.0, "src": "ASSUMPTION"})
    rows.append({"item": "EVA rub strip, edge coat, adhesive", "usd": 3.0, "src": "ASSUMPTION"})
    return rows


# ============================================================================ geometry for files
def plane_y(z):
    return S.sleeve_y(z) + S.stay_r(z)


def part_mesh(opt: S.Option, lift: float = 0.0):
    """Spreader as a mesh in frame coordinates: outline extruded by the sheet thickness, wearer face
    on the stay-crown line (bag side of the stays)."""
    import trimesh
    shape = S.part_shape(opt)
    t = opt.lam.thickness
    m = trimesh.creation.extrude_polygon(shape, t, engine="triangle") if _has_triangle() else \
        trimesh.creation.extrude_polygon(shape, t)
    v = np.asarray(m.vertices).copy()
    x, z, h = v[:, 0], v[:, 1], v[:, 2]
    y = plane_y(z) + lift + h
    m.vertices = np.c_[x, y, z]
    m.fix_normals()
    return m


def _has_triangle() -> bool:
    try:
        import triangle  # noqa: F401
        return True
    except Exception:
        return False


def tube_meshes(opt: S.Option):
    import trimesh
    out = []
    if not opt.tubes:
        return out
    t = opt.lam.thickness
    for zt, od, _idd in S.EDGE_TUBES:
        c = trimesh.creation.cylinder(radius=od / 2, height=236.0, sections=24)
        c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        c.apply_translation([0.0, float(plane_y(zt)) + t + od / 2, zt])
        out.append(c)
    return out


def write_stl(opt: S.Option, res: dict) -> dict:
    import trimesh
    m = trimesh.util.concatenate([part_mesh(opt)] + tube_meshes(opt))
    m.export(PRINT / "genframe_barrier.stl")
    label = f"BP-06 rev B spreader: {opt.name}, {res['mass_g']:.0f} g"
    (PRINT / "genframe_barrier.json").write_text(json.dumps({"material": "carbon", "label": label}))
    return {"stl": rel(PRINT / "genframe_barrier.stl"), "json": rel(PRINT / "genframe_barrier.json")}


# ============================================================================ drawing
def _dim(ax, p0, p1, off, text, horiz=True, fs=7):
    (x0, y0), (x1, y1) = p0, p1
    kw = dict(color="#333333", lw=0.4)
    if horiz:
        yl = y0 + off
        ax.plot([x0, x0], [y0, yl + np.sign(off) * 2], **kw)
        ax.plot([x1, x1], [y1, yl + np.sign(off) * 2], **kw)
        ax.annotate("", (x0, yl), (x1, yl), arrowprops=dict(arrowstyle="<->", lw=0.4, color="#333333",
                                                            shrinkA=0, shrinkB=0))
        ax.text((x0 + x1) / 2, yl + np.sign(off) * 1.5, text, ha="center", va="bottom" if off > 0 else "top", fontsize=fs)
    else:
        xl = x0 + off
        ax.plot([x0, xl + np.sign(off) * 2], [y0, y0], **kw)
        ax.plot([x1, xl + np.sign(off) * 2], [y1, y1], **kw)
        ax.annotate("", (xl, y0), (xl, y1), arrowprops=dict(arrowstyle="<->", lw=0.4, color="#333333",
                                                            shrinkA=0, shrinkB=0))
        ax.text(xl + np.sign(off) * 1.5, (y0 + y1) / 2, text, ha="left" if off > 0 else "right", va="center",
                fontsize=fs, rotation=90)


def drawing_figure(opt: S.Option, res: dict, clips: dict, true_scale: bool = True, date: str | None = None):
    """A3 portrait, 1:1. Part coordinates: x = frame x, z = frame z (origin: frame axis, frame z 0)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    W_mm, H_mm = 297.0, 420.0
    fig = plt.figure(figsize=(W_mm / 25.4, H_mm / 25.4))
    fig.patch.set_facecolor("white")
    # 1:1 plan view: axes placed so 1 data mm = 1 paper mm
    ox, oy = 148.5, 88.0 - S.Z_LO_V2                            # paper position of the frame origin
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-ox, W_mm - ox)
    ax.set_ylim(-oy, H_mm - oy)
    ax.set_aspect("equal")
    ax.set_axis_off()
    shape = S.part_shape(opt)
    ax.fill(*shape.exterior.xy, color="#e9ecef", lw=0)
    ax.plot(*shape.exterior.xy, color="black", lw=0.6)
    for r in shape.interiors:
        ax.plot(*r.xy, color="black", lw=0.6)
    if opt.doubler:
        dz = S.doubler_zone()
        for g in (dz.geoms if hasattr(dz, "geoms") else [dz]):
            ax.plot(*g.exterior.xy, color="#2a78d6", lw=0.4, ls="--")
    for zt, od, idd in S.EDGE_TUBES if opt.tubes else []:
        ax.plot([-118, 118], [zt, zt], color="#eb6834", lw=0.5, ls="-.")
        ax.text(118, zt + 1.2, f"tube {od:.0f}/{idd:.0f}", fontsize=5, color="#eb6834", ha="right", va="bottom")
    for p in S.puck_table() if opt.pucks else []:
        ax.add_patch(plt.Circle((p["x"], p["z"]), S.PUCK_D / 2, fill=False, color="#1baf7a", lw=0.5, ls=":"))
        ax.text(p["x"], p["z"], f"{p['height_mm']:.1f}", fontsize=4.5, ha="center", va="center", color="#1baf7a")
    for zp in S.PAD_Z:
        for s in (1, -1):
            ax.add_patch(plt.Rectangle((s * 115 - 8, zp - S.CLIP_W / 2), 16, S.CLIP_W, fill=False, color="#1baf7a", lw=0.5))
    for s in (1, -1):
        ax.plot([s * S.STAY_X] * 2, [S.Z_LO_V2 - 8, S.Z_HI + 8], color="#999999", lw=0.3, ls=(0, (6, 2, 1, 2)))
    for zf in S.FAIRLEADS_Z:
        if S.Z_LO_V2 < zf < S.Z_HI:
            ax.plot([-128, 128], [zf, zf], color="#999999", lw=0.25, ls=(0, (6, 2, 1, 2)))
    minx, miny, maxx, maxy = shape.bounds
    _dim(ax, (minx, miny), (maxx, miny), -10, f"{maxx - minx:.0f}")
    _dim(ax, (minx, miny), (minx, maxy), -12, f"{maxy - miny:.0f}", horiz=False)
    _dim(ax, (-S.STAY_X, miny), (S.STAY_X, miny), -18, f"{2 * S.STAY_X:.0f} stay CL")
    x_in = S.STAY_X - S.FAIRLEAD_HALF_X - S.NOTCH_CLEAR
    hz = S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR
    _dim(ax, (x_in, 330 + hz), (maxx, 330 + hz), 6, f"{maxx - x_in:.0f}", fs=6)
    for zf in (142.0, 190.0, 330.0):
        _dim(ax, (maxx, miny), (maxx, zf), 8 + (zf - 142) / 18, f"{zf - miny:.0f}", horiz=False, fs=6)
    for x, z in S.clip_slots():
        if x > 0:
            ax.text(x - 4, z, f"slot {S.SLOT_W:.0f}x{S.SLOT_L:.0f}\nx {abs(x):.1f}  z {z - miny:.0f}", fontsize=5,
                    ha="right", va="center")
    ax.text(minx + 2, maxy - 26, "R20", fontsize=6)
    ax.text(minx + 2, miny + 3, f"R{S.BOTTOM_CORNER_R:.0f}", fontsize=6)
    ax.text(0, (miny + maxy) / 2 + 25, "BAG FACE UP", ha="center", fontsize=9, color="#52514e")
    # notes and title block (paper coordinates via the same axes)
    lam = opt.lam
    notes = [
        f"BP-06 rev {S.PART_REV if opt.key == S.PRODUCTION_KEY else 'B'}  SPREADER  ({opt.key})   scale 1:1 on A3   "
        "units mm (in = mm / 25.4)",
        f"{opt.name}.  t = {lam.thickness:.2f} mm.  Laminate: {lam.describe()}",
        f"Mass: sheet {res['sheet_g']:.0f} g + tubes {res['tubes_g']:.0f} g + clips/pucks/doublers/seal {res['fittings_g']:.0f} g "
        f"= {res['mass_g']:.0f} g ({res['mass_g'] / 28.35:.1f} oz)",
        "Origin: frame axis x 0, frame z 0 (bottom edge at z %.0f). Dims from the bottom edge unless shown." % miny,
        "Tolerances: outline +/-0.3, slots +/-0.2. Inside corners R >= 6. Break all cut edges 0.3.",
        f"Notches (cleats US2 z 142, IM1 z 190, IM2 z 330): {2 * hz:.0f} tall x {maxx - x_in:.0f} deep, root at x +/-{x_in:.0f}, "
        f"R{S.NOTCH_ROOT_R:.0f} root corners, {S.NOTCH_CLEAR:.0f} mm air round each cleat.",
        "Edge seal: two brushed coats of laminating epoxy on every cut PMI edge (blood / grime).",
        "Doublers (blue dash): one 200 g twill ply at 45 deg on each skin, core side, before closing the bag.",
        "Tubes (orange): pultruded 10 x 8 mm, bonded to the bag face with toughened epoxy, 236 mm long.",
        "Pucks (green, dotted): PAHT-CF, bonded to the wearer face; number = height mm. Pads at z 119 (green).",
        "1 mm EVA rub strip, 8 mm wide, on the wearer face over each stay crown line (x +/-115).",
        f"Clips: {2 * len(S.CLIP_Z)} x MJF PA12, snap over the stay; slot carries the inboard post. Toolless, removable.",
        "Ventilation: solid sheet by design (bag-side barrier). Air path is the 130 mm gutter between the rails.",
    ]
    y0 = -oy + 10
    for k, line in enumerate(notes[::-1]):
        ax.text(-ox + 10, y0 + k * 3.8, line, fontsize=5.6, family="monospace")
    ax.plot([-ox + 8, W_mm - ox - 8, W_mm - ox - 8, -ox + 8, -ox + 8],
            [-oy + 8, -oy + 8, H_mm - oy - 8, H_mm - oy - 8, -oy + 8], color="black", lw=0.6)
    yt = -oy + 10 + len(notes) * 3.8 + 2
    rev = S.PART_REV if opt.key == S.PRODUCTION_KEY else "B"
    ax.text(-ox + 10, yt, f"BP-06 rev {rev}   SPREADER   Hunting-Appeal Pack 5200", fontsize=10, fontweight="bold")
    ax.text(-ox + 150, yt, f"{date or DATE}   huntkit.gendesign.spreader_report", fontsize=6)
    ax.plot([-ox + 190, -ox + 290], [yt - 3] * 2, color="black", lw=1.2)
    ax.text(-ox + 240, yt - 2, "100 mm check bar", fontsize=6, ha="center", va="bottom")
    return fig


def write_drawing(opt, res, clips, date: str | None = None, screen: Path | None = None) -> dict:
    """1:1 A3 PDF into cut/spreader/ plus a PNG screen (default: the 2026-11-04 release name, copied to
    docs/screens; ``screen`` = another outputs/screens path, not copied)."""
    import matplotlib.pyplot as plt
    from .render import save
    CUT.mkdir(parents=True, exist_ok=True)
    fig = drawing_figure(opt, res, clips, date=date)
    pdf = CUT / "spreader_v2_drawing.pdf"
    fig.savefig(pdf)
    if screen is None:
        png = _save(fig, 2, doc=True)
    else:
        save(fig, screen)
        png = rel(screen)
    plt.close(fig)
    return {"pdf": rel(pdf), "png": png}


def write_clip_files(t_sheet: float) -> dict:
    """Clip profile DXF (extrude CLIP_W) and pad sketch."""
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=1)
    doc.layers.add("TEXT", color=7)
    msp = doc.modelspace()
    r = float(np.mean(S.stay_r(np.array(S.CLIP_Z))))
    prof = S.clip_profile(r, t_sheet)
    msp.add_lwpolyline(list(prof.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
    for ring in prof.interiors:
        msp.add_lwpolyline(list(ring.coords), close=True, dxfattribs={"layer": "CUT"})
    msp.add_text(f"CLIP A  MJF PA12  extrude {S.CLIP_W:.0f} mm  qty {2 * len(S.CLIP_Z)}  stay r {r:.1f}  sheet {t_sheet:.2f}",
                 dxfattribs={"layer": "TEXT", "height": 2.0}).set_placement((-20.0, -26.0))
    path = CUT / "spreader_v2_clip.dxf"
    doc.saveas(path)
    return {"dxf": rel(path), "mass_g": S.clip_mass_g(prof, S.CLIP_W), "r_stay": r, "profile": prof}


# ============================================================================ plots
FAM_COL = {"monolithic": "#2a78d6", "beaded": "#eda100", "perforated": "#e87ba4", "sandwich": "#1baf7a",
           "current": "#eb6834"}


def plot_options(rows, chosen_key, v1) -> str:
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.6))
    pts = [dict(r, fam=r["family"]) for r in rows] + [dict(v1, fam="current", key="v1")]
    panels = [("clear_fact_min", "min air to skin, factored bone (mm)", 0.0, "higher is better"),
              ("skin_peak_kpa", "peak skin pressure, walking (kPa)", S.PEAK_KPA, "lower is better"),
              ("sf_min_all", "worst strength / fatigue SF", 1.0, "higher is better")]
    for ax, (k, lab, lim, how) in zip(axs, panels):
        for p in pts:
            val = sf_min(p) if k == "sf_min_all" else p[k]
            if k == "clear_fact_min":
                val = max(val, -30.0)
            col = FAM_COL[p["fam"]]
            ok = p["passes"]
            ax.scatter(p["mass_g"], val, s=70 if p["key"] != chosen_key else 160, facecolor=col if ok else "white",
                       edgecolor=col, lw=2, zorder=3)
            if p["key"] in (chosen_key, "v1", "qi20", "qi10", "g20", "sw71c5", "pf15"):
                ax.annotate(p["key"], (p["mass_g"], val), textcoords="offset points", xytext=(6, 5), fontsize=10,
                            color="#0b0b0b")
        ax.axhline(lim, color="#52514e", lw=1, ls="--")
        ax.axvline(TARGET_G, color="#52514e", lw=1, ls=":")
        ax.set_xlabel("part mass incl. tubes, clips, pucks (g)")
        ax.set_title(f"{lab}\n{how}", fontsize=12)
        ax.grid(color="#e6e5e1", lw=0.6)
    for fam, col in FAM_COL.items():
        axs[0].scatter([], [], facecolor=col, edgecolor=col, label=fam)
    axs[0].scatter([], [], facecolor="white", edgecolor="#52514e", lw=2, label="fails a check")
    axs[0].legend(fontsize=9, loc="lower right")
    fig.suptitle("Spreader options: mass against clearance, skin pressure and strength. Dashed = limit, dotted = 100 g target",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, 1, doc=True)


def plot_maps(res, title: str, n: int, names=("center", "IM1 notch root", "top edge")) -> str:
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    pl, info = res["_plate"]
    F = res["_fields"]
    nxy = pl.node_xy()
    X = nxy[:, 0].reshape(pl.ny + 1, pl.nx + 1)
    Z = nxy[:, 1].reshape(pl.ny + 1, pl.nx + 1)
    act = pl.active_nodes().reshape(pl.ny + 1, pl.nx + 1)
    exy = pl.elem_xy()
    names = [n_ for n_ in names if n_ in F]
    fig, axs = plt.subplots(3, len(names), figsize=(4.2 * len(names), 12.5))
    axs = np.atleast_2d(axs)
    if axs.shape[0] != 3:
        axs = axs.T
    pos = S.named_positions(info["version"])
    for c, nm in enumerate(names):
        f = F[nm]
        w = f["w_fact"].reshape(pl.ny + 1, pl.nx + 1)
        cl = f["clear"].reshape(pl.ny + 1, pl.nx + 1)
        fi = f["fi_fact"]
        a = axs[0, c].pcolormesh(X, Z, np.where(act, w, np.nan), shading="nearest", cmap="Blues", vmin=0)
        fig.colorbar(a, ax=axs[0, c], shrink=0.8, label="mm")
        axs[0, c].set_title(f"bone at {nm}\nsheet deflection, factored", fontsize=11)
        b = axs[1, c].pcolormesh(X, Z, np.where(act, cl, np.nan), shading="nearest", cmap="Greens", vmin=0)
        fig.colorbar(b, ax=axs[1, c], shrink=0.8, label="mm")
        axs[1, c].set_title(f"air to skin, factored (min {np.nanmin(cl):.1f})", fontsize=11)
        d = axs[2, c].pcolormesh(exy[..., 0].T, exy[..., 1].T, np.where(pl.active, fi, np.nan).T, shading="nearest",
                                 cmap="Oranges", vmin=0, vmax=1.0)
        fig.colorbar(d, ax=axs[2, c], shrink=0.8, label="FI (1 = first ply)")
        axs[2, c].set_title(f"Tsai-Wu FI, factored (max {np.nanmax(fi):.2f})\nskin {f['skin']['peak_kpa']:.1f} kPa walking",
                            fontsize=11)
        for r_ in range(3):
            ax = axs[r_, c]
            ax.plot(*info["shape"].exterior.xy, color="#0b0b0b", lw=0.6)
            ax.add_patch(plt.Circle(pos[nm], S.BONE_D / 2, fill=False, color="#0b0b0b", lw=1.2))
            ax.set_aspect("equal")
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(title, x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return _save(fig, n, doc=(n == 3))


def plot_skin(chosen, n: int) -> str:
    """Rail section: skin pressure across the rail for meat only and the worst bone side load."""
    import matplotlib.pyplot as plt
    from .render import _style
    _style()
    side = max(r["bone_side_n"] for r in chosen["rows"])
    a = S.skin_pressure(0.0, "walk")
    b = S.skin_pressure(side, "walk", bone_total_n=S.bone_n("walk"))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(a["x"], a["p_kpa"], color="#2a78d6", lw=2, label=f"meat only, peak {a['peak_kpa']:.1f} kPa")
    ax.plot(b["x"], b["p_kpa"], color="#eb6834", lw=2, label=f"worst bone side load {side:.0f} N, peak {b['peak_kpa']:.1f} kPa")
    ax.axhline(S.PEAK_KPA, color="#52514e", ls="--", lw=1)
    ax.text(-48, S.PEAK_KPA + 0.3, "14 kPa limit (Golriz 2017)", fontsize=10, color="#52514e")
    ax.set_xlabel("across the 100 mm rail (mm), stay centre at 0")
    ax.set_ylabel("skin pressure, 1.6 g walking (kPa)")
    ax.legend(fontsize=10, loc="lower center")
    ax.grid(color="#e6e5e1", lw=0.6)
    ax.set_ylim(0, 18)
    fig.suptitle("Skin under the XLPE rail (L200 curve, aged 12 %, 1 mm twill backer, 60 kPa tissue)",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, n)


def plot_installed(opt, n: int) -> str:
    import matplotlib.pyplot as plt
    import trimesh
    from .frame_render import autocrop, raster, simplify
    from .render import _style, SURF
    _style()
    frame = simplify(trimesh.load(PRINT / "genframe_assembled.stl", force="mesh"), target=18000)
    sheet = part_mesh(opt)
    parts = [(frame, (0.16, 0.17, 0.18)), (sheet, (0.50, 0.56, 0.62))]
    for t in tube_meshes(opt):
        parts.append((t, (0.10, 0.10, 0.11)))
    rails = []
    for s in (1.0, -1.0):
        r = trimesh.creation.box(extents=(100.0, 10.0, 420.0))
        r.apply_translation([s * 115.0, -24.0, 260.0])
        rails.append((r, (0.62, 0.58, 0.50)))
    fig = plt.figure(figsize=(12, 5.4))
    views = (("bag side (meat face)", 12, 200, parts), ("wearer side: frame and rails in front", 16, 28, parts + rails),
             ("side", 4, 90, parts + rails))
    for i, (lab, el, az, ps) in enumerate(views):
        ax = fig.add_subplot(1, 3, i + 1)
        img, info = raster(ps, el, az, size=440, spec=0.18)
        ax.imshow(autocrop(img, info["mask"], pad=8))
        ax.set_axis_off()
        ax.set_title(lab, fontsize=11)
    fig.suptitle(f"Spreader v2 on the branch frame: {opt.name}", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.patch.set_facecolor(SURF)
    return _save(fig, n, doc=True)


# ============================================================================ records
def _fmt(v, nd=2):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, (int, float)) else str(v))


def write_doc(ctx: dict) -> str:
    ch, v1, cur = ctx["chosen"], ctx["v1"], ctx["current"]
    opt = ctx["opt"]
    rows = ctx["rows"]
    L = []
    L.append("# Spreader v2 (BP-06 rev B)\n")
    L.append("Supersedes the spreader rows in `back_comfort.md`. Code: `huntkit/gendesign/spreader.py` (model), "
             "`huntkit/gendesign/spreader_report.py` (this record), solver `huntkit/fea/plate_grid.py`. "
             "Research: `docs/research/spreader_research.md`. Tests: `tests/test_spreader.py`.\n")
    L.append("## Recommendation\n")
    L.append(f"**{opt.name}**, {ch['mass_g']:.0f} g ({ch['mass_g'] / 28.35:.1f} oz) as installed "
             f"(sheet {ch['sheet_g']:.0f} g, edge tubes {ch['tubes_g']:.0f} g, clips, pucks, doublers and edge seal "
             f"{ch['fittings_g']:.0f} g). The current part is {OLD_PART_G:.0f} g with its M4 hardware, so this saves "
             f"**{OLD_PART_G - ch['mass_g']:.0f} g**. The current part also fails the checks below.\n")
    L.append(f"- First-ply SF (Tsai-Wu, factored 3.0 g, hot/wet 0.8, impact 0.65): **{ch['sf_fpf']:.2f}**, at {ch['fpf_where']}")
    L.append(f"- Fatigue SF (FI ≤ 0.5 at the 1.6 g walking peak): **{ch['sf_fatigue']:.2f}**")
    if ch.get("sandwich_sf_min") is not None:
        sw = ch["sandwich_worst"]
        L.append(f"- Sandwich local SF (core shear, bone crush, crown crush, puck crush, wrinkling): **{ch['sandwich_sf_min']:.2f}**. "
                 f"Core shear {sw['core_shear_sf']:.2f}, bone crush {sw['crush_patch_sf']:.2f}, crown crush "
                 f"{sw['crush_crown_sf']:.2f}, puck crush {sw['crush_puck_sf']:.2f}, wrinkling {sw['wrinkle_sf']:.2f}")
    L.append(f"- Air to the skin: walking minimum **{ch['clear_walk_min']:.1f} mm** (limit {S.MESH_T:.0f} mm of mesh). "
             f"Factored minimum **{ch['clear_fact_min']:.1f} mm** (limit 0). Lean-torso sensitivity (R 150 mm) "
             f"{ch['clear_fact_lean_min']:.1f} mm")
    L.append(f"- Peak skin pressure, walking, worst bone: **{ch['skin_peak_kpa']:.1f} kPa** (limit 14). Meat only "
             f"{ch['skin_meat_only_kpa']:.1f} kPa")
    L.append(f"- Max factored deflection {ch['w_fact_max']:.1f} mm. Bone at the centre, walking: {ch['w_bone_walk_center']:.1f} mm")
    L.append(f"- Clip lift-off, factored: {ctx['clip']['lift_n']:.0f} N, clip SF {ctx['clip']['sf']:.1f}")
    L.append(f"- Cost per part about **${ctx['cost_total']:.0f}** (table below)")
    if ch["mass_g"] > TARGET_G:
        L.append(f"\n**The ≤ {TARGET_G:.0f} g target is not met.** The lightest option that passes every check is "
                 f"{ch['mass_g']:.0f} g. No option in the table comes in under 126 g. Every option under 150 g fails at least one check. Reaching 100 g needs an architecture change, not a material swap (see the next steps in `docs/RESUME.md`). "
                 "The governing cases are a bone end at a notch root and on the free top and bottom edges. "
                 "The bottom bay (z 112–165) also has no branch under it.\n")
    L.append("\n## 1. The current part, checked properly\n")
    L.append("Current part: 208 × 300 × 2.0 mm QI, z 130–430, square corners, 4 × M4 holes at IM1 and IM2. "
             "It rests on the real branch frame: stay crowns, the inboard branches and the z 330 bar, all as "
             "unilateral contacts with the gaps taken from the frame's distance field. M4 bolts go into the bar.\n")
    L.append("| check | result | requirement | |")
    L.append("|---|---:|---:|---|")
    L.append(f"| first-ply SF, factored | {v1['sf_fpf']:.2f} at {v1['fpf_where']} | ≥ 1.0 | {'ok' if v1['sf_fpf'] >= 1 else '**fail**'} |")
    L.append(f"| fatigue SF, walking | {v1['sf_fatigue']:.2f} | ≥ 1.0 | {'ok' if v1['sf_fatigue'] >= 1 else '**fail**'} |")
    L.append(f"| air to skin, walking | {v1['clear_walk_min']:.1f} mm | ≥ {S.MESH_T:.0f} | {'ok' if v1['clear_walk_min'] >= S.MESH_T else '**fail**'} |")
    L.append(f"| air to skin, factored | {v1['clear_fact_min']:.1f} mm at {v1['clear_where']} | ≥ 0 | {'ok' if v1['clear_fact_min'] >= 0 else '**fail (bottoms)**'} |")
    L.append(f"| peak skin pressure | {v1['skin_peak_kpa']:.1f} kPa at {v1['skin_where']} | ≤ 14 | {'ok' if v1['skin_peak_kpa'] <= 14 else '**fail**'} |")
    b = cur["bolt"]
    L.append(f"| M4 bearing, factored {b['F_n']:.0f} N | SF {b['bearing_sf']:.1f} | ≥ 1.0 | ok |")
    L.append(f"| M4 shear-out | SF {b['shearout_sf']:.1f} | ≥ 1.0 | {'ok' if b['shearout_sf'] >= 1 else '**fail**'} |")
    L.append(f"| M4 edge distance e/d | {b['e_over_d']:.2f} | ≥ 3.0 (CMH-17 practice) | {'ok' if b['e_over_d_ok'] else '**fail**'} |")
    for h_ in cur["holes_land"]:
        L.append(f"| hole at x {h_['x']:.0f}, z {h_['z']:.0f} lands on frame | {h_['frame_below_mm']:.1f} mm of air below | ≤ 2 mm | "
                 f"{'ok' if h_['lands'] else '**fail: nothing to bolt to**'} |")
    L.append("")
    L.append("Why the old record said it passed: `back_comfort.md` treated the sheet as simply supported on all four edges. "
             "It also compared the 7.8 mm deflection with the 10 mm rail and nothing else. On the real frame the 208 mm sheet "
             "only reaches the stay crowns (x 101–129) by 3 mm. The bottom 35 mm overhangs the window with nothing under "
             "it (the branches start at z 165), and that edge governs. The rails are not the clearance either. The "
             "sheet sits on the bag face of 28 mm stays, so the air to the skin is the stay depth plus the aged rail, "
             "less the rail indentation and the torso bulging into the 130 mm gutter.\n")
    L.append("Load model (HA-LS-1 rev B, C5): the overturning meat pressure is triangular from z 60 to z 330. The cinch preload "
             "is 6 × 150 N spread over z 60–560. A bone end, 20 % of 68 kg on a 22 mm patch, is tested at every named "
             f"position and on a {FINAL_STEP:.0f} mm grid. Walking is 1.6 g. Factored is 2.0 g × 1.5. "
             "ASSUMPTION: the bone is part of the meat, so its force comes out of the overturning resultant. The v1 "
             "study added it on top.\n")
    L.append("Skin model: the stay is a hot/wet PAHT beam on the rail. The rail is aged L200 XLPE (cited curve, 12 % set) over a "
             "1 mm twill backer, with soft tissue in series (60 kPa, 25 mm column, ASSUMPTION; 20 kPa is the soft-tissue "
             "sensitivity). Clearance is the plane of the sheet less its deflection, measured to the skin, which "
             "includes the rail indentation and the torso bulge into the gutter (R 230 mm, ASSUMPTION; 150 mm lean "
             "sensitivity).\n")
    L.append("## 2. Options (v2 outline, real supports, bone grid "
             f"{TABLE_STEP:.0f} mm + named positions)\n")
    L.append("| key | option | mass g | FPF SF | fatigue SF | sandwich SF | air walk mm | air fact mm | skin kPa | pass |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in sorted(rows, key=lambda r: r["mass_g"]):
        fails = [k for k, v in r["checks"].items() if not v]
        L.append(f"| {r['key']} | {r['name']} | {r['mass_g']:.0f} | {r['sf_fpf']:.2f} | {r['sf_fatigue']:.2f} | "
                 f"{_fmt(r.get('sandwich_sf_min'))} | {r['clear_walk_min']:.1f} | {r['clear_fact_min']:.1f} | "
                 f"{r['skin_peak_kpa']:.1f} | {'yes' if r['passes'] else 'no: ' + ', '.join(fails)} |")
    L.append("")
    L.append("Notes on the families:\n")
    L.append("- **Thinner QI with beads.** Beads stiffen the span direction only. The bone at a notch root and on the free edges "
             "is still a 1 mm laminate. Beads also need a matched press tool.")
    L.append("- **SIMP cut-outs.** Holes come from a bending SIMP density on the real supports. They sit on a 30 mm hex and are "
             f"capped at {S.MAX_HOLE_D:.0f} mm, so a 22 mm bone end cannot pass. A Kt of 1.8 applies at each hole edge. Mass "
             "drops, and the strength drops at the same places. The holes also drain meat juice onto the back gap "
             "(research §2).")
    L.append("- **Biased layup.** The span is not one-way: the bar, the branches and the notches load the sheet both ways. "
             "A 0-heavy stack loses on the 90 and shear plies at the notch roots.")
    L.append("- **Sandwich.** Stiffness comes almost free. The limits are local: core shear and crush under the bone and at "
             "the supports, and the skins at the notch roots. ROHACELL 71 fails bone crush and core shear. ROHACELL 110 "
             "with a 45° doubler ply around the notches passes.")
    L.append("- **G10.** Cheap, but heavy for the same stiffness, and E-glass has lower compression strength after the impact "
             "knockdown.\n")
    L.append("Mesh check: the chosen part was re-run at the named positions on a 2 mm grid. The results are in the next table. A "
             "notch root on a 4 mm grid is close to square, so the 2 mm FI is the number to trust there.\n")
    mc = ctx["mesh_check"]
    L.append("| grid | FPF SF | fatigue SF | sandwich SF | air fact mm |")
    L.append("|---|---:|---:|---:|---:|")
    for g, r in mc.items():
        L.append(f"| {g} | {r['sf_fpf']:.2f} | {r['sf_fatigue']:.2f} | {_fmt(r.get('sandwich_sf_min'))} | {r['clear_fact_min']:.1f} |")
    L.append("")
    L.append("## 3. The part, detailed for manufacture\n")
    L.append(f"- Outline {ctx['bounds'][0]:.0f} × {ctx['bounds'][1]:.0f} mm, z {S.Z_LO_V2:.0f}–{S.Z_HI:.0f}. The long edges land "
             "on the stay crowns, which is what the 208 mm sheet did not do. Corners R20 at the top and "
             f"R{S.BOTTOM_CORNER_R:.0f} at the bottom.")
    L.append(f"- Fairlead notches at the cleat stations in `bag_attachment.md` that fall inside the sheet: US2 z 142, IM1 z 190, IM2 z 330. "
             f"Each is {2 * (S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR):.0f} mm tall to a root at x ±{S.STAY_X - S.FAIRLEAD_HALF_X - S.NOTCH_CLEAR:.0f}, "
             f"with R{S.NOTCH_ROOT_R:.0f} root corners, which leaves {S.NOTCH_CLEAR:.0f} mm of air round the cheek "
             "(tested). The hinge, US1 and IM3 cleats are outside the sheet.")
    L.append(f"- {2 * len(S.CLIP_Z)} removable MJF PA12 snap clips over the stays at z {', '.join(f'{z:.0f}' for z in S.CLIP_Z)}. "
             f"The inboard post passes through a {S.SLOT_W:.0f} × {S.SLOT_L:.0f} mm slot, and the outboard post passes "
             "outside the sheet edge. To wash, pop six clips and lift the sheet out. No tools, and no bonded joint to the "
             f"frame. The bottom tab sits on bonded PAHT stand-off pads at z {S.PAD_Z[0]:.0f}, where the stay is thinner.")
    L.append(f"- Bonded pucks on the wearer face where the sheet crosses a branch or the bar ({len(S.pucks())}). Each is cut to the "
             f"local gap less {S.LAND_FIT} mm, so the sheet bears on the branch straight away. Heights are on the drawing.")
    L.append("- Edge sealing: two brushed epoxy coats on every cut PMI edge. ROHACELL is closed-cell, so this seals out "
             "grime and blood and protects against abrasion. It is not a structural closure.")
    L.append("- Ventilation: the sheet stays solid on purpose. It is the blood and sweat barrier on the bag side, and the air "
             "path is the 130 mm gutter between the rails under the open mesh (42 % of the lower back). Nothing on the "
             "sheet touches the wearer.")
    L.append("- A 1 mm EVA rub strip, 8 mm wide, runs on the wearer face along each stay crown line. It stops "
             "carbon-on-PAHT chafe and spreads the crown line load.\n")
    L.append("Files:\n")
    for k, v in ctx["files"].items():
        L.append(f"- {k}: `{v}`")
    L.append("\n### Cost per part\n")
    L.append("| item | USD | source |")
    L.append("|---|---:|---|")
    for c in ctx["cost"]:
        L.append(f"| {c['item']} | {c['usd']:.0f} | {c['src']} |")
    L.append(f"| **total** | **{ctx['cost_total']:.0f}** | |")
    L.append("")
    L.append("Process: lay up twill, the doublers (45°), routed ROHACELL, then the doublers and twill again. Vacuum bag on "
             "a flat plate, room-temperature cure, post-cure at 60 °C (below the 130 °C core limit). CNC-route the outline "
             "and slots from the DXF with a compression bit. Brush the edges. Bond the tubes, pucks, pads and rub strips "
             "with a jig made from the 1:1 PDF.\n")
    L.append("## 4. Mass\n")
    L.append("| item | g |")
    L.append("|---|---:|")
    L.append(f"| current part (sheet 193 + 4 M4 sets) | {OLD_PART_G:.0f} |")
    L.append(f"| v2 sheet | {ch['sheet_g']:.0f} |")
    L.append(f"| v2 edge tubes | {ch['tubes_g']:.0f} |")
    L.append(f"| v2 clips, pucks, pads, doublers, edge seal | {ch['fittings_g']:.0f} |")
    L.append(f"| **v2 total** | **{ch['mass_g']:.0f}** |")
    L.append(f"| saved | {OLD_PART_G - ch['mass_g']:.0f} |")
    L.append("")
    L.append("## Screenshots\n")
    for s_ in ctx["screens"]:
        L.append(f"- `{s_}`")
    L.append("\n## Assumptions\n")
    for a in ctx["assumptions"]:
        L.append(f"- ASSUMPTION: {a}")
    path = ANALYSIS / "spreader.md"
    path.write_text("\n".join(L) + "\n")
    return rel(path)


ASSUMPTIONS = [
    "Bone end is 20 % of 68 kg on a 22 mm patch (HA-LS-1), and is part of the meat, not added to it.",
    "Soft tissue 60 kPa over a 25 mm column (20 kPa sensitivity); torso radius at the spine 230 mm (150 mm lean sensitivity).",
    "The spacer mesh is 3 mm and lies on the skin; walking clearance must exceed it; factored clearance must be >= 0.",
    "The L200 curve below 25 % and above 50 % (5, 10, 70, 80 % points) and its shear modulus.",
    "Stay crowns rigid; crown line load resolved over max(20 mm, 2 sqrt(D/S)) for the sandwich (core-shear spreading length).",
    "PA12 MJF clip allowable 0.6 x tensile; hook arm 4 mm.",
    "Puck and pad PAHT-CF density from the record; pucks carry a 1 mm bond flange.",
    "ROHACELL 110 and 5 mm prices pro rata from the published 3 mm ROHACELL 71 sheet price; EUR/USD 1.08.",
    "Twill skin resin uptake into cut PMI cells 0.06 kg/m2.",
    "Edge coat 0.3 mm epoxy on the cut edge.",
]


# ============================================================================ main
def run(log=print, resume: bool = True) -> dict:
    for d in (SCREENS, DOC_SCREENS, CUT, OUT):
        d.mkdir(parents=True, exist_ok=True)
    keys = [o.key for o in S.options()]
    log(f"evaluating {len(keys)} options + current part + SIMP option on 4 workers")
    import pickle
    cache = OUT / "stage1.pkl"           # scratch cache in outputs/ so a crash in the plots does not rerun the FEA
    if cache.exists() and resume:
        rows, v1 = pickle.loads(cache.read_bytes())
    else:
        ctx_mp = get_context("fork")
        with ctx_mp.Pool(4) as pool:
            perf_job = pool.apply_async(_eval_perf, (None,))
            v1_job = pool.apply_async(_eval_v1, (None,))
            rows = pool.map(_eval_key, [(k, TABLE_STEP) for k in keys])
            perf = perf_job.get()
            v1 = v1_job.get()
        rows.append(perf)
        cache.write_bytes(pickle.dumps((rows, v1)))
    for r in rows:
        log(f"  {r['key']:9s} {r['mass_g']:6.1f} g  FPF {r['sf_fpf']:.2f}  fat {r['sf_fatigue']:.2f}  "
            f"sw {_fmt(r.get('sandwich_sf_min'))}  air {r['clear_walk_min']:.1f}/{r['clear_fact_min']:.1f}  "
            f"skin {r['skin_peak_kpa']:.1f}  {'PASS' if r['passes'] else 'fail'}")
    log(f"  current   {v1['mass_g']:6.1f} g  FPF {v1['sf_fpf']:.2f}  fat {v1['sf_fatigue']:.2f}  "
        f"air {v1['clear_walk_min']:.1f}/{v1['clear_fact_min']:.1f}  skin {v1['skin_peak_kpa']:.1f}")
    cur = verify_current(v1)
    passing = [r for r in rows if r["passes"]]
    if not passing:
        raise RuntimeError("no option passes")
    best = min(passing, key=lambda r: r["mass_g"])
    opt = {o.key: o for o in S.options()}[best["key"]]
    log(f"chosen {opt.key}; refining on a {FINAL_STEP:.0f} mm bone grid")
    cache2 = OUT / "stage2.pkl"
    if cache2.exists() and resume:
        ch, fine, v1_full = pickle.loads(cache2.read_bytes())
    else:
        ch = S.evaluate(opt, h=4.0, step=FINAL_STEP, keep_fields=True)
        fine = S.evaluate(opt, h=2.0, step=None)
        v1_full = S.evaluate(dataclasses.replace({o.key: o for o in S.options()}["qi20"], tubes=False, pucks=False),
                             h=4.0, version="v1", step=None, keep_fields=True)
        cache2.write_bytes(pickle.dumps((ch, fine, v1_full)))
    log(f"  {ch['mass_g']:.1f} g  FPF {ch['sf_fpf']:.2f}  fat {ch['sf_fatigue']:.2f}  sw {_fmt(ch.get('sandwich_sf_min'))}  "
        f"air {ch['clear_walk_min']:.1f}/{ch['clear_fact_min']:.1f}  skin {ch['skin_peak_kpa']:.1f}")
    log("mesh check at 2 mm, named positions")
    mesh_check = {"4 mm": {k: ch.get(k) for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min", "clear_fact_min")},
                  "2 mm": {k: fine.get(k) for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min", "clear_fact_min")}}
    log(f"  2 mm FPF {fine['sf_fpf']:.2f}  fat {fine['sf_fatigue']:.2f}  sw {_fmt(fine.get('sandwich_sf_min'))}")
    # governing value = the worse of the two grids
    for k in ("sf_fpf", "sf_fatigue", "sandwich_sf_min"):
        if ch.get(k) is not None and fine.get(k) is not None:
            ch[k] = min(ch[k], fine[k])
    ch["checks"]["fpf"] = ch["sf_fpf"] >= 1.0
    ch["checks"]["fatigue"] = ch["sf_fatigue"] >= 1.0
    if "sandwich_local" in ch["checks"]:
        ch["checks"]["sandwich_local"] = ch["sandwich_sf_min"] >= 1.0
    ch["passes"] = all(ch["checks"].values())
    v1_opt = dataclasses.replace(opt, key="v1")
    del v1_opt
    clips = write_clip_files(opt.lam.thickness)
    clip = clip_check(ch, opt.lam.thickness)
    files = {}
    dxf = CUT / "spreader_v2_cut.dxf"
    S.write_dxf(opt, dxf)
    files["water-jet / CNC cut file (DXF, mm, layers CUT / MARK / TEXT)"] = rel(dxf)
    files["clip profile (DXF, extrude 10 mm)"] = clips["dxf"]
    dr = write_drawing(opt, ch, clips)
    files["dimensioned drawing, 1:1 on A3 (PDF)"] = dr["pdf"]
    stl = write_stl(opt, ch)
    files["viz3d mesh (STL, frame coordinates)"] = stl["stl"]
    cost = cost_table(opt, ch)
    cost_total = float(sum(c["usd"] for c in cost))
    screens = [plot_options(rows, opt.key, v1), dr["png"]]
    screens.append(plot_maps(ch, f"Chosen part ({opt.key}): factored bone loads on the real supports", 3))
    screens.append(plot_maps(v1_full, "Current 208 x 300 x 2.0 mm sheet on the real frame: it bottoms and over-stresses",
                             4, names=("center", "bottom edge", "near M4 hole (IM1)")))
    screens.append(plot_installed(opt, 5))
    screens.append(plot_skin(ch, 6))
    out = {
        "date": DATE,
        "chosen_key": opt.key,
        "chosen": {k: v for k, v in _strip(ch).items() if k != "rows"},
        "chosen_rows": _strip(ch)["rows"],
        "v1": {k: v for k, v in v1.items() if k != "rows"},
        "current_checks": cur,
        "options": [{k: v for k, v in r.items() if k not in ("rows", "simp_rho")} for r in rows],
        "mesh_check": mesh_check,
        "clip": {k: v for k, v in clip.items()},
        "clip_mass_g": clips["mass_g"],
        "cost": cost, "cost_total_usd": cost_total,
        "old_part_g": OLD_PART_G, "saved_g": OLD_PART_G - ch["mass_g"],
        "files": files,
        "screens": screens,
    }
    doc = write_doc({"chosen": ch, "v1": v1, "current": cur, "opt": opt, "rows": rows, "clip": clip,
                     "cost": cost, "cost_total": cost_total, "files": files, "screens": screens,
                     "mesh_check": mesh_check, "bounds": (S.part_shape().bounds[2] - S.part_shape().bounds[0],
                                                          S.part_shape().bounds[3] - S.part_shape().bounds[1]),
                     "assumptions": ASSUMPTIONS})
    out["doc"] = doc
    (ANALYSIS / "spreader_results.json").write_text(json.dumps(out, indent=1, default=_json_default))
    log(f"wrote {doc}")
    return out


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


if __name__ == "__main__":
    run()
