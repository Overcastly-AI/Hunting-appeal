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
