"""Team C (ROD) checks: solver closed forms on the stock tube section, and the joint mechanics in
huntkit/gendesign/frame_comp_C.py against hand calculations."""
import math

import numpy as np
import pytest

from huntkit.fea.frame import solve
from huntkit.fea.sections import from_spec
from huntkit.gendesign import frame_comp_C as C


def rel(a, b):
    return abs(a - b) / abs(b)


def _beam(L, sec, supports, loads, nseg=8):
    return {"nodes": {"A": [0, 0, 0], "B": [L, 0, 0]},
            "members": [{"id": "b", "nodes": ["A", "B"], "section": sec, "material": None, "nseg": nseg}],
            "supports": supports, "loads": loads}


@pytest.fixture(scope="module")
def stay():
    return from_spec(C.RW46710)


def test_stock_tube_section(stay):
    # Rock West 46710 modelled with repo plies: 3 UD0 + 2 UD90 + twill = 0.845 mm (vendor 1.0: conservative)
    assert stay.dims["od"] == 20.0
    assert abs(stay.dims["t"] - 0.845) < 1e-6
    assert 50000 < stay.Ex < 90000           # vendor CLT Ex 9.18 Msi = 63 GPa


def test_cantilever_composite_tube(stay):
    L, P = 500.0, 100.0
    r = solve(_beam(L, stay, {"A": "fixed"}, {"B": [0, 0, -P, 0, 0, 0]}))
    assert rel(-r.displacements["B"][2], P * L ** 3 / (3 * stay.Ex * stay.Iy)) < 0.01
    assert rel(r.reactions["A"][2], P) < 1e-9


def test_euler_buckling_composite_tube(stay):
    L, P = 530.0, 100.0
    m = _beam(L, stay, {"A": {"fix": "x y z rx"}, "B": {"fix": "y z"}}, {"B": [-P, 0, 0, 0, 0, 0]}, nseg=16)
    r = solve(m, buckling=True)
    Pcr = math.pi ** 2 * stay.Ex * stay.Iy / L ** 2
    assert rel(r.buckling_sf * P, Pcr) < 0.02


def test_thin_wall_torsion(stay):
    L, T = 400.0, 5000.0
    r = solve(_beam(L, stay, {"A": "fixed"}, {"B": [0, 0, 0, T, 0, 0]}))
    J = stay.J
    G = stay.Gxy
    assert rel(r.displacements["B"][3], T * L / (G * J)) < 0.02


def test_socket_contact_equilibrium_and_closed_form():
    L, V, M = 55.0, 300.0, 20000.0
    q, Mi = C.socket_contact(0.0, M, L)
    assert rel(q, 6 * M / L ** 2) < 1e-9        # pure moment: linear contact, peak 6M/L^2
    assert Mi(L) < 1e-6 * M                     # moment fully transferred at the tip
    assert rel(Mi(0.0), M) < 1e-9
    q2, Mi2 = C.socket_contact(V, M, L)
    assert rel(q2, 4 * V / L + 6 * M / L ** 2) < 1e-9
    assert Mi2(L) < 1e-6 * M


def test_pin_checks_hand_calc(stay):
    N, T = 400.0, 6000.0
    p = C.pin_checks(N, T, stay, e_end=12.0)
    t, d = stay.dims["t"], C.GEO["pin_d"]
    Fw = math.hypot(N / 2, T / (20.0 - t))
    assert rel(p["Fw"], Fw) < 1e-12
    assert rel(p["cf_bearing"], C.BEAR_CF * d * t / Fw) < 1e-12
    assert rel(p["shear_out"], C.SHEAR_CF_TUBE * 2 * (12.0 - d / 2) * t / Fw) < 1e-12


def test_hole_on_neutral_axis_beats_extreme_fibre(stay):
    a = np.array([0.0, 0.0, 1.0])
    F = np.zeros(3)
    M = np.array([20000.0, 0.0, 0.0])           # bending about x: extreme fibres at +-y
    on_na = C.tube_fpf_at_hole(stay, a, F, M, (1.0, 0.0, 0.0))
    at_fibre = C.tube_fpf_at_hole(stay, a, F, M, (0.0, 1.0, 0.0))
    assert on_na > 2.0 * at_fibre


def test_hole_axial_matches_laminate(stay):
    a = np.array([0.0, 0.0, 1.0])
    N = -5000.0
    sf = C.tube_fpf_at_hole(stay, a, np.array([0, 0, N]), np.zeros(3), (1.0, 0.0, 0.0))
    t = stay.dims["t"]
    nx = N / stay.A * t
    ref = min(stay.laminate.first_ply_failure((nx, 0, 0))["sf"], stay.laminate.first_ply_failure((-nx, 0, 0))["sf"])
    assert rel(sf, ref * C.NOTCH) < 1e-9


def test_belleville_keeps_preload():
    pc = C.preload_creep()
    assert pc["loss_plain_frac"] > 0.5            # plain Ti bolt on PAHT: creep takes most of the preload
    assert pc["loss_belleville_frac"] < 0.2       # the Belleville pair keeps it


def test_model_has_no_bonded_frame_joints():
    m = C.build(C.rod_candidate(), 19.0)
    assert all(j["id"].startswith(("crown_corner", "post_socket")) for j in m["joints"])
    assert len(m["rod_knuckles"]) == 4
    assert any(md["group"] == "lug_neck" for md in m["members"])


def test_one_case_runs_and_passes():
    from huntkit.fea.load_standard import ls1_envelope
    case = next(c for c in ls1_envelope("C")["crown_bar"] if c.name == "static_carry")
    row = C.run_case(C.rod_candidate(), 19.0, "crown_bar", case)
    assert min(v[0] for v in row["joints"].values()) >= 1.0
    assert min(v[0] for v in row["members"].values()) >= 1.0
    assert "fatigue" in row and "creep" in row


def test_result_json_schema():
    import json
    p = C.RESULT_JSON
    if not p.exists():
        pytest.skip("run python -m huntkit.gendesign.frame_comp_C first")
    r = json.loads(p.read_text())
    keys = {"team", "concept_name", "one_line", "frame_g", "frame_plus_spreader_g", "pack_mass_corrie_b2_M_g",
            "passes_rev_c", "worst_strength_margin", "worst_fatigue_margin", "worst_joint_margin", "governing_case",
            "torsion_stiffness_vs_today", "print_hours", "printer", "cost_usd", "build_hours", "skill_level",
            "looks_generative", "patents_checked", "governing_assumptions", "coupon_tests"}
    assert set(r) == keys
    assert rel(r["pack_mass_corrie_b2_M_g"], 3964.5 - (1225.0 - r["frame_plus_spreader_g"])) < 1e-3
    assert set(r["cost_usd"]) == {"1", "10", "100"}
