# BL-018 Better Blender models: asset library and fabric realism

**Wave:** 1 (independent) · **Agent:** pack-designer (Fable) · **Size:** XL · **Depends on:** none

## Why
The owner asked for "better blender models". Today's Cycles renders (`docs/screens/20261109_corrie_b2_*.png`, `docs/screens/20261110_bag*_1.png`) have real lighting and fabric shading, but the models under them are simple:
- **Webbing** is flat ribbon with no thickness or weave geometry.
- **Hardware** (buckles, G-hooks, ladder locks, cams, zip sliders) is boxes and blobs.
- **Seams** are drawn lines with no stitching, puckering or seam allowance ridge.
- **Fabric** is a smoothed sim surface with shader-only wrinkles, so silhouettes look inflated.
- **Add-on pods and wings** read as slabs.
- **The display form and belt** are plain.

## Goal
A reusable modelling layer that makes any bag concept in this repo render like product photography of a real sewn pack, proven on CORRIE B.2.

## Read first
`docs/backlog/RULES.md`; `huntkit/viz3d/README.md`, `cycles_render.py`, `corrie.py`, `corrie_b2.py`, `export.py`; the hardware and webbing records in `data/materials/hardware/` and `webbing/` (real dimensions); the owner camo source used by `cycles_render.py`.

## Tasks
1. **Hardware asset library.** Build parametric, dimensionally correct meshes (bevelled, with real openings and bars) for: 25 and 38 mm side-release buckles, ladder locks, tri-glides, cam buckles, G-hooks, D-rings, the rated bag hook, zip sliders with pulls (#5, #8, #10), cord locks, the 50 mm belt buckle. Dimensions from the material records or cited maker drawings; mark anything estimated. Put them in `huntkit/viz3d/assets/hardware.py` with a cached `.blend` or GLB library built on demand (not committed if over 5 MB).
2. **Webbing as geometry.** Webbing with thickness, rounded edges, a weave normal or displacement map at true scale, that follows the bag surface, dents the fabric where tensioned, threads through hardware correctly, and has hanging tails with keepers.
3. **Seams and stitching.** From the pattern piece boundaries the cloth sim already knows: a raised seam ridge, visible stitch rows at the specified stitch length, binding where the design has it, and slight puckering along seams (geometry or displacement, not only a drawn line). Bartacks and box-X stitches at load points.
4. **Zips.** Coil geometry or a convincing displaced strip with tape, slider, pull and garage.
5. **Fabric realism.** Use Blender's cloth solver (or a displacement pass driven by the sim's strain and wrinkle fields) to add fold-scale wrinkles and compression creases where straps cinch, without moving the overall shape more than 5 mm from the huntkit cloth-sim drape. Show the difference between a taut and a slack panel. Add fabric thickness at edges and hems.
6. **Materials.** Per-fabric shaders from the records: 330D Cordura, ripstop grid, ULTRA laminate, spacer mesh with real holes or alpha, Hypalon, foam edges, printed PAHT-CF (layer lines), carbon twill.
7. **Scene.** A better display form (clean torso form on a stand), three-point studio light plus an HDRI-style world, a ground with contact shadow, depth of field, and camera presets: hero, side, front 3/4, detail macro.
8. **API.** One entry point other tickets can call: `huntkit.viz3d.studio.render(concept_scene, shots, out_dir)`, where a concept supplies its drape mesh, piece boundaries, strap paths and hardware placements. Document it in `huntkit/viz3d/README.md`.
9. **Proof.** Rebuild CORRIE B.2 through the new layer. Render hero, side, belt front 3/4, door open, and two macro details (a buckle on webbing with stitching; the door zip corner). Make a before/after sheet against `docs/screens/20261109_corrie_b2_1.png` and `_3.png`.
10. Read every image you render and iterate until nothing floats, intersects or looks like CAD. Keep a defect log. Record render time per frame; keep a quick mode under 60 s per frame.

## Deliverables
- `huntkit/viz3d/assets/__init__.py`, `hardware.py`, `webbing.py`, `seams.py`, `zips.py`, `fabric.py`; `huntkit/viz3d/studio.py`
- `tests/test_viz3d_assets.py` (mesh dimensions against records; watertight checks; skips if bpy is missing)
- `designs/pack_5200/analysis/blender_model_quality.md` (what changed, defect log, how to use)
- `outputs/screens/20261111_BL018_<n>.png`; best six copied to `docs/screens/`

## Acceptance
- Hardware dimensions match the records within 0.5 mm where a record exists.
- The before/after sheet shows visible stitching, real hardware and fold-scale wrinkles.
- Another agent can render a new concept through `studio.render` by following the README alone.

## Out of scope
Changing any design. Editing `cycles_render.py` beyond additive hooks (keep the old entry points working).
