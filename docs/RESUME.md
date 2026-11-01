# Paused 2026-11-01. Both meat-haul modes are required. Resume with patterns.

## Where we are
- Pack 5200 v3.1 "Spine" bag: true 85.16 L main bag, diagonal zip, internal meat straps (no shelf)
- BACK SYSTEM (unchanged): 2.0 mm QI carbon spreader, 100 mm × 10 mm XLPE rails, open mesh over the window. Peak skin pressure 10.6 kPa, spread 100 mm. Spreader stress SF 1.95 on the factored bone. Record: `designs/pack_5200/analysis/back_comfort.md`
- FRAME: one branching PAHT-CF print. Split stays, lumbar struts, smooth surface. Printed body **774 g**. Frame **1194 g** before the fairleads. Record: `designs/pack_5200/analysis/generative_branch.md`
- ATTACHMENT: eight printed fairleads, plus two 38 mm under-straps on fairleads at z 95 and z 142. They cinch the bag floor down and stay on the frame as a meat cradle. Cradle anchor, 1 mm mesh, at 489 N: strength SF **3.28**, fatigue SF **1.47**. Added **122 g**, about **$22**. Detach **40 s**. Pack about **3101 g (6.84 lb)**
- MEAT HAUL, both required: **bag on** fatigue SF 1.62 at US1 (444 N) and cam SF 2.48. **Between bag and frame** fatigue SF 2.46. **Bag off** the cradle carries the quarter, fatigue SF 1.47, cam SF 2.25. Record: `designs/pack_5200/analysis/meat_haul_modes.md`
- The carbon-tube ladder (5.37 lb) was rejected. The solid 34 mm ladder (7.51 lb) is retired. `genframe_assembled.stl` includes the fairleads
- viz3d opens on the branch print, with the spreader loaded
- 5.0 lb is still missed, by 833 g. Fairleads are 113 g of that and the under-straps are 122 g. Soft goods, the carbon crown, the spreader and the sleeve around the crown-leg bore are most of the rest
- Camo: owner's base pattern; the SVG still needs uploading to designs/apparel/camo/source/owner_base.svg

## Done this pass
1. structural-fea-engineer: production frame is the generative branch print. Tube ladder reverted. Comfort kept
2. Bag-to-frame attachment: branch fairleads. Lifters stay on the crown. Hipbelt stays on the Ti pivot
3. Owner: both meat-haul modes required, eight swells accepted. Two under-straps cinch the floor and cradle a bare-frame quarter. IM1 stays a meat anchor only for now

## Still open
4. pattern-maker: full v3.1 bag pattern set, plus the eight accepted B-01 swells (16 mm, feathered, 90 mm long) and the spreader notches
   - pieces, seams checked, volume re-check, hipbelt S–XL
   - DXF/PDF/SVG files, markers, yardage
   - beginner print set in outputs/release/
5. Then: manufacturing-engineer (BOM, sewing ops, equipment buy list, beginner guides, tech pack), design-reviewer pass, apparel line.
6. Still waiting on the owner: proof-test the hook (1500 N) and the under-strap cam (1100 N slip); whether IM1 later gets a bag clip
