"""BL-045: crown tube under the B-25 mitre, spine clamp, IM / US fairlead clearance, loose island, stale records."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
ANALYSIS = REPO / "designs" / "pack_5200" / "analysis"
PRINT = REPO / "designs" / "pack_5200" / "print" / "frame_h1"


# ------------------------------------------------------------------------------------------- 1. crown tube
@pytest.fixture(scope="module")
def crown():
    from huntkit.gendesign import crown_tube_guy_loop as CT
    return CT.b25_topology_recheck()


def test_mitre_and_run_are_off_the_bar(crown):
    t = crown["topology"]
    assert not t["mitre_on_bar"]
    assert t["on_bar"]["sleeve"]["width_mm"] == pytest.approx(38.0)
    for v in t["off_bar"].values():
        assert v["s_mm"][0] >= 9.0 - 1e-9              # nothing of B-25 but the sleeve is above the bar's underside


def test_bl041_scalar_case_reproduced(crown):
    r = crown["checks"]["bl041_scalar"]
    assert r["sf_static"] == pytest.approx(1.36, abs=0.01)
    assert r["sf_fatigue"] == pytest.approx(1.27, abs=0.01)


def test_pull_vectors_and_run_tension(crown):
    # the real vector sum stays within 1 % of BL-041's scalar sum; the in-line bound adds at most the 0.136 x guy
    assert 0.95 <= crown["k_vector_max"] <= 1.02
    assert crown["k_bound_max"] <= 1.0 + crown["max_outboard_share"] + 1e-6
    for k in ("vector", "bound"):
        assert crown["checks"][k]["sf_static"] >= 1.0
        assert crown["checks"][k]["sf_fatigue"] >= 1.0
    # if the 30 mm toggle's pull did not spread over the 38 mm sleeve, the bound case would fail (TL-1 decides)
    assert crown["checks"]["bound_toggle_width"]["sf_static"] < 1.0
    assert crown["spine_wrap"]["sf"] > 3.0


def test_radial_sum_by_hand(crown):
    r = crown["k_vector_run"]
    ug = np.array(r["guy_dir_on_bar"])
    assert np.linalg.norm(ug) == pytest.approx(1.0, abs=0.01)
    assert r["run_tension_1g_n"] == pytest.approx(r["guy_1g_n"] * max(r["outboard_share"], 0.0), abs=0.06)


# ------------------------------------------------------------------------------------------- 2. spine clamp
@pytest.fixture(scope="module")
def clamp():
    from huntkit.gendesign import crown_spine_clamp as C
    rows = C.joint_loads()
    return C, rows, C.size_clamp(rows), C.h1_crown_interfaces()


def test_bond_check_closed_form(clamp):
    """Pure axial load on the socket: average shear = N / (2 pi r L), allowable 20 MPa x 0.8 (MMA on CFRP)."""
    C, _, _, _ = clamp
    row = [{"kit": "x", "torso": 0.0, "variant": "v", "case": "c", "req": 1.0, "g": 1.0,
            "spine": [1000.0, 0, 0, 0, 0, 0], "jump": [1000.0, 0, 0, 0, 0, 0]}]
    m = C.bond_margins(row, "spine", 20.0)
    assert m["avg"]["sf"] == pytest.approx(20.0 * 0.8 / (1000.0 / (2 * math.pi * 10.0 * 20.0)), rel=1e-3)


def test_joint_loads_cover_every_set(clamp):
    C, rows, c, _ = clamp
    kits = {r["kit"] for r in rows}
    assert kits == {"a_S", "a_M", "a_L"}
    assert len({r["case"] for r in rows}) >= 9
    assert c["loads_max_factored"]["spine_M_max_nm"] > 20.0      # the joint carries real moment (never checked before)
    # BL-045's model basis (spine rigid on TB1 in the bar's plane): 55 N m at the spine's top
    assert C._load_summary(C.joint_loads(real=False))["spine_M_max_nm"] > 40.0


def test_clamp_passes_the_frame_joint_rule(clamp):
    _, _, c, _ = clamp
    for k in ("socket", "saddle"):
        m = c["margins"][k]
        assert m["avg"]["sf"] >= 1.0 and m["peak"]["sf"] >= 1.0 and m["fat_avg"]["sf"] >= 1.0
    assert c["margins"]["socket_bending"]["sf_yield"] >= 1.0
    assert c["saddle_len_mm"] >= c["socket_od_mm"]


def test_published_constants_match(clamp):
    C, _, c, g = clamp
    assert C.SPINE_CLAMP_HALF_X == pytest.approx(c["half_x_mm"], abs=0.05)
    assert C.SPINE_CLAMP_COLLAR == pytest.approx(c["collar_below_bar_underside_mm"], abs=0.05)
    assert C.SPINE_CLAMP_MASS_G == pytest.approx(c["mass_g"], abs=0.05)
    assert C.SPINE_AXIS_FORE_MM == pytest.approx(c["spine_axis_offset_fore_mm"], abs=0.05)
    assert C.PAWL_HOUSING_UP == pytest.approx(g["pawl_housing_up_mm"], abs=0.05)
    assert C.PAWL_HOUSING_HALF_W == pytest.approx(g["pawl_housing_half_w_mm"], abs=0.05)
    assert C.BODY_TOP_Z_IN_B25_BAND == pytest.approx(g["body_top_z_in_b25_band"], abs=0.05)
    b = C.b25_clearances(c, g)
    assert C.B25_CUT_CHANGE_MM == pytest.approx(b["run_plan_mm"]["cut_change_mm"], abs=0.05)


def test_b25_clear_of_real_clamp_and_housing(clamp):
    C, _, c, g = clamp
    b = C.b25_clearances(c, g)
    assert b["band_to_clamp_ok"] and b["band_to_clamp_x_mm"] >= 10.0
    assert b["governing_kit"] == "S"
    s = b["kits"]["S"]
    assert s["wrap_to_housing_mm"] > 0 and s["mitre_to_body_in_band_mm"] > 0 and s["mitre_to_housing_side_x_mm"] > 0
    assert b["all_ok"]


def test_spine_channel_finding(clamp):
    """BL-045 found the printed channel (40.2 x 18.3, sized for the old 30 x 3 plate) shallower than the OD 20 tube;
    BL-046 re-made it (h1_spine_channel): the tube + 6 mm rack now fit the printed channel."""
    C, _, _, g = clamp
    assert g["spine_channel_depth_y_mm"] >= 20.0 + 6.0
    assert C.spine_axis()["tube_fits_channel"] and C.spine_axis()["tube_plus_rack_fits"]


# ------------------------------------------------------------------------------------------- 3. IM / US fairleads
def test_every_imus_pin_carries_webbing():
    from huntkit.gendesign import bag_attach as BA
    assert set(BA.PIN_WRAP) == set(BA.IMUS_STATIONS)
    for s in BA.IMUS_STATIONS:
        e = BA.imus_eye_envelope(s)
        assert e["gap_under_pin_mm"] >= e["eye_thickness_design_mm"] + e["eye_margin_mm"] - 1e-9
        assert e["throat_mm"] >= e["neck_w_max_mm"] + 1.0 - 1e-9
        g = BA.eye_geom(s)
        if e["on_crown_sleeve"]:                    # the saddle root stays out of the 18 mm crown bore
            from huntkit.gendesign.frame_branch import stay_radius
            assert float(stay_radius(BA.IMUS_Z[s], BA.SCALE)) - g.embed >= BA.SLEEVE_BORE_R_REAM + 1.0 - 1e-6


def test_print_stl_all_12_pass_with_eyes():
    from huntkit.gendesign import h1_fairleads as HF
    r = HF.check_stl(PRINT / "h1_assembled.stl")
    assert r["all_pass"]
    for k, v in r.items():
        if isinstance(v, dict):
            assert v.get("eye_fits") is True, k
            assert v["gap_under_pin"] >= 5.5 - 0.3


def test_crown_bores_open_at_im_stations():
    import trimesh
    m = trimesh.load(PRINT / "h1_assembled.stl")
    for z in (190.0, 330.0, 520.0):
        s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        holes = [e for e in s.discrete if abs(abs(e.mean(0)[0]) - 115.0) < 3 and 16.5 < np.ptp(e[:, 0]) < 18.5]
        assert len(holes) == 2, z


def test_imus_strength_record():
    d = json.loads((ANALYSIS / "crown_and_fairlead_checks.json").read_text())["imus_strength"]
    for st, v in d.items():
        assert v["bl045"]["sf"] >= 1.0 and v["bl045"]["fatigue"] >= 1.0, st
        assert v["bl045"]["gap_under_pin_mm"] == pytest.approx(5.5, abs=0.01)
        assert v["bl045"]["pin"]["sf_yield"] >= 1.0


# ------------------------------------------------------------------------------------------- 4. island
def test_lower_half_has_no_island():
    from huntkit.gendesign.frame_topopt import split_mesh
    import trimesh
    m = trimesh.load(PRINT / "h1_assembled.stl")
    lo, hi = split_mesh(m, 234.0)
    assert len(lo.split(only_watertight=False)) == 1
    assert len(hi.split(only_watertight=False)) == 1
    lf = trimesh.load(PRINT / "h1_lower_flat.stl")
    uf = trimesh.load(PRINT / "h1_upper_flat.stl")
    # BL-050: the assembled frame carries the two bolt-on US2 clevises, which print on their own
    cl = sum(trimesh.load(PRINT / f"us2_clevis_{s}.stl").volume for s in ("R", "L") if (PRINT / f"us2_clevis_{s}.stl").exists())
    assert m.volume - lf.volume - uf.volume - cl == pytest.approx(0.0, abs=5.0)     # nothing dropped by the export


def test_boss_core_constant():
    from huntkit.gendesign import frame_h1 as H1
    assert 0.0 < H1.BOSS_CORE_MM <= H1.H


# ------------------------------------------------------------------------------------------- 5. stale records
def test_revc_hinge_record_rerun():
    a = json.loads((ANALYSIS / "rev_c_verification_results.json").read_text())["attachments"]
    assert a["fairlead_fea"]["hinge"]["sf"] == pytest.approx(3.73, abs=0.02)
    assert a["fairlead_fea"]["hinge"]["geometry"].startswith("BL-042")
    assert "2.97" not in (ANALYSIS / "rev_c_verification.md").read_text().split("## ")[1]


def test_no_stale_fairleads_present_label():
    assert "fairleads present 1.000" not in (ANALYSIS / "h1_buckling.md").read_text()
    src = (REPO / "huntkit" / "gendesign" / "frame_fixed.py").read_text()
    assert 'ko["fairleads present"]' not in src
