"""Hipbelt B structural check (huntkit.gendesign.hipbelt_structure, hipbelt_pivot_fe).

Solver verification against closed forms first (plate strip as a cantilever and as a simply supported beam, the
Hetenyi beam on an elastic foundation, the annular plate), then the design checks."""
import math

import numpy as np
import pytest

from huntkit.fea.frame import solve
from huntkit.gendesign import hipbelt_structure as hs
from huntkit.gendesign import hipbelt_pivot_fe as pfe

E = 6500.0
MAT = {"id": "t", "name": "t", "youngs_modulus_mpa": E, "poisson": 0.35, "density_kg_m3": 1370,
       "design_allowable_mpa": 100.0}


def _strip_model(L=100.0, b=20.0, t=3.0, n=20, rib=None):
    sec, c = hs._strip(b, t, rib)
    nodes = {f"n{i}": [L * i / n, 0.0, 0.0] for i in range(n + 1)}
    mem = [{"id": f"m{i}", "nodes": [f"n{i}", f"n{i + 1}"], "section": sec, "material": MAT, "ref": [0, 1, 0]}
           for i in range(n)]
    return {"nodes": nodes, "members": mem}, sec, c


def test_plate_strip_cantilever_out_of_plane_matches_closed_form():
    L, b, t, P = 100.0, 20.0, 3.0, 10.0
    m, sec, c = _strip_model(L, b, t)
    m["supports"] = {"n0": "fixed"}
    m["loads"] = {"n20": [0, P, 0, 0, 0, 0]}          # out of plane (global y = local y)
    r = solve(m)
    I = b * t ** 3 / 12
    assert r.displacements["n20"][1] == pytest.approx(P * L ** 3 / (3 * E * I), rel=1e-3)
    Mz = abs(r.elem_forces[0, 0, 5])
    assert Mz * c / sec.Iz == pytest.approx(6 * P * L / (b * t ** 2), rel=1e-3)


def test_plate_strip_simply_supported_uniform_load():
    L, b, t, w, n = 120.0, 25.0, 2.5, 0.2, 24
    m, sec, c = _strip_model(L, b, t, n)
    m["supports"] = {"n0": {"fix": "x y z rx"}, f"n{n}": {"fix": "y z"}}
    m["loads"] = {f"n{i}": [0, w * L / n * (0.5 if i in (0, n) else 1.0), 0, 0, 0, 0] for i in range(n + 1)}
    r = solve(m)
    mid = abs(r.elem_forces[n // 2, 0, 5])
    assert mid == pytest.approx(w * L ** 2 / 8, rel=0.01)
    I = b * t ** 3 / 12
    assert abs(r.displacements[f"n{n // 2}"][1]) == pytest.approx(5 * w * L ** 4 / (384 * E * I), rel=0.01)


def test_beam_on_winkler_foundation_matches_hetenyi():
    """Long beam on springs, central point load: w0 = P lam / (2 k), M0 = P / (4 lam) (Hetenyi 1946)."""
    b, t, h = 20.0, 3.0, 2.0                     # spacing h
    kf = hs.foundation_k()
    k = kf * b                                   # N/mm per mm of length
    sec, c = hs._strip(b, t)
    lam = (k / (4 * E * sec.Iz)) ** 0.25
    L = 8.0 / lam
    n = int(L / h)
    nodes = {f"n{i}": [-L / 2 + h * i, 0.0, 0.0] for i in range(n + 1)}
    mem = [{"id": f"m{i}", "nodes": [f"n{i}", f"n{i + 1}"], "section": sec, "material": MAT, "ref": [0, 1, 0]}
           for i in range(n)]
    sup = {f"n{i}": {"fix": "x z rx ry", "spring": [0, k * h * (0.5 if i in (0, n) else 1.0), 0, 0, 0, 0]}
           for i in range(n + 1)}
    P = 100.0
    r = solve({"nodes": nodes, "members": mem, "supports": sup, "loads": {f"n{n // 2}": [0, P, 0, 0, 0, 0]}})
    assert r.displacements[f"n{n // 2}"][1] == pytest.approx(P * lam / (2 * k), rel=0.02)
    assert abs(r.elem_forces[n // 2, 0, 5]) == pytest.approx(P / (4 * lam), rel=0.03)


def test_annular_plate_closed_form():
    # narrow annulus -> cantilever strip q (a - b)^2 / 2; Roark 2L K_Mrb(b/a 0.5, nu 0.3) = 0.1730
    assert hs.annular_plate_mrb(1.0, 1.0, 0.98, 0.3) == pytest.approx(0.02 ** 2 / 2, rel=0.03)
    assert hs.annular_plate_mrb(1.0, 1.0, 0.5, 0.3) == pytest.approx(0.1730, abs=0.002)


def test_load_sets_follow_rev_c():
    L = hs.load_sets()
    assert L["C2"].factor == pytest.approx(3.0) and L["C1"].factor == pytest.approx(2.0)
    assert L["walk"].T == pytest.approx(483.0)                 # worst B form (hipbelt_results.json)
    assert L["C2"].T >= L["walk"].T / 1.6 * 3.0                # 2.0 g x 1.5 on the 1 g need
    assert hs.lumbar_push(1.0) == pytest.approx(413.0, abs=1.0)  # hipbelt_fit.md: 413 N at 15 in
    assert L["C2"].V == pytest.approx(0.8 * 68 * 9.81 * 3.0, rel=1e-3)


def test_cp_model_equilibrium():
    cp = hs.CP_VARIANTS["as_drawn"]
    L = hs.load_sets()["walk"]
    m = hs.cp_model(cp, L, inplane=True)
    r = solve(m)
    F = np.zeros(6)
    for v in m["loads"].values():
        F += np.asarray(v)
    R = np.zeros(6)
    for v in r.reactions.values():
        R += np.asarray(v)
    assert np.allclose((F + R)[:3], 0.0, atol=1e-6 * max(1.0, np.abs(F).max()))
    # out of plane: the foundation carries H + 2 T sin(theta) (plate mode)
    springs_y = sum(v[1] for v in r.reactions.values())
    assert springs_y == pytest.approx(L.H + 2 * L.T * math.sin(math.radians(hs.THETA_ROOT_DEG)), rel=1e-6)


def test_centre_plate_as_drawn_fails_and_recommended_passes():
    bad = hs.cp_check(hs.CP_VARIANTS["as_drawn"])
    assert min(v["sf_over_req"] for v in bad.values()) < 0.5
    good = hs.cp_check(hs.CP_VARIANTS["recommended"])
    assert min(v["sf_over_req"] for v in good.values()) >= 1.0
    assert hs.CP_VARIANTS["recommended"].mass_g()["total_g"] < 100.0
    # the fit model's rigid-plate assumption: walking pressure under the plate stays below the 48.6 kPa limit
    assert good["walk"]["p_body_max_kpa"] < hb_limit()


def hb_limit():
    from huntkit.gendesign import hipbelt as hb
    return hb.P_HIP_PEAK_KPA


def test_curvature_is_the_lever_for_the_bowtie():
    from dataclasses import replace
    flat = hs.cp_check(replace(hs.CP_VARIANTS["recommended"], curve_deg=0.0))
    assert min(v["sf_over_req"] for v in flat.values()) < 1.0
    assert hs.theta_residual(hs.CP_VARIANTS["recommended"]) == pytest.approx(4.8, abs=0.1)


def test_stitched_ear_joint_passes_every_case():
    e = hs.ear_check(hs.CP_VARIANTS["recommended"])
    assert e["n_per_row"] == 22 and e["edge_mm"] == pytest.approx(8.0)
    assert e["min_sf"] >= 1.5
    c2 = e["cases"]["C2"]
    assert c2["f_hole_n"] < e["hole_cap_n"]


def test_two_to_one_routing_and_hardware():
    t = hs.tab_check()
    assert t["lock_leg_frac"] == pytest.approx(1 / 1.7)
    assert t["ladder_lock_heavy"]["slip_sf_walk"] >= 1.5            # materials-engineer criterion
    assert t["lock_if_routed_between_anchor_and_ring"]["slip_sf_walk"] < 1.1   # the text routing holds 1:1
    assert t["d_ring"]["sf"] >= 1.0 and t["buckle_50"]["sf"] >= 1.0 and t["box_x"]["sf"] >= 2.0


def test_hdpe_must_float():
    h = hs.hdpe_tab()
    assert h["share_if_fixed"] > 0.8
    assert h["fixed_creep_sf"] < 1.0                               # fastened both ends: tab holes creep


def test_pivot_augment_adds_axial_push_and_offset_moment():
    from huntkit.gendesign.lugs import LugSpec, Socket
    pin = Socket("pivot_pin", np.array([0, -1.0, 0]), 10.0, "pin", role="load")
    pin.loads["static_carry|15|HP"] = np.array([0, 0, 537.0, 0, 0, 0])
    sp = LugSpec("hip_pivot_mount", "t", [pin], case_req={"static_carry|15|HP": 2.0},
                 static_keys=["static_carry|15|HP"])
    a = pfe.augment(sp, e_pad=20.0)
    H = pfe.lumbar_push_n("static_carry", 15)
    assert H == pytest.approx(413.0, abs=1.0)
    up = a.sockets[0].loads["static_carry|15|HP|Hup"]
    assert up[1] == pytest.approx(H) and up[3] == pytest.approx(-20.0 * H) and up[2] == pytest.approx(537.0)
    assert "static_carry|15|HP|Hdn" in a.static_keys and a.case_req["static_carry|15|HP|Hdn"] == 2.0


def test_pivot_hand_checks():
    rec = hs.pivot_check(hs.CP_VARIANTS["recommended"])
    withH = hs.pivot_check(hs.CP_VARIANTS["recommended"], h_on_pivot=True)
    assert all(v["pin_sf"] >= 1.0 and v["hub_bearing_sf"] >= 1.0 for v in withH.values())
    assert rec["C2"]["H_n"] == 0.0 and withH["C2"]["H_n"] == pytest.approx(1239.4, abs=1.0)
    # H on the pin with the pad centroid 20 mm high raises the M5 prying above the no-H value
    assert withH["C2"]["m5_tension_n"] > rec["C2"]["m5_tension_n"]
