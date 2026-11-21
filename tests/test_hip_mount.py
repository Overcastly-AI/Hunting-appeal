"""BL-056: the SLM Ti hip pivot mount redrawn for the 8-insert boss (huntkit.gendesign.hip_mount)."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import hip_mount as H

RES_P = H.ANALYSIS / "hip_mount_bl056.json"


def test_voxel_solver_against_the_cantilever():
    """The part FE's voxel H8 solver against Timoshenko tip deflection and beam bending stress."""
    r = H.cantilever_check()
    assert r["ratio"] == pytest.approx(1.0, abs=0.04)
    assert r["sigma_ratio"] == pytest.approx(1.0, abs=0.04)


def test_fatigue_sf_goodman_closed_form():
    # 0 -> 100 MPa: amplitude = mean = 50; n (50/200 + 50/850) = 1
    assert H.fatigue_sf(100.0, 200.0, 850.0) == pytest.approx(1.0 / (0.25 + 50.0 / 850.0))


def test_redrawn_stl_slices():
    """The exported STL: one closed shell; base D50 x 3 with 8 x D5.5 holes on the BL-055 positions and the D10 pin
    hole; the legs and the hub unchanged above the fillets; head-to-leg >= 1 mm; driver access clear."""
    g = H.geometry_check()
    assert g["watertight"] and g["shells"] == 1
    b = g["base"]
    assert b["d_eq_mm"] == pytest.approx(50.0, abs=0.1)
    assert b["top_z_mm"] == pytest.approx(3.0, abs=0.1)
    assert b["holes"] == 9 and b["hole_d_eq_mm"][:8] == pytest.approx([H.HOLE_D] * 8, abs=0.05)   # BL-058: D5.8
    assert b["pin_hole_d_eq_mm"] == pytest.approx(10.0, abs=0.05)
    assert b["hole_pos_err_mm"] < 0.05
    assert g["legs_and_hub_kept"] and g["hub_top_z_mm"] == pytest.approx(28.1, abs=0.05)
    assert g["head_to_leg_ok"] and g["head_to_leg_mm"] >= 1.0
    assert g["driver_access_ok"]
    assert g["hole_edge_to_rim_mm"] > 2.0 and g["head_overhang_rim_mm"] < 0.0


def test_hole_positions_are_the_closeout_pattern():
    d = json.loads((H.ANALYSIS / "h1_closeout.json").read_text())
    P = np.asarray(d["hip"]["chosen"]["pattern"]["positions_xz"])
    loc = H.holes_local()
    fr = H.to_frame(np.c_[loc, np.zeros(len(loc))])
    assert np.allclose(fr[:, [0, 2]], P, atol=1e-6)
    assert np.allclose(fr[:, 1], H.FACE_Y)


def test_fits_the_frame_print():
    f = H.frame_fit()
    assert f["face_y_measured"] == pytest.approx(H.FACE_Y, abs=0.01)
    assert f["clash_mm3"] < 1.0
    for k in ("face+1", "face+6", "face+10.5"):
        assert f["pilot_slices"][k]["pilots"] == 8 and f["pilot_slices"][k]["max_offset_to_mount_hole_mm"] < 0.2
    assert all(s["shank_in_frame_mm3"] < 0.5 and s["head_in_frame_mm3"] < 0.5 and s["key_in_frame_mm3"] < 0.5
               for s in f["screws"])
    assert f["tip_to_pilot_floor_mm"] >= 0.3
    assert f["boss_contact_mm2"] >= f["base_area_mm2"] * 0.99
    assert f["pass"]


def test_strip_formula_on_slm_allowables():
    s = H.strip_check()
    # hand: C2|H_frame T 238.6 N, arm a, strip b, t 3: sigma = 6 T a / (b t^2)
    sig = 6 * 238.6 * s["arm_mm"] / (s["strip_b_mm"] * 9.0)
    assert s["rows"]["C2|H_frame"]["sigma_mpa"] == pytest.approx(sig, abs=0.2)
    assert s["min_sf_over_goal"] >= 1.0


def test_mass_against_the_booked_delta():
    m = H.mass()
    # D50 x 3 annulus less 8 holes, less the drawn D44 x 1.2 disc, less the leg volume swallowed, plus fillets
    a50 = math.pi / 4 * (50 ** 2 - 10 ** 2 - 8 * H.HOLE_D ** 2) * 3.0
    a44 = math.pi / 4 * (44 ** 2 - 10 ** 2) * 1.2
    assert m["delta_g"] == pytest.approx((a50 - a44) * 4.43e-3, abs=2.0)
    assert m["ledger_correction_g"] == pytest.approx(m["delta_g"] - m["booked_bl055_g"], abs=0.01)


@pytest.mark.skipif(not RES_P.exists(), reason="run python -m huntkit.gendesign.hip_mount first")
def test_published_record():
    r = json.loads(RES_P.read_text())
    fe = r["fe"]
    assert fe["min_sf_over_goal"] >= 1.0
    for k, row in fe["rows"].items():
        assert row["min_sf_all"] >= row["goal"], k
    hb = r["tests"]
    assert hb["HB-6"]["pass_line_n_each"] >= 513
    steps = hb["HB-6b"]["steps"]
    assert [s["step"] for s in steps] == ["carry 1 g", "walk 1.6 g", "C2 proof"]
    assert all(s["pass_if_microstrain_at_most"] > s["model_microstrain"] > 0 for s in steps)
    assert r["frame_fit"]["pass"] and r["geometry"]["head_to_leg_ok"]
