"""BL-063 / BL-067 looks concepts: mass delta of each concept against CORRIE F rev 3, from the release cut list areas and the
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
    f = MAT / f"{rec}.yaml"
    if not f.exists():                                     # laminates (ULTRA 200X) live in their own folder
        f = next((ROOT / "data" / "materials").glob(f"*/{rec}.yaml"))
    return float(yaml.safe_load(f.read_text())["properties"]["areal_density_gsm"])


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
                 zero("SH-07, FP-b", "printed solid body colour (two camo zones only: cap and plinth)")]
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
        "B-06", "B-29a", "B-29c", "B-29d", "B-29e")) - 0.8 * c["B-02u"]["area"] - c["FP-b"]["area"], 3)
    out["note_C_print"] = ("C keeps ~20 % of B-02u printed (the 75 mm kick strip is about 1/5 of the U's area: "
                           "ASSUMPTION KICK-SHARE)")
    out["options"] = opt
    out["gsm"] = {k: gsm(k) for k in ("cordura_330d_nylon66", "robic_100d_ripstop", HYPERD,
                                      "polyester_ht_630d_printable")}
    return out


# =====================================================================================================================
# BL-067 (review 7 M5): the same concepts on the LEDGER scenarios (iter1_weight.rows), not on the release cut list.
# The release cut list carries rev 3's fabrics; the ledger's proven now (P) and after tests (A) carry each piece in the
# fabric of that scenario (A swaps B-06 to 70D, B-03 / B-02door to ULTRAGrid, B-02u / SH-07 to HyperD by BL-037 G-2),
# and the B-29 crown lid is an as-hunted add-on, never base. A delta = cut area x (new g/m2 - the piece's g/m2 in that
# scenario); for a piece with its own ledger row the row's mass is checked against cut area x g/m2 (test).
# =====================================================================================================================
SYSTEM = HERE.parent / "system"
LID = ("B-29a", "B-29b", "B-29c", "B-29d", "B-29e", "B-29f", "B-29g")
G2_A = ("B-02u", "SH-07")     # BL-037 G-2 (A_bl037): 'B-02u + SH-07 camo 630D -> HyperD 300', a row without per-piece names
HDPE_ROW = "B-07s"


def _iw():
    import sys
    for q in (str(SYSTEM), str(HERE.parents[1])):
        if q not in sys.path:
            sys.path.insert(0, q)
    import iter1_weight as IW
    return IW


def ledger_material(scen: str, pid: str):
    """The piece's fabric in scenario P or A: the last positive 'CORRIE F: <pid> ...(<record>' row; lid pieces and
    pieces without a row keep the release fabric; G-2 pieces are HyperD in A."""
    import re
    rx = re.compile(rf"CORRIE F: {re.escape(pid)} .*\(([a-z0-9_]+)")
    mat = None
    for r in _iw().rows(scen, "as_hunted"):
        m = rx.search(r["name"])
        if m and r["g"] > 0:
            mat = m.group(1)
    if scen == "A" and pid in G2_A:
        mat = HYPERD
    return mat or cut()[pid]["material"]


def ledger_row_g(scen: str, pid: str) -> float:
    """Net ledger mass of a piece with its own row (P or A, as hunted superset)."""
    import re
    rx = re.compile(rf"CORRIE F: {re.escape(pid)} ")
    return round(sum(r["g"] for r in _iw().rows(scen, "as_hunted") if rx.search(r["name"])), 2)


def ledger_swap(pid: str, to: str) -> dict:
    """One fabric swap on the ledger basis: delta per scenario and whether it is base or as-hunted (lid)."""
    c = cut()[pid]
    out = {"piece": pid, "to": to, "area_m2": round(c["area"], 5), "cfg": "as_hunted" if pid in LID else "base"}
    for sc_ in ("P", "A"):
        m = ledger_material(sc_, pid)
        out[f"from_{sc_}"] = m
        out[f"d_{sc_}"] = round(c["area"] * (gsm(to) - gsm(m)), 1)
    return out


# ---- C' geometry proposals (looks_render.py ROLL_HALF_MM / WRAP_LEVEL_Z / LID-LOCK): mass on the same basis
ROLL_HALF_TODAY = 262.45      # cloth_pass meta lip half (flattened mouth (W + D) / 2), all three states
ROLL_HALF_CP = 192.0          # looks_render.ROLL_HALF_MM
COLLAR_H = 494.8              # bag_concepts COLLAR_H (cloth_pass._ss().BC.COLLAR_H): collar cut height, seam -> mouth


def taper() -> dict:
    """ROLL-TAPER: the mouth perimeter drops 4 x (262.45 - 192) mm; the cut is taken out as a straight wedge at the two
    B-06 | B-06f side seams (half from each piece), zero at the collar seam (ASSUMPTION TAPER-WEDGE: linear taper over
    the whole collar height). Hem B-07 and the two B-07s HDPE strips shorten in proportion to the mouth."""
    dP = 4.0 * (ROLL_HALF_TODAY - ROLL_HALF_CP)
    mouth = 4.0 * ROLL_HALF_TODAY
    wedge = 0.5 * dP * COLLAR_H / 1e6                         # m2, both side seams together
    f = dP / mouth
    rows = []
    for sc_ in ("P", "A"):
        g = {"B-06": 0.5 * wedge * gsm(ledger_material(sc_, "B-06")),
             "B-06f": 0.5 * wedge * gsm(ledger_material(sc_, "B-06f")),
             "B-07": f * cut()["B-07"]["area"] * gsm(ledger_material(sc_, "B-07")),
             "B-07s": f * ledger_row_g(sc_, HDPE_ROW)}
        rows.append((sc_, {k: round(-v, 1) for k, v in g.items()}))
    return {"perimeter_cut_mm": round(dP, 1), "mouth_today_mm": round(mouth, 1), "wedge_m2": round(wedge, 4),
            "hem_fraction": round(f, 3), "P": rows[0][1], "A": rows[1][1],
            "d_P": round(sum(rows[0][1].values()), 1), "d_A": round(sum(rows[1][1].values()), 1)}


def collar_volume_loss_L(depth_mm: float = 2 * ROLL_HALF_TODAY - 394.0, h_mm: float = 248.0) -> float:
    """ASSUMPTION COLLAR-RULED: the standing collar (full load, 248 mm from the seam to the lip in the cloth pass) is a
    ruled shape from the W x D seam rectangle to a flat mouth line of length Lm; V = h D (W/2 + (Lm - W)/6). Loss =
    h D (Lm_today - Lm_new) / 6, W = 394 mm (RULES 9 cap), D = 2 x 262.45 - W."""
    return h_mm * depth_mm * (2 * ROLL_HALF_TODAY - 2 * ROLL_HALF_CP) / 6.0 / 1e6


def lid_locks() -> dict:
    """LID-LOCK: the two REAR crown-strap ladder locks deleted; the strap's rear end is box-X'd to the same B-28t tab
    (the rated 'crown strap tab' row keeps its box; its hardware column goes from ladder-lock slip to none). Webbing:
    ASSUMPTION LOCK-WEB 0 g net (the 30 mm lock wrap becomes the 30 mm box fold). As hunted only (crown straps are an
    add-on)."""
    import yaml as _y
    g = float(_y.safe_load((ROOT / "data" / "materials" / "hardware" / "ladder_lock_25mm_heavy.yaml").read_text())
              ["properties"]["mass_g"])
    return {"n": 2, "lock_g": g, "d": -2 * g}


def rt_cut() -> dict:
    """The two roll-clip straps re-cut for the tapered roll (looks_render.cp_checks: strap_tails.roll_row's rule on the
    re-run clip paths, RTM tab where the release has it). 0 g until cp_checks.json exists."""
    f = HERE / "cp_checks.json"
    if not f.exists():
        return {"today_mm": None, "Cp_mm": None, "d": 0.0}
    r = json.loads(f.read_text())["roll_clip"]
    g_m = float(yaml.safe_load((ROOT / "data" / "materials" / "webbing" / "poly_webbing_25mm.yaml").read_text())
                ["properties"]["mass_g_m"])
    d = 2 * (r["Cp"]["cut_mm"] - r["today"]["cut_mm"]) / 1000.0 * g_m
    return {"today_mm": r["today"]["cut_mm"], "Cp_mm": r["Cp"]["cut_mm"], "g_m": g_m, "d": round(d, 1)}


def ledger_concepts() -> dict:
    """Every concept's delta on base proven now / base after tests / as hunted (P, A); gram rows listed."""
    out = {}
    defs = {"A": [], "B": [ledger_swap("B-03", HYPERD)],
            "C": [ledger_swap("B-06", HYPERD)] + [ledger_swap(p, HYPERD) for p in ("B-29a", "B-29c", "B-29d", "B-29e")],
            "Cp": [ledger_swap("B-29a", HYPERD)]}
    for k, rows in defs.items():
        r = {"swaps": rows}
        for sc_ in ("P", "A"):
            b = sum(x[f"d_{sc_}"] for x in rows if x["cfg"] == "base")
            h = sum(x[f"d_{sc_}"] for x in rows)
            r[f"base_{sc_}"], r[f"hunted_{sc_}"] = round(b, 1), round(h, 1)
        out[k] = r
    # C' with its geometry proposals (each its own gate; listed so the owner can take them one by one)
    t, lk, rt = taper(), lid_locks(), rt_cut()
    cp = out["Cp"]
    cp["geometry"] = {"ROLL-TAPER": t, "LID-LOCK": lk, "RT-CUT": rt,
                      "collar_volume_loss_L": round(collar_volume_loss_L(), 2)}
    for sc_ in ("P", "A"):
        cp[f"base_{sc_}_with_geometry"] = round(cp[f"base_{sc_}"] + t[f"d_{sc_}"] + rt["d"], 1)
        cp[f"hunted_{sc_}_with_geometry"] = round(cp[f"hunted_{sc_}"] + t[f"d_{sc_}"] + rt["d"] + lk["d"], 1)
    # options (not in C'): delete the B-29f caps; B-02u in dyed body cloth (no print needed once it is solid)
    out["options"] = {
        "B-29f caps deleted (C / C')": {sc_: -round(cut()["B-29f"]["area"] * gsm(cut()["B-29f"]["material"]), 1)
                                        for sc_ in ("P", "A")} | {"cfg": "as_hunted"},
        "B-02u solid in the door's dyed cloth instead of a solid print (C')":
            {sc_: round(cut()["B-02u"]["area"] * (gsm(ledger_material(sc_, "B-02door")) -
                                                  gsm(ledger_material(sc_, "B-02u"))), 1) for sc_ in ("P", "A")}
            | {"cfg": "base", "note": "loses the camo-ready blade U; the zip-carrying blade on 330D / ULTRAGrid "
                                      "needs the AB-1 / A_fab gates of the door cloth"},
    }
    return out


def main():
    r = concepts()
    for k in ("A", "B", "C"):
        print(f"Concept {k}: {r[k]['total_g']:+.1f} g (release cut list), camo print area {r[k]['camo_print_area_m2']} m2")
        for row in r[k]["rows"]:
            print(f"   {row['delta_g']:+6.1f} g  {row['piece']}: {row['what']}")
    for k, row in r["options"].items():
        print(f"option {k}: {row['delta_g']:+.1f} g")
    L = ledger_concepts()
    print("\nLedger basis (review 7 M5): base P / base A / as hunted P / as hunted A")
    for k in ("A", "B", "C", "Cp"):
        x = L[k]
        print(f"  {k:3s} {x['base_P']:+6.1f} {x['base_A']:+6.1f} {x['hunted_P']:+6.1f} {x['hunted_A']:+6.1f}")
    cp = L["Cp"]
    print(f"  C' + geometry: base {cp['base_P_with_geometry']:+.1f} / {cp['base_A_with_geometry']:+.1f}, hunted "
          f"{cp['hunted_P_with_geometry']:+.1f} / {cp['hunted_A_with_geometry']:+.1f}; taper {cp['geometry']['ROLL-TAPER']}")
    r["ledger"] = L
    r["Cp"] = {"what": "C' (BL-067): camo on the lid crown B-29a only (HyperD 300 printed), A's Elk Wallow trim, "
                       "B-02u / SH-07 / FP-b / B-29 walls printed or dyed solid, B-06 solid on its own fabric",
               "camo_print_area_m2": round(cut()["B-29a"]["area"] + cut()["B-29f"]["area"], 3)}
    (HERE / "concepts_mass.json").write_text(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
