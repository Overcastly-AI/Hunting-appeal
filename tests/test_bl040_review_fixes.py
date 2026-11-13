"""BL-040: regression tests for the pre-cut review of the CORRIE F rev 3 release
(designs/pack_5200/analysis/review_20261113_rev3_release.md). Each test would have failed on the reviewed release."""
import copy
import csv
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import mfg_corrie_f_rev3 as M  # noqa: E402
import patterns_corrie_f_rev3 as P  # noqa: E402


@pytest.fixture(scope="module")
def pk():
    return M.package()


def _op(pk, word):
    return next(o for o in pk["ops"] if word in o.operation)


def _boxes(rs, pid, key=None):
    return {tuple(sorted((w, h))) for w, h, lab in M.boxes_of(rs.pieces[pid]) if key is None or key in lab}


# ---------------------------------------------------------------- B-1 hinge eye: one definition
def test_hinge_eye_one_box_everywhere(pk):
    rs = pk["ctx"].rs
    he = _boxes(rs, "HE")
    assert he == {tuple(sorted(P.HE_BOX))}                                     # BL-041 HE-PIN: 34 x 10 (was 34 x 34)
    assert _boxes(rs, "B-18", "HE") == he
    assert _boxes(rs, "B-01", "HE hinge eye") == he
    row = next(r for r in pk["load_points"] if r["point"] == "hinge eye")
    assert row["pattern"].startswith(f"box-X {P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f}")
    assert row["load_n"] == 1019.0 and "PT-3 1530" in row["proof"]          # m-2: 1.5 x 1019
    assert f"{P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f}" in _op(pk, "HE hinge eyes").notes   # BL-041 n-12: tautology removed


def test_b18_reaches_into_the_floor_seam_and_has_no_bottom_rows(pk):
    rs = pk["ctx"].rs
    b18 = rs.pieces["B-18"]
    x0, y0, x1, y1 = b18.bounds(cut=False)
    assert y1 - y0 == pytest.approx(P.B18_H) and P.B18_BELOW == P.SA_BODY      # 12 mm into the allowance
    rows = [ln for ln in b18.internal_lines if "perimeter row" in (ln.label or "")]
    assert len(rows) == 2 and not any(ln.closed for ln in rows)               # 3 sides only
    assert all(min(p[1] for p in ln.points) == pytest.approx(0.0) for ln in rows)  # open at the bottom edge
    pl = next(ln for ln in rs.pieces["B-01"].internal_lines if (ln.label or "").startswith("B-18 hinge-eye"))
    assert min(p[1] for p in pl.points) == pytest.approx(-P.B18_BELOW, abs=0.5)   # B-01 cut edge
    # the free eye is the one he_geometry solves for the pin (BL-041 HE-PIN; was 25 mm), the box clears the seam line
    assert rs.geo["he"]["eye_mm"] == pytest.approx(P.HE_EYE)
    assert rs.geo["he"]["box_z_above_seam"][0] > 0


def test_box_mismatch_check_covers_every_stack(pk):
    ctx = pk["ctx"]
    assert M.box_mismatches(ctx) == []
    bad = copy.copy(ctx)
    bad.rs = copy.deepcopy(ctx.rs)
    b17 = bad.rs.pieces["B-17"]                                  # the reviewed release: T3 box 38 x 38 on B-17
    for ln in b17.internal_lines:
        if "T3 tongue box-X" in (ln.label or ""):
            ln.label = "T3 tongue box-X 38x38"
    b18 = bad.rs.pieces["B-18"]
    for ln in b18.internal_lines:
        if "HE eye box-X" in (ln.label or ""):
            ln.label = "HE eye box-X 38x38"
    out = M.box_mismatches(bad)
    assert any("B-17" in m for m in out) and any("B-18" in m for m in out)
    assert {s[0] for s in M.BOX_STACKS} >= {"B-01", "B-18", "B-17", "B-22", "B-02h", "B-03", "B-07"}


def test_pt3_specimen_is_the_op_405_drawing():
    import physical_test_kit as K
    kit = K.build(write=False)
    pt3 = kit["register"]["PT-3"]
    for word in ("op 4.05", f"{P.HE_BOX[0]:.0f} x {P.HE_BOX[1]:.0f}", "folded in half", "90 x 62", "cut edge"):
        assert word in pt3["specimen"], word


# ---------------------------------------------------------------- B-2 roll top
def test_roll_top_has_a_mating_buckle_tab(pk):
    rs = pk["ctx"].rs
    assert "RTM" in rs.pieces and any(w["id"] == "RTM" for w in rs.webbing)
    g = rs.pieces["B-03"]
    assert any("RTM roll-clip buckle tab" in (ln.label or "") for ln in g.internal_lines)
    # BL-041 RT-FWD: the bar sits RT_CLEAR above the B-26 cord, on the clip path (was 150 mm under, mid depth)
    assert rs.geo["rtm"]["z"] == pytest.approx(rs.geo["z_c"] - rs.geo["rtm"]["below_seam_mm"])
    # BL-043 W3-OVER: the buckle sits under the lowest W3 edge (kit S 15 in), about 200 mm under the seam
    assert 150.0 < rs.geo["rtm"]["below_seam_mm"] <= 220.0
    b07 = rs.pieces["B-07"]
    assert sum("RT roll-clip strap" in (ln.label or "") for ln in b07.internal_lines) == 2
    seqs = [o.seq for o in pk["ops"]]
    rtm = _op(pk, "RTM roll-clip buckle tabs")
    frame = _op(pk, "Frame-side box seams")
    assert seqs.index(rtm.seq) < seqs.index(frame.seq)                  # flat work before the gusset seams
    rt = _op(pk, "RT roll-clip straps on the flat hem")
    assert seqs.index(rt.seq) < seqs.index(_op(pk, "Roll-top hem").seq)
    assert any(r["part"] in ("RT", "RTM") and r["load_n"] is None for r in pk["load_points"])
    assert any(h["material_id"] == "buckle_side_release_25mm" for h in rs.hardware)


def test_rtm_clear_of_the_other_gusset_placements(pk):
    rs = pk["ctx"].rs
    x0, y0, x1, y1 = rs.geo["rtm"]["rect"]
    for ln in rs.pieces["B-03"].internal_lines:
        lab = ln.label or ""
        if ln.kind != "placement" or not ln.closed or "RTM" in lab or lab.startswith("FP"):
            continue
        xs, ys = [p[0] for p in ln.points], [p[1] for p in ln.points]
        overlap = not (max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1)
        assert not overlap, lab


# ---------------------------------------------------------------- B-3 keeper / pocket stack, M-1 B-26
def test_aft_corner_seam_states_the_stack(pk):
    o = _op(pk, "Aft corner seams")
    assert "ON TOP of the mesh" in o.notes and "SK-9" in o.sketch and "B-26" in o.notes
    assert "K-W" in o.pieces
    fp = _op(pk, "FP pockets")
    assert "baste it at 6 mm inside the allowance only" in fp.notes
    fr = _op(pk, "Frame-side box seams")
    assert "ONE end of the B-26" in fr.notes and "ends (15 mm in)" not in fr.notes


# ---------------------------------------------------------------- majors
def test_m2_b17_box_and_m4_b22_label(pk):
    rs = pk["ctx"].rs
    assert _boxes(rs, "B-17") == {(34.0, 34.0)}
    note = rs.pieces["B-22"].labels["note"]
    assert "INSIDE B-02h" in note and "OUTSIDE" not in note and "149" not in note
    assert f"{rs.geo['b22']['placed_x']:.1f}" in note


def test_m3_collar_ring_gusset_has_one_notch_set(pk):
    rs = pk["ctx"].rs
    g = rs.pieces["B-03"]
    top = g.edge_points("top")                      # runs aft -> frame; frame end is the last point
    fx, fy = top[-1]
    d = sorted(round(math.hypot(n.x - fx, n.y - fy), 1) for n in g.notches if "collar ring" in n.label)
    Lg = g.edge_length("top")
    assert d == pytest.approx([0.0, 50.0, 100.0, round(Lg, 1)], abs=0.6)
    # partners on the collar wrap B-06 (x 0 at the L frame corner, 690 at the R frame corner)
    b06 = rs.pieces["B-06"]
    L6 = b06.edge_length("bottom")
    near = [n.x for n in b06.notches if "collar ring" in n.label and abs(n.y) < 1e-6]
    for want in (50.0, 100.0):
        assert min(abs(x - want) for x in near) < 1.0                     # L gusset from its frame end
        assert min(abs((L6 - x) - want) for x in near) < 1.0              # R gusset from its frame end


def test_m6_qc14_primary_targets(pk):
    m = pk["mass"]
    assert m["primary_delta_by_kit_g"]["base"] == pytest.approx(64.1, abs=1.0)   # the review's +64.1 g
    assert m["primary_base_g"] == pytest.approx(m["base_g"] + m["primary_delta_by_kit_g"]["base"], abs=0.2)
    qc14 = next(q for q in pk["qc"] if q["id"] == "QC-14")
    assert f"{m['primary_base_g']:.0f} g" in qc14["pass"] and "PRIMARY" in qc14["check"]


def test_m7_m8_ll_h_level_and_conditions(pk):
    import physical_test_kit as K
    assert M.LLH_N == pytest.approx(432.0)
    for r in pk["load_points"]:
        assert "366" not in r["proof"], r["point"]
    guy = next(r for r in pk["load_points"] if r["point"] == "port guy, bag end")
    assert guy["hardware_n"] == pytest.approx(490.0) and guy["hardware_margin"] == pytest.approx(490 / 288, abs=0.01)
    kit = K.build(write=False)
    reg = kit["register"]
    for t in ("LL-H", "MT-3"):
        for word in ("WET", "COLD", "freezer"):
            assert word in reg[t]["steps"], (t, word)
    assert "432 N" in reg["LL-H"]["steps"] and "44.0 kg" in reg["LL-H"]["steps"]


def test_m9_sew_f_in_the_kit():
    import physical_test_kit as K
    kit = K.build(write=False)
    assert kit["register"]["SEW-F"]["status"] == "ACTIVE"
    assert K.SEWF_PEAK == 442                                       # BL-041 n-13: 1.15 x 384
    assert any(o["test"] == "SEW-F" and o["group"] == "G4" for o in kit["order"])
    assert any(o["test"] == "FIT-R3" and o["group"] == "G7" for o in kit["order"])     # m-18


def test_m10_m11_camo_line_and_prototype_cost(pk):
    camo = [b for b in pk["bom"] if b.section == "fabric_print"]
    assert len(camo) == 1
    if (M.CAMO_DIR / "bom_print_line_proposed.csv").exists():
        assert camo[0].cost_usd and "camo/README.md" in camo[0].item and "strike-off" in camo[0].notes
    c = pk["costing"]
    assert c["prototype_buy"]["fabric_usd"] > c["fabric_usd_primary"]          # 1-bag markers + shop steps cost more
    assert c["prototype_usd"] > c["material_usd_primary"]


def test_m12_machine_minimum_and_m13_first_op(pk):
    assert "140/22" in M.PROTO_MACHINE_MIN and "tex 135" in M.PROTO_MACHINE_MIN
    assert "PROTO" in M.MACHINES
    o = pk["ops"][[x.seq for x in pk["ops"]].index("1.01")]
    assert "BOTTOM edge only" in o.notes and "top and bottom" not in o.notes
    assert "140/22" in (ROOT / "designs" / "pack_5200" / "BUILD_PLAN.md").read_text()


# ---------------------------------------------------------------- minors
def test_minor_pattern_fixes(pk):
    rs = pk["ctx"].rs
    assert any(ln.kind == "cut_inside" for ln in rs.pieces["B-09p"].internal_lines)                        # m-4
    assert not any(ln.kind == "cut_inside" for ln in rs.pieces["B-13x"].internal_lines)                   # m-7
    assert any(ln.kind == "cut_inside" for ln in rs.pieces["B-12"].internal_lines)
    slot = next(ln for ln in rs.pieces["B-11"].internal_lines if ln.kind == "cut_inside")                 # m-11
    xs = [p[0] for p in slot.points]
    assert max(xs) - min(xs) == pytest.approx(27.0)
    assert "no load rating" in rs.pieces["B-11"].labels["note"].lower()                                            # m-12
    assert "carabiner" in rs.pieces["B-24"].labels["note"] and "rated 38 mm hook" not in rs.pieces["B-24"].labels["note"]


def test_minor_op_fixes(pk):
    lid_tacks = [o for o in pk["ops"] if o.operation.startswith("Lid:") and "bartack" in o.operation]
    assert lid_tacks and all(o.thread_id == M.THREAD["body"] for o in lid_tacks)                       # m-8
    assert not any(o.seam == "ZIP" and "perimeter" in o.operation for o in pk["ops"])
    assert not any(o.operation.startswith("F-EL") for o in pk["ops"])                                   # m-6
    hem = _op(pk, "elastic channel hems")
    assert "per channel" in hem.notes and "NOT lapped" in hem.notes
    assert "sections F and M" not in _op(pk, "Final inspection").notes                                   # m-9
    seqs = [o.seq for o in pk["ops"]]
    fold = _op(pk, "Fold the seam-inserted loops")                                                        # m-10
    assert seqs.index(fold.seq) < seqs.index(_op(pk, "Frame-side box seams").seq)
    assert not any(o.operation.startswith(("K-W:", "HPL:", "E5:", "I2T:", "I2K:")) for o in pk["ops"])


def test_colourway_is_a_named_primary_pairing(pk):
    import yaml
    from huntkit.viz3d import export as EX
    cw = yaml.safe_load((ROOT / "designs" / "apparel" / "colorways.yaml").read_text())
    pr = next(a for a in cw["accent_pairings"] if a["id"] == "krummholz")
    assert pr["body"] == "krummholz_sage" and pr["accent_pattern"] == "owner_base"
    v = EX.colorway({})
    assert v["fallback"] is False and v["body"] == "#6E745B" and v["pairing"] == "krummholz"
    assert EX.colorway({"colorway": "talus"})["fallback"] is False
    body = [b for b in pk["bom"] if b.section == "fabric" and b.material_id == "cordura_330d_nylon66"]
    assert body and "Krummholz Sage #6E745B" in body[0].notes


def test_review_status_and_ready_to_cut(pk):
    ids = {i for i, *_ in M.REVIEW_STATUS}
    assert {f"B-{k}" for k in range(1, 4)} | {f"M-{k}" for k in range(1, 14)} | {f"m-{k}" for k in range(1, 22)} <= ids
    assert all(st == "fixed" for _, c, st, _ in M.REVIEW_STATUS if c in ("blocker", "major"))
    # BL-043: the third review's hinge-eye items (Z-1, Z-2, M-3) stay open until BL-042 / BL-044
    open_ = [i for i, c, st, _ in M.REVIEW_STATUS + M.RECHECK_STATUS + M.THIRD_STATUS
             if c in ("blocker", "major") and st != "fixed"]
    assert M.ready_to_cut() == (M.FOURTH_REVIEW_DONE and not open_)         # BL-044: a fourth review gates it


def test_released_cutlist_has_unique_piece_ids():
    f = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "patterns" / "cutlist.csv"
    if not f.exists():
        pytest.skip("release not generated")
    ids = [r["piece_id"] for r in csv.DictReader(f.open())]
    assert len(ids) == len(set(ids))
    assert "RTM" not in ids                                           # webbing is in the webbing table, not here
