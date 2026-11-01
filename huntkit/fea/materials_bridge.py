"""Soft dependency on ``huntkit.materials`` (built in parallel by the materials-engineer).

Resolution order for a material reference:

1. ``dict``  -> used directly as an inline property dict (keys per docs/CONTRACTS.md §1).
2. ``str``   -> ``huntkit.materials.load(id)`` if that module exposes ``load``;
3.             else read ``data/materials/**/<id>.yaml`` directly;
4.             else fall back to the small built-in ``FALLBACK`` table below
               (flagged ``confidence: estimate`` so reports show it was not from the DB).

All property keys are the contract's SI-suffixed names (``youngs_modulus_mpa``, ``E1_mpa`` ...).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "materials"

# ASSUMPTION: handbook-typical values, used only if the materials DB has no record.
FALLBACK: dict[str, dict[str, Any]] = {
    "alu_7075_t6": {
        "name": "Aluminum 7075-T6 (fallback, MMPDS typical)",
        "category": "metals",
        "properties": {
            "density_kg_m3": 2810, "youngs_modulus_mpa": 71700, "shear_modulus_mpa": 26900,
            "poisson": 0.33, "yield_strength_mpa": 503, "ultimate_strength_mpa": 572,
            "fatigue_limit_mpa": 159,
        },
        "confidence": "estimate",
        "sources": ["fallback table in huntkit/fea/materials_bridge.py (MMPDS-typical)"],
    },
    "cfrp_ud_t700_epoxy": {
        "name": "UD carbon/epoxy, T700-class, roll-wrapped tube grade (fallback)",
        "category": "composites",
        "properties": {
            "density_kg_m3": 1550, "E1_mpa": 125000, "E2_mpa": 8500, "G12_mpa": 4500,
            "nu12": 0.30, "Xt_mpa": 2000, "Xc_mpa": 1100, "Yt_mpa": 45, "Yc_mpa": 180,
            "S_mpa": 70, "ply_thickness_mm": 0.125,
        },
        "confidence": "estimate",
        "sources": ["fallback table in huntkit/fea/materials_bridge.py (out-of-autoclave "
                    "T700/epoxy typical, ~55% Vf)"],
    },
    "epoxy_adhesive_toughened": {
        "name": "Toughened 2-part structural epoxy (fallback)",
        "category": "polymers",
        "properties": {
            "density_kg_m3": 1150, "youngs_modulus_mpa": 2000, "shear_modulus_mpa": 700,
            "poisson": 0.40, "lap_shear_strength_mpa": 20.0,
        },
        "confidence": "estimate",
        "sources": ["fallback; typical toughened epoxy lap shear on abraded CFRP/Al 15-25 MPa"],
    },
}

# Candidate DB ids tried (in order) when a frame asks for a generic carbon tube material.
CARBON_CANDIDATES = ["cfrp_ud_t700_epoxy", "cfrp_t700_epoxy_ud", "carbon_ud_t700_epoxy",
                     "cfrp_ud_t300_epoxy", "carbon_epoxy_ud", "cfrp_ud"]


@dataclass
class Mat:
    id: str
    name: str
    category: str
    props: dict
    confidence: str = "estimate"
    source: str = "inline"          # "huntkit.materials" | "yaml" | "fallback" | "inline"
    sources: list = field(default_factory=list)

    def get(self, key, default=None):
        return self.props.get(key, default)

    def require(self, key):
        if key not in self.props or self.props[key] is None:
            raise KeyError(f"material '{self.id}' has no property '{key}' (source={self.source})")
        return self.props[key]


def _from_record(rec: dict, mid: str, source: str) -> Mat:
    return Mat(id=rec.get("id", mid), name=rec.get("name", mid),
               category=rec.get("category", ""), props=dict(rec.get("properties", rec.get("props", {}))),
               confidence=str(rec.get("confidence", "estimate")), source=source,
               sources=list(rec.get("sources", []) or []))


def _try_huntkit_materials(mid: str) -> Mat | None:
    try:
        from huntkit import materials as hm  # noqa: WPS433
        load = getattr(hm, "load", None)
        if load is None:
            return None
        m = load(mid)
    except Exception:
        return None
    props = getattr(m, "props", None) or getattr(m, "properties", None) or {}
    return Mat(id=getattr(m, "id", mid), name=getattr(m, "name", mid),
               category=getattr(m, "category", ""), props=dict(props),
               confidence=str(getattr(m, "confidence", "")), source="huntkit.materials",
               sources=list(getattr(m, "sources", []) or []))


def _try_yaml(mid: str) -> Mat | None:
    if not DATA_DIR.exists():
        return None
    hits = sorted(DATA_DIR.rglob(f"{mid}.yaml")) + sorted(DATA_DIR.rglob(f"{mid}.yml"))
    if not hits:
        return None
    try:
        import yaml
        rec = yaml.safe_load(hits[0].read_text())
    except Exception:
        return None
    if not isinstance(rec, dict):
        return None
    return _from_record(rec, mid, "yaml")


def get_material(ref) -> Mat:
    """Resolve a material id / dict / Mat into a :class:`Mat`."""
    if isinstance(ref, Mat):
        return ref
    if hasattr(ref, "props") and hasattr(ref, "id"):   # a huntkit.materials.Material
        return Mat(id=ref.id, name=getattr(ref, "name", ref.id), category=getattr(ref, "category", ""),
                   props=dict(ref.props), confidence=str(getattr(ref, "confidence", "")),
                   source="huntkit.materials", sources=list(getattr(ref, "sources", []) or []))
    if isinstance(ref, dict):
        if "properties" in ref or "props" in ref:
            return _from_record(ref, ref.get("id", "inline"), "inline")
        return Mat(id=ref.get("id", "inline"), name=ref.get("name", "inline"),
                   category=ref.get("category", ""), props={k: v for k, v in ref.items()
                                                            if k not in ("id", "name", "category")},
                   source="inline")
    if isinstance(ref, str):
        for fn in (_try_huntkit_materials, _try_yaml):
            m = fn(ref)
            if m is not None and m.props:
                return m
        if ref in FALLBACK:
            return _from_record(FALLBACK[ref], ref, "fallback")
        raise KeyError(f"material '{ref}' not found in huntkit.materials, data/materials/ or the "
                       f"FEA fallback table; pass an inline property dict instead")
    raise TypeError(f"cannot interpret material reference {ref!r}")


def first_available(ids: list[str]) -> Mat:
    """First id that resolves from the DB (module or YAML); else the first fallback hit."""
    for mid in ids:
        for fn in (_try_huntkit_materials, _try_yaml):
            m = fn(mid)
            if m is not None and m.props:
                return m
    for mid in ids:
        if mid in FALLBACK:
            return _from_record(FALLBACK[mid], mid, "fallback")
    raise KeyError(f"none of {ids} found")


# ---- property accessors with contract key names ---------------------------------------
def E_of(m: Mat) -> float:
    return float(m.require("youngs_modulus_mpa"))


def G_of(m: Mat) -> float:
    g = m.get("shear_modulus_mpa")
    if g is None:
        nu = m.get("poisson", 0.3)
        g = E_of(m) / (2 * (1 + nu))
    return float(g)


def rho_of(m: Mat) -> float:
    return float(m.get("density_kg_m3", 0.0) or 0.0)
