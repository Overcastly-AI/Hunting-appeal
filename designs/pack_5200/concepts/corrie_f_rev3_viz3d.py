"""BL-029 renders of CORRIE F rev 3, now a thin wrapper (BL-030).

Rev 3 is the module default since BL-030 and ``huntkit/viz3d/corrie_f.py`` draws it natively: B-27 port guys (outside
only from the bridle sleeve to the port), the B-29 crown lid seated on the roll, the B-28 crown straps on their taut
path, no top pouch. The run-time swap that used to live here (rev 1 scene, pouch off, guys replaced) is retired; this
script only keeps the BL-029 command line and file numbers working.

    export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python            # Blender venv (huntkit/viz3d/README.md)
    export HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets        # MakeHuman / Poly Haven cache
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --render            # hero, side, lid, open
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --render lid --prefix 20261112_BL030
    python designs/pack_5200/concepts/corrie_f_rev3_viz3d.py --docs              # copy 1-4 to docs/screens
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from huntkit.viz3d.corrie_f import lid_mesh  # noqa: E402,F401  (re-exported: tests and BL-029 callers)

SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
PREFIX = "20261112_BL030"
NUMBER = {"hero": 1, "side": 2, "lid": 3, "open": 4}


def render(names=("hero", "side", "lid", "open"), quality="final", level=2, prefix=PREFIX):
    from huntkit.viz3d import corrie_f as CF
    return CF.render(list(names), SCREENS, prefix, quality, level, numbers={n: NUMBER[n] for n in names})


def docs(nums=(1, 2, 3, 4), prefix=PREFIX):
    DOCS.mkdir(parents=True, exist_ok=True)
    out = []
    for n in nums:
        src = SCREENS / f"{prefix}_{n}.png"
        if src.exists():
            shutil.copyfile(src, DOCS / src.name)
            out.append(DOCS / src.name)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--render", nargs="?", const="hero,side,lid,open")
    ap.add_argument("--quality", default="final")
    ap.add_argument("--level", type=int, default=2)
    ap.add_argument("--prefix", default=PREFIX)
    ap.add_argument("--docs", action="store_true")
    a = ap.parse_args(argv)
    if a.render:
        for r in render(a.render.split(","), a.quality, a.level, a.prefix):
            print(r["shot"], r["file"], r["seconds"], "s", r["mb"], "MB")
    if a.docs:
        print(docs(prefix=a.prefix))


if __name__ == "__main__":
    main()
