"""Team A EVOLVE (CORRIE E), bag design competition 2026-11-10. Fast checks only (no cloth sim, no render)."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

A = Path(__file__).resolve().parents[1] / "designs" / "pack_5200" / "bag_comp" / "A"
sys.path.insert(0, str(A))

import evolve as E  # noqa: E402


def test_envelope_inside_the_fixed_size():
    v = E.volumes()
    assert v["width_max_mm"] <= 394.0 + 0.5          # 15.5 in
    assert v["depth_max_mm"] <= 12 * 25.4             # 12 in
    assert v["width_collar_mm"] < v["width_max_mm"]   # E-2 taper


def test_rounded_section_area_matches_k():
    c = E.make()
    a, d = 190.0, 250.0
    P = E.rounded_section(a, d, 0.0, E.R_AFT, M=2000)
    x, y = P[:, 0], P[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    assert area == pytest.approx(2 * a * d * c.k_at(a, d), rel=5e-3)


def test_door_wider_than_corrie_at_every_meat_strap():
    r = E.door_reach()
    for k in ("im1", "im2", "im3"):
        assert r[k]["clear_width_mm"] > r[k]["corrie_mm"]
    assert r["sill_above_floor_mm"] == pytest.approx(E.DOOR["z_lo"] - 35.0)


def test_ledger_and_system_mass():
    s = E.system()
    led = {r["id"]: r for r in s["corrie_e"]["ledger"]}
    assert set(led) >= {"E-1", "E-3", "E-4", "E-5", "E-7"}
    assert led["E-1"]["g"] < 0 and led["E-3"]["g"] < 0          # corners and tub save mass
    assert 0 < s["delta_g"] < 40                                  # honest: the pockets cost more than the cuts save
    # BL-035: 710.6 -> 738.5 g = +26.0 #10 door sliders (slider_10 record 19.0 g, was 6 g) + 1.9 IMP-4 #5 slider
    # (slider_5 record 4.9 g, was 3.0 g), both BL-034 records on CORRIE B.2's body and pocket
    assert s["corrie_b2"]["bag_system_g"] == pytest.approx(738.5, abs=1.0)


def test_cloth_sim_surface_is_continuous():
    import evolve_bag as EB
    BC = sys.modules["bag_concepts"]
    S = EB.RoundedSurface(E.make(), BC)
    for z in (60.0, 330.0, 700.0):
        q = np.array([0, 1 / 3, 2 / 3, 1.0, 2.0 - 1e-9]) * EB.US
        eps = 1e-6 * EB.US
        a = S(np.column_stack([q - eps, np.full(5, z)]))
        b = S(np.column_stack([q + eps, np.full(5, z)]))
        assert np.max(np.linalg.norm(a[1:] - b[1:], axis=1)) < 0.5     # gusset | aft | gusset | frame join


@pytest.fixture
def restore_corrie_modules():
    """evolve_loadout.install() re-points the shared ``corrie_loadout`` module at CORRIE E (G, zones, MIN_TOP_Z, the
    sim CG / peel tables, mutated in place) and sets ``corrie.DOOR = E.DOOR`` for good. Every later test that builds
    CORRIE (ledger, weight table, CORRIE F, the other teams' baselines, loadouts) then ran on CORRIE E's door (BL-025
    found 8 failures in a full run; the CORRIE B.2 total read 0.8 g light). Snapshot both modules' globals, shallow-copy
    the mutable containers, and put everything back after the test."""
    import copy

    import corrie as CO
    import corrie_loadout as CL
    snaps = []
    for mod in (CO, CL):
        g = vars(mod)
        saved = {k: v for k, v in g.items() if not k.startswith("__")}
        inner = {k: copy.copy(v) for k, v in saved.items() if isinstance(v, (dict, list, set))}
        snaps.append((g, saved, inner))
    try:
        yield
    finally:
        for g, saved, inner in snaps:
            for k in [k for k in g if not k.startswith("__") and k not in saved]:
                del g[k]
            g.update(saved)
            for k, v in inner.items():          # undo in-place mutation (e.g. _MEAT_PEEL.clear(), SIM_FILL_CG[t] = ...)
                obj = g[k]
                if isinstance(obj, (dict, set)):
                    obj.clear()
                    obj.update(v)
                else:
                    obj[:] = v


def test_loadout_no_access_miss(restore_corrie_modules):
    import evolve_loadout as LO
    res = LO.run()
    assert all(not f for f in res["misses"].values()), {k: v for k, v in res["misses"].items() if v}


def test_result_json_schema():
    f = A / "result.json"
    if not f.exists():
        pytest.skip("result.json not generated yet")
    r = json.loads(f.read_text())
    for k in ("team", "name", "one_line", "bag_system_g", "pack_mass_M_g", "volume_L", "fill_height_in", "pieces",
              "curved_seams", "zip_mm_total", "beginner_hours", "cg_fill_mm", "cg_meat_mm", "cg_method",
              "access_misses", "features", "risks", "screenshots"):
        assert k in r
    assert 82.0 <= r["volume_L"] <= 88.0
    assert all(v <= 205.0 for v in r["cg_fill_mm"].values())
    assert all(v <= 190.0 for v in r["cg_meat_mm"].values())
    assert math.isclose(r["pack_mass_M_g"], 3943.0 - r["corrie_b2_bag_system_g"] + r["bag_system_g"], abs_tol=0.2)
