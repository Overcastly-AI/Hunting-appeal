"""Pattern piece model (contract: docs/CONTRACTS.md section 3).

Conventions
-----------
* The stored outline is the **seam line** (stitch line). The cut line is the seam line offset
  outward by the seam allowance; allowances can differ per edge.
* The outline is a closed chain of **named edges**. Each edge is a polyline (straight or curved)
  that runs from its start vertex to the start vertex of the next edge. Seams are defined between
  named edges of two pieces (see :mod:`huntkit.patterns.seams`).
* Outlines are normalised to counter-clockwise order, so the outward normal of a segment with
  direction ``(dx, dy)`` is ``(dy, -dx)``.
* ``grain`` is the grain-line angle in degrees measured CCW from the piece +x axis
  (90 = vertical, the usual drafting convention). In a marker the grain is laid along the
  marker length (fabric warp).
* ``quantity`` is the **total** number of pieces cut per unit. With ``mirror=True`` half of
  them are cut mirrored (a left/right pair), so ``quantity`` should be even.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
from shapely.geometry import LineString, Point as ShPoint, Polygon
from shapely.geometry.polygon import orient
from shapely.validation import make_valid

from . import curves as C

Point = tuple[float, float]

NOTCH_DEPTH_MM = 6.0  # 1/4" notch into the seam allowance (never past the seam line)
MITER_LIMIT = 4.0     # corners whose miter exceeds this x allowance get bevelled


def _pt(a) -> Point:
    return (float(a[0]), float(a[1]))


# --------------------------------------------------------------------------------------------
# Small value types
# --------------------------------------------------------------------------------------------
@dataclass
class Notch:
    """A match notch. (x, y) is a point ON the seam line; the mark is drawn at the cut edge,
    perpendicular to it, cutting ``depth`` mm into the allowance. kind: "slit" or "v"."""
    x: float
    y: float
    kind: str = "slit"
    depth: float = NOTCH_DEPTH_MM
    label: str = ""

    @property
    def xy(self) -> Point:
        return (self.x, self.y)


@dataclass
class DrillHole:
    """Drill (awl) mark for feature placement. Industry practice: place the mark ~3 mm inside
    the actual corner of the feature so the hole is hidden after sewing."""
    x: float
    y: float
    diameter: float = 3.0
    label: str = ""

    @property
    def xy(self) -> Point:
        return (self.x, self.y)


INTERNAL_KINDS = ("fold", "placement", "stitch", "dart", "cut_inside")


@dataclass
class InternalLine:
    points: list[Point]
    kind: str = "placement"   # fold | placement | stitch | dart | cut_inside
    label: str = ""
    closed: bool = False

    def __post_init__(self):
        if self.kind not in INTERNAL_KINDS:
            raise ValueError(f"internal line kind must be one of {INTERNAL_KINDS}")
        self.points = [(float(x), float(y)) for x, y in self.points]


@dataclass(frozen=True)
class EdgeRef:
    """Reference to a named edge of a piece (what seams are made of)."""
    piece: "Piece"
    name: str
    reverse: bool = False

    @property
    def points(self) -> list[Point]:
        pts = self.piece.edge_points(self.name)
        return pts[::-1] if self.reverse else pts

    @property
    def length(self) -> float:
        return C.polyline_length(self.piece.edge_points(self.name))

    @property
    def allowance(self) -> float:
        return self.piece.allowance(self.name)

    def reversed(self) -> "EdgeRef":
        return EdgeRef(self.piece, self.name, not self.reverse)

    def point_at(self, s: float) -> Point:
        return C.point_at_length(self.points, s)[0]

    @property
    def label(self) -> str:
        return f"{self.piece.name}.{self.name}"

    def __repr__(self) -> str:
        return f"EdgeRef({self.label}, {self.length:.1f} mm)"


# --------------------------------------------------------------------------------------------
# Piece
# --------------------------------------------------------------------------------------------
class Piece:
    """A pattern piece. See module docstring for conventions.

    Parameters (contract): ``name, outline, grain, seam_allowance_mm, notches, drill_holes,
    labels, quantity, mirror, material_id``. Extensions: ``edges`` (named vertex ranges),
    ``points`` (named grade points), ``internal_lines``, ``size``, ``face``, ``grain_line``,
    ``piece_id``, ``knife_direction``.

    ``edges`` maps edge name -> ``(i_start, i_end)`` vertex indices into ``outline``
    (``i_end`` may wrap past the last vertex). Vertices not covered get auto names ``e<i>``.
    If ``edges`` is omitted every polygon segment is its own edge ``e0, e1, ...``.
    Use :meth:`from_edges` to build from named polylines directly (usually easier).
    """

    def __init__(self, name: str, outline: Sequence[Point], grain: float = 90.0,
                 seam_allowance_mm: float | dict = 10.0, notches: Iterable = (),
                 drill_holes: Iterable = (), labels: dict | None = None, quantity: int = 1,
                 mirror: bool = False, material_id: str = "", *, edges: dict | None = None,
                 points: dict | None = None, internal_lines: Iterable[InternalLine] = (),
                 size: str = "", face: str = "up", grain_line: tuple[Point, Point] | None = None,
                 piece_id: str | None = None, knife_direction: str = "",
                 _edge_list: list[tuple[str, list[Point]]] | None = None):
        self.name = name
        self.grain = float(grain)
        self.quantity = int(quantity)
        self.mirror = bool(mirror)
        self.material_id = material_id
        self.size = size
        self.face = face
        self.piece_id = piece_id or name.upper().replace(" ", "_")
        self.knife_direction = knife_direction
        self.labels = dict(labels or {})
        self.grain_line = grain_line
        if _edge_list is not None:
            edge_list = _edge_list
        else:
            edge_list = self._edges_from_outline(outline, edges)
        self._edges: list[tuple[str, list[Point]]] = []
        self._set_edges(edge_list)
        if isinstance(seam_allowance_mm, dict):
            sa = dict(seam_allowance_mm)
            unknown = set(sa) - set(self.edge_names) - {"default"}
            if unknown:
                raise KeyError(f"{name}: seam allowance given for unknown edges {sorted(unknown)}")
            sa.setdefault("default", 10.0)
            self.seam_allowance_mm: float | dict = sa
        else:
            self.seam_allowance_mm = float(seam_allowance_mm)
        self.notches: list[Notch] = [n if isinstance(n, Notch) else Notch(*n) for n in notches]
        self.drill_holes: list[DrillHole] = [d if isinstance(d, DrillHole) else DrillHole(*d)
                                             for d in drill_holes]
        self.internal_lines: list[InternalLine] = list(internal_lines)
        self.points: dict[str, Point] = {}
        for ename, pts in self._edges:  # default grade points: every edge start vertex
            self.points[f"{ename}.start"] = pts[0]
        self.points.update({k: (float(v[0]), float(v[1])) for k, v in (points or {}).items()})

    # ---------------------------------------------------------------- construction helpers
    @classmethod
    def from_edges(cls, name: str, edges: Sequence[tuple[str, Sequence[Point]]], **kw) -> "Piece":
        """Build from an ordered list of ``(edge_name, polyline)``. Each polyline starts where
        the previous one ended (the shared end point may be repeated or omitted)."""
        lst: list[tuple[str, list[Point]]] = []
        for i, (ename, pts) in enumerate(edges):
            pts = C._dedupe(pts)
            if lst and math.dist(lst[-1][1][-1], pts[0]) > 1e-6:
                # previous edge omitted its end point: close it onto this start
                lst[-1][1].append(pts[0])
            lst.append((ename, list(pts)))
        first = lst[0][1][0]
        if math.dist(lst[-1][1][-1], first) > 1e-6:
            lst[-1][1].append(first)
        return cls(name, outline=[], _edge_list=lst, **kw)

    @staticmethod
    def _edges_from_outline(outline, edges) -> list[tuple[str, list[Point]]]:
        pts = C._dedupe(outline)
        if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-9:
            pts = pts[:-1]
        n = len(pts)
        if n < 3:
            raise ValueError("outline needs at least 3 distinct points")
        if not edges:
            return [(f"e{i}", [pts[i], pts[(i + 1) % n]]) for i in range(n)]
        owner: list[str | None] = [None] * n   # owner[i] = edge owning segment i -> i+1
        for k, (a, b) in edges.items():
            a, b = int(a) % n, int(b) % n
            cnt = (b - a) % n or n
            for j in range(cnt):
                i = (a + j) % n
                if owner[i] is not None:
                    raise ValueError(f"named edges {owner[i]!r} and {k!r} overlap")
                owner[i] = k
        for i in range(n):
            if owner[i] is None:
                owner[i] = f"e{i}"
        # start the chain at a segment whose owner differs from the previous one
        start = next((i for i in range(n) if owner[i] != owner[i - 1]), 0)
        out: list[tuple[str, list[Point]]] = []
        for j in range(n):
            i = (start + j) % n
            if out and out[-1][0] == owner[i]:
                out[-1][1].append(pts[(i + 1) % n])
            else:
                out.append((owner[i], [pts[i], pts[(i + 1) % n]]))
        return out

    def _set_edges(self, edge_list):
        names = [e for e, _ in edge_list]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.name}: duplicate edge names {names}")
        edge_list = [(e, [(float(x), float(y)) for x, y in pts]) for e, pts in edge_list]
        ring = [p for _, pts in edge_list for p in pts[:-1]]
        if Polygon(ring).exterior.is_ccw is False:
            edge_list = [(e, pts[::-1]) for e, pts in reversed(edge_list)]
        self._edges = edge_list

    def copy(self) -> "Piece":
        return copy.deepcopy(self)

    # ---------------------------------------------------------------- edges / outline
    @property
    def edge_names(self) -> list[str]:
        return [e for e, _ in self._edges]

    def edge_points(self, name: str) -> list[Point]:
        for e, pts in self._edges:
            if e == name:
                return list(pts)
        raise KeyError(f"{self.name}: no edge {name!r}; edges are {self.edge_names}")

    def edge(self, name: str) -> EdgeRef:
        self.edge_points(name)  # validate
        return EdgeRef(self, name)

    def edge_length(self, name: str) -> float:
        return C.polyline_length(self.edge_points(name))

    @property
    def outline(self) -> list[Point]:
        """Seam-line vertices (CCW, not repeated)."""
        return [p for _, pts in self._edges for p in pts[:-1]]

    def seam_polygon(self) -> Polygon:
        return Polygon(self.outline)

    def allowance(self, edge_name: str) -> float:
        sa = self.seam_allowance_mm
        if isinstance(sa, dict):
            return float(sa.get(edge_name, sa["default"]))
        return float(sa)

    def _segments(self):
        """Yield (p0, p1, allowance) for every outline segment in CCW order."""
        for e, pts in self._edges:
            a = self.allowance(e)
            for p0, p1 in zip(pts[:-1], pts[1:]):
                yield p0, p1, a

    # ---------------------------------------------------------------- cut line
    def cut_polygon(self) -> Polygon:
        seam = self.seam_polygon()
        if not isinstance(self.seam_allowance_mm, dict):
            a = float(self.seam_allowance_mm)
            if a <= 0:
                return seam
            return seam.buffer(a, join_style="mitre", mitre_limit=MITER_LIMIT)
        segs = [(np.array(p0), np.array(p1), a) for p0, p1, a in self._segments()
                if math.dist(p0, p1) > 1e-9]
        offs = []
        for p0, p1, a in segs:
            d = (p1 - p0) / np.linalg.norm(p1 - p0)
            nrm = np.array([d[1], -d[0]])
            offs.append((p0 + nrm * a, p1 + nrm * a, d, a))
        ring: list[np.ndarray] = []
        m = len(offs)
        for i in range(m):
            q0, q1, d0, a0 = offs[i - 1]
            r0, r1, d1, a1 = offs[i]
            corner = segs[i][0]
            cross = d0[0] * d1[1] - d0[1] * d1[0]
            if abs(cross) < 1e-9:
                # collinear continuation: step (if allowances differ) or continue
                if abs(a0 - a1) > 1e-9:
                    ring.extend([q1, r0])
                else:
                    ring.append(r0)
                continue
            t = ((r0 - q0)[0] * d1[1] - (r0 - q0)[1] * d1[0]) / cross
            x = q0 + d0 * t
            lim = MITER_LIMIT * max(a0, a1, 1e-6)
            if np.linalg.norm(x - corner) > lim and cross > 0:
                # sharp convex corner: bevel
                ring.extend([q1 + d0 * min(a0, lim / 2), r0 - d1 * min(a1, lim / 2)])
            else:
                ring.append(x)
        poly = Polygon([tuple(p) for p in ring])
        if not poly.is_valid:
            poly = make_valid(poly)
            if poly.geom_type != "Polygon":
                polys = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon"]
                poly = max(polys, key=lambda g: g.area)
        poly = poly.union(seam)
        if poly.geom_type != "Polygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        return orient(Polygon(poly.exterior), 1.0)

    def cut_line(self) -> list[Point]:
        """Cut-line vertices: seam line offset outward by the (per-edge) seam allowance."""
        return [tuple(p) for p in list(self.cut_polygon().exterior.coords)[:-1]]

    # ---------------------------------------------------------------- measures
    @property
    def area_mm2(self) -> float:
        """Cut area of one piece (what consumes fabric)."""
        return float(self.cut_polygon().area)

    @property
    def seam_area_mm2(self) -> float:
        return float(self.seam_polygon().area)

    @property
    def cut_perimeter_mm(self) -> float:
        return float(self.cut_polygon().exterior.length)

    @property
    def seam_perimeter_mm(self) -> float:
        return float(self.seam_polygon().exterior.length)

    def bounds(self, cut: bool = True) -> tuple[float, float, float, float]:
        return (self.cut_polygon() if cut else self.seam_polygon()).bounds

    # ---------------------------------------------------------------- marks
    def add_notch(self, x: float, y: float, kind: str = "slit", label: str = "",
                  depth: float = NOTCH_DEPTH_MM) -> Notch:
        n = Notch(x, y, kind, depth, label)
        self.notches.append(n)
        return n

    def add_notch_on_edge(self, edge: str, at: float = 0.5, *, distance_mm: float | None = None,
                          from_end: bool = False, kind: str = "slit", label: str = "") -> Notch:
        """Notch on ``edge`` at fraction ``at`` of its length, or ``distance_mm`` from its
        start (or end if ``from_end``)."""
        pts = self.edge_points(edge)
        L = C.polyline_length(pts)
        s = L * at if distance_mm is None else distance_mm
        if from_end:
            s = L - s
        (x, y), _ = C.point_at_length(pts, s)
        return self.add_notch(x, y, kind, label)

    def add_drill_hole(self, x: float, y: float, diameter: float = 3.0, label: str = "") -> DrillHole:
        d = DrillHole(x, y, diameter, label)
        self.drill_holes.append(d)
        return d

    def add_internal_line(self, points: Sequence[Point], kind: str = "placement", label: str = "",
                          closed: bool = False) -> InternalLine:
        ln = InternalLine(list(points), kind, label, closed)
        self.internal_lines.append(ln)
        return ln

    def notch_marks(self) -> list[tuple[str, list[Point]]]:
        """Notch geometry at the cut edge: ``("slit", [p_out, p_in])`` or
        ``("v", [p_left, p_tip, p_right])``. The mark points inward, perpendicular to the seam."""
        seam_ring = LineString(list(self.outline) + [self.outline[0]])
        out = []
        for n in self.notches:
            s = seam_ring.project(ShPoint(n.x, n.y))
            p = np.array(seam_ring.interpolate(s).coords[0])
            # local tangent from a small window around the projection
            L = seam_ring.length
            pa = np.array(seam_ring.interpolate((s - 0.5) % L).coords[0])
            pb = np.array(seam_ring.interpolate((s + 0.5) % L).coords[0])
            d = pb - pa
            d = d / (np.linalg.norm(d) or 1.0)
            nrm = np.array([d[1], -d[0]])  # outward (CCW ring)
            # allowance of the edge the notch sits on
            a = self._allowance_near(p)
            depth = min(n.depth, a * 0.75) if a > 0 else n.depth
            outer = p + nrm * a
            inner = outer - nrm * depth
            if n.kind == "v":
                half = depth * 0.5
                out.append(("v", [_pt(outer + d * half), _pt(inner), _pt(outer - d * half)]))
            else:
                out.append(("slit", [_pt(outer), _pt(inner)]))
        return out

    def _allowance_near(self, p) -> float:
        best, best_a = 1e18, self.allowance(self.edge_names[0])
        for e, pts in self._edges:
            dist = LineString(pts).distance(ShPoint(p))
            if dist < best:
                best, best_a = dist, self.allowance(e)
        return best_a

    def grain_arrow(self) -> tuple[Point, Point]:
        """Grain-line end points. Uses ``grain_line`` if given, else a line through the seam
        polygon's representative point, 60% of the piece extent in the grain direction."""
        if self.grain_line:
            return self.grain_line
        poly = self.seam_polygon()
        c = np.array(poly.representative_point().coords[0])
        ang = math.radians(self.grain)
        d = np.array([math.cos(ang), math.sin(ang)])
        far = LineString([tuple(c - d * 1e5), tuple(c + d * 1e5)]).intersection(poly)
        L = far.length if not far.is_empty else 50.0
        half = max(min(L * 0.3, 300.0), 10.0)
        return tuple(c - d * half), tuple(c + d * half)

    # ---------------------------------------------------------------- labels
    def label_lines(self) -> list[str]:
        cut = f"CUT {self.quantity}"
        if self.mirror:
            pairs = self.quantity // 2
            cut += f" ({pairs} PAIR{'S' if pairs != 1 else ''} L+R)" if self.quantity >= 2 \
                else " (MIRROR)"
        lines = [f"ID: {self.piece_id}", f"PIECE: {self.name}"]
        if self.size:
            lines.append(f"SIZE: {self.size}")
        lines.append(f"MATERIAL: {self.material_id or '-'}")
        lines.append(cut)
        lines.append(f"FACE {self.face.upper()}")
        if self.knife_direction:
            lines.append(f"KNIFE: {self.knife_direction}")
        for k, v in self.labels.items():
            lines.append(f"{k.upper()}: {v}")
        return lines

    # ---------------------------------------------------------------- transforms
    def transformed(self, angle_deg: float = 0.0, dx: float = 0.0, dy: float = 0.0,
                    mirror_x: bool = False, origin: Point = (0.0, 0.0)) -> "Piece":
        """Rigidly transformed copy (mirror about vertical line through origin, rotate, move).
        Edge names, allowances and marks follow the geometry."""
        T = lambda pts: C.transform(pts, angle_deg, dx, dy, mirror_x, origin)  # noqa: E731
        p = self.copy()
        edges = [(e, T(pts)) for e, pts in self._edges]
        if mirror_x:  # restore CCW order
            edges = [(e, pts[::-1]) for e, pts in reversed(edges)]
        p._edges = edges
        p.notches = [Notch(*T([n.xy])[0], n.kind, n.depth, n.label) for n in self.notches]
        p.drill_holes = [DrillHole(*T([d.xy])[0], d.diameter, d.label) for d in self.drill_holes]
        p.internal_lines = [InternalLine(T(l.points), l.kind, l.label, l.closed)
                            for l in self.internal_lines]
        p.points = {k: T([v])[0] for k, v in self.points.items()}
        g = 180.0 - self.grain if mirror_x else self.grain
        p.grain = (g + angle_deg) % 360.0
        if self.grain_line:
            p.grain_line = tuple(T(list(self.grain_line)))
        return p

    def mirrored(self) -> "Piece":
        """The opposite-hand (flipped) copy of this piece, as laid face-up for cutting."""
        x0, _, x1, _ = self.seam_polygon().bounds
        p = self.transformed(mirror_x=True, origin=((x0 + x1) / 2, 0.0))
        p.piece_id = self.piece_id + "-R" if not self.piece_id.endswith("-R") else self.piece_id[:-2]
        return p

    def instances(self) -> list[tuple["Piece", bool]]:
        """Pieces to cut per unit: ``quantity`` copies, half of them mirrored if ``mirror``."""
        if not self.mirror:
            return [(self, False)] * self.quantity
        n_r = self.quantity // 2
        n_l = self.quantity - n_r
        m = self.mirrored()
        return [(self, False)] * n_l + [(m, True)] * n_r

    def __repr__(self) -> str:
        return (f"Piece({self.name!r}, size={self.size!r}, edges={self.edge_names}, "
                f"qty={self.quantity}, mirror={self.mirror}, material={self.material_id!r})")
