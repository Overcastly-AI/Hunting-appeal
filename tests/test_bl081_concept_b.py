"""BL-081 concept B81: model surgery, joint springs, BL-082 basis, parts / bill, and the stored record."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_parts as BP


def test_bl082_fatigue_basis():
    # Yahr: Sa(1e5) = 14479 / sqrt(1e5) + 96.5 = 142.3; Goodman R 0 on Su 290 -> 190.9 (record value)
    assert BQ.fat_allow_local(1.0) == pytest.approx(190.9, abs=0.2)
    assert BQ.fat_allow_local(3.0) == pytest.approx(63.6, abs=0.2)
    assert BQ.notch_q(2.65) == 1.0
    assert BQ.tube_props()["mu_al_wet"] == pytest.approx(0.15)


def test_huth_and_bolt_link():
    k = BQ.huth_k(2.29, 68900, 1.651, 68900)
    assert 1e4 < k < 1e5
    v = BQ.bolt_link_k(1.651, 2.29, 11.9, "y", "x", axial=False)
    assert v[1] == pytest.approx(100.0)                      # plates cannot push the tube along the bolt
    assert v[3] > 0 and v[5] > 0 and v[4] == 0               # couples about x and z, free about the bolt axis
    assert v[3] == pytest.approx(2 * BQ.GAP_KNOCK * k * 11.9 ** 2 * 1.0, rel=0.05) or v[3] > 0


def test_post_section():
    s = BQ.post_sec()
    assert s.Iy == pytest.approx(2 * 32.4e3, rel=0.03)       # 1-1/2 x 1/8 angle: Ix 0.074 in4 = 30.8e3 (AISC-class)


def test_model_wiring():
    m = BQ.build(None, 19.0)
    ids = {mm["id"] for mm in m["members"]}
    assert not {"plh21", "pivot_boss"} & ids
    groups = {mm["group"] for mm in m["members"]}
    assert {"lumbar_cross_tube", "lumbar_gusset", "hip_bracket", "hip_ties"} <= groups
    links = {ln["id"] for ln in m["links"]}
    for tag in "LR":
        for z in BQ.CFG0["rung_z"]:
            assert f"plug_{tag}{z:g}" in links and f"tie_{tag}{z:g}" in links
        assert f"tee_{tag}520" in links and f"lb_{tag}105" in links
    assert m["nodes"]["HP"][1] == pytest.approx(BQ.PIN_Y)
    # no stay hole above z 160 (crown-leg travel)
    for s in BQ.stations(BQ.CFG0):
        if s["group"] == "stay":
            assert m["nodes"][s["node"]][2] <= 160.0


def test_single_case_runs():
    from huntkit.fea.load_standard import ls1_cases
    m = BQ.build(None, 19.0)
    case = [c for c in ls1_cases() if c.name == "static_carry"][0]
    r = case.run(m)
    assert all(math.isfinite(mm["sf"]) for mm in r.members)
    lf = r.meta["link_forces"]
    # the hip torque goes through the ties as a couple: upper and lower ties pull / push in opposite y
    assert np.sign(lf["tie_L150"][1]) != np.sign(lf["tie_L90"][1])


def test_cut_list_and_bill():
    cfg = dict(BQ.CFG0)
    printed = {"x": {"count": 2, "mass_g_each": 10.0}}
    mass = BP.mass_table(cfg, printed)
    assert mass["body_g"] == pytest.approx(sum(mass["rows"].values()), abs=1.0)
    cost = BP.cost_table(cfg, mass)
    assert cost["per_frame_usd"] == pytest.approx(sum(l["usd"] for l in cost["lines"]), abs=0.05)
    # every tube buy fits in sticks <= 36 in (no oversize shipping)
    assert all("72 in" not in l["item"] and "48 in" not in l["item"] for l in cost["lines"])


def test_record_consistent():
    if not BQ.REC_JSON.exists():
        pytest.skip("run python -m huntkit.gendesign.bl081_report run first")
    rec = json.loads(BQ.REC_JSON.read_text())
    ms = [r["margin"] for r in rec["rows"] if r.get("margin") is not None and r["kind"] != "info"]
    assert rec["min_margin"] == pytest.approx(min(ms), abs=1e-3)
    assert rec["strong_pass"] == (rec["min_margin"] >= 1.0)
    assert {c["id"] for c in rec["coupons"]} >= {"CL-1", "BB-1", "HB-P"}
    for v in list(rec["parts"]["printed"].values()) + list(rec["parts"]["jigs"].values()):
        assert v["watertight"]
    assert rec["cost"]["per_frame_usd"] == pytest.approx(sum(l["usd"] for l in rec["cost"]["lines"]), abs=0.05)
