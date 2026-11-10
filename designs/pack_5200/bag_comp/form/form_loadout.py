"""CHERT loadout / access re-run, by the CORRIE pattern (designs/pack_5200/concepts/corrie_loadout.py, B.2 zones:
pouch, wings, scope sleeve, hipbelt pockets, strap phone pocket, holster, door pocket).

What changes for CHERT: the main-bag columns use CHERT's section (chamfered, form.make), the bulge factor and the
cloth-sim peel come from CHERT's own sims (outputs/clothsim/chert_PR{15,19,23}c) when present, and the door is the
blade door (same z 110-650 hinge, so the access classes are the same rule). The external zones are CORRIE B.2's,
unchanged on CHERT.

    python designs/pack_5200/bag_comp/form/form_loadout.py     # -> designs/pack_5200/bag_comp/form/loadout.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import form as F  # noqa: E402
import form_sim as FS  # noqa: E402

F.CO.make = lambda rev=None: F.make()          # this process only: the loadout model reads CHERT's envelope
import corrie_loadout as LO  # noqa: E402

# CHERT addition (fixes CORRIE's snack miss on S-L belts): IMP-6R, a snack / GPS stretch pocket on the RIGHT J-strap,
# mirror of IMP-6 but deeper: 110 x 210 face, 50 mm stretch mesh bellows (DECISION). Mass: IMP-6 (11.1 g, 90 x 175)
# scaled by face area x 1.15 for the bellows = 15.0 g (ASSUMPTION, booked in form.knap_mass via STRAP_SNACK_G).
SNACK = {"w": 110.0, "h": 210.0, "depth": 50.0}
_zi = LO.zones_integrated


def zones_chert(size="M"):
    Z = _zi(size)
    Z["strap_pocket_R"] = LO.Zone("strap_pocket_R", "IMP-6R right-strap snack / GPS pocket (CHERT)", "strap", 1,
                                  round((SNACK["w"] - 10) * (SNACK["h"] - 10) * SNACK["depth"] / 1e6, 2),
                                  (SNACK["h"] - 10, SNACK["w"] - 10, SNACK["depth"]), False)
    return Z


LO.zones_integrated = zones_chert


def _map_keys(data):
    ks = list(data["loadouts"])
    out = {}
    for k in ks:
        kl = k.lower()
        if "day" in kl:
            out["day"] = k
        elif "elk" in kl:
            out["elk6"] = k
        elif "sheep" in kl:
            out["sheep8"] = k
    return out


def calibrate():
    t = FS.cg_table()
    src = "CORRIE sims (CHERT sims not run)"
    if len(t["fill"]) == 3:
        LO.SIM_FILL_L = tuple(t["volume_L"][f"fill_{k}"] for k in (15, 19, 23))
        res = {}
        for to in (15, 19, 23):
            d = json.loads((FS.OUT / f"chert_PR{to}c" / "results.json").read_text())["cases"]
            res[to] = (d["fill"]["volume"]["contents_cg_mm"][1], d["meat"]["volume"]["contents_cg_mm"][1])
        LO.SIM_FILL_CG = {k: v[0] for k, v in res.items()}
        LO.SIM_MEAT_CG = {k: v[1] for k, v in res.items()}
        src = "CHERT sims outputs/clothsim/chert_PR{15,19,23}c"
    LO.G = LO.corrie_geom()
    LO._MEAT_PEEL.clear()
    return src


def run(sizes=("S", "M", "L", "XL", "XXL")):
    src = calibrate()
    data = LO.load_yaml()
    km = _map_keys(data)
    out = {"calibration": src, "geometry": {"v_geo_L": round(LO.G["v_geo"], 2), "bulge": round(LO.G["kb"], 3)},
           "keys": km, "by_size": {}, "misses_M": {}, "hourly_misses_M": {}}
    for size in sizes:
        cfg = f"integrated:{size}"
        out["by_size"][size] = {}
        for short, key in km.items():
            rows = LO.split_units(LO.expand(data, key))
            force = {}
            for r in rows:      # CHERT packing rule: snacks and GPS go to IMP-6R when the hip pockets are full
                if r["id"] in ("snacks_today", "gps"):
                    pr = list(r["pref"])
                    i = max([k + 1 for k, p in enumerate(pr) if p.startswith("hip")] + [0])
                    force[r["id"]] = pr[:i] + ["strap_pocket_R"] + pr[i:]
            P = LO.pack(rows, cfg, force=force)
            s = LO.summary(P, f"{key} [CHERT, belt {size}]")
            fails = {f: v["fail"] for f, v in s["access"].items() if v["fail"]}
            out["by_size"][size][short] = {"fails": fails, "cg_y_15": s["cg_y_rev_c_15in"],
                                           "cg_y_19": s["cg_y_rev_c_19in"], "cg_z": s["cg_geo_mm"][2],
                                           "main_used_L": s["main_bag_used_L"], "cap_L": s["main_bag_cap_L"],
                                           "top_z": s["top_z"], "unplaced": s["unplaced"]}
            if size == "M":
                out["misses_M"][short] = sum(len(v) for v in fails.values())
                out["hourly_misses_M"][short] = fails.get("hourly", [])
    return out


if __name__ == "__main__":
    r = run()
    (HERE / "loadout.json").write_text(json.dumps(r, indent=1, default=LO._json))
    print(json.dumps({k: r[k] for k in ("calibration", "geometry", "keys", "misses_M", "hourly_misses_M")}, indent=1))
    for s, d in r["by_size"].items():
        for k, v in d.items():
            print(s, k, v["fails"], v["cg_y_15"], v["top_z"])
