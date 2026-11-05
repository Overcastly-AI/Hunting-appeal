"""Membrane models per fabric and seam / attachment strengths, from the material records.

Every stiffness is derived in ``fabrics.yaml`` (break strength from ``data/materials`` over an
ASSUMPTION break elongation); see that file for the basis of each number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from huntkit import materials as MAT

HERE = Path(__file__).parent
G = 9.81


@lru_cache(maxsize=1)
def _table() -> dict:
    return yaml.safe_load((HERE / "fabrics.yaml").read_text())


@dataclass
class FabricModel:
    material_id: str
    k_warp: float            # N/mm (membrane secant stiffness per unit width)
    k_weft: float
    shear: float             # N/mm per rad (engineering shear)
    bending: float           # N mm (plate bending stiffness per unit width)
    compression: float       # fraction of k kept in compression
    areal_kg_mm2: float      # mass per mm^2
    strip_warp: float        # N/mm break strength
    strip_weft: float
    basis: dict = field(default_factory=dict)

    def scaled(self, **kw) -> "FabricModel":
        d = dict(self.__dict__)
        for k, v in kw.items():
            if k.endswith("_scale"):
                d[k[:-6]] *= float(v)
            else:
                d[k] = v
        return FabricModel(**d)


def fabric(material_id: str, **override) -> FabricModel:
    t = _table()
    spec = dict(t["defaults"])
    spec.update(t["fabrics"].get(material_id, {}))
    spec.update(override)
    m = MAT.load(material_id)
    g2s = float(t["grab_to_strip_mm"])
    basis = {}
    sw = spec.get("strip_warp_n_mm")
    if sw is None:
        sw = float(m.require("grab_warp_n")) / g2s
        basis["strip_warp"] = f"{m.id}.grab_warp_n / {g2s} mm"
    else:
        basis["strip_warp"] = "ASSUMPTION fabrics.yaml"
    sf = spec.get("strip_weft_n_mm")
    if sf is None:
        sf = float(m.get("grab_weft_n", m.get("grab_warp_n"))) / g2s
        basis["strip_weft"] = f"{m.id}.grab_weft_n / {g2s} mm"
    else:
        basis["strip_weft"] = "ASSUMPTION fabrics.yaml"
    gsm = float(m.require("areal_density_gsm"))
    return FabricModel(material_id=material_id, k_warp=sw / float(spec["elong_warp"]),
                       k_weft=sf / float(spec["elong_weft"]), shear=float(spec["shear_n_mm"]),
                       bending=float(spec["bending_n_mm"]), compression=float(spec["compression"]),
                       areal_kg_mm2=gsm * 1e-9, strip_warp=sw, strip_weft=sf, basis=basis)


def stitch_strength_n_mm(thread_id: str = "bonded_nylon_tex90", stitch_mm: float = 3.5,
                         stitch: str = "301") -> float:
    """Thread-limited seam strength: SPI x thread strength x 1.5 (301) or 1.7 (401), per mm.
    Source: docs/research/cloth_sim_methods.md (A&E / Coats seam-engineering rule)."""
    t = float(MAT.load(thread_id).require("breaking_strength_n"))
    loop = {"301": 1.5, "401": 1.7}.get(str(stitch), 1.5)
    return loop * t / stitch_mm


def seam_strength_n_mm(mat_a: str, mat_b: str, thread_id="bonded_nylon_tex90", stitch_mm=3.5,
                       stitch="301") -> dict:
    """Seam strength = min(thread rule, efficiency x weaker fabric strip strength across the seam).
    ASSUMPTION: the weaker of warp/weft is taken (the seam crosses both yarn sets somewhere)."""
    eff = float(_table()["seam_efficiency"])
    fa, fb = fabric(mat_a), fabric(mat_b)
    fab = eff * min(fa.strip_warp, fa.strip_weft, fb.strip_warp, fb.strip_weft)
    thr = stitch_strength_n_mm(thread_id, stitch_mm, stitch)
    return {"strength_n_mm": min(fab, thr), "thread_n_mm": thr, "fabric_n_mm": fab,
            "governs": "thread" if thr < fab else "fabric", "thread_id": thread_id, "stitch_mm": stitch_mm,
            "stitch": stitch}


def webbing(material_id: str) -> dict:
    """EA [N] (break / break elongation) and break strength of a webbing record."""
    m = MAT.load(material_id)
    brk = float(m.require("breaking_strength_n"))
    el = float(m.get("elongation_at_break_pct", 15.0)) / 100.0
    return {"id": material_id, "break_n": brk, "EA_n": brk / el, "width_mm": float(m.get("width_mm", 25))}
