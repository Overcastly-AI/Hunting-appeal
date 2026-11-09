"""CORRIE rev B.1 renders (2026-11-09): the adopted pockets IMP-1..6, IMP-8 and hipbelt B on the mannequin, Blender
Cycles (huntkit/viz3d/cycles_render.py). Two stages because bpy only runs in the CPython 3.11 venv
(huntkit/viz3d/README.md):

    python designs/pack_5200/concepts/corrie_b1_viz3d.py --model          # GLB + viewer manifest + shots JSON
    $SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render --glb outputs/pack3d_corrie_b1/corrie_b1.glb \\
        --shots outputs/pack3d_corrie_b1/shots.json --views b1_hero,b1_side,b1_door,b1_wings,b1_belt,b1_strap \\
        --samples 64 --prefix 20261109_corrie --out outputs/screens
    python designs/pack_5200/concepts/corrie_b1_viz3d.py --docs           # copy the best 4 to docs/screens

Builder: huntkit/viz3d/corrie_b1.py. Dimensions: designs/pack_5200/concepts/corrie.py (rev B.1 section).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "outputs" / "pack3d_corrie_b1"
SCREENS = ROOT / "outputs" / "screens"
DOCS = ROOT / "docs" / "screens"
DATE = "20261109"

# Cameras: az 0 = looking at the bag's aft face, +90 = from the wearer's right, 180 = from the front; boxes FCS mm.
SHOTS = {
    "b1_seat": {"view": {"az": 168, "el": 62, "zoom": 1.0, "box": [-150, -130, 90, 150, 30, 220]},
                "state": {"mode": "frame", "lid": True, "bp": False},   # render with --torso 99 (straps hidden)
                "caption": "CORRIE B.1: lumbar pad seat (cutaway, bag off)",
                "sub": "Pad backer on 2 EVA rails either side of the channel; the 6061 bow-tie rolls in the channel on the Ti pin"},
    "b1_beltL": {"view": {"az": 205, "el": 20, "zoom": 1.0, "box": [-290, -330, -20, 270, 60, 280]},
                 "state": {"mannequin": True, "lid": True}, "caption": "x", "sub": "x"},
    "b1_hero": {"view": {"az": -38, "el": 12, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.1: 3/4 rear on the wearer",
                "sub": "Belt B (size L, cone-cut), 85 mm spotter in the left-wing sleeve, tripod under the right wing"},
    "b1_side": {"view": {"az": 90, "el": 4, "zoom": 1.0}, "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.1: side, wearer's right",
                "sub": "Hose from the B-03R port over the strap to the bite valve; bottle holster behind the crest"},
    "b1_door": {"view": {"az": -20, "el": 12, "zoom": 1.0, "box": [-240, 0, 20, 240, 360, 1080]},
                "state": {"full": True, "lid": True},
                "caption": "CORRIE B.1: door open, kill-kit pocket",
                "sub": "IMP-4: 200 x 280 mm zipped bellows pocket on the door's inside face, blaze pull; IM1-IM3 behind"},
    "b1_wings": {"view": {"az": -4, "el": 16, "zoom": 1.0, "box": [-330, 40, 80, 330, 380, 760]},
                 "state": {"lid": True},
                 "caption": "CORRIE B.1: scope sleeve left, tripod right",
                 "sub": "IMP-1 padded sleeve (spotter drawn up 70 mm to show it) under the left wing; tripod under the right"},
    "b1_belt": {"view": {"az": 162, "el": 20, "zoom": 1.0, "box": [-270, -330, -20, 290, 60, 280]},
                "state": {"mannequin": True, "lid": True},
                "caption": "CORRIE B.1: hipbelt B, front 3/4",
                "sub": "Cone-cut padded wings, 2:1 pulls to D-rings, 1 L bottle holster (right), pocket cut to the wing (left)"},
    "b1_strap": {"view": {"az": 200, "el": 12, "zoom": 1.0, "box": [-190, -320, 330, 40, -60, 640]},
                 "state": {"mannequin": True, "lid": True},
                 "caption": "CORRIE B.1: shoulder-strap phone pocket",
                 "sub": "IMP-6 stretch-mesh pocket on the left strap for a 160 mm phone, shock-cord top, 2 G-hook wraps"},
}


def model():
    from huntkit.viz3d.corrie_b1 import corrie_b1_pack
    from huntkit.viz3d.export import build_materials, export_glb, manifest
    from huntkit.viz3d.params import load_params
    from huntkit.viz3d.viewer import build_html
    p = load_params(str(ROOT / "designs" / "pack_5200" / "spec.yaml"))
    pack = corrie_b1_pack(p)
    OUT.mkdir(parents=True, exist_ok=True)
    mats, info = build_materials(p)
    glb, _ = export_glb(pack, OUT / "corrie_b1.glb", mats=mats)
    m = dict(pack.metrics)
    m["torsos"] = {f"{k:.1f}": v for k, v in m["torsos"].items()}
    html = build_html(glb, manifest(pack), m, info, OUT / "corrie_b1_viewer.html", title="Pack 5200 CORRIE B.1 (concept)")
    (OUT / "shots.json").write_text(json.dumps(SHOTS, indent=1))
    print("GLB", glb, "HTML", html, "belt", pack.metrics.get("belt_b"))


def docs(best=(1, 3, 4, 5)):
    DOCS.mkdir(parents=True, exist_ok=True)
    for n in best:
        f = SCREENS / f"{DATE}_corrie_{n}.png"
        if f.exists():
            shutil.copy2(f, DOCS / f.name)
            print("copied", DOCS / f.name)


if __name__ == "__main__":
    if "--model" in sys.argv:
        model()
    if "--docs" in sys.argv:
        docs()
