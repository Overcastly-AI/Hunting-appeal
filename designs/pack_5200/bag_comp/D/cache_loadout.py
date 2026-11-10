"""CACHE (team D) loadout / access check: designs/pack_5200/concepts/corrie_loadout.py (the pattern RULES.md names),
run unchanged on CACHE's zones. Only the zone table changes (the packer, items, loadouts, CG model and the
cloth-sim peel are CORRIE's: the CACHE shell is the CORRIE rev B shell, so the peel calibration carries over).

Zone changes against CORRIE B.2 (`corrie_loadout.zones_integrated`):
* wing_L: flat items (pad, poles) over the optics pod under its 2 aft cinch straps: 4 L, items <= 60 mm thick.
* strap_pocket_R: the SP snack pocket on the right J-strap (cache.py), class 1; snacks prefer it (FORCE below).
* wing_R: the tripod kit (2 cinch straps over the right gusset, foot cup): same 6 L / 600 x 200 x 150 envelope as
  CORRIE's right wing (ASSUMPTION: same straps' reach), access class 3.
* scope_sleeve_L: the optics pod (CORRIE's IMP-1 sleeve, own pool), class 3.
* door_pocket -> the KILL module just inside the door sill: 260 x 90 x 280 mm box, 0.85 fill, class 4.
* top_pouch -> the LID module, same box as CORRIE B.2's pouch (2.7 L), class 3.
* SWAP slab / CAMP module: inside the main-bag columns (frame / aft); their walls are counted as a fill-efficiency
  loss (ASSUMPTION: 0.90 -> 0.86 soft items in modules).

    python designs/pack_5200/bag_comp/D/cache_loadout.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
sys.path.insert(0, str(ROOT))

import corrie_loadout as L  # noqa: E402

KILL_ENV = (280.0, 260.0, 90.0)        # cache.py modules(): KILL 260 x 90 x 280
KILL_L = round(0.260 * 0.090 * 0.280 * 1000 * 0.85, 2)
# packing rule (user guide, as CORRIE's IMP-4 rule): the KILL module holds the kill kit, first aid and game bags only
FORCE = {"puffy_jacket": ["bag_A_high"], "snacks_today": ["strap_pocket_R", "hip_R", "hip_L", "top_pouch"]}
EFF_MODULE = 0.86        # ASSUMPTION: soft gear in a module (module wall + corners) vs 0.90 loose


def zones_cache(size="M"):
    Z = L.zones_integrated(size)
    Z["wing_L"] = L.Zone("wing_L", "left gusset: over the optics pod under its 2 aft cinch straps", "wing", 3, 4.0,
                         (600, 260, 60), True, (-1, None, 375.0))
    Z["strap_pocket_R"] = L.Zone("strap_pocket_R", "SP snack pocket, right J-strap", "strap", 1, 0.64, (180, 105, 40),
                                 False)
    Z["wing_R"] = L.Zone("wing_R", "tripod kit: 2 cinch straps over the right gusset", "wing", 3, 6.0, (600, 200, 150),
                         True, (1, None, 375.0))
    Z["scope_sleeve_L"] = L.Zone("scope_sleeve_L", "optics pod (hook-on padded tube)", "wing", 3, 5.0, (430, 160, 150),
                                 True, (-1, None, 375.0))
    Z["door_pocket"] = L.Zone("door_pocket", "KILL module inside the door sill", "fixed", 4, KILL_L, KILL_ENV, True,
                              (0, "door", 250.0))
    Z["top_pouch"] = L.Zone("top_pouch", "LID module 2.7 L on the cinched collar", "pouch", 3, Z["top_pouch"].cap_L,
                            Z["top_pouch"].env_mm, True)
    return Z


def run():
    data = L.load_yaml()
    orig_zones, orig_soft = L.zones, L.EFF_SOFT
    L.zones = lambda config="today": zones_cache(config.split(":")[1] if ":" in str(config) else "M")
    L.EFF_SOFT = EFF_MODULE
    res = {}
    try:
        for size in ("S", "M", "L", "XL", "XXL"):
            for key, lo in data["loadouts"].items():
                variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
                for vname, arch in variants:
                    P = L.pack(L.split_units(L.expand(data, key, archery=arch)), f"integrated:{size}", force=FORCE)
                    s = L.summary(P, f"{lo['name']} [{vname}, CACHE, belt {size}]")
                    s["zones"] = {r["id"]: r["zone"] for r in P.rows}
                    res[f"{key}_{vname}_{size}"] = s
                    mk = lo["meat_case"]["meat_kg"]
                    Pm = L.pack(L.split_units(L.expand(data, key, archery=arch, meat_day=True)), f"integrated:{size}",
                                force=FORCE, meat_kg=mk)
                    res[f"{key}_{vname}_{size}_meat"] = L.summary(Pm, f"{lo['name']} pack-out {mk} kg [CACHE, {size}]")
    finally:
        L.zones, L.EFF_SOFT = orig_zones, orig_soft
    return res


def misses(res, size="M"):
    """Hourly / constant items not reachable pack-on (class > 1), per loadout (rifle), belt ``size``."""
    out = {}
    for key in ("day", "elk6", "sheep8"):
        s = res[f"{key}_rifle_{size}"]
        out[key] = s["access"]["constant"]["fail"] + s["access"]["hourly"]["fail"]
    return out


def other_fails(res, size="M"):
    out = {}
    for key in ("day", "elk6", "sheep8"):
        s = res[f"{key}_rifle_{size}"]
        out[key] = {f: v["fail"] for f, v in s["access"].items() if v["fail"] and f not in ("constant", "hourly")}
    return out


if __name__ == "__main__":
    r = run()
    out = ROOT / "outputs" / "loadout" / "bagD_cache_loadout.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, indent=1, default=L._json))
    for size in ("S", "M", "L", "XL", "XXL"):
        print(size, "hourly misses", misses(r, size))
    print("M other", other_fails(r, "M"))
    for k, s in r.items():
        if k.endswith("_M") or k.endswith("_M_meat"):
            print(f"{k:22s} CG geo {s['cg_geo_mm']} 15in {s['cg_y_rev_c_15in']} 19in {s['cg_y_rev_c_19in']} lim "
                  f"{s['rev_c_limit_y']} used {s['main_bag_used_L']} free {s['main_bag_free_L']} float {s['float_mode']} "
                  f"unplaced {s['unplaced']} spilled {s['spilled']}")
