"""CORRIE rev B.1 (2026-11-09): adopted pockets IMP-1..6, IMP-8 + hipbelt B (designs/pack_5200/concepts/corrie.py),
the loadout re-run (corrie_loadout.py, integrated config) and the additive clothsim pieces (contact rounding,
external loads)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
sys.path.insert(0, str(ROOT))

import corrie as CO  # noqa: E402


@pytest.fixture(scope="module")
def pockets():
    return {d["id"]: d for d in CO.bag_pockets()}


def test_bag_pockets_present_with_mass_and_materials(pockets):
    from huntkit import materials as MAT
    assert set(pockets) == {"IMP-1", "IMP-2", "IMP-4", "IMP-6", "IMP-8"}
    for d in pockets.values():
        assert d["mass_g"] > 5 and d["hours"] > 0.3
        for p in d["pieces"]:
            MAT.load(p.material_id)              # every piece material is a record
        assert d["attach"]


def test_scope_sleeve_takes_the_85mm_spotter(pockets):
    assert all(pockets["IMP-1"]["fits"].values())


def test_hydration_sleeve_clears_im3_and_door_pocket_fits_the_door(pockets):
    assert CO.HYDRO["z"][0] >= CO.BC.STATIONS["im3"] + 19 + 5          # 38 mm IM3 strap + 5 mm clear
    D = CO.DOOR_POCKET
    for z in D["z"]:
        assert CO.door_width(z) - D["w"] >= 2 * (10 + 12)             # zip SA + 12 mm clear each side
    assert D["z"][1] <= CO.DOOR["z_hinge"] - 15


def test_strap_pocket_takes_a_160mm_phone(pockets):
    i = sorted(pockets["IMP-6"]["interior_mm"], reverse=True)
    assert i[0] >= 160 and i[1] >= 80 and i[2] >= 10


@pytest.mark.parametrize("size", CO.BELT_SIZES)
def test_hip_layout_follows_belt_b(size):
    h = CO.hip_layout(size)
    x0, x1 = h["room"]
    assert h["L"]["x"] == (x0, x1)
    assert h["L"]["face"]["straight"]                                  # cone-cut outline sews as straight runs
    assert h["holster_axis_behind_crest"]
    phone_fits = sorted(h["L"]["interior_mm"], reverse=True)[0] >= 160
    assert phone_fits == (size in ("XL", "XXL"))                       # DECISIONS 2026-11-09 (IMP-6 reason)
    assert (h["R"] is not None) == (size in ("XL", "XXL"))


def test_belt_b_mass_grows_with_size_and_uses_the_new_records():
    m = [CO.belt_b(s)["body_g"] for s in CO.BELT_SIZES]
    assert all(b > a for a, b in zip(m, m[1:]))
    assert CO.DRING_G == 6 and CO.LADDER_HEAVY_G == 7 and CO.GRIP_GSM == 46
    assert 200 < CO.belt_b("M")["body_g"] < 250


def test_weight_table_adds_up():
    w = CO.weight_table("M")
    assert math.isclose(sum(r[1] for r in w["rows"]), w["total_g"], abs_tol=0.5)
    assert 3850 < w["total_g"] < 4050
    assert w["rev_b_total_g"] == pytest.approx(3714.4, abs=1.0)


def test_loadouts_with_the_adopted_pockets():
    import corrie_loadout as L
    data = L.load_yaml()
    for size in ("M", "XL"):
        for key in ("day", "elk6"):
            P = L.pack(L.split_units(L.expand(data, key)), f"integrated:{size}")
            s = L.summary(P)
            hourly = s["access"]["hourly"]["fail"]
            assert hourly == ([] if size == "XL" else ["snacks_today"])
            assert s["rev_c_ok_15in"]
            assert next(r for r in P.rows if r["id"] == "phone")["zone"] == "strap_pocket"
            assert next(r for r in P.rows if r["id"] == "bottle_1L")["zone"] == "bottle_hip"
    P = L.pack(L.split_units(L.expand(data, "elk6", meat_day=True)), "integrated:M", meat_kg=45.0)
    assert next(r for r in P.rows if r["id"] == "bladder_2L")["zone"] == "hydro_sleeve"
    assert not P.float_mode and L.summary(P)["rev_c_ok_15in"]


def test_gapfield_smoothing_keeps_a_flat_face_and_is_off_by_default():
    from huntkit.clothsim.model import GapField
    ax = np.arange(30) * 2.0
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
    f = GapField(np.zeros(3), 2.0, Z - 20.0)                           # plane z = 20
    g = f.smoothed(6.0)
    q = np.array([[30.0, 30.0, 21.0], [20.0, 25.0, 18.5]])
    assert np.allclose(g(q)[0], f(q)[0], atol=0.01)                     # grid-edge truncation only
    from huntkit.clothsim.pack import load_scenario
    assert not load_scenario(ROOT / "huntkit" / "clothsim" / "scenarios" / "pack5200_v31.yaml")["contact"].get("smooth_mm")


def test_corrie_rev_c_scenarios_carry_pouch_and_scope():
    from huntkit.clothsim.pack import load_scenario
    s = load_scenario(ROOT / "huntkit" / "clothsim" / "scenarios" / "corrie_PR15c.yaml")
    ext = {e["label"]: e for e in s["cases"]["meat"]["external"]}
    assert ext["pouch_1kg"]["kg"] >= 1.0
    assert ext["scope85_left_wing"]["kg"] >= 1.91
    assert s["contact"]["smooth_continuation"][-1] == 0.0


def test_pad_seat_clears_the_rolling_bow_tie_and_fits_the_pan():
    ps = CO.pad_seat()
    assert ps["fits_pan"]
    assert ps["depth_play_mm"] >= 4.0                                   # hipbelt_structural.md: >= 4 mm clear channel
    assert ps["roll_clear_deg"] >= 8.0                                  # belt free roll +/-8 deg on the Ti pin
    w = CO.weight_table("M")
    assert any("pad seat" in r[0] and r[1] == ps["mass_g"] for r in w["rows"])
    assert any("load path" in r[0] and abs(r[1] - 65.4) < 0.1 for r in w["rows"])
