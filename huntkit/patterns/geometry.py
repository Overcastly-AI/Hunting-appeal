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
    # quarter notches on base and body bottom (matching); base also marks the back seam
    seams[1].add_match_notches((0.25, 0.5, 0.75))
    base.add_notch(*base.edge_points("perimeter")[0], kind="v", label="BACK SEAM")
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
                          n: int = 60, *, resample: bool = True) -> DevelopedSurface:
    """Flatten the ruled surface between two 3D curves (e.g. the edges of a curved pack panel).

    Both curves are resampled to ``n`` points by arc length and joined by straight rulings;
    each quad is split along its shorter diagonal and the triangle strip is unfolded
    edge-to-edge, preserving every triangle's edge lengths (exact for developable surfaces
    such as cylinders, cones and tangent developables). The developability error is reported
    as ``max_strain``. Curves must run in the same direction. With ``resample=False`` the
    curves are used as given (same point count; ruling i joins ``curve_a[i]`` to
    ``curve_b[i]``), which keeps a known parametrisation such as rings of a loft."""
    if resample:
        A = C.resample(np.asarray(curve_a, float), n)
        B = C.resample(np.asarray(curve_b, float), n)
    else:  # keep the caller's point correspondence (rulings join A[i] to B[i])
        A = np.asarray(curve_a, float)
        B = np.asarray(curve_b, float)
        if A.shape != B.shape:
            raise ValueError("resample=False needs curves with the same number of points")
        n = len(A)
    if A.shape[1] == 2:
        A = np.column_stack([A, np.zeros(n)])
    if B.shape[1] == 2:
        B = np.column_stack([B, np.zeros(n)])
    a2, b2, strain = _unfold_strip(A, B)
    rulings = [(tuple(map(float, a2[i])), tuple(map(float, b2[i])))
               for i in range(0, n, max(1, n // 10))]
    len3 = lambda P: float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))  # noqa: E731
    return DevelopedSurface(a2, b2, rulings, strain, len3(A), len3(B))


# --------------------------------------------------------------------------------------------
# Mesh flattening of doubly curved regions (strain report, darts, split lines)
# --------------------------------------------------------------------------------------------
@dataclass
class FlatMesh:
    """A surface region triangulated in its parameter plane (``uv``), its 3D image ``V3`` and
    its flat pattern ``V2`` (least-squares on every edge length, see :func:`flatten_mesh`).

    ``strain`` is flat/3D - 1 per mesh edge; ``max_strain`` is the stretch (+) or ease (-) the
    cloth would need to take the 3D shape. Use :meth:`map_uv` to carry any parameter-space
    polyline (seam, placement line, notch) onto the pattern."""
    uv: np.ndarray
    V3: np.ndarray
    V2: np.ndarray
    tris: np.ndarray
    edges: np.ndarray
    strain: np.ndarray
    boundary_edge: np.ndarray

    @property
    def max_strain(self) -> float:
        return float(np.max(np.abs(self.strain))) if self.strain.size else 0.0

    @property
    def p95_strain(self) -> float:
        return float(np.percentile(np.abs(self.strain), 95)) if self.strain.size else 0.0

    @property
    def area_3d(self) -> float:
        a, b, c = (self.V3[self.tris[:, j]] for j in range(3))
        return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum())

    @property
    def area_flat(self) -> float:
        return float(0.5 * np.abs(_signed(self.V2, self.tris)).sum())

    def tri_strain(self) -> np.ndarray:
        """Principal strain per triangle: (n, 2) array of (min, max) stretch - 1, from the
        deformation gradient taking each 3D triangle onto its flat image."""
        a, b, c = (self.V3[self.tris[:, j]] for j in range(3))
        e1 = b - a
        l1 = np.linalg.norm(e1, axis=1)
        x = e1 / l1[:, None]
        nrm = np.cross(e1, c - a)
        y = np.cross(nrm / np.linalg.norm(nrm, axis=1)[:, None], x)
        P = np.stack([np.stack([l1, np.zeros_like(l1)], 1),
                      np.stack([np.einsum("ij,ij->i", c - a, x), np.einsum("ij,ij->i", c - a, y)], 1)], 1)
        A2, B2, C2 = (self.V2[self.tris[:, j]] for j in range(3))
        Q = np.stack([B2 - A2, C2 - A2], 1)
        F = np.linalg.solve(P, Q)              # rows: local 3D -> flat
        sv = np.linalg.svd(F, compute_uv=False)
        return np.stack([sv[:, 1] - 1.0, sv[:, 0] - 1.0], 1)

    def min_angles_deg(self) -> np.ndarray:
        P = self.V3[self.tris]
        ang = []
        for j in range(3):
            u = P[:, (j + 1) % 3] - P[:, j]
            v = P[:, (j + 2) % 3] - P[:, j]
            cosv = np.einsum("ij,ij->i", u, v) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1))
            ang.append(np.degrees(np.arccos(np.clip(cosv, -1, 1))))
        return np.min(ang, axis=0)

    def strain_stats(self, sliver_deg: float = 12.0) -> dict:
        """Area-weighted principal-strain statistics (percent): max, p99, p95, mean |e|.
        Triangles with a corner under ``sliver_deg`` (mesh slivers at acute pattern corners)
        are left out of max/p99 and counted in ``slivers``; ``max_all_pct`` includes them."""
        e_all = np.abs(self.tri_strain()).max(1)
        good = self.min_angles_deg() >= sliver_deg
        e = e_all[good]
        a, b, c = (self.V3[self.tris[good, j]] for j in range(3))
        w = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        o = np.argsort(e)
        cw = np.cumsum(w[o]) / w.sum()
        pct = lambda q: float(e[o][min(np.searchsorted(cw, q), len(o) - 1)])  # noqa: E731
        return {"max_pct": 100 * float(e.max()), "p99_pct": 100 * pct(0.99),
                "p95_pct": 100 * pct(0.95), "mean_pct": 100 * float((e * w).sum() / w.sum()),
                "max_all_pct": 100 * float(e_all.max()), "slivers": int((~good).sum())}

    def folded(self) -> int:
        """Number of triangles whose flat orientation is flipped (should be 0)."""
        s_uv = _signed(self.uv, self.tris)
        s_2 = _signed(self.V2, self.tris)
        return int(np.sum(np.sign(s_uv) != np.sign(s_2)))

    def map_uv(self, pts_uv) -> np.ndarray:
        """Flat image of parameter-space points (barycentric in the containing triangle; a
        point just outside the region snaps to the nearest triangle)."""
        P = np.atleast_2d(np.asarray(pts_uv, float))
        A, B, Cc = (self.uv[self.tris[:, j]] for j in range(3))
        out = np.zeros((len(P), 2))
        for n, p in enumerate(P):
            v0, v1, v2 = B - A, Cc - A, p - A
            den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
            den = np.where(np.abs(den) < 1e-12, 1e-12, den)
            l1 = (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / den
            l2 = (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / den
            l0 = 1 - l1 - l2
            bary = np.stack([l0, l1, l2], 1)
            bad = np.clip(-bary, 0, None).sum(1)
            j = int(np.argmin(bad))
            bb = np.clip(bary[j], 0, None)
            bb /= bb.sum()
            out[n] = bb @ self.V2[self.tris[j]]
        return out


def _signed(P, tris):
    a, b, c = (P[tris[:, j]] for j in range(3))
    return (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])


def flatten_mesh(V3, tris, init2=None, *, boundary_weight: float = 30.0, max_nfev: int = 300,
                 rest_length=None):
    """Least-squares flattening of a triangle mesh: minimise the relative error of every edge
    length. Boundary edges (seams) are weighted ``boundary_weight`` so their lengths stay
    true to 3D and the interior takes the strain. ``rest_length(E) -> (m,)`` optionally gives
    the target length of each edge (vertex-index pairs) instead of its 3D chord, e.g. the
    on-surface arc length. Returns ``(V2, edges, strain, boundary)``."""
    from scipy.optimize import least_squares
    from scipy.sparse import lil_matrix

    V3 = np.asarray(V3, float)
    tris = np.asarray(tris, int)
    cnt: dict[tuple[int, int], int] = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (min(a, b), max(a, b))
            cnt[k] = cnt.get(k, 0) + 1
    E = np.array(sorted(cnt))
    bnd = np.array([cnt[tuple(e)] == 1 for e in E])
    L = np.linalg.norm(V3[E[:, 1]] - V3[E[:, 0]], axis=1)
    if rest_length is not None:
        L = np.where(L > 1e-9, np.asarray(rest_length(E), float), L)
    ok = L > 1e-9
    E, bnd, L = E[ok], bnd[ok], L[ok]
    sw = np.where(bnd, math.sqrt(boundary_weight), 1.0) / L
    x0 = (np.asarray(init2, float) if init2 is not None else V3[:, :2]).ravel()

    def res(x):
        P = x.reshape(-1, 2)
        return (np.linalg.norm(P[E[:, 1]] - P[E[:, 0]], axis=1) - L) * sw

    J = lil_matrix((len(E), V3.shape[0] * 2), dtype=int)
    for r, (a, b) in enumerate(E):
        J[r, 2 * a:2 * a + 2] = 1
        J[r, 2 * b:2 * b + 2] = 1
    sol = least_squares(res, x0, jac_sparsity=J, method="trf", x_scale="jac",
                        max_nfev=max_nfev, xtol=1e-10, ftol=1e-10)
    V2 = sol.x.reshape(-1, 2)
    strain = np.linalg.norm(V2[E[:, 1]] - V2[E[:, 0]], axis=1) / L - 1.0
    return V2, E, strain, bnd


def develop_region(surface, polygon_uv, spacing: float = 10.0, *, boundary_spacing: float | None = None,
                   boundary_weight: float = 30.0, max_nfev: int = 300) -> FlatMesh:
    """Develop the part of a parametric surface ``surface(uv: (n,2)) -> (n,3)`` that lies inside
    ``polygon_uv`` (a shapely Polygon or a point ring in parameter units, ideally ~mm).

    The region is meshed in the parameter plane (boundary sampled every ``boundary_spacing``,
    interior grid every ``spacing``, Delaunay, triangles kept whose centroid is inside), lifted
    to 3D and flattened with :func:`flatten_mesh`. Darts are thin wedges cut out of the
    polygon; split lines are just polygon edges. The flat pattern is oriented so the parameter
    axes keep their handedness (u -> +x, v -> +y as seen from the side du x dv points to)."""
    from scipy.spatial import Delaunay
    from shapely.geometry import Point as _P, Polygon as _Poly
    from shapely.prepared import prep as _prep

    poly = polygon_uv if hasattr(polygon_uv, "exterior") else _Poly(polygon_uv)
    bs = boundary_spacing or spacing / 2
    ring = np.asarray(poly.exterior.coords)
    bpts = []
    for p, q in zip(ring[:-1], ring[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(q - p) / bs)))
        for j in range(n):
            bpts.append(p + (q - p) * j / n)
    bpts = np.array(bpts)
    x0, y0, x1, y1 = poly.bounds
    gx = np.arange(x0 + spacing / 2, x1, spacing)
    gy = np.arange(y0 + spacing / 2, y1, spacing)
    inner = poly.buffer(-0.45 * spacing)
    pin = _prep(inner) if not inner.is_empty else None
    grid = [(x, y) for x in gx for y in gy if pin is not None and pin.contains(_P(x, y))]
    uv = np.vstack([bpts, np.array(grid).reshape(-1, 2)])
    tri = Delaunay(uv).simplices
    pp = _prep(poly.buffer(1e-6))
    cen = uv[tri].mean(1)
    keep = np.array([pp.contains(_P(*c)) for c in cen])
    tri = tri[keep]
    # drop unused points
    used = np.unique(tri)
    remap = -np.ones(len(uv), int)
    remap[used] = np.arange(len(used))
    uv = uv[used]
    tri = remap[tri]
    # orient triangles CCW in uv
    sgn = _signed(uv, tri)
    tri[sgn < 0] = tri[sgn < 0][:, [0, 2, 1]]
    V3 = np.asarray(surface(uv), float)

    def arc_len(E):
        # on-surface edge length: Richardson extrapolation of chord (h) and two half chords (h/2),
        # error O(h^4) instead of the chord's O(h^2), so a developable region unrolls to true size
        a, b = V3[E[:, 0]], V3[E[:, 1]]
        m = np.asarray(surface(0.5 * (uv[E[:, 0]] + uv[E[:, 1]])), float)
        c1 = np.linalg.norm(b - a, axis=1)
        c2 = np.linalg.norm(m - a, axis=1) + np.linalg.norm(b - m, axis=1)
        return (4.0 * c2 - c1) / 3.0

    V2, E, strain, bnd = flatten_mesh(V3, tri, init2=uv, boundary_weight=boundary_weight,
                                      max_nfev=max_nfev, rest_length=arc_len)
    if np.sum(_signed(V2, tri) < 0) > len(tri) / 2:
        V2[:, 0] *= -1
    # align: least-squares rigid fit of flat onto uv (keeps the pattern upright)
    R, t = _kabsch2(V2, uv)
    V2 = V2 @ R.T + t
    return FlatMesh(uv, V3, V2, tri, E, strain, bnd)


def _kabsch2(P: np.ndarray, Q: np.ndarray):
    """Rigid (rotation + translation, no reflection) 2D fit taking P onto Q."""
    pc, qc = P.mean(0), Q.mean(0)
    H = (P - pc).T @ (Q - qc)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T)) or 1.0
    R = Vt.T @ np.diag([1.0, d]) @ U.T
    return R, qc - pc @ R.T
