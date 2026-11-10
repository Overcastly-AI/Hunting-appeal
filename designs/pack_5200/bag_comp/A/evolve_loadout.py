"""CORRIE E loadout / access / CG check, Team A EVOLVE. Pattern: designs/pack_5200/concepts/corrie_loadout.py, which
is IMPORTED and re-pointed (its geometry, zones, sim peel and door) at CORRIE E; nothing is copied or edited.

    python designs/pack_5200/bag_comp/A/evolve_loadout.py     # -> outputs/loadout/bagA_loadout.json + table

CORRIE E zones = CORRIE B.2's integrated zones (all belt sizes) plus:
* ``fp_L`` hip-reach pocket on the left wing, lower front corner (E-4): class 1 (pack on);
* ``fp_R`` hip-reach pocket on the right wing (E-4): class 1;
* ``pole_quiver`` boot in fp_R's front pleat + grip loop on the wing top (E-5): class 1.
Packing rule (CORRIE E user guide, PREFS below): snacks and GPS go to fp_L, the 2nd bottle to fp_R, poles to the quiver.
The sim peel (fill / meat) comes from CORRIE E's own cloth sims (evolve_bag.py) when they exist.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evolve as E  # noqa: E402
import corrie_loadout as L  # noqa: E402  (on sys.path via evolve)
import corrie as CO  # noqa: E402
import bag_concepts as BC  # noqa: E402

OUT = E.ROOT / "outputs" / "loadout"
SIM = E.ROOT / "outputs" / "clothsim"
TORSOS = (15, 19, 23)

# ASSUMPTION (reach): a pocket mouth at z 95-325 on the wing's FRONT corner (frame side, 30-60 mm aft of the
# B-01 seam) sits just above and behind the belt wing root, where Exo's forward-facing lower pockets sit
# ("nearly everyone can reach", research doc [A7]); gate EV-3 (reach test, S/M/L testers, pack on, loaded).
FP_Z = 0.5 * sum(E.FP["z"])
PREFS = {
    "snacks_today": ["fp_L", "hip_R", "hip_L", "top_pouch"],
    "gps": ["fp_L", "hip_L", "hip_R", "top_pouch"],
    "bottle_1L": ["bottle_hip", "fp_R", "wing_L", "wing_R", "bag_A_high"],
    "trekking_poles": ["pole_quiver", "wing_R", "wing_L", "bag_A_high"],
}


def sim_results():
    """Fill / meat volume and contents CG y of CORRIE E's converged coarse runs (None where a run is missing)."""
    out = {}
    for t in TORSOS:
        f = SIM / f"bagA_evolve_PR{t}" / "results.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text())["cases"]
        out[t] = {k: {"L": r[k]["volume"]["closed_L"], "cg": r[k]["volume"].get("contents_cg_mm"),
                      "conv": r[k]["converged"]} for k in r}
    return out


def geom(sim_fill_L):
    c = E.make()
    st = c.profile()
    z = st[:, 0]
    area = 2 * st[:, 1] * st[:, 3] * st[:, 4]
    v_geo = float(np.trapezoid(area, z)) / 1e6
    kb = float(np.mean(sim_fill_L)) / v_geo
    half = 0.5 * area * kb
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (half[1:] + half[:-1]) * np.diff(z))]) / 1e6
    return {"c": c, "z": z, "a": st[:, 1], "yf": st[:, 2], "d": st[:, 3], "half_area": half, "cum_L": cum,
            "kb": kb, "v_geo": v_geo, "v_sewn": float(np.mean(sim_fill_L)), "zc": c.z_c, "zfill": c.z_fill}


_ZONES_ORIG = L.zones


def zones_evolve(config="today"):
    if not str(config).startswith("evolve"):
        return _ZONES_ORIG(config)
    size = config.split(":")[1] if ":" in config else "M"
    Z = _ZONES_ORIG(f"integrated:{size}")
    a = L.a_at(FP_Z)
    yf = float(np.interp(FP_Z, L.G["z"], L.G["yf"]))
    for zid, side, nm, cap, env in (("fp_L", -1, "E-4 hip-reach pocket, left wing", E.FP["cap_L"], E.FP["env_mm"]),
                                    ("fp_R", 1, "E-4 hip-reach pocket, right wing", E.FP["cap_L"], E.FP["env_mm"])):
        Z[zid] = L.Zone(zid, nm, "hip", 1, cap, env, True, (side * (a + 45.0), yf + 70.0, FP_Z))
    Z["pole_quiver"] = L.Zone("pole_quiver", "E-5 pole quiver (fp_R boot + wing grip loop)", "hip", 1, E.POLE["cap_L"],
                              E.POLE["env_mm"], True, (a + 40.0, yf + 40.0, 330.0))
    return Z


def install(sim=None):
    """Point corrie_loadout at CORRIE E (geometry, zones, door, sim peel)."""
    sim = sim if sim is not None else sim_results()
    fillL = [sim[t]["fill"]["L"] for t in sim if "fill" in sim[t]] or list(L.SIM_FILL_L)
    L.G = geom(fillL)
    L.zones = zones_evolve
    CO.DOOR = E.DOOR
    L.MIN_TOP_Z = E.DOOR["z_hinge"]
    L._MEAT_PEEL.clear()
    src = {}
    for t in TORSOS:
        if t in sim and "fill" in sim[t] and sim[t]["fill"]["cg"]:
            L.SIM_FILL_CG[t] = sim[t]["fill"]["cg"][1]
            src[t] = "CORRIE E clothsim"
        if t in sim and "meat" in sim[t] and sim[t]["meat"]["cg"]:
            L.SIM_MEAT_CG[t] = sim[t]["meat"]["cg"][1]
    return {"fill_L": fillL, "peel_src": src}


def rows_for(data, key, archery=False, meat=False, evolve=True):
    rows = L.split_units(L.expand(data, key, archery=archery, meat_day=meat))
    if evolve:
        for r in rows:
            base = r["id"].split("#")[0]
            if base in PREFS:
                r["pref"] = list(PREFS[base])
    return rows


def run():
    data = L.load_yaml()
    info = install()
    res = {"install": info, "geometry": {"v_geo_L": round(L.G["v_geo"], 2), "v_sewn_L": round(L.G["v_sewn"], 2),
                                         "peel_mm": {t: round(L.peel(t), 1) for t in TORSOS},
                                         "peel_meat_mm": {t: round(L.peel_meat(t), 1) for t in TORSOS}},
           "evolve": {}, "misses": {}}
    keys = {"day": "day", "elk6": None, "sheep8": None}
    for k in data["loadouts"]:
        if "elk" in k:
            keys["elk6"] = k
        if "sheep" in k:
            keys["sheep8"] = k
    for size in CO.BELT_SIZES:
        for short, key in keys.items():
            lo = data["loadouts"][key]
            variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
            for vname, arch in variants:
                P = L.pack(rows_for(data, key, arch), f"evolve:{size}")
                s = L.summary(P, f"{lo['name']} [{vname}, CORRIE E, belt {size}]")
                s["zones"] = {r["id"]: r["zone"] for r in P.rows}
                s["access_cls"] = {r["id"]: r["access_cls"] for r in P.rows}
                tag = f"{short}_{vname}_{size}"
                res["evolve"][tag] = s
                fails = sorted({f for fr, v in s["access"].items() for f in v["fail"]
                                if fr in ("constant", "hourly", "glassing", "weather")})
                res["misses"][tag] = fails
                res.setdefault("all_fails", {})[tag] = sorted({f for v in s["access"].values() for f in v["fail"]})
                mk = lo["meat_case"]["meat_kg"]
                Pm = L.pack(rows_for(data, key, arch, meat=True), f"evolve:{size}", meat_kg=mk)
                sm = L.summary(Pm, f"{lo['name']} pack-out {mk} kg [CORRIE E, {size}]")
                res["evolve"][tag + "_meat"] = sm
    # CG by torso: the worst loadout's geometric CG + each torso's peel (corrie_loadout method)
    cg = {"fill": {}, "meat": {}}
    for t in TORSOS:
        f = [s["cg_geo_mm"][1] + L.peel(t) for k, s in res["evolve"].items() if not k.endswith("_meat")]
        m = [s["cg_geo_mm"][1] + L.peel_meat(t) for k, s in res["evolve"].items() if k.endswith("_meat")]
        cg["fill"][t], cg["meat"][t] = round(max(f), 1), round(max(m), 1)
    res["loadout_cg_worst"] = cg
    return res


def summarize_misses(res):
    out = {}
    for short in ("day", "elk6", "sheep8"):
        per = {}
        for tag, f in res["misses"].items():
            if tag.startswith(short + "_"):
                per[tag.split("_", 1)[1]] = f
        out[short] = per
    return out


if __name__ == "__main__":
    res = run()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bagA_loadout.json").write_text(json.dumps(res, indent=1, default=L._json))
    for k, v in summarize_misses(res).items():
        print(k, json.dumps(v))
    print("CG worst", res["loadout_cg_worst"], res["geometry"])
    for k, s in res["evolve"].items():
        if k.endswith("_M") or k.endswith("_M_meat"):
            print(k, s["cg_geo_mm"], s["cg_y_rev_c_15in"], s["main_bag_used_L"], s["main_bag_free_L"], s["float_mode"],
                  {i: z for i, z in s.get("zones", {}).items() if i in PREFS or i.startswith("bottle") or i == "rain_jacket"})
