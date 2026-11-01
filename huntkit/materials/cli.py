"""CLI: python -m huntkit.materials.cli list|show <id>|compare <id> <id>...|validate"""
from __future__ import annotations

import argparse
import sys

from .loader import CATEGORIES, MaterialError, all_materials, load, query
from .validate import validate_all


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def _table(rows: list[list[str]]) -> str:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def cmd_list(args) -> int:
    mats = query(args.category) if args.category else all_materials()
    rows = [["id", "category", "confidence", "cost", "name"]]
    for m in mats:
        cost = f"${_fmt(m.cost_usd['value'])}/{m.cost_usd['per']}" if m.cost_usd else "-"
        rows.append([m.id, m.category, m.confidence, cost, m.name])
    print(_table(rows))
    print(f"\n{len(mats)} materials")
    return 0


def cmd_show(args) -> int:
    m = load(args.id)
    print(f"{m.name}  [{m.id}]")
    print(f"category: {m.category}   generic: {m.generic}   confidence: {m.confidence}")
    if m.trade_names:
        print("trade names: " + "; ".join(m.trade_names))
    if m.supplier_examples:
        print("suppliers:   " + "; ".join(m.supplier_examples))
    if m.cost_usd:
        print(f"cost:        ~${_fmt(m.cost_usd['value'])} per {m.cost_usd['per']}")
    print("properties:")
    w = max(len(k) for k in m.props)
    for k, v in m.props.items():
        print(f"  {k.ljust(w)}  {_fmt(v)}")
    print("sources:")
    for s in m.sources:
        print(f"  - {s}")
    if m.notes:
        print("notes:\n  " + m.notes.strip().replace("\n", "\n  "))
    return 0


def cmd_compare(args) -> int:
    mats = [load(i) for i in args.ids]
    keys: list[str] = []
    for m in mats:
        keys += [k for k in m.props if k not in keys]
    rows = [["property"] + [m.id for m in mats]]
    rows.append(["category"] + [m.category for m in mats])
    rows.append(["confidence"] + [m.confidence for m in mats])
    for k in keys:
        rows.append([k] + [_fmt(m.props[k]) if k in m.props else "-" for m in mats])
    # specific stiffness / strength where available
    for label, num in (("E/rho (MPa*m3/kg)", "youngs_modulus_mpa"), ("sy/rho (MPa*m3/kg)", "yield_strength_mpa")):
        if any(num in m.props and "density_kg_m3" in m.props for m in mats):
            rows.append([label] + [
                f"{m.props[num] / m.props['density_kg_m3']:.2f}"
                if num in m.props and "density_kg_m3" in m.props else "-" for m in mats
            ])
    rows.append(["cost"] + [f"${_fmt(m.cost_usd['value'])}/{m.cost_usd['per']}" if m.cost_usd else "-" for m in mats])
    print(_table(rows))
    return 0


def cmd_validate(args) -> int:
    problems = validate_all()
    n = len(all_materials()) if not problems else None
    if not problems:
        print(f"OK: {n} records valid")
        return 0
    for p, errs in problems.items():
        print(f"{p}:")
        for e in errs:
            print(f"  - {e}")
    print(f"\n{len(problems)} file(s) with problems")
    return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m huntkit.materials.cli", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="list materials")
    p.add_argument("-c", "--category", choices=CATEGORIES)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="show one material")
    p.add_argument("id")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("compare", help="side-by-side property table")
    p.add_argument("ids", nargs="+")
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("validate", help="validate every YAML record")
    p.set_defaults(fn=cmd_validate)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except MaterialError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
