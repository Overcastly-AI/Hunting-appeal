"""BL-006 hipbelt B diet: belt B is reproduced first, masses come from the ledger and records, every package item
passes the ticket's gates, and the package meets the base target at belt M."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import hipbelt_diet as D  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402
from huntkit.materials import load  # noqa: E402


def test_reproduces_belt_b():
    """Acceptance: belt B's published numbers (hipbelt_fit.md / hipbelt_results.json) come out of the same code."""
    b = D.baseline()
    pub = json.loads((ROOT / "designs/pack_5200/concepts/hipbelt_results.json").read_text())["summary"]["B"]
    assert b["worst_wing_kpa"] == pytest.approx(56.5, abs=0.05) == pub["worst_peak_wing_kpa"]
    assert b["median_wing_kpa"] == pytest.approx(50.8, abs=0.05)
    assert b["worst_lumbar_kpa"] == pytest.approx(45.4, abs=0.05)
    assert round(b["median_hold"], 2) == 0.72 or b["median_hold"] == pytest.approx(0.715, abs=0.006)
    assert b["worst_hold"] == pytest.approx(0.64, abs=0.005)
    assert b["min_asis_clear_mm"] == pub["min_asis_clear_mm"]


def test_masses_from_ledger_and_base_split():
    m = D.belt_masses("M")
    assert m["ledger_belt_g"] == L.by_system("corrie_b2_h1_c", "M")["belt"]
    hs = D.holster_split()
    imp3 = next(r["g"] for r in L.parts("corrie_b2_h1_c", "M") if r["id"] == "belt:IMP-3")
    assert hs["total_g"] == pytest.approx(imp3, abs=0.05)
    assert hs["tabs_g"] == pytest.approx(0.12 * load("poly_webbing_25mm").require("mass_g_m"), abs=0.01)
    assert m["base_g"] == pytest.approx(m["as_hunted_g"] - hs["addon_g"], abs=0.1)
    # the ledger table covers every belt row and adds up
    t = D.ledger_table("M")
    assert sum(r["g"] for r in t) == pytest.approx(m["ledger_belt_g"], abs=0.2)
    assert all(r["job"] for r in t)
    assert all(r["margin"] for r in t if r["load_path"])


def test_closure_rebooking_from_records():
    c = D.closure("M")
    booked = 0.9 * load("nylon_webbing_50mm").require("mass_g_m") + 0.6 * load("poly_webbing_25mm").require("mass_g_m")
    assert c["booked_g"] == pytest.approx(booked, abs=0.05)
    # the 91.6 g ledger row = 0.9 m 50 mm + buckle + 0.8 m 25 mm stabilizers + 2 ladder locks (build_geometry recipe)
    row = next(r["g"] for r in L.parts("corrie_b2_h1_c", "M") if r["id"].startswith("belt:50_mm_belt_webbing"))
    recipe = 0.9 * 38 + load("buckle_side_release_50mm").require("mass_g") + D.stabilizers_g()
    assert row == pytest.approx(recipe, abs=0.1)
    # the 2:1 needs more 25 mm than booked (a correction, not only a cut), legs positive at the smallest waist
    assert c["need_25_m"] > 0.6 and c["leg_min_mm"] > 0
    assert c["tail_at_min_mm"] >= D.TAIL_MIN_MM
    for s in ("S", "M", "L", "XL", "XXL"):
        assert D.closure(s)["delta_g"] < 0


def test_38mm_buckle_rejected_on_rev_c():
    r = next(i for i in D.study()["items"] if i["key"] == "a1")
    assert r["verdict"] == "REJECT"
    assert load("buckle_side_release_38mm").require("breaking_strength_n") < D._c2_T()


def test_front_strap_scales_inverse_width():
    fs = {f["width_mm"]: f for f in D.study()["front_strap"]}
    assert fs[38.0]["median_kpa"] == pytest.approx(fs[50.0]["median_kpa"] * 50 / 38, rel=0.02)


def test_hdpe_mass_scales_and_gap_shortens():
    b = D.hdpe_mass_g(D.B)
    assert 35 < b < 41.5                               # developed, below the 41.0 g gap-free booking
    assert D.hdpe_mass_g(D.DESIGNS["c2"]()) == pytest.approx(0.75 * b, rel=1e-6)
    assert D.hdpe_mass_g(D.B, phi=0.3) == pytest.approx(0.7 * b, rel=1e-6)
    assert D.hdpe_mass_g(D.DESIGNS["c1"]()) < b


def test_gates_and_package():
    st = D.study()
    for r in st["items"]:
        if r["in_package"]:
            assert r["verdict"] == "PASS", r
            assert r["worst_wing_kpa"] <= D.WING_WORST_LIMIT and r["worst_hold"] >= D.HOLD_WORST_LIMIT
        if r["verdict"] == "REJECT" and r["key"] != "a1":
            assert r["worst_wing_kpa"] > D.WING_WORST_LIMIT or r["worst_hold"] < D.HOLD_WORST_LIMIT
    pk = st["package"]
    e = pk["eval"]
    assert e["worst_wing_kpa"] <= D.WING_WORST_LIMIT and e["worst_hold"] >= D.HOLD_WORST_LIMIT
    assert e["min_asis_clear_mm"] >= st["baseline"]["min_asis_clear_mm"]
    # base and as-hunted stated separately; holster sits only in the difference
    assert pk["as_hunted_g"] - pk["base_g"] == pytest.approx(D.holster_split()["addon_g"], abs=0.15)
    assert pk["base_g"] <= D.TARGET_G
    assert pk["base_g"] == pytest.approx(st["masses"]["base_g"] + pk["physical_delta_g"], abs=0.1)
    assert pk["delta_g"] == pytest.approx(sum(r["g"] for r in st["items"] if r["in_package"]), abs=0.1)
    # every size gets lighter, and S..XXL base masses rise with size
    ps = st["per_size"]
    assert all(v["base_pkg_g"] < v["base_today_g"] for v in ps.values())
    sizes = list(ps)
    assert all(ps[a]["base_pkg_g"] < ps[b]["base_pkg_g"] for a, b in zip(sizes, sizes[1:]))


def test_softer_wedge_loses_taper():
    f = D.wedge_taper_factor()
    assert 0.5 < f < 1.0
    assert D.wedge_taper_factor(0.0) == pytest.approx(1.0)
