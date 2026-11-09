"""Material records for hipbelt concept B (adopted 2026-11-09, docs/DECISIONS.md) and the `_cof` key suffix."""
import json
from pathlib import Path

import pytest

from huntkit import materials as mat
from huntkit.materials.validate import validate_record

RESULTS = Path(__file__).resolve().parents[1] / "designs" / "pack_5200" / "concepts" / "hipbelt_results.json"

BELT_B_IDS = [
    # layup (hipbelt_concepts.py, B): shell, face, load / comfort / crest-relief foams, stiffener
    "cordura_330d_nylon66", "spacer_mesh_3d", "eva_foam_45c", "eva_foam_30c", "eva_foam_perforated", "hdpe_sheet",
    # closure and 2:1 pull
    "nylon_webbing_50mm", "buckle_side_release_50mm", "poly_webbing_25mm",
    "ladder_lock_25mm_heavy", "d_ring_25mm_aluminium",
    # grip face (HB-2)
    "silicone_grip_print", "silicone_gripper_elastic_25mm",
]


@pytest.mark.parametrize("mid", BELT_B_IDS)
def test_belt_b_records_present_and_sourced(mid):
    m = mat.load(mid)
    assert m.sources and m.confidence in mat.CONFIDENCE_LEVELS
    assert m.cost_usd and m.cost_usd["value"] > 0


def test_foams_have_model_inputs():
    # hipbelt.py reads compression_25pct_kpa for every foam layer; HDPE needs a modulus
    for mid in ("eva_foam_45c", "eva_foam_30c", "eva_foam_perforated"):
        assert mat.load(mid).require("compression_25pct_kpa") > 0
    assert mat.load("hdpe_sheet").require("youngs_modulus_mpa") > 0


def _b_rows():
    rows = json.loads(RESULTS.read_text())["rows"]
    return [r for r in rows if r["design"] == "B"]


def test_heavy_ladder_lock_margin_on_2to1_pull():
    """The lock leg of the 2:1 carries pull_n = T / (2 x 0.85); need >= 1.5x on slip for every B size."""
    slip = mat.load("ladder_lock_25mm_heavy").require("slip_load_n")
    rows = _b_rows()
    assert {r["size"] for r in rows} == {"S", "M", "L", "XL", "XXL"}
    worst = max(r["pull_n"] for r in rows)
    assert slip / worst >= 1.5
    assert slip / max(r["T_req_n"] / 2 for r in rows) >= 1.5
    # the classic ladder lock does not meet it (the hipbelt_fit.md flag)
    assert mat.load("ladder_lock_25mm").require("slip_load_n") / worst < 1.5
    # break is above slip
    assert mat.load("ladder_lock_25mm_heavy").require("breaking_strength_n") > slip


def test_d_ring_carries_limit_belt_tension():
    ring = mat.load("d_ring_25mm_aluminium")
    t_max = max(r["T_req_n"] for r in _b_rows())
    assert ring.require("breaking_strength_n") >= 2.0 * t_max * 1.5   # limit 2.0 x T, then 1.5 on break
    assert ring.require("mass_g") <= 10


def test_grip_print_friction_and_mass():
    g = mat.load("silicone_grip_print")
    assert 0.3 < g.require("skin_dry_cof") < 1.5
    assert g.require("polyester_fabric_dry_cof") > 0.45   # above the HB-2 credit threshold, before the shirt/skin limit
    # areal density follows the stated dot pattern: coverage x height x density
    est = g.require("coverage_pct") / 100 * g.require("dot_height_mm") * 1e-3 * g.require("density_kg_m3") * 1e3
    assert g.require("areal_density_g_m2") == pytest.approx(est, rel=0.1)
    assert mat.query(skin_dry_cof__gt=0)


def test_cof_suffix_validates():
    good = {"id": "x_rec", "name": "x", "category": "polymers", "generic": True, "confidence": "estimate",
            "sources": ["s"], "properties": {"skin_dry_cof": 0.6}}
    assert validate_record(good) == []
    bad = dict(good, properties={"skin_dry_mu": 0.6})
    assert any("unit suffix" in e for e in validate_record(bad))
