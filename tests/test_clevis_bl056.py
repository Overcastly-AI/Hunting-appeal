"""BL-056 addition 1: the US2 clevis joint at the CLEVIS-SHARE B bound (share 1.0) on the BL-056 blocks."""
import json

import numpy as np
import pytest

from huntkit.gendesign import clevis_bl056 as CB
from huntkit.gendesign import h1_bedfit as BF

RES_P = CB.ANALYSIS / "clevis_bl056.json"


def test_blocks_grow_upward_only():
    """The lower edge (the strap's r 3 lip) stays at pin - 14.5; the top moves to pin + 19; the bolts stay at +/- 7."""
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    for b in BF.block_boxes(p).values():
        assert b[4] == pytest.approx(p["z"] - 14.5) and b[5] == pytest.approx(p["z"] + 19.0)
    assert BF.JOINT.dz == 7.0 and BF.JOINT.head_recess == 4.0 and BF.JOINT.cbore_d == 9.0
    assert BF.trap_walls()["pass_2mm"]


def test_share_one_passes_every_row_live():
    """h1_bedfit.joint_check at share 1.0 on the BL-051 lane rows (the 0.86 row of BL-053) and the bag-on rows."""
    r = BF.joint_check(share=1.0)
    assert min(v["min_fatigue"] for v in r["rows"].values()) >= CB.FAT_GOAL
    assert min(v["min_sf"] for v in r["rows"].values()) >= CB.SF_GOAL
    # the b50 lane row's net section read 0.86 at +14.5 / 12 mm plug (BL-053)
    assert r["rows"]["cradle_lane_b50"]["fatigue"]["net_section_paht"] >= CB.FAT_GOAL


def test_body_plug_and_bolt_grip():
    """Nut face 1 mm inboard (plug 13 mm): the M5 x 35 still spans head face -> nut + 1 thread, tail inside the block."""
    j = BF.JOINT
    assert j.L_body == pytest.approx(13.0)
    grip = j.head_face - j.nut_face + j.washer_t + j.nut_t
    assert grip + 1.0 <= j.bolt_len <= grip + 2.0
    assert j.head_face - j.bolt_len > j.tail_x > BF.BODY_BLOCK_X0 + 2.0
    assert j.trap_x0 == pytest.approx(j.nut_face - j.washer_t - j.nut_t - 0.2)


def test_net_section_grows_with_the_block():
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    a19 = BF.net_section(p)["A"]
    old = BF.BLOCK_UP_Z
    try:
        BF.BLOCK_UP_Z = 14.5
        a145 = BF.net_section(p)["A"]
    finally:
        BF.BLOCK_UP_Z = old
    hy = p["y_floor"] - (p["yc"] + BF.BLOCK_DY_LO)
    assert a19 - a145 == pytest.approx(hy * 4.5, rel=0.03)     # the added strip is solid (traps end below it)


@pytest.mark.skipif(not RES_P.exists(), reason="run python -m huntkit.gendesign.clevis_bl056 first")
def test_published_record():
    r = json.loads(RES_P.read_text())
    assert r["share_1_pass"]
    s1 = r["joint"]["share_1"]["all_rows_min"]
    assert s1["strength"] >= 1.5 and s1["fatigue"] >= 1.15
    assert r["slices"]["pass"]
    assert all(v["fits_with_brim"] for v in r["bed"].values())
    assert r["clearance"]["pass"] and min(r["clearance"]["worst_clear_mm"].values()) >= 10.0
    assert all(v["watertight"] and v["shells"] == 1 for k, v in r["mass"].items() if isinstance(v, dict))
    assert 0.0 < r["mass"]["print_delta_g"] < 15.0
    # the US2 strap still wraps only the lower lip, unchanged (r 3)
    assert r["strap_wrap"]["worst"]["us2"]["lip_r_mm"] >= 3.0
    t = r["gauges"]["tests"]
    for k in ("CLEVIS-SHARE|us2_inboard", "CLEVIS-SHARE|us2_yz"):
        for s in t[k]["steps"]:
            assert s["pass_if_abs_microstrain_at_most"] > abs(s["microstrain"]) > 0
    assert np.allclose(t["CLEVIS-SHARE|us2_yz"]["pull_unit_vector_frame_R"], [0.0, 0.9216, -0.3881], atol=1e-3)
