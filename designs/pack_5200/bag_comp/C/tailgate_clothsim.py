"""TAILGATE (team C) in the cloth sim: CORRIE's box body with the tailgate aft face (lid B-02L hinged at the floor
seam, inverted-U zip modelled closed as a sewn seam, hinge band B-02h with corner tongues) and the lid straps H1-H3.

    python designs/pack_5200/bag_comp/C/tailgate_clothsim.py run <scenario.yaml> [--fine] [--cases fill,meat]
    python designs/pack_5200/bag_comp/C/tailgate_clothsim.py all          # the coarse CG set + the strap-off control

The pattern loader follows huntkit/clothsim/corrie_bag.py (read only, imported) and is handed to the unchanged
``huntkit.clothsim`` by replacing ``corrie_bag.load_corrie_patterns`` IN THIS PROCESS ONLY (scenarios say
``bag: corrie``; no shared module is edited). The lid straps are the sim's ``wraps`` (cinched 25 mm webbing between
two fixed anchors): ASSUMPTION, anchored at the frame-side corners (the sim's wraps need fixed anchors; the real lid
straps end on gusset loops 15 mm forward of the zip, which the frame-side corner holds through the gusset). That
models the question asked: how much of the lid's hoop load the straps take off the corner zip legs.
Outputs: outputs/clothsim/bagC_<scenario>/ (results.json, x_<case>.npy).
"""
from __future__ import annotations

import math
import os
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
SIM_OUT = ROOT / "outputs" / "clothsim"
US = CB.US


def lid_uv(S, CO, LID):
    """Zip line in (U, z): from the right floor corner up the right aft corner seam to z_top - r, R arc onto the aft
    face, across at z_top, arc, down the left corner seam to the left floor corner."""
    c = S.c
    zt, r = LID["z_top"], LID["r"]
    z0 = float(S.BC.Z0)
    pts = []
    for z in np.linspace(z0, zt - r, 40):                       # right leg (x = +a: U = US/3)
        pts.append((US / 3, z))
    a_c = float(c.a([zt - r])[0])
    for t in np.linspace(0, math.pi / 2, 12)[1:]:
        x = a_c - r + r * math.cos(t)
        z = zt - r + r * math.sin(t)
        pts.append((S.u_of_x_aft(x, z), z))
    for t in np.linspace(math.pi / 2, math.pi, 12)[1:]:
        x = -(a_c - r) + r * math.cos(t)
        z = zt - r + r * math.sin(t)
        pts.append((S.u_of_x_aft(x, z), z))
    for z in np.linspace(zt - r, z0, 40)[1:]:
        pts.append((2 * US / 3, z))
    out = [pts[0]]
    for p, q in zip(pts[:-1], pts[1:]):
        out += CB._line(p, q, 4.0)[1:]
    return out


def load_tailgate_patterns(verbose=True) -> dict:
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    import tailgate as TG
    BC, CO = CB._concept()
    c = CO.make()
    S = CB.BoxSurface(c, BC)
    S.BC = BC
    z0, zc = float(BC.Z0), float(c.z_c)
    LID = TG.LID
    zt = LID["z_top"]
    # ASSUMPTION (sim only): the zip's two R 60 top corners are modelled square (the arcs make 0-width slivers of the
    # hinge band at the 3D corner that the 40 mm mesh cannot resolve); the zip legs are the aft corner seams and the
    # top run is the lid | hinge band seam at z 650 (lengths within 2 x 26 mm of the real U)
    regions = {
        "B-01": CB._rect(US, 2 * US, z0, zc),
        "B-03": CB._rect(0.0, US / 3, z0, zc),
        "B-02L": [("hinge", CB._line((2 * US / 3, z0), (US / 3, z0))), ("zip_R", CB._line((US / 3, z0), (US / 3, zt))),
                  ("zip_top", CB._line((US / 3, zt), (2 * US / 3, zt))),
                  ("zip_L", CB._line((2 * US / 3, zt), (2 * US / 3, z0)))],
        "B-02h": CB._rect(US / 3, 2 * US / 3, zt, zc),
    }
    names = {"B-01": ("frame-side panel", "challenge_ultra_200"), "B-03": ("side gusset", "cordura_330d_nylon66"),
             "B-02L": ("tailgate lid", "cordura_330d_nylon66"), "B-02h": ("hinge band", "cordura_330d_nylon66")}
    out = {"pieces": {}, "constants": {}, "dev_ids": list(regions),
           "release": "concept: designs/pack_5200/bag_comp/C/tailgate.py on concepts/corrie.py"}
    for pid, edges in regions.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.geom_type != "Polygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        sp = 14.0
        fm = develop_region(S, poly, spacing=sp, boundary_spacing=5.0, boundary_weight=100.0)
        E = []
        for nm, uv in edges:
            uvd = densify(np.asarray(uv, float), 2.0)
            E.append((nm, np.asarray(fm.map_uv(uvd)), np.asarray(S(uvd))))
        lab, mid = names[pid]
        V2 = np.asarray(fm.V2)
        if pid == "B-02L" and os.environ.get("TG_SIM_EASE"):
            # lid cut full across (tailgate.LID ease, 6 mm over the lid width): scale the flat lid along the flat
            # direction that maps to 3D x, about its centre; edges' flat coords move with it, 3D seam lines do not
            V3 = np.asarray(fm.V3)
            A = np.linalg.lstsq(np.column_stack([V2 - V2.mean(0), np.ones(len(V2))]), V3[:, 0], rcond=None)[0][:2]
            ax = A / np.linalg.norm(A)
            w = float(np.ptp(V3[:, 0]))
            k = float(os.environ.get("TG_SIM_EASE")) / w
            cen = V2.mean(0)
            sc = lambda P: P + np.outer((P - cen) @ ax, ax) * k            # noqa: E731
            V2 = sc(V2)
            E = [(nm, sc(np.asarray(f2)), f3) for nm, f2, f3 in E]
        out["pieces"][pid] = {"kind": "dev", "name": lab, "material_id": mid, "grain": 90.0, "V2": V2,
                              "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris), "edges": E,
                              "strain_p99": fm.strain_stats()["p99_pct"]}
    # floor + collar: exactly as CORRIE (corrie_bag.load_corrie_patterns)
    ref = _ORIG(False)
    for k in ("B-05", "B-06"):
        out["pieces"][k] = ref["pieces"][k]
    out["surface"] = ref["surface"]
    out["constants"] = dict(ref["constants"])
    out["constants"]["strain_p99"] = {k: v["strain_p99"] for k, v in out["pieces"].items() if v["kind"] == "dev"}
    return out


_ORIG = CB.load_corrie_patterns


def install():
    """Route ``bag: corrie`` to the TAILGATE pieces in this process."""
    CB.load_corrie_patterns = load_tailgate_patterns


def run(scenario: str, fine=False, cases=None, out=None):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    install()
    from huntkit.clothsim import cli
    name = Path(scenario).stem + ("_ease" if os.environ.get("TG_SIM_EASE") else "")
    out = out or str(SIM_OUT / (f"bagC_{name}" + ("_fine" if fine else "")))
    argv = ["run", "--scenario", str(scenario), "--out", out, "--no-render", "--no-sweep"]
    if fine:
        argv.append("--fine")
    if cases:
        argv += ["--cases", cases]
    return cli.main(argv)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        sc = sys.argv[2]
        cs = sys.argv[sys.argv.index("--cases") + 1] if "--cases" in sys.argv else None
        run(sc, fine="--fine" in sys.argv, cases=cs)
    elif sys.argv[1] == "all":
        for s in ("tg_PR15", "tg_PR15_nostraps", "tg_PR19", "tg_PR23"):
            run(str(SCEN_DIR / f"{s}.yaml"), cases="packed,fill,meat")
