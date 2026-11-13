"""huntkit.manufacturing: BOM / sewing-op records and the tech pack builder (CONTRACTS.md section 5).

Owner: manufacturing-engineer. Product generators (``designs/.../mfg_*.py``) build the content; this package holds the
shared shapes and the PDF layout.

    from huntkit.manufacturing import SewingOp, BOMLine, TechPack, Section, tech_pack
"""
from .records import (BOM_LINE_FIELDS, SEWING_OP_FIELDS, BOMLine, SewingOp, bom_cost, bom_rows, imperial,
                      missing_cost, op_rows, thread_metres)
from .techpack import (REQUIRED_SECTIONS, Section, TechPack, bom_table, h2, image, missing_sections, ops_table,
                       page_break, para, space, table, tech_pack)

__all__ = ["SewingOp", "BOMLine", "SEWING_OP_FIELDS", "BOM_LINE_FIELDS", "imperial", "bom_rows", "op_rows", "bom_cost",
           "missing_cost", "thread_metres", "TechPack", "Section", "tech_pack", "missing_sections", "REQUIRED_SECTIONS",
           "para", "h2", "table", "image", "space", "page_break", "bom_table", "ops_table"]
