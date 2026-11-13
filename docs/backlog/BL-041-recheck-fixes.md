# BL-041 Fix the re-review findings

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-040 · **Beside it:** structural check of the crown tube under the guy loops (Y-4)

Source: `designs/pack_5200/analysis/review_20261113_rev3_recheck.md`.

1. **X-1:** re-order op 4.05 so the B-18 rows are sewn through B-18 + B-01 before the HE is placed and boxed. Add a regression test: no stitch row may cross an open eye or loop region.
2. **X-2:** put the eye back at the pin. Make the eye top reach z 60 at the 18 mm fairlead throat with the box below it, no fold-down peel, consistent with `bag_attachment.md:118`. Re-derive the HE length and box position, re-issue PT-3 from the new drawing, and fix SK-8 (draw the B-18 rows and the real pin position). Add a test: eye-at-pin within ±3 mm.
3. **Y-1:** specify the PT-3 rig unambiguously: load through the floor seam as rated; the clamp must not bypass it. Include the B-18 rows in the specimen.
4. **Y-2:** move the RTM/RT clip path clear of the muzzle-keeper tabs, their cord and W3, with ≥ 10 mm clearance. Extend the clearance test to the buckle body and strap path.
5. **Y-3:** add 304 zigzag to the machine minimum in BUILD_PLAN.md, with a straight-stitch fallback for prototype tacks (rated or not, state which). Fix BUILD_PLAN lines 60/80 (still 120/19) and add tex 70.
6. **Y-4:** TL-1 waits for the structural result (agent running beside you; output in `designs/pack_5200/analysis/crown_tube_guy_loop.md`). Leave TL-1's load as is unless that file says otherwise. Reference it.
7. **Y-5 (orchestrator call):** first build uses solid 630D on the camo panels. Remove the double-bought base from the one-off cost, and keep the HyperD print yard as a test-kit specimen only. Fix the cost: thread by the cone, plus print shipping.
8. **Minors:** fix all 15 or accept each with a reason. That includes m-19, which needs a sewn anchor for the meat-strap cam on its rated path. The label overprint/clipping on the B-18 PDF (M-4) is a minor here too.
9. **Ledger:** book B-18 +3.1 g and the 2 RTM tabs.
10. **Regenerate** patterns, mfg and the kit, and run the full suite. The mfg README may say "ready to cut" only if 0 blockers and 0 majors remain on your own honest re-check. Say what a third review should look at.
