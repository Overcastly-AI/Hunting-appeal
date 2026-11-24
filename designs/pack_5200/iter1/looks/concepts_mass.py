"""BL-063 looks concepts: mass delta of each concept against CORRIE F rev 3, from the release cut list areas and the
material records' areal densities. Prints a table and writes ``concepts_mass.json``.

    python designs/pack_5200/iter1/looks/concepts_mass.py

Every number traces to: ``outputs/release/pack5200_corrie_f_rev3/patterns/cutlist.csv`` (cut area per piece, which
includes seam allowance) and ``data/materials/textiles/<record>.yaml`` (``areal_density_gsm``). A colour or print-file
change on the same record is 0 g. Seam deltas use the stated SEAM-ADD assumption.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
CUT = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "patterns" / "cutlist.csv"
MAT = ROOT / "data" / "materials" / "textiles"
HYPERD = "polyester_300d_printable"        # RBTR HyperD 300, the BL-037 G-2 camo base (gated by AB-1)


def gsm(rec: str) -> float:
    return float(yaml.safe_load((MAT / f"{rec}.yaml").read_text())["properties"]["areal_density_gsm"])


def cut() -> dict:
    out = {}
    with CUT.open() as f:
        for r in csv.DictReader(f):
            out.setdefault(r["piece_id"], {"material": r["material"], "area": float(r["total_area_m2"]),
                                           "piece": r["piece"]})
    return out


def swap(c, pid, to):
    p = c[pid]
    d = p["area"] * (gsm(to) - gsm(p["material"]))
    return {"piece": pid, "what": f"{p['piece']}: {p['material']} -> {to}", "area_m2": round(p["area"], 5),
            "delta_g": round(d, 1)}


def zero(pid, what):
    return {"piece": pid, "what": what, "area_m2": None, "delta_g": 0.0}


def concepts() -> dict:
    c = cut()
    A = [zero("webbing / binding / zip tape / thread", "dyed Elk Wallow instead of Deadfall Shadow, same records "
              "(ASSUMPTION TONAL-WEB: same g/m in the olive dye lot)"),
         zero("SH-07, B-29f", "printed solid body colour instead of camo (print-file change, same 630D piece)"),
         zero("guy toggles", "tonal instead of blaze (same POM part, other colour)")]
    B = A[:1] + [swap(c, "B-03", HYPERD),
                 zero("B-02u, SH-07", "printed solid body colour (print-file change); the zip-carrying blade stays "
                      "630D")]
    # B-07 hem (roll-clip strap origin, HDPE strip) and B-29g strap channels stay 330D: HyperD 300 tears at
    # 31.6 / 24.5 N against 90 / 80 N (records), so no printed fabric goes where a strap or clip pulls
    C = A[:1] + [swap(c, "B-06", HYPERD), swap(c, "B-29a", HYPERD),
                 swap(c, "B-29c", HYPERD), swap(c, "B-29d", HYPERD), swap(c, "B-29e", HYPERD),
                 zero("B-07, B-29g", "stay cordura 330D, solid body colour (strap / clip load points)"),
                 zero("B-02u", "printed camo on the 75 mm kick strip only, blades solid (print-file split, no seam)"),
                 zero("SH-07", "printed solid body colour")]
    opt = {"B alt: gussets on 630D printable instead of HyperD 300": swap(c, "B-03", "polyester_ht_630d_printable"),
           "C option: delete the B-29f camo corner caps (overlay; lid is camo already)":
               {"piece": "B-29f", "what": "delete overlay", "area_m2": c["B-29f"]["area"],
                "delta_g": -round(c["B-29f"]["area"] * gsm(c["B-29f"]["material"]), 1)}}
    out = {}
    for k, rows in (("A", A), ("B", B), ("C", C)):
        out[k] = {"rows": rows, "total_g": round(sum(r["delta_g"] for r in rows), 1),
                  "camo_print_area_m2": None}
    base_print = 0.201                               # camo README section 2: one set = 0.201 m2 (9 pieces)
    out["A"]["camo_print_area_m2"] = round(base_print - c["SH-07"]["area"] - c["B-29f"]["area"], 3)
    out["B"]["camo_print_area_m2"] = round(base_print - c["SH-07"]["area"] - c["B-02u"]["area"] + c["B-03"]["area"], 3)
    out["C"]["camo_print_area_m2"] = round(base_print - c["SH-07"]["area"] + sum(c[p]["area"] for p in (
        "B-06", "B-29a", "B-29c", "B-29d", "B-29e")) - 0.8 * c["B-02u"]["area"], 3)
    out["note_C_print"] = ("C keeps ~20 % of B-02u printed (the 75 mm kick strip is about 1/5 of the U's area: "
                           "ASSUMPTION KICK-SHARE)")
    out["options"] = opt
    out["gsm"] = {k: gsm(k) for k in ("cordura_330d_nylon66", "robic_100d_ripstop", HYPERD,
                                      "polyester_ht_630d_printable")}
    return out


def main():
    r = concepts()
    for k in ("A", "B", "C"):
        print(f"Concept {k}: {r[k]['total_g']:+.1f} g, camo print area {r[k]['camo_print_area_m2']} m2")
        for row in r[k]["rows"]:
            print(f"   {row['delta_g']:+6.1f} g  {row['piece']}: {row['what']}")
    for k, row in r["options"].items():
        print(f"option {k}: {row['delta_g']:+.1f} g")
    (HERE / "concepts_mass.json").write_text(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
