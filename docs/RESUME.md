# Updated 2026-11-05 (bag-to-frame attachment phase). The joint is designed bottom to top: crown hood + top guys at the top, rated bag hooks, sewn side with drawings. Next: owner choices in `analysis/bag_attachment.md` §12, the structural re-check with the hood loads, proof tests PT-1..PT-5.

## Bag-to-frame attachment phase (2026-11-05, pack-designer, not committed)
- Record: `designs/pack_5200/analysis/bag_attachment.md` (generated: `python -m huntkit.gendesign.attach_system` for the full run, `--docs-only` to rewrite; `bag_attach.docs_only()` still works). Numbers: `analysis/attach_system_results.json`
- Top anchor: **crown hood** (B-19, Hypalon J-profile over the crown top bar, on a 17-rung ladder B-20, one rung per crown setting) + **two fixed-length top side guys** (sewn to the hood ears, to B-22 on the outer-face corners). Lift-and-drop: a bag hinged at z 60 meets the bar in the peel direction, so no pocket can snap on passively
- Cloth sim (`huntkit/clothsim/scenarios/pack5200_v31_att_*.yaml`, new additive key `attachments.pocket`): load CG fill **189 / 177 / 168 mm** at 15 / 19 / 23 in (before 223); meat 181 / 173 / 165. 180 mm met at 19 and 23 in, missed at 15 in by 9 mm (nothing on the frame above z 601). R-28 with the simulated wall + hood: first contact >= 31 deg (15 in meat is the tightest, gap 0.6 mm at 30 deg)
- Compared: hood alone, study G (tie + guys) at 15/19/23, lifters as the anchor (rejected, US 10,952,523 switching), cinched guys (fail R-28 at 15 in)
- IM3 hook: all four bag hooks one rated part >= 2200 N; PT-1 2120 N (1.5 x C5 hood-off 1415 N); SF 1.55 (was 1.06)
- Sewn side: HE, B-18, T2 + B-23 (new), T3 + B-17, B-19/B-19s/B-19L, HT + POM toggles, B-20, TG + B-22; box-X 7 SPI tex 135, perimeters 8 SPI tex 90; every part SF >= 1.55; proof tests PT-1..PT-5. 1:1 drawings `designs/pack_5200/cut/attachment/attachment_parts.pdf` / `.dxf`
- Procedures: bag off 52 s, bag on 59 s, between 70 s + loading, bag-off haul 108 s; repair kit. `meat_haul.DETACH_S` = 52 (`meat_haul.docs_only()` added)
- Mass **+136 g**, pack **3207 g (7.07 lb)**, about $16. No new frame feature; crown-bar loads for the structural re-check are in §9 of the record
- Owner choices (record §12): (1) accept the 15 in result (rec.) vs hood on the extension posts (IP opinion); (2) accept +136 g (rec.); (3) one rated hook for all four bag hooks (rec.) vs IM3 only; (4) FTO read on US 12,495,885 + confirm MR '171/'114 expiry (rec.); (5) lighter options
- Pattern-maker regen list: record §10 (B-01 B-23 marks, B-01b/B-01u B-20 placement, B-02d B-22 marks, new pieces, webbing cut list, hardware). Patterns and the release are not edited
- Screens: `outputs/screens/20261105_attach_1.png` (exploded), `_2.png` (hood detail), `_3.png` (sim before/after at 15/19/23 in), `_4.png` (procedure storyboard), `_5.png` (sewn parts preview)

## Bag-top anchor study (2026-11-05, pack-designer, not committed)
- Record: `designs/pack_5200/analysis/bag_top_anchor.md`. Scenarios: `huntkit/clothsim/scenarios/pack5200_v31_tab_doubler.yaml`, `pack5200_v31_anchor_{A..H}_*.yaml`. Compare and PNGs: `python designs/pack_5200/bag_top_anchor.py`
- Sim additions (additive, contract §7): hinge `doubler_mm`, hook `tab`, generic `ties`, `contact.crown`, CG rows in `diff`
- Fill / meat CG, 68 kg: baseline 223 / 206 mm; tab + doubler 205 / 193; crown-bar tie (existing top bar) 192 / 186 at 19 in, 202 / 192 at 15 in; **tie + fixed-length forward top guys 179 / 174** (best; wall 6–12 mm toward the head, R-28 margin 6.8 mm, so re-check); collar-height anchor 180 / 176 (needs a new frame feature, 21 mm toward the head)
- Specified: B-17 IM3 hook tab, B-18 hinge-eye doubler (+27.8 g), bow riser carry (+12.1 g). Pack **3071 g (6.77 lb)**
- Open, carried into the attachment phase: (1) choose the top anchor and its hardware/procedure (`bag_attachment.md` untouched); (2) with the tab, the IM3 hook sees 450–472 N at 1 g, so SF 1.06 on the assumed 1500 N at C5 and the proof test must rise; (3) structural re-check of the frame at CG 205 mm (C1) / 175 mm (C5), load standard not changed; (4) pattern-maker regen list in §9 of the record (B-17, B-18, bow loops; B-01 outline unchanged)
- Feature freeze closed by the owner: bow riser carry, no spotter pocket, no meat sleeve, 15.5 in. Fabric swaps O-3/4/5/6/15 on hold, not applied
- Screens: `outputs/screens/20261105_bagtop_1.png` (profiles + CG), `_2.png` (attachment layout)

## Bag pass (2026-11-05, pack-designer, not committed)
- `build_geometry.py` reproduces `geometry.yaml` / `panels.yaml` byte for byte again (`tests/test_build_geometry.py`). Run `python designs/pack_5200/build_geometry.py` (add `--no-plots` to skip the PNGs)
- Geometry now describes the two-ring-seam head setback (z 560 / 631.2, ruled between), `geometry.yaml → bag.head_setback`. Width scale 1.0639 kept, so the released patterns stay valid. As-sewn 85.14 L (5195 cu in)
- `geometry.yaml → weight` is the PRODUCTION pack: **3030 g (6.68 lb)**, 762 g over 5.0 lb. v3.1 tube budget frozen as `weight.v31_tube_baseline`
- B-10 frame-link tabs retired (−21.6 g, 3052 → 3030 g). `bag_attachment.md` notch now 30 mm, from the source (`bag_attach.docs_only()`)
- Weight-cut plan: `designs/pack_5200/analysis/bag_weight_plan.md` (generated by `designs/pack_5200/bag_weight_plan.py`). 17 items; recommended owner YES set (O-3, O-4, O-5, O-6, O-15) is −54 g. **The bag cannot close the gap** (all items together 464 g, most cost function). Owner choice OC-0: restate the target or order a frame-side study
- Feature freeze table: DESIGN.md §4.11. Closed by the owner 2026-11-05 (bow riser carry, no spotter pocket, no sleeve, 15.5 in); IM1 bag clip still open; bag-to-frame attachment re-opened
- Screens: `outputs/screens/20261105_bag_1..4.png` (viz3d hero, side, weight budget, ranked cuts)

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
4. Proof tests: PT-1..PT-5 (rated bag hook 2120 N, T3 tongue, hinge eye, crown hood, guy ladder lock; `analysis/bag_attachment.md` §5) and the 1500 N meat-strap hook + 1100 N under-strap cam at 830 N
5. Decide whether IM1 later gets a bag clip
6. Close the weight gap (now 3030 g / 6.68 lb vs 5.0 lb). Bag side: owner answers on `analysis/bag_weight_plan.md` (OC-0 target, O-1..O-16). Spreader levers left (`spreader.md`): drop the cleat notches, a bottom-bay support from the lumbar struts, or relax the bone-at-notch-root case on a physical test
7. Update `designs/apparel/camo/owner_base.yaml` and `designs/apparel/camo/DESIGN.md` for the real camo SVG
8. Manufacturing-engineer: add the spreader (board, clips, pucks, pads, tubes) to the BOM / tech pack and the beginner release set in `outputs/release/`. Rebuild the base-weight BOM from the released cut list (plan cross-check: fly −13.6 g, accents −9.1 g vs the design estimate). The generator drift is fixed
9. materials-engineer: add the records `analysis/bag_weight_plan.md` lists as missing (70D ripstop, 20D silpoly, 300D printable, 25 mm cam/hook, #8 slider, seam tape, grid abrasion). Pattern-maker: nothing to regenerate; material-id swaps only if the owner accepts plan items
10. Then: design-reviewer pass on the spreader and frame records, BOM/tech pack, and the apparel line
