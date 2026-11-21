"""BL-058 (review 6 M-1, M-2, M-3, M-5, m-2, m-3, m-8): nut traps, pin retainers, US2 pin-head counterbore, the
real-geometry runs, hip screws / holes / insert guide. Geometry checks slice the exported STLs; the heavy FEA results
are read from analysis/bl058.json (huntkit.gendesign.bl058_frame)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "designs" / "pack_5200"
sys.path.insert(0, str(PACK))

from huntkit.gendesign import bl058_frame as B  # noqa: E402
from huntkit.gendesign import h1_bedfit as BF  # noqa: E402

RES_P = B.RESULTS
needs_res = pytest.mark.skipif(not RES_P.exists(), reason="run python -m huntkit.gendesign.bl058_frame first")


@pytest.fixture(scope="module")
def asm():
    return B._mesh()


# ------------------------------------------------------------------------------------------- verification
def test_probe_against_a_drilled_block():
    """probe() on a 20 x 20 x 40 block with a D6 x 10 blind hole from one end: the void along the axis is [30, 40]
    exactly (closed form), and off the hole (r 4) there is none."""
    import trimesh
    import manifold3d as m3d
    from huntkit.gendesign.surface import _from_manifold
    blk = m3d.Manifold.cube((20.0, 20.0, 40.0)).translate((-10.0, -10.0, 0.0))
    hole = m3d.Manifold.cylinder(11.0, 3.0, 3.0, 96).translate((0.0, 0.0, 30.0))
    m = _from_manifold(blk - hole)
    assert isinstance(m, trimesh.Trimesh) and m.is_watertight
    v = B.voids(B.probe(m, (0.0, 0.0, -5.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), 0.0, 50.0), 0.0, 50.0)
    inner = [iv for iv in v if 0.0 < iv[0] < 45.0]
    assert inner and inner[0][0] == pytest.approx(35.0, abs=1e-6)        # t from p0 at z -5: z 30
    assert inner[0][1] == pytest.approx(50.0, abs=1e-6)                  # open end at z 40 and beyond (t 45..50)
    off = B.voids(B.probe(m, (4.0, 0.0, -5.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), 0.0, 50.0), 0.0, 50.0)
    assert [iv for iv in off if iv[0] > 1.0 and iv[1] < 44.0] == []


def test_pin_moment_closed_form_and_zero_at_the_groove(monkeypatch):
    """Uniform eye load over the neck, uniform cheek reactions: with equal 8 mm bearings and the eye centred the
    mid-span moment is F (2 L - n) / 8 (L = throat + cheek, n = neck), h1_lanes.pin_check's form; inboard of the inner
    bearing (the E-clip groove) M = 0 for any eye position; the end moment closes to zero (statics)."""
    p = B.stations_R()["us2"]
    g = p["geom"]
    monkeypatch.setattr(BF, "PIN_CBORE_DEPTH", 0.0)
    F = 1000.0
    pm = B.pin_moment(F, p, 0.0, neck=18.0)
    L = g.throat + g.cheek
    assert pm["share_outer"] == pytest.approx(0.5)
    assert np.max(np.abs(pm["M"])) == pytest.approx(F * (2 * L - 18.0) / 8.0, rel=2e-3)
    b = np.max(np.abs(pm["M"]))
    monkeypatch.undo()
    f = B.faces(p)
    for off in (-1.0, 0.0, 1.0):
        pm = B.pin_moment(F, p, off)
        assert np.max(np.abs(pm["M"][pm["x"] < f["far"] - 0.05])) < 1e-6 * F * L
        assert abs(pm["M"][-1]) < 2e-3 * F * L                       # closes outboard of the head seat
    a = np.max(np.abs(B.pin_moment(F, p, 0.0)["M"]))
    assert a <= b + 1e-9                                            # the counterbore moves the outer reaction inboard


# ------------------------------------------------------------------------------------------- M-1 nuts
def test_din934_seats_and_iso4032_does_not(asm):
    """Measured on the STL: the US2 hex pocket is 4.0 mm (washer slot 1.2), so a DIN 934 nut (m <= 4.0) seats with the
    M5 x 35 tip 1.0 mm through it, and ISO 4032 (m 4.4-4.7) does not; at z 234 ISO 4032 seats only below m 4.58."""
    r = B.nut_check(asm)
    us2 = [x for x in r["rows"] if x["joint"] == "US2 clevis"]
    z234 = [x for x in r["rows"] if x["joint"] == "z 234"]
    assert len(us2) == 4 and len(z234) == 4
    for x in us2:
        assert x["hex_pocket_mm"] == pytest.approx(BF.JOINT.nut_face - BF.JOINT.washer_t - 0.2 - BF.JOINT.trap_x0, abs=0.06)
        assert x["seat"]["DIN 934"]["at_m_max_mm"] > 0.1
        assert x["seat"]["ISO 4032"]["at_m_min_mm"] < 0.0
        assert x["seat"]["DIN 934"]["tip_past_nut_nominal_mm"] == pytest.approx(1.0, abs=0.06)
        assert x["head_face_abs_x"] == pytest.approx(BF.JOINT.head_face, abs=0.05)
    for x in z234:
        assert x["seat"]["DIN 934"]["at_m_max_mm"] > 0.5
        assert x["seat"]["ISO 4032"]["at_m_max_mm"] < 0.0 < x["seat"]["ISO 4032"]["at_m_min_mm"]
    assert r["DIN 934_seats_everywhere_at_m_max"] and not r["ISO 4032_seats_everywhere_at_m_min"]
    assert r["din934_tip_through_nut_everywhere"]


# ------------------------------------------------------------------------------------------- M-3 counterbore
def test_us2_pin_counterbore_on_the_stl(asm):
    """Both clevises: a probe parallel to the pin axis at r 4.0 (outside the 7.2 hole, inside the D9 counterbore) is
    open from the clevis face to |x| face - 2.0; the head (1.5) then sits 0.5 below the face."""
    for p in BF.us2_stations():
        s = p["sign"]
        v = B.voids(B.probe(asm, (s * 170.0, p["y_pin"], p["z"] + 4.0), (s, 0.0, 0.0), (0.0, 1.0, 0.0), 0.0, 25.0),
                    0.0, 25.0)
        cb = [iv for iv in v if iv[1] > 12.9]
        assert cb and 170.0 + cb[0][0] == pytest.approx(BF.JOINT.outer_face - BF.PIN_CBORE_DEPTH, abs=0.05)
        # r 5.0 is outside the counterbore: solid through the outer cheek up to the face
        w = B.voids(B.probe(asm, (s * 176.0, p["y_pin"], p["z"] + 5.0), (s, 0.0, 0.0), (0.0, 1.0, 0.0), 0.0, 6.9),
                    0.0, 6.9)
        assert w == []
    assert BF.PIN_CBORE_DEPTH - B.US2_HEAD_T == pytest.approx(BF.JOINT.head_recess - BF.JOINT.head_h)
    assert B.pin_row("us2")["head_mm"][1] == B.US2_HEAD_T and B.pin_row("hinge")["head_mm"][1] == B.HEAD_T


# ------------------------------------------------------------------------------------------- M-2 retainers
def test_retainers_per_station(asm):
    """Every station: the retainer, head and tether envelopes 0.5 mm clear of the print, >= 1 mm under the cheek-tip
    plane B-01 rests on; the US strap ribbons >= 10 mm off them; the hinge eye clear. US2 has no clip leg (E-clip)."""
    r = B.retainer_checks(asm)
    assert set(r["rows"]) == {"hinge", "us1", "us2", "im1", "im2", "im3"}
    for n, row in r["rows"].items():
        assert row["below_b01_plane_mm"] >= B.B01_RULE, n
        assert all(v < 0.05 for k, v in row.items() if k.endswith("mm3_at_0.5mm")), n
    assert r["rows"]["us2"]["retainer"] == "eclip" and r["rows"]["us2"]["fore_room_needed_mm"] < 8.0
    assert r["rows"]["us1"]["strap_mm"]["min_mm"] >= 10.0 and r["rows"]["us2"]["strap_mm"]["min_mm"] >= 10.0
    assert r["rows"]["hinge"]["he"]["min_mm"] >= 1.0
    assert r["pass"]


def test_pin_rows_lengths_and_cited_parts():
    """Shank = head seat to the far face + tail; hairpin tail 2.5 + 0.75 + 2; US2 tail past the groove and tether hole;
    every retainer names a part with a source URL."""
    for n in B.STATION_RET:
        r = B.pin_row(n)
        assert r["shank_mm"] == pytest.approx(r["head_seat_abs_x"] - r["far_face_abs_x"] + r["tail_past_far_face_mm"])
        assert "http" in r["retainer_source"]
    assert B.pin_row("hinge")["tail_past_far_face_mm"] == pytest.approx(2.5 + 0.65 + 2.0)       # BL-053's tail kept
    assert B.pin_row("hinge")["shank_mm"] == pytest.approx(45.15) and B.pin_row("us1")["shank_mm"] == pytest.approx(41.15)
    assert B.TAIL_HAIRPIN - B.CLIP_EDGE - B.CROSS_HOLE_D / 2 >= 1.5                              # end wall past the hole
    u = B.pin_row("us2")
    g = u["features"]["groove"]
    assert g["d_mm"] == 4.0 and g["from_far_cheek_face_mm"][0] > 0.0
    assert u["features"]["tether_hole"]["from_far_cheek_face_mm"] - 0.8 >= g["from_far_cheek_face_mm"][1] + B.GROOVE_LAND - 1e-9
    assert u["head_seat_abs_x"] == pytest.approx(BF.JOINT.outer_face - BF.PIN_CBORE_DEPTH)
    assert B.CROSS_HOLE_D == pytest.approx(1.5)
    assert B.cord_len("us2") >= B.tether_route("us2")["cord_needed_mm"] + 20.0


def test_us2_sleeve_and_thin_head():
    """BL-058 follow-up: 6.5 mm outer bearing keeps the sleeve SF >= 1 on every row (dy 95 / share 1.0 included) and
    the D8 x 1.0 head carries the PIN-RET / walk loads (shear, flange bending, pull-through) with SF >= 2."""
    sb = B.sleeve_bearing()
    assert sb["bearing_now_mm"] == pytest.approx(6.5) and sb["pass"] and sb["min_now"] >= 1.0
    assert sb["rows"]["dy95|share1|L6"]["sf_yield"] < 1.0                     # the first counterbore did not
    h = B.head_check()
    assert h["head_mm"] == [8.0, 1.0] and h["pass"]
    r = h["rows"]["alu_7075_t6|walk (0.2 x dy95)"]
    assert r["tau_mpa"] == pytest.approx(h["loads_n"]["walk (0.2 x dy95)"] / (math.pi * 5.0 * 1.0), abs=0.01)


def test_groove_has_no_bending():
    g = B.groove_check()
    for k, r in g["rows"].items():
        assert r["M_at_groove_nmm"] < 1e-3, k
        assert r["misplaced_1mm"]["sf_yield"] is None or r["misplaced_1mm"]["sf_yield"] > 0
    assert g["thrust"]["sf"] > 3.0


# ------------------------------------------------------------------------------------------- m-2 / m-3 hip
def test_hip_screws_and_holes():
    s = B.hip_screws()
    r12 = s["rows"]["x12"]
    assert r12["tip_past_insert_end_mm"] < 0.0 and r12["tip_to_pilot_floor_mm"] >= 2.0
    assert r12["engagement_d"] >= 1.5
    assert s["rows"]["x14"]["tip_in_melt_reservoir"]                     # the review's m-2, reproduced
    assert s["key"]["socket_s_mm"] == 3.0 and s["key"]["driver_access_ok"] and s["key"]["frame_key_clash_mm3"] < 0.5
    h = B.hip_holes()
    assert h["rows"]["D5.8"]["guided_pass"] and not h["rows"]["D5.5"]["guided_pass"]
    assert not h["rows"]["D5.8"]["freehand_pass"] and h["choice"]["guide"]


def test_insert_guide_stl():
    g = B.insert_guide(write=False)
    assert g["watertight"] and g["shells"] == 1 and g["bores"] == 8
    assert g["bore_pos_err_mm"] < 0.05 and g["bore_d_eq_mm"][0] == pytest.approx(B.GUIDE["bore_d"], abs=0.05)
    assert g["frame_clash_mm3"] < 0.5 and g["bed_fit_with_brim"]
    assert (B.PIECES / "hip_insert_guide.stl").exists() and (B.PIECES / "hip_insert_guide.3mf").exists()


# ------------------------------------------------------------------------------------------- record
@needs_res
def test_published_record():
    r = json.loads(RES_P.read_text())
    b = r["body"]
    st = b["min"]["static_cinch"]
    assert all(st[k] >= 1.0 for k in ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue"))
    assert b["voxels"]["boss_voxels"]["run"] > b["voxels"]["boss_voxels"]["bl053"]     # BOSS-LOCAL: the boss is in
    lug = b["us2_lug"]["bl058"]
    assert lug["strength"] >= 1.5 and lug["fatigue"] >= 1.15
    for k, v in r["stl"].items():
        if isinstance(v, dict) and "watertight" in v:
            assert v["watertight"] and v["shells"] == 1, k
    assert all(v["fits_with_brim"] for v in r["stl"]["bed"].values())
    assert r["stl"]["h1_lower_flat"]["delta_g"] == pytest.approx(0.0, abs=0.01)    # the halves are unchanged
    m = r["mass"]
    assert m["frame_delta_g"] == pytest.approx(m["print_delta_g"] + m["mount_delta_g"] + m["hip_screws_delta_g"], abs=1e-3)
    assert -1.0 < m["print_delta_g"] < 0.0
    h = r["us_route_heads"]
    assert h["pin_head_pass"] and h["pin_head_recess_mm"] >= h["bolt_head_rule_recess_mm"]
    assert h["pin_head_outside_clevis_min_mm"] >= h["bolt_head_rule_recess_mm"]
    k = r["kit"]
    assert k["PIN-RET_d"]["step"] == "(d)" and "US2 pin head in its counterbore (1 per side)" in k["FIT-US_marks"]
    assert len(k["pins_bom"]) == 6 and {x["retainer"] for x in k["pins_bom"]} == {"hairpin", "eclip"}


@needs_res
def test_ledger_books_the_bl058_rows():
    from huntkit.mass import ledger as L
    m = json.loads(RES_P.read_text())["mass"]
    rows = L.corrections("corrie_b2_h1", "M")["BL058"]
    assert sum(x["g"] for x in rows) == pytest.approx(m["frame_delta_g"] + m["attachment_delta_g"], abs=0.02)
    assert all("bl058.json" in x["source"] for x in rows)
    assert L.corrections("corrie_b2_today", "M")["BL058"] == []
