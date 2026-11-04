# Paused 2026-11-01. Resume with the shoulder yoke.

## Where we are
Merged on main:

- Pack 5200 v3.1 "Spine" bag: true 85.16 L main bag, diagonal zip, internal meat straps (no shelf)
- FRAME (PR #2): one branching PAHT-CF print. Split stays, lumbar struts, smooth surface. Printed body 774 g. Frame **1194 g** before the fairleads. Min SF **1.66**, fatigue **1.10**. The split joint at z=234 is not yet re-solved. Record: `designs/pack_5200/analysis/generative_branch.md`
- SPREADER drawings: 208×300×2.0 mm QI carbon, **193 g**, square corners, no fairlead notches yet. Bone-end deflection **7.8 mm** against the 10 mm XLPE rails, still to be checked. Back system otherwise unchanged: 100 mm × 10 mm XLPE rails, open mesh over the window. Peak skin pressure 10.6 kPa, spread 100 mm. Spreader stress SF 1.95 on the factored bone. Record: `designs/pack_5200/analysis/back_comfort.md`
- ATTACHMENT (PR #3): eight printed fairleads, detachable bag, two 38 mm under-bag cradle straps at z 95 and z 142. They cinch the bag floor and stay on the frame as a meat cradle. Detach **40 s**. Cradle anchor, 1 mm mesh, at 489 N: strength SF 3.28, fatigue SF 1.47. Added 122 g, about $22. Pack about **3101 g (6.84 lb)** vs the 5.0 lb target
- MEAT HAUL, both required. Fatigue SF: **bag on 1.62** (US1, 444 N; cam SF 2.48), **between 2.46**, **bag off 1.47** (cam SF 2.25). Record: `designs/pack_5200/analysis/meat_haul_modes.md`
- The carbon-tube ladder (5.37 lb) was rejected. The solid 34 mm ladder (7.51 lb) is retired. `genframe_assembled.stl` includes the fairleads
- viz3d opens on the branch print, with the spreader loaded
- 5.0 lb is still missed, by 833 g. Fairleads are 113 g of that and the under-straps are 122 g. Soft goods, the carbon crown, the spreader and the sleeve around the crown-leg bore are most of the rest
- Camo: owner's base pattern SVG is uploaded at `designs/apparel/camo/source/owner_base.svg`. `owner_base.yaml` and `designs/apparel/camo/DESIGN.md` still describe the proxy

## Spreader v2 done (2026-11-04, not committed)
- Record: `designs/pack_5200/analysis/spreader.md` plus `spreader_results.json`. Code: `huntkit/gendesign/spreader.py` and `spreader_report.py`. Solver: `huntkit/fea/plate_grid.py`. Tests: `tests/test_spreader.py`
- The current 2.0 mm QI sheet fails on the real frame (FPF 0.66, fatigue 0.38, bottoms at the bottom edge, M4 holes land on nothing)
- Chosen part: twill / 6 mm ROHACELL 110 sandwich, notch doublers, edge tubes, pucks, 6 clips. **154 g** (−49 g). FPF 1.21, fatigue 1.04, sandwich 1.06, skin 13.0 kPa, air 10.1 / 4.0 mm
- ≤100 g not reached. Next levers: drop the cleat notches (sheet inboard of the cleats), a bottom bay support from the lumbar struts, or relax the bone-at-notch-root case with a physical test
- Cut files: `designs/pack_5200/cut/spreader/` (DXF, clip DXF, 1:1 A3 PDF)

## Merge status (all on main)
- PR #1 (owner camo SVG), PR #2 (generative branch frame), PR #3 (bag-to-frame attachment + under-straps) are all merged into `main`
- Housekeeping after the merge: analysis records stored Cursor's absolute `/workspace/...` screenshot paths. Made repo-relative so tests pass on any machine
- `python -m pytest -q`: **196 passed**. Needs `pypardiso` (in requirements.txt)
- To resume: read this file, then `docs/DECISIONS.md` (latest rows), then the analysis records linked above

## Done this pass
1. structural-fea-engineer (PR #2): production frame is the generative branch print. Tube ladder reverted. Comfort kept. Split joint at z=234 not re-solved
2. Bag-to-frame attachment (PR #3): branch fairleads, detachable bag, two under-bag cradle straps. Lifters stay on the crown. Hipbelt stays on the Ti pivot
3. Owner: both meat-haul modes required, eight swells accepted. IM1 stays a meat anchor only for now
4. Camo SVG uploaded on this branch (PR #1)

## Next
1. Torso-adjust shoulder yoke: hook-and-loop on a loop-faced fabric skin over the carbon spreader, plus a tightening strap. The run was cancelled before any output
2. Spreader v2: build a coupon and run a bone-punch test on a notch root (done in analysis, `analysis/spreader.md`)
3. Re-solve the z=234 split joint
4. Proof-test the 1500 N hook and the 1100 N under-strap cam
5. Decide whether IM1 later gets a bag clip
6. Close the weight gap (3101 g / 6.84 lb vs 5.0 lb)
7. Update `designs/apparel/camo/owner_base.yaml` and `designs/apparel/camo/DESIGN.md` for the real camo SVG
8. Then: v3.1 bag pattern set (eight accepted B-01 swells, 16 mm, feathered, 90 mm long; pieces, seams, volume, hipbelt S–XL; DXF/PDF/SVG, markers, yardage; beginner print set in `outputs/release/`), BOM/tech pack, design-reviewer pass, and the apparel line
