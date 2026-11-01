"""Marker exports: true-scale DXF and PDF (true scale on a roll if it fits the PDF page-size
limit, otherwise scaled with the scale printed on the sheet)."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, black, grey
from reportlab.pdfgen import canvas

from .export_dxf import _new_doc, draw_piece
from .export_pdf import MM, PDF_MAX_MM, draw_piece_pdf, draw_test_squares, TEST_BOX_MM


def marker_dxf(marker, path) -> Path:
    doc = _new_doc()
    msp = doc.modelspace()
    W, L = marker.fabric_width_mm, marker.length_mm
    msp.add_lwpolyline([(0, 0), (L, 0), (L, W), (0, W)], close=True,
                       dxfattribs={"layer": "TEXT"})  # fabric boundary
    for y in (marker.selvedge_mm, W - marker.selvedge_mm):
        msp.add_line((0, y), (L, y), dxfattribs={"layer": "TEXT", "linetype": "DASHED"})
    for pl in marker.placements:
        draw_piece(msp, pl.piece, text_height=4.0)
    msp.add_text(marker.summary()[:250], height=8.0,
                 dxfattribs={"layer": "TEXT"}).set_placement((0, -20))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return path


def marker_pdf(marker, path, scale: float | None = None) -> Path:
    """Marker PDF. ``scale=None``: true scale (1:1) if the length fits a single PDF page
    (5080 mm), else scaled to fit. Pass e.g. ``scale=0.1`` for a 1:10 overview."""
    W, L = marker.fabric_width_mm, max(marker.length_mm, 1.0)
    margin = 15.0
    head = 25.0
    if scale is None:
        scale = 1.0 if L + 2 * margin + TEST_BOX_MM <= PDF_MAX_MM else \
            (PDF_MAX_MM - 2 * margin - TEST_BOX_MM) / L
    page_w = L * scale + 2 * margin + (TEST_BOX_MM + 5 if scale == 1.0 else 0)
    page_h = W * scale + 2 * margin + head
    page_w = max(page_w, 250.0)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(page_w * MM, page_h * MM), pageCompression=0)
    c.setTitle("Marker")
    ox = margin + (TEST_BOX_MM + 5 if scale == 1.0 else 0)
    oy = margin
    to_pt = lambda x, y: ((ox + x * scale) * MM, (oy + y * scale) * MM)  # noqa: E731
    # fabric and selvedges
    c.setStrokeColor(black)
    c.setFillColor(Color(0.96, 0.96, 0.9))
    c.rect(*to_pt(0, 0), L * scale * MM, W * scale * MM, stroke=1, fill=1)
    c.setStrokeColor(grey)
    c.setDash(5, 3)
    for y in (marker.selvedge_mm, W - marker.selvedge_mm):
        c.line(*to_pt(0, y), *to_pt(L, y))
    c.setDash()
    for pl in marker.placements:
        draw_piece_pdf(c, pl.piece, to_pt, scale=scale, font_pt=7)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin * MM, (page_h - margin - 2) * MM,
                 f"MARKER  scale 1:{1 / scale:.3g}  " + ("TRUE SCALE" if scale == 1.0 else ""))
    c.setFont("Helvetica", 7.5)
    c.drawString(margin * MM, (page_h - margin - 9) * MM, marker.summary()[:220])
    c.drawString(margin * MM, (page_h - margin - 15) * MM,
                 "Warp/selvedge runs left-right. Grain arrows parallel to selvedge. "
                 "Spread fabric FACE UP unless noted.")
    if scale == 1.0:
        draw_test_squares(c, margin * MM, margin * MM)
    c.showPage()
    c.save()
    return path
