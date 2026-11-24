"""BL-063 looks concepts: the mass deltas come from the cut list and the material records, and concept C keeps every
strap / clip load piece on its rev 3 fabric."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("concepts_mass",
                                              ROOT / "designs" / "pack_5200" / "iter1" / "looks" / "concepts_mass.py")
CM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CM)


@pytest.fixture(scope="module")
def r():
    return CM.concepts()


def test_concept_A_is_zero_mass(r):
    assert r["A"]["total_g"] == 0.0
    assert all(row["delta_g"] == 0.0 for row in r["A"]["rows"])


def test_concept_B_gusset_swap_matches_records(r):
    c = CM.cut()
    exp = c["B-03"]["area"] * (CM.gsm("polyester_300d_printable") - CM.gsm("cordura_330d_nylon66"))
    assert r["B"]["total_g"] == pytest.approx(round(exp, 1), abs=0.05)
    assert -16.0 < r["B"]["total_g"] < -14.0          # 0.319 m2 x (133 - 180) g/m2


def test_concept_C_keeps_load_pieces_on_330d(r):
    swapped = {row["piece"] for row in r["C"]["rows"] if row["area_m2"] is not None}
    assert {"B-07", "B-29g", "B-03", "B-01"}.isdisjoint(swapped)
    assert swapped == {"B-06", "B-29a", "B-29c", "B-29d", "B-29e"}
    assert -7.0 < r["C"]["total_g"] < -4.0


def test_no_concept_adds_mass(r):
    for k in ("A", "B", "C"):
        assert r[k]["total_g"] <= 0.0


# ---------------------------------------------------------------------------------------------- BL-067 (review 7 M5)
@pytest.fixture(scope="module")
def L():
    return CM.ledger_concepts()


def test_ledger_rows_match_cut_area_times_gsm():
    """The ledger rows the swaps rest on are cut area x g/m2 of the scenario's fabric (so the basis is the ledger)."""
    c = CM.cut()
    for scen in ("P", "A"):
        for pid in ("B-06", "B-03", "B-07"):
            g = CM.ledger_row_g(scen, pid)
            assert g == pytest.approx(c[pid]["area"] * CM.gsm(CM.ledger_material(scen, pid)), abs=0.1), (scen, pid)
    assert CM.ledger_material("A", "B-06") == "nylon_ripstop_70d"          # A swaps the collar to 70D
    assert CM.ledger_material("A", "B-02u") == CM.HYPERD                     # BL-037 G-2


def test_concept_C_reproduces_review7(L):
    """Review 7 M5: C is +3.0 g base proven now, +15.2 g base after tests, +7.0 g as hunted after tests, on the release
    cut list as it was then. BL-068 P2 tapered the roll collar (B-06 cut area -10 %), so the same C swap on today's
    release cut list reads +2.7 / +13.7 / +5.5 g."""
    C = L["C"]
    assert (C["base_P"], C["base_A"], C["hunted_A"]) == (pytest.approx(2.7, abs=0.1), pytest.approx(13.7, abs=0.1),
                                                          pytest.approx(5.5, abs=0.1))


def test_concept_Cp_never_heavier(L):
    cp = L["Cp"]
    assert cp["base_P"] == 0.0 and cp["base_A"] == 0.0                     # lid is as-hunted only
    assert cp["hunted_P"] < 0 and cp["hunted_A"] < 0
    assert {s["piece"] for s in cp["swaps"]} == {"B-29a"}                   # camo on the lid crown only
    for sc in ("P", "A"):
        assert cp[f"base_{sc}_with_geometry"] < 0 and cp[f"hunted_{sc}_with_geometry"] < cp[f"hunted_{sc}"]
    t = cp["geometry"]["ROLL-TAPER"]
    assert t["perimeter_cut_mm"] == pytest.approx(4 * (262.45 - 192.0), abs=0.1)
    assert 0 < cp["geometry"]["collar_volume_loss_L"] < 3.0                # 85 L +/- 3 (RULES 9) holds


def test_bl067_render_constants_match_mass_basis():
    spec = importlib.util.spec_from_file_location(
        "looks_render_src", ROOT / "designs" / "pack_5200" / "iter1" / "looks" / "looks_render.py")
    src = Path(spec.origin).read_text()
    assert f"ROLL_HALF_MM = {CM.ROLL_HALF_CP}" in src
    assert 'WRAP_LEVEL_Z = {"W1": 250.0, "W2": 420.0}' in src
    assert 2 * CM.ROLL_HALF_CP <= 394.0                                     # roll no wider than the bag cap
