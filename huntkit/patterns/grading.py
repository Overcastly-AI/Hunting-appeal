"""Grading: point-based grade rules with a proportional-scale fallback.

Rules format (dict or :class:`GradeRules`)::

    {
      "sizes": ["S", "M", "L", "XL"],     # ordered size run
      "base": "M",                         # size the piece is drafted in
      "points": {                          # grade points (names in piece.points)
          "tr": (10, 15),                  # tuple  -> per-size-step delta (dx, dy) mm
          "tl": {"S": (0, -15), "L": (0, 15), "XL": (0, 32)},   # dict -> explicit per size
      },
      "scale_step": (0.04, 0.03),          # optional proportional fallback per step (fraction)
    }

Point-graded pieces: every outline vertex that is a named grade point moves by its rule
(points without a rule stay put, delta 0, unless ``"default": "interpolate"`` is given, in
which case unruled points are treated like intermediate vertices). Vertices between grade
points (curves) get a delta interpolated by arc length between the neighbouring grade points,
which keeps curves smooth. Notches follow their position along the outline; drill holes and
internal lines take an inverse-distance-weighted delta of the grade points.

If no point rules are given (or for sizes missing from explicit dicts when
``"fallback": "scale"``), the piece is scaled proportionally about its seam-polygon centroid
by ``(1 + k*sx, 1 + k*sy)`` where ``k`` is the signed number of size steps from base.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from shapely.geometry import LineString, Point as ShPoint

from . import curves as C
from .piece import DrillHole, InternalLine, Notch, Piece

Point = tuple[float, float]


@dataclass
class GradeRules:
    sizes: list[str]
    base: str
    points: dict[str, object] = field(default_factory=dict)
    scale_step: tuple[float, float] | None = None
    default: str = "fixed"         # "fixed" | "interpolate" for unruled named points
    fallback: str = "error"        # "error" | "scale" when an explicit dict lacks a size

    @classmethod
    def coerce(cls, rules) -> "GradeRules":
        if isinstance(rules, GradeRules):
            return rules
        r = dict(rules)
        r.setdefault("points", {})
        return cls(**r)

    def step(self, size: str) -> int:
        return self.sizes.index(size) - self.sizes.index(self.base)

    def delta(self, point: str, size: str) -> Point | None:
        rule = self.points.get(point)
        if rule is None:
            return None
        if isinstance(rule, Mapping):
            if size == self.base:
                return (0.0, 0.0)
            if size not in rule:
                if self.fallback == "scale":
                    return None
                raise KeyError(f"grade rule for point {point!r} has no entry for size {size!r}")
            dx, dy = rule[size]
            return float(dx), float(dy)
        k = self.step(size)
        dx, dy = rule
        return k * float(dx), k * float(dy)


def _scale_piece(piece: Piece, sx: float, sy: float) -> Piece:
    poly = piece.seam_polygon()
    cx, cy = poly.centroid.coords[0]
    S = lambda pts: [(cx + (x - cx) * sx, cy + (y - cy) * sy) for x, y in pts]  # noqa: E731
    p = piece.copy()
    p._edges = [(e, S(pts)) for e, pts in piece._edges]
    p.notches = [Notch(*S([n.xy])[0], n.kind, n.depth, n.label) for n in piece.notches]
    p.drill_holes = [DrillHole(*S([d.xy])[0], d.diameter, d.label) for d in piece.drill_holes]
    p.internal_lines = [InternalLine(S(l.points), l.kind, l.label, l.closed)
                        for l in piece.internal_lines]
    p.points = {k: S([v])[0] for k, v in piece.points.items()}
    if piece.grain_line:
        p.grain_line = tuple(S(list(piece.grain_line)))
    return p


def _point_grade(piece: Piece, rules: GradeRules, size: str) -> Piece | None:
    ring = piece.outline
    n = len(ring)
    # which outline vertices are grade points?
    fixed: dict[int, Point] = {}
    deltas_named: dict[str, Point] = {}
    for name, xy in piece.points.items():
        idx = min(range(n), key=lambda i: (ring[i][0] - xy[0]) ** 2 + (ring[i][1] - xy[1]) ** 2)
        on_outline = (ring[idx][0] - xy[0]) ** 2 + (ring[idx][1] - xy[1]) ** 2 < 1e-6
        d = rules.delta(name, size)
        if d is None:
            if name in rules.points:      # explicit dict lacked this size -> scale fallback
                return None
            if rules.default == "interpolate":
                continue
            d = (0.0, 0.0)
        deltas_named[name] = d
        if on_outline:
            if idx in fixed and fixed[idx] != d and name in rules.points:
                fixed[idx] = d            # an explicit rule wins over a default 0
            else:
                fixed.setdefault(idx, d)
    if not any(name in rules.points for name in piece.points):
        return None
    if not fixed:
        return None
    # interpolate deltas for all outline vertices by arc length between grade points
    seg = [np.hypot(ring[(i + 1) % n][0] - ring[i][0], ring[(i + 1) % n][1] - ring[i][1])
           for i in range(n)]
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    L = cum[-1]
    keys = sorted(fixed)
    dv = np.zeros((n, 2))
    for i in range(n):
        if i in fixed:
            dv[i] = fixed[i]
            continue
        prev = max([k for k in keys if k < i], default=keys[-1])
        nxt = min([k for k in keys if k > i], default=keys[0])
        s_prev = (cum[i] - cum[prev]) % L
        s_span = (cum[nxt] - cum[prev]) % L or L
        t = s_prev / s_span
        dv[i] = (1 - t) * np.array(fixed[prev]) + t * np.array(fixed[nxt])
    moved = {ring[i]: (ring[i][0] + dv[i][0], ring[i][1] + dv[i][1]) for i in range(n)}

    ring_ls = LineString(list(ring) + [ring[0]])
    cum_ring = cum

    def outline_delta(xy) -> np.ndarray:
        s = ring_ls.project(ShPoint(xy))
        j = int(np.searchsorted(cum_ring, s, side="right") - 1) % n
        t = (s - cum_ring[j]) / (seg[j] or 1.0)
        return (1 - t) * dv[j] + t * dv[(j + 1) % n]

    gp = np.array([piece.points[k] for k in deltas_named])
    gd = np.array([deltas_named[k] for k in deltas_named])

    def idw_delta(xy) -> np.ndarray:
        d2 = np.sum((gp - np.asarray(xy)) ** 2, axis=1)
        if np.any(d2 < 1e-9):
            return gd[int(np.argmin(d2))]
        w = 1.0 / d2
        return (w[:, None] * gd).sum(0) / w.sum()

    def mv(xy, on_outline=False):
        d = outline_delta(xy) if on_outline else idw_delta(xy)
        return (float(xy[0] + d[0]), float(xy[1] + d[1]))

    p = piece.copy()
    p._edges = [(e, [moved.get(q, mv(q, True)) for q in pts]) for e, pts in piece._edges]
    p.notches = [Notch(*mv(nt.xy, True), nt.kind, nt.depth, nt.label) for nt in piece.notches]
    p.drill_holes = [DrillHole(*mv(d.xy), d.diameter, d.label) for d in piece.drill_holes]
    p.internal_lines = [InternalLine([mv(q) for q in l.points], l.kind, l.label, l.closed)
                        for l in piece.internal_lines]
    p.points = {k: (v[0] + deltas_named[k][0], v[1] + deltas_named[k][1]) if k in deltas_named
                else mv(v, True) for k, v in piece.points.items()}
    if piece.grain_line:
        p.grain_line = tuple(mv(q) for q in piece.grain_line)
    return p


def grade(piece: Piece, rules) -> dict[str, Piece]:
    """Grade ``piece`` over a size run. Returns ``{size: Piece}`` (base size included).

    Uses point grade rules where given; falls back to proportional scaling (``scale_step``)
    when the piece has no ruled points. Graded pieces keep edge names, so seams can be
    re-checked per size."""
    R = GradeRules.coerce(rules)
    if R.base not in R.sizes:
        raise ValueError(f"base size {R.base!r} not in sizes {R.sizes}")
    out: dict[str, Piece] = {}
    for size in R.sizes:
        if size == R.base:
            g = piece.copy()
        else:
            g = _point_grade(piece, R, size) if R.points else None
            if g is None:
                if R.scale_step is None:
                    raise ValueError(f"{piece.name}: no point rules apply and no scale_step "
                                     f"fallback given for size {size!r}")
                k = R.step(size)
                g = _scale_piece(piece, 1 + k * R.scale_step[0], 1 + k * R.scale_step[1])
        g.size = size
        out[size] = g
    return out


def grade_all(pieces: list[Piece], rules_by_piece: Mapping[str, object] | object) -> dict[str, list[Piece]]:
    """Grade several pieces. ``rules_by_piece`` is either one rules object for all, or a
    mapping piece name -> rules. Returns ``{size: [pieces]}``."""
    out: dict[str, list[Piece]] = {}
    for p in pieces:
        per_piece = isinstance(rules_by_piece, Mapping) and "sizes" not in rules_by_piece
        rules = rules_by_piece[p.name] if per_piece else rules_by_piece
        for size, g in grade(p, rules).items():
            out.setdefault(size, []).append(g)
    return out


def proportional_rules(sizes: list[str], base: str, step_x: float, step_y: float) -> GradeRules:
    """Convenience: pure proportional grading by fractional step (e.g. 0.04 = 4 %/size)."""
    return GradeRules(sizes=sizes, base=base, scale_step=(step_x, step_y))
