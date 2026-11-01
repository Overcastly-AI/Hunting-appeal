# Paused 2026-11-01. The bag hangs on the branch frame. Resume with patterns.

## Where we are
- Pack 5200 v3.1 "Spine" bag: true 85.16 L main bag, diagonal zip, internal meat straps (no shelf)
- BACK SYSTEM (unchanged): 2.0 mm QI carbon spreader, 100 mm × 10 mm XLPE rails, open mesh over the window. Peak skin pressure 10.6 kPa, spread 100 mm. Record: `designs/pack_5200/analysis/back_comfort.md`
- FRAME: one branching PAHT-CF print. Split stays, lumbar struts, smooth surface. Printed body **774 g**. Frame **1194 g** before the fairleads. Record: `designs/pack_5200/analysis/generative_branch.md`
- ATTACHMENT: eight printed fairleads on the bag face of the stays. 5 mm 7075 pin, UHMWPE sleeve, 38 mm hook on IM2 and IM3. Hinge at z 60. Bag-off is optional (about 34 s). Cheek FEA at 1 mm: strength SF **2.97**, fatigue SF **1.67**. Net **+113 g**. Pack **2979 g (6.57 lb)**. Record: `designs/pack_5200/analysis/bag_attachment.md`
- The carbon-tube ladder (5.37 lb) was rejected. The solid 34 mm ladder (7.51 lb) is retired. `genframe_assembled.stl` is the branch body; the fairleads are in `frame_sdf` and show up the next time that STL is exported
- viz3d opens on the branch print, with the spreader loaded
- 5.0 lb is still missed, by 711 g. The fairleads are 113 g of that. Soft goods, the carbon crown, the spreader and the sleeve around the crown-leg bore are most of the rest
- Camo: owner's base pattern; the SVG still needs uploading to designs/apparel/camo/source/owner_base.svg

## Done this pass
1. structural-fea-engineer: production frame is the generative branch print. Tube ladder reverted. Comfort kept
2. Bag-to-frame attachment: branch fairleads, compared against a clip, a sleeve, a window lash, a rail, a cam and magnetic buckles. FEA on the printed cleat. Lifters stay on the crown. Hipbelt stays on the Ti pivot

## Still open
3. pattern-maker: full v3.1 bag pattern set, plus the eight B-01 swells over the fairleads (16 mm, feathered, 90 mm long) and the spreader notches
   - pieces, seams checked, volume re-check, hipbelt S–XL
   - DXF/PDF/SVG files, markers, yardage
   - beginner print set in outputs/release/
4. Then: manufacturing-engineer (BOM, sewing ops, equipment buy list, beginner guides, tech pack), design-reviewer pass, apparel line.
5. Owner questions on the attachment: keep bag-off, accept the eight swells, proof-test the 1500 N hook assumption, leave IM1 as meat-only
