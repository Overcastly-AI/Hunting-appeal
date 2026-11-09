"""CORRIE rev B.2 renders (2026-11-09): the owner-approved weight cuts (corrie.py spec B.2) plus the render fixes in
huntkit/viz3d/corrie_b2.py (clean wings and camo bar, display form, padded belt B). Blender Cycles, two stages because
bpy only runs in the CPython 3.11 venv (huntkit/viz3d/README.md):

    python designs/pack_5200/concepts/corrie_b2_viz3d.py --model          # GLB + viewer manifest + shots JSON
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_corrie_b2/corrie_b2.glb \\
        --shots outputs/pack3d_corrie_b2/shots.json --views b2_hero,b2_side,b2_belt,b2_wings \\
        --samples 64 --prefix 20261109_corrie_b2 --out outputs/screens
    python designs/pack_5200/concepts/corrie_b2_viz3d.py --docs           # copy the best 3 to docs/screens
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "outputs" / "pack3d_corrie_b2"
SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
DATE = "20261109"

# Cameras: az 0 = looking at the bag's aft face, +90 = from the wearer's right, 180 = from the front; boxes FCS mm.
SHOTS = {
    "b2_hero": {"view": {"az": -38, "el": 12, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.2: 3/4 rear on the display form",
                "sub": "Weight pass A + B applied: solid roll-top hem, 2.7 L pouch with camo pull tab; padded belt B (L)"},
    "b2_side": {"view": {"az": 90, "el": 4, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.2: side, wearer's right",
                "sub": "Tripod under the right wing, hose port and hose to the bite valve, bottle holster behind the crest"},
    "b2_belt": {"view": {"az": 158, "el": 18, "zoom": 1.0, "box": [-280, -340, -40, 300, 80, 300]},
                "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.2: hipbelt B, front 3/4",
                "sub": "Padded cone-cut wings, bound edges, 2:1 pulls to D-rings, bottle holster (right), pocket (left)"},
    "b2_wings": {"view": {"az": -4, "el": 16, "zoom": 1.0, "box": [-330, 40, 80, 330, 380, 760]},
                 "state": {"lid": True},
                 "caption": "CORRIE B.2: scope sleeve left, tripod right",
                 "sub": "IMP-1 sleeve (100D panel, spotter drawn up 70 mm) under the left wing; tripod under the right"},
}
BEST = (1, 3, 4)


def model():
    from huntkit.viz3d.corrie_b2 import corrie_b2_pack
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = corrie_b2_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "corrie_b2.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()}
    html = build_html(glb, manifest(pack), m, info, OUT / "corrie_b2_viewer.html", title="Pack 5200 CORRIE B.2 (concept)")
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    print("GLB", glb, "HTML", html, "belt", pack.metrics.get("belt_b"))


def docs(best=BEST):
    DOCS.mkdir(parents=True, exist_ok=True)
    for n in best:
        f = SCREENS / f"{DATE}_corrie_b2_{n}.png"
        if f.exists():
            shutil.copy2(f, DOCS / f.name)
            print("copied", DOCS / f.name)


if __name__ == "__main__":
    if "--model" in sys.argv:
        model()
    if "--docs" in sys.argv:
        docs()
