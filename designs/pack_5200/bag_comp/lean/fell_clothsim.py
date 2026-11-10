"""FELL in the cloth sim (huntkit.clothsim): pattern loader + runner. Team B LEAN, 2026-11-10.

    python designs/pack_5200/bag_comp/lean/fell_clothsim.py 15 19 23          # coarse CG runs (fill, meat)
    python designs/pack_5200/bag_comp/lean/fell_clothsim.py 19 --fine --cases packed   # one fine drape for renders

The shell is CORRIE rev B's box (same envelope as huntkit/clothsim/corrie_bag.py) with FELL's aft face: two halves
B-02R / B-02L joined by the centre seam (the #10 zip is modelled closed, as a sewn seam, as CORRIE's door zip was).
huntkit is not edited: the scenario keeps ``bag: corrie`` and this module swaps the pattern loader in at run time.

Fabric models: the sim's fabrics.yaml has no ULTRAGrid or 70D entry, so each piece uses the nearest modelled fabric
scaled by the record ratios (scenario ``panels`` *_scale keys, the sim's own mechanism):
* ULTRAGrid -> cordura_330d_nylon66 x grab 1300/1000 (warp), 1100/800 (weft), areal 132/180 (records; the same
  ASSUMPTION break elongation as 330D);
* 70D collar -> robic_100d_ripstop x grab 242/550, 174/450, areal 92/125;
* ULTRA 200X bottom -> challenge_ultra_200 (modelled directly).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from huntkit.clothsim import corrie_bag as CB  # noqa: E402
from huntkit.clothsim.assemble import densify  # noqa: E402

SCEN_DIR = HERE / "scenarios"


def load_fell_patterns(verbose=True) -> dict:
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    import fell as F
    BC, CO = CB._concept()
    c = F.make()
    S = CB.BoxSurface(c, BC)
    US = CB.US
    z0, zc = float(BC.Z0), float(c.z_c)
    um = US / 2.0                                   # aft-face centre (q = 0.5)
    regions = {
        "B-01": CB._rect(US, 2 * US, z0, zc),
        "B-03": CB._rect(0.0, US / 3, z0, zc),
        "B-02R": CB._rect(US / 3, um, z0, zc),
        "B-02L": CB._rect(um, 2 * US / 3, z0, zc),
    }
    names = {"B-01": ("frame-side panel", "challenge_ultra_200"),
             "B-03": ("side gusset (ULTRAGrid, 330D model scaled)", "cordura_330d_nylon66"),
             "B-02R": ("aft half R (ULTRAGrid, 330D model scaled)", "cordura_330d_nylon66"),
             "B-02L": ("aft half L (ULTRAGrid, 330D model scaled)", "cordura_330d_nylon66")}
    out = {"pieces": {}, "constants": {}, "dev_ids": list(regions),
           "release": "concept: designs/pack_5200/bag_comp/lean/fell.py (FELL)"}
    for pid, edges in regions.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        fm = develop_region(S, poly, spacing=14.0, boundary_spacing=5.0, boundary_weight=100.0)
        E = []
        for nm, uv in edges:
            uvd = densify(np.asarray(uv, float), 2.0)
            E.append((nm, np.asarray(fm.map_uv(uvd)), np.asarray(S(uvd))))
        lab, mid = names[pid]
        out["pieces"][pid] = {"kind": "dev", "name": lab, "material_id": mid, "grain": 90.0, "V2": np.asarray(fm.V2),
                              "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris), "edges": E,
                              "strain_p99": fm.strain_stats()["p99_pct"]}
    a0, yf0, d0 = (float(v[0]) for v in S.env([z0]))
    corners = [(-a0, yf0), (a0, yf0), (a0, yf0 + d0), (-a0, yf0 + d0)]
    e05 = []
    for nm, (p, q) in zip(("frame", "right", "aft", "left"), zip(corners, corners[1:] + corners[:1])):
        P3 = densify(np.array([p, q], float), 2.0)
        fl = np.column_stack([-P3[:, 0], P3[:, 1]])
        e05.append((nm, fl, np.column_stack([P3[:, 0], P3[:, 1], np.full(len(P3), z0)])))
    out["pieces"]["B-05"] = {"kind": "floor", "name": "bottom (ULTRA 200X)", "material_id": "challenge_ultra_200",
                             "grain": 90.0, "edges": e05, "z0": z0}
    t = np.linspace(0, 2, 4001)
    q = np.mod(1.5 + t, 2.0)
    ring = np.asarray(S(np.column_stack([q * US, np.full(len(q), zc)])))
    s3 = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    out["pieces"]["B-06"] = {"kind": "collar", "name": "roll-top collar (70D, Robic model scaled)",
                             "material_id": "robic_100d_ripstop", "grain": 90.0, "perimeter": float(s3[-1]),
                             "ring": ring, "ring_s": s3, "height_to_fill": float(c.dome_h), "z_collar": zc}
    qg = np.linspace(0, 2, 401)
    zg = np.linspace(z0, zc, 120)
    QQ, ZZ = np.meshgrid(qg, zg, indexing="ij")
    out["surface"] = {"q": qg, "z": zg, "xyz": np.asarray(S(np.column_stack([QQ.ravel() * US, ZZ.ravel()]))).reshape(
        len(qg), len(zg), 3)}
    out["constants"] = {"Z0": z0, "Z_COLLAR": zc, "Z_FILL": float(c.z_fill), "Z_SB": float(BC.Z_SB),
                        "Z_SH": float(BC.Z_SH), "design_volume_L": float(c.volume_L()), "pattern_volume_L_release": None,
                        "strain_p99": {k: v["strain_p99"] for k, v in out["pieces"].items() if v["kind"] == "dev"}}
    return out


def install():
    CB.load_corrie_patterns = load_fell_patterns


def run(torso: int, fine=False, cases=None, tag=""):
    install()
    from huntkit.clothsim import cli
    name = f"fell_PR{torso}{tag}"
    a = argparse.Namespace(scenario=str(SCEN_DIR / f"fell_PR{torso}.yaml"), time_cap=None,
                           out=str(ROOT / "outputs" / "clothsim" / name), fine=fine, cases=cases, verbose=False,
                           no_render=True, no_sweep=True, screens=None, date=None)
    return cli.cmd_run(a)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("torsos", nargs="+", type=int)
    ap.add_argument("--fine", action="store_true")
    ap.add_argument("--cases", default=None)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    for t in a.torsos:
        run(t, a.fine, a.cases, a.tag)
