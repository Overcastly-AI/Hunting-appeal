"""BL-082: cited 6061-T6 data for the concept-B tube ladder (BL-081 checks). The S-N fit, mean-stress values, notch
sensitivity, ring crush / ovalisation numbers, friction design values and tube prices in the records reproduce from
their stated formulas and sources."""
import math
from pathlib import Path

import pytest
import yaml

from huntkit import materials as mat
from huntkit.materials.validate import validate_record

METALS = Path(__file__).resolve().parents[1] / "data" / "materials" / "metals"


def sn_fit(N, m):
    return m.require("sn_fit_coeff_mpa") / math.sqrt(N) + m.require("sn_fit_floor_mpa")


def goodman_smax(sf, su, R):
    return 2 * sf * su / ((1 - R) * su + (1 + R) * sf)


def gerber_smax(sf, su, R):
    k = (1 + R) / (1 - R)
    a, b = (k / su) ** 2, 1 / sf
    sa = (-b + math.sqrt(b * b + 4 * a)) / (2 * a)
    return 2 * sa / (1 - R)


@pytest.mark.parametrize("mid", ["alu_6061_t6", "alu_6061_t6_drawn_tube"])
def test_records_validate(mid):
    p = METALS / f"{mid}.yaml"
    assert validate_record(yaml.safe_load(p.read_text()), p) == []
    m = mat.load(mid)
    assert any("BL-082" in s for s in m.sources)


def test_unnotched_sn_fit_matches_yahr_table():
    m = mat.load("alu_6061_t6")
    # Yahr Table 1 design curve (zero mean) = fit / 2 on stress at high N
    assert sn_fit(1e6, m) / 2 == pytest.approx(m.require("asme_design_sa_1e6_zero_mean_mpa"), abs=0.05)
    assert sn_fit(1e7, m) / 2 == pytest.approx(m.require("asme_design_sa_1e7_zero_mean_mpa"), abs=0.05)
    for n, key in ((1e5, "1e5"), (1e6, "1e6"), (1e7, "1e7")):
        assert m.require(f"fatigue_strength_{key}_r_minus1_mpa") == pytest.approx(sn_fit(n, m), abs=0.1)
    # the legacy 5e8 limit is the fit floor
    assert m.require("fatigue_limit_mpa") == m.require("sn_fit_floor_mpa")


@pytest.mark.parametrize("key,N", [("1e5", 1e5), ("1e6", 1e6), ("1e7", 1e7)])
def test_mean_stress_corrections(key, N):
    m = mat.load("alu_6061_t6")
    su, sf = m.require("goodman_ultimate_mpa"), sn_fit(N, m)
    sy = mat.load("alu_6061_t6_drawn_tube").require("yield_strength_mpa")  # 240, ASTM drawn-tube minimum
    assert su == m.require("ultimate_strength_sbasis_mpa")
    assert m.require(f"fatigue_smax_{key}_r01_goodman_mpa") == pytest.approx(goodman_smax(sf, su, 0.1), abs=0.1)
    assert m.require(f"fatigue_smax_{key}_r0_goodman_mpa") == pytest.approx(goodman_smax(sf, su, 0.0), abs=0.1)
    ger = min(gerber_smax(sf, su, 0.1), sy)  # capped at yield
    assert m.require(f"fatigue_smax_{key}_r01_gerber_mpa") == pytest.approx(ger, abs=1.0)
    # Goodman is the conservative (design) correction
    assert m.require(f"fatigue_smax_{key}_r01_goodman_mpa") < m.require(f"fatigue_smax_{key}_r01_gerber_mpa")


def test_bl080_allowable_was_unconservative():
    """BL-080 Basquin (0.9 Su at 1e3 to the scaled 5e8 limit) gave 74.0 MPa notched R 0 at Kt 3; the cited fit gives
    63.6 (Goodman) / about 79 (Gerber)."""
    m = mat.load("alu_6061_t6")
    su = 290.0
    se = m.require("fatigue_limit_mpa") * su / m.require("ultimate_strength_mpa")
    b = math.log10(se / (0.9 * su)) / math.log10(5e8 / 1e3)
    s_bl080 = 0.9 * su * (1e5 / 1e3) ** b
    assert 2 * s_bl080 / (3 * (1 + s_bl080 / su)) == pytest.approx(74.0, abs=0.1)
    assert s_bl080 / m.require("fatigue_strength_1e5_r_minus1_mpa") == pytest.approx(1.26, abs=0.01)
    assert m.require("fatigue_smax_1e5_r0_goodman_mpa") / 3 == pytest.approx(63.6, abs=0.1)
    assert gerber_smax(m.require("fatigue_strength_1e5_r_minus1_mpa"), su, 0.0) / 3 == pytest.approx(79.0, abs=0.3)


def test_notch_sensitivity_from_bennett_weinberg():
    m = mat.load("alu_6061_t6")
    kt = m.require("notch_kt_test_ratio")
    for key in ("1e6", "1e7"):
        q = (m.require(f"notch_kf_{key}_ratio") - 1) / (kt - 1)
        assert q == pytest.approx(m.require(f"notch_sensitivity_{key}_ratio"), abs=0.01)
    assert m.require("notch_sensitivity_design_ratio") == 1.0
    # the D5.3 hole radius is larger than the tested fillet, so q only rises (Peterson q = 1 / (1 + a / r))
    assert 5.3 / 2 > m.require("notch_radius_test_mm")
    assert m.require("bolted_joint_preload_credit_ratio") == 1.0
    assert 0.5 <= m.require("anodize_fatigue_knockdown_ratio") < 1.0


@pytest.mark.parametrize("size,od_key,wall_key", [("1x049", "od_1_in_mm", "wall_049_in_mm"),
                                                  ("3_4x035", "od_3_4_in_mm", "wall_035_in_mm")])
def test_ring_crush_and_ovalisation(size, od_key, wall_key):
    m = mat.load("alu_6061_t6_drawn_tube")
    E, sy, nu = m.require("youngs_modulus_mpa"), m.require("yield_strength_mpa"), m.require("poisson")
    t = m.require(wall_key)
    R = (m.require(od_key) - t) / 2
    assert m.require(f"diametral_first_yield_{size}_n_mm") == pytest.approx(math.pi * sy * t * t / (6 * R), abs=0.01)
    assert m.require(f"diametral_collapse_{size}_n_mm") == pytest.approx(sy * t * t / R, abs=0.05)
    assert m.require(f"ovalisation_at_10_n_mm_{size}_mm") == pytest.approx(
        0.1488 * 10 * R ** 3 * 12 / (E * t ** 3), abs=0.001)
    assert m.require(f"hoop_yield_pressure_{size}_mpa") == pytest.approx(sy * t / R, abs=0.01)
    assert m.require(f"ring_buckling_pressure_{size}_mpa") == pytest.approx(
        E / (4 * (1 - nu ** 2)) * (t / R) ** 3, abs=0.01)
    assert m.require(f"diametral_collapse_{size}_n_mm") > m.require(f"diametral_first_yield_{size}_n_mm")


def test_through_bolt_needs_crush_sleeve():
    m = mat.load("alu_6061_t6_drawn_tube")
    w = 2600 / 20  # ASSUMPTION CLAMP-PRELOAD 2.6 kN per M5 over a 20 mm saddle
    assert w / m.require("diametral_collapse_1x049_n_mm") > 4


def test_friction_design_values():
    m = mat.load("alu_6061_t6_drawn_tube")
    assert m.require("alu_6061_dry_cof") == 0.19  # VDI 2230 Table A6 lower bound
    assert m.require("alu_6061_lubricated_upper_cof") < m.require("alu_6061_wet_cof") < m.require("alu_6061_dry_cof")
    for cp in ("alu_6061", "paht_cf", "tpu_95a", "epdm_tape"):
        assert 0 < m.require(f"{cp}_wet_cof") < m.require(f"{cp}_dry_cof") <= 0.5
    # concept B upper tee slip margin at the wet design value
    assert 1.63 * m.require("alu_6061_wet_cof") / 0.2 == pytest.approx(1.22, abs=0.01)
    assert "CL-1" in m.notes


def test_prices_and_shipping():
    m = mat.load("alu_6061_t6_drawn_tube")
    assert m.require("price_1x049_72in_usd") == 43.20
    assert m.require("price_3_4x035_72in_usd") == 24.95
    assert m.require("price_1x049_48in_usd") == 34.56  # unchanged from BL-080
    assert m.require("ups_additional_handling_length_mm") == pytest.approx(48 * 25.4, abs=1)
    assert m.require("ship_72in_box_estimate_usd") == pytest.approx(
        m.require("ship_ground_base_estimate_usd") + m.require("ups_additional_handling_max_usd"), abs=0.6)
    # concept B tube: 2 x 36 in (540 + 220 mm each, under the 48 in handling trigger) beats one 72 in piece delivered
    assert 540 + 220 + 3 < 36 * 25.4
    two36 = 2 * m.require("price_1x049_36in_usd") + m.require("ship_ground_base_estimate_usd")
    one72 = m.require("price_1x049_72in_usd") + m.require("ship_72in_box_estimate_usd")
    assert two36 < one72
