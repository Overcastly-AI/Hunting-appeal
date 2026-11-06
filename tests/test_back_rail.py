"""Back-rail skin pressure at the HA-LS-1 rev C meat case (pack-designer 2026-11-06): the record and its guardrails."""
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "designs" / "pack_5200" / "analysis" / "back_rail_results.json"


@pytest.fixture(scope="module")
def res():
    return json.loads(REC.read_text())


def test_model_reproduces_the_structural_records(res):
    """Same rail model as spreader.py: 100 / 60 mm rail gives the frame re-check's 15.4 kPa at 190 mm and the spreader
    record's 12.9 kPa at 150 mm with the same worst bone reaction."""
    from huntkit.gendesign.back_rail import CURRENT, skin
    side = res["bone_side_n"]
    assert skin(CURRENT, 190.0, side)["peak_kpa"] == pytest.approx(15.44, abs=0.1)
    assert skin(CURRENT, 150.0, side)["peak_kpa"] == pytest.approx(12.91, abs=0.1)
    assert res["confirm_current"]["skin_peak_kpa"] == pytest.approx(15.44, abs=0.1)


def test_chosen_rail_meets_14_kpa_at_rev_c_with_the_full_check(res):
    from huntkit.gendesign.back_rail import GUTTER_MIN, MARGIN_KPA, PEAK_KPA, RELEASED_KEY, released, skin
    assert res["chosen"] == RELEASED_KEY
    assert skin(released(), 190.0, res["bone_side_n"])["peak_kpa"] <= PEAK_KPA - MARGIN_KPA
    c = res["confirm"]
    assert c["e_mm"] == 190.0
    assert c["skin_peak_kpa"] <= PEAK_KPA
    assert c["clear_walk_min"] >= 3.0 and c["clear_fact_min"] >= 0.0         # spreader no-bottoming rules
    assert c["clear_walk_min"] >= res["confirm_current"]["clear_walk_min"] - 0.5
    row = next(x for x in res["rows"] if x["rail"]["key"] == RELEASED_KEY)
    assert row["gutter_mm"] >= GUTTER_MIN
    # it is the lightest build that meets the rule
    assert all(x["delta_g"] >= row["delta_g"] - 1e-6 for x in res["rows"] if x["eligible"])


def test_backer_is_needed_and_foam_alone_does_not_fix_it(res):
    rows = {x["rail"]["key"]: x for x in res["rows"]}
    assert rows["r100_nobacker"]["peak_kpa"] > 30.0
    for k in ("r100_b60_f12", "r100_b60_f14", "r100_b60_f16", "r100_b60_eva", "r100_b60_eva30"):
        assert rows[k]["peak_kpa"] > 14.0


def test_panels_carry_the_released_rail():
    from huntkit.gendesign.back_rail import back_panel_pieces, mass_g, released
    d = back_panel_pieces()
    P = {p["id"]: p for p in yaml.safe_load((ROOT / "designs/pack_5200/panels.yaml").read_text())["panels"]}
    assert P["BP-02"]["approx_size_mm"] == [d["rail_w"], d["rail_l"]] and P["BP-02"]["qty_total"] == 2
    assert P["BP-08"]["approx_size_mm"] == [d["backer_w"], d["backer_l"]] and P["BP-08"]["qty_total"] == 2
    assert P["BP-05"]["approx_size_mm"][0] == d["sleeve_w"]
    assert P["BP-01"]["approx_size_mm"][0] == d["mesh_w"]
    assert P["BP-08"]["mass_g_total"] == pytest.approx(mass_g(released())["backer_g"], rel=0.03)   # R10 corners


def test_screens_and_doc(res):
    for s in res["screens"]:
        p = ROOT / s
        assert p.exists() and p.stat().st_size <= 1.5e6
    md = (ROOT / "designs/pack_5200/analysis/back_rail.md").read_text()
    assert md.startswith("# Back-rail skin pressure at the rev C meat case")
    assert "BP-08" in md and "Pattern-maker hand-off" in md
