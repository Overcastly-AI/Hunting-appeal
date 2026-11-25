"""BL-070 H1 on PPA-CF and H1-P (huntkit.gendesign.bl070_h1p): the material swap, the layer rule per axis against
the record rule, the joint / insert capacities on PPA against hand values, the H1-P geometry rules (frozen interfaces,
wearer face), and the record (every HA-LS-1 row of H1-P >= its goal on the exported geometry, mass booked)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import bl070_h1p as P
from huntkit.gendesign import frame_h1 as H1
from huntkit.gendesign import frame_iter1 as FI

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------------------------------------ material
def test_ppa_values_from_record():
    m = P.materials()["ppa_design"]
    assert (m["s_xy"], m["s_z"], m["knock"], m["fat"], m["rho"]) == (168.0, 45.0, 0.73, 0.30, 1250.0)
    assert P.materials()["ppa_tds"]["s_z"] == 57.0
    # knocked design Z 32.85 MPa; BL-069 break-even for R1 on H1: 32.85 / 0.937 = 35.1 MPa
    assert m["knock"] * m["s_z"] == pytest.approx(32.85)
    assert P.e_buckle() == pytest.approx(11800 * 0.85 * 0.85)
    assert P.e_buckle() / FI.E_BUCKLE == pytest.approx(5.26, abs=0.01)


def test_material_context_swaps_and_restores():
    from huntkit.gendesign import frame_comp_d as D
    before = (H1.MAT, dict(H1.PAHT), FI.E_BUCKLE)
    with P.material("ppa_design"):
        assert H1.MAT == "ppa_design" and D.MATERIALS["ppa_design"]["s_z"] == 45.0
        assert H1.PAHT["s_z"] == 45.0 and H1.PAHT["E_hot"] == 0.85
        assert FI.E_BUCKLE == pytest.approx(P.e_buckle())
        cap = H1.joint_capacities()
    assert (H1.MAT, dict(H1.PAHT), FI.E_BUCKLE) == before
    cap0 = H1.joint_capacities()
    # plug shear-out is interlayer: x (0.73 x 45) / (0.8 x 47) = 0.874; washer bearing in the layers x 1.74
    assert cap["plug_shear_out_n"] / cap0["plug_shear_out_n"] == pytest.approx(0.73 * 45 / (0.8 * 47))
    assert cap["washer_bearing_n"] / cap0["washer_bearing_n"] == pytest.approx(0.73 * 168 / (0.8 * 88))


# ------------------------------------------------------------------------------------------------ layer rule
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_layer_terms_match_record_rule(axis):
    from huntkit.gendesign.frame_topopt import layer_failure_index
    rng = np.random.default_rng(axis)
    S = rng.normal(0, 30, (500, 6))
    m = P.materials()["ppa_design"]
    ref = layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), axis, m["s_xy"], m["s_z"], m["knock"])
    assert np.allclose(P.fi_layer(S, axis, m), ref)
    # per-voxel axes = the rule per voxel
    ax = rng.integers(0, 3, 500)
    mix = P.fi_layer(S, ax, m)
    for a in range(3):
        sel = ax == a
        assert np.allclose(mix[sel], layer_failure_index(np.abs(S[sel, :3]), np.abs(S[sel, 3:]), a, m["s_xy"],
                                                         m["s_z"], m["knock"]))


def test_interlayer_shear_term_by_hand():
    """tau_xy 10 MPa, layer normal y: 10 / (0.73 x 0.6 x 45) = 0.507; it is the governing term."""
    m = P.materials()["ppa_design"]
    S = np.zeros((1, 6))
    S[0, 3] = 10.0
    T = P.layer_terms(S, 1, m)
    assert T[2, 0] == pytest.approx(10.0 / (0.73 * 0.6 * 45.0))
    assert T[:, 0].argmax() == 2
    # with the layer normal along z, tau_xy is in-plane: sqrt(3) x 10 / (0.73 x 168)
    assert P.fi_layer(S, 2, m)[0] == pytest.approx(math.sqrt(3) * 10.0 / (0.73 * 168.0))


def test_margins_synthetic():
    """fatigue = fat / (FI99 x 1.6 / factor) from the static-carry set; strength = 1 / FI99."""
    n = 1000
    fi_sc = np.linspace(0, 1, n)
    f = {"meta": [{"scenario": "t", "case": "static_carry", "factor": 2.0, "set": "a"},
                  {"scenario": "t", "case": "drop_2p5g", "factor": 3.0, "set": "b"}],
         "ex": {"t": np.zeros(n, bool)}}
    m = {"fat": 0.3, "rup": 0.55}
    r = P.margins(f, [fi_sc, 0.5 * fi_sc], m)
    p99 = np.percentile(fi_sc, 99)
    assert r["strength"] == pytest.approx(1 / p99)
    assert r["fatigue"] == pytest.approx(0.3 / (p99 * 1.6 / 2.0))
    assert r["creep"] == pytest.approx(0.55 / (p99 / 2.0))


# ------------------------------------------------------------------------------------------------ inserts
def test_hip_inserts_paht_reproduces_bl055_and_ppa_needs_the_through_bolt():
    paht = P.hip_inserts("paht_fdm")["paht"]["min_sf"]
    assert paht["strength"] == pytest.approx(2.149, abs=1e-3)
    assert paht["fatigue"] == pytest.approx(1.208, abs=1e-3)
    h = P.hip_inserts("ppa_design")
    # HB-6 basis scaled by the knocked Z: 1200 x 0.73 x 45 / 88 = 448 N, under the 488 N the pattern needs
    assert h["abs_z"]["capacity"]["static_n"] == pytest.approx(1200 * 0.73 * 45 / 88, abs=0.2)
    assert h["hb6_ppa_min_static_n"] == pytest.approx(488.0, abs=1.0)
    assert h["abs_z"]["min_sf"]["fatigue"] < 1.15 and h["record_rule"]["min_sf"]["fatigue"] < 1.15
    assert h["through_bolt"]["pass"]
    ring = math.pi / 4 * (P.NUT_WASHER_OD ** 2 - P.NUT_HOLE_D ** 2)
    assert h["through_bolt"]["bearing_n"] == pytest.approx(ring * 0.73 * 45, abs=0.1)


# ------------------------------------------------------------------------------------------------ geometry rules
def test_shift():
    a = np.zeros((3, 3, 3), bool)
    a[1, 1, 1] = True
    assert P._shift(a, (0, 1, 0))[1, 2, 1] and P._shift(a, (0, 1, 0)).sum() == 1
    assert P._shift(a, (-1, 0, 0))[0, 1, 1]


def test_resize_step_keeps_frozen_voxels_and_the_wearer_face():
    s0 = FI.baseline_solid()
    g = FI._base()["dom"].grid
    u = np.zeros(g.ne, np.float32)               # nothing used: everything thinnable is a candidate
    new, rem, add = P.resize_step(s0, u, 0.5, 9.0)
    fr = P.frozen(s0)
    assert rem.sum() > 0 and not (rem & fr).any() and not add.any()
    S = g.to_array(s0)
    wear = g.from_array(S & ~P._shift(S, (0, 1, 0)))
    assert not (rem & wear).any()
    # growth stays in the design domain, out of the bores and joint holes
    u[s0] = 2.0
    _, _, add = P.resize_step(s0, u, 0.0, 1.0, thin=False)
    assert not (add & ~P.allowed_add()).any()


# ------------------------------------------------------------------------------------------------ record
REC = P.REC_JSON


@pytest.mark.skipif(not REC.exists(), reason="run python -m huntkit.gendesign.bl070_h1p report")
def test_record_h1p_rows_meet_goals_on_exported_geometry():
    r = json.loads(REC.read_text())
    h = r["h1p"]
    assert h["checked_on"].startswith("exported STL re-rastered")
    for row in h["rows"]:
        assert row["value"] >= row["goal"] - 1e-9, row
    assert h["rows_by_name"]["fatigue, cinch-cycled (R1)"]["value"] >= 1.0


@pytest.mark.skipif(not REC.exists(), reason="run python -m huntkit.gendesign.bl070_h1p report")
def test_record_mass_and_print_files():
    import trimesh
    r = json.loads(REC.read_text())
    h1 = r["h1_ppa"]["body_g"]
    assert h1 == pytest.approx(P.PAHT_BODY_G * 1.25 / 1.06, abs=0.5)
    m = trimesh.load(P.STL_DIR / "h1_assembled.stl", force="mesh")
    assert m.is_watertight
    assert r["h1p"]["body_g"] == pytest.approx(m.volume * P.RHO_PPA, abs=0.5)
    for nm in ("h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R"):
        assert trimesh.load(P.STL_DIR / f"{nm}.stl", force="mesh").is_watertight


@pytest.mark.skipif(not REC.exists(), reason="run python -m huntkit.gendesign.bl070_h1p report")
def test_checked_raster_is_the_exported_stl():
    """RUBRIC 1: the H1-P rows were computed on the exported assembled STL re-rastered, not on the design voxels."""
    r = json.loads(REC.read_text())
    npz = P.OUT / f"{r['h1p']['final_iter']}_solid.npz"
    if not npz.exists():
        pytest.skip("outputs/bl070 cache not present (scratch)")
    solid, _ = P.reraster()
    checked = np.load(npz)["solid"]
    assert np.array_equal(solid, checked)
