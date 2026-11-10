"""Team B LEAN (FELL) bag-competition entry: mass booking, build rules, fixed-list checks, result.json."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEAN = ROOT / "designs" / "pack_5200" / "bag_comp" / "lean"
sys.path.insert(0, str(LEAN))

import fell as F  # noqa: E402


@pytest.fixture(scope="module")
def cmp():
    return F.comparison()


def test_corrie_baseline_booked_by_same_code(cmp):
    c = cmp["corrie_b2"]
    assert c["total_g"] == pytest.approx(716.5, abs=1.0)        # body 533.1 + IMP-1/2/4/8 124.3 + fly 53.2 + F-02 5.9
    assert c["body"]["total"] == pytest.approx(533.1, abs=0.5)


def test_fell_lighter_in_every_config(cmp):
    for k, v in cmp["configs"].items():
        assert v["vs_corrie_g"] < -100, k
    assert cmp["configs"]["day"]["total_g"] < cmp["configs"]["max"]["total_g"]


def test_width_depth_and_fixed_interface():
    v = F.volumes()
    assert v["width_max_mm"] <= 394.0
    assert v["max_depth_mm"] <= 12 * 25.4
    assert v["z_collar"] == pytest.approx(736.3)
    b = F.build()
    ids = {p.piece_id for p, _ in b.pieces}
    assert {"B-01", "B-06f", "B-13x"} <= ids                     # ULTRA frame face + collar strip, fairlead swells
    mats = {p.piece_id: p.material_id for p, _ in b.pieces}
    assert mats["B-01"] == "challenge_ultra_200" and mats["B-06f"] == "challenge_ultra_200"
    assert mats["B-03"] == F.UG and mats["B-06"] == F.R70 and mats["B-05"] == F.U200


def test_build_rules():
    s = F.system("max")
    assert s["curved_seams"] == 0
    assert len(F.build().zips) == 1 and F.build().zips[0]["corners"] == 0
    assert s["zip_mm"] == pytest.approx(540 + 260)


def test_no_hook_and_loop_anywhere():
    txt = (LEAN / "fell.py").read_text().lower()
    assert "velcro" not in txt and "hook_and_loop" not in txt


def test_result_json_schema():
    r = json.loads((LEAN / "result.json").read_text())
    keys = ("team name one_line bag_system_g pack_mass_M_g volume_L fill_height_in pieces curved_seams zip_mm_total "
            "beginner_hours cg_fill_mm cg_meat_mm cg_method access_misses features risks screenshots").split()
    for k in keys:
        assert k in r, k
    assert 82.0 <= r["volume_L"] <= 88.0
    for t in ("15", "19", "23"):
        assert r["cg_fill_mm"][t] <= 205.0 and r["cg_meat_mm"][t] <= 190.0
    assert r["bag_system_g"] == pytest.approx(F.system("max")["total_g"], abs=0.5)
