"""huntkit.camo — procedural, seamless, original camo patterns + solid colorways.

Contract (docs/CONTRACTS.md §4):
    generate(pattern_spec, palette, width_mm, height_mm, dpi, seed) -> (H, W, 3) uint8 RGB
Patterns: designs/apparel/camo/<pattern>.yaml   Solids: designs/apparel/colorways.yaml
CLI: python -m huntkit.camo.cli {render,swatches,mocks,analyze,all}
"""
from .engine import generate, load_pattern, build_fields, render_labels, coverage, target_coverage
from . import color, noise, vision

__all__ = ["generate", "load_pattern", "build_fields", "render_labels", "coverage",
           "target_coverage", "color", "noise", "vision"]
