"""Tech pack PDF builder, CONTRACTS.md section 5 ``tech_pack(design, path)`` (owner: manufacturing-engineer).

Design-neutral: a product's generator (e.g. ``designs/pack_5200/mfg_corrie_f_rev3.py``) assembles a ``TechPack``
(cover rows plus ordered sections of paragraphs, tables and images) and this module lays it out as a landscape letter
PDF a contract factory can quote from. Moved here from the CORRIE F rev 3 generator in BL-034 part C; the layout
(fonts, grid tables, footer) is the one that generator used.

Block kinds (plain dicts, so a tech pack can also come from JSON, see ``huntkit.manufacturing.cli``):

* ``{"kind": "p", "text": str}``                        paragraph (body size)
* ``{"kind": "h2", "text": str}``                       sub-heading
* ``{"kind": "table", "rows": [[...]], "widths_mm": [...], "head": True}``  grid table, first row bold
* ``{"kind": "image", "path": str, "max_w_mm": 250, "max_h_mm": 165}``    raster image, aspect kept
* ``{"kind": "space", "mm": 3}``                        vertical space
* ``{"kind": "break"}``                                 page break

Every section starts on a new page. ``missing_sections(design)`` lists the contract sections (cover, flats, BOM,
pattern list, op sequence, QC, packaging) a design does not have; ``tech_pack(..., strict=True)`` refuses to build then.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .records import BOMLine, SewingOp, imperial

# contract section -> words, any of which in a section title satisfies it (case-insensitive)
REQUIRED_SECTIONS = {
    "flats": ("flat", "piece map"),
    "BOM": ("bill of materials", "bom"),
    "pattern list": ("pattern", "cutting"),
    "op sequence": ("operation", "sewing"),
    "QC": ("qc", "quality"),
    "packaging": ("packaging",),
}


@dataclass
class Section:
    title: str
    blocks: list = field(default_factory=list)


@dataclass
class TechPack:
    title: str
    subtitle: str = ""
    date: str = ""
    footer: str = ""
    cover: list = field(default_factory=list)          # [[key, value], ...] (no header row)
    contents: str = ""
    sections: list = field(default_factory=list)       # [Section]

    @classmethod
    def from_dict(cls, d: dict) -> "TechPack":
        secs = [s if isinstance(s, Section) else Section(s["title"], list(s.get("blocks", []))) for s in d.get("sections", [])]
        return cls(title=d["title"], subtitle=d.get("subtitle", ""), date=d.get("date", ""), footer=d.get("footer", ""),
                   cover=[list(r) for r in d.get("cover", [])], contents=d.get("contents", ""), sections=secs)


# ---------------------------------------------------------------------------- block helpers
def para(text: str) -> dict:
    return {"kind": "p", "text": str(text)}


def h2(text: str) -> dict:
    return {"kind": "h2", "text": str(text)}


def table(rows: list, widths_mm: list, head: bool = True) -> dict:
    return {"kind": "table", "rows": [[("" if x is None else x) for x in r] for r in rows], "widths_mm": list(widths_mm),
            "head": head}


def image(path, max_w_mm: float = 250.0, max_h_mm: float = 165.0) -> dict:
    return {"kind": "image", "path": str(path), "max_w_mm": max_w_mm, "max_h_mm": max_h_mm}


def space(mm_: float = 3.0) -> dict:
    return {"kind": "space", "mm": mm_}


def page_break() -> dict:
    return {"kind": "break"}


# ---------------------------------------------------------------------------- standard tables
BOM_HEAD = ["Section", "Item", "Material id", "Qty", "Unit", "Imperial", "Waste %", "$ / unit", "$", "Alternate / kit",
            "Proto qty", "Source"]
BOM_WIDTHS = [17, 50, 30, 12, 8, 14, 10, 11, 11, 30, 12, 50]
OPS_HEAD = ["Seq", "Operation", "How (beginner)", "Pieces", "Machine", "Needle", "Thread", "SPI", "Stitch / seam", "mm",
            "Ref", "h / SAM min"]
OPS_WIDTHS = [9, 28, 72, 22, 16, 18, 11, 7, 20, 9, 18, 12]


def bom_table(bom: list[BOMLine]) -> dict:
    rows = [BOM_HEAD]
    for b in bom:
        rows.append([b.section, b.item, b.material_id, f"{b.qty:g}", b.unit, imperial(b), f"{b.waste_pct:g}",
                     "" if b.unit_cost_usd is None else f"{b.unit_cost_usd:.3g}",
                     "" if b.cost_usd is None else f"{b.cost_usd:.2f}", f"{b.alt_material_id} / {b.kit}",
                     "" if b.proto_qty is None else f"{b.proto_qty:g}", b.source])
    return table(rows, BOM_WIDTHS)


def ops_table(ops: list[SewingOp], thread_prefix: str = "bonded_nylon_", thread_short: str = "BN ") -> dict:
    rows = [OPS_HEAD]
    for o in ops:
        rows.append([o.seq + (" V" if o.volatile else ""), o.operation, o.notes, o.pieces, o.machine, o.needle,
                     o.thread_id.replace(thread_prefix, thread_short), o.spi or "-", f"{o.stitch_type} / {o.seam or '-'}",
                     f"{o.length_mm:.0f}" if o.length_mm else "", "; ".join(x for x in (o.sketch, o.qc, o.bartack) if x),
                     f"{o.proto_h:.2f} / {o.time_s / 60:.1f}" + ("" if o.per_bag else " 1x")])
    return table(rows, OPS_WIDTHS)


def missing_sections(design: TechPack) -> list[str]:
    titles = " | ".join(s.title.lower() for s in design.sections)
    out = [] if design.cover else ["cover"]
    return out + [k for k, words in REQUIRED_SECTIONS.items() if not any(w in titles for w in words)]


# ---------------------------------------------------------------------------- PDF
def tech_pack(design: TechPack | dict, path, strict: bool = False) -> Path:
    """Build the tech pack PDF (landscape letter): cover page, then one block of pages per section. Returns the path."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

    d = design if isinstance(design, TechPack) else TechPack.from_dict(design)
    miss = missing_sections(d)
    if strict and miss:
        raise ValueError(f"tech pack lacks contract sections: {miss}")
    path = Path(path)
    ss = getSampleStyleSheet()
    sm = ParagraphStyle("sm", parent=ss["BodyText"], fontSize=6.6, leading=7.8)
    sb = ParagraphStyle("sb", parent=sm, fontName="Helvetica-Bold")
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=11.5)
    h1, h2_ = ss["Heading1"], ss["Heading2"]
    W, H = landscape(letter)

    def esc(t):
        return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def P_(t, st=sm):
        return Paragraph(esc(t), st)

    def tbl(rows, widths, head=True):
        data = [[P_(x, sb if (head and i == 0) else sm) for x in r] for i, r in enumerate(rows)]
        t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                               ("BACKGROUND", (0, 0), (-1, 0) if head else (0, 0), colors.HexColor("#e8e4da")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
        return t

    def img(p_, maxw, maxh):
        from PIL import Image as PI
        with PI.open(p_) as im:
            w, h = im.size
        sc = min(maxw * mm / w, maxh * mm / h)
        return Image(str(p_), width=w * sc, height=h * sc)

    def flow(b):
        k = b["kind"]
        if k == "p":
            return [P_(b["text"], body)]
        if k == "h2":
            return [Paragraph(esc(b["text"]), h2_)]
        if k == "table":
            return [tbl(b["rows"], b["widths_mm"], b.get("head", True))]
        if k == "image":
            if not Path(b["path"]).exists():
                return [P_(f"(image missing: {b['path']})", body)]
            return [img(b["path"], b.get("max_w_mm", 250.0), b.get("max_h_mm", 165.0))]
        if k == "space":
            return [Spacer(1, b.get("mm", 3.0) * mm)]
        if k == "break":
            return [PageBreak()]
        raise ValueError(f"unknown tech-pack block kind {k!r}")

    story = [Paragraph(esc(f"Tech pack: {d.title}"), h1)]
    if d.subtitle:
        story += [P_(d.subtitle, body)]
    story += [Spacer(1, 4 * mm)]
    if d.cover:
        story += [tbl([["Item", "Value"]] + d.cover, [55, 190]), Spacer(1, 3 * mm)]
    if d.contents:
        story += [P_(d.contents, body)]
    for s in d.sections:
        story += [PageBreak(), Paragraph(esc(s.title), h1)]
        for b in s.blocks:
            story += flow(b)
    foot = d.footer or f"{d.title} - tech pack - {d.date}"

    def footer(cv, doc):
        cv.saveState()
        cv.setFont("Helvetica", 7)
        cv.drawString(12 * mm, 7 * mm, foot)
        cv.drawRightString(W - 12 * mm, 7 * mm, f"page {doc.page}")
        cv.restoreState()

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=(W, H), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm,
                            bottomMargin=12 * mm, title=f"Tech pack {d.title}", author="Hunting-appeal (generated)")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return path
