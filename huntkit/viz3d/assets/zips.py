"""Coil zips as geometry (BL-018 task 4): the two interlocked monofilament coils, both tapes with their stitch rows,
slider (``hardware.zip_slider_N``), cord pull with a moulded grip, top / bottom stops.

Chain width comes from the zip record (``coil_zipper_5 / _8 / _10`` ``chain_width_mm``). ASSUMPTION (YKK CN coil class,
no drawing in the records; settle by measuring the purchased chain): coil pitch = 0.22 x chain width, monofilament
diameter = 0.10 x chain width, tape width per side = 1.75 x chain width, tape thickness 0.6 mm.
"""
from __future__ import annotations

import numpy as np

from . import arclen, catmull, concat, frame, interp_rows, mesh, record, resample, sweep, tangents, tube, unit
from . import hardware as HW
from . import seams

SIZES = {5: "coil_zipper_5", 8: "coil_zipper_8", 10: "coil_zipper_10"}


def dims(size: int) -> dict:
    cw = float(record("hardware", SIZES[size])["chain_width_mm"])
    return {"chain": cw, "pitch": 0.22 * cw, "mono": 0.10 * cw, "tape": 1.75 * cw, "tape_t": 0.6,
            "coil_h": 0.30 * cw}


def _coil(P, N, d, side, s_lo, s_hi, lift, per=6):
    """One coil: a flattened helix of monofilament, its heads reaching just past the centre line."""
    s0 = arclen(P)
    n_turn = int((s_hi - s_lo) / d["pitch"])
    if n_turn < 1:
        return concat([])
    k = n_turn * per
    ph = np.arange(k + 1) / per * 2 * np.pi + (np.pi if side < 0 else 0.0)
    s = s_lo + np.arange(k + 1) / per * d["pitch"]
    C = interp_rows(P, s0, s)
    Nn = unit(interp_rows(N, s0, s))
    T = tangents(C)
    B = np.cross(Nn, T) * side
    half = d["chain"] / 2
    across = half * 0.42 - (half * 0.58) * np.cos(ph)          # from the tape edge (+) to past the centre (-)
    up = d["coil_h"] * 0.5 * np.sin(ph) + d["coil_h"] * 0.5
    lead = 0.18 * d["pitch"] * np.sin(ph)                      # heads lean so the two coils mesh
    Q = C + B * across[:, None] + Nn * (up + lift)[:, None] + T * lead[:, None]
    r = d["mono"] / 2
    ang = np.radians([45, 135, 225, 315])
    Tq = tangents(Q)
    U = unit(np.cross(Tq, Nn))
    W = np.cross(U, Tq)
    V = (Q[:, None, :] + r * np.cos(ang)[None, :, None] * U[:, None, :] + r * np.sin(ang)[None, :, None] * W[:, None, :])
    V = V.reshape(-1, 3)
    i = np.arange(k)[:, None] * 4
    j = np.arange(4)[None, :]
    j2 = (j + 1) % 4
    a, b, c, e = i + j, i + j2, i + 4 + j2, i + 4 + j
    F = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, e], -1).reshape(-1, 3)])
    return mesh(V, F)


def _tape(P, N, d, side, lift, step=2.5, open_gap=0.0):
    """One tape: from the coil's root out to the tape edge, with the corded edge bead under the coil."""
    s0 = arclen(P)
    Pr, s = resample(P, step)
    Nr = unit(interp_rows(N, s0, s))
    T = tangents(Pr)
    B = np.cross(Nr, T) * side
    half = d["chain"] / 2
    u = np.array([half * 0.10, half * 0.5, half, half + 1.0, d["tape"] * 0.6, d["tape"]]) + open_gap
    h = np.array([0.55, 0.75, 0.62, 0.42, 0.34, 0.20]) * d["tape_t"] / 0.6 * 0.6
    V = Pr[:, None, :] + u[None, :, None] * B[:, None, :] + (h + lift)[None, :, None] * Nr[:, None, :]
    n, m = V.shape[:2]
    uv = np.stack([np.broadcast_to(u[None, :], (n, m)), np.broadcast_to(s[:, None], (n, m))], -1).reshape(-1, 2)
    F = []
    for i in range(n - 1):
        for j in range(m - 1):
            a, b, c, e = i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j
            F += [[a, b, c], [a, c, e]] if side > 0 else [[a, c, b], [a, e, c]]
    return mesh(V.reshape(-1, 3), np.array(F), uv / 500.0), Pr, Nr, B


def cord_pull(p, n, down, size=10, length=46.0, cord_d=2.0, seed=0.0):
    """Quiet pull: a cord loop through the slider bridge, its legs running into a moulded grip. Returns
    {"cord": mesh, "grip": mesh}. ``down`` = the direction the pull hangs (projected into the surface)."""
    p, n = np.asarray(p, float), unit(n)
    dn = unit(np.asarray(down, float) - np.dot(down, n) * n)
    sd = np.cross(n, dn)
    wob = 0.12 * (np.sin(seed * 7.3) + 0.3)
    dn2 = unit(dn + sd * wob)
    a = p + n * 1.2
    loop = np.array([a - sd * 1.6 + n * 1.5, a + dn2 * 3 - sd * 3.2 + n * 1.2, a + dn2 * (length * 0.45) - sd * 2.0 + n * 1.4,
                     a + dn2 * (length * 0.62) - sd * 1.1 + n * 1.8, a + dn2 * (length * 0.62) + sd * 1.1 + n * 1.8,
                     a + dn2 * (length * 0.45) + sd * 2.0 + n * 1.4, a + dn2 * 3 + sd * 3.2 + n * 1.2,
                     a + sd * 1.6 + n * 1.5, a + n * 3.3])
    cord = tube(catmull(loop, 6, closed=True), cord_d / 2, n=8, closed=True)
    g0, g1 = a + dn2 * (length * 0.50) + n * 2.2, a + dn2 * length + n * 2.6
    ax = unit(g1 - g0)
    L = np.linalg.norm(g1 - g0)
    st = np.linspace(0, 1, 9)
    rw = np.array([2.6, 3.9, 4.3, 4.0, 3.9, 4.2, 4.6, 4.3, 2.4]) * (size / 10.0) ** 0.5       # grip half-width
    rt = np.array([1.9, 2.5, 2.7, 2.5, 2.4, 2.6, 2.8, 2.6, 1.6]) * (size / 10.0) ** 0.5       # half-thickness
    ang = np.linspace(0, 2 * np.pi, 14, endpoint=False)
    rings = [g0 + ax * (L * s) + np.outer(np.cos(ang) * w, sd) + np.outer(np.sin(ang) * t, n)
             for s, w, t in zip(st, rw, rt)]
    V = np.vstack(rings + [g0[None], g1[None]])
    F = []
    m = len(ang)
    for i in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % m
            F += [[i * m + j, i * m + j2, (i + 1) * m + j2], [i * m + j, (i + 1) * m + j2, (i + 1) * m + j]]
    c0, c1 = len(rings) * m, len(rings) * m + 1
    for j in range(m):
        j2 = (j + 1) % m
        F += [[c0, j2, j], [c1, (len(rings) - 1) * m + j, (len(rings) - 1) * m + j2]]
    grip = mesh(V, np.array(F))
    if grip.volume < 0:
        grip.faces = grip.faces[:, ::-1]
    return {"cord": cord, "grip": grip}


def coil_zip(P, N, size=10, sliders=(), closed=(0.0, 1.0), lift=0.6, pulls=True, pull_down=(0, 0, -1.0),
             stitch=True, stops=True, half=None):
    """Coil zip along P (surface normals N).

    ``closed`` = (s0, s1) fractions of the length where the chain is meshed; outside it the two halves part by up to
    one chain width. ``sliders`` = fractions along P; each slider's closing direction points away from the nearest
    open end. ``half`` = +1 / -1 keeps only one tape + coil (the half left on the bag when a door is zipped off).
    Returns {"tape": mesh, "coil": mesh, "slider": mesh, "cord": mesh, "grip": mesh, "thread": mesh}."""
    d = dims(size)
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    if N.ndim == 1:
        N = np.tile(N, (len(P), 1))
    s0 = arclen(P)
    Ltot = s0[-1]
    out = {k: [] for k in ("tape", "coil", "slider", "cord", "grip", "thread")}
    for side in ((1, -1) if half is None else (half,)):
        tp, Pr, Nr, B = _tape(P, N, d, side, lift)
        out["tape"].append(tp)
        out["coil"].append(_coil(P, N, d, side, closed[0] * Ltot + 1.0, closed[1] * Ltot - 1.0, lift + d["tape_t"] * 0.6))
        if stitch:
            for off in (d["tape"] * 0.55, d["tape"] * 0.88):
                out["thread"].append(seams.stitch_row(Pr + B * off + Nr * (lift + 0.36), Nr))
    sp = HW.SPECS[f"zip_slider_{size}"]
    for k, f in enumerate(sliders):
        s = float(np.clip(f, 0.0, 1.0)) * Ltot
        c = interp_rows(P, s0, [s])[0]
        n = unit(interp_rows(N, s0, [s])[0])
        t = unit(interp_rows(P, s0, [min(s + 2, Ltot)])[0] - interp_rows(P, s0, [max(s - 2, 0)])[0])
        closing = t if f <= 0.5 else -t
        R = frame(n, closing)
        zc = lift + d["tape_t"] * 0.2 + sp["T"] / 2 - 1.4
        out["slider"].append(HW.place(f"zip_slider_{size}", c + n * zc, n, closing))
        if pulls:
            anchor = c + n * (zc + sp["T"] / 2 - 2.0) - R[:, 0] * (sp["L"] * 0.05)
            pl = cord_pull(anchor, n, pull_down, size=size, seed=k + size)
            out["cord"].append(pl["cord"])
            out["grip"].append(pl["grip"])
    if stops:
        for f in (0.0, 1.0):
            s = f * Ltot
            c = interp_rows(P, s0, [s])[0]
            n = unit(interp_rows(N, s0, [s])[0])
            t = tangents(P)[0 if f == 0 else -1]
            R = frame(n, t)
            st = HW._to_mesh(HW._rbox(d["chain"] * 0.55, d["chain"] * 1.15, d["coil_h"] + 0.8, 0.4, rp=1.0))
            st.vertices = st.vertices @ R.T + c + n * (lift + d["tape_t"] + d["coil_h"] / 2)
            out["slider"].append(st)
    return {k: concat(v) for k, v in out.items()}


__all__ = ["dims", "coil_zip", "cord_pull", "SIZES"]
_ = (sweep,)
