"""CORRIE rev B.2 (2026-11-09, DECISIONS "Owner: 'Yes' to the weight-pass recommendation"): packages A + B without the
held B-8 / B-9 applied in designs/pack_5200/concepts/corrie.py (default spec), B.1 reproducible behind the flag, the
booking gaps G-1 / G-2 booked, the loadout re-run (corrie_loadout.py)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "designs" / "pack_5200" / "concepts"))
sys.path.insert(0, str(ROOT))

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
from huntkit.patterns import check_seams  # noqa: E402


@pytest.fixture(scope="module")
def builds():
    c = CO.make()
    return c, CO.build(c, True, spec="B.1"), CO.build(c, True, spec="B.2")


def test_b2_is_the_default_and_b1_stays_reproducible():
    assert CO.SPEC == "B.2" and set(CO.SPECS) == {"B.1", "B.2"}
    for s in CO.BELT_SIZES:
        w1, w2 = CO.weight_table(s, spec="B.1"), CO.weight_table(s, spec="B.2")
        assert CO.weight_table(s)["total_g"] == w2["total_g"]
        assert math.isclose(sum(r[1] for r in w2["rows"]), w2["total_g"], abs_tol=0.5)
        # B.1 books none of the B.2 rows
        assert not any(r[0].startswith(("A-2", "B-10", "G-1", "G-2")) for r in w1["rows"])
        assert 60.0 < w1["total_g"] - w2["total_g"] < 110.0
    # B.2 was published within 200 g of PUBLISH_G. Re-booked on the hardware records (BL-034: #10 door sliders +26.0,
    # IMP-4 #5 slider +1.9; BL-035: corrie.spine_rebooked_g +18.6 = stainless US tri-glides, hook keepers, lifter
    # tri-glides, torso adjust) it is 4011.0 g: HONEST RESULT, now 11 g over that bound (B.2 is superseded by CORRIE F)
    w = CO.weight_table("M", spec="B.2")["total_g"]
    assert w == pytest.approx(4011.0, abs=0.1)
    assert w - CO.spine_rebooked_g() - 27.9 < CO.PUBLISH_G + 200.0       # the bound held on the old hardware masses


def test_b2_items_in_the_build(builds):
    c, b1, b2 = builds
    ids1, ids2 = {p.piece_id for p, _ in b1.pieces}, {p.piece_id for p, _ in b2.pieces}
    assert "SH-03" in ids1 and "SH-03" not in ids2                       # B-2 (not S-12: the hem B-07 stays 330D)
    assert next(p for p, _ in b2.pieces if p.piece_id == "B-07").material_id == "cordura_330d_nylon66"
    pouch = {p.piece_id: p for p, g in b2.pieces if g == "pouch"}
    assert pouch["L-21"].material_id == "cordura_330d_nylon66"           # B-4 solid top
    assert pouch["L-22"].material_id == pouch["L-23"].material_id == "robic_100d_ripstop"   # B-3
    assert "SH-08" in pouch                                              # B-4 camo pull tab
    assert CO.POUCH == CO.POUCH_B2 == {"L": 280.0, "W": 190.0, "H": 60.0}  # B-5
    # B-1: no body seam is bound any more; G-1 books what is left (0 m)
    assert CO.bound_body_m(b1) == pytest.approx(7.28, abs=0.01)
    assert CO.bound_body_m(b2) == 0.0
    assert sum(1 for _, t in b2.seams if "seared" in t) == sum(1 for _, t in b1.seams if "bound" in t)
    real = [s for s, t in b2.seams if "flat" not in t and s.a[0].piece is not s.b[0].piece]
    assert check_seams(real, tol_mm=1.0).ok


def test_b2_pockets_and_belt():
    p1 = {d["id"]: d for d in CO.bag_pockets(spec="B.1")}
    p2 = {d["id"]: d for d in CO.bag_pockets(spec="B.2")}
    assert p2["IMP-1"]["pieces"][0].material_id == "robic_100d_ripstop"          # B-6
    assert not any("G-hook" in n for n, _ in p2["IMP-6"]["hardware"])            # B-7 sewn on
    assert any("G-hook" in n for n, _ in p1["IMP-6"]["hardware"])
    for k in ("IMP-2", "IMP-8"):                                                 # B-10 trims
        assert {p.material_id for p in p2[k]["pieces"]} & {"tpu_coated_nylon_840d"}
        assert "hypalon_coated_nylon" not in {p.material_id for p in p2[k]["pieces"]}
    for k in p1:
        assert p2[k]["mass_g"] <= p1[k]["mass_g"] + 1e-6
    # A-1: unprinted belt face (belt_bom's 5 g grip line out), every size
    for s in CO.BELT_SIZES:
        g1 = next(g for n, g in CO.belt_b(s, spec="B.1")["corrections"] if n.startswith("grip"))
        g2 = next(g for n, g in CO.belt_b(s, spec="B.2")["corrections"] if n.startswith("grip"))
        assert g2 == -5.0 and g1 > g2


def test_b2_booking_rows():
    rows = {r[0][:4]: r[1] for r in CO.weight_table("M", spec="B.2")["rows"]}
    assert rows["A-2 "] == pytest.approx(-3 * 0.10 * CO.WEB25, abs=0.1)
    assert rows["B-10"] < 0
    assert rows["G-1 "] == 0.0
    assert 3.0 < rows["G-2 "] < 10.0


def test_geometry_volume_and_cg_unchanged():
    """B.2 touches no body geometry: same rev B box, volume and uniform-fill CG as B.1; only the pouch shrinks."""
    v = BC.volumes(CO.make())
    assert 74.0 < v["volume_L"] < 78.0
    assert CO.pouch_volume_L(CO.POUCH_B2) == pytest.approx(2.71, abs=0.01)
    assert CO.pouch_volume_L(CO.POUCH_B1) == pytest.approx(4.0, abs=0.1)
    inner = sorted(CO.pouch_interior_mm(), reverse=True)
    for item in ((150, 100, 35), (160, 61, 36)):                               # snacks, sheep GPS (B-5 check)
        assert all(a >= b for a, b in zip(inner, sorted(item, reverse=True)))


def test_loadouts_b2_rev_c_and_known_access_changes():
    import corrie_loadout as L
    data = L.load_yaml()
    assert L.POUCH_ABOVE_TOP == pytest.approx(70.0)
    for size in CO.BELT_SIZES:
        for key in ("day", "elk6", "sheep8"):
            P = L.pack(L.split_units(L.expand(data, key)), f"integrated:{size}")
            s = L.summary(P)
            assert s["rev_c_ok_15in"] and not s["unplaced"]
            if key == "elk6":
                assert not any(v["fail"] for f, v in s["access"].items() if f != "hourly")
    # day hunt: the toilet kit (daily) leaves the 2.7 L pouch; packed by the IMP-4 rule (kill kit owns the door pocket,
    # toilet kit to the bag top) the day hunt keeps B.1's access
    P = L.pack(L.split_units(L.expand(data, "day")), "integrated:M", force={"toilet_kit": ["top_pouch", "bag_A_high"]})
    s = L.summary(P)
    assert s["access"]["kill"]["fail"] == [] and s["access"]["hourly"]["fail"] == ["snacks_today"]
