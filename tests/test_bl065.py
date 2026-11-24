"""BL-065 record checks (H1 eigenvalue buckling). The heavy runs are cached in outputs/bl065; these tests read the
committed record and check it against bl058.json and the closed-form relations it relies on."""
import json
import math
from pathlib import Path

import pytest

from huntkit.gendesign import bl065_text as T

REPO = Path(__file__).resolve().parents[1]
REC = REPO / "designs" / "pack_5200" / "analysis" / "bl065.json"
BL058 = REPO / "designs" / "pack_5200" / "analysis" / "bl058.json"


def test_verdict_logic():
    rec = {"summary": {"static_cinch": {"member_eigen_unbraced": 1.4, "frame_eigen_braced": 1.2},
                       "cinch_cycled": {"member_eigen_unbraced": 0.9, "frame_eigen_braced": 1.3}}}
    v = T.verdict(rec)
    assert v["real_margin"] == {"static_cinch": 1.2, "cinch_cycled": 0.9}
    assert v["fix_required"] and not v["bonus_met"]
    rec["summary"]["cinch_cycled"]["member_eigen_unbraced"] = 1.16
    v = T.verdict(rec)
    assert not v["fix_required"] and v["bonus_met"]


@pytest.fixture(scope="module")
def rec():
    if not REC.exists():
        pytest.skip("bl065.json not generated")
    return json.loads(REC.read_text())


def test_stl_lock(rec):
    from huntkit.gendesign import frame_iter1 as FI
    assert rec["stl_md5"] == FI.STL_MD5 == FI.stl_md5()


def test_record_rule_reproduces_bl058(rec):
    """The prestress is the record's: the record / section rules recomputed in BL-065 equal bl058.json."""
    b = json.loads(BL058.read_text())
    assert rec["summary"]["static_cinch"]["record_rule"] == pytest.approx(b["body"]["min"]["static_cinch"]["buckling"],
                                                                          abs=2e-3)
    assert rec["summary"]["cinch_cycled"]["record_rule"] == pytest.approx(b["body"]["min"]["cinch_cycled"]["buckling"],
                                                                          abs=2e-3)
    ub = next(r for r in rec["members"] if r["basis"] == "fine" and r["member"] == "upper branch R")
    assert ub["P_factored_n"] == pytest.approx(544.9, abs=0.5)
    assert ub["margin_section"] == pytest.approx(0.855, abs=2e-3)       # BL-061 finding


def test_k_eff_consistent(rec):
    """K_eff and P_cr obey Euler with the record's E (1621 MPa) and L, and the margin = P_cr / (1.5 P)."""
    E = 3860.0 * 0.6 * 0.7
    for r in rec["members"]:
        pcr = math.pi ** 2 * E * r["I_min_mm4"] / (r["K_eff_unbraced"] * r["L_mm"]) ** 2
        assert pcr == pytest.approx(r["Pcr_unbraced_n"], rel=5e-3)
        assert r["eigen_unbraced"] == pytest.approx(r["Pcr_unbraced_n"] / (1.5 * r["P_factored_n"]), rel=5e-3)
        assert r["eigen_braced"] >= r["eigen_unbraced"] - 1e-6          # bracing never lowers a member
        if r["margin_record"] < 1.5:                                    # the members the record rule ran close on
            assert r["K_eff_unbraced"] < 1.0                            # fused ends: better than pinned


def test_verdict_and_bl058_block(rec):
    v = T.verdict(rec)
    assert rec["fix"]["fix_required"] == v["fix_required"]
    b = json.loads(BL058.read_text())
    blk = b["bl065_eigen"]
    assert blk["buckling_of_record"]["static_cinch"] == pytest.approx(v["real_margin"]["static_cinch"], abs=1e-3)
    assert blk["buckling_of_record"]["cinch_cycled"] == pytest.approx(v["real_margin"]["cinch_cycled"], abs=1e-3)
    # the BL-058 body rows stay as run
    assert b["body"]["min"]["static_cinch"]["buckling"] == pytest.approx(1.053)


def test_squeeze_case(rec):
    sq = rec["squeeze"]
    assert sq["Q_per_side_n"] == pytest.approx(208.0 * 2.0)
    assert sq["braced_bifurcation_n_per_side"] == pytest.approx(sq["braced_margin"] * 1.5 * sq["Q_per_side_n"],
                                                                rel=5e-3)
