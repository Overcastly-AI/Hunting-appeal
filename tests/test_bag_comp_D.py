"""Team D (MODULE) bag competition entry CACHE: mass accounting, fixed-list geometry, access and result.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "designs" / "pack_5200" / "bag_comp" / "D"
sys.path.insert(0, str(D))

import cache as C  # noqa: E402


@pytest.fixture(scope="module")
def sysm():
    return C.system()


def test_corrie_baseline_same_metric():
    c2 = C.corrie_b2_system()
    # body group is corrie.build() B.2: 533.1 g in corrie_body.md section 12; BL-035 re-run on the BL-034 records:
    # 559.1 g = +26.0 g, the two #10 door sliders at the slider_10 record (19.0 g, was 6 g ASSUMPTION)
    assert dict(c2["items"])["body group (shell, collar, swells, accents, wings, pouch, door zip, wing/pouch hardware)"] \
        == pytest.approx(559.1, abs=0.5)
    assert c2["total_g"] == pytest.approx(sum(g for _, g in c2["items"]), abs=0.2)


def test_mass_rows_add_up(sysm):
    assert sysm["bag_system_g"] == pytest.approx(sum(g for _, g in sysm["rows"]), abs=0.5)
    assert C.pack_mass_M(sysm) == pytest.approx(3943.0 - sysm["corrie_b2"]["total_g"] + sysm["bag_system_g"], abs=0.1)


def test_shell_drops_wings_rolltop_pouch():
    _, b = C.shell()
    ids = {p.piece_id for p, _ in b.pieces}
    assert not ids & {"M-01", "SH-06", "B-07", "B-07s", "L-21", "L-22", "L-23"}
    assert {"B-01", "B-03", "B-05", "B-02door", "B-02u", "B-02h", "B-06f", "D-07"} <= ids
    assert not any(h[0].startswith("wing strap") for h in b.extra["hardware"])


def test_modules_fit_the_section():
    """Every in-bag module fits inside the rev B section: width <= 394 mm (15.5 in), depth <= 270 mm, and the CAMP
    module passes the door opening (2 x (a - inset)) at z 400, where it slides out (below, the soft module squeezes)."""
    import corrie as CO
    c = CO.make()
    a_mid = float(c.a([400.0])[0])
    door_w = 2 * (a_mid - CO.DOOR["inset"])
    for m in C.modules():
        W, Dd, H = m["dims_mm"]
        assert W <= 394.0 and Dd <= 270.0
    camp = next(m for m in C.modules() if m["id"] == "MC")
    assert camp["dims_mm"][0] <= door_w


def test_quiet_no_hook_and_loop_no_buckles_on_modules():
    for m in C.modules() + C.pods():
        for name, _ in m["hw"]:
            assert "hook-and-loop" not in name.lower() and "velcro" not in name.lower()
    # module roll closures are G-hook keepers, not side-release buckles
    for m in C.modules():
        assert not any("SR buckle" in n for n, _ in m["hw"])


def test_result_json_schema():
    f = D / "result.json"
    if not f.exists():
        pytest.skip("result.json not written yet")
    r = json.loads(f.read_text())
    keys = {"team", "name", "one_line", "bag_system_g", "pack_mass_M_g", "volume_L", "fill_height_in", "pieces",
            "curved_seams", "zip_mm_total", "beginner_hours", "cg_fill_mm", "cg_meat_mm", "cg_method", "access_misses",
            "features", "risks", "screenshots"}
    assert keys <= set(r)
    assert set(r["cg_fill_mm"]) == set(r["cg_meat_mm"]) == {"15", "19", "23"}
    assert all(v <= 205.0 for v in r["cg_fill_mm"].values())
    assert all(v <= 190.0 for v in r["cg_meat_mm"].values())
    assert 82.0 <= r["volume_L"] <= 88.2 + 3          # sim volume of the CORRIE shell (85.2 L design basis)
    assert r["cg_method"] in ("clothsim", "estimate")
    assert set(r["access_misses"]) == {"day", "elk6", "sheep8"}
    assert r["bag_system_g"] == pytest.approx(C.system()["bag_system_g"], abs=0.5)


def test_loadout_day_and_elk_have_no_hourly_miss():
    import cache_loadout as LO
    r = LO.run()
    m = LO.misses(r, "M")
    assert m["day"] == [] and m["elk6"] == []
