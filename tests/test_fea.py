"""Verification of huntkit.fea against closed-form solutions (tolerance 1-2 %)."""
import numpy as np
import pytest

from huntkit.fea import composite as clt
from huntkit.fea.fatigue import basquin, goodman_equivalent, rainflow
from huntkit.fea.frame import solve
from huntkit.fea.joints import bond_check, volkersen_factor
from huntkit.fea.plate import kirchhoff_plate, navier_ss_rect
from huntkit.fea.sections import composite_tube, flat_bar, tube_rect, tube_round

E, G = 70000.0, 26000.0
MAT = {"youngs_modulus_mpa": E, "shear_modulus_mpa": G, "yield_strength_mpa": 500.0,
       "density_kg_m3": 2800.0}
PLY = {"E1_mpa": 135000, "E2_mpa": 8800, "G12_mpa": 4500, "nu12": 0.3, "Xt_mpa": 2550,
       "Xc_mpa": 1470, "Yt_mpa": 69, "Yc_mpa": 200, "S_mpa": 90, "ply_thickness_mm": 0.125,
       "density_kg_m3": 1580}


def rel(a, b):
    return abs(a - b) / abs(b)


def beam(L, sec, nseg=4, supports=None, loads=None, mid=False):
    nodes = {"A": [0, 0, 0], "B": [L, 0, 0]}
    members = [{"id": "b", "nodes": ["A", "B"], "section": sec, "material": MAT, "nseg": nseg}]
    if mid:
        nodes = {"A": [0, 0, 0], "C": [L / 2, 0, 0], "B": [L, 0, 0]}
        members = [{"id": "b1", "nodes": ["A", "C"], "section": sec, "material": MAT, "nseg": nseg},
                   {"id": "b2", "nodes": ["C", "B"], "section": sec, "material": MAT, "nseg": nseg}]
    return {"nodes": nodes, "members": members, "supports": supports, "loads": loads}


def test_cantilever_tip_deflection_and_stress():
    s, L, P = tube_round(25.0, 1.5), 800.0, 150.0
    r = solve(beam(L, s, supports={"A": "fixed"}, loads={"B": [0, 0, -P, 0, 0, 0]}))
    exact = P * L ** 3 / (3 * E * s.Iy)
    assert rel(-r.displacements["B"][2], exact) < 0.01
    sig = P * L * (25.0 / 2) / s.Iy
    assert rel(r.critical_member["check"]["sigma"].__abs__(), sig) < 0.01
    assert rel(r.reactions["A"][2], P) < 1e-9          # equilibrium


def test_cantilever_rect_and_flat_lateral():
    for s in (tube_rect(20, 30, 1.5), flat_bar(25, 4)):
        L, P = 500.0, 50.0
        r = solve(beam(L, s, supports={"A": "fixed"},
                       loads={"B": [0, P, 0, 0, 0, 0]}))
        # load along global y; default ref = global Z -> local y = global Z, so bending about local y
        exact = P * L ** 3 / (3 * E * s.Iy)
        assert rel(r.displacements["B"][1], exact) < 0.01


def test_simply_supported_midspan():
    s, L, P = tube_round(20.0, 1.0), 1000.0, 200.0
    m = beam(L, s, mid=True, supports={"A": {"fix": "x y z rx"}, "B": {"fix": "y z"}},
             loads={"C": [0, 0, -P, 0, 0, 0]})
    r = solve(m)
    assert rel(-r.displacements["C"][2], P * L ** 3 / (48 * E * s.Iy)) < 0.01
    assert rel(r.reactions["A"][2] + r.reactions["B"][2], P) < 1e-9


def test_thin_tube_torsion():
    od, t, L, T = 30.0, 0.6, 600.0, 20000.0
    s = tube_round(od, t)
    Rm = (od - t) / 2
    J_thin = 2 * np.pi * Rm ** 3 * t
    r = solve(beam(L, s, supports={"A": "fixed"}, loads={"B": [0, 0, 0, T, 0, 0]}))
    assert rel(r.displacements["B"][3], T * L / (G * J_thin)) < 0.01
    tau_thin = T / (2 * np.pi * Rm ** 2 * t)              # Bredt
    assert rel(r.critical_member["check"]["torsion"], tau_thin) < 0.02


def test_euler_buckling_pinned_column():
    s, L = tube_round(16.0, 1.0), 900.0
    m = beam(L, s, nseg=10, supports={"A": {"fix": "x y z rx"}, "B": {"fix": "y z"}},
             loads={"B": [-1.0, 0, 0, 0, 0, 0]})
    r = solve(m, buckling=True)
    Pcr = np.pi ** 2 * E * s.Iy / L ** 2
    assert rel(r.buckling_factors[0], Pcr) < 0.01


def test_two_bar_truss():
    a, h, P = 400.0, 300.0, 1000.0
    A = 50.0
    from huntkit.fea.sections import generic
    sec = generic(A, 100.0, 100.0, 100.0)
    m = {"nodes": {"L": [-a, 0, 0], "R": [a, 0, 0], "T": [0, 0, h]},
         "members": [{"id": "l", "nodes": ["L", "T"], "section": sec, "material": MAT, "type": "truss"},
                     {"id": "r", "nodes": ["R", "T"], "section": sec, "material": MAT, "type": "truss"}],
         "supports": {"L": "pinned", "R": "pinned", "T": {"fix": "y"}},
         "loads": {"T": [0, 0, -P, 0, 0, 0]}}
    r = solve(m)
    Lb = np.hypot(a, h)
    sin = h / Lb
    F = P / (2 * sin)
    assert rel(-r.member_forces["l"]["start"][0], F) < 0.01          # compression
    assert rel(-r.displacements["T"][2], P * Lb / (2 * E * A * sin ** 2)) < 0.01


def test_spring_supports_and_inertia_relief():
    s, L, P = tube_round(20.0, 1.0), 500.0, 100.0
    m = beam(L, s, supports={"A": {"spring": [1e3] * 6}, "B": {"spring": [1e3] * 6}},
             loads={"B": [0, 0, -P, 0, 0, 0]})
    r = solve(m)
    assert rel(-sum(v[2] for v in r.reactions.values()), -P) < 1e-6
    # free-free bar with self-equilibrated axial loads: elongation = P L / EA
    m = beam(L, s, supports={}, loads={"A": [-P, 0, 0, 0, 0, 0], "B": [P, 0, 0, 0, 0, 0]})
    m["supports"] = None
    m["inertia_relief"] = True
    m["masses"] = {"A": 1.0, "B": 1.0, "b#2": 1.0} if False else {"A": 1.0, "B": 1.0}
    m["masses"]["A"] = 1.0
    # add a third non-collinear mass node via an extra member so rotations are defined
    m["nodes"]["C"] = [L / 2, 100.0, 0]
    m["members"].append({"id": "c", "nodes": ["A", "C"], "section": s, "material": MAT})
    m["masses"]["C"] = 1e-6
    r = solve(m)
    U = r.displacements
    assert rel(U["B"][0] - U["A"][0], P * L / (E * s.A)) < 0.01


def test_clt_quasi_isotropic_modulus():
    ply = clt.Ply.from_material(PLY)
    Eiso = clt.quasi_isotropic_modulus(ply)
    for lay in ("[0,±45,90]s", "[30,75,-15,-60]s"):
        eng = clt.Laminate.from_layup(lay, ply).engineering()
        assert rel(eng["Ex"], Eiso) < 0.01
        assert rel(eng["Ey"], Eiso) < 0.01
        assert rel(eng["Gxy"], Eiso / (2 * (1 + eng["nuxy"]))) < 0.01
    ud = clt.Laminate.from_layup("[0_4]", ply).engineering()
    assert rel(ud["Ex"], ply.E1) < 1e-9
    lam = clt.Laminate.from_layup("[0,±45,0,90]s", ply)
    assert np.allclose(lam.B, 0, atol=1e-6)
    assert len(lam.angles) == 10


def test_layup_parser():
    assert clt.parse_layup("[0,±45,0,90]s") == [0, 45, -45, 0, 90, 90, 0, -45, 45, 0]
    assert clt.parse_layup("[0/90]2") == [0, 90, 0, 90]


def test_tsai_wu_uniaxial_and_knockdown():
    ply = clt.Ply.from_material(PLY)
    assert abs(clt.tsai_wu_fi([ply.Xt, 0, 0], ply) - 1.0) < 1e-9
    assert abs(clt.tsai_wu_fi([-ply.Xc, 0, 0], ply) - 1.0) < 1e-9
    assert abs(clt.max_stress_fi([0, 0, ply.S], ply) - 1.0) < 1e-9
    kd = ply.knocked_down(clt.DEFAULT_KNOCKDOWN)
    assert abs(kd.Xc - ply.Xc * 0.8 * 0.65) < 1e-9
    # UD laminate under Nx: ply stress = Nx/t -> FI at Nx = Xt*t equals 1 (no knockdown)
    lam = clt.Laminate.from_layup("[0_4]", ply)
    r = lam.first_ply_failure((ply.Xt * lam.thickness, 0, 0), knockdown=None)
    assert abs(r["fi"] - 1.0) < 1e-6


def test_composite_tube_effective_properties():
    sec = composite_tube(12.7, "[0,±45,0,90]s", PLY, ply_t=0.1)
    eng = sec.laminate.engineering()
    st = sec.stiffness()
    assert rel(st["EA"], eng["Ex"] * sec.A) < 1e-12
    assert abs(sec.dims["t"] - 1.0) < 1e-12
    # pure axial load: tube FI equals laminate FI under Nx = N/(2 pi Rm)*... (consistent within 2 %)
    N = 1000.0
    r = sec.failure(N, 0, 0, 0, 0, 0)
    Nx = N / sec.A * sec.laminate.thickness
    r2 = sec.laminate.first_ply_failure((Nx, 0, 0))
    assert rel(r["fi"], r2["fi"]) < 1e-9


def test_plate_simply_supported_and_clamped():
    Ep, nu, t, q, a = 70000.0, 0.3, 2.0, 0.01, 100.0
    D = Ep * t ** 3 / (12 * (1 - nu ** 2))
    r = kirchhoff_plate(a, a, t, E=Ep, nu=nu, q=q, edges="ss")
    assert rel(r.w_max, navier_ss_rect(a, a, D, q)) < 0.01
    assert rel(r.M_max[0], 0.0479 * q * a ** 2) < 0.01             # Timoshenko beta
    rc = kirchhoff_plate(a, a, t, E=Ep, nu=nu, q=q, edges="clamped")
    assert rel(rc.w_max, 0.00126 * q * a ** 4 / D) < 0.01
    rr = kirchhoff_plate(2 * a, a, t, E=Ep, nu=nu, q=q, edges="ss")
    assert rel(rr.w_max, navier_ss_rect(2 * a, a, D, q)) < 0.01


def test_volkersen_and_bond():
    x = 3.0
    assert abs(volkersen_factor(x, 1.0) - (x / 2) / np.tanh(x / 2)) < 1e-12
    r = bond_check(N=1000, T=0, M=0, r=6.35, tube_Et=60000, tube_Gt=20000,
                   params={"adhesive": {"shear_modulus_mpa": 700, "lap_shear_strength_mpa": 20},
                           "overlap_mm": 25, "adhesive_t_mm": 0.15})
    assert rel(r.tau_avg, 1000 / (2 * np.pi * 6.35 * 25)) < 1e-9
    assert r.tau_peak > r.tau_avg


def test_fatigue_helpers():
    c = basquin(572.0, 159.0, Ne=5e8)
    assert rel(c.life(159.0), 5e8) < 1e-6
    assert rel(c.life(0.9 * 572.0), 1e3) < 1e-6
    assert goodman_equivalent(100, 286, 572) == pytest.approx(200)
    # ASTM E1049 example sequence
    cyc = rainflow([-2, 1, -3, 5, -1, 3, -4, 4, -2])
    full = sorted(r for r, m, n in cyc if n == 1.0)
    half = sorted(r for r, m, n in cyc if n == 0.5)
    assert full == [4.0]
    assert half == sorted([3, 4, 8, 9, 8, 6])


def test_pack_standard_cases_and_frame():
    from huntkit.fea.frames import aluminum_baseline, carbon_variant
    from huntkit.fea.load_cases import pack_standard
    cases = {c.name: c for c in pack_standard()}
    assert {"static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown",
            "meat_shelf_heavy_low", "tall_load", "overload_haul"} <= set(cases)
    assert cases["overload_haul"].required_sf == 1.5
    fm = aluminum_baseline(torso_in=19)
    r = cases["drop_2p5g"].run(fm)
    assert abs(r.meta["hip_fraction"] - 0.80) < 0.01
    # total vertical reaction balances the 2.5 g load
    assert rel(sum(v[2] for v in r.reactions.values()), 68 * 9.80665 * 2.5) < 1e-6
    r2 = cases["static_carry"].run(fm)
    assert rel(r.min_sf * 2.5, r2.min_sf) < 0.05      # linear in load (spring split recalibrated)
    fc = carbon_variant(torso_in=23)
    assert fc["warnings"]                              # 560 mm frame too short for a 23 in torso
    rs = cases["single_stay_setdown"].run(carbon_variant())
    assert np.isfinite(rs.min_sf) and rs.min_sf > 0
