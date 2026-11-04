"""huntkit.patterns: production pattern engine (contract: docs/CONTRACTS.md section 3).

Seam line is the geometry; cut line = seam line + (per-edge) seam allowance. Units: mm.

Quick tour::

    from huntkit.patterns import rect_panel, Seam, check_seams, nest, export_dxf
    front = rect_panel("front", 300, 400, corner_radius={"bl": 40, "br": 40},
                       material_id="nylon_ripstop_210d", quantity=1)
    ...
    check_seams([Seam(front.edge("right"), side.edge("left").reversed())]).assert_ok()
"""
from .curves import arc, arc_3pt, bezier, line, polyline_length
from .cutlist import CutList, cut_list
from .export_dxf import export_dxf
from .export_pdf import export_pdf_tiled
from .export_svg import export_svg
from .geometry import (BoxBag, Cylinder, DevelopedSurface, box_bag, box_bag_volume,
                       cubic_inches, cylinder, dart_seams, darted_panel, develop_region,
                       develop_ruled_surface, FlatMesh, flatten_mesh,
                       litres, panel_volume, rect_panel, tapered_panel)
from .grading import GradeRules, grade, grade_all, proportional_rules
from .nesting import Marker, Placement, nest
from .piece import DrillHole, EdgeRef, InternalLine, Notch, Piece
from .seams import Seam, SeamMismatchError, SeamReport, check_seams

__all__ = [
    "Piece", "EdgeRef", "Notch", "DrillHole", "InternalLine",
    "Seam", "SeamReport", "SeamMismatchError", "check_seams",
    "line", "bezier", "arc", "arc_3pt", "polyline_length",
    "rect_panel", "tapered_panel", "darted_panel", "dart_seams", "box_bag", "BoxBag",
    "cylinder", "Cylinder", "develop_ruled_surface", "DevelopedSurface",
    "develop_region", "flatten_mesh", "FlatMesh",
    "panel_volume", "box_bag_volume", "litres", "cubic_inches",
    "grade", "grade_all", "GradeRules", "proportional_rules",
    "export_dxf", "export_pdf_tiled", "export_svg",
    "nest", "Marker", "Placement", "cut_list", "CutList",
]
