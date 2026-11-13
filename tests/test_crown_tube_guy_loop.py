"""Review Y-4: crown top bar wall under the B-25 guy / crown-strap sleeve (huntkit.gendesign.crown_tube_guy_loop).

Closed-form verification of the ring solver (Fourier and FE), reproduction of the repo's legacy check, and the
verdict / fix the analysis doc states."""
import math

import numpy as np
import pytest

from huntkit.gendesign import crown_tube_guy_loop as T


@pytest.fixture(scope="module")
def ver():
    return T.verification()


def test_roark_case1_pair_of_point_loads(ver):
    # Roark table 9.2 case 1: |M| = F R / pi under the loads, F R (1/2 - 1/pi) at 90 deg, N = -F/2 at 90 deg
    assert ver["roark1_M_load"]["fourier"] == pytest.approx(1 / math.pi, rel=0.005)
    assert ver["roark1_M_90"]["fourier"] == pytest.approx(0.5 - 1 / math.pi, rel=0.002)
    assert ver["roark1_N_90"]["fourier"] == pytest.approx(-0.5, rel=0.002)
    # FE (huntkit.fea.frame, element-averaged moment) and the diametral change 0.1488 F R^3 / EI
    assert ver["roark1_M_load"]["fe"] == pytest.approx(1 / math.pi, rel=0.02)
    assert ver["roark1_dD"]["fe"] == pytest.approx(ver["roark1_dD"]["closed_form"], rel=0.02)


def test_bruhn_point_load_on_shear_flow(ver):
    # ring frame loaded by a point load and reacted by sinusoidal shear: M_max = 3 F R / (4 pi) = 0.2387 F R
    assert ver["bruhn_point_shear_M"]["fourier"] == pytest.approx(3 / (4 * math.pi), rel=0.005)
    assert ver["bruhn_point_shear_M"]["fe"] == pytest.approx(3 / (4 * math.pi), rel=0.02)


def test_wrap_fourier_matches_fe_and_is_self_equilibrated(ver):
    assert ver["wrap180_M"]["fe"] == pytest.approx(ver["wrap180_M"]["fourier"], rel=0.08)
    assert ver["wrap180_M"]["fourier"] < 0.02            # a 180 deg wrap is far gentler than a point load
    assert ver["fe_max_reaction_n"] < 0.01               # supports carry nothing: loads balance (F = 100 N)
    th = np.linspace(0, 2 * np.pi, 3600, endpoint=False)
    for kind in ("pair", "point_shear", "wrap_shear"):
        r = T.ring_fourier(*T.load_pattern(kind, th), th)
        assert r["p1"] == pytest.approx(r["q1"], abs=1e-6)


def test_basis_A_reproduces_the_repo_check():
    leg = T.legacy_reproduction()
    for F in ("244.5", "288"):
        assert leg[F]["basis_A_sf"] == pytest.approx(leg[F]["bar_local_sf"], rel=1e-9)
    assert 288.0 * leg["288"]["bar_local_sf"] == pytest.approx(295.0, abs=1.0)        # review Y-4's 295 N
    assert leg["rev_b_210"]["capacity_n"] == pytest.approx(228.0, abs=1.0)            # and its 228 N


def test_every_kit_uses_the_same_bar():
    ks = T.kit_sections()
    assert len({(v["od"], v["t"], v["layup"]) for v in ks.values()}) == 1
    v = next(iter(ks.values()))
    assert v["od"] == 18.0 and v["t"] == pytest.approx(1.065)


def test_capacity_linear_in_width_basis_A():
    s = T.section("rev_c")
    c25 = T.capacity(s, 25.0, "A", globals_=False)["capacity_n"]
    c50 = T.capacity(s, 50.0, "A", globals_=False)["capacity_n"]
    assert c50 == pytest.approx(2 * c25, rel=1e-9)
    # the bar's own bending + shear flow (not width-dependent) take a few per cent off
    g50 = T.capacity(s, 50.0, "A")["capacity_n"]
    assert 0.95 * c50 < g50 < c50


@pytest.fixture(scope="module")
def ctx():
    return T.run()


def test_loads_trace_to_the_sims(ctx):
    env = ctx["kit_loads"]["envelope"]
    assert env["cases"]["guy alone (C5, x3.0)"] == pytest.approx(288.0)
    assert env["static_n"] == pytest.approx(3.0 * (96.0 + 11.6), abs=0.5)
    assert env["fatigue_peak_n"] == pytest.approx(1.6 * (96.0 + 11.6), abs=0.5)


def test_verdict_today_fails_on_the_standard_basis(ctx):
    a = ctx["per_kit"]["envelope"]["A"]
    assert a["sf_static"] < 1.0 and a["sf_fatigue"] < 1.0
    assert ctx["per_kit"]["L"]["A"]["sf_static"] < 1.0
    assert ctx["per_kit"]["S"]["A"]["sf_static"] > 1.0 and ctx["per_kit"]["S"]["A"]["sf_fatigue"] > 1.0
    # TL-1 at 1.5 x factored is above the bare bar's pristine capacity on basis A: expected to crush
    assert a["proof_over_rt_capacity"] > 1.0


def test_recommended_fix_passes_and_is_light(ctx):
    fx = {f["key"]: f for f in ctx["fixes"]}
    rec = fx[ctx["recommended"]]
    assert rec["passes"] and rec["sf_static"] >= 1.3 and rec["sf_fatigue"] >= 1.2
    assert rec["d_mass_g"] < 4.0
    assert rec["proof_over_rt_capacity"] < 0.8            # TL-1 with the fix fitted should pass on basis A
    assert not fx["b25_50"]["passes"]                      # 50 mm does not fit beside the spine clamp
    assert not fx["hdpe_liner"]["passes"]
    assert ctx["lightest_passing"] == "hoop1_in"           # lightest on paper is a frame change (+2.1 g)
    tl = ctx["tl1"]
    assert tl["bar_rule_proof_n"] > tl["proof_n"]          # knocked-down basis sets the TL-1 load (~494 N)
    assert tl["bar_rule_proof_n"] < tl["rt_capacity_A_n"]
