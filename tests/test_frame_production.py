"""Production printed frame: pawl bushing, segment joint, meat barrier, heat."""
import numpy as np
import pytest

from huntkit.gendesign import frame_production as fp


def test_navier_square_plate_matches_roark():
    # Roark: simply supported square plate, center point load, δ = 0.01160 P a^2 / D
    d = fp.ss_point_deflection(100.0, 100.0, D=1.0, P=1.0, nterm=30)
    assert d == pytest.approx(0.01160 * 100.0 ** 2, rel=0.04)


def test_shoelace_square_matches_second_moment():
    xy = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], float)
    A, cx, cy, Ixx, Iyy, Ixy = fp._shoelace(xy)
    assert A == pytest.approx(1.0)
    assert cx == pytest.approx(0.5) and cy == pytest.approx(0.5)
    assert Ixx == pytest.approx(1.0 / 12.0, rel=0.02)
    assert Iyy == pytest.approx(1.0 / 12.0, rel=0.02)


def test_study_joint_baseline_and_production_sf():
    # printed_frame_study.md: one 5 mm dowel, 50 mm embed, meat_straps flange 4596 N → SF 1.03
    base = fp.pullout_sf(4596.0, n_per_flange=1, d_mm=5.0, embed_mm=50.0)
    assert base == pytest.approx(1.03, abs=0.02)
    spec = fp.size_joint()
    assert spec["min_sf"] >= 1.3
    assert spec["min_pull_sf"] >= 1.3
    assert spec["n_per_flange"] >= 2
    assert spec["mass_g"] > 0


def test_bushing_lowers_the_pawl_failure_index():
    # A fore-aft factored load large enough that a bare D4.2 hole in a 5 mm cheek is the hotspot.
    force = np.array([0.0, 1600.0, 500.0])
    bare = fp.cheek_check(force, hole_d=4.2, thick=5.0, metal=False)
    bushed = fp.cheek_check(force, hole_d=8.0, thick=8.0, metal=True, pin_d=4.2)
    assert bushed["fi99"] < bare["fi99"]
    assert bushed["fi99"] < 1.0
    assert bushed["bearing_sf"] > bare["bearing_sf"]
    assert bushed["metal_sf"] > 2.0


def test_barrier_picks_a_passing_option():
    win = fp.Window(width_mm=200, height_mm=280, cavity_mm=28, foam_mm=6.0,
                    foam_k_n_per_mm3=0.04, z0=200, z1=480, x_inner_mm=100,
                    y_wearer=-18, y_bag=10)
    comp = fp.compare_barriers(win)
    rows = [fp.attach_hardware(r, win) for r in comp["rows"]]
    passing = [r for r in rows if r["passes"]]
    assert passing, "no barrier concept passed the bone load and the skin-pressure limit"
    winner = min(passing, key=lambda r: r["mass_g"])
    assert winner["sf"] >= 1.3
    assert winner["family"] in ("printed web", "clip-in sheet", "tensioned panel")
    # every concept was actually evaluated
    assert {r["family"] for r in rows} == {"printed web", "clip-in sheet", "tensioned panel"}
    if winner["mode"] == "spanning":
        assert winner["defl_mm"] <= winner["standoff_mm"]
    else:
        assert winner["pressure_kpa"] <= fp.SKIN_KPA


def test_ppa_holds_stiffness_where_paht_does_not():
    heat = fp.heat_comparison(torsion_paht_rel=0.94, plastic_g=470)
    assert heat["ppa"]["hot_60c"] > heat["paht"]["hot_60c"]
    assert heat["paht"]["hot_60c"] < heat["feel_limit"]
    assert heat["ppa"]["hot_60c"] > heat["feel_limit"]
    assert heat["recommend"] == "pa12_cf_fdm_paht"
    assert heat["ppa_plastic_g"] > 470


def test_mass_rollup_adds_and_uses_the_soft_goods_baseline():
    joint = fp.size_joint()
    pawl = {"chosen": {"mass_g": 8.0}}
    barrier = {"mass_g": 40.0}
    roll = fp.mass_rollup(480.0, joint, pawl, barrier)
    assert roll["frame_g"] == pytest.approx(sum(roll["parts_g"].values()))
    assert roll["pack_g"] == pytest.approx(fp.SOFT_GOODS_G + roll["frame_g"])
    assert roll["target_g"] == pytest.approx(2268.0)
    assert roll["pack_lb"] == pytest.approx(roll["pack_g"] / 453.59237)


def test_default_viewer_is_the_generative_frame():
    from huntkit.viz3d.params import load_params
    assert load_params()["frame_type"] == "generative"
