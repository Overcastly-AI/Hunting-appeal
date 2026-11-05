"""Sew flat pieces in 3D: shared boundary nodes by notch position, then triangulate every piece.

Each :class:`PieceSpec` gives its boundary as named edges, each a dense flat polyline plus the 3D
position of the same points in the arranged (pre-sewn) state, and a map flat -> 3D for interior
points. Two edges are sewn where their arranged 3D curves coincide (within ``tol``). For the pack
that arrangement is the master surface the pattern was developed from, so this pairs exactly the
points the pattern's 50 mm notches pair (``designs/pack_5200/patterns_v31.py`` ``_notch_along``).

Pass 1 places nodes along every boundary at spacing <= h, reusing nodes already placed by a
neighbour. Pass 2 lets every piece collect all nodes lying on its boundary, so the mesh is
conforming (no hanging nodes) even where neighbours were meshed differently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.spatial import cKDTree

from .fabric import FabricModel
from .mesh import ClothMesh, MeshPiece, build_mesh, triangulate_loop, weld_points


@dataclass
class PieceSpec:
    name: str
    edges: list                      # [(edge_name, flat (k,2), X3 (k,3))] in loop order
    map3d: Callable                  # flat (m,2) -> (m,3)
    fabric: FabricModel
    grain_deg: float = 90.0
    rest_map: Callable | None = None  # flat -> adjusted rest flat (panel adjustments); None = identity
    meta: dict = field(default_factory=dict)


def densify(P: np.ndarray, step: float) -> np.ndarray:
    P = np.asarray(P, float)
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        t = (np.arange(1, k + 1) / k)[:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


def _project(edge_flat, edge3, idx, q):
    """Project 3D point q onto the segments next to dense index idx; return (flat point, param)."""
    best = None
    for i0 in (idx - 1, idx):
        if i0 < 0 or i0 + 1 >= len(edge3):
            continue
        a, b = edge3[i0], edge3[i0 + 1]
        ab = b - a
        t = float(np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-12), 0, 1))
        d = np.linalg.norm(a + t * ab - q)
        if best is None or d < best[0]:
            best = (d, i0 + t, edge_flat[i0] + t * (edge_flat[i0 + 1] - edge_flat[i0]))
    if best is None:
        return edge_flat[idx], float(idx), 0.0
    return best[2], best[1], best[0]


def assemble(specs: list[PieceSpec], h: float, tol: float = 1.5, outward_ref=None) -> tuple[ClothMesh, dict]:
    G3: list = []

    def tree():
        return cKDTree(np.array(G3)) if G3 else None

    # ---- pass 1: boundary nodes
    for sp_ in specs:
        for en, fl, x3 in sp_.edges:
            fl, x3 = np.asarray(fl, float), np.asarray(x3, float)
            tr = tree()
            anchors = {}
            if tr is not None:
                seg = np.linalg.norm(np.diff(x3, axis=0), axis=1)
                GG = np.array(G3)
                d, j = cKDTree(x3).query(GG, distance_upper_bound=tol + 0.5 * float(seg.max(initial=0)) + 1e-9)
                for gi in np.where(np.isfinite(d))[0]:
                    _, par, dist = _project(fl, x3, int(j[gi]), GG[gi])
                    if dist < tol:
                        anchors[int(j[gi])] = gi
            for end in (0, len(x3) - 1):
                if end not in anchors:
                    near = None
                    tr = tree()
                    if tr is not None:
                        dd, gg = tr.query(x3[end])
                        if dd < tol:
                            near = int(gg)
                    if near is None:
                        G3.append(x3[end].copy())
                        near = len(G3) - 1
                    anchors[end] = near
            ks = sorted(anchors)
            s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(fl, axis=0), axis=1))]
            for a, b in zip(ks[:-1], ks[1:]):
                L = s[b] - s[a]
                m = int(np.ceil(L / h - 0.2))
                for i in range(1, m):
                    si = s[a] + L * i / m
                    k = int(np.searchsorted(s, si))
                    k = min(max(k, 1), len(s) - 1)
                    w = (si - s[k - 1]) / max(s[k] - s[k - 1], 1e-12)
                    G3.append(x3[k - 1] + w * (x3[k] - x3[k - 1]))
    G3a = np.array(G3)
    # nodes placed twice on coincident curves (e.g. a closure folded onto itself) -> one node
    rep = weld_points(G3a, 0.5 * tol)
    G3a = G3a[np.unique(rep)]
    # ---- pass 2: loops, triangulation
    pieces, X_extra = [], []
    nb = len(G3a)
    nxt = nb
    diag = {"missing_boundary_edges": {}, "boundary_nodes": nb}
    for sp_ in specs:
        loop_xy, loop_g, loop_e = [], [], []
        for en, fl, x3 in sp_.edges:
            fl, x3 = np.asarray(fl, float), np.asarray(x3, float)
            seg = np.linalg.norm(np.diff(x3, axis=0), axis=1)
            d, j = cKDTree(x3).query(G3a, distance_upper_bound=tol + 0.5 * float(seg.max(initial=0)) + 1e-9)
            hit = np.where(np.isfinite(d))[0]
            items = []
            for gi in hit:
                xy, par, dist = _project(fl, x3, int(j[gi]), G3a[gi])
                if dist < tol:
                    items.append((par, int(gi), xy))
            items.sort(key=lambda t: t[0])
            for par, gi, xy in items:
                if loop_g and loop_g[-1] == gi:
                    loop_e[-1] = loop_e[-1] | {en}
                    continue
                loop_xy.append(xy)
                loop_g.append(gi)
                loop_e.append({en})
        if len(loop_g) > 1 and loop_g[0] == loop_g[-1]:
            loop_xy.pop()
            loop_g.pop()
            loop_e[0] = loop_e[0] | loop_e.pop()
        loop_xy = np.array(loop_xy)
        loop_g = np.array(loop_g)
        # merge coincident flat points (dart apex): same node, same place
        keep = np.ones(len(loop_xy), bool)
        for i in range(len(loop_xy)):
            j = (i + 1) % len(loop_xy)
            if np.linalg.norm(loop_xy[i] - loop_xy[j]) < 1e-3 and loop_g[i] == loop_g[j]:
                keep[j] = False
        loop_xy, loop_g, loop_e = loop_xy[keep], loop_g[keep], [e for e, k in zip(loop_e, keep) if k]
        tri = triangulate_loop(loop_xy, h, loop_g)
        diag["missing_boundary_edges"][sp_.name] = tri["missing_boundary_edges"]
        ids = tri["ids"].copy()
        inner = ids < 0
        ni = int(inner.sum())
        if ni:
            X_extra.append(np.asarray(sp_.map3d(tri["xy"][inner]), float))
            ids[inner] = np.arange(nxt, nxt + ni)
            nxt += ni
        xy_rest = tri["xy"] if sp_.rest_map is None else np.asarray(sp_.rest_map(tri["xy"]), float)
        nl = len(loop_g)     # local points 0..nl-1 are the loop (triangulate_loop keeps them first)

        def lab(i, j):
            com = loop_e[i] & loop_e[j]
            return sorted(com)[0] if com else sorted(loop_e[j])[0]
        segs = [(int(loop_g[i]), int(loop_g[(i + 1) % nl]), lab(i, (i + 1) % nl), i, (i + 1) % nl)
                for i in range(nl)]
        mp = MeshPiece(sp_.name, xy_rest, ids, tri["tris"], sp_.fabric, sp_.grain_deg,
                       loop=segs, meta={**sp_.meta, "flat_xy": tri["xy"], "polygon_area": tri["polygon"].area})
        pieces.append(mp)
    X0 = np.vstack([G3a] + X_extra) if X_extra else G3a
    mesh = build_mesh(pieces, X0, outward_ref)
    diag["seams"] = find_seams(mesh)
    diag["free_segments"] = diag["seams"].pop("_free")
    return mesh, diag


def find_seams(mesh: ClothMesh) -> dict:
    from .results import seam_table
    return seam_table(mesh)
