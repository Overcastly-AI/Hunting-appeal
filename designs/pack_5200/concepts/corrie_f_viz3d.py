"""BL-012: CORRIE F (door D2) renders through huntkit.viz3d.studio with the BL-020 cloth pass and the BL-019 hunter.

    export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python            # Blender venv (huntkit/viz3d/README.md)
    export HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets        # MakeHuman / Poly Haven cache (analysis/hunter_figure.md)
    python designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py fine --torso 19      # once: the fine drape (1 min)
    python designs/pack_5200/concepts/corrie_f_viz3d.py --render            # every shot, 1600 x 1200 at 64 samples
    python designs/pack_5200/concepts/corrie_f_viz3d.py --render hero,door  # some shots
    python designs/pack_5200/concepts/corrie_f_viz3d.py --sheets            # the three sheets from the rendered frames
    python designs/pack_5200/concepts/corrie_f_viz3d.py --docs              # copy the best six to docs/screens

The model and the shot list live in ``huntkit/viz3d/corrie_f.py``; this script only numbers the files, makes the
sheets and copies the milestone frames. Shots are saved one by one, so an interrupted run keeps what it finished.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
PREFIX = "20261111_BL012"

# file number of each shot (outputs/screens/20261111_BL012_<n>.png); 16-18 are sheets, 19-20 the comparison frames
NUMBER = {"hero": 1, "side": 2, "day": 3, "full": 4, "walk": 5, "kneel": 6, "door": 7, "meat": 8, "frame": 9,
          "frame_bare": 10, "addons_on": 11, "addons_on_left": 12, "addons_off": 13, "belt": 14, "roll": 15,
          "compare_f": 19, "compare_b2": 20}
SHEETS = {"compare": 16, "loads": 17, "addons": 18}
BEST = (1, 5, 6, 7, 16, 17)


def png(n: int) -> Path:
    return SCREENS / f"{PREFIX}_{n}.png"


def render(names, quality="final", level=2):
    from huntkit.viz3d import corrie_f as CF
    names = [n for n in CF.ORDER if n in names]
    return CF.render(names, SCREENS, PREFIX, quality, level, numbers={n: NUMBER[n] for n in names})


def _row(files, out, title, sub, width=2400):
    from PIL import Image, ImageDraw, ImageFont
    from huntkit.viz3d import cycles_render as CR
    try:
        f = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
        fs = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        f = fs = ImageFont.load_default()
    cw = (width - 12 * (len(files) - 1)) // len(files)
    ims = []
    for p in files:
        im = Image.open(p).convert("RGB")
        ims.append(im.resize((cw, int(im.height * cw / im.width)), Image.LANCZOS))
    head = 120
    sheet = Image.new("RGB", (width, head + max(i.height for i in ims)), (244, 243, 239))
    d = ImageDraw.Draw(sheet)
    d.text((28, 12), title, fill=(30, 30, 30), font=f)
    d.text((28, 68), sub, fill=(95, 95, 88), font=fs)
    for k, im in enumerate(ims):
        sheet.paste(im, (k * (cw + 12), head))
    sheet.save(out, optimize=True)
    CR.shrink_png(Path(out))
    return out


def sheets() -> list:
    from huntkit.viz3d import studio
    out = []
    if png(NUMBER["compare_b2"]).exists() and png(NUMBER["compare_f"]).exists():
        out.append(studio.sheet([(png(NUMBER["compare_b2"]), png(NUMBER["compare_f"]))], png(SHEETS["compare"]),
                                titles=("CORRIE B.2", "CORRIE F (door D2)"),
                                subs=("wings, crown hood, horseshoe door", "S15 shell, no wings, no hood; same camera, "
                                                                           "full load")))
    if all(png(NUMBER[k]).exists() for k in ("day", "hero", "full")):
        out.append(_row([png(NUMBER[k]) for k in ("day", "hero", "full")], png(SHEETS["loads"]),
                        "CORRIE F: day 12 L, 6-day 45 L, full 85 L class",
                        "Same camera, 6 ft hunter at the 19 in setting. Rendered 3D figure, not a photograph"))
    if png(NUMBER["addons_on"]).exists() and png(NUMBER["addons_off"]).exists():
        out.append(studio.sheet([(png(NUMBER["addons_on"]), png(NUMBER["addons_off"]))], png(SHEETS["addons"]),
                                titles=("Add-ons on", "Add-ons off"),
                                subs=("tripod, scope pod, top pouch", "base pack, same camera")))
    return out


def docs() -> list:
    DOCS.mkdir(parents=True, exist_ok=True)
    out = []
    for n in BEST:
        if png(n).exists():
            out.append(shutil.copy2(png(n), DOCS / png(n).name))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", nargs="?", const="all", default=None)
    ap.add_argument("--quality", default="final")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--sheets", action="store_true")
    ap.add_argument("--docs", action="store_true")
    a = ap.parse_args(argv)
    if a.render:
        names = list(NUMBER) if a.render == "all" else a.render.split(",")
        for r in render(names, a.quality, a.level):
            print(r["shot"], r["file"], r["seconds"], "s", r["mb"], "MB")
    if a.sheets:
        for p in sheets():
            print(p)
    if a.docs:
        for p in docs():
            print(p)


if __name__ == "__main__":
    main()
