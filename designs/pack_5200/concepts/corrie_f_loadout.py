"""BL-011 CORRIE F loadout / access / CG check, on the pattern of concepts/corrie_loadout.py (imported and re-pointed,
never edited; the same mechanism team A used in bag_comp/A/evolve_loadout.py).

    python designs/pack_5200/concepts/corrie_f_loadout.py        # -> outputs/loadout/corrie_f_loadout.json + table

What changes against CORRIE B.2's integrated zones (corrie_loadout.zones_integrated, every belt size):
* geometry: CORRIE F's shell (corrie_f.make: S15 + top setback) with CORRIE F's own simulated fill volume and peels
  (corrie_f_sim results) where they exist;
* the wings are deleted (owner 2026-11-11): ``wing_R`` becomes the side carry under W1/W2 on the right gusset (tripod,
  jacket) and ``wing_L`` the space under W1/W2 and the scope pod on the left; same 6 L / class 3 as CORRIE's wings
  (ASSUMPTION carried from corrie_loadout.py: W1/W2 cinch a load against the gusset as a wing did; settled by the
  FT-S2 side-hill field test the owner set for the wing deletion);
* ``scope_sleeve_L`` is the scope pod (add-on) on the left gusset, class 3;
* ``fp_L`` / ``fp_R`` team A's hip-reach pockets on the gussets' lower front corners (z 150-380), class 1, and the pole
  quiver (E-5), class 1. ASSUMPTION (reach, team A's EV-3): a pocket mouth just above and behind the belt wing root is
  reachable pack-on; on S15 the mouth sits on the gusset face at x = +/-197 (A's was on a wing outside a 320 mm base),
  so EV-3 must be run on the CORRIE F prototype, loaded, gloved, S/M/L testers;
* the door: D1 (lid from the floor to z 650) or D2 (z 110-650); the door class rule of corrie_loadout uses CO.DOOR;
* packing rule (team A's PREFS): snacks and GPS to FP-L, the 2nd bottle to FP-R, poles to the quiver.
All add-ons are fitted (the as-hunted configuration).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _p in (str(ROOT), str(HERE), str(HERE / "corrie_f_sim"), str(ROOT / "designs" / "pack_5200" / "bag_comp")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
import corrie_f as F  # noqa: E402
import corrie_loadout as L  # noqa: E402

OUT = ROOT / "outputs" / "loadout"
TORSOS = (15, 19, 23)
LOADOUTS = ("day", "elk6", "sheep8")


def _prefs() -> dict:
    import importlib
    return dict(importlib.import_module("A.evolve_loadout").PREFS)


def sim_results() -> dict:
    """Fill / meat contents volume and contents CG y of CORRIE F's stored coarse runs (variant F)."""
    import corrie_f_sim as S
    out = {}
    for t in TORSOS:
        r = S.get("F", t)
        if not r:
            continue
        out[t] = {cn: {"L": r["cases"][cn]["closed_L"], "cg": r["cases"][cn]["contents_cg_y"],
                       "conv": r["cases"][cn]["converged"]} for cn in ("fill", "meat") if cn in r["cases"]}
    return out


def geom(sim_fill_L):
    c = F.make()
    with F.frame_face(c):
        st = c.profile()
    z = st[:, 0]
    area = 2 * st[:, 1] * st[:, 3] * st[:, 4]
    v_geo = float(np.trapezoid(area, z)) / 1e6
    kb = float(np.mean(sim_fill_L)) / v_geo
    half = 0.5 * area * kb
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (half[1:] + half[:-1]) * np.diff(z))]) / 1e6

    class _C:            # the cg() the peel uses must see this shell's frame face
        def __init__(self, c):
            self.c = c

        def cg(self):
            with F.frame_face(self.c):
                return self.c.cg()

        def __getattr__(self, k):
            return getattr(self.c, k)
    return {"c": _C(c), "z": z, "a": st[:, 1], "yf": st[:, 2], "d": st[:, 3], "half_area": half, "cum_L": cum,
            "kb": kb, "v_geo": v_geo, "v_sewn": float(np.mean(sim_fill_L)), "zc": c.z_c, "zfill": c.z_fill}


_ZONES_ORIG = L.zones
FP_Z = 265.0          # pocket centre, z 150-380


def zones_f(config="integrated:M"):
    if not str(config).startswith("integrated"):
        return _ZONES_ORIG(config)          # corrie_loadout's own calibration packs (peel_meat) use 'today'
    size = config.split(":")[-1]
    Z = _ZONES_ORIG(f"integrated:{size}")
    Z["wing_L"].name = "under W1/W2 and the scope pod, left gusset (no wing)"
    Z["wing_R"].name = "under W1/W2, right gusset: tripod / jacket (no wing)"
    Z["scope_sleeve_L"].name = "scope pod (add-on) sleeve, left gusset"
    E = F._A()
    a = L.a_at(FP_Z)
    yf = float(np.interp(FP_Z, L.G["z"], L.G["yf"]))
    for zid, side, nm in (("fp_L", -1, "FP-L hip-reach pocket, left gusset"), ("fp_R", 1, "FP-R hip-reach pocket, right gusset")):
        Z[zid] = L.Zone(zid, nm, "hip", 1, E.FP["cap_L"], E.FP["env_mm"], True, (side * (a + 45.0), yf + 70.0, FP_Z))
    Z["pole_quiver"] = L.Zone("pole_quiver", "E-5 pole quiver (FP-R boot + grip loop at z 640)", "hip", 1, E.POLE["cap_L"],
                              E.POLE["env_mm"], True, (a + 40.0, yf + 40.0, 400.0))
    return Z


DOOR_LOADOUT = {"D1": {"inset": 0.0, "z_lo": float(BC.Z0), "z_hinge": F.D1["z_top"], "r": F.D1["r"]},
                "D2": {"inset": float(F.D2["blade_bot"]), "z_lo": F.D2["z_lo"], "z_hinge": F.D2["z_hinge"], "r": F.D2["r"]}}


def _import_team_a():
    """Import team A's modules BEFORE install() re-points the shared modules. ``evolve`` (and ``A.evolve``) build
    ``DOOR = dict(CO.DOOR, z_lo=130)`` and ``evolve_loadout`` captures ``_ZONES_ORIG = L.zones`` at import time; first
    imported inside install() (``_prefs()``, ``zones_f`` -> ``F._A()``) they froze CORRIE F's loadout door and
    ``zones_f`` for the rest of the process, so a later ``ledger.teams()`` built team A's bag on the wrong door."""
    _prefs()
    F._A()


def install(door: str = F.DOOR_DEFAULT, sim=None) -> dict:
    _import_team_a()
    sim = sim if sim is not None else sim_results()
    fillL = [sim[t]["fill"]["L"] for t in sim if "fill" in sim[t]] or list(L.SIM_FILL_L)
    L.G = geom(fillL)
    L.zones = zones_f
    CO.DOOR = dict(DOOR_LOADOUT[door])
    L.MIN_TOP_Z = CO.DOOR["z_hinge"]
    L._MEAT_PEEL.clear()
    src = {}
    for t in TORSOS:
        if t in sim and "fill" in sim[t]:
            L.SIM_FILL_CG[t] = sim[t]["fill"]["cg"]
            src[t] = "CORRIE F clothsim"
        if t in sim and "meat" in sim[t]:
            L.SIM_MEAT_CG[t] = sim[t]["meat"]["cg"]
    return {"fill_L": fillL, "peel_src": src}


_KEEP = {}


def _save():
    if not _KEEP:
        _KEEP.update(G=L.G, zones=L.zones, DOOR=dict(CO.DOOR), MIN=L.MIN_TOP_Z, fill=dict(L.SIM_FILL_CG),
                     meat=dict(L.SIM_MEAT_CG))


def uninstall():
    if _KEEP:
        L.G, L.zones, L.MIN_TOP_Z = _KEEP["G"], _KEEP["zones"], _KEEP["MIN"]
        CO.DOOR = dict(_KEEP["DOOR"])
        L.SIM_FILL_CG.clear()
        L.SIM_FILL_CG.update(_KEEP["fill"])
        L.SIM_MEAT_CG.clear()
        L.SIM_MEAT_CG.update(_KEEP["meat"])
        L._MEAT_PEEL.clear()


def _keys(data) -> dict:
    keys = {}
    for k in data["loadouts"]:
        for short in LOADOUTS:
            if k.startswith(short[:3]):
                keys[short] = k
    return keys


def _rows(data, key, prefs, archery=False, meat=False):
    """Loadout rows with team A's packing rule applied by base id (bottle_1L#2 takes bottle_1L's list)."""
    rows = L.split_units(L.expand(data, key, archery=archery, meat_day=meat))
    for r in rows:
        base = r["id"].split("#")[0]
        if base in prefs:
            r["pref"] = list(prefs[base])
    return rows


def run(door: str = F.DOOR_DEFAULT, sizes=tuple(CO.BELT_SIZES)) -> dict:
    _save()
    data = L.load_yaml()
    info = install(door)
    prefs = _prefs()
    res = {"door": door, "install": info, "runs": {},
           "geometry": {"v_geo_L": round(L.G["v_geo"], 2), "v_sewn_L": round(L.G["v_sewn"], 2),
                        "peel_mm": {t: round(L.peel(t), 1) for t in TORSOS},
                        "peel_meat_mm": {t: round(L.peel_meat(t), 1) for t in TORSOS}}}
    try:
        for size in sizes:
            for short, key in _keys(data).items():
                lo = data["loadouts"][key]
                variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
                for vname, arch in variants:
                    P = L.pack(_rows(data, key, prefs, arch), f"integrated:{size}")
                    s = L.summary(P, f"{lo['name']} [{vname}, CORRIE F {door}, belt {size}]")
                    s["zones"] = {r["id"]: r["zone"] for r in P.rows}
                    s["access_cls"] = {r["id"]: r["access_cls"] for r in P.rows}
                    res["runs"][f"{short}_{vname}_{size}"] = s
                    mk = lo["meat_case"]["meat_kg"]
                    Pm = L.pack(_rows(data, key, prefs, arch, True), f"integrated:{size}", meat_kg=mk)
                    res["runs"][f"{short}_{vname}_{size}_meat"] = L.summary(Pm, f"{lo['name']} pack-out {mk} kg [CORRIE F, {size}]")
    finally:
        uninstall()
    res["misses"] = {sz: misses(res, sz) for sz in sizes}
    res["worst_cg_15in"] = {"fill_like": max(s["cg_y_rev_c_15in"] for k, s in res["runs"].items() if not k.endswith("_meat")),
                            "packout": max(s["cg_y_rev_c_15in"] for k, s in res["runs"].items() if k.endswith("_meat"))}
    return res


def misses(res: dict, size: str = "M") -> dict:
    out = {}
    for short in LOADOUTS:
        fails, hourly = set(), set()
        for tag, s in res["runs"].items():
            if tag.startswith(short + "_") and tag.endswith("_" + size):
                for f, v in s["access"].items():
                    fails |= set(v["fail"])
                    if f in ("hourly", "constant"):
                        hourly |= set(v["fail"])
        out[short] = {"all": sorted(fails), "hourly": sorted(hourly)}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    allres = {}
    for door in F.DOORS:
        res = run(door)
        allres[door] = res
        print(door, "peel", res["geometry"])
        for sz, m in res["misses"].items():
            print(f"  {sz}: " + "; ".join(f"{k} hourly {v['hourly']} all {v['all']}" for k, v in m.items()))
        print("  worst 15 in CG", res["worst_cg_15in"])
    (OUT / "corrie_f_loadout.json").write_text(json.dumps(allres, indent=1, default=L._json))
    return allres


if __name__ == "__main__":
    main()
