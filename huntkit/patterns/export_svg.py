"""SVG export for laser / CNC knife cutters.

Document units are mm (width/height in mm, viewBox in mm) so 1 user unit = 1 mm.
Colour convention (common for laser software, e.g. LightBurn/RDWorks layer mapping):
  red   #FF0000  CUT (cut line, slit notches, drill holes when ``cut_drill_holes``)
  blue  #0000FF  SCORE/MARK (seam line, internal lines, grain, drill marks)
  black #000000  ENGRAVE text (labels)
V notches are merged into the cut path so the laser cuts them in one pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import svgwrite
from shapely.geometry import Polygon

from .export_dxf import arrow, layout_rows
from .piece import Piece

CUT, MARK, TEXT = "#FF0000", "#0000FF", "#000000"
HAIRLINE = 0.05  # mm


def _cut_with_v_notches(p: Piece):
    poly = p.cut_polygon()
    for kind, pts in p.notch_marks():
        if kind == "v":
            poly = poly.difference(Polygon(pts).buffer(0))
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return list(poly.exterior.coords)


def export_svg(pieces: Iterable[Piece], path: str | Path, *, labels: bool = True,
               mark_seam_line: bool = True, cut_drill_holes: bool = False,
               max_row_mm: float = 1200.0, margin_mm: float = 10.0) -> Path:
    pieces = list(pieces)
    placed = [p.transformed(dx=dx, dy=dy) for p, dx, dy in layout_rows(pieces, max_row_mm, 15)]
    X1 = max(p.bounds()[2] for p in placed) + margin_mm
    Y1 = max(p.bounds()[3] for p in placed) + margin_mm
    W, H = X1 + margin_mm, Y1 + margin_mm
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dwg = svgwrite.Drawing(str(path), size=(f"{W:.2f}mm", f"{H:.2f}mm"),
                           viewBox=f"0 0 {W:.3f} {H:.3f}")
    # SVG y runs down: flip so pattern y-up is preserved
    flip = lambda pts: [(x + margin_mm, H - (y + margin_mm)) for x, y in pts]  # noqa: E731
    g_cut = dwg.add(dwg.g(id="CUT", stroke=CUT, fill="none", stroke_width=HAIRLINE))
    g_mark = dwg.add(dwg.g(id="MARK", stroke=MARK, fill="none", stroke_width=HAIRLINE))
    g_text = dwg.add(dwg.g(id="TEXT", fill=TEXT, font_family="Helvetica", font_size=5))
    for p in placed:
        g_cut.add(dwg.polygon(flip(_cut_with_v_notches(p))))
        for kind, pts in p.notch_marks():
            if kind == "slit":
                g_cut.add(dwg.polyline(flip(pts)))
        if mark_seam_line:
            g_mark.add(dwg.polygon(flip(p.outline), stroke_dasharray="2,1"))
        for ln in p.internal_lines:
            g_mark.add(dwg.polyline(flip(ln.points)))
        for seg in arrow(*p.grain_arrow()):
            g_mark.add(dwg.polyline(flip(seg)))
        for d in p.drill_holes:
            (x, y), = flip([d.xy])
            (g_cut if cut_drill_holes else g_mark).add(dwg.circle((x, y), d.diameter / 2))
        if labels:
            cx, cy = p.seam_polygon().representative_point().coords[0]
            (x, y), = flip([(cx + 5, cy)])
            for i, t in enumerate(p.label_lines()):
                g_text.add(dwg.text(t, insert=(x, y + i * 6.5)))
    dwg.save()
    return path
