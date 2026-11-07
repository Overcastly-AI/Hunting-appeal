"""Bag-body concept study (designs/pack_5200/concepts/bag_concepts.py): volumes, frame interface, patterns."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))

import bag_concepts as BC  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def built():
    out = {}
    for c in BC.all_concepts():
        out[c.key] = (c, BC.build_concept(c))
    return out


def test_integrator_reproduces_spine():
    chk = BC.spine_volume_check()
    assert chk["volume_L"] == pytest.approx(85.14, abs=0.1)
    assert chk["cg_y"] == pytest.approx(148.2, abs=1.0)
    assert chk["cg_z"] == pytest.approx(592.5, abs=1.0)


def test_dome_law_calibrated_on_spine():
    raw = BC.spine_dome_check()
    assert abs(raw["err_pct_of_bag"]) < 2.0            # stated uncertainty of the law
    cal = BC.spine_dome_check(BC.DOME_CAL)
    assert cal["err_L"] == pytest.approx(0.0, abs=1e-6)


def test_every_concept_holds_5200_cu_in_inside_owner_envelope(built):
    for c, _ in built.values():
        v = BC.volumes(c)
        assert v["volume_L"] == pytest.approx(BC.TARGET_L, abs=0.05)
        assert v["width_max_in"] == pytest.approx(15.5, abs=0.05)     # owner freeze
        assert v["max_depth_in"] <= 12.0                               # owner 11.5-12 in cap
        assert 39.0 <= v["fill_height_in"] <= 42.5                    # ~42 in (owner), never taller


def test_frame_interface_kept(built):
    for c, b in built.values():
        # setback creases at the released seam heights; B-01 at least as wide as SPINE's at the hinge / IM stations
        assert BC.Z_SB == 560.0 and BC.Z_SH == pytest.approx(631.2)
        for z in BC.STATIONS.values():
            a_spine = float(np.interp(z, BC.SPINE_ST[:, 0], BC.SPINE_ST[:, 1]))
            assert float(c.a([z])[0]) >= a_spine - 5.0          # within 5 mm of SPINE (z 520: -3.4 mm)
            assert float(c.a([z])[0]) > BC.STAY_X + 20.0
        assert float(BC.setback([700])[0]) == pytest.approx(30.0)
        ids = {p.piece_id for p, _ in b.pieces}
        assert "B-01" in ids and "B-13x" in ids                       # one flat frame panel + 8 boxed swells
        if c.z_c < BC.LADDER_TOP - 15.0:   # B-20 ladder may overhang the collar seam <= 14 mm (released SPINE 13.8)
            assert "B-06f" in ids


def test_seams_match_and_slab_is_all_straight(built):
    for key, (c, b) in built.items():
        rep = check_seams([s for s, t in b.seams if "flat" not in t], tol_mm=1.0)
        assert rep.ok, (key, str(rep))
    m = BC.metrics(built["slab"][1])
    assert m["curved_seams"] == 0 and m["zips"] == 1
    assert BC.metrics(built["twin"][1])["curved_seams"] == 0


def test_box_unfold_is_exact(built):
    c, b = built["slab"]
    B1 = next(p for p, _ in b.pieces if p.piece_id == "B-01")
    zk = np.array(sorted({BC.Z0, BC.Z_SB, BC.Z_SH, c.z_c}))
    P = np.column_stack([c.a(zk), BC.y_frame(zk), zk])
    L3 = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    assert B1.edge_length("right") == pytest.approx(L3, abs=0.01)


def test_wrap_is_developable_and_zip_straight(built):
    c, b = built["wrap"]
    for st in b.strain.values():
        assert st["p99_pct"] < 2.0                                     # patterns_v31 acceptance
    lo = next(p for p, _ in b.pieces if p.piece_id == "W-02b")
    pts = np.asarray(lo.edge_points("split"))
    ch = pts[-1] - pts[0]
    dev = np.abs(ch[0] * (pts[:, 1] - pts[0, 1]) - ch[1] * (pts[:, 0] - pts[0, 0])) / np.linalg.norm(ch)
    assert dev.max() < 2.0                                             # straight zip on the flat


def test_edge_shape_classifier():
    assert BC.edge_shape([(0, 0), (100, 0), (200, 0)]) == (0.0, 0)
    sag, piv = BC.edge_shape([(0, 0), (100, 0), (200, 30)])            # kink between two long runs = pivot
    assert piv == 1 and sag == pytest.approx(0.0)
    t = np.linspace(0, np.pi, 100)
    sag, piv = BC.edge_shape(np.column_stack([100 * np.cos(t), 100 * np.sin(t)]))
    assert piv == 0 and sag > BC.CURVE_SAGITTA


def test_scoring_and_results_file():
    rows = {k: {"metrics": {"hours_total": h, "mass_g": {"total": m}, "curved_seams": cs},
                "volumes": {"cg_y": y, "cg_z": z}}
            for k, h, m, cs, y, z in [("spine", 35, 333, 14, 148, 592), ("slab", 20, 360, 0, 149, 558),
                                      ("twin", 19, 386, 0, 149, 558), ("wrap", 22, 363, 3, 142, 590),
                                      ("hatch", 23, 383, 1, 149, 558)]}
    sc = BC.score(rows)
    assert sc["slab"]["build"] > sc["spine"]["build"]
    assert sc["spine"]["mass"] == 5.0
    assert abs(sum(BC.WEIGHTS.values()) - 1.0) < 1e-9
    res = ROOT / "designs" / "pack_5200" / "concepts" / "concepts_results.json"
    if res.exists():
        d = json.loads(res.read_text())
        assert {"spine", "slab", "twin", "wrap", "hatch"} <= set(d["rows"])
        assert d["rows"]["spine"]["mass_delta_g"] == 0.0
