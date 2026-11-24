"""BL-062 iteration 1 system weight (designs/pack_5200/iter1/system/iter1_weight.py)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "iter1" / "system"))
sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))

import iter1_weight as I  # noqa: E402
from huntkit.materials import load  # noqa: E402


@pytest.fixture(scope="module")
def res():
    return I.compute()


def test_items_partition_every_row(res):
    """Every base row lands in exactly one item, and the items add back to the roll-up totals."""
    for scen, key in (("A", "items_after_tests"), ("P", "items_proven_now")):
        it = res[key]
        assert sum(it.values()) == pytest.approx(I.total(scen), abs=0.5)
        others = {k: v for k, v in it.items() if k.startswith("other_") and abs(v) > 0.05}
        assert not others, others
    # gated deletions really net to zero in after tests
    assert abs(res["items_after_tests"]["hood"]) < 0.1 and abs(res["items_after_tests"]["wings"]) < 0.1
    assert res["items_proven_now"]["hood"] > 50


def test_totals_match_rollup(res):
    t = res["totals"]
    assert t["after_tests_base_g"] < t["proven_now_base_g"]
    assert t["non_frame_after_tests_g"] == pytest.approx(t["after_tests_base_g"] - t["frame_after_tests_g"], abs=0.2)
    assert t["target_g"] == pytest.approx(6.6 * I.LB, abs=0.1)


def test_pareto_is_top15_non_frame_sorted(res):
    pr = res["pareto"]
    assert len(pr) == 15
    g = [r["after_tests_g"] for r in pr]
    assert g == sorted(g, reverse=True)
    assert all(r["item"] not in ("frame", "frame_hw") for r in pr)
    # each best lever saves mass and never exceeds the item
    for r in pr:
        assert r["best_delta_g"] <= 0
        assert -r["best_delta_g"] < r["after_tests_g"]


def test_mesh_lever_from_records():
    """BL-067 (review 7 M8): the lever saves real grams, from the 350 g/m2 stand-in, not the booked 380."""
    rec = load("spacer_mesh_3d")
    booked, real = rec.require("areal_density_gsm"), rec.require("stand_in_areal_density_gsm")
    assert (booked, real) == (380, 350)
    m = I.mesh_light()
    g0 = sum(m["pieces_g"].values())
    lite = load("spacer_mesh_3d_230").require("areal_density_gsm")
    assert m["delta_g"] == pytest.approx(-g0 / booked * (real - lite))
    assert m["delta_g"] == pytest.approx(-36.1, abs=0.3)                 # review 7: N1 about -36 g
    assert m["delta_g_booked_basis"] == pytest.approx(-45.1, abs=0.2)    # the BL-062 figure, kept for the trail
    assert sum(m["split"].values()) == pytest.approx(m["delta_g"])
    assert m["pieces_g"]["BP-01"] == pytest.approx(67.6, abs=0.2)     # the booked back-panel mesh
    assert m["thickness_mm"] == (3.0, 4.0)
    b = I.mesh_belt()
    assert b["delta_g"] == pytest.approx(-3.2, abs=0.1)                 # review 7: N2 about -3.2 g
    rb = I.mesh_rebook()
    assert rb["delta_g"] < 0 and rb["delta_g"] == pytest.approx(-rb["booked_mesh_g"] * 30 / 380, abs=0.1)


def test_bl064_records_wired():
    ti = I.ti_backstops()
    assert ti["ti_usd"] == pytest.approx(4.25) and ti["ti_g"] == 4.0
    assert I.wraps_dyneema()["web_break_n"] == 12000.0
    z = I.door_zip8_slider8()
    assert z["slider_g"] == pytest.approx(2 * (8.5 - 15.0))            # on top of BL-037 G-1 cord pulls
    assert z["delta_g"] == pytest.approx(z["chain_g"] + z["slider_g"])
    keys = {k for k, _, _ in I.ASSUMPTIONS}
    assert not {"MESH-320", "MESH-ROLL", "TI-TG-COST"} & keys          # settled by records
    assert {"MESH-320", "MESH-ROLL", "TI-TG-COST"} <= {k for k, _ in I.SETTLED}


def test_option_A_on_real_mesh(res):
    """Review 7 M8: option A on the 350 basis (N1 -36.1, N2 -3.2, N3 -14, N4 -8.2, N5 -8.7)."""
    assert res["options"]["A"]["base_delta_g"] == pytest.approx(-70.2, abs=0.3)


def test_kuiu_arithmetic(res):
    """Review 7 m1: 2 lb 15.9 oz = 1358 g; suspension 1044 g (lid out) or 826 g (lid in)."""
    k = res["kuiu"]
    assert k["g"]["bag_6000"] == pytest.approx(1358, abs=1)
    assert k["suspension_lid_out_g"] == pytest.approx(1044, abs=1)
    assert k["suspension_lid_in_g"] == pytest.approx(826, abs=1)
    ours = I.a_sus(res)
    md = I.report(res, [])
    if k["suspension_lid_in_g"] < ours < k["suspension_lid_out_g"]:
        assert "NOT claimed" in md and "1052" not in md


def test_fabric_and_hardware_levers_from_records():
    c = I.collar_frame_side()
    assert c["delta_g"] == pytest.approx(-c["g0"] * (1 - 92 / 133), abs=0.05)
    ti = I.ti_backstops()
    assert ti["delta_g"] == pytest.approx(2 * (4.0 - load("triglide_25mm").require("stainless_alt_mass_g")))
    dy = I.wraps_dyneema()
    assert dy["length_m"] == pytest.approx(dy["g0"] / 18.0)
    assert dy["delta_g"] < 0 and dy["web_break_n"] / 225.0 > 50


def test_modular_costs_as_hunted():
    for item in ("fp", "imp4", "imp6", "imp2", "imp5"):
        m = I.modular(item)
        assert m["base_delta_g"] < 0                    # base gets lighter
        assert m["as_hunted_delta_g"] > 0               # carrying it costs loops + tabs
        assert m["base_delta_g"] == pytest.approx(-m["pocket_g"] + 2 * I.loop_g())


def test_strength_gate(res):
    st = res["strength"]
    assert st["min_sf"] == pytest.approx(1.36, abs=0.005)      # rubric baseline untouched
    assert st["levers"]["O-cams"]["verdict"] == "FAIL"          # ladder-lock slip below the US load
    assert st["levers"]["N3"]["verdict"] == "PASS"
    assert st["levers"]["N6"]["verdict"].startswith("PENDING")
    for r in st["levers"]["O-cams"]["rows"]:
        assert "tongue" not in r["point"]                       # the IM3 carabiner is not a cam


def test_options_nested_and_consistent(res):
    O, lv = res["options"], {x["key"]: x for x in res["levers"]}
    assert set(O["A"]["keys"]) < set(O["B"]["keys"]) < set(O["C"]["keys"])
    for k, o in O.items():
        assert "O-cams" not in o["keys"]                        # fails the strength gate
        assert o["strong"] != "FAIL"
        assert o["base_delta_g"] == pytest.approx(sum(lv[i]["base_delta_g"] for i in o["keys"]), abs=0.15)
        assert o["after_tests_base_g"] == pytest.approx(res["totals"]["after_tests_base_g"] + o["base_delta_g"], abs=0.15)
        assert o["gap_to_target_g"] > 0                         # honest: 6.6 lb is not reached outside the frame
    assert O["A"]["modular_delta_g"] == 0 and O["A"]["base_delta_g"] == O["A"]["as_hunted_delta_g"]
    assert O["A"]["base_delta_g"] > O["B"]["base_delta_g"] > O["C"]["base_delta_g"]
    assert res["recommended"] == "A"


def test_no_bl037_pick_reproposed(res):
    picks = {"B-1", "B-2", "B-3", "K-1", "H-1", "H-2", "G-1", "G-2", "F-3", "X-1"}
    assert not picks & {x["key"] for x in res["levers"]}
