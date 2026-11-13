"""BL-048 N-1: the under-straps' real path (designs/pack_5200/us_route.py, analysis/us_route.json)."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import us_route as U  # noqa: E402

REC = json.loads(U.OUT_JSON.read_text())


def test_tension_is_the_bag_on_meat_case():
    t = U.tensions()
    assert t["us1"] == pytest.approx(444.4, abs=0.5) and t["us2"] == pytest.approx(296.3, abs=0.5)
    assert REC["tension_n"] == t


def test_he_shapes_sit_on_the_hinge_pin_and_b01():
    he = U.he_shapes()
    assert he["box_z"] == [39.0, 46.0]                       # box 4..11 above the floor seam at z 35
    eye, hx = he["eye_legs"]
    assert hx == pytest.approx((U._P().HE_NECK_W + U._P().HE_NECK_TOL) / 2)   # the widest neck (18.6, HE-NECK-GAUGE)
    lo_y, lo_z, hi_y, hi_z = eye.bounds
    assert lo_z <= 46.0 < 60.0 < hi_z                        # legs from the box top up round the pin


def test_no_bag_side_guide_can_clear():
    from huntkit.gendesign import bag_attach as BA
    g = U.guide_feasibility()
    assert not g["any_ok"]
    rows = {(r["strap"], r["clear_mm"]): r for r in g["rows"]}
    # US1 on the stay: no height at all to move the strap sideways under the BL-049 hinge (cheek top z 87 above the US1
    # cheek bottom z 86); BL-048 had 7 mm under the BL-042 hinge (top z 69), already an 80 deg in-plane turn
    st = U.stations()
    assert rows[("us1", 10.0)]["height_available_mm"] == pytest.approx(
        st["us1"]["z"] - st["us1"]["geom"].half_z - (st["hinge"]["z"] + BA.HINGE_GEOM.z_top) - 10.0)
    assert rows[("us1", 10.0)]["in_plane_turn_deg"] > 75.0
    assert rows[("us1", 0.0)]["in_plane_turn_deg"] > 60.0
    assert rows[("us2", 10.0)]["in_plane_turn_deg"] > 60.0 and not rows[("us2", 10.0)]["fold_fits"]
    # the US eye + box alone, hanging straight down, reach below the hinge cheeks' top edge
    assert g["us1_box_bottom_z_straight_down"] < g["hinge_cheek_top_z"]


def test_lane_offset_is_cheek_plus_clearance_plus_half_strap():
    from huntkit.gendesign import bag_attach as BA
    assert U.lane_offset() == pytest.approx(10 + BA.HINGE_GEOM.cheek + 10 + 12.5)     # BL-049 hinge cheek 10 (was 8)


def test_print_lanes_need_the_channel_moved():
    """BL-049: the print has the US stations on their lanes. With the bag's B-16 channel ends at the BL-048 drawing
    (x +/-95, 'old_channel') the straps still pass too close; with the channel ends at the lane x ('print_lanes', and
    since BL-050 B 'now' = the pattern as drawn) every drape clears by >= 10 mm."""
    from huntkit.gendesign import h1_lanes as LN
    now, old, pl = REC["layouts"]["now"], REC["layouts"]["old_channel"], REC["layouts"]["print_lanes"]
    assert now["layout"]["us1"] == pl["layout"]["us1"] == old["layout"]["us1"] == LN.US1_X
    assert pl["layout"]["us2"] == LN.US2_X
    assert not old["pass"] and pl["pass"] and now["pass"]
    assert old["layout"]["entry"] == {"us1": U.CHANNEL_X, "us2": U.CHANNEL_X}
    assert now["layout"]["entry"] == U._F().us_channels()["end_x_mm"]          # the pattern's channel ends
    for L in (pl, now):
        assert all(r["min_clear_mm"] >= U.CLEAR_REQ for r in L["rows"])
        assert {(r["torso"], r["side"]) for r in L["rows"]} == {(t, s) for t in U.TORSOS for s in "RL"}
        assert all(r["clear_mm"]["hinge"] >= U.CLEAR_REQ for r in L["rows"])     # nothing rides over the hinge


def test_us_route_line_is_inside_the_bag():
    """The dropped cradle line vs the real strap: at z 60 the real US1 strap is at the frame face (y < 20); the
    US-ROUTE line would be > 40 mm into the bag."""
    import imus_stl_check as I
    th = math.radians(I.us_cradle_theta("us1"))
    p = REC["stations"]["us1"]
    y60 = p["y_pin"] + (60.0 - p["z"]) / math.tan(th)
    assert y60 > 40.0
    for r in REC["layouts"]["now"]["rows"]:
        if r["strap"] == "us1":
            assert r["trace"]["z60"][1] < 20.0


def test_recommended_lanes_clear_by_10mm_at_every_drape():
    rec = REC["layouts"][REC["recommended"]]
    assert rec["pass"]
    assert min(rec["worst_clear_mm"].values()) >= U.CLEAR_REQ
    assert len(rec["rows"]) == 12
    sm = REC["station_move"]
    assert sm["us1"]["side"] == "inboard" and sm["us2"]["side"] == "outboard"
    assert sm["us1"]["offset_from_stay_mm"] >= U.lane_offset() and sm["us2"]["offset_from_stay_mm"] >= U.lane_offset()
    # the bare lanes with the old channel ends do not clear: the channel ends have to move with the stations
    assert not REC["layouts"]["lanes_old_channel"]["pass"]


def test_us_test_piece_is_cut_and_closed():
    tp = REC["test_piece"]
    assert tp["watertight"] and tp["shells"] == 1
    assert tp["z"] == [40.0, 160.0] and tp["fairleads"] == ["hinge", "us1", "us2"]
    assert (ROOT / tp["file"]).exists()


def test_corner_keepers_rated():
    ck = REC["corner_keepers"]
    for n in ("us1", "us2"):
        assert ck[n]["sf"] > 2.0 and ck[n]["keeper_load_n"] > 0
