"""CORRIE (owner's pick 2026-11-07): MANTLE wings + horseshoe door + roll-top + top pouch (concepts/corrie.py)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def corrie():
    return CO.numbers()


def test_volume_width_and_pouch(corrie):
    c, b, naive, m, mn, v = corrie
    # rev B: depth scaled so the SEWN (cloth-sim) volume matches SPINE's; the flat-panel rule volume is ~76 L
    assert CO.REV == "B"
    assert 74.0 < v["volume_L"] < 78.0
    assert BC.volumes(CO.make("A"))["volume_L"] == pytest.approx(BC.TARGET_L, abs=0.05)
    assert v["width_max_in"] == pytest.approx(15.5, abs=0.05)
    assert v["max_depth_in"] <= 12.0
    # B.2 (default, weight pass B-5): 280 x 190 x 60 mm pouch, 2.7 L; B.1 (flag) keeps the 4.0 L pouch
    assert CO.SPEC == "B.2"
    assert b.extra["pouch_L"] == pytest.approx(2.71, abs=0.02)
    assert CO.build(c, True, spec="B.1").extra["pouch_L"] == pytest.approx(4.0, abs=0.1)


def test_seams_match(corrie):
    b = corrie[1]
    real = [s for s, t in b.seams if "flat" not in t and s.a[0].piece is not s.b[0].piece]
    assert check_seams(real, tol_mm=1.0).ok


def test_door_reaches_im_straps_and_clears_wing_loops(corrie):
    c = corrie[0]
    r = CO.door_reach(c)
    for k in ("im1", "im2", "im3"):
        assert r[k]["through_door"] and r[k]["clear_width_mm"] >= 200
    assert CO.DOOR["inset"] >= 40          # zip inboard of the corner seams that carry the wing-strap loops
    assert CO.DOOR["z_lo"] - BC.Z0 <= 80   # door sill close to the floor


def test_guy_tab_reconciled_with_collar_seam(corrie):
    g = CO.guy_check(corrie[0])
    assert g["clear_to_collar_seam_mm"] >= 10 and g["clear_to_door_top_mm"] >= 10


def test_optimised_beats_naive_and_keeps_interface(corrie):
    c, b, naive, m, mn, v = corrie
    assert mn["mass_g"]["total"] - m["mass_g"]["total"] > 100
    assert m["curved_seams"] <= 2
    ids = {p.piece_id for p, _ in b.pieces}
    assert {"B-01", "B-13x", "B-06f", "B-02door", "B-02u", "M-01", "L-21"} <= ids
    assert not any("hook_and_loop" in p.material_id for p, _ in b.pieces)
    zips = {z["name"]: z["length_mm"] for z in b.zips}
    assert any("#10" in k for k in zips) and any("#8" in k for k in zips)


def test_cloth_sim_estimate_inside_rev_c(corrie):
    est = CO.cloth_sim_estimate(corrie[5]["cg_y"])
    assert est["inside_rev_c"]


def test_clothsim_loader_pieces_weld_and_develop():
    from huntkit.clothsim.corrie_bag import load_corrie_patterns
    pat = load_corrie_patterns(verbose=False)
    assert set(pat["dev_ids"]) == {"B-01", "B-03", "B-02u", "B-02door", "B-02h"}
    for pid in pat["dev_ids"]:
        assert pat["pieces"][pid]["strain_p99"] < 2.0            # planar facets develop ~exactly
    assert pat["pieces"]["B-06"]["height_to_fill"] == pytest.approx(CO.make().dome_h)
    assert pat["constants"]["Z_COLLAR"] == pytest.approx(736.3)
