"""HA-LS-1 rev C production verification (designs/pack_5200/analysis/rev_c_verification.md): the recorded run is
complete, every load-path check passes on the released parts, the as-built crown is what needed the fix, and the
frame-mass record the weight budget reads adds up."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "designs" / "pack_5200" / "analysis"
RESULTS = AN / "rev_c_verification_results.json"
MASS = AN / "frame_mass_production.json"


@pytest.fixture(scope="module")
def rec():
    if not RESULTS.exists():
        pytest.skip("run python -m huntkit.gendesign.rev_c_verification first")
    return json.loads(RESULTS.read_text())


def test_every_rev_c_check_passes(rec):
    parts = {r["part"] for r in rec["summary"]}
    assert {"printed body", "carbon crown (fixed)", "torso adjust", "attachments", "spreader 7 mm core"} <= parts
    bad = [r for r in rec["summary"] if r["margin"] < 1.0]
    assert not bad, bad
    # both couple variants and all three torsos were run
    assert set(rec["body"]) == {"C", "C_im3"}
    torsos = {r["torso"] for r in rec["body_rows"]}
    assert torsos == {15.0, 19.0, 23.0}
    assert {r["case"] for r in rec["body_rows"] if r["scenario"] == "C"} >= {"meat_straps", "overload_haul",
                                                                            "hipbelt_off_abuse", "tall_load_posts"}


def test_fix_is_what_makes_the_crown_pass(rec):
    from huntkit.gendesign import frame_cg_recheck as R
    for tg in ("C", "C_im3"):
        assert R.crown_pass(rec["crown"][tg])[0]
    assert not R.crown_pass(rec["crown"]["C_asbuilt"])[0]          # spine 0.96 as built
    assert not R.crown_pass(rec["crown"]["C_im3_asbuilt"])[0]      # legs 0.86 as built
    assert rec["crown"]["C_asbuilt"]["crown_spine"]["sf"] < 1.0 <= rec["crown"]["C"]["crown_spine"]["sf"]


def test_corner_bond_fatigue_was_run(rec):
    for tg in ("C", "C_im3"):
        f = rec["corner_bond_fatigue"][tg]["static_carry"]
        assert f["peak"]["sf_peak"] >= 1.0 and f["avg"]["sf_avg"] >= f["peak"]["sf_peak"]
    # the thicker bondline lowers the elastic peak: the fixed crown's peak fatigue SF beats the as-built one
    assert (rec["corner_bond_fatigue"]["C_im3"]["static_carry"]["peak"]["sf_peak"]
            > rec["corner_bond_fatigue"]["C_im3_asbuilt"]["static_carry"]["peak"]["sf_peak"])


def test_rev_c_is_harsher_than_rev_b_for_the_body(rec):
    """Same body, same engine: the rev C C8 margin is below the rev B record (1.69, frame_cg_recheck.md)."""
    b = json.loads((AN / "frame_cg_recheck_results.json").read_text())["body"]["a"]
    assert rec["body"]["C"]["sf_min"] < b["sf_min"]
    assert rec["body"]["C"]["cases"]["meat_straps"]["sf"] < b["cases"]["meat_straps"]["sf"]


def test_spreader_7mm_passes_the_sheet_checks_and_6mm_does_not(rec):
    sp = rec["spreader"]
    assert sp["key"] == "sw110c7d" and sp["meat_cg_mm"] == 190.0
    c = sp["chosen"]
    assert all(c["checks"][k] for k in ("fpf", "fatigue", "sandwich_local", "no_bottoming"))
    assert not sp["c6"]["checks"]["fatigue"]                         # 6 mm core fails fatigue at 190 mm
    assert c["mass_g"] - sp["c6"]["mass_g"] == pytest.approx(8.7, abs=0.3)


def test_frame_mass_record_adds_up():
    m = json.loads(MASS.read_text())
    assert m["frame_g"] == pytest.approx(m["printed_body_g"] + m["non_body_g"] + m["crown_fix_g"], abs=0.11)
    assert m["printed_body_g"] == pytest.approx(823.0, abs=1.0)
    assert m["crown_fix_g"] == pytest.approx(22.0, abs=0.1)
    assert sum(m["crown_fix_lines_g"].values()) == pytest.approx(m["crown_fix_g"], abs=0.1)


def test_weight_budget_reads_the_frame_mass_record():
    import yaml
    m = json.loads(MASS.read_text())
    w = yaml.safe_load((ROOT / "designs" / "pack_5200" / "geometry.yaml").read_text())["weight"]
    row = next(r for r in w["rows"] if r["group"].startswith("frame"))
    assert row["mass_g"] == pytest.approx(m["frame_g"], abs=0.05)
    assert "frame_mass_production.json" in row["basis"]
    sp = json.loads((AN / "spreader_results.json").read_text())
    srow = next(r for r in w["rows"] if r["group"].startswith("back-system spreader"))
    assert srow["mass_g"] == pytest.approx(sp["chosen"]["mass_g"], abs=0.05)
