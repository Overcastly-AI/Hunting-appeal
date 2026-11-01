"""Procedural camo engine: pattern spec (YAML dict) -> seamless, flat-colour RGB repeat.

Pipeline (see designs/apparel/camo/DESIGN.md for the design intent):

1. Every layer owns a scalar *field* built at a fixed "field resolution"
   (``field_px_per_mm``, independent of output DPI) as a weighted sum of components:
     - ``fbm``             periodic FFT fractal noise
     - ``voronoi_cells``   periodic Voronoi, flat random value per cell (slabs/plates)
     - ``voronoi_edges``   periodic Voronoi fissures  exp(-(F2-F1)/width)
   evaluated on (optionally) domain-warped coordinates, then normalised.
   ``roughness`` adds a small-scale fbm before thresholding => fractal edges.
   ``modulate`` adds another layer's base field => co-located (nested) shapes.
   Components with the same ``seed_key`` reuse the identical random draw, so two layers
   can be exact complements of each other (e.g. light vs dark slabs).
2. Threshold-to-layer stacking with *exact coverage*: working from the TOP layer down, each
   layer claims the highest-field fraction of the still-unclaimed area so that its final
   VISIBLE coverage equals ``coverage`` in the spec. The background colour gets the rest.
   The thresholds are found once at field resolution.
3. Output: each field is upsampled to the output DPI with a separable periodic cubic
   (Catmull-Rom) resampler and re-thresholded with the stored thresholds, row strip by row
   strip — so edges stay smooth at 300 dpi and memory stays bounded.
4. Optional micro-texture overlay (tonal luminance grain). OFF by default: it breaks
   flat-colour separations; meant for digital sublimation only.

Everything is periodic, so the output tiles seamlessly; everything is seeded, so it is
deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from . import color, noise

PATTERN_DIR = Path(__file__).resolve().parents[2] / "designs" / "apparel" / "camo"


# ----------------------------------------------------------------------------- spec I/O
def load_pattern(name_or_path: str | Path) -> dict:
    p = Path(name_or_path)
    if not p.suffix:
        p = PATTERN_DIR / f"{name_or_path}.yaml"
    with open(p, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    spec.setdefault("name", p.stem)
    return spec


def palette_hexes(spec: dict) -> list[str]:
    return [c["hex"] for c in spec["palette"]]


def _color_index(spec: dict, key: str) -> int:
    for i, c in enumerate(spec["palette"]):
        if c["key"] == key:
            return i
    raise KeyError(f"layer colour {key!r} not in palette")


# ----------------------------------------------------------------------------- field build
@dataclass
class FieldModel:
    """Fields + thresholds at field resolution; reusable for any output DPI."""

    spec: dict
    grid: noise.Grid
    fields: list[np.ndarray]                  # per layer (spec order), normalised
    thresholds: list[float]                   # per layer (spec order)
    color_idx: list[int]                      # per layer
    background_idx: int
    labels: np.ndarray                        # label map at field resolution
    info: dict[str, Any] = dc_field(default_factory=dict)


def _component(comp: dict, grid: noise.Grid, seed: int, Y, X, cache: dict,
               default_key: str) -> np.ndarray:
    typ = comp["type"]
    key = comp.get("seed_key", default_key)
    if typ == "fbm":
        ck = ("fbm", key, comp["scale_mm"], comp.get("min_mm"), comp.get("beta", 1.8),
              comp.get("aniso_ratio", 1.0), comp.get("aniso_angle_deg", 0.0))
        if ck not in cache:
            cache[ck] = noise.fbm(grid, noise.substream(seed, f"fbm:{key}"),
                                  comp["scale_mm"], comp.get("min_mm"), comp.get("beta", 1.8),
                                  comp.get("aniso_ratio", 1.0), comp.get("aniso_angle_deg", 0.0))
        base = cache[ck]
        return noise.sample_periodic(base, grid, Y, X, order=1)
    if typ in ("voronoi_cells", "voronoi_edges"):
        vk = ("vor", key, comp["cell_mm"], comp.get("jitter", 1.0), id(Y))
        if vk not in cache:
            cache[vk] = noise.voronoi(grid, noise.substream(seed, f"vor:{key}"),
                                      comp["cell_mm"], Y, X, comp.get("jitter", 1.0))
        v = cache[vk]
        if typ == "voronoi_cells":
            if comp.get("value_seed"):
                # re-randomise cell values without moving the cells
                r = noise.substream(seed, f"vorval:{comp['value_seed']}")
                vals = r.uniform(-1, 1, int(v["cell"].max()) + 1).astype(np.float32)
                return vals[v["cell"]]
            return v["value"]
        width = float(comp.get("width_mm", 10.0))
        return np.exp(-(v["f2"] - v["f1"]) / width).astype(np.float32)
    raise ValueError(f"unknown field component type {typ!r}")


def build_fields(spec: dict, seed: int, width_mm: float | None = None,
                 height_mm: float | None = None) -> FieldModel:
    rep = spec.get("repeat_mm", {})
    W = float(width_mm or rep.get("width", 760))
    H = float(height_mm or rep.get("height", 760))
    grid = noise.Grid.from_density(W, H, float(spec.get("field_px_per_mm", 1.25)))
    layers = spec["layers"]
    cache: dict = {}
    warp_cache: dict = {}
    Y0, X0 = grid.coords_mm()

    base_fields: dict[str, np.ndarray] = {}
    for li, layer in enumerate(layers):
        fs = layer["field"]
        w = fs.get("warp")
        if w:
            wk = (w.get("seed_key", f"warp:{layer['name']}"), w["scale_mm"], w["amp_mm"],
                  w.get("iterations", 1), w.get("beta", 2.0))
            if wk not in warp_cache:
                warp_cache[wk] = noise.warp_coords(grid, noise.substream(seed, f"warp:{wk[0]}"),
                                                   w["scale_mm"], w["amp_mm"],
                                                   w.get("iterations", 1), w.get("beta", 2.0))
            Y, X = warp_cache[wk]
        else:
            Y, X = Y0, X0
        acc = np.zeros((grid.ny, grid.nx), np.float32)
        for ci, comp in enumerate(fs["components"]):
            c = noise.normalize(_component(comp, grid, seed, Y, X, cache,
                                           f"{layer['name']}:{ci}"))
            acc += float(comp.get("weight", 1.0)) * c
        base_fields[layer["name"]] = noise.normalize(acc)

    fields = []
    for layer in layers:
        fs = layer["field"]
        f = base_fields[layer["name"]].copy()
        for m in fs.get("modulate", []) or []:
            f += float(m["weight"]) * base_fields[m["by"]]
        f = noise.normalize(f)
        r = fs.get("roughness")
        if r:
            rk = r.get("seed_key", f"rough:{layer['name']}")
            rn = noise.fbm(grid, noise.substream(seed, f"rough:{rk}"), r["scale_mm"],
                           r.get("min_mm"), r.get("beta", 1.2))
            f = noise.normalize(f + float(r["amp"]) * rn)
        fields.append(f)

    # exact-coverage stacking, top layer (last in list) first
    n = grid.nx * grid.ny
    claimed = np.zeros((grid.ny, grid.nx), bool)
    bg = _color_index(spec, spec["background"])
    labels = np.full((grid.ny, grid.nx), bg, np.uint8)
    thresholds = [0.0] * len(layers)
    cidx = [_color_index(spec, L["color"]) for L in layers]
    total = sum(float(L["coverage"]) for L in layers)
    if total >= 1.0:
        raise ValueError(f"layer coverages sum to {total:.3f}; must leave room for background")
    for li in reversed(range(len(layers))):
        need = int(round(float(layers[li]["coverage"]) * n))
        vals = fields[li][~claimed]
        if need <= 0:
            thresholds[li] = np.inf
            continue
        need = min(need, vals.size)
        t = float(np.partition(vals, vals.size - need)[vals.size - need])
        # take strictly the top `need` values: threshold just below the need-th largest
        thresholds[li] = np.nextafter(np.float32(t), np.float32(-np.inf))
        sel = (fields[li] > thresholds[li]) & ~claimed
        labels[sel] = cidx[li]
        claimed |= sel
    return FieldModel(spec, grid, fields, thresholds, cidx, bg, labels,
                      {"width_mm": W, "height_mm": H})


# ----------------------------------------------------------------------------- render
def render_labels(model: FieldModel, dpi: float, strip_rows: int = 512) -> np.ndarray:
    """Label map (uint8 palette indices) of one repeat at ``dpi``."""
    W, H = model.info["width_mm"], model.info["height_mm"]
    NX = max(8, int(round(W / 25.4 * dpi)))
    NY = max(8, int(round(H / 25.4 * dpi)))
    up = noise.PeriodicUpsampler(model.grid.ny, model.grid.nx, NY, NX)
    out = np.full((NY, NX), model.background_idx, np.uint8)
    order = list(reversed(range(len(model.fields))))
    for r0 in range(0, NY, strip_rows):
        r1 = min(NY, r0 + strip_rows)
        claimed = np.zeros((r1 - r0, NX), bool)
        lab = out[r0:r1]
        for li in order:
            f = up.rows(model.fields[li], r0, r1)
            sel = (f > model.thresholds[li]) & ~claimed
            lab[sel] = model.color_idx[li]
            claimed |= sel
    return out


def labels_to_rgb(labels: np.ndarray, palette: list[str]) -> np.ndarray:
    lut = np.array([color.hex_to_rgb8(h) for h in palette], np.uint8)
    return lut[labels]


def apply_micro_texture(rgb: np.ndarray, spec: dict, seed: int, width_mm: float,
                        height_mm: float) -> np.ndarray:
    """Optional tonal grain (multiplicative in linear light). Periodic => still seamless."""
    mt = spec.get("micro_texture") or {}
    if not mt.get("enabled", False):
        return rgb
    NY, NX = rgb.shape[:2]
    ppmm = min(NX / width_mm, float(mt.get("max_px_per_mm", 4.0)))
    g = noise.Grid.from_density(width_mm, height_mm, ppmm)
    n = noise.fbm(g, noise.substream(seed, "micro_texture"), mt.get("scale_mm", 3.0),
                  mt.get("min_mm"), mt.get("beta", 1.0))
    up = noise.PeriodicUpsampler(g.ny, g.nx, NY, NX)
    gain = 1.0 + float(mt.get("amp", 0.06)) * np.clip(up.full(n), -3, 3)
    lin = color.srgb_to_linear(rgb / 255.0) * gain[..., None]
    return np.round(color.linear_to_srgb(np.clip(lin, 0, 1)) * 255).astype(np.uint8)


def generate(pattern_spec: dict, palette: list[str] | None, width_mm: float | None,
             height_mm: float | None, dpi: float, seed: int | None = None) -> np.ndarray:
    """CONTRACT §4: return an (H, W, 3) uint8 sRGB seamless repeat.

    ``palette`` overrides the spec colours (same order / length as spec palette) — handy
    for recolouring a pattern into another colourway. ``width_mm``/``height_mm`` default to
    the spec repeat. ``seed`` defaults to the spec seed.
    """
    seed = int(pattern_spec.get("seed", 0) if seed is None else seed)
    pal = list(palette) if palette else palette_hexes(pattern_spec)
    if len(pal) != len(pattern_spec["palette"]):
        raise ValueError("palette override must have one colour per spec palette entry")
    model = build_fields(pattern_spec, seed, width_mm, height_mm)
    labels = render_labels(model, dpi)
    rgb = labels_to_rgb(labels, pal)
    return apply_micro_texture(rgb, pattern_spec, seed, model.info["width_mm"],
                               model.info["height_mm"])


def coverage(labels: np.ndarray, n_colors: int) -> np.ndarray:
    return np.bincount(labels.ravel(), minlength=n_colors) / labels.size


def target_coverage(spec: dict) -> np.ndarray:
    n = len(spec["palette"])
    t = np.zeros(n)
    for L in spec["layers"]:
        t[_color_index(spec, L["color"])] += float(L["coverage"])
    t[_color_index(spec, spec["background"])] += 1.0 - sum(float(L["coverage"]) for L in spec["layers"])
    return t
