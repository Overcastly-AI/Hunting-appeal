"""Back-comfort criterion and the smooth-frame safety factors."""
import json
from pathlib import Path

import pytest

from huntkit.gendesign.frame_smooth import PEAK_KPA, options, choose_back

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "designs" / "pack_5200" / "analysis" / "back_comfort_results.json"


def test_current_sheet_fails_the_pressure_limit():
    rows = options()
    current = rows[0]
    assert "UHMWPE" in current["name"]
    assert current["peak_kpa"] > PEAK_KPA
    assert not current["passes"]


def test_open_window_fails_a_bone_between_the_stays():
    rows = options()
    rails = next(r for r in rows if r["name"].startswith("Stay pads only"))
    assert rails["peak_kpa"] > PEAK_KPA
    assert not rails["passes"]


def test_alloy_sheet_meets_pressure_and_fails_on_yield():
    rows = options()
    alloy = next(r for r in rows if r["name"].startswith("6061"))
    assert alloy["peak_kpa"] <= PEAK_KPA
    assert alloy["sf"] < 1.3
    assert not alloy["passes"]


def test_chosen_back_meets_the_pressure_limit():
    winner = choose_back(options())
    assert winner["passes"]
    assert winner["peak_kpa"] <= PEAK_KPA
    assert winner["spread_mm"] >= 40.0
    assert "carbon" in winner["name"].lower() or "QI" in winner["name"]


def test_smooth_frame_cases_and_fatigue():
    data = json.loads(RESULT.read_text())
    assert data["sf_fatigue"] >= 1.0
    assert data["sf_min"] >= 1.0
    for name, sf in data["cases"].items():
        assert sf >= 1.0, name
    # the old coarse-mesh failures
    assert data["cases"]["single_stay_setdown"] >= 1.0
    assert data["cases"]["hipbelt_off_abuse"] >= 1.0
    assert data["cases"]["drop_2p5g"] >= 1.0
