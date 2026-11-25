"""BL-075: H1-P hip through-bolt stack clearance (designs/pack_5200/iter1/system/bl075_hip_clearance.py)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "designs" / "pack_5200" / "iter1" / "system" / "bl075_hip_clearance.py"


@pytest.fixture(scope="module")
def res():
    spec = importlib.util.spec_from_file_location("bl075_hip_clearance", MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.run()


def test_stack_geometry_matches_bl073(res):
    p = res["planes"]
    assert p["back_y"] - p["face_y"] == pytest.approx(22.0, abs=0.2)        # boss depth
    assert res["stack"]["aft_mm"] == pytest.approx(10.0, abs=0.01)           # ring 2 + nut 4 + 4 proud
    assert res["stack"]["tip_y"] == pytest.approx(p["back_y"] + 10.0, abs=0.01)


def test_aft_points_away_from_wearer(res):
    w = res["wearer"]
    assert w["tail_tip_y"] > w["flat_back_y"] > w["mount_face_y"]           # tails on the +y (bag) side
    assert w["solid_between_tails_and_wearer_side_mm"] >= 25.0
    assert w["heads_below_hub_face_mm"] > 20.0


def test_clears_frame_and_bag(res):
    f, b = res["frame"], res["bag"]
    assert f["keeper"]["min_mm"] > 0.5 and f["nuts"]["min_mm"] > 1.0 and f["tails"]["min_mm"] > 3.0
    assert b["spreader"]["gap_factored_mm"] > 15.0
    assert b["b01"]["gap_mm"] > 30.0
    assert b["b01"]["strain_needed_arc"] > 5 * b["b01"]["strain_cap"]         # B-01 cannot bulge that deep
    assert all(res["clears"].values())


def test_screw_length_and_fix(res):
    pb = res["protrusion"]
    assert pb["shortest_standard_ok"] == 35                                  # M5 x 30 does not reach 2 threads
    assert pb["standard"]["M5x35"]["min_proud_mm"] >= pb["need_proud_mm"]
    assert res["fix"] == "none (keep M5 x 35, no part)"
    assert res["fixes"][res["fix"]]["g"] == 0.0
    assert res["fixes"]["8 TPU push-on caps"]["g"] < res["fixes"]["keeper grown into a closed cover (PPA-CF)"]["g"]
