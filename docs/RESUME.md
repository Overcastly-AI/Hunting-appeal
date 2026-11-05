# Updated 2026-11-05. Spreader is done (Sandwich v2). Resume with the shoulder yoke.

## Where we are
Merged on main:

- Pack 5200 v3.1 "Spine" bag: true 85.16 L main bag, diagonal zip, internal meat straps (no shelf)
- FRAME (PR #2): one branching PAHT-CF print. Split stays, lumbar struts, smooth surface. Printed body 774 g. Frame **1194 g** before the fairleads. Min SF **1.66**, fatigue **1.10**. The split joint at z=234 is not yet re-solved. Record: `designs/pack_5200/analysis/generative_branch.md`
- SPREADER: **done**, Sandwich v2 is production (owner 2026-11-05, see below). The old 208×300×2.0 mm QI sheet (193 g) is retired: it fails on the real frame. Back system: sandwich on the bag side of the stays, 100 mm × 10 mm XLPE rails on the stay lines, open mesh over the window
- ATTACHMENT (PR #3): eight printed fairleads, detachable bag, two 38 mm under-bag cradle straps at z 95 and z 142. They cinch the bag floor and stay on the frame as a meat cradle. Detach **40 s**. Cradle anchor, 1 mm mesh, at 489 N: strength SF 3.28, fatigue SF 1.47. Added 122 g, about $22. Pack about **3101 g (6.84 lb)** with the old sheet, **3052 g (6.73 lb)** with the sandwich, vs the 5.0 lb target
- MEAT HAUL, both required. Fatigue SF: **bag on 1.62** (US1, 444 N; cam SF 2.48), **between 2.46**, **bag off 1.47** (cam SF 2.25). Record: `designs/pack_5200/analysis/meat_haul_modes.md`
- The carbon-tube ladder (5.37 lb) was rejected. The solid 34 mm ladder (7.51 lb) is retired. `genframe_assembled.stl` includes the fairleads
- viz3d opens on the branch print, with the spreader loaded
- 5.0 lb is still missed, by 784 g with the sandwich (3052 g). Fairleads are 113 g of that and the under-straps are 122 g. Soft goods, the carbon crown, the spreader and the sleeve around the crown-leg bore are most of the rest
- Camo: owner's base pattern SVG is uploaded at `designs/apparel/camo/source/owner_base.svg`. `owner_base.yaml` and `designs/apparel/camo/DESIGN.md` still describe the proxy

## Spreader: DONE (owner decision 2026-11-05)
- **Production spreader: Sandwich v2** (BP-06 rev B): 200 g twill / 6 mm ROHACELL 110 / 200 g twill, notch doublers, two 10/8 mm edge tubes, 11 pucks, 2 pads, 6 PA12 clips. **154 g (5.4 oz)**, about **$188**. FPF SF 1.21, fatigue 1.04, sandwich local 1.06, skin 13.0 kPa. With the lumbar pan in the skin model it clears the lean torso by **8.4 mm** (walking 19.3 mm)
- Records: `designs/pack_5200/analysis/spreader.md` (+ `spreader_results.json`), re-check and Decision header in `analysis/spreader_layout.md`. Code: `huntkit/gendesign/spreader.py`, `spreader_report.py`. Tests: `tests/test_spreader.py`, `tests/test_spreader_production.py`
- Build files: `designs/pack_5200/cut/spreader/` (`spreader_v2_cut.dxf`, `spreader_v2_clip.dxf`, `spreader_v2_drawing.pdf`, beginner `README.md`)
- Frame: stay sockets removed. `designs/pack_5200/print/frame/genframe_*` are the socket-free body again (restored from commit bb4e99e). `PRODUCTION.md` updated (spreader, bone-end proof points, cost about $381 with the sandwich)
- Rejected: d6L (1.5 mm HDPE + 6 carbon cross stays, 217 g, $60). Kept in code as a documented alternative (`spreader_layout.py`, layout `d6L_tubes`); it writes its socketed frame to `outputs/spreader_layout/print_d6L/`, never to the production folder. Its sheet files `cut/spreader/spreader_v3_*` are marked "do not cut"
- Contract: `docs/CONTRACTS.md` §6 bearing face now names the sandwich. `meat_haul.py` / `meat_haul_modes.md` take the sheet SFs from `spreader_results.json`. BOM line BP-06 in `panels.yaml` and `build_geometry.py` updated (98.8 g board + 55 g hardware)

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
5. v3.1 production pattern set (commit 8bf8880)
6. Spreader v2 (2026-11-04), layout study (2026-11-05), owner picked Sandwich v2; frame sockets removed (2026-11-05, not committed)

## Next
1. Spreader first article: lay up one board, weigh it (target about 141 g without clips), coin-tap, then the PRODUCTION.md bone-end proof (400 N, 22 mm dowel) at the window centre, the US2 corner relief and the IM1 notch root. A notch-root coupon first is cheaper
2. Torso-adjust shoulder yoke: hook-and-loop on a loop-faced fabric skin over the spreader, plus a tightening strap. The run was cancelled before any output
3. Re-solve the z=234 split joint
4. Proof-test the 1500 N hook and the 1100 N under-strap cam
5. Decide whether IM1 later gets a bag clip
6. Close the weight gap (3052 g / 6.73 lb vs 5.0 lb). Spreader levers left (`spreader.md`): drop the cleat notches, a bottom-bay support from the lumbar struts, or relax the bone-at-notch-root case on a physical test
7. Update `designs/apparel/camo/owner_base.yaml` and `designs/apparel/camo/DESIGN.md` for the real camo SVG
8. Manufacturing-engineer: add the spreader (board, clips, pucks, pads, tubes) to the BOM / tech pack and the beginner release set in `outputs/release/`. `build_geometry.py` is out of sync with the hand-edited `geometry.yaml` / `panels.yaml` (re-running it changes the meat-harness note and the back-panel weight group); reconcile before regenerating
9. Then: design-reviewer pass on the spreader and frame records, BOM/tech pack, and the apparel line
