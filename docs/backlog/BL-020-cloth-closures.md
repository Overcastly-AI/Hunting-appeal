# BL-020 Render realism: roll-top, top pouch and part-full loads as real cloth

**Wave:** 2 · **Agent:** pack-designer (Fable) · **Size:** L · **Depends on:** BL-018 (studio layer), BL-009 (shell S15)

## Why
After BL-018, macros read as photographs but full-pack shots do not:
- The roll-top, top pouch and (now deleted) wings are lofted shapes with added wrinkles.
- Real rolled closures and strap cinches make 10–30 mm folds; BL-018 capped the wrinkle pass at 5 mm.
- The cloth sim cannot drape part-full loads (BL-009's day and 6-day drapes did not converge).

The owner judges the design from renders.

## Goal
Full-pack renders of the merged bag's shell (S15, wings deleted) that read as photographs at day, 6-day and full loads.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/blender_model_quality.md` (defect log and limits); `huntkit/viz3d/studio.py`, `assets/`; `designs/pack_5200/analysis/shell_sweep.md` and `concepts/shell_sweep.py`; owner decisions 2026-11-11 in `docs/DECISIONS.md` (wings removed).

## Tasks
1. **Render-only cloth pass.** Use Blender's cloth solver (in the bpy venv) for presentation geometry only; the huntkit cloth sim stays the engineering source.
   - Seed from the huntkit drape.
   - Pin to the frame interface.
   - Fill with a packed-contents proxy volume: day 12 L, 6-day 45 L, full 85 L.
   - Cinch W1–W3 and the roll clips as constraints.
   - Simulate the roll-top as a rolled collar (3 turns, clipped down to the sides).
   - Simulate the top pouch on the roll.

   Report how far the result departs from the huntkit drape (mean and max, mm) at the full load. It must stay within 15 mm except at the roll and strap cinch lines.
2. **Fix BL-018's open defects:** the floating shard on the belt frame, the mottled band beside the door seam, the dimples under the pouch G-hooks, and webbing through the 50 mm belt buckle, ladder locks and sternum buckle.
3. **Shots:** hero 3/4 rear, side, and the three load states (same camera); a door-open view; one macro of the rolled closure. Wings deleted; W1–W3 carrying a tripod and the scope pod on the side for one shot.
4. Read every image and iterate until it reads as a photograph. Keep a defect log.
5. Make the pass reusable: `studio.render(..., cloth_pass=True)` with documented parameters, so BL-012 can use it on CORRIE F.

## Deliverables
- `huntkit/viz3d/cloth_pass.py`, `tests/test_viz3d_cloth_pass.py` (skips without bpy)
- `designs/pack_5200/analysis/cloth_pass.md` (method, departure numbers, defect log)
- `outputs/screens/20261111_BL020_<n>.png`; best five copied to `docs/screens/`

## Acceptance
- The three load states clearly differ in shape, and the day load does not look stuffed.
- No floating parts, intersections or lofted-looking closures in any shot.

## Out of scope
Changing the design or the engineering numbers. Editing `huntkit/clothsim/`.
