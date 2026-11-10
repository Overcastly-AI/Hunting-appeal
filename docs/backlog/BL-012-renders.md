# BL-012 Blender renders of the merged bag on the H1 frame

**Wave:** 3 · **Agent:** pack-designer · **Size:** L · **Depends on:** BL-011, BL-018 (render through `huntkit.viz3d.studio`)

## Why
The owner judges designs from renders and rejected crude ones once ("This looks like garbage"). The competition renders are acceptable but all show an over-stuffed sack, hide the frame, and the wing pods read as slabs.

## Goal
Product-photo quality renders of CORRIE F, both door options, on the H1 frame with hipbelt B.

## Read first
`docs/backlog/RULES.md` rule 11; `huntkit/viz3d/README.md`, `cycles_render.py`, `corrie_b2.py` (how the last good set was built); the display form and belt modelling in `huntkit/viz3d/corrie_b2.py`; the H1 frame GLB (`outputs/` is not tracked: regenerate it with `huntkit/gendesign/frame_h1.py` and `huntkit/viz3d/frame_pair_render.py`, see `designs/pack_5200/analysis/frame_h1.md`); BL-011's fine drape.

## Shots (1600 × 1200, ≤ 64 samples)
1. Hero 3/4 rear, 6-day load (45 L), cinched.
2. Side profile on the display form, same load.
3. Day load (about 12 L), rolled down and cinched.
4. Full 85 L.
5. Door open, option D1. 6. Door open, option D2.
7. Meat inside the bag on IM1–IM3, door open.
8. Bag off, meat on the frame, showing the H1 frame clearly.
9. Add-ons: scope pod and tripod on, then off (two images or a split).
10. Hipbelt and pockets from the front 3/4.

## Tasks
1. Build the viz3d model from the BL-011 drape; every part sits on the surface (use the projector approach in `corrie_b2.py`).
2. Fix the known look problems: straps shown tensioned over the fabric with visible dimpling; zips with coil, sliders and garages; camo at true scale; no slabs for pods (drape or round them).
3. Render, then Read every image and list defects; re-render until none remain. Write the defect log into the deliverable doc, including defects you could not fix.
4. Make one comparison sheet: CORRIE B.2 against CORRIE F, same camera, same load.

## Deliverables
- `huntkit/viz3d/corrie_f.py`, `designs/pack_5200/concepts/corrie_f_viz3d.py`, `tests/test_viz3d_corrie_f.py` (builds the scene; skips if bpy is missing)
- `outputs/screens/20261111_BL012_<n>.png` (all shots), best six copied to `docs/screens/`
- `designs/pack_5200/analysis/corrie_f_renders.md` (shot list, defect log)

## Acceptance
- No image has floating parts, intersecting geometry, z-fighting, stretched or blocky camo, or placeholder shapes.
- The three load states use the same camera and clearly differ.

## Out of scope
Changing the design to make it look better; propose such changes in the report.
