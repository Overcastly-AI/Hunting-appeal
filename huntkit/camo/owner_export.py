"""Previews, metrics and print files for the Owner Base camo (primary pattern).

Every image made from the procedural stand-in carries "PROXY" in its title
(``OwnerBase.title_tag``). Previews go to designs/apparel/camo/previews/owner_base_*.png
(<= 1.5 MB); phone copies go to outputs/screens/<date>_ownerbase_<n>.png.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

from . import color, export, owner_base as ob, vision
from .export import (JACKET, PACK, MAX_PREVIEW_BYTES, PREVIEW_DIR, _label, _resize,
                     render_mock, save_png)

SCREENS_DIR = export.ROOT / "outputs" / "screens"
BG = (246, 245, 241)


def load_spec() -> dict:
    with open(ob.SPEC_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def repeat_mm(scale: str = "full") -> float:
    return float(load_spec()["repeat_mm"][scale]["width"])


def pattern_rgb(base: ob.OwnerBase, scale: str, ppmm: float) -> np.ndarray:
    return base.rgb(max(8, int(round(repeat_mm(scale) * ppmm))))


# ----------------------------------------------------------------------------- previews
def preview_tile(base: ob.OwnerBase) -> Path:
    """One repeat + 2x2 tiling with seam ticks."""
    rgb = base.rgb(700)
    t = np.tile(rgb, (2, 2, 1))
    t = _resize(t, 1000, 1000, nearest=True)
    pad, top = 16, 70
    im = Image.new("RGB", (700 + 1000 + 3 * pad, 1000 + top + pad), BG)
    im.paste(Image.fromarray(rgb), (pad, top))
    im.paste(Image.fromarray(t), (700 + 2 * pad, top))
    d = ImageDraw.Draw(im)
    x0 = 700 + 2 * pad
    for k in (500,):
        d.line([(x0 + k, top - 12), (x0 + k, top)], fill=(220, 0, 0), width=3)
        d.line([(x0 - 12, top + k), (x0, top + k)], fill=(220, 0, 0), width=3)
    sr = base.seam_report or base.check_seamless()
    _label(im, (pad, 8), f"{base.title_tag}Owner Base — one 1000-unit repeat (left) and 2x2 tiling "
           "(right, red ticks = repeat joins)", 20, bold=True)
    _label(im, (pad, 38), f"source: {base.source} ({base.backend}); edge-wrap dE00 seam x "
           f"{sr['x']['seam_dE00']:.2f} / y {sr['y']['seam_dE00']:.2f} (z vs 7.8-unit grid lines "
           f"{sr['x']['z']:+.1f} / {sr['y']['z']:+.1f}; limit {sr['z_max']}) -> "
           f"{'SEAMLESS' if sr['seamless'] else 'NOT seamless: offset-blend fix applied'}", 16)
    return save_png(im, PREVIEW_DIR / "owner_base_tile2x2.png", limit=MAX_PREVIEW_BYTES)


def preview_swatch_card(base: ob.OwnerBase, metrics: dict) -> Path:
    cw = export.load_colorways()
    inks = base.palette
    solids = cw["solids"]
    sw, gap, left = 220, 16, 24
    W = left * 2 + 5 * (sw + gap)
    H = 1080
    im = Image.new("RGB", (W, H), (248, 247, 243))
    d = ImageDraw.Draw(im)
    _label(im, (left, 14), f"{base.title_tag}Owner Base colour card — big chip human, small chip "
           "deer (dichromat) sim. Targets only; no OBA.", 18, bold=True)

    def chip_row(y0, title, cols, cov=None):
        _label(im, (left, y0), title, 18, bold=True)
        for k, c in enumerate(cols):
            x = left + k * (sw + gap)
            rgb = color.hex_to_rgb8(c["hex"])
            d.rectangle([x, y0 + 28, x + sw, y0 + 158], fill=rgb)
            sim = color.simulate_dichromat(np.array([[rgb]], np.uint8))[0, 0]
            d.rectangle([x + sw - 64, y0 + 116, x + sw, y0 + 158], fill=tuple(int(v) for v in sim),
                        outline=(255, 255, 255))
            lab = color.hex_to_lab(c["hex"])
            labu = color.srgb_to_lab(color.simulate_dichromat(color.hex_to_srgb(c["hex"])))
            _label(im, (x, y0 + 164), c["name"], 17, bold=True)
            _label(im, (x, y0 + 188), f"{c.get('code', '')}  {c['hex']}", 14)
            _label(im, (x, y0 + 208), f"L*a*b* {lab[0]:.1f} {lab[1]:.1f} {lab[2]:.1f}", 14)
            _label(im, (x, y0 + 228), f"deer-sim L* {labu[0]:.1f}", 14)
            extra = (f"coverage {cov[c['key']] * 100:.1f} %" + (" (PROXY)" if base.is_proxy else "")
                     if cov else f"QC dE00 <= {c['qc_tolerance']['dE00']}  no OBA")
            _label(im, (x, y0 + 248), extra, 14)

    chip_row(56, "Owner inks (from the owner's SVG)", inks, metrics["coverage"])
    chip_row(356, "Solid colorway line (colorways.yaml, primary)", solids)
    # pair table
    y = 660
    _label(im, (left, y), "Ink pairs — dE00 human / dE00 deer-sim / Michelson luminance contrast (deer-sim)",
           16, bold=True)
    _label(im, (left, y + 22), "flags: dE00 deer < 5 = colours merge for deer; Michelson < 0.2 = weak tonal step", 14)
    y += 18
    names = {c["key"]: c["name"] for c in inks}
    for k, r in enumerate(sorted(metrics["dichromat_pairs"], key=lambda r: r["de00_dichromat"])):
        a, b = r["pair"].split("/")
        flag = ("MERGES" if r["de00_dichromat"] < 5 else
                "weakest — tonal only" if r["michelson_dichromat"] < 0.2 else "ok")
        yy = y + 34 + k * 30
        ca, cb = color.hex_to_rgb8(next(c["hex"] for c in inks if c["key"] == a)), \
            color.hex_to_rgb8(next(c["hex"] for c in inks if c["key"] == b))
        d.rectangle([left, yy, left + 24, yy + 22], fill=ca)
        d.rectangle([left + 26, yy, left + 50, yy + 22], fill=cb)
        _label(im, (left + 64, yy), f"{names[a]} / {names[b]}", 16)
        _label(im, (left + 420, yy), f"{r['de00_human']:5.1f}  /  {r['de00_dichromat']:5.1f}  /  "
               f"{r['michelson_dichromat']:.2f}    {flag}", 16)
    Ls = metrics["palette_L"]
    _label(im, (left, y + 34 + 6 * 30 + 16),
           f"L* ladder: {' | '.join(f'{names[k]} {v:.1f}' for k, v in sorted(Ls.items(), key=lambda kv: kv[1]))}"
           , 16)
    _label(im, (left, y + 34 + 6 * 30 + 72), "-> 34 L* gap between dark and olive (no mid-dark ink); "
           "the Elk Wallow solid (L* 38) bridges it in the garment system.", 16)
    lb = metrics["luminance_bands"]
    _label(im, (left, y + 34 + 6 * 30 + 44 + 56),
           f"Luminance bands{' (PROXY coverage)' if base.is_proxy else ''}: dark {lb['dark_L<40'] * 100:.0f} %, "
           f"mid {lb['mid_40-60'] * 100:.0f} %, light {lb['light_L>=60'] * 100:.0f} %; "
           f"weighted mean L* {metrics['coverage_weighted_mean_L']}; mean {metrics['mean_colour_hex']}", 16)
    return save_png(im, PREVIEW_DIR / "owner_base_swatch_card.png", limit=MAX_PREVIEW_BYTES)


def preview_dichromat(base: ob.OwnerBase) -> Path:
    s = 640
    a = base.rgb(s)
    sim = color.simulate_dichromat(a, "ungulate")
    lum = np.repeat(np.round(color.linear_to_srgb(color.image_luminance(sim)) * 255)
                    .astype(np.uint8)[..., None], 3, -1)
    panels = [("human (trichromat)", a), ("ungulate sim (protan-type, Vienot 1999)", sim),
              ("ungulate luminance only", lum)]
    pad, top = 16, 70
    im = Image.new("RGB", (len(panels) * (s + pad) + pad, s + top + pad), BG)
    _label(im, (pad, 8), f"{base.title_tag}Owner Base — dichromat (deer/elk) view, one repeat", 20, bold=True)
    for k, (t, arr) in enumerate(panels):
        x = pad + k * (s + pad)
        im.paste(Image.fromarray(arr), (x, top))
        _label(im, (x, top - 26), t, 18)
    return save_png(im, PREVIEW_DIR / "owner_base_dichromat.png", limit=MAX_PREVIEW_BYTES)


def mock_rgb(base: ob.OwnerBase, pairing: dict, cw: dict, ppmm: float, bg=BG, extent=None,
             geom=JACKET) -> np.ndarray:
    pat = pattern_rgb(base, pairing.get("accent_scale", "accent"), ppmm)
    kw = {"extent": extent} if extent else {}
    return render_mock(geom, export._solid_hex(cw, pairing["body"]),
                       export._solid_hex(cw, pairing["trim"]), pat, ppmm, bg=bg, **kw)


def preview_distance(base: ob.OwnerBase, cw: dict) -> Path:
    """Full-scale 2x2 repeats (1.52 m) + a Sidehill jacket mock on sagebrush, human vs deer."""
    full = repeat_mm("full")
    lab = base.labels(int(round(full)))
    tile = ob.labels_to_rgb(np.tile(lab, (2, 2)), base.hexes)
    s, pad, top, left = 260, 10, 34, 250
    rows = [(f"full scale {full:.0f} mm, 2x2\n{rt}", c) for rt, c in export._distance_rows(tile, 1.0, True, s)]
    p = next(x for x in cw["accent_pairings"] if x["id"] == "sidehill")
    mock = mock_rgb(base, p, cw, 1.0, bg=color.hex_to_rgb8(color.BACKGROUNDS["sagebrush"]),
                    extent=(-700, -260, 700, 1140))
    rows += [(f"Sidehill jacket, accent\nscale, on sagebrush\n{rt}", c)
             for rt, c in export._distance_rows(mock, 1.0, False, s)]
    ncol = len(rows[0][1])
    im = Image.new("RGB", (left + ncol * (s + pad), top + 20 + len(rows) * (s + top) + pad), BG)
    _label(im, (10, 6), f"{base.title_tag}Owner Base — distance series. Blur at acuity limit + Nyquist "
           "resample (vision.py); deer 6 cpd ASSUMPTION; no haze.", 17, bold=True)
    for r, (rt, cells) in enumerate(rows):
        y = top + 20 + r * (s + top) + 24
        _label(im, (10, y + s // 2 - 30), rt, 14)
        for c, (ct, arr) in enumerate(cells):
            x = left + c * (s + pad)
            im.paste(Image.fromarray(arr), (x, y))
            _label(im, (x, y - 20), ct, 14)
    return save_png(im, PREVIEW_DIR / "owner_base_distance.png", limit=MAX_PREVIEW_BYTES)


def preview_accent_mocks(base: ob.OwnerBase, cw: dict, ids=("sidehill", "benchland", "wallow"),
                         ppmm: float = 0.8) -> Path:
    pairs = [next(x for x in cw["accent_pairings"] if x["id"] == i) for i in ids]
    tiles = []
    for p in pairs:
        j = mock_rgb(base, p, cw, ppmm)
        k = mock_rgb(base, p, cw, ppmm, extent=(-400, -110, 400, 830), geom=PACK)
        tiles.append((p, j, k))
    jh, jw = tiles[0][1].shape[:2]
    kh, kw = tiles[0][2].shape[:2]
    top, gap = 34, 20
    im = Image.new("RGB", (jw + kw + 3 * gap, len(tiles) * (jh + top) + 60), BG)
    _label(im, (gap, 12), f"{base.title_tag}Owner Base accent mocks — solid body + Owner Base accent panels "
           f"({repeat_mm('accent'):.0f} mm repeat, true scale): yoke, forearms, sides; pack lid, pockets, "
           "hipbelt wings", 17, bold=True)
    for r, (p, j, k) in enumerate(tiles):
        y = 60 + r * (jh + top)
        _label(im, (gap, y - 8), f"{p['display_name']}: body {p['body']}, accent owner_base "
               f"({p.get('accent_scale', 'accent')}), trim {p['trim']}, thread {p['thread']}", 16)
        im.paste(Image.fromarray(j), (gap, y + top - 16))
        im.paste(Image.fromarray(k), (jw + 2 * gap, y + top - 16))
    return save_png(im, PREVIEW_DIR / "owner_base_accent_mocks.png", limit=MAX_PREVIEW_BYTES)


def phone_copy(src: Path, n: int, date: str = "20261101", width: int = 1080) -> Path:
    im = Image.open(src).convert("RGB")
    if im.width > width:
        im = im.resize((width, int(im.height * width / im.width)), Image.Resampling.LANCZOS)
    return save_png(im, SCREENS_DIR / f"{date}_ownerbase_{n}.png", limit=MAX_PREVIEW_BYTES)


# ----------------------------------------------------------------------------- print files
def export_print(base: ob.OwnerBase, scale: str = "full", dpi: float = 300, out: Path | None = None) -> dict:
    out = Path(out or export.OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    lab = ob.render_labels(base, repeat_mm(scale), dpi)
    rgb = ob.labels_to_rgb(lab, base.hexes)
    tag = "_PROXY" if base.is_proxy else ""
    p = out / f"owner_base{tag}_{scale}_{int(repeat_mm(scale))}mm_{int(dpi)}dpi"
    im = Image.fromarray(rgb)
    im.save(p.with_suffix(".tif"), compression="tiff_lzw", dpi=(dpi, dpi))
    return {"tif": p.with_suffix(".tif"), "shape": rgb.shape}


# ----------------------------------------------------------------------------- bundle
def run_all(print_dpi: float | None = 300, screens: bool = True) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ob.ProxyWarning)
        base = ob.load_owner_base()
    cw = export.load_colorways()
    res: dict = {"source": base.source, "is_proxy": base.is_proxy}
    res["seam"] = base.check_seamless()
    m_full = ob.analyze_owner(base, repeat_mm("full"))
    m_acc = ob.analyze_owner(base, repeat_mm("accent"))
    study = ob.repeat_scale_study(base)
    m_full["seam_check"] = res["seam"]
    (PREVIEW_DIR / "owner_base_metrics.json").write_text(json.dumps(
        {"full": m_full, "accent": m_acc}, indent=1), encoding="utf-8")
    (PREVIEW_DIR / "owner_base_scale_study.json").write_text(json.dumps(
        {"is_proxy": base.is_proxy, "candidates": study}, indent=1), encoding="utf-8")
    pngs = [preview_swatch_card(base, m_full), preview_distance(base, cw), preview_dichromat(base),
            preview_accent_mocks(base, cw), preview_tile(base)]
    res["previews"] = pngs
    if screens:
        res["screens"] = [phone_copy(p, i + 1) for i, p in enumerate(pngs)]
    if print_dpi:
        res["print"] = [export_print(base, "full", print_dpi), export_print(base, "accent", print_dpi)]
    res["metrics"] = {"full": m_full, "accent": m_acc}
    return res
