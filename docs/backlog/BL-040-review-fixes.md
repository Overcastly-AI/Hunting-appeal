# BL-040 Fix the pre-cut review findings

**Agent:** pack-designer (patterns, ops, analysis), handing the test items to the kit generator · **Size:** L · **Depends on:** BL-039

Source: `designs/pack_5200/analysis/review_20261113_rev3_release.md`.

1. **Blockers:** fix all 3, each with a regression test that would have caught it.
   - **Hinge eye:** make it one definition everywhere (piece, op, load table, PT-3 specimen). Put B-18 properly into the floor seam. Extend the mismatch checker to every box, not just the hinge band.
   - **Roll top:** add a buckle-half tab piece, its placement mark, and an op before 4.11.
   - **Aft corner seams:** state the keeper/pocket layer order in op 4.12, with a sketch.
2. **Majors:** fix all 13.
   - The tripod-keeper cord ends; the op 1.01 pleat basting.
   - B-17 box size; the mirrored collar-ring notches; the B-22 label.
   - Guy ladder lock face: decide inside or outside, consistent with PORT-1 and the analysis.
   - QC-14 mass target on the primary-fabric basis.
   - LL-H at 1.5 × 288 = 432 N, with wet and −20 °C conditions per the records.
   - SEW-F in the test kit.
   - One-off vs production cost shown separately.
   - Needle system consistent with the recommended machine.
   - The camo print file comes from a separate camo-designer ticket; reference it.
3. **Minors:** fix the minors, or list each as accepted with its reason.
4. **Regenerate** patterns, mfg and the test kit; run the full suite; ask the reviewer's questions of yourself again. The release README must say "ready to cut" only if 0 blockers and 0 majors remain.
