"""Team D (SERVICE) frame competition: failure rules, fatigue derivation, voxel stress vs beam theory, results.

The voxel solver itself is verified in tests/test_frame_topopt.py (cantilever, torsion); here the stress
recovery used by frame_comp_d (unit-E solve, element_stress with E = 1) is checked against M c / I.
"""
import json

import numpy as np
import pytest

from huntkit.gendesign import frame_comp_d as D
from huntkit.gendesign import frame_topopt as ft
from huntkit.gendesign.fem import Grid, ke_h8


def test_basquin_matches_avanzini_table():
    # Avanzini 2022 Tab. 2: smooth, 27.7 MPa at 1e6 from Smax = 44 N^-0.034
    assert D.basquin_smax(1e6) == pytest.approx(27.7, abs=0.3)   # A, B are rounded in the table
    assert D.fatigue_lower_bound(1e5) == pytest.approx(29.75 / np.sqrt(1.84), rel=1e-3)
    assert D.MATERIALS["pa12_mjf"]["fat"] == pytest.approx(21.93 / 48, abs=2e-3)


def test_iso_fi_uniaxial_and_shear():
    S = np.array([[40.0, 0, 0, 0, 0, 0], [0, 0, 0, 10.0, 0, 0]])
    fi = D.fi_iso(S, 50.0, 0.8)
    assert fi[0] == pytest.approx(1.0)
    assert fi[1] == pytest.approx(np.sqrt(3) * 10 / 40)


def test_ortho_fi_directions():
    m = D.MATERIALS["pa12cf_sls"]
    S = np.zeros((3, 6))
    S[0, 2] = 0.8 * m["X"]          # along the stays (recoater)
    S[1, 0] = 0.8 * m["Y"]          # across, in plane
    S[2, 1] = 0.8 * m["Z"]          # through the build
    fi = D.fi_ortho(S, m["X"], m["Y"], m["Z"], m["S"], m["knock"])
    assert fi == pytest.approx([1.0, 1.0, 1.0])


def test_paht_rule_matches_release_layer_rule():
    S = np.array([[30.0, 5.0, 20.0, 3.0, 2.0, 1.0]])
    m = D.MATERIALS["paht_fdm"]
    ref = ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, 88.0, 47.0, 0.8)
    assert D.fi_material(S, m) == pytest.approx(ref)


def test_unit_E_stress_recovery_vs_beam_theory():
    """Cantilever 120 x 12 x 12, tip load: bending stress at mid-span from a unit-E solve (as solve_fields)."""
    L, a, P, h = 120.0, 12.0, 100.0, 1.5
    g = Grid((int(L / h), int(a / h), int(a / h)), h)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    root = np.where(np.isclose(nc[:, 0], 0))[0]
    for d in range(3):
        fixed[3 * root + d] = True
    tip = np.where(np.isclose(nc[:, 0], L))[0]
    F = np.zeros((g.ndof, 1))
    F[3 * tip + 2, 0] = -P / tip.size
    solid = np.ones(g.ne, bool)
    rs = ft.ReducedSystem(g, solid, fixed, ke_h8(g.h, 1.0, ft.NU))
    U = rs.solve(rs.assemble(np.ones(g.ne)), F)
    _, S = ft.element_stress(g, U[:, 0], solid, 1.0)
    c = g.elem_centers()
    x0 = 60.0
    sel = np.isclose(c[:, 0], x0 + h / 2) & np.isclose(c[:, 2], a - h / 2)
    sxx = np.abs(S[sel, 0]).mean()
    M = P * (L - x0 - h / 2)
    s_th = M * (a / 2 - h / 2) / (a ** 4 / 12)       # at the element centre fibre
    assert sxx == pytest.approx(s_th, rel=0.08)


def test_cost_and_result_schema():
    c = D.service_cost(900.0, "pa11_mjf")
    assert c["1"] > c["100"]
    p = D.TEAM_DIR / "result.json"
    if p.exists():
        r = json.loads(p.read_text())
        keys = {"team", "concept_name", "one_line", "frame_g", "frame_plus_spreader_g", "pack_mass_corrie_b2_M_g",
                "passes_rev_c", "worst_strength_margin", "worst_fatigue_margin", "worst_joint_margin",
                "governing_case", "torsion_stiffness_vs_today", "print_hours", "printer", "cost_usd", "build_hours",
                "skill_level", "looks_generative", "patents_checked", "governing_assumptions", "coupon_tests"}
        assert set(r) == keys
        assert r["pack_mass_corrie_b2_M_g"] == pytest.approx(3964.5 - (1225.0 - r["frame_plus_spreader_g"]), abs=0.6)
