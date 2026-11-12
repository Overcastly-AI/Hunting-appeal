"""BL-029: CORRIE F rev 3 (crown lid B-29 on crown straps B-28, port guys B-27) rendered through huntkit.viz3d.studio
with the BL-020 cloth pass and the BL-019 hunter.

    export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python            # Blender venv (huntkit/viz3d/README.md)
    export HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets        # MakeHuman / Poly Haven cache
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --render            # the four BL-029 shots
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --render lid,open   # some shots
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --docs              # copy the four to docs/screens

huntkit is not edited: the rev 1 scene (``huntkit.viz3d.corrie_f.scene``) is built with the top pouch off, then this
script swaps the guys for rev 3's (short outside run into the B-27 port), adds the B-29 crown lid as a solid cloth part
seated on the roll and the cloth top under it, and the B-28 crown straps over it on their taut path (the convex hull of
the bag, roll and lid at the strap's x: a taut strap over a convex top follows it). Lid dimensions come from
``corrie_f.LID``. ``huntkit.viz3d.corrie_f.render`` runs the shots with this script's ``build_scene``.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
PREFIX = "20261112_BL029"
NUMBER = {"hero": 1, "side": 2, "lid": 3, "open": 4}
STRAP_CLEAR = 2.0          # strap centre off the cloth / lid (as corrie_f.PATH_CLEAR)
SEAT_CLOSE_MM = 45.0       # ASSUMPTION LID-SEAT (picture choice): the lid base is a soft panel that bridges the roll's
#                            ridge like cloth: the seat is the upper envelope closed over 45 mm and smoothed. Settled by a
#                            photograph of the sewn lid on a packed bag
OPEN_DEG = 196.0           # lid-open shot: front straps unhooked, lid turned back over the bar about its rear edge until
#                            its far edge rests on the form's shoulders (picture choice; on a hunter it rests on the head)


def _F():
    import corrie_f as F
    return F


def lid_mesh(seat_fn, xc: float, yc: float, nth: int = 160, top_fn=None):
    """B-29 as one closed mesh in rings: top dome, a 10 mm rounded top edge, the wall, the base on the seat.
    ``seat_fn(x, y)`` = base height; ``top_fn(x, y)`` = the smoothed seat the crown follows (the lid is stuffed over
    the roll, so its crown follows the roll's ridge: wall + dome above it). Returns (V, F, ring of face, theta of face,
    info)."""
    F = _F()
    L = F.LID
    W, D, p = L["W"], L["D"], L["n"]
    top_fn = top_fn or seat_fn
    th = np.linspace(0, 2 * np.pi, nth, endpoint=False)
    bx = W / 2 * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / p)
    by = D / 2 * np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / p)
    base_edge = seat_fn(xc + bx, yc + by)
    er = 10.0                                      # rounded top edge radius

    def crown(rho):
        x, y = xc + rho * bx, yc + rho * by
        z = top_fn(x, y) + L["wall"] + L["dome"] * np.sqrt(np.clip(1 - rho ** 4, 0, 1))
        return np.maximum(z, seat_fn(x, y) + 15.0)
    rings = []                                     # (x, y, z) arrays, nth each, top centre first
    for rho in np.linspace(0.04, 0.96, 18):
        rings.append(np.column_stack([xc + rho * bx, yc + rho * by, crown(rho)]))
    z96 = crown(0.96)
    zwall = np.maximum(top_fn(xc + bx, yc + by) + L["wall"] - er, base_edge + 8.0)
    for a in np.linspace(0, np.pi / 2, 6)[1:]:     # round over the edge
        rho = 0.96 + (1 - 0.96) * np.sin(a)
        z = z96 - (z96 - zwall) * (1 - np.cos(a))
        rings.append(np.column_stack([xc + rho * bx, yc + rho * by, z]))
    for f in np.linspace(0, 1, 7)[1:]:             # the wall down to the base edge
        z = zwall + f * (base_edge - zwall)
        rings.append(np.column_stack([xc + bx, yc + by, z]))
    zw = float(np.median(zwall)) + er
    nwall_end = len(rings) - 1
    for rho in np.linspace(0.97, 0.04, 14):        # the base on the seat
        x, y = xc + rho * bx, yc + rho * by
        rings.append(np.column_stack([x, y, seat_fn(x, y) + 1.5]))
    V = [np.array([[xc, yc, float(crown(np.zeros(1))[0])]])] + rings + [np.array([[xc, yc, float(seat_fn(np.array([xc]), np.array([yc]))[0]) + 1.5]])]
    V = np.vstack(V)
    Fs, fr, ft = [], [], []
    idx = lambda r, i: 1 + r * nth + (i % nth)        # noqa: E731
    for i in range(nth):
        Fs.append([0, idx(0, i), idx(0, i + 1)])
        fr.append(0)
        ft.append(th[i])
    for r in range(len(rings) - 1):
        for i in range(nth):
            a, b, c, d = idx(r, i), idx(r, i + 1), idx(r + 1, i + 1), idx(r + 1, i)
            Fs += [[a, d, c], [a, c, b]]
            fr += [r + 1, r + 1]
            ft += [th[i], th[i]]
    last = len(V) - 1
    for i in range(nth):
        Fs.append([last, idx(len(rings) - 1, i + 1), idx(len(rings) - 1, i)])
        fr.append(len(rings))
        ft.append(th[i])
    return V, np.asarray(Fs), np.asarray(fr), np.asarray(ft), {"rings": rings, "th": th, "wall_top": 22,
                                                                  "wall_end": nwall_end, "zw": zw, "bx": bx, "by": by,
                                                                  "zwall": zwall + er}


def _hull_path(cloud2, A, B):
    """The taut strap over a convex top in one (y, z) plane: the upper hull chain of cloud + A + B from A to B."""
    from scipy.spatial import ConvexHull
    pts = np.vstack([cloud2, A, B])
    h = ConvexHull(pts)
    ring = list(h.vertices)                         # counter-clockwise
    ia, ib = len(pts) - 2, len(pts) - 1
    if ia not in ring or ib not in ring:
        raise ValueError(f"strap end inside the hull: A {A} B {B} cloud y {cloud2[:, 0].min():.0f}-{cloud2[:, 0].max():.0f} z {cloud2[:, 1].min():.0f}-{cloud2[:, 1].max():.0f}")
    k = ring.index(ia)
    ring = ring[k:] + ring[:k]
    j = ring.index(ib)
    c1, c2 = ring[:j + 1], [ring[0]] + ring[j:][::-1]
    zmax = lambda c: pts[c][:, 1].max()             # noqa: E731
    ch = c1 if zmax(c1) >= zmax(c2) else c2
    return pts[ch]


def _resample(P, step=3.0):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    si = np.linspace(0, s[-1], max(int(s[-1] / step), 4))
    return np.column_stack([np.interp(si, s, P[:, k]) for k in range(P.shape[1])])


def rev3(sc, open_lid: bool = False) -> dict:
    """Turn the rev 1 scene (pouch off) into rev 3. Returns a report dict."""
    from huntkit.viz3d import corrie_f as CF
    from huntkit.viz3d import geom as G
    from huntkit.viz3d.assets import mesh as amesh
    from huntkit.viz3d.assets import seams as SM
    from scipy.ndimage import gaussian_filter, grey_closing
    F = _F()
    T = CF.TORSO
    vis = dict(group="bag", modes=("pack", "pack_haul"))
    byname = {x.name: x for x in sc.parts}
    # ---- the guys: rev 2/3 run inside through the B-27 port. Outside, only the stub from the sleeve to the port shows
    old = [x for x in sc.parts if x.name.startswith(("cf_guy_R", "cf_guy_L"))]
    sc.parts = [x for x in sc.parts if x not in old]
    crown = byname[f"cf_guy_loops@t{T}"]
    Vl = np.asarray(crown.mesh.vertices)
    yb, zb = float(np.median(Vl[:, 1])), float(np.median(Vl[:, 2]))
    sk = sc.cloth_skin
    X = np.asarray(sk["X"], float)
    pc = sk["piece"].astype(str)
    tris = np.asarray(sk["tris"])
    b01 = np.unique(tris[np.char.startswith(pc, "B-01")])
    rep = {"bar_y": yb, "bar_z": zb}
    ports = []
    for sx in (1, -1):
        x = sx * F.CROWN_X
        sel = b01[(np.abs(X[b01, 0] - x) < 12) & (np.abs(X[b01, 2] - min(zb, F.PORT_Z[1] - 10)) < 20)]
        q = X[sel][np.argmin(X[sel][:, 1])] if len(sel) else np.array([x, yb + 15, zb])
        P = np.array([[x, yb, zb + 9.0], [x, 0.5 * (yb + q[1]), zb + 6.0], [x, q[1] + 1.5, q[2]]])
        P = _resample(G.catmull_rom(P, 8), 2.0)
        sc.add_strap(f"cf3_guy_stub_{'R' if sx > 0 else 'L'}", P, np.tile([0.0, 0.0, 1.0], (len(P), 1)), F.GUY_W,
                     dent=False, label="Port guy B-27: outside only from the bridle sleeve to the port (rev 2/3)", **vis)
        sl = np.array([[x, q[1] + 0.8, z] for z in np.linspace(q[2] - 40, min(q[2] + 70, F.PORT_Z[1]), 30)])
        ports.append(G.ribbon(sl, 6.0, 0.8, np.tile([0.0, -1.0, 0.0], (len(sl), 1)), step=3.0))
    sc.add_part("cf3_ports", G.concat(ports), "hypalon", label="B-27 lapped guy ports in the frame face (x +/-52)", **vis)
    # ---- seat for the lid: upper envelope of the bag top and the roll, closed and smoothed (soft base panel)
    seat_parts = [byname[n] for n in ("corrie_body", "s15_roll", "corrie_b22", "s15_W3") if n in byname]
    C = np.vstack([np.asarray(p.mesh.vertices) for p in seat_parts])
    L = F.LID
    top = C[C[:, 2] > C[:, 2].max() - 160]
    yfr = float(np.percentile(X[b01][X[b01][:, 2] > zb - 40][:, 1], 5)) if len(b01) else 0.0
    aft = float(np.percentile(top[:, 1], 98))
    yc = 0.5 * (yfr + aft) + 4.0
    xc = 0.0
    res = 5.0
    gx = np.arange(-L["W"] / 2 - 40, L["W"] / 2 + 41, res)
    gy = np.arange(yc - L["D"] / 2 - 40, yc + L["D"] / 2 + 41, res)
    Hh = np.full((len(gy), len(gx)), np.nan)
    ix = np.clip(np.round((top[:, 0] - gx[0]) / res).astype(int), 0, len(gx) - 1)
    iy = np.clip(np.round((top[:, 1] - gy[0]) / res).astype(int), 0, len(gy) - 1)
    for a, b, z in zip(iy, ix, top[:, 2]):
        if np.isnan(Hh[a, b]) or z > Hh[a, b]:
            Hh[a, b] = z
    floor = np.nanpercentile(Hh, 5)
    Hh = np.where(np.isnan(Hh), floor, Hh)
    k = int(SEAT_CLOSE_MM / res)
    Hs = gaussian_filter(grey_closing(Hh, size=(k, k)), 2.0)
    Hs = np.maximum(Hs, Hh)

    def seat(x, y):
        from scipy.ndimage import map_coordinates
        return map_coordinates(Hs, [(np.asarray(y) - gy[0]) / res, (np.asarray(x) - gx[0]) / res], order=1, mode="nearest")
    Ht = gaussian_filter(Hs, 60.0 / res)

    def seat_top(x, y):
        from scipy.ndimage import map_coordinates
        return map_coordinates(Ht, [(np.asarray(y) - gy[0]) / res, (np.asarray(x) - gx[0]) / res], order=1, mode="nearest")
    if open_lid:          # off the roll the base panel relaxes flat: build it on a flat seat at the rear edge, then turn it
        zc0 = float(seat(np.array([xc]), np.array([yc - L["D"] / 2 + 10.0]))[0])
        flat = lambda x, y: np.full(np.shape(x), zc0)       # noqa: E731
        V, Fc, fr, ft, info = lid_mesh(flat, xc, yc, top_fn=flat)
    else:
        V, Fc, fr, ft, info = lid_mesh(seat, xc, yc, top_fn=seat_top)
    hinge_y = yc - L["D"] / 2
    if open_lid:                                  # turned back about its rear (frame-side) bottom edge
        a = np.radians(OPEN_DEG)
        piv = np.array([0.0, hinge_y, float(info["rings"][info["wall_end"]][int(np.argmin(info["by"])), 2])])
        R = np.array([[1, 0, 0], [0, np.cos(a), np.sin(a)], [0, -np.sin(a), np.cos(a)]])
        V = (V - piv) @ R.T + piv
    th = ft
    # camo corner caps: the wall faces within cap_mm of each aft corner (aft = +y, theta about pi/2)
    ring_wall = (fr > info["wall_top"]) & (fr <= info["wall_end"])
    bx, by = info["bx"], info["by"]
    per = np.r_[0, np.cumsum(np.hypot(np.diff(np.r_[bx, bx[0]]), np.diff(np.r_[by, by[0]])))]
    nth = len(info["th"])
    s_face = np.interp(th, np.r_[info["th"], 2 * np.pi], per)
    corners = []
    for cx in (1, -1):                            # aft corners at the superellipse's (+-W/2, +D/2) diagonal
        i = int(np.argmin((bx - cx * L["W"] / 2 * 0.84) ** 2 + (by - L["D"] / 2 * 0.84) ** 2))
        corners.append(per[i])
    cap = np.zeros(len(Fc), bool)
    for c in corners:
        d = np.abs(s_face - c)
        d = np.minimum(d, per[-1] - d)
        cap |= ring_wall & (d < L["cap_mm"])
    base = fr > info["wall_end"]
    body = ~(cap | base)
    uv = np.column_stack([V[:, 0], V[:, 1]]) / 380.0
    lidvis = dict(group="bag", modes=("pack", "pack_haul"))

    def sub(mask):
        f = Fc[mask]
        u, inv = np.unique(f, return_inverse=True)
        return amesh(V[u], inv.reshape(-1, 3), uv[u])
    from huntkit.viz3d.assets.fabric import Look
    sc.add_fabric("cf3_lid", sub(body), "body", look=Look(slack=0.22, fold=1.4, hand=0.5), max_edge=4.0,
                  uv_is_pattern=False, label=f"B-29 crown lid {F.crown_lid()['volume_L']:.1f} L", **lidvis)
    sc.add_fabric("cf3_lid_caps", sub(cap), "camo", look=Look(slack=0.1, fold=1.0, hand=0.5), max_edge=4.0,
                  uv_is_pattern=False, label="B-29 camo corner caps over the D2 blades", **lidvis)
    sc.add_fabric("cf3_lid_base", sub(base), "body", look=Look(slack=0.3, fold=1.6, hand=0.5), max_edge=4.0,
                  uv_is_pattern=False, label="B-29 base (70D)", **lidvis)
    rings = info["rings"]

    def ringpts(r):
        P = rings[r]
        if open_lid:
            P = (P - piv) @ R.T + piv
        return P
    cen = V.mean(0)
    for nm, r in (("top", info["wall_top"]), ("base", info["wall_end"])):
        P = ringpts(r)
        P = np.vstack([P, P[:1]])
        N = P - cen
        N[:, 2] *= 0.3
        N /= np.linalg.norm(N, axis=1)[:, None]
        sc.add_seam(f"cf3_lid_seam_{nm}", P, N, material="body", **lidvis)
    # zip along the aft wall, mid height, corner to corner and round both corners
    rz = (info["wall_top"] + info["wall_end"]) // 2
    Pz = ringpts(rz)
    aft_i = np.where(by > 0)[0]
    s_aft = per[aft_i]
    mid = 0.5 * (corners[0] + corners[1])
    keep = aft_i[np.abs(s_aft - mid) < L["zip_mm"] / 2]
    keep = keep[np.argsort(per[keep])]
    Pz = Pz[keep]
    Nz = Pz - cen
    Nz[:, 2] = 0
    Nz /= np.linalg.norm(Nz, axis=1)[:, None]
    sc.add_zip("cf3_lid_zip", Pz + 0.6 * Nz, Nz, size=5, sliders=(0.82,), pull_down=(0, 0, -1.0), **lidvis)
    # ---- crown straps over the lid: bar sleeve -> up the frame face -> over the lid in its channel -> hinge-band tab
    lidV = V
    out = {"lid_centre": [xc, yc], "lid_top_z": float(lidV[:, 2].max()), "straps": {}}
    for sx in (1, -1):
        x = sx * F.CROWN_X
        cl = [np.asarray(p.mesh.vertices) for p in seat_parts] + [lidV]
        cl = np.vstack(cl)
        cl = cl[np.abs(cl[:, 0] - x) < 15.0]
        A2 = np.array([yb + 9.0, zb + 2.0])
        # front tab on the hinge band at the strap's x, 40 mm under the lid's aft wall bottom
        aftv = np.unique(tris[np.char.startswith(pc, "B-02")])
        q = aftv[np.abs(X[aftv, 0] - x) < 12]
        ia = int(np.argmin(np.abs(info["rings"][info["wall_end"]][:, 0] - x) + 1e3 * (info["by"] < 0)))
        zt = (info["rings"][info["wall_end"]][ia, 2] if not open_lid else zb + 40) - 40.0
        q = q[np.argmin(np.abs(X[q, 2] - zt))] if len(q) else None
        B2 = np.array([X[q, 1] + 2.0, X[q, 2]]) if q is not None else np.array([yc + L["D"] / 2, zt])
        if open_lid:                                # unhooked: from the bar to the lid's hinge edge only, the front ends
            rear = (np.array([[x, hinge_y, piv[2]]]) - piv) @ R.T + piv
            P = np.array([[x, A2[0], A2[1]], [x, 0.5 * (A2[0] + rear[0, 1]), 0.5 * (A2[1] + rear[0, 2]) + 5], rear[0]])
            P = _resample(G.catmull_rom(P, 8), 3.0)
            sc.add_strap(f"cf3_crown_{'R' if sx > 0 else 'L'}", P, np.tile([0.0, -0.3, 1.0], (len(P), 1)), F.GUY_W,
                         dent=False, label="B-28 crown strap, front unhooked (lid open)", **vis)
            # the free front end hangs from the lid's (former) front edge
            fe = (np.array([[x, yc + L["D"] / 2 - 5, info["zw"]]]) - piv) @ R.T + piv
            Ph = np.array([fe[0], fe[0] + [0, -6, -60], fe[0] + [0, -4, -150]])
            Ph = _resample(G.catmull_rom(Ph, 6), 3.0)
            sc.add_strap(f"cf3_crown_end_{'R' if sx > 0 else 'L'}", Ph, np.tile([0.0, -1.0, 0.0], (len(Ph), 1)),
                         F.GUY_W, dent=False, **vis)
            sc.add_hardware(f"cf3_crown_lock_{'R' if sx > 0 else 'L'}", "ladder_lock_25_heavy", Ph[-12],
                            [0.0, -1.0, 0.0], [0.0, 0.0, -1.0], **vis)
            continue
        B2 = B2 + np.array([4.0, 0.0])
        cl = cl[cl[:, 2] > max(A2[1], B2[1]) + 1.0]          # both strap ends lie under the cloud: they are on the hull
        near = cl[cl[:, 2] < A2[1] + 60.0]
        if len(near):                                       # the render's frame face sits 0-17 mm inside the bar (D-9):
            A2[0] = min(A2[0], float(near[:, 1].min()) - 2.0)   # the strap leaves the sleeve on the bar's top, forward
        H2 = _hull_path(cl[:, 1:], A2, B2)
        H2 = _resample(H2, 2.0)
        # push the run clear and give it outward normals (in the y-z plane)
        t = np.gradient(H2, axis=0)
        t /= np.linalg.norm(t, axis=1)[:, None]
        n2 = np.column_stack([-t[:, 1], t[:, 0]])
        mid2 = H2.mean(0)
        n2 *= np.sign(np.einsum("ij,ij->i", n2, H2 - mid2))[:, None]
        H2 = H2 + n2 * STRAP_CLEAR
        P = np.column_stack([np.full(len(H2), x), H2])
        P = SM.smooth_path(P, 3.0, 5.0)
        N = np.column_stack([np.zeros(len(P)), n2[:len(P)] if len(n2) >= len(P) else np.resize(n2, (len(P), 2))])
        N = np.column_stack([np.zeros(len(P)), np.interp(np.linspace(0, 1, len(P)), np.linspace(0, 1, len(n2)), n2[:, 0]),
                             np.interp(np.linspace(0, 1, len(P)), np.linspace(0, 1, len(n2)), n2[:, 1])])
        N /= np.linalg.norm(N, axis=1)[:, None]
        sc.add_strap(f"cf3_crown_{'R' if sx > 0 else 'L'}", P, N, F.GUY_W, tail=0.0, dent=True,
                     label="B-28 crown strap: B-25 bridle -> over the roll and the lid -> hinge-band tab", **vis)
        tt = np.gradient(P, axis=0)
        tt /= np.linalg.norm(tt, axis=1)[:, None]
        i = len(P) - 18
        sc.add_hardware(f"cf3_crown_lock_{'R' if sx > 0 else 'L'}", "ladder_lock_25_heavy", P[i], N[i], tt[i], **vis)
        # tail of the strap past the ladder lock, tucked down the aft face
        tail = P[i] + np.outer(np.linspace(0, 1, 30), [0, 6.0, -95.0]) + N[i] * 3.0
        sc.add_strap(f"cf3_crown_tail_{'R' if sx > 0 else 'L'}", tail, np.tile(N[i], (len(tail), 1)), F.GUY_W, dent=False, **vis)
        # the channel over the lid crown: the part of the path above the lid's wall top, 30 mm wide, 1.5 mm proud
        on = (np.abs(P[:, 1] - yc) < L["D"] / 2 - 14) & (P[:, 2] > float(np.median(info["zwall"])) - 10)
        if on.sum() > 4:
            Pc = P[on] + N[on] * 1.6
            sc.add_part(f"cf3_channel_{'R' if sx > 0 else 'L'}", G.ribbon(Pc, L["channel_w"], 1.2, N[on], step=3.0),
                        "body", label="B-29 strap channel (the crown strap runs inside)", **lidvis)
            for k, j in enumerate((0, -1)):
                sc.add_seam(f"cf3_channel_bt_{'R' if sx > 0 else 'L'}{k}", Pc[[j, j]] + [[0, 0, 0], [0, 0.1, 0]],
                            N[on][[j, j]], material="body", dent=False, **lidvis)
        out["straps"]["R" if sx > 0 else "L"] = {"length_mm": float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())}
    # crown-strap toggles on the bridle (body colour; the bright ones stay on the guys, "guys on")
    togs = []
    for sx in (1, -1):
        pt = np.array([sx * (F.CROWN_X + 14.0), yb - 14.0, zb - 4.0])
        togs.append(G.capsule_between(pt - [CF.TOGGLE["L"] / 2, 0, 0], pt + [CF.TOGGLE["L"] / 2, 0, 0], CF.TOGGLE["d"] / 2))
    sc.add_part("cf3_crown_toggles", G.concat(togs), "hardware", label="Crown-strap toggles in the second bridle tab", **vis)
    sc.report["rev3"] = out
    sc.report["source"]["spec"] = "CORRIE F rev 3 (BL-029): crown lid B-29 on crown straps B-28, port guys B-27, door D2"
    return out


def build_scene(key: str, level: int = 2):
    from huntkit.viz3d import corrie_f as CF
    st = key.replace("_open", "")
    sc = CF.scene(st, False, level, with_pouch=False)
    rev3(sc, open_lid=key.endswith("_open"))
    return sc


SUB = "CORRIE F rev 3 (D2, BL-029), H1 frame, belt B. "


def shots() -> dict:
    from huntkit.viz3d import corrie_f as CF
    s = {
        "hero": CF._hunter("stand", "sixday", -36, 9, "CORRIE F rev 3 on a 6 ft hunter: crown lid, 6-day load (45 L)",
                           SUB + "1829 mm (6 ft) man, 19 in setting. ", box=CF.HUNTER_BOX, zoom=CF.HUNTER_ZOOM),
        "side": CF._hunter("side", "sixday", 90, 4, "Side profile, rev 3, 6-day load (45 L)",
                           SUB + "Crown straps over the lid. ", box=CF.HUNTER_BOX, zoom=CF.HUNTER_ZOOM),
        "lid": {"scene": "sixday", "view": {"az": -34, "el": 22, "fov": 18, "fstop": 8, "at": [0.0, 110.0, 790.0],
                                            "span": 470}, "state": {"mannequin": True, "lid": True},
                "caption": "Crown lid close-up: one strap line from the bar over the lid to the bag",
                "sub": "B-29 5.0 L lid, camo corner caps over the D2 blades, #5 coil zip; B-28 crown straps. "
                       + CF.MODEL},
        "open": {"scene": "sixday_open", "view": {"az": -58, "el": 22, "fov": 20, "fstop": 8, "at": [0.0, 20.0, 760.0],
                                                  "span": 620}, "state": {"mannequin": True, "lid": True},
                 "caption": "Lid open: front ladder locks unhooked, lid turned back over the bar",
                 "sub": "The roll top is free to open; the port guys still hold the bag top to the bar. " + CF.MODEL},
    }
    return s


def render(names=("hero", "side", "lid", "open"), quality="final", level=2):
    from huntkit.viz3d import corrie_f as CF
    CF.SHOTS.update(shots())
    CF.build_scene = build_scene
    return CF.render(list(names), SCREENS, PREFIX, quality, level, numbers={n: NUMBER[n] for n in names})


def docs(nums=(1, 2, 3, 4)):
    DOCS.mkdir(parents=True, exist_ok=True)
    out = []
    for n in nums:
        src = SCREENS / f"{PREFIX}_{n}.png"
        if src.exists():
            shutil.copyfile(src, DOCS / src.name)
            out.append(DOCS / src.name)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", nargs="?", const="hero,side,lid,open")
    ap.add_argument("--quality", default="final")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--docs", action="store_true")
    a = ap.parse_args(argv)
    if a.render:
        for r in render(a.render.split(","), a.quality, a.level):
            print(r["shot"], r["file"], r["seconds"], "s", r["mb"], "MB")
    if a.docs:
        print(docs())


if __name__ == "__main__":
    main()
