"""BL-071: the PPA-CF H1-P build path (designs/pack_5200/frame_h1p_build.py) and its wiring into the test kit."""
import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1p_build as P  # noqa: E402
import physical_test_kit as K  # noqa: E402

PPA_TESTS = ("CA-3-PPA", "CA-1-PPA", "CA-4-PPA", "T4c-PPA")


@pytest.fixture(scope="module")
def pk():
    return P.package()


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def test_pass_lines_come_from_the_json_and_match_its_numbers():
    pl, rc = P.pass_lines(), P.pass_lines_recomputed()
    for k, v in rc.items():
        assert pl[k] == pytest.approx(v, rel=5e-3), k          # the JSON text rounds to 3 figures
    assert (pl["ca3_z_mpa"], pl["ca3_sbs_mpa"], pl["ca1_smax_ratio"]) == (31.3, 18.8, 0.279)
    assert (pl["ca4_e40"], pl["ca4_e60"], pl["ca4_flex60_mpa"], pl["t4c_drop_m"]) == (0.85, 0.75, 152.0, 1.22)
    assert pl["hb6_ppa_n"] == 488.0


def test_no_pass_line_is_typed_in_the_generator():
    src = (ROOT / "designs" / "pack_5200" / "frame_h1p_build.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for lit in ("31.3", "18.8", "0.279", "152", "1.22", "488"):
        assert not re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d])", code), lit


def test_register_rows_and_kit_wiring(kit):
    reg = kit["register"]
    pl = P.pass_lines()
    for t in PPA_TESTS:
        assert reg[t]["status"] == "ACTIVE" and set(reg[t]) == set(K.COLS), t
        assert K.TEST_RELEASE[t] == "R1-PPA"
    assert f">= {pl['ca3_z_mpa']:g} MPa" in reg["CA-3-PPA"]["pass_fail"]
    assert f">= {pl['ca3_sbs_mpa']:g} MPa" in reg["CA-3-PPA"]["pass_fail"]
    assert f"{pl['ca1_smax_ratio']:g} x" in reg["CA-1-PPA"]["pass_fail"]
    assert f">= {pl['ca4_e40']:g}" in reg["CA-4-PPA"]["pass_fail"] and f"{pl['ca4_flex60_mpa']:g} MPa" in reg["CA-4-PPA"]["pass_fail"]
    assert reg["HB-6-PPA"]["status"] == "NOT-NEEDED" and "through-bolt" in reg["HB-6-PPA"]["notes"]
    ow = [o for o in kit["order"] if o["group"] == "G8"]
    assert [o["test"] for o in ow] == list(PPA_TESTS)
    assert "HB-6-PPA" not in {o["test"] for o in kit["order"]}
    # PAHT path untouched: CA-1 / CA-3 / HB-6 still on R1
    assert K.TEST_RELEASE["CA-1"] == "R1" and K.TEST_RELEASE["HB-6"] == "R1"
    assert reg["CA-3"]["pass_fail"].startswith("Z >= 37.6")


def test_results_rows_carry_the_pass_lines(kit):
    pl = P.pass_lines()
    rows = {(r["test_id"], r["quantity"]): r for r in kit["results"] if r["test_id"] in PPA_TESTS}
    z = rows[("CA-3-PPA", f"Z tensile, mean - {pl['ca3_k_sd']:g} SD")]
    assert z["check"] == "min" and float(z["limit"]) == pl["ca3_z_mpa"] and z["release"] == "R1-PPA"
    s = rows[("CA-3-PPA", f"short-beam shear, mean - {pl['ca3_k_sd']:g} SD")]
    assert float(s["limit"]) == pl["ca3_sbs_mpa"]
    cyc = [r for r in kit["results"] if r["test_id"] == "CA-1-PPA" and r["unit"] == "cycles"]
    assert len(cyc) == pl["ca1_n_z"] + pl["ca1_n_xy"] and all(float(r["limit"]) == pl["ca1_cycles"] for r in cyc)
    fr = [r for r in kit["results"] if r["test_id"] == "T4c-PPA" and r["unit"] == "C"]
    assert fr and fr[0]["check"] == "max" and float(fr[0]["limit"]) == pl["t4c_temp_c"]


def test_coupons_are_about_one_spool_and_the_spool_plan_closes(pk):
    cp, sp = pk["coupons"], pk["spools"]
    assert cp["gate_filament_g"] <= cp["spool_g"]
    assert cp["swap_fits_spool_b"]
    assert sp["frame_path_spools"] == 3 and sp["frame_path_usd"] == pytest.approx(450, abs=1)
    assert sp["t4c_fits_4_spools"]
    assert cp["t4c_filament_g"] > cp["spool_g"] - cp["gate_filament_g"] - cp["swap_g"]   # T4c does need the 4th spool
    # counts follow the JSON: 6 + 6 fatigue (+1 spare), CA-3 6+6 per condition, CA-4 5 x 3
    by = {r["for"]: r for r in cp["rows"]}
    assert by["CA-1-PPA fatigue"]["count"] == 7 and by["CA-4-PPA, 3 conditions"]["count"] == 16


def test_hip_through_bolts_torque_traces_and_inserts_are_gone(pk):
    h = pk["hip"]
    assert h["n"] == 8 and h["screw_len"] == pytest.approx(h["flange_t"] + h["seat"] + h["nut_t"])
    assert h["torque"] <= h["torque_calc"] < h["torque"] + 0.05
    assert h["f_pre"] == pytest.approx(h["rup"] * h["z_allow"] * h["a_dw"] / P.CREEP_GOAL)
    b = pk["docs"]["BUILD_H1P.md"]
    sec5 = b.split("## 5. Hip mount")[1].split("## 6.")[0]
    assert "TB-TORQUE" in sec5 and f"{h['torque']:.2f} N m" in sec5 and "in lbf" in sec5
    assert "soldering" not in sec5.lower() and "insert-setting guide" not in sec5.lower()
    assert "heat-set" not in sec5.lower()
    assert "TB-TORQUE" in P.ASSUMPTIONS and "K-NUT" in P.ASSUMPTIONS
    items = [x.item for x in P.bom()]
    assert any("M5 x 20" in i and "DIN 7984" in i for i in items) and any("DIN 934" in i for i in items)
    assert not any("heat-set" in i.lower() for i in items)


def test_print_sheet_values_and_sources(pk):
    ps = pk["print_sheet"]
    p = P.ppa()["properties"]
    rows = {a: (b, c) for a, b, c in ps["rows"]}
    assert f"{p['nozzle_temp_c']} C" in rows["nozzle"][0] and p["nozzle_temp_c"] == 290
    assert f"{p['bed_temp_c']} C" in rows["bed"][0] and p["bed_temp_c"] == 110
    assert f"{p['chamber_temp_c']} C" in rows["chamber"][0] and p["chamber_temp_c"] == 65
    assert "120 C" in rows["dryer"][0] and "30 min" in rows["chamber pre-heat"][0]
    assert "15 mm" in rows["brim"][0] and "20 mm" in rows["mouse ears"][0]
    assert rows["anneal"][0].startswith("NO")
    assert all(c.strip() for _, _, c in ps["rows"])                       # every value has a source
    pr = P.h1p_json()["h1p"]["print"]
    for h in ps["halves"]:
        assert h["print_h"] == pr[h["half"]]["print_h_est"] and h["swap"] and h["swap_after_h"] < h["print_h"]
    md = pk["docs"]["PRINT_SHEET_H2S.md"]
    assert "PAHT-CF dried 80" not in md and "anneal 90" not in md.lower()


def test_cost_is_three_spools_plus_the_dryer(pk):
    c = pk["cost"]
    sp = P.spool()
    assert c["filament_frame_usd"] == pytest.approx(3 * sp["usd"])
    assert c["dryer_usd"] > 0 and "ASSUMPTION" in P.DRYER["source"]
    assert c["filament_t4c_usd"] == pytest.approx(sp["usd"])


def test_t4c_stay_coupon_mesh():
    t = P.t4c_stay_mesh()
    assert t.is_watertight and t.body_count == 1
    assert t.bounds[0][0] == pytest.approx(P.T4C_CUT["x_min"], abs=0.01) and t.bounds[1][2] <= P.T4C_CUT["z_max"] + 1e-6
    pm = P.t4c_print_mesh(t)
    assert pm.extents[2] == pytest.approx(t.extents[1], abs=1e-3)        # layers stacked along frame y (face down)
    assert pm.bounds[0] == pytest.approx([0, 0, 0], abs=1e-6)


def test_released_files_match_the_generator(pk):
    for name, txt in pk["docs"].items():
        for d in (P.PRINT, P.REL):
            f = d / name
            assert f.exists(), f
            assert f.read_text(encoding="utf-8") == txt, f
    g8 = ROOT / "outputs" / "release" / "test_kit" / "guides" / "G8.md"
    assert g8.exists() and "CA-3-PPA" in g8.read_text()
    with open(ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv", newline="", encoding="utf-8") as f:
        ids = {r["id"] for r in csv.DictReader(f)}
    assert set(PPA_TESTS) | {"HB-6-PPA"} <= ids
    assert (P.TP_DIR / "t4c_stay_R.stl").exists()


def test_sheets_are_beginner_steps_with_imperial():
    st = P.guide_steps()
    for t in PPA_TESTS:
        assert len(st[t]) >= 6, t
        txt = " ".join(st[t])
        assert re.search(r"\(\d+(\.\d+)? ?(in|F|lb|lbf)\)", txt) or " F)" in txt or "in)" in txt, t
