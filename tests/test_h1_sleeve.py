"""BL-024: H1 body sleeve / crown-leg seat redesign on the cloth-sim loads (huntkit/gendesign/h1_sleeve.py).

Closed-form solver checks for the voxel H8 model (cantilever vs Timoshenko, square-bar torsion) are in
tests/test_frame_topopt.py; here the one new solver path (per-element stiffness weights, used for the liner trial)
is checked against a two-material cantilever, plus this module's mapping rules and its record.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import frame_topopt as ft
from huntkit.gendesign import h1_sleeve as M
from huntkit.gendesign.fem import Grid, ke_h8

REC = Path(M.RESULTS)


@pytest.fixture(scope="module")
def res():
    if not REC.exists():
        pytest.skip("run python -m huntkit.gendesign.h1_sleeve first")
    return json.loads(REC.read_text())


def test_weighted_voxel_cantilever_vs_two_segment_timoshenko():
    """Root half w = 5 x stiffer: tip deflection = P int (L-x)^2 / EI(x) dx + P int dx / (k G(x) A)."""
    E, nu, L, a, P, w = 1000.0, 0.3, 120.0, 12.0, 1.0, 5.0
    h = 1.5
    g = Grid((int(L / h), int(a / h), int(a / h)), h)
    nc = g.node_coords()
    fixed = np.zeros(g.ndof, bool)
    root = np.where(np.isclose(nc[:, 0], 0))[0]
    for d in range(3):
        fixed[3 * root + d] = True
    tip = np.where(np.isclose(nc[:, 0], L))[0]
    F = np.zeros((g.ndof, 1))
    F[3 * tip + 2, 0] = -P / tip.size
    wt = np.where(g.elem_centers()[:, 0] < L / 2, w, 1.0)
    rs = ft.ReducedSystem(g, np.ones(g.ne, bool), fixed, ke_h8(g.h, E, nu))
    U = rs.solve(rs.assemble(wt[rs.ae]), F)
    defl = -U[3 * tip + 2, 0].mean()
    I, A = a ** 4 / 12, a * a
    G = E / (2 * (1 + nu))
    x1 = L / 2
    bend = P / (w * E * I) * (L ** 3 - (L - x1) ** 3) / 3 + P / (E * I) * (L - x1) ** 3 / 3
    shear = P * x1 / (5 / 6 * w * G * A) + P * (L - x1) / (5 / 6 * G * A)
    assert defl == pytest.approx(bend + shear, rel=0.06)
    # and it differs clearly from the uniform bar (the weight is really applied)
    U1 = rs.solve(rs.assemble(np.ones(rs.ae.size)), F)
    assert -U1[3 * tip + 2, 0].mean() > 1.5 * defl


def test_sim_torso_mapping():
    assert [M.sim_torso(t) for t in (15, 17.5, 18, 19, 20, 20.5, 23)] == [15, 19, 19, 19, 19, 19, 23]
    assert M.sim_torso(18, alt=True) == 15
    assert M.sim_torso(20.5, alt=True) == 23
    assert M.sim_torso(23, alt=True) == 23


def test_kit_settings_cover_the_owner_kits():
    from huntkit.gendesign import crown_diet as CD
    for k, sz in (("a_S", "S"), ("a_M", "M"), ("a_L", "L")):
        lo, hi = CD.SIZES[sz]
        assert min(M.KITS[k]) == lo and max(M.KITS[k]) == hi


def test_liner_stiffness_equivalence_and_mass():
    """Liner ring weight gives the ring the tube's EI; added mass = tube - removed PAHT ring, both stays."""
    from huntkit.gendesign import frame_h1 as H1
    from huntkit.gendesign import crown_diet as CD
    solid = CD._h1_solid() if (H1.OUT / "h1_final.npz").exists() else None
    if solid is None:
        pytest.skip("H1 solid not generated (outputs/ untracked)")
    w, ring, added, wl = M.liner_weights(solid)
    lin = M.LINER
    I_tube = np.pi / 4 * ((lin["od"] / 2) ** 4 - (lin["od"] / 2 - lin["t"]) ** 4)
    I_ring = np.pi / 4 * (11.0 ** 4 - 9.0 ** 4)
    assert wl * M.E_PAHT * I_ring == pytest.approx(lin["E"] * I_tube, rel=1e-9)
    hand = 2 * 384.0 * (np.pi * (10 ** 2 - 9 ** 2) * 2.70e-3 - np.pi * (10 ** 2 - 9 ** 2) * 1.06e-3)
    assert added == pytest.approx(hand, rel=1e-6)
    assert ring.sum() > 0 and np.all(w[ring] == wl)


def test_region_labels():
    assert M.region([-103.0, -9.0, 167.0]) == "stay sleeve z 160-240"
    assert M.region([-110.0, 0.0, 300.0]) == "stay sleeve z 240-470"
    assert M.region([-110.0, 0.0, 520.0]) == "stay top z 470-544"
    assert M.region([-60.0, -10.0, 140.0]) == "lumbar struts / pan"


def test_reproduces_bl021(res):
    """H1 (one crown) on BL-021's fine basis, cinch static: 1.001 at 23 in meat, as BL-021 recorded."""
    rep = res["reproduce"]
    assert rep["fatigue"] == pytest.approx(1.001, abs=0.002)
    assert rep["torso"] == 23 and "meat" in rep["tag"]


def test_governing_population_is_not_the_crown_bore(res):
    """The 1 % most-utilised voxels of the governing set: shares sum to 1; the bore above z 240 holds almost none."""
    loc = res["location"]["top_regions"]
    assert sum(v["share_top"] for v in loc.values()) == pytest.approx(1.0, abs=0.01)
    assert loc["stay sleeve z 240-470"]["share_top"] + loc["stay top z 470-544"]["share_top"] < 0.02
    assert loc["lumbar struts / pan"]["share_top"] > 0.4


def test_sm8_basis_is_not_lighter_than_fine(res):
    b = res["baseline"]
    assert b["fine_sm8"]["min"]["fatigue"] <= b["fine"]["min"]["fatigue"] + 1e-9


def test_recommended_design_claims(res):
    """Whatever the recommendation is, its stated pass / fail matches its own numbers."""
    rc = res["recommended"]
    ok = rc["fatigue_min_sim"] >= M.FAT_REQ and rc["strength_min"] >= M.STR_REQ
    assert rc["passes"] == ok
    assert rc["ca1_flip"] == pytest.approx(M.PAHT_FAT / rc["fatigue_min_sim"], rel=1e-6)
    assert rc["added_g"] >= 0.0
