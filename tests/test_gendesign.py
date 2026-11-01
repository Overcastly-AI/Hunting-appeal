"""Tests for huntkit.gendesign: element/solver verification against closed form, SIMP benchmarks
(MBB, 3D cantilever), volume constraint, compliance history, watertight STL, plate rules, printables."""
import numpy as np
import pytest

from huntkit.gendesign import fem
from huntkit.gendesign.fem import Assembler, Grid, Solver, ke_h8, ke_q4
from huntkit.gendesign.simp import cantilever3d_problem, mbb_problem, run_simp


# ------------------------------------------------------------------ element / solver verification
def test_h8_q4_rank_and_symmetry():
    K = ke_h8(1.3, 210e3, 0.3)
    assert np.allclose(K, K.T)
    assert np.linalg.matrix_rank(K) == 24 - 6
    assert np.linalg.matrix_rank(ke_q4(1.0)) == 8 - 3


def test_q4_patch_uniform_tension():
    """Plane-stress strip under uniform end traction: exact uniform stress and E-modulus elongation."""
    E, nu, Lx, Ly, q = 1000.0, 0.3, 20, 5, 2.0
    g = Grid((Lx, Ly), 1.0)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    left = np.where(np.isclose(nc[:, 0], 0))[0]
    fixed[2 * left] = True
    fixed[2 * left[np.isclose(nc[left, 1], 0)] + 1] = True
    F = np.zeros(g.ndof)
    right = np.where(np.isclose(nc[:, 0], Lx))[0]
    w = np.where(np.isclose(nc[right, 1], 0) | np.isclose(nc[right, 1], Ly), 0.5, 1.0)
    F[2 * right] = q * w
    K = Assembler(g.edof, g.ndof, ke_q4(1.0, E, nu), fixed).assemble(np.ones(g.ne))
    u = Solver(nc, fixed).solve(K, F)
    assert u[2 * right].mean() == pytest.approx(q * Lx / E, rel=1e-6)


def test_h8_cantilever_vs_timoshenko_beam():
    """Voxel cantilever (64 x 8 x 8, clamped face, tip shear) vs Timoshenko beam deflection."""
    L, b, h, P, E, nu = 64, 8, 8, 1.0, 1000.0, 0.3
    g = Grid((L, b, h), 1.0)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    cl = np.where(np.isclose(nc[:, 0], 0))[0]
    for d in range(3):
        fixed[3 * cl + d] = True
    tip = np.where(np.isclose(nc[:, 0], L))[0]
    F = np.zeros(g.ndof)
    F[3 * tip + 2] = -P / len(tip)
    K = Assembler(g.edof, g.ndof, ke_h8(1.0, E, nu), fixed).assemble(np.ones(g.ne))
    u = Solver(nc, fixed, tol=1e-10, maxiter=2000).solve(K, F)
    I = b * h ** 3 / 12
    G = E / (2 * (1 + nu))
    w_beam = P * L ** 3 / (3 * E * I) + P * L / (5 / 6 * G * b * h)
    w_fe = -u[3 * tip + 2].mean()
    assert w_fe == pytest.approx(w_beam, rel=0.06)     # trilinear hex, 8 elements through the depth


# ------------------------------------------------------------------ SIMP benchmarks
@pytest.fixture(scope="module")
def mbb():
    pb = mbb_problem(60, 20, 0.5, 1.5)
    return pb, run_simp(pb, iters=100, beta_schedule=(0,))


def test_mbb_volume_and_compliance(mbb):
    pb, r = mbb
    assert r.history[-1]["volume"] == pytest.approx(0.5, abs=0.005)
    # Andreassen et al. 2011 (top88, 60x20, vf 0.5, rmin 1.5, density filter): c ~ 216-234 depending on
    # the filter variant; this implementation lands at ~219.
    assert 200 < r.compliance < 240


def test_mbb_compliance_monotone(mbb):
    _, r = mbb
    c = np.array([h["compliance"] for h in r.history])
    assert np.all(np.diff(c) <= 1e-3 * c[:-1])       # non-increasing (OC, fixed filter)
    assert c[-1] < 0.3 * c[0]


def test_mbb_classic_layout(mbb):
    """The classic MBB layout: solid top chord at the load, solid bottom chord at the support, and
    several internal holes (diagonal web members)."""
    from scipy import ndimage
    pb, r = mbb
    x = pb.grid.to_array(r.xPhys)            # (nelx, nely), y up
    nelx, nely = x.shape
    assert x[:3, -3:].mean() > 0.9            # top-left (load / symmetry line)
    assert x[-4:, :3].mean() > 0.8            # bottom-right (support)
    assert x[nelx // 2, -2:].mean() > 0.8 and x[nelx // 2, :2].mean() > 0.8    # top and bottom chords
    holes, n = ndimage.label(x < 0.5)
    sizes = ndimage.sum(np.ones_like(holes), holes, range(1, n + 1))
    assert (sizes > 10).sum() >= 3
    assert np.mean((x > 0.1) & (x < 0.9)) < 0.4      # density filter without projection leaves some grey


def test_cantilever3d_volume_and_decrease():
    pb = cantilever3d_problem(24, 6, 12, 0.15, 1.5)
    r = run_simp(pb, iters=25)
    assert r.history[-1]["volume"] == pytest.approx(0.15, abs=0.01)
    c = [h["compliance"] for h in r.history]
    assert c[-1] < 0.25 * c[0]
    x = pb.grid.to_array(r.xPhys)
    clamp = x[0]                                      # (ny, nz) at the clamped face
    nz = clamp.shape[1]
    # bending: material sits in the top/bottom fibres at the clamp, not at the neutral axis
    assert 0.5 * (clamp[:, :2].mean() + clamp[:, -2:].mean()) > clamp[:, nz // 2 - 1: nz // 2 + 1].mean()


# ------------------------------------------------------------------ surfaces / printables
def test_marching_cubes_boolean_watertight(tmp_path):
    import trimesh
    from huntkit.gendesign import surface
    n = 24
    idx = np.indices((n, n, n)).astype(float) - n / 2 + 0.5
    field = (np.linalg.norm(idx, axis=0) < 7).astype(float)
    m = surface.field_to_mesh(field, 1.0, (0, 0, 0))
    assert m.is_watertight
    sleeve = surface.cylinder((12, 12, 0), (0, 0, 1), 24, 4.0)
    bore = surface.cylinder((12, 12, -5), (0, 0, 1), 40, 2.5)
    out = surface.boolean_body(m, [sleeve], [bore])
    assert out.is_watertight and out.volume > 0
    files = surface.export(out, tmp_path / "part")
    back = trimesh.load(files[0])
    assert back.is_watertight


def test_printables_watertight_and_rack_capacity():
    from huntkit.gendesign.printables import rack_check, spring_pawl, toothed_rack, webbing_guide
    for f in (toothed_rack, spring_pawl, webbing_guide):
        m, _ = f()
        assert m.is_watertight and m.volume > 0
    # geometry.yaml lock method: 2 teeth x 20 mm x 2 mm root; 1334 N x 1.5 required
    assert rack_check("pa12_cf_fdm_paht")["sf_over_req"] > 1.0
    assert rack_check("alsi10mg_slm")["sf_over_req"] > 3.0


def test_min_web_measure():
    from huntkit.gendesign.plate import min_web_mm
    holes = np.zeros((60, 40), bool)
    holes[10:25, 10:30] = True
    holes[33:50, 10:30] = True                 # 8-pixel web between the cut-outs
    assert min_web_mm(holes, 1.0) == pytest.approx(9.0, abs=1.5)


def test_slm_and_fdm_material_records():
    from huntkit.fea.materials_bridge import get_material
    ti = get_material("ti_6al_4v_slm")
    assert ti.get("fatigue_limit_asbuilt_hip_mpa") < ti.get("fatigue_limit_machined_hip_mpa")
    assert ti.get("yield_strength_design_mpa") < get_material("ti_6al_4v").get("yield_strength_mpa")
    pa = get_material("pa12_cf_fdm_paht")
    assert pa.get("tensile_strength_z_mpa") < pa.get("tensile_strength_xy_mpa")
