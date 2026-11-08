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
