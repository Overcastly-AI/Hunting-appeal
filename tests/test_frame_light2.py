"""Lighter-frame study 2 (huntkit.gendesign.frame_light2): model build, joint checks, mass and summary logic."""
import math

import numpy as np
import pytest

from huntkit.fea.joints import bond_check, volkersen_factor
from huntkit.gendesign import frame_light2 as L


def test_volkersen_balanced_limit():
    # balanced adherends: k = (wL/2) coth(wL/2); short overlap -> 1, long -> wL/2
    assert volkersen_factor(1e-4) == pytest.approx(1.0, rel=1e-3)
    x = 8.0
    assert volkersen_factor(x, 1.0) == pytest.approx(x / 2 / math.tanh(x / 2), rel=1e-9)


def test_soft_printed_socket_raises_the_peak():
    """Same tube, same load: a 2.4 mm PAHT socket (E t 9.3 kN/mm) gives a higher Volkersen peak than the 0.75 mm
    carbon wrap of the v2 frame. This is why NODE fails and TENDON passes."""
    tube_Et, tube_Gt = 80000 * 0.815, 5000 * 0.815
    pj = L.printed_joint("through")
    wj = {**L.wrap_joint()}
    wj.pop("wrap", None)
    a = bond_check(500.0, 0.0, 20000.0, 10.0, tube_Et, tube_Gt, {**pj, "overlap_mm": 40.0})
    b = bond_check(500.0, 0.0, 20000.0, 10.0, tube_Et, tube_Gt, {**wj, "overlap_mm": 40.0})
    assert a.tau_avg == pytest.approx(b.tau_avg)
    assert a.k_axial > b.k_axial


def test_printed_bond_allowable_is_the_published_value():
    assert L.TAU_PA_DRY == 5.0          # Sedlacek et al. 2025, DP620NS on MJF PA12
    assert L.TAU_PA_MPA == pytest.approx(4.0)


def test_spigot_doubles_bond_perimeter():
    from huntkit.fea.sections import from_spec
    sec = from_spec(L._spec(18, "RW45", 4))
    k = L._spigot_factor({"spigot": True}, sec)
    assert k == pytest.approx((18 + 18 - 2 * sec.dims["t"]) / 18)
    assert L._spigot_factor({}, sec) == 1.0


def test_build_node_has_necks_and_printed_joints():
    m = L.build(L.candidate("NODE"), 19.0)
    necks = [q for q in m["members"] if q["group"] == "lug_neck"]
    assert len(necks) == 4                                    # mid + upper bar, both sides
    for q in necks:
        a, b = q["nodes"]
        assert np.linalg.norm(np.subtract(m["nodes"][b], m["nodes"][a])) == pytest.approx(L.LUG["neck_mm"])
    kinds = {j["params"].get("kind") for j in m["joints"] if (j.get("params") or {}).get("printed")}
    assert {"end", "through", "foot", "stay_top"} <= kinds
    # the crown corners keep the carbon joint with the rev C 0.8 mm bondline
    cc = next(j for j in m["joints"] if j["id"] == "crown_corner_L")
    assert cc["params"]["adhesive_t_mm"] == pytest.approx(0.8)


def test_build_tendon_uses_carbon_wraps_and_branch_adds_members():
    m = L.build(L.candidate("TENDON"), 19.0)
    assert not [q for q in m["members"] if q["group"] == "lug_neck"]
    assert any((j.get("params") or {}).get("wrap") for j in m["joints"])
    mb = L.build(L.candidate("BRANCH"), 19.0)
    assert len([q for q in mb["members"] if q["group"].startswith("branch")]) == 4


def test_static_carry_runs_and_checks_are_finite():
    from huntkit.fea.load_standard import ls1_cases
    c = next(x for x in ls1_cases(rev="C") if x.name == "static_carry")
    row = L.run_case(L.candidate("TENDON"), 19.0, "crown_bar", c)
    assert row["hip_fraction"] == pytest.approx(0.8, abs=0.02)
    assert row["members"]["stays"][0] > 1.0
    assert "fatigue" in row and row["fatigue"]["stays"][0] > 1.0
    for k in ("foot", "collar", "stay_ring", "hip_insert", "hip_flange", "clip"):
        assert row[k] > 0          # inf = the check sees no load in this case
    assert np.isfinite(row["collar"]) and np.isfinite(row["hip_insert"])


def test_summary_orders_value_name_where():
    rows = [{"case": "static_carry", "torso": 19.0, "variant": "crown_bar", "req": 2.0, "g": 1.0,
             "members": {"stays": (1.5, "S1", 3.0)}, "buckling": 2.0, "bonds": {}, "hip_fraction": 0.8,
             "crown": {"members": {}, "joints": {}, "bushings": {}, "pawl_n": [0, 0, 100.0]}, "plate": {},
             "foot": 3.0, "collar": 3.0, "stay_ring": 3.0, "hip_insert": 0.9, "hip_flange": 3.0, "clip": 5.0,
             "fatigue": {"stays": (1.2, "S1")}}]
    s = L.summarize(rows)
    assert s["min_strength"][0] == pytest.approx(0.9)
    assert s["min_strength"][1] == "hip node 4 x M5 inserts"
    assert s["pass"] is False


def test_mass_rollup_tendon_lighter_than_today_and_node_mass_positive():
    c = L.candidate("TENDON")
    m = L.build(c, 19.0)
    mr = L.mass_rollup(c, m)
    assert 600.0 < mr["frame_g"] < L.TODAY["frame_g"]
    assert all(n["g_each"] > 0 for n in mr["nodes"])
    assert mr["groups"]["carbon tendon wraps"] > 0
    assert mr["groups"]["crown + torso adjust (unchanged)"] == pytest.approx(sum(L.CROWN.values()))
    node = L.mass_rollup(L.candidate("NODE"), L.build(L.candidate("NODE"), 19.0))
    assert node["groups"]["carbon tendon wraps"] == 0.0


def test_sleeve_volume_closed_form():
    v = L._sleeve_vol(20.0, 30.0, 2.0, ta=0.5)
    assert v == pytest.approx(math.pi * (20 + 1 + 2) * 2 * 33)
