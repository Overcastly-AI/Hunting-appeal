"""BL-033: rev 3 pattern fixes on the pack-designer side (designs/pack_5200/concepts/corrie_f.py)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "designs" / "pack_5200", ROOT / "designs" / "pack_5200" / "concepts",
          ROOT / "designs" / "pack_5200" / "bag_comp"):
    sys.path.insert(0, str(p))

import corrie_f as F  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    with F.revision(3):
        return F.parts("M", "D2")


def test_hinge_window_gone_and_b18_whole():
    hs = F.hinge_standoff()
    assert "hinge" not in F.SWELL_WINDOWS and set(F.SWELL_WINDOWS) == {"im1", "im2", "im3"}
    assert hs["overlap_z_mm"] == pytest.approx(40.0)              # what BL-032 had: window z 40-130 over B-18 z 35-80
    assert hs["b18_window_overlap_mm2"] == 0.0
    assert hs["nearest_window_above_b18_mm"] > 50.0
    # BL-044: the BL-042 hinge fairlead (cheek tips 17.7 mm proud, bag_attach.HINGE_EYE_ENVELOPE) lifts B-01 7.05 mm,
    # double the US2 cleat (legacy 14.1 mm proud), still under the 16 mm swell the IM fairleads are given
    from huntkit.gendesign import bag_attach as BA
    env = BA.HINGE_EYE_ENVELOPE
    assert hs["hinge"]["top_mm"] == pytest.approx(env["stay_r_mm_at_z60"] + env["cheek_tip_above_stay_surface_mm"], abs=0.01)
    assert hs["hinge"]["push_mm"] == pytest.approx(hs["hinge"]["top_mm"] - BA.PANEL_OFFSET, abs=0.01)
    assert 5.0 < hs["hinge"]["push_mm"] < BA.SWELL
    assert 0.0 < hs["us2"]["push_mm"] < 5.0


def test_b01_booked_net_of_its_windows(rows):
    nb = F.b01_net_g()
    assert nb["windows"] == 6
    assert nb["window_mm2"] == pytest.approx(6 * F.SWELL_W * 90.0, rel=0.01)
    r = [x for x in rows if x["name"].startswith("B-01 ")]
    assert len(r) == 1 and r[0]["g"] == pytest.approx(nb["net_g"], abs=0.01) and r[0]["g"] < nb["full_g"]


def test_swell_patch_double_booking_removed_and_h1_booked(rows):
    names = [r["name"] for r in rows]
    assert "attachment: B-01 swell patches" not in names
    b13 = next(r for r in rows if r["name"].startswith("B-13x boxed fairlead swell"))
    h1 = next(r for r in rows if r["name"].startswith("BL-033 H-1"))
    assert h1["g"] == pytest.approx(-2 * b13["g"] / 8.0, abs=0.01)


def test_b27_slit_on_the_fabric():
    p = F.guy_port()
    s01 = F.b01_flat_s()
    assert p["slit_mm"] == pytest.approx(s01(745.0) - s01(595.0), abs=0.05)
    assert p["slit_mm"] == pytest.approx(156.2, abs=0.05) and p["slit_dz_mm"] == 150.0


def test_build_has_no_self_paired_seams_and_d2_seams_match():
    with F.revision(3):
        b = F.build(F.make(), "D2", "B")
    for s, _ in b.seams:
        a, c = s.a, s.b
        assert not (len(a) == 1 and len(c) == 1 and a[0].piece is c[0].piece and a[0].name == c[0].name), s.name
    rep = check_seams([s for s, _ in b.seams], tol_mm=1.0)
    assert not rep.mismatches
    names = {s.name for s, _ in b.seams}
    for n in ("door | blade U (#10 zip, R 55 corners)", "hinge band R | blade U", "hinge band L | blade U"):
        assert n in names
    zip_seam = next(s for s, _ in b.seams if s.name.startswith("door | blade U"))
    assert zip_seam.length_a == pytest.approx(b.extra["zip_door_mm"], abs=0.5)


def test_lid_hours_are_the_drafted_hours():
    with F.revision(3):
        lid = F.crown_lid()
        ad = F.addons()
    assert lid["hours"] == pytest.approx(9.53, abs=0.01)           # pattern_checks.md section 4 (drafted B-29)
    assert lid["hours_bl029"] == pytest.approx(7.76, abs=0.01)
    assert ad["crown_lid"]["hours"] == lid["hours"]
    assert F.lid_seam_list()["bl029_estimate_h"] == lid["hours_bl029"]


def test_fp_face_165_keeps_its_capacity():
    fp = F.fp_spec()
    assert fp["w"] == 165.0 and fp["pleat"] == pytest.approx(95.0)
    assert fp["cap_L"] == 2.0 and fp["cap_ratio"] == 1.0
    # the arc model: same mesh over a narrower face is deeper; pleats unchanged would lose capacity
    assert F._mesh_arc_area(165.0, 245.0) < F._mesh_arc_area(180.0, 260.0) < F._mesh_arc_area(165.0, 260.0)
    with F.revision(3):
        fpr = [d for d in F.hip_reach_pockets() if d["id"] == "FP-L/R"][0]
    assert "260 x 230 (165 mm face)" in fpr["name"]


def test_hip_reach_access_zero_hourly_misses():
    import corrie_f_loadout as FL
    with F.revision(3):
        res = FL.run("D2", sizes=("M",))
    m = res["misses"]["M"]
    assert all(m[k]["hourly"] == [] for k in m)
    assert "bottle_1L#2" not in m["sheep8"]["all"]


def test_us_channels_have_geometry(rows):
    uc = F.us_channels()
    assert uc["width_mm"] == pytest.approx(37.0) and uc["piece"].quantity == 1          # BL-050 B: B-16 + B-16b
    assert sum(p.quantity for p in uc["pieces"].values()) == 2
    assert all(0 < s < uc["floor_depth_mm"] for s in uc["stations_mm"])
    r = next(x for x in rows if x["name"].startswith("US-chan:"))
    assert r["g"] == pytest.approx(uc["mass_g"], abs=0.01)


def test_rain_fly_seams_match_and_it_is_booked(rows):
    with F.revision(3):
        fp = F.fly_pieces()
    rep = check_seams(fp["seams"], tol_mm=0.5)
    assert not rep.mismatches
    sp, sd = fp["pieces"]
    assert sd.quantity == 2
    # the spine is as wide as the eased bag at the floor and the eased lid over the top
    x0, _, x1, _ = sp.bounds(cut=False)
    assert x1 - x0 == pytest.approx(2 * F.FLY_EASE * 196.8, abs=1.0)
    f01 = next(r for r in rows if r["name"].startswith("F-01 rain fly"))
    assert f01["g"] == pytest.approx(fp["mass_g"], abs=0.01) and f01["cfg"] == "as_hunted"
    hem = next(r for r in rows if r["name"].startswith("rain fly: fly elastic hem"))
    assert hem["cfg"] == "as_hunted" and 2.0 < fp["elastic_m"] < 3.0


def test_b22_moved_tab_passes_bl033_acceptance():
    p = F.b22_placement()
    assert p["x_mm"] == pytest.approx(130.3, abs=0.05) and not p["fits_at_want"]
    r = json.loads(F.B22_CHECK.read_text())          # written by bl033_b22_check from the fine run
    mv = r["runs"]["moved"]
    assert abs(mv["b22_node_x_mm"]["R"] - p["x_mm"]) <= 13.0     # nearest fine-mesh node on the tab's row
    assert mv["meat_cg_y_mm"] <= F.CG_TARGET and mv["meat_converged"]
    assert mv["lifter_gap_min_mm"] >= F.MIN_CLEAR_MM and mv["r28_deg"] >= 31.0
    assert r["pass"] and not r["use_fallback"]
