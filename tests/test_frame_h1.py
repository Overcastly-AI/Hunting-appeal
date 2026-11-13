"""H1 frame (huntkit.gendesign.frame_h1): joint mechanics closed forms, joint geometry, bore continuity, print
orientation, and the recorded rev C result. The voxel solver itself is verified against closed forms in
tests/test_frame_topopt.py (cantilever, torsion) and tests/test_frame_comp_d.py (M c / I)."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import frame_h1 as H


def _face(n=12, r_in=9.0, r_out=13.4, h=1.0):
    g = np.arange(-r_out, r_out + 1e-9, h)
    X, Y = np.meshgrid(g, g)
    r = np.hypot(X, Y)
    m = (r >= r_in) & (r <= r_out)
    return X[m], Y[m]


def test_contact_pure_tension_splits_equally():
    x, y = _face()
    bolts = np.array([[19.0, 0.0], [-19.0, 0.0]])
    r = H.contact_solve(x, y, np.ones_like(x), 2000.0, 0.0, 0.0, bolts, 4e4, 100.0)
    assert r["bolt_n"] == pytest.approx([1000.0, 1000.0], rel=1e-3)
    assert r["contact_mpa"] == pytest.approx(0.0, abs=1e-6)


def test_contact_pure_compression_is_uniform():
    x, y = _face()
    bolts = H.JOINT.bolts_local()
    N = -3000.0
    r = H.contact_solve(x, y, np.ones_like(x), N, 0.0, 0.0, bolts, 4e4, 100.0)
    assert r["bolt_n"].max() == pytest.approx(0.0, abs=1e-6)
    # symmetric face: uniform pressure N / A (mean-free coordinates)
    assert r["contact_mpa"] == pytest.approx(-N / x.size, rel=0.05)


def test_contact_moment_equilibrium_and_lever():
    x, y = _face()
    bolts = np.array([[0.0, 19.0], [0.0, -19.0]])
    M = 30000.0                                    # N mm about x (opens the y+ side)
    r = H.contact_solve(x, y, np.ones_like(x), 0.0, M, 0.0, bolts, 4e4, 100.0)
    assert r["resid_n"] < 1.0
    Tb = r["bolt_n"].max()
    # N = 0: bolt tension = contact compression C, M = T (19 - y_c) with the compression centroid y_c on the
    # closed side of the bore axis and inside the face: 19 < lever < 19 + 13.4
    assert M / (19 + 13.4) <= Tb <= M / 19.0


def test_boss_bending_hand_calc():
    j = H.Joint(theta_deg=0.0, xy=None)
    T = 1000.0
    a = j.e - (9.0 + 4.2 * 1.05)
    L = min(j.L_upper, j.L_lower)
    sig = 6 * T * a / (2 * j.r_boss * L ** 2)
    assert H.boss_bending_fi(T, j) == pytest.approx(sig / (0.8 * 88.0), rel=1e-6)


def test_capacities_hand_numbers():
    c = H.joint_capacities()
    assert c["washer_bearing_n"] == pytest.approx(math.pi / 4 * (144 - 5.1 ** 2) * 0.8 * 88, rel=1e-9)
    assert c["bolt_tension_n"] == pytest.approx(0.7 * 895 * 14.2)


def test_joint_geometry_holes_and_bosses():
    pts, voids, solids = [], [], []
    for sx, k, p, u in H.bolt_axes():
        pts += [p, p + u * 10.0]
        # every bolt axis point is inside its boss and inside the hole
        assert H.boss_sdf(np.array([p]))[0] < 0
        assert H.hole_mask(np.array([p]))[0]
        # bore centre is not cut by the joint features
        bore = np.array([[sx * 115.0, p[1] - H.JOINT.bolts_local()[k][1], H.JOINT.z]])
        assert not H.hole_mask(bore)[0]
    # 4 bolts, 2 per side, mirror symmetric
    ax = H.bolt_axes()
    assert len(ax) == 4
    xs = sorted(round(a[2][0], 6) for a in ax)
    assert xs[0] == pytest.approx(-xs[-1]) and xs[1] == pytest.approx(-xs[2])


def test_bore_continuity_ligaments_and_leg_travel():
    b = H.bore_continuity()
    assert b["min_ligament_margin"] >= 1.0
    assert b["legs"]["15"]["leg_crosses_z234"]          # the 15 in setting slides the leg across the split
    assert not b["legs"]["23"]["leg_crosses_z234"]


def test_lay_flat_puts_wearer_face_on_the_plate():
    import trimesh
    m = trimesh.creation.box((10, 4, 30))
    m.apply_translation((0, -20.0, 100.0))
    f = H.lay_flat(m)
    assert np.linalg.det(H.FLAT_R) == pytest.approx(1.0)
    assert f.extents[2] == pytest.approx(4.0)              # thickness along frame y is the print height
    assert f.bounds[0] == pytest.approx([0, 0, 0])


def test_recorded_result_passes_rev_c():
    if not H.RESULT.exists():
        pytest.skip("run python -m huntkit.gendesign.frame_h1 first")
    r = json.loads(H.RESULT.read_text())
    assert min(r["min"].values()) >= 1.0
    assert r["buckling_min"] >= 1.0
    assert r["joint"]["min_strength"] >= 1.0 and r["joint"]["min_fatigue"] >= 1.0
    assert r["keepouts"]["outside envelope (voxels)"] == 0
    assert r["keepouts"]["boss wearer face flush (rails)"]
    assert r["keepouts"]["boss bag side outboard of spreader and inside envelope"]
    assert r["keepouts"]["boss inside x half-width 152"]
    assert r["keepouts"]["boss clear of spreader clip"]
    assert r["keepouts"]["bolt head clear of spreader clip"]
    for k, v in r["keepouts"].items():
        # BL-046: the tube + rack channel is cut into the release body (h1_spine_channel, test_bl046_spine_channel);
        # this 2026-11-10 study body predates it, so its BL-046 channel key reads part-filled by design
        if k.endswith(("present", "empty")) and "BL-046" not in k:
            assert v >= 0.999, k


def test_contact_offset_bolts_balance_with_contact():
    # H1's asymmetric bolt pair under pure tension: bolts carry N plus the contact force that balances the moment
    x, y = _face()
    r = H.contact_solve(x, y, np.ones_like(x), 2000.0, 0.0, 0.0, H.JOINT.bolts_local(), 4e4, 100.0)
    assert r["resid_n"] < 1e-6 * 2000
    assert r["bolt_n"].sum() >= 2000.0 - 1e-6
