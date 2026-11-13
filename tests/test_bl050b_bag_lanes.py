"""BL-050 Part B: the bag on the US lanes (channel ends, US2 cut, bag-off cradle on the lane span, clevis heads, the
test kit's US piece and the two frame bolt sets). Results come from designs/pack_5200/analysis/us_route.json (the
taut-strap model on the rev 3 fine meat drapes against the sliced print) and the pattern / mfg / kit code."""
import csv
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

import corrie_f as F  # noqa: E402
import us_route as U  # noqa: E402

REC = json.loads(U.OUT_JSON.read_text())
PUB = json.loads(F.H1_PUBLISHED.read_text())["published"]


# ------------------------------------------------------------------------------------------------ 1. channels
def test_channel_ends_are_the_published_lane_x():
    uc = F.us_channels()
    assert uc["end_x_mm"] == {"us1": PUB["CHANNEL_ENTRY_X"]["us1"], "us2": PUB["CHANNEL_ENTRY_X"]["us2"]}
    assert uc["end_x_mm"] == {"us1": PUB["US1_X"], "us2": PUB["US2_X"]}
    assert uc["length_mm"] == {"us1": 2 * PUB["US1_X"], "us2": 2 * PUB["US2_X"]}
    assert uc["on_f02"] == {"us1": True, "us2": False}                 # US2 runs past F-02 (190 mm) onto B-05
    # mass = both drafted pieces (floor fabric record x cut area)
    assert uc["mass_g"] == pytest.approx(sum(F.BC.piece_mass_g(p) for p in uc["pieces"].values()))


@pytest.fixture(scope="module")
def rsP():
    import patterns_corrie_f_rev3 as P
    return P.build("today")


def test_b16b_tails_drawn_on_b05_inside_the_side_seam(rsP):
    b05 = rsP.pieces["B-05"]
    tails = [ln for ln in b05.internal_lines if (ln.label or "").startswith("B-16b US2 channel tail edge")]
    ends = [ln for ln in b05.internal_lines if (ln.label or "").startswith("B-16b US2 channel end")]
    assert len(tails) == 4 and len(ends) == 2
    x0, y0, x1, y1 = b05.bounds(cut=False)
    xm = 0.5 * (x0 + x1)
    assert sorted(round(abs(ln.points[0][0] - xm), 1) for ln in ends) == [PUB["US2_X"]] * 2
    yc = F.us_channels()["stations_mm"][1]
    for ln in tails:                               # the tails run from F-02's side edge to the lane x, at the station
        xs = sorted(abs(x - xm) for x, _ in ln.points)
        assert xs[0] == pytest.approx(F.F02_WH[0] / 2) and xs[1] == pytest.approx(PUB["US2_X"])
        assert abs(ln.points[0][1] - yc) == pytest.approx(F.us_channels()["width_mm"] / 2)
    g = rsP.geo["us_chan_on_b05"]
    assert g["side_seam_clear_mm"] >= F.US_SIDE_SEAM_MIN
    assert g["side_seam_clear_mm"] == pytest.approx((x1 - x0) / 2 - PUB["US2_X"], abs=0.1)


def test_us_and_us2_webbing_cut_apart(rsP):
    web = {w["id"]: w for w in rsP.webbing}
    assert web["US"]["length_mm"] == F.US_CUT_MM["us1"] and web["US"]["qty"] == 1
    assert web["US2"]["length_mm"] == F.US_CUT_MM["us2"] and web["US2"]["qty"] == 1
    for pid in ("US", "US2"):                       # same eye, neck and box on both
        labs = [ln.label for ln in rsP.pieces[pid].internal_lines]
        assert any("sewn eye" in (lb or "") for lb in labs) and any("neck" in (lb or "") for lb in labs)


# ------------------------------------------------------------------------------------------------ 2. strap path
def test_pattern_on_the_print_clears_10mm_every_drape_and_side():
    now = REC["layouts"]["now"]
    assert now["layout"]["entry"] == F.us_channels()["end_x_mm"]
    assert now["pass"] and len(now["rows"]) == 12
    assert {(r["torso"], r["side"], r["strap"]) for r in now["rows"]} == \
        {(t, s, n) for t in U.TORSOS for s in "RL" for n in ("us1", "us2")}
    assert all(r["min_clear_mm"] >= U.CLEAR_REQ for r in now["rows"])
    assert REC["recommended"] == "now" and REC["station_move"]["pass"]
    # the BL-048 drawing (ends +/-95) on the same print does not clear: the evidence for the move
    assert not REC["layouts"]["old_channel"]["pass"]
    assert min(REC["layouts"]["old_channel"]["worst_clear_mm"].values()) < U.CLEAR_REQ


def test_us2_cut_covers_the_bag_on_path_with_a_grip():
    sl = REC["strap_lengths"]
    assert sl["cut_mm"] == F.US_CUT_MM
    now = sl["layouts"]["now"]
    for n in ("us1", "us2"):
        assert now[n]["short_by_mm"] == 0.0
        assert now[n]["grip_left_mm"] >= F.TAIL_GRIP_MM - 1e-6
        assert F.US_CUT_MM[n] >= now[n]["cut_needed_mm"]
    assert F.US_CUT_MM["us2"] == now["us2"]["cut_needed_mm"]        # set to the 5 mm-rounded need (BL-048: about 925)
    assert sl["now_ok"]


def test_us2_cut_delta_is_booked():
    rows = F.bl050_rows()
    assert len(rows) == 1
    s_, n, g, src = rows[0]
    assert s_ == "straps_meat" and n.startswith("BL-050 B: US2 under-strap cut")
    assert g == pytest.approx((F.US_CUT_MM["us1"] + F.US_CUT_MM["us2"] - 1100.0) / 1000.0 * F.WEB25)
    names = [r["name"] for r in F.parts()]
    assert any(x.startswith("BL-050 B: US2 under-strap cut") for x in names)


# ------------------------------------------------------------------------------------------------ 3. cradle
def test_cradle_on_the_lane_span_is_the_meat_haul_formula():
    from huntkit.gendesign import meat_haul as M
    cs = REC["cradle_span"]
    assert cs["half_span_mm"] == {"us1": PUB["US1_X"], "us2": PUB["US2_X"]}
    assert cs["belly_mm"] == M.BELLY_MM
    for mode in ("bag_off", "float", "bag_on"):
        for n in ("us1", "us2"):
            r = cs["modes"][mode][n]
            th = math.atan2(M.BELLY_MM, cs["half_span_mm"][n])
            assert r["theta_deg"] == pytest.approx(math.degrees(th), abs=0.05)
            assert r["tension_n"] == pytest.approx(r["vertical_n"] / (2 * math.sin(th)), abs=0.1)
    # US1 on the narrow span: steeper legs, less tension; US2 on the wide span: more
    bo = cs["modes"]["bag_off"]
    assert bo["us1"]["tension_n"] < bo["us1"]["tension_meat_haul_n"]
    assert bo["us2"]["tension_n"] > bo["us2"]["tension_meat_haul_n"]


def test_cradle_at_the_float_limit_inside_the_frame_lug_check():
    from huntkit.gendesign import h1_lanes as LN
    cs = REC["cradle_span"]
    assert cs["lug_check_n"] == LN.US_CRADLE_N
    worst = max(v["tension_n"] for v in cs["at_float_limit"].values())
    assert cs["lug_check_covers"] and worst <= LN.US_CRADLE_N
    # but the belly governs it: a 50 mm belly puts US2 over the 720 N the lug was checked at (ASSUMPTION CRADLE-SPAN)
    assert cs["sensitivity"]["belly_50"]["us2"] > LN.US_CRADLE_N
    assert cs["sensitivity"]["belly_90"]["us2"] < cs["sensitivity"]["belly_70"]["us2"]
    # the cam at the heavy-meat float case still above 1 (cam_25mm_al 1100 N, unproven: MT-3)
    assert min(v["cam_sf"] for v in cs["float_heavy"].values()) > 1.0


# ------------------------------------------------------------------------------------------------ 4. clevis heads
def test_clevis_heads_checked_on_every_drape_and_found_touching():
    from huntkit.gendesign import h1_bedfit as BF
    h = REC["clevis_heads"]
    j = BF.JOINT
    assert h["head_x_mm"] == [round(j.head_face + j.washer_t, 1), round(j.head_face + j.washer_t + j.head_h, 1)]
    assert h["head_x_mm"][1] < h["pack_half_width_mm"]
    assert {(r["torso"], r["case"], r["side"]) for r in h["rows"]} == \
        {(t, c, s) for t in U.TORSOS for c in ("fill", "meat") for s in "RL"}
    # HONEST RESULT: the free drapes reach the heads (HEAD-PROUD not supported by the model): FIT-US gates it
    assert h["cloth_min_mm"] <= 0.0
    assert h["strap_min_mm"] > 0.0                 # the US2 strap itself passes clear of them


# ------------------------------------------------------------------------------------------------ 5. kit, BOM
def test_kit_points_at_the_frame_test_piece_and_clevis():
    import physical_test_kit as K
    assert (ROOT / K.US_PIECE_PATH).exists() and (ROOT / K.US_CLEVIS_PATH).exists()
    reg = {r["id"]: r for r in csv.DictReader(open(K.REGISTER, encoding="utf-8"))}
    st = reg["HE-FIT"]["steps"]
    assert K.US_PIECE_PATH in st and K.US_CLEVIS_PATH in st and "test_kit/print" not in st
    assert "FAILS by design" not in st
    assert "M5 x 40" in st and "10 mm OD DIN 433" in st
    assert not (ROOT / "outputs" / "release" / "test_kit" / "print").exists()
    readme = (ROOT / "outputs" / "release" / "test_kit" / "README.md").read_text()
    assert K.US_PIECE_PATH in readme and K.US_CLEVIS_PATH in readme


def test_clevis_share_and_fit_us_in_the_kit():
    import physical_test_kit as K
    from huntkit.gendesign import h1_lanes as LN
    reg = {r["id"]: r for r in csv.DictReader(open(K.REGISTER, encoding="utf-8"))}
    cs = reg["CLEVIS-SHARE"]
    assert cs["status"] == "ACTIVE" and K.TEST_RELEASE["CLEVIS-SHARE"] == "R1"
    assert f"{LN.US_CRADLE_N:.0f} N" in cs["title"] and "1e5 cycles at 480 N" in cs["title"]
    assert round(LN.US_CRADLE_N * K.FAT_G / 2.4) == 480
    assert "no joint opening" in cs["pass_fail"] and "lever rig" in cs["steps"]
    assert K.group_of("CLEVIS-SHARE") == "G4"                      # the CA-1 lever rig session
    fu = reg["FIT-US"]
    assert fu["status"] == "ACTIVE" and K.group_of("FIT-US") == "G6"
    assert "bolt heads" in fu["title"] and "colour" in fu["steps"]
    res = list(csv.DictReader(open(ROOT / "outputs" / "release" / "test_kit" / "results_template.csv", encoding="utf-8")))
    ids = {r["test_id"] for r in res}
    assert {"CLEVIS-SHARE", "FIT-US"} <= ids
    assert any("HEAD-PROUD" in r["settles"] for r in res if r["test_id"] == "FIT-US")
    assert any("CLEVIS-SHARE" in r["settles"] for r in res if r["test_id"] == "CLEVIS-SHARE")


def test_two_frame_bolt_sets_on_distinct_lines():
    import mfg_corrie_f_rev3 as M
    import physical_test_kit as K
    from huntkit.gendesign import frame_h1 as FH
    from huntkit.gendesign import h1_bedfit as BF
    assert FH.JOINT.bolt_len == 45.0 and FH.JOINT.washer_od == 12.0
    assert BF.JOINT.bolt_len == 40.0 and BF.JOINT.washer_od == 10.0
    lines = {k: (item, q) for k, item, rec, q, unit, kit, frame in M.frame_bolt_lines()}
    assert "M5 x 45" in lines["z234_bolt"][0] and "M5 x 40" in lines["clevis_bolt"][0]
    assert "12 mm OD" in lines["z234_washer"][0] and "10 mm OD" in lines["clevis_washer"][0]
    assert lines["clevis_bolt"][1] == 4 and lines["clevis_washer"][1] == 8 and lines["z234_washer"][1] == 8
    bom = (ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "manufacturing" / "bom.csv").read_text()
    assert "US2 CLEVIS (BL-050): Ti gr5 low-head socket cap screw M5 x 40" in bom
    assert "z 234 JOINT: Ti gr5 low-head socket cap screw M5 x 45" in bom
    sh = [x["item"] for x in K.shopping({})]
    assert any(i.startswith("US2 CLEVIS ONLY: Ti gr5") and "M5 x 40" in i for i in sh)
    assert any(i.startswith("US2 CLEVIS ONLY: M5 washer 10 mm") for i in sh)
    assert any(i.startswith("z 234 JOINT ONLY: Ti gr5") and "M5 x 45" in i for i in sh)
    assert any(i.startswith("z 234 JOINT ONLY: M5 washer 12 mm") for i in sh)


def test_channel_ops_two_stage_and_sealed():
    import mfg_corrie_f_rev3 as M
    ops = (ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "manufacturing" / "op_sequence.md").read_text()
    assert "US floor channels B-16 (US1) and B-16b (US2) on F-02" in ops
    assert "ON F-02 ONLY" in ops and "urethane seam sealer" in ops
    assert "seam_sealer_pu" in M.PRICE_ASSUMED and "seam_sealer_pu" in M.SHOP_UNIT


# ------------------------------------------------------------------------------------------------ 6. STL checks
def test_eyes_on_the_print_with_the_real_us_pulls():
    d = json.loads((HERE / "analysis" / "imus_stl_check.json").read_text())
    assert d["eye_pass_all"]
    he = json.loads((HERE / "analysis" / "he_stl_check.json").read_text())
    assert he["pass"] and he["worst_under_pin_clear_mm"] >= he["req"]["under_pin_clear_mm"]


def test_stale_086_record_superseded():
    md = (HERE / "analysis" / "corrie_f_body.md").read_text()
    i = md.index("inboard-up direction BL-047 found fatigue 0.86")
    assert "SUPERSEDED" in md[i - 400:i + 600]


def test_bag_on_legs_stand_near_vertical_so_the_used_tension_is_conservative():
    b = REC["cradle_span"]["bag_on_path"]
    for n in ("us1", "us2"):
        assert b[n]["leg_deg_min"] > 75.0                     # straight down B-01 from the pin to the floor corner
        assert b[n]["tension_n"] == pytest.approx(b[n]["vertical_n"] / (2 * math.sin(math.radians(b[n]["leg_deg_min"]))),
                                                  abs=0.2)
        assert b[n]["tension_used_n"] >= b[n]["tension_n"]    # us_route / the lug check use meat_haul's larger value
