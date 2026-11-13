"""BL-032 part A exports (+ BL-033 fixes): CORRIE F rev 3 cut set (see patterns_corrie_f_rev3.py).

    python designs/pack_5200/patterns_corrie_f_rev3_export.py [--no-nest10]

Writes the beginner print set and the production files to outputs/release/pack5200_corrie_f_rev3/patterns/
(git-tracked deliverable), scratch copies to outputs/patterns_corrie_f_rev3/, and phone-readable PNG previews to
outputs/screens/20261113_BL034_<n>.png (BL-034 re-export; BL-032 / BL-033 screenshots keep their names). Reuses the v3.1 exporter's drawing helpers (patterns_v31_export, read only).
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

import patterns_corrie_f_rev3 as PR  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.gendesign import attach_system as AS  # noqa: E402  (B-24 box sizes, BL-035)
from huntkit.patterns import cut_list, export_dxf, export_pdf_tiled, nest  # noqa: E402
from huntkit.patterns.export_pdf import MM, PAPERS, draw_test_squares  # noqa: E402
import patterns_v31_export as PVX  # noqa: E402  (drawing helpers only)

ROOT = PR.ROOT
REL = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "patterns"
OUT = ROOT / "outputs" / "patterns_corrie_f_rev3"
SCREENS = ROOT / "outputs" / "screens"
DATE = "20261113"
SHOT_TAG = "BL041pat"                 # BL-041 re-export: screenshot prefix 20261113_BL041pat_ (earlier tickets kept their own)
YD = 914.4
WASTE_PROD = PVX.WASTE_PROD        # 3 % lay loss ASSUMPTION (v3.1 rule)
NEST_UNITS = 10
NEST_TIME_S = 90.0                 # per production marker; the rest is placed greedily (nest contract)
TITLE = "CORRIE F rev 3"

STEPS = [   # (file, title, piece ids) in the build order of the release README
    ("step1_pockets", "Step 1: pockets (FP hip-reach, IMP-4, IMP-8, IMP-2 sleeve, F-02 + B-16 floor channels)",
     ["FP-a", "FP-b", "IMP4-a", "IMP4-b", "IMP8-a", "IMP8-b", "B-09c", "B-09p", "F-02", "B-16"]),
    ("step2_small_parts", "Step 2: swells, port patches, guy-port facings, Hypalon tabs",
     ["B-13x", "B-12", "B-27f", "B-11", "B-17", "B-18", "B-22"]),
    ("step3_door_blade", "Step 3: door D2, camo blade U, hinge band, accents",
     ["B-02u", "B-02door", "B-02h", "SH-07", "SH-01b"]),
    ("step4_main_bag", "Step 4: frame panel B-01, gussets B-03, floor B-05", ["B-01", "B-03", "B-05"]),
    ("step5_collar", "Step 5: roll-top collar, hem, HDPE strips", ["B-06f", "B-06", "B-07", "B-07s"]),
    ("step6_crown_lid", "Step 6: B-29 crown lid", ["B-29a", "B-29b", "B-29c", "B-29d", "B-29e", "B-29f", "B-29g"]),
    ("step7_addons", "Step 7: add-ons (scope pod, meat liner)", ["A1-a", "A1-b", "A1-d", "MS-a", "MS-b", "MS-c", "MS-s"]),
    ("step8_rain_fly", "Step 8: F-01 rain fly (spine + 2 sides, silpoly)", ["F-01a", "F-01b"]),
]


# ---- BL-041 n-6 / n-7: printed notes and the 1:1 webbing-marks pages ------------------------------------------------
NOTE_MAX = 40                       # a label note longer than this goes to the NOTES page (the DXF keeps it in full)
WEB_MARKS = [("HE", None), ("RTM", None), ("LLT", None), ("IMC", None), ("T3", None), ("US", 110.0), ("RT", 110.0),
             ("B-25", 222.0)]
# BL-043 m-12: W3G deleted (W3-OVER); RT (sewn end) and B-25 (R half to the neck; the L half mirrors it) added; every
# line gets a leader label beside the strip (not only a legend under it)
WEB_GROUPS = (("HE", "RTM"), ("IMC", "LLT"), ("T3", "US"), ("B-25", "RT"))   # tall strip left, short one right: the
#                                     test square sits bottom right, under the short strip
WEB_LABEL_W = 46.0                  # mm of label column right of each strip
WEB_WRAP = 30


def print_copy(p):
    """Copy of a piece for the tiled print: a long label note is replaced by a pointer to the NOTES page, so it can
    neither run over the next piece nor be clipped at a tile edge (re-review n-6)."""
    q = p.copy()
    n = q.labels.get("note", "")
    if len(n) > NOTE_MAX:
        q.labels["note"] = f"see NOTES page ({p.piece_id})"
    return q


def _wrap(t, n):
    import textwrap
    return textwrap.wrap(t, n) or [""]


def _crop(p, L):
    """Webbing piece cropped to its first L mm (marks inside it only), for pieces longer than a page."""
    from huntkit.patterns import rect_panel
    w = p.bounds(cut=False)[2]
    q = rect_panel(p.name, w, L, 0.0, seam_allowance_mm=0.0, material_id=p.material_id, quantity=p.quantity,
                   piece_id=p.piece_id)
    from shapely.geometry import LineString, box
    for ln in p.internal_lines:
        if all(pt[1] <= L for pt in ln.points):
            q.add_internal_line(ln.points, ln.kind, ln.label, ln.closed)
        elif not ln.closed and min(pt[1] for pt in ln.points) < L and len(ln.points) > 1:
            g = LineString(ln.points).intersection(box(-1.0, -1.0, w + 1.0, L))   # BL-043: a line that runs past the crop
            if g.geom_type == "LineString" and g.length > 1.0:                    # is cut at it, not dropped
                q.add_internal_line(list(g.coords), ln.kind, ln.label, False)
    return q


def notes_and_marks_pdf(rs, ids, path: Path, title: str) -> int:
    """Extra pages for a step PDF: (1) NOTES, every long piece note in full, wrapped; (2) 1:1 webbing marks (folds, boxes,
    neck / tack / seam lines) for the op 4.05 / 4.08 / step 7 webbing, with a test square. Returns pages written."""
    from huntkit.patterns.export_pdf import draw_piece_pdf
    pw, ph = PAPERS["letter"]
    c = canvas.Canvas(str(path), pagesize=(pw * MM, ph * MM))
    c.setTitle(f"{title} - notes + webbing marks")
    y = ph - 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * MM, y * MM, f"{TITLE}: piece NOTES (full text; the DXFs carry the same)")
    y -= 10
    for i in ids:
        n = rs.pieces[i].labels.get("note", "")
        if len(n) <= NOTE_MAX:
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(12 * MM, y * MM, f"{i}  {rs.pieces[i].name}")
        y -= 5
        c.setFont("Helvetica", 9)
        for t in _wrap(n, 105):
            c.drawString(16 * MM, y * MM, t)
            y -= 4.5
        y -= 3
    c.showPage()
    pages = 1
    pcs = [(_crop(rs.pieces[i], L) if L else rs.pieces[i], i, L) for i, L in WEB_MARKS if i in rs.pieces]
    byid = {t[1]: t for t in pcs}
    groups = [[byid[i] for i in ids_ if i in byid] for ids_ in WEB_GROUPS]
    groups = [g_ for g_ in groups if g_]
    for gi, grp in enumerate(groups):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(12 * MM, (ph - 12) * MM, f"{TITLE}: webbing marks 1:1 (page {gi + 1} of {len(groups)})")
        c.setFont("Helvetica", 8)
        c.drawString(12 * MM, (ph - 17) * MM, "Check the test square, lay the hot-knifed strip on its outline, chalk "
                     "the folds (blue dash-dot), boxes and lines (grey dashed). Each line is named by its leader.")
        x = 14.0
        for q, i, L in grp:
            w, h = q.bounds(cut=False)[2], q.bounds(cut=False)[3]
            y0 = ph - 30 - h

            def to_pt(px, py, x=x, y0=y0):
                return ((x + px) * MM, (y0 + py) * MM)
            draw_piece_pdf(c, q, to_pt, scale=1.0, labels=False)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x * MM, (y0 - 5) * MM, f"{i}  {w:.0f} x {rs.pieces[i].bounds(cut=False)[3]:.0f} mm")
            c.setFont("Helvetica", 6.5)
            c.drawString(x * MM, (y0 - 9) * MM, f"cut {rs.pieces[i].quantity}" + (
                f"; first {L:.0f} mm shown" + ("; the L half mirrors it" if i == "B-25" else "") if L else ""))
            # leader labels: one per named line, at its height, pushed apart so none overlap
            tags = []
            for ln in q.internal_lines:
                lab = (ln.label or "").strip()
                if not lab or ln.kind not in ("fold", "stitch", "placement"):
                    continue
                ys = [pt[1] for pt in ln.points]
                xs = [pt[0] for pt in ln.points]
                tags.append([0.5 * (min(ys) + max(ys)), max(xs), 0.5 * (min(ys) + max(ys)), lab])
            tags.sort(key=lambda r: -r[0])
            gap = 3.2
            for k in range(1, len(tags)):
                tags[k][2] = min(tags[k][2], tags[k - 1][2] - gap * len(_wrap(tags[k - 1][3], WEB_WRAP)[:2]))
            c.setFont("Helvetica", 5.5)
            for ly, lx, ty, lab in tags:
                c.setLineWidth(0.25)
                c.line((x + lx) * MM, (y0 + ly) * MM, (x + w + 3) * MM, (y0 + ty) * MM)
                for k, tline in enumerate(_wrap(lab, WEB_WRAP)[:2]):
                    c.drawString((x + w + 4) * MM, (y0 + ty - 1 - k * 2.6) * MM, tline)
            x = max(x + w + WEB_LABEL_W + 6.0, 104.0)
        draw_test_squares(c, (pw - 112) * MM, 14 * MM)
        c.showPage()
        pages += 1
    c.save()
    return pages


def notes_only_pdf(rs, ids, path: Path, title: str) -> int:
    pw, ph = PAPERS["letter"]
    c = canvas.Canvas(str(path), pagesize=(pw * MM, ph * MM))
    y = ph - 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(12 * MM, y * MM, f"{TITLE} {title[:60]}: piece NOTES (full text)")
    y -= 10
    for i in ids:
        n = rs.pieces[i].labels.get("note", "")
        if len(n) <= NOTE_MAX:
            continue
        c.setFont("Helvetica-Bold", 9)
        c.drawString(12 * MM, y * MM, f"{i}  {rs.pieces[i].name}")
        y -= 5
        c.setFont("Helvetica", 9)
        for t in _wrap(n, 105):
            c.drawString(16 * MM, y * MM, t)
            y -= 4.5
        y -= 3
        if y < 20:
            c.showPage()
            y = ph - 15
    c.showPage()
    c.save()
    return 1


def roll(mid: str) -> tuple[float, float]:
    if mid in PR.ROLL_FALLBACK:
        return PR.ROLL_FALLBACK[mid]
    m = MAT.load(mid)
    return float(m.require("roll_width_mm")), float(m.require("usable_width_mm"))


def by_material(pieces):
    out: dict = {}
    for p in pieces:
        out.setdefault(p.material_id, []).append(p)
    return dict(sorted(out.items()))


def _fname(mid: str) -> str:
    return mid.split(" ")[0]


def test_square_pdf(path: Path):
    pw, ph = PAPERS["letter"]
    c = canvas.Canvas(str(path), pagesize=(pw * MM, ph * MM), pageCompression=1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * MM, (ph - 25) * MM, f"PRINT TEST - {TITLE} patterns")
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


def make_markers(rs, units=1, time_limit=None, log=print):
    out = {}
    for mid, pcs in by_material(rs.all_pieces(sizes={PR.KIT}, webbing=False)).items():
        rw, uw = roll(mid)
        kw = dict(grain_constraint=mid not in PR.FREE_ROTATION, selvedge_mm=(rw - uw) / 2, spacing_mm=3.0,
                  allow_180=mid not in PR.ONE_WAY, free_rotation_step_deg=90.0)
        t0 = time.time()
        mk = nest(pcs, rw, units=units, time_limit_s=time_limit, **kw)
        mk.material_id = mid
        assert not mk.unplaced, (mid, mk.unplaced)
        out[mid] = mk
        log(f"  marker {rs.fabrics} x{units} {mid}: {mk.length_mm / YD:.2f} yd, eff {mk.efficiency:.2f} ({time.time() - t0:.0f} s)")
    return out


def _sa_text(p):
    sa = p.seam_allowance_mm
    return f"{sa:g}" if not isinstance(sa, dict) else "/".join(f"{v:g}" for v in sorted(set(sa.values())))


def write_cutlist(rsP, rsA, mkP, mkA, mk10, path_md: Path, path_csv: Path):
    allP = rsP.all_pieces(webbing=False)
    cl = cut_list(allP)
    cl.write(path_csv)
    pa = {p.piece_id: p for p in rsA.all_pieces(sizes={PR.KIT}, webbing=False)}
    md = [f"# {TITLE} cut list (BL-032)", "",
          "Primary BOM = today's fabrics (DECISIONS 2026-11-12). Alternate = the team B set (ULTRAGrid body, 70D "
          "collar, ULTRA 200X floor), released only behind its gates (abrasion swatch, PT-3 + 50 mm strip test, 70D "
          "stock weight). Same pattern pieces; only the fabric changes.", "",
          "## Pieces (crown kit M shown; B-28 and W3 are cut per crown kit, see webbing)", "",
          "| ID | Piece | Kit | Primary fabric | Alternate fabric | Cut | L+R | SA mm | Face | Lay | Build step |",
          "|---|---|---|---|---|---:|---|---|---|---|---|"]
    for p in rsP.all_pieces(sizes={PR.KIT}, webbing=False):
        m = rsP.meta[p.piece_id]
        alt = pa[p.piece_id].material_id
        face, way = PR.MATERIAL_FACE.get(p.material_id, ("-", "-"))
        md.append(f"| {p.piece_id} | {p.name} | {m['kit']} | {p.material_id} | "
                  f"{alt if alt != p.material_id else 'same'} | {p.quantity} | {'yes' if p.mirror else ''} | "
                  f"{_sa_text(p)} | {face} | {way} | {m['step']} |")
    md += ["", "## Yardage per material (full build: base + lid + meat-trip kit + add-ons, crown kit M)", "",
           "Nested at the record's roll width. 1 bag = single-bag marker; 10 / 50 / 100 = the 10-bag production "
           f"marker per bag x N + {WASTE_PROD * 100:.0f} % lay loss (ASSUMPTION).", "",
           "| Set | Material | Roll in (usable) | Pieces | 1-bag eff. | Yd / 1 bag | m / 1 bag | 10-bag eff. | Yd / 10 | Yd / 50 | Yd / 100 |",
           "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tot = {}
    for setname, mks, rs, m10 in (("primary", mkP, rsP, mk10), ("alternate", mkA, rsA, {})):
        t = {1: 0.0, 10: 0.0, 50: 0.0, 100: 0.0}
        for mid, mk in mks.items():
            rw, uw = roll(mid)
            npc = sum(p.quantity for p in rs.all_pieces(sizes={PR.KIT}, webbing=False) if p.material_id == mid)
            m = m10.get(mid)
            per = (m.length_mm / m.units) if m else mk.length_mm
            y = {1: mk.length_mm, **{n: per * n * (1 + WASTE_PROD) for n in (10, 50, 100)}}
            for n in t:
                t[n] += y[n] / YD
            md.append(f"| {setname} | {mid} | {rw / 25.4:.0f} ({uw / 25.4:.1f}) | {npc} | {mk.efficiency * 100:.0f} % | "
                      f"{y[1] / YD:.2f} | {y[1] / 1000:.2f} | {(m.efficiency * 100 if m else mk.efficiency * 100):.0f} % | "
                      f"{y[10] / YD:.1f} | {y[50] / YD:.1f} | {y[100] / YD:.1f} |")
        md.append(f"| **{setname} total** | | | | | **{t[1]:.2f}** | | | **{t[10]:.1f}** | **{t[50]:.1f}** | **{t[100]:.1f}** |")
        tot[setname] = t
    md += ["", "10-bag markers are for the primary set only; the alternate column uses its 1-bag marker x N.",
           "Hypalon, TPU 840D and HDPE are sheet goods cut from the DXF (laser / router); their 'yard' is a sheet "
           "length.", "", "## Cutting instructions", "",
           "| Material | Face | Lay / nap | Plies | Allowances in the file |", "|---|---|---|---|---|"]
    for mid in sorted({p.material_id for p in allP} | {p.material_id for p in rsA.all_pieces(webbing=False)}):
        face, way = PR.MATERIAL_FACE.get(mid, ("-", "-"))
        plies = "die / laser / router from the DXF, no spreading" if mid in PR.FREE_ROTATION else \
            "1 ply (prototype); production up to 24 plies on a cutter, 12 for laminates and mesh"
        sas = sorted({_sa_text(p) for p in allP + rsA.all_pieces(webbing=False) if p.material_id == mid})
        md.append(f"| {mid} | {face} | {way} | {plies} | {', '.join(sas)} mm |")
    md += ["", f"Knife: {PR.KNIFE}. Notches 6 mm deep, never past the seam line. Drill holes: awl or chalk "
           "3 mm inside the feature.", "", "## Webbing, cord and elastic (hot-knife / cold-cut lengths)", "",
           "| ID | Use | Material | Length mm (in) | Qty | Kit | Source |", "|---|---|---|---:|---:|---|---|"]
    for w in rsP.webbing:
        md.append(f"| {w['id']} | {w['use']} | {w['material_id']} | {w['length_mm']:.0f} ({w['length_mm'] / 25.4:.1f}) | "
                  f"{w['qty']} | {w['kit']} | {w['source']} |")
    md += ["", "## Hardware", "", "Purchase quantities with waste and prices: `../manufacturing/bom.csv`.", "", "| Item | Record | Length mm | Qty |", "|---|---|---:|---:|"]
    for h in rsP.hardware:
        md.append(f"| {h['item']} | {h['material_id']} | {h['length_mm'] or ''} | {h['qty']} |")
    md += ["", "## Pieces with areas (primary set)", "", cl.markdown()]
    path_md.write_text("\n".join(md) + "\n")
    return tot


def bl034_section(rsP) -> list:
    """BL-034 part A marks, every number from the pattern module."""
    g = rsP.geo
    kw = g["kw_z"]
    md = ["## 8. BL-034 marks (pack-designer)", "",
          "### 8.1 B-11 lash tabs (releases op 4.07)", "",
          f"{g['b11']['per_gusset']} per gusset, drawn on B-03 (one pattern, cut as a pair) = 8 a bag (ASSUMPTION B11-PLACE):", "",
          "| Use | z mm | from the frame seam mm |", "|---|---:|---:|"]
    md += [f"| {u} | {z:.0f} | {x:.0f} |" for u, z, x in g["b11"]["tabs"]]
    md += ["", "Bow riser tabs stack on the riser line 40 mm forward of the aft seam (right gusset; the cam sits in IMP-8); "
           "the same marks on the left gusset are antler / cape lash points. The two muzzle-keeper tabs sit side by side "
           "so a keeper loop runs between them round the barrel (rifle in a butt boot on either belt wing). Each mark: the "
           "30 x 50 outline (slot end up), the sew-down box 24 x 19 and its corners.", "",
           "### 8.2 Box-X marks drawn on the webbing", "",
           "| Part | Box | Where |", "|---|---|---|",
           "| W3 (per kit) | 21 x 25 | G-hook end, as W1 / W2 |",
           f"| IM1-IM3 | 21 x 25 | end loop, fold {PR.IM_LOOP:.0f} mm, box at the tip end |",
           f"| US1/US2 | 21 x 25 | sewn eye, fold {PR.US_EYE:.0f} mm (ASSUMPTION US-EYE) |",
           f"| B-24 | {AS.LINK_HOOK_BOX[0]:.0f} x {AS.LINK_HOOK_BOX[1]:.0f} hook + 3 x {AS.LINK_LOOP_BOX[0]:.0f} x "
           f"{AS.LINK_LOOP_BOX[1]:.0f} loops | attach_system.link_piece (the loop stations at 120 / 170 / 220 mm); "
           "BL-035: the capacity row uses the same boxes |",
           f"| B-25 | {PR.B25_BOX[0]:.0f} x {PR.B25_BOX[1]:.0f} each tab | DECISION B25-BOX: leaves the 13 mm loop the POM toggle needs |",
           f"| B-02h B-28 front tab | {PR.B28_BOX[0]:.0f} x {PR.B28_BOX[1]:.0f}, OUTSIDE | DECISION B28-FACE |",
           f"| B-28t lock tabs (front + rear, 4) | {PR.B28_BOX[0]:.0f} x {PR.B28_BOX[1]:.0f} | fold round the lock bar |",
           f"| B-28s toggle loop (B-25 second fold, 2) | {PR.B25_BOX[0]:.0f} x {PR.B25_BOX[1]:.0f} at the tip | "
           "BL-035: split from B-28t; 13 mm loop passes the B-28 rear toggle (B25-BOX rule) |",
           f"| LLT + B-22 + B-02h | {PR.LLT_BOX[0]:.0f} x {PR.LLT_BOX[1]:.0f} | BL-035: the B-02h mark matches the LLT "
           "piece (was 25 x 25) |", "",
           "### 8.3 K-W keeper notches and F-02", "",
           "K-W keepers are caught in the aft corner seams where each wrap crosses it (ASSUMPTION KW-PATH, geometry.yaml "
           "anchors): " + "; ".join(f"{k} R z {v['R']:.0f} / L z {v['L']:.0f}" for k, v in kw.items()) +
           ". V-notches on B-03 (R only / L only) and on the blade U outer edges.", "",
           f"F-02 on B-05: outside, {g['f02_on_b05']['w']:.0f} x {g['f02_on_b05']['h']:.0f} mm, x {g['f02_on_b05']['x0']} / "
           f"y {g['f02_on_b05']['y0']} on the B-05 seam rectangle, zip edge aft.", ""]
    return md


def bl033_section(rsP) -> list:
    """BL-033 fixes, every number from its code."""
    import corrie_f as F
    from huntkit.gendesign import loadpath_check as LP
    hs = F.hinge_standoff()
    a5 = next(r for r in LP.compute(fea_live=False, log=lambda *a: None)["rows"] if r["id"] == "A5")
    b22 = json.loads(F.B22_CHECK.read_text()) if F.B22_CHECK.exists() else None
    fp = F.fp_spec()
    g = rsP.geo
    gp = F.guy_port()
    nb = F.b01_net_g()
    md = ["## 7. BL-033 fixes", "",
          "### 7.1 Hinge swell window vs B-18 (DECISION H-1)", "",
          f"The BL-032 hinge window (x +/-115, z {hs['dropped_window_z'][0]:.0f}-{hs['dropped_window_z'][1]:.0f}) lay over "
          f"the B-18 doubler (z {hs['b18_z'][0]:.0f}-{hs['b18_z'][1]:.0f}) for {hs['overlap_z_mm']:.0f} mm of its height: the "
          "window cut B-01 out from under the HE box-X. **The hinge window and its swell B-13xh are deleted.** B-01 now has "
          f"{nb['windows']} windows (IM1-IM3); B-18 overlaps none of them ({hs['b18_window_overlap_mm2']:.0f} mm2), the "
          f"nearest starts {hs['nearest_window_above_b18_mm']:.0f} mm above its top edge.", "",
          f"The hinge cleat now bears on B-18: it stands {hs['hinge']['top_mm']:.1f} mm from the stay centre against B-01's "
          f"{hs['panel_offset_mm']:.0f} mm, so it lifts B-01 {hs['hinge']['push_mm']:.1f} mm "
          f"({hs['hinge']['push_with_b18_mm']:.1f} mm with the {hs['b18_t_mm']:.1f} mm Hypalon) over z 51-69. The US2 cleat "
          f"has carried the same {hs['us2']['push_mm']:.1f} mm with no swell since v3.1.", "",
          f"Hinge load path (BL-010 A5, `loadpath_check`), factored {a5['factored_n']:.0f} N, verdict **{a5['verdict']}**, "
          f"governs {a5['governs']} (ratio {a5['min']:.2f}):", "", "| Check | Demand | Capacity | Ratio |", "|---|---:|---:|---:|"]
    for ck in a5["checks"]:
        md.append(f"| {ck['item']} | {ck['demand_n']:.0f} | {ck['capacity']:.0f} | {ck['ratio']:.2f} |")
    md += ["", "With the window gone the joint is built the way A5 checks it (box-X through eye plies + B-18 + B-01, "
           "B-18's lower edge in the B-01 | B-05 seam). With the window it was not: B-01 was cut away under 40 of B-18's "
           "45 mm.", ""]
    if b22:
        mv, d0 = b22["runs"]["moved"], b22["runs"]["drawn_149"]
        md += ["### 7.2 B-22 at x +/-130.3 (port guy path, 15 in, meat, fine mesh)", "",
               f"Run `{mv['run']}` (B-22 sim node x {mv['b22_node_x_mm']['R']} / {mv['b22_node_x_mm']['L']}, z "
               f"{mv['b22_node_z_mm']['R']}: the nearest fine-mesh node on the drawn tab's row, 5 mm inboard of 130.3, "
               f"ASSUMPTION B22-NODE) against `{d0['run']}` (x 149):", "",
               "| | B-22 x 130.3 | B-22 x 149 | Limit |", "|---|---:|---:|---|",
               f"| 15 in meat CG y mm | {mv['meat_cg_y_mm']} | {d0['meat_cg_y_mm']} | <= {b22['cg_target_mm']:.0f} |",
               f"| 15 in fill CG y mm | {mv['fill_cg_y_mm']} | {d0['fill_cg_y_mm']} | - |",
               f"| lifter gap min mm (crown strap + port guy outside) | {mv['lifter_gap_min_mm']} | {d0['lifter_gap_min_mm']} "
               f"| >= {b22['min_clear_mm']:.0f} |",
               f"| R-28 deg | {mv['r28_deg']} | {d0['r28_deg']} | >= {b22['r28_min_deg']:.0f} |",
               f"| port guy 1 g N (max) | {mv['port_guy_1g_n']} | {d0['port_guy_1g_n']} | - |", "",
               f"**{'PASS' if b22['pass'] else 'FAIL'}**: B-22 stays at x +/-{b22['placement']['x_mm']} (50 mm tab)"
               + ("." if b22["pass"] else f"; use the fallback {b22['fallback']['tab_w']:.0f} mm tab at x "
                                           f"+/-{b22['fallback']['x']:.0f}."), ""]
    md += ["### 7.3 FP hip-reach pockets", "",
           f"Face {fp['w']:.0f} mm (was {fp['team_a_w']:.0f}), mesh kept at {fp['w'] + fp['pleat']:.0f} mm: the two box "
           f"pleats take {fp['pleat']:.0f} mm (2 x {fp['pleat'] / 2:.1f}). Plain rectangle on the gusset, inner edge "
           f"{g['fp_min_margin_mm']} mm off the frame seam at its tightest (ASSUMPTION FP-CLEAR >= "
           f"{g['fp_clear_req_mm']:.0f}). Capacity {fp['cap_L']} L by the mesh-arc model (ratio {fp['cap_ratio']}, "
           "ASSUMPTION FP-ARC). Access check: `corrie_f_loadout.run('D2')`, see the BL-033 report.", "",
           "### 7.4 Ledger fixes (adopted bag rows)", "",
           "- 'attachment: B-01 swell patches' no longer in `adopted_bag_rows` (C2: the same swells as B-13x).",
           f"- B-01 booked net of its {nb['windows']} windows: {nb['net_g']:.2f} g ({nb['full_g']:.2f} g less "
           f"{nb['window_mm2']:.0f} mm2).",
           f"- B-27: slit {gp['slit_mm']} mm on the fabric (z {gp['z_mm'][0]:.0f}-{gp['z_mm'][1]:.0f} = "
           f"{gp['slit_dz_mm']:.0f} mm in height; the top setback Z-fold is in it); facing {gp['slit_mm'] + 2 * F.PORT_END:.1f}"
           f" mm; row {gp['mass_g']} g.",
           "- `corrie_f.build`: the door zip and the two band | blade seams are real pairs (blade U inner edge split at "
           "z 650); no self-paired seam is left in D2.",
           f"- US floor channels: B-16 x2, {g['us_channels']['width_mm']:.0f} x {F.F02_WH[0]:.0f} mm on F-02, centres "
           f"{g['us_channels']['stations_mm'][0]:.0f} / {g['us_channels']['stations_mm'][1]:.0f} mm from the floor's frame "
           "edge (the under-straps carry about 55 % of the floor vertical in bag-on; meat_haul_modes.md).",
           f"- Lid hours: {F.crown_lid()['hours']} h booked (drafted B-29), was {F.crown_lid()['hours_bl029']} h.",
           f"- H-1: hinge swells x2 removed ({next(r['g'] for r in F.parts() if r['name'].startswith('BL-033 H-1'))} g).", "",
           "### 7.5 F-01 rain fly", "",
           f"Spine F-01a + sides F-01b x2 in silpoly 40D, cut for the full rolled state (lid top z {g['fly']['lid_top_z']}): "
           f"{g['fly']['area_m2']} m2 cut, {g['fly']['mass_B_g']} g; seams {g['fly']['seam_mm']} mm a side, 0 mm error; "
           f"elastic channels {g['fly']['hem_mm']} mm, elastic {g['fly']['elastic_mm']} mm (75 %, ASSUMPTION). Ease, tuck "
           "and wrap: corrie_f FLY_* ASSUMPTIONS, settled by the first fly.", ""]
    return md


def seam_table_md(rep) -> str:
    """BL-040 m-13: the seam table with the pipe in seam names escaped (huntkit's markdown() left it raw, so every
    column after the name shifted)."""
    rows = ["| Seam | Stitch | A mm | B mm | Ease mm | Error mm | Status |", "|---|---|---:|---:|---:|---:|---|"]
    for r in rep.results:
        rows.append(f"| {r.seam.name.replace('|', chr(92) + '|')} | {r.seam.stitch} | {r.length_a:.1f} | {r.length_b:.1f} | "
                    f"{r.seam.ease_mm:.1f} | {r.error_mm:+.2f} | {'OK' if r.ok else '**MISMATCH**'} |")
    return "\n".join(rows)


def write_checks(rsP, rsB, rep, mc, rec, hours, path: Path):
    s = PR.summary(rsP)
    L = rsP.lid
    md = [f"# {TITLE} pattern checks (BL-032 part A, BL-033 fixes)", "",
          f"Generated by `designs/pack_5200/patterns_corrie_f_rev3.py`. {s['piece_types']} piece types "
          f"({s['fabric_types']} fabric / sheet + {s['webbing_types']} webbing / elastic) "
          f"({s['pieces_cut_all_fabric']} fabric / sheet pieces cut for the full build at crown kit M), "
          f"{s['webbing_lines']} webbing / cord lines.", "",
          f"## 1. Seam lengths: {len(rep.results)} seams, {len(rep.mismatches)} mismatches over 1 mm", "",
          seam_table_md(rep), "",
          "## 2. Ledger reconciliation (1:1 with `huntkit.mass.ledger.adopted_bag_rows('M')`)", "",
          f"Rows {len(rec['rows'])}; unmatched {len(rec['unmatched_rows'])}; matched twice "
          f"{len(rec['multi_matched_rows'])}; drafted ids without a row {len(rec['pieces_without_row'])}; row ids "
          f"not drafted {len(rec['row_ids_not_drafted'])}.", "",
          "| Ledger row | System | cfg | g | Status | Pieces / webbing | Note |", "|---|---|---|---:|---|---|---|"]
    for o in rec["rows"]:
        md.append(f"| {o['row'][:90]} | {o['system']} | {o['cfg']} | {o['ledger_g']:.1f} | {o['status']} | "
                  f"{', '.join(o['pieces'] + o['webbing'])} | {o['note']} |")
    md += ["", "## 3. Mass from the pattern areas (team B fabrics = the ledger's basis)", "",
           "Pattern mass = cut area less cut-outs (swell windows, slots) x record gsm. Ledger fabric part = the row, or "
           "for pockets / lid / add-ons the row's own fabric figure (its hardware is not pattern area).", "",
           "| Row | Pieces | Pattern g | Ledger fabric g | Delta g | Delta % |", "|---|---|---:|---:|---:|---:|"]
    for r in mc["rows"]:
        md.append(f"| {r['row']} | {', '.join(r['pieces'])} | {r['pattern_g']:.2f} | {r['ledger_fabric_g']:.2f} | "
                  f"{r['delta_g']:+.2f} | {r['delta_pct']:+.1f} |")
    md.append(f"| **total** | | **{mc['pattern_g']:.1f}** | **{mc['ledger_g']:.1f}** | **{mc['delta_g']:+.1f}** | "
              f"**{mc['delta_pct']:+.2f}** (limit +/-{mc['tol_pct']:.0f}: {'pass' if mc['ok'] else 'FAIL'}) |")
    md += ["", "Primary (today's fabrics) pattern mass of the same rows: "
           f"{sum(PR.pattern_mass_g(rsP.pieces[i]) for r in mc['rows'] for i in r['pieces']):.1f} g.", "",
           "## 4. B-29 lid build hours on the drafted pattern", "",
           f"**{hours['hours']} h** on the drafted lid against BL-030's seam-list estimate {hours['bl030_h']} h "
           f"({hours['delta_vs_bl030_h']:+.2f} h) and the {hours['bl029_booked_h']} h booked in `build_metrics` "
           f"({hours['delta_vs_booked_h']:+.2f} h). Cut pieces {hours['pieces_cut']} (BL-030 counted "
           f"{hours['bl030_pieces']}).", "", "| Operation | Qty | h / unit | h |", "|---|---:|---:|---:|"]
    for r in hours["rows"]:
        md.append(f"| {r['op']} | {r['qty']} | {r['rate_h']} | {r['hours']} |")
    md += ["", "## 5. B-29 crown draft", "",
           f"The drawn dome (`corrie_f.LID`, superellipse n 4, 30 mm wall + 55 mm dome) meets the wall vertically, "
           f"so it cannot be flattened as one piece (least squares: p95 strain about 40 %). The crown is drafted by "
           f"radial development (every meridian keeps its 3D length) with four corner darts that take the extra "
           f"perimeter: flat {L['flat_crown_perimeter_mm']} mm against the {L['perimeter_mm']} mm wall. Each dart "
           f"opens {L['darts'][0]['open_mm']} mm, legs {L['darts'][0]['leg_mm']} mm (ASSUMPTION LID-DART). Strap "
           f"channel line {L['channel_mm'][0]} mm on the flat against {L['channel_3d_mm']} mm over the 3D dome.", "",
           "## 6. Placement changes the pattern had to make", ""]
    md += [f"- {n}" for n in rsP.notes]
    md += [f"- FP hip-reach pocket (BL-033): face {PR.F.fp_spec()['w']:.0f} mm, a plain rectangle; inner edge "
           f"{rsP.geo['fp_min_margin_mm']} mm off the frame seam at its tightest (BL-032 clamped the 180 mm face).", ""]
    md += bl033_section(rsP)
    md += bl034_section(rsP)
    path.write_text("\n".join(md) + "\n")


def write_recon_csv(rec, path: Path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ledger_row", "system", "cfg", "ledger_g", "status", "pieces", "webbing", "note"])
        for o in rec["rows"]:
            w.writerow([o["row"], o["system"], o["cfg"], o["ledger_g"], o["status"], " ".join(o["pieces"]),
                        " ".join(o["webbing"]), o["note"]])


def make_screens(rsP, mkP, mk10, log=print):
    shots, n = [], [0]

    def nxt():
        n[0] += 1
        return SCREENS / f"{DATE}_{SHOT_TAG}_{n[0]}.png"
    shell = [rsP.pieces[k] for k in ("B-01", "B-03", "B-05", "B-02u", "B-02door", "B-02h", "B-06f", "B-06", "B-07")]
    shots.append(PVX.render_pieces(shell, f"{TITLE}: shell + door D2 + collar (primary fabrics, seam + cut lines, "
                                          "notches, windows, slits)", nxt()))
    small = [rsP.pieces[k] for k in ("B-13x", "B-12", "B-27f", "B-11", "B-17", "B-18", "B-22", "SH-07",
                                     "SH-01b", "FP-a", "FP-b", "IMP4-a", "IMP4-b", "IMP8-a", "IMP8-b", "B-09c",
                                     "B-09p", "F-02", "B-16")]
    shots.append(PVX.render_pieces(small, f"{TITLE}: pockets, swells, ports, Hypalon tabs", nxt(), max_row=1400.0))
    lid = [rsP.pieces[k] for k in ("B-29a", "B-29b", "B-29c", "B-29d", "B-29e", "B-29f", "B-29g")]
    shots.append(PVX.render_pieces(lid, f"{TITLE}: B-29 crown lid (crown with 4 corner darts, base, zipped wall, "
                                        "camo caps, channels)", nxt(), max_row=1100.0))
    fly = [rsP.pieces[k] for k in ("F-01a", "F-01b")]
    shots.append(PVX.render_pieces(fly, f"{TITLE}: F-01 rain fly (spine over the lid + 2 sides), silpoly 40D", nxt(),
                                   max_row=1400.0))
    b01 = rsP.pieces["B-01"]
    x0, y0, x1, y1 = b01.bounds()
    shots.append(PVX.render_closeup(b01, (x0 - 5, y0 + 0.55 * (y1 - y0), x1 + 5, y1 + 5),
                                    "Close-up B-01 top: B-27 guy port slits + facings, IM3 swell windows, creases",
                                    nxt(), fs=6))
    shots.append(PVX.render_closeup(b01, (x0 - 5, y0 - 5, x1 + 5, y0 + 0.32 * (y1 - y0)),
                                    "Close-up B-01 bottom (BL-033 H-1): B-18 doublers clear, no hinge window; IM1 windows",
                                    nxt(), fs=6))
    for mid in ("cordura_330d_nylon66", "challenge_ultra_200", "polyester_ht_630d_printable",
                "silicone_coated_poly_ripstop_40d"):
        mk = mkP.get(mid)
        if mk:
            shots.append(PVX.render_marker(mk, f"Marker 1 bag: {mid}, roll {mk.fabric_width_mm / 25.4:.0f} in, "
                                               f"{mk.length_mm / YD:.2f} yd, efficiency {mk.efficiency * 100:.0f} %", nxt()))
    m = mk10.get("cordura_330d_nylon66")
    if m:
        shots.append(PVX.render_marker(m, f"Production marker {m.units} bags: cordura_330d_nylon66, "
                                          f"{m.length_mm / YD:.1f} yd, efficiency {m.efficiency * 100:.0f} %", nxt()))
    # BL-034 marks
    g3 = rsP.pieces["B-03"]
    shots.append(PVX.render_pieces([g3], "BL-034: gusset B-03 - B-11 lash tabs (bow riser / lash, muzzle keepers), "
                                         "K-W keeper notches", nxt(), max_row=600.0))
    shots.append(PVX.render_pieces([rsP.pieces[k] for k in ("B-02h", "B-05")],
                                   "BL-034: hinge band B-28 front tabs OUTSIDE (21 x 20 box-X); F-02 on B-05", nxt(),
                                   max_row=900.0))
    # BL-035: the short tabs go last (their labels run into free space, clear of the B-24 hook box)
    web = [rsP.pieces[k] for k in ("B-25", "US", "IM1", "W3", "B-24", "W1", "B-28t", "B-28s")]
    shots.append(PVX.render_pieces(web, "BL-034/035: webbing box-X marks (B-25 toggle tabs, US eye, IM loop, W3, B-24, "
                                        "B-28t lock tabs, B-28s toggle loop)", nxt(), max_row=1400.0))
    for s in shots:
        assert s.stat().st_size <= 1.5e6, s
    log(f"screens {len(shots)}")
    return shots


README = """# {title} patterns: beginner print set and production files (BL-032 part A)

> The v3.1 set (`outputs/release/pack5200_v3.1_patterns/`) is **superseded and keeps its STOP notice**. Build the
> bag from THIS folder.

True-scale patterns for every sewn piece of the adopted bag (CORRIE F rev 3, door D2: shell, collar and roll top,
hip-reach pockets, B-27 guy ports, B-22 anchors, B-29 crown lid, the BL-031 straps and keepers, the meat-trip
extenders, pockets and add-ons). Generated by `designs/pack_5200/patterns_corrie_f_rev3.py` and
`patterns_corrie_f_rev3_export.py`; do not edit by hand.
**{ntypes} piece types ({nfab} fabric / sheet types + {nwebt} webbing / elastic types); {ncut} fabric / sheet pieces
cut for one full build** (crown kit M) plus {nweb} webbing, cord and elastic cut-list lines. Seam check: {nseams} seams, {nmis} mismatches over 1 mm.
Mass from the pattern areas (team B fabrics, the ledger's basis): {pm} g against {lm} g in the ledger rows
({dpct:+.2f} %, limit +/-3 %).

## 1. Which fabric

- **Primary (build this):** today's fabrics: 330D Cordura body, 100D Robic collar, 500D Cordura floor,
  ULTRA 200 frame panel and collar frame side, 630D printable camo. `dxf/primary/`, `markers/primary/`.
- **Alternate (only after its gates):** ULTRAGrid 210D body, 70D ripstop collar, ULTRA 200X floor. The
  pieces are the same; only the fabric changes. `dxf/alternate/`, `markers/alternate/`. Gates: owner sees an
  ULTRAGrid swatch; PT-3 plus a 50 mm strip test on 200X (>= 36.8 N/mm); weigh the 70D stock.

## 2. Print and check (do this first)

1. Print `print_letter/00_PRINT_FIRST_test_square.pdf` on US Letter at **100 % / Actual size**. Turn off
   "fit to page" and any scaling.
2. Measure the solid square: **100 mm** both ways (+/- 1 mm). The dashed square is **4 in**. Every pattern page
   has a test square too; check one on every print run.
3. If it is off, fix the printer. Do not cut fabric from a wrong-scale print.

## 3. Tape the pages

Page 1 of each PDF is the page map (A1, A2 ...: rows are letters, columns numbers). Each page overlaps its right
and upper neighbour by 12 mm: trim the neighbour along its border, lay it on the dashed overlap line and match the
diamonds. Tape on the back, then check the test square again.

## 4. Read a piece

- **Solid black** = cut line (allowance included). **Dashed grey** = seam (stitch) line.
- **Red ticks** = notches: cut 6 mm into the allowance, never past the seam line. Match notch to notch. A V-notch
  marks a panel corner or a feature (hard-point loop, keeper, zip corner tangent, hinge eye).
- **Circles** = drill / awl marks (window corners, slit ends, box-X corners, dart apex, zip stops).
- **Blue double arrow** = grain: parallel to the selvedge.
- **Green** = stitch / placement lines; **blue dashed** = fold or crease lines.
- **Solid black inside a piece** = cut it out (swell windows, port slots, hose slots, guy port slits). Cut these first.
- Label: ID, name, material, how many (L+R = one normal, one flipped), face up.
- Marks that say **L only** / **R only** go on that side's gusset only (the gusset is one pattern cut as a pair).
- BL-033: no hinge swell window in B-01 (B-18 doublers sit on whole fabric); B-16 under-strap channels on F-02.\n- BL-034: B-11 lash tabs (4 per gusset), K-W keeper notches, F-02 placement on B-05, every webbing box-X drawn.\n- BL-040 (pre-cut review fixes): ONE hinge eye (HE folded in half; B-18 90 x 62 reaching 12 mm into the floor seam;
  box-X 34 x 34 on HE, B-18 and B-01); B-17 box 34 x 34; RTM roll-clip buckle tabs on both gussets and RT strap
  placements on the hem B-07; collar-ring notches measured one way round (one set on the gusset); B-11 slot 27 x 5;
  B-09p hose slot drawn; the swell port slot is a mark (cut through the laser-cut B-12 slot after sewing).
- BL-041 (re-check fixes): the hinge eye points UP onto the z 60 pin (DECISION HE-PIN: HE 38 x 86, box-X 34 x 10 at
  +4..+14 mm, 2 mm under the fairlead cheeks; supersedes the 34 x 34 box above); B-18 rows sewn before the HE (op 4.05);
  roll-clip path moved forward of the muzzle keepers (RTM at flat x 91, 133.5 mm under the collar seam; muzzle tabs
  111 / 171 mm), W3G guide on the path; IMC cam anchor tabs; B-25 in 38 mm (sleeves x 26.5-64.5); GBL deleted; long
  piece notes on a NOTES page and a 1:1 webbing-marks page at the end of step 2.
- BL-043 (third-review fixes): W3 rides at the crown-bar height (z 601-804 over the kits), so the W3G guide is gone
  (DECISION W3-OVER: W3 is the outer layer, slacken it to open the top); the RTM buckle tab moves 10 mm under W3's
  lowest edge (z {rtm_z:.0f}, flat x {rtm_x:.0f}), the hose slots too (z {hose_z:.0f}, DECISION HOSE-LOW); the RT strap is
  sewn at the roll end again (DECISION RT-ORIGIN; 'roll end' and 'B-07s strip end' notches on B-07; RT cut {rt_cut:.0f});
  muzzle tabs {mk0:.0f} / {mk1:.0f} mm; B-25 drawn with its mitre turns and 25 mm neck (SK-12, cut {b25:.0f}); IMC 192 mm;
  webbing pages carry a leader label on every line, with B-25 and RT added.

## 5. Build order and what to print

| File | Step | Pages |
|---|---|---:|
{pages}

1. **Pockets** first (cheap, teach the machine): FP mesh + mouth band, IMP-4 with its #5 zip, IMP-8, IMP-2.
2. **Small parts**: set one B-13x swell into a scrap window before cutting B-01. Sew B-12 on the swell crest,
   then cut the swell out through the B-12's laser-cut slot. B-27 facings go inside B-01 under each slit.
3. **Door D2**: door + #10 zip into the blade U (notch at each corner tangent), hinge band. The B-22 anchors go
   INSIDE the hinge band; the B-28 front tabs go OUTSIDE (21 x 20 box-X); both before the band is joined.
4. **Main bag**: B-01 flat work first (swells, B-27 slits, B-17 outside, B-18 inside + HE outside: sketch SK-8,
   IMP-2 keeper tabs), then the gussets (B-11 tabs, RTM buckle tabs, kick bands, FP pockets, IMP-8, hose slots),
   then the box seams (K-W keepers ON TOP of the FP mesh: sketch SK-9), then the floor.
5. **Collar**: RT straps on the flat hem B-07 first (sketch SK-10), then B-06f + B-06 + B-07 + HDPE strips; collar
   ring matched at every notch.
6. **Crown lid B-29**: darts, channels, zip between the aft strips, caps, then the two ring seams.
7. **Straps** (`cutlist.md` webbing table): B-28 per crown kit, W1-W3 cut for carry, extenders, keepers.
8. **Rain fly F-01**: spine to both sides (notch to notch, the top aft corner is a V-notch), flat-fell and seam-seal,
   then the elastic channels. It packs into F-02.

## 6. Files

- `print_letter/` tiled US Letter PDFs per step + the test square.
- `dxf/primary/`, `dxf/alternate/`: one AAMA-style DXF per material (layers CUT SEW NOTCH GRAIN DRILL TEXT
  INTERNAL), webbing as hot-knife strips in its own files; `dxf/{title_fn}_all_primary.dxf` everything.
- `markers/primary/`, `markers/alternate/`: nested cutting markers per material at the real roll width (PDF, DXF,
  CSV); `markers/primary/*_10bag.*` the 10-bag production markers; `markers/markers.json` lengths and utilization.
- `cutlist.md` / `cutlist.csv`: pieces with both fabric columns, yardage for 1 / 10 / 50 / 100 bags, cutting
  instructions (face, lay, plies), webbing / cord / elastic lengths, hardware.
- `pattern_checks.md`: every seam length, the 1:1 ledger reconciliation, the mass check, the lid build hours, the
  crown draft and the placement changes. `ledger_reconciliation.csv`: the reconciliation as a table.

Yardage, full build, primary fabrics: **{yd1:.2f} yd for 1 bag**; {yd10:.1f} yd for 10, {yd50:.1f} for 50,
{yd100:.1f} for 100 bags (all materials).
"""


def export_all(nest10=True, log=print):
    t0 = time.time()
    rsP = PR.build("today")
    rsA = PR.build("B")
    log(f"built {time.time() - t0:.0f} s")
    rep = PR.seam_report(rsP)
    rec = PR.reconcile(rsA)
    mc = PR.mass_check(rsA)
    hours = PR.lid_hours(rsP)
    if REL.exists():
        shutil.rmtree(REL)
    for d in (REL / "print_letter", REL / "dxf" / "primary", REL / "dxf" / "alternate", REL / "markers" / "primary",
              REL / "markers" / "alternate", OUT):
        d.mkdir(parents=True, exist_ok=True)
    test_square_pdf(REL / "print_letter" / "00_PRINT_FIRST_test_square.pdf")
    pages = {}
    for fn, title, ids in STEPS:
        pcs = [print_copy(rsP.pieces[i]) for i in ids]          # BL-041 n-6: long notes -> NOTES page
        info = export_pdf_tiled(pcs, REL / "print_letter" / f"{fn}.pdf", "letter", compress=True, title=f"{TITLE} {title}")
        pages[fn] = info["pages"]
        if fn == "step2_small_parts" or any(len(rsP.pieces[i].labels.get("note", "")) > NOTE_MAX for i in ids):
            from pypdf import PdfReader, PdfWriter
            extra = OUT / f"_{fn}_extra.pdf"
            extra.parent.mkdir(parents=True, exist_ok=True)
            n = notes_and_marks_pdf(rsP, ids, extra, title) if fn == "step2_small_parts" else 0
            if fn != "step2_small_parts":                      # notes only (no webbing marks) for the other steps
                n = notes_only_pdf(rsP, ids, extra, title)
            n = len(PdfReader(str(extra)).pages)
            wr = PdfWriter()
            for src in (REL / "print_letter" / f"{fn}.pdf", extra):
                for pg in PdfReader(str(src)).pages:
                    wr.add_page(pg)
            with open(REL / "print_letter" / f"{fn}.pdf", "wb") as fh:
                wr.write(fh)
            pages[fn] += n
    for setname, rs in (("primary", rsP), ("alternate", rsA)):
        for mid, pcs in by_material(rs.all_pieces()).items():
            export_dxf(pcs, REL / "dxf" / setname / f"{_fname(mid)}.dxf")
    export_dxf(rsP.all_pieces(), REL / "dxf" / "corrie_f_rev3_all_primary.dxf")
    log(f"pdf + dxf {time.time() - t0:.0f} s")
    mkP = make_markers(rsP, log=log)
    mkA = make_markers(rsA, log=log)
    mk10 = {}
    if nest10:
        for mid in ("cordura_330d_nylon66", "challenge_ultra_200", "polyester_ht_630d_printable", "robic_100d_ripstop",
                    "cordura_500d_nylon66"):
            pcs = [p for p in rsP.all_pieces(sizes={PR.KIT}, webbing=False) if p.material_id == mid]
            rw, uw = roll(mid)
            t1 = time.time()
            m = nest(pcs, rw, units=NEST_UNITS, time_limit_s=NEST_TIME_S, grain_constraint=mid not in PR.FREE_ROTATION,
                     selvedge_mm=(rw - uw) / 2, spacing_mm=3.0, allow_180=mid not in PR.ONE_WAY)
            m.material_id = mid
            assert not m.unplaced
            mk10[mid] = m
            m.export_pdf(REL / "markers" / "primary" / f"{mid}_10bag.pdf", scale=0.1, compress=True)
            m.export_dxf(REL / "markers" / "primary" / f"{mid}_10bag.dxf")
            log(f"  10-bag {mid}: eff {m.efficiency:.2f}, {m.length_mm / m.units / YD:.2f} yd/bag ({time.time() - t1:.0f} s)")
    for setname, mks in (("primary", mkP), ("alternate", mkA)):
        for mid, mk in mks.items():
            d = REL / "markers" / setname
            mk.export_pdf(d / f"{mid}_1bag.pdf", compress=True)
            mk.export_dxf(d / f"{mid}_1bag.dxf")
            mk.export_csv(d / f"{mid}_1bag.csv")
    (REL / "markers" / "markers.json").write_text(json.dumps(
        {"primary_1bag": {k: v.report() for k, v in mkP.items()}, "alternate_1bag": {k: v.report() for k, v in mkA.items()},
         "primary_10bag": {k: v.report() for k, v in mk10.items()}}, indent=1, default=float))
    tot = write_cutlist(rsP, rsA, mkP, mkA, mk10, REL / "cutlist.md", REL / "cutlist.csv")
    write_checks(rsP, rsA, rep, mc, rec, hours, REL / "pattern_checks.md")
    write_recon_csv(rec, REL / "ledger_reconciliation.csv")
    s = PR.summary(rsP)
    t = tot["primary"]
    (REL / "README.md").write_text(README.format(
        title=TITLE, title_fn="corrie_f_rev3", ntypes=s["piece_types"], ncut=s["pieces_cut_all_fabric"],
        nfab=s["fabric_types"], nwebt=s["webbing_types"],
        nweb=len(rsP.webbing), nseams=len(rep.results), nmis=len(rep.mismatches), pm=mc["pattern_g"], lm=mc["ledger_g"],
        dpct=mc["delta_pct"], pages="\n".join(f"| `print_letter/{fn}.pdf` | {title} | {pages[fn]} |" for fn, title, _ in STEPS),
        yd1=t[1], yd10=t[10], yd50=t[50], yd100=t[100], rtm_z=rsP.geo["rtm"]["z"], rtm_x=rsP.geo["rtm"]["x"],
        hose_z=PR.HOSE_Z, rt_cut=next(w["length_mm"] for w in rsP.webbing if w["id"] == "RT"),
        mk0=rsP.geo["rt_layout"]["mk_dx"][0], mk1=rsP.geo["rt_layout"]["mk_dx"][1], b25=rsP.geo["b25"]["length_mm"]))
    shots = make_screens(rsP, mkP, mk10, log)
    summ = {**s, "seam_mismatches": [r.seam.name for r in rep.mismatches], "mass_check": {k: v for k, v in mc.items() if k != "rows"},
            "reconcile": {k: v for k, v in rec.items() if k != "rows"}, "lid_hours": {k: v for k, v in hours.items() if k != "rows"},
            "yardage_yd": {k: {str(n): round(y, 2) for n, y in v.items()} for k, v in tot.items()},
            "markers": {k: {"eff": round(v.efficiency, 3), "yd": round(v.length_mm / YD, 2)} for k, v in mkP.items()},
            "markers_10": {k: {"eff": round(v.efficiency, 3), "yd_per_bag": round(v.length_mm / v.units / YD, 2)} for k, v in mk10.items()},
            "pages": pages, "screens": [str(p.relative_to(ROOT)) for p in shots]}
    (OUT / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    size = sum(f.stat().st_size for f in REL.rglob("*") if f.is_file())
    log(f"release {size / 1e6:.1f} MB, done {time.time() - t0:.0f} s")
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-nest10", action="store_true")
    a = ap.parse_args()
    export_all(nest10=not a.no_nest10)
