"""BL-034 part A: thread mass and beginner build hours of CORRIE F rev 3 (door D2) from the sewing operation sequence.

    python designs/pack_5200/build_effort_rev3.py            # print
    python designs/pack_5200/build_effort_rev3.py --write    # also write analysis/build_effort_rev3.json

The ledger booked 4 g of bag thread (two 2 g rows) and ``corrie_f.build_metrics`` booked 44.5 beginner hours from the
``bag_concepts.HOURS`` body model plus the pockets and add-ons, without the webbing parts, the drafted lid or the
drafted fly. The manufacturing package (``mfg_corrie_f_rev3.ops``, read only here) sequences every operation on the
released pattern with its stitch length and its HOURS-model time. This module sums those operations:

* thread in the bag = sum over ops (stitch length x THREAD_FACTOR x record g/m of the op's thread), **without** the
  cone waste (THREAD_WASTE is spool loss, it does not go into the bag; the BOM's "g in the bag" includes it);
* hours = sum of ``proto_h`` of the per-bag ops; the one-off set-up ops (test square, swatches, first-article load
  samples) are reported apart;
* every op is given a weight configuration (base / as_hunted / meat_trip) from the pattern pieces it sews
  (``RevSet.meta`` kit: base -> base, as_hunted / addon -> as_hunted, meat_trip -> meat_trip; an op that sews any base
  piece is base; prep and finish ops are base);
* ops that sew the same webbing part twice (the step-2 / step-4 op and the step-7 webbing op on the same id with the
  same stitch length: IME, T3, HE) are counted once (FOUND in BL-034: the package double-counts them; reported, the
  package is part C's).

The result is cached in ``analysis/build_effort_rev3.json`` so that the ledger (``corrie_f.parts``) does not rebuild
the pattern on every call; ``tests/test_build_effort_rev3.py`` checks the cache against a fresh run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

CACHE = HERE / "analysis" / "build_effort_rev3.json"
KIT_CFG = {"base": "base", "as_hunted": "as_hunted", "addon": "as_hunted", "meat_trip": "meat_trip"}
CFG_ORDER = ("base", "as_hunted", "meat_trip")


def _ids(op, known: set) -> list:
    toks = [t.strip().split(" x")[0].strip() for t in op.pieces.replace(";", ",").split(",")]
    return [t for t in toks if t in known]


def compute() -> dict:
    import mfg_corrie_f_rev3 as M
    ctx = M.build_ctx()
    oplist = M.ops(ctx)
    rs = ctx.rs
    meta = {pid: m["kit"] for pid, m in rs.meta.items()}
    for w in rs.webbing:                             # cord / elastic lines that are not drawn as pieces
        meta.setdefault(w["id"], "as_hunted" if "as hunted" in w["kit"] or w["kit"].startswith("crown")
                        else w["kit"] if w["kit"] in KIT_CFG else "base")
    known = set(meta)
    seen, rows = {}, []
    for o in oplist:
        ids = _ids(o, known)
        kits = {KIT_CFG.get(meta[i], "base") for i in ids}
        cfg = "base" if (not kits or "base" in kits) else ("as_hunted" if "as_hunted" in kits else "meat_trip")
        dup = None
        if o.step.startswith("7 ") and o.length_mm and len(ids) == 1 and (ids[0], round(o.length_mm)) in seen:
            dup = seen[(ids[0], round(o.length_mm))]
        if o.length_mm and len(ids) >= 1:
            for i in ids:
                seen.setdefault((i, round(o.length_mm)), o.seq)
        g = 0.0
        if o.thread_id.startswith("bonded") and o.length_mm:
            g = o.length_mm / 1000.0 * M.THREAD_FACTOR * float(M.mat(o.thread_id).require("mass_g_m"))
        rows.append({"seq": o.seq, "op": o.operation[:80], "step": o.step, "cfg": cfg, "per_bag": o.per_bag,
                     "thread_id": o.thread_id, "length_mm": round(o.length_mm, 1), "thread_g": round(g, 3),
                     "hours": round(o.proto_h, 3), "duplicate_of": dup})
    live = [r for r in rows if not r["duplicate_of"]]
    thread = {c: round(sum(r["thread_g"] for r in live if r["cfg"] == c), 2) for c in CFG_ORDER}
    hours = {c: round(sum(r["hours"] for r in live if r["cfg"] == c and r["per_bag"]), 2) for c in CFG_ORDER}
    by_step = {}
    for r in live:
        if r["per_bag"]:
            by_step[r["step"]] = round(by_step.get(r["step"], 0.0) + r["hours"], 2)
    pkg_h = round(sum(r["hours"] for r in rows), 2)
    return {
        "source": "mfg_corrie_f_rev3.ops on patterns_corrie_f_rev3.build('today') (door D2, crown kit M)",
        "thread_factor": M.THREAD_FACTOR, "thread_waste_excluded": M.THREAD_WASTE,
        "thread_g": thread, "thread_g_total": round(sum(thread.values()), 2),
        "thread_g_package_incl_waste_and_duplicates": round(
            sum(r["thread_g"] for r in rows) * (1 + M.THREAD_WASTE), 2),
        "hours_per_bag": hours, "hours_per_bag_total": round(sum(hours.values()), 2),
        "hours_one_off": round(sum(r["hours"] for r in rows if not r["per_bag"]), 2),
        "hours_package_total": pkg_h, "hours_by_step": by_step,
        "duplicates": [{"seq": r["seq"], "op": r["op"], "of": r["duplicate_of"], "hours": r["hours"],
                        "thread_g": r["thread_g"]} for r in rows if r["duplicate_of"]],
        "booked_before": {"thread_g": 4.0, "hours_with_addons": 44.5},
        "ops": rows,
    }


def load() -> dict:
    return json.loads(CACHE.read_text())


def write(d: dict | None = None) -> dict:
    d = d or compute()
    CACHE.write_text(json.dumps(d, indent=1))
    return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    d = write() if a.write else compute()
    print(json.dumps({k: v for k, v in d.items() if k != "ops"}, indent=1))


if __name__ == "__main__":
    main()
