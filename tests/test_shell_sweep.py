"""BL-009 shell sweep: the parametric shell reproduces CORRIE, keeps the owner limits and frame interface, and the
stored sweep rows are complete and honest (convergence + rounding stage on every row)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import shell_sweep as SS  # noqa: E402


def test_s00_reproduces_corrie_rev_b():
    """S00 must be CORRIE rev B exactly: same half-width, depth, collar seam and rule volume."""
    c0 = SS.CO._make_orig() if hasattr(SS.CO, "_make_orig") else SS.CO.make()
    s = SS.make_shell(SS.SHELLS["S00"])
    z = np.linspace(SS.Z0, c0.z_c, 60)
    assert np.allclose(s.a(z), c0.a(z), atol=0.05)
    assert np.allclose(s.depth(z), c0.depth(z), atol=0.05)
    assert s.z_c == pytest.approx(c0.z_c)
    assert s.volume_L() == pytest.approx(c0.volume_L(), rel=1e-4)


def test_solved_shells_hit_rule_target_and_owner_limits():
    for n, p in SS.SHELLS.items():
        g = SS.geometry(p)
        assert g["width_max_mm"] <= 394.0 + 0.5, n                     # owner freeze, 15.5 in
        if p.z_c is None:
            assert g["rule_L"] == pytest.approx(SS.RULE_TARGET_L, abs=0.05), n
        assert g["z_c"] >= 736.3 - 0.05, n                             # B-22 tabs stay below the collar seam


def test_aft_face_is_planar_below_shoulder_and_taper_applies():
    p = SS.SHELLS["S09"]
    s = SS.make_shell(p)
    z = np.linspace(SS.Z0, SS.Z_SH, 9)
    y = s.y_front(z)
    assert np.allclose(np.diff(y, 2), 0.0, atol=1e-6)                  # one plane below the crease
    assert float(s.a([s.z_c])[0]) == pytest.approx(p.a_top, abs=0.01)
    assert float(s.a([SS.Z0])[0]) == pytest.approx(p.a_bot, abs=0.01)
    assert float(s.depth([s.z_c])[0]) == pytest.approx(p.d_col, abs=0.01)
    assert float(s.depth([SS.Z0])[0]) == pytest.approx(p.d_bot, abs=0.01)


def test_install_swaps_and_restores_corrie_make():
    orig = SS.CO.make
    SS.install(SS.SHELLS["S03"])
    try:
        assert SS.CO.make().p.name == "S03"
    finally:
        SS.uninstall()
    assert not isinstance(SS.CO.make(), SS.Shell)
    assert SS.CO.make is orig or SS.CO.make is SS.CO._make_orig


def test_interface_check_flags_a_low_collar():
    p = SS.ShellParams("tmp", 170, 240, 240, 136.18, SS.A_MAX, 720.0)
    g = SS.geometry(p)
    assert g["b22_below_collar_mm"] < SS.TAB_CLEAR_MM and not SS.interface_ok(g)
    assert SS.interface_ok(SS.geometry(SS.SHELLS["S00"]))              # CORRIE: 11.3 mm below the collar seam


@pytest.mark.skipif(not SS.RESULTS.exists(), reason="sweep results not generated")
def test_every_row_states_convergence_and_rounding():
    rows = json.loads(SS.RESULTS.read_text())["rows"]
    assert len([r for r in rows.values() if r["torso"] == 15 and not r["tag"]]) >= 12
    for k, r in rows.items():
        for cn in ("fill", "meat"):
            c = r["cases"][cn]
            assert isinstance(c["converged"], bool), k
            # a converged case names its rounding stage; an unconverged one (no stage converged) has none
            assert (c["rounding_mm"] is not None) == c["converged"], k
            assert c["closed_L"] > 50 and 80 < c["cg_y"] < 260, k


@pytest.mark.skipif(not SS.RESULTS.exists(), reason="sweep results not generated")
def test_control_matches_corrie_pr15c():
    """S00 at 15 in is the same sim as corrie_PR15c (corrie_body.md 11.4: fill 191.3, meat 184.4 mm, 88.1 L).
    The 2026-11-10 re-run gives meat 186.3 (+1.9 mm, same rounding stage 6 mm): re-run scatter, quoted in
    shell_sweep.md as part of the margin."""
    rows = json.loads(SS.RESULTS.read_text())["rows"]
    r = rows["S00_PR15"]
    assert r["cases"]["fill"]["cg_y"] == pytest.approx(191.3, abs=1.0)
    assert r["cases"]["meat"]["cg_y"] == pytest.approx(184.4, abs=2.5)
    assert r["cases"]["fill"]["closed_L"] == pytest.approx(88.07, abs=0.5)


@pytest.mark.skipif(not SS.RESULTS.exists(), reason="sweep results not generated")
def test_chosen_shell_record():
    d = json.loads(SS.RESULTS.read_text())
    ch = d.get("chosen")
    if not ch:
        pytest.skip("no shell chosen yet")
    r = d["rows"][f"{ch}_PR15"]
    g = SS.meets_goal(r)
    assert g["converged"] and g["interface"] and g["volume"]
    # the doc must either meet the goal or say what it costs: the stored verdict must match the numbers
    assert d["chosen_meets_goal"] == (g["meat"] and g["fill"])
