"""BL-050 Part A: bed fit, bolt-on US2 outer clevis, I-section arms, US2 notch, ledger pins."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import h1_bedfit as BF

REPO = Path(__file__).resolve().parents[1]
PD = REPO / "designs" / "pack_5200" / "print" / "frame_h1"
RES = REPO / "designs" / "pack_5200" / "analysis" / "h1_bedfit.json"


# ------------------------------------------------------------------------------------------------ closed forms
def test_footprint_fit_rectangle():
    """A 300 x 100 rectangle turned 30 deg: the fit finds it back (300 x 100, 0 brim spare = 40 / 220 - 16)."""
    P = np.array([[0, 0], [300, 0], [300, 100], [0, 100]], float)
    th = math.radians(30.0)
    R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    r = BF.footprint_fit(P @ R.T, bed=(340.0, 320.0), brim=8.0)
    # closed form: a W x H rectangle at angle a spans W cos a + H sin a by W sin a + H cos a
    a = np.radians(np.arange(0.0, 90.0, 0.01))
    w_, h_ = 300 * np.cos(a) + 100 * np.sin(a), 300 * np.sin(a) + 100 * np.cos(a)
    over = np.maximum(np.maximum(w_, h_) + 16 - 340, np.minimum(w_, h_) + 16 - 320)
    assert r["over_mm"] == pytest.approx(over.min(), abs=0.5) and r["fits_with_brim"]   # 0.25 deg steps
    assert r["w_mm"] * r["h_mm"] >= 300 * 100 - 1e-6
    big = np.array([[0, 0], [335, 0], [335, 310], [0, 310]], float)
    assert not BF.footprint_fit(big, bed=(340.0, 320.0), brim=8.0)["fits_with_brim"]


def test_orient_on_bed_turns_a_diagonal_part_onto_the_plate():
    """A thin bar 380 long fits a 340 x 320 plate only on the diagonal: orient_on_bed writes it turned so that its
    axis-aligned extents fit (what the slicer sees)."""
    import trimesh
    m = trimesh.creation.box(extents=(380.0, 60.0, 10.0))
    m.apply_translation(-m.bounds[0])
    f, info = BF.orient_on_bed(m)
    assert info["fits_with_brim"] and f.extents[0] <= 340 - 16 + 1e-6 and f.extents[1] <= 320 - 16 + 1e-6
    assert f.volume == pytest.approx(m.volume, rel=1e-6)
    assert 0 < info["rot_deg"] % 90 < 90                       # turned, not just swapped
    g, info2 = BF.orient_on_bed(trimesh.creation.box(extents=(200.0, 100.0, 10.0)))
    assert info2["rot_deg"] in (0.0, 90.0) and g.extents[0] >= g.extents[1]


def test_net_section_of_the_block_without_traps_is_the_rectangle():
    """With the traps closed (slot width 0) the net section is the block rectangle: A = b h, I = b h^3 / 12."""
    import dataclasses
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    j = dataclasses.replace(BF.JOINT, washer_od=-0.4)          # slot_w 0
    ns = BF.net_section(p, j, h=0.1)
    hy = p["y_floor"] - (p["yc"] + BF.BLOCK_DY_LO)
    hz = 2 * BF.BLOCK_HALF_Z
    assert ns["A"] == pytest.approx(hy * hz, rel=0.01)
    assert ns["Iz"] == pytest.approx(hz * hy ** 3 / 12.0, rel=0.02)
    assert ns["Iy"] == pytest.approx(hy * hz ** 3 / 12.0, rel=0.02)
    assert abs(ns["Iyz"]) < 1e-6 * ns["Iy"]


def test_contact_solve_pure_pull_and_pure_moment():
    """The joint face model (frame_h1.contact_solve on the clevis face): a pure pull N splits equally between the two
    symmetric bolts with no contact; a moment about the bolt line's normal axis is a couple: bolt force x lever
    to the compressed edge = M (rigid face, to the face grid's resolution)."""
    from huntkit.gendesign import frame_h1 as H1
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    U, V, a = BF._face_grid(p)
    bolts = [(0.0, -BF.JOINT.dz), (0.0, BF.JOINT.dz)]
    r = H1.contact_solve(U, V, a, 1000.0, 0.0, 0.0, bolts, 1e5, 1e3)
    assert r["bolt_n"] == pytest.approx([500.0, 500.0], rel=1e-3) and r["resid_n"] < 1e-6
    # moment about z (sum f u = -Mz): opening on the -u side; with a stiff face the bolts' resultant sits at u 0 and
    # the compression near the top edge: T (u_top - 0) ~ M within the contact block's own depth
    M = 5000.0
    r = H1.contact_solve(U, V, a, 0.0, 0.0, -M, bolts, 1e5, 1e6)
    T = r["bolt_n"].sum()
    lever = U.max()
    assert T * lever == pytest.approx(M, rel=0.15) and r["resid_n"] < 1e-3


def test_joint_check_hand_numbers():
    """The governing row against a hand calculation: bolt shear of the cradle row = direct shear / 2 + the torsion
    couple M_x / (2 dz); the Ti bolts are far from their limits; the PAHT governs."""
    r = BF.joint_check()
    row = r["rows"]["cradle"]
    Fc = np.array(row["force_on_clevis_n"])
    Mx = row["moment_nmm"][0]
    vy = Fc[1] / 2 + abs(Mx) / (2 * BF.JOINT.dz)
    assert max(row["bolt_shear_n"]) == pytest.approx(math.hypot(vy, Fc[2] / 2), rel=0.01)
    assert row["sf"]["bolt_tension"] > 5 and row["sf"]["bolt_shear"] > 5
    assert r["worst_strength"]["check"] in ("net_section", "hole_bearing")
    assert r["worst_strength"]["sf"] >= 2.0 and r["worst_fatigue"]["fatigue"] >= 1.15
    r1 = BF.joint_check(share=1.0)
    assert r1["worst_strength"]["sf"] >= 1.0 and r1["worst_fatigue"]["fatigue"] >= 1.0
    assert r1["worst_strength"]["sf"] < r["worst_strength"]["sf"]


def test_isect_pockets_volume_closed_form():
    """A pocketed arm loses exactly the hull of its pocket sections: for the US2 arm the I pocket volume matches the
    frustum of the two pocket rectangles (linear taper) within the hull's rounding."""
    from huntkit.gendesign import h1_lanes as LN
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    a = {**LN.ARM["us2"], "isect": dict(LN.ISECT)}
    pk = LN.pocket_solid(p, a)
    arm = LN.arm_solid(p)
    removed = arm.volume() - (arm - pk).volume()
    s = LN.arm_sections(p, a)
    da, db = LN._pocket_span(p, a)
    s0, s1 = p["stay_r"], abs(p["x"] - p["sign"] * LN.STAY_X) - (p["geom"].throat / 2 + p["geom"].cheek)
    q = a["isect"]
    areas = []
    for dd in (da, db):
        t = (dd - s0) / (s1 - s0)
        yl = s["root"]["y"][0] + t * (s["tip"]["y"][0] - s["root"]["y"][0]) + q["flange"]
        yh = s["root"]["y"][1] + t * (s["tip"]["y"][1] - s["root"]["y"][1]) - q["flange"]
        zl = s["root"]["z"][0] + t * (s["tip"]["z"][0] - s["root"]["z"][0])
        zh = s["root"]["z"][1] + t * (s["tip"]["z"][1] - s["root"]["z"][1])
        areas.append((yh - yl) * (zh - zl - q["web"]))
    A0, A1 = areas
    frustum = (db - da) / 3.0 * (A0 + A1 + math.sqrt(A0 * A1))
    assert removed == pytest.approx(frustum, rel=0.12)        # the arm's 3 mm edge radius trims the pocket corners
    assert not LN.ARM_ISECT["us1"] and not LN.ARM_ISECT["us2"]   # BL-050: rejected, arms built solid


def test_in_arm_pocket_mask_matches_solid():
    """The voxel mask (lug FEA) and the manifold (print) agree on what the pocket removes."""
    from huntkit.gendesign import h1_lanes as LN
    p = next(q for q in BF.us2_stations() if q["side"] == "R")
    a = {**LN.ARM["us2"], "isect": dict(LN.ISECT)}
    bb = LN.arm_box(p, a)
    g = np.mgrid[bb["x"][0]:bb["x"][1]:0.5, bb["y"][0]:bb["y"][1]:0.5, bb["z"][0]:bb["z"][1]:0.5].reshape(3, -1).T
    solid = LN.in_arm(g, p, dict(LN.ARM["us2"]))
    ised = LN.in_arm(g, p, a)
    assert ised.sum() < solid.sum() and not (ised & ~solid).any()
    removed_vox = (solid & ~ised).sum() * 0.125
    arm = LN.arm_solid(p)
    removed_man = arm.volume() - (arm - LN.pocket_solid(p, a)).volume()
    assert removed_vox == pytest.approx(removed_man, rel=0.2)


# ------------------------------------------------------------------------------------------------ geometry
def test_split_geometry():
    """Blocks below the throat floor only; split plane in the throat floor; bolts inside the block with washer room;
    the trap opens below the block (wearer face)."""
    for p in BF.us2_stations():
        g = p["geom"]
        assert abs(p["x"]) - g.throat / 2 < BF.SPLIT_X < abs(p["x"]) + g.throat / 2
        b = BF.block_boxes(p)
        for k in ("body", "clevis"):
            assert b[k][3] <= p["y_floor"]                         # never above the throat floor
        for (y, z) in BF.bolt_axes(p):
            assert b["body"][2] + BF.JOINT.hole_d / 2 + 2.0 <= y
            assert abs(z - p["z"]) + BF.JOINT.washer_od / 2 <= BF.BLOCK_HALF_Z
        j = BF.JOINT
        assert j.head_face - j.bolt_len < j.trap_x0                 # the bolt reaches through the nut
        assert j.tail_x > BF.BODY_BLOCK_X0                          # tail hole inside the block
        assert j.bolt_len >= (j.head_face - j.nut_face) + 2 * j.washer_t + j.nut_t


# ------------------------------------------------------------------------------------------------ shipped files
@pytest.mark.skipif(not (PD / "us2_clevis_R.stl").exists(), reason="print files not generated")
def test_print_files_bed_and_pieces():
    """The flat halves as written fit the H2S with the 8 mm brim without turning; the clevises are closed shells;
    the assembled frame is one closed shell."""
    import trimesh
    for nm in ("lower", "upper"):
        r = BF.bed_check(PD / f"h1_{nm}_flat.stl")
        assert r["fits_with_brim"], (nm, r)
    for s in ("R", "L"):
        m = trimesh.load(PD / f"us2_clevis_{s}.stl")
        assert m.is_watertight and len(m.split(only_watertight=False)) == 1 and 10.0 < m.volume * 1.06e-3 < 20.0
    a = trimesh.load(PD / "h1_assembled.stl")
    assert a.is_watertight and len(a.split(only_watertight=False)) == 1


@pytest.mark.skipif(not (PD / "us2_clevis_R.stl").exists(), reason="print files not generated")
def test_joint_slices_on_the_print():
    r = BF.joint_slices()
    assert r["pass"], r
    for s in ("R", "L"):
        assert [round(h["d_eq_mm"], 1) for h in r[s]["clevis_170"]["holes"]] == [4.8, 4.8]


@pytest.mark.skipif(not (PD / "h1_assembled.stl").exists(), reason="print files not generated")
def test_spreader_us2_notch_air():
    """A3 as revised by BL-051: the z 142 notch is 0 mm from the arm root in plan; with the stay crown restored the
    notch footprint holds the plain crown, and nothing in it stands proud of the support line the sheet bears on.
    (BL-050's 1.5 mm air was the crown cut away by strip_old_us; it no longer holds and is not the rule.)"""
    from huntkit.gendesign import spreader as S
    r = S.us2_notch_check()
    assert abs(r["plan_clear_mm"]) < 0.5
    assert r["pass"] and r["proud_mm"] <= S.US2_PROUD_MAX
    assert all(row["air_mm"] >= -S.US2_PROUD_MAX for row in r["rows"])
    assert r["air_mm"] < S.US2_ROOT_AIR          # the crown is back: the old 'air' was the defect


# ------------------------------------------------------------------------------------------------ record
@pytest.fixture(scope="module")
def res():
    if not RES.exists():
        pytest.skip("h1_bedfit.json not written")
    return json.loads(RES.read_text())


def test_option_c_fails_with_numbers(res):
    pr = res["option_c"]["probe"]
    assert pr["bed"]["lower"]["best_rotation"]["fits_with_brim"]          # 147 fits the bed ...
    assert pr["route"]["worst_clear_mm"]["us2"] < 10.0 and not pr["route"]["pass"]   # ... but the strap fails
    sw = {r["us2_x"]: r for r in res["option_c"]["sweep"]}
    assert not sw[165.0]["fits_with_brim"] and sw[147.0]["fits_with_brim"] and not sw[149.0]["fits_with_brim"]


def test_option_a_record(res):
    assert res["published"]["US2_X"] == 165.0 and res["published"]["US2_BOLT_ON"]
    ur = res["us_route"]["print_lanes"]
    assert ur["pass"] and min(r["min_clear_mm"] for r in ur["rows"]) >= 10.0
    assert len({(r["torso"], r["side"]) for r in ur["rows"]}) == 6
    assert res["joint"]["worst_strength"]["sf"] >= 2.0 and res["joint"]["worst_fatigue"]["fatigue"] >= 1.15
    sc = res["slice_checks"]
    assert sc["fairleads_pass"] and sc["channel"]["pass"] and sc["pawl"]["pass"] and sc["pieces_pass"]
    assert res["joint_slices"]["pass"]
    assert res["isect"]["adopted"] == []


def test_mass_rows_and_ledger(res):
    from huntkit.mass import ledger as L
    m = res["mass"]
    assert m["stations"] == 12 and m["pins_sleeves_delta_g"] == pytest.approx(4 * (m["pin_g"] + m["sleeve_g"]), abs=0.02)
    assert m["frame_delta_g"] == pytest.approx(m["print_delta_g"] + m["hardware_g"], abs=0.02)
    assert m["print_delta_g"] == pytest.approx(m["assembled_g"] - m["assembled_bl049_g"], abs=0.11)
    h1 = L.corrections("corrie_b2_h1", "M")["BL050"]
    today = L.corrections("corrie_b2_today", "M")["BL050"]
    # BL-051: the '4 stations booked short' row was a double count (the cradle rows book the US1 / US2 pins +
    # sleeves); BL050 keeps only the H1 clevis rows
    assert sum(r["g"] for r in h1) == pytest.approx(m["frame_delta_g"], abs=0.05)
    assert today == []
    rows = {r["name"]: r["g"] for r in L.parts("corrie_b2_today", "M")}
    assert rows["attachment: 7075 pins (8)"] == pytest.approx(8 * m["pin_g"], abs=0.02)
    assert rows["under-straps US1/US2: 7075 pins (4)"] == pytest.approx(4 * m["pin_g"], abs=0.1)     # rows to 0.1 g
    assert rows["under-straps US1/US2: UHMWPE sleeves (4)"] == pytest.approx(4 * m["sleeve_g"], abs=0.1)
