"""BL-044: the hinge eye on the BL-042 hinge fairlead and the bag-side loose ends (third review Z-1 / M-3 / m-1 / m-11,
BL-043 found-not-fixed). Every test checks a number or a geometry, and each would have failed on the BL-043 tree."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import mfg_corrie_f_rev3 as M  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402
from huntkit.gendesign import bag_attach as BA  # noqa: E402

PIECE = ROOT / "designs" / "pack_5200" / "print" / "frame_h1" / "test_pieces" / "hefit_hinge_fairlead_R_frame_coords.stl"


@pytest.fixture(scope="module")
def pk():
    return M.package()


@pytest.fixture(scope="module")
def kit():
    import physical_test_kit as K
    return K.build(write=False)


@pytest.fixture(scope="module")
def stl():
    if not PIECE.exists():
        pytest.skip("HE-FIT test piece not on disk")
    import he_stl_check as C
    return C, C.load_piece(), C.check()


# ---------------------------------------------------------------- 1 HE on the envelope (Z-1)
def test_section_model_reads_the_bl042_envelope():
    E, g = BA.HINGE_EYE_ENVELOPE, P.he_geometry()
    assert g["pin_y"] == pytest.approx(E["pin_centre_from_stay_centre_mm"])       # 19.45, not stay_r + 6.5
    assert g["throat"] == E["throat_mm"] == 20.0
    assert g["gap_under_pin"] == pytest.approx(5.5)
    assert g["tip_y"] == pytest.approx(E["stay_r_mm_at_z60"] + E["cheek_tip_above_stay_surface_mm"], abs=1e-3)
    assert g["cheek_lo"] == pytest.approx(g["pin_z"] - E["cheek_half_z_mm"])
    # the BL-041 model used the legacy constants (pin 6.5 mm proud): 3.6 mm nearer the stay
    assert g["pin_y"] - (E["stay_r_mm_at_z60"] + BA.HOLE_PROUD) == pytest.approx(3.6, abs=0.01)


def test_eye_is_solved_on_the_real_folded_neck_wrap():
    g = P.he_geometry()
    # main ply over the 2-ply fold ridge: centreline radius PIN_D/2 + 2 t + t/2 (BL-041 modelled one ply: 3.25)
    assert g["r_c"] == pytest.approx(2.5 + 2 * P.HE_T + P.HE_T / 2)
    assert P.he_pin_z(P.HE_EYE) == pytest.approx(25.0, abs=0.5)
    # the BL-041 eye (17 mm, box top +14) on the real wrap sits well below the design pin: the review's Z-1 finding
    assert P.he_pin_z(17.0) < 22.0


def test_neck_wrap_fits_the_gap_with_margin():
    E = BA.HINGE_EYE_ENVELOPE
    assert 3 * P.HE_T_RANGE[1] <= E["gap_under_pin_mm"] - 0.5 + 1e-9                 # review Z-1 rule, thickest roll
    assert (E["throat_mm"] - P.HE_NECK_W - P.HE_NECK_TOL) / 2 >= 0.5 - 1e-9         # replaces neck_w == throat
    assert 3 * 2.0 > E["gap_under_pin_mm"] - 0.5                                     # BL-041's 2.0 mm bracket fails


# ---------------------------------------------------------------- 2 the STL test piece, sliced
def test_eye_sliced_into_the_hefit_test_piece(stl):
    C, mesh, r = stl
    assert r["pass"], {k: v for k, v in r.items() if k not in ("corners", "under_pin")}
    assert r["worst_loop_overlap_mm2"] == 0.0 and r["min_loop_to_material_mm"] > 0.0
    assert r["min_clear_off_corner_mm"] >= 0.5                                        # centred and off the corners
    assert r["worst_under_pin_clear_mm"] > 0.0                                        # in the fillet corners: no touch
    assert r["throat_min_mm"] == pytest.approx(20.0, abs=0.1)
    assert r["min_box_top_to_cheek_mm"] >= P.HE_CHEEK_MIN
    assert len(r["corners"]) == 18                                                    # 3 faces x 3 plies x 2 wraps
    # the checked design numbers are the print's: floor 5.5 under the pin at the throat centre
    assert r["under_pin"][f"{P.HE_T}"]["floor_depth_centre_mm"] == pytest.approx(5.5, abs=0.1)


def test_stl_check_catches_a_raised_floor(stl):
    """The detector fails a fairlead whose floor sits 2 mm nearer the pin (a body 2 mm proud): the slice check would
    have caught Z-1."""
    C, mesh, _ = stl
    m2 = mesh.copy()
    m2.apply_translation([0.0, 2.0, 0.0])
    r = C.check(m2)
    assert not r["pass"] and r["min_clear_off_corner_mm"] < 0.5


def test_bl041_box_would_clash_on_the_print(stl):
    """The BL-041 box top (+14) under a 23 mm pin (the review's real-wrap value) is 0 mm under the cheeks."""
    E = BA.HINGE_EYE_ENVELOPE
    assert 23.0 - E["cheek_half_z_mm"] - 14.0 < P.HE_CHEEK_MIN


# ---------------------------------------------------------------- 3 box, band, stand-off (m-1, B-01)
def test_hefit_band_agrees_with_the_cheek_clearance(pk, kit):
    hg = pk["ctx"].rs.geo["he"]
    lo, hi = P.he_band()
    E = BA.HINGE_EYE_ENVELOPE
    assert lo - E["cheek_half_z_mm"] - hg["box_z_above_seam"][1] == pytest.approx(P.HE_CHEEK_MIN)
    assert lo <= hg["pin_z_range"][0] and hg["pin_z_range"][1] <= hi              # solved bracket inside the band
    assert hg["cheek_clear_min"] >= P.HE_CHEEK_MIN
    he = kit["register"]["HE-FIT"]
    assert f"{lo:.0f}-{hi:.0f}" in he["pass_fail"] and "hefit_hinge_fairlead_R" in he["specimen"]
    assert f"<= {P.HE_T_RANGE[1]:.1f} mm" in he["pass_fail"]                         # the caliper gate


def test_b01_standoff_on_the_envelope():
    hs = P.F.hinge_standoff()
    E = BA.HINGE_EYE_ENVELOPE
    assert hs["hinge"]["proud_mm"] == pytest.approx(E["cheek_tip_above_stay_surface_mm"])
    assert hs["hinge"]["push_mm"] == pytest.approx(7.05, abs=0.02)
    assert hs["us2"]["proud_mm"] == pytest.approx(BA.HOLE_PROUD + BA.HOLE_D / 2 + BA.WALL_FRONT)
    g = P.he_geometry()
    assert g["faces_y"] == (BA.PANEL_OFFSET, pytest.approx(hs["hinge"]["top_mm"], abs=0.01))


# ---------------------------------------------------------------- 4 peel is real and rated (M-3)
def test_peel_is_reported_and_rated(pk, kit):
    pl = P.he_peel()
    assert 15.0 < pl["design"]["peel_deg"] < 35.0 and pl["worst"]["peel_deg"] > pl["design"]["peel_deg"]
    reg = kit["register"]
    st = reg["PT-3"]["steps"]
    assert "spacer" in st and "cheek-tip plane" in st and "1530 N" in st
    import physical_test_kit as K
    assert K.SEWF_HE_PEAK == round(1.15 * 1.6 * 1019.0 / 3.0) == 625
    sf = reg["SEW-F"]
    assert f"{K.SEWF_HE_PEAK} N" in sf["pass_fail"] and "HE" in sf["specimen"] and "box TOP row" in sf["steps"]
    row = next(r for r in pk["load_points"] if r["point"] == "hinge eye")
    assert "PEELS" in row["note"] and "capacity" in row["note"]
    st3 = {i: (c, s) for i, c, s, _ in M.THIRD_STATUS}
    assert st3["M-3"][1] == "fixed"
    h = next(h for i, c, s, h in M.THIRD_STATUS if i == "M-3")
    assert "no peel" not in h.replace("'no peel' dropped", "")


# ---------------------------------------------------------------- 5 hinge pin, viz, B-18 label (item 5, item 1, m-11)
def test_hinge_pin_two_mm_longer_in_bom_and_ledger(pk):
    hp = P.F.hinge_pin()
    assert hp["span_hinge_mm"] - hp["span_im_mm"] == pytest.approx(2.0)
    assert hp["shank_hinge_mm"] == 38.0 and hp["overall_hinge_mm"] == 52.0
    rows = {n: g for s, n, g, src in P.F.bl044_rows()}
    pin = next(g for n, g in rows.items() if n.startswith("BL-044: hinge pins"))
    assert pin == pytest.approx(2 * math.pi * 2.5 ** 2 * 2.0 * 2.81 / 1000.0, rel=0.02)
    line = next(b for b in pk["bom"] if "7075 pins" in (b.item or ""))
    assert "38 mm shank HINGE" in line.item


def test_viz_hinge_fairlead_and_eye_follow_the_envelope():
    from huntkit.viz3d import attach as A
    assert A.fairlead_geom("hinge") is BA.HINGE_GEOM and A.fairlead_geom("im3").hole_proud == BA.HOLE_PROUD
    assert A.pin_y(60.0) == pytest.approx(float(A.stay_y(60.0) + A.stay_r(60.0)) + BA.HINGE_GEOM.hole_proud)
    sec = A.he_section()
    assert sec is not None and sec["neck_w"] == P.HE_NECK_W
    # the stack round the pin passes under it inside the gap: its lowest y relative to the pin >= -(2.5 + 4.5)
    import numpy as np
    under = sec["loop"][np.abs(sec["loop"][:, 1]) < 1.0]
    assert under[:, 0].min() >= -(2.5 + sec["neck_t"]) - 1e-6


def test_step2_labels_clear_the_marks():
    import patterns_corrie_f_rev3_export as X
    rs = P.build("today")
    for pid in ("B-18", "B-22"):
        p = X.print_copy(rs.pieces[pid])
        assert sum(X.label_clash(p).values()) > 0                                       # the reviewer's overprint
        q = X.fit_label(p)
        c = X.label_clash(q)
        assert c == {"marks_mm2": 0.0, "outside_mm2": 0.0}, (pid, c)
        assert q.label_lines()[0].startswith("ID:") or q.label_lines()[-1].startswith("ID:") or \
            any(t.startswith("ID: ") for t in q.label_lines())


# ---------------------------------------------------------------- 6 K-W keepers, rifle, stale text (items 2-4)
def test_w3_has_no_bag_fixed_keeper(pk):
    rs = pk["ctx"].rs
    assert set(rs.geo["kw_z"]) == {"W1", "W2"}
    g3 = rs.pieces["B-03"]
    assert not any("K-W keeper W3" in (n.label or "") for n in g3.notches)
    assert next(w for w in rs.webbing if w["id"] == "K-W")["qty"] == 4
    k = rs.geo["kw_w3"]
    assert k["worst"]["dz_mm"] == pytest.approx(-101.6) and k["worst"]["loop_cross_load_n"] > 100.0
    rows = {n: g for s, n, g, src in P.F.bl044_rows()}
    kw = next(g for n, g in rows.items() if n.startswith("BL-044: W3 K-W"))
    assert kw == pytest.approx(-2 * 0.080 * P.F.WEB25)


def test_rt_strap_clear_of_the_rifle(pk):
    r = pk["ctx"].rs.geo["rt_rifle"]
    assert r["ok"] and r["min_flat_mm"] >= P.RT_CLEAR
    assert r["standoff_min_mm"] is not None and r["standoff_min_mm"] > r["barrel_od"]


def test_stale_hose_text_and_strip_end_marks(pk):
    co = (ROOT / "designs" / "pack_5200" / "concepts" / "corrie.py").read_text()
    assert f"z {P.HOSE_Z:.0f}" in co and "NOT at the collar seam" in co
    for f in ("designs/pack_5200/build_geometry.py", "designs/pack_5200/concepts/corrie_loadout.py"):
        assert "hose ports at the collar seam" not in (ROOT / f).read_text()
    b07 = pk["ctx"].rs.pieces["B-07"]
    assert not any("B-07s strip end" in (n.label or "") for n in b07.notches)        # no longer merged into a slit
    for side, d in pk["ctx"].rs.geo["rt_on_b07"].items():
        xs = [ln.points[0][0] for ln in b07.internal_lines if (ln.label or "").startswith("B-07s strip end")]
        assert any(abs(x - (d["x_centre"] - P.HEM_GAP / 2)) <= 0.06 for x in xs)        # x_centre is rounded to 0.1


def test_test_kit_screens_are_named_for_this_ticket():
    import physical_test_kit as K
    assert K.SHOT == "20261113_BL044kit"
    assert "BL038_<n>" not in (K.__doc__ or "")


# ---------------------------------------------------------------- 7 release status
def test_release_not_ready_until_a_fourth_review():
    open_ = M.open_findings()
    assert open_ == ["N-1"]                     # three reviews' majors fixed; BL-048: the fourth review's N-1 waits on the frame
    assert M.FOURTH_REVIEW_DONE is False and not M.ready_to_cut()


def test_ledger_books_bl044_and_h1f():
    from huntkit.mass import ledger as L
    names = [r["name"] for r in L.adopted_bag_rows("M")]
    for pre in ("BL-044: HE hinge eyes", "BL-044: hinge pins", "BL-044: W3 K-W keeper loops deleted"):
        assert any(n.startswith(pre) for n in names), pre
    he = next(g for s, n, g, src in P.F.bl044_rows() if n.startswith("BL-044: HE"))
    assert he == pytest.approx(2 * (P.HE_CUT - P.HE_CUT_BL041) / 1000.0 * P.F._rec("poly_webbing_38mm", "mass_g_m"))
    an = ROOT / "designs" / "pack_5200" / "analysis"
    assert "H1F" in (an / "weight_rollup_v2.json").read_text()                       # roll-up regenerated (BL-044 item 6)
    assert "H1F" in (an / "mass_ledger.md").read_text()


# ---------------------------------------------------------------- 8 the rev 3 render scene (item 7)
def _has_bpy():
    from huntkit.viz3d import studio
    return studio.find_bpy_python(None) is not None


@pytest.mark.skipif(not _has_bpy(), reason="needs bpy (set HUNTKIT_BPY to the Blender venv's python)")
def test_render_scene_draws_the_released_clip_hose_and_b25():
    import numpy as np
    from huntkit.viz3d import corrie_f as CF
    BC, CO, F, CS = CF._mods()
    if not (CS.run_dir("F", CF.TORSO, "_fine") / "x_packed.npy").exists():
        pytest.skip("CORRIE F fine drape missing")
    sc = CF.scene("sixday", level=1)
    r = sc.report["bl044"]
    c = P.F.make()
    rl = P.rt_layout(P._maps(c), c)
    assert r["clips"]["z_bar"] == rl["z_bar"]
    for side in ("R", "L"):
        assert abs(r["clips"][side]["buckle_z"] - (rl["z_bar"] + P.BUCKLE_ENV[1] / 2)) < 6.0   # not 150 mm under the seam
        assert abs(r["hose"][side][2] - P.HOSE_Z) < 6.0
    assert r["b25"]["sleeve_x"] == pytest.approx(45.5)
    by = {p.name: p for p in sc.parts}
    assert "imp2_port" not in by and "cf_hose_port_frames" in by
    Vh = np.asarray(by["imp2_hose@t19"].mesh.vertices)
    assert Vh[:, 2].min() < P.HOSE_Z + 20.0                                          # the hose leaves at the low port
    assert len([n for n in by if n.startswith("s15_roll_buckle_") and "__" not in n]) == 2


# ---------------------------------------------------------------- 9 BL-045 follow-ups (orchestrator, mid-ticket)
def test_ime_and_us_eyes_are_necked_for_the_imus_envelope(pk):
    rs = pk["ctx"].rs
    for pid, w in (("IME", 38.0), ("US", 25.0), ("USA", 25.0)):
        p = rs.pieces[pid]
        folds = [ln for ln in p.internal_lines if (ln.label or "").startswith("neck: fold the edge in")]
        xs = sorted(ln.points[0][0] for ln in folds)
        neck = xs[-1] - xs[0]
        for st in ("us1", "im3"):
            env = BA.imus_eye_envelope(st)
            assert neck == pytest.approx(env["neck_w_mm"]) and neck + P.HE_NECK_TOL <= env["throat_mm"] - 1.0 + 1e-9
        assert sum(1 for ln in p.internal_lines if (ln.label or "").startswith("neck tack")) == 2
    ime = next(o for o in pk["ops"] if o.operation.startswith("IME fairlead eyes"))
    assert "NECK FIRST" in ime.notes
    assert any(o.operation.startswith("US:") and "NECK FIRST" in o.notes for o in pk["ops"])


def test_us_cam_has_a_drawn_rated_anchor(pk, kit):
    rs = pk["ctx"].rs
    assert rs.pieces["USA"].quantity == 2
    row = next(r for r in pk["load_points"] if r["point"] == "US cam anchor")
    assert row["load_n"] == 720.0 and row["sf"] >= 1.5
    usa = next(o for o in pk["ops"] if o.operation.startswith("USA:"))
    assert "CAM's anchor bar" in usa.notes and "RIGHT PIN" in usa.notes
    mt1 = kit["register"]["MT-1"]
    assert "2 USA" in mt1["specimen"] and "2 of 2 USA hold 1080 N" in mt1["pass_fail"]
    names = [n for s, n, g, src in P.F.bl044_rows()]
    assert any(n.startswith("BL-044: US cam anchors USA") for n in names)


def test_b25_on_the_bl045_clamp():
    from huntkit.gendesign import crown_spine_clamp as C
    assert P.F.SPINE_CLAMP_HALF == C.SPINE_CLAMP_HALF_X and P.F.SPINE_CLAMP_COLLAR == C.SPINE_CLAMP_COLLAR
    assert P.F.PAWL_HOUSING_UP == C.PAWL_HOUSING_UP and P.F.PAWL_HOUSING_HALF_W == C.PAWL_HOUSING_HALF_W
    t = P.F.b25_topology()
    # BL-048 M-B: corrie_f's B-25 now uses the record's 1.5 mm ply (crown_spine_clamp still books 1.2): each side's run
    # is 0.3 mm shorter and its half wrap pi x 0.15 longer
    dt = P.F.B25_T - C.B25_T
    assert t["cut_mm"] - P.F.B25_CUT_BL043_MM == pytest.approx(C.B25_CUT_CHANGE_MM + 2 * (C.SPINE_CLAMP_COLLAR - 12.0)
                                                               + 2 * (math.pi / 2 - 1) * dt, abs=0.15)
    assert t["pawl_ok"] and t["band_to_clamp_ok"]
    assert t["clamp_half_x"] <= t["clamp_envelope"]["half_x_max_mm"]
    assert P.F.guy_bridle(wide=True)["length_mm"] == pytest.approx(386.5)       # the booked BL-041 part is unchanged


# ---------------------------------------------------------------- 10 IME / US eyes sliced on the print (orchestrator)
@pytest.fixture(scope="module")
def imus():
    import imus_stl_check as C
    if not (C.IM3EC.exists() and C.PRINT.exists()):
        pytest.skip("H1 print / IM3-EC test piece not on disk")
    return C, C.check()


def test_imus_eyes_sliced_on_the_print_and_the_im3ec_piece(imus):
    C, r = imus
    st = r["stations"]
    assert len(st) == 11 and "im3_R@im3ec" in st                                     # 10 stations + the IM3-EC piece
    for k, v in st.items():
        assert v["worst_under_pin_clear_mm"] > 0.0, k                                 # no touch, even in the fillet
        assert v["min_clear_off_corner_mm"] >= 0.5, k                                 # the HE rule off the corner band
        assert v["throat_clear_side_mm"] >= 0.45, k
        if k.startswith("us"):
            # BL-048 (fourth review N-1): on the CURRENT print the real bag-on strap pulls the US / USA eye straight
            # down the stay into the fairlead below; the route fails until BL-047 moves the US stations to their lanes
            assert not v["route_ok"] and not v["eye_pass"], k
        else:
            assert v["route_ok"] and v["eye_pass"], k
    assert not r["eye_pass_all"]
    # IME is the 3-ply necked eye: 0.5-1.0 mm under the pin; the 2-ply US eye has about 1 mm
    assert 0.5 <= st["im3_R@im3ec"]["min_clear_off_corner_mm"] < 1.0
    assert st["us1_L@print"]["min_clear_off_corner_mm"] > 1.0


def test_imus_pull_directions_cover_every_kit_end(imus):
    C, r = imus
    req = r["required_pulls"]
    assert min(req["im3"]) < -80.0                                                   # the sim IM3 hook hangs nearly straight down
    assert set(r["pulls"]["kit_ends"].values()) == {15, 19, 23}                      # every kit end maps to a simulated torso
    for k in ("im3_R@im3ec", "im3_L@print", "im2_R@print"):
        assert -90 in r["stations"][k]["sweep"]["clear_thetas"]
    # straight down the stay a US strap meets the fairlead below (BL-048 N-1: that IS the real bag-on path); the
    # dropped cradle line (-50.9 / -45.6) cleared
    for k in ("us1_L@print", "us1_R@print"):
        ok = r["stations"][k]["sweep"]["clear_thetas"]
        assert -60 in ok and -90 not in ok and -75 not in ok
    assert r["required_pulls"]["us1"] == [-90.0] and r["required_pulls"]["us2"] == [-90.0]


def test_usa_pin_loop_clears_the_cheeks_like_the_us_eye(imus):
    C, r = imus
    assert P.USA_PIN_LOOP == P.US_EYE - P.BOX_TIP_GAP - 25.0 == 23.0
    assert P.USA_CUT == 2 * P.USA_PIN_FOLD + 2 * P.IMC_FOLD == 202.0
    rs = P.build("today")
    usa = rs.pieces["USA"]
    assert usa.bounds(cut=False)[3] == pytest.approx(P.USA_CUT)
    st = r["stations"]
    for side_us, side_usa in (("us1_L@print", "us1_R@print"), ("us2_L@print", "us2_R@print")):
        assert st[side_usa]["sweep"]["clear_thetas"] == st[side_us]["sweep"]["clear_thetas"]
    # the IMC's 18 mm loop would put the box 8.9 mm from the pin: inside the cheeks' reach at the cradle pull
    spec = dict(C.eye_spec("us1", "R"), leg=P.IMC_LOOP)
    assert C.box_distance(spec, P.HE_T_RANGE[1]) < 10.0 < C.box_distance(C.eye_spec("us1", "R"), P.HE_T_RANGE[1])
