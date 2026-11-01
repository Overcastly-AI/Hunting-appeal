"""Parameters for the 3D pack model.

EVERY number in DEFAULT_PARAMS is a PLACEHOLDER (visual stand-in) until the pack-designer sets the
real geometry. Override any of them from the design spec: add a ``viz3d:`` mapping to
``designs/pack_5200/spec.yaml`` (same nested keys), or pass a dict to ``build_pack``.
A ``designs/pack_5200/frame.yaml`` (huntkit.fea.frames.load_frame_params format) next to the spec,
if present, replaces the placeholder frame so the render always uses the FEA frame.

Units: mm, g; coordinates = huntkit.fea convention (x lateral, y aft toward the bag, z up,
z = 0 at the stay feet; the wearer stands at -y).
"""
from __future__ import annotations

import copy
from pathlib import Path

CU_IN_TO_L = 0.016387064

DEFAULT_PARAMS: dict = {
    "placeholder": True,           # shown in the viewer header until the pack-designer signs off
    "name": "Pack 5200",
    "target_volume_l": 5200 * CU_IN_TO_L,   # spec volume.main_bag_cu_in -> 85.2 L
    "torsos_in": [15.0, 19.0, 23.0],         # fit comparison (spec fit.torso_range_in + mid)
    "default_torso_in": 19.0,
    "colorway": "talus",           # designs/apparel/colorways.yaml accent_pairings id
    # PLACEHOLDER frame geometry, passed to huntkit.fea.frames.carbon_variant(**frame)
    "frame": {
        "height": 760.0, "width_top": 200.0, "width_bottom": 270.0,
        "lumbar_z": 135.0, "lumbar_depth": 30.0, "lumbar_width": 130.0, "top_sweep": 25.0,
        "hip_z": 100.0, "shelf_z": 40.0, "shelf_strap_z": 300.0, "lash_z": 520.0,
        "stay_style": "curved", "n_stay": 24, "yoke_drop": 50.0,
    },
    "frame_yaml": "auto",          # "auto" -> <spec dir>/frame.yaml if it exists; None disables
    "frame_plates": {"thick": 2.5, "lumbar_h": 100.0, "corner_leg": 85.0},
    # PLACEHOLDER main bag: tapered rounded box hugging the frame; depth auto-scaled to the target
    "bag": {
        "z_bottom": 55.0, "height": 715.0,
        "a_bottom": 150.0, "a_top": 156.0, "a_bulge": 14.0,      # half-widths (x)
        "b_bottom": 115.0, "b_top": 100.0, "b_bulge": 38.0,      # half-depths (y), pre-scaling
        "n_front": 2.7, "n_back": 5.0, "r_bottom": 35.0, "r_top": 85.0,
        "gap_to_frame": 6.0, "solve_depth": True, "rings": 72, "segments": 96,
    },
    "lid": {"height": 105.0, "overhang_x": 14.0, "overhang_front": 22.0, "overlap": 32.0, "radius": 46.0},
    "side_pocket": {"theta": [-0.75, 0.62], "z": [35.0, 335.0], "thick": 42.0},
    "front_pocket": {"theta_half": 0.62, "z": [110.0, 500.0], "thick": 16.0},
    "compression": {"z": [205.0, 470.0], "width": 25.0, "thick": 2.4, "theta": [-1.15, 1.22]},
    "hipbelt": {"height_center": 125.0, "height_wing": 105.0, "height_end": 72.0,
                "thick": 18.0, "end_deg": 150.0, "wing_deg": [36.0, 108.0], "pocket_deg": [110.0, 143.0]},
    "harness": {"width": 72.0, "thick": 16.0, "sternum_drop": 145.0},
    "shelf": {"depth": 230.0, "thick": 9.0},
    "quarter": {"width": 300.0, "depth": 200.0, "height": 640.0},   # bone-in elk hindquarter proxy
    "mannequin": {"enabled": True},
    "fea": {"enabled": True},
    "camo_tile_mm": 500.0,
}


def deep_merge(base: dict, over: dict | None) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_params(spec_path: str | Path | None = None, overrides: dict | None = None) -> dict:
    """DEFAULT_PARAMS <- spec.yaml (volume, torso range, optional viz3d: block) <- overrides."""
    p = copy.deepcopy(DEFAULT_PARAMS)
    if spec_path:
        import yaml
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
        p = deep_merge(p, spec.get("viz3d"))
        if p.get("frame_yaml") == "auto":
            fy = spec_path.parent / "frame.yaml"
            p["frame_yaml"] = str(fy) if fy.exists() else None
    elif p.get("frame_yaml") == "auto":
        p["frame_yaml"] = None
    return deep_merge(p, overrides)
