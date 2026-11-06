"""Whole-frame generative design (huntkit.gendesign.frame_topopt) + HA-LS-1 rev B meat-strap case.

Solver verification against closed forms (voxel cantilever, square-bar torsion, rod + voxel in parallel),
reduced direct solver vs the reference assembler, domain symmetry, load-set equilibrium, FDM layer
failure index, and the viz3d generative-frame option.
"""
import numpy as np
import pytest

from huntkit.gendesign import frame_topopt as ft
from huntkit.gendesign.fem import Assembler, Grid, ke_h8


def _bar_problem(L=120, a=12, h=2.0):
    g = Grid((int(L / h), int(a / h), int(a / h)), h)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    root = np.where(np.isclose(nc[:, 0], 0))[0]
    for d in range(3):
        fixed[3 * root + d] = True
    tip = np.where(np.isclose(nc[:, 0], L))[0]
    return g, nc, fixed, tip


def test_voxel_cantilever_vs_timoshenko():
    E, nu, L, a, P = 1000.0, 0.3, 120.0, 12.0, 1.0
    g, nc, fixed, tip = _bar_problem(L, a, 1.5)
    F = np.zeros((g.ndof, 1))
    F[3 * tip + 2, 0] = -P / tip.size
    rs = ft.ReducedSystem(g, np.ones(g.ne, bool), fixed, ke_h8(g.h, E, nu))
    U = rs.solve(rs.assemble(np.ones(g.ne)), F)
    w = -U[3 * tip + 2, 0].mean()
    I = a ** 4 / 12
    G = E / (2 * (1 + nu))
    w_th = P * L ** 3 / (3 * E * I) + P * L / (5 / 6 * G * a * a)
    assert w == pytest.approx(w_th, rel=0.06)        # H8 voxels are slightly stiff in bending


def test_voxel_square_bar_torsion_vs_saint_venant():
    E, nu, L, a = 1000.0, 0.3, 120.0, 12.0
    g, nc, fixed, tip = _bar_problem(L, a, 1.5)
    T = 100.0
    c = np.array([L, a / 2, a / 2])
    r = nc[tip] - c
    F = np.zeros((g.ndof, 1))
    # torque about x as nodal forces f = T r_perp / sum|r_perp|^2
    rp = np.c_[np.zeros(len(r)), -r[:, 2], r[:, 1]]
    f = T * rp / (r[:, 1] ** 2 + r[:, 2] ** 2).sum()
    for d in range(3):
        F[3 * tip + d, 0] = f[:, d]
    rs = ft.ReducedSystem(g, np.ones(g.ne, bool), fixed, ke_h8(g.h, E, nu))
    U = rs.solve(rs.assemble(np.ones(g.ne)), F)
    u = U[:, 0].reshape(-1, 3)[tip]
    theta = np.mean((r[:, 1] * u[:, 2] - r[:, 2] * u[:, 1]) / np.maximum(r[:, 1] ** 2 + r[:, 2] ** 2, 1e-9))
    J = 0.1406 * a ** 4                               # Saint-Venant square section
    G = E / (2 * (1 + nu))
    assert theta == pytest.approx(T * L / (G * J), rel=0.08)


def test_reduced_solver_matches_reference_assembler():
    g = Grid((6, 3, 4), 2.0)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    fixed[np.repeat(np.isclose(nc[:, 0], 0), 3)] = True
    rng = np.random.default_rng(1)
    E = 0.1 + rng.random(g.ne)
    F = rng.normal(size=(g.ndof, 2)); F[fixed] = 0
    KE = ke_h8(g.h, 1.0, 0.3)
    rs = ft.ReducedSystem(g, np.ones(g.ne, bool), fixed, KE)
    U = rs.solve(rs.assemble(E), F)
    K = Assembler(g.edof, g.ndof, KE, fixed).assemble(E)
    import scipy.sparse.linalg as spla
    U2 = spla.spsolve(K.tocsc(), F)
    assert np.allclose(U, U2, atol=1e-8 * np.abs(U2).max())


def test_rod_in_parallel_with_voxels():
    """A rod along a voxel bar adds its EA in parallel: axial stiffness = E A_bar + E_r A_r."""
    E, L, a, h = 1000.0, 60.0, 4.0, 2.0
    g = Grid((int(L / h), int(a / h), int(a / h)), h)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    root = np.isclose(nc[:, 0], 0)
    fixed[3 * np.where(root)[0]] = True                 # ux = 0 only (free lateral contraction) ...
    k0 = np.where(root & np.isclose(nc[:, 1], 0) & np.isclose(nc[:, 2], 0))[0][0]
    fixed[3 * k0 + 1] = fixed[3 * k0 + 2] = True      # ... + rigid-body restraint
    k1 = np.where(root & np.isclose(nc[:, 1], a) & np.isclose(nc[:, 2], 0))[0][0]
    fixed[3 * k1 + 2] = True
    k2 = np.where(root & np.isclose(nc[:, 1], 0) & np.isclose(nc[:, 2], a))[0][0]
    fixed[3 * k2 + 1] = True
    tip = np.where(np.isclose(nc[:, 0], L))[0]
    # consistent nodal forces of a uniform end stress (bilinear face: corner 1, edge 2, interior 4 shares)
    edge = lambda v: np.isclose(v, 0) | np.isclose(v, a)           # noqa: E731
    wgt = (2.0 - edge(nc[tip, 1])) * (2.0 - edge(nc[tip, 2]))
    rod = ft.Rod(np.array([0.0, a / 2, a / 2]), np.array([L, a / 2, a / 2]), area=2.0, E_ratio=50.0)
    centre = tip[np.isclose(nc[tip, 1], a / 2) & np.isclose(nc[tip, 2], a / 2)][0]
    for rods, EA in ((None, E * a * a), ([rod], E * a * a + 50 * E * 2.0)):
        Ptot = 100.0
        F = np.zeros((g.ndof, 1))
        F[3 * tip, 0] = Ptot * (E * a * a / EA) * wgt / wgt.sum()     # matrix share, uniform stress
        F[3 * centre, 0] += Ptot * (1 - E * a * a / EA)             # rod share at the rod end node
        rs = ft.ReducedSystem(g, np.ones(g.ne, bool), fixed, ke_h8(h, E, 0.0), rods=[
            ft.Rod(r.p0, r.p1, r.area, r.E_ratio * E, r.name) for r in rods] if rods else None)
        U = rs.solve(rs.assemble(np.ones(g.ne)), F)
        assert U[3 * tip, 0].mean() == pytest.approx(100.0 * L / EA, rel=0.03)


@pytest.fixture(scope="module")
def dom():
    return ft.build_domain(8.0)


def test_domain_symmetry_and_envelope(dom):
    m = dom.mirror
    assert np.array_equal(m[m], np.arange(dom.grid.ne))
    assert np.array_equal(dom.passive_solid, dom.passive_solid[m])
    assert np.array_equal(dom.passive_void, dom.passive_void[m])
    c = dom.grid.elem_centers()
    # nothing solid inside the bag or the crown-leg bores or the spine channel
    assert not (dom.passive_solid & (c[:, 1] > dom.env.y_hi(c[:, 2]) + 6.5)).any()
    for k in ("bore_L", "bore_R", "spine_channel"):
        assert not (dom.passive_solid & dom.masks[k]).any()
    assert (dom.passive_void & dom.masks["bore_R"]).sum() == dom.masks["bore_R"].sum()


def test_meat_strap_case_equilibrium_and_placement():
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import MEAT, ls1_cases
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19)
    # rev B table (rev C adds the hood + guys on the crown bar: tests/test_load_standard_rev_c.py)
    c = next(x for x in ls1_cases(rev="B") if x.name == "meat_straps")
    assert c.placement == "meat_straps" and c.cg_aft_mm == MEAT["meat_straps"]["cg_aft_mm"]
    loads = c._loads(fm)
    P = c.W
    F = sum(np.asarray(v[:3]) for v in loads.values())
    assert F == pytest.approx([0, 0, -P], abs=1e-6 * P)
    # the horizontal strap / pressure couple carries the overturning moment of the CG offset: sum z Fy = P e
    Mh = sum(fm["nodes"][n][2] * v[1] for n, v in loads.items())
    assert Mh == pytest.approx(P * c.cg_aft_mm, rel=1e-6)
    # no shelf in rev B or rev C
    assert all(x.placement != "meat_shelf" for x in ls1_cases(rev="B") + ls1_cases())


def test_strap_levels_follow_geometry():
    from huntkit.fea.pack5200 import strap_levels
    lv = strap_levels({"hard_points": {"meat_anchor_z190_R": [1, 2, 190.0], "meat_anchor_z330_R": [1, 2, 330.0],
                                       "meat_anchor_z520_R": [1, 2, 520.0], "bag_anchor_low_R": [1, 2, 60.0]}})
    assert lv == {"strap_bottom": 60.0, "strap_lumbar": 190.0, "strap_mid": 330.0, "strap_upper": 520.0}


def test_loadsets_balance_with_hip_clamp():
    sets = ft.beam_loadsets(torsos=(19,), log=None)
    by = {s.case: s for s in sets}
    # inertia-relief (set-down) and hipbelt-off sets are self-equilibrated on the fixed frame; the others
    # are out of balance by exactly the hipbelt reaction the clamp takes (80 % of the vertical load)
    assert by["single_stay_setdown"].resid < 0.05
    assert by["hipbelt_off_abuse"].resid < 1.0
    W = 68 * 9.80665
    assert by["static_carry"].resid == pytest.approx(0.8 * W, rel=0.05)


def test_layer_failure_index_uniaxial():
    env_s = np.array([[0.0, 10.0, 0.0]])
    env_t = np.zeros((1, 3))
    fi_flat = ft.layer_failure_index(env_s, env_t, 1, 100.0, 50.0, 1.0)     # stress normal to the layers
    fi_edge = ft.layer_failure_index(env_s, env_t, 0, 100.0, 50.0, 1.0)     # stress in the layer plane
    assert fi_flat[0] == pytest.approx(10 / 50) and fi_edge[0] == pytest.approx(10 / 100)


def test_simp_symmetric_on_coarse_frame(dom):
    sets = [s for s in ft.beam_loadsets(torsos=(19,), log=None) if s.case in ("drop_2p5g", "side_hill_torsion")]
    F, fx = ft.assemble_loads(dom, sets)
    o = ft.simp_frame(dom, F, fx, 0.06, iters=4, beta_schedule=(1,))
    assert np.allclose(o.xPhys, o.xPhys[dom.mirror], atol=1e-9)
    assert o.history[-1]["compliance"] < o.history[0]["compliance"]
    assert o.xPhys[dom.design()].mean() == pytest.approx(0.06, abs=0.01)


def test_viz_generative_frame_option(tmp_path):
    trimesh = pytest.importorskip("trimesh")
    from huntkit.viz3d.model import build_pack
    from huntkit.viz3d.params import load_params
    box = trimesh.creation.box((200, 30, 500)); box.apply_translation([0, -20, 260])
    box.export(tmp_path / "genframe_assembled.stl")
    p = load_params(overrides={"fea": {"enabled": False}, "frame_type": "generative",
                               "generative_frame_dir": str(tmp_path)})
    pk = build_pack(p)
    names = {q.name for q in pk.parts}
    assert "frame_generative" in names and "frame_stays" not in names and "lumbar_plate" not in names
    assert any(n.startswith("crown@") for n in names)       # carbon crown kept
    assert pk.metrics["frame_type"] == "generative"
    assert pk.part("frame_generative").mesh.metadata["uv"].shape[0] == len(pk.part("frame_generative").mesh.vertices)


def test_frame_simp_matches_reference_simp_on_3d_cantilever():
    """Benchmark: the whole-frame SIMP (reduced direct solver, mirror-free here) reaches the same optimum
    compliance as the validated huntkit.gendesign.simp.run_simp on the 3D cantilever benchmark."""
    from huntkit.gendesign.simp import cantilever3d_problem, run_simp
    pb = cantilever3d_problem(24, 6, 12, volfrac=0.15, rmin=1.5)
    ref = run_simp(pb, iters=40, beta_schedule=(1, 2, 4), beta_every=12)
    dom = ft.Domain(pb.grid, None, np.zeros(pb.grid.ne, bool), np.zeros(pb.grid.ne, bool),
                    np.arange(pb.grid.ne))
    o = ft.simp_frame(dom, pb.loads, pb.fixed, 0.15, iters=40, rmin_vox=1.5, beta_schedule=(1, 2, 4),
                      beta_every=12, move=0.2)
    c_ref = ref.history[-1]["compliance"]
    c_new = o.history[-1]["compliance"]
    assert c_new == pytest.approx(c_ref, rel=0.10)
    assert o.history[-1]["volume"] == pytest.approx(0.15, abs=0.01)
