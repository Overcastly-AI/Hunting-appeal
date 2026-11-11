"""BL-007 fixed-torso frame study (huntkit.gendesign.frame_fixed): model changes, hand checks, mass booking."""
import json
import math

import numpy as np
import pytest

from huntkit.gendesign import frame_fixed as F
from huntkit.gendesign import frame_h1 as H1


@pytest.fixture(scope="module")
def models():
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.gendesign import frame_cg_recheck as R
    from huntkit.gendesign import frame_topopt as ft
    base = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0), 95.0)
    return base, F.modify_model(base, "fixed"), F.modify_model(base, "printed")


def test_fixed_model_links(models):
    base, fx, _ = models
    links = {ln["id"]: ln for ln in fx["links"]}
    # leg bottom moved into the socket, axial taken by the cross-bolts, not by the spine guide
    assert fx["nodes"]["CRbot"] == fx["nodes"][f"SR{F.SOCKET_LOW_Z:g}"]
    assert links["bush_low_R"]["k"][2] == F.K_BOLT_AX
    assert links["bush_top_R"]["k"][2] == 0
    assert links["pawl"]["k"][2] == 0 and links["pawl"]["k"][0] > 0
    # the input model is not mutated
    assert {ln["id"]: ln for ln in base["links"]}["pawl"]["k"][2] > 0


def test_printed_model_sections(models):
    _, _, pr = models
    legs = [m for m in pr["members"] if m["group"].startswith("crown_leg")]
    assert legs and all(m["section"]["type"] == "tube_round" for m in legs)
    assert all(m["material"].require("youngs_modulus_mpa") == pytest.approx(3860.0) for m in legs)
    assert not any(j["id"].startswith("crown_corner") for j in pr["joints"])
    kd = F._paht_beam_material(F.BUCKLE_E_KD)
    assert kd.require("youngs_modulus_mpa") == pytest.approx(3860.0 * 0.42)


def test_axial_load_moves_from_pawl_to_legs(models):
    """Static carry at 19 in: the crown's axial load (on the pawl in H1) goes to the leg cross-bolts; the total is
    about the same (load path re-routed, not lost)."""
    from huntkit.fea.load_standard import ls1_envelope
    base, fx, _ = models
    case = next(c for c in ls1_envelope("C")["crown_bar"] if c.name == "static_carry")
    r0, r1 = case.run(base), case.run(fx)
    lf0, lf1 = r0.meta["link_forces"], r1.meta["link_forces"]
    ax0 = float(lf0["pawl"][2])
    ax1 = float(lf1["bush_low_L"][2] + lf1["bush_low_R"][2])
    assert abs(float(lf1["pawl"][2])) < 1e-6
    assert abs(ax1) == pytest.approx(abs(ax0), rel=0.15)


def test_leg_length_closed_form():
    from huntkit.gendesign.frame_topopt import load_envelope
    env = load_envelope()
    uz = 1 / math.sqrt(1 + env.axis_slope ** 2)
    assert F._leg_len_mm(19.0, "a") == pytest.approx((702.6 - 400.0) / uz, abs=0.5)
    assert F._leg_len_mm(15.0, "a") < F._leg_len_mm(23.0, "a") < 430.0


def test_printed_leg_fi_closed_form():
    leg = {"od": 34.0, "t": 3.5}
    A = math.pi / 4 * (34 ** 2 - 27 ** 2)
    N = 1000.0
    assert F.printed_leg_fi([N, 0, 0, 0, 0, 0], leg) == pytest.approx(N / A / (0.8 * 88.0), rel=1e-6)
    I = math.pi / 64 * (34 ** 4 - 27 ** 4)
    M = 50e3
    assert F.printed_leg_fi([0, 0, 0, 0, M, 0], leg) == pytest.approx(M * 17 / I / (0.8 * 88.0), rel=1e-6)
    T = 20e3
    tau = T * 17 / (2 * I)
    assert F.printed_leg_fi([0, 0, 0, T, 0, 0], leg) == pytest.approx(tau / (0.8 * 0.6 * 47.0), rel=1e-6)


def _row(case="hipbelt_off_abuse", factor=1.0, axial=0.0, radial=0.0, at_top=(0, 0, 0, 0, 0, 0)):
    s = {"low_radial_n": radial, "axial_n": axial, "top_radial_n": radial}
    ls = {"at_bolt": [axial, 0, 0, 0, 0, 0], "at_stay_top": list(at_top), "printed_max_abs": list(at_top),
          "corner_bar_end": [0, 0, 0, 0, 0, 0]}
    return {"scenario": "C", "case": case, "torso": 19.0, "factor": factor,
            "extra": {"socket": {"L": s, "R": s}, "leg_sections": {"L": ls, "R": ls}}}


def test_socket_bolt_shear_hand_check():
    rows = [_row(axial=1000.0)]
    rows += [dict(r, scenario="C_im3") for r in rows]
    rows += [_row(case="static_carry", factor=2.0, axial=100.0), dict(_row(case="static_carry", factor=2.0, axial=100.0), scenario="C_im3")]
    sc = F.socket_checks(rows)
    cap = 2 * 2 * 0.6 * 895.0 * math.pi / 4 * 4.13 ** 2
    assert sc["capacities_n"]["cross-bolt Ti double shear"] == pytest.approx(cap, rel=1e-3)
    assert sc["C"]["strength"]["cross-bolt Ti double shear"]["margin"] == pytest.approx(cap / 1000.0, rel=1e-3)


def test_leg_joint_pure_tension_shares_bolts():
    """Pure tension N on the z 544 flange: 4 symmetric bolts each take N / 4 (x prying 1.25)."""
    N = 4000.0
    rows = [_row(at_top=(N, 0, 0, 0, 0, 0)), _row(case="static_carry", factor=2.0, at_top=(N / 10, 0, 0, 0, 0, 0))]
    jc = F.leg_joint_check(rows, F.PRINT_LEG)
    cap = math.pi / 4 * (12 ** 2 - 5.1 ** 2) * 0.8 * 88.0
    assert jc["strength"]["washer bearing (XY)"]["margin"] == pytest.approx(cap / (N / 4 * H1.PRYING), rel=0.02)


def test_mass_booking_items():
    from huntkit.mass import ledger as L
    h1 = F.frame_mass("h1", 19.0, 757.0, 757.0)
    assert h1["frame_g"] == pytest.approx(1025.1, abs=0.2)            # frame_mass_h1.json, via the ledger rows
    assert h1["pack_g"] == pytest.approx(L.total("corrie_b2_h1", "M"), abs=0.1)
    lb = F.ledger_basis()
    a = F.frame_mass("a", 19.0, 757.0, 757.0)
    gpm = F.leg_g_per_mm()
    assert gpm == pytest.approx(88.1166 / 860.0, rel=1e-3)
    expect = 1025.1 + 2 * gpm * (F._leg_len_mm(19.0, "a") - 430.0) - 44.0
    from huntkit.gendesign.frame_comp_B import bolt_mass_g
    nut, washer = F.nut_washer_g()
    expect += -F.BUSHINGS_G * (1 - 200.0 / 280.0) + 4 * (bolt_mass_g(30.0) + nut + washer) + F.YOKE_STRIP_G
    assert a["frame_g"] == pytest.approx(expect, abs=0.3)
    assert a["frame_g"] == pytest.approx(sum(a["items"].values()), abs=0.05)
    assert a["pack_g"] == pytest.approx(h1["pack_g"] + (a["frame_g"] - h1["frame_g"]) - lb["torso_adjust_g"], abs=0.2)
    assert lb["torso_adjust_g"] == pytest.approx(41.7, abs=0.05)
    assert F.frame_mass("a", 15.0, 757.0, 757.0)["frame_g"] < a["frame_g"] < F.frame_mass("a", 23.0, 757.0, 757.0)["frame_g"]


def test_fit_table():
    ft = F.fit_table()
    assert ft["sizes_for_15_23_in"] == 4
    assert ft["fine_adjust_mm"] == [-25.4, 25.4]


def test_results_if_present():
    """Regression on the written record: H1 reproduced, every variant reports every margin."""
    if not F.RESULT.exists():
        pytest.skip("run python -m huntkit.gendesign.frame_fixed all")
    r = json.loads(F.RESULT.read_text())
    rep = r["h1_reproduced"]
    assert rep["reproduced"]
    assert rep["min"]["strength"] == pytest.approx(1.45, abs=0.01)
    assert rep["min"]["fatigue"] == pytest.approx(1.28, abs=0.01)
    for v in ("a", "b", "c"):
        V = r["variants"][v]
        for k in ("strength", "fatigue", "creep"):
            assert np.isfinite(V["body"]["min"][k])
        assert np.isfinite(V["body"]["buckling_min"]) and np.isfinite(V["body"]["joint"]["min_fatigue"])
        assert "crown" in V["beam"]
    assert r["variants"]["c"]["mass"]["19"]["frame_g"] <= r["variants"]["a"]["mass"]["19"]["frame_g"]


def test_clean_mesh_drops_islands():
    import trimesh
    big = trimesh.creation.box((40, 40, 40))
    small = trimesh.creation.box((5, 5, 5))
    small.apply_translation((100, 0, 0))
    out = F.clean_mesh(trimesh.util.concatenate([big, small]))
    assert len(out.split(only_watertight=False)) == 1
    assert out.volume == pytest.approx(64000.0, rel=1e-6)
