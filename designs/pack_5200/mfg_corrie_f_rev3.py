"""BL-032 part B: CORRIE F rev 3 manufacturing package (manufacturing-engineer, 2026-11-13).

    python designs/pack_5200/mfg_corrie_f_rev3.py            # regenerate the package
    python designs/pack_5200/mfg_corrie_f_rev3.py --check    # build + print the checks, write nothing

Writes ``outputs/release/pack5200_corrie_f_rev3/manufacturing/`` (BOM, cutting plan, sewing operation sequence,
bartack / load-point table, QC sheet, release tests, defect list, packaging, costing, delta-register close-out, the
tech pack PDF and its raster preview) and phone screenshots ``outputs/screens/20261113_BL032B_<n>.png``.

Everything is regenerated from the pattern module ``patterns_corrie_f_rev3.build()`` (read only) and the released
part A markers (``patterns/markers/markers.json``). Nothing here is hand-typed geometry: seam lengths come from the
pattern's own seam pairs, placements (B-22 x, FP width, swell windows, B-27 slits) from the pieces, cut lengths from
``RevSet.webbing``, the lid operations from ``patterns_corrie_f_rev3.lid_hours``. When BL-033 moves the hinge swell
window, the B-22 tab, the FP pockets or adds the F-01 fly, re-run this script; the ops marked ``volatile`` are the ones
that change.

Shared-code contracts: ``SewingOp`` and ``BOMLine`` carry the field names of CONTRACTS.md section 5 so they can move to
``huntkit.manufacturing`` (empty today) unchanged. Load capacities use ``huntkit.gendesign.attach_system`` (read only).
Units: mm, N, g, USD; inches / lb / oz / yd in the documents.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import patterns_corrie_f_rev3 as P  # noqa: E402  (sets sys.path for concepts/ and the repo root)
from huntkit import materials as MAT  # noqa: E402
from huntkit.gendesign import attach_system as AS  # noqa: E402

ROOT = P.ROOT
REL = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3"
PAT = REL / "patterns"
OUT = REL / "manufacturing"
SCREENS = ROOT / "outputs" / "screens"
DATE = "20261113"
TOPIC = "BL032B"
TITLE = "CORRIE F rev 3 (door D2) - 5200 cu in hunting pack bag"
REGISTER = ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv"
YD = 914.4
IN = 25.4

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

MACHINES = {
    "WF1": "Single-needle compound-feed walking foot lockstitch, Juki DU-1181N (or LU-1508N). Prototype: any walking "
           "foot that runs Nm 110 + tex 90 cleanly (e.g. a portable walking-foot machine).",
    "WF2": "Heavy single-needle walking foot lockstitch, large hook, Juki DNU-1541S (or LU-1561/2210 class): webbing "
           "stacks, Hypalon, tex 135 box-X. Prototype: WF1 hand-cranked through the thick spots.",
    "BT": "Computer bartacker Juki LK-1900BN (ISO 301 path / 304 zigzag, programmable, 40 x 30 mm field): every "
          "25 mm box-X and the slit bartacks. Prototype: box-X on WF2 with the J1 template.",
    "PS": "Programmable pattern sewer Juki AMS-210EN (220 x 100 mm field) with a webbing clamp: the 38 mm box-X that do "
          "not fit the LK-1900 field (HE, T3, B-24). Prototype / small shop: WF2 with the J1 template.",
    "ZZ": "Zigzag lockstitch (ISO 304), Juki LZ-2290 class or a portable straight / zigzag walking foot: elastic laps.",
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
LABOUR = {"us_contract_usd_min": 0.85, "asia_contract_usd_min": 0.12}   # ASSUMPTION LABOUR (loaded CMT minute)
OVERHEAD = 0.25                        # ASSUMPTION: contract overhead + margin on CMT
PRICE_ASSUMED = {   # items with no cost in a record: (usd, per, why)
    "elastic_25mm": (0.60, "m", "ASSUMPTION ELASTIC-COST, no record"),
    "elastic_6mm": (0.25, "m", "ASSUMPTION ELASTIC-COST, no record (fly hem)"),
    "slider_10": (0.80, "unit", "ASSUMPTION SLIDER: #10 coil slider, metal pull"),
    "slider_5": (0.40, "unit", "ASSUMPTION SLIDER: #5 coil slider"),
    "cam_25mm_al": (6.00, "unit", "ASSUMPTION CAM25 part (MT-3); no record"),
    "triglide_25mm": (0.30, "unit", "ASSUMPTION; attach_system.TRIGLIDE_G mass"),
    "pom_toggle": (0.30, "unit", "ASSUMPTION; attach_system.TOGGLE_G 3 g, POM 30 x 8 x 5"),
    "tpu_hook_sleeve": (0.20, "unit", "ASSUMPTION"),
    "rubber_pull_sleeve": (0.15, "unit", "ASSUMPTION"),
    "basting_tape_6mm": (0.05, "m", "ASSUMPTION"),
    "seam_sealer": (0.80, "bag", "ASSUMPTION: 10 ml of a silicone seam sealer"),
    "label_set": (0.60, "set", "ASSUMPTION: size / care / ID label + hang tag + warning card"),
    "polybag_carton": (0.90, "bag", "ASSUMPTION: 2 recycled poly bags + 1/10 carton"),
}


# ============================================================================ contract-shaped records
@dataclass
class SewingOp:            # CONTRACTS.md section 5 fields first
    seq: str
    operation: str
    machine: str
    stitch_type: str
    spi: float | None
    thread_id: str
    needle: str
    attachment: str
    notes: str
    time_s: float           # factory SAM, s
    step: str = ""
    pieces: str = ""
    seam: str = ""
    length_mm: float = 0.0
    bartack: str = ""
    sketch: str = ""
    qc: str = ""
    volatile: str = ""
    proto_h: float = 0.0
    per_bag: bool = True


@dataclass
class BOMLine:             # CONTRACTS.md section 5: material id, qty, unit, waste factor, cost
    section: str
    item: str
    material_id: str
    qty: float
    unit: str
    waste_pct: float
    unit_cost_usd: float | None
    cost_usd: float | None
    alt_material_id: str = ""
    alt_qty: float | None = None
    alt_cost_usd: float | None = None
    kit: str = ""
    source: str = ""
    notes: str = ""
    proto_qty: float | None = None


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
        "fp_clamped": rs.geo.get("fp_clamped_mm"), "fp_margin": rs.geo.get("fp_min_margin_mm"),
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


# hardware: (key, item, record or ASSUMPTION key, qty, unit, kit, ledger row prefix, frame_side)
def hardware_table(ctx: Ctx) -> list[tuple]:
    hw = {h["item"]: h for h in ctx.rs.hardware}
    zl = {k: v["length_mm"] for k, v in hw.items() if v["material_id"].startswith("coil")}
    z10 = sum(v for k, v in zl.items() if "#10" in k) / 1000.0
    z5 = sum(v for k, v in zl.items() if "#5" in k) / 1000.0
    n5 = sum(1 for k in zl if "#5" in k)
    ll = sum(v["qty"] for k, v in hw.items() if v["material_id"] == "ladder_lock_25mm_heavy")
    return [
        ("zip10", "#10 coil zip chain, door D2 (2 sliders)", "coil_zipper_10", round(z10, 3), "m", "base",
         "D2 door zip", False),
        ("slider10", "#10 coil slider, metal pull (door)", "slider_10", 2, "unit", "base", "D2 door zip", False),
        ("zip5", f"#5 coil zip chain: lid, IMP-4, F-02 ({n5} zips)", "coil_zipper_5", round(z5, 3), "m",
         "base,as_hunted", "IMP-4 / add-on crown_lid / F-02", False),
        ("slider5", "#5 coil slider + pull", "slider_5", n5, "unit", "base,as_hunted", "IMP-4 / crown_lid", False),
        ("pull_cord", "door pull cord 3 mm Dyneema, 2 x 0.15 m (ASSUMPTION length)", "dyneema_cord_3mm", 0.30, "m",
         "base", "door: 2 cord pulls", False),
        ("pull_sleeve", "rubber pull sleeve", "rubber_pull_sleeve", 2, "unit", "base", "door: 2 cord pulls", False),
        ("ghook", "rated 25 mm aluminium G-hook: IM1, IM2 (2) + W1-W3 (3) + bow riser (1)", "g_hook_25mm_aluminium",
         6, "unit", "base", "IM-hooks / W-hw / BL-010 S9 / bow riser", False),
        ("ghook_x", "rated 25 mm aluminium G-hook: W haul extenders", "g_hook_25mm_aluminium", 3, "unit", "meat_trip",
         "BL-031: W1-W3 haul extenders", False),
        ("cara", "wiregate carabiner 22 kN: IM3 bag hooks (2) + IM3 meat free end (1)", "carabiner_wiregate_22kn", 3,
         "unit", "base", "BL-010 A1 / BL-010 S2", False),
        ("cara_x", "wiregate carabiner 22 kN: B-24 float links", "carabiner_wiregate_22kn", 2, "unit", "meat_trip",
         "BL-010 S12", False),
        ("ll_heavy", "heavy 25 mm ladder lock: B-28 (4) + guys (2) + W1-W3 (3)", "ladder_lock_25mm_heavy", ll, "unit",
         "base,as_hunted", "W-hw / BL-010 A3 / crown_straps", False),
        ("cam", "25 mm aluminium cam buckle: IM1-IM3 (3) + US1/US2 (2)", "cam_25mm_al", 5, "unit", "base",
         "IM-cams / US-cams", False),
        ("triglide", "25 mm tri-glide: US keepers (2) + guy keepers (2)", "triglide_25mm", 4, "unit", "base",
         "US-tg / guy ladder locks", False),
        ("toggle", "POM toggle 30 x 8 x 5: B-28 rear (2) + guy loops (2)", "pom_toggle", 4, "unit", "base,as_hunted",
         "crown_straps / BL-004 REC guy bar loops", False),
        ("srb", "25 mm side-release buckle (roll top)", "buckle_side_release_25mm", 2, "unit", "base", "roll:", False),
        ("cordlock", "spring cord lock (E-5 pole grip)", "cord_lock_spring", 1, "unit", "base", "E-5 pole quiver", False),
        ("tpu_sleeve", "TPU sleeve on the IM3 carabiner (2)", "tpu_hook_sleeve", 2, "unit", "base",
         "attachment: TPU hook sleeves (4) less BL-004 REC (2)", False),
        ("fairlead", "printed fairleads (8), 7075 pins (8), UHMWPE sleeves (8), US anchors, lifter keepers",
         "frame kit", 1, "set", "base", "attachment: printed fairleads ...", True),
    ]


HW_LEDGER_KEYS = ("D2 door zip", "door: 2 cord pulls", "IM-hooks", "IM-cams", "US-anchor", "US-cams", "US-tg",
                  "B-24-hooks", "B-24-thr", "W-hw", "BL-010 S2", "BL-010 S9", "BL-010 S12",
                  "attachment: printed fairleads", "attachment: 7075 pins", "attachment: UHMWPE sleeves",
                  "attachment: bag hooks, 38 mm", "attachment: TPU hook sleeves", "attachment: elastic keepers",
                  "attachment: lifter tri-glide", "attachment system: bag hooks 1500", "attachment system: thread",
                  "BL-010 A1", "BL-010 A3")


def unmapped_hardware_rows(ctx: Ctx) -> list[str]:
    """Ledger rows booked as hardware that this BOM's hardware table does not cover (a ledger change)."""
    return [r["row"] for r in ctx.rec["rows"] if r["status"] == "hardware"
            and not any(r["row"].startswith(k) for k in HW_LEDGER_KEYS)]


def hardware_bom(ctx: Ctx) -> list[BOMLine]:
    out = [BOMLine("hardware", f"UNMAPPED ledger hardware row: {r}", "-", 0, "-", 0.0, None, None,
                   source="ledger (BL-033?)", notes="add to hardware_table()") for r in unmapped_hardware_rows(ctx)]
    for key, item, rec, qty, unit, kit, led, frame in hardware_table(ctx):
        if frame:
            out.append(BOMLine("hardware_frame_side", item, rec, qty, unit, 0.0, None, None, kit=kit,
                               source=f"ledger rows '{led}'", notes="frame kit (H1 package), not sewn; listed so the "
                                                                    "bag kit is complete"))
            continue
        if rec in PRICE_ASSUMED:
            uc, src = PRICE_ASSUMED[rec][0], PRICE_ASSUMED[rec][2]
        else:
            uc = cost_per(rec, unit) if unit == "m" else (float(mat(rec).cost_usd["value"]) if mat(rec) and mat(rec).cost_usd else None)
            src = f"record {rec}"
        out.append(BOMLine("hardware", item, rec, qty, unit, 0.0, uc, round(qty * uc, 2) if uc is not None else None,
                           alt_material_id="same", kit=kit, source=f"{src}; ledger rows '{led}'"))
    return out


def thread_bom(ops: list[SewingOp]) -> list[BOMLine]:
    by: dict = {}
    for o in ops:
        if o.thread_id.startswith("bonded") and o.length_mm:
            by[o.thread_id] = by.get(o.thread_id, 0.0) + o.length_mm / 1000.0 * THREAD_FACTOR
    out = []
    for tid, m in sorted(by.items()):
        q = m * (1 + THREAD_WASTE)
        uc = cost_per(tid, "m")
        g = q * float(mat(tid).require("mass_g_m"))
        out.append(BOMLine("thread", f"{tid} (needle + bobbin)", tid, round(q, 1), "m", THREAD_WASTE * 100, uc,
                           round(q * uc, 2) if uc else None, alt_material_id="same", kit="all",
                           source=f"record {tid}; sum of op stitch lengths x {THREAD_FACTOR} (ASSUMPTION THREAD-FACTOR)",
                           notes=f"{g:.1f} g in the bag (ledger books thread 2.0 g + B-24 2.0 g)"))
    return out


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
def load_points(ctx: Ctx) -> list[dict]:
    """Every sewn load point: pattern box size, stitch count, thread / needle, the factored load from the record that
    sets it, the capacity (attach_system rules) and the proof test that releases it."""
    rs = ctx.rs
    bx = AS.box_x
    st = 25.4 / SPI["box"]
    body_alt = ctx.rsA.pieces["B-02h"].material_id
    body = rs.pieces["B-02h"].material_id

    def box(pid, default=None):
        b = boxes_of(rs.pieces[pid]) if pid in rs.pieces else []
        return b if b else ([default] if default else [])

    rows = []

    def add(pt, pid, where, w, h, load_n, load_src, proof, extra_caps=None, kind="box", note="", vol=""):
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
                     "volatile": vol})

    guy = 288.0       # corrie_f_body.md 13.5: port guy 96.1 N at 1 g x 3.0 (23 in full)
    b22 = AS.patch_seam(50.0, body, "hypalon_coated_nylon")["cap_n"]
    b22a = AS.patch_seam(50.0, body_alt, "hypalon_coated_nylon")["cap_n"]
    for w, h, lab in box("TG"):
        add("port guy, toggle end", "TG", "TG toggle loop (B-25 tab side)", w, h, guy,
            "corrie_f_body.md 13.5: 96.1 N x 3.0", "LL-H (366 N, toggle-loop pull, loadpath A3)")
    for w, h, lab in box("LLT"):
        add("port guy, bag end", "LLT + B-22 + B-02h", f"inside the hinge band at x +/-{ctx.rs.geo['b22']['placed_x']}",
            w, h, guy, "corrie_f_body.md 13.5: 96.1 N x 3.0", "LL-H; PT-5 (lock + keeper)",
            {"B-22 perimeter 50 mm (primary body)": b22}, note=f"alternate body fabric: B-22 seam {b22a:.0f} N",
            vol="BL-033 B-22 x")
    add("port guy, B-27 slit ends", "B-01", f"both ends of each slit, z {P.F.PORT_Z[0]:.0f} / {P.F.PORT_Z[1]:.0f}",
        0, 0, None, "no rated load (lap only); port mock-up: 100 N guy pull through the lap", "port mock-up (13.9)",
        kind="BT-S")
    for w, h, lab in box("B-28t"):
        add("crown strap tabs (6)", "B-28t", "front: hinge band (outside); rear: through the B-25 toggle; B-25 second "
            "fold", w, h, guy, "corrie_f_body.md 15.2: 288 N envelope (port guy) if a crown strap ever holds the top",
            "LL-H (heavy lock slip 366 N covers 288 N; BL-031 dropped the 20 mm gate)")
    for pid, where in (("B-02h", "B-28 front tab box on the hinge band"),):
        for w, h, lab in [b for b in box(pid) if "B-28" in b[2]]:
            add("crown strap front tab on the band", pid, where, w, h, guy, "as above", "LL-H")
    add("B-25 bridle tab folds (4)", "B-25", "toggle tab + second fold, each side (not drawn on the pattern)", 21, 20,
        guy, "corrie_f_body.md 13.5 (guy) / 15.2 (crown strap)", "LL-H toggle-loop pull 366 N",
        note="ASSUMPTION B25-BOX: box-X 21 x 20 closes each fold; pattern shows folds only")
    for w, h, lab in box("GBL"):
        add("guy bar loop", "GBL", "round the crown top bar", w, h, 244.0, "loadpath_verification A3: 244 N", "LL-H")
    t3 = box("T3")
    for w, h, lab in t3:
        add("IM3 bag-hook tongue", "T3", lab.replace(" box-X", ""), w, h, 1702.0,
            "loadpath_verification A1: IM3 1702 N factored (guys-off misuse)", "PT-1 2553 N carabiner; PT-2 2553 N",
            {"webbing on carabiner bed": AS.web_pin("poly_webbing_38mm"), "carabiner (PT-1 basis: 0.5 x 8 kN minor axis)": 4000.0})
    add("B-17 IM3 tab perimeter (double row)", "B-17", "OUTSIDE B-01 at x +/-115, z 385-455", 0, 0, 1702.0,
        "loadpath_verification A1", "PT-2 2553 N on the 70 mm tab",
        {"perimeter 80 mm loaded, 2 rows": AS.patch_seam(80.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"]},
        kind="perim", note="perimeter 3 / 9 mm, 8 SPI tex 90; SF from the 90 x 110 basis, PT-2 settles the 70 mm tab")
    for w, h, lab in box("IME"):
        add("IM fairlead eyes (6)", "IME", "frame side, captive in the printed fairleads", w, h, 1702.0,
            "IM3 eye carries the bag hook (A1 1702 N); IM1/IM2 605 N (S1)", "MT-1 analogue at 38 mm; IM3-EP 2553 N")
    for w, h, lab in box("HE"):
        add("hinge eye", "HE + B-18 + B-01", "x +/-115, eye top z 60", w, h, 795.0,
            "loadpath_verification A5: 795 N", "PT-3 1530 N",
            {"B-18 seam (80 mm, B-05 strip)": AS.patch_seam(80.0, "cordura_500d_nylon66", "hypalon_coated_nylon")["cap_n"]},
            vol="BL-033 hinge window vs B-18")
    for pid in ("IM1", "IM2", "IM3"):
        add(f"{pid} end loop", pid, "left end loop (girth hitch on the eye); not drawn as a box on the pattern", 21, 25,
            605.0, "loadpath_verification S1: 605 N", "MT-1 908 N",
            note="ASSUMPTION IM-BOX: box-X 21 x 25 closes the 60 mm loop (MT-1 specimen)")
    add("US1/US2 sewn eye", "US", "eye on the left pin", 21, 25, 720.0, "loadpath_verification S5-S7: 720 N",
        "MT-1 1080 N", note="ASSUMPTION US-BOX: box-X 21 x 25; pattern has no marks")
    for pid in ("W1", "W2", "W3"):
        bb = box(pid) or [(21.0, 25.0, "ASSUMPTION W3-BOX (pattern draws the fold only)")]
        for w, h, lab in bb:
            add(f"{pid} G-hook end", pid, "G-hook fold 2 x 30 mm", w, h, 225.0, "loadpath_verification S9: 225 N",
                "LL-H 366 N; W-PULL 338 N", note=lab if "ASSUMPTION" in lab else "")
    for w, h, lab in box("WX"):
        add("W haul extender", "WX", lab.replace(" box-X 21x25", ""), w, h, 225.0,
            "ASSUMPTION WX-LOAD: same float-clamp load as S9 (225 N)", "LL-H; one extender pulled to 338 N")
    add("B-24 float link: hook end", "B-24", "38 mm, hook fold (pattern: folds only)", 34, 34, 941.0,
        "loadpath_verification S12 / RD-02: 941 N misuse", "PT-6 1410 N",
        {"carabiner": 4000.0, "webbing on bed": AS.web_pin("poly_webbing_38mm")},
        note="attach_system B-24: box-X 38 x 38 (hook) + 3 x 38 x 20 (loops); drawn here 34 wide (2 mm edge)")
    add("B-24 float link: 3 loops", "B-24", "loop beds 120 / 170 / 220 mm", 34, 20, 941.0, "as above", "PT-6 1410 N")
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
    ("camo caps", "Turn the short ends of each B-29f 10 mm and topstitch the cap on B-29e at its placement; long edges "
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
       "x 25 mm box-X loops (MT-1), 5 T3 tongues on 70 mm B-17 tabs on B-01 swatches (PT-2), 5 HE eyes on B-18 + B-01 "
       "+ B-05 swatches without binding (PT-3), 5 B-24 links (PT-6). The bag's load points are sewn only after these "
       "pass.", "box", seam="BOX + LSd (as the bag)", bartack="all load points", qc="TEST gates", hours=3.0, sketch="SK-1",
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
       f"finished {g['fp_finished_w']:.0f} mm), baste across top and bottom at 6 mm. Do not stretch the mesh.",
       "mesh", pieces="FP-a x2", seam="SSa", length=2 * 2 * g["fp_flat_w"], hours=2 * 2 * 2 * H["pivot"] + rate(4 * g["fp_flat_w"]),
       vol="BL-033 FP width", sketch="SK-5")
    op("FP mouth band and shock-cord channel", f"Sew FP-b to the FP-a top ({fp_seam:.0f} mm), fold the band on its "
       "fold line over the seam, edge-stitch 2 mm to form the channel; thread the shock cord (FP-cord) and bar it at "
       "both ends inside the side allowance.", "mesh", pieces="FP-a, FP-b x2, FP-cord", seam="SSa + EFa channel",
       length=2 * fp_seam * 2, hours=rate(4 * fp_seam), vol="BL-033 FP width", sketch="SK-2")
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
    op("F-02 fly base pocket", "Set the #5 zip (230 mm), turn the edges 10 mm. It is sewn to the floor in op 4.13. "
       "Placement on B-05 is NOT drawn on the pattern: centre it on the outside of B-05 (ASSUMPTION F02-PLACE).",
       "body", pieces="F-02, #5 zip", seam="ZIP + EFa", length=2 * 230 + piece_perim(f2),
       hours=H["zip_fixed"] + 0.23 * H["zip_m"] + rate(piece_perim(f2)), vol="BL-033 F-01")

    # ---------------------------------------------------------------- 2 small parts
    step("2 Small parts")
    b12 = rs.pieces["B-12"]
    op("B-12 strap-port patches on the swell crests", "Lay a B-12 (TPU face out) on the crest of each B-13x (6, not the "
       "hinge swells), sew the 3 mm perimeter, then cut the 45 x 12 slot through both and edge-stitch the slot.",
       "hyp", pieces="B-12 x6, B-13x x6", seam="LSd", length=6 * (piece_perim(b12) + 2 * (45 + 12)),
       hours=6 * rate(piece_perim(b12) + 114, "applique"), sketch="SK-2")
    sw_ids = ", ".join(f"{i} x{rs.pieces[i].quantity}" for i in g["swell_ids"])
    op("Box the swells", f"Sew the 4 corner folds of every swell ({sw_ids}): fold on 'box the corner', sew "
       "across. Practice: set one swell into a scrap window before touching B-01.", "body",
       pieces=sw_ids, seam="SSa", hours=g["swell_n"] * H["swell_boxed"] / 2, vol="BL-033 hinge window vs B-18")
    t3 = rs.pieces["T3"]
    op("T3 IM3 tongues onto B-17", "Fold each T3 45 mm round the bed (empty loop: the carabiner clips in later), box-X "
       "the loop; box-X the other end to the centre of a B-17 (Hypalon, coated face out).", "box",
       pieces="T3 x2, B-17 x2", seam="BOX", bartack="T3 (load table)", sketch="SK-1", qc="QC-07",
       hours=2 * 2 * H["bartack"], length=bl(34, 30, 2) + bl(34, 34, 2))
    op("IME fairlead eyes (frame kit)", "Fold each 38 mm IME at 100 mm into an eye, box-X 34 x 30. These go on the frame "
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
       hours=2 * rate(2 * piece_perim(b22), "applique"), vol="BL-033 B-22 x",
       sketch="SK-4", qc="QC-07")
    op("Guy ladder-lock tabs LLT through B-22", "Fold each LLT round the bar of a heavy 25 mm ladder lock, box-X "
       "through LLT + B-22 + B-02h at the drawn 'B-22 / guy LLT box' (drill corners).", "box",
       pieces="LLT x2, B-22, B-02h, 2 heavy ladder locks", seam="BOX", bartack="LLT + B-22 + B-02h",
       hours=2 * H["bartack"], vol="BL-033 B-22 x", sketch="SK-1, SK-4", qc="QC-07", length=bl(21, 25, 2))
    op("B-28 front tabs on the hinge band (OUTSIDE)", "Fold a B-28t round a heavy ladder lock, box-X it on the OUTSIDE "
       "of B-02h at the drawn 'B-28 front tab box' (ASSUMPTION B28-FACE: the strap runs on the aft face, so the tab is "
       "outside; part A README says 'inside').", "box", pieces="B-28t x2, B-02h, 2 heavy ladder locks", seam="BOX",
       bartack="B-28t", hours=2 * H["bartack"], sketch="SK-4", qc="QC-07", length=bl(25, 25, 2))
    hb = seam_mm(ctx, "hinge band | door (door hinge, z 650)")
    op("Hinge band to the door top", f"Join B-02h to the door top ({hb:.0f} mm), SSa2.", "body",
       pieces="B-02h, B-02door", seam="SSa2", length=2 * hb, hours=rate(hb))
    hbu = seam_mm(ctx, "hinge band R | blade U") + seam_mm(ctx, "hinge band L | blade U")
    op("Hinge band ends to the blade U", f"Join both short band ends to the blade tops ({hbu:.0f} mm total).", "body",
       pieces="B-02h, B-02u", seam="SSa2", length=2 * hbu, hours=rate(hbu) + 2 * H["pivot"])

    # ---------------------------------------------------------------- 4 main bag
    step("4 Main bag")
    op("Check the B-01 cut-outs", f"{g['windows']} swell windows, 2 B-27 slits ({g['port_slit_mm']:.0f} mm at x "
       "+/-52), IMP-2 keeper drill marks. All cut, corners awled.", "none", pieces="B-01", hours=0.1,
       vol="BL-033 hinge window vs B-18", qc="QC-03")
    op(f"Set the {g['swell_n']} swells into the B-01 windows", f"Swell base to window edge, INSIDE B-01, notch to "
       f"notch ({g['windows']} windows, {g['window_perim_mm']:.0f} mm of window edge in all; hinge windows: "
       f"{g['hinge_windows']}). Sew from the swell side, needle down at every corner.", "body",
       pieces=f"{sw_ids}, B-01", seam="SSa", length=g["window_perim_mm"], hours=g["swell_n"] * H["swell_boxed"] / 2,
       vol="BL-033 hinge window vs B-18", sketch="SK-3", qc="QC-08")
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
    op("B-18 doublers + HE hinge eyes", "Lay each B-18 INSIDE B-01 at the placement (lower edge to the floor seam "
       "line). Fold the HE eye (50 mm back, 25 mm eye; first 30 mm tri-folded to an 18 mm neck, 304 bartack across the "
       "neck), box-X 34 x 34 through HE + B-18 + B-01, then the B-18 perimeter rows on 3 sides (the 4th goes in the "
       "floor seam).", "box", pieces="HE x2, B-18 x2, B-01", seam="BOX + LSd",
       length=2 * 1.5 * piece_perim(b18) + bl(34, 34, 2),
       hours=2 * (2 * H["bartack"] + rate(1.5 * piece_perim(b18), "applique")), bartack="HE + B-18 + B-01",
       vol="BL-033 hinge window vs B-18", sketch="SK-1, SK-3", qc="QC-07")
    op("IMP-2 keeper tabs I2K on B-01", "Fold each I2K, bartack at the 2 'IMP-2 keeper tab' drill marks (inside).",
       "bt", pieces="I2K x2, B-01", seam="BT", hours=2 * H["bartack"])
    op("B-11 lash tabs (8)", "Bow riser + muzzle keepers. NOT placed on any rev 3 pattern piece (found in this "
       "ticket). HOLD until the pattern-maker draws the placements; sew-down box 301 tex 90 when placed.", "hyp",
       pieces="B-11 x8", seam="LSd", hours=8 * H["bartack"], notes="HOLD (pattern).")
    g3 = rs.pieces["B-03"]
    kb = rs.pieces["SH-01b"]
    op("Gusset flat work: kick bands", "SH-01b on each gusset foot at the 'kick band top' line, top edge turned 8 mm, "
       "topstitched; bottom and sides go in the seams.", "body", pieces="SH-01b x2, B-03 x2", seam="LSd",
       length=2 * kb.bounds(cut=False)[2], hours=rate(2 * kb.bounds(cut=False)[2], "applique"))
    op("Gusset flat work: FP pockets (both)", f"Sew each FP to its gusset at the placement, z {g['fp_z'][0]:.0f}-"
       f"{g['fp_z'][1]:.0f}, {g['fp_finished_w']:.0f} mm face; inner edge >= 9 mm off the frame seam (now "
       f"{g['fp_margin'] if g['fp_margin'] is not None else '-'} mm at the tightest; part A clamp "
       f"{g['fp_clamped'] or 0} mm). "
       "Bottom and sides 301, box pleats laid flat, bartack the 2 mouth corners.", "mesh", pieces="FP x2, B-03 x2",
       seam="LSd", length=2 * (g["fp_h"] * 2 + g["fp_finished_w"]), bartack="FP corners (BT-S)",
       hours=2 * (rate(2 * g["fp_h"] + g["fp_finished_w"]) + 2 * H["bartack"]), vol="BL-033 FP width",
       sketch="SK-5")
    op("Gusset flat work: IMP-8 (R only) and hose ports", f"IMP-8 cup at 'IMP-8 cup top (R only)'. Hose slots (both "
       f"gussets, z {g['hose_z']:.0f}): B-09p binding (TPU, laser-cut) laid over the slot, perimeter + slot edge "
       "stitched.", "body", pieces="IMP-8, B-09p x2, B-03 x2", seam="LSd",
       length=piece_perim(i8) / 2 + 2 * 2 * piece_perim(rs.pieces["B-09p"]),
       hours=rate(piece_perim(i8) / 2) + 2 * rate(2 * piece_perim(rs.pieces["B-09p"]), "applique"))
    s_r = seam_mm(ctx, "B-01 | gusset R (FP-R edge, pole-grip tab)")
    s_l = seam_mm(ctx, "B-01 | gusset L (2 hard-point loops, FP-L edge)")
    op("Frame-side box seams B-01 | gussets", f"R ({s_r:.0f} mm): E5 pole-grip tab at z {g['pole_tab_z']:.0f} and the "
       "B-26 shock-cord ends (15 mm in) inserted. L ({:.0f} mm): 2 HPL hard-point loops at z {:.0f} / {:.0f} "
       "inserted. Notch to notch every 50 mm; SSa2.".format(s_l, *g["hard_z"]), "body",
       pieces="B-01, B-03 x2, E5, E5-cord, B-26, HPL x2", seam="SSa-ins + SSa2", length=2 * (s_r + s_l),
       hours=rate(s_r + s_l) + 3 * H["bartack"], sketch="SK-5", qc="QC-08")
    s_br = seam_mm(ctx, "blade U | gusset R (aft corner)")
    s_bl = seam_mm(ctx, "blade U | gusset L (aft corner, 2 hard-point loops)")
    op("Aft corner seams blade U | gussets (closes the tube)", f"R and L ({s_br:.0f} / {s_bl:.0f} mm): 2 HPL loops in "
       "the L seam at the hard-point notches; 3 K-W keeper loops in each seam at W1-W3 heights (ASSUMPTION KW-PLACE: "
       "W heights z 80 / 250 / 420 from the frame lash points; not drawn). SSa2.", "body",
       pieces="B-02u, B-03 x2, HPL x2, K-W x6", seam="SSa-ins + SSa2", length=2 * (s_br + s_bl),
       hours=rate(s_br + s_bl) + 8 * H["bartack"], sketch="SK-5", qc="QC-08")
    fl = sum(seam_mm(ctx, n) for n in ("bottom | B-01 (hinge eyes in it)", "bottom | gusset R", "bottom | gusset L",
                                       "bottom | blade U kick strip"))
    if g["b16"]:
        b16 = rs.pieces["B-16"]
        L16 = 2 * b16.bounds(cut=False)[2]
        op("US floor channels B-16 on F-02", f"Turn both ends of each B-16 15 mm (left OPEN: the 25 mm under-strap "
           f"passes through), lay it across F-02's outer face on the drawn 'B-16 channel' lines (stations "
           f"{g['us_channels']['stations_mm'] if g['us_channels'] else '-'} mm), topstitch both long edges, bartack the "
           "4 corners.", "body", pieces=f"B-16 x{b16.quantity}, F-02", seam="LSd", length=b16.quantity * L16,
           hours=b16.quantity * (rate(L16, "applique") + 2 * H["bartack"]), vol="BL-033 ledger (US-chan)")
        us_txt = "US channels: on F-02 (op above)."
    else:
        us_txt = "US floor channels: NOT drafted (ledger row US-chan, not_drafted) - HOLD."
    op("Floor B-05 (F-02 first)", f"Sew F-02 to the outside of B-05. Then the floor ring ({fl:.0f} mm): B-01 edge "
       "first with the HE tails and the B-18 lower edges caught in it, then gussets, then the blade kick strip; "
       f"quarter notches matched, needle down at the 4 corners. SSa2. {us_txt}", "body",
       pieces="B-05, F-02, B-01, B-03 x2, B-02u", seam="SSa2",
       length=2 * fl + piece_perim(f2), hours=rate(fl) + H["ring"] + 4 * H["pivot"] + rate(piece_perim(f2), "applique"),
       qc="QC-08", vol="" if g["b16"] else "BL-033 ledger (US-chan)")

    # ---------------------------------------------------------------- 5 collar
    step("5 Collar and roll top")
    cr = seam_mm(ctx, "collar frame side | collar R") + seam_mm(ctx, "collar frame side | collar L")
    op("Collar tube", f"B-06f (ULTRA) to B-06 both sides ({cr:.0f} mm); I2T hang tab at the B-06f drill mark.", "light",
       pieces="B-06f, B-06, I2T", seam="SSa2", length=2 * cr, hours=rate(cr) + H["bartack"])
    hm = seam_mm(ctx, "hem back seam")
    ht = seam_mm(ctx, "hem | collar top (ring)")
    rt = [w for w in webs if w["id"] == "RT"][0]
    op("Roll-top hem with HDPE strips and clip straps", f"Close the hem back seam ({hm:.0f} mm). Sew the hem to the "
       f"collar top ring ({ht:.0f} mm), fold over the two B-07s HDPE strips and stitch closed (EFb). RT clip straps "
       f"({rt['length_mm']:.0f} mm) at each roll end: 60 mm sewn to the roll end, 30 mm round the side-release buckle "
       "bar, box-X.", "body", pieces="B-07, B-07s x2, B-06, RT x2, 2 SR buckles", seam="SSa + EFb + BOX",
       length=hm + 2 * ht + bl(21, 25, 2), hours=rate(hm) + rate(ht) + H["ring"] + 2 * H["bartack"], sketch="SK-2")
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
        kind = "box" if "bartack" in t else ("light" if "base" in t else "body")
        L = r["qty"] * 1000.0 if r["rate_h"] in (H["straight_m"], H["curved_m"], H["applique_m"], H["zip_m"]) else 0.0
        seam = ("DART" if "dart" in t else "ZIP" if "zip" in t else "BT" if "bartack" in t else
                "LSd" if ("channel" in t or "cap" in t) else "SSa2")
        how = next((v for k_, v in LID_HOW if k_ in t), "As the drafted B-29 pieces.")
        op(f"Lid: {t}", how + " (rows from patterns_corrie_f_rev3.lid_hours)", kind, pieces=", ".join(sorted(i for i in rs.pieces if i.startswith("B-29"))), seam=seam, length=L * (2 if seam in ("SSa2", "ZIP") else 1), hours=r["hours"],
           sketch="SK-6")

    # ---------------------------------------------------------------- 7 straps and webbing (from the pieces)
    step("7 Straps and webbing")
    for w in webs:
        pid = w["id"]
        p = rs.pieces.get(pid)
        if w["material_id"] == "shock_cord_3mm":
            continue                                        # sewn where it is inserted (ops 1.02, 4.12, E5 below)
        folds = [ln.label for ln in lines(p, "fold")] if p is not None else []
        bxs = boxes_of(p) if p is not None else []
        lpr = lp.get(pid)
        if w["material_id"].startswith("elastic"):
            op(f"{pid}: {w['use']} x{w['qty']}", f"Cut {w['length_mm']:.0f} mm, lap 15 mm into a loop round its strap, "
               "zigzag the lap (3 passes).", "zz", pieces=f"{pid} x{w['qty']}", seam="BT (zigzag lap)",
               hours=w["qty"] * H["bartack"])
            continue
        if not folds and not bxs:
            how = "straight strap, sealed ends; threaded at assembly (op 7.end)."
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
        if pid == "B-25":
            how += (" FRAME COORDINATION: the bar sleeves close round the crown top bar BEFORE the crown corners are "
                    "bonded (H1 build); sew the toggle tabs + second folds here, the sleeves at frame assembly.")
        op(f"{pid}: {w['use']} x{w['qty']}", how, kind, pieces=f"{pid} x{w['qty']}",
           seam="BOX" if kind == "box" else ("BT" if kind == "bt" else "-"),
           bartack=pid if lpr else "", hours=hrs, length=wl, sketch="SK-1, SK-7", qc="QC-07" if lpr else "",
           vol="BL-033 ledger" if pid in ("US",) else "")
    op("Fit the hardware", "IM1/IM2: G-hook right end, cam threaded; IM3: wiregate carabiner on the free end; T3 loops: "
       "wiregate carabiner + TPU sleeve; W1-W3: rated G-hook end, heavy ladder lock on the gusset side; guys: "
       "toggle in the B-25 tab, through the B-27 port, heavy ladder lock on LLT, tri-glide keeper; B-28: toggle rear, "
       "ladder lock both ends, 2 elastic keepers; RT: side-release buckles; E5: cord lock.", "none",
       pieces="hardware", hours=1.0, qc="QC-11")

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

    # ---------------------------------------------------------------- 9 fly (volatile: BL-033)
    step("9 Rain fly F-01")
    if g["fly_drafted"]:
        fids = g["fly_ids"]
        fs = {k: v for k, v in ctx.seams.items() if "F-01" in k}
        fl_len = sum(fs.values())
        note = " ".join(rs.pieces[i].labels.get("note", "") for i in fids[:1])
        op("F-01 fly: panel seams", f"Join the fly panels ({'; '.join(f'{k} {v:.0f} mm' for k, v in fs.items())}). "
           f"Silpoly: weights and clips, no pins; 301 then flat-fell; seam-seal the felled seams (piece note: {note})",
           "light", pieces=", ".join(fids), seam="SSa then LSc flat-fell (ISO 4916 class 2)", length=3 * fl_len,
           hours=rate(fl_len) * 2, vol="BL-033 F-01")
        hem = sum(sum(_len(ln.points) for ln in lines(rs.pieces[i], "fold", "hem")) * rs.pieces[i].quantity for i in fids)
        el = [w for w in rs.webbing if w["id"] == "F-EL"]
        op("F-01 fly: elastic channel hems", f"Turn the hems 20 mm on the drawn hem lines ({hem:.0f} mm of hem); "
           + (f"thread {el[0]['length_mm']:.0f} mm of 6 mm elastic (F-EL), bar each end." if el else "elastic per the "
              "pattern."), "light", pieces=", ".join(fids) + (", F-EL" if el else ""), seam="EFb channel",
           length=hem, hours=rate(hem) + 4 * H["bartack"], vol="BL-033 F-01")
    else:
        op("F-01 rain fly: HOLD", "F-01 is not drafted (ledger row 'F-01 rain fly' not_drafted; BL-033 adds it). "
           "Re-run this script when the pattern lands; ops are generated from the F-01 pieces.", "none",
           pieces="F-01", hours=0.0, vol="BL-033 F-01")

    # ---------------------------------------------------------------- 10 finish
    step("10 Finish, inspect, pack")
    op("Trim, seal, turn", "Trim thread ends to 3 mm, heat-seal webbing ends that frayed, turn the bag right side out "
       "through the door.", "none", hours=0.5)
    op("Final inspection and weigh", "QC sheet sections F and M; weigh each kit against the ledger.", "none",
       qc="QC-12 to QC-20", hours=0.5)
    op("Pack", "README.md, Packaging section.", "none", hours=0.2)
    miss = unsequenced(rs, out)
    if miss:
        step("11 Unsequenced (pattern changed)")
        for pid in miss:
            op(f"{pid}: HOLD, not sequenced", "This piece is in the pattern but no operation uses it: the pattern "
               "changed after this generator was written. Add its operation here.", "none", pieces=pid,
               vol="BL-033 ledger")
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
         "85 L +/- 3 L (5200 cu in) (owner limit)", "first article"),
        ("QC-14", "Final", "Mass, bag base", "1 g scale",
         f"within +/- 3 % of the ledger base bag ({rows_mass['base_g']:.0f} g on the ledger basis; primary fabrics are heavier, see costing.md)", "every bag"),
        ("QC-15", "Final", "No hook-and-loop, coil zips only", "visual", "zero hook-and-loop anywhere (owner: quiet bag)", "100 %"),
        ("QC-16", "Final", "Camo use", "visual", "camo only on B-02u, SH-07, SH-01b, FP-b, B-29f, A1-d (accents)", "100 %"),
        ("QC-17", "Final", "Thread ends, seals", "visual", "ends <= 3 mm, no open webbing ends, no burnt fabric", "100 %"),
        ("QC-18", "Final", "Labels", "visual", "ID label with rev 3 + date, size / crown kit, load-limit card (53 kg frame meat, RD-02)", "100 %"),
        ("QC-19", "Final", "Kits complete", "count", "base / as-hunted (lid, B-28 per kit, scope pod) / meat-trip (WX, B-24, liner) bags each complete", "100 %"),
        ("QC-20", "Final", "Fit on the frame", "hook to a frame or the fit jig: hinge pins, IM eyes through B-12 ports, guys through B-27",
         "every eye reaches its port without strain; door opens fully", "first article + 1 in 25"),
    ]
    return [dict(zip(("id", "stage", "check", "method", "pass", "frequency"), r)) for r in q]


RELEASE_TESTS = [   # id, why it gates this package (register row read at run time)
    ("MT-1", "every 25 mm box-X on IM1-IM3 and US1/US2"), ("MT-2", "IM free-end hooks"), ("MT-3", "IM / US cams"),
    ("PT-1", "IM3 carabiner on T3"), ("PT-2", "T3 on the 70 mm B-17 tab"), ("PT-3", "HE eye on B-18 (no binding)"),
    ("PT-5", "guy lock + tri-glide keeper"), ("PT-6", "B-24 float link"),
    ("LL-H", "heavy 25 mm ladder lock slip: guys, W1-W3 and the B-28 crown straps (the B-28 slip gate since BL-031)"),
    ("T9", "rev 3 items: port guys at the S kit, crown strap cinch and free length, lid mass and seat"),
    ("FS-O5", "alternate fabric gate: ULTRA 200X 50 mm strip (floor / frame side)"),
]
EXTRA_GATES = [
    ("B-28 slip", "B-28 crown strap on its heavy ladder lock: covered by LL-H at 366 N (BL-031 dropped the 20 mm gate; "
                  "25 mm strap on ladder_lock_25mm_heavy)", "LL-H pass", "corrie_f_body.md 15.6 / 16"),
    ("PORT-1", "B-27 port mock-up: hose from above 1 min with the guy pulled at 45 deg; 100 N guy pull through the lap; "
               "gloved lock use at the port", "no water inside; lap stays closed at 100 N", "corrie_f_body.md 13.9"),
    ("GT-1", "capstan pull: 5 kg on the guy over the packed bag's corner", "record MU_WEB_FAB (0.20-0.40 band)",
     "corrie_f_body.md 13.9"),
    ("ALT-1", "alternate set: owner sees an ULTRAGrid swatch", "owner OK in writing", "part A README section 1"),
    ("ALT-2", "alternate set: PT-3 on 200X + 50 mm strip test", ">= 36.8 N/mm (1840 N / 50 mm mean, FS-O5)",
     "part A README; register FS-O5"),
    ("ALT-3", "alternate set: weigh the 70D stock", "gsm within +/- 5 % of nylon_ripstop_70d record", "part A README"),
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
def costing(ctx: Ctx, bom: list[BOMLine], oplist: list[SewingOp]) -> dict:
    mat_cost = sum(b.cost_usd or 0.0 for b in bom if b.section in ("fabric", "webbing", "hardware", "thread",
                                                                     "consumable", "packaging"))
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
    return {"material_usd_primary": round(mat_cost, 2),
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
    return {"base_g": round(base, 1), "as_hunted_g": round(hunted, 1), "meat_trip_g": round(meat, 1),
            "pattern_fabric_alt_g": mc["pattern_g"], "ledger_fabric_g": mc["ledger_g"], "mass_delta_pct": mc["delta_pct"],
            "mass_ok": mc["ok"], "pattern_fabric_primary_g": round(prim, 1),
            "primary_minus_alt_g": round(prim - mc["pattern_g"], 1)}


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
        "first article build; CORRIE gates; BL-033 items listed as volatile ops")
    add("RD-17", "restated", f"IMP-2 / IMP-4 / IMP-8 in the bag: {has('B-09c', 'IMP4-a', 'IMP8-a')}; SH-03 absent: "
        f"{'SH-03' not in ids}; body seams un-bound (SSa2, ASSUMPTION NO-BIND)",
        "FRAY-1 wash-swatch test; IMP-1/3/5/6 belong to the harness / belt packages")
    add("RD-18", "closed", f"B-11 x8 + BRL x2 + BRS + G-hook in the BOM: {has('B-11', 'BRL', 'BRS')}",
        "B-11 placements are not drawn on any rev 3 piece (pattern-maker)")
    add("RD-21", "restated", "this op sequence supersedes BUILD_PLAN.md step 9 for the bag (bag ops only)",
        "BUILD_PLAN.md still describes stubs, bay mode, the PA66 plate: needs a pointer to this package (not edited here)")
    add("RD-22", "open", "the packaging card (README Packaging) carries the load limits", "the user guide itself")
    add("RD-23", "restated", f"B-25, B-27f, B-22 inside, TG, LLT drafted and sequenced (ops 3.04-3.05, 4.03): "
        f"{has('B-25', 'B-27f', 'B-22', 'TG', 'LLT')}", "T9 rev 3 at the S kit; LL-H; PORT-1; attorney review; BL-033 "
        "may move B-22 (x +/-130.3 vs 149)")
    add("RD-24", "restated", f"B-29 (7 piece types) + B-28 per kit + keepers sequenced; lid {ctx.lid['hours']} h on the "
        f"drafted pattern vs {ctx.lid['bl029_booked_h']} h booked", "T9 lid weigh / photo, cinch, free lengths; "
        "build_metrics still books the old lid hours (ledger / corrie_f owner)")
    return R


# ============================================================================ build everything (no files)
def package(ctx: Ctx | None = None) -> dict:
    ctx = ctx or build_ctx()
    g = geo(ctx)
    oplist = ops(ctx)
    bom = fabric_bom(ctx) + webbing_bom(ctx) + hardware_bom(ctx) + thread_bom(oplist) + consumables_bom(g)
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
    ("B28-FACE", "B-28 front tabs go on the OUTSIDE of the hinge band (the strap runs on the aft face); part A README "
                 "says 'inside'.", "pattern-maker / pack-designer confirm; T9 strap path"),
    ("B25-BOX", "Each B-25 toggle tab and second fold is closed with a 21 x 20 box-X (pattern shows folds only).", "LL-H toggle-loop pull"),
    ("IM-BOX / US-BOX / W3-BOX", "IM1-IM3 end loops, US eyes and W3's hook end get a 21 x 25 box-X (pattern draws folds only).",
     "MT-1 specimens are sewn exactly this way"),
    ("WX-LOAD", "Haul extenders carry the S9 float-clamp load (225 N).", "pack-designer load case; LL-H"),
    ("KW-PLACE", "K-W keepers at W1-W3 heights z 80 / 250 / 420 in the aft corner seams (not drawn).", "pattern-maker notches"),
    ("F02-PLACE", "F-02 centred on the outside of B-05 (not drawn).", "pattern-maker placement; fly fit (BL-033)"),
    ("BT-STD", "Slit-end bartack 10 x 2 mm, 28 stitches; standard tack 16 x 2 mm, 42 stitches (LK-1900 patterns).", "QC-07"),
    ("PRICES", "Items with no record cost use PRICE_ASSUMED (sliders, cams, tri-glides, toggles, elastic, labels).",
     "supplier quotes; materials-engineer records"),
    ("ELASTIC", "25 mm elastic keepers: no material record (pattern module ELASTIC).", "materials-engineer record"),
]

JIGS = [
    ("J1", "Box-X templates, clear acrylic 2 mm, one per size in the load table (21x20, 21x25, 25x25, 34x20, 34x30, 34x34), "
           "slots for chalk on the rectangle and both diagonals; production: LK-1900 / AMS-210EN programs of the same paths"),
    ("J2", "Swell window corner template + clip board (8 swells, notch to notch)"),
    ("J3", "B-27 port gauge: 6 mm turn, 20 mm lap, facing line; a slotted ruler"),
    ("J4", "Webbing fold gauge: aluminium angle with stops at 15 / 30 / 45 / 50 / 60 / 100 mm"),
    ("J5", "LK-1900 / AMS-210EN work clamps for 25 and 38 mm webbing stacks (Hypalon + panel)"),
    ("J6", "Door zip board: B-02door + B-02u laid flat with the corner-tangent notches pinned to the board"),
    ("J7", "Lid dart template (B-29a, 4 darts, apex drill marks)"),
    ("J8", "Hot-knife length fence with a scale in mm and in (cut lengths in cutting_plan.csv)"),
]


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


def _imp(b: BOMLine) -> str:
    if b.unit == "m":
        return f"{b.qty / 0.9144:.2f} yd"
    if b.unit == "m2":
        return f"{b.qty * 10.764:.2f} ft2"
    return ""


def write_files(pk: dict, out: Path = OUT) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    files = []
    ctx, g = pk["ctx"], pk["geo"]
    bom_rows = [{**asdict(b), "imperial": _imp(b)} for b in pk["bom"]]
    _w_csv(out / "bom.csv", bom_rows)
    op_rows = [asdict(o) for o in pk["ops"]]
    _w_csv(out / "op_sequence.csv", op_rows)
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
    md = [f"# {TITLE}: manufacturing package (BL-032 part B)", "",
          f"Generated {DATE} by `designs/pack_5200/mfg_corrie_f_rev3.py` from `patterns_corrie_f_rev3.build()` and the "
          "part A markers. **Do not edit by hand: re-run the script.** Patterns: `../patterns/`.", "",
          "## Files", "",
          "| File | What |", "|---|---|",
          "| `techpack_corrie_f_rev3.pdf` | the tech pack a contract factory quotes from (all sections below) |",
          "| `preview/` | raster preview of every tech-pack page (60 dpi) |",
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
          f"- Material cost a bag (record prices): primary ${c['material_usd_primary']:.0f}, alternate "
          f"${c['material_usd_alternate']:.0f}. CMT + materials: US contract ${c['landed_usd']['us_contract_usd_min']:.0f}, "
          f"Asia ${c['landed_usd']['asia_contract_usd_min']:.0f} (ASSUMPTION LABOUR).",
          f"- Load points: {len(pk['load_points'])}; lowest SF {checks(pk)['min_sf']} ({checks(pk)['min_sf_point']}).", "",
          "## Re-run when BL-033 lands (volatile operations)", "",
          "These ops read their numbers from the pattern; re-run `python designs/pack_5200/mfg_corrie_f_rev3.py` after "
          "the pattern module changes and they update:", ""]
    for v in pk["volatile"]:
        md.append(f"- **{v}**: ops " + ", ".join(o.seq for o in pk["ops"] if o.volatile == v)
                  + ("; load points " + ", ".join(r["point"] for r in pk["load_points"] if r["volatile"] == v)
                     if any(r["volatile"] == v for r in pk["load_points"]) else ""))
    md += ["", f"Current values: B-22 at x +/-{g['b22_x']} mm (drawn {g['b22_drawn_x']}); FP flat width "
           f"{g['fp_flat_w']} mm (finished {g['fp_finished_w']}); {g['windows']} swell windows; F-01 drafted: "
           f"{g['fly_drafted']}.", "", "## On HOLD (cannot be sewn from the pattern as released)", ""]
    md += [f"- {h}" for h in checks(pk)["holds"]]
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
    cm += ["", "One-off tooling (not a bag): J1-J8 jigs; LK-1900 / AMS-210EN programs; laser files are the part A DXFs; "
           "dies only above ~500 bags a year.", "", "Assumptions: " + "; ".join(c["assumptions"]) + "."]
    (out / "costing.md").write_text("\n".join(cm) + "\n")
    files.append(out / "costing.md")
    dm = [f"# Release delta register: rows this release resolves (BL-032)", "",
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
    cols = 4
    rows = math.ceil(n / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(14, 3.6 * rows))
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
        ax.text(0.0, -0.12, f"{nst} stitches incl. 4 lock, 7 SPI, tex 135, Nm 140 R\nused on: {', '.join(used)}",
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
        ax.text(0.0, -0.3, "LK-1900 standard tack, tex 90, Nm 110 R\nB-27 slit ends, FP mouth corners, I2K",
                transform=ax.transAxes, fontsize=8, va="top")
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
                  f"{g['port_z'][1]:.0f}. Volatile: hinge window vs B-18 (BL-033).", "6 with port (B-12 on the crest) "
                  "+ 2 hinge (B-13xh)", "facing INSIDE, inboard stitch line"], figsize=(16, 9))
    sk["SK-4"] = d / "SK-4_hinge_band.png"
    sk_piece_map(pk, ["B-02h", "B-22", "B-02door"], f"SK-4  Hinge band B-02h: B-22 INSIDE at x +/-{g['b22_x']} "
                 "(volatile), LLT box-X, B-28 front tab box-X (outside); then the door hinge seam", sk["SK-4"],
                 [f"B-22 drawn x +/-{g['b22_drawn_x']:.0f}, placed +/-{g['b22_x']}", "double-row perimeter",
                  "IMP-4 placement INSIDE"], figsize=(16, 7))
    sk["SK-5"] = d / "SK-5_gusset.png"
    sk_piece_map(pk, ["B-03", "FP-a", "FP-b"], "SK-5  Side gusset B-03 (cut L+R): kick band, FP pocket (volatile "
                 "width), IMP-8 (R only), hose slot; corner seams carry HPL (L) and E5 (R)", sk["SK-5"],
                 [f"FP z {g['fp_z'][0]:.0f}-{g['fp_z'][1]:.0f}", f"flat {g['fp_flat_w']:.0f} wide, 2 box pleats",
                  "fold = shock-cord channel"], figsize=(16, 9))
    sk["SK-6"] = d / "SK-6_crown_lid.png"
    sk_piece_map(pk, ["B-29a", "B-29b", "B-29e", "B-29g"], "SK-6  B-29 crown lid: darts -> channels -> zip between "
                 "the aft strips -> caps -> crown|wall ring -> wall|base ring (turn through the zip)", sk["SK-6"],
                 ["4 darts, 2 channel lines", "base (70D / 100D)", "aft lower: caps + #5 zip", "channel x2"],
                 figsize=(17, 7))
    sk["SK-7"] = d / "SK-7_webbing.png"
    sk_webbing(pk, sk["SK-7"])
    return sk


# ============================================================================ tech pack PDF (reportlab)
def tech_pack(pk: dict, sk: dict, path: Path) -> Path:
    """CONTRACTS.md section 5 tech_pack(design, path): cover, flats, BOM, pattern list, op sequence, QC, packaging."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

    ss = getSampleStyleSheet()
    sm = ParagraphStyle("sm", parent=ss["BodyText"], fontSize=6.6, leading=7.8)
    sb = ParagraphStyle("sb", parent=sm, fontName="Helvetica-Bold")
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=11.5)
    h1, h2 = ss["Heading1"], ss["Heading2"]
    ctx, g, c = pk["ctx"], pk["geo"], pk["costing"]
    ck = checks(pk)
    W, H = landscape(letter)
    story = []

    def P_(t, st=sm):
        return Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), st)

    def table(rows, widths, head=True):
        data = [[P_(x, sb if (head and i == 0) else sm) for x in r] for i, r in enumerate(rows)]
        t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e4da")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
        return t

    def img(p_, maxw=250, maxh=165):
        from PIL import Image as PI
        with PI.open(p_) as im:
            w, h = im.size
        sc = min(maxw * mm / w, maxh * mm / h)
        return Image(str(p_), width=w * sc, height=h * sc)

    # ---- 1 cover
    story += [Paragraph(f"Tech pack: {TITLE}", h1),
              P_(f"Revision 3, door D2, crown kit M shown (S / L cut lists in cutting_plan.csv). Issued {DATE}. "
                 "Generated by designs/pack_5200/mfg_corrie_f_rev3.py from the pattern module; patterns, DXF and markers in "
                 "../patterns/. Units mm, N, g (imperial alongside).", body), Spacer(1, 4 * mm)]
    key = [["Item", "Value"],
           ["Pieces", f"{len(ctx.rs.pieces)} piece types; {sum(p.quantity for p in _fabric_pieces(ctx.rs))} fabric / sheet "
                      f"pieces; {sum(w['qty'] for w in ctx.rs.webbing if not ('kit S' in w['kit'] or 'kit L' in w['kit']))} "
                      "webbing / cord / elastic"],
           ["Ledger reconciliation", f"{ck['recon_rows']} rows, {ck['recon_unmatched']} unmatched, "
                                     f"{ck['recon_pieces_without_row']} pieces without a row"],
           ["Mass from pattern areas", f"{pk['mass']['pattern_fabric_alt_g']} g vs ledger {pk['mass']['ledger_fabric_g']} g "
                                       f"({pk['mass']['mass_delta_pct']:+.2f} %, limit 3 %); bag ledger base "
                                       f"{pk['mass']['base_g']} g / as hunted {pk['mass']['as_hunted_g']} g / meat trip "
                                       f"{pk['mass']['meat_trip_g']} g (team B basis); primary fabrics "
                                       f"{pk['mass']['primary_minus_alt_g']:+.1f} g"],
           ["Operations", f"{ck['ops']} ops; beginner {c['proto_hours']} h; factory SAM {c['sam_min']:.0f} min"],
           ["Cost a bag", f"materials ${c['material_usd_primary']:.0f} primary / ${c['material_usd_alternate']:.0f} "
                          f"alternate; + CMT: US ${c['landed_usd']['us_contract_usd_min']:.0f}, Asia "
                          f"${c['landed_usd']['asia_contract_usd_min']:.0f} (ASSUMPTIONS)"],
           ["Load points", f"{ck['load_points']}; lowest SF {ck['min_sf']} ({ck['min_sf_point']}); every load point "
                           "is released by a proof test (section 7)"],
           ["HOLD", "; ".join(ck["holds"]) or "none"],
           ["Volatile (re-run on BL-033)", "; ".join(ck["volatile"])],
           ["Fabric sets", "PRIMARY = today's fabrics (build this). ALTERNATE = team B set (ULTRAGrid body, 70D collar, "
                           "ULTRA 200X floor) only after gates ALT-1..3 and FS-O5."],
           ["Owner rules", "No hook-and-loop; coil zips; mostly solid colours, camo on accents only; width <= 394 mm "
                           "(15.5 in); 85 L +/- 3."]]
    story += [table(key, [55, 190], head=True), Spacer(1, 3 * mm),
              P_("Contents: 1 cover; 2 equipment and stitch standards; 3 flats / piece maps; 4 BOM; 5 cutting plan; "
                 "6 operation sequence; 7 load points and sketches; 8 QC, release tests, defects; 9 packaging; "
                 "10 costing; 11 delta register; 12 assumptions.", body), PageBreak()]
    # ---- 2 equipment
    story += [Paragraph("2. Equipment and stitch standards", h1),
              table([["ID", "Machine / tool"]] + [[k, v] for k, v in MACHINES.items()], [18, 227]), Spacer(1, 3 * mm),
              table([["Use", "Thread (record)", "Needle", "SPI (mm)", "Stitch"],
                     ["40D-100D, mesh, silpoly", THREAD["light"], NEEDLE["light"] + " / " + NEEDLE["mesh"],
                      f"{SPI['light']} ({25.4 / SPI['light']:.1f})", "301"],
                     ["body seams, zips, Hypalon perimeters", THREAD["body"], NEEDLE["body"],
                      f"{SPI['body']} ({25.4 / SPI['body']:.1f})", "301"],
                     ["load box-X", THREAD["box"], NEEDLE["box"], f"{SPI['box']} ({25.4 / SPI['box']:.1f})",
                      "301 path (LK-1900 / AMS-210EN programmed)"],
                     ["bartacks, elastic laps", THREAD["body"], NEEDLE["body"], "LK-1900 std", "304"]],
                    [50, 40, 75, 25, 55]), Spacer(1, 2 * mm), P_(NEEDLE_RULE, body),
              P_(f"Seam efficiency: a 301 seam is taken at {SEAM_EFF:.0%} of the weaker strip (clothsim/fabrics.yaml, "
                 "attach_system.SEAM_EFF); box-X capacity = 0.5 x 1.5 x thread break / stitch length x path "
                 "(attach_system.box_x, ETA_BOX 0.5 ASSUMPTION).", body), Spacer(1, 2 * mm),
              table([["Code", "Seam construction"]] + [[k, v] for k, v in SEAMS.items()], [18, 227]), Spacer(1, 2 * mm),
              table([["Jig", "What"]] + [list(j) for j in JIGS], [18, 227]), PageBreak()]
    # ---- 3 flats
    story += [Paragraph("3. Flats and piece maps (from the pattern pieces)", h1)]
    render = ROOT / "docs" / "screens" / "20261112_BL030_2.png"
    if render.exists():
        story += [img(render, 200, 120), P_("Render of rev 3 (docs/screens/20261112_BL030_2.png, BL-030): side view, "
                                            "lid and crown straps. Colours / camo placement as drawn there.", body),
                  PageBreak()]
    for k in ("SK-3", "SK-4", "SK-5", "SK-6"):
        story += [img(sk[k]), PageBreak()]
    # ---- 4 BOM
    story += [Paragraph("4. Bill of materials (one bag, full build, crown kit M)", h1),
              P_("Production qty = 10-bag marker + 3 % lay loss where part A nested one, else net / utilisation "
                 "(ASSUMPTION). Prototype (1-bag marker) quantity in the last column. Waste % = gross / net - 1.", body)]
    rows = [["Section", "Item", "Material id", "Qty", "Unit", "Imperial", "Waste %", "$ / unit", "$", "Alternate / kit",
             "Proto qty", "Source"]]
    for b in pk["bom"]:
        rows.append([b.section, b.item, b.material_id, f"{b.qty:g}", b.unit, _imp(b), f"{b.waste_pct:g}",
                     "" if b.unit_cost_usd is None else f"{b.unit_cost_usd:.3g}",
                     "" if b.cost_usd is None else f"{b.cost_usd:.2f}", f"{b.alt_material_id} / {b.kit}",
                     "" if b.proto_qty is None else f"{b.proto_qty:g}", b.source])
    story += [table(rows, [17, 50, 30, 12, 8, 14, 10, 11, 11, 30, 12, 50]), PageBreak()]
    # ---- 5 cutting
    story += [Paragraph("5. Cutting plan", h1),
              P_("Markers: ../patterns/markers/. Cut windows, slots and slits first; knife clockwise from the grain "
                 "arrow; notches 6 mm. Ply height: woven nylon 24, laminates / mesh / silpoly 12, camo single ply "
                 "(one way, print placement), sheet goods laser single sheet.", body)]
    rows = [["Set", "Material", "Pieces", "1-bag m", "eff", "10-bag m / bag", "eff", "Lay", "Prototype", "Production"]]
    for r in pk["cutting"]:
        if r["set"] == "webbing":
            continue
        rows.append([r["set"], r["material_id"], r["pieces"], r["marker_1bag_m"] or "", r["eff_1bag"] or "",
                     r["marker_10bag_m_per_bag"] or "", r["eff_10bag"] or "", r["lay"], r["prototype_cut"],
                     r["production_cut"]])
    story += [table(rows, [14, 30, 50, 11, 9, 14, 9, 25, 40, 50]), Spacer(1, 3 * mm),
              Paragraph("Webbing, cord and elastic cut lengths", h2)]
    rows = [["ID", "Use", "Material", "Length mm (in)", "Qty", "Kit", "Source"]]
    for w in ctx.rs.webbing:
        rows.append([w["id"], w["use"], w["material_id"], f"{w['length_mm']:.0f} ({w['length_mm'] / IN:.1f})", w["qty"],
                     w["kit"], w["source"]])
    story += [table(rows, [14, 75, 35, 22, 8, 30, 60]), PageBreak()]
    # ---- 6 ops
    story += [Paragraph("6. Sewing operation sequence", h1),
              P_("All flat work before the bag becomes 3D. Clips, never pins, in coated fabric. Swatch every new stack. "
                 "Load points only after their proof test passes (section 8). V = volatile (re-run on BL-033).", body)]
    rows = [["Seq", "Operation", "How (beginner)", "Pieces", "Machine", "Needle", "Thread", "SPI", "Stitch / seam",
             "mm", "Ref", "h / SAM min"]]
    for o in pk["ops"]:
        rows.append([o.seq + (" V" if o.volatile else ""), o.operation, o.notes, o.pieces, o.machine, o.needle,
                     o.thread_id.replace("bonded_nylon_", "BN "), o.spi or "-", f"{o.stitch_type} / {o.seam or '-'}",
                     f"{o.length_mm:.0f}" if o.length_mm else "",
                     "; ".join(x for x in (o.sketch, o.qc, o.bartack) if x),
                     f"{o.proto_h:.2f} / {o.time_s / 60:.1f}" + ("" if o.per_bag else " 1x")])
    story += [table(rows, [9, 28, 72, 22, 16, 18, 11, 7, 20, 9, 18, 12]), PageBreak()]
    # ---- 7 load points
    story += [Paragraph("7. Load points: bartack and box-X specification", h1),
              P_("Load = factored design load from the record named (x 3.0 on the 1 g simulation per HA-LS-1 rev C). "
                 "Capacity by attach_system rules. Proof = the test that releases the point (register).", body)]
    rows = [["Point", "Part", "Where", "Pattern", "Stitches", "Machine", "Thread / needle", "Load N (lbf)", "Source",
             "Capacity N", "Governs", "SF", "Proof"]]
    for r in pk["load_points"]:
        rows.append([r["point"], r["part"], r["where"], r["pattern"], r["stitches"] or "", r["machine"],
                     f"{r['thread']} / {r['needle']}", f"{r['load_n'] or '-'} ({r['load_lbf'] or '-'})",
                     r["load_source"], r["capacity_n"] or "", r["governs"], r["sf"] or "", r["proof"] +
                     (f"; {r['note']}" if r["note"] else "")])
    story += [table(rows, [22, 18, 26, 28, 10, 18, 26, 14, 30, 12, 18, 7, 30]), PageBreak(),
              img(sk["SK-1"]), PageBreak(), img(sk["SK-2"]), PageBreak(), img(sk["SK-7"], 250, 170), PageBreak()]
    # ---- 8 QC
    story += [Paragraph("8. QC checkpoints", h1),
              table([["ID", "Stage", "Check", "Method", "Pass", "Frequency"]] +
                    [[q["id"], q["stage"], q["check"], q["method"], q["pass"], q["frequency"]] for q in pk["qc"]],
                    [12, 18, 35, 60, 85, 35]), PageBreak(),
              Paragraph("Physical tests that gate release", h1),
              table([["ID", "Test", "Gates", "Steps", "Pass / fail", "Source"]] +
                    [[t["id"], t["title"], t["gates"], t["steps"], t["pass"], t["source"]] for t in pk["tests"]],
                    [13, 45, 40, 75, 55, 17]), PageBreak(),
              Paragraph("Defect list", h1),
              table([["Defect", "Where", "Cause", "Prevent / fix", "Class"]] + [list(d) for d in DEFECTS],
                    [60, 35, 50, 85, 15]), Spacer(1, 4 * mm),
              Paragraph("9. Packaging", h1)] + [P_(f"{i + 1}. {t}", body) for i, t in enumerate(PACKAGING)] + [PageBreak()]
    # ---- 10 costing
    story += [Paragraph("10. Costing and hours", h1),
              table([["Step", "Beginner h"]] + [[k, f"{v:.2f}"] for k, v in c["proto_hours_by_step"].items()] +
                    [["Total (incl. one-off set-up)", f"{c['proto_hours']}"]], [100, 30]), Spacer(1, 3 * mm),
              table([["Scenario", "SAM min", "Labour $", "CMT incl. overhead $", "Materials $", "Total $"]] +
                    [[k, f"{c['sam_min']:.0f}", f"{c['labour_usd'][k]:.2f}", f"{c['cmt_usd'][k]:.2f}",
                      f"{c['material_usd_primary']:.2f}", f"{c['landed_usd'][k]:.2f}"] for k in LABOUR], [60, 20, 25, 35, 25, 25]),
              Spacer(1, 2 * mm),
              P_(f"Lid on the drafted pattern {c['lid_hours_drafted']} h (booked {c['lid_hours_booked']} h). Alternate "
                 f"set materials ${c['material_usd_alternate']:.2f}. Assumptions: {'; '.join(c['assumptions'])}.", body),
              PageBreak()]
    # ---- 11 delta + 12 assumptions
    story += [Paragraph("11. Release delta register: rows this release resolves", h1),
              table([["RD", "Status", "Evidence (checked by the script)", "Still open"]] +
                    [[d["id"], d["status_after_rev3_package"], d["evidence"], d["still_open"]] for d in pk["delta"]],
                    [14, 25, 110, 96]), PageBreak(),
              Paragraph("12. Assumptions that govern", h1),
              table([["ID", "Assumption", "Settled by"]] + [list(a) for a in ASSUMPTIONS], [30, 125, 90])]

    def footer(cv, doc):
        cv.saveState()
        cv.setFont("Helvetica", 7)
        cv.drawString(12 * mm, 7 * mm, f"{TITLE} - tech pack - {DATE} - generated, do not edit")
        cv.drawRightString(W - 12 * mm, 7 * mm, f"page {doc.page}")
        cv.restoreState()

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=(W, H), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=12 * mm, title=f"Tech pack {TITLE}", author="Hunting-appeal (generated)")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path


# ============================================================================ previews and screenshots
def preview(pdf: Path, out: Path) -> list[Path]:
    d = out / "preview"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("techpack-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", "60", str(pdf), str(d / "techpack")], check=True)
    return sorted(d.glob("techpack-*.png"))


def screenshots(pdf: Path, sk: dict) -> list[Path]:
    """Phone-readable PNGs (<= 1.5 MB): cover page, an op-sequence page, SK-1, SK-3 (pages at 110 dpi)."""
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
    srcs = [sorted(tmp.glob("cover*.png"))[0], sorted(tmp.glob("ops*.png"))[0], sk["SK-1"], sk["SK-3"]]
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
    pdf = tech_pack(pk, sk, out / "techpack_corrie_f_rev3.pdf")
    pv = preview(pdf, out)
    print(f"wrote {len(files)} files, {len(sk)} sketches, {pdf} ({len(pv)} pages previewed)")
    if not a.no_screens and out == OUT:
        for s_ in screenshots(pdf, sk):
            print("SCREEN", s_)
    return pk


if __name__ == "__main__":
    main()
