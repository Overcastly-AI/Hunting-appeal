"""Material evidence for the held CORRIE fabric swaps (O-3, O-4, O-5, O-6, O-15) and the 2026-11-09 records
(designs/pack_5200/analysis/fabric_swap_evidence.md)."""
import re

import pytest

from huntkit import materials as mat
from huntkit.materials.validate import validate_record

NEW_IDS = ["nylon_ripstop_70d", "polyester_300d_printable", "insert_heatset_brass_m5", "shock_cord_3mm"]
UPDATED_IDS = ["ultragrid_210d_uhmwpe_ripstop", "challenge_ultra_200", "robic_100d_ripstop"]
URL = re.compile(r"https?://\S+")


@pytest.mark.parametrize("mid", NEW_IDS + UPDATED_IDS)
def test_records_sourced_with_urls(mid):
    m = mat.load(mid)
    assert m.confidence in mat.CONFIDENCE_LEVELS and m.cost_usd and m.cost_usd["value"] > 0
    # every non-ASSUMPTION source line carries a URL; anything unpublished is labelled ASSUMPTION
    for s in m.sources:
        assert URL.search(s) or s.startswith("ASSUMPTION"), f"{mid}: source without URL: {s[:60]}"
    assert any(URL.search(s) for s in m.sources)


def test_70d_ripstop_datasheet_values():
    r = mat.load("nylon_ripstop_70d")
    assert r.require("areal_density_gsm") == pytest.approx(92)          # RBTR data sheet, finished
    assert min(r.require("tear_warp_n"), r.require("tear_weft_n")) >= 35  # bag_weight_plan O-3 threshold
    assert r.require("grab_warp_n") > r.require("grab_weft_n") > 0
    assert r.require("seam_strength_warp_n") > 0 and r.require("abrasion_cycles_martindale") > 0
    assert "PU" in r.require("coating")


def test_300d_printable_values():
    p = mat.load("polyester_300d_printable")
    assert p.require("fiber") == "polyester" and p.require("denier") == 300
    assert p.require("areal_density_gsm") == pytest.approx(133)
    assert p.require("areal_density_gsm") < mat.load("polyester_ht_630d_printable").require("areal_density_gsm")
    assert p.require("grab_warp_n") > 0 and p.require("tear_warp_n") > 0
    assert "print" in p.require("printable")


def test_ultragrid_has_published_abrasion():
    g = mat.load("ultragrid_210d_uhmwpe_ripstop")
    assert g.require("abrasion_taber_cycles") == 1100                  # Challenge EcoPak guide, ASTM D3884
    assert g.require("areal_density_gsm") == pytest.approx(132)
    # O-4 plan criterion: >= the 330D record's Taber value
    assert g.require("abrasion_taber_cycles") >= mat.load("cordura_330d_nylon66").require("abrasion_taber_cycles")


def test_ultra200_strength_and_o5_seam_margin():
    u = mat.load("challenge_ultra_200")
    assert u.require("tear_warp_n") == pytest.approx(103.1 * 4.448, rel=1e-3)
    assert u.require("abrasion_taber_cycles") == 4400
    strip_ultra = min(u.require("tensile_warp_n_50mm"), u.require("tensile_weft_n_50mm")) / 50.0
    # B-18 seam on 500D: 0.8 x 80 mm x 500D strip (grab / 31.25) = 2355 N, SF 2.31 (attach_system)
    c5 = mat.load("cordura_500d_nylon66")
    strip_500 = min(c5.require("grab_warp_n"), c5.require("grab_weft_n")) / 31.25
    assert 0.8 * 80 * strip_500 == pytest.approx(2355, abs=1)
    assert strip_ultra > strip_500        # ULTRA (ASSUMPTION 60 N/mm) does not lower the seam; PT-3 confirms


def test_heatset_insert_record():
    i = mat.load("insert_heatset_brass_m5")
    assert i.require("thread").startswith("M5")
    assert i.require("hole_diameter_mm") == pytest.approx(6.4)
    assert 0 < i.require("pullout_strength_n") <= i.require("pullout_ref_pa12_mjf_n")
    assert i.require("tightening_torque_max_n_m") < i.require("torque_out_n_m")
    assert i.require("mass_g") < 3


def test_shock_cord_record_replaces_dyneema_proxy():
    s = mat.load("shock_cord_3mm")
    assert s.require("diameter_mm") == 3 and s.require("mass_g_m") == pytest.approx(6.0)
    assert s.require("mass_g_m") > mat.load("dyneema_cord_2mm").require("mass_g_m")
    assert s.require("breaking_strength_n") > 0


def test_torque_suffix_validates():
    raw = {"id": "x_insert", "name": "x", "category": "hardware", "generic": True, "confidence": "estimate",
           "sources": ["ASSUMPTION"], "properties": {"torque_out_n_m": 5.0}}
    assert validate_record(raw) == []
