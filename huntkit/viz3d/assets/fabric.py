"""Fabric realism on top of a cloth-sim drape (BL-018 task 5).

The huntkit cloth sim gives the *shape* on a 20-40 mm mesh; it cannot buckle below its element size, so the areas
where real cloth would wrinkle show up as in-plane compression in its strain field. ``displace`` turns that field
into geometry on a refined copy of the drape:

* fold-scale wrinkles where the minor principal stretch is below 1 (slack), ridges running across the compression
  direction, amplitude growing with the compression; taut panels (major stretch above 1) get almost none;
* the "hand" of woven nylon: a low, broad unevenness everywhere, because no sewn panel is CAD-flat;
* seams: the crease where two panels meet dips, and the cloth gathers at the stitch pitch either side (pucker);
* straps: the cloth is pressed in under the webbing, pillows up beside it and creases away from its edges;
* anything that sits on the cloth (patches, zips, hardware) flattens it locally, so nothing pokes through.

The displacement is along the surface normal and clamped to ``limit`` (default 5 mm, the BL-018 bound): the overall
shape stays the simulated one. ``solidify`` adds cloth thickness so free edges and hems show an edge.

All amplitudes are render parameters (ASSUMPTION: chosen to look like 330D pack cloth, not measured; a photo of the
first sewn prototype settles them).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from . import TILE_MM, arclen, hash01, mesh, resample, tangents, unit


@dataclass
class Look:
    """Amplitudes in mm (see module docstring)."""
    limit: float = 5.0            # hard clamp on |displacement|
    hand: float = 0.45            # broad unevenness everywhere
    hand_mm: float = 55.0         # its wavelength
    fold: float = 3.2             # wrinkle amplitude at full slack
    fold_mm: tuple = (26.0, 58.0)  # wrinkle wavelength range
    slack_gain: float = 12.0      # compression strain -> slack (1 at 8 % compression)
    slack: float | None = None    # override: constant slack 0..1 for parts without a pattern UV
    slack_dir: tuple | None = None  # with ``slack``: wrinkle ridges run ACROSS this 3D direction
    seam_dip: float = 1.1         # crease depth at a seam line
    seam_w: float = 4.5           # crease half-width
    pucker: float = 0.55          # stitch-pitch gathering amplitude
    pucker_mm: float = 11.0       # gathering wavelength (about 3.7 stitches)
    pucker_reach: float = 16.0    # e-folding distance from the seam
    strap_press: float = 0.9      # cloth pressed in under webbing
    strap_pillow: float = 2.2     # pillow height beside webbing
    strap_crease: float = 0.9     # creases running away from the strap edges
    flat_reach: float = 14.0      # distance over which things sitting on the cloth flatten it
    taut_fade: float = 0.6        # fraction of hand kept on taut cloth


def refine(m, levels=1, max_edge=None):
    """Midpoint-subdivide ``levels`` times (or until the longest edge is under ``max_edge`` mm), carrying UVs."""
    import trimesh
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces, int)
    uv = np.asarray(m.metadata.get("uv", np.zeros((len(V), 2))), float)
    k = 0
    while True:
        if max_edge is not None:
            e = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1)
            if np.median(e) <= max_edge or k >= 4:
                break
        elif k >= levels:
            break
        V, F, att = trimesh.remesh.subdivide(V, F, vertex_attributes={"uv": uv})
        uv = att["uv"]
        k += 1
    return mesh(V, F, uv)


def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    vn = np.zeros_like(V)
    for i in range(3):
        np.add.at(vn, F[:, i], fn)
    return unit(vn)


def smooth_scalar(F, x, n, it=3):
    """Laplacian smoothing of a per-vertex field (also works on (n, k) fields)."""
    x = np.asarray(x, float)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    deg = np.bincount(E.ravel(), minlength=n).astype(float)
    for _ in range(it):
        acc = np.zeros_like(x)
        np.add.at(acc, E[:, 0], x[E[:, 1]])
        np.add.at(acc, E[:, 1], x[E[:, 0]])
        x = 0.5 * x + 0.5 * acc / np.maximum(deg, 1)[(...,) + (None,) * (x.ndim - 1)]
    return x


def strain_field(V, F, uv_mm):
    """Per-vertex (slack compression e_c >= 0, 3D direction of that compression, major stretch) from the flat pattern
    coordinates ``uv_mm`` (mm) to the draped positions V. Triangles whose UVs are not a real flattening (seam
    triangles carrying the neighbour piece's UV) are ignored."""
    V, F, uv = np.asarray(V, float), np.asarray(F, int), np.asarray(uv_mm, float)
    e1u, e2u = uv[F[:, 1]] - uv[F[:, 0]], uv[F[:, 2]] - uv[F[:, 0]]
    e1, e2 = V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]
    det = e1u[:, 0] * e2u[:, 1] - e1u[:, 1] * e2u[:, 0]
    ok = np.abs(det) > 1e-6
    det = np.where(ok, det, 1.0)
    # deformation gradient G (3x2): G @ [e1u e2u] = [e1 e2]
    G = np.einsum("tik,tkj->tij", np.stack([e1, e2], -1), np.linalg.inv(np.where(ok[:, None, None], np.stack([e1u, e2u], -1),
                                                                             np.eye(2)[None])))
    C = np.einsum("tki,tkj->tij", G, G)
    w, U = np.linalg.eigh(C)
    lam_min, lam_max = np.sqrt(np.maximum(w[:, 0], 1e-9)), np.sqrt(np.maximum(w[:, 1], 1e-9))
    ok &= (lam_min > 0.6) & (lam_max < 1.4)
    d3 = unit(np.einsum("tij,tj->ti", G, U[:, :, 0]))
    comp = np.where(ok, np.clip(1.0 - lam_min, 0.0, 0.3), 0.0)
    stretch = np.where(ok, lam_max, 1.0)
    n = len(V)
    wsum = np.zeros(n)
    ec = np.zeros(n)
    st = np.zeros(n)
    D = np.zeros((n, 3, 3))
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1) * ok
    outer = d3[:, :, None] * d3[:, None, :]
    for i in range(3):
        np.add.at(wsum, F[:, i], area)
        np.add.at(ec, F[:, i], area * comp)
        np.add.at(st, F[:, i], area * stretch)
        np.add.at(D, F[:, i], (area * comp)[:, None, None] * outer)
    wsum = np.maximum(wsum, 1e-9)
    ec, st = ec / wsum, np.where(wsum > 1e-8, st / wsum, 1.0)
    ec = smooth_scalar(F, ec, n, 4)
    D = smooth_scalar(F, D, n, 4)
    _, vec = np.linalg.eigh(D + 1e-12 * np.eye(3)[None])
    return ec, vec[:, :, 2], st


_BANK = None


def _bank(k=48, seed=7):
    global _BANK
    if _BANK is None:
        rng = np.random.default_rng(seed)
        d = unit(rng.normal(size=(k, 3)))
        _BANK = (d, rng.uniform(0, 1, k), rng.uniform(0, 2 * np.pi, k))
    return _BANK


def _oriented_waves(X, dirs, lam_lo, lam_hi, sharp=6.0, chunk=20000):
    """Sum of plane waves whose wave vectors lie near ``dirs`` (per-vertex unit vectors): ridges across ``dirs``.
    Returns values in about [-1, 1], with rounded crests and tighter valleys (the look of buckled cloth)."""
    d, lu, ph = _bank()
    lam = lam_lo + (lam_hi - lam_lo) * lu
    out = np.zeros(len(X))
    for a in range(0, len(X), chunk):
        x, e = X[a:a + chunk], dirs[a:a + chunk]
        w = np.abs(e @ d.T) ** sharp                                  # (n, k) alignment weights
        w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
        c = np.cos(x @ (d * (2 * np.pi / lam)[:, None]).T + ph[None, :])
        h = (w * c).sum(1) / np.sqrt(np.maximum((w * w).sum(1), 1e-9)) * 0.75
        out[a:a + chunk] = h
    out = np.tanh(out * 1.0)
    return out - 0.12 * (1 - out * out)                                # sharper valleys, rounder crests


def _iso_noise(X, lam, seed=0):
    d, lu, ph = _bank()
    lamk = lam * (0.6 + 0.9 * lu)
    c = np.cos(X @ (d * (2 * np.pi / lamk)[:, None]).T + ph[None, :] + seed)
    return c.sum(1) / np.sqrt(len(d) / 2.0) * 0.6


def _polyline_field(X, P, step=2.0):
    """Distance d to polyline P, arclength s of the nearest point and its tangent, for every X."""
    Q, s = resample(P, step)
    tr = cKDTree(Q)
    d, j = tr.query(X)
    return d, s[j], tangents(Q)[j], Q[j]


def displacement(V, F, uv_mm=None, seams=(), straps=(), blockers=None, look: Look | None = None, seed=0.0):
    """Normal displacement h (mm, per vertex) and a report. ``seams`` = [polyline (n, 3)], ``straps`` = [(polyline,
    width mm)], ``blockers`` = (m, 3) points of everything that sits on this cloth."""
    L = look or Look()
    V, F = np.asarray(V, float), np.asarray(F, int)
    n = len(V)
    Nrm = vertex_normals(V, F)
    if L.slack is not None:
        ec = np.full(n, L.slack / L.slack_gain)
        if L.slack_dir is not None:
            dirs = np.tile(unit(np.asarray(L.slack_dir, float)), (n, 1))
        else:
            dirs = unit(np.cross(Nrm, [0.3, 0.2, 0.93]))
        stretch = np.ones(n)
    elif uv_mm is not None:
        ec, dirs, stretch = strain_field(V, F, uv_mm)
    else:
        ec, dirs, stretch = np.zeros(n), unit(np.cross(Nrm, [0, 0, 1.0])), np.ones(n)
    slack = np.clip(ec * L.slack_gain, 0.0, 1.0)
    taut = np.clip((stretch - 1.004) / 0.02, 0.0, 1.0) * (1 - slack)
    h_fold = L.fold * slack ** 0.8 * _oriented_waves(V, dirs, *L.fold_mm)
    h_hand = L.hand * (1 - (1 - L.taut_fade) * taut) * _iso_noise(V, L.hand_mm, seed)
    h = h_fold + h_hand
    rep = {"slack_mean": float(slack.mean()), "taut_mean": float(taut.mean()), "fold_max": float(np.abs(h_fold).max())}
    # seams
    damp = np.ones(n)
    hs = np.zeros(n)
    for k, P in enumerate(seams):
        if len(P) < 2:
            continue
        d, s, _, _ = _polyline_field(V, P)
        near = d < 4 * L.pucker_reach
        if not near.any():
            continue
        dd, ss = d[near], s[near]
        ph = 6.28 * float(hash01(k * 3.3 + seed))
        lam = L.pucker_mm * (1.0 + 0.22 * np.sin(ss / 61.0 + ph))
        puck = L.pucker * np.exp(-dd / L.pucker_reach) * (1 - np.exp(-(dd / 2.5) ** 2)) * \
            np.sin(2 * np.pi * ss / lam + ph) * (0.75 + 0.25 * np.sin(ss / 23.0 + 2 * ph))
        dip = -L.seam_dip * np.exp(-(dd / L.seam_w) ** 2)
        hs[near] += puck + dip
        damp[near] = np.minimum(damp[near], 1 - 0.85 * np.exp(-(dd / (2.0 * L.seam_w)) ** 2))
    h = h * damp + hs
    # straps
    for k, (P, width) in enumerate(straps):
        if len(P) < 2:
            continue
        d, s, _, Q = _polyline_field(V, P)
        reach = width / 2 + 45.0
        near = d < reach
        if not near.any():
            continue
        # only cloth that the strap actually lies on (not the far side of the bag)
        near &= np.abs(np.einsum("ij,ij->i", V - Q, Nrm)) < 12.0
        dd, ss = d[near], s[near]
        e = np.clip(dd - width / 2, 0.0, None)
        under = dd <= width / 2
        t = e / 9.0
        pillow = L.strap_pillow * t * np.exp(1 - t)
        ph = 6.28 * float(hash01(k * 1.9 + seed + 0.5))
        crease = L.strap_crease * np.exp(-e / 22.0) * (1 - np.exp(-(e / 3.0) ** 2)) * np.sin(2 * np.pi * ss / 17.0 + ph)
        hk = np.where(under, -L.strap_press, pillow + crease)
        keep = np.where(under, 0.0, 1 - np.exp(-(e / 10.0) ** 2))
        h[near] = h[near] * keep + hk
    # blockers: clamp outward displacement near things that sit on the cloth
    if blockers is not None and len(blockers):
        tr = cKDTree(blockers)
        d, j = tr.query(V, distance_upper_bound=L.flat_reach * 2.5)
        out_side = np.zeros(n, bool)
        ok = np.isfinite(d)
        out_side[ok] = np.einsum("ij,ij->i", blockers[j[ok]] - V[ok], Nrm[ok]) > -0.5
        f = np.where(ok & out_side, np.clip((d - 3.0) / L.flat_reach, 0.0, 1.0), 1.0)
        f = smooth_scalar(F, f, n, 4)                 # no patchy mask from the thinned blocker cloud
        f = f * f * (3 - 2 * f)
        h = np.where(h > 0, h * f, h * (0.35 + 0.65 * f))
        rep["blocked_frac"] = float((f < 0.99).mean())
    h = 0.6 * h + 0.4 * smooth_scalar(F, h, n, 1)
    h = np.clip(h, -L.limit, L.limit)
    rep.update(max_abs_mm=float(np.abs(h).max()), rms_mm=float(np.sqrt((h * h).mean())), limit_mm=L.limit)
    return h, Nrm, rep


def displace(m, uv_scale=TILE_MM, **kw):
    """``displacement`` applied to a mesh (UV in TILE units -> mm via ``uv_scale``; pass ``uv_mm=None`` in ``kw`` to
    ignore the UVs). Returns (new mesh, report)."""
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces, int)
    uv = np.asarray(m.metadata.get("uv", np.zeros((len(V), 2))), float)
    if "uv_mm" not in kw:
        kw["uv_mm"] = uv * uv_scale
    h, Nrm, rep = displacement(V, F, **kw)
    out = mesh(V + Nrm * h[:, None], F, uv)
    return out, rep


def solidify(m, thick=0.6):
    """Give an open cloth mesh thickness (inward), closing the rim: free edges and hems then show an edge.
    Closed meshes are returned unchanged."""
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces, int)
    uv = np.asarray(m.metadata.get("uv", np.zeros((len(V), 2))), float)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(E, 1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    b = E[cnt[inv.ravel()] == 1]
    if len(b) == 0:
        return m
    Nrm = vertex_normals(V, F)
    n = len(V)
    V2 = np.vstack([V, V - Nrm * thick])
    F2 = [F, F[:, ::-1] + n]
    rim = np.concatenate([np.stack([b[:, 1], b[:, 0], b[:, 0] + n], -1), np.stack([b[:, 1], b[:, 0] + n, b[:, 1] + n], -1)])
    F2.append(rim)
    return mesh(V2, np.vstack(F2), np.vstack([uv, uv]))


def offset_copy(m, d):
    """Copy of a cloth mesh moved d mm along its normals (d < 0 = inside) with the faces turned over: a lining that
    follows every wrinkle of the face cloth and so cannot cut through it."""
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces, int)
    return mesh(V + vertex_normals(V, F) * d, F[:, ::-1], m.metadata.get("uv"))


def deviation(V_ref, V_new):
    """Max and RMS distance (mm) from the displaced vertices to the reference drape vertices."""
    d, _ = cKDTree(V_ref).query(V_new)
    return float(d.max()), float(np.sqrt((d * d).mean()))


__all__ = ["Look", "refine", "displace", "displacement", "strain_field", "solidify", "deviation"]
_ = (field, arclen)
