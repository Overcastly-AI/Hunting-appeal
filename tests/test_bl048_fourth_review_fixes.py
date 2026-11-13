"""BL-048: fourth-review fixes, bag side (M-A, M-B, M-C, m-2..m-9; N-1 is tests/test_us_route.py)."""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import corrie_f as F  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402
import physical_test_kit as K  # noqa: E402
import strap_tails as ST  # noqa: E402


def test_mb_one_webbing_thickness_from_the_record():
    rec = yaml.safe_load((ROOT / "data/materials/webbing/poly_webbing_38mm.yaml").read_text())["properties"]
    assert rec["thickness_mm"] == 1.5 and rec["thickness_max_mm"] == 1.6 and rec["thickness_min_mm"] == 1.2
    assert P.HE_T == F.B25_T == F.WEB38_T == rec["thickness_mm"]          # one value for HE and B-25
    assert P.HE_T_RANGE == (1.2, 1.6)
    assert rec["breaking_strength_min_n"] >= 2355 * 2                     # the B-18 seam governs the hinge row


def test_mb_bom_and_shopping_list_carry_the_spec():
    import mfg_corrie_f_rev3 as M
    spec = M._web_spec("poly_webbing_38mm")
    assert "1.2-1.6 mm" in spec and "sample" in spec
    assert M._web_spec("poly_webbing_25mm") == ""
    src = (HERE / "physical_test_kit.py").read_text()
    assert "BUY A SAMPLE FIRST" in src and "poly webbing 38 mm, PLY" in src


def test_mc_fixture_pin_is_a_hardened_m5x40_dowel():
    assert "M5 x 40" in K.FIX_PIN and "hardened" in K.FIX_PIN and K.FIX_PIN_N >= 2
    steps = K.pt3_steps()
    assert "M5 x 40" in steps and "PIN CHECK" in steps
    # why: the frame's own pin model puts a 5 mm 7075 pin past yield at the PT-3 proof
    from huntkit.gendesign import h1_fairleads as H
    assert H.pin_bending(1530.0, 20.0, 8.0, 5.0, 2.4)["sf_yield"] < 1.0
    assert H.pin_bending(1019.0, 20.0, 8.0, 5.0, 2.4)["sf_yield"] == pytest.approx(1.24, abs=0.01)


def test_ma_tl1_reads_the_bl047_record_with_two_rigs():
    ct = K.crown_tube()
    rec = json.loads((HERE / "analysis/bl047_frame_items.json").read_text())["tl1"]
    assert ct["proof_n"] == round(rec["proof_publish_n"]) == 497
    A, B = ct["rigs"]["A"], ct["rigs"]["B"]
    assert A["below_horizontal_deg"] == pytest.approx(22.2, abs=0.1) and A["guy_n"] == 454
    assert B["below_horizontal_deg"] == pytest.approx(58.1, abs=0.1) and B["outboard_pct"] == pytest.approx(13.6)
    assert A["crown_strap_n"] == B["crown_strap_n"] == 43
    for r in (A, B):
        assert r["down"] ** 2 + r["aft"] ** 2 + r["outboard"] ** 2 == pytest.approx(1.0, abs=0.01)
    t = K.tl1_patch()
    assert "RIG A" in t["steps"] and "RIG B" in t["steps"] and "58 deg below horizontal" in t["steps"]
    assert "43 N" in t["steps"] and "spine stub 25.0 mm fore" in t["steps"]
    import mfg_corrie_f_rev3 as M
    assert M.TL1_N == 497


def test_m2_rt_cut_rounded_up_with_the_grip_and_an_exception():
    r = ST.roll_row()
    assert r["after"]["cut_mm"] % 5 == 0
    assert r["after"]["tail_longest_path_mm"] >= F.TAIL_GRIP_MM            # grip at the full bag
    assert r["exception"]["decision"] == "RT-TAIL-EXC" and "K-RT" in r["exception"]["mitigation"]


def test_m6_sewf_he_rows_and_he_fit_step0_pass_criterion():
    src = (HERE / "physical_test_kit.py").read_text()
    assert '"HEtop#"' in src and '"HEproof#"' in src
    he = K.he_fit_row()
    s0 = he["steps"].split("(1)")[0]
    assert "PASS (gate US-ROUTE)" in s0 and "10 mm feeler" in s0 and "us_route_stay_R.stl" in s0


def test_m8_test_square_avoids_the_strips():
    import patterns_corrie_f_rev3_export as E
    pw, ph = 215.9, 279.4
    occ = [(14.0, 35.0, 14 + 38 + 46, 249.0)]                       # one tall strip + its labels, left column
    x, y = E.test_square_spot(occ, pw, ph)
    box = (x, y, x + E.SQ_BOX, y + E.SQ_BOX)
    assert all(box[2] <= o[0] or box[0] >= o[2] or box[3] <= o[1] or box[1] >= o[3] for o in occ)
    with pytest.raises(RuntimeError):                                # two tall strips: no room, the layout must split
        E.test_square_spot(occ + [(104.0, 35.0, 175.0, 249.0)], pw, ph)
    assert ("IME",) in E.WEB_GROUPS and ("USA",) in E.WEB_GROUPS     # page 5 (IME + USA) split


def test_fourth_status_and_not_ready():
    import mfg_corrie_f_rev3 as M
    st = {i: (c, s) for i, c, s, _ in M.FOURTH_STATUS}
    assert st["N-1"] == ("blocker", "open (frame side)")
    assert all(st[k][1] == "fixed" for k in ("M-A", "M-B", "M-C"))
    assert "N-1" in M.open_findings() and not M.ready_to_cut()
