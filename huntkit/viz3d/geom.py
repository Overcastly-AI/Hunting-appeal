"""Mesh primitives for the 3D pack model (numpy + trimesh).

All geometry is built in the huntkit.fea frame convention: millimetres, x lateral (+ wearer's
right), y fore-aft (+ AFT, toward the bag; the wearer stands at -y), z up, z = 0 at the stay feet.
Conversion to glTF (metres, +Y up) happens once, at export (see export.py).

Every builder returns a ``trimesh.Trimesh`` carrying per-vertex UVs in *texture tiles*
(``uv = mm / tile_mm``) in ``mesh.metadata['uv']``; export.py attaches the material.
Seams duplicate vertices (for UV wrap), so use :func:`is_closed` to test watertightness.
"""
from __future__ import annotations

import numpy as np
import trimesh

TILE_MM = 500.0          # fabric/camo texture tile (one texture repeat = 500 mm on the fabric)


# ----------------------------------------------------------------------------- helpers
def _unit(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.where(n < 1e-12, 1.0, n)


def _mesh(V, F, uv, flip_if_negative=True) -> trimesh.Trimesh:
    m = trimesh.Trimesh(vertices=np.asarray(V, float), faces=np.asarray(F, np.int64), process=False)
    m.metadata["uv"] = np.asarray(uv, float)
    if flip_if_negative and _signed_volume(m) < 0:
        m.faces = m.faces[:, ::-1]
    return m


def _signed_volume(m: trimesh.Trimesh) -> float:
    v = m.vertices[m.faces]
    return float(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6.0)


def volume_mm3(m: trimesh.Trimesh) -> float:
    """Enclosed volume (divergence theorem over the triangles; seam duplicates don't matter)."""
    return abs(_signed_volume(m))


def is_closed(m: trimesh.Trimesh) -> bool:
    """Watertight test on the pure geometry (UV-seam duplicate vertices merged)."""
    g = trimesh.Trimesh(vertices=m.vertices.copy(), faces=m.faces.copy(), process=False)
    g.merge_vertices(merge_tex=True, merge_norm=True, digits_vertex=6)
    g.remove_unreferenced_vertices()
    # drop degenerate triangles made by poles
    g.update_faces(g.nondegenerate_faces())
    return bool(g.is_watertight)


def concat(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    V, F, U, off = [], [], [], 0
    for m in meshes:
        V.append(m.vertices)
        F.append(m.faces + off)
        U.append(m.metadata.get("uv", np.zeros((len(m.vertices), 2))))
        off += len(m.vertices)
    out = trimesh.Trimesh(vertices=np.vstack(V), faces=np.vstack(F), process=False)
    out.metadata["uv"] = np.vstack(U)
    return out


def grid_mesh(V, uv=None, pole_start=None, pole_end=None, close_u=True, cap_start=False,
              cap_end=False) -> trimesh.Trimesh:
    """Mesh from a vertex grid ``V`` (K rings x M points, rings closed if ``close_u``).

    The ring wrap is done with a duplicate column (UV seam). Ends are closed by fanning to a
    pole point (``pole_start``/``pole_end``) or, with ``cap_*``, to the ring centroid.
    """
    V = np.asarray(V, float)
    K, M, _ = V.shape
    if uv is None:
        uv = _arc_uv(V, close_u)
    if close_u:
        V = np.concatenate([V, V[:, :1]], axis=1)
        if uv.shape[1] == M:
            uv = np.concatenate([uv, uv[:, -1:] + (uv[:, -1:] - uv[:, -2:-1])], axis=1)
    Mc = V.shape[1]
    verts = V.reshape(-1, 3)
    uvs = uv.reshape(-1, 2)
    idx = np.arange(K * Mc).reshape(K, Mc)
    a, b = idx[:-1, :-1], idx[:-1, 1:]
    c, d = idx[1:, 1:], idx[1:, :-1]
    F = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    extra_v, extra_uv, extra_f = [], [], []
    n = len(verts)
    for ring, pole, cap, rev in ((0, pole_start, cap_start, True), (K - 1, pole_end, cap_end, False)):
        if pole is None and not cap:
            continue
        p = np.asarray(pole, float) if pole is not None else V[ring, :-1].mean(axis=0)
        extra_v.append(p)
        extra_uv.append(uvs[idx[ring]].mean(axis=0))
        pi = n + len(extra_v) - 1
        r = idx[ring]
        tri = np.stack([np.full(Mc - 1, pi), r[1:], r[:-1]], -1) if rev else \
            np.stack([np.full(Mc - 1, pi), r[:-1], r[1:]], -1)
        extra_f.append(tri)
    if extra_v:
        verts = np.vstack([verts, np.array(extra_v)])
        uvs = np.vstack([uvs, np.array(extra_uv)])
        F = np.vstack([F] + extra_f)
    return _mesh(verts, F, uvs)


def _arc_uv(V, close_u, tile=TILE_MM):
    """UVs from arc length: u around the ring, v along the rings (mm / tile)."""
    K, M, _ = V.shape
    Vc = np.concatenate([V, V[:, :1]], axis=1) if close_u else V
    du = np.linalg.norm(np.diff(Vc, axis=1), axis=2)
    u = np.concatenate([np.zeros((K, 1)), np.cumsum(du, axis=1)], axis=1)
    mid = M // 4
    dv = np.linalg.norm(np.diff(V[:, mid], axis=0), axis=1)
    v = np.concatenate([[0.0], np.cumsum(dv)])
    U = u / tile
    Vv = np.repeat(v[:, None] / tile, U.shape[1], axis=1)
    uv = np.stack([U, Vv], -1)
    return uv if close_u else uv


# ----------------------------------------------------------------------------- curves
def catmull_rom(P, samples_per_seg=8, closed=False):
    """Centripetal Catmull-Rom through the points ``P`` (passes through every point)."""
    P = np.asarray(P, float)
    if len(P) < 3:
        t = np.linspace(0, 1, samples_per_seg * max(len(P) - 1, 1) + 1)[:, None]
        return P[0] * (1 - t) + P[-1] * t
    if closed:
        Q = np.vstack([P[-1], P, P[0], P[1]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** 0.5
        ts = np.linspace(t1, t2, samples_per_seg, endpoint=False)[:, None]
        A1 = (t1 - ts) / (t1 - t0) * p0 + (ts - t0) / (t1 - t0) * p1
        A2 = (t2 - ts) / (t2 - t1) * p1 + (ts - t1) / (t2 - t1) * p2
        A3 = (t3 - ts) / (t3 - t2) * p2 + (ts - t2) / (t3 - t2) * p3
        B1 = (t2 - ts) / (t2 - t0) * A1 + (ts - t0) / (t2 - t0) * A2
        B2 = (t3 - ts) / (t3 - t1) * A2 + (ts - t1) / (t3 - t1) * A3
        out.append((t2 - ts) / (t2 - t1) * B1 + (ts - t1) / (t2 - t1) * B2)
    out.append(P[-1:] if not closed else P[:1])
    return np.vstack(out)


def resample(P, step):
    P = np.asarray(P, float)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    n = max(int(np.ceil(d[-1] / step)), 1) + 1
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, P[:, k]) for k in range(3)], -1)


def frames_along(P, up=None):
    """Tangent, side, normal frames along a polyline. ``up``: (3,) or (N,3) reference normals
    (the profile's +y axis is aligned with them); otherwise parallel transport."""
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0)
    T = _unit(T)
    N = len(P)
    if up is not None:
        U = np.broadcast_to(np.asarray(up, float), (N, 3))
        S = _unit(np.cross(U, T))
        Nn = _unit(np.cross(T, S))
        return T, S, Nn
    ref = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    S = np.zeros_like(P)
    Nn = np.zeros_like(P)
    s0 = _unit(np.cross(ref, T[0]))
    S[0] = s0
    Nn[0] = np.cross(T[0], s0)
    for i in range(1, N):
        b = np.cross(T[i - 1], T[i])
        bn = np.linalg.norm(b)
        s = S[i - 1]
        if bn > 1e-9:
            b /= bn
            ang = np.arccos(np.clip(np.dot(T[i - 1], T[i]), -1, 1))
            s = (s * np.cos(ang) + np.cross(b, s) * np.sin(ang) + b * np.dot(b, s) * (1 - np.cos(ang)))
        s = _unit(s - T[i] * np.dot(s, T[i]))
        S[i] = s
        Nn[i] = np.cross(T[i], s)
    return T, S, Nn


# ----------------------------------------------------------------------------- profiles
def circle(r, n=24):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.stack([r * np.cos(a), r * np.sin(a)], -1)


def rounded_rect(w, h, nexp=4.0, n=40):
    """Closed rounded-rectangle profile (superellipse, exponent ``nexp``), w along x, h along y."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(a), np.sin(a)
    x = w / 2 * np.sign(c) * np.abs(c) ** (2 / nexp)
    y = h / 2 * np.sign(s) * np.abs(s) ** (2 / nexp)
    return np.stack([x, y], -1)


def sweep(path, profile, up=None, scale=None, offset=None, caps=True, tile=TILE_MM,
          smooth=False, step=None) -> trimesh.Trimesh:
    """Sweep a closed 2D ``profile`` (M,2) - or per-point profiles (N,M,2) - along ``path``.

    ``scale``: (N,2) per-point x/y scale; ``offset``: (N,2) per-point profile offset; ``up``:
    reference normals for the profile y axis (e.g. surface normals for straps).
    """
    P = np.asarray(path, float)
    if smooth:
        P = catmull_rom(P, 10)
    if step:
        P = resample(P, step)
    N = len(P)
    T, S, Nn = frames_along(P, None if up is None else (np.asarray(up, float) if np.ndim(up) == 1 else
                                                         _interp_rows(np.asarray(up, float), N)))
    prof = np.asarray(profile, float)
    if prof.ndim == 2:
        prof = np.broadcast_to(prof, (N,) + prof.shape).copy()
    if scale is not None:
        prof = prof * _interp_rows(np.asarray(scale, float), N)[:, None, :]
    if offset is not None:
        prof = prof + _interp_rows(np.asarray(offset, float), N)[:, None, :]
    V = P[:, None, :] + prof[..., :1] * S[:, None, :] + prof[..., 1:2] * Nn[:, None, :]
    # uv: u = profile arc length, v = path length
    pc = np.concatenate([prof, prof[:, :1]], axis=1)
    u = np.concatenate([np.zeros((N, 1)), np.cumsum(np.linalg.norm(np.diff(pc, axis=1), axis=2), axis=1)], 1)
    v = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    uv = np.stack([u / tile, np.repeat(v[:, None], u.shape[1], 1) / tile], -1)
    return grid_mesh(V, uv=uv, cap_start=caps, cap_end=caps)


def _interp_rows(A, N):
    A = np.asarray(A, float)
    if len(A) == N:
        return A
    s = np.linspace(0, 1, len(A))
    t = np.linspace(0, 1, N)
    return np.stack([np.interp(t, s, A[:, k]) for k in range(A.shape[1])], -1)


def tube(path, r, n=24, tile=40.0, smooth=False, step=None, caps=True):
    return sweep(path, circle(r, n), tile=tile, smooth=smooth, step=step, caps=caps)


def ribbon(path, width, thick, normals, tile=TILE_MM, step=6.0, caps=True):
    """Flat strap/webbing lying on a surface: the strap face is perpendicular to ``normals``."""
    P = np.asarray(path, float)
    Nrm = _interp_rows(np.asarray(normals, float), len(P)) if np.ndim(normals) == 2 else normals
    if step:
        d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        n = max(int(np.ceil(d[-1] / step)), 1) + 1
        s = np.linspace(0, d[-1], n)
        P2 = np.stack([np.interp(s, d, P[:, k]) for k in range(3)], -1)
        if np.ndim(Nrm) == 2:
            Nrm = _unit(np.stack([np.interp(s, d, Nrm[:, k]) for k in range(3)], -1))
        P = P2
    prof = rounded_rect(width, thick, nexp=6.0, n=28)
    return sweep(P, prof, up=Nrm, tile=tile, caps=caps)


# ----------------------------------------------------------------------------- solids
def superellipse_ring(a, b, n_front, n_back=None, M=64, cx=0.0, cy=0.0, z=0.0, n_side=None):
    """Closed ring at height z: half-widths a (x), b (y); exponent n_front for +y half,
    n_back for the -y half (flatter back)."""
    th = np.linspace(0, 2 * np.pi, M, endpoint=False)
    c, s = np.cos(th), np.sin(th)
    nb = n_back or n_front
    nexp = np.where(s >= 0, n_front, nb)
    x = cx + a * np.sign(c) * np.abs(c) ** (2 / nexp)
    y = cy + b * np.sign(s) * np.abs(s) ** (2 / nexp)
    return np.stack([x, y, np.full_like(x, z)], -1)


def loft(rings, pole_start=None, pole_end=None, cap_start=False, cap_end=False, tile=TILE_MM):
    V = np.asarray(rings, float)
    return grid_mesh(V, uv=_arc_uv(V, True, tile), pole_start=pole_start, pole_end=pole_end,
                     cap_start=cap_start, cap_end=cap_end)


def superellipsoid(center, radii, e_ns=0.4, e_ew=0.4, nu=48, nv=24, R=None, tile=TILE_MM):
    """Superellipsoid (rounded box/pillow). e -> 0 boxy, 1 ellipsoid. Optional 3x3 rotation R."""
    a, b, c = radii
    eta = np.linspace(-np.pi / 2, np.pi / 2, nv)
    om = np.linspace(-np.pi, np.pi, nu, endpoint=False)
    E, O = np.meshgrid(eta, om, indexing="ij")

    def f(w, m):
        return np.sign(np.cos(w)) * np.abs(np.cos(w)) ** m, np.sign(np.sin(w)) * np.abs(np.sin(w)) ** m
    ce, se = f(E, e_ns)
    co, so = f(O, e_ew)
    X = a * ce * co
    Y = b * ce * so
    Z = c * se
    V = np.stack([X, Y, Z], -1)[1:-1]
    if R is not None:
        V = V @ np.asarray(R).T
    V = V + np.asarray(center, float)
    ps = np.asarray(center, float) + (np.array([0, 0, -c]) @ (np.asarray(R).T if R is not None else np.eye(3)))
    pe = np.asarray(center, float) + (np.array([0, 0, c]) @ (np.asarray(R).T if R is not None else np.eye(3)))
    return grid_mesh(V, uv=_arc_uv(V, True, tile), pole_start=ps, pole_end=pe)


def capsule_between(p0, p1, r0, r1=None, n=32, tile=TILE_MM):
    """Tapered capsule from p0 (radius r0) to p1 (radius r1) with hemispherical ends."""
    r1 = r0 if r1 is None else r1
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = _unit(p1 - p0)
    ref = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 1.0, 0])
    s = _unit(np.cross(ax, ref))
    t = np.cross(ax, s)
    rings, k = [], 8
    for i in range(k):  # bottom hemisphere
        phi = -np.pi / 2 + np.pi / 2 * (i + 1) / (k + 1)
        rings.append((p0 + ax * r0 * np.sin(phi), r0 * np.cos(phi)))
    for i in range(6):
        w = i / 5
        rings.append((p0 * (1 - w) + p1 * w, r0 * (1 - w) + r1 * w))
    for i in range(k):
        phi = np.pi / 2 * (i + 1) / (k + 1)
        rings.append((p1 + ax * r1 * np.sin(phi), r1 * np.cos(phi)))
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.array([[c + r * (np.cos(aa) * s + np.sin(aa) * t) for aa in a] for c, r in rings])
    return grid_mesh(V, uv=_arc_uv(V, True, tile), pole_start=p0 - ax * r0, pole_end=p1 + ax * r1)


def plate(poly2d, origin, ex, ey, thick, tile=40.0):
    """Extrude a shapely polygon (local 2D coords, mm) into a plate; local x->ex, y->ey,
    thickness along ex x ey, centred on the plane through ``origin``."""
    m = trimesh.creation.extrude_polygon(poly2d, thick)
    v = m.vertices.copy()
    ex, ey = _unit(np.asarray(ex, float)), _unit(np.asarray(ey, float))
    ez = _unit(np.cross(ex, ey))
    uv = np.stack([v[:, 0] / tile, v[:, 1] / tile], -1)
    v[:, 2] -= thick / 2
    W = np.asarray(origin, float) + v[:, :1] * ex + v[:, 1:2] * ey + v[:, 2:3] * ez
    return _mesh(W, m.faces, uv)


def patch_shell(surf, nrm, u_rng, v_rng, thick, inset=3.0, nu=40, nv=40, tile=TILE_MM):
    """Pillow-shaped closed shell conforming to a surface.

    ``surf(u, v) -> (...,3)`` points and ``nrm(u, v) -> (...,3)`` outward unit normals on a
    parameter rectangle; ``thick(s, t)`` gives the outward thickness for s, t in [0, 1].
    The inner face sits ``inset`` mm inside the surface so the pocket visibly attaches.
    """
    s = np.linspace(0, 1, nu)
    t = np.linspace(0, 1, nv)
    S, Tt = np.meshgrid(s, t, indexing="ij")
    U = u_rng[0] + (u_rng[1] - u_rng[0]) * S
    Vv = v_rng[0] + (v_rng[1] - v_rng[0]) * Tt
    P = surf(U, Vv)
    Nn = nrm(U, Vv)
    th = thick(S, Tt)
    outer = P + Nn * th[..., None]
    inner = P - Nn * inset
    nO = nu * nv
    verts = np.vstack([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    idx = np.arange(nO).reshape(nu, nv)
    a, b, c, d = idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]
    Fo = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    Fi = Fo[:, ::-1] + nO
    loop = ([(i, 0) for i in range(nu)] + [(nu - 1, j) for j in range(1, nv)] +
            [(i, nv - 1) for i in range(nu - 2, -1, -1)] + [(0, j) for j in range(nv - 2, 0, -1)])
    L = np.array([idx[i, j] for i, j in loop])
    L2 = np.roll(L, -1)
    Fs = np.concatenate([np.stack([L, L + nO, L2 + nO], -1), np.stack([L, L2 + nO, L2], -1)])
    F = np.vstack([Fo, Fi, Fs])
    # uv from arc length on the outer face
    du = np.linalg.norm(np.diff(outer, axis=0), axis=2)
    dv = np.linalg.norm(np.diff(outer, axis=1), axis=2)
    uu = np.concatenate([np.zeros((1, nv)), np.cumsum(du, axis=0)], 0)
    vv = np.concatenate([np.zeros((nu, 1)), np.cumsum(dv, axis=1)], 1)
    uv = np.stack([uu, vv], -1).reshape(-1, 2) / tile
    m = trimesh.Trimesh(vertices=verts, faces=F, process=False)
    # make winding consistent and outward
    trimesh.repair.fix_winding(m)
    if _signed_volume(m) < 0:
        m.faces = m.faces[:, ::-1]
    m.metadata["uv"] = np.vstack([uv, uv])
    return m


def bump(s, power=0.5):
    """Smooth 0..1..0 bump on [0, 1]."""
    return np.clip(np.sin(np.pi * np.clip(s, 0, 1)), 0, 1) ** power


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])
