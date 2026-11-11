"""BL-013 whole-pack weight roll-up v2: start reconciles to the ledger, scenarios stay separate, every bar traces to
a ticket's code, the clean-ups are resolved against their sources.

    python -m pytest -q tests/test_weight_rollup_v2.py
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "designs" / "pack_5200"
for p in (str(ROOT), str(PACK), str(PACK / "concepts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import weight_rollup_v2 as W  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402


@pytest.mark.parametrize("size", L.SIZES)
def test_start_reconciles_to_the_ledger_at_every_belt_size(size):
    rows = W.b2_rows(size)
    assert W.cfg_total(rows, "meat_trip") == pytest.approx(L.total("corrie_b2_h1", size), abs=0.15)
    # base < as hunted < meat trip, and the holster is the only suspension add-on
    assert W.cfg_total(rows, "base") < W.cfg_total(rows, "as_hunted") < W.cfg_total(rows, "meat_trip")
    sus_addons = [r for r in rows if r["system"] in L.SUSPENSION and r["cfg"] != "base"]
    assert [r["name"][:5] for r in sus_addons] == ["IMP-3"]


def test_scenarios_are_kept_separate():
    for scen in W.SCEN:
        allowed = W.SCEN[: W.SCEN.index(scen) + 1]
        steps = {r["step"] for r in W.scenario_rows(scen)} - {"start"}
        assert steps, scen
        for s in steps:
            assert W.STEP_META[s][0] in allowed, (scen, s)
    p_steps = {r["step"] for r in W.scenario_rows("P")}
    assert not any(W.STEP_META[s][0] == "A" for s in p_steps if s != "start")   # no after-tests saving in proven now
    t = W.scenario_table()
    assert t["B.2"]["base"] > t["P"]["base"] > t["A"]["base"]


def test_waterfall_closes_and_every_bar_is_a_step():
    st = W.step_deltas("M")
    t = W.scenario_table("M")
    run = t["B.2"]["base"]
    for sc in W.SCEN:
        run += sum(st[k]["base"] for k in W.ORDER if W.STEP_META[k][0] == sc)
        assert run == pytest.approx(t[sc]["base"], abs=0.3), sc
    for k, rows in W.steps("M").items():
        assert rows, k
        assert all(r["source"] and r["system"] in L.SYSTEMS and r["cfg"] in W.CFGS for r in rows), k


def test_cleanups_resolved_against_sources():
    led = {r["name"]: r["g"] for r in L.parts("corrie_b2_h1", "M")}
    st = W.step_deltas("M")
    assert st["C1"]["base"] == pytest.approx(-led["attachment: printed fairleads (8)"])
    assert st["C2"]["base"] == pytest.approx(-led["attachment: B-01 swell patches"])
    cw = W.corner_wraps()
    assert 15.0 < cw["wraps_g"] < 20.0                    # the "about 18 g" flag of BL-017
    assert cw["unbooked_g"] == pytest.approx(cw["wraps_g"] + cw["adhesive_g"] - 2.21)
    nb = W.non_body_sources()
    assert nb["short_g"] == pytest.approx(9.1, abs=0.1)   # BL-017's 9.1 g
    assert st["C4"]["base"] == pytest.approx(-8.0)
    assert st["C6"]["base"] == pytest.approx(0.0)         # a move, not a saving
    c6 = W.steps("M")["C6"]
    assert {r["system"] for r in c6} == {"attachment", "harness"}
    assert st["C7"]["as_hunted"] == pytest.approx(0.0) and st["C7"]["base"] > 0
    assert st["C8"]["base"] == pytest.approx(W._HD().closure("M")["delta_g"], abs=0.05)


def test_ticket_steps_match_the_ticket_modules():
    F = W._F()
    st = W.step_deltas("M")
    wings = sum(p.g for p in W.wing_parts())
    # P: CORRIE F, today's fabrics, with the wing parts kept; A: wings off and the fabric swaps
    wt, wb = F.weight_table("M", "base", "D2", "today"), F.weight_table("M", "base", "D2", "B")
    assert st["P_F"]["base"] == pytest.approx(wt["bag_side_g"] - wt["corrie_b2_bag_side_g"] + wings, abs=0.3)
    assert st["A_wings"]["base"] == pytest.approx(-wings, abs=0.05)
    assert st["A_fab"]["base"] == pytest.approx(wb["bag_side_g"] - wt["bag_side_g"], abs=0.3)
    assert st["A_back"]["base"] == pytest.approx(-44.6, abs=0.1)              # BL-005 record
    assert st["P_pkgC"]["base"] == pytest.approx(L.total("corrie_b2_h1_c", "M") - L.total("corrie_b2_h1", "M"), abs=0.05)
    assert st["P_d2"]["base"] + st["P_kits"]["base"] == pytest.approx(W.crown("(a)+(d2)"), abs=0.05)
    assert st["A_c17"]["base"] < 0
    assert W.cheek_g() == pytest.approx(2 * (8.8 - 6.13104), abs=0.01)          # loadpath_check.FROZEN
    assert st["P_cheek"]["base"] == pytest.approx(W.cheek_g(), abs=0.05)
    fx = W.fixed_torso("a")
    assert fx["pack_delta_g"] == pytest.approx(3839.3 - 3927.0, abs=0.15)    # BL-007's own result at 19 in


def test_six_point_six_pounds_is_not_reached_and_the_gap_is_reported():
    t = W.scenario_table("M")
    for s in W.SCEN:
        assert t[s]["base"] > W.TARGET_G
    fc = W.feature_costs("M")
    assert fc["gap_g"] == pytest.approx(t["O"]["base"] - W.TARGET_G, abs=0.2)
    assert all(not c["frozen"] for c in fc["candidates"] if c["item"] in fc["greedy_take"])


def test_leaders_basis_and_configs():
    lf = {r["leader"]: r for r in W.like_for_like_leaders("M")}
    t = W.scenario_table("M")
    kuiu = lf["KUIU ICON 6 6000 full kit"]
    assert kuiu["A"]["ours_g"] == pytest.approx(t["A"]["base"])
    sg = lf["Stone Glacier Sky 5900 + Krux, M belt"]
    assert sg["A"]["ours_g"] < t["A"]["base"]                                  # hip pocket and sleeve removed
    cf = W.configs("M")
    assert L.total(cf["corrie_f_as_hunted"]) > L.total(cf["corrie_f_base"])
    assert L.total(cf["bl005_back"]) == pytest.approx(t["B.2"]["base"] - 44.6, abs=0.2)
    assert L.total(cf["bl007_c"]) < L.total(cf["bl007_a"])


def test_estimates_cover_every_row():
    e = W.estimates("A", "M")
    assert sum(c["g"] for c in e["classes"].values()) == pytest.approx(e["total_g"], abs=0.5)
    assert 0 < e["rss_g"] < e["worst_g"]


def test_screenshots_are_phone_sized_if_written():
    for n in (1, 2):
        p = W.SCREENS / f"{W.PREFIX}{n}.png"
        if p.exists():
            assert p.stat().st_size <= 1.5 * 1024 * 1024
