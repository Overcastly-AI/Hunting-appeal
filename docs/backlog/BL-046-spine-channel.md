# BL-046 H1 spine channel and spine offset

**Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-045

1. **Spine channel:** the printed channel (40.2 × 18.3 mm) was sized for the old 30 × 3 mm plate spine. Re-size the channel and the pawl housing for the OD 20 spine tube and the 6 mm rack, with stated running clearance, at every crown kit S/M/L and every torso setting. Re-export the print files; the slice check and the watertight checks must pass. Slice-check the channel too, and add a test.
2. **Spine offset:** decide whether the spine sits in the bar's plane, as modelled, or 15.85 mm fore, as printed. Make the model and the print agree. If it stays offset, carry the roughly 12 N·m at the clamp and in the body; then re-run the clamp bond, the body fatigue (all R1 bases) and buckling. The R1 margins must hold, or the report must say which don't.
3. **Ledger and records:** book the clamp (+4.4 g) and any channel mass change. Re-run `frame_fixed_results.json` and `frame_h1_results.json`, which still carry the "fairleads present" key.
4. **Roll-up test:** `test_weight_rollup_v2::test_scenarios_are_kept_separate` now fails because proven-now (3741.9 g) exceeds the B.2 start (3740.9 g). Restate what the test should assert honestly (the scenarios stay separate and are not ordered by mass), and fix it.
5. **Full suite.** Screenshots prefix `20261113_BL046_`.

Don't edit the bag pattern, mfg or `corrie_f` files (BL-044 is in them).
