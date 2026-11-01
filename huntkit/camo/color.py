"""Colour science for camo/colorway work: sRGB <-> CIELAB (D65), CIEDE2000, a dichromat
(ungulate) vision simulation and luminance-contrast metrics.

Ungulate vision model — what it is and what it is NOT
------------------------------------------------------
Deer, elk and other cervids/bovids are cone dichromats: a short-wave cone (lambda_max
~455 nm) and a middle-wave cone (lambda_max ~537 nm), no long-wave (L, ~560 nm) cone
(Jacobs et al. 1994, white-tailed/fallow deer ERG flicker photometry). Their lens also
transmits more near-UV than ours.

We only have RGB images, not spectra, so we approximate with a human-dichromat projection:

* The missing cone in deer is the LONG-wave cone, so the closest human analogue is
  *protanopia* (L missing, M+S retained), not deuteranopia (M missing). The deer M cone at
  ~537 nm sits within a few nm of the human M cone (~535-541 nm), so the retained cone set
  of a human protanope is a reasonable stand-in. We therefore use the Vienot, Brettel &
  Mollon (1999) single-plane protanope projection in LMS space ("ungulate" model).
  A deuteranope projection is also provided ("deuteranope") for comparison only.
* Not modelled: the 455 vs ~440 nm S-cone shift, UV sensitivity (an RGB image has no UV
  channel — optical brighteners must be controlled by spec, see colorways.yaml), rod-
  dominated crepuscular vision, and deer spatial acuity (see vision.py for acuity).
* Luminance for the ungulate model is taken from the simulated image (no L-cone input),
  so reds/oranges darken markedly — the well-known reason blaze orange reads as a dull
  grey-yellow to deer.

Treat the output as a *screening* tool for colour pairs that collapse, not a spectral
truth. Spectral reflectance (incl. UV and NIR) must be checked on physical lab dips.
"""
from __future__ import annotations

import numpy as np

# D65 reference white (CIE 1931 2 deg), Y = 1
WHITE_D65 = np.array([0.95047, 1.00000, 1.08883])

_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]])
_M_XYZ2RGB = np.linalg.inv(_M_RGB2XYZ)


# ----------------------------------------------------------------------------- hex helpers
def hex_to_rgb8(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"bad hex colour {h!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb8_to_hex(rgb) -> str:
    r, g, b = (int(np.clip(round(float(c)), 0, 255)) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_srgb(h: str) -> np.ndarray:
    return np.array(hex_to_rgb8(h), dtype=np.float64) / 255.0


# ----------------------------------------------------------------------------- transfer
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, None)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


# ----------------------------------------------------------------------------- XYZ / Lab
def srgb_to_xyz(rgb):
    """sRGB in [0,1] (..., 3) -> XYZ (Y=1 white)."""
    return srgb_to_linear(rgb) @ _M_RGB2XYZ.T


def xyz_to_srgb(xyz):
    return linear_to_srgb(np.asarray(xyz) @ _M_XYZ2RGB.T)


def _f(t):
    d = 6 / 29
    return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)


def _finv(t):
    d = 6 / 29
    return np.where(t > d, t ** 3, 3 * d * d * (t - 4 / 29))


def xyz_to_lab(xyz, white=WHITE_D65):
    x = np.asarray(xyz, dtype=np.float64) / white
    fx, fy, fz = _f(x[..., 0]), _f(x[..., 1]), _f(x[..., 2])
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1)


def lab_to_xyz(lab, white=WHITE_D65):
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    return np.stack([_finv(fx), _finv(fy), _finv(fz)], axis=-1) * white


def srgb_to_lab(rgb):
    return xyz_to_lab(srgb_to_xyz(rgb))


def lab_to_srgb(lab):
    return xyz_to_srgb(lab_to_xyz(lab))


def hex_to_lab(h: str) -> np.ndarray:
    return srgb_to_lab(hex_to_srgb(h))


def relative_luminance(rgb):
    """CIE Y of sRGB colour(s) in [0,1]."""
    return srgb_to_xyz(rgb)[..., 1]


# ----------------------------------------------------------------------------- CIEDE2000
def delta_e2000(lab1, lab2, kL: float = 1.0, kC: float = 1.0, kH: float = 1.0):
    """CIEDE2000 colour difference (Sharma, Wu & Dalal 2005 formulation). Broadcasts."""
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cbar ** 7 / (Cbar ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    h1p = np.where((a1p == 0) & (b1 == 0), 0.0, h1p)
    h2p = np.where((a2p == 0) & (b2 == 0), 0.0, h2p)

    dLp = L2 - L1
    dCp = C2p - C1p
    zero = (C1p * C2p) == 0
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, dh)
    dh = np.where(dh < -180, dh + 360, dh)
    dh = np.where(zero, 0.0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh) / 2)

    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hsum = h1p + h2p
    hbp = np.where(np.abs(h1p - h2p) <= 180, hsum / 2,
                   np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2))
    hbp = np.where(zero, hsum, hbp)
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2 + (dHp / (kH * Sh)) ** 2
                   + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


# ----------------------------------------------------------------------------- dichromat sim
# Vienot, Brettel & Mollon (1999), "Digital video colourmaps for checking the legibility of
# displays by dichromats", Color Res. Appl. 24(4). Linear-RGB -> LMS (Smith-Pokorny based).
_M_RGB2LMS = np.array([[17.8824, 43.5161, 4.11935],
                       [3.45565, 27.1554, 3.86714],
                       [0.0299566, 0.184309, 1.46709]])
_M_LMS2RGB = np.linalg.inv(_M_RGB2LMS)
_PROJ = {
    # protanope: L reconstructed from M and S (missing long-wave cone) -> ungulate analogue
    "ungulate": np.array([[0.0, 2.02344, -2.52581], [0, 1, 0], [0, 0, 1]]),
    "protanope": np.array([[0.0, 2.02344, -2.52581], [0, 1, 0], [0, 0, 1]]),
    # deuteranope: M reconstructed from L and S (comparison only)
    "deuteranope": np.array([[1, 0, 0], [0.494207, 0.0, 1.24827], [0, 0, 1]]),
}
_SIM_CACHE: dict[str, np.ndarray] = {}


def dichromat_matrix(kind: str = "ungulate") -> np.ndarray:
    """3x3 linear-RGB -> simulated linear-RGB matrix."""
    if kind not in _SIM_CACHE:
        if kind not in _PROJ:
            raise ValueError(f"unknown dichromat model {kind!r}; use {sorted(_PROJ)}")
        _SIM_CACHE[kind] = _M_LMS2RGB @ _PROJ[kind] @ _M_RGB2LMS
    return _SIM_CACHE[kind]


def simulate_dichromat(rgb, kind: str = "ungulate"):
    """Simulate dichromat appearance. ``rgb``: sRGB floats [0,1] or uint8, (..., 3).

    Returns the same dtype convention as the input (uint8 in -> uint8 out).
    """
    a = np.asarray(rgb)
    is_u8 = a.dtype == np.uint8
    f = a.astype(np.float64) / 255.0 if is_u8 else a.astype(np.float64)
    lin = srgb_to_linear(f) @ dichromat_matrix(kind).T
    out = linear_to_srgb(np.clip(lin, 0.0, 1.0))
    return np.round(out * 255).astype(np.uint8) if is_u8 else out


# ----------------------------------------------------------------------------- contrast metrics
def weber_contrast(y_target, y_background):
    return (np.asarray(y_target) - y_background) / y_background


def michelson_contrast(y1, y2):
    y1, y2 = np.asarray(y1, float), np.asarray(y2, float)
    return np.abs(y1 - y2) / (y1 + y2)


def rms_contrast(y_image):
    """RMS (std/mean) luminance contrast of an image of luminances."""
    y = np.asarray(y_image, dtype=np.float64)
    m = y.mean()
    return float(y.std() / m) if m > 0 else 0.0


def image_luminance(rgb_u8_or_float):
    a = np.asarray(rgb_u8_or_float)
    f = a.astype(np.float64) / 255.0 if a.dtype == np.uint8 else a.astype(np.float64)
    return relative_luminance(f)


def palette_contrast_table(hexes: list[str], kind: str = "ungulate") -> list[dict]:
    """Pairwise metrics for a palette: dE00 (human), dE00 (simulated dichromat), luminance
    Michelson contrast (human Y and dichromat-sim Y)."""
    rgb = np.array([hex_to_srgb(h) for h in hexes])
    sim = simulate_dichromat(rgb, kind)
    lab_h, lab_s = srgb_to_lab(rgb), srgb_to_lab(sim)
    yh, ys = relative_luminance(rgb), relative_luminance(sim)
    rows = []
    for i in range(len(hexes)):
        for j in range(i + 1, len(hexes)):
            rows.append({
                "i": i, "j": j,
                "de00_human": float(delta_e2000(lab_h[i], lab_h[j])),
                "de00_dichromat": float(delta_e2000(lab_s[i], lab_s[j])),
                "michelson_human": float(michelson_contrast(yh[i], yh[j])),
                "michelson_dichromat": float(michelson_contrast(ys[i], ys[j])),
                "dL_dichromat": float(abs(lab_s[i, 0] - lab_s[j, 0])),
            })
    return rows


# ASSUMPTION: representative western-mountain background colours (sRGB, eyeballed from
# typical field photography under overcast/diffuse light, NOT spectro-measured). Used only
# for relative "does the pattern mean sit inside the habitat gamut" screening.
BACKGROUNDS = {
    "dry_bunchgrass": "#A38F6A",
    "sagebrush": "#878A76",
    "conifer_shade": "#3A3C31",
    "talus_scree": "#9A958B",
    "aspen_bark_late": "#B6B1A3",
    "shaded_snow": "#C8CCD0",
    "dark_timber_floor": "#4B4237",
}
