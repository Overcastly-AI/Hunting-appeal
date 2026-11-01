"""Curve primitives (polyline approximations) and small polyline utilities.

All coordinates are mm. Curves are returned as ``list[(x, y)]`` including both end points,
so they can be passed straight in as named edges of a :class:`~huntkit.patterns.piece.Piece`.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

Point = tuple[float, float]


def _arr(pts) -> np.ndarray:
    a = np.asarray(pts, dtype=float)
    if a.ndim != 2 or a.shape[1] < 2:
        raise ValueError(f"expected Nx2 points, got shape {a.shape}")
    return a


def line(p0: Point, p1: Point, n: int = 1) -> list[Point]:
    """Straight segment p0 -> p1 split into ``n`` pieces (n+1 points)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    t = np.linspace(0.0, 1.0, n + 1)[:, None]
    return [tuple(p) for p in (p0 + (p1 - p0) * t)]


def bezier(*ctrl: Point, n: int = 32) -> list[Point]:
    """Bezier curve of any degree through control points ``ctrl`` (2 = line, 3 = quadratic,
    4 = cubic). Returns ``n + 1`` points from first to last control point."""
    if len(ctrl) < 2:
        raise ValueError("bezier needs at least 2 control points")
    c = _arr(ctrl)
    k = len(c) - 1
    t = np.linspace(0.0, 1.0, n + 1)
    out = np.zeros((n + 1, 2))
    for i, p in enumerate(c):
        b = math.comb(k, i) * t**i * (1 - t) ** (k - i)
        out += b[:, None] * p[None, :2]
    return [tuple(p) for p in out]


def arc(center: Point, radius: float, a0_deg: float, a1_deg: float,
        n: int | None = None, max_seg_mm: float = 2.0) -> list[Point]:
    """Circular arc from angle a0 to a1 (degrees, CCW positive; a1 < a0 runs clockwise).

    ``n`` segments, or enough segments that none is longer than ``max_seg_mm``."""
    sweep = math.radians(a1_deg - a0_deg)
    if n is None:
        n = max(4, int(math.ceil(abs(sweep) * radius / max_seg_mm)))
    t = np.linspace(math.radians(a0_deg), math.radians(a0_deg) + sweep, n + 1)
    cx, cy = center
    return [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in t]


def arc_3pt(p0: Point, pm: Point, p1: Point, n: int | None = None) -> list[Point]:
    """Circular arc through three points."""
    (x1, y1), (x2, y2), (x3, y3) = p0, pm, p1
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return line(p0, p1)
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a0 = math.degrees(math.atan2(y1 - uy, x1 - ux))
    am = math.degrees(math.atan2(y2 - uy, x2 - ux))
    a1 = math.degrees(math.atan2(y3 - uy, x3 - ux))

    def ccw(a, b):  # CCW sweep from a to b in [0, 360)
        return (b - a) % 360.0

    if ccw(a0, am) <= ccw(a0, a1):
        return arc((ux, uy), r, a0, a0 + ccw(a0, a1), n)
    return arc((ux, uy), r, a0, a0 - (360.0 - ccw(a0, a1)), n)


def polyline_length(pts: Sequence[Point]) -> float:
    a = _arr(pts)
    if len(a) < 2:
        return 0.0
    return float(np.sum(np.hypot(*np.diff(a[:, :2], axis=0).T)))


def cumulative_length(pts: Sequence[Point]) -> np.ndarray:
    a = _arr(pts)
    seg = np.hypot(*np.diff(a[:, :2], axis=0).T)
    return np.concatenate([[0.0], np.cumsum(seg)])


def point_at_length(pts: Sequence[Point], s: float) -> tuple[Point, Point]:
    """Point at arc length ``s`` along a polyline and the unit tangent there."""
    a = _arr(pts)[:, :2]
    cum = cumulative_length(a)
    s = min(max(s, 0.0), cum[-1])
    i = int(np.searchsorted(cum, s, side="right") - 1)
    i = min(max(i, 0), len(a) - 2)
    seg = cum[i + 1] - cum[i]
    t = 0.0 if seg == 0 else (s - cum[i]) / seg
    p = a[i] + (a[i + 1] - a[i]) * t
    d = a[i + 1] - a[i]
    nd = np.hypot(*d)
    tan = (1.0, 0.0) if nd == 0 else (d[0] / nd, d[1] / nd)
    return (float(p[0]), float(p[1])), (float(tan[0]), float(tan[1]))


def resample(pts: Sequence[Point], n: int) -> np.ndarray:
    """Resample a 2D or 3D polyline to ``n`` points evenly spaced by arc length."""
    a = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(a, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    s = np.linspace(0.0, cum[-1], n)
    return np.column_stack([np.interp(s, cum, a[:, k]) for k in range(a.shape[1])])


def split_at_length(pts: Sequence[Point], s: float) -> tuple[list[Point], list[Point]]:
    """Split a polyline at arc length ``s`` into two polylines sharing the split point."""
    a = _arr(pts)[:, :2]
    cum = cumulative_length(a)
    p, _ = point_at_length(a, s)
    i = int(np.searchsorted(cum, s, side="right"))
    first = [tuple(q) for q in a[:i]] + [p]
    second = [p] + [tuple(q) for q in a[i:]]
    first = _dedupe(first)
    second = _dedupe(second)
    return first, second


def _dedupe(pts: Iterable[Point], tol: float = 1e-9) -> list[Point]:
    out: list[Point] = []
    for p in pts:
        p = (float(p[0]), float(p[1]))
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    return out


def transform(pts: Iterable[Point], angle_deg: float = 0.0, dx: float = 0.0, dy: float = 0.0,
              mirror_x: bool = False, origin: Point = (0.0, 0.0)) -> list[Point]:
    """Mirror about the vertical line through ``origin`` (optional), rotate about ``origin``,
    then translate."""
    ox, oy = origin
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    out = []
    for x, y in pts:
        x, y = x - ox, y - oy
        if mirror_x:
            x = -x
        out.append((ox + c * x - s * y + dx, oy + s * x + c * y + dy))
    return out
