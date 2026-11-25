"""BL-078: the PAHT-CF coupons that decide the H1 frame (designs/pack_5200/frame_h1_paht_coupons.py), their wiring into
the test kit as the next session (G0), the SAFETY HOLD on the released H1 and the PARKED mark on the PPA-CF docs."""
import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1_paht_coupons as P  # noqa: E402
import frame_h1p_build as H1P  # noqa: E402
import physical_test_kit as K  # noqa: E402


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


@pytest.fixture(scope="module")
def pk():
    return P.package()


def test_pass_lines_come_from_bl077_and_match_its_numbers():
    pl, rc = P.pass_lines(), P.pass_lines_recomputed()
    for k, v in rc.items():
        assert pl[k] == pytest.approx(v, abs=max(0.005 * abs(v), 0.051)), k      # the JSON text rounds to 3 figures
    # BL-079: every minimum line rounded UP to 0.1 MPa (was 19.0 / 26.7 / 15.4, slightly lenient)
    assert (pl["z_line"], pl["sbs_line"], pl["z_joint"], pl["sbs_joint"]) == (19.1, 11.0, 26.8, 15.5)
    for k in ("z_line", "sbs_line"):
        assert pl[k] >= rc[k] - 1e-9 and pl[k] >= {"z_line": pl["z_hw"], "sbs_line": pl["tau_hw"]}[k] / pl["m_body"]
    # BL-079: test load rounded up; E ratio covers the record-rule buckling row too (0.6 / 1.654 = 0.363)
    assert (pl["k10"], pl["c1_smax"], pl["c1_peak_n"], pl["c4_e_ratio"], pl["share_max"]) == (2.355, 5.43, 131.0, 0.37, 0.6)
    # BL-079: the floor at the real 0.20 mm profile (was 237 s at 0.3 mm)
    assert pl["layer_s"] == pl["layer_s_json"] == 175.0 and pl["layer_h_bl077"] == P.frame_layer_h() == 0.2
    assert (pl["c1_nose_d"], pl["c1_pin_d"], pl["c1_span"]) == (6.0, 3.0, 12.0)       # ASTM D2344 nose and supports
    assert pl["cond_c"] == 50.0
    assert (pl["n_z_hw"], pl["n_z_dry"], pl["n_sbs_hw"], pl["n_sbs_dry"]) == (10, 6, 10, 6)


def test_no_pass_line_is_typed_in_the_generator():
    src = (ROOT / "designs" / "pack_5200" / "frame_h1_paht_coupons.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for lit in ("19.1", "26.8", "11.0", "15.5", "2.355", "5.425", "5.43", "0.37", "0.60", "0.909", "0.481", "175", "1.034",
                "36.8", "21.3", "89.7", "40.9", "23.6", "0.52", "0.59"):
        assert not re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d])", code), lit


def test_jobs_hold_the_frame_layer_time_by_dwell_not_towers(pk):
    pl = P.pass_lines()
    J = pk["coupons"]["jobs"]
    assert {it["kind"] for j in J for it in j["items"]} == {"sbs", "z", "flex", "traveller"}
    for j in J:
        # BL-079: only the 15 x 15 mm prime pillar, the layer time comes from the per-layer dwell
        assert [s for _, _, s in j["tower_steps"]] == [P.TOWER_MIN_MM2]
        assert j["min_layer_s"] >= pl["layer_s"] - 0.5 and j["min_printed_s"] + j["dwell_s"] >= pl["layer_s"], j["job"]
        assert j["dwell_s"] < pl["layer_s"]
    assert pk["coupons"]["tower_g"] < 30.0                     # BL-078 towers were 709 g
    assert "Layer change G-code" in " ".join(P.print_steps()) and "G4" in " ".join(P.print_steps())
    bk = P.blocks()
    assert bk["z"]["n"] == pl["n_z_hw"] + pl["n_z_dry"] + P.SPARES and max(bk["z"]["combs"]) == pl["comb_n"]
    assert bk["sbs"]["n"] >= pl["n_sbs_hw"] + pl["n_sbs_dry"] + pl["c1_n_fat"] + pl["c1_n_static"]
    m = P.comb_mesh(10)
    assert m.is_watertight and m.body_count == 1 and m.bounds[0] == pytest.approx([0, 0, 0], abs=1e-6)
    assert m.extents[2] == pytest.approx(75.0) and m.extents[1] == pytest.approx(pl["z_t"])
    poly, g = P.iso1ba_outline()
    assert poly.is_valid and g["l1"] == 30.0 and poly.bounds[2] - poly.bounds[0] == pytest.approx(10.0)


def test_cost_inside_the_proving_cap(pk):
    c = pk["cost"]
    assert c["within_cap"] and c["all_in_usd"] <= c["cap_usd"] == 150.0
    assert c["new_usd"] <= 60.0                                 # BL-079 aim (was USD 114.12 with the towers)
    assert c["new_usd"] + P.fallback_tower_usd() <= c["cap_usd"]   # the tower fallback still fits the cap
    assert sum("D2344" in x["item"] for x in c["lines"]) == 1    # one pin set, no double count
    assert c["filament_usd"] == pytest.approx(c["filament_g"] * P.usd_per_g(), abs=0.02)
    assert all(x["source"].startswith(("record", "bl077", "ASSUMPTION")) for x in c["lines"])
    assert P.rig_check()["all_under_cell"]


def test_outcomes_name_the_three_paths_and_the_h1_line_from_bl077():
    oc = P.outcomes()
    means = " ".join(o["means"] for o in oc)
    assert P.OUT_RE in means and P.OUT_H1C in means and P.OUT_H1 in means
    assert oc[0]["means"].startswith(P.OUT_H1)                  # read top-down: H1 as is is checked first
    h = P.b77()["h1_as_is"]
    pl = P.pass_lines()
    # BL-079: the released H1 is not reachable on Z / SBS (in-plane terms saturate), so the row says it is not cleared
    assert not h["sleeved"]["layer_route"]["reachable"] and not pl["h1_sleeved_ok"]
    assert "NOT cleared" in oc[0]["means"]
    for v in (pl["h1_sleeved_ratio"], pl["h1_sleeved_ratio_z"], *pl["h1_sleeved_all"], pl["h1_e_ratio"]):
        assert f"{v:g}" in oc[0]["if"], v


def test_kit_wiring_g0_first(kit):
    reg = kit["register"]
    for t in P.IDS:
        assert reg[t]["status"] == "ACTIVE" and set(reg[t]) == set(K.COLS), t
        assert K.TEST_RELEASE[t] == "PAHT-COUPONS"
    ow = kit["order"]
    assert [o["test"] for o in ow[:len(P.IDS)]] == list(P.IDS) and all(o["group"] == "G0" for o in ow[:len(P.IDS)])
    pl = P.pass_lines()
    z = next(r for r in kit["results"] if r["test_id"] == "CA-3-PAHT" and r["check"] == "min" and r["quantity"].startswith("Z tensile B-basis"))
    assert float(z["limit"]) == pl["z_line"] and "REDESIGN" in z["quantity"]
    sh = next(r for r in kit["results"] if r["test_id"] == "CLEVIS-SHARE-B-PAHT" and r["check"] == "max")
    assert float(sh["limit"]) == pl["share_max"]
    # the PPA path is untouched in the kit (G8, R1-PPA) but marked parked
    assert K.TEST_RELEASE["CA-1"] == "R1" and "PARKED" in next(g for g in K.GROUPS if g["id"] == "G8")["title"]


def test_hold_marks_cover_the_stand_session():
    g6 = next(g for g in K.GROUPS if g["id"] == "G6")["tests"]
    assert set(g6) <= set(P.HOLD_CLASS)
    for t in ("T1", "T2", "T2u", "T3", "IM3-EP", "CR-1", "T4a"):
        assert P.HOLD_CLASS[t][0] == "HOLD", t
    assert P.hold_mark("MH-1", "G7")[0] == "HOLD"


def test_sheets_are_beginner_steps_with_imperial():
    st = P.guide_steps()
    for t in P.IDS:
        assert len(st[t]) >= 6, t
        assert re.search(r"\d[\d,]*(\.\d+)? ?(in|F|lb|lbf|oz)\b", " ".join(st[t])), t


def test_written_files(pk):
    md = pk["docs"]["COUPONS_PAHT.md"]
    for d in (P.PRINT, P.REL):
        assert (d / "COUPONS_PAHT.md").read_text(encoding="utf-8") == md
    assert P.SAFETY_HOLD in md and "What the results mean" in md
    for f in ("block_sbs.stl", "bend_bar.stl", "traveller.stl", "tower_A.stl", "tower_B.stl", "z_comb_10.stl"):
        assert (P.CP_DIR / f).exists(), f
    for name in ("BUILD_H1.md", "README.md"):
        assert P.SAFETY_HOLD in (P.PRINT / name).read_text(encoding="utf-8"), name
    for name in ("COUPONS_H1P.md", "BUILD_H1P.md", "PRINT_SHEET_H2S.md", "README.md"):
        assert H1P.PARKED in (H1P.PRINT / name).read_text(encoding="utf-8"), name
    kit_dir = ROOT / "outputs" / "release" / "test_kit"
    assert P.SAFETY_HOLD in (kit_dir / "README.md").read_text() and P.SAFETY_HOLD in (kit_dir / "guides" / "G6.md").read_text()
    assert "CA-3-PAHT" in (kit_dir / "guides" / "G0.md").read_text()
    with open(ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv", newline="", encoding="utf-8") as f:
        ids = {r["id"] for r in csv.DictReader(f)}
    assert set(P.IDS) <= ids
    for n in (1, 2, 3):
        s = P.SCREENS / f"{P.SHOT}_{n}.png"
        assert s.exists() and s.stat().st_size <= 1.5e6
    s = P.SCREENS / f"{P.SHOT_BL079}.png"
    assert s.exists() and s.stat().st_size <= 1.5e6
