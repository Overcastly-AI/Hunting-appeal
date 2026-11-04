"""DXF export (ezdxf), AAMA/ASTM D6673-style: one BLOCK per piece, inserted in modelspace.

Layers (with the AAMA layer number each corresponds to, noted in the layer description):
  CUT    (AAMA 1)  cut line / piece boundary
  SEW    (AAMA 14) seam (stitch) line and stitch internal lines
  INTERNAL (AAMA 8) fold / placement / dart lines (``cut_inside`` holes go on CUT)
  NOTCH  (AAMA 4)  notches (slit = line, V = 2-segment polyline)
  GRAIN  (AAMA 7)  grain line with arrow heads
  DRILL  (AAMA 13) drill holes (POINT + circle)
  TEXT   (AAMA 15) piece annotation (ID, size, material, quantity, face)
Units: millimetres ($INSUNITS = 4).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import ezdxf

from .piece import Piece

LAYERS = {
    "CUT": (7, "AAMA 1 boundary/cut line"),
    "SEW": (3, "AAMA 14 sew line"),
    "INTERNAL": (6, "AAMA 8 internal lines (fold/placement/dart)"),
    "NOTCH": (1, "AAMA 4 notches"),
    "GRAIN": (5, "AAMA 7 grain line"),
    "DRILL": (4, "AAMA 13 drill holes"),
    "TEXT": (2, "AAMA 15 annotation text"),
}


def _new_doc():
    doc = ezdxf.new("R2000", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for name, (color, desc) in LAYERS.items():
        if name not in doc.layers:
            lay = doc.layers.add(name, color=color)
            lay.description = desc
    return doc


def _block_name(p: Piece, idx: int) -> str:
    base = f"{p.piece_id}_{p.size}" if p.size else p.piece_id
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in base) + f"_{idx}"


def arrow(p0, p1, head: float = 8.0) -> list[list[tuple[float, float]]]:
    """Grain arrow as polylines: shaft plus two-sided heads."""
    (x0, y0), (x1, y1) = p0, p1
    ang = math.atan2(y1 - y0, x1 - x0)
    out = [[p0, p1]]
    for (x, y), a in (((x1, y1), ang + math.pi), ((x0, y0), ang)):
        out.append([(x + head * math.cos(a + 0.4), y + head * math.sin(a + 0.4)), (x, y),
                    (x + head * math.cos(a - 0.4), y + head * math.sin(a - 0.4))])
    return out


def draw_piece(layout, p: Piece, text_height: float = 5.0, with_text: bool = True) -> None:
    """Draw one piece's entities into ``layout`` (a block, modelspace, ...)."""
    layout.add_lwpolyline(p.cut_line(), close=True, dxfattribs={"layer": "CUT"})
    layout.add_lwpolyline(p.outline, close=True, dxfattribs={"layer": "SEW", "linetype": "DASHED"})
    for ln in p.internal_lines:
        layer = {"stitch": "SEW", "cut_inside": "CUT"}.get(ln.kind, "INTERNAL")
        lt = {"fold": "DASHDOT", "stitch": "DASHED"}.get(ln.kind, "CONTINUOUS")
        layout.add_lwpolyline(ln.points, close=ln.closed, dxfattribs={"layer": layer, "linetype": lt})
    for kind, pts in p.notch_marks():
        layout.add_lwpolyline(pts, dxfattribs={"layer": "NOTCH"})
    for d in p.drill_holes:
        layout.add_point(d.xy, dxfattribs={"layer": "DRILL"})
        layout.add_circle(d.xy, d.diameter / 2, dxfattribs={"layer": "DRILL"})
    g0, g1 = p.grain_arrow()
    for seg in arrow(g0, g1):
        layout.add_lwpolyline(seg, dxfattribs={"layer": "GRAIN"})
    if with_text:
        poly = p.seam_polygon()
        cx, cy = poly.representative_point().coords[0]
        lines = p.label_lines()
        y = cy + (len(lines) / 2) * text_height * 1.6
        for t in lines:
            y -= text_height * 1.6
            layout.add_text(t, height=text_height, dxfattribs={"layer": "TEXT"}).set_placement(
                (cx + 12, y))


def layout_rows(pieces: Sequence[Piece], max_row_mm: float = 2000.0, gap: float = 30.0):
    """Shelf layout for display/export: yields (piece, dx, dy) placing each piece's cut bbox."""
    x = y = row_h = 0.0
    out = []
    for p in pieces:
        x0, y0, x1, y1 = p.bounds()
        w, h = x1 - x0, y1 - y0
        if x > 0 and x + w > max_row_mm:
            x, y, row_h = 0.0, y + row_h + gap, 0.0
        out.append((p, x - x0, y - y0))
        x += w + gap
        row_h = max(row_h, h)
    return out


def export_dxf(pieces: Iterable[Piece], path: str | Path, *, text_height: float = 5.0,
               max_row_mm: float = 2000.0) -> Path:
    """Write pieces to a DXF file. Each piece becomes a BLOCK (AAMA style) inserted in
    modelspace, laid out in rows; the block carries the piece annotation on layer TEXT."""
    pieces = list(pieces)
    doc = _new_doc()
    msp = doc.modelspace()
    for i, (p, dx, dy) in enumerate(layout_rows(pieces, max_row_mm)):
        name = _block_name(p, i)
        blk = doc.blocks.new(name=name)
        draw_piece(blk, p, text_height)
        msp.add_blockref(name, (dx, dy), dxfattribs={"layer": "CUT"})
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    return path
