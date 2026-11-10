"""Seams and stitching as geometry (BL-018 task 3).

* ``stitch_row``  individual stitches (thread arcs that dive into the cloth) at the specified stitch length;
* ``seam``        a plain seam seen from the face side: the seam allowance pressed to one side and topstitched makes a
                  raised band (the ridge) next to the crease where the two panels meet, with stitch-pitch pucker;
* ``binding``     folded grosgrain binding over an edge, with its stitch row;
* ``bartack``, ``box_x``  load-point stitches.

Defaults: stitch length 3.0 mm (designs/pack_5200/BUILD_PLAN.md step 1: "stitch length 2.5-3.5 mm"; 3.0 is the middle
of that range, ASSUMPTION until the op sheet fixes SPI per seam), thread 0.36 mm (ASSUMPTION for bonded nylon Tex 70,
data/materials/thread/bonded_nylon_tex70.yaml gives no diameter; measure the cone), bartack 42 stitches over
2.5 mm (ASSUMPTION, common machine default).

The fabric itself is puckered and dipped along the same lines by ``fabric.displace`` (it takes the seam polylines).
"""
from __future__ import annotations

import numpy as np

from . import arclen, concat, hash01, interp_rows, mesh, resample, sweep, tangents, unit

STITCH_MM = 3.0
THREAD_D = 0.36
ALLOWANCE = 8.0


def _stitches(A, B, N, d=THREAD_D, arch=0.22, sink=0.12):
    """One thread segment per (A[i] -> B[i]) on a surface with normals N: a 4-sided tube through 4 stations, ends
    below the surface. Vectorised."""
    A, B, N = np.asarray(A, float), np.asarray(B, float), unit(np.asarray(N, float))
    k = len(A)
    if k == 0:
        return concat([])
    T = unit(B - A)
    S = np.cross(N, T)
    r = d / 2
    st = np.array([0.0, 0.16, 0.84, 1.0])
    hz = np.array([-sink - r, arch * d + r * 0.6, arch * d + r * 0.6, -sink - r])       # height of the centre
    ang = np.radians([45, 135, 225, 315])
    ring = np.stack([np.cos(ang), np.sin(ang)], -1) * r * 1.25
    C = A[:, None, :] + (B - A)[:, None, :] * st[None, :, None] + N[:, None, :] * hz[None, :, None]     # k,4,3
    V = C[:, :, None, :] + ring[None, None, :, 0, None] * S[:, None, None, :] + \
        ring[None, None, :, 1, None] * N[:, None, None, :]                                               # k,4,4,3
    V = V.reshape(k, 16, 3)
    f = []
    for i in range(3):
        for j in range(4):
            a, b, c, e = i * 4 + j, i * 4 + (j + 1) % 4, (i + 1) * 4 + (j + 1) % 4, (i + 1) * 4 + j
            f += [[a, b, c], [a, c, e]]
    f += [[0, 2, 1], [0, 3, 2], [12, 13, 14], [12, 14, 15]]
    f = np.array(f)
    F = (f[None, :, :] + (np.arange(k) * 16)[:, None, None]).reshape(-1, 3)
    return mesh(V.reshape(-1, 3), F)


def stitch_row(P, N, pitch=STITCH_MM, d=THREAD_D, lift=0.0, visible=0.80, jitter=0.04):
    """Lockstitch row along P (surface normals N). Each stitch shows ``visible`` of the pitch on the face."""
    P = np.asarray(P, float)
    s0 = arclen(P)
    if s0[-1] < pitch:
        return concat([])
    n = int(s0[-1] / pitch)
    s = (np.arange(n + 1) + 0.5 * (s0[-1] / pitch - n)) * pitch
    Q = interp_rows(P, s0, s)
    Nq = unit(interp_rows(np.asarray(N, float) if np.ndim(N) == 2 else np.tile(N, (len(P), 1)), s0, s))
    Tq = tangents(Q)
    Sq = np.cross(Nq, Tq)
    Q = Q + Sq * ((hash01(np.arange(n + 1) * 1.7 + P[0, 0]) - 0.5) * 2 * jitter * pitch)[:, None] + Nq * lift
    g = (1 - visible) / 2
    A = Q[:-1] + (Q[1:] - Q[:-1]) * g
    B = Q[:-1] + (Q[1:] - Q[:-1]) * (1 - g)
    return _stitches(A, B, 0.5 * (Nq[:-1] + Nq[1:]), d)


def offset_line(P, N, off):
    """Path shifted sideways on the surface by ``off`` mm (positive = towards N x T)."""
    P = np.asarray(P, float)
    return P + np.cross(unit(N), tangents(P)) * off


def seam(P, N, side=1.0, allowance=ALLOWANCE, pitch=STITCH_MM, rows=1, lift=0.25, ridge=0.75, topstitch=2.5,
         step=1.5, seed=0.0):
    """Plain seam, allowance pressed to ``side`` and topstitched ``topstitch`` mm from the seam line.

    Returns {"ridge": mesh in the panel's own fabric, "thread": mesh}. The ridge is a low rounded band ``allowance``
    wide and ``ridge`` mm proud (two extra layers of cloth under the face), dimpled at every stitch and gathered at
    the stitch pitch (pucker), so the seam line throws a real shadow."""
    P = np.asarray(P, float)
    s0 = arclen(P)
    if s0[-1] < 6.0:
        return {"ridge": concat([]), "thread": concat([])}
    Pr, s = resample(P, step)
    Nr = unit(interp_rows(np.asarray(N, float), s0, s))
    T = tangents(Pr)
    B = np.cross(Nr, T) * side
    us = np.array([-0.6, 0.0, 0.5, 1.4, topstitch, topstitch + 1.4, allowance - 1.2, allowance, allowance + 0.8])
    hs = np.array([-0.5, 0.05, 0.62, 0.95, 0.72, 1.0, 0.92, 0.5, -0.5]) * ridge
    # pucker: the allowance gathers between stitches, strongest at the topstitch line
    ph = 6.28 * hash01(seed + 3.1)
    wob = 1.0 + 0.35 * np.sin(s / (37.0 + 11 * hash01(seed)) + ph)
    puck = 0.5 + 0.5 * np.cos(2 * np.pi * s / pitch)
    wave = np.sin(2 * np.pi * s / (pitch * 3.7) + ph) * 0.5 + np.sin(2 * np.pi * s / (pitch * 9.3) + 2 * ph) * 0.5
    H = hs[None, :] * (1.0 + 0.16 * wave[:, None] * wob[:, None])
    dip = np.exp(-((us - topstitch) / 0.9) ** 2)[None, :] * (0.30 * ridge) * puck[:, None]
    H = H - dip
    n, m = len(Pr), len(us)
    top = Pr[:, None, :] + us[None, :, None] * B[:, None, :] + (H + lift)[:, :, None] * Nr[:, None, :]
    V = top.reshape(-1, 3)
    uv = np.stack([np.broadcast_to(us[None, :], (n, m)), np.broadcast_to(s[:, None], (n, m))], -1).reshape(-1, 2)
    F = []
    for i in range(n - 1):
        for j in range(m - 1):
            a, b, c, e = i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j
            F += [[a, b, c], [a, c, e]] if side > 0 else [[a, c, b], [a, e, c]]
    rid = mesh(V, np.array(F), uv / 500.0)
    thr = []
    for r in range(rows):
        off = topstitch + r * 6.0
        j = int(np.argmin(np.abs(us - off)))
        line = Pr + B * off + Nr * (lift + H[:, j][:, None] + 0.02)
        thr.append(stitch_row(line, Nr, pitch))
    return {"ridge": rid, "thread": concat(thr)}


def binding(P, N, width=10.0, thick=0.9, pitch=STITCH_MM, edge_out=None, step=2.0):
    """Folded binding tape over a free edge running along P. N = face normal of the cloth, ``edge_out`` = direction
    pointing out of the cloth across the edge (default N x T). Returns {"binding": mesh, "thread": mesh}."""
    P = np.asarray(P, float)
    s0 = arclen(P)
    Pr, s = resample(P, step)
    Nr = unit(interp_rows(np.asarray(N, float), s0, s))
    T = tangents(Pr)
    O = unit(interp_rows(np.asarray(edge_out, float), s0, s)) if edge_out is not None else np.cross(Nr, T)
    h = thick + 0.5
    pr = [[-width, h * 0.6], [-width * 0.5, h * 0.95], [-0.8, h], [0.5, h * 0.7], [0.9, 0.0], [0.5, -h * 0.7],
          [-0.8, -h], [-width * 0.5, -h * 0.95], [-width, -h * 0.6], [-width, -h * 0.6 + 0.01]]
    pr = np.array(pr)
    V = (Pr[:, None, :] + pr[None, :, 0, None] * O[:, None, :] + pr[None, :, 1, None] * Nr[:, None, :])
    n, m = V.shape[:2]
    uv = np.stack([np.broadcast_to(np.linspace(0, 2 * width, m)[None, :], (n, m)),
                   np.broadcast_to(s[:, None], (n, m))], -1).reshape(-1, 2)
    F = []
    for i in range(n - 1):
        for j in range(m - 1):
            a, b, c, e = i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j
            F += [[a, c, b], [a, e, c]]
    bm = mesh(V.reshape(-1, 3), np.array(F), uv / 500.0)
    thr = stitch_row(Pr - O * (width - 2.5) + Nr * (h * 0.72), Nr, pitch)
    return {"binding": bm, "thread": thr}


def bartack(p, n, across, width=20.0, length=2.5, count=42, d=THREAD_D):
    """Bartack centred on p: ``count`` zigzag stitches over ``width`` mm along ``across``, ``length`` mm deep."""
    p, n, a = np.asarray(p, float), unit(n), unit(across)
    a = unit(a - np.dot(a, n) * n)
    b = np.cross(n, a)
    u = np.linspace(-width / 2, width / 2, count + 1)
    sgn = np.where(np.arange(count + 1) % 2 == 0, -1.0, 1.0)
    Q = p + u[:, None] * a + (sgn * length / 2)[:, None] * b
    zig = _stitches(Q[:-1], Q[1:], np.tile(n, (count, 1)), d, arch=0.5, sink=0.05)
    under = _stitches(p - a * width / 2 + n * 0.02, p + a * width / 2 + n * 0.02, n[None, :], d * 2.4, arch=0.1,
                      sink=0.0) if False else None
    lay = np.linspace(-width / 2, width / 2, 9)
    core = _stitches(p + lay[:-1, None] * a, p + lay[1:, None] * a, np.tile(n, (8, 1)), d * 1.6, arch=0.2, sink=0.0)
    _ = under
    return concat([zig, core])


def box_x(p, n, t, L=25.0, W=19.0, pitch=2.6, d=THREAD_D):
    """Box-X: rectangle L (along t) x W with both diagonals, one continuous row."""
    p, n, t = np.asarray(p, float), unit(n), unit(t)
    t = unit(t - np.dot(t, n) * n)
    b = np.cross(n, t)
    c = [p + sx * L / 2 * t + sy * W / 2 * b for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    path = [c[0], c[1], c[2], c[3], c[0], c[2], c[3], c[1]]
    rows = []
    for a0, a1 in zip(path[:-1], path[1:]):
        k = max(int(np.linalg.norm(a1 - a0) / 1.0), 2)
        seg = a0 + (a1 - a0) * np.linspace(0, 1, k)[:, None]
        rows.append(stitch_row(seg, np.tile(n, (k, 1)), pitch, d, jitter=0.0))
    return concat(rows)


def shared_seams(V, F, piece):
    """Seam polylines of a drape mesh: every edge chain shared by two different pattern pieces.
    Returns [(pieceA, pieceB, vertex index chain)]."""
    from collections import defaultdict
    ef = defaultdict(set)
    for tix, tri in enumerate(np.asarray(F)):
        for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            ef[(min(u, v), max(u, v))].add(piece[tix])
    by = defaultdict(list)
    for e, ps in ef.items():
        if len(ps) == 2:
            by[tuple(sorted(ps))].append(e)
    out = []
    for (a, b), E in by.items():
        for ch in chains(E):
            out.append((a, b, ch))
    return out


def chains(E):
    """Chain undirected edges into polylines (broken at junctions)."""
    from collections import defaultdict
    adj = defaultdict(list)
    for u, v in E:
        adj[u].append(v)
        adj[v].append(u)
    seen, out = set(), []
    for u, v in E:
        k = (min(u, v), max(u, v))
        if k in seen:
            continue
        seen.add(k)
        ch = [u, v]
        for end in (0, 1):
            while True:
                tip = ch[-1] if end == 0 else ch[0]
                prev = ch[-2] if end == 0 else ch[1]
                if len(adj[tip]) != 2:
                    break
                nxt = [w for w in adj[tip] if w != prev and (min(tip, w), max(tip, w)) not in seen]
                if not nxt:
                    break
                w = nxt[0]
                seen.add((min(tip, w), max(tip, w)))
                ch.append(w) if end == 0 else ch.insert(0, w)
        out.append(ch)
    return out


def smooth_path(P, step=3.0, sigma=8.0):
    """Resample at ``step`` and Gaussian-smooth along the length (ends pinned)."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    Q, _ = resample(P, step)
    n = len(Q)
    h = max(1, int(round(sigma / step)))
    if n < 5:
        return Q
    k = np.exp(-0.5 * (np.arange(-3 * h, 3 * h + 1) / h) ** 2)
    k /= k.sum()
    pad = np.vstack([np.repeat(Q[:1], 3 * h, 0), Q, np.repeat(Q[-1:], 3 * h, 0)])
    S = np.stack([np.convolve(pad[:, i], k, "same")[3 * h:3 * h + n] for i in range(3)], -1)
    S[0], S[-1] = Q[0], Q[-1]
    return S
