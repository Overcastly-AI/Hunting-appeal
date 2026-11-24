"""BL-061 iteration-1 frame concepts (huntkit.gendesign.frame_iter1 / frame_iter1_report) and the side task (T1 US1
gauge record only, the second US1 gauge re-run on the current STL). Closed forms first, then the published record."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import frame_iter1 as F

ROOT = Path(__file__).resolve().parents[1]
REC_P = ROOT / "designs" / "pack_5200" / "iter1" / "frame" / "frame_iter1.json"
BL058 = json.loads((ROOT / "designs" / "pack_5200" / "analysis" / "bl058.json").read_text())


# ------------------------------------------------------------------------------------------------ closed forms
def _grid(nu, nv, h=F.H, hollow=0):
    u, v = np.meshgrid((np.arange(nu) + 0.5) * h, (np.arange(nv) + 0.5) * h, indexing="ij")
    keep = np.ones_like(u, bool)
    if hollow:
        keep[hollow:nu - hollow, hollow:nv - hollow] = False
    return u[keep], v[keep]


def test_section_props_rectangle_exact():
    u, v = _grid(8, 5)                                   # 16 x 10 mm
    sp = F.section_props(u, v, np.ones_like(u))
    assert sp["A"] == pytest.approx(160.0)
    assert sp["Iu"] == pytest.approx(16 * 10 ** 3 / 12)  # about the u axis (depth along v)
    assert sp["Iv"] == pytest.approx(10 * 16 ** 3 / 12)
    assert sp["Imin"] == pytest.approx(16 * 10 ** 3 / 12)


def test_section_props_box_and_weights():
    u, v = _grid(8, 8, hollow=2)                         # 16 x 16 box, 4 mm walls
    sp = F.section_props(u, v, np.ones_like(u))
    assert sp["A"] == pytest.approx(16 ** 2 - 8 ** 2)
    assert sp["Imin"] == pytest.approx((16 ** 4 - 8 ** 4) / 12)
    sp2 = F.section_props(u, v, np.full_like(u, 2.0))    # a uniform weight scales A and I
    assert sp2["Imin"] == pytest.approx(2 * sp["Imin"])


def test_box_beats_round_rule_and_flat_section_loses():
    """The record rule (area as a solid round) under-credits a box and over-credits a flat bar."""
    u, v = _grid(8, 8, hollow=2)
    sp = F.section_props(u, v, np.ones_like(u))
    assert sp["Imin"] > sp["A"] ** 2 / (4 * math.pi) * 1.5
    u, v = _grid(8, 4)
    sp = F.section_props(u, v, np.ones_like(u))
    assert sp["Imin"] < sp["A"] ** 2 / (4 * math.pi)


def test_euler_closed_form():
    assert F.euler_pcr(1000.0, 100.0, 1000.0) == pytest.approx(math.pi ** 2 * 0.1)
    assert F.euler_pcr(1000.0, 100.0, 1000.0, K=0.5) == pytest.approx(4 * math.pi ** 2 * 0.1)


def test_gyroid_scaling_and_tube_inputs():
    assert F.W_GYROID == pytest.approx(0.15 ** 2)
    assert F.S_GYROID == pytest.approx(0.3 * 0.15 ** 1.5)
    assert F.TUBE["id"] == 18.0                          # the reamed crown-leg bore is kept


def test_volkersen_limit_cases():
    from huntkit.fea.joints import volkersen_factor
    assert volkersen_factor(1e-9) == 1.0
    assert volkersen_factor(0.05) == pytest.approx(1.0, abs=1e-3)
    assert volkersen_factor(10.0, 1.0) > 4.9


def test_bonds_on_a_synthetic_record(tmp_path, monkeypatch):
    """A known axial force of 1000 N transferred over each sleeve gives tau = N / (pi d L) and the margins that
    follow from it; the fail-safe pin bears on two 2 mm walls."""
    monkeypatch.setattr(F, "OUT", tmp_path)
    meta = [json.dumps({"set": "s", "case": "static_carry", "factor": 2.0, "scenario": "x"})]
    cuts = {}
    for sd in ("R", "L"):
        for i, zc in enumerate(F.TUBE_CUTS):
            cuts[f"{sd}_{zc:g}"] = np.array([[1000.0 * (i + 1), 0.0, 0.0, 0.0, 0.0]])
    np.savez_compressed(tmp_path / "tube_t_fine.npz", meta=np.array(meta), **cuts)
    b = F.bonds("t", bases=("fine",))
    L = b["P1 lower node"]["L_mm"]
    N = 1000.0 * (F.TUBE_CUTS.index(192.0) + 1)          # P1: free end below, cut 192 above
    tau = N / (math.pi * F.TUBE["od"] * L)
    assert b["P1 lower node"]["avg"]["margin"] == pytest.approx(F.BOND_PA_MPA * F.BOND_HOT_WET / tau, rel=1e-2)
    pin = F.TUBE_BEARING_MPA / (N / 2.0 / (2 * F.CROSS_PIN_D * 2.0))
    assert b["P1 lower node"]["pin"]["margin"] == pytest.approx(pin, rel=1e-2)
    assert b["P2 mid-bar knuckle"]["avg"]["margin"] == pytest.approx(
        F.BOND_PA_MPA * F.BOND_HOT_WET / (1000.0 / (math.pi * F.TUBE["od"] * 36.0)), rel=1e-2)


def test_stl_lock():
    assert F.stl_md5() == F.STL_MD5


# ------------------------------------------------------------------------------------------------ published record
@pytest.fixture(scope="module")
def rec():
    if not REC_P.exists():
        pytest.skip("frame_iter1.json not written yet")
    return json.loads(REC_P.read_text())


def test_baseline_reproduces_the_bl058_record(rec):
    """Same body, same bases, same sanding: the H1 row equals bl058.json body.min (governing run)."""
    h1 = rec["concepts"]["h1"]
    for k in ("strength", "fatigue", "creep"):
        assert h1["static_cinch"][k] == pytest.approx(BL058["body"]["min"]["static_cinch"][k], abs=2e-3)
        assert h1["cinch_cycled"][k] == pytest.approx(BL058["body"]["min"]["cinch_cycled"][k], abs=2e-3)
    assert h1["static_cinch"]["buckling_record"] == pytest.approx(BL058["body"]["min"]["static_cinch"]["buckling"], abs=2e-3)
    assert h1["mass"]["delta_g"] == 0.0


def test_section_rule_flags_the_baseline(rec):
    """The section rule (real I_min) is stricter than the record rule on H1's flat members."""
    h1 = rec["concepts"]["h1"]["static_cinch"]
    assert h1["buckling_section"] < h1["buckling_record"]


def test_frame_line_and_masses(rec):
    fl = rec["frame_line_h1_g"]
    for n, r in rec["concepts"].items():
        assert r["frame_line_g"] == pytest.approx(fl + r["mass"]["delta_g"], abs=0.11)
        assert r["mass"]["frame_print_g"] == pytest.approx(sum(r["mass"]["rows"].values()), abs=0.11)
    for n in ("cfstay", "cfbox"):
        if n in rec["concepts"]:
            rows = rec["concepts"][n]["mass"]["rows"]
            tube = [v for k, v in rows.items() if k.startswith("2 carbon tubes")][0]
            assert tube == pytest.approx(2 * 0.1948 * (F.TUBE["z1"] - F.TUBE["z0"]), rel=2e-3)


def test_recommendation_follows_the_rubric(rec):
    from huntkit.gendesign import frame_iter1_report as R
    assert rec["recommended"] == R.pick(rec)
    r = rec["concepts"][rec["recommended"]]
    assert r["gate"]["R1_pass"]
    assert r["frame_line_g"] <= rec["frame_line_h1_g"]


def test_screens_exist_and_small(rec):
    for s in rec["screenshots"]:
        p = Path(s)
        if p.exists():
            assert p.stat().st_size <= 1_500_000


# ------------------------------------------------------------------------------------------------ side task
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))


def test_us1_outer_gauge_locked_to_the_current_stl():
    import physical_test_kit as K
    g = K.g2()
    assert g["stl_md5"] == K.stl_md5()
    assert K.g2_locked()
    assert "was" in g and "T1|us1_outer" in g["was"]["lines"]
    for k, v in g["tests"].items():
        for s in v["steps"]:
            assert s["pass_if_abs_microstrain_at_most"] >= abs(s["microstrain"]) - 0.5
    # the re-run moves the lines by well under 1 % (no geometry change at the outer cheek since BL-055)
    for k, old in g["was"]["lines"].items():
        new = [s["pass_if_abs_microstrain_at_most"] for s in g["tests"][k]["steps"]]
        for a, b in zip(old, new):
            assert abs(a - b) <= max(3.0, 0.01 * a)


def test_t1_us1_root_is_record_only():
    import physical_test_kit as K
    assert "US1 ROOT" in K.T1_RECORD_ONLY
    p = K.t1_patch()
    assert "US1 ROOT is RECORD ONLY" in p["pass_fail"]
    head = p["pass_fail"].split("US1 ROOT is RECORD ONLY")[0]
    assert "US2 ROOT" in head and "US1 OUTER CHEEK" in head
    assert "US1 ROOT (a)" not in head                     # no pass line for it before the record-only note
    assert "us1_outer_gauge.json (BL-061" in p["defined_in"]


def test_t1_us1_root_results_rows_are_record_only():
    import csv
    p = ROOT / "outputs" / "release" / "test_kit" / "results_template.csv"
    rows = [r for r in csv.reader(p.open(encoding="utf-8")) if len(r) > 7 and r[1] == "T1" and "US1 ROOT" in r[4]]
    assert len(rows) == 3
    assert all(r[7] == "record" and "RECORD ONLY" in r[5] for r in rows)
    other = [r for r in csv.reader(p.open(encoding="utf-8")) if len(r) > 7 and r[1] == "T1" and "US2 ROOT" in r[4]]
    assert other and all(r[7] == "band" for r in other)
