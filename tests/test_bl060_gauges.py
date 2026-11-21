"""BL-060: every gauge line h1_rev5.gauge_values produces that the kit uses (MT-1cr|us1 / us2, T1|us1 / us2,
CLEVIS-SHARE A / B) republished on the current print in one md5-locked record, read by the kit with the BL-059
lock / fallback; text leftovers (hipbelt_structural BL-056 note, lugs PROTECTED reason, BUILD_H1 MOUNT-SEAT) read
from the records. Checks compare against the JSON records, never typed values."""
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1_build as B  # noqa: E402
import physical_test_kit as K  # noqa: E402

AN = ROOT / "designs" / "pack_5200" / "analysis"
TP = ROOT / "designs" / "pack_5200" / "tests_physical"
B58 = json.loads((AN / "bl058.json").read_text())
HIP56 = json.loads((AN / "hip_mount_bl056.json").read_text())
REC = json.loads((TP / "gauge_lines_bl060.json").read_text())


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def test_record_locked_to_the_current_stl_and_complete():
    assert REC["stl_md5"] == K.stl_md5()
    assert REC["source"].startswith("huntkit.gendesign.h1_rev5.gauge_values")
    assert set(REC["tests"]) == set(K.GAUGES60_KEYS)
    assert K.gauges60_record() == REC


def test_kit_uses_every_bl060_line():
    t = K.gauge_tests()
    for k in K.GAUGES60_KEYS:
        assert t[k] == REC["tests"][k], k


def test_lines_are_consistent_with_the_kit_loads():
    """CLEVIS-SHARE proof / cycle peak and MT-1cr steps are the clevis_bl056 kit loads (same rows, same vectors): the
    republish changed strain lines, not loads."""
    c56 = K.clevis56()
    for lab, k in c56["kit"].items():
        st = REC["tests"][k["test"]]["steps"]
        assert abs(st[0]["pin_load_n"] - k["proof_n"]) < 0.05
        assert REC["tests"][k["test"]]["pull_unit_vector_frame_R"] == k["pull_unit_vector_frame_R"]
    for k in K.GAUGES60_KEYS:
        for s in REC["tests"][k]["steps"]:
            e = s["pass_if_abs_microstrain_at_most"]
            # pass line = 1.15 x the worst of point and band, so never under the point value
            assert e >= abs(s["microstrain"]) - 0.5


def test_t1_us1_shift_is_recorded_with_the_old_lines():
    was = REC["was"]["T1|us1"]
    now = [s["pass_if_abs_microstrain_at_most"] for s in REC["tests"]["T1|us1"]["steps"]]
    assert was["from"] == "analysis/h1_rev5.json"
    assert was["pin_load_n"] == [s["pin_load_n"] for s in REC["tests"]["T1|us1"]["steps"]]  # same loads
    assert now[2] > was["pass_if_abs_microstrain_at_most"][2]                               # the hub moved the line
    assert "hip boss" in REC["t1_us1_shift"]


def test_t1_us1_and_us2_lines_in_the_register(kit):
    gl = K.t1_gauge_lines()
    for name, key in (("US1 ROOT", "T1|us1"), ("US2 ROOT", "T1|us2")):
        top = max(REC["tests"][key]["steps"], key=lambda s: s["pin_load_n"])
        assert gl[name]["(b)"][1] == round(top["pass_if_abs_microstrain_at_most"])
    assert "gauge_lines_bl060.json" in kit["register"]["T1"]["defined_in"]
    assert "gauge_lines_bl060.json" in kit["register"]["MT-1cr"]["defined_in"]
    assert "gauge_lines_bl060.json" in kit["register"]["CLEVIS-SHARE"]["defined_in"]
    rows = {r["id"]: r for r in csv.DictReader((TP / "test_register.csv").open(encoding="utf-8"))}
    assert rows["T1"]["pass_fail"] == kit["register"]["T1"]["pass_fail"]
    assert rows["MT-1cr"]["pass_fail"] == kit["register"]["MT-1cr"]["pass_fail"]


def test_falls_back_to_assumption_on_another_print(monkeypatch):
    monkeypatch.setattr(K, "stl_md5", lambda path=None: "0" * 32)
    assert K.gauges60_record() == {}
    assert K.gauge_tests()["T1|us1"] == K.rev5()["gauges"]["tests"]["T1|us1"]
    assert K.gauge_tests()["CLEVIS-SHARE|us2_yz"] == K.clevis56()["gauges"]["tests"]["CLEVIS-SHARE|us2_yz"]
    assert "ASSUMPTION GAUGE-GEOM" in K.gauge_src_txt("x")


def test_hipbelt_bl056_note_from_records():
    hs = (AN / "hipbelt_structural.md").read_text()
    note = K.hb_bl056_note()
    assert note in hs
    hm = B58["hip_mount"]
    assert f"D{hm['hole_d_mm']:g}" in note and f"{B.mount_g():.1f} g" in note
    assert "superseded" in note
    assert "8 x D5.5 holes, legs and hub kept, 34.3 g" not in hs


def test_lugs_protected_reason_reads_the_hole():
    from huntkit.gendesign import lugs
    why = lugs.PROTECTED[("hip_pivot_mount", "slm_ti")]
    assert f"D{B58['hip_mount']['hole_d_mm']:g} holes" in why and "D5.5" not in why


def test_mount_seat_reads_the_c2_pin_load():
    v = HIP56["fe"]["rows"]["C2|H_pin"]["V_n"]
    txt = B.ASSUMPTIONS["MOUNT-SEAT"][0]
    assert f"{v:.0f} N C2 pin load" in txt and "|" not in txt
    md = (ROOT / "designs/pack_5200/print/frame_h1/BUILD_H1.md").read_text()
    assert txt in md
