"""BL-069 ("work with a PPU 3D printed frame"): the PPA-CF record (chosen reading) and the PPS-CF alternative load,
validate, carry every frame-study key the H1 checks read, and keep the design-value arithmetic of
docs/backlog/BL-069-ppu-frame-material.md."""
from pathlib import Path

import pytest
import yaml

from huntkit import materials as mat
from huntkit.materials.validate import validate_record

POLY = Path(__file__).resolve().parents[1] / "data" / "materials" / "polymers"
IDS = ["ppa_cf_fdm", "pps_cf_fdm_bambu"]

# keys frame_topopt.load_print_materials / bag_attach / weight_c / frame_production read from a print material
FRAME_KEYS = [
    "density_kg_m3", "youngs_modulus_xy_mpa", "youngs_modulus_z_mpa", "tensile_strength_xy_mpa",
    "tensile_strength_z_mpa", "env_knockdown_ratio", "modulus_40c_wet_ratio", "modulus_60c_ratio",
    "creep_modulus_8h_40c_ratio", "creep_rupture_8h_40c_ratio", "fatigue_1e5_ratio", "modulus_minus20c_ratio",
    "impact_minus20c_ratio", "heat_deflection_temp_c", "glass_transition_c", "water_absorption_pct",
    "drying_temp_c", "drying_time_hours", "nozzle_temp_c", "bed_temp_c", "chamber_temp_c", "min_wall_mm",
    "print_cost_usd_per_g",
]


@pytest.mark.parametrize("mid", IDS)
def test_record_loads_and_validates(mid):
    m = mat.load(mid)
    assert m.id == mid and m.category == "polymers"
    assert m.confidence == "datasheet"
    assert len(m.sources) >= 3 and all("http" in s for s in m.sources)
    assert m.cost_usd and m.cost_usd["per"] == "kg" and m.cost_usd["value"] > 0
    raw = yaml.safe_load((POLY / f"{mid}.yaml").read_text())
    assert validate_record(raw, POLY / f"{mid}.yaml") == []
    for k in FRAME_KEYS:
        assert m.require(k) is not None, k
    assert m.get("anisotropic") is True


def test_ppa_tds_values_and_design_rule():
    p = mat.load("ppa_cf_fdm")
    assert p.require("density_kg_m3") == 1250
    assert (p.require("tensile_strength_xy_mpa"), p.require("tensile_strength_z_mpa")) == (168, 57)
    assert (p.require("youngs_modulus_xy_mpa"), p.require("youngs_modulus_z_mpa")) == (11800, 4300)
    # design Z = TDS mean - 2.4 SD (SD 5 MPa); wet knock = Raise3D conditioned / Bambu dry
    assert p.require("tensile_strength_z_design_mpa") == pytest.approx(57 - 2.4 * 5)
    assert p.require("env_knockdown_ratio") == pytest.approx(
        p.require("tensile_strength_xy_conditioned_mpa") / p.require("tensile_strength_xy_mpa"), abs=0.005)
    # conditioned Raise3D mono-layer Z sits at the knocked-down design Z (within 10 %)
    zd = p.require("tensile_strength_z_design_mpa") * p.require("env_knockdown_ratio")
    assert p.require("tensile_strength_z_conditioned_mpa") == pytest.approx(zd, rel=0.10)
    # H2S can hold it: chamber 65 C max is inside the TDS 50-80 C window, nozzle well under 350 C
    assert 50 <= p.require("chamber_temp_c") <= 65
    assert p.require("nozzle_temp_c") <= 350 and p.require("bed_temp_c") <= 120


def test_ppa_vs_paht_headline_ratios():
    """The BL-069 comparison table: stronger and much stiffer in the layer plane, weaker across the layers once
    knocked down, 18 % denser."""
    p, a = mat.load("ppa_cf_fdm"), mat.load("pa12_cf_fdm_paht")
    rho = p.require("density_kg_m3") / a.require("density_kg_m3")
    assert rho == pytest.approx(1.179, abs=0.001)
    xy = (p.require("tensile_strength_xy_mpa") * p.require("env_knockdown_ratio")) / (
        a.require("tensile_strength_xy_mpa") * a.require("env_knockdown_ratio"))
    z = (p.require("tensile_strength_z_design_mpa") * p.require("env_knockdown_ratio")) / (
        a.require("tensile_strength_z_mpa") * a.require("env_knockdown_ratio"))
    assert xy == pytest.approx(1.742, abs=0.005)
    assert z == pytest.approx(0.875, abs=0.005) and z < 1.0
    e_buckle = (p.require("youngs_modulus_xy_mpa") * p.require("modulus_40c_wet_ratio")
                * p.require("creep_modulus_8h_40c_ratio")) / (
        a.require("youngs_modulus_xy_mpa") * a.require("modulus_40c_wet_ratio")
        * a.require("creep_modulus_8h_40c_ratio"))
    assert e_buckle == pytest.approx(5.26, abs=0.01)
    # brittle across the layers: the cold-drop risk the FI check cannot see
    assert p.require("impact_z_kj_m2") < 0.5 * 13.3
    assert p.require("water_absorption_pct") > a.require("water_absorption_pct")


def test_pps_is_weaker_across_layers_than_both():
    s, p, a = (mat.load(i) for i in ("pps_cf_fdm_bambu", "ppa_cf_fdm", "pa12_cf_fdm_paht"))
    assert s.require("tensile_strength_z_mpa") < a.require("tensile_strength_z_mpa") < p.require(
        "tensile_strength_z_mpa")
    assert s.require("tensile_strength_xy_mpa") <= a.require("tensile_strength_xy_mpa")
    assert s.require("water_absorption_pct") < 0.1
