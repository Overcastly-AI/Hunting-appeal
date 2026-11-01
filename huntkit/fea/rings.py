"""Thin circular ring under self-equilibrated radial loads (bushing contact on a tube wall).

Used for the telescoping-crown bushings: the leg presses on the stay (and the stay on the leg)
through a UHMWPE bushing. The old check used the diametral POINT-load ring moment
M_max = F R / pi = 0.318 F R (Roark, ring under two opposed concentrated loads). A close-fit
bushing spreads the contact over an arc; this module gives the peak ring moment for a cosine
pressure distribution over +-alpha at the load side, reacted by the same distribution diametrically
opposite (the bushing pair carries a net side force F from leg to stay).

Theory (inextensional thin ring, Fourier series): radial line load w(theta) = a0 + sum a_n cos n theta
(force per unit arc length, self-equilibrated, symmetric). The bending moment is
    M(theta) = -R^2 sum_{n>=2} a_n cos(n theta) / (n^2 - 1)
Check: two opposed point loads F -> a_n = 2F/(pi R) (even n) -> M(0) = -F R / pi (Roark case 1,
|M| = 0.3183 F R under the load) and M(pi/2) = F R (1/2 - 1/pi) = 0.1817 F R.
Verified in tests/test_fea.py (point-load limit + Roark values).
"""
from __future__ import annotations

import numpy as np


def _coeffs(alpha_rad: float, n_max: int):
    """Fourier cosine coefficients (per unit F/R) of two opposed cosine pressure patches of
    half-angle alpha, each with resultant F (patch at theta=0 pushes +, patch at pi pushes back)."""
    n = np.arange(n_max + 1)
    if alpha_rad < 1e-6:
        a = np.where(n % 2 == 0, 2.0 / np.pi, 0.0)
        a[0] = 1.0 / np.pi
        return n, a
    th = np.linspace(-alpha_rad, alpha_rad, 2001)
    shape = np.cos(np.pi * th / (2 * alpha_rad))           # half-cosine pressure, zero at the patch edges
    # resultant of the patch along theta=0: integral w cos(theta) R dtheta = F
    norm = np.trapezoid(shape * np.cos(th), th)
    w = shape / norm                                         # per unit F/R
    a = np.array([np.trapezoid(w * np.cos(k * th), th) / np.pi for k in n])
    a = np.where(n % 2 == 0, 2 * a, 0.0)                     # opposite patch doubles even, cancels odd
    a[0] = a[0] / 2
    return n, a


def ring_moment(theta, alpha_deg: float = 0.0, n_max: int = 600):
    """M(theta) / (F R) for the ring (sign: + = tension on the inner fibre)."""
    n, a = _coeffs(np.radians(alpha_deg), n_max)
    th = np.atleast_1d(np.asarray(theta, float))
    k = n[2:]
    M = -(a[2:, None] * np.cos(k[:, None] * th[None, :]) / (k[:, None] ** 2 - 1)).sum(axis=0)
    return M if np.ndim(theta) else float(M[0])


def ring_moment_coeff(alpha_deg: float = 0.0) -> float:
    """Peak |M| / (F R) for opposed cosine contact patches of half-angle ``alpha_deg``.
    alpha 0 -> 1/pi = 0.318 (point loads)."""
    th = np.linspace(0, np.pi / 2, 721)
    return float(np.max(np.abs(ring_moment(th, alpha_deg))))
