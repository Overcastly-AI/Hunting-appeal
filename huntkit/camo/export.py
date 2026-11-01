"""Exports and previews for camo patterns and the solid colorway line.

Big print files go to ``outputs/camo/``; small (<= 1.5 MB) previews go to
``designs/apparel/camo/previews/`` so they are tracked in git.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from . import color, engine, vision

ROOT = Path(__file__).resolve().parents[2]
PREVIEW_DIR = ROOT / "designs" / "apparel" / "camo" / "previews"
OUT_DIR = ROOT / "outputs" / "camo"
COLORWAYS = ROOT / "designs" / "apparel" / "colorways.yaml"
MAX_PREVIEW_BYTES = 1_500_000


# ----------------------------------------------------------------------------- helpers
def _font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for p in (f"/usr/share/fonts/truetype/dejavu/{name}", name):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def save_png(img: Image.Image | np.ndarray, path: Path, dpi: float | None = None,
             limit: int | None = None) -> Path:
    """Save PNG; palette-mode when the image has <= 256 colours (exact), and if over
    ``limit`` bytes, retry with adaptive 256-colour quantisation, then downscaling."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(img)
    path.parent.mkdir(parents=True, exist_ok=True)
    kw = {"optimize": True}
    if dpi:
        kw["dpi"] = (dpi, dpi)
    im = img.convert("RGB")
    if im.getcolors(256) is not None:
        im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    im.save(path, **kw)
    while limit and path.stat().st_size > limit:
        if im.mode != "P":
            im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE)
        else:
            im = im.convert("RGB").resize((int(im.width * 0.8), int(im.height * 0.8)),
                                          Image.Resampling.LANCZOS)
            im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                             dither=Image.Dither.NONE)
        im.save(path, **kw)
    return path


def _resize(rgb: np.ndarray, w: int, h: int, nearest: bool = False) -> np.ndarray:
    m = Image.Resampling.NEAREST if nearest else Image.Resampling.LANCZOS
    return np.asarray(Image.fromarray(rgb).resize((w, h), m))


def _label(img: Image.Image, xy, text, size=18, fill=(20, 20, 20), bold=False):
    ImageDraw.Draw(img).text(xy, text, font=_font(size, bold), fill=fill)


def load_colorways(path: Path = COLORWAYS) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def colorway_section(cw: dict, section: str | None = None) -> dict:
    """``None``/"primary" -> top-level (Owner Base system); "alternate" -> Cirquefall system."""
    if section in (None, "primary"):
        return cw
    return cw[section]


def all_solids(cw: dict) -> list[dict]:
    return list(cw.get("solids", [])) + list(cw.get("alternate", {}).get("solids", []))


def _solid_hex(cw: dict, key: str) -> str:
    for s in all_solids(cw):
        if s["key"] == key:
            return s["hex"]
    raise KeyError(key)


def render_rgb(spec: dict, dpi: float, seed: int | None = None) -> np.ndarray:
    rep = spec["repeat_mm"]
    return engine.generate(spec, None, rep["width"], rep["height"], dpi, seed)


# ----------------------------------------------------------------------------- print files
def export_repeat(spec: dict, dpi: float = 300, out: Path | None = None,
                  seed: int | None = None, tiff: bool = True) -> dict:
    """Full-resolution seamless repeat -> outputs/camo/<name>_repeat_<dpi>dpi.{png,tif}."""
    out = Path(out or OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    rgb = render_rgb(spec, dpi, seed)
    base = out / f"{spec['name']}_repeat_{int(dpi)}dpi"
    files = {}
    im = Image.fromarray(rgb)
    files["png"] = save_png(im, base.with_suffix(".png"), dpi=dpi)
    if tiff:
        im.save(base.with_suffix(".tif"), compression="tiff_lzw", dpi=(dpi, dpi))
        files["tif"] = base.with_suffix(".tif")
    return {"files": files, "shape": rgb.shape}


def export_separations_svg(spec: dict, out: Path | None = None, px_per_mm: float = 1.0,
                           seed: int | None = None) -> Path:
    """Vector colour separations (one <g> per ink) of one repeat, in mm units."""
    import contourpy
    from scipy import ndimage

    out = Path(out or OUT_DIR)
    rep = spec["repeat_mm"]
    seed = spec.get("seed", 0) if seed is None else seed
    model = engine.build_fields(spec, seed)
    labels = engine.render_labels(model, px_per_mm * 25.4)
    H, W = labels.shape
    sx, sy = rep["width"] / W, rep["height"] / H
    pal = spec["palette"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{rep["width"]}mm" '
             f'height="{rep["height"]}mm" viewBox="0 0 {rep["width"]} {rep["height"]}">']
    order = [model.background_idx] + [i for i in range(len(pal)) if i != model.background_idx]
    for i in order:
        c = pal[i]
        if i == model.background_idx:
            parts.append(f'<g id="{c["key"]}" inkscape:label="{c["name"]}" '
                         f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">'
                         f'<rect width="{rep["width"]}" height="{rep["height"]}" '
                         f'fill="{c["hex"]}"/></g>')
            continue
        m = ndimage.gaussian_filter((labels == i).astype(np.float32), 0.6, mode="wrap")
        gen = contourpy.contour_generator(z=m, fill_type=contourpy.FillType.OuterCode)
        pts_list, codes_list = gen.filled(0.5, 2.0)
        d = []
        for pts, codes in zip(pts_list, codes_list):
            for (x, y), code in zip(pts, codes):
                X, Y = (x + 0.5) * sx, (y + 0.5) * sy
                d.append(f"M{X:.1f} {Y:.1f}" if code == 1 else
                         ("Z" if code == 79 else f"L{X:.1f} {Y:.1f}"))
        parts.append(f'<g id="{c["key"]}"><path fill="{c["hex"]}" fill-rule="evenodd" '
                     f'd="{" ".join(d)}"/></g>')
    parts.append("</svg>")
    p = out / f"{spec['name']}_separations.svg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


# ----------------------------------------------------------------------------- analysis
def analyze(spec: dict, seed: int | None = None) -> dict:
    """Coverage, luminance distribution, dichromat contrast, distance contrast, panel test."""
    seed = spec.get("seed", 0) if seed is None else seed
    hexes = engine.palette_hexes(spec)
    rep = spec["repeat_mm"]
    model = engine.build_fields(spec, seed)
    lab1 = engine.render_labels(model, 25.4)          # 1 px / mm
    cov = engine.coverage(lab1, len(hexes))
    tgt = engine.target_coverage(spec)
    rgb = np.array([color.hex_to_srgb(h) for h in hexes])
    labs = color.srgb_to_lab(rgb)
    sim = color.simulate_dichromat(rgb, "ungulate")
    labs_sim = color.srgb_to_lab(sim)
    Ls = labs[:, 0]
    band = {"dark_L<40": float(cov[Ls < 40].sum()), "mid_40-60": float(cov[(Ls >= 40) & (Ls < 60)].sum()),
            "light_L>=60": float(cov[Ls >= 60].sum())}
    mean_L = float((cov * Ls).sum())
    # pairwise dichromat table
    table = color.palette_contrast_table(hexes, "ungulate")
    keys = [c["key"] for c in spec["palette"]]
    for r in table:
        r["pair"] = f"{keys[r['i']]}/{keys[r['j']]}"
    collapsed = [r["pair"] for r in table if r["de00_dichromat"] < 5.0]
    # distance contrast on 2x2 tiles at 1 px/mm, deer acuity + deer colour, human acuity + colour
    tile = engine.labels_to_rgb(np.tile(lab1, (2, 2)), hexes)
    tile_deer = color.simulate_dichromat(tile, "ungulate")
    dist = {}
    for d in vision.STANDARD_DISTANCES_M:
        _, ih = vision.simulate_distance(tile, 1.0, d, vision.HUMAN_CPD, display_shape=(8, 8))
        _, iu = vision.simulate_distance(tile_deer, 1.0, d, vision.UNGULATE_CPD, display_shape=(8, 8))
        dist[f"{d}m"] = {"human_rms_contrast": round(ih["rms_contrast"], 4),
                         "ungulate_rms_contrast": round(iu["rms_contrast"], 4),
                         "ungulate_cycle_mm": round(iu["cycle_mm"], 1)}
    dist["0m"] = {"human_rms_contrast": round(color.rms_contrast(color.image_luminance(tile)), 4),
                  "ungulate_rms_contrast": round(color.rms_contrast(color.image_luminance(tile_deer)), 4)}
    # mean colour vs habitat backgrounds (deer view)
    mean_lin = (cov[:, None] * color.srgb_to_linear(rgb)).sum(0)
    mean_srgb = color.linear_to_srgb(mean_lin)
    mean_lab_sim = color.srgb_to_lab(color.simulate_dichromat(mean_srgb, "ungulate"))
    bg = {k: round(float(color.delta_e2000(
        mean_lab_sim, color.srgb_to_lab(color.simulate_dichromat(color.hex_to_srgb(h), "ungulate")))), 1)
        for k, h in color.BACKGROUNDS.items()}
    return {
        "pattern": spec["name"], "seed": seed, "repeat_mm": rep,
        "coverage": {k: round(float(c), 4) for k, c in zip(keys, cov)},
        "coverage_target": {k: round(float(c), 4) for k, c in zip(keys, tgt)},
        "coverage_max_abs_error": round(float(np.abs(cov - tgt).max()), 4),
        "palette_L": {k: round(float(v), 1) for k, v in zip(keys, Ls)},
        "palette_L_ungulate": {k: round(float(v), 1) for k, v in zip(keys, labs_sim[:, 0])},
        "luminance_bands": {k: round(v, 3) for k, v in band.items()},
        "coverage_weighted_mean_L": round(mean_L, 1),
        "dichromat_pairs": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
                             if k not in ("i", "j")} for r in table],
        "dichromat_collapsed_pairs_dE00_lt_5": collapsed,
        "distance_rms_contrast": dist,
        "mean_colour_hex": color.rgb8_to_hex(mean_srgb * 255),
        "mean_vs_backgrounds_dE00_ungulate": bg,
        "panel_test": panel_test(lab1, Ls),
    }


def panel_test(labels_1ppmm: np.ndarray, palette_L: np.ndarray,
               sizes_mm=(150, 250, 400), n: int = 400, seed: int = 1) -> dict:
    """How does a small accent panel cut at a random position look? For square windows,
    fraction that are a 'flat blob' (one colour > 70 %) and median L* range of colours
    present at >= 5 %. Periodic sampling (wrap)."""
    rng = np.random.default_rng(seed)
    H, W = labels_1ppmm.shape
    big = np.tile(labels_1ppmm, (2, 2))
    res = {}
    nc = len(palette_L)
    for s in sizes_mm:
        s = int(min(s, H, W))
        blobs, ranges, ncol = 0, [], []
        for _ in range(n):
            y, x = rng.integers(0, H), rng.integers(0, W)
            win = big[y:y + s, x:x + s]
            cov = np.bincount(win.ravel(), minlength=nc) / win.size
            if cov.max() > 0.70:
                blobs += 1
            present = palette_L[cov >= 0.05]
            ranges.append(float(present.max() - present.min()))
            ncol.append(int((cov >= 0.05).sum()))
        res[f"{s}mm"] = {"flat_blob_fraction": round(blobs / n, 3),
                         "median_L_range": round(float(np.median(ranges)), 1),
                         "median_colours_ge5pct": float(np.median(ncol))}
    return res


# ----------------------------------------------------------------------------- previews
def preview_repeat(spec: dict, name: str | None = None) -> tuple[Path, np.ndarray]:
    rgb = render_rgb(spec, 72)
    p = save_png(rgb, PREVIEW_DIR / f"{name or spec['name']}_repeat_72dpi.png", dpi=72,
                 limit=MAX_PREVIEW_BYTES)
    return p, rgb


def preview_tile2x2(spec: dict, rgb72: np.ndarray) -> Path:
    t = np.tile(rgb72, (2, 2, 1))
    h, w = t.shape[:2]
    s = min(1.0, 1600 / max(h, w))
    t = _resize(t, int(w * s), int(h * s), nearest=True)
    im = Image.fromarray(t)
    d = ImageDraw.Draw(im)
    # faint tick marks at the repeat boundaries (outside the image centre) to show where seams are
    for k in (im.width // 2,):
        d.line([(k, 0), (k, 12)], fill=(255, 0, 0), width=2)
        d.line([(k, im.height - 12), (k, im.height)], fill=(255, 0, 0), width=2)
    for k in (im.height // 2,):
        d.line([(0, k), (12, k)], fill=(255, 0, 0), width=2)
        d.line([(im.width - 12, k), (im.width, k)], fill=(255, 0, 0), width=2)
    return save_png(im, PREVIEW_DIR / f"{spec['name']}_tile2x2.png", limit=MAX_PREVIEW_BYTES)


def preview_dichromat(spec: dict, rgb72: np.ndarray) -> Path:
    s = 640
    a = _resize(rgb72, s, s, nearest=True)
    panels = [("human (trichromat)", a), ("ungulate sim (protan-type, Vienot 1999)",
                                          color.simulate_dichromat(a, "ungulate")),
              ("ungulate luminance only", np.repeat(np.round(color.linear_to_srgb(
                  color.image_luminance(color.simulate_dichromat(a, "ungulate"))) * 255)
                  .astype(np.uint8)[..., None], 3, -1))]
    pad, top = 16, 40
    im = Image.new("RGB", (len(panels) * (s + pad) + pad, s + top + pad), (245, 244, 240))
    for k, (t, arr) in enumerate(panels):
        x = pad + k * (s + pad)
        im.paste(Image.fromarray(arr), (x, top))
        _label(im, (x, 10), t, 18)
    return save_png(im, PREVIEW_DIR / f"{spec['name']}_dichromat.png", limit=MAX_PREVIEW_BYTES)


def _distance_rows(img_rgb: np.ndarray, ppmm: float, wrap: bool, s: int):
    rows = []
    for title, cpd, kind in (("human eye (30 cpd)", vision.HUMAN_CPD, None),
                             ("ungulate (6 cpd, dichromat)", vision.UNGULATE_CPD, "ungulate")):
        src = color.simulate_dichromat(img_rgb, kind) if kind else img_rgb
        cells = [("0 m (full detail)", _resize(src, s, s))]
        for d in vision.STANDARD_DISTANCES_M:
            disp, info = vision.simulate_distance(src, ppmm, d, cpd, wrap=wrap, display_shape=(s, s))
            cells.append((f"{d} m  RMS C={info['rms_contrast']:.2f}", disp))
        rows.append((title, cells))
    return rows


def preview_distance(spec: dict, extra: list[tuple[str, np.ndarray, float]] | None = None) -> Path:
    """Distance series of a 2x2 tile (one 'person-sized' area for 760 mm repeats).
    ``extra``: optional (title, rgb, px_per_mm) images (non-periodic, e.g. a garment mock)."""
    hexes = engine.palette_hexes(spec)
    model = engine.build_fields(spec, spec.get("seed", 0))
    lab = engine.render_labels(model, 25.4)
    reps = max(2, int(math.ceil(1500 / spec["repeat_mm"]["width"])))
    tile = engine.labels_to_rgb(np.tile(lab, (reps, reps)), hexes)
    s, pad, top, left = 280, 10, 34, 230
    rows = _distance_rows(tile, 1.0, True, s)
    titles = [f"{reps}x{reps} repeats ({reps * spec['repeat_mm']['width'] / 1000:.2f} m)"]
    for t, img, ppmm in extra or []:
        r = _distance_rows(img, ppmm, False, s)
        rows += [(f"{t}\n{rt}", c) for rt, c in r]
    ncol = len(rows[0][1])
    im = Image.new("RGB", (left + ncol * (s + pad), top + len(rows) * (s + top) + pad), (245, 244, 240))
    _label(im, (10, 6), f"{spec.get('display_name', spec['name'])} — distance series; {titles[0]}. "
           "Blur at acuity limit + Nyquist resample; no haze modelled.", 16, bold=True)
    for r, (rt, cells) in enumerate(rows):
        y = top + r * (s + top) + 24
        _label(im, (10, y + s // 2 - 20), rt, 15)
        for c, (ct, arr) in enumerate(cells):
            x = left + c * (s + pad)
            im.paste(Image.fromarray(arr), (x, y))
            _label(im, (x, y - 20), ct, 14)
    return save_png(im, PREVIEW_DIR / f"{spec['name']}_distance.png", limit=MAX_PREVIEW_BYTES)


def swatch_card(pattern_names: list[str], path: Path | None = None,
                section: str | None = "alternate") -> Path:
    """Cirquefall (alternate) colour card. The Owner Base card is owner_export.swatch_card."""
    cw = colorway_section(load_colorways(), section)
    rows: list[tuple[str, list[dict]]] = []
    seen = set()
    for n in pattern_names:
        sp = engine.load_pattern(n)
        key = tuple(c["hex"] for c in sp["palette"])
        if key in seen:
            continue
        seen.add(key)
        rows.append((f"Camo inks — {sp.get('display_name', n)}", sp["palette"]))
    rows.append((f"Solid colorway line (colorways.yaml{' ' + section if section else ''})", cw["solids"]))
    sw, gap, rowh, left = 200, 14, 300, 20
    ncol = max(len(r[1]) for r in rows)
    W = left * 2 + ncol * (sw + gap)
    im = Image.new("RGB", (W, 60 + len(rows) * rowh), (248, 247, 243))
    _label(im, (left, 14), "Hunting-Appeal colour card — top chip: human; small chip: ungulate "
           "(dichromat) simulation. Targets only: approve on lab dips.", 18, bold=True)
    for r, (title, cols) in enumerate(rows):
        y0 = 60 + r * rowh
        _label(im, (left, y0), title, 18, bold=True)
        for k, c in enumerate(cols):
            x = left + k * (sw + gap)
            rgb = color.hex_to_rgb8(c["hex"])
            ImageDraw.Draw(im).rectangle([x, y0 + 28, x + sw, y0 + 148], fill=rgb)
            sim = color.simulate_dichromat(np.array([[rgb]], np.uint8))[0, 0]
            ImageDraw.Draw(im).rectangle([x + sw - 60, y0 + 108, x + sw, y0 + 148],
                                         fill=tuple(int(v) for v in sim), outline=(255, 255, 255))
            lab = color.hex_to_lab(c["hex"])
            _label(im, (x, y0 + 154), c["name"], 16, bold=True)
            _label(im, (x, y0 + 176), f"{c.get('code', '')}  {c['hex']}", 14)
            _label(im, (x, y0 + 196), f"sRGB {rgb[0]},{rgb[1]},{rgb[2]}", 14)
            _label(im, (x, y0 + 216), f"L*a*b* {lab[0]:.1f} {lab[1]:.1f} {lab[2]:.1f}", 14)
            if "qc_tolerance" in c:
                _label(im, (x, y0 + 236), f"QC dE00 <= {c['qc_tolerance']['dE00']}  no OBA", 14)
    return save_png(im, path or PREVIEW_DIR / "palette_swatch_card.png", limit=MAX_PREVIEW_BYTES)


# ----------------------------------------------------------------------------- garment mocks
# Silhouettes are flat front views in mm (x right, y down, origin centre-top of body).
# ASSUMPTION: approximate men's L proportions for visual mocks only — the pattern-maker owns
# real garment geometry. Accent shards are drawn large and clipped to the garment parts.
def _mirror(poly):
    return [(-x, y) for x, y in poly]


JACKET = {
    "parts": {
        "body": [(-95, 0), (95, 0), (235, 48), (292, 262), (282, 770), (-282, 770), (-292, 262), (-235, 48)],
        "collar": [(-95, 0), (-108, -85), (108, -85), (95, 0)],
        "sleeve_r": [(235, 48), (575, 575), (492, 632), (292, 262)],
    },
    "accents": {   # shard / chevron accent panels; seams double as articulation lines
        "yoke": [(-420, -120), (420, -120), (420, 150), (300, 175), (40, 120), (-60, 205), (-420, 140)],
        "forearm_r": [(430, 330), (700, 520), (700, 800), (360, 650), (440, 545), (395, 470)],
        "side_r": [(300, 250), (240, 330), (232, 610), (300, 690)],
    },
    "seams": [  # extra functional seam lines (dart / articulation), drawn in trim colour
        [(-282, 560), (-120, 600), (-20, 770)],
    ],
}
JACKET["parts"]["sleeve_l"] = _mirror(JACKET["parts"]["sleeve_r"])
JACKET["accents"]["forearm_l"] = _mirror(JACKET["accents"]["forearm_r"])
JACKET["accents"]["side_l"] = _mirror(JACKET["accents"]["side_r"])

PACK = {  # ~5200 cu in pack, front view
    "parts": {
        "body": [(-170, 40), (170, 40), (178, 720), (150, 770), (-150, 770), (-178, 720)],
        "lid": [(-185, -40), (185, -40), (192, 150), (60, 178), (-192, 150)],
        "pocket_r": [(170, 330), (228, 360), (236, 700), (178, 720)],
        "wing_r": [(178, 600), (340, 640), (352, 700), (300, 740), (178, 735)],
        "base": [(-178, 720), (178, 720), (150, 770), (-150, 770)],
    },
    "accents": {
        "lid": [(-200, -60), (200, -60), (200, 200), (-200, 200)],
        "pocket_r": [(160, 300), (260, 300), (260, 760), (160, 760)],
        "wing_r": [(170, 580), (380, 580), (380, 760), (170, 760)],
        "front_shard": [(-170, 330), (-20, 260), (60, 300), (-170, 520)],
    },
    "trim": ["base"],
    "seams": [[(-170, 300), (170, 250)], [(-170, 520), (170, 470)]],  # compression straps
}
PACK["parts"]["pocket_l"] = _mirror(PACK["parts"]["pocket_r"])
PACK["parts"]["wing_l"] = _mirror(PACK["parts"]["wing_r"])
PACK["accents"]["pocket_l"] = _mirror(PACK["accents"]["pocket_r"])
PACK["accents"]["wing_l"] = _mirror(PACK["accents"]["wing_r"])


def _poly_mask(poly, ppmm, ox, oy, shape):
    m = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(m).polygon([((x + ox) * ppmm, (y + oy) * ppmm) for x, y in poly], fill=255)
    return np.asarray(m) > 0


def _edges(mask):
    from scipy import ndimage
    return mask & ~ndimage.binary_erosion(mask, iterations=2)


def render_mock(geom: dict, body_hex: str, trim_hex: str, pattern_rgb: np.ndarray | None,
                ppmm: float, full_fill: bool = False, bg=(246, 245, 241),
                extent=(-600, -110, 600, 830)) -> np.ndarray:
    """Rasterise a silhouette: solid body, camo accent panels (pattern tiled at true scale,
    ``pattern_rgb`` rendered at ``ppmm``), seam/trim lines."""
    x0, y0, x1, y1 = extent
    H, W = int((y1 - y0) * ppmm), int((x1 - x0) * ppmm)
    ox, oy = -x0, -y0
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = bg
    garment = np.zeros((H, W), bool)
    for poly in geom["parts"].values():
        garment |= _poly_mask(poly, ppmm, ox, oy, (H, W))
    camo = None
    if pattern_rgb is not None:
        ph, pw = pattern_rgb.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]
        camo = pattern_rgb[yy % ph, xx % pw]
    img[garment] = color.hex_to_rgb8(body_hex)
    if full_fill and camo is not None:
        img[garment] = camo[garment]
    elif camo is not None:
        for poly in geom["accents"].values():
            m = _poly_mask(poly, ppmm, ox, oy, (H, W)) & garment
            img[m] = camo[m]
            img[_edges(m)] = color.hex_to_rgb8(trim_hex)
    trim = color.hex_to_rgb8(trim_hex)
    for k in geom.get("trim", []):
        m = _poly_mask(geom["parts"][k], ppmm, ox, oy, (H, W))
        img[m] = trim
    for poly in geom["parts"].values():
        img[_edges(_poly_mask(poly, ppmm, ox, oy, (H, W)))] = trim
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    for line in geom.get("seams", []):
        d.line([((x + ox) * ppmm, (y + oy) * ppmm) for x, y in line], fill=trim,
               width=max(2, int(round(3 * ppmm))))
    return np.asarray(im)


def preview_accent_mocks(ppmm: float = 0.8, section: str | None = "alternate") -> Path:
    """Jacket + pack front, solid body + camo accents, one row per accent pairing
    (Cirquefall alternate system; Owner Base mocks are in owner_export)."""
    cw = load_colorways()
    pairs = colorway_section(cw, section)["accent_pairings"]
    cache: dict[str, np.ndarray] = {}
    tiles = []
    for p in pairs:
        if p["accent_pattern"] not in cache:
            cache[p["accent_pattern"]] = render_rgb(engine.load_pattern(p["accent_pattern"]), ppmm * 25.4)
        pat = cache[p["accent_pattern"]]
        body, trim = _solid_hex(cw, p["body"]), _solid_hex(cw, p["trim"])
        j = render_mock(JACKET, body, trim, pat, ppmm)
        k = render_mock(PACK, body, trim, pat, ppmm, extent=(-400, -110, 400, 830))
        tiles.append((p, j, k))
    jh, jw = tiles[0][1].shape[:2]
    kh, kw = tiles[0][2].shape[:2]
    top, gap = 34, 20
    im = Image.new("RGB", (jw + kw + 3 * gap, len(tiles) * (jh + top) + 50), (246, 245, 241))
    _label(im, (gap, 12), "Accent system mocks — solid body + Cirquefall Shard/Firn Shard accent "
           "panels at true scale (yoke, forearms, side panels; pack lid, side pockets, hipbelt wings)", 17, bold=True)
    for r, (p, j, k) in enumerate(tiles):
        y = 50 + r * (jh + top)
        _label(im, (gap, y), f"{p['display_name']}: body {p['body']}, accent {p['accent_pattern']}, "
               f"trim {p['trim']}, thread {p['thread']}", 16)
        im.paste(Image.fromarray(j), (gap, y + top - 8))
        im.paste(Image.fromarray(k), (jw + 2 * gap, y + top - 8))
    return save_png(im, PREVIEW_DIR / "accent_mocks_jacket_pack.png", limit=MAX_PREVIEW_BYTES)


def preview_fullfill_mock(names: list[str], ppmm: float = 0.6) -> Path:
    cw = load_colorways()
    imgs = []
    for n in names:
        sp = engine.load_pattern(n)
        pat = render_rgb(sp, ppmm * 25.4)
        imgs.append((sp.get("display_name", n), render_mock(JACKET, "#000000", _solid_hex(cw, "basalt_ink"),
                                                             pat, ppmm, full_fill=True)))
    h, w = imgs[0][1].shape[:2]
    im = Image.new("RGB", (len(imgs) * (w + 20) + 20, h + 50), (246, 245, 241))
    for k, (t, a) in enumerate(imgs):
        im.paste(Image.fromarray(a), (20 + k * (w + 20), 40))
        _label(im, (20 + k * (w + 20), 12), f"{t} — full-fill jacket mock (true scale)", 16, bold=True)
    return save_png(im, PREVIEW_DIR / "fullfill_jacket_mock.png", limit=MAX_PREVIEW_BYTES)


def accent_mock_rgb(pairing_id: str, ppmm: float = 1.0, bg_hex: str | None = None,
                    section: str | None = "alternate") -> np.ndarray:
    cw = load_colorways()
    p = next(x for x in colorway_section(cw, section)["accent_pairings"] if x["id"] == pairing_id)
    pat = render_rgb(engine.load_pattern(p["accent_pattern"]), ppmm * 25.4)
    bg = color.hex_to_rgb8(bg_hex) if bg_hex else (246, 245, 241)
    return render_mock(JACKET, _solid_hex(cw, p["body"]), _solid_hex(cw, p["trim"]), pat, ppmm,
                       bg=bg, extent=(-700, -260, 700, 1140))


# ----------------------------------------------------------------------------- bundles
def render_all(name: str, dpi: float = 300, out: Path | None = None, tiff: bool = True,
               svg: bool = True) -> dict:
    spec = engine.load_pattern(name)
    res = {"print": export_repeat(spec, dpi, out, tiff=tiff)}
    p72, rgb72 = preview_repeat(spec)
    res["preview_repeat"] = p72
    res["tile2x2"] = preview_tile2x2(spec, rgb72)
    res["dichromat"] = preview_dichromat(spec, rgb72)
    res["distance"] = preview_distance(spec)
    if svg:
        res["svg"] = export_separations_svg(spec, out)
    metrics = analyze(spec)
    mp = PREVIEW_DIR / f"{spec['name']}_metrics.json"
    mp.write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    res["metrics"] = mp
    return res
