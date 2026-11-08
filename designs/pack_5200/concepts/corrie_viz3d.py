"""CORRIE renders in the viz3d pipeline (same materials, owner camo texture, lighting, frame, harness, mannequin and
headless three.js renderer as the SPINE renders outputs/screens/2026110x_pack3d_*.png).

    python designs/pack_5200/concepts/corrie_viz3d.py        # GLB + offline viewer + PNGs (~6 min)

Writes outputs/pack3d_corrie/{corrie.glb, corrie_viewer.html} and outputs/screens/20261108_corrie_<n>.png:
1 3/4 rear  2 side  3 door open  4 wing on a tripod  5 top pouch  6 float meat mode  7 SPINE vs CORRIE (same camera)
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from huntkit.viz3d.cli import shrink_png  # noqa: E402
from huntkit.viz3d.corrie import corrie_pack  # noqa: E402
from huntkit.viz3d.export import build_materials, export_glb, manifest  # noqa: E402
from huntkit.viz3d.params import load_params  # noqa: E402
from huntkit.viz3d.viewer import build_html  # noqa: E402

OUT = ROOT / "outputs" / "pack3d_corrie"
SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
DATE = "20261108"

SHOTS = [
    dict(n=1, view="hero", state={"mode": "pack"},
         caption="CORRIE: 3/4 rear, 19 in torso",
         sub="Cloth-sim drape of the sewn flat pieces (packed case); horseshoe door zip with garages, side wings with "
             "G-hook straps, roll-top clipped to the sides, 4 L pouch seated on the roll"),
    dict(n=2, view="side", state={"mode": "pack", "mannequin": True},
         caption="CORRIE: side profile on the wearer",
         sub="Wing taut over the side gusset, 2 G-hook straps to the aft corner seam; guys from the crown hood to "
             "B-22 at z 695; pouch on the closed roll"),
    dict(n=3, view="door", state={"mode": "pack", "full": True},
         caption="CORRIE: horseshoe door open",
         sub="Door unzipped (1.26 m #10 coil, 2 sliders) and folded up over the hinge band; IM1-IM3 (bone, 38 mm) "
             "and the floor in reach; wings stay cinched"),
    dict(n=4, view="wing", state={"mode": "pack", "lid": True},
         caption="CORRIE: tripod under the right wing",
         sub="Wing tensioned over the tripod legs by two G-hook straps to webbing loops in the aft corner seam, "
             "outboard of the door zip"),
    dict(n=5, view="pouch", state={"mode": "pack"},
         caption="CORRIE: top pouch seated on the roll",
         sub="4.0 L / 244 cu in pouch, camo top, #8 zip on the aft edge with a glove pull; 2 rear straps to the "
             "hem loops, 2 front straps to the roll clips"),
    dict(n=6, view="float", state={"mode": "pack", "haul": True, "gap": 170.0},
         caption="CORRIE: float meat mode (170 mm / 6.7 in loop)",
         sub="Quarter in the US1/US2 cradle under IM1-IM3; bag hung upright on the B-24 links; W1-W3 round both"),
]
# shot 7: ONE fixed camera for both bags (hero angle az -38 / el 14, fov 30), so sizes compare 1:1
_AZ, _EL, _D = math.radians(-38), math.radians(14), 3.05
_T = [0.0, 0.56, 0.16]                      # glTF metres: x, z (up), y (aft)
CAM7 = {"pos": [_T[0] + _D * math.sin(_AZ) * math.cos(_EL), _T[1] + _D * math.sin(_EL),
                _T[2] + _D * math.cos(_AZ) * math.cos(_EL)], "tgt": _T, "fov": 30}
ONLY = {int(x) for x in __import__("os").environ.get("CORRIE_SHOTS", "").split(",") if x.strip()}


def render(html: Path, shots: list, width=800, height=600, scale=2):
    cfg = {"html": str(html.resolve()), "width": width, "height": height, "scale": scale, "shots": shots}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(cfg, tf)
    subprocess.run(["node", str(ROOT / "huntkit" / "viz3d" / "render.js"), tf.name], check=True,
                   env={**__import__("os").environ, "NODE_PATH": "/opt/node22/lib/node_modules"})


def side_by_side(spine_png: Path, corrie_png: Path, out: Path):
    from PIL import Image, ImageDraw, ImageFont
    a, b = Image.open(spine_png).convert("RGB"), Image.open(corrie_png).convert("RGB")
    h = max(a.height, b.height)
    im = Image.new("RGB", (a.width + b.width, h + 120), (244, 243, 239))
    im.paste(a, (0, 120))
    im.paste(b, (a.width, 120))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except OSError:
        f = ImageFont.load_default()
    d.text((30, 14), "SPINE v3.1 (released)", fill=(30, 30, 30), font=f)
    d.text((a.width + 30, 14), "CORRIE (same fixed camera)", fill=(30, 30, 30), font=f)
    try:
        fs = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        fs = ImageFont.load_default()
    d.text((30, 66), "collar rolled down, 61 L (released render)", fill=(90, 90, 82), font=fs)
    d.text((a.width + 30, 66), "cloth-sim packed case, 92 L closed (roll at the sim closure line) + 4 L pouch",
           fill=(90, 90, 82), font=fs)
    im.save(out, optimize=True)
    shrink_png(out)


def main():
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = corrie_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "corrie.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()}
    html = build_html(glb, manifest(pack), m, info, OUT / "corrie_viewer.html", title="Pack 5200 CORRIE (concept)")
    shots = []
    for s in SHOTS:
        if ONLY and s["n"] not in ONLY:
            continue
        shots.append({**s, "file": str((SCREENS / f"{DATE}_corrie_{s['n']}.png").resolve())})
    do7 = not ONLY or 7 in ONLY
    if do7:
        shots.append(dict(n=7, cam=CAM7, state={"mode": "pack"}, caption="CORRIE", sub="",
                          file=str((OUT / "corrie_hero_compare.png").resolve())))
    render(html, shots)
    for s in shots[:-1] if do7 else shots:
        shrink_png(Path(s["file"]))
    # SPINE at the same camera: the released viewer, same view / state
    spine_html = ROOT / "outputs" / "pack3d" / "pack5200_viewer.html"
    sp = OUT / "spine_hero_compare.png"
    if spine_html.exists() and do7:
        render(spine_html, [dict(cam=CAM7, state={"mode": "pack"}, caption="SPINE v3.1", sub="", file=str(sp.resolve()))])
        side_by_side(sp, OUT / "corrie_hero_compare.png", SCREENS / f"{DATE}_corrie_7.png")
    for n in (1, 3, 4, 7):
        f = SCREENS / f"{DATE}_corrie_{n}.png"
        if f.exists():
            shutil.copy2(f, DOCS / f.name)
    print("GLB", glb, "HTML", html)
    for n in range(1, 8):
        f = SCREENS / f"{DATE}_corrie_{n}.png"
        if f.exists():
            print("PNG", f, f"{f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
