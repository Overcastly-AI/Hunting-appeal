"""Parameters for the 3D pack model.

Source of truth (pack-designer): ``designs/pack_5200/geometry.yaml`` (+ DESIGN.md, panels.yaml).
The model reads frame hard points, crown settings, bag / lid / pocket / shelf / wing / hipbelt /
harness dimensions from it. Frame TUBE SIZES come from ``designs/pack_5200/frame.yaml`` (FEA
agent) when it exists; until then the ``frame_tubes`` below are PLACEHOLDERS.

Everything in DEFAULT_PARAMS that is not read from geometry.yaml is a VISUAL PLACEHOLDER
(strap paths, foam thicknesses, mannequin anthropometry, quarter proxy size...). Override any of it
with a ``viz3d:`` mapping in spec.yaml or a dict passed to ``build_pack``.

Units mm, g. Coordinates = FCS (huntkit.fea): x lateral (+ wearer's right), y aft (+ toward the
bag; the wearer stands at -y), z up, z = 0 at the stay feet.
"""
from __future__ import annotations

import copy
from pathlib import Path

CU_IN_TO_L = 0.016387064
REPO = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = REPO / "designs" / "pack_5200" / "spec.yaml"

DEFAULT_PARAMS: dict = {
    "name": "Pack 5200",
    "target_volume_l": 5200 * CU_IN_TO_L,   # spec volume.main_bag_cu_in -> 85.2 L
    "torsos_in": [15.0, 19.0, 23.0],
    "default_torso_in": 19.0,
    "colorway": "talus",                    # colorways.yaml accent_pairings id
    "geometry_yaml": str(REPO / "designs" / "pack_5200" / "geometry.yaml"),
    "frame_yaml": "auto",                   # <spec dir>/frame.yaml if present (tube sizes)
    # PLACEHOLDER tube sizes until frame.yaml exists (FEA agent sizes them)
    "frame_tubes": {"stay_od": 19.05, "crown_leg_od": 15.9, "bar_od": 15.9, "post_od": 12.7},
    "lumbar_plate_t": 3.0, "spine_w": 46.0, "spine_t": 3.0, "yoke_plate_t": 1.5,
    "bag_edge_radius": 10.0, "bag_top_radius": 14.0,
    "lid_edge_radius": 22.0,
    "shard_thick": 1.2,
    "compression_z": [180.0, 400.0, 620.0],   # from the concept sketch (DESIGN.md: 3 x 25 mm per side)
    "hipbelt": {"size": "M", "thick": 20.0, "height_center": 130.0, "height_wing": 100.0, "height_tip": 95.0},
    "harness": {"thick": 16.0, "sternum_drop": 150.0},
    "haul_pullback_y": None,                 # None -> geometry.yaml bag.haul_mode_pullback_y_max
    "quarter": {"width": 280.0, "depth": 190.0, "height": 620.0},   # bone-in elk hindquarter proxy
    "mannequin": {"enabled": True},
    "fea": {"enabled": True},
}


def deep_merge(base: dict, over: dict | None) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_params(spec_path: str | Path | None = DEFAULT_SPEC, overrides: dict | None = None) -> dict:
    """DEFAULT_PARAMS <- spec.yaml (volume, torso range, optional viz3d: block) <- overrides.
    geometry.yaml / frame.yaml are looked up next to the spec."""
    import yaml
    p = copy.deepcopy(DEFAULT_PARAMS)
    if spec_path:
        spec_path = Path(spec_path)
        spec = yaml.safe_load(spec_path.read_text()) or {}
        p["name"] = spec.get("name", p["name"])
        cu = (spec.get("volume") or {}).get("main_bag_cu_in")
        if cu:
            p["target_volume_l"] = float(cu) * CU_IN_TO_L
        tr = (spec.get("fit") or {}).get("torso_range_in")
        if tr and len(tr) == 2:
            lo, hi = float(tr[0]), float(tr[1])
            p["torsos_in"] = [lo, (lo + hi) / 2, hi]
            p["default_torso_in"] = (lo + hi) / 2
        gy = spec_path.parent / "geometry.yaml"
        if gy.exists():
            p["geometry_yaml"] = str(gy)
        p = deep_merge(p, spec.get("viz3d"))
        if p.get("frame_yaml") == "auto":
            fy = spec_path.parent / "frame.yaml"
            p["frame_yaml"] = str(fy) if fy.exists() else None
    p = deep_merge(p, overrides)
    if p.get("frame_yaml") == "auto":
        fy = Path(p["geometry_yaml"]).parent / "frame.yaml"
        p["frame_yaml"] = str(fy) if fy.exists() else None
    return p


def load_geometry(p: dict) -> dict:
    import yaml
    return yaml.safe_load(Path(p["geometry_yaml"]).read_text())
