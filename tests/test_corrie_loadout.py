"""CORRIE loadout / packing study (concepts/corrie_loadout.py, designs/pack_5200/loadouts.yaml)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import corrie_loadout as L  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return L.load_yaml()


@pytest.fixture(scope="module")
def res(data):
    return L.run(data)


def test_every_number_is_cited_or_assumption(data):
    keys = set(data["sources"])
    assert all(str(u).startswith("https://") for u in data["sources"].values())
    for iid, it in data["items"].items():
        for f in ("mass_src", "vol_src"):
            s = str(it[f])
            assert s.startswith("ASSUMPTION") or "ASSUMPTION" in s or any(k in s for k in keys), (iid, f, s)
        assert it["mass_g"] >= 0 and it["vol_L"] >= 0 and len(it["dims_mm"]) == 3
        assert it["access"] in L.REQUIRED
    for lo in data["loadouts"].values():
        assert set(lo["items"]) <= set(data["items"])


def test_layer_model_reproduces_corrie_uniform_cg_and_sim_volume():
    cap = L.G["cum_L"][-1]
    assert 2 * cap == pytest.approx(L.G["v_sewn"], rel=1e-3)
    fill = lambda col: {"id": col, "name": col, "cat": "fill", "pref": [f"bag_{col}_low"], "dims_mm": [1, 1, 1],  # noqa: E731
                        "access": "camp", "qty": 1, "vol_L": cap * L.EFF_SOFT, "vol_tot": cap * L.EFF_SOFT,
                        "mass_g": 1000.0, "mass_tot": 1000.0}
    P = L.pack([fill("F"), fill("A")], "today")
    _, cg = L.bag_cg(P)
    gy, gz = L.G["c"].cg()
    assert cg[1] == pytest.approx(gy, abs=6.0)      # half-column centroids vs the full-section integrator
    assert cg[2] == pytest.approx(gz, abs=25.0)     # two half-volume masses vs a continuous fill


def test_all_loadouts_fit_and_pass_rev_c(res):
    for k, s in res["loadouts"].items():
        assert not s["unplaced"], k
        assert s["main_bag_free_L"] >= 0, k
        assert s["rev_c_ok_15in"], (k, s["cg_y_rev_c_15in"])
        if k.endswith("_meat"):
            assert not s["float_mode"] and s["load_kg_incl_meat"] <= L.RATED_KG, k


def test_today_access_gaps_and_recommended_set_closes_them(res):
    t = res["loadouts"]["elk6_rifle_today"]["access"]["hourly"]["fail"]
    assert {"bladder_2L", "bottle_1L", "phone"} <= set(t)
    for k in ("day_rifle_after", "elk6_rifle_after", "elk6_archery_after"):
        assert all(not v["fail"] for v in res["loadouts"][k]["access"].values()), k


def test_hip_pocket_phone_fit():
    phone = (160, 80, 10)
    assert not L.fits_env(phone, L.HIP_TODAY_ENV)
    assert L.fits_env(phone, L.HIP_AFTER_ENV)


def test_improvements_traceable_and_small(res):
    ids = {i["id"] for i in res["improvements"]}
    assert set(L.RECOMMENDED) <= ids
    for i in res["improvements"]:
        assert i["mass_g"] > 0 and i["hours"] >= 0 and i["problem"] and i["ip"]
    assert res["recommended"]["mass_g"] < 150 and res["recommended"]["hours"] < 10


def test_spotter_options_inside_rev_c(res):
    for key, opts in res["spotter"].items():
        assert opts["a_wing_sleeve"]["zone"] == "scope_sleeve_L"
        for o in opts.values():
            assert o["cg_y_rev_c_15in"] <= L.REV_C["bag_y"], (key, o)
