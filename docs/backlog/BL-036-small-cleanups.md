# BL-036 Small cleanups left by BL-034/035

**Agent:** pack-designer · **Size:** S

1. **attach_system B-24 / B-22 boxes:** `attach_system_results.json`, attach_system.md and cut/attachment/README.md still say B-24 has a 38 × 38 box; make them match the drawn boxes. B-22's capacity uses a 25 × 25 box; check it. Re-run attach_system, and in the same change set `corrie_f.BOOKED_TRIGLIDE_G` to 2.6 g so the tri-glides are not corrected twice.
2. **geometry.yaml misc thread:** it counts the harness soft goods twice (harness_J + harness_S); fix that (about −2.7 g). Then make `corrie_f.weight_table` / `pack_with_adopted` drop the bag thread share from misc, the way weight_rollup_v2 does.
3. **Stale numbers:**
   - `bag_weight_plan.py` cam (12.0 → record), or mark the file historical;
   - the bag_comp write-ups and verdict, and the crown_diet.md tables: refresh them from the JSONs, or add "superseded by BL-035" notes.
4. **Stale tags:** in `mfg_corrie_f_rev3.py`, the "BL-033 volatile" op tags (BL-033 has landed), 2 unused locals and an f-string with no placeholders.
5. **Full suite green.**
