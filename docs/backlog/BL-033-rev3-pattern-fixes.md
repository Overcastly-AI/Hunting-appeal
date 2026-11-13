# BL-033 Rev 3 pattern fixes before the build package closes

**Agent:** pack-designer, with pattern updates · **Size:** M · **Depends on:** BL-032 A

## Tasks
1. **Hinge swell window vs B-18:** the window (x ±115, z 40–130) overlaps the B-18 hinge doubler (z 35–80). Move one or reshape so the doubler is never cut away. Recheck the hinge load path (`loadpath_check` / BL-010 method) and report.
2. **B-22 at x ±130.3:** recompute the port guy path with BL-028/029 `--route` at 15 in meat (fine mesh). It must stay ≤ 185 mm, with lifter gap ≥ 10 mm and R-28 ≥ 31°. If it fails, use a 38 mm tab at ±149 instead.
3. **FP pockets:** cut 165 mm wide; update the geometry and the access check (hip-reach, zero misses).
4. **Ledger fixes:**
   - remove the "attachment: B-01 swell patches" (12.3 g) double booking from `adopted_bag_rows`;
   - book B-01 net of its 8 swell windows;
   - set the B-27 slit to 156.2 mm on the fabric;
   - replace the three self-paired placeholder seams in `corrie_f.build` with the real pairs from `patterns_corrie_f_rev3.py`;
   - give the US floor channels geometry, or delete the row if there is no function for them;
   - correct the lid hours to the drafted 9.53 h.
5. **F-01 rain fly:** draft it for the CORRIE F rev 3 shape and lid, add it to the pattern release (DXF, PDF, marker), and reconcile it with the ledger.
6. **Patterns:** re-run `patterns_corrie_f_rev3` and its export, so the release folder matches. Run the full test suite. Screenshots prefix `20261113_BL033_`.
