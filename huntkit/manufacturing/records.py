"""Contract records of CONTRACTS.md section 5: ``SewingOp`` and ``BOMLine`` (owner: manufacturing-engineer).

Moved here from ``designs/pack_5200/mfg_corrie_f_rev3.py`` (BL-034 part C) with the field names and order unchanged,
so CSVs written before the move read the same. Contract fields come first; the rest are optional extras a design's
generator may fill.

Units: mm, s, USD; ``spi`` in stitches per inch (the shop unit; 25.4 / spi gives the stitch length in mm).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

YD_M = 0.9144
FT2_M2 = 10.764


@dataclass
class SewingOp:
    """One sewing (or prep / cut / inspect) operation. CONTRACTS.md section 5 fields first."""
    seq: str                 # "4.07": step . op
    operation: str
    machine: str
    stitch_type: str         # ISO 4915 (301, 304, 401, 504, 516, 607) or "301 box-X path"; "-" for no stitching
    spi: float | None
    thread_id: str           # data/materials/thread record id, or "-"
    needle: str              # "Nm 110/18 DPx17, round point R"
    attachment: str          # folder / binder / foot, "-" for none
    notes: str               # how to do it (beginner wording)
    time_s: float            # factory SAM, s (0 for one-off set-up)
    step: str = ""
    pieces: str = ""
    seam: str = ""
    length_mm: float = 0.0   # stitching length of the op (thread is booked from it)
    bartack: str = ""
    sketch: str = ""
    qc: str = ""
    volatile: str = ""
    proto_h: float = 0.0     # beginner hours
    per_bag: bool = True


@dataclass
class BOMLine:
    """One BOM line. CONTRACTS.md section 5: material id, qty, unit, waste factor, cost."""
    section: str
    item: str
    material_id: str
    qty: float               # purchase quantity per product, waste included
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


SEWING_OP_FIELDS = tuple(f.name for f in fields(SewingOp))
BOM_LINE_FIELDS = tuple(f.name for f in fields(BOMLine))


def imperial(b: BOMLine) -> str:
    """Imperial text for a BOM quantity (yd for m, ft2 for m2), '' otherwise."""
    if b.unit == "m":
        return f"{b.qty / YD_M:.2f} yd"
    if b.unit == "m2":
        return f"{b.qty * FT2_M2:.2f} ft2"
    return ""


def bom_rows(bom: list[BOMLine]) -> list[dict]:
    return [{**asdict(b), "imperial": imperial(b)} for b in bom]


def op_rows(ops: list[SewingOp]) -> list[dict]:
    return [asdict(o) for o in ops]


def bom_cost(bom: list[BOMLine], sections=None) -> float:
    """Sum of line costs (None counts 0), optionally only the given sections."""
    return float(sum(b.cost_usd or 0.0 for b in bom if sections is None or b.section in sections))


def missing_cost(bom: list[BOMLine], skip=()) -> list[str]:
    return [b.item for b in bom if b.cost_usd is None and b.section not in skip]


def thread_metres(ops: list[SewingOp], factor: float) -> dict:
    """Thread consumed by stitching, by thread id: op length x ``factor`` (m of thread per m of seam, both threads).
    No waste: this is what ends up in the product. Purchase quantity = this x (1 + cone waste)."""
    out: dict = {}
    for o in ops:
        if o.length_mm and o.thread_id not in ("", "-"):
            out[o.thread_id] = out.get(o.thread_id, 0.0) + o.length_mm / 1000.0 * factor
    return out
