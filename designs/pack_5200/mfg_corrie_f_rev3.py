"""BL-032 part B / BL-034 part C: CORRIE F rev 3 manufacturing package (manufacturing-engineer, 2026-11-13).

    python designs/pack_5200/mfg_corrie_f_rev3.py            # regenerate the package
    python designs/pack_5200/mfg_corrie_f_rev3.py --check    # build + print the checks, write nothing

Writes ``outputs/release/pack5200_corrie_f_rev3/manufacturing/`` (BOM, cutting plan, sewing operation sequence,
bartack / load-point table, QC sheet, release tests, defect list, packaging, costing, delta-register close-out, the
tech pack PDF and its raster preview) and phone screenshots ``outputs/screens/20261113_BL034C_<n>.png``.

Everything is regenerated from the pattern module ``patterns_corrie_f_rev3.build()`` (read only) and the released
part A markers (``patterns/markers/markers.json``). Nothing here is hand-typed geometry: seam lengths come from the
pattern's own seam pairs, placements (B-22 x, FP width, swell windows, B-27 slits) from the pieces, cut lengths from
``RevSet.webbing``, the lid operations from ``patterns_corrie_f_rev3.lid_hours``, box-X sizes from the box marks drawn on
the pieces, the B-11 / K-W / F-02 placements from ``RevSet.geo``. When the pattern changes (a new webbing piece, a box
size, a keeper height, a cord), re-run this script: webbing, cord and elastic pieces get their operation, BOM line and
load-point row from the pattern; pieces no operation names land in step 11 as HOLD; ledger hardware rows the BOM does
not map land as UNMAPPED lines.

Shared code (BL-034 part C): ``SewingOp``, ``BOMLine`` and the tech pack PDF builder live in ``huntkit.manufacturing``
(CONTRACTS.md section 5); this script assembles the CORRIE content (``techpack_design``). Load capacities use
``huntkit.gendesign.attach_system`` (read only).
Units: mm, N, g, USD; inches / lb / oz / yd in the documents.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import patterns_corrie_f_rev3 as P  # noqa: E402  (sets sys.path for concepts/ and the repo root)
from huntkit import materials as MAT  # noqa: E402
from huntkit.gendesign import attach_system as AS  # noqa: E402
from huntkit import manufacturing as MF  # noqa: E402
from huntkit.manufacturing import BOMLine, SewingOp  # noqa: E402,F401  (contract records, CONTRACTS.md section 5)

ROOT = P.ROOT
REL = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3"
PAT = REL / "patterns"
OUT = REL / "manufacturing"
SCREENS = ROOT / "outputs" / "screens"
DATE = "20261113"
TOPIC = "BL044mfg"            # BL-044: screenshots named for the ticket that regenerates the package
TITLE = "CORRIE F rev 3 (door D2) - 5200 cu in hunting pack bag"
REGISTER = ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv"
YD = 914.4
IN = 25.4
GUY_N = 288.0                  # corrie_f_body.md 13.5: port guy envelope, 96.1 N at 1 g x 3.0 (23 in full)
PROOF = 1.5                    # loadpath_verification.md: "Proof rule: 1.5 x factored"
LLH_N = PROOF * GUY_N          # BL-040 M-7: 432 N (was 366 N = 1.5 x the old 244 N A3 guy load)
QC14_TOL_PCT = 3.0             # QC-14 band (BL-032)
PREVIEW_DPI = 110              # BL-040 m-21: 60 dpi previews were unreadable on a phone
# BL-041 (crown_tube_guy_loop.md, orchestrator 2026-11-13): the B-25 tab carries the port guy AND the B-28 crown strap
# (second fold of the same tab): 323 N design envelope (guy 96 N + crown 11.6 N at 1 g, x 3.0); TL-1 proof 494 N (bar
# rule 323 / KD_eff 0.654 governs the sewn 1.5 x 323 = 484 N). Read from crown_tube_guy_loop.json.
_CT = json.loads((ROOT / "designs" / "pack_5200" / "analysis" / "crown_tube_guy_loop.json").read_text())
B25_N = round(_CT["kit_loads"]["envelope"]["static_n"])                                       # 323
TL1_N = round(max(_CT["tl1"]["proof_n"], _CT["tl1"]["bar_rule_proof_n"]))                     # 494
HINGE_N = 1019.0               # load_standard.md rev C / bag_attachment.md section 5: bag-on hinge, factored (BL-040 m-2)

# ============================================================================ shop standards (sources inline)
# Thread: records in data/materials/thread/. Needle sizes for tex 90 / 135: attach_system.NEEDLE (ASSUMPTION there,
# thread-needle chart). Tex 70 -> Nm 90: ASSUMPTION THREAD-NEEDLE (same chart family), settled by the swatch in op 0.04.
THREAD = {"light": "bonded_nylon_tex70", "body": "bonded_nylon_tex90", "box": "bonded_nylon_tex135"}
NEEDLE = {
    "light": "Nm 90/14 DPx17, round point R",
    "mesh": "Nm 90/14 DPx17, medium ball SUK (knit mesh)",
    "body": "Nm 110/18 DPx17, round point R",
    "box": "Nm 140/22 DPx17, round point R",
}
NEEDLE_RULE = ("Round point (R) or slim set point on every coated fabric, laminate, Hypalon and webbing. Never a leather "
               "/ cutting point (LR, S, DI): it cuts the reinforcement and the coating and drops seam strength. "
               "Ball point (SUK) only on the power mesh. New needle every bag (prototype) or every 8 h (production).")
SPI = {"light": 10, "body": AS.SPI["perim"], "box": AS.SPI["box"], "top": AS.SPI["perim"]}   # 10 = ASSUMPTION SPI-LIGHT
SEAM_EFF = AS.SEAM_EFF                         # 0.80, clothsim/fabrics.yaml (301 seam vs the weaker strip)

# BL-040 M-12: the owner has no machine yet and BUILD_PLAN budgeted a domestic machine with 110/18-120/19 needles. Every
# box-X and proof specimen in this release is specified on Nm 140/22 DPx17 + tex 135, so the prototype machine must take it.
PROTO_MACHINE_MIN = ("MINIMUM PROTOTYPE MACHINE (buy this or better): a walking-foot (compound or upper-and-lower feed) "
                     "lockstitch that takes the 135x17 / DPx17 needle system up to size 140/22, sews tex 135 (V-138 / "
                     "No. 138) bonded nylon top and bobbin, and clears at least 6 mm under the raised foot (38 mm "
                     "webbing folded in half + Hypalon + laminate is about 5 mm), AND sews a 304 zigzag up to 5 mm wide "
                     "(BL-041 Y-3: the BT-S / BT-M tacks and elastic laps are ISO 304; e.g. a portable straight / zigzag "
                     "walking foot). A straight-stitch-only walking foot (the WF2 class) may be used if every 304 tack is "
                     "sewn as the BT-301 fallback below. A domestic or 'heavy-duty domestic' "
                     "machine (130/705H needles, tex 90 max) CANNOT sew the load points as specified. The alternative, "
                     "re-rating every box-X for Nm 120/19 + tex 90 and re-running MT-1 / PT-1..PT-6 on it, is an owner "
                     "decision, not taken here.")
# BL-041 Y-3: straight-stitch substitute for every ISO 304 tack in this release. Every 304 tack here is UNRATED (B-27
# slit ends, HE neck tacks, I2K, FP mouth corners, B-16 corners, lid channel ends, BRL / BRS, W3G, B-25 sleeve laps,
# elastic laps): none carries an HA-LS-1 load-table load (load_points.csv: the only 304 rows have no load). The box-X
# load points are ISO 301 already.
BT_301_FALLBACK = ("BT-301 (prototype, straight stitch only): 4 passes over the tack length (16 mm for BT-M, 10 mm "
                   "for BT-S and slit ends, the full lap width for elastic laps) at 2 mm stitch, needle down and pivot at each "
                   "end, 3-stitch backtack, same thread and needle as the 304 tack it replaces. UNRATED, like every 304 "
                   "tack in this release (none is on a load-table path); the PT-3 neck tacks are sewn the same way as the "
                   "bag's.")
MACHINES = {
    "PROTO": PROTO_MACHINE_MIN,
    "BT-301": BT_301_FALLBACK,
    "WF1": "Single-needle compound-feed walking foot lockstitch, Juki DU-1181N (or LU-1508N). Prototype: the PROTO "
           "machine above (it also runs Nm 110 + tex 90 for the body seams).",
    "WF2": "Heavy single-needle walking foot lockstitch, large hook, Juki DNU-1541S (or LU-1561/2210 class): webbing "
           "stacks, Hypalon, tex 135 box-X. Prototype: WF1 hand-cranked through the thick spots.",
    "BT": "Computer bartacker Juki LK-1900BN (ISO 301 path / 304 zigzag, programmable, 40 x 30 mm field): every "
          "25 mm box-X and the slit bartacks. Prototype: box-X on WF2 with the J1 template.",
    "PS": "Programmable pattern sewer Juki AMS-210EN (220 x 100 mm field) with a webbing clamp: the 38 mm box-X that do "
          "not fit the LK-1900 field (HE, T3, B-24). Prototype / small shop: WF2 with the J1 template.",
    "ZZ": "Zigzag lockstitch (ISO 304), Juki LZ-2290 class or a portable straight / zigzag walking foot: elastic laps "
          "and BT-S / BT-M tacks. Prototype without zigzag: the BT-301 fallback.",
    "LASER": "CO2 laser cutter 60-100 W, bed >= 600 x 900 mm, fume extraction: Hypalon, TPU-840D, B-12, port bindings, "
             "HDPE <= 0.8 mm (or shear + round the corners).",
    "HK": "Hot knife, blade type, on a steel / glass plate with the J8 length stop: webbing, elastic, cord.",
    "SK": "Straight knife, 5 in blade (Eastman Blue Streak II class) on a cutting table for production lays. "
          "Prototype: 45 / 60 mm rotary cutter, 600 x 900 mat, 6 x 24 in ruler.",
    "DIE": "Clicker press + steel-rule dies: only above about 500 bags a year (Hypalon tabs, B-12, keepers).",
    "TAPE": "Hot-air seam-tape machine: NOT used. Rev 3 has no taped seams (ASSUMPTION NO-TAPE: the bag is water "
            "resistant, not waterproof; contents go in the user's dry bag). Needed only for a waterproof variant.",
}
SEAMS = {   # seam constructions (ASTM D6193 code; ISO 4916 class / number)
    "SSa2": "SSa plain seam, 12 mm allowance, then both allowances turned to one side and caught by a 2nd row at 6 mm "
            "(ISO 4916 1.01.01, two rows; no binding, see ASSUMPTION NO-BIND)",
    "SSa": "SSa plain seam, single row (ISO 4916 1.01.01)",
    "SSa-ins": "SSa with a webbing tab / loop inserted between the plies (ISO 4916 class 1 with insert); tab ends reach "
               "the cut edge, a backtack each side of the tab",
    "LSd": "LSd lapped patch: piece laid flat on the panel, perimeter row(s) (ISO 4916 class 2, lapped)",
    "EFa": "EFa edge turned once and edge-stitched (ISO 4916 class 6, edge finish)",
    "EFb": "EFb edge turned twice, stitched (ISO 4916 class 6); hem round a stiffener strip",
    "ZIP": "zip set: each tape laid face down on its panel edge, sewn at 5 mm, turned and edge-stitched at 3 mm "
           "(ISO 4916 class 1, two rows per tape)",
    "BOX": "box-X: rectangle + both diagonals through the webbing stack (ISO 4915 301 path; ISO 4916 class 7 when it "
           "fixes the webbing to a panel)",
    "BT": "bartack, ISO 4915 304 zigzag lockstitch, LK-1900 standard pattern",
    "DART": "dart: fold on the dart centre, sew leg to leg, tie off at the apex (ISO 4916 1.01.01)",
}
BARTACK_STD = {"BT-S": {"len_mm": 10.0, "w_mm": 2.0, "stitches": 28},     # ASSUMPTION BT-STD (LK-1900 short tack)
               "BT-M": {"len_mm": 16.0, "w_mm": 2.0, "stitches": 42}}     # LK-1900 standard tack, 42 stitches
HOURS = P.BC.HOURS                     # bag_concepts.HOURS: the beginner-hours model every bag entry is booked on
WEB_CUT_H = 0.03                       # ASSUMPTION: hot-knife cut + seal per webbing piece (h, beginner)
PLACE_H = 0.05                         # ASSUMPTION: mark + clip one placement (h, beginner)
FACTORY_RATIO = 0.12                   # ASSUMPTION SAM-RATIO: factory SAM = 12 % of beginner hours (time study settles)
UTIL_SMALL = 0.70                      # ASSUMPTION UTIL-SMALL: production utilisation of small / sheet pieces nested across bags
THREAD_FACTOR = 2.75                   # ASSUMPTION: m of thread per m of 301 seam, both threads, incl. ends
THREAD_WASTE = 0.15                    # ASSUMPTION: cone ends, test sewing
WEB_WASTE = 0.05                       # ASSUMPTION: webbing trim, seal and a test piece
# Stainless 25 mm tri-glide (US backstop, orchestrator 2026-11-13): triglide_25mm record, stainless_alt source line
# "EUR 3.10 incl. VAT", converted as the record's own price note (ex 19 % VAT x 1.09 USD/EUR, the record's ASSUMPTION)
TG_SS_USD = round(3.10 / 1.19 * 1.09, 2)
LABOUR = {"us_contract_usd_min": 0.85, "asia_contract_usd_min": 0.12}   # ASSUMPTION LABOUR (loaded CMT minute)
OVERHEAD = 0.25                        # ASSUMPTION: contract overhead + margin on CMT
PRICE_ASSUMED = {   # items with no material record: (usd, per, why). BL-034 C: the 7 hardware / elastic keys that have
    #               records now (slider_10, slider_5, cam_25mm_al, triglide_25mm, pom_toggle, elastic_25mm, elastic_6mm)
    #               are gone, so the record cost_usd is used
    "tpu_hook_sleeve": (0.20, "unit", "ASSUMPTION"),
    "rubber_pull_sleeve": (0.15, "unit", "ASSUMPTION"),
    "basting_tape_6mm": (0.05, "m", "ASSUMPTION"),
    "seam_sealer": (0.80, "bag", "ASSUMPTION: 10 ml of a silicone seam sealer"),
    "label_set": (0.60, "set", "ASSUMPTION: size / care / ID label + hang tag + warning card"),
    "polybag_carton": (0.90, "bag", "ASSUMPTION: 2 recycled poly bags + 1/10 carton"),
}
# BL-041 n-10 / Y-5: what a one-off buyer can actually buy. ASSUMPTIONS SHOP-UNIT (settled by the owner's order):
THREAD_CONE_G = 113.4          # 4 oz cone (the smallest common bonded-nylon put-up); cone price = record $/m x cone length
SHOP_UNIT = {"basting_tape_6mm": (1, "roll of 20 m", 6.00, "ASSUMPTION SHOP-UNIT: smallest roll"),
             "seam_sealer": (1, "tube 1 oz (28 ml)", 8.00, "ASSUMPTION SHOP-UNIT: smallest tube of silicone seam sealer")}
# DECISION CAMO-FIRST (orchestrator, BL-041 Y-5): the first build is solid 630D on the camo panels (camo route D). The
# HyperD 300 print yard is bought by the test kit as the AB-1 / FRAY-1 specimen only (with its shipping), not by the bag.
FIRST_BUILD_CAMO = "solid 630D (polyester_ht_630d_printable, unprinted) on B-02u, SH-07, SH-01b, FP-b, B-29f and A1-d"


# ============================================================================ contract records
# SewingOp and BOMLine: huntkit.manufacturing.records (moved in BL-034 part C, fields unchanged).


# ============================================================================ inputs
@dataclass
class Ctx:
    rs: object                      # primary (today's fabrics)
    rsA: object                     # alternate (team B set)
    seams: dict                     # seam name -> mm (pattern seam pairs)
    markers: dict
    rec: dict
    lid: dict
    register: dict
    notes: list = field(default_factory=list)


def _markers() -> dict:
    f = PAT / "markers" / "markers.json"
    if f.exists():
        return json.loads(f.read_text())
    return {}                                            # fallback handled in the BOM (ASSUMPTION MK-FALLBACK)


def _register() -> dict:
    if not REGISTER.exists():
        return {}
    with REGISTER.open() as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def build_ctx() -> Ctx:
    rs = P.build("today")
    rsA = P.build("B")
    rep = P.seam_report(rs)
    seams = {r.seam.name: round(0.5 * (r.length_a + r.length_b), 1) for r in rep.results}
    lid = P.lid_hours(rs) if hasattr(P, "lid_hours") else P.lid_hours_ops(rs)
    lid.setdefault("bl029_booked_h", None)
    return Ctx(rs=rs, rsA=rsA, seams=seams, markers=_markers(), rec=P.reconcile(rsA), lid=lid, register=_register())


def mat(mid: str):
    try:
        return MAT.load(mid)
    except Exception:
        return None


def cost_per(mid: str, unit: str) -> float | None:
    """Record cost converted to USD per ``unit`` (m2, m, unit, kg)."""
    m = mat(mid)
    if m is None or not m.cost_usd:
        return None
    v, per = float(m.cost_usd["value"]), m.cost_usd["per"]
    if per == unit:
        return v
    if per == "yd" and unit == "m2":
        rw = float(m.get("roll_width_mm") or (P.ROLL_FALLBACK.get(mid, (1500.0,))[0])) / 1000.0
        return v / (YD / 1000.0) / rw
    if per == "yd" and unit == "m":
        return v / (YD / 1000.0)
    if per == "kg" and unit == "m2":                    # sheet goods: density x thickness
        t = float(m.get("thickness_mm") or 0.8)
        return v * float(m.require("density_kg_m3")) * t / 1000.0
    return None


def _len(pts) -> float:
    return float(sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)))


def _closed_perim(pts) -> float:
    return _len(list(pts) + [pts[0]])


def piece_perim(p) -> float:
    return float(sum(p.edge_length(e) for e in p.edge_names))


def lines(p, kind=None, label=None):
    return [ln for ln in p.internal_lines if (kind is None or ln.kind == kind) and (label is None or label in (ln.label or ""))]


def boxes_of(p) -> list[tuple[float, float, str]]:
    """Box-X marks drawn on a piece: (w, h, label) parsed from the pattern's own 'box-X WxH' stitch lines."""
    out = []
    for ln in p.internal_lines:
        lab = ln.label or ""
        if ln.kind == "stitch" and "box-X" in lab and "x" in lab.split("box-X")[-1]:
            dims = lab.split("box-X")[-1].strip().split()[0]
            try:
                w, h = (float(v) for v in dims.split("x"))
            except ValueError:
                continue
            out.append((w, h, lab))
    return out


def seam_mm(ctx: Ctx, name: str) -> float:
    if name not in ctx.seams:
        raise KeyError(f"seam {name!r} not in the pattern's seam list (pattern changed?)")
    return ctx.seams[name]


# ============================================================================ geometry the ops quote
def _b11_box(rs) -> tuple[float, float]:
    """Size of the B-11 sew-down box as drawn on the gusset (BL-034 part A), else on the B-11 piece."""
    for pid in ("B-03", "B-11"):
        p = rs.pieces.get(pid)
        for ln in (lines(p, "stitch", "B-11 sew-down") or lines(p, "stitch", "sew-down")) if p is not None else []:
            xs, ys = [q[0] for q in ln.points], [q[1] for q in ln.points]
            return round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)
    return 24.0, 19.0


def geo(ctx: Ctx) -> dict:
    rs = ctx.rs
    F = P.F
    b01 = rs.pieces["B-01"]
    win = lines(b01, "cut_inside", "swell window")
    fp = rs.pieces["FP-a"]
    fpb = fp.bounds(cut=False)
    g = {
        "b22_x": rs.geo["b22"]["placed_x"], "b22_drawn_x": rs.geo["b22"]["drawn_x"],
        "b22_moved": rs.geo["b22"]["moved_mm"],
        "fp_flat_w": round(fpb[2] - fpb[0], 1), "fp_h": round(fpb[3] - fpb[1], 1),
        "fp_finished_w": (F.fp_spec() if hasattr(F, "fp_spec") else F._A().FP)["w"], "fp_z": P.FP_Z,
        "fp_margin": rs.geo.get("fp_min_margin_mm"), "fp_clear_req": rs.geo.get("fp_clear_req_mm"),
        "b11": rs.geo.get("b11"), "b11_box": _b11_box(rs), "kw_z": rs.geo.get("kw_z") or {},
        "f02": rs.geo.get("f02_on_b05"),
        "swell_ids": sorted(pid for pid in rs.pieces if pid.startswith("B-13")),
        "swell_n": sum(q.quantity for pid, q in rs.pieces.items() if pid.startswith("B-13")),
        "hinge_windows": len(lines(b01, "cut_inside", "HINGE")),
        "us_channels": rs.geo.get("us_channels"), "b16": "B-16" in rs.pieces,
        "port_z": F.PORT_Z, "port_turn": F.PORT_TURN, "port_facing_w": F.PORT_FACING_W,
        "port_slit_mm": round(float(F.guy_port().get("slit_mm", F.PORT_Z[1] - F.PORT_Z[0])), 1)
        if hasattr(F, "guy_port") else F.PORT_Z[1] - F.PORT_Z[0],
        "windows": len(win), "window_perim_mm": round(sum(_closed_perim(w.points) for w in win), 1),
        "swells": dict(P.SWELLS), "hose_z": P.HOSE_Z, "hard_z": F.HARD_Z, "pole_tab_z": P.POLE_TAB_Z,
        "zip_door_mm": round(rs.geo["zip_door_mm"], 1), "lid_zip_mm": P.LID["zip_mm"],
        "crown_tab": F.CROWN_TAB, "z_collar": rs.geo["z_c"],
        "fly_drafted": any(pid.startswith("F-01") for pid in rs.pieces),
        "fly_ids": sorted(pid for pid in rs.pieces if pid.startswith("F-01")),
    }
    return g


# ============================================================================ BOM
def _fabric_pieces(rs):
    return [p for p in rs.all_pieces(sizes={P.KIT}, webbing=False)]


def _kits_of(rs, mid):
    return ",".join(sorted({rs.meta[p.piece_id]["kit"] for p in rs.pieces.values() if p.material_id == mid}))


def _roll_w(mid: str) -> float:
    m = mat(mid)
    return float((m.get("roll_width_mm") if m else None) or P.ROLL_FALLBACK.get(mid, (1500.0,))[0])


UTIL_ALT_LARGE = 0.85      # ASSUMPTION UTIL-ALT: alternate-set production utilisation, materials with > 0.2 m2 net a bag
                           # (the primary 10-bag markers reach 0.88-0.92 on the same pieces); smaller: UTIL_SMALL


def fabric_bom(ctx: Ctx) -> list[BOMLine]:
    """Per material: production quantity a bag (10-bag marker + 3 % lay loss, or net / UTIL_SMALL for small and sheet
    pieces nested across bags) and the 1-bag prototype yield. Alternate column: the team B set on the same pieces."""
    out = []
    mk = ctx.markers
    for setname, rs, key in (("fabric", ctx.rs, "primary_1bag"), ("fabric_alternate", ctx.rsA, "alternate_1bag")):
        other = {p.piece_id: p for p in _fabric_pieces(ctx.rsA if setname == "fabric" else ctx.rs)}
        by_mat: dict = {}
        for p in _fabric_pieces(rs):
            by_mat.setdefault(p.material_id, []).append(p)
        for mid, pcs in sorted(by_mat.items()):
            net = sum(p.area_mm2 * p.quantity for p in pcs) / 1e6
            rw = _roll_w(mid) / 1000.0
            m1 = mk.get(key, {}).get(mid)
            m10 = mk.get("primary_10bag", {}).get(mid) if setname == "fabric" else None
            if m10:
                prod_m = m10["yield_m_per_unit"] * 1.03
                basis = f"10-bag marker eff {m10['efficiency']:.2f} + 3 % lay loss (part A WASTE_PROD)"
            elif setname == "fabric_alternate" and net > 0.2:
                prod_m = net / rw / UTIL_ALT_LARGE
                basis = f"ASSUMPTION UTIL-ALT {UTIL_ALT_LARGE:.2f}"
            else:
                prod_m = net / rw / UTIL_SMALL
                basis = f"ASSUMPTION UTIL-SMALL {UTIL_SMALL:.2f} (small / sheet pieces nested across bags)"
            proto_m = m1["yield_m_per_unit"] if m1 else net / rw / 0.6
            unit = "m2" if mid in P.FREE_ROTATION else "m"
            conv = rw if unit == "m2" else 1.0
            qty, pq = prod_m * conv, proto_m * conv
            uc = cost_per(mid, unit)
            alts = sorted({other[p.piece_id].material_id for p in pcs if p.piece_id in other})
            alt = " / ".join(alts)
            out.append(BOMLine(setname, f"{mid}: " + " ".join(f"{p.piece_id}x{p.quantity}" for p in pcs), mid,
                               round(qty, 3), unit, round(100.0 * (prod_m * rw / net - 1.0), 1), uc,
                               round(qty * uc, 2) if uc else None,
                               alt_material_id=("same" if alt == mid else alt), kit=_kits_of(rs, mid),
                               source=f"record {mid}; net {net:.3f} m2 from the pattern areas; {basis}",
                               notes=f"net {net:.3f} m2 ({net * 10.764:.2f} ft2); roll {rw * 1000:.0f} mm; prototype "
                                     f"1-bag marker {pq:.3f} {unit} ({proto_m / 0.9144:.2f} yd)"
                                     + ("" if m1 else " (ASSUMPTION MK-FALLBACK 60 %)"),
                               proto_qty=round(pq, 3)))
    return out


def webbing_bom(ctx: Ctx) -> list[BOMLine]:
    rows = [w for w in ctx.rs.webbing if not ("kit S" in w["kit"] or "kit L" in w["kit"])]
    by: dict = {}
    for w in rows:
        by.setdefault(w["material_id"], []).append(w)
    out = []
    for mid, ws in sorted(by.items()):
        net_m = sum(w["length_mm"] * w["qty"] for w in ws) / 1000.0
        qty = net_m * (1 + WEB_WASTE)
        key = mid.split(" ")[0]
        uc = cost_per(mid, "m") if key not in PRICE_ASSUMED else PRICE_ASSUMED[key][0]
        ids = " ".join(sorted({w["id"] for w in ws}))
        out.append(BOMLine("webbing", f"{key}: {ids}", key, round(qty, 3), "m", WEB_WASTE * 100, uc,
                           round(qty * uc, 2) if uc else None, alt_material_id="same",
                           kit=",".join(sorted({w['kit'] for w in ws})),
                           source=("record " + mid) if mat(mid) else PRICE_ASSUMED.get(key, (0, 0, "ASSUMPTION, no record"))[2],
                           notes=f"net {net_m:.2f} m ({net_m / 0.9144:.2f} yd), crown kit M; per-kit cuts in "
                                 "cutting_plan.csv"))
    return out


# hardware: (key, item, record, qty, unit, kit, frame_side). Quantities from RevSet.hardware where the pattern lists
# the part; ledger rows reach each line through HW_LEDGER_MAP.
def _hw_qty(ctx: Ctx, mid: str, default):
    q = sum(h["qty"] for h in ctx.rs.hardware if h["material_id"] == mid)
    return q or default


def hardware_table(ctx: Ctx) -> list[tuple]:
    hw = {h["item"]: h for h in ctx.rs.hardware}
    zl = {k: v["length_mm"] for k, v in hw.items() if v["material_id"].startswith("coil")}
    z10 = sum(v for k, v in zl.items() if "#10" in k) / 1000.0
    z5 = sum(v for k, v in zl.items() if "#5" in k) / 1000.0
    n5 = sum(1 for k in zl if "#5" in k)
    ll = _hw_qty(ctx, "ladder_lock_25mm_heavy", 9)
    tog = _hw_qty(ctx, "pom_toggle", 4)
    ncl = _hw_qty(ctx, "cord_lock_spring", 1)
    cl_use = " + ".join(h["item"].split(":")[-1].strip() if ":" in h["item"] else h["item"]
                        for h in ctx.rs.hardware if h["material_id"] == "cord_lock_spring") or "E-5 pole grip"
    return [
        ("zip10", "#10 coil zip chain, door D2 (2 sliders)", "coil_zipper_10", round(z10, 3), "m", "base", False),
        ("slider10", "#10 coil slider, metal pull (door)", "slider_10", 2, "unit", "base", False),
        ("zip5", f"#5 coil zip chain: lid, IMP-4, F-02 ({n5} zips)", "coil_zipper_5", round(z5, 3), "m",
         "base,as_hunted", False),
        ("slider5", f"#5 coil slider + pull ({n5}: lid, IMP-4, F-02)", "slider_5", n5, "unit", "base,as_hunted", False),
        ("pull_cord", "door pull cord 3 mm Dyneema, 2 x 0.15 m (ASSUMPTION length)", "dyneema_cord_3mm", 0.30, "m",
         "base", False),
        ("pull_sleeve", "rubber pull sleeve", "rubber_pull_sleeve", 2, "unit", "base", False),
        ("ghook", "rated 25 mm aluminium G-hook: IM1, IM2 (2) + W1-W3 (3) + bow riser (1)", "g_hook_25mm_aluminium",
         6, "unit", "base", False),
        ("ghook_x", "rated 25 mm aluminium G-hook: W haul extenders", "g_hook_25mm_aluminium", 3, "unit", "meat_trip",
         False),
        ("cara", "wiregate carabiner 22 kN: IM3 bag hooks (2) + IM3 meat free end (1)", "carabiner_wiregate_22kn", 3,
         "unit", "base", False),
        ("cara_x", "wiregate carabiner 22 kN: B-24 float links", "carabiner_wiregate_22kn", 2, "unit", "meat_trip",
         False),
        ("ll_heavy", f"heavy 25 mm ladder lock ({ll}): B-28 (4) + guys (2) + W1-W3 (3)", "ladder_lock_25mm_heavy", ll,
         "unit", "base,as_hunted", False),
        ("cam", "25 mm aluminium cam buckle: IM1-IM3 (3) + US1/US2 (2)", "cam_25mm_al", 5, "unit", "base", False),
        ("triglide_ss", "25 mm STAINLESS tri-glide: US1/US2 cradle backstop behind the cam (2; orchestrator "
         "2026-11-13, 11 g, 3.75 kN)", "triglide_25mm", 2, "unit", "base", False),
        ("triglide", "25 mm nylon tri-glide: guy tail keepers (2)", "triglide_25mm", 2, "unit", "base", False),
        ("toggle", f"POM toggle 30 x 8 x 5 ({tog}): B-28 rear (2) + guy loops (2)", "pom_toggle", tog, "unit",
         "base,as_hunted", False),
        ("srb", "25 mm side-release buckle (roll top)", "buckle_side_release_25mm", 2, "unit", "base", False),
        ("cordlock", f"spring cord lock ({ncl}): {cl_use}", "cord_lock_spring", ncl, "unit", "base", False),
        ("tpu_sleeve", "TPU sleeve on the IM3 carabiner (2)", "tpu_hook_sleeve", 2, "unit", "base", False),
        ("fairlead", "printed fairleads (8), 7075 pins (8: 6 x {:.0f} mm shank IM / US + 2 x {:.0f} mm shank HINGE for the "
         "20 mm throat, BL-044), UHMWPE sleeves (8), US anchors, lifter keepers".format(
             P.F.hinge_pin()["shank_im_mm"], P.F.hinge_pin()["shank_hinge_mm"]), "frame kit", 1, "set", "base", True),
    ]


# ledger hardware row prefix -> BOM line keys it is bought on (hardware_table keys, "thread", or a webbing material id)
HW_LEDGER_MAP = {
    "D2 door zip": ("zip10", "slider10"), "door: 2 cord pulls": ("pull_cord", "pull_sleeve"),
    "IM-hooks": ("ghook",), "IM-cams": ("cam",), "US-anchor": ("fairlead",), "US-cams": ("cam",),
    "US-tg": ("triglide_ss",), "B-24-hooks": ("cara_x",), "B-24-thr": ("thread",), "W-hw": ("ghook", "ll_heavy"),
    "BL-010 S2": ("cara",), "BL-010 S9": ("ghook", "ll_heavy"), "BL-010 S12": ("cara_x",),
    "attachment: printed fairleads": ("fairlead",), "attachment: 7075 pins": ("fairlead",),
    "BL-044: hinge pins": ("fairlead",),
    "attachment: UHMWPE sleeves": ("fairlead",), "attachment: bag hooks, 38 mm": ("cara",),
    "attachment: TPU hook sleeves": ("tpu_sleeve",), "attachment: elastic keepers": ("elastic_25mm",),
    "attachment: lifter tri-glide": ("fairlead",), "attachment system: bag hooks 1500": ("cara",),
    "attachment system: thread": ("thread",), "BL-010 A1": ("cara",), "BL-010 A3": ("ll_heavy",),
    # BL-034 part A rows (record masses and the thread from the op lengths)
    "BL-034 records: US1/US2 backstop tri-glides": ("triglide_ss",),
    "BL-034 records: lifter tri-glide keepers": ("fairlead",),
    "BL-034 records: guy tri-glides": ("triglide",),
    "BL-004 REC: guy toggles": ("toggle",),          # BL-043 m-14: relabelled row (was 'guy bar loops x2 ... + POM toggle')
    "BL-034 records: guy tail elastic keepers": ("elastic_25mm",),
    "BL-034 records: F-02 fly pocket #5 slider": ("slider5",),
    "BL-034 thread:": ("thread",),
}
# fallback for rows added later (e.g. BL-035): a keyword in the row text -> BOM line key. Rows mapped this way are listed
# in checks()["hardware_rows_by_keyword"] so a person confirms them.
HW_KEYWORDS = (("stainless", "triglide_ss"), ("tri-glide", "triglide"), ("#10", "slider10"), ("#5", "slider5"),
               ("slider", "slider5"), ("elastic", "elastic_25mm"), ("thread", "thread"), ("toggle", "toggle"),
               ("cam", "cam"), ("carabiner", "cara"), ("G-hook", "ghook"), ("ladder lock", "ll_heavy"),
               ("cord lock", "cordlock"), ("cord", "cord"), ("fairlead", "fairlead"), ("sleeve", "tpu_sleeve"))


def _hw_rows(ctx: Ctx) -> list[dict]:
    return [r for r in ctx.rec["rows"] if r["status"] == "hardware"]


def ledger_map(ctx: Ctx) -> dict:
    """Every ledger hardware row -> (BOM keys, how, label): how = 'prefix', 'keyword' or None (unmapped)."""
    out = {}
    for r in _hw_rows(ctx):
        t = r["row"]
        hit = next(((k, v) for k, v in sorted(HW_LEDGER_MAP.items(), key=lambda kv: -len(kv[0])) if t.startswith(k)),
                   None)
        if hit:
            out[t] = (hit[1], "prefix", hit[0].rstrip(":"))
            continue
        kw = next((key for word, key in HW_KEYWORDS if word.lower() in t.lower()), None)
        out[t] = ((kw,), "keyword", t[:60]) if kw else ((), None, t[:60])
    return out


def unmapped_hardware_rows(ctx: Ctx) -> list[str]:
    """Ledger rows booked as hardware that this BOM does not cover (a ledger change)."""
    return [t for t, (_, how, _l) in ledger_map(ctx).items() if how is None]


def keyword_mapped_rows(ctx: Ctx) -> list[str]:
    return [f"{t} -> {keys[0]}" for t, (keys, how, _l) in ledger_map(ctx).items() if how == "keyword"]


def _rows_for(ctx: Ctx, key: str) -> list[str]:
    return sorted({lab for _t, (keys, _h, lab) in ledger_map(ctx).items() if key in keys})


def hardware_bom(ctx: Ctx) -> list[BOMLine]:
    out = [BOMLine("hardware", f"UNMAPPED ledger hardware row: {r}", "-", 0, "-", 0.0, None, None,
                   source="ledger", notes="add to HW_LEDGER_MAP / hardware_table()") for r in unmapped_hardware_rows(ctx)]
    table_recs = set()
    for key, item, rec, qty, unit, kit, frame in hardware_table(ctx):
        table_recs.add(rec)
        led = "; ".join(_rows_for(ctx, key)) or "-"
        if frame:
            out.append(BOMLine("hardware_frame_side", item, rec, qty, unit, 0.0, None, None, kit=kit,
                               source=f"ledger rows: {led}", notes="frame kit (H1 package), not sewn; listed so the bag "
                                                                   "kit is complete"))
            continue
        if key == "triglide_ss":
            uc, src = TG_SS_USD, "record triglide_25mm stainless_alt (EUR 3.10 incl. VAT, converted as the record)"
        elif rec in PRICE_ASSUMED:
            uc, src = PRICE_ASSUMED[rec][0], PRICE_ASSUMED[rec][2]
        else:
            m = mat(rec)
            uc = cost_per(rec, unit) if unit == "m" else (float(m.cost_usd["value"]) if m and m.cost_usd else None)
            src = f"record {rec}"
        out.append(BOMLine("hardware", item, rec, qty, unit, 0.0, uc, round(qty * uc, 2) if uc is not None else None,
                           alt_material_id="same", kit=kit, source=f"{src}; ledger rows: {led}"))
    # parts the pattern's hardware list names that the table above does not (e.g. a part a later ticket adds)
    for h in ctx.rs.hardware:
        mid = h["material_id"]
        if mid in table_recs or mid in ("-",) or mid.startswith("coil"):
            continue
        m = mat(mid)
        per = (m.cost_usd or {}).get("per") if m else None
        unit = "m" if (h.get("length_mm") and per in ("m", "yd")) else "unit"
        qty = round(h["length_mm"] * h["qty"] / 1000.0, 3) if unit == "m" else h["qty"]
        uc = cost_per(mid, "m") if unit == "m" else (float(m.cost_usd["value"]) if m and m.cost_usd else None)
        out.append(BOMLine("hardware", f"{h['item']} (pattern hardware list)", mid, qty, unit, 0.0, uc,
                           round(qty * uc, 2) if uc is not None else None, alt_material_id="same",
                           source=f"record {mid}" if m else "no record: ASSUMPTION, price missing",
                           notes="added from RevSet.hardware (not in hardware_table)"))
    return out


def thread_bom(ops: list[SewingOp], ledger_thread_g: float | None = None) -> list[BOMLine]:
    """Purchase quantity = stitch use x (1 + cone waste). The mass in the bag excludes the cone waste (it never reaches
    the bag), as ``build_effort_rev3`` books it on the ledger."""
    use = {k: v for k, v in MF.thread_metres(ops, THREAD_FACTOR).items() if k.startswith("bonded")}
    out = []
    for tid, m in sorted(use.items()):
        q = m * (1 + THREAD_WASTE)
        uc = cost_per(tid, "m")
        g_bag = m * float(mat(tid).require("mass_g_m"))
        out.append(BOMLine("thread", f"{tid} (needle + bobbin)", tid, round(q, 1), "m", THREAD_WASTE * 100, uc,
                           round(q * uc, 2) if uc else None, alt_material_id="same", kit="all",
                           source=f"record {tid}; sum of op stitch lengths x {THREAD_FACTOR} (ASSUMPTION THREAD-FACTOR) "
                                  f"+ {THREAD_WASTE:.0%} cone waste on the purchase quantity only",
                           notes=f"{m:.1f} m sewn = {g_bag:.1f} g in the bag (no cone waste)"
                                 + (f"; ledger books {ledger_thread_g:.1f} g of bag thread in all" if ledger_thread_g
                                    is not None else "")))
    return out


def thread_bag_g(ops: list[SewingOp]) -> float:
    """Thread mass that ends up in the bag (all ops, no cone waste)."""
    return float(sum(m * float(mat(t).require("mass_g_m")) for t, m in MF.thread_metres(ops, THREAD_FACTOR).items()
                     if t.startswith("bonded")))


def ledger_thread_g() -> float:
    """Bag thread booked on the ledger: the original thread rows plus the BL-034 rows from the op lengths."""
    return float(sum(r["g"] for r in P.ledger_rows() if r["name"].startswith(
        ("attachment system: thread", "B-24-thr", "BL-034 thread"))))


def consumables_bom(g: dict) -> list[BOMLine]:
    tape_m = (g["zip_door_mm"] * 2 + g["lid_zip_mm"] * 2) / 1000.0
    out = [BOMLine("consumable", "6 mm double-sided basting tape (zips)", "basting_tape_6mm", round(tape_m, 2), "m", 0,
                   PRICE_ASSUMED["basting_tape_6mm"][0], round(tape_m * PRICE_ASSUMED["basting_tape_6mm"][0], 2),
                   source=PRICE_ASSUMED["basting_tape_6mm"][2]),
           BOMLine("consumable", "labels: size / care / ID, hang tag, load-limit warning card", "label_set", 1, "set",
                   0, PRICE_ASSUMED["label_set"][0], PRICE_ASSUMED["label_set"][0], source=PRICE_ASSUMED["label_set"][2]),
           BOMLine("consumable", "silicone seam sealer for the silpoly fly and liner seams, ~10 ml (ASSUMPTION)",
                   "seam_sealer", 1, "bag", 0, PRICE_ASSUMED["seam_sealer"][0], PRICE_ASSUMED["seam_sealer"][0],
                   source=PRICE_ASSUMED["seam_sealer"][2]),
           BOMLine("packaging", "poly bags + carton share", "polybag_carton", 1, "bag", 0,
                   PRICE_ASSUMED["polybag_carton"][0], PRICE_ASSUMED["polybag_carton"][0],
                   source=PRICE_ASSUMED["polybag_carton"][2])]
    return out


CAMO_DIR = REL / "camo"         # BL-040 M-10: the camo-designer's release folder (separate ticket)
PACK_COLORWAY = "krummholz"     # BL-040 (orchestrator 2026-11-13): named primary pairing in designs/apparel/colorways.yaml
SUBLIMATION_CAVEAT = ("630D printable base is TPU-coated and sublimation transfer runs at about 200 C: print BEFORE the "
                      "coating is applied (mill print), or order a strike-off and check the coat survives, before buying "
                      "yardage")


def colour_spec() -> dict:
    """Body / trim / accent of the pack colourway, read from designs/apparel/colorways.yaml (no fallback: raises if the
    pairing is missing, so the BOM never names a colour the colour standard does not hold)."""
    import yaml
    cw = yaml.safe_load((ROOT / "designs" / "apparel" / "colorways.yaml").read_text())
    solids = {x["key"]: x for x in cw["solids"]}
    pr = next(a for a in cw["accent_pairings"] if a["id"] == PACK_COLORWAY)
    f = lambda k: f"{solids[k]['name']} {solids[k]['hex']} ({solids[k]['code']})"  # noqa: E731
    return {"pairing": PACK_COLORWAY, "name": pr["display_name"], "body": f(pr["body"]), "trim": f(pr["trim"]),
            "harness": f(pr.get("harness", pr["trim"])), "accent": pr["accent_pattern"],
            "ref": f"designs/apparel/colorways.yaml accent_pairings id '{PACK_COLORWAY}'"}


def colour_note(section: str, mid: str) -> str:
    c = colour_spec()
    if mid in ("polyester_ht_630d_printable", "polyester_300d_printable") or section == "fabric_print":
        return f"colour: {c['accent']} camo accent print ({c['ref']})"
    if mid in P.WEBBING or mid.startswith(("coil_zipper", "poly_webbing", "elastic", "shock_cord")) or section == "webbing":
        return f"colour: trim {c['trim']} ({c['ref']})"
    if section in ("fabric", "fabric_alternate") and mid not in P.FREE_ROTATION and mid != "power_mesh_nylon_spandex":
        return f"colour: body {c['body']} ({c['ref']})"
    return ""


def camo_bom(ctx: Ctx) -> list[BOMLine]:
    """BL-040 M-10: the camo print line, read from the camo-designer's release (``camo/bom_print_line_proposed.csv``).
    Until that folder exists the line is a marked TODO with no price (it lands in costing's missing list)."""
    f = CAMO_DIR / "bom_print_line_proposed.csv"
    if not f.exists():
        return [BOMLine("fabric_print", "TODO camo print: camo/ release folder not issued yet (camo-designer ticket); "
                        "print file, colourway, repeat, vendor, MOQ and lead time come from there. Fallback: solid "
                        "630D (no camo) for the first build", "-", 0, "-", 0.0, None, None, kit="base",
                        source="BL-040 M-10 TODO", notes="re-run this script when camo/ lands")]
    out = []
    with f.open() as fh:
        for r in csv.DictReader(fh):
            q1, q10 = float(r["qty_1bag"]), float(r["qty_10bag"])
            uc = float(r["unit_cost_usd"])
            out.append(BOMLine("fabric_print", f"{r['item']} -- see camo/README.md (print file camo/print/, colours "
                               "camo/colour_spec.csv, placement camo/placement.csv, vendors camo/vendors.csv)",
                               r["material_id"], round(q10 / 10.0, 3), r["unit"], 0.0, uc, round(q10 / 10.0 * uc, 2),
                               alt_material_id="polyester_ht_630d_printable (unprinted, fabric line)", kit="base",
                               source=f"camo/bom_print_line_proposed.csv: {r['source']}",
                               notes=f"{r['notes']}; PRODUCTION ONLY (DECISION CAMO-FIRST, BL-043 m-10): the first "
                                     "build is solid 630D on the camo pieces, so the prototype buys none of this line "
                                     f"(the camo test yard is a test-kit specimen); a 1-bag print run would be {q1:g} "
                                     f"{r['unit']} = ${float(r['cost_1bag_usd']):.2f}; CAVEAT: {SUBLIMATION_CAVEAT}",
                               proto_qty=0.0))
    return out


# ============================================================================ cutting plan
CUT_METHOD = {   # material -> (prototype, production, lay rule)
    "cordura_330d_nylon66": ("rotary + hot-knife the window / slot cut-outs", "straight knife, 10-bag marker, 24 plies max; or laser single ply (sealed edges)", "face up, one way not needed"),
    "cordura_500d_nylon66": ("rotary", "straight knife, 24 plies max", "face up"),
    "robic_100d_ripstop": ("rotary", "straight knife, 24 plies max (paper between every 6 plies: slippery)", "face up"),
    "nylon_ripstop_70d": ("rotary", "straight knife, 12 plies max (slippery)", "face up"),
    "challenge_ultra_200": ("rotary; windows and B-27 slits with a hot knife / scalpel on a cutting mat", "straight knife, 12 plies max (laminate creeps), or laser single ply", "laminate face up, all pieces one way"),
    "ultragrid_210d_uhmwpe_ripstop": ("rotary (UHMWPE grid: new blade)", "straight knife 12 plies; UHMWPE dulls blades: sharpen every lay", "face up"),
    "polyester_ht_630d_printable": ("rotary", "single ply (printed camo, one way, pattern placement)", "print face up, ONE WAY"),
    "power_mesh_nylon_spandex": ("rotary, no stretch while cutting", "straight knife 12 plies, relaxed 24 h before cutting", "stretch ACROSS, one way"),
    "silicone_coated_poly_ripstop_40d": ("rotary, weights not pins", "straight knife 12 plies with paper underlay", "face up"),
    "hypalon_coated_nylon": ("laser from the DXF (makerspace) or a knife + template", "laser single sheet; dies above 500 bags", "coated face up, free rotation"),
    "tpu_coated_nylon_840d": ("laser from the DXF", "laser single sheet", "coated face up, free rotation"),
    "hdpe_sheet": ("shear / router, round every corner R >= 3", "CNC router from the DXF", "free rotation"),
}


def cutting_plan(ctx: Ctx) -> list[dict]:
    mk = ctx.markers
    out = []
    for setname, rs, key in (("primary", ctx.rs, "primary_1bag"), ("alternate", ctx.rsA, "alternate_1bag")):
        by: dict = {}
        for p in _fabric_pieces(rs):
            by.setdefault(p.material_id, []).append(p)
        for mid, pcs in sorted(by.items()):
            m1 = mk.get(key, {}).get(mid, {})
            m10 = mk.get("primary_10bag", {}).get(mid, {}) if setname == "primary" else {}
            proto, prod, lay = CUT_METHOD.get(mid, ("rotary", "straight knife", "face up"))
            out.append({"set": setname, "material_id": mid,
                        "pieces": " ".join(f"{p.piece_id}x{p.quantity}" for p in pcs),
                        "marker_1bag_m": m1.get("yield_m_per_unit"), "eff_1bag": m1.get("efficiency"),
                        "marker_10bag_m_per_bag": m10.get("yield_m_per_unit"), "eff_10bag": m10.get("efficiency"),
                        "marker_files": f"patterns/markers/{setname}/{mid}_1bag.pdf/.dxf"
                                        + (f"; patterns/markers/primary/{mid}_10bag.pdf/.dxf" if m10 else ""),
                        "lay": lay, "prototype_cut": proto, "production_cut": prod,
                        "mirror_rule": "L+R pieces: cut 2 plies face to face (or flip the pattern)" if any(p.mirror for p in pcs) else "-"})
    for w in ctx.rs.webbing:
        out.append({"set": "webbing", "material_id": w["material_id"], "pieces": f"{w['id']}x{w['qty']}",
                    "marker_1bag_m": round(w["length_mm"] / 1000.0, 3), "eff_1bag": None, "marker_10bag_m_per_bag": None,
                    "eff_10bag": None, "marker_files": "-", "lay": f"{w['use']} ({w['kit']})",
                    "prototype_cut": f"hot knife at {w['length_mm']:.0f} mm ({w['length_mm'] / IN:.2f} in), seal both ends",
                    "production_cut": "automatic hot-knife webbing cutter, length stop", "mirror_rule": "-"})
    return out


# ============================================================================ bartack / load points
def _hw_values() -> dict:
    """Governing hardware values from the records (BL-040 M-7: the load table shows them beside the stitch SF)."""
    def v(mid, key, default):
        m = mat(mid)
        try:
            return float(m.require(key)) if m else default
        except Exception:
            return default
    return {"ll": v("ladder_lock_25mm_heavy", "slip_load_n", 490.0), "cam": v("cam_25mm_al", "slip_load_n", 1100.0),
            "srb": v("buckle_side_release_25mm", "breaking_strength_n", 450.0),
            "ghook_noset": v("g_hook_25mm_aluminium", "no_set_load_n", 900.0)}


HE_405_STEPS = ("NECK", "B18-ROWS", "PLACE-HE", "BOX", "BASTE")   # BL-041 X-1: the order op 4.05 sews in


def step_spec(kind: str, stitch: str = "301", note: str = "") -> str:
    """BL-043 m-2: one step's machine / needle / thread / stitch, in words (an op may mix box-X, rows and tacks)."""
    mach = {"box": "BT / PS (prototype: WF2 + J1 template)", "body": "WF2", "light": "WF1", "bt": "ZZ or BT",
            "baste": "WF1"}[kind]
    k = {"bt": "body", "baste": "body"}.get(kind, kind)
    spi = {"box": f"box-X path {SPI['box']} SPI", "body": f"{SPI['body']} SPI", "light": f"{SPI['light']} SPI",
           "bt": "16 x 2 mm zigzag", "baste": "6 mm stitch"}[kind]
    fb = "; prototype without zigzag: BT-301 fallback (4 passes, UNRATED)" if stitch == "304" else ""
    return f"[{mach}; {NEEDLE[k]}; {THREAD[k]}; ISO {stitch}, {spi}{fb}{'; ' + note if note else ''}]"


def he_405_text(ctx) -> str:
    """Op 4.05 (BL-041 X-1 order): the B-18 rows are sewn through B-18 + B-01 ONLY, before the HE is laid on, so no row
    can cross the open eye; then the HE is placed and boxed below the fairlead cheeks (DECISION HE-PIN). The PT-3
    specimen text is built from the same steps (physical_test_kit)."""
    rs = ctx.rs
    hg = rs.geo["he"]
    hbx = (boxes_of(rs.pieces["HE"]) or [(34.0, 10.0, "")])[0][:2]
    return (f"(1) NECK, on the FLAT HE strip ({hg['cut']:.0f} mm): fold each long edge {P.HE_NECK_EDGE:.0f} mm in between "
            f"the two 'neck lines' (the strip there is {hg['neck_w']:.0f} mm wide, the fairlead throat), then one BT-M bartack "
            "across each leg at the 'neck tack' lines (through that leg only) " + step_spec("bt", "304") + ". "
            "(2) B-18 ROWS FIRST: lay B-18 INSIDE B-01 on the drawn placement, coated face to B-01, its lower edge ON the "
            f"B-01 cut edge (it runs {hg['b18_below_seam']:.0f} mm below the floor seam line); sew its perimeter rows 3 and 9 mm "
            "in, on the TOP and BOTH SIDES only (the bottom goes in the floor seam), through B-18 + B-01 ONLY "
            + step_spec("body", "301", "rated rows (load_points B-18)") + ". Nothing else "
            "is on the panel yet: these rows must never catch the HE. "
            "(3) PLACE THE HE: fold the strip in half on the 'EYE FOLD' line (raw ends together, neck folds inside) and lay it "
            "OUTSIDE B-01 over B-18, centred on the 'hinge eye CL' notch, eye fold pointing UP, both raw ends ON the B-01 cut "
            "edge. Layer order from outside: HE leg / HE leg / B-01 / B-18. Clip. "
            f"(4) BOX: box-X {hbx[0]:.0f} x {hbx[1]:.0f} at the drawn 'HE hinge eye' box (drill corners: its lower edge "
            f"{hg['box_z_above_seam'][0]:.0f} mm, its top {hg['box_z_above_seam'][1]:.0f} mm above the floor seam line), through "
            "all four layers " + step_spec("box") + ". Its top edge must stay BELOW the fairlead cheeks: nothing but the 18 mm neck may sit above "
            f"+{hg['cheek_z'][0]:.0f} mm. "
            "(5) BASTE the bottom of the stack (2 HE raw ends + B-18 + B-01) at 6 mm, inside the allowance, so op 4.15 "
            f"catches all of it {step_spec('baste')}. The free loop above the box ({hg['eye_mm']:.0f} mm, fold {hg['fold_z_flat']:.0f} mm above the "
            f"seam line) is the eye: it points UP and takes the z 60 pin with the {hg['neck_w']:.0f} mm neck in the "
            f"{hg['throat']:.0f} mm throat and the 3-ply neck through the {hg['gap_under_pin']:.1f} mm gap under the pin "
            f"(DECISION HE-ENV, BL-042 hinge fairlead; loaded pin centre {hg['pin_z_design']:.1f} mm above the seam line, "
            f"HE-FIT band {hg['pin_band'][0]:.0f}-{hg['pin_band'][1]:.0f}). No stitching crosses the eye after step 3.")


def load_points(ctx: Ctx) -> list[dict]:
    """Every sewn load point: pattern box size, stitch count, thread / needle, the factored load from the record that
    sets it, the capacity (attach_system rules) and the proof test that releases it. Box sizes are the box-X marks drawn
    on the pieces (BL-034 part A); a webbing piece with drawn boxes that no row below names gets an UNRATED row."""
    rs = ctx.rs
    HW = _hw_values()
    bx = AS.box_x
    st = 25.4 / SPI["box"]
    body_alt = ctx.rsA.pieces["B-02h"].material_id
    body = rs.pieces["B-02h"].material_id

    def box(pid, label=None):
        b = boxes_of(rs.pieces[pid]) if pid in rs.pieces else []
        return [x for x in b if label is None or label in x[2]]

    rows = []

    def add(pt, pid, where, w, h, load_n, load_src, proof, extra_caps=None, kind="box", note="", vol="", hw=None):
        if kind == "box":
            c = bx(w, h)
            n = math.ceil(c["path_mm"] / st) + 4
            caps = {"box-X": c["cap_n"], **(extra_caps or {})}
            machine = "BT LK-1900BN" if (w <= 40 and h <= 30) else "PS AMS-210EN (or WF2 + J1)"
            pattern = f"box-X {w:.0f} x {h:.0f} mm ({w / IN:.2f} x {h / IN:.2f} in), path {c['path_mm']:.0f} mm"
            thread, needle, spi = THREAD["box"], NEEDLE["box"], SPI["box"]
        elif kind == "perim":
            caps = extra_caps or {}
            n = None
            machine = "WF2"
            pattern = "double-row perimeter 3 / 9 mm, 301"
            thread, needle, spi = THREAD["body"], NEEDLE["body"], SPI["body"]
        else:
            b = BARTACK_STD[kind]
            n = b["stitches"]
            caps = extra_caps or {}
            machine = "BT LK-1900BN"
            pattern = f"bartack {b['len_mm']:.0f} x {b['w_mm']:.0f} mm, 304"
            thread, needle, spi = THREAD["body"], NEEDLE["body"], None
        gov = min(caps, key=caps.get) if caps else "-"
        cap = caps[gov] if caps else None
        rows.append({"point": pt, "part": pid, "where": where, "pattern": pattern, "stitches": n, "machine": machine,
                     "stitch": {"box": "301 path", "perim": "301"}.get(kind, "304"), "spi": spi, "thread": thread, "needle": needle,
                     "load_n": load_n, "load_lbf": round(load_n / 4.448, 0) if load_n else None, "load_source": load_src,
                     "capacity_n": round(cap, 0) if cap else None, "governs": gov,
                     "sf": round(cap / load_n, 2) if (cap and load_n) else None, "proof": proof, "note": note,
                     "volatile": vol,
                     # BL-040 M-7: the governing HARDWARE beside the sewn capacity (record value; most are ASSUMPTIONs)
                     "hardware": hw[0] if hw else "-", "hardware_n": hw[1] if hw else None,
                     "hardware_basis": hw[2] if hw else "",
                     "hardware_margin": round(hw[1] / load_n, 2) if (hw and hw[1] and load_n) else None})

    guy = GUY_N       # corrie_f_body.md 13.5: port guy 96.1 N at 1 g x 3.0 (23 in full)
    LL = (f"heavy ladder lock slip ({HW['ll']:.0f} N, ASSUMPTION 0.5 x tensile, ladder_lock_25mm_heavy)", HW["ll"],
          "record slip_load_n; LL-H settles it dry / wet / -20 C")
    CAM = (f"25 mm cam slip ({HW['cam']:.0f} N, ASSUMPTION, cam_25mm_al)", HW["cam"], "record; MT-3 settles it dry / wet / -20 C")
    CARA = ("wiregate carabiner, PT-1 basis 0.5 x 8 kN minor axis", 4000.0, "carabiner_wiregate_22kn record; PT-1")
    BUCKLE = (f"25 mm side-release buckle break ({HW['srb']:.0f} N, buckle_side_release_25mm, ESTIMATE)", HW["srb"],
              "record; no load case (hand cinch)")
    b22 = AS.patch_seam(50.0, body, "hypalon_coated_nylon")["cap_n"]
    b22a = AS.patch_seam(50.0, body_alt, "hypalon_coated_nylon")["cap_n"]
    for w, h, lab in box("TG"):
        add("port guy, toggle end", "TG", "TG toggle loop (B-25 tab side)", w, h, guy,
            "corrie_f_body.md 13.5: 96.1 N x 3.0", f"TL-1 {TL1_N} N (toggle in the B-25 tab, BL-041)",
            hw=("POM toggle pull-through (670 N, ASSUMPTION attach_system)", 670.0, "TL-1 settles it"))   # BL-041 n-8a
    band_llt = sorted({(w, h) for w, h, _ in box("B-02h", "LLT")})
    for w, h, lab in box("LLT"):
        mism = [f"{a:.0f}x{b:.0f}" for a, b in band_llt if (a, b) != (w, h)]
        add("port guy, bag end", "LLT + B-22 + B-02h", f"inside the hinge band at x +/-{ctx.rs.geo['b22']['placed_x']}",
            w, h, guy, "corrie_f_body.md 13.5: 96.1 N x 3.0", f"LL-H {LLH_N:.0f} N; PT-5 (lock + keeper)",
            {"B-22 perimeter 50 mm (primary body)": b22}, hw=LL,
            note=f"alternate body fabric: B-22 seam {b22a:.0f} N"
                 + (f"; PATTERN MISMATCH: B-02h draws the LLT box {', '.join(mism)}, the LLT piece {w:.0f}x{h:.0f}: "
                    "sew the LLT size (the tab is 25 mm wide)" if mism else ""),
            vol="pattern: B-22 x")
    add("port guy, B-27 slit ends", "B-01", f"both ends of each slit, z {P.F.PORT_Z[0]:.0f} / {P.F.PORT_Z[1]:.0f}",
        0, 0, None, "no rated load (lap only); port mock-up: 100 N guy pull through the lap", "port mock-up (13.9)",
        kind="BT-S")
    # crown strap tabs: every B-28 tab piece the pattern draws (B-28t today; BL-035 may split it) + the band box
    for pid in sorted(i for i in rs.pieces if i.startswith("B-28") and i != "B-28"):
        use = next((w["use"] for w in rs.webbing if w["id"] == pid), rs.pieces[pid].name)
        for w, h, lab in box(pid):
            add(f"crown strap tab ({pid} x{rs.pieces[pid].quantity})", pid, use, w, h, guy,
                f"corrie_f_body.md 15.2: {guy:.0f} N envelope (port guy) if a crown strap ever holds the top",
                f"LL-H {LLH_N:.0f} N (1.5 x {guy:.0f} N; BL-031 dropped the 20 mm gate)", hw=LL)
    for w, h, lab in box("B-02h", "B-28"):
        add("crown strap front tab on the band", "B-02h", "B-28 front lock tab, OUTSIDE the hinge band (DECISION "
            "B28-FACE, BL-034), box through tab + band", w, h, guy, "corrie_f_body.md 15.2 (as above)",
            f"LL-H {LLH_N:.0f} N", hw=LL)
    for w, h, lab in box("B-25"):
        add("B-25 bridle toggle tab", "B-25", f"{lab.split(' box-X')[0]}: tip-end box, clear loop for the POM toggle "
            "(DECISION B25-BOX, BL-034); 38 mm bridle, sleeve x 26.5-64.5 (BL-041)", w, h, float(B25_N),
            f"crown_tube_guy_loop.md 2: guy + B-28 crown strap on one tab, envelope {B25_N} N",
            f"TL-1 {TL1_N} N on real bar stock (crown_tube_guy_loop.md 6)",
            {"crown bar wall under the 38 mm sleeve (basis A, knocked down)": round(_CT["tl1"]["kd_capacity_A_n"]),
             "POM toggle pull-through (ASSUMPTION 670 N)": 670.0})
    if not box("B-25"):
        add("B-25 bridle toggle tab", "B-25", "NOT DRAWN on the pattern", 21, 15, guy, "corrie_f_body.md 13.5",
            f"LL-H toggle-loop pull {LLH_N:.0f} N", note="pattern draws no B-25 box: HOLD the B-25 tabs")
    laps = [ln.label for ln in lines(rs.pieces["B-25"], "fold") if "bartack" in (ln.label or "")] if "B-25" in rs.pieces else []
    if laps:
        add("B-25 bar sleeve laps", "B-25", "; ".join(laps) + " (sewn at frame assembly, round the crown top bar)",
            0, 0, None, "no rated load: the sleeve wraps the bar, the lap only keeps it closed",
            "LL-H toggle-loop pull (whole bridle)", kind="BT-M")
    # BL-041: GBL deleted (carried nothing in rev 3; crown_tube_guy_loop.md 8.2)
    for w, h, lab in box("T3"):
        add("IM3 bag-hook tongue", "T3", lab.replace(" box-X", ""), w, h, 1702.0,
            "loadpath_verification A1: IM3 1702 N factored (guys-off misuse)", "PT-1 2553 N carabiner; PT-2 2553 N",
            {"webbing on carabiner bed": AS.web_pin("poly_webbing_38mm"), "carabiner (PT-1 basis: 0.5 x 8 kN minor axis)": 4000.0},
            hw=CARA)
    add("B-17 IM3 tab perimeter (double row)", "B-17", "OUTSIDE B-01 at x +/-115, z 385-455", 0, 0, 1702.0,
        "loadpath_verification A1", "PT-2 2553 N on the 70 mm tab",
        {"perimeter 80 mm loaded, 2 rows": AS.patch_seam(80.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"]},
        kind="perim", note="perimeter 3 / 9 mm, 8 SPI tex 90; capacity = patch_seam on the 80 mm loaded top edge (the "
                           "same for the 70 or 110 mm tall tab: the side rows are not credited); SF PENDING PT-2 on the "
                           "70 mm tab (BL-040 m-3)")
    for w, h, lab in box("IME"):
        add("IM fairlead eyes (6)", "IME", "frame side, captive in the printed fairleads", w, h, 1702.0,
            "IM3 eye carries the bag hook (A1 1702 N); IM1/IM2 605 N (S1)", "MT-1 analogue at 38 mm; IM3-EP 2553 N")
    he_b18 = sorted({(a, b) for a, b, _ in boxes_of(rs.pieces["B-18"])})
    for w, h, lab in box("HE"):
        mism = [f"{a:.0f}x{b:.0f}" for a, b in he_b18 if sorted((a, b)) != sorted((w, h))]
        add("hinge eye", "HE + B-18 + B-01", f"x +/-115, box {P.HE_BOX_GAP:.0f}-{P.HE_BOX_GAP + h:.0f} mm above the "
            "floor seam line; B-18 and both HE raw ends in the B-01 | B-05 seam (DECISION HE-ONE)", w, h, HINGE_N,
            "load_standard.md (rev C) bag-on hinge case 1019 N factored; bag_attachment.md section 5 (loadpath A5 "
            "795 N is the sim-only value)", "PT-3 1530 N (= 1.5 x 1019) on the printed fairlead; SEW-F HE 625 N x 1e5",
            {"B-18 seam (80 mm, B-05 strip)": AS.patch_seam(80.0, "cordura_500d_nylon66", "hypalon_coated_nylon")["cap_n"]},
            note=(("PATTERN MISMATCH: B-18 box " + ", ".join(mism) + "; ") if mism else "") + (
                f"box-X {w:.0f} x {h:.0f} capacity {AS.box_x(w, h)['cap_n']:.0f} N (attach_system.box_x thread path); "
                f"the box top row PEELS (BL-044 he_peel): leg B leaves it {P.he_peel()['design']['peel_deg']:.0f} deg off "
                f"the box line in line, {P.he_peel()['worst']['peel_deg']:.0f} deg with B-01 held at the cheek tips = "
                f"{P.he_peel()['peel_frac_design']:.2f}-{P.he_peel()['peel_frac_worst']:.2f} x the hinge load across the "
                "row; no peel capacity is credited: rated by PT-3 on the printed fairlead (worst peel) and SEW-F HE"),
            vol="pattern: HE / B-18")
    for pid in ("IM1", "IM2", "IM3"):
        for w, h, lab in box(pid) or [(21.0, 25.0, "ASSUMPTION IM-BOX (not drawn)")]:
            add(f"{pid} end loop", pid, "left end loop, girth-hitched on the eye (box drawn at the tip end)", w, h,
                605.0, "loadpath_verification S1: 605 N", "MT-1 908 N; SEW-F (box-X fatigue)",
                note=lab if "ASSUMPTION" in lab else "MT-1 specimens are sewn exactly this way", hw=CAM)
    for w, h, lab in box("IMC"):                       # BL-041 m-19 / n-15 DECISION IM-CAM-TAB
        add("IM cam anchor tab", "IMC", f"{lab.replace(' box-X', '')}: dog-bone between the cam bar and the hook / "
            "carabiner (SK-11)", w, h, 605.0, "loadpath_verification S1: 605 N (same strap)",
            "MT-1 908 N (2 IMC specimens added to the MT-1 lot)", hw=CAM)
    for w, h, lab in box("USA"):                       # BL-044: the US cam's sewn anchor on the right pin
        add("US cam anchor", "USA", f"{lab.replace(' box-X', '')}: dog-bone between the right pin and the cam bar", w, h,
            720.0, "loadpath_verification S5-S7: 720 N cradle (the same strap as the left eye)",
            "MT-1 1080 N (2 USA specimens added to the MT-1 lot)", hw=CAM)
    for w, h, lab in box("US") or [(21.0, 25.0, "ASSUMPTION US-BOX (not drawn)")]:
        add("US1/US2 sewn eye", "US", "eye on the left pin (US-EYE fold, pattern)", w, h, 720.0,
            "loadpath_verification S5-S7: 720 N", "MT-1 1080 N; SEW-F (box-X fatigue); US-BS", hw=CAM,
            note=(lab if "ASSUMPTION" in lab else "") + "; cam side: stainless tri-glide backstop behind the cam "
                 "(orchestrator 2026-11-13; gate US-BS)")
    for pid in ("W1", "W2", "W3"):
        for w, h, lab in box(pid) or [(21.0, 25.0, "ASSUMPTION W-BOX (pattern draws the fold only)")]:
            add(f"{pid} G-hook end", pid, "G-hook fold 2 x 30 mm", w, h, 225.0, "loadpath_verification S9: 225 N",
                f"LL-H {LLH_N:.0f} N; W-PULL 338 N", note=lab if "ASSUMPTION" in lab else "", hw=LL)
    for w, h, lab in box("WX"):
        add("W haul extender", "WX", lab.split(" box-X")[0], w, h, 225.0,
            "ASSUMPTION WX-LOAD: same float-clamp load as S9 (225 N)", "LL-H; one extender pulled to 338 N",
            hw=(f"25 mm G-hook no-set ({HW['ghook_noset']:.0f} N, g_hook_25mm_aluminium)", HW["ghook_noset"], "record"))
    b24caps = {"carabiner": 4000.0, "webbing on bed": AS.web_pin("poly_webbing_38mm")}
    n_loops = sum(1 for x in box("B-24") if "hook" not in x[2])
    for w, h, lab in box("B-24"):
        hook = "hook" in lab
        add("B-24 float link: " + ("hook end" if hook else "loop bases"), "B-24",
            ("hook-end fold" if hook else f"{n_loops} loop bases") + " (boxes as drawn by attach_system.link_piece)",
            w, h, 941.0,
            "loadpath_verification S12 / RD-02: 941 N misuse", "PT-6 1410 N", b24caps,
            note="loop boxes close each T3 loop across both plies" if not hook else "", hw=CARA)
    # BL-040 B-2: the roll-top clip (no load case: a hand cinch on the closure)
    rtm_g = rs.geo["rtm"]
    for pid, where in (("RT", "strap end box-X'd on the hem B-07, free end at the clip-path notch (BL-041 RT-FWD)"),
                       ("RTM", f"female buckle tab box-X'd on the gusset B-03, {rtm_g['depth_from_frame_mm']:.0f} mm aft of "
                               f"the frame seam, {rtm_g['below_seam_mm']:.0f} mm under the collar seam (BL-041 RT-FWD)")):
        for w, h, lab in box(pid):
            add(f"roll-top clip ({pid})", pid, where, w, h, None, "UNRATED: hand cinch on the roll-top closure, no load "
                "case (not on an HA-LS-1 path)", "QC-11 hand pull", hw=BUCKLE,
                note="buckle record 450 N (ESTIMATE) governs anything put on it")
    # any other webbing piece with drawn boxes (a piece a later ticket adds): listed, UNRATED until it has a load case
    named = {r["part"].split(" ")[0] for r in rows}
    for pid, p in sorted(rs.pieces.items()):
        if p.material_id in P.WEBBING and pid not in named:
            for w, h, lab in boxes_of(p):
                add(f"{pid} (new piece)", pid, lab.split(" box-X")[0], w, h, None, "UNRATED: no load case yet "
                    "(pack-designer)", "MT-1 method on the drawn box", note="new in the pattern; give it a load")
    seen, out = set(), []
    for r in rows:                                   # L / R marks of one tab give one row
        k = (r["point"], r["part"], r["where"], r["pattern"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


# ============================================================================ operations
LID_HOW = [   # keyword in the lid_hours row -> beginner instruction
    ("dart", "Fold each B-29a corner dart on its centre, sew leg to leg from the edge to the apex drill mark, tie off "
             "(no backtack at the apex), press the dart toward the aft edge."),
    ("channels topstitched", "Lay each B-29g on its 'strap channel CL' line (x +/-52), edges turned 8 mm, topstitch both "
                             "long edges; channels are 30 mm wide for the 25 mm B-28 strap (drawn so)."),
    ("bartacks", "BT-M bartack across each channel end (tex 90, 304), 3 mm in from the turned end."),
    ("camo caps", f"Turn the short ends of each B-29f {P.SA_FLAT:.0f} mm (its pattern allowance) and topstitch the cap "
                  "on B-29e at its placement; long edges "
                  "go into the ring seams."),
    ("tape baste", "Baste the #5 zip between B-29d (upper) and B-29e (lower) with 6 mm tape; zip stops at the drill "
                   "marks; slider on before closing."),
    ("zip sewn", "ZIP seam: each tape at 5 mm, turn, edge-stitch 3 mm."),
    ("aft corners", "Ease the zip round each aft corner; clip the tape 3 mm at the corner tangent notches."),
    ("wall ring closed", "Join the front wall run B-29c to the aft strips at both ends (30 mm seams), SSa2."),
    ("crown | wall perimeter", "Crown to wall ring notch to notch, darts matched to the corner notches; clip the crown "
                               "allowance every 15 mm on the curves; crown on top."),
    ("crown | wall: closed", "Sew the ring in one pass, needle down at each notch; open the zip first."),
    ("wall | base perimeter", "Base B-29b to the wall ring, notch to notch, inside out; then turn the lid right side out "
                              "through the open zip."),
    ("wall | base: closed", "As the crown ring: one pass, needle down at each notch."),
]
EARLY_FOLD = ("K-W", "HPL", "E5", "I2T", "I2K")    # BL-040 m-10: folded in step 2, sewn by the op that inserts them




def ops(ctx: Ctx) -> list[SewingOp]:
    rs, g = ctx.rs, geo(ctx)
    out: list[SewingOp] = []
    H = HOURS
    sec = {"n": 0, "step": ""}

    def preset(kind):
        return {
            "body": ("WF1", "301", SPI["body"], THREAD["body"], NEEDLE["body"]),
            "light": ("WF1", "301", SPI["light"], THREAD["light"], NEEDLE["light"]),
            "mesh": ("WF1", "301", SPI["light"], THREAD["light"], NEEDLE["mesh"]),
            "hyp": ("WF2", "301", SPI["body"], THREAD["body"], NEEDLE["body"]),
            "box": ("BT / PS (prototype WF2 + J1)", "301 box-X path", SPI["box"], THREAD["box"], NEEDLE["box"]),
            "bt": ("BT", "304", None, THREAD["body"], NEEDLE["body"]),
            "zz": ("ZZ", "304", SPI["body"], THREAD["body"], NEEDLE["body"]),
            "cut": ("SK / LASER / HK", "-", None, "-", "-"),
            "none": ("bench", "-", None, "-", "-"),
        }[kind]

    def step(name):
        sec["step"] = name
        sec["n"] = 0

    def op(title, how, kind, pieces="", seam="", length=0.0, hours=0.0, attach="-", bartack="", sketch="", qc="",
           vol="", notes="", one_off=False):
        sec["n"] += 1
        m, stt, spi, thr, ndl = preset(kind)
        seq = f"{sec['step'].split()[0]}.{sec['n']:02d}"
        out.append(SewingOp(seq=seq, operation=title, machine=m, stitch_type=stt, spi=spi, thread_id=thr, needle=ndl,
                            attachment=attach, notes=(how + (" " + notes if notes else "")).strip(),
                            time_s=0.0 if one_off else round(hours * 3600.0 * FACTORY_RATIO, 0), step=sec["step"],
                            pieces=pieces, seam=seam, length_mm=round(length, 1), bartack=bartack, sketch=sketch, qc=qc,
                            volatile=vol, proto_h=round(hours, 3), per_bag=not one_off))

    def bl(w, h, n=1):          # thread path of n box-X
        return n * AS.box_x(w, h)["path_mm"]

    rate = lambda mm, kind="straight": mm / 1000.0 * H[f"{kind}_m"]  # noqa: E731
    pcs_all = rs.all_pieces(sizes={P.KIT}, webbing=False)
    n_cut = sum(p.quantity for p in pcs_all)
    webs = [w for w in rs.webbing if not ("kit S" in w["kit"] or "kit L" in w["kit"])]
    n_web = sum(w["qty"] for w in webs)
    lp = {r["part"]: r for r in load_points(ctx)}

    # ---------------------------------------------------------------- 0 preparation
    step("0 Prep and cutting")
    op("Print and check the test square", "Print patterns/print_letter/00_PRINT_FIRST_test_square.pdf at 100 %. The "
       "solid square must read 100 mm (+/- 1 mm) both ways, the dashed one 4 in. Do not cut from a wrong-scale print.",
       "none", qc="QC-01", hours=0.1, one_off=True)
    op("Machine set-up and stack swatches", "Make a 150 x 150 mm swatch of each stack and set tension until the lock "
       "sits mid-stack on both faces: (a) ULTRA + 330D body seam, tex 90 / Nm 110 R, 8 SPI; (b) Hypalon on ULTRA, "
       "double row; (c) 25 mm box-X tex 135 / Nm 140 R, 7 SPI; (d) 70D / mesh at 10 SPI. Keep them in the QC folder.",
       "body", seam="SSa2, LSd, BOX, SSa (swatches)", qc="QC-05, QC-06", hours=1.0, sketch="SK-1, SK-2", one_off=True)
    op("Sew the first-article load samples", "Before cutting the bag, sew the proof specimens exactly as the bag: 10 "
       "x 25 mm box-X loops + 2 IMC cam tabs (MT-1), 5 T3 tongues on 70 mm B-17 tabs on B-01 swatches (PT-2), 1 hinge "
       "eye for the HE-FIT dry fit on a printed z 60 fairlead FIRST, then 5 hinge eyes exactly as op 4.05 and SK-8 in "
       f"its order (B-18 rows first through B-18 + B-01 only; then HE folded in half, eye UP, box-X {P.HE_BOX[0]:.0f} x "
       f"{P.HE_BOX[1]:.0f} through HE + B-01 + B-18 below the cheek line; B-18 and both HE raw ends caught in a B-01 | "
       "B-05 SSa2 floor seam sewn with the zipper / edge foot, no binding: PT-3), 5 B-24 links (PT-6), 5 TL-1 sleeves "
       "(38 mm B-25) on real crown bar stock. The bag's load points are sewn only after these pass.", "box", seam="BOX + LSd (as the bag)", bartack="all load points", qc="TEST gates", hours=3.0, sketch="SK-1",
       one_off=True)
    op(f"Cut {n_cut} fabric / sheet pieces", "Per cutting_plan.csv: lay face up (one way for camo and mesh), L+R "
       "pieces face to face, cut windows, slots and slits FIRST, knife clockwise from the grain arrow. Notches 6 mm, "
       "never past the seam line. Hypalon, TPU-840D and HDPE from the DXF on the laser / router.", "cut",
       pieces="all", hours=n_cut * H["cut_piece"], qc="QC-02, QC-03, QC-04")
    op(f"Hot-knife {n_web} webbing / elastic / cord pieces", "Cut lengths in cutting_plan.csv (crown kit M shown; "
       "B-28 and W3 per crown kit). Use the J8 stop; seal both ends; no hard bead wider than the webbing.",
       "cut", pieces="webbing", hours=n_web * WEB_CUT_H, qc="QC-04")
    op("Mark every placement", "Chalk / silver pen on the INSIDE unless the pattern says OUTSIDE; awl the drill marks "
       "(box corners, slit ends, window corners, zip stops). Pieces: B-01, B-03 (L only / R only marks), B-02h, "
       "B-02door, B-02u, B-06f, B-29a.", "none", hours=12 * PLACE_H)

    # ---------------------------------------------------------------- 1 pockets
    step("1 Pockets")
    fp_seam = seam_mm(ctx, "FP body | mouth band")
    op("FP hip-reach pocket: pleats", f"Fold the 2 box pleats on each FP-a (flat {g['fp_flat_w']:.0f} mm wide, "
       f"finished {g['fp_finished_w']:.0f} mm), baste across the BOTTOM edge only, at 6 mm. The top stays "
       f"{g['fp_flat_w']:.0f} mm wide (op 1.02 sews the band to it; the cord gathers it). Do not stretch the mesh.",
       "mesh", pieces="FP-a x2", seam="SSa", length=2 * g["fp_flat_w"], hours=2 * 2 * 2 * H["pivot"] + rate(2 * g["fp_flat_w"]),
       vol="pattern: FP width", sketch="SK-5")
    op("FP mouth band and shock-cord channel", f"Sew FP-b to the FP-a top ({fp_seam:.0f} mm), fold the band on its "
       "fold line over the seam, edge-stitch 2 mm to form the channel; thread the shock cord (FP-cord) and bar it at "
       "both ends inside the side allowance.", "mesh", pieces="FP-a, FP-b x2, FP-cord", seam="SSa + EFa channel",
       length=2 * fp_seam * 2, hours=rate(4 * fp_seam), vol="pattern: FP width", sketch="SK-2")
    i4 = rs.pieces["IMP4-b"]
    op("IMP-4 zip pocket", "Set the #5 zip (210 mm) in the top of IMP4-a (basting tape, ZIP seam), stops at the drill "
       "marks; sew the bellows strip IMP4-b round bottom + sides of IMP4-a.", "light", pieces="IMP4-a, IMP4-b, #5 zip",
       seam="ZIP + SSa", length=2 * 210 + piece_perim(i4) / 2, hours=H["zip_fixed"] + 0.21 * H["zip_m"] + rate(piece_perim(i4) / 2, "curved") + 2 * H["pivot"])
    i8 = rs.pieces["IMP8-a"]
    op("IMP-8 cam cup", "Fold IMP8-a, sew the 2 side seams; sew the laser-cut TPU base IMP8-b in (TPU face out).",
       "body", pieces="IMP8-a, IMP8-b", seam="SSa", length=piece_perim(i8) / 2 + piece_perim(rs.pieces["IMP8-b"]),
       hours=rate(piece_perim(rs.pieces["IMP8-b"]), "curved") + rate(piece_perim(i8) / 2))
    b9 = rs.pieces["B-09c"]
    op("IMP-2 hydration sleeve", "Fold B-09c into a tube, one side seam; turn the top edge 10 mm and edge-stitch; I2T "
       "hang tab goes in later (op 5.01).", "light", pieces="B-09c", seam="SSa + EFa",
       length=b9.bounds(cut=False)[3] + b9.bounds(cut=False)[2], hours=rate(b9.bounds(cut=False)[3] + b9.bounds(cut=False)[2]))
    f2 = rs.pieces["F-02"]
    f02p = g["f02"]
    op("F-02 fly base pocket", "Set the #5 zip (230 mm), turn the edges 10 mm. It is sewn to the floor B-05 in step 4 "
       + (f"on the drawn 'F-02 fly pocket' placement ({f02p['w']:.0f} x {f02p['h']:.0f} mm, {f02p['face']}, zip on the "
          "aft edge, corners drilled; pattern ASSUMPTION F02-CENTRE fore-aft)." if f02p else
          "(placement NOT drawn on B-05: HOLD the floor op until it is)."),
       "body", pieces="F-02, #5 zip", seam="ZIP + EFa", length=2 * 230 + piece_perim(f2),
       hours=H["zip_fixed"] + 0.23 * H["zip_m"] + rate(piece_perim(f2)), vol="pattern: F-01")

    # ---------------------------------------------------------------- 2 small parts
    step("2 Small parts")
    b12 = rs.pieces["B-12"]
    op("B-12 strap-port patches on the swell crests", "Lay a B-12 (TPU face out) on the crest of each B-13x (6, not the "
       "hinge swells), centred on the swell's 'port slot' mark, and sew the 3 mm perimeter. Then cut the swell "
       "fabric out through the B-12's laser-cut 45 x 12 slot (scalpel, the B-12 slot is the guide; the swell slot is a "
       "mark on the pattern, not a pre-cut hole) and edge-stitch the slot.",
       "hyp", pieces="B-12 x6, B-13x x6", seam="LSd", length=6 * (piece_perim(b12) + 2 * (45 + 12)),
       hours=6 * rate(piece_perim(b12) + 114, "applique"), sketch="SK-2")
    sw_ids = ", ".join(f"{i} x{rs.pieces[i].quantity}" for i in g["swell_ids"])
    op("Box the swells", f"Sew the 4 corner folds of every swell ({sw_ids}): fold on 'box the corner', sew "
       "across. Practice: set one swell into a scrap window before touching B-01.", "body",
       pieces=sw_ids, seam="SSa", hours=g["swell_n"] * H["swell_boxed"] / 2, vol="pattern: HE / B-18")
    t3b = [f"{a:.0f} x {b:.0f}" for a, b, _ in boxes_of(rs.pieces["T3"])]
    b17b = [f"{a:.0f} x {b:.0f}" for a, b, _ in boxes_of(rs.pieces["B-17"])]
    op("T3 IM3 tongues onto B-17", "Fold each T3 45 mm round the bed (empty loop: the carabiner clips in later), box-X "
       f"the loop ({t3b[0]}); box-X the other end ({t3b[-1]}) through T3 + B-17 on the drawn 'T3 tongue box-X "
       f"{b17b[0].replace(' ', '')}' at the B-17 centre (Hypalon, coated face out).", "box",
       pieces="T3 x2, B-17 x2", seam="BOX", bartack="T3 (load table)", sketch="SK-1", qc="QC-07",
       hours=2 * 2 * H["bartack"], length=bl(34, 30, 2) + bl(34, 34, 2))
    # BL-040 m-10: loops that a later seam or bartack inserts are folded here, before the ops that sew them in (they
    # were step 7 ops, after insertion, with bartack time that could not happen once they were in a seam)
    early = [w for w in webs if w["id"] in EARLY_FOLD]
    if early:
        txt = "; ".join(f"{w['id']} x{w['qty']} ({w['length_mm']:.0f} mm): "
                        + ", ".join(f"{ln.label} at {ln.points[0][1]:.0f} mm" for ln in lines(rs.pieces[w["id"]], "fold"))
                        for w in early if w["id"] in rs.pieces)
        op("Fold the seam-inserted loops", "Fold and clip each loop, raw ends together; no stitching here: the seam or "
           f"bartack that inserts it sews it (ops named in its use). {txt}.", "none",
           pieces=", ".join(f"{w['id']} x{w['qty']}" for w in early), hours=sum(w["qty"] for w in early) * WEB_CUT_H,
           sketch="SK-7")
    op("IME fairlead eyes (frame kit)", "NECK FIRST (BL-044, as op 4.05's HE): on the FLAT strip fold each long edge "
       f"{P.IME_NECK_EDGE:.0f} mm in between the two 'neck lines' (18 mm wide: the eye passes the 20 mm throat of the "
       "BL-045 fairlead) and sew one BT-M tack across each leg at the 'neck tack' lines " + step_spec("bt", "304") + ". "
       "Then fold each 38 mm IME at 100 mm into an eye (neck folds INSIDE), box-X 34 x 30. These go on the frame "
       "fairleads, not the bag.", "box", pieces="IME x6", seam="BOX", bartack="IME", hours=6 * H["bartack"], qc="QC-07",
       length=bl(34, 30, 6))

    # ---------------------------------------------------------------- 3 door
    step("3 Door D2 and hinge band")
    sh7 = rs.pieces["SH-07"]
    op("SH-07 slider garage on the right blade", "Turn the edges 8 mm and topstitch SH-07 to B-02u at its placement.",
       "body", pieces="SH-07, B-02u", seam="LSd", length=piece_perim(sh7), hours=rate(piece_perim(sh7), "applique"))
    op("IMP-4 onto the door, INSIDE face", "Sew the IMP-4 bellows edge to B-02door at the IMP-4 placement (inside), "
       "pivot at the drill marks.", "light", pieces="IMP-4, B-02door", seam="SSa", length=piece_perim(i4) / 2,
       hours=rate(piece_perim(i4) / 2) + 4 * H["pivot"])
    zd = seam_mm(ctx, "door | blade U (#10 zip, R 55 corners)")
    op("Door #10 zip", f"Basting-tape the #10 zip to the door edge and to the blade U inner edge ({zd:.0f} mm, "
       f"{zd / IN:.1f} in), notch to notch, corner tangent notches at each R 55 corner; 2 sliders head to head; sew "
       "each tape at 5 mm, turn, edge-stitch 3 mm; zip stops at the hinge band.", "body",
       pieces="B-02door, B-02u, #10 zip", seam="ZIP", length=4 * zd,
       hours=H["zip_fixed"] + zd / 1000 * H["zip_m"] + 2 * H["zip_corner"], attach="zipper foot (left / right)",
       qc="QC-09", sketch="SK-2")
    b22x = g["b22_x"]
    b22 = rs.pieces["B-22"]
    op("B-22 guy anchors INSIDE the hinge band", f"Place each B-22 (coated face down on the band's inside) at x "
       f"+/-{b22x:.1f} mm ({b22x / IN:.2f} in) on the drawn placement (drawn x +/-{g['b22_drawn_x']:.0f}, moved "
       f"{g['b22_moved']:.1f} mm inboard, ASSUMPTION B22-IN). Double-row perimeter 3 / 9 mm.", "hyp",
       pieces="B-22 x2, B-02h", seam="LSd (2 rows)", length=2 * 2 * piece_perim(b22),
       hours=2 * rate(2 * piece_perim(b22), "applique"), vol="pattern: B-22 x",
       sketch="SK-4", qc="QC-07")
    llt_box = (boxes_of(rs.pieces["LLT"]) or [(21.0, 25.0, "")])[0][:2]
    band_llt = next(((w, h) for w, h, lab in boxes_of(rs.pieces["B-02h"]) if "LLT" in lab), None)
    op("Guy ladder-lock tabs LLT through B-22", "Fold each LLT round the bar of a heavy 25 mm ladder lock, box-X "
       "through LLT + B-22 + B-02h at the drawn 'B-22 / guy LLT box' (drill corners).", "box",
       pieces="LLT x2, B-22, B-02h, 2 heavy ladder locks", seam="BOX", bartack="LLT + B-22 + B-02h",
       hours=2 * H["bartack"], vol="pattern: B-22 x", sketch="SK-1, SK-4", qc="QC-07", length=bl(*llt_box, 2),
       notes=f"Box {llt_box[0]:.0f} x {llt_box[1]:.0f} mm (LLT piece)."
             + (f" PATTERN MISMATCH: B-02h draws {band_llt[0]:.0f} x {band_llt[1]:.0f}; sew the LLT size."
                if band_llt and tuple(band_llt) != tuple(llt_box) else ""))
    b28_front = _b28_front(rs) or "B-28t"
    b28_box = next(((w, h) for w, h, lab in boxes_of(rs.pieces["B-02h"]) if "B-28" in lab), None)
    op("B-28 front tabs on the hinge band (OUTSIDE)", f"Fold a {b28_front} round the bar of a heavy ladder lock (lock bar "
       "on the top line of the drawn 'B-28 front lock tab' placement), box-X it through tab + band on the OUTSIDE of "
       "B-02h at the drawn 'B-28 front tab (OUTSIDE)' box"
       + (f", {b28_box[0]:.0f} x {b28_box[1]:.0f} mm" if b28_box else " (box NOT drawn: HOLD)")
       + ". DECISION B28-FACE (BL-034): the crown strap runs down the band's aft face to the lock, so the tab is "
       "outside.", "box", pieces=f"{b28_front} x2, B-02h, 2 heavy ladder locks", seam="BOX",
       bartack=b28_front, hours=2 * H["bartack"], sketch="SK-4", qc="QC-07",
       length=bl(*(b28_box or (21.0, 20.0)), 2))
    hb = seam_mm(ctx, "hinge band | door (door hinge, z 650)")
    op("Hinge band to the door top", f"Join B-02h to the door top ({hb:.0f} mm), SSa2.", "body",
       pieces="B-02h, B-02door", seam="SSa2", length=2 * hb, hours=rate(hb))
    hbu = seam_mm(ctx, "hinge band R | blade U") + seam_mm(ctx, "hinge band L | blade U")
    op("Hinge band ends to the blade U", f"Join both short band ends to the blade tops ({hbu:.0f} mm total). The "
       f"B-22 tabs sit {P.B22_EDGE_CLEAR:.0f} mm inside this seam line: turn the allowances AWAY from B-22 (onto the "
       "blade) and sew the SSa2 second row on the blade side, so it does not run onto the Hypalon edge.", "body",
       pieces="B-02h, B-02u", seam="SSa2", length=2 * hbu, hours=rate(hbu) + 2 * H["pivot"])

    # ---------------------------------------------------------------- 4 main bag
    step("4 Main bag")
    op("Check the B-01 cut-outs", f"{g['windows']} swell windows, 2 B-27 slits ({g['port_slit_mm']:.0f} mm at x "
       "+/-52), IMP-2 keeper drill marks. All cut, corners awled.", "none", pieces="B-01", hours=0.1,
       vol="pattern: HE / B-18", qc="QC-03")
    op(f"Set the {g['swell_n']} swells into the B-01 windows", f"Swell base to window edge, INSIDE B-01, notch to "
       f"notch ({g['windows']} windows, {g['window_perim_mm']:.0f} mm of window edge in all; hinge windows: "
       f"{g['hinge_windows']}). Sew from the swell side, needle down at every corner.", "body",
       pieces=f"{sw_ids}, B-01", seam="SSa", length=g["window_perim_mm"], hours=g["swell_n"] * H["swell_boxed"] / 2,
       vol="pattern: HE / B-18", sketch="SK-3", qc="QC-08")
    pz = g["port_slit_mm"]
    op("B-27 guy ports (2)", f"Each slit ({pz:.0f} mm, x +/-52, z {g['port_z'][0]:.0f}-{g['port_z'][1]:.0f}): turn "
       f"both edges {g['port_turn']:.0f} mm and edge-stitch; sew the B-27f facing INSIDE along the inboard stitch line "
       "so the outboard edge laps 20 mm over it; bartack both slit ends. It crosses the setback crease at z 631: the "
       "facing follows the crease.", "body", pieces="B-01, B-27f x2", seam="EFa + LSd (lapped port)",
       length=2 * (2 * pz + 170), hours=2 * (rate(2 * pz + 170) + 2 * H["bartack"]), bartack="B-27 slit ends",
       sketch="SK-2, SK-3", qc="QC-10")
    b17 = rs.pieces["B-17"]
    op("B-17 IM3 tabs OUTSIDE B-01", "Place each B-17 (with its T3) OUTSIDE B-01 at x +/-115, z 385-455 (placement). "
       "Double-row perimeter 3 / 9 mm, 8 SPI, tex 90; the 90 mm top edge carries the load: no gaps, backtack 10 mm.",
       "hyp", pieces="B-17 x2, B-01", seam="LSd (2 rows)", length=2 * 2 * piece_perim(b17),
       hours=2 * rate(2 * piece_perim(b17), "applique"), bartack="B-17 perimeter", sketch="SK-3",
       qc="QC-07")
    b18 = rs.pieces["B-18"]
    hg = rs.geo["he"]
    hbx = (boxes_of(rs.pieces["HE"]) or [(34.0, 34.0, "")])[0][:2]
    b18_rows = sum(_len(ln.points) for ln in lines(b18, "stitch", "perimeter row"))
    op("B-18 doublers + HE hinge eyes (DECISION HE-ONE / HE-PIN, sketch SK-8)", he_405_text(ctx), "box",
       pieces="HE x2, B-18 x2, B-01", seam="LSd + BOX", length=2 * (b18_rows + 2 * 40.0) + bl(*hbx, 2),
       hours=2 * (3 * H["bartack"] + rate(b18_rows, "applique")), bartack="HE + B-18 + B-01",
       vol="pattern: HE / B-18", sketch="SK-8, SK-1, SK-3", qc="QC-07")
    op("IMP-2 keeper tabs I2K on B-01", "Fold each I2K, bartack at the 2 'IMP-2 keeper tab' drill marks (inside).",
       "bt", pieces="I2K x2, B-01", seam="BT", hours=2 * H["bartack"])
    b11 = g["b11"]
    if b11:
        n11 = 2 * b11["per_gusset"]
        bw, bh = g["b11_box"]
        tabs = "; ".join(f"{k} z {z:.0f} ({dx:.0f} mm aft of the frame seam)" if "muzzle" in k else
                         f"{k} z {z:.0f} ({dx:.0f} mm aft of the frame seam, 40 mm forward of the aft corner)"
                         for k, z, dx in b11["tabs"])
        op(f"B-11 lash tabs ({n11}) on the gussets", f"Gusset flat work, before the gusset seams: {b11['per_gusset']} "
           f"tabs on each B-03 at the drawn 'B-11 lash tab' placements ({tabs}). Tab coated face out, slot end UP; awl "
           f"the 4 'B-11 box corner' drill marks; sew the {bw:.0f} x {bh:.0f} mm 'B-11 sew-down box' (rectangle + both "
           "diagonals, 301) through tab + gusset. Right gusset: bow riser; left: LIGHT LASH ONLY, no load rating "
           "(BL-040 m-12); muzzle keepers both "
           "sides, AFT of the roll-clip path (BL-041 RT-FWD: 10 mm clear of the buckle; pattern ASSUMPTION B11-PLACE / "
           "MK-GAP, settled by the archery and rifle loadout fits and FIT-R3).", "hyp",
           pieces=f"B-11 x{n11}, B-03 x2", seam="LSd (box-X sew-down)", length=n11 * AS.box_x(bw, bh)["path_mm"],
           hours=n11 * H["bartack"], sketch="SK-5", qc="QC-07")
    else:
        op("B-11 lash tabs (8)", "Bow riser + muzzle keepers: placements NOT drawn on the pattern. HOLD until they "
           "are.", "hyp", pieces="B-11 x8", seam="LSd", hours=8 * H["bartack"], notes="HOLD (pattern).")
    # BL-040 B-2 DECISION RT-MATE: the roll-clip buckle's female half on each gusset, flat work before the gusset seams
    if "RTM" in rs.pieces:
        rtm = rs.geo["rtm"]
        rbx = (boxes_of(rs.pieces["RTM"]) or [(21.0, 25.0, "")])[0][:2]
        rlo = rs.geo["rt_layout"]
        op("RTM roll-clip buckle tabs on the gussets", "Gusset flat work, before the gusset seams. (1) Thread each RTM "
           "through the bar of a side-release buckle's FEMALE half (the half with the socket) and fold it on its fold line. "
           f"(2) Lay it on the OUTSIDE of each B-03 on the drawn 'RTM roll-clip buckle tab' placement (z {rtm['z']:.0f}, "
           f"{rtm['below_seam_mm']:.0f} mm under the collar seam, {rtm['depth_from_frame_mm']:.0f} mm aft of the frame seam "
           "line): buckle bar on the top line, socket pointing UP (the male half on the RT strap comes down into it from "
           "the roll end along the drawn 'RT strap from the roll end' line). DECISION W3-OVER (BL-043): the buckle sits "
           f"{P.RT_CLEAR:.0f} mm under the lowest W3 edge of every crown kit (W3 z {rlo['z_w3_min']:.0f}-"
           f"{rlo['z_w3_max']:.0f} with the torso setting), so W3 never bears on it; nothing else is sewn on the strap "
           "path (the BL-041 W3G guide is deleted). "
           f"(3) Box-X {rbx[0]:.0f} x {rbx[1]:.0f} at the drawn 'RTM buckle tab' box through RTM (2 plies) + B-03 "
           + step_spec("box") + ".", "box",
           pieces="RTM x2, B-03 x2, 2 SR buckle female halves", seam="BOX", bartack="RTM",
           hours=2 * (H["bartack"] + PLACE_H), length=bl(*rbx, 2), sketch="SK-10", qc="QC-07")
    kb = rs.pieces["SH-01b"]
    op("Gusset flat work: kick bands", "SH-01b on each gusset foot at the 'kick band top' line, top edge turned 8 mm, "
       "topstitched; bottom and sides go in the seams.", "body", pieces="SH-01b x2, B-03 x2", seam="LSd",
       length=2 * kb.bounds(cut=False)[2], hours=rate(2 * kb.bounds(cut=False)[2], "applique"))
    op("Gusset flat work: FP pockets (both)", f"Sew each FP to its gusset at the placement, z {g['fp_z'][0]:.0f}-"
       f"{g['fp_z'][1]:.0f}, {g['fp_finished_w']:.0f} mm face; inner edge >= {g['fp_clear_req'] or 9:.0f} mm off "
       f"the frame seam ({g['fp_margin'] if g['fp_margin'] is not None else '-'} mm at the tightest point, pattern "
       "fp_min_margin_mm). "
       "Bottom and FRAME-side edge 301 at 3 mm, box pleats laid flat, bartack the 2 mouth corners. The AFT edge lies "
       "on the aft corner seam line: baste it at 6 mm inside the allowance only; the aft corner seam (op 4.13) sews it, "
       "UNDER the K-W keeper loops (SK-9).", "mesh", pieces="FP x2, B-03 x2",
       seam="LSd", length=2 * (g["fp_h"] * 2 + g["fp_finished_w"]), bartack="FP corners (BT-S)",
       hours=2 * (rate(2 * g["fp_h"] + g["fp_finished_w"]) + 2 * H["bartack"]), vol="pattern: FP width",
       sketch="SK-5")
    op("Gusset flat work: IMP-8 (R only) and hose ports", f"IMP-8 cup at 'IMP-8 cup top (R only)'. Hose slots (both "
       f"gussets, z {g['hose_z']:.0f}; BL-043 DECISION HOSE-LOW: below W3 at every crown setting, so a cinched W3 never "
       "lies on the hose): B-09p binding (TPU, laser-cut) laid over the slot, perimeter + slot edge stitched.", "body", pieces="IMP-8, B-09p x2, B-03 x2", seam="LSd",
       length=piece_perim(i8) / 2 + 2 * 2 * piece_perim(rs.pieces["B-09p"]),
       hours=rate(piece_perim(i8) / 2) + 2 * rate(2 * piece_perim(rs.pieces["B-09p"]), "applique"))
    s_r = seam_mm(ctx, "B-01 | gusset R (FP-R edge, pole-grip tab)")
    s_l = seam_mm(ctx, "B-01 | gusset L (2 hard-point loops, FP-L edge)")
    op("Frame-side box seams B-01 | gussets", f"R ({s_r:.0f} mm): E5 pole-grip tab at z {g['pole_tab_z']:.0f} and the "
       "ONE end of the B-26 shock cord inserted 15 mm at the 'B-26 tripod keeper' notch (the other end stays loose "
       "until op 4.13). L ({:.0f} mm): 2 HPL hard-point loops at z {:.0f} / {:.0f} inserted. Notch to notch every 50 "
       "mm; SSa2.".format(s_l, *g["hard_z"]), "body",
       pieces="B-01, B-03 x2, E5, E5-cord, B-26, HPL x2", seam="SSa-ins + SSa2", length=2 * (s_r + s_l),
       hours=rate(s_r + s_l) + 3 * H["bartack"], sketch="SK-5", qc="QC-08")
    s_br = seam_mm(ctx, "blade U | gusset R (aft corner)")
    s_bl = seam_mm(ctx, "blade U | gusset L (aft corner, 2 hard-point loops)")
    kwz = g["kw_z"]
    kw_txt = ("; ".join(f"{side} seam z " + " / ".join(f"{kwz[w][side]:.0f}" for w in sorted(kwz)) for side in ("R", "L"))
              + f" ({', '.join(sorted(kwz))}; the drawn 'K-W keeper' notches on B-03 and B-02u, pattern ASSUMPTION "
              "KW-PATH)") if kwz else "heights NOT drawn: HOLD the keepers"
    n_kw = next((w["qty"] for w in rs.webbing if w["id"] == "K-W"), 6)
    kw_fp = [(wid, side, z) for wid in sorted(kwz) for side, z in kwz[wid].items() if P.FP_Z[0] <= z <= P.FP_Z[1]]
    kw_fp_txt = ", ".join(f"{side} z {z:.0f} ({wid})" for wid, side, z in kw_fp) or "none"
    op("Aft corner seams blade U | gussets (closes the tube)", f"R and L ({s_br:.0f} / {s_bl:.0f} mm): 2 HPL loops in "
       f"the L seam at the hard-point notches; {n_kw // 2} K-W keeper loops in each seam, raw ends in the seam, at the "
       f"W1-W3 crossings: {kw_txt}. R seam: the B-26 free end inserted 15 mm at the 'B-26 keeper' notch. SSa2. "
       "LAYER ORDER where a K-W keeper meets the FP pocket edge (SK-9; it happens at "
       f"{kw_fp_txt}): gusset B-03 face up, FP mesh edge on it (already basted), the K-W loop ON TOP of the mesh "
       "(raw ends at the cut edge, loop pointing into the gusset), then the blade U face down. Sew. Turned out, the "
       "keeper sits OUTSIDE the mesh, so the haul wrap runs over the pocket, not inside it. Check each one before "
       "sewing the next 100 mm: a keeper under the mesh means unpicking this 715 mm seam.", "body",
       pieces=f"B-02u, B-03 x2, HPL x2, K-W x{n_kw}, B-26", seam="SSa-ins + SSa2", length=2 * (s_br + s_bl),
       hours=rate(s_br + s_bl) + 8 * H["bartack"], sketch="SK-9, SK-5", qc="QC-08")
    fl = sum(seam_mm(ctx, n) for n in ("bottom | B-01 (hinge eyes in it)", "bottom | gusset R", "bottom | gusset L",
                                       "bottom | blade U kick strip"))
    if g["b16"]:
        b16 = rs.pieces["B-16"]
        L16 = 2 * b16.bounds(cut=False)[2]
        op("US floor channels B-16 on F-02", f"Turn both ends of each B-16 15 mm (left OPEN: the 25 mm under-strap "
           f"passes through), lay it across F-02's outer face on the drawn 'B-16 channel' lines (stations "
           f"{g['us_channels']['stations_mm'] if g['us_channels'] else '-'} mm), topstitch both long edges, bartack the "
           "4 corners.", "body", pieces=f"B-16 x{b16.quantity}, F-02", seam="LSd", length=b16.quantity * L16,
           hours=b16.quantity * (rate(L16, "applique") + 2 * H["bartack"]), vol="pattern: ledger (US-chan)")
        us_txt = "US channels: on F-02 (op above)."
    else:
        us_txt = "US floor channels: NOT drafted (ledger row US-chan, not_drafted) - HOLD."
    op("Floor B-05 (F-02 first)", "Sew F-02 to the OUTSIDE of B-05 on the drawn 'F-02 fly pocket' placement (zip edge "
       f"aft, corner drill marks), perimeter row. Then the floor ring ({fl:.0f} mm): B-01 edge "
       "first with the HE tails and the B-18 lower edges caught in it, then gussets, then the blade kick strip; "
       f"quarter notches matched, needle down at the 4 corners. SSa2. At the two hinge eyes turn the allowances DOWN "
       "onto B-05 (the second row runs on the floor, clear of the HE box, ASSUMPTION HE-GAP). BL-041 n-14: sew the two "
       "hinge-eye spans (x +/-115, 50 mm each way) with the ZIPPER / EDGE FOOT: the floor seam runs 4 mm from the HE box "
       "stack and a walking foot (5-6 mm half width) rides up on it there; check from inside that "
       f"the B-18 lower edge and both HE raw ends are in the seam. {us_txt}", "body",
       pieces="B-05, F-02, B-01, B-03 x2, B-02u", seam="SSa2",
       length=2 * fl + piece_perim(f2), hours=rate(fl) + H["ring"] + 4 * H["pivot"] + rate(piece_perim(f2), "applique"),
       qc="QC-08", vol="" if g["b16"] else "pattern: ledger (US-chan)")

    # ---------------------------------------------------------------- 5 collar
    step("5 Collar and roll top")
    cr = seam_mm(ctx, "collar frame side | collar R") + seam_mm(ctx, "collar frame side | collar L")
    op("Collar tube", f"B-06f (ULTRA) to B-06 both sides ({cr:.0f} mm); I2T hang tab at the B-06f drill mark.", "light",
       pieces="B-06f, B-06, I2T", seam="SSa2", length=2 * cr, hours=rate(cr) + H["bartack"])
    hm = seam_mm(ctx, "hem back seam")
    ht = seam_mm(ctx, "hem | collar top (ring)")
    rt = [w for w in webs if w["id"] == "RT"][0]
    rtg = rs.geo.get("rt_on_b07") or {}
    rbx = (boxes_of(rs.pieces["RT"]) or [(21.0, 25.0, "")])[0][:2]
    # BL-040 B-2: the RT straps go on the FLAT hem first (one fabric layer, no HDPE under the needle)
    op("RT roll-clip straps on the flat hem B-07", f"B-07 still flat. Each RT strap ({rt['length_mm']:.0f} mm): lay its "
       "first 60 mm (to the 'end of the sewn zone' line) on the OUTSIDE of B-07 on the drawn 'RT roll-clip strap' "
       f"rectangle (L at x {rtg.get('L', {}).get('x0', 0):.0f}-{rtg.get('L', {}).get('x1', 0):.0f} mm, R at x "
       f"{rtg.get('R', {}).get('x0', 0):.0f}-{rtg.get('R', {}).get('x1', 0):.0f} mm from the B-07 left end), strap end "
       "on the outer line, the free strap running along the hem out across the 'roll end' notch (BL-043 DECISION "
       "RT-ORIGIN: the strap leaves the roll at its end, where the hem folds; its box sits on the B-07s strip, "
       f"{rtg.get('R', {}).get('box_to_gap_mm', 0):.1f} mm clear of the 40 mm fold gap). Box-X "
       f"{rbx[0]:.0f} x {rbx[1]:.0f} at the drawn 'RT strap' box through strap + B-07. Fold the free strap back over "
       "the box for now and clip it out of the way. The ADJUSTABLE (male) buckle half is threaded on the free end at "
       "hardware fitting (op @FIT).", "box", pieces="RT x2, B-07", seam="BOX", bartack="RT", length=bl(*rbx, 2),
       hours=2 * (H["bartack"] + PLACE_H), sketch="SK-10", qc="QC-07")
    op("Roll-top hem with HDPE strips", f"Close the hem back seam ({hm:.0f} mm). Sew the hem to the collar top ring "
       f"({ht:.0f} mm), the RT straps hanging free outside; fold over the two B-07s HDPE strips, their ends on the "
       "drawn 'B-07s strip end' lines (a 40 mm gap at each roll end, where the hem folds flat), and stitch closed "
       "(EFb), keeping the strap ends out of the fold.", "body", pieces="B-07, B-07s x2, B-06", seam="SSa + EFb",
       length=hm + 2 * ht, hours=rate(hm) + rate(ht) + H["ring"], sketch="SK-2")
    cb = seam_mm(ctx, "collar | body tops (ring)")
    op("Collar ring to the body", f"Collar to the body tops ({cb:.0f} mm), matched at every panel-corner V-notch. The "
       "seam closes the top end of each B-27 port; bartack the port top over it.", "body",
       pieces="collar, body", seam="SSa2", length=2 * cb, hours=rate(cb) + H["ring"] + 2 * H["bartack"],
       qc="QC-08, QC-10")

    # ---------------------------------------------------------------- 6 lid (from the drafted-lid hour rows)
    step("6 Crown lid B-29 (as hunted)")
    for r in ctx.lid["rows"]:
        t = r["op"]
        if t.startswith("cut"):
            continue                                        # cut in step 0
        kind = "bt" if "bartack" in t else ("light" if "base" in t else "body")      # BL-040 m-8: BT-M is 304 tex 90
        L = r["qty"] * 1000.0 if r["rate_h"] in (H["straight_m"], H["curved_m"], H["applique_m"], H["zip_m"]) else 0.0
        seam = ("DART" if "dart" in t else "SSa2" if "perimeter" in t or "ring" in t else "ZIP" if "zip" in t
                else "BT" if "bartack" in t else
                "LSd" if ("channel" in t or "cap" in t) else "SSa2")
        how = next((v for k_, v in LID_HOW if k_ in t), "As the drafted B-29 pieces.")
        op(f"Lid: {t}", how + " (rows from patterns_corrie_f_rev3.lid_hours)", kind, pieces=", ".join(sorted(i for i in rs.pieces if i.startswith("B-29"))), seam=seam, length=L * (2 if seam in ("SSa2", "ZIP") else 1), hours=r["hours"],
           sketch="SK-6")

    # ---------------------------------------------------------------- 7 straps and webbing (from the pieces)
    step("7 Straps and webbing")
    # Webbing parts whose box-X an earlier box op already sews (T3 2.03, IME 2.04, LLT 3.05, HE 4.05; 2 of the 6 B-28t
    # in 3.06) get no second op here for those pieces (BL-034 C: the old 7.15 IME, 7.19 T3, 7.22 LLT and 7.18 HE sewed
    # them twice). A cord that an earlier op inserts is skipped.
    boxed_before: dict = {}
    for o in out:
        if "box" in o.stitch_type and o.length_mm:
            for x in o.pieces.split(","):
                t, _, n_ = x.strip().partition(" x")
                boxed_before[t] = boxed_before.get(t, 0) + (int(n_) if n_.isdigit() else 1)
    named_before = {t for o in out for t in _tokens(o.pieces)}
    for w in webs:
        pid = w["id"]
        p = rs.pieces.get(pid)
        done = boxed_before.get(pid, 0)
        if done >= w["qty"] or pid in EARLY_FOLD or pid == "F-EL":
            continue                                        # F-EL: threaded in op 9.02 (BL-040 m-6)
        if done:
            w = {**w, "qty": w["qty"] - done, "use": f"{w['use']} (the other {done} are boxed in an earlier op)"}
        if "cord" in w["material_id"]:
            if pid in named_before:
                continue                                    # sewn where it is inserted (ops 1.02, 4.11, 4.12)
            op(f"{pid}: {w['use']} x{w['qty']}", f"Cut {w['length_mm']:.0f} mm ({w['length_mm'] / IN:.1f} in), melt / "
               "whip both ends; fitted at hardware assembly (op below) as its use says.", "none",
               pieces=f"{pid} x{w['qty']}", hours=w["qty"] * WEB_CUT_H)
            continue
        folds = [ln.label for ln in lines(p, "fold")] if p is not None else []
        bxs = boxes_of(p) if p is not None else []
        lpr = lp.get(pid)
        if w["material_id"].startswith("elastic"):
            op(f"{pid}: {w['use']} x{w['qty']}", f"Cut {w['length_mm']:.0f} mm, lap 15 mm into a loop round its strap, "
               "zigzag the lap (3 passes).", "zz", pieces=f"{pid} x{w['qty']}", seam="BT (zigzag lap)",
               hours=w["qty"] * H["bartack"])
            continue
        if not folds and not bxs:
            how = "straight strap, sealed ends; threaded at assembly (op @FIT)."
            kind = "none"
            hrs = 0.0
            wl = 0.0
        else:
            how = (f"{w['length_mm']:.0f} mm ({w['length_mm'] / IN:.1f} in). Folds: {'; '.join(folds) or '-'}. "
                   + (f"Box-X: {', '.join(f'{a:.0f} x {b:.0f}' for a, b, _ in bxs)} at the drawn marks."
                      if bxs else "Box-X / bartack per the load table where it is caught in a seam."))
            kind = "box" if (bxs or lpr) else "bt"
            hrs = w["qty"] * max(1, len(bxs)) * H["bartack"]
            wl = w["qty"] * (sum(bl(a, b) for a, b, _ in bxs) if bxs else (bl(21, 25) if lpr else 0.0))
        if pid == "IMC":                           # BL-043 m-5: the loops close on the bars, so the bars go in first
            how = ("HARDWARE FIRST (BL-043 m-5): this op closes both loops, so before sewing either box thread the "
                   "25 mm CAM's anchor bar into the 'fold round the CAM anchor bar' loop (all 3 tabs) and the rated "
                   "G-HOOK's bar into the other loop of the IM1 and IM2 tabs; the IM3 tab's second loop stays EMPTY (the "
                   "wiregate carabiner clips in at op @FIT). Hardware for this op: 3 cams, 2 G-hooks. Then: " + how)
        if pid in ("US", "USA"):                   # BL-044 (BL-045 imus_eye_envelope): necked where it passes the throat
            neck = (f"NECK FIRST (BL-044, as op 4.05's HE): on the FLAT strip fold each long edge {P.US_NECK_EDGE:.1f} mm "
                    "in between the two 'neck lines' (18 mm: the eye passes the 20 mm throat of the BL-045 fairlead), "
                    "one BT-M tack across each leg at the 'neck tack' lines " + step_spec("bt", "304") + ". ")
            if pid == "USA":
                how = (neck + "HARDWARE FIRST: thread the US CAM's anchor bar into the 'fold round the CAM anchor bar' "
                       "loop before its box is sewn; the necked 'RIGHT PIN' loop is sewn closed round the right pin's "
                       "UHMWPE sleeve (no pin in it: the pin goes through cheek, sleeve, cheek at frame-kit assembly). "
                       "Hardware for this op: 2 cams. Then: " + how)
            else:
                how = neck + how
        if pid == "B-25":
            tp = rs.geo["b25"]["topology"]
            kS = tp["kits"][tp["governing_kit"]]
            how += (" Toggle tabs: fold each end on its 'tab fold' line and sew the drawn tip-end box (DECISION "
                    "B25-BOX: the clear loop passes the POM toggle). TOPOLOGY (BL-043 DECISION B25-TOPO, sketch SK-12): "
                    "round the bar = the sleeve; the strip leaves the bar DOWN on its aft (bag) side inside the sleeve "
                    f"band, drops {tp['lengths_mm']['drop']:.0f} mm, turns 90 deg inboard at the drawn 45 deg 'MITRE' "
                    f"fold (under the sleeve, x {tp['band_x'][0]:.1f}-{tp['band_x'][1]:.1f}), is NECKED to "
                    f"{tp['neck_w_mm']:.0f} mm on the 'NECK' line (lower edge folded up) from the band edge inboard, and "
                    "wraps once round the spine under the clamp collar, continuous to the other side. Nothing on the "
                    "wearer side of the bar. FRAME COORDINATION: the bar sleeves close round the crown top bar BEFORE the "
                    "crown corners are bonded (H1 build); the two sleeve-lap bartacks (BT-M) are sewn at frame assembly, "
                    "not here. GATE B25-FIT (before the laps are tacked): dry-fit the bridle on the crown with the clamp "
                    f"fitted and the crown at kit {tp['governing_kit']}'s SHORTEST setting ({kS['torso_in']:g} in): the "
                    f"mitres sit inside the sleeve bands, the necked run passes under the clamp collar, and the spine "
                    f"wrap clears the pawl housing (design {kS['clear_mm']:.0f} mm on the BL-045 clamp and measured housing; the run "
                    f"reaches the spine {tp['spine_fore_mm']:.2f} mm FORE of the bar plane); a "
                    "no stops the laps: photo to the pack-designer.")
        op(f"{pid}: {w['use']} x{w['qty']}", how, kind,
           pieces=f"{pid} x{w['qty']}" + (", 3 x 25 mm cam, 2 x rated G-hook" if pid == "IMC" else ""),
           seam="BOX" if kind == "box" else ("BT" if kind == "bt" else "-"),
           bartack=pid if lpr else "", hours=hrs, length=wl, sketch="SK-1, SK-7" + (", SK-12" if pid == "B-25" else ""),
           qc="QC-07" if lpr else "",
           vol="pattern: ledger" if pid in ("US",) else "")
    cords = [w["id"] for w in webs if "cord" in w["material_id"] and w["id"] not in named_before]
    op("Fit the hardware", "IM1-IM3 (SK-11, DECISION IM-CAM-TAB): the cam is SEWN to the IMC tab (cam end box), the "
       "IMC's other loop carries the G-hook (IM1 / IM2) or the wiregate carabiner (IM3); the IM strap's free end goes "
       "through the cam from the wearer side, its sewn loop girth-hitched on the left eye; US1/US2: "
       "cam, then the STAINLESS 25 mm tri-glide threaded behind the cam as the cradle slip backstop (orchestrator "
       "2026-11-13; gate US-BS); T3 loops: wiregate carabiner + TPU sleeve; W1-W3: rated G-hook end, heavy ladder lock on "
       "the gusset side; W3 is the OUTER layer (BL-043 DECISION W3-OVER): it may lie over the RT straps and the roll, "
       "so slacken W3 (G-hook off) before opening the roll top; guys: toggle in the B-25 tab, through the B-27 port, heavy ladder lock on LLT, nylon tri-glide "
       "tail keeper; B-28: toggle rear, ladder lock both ends, 2 elastic keepers; RT: thread the free end through the "
       "ADJUSTABLE (male) half of each side-release buckle (its female half is already on the RTM gusset tab), K-RT "
       "keeper below it; E5: cord "
       "lock" + (f"; cords {', '.join(cords)} per their use" if cords else "") + ".", "none",
       pieces="hardware", hours=1.0, qc="QC-11", sketch="SK-11")

    # ---------------------------------------------------------------- 8 add-ons
    step("8 Add-ons (scope pod as hunted, meat liner meat trip)")
    a1 = sum(piece_perim(rs.pieces[i]) for i in ("A1-a", "A1-b", "A1-d"))
    op("Scope pod A1", "Box pleats in A1-b, leading-edge bar A1-d on the sleeve mouth (EFa), sleeve face to back "
       "panel A1-a round the perimeter; 4 hooks / loops to the HPL hard points.", "body", pieces="A1-a, A1-b, A1-d",
       seam="SSa2 + EFa", length=a1, hours=rate(a1 / 2) + 2 * H["pivot"] + 4 * H["bartack"])
    ms = sum(piece_perim(rs.pieces[i]) for i in ("MS-a", "MS-b", "MS-c"))
    op("Meat liner MS (SWAP slab)", "Tube MS-a to frame face MS-b and floor MS-c; HDPE MS-s in the roll pocket. "
       "Silpoly: clips, no pins; 10 SPI tex 70.", "light", pieces="MS-a, MS-b, MS-c, MS-s x2", seam="SSa2",
       length=ms, hours=rate(ms / 2) + H["ring"])

    # ---------------------------------------------------------------- 9 fly (volatile: reads the F-01 pattern)
    step("9 Rain fly F-01")
    if g["fly_drafted"]:
        fids = g["fly_ids"]
        fs = {k: v for k, v in ctx.seams.items() if "F-01" in k}
        fl_len = sum(fs.values())
        note = " ".join(rs.pieces[i].labels.get("note", "") for i in fids[:1])
        op("F-01 fly: panel seams", f"Join the fly panels ({'; '.join(f'{k} {v:.0f} mm' for k, v in fs.items())}). "
           f"Silpoly: weights and clips, no pins; 301 then flat-fell; seam-seal the felled seams (piece note: {note})",
           "light", pieces=", ".join(fids), seam="SSa then LSc flat-fell (ISO 4916 class 2)", length=3 * fl_len,
           hours=rate(fl_len) * 2, vol="pattern: F-01")
        hem = sum(sum(_len(ln.points) for ln in lines(rs.pieces[i], "fold", "hem")) * rs.pieces[i].quantity for i in fids)
        el = [w for w in rs.webbing if w["id"] == "F-EL"]
        # BL-040 m-6: one elastic length per channel (the F-EL total split in proportion to each channel's hem)
        chans = []
        for i in fids:
            pc = rs.pieces[i]
            for ln in lines(pc, "fold", "hem"):
                e_ = next((e for e in pc.edge_names if _len(pc.edge_points(e)) > 0 and
                           abs(_len(pc.edge_points(e)) - _len(ln.points)) < 0.5), "hem")
                chans.append((i, e_, _len(ln.points), pc.quantity))
        ratio = (el[0]["length_mm"] / hem) if (el and hem) else 0.0
        ch_txt = "; ".join(f"{i} {e_} hem {Lc:.0f} mm: elastic {ratio * Lc:.0f} mm" + (f" (x{q}, one per side)" if q > 1 else "")
                           for i, e_, Lc, q in chans)
        op("F-01 fly: elastic channel hems", f"Turn the hems 20 mm on the drawn hem lines ({hem:.0f} mm of hem). Cut "
           f"one length of 6 mm elastic (F-EL) per channel: {ch_txt} (total {el[0]['length_mm'] if el else 0:.0f} mm). "
           "Thread each with a safety pin, bar-tack both ends of the elastic inside its channel (it is NOT lapped into "
           "a loop)." if el else "elastic per the pattern.", "light", pieces=", ".join(fids) + (", F-EL" if el else ""),
           seam="EFb channel",
           length=hem, hours=rate(hem) + 4 * H["bartack"], vol="pattern: F-01")
    else:
        op("F-01 rain fly: HOLD", "F-01 is not drafted (ledger row 'F-01 rain fly' not_drafted; BL-033 drafted it, so this branch runs only if it goes missing). "
           "Re-run this script when the pattern lands; ops are generated from the F-01 pieces.", "none",
           pieces="F-01", hours=0.0, vol="pattern: F-01")

    # ---------------------------------------------------------------- 10 finish
    step("10 Finish, inspect, pack")
    op("Trim, seal, turn", "Trim thread ends to 3 mm, heat-seal webbing ends that frayed, turn the bag right side out "
       "through the door.", "none", hours=0.5)
    op("Final inspection and weigh", "QC sheet rows QC-12 to QC-20 (qc_sheet.md); weigh each kit against the PRIMARY "
       "mass targets in QC-14.", "none",
       qc="QC-12 to QC-20", hours=0.5)
    op("Pack", "README.md, Packaging section.", "none", hours=0.2)
    miss = unsequenced(rs, out)
    if miss:
        step("11 Unsequenced (pattern changed)")
        for pid in miss:
            op(f"{pid}: HOLD, not sequenced", "This piece is in the pattern but no operation uses it: the pattern "
               "changed after this generator was written. Add its operation here.", "none", pieces=pid,
               vol="pattern: ledger")
    fit = next((o for o in out if o.operation == "Fit the hardware"), None)   # BL-041 n-4: the real op number
    for o in out:
        if fit is not None and "@FIT" in o.notes:
            o.notes = o.notes.replace("@FIT", fit.seq)
    return out


def _tokens(txt: str) -> set:
    import re
    return {t for t in re.split(r"[\s,;+/()]+", txt or "") if t}


def unsequenced(rs, oplist) -> list[str]:
    """Pieces and webbing ids no operation names (the 'cut all' op does not count)."""
    used = set()
    for o in oplist:
        if o.pieces in ("all", "webbing", "hardware"):
            continue
        used |= _tokens(o.pieces) | _tokens(o.operation.split(":")[0])
    ids = set(rs.pieces) | {w["id"] for w in rs.webbing}
    return sorted(i for i in ids if i not in used)


# ============================================================================ QC, tests, defects, packaging
def qc_points(ctx: Ctx, g: dict, rows_mass: dict) -> list[dict]:
    q = [
        ("QC-01", "Print", "Test square", "ruler on 00_PRINT_FIRST and on one page per print run", "100.0 +/- 1.0 mm both ways", "every print run"),
        ("QC-02", "Incoming", "Fabric weight and width", "cut 100 x 100 mm, weigh 0.01 g; tape the roll width",
         "gsm within +/- 5 % of the record; width >= usable_width_mm", "every roll"),
        ("QC-03", "Cutting", "Piece size and cut-outs", "lay the pattern on the cut piece",
         "+/- 1 mm on pieces < 300 mm, +/- 2 mm on larger; windows / slots / slits present and clean", "first piece of each lay + 1 in 10"),
        ("QC-04", "Cutting", "Notches, grain, webbing length", "visual; tape",
         "notch 6 mm (never past the seam line); grain within 2 deg of the arrow; webbing +/- 2 mm, ends sealed", "first of each + 1 in 10"),
        ("QC-05", "Sewing", "Stitch density", "count stitches over 25.4 mm", "body 8, light 10, box-X 7 SPI; +/- 1", "start of each shift / each op set-up"),
        ("QC-06", "Sewing", "Tension balance", "cut a swatch seam open", "lock mid-stack, no loops on either face", "each set-up"),
        ("QC-07", "Load points", "Box-X and bartacks", "visual against SK-1; count",
         "full rectangle + both diagonals, start / end overlap >= 10 mm, stitch count >= load table, no skipped stitch, needle hole not torn", "100 %"),
        ("QC-08", "Assembly", "Seam match", "notches at both ends of every 50 mm", "notch offset <= 2 mm; seam end mismatch <= 3 mm; allowance 12 +/- 1 mm", "100 %"),
        ("QC-09", "Assembly", "Door zip", "run both sliders 10 x end to end; look at the corners",
         "no snag, no wave > 3 mm at the R 55 corners, tape not caught, stops at the hinge band", "100 %"),
        ("QC-10", "Assembly", "B-27 ports", "pull the guy through at 45 deg; look inside",
         "20 mm lap closes flat; both ends bartacked; facing follows the crease at z 631", "100 %"),
        ("QC-11", "Hardware", "Hardware fitted", "count against the BOM; threading as SK-7",
         "every lock threaded the right way (pull test by hand), carabiners gate-in, cord lock holds", "100 %"),
        ("QC-12", "Final", "Width", "tape across the widest point, bag packed full", "<= 394 mm (15.5 in) (owner limit)", "first article + 1 in 10"),
        ("QC-13", "Final", "Volume", "fill with 10 mm foam balls / litre jug method, collar rolled 3 times",
         "owner limit 85 L +/- 3 L (82-88 L, 5200 cu in). EXPECTED on the sewn bag: 81.9-84.0 L (fine-mesh closed volume, "
         "corrie_f_body.md 13.5), so a reading of 81.9-82.0 L is the design, not a sewing fault: record it and tell the "
         "pack-designer (BL-040 m-17)", "first article"),
        ("QC-14", "Final", "Mass by kit, PRIMARY fabrics (the set you build)", "1 g scale, bag empty, kit by kit",
         f"base {rows_mass['primary_base_g']:.0f} g ({rows_mass['primary_base_g'] / 28.3495:.1f} oz), as hunted "
         f"{rows_mass['primary_as_hunted_g']:.0f} g, meat trip {rows_mass['primary_meat_trip_g']:.0f} g, each +/- "
         f"{QC14_TOL_PCT:.0f} % (= ledger on the team B basis {rows_mass['base_g']:.0f} / {rows_mass['as_hunted_g']:.0f} / "
         f"{rows_mass['meat_trip_g']:.0f} g + the primary pattern delta of each kit, costing.md). Alternate-fabric bags: "
         "the ledger values", "every bag"),
        ("QC-15", "Final", "No hook-and-loop, coil zips only", "visual", "zero hook-and-loop anywhere (owner: quiet bag)", "100 %"),
        ("QC-16", "Final", "Camo use", "visual", "camo only on B-02u, SH-07, SH-01b, FP-b, B-29f, A1-d (accents)", "100 %"),
        ("QC-17", "Final", "Thread ends, seals", "visual", "ends <= 3 mm, no open webbing ends, no burnt fabric", "100 %"),
        ("QC-18", "Final", "Labels", "visual", "ID label with rev 3 + date, size / crown kit, load-limit card (53 kg frame meat, RD-02)", "100 %"),
        ("QC-19", "Final", "Kits complete", "count", "base / as-hunted (lid, B-28 per kit, scope pod) / meat-trip (WX, B-24, liner) bags each complete", "100 %"),
        ("QC-20", "Final", "Fit on the frame", "hook to a frame or the fit jig: hinge pins, IM eyes through B-12 ports, guys through B-27",
         "every eye reaches its port without strain; door opens fully; hinge eyes on the z 60 pins with the pin centre "
         f"{P.he_band()[0]:.0f}-{P.he_band()[1]:.0f} mm above the floor seam (the HE-FIT band, already proven before cut; "
         "this confirms the batch)",
         "first article + 1 in 25"),
    ]
    return [dict(zip(("id", "stage", "check", "method", "pass", "frequency"), r)) for r in q]


RELEASE_TESTS = [   # id, why it gates this package (register row read at run time)
    ("MT-1", "every 25 mm box-X on IM1-IM3 and US1/US2"), ("MT-2", "IM free-end hooks"), ("MT-3", "IM / US cams"),
    ("PT-1", "IM3 carabiner on T3"), ("PT-2", "T3 on the 70 mm B-17 tab"), ("PT-3", "HE eye on B-18 (no binding)"),
    ("HE-FIT", "hinge eye on the z 60 pin of the printed BL-042 hinge fairlead, 1:1 dry fit before PT-3 and before cut "
               "(BL-041 X-2, BL-044 DECISION HE-ENV)"),
    ("TL-1", "B-25 38 mm sleeve + guy and crown-strap toggles on the real crown bar at 494 N (BL-041, crown_tube_guy_loop.md)"),
    ("PT-5", "guy lock + tri-glide keeper"), ("PT-6", "B-24 float link"),
    ("LL-H", "heavy 25 mm ladder lock slip at 432 N (1.5 x 288 N), dry, wet and -20 C: guys, W1-W3 and the B-28 crown "
             "straps (the B-28 slip gate since BL-031)"),
    ("SEW-F", "box-X fatigue (ASSUMPTION SEW_FAT 0.40 x box strength): IM end loops (S1), US eyes (S6), belt tabs (H1), "
              "HE hinge-eye box on the printed fairlead (BL-044, review M-3)"),
    ("T9", "loaded CG on the first article (rev C basis); its rev 3 items are the T9-R3a..d rows below (BL-038 split)"),
    ("T9-R3a", "rev 3 (a): B-27 port guys hold the S-kit top, CG at the S kit (BL-030)"),
    ("T9-R3b", "rev 3 (b): B-28 crown strap cinch force and retention"),
    ("T9-R3c", "rev 3 (c): B-28 crown strap free length per crown kit (cut = longest path + 40 mm spare + 2 grips, BL-039)"),
    ("T9-R3d", "rev 3 (d): sewn B-29 lid mass and seat"),
    ("FS-O5", "alternate fabric gate: ULTRA 200X 50 mm strip (floor / frame side)"),
]
EXTRA_GATES = [
    ("B-28 slip", f"B-28 crown strap on its heavy ladder lock: covered by LL-H at {LLH_N:.0f} N (BL-031 dropped the 20 mm "
                  "gate; 25 mm strap on ladder_lock_25mm_heavy)", "LL-H pass", "corrie_f_body.md 15.6 / 16"),
    ("PORT-1", "B-27 port mock-up: hose from above 1 min with the guy pulled at 45 deg; 100 N guy pull through the lap; "
               "gloved use of the guy ladder lock where it is sewn: on its LLT tab at B-22, INSIDE the hinge band "
               "(DECISION GUY-LOCK-IN, BL-040 M-5), reached through the open roll top",
     "no water inside; lap stays closed at 100 N; 5 of 5 gloved adjustments at B-22", "corrie_f_body.md 13.9, 13.5"),
    ("GT-1", "capstan pull: 5 kg on the guy over the packed bag's corner", "record MU_WEB_FAB (0.20-0.40 band)",
     "corrie_f_body.md 13.9"),
    ("ALT-1", "alternate set: owner sees an ULTRAGrid swatch", "owner OK in writing", "part A README section 1"),
    ("ALT-2", "alternate set: PT-3 on 200X + 50 mm strip test", ">= 36.8 N/mm (1840 N / 50 mm mean, FS-O5)",
     "part A README; register FS-O5"),
    ("ALT-3", "alternate set: weigh the 70D stock", "gsm within +/- 5 % of nylon_ripstop_70d record", "part A README"),
    ("US-BS", "US backstop: cam on 25 mm webbing with the stainless tri-glide threaded behind it; open the cam (forced "
              "slip) and load the strap to the US proof 1080 N (MT-1 basis, S5-S7 720 N x 1.5)",
     "tri-glide stops the strap within 10 mm and holds 1080 N for 1 min, 3 of 3 (ASSUMPTION US-BS)",
     "triglide_25mm record note; DECISIONS 2026-11-13"),
    ("FRAY-1", "wash-swatch fray test of the un-bound SSa2 seam (3 wash cycles, R-12)",
     "no allowance frayed past the 2nd row; else bind (ASSUMPTION NO-BIND)", "RD-17"),
]


def release_tests(ctx: Ctx) -> list[dict]:
    out = []
    for tid, why in RELEASE_TESTS:
        r = ctx.register.get(tid, {})
        out.append({"id": tid, "title": r.get("title", "(row not in register)"), "gates": why,
                    "steps": r.get("steps", ""), "pass": r.get("pass_fail", ""), "source": "test_register.csv"})
    for tid, what, pf, src in EXTRA_GATES:
        out.append({"id": tid, "title": what, "gates": "release of this package", "steps": what, "pass": pf,
                    "source": src})
    return out


DEFECTS = [   # defect, where, cause, prevention / fix, class
    ("Skipped stitches in a box-X", "load points", "needle too small / wrong point, flagging on Hypalon", "Nm 140 R, tex 135, walking foot pressure; re-sew the whole box offset 1 mm", "critical"),
    ("Box-X short (stitch count under the table)", "load points", "early stop, wrong program", "count against the load table; re-sew", "critical"),
    ("Hardware threaded backwards (ladder lock, cam)", "straps", "assembly", "QC-11 hand pull; SK-7", "critical"),
    ("Load tab on the wrong face (B-17 out, B-18 / B-22 in)", "B-01, B-02h", "face mix-up", "placement labels say INSIDE / OUTSIDE; check before sewing", "critical"),
    ("Needle-cut Hypalon / laminate (perforation line)", "B-17, B-18, B-22, B-01", "cutting point needle or SPI too high", "R point only; 8 SPI max on Hypalon", "critical"),
    ("Swell puckered or twisted in its window", "B-01", "window not notch-matched", "unpick, re-clip at the corners", "major"),
    ("B-27 port gapes (lap < 20 mm)", "B-01", "facing sewn on the wrong line", "re-sew on the drawn stitch line", "major"),
    ("Door zip waves / snakes at the corners", "door", "zip stretched while sewing", "basting tape, corner notches, ease into the corner", "major"),
    ("Seam allowance frayed past the 2nd row", "body seams", "straight-knife cut nylon", "laser / hot-knife cut or bind (FRAY-1)", "major"),
    ("Notch mismatch > 2 mm / seam end mismatch > 3 mm", "box seams, collar ring", "pieces stretched", "re-clip notch to notch, walking foot", "major"),
    ("Mesh pocket over-stretched", "FP", "mesh pulled while sewing", "baste the pleats first, sew with the mesh on top", "minor"),
    ("Thread tension loops on the underside", "any", "tension / bobbin", "QC-06 swatch at each set-up", "minor"),
    ("Burn marks / hard beads on webbing ends", "webbing", "hot knife too hot / slow", "J8 stop, steady cut", "minor"),
    ("Camo piece cut against the print direction", "B-02u, SH-*", "lay error", "ONE WAY lay rule", "minor"),
    ("Hook-and-loop or a non-coil zip fitted", "any", "substitution", "BOM check (owner: quiet bag)", "critical"),
]

PACKAGING = [
    "Bag: collar unrolled, door zipped, straps coiled inside the bag (keepers on), folded flat to about 450 x 350 mm.",
    "Base kit inside the bag: IM1-IM3, US1/US2, W1-W3 fitted; guys fitted to B-22 with the toggle end coiled.",
    "As-hunted kit bag (poly bag 1, labelled): B-29 lid with the B-28 straps for the ordered crown kit (S / M / L), "
    "scope pod.",
    "Meat-trip kit bag (poly bag 2, labelled 'MEAT TRIP KIT'): 3 WX extenders with G-hooks, 2 B-24 links with "
    "carabiners, meat liner MS.",
    "Card on top: load limits (53 kg / 116 lb frame meat in float mode, RD-02), guy rule (port guys fitted for every "
    "carry, RD-23), the strap tail rule, wash cold / line dry, no hook-and-loop.",
    "Outer: recycled poly bag 600 x 800 mm, 10 bags per carton; carton label: rev 3, door D2, crown kit, fabric set "
    "(primary / alternate), date, lot.",
]


# ============================================================================ costing
YD_STEP = 0.5 * YD / 1000.0     # ASSUMPTION SHOP-INCR: roll goods (incl. Hypalon, TPU-840D) sold in half-yard steps at
#                                 full roll width; webbing / cord / elastic in whole yards; HDPE as one 0.25 m2 sheet
WEB_STEP = YD / 1000.0
HDPE_MIN_M2 = 0.25


def prototype_buy(bom: list[BOMLine]) -> dict:
    """BL-040 M-11: what ONE bag costs to buy (prototype 1-bag marker, rounded to shop increments), next to the
    production figure (10-bag markers + waste). Hardware, thread and consumables: the production quantity, whole units."""
    rows, tot = [], 0.0
    for b in bom:
        if b.section not in ("fabric", "fabric_print", "webbing", "hardware", "thread", "consumable", "packaging"):
            continue
        uc = b.unit_cost_usd
        if b.section == "fabric":
            if b.unit == "m":
                q = math.ceil((b.proto_qty or b.qty) / YD_STEP - 1e-9) * YD_STEP
                how = f"1-bag marker {b.proto_qty:g} m -> {q / (YD / 1000):.1f} yd"
            elif b.material_id == "hdpe_sheet":
                q = max(b.proto_qty or b.qty, HDPE_MIN_M2)
                how = f"one sheet >= {HDPE_MIN_M2} m2"
            else:                                           # m2 sheet goods sold by the yard at roll width
                rw = _roll_w(b.material_id) / 1000.0
                L = math.ceil((b.proto_qty or b.qty) / rw / YD_STEP - 1e-9) * YD_STEP
                q = L * rw
                how = f"1-bag {b.proto_qty:g} m2 -> {L / (YD / 1000):.1f} yd x {rw * 1000:.0f} mm roll"
        elif b.section == "fabric_print":
            q, how = 0.0, ("NOT in the first build (DECISION CAMO-FIRST): " + FIRST_BUILD_CAMO + "; the HyperD print "
                           "yard + shipping is bought by the test kit (AB-1 / FRAY-1 specimen)")
        elif b.section == "thread":
            cone_m = THREAD_CONE_G / float(mat(b.material_id).require("mass_g_m"))
            n = max(1, math.ceil(b.qty / cone_m - 1e-9))
            q = n * cone_m
            how = f"{n} cone(s) of {THREAD_CONE_G / 28.35:.0f} oz = {cone_m:.0f} m each ({b.qty:g} m used)"
        elif b.material_id in SHOP_UNIT:
            n, unit, price, why = SHOP_UNIT[b.material_id]
            rows.append({"section": b.section, "item": b.item[:70], "material_id": b.material_id, "unit": unit,
                         "production_qty": b.qty, "production_usd": b.cost_usd, "prototype_qty": n,
                         "prototype_usd": price * n, "how": f"{n} {unit} ({why})"})
            tot += price * n
            continue
        elif b.section == "webbing":
            q = math.ceil(b.qty / WEB_STEP - 1e-9) * WEB_STEP
            how = f"{b.qty:g} m -> {q / (YD / 1000):.0f} yd"
        else:
            q, how = b.qty, "as production (whole units / cones)"
        c = round(q * uc, 2) if uc is not None else None
        tot += c or 0.0
        rows.append({"section": b.section, "item": b.item[:70], "material_id": b.material_id, "unit": b.unit,
                     "production_qty": b.qty, "production_usd": b.cost_usd, "prototype_qty": round(q, 3),
                     "prototype_usd": c, "how": how})
    return {"rows": rows, "total_usd": round(tot, 2),
            "fabric_usd": round(sum(r["prototype_usd"] or 0 for r in rows if r["section"] == "fabric"), 2),
            "assumption": "SHOP-INCR: roll goods in 0.5 yd steps at full width, webbing whole yards, HDPE one 0.25 m2 "
                          "sheet; hardware as production (whole units); thread by the 4 oz cone, basting tape and seam "
                          "sealer by the smallest pack (SHOP-UNIT, BL-041 n-10); no camo print (CAMO-FIRST, BL-041 Y-5)"}
def costing(ctx: Ctx, bom: list[BOMLine], oplist: list[SewingOp]) -> dict:
    mat_cost = sum(b.cost_usd or 0.0 for b in bom if b.section in ("fabric", "fabric_print", "webbing", "hardware",
                                                                     "thread", "consumable", "packaging"))
    missing = [b.item for b in bom if b.cost_usd is None and b.section not in ("hardware_frame_side", "fabric_alternate")]
    alt_fab = sum(b.cost_usd or 0.0 for b in bom if b.section == "fabric_alternate")
    prim_fab = sum(b.cost_usd or 0.0 for b in bom if b.section == "fabric")
    proto_h = sum(o.proto_h for o in oplist)
    by_step: dict = {}
    for o in oplist:
        by_step[o.step] = by_step.get(o.step, 0.0) + o.proto_h
    sam_min = sum(o.time_s for o in oplist) / 60.0
    lab = {k: sam_min * v for k, v in LABOUR.items()}
    cmt = {k: v * (1 + OVERHEAD) for k, v in lab.items()}
    pb = prototype_buy(bom)
    return {"material_usd_primary": round(mat_cost, 2),
            "prototype_buy": pb, "prototype_usd": pb["total_usd"],
            "material_usd_alternate": round(mat_cost - prim_fab + alt_fab, 2),
            "fabric_usd_primary": round(prim_fab, 2), "fabric_usd_alternate": round(alt_fab, 2),
            "missing_cost": missing, "proto_hours": round(proto_h, 1),
            "proto_hours_by_step": {k: round(v, 2) for k, v in by_step.items()},
            "sam_min": round(sam_min, 1), "labour_usd": {k: round(v, 2) for k, v in lab.items()},
            "cmt_usd": {k: round(v, 2) for k, v in cmt.items()},
            "landed_usd": {k: round(v + mat_cost, 2) for k, v in cmt.items()},
            "lid_hours_drafted": ctx.lid["hours"], "lid_hours_booked": ctx.lid["bl029_booked_h"],
            "assumptions": [f"SAM-RATIO {FACTORY_RATIO}", f"LABOUR {LABOUR}", f"OVERHEAD {OVERHEAD}", "THREAD-FACTOR 2.75",
                            "WEB_WASTE 5 %", "prices with no record: PRICE_ASSUMED"]}


def ledger_mass(ctx: Ctx) -> dict:
    rows = P.ledger_rows()
    base = sum(r["g"] for r in rows if r["cfg"] == "base")
    hunted = base + sum(r["g"] for r in rows if r["cfg"] == "as_hunted")
    meat = hunted + sum(r["g"] for r in rows if r["cfg"] == "meat_trip")
    mc = P.mass_check(ctx.rsA, rows)
    # primary fabric mass from the same pattern areas (today's fabrics)
    prim = sum(P.pattern_mass_g(ctx.rs.pieces[i]) for o in mc["rows"] for i in o["pieces"])
    # BL-040 M-6: the ledger is on the team B (alternate) fabrics; the owner builds the PRIMARY set. Primary target per
    # kit = ledger + (primary - alternate) pattern mass of that kit's cut pieces (webbing is the same in both sets)
    kit_cfg = {"base": "base", "as_hunted": "as_hunted", "addon": "as_hunted", "meat_trip": "meat_trip"}
    dk = {"base": 0.0, "as_hunted": 0.0, "meat_trip": 0.0}
    for pid, pa in ctx.rs.pieces.items():
        if pa.material_id in P.WEBBING or pid not in ctx.rsA.pieces:
            continue
        dk[kit_cfg[ctx.rs.meta[pid]["kit"]]] += P.pattern_mass_g(pa) - P.pattern_mass_g(ctx.rsA.pieces[pid])
    pb = base + dk["base"]
    ph = hunted + dk["base"] + dk["as_hunted"]
    pm_ = meat + sum(dk.values())
    return {"base_g": round(base, 1), "as_hunted_g": round(hunted, 1), "meat_trip_g": round(meat, 1),
            "pattern_fabric_alt_g": mc["pattern_g"], "ledger_fabric_g": mc["ledger_g"], "mass_delta_pct": mc["delta_pct"],
            "mass_ok": mc["ok"], "pattern_fabric_primary_g": round(prim, 1),
            "primary_minus_alt_g": round(prim - mc["pattern_g"], 1),
            "primary_delta_by_kit_g": {k: round(v, 1) for k, v in dk.items()},
            "primary_base_g": round(pb, 1), "primary_as_hunted_g": round(ph, 1), "primary_meat_trip_g": round(pm_, 1),
            "qc14_tol_pct": QC14_TOL_PCT}


# ============================================================================ delta register close-out
def delta_closeout(ctx: Ctx, bom: list[BOMLine], lpts: list[dict]) -> list[dict]:
    ids = set(ctx.rs.pieces) | {w["id"] for w in ctx.rs.webbing}
    items = " ".join(b.item for b in bom)
    im1 = [w for w in ctx.rs.webbing if w["id"] == "IM1"][0]["length_mm"]

    def has(*xs):
        return all(x in ids for x in xs)

    R = []

    def add(rd, status, evidence, remains):
        R.append({"id": rd, "status_after_rev3_package": status, "evidence": evidence, "still_open": remains})

    add("RD-01", "closed" if "F-03" not in ids else "open", f"F-03 in the rev 3 piece list: {'F-03' in ids}",
        "nothing (v3.1 set stays superseded with its STOP notice)")
    add("RD-02", "restated", f"B-24 x2 + 2 carabiners in the meat-trip kit BOM: {has('B-24') and 'B-24 float links' in items}; "
        "PT-6 in the release gates", "user guide (RD-22) with the 53 kg limit and belly rule; PT-6")
    add("RD-03", "closed" if abs(im1 - 990.0) < 1.0 else "restated", f"IM1 cut {im1:.0f} mm in the rev 3 cut list",
        "MT-1 / MT-2 on the sewn straps")
    add("RD-12", "restated", f"B-17, B-18, B-22, HE, T3, LLT, TG drafted and sequenced: {has('B-17', 'B-18', 'B-22', 'HE', 'T3', 'LLT', 'TG')}; "
        "B-19 / B-20 / B-23 / T2 removed (BL-004 REC); IM3 hooks are wiregate carabiners (BL-010)",
        "PT-1, PT-2, PT-3, PT-5, PT-6, LL-H before any load point is sewn on a bag that will carry")
    add("RD-15", "closed (numbers)", "BOM, yardage and mass use the current records (robic 125 gsm, ultragrid 132 gsm "
        "1500 mm roll, ULTRA 133 gsm)", "physical: swatch weights (QC-02), FS-O5 / PT-3 on 200X (alternate gate)")
    add("RD-16", "closed (release)", "CORRIE F rev 3 patterns (part A) + this op sequence replace SPINE step 9",
        "first article build; CORRIE gates; pattern-read ops listed as volatile ops")
    add("RD-17", "restated", f"IMP-2 / IMP-4 / IMP-8 in the bag: {has('B-09c', 'IMP4-a', 'IMP8-a')}; SH-03 absent: "
        f"{'SH-03' not in ids}; body seams un-bound (SSa2, ASSUMPTION NO-BIND)",
        "FRAY-1 wash-swatch test; IMP-1/3/5/6 belong to the harness / belt packages")
    b11 = ctx.rs.geo.get("b11") or {}
    add("RD-18", "closed", f"B-11 x8 + BRL x2 + BRS + G-hook in the BOM: {has('B-11', 'BRL', 'BRS')}; B-11 placements "
        f"drawn on B-03: {2 * b11.get('per_gusset', 0)} tabs (op 4.07 released)",
        "archery / rifle loadout fit settles ASSUMPTION B11-PLACE")
    bp = ROOT / "designs" / "pack_5200" / "BUILD_PLAN.md"
    ptr = bp.exists() and "outputs/release/pack5200_corrie_f_rev3/" in bp.read_text()
    add("RD-21", "closed (pointer)" if ptr else "restated",
        f"this op sequence supersedes BUILD_PLAN.md step 9 for the bag; BUILD_PLAN.md points at the rev 3 release: {ptr}",
        "BUILD_PLAN.md body still describes the SPINE bag (its banner says so)" if ptr else
        "BUILD_PLAN.md needs a pointer to this package")
    add("RD-22", "open", "the packaging card (README Packaging) carries the load limits", "the user guide itself")
    add("RD-23", "restated", f"B-25, B-27f, B-22 inside, TG, LLT drafted and sequenced (ops 3.04-3.05, 4.03): "
        f"{has('B-25', 'B-27f', 'B-22', 'TG', 'LLT')}", "T9 rev 3 at the S kit; LL-H; PORT-1; attorney review; B-22 placed at "
        f"x +/-{ctx.rs.geo['b22']['placed_x']:.1f} vs drawn {ctx.rs.geo['b22']['drawn_x']:.0f} (ASSUMPTION B22-IN)")
    eff = _build_effort()
    add("RD-24", "restated", f"B-29 (7 piece types) + B-28 per kit + keepers sequenced; lid {ctx.lid['hours']} h on the "
        "drafted pattern; build_metrics books the op-sequence hours (build_effort_rev3.json: "
        f"{eff.get('hours_per_bag_total', '-')} h a bag)", "T9 lid weigh / photo, cinch, free lengths")
    return R


def _build_effort() -> dict:
    f = ROOT / "designs" / "pack_5200" / "analysis" / "build_effort_rev3.json"
    return json.loads(f.read_text()) if f.exists() else {}


def _b28_front(rs) -> str | None:
    """The B-28 tab piece that is boxed through the hinge band (its webbing use names the front tab)."""
    tabs = sorted(i for i in rs.pieces if i.startswith("B-28") and i != "B-28")
    use = {w["id"]: w["use"] for w in rs.webbing}
    for word in ("front", "lock"):                       # BL-035 renamed the uses: 'lock tab' / 'toggle loop'
        hit = next((i for i in tabs if word in use.get(i, "")), None)
        if hit:
            return hit
    band = {(w, h) for w, h, lab in boxes_of(rs.pieces["B-02h"]) if "B-28" in lab}
    return next((i for i in tabs if band & {(w, h) for w, h, _ in boxes_of(rs.pieces[i])}), tabs[0] if tabs else None)


# BL-040 B-1: every webbing piece that is box-X'd through a panel, and every panel in that stack, carry the same box.
# (panel id, label key on the panel, webbing id, label key on the webbing piece or None = all its boxes)
BOX_STACKS = [
    ("B-01", "HE hinge eye", "HE", "box-X"), ("B-18", "HE eye", "HE", "box-X"),
    ("B-17", "T3 tongue", "T3", "B-17"),
    ("B-22", "ladder-lock tab", "LLT", None), ("B-02h", "LLT", "LLT", None),
    ("B-02h", "B-28", "@B28", None),
    ("B-03", "RTM", "RTM", None), ("B-07", "RT strap", "RT", None),
]


def box_mismatches(ctx: Ctx) -> list[str]:
    """Box-X marks that disagree between a panel and the webbing piece sewn through it (pattern consistency). Sizes are
    compared without regard to orientation (a strap laid along a hem draws its box rotated). A stack whose panel or
    webbing draws no box at all is reported too (BL-034 compared only B-02h)."""
    rs, out = ctx.rs, []
    for panel, pkey, wid, wkey in BOX_STACKS:
        wid = _b28_front(rs) if wid == "@B28" else wid
        if wid is None or panel not in rs.pieces or wid not in rs.pieces:      # BL-041 n-12: a missing piece is an error
            out.append(f"stack {panel} / {wid or 'B-28 front tab'}: piece MISSING")
            continue
        a = sorted({tuple(sorted((w, h))) for w, h, lab in boxes_of(rs.pieces[panel]) if pkey in lab})
        b = sorted({tuple(sorted((w, h))) for w, h, lab in boxes_of(rs.pieces[wid]) if wkey is None or wkey in lab})
        if not a or not b:
            out.append(f"{panel} '{pkey}' box {a or 'NOT DRAWN'} vs {wid} box {b or 'NOT DRAWN'}")
        elif not set(a) & set(b):
            out.append(f"{panel} '{pkey}' box {a} vs {wid} box {b}")
    return out + box_positions(ctx)


def _box_centres(p, key):
    out = []
    for ln in p.internal_lines:
        lab = ln.label or ""
        if ln.kind == "stitch" and ln.closed and key in lab and "box-X" in lab:
            xs, ys = [q[0] for q in ln.points], [q[1] for q in ln.points]
            out.append((0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys))))
    return out


def box_positions(ctx: Ctx, tol: float = 1.0) -> list[str]:
    """BL-041 n-12: box CENTRES against the placement they belong to (+/- tol mm), not only sizes. HE: the box height
    above the floor seam line on B-18, on the HE strip (both legs) and on B-01 (via the B-01 flat map); RTM: the box on
    B-03 inside the drawn RTM rectangle at the tab rule offset under the bar."""
    rs, out = ctx.rs, []
    hg = rs.geo["he"]
    zc = hg["box_z_above_seam"][0] + hg["box"][1] / 2.0           # above the floor seam line
    want = {"B-18": [(P.B18_W / 2, P.B18_BELOW + zc)],
            "HE": [(P.HE_W / 2, P.B18_BELOW + zc), (P.HE_W / 2, hg["cut"] - P.B18_BELOW - zc)]}
    s01 = P.F.b01_flat_s()
    want["B-01"] = [(sx * P.STAY_X, s01(P.BC.Z0 + zc)) for sx in (-1, 1)]
    keys = {"B-18": "HE eye", "HE": "", "B-01": "HE hinge eye"}
    for pid, pts in want.items():
        got = _box_centres(rs.pieces[pid], keys[pid])
        for w in pts:
            if not got or min(math.hypot(g[0] - w[0], g[1] - w[1]) for g in got) > tol:
                out.append(f"{pid} HE box centre not at {w[0]:.1f}, {w[1]:.1f} (+/-{tol:g} mm): {got}")
    r = rs.geo["rtm"]
    w = (r["x"], r["y_bar"] - (P.RTM_CUT * 0.75 - P.RTM_FOLD))
    got = _box_centres(rs.pieces["B-03"], "RTM buckle tab")
    if not got or min(math.hypot(g[0] - w[0], g[1] - w[1]) for g in got) > tol:
        out.append(f"B-03 RTM box centre not at {w[0]:.1f}, {w[1]:.1f}: {got}")
    return out


# ============================================================================ build everything (no files)
def package(ctx: Ctx | None = None) -> dict:
    ctx = ctx or build_ctx()
    g = geo(ctx)
    oplist = ops(ctx)
    bom = (fabric_bom(ctx) + camo_bom(ctx) + webbing_bom(ctx) + hardware_bom(ctx) + thread_bom(oplist, ledger_thread_g())
           + consumables_bom(g))
    for b in bom:                                   # BL-040: every coloured line names the colorways.yaml standard
        cn = colour_note(b.section, b.material_id)
        if cn:
            b.notes = (b.notes + "; " if b.notes else "") + cn
    lpts = load_points(ctx)
    lm = ledger_mass(ctx)
    return {"ctx": ctx, "geo": g, "ops": oplist, "bom": bom, "load_points": lpts, "cutting": cutting_plan(ctx),
            "qc": qc_points(ctx, g, lm), "tests": release_tests(ctx), "mass": lm,
            "costing": costing(ctx, bom, oplist), "delta": delta_closeout(ctx, bom, lpts),
            "volatile": sorted({o.volatile for o in oplist if o.volatile} | {r["volatile"] for r in lpts if r["volatile"]})}


def checks(pk: dict) -> dict:
    ctx = pk["ctx"]
    rec = ctx.rec
    lp = pk["load_points"]
    rated = [r for r in lp if r["sf"] is not None]
    return {"recon_unmatched": len(rec["unmatched_rows"]), "recon_pieces_without_row": len(rec["pieces_without_row"]),
            "recon_rows": len(rec["rows"]), "mass_delta_pct": pk["mass"]["mass_delta_pct"], "mass_ok": pk["mass"]["mass_ok"],
            "ops": len(pk["ops"]), "load_points": len(lp), "min_sf": min(r["sf"] for r in rated),
            "min_sf_point": min(rated, key=lambda r: r["sf"])["point"],
            "holds": [o.seq + " " + o.operation for o in pk["ops"] if "HOLD" in o.operation or "HOLD" in o.notes],
            "unsequenced": unsequenced(ctx.rs, pk["ops"]), "unmapped_hardware": unmapped_hardware_rows(ctx),
            "hardware_rows_by_keyword": keyword_mapped_rows(ctx), "box_mismatches": box_mismatches(ctx),
            "thread_bag_g": round(thread_bag_g(pk["ops"]), 2), "thread_ledger_g": round(ledger_thread_g(), 2),
            "proto_hours": pk["costing"]["proto_hours"], "sam_min": pk["costing"]["sam_min"],
            "volatile": pk["volatile"]}


# ============================================================================ assumptions that govern (id, text, settled by)
ASSUMPTIONS = [
    ("NO-BIND", "Body seams are SSa2 (second row over the turned allowances), not bound: the ledger books no binding "
                "(RD-17 B-1).", "FRAY-1 wash-swatch test (3 cycles); if it fails, bind with 20 mm grosgrain via a binder"),
    ("NO-TAPE", "No taped seams: the bag is water resistant, contents in the user's dry bag.", "owner decision if a "
                "waterproof bag is wanted (seam-tape machine + taped ULTRA seams)"),
    ("SAM-RATIO", f"Factory SAM = {FACTORY_RATIO:.2f} x beginner hours (bag_concepts.HOURS basis).",
     "time study on the first 10-bag lot"),
    ("LABOUR", f"Loaded CMT minute: US contract ${LABOUR['us_contract_usd_min']}/min, Asia ${LABOUR['asia_contract_usd_min']}/min; "
               f"overhead + margin {OVERHEAD:.0%}.", "two contract quotes from this tech pack"),
    ("THREAD-FACTOR", f"{THREAD_FACTOR} m of thread per m of 301 stitching (both threads, ends).", "weigh the cones before / after the first bag"),
    ("SPI-LIGHT", "10 SPI on 40D-100D and mesh.", "QC-05/06 swatch: no puckering, no perforation"),
    ("THREAD-NEEDLE", "Tex 70 / Nm 90, tex 90 / Nm 110, tex 135 / Nm 140, round point (attach_system.NEEDLE for 90 / 135).",
     "swatches in op 0.02: no skipped stitches, no shredding"),
    ("UTIL-SMALL", f"Small and sheet pieces nest at {UTIL_SMALL:.0%} across bags in production.", "first production markers"),
    ("UTIL-ALT", f"Alternate-set body fabrics nest at {UTIL_ALT_LARGE:.0%} in production (no 10-bag alternate marker).",
     "alternate 10-bag markers if the alternate set passes its gates"),
    ("B11-PLACE / KW-PATH / F02-CENTRE / US-EYE", "Pattern placements read by this package (patterns_corrie_f_rev3, BL-034 "
     "part A): B-11 tab heights, K-W keeper heights from the W path, F-02 fore-aft on B-05, the US eye fold.",
     "archery / rifle loadout fits; T9 W free lengths (keeper within +/-15 mm of the wrap); fly fit; MT-1 specimens"),
    ("WX-LOAD", "Haul extenders carry the S9 float-clamp load (225 N).", "pack-designer load case; LL-H"),
    ("US-BS", "The stainless 25 mm tri-glide behind each US cam stops cradle slip (record: 3.75 kN break, no slip rating).",
     "gate US-BS: cam slipped on purpose, backstop holds"),
    ("TG-SS-PRICE", f"Stainless tri-glide USD {TG_SS_USD} from the record's EUR source line, converted as the record does "
                    "(ex VAT x 1.09 USD/EUR).", "supplier quote"),
    ("BT-STD", "Slit-end bartack 10 x 2 mm, 28 stitches; standard tack 16 x 2 mm, 42 stitches (LK-1900 patterns).", "QC-07"),
    ("HE-ONE / HE-PIN / HE-ENV / HE-GAP / HE-CHEEK / HE-T / HE-PIN-HI", f"BL-040 B-1 + BL-041 X-1 / X-2 + BL-044 Z-1 / "
     f"M-3 / m-1: one hinge-eye construction (HE {P.HE_CUT:.0f} mm folded in half, both raw ends and the B-18 edge in the "
     f"floor seam, B-18 rows sewn first through B-18 + B-01 only); eye UP on the z 60 pin of the BL-042 hinge fairlead "
     f"(bag_attach.HINGE_EYE_ENVELOPE: pin 10.1 mm above the stay, 5.5 mm under it, 20 mm throat); box-X "
     f"{P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f} at +{P.HE_BOX_GAP:.0f}..+{P.HE_BOX_GAP + P.HE_BOX[1]:.0f} mm, "
     f"{P.HE_CHEEK_CLEAR:.0f} mm under the cheeks at the design pin and >= {P.HE_CHEEK_MIN:.0f} mm over the HE-FIT band; "
     f"eye {P.HE_EYE} mm solved on the real 3-ply neck wrap for webbing {P.HE_T} mm (bracket "
     f"{P.HE_T_RANGE[0]}-{P.HE_T_RANGE[1]} mm, thicker rejected). The box PEELS (leg B 23-50 deg off the box line): "
     "rated by PT-3 on the printed fairlead and SEW-F HE specimens.",
     f"caliper gate on the roll (ply <= {P.HE_T_RANGE[1]} mm); HE-FIT on the BL-042 test piece (pin "
     f"{P.he_band()[0]:.0f}-{P.he_band()[1]:.0f} mm above the seam line, box >= {P.HE_CHEEK_MIN:.0f} mm under the cheeks), "
     "then PT-3 and SEW-F HE on specimens sewn as op 4.05 / SK-8"),
    ("RT-MATE / RT-HEM / RT-FWD / RT-ORIGIN / W3-OVER / HOSE-LOW / BUCKLE-ENV / MK-GAP", "BL-040 B-2 + BL-041 Y-2 + "
     "BL-043 M-1 / M-2 / m-9: the RT strap is sewn at the roll end (gusset centre of the hem); its buckle's female half "
     "on an RTM tab forward on the gusset (hose slot + 10 mm + half a buckle), the buckle body 10 mm under the lowest W3 "
     "edge of every crown kit (W3 rides at the crown-bar height, z 601-804); W3 is the outer layer (slacken it to open "
     "the top); the hose slot also sits under W3's sweep; muzzle tabs 10 mm clear of the strap's line to the roll end; "
     "buckle envelope 35 x 35; RT cut from the cloth-pass roll model re-run with this tab and origin.",
     "FIT-R3 rows 5-7 (rifle + roll clip + W3, at both ends of the owner's crown kit); T9 roll-clip free length; "
     "hydration fit (HOSE-LOW); caliper on the buckle"),
    ("IM-CAM-TAB / IMC-LOOP", "BL-041 m-19: each IM cam sewn to an IMC dog-bone (21 x 25 box-X each end, 18 mm loops) "
     "carrying the G-hook / carabiner.", "MT-1 (2 IMC tabs at 908 N); threading the bought cam and hook"),
    ("B25-TAB-CENTRE / WIDE_SLEEVE", "BL-041 (crown_tube_guy_loop.md): B-25 in 38 mm webbing, sleeves x 26.5-64.5, "
     "toggle tab at the sleeve centre x 45.5; the 25 mm tab pull spreads over the 38 mm sleeve.",
     "TL-1 at 494 N on real bar stock, specimen WITH the mitre turn and run (BL-043)"),
    ("B25-TOPO / CLAMP (BL-045)", "BL-043 M-4: B-25 = tab | sleeve | 45 deg mitre under the sleeve | run necked to "
     "25 mm | one wrap round the spine under the clamp. BL-044: on the BL-045 sized clamp (half 12.0 along the bar, "
     "collar 12.8) and the measured pawl housing (15.62 up, +/-24.82); the run reaches the printed spine 15.85 mm fore "
     "of the bar (+34.1 mm cut). Was ASSUMED (B25-CLAMP / PAWL-TOP / SPINE_CLAMP_HALF).",
     "BL-045 clamp T6 coupon (CLAMP-TYPE); op 7.17 gate B25-FIT at kit S 15 in; TL-1 specimen"),
    ("GUY-LOCK-IN", "BL-040 M-5: the guy ladder lock stays on its LLT tab at B-22 inside the hinge band; the guy length is "
     "set with the roll top open (per crown kit / load), not on the move.", "PORT-1 gloved adjustment at B-22"),
    ("KW-OVER-FP", "BL-040 B-3: haul wraps W1 / W2 cross the FP hip pockets, over the mesh (keeper loop on top).",
     "T9 W free lengths; first loaded haul: pocket still reachable with the wraps cinched (owner)"),
    ("SHOP-INCR", "Prototype buy: roll goods in 0.5 yd steps at full width, webbing whole yards, HDPE one 0.25 m2 sheet.",
     "the owner's actual order"),
    ("PRICES", "Items with no material record use PRICE_ASSUMED (TPU hook sleeve, rubber pull sleeve, basting tape, seam "
               "sealer, labels, packaging). Hardware and elastic use their records since BL-034.",
     "supplier quotes"),
]

JIGS = [
    ("J1", "Box-X templates, clear acrylic 2 mm, one per box size in the load table (section 7 / SK-1), slots for chalk on "
           "the rectangle and both diagonals; production: LK-1900 / AMS-210EN programs of the same paths"),
    ("J2", "Swell window corner template + clip board (8 swells, notch to notch)"),
    ("J3", "B-27 port gauge: 6 mm turn, 20 mm lap, facing line; a slotted ruler"),
    ("J4", "Webbing fold gauge: aluminium angle with stops at 15 / 30 / 45 / 50 / 60 / 100 mm"),
    ("J5", "LK-1900 / AMS-210EN work clamps for 25 and 38 mm webbing stacks (Hypalon + panel)"),
    ("J6", "Door zip board: B-02door + B-02u laid flat with the corner-tangent notches pinned to the board"),
    ("J7", "Lid dart template (B-29a, 4 darts, apex drill marks)"),
    ("J8", "Hot-knife length fence with a scale in mm and in (cut lengths in cutting_plan.csv)"),
]


# ============================================================================ BL-040 review status
# design-reviewer pre-cut review (analysis/review_20261113_rev3_release.md): id, class, status, how
REVIEW_STATUS = [
    ("B-1", "blocker", "fixed", "DECISION HE-ONE: one hinge eye on HE / B-18 / B-01 / op 4.05 / load table / PT-3; SK-8; box_mismatches covers every stack"),
    ("B-2", "blocker", "fixed", "RTM buckle tabs on both gussets (op 4.08) + RT strap placements on the flat hem (op 5.02); SK-10; load rows (unrated)"),
    ("B-3", "blocker", "fixed", "op 4.13 states the keeper / mesh stack; SK-9; FP aft edge basted only; W1/W2 over FP confirmed"),
    ("M-1", "major", "fixed", "B-26: one end in op 4.12, the free end caught in op 4.13"),
    ("M-2", "major", "fixed", "B-17 box 34 x 34"),
    ("M-3", "major", "fixed", "collar ring one way round; one notch set on the gusset (test)"),
    ("M-4", "major", "fixed", "B-22 label: INSIDE B-02h, x placed, z 695, coated face to the band"),
    ("M-5", "major", "fixed", "DECISION GUY-LOCK-IN: lock at B-22 inside; corrie_f_body 13.5 and PORT-1 updated"),
    ("M-6", "major", "fixed", "QC-14 on the primary fabrics per kit; costing.md + README publish them"),
    ("M-7", "major", "fixed", "LL-H 432 N; load_points.csv hardware columns"),
    ("M-8", "major", "fixed", "MT-3 and LL-H dry / wet / cold"),
    ("M-9", "major", "fixed", "SEW-F in the kit (G4 lever rig)"),
    ("M-10", "major", "fixed", "camo/ referenced; BOM fabric_print line from camo/bom_print_line_proposed.csv; sublimation caveat"),
    ("M-11", "major", "fixed", "prototype buy vs production in costing.md / README"),
    ("M-12", "major", "fixed", "minimum prototype machine stated (README, tech pack section 2, BUILD_PLAN pointer)"),
    ("M-13", "major", "fixed", "op 1.01 bastes the bottom only"),
    ("m-1", "minor", "fixed", "already three-way max since BL-039 (test + README)"),
    ("m-2", "minor", "fixed", "hinge 1019 N"), ("m-3", "minor", "fixed", "B-17 perimeter SF labelled pending PT-2"),
    ("m-4", "minor", "fixed", "B-09p slot drawn"), ("m-5", "minor", "accepted",
     "IMP-4 / F-02 zip-construction sketch not drawn this ticket: pockets are sewn first on cheap fabric and do not gate any load or other step; next pattern ticket"),
    ("m-6", "minor", "fixed", "fly elastic per channel, lap text removed"), ("m-7", "minor", "fixed", "swell slot is a mark; cut through the B-12 slot"),
    ("m-8", "minor", "fixed", "lid presets / cap turn / seam label"), ("m-9", "minor", "fixed", "QC-12..QC-20"),
    ("m-10", "minor", "fixed", "seam-inserted loops folded in step 2"), ("m-11", "minor", "fixed", "B-11 slot 27 x 5"),
    ("m-12", "minor", "fixed", "left-gusset B-11: light lash only, no load rating"), ("m-13", "minor", "fixed", "seam table pipes escaped"),
    ("m-14", "minor", "fixed", "piece-type split; cut-list hardware = BOM quantities"),
    ("m-15", "minor", "fixed", "B-24 label, SK-3 caption"),
    ("m-16", "minor", "accepted", "test square placement is in the shared huntkit/patterns/export_pdf (pattern-maker); it already picks a free corner when one exists"),
    ("m-17", "minor", "fixed", "QC-13 records the expected 81.9-84.0 L"), ("m-18", "minor", "fixed", "FIT-R3 in G7"),
    ("m-19", "minor", "fixed", "BL-041 (re-check n-15): IMC cam anchor tab + SK-11 per strap"),
    ("m-20", "minor", "fixed", "op 3.08 turns the allowances away from B-22"), ("m-21", "minor", "fixed", "previews 110 dpi"),
]


# BL-041: design-reviewer RE-CHECK (analysis/review_20261113_rev3_recheck.md): id, class, status, how
RECHECK_STATUS = [
    ("X-1", "blocker", "fixed", "op 4.05 reordered: NECK, B-18 ROWS (through B-18 + B-01 only), PLACE HE, BOX, BASTE; "
     "test: no B-18 / B-01 stitch line crosses the eye footprint and the rows precede the HE in the op text; PT-3 specimen built from the same order"),
    ("X-2", "blocker", "fixed", "DECISION HE-PIN: eye UP on the z 60 pin, box-X 34 x 10 at +4..+14 (2 mm under the cheeks), "
     "eye 17 mm solved by he_geometry, HE 86 mm; loaded pin +23.4..+25.3 over the B-01 / webbing bracket (target 25 +/- 3, test); "
     "HE-FIT dry fit is a BAG-CUT gate before PT-3; SK-8 redrawn with the rows and the real pin [superseded by BL-044 "
     "DECISION HE-ENV: box 34 x 7 at +4..+11, eye 25 mm, HE 96 mm on the BL-042 fairlead]"),
    ("Y-1", "major", "fixed", "[BL-044: the rig is now the printed BL-042 fairlead with a spacer, see M-3] PT-3 rig: pin in an 18 mm slot fixture, B-05 strip alone in the clamp, B-01 top free, pull "
     "down B-01; specimen = reordered op 4.05 with the B-18 rows and the baste"),
    ("Y-2", "major", "fixed", "DECISION RT-FWD: clip path on the gusset at 10.9 mm from the hose slot, buckle bar 10 mm "
     "over the B-26 cord, muzzle tabs aft (111 / 171 mm, 60 apart); min clearance 10.0 mm over tabs, keeper cord, hose "
     "slot, bow tabs, B-26 cord (test on the buckle envelope + strap corridor); W3 through a W3G guide under the RT "
     "strap (DECISION RT-OVER-W3); FIT-R3 rows 5-6"),
    ("Y-3", "major", "fixed", "machine minimum adds a 304 zigzag; BT-301 straight-stitch fallback, unrated (every 304 tack "
     "in the release is unrated); BUILD_PLAN 140/22 and tex 70 / 90 / 135"),
    ("Y-4", "major", "fixed", "structural result adopted (crown_tube_guy_loop.md): B-25 in 38 mm, sleeves x 26.5-64.5, "
     "load row 323 N, bar wall SF 1.36 / 1.27 fatigue; TL-1 at 494 N on real bar stock with both toggles, TL-1b data "
     "test; GBL deleted; ledger booked"),
    ("Y-5", "major", "fixed", "DECISION CAMO-FIRST: first build solid 630D on the camo pieces (README, BOM print line "
     "production-only, prototype buy without the print); HyperD yard + shipping in the test kit only"),
    ("n-1", "minor", "fixed", "IM3-EC text says 'R about 0.02' (24 / 1178 = 0.0204, the countersign's F_min kept)"),
    ("n-2", "minor", "fixed", "CA-1 retitled 0.40 (fallback >= 0.313); table cut at 115 %, above: stop, structural re-run"),
    ("n-3", "minor", "fixed", "LL-H / MT-3 COLD is its own step; -18 C freezer accepted as the record's -20 C (ASSUMPTION FREEZER)"),
    ("n-4", "minor", "fixed", "op 7.end replaced by the real op number of 'Fit the hardware'"),
    ("n-5", "minor", "fixed", "SK-10 (b) axis 'sigma (mm along the gusset)', callout moved; SK-1 columns re-laid"),
    ("n-6", "minor", "fixed", "B-18 / B-22 notes wrapped inside the pieces on the printed tiles (export)"),
    ("n-7", "minor", "fixed", "1:1 webbing-marks page added to step 2 (HE, RTM, W3G, IMC, T3, LLT, US)"),
    ("n-8", "minor", "fixed", "TG toggle end: POM toggle hardware; GBL row gone (deleted); README lowest SF notes PENDING PT-2"),
    ("n-9", "minor", "fixed", "BUILD_PLAN thread list tex 70 / 90 / 135, needles 140/22"),
    ("n-10", "minor", "fixed", "one-off buy: thread by the 4 oz cone, sealer and tape by the pack; print shipping in the test kit"),
    ("n-11", "minor", "fixed", "bag_attachment.md HE / B-18 rows marked superseded by HE-ONE / HE-PIN"),
    ("n-12", "minor", "fixed", "tautology removed; a missing stack piece is an error; HE and RTM box centres checked to +/-1 mm"),
    ("n-13", "minor", "fixed", "SEW-F peak 1.15 x 384 = 442 N"),
    ("n-14", "minor", "fixed", "op 4.15: hinge-eye spans with the zipper / edge foot; PT-3 floor seams the same"),
    ("n-15", "minor", "fixed", "DECISION IM-CAM-TAB: IMC dog-bone sews each cam to its hook / carabiner; SK-11 per strap; load row; MT-1 specimens"),
]


# BL-043: design-reviewer THIRD review (analysis/review_20261113_rev3_third.md): id, class, status, how. The hinge-eye
# items wait for BL-042 (frame print files, hinge fairlead) and BL-044 (HE redesign on BL-042's envelope).
THIRD_STATUS = [
    ("Z-1", "blocker", "fixed", "BL-042 hinge fairlead (5.5 mm under the pin, 20 mm throat) + BL-044 DECISION HE-ENV: "
     "the eye is solved on the real 3-ply neck wrap against bag_attach.HINGE_EYE_ENVELOPE and checked by slicing the "
     "HE-FIT test-piece STL at every bracket corner (he_stl_check: no overlap, gap and throat clearances); the test at "
     "test_bl041:55 (neck == throat) is replaced by a clearance test; SK-8 (c) redrawn on the envelope"),
    ("Z-2", "blocker", "fixed", "BL-042: H1 print files carry the whole fairleads (12 / 12 pass the STL slice check); "
     "HE-FIT and IM3-EC print the BL-042 test pieces"),
    ("M-1", "major", "fixed", "DECISION W3-OVER: W3 rides at the crown-bar height (z 601-804 over kits S / M / L); W3G "
     "deleted; RTM buckle and the hose slot (HOSE-LOW) 10 mm under the lowest W3 edge; W3 lies only on webbing, cord "
     "and the roll at all 6 kit-end corners (test); W3 crosses the roll at kit M / L part loads, so W3 is slackened "
     "to open the top; FIT-R3 row 7 at both ends of the owner's kit"),
    ("M-2", "major", "fixed", "DECISION RT-ORIGIN: BL-041's origin needed a 76 mm gusset tuck to fold flat and put the "
     "box across the hem fold gap: fall back to the roll end; cloth-pass roll model re-run with the new tab "
     "(corrie_f_roll_clips.json): paths 202-424 mm, RT cut 510 -> 560 mm"),
    ("M-3", "major", "fixed", "peel cannot be avoided (the stay-side leg passes under a pin 1.5-7.6 mm toward the frame "
     "from B-01: leg B leaves the box 23 deg off the box line in line, 50 deg held at the cheek-tip plane; he_peel); "
     "'no peel' dropped; rated instead: PT-3 on the printed BL-042 fairlead with B-01 held at the cheek-tip plane "
     "(worst peel) to 1530 N, and 3 HE specimens added to SEW-F at 625 N peak (1.15 x 1.6 g x 1019 / 3); load row "
     "lists the 34 x 7 box capacity and its peel"),
    ("M-4", "major", "fixed", "DECISION B25-TOPO drawn (SK-12, corrie_f.b25_topology): mitre under each sleeve, run "
     "and spine wrap necked to 25 mm, 13 mm over the (assumed) pawl housing at kit S 15 in; clamp undrawn in the frame "
     "files: ASSUMPTIONS B25-CLAMP / PAWL-TOP, gate B25-FIT in op 7.17; TL-1 specimen carries the turn and run"),
    ("m-1", "minor", "fixed", "box top +11 (5 mm under the cheeks at the design pin); HE-FIT band 22-29 keeps the box "
     ">= 2 mm under the cheeks over the whole band; the solved bracket 23.1-28.9 sits inside it (test)"),
    ("m-2", "minor", "fixed", "ops 4.05 / 4.08 give machine / needle / thread / stitch per step (step_spec), BT-301 "
     "named on the 304 tacks"),
    ("m-3", "minor", "fixed", "W3G (the only 16 mm BT-S) deleted; every BT-S is 10 x 2 (SK-1)"),
    ("m-4", "minor", "fixed", "IMC 192 mm, 48 mm folds, boxes 5 mm in from each raw end; MT-1 IMC specimens cut to it"),
    ("m-5", "minor", "fixed", "op 7.13 (IMC): cam and G-hook bars threaded before the boxes, hardware listed"),
    ("m-6", "minor", "fixed", "B25-BOX exception stated on the piece and on SK-1"),
    ("m-7", "minor", "fixed", "TL-1 / TL-1b read ovalisation at the loop centre with a bore gauge"),
    ("m-8", "minor", "fixed", "bar stock 2.0 m (5 x 200 + control 200 + 2 x 160 + 10 %); TL-1b steps include 288 N; "
     "TL-1b count 2 everywhere"),
    ("m-9", "minor", "fixed", "W3 / hose slot in the clearance set at all 6 corners; DECISION HOSE-LOW moves the slot "
     "below W3's sweep"),
    ("m-10", "minor", "fixed", "camo print BOM line proto_qty 0, 'production only'"),
    ("m-11", "minor", "fixed", "step 2 tiled print: every label block re-flowed into a clear spot (export.fit_label); "
     "B-18 and B-22 labels clear every mark and stay inside the outline (test); shortened labels in full on the NOTES "
     "page"),
    ("m-12", "minor", "fixed", "webbing pages: leader label on every line; B-25 and RT added; W3G removed"),
    ("m-13", "minor", "fixed", "SK-8 (c): stay labelled printed PAHT-CF, throat floor drawn with its gap under the pin "
     "(the HE redraw itself is BL-044)"),
    ("m-14", "minor", "fixed", "ledger row relabelled 'BL-004 REC: guy toggles x2', mapped by prefix (no keyword rows)"),
]


# BL-044: three review rounds found fixes that passed their own checks and failed on the real geometry. The release may
# say 'ready to cut' only after a FOURTH independent review of the BL-042 / 043 / 044 changes (orchestrator rule).
FOURTH_REVIEW_DONE = False


def open_findings() -> list:
    return [i for i, c, st, _ in REVIEW_STATUS + RECHECK_STATUS + THIRD_STATUS if c in ("blocker", "major") and st != "fixed"]


def ready_to_cut() -> bool:
    return FOURTH_REVIEW_DONE and not open_findings()


# ============================================================================ writers
def _w_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


def _md_table(rows: list[dict], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str("" if r.get(k) is None else r.get(k)).replace("|", "/").replace("\n", " ")
                                     for k, _ in cols) + " |")
    return "\n".join(out)


_imp = MF.imperial


def write_files(pk: dict, out: Path = OUT) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    files = []
    ctx, g = pk["ctx"], pk["geo"]
    _w_csv(out / "bom.csv", MF.bom_rows(pk["bom"]))
    _w_csv(out / "op_sequence.csv", MF.op_rows(pk["ops"]))
    _w_csv(out / "load_points.csv", pk["load_points"])
    _w_csv(out / "cutting_plan.csv", pk["cutting"])
    _w_csv(out / "qc_sheet.csv", pk["qc"])
    _w_csv(out / "release_tests.csv", pk["tests"])
    _w_csv(out / "defects.csv", [dict(zip(("defect", "where", "cause", "prevent_fix", "class"), d)) for d in DEFECTS])
    _w_csv(out / "delta_register_rev3.csv", pk["delta"])
    files += [out / n for n in ("bom.csv", "op_sequence.csv", "load_points.csv", "cutting_plan.csv", "qc_sheet.csv",
                                "release_tests.csv", "defects.csv", "delta_register_rev3.csv")]
    c = pk["costing"]
    (out / "costing.json").write_text(json.dumps(c, indent=1))
    (out / "manifest.json").write_text(json.dumps({"checks": checks(pk), "mass": pk["mass"], "geo": {
        k: v for k, v in g.items() if not isinstance(v, dict)}, "generator": "designs/pack_5200/mfg_corrie_f_rev3.py",
        "pattern_module": "designs/pack_5200/patterns_corrie_f_rev3.py", "date": DATE}, indent=1, default=str))
    files += [out / "costing.json", out / "manifest.json"]
    # ---- markdown
    md = [f"# {TITLE}: manufacturing package (BL-032 part B, BL-034 part C)", "",
          f"Generated {DATE} by `designs/pack_5200/mfg_corrie_f_rev3.py` from `patterns_corrie_f_rev3.build()` and the "
          "part A markers. **Do not edit by hand: re-run the script.** Patterns: `../patterns/`.", "",
          "## Files", "",
          "| File | What |", "|---|---|",
          "| `techpack_corrie_f_rev3.pdf` | the tech pack a contract factory quotes from (all sections below) |",
          f"| `preview/` | raster preview of every tech-pack page ({PREVIEW_DPI} dpi, phone-readable) |",
          "| `../camo/` | camo print file, colours, placement, vendors, costs (camo-designer release; BOM line 'fabric_print') |",
          "| `bom.csv` | BOM: primary and alternate fabric, webbing, hardware, thread, consumables, waste %, cost |",
          "| `cutting_plan.csv` | per material: markers, utilisation, lay, ply height, cutting method; webbing cut lengths |",
          "| `op_sequence.csv` / `op_sequence.md` | sewing operations in build order (machine, needle, thread, SPI, stitch, seam, time) |",
          "| `load_points.csv` | every load bartack / box-X: size, stitch count, load, capacity, SF, proof test |",
          "| `qc_sheet.md` / `qc_sheet.csv` / `release_tests.csv` / `defects.csv` | QC points, release gates, defect list |",
          "| `costing.md` / `costing.json` | material cost, beginner hours, factory SAM, CMT estimates |",
          "| `delta_register_rev3.csv` / `.md` | RD rows this release closes or restates |",
          "| `sketches/SK-*.png` | sketches the ops refer to |", "",
          "## Key numbers", "",
          f"- Pieces: {len(ctx.rs.pieces)} piece types; {sum(p.quantity for p in _fabric_pieces(ctx.rs))} fabric / sheet "
          f"pieces + {sum(w['qty'] for w in ctx.rs.webbing if not ('kit S' in w['kit'] or 'kit L' in w['kit']))} webbing / "
          f"cord / elastic pieces (crown kit M).",
          f"- Ledger 1:1: {pk['ctx'].rec and len(pk['ctx'].rec['rows'])} rows, {len(ctx.rec['unmatched_rows'])} unmatched, "
          f"{len(ctx.rec['pieces_without_row'])} pieces without a row. Mass from pattern areas (ledger basis, team B "
          f"fabrics): {pk['mass']['pattern_fabric_alt_g']} g vs {pk['mass']['ledger_fabric_g']} g "
          f"({pk['mass']['mass_delta_pct']:+.2f} %, limit +/-3 %). Primary fabrics weigh "
          f"{pk['mass']['primary_minus_alt_g']:+.1f} g more on the same pieces.",
          f"- Operations: {len(pk['ops'])}; beginner hours {c['proto_hours']} h (one-off set-up "
          f"{sum(o.proto_h for o in pk['ops'] if not o.per_bag):.1f} h of it); factory SAM {c['sam_min']:.0f} min "
          f"({c['sam_min'] / 60:.1f} h, ASSUMPTION SAM-RATIO).",
          f"- Material cost a bag, PRODUCTION (10-bag markers, record prices): primary ${c['material_usd_primary']:.0f}, "
          f"alternate ${c['material_usd_alternate']:.0f}. CMT + materials: US contract "
          f"${c['landed_usd']['us_contract_usd_min']:.0f}, Asia ${c['landed_usd']['asia_contract_usd_min']:.0f} "
          "(ASSUMPTION LABOUR).",
          f"- **What ONE bag costs to buy (prototype, 1-bag markers rounded to shop steps): ${c['prototype_usd']:.0f}** "
          f"(fabric ${c['prototype_buy']['fabric_usd']:.0f} vs ${c['fabric_usd_primary']:.0f} in production; "
          "ASSUMPTION SHOP-INCR; thread by the 4 oz cone, sealer and tape by the smallest pack, ASSUMPTION SHOP-UNIT; "
          "no camo print: DECISION CAMO-FIRST; table in costing.md).",
          f"- **Mass targets, PRIMARY fabrics (the set you build): base {pk['mass']['primary_base_g']:.0f} g "
          f"({pk['mass']['primary_base_g'] / 453.592:.2f} lb), as hunted {pk['mass']['primary_as_hunted_g']:.0f} g, meat "
          f"trip {pk['mass']['primary_meat_trip_g']:.0f} g** (QC-14, +/- {QC14_TOL_PCT:.0f} %); ledger (team B basis) "
          f"{pk['mass']['base_g']:.0f} / {pk['mass']['as_hunted_g']:.0f} / {pk['mass']['meat_trip_g']:.0f} g.",
          f"- **Sewing machine:** {PROTO_MACHINE_MIN} Fallback for the 304 tacks: {BT_301_FALLBACK}",
          f"- **First build fabric for the camo pieces (DECISION CAMO-FIRST, orchestrator 2026-11-13):** {FIRST_BUILD_CAMO}. "
          "B-02u is structural (two 715 mm corner seams, the floor seam and the #10 door zip): it is cut from 630D, the "
          "base the patterns, the BOM `fabric` line and QC-14 assume. The HyperD 300 print yard is a test-kit specimen "
          "only (AB-1 / FRAY-1, not a bag-cut gate); a printed bag waits for AB-1, FRAY-1 (HyperD | 330D) and a QC-14 "
          "target on that base.",
          "- **Camo (later builds):** the print comes from the camo-designer's release: read `../camo/README.md` first "
          "(print file `../camo/print/`, colours, placement, vendors, 1- and 10-bag costs). BOM section `fabric_print` "
          f"(production only). **Caveat:** {SUBLIMATION_CAVEAT}.",
          f"- **Colourway:** {colour_spec()['name']} = body {colour_spec()['body']}, trim {colour_spec()['trim']}, "
          f"harness {colour_spec()['harness']}, {colour_spec()['accent']} camo accents ({colour_spec()['ref']}); the "
          "BOM notes name it on every coloured line.",
          f"- Load points: {len(pk['load_points'])}; lowest SF {checks(pk)['min_sf']} ({checks(pk)['min_sf_point']}); the "
          "B-17 perimeter row is labelled SF PENDING PT-2 (load_points.csv).", "",
          "## Volatile operations (re-run when the pattern changes)", "",
          "These ops read their numbers from the pattern; re-run `python designs/pack_5200/mfg_corrie_f_rev3.py` after "
          "the pattern module changes and they update (tags name the pattern value each op reads; BL-033, which last "
          "moved them, has landed):", ""]
    for v in pk["volatile"]:
        md.append(f"- **{v}**: ops " + ", ".join(o.seq for o in pk["ops"] if o.volatile == v)
                  + ("; load points " + ", ".join(r["point"] for r in pk["load_points"] if r["volatile"] == v)
                     if any(r["volatile"] == v for r in pk["load_points"]) else ""))
    md += ["", f"Current values: B-22 at x +/-{g['b22_x']} mm (drawn {g['b22_drawn_x']}); FP flat width "
           f"{g['fp_flat_w']} mm (finished {g['fp_finished_w']}); {g['windows']} swell windows; F-01 drafted: "
           f"{g['fly_drafted']}; B-11 tabs on the gussets: {2 * (g['b11'] or {}).get('per_gusset', 0)}; K-W keeper z: "
           f"{g['kw_z']}.", "", "## On HOLD (cannot be sewn from the pattern as released)", ""]
    ck_ = checks(pk)
    md += [f"- {h}" for h in ck_["holds"]] or ["- none"]
    md += ["", "## Pattern / ledger flags", "",
           f"- Thread in the bag (all ops, no cone waste): {ck_['thread_bag_g']} g; booked on the ledger: "
           f"{ck_['thread_ledger_g']} g (build_effort_rev3.json; re-run `python designs/pack_5200/build_effort_rev3.py "
           "--write` when they differ).",
           f"- Box-X mismatches between a panel and its tab: {'; '.join(ck_['box_mismatches']) or 'none'}.",
           f"- Ledger hardware rows mapped by keyword (confirm): {'; '.join(ck_['hardware_rows_by_keyword']) or 'none'}.",
           f"- Unmapped ledger hardware rows: {'; '.join(ck_['unmapped_hardware']) or 'none'}."]
    allst = REVIEW_STATUS + RECHECK_STATUS + THIRD_STATUS
    nb = sum(1 for _, c, st, _ in allst if c == "blocker" and st != "fixed")
    nm = sum(1 for _, c, st, _ in allst if c == "major" and st != "fixed")
    md += ["", "## Pre-cut THIRD review status (BL-043 / BL-044)", "",
           "design-reviewer third review `analysis/review_20261113_rev3_third.md` (2 blockers, 4 majors, 14 minors). "
           "BL-043 fixed the bag-side items and checked each against every crown kit and torso end "
           "(tests/test_bl043_third_review_fixes.py); BL-042 fixed the frame print files and BL-044 the hinge eye on "
           "the BL-042 fairlead, checked by slicing the HE-FIT test-piece STL (tests/test_bl044_hinge_eye.py). "
           f"Open: {nb} blockers, {nm} majors. " + ("**ready to cut** after the physical gates." if ready_to_cut()
                                                    else "**NOT ready to cut**: " + ("findings open." if (nb or nm) else
                                                    "a FOURTH independent review of BL-042 / 043 / 044 is due first "
                                                    "(three rounds found fixes that passed their own checks but failed "
                                                    "on the real geometry).")), "",
           "| Finding | Class | Status | How |", "|---|---|---|---|"]
    md += [f"| {i} | {c} | {st} | {h.replace('|', '/')} |" for i, c, st, h in THIRD_STATUS]
    md += ["", "## Pre-cut re-check status (BL-041)", "",
           "design-reviewer re-check `analysis/review_20261113_rev3_recheck.md` (2 blockers, 5 majors, 15 minors), "
           "fixed by BL-041 and re-checked geometrically (tests/test_bl041_recheck_fixes.py). A third independent "
           "review is still due before the fabric is cut.", "",
           "| Finding | Class | Status | How |", "|---|---|---|---|"]
    md += [f"| {i} | {c} | {st} | {h.replace('|', '/')} |" for i, c, st, h in RECHECK_STATUS]
    md += ["", "## Pre-cut review status (BL-040)", "",
           f"Open after BL-044 (all three reviews): {nb} blockers, {nm} majors. " + (
               "**Ready to cut** the bag fabric once the G2 proof tests and the G3 wash have passed (the physical "
               "gates in qc_sheet.md still apply)." if ready_to_cut() else "**NOT ready to cut.**"), "",
           "| Finding | Class | Status | How |", "|---|---|---|---|"]
    md += [f"| {i} | {c} | {st} | {h.replace('|', '/')} |" for i, c, st, h in REVIEW_STATUS]
    md += ["", "## Assumptions that govern", "", "| ID | Assumption | Settled by |", "|---|---|---|"]
    md += [f"| {a} | {t} | {s} |" for a, t, s in ASSUMPTIONS]
    md += ["", "## Packaging", ""] + [f"{i + 1}. {t}" for i, t in enumerate(PACKAGING)]
    (out / "README.md").write_text("\n".join(md) + "\n")
    files.append(out / "README.md")
    # op sequence md
    om = [f"# {TITLE}: sewing operation sequence", "",
          "Beginner rules: all flat work before the bag becomes 3D; clips, never pins, in coated fabric; sew a swatch "
          "of the exact stack before every new operation; every load point is sewn only after its proof test passes "
          "(qc_sheet.md). Machines, needles and seams: tech pack section 2.", ""]
    cur = None
    for o in pk["ops"]:
        if o.step != cur:
            cur = o.step
            om += ["", f"## Step {cur}", ""]
        om.append(f"**{o.seq} {o.operation}**" + (f"  _(volatile: {o.volatile})_" if o.volatile else ""))
        om.append(f"- How: {o.notes}")
        om.append(f"- Machine {o.machine}; needle {o.needle}; thread {o.thread_id}; SPI {o.spi or '-'}; stitch "
                  f"{o.stitch_type}; seam {o.seam or '-'}" + (f"; attachment {o.attachment}" if o.attachment != '-' else ""))
        extra = []
        if o.length_mm:
            extra.append(f"stitching {o.length_mm:.0f} mm ({o.length_mm / IN:.0f} in)")
        if o.bartack:
            extra.append(f"load table: {o.bartack}")
        if o.sketch:
            extra.append(f"sketch {o.sketch}")
        if o.qc:
            extra.append(f"QC {o.qc}")
        extra.append(f"beginner {o.proto_h:.2f} h, SAM {o.time_s / 60:.1f} min" + ("" if o.per_bag else " (one-off)"))
        om.append("- " + "; ".join(extra))
    (out / "op_sequence.md").write_text("\n".join(om) + "\n")
    files.append(out / "op_sequence.md")
    # QC md
    qm = [f"# {TITLE}: QC sheet, release tests, defects", "", "## In-line and final checks", "",
          _md_table(pk["qc"], [("id", "ID"), ("stage", "Stage"), ("check", "Check"), ("method", "Method"),
                               ("pass", "Pass"), ("frequency", "Frequency")]), "",
          "## Physical tests that gate release (no load point is sewn on a carrying bag before its test passes)", "",
          _md_table(pk["tests"], [("id", "ID"), ("title", "Test"), ("gates", "Gates"), ("pass", "Pass / fail"),
                                  ("source", "Source")]), "",
          "## Defect list", "", "| Defect | Where | Cause | Prevent / fix | Class |", "|---|---|---|---|---|"]
    qm += [f"| {' | '.join(d)} |" for d in DEFECTS]
    (out / "qc_sheet.md").write_text("\n".join(qm) + "\n")
    files.append(out / "qc_sheet.md")
    # costing md
    cm = [f"# {TITLE}: costing and hours", "",
          f"Material cost a bag, record prices (production quantities): **primary ${c['material_usd_primary']:.2f}**, "
          f"alternate ${c['material_usd_alternate']:.2f} (fabric ${c['fabric_usd_primary']:.2f} / "
          f"${c['fabric_usd_alternate']:.2f}).", "",
          f"Beginner hours (bag_concepts.HOURS model, every op): **{c['proto_hours']} h**, of which one-off set-up "
          f"{sum(o.proto_h for o in pk['ops'] if not o.per_bag):.1f} h. Lid on the drafted pattern "
          f"{c['lid_hours_drafted']} h (booked {c['lid_hours_booked']} h).", "",
          "| Step | Beginner h |", "|---|---:|"]
    cm += [f"| {k} | {v:.2f} |" for k, v in c["proto_hours_by_step"].items()]
    cm += ["", f"Factory SAM {c['sam_min']:.0f} min ({c['sam_min'] / 60:.1f} h) a bag (ASSUMPTION SAM-RATIO "
           f"{FACTORY_RATIO}).", "", "| Scenario | Labour $ | CMT incl. overhead $ | + materials $ |", "|---|---:|---:|---:|"]
    for k in LABOUR:
        cm.append(f"| {k} | {c['labour_usd'][k]:.2f} | {c['cmt_usd'][k]:.2f} | {c['landed_usd'][k]:.2f} |")
    pbk = c["prototype_buy"]
    cm += ["", "## One bag (prototype buy) vs production (BL-040 M-11)", "",
           f"Production a bag (10-bag markers + waste): **${c['material_usd_primary']:.2f}**. Buying for ONE bag "
           f"(1-bag markers, shop increments): **${pbk['total_usd']:.2f}**. {pbk['assumption']}.", "",
           "| Section | Item | Unit | Production qty | Production $ | Prototype qty | Prototype $ | How |",
           "|---|---|---|---:|---:|---:|---:|---|"]
    def _usd(v):
        return "" if v is None else f"{v:.2f}"
    cm += [f"| {r['section']} | {r['item'].replace('|', '/')} | {r['unit']} | {r['production_qty']:g} | "
           f"{_usd(r['production_usd'])} | {r['prototype_qty']:g} | {_usd(r['prototype_usd'])} | {r['how']} |"
           for r in pbk["rows"]]
    ms = pk["mass"]
    cm += ["", "## Mass by kit (BL-040 M-6)", "",
           "| Kit | Ledger, team B fabrics (g) | Primary pattern delta (g) | PRIMARY target (g) | lb |", "|---|---:|---:|---:|---:|"]
    for k, lk, pk_ in (("base", "base_g", "primary_base_g"), ("as hunted", "as_hunted_g", "primary_as_hunted_g"),
                       ("meat trip", "meat_trip_g", "primary_meat_trip_g")):
        cm.append(f"| {k} | {ms[lk]:.1f} | {ms[pk_] - ms[lk]:+.1f} | {ms[pk_]:.1f} | {ms[pk_] / 453.592:.2f} |")
    cm += ["", "One-off tooling (not a bag): J1-J8 jigs; LK-1900 / AMS-210EN programs; laser files are the part A DXFs; "
           "dies only above ~500 bags a year.", "", "Assumptions: " + "; ".join(c["assumptions"]) + "."]
    (out / "costing.md").write_text("\n".join(cm) + "\n")
    files.append(out / "costing.md")
    dm = ["# Release delta register: rows this release resolves (BL-032)", "",
          "For the orchestrator to merge into `docs/release_delta_register.md` (not edited here).", "",
          _md_table(pk["delta"], [("id", "RD"), ("status_after_rev3_package", "Status"), ("evidence", "Evidence (checked "
                                                                                                     "by the script)"),
                                  ("still_open", "Still open")])]
    (out / "delta_register_rev3.md").write_text("\n".join(dm) + "\n")
    files.append(out / "delta_register_rev3.md")
    return files


# ============================================================================ sketches (matplotlib, from the pieces)
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


KIND_STYLE = {"cut_inside": ("k", "-", 1.2), "placement": ("#1a7f37", "--", 1.0), "stitch": ("#1a7f37", "-", 0.8),
              "fold": ("#1f5fbf", "-.", 0.9), "crease": ("#1f5fbf", "-.", 0.9)}


def draw_piece(ax, p, title, notes=None, label_lines=True, fs=7):
    cut = p.cut_line()
    xs, ys = zip(*(list(cut) + [cut[0]]))
    ax.plot(xs, ys, "k-", lw=1.4)
    sl = p.outline
    xs, ys = zip(*(list(sl) + [sl[0]]))
    ax.plot(xs, ys, color="0.55", ls="--", lw=0.8)
    seen = set()
    for ln in p.internal_lines:
        c, ls, lw = KIND_STYLE.get(ln.kind, ("0.4", ":", 0.8))
        pts = list(ln.points) + ([ln.points[0]] if ln.closed else [])
        if len(pts) < 2:
            continue
        x, y = zip(*pts)
        ax.plot(x, y, color=c, ls=ls, lw=lw)
        if label_lines and ln.label and ln.label not in seen:
            seen.add(ln.label)
            cx, cy = sum(x) / len(x), sum(y) / len(y)
            ax.annotate(ln.label, (cx, cy), fontsize=fs, color=c, ha="center",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    for d in p.drill_holes:
        ax.plot(*d.xy, "o", ms=3, mfc="none", mec="#b00")
    for n in p.notches:
        ax.plot(*n.xy, "|", color="#d00", ms=4)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=fs + 3, loc="left")
    ax.tick_params(labelsize=fs)
    ax.grid(True, lw=0.3, color="0.85")
    if notes:
        ax.text(0.0, -0.06, notes, transform=ax.transAxes, fontsize=fs + 1, va="top", wrap=True)


def sk_boxes(pk, path):
    plt = _plt()
    sizes = sorted({(r["pattern"].split("box-X ")[1].split(" mm")[0], r["stitches"]) for r in pk["load_points"]
                    if r["pattern"].startswith("box-X")})
    n = len(sizes) + 2
    cols = 3                    # BL-041 n-5: 4 columns clipped the right-hand labels
    rows = math.ceil(n / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(14, 3.9 * rows))
    import textwrap
    axs = axs.ravel()
    st = 25.4 / SPI["box"]
    for ax, (dims, nst) in zip(axs, sizes):
        w, h = (float(v) for v in dims.split(" x "))
        path_pts = [(0, 0), (w, 0), (w, h), (0, h), (0, 0), (w, h), (w, 0), (0, h)]
        x, y = zip(*path_pts)
        ax.plot(x, y, color="#1a7f37", lw=1.2)
        # stitch dots along the path
        for (x0, y0), (x1, y1) in zip(path_pts[:-1], path_pts[1:]):
            L = math.dist((x0, y0), (x1, y1))
            k = max(1, int(L / st))
            ax.plot([x0 + (x1 - x0) * i / k for i in range(k + 1)], [y0 + (y1 - y0) * i / k for i in range(k + 1)],
                    ".", color="k", ms=3)
        ax.annotate("start / end\n(overlap 10 mm)", (0, 0), (-0.45 * w, -0.35 * h), fontsize=7,
                    arrowprops=dict(arrowstyle="->", lw=0.7))
        used = sorted({r["part"] for r in pk["load_points"] if r["pattern"].startswith(f"box-X {dims} mm")})
        ax.set_title(f"box-X {dims} mm ({w / IN:.2f} x {h / IN:.2f} in)", fontsize=10, loc="left")
        exc = ("\nEXCEPTION (B25-BOX): B-25 is 38 mm webbing; this 21 mm box leaves 8.5 mm unsewn each edge so the "
               "13 mm toggle loop stays open" if any(u_.startswith("B-25") for u_ in used) else "")
        ax.text(0.0, -0.12, f"{nst} stitches incl. 4 lock, 7 SPI, tex 135, Nm 140 R\n"
                + textwrap.fill("used on: " + ", ".join(used), 48) + textwrap.fill(exc, 52, replace_whitespace=False),
                transform=ax.transAxes, fontsize=8, va="top")
        ax.set_xlim(-0.6 * w, 1.3 * w)
        ax.set_ylim(-0.5 * h, 1.3 * h)
        ax.set_aspect("equal")
        ax.axis("off")
    for ax, key in zip(axs[len(sizes):], ("BT-S", "BT-M")):
        b = BARTACK_STD[key]
        k = b["stitches"]
        xs = [b["len_mm"] * i / (k - 1) for i in range(k)]
        ys = [(b["w_mm"] if i % 2 else 0.0) for i in range(k)]
        ax.plot(xs, ys, "-", color="#1a7f37", lw=0.8)
        ax.set_title(f"{key} bartack {b['len_mm']:.0f} x {b['w_mm']:.0f} mm, {k} st (304)", fontsize=10, loc="left")
        used = {"BT-S": "B-27 slit ends, FP mouth corners (BL-043: W3G deleted; every BT-S is 10 x 2)",
                "BT-M": "I2K, HE neck (1 per leg), lid channel ends, B-25 sleeve laps"}[key]
        ax.text(0.0, -0.3, f"LK-1900 standard tack, tex 90, Nm 110 R (unrated)\n" + textwrap.fill(used, 48)
                + "\nno zigzag: BT-301 = 4 straight passes, 2 mm stitch", transform=ax.transAxes, fontsize=8, va="top")
        ax.set_ylim(-8, 10)
        ax.set_aspect("equal")
        ax.axis("off")
    for ax in axs[n:]:
        ax.axis("off")
    fig.suptitle("SK-1  Load-point stitch patterns (true proportions; dots = 7 SPI stitch positions)", fontsize=13, x=0.01,
                 ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def sk_seams(path):
    plt = _plt()
    fig, axs = plt.subplots(2, 4, figsize=(15, 7.5))
    axs = axs.ravel()

    def ply(ax, x0, x1, y, c="#335", lw=3):
        ax.plot([x0, x1], [y, y], color=c, lw=lw, solid_capstyle="butt")

    def needle(ax, x, y0, y1):
        ax.plot([x, x], [y0, y1], color="#c00", lw=1, ls=(0, (2, 1)))

    # SSa2
    ax = axs[0]
    ply(ax, 0, 10, 1.0); ply(ax, 0, 10, 0.6, "#6a6")
    ax.plot([10, 10.6, 10.6, 5.0], [1.0, 1.0, 1.25, 1.25], color="#335", lw=3)
    ax.plot([10, 10.6, 10.6, 5.0], [0.6, 0.6, 1.45, 1.45], color="#6a6", lw=3)
    needle(ax, 10.0, 0.3, 1.8); needle(ax, 6.0, 0.3, 1.8)
    ax.set_title("SSa2 body seam: 12 mm, then allowances\nturned and caught at 6 mm (2 rows)", fontsize=9)
    # LSd patch
    ax = axs[1]
    ply(ax, 0, 12, 0.5); ply(ax, 3, 9, 0.85, "#555", 5)
    for x in (3.3, 3.9, 8.1, 8.7):
        needle(ax, x, 0.2, 1.2)
    ax.set_title("LSd Hypalon patch: double row\n3 / 9 mm from the edge, 8 SPI tex 90", fontsize=9)
    # EFb hem with HDPE
    ax = axs[2]
    ax.plot([0, 9, 9.8, 9.8, 4], [0.5, 0.5, 0.5, 1.3, 1.3], color="#335", lw=3)
    ax.add_patch(plt.Rectangle((5, 0.7), 4.2, 0.35, color="#bbb"))
    ax.text(5.2, 0.8, "B-07s HDPE", fontsize=7)
    needle(ax, 4.6, 0.2, 1.6)
    ax.set_title("EFb roll-top hem round the HDPE strip", fontsize=9)
    # ZIP
    ax = axs[3]
    ply(ax, 0, 5.5, 1.0); ply(ax, 6.5, 12, 1.0, "#6a6")
    ax.add_patch(plt.Rectangle((4.5, 0.6), 3, 0.25, color="#222"))
    ax.text(5.1, 0.35, "#10 coil", fontsize=7)
    for x in (5.0, 4.2, 7.0, 7.8):
        needle(ax, x, 0.3, 1.4)
    ax.set_title("ZIP: tape sewn at 5 mm, turned,\nedge-stitched 3 mm (door, lid, pockets)", fontsize=9)
    # SSa-ins
    ax = axs[4]
    ply(ax, 0, 10, 1.0); ply(ax, 0, 10, 0.5, "#6a6"); ply(ax, 3, 10, 0.75, "#a60", 4)
    ax.text(2.0, 0.78, "webbing loop", fontsize=7, ha="right")
    needle(ax, 9.0, 0.2, 1.4)
    ax.set_title("SSa-ins: loop / tab caught in the seam,\nbacktack each side (HPL, K-W, E5)", fontsize=9)
    # B-27 lapped port
    ax = axs[5]
    ax.plot([0, 6, 6.6, 6.6, 5.4], [1.0, 1.0, 1.0, 1.3, 1.3], color="#335", lw=3)
    ax.plot([4, 10, 10, 9.4], [0.7, 0.7, 0.45, 0.45], color="#335", lw=3)
    ply(ax, 4.3, 9.3, 0.35, "#888", 3)
    ax.text(4.3, 0.1, "B-27f facing (inside)", fontsize=7)
    ax.annotate("outboard edge laps 20 mm", (5.5, 1.0), (1, 1.6), fontsize=7, arrowprops=dict(arrowstyle="->"))
    needle(ax, 6.2, 0.9, 1.5); needle(ax, 9.7, 0.2, 0.9); needle(ax, 8.8, 0.1, 0.8)
    ax.set_title("B-27 guy port: both edges turned 6 mm,\nfacing on the inboard edge, bartack ends", fontsize=9)
    # box-X stack
    ax = axs[6]
    ply(ax, 0, 12, 0.3)
    ply(ax, 2, 12, 0.55, "#555", 4)
    ax.plot([3, 11, 11, 3], [0.8, 0.8, 1.0, 1.0], color="#a60", lw=4)
    for x in (4, 6, 8, 10):
        needle(ax, x, 0.1, 1.2)
    ax.set_title("Load stack (e.g. LLT + B-22 + B-02h):\nwebbing fold / Hypalon / panel, box-X through all", fontsize=9)
    # dart
    ax = axs[7]
    ax.plot([0, 5, 10], [0, 3, 0], color="#335", lw=2)
    ax.plot([5, 5], [3, -0.5], color="#1f5fbf", ls="-.")
    needle(ax, 2.5, 0, 1.6); needle(ax, 7.5, 0, 1.6)
    ax.set_title("DART (B-29a, 4 corners): fold on the\ncentre, sew leg to leg, tie off at the apex", fontsize=9)
    for ax in axs:
        ax.set_xlim(-1, 13); ax.set_ylim(-0.6, 2.0); ax.axis("off")
    fig.suptitle("SK-2  Seam constructions (cross-sections, not to scale; red dashed = stitch row)", fontsize=13,
                 x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def sk_piece_map(pk, ids, title, path, notes, figsize=(15, 9)):
    plt = _plt()
    rs = pk["ctx"].rs
    fig, axs = plt.subplots(1, len(ids), figsize=figsize, gridspec_kw={"width_ratios": [
        max(1.0, rs.pieces[i].bounds()[2] - rs.pieces[i].bounds()[0]) for i in ids]})
    axs = [axs] if len(ids) == 1 else list(axs)
    for ax, pid, nt in zip(axs, ids, notes):
        p = rs.pieces[pid]
        draw_piece(ax, p, f"{pid} {p.name} ({p.material_id}, cut {p.quantity})", nt)
    fig.suptitle(title, fontsize=13, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def sk_webbing(pk, path):
    plt = _plt()
    rs = pk["ctx"].rs
    webs = [p for p in rs.pieces.values() if p.material_id in P.WEBBING]
    fig, ax = plt.subplots(figsize=(15, 0.42 * len(webs) + 1.5))
    y = 0.0
    for p in webs:
        L = p.edge_length("left")
        w = p.bounds(cut=False)[2]
        ax.add_patch(plt.Rectangle((0, y), L, w * 0.6, fc="#e9dcc4", ec="k", lw=0.6))
        for ln in p.internal_lines:
            if ln.kind == "fold":
                yy = ln.points[0][1]
                ax.plot([yy, yy], [y, y + w * 0.6], color="#1f5fbf", lw=1.0, ls="-.")
            if ln.kind == "stitch" and ln.closed:
                xs = [pt[1] for pt in ln.points]
                ax.add_patch(plt.Rectangle((min(xs), y + 1), max(xs) - min(xs), w * 0.6 - 2, fc="none", ec="#1a7f37", lw=1))
                ax.plot([min(xs), max(xs)], [y + 1, y + w * 0.6 - 1], color="#1a7f37", lw=0.7)
                ax.plot([min(xs), max(xs)], [y + w * 0.6 - 1, y + 1], color="#1a7f37", lw=0.7)
        ax.text(-15, y + w * 0.3, f"{p.piece_id} x{p.quantity}  {L:.0f} mm ({L / IN:.1f} in)", ha="right", va="center",
                fontsize=8)
        y += w * 0.6 + 8
    ax.set_xlim(-420, 2300)
    ax.set_ylim(-5, y + 5)
    ax.set_xlabel("mm along the strap (folds blue dash-dot, box-X green)")
    ax.set_yticks([])
    ax.set_title("SK-7  Webbing parts as cut (crown kit M); hot-knife length = strap length", fontsize=13, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def _eye_loop(g):
    """Main-ply centreline of the loaded hinge eye in section (y towards the bag, z above the floor seam line): leg A
    from the box top up the bag side of the pin, round it over the fold plies, leg B down the stay side between the
    pin and the throat floor (P.he_loop, BL-044 DECISION HE-ENV)."""
    import numpy as np
    lp = g["loop"]
    (cy, cz), r = lp["C"], lp["r_c"]
    th = np.linspace(lp["thA"], lp["thB"], 80)
    ys = [lp["A"][0]] + list(cy + r * np.cos(th)) + [lp["B"][0]]
    zs = [lp["A"][1]] + list(cz + r * np.sin(th)) + [lp["B"][1]]
    return ys, zs


def sk_hinge_eye(pk, path):
    """SK-8 (BL-040 B-1, redrawn BL-041 X-1 / X-2 and BL-044 Z-1 / M-3): the hinge eye as sewn (op 4.05 order: B-18
    rows FIRST, then the HE) and as loaded on the z 60 pin of the BL-042 hinge fairlead (DECISION HE-ENV), every
    dimension from the pattern and bag_attach.HINGE_EYE_ENVELOPE."""
    plt = _plt()
    rs = pk["ctx"].rs
    hg = rs.geo["he"]
    g = P.he_geometry()
    pl = P.he_peel()
    gap, top = hg["box_z_above_seam"]
    fig, axs = plt.subplots(1, 4, figsize=(19, 8.4), gridspec_kw={"width_ratios": [0.55, 0.9, 1.15, 1.25]})
    # (a) the flat strip
    draw_piece(axs[0], rs.pieces["HE"], f"(a) HE strip, flat\n(38 x {hg['cut']:.0f} mm)", fs=6)
    # (b) the op 4.05 order
    ax = axs[1]
    ax.axis("off")
    steps = [f"0  CALIPER one ply of the roll: <= {P.HE_T_RANGE[1]:.1f} mm\n   (3 plies must pass the {g['gap_under_pin']:.1f} mm gap\n"
             "   under the pin), else change webbing.",
             "1  NECK (flat strip): fold both long edges 10 mm in\n   between the neck lines (18 mm wide); BT-M tack\n"
             "   across each leg at the tack lines.",
             "2  B-18 ROWS FIRST: B-18 inside B-01, lower edge on\n   the B-01 cut edge; sew its 3 / 9 mm rows (top +\n"
             "   both sides) through B-18 + B-01 ONLY.",
             "3  PLACE HE: fold in half on EYE FOLD (neck folds\n   INSIDE), lay it OUTSIDE B-01 on the CL notch, eye\n"
             "   UP, raw ends on the cut edge. HE / HE / B-01 / B-18.",
             f"4  BOX-X {P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f} at +{gap:.0f}..+{top:.0f} mm through all 4\n"
             f"   layers. Box top stays BELOW +{g['cheek_lo']:.0f} (the cheeks).",
             "5  BASTE the stack at 6 mm in the allowance. Op 4.15\n   catches it in the floor seam (zipper / edge foot).",
             "No stitching may cross the eye after step 3."]
    for i, t in enumerate(steps):
        ax.text(0.0, 0.98 - i * 0.14, t, transform=ax.transAxes, va="top", fontsize=9.2,
                color="#b00" if i in (0, 2, 6) else "k", fontweight="bold" if i == 6 else "normal")
    ax.set_title("(b) op 4.05 order (PT-3 / SEW-F HE specimens: the same)", fontsize=10, loc="left")
    # (c) section through the eye on the BL-042 hinge fairlead (y towards the bag, z above the floor seam line)
    ax = axs[2]
    sr = g["stay_r"]
    ax.add_patch(plt.Rectangle((-sr, -14), 2 * sr, 70, fc="#666", alpha=0.35, ec="none"))
    ax.text(0, 52, "stay (printed PAHT-CF body)", ha="center", fontsize=8)
    # fairlead (BL-042 HINGE_GEOM): saddle root from the stay centreline up to the throat floor, cheeks beside the eye
    ax.add_patch(plt.Rectangle((0.0, g["cheek_lo"]), g["floor_y"], g["cheek_hi"] - g["cheek_lo"], fc="#577", ec="#233",
                               alpha=0.85))
    ax.add_patch(plt.Rectangle((g["floor_y"], g["cheek_lo"]), g["tip_y"] - g["floor_y"], g["cheek_hi"] - g["cheek_lo"],
                               fc="#9bb", ec="#577", hatch="//", alpha=0.45))
    ax.annotate(f"throat floor (saddle root)\n{g['gap_under_pin']:.1f} mm under the pin;\n3-ply neck {3 * P.HE_T:.1f} mm "
                f"+ {g['gap_under_pin'] - 3 * P.HE_T:.1f} clear", (g["floor_y"], g["cheek_hi"] - 3), (-13.5, 5.5),
                fontsize=7.5, color="#233", arrowprops=dict(arrowstyle="->"))
    ax.text(-13.5, 37.0, f"fairlead cheeks beside the eye (hatched)\nz +{g['cheek_lo']:.0f}..+{g['cheek_hi']:.0f}, tips "
            f"{g['tip_y']:.1f} mm from the stay CL\n(bag_attach.HINGE_EYE_ENVELOPE)", fontsize=7.5, color="#355")
    fy = g["face_y"]
    ax.plot([fy, fy], [-12, g["cheek_lo"] - 1], color="#2b6cb0", lw=4)
    ax.plot([fy, g["tip_y"]], [g["cheek_lo"] - 1, g["cheek_lo"]], color="#2b6cb0", lw=4)
    ax.plot([g["tip_y"], g["tip_y"]], [g["cheek_lo"], 52], color="#2b6cb0", lw=4)
    ax.plot([g["tip_y"] + 1.6, g["tip_y"] + 1.6], [g["cheek_lo"], P.B18_TOP], color="#555", lw=3)
    ax.text(g["tip_y"] + 2.2, 44, "B-01 | B-18\n(inside)", fontsize=8)
    ax.plot([g["tip_y"]] * 2, [gap, g["cheek_lo"]], color="#2b6cb0", lw=1, ls="--")
    ys, zs = _eye_loop(g)
    ax.plot(ys, zs, color="#c27c0e", lw=3.2)
    ax.plot([fy - g["t"] / 2] * 2, [-12, gap], color="#c27c0e", lw=2.2)
    ax.add_patch(plt.Circle((g["pin_y"], g["pin_z"]), g["pin_d"] / 2, fc="#222"))
    ax.add_patch(plt.Rectangle((fy - 2 * g["t"], gap), 2 * g["t"] + 3.0, top - gap, fc="#1a7f37", alpha=0.35, ec="#1a7f37"))
    ax.annotate(f"5 mm pin, frame z 60 = +{g['pin_z']:.0f}\n{g['pin_y'] - sr:.1f} mm above the stay\n(eye wraps it, box BELOW)",
                (g["pin_y"], g["pin_z"]), (-13.5, 45.0), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.annotate(f"box-X {P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f}, +{gap:.0f}..+{top:.0f}\n{hg['cheek_clear']:.0f} mm under the "
                f"cheeks\nleg B peels {pl['design']['peel_deg']:.0f} deg (in line) to\n{pl['worst']['peel_deg']:.0f} deg "
                "(B-01 held at the tips):\nrated by PT-3 + SEW-F HE", (fy, (gap + top) / 2), (fy + 1.5, -11),
                fontsize=7.5, color="#1a7f37", arrowprops=dict(arrowstyle="->", color="#1a7f37"))
    ax.plot([-14, 40], [0, 0], "k--", lw=1)
    ax.text(-13, 1.0, "floor seam line (frame z 35)", fontsize=8)
    ax.plot([-14, 40], [-12, -12], "k:", lw=1)
    ax.text(-13, -13.6, "B-01 cut edge (in the seam)", fontsize=8)
    ax.text(-13.5, -8.5, f"neck {P.HE_NECK_W:.0f} mm wide in the\n{g['throat']:.0f} mm throat (+/-1 mm\nneck: >= "
            f"{hg['throat_clear_side_min']:.1f} mm a side)", fontsize=7.5, color="#a5650a")
    ax.set_xlim(-14, 40)
    ax.set_ylim(-16, 56)
    ax.set_aspect("equal")
    ax.set_xlabel("mm from the stay centre towards the bag")
    ax.set_ylabel("mm above the floor seam line")
    ax.set_title(f"(c) Loaded on the BL-042 hinge fairlead (pin +{hg['pin_z_design']:.1f}; HE-FIT band "
                 f"{hg['pin_band'][0]:.0f}-{hg['pin_band'][1]:.0f})", fontsize=10, loc="left")
    # (d) on B-01, outside view, with the B-18 rows
    ax = axs[3]
    ax.add_patch(plt.Rectangle((-P.B18_W / 2, -P.B18_BELOW), P.B18_W, P.B18_H, fc="#ddd", ec="#555", ls="--"))
    for d, c in ((3.0, "#b00"), (9.0, "#b00")):
        ax.plot([-P.B18_W / 2 + d, -P.B18_W / 2 + d, P.B18_W / 2 - d, P.B18_W / 2 - d],
                [-P.B18_BELOW, P.B18_TOP - d, P.B18_TOP - d, -P.B18_BELOW], color=c, lw=1.1, ls="-")
    ax.text(-P.B18_W / 2, P.B18_TOP + 2, "B-18 rows 3 / 9 mm (red): sewn in STEP 2, before the HE", fontsize=8, color="#b00")
    x0, z0, x1, z1 = hg["eye_footprint"]
    nw = hg["neck_w"]
    ax.add_patch(plt.Rectangle((-P.HE_W / 2, -P.B18_BELOW), P.HE_W, top + P.B18_BELOW, fc="#f3d9a8", ec="#c27c0e", lw=1.2))
    ax.add_patch(plt.Rectangle((-nw / 2, z0), nw, z1 - z0, fc="#f3d9a8", ec="#c27c0e", lw=1.2, hatch=".."))
    ax.text(x1 + 2, (z0 + z1) / 2, f"open eye {hg['eye_mm']:.0f} mm, 18 mm neck\n(no row crosses it)", fontsize=8,
            color="#a5650a", va="center")
    bx0 = -P.HE_BOX[0] / 2
    ax.add_patch(plt.Rectangle((bx0, gap), P.HE_BOX[0], P.HE_BOX[1], fc="none", ec="#1a7f37", lw=1.6))
    ax.plot([bx0, -bx0], [gap, top], color="#1a7f37")
    ax.plot([bx0, -bx0], [top, gap], color="#1a7f37")
    th2 = g["throat"] / 2
    for xa in (-th2 - 8.0, th2):                            # cheeks: 8 mm (bag_attach.CHEEK) either side of the throat
        ax.add_patch(plt.Rectangle((xa, g["cheek_lo"]), 8.0, g["cheek_hi"] - g["cheek_lo"], fc="#9bb", alpha=0.35,
                                   ec="#577", ls=":"))
    ax.text(-th2 - 30, g["cheek_hi"] + 1.5, "cheek footprint", fontsize=7.5, color="#355")
    ax.plot([0], [g["pin_z"]], "o", color="#222", ms=7)
    ax.text(3, g["pin_z"] + 1.5, "pin", fontsize=8)
    ax.plot([-70, 70], [0, 0], "k--", lw=1)
    ax.plot([-70, 70], [-P.B18_BELOW] * 2, "k-", lw=1)
    ax.plot([0, 0], [-P.B18_BELOW - 6, -P.B18_BELOW], color="#d00", lw=2)
    ax.text(2, -P.B18_BELOW - 9, "'hinge eye CL' notch", fontsize=8, color="#d00")
    ax.text(-68, 1.5, "floor seam line", fontsize=8)
    ax.text(-68, -P.B18_BELOW + 1.5, "cut edge", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-72, 72)
    ax.set_ylim(-32, 62)
    ax.set_title(f"(d) On B-01 from OUTSIDE, x +/-{P.STAY_X:.0f} (both sides)", fontsize=10, loc="left")
    fig.suptitle("SK-8  Hinge eye HE + B-18 (DECISIONS HE-ONE + HE-PIN + HE-ENV, op 4.05; PT-3, SEW-F HE and HE-FIT "
                 "specimens are sewn exactly so)", fontsize=13, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=95)
    plt.close(fig)


def sk_keeper_stack(pk, path):
    """SK-9 (BL-040 B-3): stack order where a K-W keeper loop is caught in the aft corner seam over the FP pocket."""
    plt = _plt()
    g = pk["geo"]
    kw = g["kw_z"]
    hits = [f"{side} z {z:.0f} ({wid})" for wid in sorted(kw) for side, z in kw[wid].items() if P.FP_Z[0] <= z <= P.FP_Z[1]]
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.4))
    ax = axs[0]
    rows = [("blade U  (face DOWN)", 3.0, "#2b6cb0", 0, 12), ("K-W keeper loop (ON TOP of the mesh)", 2.0, "#c27c0e", 1, 12),
            ("FP mesh edge (basted, op 4.10)", 1.0, "#7a7", 2, 12), ("gusset B-03  (face UP)", 0.0, "#555", 0, 12)]
    for lab, y, c, x0, x1 in rows:
        ax.plot([x0, x1], [y, y], color=c, lw=6, solid_capstyle="butt")
        ax.text(x1 + 0.4, y, lab, va="center", fontsize=10, color=c)
    ax.plot([1, -1.2, -1.2, 1], [2.0, 2.0, 2.35, 2.35], color="#c27c0e", lw=3)
    ax.text(-1.4, 2.6, "loop points INTO\nthe gusset", fontsize=8, ha="center")
    ax.plot([10, 10], [-0.6, 3.6], color="#c00", ls=(0, (3, 2)), lw=1.4)
    ax.text(10, -1.0, "seam line (12 mm in from the cut edge)", ha="center", fontsize=8, color="#c00")
    ax.plot([12, 12], [-0.6, 3.6], color="k", lw=1)
    ax.text(12, -1.6, "cut edge", ha="center", fontsize=8)
    ax.set_xlim(-3, 26)
    ax.set_ylim(-2.2, 4.5)
    ax.axis("off")
    ax.set_title("(a) Before sewing op 4.13: layers bottom to top", fontsize=11, loc="left")
    ax = axs[1]
    ax.add_patch(plt.Rectangle((0, 0), 10, 6, fc="#e8f0e8", ec="#7a7"))
    ax.text(4, 5.0, "FP mesh pocket\n(on the gusset)", ha="center", va="center", fontsize=10, color="#363")
    ax.plot([10, 10], [-1, 8], color="#555", lw=3)
    ax.text(10.2, 7.6, "aft corner seam", fontsize=9)
    ax.add_patch(plt.Rectangle((7.2, 2.4), 2.8, 1.2, fc="#f3d9a8", ec="#c27c0e", lw=1.5))
    ax.text(7.0, 4.0, "K-W keeper: OVER the mesh", fontsize=9, color="#a5650a", ha="right")
    ax.annotate("", (-1.5, 3.0), (13.5, 3.0), arrowprops=dict(arrowstyle="<->", color="#2b6cb0", lw=2))
    ax.text(10.6, 0.6, "haul wrap W runs through\nthe keeper, OVER the pocket", fontsize=9, color="#2b6cb0")
    ax.text(0, -1.8, "WRONG: keeper under the mesh = the wrap must thread INSIDE the pocket; fixing it means unpicking "
            "the 715 mm seam.\nCheck every keeper before sewing on. Keepers on the FP edge: " + ("; ".join(hits) or "none"),
            fontsize=9, color="#b00")
    ax.set_xlim(-2, 18)
    ax.set_ylim(-3, 8.5)
    ax.axis("off")
    ax.set_title("(b) Turned right side out: what you must see", fontsize=11, loc="left")
    fig.suptitle("SK-9  Aft corner seam (op 4.13): K-W keeper loop goes ON TOP of the FP mesh edge", fontsize=13, x=0.01,
                 ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def sk_roll_clip(pk, path):
    """SK-10 (BL-040 B-2): roll-top clip: RT strap on the hem, RTM buckle tab on the gusset."""
    plt = _plt()
    rs = pk["ctx"].rs
    rtm, rt = rs.geo["rtm"], rs.geo["rt_on_b07"]
    fig = plt.figure(figsize=(16, 8.5))
    ax = fig.add_axes([0.04, 0.58, 0.92, 0.32])
    b07 = rs.pieces["B-07"]
    draw_piece(ax, b07, "(a) B-07 hem, flat, OUTSIDE up: RT strap rectangles + box-X (op 5.02); red ticks = notches",
               label_lines=False, fs=7)
    for side, d in rt.items():
        ax.annotate(f"RT {side}: sewn 60 mm on the B-07s strip,\nfree strap out across the roll-end notch",
                    (d["x_centre"], 30), (d["x_centre"] - 130, 95), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax.set_ylim(-20, 120)
    ax2 = fig.add_axes([0.05, 0.05, 0.50, 0.47])
    G = rs.pieces["B-03"]
    draw_piece(ax2, G, "(b) Gusset B-03 (upper part): RTM tab, strap line to the roll end, W3 sweep (op 4.08)",
               label_lines=False, fs=7)
    rl, rc = rs.geo["rt_layout"], rs.geo["rt_clear"]
    x0, y0, x1, y1 = rtm["rect"]
    xm, yb = rl["x"], rl["y_bar"]
    sig = P._maps(P.F.make())["sig"]
    sw = rs.geo["w3_sweep"]
    ax2.axhspan(sig(sw["z_min"]) - sw["half_w"], rl["y_top"], color="#4a5d7a", alpha=0.12)
    for nm, z in sw["corners"].items():
        if z < rs.geo["z_c"]:
            ax2.plot([-20, 240], [sig(z)] * 2, color="#4a5d7a", lw=0.8, ls=":")
    on_g = ", ".join(f"{k}" for k, z in sw["corners"].items() if z < rs.geo["z_c"])
    ax2.text(255, 722, f"W3 sweep (shaded), z {sw['z_min']:.0f}-{sw['z_max']:.0f}: crown bar height,\nall kits; dotted = "
             f"kit ends on the gusset\n({on_g});\nW3 lies OVER the strap: slacken W3 to open the top", fontsize=7.5,
             color="#4a5d7a", va="top")
    ax2.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f3d9a8", ec="#c27c0e", lw=1.5))
    ax2.add_patch(plt.Rectangle((xm - P.BUCKLE_ENV[0] / 2, yb), P.BUCKLE_ENV[0], P.BUCKLE_ENV[1], fc="#ccc", ec="#333",
                                lw=1.0, ls="--"))
    (cx0, cy0), (cx1, cy1) = rl["corridor"]
    ax2.plot([cx0, cx1], [cy0, cy1], color="#c27c0e", lw=8, alpha=0.35, solid_capstyle="butt")
    ax2.plot([-20, 240], [rl["y_cord"]] * 2, color="#7a2e2e", lw=1.2, ls="-.")
    ax2.text(-25, rl["y_cord"] + 3, "B-26 cord (R)", fontsize=7, color="#7a2e2e")
    ax2.annotate(f"RTM: bar z {rtm['z']:.0f} ({rtm['below_seam_mm']:.0f} mm under the collar seam),\n"
                 f"{rtm['depth_from_frame_mm']:.0f} mm aft of the frame seam; dashed = buckle envelope,\n"
                 f"{rc['w3_hard_min']:.1f} mm under W3 at kit S 15 in; min clear {rc['min_gap']:.1f} mm to tabs / slot",
                 (x1, y0 + 10), (250, 430), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax2.annotate("RT strap from the roll end\n(off the cloth above the buckle)", (0.5 * (cx0 + cx1), 0.5 * (cy0 + cy1)),
                 (255, 625), fontsize=8, color="#a5650a", arrowprops=dict(arrowstyle="->", color="#a5650a"))
    ax2.annotate("muzzle keeper tabs", (205, 600), (255, 580), fontsize=8, color="#1a7f37",
                 arrowprops=dict(arrowstyle="->", color="#1a7f37"))
    hz = sig(P.HOSE_Z)
    ax2.annotate(f"IMP-2 hose slot (z {P.HOSE_Z:.0f}, below W3)", (16, hz), (-20, 410), fontsize=8,
                 arrowprops=dict(arrowstyle="->"))
    ax2.set_xlim(-30, 420)
    ax2.set_xlabel("mm across the gusset (flat)")
    ax2.set_ylabel("sigma (mm along the gusset)")
    ax2.set_ylim(400, 730)
    ax3 = fig.add_axes([0.60, 0.05, 0.38, 0.45])
    ax3.plot([0, 0, 10, 10], [0, 7, 7, 0], color="#555", lw=2)
    ax3.add_patch(plt.Circle((5, 7.7), 1.1, fc="#ccd", ec="#335"))
    ax3.text(5, 9.2, "rolled collar (3 rolls)", ha="center", fontsize=9)
    ax3.plot([6.0, 7.5, 7.6], [7.9, 6.0, 4.6], color="#c27c0e", lw=3)
    ax3.add_patch(plt.Rectangle((7.2, 4.0), 0.8, 0.6, fc="#222"))
    ax3.add_patch(plt.Rectangle((7.25, 3.3), 0.7, 0.7, fc="#666"))
    ax3.plot([7.6, 7.6], [3.3, 2.6], color="#c27c0e", lw=3)
    ax3.text(8.2, 4.9, "male half (adjustable), on the RT strap", fontsize=8)
    ax3.text(8.2, 3.0, "female half on the RTM tab,\nbox-X'd to the gusset", fontsize=8)
    ax3.text(7.8, 2.2, "tail + K-RT keeper", fontsize=8)
    ax3.text(5, 1.0, "gusset (side of the bag)", ha="center", fontsize=9)
    ax3.set_xlim(-1, 13)
    ax3.set_ylim(0, 10)
    ax3.axis("off")
    ax3.set_title("(c) Closed: roll end -> RT strap -> buckle -> RTM tab", fontsize=10, loc="left")
    fig.suptitle("SK-10  Roll-top clip: what to sew where (BL-040 B-2; BL-041 RT-FWD; BL-043 W3-OVER / RT-ORIGIN)", fontsize=13, x=0.01,
                 ha="left")
    fig.savefig(path, dpi=100)
    plt.close(fig)


def sk_meat_straps(pk, path):
    """SK-11 (BL-041 m-19 / n-15, DECISION IM-CAM-TAB): IM1-IM3 and US1/US2 as assembled, every part and every sewn
    joint on the rated path."""
    plt = _plt()
    rs = pk["ctx"].rs
    fig, axs = plt.subplots(4, 1, figsize=(15, 9.5))
    ims = {w["id"]: w for w in rs.webbing}
    imc = rs.pieces["IMC"]
    for ax, sid, end in ((axs[0], "IM1", "G-hook"), (axs[1], "IM2", "G-hook"), (axs[2], "IM3", "wiregate carabiner")):
        L = ims[sid]["length_mm"]
        ax.plot([0, 100], [0, 0], color="#555", lw=8)
        ax.text(2, 0.35, "left IM eye\n(frame, girth hitch)", fontsize=8)
        ax.add_patch(plt.Rectangle((100, -0.18), 30, 0.36, fc="#c27c0e"))
        ax.add_patch(plt.Rectangle((130, -0.18), 25, 0.36, fc="none", ec="#1a7f37", lw=1.5))
        ax.text(118, -0.6, "sewn loop\nbox-X 21 x 25", fontsize=7.5, color="#1a7f37")
        ax.plot([155, 610], [0, 0], color="#c27c0e", lw=6)
        ax.text(330, 0.25, f"{sid} strap {L:.0f} mm (25 mm), over the meat", fontsize=8.5, ha="center")
        ax.add_patch(plt.Rectangle((610, -0.35), 40, 0.7, fc="#888", ec="#222"))
        ax.text(612, 0.45, "CAM\n(free end in\nfrom the wearer)", fontsize=7.5)
        ax.plot([650, 700], [0.15, 0.15], color="#c27c0e", lw=4, ls=":")
        ax.text(655, 0.28, "tail + K-IM", fontsize=7.5)
        ax.add_patch(plt.Rectangle((650, -0.25), 4.0 * P.IMC_FOLD / 2.2, 0.22, fc="#e9b96e", ec="#a5650a"))
        ax.text(690, -0.78, f"IMC {imc.edge_length('left'):.0f} mm: box-X 21 x 25\nat both ends (SEWN to the cam bar\nand to the "
                f"{'hook' if 'hook' in end else 'carabiner'})", fontsize=7.5, color="#a5650a")
        ax.add_patch(plt.Circle((740, -0.14), 0.18, fc="#444"))
        ax.text(760, -0.2, f"{end}\n-> right IM eye", fontsize=8)
        ax.set_xlim(-5, 900)
        ax.set_ylim(-1.0, 1.0)
        ax.axis("off")
        ax.set_title(f"{sid}: rated path left eye -> loop box -> strap -> cam -> IMC (2 boxes) -> {end} -> right eye "
                     "(605 N, MT-1)", fontsize=10, loc="left")
    ax = axs[3]
    ax.plot([0, 100], [0, 0], color="#555", lw=8)
    ax.text(2, 0.35, "left pin\n(UHMWPE sleeve)", fontsize=8)
    ax.add_patch(plt.Rectangle((100, -0.18), 25, 0.36, fc="none", ec="#1a7f37", lw=1.5))
    ax.text(100, -0.62, "sewn eye box-X 21 x 25", fontsize=7.5, color="#1a7f37")
    ax.plot([125, 600], [0, 0], color="#c27c0e", lw=6)
    ax.text(330, 0.25, "US1 / US2 550 mm, under the floor channels", fontsize=8.5, ha="center")
    ax.add_patch(plt.Rectangle((600, -0.35), 40, 0.7, fc="#888", ec="#222"))
    ax.text(602, 0.45, "CAM on the\nright pin", fontsize=7.5)
    ax.add_patch(plt.Rectangle((645, -0.2), 20, 0.4, fc="#bbb", ec="#222"))
    ax.text(645, -0.62, "stainless tri-glide backstop\n(US-BS)", fontsize=7.5)
    ax.set_xlim(-5, 900)
    ax.set_ylim(-1.0, 1.0)
    ax.axis("off")
    ax.set_title("US1 / US2: sewn eye on the left pin -> strap -> cam on the right pin -> backstop (720 N, MT-1, US-BS)",
                 fontsize=10, loc="left")
    fig.suptitle("SK-11  Meat straps as assembled: every joint on the rated path is sewn or a rated part "
                 "(BL-041 DECISION IM-CAM-TAB)", fontsize=13, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=95)
    plt.close(fig)


def sk_bridle(pk, path):
    """SK-12 (BL-043 M-4, DECISION B25-TOPO): the 38 mm B-25 on the crown, drawn to scale from corrie_f.b25_topology:
    (a) looking forward from the bag (aft elevation, x along the bar, z down the spine); (b) section through the sleeve
    (y-z): the strip leaves the bar down on the aft side; (c) the flat strip with its folds."""
    plt = _plt()
    from matplotlib.patches import Circle, Polygon, Rectangle
    rs = pk["ctx"].rs
    tp = rs.geo["b25"]["topology"]
    F_ = P.F
    rb, rsp = F_.BAR_OD / 2, F_.SPINE_OD / 2
    x0, x1 = tp["band_x"]
    st, sb = tp["mitre"]["s"]
    ns = tp["run_s"]
    ch, cc = tp["clamp_half_x"], tp["clamp_collar_mm"]
    kS = tp["kits"][tp["governing_kit"]]
    fig = plt.figure(figsize=(16, 9.5))
    ax = fig.add_axes([0.04, 0.38, 0.60, 0.52])
    ax.add_patch(Rectangle((-110, -rb), 220, 2 * rb, fc="#cfcfcf", ec="#333"))                     # bar
    ax.add_patch(Rectangle((-rsp, -kS["s_pawl_mm"] - 10), 2 * rsp, kS["s_pawl_mm"] + 10 - rb, fc="#e2e2e2", ec="#333"))
    ax.add_patch(Rectangle((-ch, -rb - cc), 2 * ch, cc + 2 * rb, fc="#9aa7b8", ec="#333", alpha=0.8))  # clamp
    ax.text(0, rb + 3, f"spine clamp (BL-045 sized: half {ch:.1f}, collar {cc:.1f})\nspine axis "
                       f"{tp['spine_fore_mm']:.2f} mm FORE of the bar plane", ha="center", fontsize=8)
    ht = -kS["housing_top_s_mm"]
    hw = F_.PAWL_HOUSING_HALF_W
    ax.add_patch(Rectangle((-hw, -kS["s_pawl_mm"] - 11), 2 * hw, kS["s_pawl_mm"] + 11 + ht, fc="#d9c7a0", ec="#7a5c1e",
                           alpha=0.7))
    ax.add_patch(Rectangle((-110, -kS["s_pawl_mm"] - 11), 220, 22, fc="#e8e0cc", ec="#7a5c1e", alpha=0.6))
    ax.text(-108, ht - 22, f"upper bar + pawl housing at kit {tp['governing_kit']} {kS['torso_in']:g} in (housing measured on the H1 STL, BL-045)",
            fontsize=8, color="#7a5c1e")
    for sx in (-1, 1):
        a, b = sorted((sx * x0, sx * x1))
        ax.add_patch(Rectangle((a, -rb), b - a, 2 * rb, fc="#e9b96e", ec="#a5650a", alpha=0.9))      # sleeve
        ax.add_patch(Rectangle((a, -rb - (st - rb)), b - a, st - rb, fc="#e9b96e", ec="#a5650a", alpha=0.5))   # drop
        xi, xo = (x0, x1) if sx > 0 else (-x0, -x1)
        ax.add_patch(Polygon([(xo, -st), (xo, -sb), (xi, -sb)], fc="#e9b96e", ec="#a5650a", alpha=0.75))
        ax.plot([xo, xi], [-st, -sb], color="#2b6cb0", lw=1.5, ls="-.")
        ax.add_patch(Rectangle((min(sx * (rsp + 1.2), xi), -ns[1]), abs(xi - sx * (rsp + 1.2)), ns[1] - ns[0],
                               fc="#e9b96e", ec="#a5650a", alpha=0.75))
        ax.text(sx * 0.5 * (x0 + x1), rb + 19, f"sleeve x {x0:.1f}-{x1:.1f}", ha="center", fontsize=8)
        ax.text(sx * (x1 + 3), -0.5 * (st + sb), "45 deg MITRE\n(under the sleeve)", ha="left" if sx > 0 else "right",
                fontsize=7.5, color="#2b6cb0", va="center")
    ax.add_patch(Rectangle((-rsp - 1.2, -ns[1]), 2 * rsp + 2.4, ns[1] - ns[0], fc="#c27c0e", ec="#a5650a"))
    ax.annotate(f"spine wrap, necked to {tp['neck_w_mm']:.0f} mm,\n{kS['clear_mm']:.0f} mm above the pawl housing at "
                f"kit {tp['governing_kit']} {kS['torso_in']:g} in", (-rsp, -0.5 * (ns[0] + ns[1])), (-112, 11), fontsize=7.5,
                arrowprops=dict(arrowstyle="->"))
    ax.annotate(f"{tp['band_to_clamp_x_mm']:.1f} mm", (ch, 0), (ch + 1, -2), fontsize=7)
    ax.set_xlim(-115, 115)
    ax.set_ylim(-kS["s_pawl_mm"] - 18, 36)
    ax.set_aspect("equal")
    ax.set_xlabel("x along the crown bar from the spine centre (mm)")
    ax.set_ylabel("z from the bar centre (mm)")
    ax.set_title(f"(a) Crown seen from the bag (aft): sleeve, drop, mitre, necked run (+{tp['run_extra_mm']:.1f} mm a side "
                 "to reach the spine fore of the bar), spine wrap", fontsize=10, loc="left")
    ax2 = fig.add_axes([0.68, 0.40, 0.29, 0.48])
    ax2.add_patch(Circle((0, 0), rb, fc="#cfcfcf", ec="#333"))
    th = __import__("numpy").linspace(0.5 * math.pi, 2.5 * math.pi, 60)
    r = rb + 1.2
    ax2.plot(r * __import__("numpy").cos(th), r * __import__("numpy").sin(th), color="#a5650a", lw=3)
    ax2.plot([r, r], [0, -st + 2], color="#a5650a", lw=3)
    ax2.add_patch(Rectangle((r - 1, -sb), 2, sb - st, fc="#e9b96e", ec="#a5650a"))
    ax2.plot([0, 0], [r, r + 30], color="#a5650a", lw=3)
    ax2.text(2, r + 20, "toggle tab\n(guy + crown strap)", fontsize=8)
    ax2.annotate("strip leaves DOWN\non the AFT side", (r, -14), (r + 6, -30), fontsize=8, arrowprops=dict(arrowstyle="->"))
    ax2.text(-r - 3, -6, "wearer\n(fore)", ha="right", fontsize=8, color="#555")
    ax2.text(r + 8, 4, "bag\n(aft)", fontsize=8, color="#555")
    ax2.set_xlim(-35, 45)
    ax2.set_ylim(-sb - 5, 45)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("(b) Section through a sleeve (y-z)", fontsize=10, loc="left")
    ax3 = fig.add_axes([0.04, 0.05, 0.92, 0.22])
    b25 = rs.pieces["B-25"]
    L = b25.bounds(cut=False)[3]
    ax3.add_patch(Rectangle((0, 0), L, tp["width_mm"], fc="#fbeed6", ec="#333"))
    for ln in b25.internal_lines:
        pts = [(q[1], q[0]) for q in ln.points]
        col = {"fold": "#2b6cb0", "stitch": "#1a7f37", "placement": "#888"}.get(ln.kind, "#333")
        ax3.plot(*zip(*pts), color=col, lw=1.0, ls="-." if ln.kind == "fold" else "-")
    fl = rs.geo["b25"]["flat"]
    for yy, lab, up in ((fl["mitre_y"], "MITRE R", 1), (L - fl["mitre_y"], "MITRE L", 1), (fl["neck_y"], "NECK from here", 0),
                        (fl["centre_y"], "spine wrap centre", 1), (30, "tab fold", 1), (L - 30, "tab fold", 1)):
        ax3.text(yy, tp["width_mm"] + 3 if up else -6, lab, ha="center", fontsize=7.5)
    ax3.set_xlim(-10, L + 10)
    ax3.set_ylim(-8, tp["width_mm"] + 14)
    ax3.set_aspect("equal")
    ax3.set_xlabel("mm along the strip (cut %.0f mm; BL-043 drew %.0f in the bar plane, BL-041 %.0f with no turn)"
                   % (tp["cut_mm"], tp["cut_bl043_mm"], tp["cut_bl041_mm"]))
    ax3.set_yticks([])
    ax3.set_title("(c) B-25 flat, 38 mm: folds blue dash-dot, boxes green (op 7.17)", fontsize=10, loc="left")
    fig.suptitle("SK-12  B-25 guy bridle on the crown (BL-043 B25-TOPO, BL-044 on the BL-045 clamp): the turn sits UNDER each sleeve; "
                 "gate B25-FIT dry-fits it before the laps are tacked", fontsize=12, x=0.01, ha="left")
    fig.savefig(path, dpi=100)
    plt.close(fig)


def sketches(pk, out: Path = OUT) -> dict:
    d = out / "sketches"
    d.mkdir(parents=True, exist_ok=True)
    g = pk["geo"]
    sk = {}
    sk["SK-1"] = d / "SK-1_load_point_patterns.png"
    sk_boxes(pk, sk["SK-1"])
    sk["SK-2"] = d / "SK-2_seam_constructions.png"
    sk_seams(sk["SK-2"])
    sk["SK-3"] = d / "SK-3_B-01_flat_work.png"
    sk_piece_map(pk, ["B-01", "B-13x", "B-27f"], "SK-3  B-01 frame-side panel: flat work in order 4.02 swells, 4.03 "
                 "B-27 ports, 4.04 B-17 (outside), 4.05 B-18 + HE (inside), 4.06 I2K", sk["SK-3"],
                 [f"{g['windows']} swell windows (cut-outs), B-27 slits x +/-52 z {g['port_z'][0]:.0f}-"
                  f"{g['port_z'][1]:.0f}. HE / B-18 box drawn (read from the pattern).", "6 with port (B-12 on the crest; "
                  "no hinge swells since BL-033 H-1)", "facing INSIDE, inboard stitch line"], figsize=(16, 9))
    sk["SK-4"] = d / "SK-4_hinge_band.png"
    sk_piece_map(pk, ["B-02h", "B-22", "B-02door"], f"SK-4  Hinge band B-02h: B-22 INSIDE at x +/-{g['b22_x']} "
                 "(volatile), LLT box-X, B-28 front tab box-X (outside); then the door hinge seam", sk["SK-4"],
                 [f"B-22 drawn x +/-{g['b22_drawn_x']:.0f}, placed +/-{g['b22_x']}", "double-row perimeter",
                  "IMP-4 placement INSIDE"], figsize=(16, 7))
    sk["SK-5"] = d / "SK-5_gusset.png"
    sk_piece_map(pk, ["B-03", "FP-a", "FP-b"], "SK-5  Side gusset B-03 (cut L+R): kick band, FP pocket, IMP-8 (R only), "
                 "hose slot, 4 B-11 lash tabs (op 4.07), K-W keeper notches on the aft edge; corner seams carry HPL (L) "
                 "and E5 (R)", sk["SK-5"],
                 [f"FP z {g['fp_z'][0]:.0f}-{g['fp_z'][1]:.0f}", f"flat {g['fp_flat_w']:.0f} wide, 2 box pleats",
                  "fold = shock-cord channel"], figsize=(16, 9))
    sk["SK-6"] = d / "SK-6_crown_lid.png"
    sk_piece_map(pk, ["B-29a", "B-29b", "B-29e", "B-29g"], "SK-6  B-29 crown lid: darts -> channels -> zip between "
                 "the aft strips -> caps -> crown|wall ring -> wall|base ring (turn through the zip)", sk["SK-6"],
                 ["4 darts, 2 channel lines", "base (70D / 100D)", "aft lower: caps + #5 zip", "channel x2"],
                 figsize=(17, 7))
    sk["SK-7"] = d / "SK-7_webbing.png"
    sk_webbing(pk, sk["SK-7"])
    sk["SK-8"] = d / "SK-8_hinge_eye.png"
    sk_hinge_eye(pk, sk["SK-8"])
    sk["SK-9"] = d / "SK-9_aft_corner_keeper_stack.png"
    sk_keeper_stack(pk, sk["SK-9"])
    sk["SK-10"] = d / "SK-10_roll_top_clip.png"
    sk_roll_clip(pk, sk["SK-10"])
    sk["SK-11"] = d / "SK-11_meat_straps.png"
    sk_meat_straps(pk, sk["SK-11"])
    sk["SK-12"] = d / "SK-12_B-25_bridle.png"
    sk_bridle(pk, sk["SK-12"])
    return sk


# ============================================================================ tech pack content (PDF: huntkit.manufacturing)
def techpack_design(pk: dict, sk: dict) -> MF.TechPack:
    """CORRIE F rev 3 content for ``huntkit.manufacturing.tech_pack`` (CONTRACTS.md section 5): cover, equipment, flats,
    BOM, cutting plan, op sequence, load points, QC, packaging, costing, delta register, assumptions."""
    from huntkit.manufacturing import h2, image, page_break, para, space, table
    ctx, c = pk["ctx"], pk["costing"]
    ck = checks(pk)
    S = MF.Section
    n_web = sum(w['qty'] for w in ctx.rs.webbing if not ('kit S' in w['kit'] or 'kit L' in w['kit']))
    cover = [
        ["Pieces", f"{len(ctx.rs.pieces)} piece types; {sum(p.quantity for p in _fabric_pieces(ctx.rs))} fabric / sheet "
                   f"pieces; {n_web} webbing / cord / elastic"],
        ["Ledger reconciliation", f"{ck['recon_rows']} rows, {ck['recon_unmatched']} unmatched, "
                                  f"{ck['recon_pieces_without_row']} pieces without a row; hardware rows unmapped: "
                                  f"{len(ck['unmapped_hardware'])}"],
        ["Mass from pattern areas", f"{pk['mass']['pattern_fabric_alt_g']} g vs ledger {pk['mass']['ledger_fabric_g']} g "
                                    f"({pk['mass']['mass_delta_pct']:+.2f} %, limit 3 %); bag ledger base "
                                    f"{pk['mass']['base_g']} g / as hunted {pk['mass']['as_hunted_g']} g / meat trip "
                                    f"{pk['mass']['meat_trip_g']} g (team B basis); primary fabrics "
                                    f"{pk['mass']['primary_minus_alt_g']:+.1f} g"],
        ["Thread", f"{ck['thread_bag_g']} g in the bag from the op lengths (no cone waste); ledger books "
                   f"{ck['thread_ledger_g']} g; purchase quantities in the BOM include {THREAD_WASTE:.0%} cone waste"],
        ["Operations", f"{ck['ops']} ops; beginner {c['proto_hours']} h; factory SAM {c['sam_min']:.0f} min"],
        ["One bag to buy (prototype)", f"${c['prototype_usd']:.0f} (1-bag markers, shop increments; costing section)"],
        ["Mass targets, PRIMARY fabrics (QC-14)", f"base {pk['mass']['primary_base_g']:.0f} g / as hunted "
                                                   f"{pk['mass']['primary_as_hunted_g']:.0f} g / meat trip "
                                                   f"{pk['mass']['primary_meat_trip_g']:.0f} g, +/- {QC14_TOL_PCT:.0f} %"],
        ["Pre-cut reviews (BL-040 / 041 / 043)", ("0 blockers, 0 majors open: ready to cut after the G2 / G3 gates"
                                                 if ready_to_cut() else ("third-review items open: NOT ready to cut"
                                                 if open_findings() else "third-review findings all fixed (BL-042 / "
                                                 "043 / 044); a FOURTH independent review is due: NOT ready to cut"))],
        ["Cost a bag (production)", f"materials ${c['material_usd_primary']:.0f} primary / ${c['material_usd_alternate']:.0f} "
                       f"alternate; + CMT: US ${c['landed_usd']['us_contract_usd_min']:.0f}, Asia "
                       f"${c['landed_usd']['asia_contract_usd_min']:.0f} (ASSUMPTIONS)"],
        ["Load points", f"{ck['load_points']}; lowest SF {ck['min_sf']} ({ck['min_sf_point']}); every load point "
                        "is released by a proof test (section 8)"],
        ["HOLD", "; ".join(ck["holds"]) or "none"],
        ["Pattern flags", "; ".join(ck["box_mismatches"]) or "none"],
        ["Volatile (re-run on a pattern change)", "; ".join(ck["volatile"])],
        ["Fabric sets", "PRIMARY = today's fabrics (build this). ALTERNATE = team B set (ULTRAGrid body, 70D collar, "
                        "ULTRA 200X floor) only after gates ALT-1..3 and FS-O5."],
        ["Owner rules", "No hook-and-loop; coil zips; mostly solid colours, camo on accents only; width <= 394 mm "
                        "(15.5 in); 85 L +/- 3."]]
    secs = []
    secs.append(S("2. Equipment and stitch standards", [
        table([["ID", "Machine / tool"]] + [[k, v] for k, v in MACHINES.items()], [18, 227]), space(3),
        table([["Use", "Thread (record)", "Needle", "SPI (mm)", "Stitch"],
               ["40D-100D, mesh, silpoly", THREAD["light"], NEEDLE["light"] + " / " + NEEDLE["mesh"],
                f"{SPI['light']} ({25.4 / SPI['light']:.1f})", "301"],
               ["body seams, zips, Hypalon perimeters, B-11 sew-down", THREAD["body"], NEEDLE["body"],
                f"{SPI['body']} ({25.4 / SPI['body']:.1f})", "301"],
               ["load box-X", THREAD["box"], NEEDLE["box"], f"{SPI['box']} ({25.4 / SPI['box']:.1f})",
                "301 path (LK-1900 / AMS-210EN programmed)"],
               ["bartacks, elastic laps", THREAD["body"], NEEDLE["body"], "LK-1900 std", "304"]],
              [50, 40, 75, 25, 55]), space(2), para(NEEDLE_RULE), space(2), para(PROTO_MACHINE_MIN),
        para(f"Seam efficiency: a 301 seam is taken at {SEAM_EFF:.0%} of the weaker strip (clothsim/fabrics.yaml, "
             "attach_system.SEAM_EFF); box-X capacity = 0.5 x 1.5 x thread break / stitch length x path "
             "(attach_system.box_x, ETA_BOX 0.5 ASSUMPTION)."), space(2),
        table([["Code", "Seam construction"]] + [[k, v] for k, v in SEAMS.items()], [18, 227]), space(2),
        table([["Jig", "What"]] + [list(j) for j in JIGS], [18, 227])]))
    flats = []
    render = ROOT / "docs" / "screens" / "20261112_BL030_2.png"
    if render.exists():
        flats += [image(render, 200, 120), para("Render of rev 3 (docs/screens/20261112_BL030_2.png, BL-030): side view, "
                                                "lid and crown straps. Colours / camo placement as drawn there."),
                  page_break()]
    fl = ("SK-3", "SK-8", "SK-4", "SK-5", "SK-9", "SK-10", "SK-6")
    for i, k in enumerate(fl):
        flats += [image(sk[k])] + ([page_break()] if i < len(fl) - 1 else [])
    secs.append(S("3. Flats and piece maps (from the pattern pieces)", flats))
    secs.append(S("4. Bill of materials (one bag, full build, crown kit M)", [
        para("Production qty = 10-bag marker + 3 % lay loss where part A nested one, else net / utilisation "
             "(ASSUMPTION). Prototype (1-bag marker) quantity in the Proto column. Waste % = gross / net - 1. Thread: "
             "purchase quantity includes the cone waste; the grams in the bag (notes) do not."),
        MF.bom_table(pk["bom"])]))
    cut = [["Set", "Material", "Pieces", "1-bag m", "eff", "10-bag m / bag", "eff", "Lay", "Prototype", "Production"]]
    for r in pk["cutting"]:
        if r["set"] != "webbing":
            cut.append([r["set"], r["material_id"], r["pieces"], r["marker_1bag_m"] or "", r["eff_1bag"] or "",
                        r["marker_10bag_m_per_bag"] or "", r["eff_10bag"] or "", r["lay"], r["prototype_cut"],
                        r["production_cut"]])
    web = [["ID", "Use", "Material", "Length mm (in)", "Qty", "Kit", "Source"]]
    for w in ctx.rs.webbing:
        web.append([w["id"], w["use"], w["material_id"], f"{w['length_mm']:.0f} ({w['length_mm'] / IN:.1f})", w["qty"],
                    w["kit"], w["source"]])
    secs.append(S("5. Cutting plan (pattern list, markers, cut lengths)", [
        para("Markers: ../patterns/markers/. Cut windows, slots and slits first; knife clockwise from the grain "
             "arrow; notches 6 mm. Ply height: woven nylon 24, laminates / mesh / silpoly 12, camo single ply "
             "(one way, print placement), sheet goods laser single sheet."),
        table(cut, [14, 30, 50, 11, 9, 14, 9, 25, 40, 50]), space(3), h2("Webbing, cord and elastic cut lengths"),
        table(web, [14, 75, 35, 22, 8, 30, 60])]))
    secs.append(S("6. Sewing operation sequence", [
        para("All flat work before the bag becomes 3D. Clips, never pins, in coated fabric. Swatch every new stack. "
             "Load points only after their proof test passes (section 8). V = volatile (re-run on a pattern change)."),
        MF.ops_table(pk["ops"])]))
    lpr = [["Point", "Part", "Where", "Pattern", "Stitches", "Machine", "Thread / needle", "Load N (lbf)", "Source",
            "Capacity N", "Governs", "SF", "Proof"]]
    for r in pk["load_points"]:
        lpr.append([r["point"], r["part"], r["where"], r["pattern"], r["stitches"] or "", r["machine"],
                    f"{r['thread']} / {r['needle']}", f"{r['load_n'] or '-'} ({r['load_lbf'] or '-'})",
                    r["load_source"], r["capacity_n"] or "", r["governs"], r["sf"] or "",
                    r["proof"] + (f"; {r['note']}" if r["note"] else "")])
    secs.append(S("7. Load points: bartack and box-X specification", [
        para("Box sizes are the box-X marks drawn on the pattern pieces. Load = factored design load from the record "
             "named (x 3.0 on the 1 g simulation per HA-LS-1 rev C). Capacity by attach_system rules. Proof = the test "
             "that releases the point (register)."),
        table(lpr, [22, 18, 26, 28, 10, 18, 26, 14, 30, 12, 18, 7, 30]), page_break(),
        image(sk["SK-1"]), page_break(), image(sk["SK-2"]), page_break(), image(sk["SK-7"], 250, 170)]))
    secs.append(S("8. QC checkpoints, release tests, defects", [
        table([["ID", "Stage", "Check", "Method", "Pass", "Frequency"]] +
              [[q["id"], q["stage"], q["check"], q["method"], q["pass"], q["frequency"]] for q in pk["qc"]],
              [12, 18, 35, 60, 85, 35]), page_break(),
        h2("Physical tests that gate release"),
        table([["ID", "Test", "Gates", "Steps", "Pass / fail", "Source"]] +
              [[t["id"], t["title"], t["gates"], t["steps"], t["pass"], t["source"]] for t in pk["tests"]],
              [13, 45, 40, 75, 55, 17]), page_break(),
        h2("Defect list"),
        table([["Defect", "Where", "Cause", "Prevent / fix", "Class"]] + [list(d) for d in DEFECTS],
              [60, 35, 50, 85, 15])]))
    secs.append(S("9. Packaging", [para(f"{i + 1}. {t}") for i, t in enumerate(PACKAGING)]))
    secs.append(S("10. Costing and hours", [
        table([["Step", "Beginner h"]] + [[k, f"{v:.2f}"] for k, v in c["proto_hours_by_step"].items()] +
              [["Total (incl. one-off set-up)", f"{c['proto_hours']}"]], [100, 30]), space(3),
        table([["Scenario", "SAM min", "Labour $", "CMT incl. overhead $", "Materials $", "Total $"]] +
              [[k, f"{c['sam_min']:.0f}", f"{c['labour_usd'][k]:.2f}", f"{c['cmt_usd'][k]:.2f}",
                f"{c['material_usd_primary']:.2f}", f"{c['landed_usd'][k]:.2f}"] for k in LABOUR],
              [60, 20, 25, 35, 25, 25]), space(2),
        para(f"Lid on the drafted pattern {c['lid_hours_drafted']} h (booked {c['lid_hours_booked']} h). Alternate "
             f"set materials ${c['material_usd_alternate']:.2f}. Assumptions: {'; '.join(c['assumptions'])}.")]))
    secs.append(S("11. Release delta register: rows this release resolves", [
        table([["RD", "Status", "Evidence (checked by the script)", "Still open"]] +
              [[d["id"], d["status_after_rev3_package"], d["evidence"], d["still_open"]] for d in pk["delta"]],
              [14, 25, 110, 96])]))
    secs.append(S("12. Assumptions that govern", [
        table([["ID", "Assumption", "Settled by"]] + [list(a) for a in ASSUMPTIONS], [30, 125, 90])]))
    return MF.TechPack(
        title=TITLE, date=DATE, footer=f"{TITLE} - tech pack - {DATE} - generated, do not edit",
        subtitle=(f"Revision 3, door D2, crown kit M shown (S / L cut lists in cutting_plan.csv). Issued {DATE}. "
                  "Generated by designs/pack_5200/mfg_corrie_f_rev3.py from the pattern module; patterns, DXF and "
                  "markers in ../patterns/. Units mm, N, g (imperial alongside)."),
        cover=cover,
        contents="Contents: 1 cover; 2 equipment and stitch standards; 3 flats / piece maps; 4 BOM; 5 cutting plan; "
                 "6 operation sequence; 7 load points and sketches; 8 QC, release tests, defects; 9 packaging; "
                 "10 costing; 11 delta register; 12 assumptions.",
        sections=secs)


# ============================================================================ previews and screenshots
def preview(pdf: Path, out: Path) -> list[Path]:
    d = out / "preview"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("techpack-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", str(PREVIEW_DPI), str(pdf), str(d / "techpack")], check=True)
    return sorted(d.glob("techpack-*.png"))


def screenshots(pdf: Path, sk: dict) -> list[Path]:
    """Phone-readable PNGs (<= 1.5 MB): cover page, an op-sequence page, SK-1, SK-5 (pages at 110 dpi)."""
    from PIL import Image as PI
    SCREENS.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "preview" / "_hi"
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-f", "1", "-l", "1", str(pdf), str(tmp / "cover")], check=True)
    # first op-sequence page: find it by text
    import pypdf
    rd = pypdf.PdfReader(str(pdf))
    op_page = next((i + 1 for i, pg in enumerate(rd.pages) if "6. Sewing operation sequence" in (pg.extract_text() or "")), 2)
    subprocess.run(["pdftoppm", "-png", "-r", "110", "-f", str(op_page + 2), "-l", str(op_page + 2), str(pdf),
                    str(tmp / "ops")], check=True)
    srcs = [sorted(tmp.glob("cover*.png"))[0], sk["SK-8"], sk["SK-9"], sk["SK-10"], sk["SK-11"], sorted(tmp.glob("ops*.png"))[0],
            sk["SK-12"]]                                              # BL-043: the B-25 topology
    out = []
    for i, s_ in enumerate(srcs, 1):
        dst = SCREENS / f"{DATE}_{TOPIC}_{i}.png"
        with PI.open(s_) as im:
            im = im.convert("RGB")
            if im.width > 1800:
                im = im.resize((1800, int(im.height * 1800 / im.width)))
            im.save(dst, optimize=True)
        assert dst.stat().st_size <= 1.5e6, dst
        out.append(dst)
    for f_ in tmp.glob("*.png"):
        f_.unlink()
    tmp.rmdir()
    return out


# ============================================================================ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="build and print the checks; write nothing")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-screens", action="store_true")
    a = ap.parse_args(argv)
    pk = package()
    ck = checks(pk)
    print(json.dumps(ck, indent=1, default=str))
    if a.check:
        return pk
    out = Path(a.out)
    files = write_files(pk, out)
    sk = sketches(pk, out)
    pdf = MF.tech_pack(techpack_design(pk, sk), out / "techpack_corrie_f_rev3.pdf", strict=True)
    pv = preview(pdf, out)
    print(f"wrote {len(files)} files, {len(sk)} sketches, {pdf} ({len(pv)} pages previewed)")
    if not a.no_screens and out == OUT:
        for s_ in screenshots(pdf, sk):
            print("SCREEN", s_)
    return pk


if __name__ == "__main__":
    main()
