"""CORRIE E for the cloth sim (huntkit.clothsim), Team A EVOLVE. It IMPORTS CORRIE's loader
(huntkit/clothsim/corrie_bag.py: ``BoxSurface``, ``_line``, ``_rect``, the piece layout and the B-06 closure) and only
changes what CORRIE E changes:

* the surface: rounded aft corners R 40 (E-1) and the shoulder taper (E-2), via ``RoundedSurface(BoxSurface)``;
  q convention as CORRIE (outer half 0..1: right gusset 0..1/3, aft panel incl. both corner arcs 1/3..2/3, left
  gusset 2/3..1; frame face 1..2). On the aft panel U is arc length, so the door inset (45 mm) is along the surface;
* the camo tub wall ``B-05w`` (E-3): z 35 -> 95 round the outer three sides; gussets and the U-surround start at z 95;
* the floor ``B-05``: rounded aft corners; the door: sill z 130 (``evolve.DOOR``).

The sim selects a bag by name (``bag: corrie``), so ``patched()`` points corrie_bag.load_corrie_patterns at
``load_evolve_patterns`` for the duration of a run (huntkit is not edited).

    python designs/pack_5200/bag_comp/A/evolve_bag.py run --torso 19 [--cases packed,fill,meat] [--fine]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evolve as E  # noqa: E402

from huntkit.clothsim import corrie_bag as CB  # noqa: E402
from huntkit.clothsim.assemble import densify  # noqa: E402

US = CB.US
ROOT = E.ROOT
SCEN_DIR = HERE / "scenarios"
OUT_DIR = ROOT / "outputs" / "clothsim"


class RoundedSurface(CB.BoxSurface):
    """CORRIE's BoxSurface with R aft corners: (U, z) -> xyz."""

    def __init__(self, c, BC, r=E.R_AFT):
        super().__init__(c, BC)
        self.r = r

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        q = np.mod(uv[:, 0] / US, 2.0)
        z = uv[:, 1]
        a, yf, d = self.env(z)
        r = np.minimum(self.r, 0.45 * d)
        x = np.zeros_like(q)
        y = np.zeros_like(q)
        m = q < 1 / 3                                     # right gusset: frame corner -> side tangent
        t = q[m] * 3
        x[m], y[m] = a[m], yf[m] + (d[m] - r[m]) * t
        m = (q >= 1 / 3) & (q < 2 / 3)                    # aft panel: arc R, flat, arc L (arc length param)
        t = q[m] * 3 - 1
        am, ym, dm, rm = a[m], yf[m], d[m], r[m]
        L = 2 * (am - rm) + np.pi * rm
        s = t * L
        arc = np.pi * rm / 2
        xx = np.zeros_like(s)
        yy = np.zeros_like(s)
        k = s < arc
        ph = s[k] / rm[k]
        xx[k] = am[k] - rm[k] + rm[k] * np.cos(ph)
        yy[k] = ym[k] + dm[k] - rm[k] + rm[k] * np.sin(ph)
        k2 = (s >= arc) & (s <= L - arc)
        xx[k2] = am[k2] - rm[k2] - (s[k2] - arc[k2])
        yy[k2] = ym[k2] + dm[k2]
        k3 = s > L - arc
        ph = (L[k3] - s[k3]) / rm[k3]
        xx[k3] = -(am[k3] - rm[k3] + rm[k3] * np.cos(ph))
        yy[k3] = ym[k3] + dm[k3] - rm[k3] + rm[k3] * np.sin(ph)
        x[m], y[m] = xx, yy
        m = (q >= 2 / 3) & (q < 1)                        # left gusset: side tangent -> frame corner
        t = q[m] * 3 - 2
        x[m], y[m] = -a[m], yf[m] + (d[m] - r[m]) * (1 - t)
        m = q >= 1
        t = q[m] - 1
        x[m], y[m] = -a[m] + 2 * a[m] * t, yf[m]
        return np.column_stack([x, y, z])

    def aft_len(self, z):
        a, _, d = (float(v[0]) for v in self.env([z]))
        r = min(self.r, 0.45 * d)
        return 2 * (a - r) + math.pi * r

    def u_of_s_aft(self, s, z):
        """U of a point s mm along the aft panel surface from the RIGHT side tangent."""
        return US * (1 / 3 + s / self.aft_len(z) / 3)


def door_uv(S, door=None):
    """Door U (as corrie_bag.door_uv): from the hinge on the left, down, round both R 60 corners, up the right side;
    the zip lies ``inset`` mm along the surface from each side tangent."""
    H = door or E.DOOR
    zz = np.linspace(H["z_hinge"], H["z_lo"] + H["r"], 30)
    pts = [(S.u_of_s_aft(S.aft_len(z) - H["inset"], z), z) for z in zz]
    zc = H["z_lo"] + H["r"]
    Lc = S.aft_len(zc)
    th = np.linspace(0, np.pi / 2, 10)
    for t in th:                                          # lower-left corner (large s)
        s = Lc - H["inset"] - H["r"] + H["r"] * np.cos(t)
        pts.append((S.u_of_s_aft(s, zc - H["r"] * np.sin(t)), zc - H["r"] * np.sin(t)))
    for t in th[::-1]:                                    # lower-right corner (small s)
        s = H["inset"] + H["r"] - H["r"] * np.cos(t)
        pts.append((S.u_of_s_aft(s, zc - H["r"] * np.sin(t)), zc - H["r"] * np.sin(t)))
    for z in zz[::-1]:
        pts.append((S.u_of_s_aft(H["inset"], z), z))
    out = [pts[0]]
    for p, q in zip(pts[:-1], pts[1:]):
        out += CB._line(p, q, 4.0)[1:]
    return out


def load_evolve_patterns(verbose=True) -> dict:
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    BC, CO = CB._concept()
    c = E.make()
    S = RoundedSurface(c, BC)
    z0, zc = float(BC.Z0), float(c.z_c)
    zt = z0 + E.TUB_H
    H = E.DOOR
    zh = H["z_hinge"]
    du = door_uv(S, H)
    _line, _rect = CB._line, CB._rect
    regions = {
        "B-01": _rect(US, 2 * US, z0, zc),
        "B-03": _rect(0.0, US / 3, zt, zc),
        "B-05w": _rect(0.0, US, z0, zt),
        "B-02h": _rect(US / 3, 2 * US / 3, zh, zc),
        "B-02door": [("hinge", _line(du[0], du[-1])), ("zip", du[::-1])],
        "B-02u": [("bottom", _line((US / 3, zt), (2 * US / 3, zt))), ("outer_left", _line((2 * US / 3, zt), (2 * US / 3, zh))),
                  ("top_left", _line((2 * US / 3, zh), du[0])), ("zip", du), ("top_right", _line(du[-1], (US / 3, zh))),
                  ("outer_right", _line((US / 3, zh), (US / 3, zt)))],
    }
    names = {"B-01": ("frame-side panel", "challenge_ultra_200"), "B-03": ("side gusset", "cordura_330d_nylon66"),
             "B-05w": ("camo tub wall (500D printed)", E.TUB_MAT),
             "B-02h": ("hinge band", "cordura_330d_nylon66"), "B-02door": ("horseshoe door", "cordura_330d_nylon66"),
             "B-02u": ("U-surround", "cordura_330d_nylon66")}
    out = {"pieces": {}, "constants": {}, "dev_ids": list(regions),
           "release": "concept: designs/pack_5200/bag_comp/A/evolve.py (CORRIE E)"}
    for pid, edges in regions.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.geom_type != "Polygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        fine = pid in ("B-02u", "B-05w")
        fm = develop_region(S, poly, spacing=7.0 if fine else 14.0, boundary_spacing=3.5 if fine else 5.0,
                            boundary_weight=100.0)
        Ed = []
        for nm, uv in edges:
            uvd = densify(np.asarray(uv, float), 2.0)
            Ed.append((nm, np.asarray(fm.map_uv(uvd)), np.asarray(S(uvd))))
        lab, mid = names[pid]
        out["pieces"][pid] = {"kind": "dev", "name": lab, "material_id": mid, "grain": 90.0, "V2": np.asarray(fm.V2),
                              "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris), "edges": Ed,
                              "strain_p99": fm.strain_stats()["p99_pct"]}
    # floor at z0, rounded aft corners: edges from the surface itself so they coincide with B-05w / B-01
    def fl_edge(q0, q1, n):
        P3 = np.asarray(S(np.column_stack([np.linspace(q0, q1, n) * US, np.full(n, z0)])))
        return np.column_stack([-P3[:, 0], P3[:, 1]]), P3
    e05 = []
    for nm, q0, q1, n in (("frame", 1.0, 2.0 - 1e-9, 200), ("right", 0.0, 1 / 3, 60), ("aft", 1 / 3, 2 / 3, 240),
                          ("left", 2 / 3, 1.0 - 1e-9, 60)):
        fl, P3 = fl_edge(q0, q1, n)
        e05.append((nm, fl, P3))
    # loop order: frame (-x -> +x), right (frame corner -> tangent), aft (+x -> -x), left (tangent -> frame corner)
    out["pieces"]["B-05"] = {"kind": "floor", "name": "bottom (rounded aft corners)", "material_id": "cordura_500d_nylon66",
                             "grain": 90.0, "edges": e05, "z0": z0}
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


@contextlib.contextmanager
def patched():
    old = CB.load_corrie_patterns
    CB.load_corrie_patterns = load_evolve_patterns
    try:
        yield
    finally:
        CB.load_corrie_patterns = old


def scenario_file(torso: int) -> Path:
    return SCEN_DIR / f"evolve_PR{torso}.yaml"


def run(torso: int, cases=None, fine=False, tag="", time_cap=None, scen=None):
    from huntkit.clothsim import cli
    a = argparse.Namespace(scenario=str(scen or scenario_file(torso)), time_cap=time_cap, out=str(OUT_DIR / f"bagA_evolve_PR{torso}{tag}"),
                           fine=fine, cases=cases, verbose=False, no_render=True, no_sweep=True, screens=None, date=None)
    with patched():
        cli.cmd_run(a)
    f = Path(a.out) / "results.json"
    r = json.loads(f.read_text())
    r["source"]["patterns"] = "designs/pack_5200/bag_comp/A/evolve.py via evolve_bag.py (imports huntkit/clothsim/corrie_bag.py)"
    f.write_text(json.dumps(r, indent=1))
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "check"])
    ap.add_argument("--torso", type=int, default=19)
    ap.add_argument("--cases", default=None)
    ap.add_argument("--fine", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--scen", default=None)
    a = ap.parse_args()
    if a.cmd == "check":
        t = time.time()
        p = load_evolve_patterns()
        print({k: (v.get("strain_p99"), len(v.get("edges", []))) for k, v in p["pieces"].items()}, time.time() - t)
    else:
        run(a.torso, a.cases, a.fine, a.tag, scen=a.scen)
