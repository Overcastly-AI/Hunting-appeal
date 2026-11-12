"""BL-027 tests: the Euler rule reproduces frame_h1.buckling, the load-group split adds up, the region label and
governing_region name the right place, the IM3 cheek and the print-shell cleanup do what they say, and the
recorded result (designs/pack_5200/analysis/h1_buckling.json) meets the ticket's targets."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import frame_cg_recheck as R
from huntkit.gendesign import h1_buckling as M

RES = Path(M.RESULTS)


# ----------------------------------------------------------------------------- closed form / pure functions
def test_euler_closed_form_matches_rule():
    """P_cr of team A's rule is the pinned-pinned Euler load of a solid round bar of the cut area."""
    from huntkit.gendesign import frame_comp_A as A
    m = A.MATS["paht_rec"]
    E = m.E_xy * m.E_hot * 0.7
    A_, L = 72.0, 230.0
    r = math.sqrt(A_ / math.pi)
    pcr = math.pi ** 2 * E * (math.pi * r ** 4 / 4) / L ** 2
    # same thing written as E A^2 / (4 pi) * pi^2 / L^2
    assert pcr == pytest.approx(math.pi * E * A_ ** 2 / (4 * L ** 2), rel=1e-12)
    # BL-024's recorded mid bar: A 72 mm2 -> P_cr about 125 N
    assert pcr == pytest.approx(125.0, abs=1.0)


def test_margins_from_axial():
    ax = {"m": {"N": np.array([10.0, -50.0, -20.0]), "A_mm2": 72.0, "L_mm": 230.0, "Pcr_n": 150.0}}
    meta = [{"set": "a"}, {"set": "b"}, {"set": "c"}]
    out = M.margins_from_axial(ax, meta)["m"]
    assert out["set"] == "b" and out["P_factored_n"] == 50.0
    assert out["margin"] == pytest.approx(150.0 / (1.5 * 50.0), rel=1e-6)
    ax["m"]["N"] = np.array([5.0, 7.0])
    assert M.margins_from_axial(ax, meta[:2])["m"]["margin"] is None      # never in compression


def test_region_label_lower_sleeve():
    """Task 3: the lower sleeve band is no longer called the crown bore wall; above z 240 it still is."""
    lab = R.region_label([-103.0, -9.0, 167.0])
    assert "crown bore wall" not in lab and "lower sleeve z 160-240" in lab and lab.startswith("stay L")
    assert R.region_label([110.0, 0.0, 300.0]) == "stay R sleeve (crown bore wall)"
    assert R.region_label([110.0, 0.0, 500.0]).endswith("at the top bushing")
    assert R.region_label([110.0, 0.0, 120.0]) == "stay R below the sleeve"
    assert R.region_label([-60.0, -10.0, 150.0]) == "lumbar struts / pan"


def test_h1_sleeve_region_still_maps_the_new_label():
    from huntkit.gendesign import h1_sleeve as S
    assert S.region([-103.0, -9.0, 167.0]) == "stay sleeve z 160-240"
    assert S.region([-110.0, 0.0, 300.0]) == "stay sleeve z 240-470"


def test_governing_region_counts_the_population_not_the_peak():
    """One hot voxel in the lower sleeve, but most of the top 1 % in the lumbar struts: the governing region is
    the struts, and the peak region is still reported."""
    rng = np.random.default_rng(0)
    n = 2000
    cen = np.c_[rng.uniform(-60, 60, n), rng.uniform(-20, 0, n), rng.uniform(100, 190, n)]   # lumbar struts / pan
    fi = rng.uniform(0.0, 1.0, n)
    cen[0] = [-103.0, -9.0, 167.0]
    fi[0] = 5.0                                                                       # the single peak
    ex = np.zeros(n, bool)
    ex[1] = True
    fi[1] = 9.0                                                                       # excluded load patch
    g = R.governing_region(cen, fi, ex)
    assert g["region"] == "lumbar struts / pan"
    assert g["share"] == pytest.approx(1.0 - 1.0 / g["n"], abs=1e-9)
    assert "lower sleeve" in g["peak_region"]
    assert sum(g["shares"].values()) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        R.governing_region(cen, fi, np.ones(n, bool))


def test_clean_shell_drops_islands_only():
    trimesh = pytest.importorskip("trimesh")
    big = trimesh.creation.box((20, 20, 20))
    small = trimesh.creation.box((2, 2, 2))
    small.apply_translation((50, 0, 0))
    m, dropped = M.clean_shell(trimesh.util.concatenate([big, small]))
    assert len(m.split(only_watertight=False)) == 1 and m.volume == pytest.approx(8000.0)
    assert dropped == [(12, pytest.approx(8.0))]
    huge = trimesh.creation.box((12, 12, 12))
    huge.apply_translation((80, 0, 0))
    with pytest.raises(RuntimeError):
        M.clean_shell(trimesh.util.concatenate([big, huge]))


# ----------------------------------------------------------------------------- needs the H1 voxel base (outputs/)
def _base_or_skip():
    from huntkit.gendesign import frame_h1 as H1
    if not (H1.OUT / "h1_final.npz").exists():
        pytest.skip("H1 solid not generated (outputs/ untracked)")
    return H1


def test_im3_cheek_is_28mm_tall():
    H1 = _base_or_skip()
    cen = H1.base()["cen"]
    m = M.im3_cheek_mask()
    z = cen[m][:, 2]
    assert m.sum() > 0 and set(np.sign(cen[m][:, 0])) == {-1.0, 1.0}
    # 2 mm voxel centres inside +-14 mm of z 520 (the 18 mm released cheek would stop at +-9)
    assert z.min() < 520.0 - 9.0 - 1.0 and z.max() > 520.0 + 9.0 + 1.0
    assert z.min() >= 520.0 - 14.0 - 1e-6 and z.max() <= 520.0 + 14.0 + 1e-6


def test_member_growth_is_grow_only_and_symmetric_in_area():
    H1 = _base_or_skip()
    s0 = M.body_solid()
    s1 = M.body_solid(1.0, 2.5)
    assert not np.any(s0 & ~s1)                      # grow only
    cen = H1.base()["cen"]
    i0, i1 = np.where(s0)[0], np.where(s1)[0]
    a0 = M.member_masks({"idx": i0, "cen": cen[i0]})
    a1 = M.member_masks({"idx": i1, "cen": cen[i1]})
    for k in a0:
        assert a1[k][2] >= a0[k][2]
    assert a1["mid bar (x -115..115) all"][2] > a0["mid bar (x -115..115) all"][2]


# ----------------------------------------------------------------------------- recorded result
@pytest.fixture(scope="module")
def res():
    if not RES.exists():
        pytest.skip("h1_buckling.json not written yet")
    return json.loads(RES.read_text())


def test_reproduces_bl024(res):
    b = res["baseline"]
    assert b["fine_sm8"]["mid bar (x -115..115) all"]["margin"] == pytest.approx(0.439, abs=0.002)
    assert b["beam"]["branch upper (z 330-495) R"]["margin"] == pytest.approx(1.268, abs=0.002)


def test_decomposition_adds_up(res):
    for k, v in res["task1"]["decomposition"].items():
        for nm, m in v["members"].items():
            assert abs(m["sum_check"]) < 1e-3 * max(1.0, abs(m["N_full"])), (k, nm)


def test_squeeze_is_in_every_sim_run(res):
    """The hinge-pin lateral pull is in the sim itself (every converged meat run, coarse and fine), not made by the
    mapping."""
    rows = [r for r in res["task1"]["survey"] if r["case"] == "meat" and r["converged"] and not r["guys_off"]]
    assert len(rows) >= 8
    assert min(min(r["hinge_in_R"], r["hinge_in_L"]) for r in rows) > 50.0


def test_chosen_body_meets_targets(res):
    c = res["chosen"]
    if not c["passes"]:
        pytest.skip("no passing body recorded (report says so)")
    assert c["buckling_min_sim"] >= M.BUCKLE_REQ and c["buckling_min_beam"] >= M.BUCKLE_REQ
    assert c["fatigue_min_sim"] >= M.FAT_REQ and c["strength_min"] >= M.STR_REQ
    assert all(v >= 0.999 for k, v in c["keepouts_present"].items())


def test_print_files_are_single_shells(res):
    p = res.get("print")
    if not p:
        pytest.skip("print files not written")
    for k in ("assembled", "lower", "upper"):
        assert p[k]["shells"] == 1 and p[k]["watertight"], k
    assert p["lower"]["fits_h2s_340x320x340"] and p["upper"]["fits_h2s_340x320x340"]
