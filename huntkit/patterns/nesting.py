"""Greedy bottom-left-fill nesting marker.

Marker coordinates: x = marker length (along the fabric warp / selvedge), y = across the
fabric width. Usable band: ``selvedge_mm <= y <= fabric_width_mm - selvedge_mm``.

Grain: each piece's grain line is laid parallel to the warp (marker x axis). With
``grain_constraint=True`` only 0/180 deg about that alignment is allowed (directional or
napped fabrics: use ``allow_180=False`` to forbid even that, "one-way" marker). With
``grain_constraint=False`` (non-directional fabric such as DCF/X-Pac laminates or
non-wovens) rotations in ``free_rotation_step_deg`` steps are tried.

Algorithm: pieces (all instances: quantity x units, mirrored halves flipped) are sorted by
cut area, largest first. For each piece and allowed rotation, candidate positions are
generated from the edges of already placed pieces' bounding boxes; candidates are tried in
order of increasing x then y, the first collision-free one is taken and then compacted
(slid toward -x, then -y, by bisection). The rotation giving the smallest resulting x-extent
(then y) wins. Spacing (knife clearance) is enforced between pieces.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

from .piece import Piece


@dataclass
class Placement:
    piece: Piece            # transformed copy, in marker coordinates
    source: Piece           # original piece
    rotation_deg: float
    mirrored: bool
    unit: int

    @property
    def polygon(self) -> Polygon:
        return self.piece.cut_polygon()


@dataclass
class Marker:
    fabric_width_mm: float
    selvedge_mm: float
    spacing_mm: float
    placements: list[Placement] = field(default_factory=list)
    units: int = 1
    grain_constraint: bool = True
    material_id: str = ""
    unplaced: list[str] = field(default_factory=list)

    @property
    def usable_width_mm(self) -> float:
        return self.fabric_width_mm - 2 * self.selvedge_mm

    @property
    def length_mm(self) -> float:
        if not self.placements:
            return 0.0
        return max(p.polygon.bounds[2] for p in self.placements)

    @property
    def piece_area_mm2(self) -> float:
        return sum(p.polygon.area for p in self.placements)

    @property
    def efficiency(self) -> float:
        """Piece area / (marker length x usable width), 0..1."""
        L = self.length_mm
        return 0.0 if L == 0 else self.piece_area_mm2 / (L * self.usable_width_mm)

    @property
    def fabric_area_m2(self) -> float:
        """Fabric consumed (full roll width x marker length)."""
        return self.length_mm * self.fabric_width_mm / 1e6

    @property
    def yield_m_per_unit(self) -> float:
        """Linear metres of fabric per unit (garment/pack)."""
        return self.length_mm / 1000.0 / max(self.units, 1)

    @property
    def yield_yd_per_unit(self) -> float:
        return self.yield_m_per_unit / 0.9144

    @property
    def units_per_m(self) -> float:
        return 0.0 if self.length_mm == 0 else self.units / (self.length_mm / 1000.0)

    def summary(self) -> str:
        return (f"Marker {self.material_id or ''}: fabric {self.fabric_width_mm:.0f} mm "
                f"({self.fabric_width_mm / 25.4:.1f} in) wide, selvedge {self.selvedge_mm:.0f} mm, "
                f"{len(self.placements)} pieces, {self.units} unit(s); length "
                f"{self.length_mm:.0f} mm ({self.length_mm / 914.4:.2f} yd), efficiency "
                f"{self.efficiency * 100:.1f} %, yield {self.yield_m_per_unit:.3f} m/unit "
                f"({self.yield_yd_per_unit:.3f} yd/unit), {self.fabric_area_m2:.3f} m2 fabric"
                + (f"; UNPLACED: {self.unplaced}" if self.unplaced else ""))

    def report(self) -> dict:
        return {"material_id": self.material_id, "fabric_width_mm": self.fabric_width_mm,
                "selvedge_mm": self.selvedge_mm, "pieces": len(self.placements),
                "units": self.units, "length_mm": round(self.length_mm, 1),
                "efficiency": round(self.efficiency, 4),
                "yield_m_per_unit": round(self.yield_m_per_unit, 4),
                "yield_yd_per_unit": round(self.yield_yd_per_unit, 4),
                "fabric_area_m2": round(self.fabric_area_m2, 4), "unplaced": self.unplaced}

    # ------------------------------------------------------------------ exports
    def export_pdf(self, path: str | Path, scale: float | None = None) -> Path:
        from .export_marker import marker_pdf
        return marker_pdf(self, path, scale)

    def export_dxf(self, path: str | Path) -> Path:
        from .export_marker import marker_dxf
        return marker_dxf(self, path)

    def export_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["piece", "size", "unit", "rotation_deg", "mirrored", "x_min_mm",
                        "y_min_mm", "area_m2"])
            for p in self.placements:
                b = p.polygon.bounds
                w.writerow([p.source.name, p.source.size, p.unit, round(p.rotation_deg, 1),
                            p.mirrored, round(b[0], 1), round(b[1], 1),
                            round(p.polygon.area / 1e6, 5)])
        return path


def _rotations(piece: Piece, grain_constraint: bool, allow_180: bool, step: float) -> list[float]:
    base = -piece.grain  # rotate grain onto +x (warp)
    if grain_constraint:
        rots = [base] + ([base + 180.0] if allow_180 else [])
    else:
        n = max(1, int(round(360.0 / step)))
        rots = [base + i * step for i in range(n)]
    return [r % 360.0 for r in rots]


def nest(pieces: Iterable[Piece], fabric_width_mm: float, grain_constraint: bool = True, *,
         selvedge_mm: float = 10.0, spacing_mm: float = 3.0, units: int = 1,
         allow_180: bool = True, free_rotation_step_deg: float = 90.0,
         allow_mixed_materials: bool = False, max_length_mm: float = 1e6) -> Marker:
    """Nest pieces into a marker (see module docstring). ``pieces`` may mix sizes (e.g. the
    values of :func:`grade`); each contributes ``quantity x units`` instances."""
    pieces = list(pieces)
    mats = {p.material_id for p in pieces}
    if len(mats) > 1 and not allow_mixed_materials:
        raise ValueError(f"pieces span several materials {sorted(mats)}; nest each material "
                         f"separately (or pass allow_mixed_materials=True)")
    y_lo, y_hi = selvedge_mm, fabric_width_mm - selvedge_mm
    if y_hi <= y_lo:
        raise ValueError("selvedge margins exceed fabric width")
    items = []
    for u in range(units):
        for p in pieces:
            for inst, mirrored in p.instances():
                items.append((inst, p, mirrored, u))
    items.sort(key=lambda it: -it[0].area_mm2)

    marker = Marker(fabric_width_mm, selvedge_mm, spacing_mm, units=units,
                    grain_constraint=grain_constraint, material_id=",".join(sorted(mats)))
    placed_polys: list[Polygon] = []
    tree: STRtree | None = None
    clear = max(spacing_mm - 1e-3, 0.0)

    def collides(poly: Polygon) -> bool:
        if not placed_polys:
            return False
        test = poly.buffer(clear, join_style="mitre") if clear > 0 else poly
        for i in tree.query(test):
            other = placed_polys[i]
            if test.intersects(other) and (clear > 0 or test.intersection(other).area > 1e-6):
                return True
        return False

    def fits_band(poly: Polygon) -> bool:
        b = poly.bounds
        return b[1] >= y_lo - 1e-6 and b[3] <= y_hi + 1e-6 and b[0] >= -1e-6

    for inst, src, mirrored, unit in items:
        best = None
        for rot in _rotations(inst, grain_constraint, allow_180, free_rotation_step_deg):
            poly0 = affinity.rotate(inst.cut_polygon(), rot, origin=(0, 0))
            bx0, by0, bx1, by1 = poly0.bounds
            w, h = bx1 - bx0, by1 - by0
            if h > y_hi - y_lo + 1e-6:
                continue
            xs = {0.0} | {pp.bounds[2] + spacing_mm for pp in placed_polys}
            ys = {y_lo, y_hi - h} | {pp.bounds[3] + spacing_mm for pp in placed_polys} | \
                {pp.bounds[1] - spacing_mm - h for pp in placed_polys}
            ys = {y for y in ys if y_lo - 1e-6 <= y <= y_hi - h + 1e-6}
            cands = sorted((x, y) for x in xs for y in ys)
            found = None
            for x, y in cands:
                if best is not None and x >= best[0]:
                    break
                cand = affinity.translate(poly0, x - bx0, y - by0)
                if fits_band(cand) and not collides(cand):
                    found = (x, y)
                    break
            if found is None:
                continue
            x, y = found
            # compaction: slide -x then -y by bisection, twice
            for _ in range(2):
                for axis in (0, 1):
                    lo = 0.0
                    hi = x if axis == 0 else y - y_lo
                    while hi - lo > 0.5:
                        mid = (lo + hi) / 2
                        tx, ty = (x - mid, y) if axis == 0 else (x, y - mid)
                        cand = affinity.translate(poly0, tx - bx0, ty - by0)
                        if fits_band(cand) and not collides(cand):
                            lo = mid
                        else:
                            hi = mid
                    if axis == 0:
                        x -= lo
                    else:
                        y -= lo
            ext = x + w
            if best is None or (ext, y) < (best[0], best[1]):
                best = (ext, y, rot, x - bx0, y - by0)
        if best is None or best[0] > max_length_mm:
            marker.unplaced.append(f"{src.name}[{src.size}]")
            continue
        _, _, rot, dx, dy = best
        moved = inst.transformed(angle_deg=rot).transformed(dx=dx, dy=dy)
        marker.placements.append(Placement(moved, src, rot, mirrored, unit))
        placed_polys.append(moved.cut_polygon())
        tree = STRtree(placed_polys)
    return marker
