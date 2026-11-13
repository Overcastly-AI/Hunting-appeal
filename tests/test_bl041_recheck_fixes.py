"""BL-041: regression tests for the design-reviewer re-check of the CORRIE F rev 3 release
(designs/pack_5200/analysis/review_20261113_rev3_recheck.md) and the adopted crown-tube result
(designs/pack_5200/analysis/crown_tube_guy_loop.md). Each test checks geometry or numbers, not just that code runs,
and each would have failed on the re-checked release."""
import copy
import json
import math
import sys
from pathlib import Path

import pytest
from shapely.geometry import LineString, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import mfg_corrie_f_rev3 as M  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402


@pytest.fixture(scope="module")
def pk():
    return M.package()


@pytest.fixture(scope="module")
def kit():
    import physical_test_kit as K
    return K.build(write=False)


def _op(pk, word):
    return next(o for o in pk["ops"] if word in o.operation)


# ---------------------------------------------------------------- X-2 eye on the pin
def test_eye_at_pin_within_3mm_over_the_bracket(pk):
    hg = pk["ctx"].rs.geo["he"]
    g = P.he_geometry()
    assert g["pin_z"] == pytest.approx(25.0)                                  # frame z 60 with the floor at z 35
    for fy in g["faces_y"]:
        for t in (1.2, P.HE_T, 2.0):
            assert abs(P.he_pin_z(P.HE_EYE, fy, t) - g["pin_z"]) <= P.HE_PIN_TOL, (fy, t)
    assert abs(hg["pin_z_design"] - 25.0) <= 1.0
    # the BL-040 eye (box top +38, 25 mm eye) puts the pin far outside the tolerance: the test would have caught X-2
    assert g["pin_z"] < 38.0 - P.HE_PIN_TOL


def test_box_below_the_cheeks_only_the_neck_in_the_throat(pk):
    hg = pk["ctx"].rs.geo["he"]
    lo, top = hg["box_z_above_seam"]
    assert top <= hg["cheek_z"][0] - P.HE_CHEEK_CLEAR + 1e-9                    # no box stack against the cheeks
    assert lo >= P.HE_BOX_GAP - 1e-9 and lo > 0
    assert hg["neck_w"] == pytest.approx(hg["throat"])                         # 18 mm neck, 18 mm throat
    assert hg["fold_z_flat"] > hg["pin_target_z"]                              # the eye reaches over the pin
    assert P.HE_CUT == pytest.approx(2 * (P.B18_BELOW + P.HE_BOX_GAP + P.HE_BOX[1] + P.HE_EYE))


def test_loop_length_closed_form_is_consistent():
    g = P.he_geometry()
    for z in (20.0, 25.0, 30.0):
        e = g["loop_len"](z) / 2
        assert P.he_pin_z(e) == pytest.approx(z, abs=0.05)                     # inverse of the forward model
    # a longer eye puts the pin higher (monotonic)
    assert P.he_pin_z(P.HE_EYE + 2) > P.he_pin_z(P.HE_EYE)


# ---------------------------------------------------------------- X-1 no row across the open eye
def _eye_box_on(rs, pid):
    hg = rs.geo["he"]
    x0, z0, x1, z1 = hg["eye_footprint"]
    if pid == "B-18":
        cx = P.B18_W / 2
        return [box(cx + x0, P.B18_BELOW + z0, cx + x1, P.B18_BELOW + z1)]
    s01 = P.F.b01_flat_s()
    return [box(sx * P.STAY_X + x0, s01(P.BC.Z0 + z0), sx * P.STAY_X + x1, s01(P.BC.Z0 + z1)) for sx in (-1, 1)]


def test_no_stitch_row_crosses_the_open_eye(pk):
    rs = pk["ctx"].rs
    for pid in ("B-18", "B-01"):
        eyes = _eye_box_on(rs, pid)
        for ln in rs.pieces[pid].internal_lines:
            if ln.kind != "stitch" or len(ln.points) < 2:
                continue
            lab = ln.label or ""
            if "HE" in lab or lab == "":                                       # the HE box itself (and its diagonals)
                continue
            geom = LineString(list(ln.points) + ([ln.points[0]] if ln.closed else []))
            for e in eyes:
                assert not geom.intersects(e.buffer(-0.01)), (pid, lab)


def test_bl040_row_heights_would_have_crossed_the_eye():
    """The detector catches the BL-040 geometry: rows at +41 / +47 across an eye spanning +38..+63."""
    eye = box(-19, 38, 19, 63)
    for zr in (41.0, 47.0):
        assert LineString([(-42, zr), (42, zr)]).intersects(eye)


def test_op_405_sews_the_rows_before_the_he(pk):
    n = _op(pk, "HE hinge eyes").notes
    i_rows, i_place, i_box = n.index("B-18 ROWS FIRST"), n.index("PLACE THE HE"), n.index("(4) BOX")
    assert i_rows < i_place < i_box
    assert "through B-18 + B-01 ONLY" in n and "No stitching crosses the eye" in n
    assert M.HE_405_STEPS == ("NECK", "B18-ROWS", "PLACE-HE", "BOX", "BASTE")


# ---------------------------------------------------------------- Y-1 PT-3 rig and specimen; HE-FIT gate
def test_pt3_rig_and_specimen(kit):
    reg = kit["register"]
    pt3 = reg["PT-3"]
    assert "rows first, before HE" in pt3["specimen"] and f"38 x {P.HE_CUT:.0f}" in pt3["specimen"]
    assert f"{P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f}" in pt3["specimen"] and "basted" in pt3["specimen"]
    st = pt3["steps"]
    assert "B-05 strip ALONE" in st and "B-01 top edge stays FREE" in st and "18 mm wide slot" in st
    assert "eye still open" in pt3["pass_fail"]
    he = reg["HE-FIT"]
    assert he["status"] == "ACTIVE" and "22-28" in he["pass_fail"]
    order = [o["test"] for o in kit["order"] if o["group"] == "G2"]
    assert order.index("HE-FIT") < order.index("PT-3")


# ---------------------------------------------------------------- Y-2 roll clip clear of the rifle keeper, cords, W3
def test_clip_path_clearances(pk):
    rs = pk["ctx"].rs
    rc = rs.geo["rt_clear"]
    assert rc["min_gap"] >= P.RT_CLEAR - 1e-6, rc["min_pair"]
    kinds = {k.split(" | ")[1].split(" x")[0] for k in rc["gaps"]}
    assert {"muzzle tab", "muzzle keeper cord", "hose slot", "bow tab", "B-26 cord (R)"} <= kinds
    parts = {k.split(" | ")[0] for k in rc["gaps"]}
    assert parts == {"RTM tab", "buckle envelope", "strap corridor"}           # buckle body + strap path, not the tab only
    # BL-043 (M-1, DECISION W3-OVER) supersedes BL-041 RT-OVER-W3: the buckle now sits under the B-26 cord, so the cord
    # crosses the strap (accepted, soft on soft) and no longer the flat RTM tab; W3G is deleted
    assert set(rc["accepted"]) == {"strap corridor | B-26 cord (R)"}
    g = rs.pieces["B-03"]
    assert not [ln for ln in g.internal_lines if "W3G" in (ln.label or "")]
    assert "W3G" not in rs.pieces and not any(w["id"] == "W3G" for w in rs.webbing)
    assert rc["w3_hard_min"] >= P.RT_CLEAR - 1e-6


def test_bl040_layout_fails_the_clearance_check(pk):
    """The re-checked layout (RTM at mid depth, muzzle tabs 60 / 130) fails the new check: it would have caught Y-2."""
    rs = pk["ctx"].rs
    G = copy.deepcopy(rs.pieces["B-03"])
    M_ = P._maps(P.F.make())
    gf = M_["gy_frame"]
    G.internal_lines = [ln for ln in G.internal_lines if "muzzle" not in (ln.label or "")]
    for dx in (60.0, 130.0):
        P._b11_marks(G, gf(P.B11_MUZ_Z) + dx, M_["sig"](P.B11_MUZ_Z), "muzzle keeper")
    rl = dict(rs.geo["rt_layout"])
    rl["x"] = 0.5 * (gf(595.0) + M_["gy_aft"](595.0))
    rl["y_bar"] = M_["sig"](595.0)
    assert P.rt_clearances(G, rl)["min_gap"] < P.RT_CLEAR


def test_fit_r3_covers_rifle_roll_clip_and_w3(kit):
    st = kit["register"]["FIT-R3"]["steps"]
    assert "ROLL CLIP + RIFLE + W3" in st and "MK-GAP" in st


def test_hem_strap_and_gusset_path_agree(pk):
    """BL-043 M-2 (DECISION RT-ORIGIN) supersedes BL-041's origin at the clip path: the strap is sewn at the roll end
    (gusset centre), its sewn 60 mm on the frame-side half, ending at the roll-end notch."""
    rs = pk["ctx"].rs
    rl = rs.geo["rt_layout"]
    assert rl["frac_top"] == pytest.approx(0.5)
    rt = rs.geo["rt_on_b07"]
    assert rt["R"]["x1"] == pytest.approx(rt["R"]["x_centre"])
    assert rt["L"]["x0"] == pytest.approx(rt["L"]["x_centre"])


# ---------------------------------------------------------------- Y-3 machine
def test_machine_minimum_and_build_plan():
    assert "304 zigzag" in M.PROTO_MACHINE_MIN and "BT-301" in M.PROTO_MACHINE_MIN
    assert "UNRATED" in M.BT_301_FALLBACK and "4 passes" in M.BT_301_FALLBACK
    bp = (ROOT / "designs" / "pack_5200" / "BUILD_PLAN.md").read_text()
    assert "120/19" not in bp and "bonded_nylon_tex70" in bp and "304 zigzag" in bp
    assert "bonded_poly_tex90" not in bp


def test_every_304_tack_is_unrated(pk):
    assert all(r["load_n"] is None for r in pk["load_points"] if r["stitch"] == "304")


# ---------------------------------------------------------------- Y-4 crown tube (structural result adopted)
def test_b25_is_38mm_and_clears_the_spine_clamp(pk):
    rs = pk["ctx"].rs
    b = rs.geo["b25"]
    assert b["width_mm"] == 38.0 and b["band"] == (26.5, 64.5)
    assert b["clear_to_clamp_mm"] >= b["min_clear"]
    assert rs.pieces["B-25"].material_id == "poly_webbing_38mm"
    assert b["length_bl041_mm"] == pytest.approx(387.0, abs=1.0)    # BL-043 B25-TOPO adds the drawn turn: length_mm
    assert "GBL" not in rs.pieces and not any(w["id"] == "GBL" for w in rs.webbing)
    rows = [r for r in pk["load_points"] if r["point"] == "B-25 bridle toggle tab"]
    assert rows and all(r["load_n"] == 323.0 and "TL-1 494 N" in r["proof"] and r["sf"] >= 1.3 for r in rows)
    assert not any(r["part"] == "GBL" for r in pk["load_points"])


def test_tl1_and_tl1b(kit):
    reg = kit["register"]
    tl = reg["TL-1"]
    assert "494 N" in tl["title"] and "real rev C crown top bar stock" in tl["specimen"]
    assert "0.40 mm" in tl["pass_fail"] and "0.02 mm" in tl["pass_fail"] and "NO cradle" in tl["steps"]
    assert reg["TL-1b"]["status"] == "ACTIVE" and reg["TL-1b"]["gates"].startswith("none")
    assert any(o["test"] == "TL-1b" and o["release"] == "DATA" for o in kit["order"])


def test_loadpath_a3_carries_the_rev3_fix():
    d = json.loads((ROOT / "designs" / "pack_5200" / "analysis" / "loadpath_verification.json").read_text())
    a3 = next(r for r in d["rows"] if r["id"] == "A3")
    assert "38 mm" in a3["fix"]["change"] and a3["fix"]["after_min"] >= 1.2
    assert any(c["demand_n"] == pytest.approx(322.8, abs=0.5) for c in a3["fix"]["checks"])


# ---------------------------------------------------------------- Y-5 camo / cost; n-10
def test_first_build_has_no_print_and_buys_whole_cones(pk):
    pb = pk["costing"]["prototype_buy"]
    pr = [r for r in pb["rows"] if r["section"] == "fabric_print"]
    assert pr and all((r["prototype_usd"] or 0) == 0 for r in pr)
    for r in pb["rows"]:
        if r["section"] == "thread":
            assert "cone" in r["how"]
            cone_m = M.THREAD_CONE_G / M.mat(r["material_id"]).require("mass_g_m")
            assert r["prototype_qty"] / cone_m == pytest.approx(round(r["prototype_qty"] / cone_m))
    assert any(r["material_id"] == "seam_sealer" and r["prototype_qty"] == 1 and "tube" in r["unit"] for r in pb["rows"])


def test_print_shipping_in_the_kit(kit):
    assert any("shipping for the HyperD print" in r["item"] for r in kit["shopping"])


# ---------------------------------------------------------------- m-19 / n-15 meat-strap cam anchor
def test_im_cam_has_a_sewn_anchor(pk):
    rs = pk["ctx"].rs
    imc = rs.pieces["IMC"]
    boxes = [b for b in M.boxes_of(imc)]
    assert len(boxes) == 2 and all(sorted((w, h)) == [21.0, 25.0] for w, h, _ in boxes)
    folds = [ln for ln in imc.internal_lines if ln.kind == "fold"]
    assert len(folds) == 2
    # clear loop at each end >= 18 mm (fold to the nearest box edge)
    by = sorted(min(q[1] for q in ln.points) for ln in imc.internal_lines if "box-X" in (ln.label or ""))
    fy = sorted(f.points[0][1] for f in folds)
    assert by[0] - fy[0] >= 18.0 - 1e-6 and fy[1] - (by[1] + 25.0) >= 18.0 - 1e-6
    rows = [r for r in pk["load_points"] if r["part"] == "IMC"]
    assert len(rows) == 2 and all(r["load_n"] == 605.0 and r["sf"] > 1.5 for r in rows)
    fit = _op(pk, "Fit the hardware")
    assert "SK-11" in fit.sketch and "IMC" in fit.notes and "cam threaded" not in fit.notes


# ---------------------------------------------------------------- minors
def test_minors(pk, kit):
    import physical_test_kit as K
    ec = K.im3_ec_load()
    assert ec["min_n"] == 24 and "R <= 0.02" not in kit["register"]["IM3-EC"]["steps"]   # n-1: "R about 0.02"
    assert "0.30 then 0.40" not in kit["register"]["CA-1"]["title"]             # n-2
    lv = K.release_levels()
    assert "STOP" in K.fallback_txt(lv) and all(f"{lev}" not in K.fallback_txt(lv) for p_, lev in lv["fallback_table"]
                                                 if lev >= K.R1_CA1_LEVEL)
    assert "COLD:" in kit["register"]["LL-H"]["steps"].split(";")[-1] or any(
        s.strip().startswith("COLD") for s in kit["register"]["LL-H"]["steps"].split(";"))   # n-3: its own step
    assert not any("7.end" in o.notes for o in pk["ops"])                       # n-4
    tg = next(r for r in pk["load_points"] if r["point"] == "port guy, toggle end")
    assert "POM toggle" in tg["hardware"]                                        # n-8a
    assert K.SEWF_PEAK == round(1.15 * 384)                                     # n-13
    assert "ZIPPER / EDGE FOOT" in _op(pk, "Floor B-05").notes                  # n-14
    ba = (ROOT / "designs" / "pack_5200" / "analysis" / "bag_attachment.md").read_text()
    assert "SUPERSEDED for CORRIE F rev 3" in ba                                # n-11


def test_box_checker_checks_position_and_missing_pieces(pk):
    ctx = pk["ctx"]
    assert M.box_mismatches(ctx) == []
    bad = copy.copy(ctx)
    bad.rs = copy.deepcopy(ctx.rs)
    for ln in bad.rs.pieces["B-18"].internal_lines:                           # move the B-18 box 5 mm up
        if "HE eye" in (ln.label or "") or (ln.kind == "stitch" and not ln.label and len(ln.points) == 2):
            ln.points = [(x, y + 5.0) for x, y in ln.points]
    assert any("B-18 HE box centre" in m for m in M.box_mismatches(bad))
    gone = copy.copy(ctx)
    gone.rs = copy.deepcopy(ctx.rs)
    del gone.rs.pieces["RTM"]
    assert any("MISSING" in m for m in M.box_mismatches(gone))


def test_ledger_books_the_rev3_parts():
    import corrie_f as F
    with F.revision(3):
        rows = {r["name"]: r for r in F.parts("M", "D2")}
    b = {n: r["g"] for n, r in rows.items() if n.startswith("BL-041")}
    assert len(b) == 6                  # BL-043 deleted the W3G row (DECISION W3-OVER)
    assert next(v for n, v in b.items() if "B-18" in n) == pytest.approx(3.1, abs=0.1)
    assert next(v for n, v in b.items() if "RTM" in n) > 0 and next(v for n, v in b.items() if "GBL" in n) < 0
    assert next(v for n, v in b.items() if "B-25" in n) == pytest.approx(3.39, abs=0.02)
    rs = P.build("B")
    rec = P.reconcile(rs)
    assert not rec["unmatched_rows"] and not rec["pieces_without_row"] and not rec["row_ids_not_drafted"]
    assert P.mass_check(rs)["ok"]


def test_recheck_status_and_ready_to_cut():
    ids = {i for i, *_ in M.RECHECK_STATUS}
    assert {"X-1", "X-2", "Y-1", "Y-2", "Y-3", "Y-4", "Y-5"} | {f"n-{k}" for k in range(1, 16)} <= ids
    open_major = [i for i, c, st, _ in M.RECHECK_STATUS + M.REVIEW_STATUS + M.THIRD_STATUS
                  if c in ("blocker", "major") and st != "fixed"]
    assert M.ready_to_cut() == (not open_major)
