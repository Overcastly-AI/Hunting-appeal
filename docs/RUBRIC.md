# Iteration rubric: strong, lighter, better looking (owner, 2026-11-24)

Owner: "Keep iterating on the design. Strong, weighs less, and looks better. You might not reach all of these but it can be a rubric."

Every iteration proposal is scored on the three axes below, in this priority order. A change that loses on **Strong** is rejected whatever it gains elsewhere.

## 1. Strong (gate, never traded)
- Every HA-LS-1 rev C row ≥ its goal (`designs/pack_5200/analysis/load_standard.md`), checked on the exported print geometry, not the voxel model.
- Score = the minimum margin over: strength, buckling, creep, fatigue (static-cinch), joints. Baseline 2026-11-21 (BL-058): strength 1.63, fatigue 1.25, creep 2.66, **buckling 1.05**, US2 lug 3.34/1.50.
- Bonus: lifting the R1 hold (cinch-cycled fatigue **0.86 → ≥ 1.0**) and the buckling margin (1.05 → ≥ 1.15).
- Bag: every load point SF ≥ its goal (`mfg_corrie_f_rev3.py --check`, min SF 1.36 baseline).

## 1b. Cost cap (owner, 2026-11-25: "$2100 is out of control for a backpack frame")
- Gate after Strong. ASSUMPTION COST-CAP (orchestrator call, owner may override): frame materials ≤ USD 150 per frame (filament + frame hardware, landed incl. shipping; briefly raised to 160 for B81-Lb, reverted after review 9); first-frame proving prints (coupons, first articles) ≤ USD 150 more; no new tool over USD 50 beyond the existing test kit.
- Every price from a material record or a cited shop page.

## 2. Weighs less
- Metric: ledger base mass, belt M, crown kit M ("proven now"), `designs/pack_5200/analysis/weight_rollup_v2.md`. Baseline 4038.1 g (8.90 lb) proven now, 3450.9 g (7.61 lb) after tests (`weight_rollup_v2.py` re-run 2026-11-24, BL-067; the old 3.99 kg / 3986.8 g predates BL-053 to BL-058); ledger default config total 4274.2 g after BL-058.
- Standing target 2993.7 g (6.6 lb) base; the previous push (`weight_push.md`) found only 119 g of incremental levers, so further gains must come from architecture (frame material/topology, part count, fabric/system choices), not trims.
- Every gram from the ledger; competitor weights from cited sources (`docs/research/`).

## 3. Looks better
- Judged on phone-readable renders (front, back, side, carried on a figure, loaded and empty), against a written design-language brief (`docs/research/` cited references for premium mountain packs; original IP only).
- Criteria: one coherent silhouette and line language across bag and frame; clean panel/seam lines; solid colourway with camo as edgy accent panels (house rule); no visible hardware clutter or hanging tails; frame surfaces that look intentional, not like an FE result.
- Score: a design-reviewer pass/fail per criterion on the renders, plus owner pick between A/B renders.

## Process per iteration
1. Research first (cited).
2. Concepts scored on this rubric → orchestrator picks (logged in DECISIONS as owner-may-override).
3. Implement → checks on real geometry → screenshots → independent review.
