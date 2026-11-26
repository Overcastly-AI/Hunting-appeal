"""BL-086 (B86): design-curve basis, model changes, saddle-washer superposition, part geometry, bill arithmetic and the
stored record (every metal fatigue row on the design curve, walk envelope, C6p, screens). The solid-FE unit fields and
the full run are not repeated here (minutes, GBs); the record is checked instead."""
import json
import math
import os

import numpy as np
import pytest

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_local as BL
from huntkit.gendesign import bl086_global as G
from huntkit.gendesign import bl086_local as L
from huntkit.gendesign import bl086_parts as P

REC = P.OUTDIR / "bl086.json"


def test_design_curve_allowables():
    d = 14479 / math.sqrt(1e5) / 2 + 96.5 / 2          # Yahr fit / 2 at 1e5 (alu_6061_t6 record)
    gm = lambda sa: 2 * sa * 290 / (290 + sa)          # noqa: E731  R 0 Goodman
    assert L.smax_r0(None) == pytest.approx(gm(d), rel=1e-6)
    assert L.smax_r0("metal") == pytest.approx(gm(0.6 * d), rel=1e-6)
    assert L.smax_r0("poly") == pytest.approx(gm(0.85 * d), rel=1e-6)
    assert L.smax_r0(None) == pytest.approx(114.26, abs=0.05)


def test_design_curve_context_patches_and_restores():
    mean = BQ.fat_allow_local(1.0)
    with L.design_curve() as fa:
        assert BQ.fat_allow_local(1.0) == pytest.approx(fa)
        assert BQ.fat_allow_local(2.0) == pytest.approx(fa / 2)
    assert BQ.fat_allow_local(1.0) == pytest.approx(mean) and mean == pytest.approx(190.9, abs=0.1)


def test_b86_model_changes():
    c = L.cfg86()
    m = G.build(c, 19.0)
    m0 = BQ.build({**BQ.CFG0, **{k: v for k, v in c.items() if k == "stay_bolt_z"}}, 19.0)
    for z in c["stay_bolt_z"]:
        assert f"SL{z:g}" in m["nodes"]
    links = {ln["id"]: ln for ln in m["links"]}
    assert links["tie_L155"]["k"][0] == 100.0 and links["tie_L155"]["k"][1] == 3.0e4
    assert links["tie_L85"]["k"] == {ln["id"]: ln for ln in m0["links"]}["tie_L85"]["k"]
    assert links["tee_L330"]["k"][2] == 200.0                      # BL-085 pinned saddle kept
    assert m["nodes"]["HP"][1] == pytest.approx(m0["nodes"]["HP"][1] - 0.125 * BQ.IN)
    names = [s["name"] for s in G.zone_stations(m, c)]
    assert "stay at plug z155 L" in names and any(n.startswith("stay leg-end zone R") for n in names)


def test_saddle_superposition_reduces_to_bl081_without_saddle():
    U = BL.hole_units("t1000_065")
    if not (BQ.CACHE / "hole_units_v2_t1000_065.npz").exists():
        pytest.skip("BL-081 hole units not cached")
    p = L._cache() / "saddle_units_t1000_065_25_80.npz"
    if not p.exists():
        pytest.skip("saddle units not computed (bl086_report run)")
    sec = np.array([100.0, 50.0, -30.0, 2000.0, 3000.0, -15000.0])
    w0, w1 = np.array([40.0, 90.0]), np.array([40.0, -60.0])
    a = L.hole_peak_saddle("t1000_065", sec, w0, w1, (0.0, 0.0), 25.0, 80.0)["peak"]
    b = BL.hole_peak("t1000_065", sec, w0, w1, (0.0, 0.0))["peak"]
    assert a == pytest.approx(b, rel=1e-9)
    # the same 400 N spread over the saddle gives a lower bore peak than over the 14 mm washer
    s = L.hole_peak_saddle("t1000_065", np.zeros(6), np.zeros(2), np.zeros(2), (0.0, 400.0), 25.0, 80.0)["peak"]
    w = BL.hole_peak("t1000_065", np.zeros(6), np.zeros(2), np.zeros(2), (0.0, 400.0))["peak"]
    assert s < 0.6 * w and U["S0"].shape[0] == 12


def test_bond_rejection_volkersen():
    b = L.bond_check()
    E, t1, t2 = BQ.E_AL, 0.065 * BQ.IN, 0.120 * BQ.IN
    lam = math.sqrt(700 / 0.13 * (1 / (E * t1) + 1 / (E * t2)))
    assert b["lambda_per_mm"] == pytest.approx(lam)
    assert b["tau_peak_walk_mpa"] > 10.0


def test_printed_parts_and_interference():
    out = P.export(log=lambda *a: None)
    for k, v in out.items():
        assert v["watertight"], k
    chk = P.interference_check()
    for k, v in chk.items():
        if k.endswith("mm3") or "mm3 (notched)" in k:
            assert v < 1.0, (k, v)
    assert chk["post_stem_vs_rungs_mm3 (B81, unnotched)"] > 100.0     # finding F1 reproduced


def test_bill_arithmetic():
    printed = P.export(log=lambda *a: None)
    m = P.mass_table(printed)
    assert m["body_g"] == pytest.approx(sum(m["rows"].values()), abs=0.5)
    c8, c5 = P.cost_table(m, ship_zone=8), P.cost_table(m, ship_zone=5)
    assert c8["per_frame_usd"] == pytest.approx(sum(x["usd"] for x in c8["lines"]), abs=0.05)
    assert c8["per_frame_usd"] - c5["per_frame_usd"] == pytest.approx((20.43 - 13.24) * 1.2, abs=0.02)
    assert all(x["source"] for x in c8["lines"])


@pytest.mark.skipif(not REC.exists(), reason="record not generated")
def test_record_basis_and_consistency():
    r = json.loads(REC.read_text())
    gated = [x for x in r["rows"] if x.get("margin") is not None and x["kind"] != "info"]
    assert min(x["margin"] for x in gated) == pytest.approx(r["min_margin"])
    assert r["strong_pass"] == (r["min_margin"] >= 1.0)
    # no metal fatigue row left on the Yahr mean-curve allowable (190.9 MPa)
    assert not [x for x in r["rows"] if x["kind"] == "fatigue" and x.get("allow") and abs(x["allow"] - 190.9) < 0.5]
    assert r["basis"]["c6p"] and "meat_straps" in r["basis"]["walk"]
    assert any("tall_load_posts" in str(v.get("case", "")) for v in r["global"]["c6p"].values())
    assert r["cap_pass_zone8"] == (r["cost"]["per_frame_usd"] <= 150.0)
    assert r["cap_pass_zone5"] == (r["cost_zone5"]["per_frame_usd"] <= 150.0)
    for f in r["fixed"]:
        assert f["b85_design"] < 1.0
    for s in r["screens"]:
        assert os.path.getsize(BQ.REPO / s) < 1.5e6
