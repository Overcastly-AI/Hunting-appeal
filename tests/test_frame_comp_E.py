"""Team E (FIBRE / LOOM) verification: the printed continuous-fibre section model and its use in the beam solver,
checked against closed-form solutions (cantilever, Euler buckling, rectangular shear, thin-wall torsion,
transformed section). Fast (< 10 s); the full rev C run is `python -m huntkit.gendesign.frame_comp_e`."""
import numpy as np
import pytest

from huntkit.fea.frame import solve
from huntkit.gendesign import frame_comp_e as E


def rel(a, b):
    return abs(a - b) / abs(b)


def matrix_only(b=12.0, h=20.0, d=0.1):
    """No fibre, solid core: a homogeneous Onyx rectangle."""
    return E.printed_section(b, h, tf=0.0, nr=0, rho_c=1.0, d=d)


def test_homogeneous_section_matches_rectangle():
    b, h = 12.0, 20.0
    s = matrix_only(b, h)
    assert rel(s.EA, E.E_M * b * h) < 1e-3
    assert rel(s.EIy, E.E_M * b * h ** 3 / 12) < 1e-3
    assert rel(s.EIz, E.E_M * h * b ** 3 / 12) < 1e-3
    assert rel(s.mass_g_per_mm, E.RHO_M * b * h * 1e-6) < 1e-3
    assert s.fibre_mm2 == 0.0


def test_rectangular_shear_is_1p5_V_over_A():
    b, h, V = 12.0, 20.0, 1000.0
    s = matrix_only(b, h)
    assert rel(V * s._qmax("z"), 1.5 * V / (b * h)) < 0.02
    assert rel(V * s._qmax("y"), 1.5 * V / (b * h)) < 0.02


def test_transformed_section_flanges_parallel_axis():
    """Fibre flanges of width (b - 2 WALL), thickness tf under a SKIN: EIy by hand (parallel axis)."""
    b, h, tf = 16.0, 22.0, 1.0
    s = E.printed_section(b, h, tf=tf, nr=0, rho_c=1.0, d=0.05)
    wf = b - 2 * E.WALL
    zc = h / 2 - E.SKIN - tf / 2
    If = 2 * (wf * tf ** 3 / 12 + wf * tf * zc ** 2)
    hand = E.E_M * (b * h ** 3 / 12 - If) + E.E_F * If
    assert rel(s.EIy, hand) < 0.01
    assert rel(s.fibre_mm2, 2 * wf * tf) < 0.01


def test_flange_stress_from_moment():
    b, h, tf, M = 16.0, 22.0, 1.0, 20000.0
    s = E.printed_section(b, h, tf=tf, nr=0, rho_c=1.0, d=0.05)
    c = s.components(0, 0, 0, 0, M, 0)
    zmax = h / 2 - E.SKIN
    assert rel(c["sig_f_t"], E.E_F * M * zmax / s.EIy) < 0.01
    assert rel(c["sig_f_c"], c["sig_f_t"]) < 1e-6


def test_fi_batch_equals_fi():
    s = E.sections()["stay_upper"]
    rng = np.random.default_rng(1)
    F = rng.normal(0, 1, (6, 6)) * [300, 200, 400, 3000, 30000, 15000]
    a = s.fi_batch(F, 1.5)
    for i, f in enumerate(F):
        b = s.fi(*f, factor=1.5)
        for k in b:
            assert abs(a[k][i] - b[k]) < 1e-9 + 1e-9 * abs(b[k])


def test_bredt_box_torsion():
    """Closed box round a bore: J by Bredt; walls of the sleeve give the stress q / t."""
    s = E.printed_section(26.0, 26.0, tf=0.0, nr=0, bore=18.0, rho_c=1.0)
    t = 4.0
    Am = 22.0 * 22.0
    J = 4 * Am ** 2 / (4 * 22.0 / t)
    assert rel(s.J, J) < 1e-9
    tz, ty = s._torsion(10000.0)
    assert rel(tz, 10000.0 / (2 * Am * t)) < 1e-9


def _beam(sec, L=500.0, nseg=8):
    return {"nodes": {"A": [0, 0, 0], "B": [0, 0, L]},
            "members": [{"id": "b", "nodes": ["A", "B"], "section": sec, "material": None, "nseg": nseg,
                         "ref": [1.0, 0.0, 0.0], "group": "stay_upper_L"}],
            "supports": {"A": "fixed"}}


def test_cantilever_with_printed_section():
    """A stay-like vertical cantilever (ref = frame x): a y tip load bends it about local y (EIy)."""
    sec = E.sections()["stay_upper"]
    L, P = 500.0, 100.0
    m = _beam(sec, L)
    m["loads"] = {"B": [0, P, 0, 0, 0, 0]}
    r = solve(m)
    exact = P * L ** 3 / (3 * sec.EIy)
    assert rel(abs(r.displacements["B"][1]), exact) < 0.01
    # the member check uses the printed section's own failure model
    chk = r.critical_member["check"]
    assert chk["mode"] in ("fibre_t", "fibre_c", "interlayer", "inplane_shear", "matrix")


def test_euler_buckling_with_printed_section():
    sec = E.sections()["mid_bar"]
    L, P = 400.0, 100.0
    m = _beam(sec, L, nseg=16)
    m["loads"] = {"B": [0, 0, -P, 0, 0, 0]}
    r = solve(m, buckling=True)
    Pcr = np.pi ** 2 * min(sec.EIy, sec.EIz) / (4 * L ** 2)
    assert rel(r.buckling_sf * P, Pcr) < 0.02


def test_knockdowns_and_allowables():
    xt, xc = E.fibre_allow()
    assert rel(xt, 800 * 0.8 * 0.85) < 1e-9
    assert rel(xc, 320 * 0.8 * 0.65 * 0.85) < 1e-9
    ma = E.matrix_allow()
    assert rel(ma["ilss"], 14.0 * 0.6) < 1e-9


def test_splice_and_pawl_checks_scale_linearly():
    a = E.splice_check([100, 50, 80, 1000, 20000, 5000], 1.0)
    b = E.splice_check([100, 50, 80, 1000, 20000, 5000], 2.0)
    assert rel(b["fi_bearing"], 2 * a["fi_bearing"]) < 1e-9
    p1, p2 = E.pawl_check([1000.0, 0.0]), E.pawl_check([2000.0, 0.0])
    assert rel(p2["fi_loop"], 2 * p1["fi_loop"]) < 1e-9


def test_sleeve_ring_point_load():
    """Ring under a diametral load: M = 0.318 F R per unit length (Roark), stress 6 M / t^2."""
    c = E.sleeve_check(700.0, "low")
    p = E.DESIGN["stay_upper"]
    t = (p["b"] - p["bore"]) / 2
    R = p["bore"] / 2 + t / 2
    assert rel(c["sigma_mpa"], 6 * 0.318 * 700.0 * R / E.BUSH_LEN / t ** 2) < 1e-9


@pytest.mark.parametrize("torso", [19.0])
def test_model_swaps_every_printed_member(torso):
    m = E.model(torso)
    groups = {x["group"] for x in m["members"] if isinstance(x["section"], E.PrintedSection)}
    for g in ("stay_lower_L", "stay_upper_R", "stay_top_L", "mid_bar", "upper_bar", "lumbar_rib",
              "lumbar_spine", "lumbar_tie"):
        assert g in groups
    ms = E.mass()
    assert ms["frame_g"] > ms["body_g"] > 0
