# BL-019 A realistic hunter wearing the pack

**Wave:** 1 (independent) · **Agent:** pack-designer (Fable) · **Size:** XL · **Depends on:** none (hands its figure to BL-018's studio layer)

## Why
The owner: "We need a real hunter wearing it." Today the pack is shown on a grey display form or a clay mannequin. The owner judges the design from renders and wants to see it on a person: fit on the back, where the belt sits, how tall the bag rides behind the head, how it looks in the field.

## Goal
A realistic, clothed, posed 3D human figure wearing the pack, rendered in Blender Cycles in a studio and in an outdoor setting, with the pack fitted to the body correctly. It is a rendered 3D person, not a photograph; say so in captions.

## Read first
`docs/backlog/RULES.md`; `huntkit/viz3d/README.md`, `cycles_render.py`, `corrie_b2.py` (current display form, belt B on the pelvis, harness); `designs/pack_5200/analysis/hipbelt_fit.md` and `hipbelt_anthro.yaml` (ANSUR II hip forms; belt on the iliac crest); `designs/pack_5200/DESIGN.md` (torso settings 15/19/23 in, head clearance R-28, lifter angle); `docs/backlog/BL-018-blender-model-quality.md` (the studio layer being built in parallel: your figure must plug into it).

## Tasks
1. **Research and licence check first** (`docs/research/human_figure_sources.md`, URL and licence text quoted for each): open human-model sources usable for commercial product images. Candidates: MPFB2 / MakeHuman (CC0 base assets), Blender Studio human base meshes (CC0), others you find. Reject anything non-commercial (for example SMPL) or with unclear terms. Record the licence of every asset you use, including clothing, hair, textures and HDRIs (Poly Haven is CC0).
2. **Figure.** Build a parametric adult figure sized from ANSUR II to match the 19 in torso setting (also able to produce 15 in and 23 in wearers). Realistic skin, face, hands and hair or a cap; no uncanny blank face in hero shots (a cap, beard, sunglasses or a three-quarter-back camera are acceptable ways to keep it natural). Download assets outside the repo (scratchpad cache); commit only the build script and a manifest with URLs, versions and checksums.
3. **Clothing.** Original, plain technical hunting clothing in solid colours from our palette (no logos, no other brand's camo or trade dress): base top, soft-shell jacket or mid-layer, pants, boots, gloves optional, cap. Our apparel line is not designed yet, so keep it generic and say so. Cloth should drape (Blender cloth or sculpted folds), and compress under the shoulder straps and hipbelt.
4. **Fit the pack to the body.** Hipbelt B centred on the iliac crest with the wings wrapping the hips; lumbar pad in the lumbar hollow; shoulder straps following the shoulders with the sternum strap closed; lifters at their design angle; frame along the back; head clearance as the design says. Straps must touch the body: no gaps, no intersections. State the fit numbers you matched (torso length, belt height, lifter angle, head gap) against the design values.
5. **Poses.** At least: standing three-quarter rear (hero), walking uphill with trekking poles, side profile, kneeling and glassing with the pack on, and front three-quarter showing belt, pockets and bottle. Rig with a standard armature; keep poses natural and the pack rigid on the torso.
6. **Scenes.** (a) studio, matching BL-018's lighting; (b) outdoor mountain setting with a CC0 HDRI and a simple ground, sun low, pack readable.
7. **Use CORRIE B.2 as the pack** (regenerate its drape if `outputs/` is empty; see `designs/pack_5200/concepts/corrie_b2_viz3d.py`). Expose the figure so any later concept can be dressed on it: `huntkit/viz3d/wearer.py` with `build_wearer(torso_in, pose, outfit)` returning objects BL-018's `studio.render` can take. Coordinate through files only: read `huntkit/viz3d/studio.py` if it exists when you integrate; if it does not, provide a standalone render path and note the hook.
8. Render at 1600 × 1200, ≤ 96 samples. Read every image; fix interpenetration, floating straps, stretched textures, broken fingers and dead eyes before reporting. Keep a defect log.

## Deliverables
- `huntkit/viz3d/wearer.py`, `huntkit/viz3d/assets/human_manifest.json`, `tests/test_viz3d_wearer.py` (figure dimensions against ANSUR targets; skips if bpy or assets are missing)
- `docs/research/human_figure_sources.md`
- `designs/pack_5200/analysis/hunter_figure.md` (fit numbers, licences, defect log, how to re-run)
- `outputs/screens/20261110_BL019_<n>.png`; best five copied to `docs/screens/`

## Acceptance
- Every asset has a recorded licence that allows commercial use; nothing large is committed.
- In the hero and front shots the belt sits on the hips and the straps touch the body with no visible gaps or intersections.
- A reader would describe the image as "a hunter wearing a pack", not "a mannequin".

## Out of scope
Designing the apparel line. Changing the pack design. Real photographs or generated photos of real people.
