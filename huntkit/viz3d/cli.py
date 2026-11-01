"""CLI for huntkit.viz3d.

  python -m huntkit.viz3d.cli build [--spec designs/pack_5200/spec.yaml] [--out outputs/pack3d/]
                                    [--no-render] [--screens outputs/screens] [--date 20261101]

Writes <out>/pack5200.glb, <out>/pack5200_viewer.html (offline, self-contained), <out>/metrics.json
and PNG renders <screens>/<date>_pack3d_<view>.png (copies of the best three in docs/screens/).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .export import build_materials, export_glb, manifest, write_metrics
from .model import build_pack
from .params import DEFAULT_SPEC, REPO, load_params
from .viewer import build_html

BEST = ("hero", "haul", "fit", "side", "front")


def shots(m: dict) -> list[dict]:
    vol = f"main bag {m['bag_volume_l']:.1f} L ({m['bag_volume_cu_in']:,.0f} cu in, from the mesh)"
    t = m["torsos"]
    fea = m.get("fea") or {}
    v3 = m.get("bag_type") == "teardrop_rolltop"
    rolled = f"rolled down {m.get('bag_volume_rolled_l', 0):.0f} L" if v3 else ""
    hero_sub = (f"{rolled}; {vol} with the collar unrolled. SPINE: diagonal zip under a stretch band, camo on wear zones"
                if v3 else f"{vol} + {m['lid_design_l']:.1f} L lid · camo shards on corners, lash zone, lid, pockets")
    out = [
        dict(name="hero", view="hero", state={"mode": "pack"},
             caption="Pack 5200 v3.1 SPINE: 3/4 view of the outer face" if v3 else "Pack 5200: 3/4 view of the outer face",
             sub=hero_sub),
        dict(name="side", view="side", state={"mode": "pack", "mannequin": True},
             caption="Side profile, 19 in torso: deeper teardrop, 30 mm head setback" if v3 else "Side profile, 19 in torso",
             sub="Crown sets yoke + lifters together; hipbelt on the Ti pivot at z 120 mm"),
        dict(name="back", view="back", state={"mode": "pack"},
             caption="Back panel and suspension",
             sub="Lumbar plate, J-straps on the crown yoke, sternum strap, load lifters, hipbelt (M)"),
        dict(name="haul", view="haul", state={"mode": "pack", "haul": True},
             caption=f"Haul mode: bag hinges back {m['haul_pullback_mm']:.0f} mm",
             sub=("No shelf: internal 38 mm meat straps hook to frame stubs and cam the quarter to the frame; wraps close the bay"
                  if v3 else "Bone-in hindquarter on the 270 x 260 shelf, shelf straps to the mid-bar nodes, load wings, flag on extension posts")),
        dict(name="exploded", view="exploded", state={"mode": "pack", "explode": True},
             caption="Exploded view", sub="Frame, crown, shelf, bag, pockets, harness and hipbelt"),
        dict(name="frame", view="frame", state={"mode": "frame", "harness": False},
             caption="Carbon frame close-up",
             sub=f"Straight stays (v2), formed lumbar pan, Ti pivot mount, telescoping crown, swept top bar. Tubes: {m['tube_size_source']}"),
        dict(name="fea", view="fea", state={"mode": "frame", "fea": True, "harness": False},
             caption="FEA utilization overlay (worst load case)",
             sub=(f"max {fea.get('max_utilization', 0):.2f} in {str(fea.get('critical_case', '')).replace('_', ' ')}"
                  f" · {fea.get('source', '')}") if fea else "FEA unavailable"),
        dict(name="fit", view="fit", state={"mode": "pack", "fit": True, "mannequin": True},
             caption="Fit: one frame, three torsos",
             sub=" · ".join(f"{k:g} in: crown top {v['crown_top_z']:.0f} mm" for k, v in sorted(t.items()))),
    ]
    if v3:
        out.insert(1, dict(name="full", view="hero", state={"mode": "pack", "full": True},
                           caption="Collar unrolled: the counted 85.2 L",
                           sub=f"{vol}; computed to the fill line with the roll-top closed by 3 rolls"))
        out.insert(2, dict(name="front", view="front", state={"mode": "pack"},
                           caption="Outer face: taper + SPINE diagonal",
                           sub="One #10 zip from the right hip to the left shoulder, reachable from either side"))
        out.append(dict(name="lid", view="hero", state={"mode": "pack", "lid": True},
                        caption="Optional lid / hip pack on the closed roll",
                        sub="Short fixed rear tabs + front magnets: nothing to flop"))
    return out


def render(html: Path, shot_list: list[dict], screens: Path, date: str, width=800, height=600, scale=2) -> list[Path]:
    screens.mkdir(parents=True, exist_ok=True)
    cfg = {"html": str(html.resolve()), "width": width, "height": height, "scale": scale, "shots": []}
    files = []
    for s in shot_list:
        f = screens / f"{date}_pack3d_{s['name']}.png"
        files.append(f)
        cfg["shots"].append({**s, "file": str(f.resolve())})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(cfg, tf)
    subprocess.run(["node", str(Path(__file__).parent / "render.js"), tf.name], check=True,
                   env={**__import__("os").environ, "NODE_PATH": "/opt/node22/lib/node_modules"})
    for f in files:
        shrink_png(f)
    return files


def shrink_png(path: Path, max_bytes: int = 1_500_000):
    from PIL import Image
    if path.stat().st_size <= max_bytes:
        return
    im = Image.open(path).convert("RGB")
    im.save(path, optimize=True)
    if path.stat().st_size > max_bytes:
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, optimize=True)


def build(spec=DEFAULT_SPEC, out="outputs/pack3d", do_render=True, screens="outputs/screens", date=None,
          only=None) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    p = load_params(spec)
    pack = build_pack(p)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, out / "pack5200.glb", mats=mats)
    man = manifest(pack)
    metrics = dict(pack.metrics)
    metrics["torsos"] = {f"{k:.1f}": v for k, v in metrics["torsos"].items()}
    html = build_html(glb, man, metrics, info, out / "pack5200_viewer.html", title=p["name"])
    write_metrics(pack, out / "metrics.json", {"camo_source": info["camo_source"]})
    res = {"glb": glb, "html": html, "metrics": pack.metrics, "info": info, "screens": []}
    if do_render:
        date = date or dt.date.today().strftime("%Y%m%d")
        sl = [s for s in shots(pack.metrics) if not only or s["name"] in only]
        files = render(html, sl, Path(screens), date)
        docs = REPO / "docs" / "screens"
        docs.mkdir(parents=True, exist_ok=True)
        for f in files:
            if any(f.stem.endswith("_" + b) for b in BEST):
                shutil.copy2(f, docs / f.name)
        res["screens"] = files
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m huntkit.viz3d.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="model -> GLB + offline HTML viewer + PNG renders")
    b.add_argument("--spec", default=str(DEFAULT_SPEC))
    b.add_argument("--out", default="outputs/pack3d")
    b.add_argument("--screens", default="outputs/screens")
    b.add_argument("--date", default=None, help="YYYYMMDD prefix for screenshots (default today)")
    b.add_argument("--no-render", action="store_true")
    b.add_argument("--only", default=None, help="comma list of views to render (default all)")
    a = ap.parse_args(argv)
    r = build(a.spec, a.out, not a.no_render, a.screens, a.date, a.only.split(",") if a.only else None)
    m = r["metrics"]
    print(f"GLB   {r['glb']}  ({r['glb'].stat().st_size / 1e6:.1f} MB)")
    print(f"HTML  {r['html']}  ({r['html'].stat().st_size / 1e6:.1f} MB, offline)")
    print(f"bag volume {m['bag_volume_l']:.2f} L = {m['bag_volume_cu_in']:.0f} cu in "
          f"(target {m['target_volume_l']:.2f} L, {m['volume_error_pct']:+.2f} %)")
    print(f"camo: {r['info']['camo_source']}; tubes: {m['tube_size_source']}")
    for f in r["screens"]:
        print(f"PNG   {f}  ({f.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
