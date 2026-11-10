"""FELL loadout / access check (Team B LEAN, 2026-11-10), on the pattern of concepts/corrie_loadout.py.

    python designs/pack_5200/bag_comp/lean/fell_loadout.py      # -> outputs/loadout/fell_loadout_results.json

The CORRIE study model is reused unchanged (column stacking, CG, peel, access classes); only its zone table is
swapped for FELL's, per loadout configuration (fell.CONFIGS):
* bag body: the same shell, so the same columns. The centre zip spans z 110-650 like CORRIE's door, so an aft-half
  item inside that span is class 4 (pack off, through the zip), as CORRIE's door rule;
* no door pocket (IMP-4 is gone: the kill kit packs in the bag or the lid pod);
* wing_L = under the glass pod panel (A1, cinched like a wing), scope_sleeve_L = its sleeve; wing_R = under the
  right side strap pair (A2). Same 6 L / class 3 as CORRIE's wings (ASSUMPTION carried from corrie_loadout.py);
* top_pouch = lid pod A3 (2.7 L, CORRIE B.2 size) only where fitted;
* strap_pod_R = A4 on the right J-strap, class 1. Packing rule (DECISION): snacks and the GPS go there first.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import corrie_loadout as CL  # noqa: E402
import fell as F  # noqa: E402

_ORIG_ZONES = CL.zones
FORCE = {"snacks_today": ["strap_pod_R", "hip_R", "hip_L", "top_pouch"],
         "gps": ["strap_pod_R", "hip_L", "hip_R", "top_pouch"],
         "kill_kit": ["bag_A_mid", "bag_A_low", "top_pouch"]}   # packing rule: kill kit mid-aft, behind the zip


def zones_fell(loadout: str, size: str) -> dict:
    Z = _ORIG_ZONES(f"integrated:{size}")
    on = F.CONFIGS[loadout]
    ad = F.addons()
    Z.pop("door_pocket", None)
    if "A1" not in on:
        Z.pop("wing_L", None)
        Z.pop("scope_sleeve_L", None)
    else:
        Z["wing_L"].name = "under the glass pod panel A1 (left)"
        Z["scope_sleeve_L"].name = "A1 glass pod sleeve"
    if "A2" not in on:
        Z.pop("wing_R", None)
    else:
        Z["wing_R"].name = "under the right side strap pair A2"
    if "A3" not in on:
        Z.pop("top_pouch", None)
    else:
        Z["top_pouch"].name = "lid pod A3 2.7 L"
    if "A4" in on:
        i = ad["A4"]["interior_mm"]
        Z["strap_pod_R"] = CL.Zone("strap_pod_R", "A4 strap pod, right J-strap", "strap", 1,
                                   round(i[0] * i[1] * i[2] / 1e6, 3), tuple(sorted(i, reverse=True)), False)
    return Z


def run(sizes=("S", "M", "L", "XL", "XXL")) -> dict:
    data = CL.load_yaml()
    res = {}
    for size in sizes:
        for key, lo in data["loadouts"].items():
            CL.zones = lambda config, _k=key, _s=size: zones_fell(_k, _s)
            variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
            for vname, arch in variants:
                P = CL.pack(CL.split_units(CL.expand(data, key, archery=arch)), f"integrated:fell:{size}", force=FORCE)
                tag = f"{key}_{vname}_{size}"
                s = CL.summary(P, f"{lo['name']} [{vname}, FELL {F.CONFIGS[key]}, belt {size}]")
                s["zones"] = {r["id"]: r["zone"] for r in P.rows}
                res[tag] = s
                mk = lo["meat_case"]["meat_kg"]
                Pm = CL.pack(CL.split_units(CL.expand(data, key, archery=arch, meat_day=True)), f"integrated:fell:{size}", force=FORCE,
                             meat_kg=mk)
                res[tag + "_meat"] = CL.summary(Pm, f"{lo['name']} pack-out {mk} kg [FELL, {size}]")
    CL.zones = _ORIG_ZONES
    return res


def misses(res, size="M") -> dict:
    out = {}
    for key in ("day", "elk6", "sheep8"):
        fails = set()
        hourly = set()
        for tag, s in res.items():
            if tag.startswith(key + "_") and tag.endswith("_" + size):
                for f, v in s["access"].items():
                    fails |= set(v["fail"])
                    if f in ("hourly", "constant"):
                        hourly |= set(v["fail"])
        out[key] = {"all": sorted(fails), "hourly": sorted(hourly)}
    return out


if __name__ == "__main__":
    res = run()
    out = ROOT / "outputs" / "loadout"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fell_loadout_results.json").write_text(json.dumps(res, indent=1, default=CL._json))
    for k, s in res.items():
        bad = {f: v["fail"] for f, v in s["access"].items() if v["fail"]}
        print(f"{k:24s} 15in {s['cg_y_rev_c_15in']:6.1f} 19in {s['cg_y_rev_c_19in']:6.1f} lim {s['rev_c_limit_y']} "
              f"z {s['cg_geo_mm'][2]:5.0f} used {s['main_bag_used_L']:5.1f} top {s['top_z']:5.0f} "
              f"float {s['float_mode']} spill {s['spilled']} fails {bad}")
    for sz in ("S", "M", "XL"):
        print(sz, misses(res, sz))
