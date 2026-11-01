"""Procedural textures for the pack render: camo accent, carbon twill, fabric normal maps.

All textures tile seamlessly (wrap-mode filters). One texture repeat = geom.TILE_MM on fabric
(500 mm) and 40 mm on carbon tubes/plates.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

OWNER_BASE_HEX = ["#ae9d6c", "#8b8148", "#c6b497", "#313120"]   # base tan, olive, light tan, dark


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _field(rng, n, sigma):
    f = ndimage.gaussian_filter(rng.standard_normal((n, n)), sigma, mode="wrap")
    return (f - f.mean()) / (f.std() + 1e-12)


def fallback_camo(size: int = 1024, seed: int = 7, palette=OWNER_BASE_HEX) -> Image.Image:
    """4-colour stand-in in the *structure* of the owner base camo (macro blobs traced on a
    coarse grid + digital pixel overlays at two scales). Only used until
    huntkit.camo.owner_base.load_owner_base() exists."""
    rng = np.random.default_rng(seed)
    g = size // 8                                # macro grid (blob edges stair-step on it)
    olive = _field(rng, g, g / 14) + 0.35 * _field(rng, g, g / 40)
    light = _field(rng, g, g / 18) + 0.3 * _field(rng, g, g / 50)
    dark = _field(rng, g, g / 22) + 0.35 * _field(rng, g, g / 60)
    idx = np.zeros((g, g), np.uint8)                # 0 base tan
    idx[light > 0.75] = 2
    idx[olive > 0.25] = 1
    idx[(dark > 0.65) & (olive > -0.2)] = 3
    up = np.kron(idx, np.ones((8, 8), np.uint8))
    # digital pixel overlays at 16 px and 8 px near blob edges
    for blk, p in ((16, 0.10), (8, 0.07)):
        gb = size // blk
        small = up[::blk, ::blk]
        edge = ndimage.binary_dilation(ndimage.morphological_gradient(small, size=2) > 0)
        flip = (rng.random((gb, gb)) < p) & edge
        nb = np.roll(small, rng.integers(-1, 2), axis=rng.integers(0, 2))
        small = np.where(flip, nb, small)
        up = np.where(np.kron(flip, np.ones((blk, blk), bool)), np.kron(small, np.ones((blk, blk), np.uint8)), up)
    pal = np.array([hex_rgb(h) for h in palette], np.uint8)
    rgb = pal[up]
    # subtle fabric mottling so flat ink areas don't look plastic
    m = ndimage.gaussian_filter(rng.standard_normal((size, size)), 1.0, mode="wrap")
    rgb = np.clip(rgb.astype(float) * (1 + 0.03 * m[..., None]), 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def owner_base_camo(size: int = 1024) -> tuple[Image.Image, str]:
    """Owner base camo if huntkit.camo.owner_base exists, else the 4-colour fallback."""
    try:
        from huntkit.camo.owner_base import load_owner_base  # type: ignore
        obj = load_owner_base()
        img = _to_image(obj)
        if img is not None:
            return img.convert("RGB").resize((size, size), Image.NEAREST), "owner_base"
    except Exception:  # noqa: BLE001 - another agent is building it; any failure -> fallback
        pass
    return fallback_camo(size), "fallback_4color"


def _to_image(obj):
    from pathlib import Path
    if isinstance(obj, Image.Image):
        return obj
    if isinstance(obj, (str, Path)) and Path(obj).exists() and str(obj).lower().endswith((".png", ".jpg")):
        return Image.open(obj)
    if isinstance(obj, np.ndarray):
        a = obj
        if a.dtype != np.uint8:
            a = (np.clip(a, 0, 1) * 255).astype(np.uint8) if a.max() <= 1.0 else a.astype(np.uint8)
        return Image.fromarray(a)
    for key in ("image", "rgb", "raster", "img"):
        v = obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
        if v is not None:
            return _to_image(v)
    return None


def carbon_twill(size: int = 512, tows: int = 16) -> Image.Image:
    """2x2 twill carbon weave, base colour (dark, with per-tow sheen variation)."""
    cell = size // tows
    y, x = np.mgrid[0:size, 0:size]
    i, j = x // cell, y // cell
    fx, fy = (x % cell) / cell, (y % cell) / cell
    warp = ((i + j) // 2) % 2 == 0
    # tow cross-section shading (bright crown, darker edges) along the tow width
    across = np.where(warp, fx, fy)
    along = np.where(warp, fy, fx)
    crown = np.sin(np.pi * across) ** 0.7
    rng = np.random.default_rng(3)
    streak = ndimage.gaussian_filter(rng.standard_normal((size, size)), (0.6, 6), mode="wrap")
    streak2 = ndimage.gaussian_filter(rng.standard_normal((size, size)), (6, 0.6), mode="wrap")
    st = np.where(warp, streak, streak2)
    base = 26 + 30 * crown * np.where(warp, 1.0, 0.75) + 5 * st - 6 * (np.abs(along - 0.5) > 0.47)
    rgb = np.stack([base * 0.97, base * 1.0, base * 1.06], -1)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def _height_to_normal(h, strength):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-gx, -gy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB")


def ripstop_normal(size: int = 512, cells: int = 80, strength: float = 1.6) -> Image.Image:
    """Cordura/ripstop look: plain-weave grain plus a ripstop grid (500 mm tile -> 6.25 mm grid)."""
    y, x = np.mgrid[0:size, 0:size] / size
    weave = 0.35 * np.sin(2 * np.pi * x * size / 2.0) * np.sin(2 * np.pi * y * size / 2.0)
    gx = np.abs(((x * cells) % 1.0) - 0.5)
    gy = np.abs(((y * cells) % 1.0) - 0.5)
    grid = np.clip((gx - 0.42) / 0.08, 0, 1) + np.clip((gy - 0.42) / 0.08, 0, 1)
    rng = np.random.default_rng(11)
    noise = ndimage.gaussian_filter(rng.standard_normal((size, size)), 2.0, mode="wrap")
    h = 0.25 * weave + 0.9 * grid + 0.35 * noise
    return _height_to_normal(h, strength)


def knit_mesh_normal(size: int = 512, cells: int = 110, strength: float = 2.5) -> Image.Image:
    """Stretch-mesh (front pocket) look: diamond knit holes."""
    y, x = np.mgrid[0:size, 0:size] / size
    u = (x + y) * cells
    v = (x - y) * cells
    h = -np.clip(1 - 2.2 * np.hypot((u % 1) - 0.5, (v % 1) - 0.5), 0, 1)
    return _height_to_normal(ndimage.gaussian_filter(h, 0.7, mode="wrap"), strength)


def foam_normal(size: int = 256, strength: float = 1.2) -> Image.Image:
    """Spacer-mesh / padded-strap surface."""
    y, x = np.mgrid[0:size, 0:size] / size
    h = np.sin(2 * np.pi * x * 64) * np.sin(2 * np.pi * y * 64) * 0.5
    rng = np.random.default_rng(5)
    h += 0.5 * ndimage.gaussian_filter(rng.standard_normal((size, size)), 1.2, mode="wrap")
    return _height_to_normal(h, strength)


def solid(hex_color: str, size: int = 4) -> Image.Image:
    return Image.new("RGB", (size, size), hex_rgb(hex_color))
