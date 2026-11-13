"""BL-049: hinge fairlead for the sims' inboard-up pull, US stations on lane lugs (huntkit/gendesign/h1_lanes.py)."""
from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import bag_attach as BA
from huntkit.gendesign import h1_fairleads as HF
from huntkit.gendesign import h1_lanes as L

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "designs" / "pack_5200" / "analysis" / "h1_lanes.json"
PRINT = REPO / "designs" / "pack_5200" / "print" / "frame_h1" / "h1_assembled.stl"


# ---------------------------------------------------------------------------------------------------- geometry
def test_hinge_geometry_bl049():
    g, g0 = BA.HINGE_GEOM, BA.HINGE_GEOM_BL042
    assert g.hole_proud == pytest.approx(g0.hole_proud)            # the pin does not move
    assert g.throat == g0.throat == 20.0
    assert g.half_z == g0.half_z == 9.0                            # the HE box side is untouched
    assert g.z_top == 27.0 and g.cheek == 10.0
    assert g.floor_proud == pytest.approx(g0.floor_proud - 1.0)
    assert g.gap_under_pin == pytest.approx(6.5)
    e = BA.HINGE_EYE_ENVELOPE
    assert e["gap_under_pin_mm"] == pytest.approx(6.5) and e["cheek_up_mm"] == 27.0 and e["cheek_half_z_mm"] == 9.0
    assert e["gap_clearance_over_eye_mm"] == pytest.approx(2.0)
    # the IM / US stations keep BL-045's section (only the hinge changed)
    for n in BA.IMUS_STATIONS:
        ge = BA.eye_geom(n)
        assert ge.floor_proud == pytest.approx(g0.floor_proud) and ge.cheek == 8.0 and ge.half_z_up is None


def test_asymmetric_cheek_field():
    """fairlead_local: material 27 mm above the pin axis on the cheek, none at 28; 9 below, none at 10."""
    g, r = BA.HINGE_GEOM, 9.3545
    x = g.throat / 2 + g.cheek / 2
    y = r + g.tip_proud - 1.0
    f = BA.fairlead_local(np.array([[x, y, 26.5], [x, y, 28.0], [x, y, -8.5], [x, y, -10.0]]), r, g)
    assert f[0] < 0 and f[1] > 0 and f[2] < 0 and f[3] > 0
    assert g.z_mid == pytest.approx(9.0) and g.z_half_span == pytest.approx(18.0)


def test_placed_lanes():
    P = {p["id"]: p for p in HF.placed()}
    assert P["us1_R"]["x"] == L.US1_X and P["us1_L"]["x"] == -L.US1_X and P["us1_R"]["lane"]
    assert P["us2_R"]["x"] == L.US2_X and P["us2_L"]["x"] == -L.US2_X
    assert P["hinge_R"]["x"] == 115.0 and not P["hinge_R"]["lane"]
    old = {p["id"]: p for p in HF.placed(lanes=False)}
    assert old["us1_R"]["x"] == 115.0
    # the eye envelope heights do not move with the lane
    for k in ("y_pin", "y_floor", "y_tip"):
        assert P["us2_R"][k] == pytest.approx(old["us2_R"][k])


def test_published_match_us_route():
    sm = json.loads((REPO / "designs/pack_5200/analysis/us_route.json").read_text())["station_move"]
    assert sm["us1"]["x"] == L.US1_X and sm["us1"]["z"] == L.US1_Z
    assert sm["us2"]["x"] == L.US2_X and sm["us2"]["z"] == L.US2_Z


def test_arm_taper_and_clearances():
    P = {p["id"]: p for p in HF.placed()}
    for n in ("us1", "us2"):
        p = P[f"{n}_R"]
        s = L.arm_sections(p)
        # root at the stay, tip at the fairlead's inner cheek face
        assert min(s["root"]["x"]) == pytest.approx(min(115.0, 115.0 + np.sign(p["x"] - 115) * p["stay_r"]))
        assert s["tip"]["y"][1] == pytest.approx(p["y_floor"])
        assert s["root"]["y"][1] < p["yc"] + p["stay_r"]          # never proud of the stay's bag face at the root
        pts = np.array([[0.5 * sum(s["tip"]["x"]), 0.5 * sum(s["tip"]["y"]), p["z"]],
                        [p["x"], p["y_floor"] + 2.0, p["z"]]])
        assert list(L.in_arm(pts, p)) == [True, False]
    # US1 clears the hinge cheek top and the spreader sheet's bottom edge (z 112) by >= 3 / 6 mm
    b1 = L.arm_box(P["us1_R"])
    assert b1["z"][0] - (60.0 + BA.HINGE_GEOM.z_top) >= 3.0 and 112.0 - b1["z"][1] >= 6.0


# ---------------------------------------------------------------------------------------------------- loads / FE
def test_lane_items_moment():
    F = np.array([0.0, 30.0, -50.0])
    items = [(np.array([115.0, -1.7, 90.0]), np.r_[F, 0, 0, 0], "bag"),
             (np.array([-115.0, -2.5, 130.0]), np.r_[F, 0, 0, 0], "bag"),
             (np.array([115.0, -1.1, 60.0]), np.r_[F, 0, 0, 0], "bag")]
    out, n = L.lane_items(items)
    assert n == 2
    dx1 = 70.0 - 115.0
    assert np.allclose(out[0][1][3:], np.cross([dx1, 0, 0], F))
    dx2 = -165.0 + 115.0
    assert np.allclose(out[1][1][3:], np.cross([dx2, 0, 0], F))
    assert np.allclose(out[2][1], items[2][1])                   # the hinge node is not a US pin
    assert np.allclose(out[0][1][:3], F)                          # the force itself is unchanged


def test_cradle_sets_balanced_per_pin():
    from huntkit.gendesign import meat_haul as MH
    sets = L.cradle_sets()
    assert len(sets) == 2
    s = sets[0]
    assert s.factor == 2.4 and len(s.items) == 4 + 10                 # 4 pins + the meat face on 5 nodes a side
    th = MH._theta()
    for p, v, side in s.items[:4]:
        assert np.linalg.norm(v[:3]) * s.factor == pytest.approx(L.US_CRADLE_N)
        assert math.degrees(math.atan2(-v[2], v[1])) == pytest.approx(math.degrees(th), abs=1e-6)
        assert np.linalg.norm(v[3:]) > 0                               # the lane moment rides along
    # the straps' aft pull is reacted by the meat on the frame face: no net fore-aft force left for the hip pivot
    assert sum(float(v[1]) for _, v, _ in s.items) == pytest.approx(0.0, abs=1e-6)
    assert sum(float(v[2]) for _, v, _ in s.items) < 0.0              # the weight goes to the hip pivot


def test_lug_fea_reproduces_fairlead_fea():
    """xoff 0, no arm: lug_fea is h1_fairleads.fairlead_fea (same mesh, loads, FI99 over the yoke)."""
    loads = {"a": [0.0, 300.0, -500.0], "b": [-400.0, 50.0, 200.0]}
    g, r = BA.HINGE_GEOM_BL042, 9.3545
    a = L.lug_fea(g, r, 0.0, None, loads, h=1.0)
    b = HF.fairlead_fea(g, r, loads, h=1.0)
    for k in loads:
        assert a["loads"][k]["fi99"] == pytest.approx(b["loads"][k]["fi99"], rel=1e-6)


def test_fe_linear_in_load():
    g, r = BA.HINGE_GEOM, 9.3545
    a = L.lug_fea(g, r, 0.0, None, {"x1": [0.0, 0.0, -500.0], "x2": [0.0, 0.0, -1000.0]}, h=1.5)
    assert a["loads"]["x2"]["fi99"] == pytest.approx(2 * a["loads"]["x1"]["fi99"], rel=1e-6)


def test_pin_check_closed_form():
    """Simply supported pin, load spread over the throat: M = F (2L - b) / 8, sigma = 32 M / (pi d^3)."""
    r = L.pin_check(1019.0, 20.0, 10.0, 5.0, "ti_6al_4v", 2.4)
    M = 1019.0 * (2 * 30.0 - 20.0) / 8.0
    assert r["M_nmm"] == pytest.approx(M)
    assert r["sigma_mpa"] == pytest.approx(32 * M / (math.pi * 125.0))
    assert r["sigma_walk_mpa"] == pytest.approx(r["sigma_mpa"] * 1.6 / 2.4)
    # matches h1_fairleads.pin_bending for the 7075 record
    a = L.pin_check(724.0, 20.0, 8.0, 5.0, "alu_7075_t6", 3.0)
    b = HF.pin_bending(724.0, 20.0, 8.0, 5.0, 3.0)
    assert a["sf_yield"] == pytest.approx(b["sf_yield"]) and a["sf_fatigue"] == pytest.approx(b["sf_fatigue"])


def test_hinge_pin_choice():
    p = L.hinge_pin()
    c = p[p["chosen"]]
    assert c["material"] == L.HINGE_PIN_MATERIAL and c["pin_d_mm"] == L.HINGE_PIN_D
    assert c["sf_yield"] >= 1.0 and c["sf_fatigue"] >= 1.15
    assert p["bl049|alu_7075_t6"]["sf_fatigue"] < 1.0           # why the pin changed


def test_bed_fit_box(tmp_path):
    import trimesh
    m = trimesh.creation.box(extents=(300.0, 200.0, 20.0))
    m.apply_translation(-m.bounds[0])
    m.export(tmp_path / "b.stl")
    r = L.bed_fit(tmp_path / "b.stl")
    assert r["fits"] and r["w_mm"] == pytest.approx(300.0, abs=0.5)
    m2 = trimesh.creation.box(extents=(400.0, 50.0, 20.0))
    m2.export(tmp_path / "c.stl")
    r2 = L.bed_fit(tmp_path / "c.stl")
    assert r2["fits"]                                             # on the diagonal
    m3 = trimesh.creation.box(extents=(400.0, 300.0, 20.0))
    m3.export(tmp_path / "d.stl")
    assert not L.bed_fit(tmp_path / "d.stl")["fits"]


# ---------------------------------------------------------------------------------------------------- results
@pytest.fixture(scope="module")
def res():
    if not RES.exists():
        pytest.skip("h1_lanes.json not written")
    return json.loads(RES.read_text())


def test_hinge_targets(res):
    h = res["hinge"]["study"]
    assert h["bl049"]["sim"]["fatigue"] >= L.FAT_GOAL
    assert h["bl049_h0.75"]["sim"]["fatigue"] >= L.FAT_GOAL
    assert h["bl049"]["sim"]["strength"] >= 1.0 and h["bl049"]["sim"]["creep"] >= 1.0
    assert h["bl049"]["revC"]["fatigue"] >= h["bl047_print"]["revC"]["fatigue"]       # rev C direction kept passing
    assert h["bl047_print"]["sim"]["fatigue"] < 1.0                 # the print before this ticket did not


def test_lug_results(res):
    for n in ("us1", "us2"):
        r = res["lugs"][n]
        assert r["worst_strength"]["sf"] >= 1.0
        for k, row in r["rows"].items():
            if k.startswith("bagon"):
                assert row["fatigue"] >= 1.0                       # bag-on passes everywhere
            assert row["regions"]["fairlead"]["fatigue"] >= L.FAT_GOAL


def test_print_checks(res):
    sc = res["slice_checks"]
    assert res["slice_checks"]["fairleads_pass"] and sc["channel"]["pass"] and sc["pawl"]["pass"]
    assert sc["fairleads"]["us1_R"]["x"] == pytest.approx(L.US1_X)
    assert sc["fairleads"]["hinge_R"]["gap_under_pin"] == pytest.approx(6.5, abs=0.3)
    ex = res["export"]
    assert ex["assembled"]["watertight"] and ex["lower"]["shells"] == 1 and ex["upper"]["shells"] == 1
    # the record states the bed fit as measured (the lower half with the US2 lugs does not fit the H2S)
    assert res["bed"]["upper"]["fits"]
    assert res["bed"]["lower"]["fits"] == (res["bed"]["lower"]["over_mm"] <= 0)


def test_mass_rows_add_up(res):
    m = res["mass"]
    assert m["lug_arms_g"] + m["print_rest_g"] == pytest.approx(m["delta_print_g"], abs=0.11)
    assert m["assembled_g"] - m["assembled_bl047_g"] == pytest.approx(m["delta_print_g"], abs=0.11)
    from huntkit.mass import ledger as LG
    rows = [r for r in LG.parts("corrie_b2_h1_v2", "M") if r.get("correction") == "BL049"]
    assert sum(r["g"] for r in rows) == pytest.approx(m["delta_print_g"] + m["hinge_pins_delta_g"], abs=0.11)


def test_us_route_rerun(res):
    lay = res["us_route"]["layouts"]
    assert lay["print_lanes"]["layout"]["us1"] == pytest.approx(L.US1_X)
    assert lay["print_lanes"]["pass"] == (min(lay["print_lanes"]["worst_clear_mm"].values()) >= 10.0)


@pytest.mark.skipif(not PRINT.exists(), reason="print STL not on disk")
def test_old_us_stubs_gone_on_the_stl():
    """Slice the print at the old US1 / US2 pin heights on the stay: nothing stands proud of the stay where the old
    fairleads were (the bag face above the stay is clear), and the lane fairlead is there instead."""
    import trimesh
    m = trimesh.load(PRINT)
    for n in ("us1", "us2"):
        p = next(q for q in HF.placed(lanes=False) if q["id"] == f"{n}_R")
        S = HF._zplane(m, p["z"])
        from shapely.geometry import box
        # BL-051: the stay's own crown is back over the old sites; 'proud' = above the plain stay crown (z 122) + 0.5
        crown = HF._zplane(m, 122.0).intersection(box(107.0, -20.0, 123.0, 20.0)).bounds[3]
        above = box(115.0 - 8.0, max(p["y_floor"] + 1.0, crown + 0.5), 115.0 + 8.0, p["y_tip"])
        assert S.intersection(above).area < 1.0
        lane = box(L.LANE_X[n] - 18.0, p["y_floor"] + 1.0, L.LANE_X[n] + 18.0, p["y_tip"])
        assert S.intersection(lane).area > 100.0
