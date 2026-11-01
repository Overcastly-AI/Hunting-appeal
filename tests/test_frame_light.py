"""Production frame is the printed branch body, not the carbon-tube ladder."""
import json
from pathlib import Path

import pytest

from huntkit.gendesign.frame_light import print_hours

ROOT = Path(__file__).resolve().parents[1]
BRANCH = ROOT / "designs" / "pack_5200" / "analysis" / "generative_branch_results.json"
TUBE = ROOT / "designs" / "pack_5200" / "analysis" / "mass_cut_results.json"


def test_branch_frame_clears_strength_fatigue_and_comfort():
    data = json.loads(BRANCH.read_text())
    assert data["winner"].startswith("Branch")
    assert data["h_mm"] == 2.0
    assert data["sf_min"] >= 1.0
    assert data["sf_fatigue"] >= 1.0
    assert data["peak_kpa"] <= 14.0
    assert data["spread_mm"] >= 40.0
    assert data["frame_g"] < 1400.0
    assert data["pack_lb"] < 7.0
    for name, sf in data["cases"].items():
        assert sf >= 1.0, name
    assert data["cases"]["hipbelt_off_abuse"] >= 1.0
    assert data["cases"]["single_stay_setdown"] >= 1.0
    assert data["cases"]["drop_2p5g"] >= 1.0


def test_tube_ladder_is_lighter_and_not_the_product():
    tube = json.loads(TUBE.read_text())
    branch = json.loads(BRANCH.read_text())
    assert tube["pack_g"] < branch["pack_g"]
    assert tube["winner"] == "Carbon-tube ladder"


def test_rack_print_is_about_an_hour_and_a_half():
    assert print_hours(44.0) == pytest.approx(1.56, abs=0.05)
