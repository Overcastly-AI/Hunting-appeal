# BL-051 Stay crown section loss at the US2 root, plus record cleanup

**Agent:** structural-fea-engineer · **Size:** S · **Beside:** BL-050B

1. **Stay crown:** over z 133–152 the stay's bag-face crown sits 3–4 mm lower than on either side (top y 7.7 against 10–11.8). The likely cause is `strip_old_us` removing crown material along with the old stub. Find it, restore the crown, re-export the print, and re-run:
   - the slice checks;
   - the US2 lug and joint;
   - the body strength, fatigue and buckling;
   - `us_route`.

   Add a test that the stay crown height is continuous.
2. **US1 root:** fatigue is 0.80 on the stub model and 1.14 on the whole body. State plainly which governs and why, and make sure the strain-gauge test at T1 is in the kit text (list the kit text change for BL-050B if you can't edit it).
3. **Cleanup:**
   - fix `bag_attach._mass_budget` n_pin at the source (12 stations);
   - add a superseded note to h1_lanes.md / .json pointing at h1_bedfit;
   - check the BOM mix-up risk (10 mm vs 12 mm washers, M5×40 vs M5×45): give the parts distinct BOM lines and README callouts.
4. **Full suite.**

Don't edit the bag pattern, mfg, corrie_f or physical_test_kit files.
