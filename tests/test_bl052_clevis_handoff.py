"""BL-052: hand-off from BL-051 (h1_crown.md 4). Clevis hardware from h1_bedfit.JOINT, the kit text (US-route /
CLEVIS-SHARE hardware, US1 / US2 arm-root gauges in T1 and the MT-1 cradle pull, the belly record, the required
CLEVIS-SHARE gauge), the 60 mm minimum cradle belly (strap gauge, card line, assumption), and the CLEVIS-FACE
inspection after FIT-US / T9. Checks the generated values, the register and the regenerated release files."""
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(HERE / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import corrie_f as F  # noqa: E402

REL = ROOT / "outputs" / "release"
MFG = REL / "pack5200_corrie_f_rev3" / "manufacturing"
CROWN = json.loads((HERE / "analysis" / "h1_crown.json").read_text())


def _reg():
    import physical_test_kit as K
    return {r["id"]: r for r in csv.DictReader(open(K.REGISTER, encoding="utf-8"))}


# ------------------------------------------------------------------------------------------- 3. minimum belly
def test_belly_minimum_is_the_orchestrator_call_and_covers_us1():
    assert F.BELLY_MIN_MM == 60.0 and F.BELLY_GAUGE_MM == F.BELLY_MIN_MM
    bs = CROWN["belly_sweep"]
    # at the minimum the US1 root meets the fatigue requirement (>= 1.0), at 50 mm it does not
    assert bs["60"]["us1"]["fatigue"] >= 1.0 > bs["50"]["us1"]["fatigue"]
    # and the US2 tension at 60 mm stays under the 50 mm row the lug was checked at
    assert bs["60"]["us2"]["tension_n"] < bs["50"]["us2"]["tension_n"]


def test_gauge_tacks_drawn_on_both_us_straps_60mm_apart():
    import patterns_corrie_f_rev3 as P
    rs = P.build("today")
    for pid, n in (("US", "us1"), ("US2", "us2")):
        tk = [ln for ln in rs.pieces[pid].internal_lines if (ln.label or "").startswith("belly gauge tack")]
        assert len(tk) == 2
        ys = sorted(ln.points[0][1] for ln in tk)
        assert ys[1] - ys[0] == pytest.approx(F.BELLY_GAUGE_MM)
        assert F.US_CUT_MM[n] - ys[1] == pytest.approx(F.BELLY_GAUGE_TIP_MM)        # from the sealed tail tip
        for ln in tk:                                                          # a 10 mm tack across the centre
            (x0, _), (x1, _) = ln.points
            assert x1 - x0 == pytest.approx(P.BELLY_TACK_MM) and (x0 + x1) / 2 == pytest.approx(12.5)
        # the tacks sit on the tail, clear of the eye box and neck at the other end
        assert ys[0] > 2 * P.US_EYE + 50.0


def test_gauge_op_books_its_thread():
    import build_effort_rev3 as B
    import mfg_corrie_f_rev3 as M
    ops = M.ops(M.build_ctx())
    g = [o for o in ops if o.operation.startswith("US / US2 belly gauge tacks")]
    assert len(g) == 1 and g[0].stitch_type == "304" and "CONTRAST" in g[0].notes
    assert g[0].length_mm == pytest.approx(4 * M.bt_path_mm("BT-S"), abs=0.1)
    assert M.bt_path_mm("BT-S") > M.BARTACK_STD["BT-S"]["len_mm"]
    # the cached thread roll-up (read by the ledger) carries the op: mass flows into corrie_f.parts
    cache = json.loads(B.CACHE.read_text())
    row = [r for r in cache["ops"] if r["op"].startswith("US / US2 belly gauge tacks")]
    assert len(row) == 1 and row[0]["cfg"] == "base"
    want = g[0].length_mm / 1000.0 * M.THREAD_FACTOR * float(M.mat("bonded_nylon_tex90").require("mass_g_m"))
    assert row[0]["thread_g"] == pytest.approx(want, abs=1e-3) and 0.03 < want < 0.1


def test_card_and_records_carry_the_belly_rule():
    import mfg_corrie_f_rev3 as M
    card = [t for t in M.PACKAGING if "meat-haul rule" in t]
    assert len(card) == 1 and "NEVER flatter than the 60 mm" in card[0] and "contrast" in card[0]
    names = {a[0] for a in M.ASSUMPTIONS}
    assert {"BELLY-MIN", "BELLY-GAUGE", "CLEVIS-FACE"} <= names
    bm = next(a for a in M.ASSUMPTIONS if a[0] == "BELLY-MIN")
    assert f"{CROWN['belly_sweep']['60']['us1']['fatigue']:.2f} at 60 mm" in bm[1] and "MT-1cr" in bm[2]
    pk = (MFG / "README.md").read_text()
    assert "## Packaging" in pk and "NEVER flatter than the 60 mm" in pk.split("## Packaging")[1]
    dr = list(csv.DictReader(open(MFG / "delta_register_rev3.csv", encoding="utf-8")))
    rd22 = next(r for r in dr if r["id"] == "RD-22")
    assert "60 mm minimum cradle belly" in rd22["evidence"]


# ------------------------------------------------------------------------------------------- 2. kit text
def test_t1_carries_both_root_gauges_and_stays_idempotent():
    import physical_test_kit as K
    t1 = _reg()["T1"]
    assert t1["steps"].startswith(K.T1_STEPS) and t1["steps"].count("STRAIN GAUGES") == 1
    assert "US1 and US2 arm roots" in t1["steps"] and "0 / 150 / 300 lb" in t1["steps"]
    assert "3.86 GPa" in t1["steps"]                    # = record pa12_cf_fdm_paht youngs_modulus_xy_mpa
    assert t1["pass_fail"].startswith(K.T1_PASS) and "US1-STUB-GOVERNS" in t1["pass_fail"]
    # a second patch gives the same text (no double append)
    assert K.t1_patch()["steps"] == t1["steps"]


def test_mt1_cradle_pull_row_gauges_and_belly():
    import physical_test_kit as K
    from huntkit.gendesign import h1_lanes as LN
    r = _reg()["MT-1cr"]
    assert r["status"] == "ACTIVE" and r["tier"] == "safety"
    assert K.TEST_RELEASE["MT-1cr"] == "R1" and K.group_of("MT-1cr") == "G6"
    assert "240 / 480 / 720 N" in r["title"] and round(LN.US_CRADLE_N) == 720
    assert "arm roots" in r["specimen"] and "belly" in r["steps"] and ">= 60 mm (6 of 6)" in r["pass_fail"]
    assert "MT-1cr" in _reg()["MT-1"]["notes"]           # the bench MT-1 points at the frame-side pull
    res = list(csv.DictReader(open(REL / "test_kit" / "results_template.csv", encoding="utf-8")))
    bel = [x for x in res if x["test_id"] == "MT-1cr" and "belly" in x["quantity"]]
    assert len(bel) == 6 and all(x["limit"] == "60" and x["check"] == "min" for x in bel)
    assert any(x["test_id"] == "MT-1cr" and "US1-STUB-GOVERNS" in x["settles"] for x in res)
    assert sum(1 for x in res if x["test_id"] == "T1" and "arm-root strain" in x["quantity"]) == 6


def test_clevis_share_gauge_required_and_bl051_hardware():
    from huntkit.gendesign import h1_bedfit as BF
    r = _reg()["CLEVIS-SHARE"]
    assert "optional strain gauge" not in r["steps"] and "STRAIN GAUGE (required, BL-052)" in r["steps"]
    assert "US2 arm root" in r["specimen"] and "REQUIRED" in r["specimen"]
    assert f"M5 x {BF.JOINT.bolt_len:.0f}" in r["specimen"] and "NO washer under the head" in r["specimen"]
    assert "2 x 10 mm OD DIN 433 washers on the NUT side only" in r["specimen"]
    # the joint numbers quoted are BL-051's (counterbored heads), not BL-050's 3.85 / 1.73
    j = CROWN["joint"]
    assert f"strength {j['worst_strength']['sf']}, fatigue {j['worst_fatigue']['fatigue']}" in r["what_it_proves"]
    assert "3.85" not in r["what_it_proves"] and "HEAD-BEAR" in r["pass_fail"] + r["steps"] + r["what_it_proves"]
    res = list(csv.DictReader(open(REL / "test_kit" / "results_template.csv", encoding="utf-8")))
    assert any(x["test_id"] == "CLEVIS-SHARE" and "HEAD-BEAR" in x["settles"] for x in res)
    assert sum(1 for x in res if x["test_id"] == "CLEVIS-SHARE" and "strain" in x["quantity"]) == 3


def test_kit_shopping_has_gauges_and_the_right_washer_count():
    import physical_test_kit as K
    from huntkit.gendesign import h1_bedfit as BF
    sh = K.shopping({})
    w = next(x for x in sh if x["item"].startswith("US2 CLEVIS ONLY: M5 washer 10 mm"))
    assert int(float(w["qty"])) == 2 * 2 * BF.JOINT.n_washers + 2 == 6
    assert any("strain gauges" in x["item"] for x in sh)
    assert any("half-bridge" in x["item"] for x in sh)          # BL-054 (review 5 m-8): dummy-gauge compensation


# ------------------------------------------------------------------------------------------- 4. clevis face
def test_clevis_face_inspection_after_fit_us_and_t9():
    import physical_test_kit as K
    assert K.clevis_face_z() == (127, 157)                 # US2 pin z 142 +/- the 14.5 mm joint block
    fu = _reg()["FIT-US"]
    st = fu["steps"]
    assert "(7) CLEVIS-FACE INSPECTION" in st and "after step 4 and again after the T9" in st
    assert "z 127-157" in st and "loupe" in st and "CLEVIS-FACE" in fu["pass_fail"]
    res = list(csv.DictReader(open(REL / "test_kit" / "results_template.csv", encoding="utf-8")))
    face = [x for x in res if x["test_id"] == "FIT-US" and x["settles"] == "CLEVIS-FACE"]
    assert len(face) == 2
    rt = list(csv.DictReader(open(MFG / "release_tests.csv", encoding="utf-8")))
    assert "CLEVIS-FACE INSPECTION" in next(x for x in rt if x["id"] == "FIT-US")["steps"]
