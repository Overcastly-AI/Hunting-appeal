# BL-050 Print-bed fit for the US2 lanes, then the bag on the lanes

## Part A (structural-fea-engineer)
1. **Bed fit:** find the largest US2 x at which the lower half fits the H2S bed (340 × 320 mm, with an 8 mm brim and the best rotation). Move US2 there, re-run `designs/pack_5200/us_route.py` on the new STL, and check its lug.
   - If the strap clears ≥ 10 mm at every torso and side, take it.
   - If not, design (a) bolt-on US2 lugs: the joint, the check and the print pieces.
   - Either way, the strict xfail `test_print_halves_fit_the_h2s_bed` must pass.
2. **Lug arms:** try I-section arms (about −15 g) if every margin holds.
3. **Spreader:** fix the US2 notch clearance (about 0 mm to the arm root).
4. **Ledger:** fix the pin count (12 stations).
5. **Output:** publish the final station constants, re-export the print, run the slice checks and run the full suite.

## Part B (pack-designer, after A)
1. Move the B-16 channel ends to the final US x positions, re-run the bag-off cradle (`meat_haul`) on the new span, and set the US2 cut (BL-048 says about 925 mm on lanes).
2. Point the test kit at `print/frame_h1/test_pieces/us_route_stay_R`.
3. Regenerate the patterns, mfg and the kit on HINGE_EYE_ENVELOPE (gap 6.5) and the B-25 runtime change.
4. Clear any stale 0.86 hinge records.
5. Run the full suite. The release stays NOT ready; review 5 follows.
