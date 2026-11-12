"""BL-021: IM3 eye and H1 body on the cloth-sim loads (huntkit/gendesign/im3_body_simloads.py).

Solver verification against closed forms (voxel H8 cantilever vs Timoshenko, square-bar torsion, beam frame vs
Euler-Bernoulli) lives in tests/test_gendesign.py, tests/test_frame_topopt.py and tests/test_fea.py; the eye FEA here
uses the same fem.Grid / ke_h8 / ReducedSystem path. These tests check this module's own physics and its record.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import im3_body_simloads as M

REC = Path(M.RESULTS)


@pytest.fixture(scope="module")
def res():
    if not REC.exists():
        pytest.skip("run python -m huntkit.gendesign.im3_body_simloads first")
    return json.loads(REC.read_text())


def test_strap_vector_is_rev_c_im3():
    """The strap vector per 1 g reproduces rev C's factored IM3 strap force divided by g x factor."""
    rc = json.loads((M.ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]["gov_c"]["im3"]
    v = M.strap_vector_1g()
    assert np.allclose(v * rc["g_times_req"], [rc["fx"], rc["fy"], rc["fz"]])
    assert v[1] > 0 and v[2] < 0           # aft toward the bag and down: the strap pulls the eye aft


def test_eye_fea_is_linear_and_puts_on_the_load():
    """FI99 per newton is independent of the load size (linear solve, fixed direction) and the patch carries the
    requested force; a lateral part adds to the FI (cheek face load)."""
    r = M.eye_fea(13.5, 8.0, {"a": [0.0, 0.0, -1000.0], "b": [0.0, 0.0, -2500.0], "lat": [150.0, 0.0, -1000.0]},
                  h=1.0)
    a, b, lat = r["loads"]["a"], r["loads"]["b"], r["loads"]["lat"]
    assert a["fi99_per_n"] == pytest.approx(b["fi99_per_n"], rel=1e-6)
    assert a["applied_n"] == pytest.approx(1000.0, rel=0.02)
    assert lat["applied_n"] == pytest.approx(np.hypot(150.0, 1000.0), rel=0.02)
    assert lat["fi99"] > a["fi99"]
    assert 9.0 < r["added_g"] < 10.5        # 27 mm cheek: loadpath_check FROZEN 9.53 g at h 1.0


def test_hook_vectors_against_leg_sums(res):
    """The rebuilt hook vector can't exceed the scalar sum of its legs and, with legs within ~30 deg of each other,
    is at least 85 % of it; the pull is mostly downward (aft angle < 15 deg)."""
    for key, hv in res["hook_vectors"].items():
        for s in "RL":
            h = hv[s]
            assert h["mag"] <= h["leg_sum"] + 0.5, (key, s)
            assert h["mag"] >= 0.85 * h["leg_sum"], (key, s)
            assert 0.0 < h["aft_of_down_deg"] < 15.0, (key, s)


def test_chosen_cheek_meets_target_on_every_grid_and_hook(res):
    e = res["eye"]
    ch = e["cands"][e["chosen"]]
    for g, pg in ch["per_grid"].items():
        for k, r in pg["rows"].items():
            assert r["fatigue"] >= M.FAT_REQ, (g, k)
            assert r["strength"] >= M.STR_REQ, (g, k)
            assert r["creep"] >= 1.0, (g, k)
        assert pg["misuse_strength"] >= M.STR_REQ
    # design value is the smallest margin over grids and hooks
    allf = [r["fatigue"] for pg in ch["per_grid"].values() for r in pg["rows"].values()]
    assert ch["design"]["fatigue"]["value"] == pytest.approx(min(allf))
    # it is the lightest candidate that passes
    for k, c in e["cands"].items():
        if c["added_g_h1"] < ch["added_g_h1"]:
            assert not c["pass"], k


def test_margins_scale_as_expected(res):
    """Fatigue / creep / strength of one row all come from the same FI per newton: fat/(1.6 F) vs rup/F vs 1/(3 F)."""
    pa = M._paht()
    ch = res["eye"]["cands"][res["eye"]["chosen"]]
    r = next(iter(ch["per_grid"]["1"]["rows"].values()))
    assert r["creep"] / r["fatigue"] == pytest.approx(pa["rupture"] * M.G_WALK / pa["fat"], rel=1e-9)
    assert r["strength"] / r["fatigue"] == pytest.approx(M.G_WALK / (M.FACTOR * pa["fat"]), rel=1e-9)


def test_flip_points(res):
    pa = M._paht()
    ch = res["eye"]["cands"][res["eye"]["chosen"]]
    assert ch["ca1_flip_ratio"] == pytest.approx(pa["fat"] / ch["design"]["fatigue"]["value"])
    for b, bases in res["body"].items():
        for base, v in bases.items():
            assert v["ca1_flip_ratio"] == pytest.approx(pa["fat"] / v["min"]["fatigue"]), (b, base)


def test_beam_basis_reproduces_bl017(res):
    """H1 on the beam loads with per-torso tags reproduces BL-017's recorded per-torso body (fatigue 1.150)."""
    cd = json.loads((M.ANALYSIS / "crown_diet_results.json").read_text())["body"]
    h1 = res["body"]["h1"]["beam"]["min"]
    assert h1["fatigue"] == pytest.approx(cd["h1"]["min"]["fatigue"], abs=0.005)
    assert h1["strength"] == pytest.approx(cd["h1"]["min"]["strength"], abs=0.005)


def test_sim_loads_balance_the_bag_weight():
    """The sim forces mapped onto the beam nodes (plus the under-strap residual) balance the bag weight at 1 g,
    and the residual left for the under-strap pins is a small share of it."""
    if not M.SIMFORCES1.exists():
        pytest.skip("sim frame forces not cached (outputs/ untracked)")
    from huntkit.fea.frame import G_ACC
    from huntkit.gendesign import crown_diet as CD
    sf = M.sim_forces(rev=1)
    run = "F_PR19_fineFM"
    model = CD.build(CD.specs()["h1"], 19.0)
    for case in ("fill", "meat"):
        kg = M.sim_total_kg(run, case)
        gp, fx, resid = M.sim_nodal_1g(model, sf[f"{run}|{case}"], kg)
        tot = sum(np.asarray(v) for v in gp.values()) + sum((np.asarray(v) for v in fx.values()), np.zeros(3))
        assert tot[2] == pytest.approx(-kg * G_ACC, rel=1e-6)
        assert abs(tot[0]) < 1e-6 and abs(tot[1]) < 1e-6
        assert np.linalg.norm(resid) < 0.35 * kg * G_ACC, case
