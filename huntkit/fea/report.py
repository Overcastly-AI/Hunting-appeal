"""Markdown + PNG reports for FEA results.

``report(obj, path)`` accepts
- a single :class:`frame.Result`,
- a study dict from :func:`analysis.run_study`,
- a list of study dicts (comparison report, e.g. the CLI demo).
``path`` may be a directory (``report.md`` is written inside) or a ``.md`` file path.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import colors as mcolors  # noqa: E402

from .analysis import summarize  # noqa: E402
from .frame import Result, rigid_body_modes  # noqa: E402

LB_PER_KG = 2.20462
OZ_PER_G = 1 / 28.3495
INK = "#333333"
MUTED = "#9a9a9a"
DEFORMED = "#2a6fb0"
CMAP = plt.get_cmap("Oranges")     # sequential, one hue: utilisation magnitude


def _paths(path, stem="report"):
    p = Path(path)
    if p.suffix.lower() == ".md":
        p.parent.mkdir(parents=True, exist_ok=True)
        return p, p.parent
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{stem}.md", p


def _fmt(x, nd=2):
    if x is None:
        return "-"
    if isinstance(x, (float, np.floating)):
        if not np.isfinite(x):
            return "inf"
        return f"{x:.{nd}f}"
    return str(x)


def _elastic_u(res: Result) -> np.ndarray:
    """Displacements with the best-fit rigid-body motion (on the body springs) removed."""
    Phi = rigid_body_modes(res.coords)
    a, *_ = np.linalg.lstsq(Phi, res.u, rcond=None)
    return (res.u - Phi @ a).reshape(-1, 6)[:, :3]


def _elem_util(res: Result) -> np.ndarray:
    req = res.meta.get("required_sf", 2.0)
    return np.array([req / c["sf"] if c["sf"] > 0 else np.inf for c in res.elem_check])


def _setup3d(ax, coords):
    c = coords
    span = (c.max(0) - c.min(0)).max() / 2 * 1.1
    mid = (c.max(0) + c.min(0)) / 2
    ax.set_xlim(mid[0] - span, mid[0] + span)
    ax.set_ylim(mid[1] - span, mid[1] + span)
    ax.set_zlim(mid[2] - span, mid[2] + span)
    ax.view_init(elev=15, azim=-60)
    ax.set_xlabel("x lateral (mm)", fontsize=7, color=INK)
    ax.set_ylabel("y aft (mm)", fontsize=7, color=INK)
    ax.set_zlabel("z up (mm)", fontsize=7, color=INK)
    ax.tick_params(labelsize=6, colors=MUTED)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor("white")
        pane.set_edgecolor("#e6e6e6")


def plot_deformed(results: dict, png: Path, title: str):
    n = len(results)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    fig = plt.figure(figsize=(3.6 * cols, 3.8 * rows), dpi=130)
    for k, (name, r) in enumerate(results.items()):
        ax = fig.add_subplot(rows, cols, k + 1, projection="3d")
        ue = _elastic_u(r)
        dmax = np.linalg.norm(ue, axis=1).max()
        H = np.ptp(r.coords[:, 2]) or 1.0
        sc = 0.08 * H / dmax if dmax > 0 else 1.0
        d = r.coords + sc * ue
        for el in r.elements:
            p = r.coords[[el.n1, el.n2]]
            q = d[[el.n1, el.n2]]
            ax.plot(*p.T, color=MUTED, lw=1.0, ls=(0, (2, 2)))
            ax.plot(*q.T, color=DEFORMED, lw=2.0)
        _setup3d(ax, r.coords)
        ax.set_title(f"{name}\nmax elastic {dmax:.1f} mm (x{sc:.0f})", fontsize=8, color=INK)
    fig.suptitle(f"{title}: deformed shape (blue, rigid-body motion on body springs removed) "
                 f"vs undeformed (grey dashed)", fontsize=9, color=INK)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.03, top=0.88, wspace=0.05, hspace=0.25)
    fig.savefig(png)
    plt.close(fig)


def plot_utilization(results: dict, png: Path, title: str):
    n = len(results)
    cols = min(4, n)
    rows = int(np.ceil(n / cols))
    utils = {k: _elem_util(r) for k, r in results.items()}
    vmax = max(1.5, max(float(np.nanmax(u[np.isfinite(u)])) for u in utils.values()))
    norm = mcolors.Normalize(0, vmax)
    fig = plt.figure(figsize=(3.6 * cols, 3.8 * rows + 0.6), dpi=130)
    for k, (name, r) in enumerate(results.items()):
        ax = fig.add_subplot(rows, cols, k + 1, projection="3d")
        u = utils[name]
        for e, el in enumerate(r.elements):
            p = r.coords[[el.n1, el.n2]]
            ax.plot(*p.T, color=CMAP(norm(min(u[e], vmax))), lw=3.0 if u[e] > 1 else 2.0,
                    solid_capstyle="round")
        e_max = int(np.argmax(u))
        pm = r.coords[[r.elements[e_max].n1, r.elements[e_max].n2]].mean(0)
        ax.scatter(*pm, s=40, facecolors="none", edgecolors=INK, linewidths=1.0)
        _setup3d(ax, r.coords)
        status = "FAIL" if u.max() > 1 else "ok"
        ax.set_title(f"{name}\nmax u = {u.max():.2f} ({status}; SF {r.min_sf:.2f} vs req "
                     f"{r.meta.get('required_sf', 2.0):g})", fontsize=8, color=INK)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
    cax = fig.add_axes([0.25, 0.07, 0.5, 0.015])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_label("utilisation u = required SF / member SF  (u > 1 fails; thick lines; circle = max)",
                 fontsize=8, color=INK)
    cb.ax.tick_params(labelsize=7)
    fig.suptitle(f"{title}: member utilisation", fontsize=9, color=INK)
    fig.subplots_adjust(left=0.02, right=0.98, bottom=0.13, top=0.9, wspace=0.05, hspace=0.25)
    fig.savefig(png)
    plt.close(fig)


# ----------------------------------------------------------------------------- markdown
def _mass_table(res: Result) -> list[str]:
    groups = {}
    for m in res.members:
        g = groups.setdefault(m["group"], {"mass": 0.0, "L": 0.0, "section": m["section"],
                                           "material": m["material"]})
        g["mass"] += m["mass_kg"]
        g["L"] += m["L"]
    out = ["| member group | section | material | length mm | mass g (oz) |", "|---|---|---|---|---|"]
    for k, g in groups.items():
        out.append(f"| {k} | {g['section']} | {g['material']} | {g['L']:.0f} | "
                   f"{g['mass'] * 1e3:.1f} ({g['mass'] * 1e3 * OZ_PER_G:.2f}) |")
    tot = res.mass_kg * 1e3
    out.append(f"| **total tubes** | | | | **{tot:.1f} ({tot * OZ_PER_G:.2f})** |")
    return out


def _study_md(study: dict, outdir: Path, stem: str) -> list[str]:
    res = study["results"]
    label = study["label"]
    fm = study["frame"]
    p = fm.get("params", {})
    L = [f"## {label}", ""]
    if p:
        L += [f"Frame: height {p.get('height', 0):.0f} mm ({p.get('height', 0) / 25.4:.1f} in), stays "
              f"{p.get('stay_style')}, torso setting {p.get('torso_in')} in -> yoke at z = "
              f"{p.get('shoulder_z', 0):.0f} mm, haul mode = {p.get('haul_mode')}.", ""]
    for w in fm.get("warnings", []):
        L.append(f"> WARNING: {w}")
    if fm.get("warnings"):
        L.append("")
    L += ["| load case | load | min SF | req. | critical member | buckling factor | bond SF (avg / Volkersen peak) | hip share | pass |",
          "|---|---|---|---|---|---|---|---|---|"]
    for row in summarize(study):
        c = res[row["case"]].meta["case"]
        L.append(f"| {row['case']} | {c.load_kg:g} kg ({c.load_kg * LB_PER_KG:.0f} lb) x {c.g_factor:g} g | "
                 f"{_fmt(row['min_sf'])} | {row['required_sf']:g} | {row['critical']} ({row['critical_group']}) | "
                 f"{_fmt(row['buckling'], 1)} | {_fmt(row['joint_sf'])} / {_fmt(row['joint_peak_sf'])} "
                 f"{row['joint']} | {_fmt(row['hip_fraction'])} | {'yes' if row['pass'] else '**NO**'} |")
    L.append("")
    any_r = next(iter(res.values()))
    L += ["Mass of load-path tubes (fittings, bonded nodes, shelf and hardware not included):", ""]
    L += _mass_table(any_r) + [""]
    fat = study.get("fatigue")
    if fat:
        c = fat["cfg"]
        L += [f"Fatigue screen ({c['g']:g} g carry, pulsating R = 0, required {c['cycles_required']:.0e} cycles):", ""]
        mets = [r for r in fat["members"] if r["kind"] == "metal"]
        cfs = [r for r in fat["members"] if r["kind"] == "cfrp"]
        if mets:
            w = min(mets, key=lambda r: r["life"])
            L.append(f"- metal (Kt = {c['Kt_metal']:g}, Goodman + Basquin): min life {w['life']:.2e} cycles "
                     f"at {w['member']} (Smax {w['smax']:.0f} MPa) -> {'ok' if w['ok'] else '**FAIL**'}")
        if cfs:
            w = max(cfs, key=lambda r: r["fi"])
            L.append(f"- CFRP: max FI at {c['g']:g} g = {w['fi']:.3f} (limit {c['cfrp_fi_limit']:g}) at "
                     f"{w['member']} -> {'ok' if w['ok'] else '**FAIL**'}")
        if fat["joints"]:
            w = min(fat["joints"], key=lambda r: r["sf"])
            L.append(f"- bonds: max tau_avg {w['tau']:.2f} MPa vs {w['limit']:.2f} MPa "
                     f"({c['adhesive_frac']:.0%} of lap shear) at {w['joint']} -> {'ok' if w['ok'] else '**FAIL**'}")
        L.append("")
    dpng = outdir / f"{stem}_deformed.png"
    upng = outdir / f"{stem}_utilization.png"
    plot_deformed(res, dpng, label)
    plot_utilization(res, upng, label)
    L += [f"![deformed]({dpng.name})", "", f"![utilisation]({upng.name})", ""]
    return L


def _result_md(r: Result, outdir: Path, stem: str) -> list[str]:
    L = [f"## {r.name or 'result'}", "",
         f"- min SF (governing, `max_sf`): {_fmt(r.min_sf)} at {r.critical_member['id']}",
         f"- buckling factor: {_fmt(r.buckling_sf, 1)}",
         f"- max displacement: {r.max_displacement():.2f} mm", ""]
    L += ["| member | group | SF | max |N| N | max |M| N*mm | max |T| N*mm |", "|---|---|---|---|---|---|"]
    for m in sorted(r.members, key=lambda m: m["sf"])[:20]:
        f = m["max_abs_forces"]
        L.append(f"| {m['id']} | {m['group']} | {_fmt(m['sf'])} | {f[0]:.0f} | {max(f[4], f[5]):.0f} | {f[3]:.0f} |")
    L += ["", "Reactions (N, N*mm):", "", "| node | Fx | Fy | Fz | Mx | My | Mz |", "|---|---|---|---|---|---|---|"]
    for k, v in r.reactions.items():
        L.append(f"| {k} | " + " | ".join(f"{x:.1f}" for x in v) + " |")
    L += [""] + _mass_table(r) + [""]
    dpng, upng = outdir / f"{stem}_deformed.png", outdir / f"{stem}_utilization.png"
    plot_deformed({r.name or "case": r}, dpng, r.name or "result")
    plot_utilization({r.name or "case": r}, upng, r.name or "result")
    L += [f"![deformed]({dpng.name})", "", f"![utilisation]({upng.name})", ""]
    return L


ASSUMPTIONS_MD = """## Method and assumptions

- Solver: `huntkit.fea.frame` 3D Euler-Bernoulli frame, 6 DOF/node, members subdivided (2 elements
  per member segment); linear static; linear buckling from the consistent geometric stiffness.
  Verified against closed-form solutions in `tests/test_fea.py`.
- Metal SF = design yield / von Mises at the extreme fibre (peak axial+bending combined with peak
  torsion+transverse shear; conservative). Design yield = MMPDS S-basis when the material record
  has it (7075-T6: 462 MPa), else typical.
- CFRP SF = 1 / Tsai-Wu inverse strength ratio of the worst ply (24 points around the tube wall,
  membrane running loads at the mean radius, Ny = 0), strengths knocked down x0.8 hot/wet and a
  further x0.65 on compression (impact). Wall effective stiffness from CLT (membrane A-matrix).
- ASSUMPTION: body interface springs (global axes) - hipbelt kx 20 / ky 30 / kz 40 N/mm total,
  shoulder yoke 4 / 8 / 10 N/mm, load lifters at the stay tops 0 / 6 / 3 N/mm; the shoulder+lifter
  vertical stiffness is rescaled per case so the hipbelt carries 80 % of the vertical load.
- ASSUMPTION: bag load = equal nodal forces at the bag attachment points plus rigid-link moments for
  the CG offset aft; meat shelf = rigid shelf on the pivots with its tip strapped to mid-frame anchors;
  tall load = weight on the shelf pivots, overturning moment reacted by horizontal lashing at the
  upper lash points. Frame self-weight ignored (<0.5 % of load).
- ASSUMPTION: single-stay set-down = impact force (load x 2.5 g vertical + 0.2 friction) at one
  stay foot balanced by the load's d'Alembert inertia (inertia relief, free-free solve).
- Bonded joints: average bond shear vs lap-shear strength x0.8 hot/wet (SF governs), Volkersen
  elastic peak reported for information; bending treated as axial line load around the bond,
  transverse shear assumed to bear on the socket lip, peel not modelled.
- Fatigue: pulsating 0 -> 1.2 g static-carry stress; metal Goodman + Basquin with Kt = 2;
  CFRP FI limit 0.5; bonds 30 % of lap shear. Screening level only.
- Not covered: local tube crushing at clamps/fittings, fitting/node stress, bearing at shelf pivots,
  large-displacement effects, HDPE framesheet / hipbelt plate (use `huntkit.fea.plate`).
"""


def report(obj, path, title: str | None = None) -> Path:
    md, outdir = _paths(path)
    stem = md.stem
    L = [f"# {title or 'FEA report'}", ""]
    if isinstance(obj, Result):
        L += _result_md(obj, outdir, stem)
    elif isinstance(obj, dict) and "results" in obj:
        L += _study_md(obj, outdir, stem)
    elif isinstance(obj, (list, tuple)):
        L += ["## Summary: min SF per load case", ""]
        names = list(obj[0]["results"].keys())
        L.append("| load case (req. SF) | " + " | ".join(s["label"] for s in obj) + " |")
        L.append("|---|" + "---|" * len(obj))
        for n in names:
            req = obj[0]["results"][n].meta["required_sf"]
            cells = []
            for s in obj:
                r = s["results"].get(n)
                cells.append("-" if r is None else (f"{r.min_sf:.2f}" + ("" if r.min_sf >= req else " (FAIL)")))
            L.append(f"| {n} ({req:g}) | " + " | ".join(cells) + " |")
        L.append("| tube mass g | " + " | ".join(f"{next(iter(s['results'].values())).mass_kg * 1e3:.0f}"
                                                for s in obj) + " |")
        L.append("")
        for i, s in enumerate(obj):
            L += _study_md(s, outdir, f"{stem}_{i:02d}")
    else:
        raise TypeError("report() expects a Result, a study dict or a list of study dicts")
    L.append(ASSUMPTIONS_MD)
    md.write_text("\n".join(L))
    return md
