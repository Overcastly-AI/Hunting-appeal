"""Webbing as geometry (BL-018 task 2): thickness, rounded selvedges, true-scale weave UVs, tails, keepers and the
wraps through hardware.

UV convention for every strap: u = distance across the width, v = distance along the strap, both in mm / TILE_MM,
so the Cycles webbing shader (``studio`` material ``webbing``) weaves at the real pick pitch. Thickness defaults come
from the webbing class (ASSUMPTION: 1.5 mm for 25 mm heavyweight nylon, 1.8 mm for 38 / 50 mm; the records give
width and mass only. Settle with a caliper on the purchased roll).
"""
from __future__ import annotations

import numpy as np

from . import arclen, catmull, concat, hash01, interp_rows, resample, sweep, tangents, unit

THICK = {20: 1.4, 25: 1.5, 38: 1.8, 50: 1.8}      # mm, ASSUMPTION (see module docstring)


def thickness(width):
    return THICK.get(int(round(width)), 1.6)


def profile(width, thick, n_edge=5):
    """Closed cross-section (across, out): flat faces, half-round selvedges with a slightly proud selvedge bead."""
    r = thick / 2
    hw = width / 2 - r
    pts = []
    for a in np.linspace(-np.pi / 2, np.pi / 2, n_edge):          # +u selvedge
        pts.append([hw + 1.08 * r * np.cos(a), 1.08 * r * np.sin(a)])
    for u in np.linspace(hw, -hw, 7)[1:-1]:                       # top face (very slightly cupped)
        pts.append([u, r * (0.94 + 0.06 * (u / hw) ** 2)])
    for a in np.linspace(np.pi / 2, 3 * np.pi / 2, n_edge):       # -u selvedge
        pts.append([-hw + 1.08 * r * np.cos(a), 1.08 * r * np.sin(a)])
    for u in np.linspace(-hw, hw, 7)[1:-1]:
        pts.append([u, -r * (0.94 + 0.06 * (u / hw) ** 2)])
    return np.array(pts)


def _u_mm(prof, width):
    """UV u for the profile: the top face runs 0..width, the bottom face mirrors it (so both faces weave)."""
    return prof[:, 0] + width / 2


def strap(P, N, width=25.0, thick=None, step=3.0, v0=0.0):
    """Webbing along path P (n, 3) with surface normals N (n, 3) (the strap face is perpendicular to N)."""
    thick = thick or thickness(width)
    P = np.asarray(P, float)
    N = np.asarray(N, float)
    if N.ndim == 1:
        N = np.tile(N, (len(P), 1))
    if len(N) != len(P):
        N = interp_rows(N, np.linspace(0, 1, len(N)), np.linspace(0, 1, len(P)))
    s0 = arclen(P)
    if s0[-1] < 1e-6:
        return concat([])
    Pr, s = resample(P, step)
    Nr = unit(interp_rows(N, s0, s))
    prof = profile(width, thick)
    m = sweep(Pr, Nr, prof, u_mm=_u_mm(prof, width), v0=v0)
    m.metadata["strap"] = {"P": Pr, "N": Nr, "width": float(width), "thick": float(thick)}
    return m


def local_strap(pts_xz, width, thick=None, R=None, p=None, per=6, smooth=True):
    """Strap whose centreline is drawn in the local x-z plane of a placement frame (it runs across y). Used for the
    wraps round buckle bars. ``R``, ``p`` place it in the world."""
    thick = thick or thickness(width)
    q = np.asarray(pts_xz, float)
    P = np.column_stack([q[:, 0], np.zeros(len(q)), q[:, 1]])
    if smooth and len(P) > 2:
        P = catmull(P, per)
    T = tangents(P)
    N = np.column_stack([-T[:, 2], np.zeros(len(P)), T[:, 0]])     # rotate the tangent +90 deg in x-z
    m = strap(P, N, width, thick, step=1.2)
    if R is not None:
        from . import placed
        m = placed(m, R, p if p is not None else np.zeros(3))
    return m


def tail(p0, t0, n0, length=70.0, width=25.0, thick=None, gravity=(0, 0, -1.0), stiffness=0.55, seed=0.0,
         fold=12.0, skin_push=None):
    """Free tail leaving p0 along t0 (surface normal n0): it bends towards gravity as a stiff ribbon does, with a
    slight twist and wave, and ends in the folded, bartacked stop (``fold`` mm doubled back) that keeps it from
    pulling through a buckle. ``skin_push(P) -> P`` keeps it off the bag."""
    thick = thick or thickness(width)
    g = unit(np.asarray(gravity, float))
    t, n = unit(np.asarray(t0, float)), unit(np.asarray(n0, float))
    P, Ns = [np.asarray(p0, float)], [n]
    ds = 3.0
    ph = 6.28 * float(hash01(seed + 0.37))
    for k in range(int(length / ds)):
        s = (k + 1) * ds
        pull = g - np.dot(g, t) * t
        t = unit(t + pull * (ds / (stiffness * 60.0)))
        b = np.cross(n, t)
        t = unit(t + b * 0.02 * np.sin(s / 23.0 + ph))                       # slight sideways wander
        n = unit(n - np.dot(n, t) * t)
        P.append(P[-1] + t * ds)
        Ns.append(n)
    P, Ns = np.array(P), np.array(Ns)
    if skin_push is not None:
        P = skin_push(P)
    out = [strap(P, Ns, width, thick, step=3.0)]
    if fold > 0:                                                             # folded stop: doubled end + bartack
        from . import seams
        te, ne = unit(P[-1] - P[-2]), Ns[-1]
        f = np.array([P[-1], P[-1] + te * 1.2 + ne * (thick * 0.6), P[-1] + ne * (thick * 1.15),
                      P[-1] - te * fold + ne * (thick * 1.1)])
        out.append(strap(catmull(f, 5), ne, width, thick, step=1.5))
        bt = seams.bartack(P[-1] - te * (fold * 0.55) + ne * (thick * 1.65), ne, np.cross(ne, te), width - 5.0)
        out[0].metadata.setdefault("extras", {}).setdefault("thread", []).append(bt)
    return concat(out)


def keeper(p, n, t, width=25.0, stack=3.2, band=12.0, thick=1.0):
    """Elastic keeper: a 12 mm band round the strap stack (``stack`` mm high) at p; n out of the surface, t along
    the strap. Material ``elastic``."""
    n, t = unit(n), unit(t)
    b = np.cross(n, t)
    hw, hh = width / 2 + 0.8, stack / 2 + 0.5
    ring = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, 5)):
            ring.append([sx * (hw - 1.0) + 1.0 * np.cos(a) * 1.0, sy * (hh - 0.8) + 0.8 * np.sin(a)])
    ring = np.array(ring)
    P = np.asarray(p, float) + ring[:, :1] * b + ring[:, 1:] * n
    out_n = unit(ring[:, :1] * b / hw + ring[:, 1:] * n / hh)
    prof = profile(band, thick, n_edge=4)
    m = sweep(P, out_n, prof, closed=True, u_mm=_u_mm(prof, band))
    return m


# ------------------------------------------------------------------------------------- wraps through hardware
def threading(kind: str, tail_len: float = 34.0):
    """Webbing wrapped through a piece of hardware and its stitching, in the hardware's local frame (mm).

    Returns {"webbing": [mesh], "thread": [mesh]}. The standing strap is expected to arrive along the surface under
    the piece from -x (adjustable side) and, for buckles with a sewn side, to leave to +x. Each wrap starts inside
    the standing strap's own thickness, so there is no gap and no coincident face.
    """
    from . import hardware as HW, seams
    sp = HW.SPECS[kind]
    fam = HW._family(kind)
    w = sp.get("web", 25.0)
    th = thickness(w)
    T, L = sp["T"], sp["L"]
    zs = -T / 2 - th / 2 - 0.25                    # centreline of the standing strap lying under the piece
    web, thr = [], []
    if fam == "side_release":
        x0 = -L / 2
        xa, xb = x0 + 3.6 + 2.1, x0 + 3.6 + 4.2 + 4.4 + 2.1          # outer slot, inner slot (hardware._side_release)
        top = T * 0.40 + th / 2 + 0.9
        # adjustable (male) side: up the inner slot, over the toothed bar, down the outer slot, tail on top
        pts = [[xb + 7.0, zs], [xb + 1.5, zs + 0.2], [xb, 0.0], [xb - 1.0, top - 0.5], [(xa + xb) / 2, top],
               [xa + 1.0, top - 0.5], [xa, T * 0.1], [xa - 2.4, -T / 2 + th / 2 + 0.5], [x0 - 6.0, zs + th + 0.5],
               [x0 - tail_len, zs + th + 0.35]]
        web.append(local_strap(pts, w, th))
        # sewn (female) side: round the end bar and back, box-X through both layers
        bar_x = L / 2 - 2.1
        slot_x = L / 2 - 4.2 - 2.3
        bt = T * 0.30 + th / 2 + 0.5
        pts = [[L / 2 + 34.0, zs], [slot_x + 2.0, zs], [slot_x, zs + 1.2], [slot_x - 0.3, 0.0], [slot_x + 0.6, bt - 0.5],
               [bar_x, bt + 0.2], [L / 2 + th * 0.9, bt - 1.5], [L / 2 + 2.6, zs + th + 1.2], [L / 2 + 9.0, zs + th + 0.2],
               [L / 2 + 34.0, zs + th + 0.15]]
        web.append(local_strap(pts, w, th))
        thr.append(seams.box_x([L / 2 + 20.5, 0, zs + th * 1.5 + 0.3], [0, 0, 1.0], [1.0, 0, 0], 20.0, w - 6.0))
    elif fam == "ladder_lock":
        x0, x1, zb = -L / 2, L / 2, -T / 2
        gx, gz = x0 + 0.47 * L, zb + 0.60 * T
        top = gz + 0.2 * T + 0.9 + th / 2 + 0.4
        pts = [[gx + 0.30 * L, zs], [gx + 0.17 * L, zs + 0.3], [gx + 0.125 * L, gz - 0.1 * T], [gx + 0.10 * L, top - 0.6],
               [gx, top], [gx - 0.10 * L, top - 0.5], [x0 + 0.20 * L, zb + 0.56 * T], [x0 + 0.02 * L, zb + 0.20 * T + th],
               [x0 - 5.0, zs + th + 0.6], [x0 - tail_len * 0.5, zs + th + 0.35]]
        web.append(local_strap(pts, w, th))
        ax = x1 - 0.065 * L                                           # anchor bar: sewn loop out to +x
        at = zb + 0.36 * T + th / 2 + 0.4
        pts = [[x1 + 30.0, zs], [ax - 0.10 * L, zs], [ax - 0.13 * L, zb + 0.18 * T], [ax - 0.09 * L, at - 0.3],
               [ax, at + 0.1], [x1 + th * 0.8, at - 0.8], [x1 + 3.0, zs + th + 0.9], [x1 + 9.0, zs + th + 0.2],
               [x1 + 30.0, zs + th + 0.15]]
        web.append(local_strap(pts, w, th))
        thr.append(seams.bartack([x1 + 12.0, 0, zs + th * 1.5 + 0.3], [0, 0, 1.0], [0, 1.0, 0], w - 5.0))
        thr.append(seams.bartack([x1 + 25.0, 0, zs + th * 1.5 + 0.3], [0, 0, 1.0], [0, 1.0, 0], w - 5.0))
    elif fam in ("g_hook", "bag_hook"):
        sx = -L / 2 + (4.0 + 2.5 if fam == "g_hook" else 5.0 + 2.75)  # closed slot centre (-x side)
        top = T / 2 + th / 2 + 0.3
        pts = [[sx - 34.0, zs + 0.0], [sx - 8.0, zs], [sx - 2.0, zs + 0.6], [sx + 0.2, 0.0], [sx - 1.2, top - 0.2],
               [sx - 4.0, top + 0.1], [-L / 2 - 1.5, top - 0.6], [-L / 2 - 6.0, zs + th + 0.5],
               [sx - 34.0, zs + th + 0.15]]
        web.append(local_strap(pts, w, th))
        thr.append(seams.bartack([-L / 2 - 12.0, 0, zs + th * 1.5 + 0.3], [0, 0, 1.0], [0, 1.0, 0], w - 5.0))
        thr.append(seams.bartack([-L / 2 - 24.0, 0, zs + th * 1.5 + 0.3], [0, 0, 1.0], [0, 1.0, 0], w - 5.0))
    return {"webbing": web, "thread": thr}
