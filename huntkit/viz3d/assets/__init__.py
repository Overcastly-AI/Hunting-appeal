"""huntkit.viz3d.assets - the modelling layer under the Cycles product renders (BL-018).

Pure numpy / trimesh / manifold3d geometry (no bpy), so the same meshes feed the GLB, the tests and Blender:

* ``hardware``  parametric buckles, ladder locks, tri-glides, cam buckles, G-hooks, D-rings, bag hook, zip sliders,
                cord locks. Real slots, bars and rounded edges; dimensions from ``data/materials/hardware`` where a
                record gives one, otherwise marked ASSUMPTION in ``hardware.SPECS``.
* ``webbing``   webbing with thickness and rounded selvedges, true-scale weave UVs, tails, keepers, wraps round bars.
* ``seams``     seam ridge + crease, stitch rows at the specified stitch length, bartacks, box-X, binding.
* ``zips``      coil chain, tape, slider, cord pull, stops.
* ``fabric``    fold-scale wrinkles from the drape's own strain field, seam pucker, strap pillowing, hems.

Conventions (same as the rest of viz3d): FCS mm, x lateral, y aft, z up. A *placement frame* is the 3x3 matrix
``frame(n, t)`` with columns (t, n x t, n): local +x along the strap / zip, +z out of the fabric surface.
Every builder returns ``trimesh.Trimesh`` with ``metadata["uv"]`` (one UV unit = ``TILE_MM`` = 500 mm on the part,
the convention ``export.py`` and the Cycles shaders use, so weave and ripstop pitches come out at true scale).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
TILE_MM = 500.0


def unit(v, axis=-1):
    v = np.asarray(v, float)
    return v / np.maximum(np.linalg.norm(v, axis=axis, keepdims=True), 1e-12)


def frame(n, t):
    """Rotation with columns (t, n x t, n): local x along the strap, z out of the surface."""
    n, t = unit(n), unit(t)
    t = unit(t - np.dot(t, n) * n)
    return np.column_stack([t, np.cross(n, t), n])


@lru_cache(maxsize=None)
def record(kind: str, rid: str) -> dict:
    """``properties`` of a material record, e.g. record("hardware", "ladder_lock_25mm_heavy")."""
    import yaml
    f = REPO / "data" / "materials" / kind / f"{rid}.yaml"
    return dict(yaml.safe_load(f.read_text()).get("properties", {}))


def mesh(V, F, uv=None):
    import trimesh
    m = trimesh.Trimesh(np.asarray(V, float), np.asarray(F, int), process=False)
    m.metadata["uv"] = np.zeros((len(m.vertices), 2)) if uv is None else np.asarray(uv, float)
    return m


def concat(meshes):
    """Join meshes (keeps UVs and the per-material ``extras`` side meshes, see ``with_extras``)."""
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    if not meshes:
        return mesh(np.zeros((0, 3)), np.zeros((0, 3), int))
    V, F, U, off, ex = [], [], [], 0, {}
    for m in meshes:
        V.append(m.vertices)
        F.append(m.faces + off)
        U.append(m.metadata.get("uv", np.zeros((len(m.vertices), 2))))
        off += len(m.vertices)
        for k, lst in m.metadata.get("extras", {}).items():
            ex.setdefault(k, []).extend(lst)
    out = mesh(np.vstack(V), np.vstack(F), np.vstack(U))
    if ex:
        out.metadata["extras"] = ex
    return out


def with_extras(m, **by_material):
    """Attach side meshes of other materials to ``m`` (e.g. the webbing wrapped through a buckle and its stitches).
    ``concat`` carries them along; ``studio`` turns them into sibling parts."""
    ex = m.metadata.setdefault("extras", {})
    for k, v in by_material.items():
        if v is None:
            continue
        for q in (v if isinstance(v, (list, tuple)) else [v]):
            if q is not None and len(q.faces):
                ex.setdefault(k, []).append(q)
    return m


def placed(m, R, p):
    """Copy of ``m`` rotated by R (3x3) and moved to p; extras move with it."""
    R, p = np.asarray(R, float), np.asarray(p, float)
    out = mesh(m.vertices @ R.T + p, m.faces, m.metadata.get("uv"))
    for k, lst in m.metadata.get("extras", {}).items():
        out.metadata.setdefault("extras", {})[k] = [placed(q, R, p) for q in lst]
    return out


def resample(P, step):
    P = np.asarray(P, float)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    if d[-1] < 1e-9:
        return P[:1].copy(), np.zeros(1)
    n = max(int(np.ceil(d[-1] / step)), 1) + 1
    s = np.linspace(0, d[-1], n)
    return np.stack([np.interp(s, d, P[:, k]) for k in range(3)], -1), s


def interp_rows(A, s_from, s_to):
    A = np.asarray(A, float)
    return np.stack([np.interp(s_to, s_from, A[:, k]) for k in range(A.shape[1])], -1)


def arclen(P):
    return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(np.asarray(P, float), axis=0), axis=1))])


def tangents(P):
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0) if len(P) > 2 else np.repeat(P[-1:] - P[:1], len(P), 0)
    return unit(T)


def sweep(P, N, prof, closed=False, caps=True, u_mm=None, v0=0.0):
    """Sweep a closed 2D profile ``prof`` (m, 2) = (across, out) along path P with surface normals N.
    UV: u = distance across the profile, v = distance along the path (both mm / TILE_MM)."""
    P, N = np.asarray(P, float), unit(N)
    T = tangents(P)
    if closed:
        T = unit(np.roll(P, -1, 0) - np.roll(P, 1, 0))
    N = unit(N - np.einsum("ij,ij->i", N, T)[:, None] * T)
    B = np.cross(N, T)
    n, m = len(P), len(prof)
    V = (P[:, None, :] + prof[None, :, 0, None] * B[:, None, :] + prof[None, :, 1, None] * N[:, None, :]).reshape(-1, 3)
    s = arclen(P) + v0
    pu = prof[:, 0] if u_mm is None else np.asarray(u_mm, float)
    uv = np.stack([np.broadcast_to(pu[None, :], (n, m)), np.broadcast_to(s[:, None], (n, m))], -1).reshape(-1, 2)
    F = []
    rows = n if closed else n - 1
    for i in range(rows):
        i2 = (i + 1) % n
        for j in range(m):
            j2 = (j + 1) % m
            a, b, c, d = i * m + j, i * m + j2, i2 * m + j2, i2 * m + j
            F += [[a, b, c], [a, c, d]]
    V, uv = list(V), list(uv)
    if caps and not closed:
        for i, flip in ((0, True), (n - 1, False)):
            V.append(P[i])
            uv.append([0.0, s[i]])
            c = len(V) - 1
            for j in range(m):
                j2 = (j + 1) % m
                F.append([c, i * m + j2, i * m + j] if flip else [c, i * m + j, i * m + j2])
    out = mesh(np.array(V), np.array(F), np.array(uv) / TILE_MM)
    if out.volume < 0:
        out.faces = out.faces[:, ::-1]
    return out


def circle_prof(r, n=10):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([r * np.cos(a), r * np.sin(a)])


def any_normal(P):
    """A usable normal field for a free 3D path (parallel-transported)."""
    P = np.asarray(P, float)
    T = tangents(P)
    n0 = np.cross(T[0], [0, 0, 1.0])
    if np.linalg.norm(n0) < 0.2:
        n0 = np.cross(T[0], [1.0, 0, 0])
    N = [unit(n0)]
    for i in range(1, len(P)):
        n = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(unit(n))
    return np.array(N)


def tube(P, r, n=10, closed=False, caps=True):
    P = np.asarray(P, float)
    if closed and np.linalg.norm(P[0] - P[-1]) < 1e-6:
        P = P[:-1]
    return sweep(P, any_normal(P), circle_prof(r, n), closed=closed, caps=caps)


def catmull(P, per=8, closed=False):
    P = np.asarray(P, float)
    if closed:
        Q = np.vstack([P[-1:], P, P[:2]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-1])
    return np.array(out)


def hash01(x):
    """Deterministic pseudo-random in [0, 1) from floats / ints (no global RNG state)."""
    x = np.sin(np.asarray(x, float) * 12.9898 + 78.233) * 43758.5453
    return x - np.floor(x)
