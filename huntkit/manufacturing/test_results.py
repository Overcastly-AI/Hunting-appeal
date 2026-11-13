"""Read back the owner's physical-test results sheet and say which ASSUMPTIONs it settles (BL-038).

The sheet is ``outputs/release/test_kit/results_template.csv`` (written by ``designs/pack_5200/physical_test_kit.py``). The
owner fills in two columns per row, ``measured`` and ``date`` (plus ``photo`` and ``notes`` if wanted), and sends the
file back. Every other column is pre-filled and must not be edited.

Columns: ``row_id, test_id, group, release, sample, quantity, unit, check, limit, measured, date, photo, notes,
settles``.

``check`` says how a row is judged:

* ``max``    pass when measured <= limit (numbers; a slip in mm, a pressure in kPa, a mass in g)
* ``min``    pass when measured >= limit (a peak load in kg, a friction ratio, a cycle count)
* ``band``   pass when lo <= measured <= hi, limit written ``lo..hi``
* ``yes``    pass when measured is Y / YES / PASS / 1 / TRUE (held the load, gate closed, owner OK)
* ``record`` any value passes; the number is kept for the engineers (a CG, a free length, a ratio)

A test is PASS when every row of it is filled and passes, FAIL when any filled row fails, PARTIAL when some rows are
filled and all of those pass, OPEN when none is filled. An ASSUMPTION (``settles``, ``;``-separated) is VERIFIED when
every test that settles it is PASS, FAILED when any of them FAILs, otherwise OPEN.

CLI: ``python -m huntkit.manufacturing.test_results results.csv [--md out.md] [--json out.json]``.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

COLUMNS = ["row_id", "test_id", "group", "release", "sample", "quantity", "unit", "check", "limit", "measured",
           "date", "photo", "notes", "settles"]
OWNER_COLUMNS = ("measured", "date", "photo", "notes")
CHECKS = ("max", "min", "band", "yes", "record")
YES = {"y", "yes", "pass", "1", "true", "ok"}
NO = {"n", "no", "fail", "0", "false"}


@dataclass
class Row:
    row_id: str
    test_id: str
    group: str
    release: str
    sample: str
    quantity: str
    unit: str
    check: str
    limit: str
    measured: str = ""
    date: str = ""
    photo: str = ""
    notes: str = ""
    settles: str = ""

    @property
    def filled(self) -> bool:
        return self.measured.strip() != ""

    def judge(self) -> bool | None:
        """True / False for a filled row, None for an empty one. Raises ValueError on an unreadable entry."""
        if not self.filled:
            return None
        m = self.measured.strip()
        if self.check == "record":
            return True
        if self.check == "yes":
            low = m.lower()
            if low in YES:
                return True
            if low in NO:
                return False
            raise ValueError(f"{self.row_id}: '{m}' is not Y or N")
        x = _num(m, self.row_id)
        if self.check == "max":
            return x <= _num(self.limit, self.row_id)
        if self.check == "min":
            return x >= _num(self.limit, self.row_id)
        if self.check == "band":
            lo, hi = (_num(v, self.row_id) for v in self.limit.split(".."))
            return lo <= x <= hi
        raise ValueError(f"{self.row_id}: unknown check '{self.check}'")

    def assumptions(self) -> list[str]:
        return [a.strip() for a in self.settles.split(";") if a.strip()]


def _num(s: str, rid: str) -> float:
    try:
        return float(str(s).strip().replace(",", "."))
    except ValueError as e:
        raise ValueError(f"{rid}: '{s}' is not a number") from e


@dataclass
class Verdict:
    test_id: str
    status: str                    # PASS / FAIL / PARTIAL / OPEN
    rows: int
    filled: int
    passed: int
    release: str = ""
    failed_rows: list = field(default_factory=list)
    records: dict = field(default_factory=dict)     # row_id -> measured value, for 'record' rows and numbers


def load_results(path) -> list[Row]:
    """Read the sheet. Checks the header and the ``check`` column; tolerates a UTF-8 BOM and spreadsheet blank rows."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (rd.fieldnames or [])]
        if missing:
            raise ValueError(f"results sheet is missing columns {missing}")
        out = []
        for d in rd:
            if not (d.get("row_id") or "").strip():
                continue
            r = Row(**{c: (d.get(c) or "").strip() for c in COLUMNS})
            if r.check not in CHECKS:
                raise ValueError(f"{r.row_id}: check '{r.check}' not one of {CHECKS}")
            out.append(r)
    ids = [r.row_id for r in out]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"duplicate row_id {dup}")
    return out


def verdicts(rows: list[Row]) -> dict[str, Verdict]:
    by: dict[str, list[Row]] = {}
    for r in rows:
        by.setdefault(r.test_id, []).append(r)
    out = {}
    for tid, rs in by.items():
        judged = [(r, r.judge()) for r in rs]
        filled = [(r, j) for r, j in judged if j is not None]
        fails = [r.row_id for r, j in filled if j is False]
        if fails:
            st = "FAIL"
        elif not filled:
            st = "OPEN"
        elif len(filled) == len(rs):
            st = "PASS"
        else:
            st = "PARTIAL"
        out[tid] = Verdict(tid, st, len(rs), len(filled), len(filled) - len(fails), rs[0].release, fails,
                           {r.row_id: r.measured for r, _ in filled})
    return out


def assumption_status(rows: list[Row], v: dict[str, Verdict] | None = None) -> dict[str, dict]:
    """ASSUMPTION id -> {status, tests}. VERIFIED only when every settling test is PASS."""
    v = v if v is not None else verdicts(rows)
    tests_of: dict[str, set] = {}
    for r in rows:
        for a in r.assumptions():
            tests_of.setdefault(a, set()).add(r.test_id)
    out = {}
    for a, ts in sorted(tests_of.items()):
        sts = [v[t].status for t in ts]
        st = "FAILED" if "FAIL" in sts else ("VERIFIED" if all(s == "PASS" for s in sts) else "OPEN")
        out[a] = {"status": st, "tests": sorted(ts)}
    return out


def release_status(v: dict[str, Verdict]) -> dict[str, str]:
    """Release label -> PASS (every test in it PASS), FAIL (any FAIL) or OPEN."""
    rel: dict[str, list] = {}
    for t in v.values():
        for lab in [x.strip() for x in t.release.split(";") if x.strip()]:
            rel.setdefault(lab, []).append(t.status)
    return {k: ("FAIL" if "FAIL" in s else "PASS" if all(x == "PASS" for x in s) else "OPEN") for k, s in rel.items()}


def report_md(rows: list[Row]) -> str:
    v = verdicts(rows)
    a = assumption_status(rows, v)
    rs = release_status(v)
    L = ["# Physical test results read back", "",
         f"{sum(1 for t in v.values() if t.status == 'PASS')} PASS, {sum(1 for t in v.values() if t.status == 'FAIL')} "
         f"FAIL, {sum(1 for t in v.values() if t.status == 'PARTIAL')} PARTIAL, "
         f"{sum(1 for t in v.values() if t.status == 'OPEN')} OPEN of {len(v)} tests.", "", "## Releases", "",
         "| release | status |", "|---|---|"]
    L += [f"| {k} | {s} |" for k, s in sorted(rs.items())]
    L += ["", "## Tests", "", "| test | status | rows filled | failed rows |", "|---|---|---:|---|"]
    L += [f"| {t.test_id} | {t.status} | {t.filled}/{t.rows} | {', '.join(t.failed_rows) or '-'} |" for t in v.values()]
    L += ["", "## ASSUMPTION rows", "", "| assumption | status | settled by |", "|---|---|---|"]
    L += [f"| {k} | {d['status']} | {', '.join(d['tests'])} |" for k, d in a.items()]
    return "\n".join(L) + "\n"


def summary(path) -> dict:
    rows = load_results(path)
    v = verdicts(rows)
    return {"tests": {k: vars(t) for k, t in v.items()}, "assumptions": assumption_status(rows, v),
            "releases": release_status(v)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read the physical-test results sheet back (BL-038).")
    ap.add_argument("results", help="filled results CSV")
    ap.add_argument("--md", help="write a markdown report here")
    ap.add_argument("--json", help="write a JSON summary here")
    a = ap.parse_args(argv)
    rows = load_results(a.results)
    md = report_md(rows)
    if a.md:
        Path(a.md).write_text(md, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(summary(a.results), indent=1), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
