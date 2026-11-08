"""CORRIE bag for the cloth sim: the concept's flat pieces as the pattern dict ``pack.load_patterns`` returns.

Scenario key ``bag: corrie`` selects it (``pack.PackModel``). Pieces (same role names the sim attaches to):

* B-01   frame-side panel (dev): hinge eyes, hook tabs, hood band and meat face load act on it
* B-03   right side gusset (dev, mirrored to B-03L by ``piece_specs``)
* B-02u, B-02door, B-02h  aft face: U-surround, horseshoe door (its zip modelled as a sewn seam: closed), hinge band
* B-05   floor 272 x 190 at z 35
* B-06   roll-top collar from the collar seam (z 736.3) to the fill line, closed flat (the rolled closure)

The 3D start shape is CORRIE's box envelope (``designs/pack_5200/concepts/corrie.py``): planar facets, so every piece
develops with ~0 strain (``develop_region`` on a piecewise-planar surface). The cloth sim rounds the corners and puts
the fabric in tension under the fill. Wings, pouch, swells, tabs and binding are not modelled (as for SPINE).
"""
from __future__ import annotations

import sys

import numpy as np

from .assemble import densify
from .pack import PACK

US = 600.0


def _concept():
    sys.path.insert(0, str(PACK / "concepts"))
    sys.path.insert(0, str(PACK))
    import bag_concepts as BC  # noqa: E402
    import corrie as CO  # noqa: E402
    return BC, CO


class BoxSurface:
    """(U, z) -> xyz on CORRIE's box. q = U / 600: outer half 0..1 = right gusset (0..1/3, frame corner -> aft
    corner), aft face (1/3..2/3, +x -> -x), left gusset (2/3..1); frame half 1..2 = frame face (-x -> +x).
    Same convention as patterns_v31.MasterSurface (q 1.5 = frame-face centre)."""

    def __init__(self, c, BC):
        self.c, self.BC = c, BC

    def env(self, z):
        z = np.clip(np.asarray(z, float), self.BC.Z0, self.c.z_c)
        return self.c.a(z), self.BC.y_frame(z), self.c.depth(z)

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        q = np.mod(uv[:, 0] / US, 2.0)
        z = uv[:, 1]
        a, yf, d = self.env(z)
        x = np.zeros_like(q)
        y = np.zeros_like(q)
        m = q < 1 / 3
        t = q[m] * 3
        x[m], y[m] = a[m], yf[m] + d[m] * t
        m = (q >= 1 / 3) & (q < 2 / 3)
        t = q[m] * 3 - 1
        x[m], y[m] = a[m] - 2 * a[m] * t, yf[m] + d[m]
        m = (q >= 2 / 3) & (q < 1)
        t = q[m] * 3 - 2
        x[m], y[m] = -a[m], yf[m] + d[m] * (1 - t)
        m = q >= 1
        t = q[m] - 1
        x[m], y[m] = -a[m] + 2 * a[m] * t, yf[m]
        return np.column_stack([x, y, z])

    def u_of_x_aft(self, x, z):
        a = float(self.c.a([min(z, self.c.z_c)])[0])
        return US * (1 / 3 + (a - x) / (2 * a) / 3)


def _line(a, b, step=4.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
    return [tuple(a + (b - a) * i / n) for i in range(n + 1)]


def _rect(u0, u1, z0, z1):
    return [("bottom", _line((u0, z0), (u1, z0))), ("right", _line((u1, z0), (u1, z1))),
            ("top", _line((u1, z1), (u0, z1))), ("left", _line((u0, z1), (u0, z0)))]


def door_uv(S, CO):
    """Door U (CCW on the door): down the left side, round the lower-left corner, across, up the right side; in (U, z)."""
    H = CO.DOOR
    c = S.c
    pts = []
    zz = np.linspace(H["z_hinge"], H["z_lo"] + H["r"], 30)
    for z in zz:                                            # left side (x < 0 -> larger U), going down
        a = float(c.a([z])[0]) - H["inset"]
        pts.append((S.u_of_x_aft(-a, z), z))
    th = np.linspace(0, np.pi / 2, 10)
    a_c = float(c.a([H["z_lo"] + H["r"]])[0]) - H["inset"]
    for t in th:                                            # lower-left corner
        x = -(a_c - H["r"] + H["r"] * np.cos(t))
        z = H["z_lo"] + H["r"] - H["r"] * np.sin(t)
        pts.append((S.u_of_x_aft(x, z), z))
    for t in th[::-1]:                                      # lower-right corner
        x = a_c - H["r"] + H["r"] * np.cos(t)
        z = H["z_lo"] + H["r"] - H["r"] * np.sin(t)
        pts.append((S.u_of_x_aft(x, z), z))
    for z in zz[::-1]:                                      # right side going up
        a = float(c.a([z])[0]) - H["inset"]
        pts.append((S.u_of_x_aft(a, z), z))
    # densify
    out = [pts[0]]
    for p, q in zip(pts[:-1], pts[1:]):
        out += _line(p, q, 4.0)[1:]
    return out


def load_corrie_patterns(verbose=True) -> dict:
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    BC, CO = _concept()
    c = CO.make()
    S = BoxSurface(c, BC)
    z0, zc = float(BC.Z0), float(c.z_c)
    H = CO.DOOR
    zh = H["z_hinge"]
    du = door_uv(S, CO)                       # from the hinge-left point, round the U, to the hinge-right point
    regions = {
        "B-01": _rect(US, 2 * US, z0, zc),
        "B-03": _rect(0.0, US / 3, z0, zc),
        "B-02h": _rect(US / 3, 2 * US / 3, zh, zc),
        "B-02door": [("hinge", _line(du[0], du[-1])), ("zip", du[::-1])],
        "B-02u": [("bottom", _line((US / 3, z0), (2 * US / 3, z0))), ("outer_left", _line((2 * US / 3, z0), (2 * US / 3, zh))),
                  ("top_left", _line((2 * US / 3, zh), du[0])), ("zip", du), ("top_right", _line(du[-1], (US / 3, zh))),
                  ("outer_right", _line((US / 3, zh), (US / 3, z0)))],
    }
    names = {"B-01": ("frame-side panel", "challenge_ultra_200"), "B-03": ("side gusset", "cordura_330d_nylon66"),
             "B-02h": ("hinge band", "cordura_330d_nylon66"), "B-02door": ("horseshoe door", "cordura_330d_nylon66"),
             "B-02u": ("U-surround", "cordura_330d_nylon66")}
    out = {"pieces": {}, "constants": {}, "dev_ids": list(regions), "release": "concept: designs/pack_5200/concepts/corrie.py"}
    for pid, edges in regions.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.geom_type != "Polygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        sp = 7.0 if pid == "B-02u" else 14.0          # the 45 mm surround strips need a finer mesh
        fm = develop_region(S, poly, spacing=sp, boundary_spacing=3.5 if pid == "B-02u" else 5.0, boundary_weight=100.0)
        E = []
        for nm, uv in edges:
            uvd = densify(np.asarray(uv, float), 2.0)
            E.append((nm, np.asarray(fm.map_uv(uvd)), np.asarray(S(uvd))))
        lab, mid = names[pid]
        out["pieces"][pid] = {"kind": "dev", "name": lab, "material_id": mid, "grain": 90.0, "V2": np.asarray(fm.V2),
                              "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris), "edges": E,
                              "strain_p99": fm.strain_stats()["p99_pct"]}
    # floor at z0: flat coords such that 3D = (-x, y, z0) (pack.piece_specs floor map)
    a0, yf0, d0 = (float(v[0]) for v in S.env([z0]))
    corners = [(-a0, yf0), (a0, yf0), (a0, yf0 + d0), (-a0, yf0 + d0)]
    e05 = []
    for nm, (p, q) in zip(("frame", "right", "aft", "left"), zip(corners, corners[1:] + corners[:1])):
        P3 = densify(np.array([p, q], float), 2.0)
        fl = np.column_stack([-P3[:, 0], P3[:, 1]])
        e05.append((nm, fl, np.column_stack([P3[:, 0], P3[:, 1], np.full(len(P3), z0)])))
    out["pieces"]["B-05"] = {"kind": "floor", "name": "bottom", "material_id": "cordura_500d_nylon66", "grain": 90.0,
                             "edges": e05, "z0": z0}
    t = np.linspace(0, 2, 4001)
    q = np.mod(1.5 + t, 2.0)
    ring = np.asarray(S(np.column_stack([q * US, np.full(len(q), zc)])))
    s3 = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    out["pieces"]["B-06"] = {"kind": "collar", "name": "roll-top collar", "material_id": "robic_100d_ripstop",
                             "grain": 90.0, "perimeter": float(s3[-1]), "ring": ring, "ring_s": s3,
                             "height_to_fill": float(c.dome_h), "z_collar": zc}
    qg = np.linspace(0, 2, 401)
    zg = np.linspace(z0, zc, 120)
    QQ, ZZ = np.meshgrid(qg, zg, indexing="ij")
    out["surface"] = {"q": qg, "z": zg, "xyz": np.asarray(S(np.column_stack([QQ.ravel() * US, ZZ.ravel()]))).reshape(
        len(qg), len(zg), 3)}
    out["constants"] = {"Z0": z0, "Z_COLLAR": zc, "Z_FILL": float(c.z_fill), "Z_SB": float(BC.Z_SB),
                        "Z_SH": float(BC.Z_SH), "design_volume_L": float(c.volume_L()), "pattern_volume_L_release": None,
                        "strain_p99": {k: v["strain_p99"] for k, v in out["pieces"].items() if v["kind"] == "dev"}}
    return out
