"""BL-034 part A: thread / hours from the op sequence, hardware records, pattern marks, D1 seams."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "designs" / "pack_5200", ROOT / "designs" / "pack_5200" / "concepts",
          ROOT / "designs" / "pack_5200" / "bag_comp"):
    sys.path.insert(0, str(p))

import build_effort_rev3 as BE  # noqa: E402
import patterns_corrie_f_rev3 as PR  # noqa: E402
import corrie_f as F  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def eff():
    return BE.compute()


@pytest.fixture(scope="module")
def rs():
    return PR.build("today")


def test_cache_matches_a_fresh_run(eff):
    c = BE.load()
    assert c["thread_g"] == pytest.approx(eff["thread_g"], abs=0.05)
    assert c["hours_per_bag"] == pytest.approx(eff["hours_per_bag"], abs=0.05)


def test_thread_and_hours_from_the_ops(eff):
    tot = eff["thread_g_total"]
    assert 15.0 < tot < 22.0 and tot > 4.0 * 3                       # ticket: ~21 g (BOM incl. waste) vs 4 g booked
    live = [r for r in eff["ops"] if not r["duplicate_of"]]
    assert tot == pytest.approx(sum(r["thread_g"] for r in live), abs=0.05)
    assert eff["thread_g_package_incl_waste_and_duplicates"] > tot  # waste + double-sewn ops are out of the bag mass
    h = eff["hours_per_bag_total"]
    assert 68.0 < h < 74.0                                           # ticket: ~71 h a bag
    assert h + eff["hours_one_off"] + sum(d["hours"] for d in eff["duplicates"]) == pytest.approx(
        eff["hours_package_total"], abs=0.05)
    assert eff["hours_by_step"]["7 Straps and webbing"] > 5.0      # webbing, lid and fly are counted
    assert eff["hours_by_step"]["6 Crown lid B-29 (as hunted)"] > 5.0 and eff["hours_by_step"]["9 Rain fly F-01"] > 3.0


def test_ledger_books_thread_and_records():
    with F.revision(3):
        rows = F.parts("M", "D2")
        m = F.build_metrics("D2")
    e = BE.load()
    thr = {r["cfg"]: r["g"] for r in rows if r["name"].startswith("BL-034 thread")}
    booked = sum(r["g"] for r in rows if r["name"].startswith(("attachment system: thread", "B-24-thr")))
    assert sum(thr.values()) + booked == pytest.approx(e["thread_g_total"], abs=0.05)
    us = next(r for r in rows if r["name"].startswith("US-tg:"))["g"] + \
        next(r for r in rows if r["name"].startswith("BL-034 records: US1/US2"))["g"]
    assert us == pytest.approx(2 * MAT.load("triglide_25mm").require("stainless_alt_mass_g"), abs=0.01)
    assert F.TAIL_KEEPER_G == pytest.approx(15.0 * 0.090, abs=1e-6)
    assert m["beginner_hours_with_addons"] == pytest.approx(e["hours_per_bag_total"], abs=0.05)
    assert m["beginner_hours_hours_model"] < m["beginner_hours_with_addons"]


def test_hardware_constants_read_the_records():
    import bag_concepts as BC
    import corrie as CO
    import attach_diet as AD
    from huntkit.gendesign import attach_system as AS, meat_haul as MH
    assert BC.SLIDER_G == MAT.load("slider_10").require("mass_g") == 19.0
    assert CO.SLIDER5_G == F.LID_SLIDER5_G == MAT.load("slider_5").require("mass_g") == 4.9
    assert AS.TOGGLE_G == AD.TOGGLE_G == MAT.load("pom_toggle").require("mass_g") == 1.7
    assert AS.TRIGLIDE_G == MAT.load("triglide_25mm").require("mass_g") == 2.6
    assert MH.cradle_parts_g({})["tri-glide keepers (2)"] == pytest.approx(22.0)


def test_pattern_marks(rs):
    g3 = rs.pieces["B-03"]
    assert sum(1 for ln in g3.internal_lines if ln.kind == "placement" and ln.label.startswith("B-11 lash tab")) == 4
    assert rs.pieces["B-11"].quantity == 8 and rs.geo["b11"]["per_gusset"] * 2 == 8
    kw = sum(n.label.count("K-W keeper") for n in g3.notches)
    assert kw == 6                                       # W3 R and L share one notch (same height, merged label)
    assert rs.geo["kw_z"]["W1"]["R"] < rs.geo["kw_z"]["W1"]["L"] < rs.geo["kw_z"]["W2"]["R"]
    b28 = [ln.label for ln in rs.pieces["B-02h"].internal_lines if "B-28 front tab" in (ln.label or "")
           and "box-X" in ln.label]
    assert b28 and all("21x20" in s and "OUTSIDE" in s for s in b28)
    for pid, want in (("W3", "21x25"), ("IM1", "21x25"), ("US", "21x25"), ("B-25", "21x15")):
        labs = [ln.label for ln in rs.pieces[pid].internal_lines if "box-X" in (ln.label or "")]
        assert labs and all(want in s for s in labs), pid
    for k in rs.graded["W3"].values():
        assert any("box-X 21x25" in (ln.label or "") for ln in k.internal_lines)
    b24 = [ln.label for ln in rs.pieces["B-24"].internal_lines if "box-X" in (ln.label or "")]
    assert len(b24) == 4 and sum("34x20" in s for s in b24) == 3
    assert any("F-02 fly pocket" in (ln.label or "") for ln in rs.pieces["B-05"].internal_lines)
    # B-25 toggle loop: fold at 30, box edge 2 mm from the tip -> clear loop >= 13 mm (POM toggle 8 + 5)
    clear = PR._tip_box_y(30.0, PR.B25_BOX[1]) - PR.B25_BOX[1] / 2 - 30.0
    assert clear >= 13.0 - 1e-9


def test_d1_has_real_seam_pairs():
    with F.revision(3):
        b = F.build(F.make(), "D1", "B")
    for s, _ in b.seams:
        a, c = s.a, s.b
        assert not (len(a) == 1 and len(c) == 1 and a[0].piece is c[0].piece and a[0].name == c[0].name), s.name
    rep = {r.seam.name: r for r in check_seams([s for s, _ in b.seams], tol_mm=1.0).results}
    assert abs(rep["hinge band R | gusset R (above the zip)"].error_mm) < 0.5
    assert abs(rep["hinge band L | gusset L (above the zip)"].error_mm) < 0.5
    # the lid side is longer by team C's lid ease only (3 mm a side)
    assert rep["lid | gussets + hinge band (#10 zip, inverted U, R 60)"].error_mm == pytest.approx(6.0, abs=0.5)
