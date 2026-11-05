"""huntkit.clothsim: gradient checks and analytic validation (docs/CONTRACTS.md section 7).

Validation targets (designs/pack_5200/analysis/cloth_sim.md section 2):
- inflated closed cylinder: hoop p r, axial p r / 2, longitudinal seam line force p r, cap seam p r / 2
- hanging sheet: catenary sag, horizontal tension w a, shape
- flat-pattern area: mesher conserves the pattern area; a draped sheet keeps its area
"""
import math

import numpy as np
import pytest

from huntkit.clothsim import validation as V
from huntkit.clothsim.assemble import PieceSpec, assemble, densify
from huntkit.clothsim.mesh import triangulate_loop
from huntkit.clothsim.model import (Bending, Cable, Cables, DeadLoad, FieldContact, GapField, Gravity, Membrane,
                                    Pressure, Sim)


def _box_mesh(h=30.0):
    """Small closed box (5 sewn faces + floor) for gradient checks."""
    fab = V.iso_fabric(k=150.0, shear=3.0, bending=0.2, c=0.05)
    W, D, H = 120.0, 90.0, 100.0

    def face(name, o, u, v, a, b):
        o, u, v = (np.asarray(t, float) for t in (o, u, v))

        def m3(fl):
            return o + np.outer(fl[:, 0], u) + np.outer(fl[:, 1], v)
        c = np.array([[0, 0], [a, 0], [a, b], [0, b]], float)
        edges = [(f"e{i}", densify(np.array([c[i], c[(i + 1) % 4]]), 2.0), None) for i in range(4)]
        edges = [(n, fl, m3(fl)) for n, fl, _ in edges]
        return PieceSpec(name, edges, m3, fab, grain_deg=20.0)
    specs = [face("bottom", (0, 0, 0), (1, 0, 0), (0, 1, 0), W, D), face("top", (0, 0, H), (1, 0, 0), (0, 1, 0), W, D),
             face("front", (0, 0, 0), (1, 0, 0), (0, 0, 1), W, H), face("back", (0, D, 0), (1, 0, 0), (0, 0, 1), W, H),
             face("left", (0, 0, 0), (0, 1, 0), (0, 0, 1), D, H), face("right", (W, 0, 0), (0, 1, 0), (0, 0, 1), D, H)]
    mesh, diag = assemble(specs, h, tol=0.5, outward_ref=np.array([W / 2, D / 2, H / 2]))
    return mesh, diag


def _fd_check(term, x, eps=1e-5, n=12, seed=0):
    rng = np.random.default_rng(seed)
    E0, g, _ = term(x, False)
    errs = []
    for _ in range(n):
        i, d = rng.integers(len(x)), rng.integers(3)
        xp, xm = x.copy(), x.copy()
        xp[i, d] += eps
        xm[i, d] -= eps
        fd = (term(xp, False)[0] - term(xm, False)[0]) / (2 * eps)
        errs.append(abs(fd - g[i, d]) / max(1e-6, abs(fd), abs(g[i, d]), 1e-3 * np.abs(g).max()))
    return max(errs)


def test_box_is_closed_and_gradients_are_exact():
    mesh, diag = _box_mesh()
    assert len(diag["free_segments"]) == 0
    assert all(v == 0 for v in diag["missing_boundary_edges"].values())
    rng = np.random.default_rng(3)
    x = mesh.X0 * 1.02 + rng.normal(0, 1.5, mesh.X0.shape)
    pr = Pressure(mesh.tris, p0=2e-3, rho_g=0.8 * 9.81e-6, z_ref=120.0)
    assert pr.volume(mesh.X0) == pytest.approx(120 * 90 * 100, rel=1e-9)
    n0 = int(np.argmin(mesh.X0[:, 2]))
    cab = Cables([Cable("e", np.array([-1, n0, -1]), np.array([[-50, 0, 200], [np.nan] * 3, [200, 0, 200.0]]), 1e4, 100.0),
                  Cable("c", np.array([-1, n0]), np.array([[0, 0, 300.0], [np.nan] * 3]), 1e4, 1.0, T_const=40.0)])
    P = np.array([[a, b, -5.0] for a in np.linspace(-20, 140, 40) for b in np.linspace(-20, 110, 30)])
    fld = GapField.from_samples(P, np.tile([0, 0, 1.0], (len(P), 1)), spacing=4.0)
    xc = x.copy()
    xc[:, 2] -= 3.0                                    # push the floor into the plane
    terms = [Membrane(mesh), Bending(mesh), pr, Gravity(mesh.mass), cab,
             DeadLoad(np.array([1, 2]), np.array([[0, 1.0, -2.0], [3.0, 0, 0]]))]
    for t in terms:
        assert _fd_check(t, x) < 2e-4, t.name
    fc = FieldContact(fld, kc=30.0, clearance=1.0)
    assert _fd_check(fc, xc, eps=1e-6) < 2e-3


def test_triangulation_conserves_pattern_area():
    # concave pattern piece with a dart notch
    loop = np.array([[0, 0], [300, 0], [300, 250], [170, 250], [150, 140], [130, 250], [0, 250]], float)
    pts = densify(np.vstack([loop, loop[:1]]), 15.0)[:-1]
    t = triangulate_loop(pts, 20.0)
    a = t["xy"][t["tris"]]
    area = 0.5 * np.abs((a[:, 1, 0] - a[:, 0, 0]) * (a[:, 2, 1] - a[:, 0, 1])
                        - (a[:, 1, 1] - a[:, 0, 1]) * (a[:, 2, 0] - a[:, 0, 0]))
    assert t["missing_boundary_edges"] == 0
    assert area.sum() == pytest.approx(t["polygon"].area, rel=1e-9)


def test_inflated_cylinder_hoop_axial_and_seam_forces():
    r = V.cylinder(R=100.0, L=500.0, p=0.005, h=20.0)
    assert r["info"].converged
    assert r["free_segments"] == 0
    assert r["hoop"] == pytest.approx(r["hoop_exact"], rel=0.01)
    assert r["axial"] == pytest.approx(r["axial_exact"], rel=0.01)
    assert r["seam_long"] == pytest.approx(r["hoop_exact"], rel=0.03)      # longitudinal seam carries p r
    assert r["seam_cap"] == pytest.approx(r["axial_exact"], rel=0.03)      # end seam carries p r / 2
    assert r["r_eq"] == pytest.approx(r["r_exact_linear"], rel=0.002)       # membrane strain p R / k


def test_hanging_sheet_is_a_catenary():
    r = V.catenary()
    assert r["sag"] == pytest.approx(r["sag_exact"], rel=0.01)
    assert r["H"] == pytest.approx(r["H_exact"], rel=0.02)
    assert r["V"] == pytest.approx(r["V_exact"], rel=0.01)
    assert r["shape_err_mm"] < 1.0


def test_draped_sheet_keeps_its_area():
    r = V.drape_area()
    assert r["info"].converged
    assert r["flat_area"] == pytest.approx(r["polygon_area"], rel=1e-9)
    assert r["area_3d"] == pytest.approx(r["flat_area"], rel=0.01)
    assert r["sag"] > 20.0


@pytest.mark.skipif(not __import__("os").environ.get("CLOTHSIM_FULL"), reason="full bag run (~1 min after the ~30 s pattern cache); set CLOTHSIM_FULL=1")
def test_pack5200_bag_is_sewn_closed_and_inflates_near_design_volume():
    from huntkit.clothsim.pack import PackModel, load_scenario, run_case
    scen = load_scenario()
    pm = PackModel(scen, verbose=False)
    assert len(pm.diag["free_segments"]) == 0
    assert all(v == 0 for v in pm.diag["missing_boundary_edges"].values())
    assert pm.mesh.flat_area() == pytest.approx(sum(p.meta["polygon_area"] for p in pm.mesh.pieces), rel=1e-6)
    x, sim, infos = run_case(pm, {"p0_kpa": 0.5, "wraps": False})
    V = sim.term("gas").volume(x) / 1e6
    assert 80.0 < V < 92.0
