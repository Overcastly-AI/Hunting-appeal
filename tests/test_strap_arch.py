"""Tests for BL-003 strap architectures (designs/pack_5200/concepts/strap_arch.py)."""
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import strap_arch as S  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402


@pytest.fixture(scope="module")
def A():
    return S.architectures()


@pytest.fixture(scope="module")
def SV():
    return S.savings()


def test_today_equals_ledger(A):
    sysm = L.by_system(S.CONFIG, S.SIZE)
    tot = sum(p.g for p in A["today"])
    assert tot == pytest.approx(sysm["straps_meat"] + sysm["straps_compression"], abs=0.1)
    meat = sum(p.g for p in A["today"] if p.system == "straps_meat")
    assert meat == pytest.approx(sysm["straps_meat"], abs=0.1)


def test_im_split_matches_ledger_row(A):
    ids = ("IM-web", "IM-eyes", "IM-hooks", "IM-cams")
    g = sum(p.g for p in A["today"] if p.id in ids)
    assert g == pytest.approx(S._lg("internal meat harness: 3 x 38 mm"), abs=0.05)


def test_configs_today_match_owner_rule(SV):
    pk = SV["today"]["pack"]
    assert pk["meat_trip_g"] == pytest.approx(L.total(S.CONFIG, S.SIZE), abs=0.05)
    # BL-008 / DECISIONS 2026-11-10: base 3700.4 g, as hunted 3872.4 g (proposal rounding). BL-035: +46.5 g on every
    # config from the record re-booking of CORRIE B.2 and the shared rows (+26.0 #10 door sliders, +16.0 stainless US
    # tri-glides, +1.9 IMP-4 #5 slider, +4.5 elastic hook keepers, -0.8 lifter tri-glides, -1.1 torso adjust)
    assert pk["base_g"] == pytest.approx(3747.1, abs=0.5)
    assert pk["as_hunted_g"] == pytest.approx(3919.1, abs=0.5)
    assert pk["meat_trip_g"] - pk["as_hunted_g"] == pytest.approx(54.4, abs=0.1)   # B-24


def test_rec_meets_target_in_every_config(SV):
    t, r = SV["today"]["pack"], SV["rec"]["pack"]
    for k in ("base_g", "as_hunted_g", "meat_trip_g"):
        assert t[k] - r[k] >= 200.0
    assert SV["rec"]["saved_removed_g"] >= 200.0
    assert SV["rec"]["saved_removed_g"] < 300.0            # stretch honestly not met


def test_rec_saving_by_hand(A, SV):
    """Independent recomputation of the REC saving from the records and ledger rows."""
    im = sum(S.IM_CUTS_MM) / 1000 * (S.WEB38 - S.WEB25) + 6 * 9.0 - 3 * S.G25R_G + 3 * (22.0 - S.CAM25_G)
    us = 1.10 * (S.WEB38 - S.WEB25) + 2 * (22.0 - S.CAM25_G)
    wings = S._lg("M-01") + S._lg("SH-06") + sum(S._lg(f"wing strap {i}") for i in range(1, 5))
    assert SV["rec"]["saved_removed_g"] == pytest.approx(im + us + wings, abs=0.15)


def test_rec_saving_survives_heavier_im_hook(SV):
    """If the 25 mm hook fails the 910 N proof and the 14 g 2200 N hook goes on the IM free ends, still >= 200 g."""
    penalty = 3 * (S.HOOK_RATED_G - S.G25R_G)
    # BL-035: the 25 mm cam is the cam_25mm_al record + 1 g pull tab = 13.2 g (was 13.0 typed), 5 cams: the REC saving
    # drops 218.5 -> 217.5 g, and with the heavy-hook fallback 200.5 -> 199.5 g. HONEST RESULT: the fallback now misses
    # the 200 g bar by 0.5 g (BL-003 history; REC is adopted, the fallback is only taken if the 25 mm hook fails 910 N).
    assert SV["rec"]["saved_removed_g"] - penalty == pytest.approx(199.5, abs=0.1)
    assert SV["rec"]["saved_removed_g"] - penalty < 200.0


def test_b24_is_meat_trip_and_pouch_straps_as_hunted(A):
    for k in ("today", "rec", "c"):
        cf = {p.id: p.cfg for p in A[k]}
        assert cf["B-24-hooks"] == "meat_trip" and cf["B-24-web"] == "meat_trip"
        assert cf["pouch-straps"] == "as_hunted"


def test_every_function_served_except_b1_float(A):
    for k in ("today", "a", "b2", "c", "rec"):
        served = {f for p in A[k] for f in p.funcs}
        assert served == set(S.FUNCS), k
    # b1 keeps F3 only through the meat straps and B-24: no frame-anchored wrap left
    assert not any(p.id.startswith("W-") for p in A["b1"])


def test_rec_deletes_wings_and_keeps_wraps(A):
    ids = {p.id for p in A["rec"]}
    assert not ids & {"M-01", "SH-06", "wing-straps"}
    assert {"W-web", "W-hw", "keepers", "roll", "pouch-straps", "B-24-hooks"} <= ids


def test_hardware_and_ops_drop(SV):
    assert SV["rec"]["hw_count"] < SV["today"]["hw_count"]
    assert SV["rec"]["ops"] < SV["today"]["ops"]
    assert SV["rec"]["hw"].get("38 mm sliding-gate hook", 0) == 0
    assert SV["rec"]["hw"]["25 mm rated G-hook"] == 3


def test_margins_flag_overstrength():
    m = {(r["system"], r["part"]): r for r in S.today_margins()}
    assert m[("IM1-IM3", "38 mm webbing")]["over2"]
    assert not m[("IM1-IM3", "38 mm cam slip (ASSUMPTION 1100 N)")]["over2"]
    assert m[("IM1-IM3", "38 mm cam slip (ASSUMPTION 1100 N)")]["ratio"] == pytest.approx(1100 / 605, rel=1e-3)
    us = m[("US1/US2", "38 mm cam slip (ASSUMPTION 1100 N)")]
    assert us["req_n"] == pytest.approx(720, abs=1)        # float_fea.md: 720 N at 53 kg
    assert math.isnan(m[("W1-W3", "G-hook 4 g (no rating on file)")]["ratio"])


def test_procedure_times():
    sec = S.procedures()["seconds"]
    assert S.HOOK_S == 4 and S.IM_STRAP_S == 8
    assert sec["F2"]["today_documented"] == 108 and sec["F3"]["today_documented"] == 128
    assert sec["F1"]["rec"] == 12 and sec["F1"]["today"] == 24
    assert sec["bag_off"]["rec"] <= 120                   # owner limit 2 min
    assert sec["F2"]["rec"] == 12 + 52 + 21 + 12 + 12 + 20


def test_load_paths_list_flags_proof_conflict():
    lp = S.load_paths()
    hook = next(x for x in lp if x["loc"].startswith("IM1-IM3 right eyes"))
    assert S.G25R_YIELD_N < S.PROOF_MEAT_N and "BELOW" in hook["note"]
    for x in lp:
        assert {"loc", "dir", "n", "part", "rated_n"} <= set(x)


def test_patent_guardrails_pass():
    for k in ("a", "b1", "b2", "c", "rec"):
        for _, st, _ in S.patent_check(k):
            assert st.startswith("pass")


def test_b1_cuts_interpolated():
    c = S.b1_strap_cuts_mm()
    assert len(c) == 3 and c[0] < c[1] < c[2]
    assert c[1] == pytest.approx(1262 - 5 / 170 * 72 + 150, abs=0.5)
