"""CHERT cloth sim: the bag's flat pieces (form.regions, developed on the chamfered box) sewn and loaded with
huntkit.clothsim, on CORRIE's own rev C integration scenarios (corrie_PR15c / 19c / 23c: same frame, crown hood,
guys at x +/-149 z 695 on B-02h, 1 kg pouch on the collar, 85 mm spotter in the left-wing sleeve).

Not a shared-module edit: the pattern loader lives here and is handed to ``huntkit.clothsim.pack.PackModel`` by
replacing the module's ``load_patterns`` reference for this process only (scenario ``bag: spine`` path), the same
pattern dict contract as huntkit/clothsim/corrie_bag.py.

    python designs/pack_5200/bag_comp/form/form_sim.py run 15 19 23            # coarse h 40: packed, fill, meat
    python designs/pack_5200/bag_comp/form/form_sim.py fine 19                 # h 25 packed drape for the renders
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import form as F  # noqa: E402

ROOT = F.ROOT
SCEN_DIR = ROOT / "huntkit" / "clothsim" / "scenarios"
OUT = ROOT / "outputs" / "clothsim"


def load_chert_patterns(verbose=False) -> dict:
    from huntkit.clothsim.assemble import densify
    from huntkit.patterns import develop_region
    from shapely.geometry import Polygon
    BC = F.BC
    c = F.make()
    S, R = F.regions(c)
    z0, zc = float(BC.Z0), float(c.z_c)
    names = {"B-01": ("frame-side panel", "challenge_ultra_200"), "B-03": ("side gusset", F.SOLID),
             "B-02h": ("hinge band", F.SOLID), "B-02door": ("door", F.SOLID),
             "B-02u": ("blade U (camo)", F.SOLID)}   # camo 630D is stiffer/heavier; modelled as 330D (ASSUMPTION)
    out = {"pieces": {}, "constants": {}, "dev_ids": list(R), "release": "concept: designs/pack_5200/bag_comp/form/form.py"}
    for pid, edges in R.items():
        ring = []
        for _, pts in edges:
            ring.extend([tuple(p) for p in pts[:-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
            if poly.geom_type != "Polygon":
                poly = max(poly.geoms, key=lambda g: g.area)
        sp = 6.0 if pid == "B-02u" else 14.0
        fm = develop_region(S, poly, spacing=sp, boundary_spacing=3.0 if pid == "B-02u" else 5.0, boundary_weight=100.0)
        E = []
        for nm, uv in edges:
            uvd = densify(np.asarray(uv, float), 2.0)
            E.append((nm, np.asarray(fm.map_uv(uvd)), np.asarray(S(uvd))))
        lab, mid = names[pid]
        out["pieces"][pid] = {"kind": "dev", "name": lab, "material_id": mid, "grain": 90.0, "V2": np.asarray(fm.V2),
                              "V3": np.asarray(fm.V3), "tris": np.asarray(fm.tris), "edges": E,
                              "strain_p99": fm.strain_stats()["p99_pct"]}
    a0, yf0, d0, cx0, cy0 = (float(np.asarray(v).ravel()[0]) for v in S.env([z0]))
    corners = [(-a0, yf0), (a0, yf0), (a0, yf0 + d0 - cy0), (a0 - cx0, yf0 + d0), (-(a0 - cx0), yf0 + d0),
               (-a0, yf0 + d0 - cy0)]
    e05 = []
    for nm, (p, q) in zip(("frame", "right", "blade_r", "aft", "blade_l", "left"), zip(corners, corners[1:] + corners[:1])):
        P3 = densify(np.array([p, q], float), 2.0)
        fl = np.column_stack([-P3[:, 0], P3[:, 1]])
        e05.append((nm, fl, np.column_stack([P3[:, 0], P3[:, 1], np.full(len(P3), z0)])))
    out["pieces"]["B-05"] = {"kind": "floor", "name": "bottom (hexagon)", "material_id": "cordura_500d_nylon66",
                             "grain": 90.0, "edges": e05, "z0": z0}
    t = np.linspace(0, 2, 4001)
    q = np.mod(1.5 + t, 2.0)
    ring = np.asarray(S(np.column_stack([q * F.US, np.full(len(q), zc)])))
    s3 = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ring, axis=0), axis=1))]
    out["pieces"]["B-06"] = {"kind": "collar", "name": "roll-top collar", "material_id": "robic_100d_ripstop",
                             "grain": 90.0, "perimeter": float(s3[-1]), "ring": ring, "ring_s": s3,
                             "height_to_fill": float(c.dome_h), "z_collar": zc}
    qg = np.linspace(0, 2, 401)
    zg = np.linspace(z0, zc, 120)
    QQ, ZZ = np.meshgrid(qg, zg, indexing="ij")
    out["surface"] = {"q": qg, "z": zg, "xyz": np.asarray(S(np.column_stack([QQ.ravel() * F.US, ZZ.ravel()]))).reshape(
        len(qg), len(zg), 3)}
    out["constants"] = {"Z0": z0, "Z_COLLAR": zc, "Z_FILL": float(c.z_fill), "Z_SB": float(BC.Z_SB),
                        "Z_SH": float(BC.Z_SH), "design_L": float(c.volume_L()), "design_volume_L": float(c.volume_L()),
                        "pattern_volume_L_release": None,
                        "strain_p99": {k: v["strain_p99"] for k, v in out["pieces"].items() if v["kind"] == "dev"}}
    return out


_PAT = None


def _install():
    """Point PackModel's SPINE loader at CHERT for this process (no file edit)."""
    import huntkit.clothsim.pack as PK
    global _PAT

    def loader(verbose=True):
        global _PAT
        if _PAT is None:
            _PAT = load_chert_patterns(verbose)
        return _PAT
    PK.load_patterns = loader
    return PK


def scenario(torso: int) -> dict:
    PK = _install()
    scen = PK.load_scenario(str(SCEN_DIR / f"corrie_PR{torso}c.yaml"))
    scen["bag"] = "spine"            # -> the replaced loader = CHERT
    scen["name"] = f"chert_PR{torso}"
    return scen


def model(torso=19, fine=False):
    PK = _install()
    return PK.PackModel(scenario(torso), fine=fine, verbose=False)


def run(torso: int, cases=("packed", "fill", "meat"), fine=False, out=None) -> dict:
    from huntkit.clothsim.pack import run_case
    from huntkit.clothsim.report import summarize, to_json
    t0 = time.time()
    pm = model(torso, fine)
    out = Path(out or OUT / f"chert_PR{torso}{'_fine' if fine else 'c'}")
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    Vpack = None
    for cname in cases:
        case = dict(pm.scen["cases"][cname])
        if case.get("contents_L") == "auto":
            case["contents_L"] = Vpack
        t = time.time()
        x, sim, infos = run_case(pm, case)
        r = summarize(pm, cname, case, x, sim, infos)
        if cname == "packed":
            Vpack = r["volume"]["closed_L"]
        res[cname] = r
        np.save(out / f"x_{cname}.npy", x)
        print(f"[chert {torso} in] {cname}: {'converged' if r['converged'] else 'NOT converged'} {time.time() - t:.0f} s,"
              f" V {r['volume']['closed_L']:.1f} L, CG {r['volume'].get('cg_with_external_mm')}", flush=True)
    summ = {"scenario": f"chert_PR{torso}", "torso_in": torso, "fine": fine, "mesh": {"nodes": pm.mesh.n, "h_mm": pm.h},
            "cases": res, "seconds": time.time() - t0, "source": "designs/pack_5200/bag_comp/form/form_sim.py"}
    (out / "results.json").write_text(json.dumps(to_json(summ), indent=1, default=float))
    return summ


def cg_table(torsos=(15, 19, 23)) -> dict:
    """Mass-weighted CG y (with pouch + scope) per torso, fill and meat, from the coarse runs."""
    t = {"fill": {}, "meat": {}, "volume_L": {}, "rounding_mm": {}, "converged": {}, "cg_z": {}}
    for to in torsos:
        f = OUT / f"chert_PR{to}c" / "results.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for cs in ("fill", "meat"):
            r = d["cases"].get(cs)
            if not r:
                continue
            v = r["volume"]
            cg = v.get("cg_with_external_mm") or v["contents_cg_mm"]
            t[cs][str(to)] = round(float(cg[1]), 1)
            t["cg_z"][f"{cs}_{to}"] = round(float(cg[2]), 1)
            t["volume_L"][f"{cs}_{to}"] = round(float(v["closed_L"]), 1)
            t["rounding_mm"][f"{cs}_{to}"] = r.get("contact_rounding_mm")
            t["converged"][f"{cs}_{to}"] = bool(r["converged"])
    return t


if __name__ == "__main__":
    cmd = sys.argv[1]
    tors = [int(v) for v in sys.argv[2:]] or [19]
    if cmd == "run":
        for to in tors:
            run(to)
    elif cmd == "fine":
        for to in tors:
            run(to, cases=("packed",), fine=True)
    elif cmd == "table":
        print(json.dumps(cg_table(), indent=1))
