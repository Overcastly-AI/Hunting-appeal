"""CORRIE B.1 whole-pack weight pass (designs/pack_5200/weight_pass_corrie.py): the breakdown re-books every part and
must reproduce corrie.weight_table(); cuts carry every field the pass promises; packages are computed, not typed."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "designs" / "pack_5200", ROOT / "designs" / "pack_5200" / "concepts"):
    sys.path.insert(0, str(p))

import corrie as CO  # noqa: E402
import weight_pass_corrie as WP  # noqa: E402


@pytest.fixture(scope="module")
def run():
    return WP.run(write=False)


def test_breakdown_reproduces_weight_table(run):
    wt = CO.weight_table("M", spec="B.1")             # the pass is computed on B.1 (every cut is defined on it)
    assert run["total_g"] == wt["total_g"]
    assert sum(p["g"] for p in run["parts"]) == pytest.approx(wt["total_g"], abs=0.05)
    assert sum(run["groups"].values()) == pytest.approx(wt["total_g"], abs=0.2)
    # the only balancing row is a few grams of SPINE-body booking basis, not a hidden total
    assert abs(run["reconciliation_g"]) < 10.0
    assert sum(1 for p in run["parts"] if p["group"] == WP.G_REC) == 1


def test_breakdown_is_part_level_and_sourced(run):
    parts = [p for p in run["parts"] if p["group"] != WP.G_REC]
    assert len(parts) > 80
    assert all(p["source"] and p["g"] != 0 for p in parts if abs(p["g"]) > 0.05)
    fm = WP._json("frame_mass_production.json")
    frame = sum(p["g"] for p in parts if p["group"].startswith("Frame"))
    assert frame == pytest.approx(fm["frame_g"], abs=0.1)
    # SPINE side pockets, the PA66 plate and the diagonal zip are gone; CORRIE's door zip is in
    names = " ".join(p["part"] for p in parts)
    assert "floating side pockets" not in names and "diagonal zip" not in names and "pa66_gf30 / POM" not in names
    assert "horseshoe door zip" in names


def test_group_pareto_sorted_and_frame_first(run):
    vals = [v for k, v in run["groups"].items() if k != WP.G_REC]
    assert vals == sorted(vals, reverse=True)
    assert next(iter(run["groups"])).startswith("Frame")


def test_every_cut_has_the_promised_fields(run):
    need = {"g", "usd", "hours", "durability", "quiet", "ip", "load_path", "confidence", "rec", "pkg"}
    cl = run["cuts"]
    assert len(cl) >= 25
    for x in cl:
        assert need <= set(x), x["id"]
        assert x["g"] > 0, x["id"]
    # package rules: A and B never touch a load path; every C item states one
    for x in cl:
        lp = x["load_path"].lower()
        if x["pkg"] in "AB":
            assert not lp.startswith("yes"), x["id"]
        if x["pkg"] == "C":
            assert lp.startswith(("yes", "comfort")), x["id"]


def test_packages_are_cumulative_and_honest(run):
    pk = run["packages"]
    steps = pk["steps"]
    assert [s["pkg"] for s in steps] == ["A", "B", "C"]
    cur = pk["start_real_g"]
    for s in steps:
        cur -= s["saved_real_g"]
        assert s["after_real_g"] == pytest.approx(cur, abs=0.2)
        assert s["saved_real_g"] > 0
    assert pk["start_real_g"] > run["total_g"]                # booking gaps make the real pack heavier
    # the target is not reachable with A+B+C, nor with the T items on top (stated in the report)
    assert steps[-1]["after_real_g"] > CO.TARGET_G
    assert pk["after_all_take_g"] > CO.TARGET_G
    assert pk["frame_plus_spreader_needed_g"] < pk["frame_plus_spreader_now_g"] / 2


def test_pouch_variants_match_corrie_booking(run):
    body = WP.C.build(WP.C.make(), True, spec="B.1")
    booked = sum(WP.BC.piece_mass_g(p) for p, g in body.pieces if g == "pouch")
    booked += next(WP.BC.zip_mass_g(z) for z in body.zips if "pouch" in z["name"])
    booked += sum(g for n, g in body.extra["hardware"] if n.startswith("pouch"))
    assert WP.pouch_mass()["g"] == pytest.approx(booked, abs=0.2)
    assert run["pouch_combo"]["g"] < WP.pouch_mass()["g"]


def test_benchmarks_are_cited(run):
    for r in run["benchmarks"]:
        for _lab, g, url in r["bench"]:
            assert url.startswith("https://") and g > 0


def test_b2_is_applied_from_the_corrie_table(run):
    """Owner 2026-11-09: A + B (without held B-8 / B-9) = corrie spec B.2; the waterfall's after-A+B bar and the size
    table are corrie.weight_table(size, spec="B.2"), C is a projection on top."""
    b2 = run["packages"]["b2"]
    assert b2["spec"] == "B.2" and set(b2["items"]) == set(CO.SPECS["B.2"]["items"])
    assert {"B-8", "B-9"}.isdisjoint(b2["items"])
    assert not any(i.startswith("C-") for i in b2["items"])
    for s, r in b2["sizes"].items():
        assert r["b2_g"] == CO.weight_table(s, spec="B.2")["total_g"]
        assert r["b1_g"] == CO.weight_table(s, spec="B.1")["total_g"]
        assert r["with_c_g"] == pytest.approx(r["b2_g"] - b2["c_saving_g"], abs=0.05)
    steps = {s["pkg"]: s for s in run["packages"]["steps"]}
    assert set(steps["B"]["items"]) == {i for i in CO.SPECS["B.2"]["items"] if i.startswith("B-")}
    # the B.2 booking and the package arithmetic agree within a few grams (pull tab, zip length)
    assert abs(b2["recon_vs_packages_g"]) < 5.0


def test_stored_spine_outer_area_matches_the_cut_set():
    assert CO.SPINE_OUTER_M2 == pytest.approx(WP._spine_outer_area(), abs=5e-4)
