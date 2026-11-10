"""Parametric pack hardware with real slots, bars and rounded edges (BL-018 task 1).

Every piece is a watertight solid built with manifold3d (2D profile -> extrude -> Minkowski round, then CSG for
cavities and slots), in the *placement frame* of ``assets.frame``:

    +x  along the webbing (load direction), +y across the webbing width, +z out of the fabric; origin at the
    centre of the piece's bounding box.

``SPECS[kind]`` holds the dimensions and where each came from. Values a material record gives are read from the
record (``data/materials/hardware/*.yaml``) and are met within 0.5 mm (tests/test_viz3d_assets.py). Everything else is
``ASSUMPTION:`` typical of the class named in the record (ITW Nexus / Duraflex acetal, YKK coil sliders): settle each
by measuring the purchased part or the maker's drawing; the render uses them, no load path does.

    from huntkit.viz3d.assets import hardware as HW
    m = HW.build("side_release_25")              # trimesh, mm, local frame
    m = HW.place("ladder_lock_25", p, n, t)      # at point p, surface normal n, strap direction t
    HW.library_glb("outputs/viz3d_assets/hardware.glb")   # cached library, built on demand (about 1 MB)

Kinds: side_release_25 / _38 / _50 (the 50 is the belt buckle), ladder_lock_25, ladder_lock_25_heavy, tri_glide_25,
tri_glide_38, cam_buckle_25, cam_buckle_38, g_hook_25, g_hook_38, d_ring_25, bag_hook_38, zip_slider_5 / _8 / _10,
zip_pull_5 / _8 / _10, cord_lock.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from . import REPO, concat, frame, mesh, placed, record

A = "ASSUMPTION (class-typical, measure the purchased part)"


def _rec(rid, key, default=None):
    try:
        return record("hardware", rid).get(key, default)
    except FileNotFoundError:
        return default


def _specs() -> dict:
    S = {}
    for w, L, T in ((25, 62.0, 11.0), (38, 76.0, 13.0), (50, 92.0, 15.5)):
        web = float(_rec(f"buckle_side_release_{w}mm", "width_mm", w))
        S[f"side_release_{w}"] = {
            "web": web, "L": L, "W": web + 9.0, "T": T, "slot": web + 1.5, "material": "pom",
            "src": {"web": f"record buckle_side_release_{w}mm width_mm", "L": A, "W": A, "T": A, "slot": A}}
    web = float(_rec("ladder_lock_25mm", "width_mm", 25))
    S["ladder_lock_25"] = {"web": web, "L": 38.0, "W": web + 8.0, "T": 8.5, "slot": web + 1.5, "material": "pom",
                           "src": {"web": "record ladder_lock_25mm width_mm", "L": A, "W": A, "T": A, "slot": A}}
    h = "ladder_lock_25mm_heavy"
    S["ladder_lock_25_heavy"] = {
        "web": float(_rec(h, "width_mm", 25)), "L": float(_rec(h, "outer_length_mm", 49.9)),
        "W": float(_rec(h, "outer_width_mm", 34.2)), "T": float(_rec(h, "thickness_mm", 10.3)),
        "slot": float(_rec(h, "width_mm", 25)) + 1.5, "material": "pom",
        "src": {k: f"record {h}" for k in ("web", "L", "W", "T")} | {"slot": A}}
    for w, L, T in ((25, 24.0, 3.2), (38, 28.0, 3.6)):
        S[f"tri_glide_{w}"] = {"web": float(w), "L": L, "W": w + 8.0, "T": T, "slot": w + 1.5, "material": "pom",
                               "src": {"web": f"webbing record width {w}", "L": A, "W": A, "T": A, "slot": A}}
    for w, L, T in ((25, 44.0, 14.0), (38, 52.0, 16.0)):
        S[f"cam_buckle_{w}"] = {"web": float(w), "L": L, "W": w + 9.0, "T": T, "slot": w + 1.5, "material": "metal",
                                "src": {"web": f"webbing record width {w}", "L": A, "W": A, "T": A, "slot": A}}
    for w in (25, 38):
        S[f"g_hook_{w}"] = {"web": float(w), "L": 27.0, "W": w + 12.0, "T": 3.5, "slot": w + 1.5, "material": "metal",
                            "src": {"web": f"webbing record width {w}", "L": A, "W": A, "T": A, "slot": A}}
    d = "d_ring_25mm_aluminium"
    sec = float(_rec(d, "section_thickness_mm", 4))
    web = float(_rec(d, "width_mm", 25))
    S["d_ring_25"] = {"web": web, "sec": sec, "inner_w": web + 1.0, "inner_h": 17.0, "L": 17.0 + 2 * sec,
                      "W": web + 1.0 + 2 * sec, "T": sec, "material": "metal",
                      "src": {"web": f"record {d} width_mm", "sec": f"record {d} section_thickness_mm",
                              "inner_w": A, "inner_h": A}}
    S["bag_hook_38"] = {"web": 38.0, "L": 48.0, "W": 52.0, "T": 4.0, "slot": 39.5, "mouth": 7.0, "material": "metal",
                        "src": {"web": "bag_attachment.md bag hooks 38 mm", "L": A, "W": A, "T": A, "slot": A,
                                "mouth": A}}
    for n, rid in ((5, "coil_zipper_5"), (8, "coil_zipper_8"), (10, "coil_zipper_10")):
        cw = float(_rec(rid, "chain_width_mm", {5: 5.8, 8: 7.8, 10: 9.0}[n]))
        S[f"zip_slider_{n}"] = {"chain": cw, "W": round(cw * 2.0, 2), "L": round(cw * 2.5, 2),
                                "T": round(cw * 0.62 + 4.6, 2), "throat": cw + 0.6, "material": "metal",
                                "src": {"chain": f"record {rid} chain_width_mm", "W": A, "L": A, "T": A, "throat": A}}
        S[f"zip_pull_{n}"] = {"chain": cw, "W": round(cw * 1.25, 2), "L": round(cw * 3.4, 2), "T": 1.6,
                              "material": "metal", "src": {"chain": f"record {rid} chain_width_mm", "W": A, "L": A,
                                                           "T": A}}
    cd = float(_rec("cord_lock_spring", "cord_diameter_max_mm", 4))
    S["cord_lock"] = {"cord": cd, "hole": cd + 0.5, "L": 24.0, "W": 17.0, "T": 12.0, "material": "pom",
                      "src": {"cord": "record cord_lock_spring cord_diameter_max_mm", "hole": A, "L": A, "W": A,
                              "T": A}}
    return S


SPECS = _specs()


# ------------------------------------------------------------------------------------------- manifold helpers
def _m3():
    import manifold3d as m3
    return m3


def _rrect(L, W, r, cx=0.0, cy=0.0, n=8):
    """Rounded rectangle polygon (CCW), L along x, W along y."""
    r = min(r, L / 2 - 1e-3, W / 2 - 1e-3)
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, n)):
            pts.append([cx + sx * (L / 2 - r) + r * np.cos(a), cy + sy * (W / 2 - r) + r * np.sin(a)])
    return np.array(pts)


def _xs(outer, holes=()):
    m3 = _m3()
    return m3.CrossSection([np.asarray(outer, float)] + [np.asarray(h, float)[::-1] for h in holes],
                           m3.FillRule.EvenOdd)


def _round_extrude(outer, holes, T, r=0.6, seg=6):
    """Profile (outer + holes) extruded to thickness T (z in [-T/2, T/2]) with every edge rounded to radius r.
    The outline and T are exact (inset by r, then Minkowski sum with a sphere of radius r)."""
    m3 = _m3()
    r = min(r, T / 2 - 0.05)
    cs = _xs(outer, holes).offset(-r, m3.JoinType.Round, 2.0, 12)
    body = cs.extrude(T - 2 * r).translate((0, 0, -(T - 2 * r) / 2))
    return body.minkowski_sum(m3.Manifold.sphere(r, 4 * max(seg // 2, 2)))


def _box(L, W, T, c=(0, 0, 0)):
    m3 = _m3()
    return m3.Manifold.cube((L, W, T), True).translate(tuple(c))


def _rbox(L, W, T, r=0.6, c=(0, 0, 0), rp=None):
    return _round_extrude(_rrect(L, W, rp if rp is not None else min(L, W) * 0.2), (), T, r).translate(tuple(c))


def _side_profile(poly_xz, width, r=0.5, cy=0.0):
    """Extrude a profile drawn in the x-z plane along y (centred on cy)."""
    m = _round_extrude(np.asarray(poly_xz, float), (), width, r)       # profile in (x, y'), thickness along z'
    # (x, y', z') -> (x, z', y') i.e. rotate +90 deg about x so y' becomes z and the thickness runs along y
    return m.rotate((90.0, 0.0, 0.0)).translate((0, cy, 0))


def _cyl_y(r, length, c=(0, 0, 0), seg=20):
    m3 = _m3()
    return m3.Manifold.cylinder(length, r, r, seg, True).rotate((90.0, 0, 0)).translate(tuple(c))


def _to_mesh(man, uv_scale=1.0 / 40.0):
    me = man.to_mesh()
    V = np.asarray(me.vert_properties)[:, :3].astype(float)
    F = np.asarray(me.tri_verts).astype(int)
    return mesh(V, F, V[:, :2] * uv_scale)


def _centre(m):
    lo, hi = m.vertices.min(0), m.vertices.max(0)
    m.vertices = m.vertices - (lo + hi) / 2
    return m


# --------------------------------------------------------------------------------------------------- builders
def _side_release(sp):
    """Female body (+x): hollow shell, pinch windows in both side walls, strap bar at the far end. Male (-x): ladder
    base (two slots, toothed centre bar), two sprung arms whose barbs sit in the windows, centre guide tongue."""
    m3 = _m3()
    L, W, T, slot = sp["L"], sp["W"], sp["T"], sp["slot"]
    wall = 0.17 * T + 0.3
    Lf = 0.60 * L
    xf0, xf1 = L / 2 - Lf, L / 2
    cf = (xf0 + xf1) / 2
    # female: slightly waisted plan, big corner radii at the strap end
    pl = []
    for x, hw in ((xf0, W / 2), (xf0 + 0.55 * Lf, W / 2), (xf1 - 0.12 * Lf, W / 2 - 1.6), (xf1, W / 2 - 4.5)):
        pl.append([x, hw])
    outer = np.array(pl + [[x, -y] for x, y in pl[::-1]])[::-1]
    fem = _round_extrude(outer, (), T, r=1.0)
    bar = 4.2                                                   # strap bar at the far end
    cav_L = Lf - bar - 5.0
    cav = _box(cav_L + 2, W - 2 * wall, T - 2 * wall, (xf0 + cav_L / 2 - 1, 0, 0))
    fem = fem - cav
    fem = fem - _box(4.6, slot, T + 2, (xf1 - bar - 2.3, 0, 0))                       # webbing slot
    for sz in (1, -1):                                                                 # strap bar 0.6 T high
        fem = fem - _box(bar + 6.0, slot, 0.2 * T + 1, (xf1 - bar / 2 + 0.6, 0, sz * (T / 2 + 0.5 - 0.1 * T)))
    win_L, win_x = 0.34 * Lf, xf0 + 0.50 * Lf
    for sy in (1, -1):                                                                 # pinch windows
        fem = fem - _round_extrude(_rrect(win_L, 2 * wall + 2, 1.0), (), T - 2 * wall - 0.6, 0.3).translate(
            (win_x, sy * (W / 2 - wall / 2), 0))
    fem = fem - _rbox(0.36 * Lf, 0.42 * W, 1.2, 0.3, (xf0 + 0.36 * Lf, 0, T / 2), rp=3.0)   # thumb recess, top face
    # male
    Lb = L - Lf
    xb0 = -L / 2
    s1 = 4.2
    base = _round_extrude(_rrect(Lb, W, 3.0, cx=xb0 + Lb / 2),
                          (_rrect(s1, slot, 0.8, cx=xb0 + 3.6 + s1 / 2), _rrect(s1, slot, 0.8, cx=xb0 + 3.6 + s1 + 4.4 + s1 / 2)),
                          T * 0.80, r=0.8)
    ti = T - 2 * wall - 0.7
    arm_L = 0.72 * (Lf - bar - 5.0)
    arms = []
    for sy in (1, -1):
        y_out = W / 2 - wall - 0.35
        prof = np.array([[xf0 - 2.0, sy * (y_out - 4.2)], [xf0 + arm_L * 0.55, sy * (y_out - 3.4)],
                         [xf0 + arm_L, sy * (y_out - 2.8)], [xf0 + arm_L + 1.5, sy * (y_out - 0.8)],
                         [win_x + win_L / 2 - 0.6, sy * (W / 2 - 0.25)], [win_x - win_L / 2 + 0.6, sy * (W / 2 - 0.25)],
                         [win_x - win_L / 2 - 0.2, sy * y_out], [xf0 - 2.0, sy * y_out]])
        if sy < 0:
            prof = prof[::-1]
        arms.append(_round_extrude(prof[::-1] if _signed_area(prof) < 0 else prof, (), ti, r=0.5))
    tongue = _round_extrude(_rrect(arm_L + 3.0, 0.26 * W, 1.6, cx=xf0 - 2.0 + (arm_L + 3.0) / 2), (), ti, r=0.5)
    neck = _box(4.0, W - 2 * wall - 1.0, ti, (xf0 - 0.5, 0, 0))
    male = base + arms[0] + arms[1] + tongue + neck
    # teeth on the centre bar of the ladder
    for k in range(5):
        y = (k - 2) * slot / 5.5
        male = male + _box(4.0, 1.1, 1.0, (xb0 + 3.6 + s1 + 2.2, y, T * 0.40 + 0.3))
    return {"female": _to_mesh(fem), "male": _to_mesh(male)}


def _signed_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _ccw(p):
    p = np.asarray(p, float)
    return p if _signed_area(p) > 0 else p[::-1]


def _ladder_lock(sp):
    """Two side rails (boomerang side profile), anchor bar at +x (sewn loop), raised toothed grip bar, lift tab at
    -x. The adjustable strap comes in from -x, under the tab, over the grip bar and back out under itself."""
    L, W, T, slot = sp["L"], sp["W"], sp["T"], sp["slot"]
    rail = (W - slot) / 2
    x0, x1 = -L / 2, L / 2
    zb = -T / 2
    prof = _ccw(np.array([[x1, zb], [x1, zb + 0.42 * T], [x1 - 0.30 * L, zb + 0.46 * T], [x0 + 0.42 * L, zb + T],
                          [x0 + 0.16 * L, zb + T], [x0, zb + 0.62 * T], [x0, zb + 0.38 * T], [x0 + 0.30 * L, zb]]))
    out = None
    for sy in (1, -1):
        r = _side_profile(prof, rail, r=0.7, cy=sy * (W / 2 - rail / 2))
        out = r if out is None else out + r
    inner = W - 2 * rail + 1.0
    anchor = _side_profile(_rrect(0.13 * L, 0.36 * T, 1.2, cx=x1 - 0.065 * L, cy=zb + 0.18 * T), inner, r=0.6)
    gx, gz = x0 + 0.47 * L, zb + 0.60 * T
    grip = _side_profile(_ccw(np.array([[gx - 0.085 * L, gz - 0.2 * T], [gx + 0.085 * L, gz - 0.2 * T],
                                        [gx + 0.07 * L, gz + 0.2 * T], [gx - 0.10 * L, gz + 0.2 * T]])), inner, r=0.5)
    tab = _side_profile(_ccw(np.array([[x0, zb + 0.40 * T], [x0 + 0.17 * L, zb + 0.74 * T], [x0 + 0.17 * L, zb + T],
                                       [x0 + 0.10 * L, zb + T], [x0, zb + 0.62 * T]])), inner, r=0.5)
    out = out + anchor + grip + tab
    for k in range(6):                                                               # grip teeth
        y = (k - 2.5) * slot / 6.5
        out = out + _box(0.14 * L, 1.0, 0.9, (gx, y, gz + 0.2 * T + 0.25))
    return {"body": _to_mesh(out)}


def _tri_glide(sp):
    L, W, T, slot = sp["L"], sp["W"], sp["T"], sp["slot"]
    bar = 4.4
    sl = (L - 3 * bar) / 2 + 0.6
    cx = bar / 2 + sl / 2 - 0.3
    m = _round_extrude(_rrect(L, W, 3.0), (_rrect(sl, slot, 0.9, cx=cx), _rrect(sl, slot, 0.9, cx=-cx)), T, r=0.8)
    return {"body": _to_mesh(m)}


def _cam_buckle(sp):
    """Die-cast base (floor plate with the anchor slot, two cheeks), 3 mm pin, cam lever with a toothed lobe."""
    L, W, T, slot = sp["L"], sp["W"], sp["T"], sp["slot"]
    x0, x1, zb = -L / 2, L / 2, -T / 2
    floor = _round_extrude(_rrect(L, W, 4.0), (_rrect(5.0, slot, 1.0, cx=x1 - 6.0),), 2.4, r=0.6).translate(
        (0, 0, zb + 1.2))
    ch = (W - slot) / 2
    px, pz = x0 + 0.40 * L, zb + 0.56 * T
    prof = _ccw(np.array([[x0 + 2, zb], [x0 + 2, zb + 0.45 * T], [px - 5, zb + 0.9 * T], [px + 5, zb + 0.9 * T],
                          [x1 - 10, zb + 0.30 * T], [x1 - 6, zb]]))
    base = floor
    for sy in (1, -1):
        base = base + _side_profile(prof, ch, r=0.6, cy=sy * (W / 2 - ch / 2))
    pin = _cyl_y(1.6, W + 0.8, (px, 0, pz))
    a = np.radians(np.linspace(0, 360, 25)[:-1])
    lobe = np.column_stack([px + 5.2 * np.cos(a), pz + 5.2 * np.sin(a)])
    lever = _ccw(np.array([[px - 2, pz + 3.6], [px + 8, pz + 3.2], [x1 - 0.5, zb + T - 1.4], [x1, zb + T - 0.2],
                           [x1 - 1.5, zb + T], [px + 6, pz + 6.8], [px - 3, pz + 5.4]]))
    cam = _side_profile(lobe, slot - 1.0, r=0.5) + _side_profile(lever, slot - 1.0, r=0.6)
    for k in range(7):                                                               # teeth under the lobe
        y = (k - 3) * (slot - 3.0) / 7.0
        cam = cam + _box(3.5, 1.0, 1.0, (px + 1.0, y, pz - 5.3))
    return {"base": _to_mesh(base), "cam": _to_mesh(cam + pin)}


def _g_hook(sp):
    """Flat aluminium plate: closed slot for the sewn webbing at -x, hook slot at +x opened to the -y end."""
    L, W, T, slot = sp["L"], sp["W"], sp["T"], sp["slot"]
    s = 5.0
    closed = _rrect(s, slot, 1.6, cx=-L / 2 + 4.0 + s / 2)
    hx = L / 2 - 4.0 - s / 2
    hook = _rrect(s, slot, 1.6, cx=hx)
    m = _round_extrude(_rrect(L, W, 5.0), (closed, hook), T, r=0.9)
    m = m - _box(s - 0.4, (W - slot) / 2 + 3.0, T + 2, (hx, -W / 2 + (W - slot) / 4 - 0.5, 0))
    return {"body": _to_mesh(m)}


def _d_ring(sp):
    from . import tube
    sec, iw, ih = sp["sec"], sp["inner_w"], sp["inner_h"]
    r = sec / 2
    hw = iw / 2 + r
    x_bar = -(ih / 2 + r)
    rc = 2.5 + r
    pts = [[x_bar, -hw + rc], [x_bar, hw - rc]]
    for a in np.radians(np.linspace(180, 90, 6)[1:]):
        pts.append([x_bar + rc + rc * np.cos(a), hw - rc + rc * np.sin(a)])
    R = hw                                        # the bow: an ellipse arc from (x_bar + rc, +hw) round to -hw
    bow_x = ih + 2 * r - rc
    for a in np.radians(np.linspace(90, -90, 26)):
        pts.append([x_bar + rc + bow_x * np.cos(a) * (1 if True else 0), R * np.sin(a)])
    for a in np.radians(np.linspace(270, 180, 6)[1:-1]):
        pts.append([x_bar + rc + rc * np.cos(a), -hw + rc + rc * np.sin(a)])
    P = np.array(pts)
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2
    P3 = np.column_stack([P, np.zeros(len(P))])
    N = np.tile([0, 0, 1.0], (len(P3), 1))
    from . import circle_prof, sweep
    m = sweep(P3, N, circle_prof(r, 14), closed=True)
    _ = tube
    return {"body": m}


def _bag_hook(sp):
    """Rated bag hook: 4 mm plate, closed 38 mm webbing slot at -x, hook mouth at +x that drops over a 5 mm pin,
    spring gate (thin plate with a thumb nub) closing the mouth."""
    L, W, T, slot, mouth = sp["L"], sp["W"], sp["T"], sp["slot"], sp["mouth"]
    closed = _rrect(5.5, slot, 1.8, cx=-L / 2 + 5.0 + 2.75)
    eye_x = L / 2 - 14.0
    eye = _rrect(mouth + 5.0, 20.0, 3.2, cx=eye_x)
    m = _round_extrude(_rrect(L, W, 7.0), (closed, eye), T, r=1.0)
    m = m - _box(mouth, 16.0, T + 2, (eye_x + 1.5, -W / 2 + 6.0, 0))                 # mouth open to the -y edge
    gate = _round_extrude(_rrect(mouth + 9.0, 15.0, 2.0, cx=eye_x + 1.0, cy=-W / 2 + 12.0), (), 1.2, r=0.4) \
        .translate((0, 0, T / 2 + 0.6))
    nub = _rbox(4.0, 7.0, 2.2, 0.6, (eye_x + 1.0, -W / 2 + 12.0, T / 2 + 1.8), rp=1.5)
    rivet = _cyl_y(1.6, 2.0, (0, 0, 0)).rotate((90.0, 0, 0)).translate((eye_x - mouth / 2 - 5.0, -W / 2 + 18.0,
                                                                         T / 2 + 1.0))
    return {"body": _to_mesh(m), "gate": _to_mesh(gate + nub + rivet)}


def _zip_slider(sp):
    """Coil slider: shield-shaped top and bottom plates joined by the front diamond, side flanges, pull bridge.
    +x = the direction the slider moves to CLOSE the zip (the diamond / two-throat end leads)."""
    W, L, T, throat = sp["W"], sp["L"], sp["T"], sp["throat"]
    x0, x1 = -L / 2, L / 2
    hw, nk = W / 2, throat / 2 + 1.3
    sh = np.array([[x1, hw * 0.78], [x1 - 0.16 * L, hw], [x1 - 0.45 * L, hw], [x0 + 0.22 * L, nk], [x0, nk]])
    plan = _ccw(np.vstack([sh, sh[::-1] * [1, -1]]))
    tp = 1.25
    body_T = T - 2.6                                              # plates + chain gap; the bridge adds 2.6 on top
    zc = -T / 2 + body_T / 2
    top = _round_extrude(plan, (), tp, r=0.45).translate((0, 0, zc + body_T / 2 - tp / 2))
    bot = _round_extrude(plan, (), tp, r=0.45).translate((0, 0, zc - body_T / 2 + tp / 2))
    dia = _round_extrude(_ccw(np.array([[x1 - 0.6, 0], [x1 - 0.30 * L, 1.7], [x1 - 0.50 * L, 0],
                                        [x1 - 0.30 * L, -1.7]])), (), body_T - 0.6, r=0.25).translate((0, 0, zc))
    out = top + bot + dia
    for sy in (1, -1):                                            # side flanges on the top plate
        fl = _ccw(np.array([[x1 - 0.42 * L, sy * hw], [x0 + 0.22 * L, sy * nk], [x0, sy * nk], [x0, sy * (nk - 1.1)],
                            [x0 + 0.22 * L, sy * (nk - 1.1)], [x1 - 0.42 * L, sy * (hw - 1.1)]]))
        out = out + _round_extrude(fl, (), body_T * 0.36, r=0.2).translate((0, 0, zc + body_T / 2 - body_T * 0.18 - 0.4))
    zt = zc + body_T / 2 - 0.4
    br = _ccw(np.array([[x1 - 0.22 * L, zt], [x1 - 0.30 * L, zt + 2.9], [x0 + 0.30 * L, zt + 2.9],
                        [x0 + 0.14 * L, zt], [x0 + 0.30 * L, zt], [x0 + 0.36 * L, zt + 1.6],
                        [x1 - 0.36 * L, zt + 1.6], [x1 - 0.34 * L, zt]]))
    out = out + _side_profile(br, max(2.6, 0.26 * W), r=0.35)
    return {"body": _to_mesh(out)}


def _zip_pull(sp):
    """Flat pull tab with the eye that hangs in the slider bridge and a finger hole."""
    W, L, T = sp["W"], sp["L"], sp["T"]
    eye = _rrect(3.4, W * 0.55, 1.2, cx=L / 2 - 3.0)
    hole = _rrect(L * 0.34, W * 0.44, 1.6, cx=-L / 2 + L * 0.30)
    pl = _ccw(np.array([[L / 2, W * 0.36], [L / 2 - 6.0, W * 0.36], [-L / 2 + L * 0.5, W / 2], [-L / 2 + 2.5, W / 2],
                        [-L / 2, W / 2 - 2.5], [-L / 2, -W / 2 + 2.5], [-L / 2 + 2.5, -W / 2],
                        [-L / 2 + L * 0.5, -W / 2], [L / 2 - 6.0, -W * 0.36], [L / 2, -W * 0.36]]))
    return {"body": _to_mesh(_round_extrude(pl, (eye, hole), T, r=0.5))}


def _cord_lock(sp):
    """Barrel body with the cord hole across it (y) and the sprung plunger out of the -x end."""
    L, W, T, hole = sp["L"], sp["W"], sp["T"], sp["hole"]
    Lb = L - 6.0
    body = _rbox(Lb, W, T, 2.4, (L / 2 - Lb / 2, 0, 0), rp=5.0)
    body = body - _cyl_y(hole / 2, W + 4, (L / 2 - Lb * 0.52, 0, 0))
    plunger = _rbox(9.0, W * 0.62, T * 0.62, 1.6, (-L / 2 + 4.5, 0, 0), rp=3.0)
    plunger = plunger - _cyl_y(hole / 2, W + 4, (L / 2 - Lb * 0.52, 0, 0))
    grip = _rbox(Lb * 0.42, W * 0.5, 0.9, 0.3, (L / 2 - Lb * 0.30, 0, T / 2), rp=2.0)
    return {"body": _to_mesh(body - grip), "plunger": _to_mesh(plunger)}


_BUILDERS = {"side_release": _side_release, "ladder_lock": _ladder_lock, "tri_glide": _tri_glide,
             "cam_buckle": _cam_buckle, "g_hook": _g_hook, "d_ring": _d_ring, "bag_hook": _bag_hook,
             "zip_slider": _zip_slider, "zip_pull": _zip_pull, "cord_lock": _cord_lock}


def _family(kind):
    for f in sorted(_BUILDERS, key=len, reverse=True):
        if kind.startswith(f):
            return f
    raise KeyError(f"unknown hardware kind {kind!r}; kinds: {sorted(SPECS)}")


@lru_cache(maxsize=None)
def components(kind: str) -> dict:
    """{component name: trimesh} for one kind, centred on the assembly's bounding box (local frame, mm)."""
    comps = _BUILDERS[_family(kind)](SPECS[kind])
    allv = np.vstack([m.vertices for m in comps.values()])
    c = (allv.min(0) + allv.max(0)) / 2
    for m in comps.values():
        m.vertices = m.vertices - c
    return comps


def build(kind: str, part: str | None = None):
    """One mesh for ``kind`` (all components, or the one named ``part``: e.g. ``female`` / ``male``)."""
    comps = components(kind)
    if part is not None:
        return comps[part].copy()
    return concat([m.copy() for m in comps.values()])


def envelope(kind: str):
    """(L, W, T) of the built mesh, mm."""
    m = build(kind)
    return tuple(float(v) for v in (m.vertices.max(0) - m.vertices.min(0)))


def place(kind: str, p, n, t, part: str | None = None, lift: float = 0.0):
    """``kind`` at point p (its centre), surface normal n, strap direction t (FCS mm)."""
    R = frame(n, t)
    return placed(build(kind, part), R, np.asarray(p, float) + lift * R[:, 2])


def is_watertight(m) -> bool:
    """Every connected component closed and consistently wound."""
    import trimesh
    tm = trimesh.Trimesh(m.vertices, m.faces, process=False)
    return all(c.is_watertight and c.is_winding_consistent for c in tm.split(only_watertight=False))


def library_glb(path=None, kinds=None) -> Path:
    """Write (or reuse) the GLB library: one node per ``kind/component``, mm, local frame. About 1 MB; cached in
    ``outputs/viz3d_assets/`` (untracked), rebuilt when this file or a hardware record is newer."""
    import trimesh
    path = Path(path) if path else REPO / "outputs" / "viz3d_assets" / "hardware.glb"
    srcs = [Path(__file__)] + sorted((REPO / "data" / "materials" / "hardware").glob("*.yaml"))
    if path.exists() and all(path.stat().st_mtime >= s.stat().st_mtime for s in srcs) and kinds is None:
        return path
    sc = trimesh.Scene()
    for k in (kinds or sorted(SPECS)):
        for cn, m in components(k).items():
            sc.add_geometry(trimesh.Trimesh(m.vertices, m.faces, process=False), node_name=f"{k}/{cn}",
                            geom_name=f"{k}/{cn}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sc.export(file_type="glb"))
    return path


def spec_table() -> str:
    """Markdown table of every dimension and its source (for the design doc)."""
    rows = ["| Kind | L x W x T mm (in) | Slot / key mm | Sources |", "|---|---|---|---|"]
    for k in sorted(SPECS):
        sp = SPECS[k]
        L, W, T = envelope(k)
        key = sp.get("slot", sp.get("throat", sp.get("hole", sp.get("inner_w", ""))))
        rec = sorted({v for v in sp["src"].values() if v.startswith("record") or "md" in v})
        est = sorted(kk for kk, v in sp["src"].items() if v == A)
        rows.append(f"| {k} | {L:.1f} x {W:.1f} x {T:.1f} ({L / 25.4:.2f} x {W / 25.4:.2f} x {T / 25.4:.2f}) | {key} | "
                    f"{'; '.join(rec) or '-'}; ASSUMPTION: {', '.join(est) or 'none'} |")
    return "\n".join(rows)
