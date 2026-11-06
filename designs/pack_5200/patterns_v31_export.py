"""Exports for the Pack 5200 v3.1 pattern set (see patterns_v31.py).

Writes outputs/patterns_pack5200/ (scratch, regenerated) and the beginner print set in
outputs/release/pack5200_v3.1_patterns/ (git-tracked deliverable), plus phone-readable PNG
previews in outputs/screens/20261105_packpatterns_<n>.png.
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import cut_list, export_dxf, export_pdf_tiled, export_svg, nest  # noqa: E402
from huntkit.patterns.export_dxf import arrow, layout_rows  # noqa: E402
from huntkit.patterns.export_pdf import MM, PAPERS, draw_test_squares  # noqa: E402

import patterns_v31 as PV  # noqa: E402

ROOT = PV.ROOT
OUT = ROOT / "outputs" / "patterns_pack5200"
REL = ROOT / "outputs" / "release" / "pack5200_v3.1_patterns"
SCREENS = ROOT / "outputs" / "screens"
DOCS_SCREENS = ROOT / "docs" / "screens"
DATE = "20261105"
YD = 914.4
WASTE_PROD = 0.03       # ASSUMPTION: 3 % spreading / end / defect loss on production lays
N_LOTS = (1, 10, 50, 100)
NEST_UNITS = 10         # production marker: 10 packs nested together
NEST_TIME_S = 240.0     # per-marker time cap; after it the nester places the rest greedily


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def roll(mid: str) -> tuple[float, float]:
    m = MAT.load(mid)
    return float(m.require("roll_width_mm")), float(m.require("usable_width_mm"))


def by_material(pieces):
    out: dict[str, list] = {}
    for p in pieces:
        out.setdefault(p.material_id, []).append(p)
    return dict(sorted(out.items()))


# ============================================================================ previews
def _draw(ax, p, dx=0.0, dy=0.0, labels=True, fs=5.0, lw=0.6):
    T = lambda pts: np.asarray([(x + dx, y + dy) for x, y in pts])  # noqa: E731
    c = T(p.cut_line() + [p.cut_line()[0]])
    ax.fill(c[:, 0], c[:, 1], color="#f3efe4", zorder=1)
    ax.plot(c[:, 0], c[:, 1], color="black", lw=lw, zorder=3)
    s = T(p.outline + [p.outline[0]])
    ax.plot(s[:, 0], s[:, 1], color="#666", lw=lw * 0.6, ls=(0, (4, 2)), zorder=3)
    for ln in p.internal_lines:
        q = T(ln.points + ([ln.points[0]] if ln.closed else []))
        col = {"cut_inside": "black", "stitch": "#2a7", "fold": "#36c", "dart": "#36c"}.get(ln.kind, "#36c")
        ax.plot(q[:, 0], q[:, 1], color=col, lw=lw * (1.0 if ln.kind == "cut_inside" else 0.6),
                ls="-" if ln.kind in ("cut_inside", "placement") else (0, (3, 2)), zorder=4)
    for _, pts in p.notch_marks():
        q = T(pts)
        ax.plot(q[:, 0], q[:, 1], color="red", lw=lw * 1.4, zorder=5)
    for d in p.drill_holes:
        (x, y), = T([d.xy])
        ax.add_patch(plt.Circle((x, y), max(d.diameter / 2, 1.5), fill=False, color="#a0a", lw=lw * 0.8, zorder=5))
    for seg in arrow(*p.grain_arrow(), head=10.0):
        q = T(seg)
        ax.plot(q[:, 0], q[:, 1], color="#1565c0", lw=lw * 1.1, zorder=4)
    if labels:
        cx, cy = p.seam_polygon().representative_point().coords[0]
        txt = f"{p.piece_id}" + (f" [{p.size}]" if p.size else "") + f"\n{p.name}\nCUT {p.quantity}" + \
              (" (L+R)" if p.mirror else "")
        ax.text(cx + dx, cy + dy, txt, fontsize=fs, ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))


def _save(fig, path: Path, dpi=110):
    """Save a phone-readable PNG, stepping the dpi down until it is <= 1.5 MB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
        if path.stat().st_size <= 1.5e6 or dpi <= 50:
            break
        dpi = int(dpi * 0.8)
    plt.close(fig)
    return path


def render_pieces(pieces, title, path, max_row=1800.0):
    rows = layout_rows(pieces, max_row_mm=max_row, gap=40.0)
    xs = [dx + p.bounds()[2] for p, dx, dy in rows]
    ys = [dy + p.bounds()[3] for p, dx, dy in rows]
    W, H = max(xs), max(ys)
    w_in = 13.0
    h_in = max(4.0, min(w_in * H / max(W, 1), 22.0))
    fig, ax = plt.subplots(figsize=(w_in, h_in + 0.8))
    fs = max(4.0, min(7.5, 7.5 * 1800 / max(W, 600)))
    for p, dx, dy in rows:
        _draw(ax, p, dx, dy, fs=fs)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("mm  (black = cut line, dashed = seam line, red = notches, purple = drill holes, "
                  "blue arrow = grain, green = stitch/placement)", fontsize=8)
    ax.tick_params(labelsize=7)
    return _save(fig, path)


def render_marker(mk, title, path):
    L, W = max(mk.length_mm, 1.0), mk.fabric_width_mm
    w_in = 13.0
    h_in = max(3.0, min(w_in * W / L, 14.0))
    fig, ax = plt.subplots(figsize=(w_in, h_in + 1.0))
    ax.add_patch(plt.Rectangle((0, 0), L, W, fc="#eef3f6", ec="black", lw=0.8))
    for y in (mk.selvedge_mm, W - mk.selvedge_mm):
        ax.plot([0, L], [y, y], color="#888", ls="--", lw=0.6)
    cmap = plt.get_cmap("tab20")
    ids = sorted({pl.source.piece_id for pl in mk.placements})
    for pl in mk.placements:
        c = np.asarray(pl.piece.cut_line() + [pl.piece.cut_line()[0]])
        k = ids.index(pl.source.piece_id)
        ax.fill(c[:, 0], c[:, 1], color=cmap(k % 20), alpha=0.65, lw=0)
        ax.plot(c[:, 0], c[:, 1], color="black", lw=0.4)
        g0, g1 = pl.piece.grain_arrow()
        ax.plot([g0[0], g1[0]], [g0[1], g1[1]], color="#1565c0", lw=0.5)
        if mk.units <= 1 or pl.unit == 0:
            cx, cy = pl.piece.seam_polygon().representative_point().coords[0]
            ax.text(cx, cy, pl.source.piece_id + (f"\n{pl.source.size}" if pl.source.size else ""), fontsize=5.5,
                    ha="center", va="center")
    ax.set_xlim(-20, L + 20)
    ax.set_ylim(-20, W + 20)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlabel("marker length mm (warp / selvedge runs left-right; grain arrows parallel to it)", fontsize=8)
    ax.tick_params(labelsize=7)
    return _save(fig, path)


def render_closeup(p, box, title, path, fs=7.0):
    fig, ax = plt.subplots(figsize=(9, 9 * (box[3] - box[1]) / (box[2] - box[0])))
    _draw(ax, p, labels=False, lw=1.3)
    for n in p.notches:
        if box[0] <= n.x <= box[2] and box[1] <= n.y <= box[3] and n.label:
            ax.annotate(n.label, (n.x, n.y), fontsize=fs - 1.5, color="red", xytext=(6, 4), textcoords="offset points")
    for d in p.drill_holes:
        if box[0] <= d.x <= box[2] and box[1] <= d.y <= box[3]:
            ax.annotate(d.label, (d.x, d.y), fontsize=fs - 1.5, color="#a0a", xytext=(6, -8), textcoords="offset points")
    lab = "\n".join(p.label_lines()[:6])
    ax.text(box[0] + 5, box[3] - 5, lab, fontsize=fs, va="top", family="monospace",
            bbox=dict(fc="white", ec="#999", alpha=0.9))
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10, loc="left")
    ax.tick_params(labelsize=7)
    return _save(fig, path, dpi=120)


# ============================================================================ reports
def strain_table(ps) -> str:
    rows = ["| Piece | Method | p99 strain % | max % (no slivers) | mean % | Folded tris | Status |",
            "|---|---|---:|---:|---:|---:|---|"]
    for pid, v in ps.strain.items():
        ok = v["p99_pct"] <= 2.0
        rows.append(f"| {pid} | {v.get('method', 'develop_region (mesh LSQ)')} | {v['p99_pct']:.2f} | {v['max_pct']:.2f} | "
                    f"{v['mean_pct']:.2f} | {v.get('folded', 0)} | {'OK' if ok else '**>2 %**'} |")
    return "\n".join(rows)


def write_checks(ps, vol, rep, graded, path: Path):
    L = ["# Pack 5200 v3.1 pattern checks", "",
         "Generated by `designs/pack_5200/patterns_v31.py`. Units mm. Tolerance 1.0 mm on every seam.", "",
         "## Flattening strain", "",
         "Body panels are meshed in the (q, z) parameter plane and flattened by least squares on every edge "
         "(`huntkit.patterns.develop_region`). Strain is the principal stretch of each triangle, area-weighted "
         "99th percentile; slivers (< 12 deg corner) at acute pattern corners are left out of max. Limit 2 %.", "",
         "**Split decision.** Drafted on the smooth v3.1 surface, the frame panel needed 10.5 % and the outer face "
         "8.5 % (p99): the 30 mm head setback is a smooth step over z 560-640 (bend radius ~36 mm) and the "
         "depth has a slope kink at T_PEAK (z 632). Two ring seams fix it: the SETBACK seam at z 560 and the "
         "SHOULDER seam at z 631.2 (= the zip's upper end, 0.8 mm under the kink). Between them the band is "
         "ruled ring to ring. The upper face gets two 110 mm darts from the collar seam. The side gores stay "
         "one piece (they crease at the two seam heights).", "", strain_table(ps), "",
         "## Volume (flattened seam lines re-assembled)", "",
         f"- Design (geometry.yaml, exact ring integral): **{vol['design_L']:.2f} L**",
         f"- Body to the collar seam, master surface: {vol['master_surface_body_L']:.2f} L; rebuilt from the "
         f"flat pattern (ring perimeters from the flat pieces, heights from the flat B-01|B-03 seam): "
         f"**{vol['pattern_body_L']:.2f} L**",
         f"- Collar seam to the fill line (straight collar tube, design dome): {vol['collar_to_fill_L']:.2f} L. "
         f"Collar width {vol['collar_perimeter_mm']:.1f} mm vs largest ring above it "
         f"{vol['max_ring_perimeter_above_collar_mm']:.1f} mm: {'fits' if vol['collar_fits'] else 'DOES NOT FIT'}",
         f"- Eight fairlead swells bulge inward: -{vol['swells_L']:.3f} L",
         f"- **Pattern total {vol['pattern_total_L']:.2f} L ({vol['pattern_total_cu_in']:.0f} cu in)**, "
         f"{vol['delta_vs_design_L']:+.2f} L vs design (R-01 window 85.2 +/- 1 L)",
         f"- Largest ring-perimeter difference flat vs 3D: {vol['perimeter_err_max_mm']:.2f} mm; body height "
         f"flat {vol['height_flat_mm']:.1f} vs 3D {vol['height_3d_mm']:.1f} mm", "",
         "## Fairlead swells (B-01)", "",
         "| Station | Side | Crest z | Lower mm | Upper mm | Length | Height | Width |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for w in ps.swell_windows:
        L.append(f"| {w['station']} | {w['side']} | {w['z']:.0f} | {w['lower']:.0f} | {w['upper']:.0f} | {w['length']:.0f} | "
                 f"{w['height']:.0f} | {w['width']:.0f} |")
    L += ["", "Each swell = a rhombus window in B-01 + two developable cone halves (B-13/B-14/B-15) "
          "joined on the crest. The crest is left open 45 mm on IM1-IM3: that is the meat-strap port (B-12 frame on "
          "the inside). Hinge and IM3 are asymmetric so the tips clear the bottom seam (5 mm) and the setback "
          "seam (8 mm).", "",
          "## Seam check", "", f"{len(rep.results)} seams, **{len(rep.mismatches)} mismatches**.", "", rep.markdown(), ""]
    for s, g in graded.items():
        L += [f"### Graded {s}: {len(g.results)} seams, {len(g.mismatches)} mismatches", "", g.markdown(), ""]
    L += ["## Note for the pack-designer: geometry.yaml vs the patterns", "",
          "**`designs/pack_5200/geometry.yaml` still describes the smooth 30 mm head-setback step (z 560-640, "
          "kink at T_PEAK z 632). The production patterns do not follow it: they take the setback with two ring "
          "seams, SETBACK at z 560 and SHOULDER at z 631.2 (= zip upper end), ruled between, so the frame panel "
          "(B-01 / B-01b / B-01u) and the outer face (B-02a-d) are 3 tiers each.** Volume rebuilt from the flats is "
          "85.02 L vs 85.16 L design (see above). Action for the pack-designer: adopt the two seams in geometry.yaml / panels.yaml "
          "(seam z levels, tier piece ids) and in DESIGN.md, then rerun `python designs/pack_5200/patterns_v31.py "
          "--check`. Until then geometry.yaml and the cut pieces disagree above z 560 by design. Also: BUILD_PLAN.md "
          "step 9 still puts the B-12 ports at x +/-100, z 190/330/520; the patterns put them in the swell crests "
          "over the fairlead eyes (x +/-115), and step 6 still lists the retired frame stubs.", ""]
    L += ["## Open items for other owners", ""] + [f"- {n}" for n in ps.notes]
    path.write_text("\n".join(L) + "\n")
    return path


def cut_instructions(mid):
    face, way = PV.MATERIAL_FACE.get(mid, ("-", "-"))
    plies = "1 ply (prototype); production: up to 24 plies on an automatic cutter, 12 for laminates" \
        if mid not in PV.FREE_ROTATION else "die/laser/router from the DXF, no spreading"
    return face, way, plies


def write_cutlist(ps, markers, markers10, path_csv: Path, path_md: Path):
    base = ps.all_pieces(kit={"base"}, sizes={"M", "J"})
    acc = ps.all_pieces(kit={"accessory"})
    allp = ps.all_pieces()
    cl = cut_list(allp)
    cl.write(path_csv)
    rows = []
    for mid in sorted({p.material_id for p in base}):
        mk, mk10 = markers.get(mid), markers10.get(mid)
        rw, uw = roll(mid)
        per_unit_10 = (mk10.length_mm / mk10.units) if mk10 else mk.length_mm
        y = {1: mk.length_mm * 1.0}
        for n in N_LOTS[1:]:
            y[n] = per_unit_10 * n * (1 + WASTE_PROD)
        rows.append((mid, rw, uw, mk, mk10, y))
    md = ["# Pack 5200 v3.1 cut list and yardage", "",
          "Base pack = bag + fly + pockets + size M hipbelt + J straps + back panel (lid and rifle boot are "
          "accessories, listed below). Yardage = nested marker length at the material's real roll width "
          "(`data/materials` `roll_width_mm`, `usable_width_mm`). 1 pack = single-pack marker; 10/50/100 packs = "
          f"the {NEST_UNITS}-pack production marker per pack x N + {WASTE_PROD * 100:.0f} % lay loss (ASSUMPTION).", "",
          "## Yardage per material", "",
          "| Material | Roll in (usable) | Pieces/pack | 1-pack marker eff. | Yd / 1 pack | m / 1 pack | 10-pack eff. | Yd / 10 | Yd / 50 | Yd / 100 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tot = {n: 0.0 for n in N_LOTS}
    for mid, rw, uw, mk, mk10, y in rows:
        npcs = sum(p.quantity for p in base if p.material_id == mid)
        md.append(f"| {mid} | {rw / 25.4:.0f} ({uw / 25.4:.1f}) | {npcs} | {mk.efficiency * 100:.0f} % | {y[1] / YD:.2f} | "
                  f"{y[1] / 1000:.2f} | {(mk10.efficiency * 100 if mk10 else mk.efficiency * 100):.0f} % | {y[10] / YD:.1f} | "
                  f"{y[50] / YD:.1f} | {y[100] / YD:.1f} |")
        for n in N_LOTS:
            tot[n] += y[n] / YD
    md.append(f"| **all materials** | | | | **{tot[1]:.2f}** | | | **{tot[10]:.1f}** | **{tot[50]:.1f}** | **{tot[100]:.1f}** |")
    md += ["", "Foams, HDPE and Hypalon are sheet goods: their 'yard' is a 1000 / 1220 / 1370 mm wide sheet length; "
           "send the DXF to the converter.", "", "## Cutting instructions per material", "",
           "| Material | Face | Lay | Plies | Allowance |", "|---|---|---|---|---|"]
    for mid in sorted({p.material_id for p in allp}):
        face, way, plies = cut_instructions(mid)
        sas = sorted({(f"{p.seam_allowance_mm:g}" if not isinstance(p.seam_allowance_mm, dict) else
                       "/".join(f"{v:g}" for v in sorted(set(p.seam_allowance_mm.values())))) for p in allp
                      if p.material_id == mid})
        md.append(f"| {mid} | {face} | {way} | {plies} | {', '.join(sas)} mm |")
    md += ["", "Knife: " + PV.KNIFE + ". Notches 6 mm (never past the seam line). Drill holes 3 mm inside the feature.",
           "", "## Pieces", "", cl.markdown(), "", "## Webbing, binding and hardware (cut lengths)", "",
           "| Use | Material | Length mm | Qty | Total m | Source |", "|---|---|---:|---:|---:|---|"]
    for w in ps.webbing:
        md.append(f"| {w['use']} | {w['material_id']} | {w['length_mm']} | {w['qty']} | "
                  f"{w['length_mm'] * w['qty'] / 1000:.2f} | {w.get('source', '')} |")
    for h in ps.hardware:
        md.append(f"| {h['item']} | {h['material_id']} | {h['length_mm'] or ''} | {h['qty']} | | |")
    md += ["", "## Accessories (not in the base yardage)", ""]
    for p in acc:
        md.append(f"- {p.piece_id} {p.name}: {p.material_id}, cut {p.quantity}, {p.area_mm2 * p.quantity / 1e6:.3f} m2")
    path_md.write_text("\n".join(md) + "\n")
    return tot


def test_square_pdf(path: Path):
    pw, ph = PAPERS["letter"]
    c = canvas.Canvas(str(path), pagesize=(pw * MM, ph * MM), pageCompression=1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * MM, (ph - 25) * MM, "PRINT TEST - Pack 5200 v3.1 patterns")
    c.setFont("Helvetica", 10)
    for i, t in enumerate(["Print at 100 % / Actual size (NOT 'fit to page').",
                           "Measure the solid square: it must be 100 mm on both sides (+/- 1 mm).",
                           "Measure the dashed square: it must be 4 in on both sides.",
                           "If not, fix the printer setting before printing any pattern page."]):
        c.drawString(20 * MM, (ph - 40 - 7 * i) * MM, t)
    draw_test_squares(c, 50 * MM, 60 * MM)
    c.showPage()
    c.save()
    return path


# ============================================================================ main
def export_all(ps, *, release=True, screens=True, nest10=True, log=print):
    t0 = time.time()
    for d in (OUT, OUT / "dxf", OUT / "pdf_letter", OUT / "pdf_a0", OUT / "pdf_plotter36", OUT / "svg_laser", OUT / "markers"):
        d.mkdir(parents=True, exist_ok=True)
    allp = ps.all_pieces()
    base = ps.all_pieces(kit={"base"}, sizes={"M", "J"})
    groups = by_material(allp)
    files = []
    for mid, pcs in groups.items():
        files.append(export_dxf(pcs, OUT / "dxf" / f"{mid}.dxf"))
        export_pdf_tiled(pcs, OUT / "pdf_letter" / f"{mid}_letter.pdf", "letter", compress=True,
                         title=f"Pack5200 v3.1 {mid}")
        export_pdf_tiled(pcs, OUT / "pdf_a0" / f"{mid}_A0.pdf", "a0", compress=True, title=f"Pack5200 v3.1 {mid}")
        export_pdf_tiled(pcs, OUT / "pdf_plotter36" / f"{mid}_36in.pdf", "plotter36", compress=True,
                         title=f"Pack5200 v3.1 {mid}")
        export_svg(pcs, OUT / "svg_laser" / f"{mid}.svg")
    export_dxf(allp, OUT / "dxf" / "pack5200_v31_all.dxf")
    log(f"exports {time.time() - t0:.0f} s")
    # markers at real roll width
    markers, markers10 = {}, {}
    for mid, pcs in by_material(base).items():
        rw, uw = roll(mid)
        kw = dict(grain_constraint=mid not in PV.FREE_ROTATION, selvedge_mm=(rw - uw) / 2, spacing_mm=3.0,
                  allow_180=mid not in PV.ONE_WAY, free_rotation_step_deg=90.0)
        mk = nest(pcs, rw, **kw)
        mk.material_id = mid
        assert not mk.unplaced, (mid, mk.unplaced)
        markers[mid] = mk
        mk.export_pdf(OUT / "markers" / f"{mid}_marker_1pack.pdf", compress=True)
        mk.export_dxf(OUT / "markers" / f"{mid}_marker_1pack.dxf")
        mk.export_csv(OUT / "markers" / f"{mid}_marker_1pack.csv")
        if nest10:
            t1 = time.time()
            units = NEST_UNITS
            npc = sum(p.quantity for p in pcs) * units

            def prog(i, n, m, _mid=mid, _t=t1):
                if i % 25 == 0 or i == n:
                    log(f"    {_mid} 10-pack {i}/{n} placed, L {m.length_mm:.0f} mm, {time.time() - _t:.0f} s")
            m10 = nest(pcs, rw, units=units, time_limit_s=NEST_TIME_S, progress=prog if npc > 60 else None, **kw)
            m10.material_id = mid
            assert not m10.unplaced, (mid, m10.unplaced)
            markers10[mid] = m10
            m10.export_pdf(OUT / "markers" / f"{mid}_marker_{units}pack.pdf", scale=0.1, compress=True)
            m10.export_dxf(OUT / "markers" / f"{mid}_marker_{units}pack.dxf")
            log(f"  {mid}: 1-pack {mk.length_mm / YD:.2f} yd eff {mk.efficiency:.2f}; {units}-pack eff "
                f"{m10.efficiency:.2f} ({time.time() - t1:.0f} s)")
    json.dump({k: v.report() for k, v in markers.items()}, open(OUT / "markers" / "markers_1pack.json", "w"), indent=1)
    json.dump({k: v.report() for k, v in markers10.items()}, open(OUT / "markers" / "markers_production.json", "w"), indent=1)
    tot = write_cutlist(ps, markers, markers10, OUT / "cutlist.csv", OUT / "cutlist.md")
    rep, graded = PV.seam_report(ps)
    vol = PV.volume_check(ps)
    write_checks(ps, vol, rep, graded, OUT / "pattern_checks.md")
    (OUT / "seam_check.md").write_text("# Seam check\n\n" + rep.markdown() + "\n\n" +
                                       "\n\n".join(f"## {s}\n\n{g.markdown()}" for s, g in graded.items()) + "\n")
    summary = {**PV.summary(ps), "volume": vol, "yardage_yd": {str(k): round(v, 2) for k, v in tot.items()},
               "strain": ps.strain, "swells": ps.swell_windows}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
    shots = []
    if screens:
        shots = make_screens(ps, markers, markers10, log)
    if release:
        make_release(ps, markers, tot, vol, rep, log)
    log(f"done {time.time() - t0:.0f} s")
    return {"summary": summary, "screens": shots}


def make_screens(ps, markers, markers10, log):
    shots = []
    n = [0]

    def nxt(topic):
        n[0] += 1
        return SCREENS / f"{DATE}_packpatterns_{n[0]}.png"
    allp = ps.all_pieces()
    order = ["challenge_ultra_200", "cordura_330d_nylon66", "cordura_500d_nylon66", "robic_100d_ripstop"]
    groups = by_material(allp)
    mids = order + [m for m in groups if m not in order]
    for mid in mids:
        pcs = groups[mid]
        shots.append(render_pieces(pcs, f"Pack 5200 v3.1 pieces: {mid} ({len(pcs)} piece types incl. sizes)", nxt("pieces")))
    for mid in mids:
        if mid in markers:
            mk = markers[mid]
            shots.append(render_marker(mk, f"Marker 1 pack: {mid}, roll {mk.fabric_width_mm / 25.4:.0f} in, "
                                           f"{mk.length_mm / YD:.2f} yd, efficiency {mk.efficiency * 100:.0f} %", nxt("marker")))
    for mid in ("cordura_330d_nylon66", "challenge_ultra_200"):
        if mid in markers10:
            mk = markers10[mid]
            shots.append(render_marker(mk, f"Production marker {mk.units} packs: {mid}, {mk.length_mm / YD:.1f} yd, "
                                           f"efficiency {mk.efficiency * 100:.0f} %", nxt("marker10")))
    b01 = ps.pieces["B-01"]
    w = [s for s in ps.swell_windows if s["station"] == "im2" and s["side"] == "R"][0]
    cx, cy = w["centre_flat"]
    shots.append(render_closeup(b01, (cx - 110, cy - 130, cx + 110, cy + 90),
                                "Close-up B-01: IM2 R fairlead swell window (cut-out + set-in seam), corner drills, "
                                "bag-hook box-X, notches", nxt("closeup")))
    cap = ps.pieces["B-13"]
    x0, y0, x1, y1 = cap.bounds()
    shots.append(render_closeup(cap, (x0 - 10, y0 - 10, x1 + 10, y1 + 10),
                                "Close-up B-13 swell cap half (developed cone, 0 % strain): port-end notches on the crest",
                                nxt("closeup")))
    d = ps.pieces["B-02d"]
    x0, y0, x1, y1 = d.bounds()
    shots.append(render_closeup(d, (x0 - 5, y0 - 5, x1 + 5, y1 + 5), "Close-up B-02d upper face: darts, notches every 50 mm, label",
                                nxt("closeup"), fs=6))
    b05 = ps.pieces["B-05"]
    x0, y0, x1, y1 = b05.bounds()
    shots.append(render_closeup(b05, (x0 - 5, y0 - 5, x1 + 5, y1 + 5), "Close-up B-05 bottom: seam V-notches, 50 mm notches, "
                                "hinge-eye box-X, drain grommets", nxt("closeup"), fs=6))
    for s in shots:
        assert s.stat().st_size <= 1.5e6, s
    best = [shots[0], shots[1], shots[len(mids) + 1], shots[-4]]
    DOCS_SCREENS.mkdir(parents=True, exist_ok=True)
    for s in best:
        shutil.copy(s, DOCS_SCREENS / s.name)
    log(f"screens: {len(shots)}")
    (OUT / "screens.json").write_text(json.dumps({"screens": [rel(s) for s in shots], "docs": [rel(DOCS_SCREENS / s.name) for s in best]}, indent=1))
    return shots


STEPS = [
    ("step3_hipbelt_pocket", "Step 3: hipbelt pocket (make 3, keep 2)", lambda ps: [ps.graded["HP-01"]["M"], ps.graded["HP-02"]["M"]]),
    ("step4_shard_practice", "Step 4: camo shard + lash tab practice", lambda ps: [ps.pieces["SH-01"], ps.pieces["SH-04"], ps.pieces["B-11"]]),
    ("step5_collar_fly", "Step 5: roll-top collar + rain fly", lambda ps: [ps.pieces[k] for k in ("B-06", "B-07", "B-07s", "SH-03", "F-01a", "F-01c", "F-01b", "F-02", "B-16")]),
    ("step6_meat_ports_swells", "Step 6: meat ports + fairlead swell (practise one swell on scrap)", lambda ps: [ps.pieces[k] for k in ("B-12", "B-13", "B-14a", "B-14b", "B-15a", "B-15b")]),
    ("step7_back_panel_harness", "Step 7: back panel + shoulder straps (J and S)", lambda ps: [ps.pieces[k] for k in ("BP-01", "BP-02", "BP-03", "BP-04", "BP-05", "BP-07", "HS-05")] + [g for k in ("HS-1", "HS-2", "HS-3", "HS-4") for g in ps.graded[k].values()]),
    ("step8_hipbelt_S", "Step 8: hipbelt size S", lambda ps: _belt(ps, "S")),
    ("step8_hipbelt_M", "Step 8: hipbelt size M", lambda ps: _belt(ps, "M")),
    ("step8_hipbelt_L", "Step 8: hipbelt size L", lambda ps: _belt(ps, "L")),
    ("step8_hipbelt_XL", "Step 8: hipbelt size XL", lambda ps: _belt(ps, "XL")),
    ("step9_main_bag", "Step 9: main bag", lambda ps: [ps.pieces[k] for k in ("B-01", "B-01b", "B-01u", "B-02a", "B-02b", "B-02c", "B-02d", "B-03", "B-05", "B-08", "B-09", "D-01", "SH-02")]),
]


def _belt(ps, s):
    return [ps.graded[k][s] for k in ("H-01", "H-02", "H-03", "H-04", "H-05")] + \
        [ps.pieces[k] for k in ("H-06", "H-07", "H-08", "H-09", "H-10", "SH-05", "R-03")]


def make_release(ps, markers, tot, vol, rep, log):
    if REL.exists():
        shutil.rmtree(REL)
    (REL / "print_letter").mkdir(parents=True)
    (REL / "dxf").mkdir()
    test_square_pdf(REL / "print_letter" / "00_PRINT_FIRST_test_square.pdf")
    pages = {}
    for fn, title, fnp in STEPS:
        info = export_pdf_tiled(fnp(ps), REL / "print_letter" / f"{fn}.pdf", "letter", compress=True, title=title)
        pages[fn] = info["pages"]
    for mid, pcs in by_material(ps.all_pieces()).items():
        export_dxf(pcs, REL / "dxf" / f"{mid}.dxf")
    shutil.copy(OUT / "cutlist.md", REL / "cutlist.md")
    shutil.copy(OUT / "cutlist.csv", REL / "cutlist.csv")
    shutil.copy(OUT / "pattern_checks.md", REL / "pattern_checks.md")
    readme = README.format(
        pages="\n".join(f"| `print_letter/{fn}.pdf` | {title} | {pages[fn]} |" for fn, title, _ in STEPS),
        yd1=tot[1], yd10=tot[10], yd50=tot[50], yd100=tot[100], vol=vol["pattern_total_L"], cuin=vol["pattern_total_cu_in"],
        nseams=len(rep.results), nmis=len(rep.mismatches), ntypes=len(ps.pieces),
        ncut=sum(p.quantity for p in ps.all_pieces(kit={"base"}, sizes={"M", "J"})))
    (REL / "README.md").write_text(readme)
    size = sum(f.stat().st_size for f in REL.rglob("*") if f.is_file())
    log(f"release {size / 1e6:.1f} MB")
    assert size < 40e6, size


README = """# Pack 5200 v3.1 patterns: beginner print set

True-scale patterns for the Spine bag and every soft part (hipbelt S-XL, shoulder straps J and S, back
panel, fly, pockets). Generated by `designs/pack_5200/patterns_v31.py`; do not edit by hand.
{ntypes} piece types, {ncut} pieces cut per pack (size M belt, J straps, no accessories).
Seam check: {nseams} seams, {nmis} mismatches over 1 mm. Volume rebuilt from the flat pattern: {vol:.2f} L ({cuin:.0f} cu in).

## 1. Print and check (do this first)

1. Print `print_letter/00_PRINT_FIRST_test_square.pdf` on US Letter at **100 % / Actual size**.
   Turn off "fit to page", "shrink oversized pages" and any scaling.
2. Measure the solid square with a ruler: **100 mm** both ways (+/- 1 mm). The dashed square is **4 in**.
   Every pattern page also has a test square; check one on every print run.
3. If it is off, fix the printer setting. Do not cut fabric from a wrong-scale print.

## 2. Tape the pages together

- Page 1 of each PDF is the **page map** (which page goes where: A1, A2, ... rows are letters, columns numbers).
- Each page overlaps its right and upper neighbour by 12 mm. Trim the neighbour page along its printed
  border, lay it on the dashed overlap line, and match the **diamonds** (each diamond names the page it meets).
- Tape on the back. Check the test square again on the taped sheet.
- Larger prints: `outputs/patterns_pack5200/pdf_a0/` (A0 sheet) or `pdf_plotter36/` (36 in roll plotter) at a
  copy shop, same 100 % rule.

## 3. Read a piece

- **Solid black** = cut line (seam allowance included). **Dashed grey** = seam (stitch) line.
- **Red ticks** = notches: cut 6 mm into the allowance, never past the seam line. Match notch to notch.
- **Circles** = drill / awl marks (bartacks, zip ends, swell corners, pocket corners, grommets). Mark through
  with an awl or chalk pen 3 mm inside the feature.
- **Blue double arrow** = grain line: keep it parallel to the selvedge.
- **Green** = stitch / placement lines for parts sewn on flat (pockets, sleeve, band, channels).
- Solid black **inside** a piece = cut-out window or slot (cut these first).
- The label gives ID, name, size, material, how many to cut (L+R = one normal, one flipped), face up.

## 4. What to print for each step (BUILD_PLAN.md skill ladder)

| File | Step | Pages |
|---|---|---:|
{pages}

Practice order (cheapest fabric first, every practice piece is usable gear):
1. Step 1-2 drills and the stuff sack (`python -m huntkit.patterns.cli demo`).
2. **Step 3 hipbelt pocket**: zip, gusset, small curves. Make 3, keep the best 2.
3. **Step 4 shard + lash tab**: edge-turn appliqué on scrap 500D.
4. **Step 5 collar + fly**: long straight seams, hems, the light silpoly.
5. **Step 6 ports + one swell**: set a B-13 cap pair into a scrap window before cutting B-01.
   The swell is new in v3.1 and is the trickiest small seam on the bag (sew the crest first, then the
   window, cap on top, needle down at the 4 corners).
6. **Step 7 back panel + straps**, then **step 8 hipbelt** in your size.
7. **Step 9 main bag** last. Join B-01 + B-01b + B-01u and B-02a/B-02c + zip + B-02b + B-02d flat before
   the 3D seams. Match notches every 50 mm. Press the setback-seam allowance UP.

## 5. Fabric to buy

Nested at the real roll widths (`cutlist.md` has every material):
**{yd1:.1f} yd per pack** (all materials, one-off marker); {yd10:.0f} yd for 10, {yd50:.0f} yd for 50, {yd100:.0f} yd for 100 packs.
Foams, HDPE and Hypalon go to a converter / laser shop as DXF (`dxf/`, one file per material, layers
CUT SEW NOTCH GRAIN DRILL TEXT INTERNAL).

## 6. Files

- `print_letter/` tiled US Letter PDFs per build step, `dxf/` one DXF per material (all sizes).
- `cutlist.md` / `cutlist.csv` pieces, yardage per 1/10/50/100 packs, cutting instructions, webbing lengths.
- `pattern_checks.md` flattening strain, volume, swells, every seam length.
"""
