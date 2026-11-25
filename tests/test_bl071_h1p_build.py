"""BL-071 / BL-074: the PPA-CF H1-P build path (designs/pack_5200/frame_h1p_build.py) and its wiring into the test kit.
BL-074 rebuilt it from the BL-073 keys of bl070_h1p.json (coupons_bl073, bl071_requests, h1p.hip_mount, h1p.z234_joint_xy)."""
import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import frame_h1p_build as P  # noqa: E402
import physical_test_kit as K  # noqa: E402

ACTIVE = P.ACTIVE_IDS
OLD = tuple(P.SUPERSEDED)


@pytest.fixture(scope="module")
def pk():
    return P.package()


@pytest.fixture(scope="module")
def kit():
    return K.build(write=False)


def test_pass_lines_come_from_the_json_and_match_its_numbers():
    pl, rc = P.pass_lines(), P.pass_lines_recomputed()
    for k, v in rc.items():
        if k in ("lug_factor", "share_max"):
            continue
        assert pl[k] == pytest.approx(v, rel=5e-3), k          # the JSON text rounds to 3 figures
    # the orchestrator's gate numbers follow from the JSON rows: 1.15 / 1.07 rounded up, 0.91 / 1.15 rounded down
    assert pl["lug_factor"] >= rc["lug_factor"] and pl["lug_factor"] - rc["lug_factor"] < 0.01
    assert pl["share_max"] <= rc["share_max"] and rc["share_max"] - pl["share_max"] < 0.01
    assert (pl["ca3_z_mpa"], pl["ca3_sbs_mpa"], pl["ca3_k"]) == (23.7, 14.2, 2.355)
    assert (pl["ca1_smax_mpa"], pl["ca1_peak_n"], pl["ca1_temp_c"]) == (5.52, 132.0, 40.0)
    assert (pl["lug_factor"], pl["share_max"], pl["layer_s"], pl["t4c_p_n"]) == (1.08, 0.79, 181.0, 467.0)
    assert pl["t4c_z_max"] == 140 and pl["t4c_arm_mm"] == 120


def test_no_pass_line_is_typed_in_the_generator():
    src = (ROOT / "designs" / "pack_5200" / "frame_h1p_build.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    for lit in ("23.7", "14.2", "2.355", "5.52", "132", "467", "181", "143", "0.79", "24.8", "1.048"):
        assert not re.search(rf"(?<![\d.]){re.escape(lit)}(?![\d])", code), lit


def test_register_rows_and_kit_wiring(kit):
    reg = kit["register"]
    pl = P.pass_lines()
    for t in ACTIVE:
        assert reg[t]["status"] == "ACTIVE" and set(reg[t]) == set(K.COLS), t
        assert K.TEST_RELEASE[t] == "R1-PPA"
        assert "REVIEW 8" not in reg[t]["notes"], t                       # resolved notes dropped
    for t in OLD:                                                          # BL-070 rows kept, marked superseded
        assert reg[t]["status"].startswith("SUPERSEDED") and t not in K.TEST_RELEASE
    assert P.coupons_bl070()["CA-3-PPA"]["if_below_corrected"] in reg["CA-3-PPA"]["notes"]
    assert f">= {pl['ca3_z_mpa']:g} MPa" in reg["CA-3-HW"]["pass_fail"]
    assert f">= {pl['ca3_sbs_mpa']:g} MPa" in reg["CA-3-HW"]["pass_fail"]
    assert f"{pl['ca1_smax_mpa']:g} MPa" in reg["CA-1-HW"]["pass_fail"]
    assert f">= {pl['ca4_e_ratio']:g}" in reg["CA-4-HW"]["pass_fail"]
    assert f"{pl['t4c_p_n']:g} N" in reg["T4c-PPA-HW"]["pass_fail"]
    assert f"<= {pl['share_max']:g}" in reg["CLEVIS-SHARE-B-PPA"]["pass_fail"]
    assert f"x {pl['lug_factor']:g}" in reg["US2-LUG-PPA"]["title"]
    assert reg["HB-6-PPA"]["status"] == "NOT-NEEDED"
    ow = [o for o in kit["order"] if o["group"] == "G8"]
    assert [o["test"] for o in ow] == list(ACTIVE)
    assert not ({"HB-6-PPA"} | set(OLD)) & {o["test"] for o in kit["order"]}
    assert K.TEST_RELEASE["CA-1"] == "R1" and K.TEST_RELEASE["HB-6"] == "R1"     # PAHT path untouched
    assert reg["CA-3"]["pass_fail"].startswith("Z >= 37.6")


def test_results_rows_carry_the_pass_lines(kit):
    pl = P.pass_lines()
    rows = [r for r in kit["results"] if r["test_id"] in ACTIVE]
    z = next(r for r in rows if r["test_id"] == "CA-3-HW" and r["quantity"].startswith("Z tensile B-basis"))
    assert z["check"] == "min" and float(z["limit"]) == pl["ca3_z_mpa"] and z["release"] == "R1-PPA"
    cyc = [r for r in rows if r["test_id"] == "CA-1-HW" and r["unit"] == "cycles"]
    assert len(cyc) == pl["ca1_n_fat"] and all(float(r["limit"]) == pl["ca1_cycles"] for r in cyc)
    sh = next(r for r in rows if r["test_id"] == "CLEVIS-SHARE-B-PPA" and r["check"] == "max")
    assert float(sh["limit"]) == pl["share_max"]
    assert {r["test_id"] for r in rows} == set(ACTIVE)


def test_every_coupon_job_has_a_tower_and_the_frame_layer_time(pk):
    pl = P.pass_lines()
    J = pk["coupons"]["jobs"]
    assert {it["kind"] for j in J for it in j["items"]} >= {"sbs", "sbs_pause", "z", "flex", "stay", "crown", "us2"}
    for j in J:
        assert j["tower_steps"] and min(s for _, _, s in j["tower_steps"]) >= P.TOWER_MIN_MM2, j["job"]
        assert j["min_layer_s"] >= pl["layer_s"] - 0.5, j["job"]
    sp = P.spool()
    for j in J:                                      # a coupon job never changes spool mid-print
        if j["mat"] == "PPA-CF":
            assert j["filament_g"] <= sp["g"] - pl["spool_reserve_g"], j["job"]
    pause = [j for j in J if j["pause"]]
    assert len(pause) == 1 and f"{pl['ca3_pause_min']:.0f} min" in pause[0]["pause"]
    # the stay coupon is cut to z 0-140 (bl071_requests)
    assert P.pieces()["stay"]["frame"].bounds[1][2] <= pl["t4c_z_max"] + 1e-6


def test_static_loads_stay_under_the_100kg_cell_and_the_extras_are_gone(kit):
    rc = P.rig_check()
    assert rc["all_under_cell"] and rc["cell_n"] == pytest.approx(P.CELL_KG * 9.81, abs=1)
    items = " ".join(x["item"] for x in K.H1P_shopping())
    assert "200 kg" not in items and "second 6061" not in items
    assert "200 kg" not in P.package()["docs"]["COUPONS_H1P.md"].split("## 3.")[1].split("## 4.")[0].replace("200 kg cell and the second lever bar BL-071", "")


def test_spools_and_cost_follow_the_plan(pk):
    s, c, sp = pk["spools"], pk["cost"], P.spool()
    assert c["filament_usd"] == pytest.approx(s["spools"] * sp["usd"])
    assert s["booked_bl073"] == 5
    used = s["spools"] * sp["g"] - s["left_g"]
    sw = P.h1p_json()["bl073"]["spool_plan"]
    band = sum(k * (sw[h]["swap"]["spool1_g_range"][1] - sw[h]["swap"]["spool1_g_range"][0]) for h, k in (("lower", 1), ("upper", 2)))
    assert used == pytest.approx(s["total_g"] + band, abs=3)       # each change booked high on both spools
    for r in s["rows"]:
        assert r["left_g"] >= s["reserve_g"] - 0.5
    assert "BL-073 booked 5" in pk["docs"]["BUILD_H1P.md"]


def test_hip_trap_free_ring_torque_and_threads_proud(pk):
    h = pk["hip"]
    pl = P.pass_lines()
    assert h["n"] == 8 and h["screw_len"] == 35 and h["torque"] == pytest.approx(0.6)
    assert h["torque_inlbf"] == pytest.approx(5.3, abs=0.05)
    # BL-073 rule: >= 2 threads proud (BL-071's zero-protrusion test retired); the JSON gives 5
    assert h["protrusion_threads"] >= P.THREADS_PROUD_MIN and h["protrusion_threads"] == 5
    assert h["threads_calc"] == pytest.approx(h["protrusion_threads"])
    assert h["boss"]["traps"] == 0
    b = pk["docs"]["BUILD_H1P.md"]
    sec5 = b.split("## 5. Hip mount")[1].split("## 6.")[0]
    assert "0.6 N m (5.3 in lbf)" in sec5 and "Wera 7440" in sec5 and "preload is gone at -20 C" in sec5
    assert "No HA-LS-1 row relies on it" in sec5 and "SendCutSend" in sec5
    # BL-075 additions
    c = P.bl075()
    assert f"{c['tail_min']:g}-{c['tail_max']:g} mm" in sec5 and (c["tail_min"], c["tail_max"]) == (3.1, 5.2)
    assert "BL075-CORD" in sec5 and f"|x| {c['cord_x']:g} mm" in sec5 and "TPU" in sec5 and "do not force it" in sec5
    items = [x.item for x in P.bom()]
    assert any("M5 x 35" in i and "DIN 7984" in i for i in items) and any("DIN 934" in i for i in items)
    assert any("HW-HIP-RING" in i for i in items) and any("HW-HIP-KEEP" in i for i in items)
    assert any("Wera 7440" in i for i in items) and not any("heat-set" in i.lower() for i in items)
    assert "trap" not in " ".join(items).lower()


def test_z234_bolt_positions_from_the_json(pk):
    b = pk["docs"]["BUILD_H1P.md"].split("## 4. z 234 joint")[1].split("## 5.")[0]
    for x, y in P.h1p_json()["h1p"]["z234_joint_xy"]["bl073"]:
        assert f"({x:+.1f}, {y:+.1f})" in b


def test_print_sheet_pads_change_and_source(pk):
    ps = pk["print_sheet"]
    rows = {a: (b, c) for a, b, c in ps["rows"]}
    assert "mouse ears" not in rows and "snap-off pads" in rows
    assert "Add Pause" in rows["filament change"][0] and "wiki.bambulab.com" in rows["filament change"][1]
    assert all(c.strip() for _, _, c in ps["rows"])
    sp = P.h1p_json()["bl073"]["spool_plan"]
    for h in ps["halves"]:
        assert h["file"].endswith("_flat_print.stl") and (ROOT / h["file"]).exists()
        assert h["swap"]["layer"] == sp[h["half"]]["swap"]["layer"]
    md = pk["docs"]["PRINT_SHEET_H2S.md"]
    assert "layer 134" not in md or "**134**" in md
    assert "40.05 mm" in md and "30.15 mm" in md and "**134**" in md and "**101**" in md
    assert "flush cutters" in md and "Add Pause" in md


def test_hold_gate_and_release(pk):
    for name in ("PRINT_SHEET_H2S.md", "BUILD_H1P.md", "COUPONS_H1P.md", "README.md"):
        d = pk["docs"][name]
        assert P.HOLD in d and P.RELEASED in d, name
        assert "x 1.08 load" in d and "share <= 0.79" in d, name
    c = pk["docs"]["COUPONS_H1P.md"]
    assert c.index("FA-H1P-UP") < c.index("## 2.")                       # first article before the coupons


def test_released_files_match_the_generator(pk):
    for name, txt in pk["docs"].items():
        for d in (P.PRINT, P.REL):
            f = d / name
            assert f.exists(), f
            assert f.read_text(encoding="utf-8") == txt, f
    g8 = ROOT / "outputs" / "release" / "test_kit" / "guides" / "G8.md"
    assert g8.exists() and "CA-3-HW" in g8.read_text()
    with open(ROOT / "designs" / "pack_5200" / "tests_physical" / "test_register.csv", newline="", encoding="utf-8") as f:
        ids = {r["id"]: r["status"] for r in csv.DictReader(f)}
    assert set(ACTIVE) | set(OLD) | {"HB-6-PPA"} <= set(ids)
    for j in pk["coupons"]["jobs"]:
        assert (P.TP_DIR / f"tower_{j['job']}.stl").exists()
    for f in ("t4c_stay_R.stl", "crown_corner_R.stl", "us2_route_stay_R_h1p.stl"):
        assert (P.TP_DIR / f).exists()


def test_coupon_pieces_are_single_watertight_bodies():
    for k in ("stay", "crown", "us2"):
        q = P.pieces()[k]
        assert q["watertight"] and q["bodies"] == 1, k
    pm = P.t4c_print_mesh()
    assert pm.bounds[0] == pytest.approx([0, 0, 0], abs=1e-6)


def test_sheets_are_beginner_steps_with_imperial():
    st = P.guide_steps()
    for t in ACTIVE:
        assert len(st[t]) >= 6, t
        txt = " ".join(st[t])
        assert re.search(r"\d[\d,]*(\.\d+)? ?(in|F|lb|lbf|oz)\b", txt), t
