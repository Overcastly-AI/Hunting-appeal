"""BL-043: regression tests for the design-reviewer THIRD review of the CORRIE F rev 3 release
(designs/pack_5200/analysis/review_20261113_rev3_third.md), bag side (the hinge eye waits for BL-042 / BL-044).

Every fix is checked against the real geometry at EVERY crown kit and torso end (W3 rides on the crown bar, which moves
25.4 mm per inch), not at 19 in / kit M only. Each test checks numbers or geometry, and the ones marked 'would have
caught' fail on the BL-041 layout."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
sys.path.insert(0, str(ROOT))

import corrie_f as F  # noqa: E402
import mfg_corrie_f_rev3 as M  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402


@pytest.fixture(scope="module")
def pk():
    return M.package()


@pytest.fixture(scope="module")
def kit():
    import physical_test_kit as K
    return K.build(write=False)


@pytest.fixture(scope="module")
def maps():
    return P._maps(F.make())


def _op(pk, word):
    return next(o for o in pk["ops"] if word in o.operation)


# ---------------------------------------------------------------- M-1 W3 at every kit and torso end
def test_w3_sweep_has_six_corners_from_the_crown_settings():
    sw = P.w3_sweep()
    assert set(sw["corners"]) == {"S 15 in", "S 18 in", "M 17.5 in", "M 20.5 in", "L 20 in", "L 23 in"}
    cs = {round(q["torso_in"], 1): q["crown_top_z"] for q in P.BC.GEOM["frame"]["crown_settings"]}
    for name, z in sw["corners"].items():
        assert z == pytest.approx(cs[float(name.split()[1])])
    assert sw["z_min"] == pytest.approx(601.0) and sw["z_max"] == pytest.approx(804.2)
    # level wrap: kw_heights puts W3 at the crown-bar height on both sides (both anchors on the bar)
    kw = P.kw_heights(F.make())["W3"]
    assert kw["R"] == kw["L"] == pytest.approx(cs[19.0])


def test_w3_never_bears_on_a_hard_part_at_any_setting(pk, maps):
    """All six corners (and every 0.5 in setting between): W3's band is >= RT_CLEAR from the buckle body and the hose
    slot. Soft things (strap, tab, cord, muzzle tabs) may lie under W3 (DECISION W3-OVER)."""
    rs = pk["ctx"].rs
    rc = rs.geo["rt_clear"]
    corners = rc["w3_corners"]
    assert len(corners) == 6 and all(v["ok"] for v in corners.values()), corners
    assert rc["w3_hard_min"] >= P.RT_CLEAR - 1e-6
    assert corners["S 15 in"]["hard_gaps"]["buckle envelope"] == pytest.approx(P.RT_CLEAR, abs=0.2)  # governing
    assert not corners["L 23 in"]["on_gusset"]                       # above the collar seam: on the collar / roll
    sig = maps["sig"]
    rl = rs.geo["rt_layout"]
    env_top = rl["y_bar"] + P.BUCKLE_ENV[1]
    slot_top = sig(P.HOSE_Z) + P.HOSE_SLOT[1] / 2
    for k, d in P.w3_sweep()["kits"].items():
        for t, z in d.items():
            lo = sig(z) - P.STRAP_W / 2
            assert lo - env_top >= P.RT_CLEAR - 1e-6, (k, t)
            assert lo - slot_top >= P.RT_CLEAR - 1e-6, (k, t)
    soft = {"strap corridor", "RTM tab", "B-26 cord (R)", "muzzle keeper cord"}
    for v in corners.values():
        assert all(o in soft or o.startswith("muzzle tab") for o in v["lies_over"]), v


def test_bl041_layout_fails_the_corner_check(pk, maps):
    """Would have caught M-1: the BL-041 buckle (bar 10 mm over the B-26 cord, z 611.5) under W3 at kit S 15 in."""
    rs = pk["ctx"].rs
    G = rs.pieces["B-03"]
    rl = dict(rs.geo["rt_layout"])
    rl["y_bar"] = maps["sig"](611.5)
    path = {"buckle envelope": (rl["x"] - 17.5, rl["y_bar"], rl["x"] + 17.5, rl["y_bar"] + 35.0)}
    c = P.w3_corners(G, rl, path, {}, maps)
    assert not c["S 15 in"]["ok"] and c["S 15 in"]["hard_gaps"]["buckle envelope"] < P.RT_CLEAR


def test_w3g_deleted_and_w3_is_the_outer_layer(pk):
    rs = pk["ctx"].rs
    assert "W3G" not in rs.pieces and not any(w["id"] == "W3G" for w in rs.webbing)
    assert not any("W3G" in (ln.label or "") for ln in rs.pieces["B-03"].internal_lines)
    assert not hasattr(P, "W3G_CUT")
    with F.revision(3):
        names = [r["name"] for r in F.parts("M", "D2")]
    assert not any("W3G" in n and n.startswith("BL-041") for n in names)
    fit = _op(pk, "Fit the hardware").notes
    assert "W3-OVER" in fit and "slacken W3" in fit and "UNDER the W3G" not in fit
    assert "W3G GUIDE" not in _op(pk, "RTM roll-clip buckle tabs").notes
    # no unrated tack on W3's path any more: the only 304 tacks in the gusset ops are none
    assert not any("W3G" in r["part"] for r in pk["load_points"])


def test_roll_model_json_matches_the_pattern_and_shows_w3_on_the_roll(maps):
    """M-2: the roll-clip JSON was solved with THIS tab (no drift); M-1: it shows W3 on the roll at kit M / L part
    loads, the reason no guide on the gusset can keep the roll free (DECISION W3-OVER)."""
    d = json.loads(P.ROLL_CLIPS_JSON.read_text())
    rl = P.rt_layout(maps, F.make())
    assert d["tab"]["z_bar"] == pytest.approx(rl["z_bar"], abs=0.05)
    assert d["tab"]["tab_frac"] == pytest.approx(rl["tab_frac"], abs=1e-3)
    assert "roll end" in d["tab"]["origin"]
    wr = d["w3_roll"]
    assert set(wr) == set(P.w3_sweep()["corners"])
    assert wr["M 20.5 in"]["day"] == "on the roll" and wr["L 20 in"]["sixday"] == "on the roll"
    assert all(v["full"] == "below the roll" for v in wr.values())
    for st, r in d["states"].items():
        assert r["bend_deg"] == pytest.approx(75.0)            # the bend cap: moving the tab leaves the cloth unchanged
        for side in ("R", "L"):
            assert r["roll_clip_mm"][side] > r["bl031_roll_clip_mm"][side]       # lower tab, longer strap
            on = r["standoff"][side]["bears_on_cloth_z"]
            assert on is not None and on[1] < rl["z_bar"] + P.BUCKLE_ENV[1] + 50.0


# ---------------------------------------------------------------- M-2 strap origin at the roll end, RT cut re-derived
def test_rt_origin_at_the_roll_end_and_clear_of_the_fold(pk):
    rs = pk["ctx"].rs
    o = rs.geo["rt_origin"]
    assert o["front_layer_mm"] == pytest.approx(0.5 * o["hem_mm"], abs=0.1)
    assert o["bl041_tuck_each_mm"] > 50.0                            # BL-041's origin needed a gusset tuck: fall back
    rt = rs.geo["rt_on_b07"]
    b07 = rs.pieces["B-07"]
    for side, d in rt.items():
        assert d["x1"] - d["x0"] == pytest.approx(P.RT_SEWN)
        assert d["box_to_gap_mm"] >= 5.0                             # box on the strip, clear of the 40 mm fold gap
        # BL-044: the strip ends are exact placement lines (the L one had merged into a hem-ring slit 2.7 mm away)
        ends = [ln.points[0][0] for ln in b07.internal_lines if (ln.label or "").startswith("B-07s strip end")]
        assert any(abs(e - (d["x_centre"] - P.HEM_GAP / 2)) <= 0.06 for e in ends)
        assert any(abs(e - (d["x_centre"] + P.HEM_GAP / 2)) <= 0.06 for e in ends)
    # roll ends 180 deg apart on the hem ring (equal flat layers)
    assert abs(rt["L"]["x_centre"] - rt["R"]["x_centre"]) == pytest.approx(0.5 * o["hem_mm"], abs=1.0)


def test_rt_cut_comes_from_the_rerun_roll_model(pk):
    import strap_tails as ST
    d = json.loads(P.ROLL_CLIPS_JSON.read_text())
    mx = max(v for s in d["states"].values() for v in s["roll_clip_mm"].values())
    r = ST.roll_row()
    assert r["paths_mm"]["max"] == pytest.approx(mx)
    assert r["after"]["cut_mm"] == 5 * math.floor((ST.ROLL_END_MM + mx + F.TAIL_GRIP_MM) / 5 + 1e-9)
    assert r["after"]["cut_mm"] > 510.0                              # BL-041's "510 unchanged" did not hold
    rt = next(w for w in pk["ctx"].rs.webbing if w["id"] == "RT")
    assert rt["length_mm"] == pytest.approx(r["after"]["cut_mm"])


def test_roll_clip_function_reproduces_bl031_paths():
    """The refactored cloth_pass.roll_clip_path (default tab) gives BL-031's numbers on the cached solve."""
    from huntkit.viz3d import cloth_pass as CP
    from huntkit.viz3d import corrie_f as V
    p = CP.ClothParams(level=2, clip_below_seam=V.CLIP_BELOW_SEAM_MM)
    try:
        r = CP.prepare("day", p, V.SHELL, V.TORSO)
    except Exception as e:                                           # noqa: BLE001
        pytest.skip(f"cloth-pass seed not available: {e}")
    out = Path(r["job"]["out"])
    if not out.exists():
        pytest.skip("cloth-pass solve not cached (outputs/ is not tracked)")
    d = json.loads(P.ROLL_CLIPS_JSON.read_text())["states"]["day"]["bl031_roll_clip_mm"]
    res = CP.run("day", p, V.SHELL, V.TORSO)
    sk, meta = V.d2_recut(res["skin"]), res["meta"]
    q = CP.ClothParams(**meta["params"])
    _, _, C, fr = CP.roll_mesh(meta["lip"], meta["collar_in_roll_mm"], q)
    S = CP.Surf(sk["X"], sk["tris"])
    for sx, side in ((1, "R"), (-1, "L")):
        assert CP.roll_clip_path(S, sk, C, fr, sx, meta["z_clip"])["length_mm"] == pytest.approx(d[side], abs=0.2)
    assert d["R"] == pytest.approx(165.5, abs=0.2) and d["L"] == pytest.approx(161.3, abs=0.2)   # BL-031 file


# ---------------------------------------------------------------- m-9 hose slot below W3; clip path clearances
def test_hose_slot_below_w3_and_clip_path_clear(pk, maps):
    rs = pk["ctx"].rs
    rc = rs.geo["rt_clear"]
    assert rc["min_gap"] >= P.RT_CLEAR - 1e-6, rc["min_pair"]
    assert set(rc["accepted"]) == {"strap corridor | B-26 cord (R)"}
    assert rc["gaps"]["buckle envelope | B-26 cord (R)"] >= P.RT_CLEAR
    assert P.HOSE_Z + P.HOSE_SLOT[1] / 2 <= P.w3_sweep()["z_min"] - P.STRAP_W / 2 - P.RT_CLEAR + 1e-9
    G = rs.pieces["B-03"]
    slot = next(ln for ln in G.internal_lines if (ln.label or "").startswith("IMP-2 hose port slot"))
    ys = [q[1] for q in slot.points]
    assert max(ys) == pytest.approx(maps["sig"](P.HOSE_Z) + P.HOSE_SLOT[1] / 2)
    assert pk["geo"]["hose_z"] == P.HOSE_Z
    assert "HOSE-LOW" in _op(pk, "hose ports").notes
    # the aft muzzle tab keeps the FP-CLEAR presser-foot rule (9 mm) to the aft seam line
    gf, ga = maps["gy_frame"], maps["gy_aft"]
    mk = rs.geo["rt_layout"]["mk_dx"]
    assert ga(P.B11_MUZ_Z) - gf(P.B11_MUZ_Z) - (mk[1] + P.B11_W / 2) >= 9.0


# ---------------------------------------------------------------- M-4 B-25 topology
def test_b25_topology_turn_fits_and_clears_at_every_kit(pk):
    tp = F.b25_topology()
    assert tp["turn_inside_band"] and tp["band_to_clamp_ok"]
    assert tp["mitre"]["x"] == tp["band_x"] and tp["band_to_clamp_x_mm"] >= F.MIN_CLEAR_MM
    assert tp["run_s"][0] >= F.BAR_OD / 2 + F.SPINE_CLAMP_COLLAR          # under the clamp collar
    for k, v in tp["kits"].items():
        assert v["clear_mm"] >= 10.0, k                                     # spine wrap vs pawl housing
        assert v["mitre_to_upper_bar_mm"] >= 5.0, k
        assert v["mitre_to_housing_x_mm"] >= 5.0, k
    assert tp["governing_kit"] == "S"                                        # shortest spine above the pawl
    # the BL-041 un-necked 38 mm wrap would hit the housing at kit S 15 in: would have caught the M-4 spine check
    assert tp["kits"]["S"]["housing_top_s_mm"] - (tp["run_s"][0] + tp["width_mm"]) < 1.0
    rs = pk["ctx"].rs
    q = rs.pieces["B-25"]
    assert q.bounds(cut=False)[3] == pytest.approx(tp["cut_mm"])
    mit = [ln for ln in q.internal_lines if (ln.label or "").startswith("MITRE")]
    assert len(mit) == 2
    for ln in mit:                                                          # 45 deg across the full 38 mm
        (x0, y0), (x1, y1) = ln.points
        assert abs(x1 - x0) == pytest.approx(38.0) and abs(y1 - y0) == pytest.approx(38.0)
    assert any((ln.label or "").startswith("NECK") for ln in q.internal_lines)
    assert "B25-BOX" in q.labels["note"] and "exception" in q.labels["note"]           # m-6
    assert "GATE B25-FIT" in _op(pk, "B-25:").notes and "SK-12" in _op(pk, "B-25:").sketch


def test_tl1_specimen_carries_the_turn_and_reads_the_loop_centre(kit):
    import physical_test_kit as K
    reg = kit["register"]
    tl1, tl1b = reg["TL-1"], reg["TL-1b"]
    assert "MITRE" in tl1["specimen"] and "spine stub" in tl1["specimen"] and "necked" in tl1["specimen"]
    assert "bore gauge" in tl1["steps"] and "LOOP CENTRE" in tl1["steps"] and "2 mm outboard" not in tl1["steps"]
    assert "loop centre" in tl1["pass_fail"].lower()
    assert "bore gauge" in tl1b["steps"] and "288" in tl1b["steps"]                       # m-7, m-8
    assert tl1b["specimen"].startswith(f"{K.TL1B_N_SPEC} lengths")
    assert K.TL1_STOCK_MM == pytest.approx(5 * 200 + 200 + 2 * 160)
    assert K.TL1_BUY_M * 1000.0 >= K.TL1_STOCK_MM * 1.1 and K.TL1_BUY_M >= 1.5            # m-8: 1 m was short


# ---------------------------------------------------------------- minors
def test_ops_405_408_give_a_spec_per_step(pk):
    n5 = _op(pk, "HE hinge eyes").notes
    assert "BT-301 fallback" in n5 and "bonded_nylon_tex135" in n5 and "bonded_nylon_tex90" in n5
    assert n5.count("[") >= 4                                                # neck, rows, box, baste
    assert "Nm 140/22" in n5 and "Nm 110/18" in n5
    n8 = _op(pk, "RTM roll-clip buckle tabs").notes
    assert "Nm 140/22" in n8 and "bonded_nylon_tex135" in n8


def test_imc_raw_ends_5mm_past_the_boxes(pk, kit):
    rs = pk["ctx"].rs
    q = rs.pieces["IMC"]
    L = q.bounds(cut=False)[3]
    assert L == pytest.approx(4 * P.IMC_FOLD) and P.IMC_FOLD > P.IMC_FOLD_BL041
    f1, f2 = P.IMC_FOLD, L - P.IMC_FOLD
    boxes = [ln for ln in q.internal_lines if "box-X" in (ln.label or "")]
    assert len(boxes) == 2
    for ln in boxes:
        ys = [p_[1] for p_ in ln.points]
        lo, hi = min(ys), max(ys)
        if hi <= L / 2:                                       # cam end: folded raw end lands at 2 * f1
            assert lo - f1 == pytest.approx(P.IMC_LOOP) and 2 * f1 - hi >= 5.0 - 1e-9
        else:                                                 # hook end: raw end lands at L - 2 * (L - f2)
            assert f2 - hi == pytest.approx(P.IMC_LOOP) and lo - (L - 2 * (L - f2)) >= 5.0 - 1e-9
    assert f"{4 * P.IMC_FOLD:.0f} mm" in kit["register"]["MT-1"]["specimen"]


def test_op_713_threads_the_hardware_first(pk):
    o = _op(pk, "IMC:")
    assert o.notes.index("HARDWARE FIRST") < o.notes.index("Box-X")
    assert "cam" in o.pieces and "G-hook" in o.pieces


def test_camo_print_is_production_only(pk):
    lines = [b for b in pk["bom"] if b.section == "fabric_print"]
    assert lines and all((b.proto_qty or 0.0) == 0.0 for b in lines)
    assert all("ON TOP of the unprinted" not in (b.notes or "") for b in lines)
    assert all("PRODUCTION ONLY" in (b.notes or "") or "TODO" in b.item for b in lines)


def test_webbing_pages_name_every_line_with_b25_and_rt(pk, tmp_path):
    import patterns_corrie_f_rev3_export as E
    import pdfplumber
    ids = [i for i, _ in E.WEB_MARKS]
    assert "B-25" in ids and "RT" in ids and "W3G" not in ids
    assert {i for g in E.WEB_GROUPS for i in g} == set(ids)
    rs = pk["ctx"].rs
    f = tmp_path / "marks.pdf"
    E.notes_and_marks_pdf(rs, ["B-18", "B-22"], f, "test")
    txt = " ".join((pg.extract_text() or "") for pg in pdfplumber.open(str(f)).pages)
    for word in ("MITRE R", "NECK", "EYE FOLD", "neck line", "floor seam line", "end of the sewn zone",
                 "fold round the CAM anchor bar", "toggle tab R"):
        assert word in txt, word


def test_guy_toggle_ledger_row_relabelled(pk):
    ck = M.checks(pk)
    assert ck["hardware_rows_by_keyword"] == [] and ck["unmapped_hardware"] == []
    with F.revision(3):
        names = [r["name"] for r in F.parts("M", "D2")]
    assert any(n.startswith("BL-004 REC: guy toggles x2") for n in names)
    assert not any(n.startswith("BL-004 REC: guy bar loops") for n in names)


def test_sk8_section_names_the_printed_stay_and_draws_the_floor():
    src = (ROOT / "designs" / "pack_5200" / "mfg_corrie_f_rev3.py").read_text()
    i = src.index("def sk_hinge_eye")
    body = src[i:src.index("\ndef ", i + 10)]
    assert "stay (carbon)" not in body and "printed PAHT-CF" in body and "throat floor" in body


def test_fit_r3_checks_w3_at_both_ends_of_the_owners_kit(kit):
    st = kit["register"]["FIT-R3"]["steps"]
    assert "(7) W3 SWEEP" in st and "BOTH ends" in st and "W3G" not in st
    assert "strap leaves the roll at its END" in st


def test_ledger_books_bl043_and_reconciles(pk):
    with F.revision(3):
        rows = {r["name"]: r["g"] for r in F.parts("M", "D2") if r["name"].startswith("BL-043")}
    assert len(rows) == 2
    tp = F.b25_topology()
    w38 = F._rec("poly_webbing_38mm", "mass_g_m")
    b25 = next(v for n, v in rows.items() if "B-25" in n)
    assert b25 == pytest.approx((tp["cut_mm"] - tp["cut_bl041_mm"]) / 1000.0 * w38, abs=0.01)   # ledger rounds to 0.01 g
    ck = M.checks(pk)
    assert ck["recon_unmatched"] == 0 and ck["recon_pieces_without_row"] == 0 and ck["mass_ok"]
    assert ck["box_mismatches"] == [] and ck["holds"] == [] and ck["unsequenced"] == []


def test_third_review_status_is_honest():
    st = {i: (c, s) for i, c, s, _ in M.THIRD_STATUS}
    assert {"Z-1", "Z-2", "M-1", "M-2", "M-3", "M-4"} | {f"m-{k}" for k in range(1, 15)} <= set(st)
    for i in ("M-1", "M-2", "M-4"):
        assert st[i][1] == "fixed"
    for i in ("Z-1", "Z-2", "M-3", "m-1", "m-11"):                  # hinge eye: fixed by BL-042 / BL-044
        assert st[i][1] == "fixed"
    assert not M.ready_to_cut()                                     # BL-044: NOT ready until a fourth review
