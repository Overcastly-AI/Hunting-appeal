"""The production frame is the carbon-tube ladder plus the kept back system."""
import json
from pathlib import Path

import pytest

from huntkit.gendesign.frame_light import pack_g, print_hours, TUBE_FRAME_G

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "designs" / "pack_5200" / "analysis" / "mass_cut_results.json"


def test_saved_ladder_meets_strength_fatigue_and_comfort():
    data = json.loads(RESULT.read_text())
    assert data["winner"] == "Carbon-tube ladder"
    assert data["sf_min"] >= 1.0
    assert data["sf_fatigue"] >= 1.0
    assert data["peak_kpa"] <= 14.0
    assert data["spread_mm"] >= 40.0
    assert data["pack_lb"] < 6.0
    for name, sf in data["cases"].items():
        assert sf >= 1.0, name
    # the cases that were under 1.0 on the lumpy 4 mm mesh
    assert data["cases"]["single_stay_setdown"] >= 1.0
    assert data["cases"]["hipbelt_off_abuse"] >= 1.0
    assert data["cases"]["drop_2p5g"] >= 1.0


def test_hollow_stay_that_misses_fatigue_is_not_chosen():
    data = json.loads(RESULT.read_text())
    thin = next(r for r in data["rows"] if "OD 26" in r["name"])
    assert not thin["passes"]
    assert thin["sf_fatigue"] < 1.0
    assert data["pack_g"] < thin["pack_g"]


def test_pack_mass_is_soft_goods_plus_frame_plus_foam():
    data = json.loads(RESULT.read_text())
    frame = TUBE_FRAME_G + 193.44
    assert data["frame_g"] == pytest.approx(frame, abs=0.1)
    assert data["pack_g"] == pytest.approx(pack_g(frame, 16.22), abs=0.1)


def test_rack_print_is_about_an_hour_and_a_half():
    assert print_hours(44.0) == pytest.approx(1.56, abs=0.05)
