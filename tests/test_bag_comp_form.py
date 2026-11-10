"""Team E FORM (CHERT) bag competition entry: envelope, fixed-list limits, mass booking and result.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "designs" / "pack_5200" / "bag_comp" / "form"
sys.path.insert(0, str(FORM))

import form as F  # noqa: E402


@pytest.fixture(scope="module")
def c():
    return F.make()


def test_envelope_limits(c):
    zz = np.linspace(F.BC.Z0, c.z_c, 200)
    assert 2 * c.a(zz).max() <= 394.0 + 1e-6          # width <= 15.5 in
    assert c.depth(zz).max() <= 12 * 25.4             # depth <= 12 in


def test_chamfer_tapers_and_door_stays_wide(c):
    cx0, cy0 = (float(v[0]) for v in c.ch([F.BC.Z0]))
    cx1, cy1 = (float(v[0]) for v in c.ch([c.z_c]))
    assert cx0 > cx1 and cy0 > cy1
    assert F.door_width(c, F.DOOR["z_lo"]) >= 160.0    # DECISION in form.py
    assert F.door_width(c, F.DOOR["z_hinge"]) >= 300.0


def test_rule_volume_matches_target(c):
    assert abs(c.volume_L() - F.rule_target_L()) < 0.05


def test_chamfer_moves_uniform_cg_forward(c):
    y, _ = c.cg()
    y0, _ = F.corrie_ref().cg()
    assert y < y0


def test_surface_is_closed_and_on_frame(c):
    S = F.KnapSurface(c)
    for z in (60.0, 400.0, 700.0):
        q = np.linspace(0, 2, 401)[:-1]
        P = S(np.column_stack([q * F.US, np.full(len(q), z)]))
        gaps = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
        assert gaps.max() < 20.0                       # continuous ring
        fr = P[q >= 1.0]
        assert np.allclose(fr[:, 1], F.BC.y_frame([z])[0])   # frame face on the fixed interface plane


def test_result_json_schema():
    f = FORM / "result.json"
    if not f.exists():
        pytest.skip("result.json not written yet")
    r = json.loads(f.read_text())
    keys = {"team", "name", "one_line", "bag_system_g", "pack_mass_M_g", "volume_L", "fill_height_in", "pieces",
            "curved_seams", "zip_mm_total", "beginner_hours", "cg_fill_mm", "cg_meat_mm", "cg_method",
            "access_misses", "features", "risks", "screenshots"}
    assert keys <= set(r)
    assert r["team"] == "E"
    assert abs(r["pack_mass_M_g"] - (3943 - r["corrie_b2_bag_system_g"] + r["bag_system_g"])) < 0.6
    assert set(r["cg_fill_mm"]) == {"15", "19", "23"} and set(r["cg_meat_mm"]) == {"15", "19", "23"}
    if r["cg_method"] == "clothsim":
        assert all(v <= 205.0 for v in r["cg_fill_mm"].values())
        assert all(v <= 190.0 for v in r["cg_meat_mm"].values())
