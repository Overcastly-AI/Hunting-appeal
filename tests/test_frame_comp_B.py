"""Team B (SEG) frame competition checks: closed-form joint mechanics, FI rule parity, result schema."""
import json

import numpy as np
import pytest

from huntkit.gendesign import frame_comp_B as B
from huntkit.gendesign import frame_topopt as ft

KEYS = {"team", "concept_name", "one_line", "frame_g", "frame_plus_spreader_g", "pack_mass_corrie_b2_M_g",
        "passes_rev_c", "worst_strength_margin", "worst_fatigue_margin", "worst_joint_margin", "governing_case",
        "torsion_stiffness_vs_today", "print_hours", "printer", "cost_usd", "build_hours", "skill_level",
        "looks_generative", "patents_checked", "governing_assumptions", "coupon_tests"}

GEOM = {"x": [-128.0, -86.0], "y": [-18.0, 10.0]}


def test_layer_terms_match_shared_rule():
    rng = np.random.default_rng(1)
    S = rng.normal(0, 20, (500, 6))
    for a in range(3):
        mine = B.layer_terms(S, a).max(axis=1)
        ref = ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), a, B.S_XY, B.S_Z, B.KNOCK)
        assert np.allclose(mine, ref)


def test_bolt_group_pure_moment_closed_form():
    """Two rows of n bolts a lever L apart under a pure Mx: each tension-row bolt carries Mx / (n L)."""
    j = B.FlangeJoint(n_row=2, prying=1.0)
    xy = j.bolt_xy(GEOM)
    L = j.lever(GEOM)
    row = {"N": 0.0, "Mx": 50_000.0, "My": 0.0}
    assert B.bolt_tension(row, xy, 1.0) == pytest.approx(50_000.0 / (2 * L), rel=1e-9)
    row["N"] = 400.0                      # + uniform share of a tensile N
    assert B.bolt_tension(row, xy, 1.0) == pytest.approx(50_000.0 / (2 * L) + 100.0, rel=1e-9)


def test_aft_row_stays_inside_bag_envelope_and_clear_of_bore():
    j = B.FlangeJoint(n_row=2)
    xy = j.bolt_xy(GEOM)
    assert xy[:, 1].max() + j.boss_d / 2 <= j.y_env + 1e-9
    env = ft.load_envelope()
    c = np.array([-env.top_pt[0], env.sleeve_y(B.Z_CUT)])
    lig = np.linalg.norm(xy - c, axis=1) - 9.0 - 2.65           # bore R 9, M5 clearance hole R 2.65
    assert lig.min() >= 2.6                                        # >= insert min wall


def test_bolt_mass_closed_form():
    v = np.pi / 4 * 4.5 ** 2 * 30 + np.pi / 4 * 8.5 ** 2 * 5
    assert B.bolt_mass_g(30.0) == pytest.approx(v * 4.43 / 1000)


def test_upper_segment_fits_h2s_bed():
    assert (ft.Z_TOP - B.Z_CUT) + B.FlangeJoint().t_boss <= 340.0     # H2S 340 x 320 x 340 mm


def test_result_json_schema_and_pack_mass():
    p = B.TEAM_DIR / "result.json"
    if not p.exists():
        pytest.skip("run python -m huntkit.gendesign.frame_comp_B first")
    r = json.loads(p.read_text())
    assert set(r) == KEYS
    assert r["pack_mass_corrie_b2_M_g"] == pytest.approx(3964.5 - (1225.0 - r["frame_plus_spreader_g"]), abs=0.2)
    assert set(r["cost_usd"]) == {"1", "10", "100"}
    assert r["passes_rev_c"] == (min(r["worst_strength_margin"], r["worst_fatigue_margin"],
                                     r["worst_joint_margin"]) >= 1.0)
