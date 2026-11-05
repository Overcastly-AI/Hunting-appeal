"""Cloth mesh: flat-pattern pieces triangulated in their own (rest) plane and welded at the seams.

A :class:`ClothMesh` holds global nodes (3D start positions) and triangles. Every triangle keeps
the flat coordinates of its own piece as its rest state, rotated so the warp (grain) is local +x.
Welded seam nodes therefore have a different rest position in each piece, as a sewn seam does.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import shapely
from scipy.spatial import Delaunay, cKDTree
from shapely.geometry import Polygon

from .fabric import FabricModel


# ----------------------------------------------------------------------------- polygon mesher
def hex_grid(poly: Polygon, h: float, inset: float) -> np.ndarray:
    x0, y0, x1, y1 = poly.bounds
    dy = h * math.sqrt(3) / 2
    ys = np.arange(y0 + dy / 2, y1, dy)
    pts = []
    for j, y in enumerate(ys):
        xs = np.arange(x0 + (h / 2 if j % 2 else 0) + h / 4, x1, h)
        pts.append(np.column_stack([xs, np.full(len(xs), y)]))
    if not pts:
        return np.zeros((0, 2))
    P = np.vstack(pts)
    inner = poly.buffer(-inset)
    if inner.is_empty:
        return np.zeros((0, 2))
    return P[shapely.contains_xy(inner, P[:, 0], P[:, 1])]


def triangulate_loop(loop_xy: np.ndarray, h: float, loop_ids: np.ndarray | None = None,
                     inset: float = 0.5) -> dict:
    """Triangulate the region inside a closed boundary loop (flat coords, any orientation).

    Boundary points are kept as given (spacing should be <= h); interior points on a hexagonal
    lattice of pitch ``h``, ``inset * h`` clear of the boundary. Delaunay, then triangles whose
    centroid lies outside the polygon, or that join two copies of the same welded node (``loop_ids``
    repeated, e.g. both sides of a dart), are dropped.

    Returns ``{"xy": (k,2), "ids": (k,) global id or -1 for interior, "tris": (t,3) local,
    "missing_boundary_edges": int}``."""
    loop_xy = np.asarray(loop_xy, float)
    ids = np.arange(len(loop_xy)) if loop_ids is None else np.asarray(loop_ids)
    poly = Polygon(loop_xy)
    if not poly.is_valid:
        poly = poly.buffer(0)
        if poly.geom_type != "Polygon":
            poly = max(poly.geoms, key=lambda g: g.area)
    inner = hex_grid(poly, h, inset * h)
    # interior points too close to a boundary point would make slivers: drop them
    if len(inner):
        d, _ = cKDTree(loop_xy).query(inner)
        inner = inner[d > 0.45 * h]
    xy = np.vstack([loop_xy, inner])
    lid = np.r_[ids, -np.ones(len(inner), int)]
    tri = Delaunay(xy).simplices
    c = xy[tri].mean(1)
    ok = shapely.contains_xy(poly.buffer(1e-6), c[:, 0], c[:, 1])
    g = np.where(lid[tri] >= 0, lid[tri], -10 - tri)        # unique ids for interior points
    ok &= (g[:, 0] != g[:, 1]) & (g[:, 1] != g[:, 2]) & (g[:, 0] != g[:, 2])
    a = xy[tri]
    area = 0.5 * np.abs((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1])
                        - (a[:, 1, 1] - a[:, 0, 1]) * (a[:, 2, 0] - a[:, 0, 0]))
    ok &= area > 1e-4 * h * h
    tri = tri[ok]
    # boundary edges present?
    es = set()
    for t in tri:
        for i in range(3):
            u, v = t[i], t[(i + 1) % 3]
            es.add((min(u, v), max(u, v)))
    nb = len(loop_xy)
    miss = 0
    for i in range(nb):
        u, v = i, (i + 1) % nb
        if ids[u] == ids[v]:
            continue
        if (min(u, v), max(u, v)) not in es:
            miss += 1
    return {"xy": xy, "ids": lid, "tris": tri, "missing_boundary_edges": miss, "polygon": poly}


# ----------------------------------------------------------------------------- cloth mesh
@dataclass
class MeshPiece:
    """One piece ready to merge: local flat points, local triangles, global id per local point."""
    name: str
    xy: np.ndarray            # (k,2) rest (flat) coordinates, mm
    gid: np.ndarray           # (k,) global node id
    tris: np.ndarray          # (t,3) local indices
    fabric: FabricModel
    grain_deg: float = 90.0   # warp direction in the flat (piece) frame
    loop: list = field(default_factory=list)        # boundary loop: [(gid, edge_name)]
    meta: dict = field(default_factory=dict)


@dataclass
class ClothMesh:
    X0: np.ndarray                    # (n,3) start positions
    tris: np.ndarray                  # (T,3) global node ids, outward orientation
    tri_piece: np.ndarray             # (T,) piece index
    pieces: list                      # [MeshPiece]
    rest: np.ndarray                  # (T,3,2) rest coords in the warp frame
    beta: np.ndarray = None           # (T,3,2) shape-function gradients
    A0: np.ndarray = None             # (T,) rest area
    k1: np.ndarray = None
    k2: np.ndarray = None
    g: np.ndarray = None
    c: np.ndarray = None
    mass: np.ndarray = None           # (n,) kg
    Q: sp.csr_matrix = None           # (n,n) bending matrix (N/mm per coordinate)

    @property
    def n(self) -> int:
        return len(self.X0)

    def piece_index(self, name: str) -> int:
        return [p.name for p in self.pieces].index(name)

    def flat_area(self) -> float:
        return float(self.A0.sum())

    def area(self, x: np.ndarray, mask=None) -> float:
        a, b, c = (x[self.tris[:, j]] for j in range(3))
        ar = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        return float(ar.sum() if mask is None else ar[mask].sum())


def _cot_laplacian(xy_tri: np.ndarray, tris: np.ndarray, n: int):
    """Cotangent weights from rest triangle corners (T,3,2) on global ids (T,3). Returns
    (W sparse n x n symmetric, vertex area (n,))."""
    rows, cols, vals = [], [], []
    for k in range(3):
        i, j, o = k, (k + 1) % 3, (k + 2) % 3
        u = xy_tri[:, i] - xy_tri[:, o]
        v = xy_tri[:, j] - xy_tri[:, o]
        cr = np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])
        cot = np.einsum("ij,ij->i", u, v) / np.maximum(cr, 1e-12)
        rows += [tris[:, i], tris[:, j]]
        cols += [tris[:, j], tris[:, i]]
        vals += [0.5 * cot, 0.5 * cot]
    W = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    e1 = xy_tri[:, 1] - xy_tri[:, 0]
    e2 = xy_tri[:, 2] - xy_tri[:, 0]
    A = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    va = np.bincount(tris.ravel(), np.repeat(A / 3, 3), minlength=n)
    return W, va


def build_mesh(pieces: list[MeshPiece], X0: np.ndarray, outward_ref: np.ndarray | None = None) -> ClothMesh:
    """Merge pieces into one welded mesh. ``outward_ref`` (3,) is a point inside the closed bag:
    each piece's triangles are flipped as a block so their 3D normals point away from it."""
    n = len(X0)
    T, TP, R, K1, K2, GG, CC, RHO = [], [], [], [], [], [], [], []
    for pi, p in enumerate(pieces):
        tg = p.gid[p.tris]
        if outward_ref is not None:
            a, b, c = (X0[tg[:, j]] for j in range(3))
            nrm = np.cross(b - a, c - a)
            s = np.einsum("ij,ij->i", nrm, (a + b + c) / 3 - outward_ref).sum()
            if s < 0:
                tg = tg[:, [0, 2, 1]]
                p.tris = p.tris[:, [0, 2, 1]]
        th = math.radians(p.grain_deg)
        rot = np.array([[math.cos(th), math.sin(th)], [-math.sin(th), math.cos(th)]])  # flat -> warp frame
        xy = p.xy @ rot.T
        T.append(tg)
        TP.append(np.full(len(tg), pi))
        R.append(xy[p.tris])
        f = p.fabric
        K1.append(np.full(len(tg), f.k_warp))
        K2.append(np.full(len(tg), f.k_weft))
        GG.append(np.full(len(tg), f.shear))
        CC.append(np.full(len(tg), f.compression))
        RHO.append(np.full(len(tg), f.areal_kg_mm2))
    m = ClothMesh(X0=np.asarray(X0, float), tris=np.vstack(T), tri_piece=np.concatenate(TP), pieces=pieces,
                  rest=np.concatenate(R))
    m.k1, m.k2, m.g, m.c = (np.concatenate(v) for v in (K1, K2, GG, CC))
    Dm = np.stack([m.rest[:, 1] - m.rest[:, 0], m.rest[:, 2] - m.rest[:, 0]], -1)   # (T,2,2) columns
    det = Dm[:, 0, 0] * Dm[:, 1, 1] - Dm[:, 0, 1] * Dm[:, 1, 0]
    m.A0 = 0.5 * np.abs(det)
    B = np.linalg.inv(Dm)
    beta = np.zeros((len(det), 3, 2))
    beta[:, 1] = B[:, 0]
    beta[:, 2] = B[:, 1]
    beta[:, 0] = -(B[:, 0] + B[:, 1])
    m.beta = beta
    rho = np.concatenate(RHO)
    m.mass = np.bincount(m.tris.ravel(), np.repeat(m.A0 * rho / 3, 3), minlength=n)
    # bending: per piece, interior vertices only (seams and free edges are hinges)
    Q = sp.csr_matrix((n, n))
    for pi, p in enumerate(pieces):
        sel = m.tri_piece == pi
        tg = m.tris[sel]
        if not len(tg) or p.fabric.bending <= 0:
            continue
        W, va = _cot_laplacian(m.rest[sel], tg, n)
        L = W - sp.diags(np.asarray(W.sum(1)).ravel())
        e = np.sort(np.vstack([tg[:, [0, 1]], tg[:, [1, 2]], tg[:, [2, 0]]]), 1)
        key = e[:, 0] * n + e[:, 1]
        u, cnt = np.unique(key, return_counts=True)
        bnd = np.unique(np.r_[u[cnt == 1] // n, u[cnt == 1] % n])
        used = np.unique(tg)
        inner = np.setdiff1d(used, bnd)
        w = np.zeros(n)
        w[inner] = p.fabric.bending / np.maximum(va[inner], 1e-9)
        Q = Q + (L.T @ sp.diags(w) @ L)
    m.Q = Q.tocsr()
    return m


def weld_points(P: np.ndarray, tol: float) -> np.ndarray:
    """Union points closer than ``tol``: returns representative index per point."""
    tree = cKDTree(P)
    parent = np.arange(len(P))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in tree.query_pairs(tol):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    return np.array([find(i) for i in range(len(P))])
