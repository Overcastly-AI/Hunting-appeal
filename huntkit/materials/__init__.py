"""Material database loader (contract: docs/CONTRACTS.md §1).

Records live in ``data/materials/<category>/<id>.yaml``. Public API::

    from huntkit.materials import load, query, all_materials
    m = load("alu_7075_t6")
    m.require("yield_strength_mpa")
    query("textiles", areal_density_gsm__lt=150)
"""
from .loader import (
    CATEGORIES,
    CONFIDENCE_LEVELS,
    Material,
    MaterialError,
    MissingPropertyError,
    all_materials,
    data_dir,
    load,
    query,
    reload,
)
from .validate import validate_all, validate_record

__all__ = [
    "CATEGORIES",
    "CONFIDENCE_LEVELS",
    "Material",
    "MaterialError",
    "MissingPropertyError",
    "all_materials",
    "data_dir",
    "load",
    "query",
    "reload",
    "validate_all",
    "validate_record",
]
