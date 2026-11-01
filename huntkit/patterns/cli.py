"""CLI for huntkit.patterns.

    python -m huntkit.patterns.cli demo [--out outputs/patterns_demo] [--paper letter|a4]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from . import (Seam, check_seams, cut_list, cylinder, export_dxf, export_pdf_tiled, export_svg,
               grade, nest, rect_panel)
from .geometry import cubic_inches, litres

DEMO_MATERIAL = "robic_100d_ripstop"  # data/materials/textiles/robic_100d_ripstop.yaml
SIZES = ["S", "M", "L"]


def build_stuff_sack(diameter: float = 180.0, height: float = 300.0, size: str = "M",
                     material_id: str = DEMO_MATERIAL):
    """3-piece drawcord stuff sack: body (tube, one back seam), round base, drawcord channel.

    Seam allowances: 10 mm (301 lockstitch, seams overlocked 504 after). Channel is a strip
    folded in half lengthwise (fold line marked); both raw long edges sew to the body top."""
    cyl = cylinder(diameter, height, seam_allowance_mm=10.0, material_id=material_id, size=size)
    body, base = cyl.pieces["body"], cyl.pieces["base"]
    body.piece_id, base.piece_id = "SS-01", "SS-02"
    body.labels["note"] = "back seam: side_a to side_b"
    circ = body.edge_length("top")
    ch_h = 2 * 25.0  # 25 mm finished channel for 3 mm cord
    channel = rect_panel("channel", circ, ch_h, 0.0, seam_allowance_mm=10.0,
                         material_id=material_id, size=size, piece_id="SS-03", grain=0.0)
    channel.add_internal_line([(0, ch_h / 2), (circ, ch_h / 2)], "fold", "FOLD")
    channel.labels["note"] = "fold lengthwise; leave 15 mm cord exit at ends"
    # drill marks for cord-lock/loop placement on body, 40 mm below top, at back seam
    body.add_drill_hole(20.0, height - 40.0, label="loop placement")
    seams = cyl.seams + [
        Seam(channel.edge("bottom"), body.edge("top").reversed(), stitch="301",
             name="channel to body top"),
    ]
    seams[-1].add_match_notches((0.25, 0.5, 0.75))
    return [body, base, channel], seams


def grade_stuff_sack(diameter=180.0, height=300.0, d_step=30.0, h_step=60.0):
    """Grade the sack S/M/L. Base: proportional scale. Body/channel: point rules whose
    x-delta equals the graded base perimeter change, so the base seam still matches."""
    pieces, _ = build_stuff_sack(diameter, height)
    body, base, channel = pieces
    s = d_step / diameter
    base_rules = {"sizes": SIZES, "base": "M", "scale_step": (s, s)}
    dper = base.edge_length("perimeter") * s
    body_rules = {"sizes": SIZES, "base": "M",
                  "points": {"br": (dper, 0.0), "tr": (dper, h_step), "tl": (0.0, h_step)}}
    ch_rules = {"sizes": SIZES, "base": "M", "points": {"br": (dper, 0.0), "tr": (dper, 0.0)}}
    graded = {"base": grade(base, base_rules), "body": grade(body, body_rules),
              "channel": grade(channel, ch_rules)}
    out = {}
    for sz in SIZES:
        b, bs, ch = graded["body"][sz], graded["base"][sz], graded["channel"][sz]
        seams = [Seam(b.edge("side_b"), b.edge("side_a").reversed(), name=f"{sz} back seam"),
                 Seam(b.edge("bottom"), bs.edge("perimeter"), name=f"{sz} body to base"),
                 Seam(ch.edge("bottom"), b.edge("top").reversed(), name=f"{sz} channel to body")]
        out[sz] = ([b, bs, ch], seams)
    return out


def demo(out_dir: str | Path = "outputs/patterns_demo", paper: str = "letter") -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pieces, seams = build_stuff_sack()
    rep = check_seams(seams)
    files = {}
    files["dxf"] = export_dxf(pieces, out / "stuff_sack_M.dxf")
    info = export_pdf_tiled(pieces, out / f"stuff_sack_M_tiled_{paper}.pdf", paper=paper,
                            title="Stuff sack M")
    files["pdf_tiled"] = out / f"stuff_sack_M_tiled_{paper}.pdf"
    export_pdf_tiled(pieces, out / "stuff_sack_M_plotter36.pdf", paper="plotter36",
                     title="Stuff sack M")
    files["pdf_plotter"] = out / "stuff_sack_M_plotter36.pdf"
    files["svg"] = export_svg(pieces, out / "stuff_sack_M_laser.svg")

    graded = grade_stuff_sack()
    all_pieces, all_seams = [], []
    for sz, (ps, ss) in graded.items():
        all_pieces += ps
        all_seams += ss
    grep = check_seams(all_seams)
    files["dxf_graded"] = export_dxf(all_pieces, out / "stuff_sack_SML.dxf")

    # 1 sack of each size on 1420 mm (56 in) roll, grain constrained
    marker = nest(all_pieces, fabric_width_mm=1420.0, grain_constraint=True, selvedge_mm=10.0,
                  spacing_mm=3.0)
    files["marker_pdf"] = marker.export_pdf(out / "marker_SML.pdf")
    files["marker_dxf"] = marker.export_dxf(out / "marker_SML.dxf")
    files["marker_csv"] = marker.export_csv(out / "marker_SML.csv")
    cl = cut_list(all_pieces)
    files["cutlist_csv"] = cl.write(out / "cut_list.csv")
    files["cutlist_md"] = cl.write(out / "cut_list.md")

    base = pieces[1]
    vol = base.seam_area_mm2 * 300.0
    md = [f"# Stuff sack pattern demo", "",
          f"Material: `{DEMO_MATERIAL}`. Base size M: Ø180 x 300 mm "
          f"(Ø{180 / 25.4:.2f} x {300 / 25.4:.2f} in), closed volume {litres(vol):.2f} L "
          f"({cubic_inches(vol):.0f} cu in). Seam allowance 10 mm (3/8 in), 301 lockstitch.", "",
          "## Seam check, size M", "", rep.markdown(), "",
          "## Seam check, graded S/M/L", "", grep.markdown(), "",
          "## Marker", "", marker.summary(), "",
          "## Cut list", "", cl.markdown(), "",
          "## Files", ""] + [f"- `{Path(v).name}`" for v in files.values()] + [
          f"- tiled PDF: {info['pages']} pages ({info['rows']} x {info['cols']} tiles + map)"]
    (out / "README.md").write_text("\n".join(md) + "\n")
    (out / "marker_report.json").write_text(json.dumps(marker.report(), indent=2))
    print(rep)
    print(grep)
    print(marker.summary())
    print(f"Wrote {len(files) + 2} files to {out}/")
    return {"seams": rep, "graded_seams": grep, "marker": marker, "files": files, "pdf": info}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m huntkit.patterns.cli",
                                 description="huntkit pattern engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="3-piece stuff sack: seams, DXF, tiled PDF, marker, cut list")
    d.add_argument("--out", default="outputs/patterns_demo")
    d.add_argument("--paper", default="letter", choices=["letter", "a4"])
    a = ap.parse_args(argv)
    if a.cmd == "demo":
        res = demo(a.out, a.paper)
        return 0 if res["seams"].ok and res["graded_seams"].ok else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
