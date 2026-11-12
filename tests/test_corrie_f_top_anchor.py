"""BL-029 CORRIE F top anchor and lid: the B-29 crown lid geometry and mass, rev 3's ledger rows, the crown-strap
routing, and the stored fine-mesh results (15 in meat CG, R-28, lifter gaps).

    python -m pytest -q tests/test_corrie_f_top_anchor.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(CONCEPTS / "corrie_f_sim")):
    if p not in sys.path:
        sys.path.insert(0, p)

import corrie_f as F  # noqa: E402

RESULTS = CONCEPTS / "corrie_f_sim" / "corrie_f_sim_results.json"


def _rows():
    return json.loads(RESULTS.read_text())["rows"]


# ------------------------------------------------------------------------------------------- lid geometry and mass
def test_lid_volume_lies_between_the_wall_box_and_the_full_height_box():
    g = F.lid_geometry()
    a = g["plan_area_mm2"]
    lo = a * F.LID["wall"] / 1e6
    hi = a * (F.LID["wall"] + F.LID["dome"]) / 1e6
    assert lo < g["volume_L"] < hi
    # dome of sqrt(1 - r^4) over a superellipse-4 plan: the mean dome rise is well over half the crown height
    assert (g["volume_L"] - lo) / (hi - lo) > 0.6
    assert g["volume_L"] == pytest.approx(4.98, abs=0.05)
    assert abs(g["volume_cu_in"] - g["volume_L"] * 61.0237) < 1.0


def test_lid_plan_fits_the_bag_top_and_the_superellipse_area_is_right():
    g = F.lid_geometry()
    c = F.make()
    assert g["plan_W_mm"] <= 2 * float(c.a([c.z_c])[0])          # never wider than the collar seam (360 mm)
    # area of |2x/W|^4 + |2y/D|^4 <= 1 is W D Gamma(1 + 1/4)^2 / Gamma(1 + 1/2)
    from math import gamma
    exact = F.LID["W"] * F.LID["D"] * gamma(1.25) ** 2 / gamma(1.5)
    assert g["plan_area_mm2"] == pytest.approx(exact, rel=0.01)
    assert g["perimeter_mm"] > 2 * (F.LID["W"] + F.LID["D"]) * 0.85
    assert g["channel_run_mm"] > F.LID["D"]                      # the channel runs over the dome, longer than the plan


def test_lid_mass_is_records_times_area():
    d = F.crown_lid()
    g = F.lid_geometry()
    per, SA = g["perimeter_mm"], F.SA_BODY
    crown = (g["crown_area_mm2"] + per * SA) * F._gsm(F.UG) / 1e6
    base = (g["plan_area_mm2"] + per * SA) * F._gsm(F.R70) / 1e6
    assert d["fabric_g"] > crown + base                           # plus wall, caps and channels
    zip_g = F._rec("coil_zipper_5", "mass_g_m") * (F.LID["zip_mm"] + 60) / 1000 + F.LID_SLIDER5_G + F.CORD_PULL_G
    assert d["zip_g"] == pytest.approx(zip_g, abs=0.1)
    assert d["mass_g"] == pytest.approx(d["fabric_g"] * (1 + F.LID_THREAD) + d["zip_g"], abs=0.15)
    assert 30.0 < d["mass_g"] < 80.0
    assert F.crown_lid("today")["mass_g"] > d["mass_g"]          # today's fabrics are heavier


# ------------------------------------------------------------------------------------------- rev 3 rows
def _by_name(rows):
    return {r["name"]: r for r in rows}


def test_rev3_swaps_the_pouch_for_the_lid_and_keeps_base_as_rev2():
    if not F.CROWN_PATHS.exists():
        pytest.skip("corrie_f_crown_paths.json missing: run corrie_f.py --bl029")
    with F.revision(2):
        r2 = F.parts()
    with F.revision(3):
        r3 = F.parts()
        assert F.REVISION == 3
    assert F.REVISION == 3                                        # BL-030: rev 3 is the module default
    n2, n3 = _by_name(r2), _by_name(r3)
    assert any("top_pouch" in n for n in n2) and not any("top_pouch" in n for n in n3)
    lid = [r for n, r in n3.items() if "crown_lid" in n]
    cs = [r for n, r in n3.items() if "crown_straps" in n]
    assert len(lid) == 1 and len(cs) == 1
    assert lid[0]["system"] == "pouch" and lid[0]["cfg"] == "as_hunted"
    assert cs[0]["system"] == "straps_compression" and cs[0]["cfg"] == "as_hunted"
    base2 = sum(r["g"] for r in r2 if r["cfg"] == "base")
    base3 = sum(r["g"] for r in r3 if r["cfg"] == "base")
    assert base3 == pytest.approx(base2, abs=0.01)                # the lid and its straps are as-hunted only
    hunted = lambda rows: sum(r["g"] for r in rows if r["cfg"] in ("base", "as_hunted"))  # noqa: E731
    d = hunted(r3) - hunted(r2)
    pouch = sum(r["g"] for n, r in n2.items() if "top_pouch" in n)
    assert d == pytest.approx(lid[0]["g"] + cs[0]["g"] - pouch, abs=0.05)


def test_revs_0_to_2_are_unchanged_by_rev3():
    with F.revision(0):
        a0 = F.addons()
    with F.revision(2):
        a2 = F.addons()
    for a in (a0, a2):
        assert "top_pouch" in a and "crown_lid" not in a


def test_crown_strap_cut_covers_the_longest_path_plus_the_lid():
    if not F.CROWN_PATHS.exists():
        pytest.skip("corrie_f_crown_paths.json missing")
    L = F.crown_strap_length()
    gp = json.loads(F.CROWN_PATHS.read_text())["rows"]
    longest = max(max(r["R"]["length_mm"], r["L"]["length_mm"]) for r in gp.values())
    assert L["path_mm"] == pytest.approx(longest, abs=0.1)
    assert L["cut_mm"] >= longest + 2 * (F.LID["wall"] + F.LID["dome"]) + F.CROWN_TAIL


# ------------------------------------------------------------------------------------------- routing
def test_vias_are_given_bag_end_first():
    assert F._vias_head_first([1, 2, 3]) == [3, 2, 1]


def test_over_route_is_registered_and_cinched():
    for k in ("over", "over_port", "wrapfix"):
        assert k in F.ROUTES
    assert F.CROWN_PRE_N == 80.0 and F.CROWN_X == F.REVS[1]["guy_x"]


# ------------------------------------------------------------------------------------------- stored results
def _need(*keys):
    rows = _rows()
    miss = [k for k in keys if k not in rows]
    if miss:
        pytest.skip(f"stored rows missing: {miss}")
    return rows


def test_crown_straps_alone_do_not_hold_the_15in_meat_load():
    rows = _need("F_PR15_fineFM_over")
    m = rows["F_PR15_fineFM_over"]["cases"]["meat"]
    assert m["converged"]
    assert m["cg_y"] > 190.0                                      # over rev C: an outside strap from the low S bar
    assert rows["F_PR15_fineFM_over"]["route"]["name"] == "over"


def test_rev3_meets_bl029_acceptance_on_the_fine_mesh():
    rows = _need(*(f"F_PR{t}_fineFM_over_port" for t in (15, 19, 23)))
    t = F.bl029_table()
    a = t["acceptance"]
    assert a["cg15_meat_mm"] <= F.CG_TARGET                        # 185 mm (rev C 190)
    assert a["r28_ok"] and min(a["r28_deg"]) >= 31.0
    assert a["rev_c_ok"]
    for tt in (15, 19, 23):
        for cn in ("fill", "meat"):
            assert rows[f"F_PR{tt}_fineFM_over_port"]["cases"][cn]["converged"]
    if F.CROWN_PATHS.exists():
        assert a["lifter_ok"] and a["lifter_gap_min_mm"] >= F.MIN_CLEAR_MM


def test_wrap_route_check_run_is_worse_than_the_stored_bar_first_run():
    rows = _need("F_PR15_fineFM_wrap", "F_PR15_fineFM_wrapfix")
    a = rows["F_PR15_fineFM_wrap"]["cases"]["meat"]["cg_y"]
    b = rows["F_PR15_fineFM_wrapfix"]["cases"]["meat"]["cg_y"]
    assert b > 190.0 and a > 190.0                                 # rev 1's real path fails rev C either way


# ------------------------------------------------------------------------------------------- render mesh
def test_render_lid_mesh_is_closed_and_holds_the_design_volume_on_a_flat_seat():
    import trimesh
    import corrie_f_rev3_viz3d as R3
    seat = lambda x, y: np.zeros_like(np.asarray(x, float))      # noqa: E731
    V, Fc, fr, ft, info = R3.lid_mesh(seat, 0.0, 0.0)
    m = trimesh.Trimesh(V, Fc, process=True)
    assert m.is_watertight
    vol = abs(m.volume) / 1e6
    # the render's base sits 1.5 mm up and the top edge is rounded (10 mm): a little under the design volume
    assert 0.85 * F.lid_geometry()["volume_L"] < vol < 1.01 * F.lid_geometry()["volume_L"]
