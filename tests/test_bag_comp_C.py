"""Team C (OPEN) TAILGATE: geometry, mass bookkeeping, access and the result file (no cloth sim, no render)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "bag_comp" / "C"))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import tailgate as TG  # noqa: E402


@pytest.fixture(scope="module")
def nums():
    return TG.numbers()


def test_envelope_unchanged(nums):
    c = TG.make()
    assert 2 * float(c.a([c.z_c])[0]) <= 394.0 + 1e-6          # width <= 15.5 in
    assert max(float(c.depth([z])[0]) for z in range(35, 737, 10)) <= 305.0   # depth <= 12 in
    assert abs(nums["fill_height_in"] - 40.2) < 0.1


def test_lid_opens_wider_than_corrie(nums):
    for k in ("im1", "im2", "im3", "floor"):
        r = nums["reach"][k]
        assert r["tailgate_clear_mm"] > r["corrie_door_clear_mm"] + 60
    assert nums["opening_m2"]["tailgate_lid"] > 1.4 * nums["opening_m2"]["corrie_door"]


def test_zip_and_lid_geometry():
    c = TG.make()
    lid, band, L = TG.lid_face(c)
    assert 1500 < L < 1700                                     # inverted U, #10, ~1.59 m
    zk, s, a = TG.BC.front_face_profile(c)
    # the lid hinge edge is the full floor width plus the ease
    assert abs(lid.edge_length("hinge") - (2 * a[0] + TG.LID["ease_mm"])) < 1.0
    assert TG.LID["z_top"] + 30 <= TG.CO.B22_Z                 # B-22 tabs stay on the hinge band, clear of the zip


def test_mass_bookkeeping(nums):
    bs, cb = nums["bag_system"], nums["corrie_b2_bag_system"]
    assert abs(cb["total_g"] - (cb["body_group_g"] + cb["pockets_g"] + cb["fly_g"])) < 0.2
    assert 650 < cb["total_g"] < 760                           # CORRIE B.2, same definition
    assert abs(nums["pack_mass_M_g"] - (3943.0 - cb["total_g"] + bs["total_g"])) < 0.2
    # no wings, no door surround in TAILGATE
    ids = {p[0] for p in nums["pieces_list"]}
    assert not ids & {"M-01", "SH-06", "B-02u", "B-02door"}
    assert {"B-02L", "B-02h", "SH-09", "SH-07"} <= ids


def test_hoop_ease_beats_strap_stretch():
    h = TG.hoop_check()
    assert h["ease"]["strap_stretch_mm"] < h["ease"]["ease_mm"]
    assert h["zip_crosswise_n_mm"] > 30


def test_result_json_schema():
    f = ROOT / "designs" / "pack_5200" / "bag_comp" / "C" / "result.json"
    if not f.exists():
        pytest.skip("result.json not written yet")
    r = json.loads(f.read_text())
    for k in ("team", "name", "one_line", "bag_system_g", "pack_mass_M_g", "volume_L", "fill_height_in", "pieces",
              "curved_seams", "zip_mm_total", "beginner_hours", "cg_fill_mm", "cg_meat_mm", "cg_method",
              "access_misses", "features", "risks", "screenshots"):
        assert k in r, k
    assert set(r["cg_fill_mm"]) == {"15", "19", "23"} and set(r["cg_meat_mm"]) == {"15", "19", "23"}
    assert all(v <= 205 for v in r["cg_fill_mm"].values())
    assert all(v <= 190 for v in r["cg_meat_mm"].values())
    assert set(r["access_misses"]) == {"day", "elk6", "sheep8"}
    assert 82.2 <= r["volume_L"] <= 88.2
