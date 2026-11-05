"""designs/pack_5200/build_geometry.py is the single source of truth for geometry.yaml and panels.yaml.

Running the generator must reproduce the committed files byte for byte, so nobody hand-edits them again.
If this fails: change build_geometry.py, then run `python designs/pack_5200/build_geometry.py`.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "designs" / "pack_5200"
sys.path.insert(0, str(PACK))


@pytest.fixture(scope="module")
def built():
    import build_geometry as BG
    geom, pan, ctx = BG.build()
    return BG, geom, pan, ctx


def test_geometry_yaml_matches_generator(built):
    BG, geom, _, _ = built
    committed = (PACK / "geometry.yaml").read_text()
    assert BG.render_yaml(geom) == committed, "geometry.yaml drifted from build_geometry.py: re-run the generator"


def test_panels_yaml_matches_generator(built):
    BG, _, pan, _ = built
    committed = (PACK / "panels.yaml").read_text()
    assert BG.render_yaml(pan) == committed, "panels.yaml drifted from build_geometry.py: re-run the generator"


def test_head_setback_is_the_two_ring_seams_the_patterns_use(built):
    BG, geom, _, _ = built
    sb = geom["bag"]["head_setback"]
    assert sb["z_setback_seam"] == pytest.approx(560.0)
    # shoulder seam = the diagonal zip's upper end (patterns_v31.Z_SH reads it from there)
    assert sb["z_shoulder_seam"] == pytest.approx(geom["bag"]["diagonal"]["zip_end_left"][2], abs=0.05)
    st = [r for r in geom["bag"]["profile"]["stations"] if sb["z_setback_seam"] < r[0] < sb["z_shoulder_seam"]]
    assert len(st) >= 3
    # ruled band: the frame-face y is linear in z between the two seam rings
    Hf = geom["bag"]["height_z"]
    y1 = float(BG.y_frame(sb["z_setback_seam"], Hf)[0])
    y2 = float(BG.y_frame(sb["z_shoulder_seam"], Hf)[0])
    for z, _, y, _ in st:
        w = (z - sb["z_setback_seam"]) / (sb["z_shoulder_seam"] - sb["z_setback_seam"])
        assert y == pytest.approx(y1 + w * (y2 - y1), abs=0.02)
    # volume: as-sewn stays inside R-01 (85.2 +/- 1 L) and the band costs well under 0.1 L
    assert abs(geom["volumes"]["main_bag_L"] - 85.2) <= 1.0
    assert -0.1 < sb["volume_effect_L"] <= 0.0


def test_weight_budget_is_the_production_pack(built):
    _, geom, pan, _ = built
    w = geom["weight"]
    assert w["total_g"] == pytest.approx(sum(r["mass_g"] for r in w["rows"]), abs=0.6)
    assert w["total_g"] == pytest.approx(sum(w["groups_g"].values()), abs=0.6)
    assert w["gap_g"] == pytest.approx(w["total_g"] - w["target_g"], abs=0.1)
    frame = next(k for k in w["groups_g"] if k.startswith("frame"))     # viz3d reads the frame line by prefix
    assert w["groups_g"][frame] > 900                                   # printed branch frame, not the v2 tube
    assert w["v31_tube_baseline"]["total_g"] == pytest.approx(2224.1)  # frozen basis of frame_production.SOFT_GOODS_G
    ids = {p["id"] for p in pan["panels"]}
    assert "B-10" not in ids                                            # retired with the fairlead attachment
    assert pan["meta"]["piece_count_total"] == sum(p["qty_total"] for p in pan["panels"])
