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

BEST = ("hero", "float", "float220", "float_links", "attach", "bagoff", "spreader", "side", "front", "fit")


def shots(m: dict) -> list[dict]:
    """Shot list with captions written from the metrics (no stale design words: there is no shelf, no LINK toggles,
    no tube frame; the spreader is the flat Sandwich v2 board)."""
    vol = f"main bag {m['bag_volume_l']:.1f} L ({m['bag_volume_cu_in']:,.0f} cu in, from the mesh)"
    t = m["torsos"]
    fea = m.get("fea") or {}
    v3 = m.get("bag_type") == "teardrop_rolltop"
    gen = m.get("frame_type") == "generative"
    att, fl, sp, bp = m.get("attach"), m.get("float"), m.get("spreader"), m.get("back_panel")
    rolled = f"rolled down {m.get('bag_volume_rolled_l', 0):.0f} L" if v3 else ""
    hero_sub = (f"{rolled}; {vol} with the collar unrolled. SPINE: diagonal zip under a stretch band, camo on wear zones"
                if v3 else f"{vol} + {m['lid_design_l']:.1f} L lid · camo shards on corners, lash zone, lid, pockets")
    out = [
        dict(name="hero", view="hero", state={"mode": "pack"},
             caption="Pack 5200 v3.1 SPINE: 3/4 view of the outer face" if v3 else "Pack 5200: 3/4 view of the outer face",
             sub=hero_sub),
        dict(name="side", view="side", state={"mode": "pack", "mannequin": True},
             caption="Side profile, 19 in torso: teardrop, 30 mm head setback" if v3 else "Side profile, 19 in torso",
             sub="Crown sets yoke + lifters together; hipbelt on the Ti pivot at z 120 mm; top guys run outside the gores"),
        dict(name="back", view="back", state={"mode": "pack"},
             caption="Back panel and suspension",
             sub=("BP-01 mesh over the stay rails, J-straps on the crown yoke, sternum strap, load lifters on the crown "
                  "corner wraps, hipbelt (M) on the Ti pivot")),
        dict(name="exploded", view="exploded", state={"mode": "pack", "explode": True},
             caption="Exploded view",
             sub=("Frame + crown, spreader, back panel (mesh, rails, backers), bag with tongues, doublers and ladders, "
                  "crown hood + guys, harness, hipbelt. No shelf: meat rides on the IM1-IM3 straps")),
        dict(name="frame", view="frame", state={"mode": "frame", "harness": False, "bp": False},
             caption="Printed frame close-up" if gen else "Carbon frame close-up",
             sub=("PAHT-CF branch frame with its printed fairleads, carbon crown with corner wraps, Sandwich v2 spreader, "
                  "under-straps hanging as the cradle" if gen
                  else f"Straight stays (v2), formed lumbar pan, Ti pivot mount, telescoping crown. Tubes: {m['tube_size_source']}")),
        dict(name="fit", view="fit", state={"mode": "pack", "fit": True, "mannequin": True},
             caption="Fit: one frame, three torsos",
             sub=" · ".join(f"{k:g} in: crown top {v['crown_top_z']:.0f} mm" for k, v in sorted(t.items()))),
    ]
    if fea:
        out.insert(5, dict(name="fea", view="fea", state={"mode": "frame", "fea": True, "harness": False},
                           caption="FEA utilization overlay (worst load case)",
                           sub=f"max {fea.get('max_utilization', 0):.2f} in {str(fea.get('critical_case', '')).replace('_', ' ')}"
                               f" · {fea.get('source', '')}"))
    if v3:
        out.insert(1, dict(name="full", view="hero", state={"mode": "pack", "full": True},
                           caption="Collar unrolled: the counted 85.2 L",
                           sub=f"{vol}; computed to the fill line with the roll-top closed by 3 rolls"))
        out.insert(2, dict(name="front", view="front", state={"mode": "pack"},
                           caption="Outer face: taper + SPINE diagonal",
                           sub="One #10 zip from the right hip to the left shoulder; bow riser loops + G-hook strap on "
                               "the right side, cam/limb in the band's cam cup"))
        out.append(dict(name="lid", view="hero", state={"mode": "pack", "lid": True},
                        caption="Optional lid / hip pack on the closed roll",
                        sub="Short fixed rear tabs + front magnets: nothing to flop"))
    if att and fl:
        gaps = " / ".join(f"{g:.0f}" for g in fl["gaps_mm"])

        def float_shot(name, gap):
            return dict(name=name, view="float", state={"mode": "pack", "haul": True, "gap": gap},
                        caption=f"Float mode: bag hung upright on the {gap:.0f} mm loop of the {fl['link_id']} links",
                        sub=(f"Bone-in quarter in the US1/US2 cradle, IM1-IM3 eye to eye over it; two {fl['link_id']} "
                             f"stand-off links on the IM3 eyes, the bag's T3 hooks in the {gap:.0f} mm loop (loops {gaps} mm); "
                             "W1-W3 round bag and meat; hood lies on the bag top"))
        out[1:1] = [
            float_shot("float", fl["view_gap_mm"]),
            float_shot("float220", max(fl["gaps_mm"])),
            dict(name="float_links", view="float_links", state={"mode": "pack", "haul": True, "gap": fl["view_gap_mm"],
                                                                 "xray": True, "harness": False, "bp": False},
                 caption=f"Float mode close-up (bag in X-ray): {fl['link_id']} links at IM3",
                 sub=(f"Rated hook on each IM3 eye beside the meat-strap hook, 38 mm link aft to the bag's T3 hook in the "
                      f"{fl['view_gap_mm']:.0f} mm loop; the bag moved straight aft, the hinge pins went with it")),
            dict(name="attach", view="attach", state={"mode": "pack", "xray": True, "harness": False, "bp": False},
                 caption="Attachment close-up, bag in X-ray: hood on the bar, guys, IM3 hooks",
                 sub=(f"Crown hood on the top bar, tongues in the B-20 ladder, top guys round the gores to B-22; "
                      f"{att['hook_rated_n']:.0f} N bag hook on the IM3 fairlead eye, T3 tongue on tab B-17")),
            dict(name="attach_low", view="attach_low", state={"mode": "pack", "xray": True, "harness": False, "bp": False},
                 caption="Attachment close-up, lower joint (bag in X-ray)",
                 sub=("Hinge eye on the z 60 pull-pin (B-18 doubler inside B-01), under-straps US1 / US2 under the floor, "
                      "IM1 eye, IM2 bag hook + T2 tongue; fairleads with 5 mm pins; spreader edge and tube")),
            dict(name="bagoff", view="bagoff", state={"mode": "frame", "haul": True},
                 caption="Bag off: meat on the frame",
                 sub=("Quarter in the two under-strap cradles (US1 / US2), IM1-IM3 cammed over it against the spreader; "
                      "the hinge pins went with the bag")),
            dict(name="hood", view="hood", state={"mode": "pack", "harness": False},
                 caption="Crown hood B-19 on the top bar (19 in)",
                 sub=(f"{att['hood_width_mm']:.0f} mm shell, J-lip relieved to x +/-{att['hood_lip_half_mm']:.0f} "
                      f"clear of the corner wraps; tongues woven at the rung for the setting; guys to B-22 at "
                      f"x +/-{att['guy_xz'][0]:.0f}, z {att['guy_xz'][1]:.0f}")),
        ]
        out.insert(5, dict(name="bow", view="bow", state={"mode": "pack"},
                           caption="Bow riser carry, right side",
                           sub="Two 25 mm loops through B-11 lash tabs hold the riser, one 25 mm G-hook strap closes over "
                               "it; cam / lower limb in the SPINE band's cam cup"))
        if sp:
            out.insert(5, dict(name="spreader", view="spreader", state={"mode": "frame", "harness": False},
                               caption="Spreader BP-06 rev C: flat Sandwich v2 board",
                               sub=(f"{sp['size_mm'][0]:.0f} x {sp['size_mm'][1]:.0f} x {sp['t_mm']:.2f} mm, twill / 7 mm "
                                    f"ROHACELL 110 / twill; notched at the cleats, {sp['edge_tubes']} carbon edge tubes, "
                                    f"{sp['clips']} PA12 clips, {sp['pucks']} pucks")))
        if bp:
            out.insert(6, dict(name="backpanel", view="backpanel", state={"mode": "pack", "harness": False, "xray": True},
                               caption=f"Back panel X-ray: {bp['rail_w']:.0f} mm XLPE rails on {bp['backer_w']:.0f} mm "
                                       "carbon backers (BP-08)",
                               sub=(f"Rails {bp['rail_w']:.0f} x {bp['rail_l']:.0f} x {bp['rail_t']:.0f} on the stay lines; "
                                    f"BP-01 mesh {bp['mesh_w']:.0f} x {bp['mesh_h']:.0f} (drawn see-through) spans a "
                                    f"{bp['gutter_mm']:.0f} mm air gutter")))
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
