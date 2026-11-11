# huntkit.viz3d renderers

There are two render paths for the same GLB:

| Path | Code | Use | Time per 1600 x 1200 frame |
|---|---|---|---|
| three.js raster (headless Chromium) | `viewer.py`, `render.js`, `cli.py` | interactive offline viewer, quick review renders | seconds |
| Blender Cycles path trace (headless `bpy`) | `cycles_render.py` | product-photography renders for the owner | about 2 min (48 spp + OIDN, 4 CPU cores) |

## Cycles path (`cycles_render.py`)

The Cycles path imports the GLB and swaps each glTF material, by name, for a Cycles shader:
- ripstop with sheen, a 6 mm grid bump and shader-only fine wrinkles;
- the owner camo, re-rasterised from the SVG at 2048 px per 380 mm accent repeat;
- webbing weave;
- matte black POM and anodised hardware;
- clear-coated carbon;
- black spacer mesh over black XLPE foam;
- a matte grey mannequin.

The lighting is a three-softbox studio rig with a gradient world, a shadow-catcher floor and AgX (Punchy), with mild depth of field. The GLB geometry, including the cloth-sim drape, is not changed.

Part visibility and camera presets are Python ports of `viewer.py` (`visibleFor`, `VIEWS`). The part manifest is read from the `<stem>_viewer.html` next to the GLB, or from `--manifest`. As a result, `--views hero` frames the same shot as the three.js `hero` view.

### Install (once, outside the repo: the wheel is about 1 GB)

```
python3.11 -m venv $SCRATCH/bpyenv                       # bpy wheels exist for CPython 3.11 only
$SCRATCH/bpyenv/bin/pip install bpy pillow pyyaml         # bpy 5.0.1 tested 2026-11-08
```

The camo is re-rasterised by the repo's own Python (`python3`, or set `HUNTKIT_PY`) because that interpreter has cairosvg and scipy. The result is cached in `outputs/cycles_work/`.

### Run

```
$SCRATCH/bpyenv/bin/python -m huntkit.viz3d.cycles_render \
    --glb outputs/pack3d_corrie/corrie.glb \
    --views rear34,side,door,wing,hero --samples 48 \
    --out outputs/screens --prefix 20261108_cycles --start 2 \
    --before outputs/screens/20261108_corrie_1.png --before-out outputs/screens/20261108_cycles_1.png
```

Named shots are `rear34`, `side`, `door`, `wing`, `hero` and `backpanel`. Any raw viewer view name also works.

Other options:
- `--res 1600x1200`, `--torso 19`, `--camo my.png` and `--no-caption`.
- `--before` takes the three.js PNG of the `hero` view and writes a before/after sheet.

Raw RGBA frames and the timing file go to `outputs/cycles_work/` (scratch). Final PNGs are composited onto the viewer backdrop and kept at 1.5 MB or less.

### Measured (2026-11-08, CORRIE GLB, 133 parts, 4 vCPU, CPU only)

- Import and material build: about 2 s.
- 1600 x 1200 at 48 samples with adaptive sampling and OIDN: 100-150 s per frame (rear34 127, side 101, door 130, wing 146, hero 140 s; 11.3 min for all 5) (see `outputs/cycles_work/<prefix>_timing.json`).
- 800 x 600 at 16-24 samples (look development): about 20 s.

### Tests

`tests/test_viz3d_cycles.py` checks the visibility port, camera fit and manifest parsing without bpy. The tiny Cycles render test skips when `bpy` is not importable.

## Studio layer (`studio.py` + `assets/`), BL-018: the path to use for new renders

`studio.render(concept_scene, shots, out_dir)` is the one entry point. A concept hands over its drape mesh, piece
boundaries, strap paths and hardware placements; the modelling layer in `huntkit/viz3d/assets/` turns them into
geometry that renders like a sewn pack:

| Module | What it builds |
|---|---|
| `assets/hardware.py` | watertight buckles, ladder locks, tri-glides, cam buckles, G-hooks, D-ring, bag hook, zip sliders and pulls, cord lock, with real slots and rounded edges. `HW.SPECS` lists every dimension and its source (record or ASSUMPTION). `HW.library_glb()` writes the cached library to `outputs/viz3d_assets/hardware.glb` (about 1 MB, untracked, rebuilt on demand). |
| `assets/webbing.py` | webbing with thickness and rounded selvedges, weave UVs in mm, hanging tails with a folded bartacked stop, elastic keepers, and the wraps through each buckle (`threading(kind)`). |
| `assets/seams.py` | seam ridge and crease, stitch rows at 3.0 mm, binding, bartack, box-X. |
| `assets/zips.py` | coil chain (both coils), tapes with stitch rows, slider, cord pull with grip, stops; a parted half for an open door. |
| `assets/fabric.py` | the fabric pass: wrinkles from the drape's strain field, seam pucker, strap pillowing, flattening under anything that sits on the cloth, cloth thickness, linings. Displacement is clamped to 5 mm. |

### Minimal use

```python
import numpy as np
from huntkit.viz3d import studio

sc = studio.ConceptScene("my_bag")                      # all coordinates FCS mm (x right, y aft, z up)
# 1. cloth: the cloth-sim drape. mesh.metadata["uv"] = flat-pattern coordinates in mm / 500 (so the strain field
#    is real). Build the mesh with huntkit.viz3d.assets.mesh(V, F, uv).
sc.add_fabric("body", drape_mesh, "body")               # materials: studio.MATERIALS keys
# 2. seams: every boundary between two pattern pieces (piece = one name per triangle)
sc.add_seams_from_pieces(V, F, piece, vertex_normals, skip=[("door", "surround")])
# 3. webbing: a path ON the cloth (lift it 1-2 mm) and the cloth normals along it
sc.add_strap("comp_strap", path, normals, width=25.0, tail=80.0, keeper=True)
# 4. hardware: p = point on the strap centreline, n = cloth normal, t = strap direction
#    (+x of the piece: side-release female / sewn side; ladder lock anchor; G-hook mouth)
sc.add_hardware("comp_buckle", "side_release_25", p, n, t)
# 5. zip along the door seam; sliders as fractions of its length
sc.add_zip("door_zip", zip_path, zip_normals, size=10, sliders=(0.05,))
# 6. anything already meshed (frame, belt, display form): sc.add_part(name, mesh, material, group="frame")

shots = studio.shots("hero", "side", "front34",         # presets
                     buckle={"view": {"at": [240, 170, 740], "az": 70, "span": 130}, "caption": "buckle"})
studio.render(sc, shots, "outputs/screens", prefix="20261111_mybag", quality="quick")   # then quality="final"
```

Run it with the repo Python. Stage 2 needs Blender's Python: set `HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python` (install
as above) and make sure the repo is on `PYTHONPATH`. If `bpy` imports in the calling interpreter, everything runs
in-process.

- A shot is `{"view": {...}, "state": {...}, "caption": str, "sub": str}`. View keys: `az` (0 = looking at the bag's
  aft face, 90 = from the wearer's right, 180 = from the front), `el`, `fov`, `fstop`, `zoom`, and one framing:
  `"frame": "pack"` (everything but the display form), `"box": [x0, y0, z0, x1, y1, z1]` or `"at": [x, y, z]` with
  `"span"` mm (macro). `state` is the viewer state (`mannequin`, `lid`, `full`, ...); parts carry `group`, `variant`,
  `modes`, `torso` as in `export.manifest`.
- Quality: `quick` 800 x 600 at 16 samples (28-57 s a frame on 4 shared cores), `preview` 1200 x 900 at 40,
  `final` 1600 x 1200 at 72. Captions are written in a band below the picture, never over the subject.
- Legacy viz3d packs: build them inside `with studio.upgraded_legacy():` and pass the pack to `sc.add_pack(pack,
  drape={part name: {...}})`. The old block hardware and flat ribbons then come out as the new assets.
  `studio.corrie_b2_scene()` is the worked example; `python -m huntkit.viz3d.studio --concept corrie_b2 --shots
  hero,side --quality quick` renders it. Other registered concepts: `hardware_sheet`, `fabric_swatches`.
- `studio.sheet([(before, after), ...], out_png)` makes a before/after sheet.

### Wearer hook (BL-019)

`studio.render(..., wearer=, wearer_kwargs=, pack_on_torso=, torso=)` puts a figure in place of the display form:

- `wearer="huntkit.viz3d.wearer:build_wearer"` (a `"module:function"` string) is called inside Blender as
  `function(**wearer_kwargs)` after the pack is imported. It may return a list of Blender objects, a dict
  `{"objects": [...], "pack_on_torso": 4x4}`, or an object with `.figure` / `.props` / `.pack` / `.objects`
  (`wearer.Wearer`): the studio then renders the figure and props and hides the pack copy the wearer brought.
  In-process callers may pass the callable or the object list directly.
- `pack_on_torso` is a 4x4 rigid transform (nested lists, Blender world metres, Z up) applied to every pack object.
  Identity keeps the pack in its own frame (FCS x, -y, z in metres), which is where `wearer.py` stands its figure
  (wearer faces +Y). `torso` picks the pack's torso setting (15, 19 or 23 in the legacy packs).
- With a wearer the display form is hidden, the floor drops to the lowest point of pack and figure (the 6 ft hunter's
  boots), and `"frame": "pack"` shots frame pack and figure together. `studio.marker_wearer` is a stand-in post for
  framing tests.

### Tests

`tests/test_viz3d_assets.py`: hardware envelopes against the records (0.5 mm), watertight solids, through-slots as
wide as the webbing, stitch count at 3.0 mm, zip chain width, the 5 mm displacement bound, taut against slack, the
scene build, and a 160 x 120 render through the wearer hook (skips without `bpy`).
