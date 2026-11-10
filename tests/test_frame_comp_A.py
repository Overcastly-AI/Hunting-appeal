"""Team A (MONO) printed-frame competition: geometry, resizing rule, dry joint, allowables and result file.

The voxel solver itself is verified against closed forms in tests/test_frame_topopt.py (Timoshenko cantilever,
Saint-Venant torsion, rod-in-parallel); test_voxel_cantilever_closed_form below re-checks the path this module uses.
"""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import frame_comp_A as A

KEYS = {"team", "concept_name", "one_line", "frame_g", "frame_plus_spreader_g", "pack_mass_corrie_b2_M_g",
        "passes_rev_c", "worst_strength_margin", "worst_fatigue_margin", "worst_joint_margin", "governing_case",
        "torsion_stiffness_vs_today", "print_hours", "printer", "cost_usd", "build_hours", "skill_level",
        "looks_generative", "patents_checked", "governing_assumptions", "coupon_tests"}


def test_default_body_is_todays_body():
    """With every scale 1.05 and the 4.41 mm wall the parametric SDF equals the released frame_sdf."""
    from huntkit.gendesign.spreader_layout import frame_sdf_layout
    rng = np.random.default_rng(1)
    pts = np.c_[rng.uniform(-150, 150, 4000), rng.uniform(-60, 40, 4000), rng.uniform(-5, 545, 4000)]
    a = A.body_sdf(pts, A.Body())
    b = frame_sdf_layout(pts, None, 1.05)
    inside_a, inside_b = a <= 0, b <= 0
    assert (inside_a == inside_b).mean() > 0.999
    near = np.abs(b) < 20
    assert np.allclose(a[near], b[near], atol=1e-6)


def test_stay_radius_floors():
    b = A.Body(low=0.9, sleeve=0.9, top=0.9, sleeve_w=3.6)
    z = np.array([100.0, 300.0, 500.0])
    r = A.stay_radius(z, b)
    assert r[1] == pytest.approx(max(13.2 * 0.9, 9.0 + 3.6), rel=0.02)
    assert r[2] >= 16.0 * 0.9 - 1e-9
    assert r[0] == pytest.approx(np.interp(100.0, [40, 150], [9.0, 8.5]) * 0.9)


def test_resize_cube_root_rule_and_limits():
    b = A.Body()
    nb = A.resize(b, {"low": 1.0 * 1.1, "branch": 0.5, "foot": 0.01}, target=1.0)
    assert nb.low == pytest.approx(1.05 * 1.1 ** (1 / 3))           # bending: r ~ u^(1/3)
    assert nb.branch == pytest.approx(1.05 * 0.9)                   # step limit 10 %
    assert nb.foot == pytest.approx(1.05 * 0.9)
    for _ in range(20):
        nb = A.resize(nb, {"foot": 0.01, "branch": 0.01}, target=1.0)
    assert nb.foot == pytest.approx(A.MIN_SCALE["foot"])            # size floor holds
    assert nb.branch == pytest.approx(A.MIN_SCALE["branch"])


def test_layer_failure_index_uses_z_across_layers():
    m = A.MATS["paht_rec"]
    S = np.zeros((3, 6))
    S[0, 0] = 10.0          # sigma_x, in the layer plane for normal y
    S[1, 1] = 10.0          # sigma_y, across the layers
    S[2, 3] = 5.0           # tau_xy: interlayer shear for normal y
    fi = A.fi_layer(S, 1, m)
    assert fi[0] == pytest.approx(10 / (0.8 * 88))
    assert fi[1] == pytest.approx(10 / (0.8 * 47))
    assert fi[2] == pytest.approx(5 / (0.8 * 0.6 * 47))


def test_dry_joint_capacity_hand_calc():
    m = A.MATS["paht_rec"]
    c = A.joint_capacity(m)
    ring = math.pi / 4 * (12.0 ** 2 - 5.5 ** 2)
    assert c["bearing_n"] == pytest.approx(ring * 0.8 * 88)
    assert c["shear_out_n"] == pytest.approx(2 * 35 * 12 * 0.6 * 0.8 * 47)
    assert c["bolt_n"] == pytest.approx(14.2 * 450)
    assert c["tension_n"] == pytest.approx(min(c["bearing_n"], c["shear_out_n"], c["bolt_n"]))
    cf = A.joint_capacity(m, fatigue=True)
    assert cf["bearing_n"] == pytest.approx(0.3 * c["bearing_n"])


def test_frame_mass_bookkeeping():
    m = A.MATS["paht_rec"]
    r = A.frame_mass(A.TODAY["body_g"], m)
    assert r["frame_g"] == pytest.approx(1063.0 + r["joint_bosses_g"] + r["joint_hw_delta_g"])
    assert r["pack_corrie_b2_M_g"] == pytest.approx(3964.5 - (1225.0 - r["frame_plus_spreader_g"]), abs=0.2)


def test_materials_cited_values():
    """Allowables match the TDS numbers quoted in docs/research/frame_comp_A.md."""
    p, q = A.MATS["paht_rec"], A.MATS["ppa"]
    assert (p.s_xy, p.s_z, p.rho, p.fat) == (88, 47, 1060, 0.30)
    assert (q.s_xy, q.rho, q.E_xy) == (168, 1250, 11800)
    assert q.knock == pytest.approx(122 / 168, abs=0.01)


def test_voxel_cantilever_closed_form():
    """Solid voxel cantilever (the frame_topopt kernel this module uses) vs Euler-Bernoulli + shear, within 10 %."""
    from huntkit.gendesign import frame_topopt as ft
    from huntkit.gendesign.fem import Grid
    h, L, b, d = 2.0, 120.0, 12.0, 12.0
    g = Grid((int(L / h), int(b / h), int(d / h)), h, np.zeros(3))
    solid = np.ones(g.ne, bool)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    root = np.where(nc[:, 0] < 1e-6)[0]
    for k in range(3):
        fixed[3 * root + k] = True
    tip = np.where(np.abs(nc[:, 0] - L) < 1e-6)[0]
    F = np.zeros((g.ndof, 1))
    P = 100.0
    F[3 * tip + 2, 0] = -P / tip.size
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(h, 1.0, ft.NU))
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    E = 3860.0
    U = rs.solve(K, F) / E
    w = -U[3 * tip + 2, 0].mean()
    I = b * d ** 3 / 12
    G = E / (2 * (1 + ft.NU))
    w_ref = P * L ** 3 / (3 * E * I) + P * L / (5 / 6 * G * b * d)
    assert w == pytest.approx(w_ref, rel=0.10)


def test_result_json_schema():
    if not A.RESULT_JSON.exists():
        pytest.skip("result.json not written yet")
    r = json.loads(A.RESULT_JSON.read_text())
    assert set(r) == KEYS
    assert r["team"] == "A"
    assert set(r["cost_usd"]) == {"1", "10", "100"}
    assert r["pack_mass_corrie_b2_M_g"] == pytest.approx(3964.5 - (1225 - r["frame_plus_spreader_g"]), abs=0.6)
    if r["passes_rev_c"]:
        assert min(r["worst_strength_margin"], r["worst_fatigue_margin"], r["worst_joint_margin"]) >= 1.0
