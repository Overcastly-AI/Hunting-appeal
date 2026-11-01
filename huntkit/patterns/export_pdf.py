"""True-scale PDF export (reportlab).

* ``export_pdf_tiled(pieces, path, paper="letter"|"a4")`` tiles the pattern across home-printer
  pages with an overlap strip, diamond match marks labelled with the neighbouring page, a page
  map, and a 100 mm + 4 in test square on every page.
* ``paper="a0" | "a1" | "plotter36" | "plotter44"`` gives a large-format single sheet when the
  layout fits (roll plotters: fixed width, length grows with the layout), else tiles on it.

Geometry is drawn at exactly 1 mm = 72/25.4 pt. Print at 100 % ("actual size").
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Iterable, Sequence

from reportlab.lib.colors import Color, black, blue, grey, red
from reportlab.pdfgen import canvas
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.prepared import prep

from .export_dxf import arrow, layout_rows
from .piece import Piece

MM = 72.0 / 25.4  # points per mm
PAPERS = {  # (width, height) mm; None height = roll (grows with content)
    "letter": (215.9, 279.4), "a4": (210.0, 297.0), "tabloid": (279.4, 431.8),
    "a3": (297.0, 420.0), "a1": (594.0, 841.0), "a0": (841.0, 1189.0),
    "plotter36": (914.4, None), "plotter44": (1117.6, None), "plotter60": (1524.0, None),
}
LARGE = {"a0", "a1", "plotter36", "plotter44", "plotter60"}
PDF_MAX_MM = 5080.0  # PDF page size limit (200 in)
TEST_SQ_MM = 100.0
TEST_SQ_IN_MM = 101.6
TEST_BOX_MM = 112.0  # footprint reserved for the test squares + their labels

ToPt = Callable[[float, float], tuple[float, float]]


# --------------------------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------------------------
def _poly(c: canvas.Canvas, pts, to_pt: ToPt, close: bool):
    if len(pts) < 2:
        return
    path = c.beginPath()
    x, y = to_pt(*pts[0])
    path.moveTo(x, y)
    for q in pts[1:]:
        path.lineTo(*to_pt(*q))
    if close:
        path.close()
    c.drawPath(path, stroke=1, fill=0)


def draw_piece_pdf(c: canvas.Canvas, p: Piece, to_pt: ToPt, *, scale: float = 1.0,
                   labels: bool = True, font_pt: float = 9.0) -> None:
    """Draw a piece. ``to_pt`` maps piece mm coordinates to page points; ``scale`` is the
    drawing scale (1 = true size) used to size marks and text."""
    c.saveState()
    c.setStrokeColor(black)
    c.setLineWidth(0.7)
    c.setDash()
    _poly(c, p.cut_line(), to_pt, True)
    c.setLineWidth(0.35)
    c.setDash(3, 2)
    c.setStrokeColor(grey)
    _poly(c, p.outline, to_pt, True)
    for ln in p.internal_lines:
        dash = {"fold": [6, 2, 1, 2], "stitch": [3, 2]}.get(ln.kind)
        c.setDash(dash) if dash else c.setDash()
        c.setStrokeColor(blue if ln.kind != "stitch" else grey)
        _poly(c, ln.points, to_pt, ln.closed)
    c.setDash()
    c.setStrokeColor(red)
    c.setLineWidth(0.6)
    for _, pts in p.notch_marks():
        _poly(c, pts, to_pt, False)
    c.setStrokeColor(black)
    c.setLineWidth(0.4)
    for d in p.drill_holes:
        x, y = to_pt(*d.xy)
        r = max(d.diameter / 2 * MM * scale, 1.0)
        c.circle(x, y, r)
        c.line(x - 2 * r, y, x + 2 * r, y)
        c.line(x, y - 2 * r, x, y + 2 * r)
    c.setStrokeColor(blue)
    c.setLineWidth(0.5)
    g0, g1 = p.grain_arrow()
    for seg in arrow(g0, g1, head=8.0):
        _poly(c, seg, to_pt, False)
    if labels:
        poly = p.seam_polygon()
        cx, cy = poly.representative_point().coords[0]
        px, py = to_pt(cx, cy)
        lines = p.label_lines()
        fs = max(font_pt * min(1.0, scale * 4), 3.0)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", fs)
        y = py + len(lines) * fs * 1.2 / 2
        for t in lines:
            y -= fs * 1.2
            c.drawString(px + 4, y, t)
            c.setFont("Helvetica", fs)
    c.restoreState()


def draw_test_squares(c: canvas.Canvas, x_pt: float, y_pt: float, color=black) -> None:
    """100 mm square (solid) and 4 in square (dashed), sharing the lower-left corner at
    (x_pt, y_pt). Drawn in raw page units (no transform) so the size is exact."""
    s_mm = TEST_SQ_MM * MM
    s_in = 4 * 72.0
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.setDash()
    c.rect(x_pt, y_pt, s_mm, s_mm, stroke=1, fill=0)
    c.setDash(4, 2)
    c.rect(x_pt, y_pt, s_in, s_in, stroke=1, fill=0)
    c.setDash()
    c.setFillColor(color)
    c.setFont("Helvetica", 7)
    c.drawString(x_pt + 3, y_pt + s_mm - 10, "100 mm TEST SQUARE (solid)")
    c.drawString(x_pt + 3, y_pt + s_mm - 19, "4 in TEST SQUARE (dashed)")
    c.drawString(x_pt + 3, y_pt + 4, "Measure: must be exactly 100 mm / 4 in")
    c.restoreState()


def _find_free(obstacles, x0, y0, w, h, need) -> tuple[float, float] | None:
    """Lower-left of a free ``need`` x ``need`` box inside [x0, x0+w] x [y0, y0+h] (mm)."""
    if w < need or h < need:
        return None
    step = 10.0
    nx = int((w - need) // step) + 1
    ny = int((h - need) // step) + 1
    cands = [(x0 + i * step, y0 + j * step) for j in range(ny) for i in range(nx)]
    # prefer corners first
    corners = [(x0, y0), (x0 + w - need, y0), (x0, y0 + h - need), (x0 + w - need, y0 + h - need)]
    for cx, cy in corners + cands:
        if obstacles is None or not obstacles.intersects(box(cx, cy, cx + need, cy + need)):
            return cx, cy
    return None


def _placed(pieces: Sequence[Piece], max_row_mm: float):
    out = []
    for p, dx, dy in layout_rows(pieces, max_row_mm):
        out.append(p.transformed(dx=dx, dy=dy))
    return out


def _obstacles(placed: Sequence[Piece]):
    geoms = []
    for p in placed:
        geoms.append(p.cut_polygon().buffer(3))
    return prep(unary_union(geoms)) if geoms else None


# --------------------------------------------------------------------------------------------
# tiled / large format
# --------------------------------------------------------------------------------------------
def export_pdf_tiled(pieces: Iterable[Piece], path: str | Path, paper: str = "letter", *,
                     margin_mm: float = 8.0, overlap_mm: float = 12.0, landscape: bool = False,
                     title: str = "Pattern", max_row_mm: float | None = None) -> dict:
    """Write a true-scale PDF. Returns info: ``pages, cols, rows, single_sheet, page_size_mm``.

    Home papers (letter/a4/...): page 1 is the page map (+ instructions), then one page per
    tile, labelled A1, A2, ... (row letter, column number). Each tile overlaps its right and
    upper neighbours by ``overlap_mm``; trim the neighbour page along its border and align its
    border with the dashed overlap line, matching the diamond marks.
    Large papers (a0/a1/plotter*): a single sheet if it fits, otherwise tiled as above.
    """
    paper = paper.lower()
    if paper not in PAPERS:
        raise ValueError(f"paper must be one of {sorted(PAPERS)}")
    pieces = list(pieces)
    pw, ph = PAPERS[paper]
    roll = ph is None
    if landscape and not roll:
        pw, ph = ph, pw
    pr_w = pw - 2 * margin_mm
    widest = max(p.bounds()[2] - p.bounds()[0] for p in pieces)
    if max_row_mm is None:
        max_row_mm = pr_w if paper in LARGE else max(widest, 3 * (pr_w - overlap_mm))
    placed = _placed(pieces, max(max_row_mm, widest))
    obst = _obstacles(placed)
    X1 = max(p.bounds()[2] for p in placed)
    Y1 = max(p.bounds()[3] for p in placed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # ---- single large sheet?
    if paper in LARGE:
        need_w = X1 + 2 * margin_mm
        need_h = Y1 + 2 * margin_mm + TEST_BOX_MM + 20
        if roll:
            sheet_h = need_h
            fits = need_w <= pw + 1e-6 and sheet_h <= PDF_MAX_MM
        else:
            sheet_h = ph
            fits = need_w <= pw and need_h <= ph
            if not fits and need_w <= ph and need_h <= pw:  # try landscape
                pw, ph, sheet_h, fits = ph, pw, pw, True
        if fits:
            c = canvas.Canvas(str(path), pagesize=(pw * MM, sheet_h * MM), pageCompression=0)
            c.setTitle(title)
            off_y = margin_mm + TEST_BOX_MM + 10
            to_pt = lambda x, y: ((x + margin_mm) * MM, (y + off_y) * MM)  # noqa: E731
            for p in placed:
                draw_piece_pdf(c, p, to_pt)
            draw_test_squares(c, margin_mm * MM, margin_mm * MM)
            c.setFont("Helvetica-Bold", 14)
            c.drawString((margin_mm + TEST_BOX_MM) * MM, (margin_mm + 60) * MM,
                         f"{title} - {paper.upper()} single sheet - PRINT AT 100% (ACTUAL SIZE)")
            c.setFont("Helvetica", 10)
            c.drawString((margin_mm + TEST_BOX_MM) * MM, (margin_mm + 50) * MM,
                         f"{len(pieces)} pieces. Layout {X1:.0f} x {Y1:.0f} mm. Units mm.")
            c.showPage()
            c.save()
            return {"pages": 1, "cols": 1, "rows": 1, "single_sheet": True,
                    "page_size_mm": (pw, sheet_h)}
        if roll:
            ph = min(PDF_MAX_MM, max(1189.0, pw * 1.3))

    # ---- tiled
    pr_h = ph - 2 * margin_mm
    step_x, step_y = pr_w - overlap_mm, pr_h - overlap_mm
    cols = max(1, math.ceil((X1 - overlap_mm) / step_x)) if X1 > pr_w else 1
    rows = max(1, math.ceil((Y1 - overlap_mm) / step_y)) if Y1 > pr_h else 1
    total = rows * cols + 1
    c = canvas.Canvas(str(path), pagesize=(pw * MM, ph * MM), pageCompression=0)
    c.setTitle(title)

    def tile_id(r, col):
        letters = ""
        r0 = r
        while True:
            letters = chr(ord("A") + r0 % 26) + letters
            r0 = r0 // 26 - 1
            if r0 < 0:
                break
        return f"{letters}{col + 1}"

    def tile_origin(r, col):  # lower-left of tile in layout mm; row 0 = top of layout
        top = max(Y1, pr_h)
        return col * step_x, top - pr_h - r * step_y

    # ---- page 1: map
    _page_map(c, pw, ph, margin_mm, placed, rows, cols, tile_id, tile_origin, pr_w, pr_h,
              overlap_mm, title, paper, total)
    # ---- tiles
    n = 1
    for r in range(rows):
        for col in range(cols):
            n += 1
            tx, ty = tile_origin(r, col)
            to_pt = lambda x, y, tx=tx, ty=ty: ((x - tx + margin_mm) * MM,  # noqa: E731
                                                (y - ty + margin_mm) * MM)
            c.saveState()
            p = c.beginPath()
            p.rect(margin_mm * MM, margin_mm * MM, pr_w * MM, pr_h * MM)
            c.clipPath(p, stroke=0, fill=0)
            tile_box = box(tx, ty, tx + pr_w, ty + pr_h)
            for pc in placed:
                if box(*pc.bounds()).intersects(tile_box):
                    draw_piece_pdf(c, pc, to_pt)
            c.restoreState()
            # border, overlap lines and match marks
            c.setLineWidth(0.3)
            c.setStrokeColor(grey)
            c.rect(margin_mm * MM, margin_mm * MM, pr_w * MM, pr_h * MM)
            c.setDash(4, 3)
            has_right, has_up = col < cols - 1, r > 0
            has_left, has_down = col > 0, r < rows - 1
            if has_right:
                x = (margin_mm + pr_w - overlap_mm) * MM
                c.line(x, margin_mm * MM, x, (margin_mm + pr_h) * MM)
            if has_up:
                y = (margin_mm + pr_h - overlap_mm) * MM
                c.line(margin_mm * MM, y, (margin_mm + pr_w) * MM, y)
            c.setDash()
            c.setFillColor(black)
            for frac in (0.25, 0.75):
                if has_right:
                    _diamond(c, (margin_mm + pr_w - overlap_mm) * MM,
                             (margin_mm + pr_h * frac) * MM, f"{tile_id(r, col + 1)}", "right")
                if has_left:
                    _diamond(c, margin_mm * MM, (margin_mm + pr_h * frac) * MM,
                             f"{tile_id(r, col - 1)}", "left")
                if has_up:
                    _diamond(c, (margin_mm + pr_w * frac) * MM,
                             (margin_mm + pr_h - overlap_mm) * MM, f"{tile_id(r - 1, col)}", "up")
                if has_down:
                    _diamond(c, (margin_mm + pr_w * frac) * MM, margin_mm * MM,
                             f"{tile_id(r + 1, col)}", "down")
            # test squares: free spot inside this tile (excluding overlap strips) or overlay
            free = _find_free(obst, tx, ty, pr_w - (overlap_mm if has_right else 0),
                              pr_h - (overlap_mm if has_up else 0), TEST_BOX_MM)
            if free is not None:
                draw_test_squares(c, *to_pt(free[0] + 3, free[1] + 3))
            else:
                draw_test_squares(c, *to_pt(tx + 3, ty + 3), color=Color(0, 0.55, 0.9))
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(black)
            c.drawString(margin_mm * MM, (ph - margin_mm + 2) * MM,
                         f"{title}   PAGE {tile_id(r, col)}   ({n} of {total})")
            c.setFont("Helvetica", 6.5)
            c.drawRightString((pw - margin_mm) * MM, (ph - margin_mm + 2) * MM,
                              "PRINT AT 100% / ACTUAL SIZE - check test square")
            c.drawString(margin_mm * MM, (margin_mm - 5) * MM,
                         "Trim neighbour page on its border; align to dashed line; match diamonds.")
            c.showPage()
    c.save()
    return {"pages": total, "cols": cols, "rows": rows, "single_sheet": False,
            "page_size_mm": (pw, ph)}


def _diamond(c, x, y, label, side):
    s = 4.0 * MM
    p = c.beginPath()
    p.moveTo(x, y - s)
    p.lineTo(x + s, y)
    p.lineTo(x, y + s)
    p.lineTo(x - s, y)
    p.close()
    c.saveState()
    c.setFillColor(Color(0.3, 0.3, 0.3))
    c.drawPath(p, stroke=1, fill=1)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(black)
    if side == "right":
        c.drawRightString(x - s - 2, y - 2.5, f"{label} >")
    elif side == "left":
        c.drawString(x + s + 2, y - 2.5, f"< {label}")
    elif side == "up":
        c.drawString(x + s + 2, y - s - 6, f"^ {label}")
    else:
        c.drawString(x + s + 2, y + s + 2, f"v {label}")
    c.restoreState()


def _page_map(c, pw, ph, margin, placed, rows, cols, tile_id, tile_origin, pr_w, pr_h, overlap,
              title, paper, total):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin * MM, (ph - margin - 8) * MM, f"{title} - PAGE MAP")
    c.setFont("Helvetica", 8.5)
    info = [f"Paper: {paper.upper()}  {pw:.1f} x {ph:.1f} mm, {rows} rows x {cols} cols = "
            f"{rows * cols} tiles (+ this map = {total} pages).",
            "Print at 100% / ACTUAL SIZE (no 'fit to page'). Verify the 100 mm and 4 in squares.",
            f"Assemble: rows A.. top to bottom, columns 1.. left to right; overlap {overlap:.0f} mm.",
            "Lines: solid = CUT, grey dashed = SEW, red = notches, blue arrow = grain, "
            "circle+cross = drill hole."]
    y = ph - margin - 15
    for t in info:
        c.drawString(margin * MM, y * MM, t)
        y -= 5
    # map area: above test square, below text
    avail_w = pw - 2 * margin
    avail_h = y - margin - TEST_BOX_MM - 8
    full_w = cols * (pr_w - overlap) + overlap
    full_h = rows * (pr_h - overlap) + overlap
    k = min(avail_w / full_w, avail_h / full_h)
    ox = margin
    oy = margin + TEST_BOX_MM + 4
    tx0, ty0 = tile_origin(rows - 1, 0)
    to_pt = lambda x, yy: ((ox + (x - tx0) * k) * MM, (oy + (yy - ty0) * k) * MM)  # noqa: E731
    for p in placed:
        draw_piece_pdf(c, p, to_pt, scale=k, labels=True, font_pt=7)
    c.setStrokeColor(red)
    c.setLineWidth(0.4)
    for r in range(rows):
        for col in range(cols):
            x, yy = tile_origin(r, col)
            x0, y0 = to_pt(x, yy)
            c.rect(x0, y0, pr_w * k * MM, pr_h * k * MM)
            c.setFont("Helvetica-Bold", max(6, min(14, pr_w * k * MM / 4)))
            c.setFillColor(red)
            c.drawCentredString(x0 + pr_w * k * MM / 2, y0 + pr_h * k * MM / 2, tile_id(r, col))
    c.setFillColor(black)
    c.setStrokeColor(black)
    draw_test_squares(c, margin * MM, margin * MM)
    c.showPage()
