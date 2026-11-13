# BL-034 Rev 3 package cleanup (closes the release)

**Size:** M · **Depends on:** BL-032, BL-033

## Part A (pack-designer, with pattern edits)
1. **Pattern marks** in `patterns_corrie_f_rev3.py` + export:
   - place the 8 B-11 lash tabs (bow riser and muzzle keepers), which un-holds op 4.07;
   - draw box-X marks on W3, the IM1–IM3 end loops, the US eyes, B-24 (38×38 + 3 × 38×20 per `attach_system`) and the B-25 folds;
   - add K-W keeper notches at the W heights and the F-02 placement on B-05;
   - settle the B-28 front tab face (inside or outside the hinge band) and its box size (25×25 vs 21×20), consistent with the T9 strap path.
2. **Ledger:**
   - thread from the op lengths, about 21 g instead of the 4 g booked;
   - beginner build hours to match the op sequence (about 71 h per bag; the HOURS model must count webbing parts, lid and fly).
3. **Regenerate and update:** `weight_rollup_v2.md/.json`, `outputs/loadout/corrie_f_loadout.json`, and the totals in DESIGN.md and `corrie_f_body.md`.
4. **Door D1:** replace D1's three self-paired placeholder seams in `corrie_f.build`.
5. **BUILD_PLAN.md (RD-21):** point it at `outputs/release/pack5200_corrie_f_rev3/`. Merge `manufacturing/delta_register_rev3.md` into `docs/release_delta_register.md/.csv`.

## Part B (materials-engineer, in parallel)
Write material records for: 25 mm cam buckle, tri-glide, POM toggle, 25 mm and 6 mm elastic, #5 coil sliders, and any other BOM line marked PRICES or ELASTIC in `outputs/release/pack5200_corrie_f_rev3/manufacturing/bom.csv`. Each record needs cited properties, mass and price.

## Part C (manufacturing-engineer, after A and B)
1. Re-run `mfg_corrie_f_rev3.py` against the final patterns and records. Fix the stale "part A clamp" text.
2. Propose moving `SewingOp`/`BOMLine`/`tech_pack` into `huntkit/manufacturing/`, with every consumer updated per CONTRACTS.
3. Regenerate the tech pack. Op 4.07 must be released (no longer on HOLD).
4. Run the full suite.
