"""HA-LS-1 rev C (owner 2026-11-06): the default standard, rev B still reachable, the hood + guy top anchor in
closed form, and the spreader skin-pressure cache regression (it used to be keyed without the meat load)."""
import numpy as np
import pytest

from huntkit.fea.frame import G_ACC
from huntkit.fea.frames import build_frame_from_yaml
from huntkit.fea.load_cases import top_anchor_loads_1g
from huntkit.fea import load_standard as LS
from huntkit.gendesign import frame_topopt as ft


@pytest.fixture(scope="module")
def fm19():
    return build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)


def _by(cases):
    return {c.name: c for c in cases}


def test_rev_c_is_the_default_and_rev_b_reproduces():
    assert LS.REVISION == "C"
    c = _by(LS.ls1_cases())
    for n in LS.BAG_CASES:
        assert c[n].cg_aft_mm == 205.0 and c[n].cg_z_mm == 550.0
        assert "couple_top_group" not in c[n].params                # default variant: crown top bar
    for n in LS.MEAT_CASES:
        assert c[n].cg_aft_mm == 190.0 and c[n].params["top_anchor"]["kind"] == "hood_guys"
    for n in LS.TALL_CASES:
        assert c[n].cg_aft_mm == 185.0 and "top_anchor" not in c[n].params
    b = _by(LS.ls1_cases(rev="B"))
    assert [b[n].cg_aft_mm for n in ("static_carry", "meat_straps", "tall_load", "hipbelt_off_abuse")] == \
        [180.0, 150.0, 160.0, 180.0]
    assert all(x.cg_z_mm is None and "top_anchor" not in x.params for x in b.values())
    # rev B kept its quirk: a bag CG override does not reach C8; rev C applies it to all five bag cases
    assert _by(LS.ls1_cases(148.0, rev="B"))["hipbelt_off_abuse"].cg_aft_mm == 180.0
    assert _by(LS.ls1_cases(148.0))["hipbelt_off_abuse"].cg_aft_mm == 148.0
    # same factors and g-levels in both revisions
    for n, (g, req, kg) in LS.TABLE.items():
        assert (c[n].g_factor, c[n].required_sf, c[n].load_kg) == (g, req, kg) == \
            (b[n].g_factor, b[n].required_sf, b[n].load_kg)
    with pytest.raises(ValueError):
        LS.ls1_cases(rev="B", couple_top="strap_upper")


def test_envelope_has_both_couple_tops():
    env = LS.ls1_envelope()
    assert set(env) == {"crown_bar", "strap_upper"}
    assert [c.name for c in env["strap_upper"]] == [n for n in LS.TABLE if n in LS.BAG_CASES]
    assert all(c.params["couple_top_group"] == "strap_upper" for c in env["strap_upper"])
    assert set(LS.ls1_envelope("B")) == {"crown_bar"}


def test_tie_webbing_rule():
    assert LS.tie_bearing_ok(25.0) and LS.tie_bearing_ok(38.0) and not LS.tie_bearing_ok(20.0)
    assert LS.tie_bearing_ok(20.0, rev="B")


def test_hood_guy_loads_closed_form(fm19):
    """Resultant: hood 52.5 N aft + two 34.6 N guys toward (+/-149, y + dy, 752). The nodal split preserves the
    resultant and the moment about the bar exactly, with or without nodes at the hood ears."""
    spec = LS.TOP_ANCHOR_HOOD_GUYS
    L = top_anchor_loads_1g(fm19, spec)
    F = sum(L.values())
    nodes = fm19["nodes"]
    pc = np.array(nodes["TB1"], float)
    ids = ["CLtop", "TB0", "TB1", "TB2", "CRtop"]
    P = np.array([nodes[n] for n in ids], float)
    guys, mom = np.zeros(3), np.zeros(3)
    for s in (-1.0, 1.0):
        k = 0 if s < 0 else 3
        t = (s * 95.0 - P[k, 0]) / (P[k + 1, 0] - P[k, 0])
        p = P[k] + t * (P[k + 1] - P[k])
        d = np.array([s * 149.0, p[1] + spec["guy_dy_mm"], 752.0]) - p
        g = spec["guy_n"] * d / np.linalg.norm(d)
        guys += g
        mom += np.cross(p - pc, g)
    assert F == pytest.approx(np.array([0.0, spec["hood_n"], 0.0]) + guys, abs=1e-9)
    assert guys[0] == pytest.approx(0.0, abs=1e-9)             # symmetric
    M = sum(np.cross(np.asarray(nodes[n], float) - pc, v) for n, v in L.items())
    # the hood line load is symmetric about TB1 on a straight bar: its moment about the centre is ~0
    assert M == pytest.approx(mom, abs=1e-6)


def test_meat_case_rev_c_equilibrium_and_c7_scaling(fm19):
    c = _by(LS.ls1_cases())
    spec = LS.TOP_ANCHOR_HOOD_GUYS
    F1 = sum(top_anchor_loads_1g(fm19, spec).values())
    for n, kg in (("meat_straps", 68.0), ("overload_haul", 91.0)):
        x = c[n]
        F = sum(np.asarray(v[:3]) for v in x._loads(fm19).values())
        assert F == pytest.approx(np.array([0, 0, -x.W]) + x.g_factor * kg / 68.0 * F1, abs=1e-6 * x.W)
    # without the anchor the rev C meat couple is the rev B couple scaled by 190 / 150
    a = c["meat_straps"]
    a.params = {k: v for k, v in a.params.items() if k != "top_anchor"}
    Mh = sum(fm19["nodes"][k][2] * v[1] for k, v in a._loads(fm19).items())
    assert Mh == pytest.approx(a.W * 190.0, rel=1e-6)
    assert a.W == pytest.approx(68.0 * G_ACC * 2.0)


def test_crown_fix_in_frame_yaml(fm19):
    """frame.yaml carries the rev C crown: inner UD plies at the same OD, 0.8 mm corner bondline."""
    from huntkit.gendesign import frame_cg_recheck as R
    from huntkit.fea.pack5200 import _sec
    sec = {m["group"]: _sec(m["section"]) for m in fm19["members"]}
    fp = R._frame_params()                          # rev B baseline (crown_rev_b)
    b = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0, **R.rev_b_crown())
    secb = {m["group"]: _sec(m["section"]) for m in b["members"]}
    for g in ("crown_top_bar", "crown_spine"):
        assert sec[g].dims["od"] == secb[g].dims["od"]
        assert sec[g].dims["t"] == pytest.approx(secb[g].dims["t"] + 0.125, abs=1e-6)
    leg = next(k for k in sec if k.startswith("crown_leg"))
    assert sec[leg].dims["t"] == pytest.approx(secb[leg].dims["t"] + 0.25, abs=1e-6)
    assert sec["mid_bar"].dims["t"] == secb["mid_bar"].dims["t"]        # the printed mid bar line is untouched
    corner = {j["id"]: j for j in fm19["joints"]}["crown_corner_R"]["params"]
    hub = {j["id"]: j for j in fm19["joints"]}["mid_hub_R"]["params"]
    assert corner["adhesive_t_mm"] == 0.8 and hub["adhesive_t_mm"] == 0.5
    assert len(fp["leg_section"]["layup"]) == 8


def test_spreader_skin_cache_keys_on_meat_load():
    """Regression (frame_cg_recheck.md section 5): a changed meat load must not reuse a cached skin pressure."""
    from huntkit.gendesign import frame_smooth as fs
    from huntkit.gendesign import spreader as S
    old = S.MEAT_CG_MM
    try:
        S._SKIN_CACHE.clear()
        S.MEAT_CG_MM = 150.0
        a = S.skin_pressure(0.0, "walk")["peak_kpa"]
        S.MEAT_CG_MM = 190.0
        b = S.skin_pressure(0.0, "walk")["peak_kpa"]
        assert b > a * 1.05
        S.MEAT_CG_MM = 150.0
        assert S.skin_pressure(0.0, "walk")["peak_kpa"] == pytest.approx(a)
        assert len(S._SKIN_CACHE) == 2
        # the old way of changing the load (patching frame_smooth) is also seen by the key
        orig = fs.meat_normal_n
        fs.meat_normal_n = lambda g_level=1.6, e_mm=150.0, _o=orig: _o(g_level, e_mm) * 1.3
        try:
            assert S.skin_pressure(0.0, "walk")["peak_kpa"] > a * 1.05
        finally:
            fs.meat_normal_n = orig
    finally:
        S.MEAT_CG_MM = old
        S._SKIN_CACHE.clear()
    assert S.MEAT_CG_MM == LS.meat_cg_mm() == 190.0
