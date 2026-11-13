"""BL-004 attachment diet: masses from the ledger, scenarios, procedures and the stored sim results."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import attach_diet as AD  # noqa: E402


@pytest.fixture(scope="module")
def mt():
    return AD.mass_table()


def test_today_is_the_ledger_attachment_system(mt):
    from huntkit.mass import ledger as L
    assert mt["today_g"] == pytest.approx(L.by_system(AD.CONFIG, AD.SIZE)["attachment"], abs=0.05)


def test_unit_masses_rebuild_their_ledger_rows():
    u = AD.unit_masses()
    rows = AD.ledger_rows()
    g = lambda n: AD._row(rows, n)["g"]  # noqa: E731
    assert 4 * u["bag_hook"] == pytest.approx(g("bag hooks, 38 mm Al") + g("bag hooks 1500 N -> 2200 N"))
    assert u["bag_hook"] == pytest.approx(14.0, abs=0.05)          # attach_system.HOOK_RATED_G
    assert u["b17_pair"] + u["b18_pair"] == pytest.approx(g("bag-side load spreaders"))
    assert u["hood_family"] == pytest.approx(24.3 + 3.9 + 0.6 + 20.0 + 10.3 + 1.6, abs=0.05)


def test_variant_masses_are_ledger_minus_changes(mt):
    for v, r in mt["variants"].items():
        assert r["attachment_g"] == pytest.approx(mt["today_g"] + sum(c[1] for c in r["changes"]), abs=0.06)
    assert mt["variants"]["V0"]["delta_g"] == 0.0
    # every deletion is a deletion, and the IM2 cut is two hooks + two tongues + B-23 + sleeves + keepers
    c = dict((n, g) for n, g, _ in mt["variants"]["C_im2"]["changes"])
    assert c["IM2 bag hooks x2 (rated 38 mm)"] == pytest.approx(-28.0, abs=0.05)
    assert sum(c.values()) < -40


def test_recommendation_meets_the_220_goal_but_not_the_stretch(mt):
    rec = mt["variants"]["REC"]
    assert rec["attachment_g"] <= AD.TARGET_G
    assert rec["attachment_g"] > AD.STRETCH_G
    # D moves a hook to the B-24 link (straps_meat): the net pack saving is smaller than the attachment saving
    d = mt["variants"]["D_loops"]
    assert d["net_pack_delta_g"] > d["delta_g"]


def test_bag_off_times():
    t = {v: AD.procedures(v)["seconds"] for v in AD.VARIANTS}
    assert t["V0"]["bag_off"] == 85          # BL-003 REC count (strap_architecture.md 5)
    assert t["V0"]["bag_on"] == 92
    assert t["REC"]["bag_off"] <= AD.BAG_OFF_LIMIT_S
    assert t["REC"]["bag_off"] < t["V0"]["bag_off"]
    assert not AD.procedures("D_loops")["r08_pass"]   # the IM3 eye swap breaks R-08


def test_scenarios_merge_as_intended():
    from huntkit.clothsim.pack import load_scenario
    AD.write_scenarios()
    for t in AD.TORSOS:
        rec = load_scenario(str(AD.scenario_path("REC", t)))
        assert rec["bag"] == "corrie"
        assert rec["attachments"]["pocket"]["enabled"] is False
        assert rec["attachments"]["hooks"]["stations"] == [520]
        assert [x["id"] for x in rec["attachments"]["ties"]["list"]] == ["TG_R", "TG_L"]
        assert rec["contact"]["smooth_mm"] == 6.0          # corrie_PR{t}c rounding kept
        v0 = load_scenario(str(AD.scenario_path("V0", t)))
        assert v0["attachments"]["pocket"]["enabled"] is True
        assert v0["attachments"]["hooks"]["stations"] == [330, 520]
        lo = load_scenario(str(AD.scenario_path("B_loops", t)))
        assert [x["id"] for x in lo["attachments"]["ties"]["list"]] == ["TG_R", "TG_L", "CT_R", "CT_L"]
        assert lo["attachments"]["ties"]["list"][2]["anchor"][2] == rec["contact"]["crown"]["top_z"]
        none = load_scenario(str(AD.scenario_path("M_notop", t)))
        assert none["attachments"]["ties"]["list"] == []


def test_inventory_covers_every_ledger_row_and_flags():
    inv = AD.inventory()
    assert inv["total_g"] == pytest.approx(AD.mass_table()["today_g"], abs=0.05)
    names = {r["name"]: r for r in inv["rows"]}
    assert len(names) == len(AD.ledger_rows())
    assert all(r["no_load"] for n, r in names.items() if "keepers" in n or "swell" in n or "TPU" in n)
    hood = next(r for n, r in names.items() if "crown hood B-19" in n)
    assert hood["over_2x"] and hood["per_case_factored_n"]["meat_straps"] == pytest.approx(158, abs=1)


_RES = AD.load_results()["rows"]


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_every_simulated_variant_has_15in_runs_on_both_shells():
    for v, meta in AD.VARIANTS.items():
        for s in AD.SHELLS:
            r = AD.get(v, s, 15)
            assert r is not None, (v, s)
            assert r["mesh_h"] == 40


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_recommendation_does_not_worsen_the_15in_meat_cg():
    for s in AD.SHELLS:
        rec, v0 = AD.get("REC", s, 15), AD.get("V0", s, 15)
        assert rec["cases"]["meat"]["converged"]
        assert rec["cases"]["meat"]["cg_y"] <= AD.LIMIT["meat"]
        assert rec["cases"]["fill"]["cg_y"] <= AD.LIMIT["fill"]
        # never worse than the same-session control by more than the 2 mm re-run scatter (shell_sweep.md section 2)
        assert rec["cases"]["meat"]["cg_y"] <= v0["cases"]["meat"]["cg_y"] + 2.0
    # the merged bag's shell (S15): not worse than its own control; CORRIE: not worse than the ticket's 184.4 mm
    assert AD.get("REC", "S15", 15)["cases"]["meat"]["cg_y"] <= AD.get("V0", "S15", 15)["cases"]["meat"]["cg_y"]
    assert AD.get("REC", "CORRIE", 15)["cases"]["meat"]["cg_y"] <= AD.TODAY_MEAT_15


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_hood_carries_nothing_at_15in_so_deleting_it_changes_nothing():
    for s in AD.SHELLS:
        v0, bg = AD.get("V0", s, 15), AD.get("B_guys", s, 15)
        assert max(v0["cases"][c]["loads_1g"].get("pocket", 0.0) for c in ("fill", "meat")) == 0.0
        for c in ("fill", "meat"):
            assert bg["cases"][c]["cg_y"] == pytest.approx(v0["cases"][c]["cg_y"], abs=0.05)


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_forgetting_the_guys_breaks_the_rev_c_meat_cg():
    for s in AD.SHELLS:
        assert AD.get("M_notop", s, 15)["cases"]["meat"]["cg_y"] > AD.LIMIT["meat"]


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_load_paths_are_factored_sim_peaks():
    lp = {r["location"].split(",")[0]: r for r in AD.load_paths()}
    im3 = next(r for k, r in lp.items() if k.startswith("IM3"))
    peak = max(AD.peak_1g("REC", ("hook_im520_R", "hook_im520_L"))[0],
               AD.peak_1g("M_notop", ("hook_im520_R", "hook_im520_L"))[0])
    assert im3["factored_n"] == pytest.approx(AD.FACTOR * peak, abs=1)


def test_heavy_guy_lock_sensitivity_is_record_based(mt):
    from huntkit.materials import load
    d = 2 * (float(load("ladder_lock_25mm_heavy").require("mass_g")) - float(load("ladder_lock_25mm").require("mass_g")))
    for v, r in mt["variants"].items():
        assert r["with_heavy_guy_locks_g"] == pytest.approx(r["attachment_g"] + d, abs=0.06)
    # honest edge: with the heavy locks REC misses 220 g by under a gram. History: 220.7 (BL-004); 218.1 after the
    # BL-034 toggle / tri-glide records (-2 x 1.3 g toggles, guy and lifter tri-glides); BL-035: 220.3 g, the six
    # elastic hook keepers on the elastic_25mm record (+0.75 g each; REC keeps 4 of the 6: +3.0 g) and the lifter
    # tri-glide ledger row on the triglide_25mm record (2 x 2.6 g, was 2 x 3.0: -0.8 g) = +2.2 g
    assert mt["variants"]["REC"]["with_heavy_guy_locks_g"] == pytest.approx(220.3, abs=0.1)
    assert mt["variants"]["REC"]["with_heavy_guy_locks_g"] > AD.TARGET_G


@pytest.mark.skipif(not _RES, reason="no stored attach_diet sims")
def test_r28_at_23in_s15_still_fails_with_rec():
    assert not AD.get("V0", "S15", 23)["r28"]["meat"]["pass"]
    assert not AD.get("REC", "S15", 23)["r28"]["meat"]["pass"]
    assert not AD.get("V0", "CORRIE", 23)["r28"]["meat"]["pass"]
    assert AD.get("REC", "CORRIE", 23)["r28"]["meat"]["pass"]
