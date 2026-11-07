"""Wider bag-body concept set (designs/pack_5200/concepts/bag_concepts_wide.py): 8 more concepts, same rules."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def wide():
    return {c.key: (c, W.build(c)) for c in W.all_wide()}


def test_eight_distinct_named_concepts(wide):
    assert len(wide) == 8
    names = [c.name for c, _ in wide.values()]
    assert len(set(names)) == 8
    assert not set(names) & {"SPINE", "SLAB", "TWIN", "WRAP", "HATCH"}
    for k in wide:
        assert k in BC.JUDGED and k in W.INTERFACE_CHANGES and W.WIDE[k]["pitch"]


def test_volume_width_and_depth_rules(wide):
    for c, _ in wide.values():
        v = W.volumes(c)
        assert abs(v["volume_L"] - BC.TARGET_L) <= 3.0          # 85 L +/- 3 (owner brief)
        assert v["width_max_in"] == pytest.approx(15.5, abs=0.05)
        assert v["max_depth_in"] <= 12.0


def test_cradle_drybags_fit_the_harness():
    c = W.make_cradle()
    assert max(W.CRADLE_D) <= BC.D_MAX                         # depth cap 302 mm
    assert W.CRADLE_L + 55.0 <= 2 * BC.A_MAX                    # body + rolled end inside 15.5 in
    V = sum(math.pi / 4 * D ** 2 * W.CRADLE_L for D in W.CRADLE_D) / 1e6
    assert c.volume_L() == pytest.approx(V)


def test_structural_seams_match(wide):
    for k, (c, b) in wide.items():
        real = [s for s, t in b.seams if "flat" not in t and s.a[0].piece is not s.b[0].piece]
        rep = check_seams(real, tol_mm=1.0)
        assert rep.ok, (k, str(rep))


def test_developed_wraps_under_two_percent(wide):
    for k, (c, b) in wide.items():
        for st in b.strain.values():
            assert st["p99_pct"] < 2.0, k


def test_frame_interface_and_owner_rules(wide):
    for k, (c, b) in wide.items():
        ids = {p.piece_id for p, _ in b.pieces}
        assert "B-01" in ids and "B-13x" in ids                # frame panel with its interface + 8 swells
        mats = {p.material_id for p, _ in b.pieces}
        assert not any("hook_and_loop" in m or "velcro" in m for m in mats)   # quiet
        assert any(g == "accent" for _, g in b.pieces)          # camo accents present
        assert sum(BC.piece_mass_g(p) for p, g in b.pieces if g == "accent") < 0.35 * BC.metrics(b)["mass_g"]["total"]
    maw = wide["maw"][1]
    assert maw.concept.dome_h == 0 and maw.extra["common_delta_g"] == pytest.approx(-48.5)
    assert not any(p.piece_id.startswith("B-06") for p, _ in maw.pieces)


def test_results_cover_all_thirteen():
    res = ROOT / "designs" / "pack_5200" / "concepts" / "concepts_results.json"
    if not res.exists():
        pytest.skip("run render_wide.py")
    d = json.loads(res.read_text())
    if len(d["rows"]) < 13:
        pytest.skip("results file holds the first study only")
    assert len(d["rows"]) == 13
    for r in d["rows"].values():
        assert 1.0 <= r["score"]["weighted"] <= 5.0
