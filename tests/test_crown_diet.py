"""BL-017 crown block diet (huntkit.gendesign.crown_diet). Beam-model checks run at one or two torsos (a few
seconds each); the voxel body numbers are read from the committed results JSON."""
import dataclasses
import json
import math

import pytest

from huntkit.gendesign import crown_diet as C


def test_size_geometry_matches_h1_governing_overlap():
    # every size, at its top setting, has H1's 23 in leg overlap (155.8 mm)
    for sz, (lo, hi) in C.SIZES.items():
        assert C.overlap_mm(hi, C.size_leg_mm(sz)) == pytest.approx(C.overlap_mm(23.0), abs=0.1)
        assert C.size_travel_mm(sz) == pytest.approx(76.2, abs=0.2)            # +-1.5 in
    assert C.size_leg_mm("L") == pytest.approx(430.0, abs=0.1)
    assert C.size_spine_mm("L") == pytest.approx(300.0, abs=0.1)
    assert C.size_leg_mm("S") == pytest.approx(303.0, abs=0.5)
    # three sizes cover 15-23 in with overlap
    assert C.SIZES["S"][0] == 15.0 and C.SIZES["L"][1] == 23.0
    assert C.SIZES["M"][0] < C.SIZES["S"][1] and C.SIZES["L"][0] < C.SIZES["M"][1]


def test_block_items_and_ledger():
    blk = C.block_items()
    assert blk["crown legs 2 x 430 mm (OD 16, rev C)"] == pytest.approx(88.1, abs=0.1)
    soft = sum(v for k, v in blk.items() if k.startswith(("pulley webbing", "cam", "release")))
    lb = C.ledger_basis()
    assert soft == pytest.approx(lb["torso_adjust_g"], abs=0.01) == pytest.approx(C.TORSO_ADJUST_ROW_G, abs=0.01)
    assert 250.0 < sum(blk.values()) < 265.0                                     # ticket: "about 250 g"
    # BL-035: 3927.0 (BL-017) -> 3973.5 g = +26.0 #10 door sliders, +16.0 stainless US tri-glides, +1.9 IMP-4 #5 slider
    # (BL-034 records) + 4.5 elastic hook keepers, -0.8 lifter tri-glides, -1.1 torso adjust (BL-035 records)
    assert lb["pack_g"] == pytest.approx(3973.5, abs=0.1)
    assert C.TORSO_ADJUST_ROW_G == pytest.approx(25.2 + 12.2 + 1.5 + 1.7, abs=0.01)   # web + cam + cord + toggle records


def test_option_masses():
    h = C.option_mass(C.Option("x"), "M")
    assert h["delta_g"] == 0.0
    d1 = C.option_mass(C.Option("d1", lock="pawl"), "L")["delta_g"]
    assert d1 == pytest.approx(-(25.2 + 12.2 + 8.0), abs=0.05)          # cam_25mm_al record 12.2 g (BL-035; was 12.0)
    a_l = C.option_mass(C.Option("a", kit=True), "L")
    assert a_l["items"].get("crown legs", 0.0) == pytest.approx(0.0, abs=0.01)    # L keeps 430 mm legs
    a_s = C.option_mass(C.Option("a", kit=True), "S")
    assert a_s["items"]["crown legs"] == pytest.approx(-2 * 0.10246 * 127.0, abs=0.3)


def test_leg_section_family():
    ref = C.leg_section(16.0, 8)
    assert ref.dims["t"] == pytest.approx(1.44, abs=1e-3)                       # frame.yaml rev C leg
    s17 = C.leg_section(17.0, 7)
    assert s17.Ex * s17.Iy > ref.Ex * ref.Iy                                     # stiffer
    assert C.leg_g_per_mm(17.0, 7) < C.leg_g_per_mm(16.0, 8)                      # lighter


@pytest.fixture(scope="module")
def h1_23():
    spec = C.Spec("t_h1", torsos=(23.0,))
    return C.beam_runs(spec, log=None)


def test_h1_crown_reproduced(h1_23):
    _, rows = h1_23
    m = C.crown_margins(rows)["min"]
    assert m["crown_leg"]["sf"] == pytest.approx(1.116, abs=0.002)              # rev C record, IM3 C8 23 in
    assert "hipbelt_off_abuse|23" in m["crown_leg"]["set"]
    assert m["rack"]["sf"] == pytest.approx(6.27, abs=0.01)


def test_h1_spine_and_top_bar_at_15():
    _, rows = C.beam_runs(C.Spec("t_h1_15", torsos=(15.0,)), log=None)
    m = C.crown_margins(rows)["min"]
    assert m["crown_spine"]["sf"] == pytest.approx(1.178, abs=0.002)
    assert m["crown_top_bar"]["sf"] == pytest.approx(1.246, abs=0.002)
    assert m["corner_bond_peak"]["sf"] == pytest.approx(1.217, abs=0.002)        # C6p posts


def test_kit_s_top_setting_not_worse_than_h1():
    sp = C.specs()["a_S"]
    _, rows = C.beam_runs(dataclasses.replace(sp, torsos=(18.0,)), log=None)
    m = C.crown_margins(rows)["min"]
    assert m["crown_leg"]["sf"] >= 1.116
    assert m["leg_ring_crush"]["sf"] > 1.0


def test_thin_legs_fail_honestly():
    _, rows = C.beam_runs(C.Spec("t_c17n6", torsos=(23.0,), leg=(17.0, 6), bushing_wall=0.5), log=None)
    assert C.crown_margins(rows)["min"]["crown_leg"]["sf"] < 1.0                 # same stiffness is not same strength


def test_e50_changes_checks_not_loads(h1_23):
    sets0, rows0 = h1_23
    sets1, rows1 = C.beam_runs(C.Spec("t_e50", torsos=(23.0,), bushing_mm=50.0), log=None)
    for a, b in zip(sets0, sets1):
        for (ta, za, fa), (tb, zb, fb) in zip(a.bushings, b.bushings):
            assert za == zb and max(abs(x - y) for x, y in zip(fa, fb)) < 1e-6
    m0, m1 = C.crown_margins(rows0)["min"], C.crown_margins(rows1)["min"]
    assert m1["leg_ring_crush"]["sf"] == pytest.approx(m0["leg_ring_crush"]["sf"] * 50 / 70, rel=0.02)


def test_leg_holes_and_locks(h1_23):
    _, rows = h1_23
    _, rows15 = C.beam_runs(C.Spec("t_h1_15b", torsos=(15.0,)), log=None)
    hz = C.leg_hole_zone(rows + rows15)
    # with the full 15-23 in range a hole fails below the low-bushing top: no travel for a leg cross-pin
    assert hz["max_travel_mm"] == 0.0 and hz["z_hole_fails_above"] < hz["low_bushing_top_at_highest_setting"]
    pl = C.plunger_lock_check(rows)
    assert min(pl["strip_bearing_sf"], pl["strip_shear_out_sf"], pl["plunger_bending_sf"]) > 1.5
    st = C.pull_strap_d2(rows)
    assert st["ok"] and st["tail_hoist_static_n"] == pytest.approx(st["crown_force_static_n"] * math.exp(0.1 * math.pi), rel=1e-3)


def test_results_recommended_option():
    d = json.loads(C.RESULT.read_text())
    rec = d["masses"][d["recommended"]]
    assert all(-rec[sz]["delta_g"] >= 60.0 for sz in C.SIZES)                    # goal at every size
    for k in ("acb_S", "acb_M", "acb_L", "c17b19"):
        assert d["crown"][k]["min_all"] >= 1.0
        assert d["crown"][k]["min"]["crown_leg"]["sf"] >= d["crown"]["h1"]["min"]["crown_leg"]["sf"]
    b = d["body"]
    assert b["h1_recorded_basis"]["min"]["fatigue"] == pytest.approx(1.279, abs=0.003)   # H1 reproduced
    assert b["h1_recorded_basis"]["min"]["strength"] == pytest.approx(1.453, abs=0.003)
    assert min(b["acb19"]["min"].values()) >= 1.0 and b["acb19"]["buckling_min"] >= 1.0
    # the crown kits alone do not move the body (L 23 in is H1's governing geometry)
    assert b["a"]["min"]["fatigue"] == pytest.approx(b["h1"]["min"]["fatigue"], abs=0.002)
