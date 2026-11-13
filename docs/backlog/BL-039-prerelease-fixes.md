# BL-039 Pre-release fixes after BL-038

**Agent:** pack-designer, asking structural questions in its report · **Size:** S

1. **S crown strap has zero spare:** the S kit's longest simulated path (928.1 mm) equals the cut minus two 50 mm grip tails. Add margin (e.g. +40 mm on S, and check M and L the same way). Update `corrie_f.py`, the ledger, the patterns and the mfg package (keepers stay).
2. **Structural confirmations, recorded in `designs/pack_5200/analysis/`:**
   - the CA-1 release rule "flip + 0.02 on the BL-027 body", giving 0.276;
   - the MT-1c bound "static if peak-to-peak ≤ 10 % of mean".
   Use h1_buckling.json, im3_body_simloads.json and load_standard.md; correct either if the data says otherwise.
3. **Stale docs:**
   - `CA1_fatigue_rig.md`: 0.310 → 0.276, 28 mm cheek, the current load.
   - TEST_PLAN §0/§3 counts and kit totals.
   - Retire PT-4 (crown hood removed 2026-11-12).
   - The h1_buckling.md §4.2 claim about the spreader share (wrong per BL-037).
   - The BP-1 sample cost.
   - The roll-up's feature greedy: exclude DESIGN requirements (hydration sleeve, hipbelt pocket) from the "unfrozen" items.
4. **Regenerate** the rev 3 mfg package so release_tests.csv picks up the T9-R3a–d split; also regenerate the test kit. Run the full suite.
