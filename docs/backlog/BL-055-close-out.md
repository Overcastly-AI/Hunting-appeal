# BL-055 Close-out before review 6

## Part A (structural-fea-engineer)
1. **Whole body:** run `h1_buckling.full_check` / `h1_crown --body` on the BL-053 print body (strength, fatigue, buckling on every R1 basis, the joint at z 234). Also reflect the 0.2 mm sanding allowance on the stay wearer faces. Report the margins against R1.
2. **Hip boss:** define the insert pattern (count, pilot holes, positions, wall) and check it. `hipbelt_structural.md` books 2 inserts at SF 0.995; size for SF ≥ 1.5 / fatigue ≥ 1.15. Add the pilot holes to the print, re-export and slice-check.
3. **Pins:** Ti US1 pins (orchestrator call); update the pin rows and ledger.
4. **Cleanup:**
   - fix the `us_route.section_bearing` hull sign;
   - add superseded notes to h1_crown, h1_bedfit and h1_lanes pointing at h1_rev5;
   - fix `bag_attach.THROAT` (18 → 20) and the "pin sleeve" text.
5. **Full suite.** Don't edit physical_test_kit, mfg or `print/frame_h1/README.md` / BUILD_H1; publish JSON.

## Part B (manufacturing-engineer)
1. **Wire BL-053's data into the kit and register** (`h1_rev5.json`, `print_settings_bl053.json`):
   - CLEVIS-SHARE as two loadings, A and B (1104 / 643 N), with vectors and µε pass lines;
   - MT-1cr along the published 3D vectors, with a ≥ 50 kg quarter-shaped load and a photo of the contact line;
   - T1 gauge pass lines, with the second US1 gauge on the outer cheek;
   - a PIN-RET test;
   - a FIT-US lip and strap inspection;
   - CA-1 bars printed over supports;
   - a T6(c) register row.
2. **BUILD_H1 / README:** regenerate them from the Part A data when it lands (Ti US1 pins, hip insert pattern). Literal op numbers in the mfg text: read them from the op list.
3. **Finish:** regenerate the kit, mfg and the frame build package, then run the full suite.
