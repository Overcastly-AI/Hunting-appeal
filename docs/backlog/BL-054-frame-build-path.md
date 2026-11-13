# BL-054 Frame build path for a beginner, and the review-5 text and minor fixes

**Agent:** manufacturing-engineer · **Size:** M · **Beside:** BL-053

Source: `designs/pack_5200/analysis/review_20261113_fifth.md` (M-7, the bag gate print text, minors m-1..m-10).

1. **H1 frame build package:** write a complete, beginner-unambiguous build package in `designs/pack_5200/print/frame_h1/` (README plus a new `BUILD_H1.md`). It replaces any pointer to `../frame/PRODUCTION.md` (DO NOT PRINT). Cover:
   - **Printing:** the current masses and footprints from the STL and records, print settings and supports (read the BL-053 JSON when it lands; leave a clearly marked placeholder until then), reaming, inserts.
   - **Parts:** a spine clamp drawing (from `crown_spine_clamp` constants); a full hardware list (fairlead pins and sleeves, Ti hinge pins, pawl pin and spring, inserts, bushings, spine tube, rack, adhesive, every bolt and washer by ID).
   - **Assembly:** bonding procedure; assembly order, including the B-25 sleeves going onto the top bar before the crown corners are bonded; first-article checks.
2. **Gate print text:** fix the test-kit print instructions for every printed test piece (HE-FIT, PT-3, US route, clevis, IM3-EC), so the bag-cut gate can be run. Read BL-053's support data.
3. **Minors:** fix m-1..m-10 (kit sentence splits, stale op numbers, stale hinge numbers, fixture dowel, the US-route bench check, the belly-gauge tack spec, the G1 print list, strain-gauge temperature compensation, clevis-face contact, bed margin), or accept each with a reason.
4. **Meat haul text:** update `huntkit/gendesign/meat_haul.py` step 6. The belly guidance is now advice only, because BL-053 makes the frame safe down to a 40 mm belly.
5. **Finish:** regenerate the test kit and mfg package, then run the full suite. Don't edit huntkit/gendesign frame FEA files or the STLs (BL-053 owns them).
