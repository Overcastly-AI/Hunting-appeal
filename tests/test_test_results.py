"""BL-038: the results-sheet reader (huntkit.manufacturing.test_results)."""
import csv

import pytest

from huntkit.manufacturing import test_results as TR


def _sheet(tmp_path, rows):
    p = tmp_path / "r.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TR.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in TR.COLUMNS})
    return p


def _row(rid, tid, check, limit, measured="", settles="", release="R1"):
    return dict(row_id=rid, test_id=tid, group="G2", release=release, sample="1", quantity="q", unit="u",
                check=check, limit=limit, measured=measured, settles=settles)


def test_judging_each_check(tmp_path):
    p = _sheet(tmp_path, [
        _row("a", "LL-H", "max", "5", "4.9"), _row("b", "LL-H", "max", "5", "5.1"),
        _row("c", "HB-7", "min", "50.0", "50"), _row("d", "GT-1", "band", "0.20..0.40", "0,41"),
        _row("e", "PT-1", "yes", "Y", "y"), _row("f", "PT-1", "yes", "Y", "N"), _row("g", "T9-R3c", "record", "", "438"),
    ])
    rows = {r.row_id: r for r in TR.load_results(p)}
    assert [rows[k].judge() for k in "abcdefg"] == [True, False, True, False, True, False, True]


def test_test_and_assumption_status(tmp_path):
    p = _sheet(tmp_path, [
        _row("1", "US-BS", "max", "10", "6", "US-BS"), _row("2", "US-BS", "max", "10", "8", "US-BS"),
        _row("3", "MT-3", "max", "3", "2", "CAM-SLIP"), _row("4", "MT-3", "max", "3", "", "CAM-SLIP"),
        _row("5", "LL-H", "max", "5", "7", "LL-SLIP"), _row("6", "HB-7", "min", "50", "55", "LL-SLIP", "CARRY"),
        _row("7", "SL-1", "max", "15.0", "", "SLIDER-CORD", "BL037"),
    ])
    rows = TR.load_results(p)
    v = TR.verdicts(rows)
    assert v["US-BS"].status == "PASS" and v["MT-3"].status == "PARTIAL"
    assert v["LL-H"].status == "FAIL" and v["LL-H"].failed_rows == ["5"]
    assert v["SL-1"].status == "OPEN"
    a = TR.assumption_status(rows, v)
    assert a["US-BS"]["status"] == "VERIFIED"
    assert a["CAM-SLIP"]["status"] == "OPEN"
    assert a["LL-SLIP"]["status"] == "FAILED" and a["LL-SLIP"]["tests"] == ["HB-7", "LL-H"]
    rs = TR.release_status(v)
    assert rs["R1"] == "FAIL" and rs["CARRY"] == "PASS" and rs["BL037"] == "OPEN"
    md = TR.report_md(rows)
    assert "| LL-SLIP | FAILED | HB-7, LL-H |" in md


def test_bad_entries_are_refused(tmp_path):
    with pytest.raises(ValueError, match="not a number"):
        TR.load_results(_sheet(tmp_path, [_row("x", "LL-H", "max", "5", "about 4")]))[0].judge()
    with pytest.raises(ValueError, match="not Y or N"):
        TR.load_results(_sheet(tmp_path, [_row("x", "PT-1", "yes", "Y", "maybe")]))[0].judge()
    with pytest.raises(ValueError, match="duplicate"):
        TR.load_results(_sheet(tmp_path, [_row("x", "A", "yes", "Y"), _row("x", "B", "yes", "Y")]))
    bad = tmp_path / "bad.csv"
    bad.write_text("row_id,test_id\n1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        TR.load_results(bad)


def test_cli_writes_report(tmp_path):
    p = _sheet(tmp_path, [_row("1", "PT-1", "yes", "Y", "Y", "CARA-PROOF")])
    md, js = tmp_path / "o.md", tmp_path / "o.json"
    assert TR.main([str(p), "--md", str(md), "--json", str(js)]) == 0
    assert "| PT-1 | PASS | 1/1 | - |" in md.read_text()
    assert '"CARA-PROOF"' in js.read_text()
