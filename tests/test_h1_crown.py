"""BL-051: H1 stay crown restored over the old US stub sites (huntkit/gendesign/h1_crown.py, h1_lanes.strip_old_us)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
PD = REPO / "designs" / "pack_5200" / "print" / "frame_h1"
RES = REPO / "designs" / "pack_5200" / "analysis" / "h1_crown.json"


# ------------------------------------------------------------------------------------------------ the bridge rule
def _grid(nx=9, ny=12, nz=30, h=2.0):
    i, j, k = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    cen = np.c_[i.ravel(), j.ravel(), k.ravel()].astype(float) * h + h / 2 + np.array([101.0, -13.0, 81.0]) - h / 2
    return cen


def test_crown_bridge_restores_the_stay_prism():
    """A 'stay' whose crown is higher than a circle; the zone has the crown cut away: the bridge marks exactly the
    cut crown voxels (the section of the reference planes), not more."""
    from huntkit.gendesign import h1_lanes as L
    cen = _grid()
    x, y, z = cen.T
    stay = (np.abs(x - 109) <= 6) & (y >= -11) & (y <= 9)          # crown top y 9 (voxel centres)
    zone = (z >= 95) & (z <= 115) & (np.abs(x - 109) <= 8) & (y > 5)  # strip zone above y 5
    rm = np.where(zone)[0]
    br = L._crown_bridge(stay, cen, rm, 2.0)
    assert br.sum() > 0
    np.testing.assert_array_equal(br, stay[rm])                    # exactly the stay section, nothing proud of it
    # a blend one voxel past the zone is not copied (references are 2-4 voxels out)
    blob = stay | ((z == 117) & (np.abs(x - 109) <= 8) & (y <= 13))
    np.testing.assert_array_equal(L._crown_bridge(blob, cen, rm, 2.0), stay[rm])


def test_crown_bridge_takes_the_leaner_side():
    from huntkit.gendesign import h1_lanes as L
    cen = _grid()
    x, y, z = cen.T
    lean = (np.abs(x - 109) <= 6) & (y >= -11) & (y <= np.where(z < 105, 9, 5))
    rm = np.where((z >= 99) & (z <= 109) & (np.abs(x - 109) <= 8) & (y > 3))[0]
    br = L._crown_bridge(lean, cen, rm, 2.0)
    assert cen[rm][br, 1].max() == pytest.approx(5.0)


def test_mass_budget_books_every_pin_once():
    """BL-051 item 3: 12 stations; the attachment budget books 8 pins + sleeves and the under-strap cradle rows
    (meat_haul.cradle_parts_g) book the US1 / US2 four. Together 12, none twice."""
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign import meat_haul as MH
    m = BA._mass_budget(6.0, {"pin_g": 2.4, "sleeve_g": 0.3})
    n = len(BA.stations())
    n_at = len(BA._pins_booked_here())
    cr = MH.cradle_parts_g({})
    n_cr = int(next(k for k in cr if k.startswith("7075 pins (")).split("(")[1].rstrip(")"))
    assert n == 12 and n_at + n_cr == n
    assert {s["name"] for s in BA.stations() if s not in BA._pins_booked_here()} == set(BA.CRADLE_PIN_STATIONS)
    assert m["parts_g"][f"7075 pins ({n_at})"] == pytest.approx(n_at * 2.4)
    assert m["parts_g"][f"UHMWPE sleeves ({n_at})"] == pytest.approx(n_at * 0.3)


# ------------------------------------------------------------------------------------------------ verification
def test_lug_fea_polygon_circle_matches_circle():
    """The stay_poly option with a 64-gon of the stay circle reproduces the circle model (same mesh, same FI99)."""
    from huntkit.gendesign import h1_lanes as L
    gi = L.lug_geom_inputs("us2")
    p = gi["p"]
    lo = L.lug_loads("us2")
    loads = {"cradle": lo["cradle"]["vec"]}
    r = p["stay_r"]
    t = np.linspace(0, 2 * math.pi, 64, endpoint=False)
    poly = np.c_[r * np.cos(t), r * np.sin(t)].tolist()
    a = L.lug_fea(p["geom"], r, gi["xoff"], gi["arm"], loads, h=1.0)
    b = L.lug_fea(p["geom"], r, gi["xoff"], gi["arm"], loads, h=1.0, stay_poly=poly)
    for rn in ("use", "root", "arm"):
        assert b["loads"]["cradle"][rn]["fi99"] == pytest.approx(a["loads"]["cradle"][rn]["fi99"], rel=0.03)


# ------------------------------------------------------------------------------------------------ on the print
@pytest.mark.skipif(not (PD / "h1_assembled.stl").exists(), reason="print files not generated")
def test_crown_is_continuous():
    """BL-051 item 1: the stay's bag-face crown on the print is continuous over the old US1 / US2 stub sites."""
    from huntkit.gendesign import h1_crown as C
    r = C.crown_continuity()
    assert r["pass"], r
    for side in ("R", "L"):
        for ln in r[side]["lines"]:
            assert ln["drop_mm"] <= C.CROWN_DROP_MAX and ln["max_step_mm"] <= C.CROWN_STEP_MAX


@pytest.mark.skipif(not (PD / "h1_assembled.stl").exists(), reason="print files not generated")
def test_crown_top_at_the_old_us2_site():
    from huntkit.gendesign import h1_crown as C
    m = C._mesh()
    for x in (115.0, -115.0):
        ref = C.crown_top(m, 120.0, x)
        for z in (136.0, 142.0, 148.0, 96.0):
            assert C.crown_top(m, z, x) == pytest.approx(ref, abs=0.5)


# ------------------------------------------------------------------------------------------------ record
@pytest.fixture(scope="module")
def res():
    if not RES.exists():
        pytest.skip("h1_crown.json not generated")
    return json.loads(RES.read_text())


def test_record_before_failed_after_passes(res):
    assert res["after"]["continuity"]["pass"]
    b = res["before"]["continuity"]
    assert not b["pass"] and min(b["R"]["drop_mm"], b["L"]["drop_mm"]) > 1.5


def test_record_checks(res):
    sc = res["slice_checks"]
    assert sc["fairleads_pass"] and sc["channel"]["pass"] and sc["pawl"]["pass"] and sc["pieces_pass"]
    assert res["joint_slices"]["pass"]
    assert res["us_route"]["print_lanes"]["pass"]
    assert min(res["us_route"]["print_lanes"]["worst_clear_mm"].values()) >= 10.0
    assert res["joint"]["worst_strength"]["sf"] >= 2.0 and res["joint"]["worst_fatigue"]["fatigue"] >= 1.15
    sp = res["spreader_us2_notch"]
    assert sp["pass"] and sp["proud_mm"] <= 0.0 and not sp["air_rule_pass"]
    lb = res["export"]["lower"]["bed_bl050"]
    assert lb["fits_with_brim"]
    for k in ("assembled", "lower", "upper"):
        assert res["export"][k]["watertight"] and res["export"][k]["shells"] == 1


def test_record_lugs(res):
    u2 = res["lug"]["us2"]
    assert u2["crown"]["worst_strength"]["sf"] >= 2.0 and u2["crown"]["worst_fatigue"]["fatigue"] >= 1.0
    assert u2["crown"]["worst_fatigue"]["fatigue"] >= u2["circle"]["worst_fatigue"]["fatigue"]
    u1 = res["us1_root"]
    assert u1["governs"] == "stub_crown"
    assert u1["stub_crown_fatigue"] < 1.0           # honest: the US1 root does not meet fatigue (reported, not fixed)
    assert u1["stub_crown_fatigue"] <= (u1["body_cradle_fatigue"] or 99)


def test_record_body(res):
    bs = res["body"]
    assert bs is not None
    for b, v in bs["bases"].items():
        assert v["after"]["strength"] >= v["before"]["strength"] - 0.02, b
        assert v["after"]["buckling"] >= v["before"]["buckling"] - 0.02, b
    assert bs["cradle"]["after"]["strength"] >= 2.0


def test_record_mass_and_ledger(res):
    from huntkit.mass import ledger as L
    m = res["mass"]
    assert m["print_delta_g"] == pytest.approx(m["assembled_g"] - m["assembled_bl050_g"], abs=0.11)
    assert 0.0 < m["print_delta_g"] < 10.0
    rows = L.corrections("corrie_b2_h1", "M")["BL051"]
    assert len(rows) == 1 and rows[0]["g"] == pytest.approx(m["print_delta_g"], abs=0.01)
    assert L.corrections("corrie_b2_today", "M")["BL051"] == []
    assert L.corrections("corrie_b2_today", "M")["BL050"] == []          # the double-counted pins row is gone
    hw = [r for r in L.corrections("corrie_b2_h1", "M")["BL050"] if "hardware" in r["name"]]
    assert hw and "M5 x 40" in hw[0]["name"] and "M5 x 35" not in hw[0]["name"]
