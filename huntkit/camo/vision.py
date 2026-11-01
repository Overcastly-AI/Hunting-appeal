"""Distance (spatial-acuity) simulation.

A viewer with acuity ``cpd`` cycles/degree cannot resolve detail finer than one cycle,
which at distance d spans  d * tan(1 deg / cpd)  millimetres. We model viewing at
distance d by:

1. low-pass filtering in *linear light* with a Gaussian whose half-amplitude cutoff equals
   the acuity limit (sigma chosen so the Gaussian MTF = 0.5 at f_c = 1/cycle_mm:
   sigma_mm = sqrt(2 ln 2) / (2 pi f_c));
2. resampling to the Nyquist spacing of the observer (cycle_mm / 2 per sample) — this is
   the "downsample by angular resolution" step; it produces what the observer's retina can
   represent;
3. optionally re-enlarging (nearest) for display.

ASSUMPTION: ungulate acuity defaults to 6 cycles/degree, i.e. roughly a Snellen 20/100
equivalent reported for white-tailed deer (D'Angelo et al. 2008 estimated ~20/100 from
ganglion-cell density; behavioural estimates vary). Human 20/20 ~ 30 cpd.
Atmospheric haze/contrast loss over distance is NOT modelled (a conservative choice for
camo: real-world contrast at 300 m is lower still).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from . import color

UNGULATE_CPD = 6.0   # ASSUMPTION, see module docstring
HUMAN_CPD = 30.0
STANDARD_DISTANCES_M = (10, 50, 150, 300)


def cycle_mm(distance_m: float, cpd: float = UNGULATE_CPD) -> float:
    """Smallest resolvable cycle (mm) at a distance."""
    return distance_m * 1000.0 * math.tan(math.radians(1.0 / cpd))


def simulate_distance(rgb_u8: np.ndarray, px_per_mm: float, distance_m: float,
                      cpd: float = UNGULATE_CPD, wrap: bool = True,
                      display_shape: tuple[int, int] | None = None) -> tuple[np.ndarray, dict]:
    """Return (image, info). ``image`` is uint8 RGB as the observer resolves it, enlarged
    back to ``display_shape`` (default: input shape) with nearest-neighbour for display.

    ``wrap=True`` treats the image as a periodic tile (correct for a seamless repeat).
    """
    cyc = cycle_mm(distance_m, cpd)
    fc = 1.0 / cyc  # cycles / mm
    sigma_mm = math.sqrt(2 * math.log(2)) / (2 * math.pi * fc)
    sigma_px = sigma_mm * px_per_mm
    lin = color.srgb_to_linear(rgb_u8.astype(np.float64) / 255.0)
    mode = "wrap" if wrap else "nearest"
    blurred = np.stack([ndimage.gaussian_filter(lin[..., c], sigma_px, mode=mode)
                        for c in range(3)], -1)
    # Nyquist resampling of the observer: samples every cyc/2 mm
    step_px = max(1.0, (cyc / 2.0) * px_per_mm)
    h, w = rgb_u8.shape[:2]
    ny, nx = max(1, int(round(h / step_px))), max(1, int(round(w / step_px)))
    ys = ((np.arange(ny) + 0.5) * h / ny).astype(int).clip(0, h - 1)
    xs = ((np.arange(nx) + 0.5) * w / nx).astype(int).clip(0, w - 1)
    small = blurred[np.ix_(ys, xs)]
    y_small = color.relative_luminance(color.linear_to_srgb(small))
    info = {
        "distance_m": distance_m, "cpd": cpd, "cycle_mm": cyc, "sigma_mm": sigma_mm,
        "observer_samples": (ny, nx),
        "rms_contrast": color.rms_contrast(y_small),
    }
    dh, dw = display_shape or (h, w)
    yi = (np.arange(dh) * ny // dh).clip(0, ny - 1)
    xi = (np.arange(dw) * nx // dw).clip(0, nx - 1)
    disp = color.linear_to_srgb(small[np.ix_(yi, xi)])
    return np.round(disp * 255).astype(np.uint8), info
