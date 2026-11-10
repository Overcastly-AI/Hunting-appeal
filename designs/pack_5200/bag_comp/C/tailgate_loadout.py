"""TAILGATE loadout / access check (team C), on the pattern of concepts/corrie_loadout.py (imported, not edited).

    python designs/pack_5200/bag_comp/C/tailgate_loadout.py     # -> outputs/bag_comp_C/loadout_C.json

Differences from CORRIE B.2 in the zone model (everything else is corrie_loadout's model and loadouts.yaml data):
* door access: the lid opens the whole aft face from the floor (z 35) to z 650, so BOTH bag columns are reachable
  through it (class 4) for items that start below z 620; CORRIE: aft column only, z 110-620.
* side carry: the wing zones become "under the side straps" (same capacity ASSUMPTION, 6 L a side; the IMP-1 sleeve
  is on the left gusset, the tripod on the right under 2 side straps with the IMP-8 cup at its foot).
* IMP-4 rides on the inside of the lid (class 4, the lid's y).
* IMP-C1 snack / GPS sleeve on the right J-strap: class 1, harness (not in the bag CG). The snack and GPS rows get it
  in their preference list (after the hipbelt pockets, before the pouch): this file's DECISION, loadouts.yaml unchanged.
* Peel (cloth-sim CG minus geometric CG): TAILGATE's own sims when their results exist (outputs/clothsim/bagC_tg_PR*),
  else CORRIE's (same box shell).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
sys.path.insert(0, str(HERE))

import corrie as CO  # noqa: E402
import corrie_loadout as L  # noqa: E402
import tailgate as TG  # noqa: E402

OUT = ROOT / "outputs" / "bag_comp_C"
SIM = ROOT / "outputs" / "clothsim"
LID_TOP = TG.LID["z_top"]
SNACK_ZONE = "strap_snack"


def sim_cg():
    """(fill, meat) contents CG y per torso from the TAILGATE runs; None where a run is missing."""
    f, m = {}, {}
    for t in (15, 19, 23):
        p = SIM / f"bagC_tg_PR{t}" / "results.json"
        if p.exists():
            r = json.loads(p.read_text())["cases"]
            if "fill" in r:
                f[t] = r["fill"]["volume"]["contents_cg_mm"][1]
            if "meat" in r:
                m[t] = r["meat"]["volume"]["contents_cg_mm"][1]
    return f, m


def zones_tailgate(size="M"):
    Z = L.zones_integrated(size)
    for k in ("wing_L", "wing_R"):
        Z[k].name = Z[k].name.replace("wing", "side straps")
    Z["scope_sleeve_L"].name = "IMP-1 padded scope sleeve on the left gusset (under the side straps)"
    Z["door_pocket"].name = "IMP-4 zipped pocket inside the tailgate lid"
    pk = {p["id"]: p for p in TG.pockets()}
    s = pk["IMP-C1"]
    Z[SNACK_ZONE] = L.Zone(SNACK_ZONE, "IMP-C1 snack / GPS sleeve, right J-strap", "strap", 1, s["volume_L"],
                           tuple(sorted(s["interior_mm"], reverse=True)), False)
    return Z


def install():
    L.zones_integrated_orig = getattr(L, "zones_integrated_orig", L.zones_integrated)
    orig = L.zones_integrated_orig

    def zones(config="today"):
        if str(config).startswith("tailgate"):
            size = config.split(":")[1] if ":" in config else "M"
            L.zones_integrated = orig
            try:
                return zones_tailgate(size)
            finally:
                L.zones_integrated = orig
        return L.zones.__wrapped__(config)
    zones.__wrapped__ = getattr(L.zones, "__wrapped__", L.zones)
    L.zones = zones
    # door: the full face from the floor (z 35) to the lid top (z 650)
    CO.DOOR = dict(CO.DOOR, z_lo=float(L.BC.Z0), z_hinge=LID_TOP, inset=0.0)
    f, m = sim_cg()
    L.SIM_FILL_CG.update(f)
    L.SIM_MEAT_CG.update(m)
    L._MEAT_PEEL.clear()
    return f, m


def data_tailgate():
    d = copy.deepcopy(L.load_yaml())
    for iid in ("snacks_today", "gps"):
        pr = d["items"][iid]["pref"]
        i = pr.index("top_pouch") if "top_pouch" in pr else len(pr)
        d["items"][iid]["pref"] = pr[:i] + [SNACK_ZONE] + pr[i:]
    return d


def pack(rows, cfg, meat_kg=0.0):
    P = L.pack(rows, cfg, meat_kg=meat_kg)
    for r in P.rows:          # the frame column is reachable through the full-face lid too
        if r.get("slot") and r["zone"] in P.zones and P.zones[r["zone"]].kind == "bagcol":
            col, z0, z1 = r["slot"]
            if z0 < LID_TOP - 30:
                r["access_cls"] = 4
                r["ok"] = r["access_cls"] <= r["required"]
    return P


def run():
    f, m = install()
    data = data_tailgate()
    res = {"peel_source": "TAILGATE sims " + str(sorted(f)) if f else "CORRIE sims (TAILGATE runs not found)",
           "sim_fill_cg": dict(L.SIM_FILL_CG), "sim_meat_cg": dict(L.SIM_MEAT_CG), "cases": {}}
    for size in CO.BELT_SIZES:
        for key, lo in data["loadouts"].items():
            variants = [("rifle", False)] + ([("archery", True)] if lo.get("archery_swap") else [])
            for vname, arch in variants:
                rows = L.split_units(L.expand(data, key, archery=arch))
                P = pack(rows, f"tailgate:{size}")
                s = L.summary(P, f"{lo['name']} [{vname}, TAILGATE, belt {size}]")
                s["cg_y_rev_c_23in"] = round(float(s["cg_geo_mm"][1]) + L.peel(23), 1)
                s["zones"] = {r["id"]: (r["zone"], r["access_cls"]) for r in P.rows}
                s["hourly_misses"] = [r["id"] for r in P.rows if r["access"] in ("constant", "hourly") and not r["ok"]
                                      and r["zone"] != "hands"]
                s["class4_misses"] = [r["id"] for r in P.rows if r["required"] == 4 and not r["ok"]]
                res["cases"][f"{key}_{vname}_{size}"] = s
                mk = lo["meat_case"]["meat_kg"]
                Pm = pack(L.split_units(L.expand(data, key, archery=arch, meat_day=True)), f"tailgate:{size}", meat_kg=mk)
                sm = L.summary(Pm, f"{lo['name']} pack-out {mk} kg [TAILGATE, {size}]")
                sm["cg_y_rev_c_23in"] = round(float(sm["cg_geo_mm"][1]) + L.peel_meat(23), 1)
                res["cases"][f"{key}_{vname}_{size}_meat"] = sm
    return res


def _json(o):
    return L._json(o)


if __name__ == "__main__":
    res = run()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "loadout_C.json").write_text(json.dumps(res, indent=1, default=_json))
    print(res["peel_source"])
    for k, s in res["cases"].items():
        if k.endswith("_M") or k.endswith("_M_meat"):
            print(f"{k:24s} bag {s['bag_load_g'] / 1000:5.1f} kg CG {s['cg_geo_mm']} 15/19/23 "
                  f"{s['cg_y_rev_c_15in']}/{s['cg_y_rev_c_19in']}/{s['cg_y_rev_c_23in']} (lim {s['rev_c_limit_y']}) "
                  f"float {s['float_mode']} misses {s.get('hourly_misses')} c4 {s.get('class4_misses')}")
    for k, s in res["cases"].items():
        if not k.endswith("_meat"):
            print(k, s["hourly_misses"])
