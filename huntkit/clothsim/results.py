"""Post-processing: seams, seam line forces, strains and tensions, volumes."""
from __future__ import annotations

import numpy as np

from .mesh import ClothMesh


# ----------------------------------------------------------------------------- seams
def seam_table(mesh: ClothMesh) -> dict:
    """Boundary segments shared by two pieces (or two edges of one piece) = seam segments.

    Returns {name: {"pieces": (A, B), "edges": (ea, eb), "segments": [(u, v)], "sideA": {gid: local},
    "sideB": {gid: local}}} and "_free": [(u, v, piece, edge)] for unshared boundary segments."""
    owner: dict = {}
    for pi, p in enumerate(mesh.pieces):
        for u, v, e, iu, iv in p.loop:
            if u == v:
                continue
            owner.setdefault((min(u, v), max(u, v)), []).append((p.name, e, pi, {u: iu, v: iv}))
    seams: dict = {}
    free = []
    for key, lst in owner.items():
        if len(lst) == 1:
            free.append((*key, lst[0][0], lst[0][1]))
            continue
        a, b = sorted(lst[:2], key=lambda t: (t[0], t[1]))
        nm = f"{a[0]}.{a[1]} | {b[0]}.{b[1]}"
        s = seams.setdefault(nm, {"pieces": (a[0], b[0]), "edges": (a[1], b[1]), "pi": (a[2], b[2]),
                                  "segments": [], "sideA": {}, "sideB": {}})
        s["segments"].append(key)
        s["sideA"].update(a[3])
        s["sideB"].update(b[3])
    seams["_free"] = free
    return seams


def chain_order(segments) -> list:
    """Order seam segments into a node chain (open or closed)."""
    adj: dict = {}
    for u, v in segments:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    ends = [k for k, v in adj.items() if len(v) == 1]
    start = ends[0] if ends else next(iter(adj))
    out, prev, cur = [start], None, start
    while True:
        nb = [w for w in adj[cur] if w != prev]
        if not nb or (nb[0] == start):
            break
        prev, cur = cur, nb[0]
        if cur in out:
            break
        out.append(cur)
    return out


def local_forces(mesh: ClothMesh, tri_force: np.ndarray) -> list:
    """Per piece, the membrane force on each LOCAL point (welded copies kept apart)."""
    out = []
    for pi, p in enumerate(mesh.pieces):
        sel = np.where(mesh.tri_piece == pi)[0]
        f = np.zeros((len(p.xy), 3))
        for d in range(3):
            f[:, d] = np.bincount(p.tris.ravel(), tri_force[sel].reshape(-1, 3)[:, d], minlength=len(p.xy))
        out.append(f)
    return out


def seam_forces(mesh: ClothMesh, x: np.ndarray, membrane, seams: dict, exclude=()) -> dict:
    """Line force each seam carries, N/mm, at every seam node.

    The force panel A exerts on a welded node (sum of A's triangle forces at A's copy of the node)
    is what the stitches pass to panel B. ``line`` = component perpendicular to the seam tangent,
    averaged over the two sides, / tributary seam length; ``shear`` = along-seam component.
    Seam ends, junctions of 3+ pieces and attachment nodes (``exclude``) are flagged, not counted
    in max / p95."""
    lf = local_forces(mesh, membrane.tri_forces(x))
    count: dict = {}
    for pi, p in enumerate(mesh.pieces):
        for g in set(u for u, *_ in p.loop):
            count[g] = count.get(g, 0) + 1
    ex = set(int(e) for e in exclude)
    out = {}
    for nm, s in seams.items():
        if nm.startswith("_"):
            continue
        adj: dict = {}
        for u, v in s["segments"]:
            adj.setdefault(u, []).append(v)
            adj.setdefault(v, []).append(u)
        rows = []
        pa, pb = s["pi"]
        for nd, nbs in adj.items():
            xs = x[nd]
            trib = 0.5 * sum(np.linalg.norm(x[w] - xs) for w in nbs)
            if len(nbs) >= 2:
                t = x[nbs[1]] - x[nbs[0]]
            else:
                t = x[nbs[0]] - xs
            t = t / max(np.linalg.norm(t), 1e-12)
            fa = lf[pa][s["sideA"][nd]]
            fb = lf[pb][s["sideB"][nd]]
            perp = 0.5 * (np.linalg.norm(fa - fa.dot(t) * t) + np.linalg.norm(fb - fb.dot(t) * t))
            shr = 0.5 * (abs(fa.dot(t)) + abs(fb.dot(t)))
            flag = "end" if len(nbs) == 1 else ("junction" if count.get(nd, 0) > 2 else
                                                ("attachment" if nd in ex else ""))
            rows.append((nd, perp / max(trib, 1e-9), shr / max(trib, 1e-9), trib, flag))
        nodes = np.array([r[0] for r in rows])
        line = np.array([r[1] for r in rows])
        shear = np.array([r[2] for r in rows])
        trib = np.array([r[3] for r in rows])
        flags = [r[4] for r in rows]
        ok = np.array([f == "" for f in flags])
        use = line[ok] if ok.any() else line
        imax = int(np.argmax(np.where(ok, line, -1))) if ok.any() else int(np.argmax(line))
        out[nm] = {"pieces": s["pieces"], "edges": s["edges"], "nodes": nodes, "line_n_mm": line,
                   "shear_n_mm": shear, "trib_mm": trib, "flags": flags, "length_mm": float(trib.sum()),
                   "max_n_mm": float(use.max()), "p95_n_mm": float(np.percentile(use, 95)),
                   "mean_n_mm": float(np.average(use, weights=trib[ok] if ok.any() else trib)),
                   "max_at": x[nodes[imax]].tolist(),
                   "max_incl_flagged_n_mm": float(line.max())}
    return out


# ----------------------------------------------------------------------------- strains, tensions
def tri_measures(mesh: ClothMesh, membrane, x: np.ndarray) -> dict:
    F, E, S, _, _ = membrane.stress(x)
    C = np.einsum("tda,tdb->tab", F, F)
    tr = C[:, 0, 0] + C[:, 1, 1]
    det = C[:, 0, 0] * C[:, 1, 1] - C[:, 0, 1] ** 2
    disc = np.sqrt(np.maximum(tr ** 2 / 4 - det, 0))
    l1, l2 = tr / 2 + disc, tr / 2 - disc
    emax, emin = np.sqrt(np.maximum(l1, 0)) - 1, np.sqrt(np.maximum(l2, 0)) - 1
    J = np.sqrt(np.maximum(det, 1e-12))
    M = np.einsum("tab,tbc->tac", S, C) / J[:, None, None]      # same eigenvalues as Cauchy F S F^T / J
    trm = M[:, 0, 0] + M[:, 1, 1]
    dm = M[:, 0, 0] * M[:, 1, 1] - M[:, 0, 1] * M[:, 1, 0]
    dd = np.sqrt(np.maximum(trm ** 2 / 4 - dm, 0))
    a, b, c = (x[mesh.tris[:, j]] for j in range(3))
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    return {"e_max": emax, "e_min": emin, "e_warp": np.sqrt(C[:, 0, 0]) - 1, "e_weft": np.sqrt(C[:, 1, 1]) - 1,
            "shear_rad": np.arcsin(np.clip(C[:, 0, 1] / np.sqrt(C[:, 0, 0] * C[:, 1, 1]), -1, 1)),
            "t_max": trm / 2 + dd, "t_min": trm / 2 - dd, "area": area, "J": J,
            "centroid": (a + b + c) / 3}


def cauchy(mesh: ClothMesh, membrane, x):
    """(T,3,3) Cauchy membrane tension tensors (N/mm)."""
    F, E, S, _, _ = membrane.stress(x)
    C = np.einsum("tda,tdb->tab", F, F)
    J = np.sqrt(np.maximum(C[:, 0, 0] * C[:, 1, 1] - C[:, 0, 1] ** 2, 1e-12))
    return np.einsum("tda,tab,teb->tde", F, S, F) / J[:, None, None]


# ----------------------------------------------------------------------------- volumes
def signed_volume(x, tris) -> float:
    a, b, c = (x[tris[:, j]] for j in range(3))
    o = x[np.unique(tris)].mean(0)
    return float(np.einsum("ij,ij->i", a - o, np.cross(b - o, c - o)).sum() / 6)


def volume_centroid(x, tris):
    a, b, c = (x[tris[:, j]] for j in range(3))
    o = x[np.unique(tris)].mean(0)
    v = np.einsum("ij,ij->i", a - o, np.cross(b - o, c - o)) / 6
    cen = (a + b + c + o) / 4
    return (v[:, None] * cen).sum(0) / v.sum()


def capped_volume(x, tris, loop) -> float:
    """Volume of an open surface closed by a fan over the ordered boundary loop ``loop``
    (orientation chosen so the result is positive: the cap faces away from the surface)."""
    P = x[np.asarray(loop)]
    c = P.mean(0)
    n = len(loop)
    xx = np.vstack([x, c[None]])
    ci = len(x)
    cap = np.array([[ci, loop[i], loop[(i + 1) % n]] for i in range(n)])

    def varea(xx_, t_):
        a, b, c_ = (xx_[t_[:, j]] for j in range(3))
        return 0.5 * np.cross(b - a, c_ - a).sum(0)
    if np.dot(varea(xx, cap), varea(x, tris)) > 0:
        cap = cap[:, [0, 2, 1]]
    return signed_volume(xx, np.vstack([tris, cap]))
