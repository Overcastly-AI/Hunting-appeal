"""BL-053 (fifth review): 3D cradle, lane lug fixes, US2 nut traps, strap wrap, gauge pass values, pin retention,
print plan. The heavy FEA results are read from analysis/h1_rev5.json (written by huntkit.gendesign.h1_rev5); the
geometry checks slice the exported STLs."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "designs" / "pack_5200"
PRINT = PACK / "print" / "frame_h1"
sys.path.insert(0, str(PACK))

from huntkit.gendesign import h1_bedfit as BF  # noqa: E402
from huntkit.gendesign import h1_rev5 as R  # noqa: E402

RES = json.loads((PACK / "analysis" / "h1_rev5.json").read_text())


def _section_loops(mesh, origin, normal):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    return [] if s is None else [np.asarray(d) for d in s.discrete]


def _inside(loops, pts, dims):
    from matplotlib.path import Path as MPath
    k = np.zeros(len(pts), int)
    for d in loops:
        k += MPath(d[:, dims]).contains_points(pts)
    return (k % 2) == 1


@pytest.fixture(scope="module")
def asm():
    import trimesh
    return trimesh.load(PRINT / "h1_assembled.stl")


# ------------------------------------------------------------------------------------------------ M-1 cradle
def test_cradle_3d_statics():
    import us_route as U
    cd = U.cradle_3d()
    for n, half in (("us1", 70.0), ("us2", 165.0)):
        V = cd["vertical_n"][n]
        for b in U.CRADLE3D_BELLY:
            lat = {cd["rows"][f"{n}|b{b:g}|dy{dy:g}|in"]["lateral_n"] for dy in U.CRADLE3D_DY}
            assert max(lat) - min(lat) < 0.2                                  # lateral pull independent of dy
            assert min(lat) == pytest.approx(V * half / (2 * b), rel=1e-3)     # = V x / (2 belly)
            for dy in U.CRADLE3D_DY:
                r = cd["rows"][f"{n}|b{b:g}|dy{dy:g}|in"]
                v = np.asarray(r["vec_n"])
                assert v[0] < 0 and v[2] < 0                                    # inboard and down on the R pin
                assert 2 * -v[2] == pytest.approx(V, rel=2e-3)                  # two legs carry V
    # the 280 mm quarter: US1 legs run outboard 70 mm, US2 straight down at its edge
    assert cd["rows"]["us1|b40|dy0|out"]["vec_n"][0] > 0
    assert cd["rows"]["us2|b40|dy0|out"]["vec_n"][0] == pytest.approx(0.0, abs=0.1)
    assert cd["rows"]["us2|b40|dy0|in"]["lateral_n"] == pytest.approx(1029.1, abs=1.0)


# ------------------------------------------------------------------------------------------------ M-3 lugs
def test_lugs_meet_the_ticket_down_to_40mm():
    for n in ("us1", "us2"):
        dm = RES["lugs"][n]["print"]["design_min"]
        assert dm["strength"] >= R.STRENGTH_GOAL and dm["fatigue"] >= R.FAT_GOAL
        fam = RES["lugs"][n]["print"]["families"]
        for b in (40, 50, 60, 70):
            assert fam[f"cradle3d|b{b}"]["fatigue"] >= R.FAT_GOAL
        # the sensitivity (contact 95 mm aft) at least at the goal
        assert fam["cradle3d_dy95|b40"]["fatigue"] >= R.FAT_GOAL - 0.005
        # monotone in belly (flatter = worse)
        f = [fam[f"cradle3d|b{b}"]["fatigue"] for b in (40, 50, 60, 70)]
        assert f == sorted(f)


def test_bl051_print_failed_the_3d_cradle():
    """The finding is real: the BL-051 print fails the 3D cradle at 40 mm on both lugs, and US2 misses the goal even
    at the old 60 mm minimum belly."""
    for n in ("us1", "us2"):
        fam = RES["lugs"][n]["bl051_print"]["families"]
        assert fam["cradle3d|b40"]["fatigue"] < 1.0
    assert RES["lugs"]["us2"]["bl051_print"]["families"]["cradle3d|b60"]["fatigue"] < R.FAT_GOAL
    assert RES["lugs"]["us2"]["bl051_print"]["families"]["cradle3d|b40"]["region"] == "fairlead"   # inner cheek


def test_fixes_are_in_the_print(asm):
    """US1: solid between the fairlead block and the lower branch (the old gap); US2: the inner cheek reaches z pin
    +/- 14 and its buttress stands inboard of it; the pin slot (+/- 6 mm of the pin axis) inboard stays clear."""
    p1, p2 = R.station("us1"), R.station("us2")
    # US1 at z 100, x 55: the BL-051 print had a 10 mm gap between y -15 (block) and y -17 (branch top) .. -2
    loops = _section_loops(asm, [0, 0, 100.0], [0, 0, 1])
    ys = np.arange(-16.0, -3.0, 1.0)
    assert _inside(loops, np.c_[np.full(ys.size, 55.0), ys], [0, 1]).all()
    # US2 inner cheek grown: at z pin + 12 the cheek (x 147-155) is solid up to the tip
    loops = _section_loops(asm, [0, 0, p2["z"] + 12.0], [0, 0, 1])
    q = np.array([[151.0, p2["y_pin"]], [151.0, p2["y_tip"] - 1.0], [140.0, p2["y_floor"] + 1.0]])
    assert _inside(loops, q, [0, 1]).all()
    # pin slot: at z = pin, inboard of the inner cheek (x 140-146) nothing above the arm top at the pin height
    loops = _section_loops(asm, [0, 0, p2["z"]], [0, 0, 1])
    q = np.c_[np.arange(140.0, 146.0, 1.0), np.full(6, p2["y_pin"])]
    assert not _inside(loops, q, [0, 1]).any()
    # pin holes open through both cheeks of every lane station (printed 7.0)
    for p in (p1, p2):
        for dx in (-14.0, 14.0):
            loops = _section_loops(asm, [p["x"] + dx, 0, 0], [1, 0, 0])
            ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
            ring = np.c_[p["y_pin"] + 3.2 * np.cos(ang), p["z"] + 3.2 * np.sin(ang)]
            assert not _inside(loops, ring, [1, 2]).any()


# ------------------------------------------------------------------------------------------------ M-2 joint
def test_nut_trap_holds_the_nut_and_walls_are_2mm(asm):
    tw = BF.trap_walls()
    assert tw["pass_2mm"] and tw["min_wall_mm"] >= 2.0 and tw["nut_held_by_flats"]
    p = R.station("us2")
    (y, z) = BF.bolt_axes(p)[0]
    loops = _section_loops(asm, [147.5, 0, 0], [1, 0, 0])
    # hex slot: open within +/- 4.0 of the axis in z, solid at +/- 4.4 (8.2 AF), and the nut cannot be 9.24 across
    open_ = np.c_[np.full(3, y), z + np.array([-3.9, 0.0, 3.9])]
    shut = np.c_[np.full(2, y), z + np.array([-4.4, 4.4])]
    assert not _inside(loops, open_, [1, 2]).any()
    assert _inside(loops, shut, [1, 2]).all()
    # the block's z faces stand >= 2 mm beyond the washer slot
    loops = _section_loops(asm, [150.5, 0, 0], [1, 0, 0])
    wall = np.c_[np.full(2, y), np.array([z - BF.JOINT.slot_w / 2 - 1.0, p["z"] - BF.BLOCK_HALF_Z + 1.0])]
    assert _inside(loops, wall, [1, 2]).all()


def test_joint_carries_the_3d_rows_and_the_wrap():
    j = RES["joint"]
    assert j["share_0.6"]["families"]["c3d"]["min_sf"] >= 1.5
    assert j["share_0.6"]["families"]["c3d"]["min_fatigue"] >= R.FAT_GOAL
    assert j["share_1"]["families"]["c3d"]["min_fatigue"] >= 1.0
    assert j["share_1"]["families"]["wrap"]["min_fatigue"] > 2.0
    assert all(w["direct"] and w["g_times_req"] == 3.0 for w in j["wrap_rows"].values())


# ------------------------------------------------------------------------------------------------ M-6 wrap
def test_strap_wrap_on_its_own_lip(asm):
    import us_route as U
    w = RES["strap_wrap"]
    assert w["worst"]["us2"]["wrap_deg"] > 5.0 and w["worst"]["us2"]["lip_r_mm"] >= 3.0
    assert w["worst"]["us1"]["wrap_deg"] < 5.0                     # US1 clears its rounded floor end
    p = R.station("us2")
    # the lip is rounded: no print at the old sharp corner (y_floor - 0.4, z pin - 14.5 + 0.4) across the throat
    loops = _section_loops(asm, [p["x"], 0, 0], [1, 0, 0])
    corner = np.array([[p["y_floor"] - 0.4, p["z"] - BF.BLOCK_HALF_Z + 0.4]])
    assert not _inside(loops, corner, [1, 2]).any()
    env = U.own_envelope(asm, "us2")
    assert min(z for _, z in env) < p["z"] - BF.BLOCK_HALF_Z + 1.0


# ------------------------------------------------------------------------------------------------ M-4 gauges
def test_gauge_pass_lines_are_numbers():
    g = RES["gauges"]
    for key in ("MT-1cr|us1", "MT-1cr|us2", "T1|us1", "T1|us2", "CLEVIS-SHARE|us2_inboard", "CLEVIS-SHARE|us2_yz"):
        t = g["tests"][key]
        assert abs(np.linalg.norm(t["pull_unit_vector_frame_R"]) - 1.0) < 1e-3
        for st in t["steps"]:
            assert st["band_mpa"][0] <= st["sigma_mpa"] + 1e-6 <= st["band_mpa"][1] + 2e-6
            assert st["pass_if_abs_microstrain_at_most"] >= abs(st["microstrain"])
            assert st["microstrain"] == pytest.approx(st["sigma_mpa"] / g["E_xy_mpa"] * 1e6, abs=1.5)
    # linear in the pin load
    s = g["tests"]["MT-1cr|us2"]["steps"]
    assert s[1]["sigma_mpa"] == pytest.approx(2 * s[0]["sigma_mpa"], rel=0.02)
    assert "inner" in g["tests"]["CLEVIS-SHARE|us2_inboard"]["eye_bears_on"]


# ------------------------------------------------------------------------------------------------ M-5 pins
def test_pin_retention_for_all_12():
    pn = RES["pins"]
    assert set(pn["stations"]) == {"hinge", "us1", "us2", "im1", "im2", "im3"}
    for n, r in pn["stations"].items():
        assert r["qty"] == 2
        assert r["shank_mm"] == pytest.approx(r["span_mm"] + R.CLIP_EDGE + R.CLIP_HOLE_D / 2 + R.TAIL_BEYOND_HOLE, abs=0.06)
        if "bending" in r:
            assert r["bending"]["sf_yield"] >= 1.5 and r["bending"]["sf_fatigue"] >= 1.15
    assert pn["stations"]["hinge"]["material"] == "ti_6al_4v" and pn["stations"]["hinge"]["removed_at_bag_off"]
    assert pn["clip_double_shear_n"] > 500
    assert len(pn["test"]["steps"]) == 3 and "http" in pn["retainer"]["source"]
    assert R.SLOT_HALF * 2 >= 12.0                                  # the buttress leaves room for tail + clip


# ------------------------------------------------------------------------------------------------ B-1 print
def test_support_map_on_a_known_overhang():
    """An L: a 10 mm cube on the plate with a 20 x 10 x 4 mm arm off its top (y up is the build axis): the arm's
    underside needs support except the 1 mm next to the cube (45 deg rule at 1 mm voxels)."""
    import trimesh
    a = trimesh.creation.box(extents=(10, 10, 10))
    a.apply_translation((5, 5, 5))
    b = trimesh.creation.box(extents=(20, 4, 10))
    b.apply_translation((20, 8, 5))
    m = trimesh.util.concatenate([a, b])
    m = trimesh.boolean.union([a, b], engine="manifold") if hasattr(trimesh.boolean, "union") else m
    r = R.support_map(m, up=1.0, pad=1.0)
    assert r["plate_contact_mm2"] == pytest.approx(100.0, abs=12.0)
    assert r["supported_mm2"] == pytest.approx(190.0, abs=25.0)          # (20 - 1) x 10
    assert r["support_column_mm3"] == pytest.approx(190.0 * 6.0, rel=0.15)


def test_print_settings_published():
    ps = json.loads((PRINT / "print_settings_bl053.json").read_text())
    assert ps == RES["print_settings"]
    assert "wearer face down" in ps["orientation"]["all_files"]
    assert ps["supports"]["interface_layers"] == 3 and ps["supports"]["material"].startswith("PAHT-CF")
    assert len(ps["supports"]["blockers"]) >= 4
    for k, f in ps["files"].items():
        assert f["filament_g_high"] >= f["filament_g_est"] >= f["part_g"]
        assert f["print_h_est"] > 0
    lo = ps["files"]["h1_lower_flat.stl"]
    assert lo["supported_by_region_mm2"]["stay"] > 0 and ps["scars"]["fatigue_critical"]
    assert ps["scars"]["allowance"]["max_removed_mm"] <= 0.2


# ------------------------------------------------------------------------------------------------ finish
def test_reexport_checks_and_ledger():
    sl = RES["slices"]
    assert sl["lanes"]["fairleads_pass"] and sl["joint"]["pass"] and sl["crown"]["pass"]
    assert RES["bed"]["lower"]["fits_with_brim"] and RES["bed"]["upper"]["fits_with_brim"]
    if "clearance" in RES:
        assert RES["clearance"]["pass"]
    from huntkit.mass import ledger as L
    m = RES["mass"]
    assert m["print_delta_g"] == pytest.approx(m["assembled_g"] - m["assembled_bl051_g"], abs=0.11)
    rows = L.corrections("corrie_b2_h1", "M")["BL053"]
    assert sum(r["g"] for r in rows) == pytest.approx(m["print_delta_g"] + m["retention_delta_g"], abs=0.05)
    assert L.corrections("corrie_b2_today", "M")["BL053"] == []
    assert 40.0 < m["lug_fixes_g"] < 70.0
