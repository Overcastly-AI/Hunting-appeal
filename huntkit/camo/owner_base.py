"""Owner Base camo: ingestion pipeline for the owner's master SVG, plus a labelled PROXY.

The owner's own 4-colour SVG is the PRIMARY camo ("Owner Base"; docs/DECISIONS.md
2026-11-01). Its master lives at ``designs/apparel/camo/source/owner_base.svg`` (byte-exact,
uploaded by the owner). Until it is in the repo, :func:`load_owner_base` falls back to
:func:`owner_base_proxy` (a procedural stand-in that mimics the described structure) and
emits a :class:`ProxyWarning`. Every image or metric made from the proxy must be labelled
"PROXY"; ``OwnerBase.is_proxy`` / ``OwnerBase.title_tag`` carry that.

Pipeline (real file)
--------------------
1. ``parse_svg``  - reads <rect>, <polygon>, <polyline> and <path> elements in paint order,
   with fill (attribute or style), fill-rule and simple transforms (translate/scale/matrix
   on the element and its <g> ancestors). Path data: straight segments only
   (M/m L/l H/h V/v Z/z, implicit lineto after moveto, multiple subpaths per path, e.g.
   ``M0 0L10 0 10 10zM20 20h5v5h-5z``). Curves raise ``ValueError`` (the owner file has none).
2. Rasterise at any pixel size / DPI. Two back ends:
   * ``cairosvg`` when importable (render with crispEdges, then every pixel is snapped to the
     nearest palette ink in CIELAB, so the output is flat 4-ink separations);
   * pure-Python vectorised scanline fill (``rasterize_shapes``), exact pixel-centre
     sampling, even-odd or non-zero rule. Used when cairosvg is missing and in tests.
3. ``edge_wrap_check`` - is the 1000x1000 tile seamless? Mean CIEDE2000 across the wrap seam
   vs the same statistic on interior lines that sit on the SAME pixel grids (multiples of
   250 units are grid lines of the 5.556, 15.625 and 7.8125 unit grids), so a digital-pixel
   boundary at the seam is not mistaken for a seam.
4. ``make_seamless`` - if the check fails: ``offset_blend`` (default) or ``mirror``.
   offset_blend = half-repeat offset copy cross-faded in LABEL space with a noisy smoothstep
   mask (x pass then y pass), so the output still contains only the 4 inks and the repeat
   size is unchanged. mirror = 2x2 reflected tile (always seamless, but it doubles the
   repeat and creates visible Rorschach symmetry axes) - kept only as a fallback.
5. Physical scale: ``render_labels(base, repeat_mm, dpi)``; repeat candidates are scored by
   :func:`repeat_scale_study` with the existing distance (vision.py) and dichromat
   (color.py) metrics plus export.panel_test.

Palette and paint order (owner file): field rect #AE9D6C, paths #8B8148, #C6B497, #313120,
then pixel overlays in #AE9D6C, #8B8148, #313120. Index order everywhere here:
0 field tan, 1 olive, 2 light tan, 3 dark.
"""
from __future__ import annotations

import io
import math
import re
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field as dc_field
from pathlib import Path

import numpy as np
import yaml
from scipy import ndimage, sparse

from . import color, noise

ROOT = Path(__file__).resolve().parents[2]
CAMO_DIR = ROOT / "designs" / "apparel" / "camo"
SVG_PATH = CAMO_DIR / "source" / "owner_base.svg"
SPEC_PATH = CAMO_DIR / "owner_base.yaml"
TILE_UNITS = 1000.0                       # owner viewBox is 0 0 1000 1000

# Grids described for the owner file (units of the 1000-unit viewBox)
MACRO_CELLS = 180                         # 1000/180 = 5.556 units (traced raster)
PIXEL_GRIDS = (64, 128)                   # 15.625 and 7.8125 units (digital overlays)
COMMON_GRID_LINES = (250.0, 500.0, 750.0)  # lines shared by all three grids

# Fallback palette if the YAML spec is unavailable (same values as owner_base.yaml)
_DEFAULT_PALETTE = [
    {"key": "bench_grass", "hex": "#AE9D6C", "role": "field"},
    {"key": "sidehill_olive", "hex": "#8B8148", "role": "olive"},
    {"key": "bleached_tine", "hex": "#C6B497", "role": "light_tan"},
    {"key": "deadfall_shadow", "hex": "#313120", "role": "dark"},
]


class ProxyWarning(UserWarning):
    """The owner's SVG is missing; a procedural PROXY is being used instead."""


# ============================================================================ palette
def load_owner_palette(spec_path: Path = SPEC_PATH) -> list[dict]:
    """Owner palette (list of dicts with key/name/hex/...) in index order
    0 field tan, 1 olive, 2 light tan, 3 dark."""
    try:
        with open(spec_path, "r", encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        pal = spec["palette"]
    except (OSError, KeyError, TypeError):
        pal = _DEFAULT_PALETTE
    order = {"field": 0, "olive": 1, "light_tan": 2, "dark": 3}
    pal = sorted(pal, key=lambda c: order.get(c.get("role"), 99))
    if [c.get("role") for c in pal] != list(order):
        raise ValueError("owner palette must have roles field, olive, light_tan, dark")
    return pal


def palette_hexes(pal: list[dict] | None = None) -> list[str]:
    return [c["hex"].upper() for c in (pal or load_owner_palette())]


def labels_to_rgb(labels: np.ndarray, hexes: list[str]) -> np.ndarray:
    lut = np.array([color.hex_to_rgb8(h) for h in hexes], np.uint8)
    return lut[labels]


def coverage(labels: np.ndarray, n: int = 4) -> np.ndarray:
    return np.bincount(labels.ravel(), minlength=n)[:n] / labels.size


# ============================================================================ SVG parsing
_TOKEN = re.compile(r"[MmLlHhVvZzCcSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_path_d(d: str) -> list[np.ndarray]:
    """Straight-segment SVG path data -> list of subpath vertex arrays (k, 2).

    Supports M/m, L/l, H/h, V/v, Z/z, implicit lineto after a moveto, repeated
    coordinates after a command, and several subpaths in one string. Subpaths are
    returned open (the first vertex is not repeated); every subpath is filled as closed.
    """
    toks = _TOKEN.findall(d)
    subs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = 0.0
    sx = sy = 0.0
    cmd = None
    i = 0

    def num():
        nonlocal i
        if i >= len(toks) or toks[i].isalpha():
            raise ValueError(f"path data: expected number at token {i} in {d[:60]!r}")
        v = float(toks[i])
        i += 1
        return v

    def flush():
        nonlocal cur
        if len(cur) >= 3:
            subs.append(cur)
        cur = []

    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                flush()
                x, y = sx, sy
                continue
            if cmd not in "MmLlHhVv":
                raise ValueError(f"unsupported path command {cmd!r} (straight segments only)")
        elif cmd is None:
            raise ValueError("path data must start with a command")
        if cmd in "Mm":
            nx_, ny_ = num(), num()
            if cmd == "m":
                nx_, ny_ = x + nx_, y + ny_
            flush()
            x, y = sx, sy = nx_, ny_
            cur = [(x, y)]
            cmd = "L" if cmd == "M" else "l"     # implicit lineto
        elif cmd in "Ll":
            nx_, ny_ = num(), num()
            x, y = (x + nx_, y + ny_) if cmd == "l" else (nx_, ny_)
            cur.append((x, y))
        elif cmd in "Hh":
            v = num()
            x = x + v if cmd == "h" else v
            cur.append((x, y))
        elif cmd in "Vv":
            v = num()
            y = y + v if cmd == "v" else v
            cur.append((x, y))
        else:  # pragma: no cover - Zz handled above
            raise ValueError(cmd)
    flush()
    return [np.asarray(s, dtype=np.float64) for s in subs]


def _parse_transform(s: str | None) -> np.ndarray:
    m = np.eye(3)
    if not s:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s):
        a = [float(v) for v in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", args)]
        if name == "translate":
            t = np.array([[1, 0, a[0]], [0, 1, a[1] if len(a) > 1 else 0], [0, 0, 1]])
        elif name == "scale":
            sy_ = a[1] if len(a) > 1 else a[0]
            t = np.diag([a[0], sy_, 1.0])
        elif name == "matrix":
            t = np.array([[a[0], a[2], a[4]], [a[1], a[3], a[5]], [0, 0, 1]])
        else:
            raise ValueError(f"unsupported transform {name!r}")
        m = m @ t
    return m


def _style(el: ET.Element, inherited: dict) -> dict:
    st = dict(inherited)
    for k in ("fill", "fill-rule", "display"):
        if el.get(k) is not None:
            st[k] = el.get(k).strip()
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = (p.strip() for p in part.split(":", 1))
            if k in ("fill", "fill-rule", "display"):
                st[k] = v
    return st


@dataclass
class Shape:
    fill: str                       # '#RRGGBB'
    rule: str                       # 'evenodd' | 'nonzero'
    subpaths: list[np.ndarray]      # in viewBox units (transforms applied)


@dataclass
class SvgDoc:
    viewbox: tuple[float, float, float, float]
    shapes: list[Shape]


def _norm_hex(v: str) -> str | None:
    v = v.strip()
    if v.lower() in ("none", "transparent"):
        return None
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v.upper()
    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", v)
    if m:
        return color.rgb8_to_hex([int(g) for g in m.groups()])
    raise ValueError(f"unsupported fill {v!r}")


def parse_svg(source: str | Path, default_rule: str = "evenodd") -> SvgDoc:
    """Parse an SVG file path or SVG text into filled shapes in paint order.

    ``default_rule``: fill rule used when an element doesn't set one. The SVG default is
    nonzero; the owner brief specifies even-odd, and for traced artwork (holes wound
    opposite to outers, or non-overlapping subpaths) both give the same result.
    """
    text = Path(source).read_text(encoding="utf-8") if (
        isinstance(source, Path) or not str(source).lstrip().startswith("<")) else str(source)
    root = ET.fromstring(text)
    vb = root.get("viewBox") or root.get("viewbox")
    if vb:
        viewbox = tuple(float(v) for v in re.split(r"[\s,]+", vb.strip()))
    else:
        w = float(re.sub(r"[a-z%]+$", "", root.get("width", "1000")))
        h = float(re.sub(r"[a-z%]+$", "", root.get("height", "1000")))
        viewbox = (0.0, 0.0, w, h)
    shapes: list[Shape] = []

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def walk(el, mat, st):
        tag = local(el.tag)
        if tag in ("defs", "clipPath", "mask", "metadata", "title", "desc", "style", "pattern"):
            return
        st = _style(el, st)
        if st.get("display") == "none":
            return
        mat = mat @ _parse_transform(el.get("transform"))
        subs = None
        if tag == "rect":
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            w, h = float(el.get("width", 0)), float(el.get("height", 0))
            subs = [np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])]
        elif tag in ("polygon", "polyline"):
            v = [float(t) for t in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?",
                                              el.get("points", ""))]
            subs = [np.array(v, float).reshape(-1, 2)]
        elif tag == "path":
            subs = parse_path_d(el.get("d", ""))
        if subs is not None:
            fill = _norm_hex(st.get("fill", "#000000"))
            if fill is not None and subs:
                tsubs = [(np.c_[s, np.ones(len(s))] @ mat.T)[:, :2] for s in subs]
                shapes.append(Shape(fill, st.get("fill-rule", default_rule), tsubs))
        for ch in el:
            walk(ch, mat, st)

    walk(root, np.eye(3), {})
    return SvgDoc(viewbox, shapes)


# ============================================================================ rasterise (pure)
def fill_mask(subpaths: list[np.ndarray], viewbox, nx: int, ny: int,
              rule: str = "evenodd", strip_rows: int = 1024) -> np.ndarray:
    """Exact pixel-centre scanline fill of closed polygons. Returns bool (ny, nx)."""
    x0, y0, w, h = viewbox
    sx, sy = nx / w, ny / h
    P1, P2 = [], []
    for s in subpaths:
        if len(s) < 3:
            continue
        p = np.c_[(s[:, 0] - x0) * sx, (s[:, 1] - y0) * sy]
        P1.append(p)
        P2.append(np.roll(p, -1, axis=0))
    out = np.zeros((ny, nx), bool)
    if not P1:
        return out
    a, b = np.concatenate(P1), np.concatenate(P2)
    keep = a[:, 1] != b[:, 1]
    a, b = a[keep], b[keep]
    direction = np.where(b[:, 1] > a[:, 1], 1, -1).astype(np.int32)
    ylo, yhi = np.minimum(a[:, 1], b[:, 1]), np.maximum(a[:, 1], b[:, 1])
    # rows j with ylo <= j + 0.5 < yhi
    jmin = np.clip(np.ceil(ylo - 0.5), 0, ny).astype(np.int64)
    jmax = np.clip(np.ceil(yhi - 0.5), 0, ny).astype(np.int64)      # exclusive
    cnt = np.maximum(jmax - jmin, 0)
    if cnt.sum() == 0:
        return out
    e = np.repeat(np.arange(len(a)), cnt)
    off = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    j = jmin[e] + off
    yc = j + 0.5
    t = (yc - a[e, 1]) / (b[e, 1] - a[e, 1])
    xc = a[e, 0] + t * (b[e, 0] - a[e, 0])
    col = np.clip(np.ceil(xc - 0.5), 0, nx).astype(np.int64)        # first pixel centre >= x
    val = direction[e] if rule == "nonzero" else np.ones_like(e, dtype=np.int32)
    order = np.argsort(j, kind="stable")
    j, col, val = j[order], col[order], val[order]
    for r0 in range(0, ny, strip_rows):
        r1 = min(ny, r0 + strip_rows)
        lo, hi = np.searchsorted(j, [r0, r1])
        acc = np.zeros((r1 - r0, nx + 1), np.int32)
        np.add.at(acc, (j[lo:hi] - r0, col[lo:hi]), val[lo:hi])
        cum = np.cumsum(acc[:, :nx], axis=1)
        out[r0:r1] = (cum % 2 == 1) if rule != "nonzero" else (cum != 0)
    return out


def _nearest_ink(hex_or_rgb, hexes: list[str]) -> int:
    lab = color.srgb_to_lab(np.asarray(hex_or_rgb, float) if not isinstance(hex_or_rgb, str)
                            else color.hex_to_srgb(hex_or_rgb))
    labs = np.array([color.hex_to_lab(h) for h in hexes])
    return int(np.argmin(color.delta_e2000(lab[None], labs)))


def rasterize_shapes(doc: SvgDoc, nx: int, ny: int | None = None,
                     hexes: list[str] | None = None) -> np.ndarray:
    """Pure-Python rasteriser: paint shapes in order into a palette label map (uint8)."""
    ny = ny or nx
    hexes = hexes or palette_hexes()
    labels = np.zeros((ny, nx), np.uint8)
    idx_cache: dict[str, int] = {}
    for s in doc.shapes:
        if s.fill not in idx_cache:
            idx_cache[s.fill] = (hexes.index(s.fill) if s.fill in hexes
                                 else _nearest_ink(s.fill, hexes))
        labels[fill_mask(s.subpaths, doc.viewbox, nx, ny, s.rule)] = idx_cache[s.fill]
    return labels


def snap_rgb_to_palette(rgb: np.ndarray, hexes: list[str]) -> np.ndarray:
    """Map every pixel to the nearest palette ink (CIEDE2000), via the unique colours."""
    flat = rgb.reshape(-1, 3)
    uniq, inv = np.unique(flat, axis=0, return_inverse=True)
    labs = np.array([color.hex_to_lab(h) for h in hexes])
    ul = color.srgb_to_lab(uniq / 255.0)
    d = color.delta_e2000(ul[:, None, :], labs[None, :, :])
    return np.argmin(d, axis=1).astype(np.uint8)[inv.ravel()].reshape(rgb.shape[:2])


def _cairosvg():
    try:
        import cairosvg  # noqa: F401
        return cairosvg
    except Exception:  # ImportError or missing libcairo (OSError)
        return None


def rasterize_svg(path: Path | str, nx: int, ny: int | None = None,
                  hexes: list[str] | None = None, backend: str = "auto") -> tuple[np.ndarray, str]:
    """Rasterise an SVG to a label map. backend: 'auto' (cairosvg if available), 'cairo',
    'pure'. Returns (labels, backend_used)."""
    ny = ny or nx
    hexes = hexes or palette_hexes()
    cs = _cairosvg() if backend in ("auto", "cairo") else None
    if backend == "cairo" and cs is None:
        raise RuntimeError("cairosvg not available")
    if cs is not None:
        from PIL import Image
        text = Path(path).read_text(encoding="utf-8")
        # crisp edges: no anti-aliasing -> flat inks (any residual AA pixel is snapped)
        text = re.sub(r"<svg\b", '<svg shape-rendering="crispEdges"', text, count=1)
        png = cs.svg2png(bytestring=text.encode("utf-8"), output_width=nx, output_height=ny,
                         background_color=hexes[0])
        rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
        return snap_rgb_to_palette(rgb, hexes), "cairosvg"
    return rasterize_shapes(parse_svg(path), nx, ny, hexes), "pure-python"


# ============================================================================ seamless
def _line_de(lab_img: np.ndarray, i: int, axis: int) -> float:
    """Mean dE00 between line i-1 and line i (wrapping) along ``axis``."""
    a = np.take(lab_img, i - 1, axis=axis)
    b = np.take(lab_img, i % lab_img.shape[axis], axis=axis)
    return float(color.delta_e2000(a, b).mean())


def edge_wrap_check(labels: np.ndarray, hexes: list[str] | None = None,
                    tol_ratio: float = 1.5, tol_abs: float = 1.0) -> dict:
    """Edge-wrap dE00 seam test. For each axis: mean dE00 across the wrap seam, the mean
    over the common-grid interior lines (250/500/750 units) and over all interior lines.
    Seamless if seam <= tol_ratio * max(common, interior) + tol_abs."""
    hexes = hexes or palette_hexes()
    labs = np.array([color.hex_to_lab(h) for h in hexes])
    L = labs[labels]
    res = {"tol_ratio": tol_ratio, "tol_abs": tol_abs}
    ok = True
    for axis, name in ((1, "x"), (0, "y")):
        n = labels.shape[axis]
        seam = _line_de(L, 0, axis)
        common = float(np.mean([_line_de(L, int(round(u / TILE_UNITS * n)), axis)
                                for u in COMMON_GRID_LINES]))
        diff = np.diff(L, axis=axis)
        changed = np.any(diff != 0, axis=-1)
        # mean dE over all interior lines (dE only where the ink changes; exact otherwise 0)
        a = np.take(L, np.arange(n - 1), axis=axis)[changed]
        b = np.take(L, np.arange(1, n), axis=axis)[changed]
        interior = float(color.delta_e2000(a, b).sum() / changed.size) if a.size else 0.0
        limit = tol_ratio * max(common, interior) + tol_abs
        res[name] = {"seam_dE00": round(seam, 3), "common_grid_lines_dE00": round(common, 3),
                     "interior_dE00": round(interior, 3), "limit": round(limit, 3),
                     "seam_change_fraction": round(float(np.mean(
                         np.any(np.take(labels, [0], axis=axis) != np.take(labels, [-1], axis=axis), axis=axis))), 4)}
        ok &= seam <= limit
    res["seamless"] = bool(ok)
    return res


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def make_seamless(labels: np.ndarray, method: str = "offset_blend", seed: int = 1,
                  zone=(0.55, 0.85), noise_amp: float = 0.4) -> np.ndarray:
    """Return a seamless version of a label map.

    ``offset_blend`` (default): for x then y, cross-fade the tile with a half-repeat-offset
    copy of itself. Weight w = smoothstep(zone) of the normalised distance from the tile
    centre (0 centre, 1 edge); the copy wins where w + noise_amp * n > 0.5, with n a smooth
    random field in [-1, 1]. At the edges w = 1 (copy only: its edges are interior content
    of the original, so the wrap is continuous); at the centre w = 0 (original only: hides the
    copy's own seam). Works on labels, so only palette inks appear; repeat size unchanged.
    ``mirror``: 2x2 reflected tile (2x repeat, symmetry axes visible).
    """
    if method == "mirror":
        top = np.concatenate([labels, labels[:, ::-1]], axis=1)
        return np.concatenate([top, top[::-1]], axis=0)
    if method != "offset_blend":
        raise ValueError(method)
    rng = np.random.default_rng(seed)
    out = labels.copy()
    H, W = labels.shape
    for axis in (1, 0):
        n = out.shape[axis]
        rolled = np.roll(out, n // 2, axis=axis)
        d = np.abs((np.arange(n) + 0.5) - n / 2) / (n / 2)
        w = _smoothstep(zone[0], zone[1], d)
        w = w[None, :] if axis == 1 else w[:, None]
        nz = ndimage.gaussian_filter(rng.standard_normal((H, W)), max(1.0, min(H, W) / 60), mode="wrap")
        nz = np.clip(nz / (3 * nz.std() + 1e-12), -1, 1)
        out = np.where(w + noise_amp * nz > 0.5, rolled, out)
    return out


# ============================================================================ PROXY generator
PROXY_SEED = 20261101
# ASSUMPTION (proxy only): visible-coverage targets read off the brief ("tan field dominant,
# olive large, dark medium, light tan smaller highlight"). The real file's measured values
# replace these as soon as it is ingested.
PROXY_MACRO_COVERAGE = {"olive": 0.27, "light_tan": 0.17, "dark": 0.20}


def _bilinear_matrix(n_in: int, n_out: int) -> sparse.csr_matrix:
    """Periodic bilinear interpolation: samples at output pixel centres from input cell centres."""
    u = (np.arange(n_out) + 0.5) * n_in / n_out - 0.5
    i0 = np.floor(u).astype(int)
    f = u - i0
    rows = np.r_[np.arange(n_out), np.arange(n_out)]
    cols = np.r_[i0 % n_in, (i0 + 1) % n_in]
    return sparse.csr_matrix((np.r_[1 - f, f], (rows, cols)), shape=(n_out, n_in))


def _nearest_index(n_cells: int, n_out: int) -> np.ndarray:
    return np.floor((np.arange(n_out) + 0.5) * n_cells / n_out).astype(int) % n_cells


@dataclass
class ProxyModel:
    """Coarse-grid masks + overlay grids; rendered at any pixel size by ``render``."""

    macro_masks: list[tuple[int, np.ndarray]]        # (ink, 180x180 float mask) in paint order
    overlays: dict[int, np.ndarray]                  # grid -> int8 (g, g), -1 = none
    seed: int
    info: dict = dc_field(default_factory=dict)

    def macro(self, n: int, r0: int = 0, r1: int | None = None) -> np.ndarray:
        r1 = n if r1 is None else r1
        A = _bilinear_matrix(MACRO_CELLS, n)
        Ay, AxT = A[r0:r1], A.T.tocsr()
        lab = np.zeros((r1 - r0, n), np.uint8)
        for ink, m in self.macro_masks:
            up = np.asarray((AxT.T @ (Ay @ m).T).T)
            lab[up > 0.5] = ink       # bilinear of a binary grid at 0.5 = 45-deg corner cuts
        return lab

    def render(self, n: int, strip_rows: int = 2048) -> np.ndarray:
        out = np.zeros((n, n), np.uint8)
        idx = {g: _nearest_index(g, n) for g in self.overlays}
        for r0 in range(0, n, strip_rows):
            r1 = min(n, r0 + strip_rows)
            lab = self.macro(n, r0, r1)
            for ink in (0, 1, 3):                     # overlay paint order: tan, olive, dark
                for g, ov in self.overlays.items():
                    o = ov[np.ix_(idx[g][r0:r1], idx[g])]
                    lab[o == ink] = ink
            out[r0:r1] = lab
        return out


def build_proxy(seed: int = PROXY_SEED, macro_coverage: dict | None = None) -> ProxyModel:
    """Procedural PROXY of the owner's hybrid structure (see module docstring).

    Macro: periodic fbm blobs classified on the 180x180 grid (dark nested inside olive,
    light-tan highlights in the tan field), then corner-cut diagonally when rendered.
    Micro: square pixel clusters on the 64 and 128 grids, seeded only on blob edges, each
    cluster pulls the colour from across the edge (light tan never used in overlays, as in
    the owner file), grown by a short random walk into polyomino clusters.
    """
    cov = {**PROXY_MACRO_COVERAGE, **(macro_coverage or {})}
    g = noise.Grid(TILE_UNITS, TILE_UNITS, MACRO_CELLS, MACRO_CELLS)
    f_olive = noise.fbm(g, noise.substream(seed, "olive"), 330, 30, 2.2)
    f_dark = noise.normalize(0.75 * f_olive + 0.6 * noise.fbm(g, noise.substream(seed, "dark"), 160, 25, 2.0))
    f_light = noise.fbm(g, noise.substream(seed, "light"), 200, 25, 2.1)
    n = f_olive.size

    def top(f, frac, allowed):
        vals = f[allowed]
        k = int(round(frac * n))
        t = np.partition(vals, vals.size - k)[vals.size - k]
        return (f >= t) & allowed

    free = np.ones_like(f_olive, bool)
    dark = top(f_dark, cov["dark"], free)
    olive = top(f_olive, cov["olive"], ~dark)
    light = top(f_light, cov["light_tan"], ~dark & ~olive)
    # remove isolated single cells (the trace smooths them away)
    for m in (dark, olive, light):
        lone = m & (ndimage.convolve(m.astype(int), np.ones((3, 3)), mode="wrap") <= 1)
        m &= ~lone
    macro_masks = [(1, (olive | dark).astype(np.float64)),
                   (2, light.astype(np.float64)),
                   (3, dark.astype(np.float64))]
    model = ProxyModel(macro_masks, {}, seed)
    rng = noise.substream(seed, "pixels")
    params = {64: (0.10, 6), 128: (0.16, 8)}           # (seed probability, max cluster size)
    for grid in PIXEL_GRIDS:
        L = model.macro(grid)
        edge_nb = np.full(L.shape, -1, np.int16)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = np.roll(L, (dy, dx), axis=(0, 1))
            m = (nb != L) & (edge_nb < 0)
            edge_nb[m] = nb[m]
        ov = np.full(L.shape, -1, np.int8)
        p, smax = params[grid]
        ys, xs = np.nonzero(edge_nb >= 0)
        pick = rng.random(ys.size) < p
        for y, x in zip(ys[pick], xs[pick]):
            ink = int(edge_nb[y, x])
            ink = 0 if ink == 2 else ink                # light tan never in overlays
            size = int(rng.integers(1, smax + 1))
            cy, cx = y, x
            for _ in range(size):
                ov[cy % grid, cx % grid] = ink
                dy, dx = ((0, 1), (0, -1), (1, 0), (-1, 0))[rng.integers(4)]
                cy, cx = cy + dy, cx + dx
        model.overlays[grid] = ov
    model.info = {"macro_coverage_target": cov, "overlay_params": params}
    return model


def owner_base_proxy(n_px: int = 1000, seed: int = PROXY_SEED) -> np.ndarray:
    """PROXY label map (n_px x n_px, inks 0..3) of the 1000-unit owner tile. NOT the real
    owner pattern: a stand-in until designs/apparel/camo/source/owner_base.svg exists."""
    return build_proxy(seed).render(n_px)


# ============================================================================ loader
@dataclass
class OwnerBase:
    source: str                    # 'svg' | 'proxy'
    palette: list[dict]
    path: Path | None = None
    backend: str = ""
    seamless_method: str = "offset_blend"
    seam_report: dict | None = None
    _proxy: ProxyModel | None = None
    _cache: dict = dc_field(default_factory=dict)

    @property
    def is_proxy(self) -> bool:
        return self.source == "proxy"

    @property
    def title_tag(self) -> str:
        return "PROXY - " if self.is_proxy else ""

    @property
    def hexes(self) -> list[str]:
        return palette_hexes(self.palette)

    def raw_labels(self, n: int) -> np.ndarray:
        if ("raw", n) not in self._cache:
            if self.is_proxy:
                lab = self._proxy.render(n)
            else:
                lab, self.backend = rasterize_svg(self.path, n, n, self.hexes)
            self._cache[("raw", n)] = lab
        return self._cache[("raw", n)]

    def check_seamless(self, n: int = 1000) -> dict:
        self.seam_report = edge_wrap_check(self.raw_labels(n), self.hexes)
        return self.seam_report

    def labels(self, n: int) -> np.ndarray:
        """Seamless label map of one repeat at n x n px (fixes the tile if needed)."""
        if self.seam_report is None:
            self.check_seamless()
        lab = self.raw_labels(n)
        if self.seam_report["seamless"]:
            return lab
        if self.seamless_method == "mirror":
            # mirror doubles the tile; render at n/2 so the output stays n px per repeat
            return make_seamless(self.raw_labels(max(8, n // 2)), "mirror")
        return make_seamless(lab, "offset_blend")

    def rgb(self, n: int) -> np.ndarray:
        return labels_to_rgb(self.labels(n), self.hexes)


def load_owner_base(path: Path | str | None = None, allow_proxy: bool = True,
                    seamless_method: str = "offset_blend") -> OwnerBase:
    """Prefer the owner's SVG; fall back to the PROXY (with a ProxyWarning) if it's missing."""
    p = Path(path) if path else SVG_PATH
    pal = load_owner_palette()
    if p.is_file():
        backend = "cairosvg" if _cairosvg() else "pure-python"
        return OwnerBase("svg", pal, p, backend, seamless_method)
    if not allow_proxy:
        raise FileNotFoundError(f"owner SVG not found: {p}")
    warnings.warn(f"Owner base SVG not found at {p}; using the procedural PROXY. "
                  "All outputs are labelled PROXY until the real file is uploaded.",
                  ProxyWarning, stacklevel=2)
    return OwnerBase("proxy", pal, None, "procedural-proxy", seamless_method,
                     _proxy=build_proxy())


# ============================================================================ physical scale
def render_labels(base: OwnerBase, repeat_mm: float, dpi: float) -> np.ndarray:
    n = max(8, int(round(repeat_mm / 25.4 * dpi)))
    return base.labels(n)


def blob_sizes_units(labels: np.ndarray) -> dict:
    """Area-weighted median equivalent diameter (in tile units) of connected regions per ink
    (8-connected, ignores regions < 0.01 % of the tile)."""
    n = labels.shape[0]
    u = TILE_UNITS / n
    out = {}
    for ink in range(4):
        lab, k = ndimage.label(labels == ink, structure=np.ones((3, 3)))
        if k == 0:
            out[ink] = 0.0
            continue
        areas = np.bincount(lab.ravel())[1:].astype(float)
        areas = areas[areas > 1e-4 * labels.size]
        d = 2 * np.sqrt(areas / np.pi) * u
        o = np.argsort(d)
        cw = np.cumsum(areas[o]) / areas.sum()
        out[ink] = float(d[o][np.searchsorted(cw, 0.5)])
    return out


def analyze_owner(base: OwnerBase, repeat_mm: float, n_unit: int = 1000) -> dict:
    """Coverage, luminance, dichromat pair table, distance contrast, panel test at a repeat."""
    from . import export, vision
    keys = [c["key"] for c in base.palette]
    hexes = base.hexes
    lab_u = base.labels(n_unit)
    cov = coverage(lab_u)
    rgb = np.array([color.hex_to_srgb(h) for h in hexes])
    labs = color.srgb_to_lab(rgb)
    labs_sim = color.srgb_to_lab(color.simulate_dichromat(rgb, "ungulate"))
    table = color.palette_contrast_table(hexes, "ungulate")
    for r in table:
        r["pair"] = f"{keys[r['i']]}/{keys[r['j']]}"
    lab1 = base.labels(max(8, int(round(repeat_mm))))           # 1 px / mm
    reps = max(2, int(math.ceil(1500 / repeat_mm)))
    tile = labels_to_rgb(np.tile(lab1, (reps, reps)), hexes)
    tile_deer = color.simulate_dichromat(tile, "ungulate")
    dist = {"0m": {"human_rms_contrast": round(color.rms_contrast(color.image_luminance(tile)), 4),
                   "ungulate_rms_contrast": round(color.rms_contrast(color.image_luminance(tile_deer)), 4)}}
    for d in vision.STANDARD_DISTANCES_M:
        _, ih = vision.simulate_distance(tile, 1.0, d, vision.HUMAN_CPD, display_shape=(8, 8))
        _, iu = vision.simulate_distance(tile_deer, 1.0, d, vision.UNGULATE_CPD, display_shape=(8, 8))
        dist[f"{d}m"] = {"human_rms_contrast": round(ih["rms_contrast"], 4),
                         "ungulate_rms_contrast": round(iu["rms_contrast"], 4),
                         "ungulate_cycle_mm": round(iu["cycle_mm"], 1)}
    blobs = blob_sizes_units(lab_u)
    s = repeat_mm / TILE_UNITS
    mean_lin = (cov[:, None] * color.srgb_to_linear(rgb)).sum(0)
    mean_srgb = color.linear_to_srgb(mean_lin)
    mean_sim = color.srgb_to_lab(color.simulate_dichromat(mean_srgb, "ungulate"))
    bg = {k: round(float(color.delta_e2000(mean_sim, color.srgb_to_lab(
        color.simulate_dichromat(color.hex_to_srgb(h), "ungulate")))), 1)
        for k, h in color.BACKGROUNDS.items()}
    deer_100 = vision.cycle_mm(100, vision.UNGULATE_CPD)
    return {
        "source": base.source, "is_proxy": base.is_proxy, "repeat_mm": repeat_mm,
        "coverage": {k: round(float(c), 4) for k, c in zip(keys, cov)},
        "palette_L": {k: round(float(v), 1) for k, v in zip(keys, labs[:, 0])},
        "palette_L_ungulate": {k: round(float(v), 1) for k, v in zip(keys, labs_sim[:, 0])},
        "coverage_weighted_mean_L": round(float((cov * labs[:, 0]).sum()), 1),
        "luminance_bands": {"dark_L<40": round(float(cov[labs[:, 0] < 40].sum()), 3),
                            "mid_40-60": round(float(cov[(labs[:, 0] >= 40) & (labs[:, 0] < 60)].sum()), 3),
                            "light_L>=60": round(float(cov[labs[:, 0] >= 60].sum()), 3)},
        "dichromat_pairs": [{k: (round(v, 3) if isinstance(v, float) else v)
                             for k, v in r.items() if k not in ("i", "j")} for r in table],
        "dichromat_collapsed_pairs_dE00_lt_5": [r["pair"] for r in table if r["de00_dichromat"] < 5],
        "feature_mm": {"macro_cell": round(TILE_UNITS / MACRO_CELLS * s, 2),
                       "pixel_64": round(TILE_UNITS / 64 * s, 2),
                       "pixel_128": round(TILE_UNITS / 128 * s, 2)},
        "blob_median_diameter_mm": {k: round(blobs[i] * s, 1) for i, k in enumerate(keys)},
        "deer_dissolve_distance_m": {   # distance where deer cycle = feature size
            "pixel_128": round(100 * TILE_UNITS / 128 * s / deer_100, 1),
            "pixel_64": round(100 * TILE_UNITS / 64 * s / deer_100, 1),
            **{f"blob_{k}": round(100 * blobs[i] * s / deer_100, 1) for i, k in enumerate(keys)}},
        "distance_rms_contrast": dist,
        "mean_colour_hex": color.rgb8_to_hex(mean_srgb * 255),
        "mean_vs_backgrounds_dE00_ungulate": bg,
        "panel_test": export.panel_test(lab1, labs[:, 0]),
    }


def repeat_scale_study(base: OwnerBase, candidates_mm=(508, 610, 640, 760, 254, 305, 320, 380)) -> dict:
    """Run analyze_owner for each candidate repeat; compact comparison table."""
    rows = {}
    for r in candidates_mm:
        a = analyze_owner(base, float(r))
        rows[f"{r}mm"] = {
            "min_feature_mm": a["feature_mm"]["pixel_128"],
            "printable_2p5mm": a["feature_mm"]["pixel_128"] >= 2.5,
            "repeats_across_1520mm": round(1520 / r, 2),
            "blob_median_mm": a["blob_median_diameter_mm"],
            "deer_dissolve_m": a["deer_dissolve_distance_m"],
            "ungulate_rms": {k: v["ungulate_rms_contrast"] for k, v in a["distance_rms_contrast"].items()},
            "panel_test": a["panel_test"],
        }
    return rows
