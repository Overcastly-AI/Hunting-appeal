"""Frame re-check at the cloth-sim CG (designs/pack_5200/analysis/frame_cg_recheck.md).

Load-model checks against closed form (statics of the bag couple, the CG-height couple, the ideal 3:1 pulley,
Euler-Eytelwein), the additive LoadCase options keep rev B unchanged, and the recorded results stay consistent.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.fea.frame import G_ACC
from huntkit.fea.frames import build_frame_from_yaml
from huntkit.fea.load_standard import ls1_cases
from huntkit.gendesign import frame_cg_recheck as R
from huntkit.gendesign import frame_topopt as ft

RESULTS = Path(__file__).resolve().parents[1] / "designs" / "pack_5200" / "analysis" / "frame_cg_recheck_results.json"


@pytest.fixture(scope="module")
def fm19():
    return build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)


def _case(name, **kw):
    c = next(x for x in ls1_cases() if x.name == name)
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def _resultant(loads, nodes):
    F, M = np.zeros(3), np.zeros(3)
    for nid, v in loads.items():
        v = np.zeros(6) + np.r_[v, np.zeros(6 - len(v))]
        r = np.asarray(nodes[nid], float)
        F += v[:3]
        M += v[3:] + np.cross(r, v[:3])
    return F, M


def test_defaults_reproduce_rev_b(fm19):
    """cg_z_mm=None, no couple_top_group, no extra loads: identical loads to rev B."""
    for name in ("static_carry", "side_hill_torsion", "meat_straps"):
        a = _case(name)._loads(fm19)
        b = _case(name, cg_z_mm=None)._loads(fm19)
        assert a.keys() == b.keys()
        for k in a:
            assert np.allclose(a[k], b[k])


def test_bag_couple_statics(fm19):
    """Closed form: the aft couple H (z_top - z_bot) equals W e, net force is the weight only."""
    for e in (180.0, 205.0, 223.0):
        c = _case("static_carry", cg_aft_mm=e)
        L = c._loads(fm19)
        F, M = _resultant(L, fm19["nodes"])
        W = 68.0 * G_ACC
        assert np.allclose(F, [0, 0, -W], atol=1e-6)
        # M_x = sum(y Fz - z Fy): the weights give -W y_bar, the couple -H (z_t - z_b) = -W e
        ys = np.array([fm19["nodes"][n][1] for n in fm19["groups"]["bag"]])
        w = np.array(fm19["bag_weights"]) / np.sum(fm19["bag_weights"])
        assert M[0] == pytest.approx(-W * e - W * float(w @ ys), rel=1e-6)


def test_couple_on_im3_keeps_the_moment(fm19):
    """Moving the couple top to the IM3 anchors (z 520) keeps the resultant and the moment W e."""
    a = _case("static_carry", cg_aft_mm=205.0)
    b = _case("static_carry", cg_aft_mm=205.0)
    b.params = {**b.params, "couple_top_group": "strap_upper"}
    Fa, Ma = _resultant(a._loads(fm19), fm19["nodes"])
    Fb, Mb = _resultant(b._loads(fm19), fm19["nodes"])
    assert np.allclose(Fa, Fb, atol=1e-6)
    assert np.allclose(Ma, Mb, atol=1e-6)
    top = fm19["groups"]["strap_upper"]
    zt = np.mean([fm19["nodes"][n][2] for n in top])
    zb = np.mean([fm19["nodes"][n][2] for n in fm19["bag_couple"]["bottom"]])
    H = sum(b._loads(fm19)[n][1] for n in top) - sum(a._loads(fm19).get(n, np.zeros(6))[1] for n in top)
    assert H == pytest.approx(68.0 * G_ACC * 205.0 / (zt - zb), rel=1e-6)


def test_cg_height_couple_closed_form(fm19):
    """Side-hill: with cg_z the lateral load acts at the CG height. Net force unchanged; the moment about y
    grows by Fx (z_cg - z_w), Fx = W g sin 25."""
    a = _case("side_hill_torsion", cg_aft_mm=205.0)
    b = _case("side_hill_torsion", cg_aft_mm=205.0, cg_z_mm=550.0)
    Fa, Ma = _resultant(a._loads(fm19), fm19["nodes"])
    Fb, Mb = _resultant(b._loads(fm19), fm19["nodes"])
    assert np.allclose(Fa, Fb, atol=1e-6)
    bag = fm19["groups"]["bag"]
    xs = np.array([fm19["nodes"][n][0] for n in bag])
    zs = np.array([fm19["nodes"][n][2] for n in bag])
    w = np.array(fm19["bag_weights"], float) * (1 + 0.3 * np.sign(xs))
    w /= w.sum()
    Fx = 68.0 * G_ACC * 1.6 * np.sin(np.radians(25.0))
    assert Mb[1] - Ma[1] == pytest.approx(Fx * (550.0 - float(w @ zs)), rel=1e-6)
    assert np.allclose(Ma[[0, 2]], Mb[[0, 2]], atol=1e-6)


def test_extra_nodal_loads_scale_with_g(fm19):
    c = _case("meat_straps")
    base = c._loads(fm19)
    c.params = {**c.params, "extra_nodal_1g": {"TB0": [0.0, 70.0, 0.0]}}
    L = c._loads(fm19)
    assert L["TB0"][1] - base.get("TB0", np.zeros(6))[1] == pytest.approx(70.0 * c.g_factor)


def test_split_top_bar_is_neutral_and_anchor_totals(fm19):
    m = R.split_top_bar(fm19)
    assert {"TBL100", "TBR100"} <= set(m["nodes"])
    assert m["nodes"]["TBR100"][0] == pytest.approx(100.0)
    corner = {j["id"]: j for j in m["joints"]}["crown_corner_R"]
    assert "TBR100-CRtop" in corner["members"]
    c = _case("static_carry")
    c.buckling = False
    r0, r1 = c.run(fm19), c.run(m)
    assert np.allclose(r0.meta["link_forces"]["pawl"], r1.meta["link_forces"]["pawl"], rtol=1e-6, atol=1e-6)
    for where in ("x70", "x100", "pocket"):
        L = R.anchor_loads_1g(m, where, 0.0)
        assert sum(v[1] for v in L.values()) == pytest.approx(2 * R.ANCHOR_N_1G)
    L = R.anchor_loads_1g(m, "x70", 20.0)
    assert L["TB0"][2] / L["TB0"][1] == pytest.approx(np.tan(np.radians(20.0)))


def test_pulley_closed_form():
    """mu = 0 gives the ideal 3:1; with friction the hold ratio exceeds 3 and the hoist ratio is below 3."""
    old = R.PULLEY_MU
    try:
        R.PULLEY_MU = 0.0
        p = R.pulley_tensions(300.0)
        assert p["tail_hold_n"] == pytest.approx(100.0) and p["tail_hoist_n"] == pytest.approx(100.0)
    finally:
        R.PULLEY_MU = old
    p = R.pulley_tensions(300.0)
    k = np.exp(0.1 * np.pi)
    kc = np.exp(0.1 * np.pi / 2)
    assert p["ratio_hold"] == pytest.approx(kc + kc * k + kc * k * k)
    assert p["ratio_hoist"] < 3.0 < p["ratio_hold"]


def test_scenarios_apply_offsets():
    S = R.scenarios()
    cs = {c.name: c for c in S["b"].case_list()}
    assert cs["static_carry"].cg_aft_mm == 205.0 and cs["hipbelt_off_abuse"].cg_aft_mm == 205.0
    assert cs["side_hill_torsion"].cg_z_mm == 550.0
    assert cs["meat_straps"].cg_aft_mm == 175.0 and cs["tall_load"].cg_aft_mm == 185.0
    ca = {c.name: c for c in S["a"].case_list()}
    assert ca["static_carry"].cg_aft_mm == 180.0 and ca["meat_straps"].cg_aft_mm == 150.0
    assert ca["side_hill_torsion"].cg_z_mm is None
    assert {c.name for c in S["b_im3"].case_list()} == set(R.BAG_CASES)


def test_bar_local_ring_is_linear():
    a, b = R.bar_local(100.0, 25.0), R.bar_local(200.0, 25.0)
    assert a["tie"]["m_hoop"] * 2 == pytest.approx(b["tie"]["m_hoop"])
    assert b["tie"]["sf"] < a["tie"]["sf"]


@pytest.mark.skipif(not RESULTS.exists(), reason="run huntkit.gendesign.frame_cg_recheck first")
def test_recorded_results_consistent():
    d = json.loads(RESULTS.read_text())
    a, b, c = (d["body"][k] for k in ("a", "b", "c"))
    # (a) reproduces the production record (spreader_layout.md section 3, 'today'): 1.69 / 1.19 / 2.55
    assert a["sf_min"] == pytest.approx(1.69, abs=0.02)
    assert a["sf_fatigue"] == pytest.approx(1.19, abs=0.02)
    assert a["sf_creep"] == pytest.approx(2.55, abs=0.03)
    # more aft CG cannot raise the static-carry margin
    assert b["cases"]["static_carry"]["sf"] <= a["cases"]["static_carry"]["sf"] + 1e-6
    assert c["cases"]["static_carry"]["sf"] <= b["cases"]["static_carry"]["sf"] + 1e-6
    sw = [d["body"][f"s{e:g}"]["cases"]["static_carry"]["sf"] for e in (150, 180, 205, 223, 250)]
    assert all(x >= y - 1e-6 for x, y in zip(sw, sw[1:]))


def test_crown_fix_keeps_od_and_mass():
    fp = R._frame_params()
    s = R.add_ud(fp["leg_section"], 2)
    assert s["od"] == fp["leg_section"]["od"]
    assert len(s["layup"]) == len(fp["leg_section"]["layup"]) + 2
    m = R.fix_mass_total()
    # hand check, legs: 2 x pi x d_mean x 2 plies x 0.125 x 430 x 1.58e-3, d_mean ~ 13.4 mm -> ~14.3 g
    assert m["legs"] == pytest.approx(2 * np.pi * 13.36 * 0.25 * 430 * 1.58e-3, rel=0.02)
    assert 20.0 < m["total"] < 24.0


@pytest.mark.skipif(not RESULTS.exists(), reason="run huntkit.gendesign.frame_cg_recheck first")
def test_recorded_fix_passes_and_as_built_crown_fails():
    d = json.loads(RESULTS.read_text())
    assert all(d["fix"]["pass"].values())
    assert d["crown"]["b"]["crown_spine"]["sf"] < 1.0          # the reason for the fix
    assert min(b["sf_min"] for b in d["body"].values() if "sf_min" in b) >= 1.0   # body passes everywhere
    sp = d["spreader"]
    assert all(sp["175"]["checks"][k] for k in ("fpf", "fatigue", "sandwich_local", "no_bottoming"))
    assert not sp["190"]["checks"]["fatigue"]
    # skin pressure grows with the offset (the stale-cache bug would make these equal)
    assert sp["150"]["skin_peak_kpa"] < sp["175"]["skin_peak_kpa"] < sp["223"]["skin_peak_kpa"]
    c7 = d["spreader_core7"]["223"]
    assert all(c7["checks"][k] for k in ("fpf", "fatigue", "sandwich_local", "no_bottoming"))
    fa = d["final_attachment"]
    assert min(v["sf_min"] for v in fa["body"].values()) >= 1.0
    assert all(R.crown_pass(v)[0] for v in fa["crown"].values())


def test_hood_guy_loads_match_attachment_record(fm19):
    m = R.split_top_bar(fm19, 95.0)
    L = R.hood_guy_loads_1g(m)
    hood_y = sum(v[1] for k, v in L.items() if k in ("TB0", "TB1", "TB2")) + 2 * R.HOOD_1G_N * 12.5 / 190.0
    assert hood_y == pytest.approx(R.HOOD_1G_N)
    g = L["TBR95"] - np.array([0.0, R.HOOD_1G_N * 12.5 / 190.0, 0.0])
    assert np.linalg.norm(g) == pytest.approx(R.GUY_1G_N)
    assert g[0] > 0 and g[1] > 0                       # outboard and aft
    # factored at C5 (x 3.0): 158 N hood, 104 N per guy (attach_system_results.json factored_n)
    assert 3.0 * R.HOOD_1G_N == pytest.approx(157.5) and 3.0 * R.GUY_1G_N == pytest.approx(103.8)
