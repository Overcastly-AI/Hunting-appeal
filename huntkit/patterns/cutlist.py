"""Cut sheet / cut list (CSV + Markdown)."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .piece import Piece

COLUMNS = ["piece_id", "piece", "material", "size", "qty", "mirror", "face", "area_m2",
           "total_area_m2", "perimeter_mm", "seam_allowance_mm", "mass_g"]


def _areal_density(material_id: str):
    """Soft dependency on huntkit.materials: areal density in g/m2 if available."""
    if not material_id:
        return None
    try:
        from huntkit import materials  # type: ignore
        m = materials.load(material_id)
        return m.get("areal_density_gsm")
    except Exception:
        return None


@dataclass
class CutList:
    rows: list[dict]

    def csv(self) -> str:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUMNS)
        w.writeheader()
        for r in self.rows:
            w.writerow(r)
        return buf.getvalue()

    def markdown(self) -> str:
        head = ["Piece ID", "Piece", "Material", "Size", "Qty", "Mirror", "Face", "Area m² (ea)",
                "Total m²", "Perimeter mm", "SA mm", "Mass g"]
        out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for r in self.rows:
            out.append("| " + " | ".join("" if r[k] is None else str(r[k]) for k in COLUMNS) + " |")
        tot = {}
        for r in self.rows:
            tot[r["material"]] = tot.get(r["material"], 0.0) + r["total_area_m2"]
        out.append("")
        out.append("**Net piece area by material** (before marker waste): " +
                   ", ".join(f"{k or '-'}: {v:.4f} m² ({v * 10.7639:.3f} ft²)" for k, v in tot.items()))
        return "\n".join(out)

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.markdown() if path.suffix.lower() == ".md" else self.csv())
        return path

    @property
    def total_area_m2(self) -> float:
        return sum(r["total_area_m2"] for r in self.rows)


def cut_list(pieces: Iterable[Piece]) -> CutList:
    """One row per piece (per size): cut area/perimeter from the cut line."""
    rows = []
    for p in pieces:
        a = p.area_mm2 / 1e6
        sa = p.seam_allowance_mm
        sa_s = f"{sa:g}" if not isinstance(sa, dict) else \
            "; ".join(f"{k}={v:g}" for k, v in sa.items())
        gsm = _areal_density(p.material_id)
        rows.append({"piece_id": p.piece_id, "piece": p.name, "material": p.material_id,
                     "size": p.size, "qty": p.quantity, "mirror": "L+R" if p.mirror else "",
                     "face": p.face.upper(), "area_m2": round(a, 5),
                     "total_area_m2": round(a * p.quantity, 5),
                     "perimeter_mm": round(p.cut_perimeter_mm, 1), "seam_allowance_mm": sa_s,
                     "mass_g": None if gsm is None else round(a * p.quantity * gsm, 1)})
    return CutList(rows)
