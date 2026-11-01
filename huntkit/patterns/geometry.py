"""Soft-goods geometry generators: panels, box bags, cylinders/roll-tops, tapers, darts,
developable (ruled) surface flattening, and volumes.

Every generator returns seam-line :class:`Piece` objects with meaningful edge names so the
seams between them can be declared and checked.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from . import curves as C
from .piece import Piece
from .seams import Seam

Point = tuple[float, float]
CORNERS = ("bl", "br", "tr", "tl")


def _radii(corner_radius) -> dict[str, float]:
    if isinstance(corner_radius, dict):
        return {k: float(corner_radius.get(k, 0.0)) for k in CORNERS}
    if isinstance(corner_radius, (list, tuple)):
        return dict(zip(CORNERS, map(float, corner_radius)))
    return {k: float(corner_radius) for k in CORNERS}


# --------------------------------------------------------------------------------------------
# Rectangle with radiused corners
# --------------------------------------------------------------------------------------------
def rect_panel(name: str, width: float, height: float, corner_radius: float | dict | Sequence = 0.0,
               *, split_corners: bool = True, **piece_kw) -> Piece:
    """Rectangle ``width`` x ``height`` (seam line) with lower-left corner at the origin.

    Edges ``bottom, right, top, left``. Corner radii (single value, per-corner dict with keys
    ``bl br tr tl`` or a 4-tuple in that order). With ``split_corners=True`` each corner arc is
    split at its midpoint between the two adjoining edges (so a gusset joined to adjacent edges
    meets at the arc middle); otherwise each arc belongs to the edge that follows it CCW.
    Grade points: ``bl br tr tl`` (the theoretical square corners' arc midpoints)."""
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    r = _radii(corner_radius)
    if r["bl"] + r["br"] > width + 1e-9 or r["tl"] + r["tr"] > width + 1e-9 or \
            r["bl"] + r["tl"] > height + 1e-9 or r["br"] + r["tr"] > height + 1e-9:
        raise ValueError("corner radii too large for panel")
    W, H = width, height
    # (centre, start angle) of each corner arc going CCW: bl(180->270), br(270->360) ...
    specs = {"bl": ((r["bl"], r["bl"]), 180), "br": ((W - r["br"], r["br"]), 270),
             "tr": ((W - r["tr"], H - r["tr"]), 0), "tl": ((r["tl"], H - r["tl"]), 90)}

    def corner(k):  # (part of the arc ending edge before, part starting the edge after)
        rad = r[k]
        (cx, cy), a0 = specs[k]
        if rad <= 0:
            return [(cx, cy)], [(cx, cy)]
        if split_corners:
            return C.arc((cx, cy), rad, a0, a0 + 45), C.arc((cx, cy), rad, a0 + 45, a0 + 90)
        full = C.arc((cx, cy), rad, a0, a0 + 90)
        return [full[0]], full

    order = [("bottom", "bl", "br"), ("right", "br", "tr"), ("top", "tr", "tl"), ("left", "tl", "bl")]
    edges = [(ename, list(corner(c0)[1]) + list(corner(c1)[0])) for ename, c0, c1 in order]
    pts_named = {}
    for k in CORNERS:
        (cx, cy), a0 = specs[k]
        a = math.radians(a0 + 45)
        pts_named[k] = (cx + r[k] * math.cos(a), cy + r[k] * math.sin(a)) if r[k] > 0 else (cx, cy)
    user_points = piece_kw.pop("points", {}) or {}
    p = Piece.from_edges(name, edges, points={**pts_named, **user_points}, **piece_kw)
    return p


# --------------------------------------------------------------------------------------------
# Tapered panel
# --------------------------------------------------------------------------------------------
def tapered_panel(name: str, width_bottom: float, width_top: float, height: float,
                  *, align: str = "center", **piece_kw) -> Piece:
    """Trapezoid: ``width_bottom`` at y=0, ``width_top`` at y=height. ``align`` = center |
    left | right. Edges ``bottom, right, top, left``; grade points ``bl br tr tl``."""
    off = {"center": (width_bottom - width_top) / 2, "left": 0.0,
           "right": width_bottom - width_top}[align]
    bl, br = (0.0, 0.0), (width_bottom, 0.0)
    tr, tl = (off + width_top, height), (off, height)
    user_points = piece_kw.pop("points", {}) or {}
    return Piece.from_edges(name, [("bottom", [bl, br]), ("right", [br, tr]), ("top", [tr, tl]),
                                   ("left", [tl, bl])],
                            points={"bl": bl, "br": br, "tr": tr, "tl": tl, **user_points}, **piece_kw)


# --------------------------------------------------------------------------------------------
# Darted panel
# --------------------------------------------------------------------------------------------
def darted_panel(name: str, width: float, height: float, dart_width: float, dart_length: float,
                 *, dart_x: float | None = None, n_darts: int = 1, **piece_kw) -> Piece:
    """Rectangle with V darts cut into the bottom edge (used to cup a pack bottom or shape a
    panel). Darts are centred at ``dart_x`` (or spaced evenly for ``n_darts``).

    Edges: ``bottom_0 .. bottom_n`` (the bottom segments between darts), ``dart<i>_l`` and
    ``dart<i>_r`` (the two legs, which sew to each other), ``right``, ``top``, ``left``.
    A drill hole marks each dart apex (3 mm inside, the industry convention) and the legs
    get notches at the mouth. Closing all darts shortens the bottom by ``n_darts*dart_width``.
    """
    if dart_length >= height:
        raise ValueError("dart longer than panel")
    centres = [dart_x if dart_x is not None else width / 2] if n_darts == 1 else \
        [width * (i + 1) / (n_darts + 1) for i in range(n_darts)]
    edges = []
    x_prev = 0.0
    apexes = []
    for i, cx in enumerate(centres):
        x0, x1 = cx - dart_width / 2, cx + dart_width / 2
        if x0 <= x_prev:
            raise ValueError("darts overlap or exceed the panel")
        apex = (cx, dart_length)
        apexes.append(apex)
        edges.append((f"bottom_{i}", [(x_prev, 0.0), (x0, 0.0)]))
        edges.append((f"dart{i}_l", [(x0, 0.0), apex]))
        edges.append((f"dart{i}_r", [apex, (x1, 0.0)]))
        x_prev = x1
    if x_prev >= width:
        raise ValueError("darts exceed the panel")
    edges.append((f"bottom_{len(centres)}", [(x_prev, 0.0), (width, 0.0)]))
    edges.append(("right", [(width, 0.0), (width, height)]))
    edges.append(("top", [(width, height), (0.0, height)]))
    edges.append(("left", [(0.0, height), (0.0, 0.0)]))
    user_points = piece_kw.pop("points", {}) or {}
    pts = {"bl": (0.0, 0.0), "br": (width, 0.0), "tr": (width, height), "tl": (0.0, height)}
    p = Piece.from_edges(name, edges, points={**pts, **user_points}, **piece_kw)
    for i, (cx, ay) in enumerate(apexes):
        p.add_drill_hole(cx, ay - 3.0, label=f"dart{i} apex")
        p.add_internal_line([(cx, 0.0), (cx, ay)], "dart", f"dart{i} fold")
    return p


def dart_seams(piece: Piece, stitch: str = "301") -> list[Seam]:
    """Seams closing every dart of a :func:`darted_panel` (leg to leg)."""
    out = []
    i = 0
    while f"dart{i}_l" in piece.edge_names:
        out.append(Seam(piece.edge(f"dart{i}_l"), piece.edge(f"dart{i}_r").reversed(),
                        stitch=stitch, name=f"{piece.name} dart{i}"))
        i += 1
    return out


# --------------------------------------------------------------------------------------------
# Box bag
# --------------------------------------------------------------------------------------------
@dataclass
class BoxBag:
    """A box bag: front & back panels (W x H, bottom corners radiused in the face plane),
    two side gussets (D wide) and a bottom panel (D wide). Top edges are left free (hem,
    binding, zipper or lid). Gusset/bottom seams sit at the corner-arc midpoints."""
    width: float
    height: float
    depth: float
    corner_radius: float
    pieces: dict[str, Piece] = field(default_factory=dict)
    seams: list[Seam] = field(default_factory=list)

    @property
    def piece_list(self) -> list[Piece]:
        return list(self.pieces.values())

    def volume_mm3(self) -> float:
        return box_bag_volume(self.pieces["front"], self.pieces["side_left"])

    def analytic_volume_mm3(self) -> float:
        r = self.corner_radius
        return (self.width * self.height - 2 * (1 - math.pi / 4) * r * r) * self.depth


def box_bag(width: float, height: float, depth: float, corner_radius: float = 0.0, *,
            seam_allowance_mm: float | dict = 10.0, material_id: str = "", size: str = "",
            stitch: str = "301", prefix: str = "") -> BoxBag:
    """Generate the 5 panels and 8 seams of a box bag (see :class:`BoxBag`)."""
    r = float(corner_radius)
    if r > min(width / 2, height, depth * 4):
        raise ValueError("corner radius too large")
    kw = dict(seam_allowance_mm=seam_allowance_mm, material_id=material_id, size=size)

    face_r = {"bl": r, "br": r, "tr": 0.0, "tl": 0.0}
    front = rect_panel(prefix + "front", width, height, face_r, quantity=1, **kw)
    back = rect_panel(prefix + "back", width, height, face_r, quantity=1, **kw)
    # The polyline arcs are slightly shorter than true arcs; size gussets from the actual
    # seam-line lengths of the face panel so the seams match exactly.
    side_len = front.edge_length("right")
    bottom_len = front.edge_length("bottom")
    side_l = rect_panel(prefix + "side_left", depth, side_len, 0.0, quantity=1, **kw)
    side_r = rect_panel(prefix + "side_right", depth, side_len, 0.0, quantity=1, **kw)
    bottom = rect_panel(prefix + "bottom", bottom_len, depth, 0.0, quantity=1, **kw)
    for p in (front, back, side_l, side_r, bottom):
        p.labels["top"] = "OPEN EDGE" if p is not bottom else ""
        if not p.labels["top"]:
            del p.labels["top"]

    # Gusset orientation: side gusset x = depth (front edge = left, back edge = right),
    # y up from bottom; bottom panel x along width, y = depth (front edge = bottom).
    # Front panel walks CCW, so its right edge runs bottom->top; the right gusset's left edge
    # runs top->bottom; reverse refs keep the walking direction consistent for notches.
    seams = [
        Seam(front.edge("right"), side_r.edge("left").reversed(), stitch=stitch),
        Seam(front.edge("left"), side_l.edge("right").reversed(), stitch=stitch),
        Seam(front.edge("bottom"), bottom.edge("bottom"), stitch=stitch),
        Seam(back.edge("right"), side_l.edge("left").reversed(), stitch=stitch),
        Seam(back.edge("left"), side_r.edge("right").reversed(), stitch=stitch),
        Seam(back.edge("bottom"), bottom.edge("top").reversed(), stitch=stitch),
        Seam(side_l.edge("bottom"), bottom.edge("left").reversed(), stitch=stitch),
        Seam(side_r.edge("bottom"), bottom.edge("right"), stitch=stitch),
    ]
    for s in seams[:6]:
        s.add_match_notches((0.5,))
    bag = BoxBag(width, height, depth, r,
                 {"front": front, "back": back, "side_left": side_l, "side_right": side_r,
                  "bottom": bottom}, seams)
    return bag


def panel_volume(face: Piece, depth_mm: float) -> float:
    """Volume (mm^3) of a prism whose cross-section is ``face``'s seam polygon."""
    return face.seam_area_mm2 * depth_mm


def box_bag_volume(face: Piece, gusset: Piece, gusset_width_edge: str = "bottom") -> float:
    """Volume of a box bag from its panels: face seam area x gusset width (the gusset's
    ``gusset_width_edge`` seam length). Assumes the gusset width is constant (true for
    :func:`box_bag`). Returns mm^3 (divide by 1e6 for litres, by 16387.064 for cu in)."""
    return panel_volume(face, gusset.edge_length(gusset_width_edge))


def litres(mm3: float) -> float:
    return mm3 / 1e6


def cubic_inches(mm3: float) -> float:
    return mm3 / 16387.064


# --------------------------------------------------------------------------------------------
# Cylinder / roll-top
# --------------------------------------------------------------------------------------------
@dataclass
class Cylinder:
    pieces: dict[str, Piece]
    seams: list[Seam]
    diameter: float
    height: float

    @property
    def piece_list(self) -> list[Piece]:
        return list(self.pieces.values())

    def volume_mm3(self) -> float:
        """Closed volume below the roll-top (base area x body height)."""
        return self.pieces["base"].seam_area_mm2 * self.height


def cylinder(diameter: float, height: float, *, rolltop_mm: float = 0.0, oval_ratio: float = 1.0,
             seam_allowance_mm: float = 10.0, top_hem_mm: float = 0.0, material_id: str = "",
             base_material_id: str | None = None, size: str = "", stitch: str = "301",
             prefix: str = "", n_base: int = 96) -> Cylinder:
    """Cylindrical sack: a body panel wrapped into a tube (one back seam ``side_a``↔``side_b``)
    and a circular (or oval, ``oval_ratio`` = minor/major) base. ``rolltop_mm`` extends the body
    above the closed height for a roll-top closure (fold line marked); ``top_hem_mm`` adds a
    hem/channel allowance on the top edge.

    Body width is the base's actual seam-line perimeter, so the base seam matches exactly."""
    a = diameter / 2
    b = a * oval_ratio
    t = np.linspace(0, 2 * math.pi, n_base, endpoint=False)
    base_pts = [(a + a * math.cos(u), b + b * math.sin(u)) for u in t]
    base = Piece.from_edges(prefix + "base", [("perimeter", base_pts + [base_pts[0]])],
                            seam_allowance_mm=seam_allowance_mm,
                            material_id=base_material_id or material_id, size=size,
                            points={"e": base_pts[0], "n": base_pts[n_base // 4],
                                    "w": base_pts[n_base // 2], "s": base_pts[3 * n_base // 4]})
    circ = base.edge_length("perimeter")
    body_h = height + rolltop_mm
    sa = {"default": seam_allowance_mm}
    if top_hem_mm:
        sa["top"] = top_hem_mm
    body = rect_panel(prefix + "body", circ, body_h, 0.0, seam_allowance_mm=sa,
                      material_id=material_id, size=size)
    # rename side edges for clarity
    body._edges = [({"left": "side_a", "right": "side_b"}.get(e, e), pts) for e, pts in body._edges]
    body.points.update({"side_a.start": body.edge_points("side_a")[0],
                        "side_b.start": body.edge_points("side_b")[0]})
    if rolltop_mm:
        body.add_internal_line([(0, height), (circ, height)], "fold", "ROLL-TOP START")
    seams = [Seam(body.edge("side_b"), body.edge("side_a").reversed(), stitch=stitch,
                  name=f"{prefix}body back seam"),
             Seam(body.edge("bottom"), base.edge("perimeter"), stitch=stitch,
                  name=f"{prefix}body to base")]
    # quarter notches on base and body bottom (matching)
    seams[1].add_match_notches((0.0, 0.25, 0.5, 0.75))
    return Cylinder({"body": body, "base": base}, seams, diameter, height)


# --------------------------------------------------------------------------------------------
# Developable (ruled) surface flattening
# --------------------------------------------------------------------------------------------
@dataclass
class DevelopedSurface:
    """Result of :func:`develop_ruled_surface`.

    ``edge_a`` / ``edge_b`` are the flattened curves (2D, mm). ``rulings`` are the flattened
    ruling lines. ``max_strain`` is the largest relative length error of the *unused* quad
    diagonals: ~0 for a truly developable surface; > ~0.5 % means the fabric must stretch or
    the surface needs a dart/seam."""
    edge_a: np.ndarray
    edge_b: np.ndarray
    rulings: list[tuple[Point, Point]]
    max_strain: float
    length_a_3d: float
    length_b_3d: float

    def outline(self) -> list[Point]:
        return [tuple(p) for p in self.edge_a] + [tuple(p) for p in self.edge_b[::-1]]

    def to_piece(self, name: str, **piece_kw) -> Piece:
        """Piece with edges ``a`` (along curve A), ``end1``, ``b`` (curve B, reversed),
        ``end0``. Rulings are drawn as placement lines."""
        A = [tuple(map(float, p)) for p in self.edge_a]
        B = [tuple(map(float, p)) for p in self.edge_b]
        p = Piece.from_edges(name, [("a", A), ("end1", [A[-1], B[-1]]), ("b", B[::-1]),
                                    ("end0", [B[0], A[0]])], **piece_kw)
        return p


def _unfold_strip(A: np.ndarray, B: np.ndarray):
    n = len(A)
    d3 = lambda p, q: float(np.linalg.norm(p - q))  # noqa: E731

    def place(p, q, dp, dq, away):
        """2D point at distance dp from p and dq from q, on the side of line p-q opposite
        to the already-placed point ``away`` (so triangles unfold instead of folding back)."""
        L = np.linalg.norm(q - p)
        x = (dp**2 - dq**2 + L**2) / (2 * L)
        h = math.sqrt(max(dp**2 - x**2, 0.0))
        u = (q - p) / L
        v = np.array([-u[1], u[0]])
        side = -1.0 if np.dot(away - p, v) > 0 else 1.0
        return p + u * x + v * h * side

    a2 = np.zeros((n, 2))
    b2 = np.zeros((n, 2))
    b2[0] = (d3(A[0], B[0]), 0.0)
    prev = np.array([b2[0][0] / 2, 1.0])  # fake previous vertex: strip unfolds toward -y
    strain = 0.0
    for i in range(n - 1):
        if d3(A[i + 1], B[i]) <= d3(A[i], B[i + 1]):  # diagonal a_{i+1}-b_i (shorter one)
            a2[i + 1] = place(a2[i], b2[i], d3(A[i], A[i + 1]), d3(B[i], A[i + 1]), prev)
            b2[i + 1] = place(a2[i + 1], b2[i], d3(A[i + 1], B[i + 1]), d3(B[i], B[i + 1]), a2[i])
            other3, other2 = d3(A[i], B[i + 1]), float(np.linalg.norm(a2[i] - b2[i + 1]))
            prev = b2[i]
        else:                                          # diagonal a_i-b_{i+1}
            b2[i + 1] = place(a2[i], b2[i], d3(A[i], B[i + 1]), d3(B[i], B[i + 1]), prev)
            a2[i + 1] = place(a2[i], b2[i + 1], d3(A[i], A[i + 1]), d3(A[i + 1], B[i + 1]), b2[i])
            other3, other2 = d3(A[i + 1], B[i]), float(np.linalg.norm(a2[i + 1] - b2[i]))
            prev = a2[i]
        if other3 > 0:
            strain = max(strain, abs(other2 - other3) / other3)
    # normalise: chord of A along +x from the origin, B above A
    chord = a2[-1] - a2[0]
    ang = math.atan2(chord[1], chord[0]) if np.linalg.norm(chord) > 1e-9 else 0.0
    R = np.array([[math.cos(-ang), -math.sin(-ang)], [math.sin(-ang), math.cos(-ang)]])
    o = a2[0].copy()
    a2 = (a2 - o) @ R.T
    b2 = (b2 - o) @ R.T
    if np.mean(b2[:, 1]) < np.mean(a2[:, 1]):
        a2[:, 1] *= -1
        b2[:, 1] *= -1
    return a2, b2, strain


def develop_ruled_surface(curve_a: Sequence[Sequence[float]], curve_b: Sequence[Sequence[float]],
                          n: int = 60) -> DevelopedSurface:
    """Flatten the ruled surface between two 3D curves (e.g. the edges of a curved pack panel).

    Both curves are resampled to ``n`` points by arc length and joined by straight rulings;
    each quad is split along its shorter diagonal and the triangle strip is unfolded
    edge-to-edge, preserving every triangle's edge lengths (exact for developable surfaces
    such as cylinders, cones and tangent developables). The developability error is reported
    as ``max_strain``. Curves must run in the same direction."""
    A = C.resample(np.asarray(curve_a, float), n)
    B = C.resample(np.asarray(curve_b, float), n)
    if A.shape[1] == 2:
        A = np.column_stack([A, np.zeros(n)])
    if B.shape[1] == 2:
        B = np.column_stack([B, np.zeros(n)])
    a2, b2, strain = _unfold_strip(A, B)
    rulings = [(tuple(map(float, a2[i])), tuple(map(float, b2[i])))
               for i in range(0, n, max(1, n // 10))]
    len3 = lambda P: float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))  # noqa: E731
    return DevelopedSurface(a2, b2, rulings, strain, len3(A), len3(B))
