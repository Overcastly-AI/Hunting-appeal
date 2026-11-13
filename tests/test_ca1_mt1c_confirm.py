"""BL-039: CA-1 release rule and MT-1c bound confirmation (designs/pack_5200/ca1_mt1c_confirm.py), plus the BL-039
register / kit fixes (crown-strap spare in T9-R3c, PT-4 retired, BP-1 cost)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import ca1_mt1c_confirm as CC  # noqa: E402
import physical_test_kit as K  # noqa: E402


@pytest.fixture(scope="module")
def c():
    return CC.confirm()


def test_release_rule_reproduces_the_kit_level(c):
    i = c["inputs"]
    assert c["release_matches_kit"]
    assert c["release"] == pytest.approx(0.276)
    # flip = record / margin, and the release = governing flip + 0.02 rounded up to 0.001
    assert c["flips"]["body (cinch static)"] == pytest.approx(i["record_ratio"] / i["m_body"], abs=1e-4)
    assert c["flip_gov"] == pytest.approx(max(c["flips"].values()), abs=1e-4)
    assert c["flip_gov"] + 0.02 <= c["release"] < c["flip_gov"] + 0.021
    # every part >= 1.0 at the release level; margins scale linearly with the ratio
    for n, m in c["margins_at_release"].items():
        assert m >= 1.0, n
    assert c["margins_at_release"]["body (cinch static)"] == pytest.approx(i["m_body"] * c["release"] / 0.30, abs=1e-3)
    # the 1.15 goal at the measured ratio would need about the record value
    assert c["goal_level_1p15"] == pytest.approx(c["flip_gov"] * 1.15, abs=1e-3)


def test_swing_bound_chord_and_brackets(c):
    i = c["inputs"]
    # no swing = the static body flip; full cycling (q = 1) = the cycled run
    assert CC.body_flip(i, 0.0, 1.0) == pytest.approx(i["record_ratio"] / i["m_body"])
    assert CC.body_flip(i, 0.9, 1.0) == pytest.approx(i["record_ratio"] / i["m_body_cyc"])
    assert CC.body_flip(i, 5.0, 1.0) == pytest.approx(i["record_ratio"] / i["m_body_cyc"])     # capped
    # p_at_flip inverts body_flip
    p = CC.p_at_flip(i, 0.27, 0.8)
    assert CC.body_flip(i, p, 0.8) == pytest.approx(0.27, abs=1e-9)
    # the worst bracket is the smallest k
    sw = c["swing"]
    assert sw["k0.8"]["margin_at_release_10pct"] < sw["k1"]["margin_at_release_10pct"] < sw["k1.6"]["margin_at_release_10pct"]
    # the BL-038 10 % bound keeps margin >= 1.0 at 0.276 but not the flip + 0.02 rule
    assert c["swing_bound_margin_ok"] and not c["swing_bound_rule_ok"]
    assert c["swing_worst"]["release_for_10pct"] > c["release"]
    # graded table rises with the swing and ends at the kit's cycled level
    rel = [g["release"] for g in c["graded"]]
    assert rel == sorted(rel) and rel[0] == c["release"] and rel[-1] == c["cycled_release"]


def test_kit_uses_the_graded_rule(c):
    lv = K.release_levels()
    w = c["swing_worst"]
    assert lv["swing_ok_release_pct"] == pytest.approx(100 * w["p_rule_at_release"], abs=0.1)
    assert lv["swing_ok_040_pct"] == pytest.approx(100 * w["p_rule_at_040"], abs=0.1)
    kit = K.build(write=False)
    mt = kit["register"]["MT-1c"]["pass_fail"]
    assert "0.40" in mt and str(lv["release_cycled"]) in mt and "<= 10 %" not in mt
    g4 = next(g for g in K.GROUPS if g["id"] == "G4")
    txt = K.guide_md(g4, kit["register"], lv, K.loads(lv), kit["results"], kit["order"])
    # the CA-1 guide no longer says the 0.40 run covers a fully cycling cinch (0.404 > 0.40)
    assert "covers it if it passes" not in txt and "does not cover it" in txt


def test_bl039_register_fixes():
    kit = K.build(write=False)
    reg = kit["register"]
    # PT-4 retired (crown hood removed), and out of every session
    assert reg["PT-4"]["status"] == "RETIRED"
    assert all("PT-4" not in g["tests"] for g in K.GROUPS)
    # BP-1 cost from the records, and the shopping list carries it without double counting
    b = K.bp1_cost()
    assert float(reg["BP-1"]["cost_usd"]) == pytest.approx(b["usd"]) and b["usd"] > 0
    assert b["usd"] == pytest.approx(0.02 * K.rec_price("rohacell_71_igf")
                                     + 2 * 0.07 * 0.2 * K.rec_price("cfrp_t300_3k_woven_epoxy_ply"), abs=0.01)
    bp = [x for x in kit["shopping"] if "BP-1" in x["tests"] and x["kit"] == "S"]
    assert sum(x["total_usd"] for x in bp) == pytest.approx(b["usd"], abs=0.02)
    # T9-R3c: the S path limit now has the BL-039 spare beyond the sim path
    cut = K.crown_cut_mm()
    for k, d in cut.items():
        assert d["path_limit_mm"] - d["longest_mm"] == pytest.approx(d["spare_mm"], abs=0.1) and d["spare_mm"] >= 40
        assert d["cut_mm"] == pytest.approx(d["path_limit_mm"] + 2 * 50.0, abs=0.1)
    assert str(cut["S"]["path_limit_mm"]) in reg["T9-R3c"]["pass_fail"]


def test_im3_ec_load_from_the_bl021_demand():
    ec = K.im3_ec_load()
    import json
    e = json.loads((ROOT / "designs/pack_5200/analysis/im3_body_simloads.json").read_text())
    f1 = e["eye"]["cands"]["14_8"]["sensitivity"]["governing_combo_1g_n"]
    assert ec["peak_n"] == round(1.15 * 1.6 * f1) and ec["peak_n"] > 1017       # BL-010's 1017 N was below demand
    assert ec["min_n"] == round(0.1 * ec["peak_n"])
    reg = K.build(write=False)["register"]["IM3-EC"]
    assert f"{ec['peak_n']} N" in reg["pass_fail"] and "1017 N" not in reg["pass_fail"]
    doc = (ROOT / "designs/pack_5200/tests_physical/CA1_fatigue_rig.md").read_text()
    assert f"{ec['peak_n']} N" in doc and "0.276" in doc
