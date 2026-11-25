"""BL-079: coupon thresholds for the released PAHT-CF H1 (huntkit/gendesign/bl079_h1_thresholds.py) and the BL-079
corrections to bl077.json (layer-time floor at 0.20 mm, D2344 nose, heated conditioning, rounding, kit_needs)."""
from __future__ import annotations

import json
import math

import pytest

from huntkit.gendesign import bl077_paht as X
from huntkit.gendesign import bl079_h1_thresholds as T


def test_f_needed_chord_is_conservative_on_a_concave_margin():
    fs = T.FACTORS
    m = [1.0 - math.exp(-f) for f in fs]                    # concave, rising
    goal = 0.85
    f_true = -math.log(1 - goal)
    f = T.f_needed(m, goal)
    assert f >= f_true - 1e-9 and f == pytest.approx(f_true, rel=0.15)
    assert T.f_needed(m, 0.999) is None                      # saturates below goal on the grid
    assert T.f_needed([1.2] * len(fs), 1.0) == 1.0


def test_round_up_is_never_lenient():
    assert T.up(19.0135) == 19.1 and T.up(19.0) == 19.0 and T.up(10.977) == 11.0 and X.up(0.3628, 0.01) == 0.37


@pytest.fixture(scope="module")
def scan():
    if not T.SCAN_JSON.exists():
        pytest.skip("outputs/bl079/scan_h1.json not generated")
    return json.loads(T.SCAN_JSON.read_text())


def test_scan_f1_reproduces_the_bl077_h1_hot_wet_rows(scan):
    """The f 1 column must be BL-077's H1 hot/wet column exactly (same solve, same rules)."""
    tab = T.table(scan)
    rec = {r["key"]: r for r in json.loads(X.REC_JSON.read_text())["rows"]}
    for k in ("strength", "static_fatigue", "R1", "creep", "joint_strength", "joint_fatigue", "lug_strength",
              "lug_fatigue", "clevis_fatigue", "clevis_fatigue_06"):
        assert tab[k][0] == pytest.approx(rec[k]["h1_hw"], abs=2e-3), k
    assert tab["hip_ins_fatigue"][0] == pytest.approx(rec["hip_fatigue"]["h1_hw"], abs=2e-3)


def test_margins_rise_with_f_and_fatigue_is_linear_in_the_ratio(scan):
    t = T.thresholds(scan)
    for k, v in t["table"].items():
        assert all(b >= a - 2e-3 for a, b in zip(v, v[1:])), k
    for k, r in t["fatigue_linearity_g"]["ratio"].items():
        assert r == pytest.approx(T.G_CHECK, abs=0.01), k
    # hip inserts: pull-out across the layers scales exactly with the layer allowable
    ins = t["table"]["hip_ins_fatigue"]
    assert ins[-1] / ins[0] == pytest.approx(T.FACTORS[-1], rel=0.01)


def test_h1_as_is_lines_and_plausibility(scan):
    t = T.thresholds(scan)
    s = t["sleeved"]
    # on Z / SBS alone the body fatigue rows saturate below goal (in-plane terms take over)
    A = s["layer_route"]
    assert not A["reachable"] and {"R1", "static_fatigue"} <= set(A["saturate_below_goal"])
    assert all(v < 1.0 for k, v in A["at_fmax"].items() if k != "lug_fatigue")
    # ratio route: the least ratio is where the worst saturated fatigue row reaches goal
    Bm = s["ratio_route"]
    assert Bm["fat_ratio_min"] == pytest.approx(T.up(0.30 / t["rows"]["R1"]["at_fmax"], 0.01))
    assert Bm["reachable"] and Bm["z_b_mpa"] == T.up(t["basis"]["z_hw"] * Bm["f"])
    # all-allowables route: R1 governs, F = 1 / R1(f 1)
    C = s["all_route"]
    assert C["governing"] == "R1" and C["F"] == pytest.approx(1.0 / t["rows"]["R1"]["at_f1"], rel=1e-3)
    assert C["xy_b_mpa"] >= t["basis"]["xy_hw"] * C["F"] - 1e-9
    rec = json.loads(X.REC_JSON.read_text())
    h = rec["h1_as_is"]
    pr = h["plausible"]
    # the lines lie beyond what the cited data allow: ratio above 0.40 (best cited), XY above the dry TDS mean
    assert Bm["fat_ratio_min"] > 0.40 and C["xy_b_mpa"] > 88.0 and C["z_b_mpa"] > pr["z_best_mpa"]
    assert "cannot plausibly reach" in h["verdict"]
    assert h["e_ratio_min"] == X.up(max(h["e_ratio_rows"].values()), 0.01)


def test_bl077_json_corrections():
    rec = json.loads(X.REC_JSON.read_text())
    lt = rec["layer_time"]
    assert lt["layer_h_mm"] == 0.20 and rec["layer_time_median_s"] == lt["floor_s"]
    med = max(v["median_s"] for v in lt["halves"].values())
    assert lt["floor_s"] == math.ceil(med) and lt["floor_s"] < lt["bl077_floor_s_at_0p3"]
    assert lt["floor_s"] >= max(v["median_s"] for k, v in lt["halves"].items() if k.startswith("H1 "))
    assert "Seppala" in lt["sources"]["weld"] and "Min print speed" in lt["sources"]["slowdown"]
    c = {x["id"]: x for x in rec["coupons"]}
    assert "D6 loading nose, two D3 supports, span 12" in c["CA-1-PAHT"]["what"]
    for i in ("CA-3-PAHT", "CA-1-PAHT", "CA-4-PAHT"):
        assert "HEATED TO 50 C" in c[i]["what"] and "conditioning box" not in c[i]["what"], i
    b = rec["basis"]["hw"]
    m_body = min(r["after"] for r in rec["rows"] if r["key"] in ("R1", "static_fatigue"))
    assert c["CA-3-PAHT"]["z_line_mpa"] >= b["z"] / m_body and c["CA-3-PAHT"]["sbs_line_mpa"] >= b["tau"] / m_body
    assert c["CA-1-PAHT"]["peak_load_n"] >= c["CA-1-PAHT"]["smax_test_mpa"] * 18.0 / 0.75
    kn = " ".join(rec["kit_needs"])
    assert "do NOT replace" in kn and "replace CA-1 / CA-3 / CA-4" not in kn
