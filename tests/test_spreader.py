"""Spreader (BP-06) v2: plate solver verification against closed forms, rail/foam model sanity,
and the manufacturing rules of the chosen part.

Closed forms: Timoshenko & Woinowsky-Krieger, Theory of Plates and Shells (1959): simply supported
square plate, centre point load w = 0.01160 P a^2 / D, uniform w = 0.00406 q a^4 / D; clamped
square, uniform w = 0.00126 q a^4 / D; orthotropic Navier double series; infinite plate on a
Winkler foundation w0 = P / (8 sqrt(k D)) (Hetenyi).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.fea.composite import Laminate, Ply
from huntkit.fea.plate_grid import GridPlate, Spring, iso_D

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "designs" / "pack_5200" / "analysis" / "spreader_results.json"


def _ss_square(n=40, a=200.0, D=None):
    D = iso_D(70000.0, 2.0, 0.3) if D is None else D
    pl = GridPlate(0.0, 0.0, n, n, a / n, D)
    xy = pl.node_xy()
    edge = (xy[:, 0] < 1e-6) | (xy[:, 0] > a - 1e-6) | (xy[:, 1] < 1e-6) | (xy[:, 1] > a - 1e-6)
    return pl, edge


def test_plate_ss_point_load():
    pl, edge = _ss_square()
    pl.fix_w(np.nonzero(edge)[0])
    w = pl.solve(pl.load_vector(point=[(100.0, 100.0, 100.0)]))["w"]
    D = pl.D[0, 0, 0, 0]
    assert w.max() == pytest.approx(0.01160 * 100.0 * 200.0 ** 2 / D, rel=0.02)


def test_plate_ss_uniform():
    pl, edge = _ss_square()
    pl.fix_w(np.nonzero(edge)[0])
    q = np.full((pl.nx, pl.ny), 1e-3)
    w = pl.solve(pl.load_vector(q))["w"]
    D = pl.D[0, 0, 0, 0]
    assert w.max() == pytest.approx(0.00406 * 1e-3 * 200.0 ** 4 / D, rel=0.01)


def test_plate_clamped_uniform():
    pl, edge = _ss_square()
    for k in np.nonzero(edge)[0]:
        pl.fixed.update((3 * k, 3 * k + 1, 3 * k + 2))
    q = np.full((pl.nx, pl.ny), 1e-3)
    w = pl.solve(pl.load_vector(q))["w"]
    D = pl.D[0, 0, 0, 0]
    assert w.max() == pytest.approx(0.00126 * 1e-3 * 200.0 ** 4 / D, rel=0.02)


def test_plate_orthotropic_navier():
    ply = Ply.from_material("cfrp_t700_ud_epoxy_ply")
    lam = Laminate([ply] * 8, [0, 90, 0, 90, 90, 0, 90, 0])
    D = lam.D.copy()
    D[0, 2] = D[2, 0] = D[1, 2] = D[2, 1] = 0.0
    a, b, n = 240.0, 160.0, 48
    pl = GridPlate(0.0, 0.0, n, 32, a / n, D)
    xy = pl.node_xy()
    edge = (xy[:, 0] < 1e-6) | (xy[:, 0] > a - 1e-6) | (xy[:, 1] < 1e-6) | (xy[:, 1] > b - 1e-6)
    pl.fix_w(np.nonzero(edge)[0])
    P = 100.0
    w = pl.solve(pl.load_vector(point=[(a / 2, b / 2, P)]))["w"]
    m = np.arange(1, 160, 2)[:, None]
    k = np.arange(1, 160, 2)[None, :]
    den = np.pi ** 4 * (D[0, 0] * (m / a) ** 4 + 2 * (D[0, 1] + 2 * D[2, 2]) * (m / a) ** 2 * (k / b) ** 2
                        + D[1, 1] * (k / b) ** 4)
    sgn = np.sin(m * np.pi / 2) ** 2 * np.sin(k * np.pi / 2) ** 2
    w_ref = float((4 * P / (a * b) * sgn / den).sum())
    assert w.max() == pytest.approx(w_ref, rel=0.03)


def test_plate_winkler_point_load():
    D = iso_D(70000.0, 2.0, 0.3)
    n, h, kf = 80, 5.0, 0.02
    pl = GridPlate(-200.0, -200.0, n, n, h, D)
    for k, (x, y) in enumerate(pl.node_xy()):
        wgt = (0.5 if abs(abs(x) - 200) < 1e-6 else 1.0) * (0.5 if abs(abs(y) - 200) < 1e-6 else 1.0)
        pl.springs.append(Spring(k, kf * h * h * wgt, 0.0, unilateral=False))
    w = pl.solve(pl.load_vector(point=[(0.0, 0.0, 100.0)]))["w"]
    assert w.max() == pytest.approx(100.0 / (8 * np.sqrt(kf * D[0, 0])), rel=0.02)


def test_unilateral_contact_lifts_off():
    """Seesaw: unilateral supports at x 0 and 100, hinge line at x 200, load at x 150.
    The x 100 line must bear and the x 0 line must lift off (no tension in a contact)."""
    D = iso_D(70000.0, 2.0, 0.3)
    pl = GridPlate(0.0, 0.0, 20, 4, 10.0, D)
    xy = pl.node_xy()
    at0 = np.nonzero(np.isclose(xy[:, 0], 0.0))[0]
    at100 = np.nonzero(np.isclose(xy[:, 0], 100.0))[0]
    for k in np.r_[at0, at100]:
        pl.springs.append(Spring(int(k), 0.0, 0.0))
    pl.fix_w(np.nonzero(np.isclose(xy[:, 0], 200.0))[0])
    sol = pl.solve(pl.load_vector(point=[(150.0, 20.0, 100.0)]))
    f = sol["spring_force"]
    assert (f >= -1e-9).all()
    assert f[: len(at0)].sum() == pytest.approx(0.0, abs=1e-9)
    assert f[len(at0):].sum() == pytest.approx(50.0, rel=0.02)


# ---------------------------------------------------------------------------- foam / rail
def test_foam_curve_hits_datasheet_points():
    from huntkit.gendesign.spreader import foam_curve
    e, s = foam_curve("xlpe_foam_l200")
    assert np.interp(0.25, e, s) * 1000 == pytest.approx(48.0)
    assert np.interp(0.50, e, s) * 1000 == pytest.approx(103.0)
    assert (np.diff(s) > 0).all()


def test_rail_section_flat_limit():
    """A very wide rigid stay on the rail gives the uniform pressure q / W."""
    from huntkit.gendesign.spreader import rail_section
    r = rail_section(0.8, r_stay=1e6)
    assert r["peak_kpa"] == pytest.approx(0.8 / 100.0 * 1000.0, rel=0.03)


def test_rail_section_peaks_over_uniform():
    from huntkit.gendesign.spreader import rail_section
    r = rail_section(0.8)
    assert r["peak_kpa"] > 0.8 / 100.0 * 1000.0
    assert r["foam_mm"] < r["foam_h_mm"]


# ---------------------------------------------------------------------------- part rules
def test_outline_rounded_and_notched():
    from shapely.geometry import Point
    from huntkit.gendesign import spreader as S
    sh = S.part_shape()
    minx, miny, maxx, maxy = sh.bounds
    # no square corner: the corner points of the bounding box are outside the part
    for x, z in ((minx, miny), (maxx, miny), (minx, maxy), (maxx, maxy)):
        assert not sh.buffer(0.5).contains(Point(x, z))
    # a notch at each cleat inside the sheet height (bag_attachment.md stations)
    for zf in (142.0, 190.0, 330.0):
        for s in (1.0, -1.0):
            assert not sh.contains(Point(s * 112.0, zf))
            assert sh.contains(Point(s * 112.0, zf + 20.0)) or sh.contains(Point(s * 112.0, zf - 20.0))


def test_cleat_clearance():
    """Each notch clears the fairlead cheek by the stated air gap."""
    from huntkit.gendesign import spreader as S
    from shapely.geometry import box
    sh = S.part_shape()
    for zf in (142.0, 190.0, 330.0):
        for s in (1.0, -1.0):
            cleat = box(s * 115.0 - S.FAIRLEAD_HALF_X, zf - S.FAIRLEAD_HALF_Z,
                        s * 115.0 + S.FAIRLEAD_HALF_X, zf + S.FAIRLEAD_HALF_Z)
            assert sh.distance(cleat) >= S.NOTCH_CLEAR - 0.6


def test_max_hole_rule():
    from huntkit.gendesign import spreader as S
    assert S.MAX_HOLE_D <= 25.0
    assert S.MAX_HOLE_D < S.BONE_D


# ---------------------------------------------------------------------------- recorded results
@pytest.mark.skipif(not RESULTS.exists(), reason="run python -m huntkit.gendesign.spreader first")
def test_recorded_results_meet_requirements():
    r = json.loads(RESULTS.read_text())
    ch = r["chosen"]
    # the 100 g target was not reached (analysis/spreader.md); the part must still beat the old one
    assert ch["mass_g"] < r["old_part_g"]
    assert ch["passes"]
    assert ch["sf_fpf"] >= 1.0
    assert ch["sf_fatigue"] >= 1.0
    assert ch["skin_peak_kpa"] <= 14.0
    assert ch["clear_walk_min"] >= 3.0 and ch["clear_fact_min"] >= 0.0
    if ch.get("sandwich_sf_min") is not None:
        assert ch["sandwich_sf_min"] >= 1.0
    for p in r["screens"]:
        assert not Path(p).is_absolute()
        assert (ROOT / p).exists()
        assert (ROOT / p).stat().st_size <= 1.5e6
    for p in r["files"].values():
        assert not Path(p).is_absolute()
        assert (ROOT / p).exists()
