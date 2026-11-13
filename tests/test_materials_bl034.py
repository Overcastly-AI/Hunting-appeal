"""BL-034 part B: records for the BOM lines that carried PRICES / ELASTIC assumptions."""
import pytest

import huntkit.materials as mat

BL034 = {  # id: (mass key, expected mass, cost per)
    "slider_10": ("mass_g", 19.0, "unit"),
    "slider_5": ("mass_g", 4.9, "unit"),
    "cam_25mm_al": ("mass_g", 12.2, "unit"),
    "triglide_25mm": ("mass_g", 2.6, "unit"),
    "pom_toggle": ("mass_g", 1.7, "unit"),
    "elastic_25mm": ("mass_g_m", 15.0, "m"),
    "elastic_6mm": ("mass_g_m", 3.0, "m"),
}


@pytest.mark.parametrize("mid", sorted(BL034))
def test_record_has_mass_price_and_url_sources(mid):
    m = mat.load(mid)
    key, val, per = BL034[mid]
    assert m.require(key) == pytest.approx(val)
    assert m.cost_usd["per"] == per and m.cost_usd["value"] > 0
    # every record cites at least one web source, and every unsourced number is flagged ASSUMPTION
    assert any("https://" in s for s in m.sources)
    assert all(("https://" in s) or ("computed" in s) or ("ASSUMPTION" in s) for s in m.sources)


def test_toggle_mass_matches_geometry_and_pom_density():
    t, pom = mat.load("pom_toggle"), mat.load("pom_acetal")
    vol_mm3 = t.require("length_mm") * t.require("width_mm") * t.require("thickness_mm")
    assert t.require("mass_g") == pytest.approx(vol_mm3 * pom.require("density_kg_m3") * 1e-6, abs=0.05)


def test_cam_slip_matches_design_assumption():
    # the record carries the same unproven 1100 N slip value the pack checks use (strap_arch.CAM25_N)
    assert mat.load("cam_25mm_al").require("slip_load_n") == 1100


def test_heavier_than_booked_sliders_are_visible():
    # listings put metal coil sliders well above the 6 g (#10) / 3 g (#5) the concepts book
    assert mat.load("slider_10").require("mass_g") > 6.0 * 2.5
    assert mat.load("slider_5").require("mass_g") > 3.0
