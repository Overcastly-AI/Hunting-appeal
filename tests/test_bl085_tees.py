"""BL-085 (B85 tees): fatigue basis against the record's closed forms, part geometry (no collision, real free end),
bill arithmetic, and the stored record's consistency (every clamp row at both scatter limits, C6p in the envelope,
screens under 1.5 MB). The solid-FE rows are not re-run here (minutes, GBs): the record is checked instead."""
import json
import math
import os

import pytest

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl085_parts as P
from huntkit.gendesign import bl085_tee as T

REC = P.OUTDIR / "bl085.json"


def test_design_curve_is_half_the_yahr_fit_at_1e5():
    b = T.sn_basis()
    assert b["mean"] == pytest.approx(14479 / math.sqrt(1e5) + 96.5, rel=1e-6)       # 142.3, alu_6061_t6 record
    assert b["design"] == pytest.approx(b["mean"] / 2, rel=1e-6)                     # stress / 2 governs over life / 20
    # R 0 Goodman on the mean curve reproduces the record field fatigue_smax_1e5_r0_goodman_mpa
    sm = 2 * b["mean"] * 290 / (290 + b["mean"])
    assert sm == pytest.approx(190.9, abs=0.2)


def test_knockdowns_multiply():
    cfg = dict(T.CFG85)
    d = T.sn_basis()["design"]
    assert T.allowable_sa("metal", cfg) == pytest.approx(0.6 * d)
    assert T.allowable_sa("poly", cfg) == pytest.approx(0.85 * d)
    assert T.allowable_sa("metal", {**cfg, "finish": "anodised"}) == pytest.approx(0.6 * 0.7 * d)
    assert T.goodman_margin(25.0, 145.0, 50.0) == pytest.approx(1.0)


def test_upper_tee_geometry_has_a_real_free_end_and_no_collision():
    c = T.CFG85
    assert c["stay_len"] - c["shell_top_z"] == pytest.approx(c["free_above"]) and c["free_above"] >= 15.0
    chk = P.interference_check()
    assert chk["ok"], chk
    assert chk["shell_vs_collar_mm3"] == 0.0 and chk["gap_shell_to_collar_mm"] >= 3.0


def test_bolt_grip_fits_the_screw():
    grip = P.stock_shell()["od"] + 2 * T.CFG85["backer_t"]
    clamp = [L for n, d, L, w in P.BOLTS85 if "clamp bolts" in w][0]
    assert clamp >= grip + 0.8 * 5 + 1.0            # nut (0.8 d) + a thread past it


def test_printed_parts_watertight_and_light():
    out = P.export(log=lambda *a: None)
    for k, v in out.items():
        assert v["watertight"], k
        assert v["mass_g_each"] < 15.0, k


def test_bill_arithmetic():
    printed = P.export(log=lambda *a: None)
    m = P.mass_table(printed)
    assert m["body_g"] == pytest.approx(sum(m["rows"].values()), abs=0.5)
    c = P.cost_table(m)
    assert c["per_frame_usd"] == pytest.approx(sum(l["usd"] for l in c["lines"]), abs=0.02)
    assert any("FedEx" in l["item"] for l in c["lines"])                    # shipping is booked, not dropped (M6)
    assert all(l["source"] for l in c["lines"])
    assert P.cost_table(m, ship_zone=5)["per_frame_usd"] < c["per_frame_usd"]


@pytest.fixture(scope="module")
def rec():
    if not REC.exists():
        pytest.skip("run python -m huntkit.gendesign.bl085_report run")
    return json.loads(REC.read_text())


def test_record_tees_at_both_scatter_limits(rec):
    up = [r for r in rec["rows"] if r.get("tee") == "upper"]
    for k in ("lo", "nom", "hi"):
        assert any(f"fatigue, preload {k}" in r["row"] for r in up)
    assert any("slip" in r["row"] and "preload lo" in r["row"] for r in up)
    assert any("+30 %" in r["row"] and r["kind"] == "strength" for r in up)
    assert any(r.get("tee") == "mid" and r["kind"] == "fatigue" for r in rec["rows"])     # M1: mid tee checked


def test_record_c6p_in_envelope(rec):
    assert rec["global"]["c6p"]["included"]
    assert "tall_load_posts" in rec["global"]["strength"]["stays"]["case"]


def test_record_verdict_consistent(rec):
    strong = [r for r in rec["rows"] if r.get("margin") is not None and r["kind"] != "info"]
    assert rec["min_margin"] == pytest.approx(min(r["margin"] for r in strong))
    assert rec["strong_pass"] == (rec["min_margin"] >= 1.0)
    assert rec["cap_pass"] == (rec["cost"]["per_frame_usd"] <= 150.0)
    assert {c["option"] for c in rec["comparison"]} >= {"H1c", "B81", "B81-Lb", "D83-L"}
    # the B1 control reproduces review 9's failure of the as-drawn B81 tee
    assert rec["b81_asbuilt"]["static_margin"] < 1.0 and rec["b81_asbuilt"]["fatigue_mean"] < 1.0


def test_record_coupons_and_screens(rec):
    ids = {c["id"] for c in rec["coupons"]}
    assert {"CL-T", "KF-T", "KF-S", "BS-T", "OV-2"} <= ids
    assert all(c["pass"] for c in rec["coupons"])
    for s in rec["screens"]:
        p = BQ.REPO / s
        assert p.exists() and os.path.getsize(p) < 1.5e6
