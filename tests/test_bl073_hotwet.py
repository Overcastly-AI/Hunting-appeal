"""BL-073 (review 8 close-out, huntkit.gendesign.bl073_hotwet): the hot/wet B-basis (tolerance factor, hot ratio,
record values), the hip bearing ring (closed-form Hetenyi check against a finite-difference beam on an elastic
foundation, bolt length, torque / preload rows, no traps), the z 234 bolt move, the coupon arithmetic, the tornado and
the record on the exported geometry."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import bl070_h1p as P
from huntkit.gendesign import bl073_hotwet as B


# ------------------------------------------------------------------------------------------------ basis
def test_k_factor_matches_b_basis_tables():
    # CMH-17-1G Vol 1 8.3.4.3 normal B-basis k: n 5 3.407, n 6 3.006, n 10 2.355
    assert B.k_factor(5) == pytest.approx(3.4066, abs=2e-4)
    assert B.k_factor(6) == pytest.approx(3.0063, abs=2e-4)
    assert B.k_factor(10) == pytest.approx(2.3546, abs=2e-4)
    # monotone in n and above the population z_0.90
    ks = [B.k_factor(n) for n in range(3, 40)]
    assert all(a > b for a, b in zip(ks, ks[1:])) and ks[-1] > 1.2816


def test_k_factor_by_simulation():
    """A population whose 10th percentile sits on the line passes 'mean - k SD' about 5 % of the time at n 6."""
    rng = np.random.default_rng(7)
    n, k = 6, B.k_factor(6)
    x = rng.normal(0.0, 1.0, (200_000, n))
    line = -1.2816       # true 10th percentile
    pas = (x.mean(1) - k * x.std(1, ddof=1)) >= line
    assert pas.mean() == pytest.approx(0.05, abs=0.004)


def test_hot_ratio_and_record_values():
    h = B.hot_ratio()
    assert h["fiberlogy_40_20_dry"] == pytest.approx(55.7 / 64.5, abs=1e-3)
    assert h["chosen"] == 0.85 and h["chosen"] <= min(v["ratio"] for v in h.values() if isinstance(v, dict))
    r = P.ppa_record()
    assert r["hot"] == h["chosen"]
    assert r["knock_hw"] == pytest.approx(r["wet"] * r["hot"], abs=1e-4)
    assert r["s_z_b"] == pytest.approx(57 - B.k_factor(5) * 5, abs=0.01)
    assert r["s_xy_b"] == pytest.approx(168 - B.k_factor(5) * 4, abs=0.05)
    assert r["E_hot_hw"] == pytest.approx(7800 / 11800 * h["modulus_hot"], abs=1e-3)
    b = B.basis()
    assert b["z_knocked_hw"] == pytest.approx(39.97 * 0.6205, abs=0.01)
    # Raise3D conditioned Z (30.2, 23 C) is above the 23 C wet design value now (review 8 M-1)
    assert 30.2 > b["raise3d_cond_z_vs_hw_23c"]


def test_ppa_hw_layer_rule_by_hand():
    m = P.materials()["ppa_hw"]
    S = np.zeros((1, 6))
    S[0, 3] = 10.0                                   # tau_xy, layer normal y: interlayer
    assert P.layer_terms(S, 1, m)[2, 0] == pytest.approx(10.0 / (0.6205 * 0.6 * 39.97))
    with P.material("ppa_hw"):
        from huntkit.gendesign import frame_h1 as H1
        assert H1.PAHT["E_hot"] == pytest.approx(0.5876) and H1.PAHT["knock"] == 0.6205
    assert P.e_buckle("ppa_hw") == pytest.approx(11800 * 0.5876 * 0.85)


# ------------------------------------------------------------------------------------------------ hip mount
def test_hetenyi_against_finite_difference_beam():
    """Closed form: infinite beam on a Winkler foundation, point load P: peak deflection P beta / (2 k b), peak
    pressure P beta / (2 b). Finite-difference EI w'''' + k b w = q on a long beam reproduces it (< 1 %)."""
    E, t, b, k0, Pn = 68900.0, 2.0, 11.5, 244.0, 1000.0
    EI = E * b * t ** 3 / 12.0
    beta = (k0 * b / (4 * EI)) ** 0.25
    assert beta == pytest.approx(B.hetenyi(t=t, E_found=k0 * B.BOSS_DEPTH)["beta"], rel=1e-3)
    L, n = 200.0, 2001
    h = L / (n - 1)
    from scipy.sparse import diags
    from scipy.sparse.linalg import spsolve
    main = np.full(n, 6.0 * EI / h ** 4 + k0 * b)
    A = diags([np.full(n - 2, EI / h ** 4), np.full(n - 1, -4 * EI / h ** 4), main,
               np.full(n - 1, -4 * EI / h ** 4), np.full(n - 2, EI / h ** 4)], [-2, -1, 0, 1, 2]).tocsc()
    q = np.zeros(n)
    q[n // 2] = Pn / h
    w = spsolve(A, q)
    p_fd = k0 * w.max()
    assert p_fd == pytest.approx(Pn * beta / (2 * b), rel=0.01)


def test_hip_plate_rows_bolt_length_and_no_traps():
    hp = B.hip_plate()
    assert hp["pass"] and hp["webs"]["traps"] == 0
    assert hp["webs"]["between_holes_mm"] >= 2.0 and hp["webs"]["hole_to_boss_edge_mm"] >= 2.0
    sl = hp["screw"]
    assert sl["protrusion_mm"] >= 2 * 0.8 and sl["stack_mm"] == pytest.approx(3 + B.BOSS_DEPTH + B.RING_T + 4.0)
    assert sl["bl070_protrusion_mm"] == pytest.approx(0.0)          # review 8 B-1: flush on the BL-070 stack
    # preload from T = K F d at the low nut factor sets the creep row; bearing per bolt force is the larger of the
    # Hetenyi peak and the ring average
    assert hp["preload_n"]["max"] == pytest.approx(B.TORQUE_NM / (B.K_LO * 0.005), abs=1)
    per = hp["pressure_mpa_per_kn"] / 1e3
    carry = [r for r in hp["rows"].values() if r["kind"] == "creep"]
    for r in carry:
        assert r["pressure_mpa"] == pytest.approx(per * max(hp["preload_n"]["max"], r["T_max_n"]), rel=0.01)
        assert r["sf"] == pytest.approx(0.55 * hp["allow_mpa"] / r["pressure_mpa"], rel=0.01)
    assert hp["min_sf"]["fatigue"] >= 1.15 and hp["min_sf"]["creep"] >= 1.5 and hp["min_sf"]["strength"] >= 1.5
    # the BL-070 seat on the nut face reproduces review 8 (fatigue 1.06 on the BL-069 basis)
    assert hp["bl070_dw_ring_check"]["fatigue_on_dw_bl069_basis"] == pytest.approx(1.06, abs=0.01)
    assert hp["relaxation"]["closed_at_walk"]


def test_z234_bolt_move_stays_in_the_envelope():
    from dataclasses import replace
    from huntkit.gendesign import frame_h1 as H1
    j = replace(H1.JOINT, xy=B.JOINT_XY)
    env = H1.boss_envelope(j)
    assert all(v for v in env.values() if isinstance(v, bool))
    bc = H1.bore_continuity(j)
    assert bc["min_ligament_margin"] >= 1.0
    with B.plate_hook():
        assert H1.JOINT.xy == B.JOINT_XY and P.add_hip_through is B.add_hip_plate
    assert H1.JOINT.xy == B.JOINT_XY_BL070 and P.add_hip_through is not B.add_hip_plate


# ------------------------------------------------------------------------------------------------ coupons, tornado
def _M():
    return {"R1": 1.02, "z 234 joint fatigue": 1.05, "US2 lug fatigue": 1.10, "US2 clevis fatigue (share 0.6)": 1.5,
            "hip mount fatigue": 5.0, "buckling": 2.5, "_e_need": 0.5}


def test_coupon_lines():
    b = B.basis()
    lt = {"lower": {"median_s": 150.0}, "upper": {"median_s": 140.0}}
    c = {x["id"]: x for x in B.coupons_hw(_M(), b, lt)}
    m_fat = min(1.02, 1.05, 1.10 / 1.15, 1.5 / 1.15, 5.0 / 1.15)
    assert c["CA-1-HW"]["smax_design_mpa"] == pytest.approx(0.30 * b["tau_il_hw"] / m_fat, abs=1e-3)
    assert c["CA-1-HW"]["smax_test_mpa"] == pytest.approx(1.15 * c["CA-1-HW"]["smax_design_mpa"], abs=1e-3)
    assert c["CA-1-HW"]["peak_load_n"] == pytest.approx(c["CA-1-HW"]["smax_test_mpa"] * B.SBS_G["w"] * B.SBS_G["t"] / 0.75, abs=1)
    assert c["CA-3-HW"]["need_z_mpa"] == pytest.approx(b["z_knocked_hw"] / 1.02, abs=0.01)
    assert "2.355" in c["CA-3-HW"]["statistic"] and "140 s" in c["CA-3-HW"]["what"]
    assert "33 J" in c["T4c-PPA-HW"]["load"] and "5 PPA-CF" in c["T4c-PPA-HW"]["coupons"]
    assert c["T4c-PPA-HW"]["bend"]["under_rig_cell"] and B.rig_loads(b)["all_under_cell"]
    assert {"T4b-PPA-COLD", "T4c-PPA-COLD", "T4c-PPA-CROWN"} <= set(c)


def test_tornado_scaling():
    M = {"R1": 1.2, "hip mount fatigue": 5.0, "buckling": 2.0}
    t = {x["variation"].split(" (")[0]: x["rows"] for x in B.tornado(M, {"R1": 0.9, "R1|z": 0.97})}
    assert t["fatigue ratio 0.25"]["R1"] == pytest.approx(1.2 * 0.25 / 0.30, abs=1e-3)
    assert t["fatigue ratio 0.25"]["buckling"] == 2.0
    assert t["interlayer shear 0.55 x Z"]["R1"] == pytest.approx(1.2 / (0.9 * 0.6 / 0.55 + 0.1), abs=1e-3)
    assert t["interlayer shear 0.55 x Z"]["hip mount fatigue"] == 5.0
    assert t["hot/wet modulus 0.50"]["buckling"] == pytest.approx(2.0 * 0.5 / 0.5876, abs=1e-3)


# ------------------------------------------------------------------------------------------------ record
REC = P.REC_JSON
has_bl073 = REC.exists() and "bl073" in json.loads(REC.read_text())


def by_name(h):
    return {q["name"]: q for q in h["rows"]}


@pytest.mark.skipif(not has_bl073, reason="run python -m huntkit.gendesign.bl073_hotwet report")
def test_record_hot_wet_rows():
    r = json.loads(REC.read_text())
    h, x = r["h1p"], r["bl073"]
    assert "hot/wet" in h["checked_on"] and x["margins_bl073_hw"]["R1"] == pytest.approx(
        by_name(h)["fatigue, cinch-cycled (R1)"]["value"], abs=1e-3)
    by = {q["name"]: q for q in h["rows"]}
    # the two rows the ticket names, on the hot/wet basis
    assert by["fatigue, cinch-cycled (R1)"]["value"] >= 1.0
    assert by["z 234 joint fatigue"]["value"] >= 1.0
    for q in h["rows"]:
        assert q["pass"] or q.get("gated_by"), q
    # hip mount: no traps, the ring, >= 2 threads proud; keys BL-071 reads are still there
    hm = h["hip_mount"]
    for k in ("nut_seat_depth_mm", "bearing_ring_mm2", "bearing_n", "rows", "min_sf", "pass", "hardware"):
        assert k in hm
    assert hm["pass"] and hm["boss"]["traps"] == 0 and hm["screw"]["protrusion_threads"] >= 2
    # BL-070 record kept, coupons added under new keys
    assert "h1p_bl070" in r and r["coupons"] and r["coupons_bl073"]
    assert {c["id"] for c in r["coupons_bl073"]} >= {"CA-1-HW", "CA-3-HW", "CA-4-HW", "T4b-PPA-COLD"}


@pytest.mark.skipif(not has_bl073, reason="run python -m huntkit.gendesign.bl073_hotwet report")
def test_record_mass_and_print_files():
    import trimesh
    r = json.loads(REC.read_text())
    m = trimesh.load(P.STL_DIR / "h1_assembled.stl", force="mesh")
    assert m.is_watertight
    assert r["h1p"]["body_g"] == pytest.approx(m.volume * P.RHO_PPA, abs=0.5)
    pf = r["bl073"]["print_files"]
    for n in ("lower", "upper"):
        f = trimesh.load(P.STL_DIR / f"h1_{n}_flat_print.stl", force="mesh")
        assert f.is_watertight
        assert pf[n]["plate_contact_with_pads_mm2"] > pf[n]["plate_contact_part_mm2"] + 1000
        assert f.extents[0] <= 340 and f.extents[1] <= 320
    for n in ("lower", "upper"):
        sw = r["bl073"]["spool_plan"][n]["swap"]
        assert sw is not None and sw["spool1_g_range"][1] <= B.SPOOL_NET_G - B.SPOOL_RESERVE_G


def test_checked_raster_is_the_exported_stl():
    """Review 8 m-3: the checked raster is tracked (h1p/h1p_checked_raster.npz), so this runs on a clean checkout."""
    npz = P.STL_DIR / "h1p_checked_raster.npz"
    if not npz.exists():
        pytest.skip("run python -m huntkit.gendesign.bl073_hotwet report")
    solid, _ = P.reraster()
    assert np.array_equal(solid, np.load(npz)["solid"])
