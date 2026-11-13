# BL-035 Record masses everywhere; small pattern and ledger fixes

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-034 A

1. **Record masses everywhere** (orchestrator call, one mass basis): re-run `geometry.yaml`/`build_geometry`, the bag-competition results, CORRIE B.2 and the crown diet. Then re-set these 9 failing tests with the new reference values, and explain each delta:
   - attach_diet sensitivity;
   - bag_comp_A, two bag_comp_D tests, two bag_comp_lean tests;
   - build_geometry, crown_diet, mass_ledger frame cross-check;
   - strap_arch;
   - strap_tails BL-029 history (keep history values reproducible, or document why they move).

   Also apply crown_diet TOGGLE_G, the bag_attach lifter tri-glide constant and cam_25mm_al (keeping 1 g of pull tab) from the records.
2. **B-28t:** split it into its own piece with a 21×15 box at the tip end, so the B-28 rear toggle passes. Then fix the box mismatches:
   - B-02h B-22/LLT box vs LLT piece (25×25 vs 21×25);
   - `attach_system.link_piece` 34×30 hook box vs its 38×38 capacity row (pick one and make capacity match);
   - move the B-28t label so it doesn't cover the B-24 hook box.
3. **Ledger:**
   - remove the thread double count in the misc line (3 % of soft goods), since bag thread is now booked;
   - add the rifle muzzle-keeper cord to the ledger and BOM inputs;
   - re-base "attachment: elastic keepers" on elastic_25mm with a cut length.
4. **Regenerate** the patterns release and the roll-up. Run the full suite. It must be green apart from any tests in `tests/test_mfg_corrie_f_rev3.py`, which the manufacturing-engineer owns concurrently.
