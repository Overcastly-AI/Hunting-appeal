"""Tests for huntkit.materials (contract docs/CONTRACTS.md §1)."""
from pathlib import Path

import pytest
import yaml

from huntkit import materials as mat
from huntkit.materials import cli
from huntkit.materials.validate import validate_all, validate_record

REQUIRED_IDS = [
    "alu_7075_t6", "alu_6061_t6", "alu_7001_t6_tube", "ti_6al_4v", "ti_3al_2_5v_tube",
    "cfrp_t700_ud_epoxy_ply", "cfrp_t300_3k_woven_epoxy_ply", "cfrp_m40j_ud_epoxy_ply",
    "cfrp_pultruded_rod_tube", "gfrp_eglass_ud_epoxy_ply",
    "hdpe_sheet", "uhmwpe_sheet", "pom_acetal", "pa66_gf30", "tpu_sheet_film",
    "cordura_500d_nylon66", "dcf_ct9hk_18", "xpac_vx21", "spacer_mesh_3d",
    "merino_190_jersey", "laminate_3l_eptfe", "down_850fp_hydrophobic",
    "eva_foam_45c", "xlpe_foam", "nylon_webbing_50mm", "bonded_nylon_tex90",
    "coil_zipper_8", "buckle_side_release_50mm", "dyneema_cord_2mm",
    # owner decisions 2026-11-01: carbon frame, meat hauling, camo accents
    "cfrp_rollwrapped_tube", "cfrp_plate_quasi_iso", "cfrp_plate_0_90_woven", "cfrp_plate_pm45",
    "adhesive_epoxy_toughened_2part", "adhesive_methacrylate_ma",
    "insert_al_7075_bonded", "insert_ti_6al_4v_bonded",
    "polyester_ht_630d_printable", "poly_spandex_stretch_woven_printable",
    "pvc_coated_polyester_18oz", "silicone_coated_poly_ripstop_40d",
]


# ---- loader ------------------------------------------------------------------
def test_load_returns_material():
    m = mat.load("alu_7075_t6")
    assert isinstance(m, mat.Material)
    assert m.id == "alu_7075_t6"
    assert m.category == "metals"
    assert m.confidence in mat.CONFIDENCE_LEVELS
    assert m.props["density_kg_m3"] == pytest.approx(2810)
    assert m.sources


def test_get_and_require():
    m = mat.load("alu_7075_t6")
    assert m.get("yield_strength_mpa") == pytest.approx(503)
    assert m.get("not_a_prop") is None
    assert m.get("not_a_prop", 7) == 7
    assert m.require("youngs_modulus_mpa") == pytest.approx(71700)
    with pytest.raises(KeyError) as exc:
        m.require("not_a_prop")
    assert "alu_7075_t6" in str(exc.value) and "not_a_prop" in str(exc.value)


def test_unknown_id_suggests():
    with pytest.raises(mat.MaterialError, match="alu_7075_t6"):
        mat.load("alu_7075_t")


@pytest.mark.parametrize("mid", REQUIRED_IDS)
def test_required_records_present(mid):
    assert mat.load(mid).id == mid


def test_all_materials_count_and_unique():
    allm = mat.all_materials()
    assert 45 <= len(allm) <= 110
    ids = [m.id for m in allm]
    assert len(ids) == len(set(ids))
    assert {m.category for m in allm} == set(mat.CATEGORIES)


# ---- query -------------------------------------------------------------------
def test_query_category():
    metals = mat.query("metals")
    assert metals and all(m.category == "metals" for m in metals)
    with pytest.raises(mat.MaterialError):
        mat.query("not_a_category")


def test_query_comparisons():
    light = mat.query("textiles", areal_density_gsm__lt=150)
    assert light and all(m.props["areal_density_gsm"] < 150 for m in light)
    assert all(m.category == "textiles" for m in light)
    lte = mat.query("metals", density_kg_m3__lte=2810)
    assert {m.id for m in lte} >= {"alu_7075_t6", "alu_6061_t6"}
    assert "ti_6al_4v" not in {m.id for m in lte}
    strong = mat.query("metals", yield_strength_mpa__gt=600)
    assert {m.id for m in strong} == {"alu_7001_t6_tube", "ti_6al_4v", "ti_3al_2_5v_tube", "ti_6al_4v_slm"}
    gte = mat.query(yield_strength_mpa__gte=880)
    assert "ti_6al_4v" in {m.id for m in gte}


def test_query_in_contains_eq_and_missing():
    sel = mat.query(id__in=["alu_7075_t6", "hdpe_sheet"])
    assert {m.id for m in sel} == {"alu_7075_t6", "hdpe_sheet"}
    merino = mat.query("textiles", fiber__contains="merino")
    assert len(merino) >= 4
    zips = mat.query("hardware", zipper_size=8)
    assert {m.id for m in zips} == {"coil_zipper_8", "aquaguard_zipper_8"}
    closed = mat.query("foams", closed_cell=True)
    assert "pu_memory_foam" not in {m.id for m in closed}
    # records lacking the filtered property are excluded, not errors
    assert all("E1_mpa" in m.props for m in mat.query(E1_mpa__gt=0))
    assert mat.query(confidence="handbook")
    assert all(m.get("quietness_1to5", 0) >= 5 for m in mat.query(quietness_1to5__gte=5))
    # list-valued top-level field: membership
    assert mat.query(trade_names__contains="Toray TORAYCA M40J")


def test_adhesives_and_meat_zone_props():
    for a in mat.query(lap_shear_strength_mpa__gt=0):
        assert a.require("service_temp_max_c") > 0
        assert "floating_roller_peel_n_mm" in a.props
    assert len(mat.query(lap_shear_strength_mpa__gt=0)) >= 2
    best = mat.query("textiles", hydrolysis_resistance_1to5__gte=4, abrasion_taber_cycles__gte=3000)
    assert "tpu_coated_nylon_840d" in {m.id for m in best}
    pu = [m for m in mat.query(coating__contains="PU back coat") if "TPU" not in m.props["coating"]]
    assert pu and all(m.props["hydrolysis_resistance_1to5"] <= 2 for m in pu)


# ---- validation ---------------------------------------------------------------
def test_all_records_validate():
    problems = validate_all()
    assert not problems, "\n".join(f"{p}: {e}" for p, e in problems.items())


def _good():
    return yaml.safe_load(Path(mat.load("hdpe_sheet").path).read_text())


def test_validator_catches_errors(tmp_path):
    good = _good()
    p = tmp_path / "polymers" / "hdpe_sheet.yaml"
    assert validate_record(good, p) == []

    bad = dict(good, id="other")
    assert any("stem" in e for e in validate_record(bad, p))
    bad = dict(good, category="plastics")
    assert any("category" in e for e in validate_record(bad))
    bad = dict(good, confidence="trust me")
    assert any("confidence" in e for e in validate_record(bad))
    bad = {k: v for k, v in good.items() if k != "sources"}
    assert any("sources" in e for e in validate_record(bad))
    bad = dict(good, properties={**good["properties"], "stiffness": 5})
    assert any("unit suffix" in e for e in validate_record(bad))
    bad = dict(good, cost_usd={"value": 3, "per": "bucket"})
    assert any("cost_usd" in e for e in validate_record(bad))


def test_validate_all_on_tmp_tree(tmp_path):
    good = _good()
    d = tmp_path / "polymers"
    d.mkdir()
    (d / "hdpe_sheet.yaml").write_text(yaml.safe_dump(good))
    (d / "wrong_name.yaml").write_text(yaml.safe_dump(good))
    probs = validate_all(tmp_path)
    assert list(probs) == [d / "wrong_name.yaml"]


# ---- CLI ---------------------------------------------------------------------
def test_cli(capsys):
    assert cli.main(["validate"]) == 0
    assert cli.main(["list", "-c", "metals"]) == 0
    assert cli.main(["show", "ti_6al_4v"]) == 0
    assert cli.main(["compare", "alu_7075_t6", "ti_6al_4v"]) == 0
    out = capsys.readouterr().out
    assert "ti_6al_4v" in out and "E/rho" in out
    assert cli.main(["show", "nope"]) == 2
