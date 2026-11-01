"""huntkit.viz3d - parametric 3D pack model, GLB export, offline three.js viewer, PNG renders.

    python -m huntkit.viz3d.cli build [--spec designs/pack_5200/spec.yaml] [--out outputs/pack3d/]

Owner: viz3d. Geometry defaults are PLACEHOLDERS (see params.py) until the pack-designer sets them.
"""
from .params import DEFAULT_PARAMS, load_params  # noqa: F401
