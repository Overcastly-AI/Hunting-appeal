"""Originality screening for camo artwork: structure descriptors and image-to-image similarity.

What this can and cannot do (also in docs/research/camo_originality_print_2026.md):

* ``image_similarity(a, b)`` compares two **images**. Its copy indicator is the peak normalised
  cross-correlation of luminance over every cyclic shift, the 8 flips/rotations and +-25 % scale
  (``ncc_max``). A traced, shifted, rescaled or recoloured copy scores high; an independent
  pattern of the *same style* scores low. Calibrated in ``calibrate()`` and the tests: the owner
  file against itself shifted + rescaled 10 % + 15 % pixel noise + recoloured (0.96), against a
  procedural pattern built to match its statistics, the retired proxy (0.27), and against
  Cirquefall Shard (0.16). Thresholds: >= 0.60 probable copy, < 0.35 no resemblance found.
* ``describe(img)`` gives class-level structure numbers (ink count, L* ladder, pixel/axis
  alignment, vertical streaking, blob scales). ``compare_to_references`` sets them against the
  *published descriptions* of commercial patterns (``designs/apparel/camo/originality_refs.yaml``,
  every line cited). That only shows which design *families* overlap. Concepts such as
  "macro blobs + pixel micro" are shared by many patterns and are not what copyright protects;
  the specific arrangement is.
* Nothing here proves originality. The repo holds no commercial pattern images (benchmark only,
  never copied), so no image-to-image comparison against them has been run. To run one, photograph
  a legally owned swatch flat with a ruler in frame and call
  ``python -m huntkit.camo.originality compare <ours.png> <swatch.jpg> --ppmm-a .. --ppmm-b ..``.
  The provenance of owner-supplied artwork rests on the owner's own statement.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage

from . import color

REFS_PATH = Path(__file__).resolve().parents[2] / "designs" / "apparel" / "camo" / "originality_refs.yaml"

# Calibrated thresholds (calibrate(); tests/test_camo_originality.py keeps them honest)
NCC_COPY = 0.60        # >= : treat as a probable copy / derivative; stop and get IP advice
NCC_CLEAR = 0.35       # <  : no image-level resemblance found at any shift/flip/scale tried


# ============================================================================ helpers
def _as_rgb(img) -> np.ndarray:
    if isinstance(img, Image.Image):
        img = np.asarray(img.convert("RGB"))
    a = np.asarray(img)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return a[..., :3].astype(np.uint8)


def resample(rgb: np.ndarray, ppmm: float, target_ppmm: float) -> np.ndarray:
    """Area-resample an RGB image to ``target_ppmm`` px/mm."""
    h, w = rgb.shape[:2]
    s = target_ppmm / ppmm
    nw, nh = max(8, int(round(w * s))), max(8, int(round(h * s)))
    return np.asarray(Image.fromarray(rgb).resize((nw, nh), Image.Resampling.BOX if s < 1 else
                                                   Image.Resampling.NEAREST))


def lightness(rgb: np.ndarray) -> np.ndarray:
    return color.srgb_to_lab(rgb.astype(np.float64) / 255.0)[..., 0]


def inks(rgb: np.ndarray, min_share: float = 0.005, levels: int = 16) -> list[tuple[str, float]]:
    """Distinct colours (quantised to ``levels`` per channel) covering >= ``min_share``."""
    q = (rgb.astype(np.int32) * levels // 256)
    code = (q[..., 0] * levels + q[..., 1]) * levels + q[..., 2]
    vals, cnt = np.unique(code.ravel(), return_counts=True)
    share = cnt / cnt.sum()
    out = []
    for v, s in sorted(zip(vals, share), key=lambda t: -t[1]):
        if s < min_share:
            continue
        m = code == v
        mean = rgb[m].mean(0)
        out.append((color.rgb8_to_hex(np.round(mean).astype(int)), float(s)))
    return out


# ============================================================================ descriptors
def axis_alignment(L: np.ndarray, sigma_px: float = 1.0, band_deg: float = 11.25) -> float:
    """Share of edge energy whose gradient is within +-band of 0 or 90 deg. Uniform = 0.25 for the
    default band; square-pixel ('digital') art scores well above that."""
    gx = ndimage.gaussian_filter(L, sigma_px, order=(0, 1), mode="wrap")
    gy = ndimage.gaussian_filter(L, sigma_px, order=(1, 0), mode="wrap")
    mag = np.hypot(gx, gy)
    ang = np.degrees(np.arctan2(gy, gx)) % 90.0          # fold 0/90/180/270 together
    near = (ang <= band_deg) | (ang >= 90.0 - band_deg)
    tot = mag.sum()
    return float(mag[near].sum() / tot) if tot > 0 else 0.0


def orientation_hist(L: np.ndarray, sigma_px: float = 2.0, bins: int = 36) -> np.ndarray:
    gx = ndimage.gaussian_filter(L, sigma_px, order=(0, 1), mode="wrap")
    gy = ndimage.gaussian_filter(L, sigma_px, order=(1, 0), mode="wrap")
    ang = np.degrees(np.arctan2(gy, gx)) % 180.0
    h, _ = np.histogram(ang, bins=bins, range=(0, 180), weights=np.hypot(gx, gy))
    return h / max(h.sum(), 1e-12)


def streak(L: np.ndarray, ppmm: float, scale_mm: float = 10.0) -> dict:
    """Structure-tensor coherence of the low-passed image and the dominant *feature* direction
    (deg, 90 = vertical streaks)."""
    Ls = ndimage.gaussian_filter(L, scale_mm * ppmm / 4, mode="wrap")
    gx = ndimage.sobel(Ls, 1, mode="wrap")
    gy = ndimage.sobel(Ls, 0, mode="wrap")
    jxx, jyy, jxy = (gx * gx).mean(), (gy * gy).mean(), (gx * gy).mean()
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = math.sqrt(max(tr * tr / 4 - det, 0.0))
    l1, l2 = tr / 2 + disc, tr / 2 - disc
    coh = (l1 - l2) / (l1 + l2) if (l1 + l2) > 0 else 0.0
    grad_dir = 0.5 * math.degrees(math.atan2(2 * jxy, jxx - jyy))
    feat = (grad_dir + 90.0) % 180.0
    return {"coherence": float(coh), "feature_deg": float(feat)}


def blob_scales(L: np.ndarray, ppmm: float, dark_lt: float = 35.0, micro_mm: float = 20.0) -> dict:
    """Area-weighted median equivalent diameter of dark regions (mm) and the share of dark area in
    regions smaller than ``micro_mm`` (micro elements)."""
    m = L < dark_lt
    lab, k = ndimage.label(m, structure=np.ones((3, 3)))
    if k == 0:
        return {"dark_share": 0.0, "dark_blob_median_mm": 0.0, "dark_micro_share": 0.0}
    areas = np.bincount(lab.ravel())[1:].astype(float)
    d = 2 * np.sqrt(areas / np.pi) / ppmm
    o = np.argsort(d)
    cw = np.cumsum(areas[o]) / areas.sum()
    return {"dark_share": float(m.mean()),
            "dark_blob_median_mm": float(d[o][np.searchsorted(cw, 0.5)]),
            "dark_micro_share": float(areas[d < micro_mm].sum() / areas.sum())}


def describe(img, ppmm: float, target_ppmm: float = 2.0) -> dict:
    """Class-level structure descriptor of an artwork image at a known scale (px per mm)."""
    rgb = resample(_as_rgb(img), ppmm, target_ppmm)
    L = lightness(rgb)
    ik = inks(rgb)
    flat = len(ik) <= 12 and sum(s for _, s in ik) > 0.9
    labs = [color.hex_to_lab(h) for h, _ in ik[:8]]
    out = {
        "n_inks": len(ik) if flat else None,
        "continuous_tone": not flat,
        "inks": [{"hex": h, "share": round(s, 4), "L": round(float(color.hex_to_lab(h)[0]), 1)}
                 for h, s in ik[:8]],
        "mean_L": float(L.mean()),
        "L_spread_p5_p95": [float(np.percentile(L, 5)), float(np.percentile(L, 95))],
        "axis_alignment": axis_alignment(L),
        "digital_micro": None,
        **streak(L, target_ppmm),
        **blob_scales(L, target_ppmm),
        "ppmm_used": target_ppmm,
    }
    out["digital_micro"] = bool(out["axis_alignment"] > 0.45)
    # organic vs pixel MACRO is not measured: a traced 45-deg-corner blob and a pixel cluster score
    # alike once blurred to macro scale (tested), so it is left to the spec / by eye.
    out["organic_macro"] = None
    out["vertical_streaks"] = bool(out["coherence"] > 0.15 and 60 <= out["feature_deg"] <= 120)
    out["L_ladder"] = sorted(round(float(x[0]), 1) for x in labs)
    return out


# ============================================================================ image similarity
def _dihedral(a: np.ndarray, k: int) -> np.ndarray:
    b = np.rot90(a, k % 4)
    return b[:, ::-1] if k >= 4 else b


def _crop_square(a: np.ndarray, n: int) -> np.ndarray:
    h, w = a.shape
    y, x = (h - n) // 2, (w - n) // 2
    return a[y:y + n, x:x + n]


def _ncc_cyclic(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float((a * a).sum() * (b * b).sum()))
    if den == 0:
        return 0.0
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(b)), s=a.shape)
    return float(c.max() / den)


def radial_spectrum(L: np.ndarray, nbins: int = 24) -> np.ndarray:
    F = np.abs(np.fft.fft2(L - L.mean())) ** 2
    h, w = L.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    r = np.hypot(fx, fy)
    edges = np.logspace(math.log10(2.0 / max(h, w)), math.log10(0.5), nbins + 1)
    idx = np.digitize(r.ravel(), edges) - 1
    ok = (idx >= 0) & (idx < nbins)
    p = np.bincount(idx[ok], weights=F.ravel()[ok], minlength=nbins)
    n = np.bincount(idx[ok], minlength=nbins)
    return np.log10(p / np.maximum(n, 1) + 1e-12)


def _corr(u: np.ndarray, v: np.ndarray) -> float:
    u = u - u.mean()
    v = v - v.mean()
    d = math.sqrt(float((u * u).sum() * (v * v).sum()))
    return float((u * v).sum() / d) if d > 0 else 0.0


def palette_distance(a_rgb: np.ndarray, b_rgb: np.ndarray, top: int = 6) -> float:
    """Symmetric mean nearest-ink CIEDE2000 between the main inks of two images."""
    A = [color.hex_to_lab(h) for h, _ in inks(a_rgb, 0.02)[:top]]
    B = [color.hex_to_lab(h) for h, _ in inks(b_rgb, 0.02)[:top]]
    if not A or not B:
        return float("nan")
    da = [min(float(color.delta_e2000(x, y)) for y in B) for x in A]
    db = [min(float(color.delta_e2000(x, y)) for y in A) for x in B]
    return float((np.mean(da) + np.mean(db)) / 2)


def image_similarity(a, b, ppmm_a: float, ppmm_b: float, target_ppmm: float = 0.5,
                     scales=(0.8, 0.9, 1.0, 1.1, 1.25), size_mm: float | None = None) -> dict:
    """Compare two artworks at a common physical scale.

    Returns ``ncc_max`` (copy indicator, max over shift, 8 dihedral transforms and ``scales``),
    ``spectrum_corr`` (radial power spectrum shape), ``orientation_corr`` (edge directions),
    ``palette_dE00`` and a plain ``verdict``. Images are compared over a centred square of
    ``size_mm`` (default: the smaller image extent)."""
    ra = resample(_as_rgb(a), ppmm_a, target_ppmm)
    rb_full = resample(_as_rgb(b), ppmm_b, target_ppmm)
    La = lightness(ra)
    n = min(La.shape) if size_mm is None else int(size_mm * target_ppmm)
    best = (-1.0, None)
    for s in scales:
        rb = np.asarray(Image.fromarray(rb_full).resize(
            (max(8, int(rb_full.shape[1] * s)), max(8, int(rb_full.shape[0] * s))), Image.Resampling.BILINEAR))
        Lb = lightness(rb)
        m = min(n, *La.shape, *Lb.shape)
        A = _crop_square(La, m)
        for k in range(8):
            B = _crop_square(_dihedral(Lb, k), m)
            v = _ncc_cyclic(A, B)
            if v > best[0]:
                best = (v, {"scale": s, "dihedral": k, "size_px": m})
    Lb0 = lightness(rb_full)
    m0 = min(La.shape + Lb0.shape)
    res = {
        "ncc_max": round(best[0], 4),
        "ncc_at": best[1],
        "spectrum_corr": round(_corr(radial_spectrum(_crop_square(La, m0)), radial_spectrum(_crop_square(Lb0, m0))), 4),
        "orientation_corr": round(_corr(orientation_hist(La), orientation_hist(Lb0)), 4),
        "palette_dE00": round(palette_distance(ra, rb_full), 2),
        "target_ppmm": target_ppmm,
    }
    if res["ncc_max"] >= NCC_COPY:
        res["verdict"] = "PROBABLE COPY / DERIVATIVE - stop, get IP advice"
    elif res["ncc_max"] < NCC_CLEAR:
        res["verdict"] = "no image-level resemblance found (shift, flip, +-25 % scale)"
    else:
        res["verdict"] = "inconclusive - review by eye and get IP advice"
    return res


# ============================================================================ references (text)
FEATURES = ("digital_micro", "organic_macro", "continuous_tone", "vertical_streaks")


def load_refs(path: Path = REFS_PATH) -> list[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["references"]


def compare_to_references(ours: dict, refs: list[dict] | None = None) -> list[dict]:
    """Class-level overlap with each reference's *published* description. ``None`` features in
    a reference (not described in the cited sources) are skipped, not guessed."""
    refs = refs if refs is not None else load_refs()
    out = []
    for r in refs:
        f = r.get("features", {})
        known = [k for k in FEATURES if f.get(k) is not None and ours.get(k) is not None]
        same = [k for k in known if bool(f[k]) == bool(ours[k])]
        out.append({"id": r["id"], "name": r["name"], "compared": known, "same": same,
                    "family_overlap": round(len(same) / len(known), 2) if known else None,
                    "note": r.get("note", "")})
    return out


# ============================================================================ calibration
def calibrate(ppmm: float = 1.0, repeat_mm: float = 380.0, seed: int = 1) -> dict:
    """Score the method on known cases built from repo art (no outside images)."""
    import warnings
    from . import owner_base as ob
    from .engine import generate, load_pattern
    warnings.simplefilter("ignore", ob.ProxyWarning)
    n = int(repeat_mm * ppmm)
    base = ob.load_owner_base()
    own = base.rgb(n)
    rng = np.random.default_rng(seed)
    # derivative: shifted, rescaled 10 %, 15 % of pixels re-inked at random, recoloured
    der = np.roll(own, (n // 3, n // 5), (0, 1))
    der = np.asarray(Image.fromarray(der).resize((int(n * 1.1), int(n * 1.1)), Image.Resampling.NEAREST))
    noise = rng.random(der.shape[:2]) < 0.15
    der = der.copy()
    der[noise] = own.reshape(-1, 3)[rng.integers(0, own.shape[0] * own.shape[1], noise.sum())]
    der = 255 - (255 - der) * 0.85
    der = der.astype(np.uint8)
    proxy = ob.labels_to_rgb(ob.owner_base_proxy(n), base.hexes)
    cf_spec = load_pattern("cirquefall_shard")
    cf = generate(cf_spec, None, repeat_mm, repeat_mm, ppmm * 25.4, seed=cf_spec.get("seed", 7))
    cases = {"owner_vs_shift_scale_noise_copy": (own, der, ppmm, ppmm * 1.1),
             "owner_vs_proxy_same_statistics": (own, proxy, ppmm, ppmm),
             "owner_vs_cirquefall_shard": (own, cf, ppmm, cf.shape[0] / repeat_mm)}
    return {k: image_similarity(a, b, pa, pb) for k, (a, b, pa, pb) in cases.items()}


# ============================================================================ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.camo.originality", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="image vs image (ncc_max is the copy indicator)")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--ppmm-a", type=float, required=True, help="pixels per mm of image a")
    c.add_argument("--ppmm-b", type=float, required=True, help="pixels per mm of image b (ruler in the photo)")
    d = sub.add_parser("describe", help="structure descriptor + overlap with the cited references")
    d.add_argument("img")
    d.add_argument("--ppmm", type=float, required=True)
    sub.add_parser("calibrate", help="score the method on built-in known cases")
    a = ap.parse_args(argv)
    if a.cmd == "compare":
        r = image_similarity(Image.open(a.a), Image.open(a.b), a.ppmm_a, a.ppmm_b)
    elif a.cmd == "describe":
        desc = describe(Image.open(a.img), a.ppmm)
        r = {"descriptor": desc, "references": compare_to_references(desc)}
    else:
        r = calibrate()
    print(json.dumps(r, indent=1, default=str))


if __name__ == "__main__":
    main()
