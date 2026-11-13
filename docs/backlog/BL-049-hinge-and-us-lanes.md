# BL-049 Hinge fairlead fatigue (inboard-up) and US station lanes

**Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-047, BL-048

1. **Hinge fairlead:** the sims give the hinge eye force inboard and up in every case (`analysis/hinge_eye_vectors.json`, worst unit vector (0.917, 0.034, 0.397)). The hinge fairlead's fatigue is 0.86 in that direction at the 1019 N row. Grow or reshape it to fatigue ≥ 1.15 (BL-021 scatter goal; ≥ 1.0 minimum) in the sim direction, keeping the rev C direction passing. Make 1019 N the single hinge-pin check load (yield and fatigue at 2.4 g), and size the pin.
2. **US lanes:** move US1 to an inboard lug at x ±70 and US2 to an outboard lug at x ±165 (`analysis/us_route.json`, station_move). Design the lugs, check their strength and fatigue under the US loads (bag-on 444 / 296 N and the bag-off cradle), and keep the eye envelope (`imus_eye_envelope`). Re-check body strength, fatigue and buckling.
3. **Print:** re-export the print files. The slice checks must pass for the fairleads, channel and pawl. Re-cut the `us_route_stay_R` test piece on the moved stations, put it in `print/frame_h1/test_pieces/`, and re-run `designs/pack_5200/us_route.py` against the new STL. ≥ 10 mm clearance is required.
4. **Smaller items:**
   - `crown_spine_clamp.B25_T`: read it from the webbing record (1.5 mm).
   - Fix the roll-up frame-system mismatch of 6.7 g (1220.2 vs 1213.5 at M).
   - Ledger.
   - Full suite.

   Screenshots prefix `20261113_BL049_`.

Don't edit the bag pattern, mfg or corrie_f files. Publish the new station x/z as constants for BL-050.
