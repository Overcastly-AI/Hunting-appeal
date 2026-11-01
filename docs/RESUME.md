# Paused 2026-11-01. The production frame is the printed branch body. Resume with patterns.

## Where we are
- Pack 5200 v3.1 "Spine" bag: true 85.16 L main bag, diagonal zip, internal meat straps (no shelf)
- BACK SYSTEM (unchanged): 2.0 mm QI carbon spreader, 100 mm × 10 mm XLPE rails, open mesh over the window. Peak skin pressure 10.6 kPa, spread 100 mm. Record: `designs/pack_5200/analysis/back_comfort.md`
- FRAME: one branching PAHT-CF print. Split stays, lumbar struts, smooth surface. Printed body **774 g**. Frame **1194 g**. Pack **2865 g (6.32 lb)**. 2 mm check, minimum SF **1.66**, fatigue **1.10**. Record: `designs/pack_5200/analysis/generative_branch.md`
- The carbon-tube ladder (5.37 lb) was rejected. The solid 34 mm ladder (7.51 lb) is retired. `genframe_assembled.stl` is the branch body
- viz3d opens on that print, with the spreader loaded
- 5.0 lb is still missed, by 597 g. Soft goods, the carbon crown, the spreader and the sleeve around the crown-leg bore are most of that gap
- Camo: owner's base pattern; the SVG still needs uploading to designs/apparel/camo/source/owner_base.svg

## Done this pass
1. structural-fea-engineer: production frame is the generative branch print. Tube ladder reverted. Comfort kept

## Still open
2. pattern-maker: full v3.1 bag pattern set
   - pieces, seams checked, volume re-check, hipbelt S–XL
   - DXF/PDF/SVG files, markers, yardage
   - beginner print set in outputs/release/
3. Then: manufacturing-engineer (BOM, sewing ops, equipment buy list, beginner guides, tech pack), design-reviewer pass, apparel line.
