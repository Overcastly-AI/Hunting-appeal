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


# ---------------------------------------------------------------- structural countersign (2026-11-13)
def test_goodman_step_closed_form():
    # 0 -> P (R 0) and the R 0.1 coupon at S have equal sa / (1 - sm): P / 2 / (1 - P / 2) = 0.45 S / (1 - 0.55 S)
    for P in (0.1, 0.2553, 0.4):
        S = CC.goodman_r01(P)
        assert (P / 2) / (1 - P / 2) == pytest.approx(0.45 * S / (1 - 0.55 * S), rel=1e-12)
        assert S > P                     # an R 0.1 coupon at equal max is milder than the R 0 frame cycle
    assert CC.goodman_r01(0.2553) == pytest.approx(0.2758, abs=2e-4)


def test_countersign_explicit_run_reproduces_and_fixes_k(c):
    s = c["countersign"]
    assert s is not None, "run python designs/pack_5200/ca1_mt1c_confirm.py --explicit"
    i, x = c["inputs"], s["explicit"]
    # the split W + C re-solve reproduces both official body margins exactly (same solver, same sets)
    assert s["reproduces"]
    assert x["m_static"] == pytest.approx(i["m_body"], abs=1e-9) and x["m_cycled"] == pytest.approx(i["m_body_cyc"], abs=1e-9)
    assert x["raster_g"] == pytest.approx(800.656, abs=0.01)
    # the cycled run is peak = 1.6 W + 1.6 C: k = 1.6, not a bracket
    assert s["k_check"] and x["flip_peak_a"]["1.6"] == pytest.approx(i["record_ratio"] / i["m_body_cyc"], abs=1e-9)
    # the chord is above the explicit curve on this body (an empirical result: FI99 is a percentile)
    assert s["chord_conservative"]
    # explicit flips rise with the cinch share / swing; in phase governs
    fa = [x["flip_peak_a"][k] for k in sorted(x["flip_peak_a"], key=float)]
    assert fa == sorted(fa)
    assert s["antiphase_10pct"] < x["flip_goodman"]["0.1"]


def test_countersign_release_rule(c):
    s = c["countersign"]
    x = s["explicit"]
    # mean stress and the R 0 / R 0.1 gap move the static-cinch body flip above the BL-039 rule
    assert x["flip_goodman_no_cinch"] == pytest.approx(CC.goodman_r01(c["flips"]["body (cinch static)"]), abs=2e-4)
    assert s["flip_static_goodman"] == pytest.approx(0.2926, abs=5e-4)
    assert s["margin_at_276"] < 1.0 < s["margin_at_276_signed"]
    assert c["release"] < s["flip_static_goodman_signed"] + 0.02      # even the lower bound breaks flip + 0.02
    assert s["release_static"] == pytest.approx(0.313) and s["release_static"] > c["release"]
    # body governs the cheek and the joint on the same basis
    assert max(s["other_goodman"].values()) < s["flip_static_goodman"]
    # the table: rising, 0.40 covers swings up to ~117 %, 0.276 covers none
    lv = [r["level"] for r in s["table"]]
    assert lv == sorted(lv) and lv[0] == s["release_static"]
    assert 115.0 <= s["p_040_pct"] <= 120.0 and s["p_276_pct"] == 0.0
    assert next(r for r in s["table"] if r["swing_pct"] == 100)["level"] <= 0.40 - 1e-9
    assert next(r for r in s["table"] if r["swing_pct"] == 150)["level"] > 0.40
    assert s["margin_040_p100"] > 1.0


def test_countersign_im3_ec(c):
    ec = c["countersign"]["ec"]
    i = c["inputs"]
    assert ec["peak_n"] == 1178 and ec["aft_deg"] == pytest.approx(22.3, abs=0.05)
    assert ec["aft_deg_dir"] == pytest.approx(ec["aft_deg"] + 10.0, abs=0.05)
    # at the computed angle the 1.15 coupon proves only 1.15 x (DIR_SCATTER / design) at the +10 deg angle
    assert ec["proven_dir_margin_at_aft"] == pytest.approx(1.15 * i["m_cheek_dir"] / i["m_cheek"], abs=1e-3)
    assert ec["proven_dir_margin_at_aft"] < 1.15
    assert ec["peak_n_at_aft_for_dir"] == pytest.approx(1178 * i["m_cheek"] / i["m_cheek_dir"], abs=1.0)
    assert ec["min_n_r002"] == round(0.02 * 1.15 * 1.6 * ec["combo_1g_n"])
