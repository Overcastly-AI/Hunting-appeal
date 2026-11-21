"""BL-038: the physical test kit generator (designs/pack_5200/physical_test_kit.py), built in memory (writes nothing)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import physical_test_kit as K  # noqa: E402
from huntkit.manufacturing import test_results as TR  # noqa: E402


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def test_register_has_every_gate_the_ticket_names(kit):
    reg = kit["register"]
    for t in ("HS-1", "CS-1", "AB-1", "SL-1", "ST-1", "BU-1", "T9-R3a", "T9-R3b", "T9-R3c", "T9-R3d", "US-BS",
              "PORT-1", "GT-1", "FRAY-1", "MT-1c"):
        assert reg[t]["status"] == "ACTIVE", t
        assert set(reg[t]) == set(K.COLS)
    assert reg["B-28 slip"]["status"] == "COVERED->LL-H"
    assert "B-28" in reg["LL-H"]["gates"]
    assert "28 mm cheek" in reg["IM3-EC"]["specimen"]


def test_ca1_release_level_from_the_adopted_results(kit):
    lv = kit["levels"]
    # BL-039 flips kept (history); BL-040: the R1 level is the adopted countersign's 0.40, fallback >= 0.313
    assert lv["flip_gov"] == pytest.approx(max(lv["flip_body"], lv["flip_cheek"], lv["flip_cheek_dir"]))
    assert lv["flip_body"] == pytest.approx(0.30 / lv["fatigue_static"], abs=2e-3)
    assert lv["release"] == pytest.approx(0.40)
    assert lv["fallback_min"] > lv["flip_goodman_static"] + 0.02 - 1e-9
    assert lv["release_bl039"] < lv["fallback_min"] <= lv["release"]
    assert "0.40" in kit["register"]["CA-1"]["pass_fail"]


def test_ca1_is_rescored_to_bl037(kit):
    rk = {d["test"]: d for d in kit["ranking"]}
    assert rk["CA-1"]["grams"] == pytest.approx(9.9)
    assert rk["CA-1"]["booked"] is False
    assert rk["CA-1"]["rank"] > 10
    s = [d["score"] for d in kit["ranking"]]
    assert s == sorted(s, reverse=True)
    assert float(kit["register"]["CA-1"]["grams_at_stake_g"]) == pytest.approx(9.9)


def test_order_releases_r1_then_bag_then_bl037(kit):
    ow = [o for o in kit["order"] if o["stage"] == "run"]
    first = {}
    for o in ow:
        first.setdefault(o["release"], o["seq"])
    assert first["R1"] < first["BAG-CUT"] < first["BAG-BATCH"] < first["BL037"]
    # inside every session R1 tests come before the bag's and the bag's before BL-037 (G6 follows load_standard 5.3)
    for g in ("G2", "G3", "G4", "G5", "G7"):
        ranks = [K.REL_ORDER[o["release"]] for o in ow if o["group"] == g]
        assert ranks == sorted(ranks), g
    active = {t for t, r in kit["register"].items() if r["status"].startswith(("ACTIVE", "PROPOSED"))}
    assert active <= {o["test"] for o in kit["order"]}
    seq = [o["test"] for o in ow if o["group"] == "G6"]
    assert seq.index("T9") < seq.index("T1") < seq.index("T2") < seq.index("MT-1c") and seq[-1] == "T2u"


def test_shopping_list_is_priced_and_flags_long_lead(kit):
    sh = kit["shopping"]
    for x in sh:
        assert x["total_usd"] == pytest.approx(x["qty"] * x["unit_usd"], abs=0.01)
        assert x["price_source"].startswith(("http", "record", "ASSUMPTION", "test_register", "frame_h1"))
    cam = next(x for x in sh if x["item"].startswith("cam buckle"))
    assert cam["unit_usd"] == pytest.approx(K.rec_price("cam_25mm_al")) and cam["long_lead"]
    assert next(x for x in sh if "#10 coil slider" in x["item"])["long_lead"]
    assert sum(x["total_usd"] for x in sh) > 2000


def test_results_template_reads_back(kit, tmp_path):
    res = kit["results"]
    p = tmp_path / "r.csv"
    K._csv(p, res, TR.COLUMNS)
    rows = TR.load_results(p)
    assert len(rows) == len(res)
    v = TR.verdicts(rows)
    assert all(t.status == "OPEN" for t in v.values())
    a = TR.assumption_status(rows, v)
    for key in ("US-BS", "NO-BIND", "CINCH_STATIC", "PAHT_FAT", "XLPE-SET", "SLIDER-CORD", "MU_WEB_FAB", "ROLL-PATH"):
        assert a[key]["status"] == "OPEN", key
    # fill every US-BS row with a pass: its assumption flips to VERIFIED
    for r in rows:
        if r.test_id == "US-BS":
            r.measured = "Y" if r.check == "yes" else "4"
    assert TR.assumption_status(rows)["US-BS"]["status"] == "VERIFIED"
    lid = next(r for r in rows if r.test_id == "T9-R3d" and r.check == "band")
    lo, hi = (float(x) for x in lid.limit.split(".."))
    assert hi - lo == pytest.approx(10.0) and lo < kit["lid_g"] < hi


# ---------------------------------------------------------------------------- BL-055 Part B
import json as _json  # noqa: E402
import re as _re  # noqa: E402

_REV5 = _json.loads((ROOT / "designs/pack_5200/analysis/h1_rev5.json").read_text())
_G2 = _json.loads((ROOT / "designs/pack_5200/tests_physical/us1_outer_gauge.json").read_text())
# BL-057: the US2 lines on the BL-056 re-printed joint blocks replace BL-053's (CLEVIS-SHARE A/B and MT-1cr|us2)
_C56 = _json.loads((ROOT / "designs/pack_5200/analysis/clevis_bl056.json").read_text())
_US2 = {**_REV5["gauges"]["tests"], **_C56["gauges"]["tests"]}


def _nums(txt: str) -> set:
    return {float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", txt)}


def test_clevis_share_is_two_loadings_with_vectors_and_microstrain_lines(kit):
    r = kit["register"]["CLEVIS-SHARE"]
    t = _US2
    A, B = t["CLEVIS-SHARE|us2_inboard"], t["CLEVIS-SHARE|us2_yz"]
    pa, pb = A["steps"][0]["pin_load_n"], B["steps"][0]["pin_load_n"]
    assert round(pa) == 1104 and round(pb) == 643                     # the ticket's A / B loads
    assert f"{pa:.0f} N proof" in r["title"] and f"{pb:.0f} N proof" in r["title"]
    for L in (A, B):
        # the pull vector, as 100 mm components a beginner sets with a rule
        assert str(L["pull_unit_vector_frame_R"]) in r["steps"]
        for s in L["steps"]:                                         # every published pass line is in the pass text
            assert f"PASS if size <= {s['pass_if_abs_microstrain_at_most']:.0f}" in r["pass_fail"]
    assert "LOADING A" in r["steps"] and "LOADING B" in r["steps"]
    # the static steps of A are MT-1cr|us2's (same row, same vector), so MT-1cr and CLEVIS-SHARE A cross-check
    assert [s["pin_load_n"] for s in t["MT-1cr|us2"]["steps"]] == K.clevis_loadings()["A"]["steps_n"]


def test_mt1cr_uses_the_3d_vectors_a_50kg_quarter_and_a_contact_photo(kit):
    r = kit["register"]["MT-1cr"]
    kg = K.float_limit_kg()
    assert kg >= 50.0 and f"{kg:.0f} kg" in r["title"]
    assert "photograph" in r["steps"] and "contact" in r["pass_fail"]
    for key in ("MT-1cr|us1", "MT-1cr|us2"):
        assert str(_REV5["gauges"]["tests"][key]["pull_unit_vector_frame_R"]) in r["steps"]
    # three gauges, each step with its number
    for key, tests in (("MT-1cr|us1", _REV5["gauges"]["tests"]), ("MT-1cr|us2", _US2),
                       ("MT-1cr|us1_outer", _G2["tests"])):
        for s in tests[key]["steps"]:
            if s["pin_load_n"] > 0:
                assert f"PASS if size <= {s['pass_if_abs_microstrain_at_most']:.0f}" in r["pass_fail"], (key, s)
    assert "US1 OUTER CHEEK" in r["specimen"]


def test_t1_has_three_gauges_and_numeric_lines_with_the_outer_cheek_gauge(kit):
    r = kit["register"]["T1"]
    gl = K.t1_gauge_lines()
    assert set(gl) == {"US1 ROOT", "US1 OUTER CHEEK", "US2 ROOT"}
    for g_, v in gl.items():
        for c in K.T1_LB:
            assert f"at most {v[c][1]:.0f}" in r["pass_fail"]
    # 300 lb is the published top step (h1_rev5 / us1_outer_gauge), 150 lb its half, 225 lb linear in between
    top = _G2["tests"]["T1|us1_outer"]["steps"][-1]["pass_if_abs_microstrain_at_most"]
    assert gl["US1 OUTER CHEEK"]["(b)"][1] == round(top)
    assert abs(gl["US1 OUTER CHEEK"]["(c)"][1] - 0.75 * top) <= 1.0
    assert "outboard face of the US1 fairlead's outer cheek" in r["steps"]


def test_us1_outer_gauge_site_is_the_rev5_governing_spot():
    s = _G2["site"]
    assert 80.0 <= s["x"] <= 88.0 and 98.0 <= s["z"] <= 104.0          # h1_rev5.md 4: x 80-88, z 98-104
    for k in ("MT-1cr|us1_outer", "T1|us1_outer"):
        base = k.replace("_outer", "")
        assert _G2["tests"][k]["pull_unit_vector_frame_R"] == _REV5["gauges"]["tests"][base]["pull_unit_vector_frame_R"]
        assert [x["pin_load_n"] for x in _G2["tests"][k]["steps"]] == \
               [x["pin_load_n"] for x in _REV5["gauges"]["tests"][base]["steps"]]


def test_pin_ret_fit_us_ca1_and_t6c_rows(kit):
    reg = kit["register"]
    p = reg["PIN-RET"]
    n = sum(v["qty"] for v in _REV5["pins"]["stations"].values())
    assert n == 12 and f"all {n} fairlead pins" in p["title"]
    assert "50 N" in p["pass_fail"] and "0.5 mm" in p["pass_fail"] and "<= 8 s" in p["pass_fail"]
    f = reg["FIT-US"]
    w = _REV5["strap_wrap"]["worst"]["us2"]
    assert "LIP AND STRAP" in f["steps"] and f"{w['wrap_deg']:.0f} deg" in f["steps"]
    assert f"r {w['lip_r_mm']:.0f} mm" in f["steps"]
    c = reg["CA-1"]
    assert f"{K.SCAR_BARS} SCAR BARS" in c["specimen"] and "support interface" in c["specimen"]
    assert "SCAR BARS" in c["pass_fail"] and float(c["hours_machine"]) == pytest.approx((8 + K.SCAR_BARS) * 27.8, abs=1)
    t = reg["T6(c)"]
    cp = K._FB().clamp()
    assert f"{1.5 * cp['limit_spine_axial_n']:.0f} N" in t["pass_fail"]
    assert f"{1.5 * cp['limit_bar_torque_nm']:.1f} N m" in t["pass_fail"]
    for tid in ("CLEVIS-SHARE", "MT-1cr", "PIN-RET", "T6(c)"):
        assert set(reg[tid]) == set(K.COLS), tid


def test_every_new_bl055_row_has_numeric_results_lines(kit):
    """The beginner checks numbers: every results row of the BL-055 tests carries a unit and a limit (or a record)."""
    rows = [r for r in kit["results"] if r.get("test_id") in ("CLEVIS-SHARE", "MT-1cr", "PIN-RET", "T6(c)", "T1")]
    assert len(rows) > 40
    gauge = [r for r in rows if r.get("unit") == "microstrain"]
    assert gauge and all(_re.fullmatch(r"-\d+\.\.\d+", str(r["limit"])) for r in gauge if r.get("check") == "band")
