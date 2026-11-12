"""BL-025: huntkit.clothsim.recontact re-evaluates stored contact forces on the kept stage's field."""
from pathlib import Path

import numpy as np
import pytest

from huntkit.clothsim import recontact as R

REPO = Path(__file__).resolve().parents[1]
CF = REPO / "outputs" / "clothsim" / "corrie_f"
CACHE = REPO / "outputs" / "clothsim" / "cache"


def test_stages_reads_the_failed_stage_from_the_solve_log():
    case = {"contact_rounding_mm": 3.0, "solve": [
        {"stage": "load x1: converged"}, {"stage": "re-cinched: converged"},
        {"stage": "contact rounding 4 mm: converged"}, {"stage": "contact rounding 3 mm: converged"},
        {"stage": "contact rounding 2 mm: max_iter"}, {"stage": "kept the last converged stage: contact rounding 3 mm"}]}
    st = R.stages(case, {"smooth_mm": 6.0})
    assert st == {"kept": 3.0, "used_by_report": 2.0, "start": 6.0, "stopped": True}
    # first solve failed: no continuation ran, the report used the starting (smoothed) field
    st = R.stages({"contact_rounding_mm": None, "solve": [{"stage": "load x1: stalled"}]}, {"smooth_mm": 6.0})
    assert st["kept"] is None and st["used_by_report"] == 6.0 and not st["stopped"]


@pytest.mark.skipif(not (CACHE / "frame_cloud_4.0.npz").exists(), reason="frame cloud cache not built (outputs/ untracked)")
def test_pass_through_flags_a_panel_behind_the_spreader_only():
    cs = {"spacing": 4.0, "spreader_ny_min": 0.5}
    cl = R.frame_clouds(4.0)
    P = cl["spreader_p"][cl["spreader_n"][:, 1] > 0.5]
    # a grid of points just in front of the face (sound) and the same grid 40 mm behind it (tunnelled)
    sel = P[np.linspace(0, len(P) - 1, 60).astype(int)]
    front = sel + [0.0, 3.0, 0.0]
    behind = sel - [0.0, 40.0, 0.0]
    assert R.pass_through(front, cs)["nodes_through"] == 0
    r = R.pass_through(np.vstack([front, behind]), cs)
    assert r["nodes_through"] == 60 and r["deepest_mm"] == pytest.approx(40.0, abs=0.5)


@pytest.mark.skipif(not (CF / "F_r1_PR15_fineFM" / "x_meat.npy").exists(), reason="BL-022 fine run not in this checkout")
def test_bl021_case_is_reproduced_and_corrected():
    """F_r1_PR15_fineFM meat (BL-021 finding): the stored 1331.8 N was evaluated on the 2 mm field (the stage that
    failed); on the kept 3 mm field the spreader takes 1086.8 N in y (1115.5 N total)."""
    o = R.recontact_run(CF / "F_r1_PR15_fineFM")
    m = o["cases"]["meat"]
    assert m["stages"]["kept"] == 3.0 and m["stages"]["used_by_report"] == 2.0
    assert m["reproduced_n"]["contact_spreader"] == pytest.approx(m["stored"]["contact_spreader"], abs=0.1)
    assert m["kept"]["contact_spreader"] == pytest.approx(1115.5, abs=0.5)
    assert m["kept_detail"]["contact_spreader"]["force_n"][1] == pytest.approx(1086.8, abs=0.5)
    assert m["pass_through"]["nodes_through"] == 0
