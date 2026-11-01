"""CLI: python -m huntkit.camo.cli {render,swatches,mocks,analyze,owner-base,all} ..."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import engine, export

DEFAULT_PATTERNS = ["cirquefall", "cirquefall_shard", "cirquefall_firn", "cirquefall_firn_shard"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m huntkit.camo.cli",
                                 description="Procedural camo + colorway generator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="print repeat (PNG+TIFF at --dpi to --out) + previews + metrics")
    r.add_argument("pattern", help="pattern name in designs/apparel/camo/ or a YAML path")
    r.add_argument("--dpi", type=float, default=300)
    r.add_argument("--out", type=Path, default=export.OUT_DIR)
    r.add_argument("--no-tiff", action="store_true")
    r.add_argument("--no-svg", action="store_true")
    s = sub.add_parser("swatches", help="palette + solids swatch card PNG")
    s.add_argument("--patterns", nargs="*", default=DEFAULT_PATTERNS)
    sub.add_parser("mocks", help="jacket/pack accent mocks, full-fill mock, mock distance series")
    a = sub.add_parser("analyze", help="print metrics JSON")
    a.add_argument("pattern")
    ob = sub.add_parser("owner-base", help="Owner Base (primary): ingest SVG or PROXY, metrics, "
                        "scale study, previews, phone screenshots, print TIFFs")
    ob.add_argument("--dpi", type=float, default=300, help="print TIFF dpi (0 = skip)")
    ob.add_argument("--no-screens", action="store_true")
    al = sub.add_parser("all", help="render every default pattern + swatches + mocks")
    al.add_argument("--dpi", type=float, default=300)
    args = ap.parse_args(argv)

    if args.cmd == "render":
        res = export.render_all(args.pattern, args.dpi, args.out, tiff=not args.no_tiff,
                                svg=not args.no_svg)
        _print(res)
    elif args.cmd == "swatches":
        print(export.swatch_card(args.patterns))
    elif args.cmd == "mocks":
        _mocks()
    elif args.cmd == "analyze":
        print(json.dumps(export.analyze(engine.load_pattern(args.pattern)), indent=1))
    elif args.cmd == "owner-base":
        from . import owner_export
        res = owner_export.run_all(args.dpi or None, not args.no_screens)
        res.pop("metrics")
        _print(res)
    elif args.cmd == "all":
        for p in DEFAULT_PATTERNS:
            _print(export.render_all(p, args.dpi))
        print(export.swatch_card(DEFAULT_PATTERNS))
        _mocks()
    return 0


def _mocks():
    from .color import BACKGROUNDS
    print(export.preview_accent_mocks())
    print(export.preview_fullfill_mock(["cirquefall", "cirquefall_firn"]))
    mock = export.accent_mock_rgb("talus", 1.0, BACKGROUNDS["sagebrush"])
    print(export.preview_distance(engine.load_pattern("cirquefall_shard"),
                                  extra=[("Talus jacket on sagebrush", mock, 1.0)]))


def _print(res):
    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    raise SystemExit(main())
