"""BL-055 Part A: H1 close-out (whole body on the BL-053 body, hip-boss inserts, Ti US1 pins, cleanup).

Closed-form checks of the new pieces (section properties, the sanding ratio, the prying model against
hipbelt_structural 4, the hull sign of us_route.section_bearing) plus the recorded results."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import h1_closeout as C

REPO = Path(__file__).resolve().parents[1]
RES_P = REPO / "designs" / "pack_5200" / "analysis" / "h1_closeout.json"
RES = json.loads(RES_P.read_text()) if RES_P.exists() else None
needs_res = pytest.mark.skipif(RES is None, reason="analysis/h1_closeout.json not written yet")


# ---------------------------------------------------------------------------------------------- section / sanding
def test_section_props_match_closed_form_rectangle_and_tube():
    from shapely.geometry import Point, box
    r = C._section_props(box(0.0, 0.0, 10.0, 18.0))
    assert r["A"] == pytest.approx(180.0)
    assert r["Ix"] == pytest.approx(10.0 * 18.0 ** 3 / 12.0)
    assert r["Iy"] == pytest.approx(18.0 * 10.0 ** 3 / 12.0)
    assert r["Zx_wearer"] == pytest.approx(10.0 * 18.0 ** 2 / 6.0)
    ring = Point(0, 0).buffer(9.0, 512).difference(Point(0, 0).buffer(6.0, 512))
    rr = C._section_props(ring)
    assert rr["Ix"] == pytest.approx(math.pi / 4 * (9.0 ** 4 - 6.0 ** 4), rel=2e-3)
    assert rr["A"] == pytest.approx(math.pi * (81.0 - 36.0), rel=1e-3)


def test_sanding_rectangle_reproduces_the_bl053_estimate():
    """0.2 mm off one face of an 18 mm deep rectangle: Z0 / Z at the far fibre = (18 / 17.8)^2 (the BL-053 2.2 %)."""
    from shapely import affinity
    from shapely.geometry import box
    P = box(0.0, 0.0, 10.0, 18.0)
    Ps = P.intersection(affinity.translate(P, 0.0, 0.2))
    a, b = C._section_props(P), C._section_props(Ps)
    assert a["A"] / b["A"] == pytest.approx(18.0 / 17.8)
    assert a["Zx_bag"] / b["Zx_bag"] == pytest.approx((18.0 / 17.8) ** 2)
    assert 1 - (17.8 / 18.0) ** 2 == pytest.approx(0.0221, abs=1e-4)


@needs_res
def test_sand_factor_on_the_print_is_above_the_rectangle_estimate():
    sf = RES["body"]["sand_factor"]
    assert sf["sand_mm"] == 0.2
    assert 1.0 + sf["rect_equivalent_loss"] < sf["k"] < 1.06       # real sections (crown, sleeves) lose more than 2.2 %


# ---------------------------------------------------------------------------------------------- hip boss inserts
def test_prying_model_reproduces_hipbelt_structural():
    r = C.hip_record_check()
    assert r["H_pin"]["sf_record_cap"] == pytest.approx(0.995, abs=0.002)      # hipbelt_structural.md 4
    assert r["H_frame"]["sf_record_cap"] == pytest.approx(1.142, abs=0.002)
    # every tipping direction is worse than the record's single (downward) one for the 2-screw row
    assert r["H_pin"]["all_directions"]["T_max_n"] > r["H_pin"]["T_n"]


def test_tip_tension_closed_form_ring():
    """n equal screws on a ring r, boss radius R: sum d^2 = n R^2 + n r^2 / 2, worst d = R + r (a screw on the
    tipping direction)."""
    pat = C.hip_pattern(6, 16.0, 44.0, 0.0)
    t = C.tip_tension(pat, V=1000.0, H=0.0, e=0.0, stand=21.0, n_dir=360)
    R, r = 22.0, 16.0
    T = 21.0 * 1000.0 * (R + r) / (6 * R ** 2 + 6 * r ** 2 / 2)
    assert t["T_max_n"] == pytest.approx(T, rel=1e-3)


def test_insert_capacity_from_records():
    cap = C.hip_capacity(True)
    ir = C.insert_record()
    assert ir["pullout_n"] == 1200.0 and ir["hole_d"] == 6.4 and ir["min_wall"] == 2.6
    assert cap["static_n"] == pytest.approx(1200.0 * 0.8 * 47.0 / 88.0, abs=0.1)
    assert cap["fatigue_n"] == pytest.approx(cap["static_n"] * 0.3, abs=0.1)


def test_chosen_hip_pattern_meets_the_ticket():
    pat = C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)
    ch = C.hip_check(pat, True)
    assert pat["walls_ok"] and all(v >= 2.6 for k, v in pat["walls"].items() if k != "to_pin_bore_mm")
    assert ch["min_sf"]["strength"] >= 1.5 and ch["min_sf"]["fatigue"] >= 1.15 and ch["pass"]
    # one fewer insert does not pass on the same capacity: the count is the least that does
    n, r, D, rot = C.HIP_CHOSEN
    assert not C.hip_check(C.hip_pattern(n - 1, r, D, rot, depth=C.HIP_BOSS_DEPTH), True)["pass"]


@needs_res
def test_hip_pilots_on_the_exported_print():
    sl = RES["hip_slices"]
    assert sl["pass"]
    n = C.HIP_CHOSEN[0]
    for k, row in sl["rows"].items():
        if row["holes_d_eq"] and any(h is not None for h in row["holes_d_eq"]):
            assert all(abs(h - 6.4) < 0.25 for h in row["holes_d_eq"])
    assert all(v == n for v in sl["lower_flat_round_holes"].values())


# ---------------------------------------------------------------------------------------------- pins
def test_us1_pins_ti_and_rechecked():
    p = C.pins()
    u1 = p["stations"]["us1"]
    assert u1["material"] == "ti_6al_4v" and u1["was"]["material"] == "alu_7075_t6"
    assert u1["pin_g"] == pytest.approx(u1["was"]["pin_g"] * 4430.0 / 2810.0, abs=0.02)
    assert u1["bending"]["dy95_sf_fatigue"] >= 1.15 > u1["was"]["bending"]["dy95_sf_fatigue"]
    assert p["stations"]["hinge"]["material"] == "ti_6al_4v"
    assert all(p["stations"][n]["material"] == "alu_7075_t6" for n in ("us2", "im1", "im2", "im3"))
    assert p["mass"]["delta_vs_bl053_g"] == pytest.approx(2 * (u1["pin_g"] - u1["was"]["pin_g"]), abs=0.02)
    assert len(p["bom"]) == 6 and sum(r["qty"] for r in p["bom"]) == 12


# ---------------------------------------------------------------------------------------------- cleanup
def test_section_bearing_keeps_the_bag_side_hull():
    """A strap from a pin at z 100 to a corner at z 0 over one obstacle standing 5 mm proud at z 50 must turn on it."""
    pack = REPO / "designs" / "pack_5200"
    if str(pack) not in sys.path:
        sys.path.insert(0, str(pack))
    import us_route as U
    xs = np.arange(-20.0, 21.0, 1.0)
    ys = np.arange(-10.0, 20.0, 1.0)
    zs = np.arange(0.0, 101.0, 1.0)
    occ = np.zeros((len(xs), len(ys), len(zs)), np.uint8)
    iy = np.where(ys <= 10.0)[0]
    iz = np.where((zs >= 45) & (zs <= 55))[0]
    for k in iz:
        occ[:, iy, k] = 2                                   # 'hinge' label as the obstacle, up to y 10
    pin = {"y_pin": 5.0, "z": 100.0}
    r = U.section_bearing({"axes": (xs, ys, zs), "occ": occ}, 0.0, pin, (5.0, 0.0), T=100.0, own=3)
    assert r["turn_deg"] > 5.0 and r["bearing_n"].get("hinge", 0.0) > 10.0
    assert any(y >= 10.0 for y, z in r["hull"][1:-1])


def test_throat_is_the_printed_width():
    from huntkit.gendesign import bag_attach as BA
    assert BA.THROAT == 20.0 == BA.HINGE_GEOM.throat == BA.eye_geom("us1").throat == BA.eye_geom("im3").throat
    assert BA.THROAT_LEGACY == 18.0 == BA.legacy_geom().throat == BA.FairleadGeom().throat
    assert "pin sleeve" not in BA.PIN_WRAP["us1"]["wraps"]


def test_superseded_notes():
    an = REPO / "designs" / "pack_5200" / "analysis"
    for f in ("h1_crown.md", "h1_bedfit.md", "h1_lanes.md"):
        head = "\n".join((an / f).read_text().split("\n")[:4])
        assert "SUPERSEDED (2026-11-14, BL-055)" in head and "h1_rev5.md" in head


# ---------------------------------------------------------------------------------------------- whole body, mass
@needs_res
def test_whole_body_on_the_bl053_body():
    b = RES["body"]["bases"]
    assert set(b) == {"fine_sm8", "fine", "beam", "fine_sm8.cyc"}
    for k, v in b.items():
        n, s = v["bl053"], v["bl053_sanded"]
        assert s["strength"] <= n["strength"] + 1e-6 and s["fatigue"] <= n["fatigue"] + 1e-6
        # the sanded run divides stay stresses by k: no margin can drop by more than k
        assert s["fatigue"] >= n["fatigue"] / RES["body"]["sand_factor"]["k"] - 1e-3
    assert RES["body"]["raster_g"]["bl053"] > RES["body"]["raster_g"]["bl051"]


@needs_res
def test_ledger_books_bl055():
    from huntkit.mass import ledger as L
    m = RES["mass"]
    rows = L.corrections("corrie_b2_h1", "M")["BL055"]
    assert sum(r["g"] for r in rows) == pytest.approx(m["print_delta_g"] + m["hardware_delta_g"]
                                                      + m["us1_ti_pins_delta_g"], abs=0.05)
    assert L.corrections("corrie_b2_today", "M")["BL055"] == []
    assert m["hardware_delta_g"] == pytest.approx((C.HIP_CHOSEN[0] - 2) * (1.5 + m["hip_screw_g"]), abs=0.05)
