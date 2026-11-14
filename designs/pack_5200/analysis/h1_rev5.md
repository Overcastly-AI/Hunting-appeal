# H1 frame fixes from the fifth review (BL-053)

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-053-frame-review5.md`, findings `review_20261113_fifth.md` (B-1, M-1..M-6). Code `huntkit/gendesign/h1_rev5.py` (`python -m huntkit.gendesign.h1_rev5 --fea` then the report with no flag), `designs/pack_5200/us_route.py` (`cradle_3d`, `strap_wrap`), joint `h1_bedfit` (dz 7, `trap_solid`, `trap_walls`, `lip_round_cut`), print hook `frame_h1.print_mesh` -> `h1_rev5.add_fixes`; tests `tests/test_h1_rev5.py`. Results `h1_rev5.json`; print data for BL-054 `print/frame_h1/print_settings_bl053.json`. Units mm, N, MPa, g (imperial in brackets).

## Summary

- **M-1 cradle direction:** the cradle is now a 3D string (`us_route.cradle_3d`): legs from each pin to the quarter's lowest front edge, inboard to x 0 for a narrow load, outboard to the edge of the 280 mm R-08 quarter proxy for a wide one, contact 0 / 50 mm aft (95 mm as sensitivity), bellies 40-70 mm at the 53 kg float limit (V per strap US1 748.5 N, US2 499.0 N, factored 1.6 g x 1.5). The leg's pull along the pin is V x_lane / (2 belly): at 40 mm US2 **1029 N inboard** onto the INNER (body) cheek, US1 655 N. Checked on a submodel cut from the print itself (lower branch, hub, clevis, Ti bolts in; the stub model left the branch out) with the eye-edge-on-the-cheek rule that failed the hinge before BL-049.
- **The BL-051 print fails it:** at a 40 mm belly US1 strength 1.85 / fatigue 0.83 (the fairlead's merge into the lower branch), US2 1.58 / 0.71 (inner cheek root). At the old 60 mm minimum: US1 1.21, US2 1.05.
- **M-3 fix (applied, re-exported):** US1: the lug block and the lower branch under it filled to their convex hull (BL-049 proposal 2, the arm onto the branch) and the inner cheek grown to +/-12 with a buttress; US2: inner cheek grown to +/-14 with a buttress, root flared to +/-22 mm over 16 mm at the stay. Both buttresses leave a 12 mm slot about the pin axis for the pin tail and its clip. **On the new print, every design row down to a 40 mm belly: US1 strength 2.71 / fatigue 1.22, US2 3.33 / 1.5** (goal 1.5 / 1.15; contact 95 mm aft: US1 1.16, US2 1.15). The belly stops being a safety rule; the card can stay as advice (BL-054). **Mass +54.0 g print** (1.90 oz; fixes 56.05 g: US1 20.99 g, US2 7.15 g a side).
- **M-2 nut traps:** two-step trap as at z 234 (washer slot 10.4 x 1.2 mm, then an 8.2 AF hex slot that holds the nut by its flats), bolt axes moved to z pin +/- 7: walls 2.3 mm (>= 2). Joint on every row incl. the 3D cradle and the strap wrap: share 0.6 strength 4.23 / fatigue 1.9 (3D rows); share 1.0 2.54 / 1.14. The BL-051 lane rows (legs in the y-z plane, a direction the lane geometry cannot produce) still read 0.86 at share 1.0; they are kept for comparison only.
- **M-6 strap route:** each strap now laid over its own print (`us_route.strap_wrap`): US2 wraps the joint blocks' lower aft edge by up to 38.0 deg, 192.8 N on the lip (bag-on 296 N factored), now a 3 mm radius (3.95 MPa line pressure); US1 clears its own floor end once that is rounded r 3 (wrap 0.0 deg). The clevis share of the wrap is in the joint check (fatigue >= 10.69). Strap clearance to hinge / HE re-run on the new print: US1 12.4 / US2 14.6 mm (>= 10).
- **M-4 gauges:** model root stress (MPa) and microstrain with a placement band and a numeric pass line per gauge, load step and test (section 4); CLEVIS-SHARE raised to the governing 3D rows (A: inboard leg, proof 1103.9 N; B: the clevis's share-1.0 leg, proof 642.9 N).
- **M-5 pins:** one scheme on all 12 stations: headed pin (head outboard), R-clip in a 1.3 mm cross hole 2.5 mm past the far cheek, pin and clip on one Dyneema tether; hinge Ti 5 x 45.1, the others 7075 5 x 41.1; test PIN-RET. Mass +11.17 g against what the ledger books.
- **B-1 printability:** orientation kept (layer normal = frame y, wearer face down); tree supports from the plate in PAHT-CF, 3 interface layers, top gap 0.2-0.25 mm, blockers in every bore and trap. Lower half 477.6 g + 49.0 g support (high 94.3 g), about 18.6 h; upper 544.2 g + 55.3 g (high 102.7 g), about 21.2 h. Support scars land on fatigue-critical faces (the stays' wearer faces and the lug undersides): sand to <= 0.2 mm (2.2 % of the stay section modulus; body sim-basis fatigue 1.258 -> about 1.23) and add 2 XY bars printed over supports to CA-1 (SCAR-KD). Data for BL-054: `print/frame_h1/print_settings_bl053.json`.
- **Finish:** re-exported (assembled 1050.6 g, lower 479.7 g, upper 543.4 g, clevises 13.74 g each), every slice check passes, both halves still fit the H2S bed with the brim (lower spare [2.95, 4.42] mm). Ledger row BL053. The whole-body check was not re-run (ASSUMPTION BODY-NOT-RERUN).

## 1. The cradle as a 3D string (M-1)

In the plane through the two pins that touches the quarter's lowest front edge, a taut strap is two straight legs from each pin to that edge; a rounded or wide bottom only makes the legs steeper, so the straight V is the flattest (highest-tension) case for a given drop. Vertical equilibrium per strap: V = 2 T belly / |leg|. The lateral pull T dx / |leg| = V dx / (2 belly) does not depend on the contact's aft distance dy; dy adds only to the y-z part. Leg vector on the R pin (x + outboard, y + aft, z + up), tension factored as the 720 N row was (1.6 g x 1.5), from `us_route.cradle_3d`:

| strap | belly mm | legs | dy mm | vector N | tension N | below horizontal deg |
|---|---:|---|---:|---|---:|---:|
| us1 | 40 | in | 0 | [-655.0, 0.0, -374.3] | 754.4 | 29.7 |
| us1 | 40 | out | 0 | [655.0, 0.0, -374.3] | 754.4 | 29.7 |
| us1 | 40 | in | 50 | [-655.0, 467.8, -374.3] | 887.7 | 24.9 |
| us1 | 40 | out | 50 | [655.0, 467.8, -374.3] | 887.7 | 24.9 |
| us1 | 40 | in | 95 | [-655.0, 888.9, -374.3] | 1165.9 | 18.7 |
| us1 | 40 | out | 95 | [655.0, 888.9, -374.3] | 1165.9 | 18.7 |
| us1 | 60 | in | 0 | [-436.7, 0.0, -374.3] | 575.1 | 40.6 |
| us1 | 60 | out | 0 | [436.7, 0.0, -374.3] | 575.1 | 40.6 |
| us1 | 60 | in | 50 | [-436.7, 311.9, -374.3] | 654.2 | 34.9 |
| us1 | 60 | out | 50 | [436.7, 311.9, -374.3] | 654.2 | 34.9 |
| us1 | 60 | in | 95 | [-436.7, 592.6, -374.3] | 825.8 | 27.0 |
| us1 | 60 | out | 95 | [436.7, 592.6, -374.3] | 825.8 | 27.0 |
| us2 | 40 | in | 0 | [-1029.1, 0.0, -249.5] | 1058.9 | 13.6 |
| us2 | 40 | out | 0 | [0.0, 0.0, -249.5] | 249.5 | 90.0 |
| us2 | 40 | in | 50 | [-1029.1, 311.9, -249.5] | 1103.9 | 13.1 |
| us2 | 40 | out | 50 | [0.0, 311.9, -249.5] | 399.4 | 38.7 |
| us2 | 40 | in | 95 | [-1029.1, 592.5, -249.5] | 1213.4 | 11.9 |
| us2 | 40 | out | 95 | [0.0, 592.5, -249.5] | 642.9 | 22.8 |
| us2 | 60 | in | 0 | [-686.1, 0.0, -249.5] | 730.0 | 20.0 |
| us2 | 60 | out | 0 | [0.0, 0.0, -249.5] | 249.5 | 90.0 |
| us2 | 60 | in | 50 | [-686.1, 207.9, -249.5] | 759.1 | 19.2 |
| us2 | 60 | out | 50 | [0.0, 207.9, -249.5] | 324.8 | 50.2 |
| us2 | 60 | in | 95 | [-686.1, 395.0, -249.5] | 830.1 | 17.5 |
| us2 | 60 | out | 95 | [0.0, 395.0, -249.5] | 467.2 | 32.3 |

'in' = a narrow load the strap meets at x 0 (legs inboard); 'out' = the 280 mm quarter, wider than the US1 span (legs outboard to its edge at x 140) and as wide as US2's edge (legs straight down there). MT-1cr must pull along these vectors (section 4), not along the BL-051 y-z leg.

## 2. Lugs on the print, before and after (M-1, M-3)

Submodel (`sub_fea`): the print sliced into 1 mm voxels inside a box (US1 x -6..140, y -56..32, z 46..146, the lumbar hub and the lower branch in; US2 x 80..192, y -50..40, z 90..196, the clevis in), solid cut by the box fixed, the US2 joint face a 1-voxel gap except the Ti bolts (E 110 GPa); the pin's y-z force as bearing on the hole band of both cheeks, its x force as the eye's edge on the inner face of the cheek it moves towards; FI99 per region (fairlead, root, arm, US1 web, the BL-053 additions), layer normal frame y; elements within 5 mm of the box and the US2 joint's own bearing zone (checked by `joint_check`) left out of the statistics. Box sensitivity (US1): a box ending at x 34 read the BL-051 US1 at 0.63 instead of 0.54, so the large box is kept.

| lug | print | belly | strength (min) | fatigue | governing row | region | peak (frame) |
|---|---|---:|---:|---:|---|---|---|
| us1 | BL-051 | 40 | 1.85 | 0.83 | c3d|b40|dy50|out (887.7 N) | web | [69.5, -14.5, 93.5] |
| us1 | BL-051 | 50 | 2.27 | 1.02 | c3d|b50|dy50|out (744.8 N) | web | [69.5, -14.5, 94.5] |
| us1 | BL-051 | 60 | 2.69 | 1.21 | c3d|b60|dy50|out (654.3 N) | web | [69.5, -14.5, 94.5] |
| us1 | BL-051 | 70 | 3.07 | 1.38 | c3d|b70|dy50|out (593.0 N) | web | [69.5, -14.5, 94.5] |
| us1 | BL-051 | 40, dy 95 (sens.) | 1.21 | 0.54 | c3d|b40|dy95|out | web | [69.5, -14.5, 93.5] |
| us1 | BL-051 | bag-on (3.0) | 3.13 | 1.76 | bagon_drape|fleet_in | web | [69.5, -14.5, 93.5] |
| us1 | BL-053 | 40 | 2.71 | 1.22 | c3d|b40|dy50|out (887.7 N) | fairlead | [80.5, 11.5, 103.5] |
| us1 | BL-053 | 50 | 3.36 | 1.51 | c3d|b50|dy50|out (744.8 N) | fairlead | [80.5, 11.5, 103.5] |
| us1 | BL-053 | 60 | 4.0 | 1.8 | c3d|b60|dy0|out (575.2 N) | fairlead | [80.5, 11.5, 103.5] |
| us1 | BL-053 | 70 | 4.51 | 2.03 | c3d|b70|dy50|out (593.0 N) | fairlead | [80.5, 11.5, 103.5] |
| us1 | BL-053 | 40, dy 95 (sens.) | 2.59 | 1.16 | c3d|b40|dy95|out | fairlead | [80.5, 11.5, 103.5] |
| us1 | BL-053 | bag-on (3.0) | 4.62 | 2.6 | bagon_fore30|fleet_out | root | [102.5, 2.5, 87.5] |
| us2 | BL-051 | 40 | 1.58 | 0.71 | c3d|b40|dy50|in (1103.9 N) | fairlead | [154.5, 9.5, 150.5] |
| us2 | BL-051 | 50 | 1.96 | 0.88 | c3d|b50|dy50|in (895.7 N) | fairlead | [147.5, 9.5, 133.5] |
| us2 | BL-051 | 60 | 2.33 | 1.05 | c3d|b60|dy50|in (759.1 N) | fairlead | [147.5, 9.5, 133.5] |
| us2 | BL-051 | 70 | 2.74 | 1.23 | c3d|b70|dy0|in (638.8 N) | fairlead | [147.5, 9.5, 133.5] |
| us2 | BL-051 | 40, dy 95 (sens.) | 1.56 | 0.7 | c3d|b40|dy95|in | fairlead | [154.5, 9.5, 150.5] |
| us2 | BL-051 | bag-on (3.0) | 7.9 | 4.44 | bagon_drape|fleet_out | root | [128.5, 6.5, 155.5] |
| us2 | BL-053 | 40 | 3.33 | 1.5 | c3d|b40|dy50|in (1103.9 N) | root | [126.5, 4.5, 122.5] |
| us2 | BL-053 | 50 | 4.17 | 1.88 | c3d|b50|dy50|in (895.7 N) | root | [126.5, 4.5, 122.5] |
| us2 | BL-053 | 60 | 4.9 | 2.2 | c3d|b60|dy50|in (759.1 N) | root | [126.5, 4.5, 122.5] |
| us2 | BL-053 | 70 | 5.58 | 2.51 | c3d|b70|dy50|in (663.2 N) | root | [126.5, 4.5, 122.5] |
| us2 | BL-053 | 40, dy 95 (sens.) | 2.55 | 1.15 | c3d|b40|dy95|in | root | [129.5, 6.5, 153.5] |
| us2 | BL-053 | bag-on (3.0) | 8.89 | 5.0 | bagon_drape|fleet_out | root | [128.5, 6.5, 155.5] |

Requirement (ticket): strength >= 1.5, fatigue >= 1.15 (1e5 x 1.6 g on the factored row / 2.4) down to a 40 mm belly. **Met on the BL-053 print for every design row; the dy 95 sensitivity sits at 1.15-1.16.** The fixes, in `h1_rev5` (US1_HULL, US1_BUTTRESS, US2_BUTTRESS, US2_FLARE, SLOT_HALF), are unioned onto the print by `add_fixes` and the FEA above runs on the exported STL with nothing added. Why each: US1's aft and outboard pull bent the fairlead block against the small merge with the lower branch (peak at the merge, x 70, y -14.5); filling the gap to the hull turns the block and the branch into one section and the column fill alone (tried) only moved the notch. The inner cheeks carry the inboard pull out of plane at their floor corner (same mechanism as the hinge): growing them in z and propping their inboard face takes that corner down. US2's root then governed at the stay; the flare (outboard of the stay surface, clear of the spreader sheet edge at x 121) lifts it.

Fairlead pins at the new rows (y-z part bends the pin; the x part goes to the cheek through the eye): see section 5.

## 3. US2 clevis joint and the strap wrap (M-2, M-6)

Trap (`h1_bedfit.trap_solid`, as the z 234 joint): washer slot 10.4 mm wide over |x| 149.8-151 (washer 1 mm + 0.2), then an 8.2 AF hex slot (nut 8 AF, corners 9.24: it cannot turn) over |x| 145.8-149.8, both open to the wearer face for the nut to slide in. Bolt axes at z pin +/- 7: walls washer slot 2.3 mm, hex slot 3.4 mm, between the traps 3.6 mm (rule >= 2: True). Slice check of the new STL (`joint_slices`): True.

| share | family | worst row | force on clevis N | strength | fatigue | check |
|---:|---|---|---|---:|---:|---|
| 0.6 | c3d | c3d|b40|dy95|in | [0.0, 355.5, -149.7] | 4.23 | 1.9 | net_section / net_section_paht |
| 0.6 | bagon_down | bagon_down | [0.0, 0.0, -177.8] | 7.89 | 4.44 | hole_bearing / hole_paht |
| 0.6 | bagon_fore30 | bagon_fore30|fleet_out | [51.5, -87.5, -151.6] | 6.53 | 3.68 | washer_bearing / washer_paht |
| 0.6 | bagon_drape | bagon_drape|fleet_out | [51.5, -174.9, -8.6] | 6.1 | 3.43 | washer_bearing / washer_paht |
| 0.6 | cradle_lane | cradle_lane | [0.0, 352.8, -149.7] | 4.25 | 1.91 | net_section / net_section_paht |
| 0.6 | cradle_lane_b50 | cradle_lane_b50 | [0.0, 493.9, -149.7] | 3.17 | 1.43 | net_section / net_section_paht |
| 0.6 | wrap | wrap|15 | [0.0, -52.6, 98.7] | 19.01 | 10.69 | net_section / net_section_paht |
| 1 | c3d | c3d|b40|dy95|in | [0.0, 592.5, -249.5] | 2.54 | 1.14 | net_section / net_section_paht |
| 1 | bagon_down | bagon_down | [0.0, 0.0, -296.3] | 4.74 | 2.66 | hole_bearing / hole_paht |
| 1 | bagon_fore30 | bagon_fore30|fleet_out | [51.5, -145.9, -252.7] | 4.55 | 2.56 | washer_bearing / washer_paht |
| 1 | bagon_drape | bagon_drape|fleet_out | [51.5, -291.4, -14.3] | 4.21 | 2.37 | washer_bearing / washer_paht |
| 1 | cradle_lane | cradle_lane | [0.0, 588.1, -249.5] | 2.55 | 1.15 | net_section / net_section_paht |
| 1 | cradle_lane_b50 | cradle_lane_b50 | [0.0, 823.2, -249.5] | 1.9 | 0.86 | net_section / net_section_paht |
| 1 | wrap | wrap|15 | [0.0, -52.6, 98.7] | 19.01 | 10.69 | net_section / net_section_paht |

'c3d' = every 3D cradle row incl. dy 95 (the worst is the y-z 'out' leg, the clevis's own case); 'cradle_lane*' = the BL-051 y-z rows, kept for comparison (no lane geometry produces them). 'wrap' = the strap's bearing on the block lip, clevis share of the 25 mm strap outboard of the joint face, applied at the lip.

Strap wrap (`us_route.strap_wrap`, R side, bag-on cam-tight, the recorded 'now' meat drapes):

| torso | strap | wrap deg | bearing N (y, z) | on the print at (y, z) | lip r mm |
|---:|---|---:|---|---|---:|
| 15 | us1 | 0.0 | 0.0 [0.0, 0.0] | [] | 3.0 |
| 15 | us2 | 38.0 | 192.8 [-90.7, 170.2] | [[8.36, 127.5]] | 3.0 |
| 19 | us1 | 0.0 | 0.0 [0.0, 0.0] | [] | 3.0 |
| 19 | us2 | 26.1 | 133.8 [-74.8, 110.9] | [[8.36, 127.5]] | 3.0 |
| 23 | us1 | 0.0 | 0.0 [0.0, 0.0] | [] | 3.0 |
| 23 | us2 | 13.6 | 70.3 [-45.4, 53.6] | [[8.36, 127.5]] | 3.0 |

On the BL-051 print the same model gives US2 up to 38 deg / 193 N on the sharp (r 1.5) block edge and US1 3.9 deg / 30 N on its floor end. The lip is a wear point: FIT-US must inspect strap and lip for fuzz or whitening after the crank cycles (BL-054 kit text).

## 4. Gauge pass values (M-4)

Gauge sites (R side, bag face, gauge axis along the arm, centre 3 mm off the stay surface): US1 at [102.81, 8.06, 98.0], US2 at [126.96, 6.81, 142.0]. Model sigma_xx on the BL-053 print; band = min / max within +/- 1.5 mm of the site; E_xy 3860 MPa. **Pass if the measured |microstrain| is at most the pass line** (band extreme x 1.15). Pull along the unit vector given (frame, R pin; mirror x for L).

| test | gauge | pull unit vector | pin load N | sigma MPa | band MPa | microstrain | pass if abs <= |
|---|---|---|---:|---:|---|---:|---:|
| MT-1cr  | us1 | [0.7379, 0.527, -0.4217] | 240.0 | -0.92 | [-1.03, -0.71] | -238 | 306 |
| MT-1cr  | us1 | [0.7379, 0.527, -0.4217] | 480.0 | -1.84 | [-2.05, -1.42] | -477 | 612 |
| MT-1cr  | us1 | [0.7379, 0.527, -0.4217] | 720.0 | -2.76 | [-3.08, -2.13] | -715 | 918 |
| MT-1cr  | us1 | [0.7379, 0.527, -0.4217] | 887.7 | -3.4 | [-3.8, -2.63] | -882 | 1132 |
| T1  | us1 | [0.0, -0.9641, 0.2655] | 0.0 | -0.0 | [-0.0, 0.0] | -0 | 0 |
| T1  | us1 | [0.0, -0.9641, 0.2655] | 148.1 | -0.03 | [-0.09, 0.05] | -7 | 27 |
| T1  | us1 | [0.0, -0.9641, 0.2655] | 296.3 | -0.06 | [-0.18, 0.1] | -15 | 53 |
| MT-1cr  | us2 | [-0.9322, 0.2825, -0.226] | 240.0 | -2.7 | [-3.04, -1.73] | -698 | 904 |
| MT-1cr  | us2 | [-0.9322, 0.2825, -0.226] | 480.0 | -5.39 | [-6.07, -3.45] | -1397 | 1808 |
| MT-1cr  | us2 | [-0.9322, 0.2825, -0.226] | 720.0 | -8.09 | [-9.11, -5.18] | -2095 | 2713 |
| MT-1cr  | us2 | [-0.9322, 0.2825, -0.226] | 1103.9 | -12.4 | [-13.96, -7.94] | -3212 | 4159 |
| T1  | us2 | [0.0, -0.9988, -0.0491] | 0.0 | 0.0 | [0.0, 0.0] | 0 | 0 |
| T1  | us2 | [0.0, -0.9988, -0.0491] | 98.8 | 1.34 | [0.81, 1.54] | 347 | 459 |
| T1  | us2 | [0.0, -0.9988, -0.0491] | 197.5 | 2.68 | [1.62, 3.08] | 694 | 917 |
| CLEVIS-SHARE us2_inboard | us2 | [-0.9322, 0.2825, -0.226] | 1103.9 | -12.4 | [-13.96, -7.94] | -3212 | 4159 |
| CLEVIS-SHARE us2_inboard | us2 | [-0.9322, 0.2825, -0.226] | 735.9 | -8.27 | [-9.31, -5.29] | -2141 | 2773 |
| CLEVIS-SHARE us2_yz | us2 | [0.0, 0.9216, -0.3881] | 642.9 | -7.92 | [-9.0, -4.82] | -2052 | 2681 |
| CLEVIS-SHARE us2_yz | us2 | [0.0, 0.9216, -0.3881] | 428.6 | -5.28 | [-6.0, -3.21] | -1368 | 1787 |

MT-1cr: pull each pin along its governing 3D leg (US1: outboard, aft, down, the wide quarter; US2: inboard, aft, down) at 240 / 480 / 720 N and the factored row. CLEVIS-SHARE A: the inboard leg, the eye on the INNER (body) cheek with the PTFE shim there, proof at the factored row, 1e5 cycles at x 1.6 / 2.4 (R 0.1). CLEVIS-SHARE B: the y-z leg with the eye on the OUTER (clevis) cheek (the share-1.0 case). The US1 arm-root gauge now reads little (the BL-053 block carries the pin load into the branch; < 4 MPa at the factored row): keep it as a check that the block works, and if a second gauge is fitted put it on the US1 outer cheek's outboard face at its floor (the governing spot, x 80-88, z 98-104). T1 values are local only (GAUGE-LOCAL).

## 5. Pin retention (M-5)

Scheme: headed pin, R-clip through a cross hole on the far side, pin + clip on one tether. Retainer: hitch-pin (R-) clip, 302 / 18-8 stainless, 1.2 mm wire, for 4.8-6.4 mm (3/16-1/4 in) pins; source https://www.mcmaster.com/products/hitch-pin-clips/ (secondary: catalogue page not fetched; any 18-8 R-clip in that size range); tether: 1.5 mm Dyneema (UHMWPE) cord, 120 mm, through the pin head's 1.6 mm hole and the clip's eye, larks-head round the stay beside the fairlead: pin and clip stay on the frame when pulled. Clip wire double shear 699 N (ASSUMPTION CLIP-UTS (ASTM A240 304 minimum 515 MPa)); the eye's pull along the pin bears on the cheek, not the pin, so the clip only stops a pin that walks. An R-clip is spring-held round the pin (it does not unscrew or back out in vibration); PIN-RET (b) checks it after the walk and the cycle tests.

| station | material | shank mm (span + tail) | head | clip side | pin g | set g (pin + clip + tether) | out at bag-off | pin bending yield / fatigue |
|---|---|---:|---|---|---:|---:|---|---|
| hinge (x2) | ti_6al_4v | 45.1 | 8 x 1.5 | inboard | 4.26 | 5.06 | True | 1.99 / 2.24 |
| us1 (x2) | alu_7075_t6 | 41.1 | 8 x 1.5 | inboard (towards x 0; the buttress leaves a 12 mm slot) | 2.48 | 3.28 | False | 2.1 / 1.56 (dy 95: 1.31 / 0.97) |
| us2 (x2) | alu_7075_t6 | 41.1 | 8 x 1.5 | inboard (towards x 0; the buttress leaves a 12 mm slot) | 2.48 | 3.28 | False | 3.15 / 2.34 (dy 95: 1.96 / 1.46) |
| im1 (x2) | alu_7075_t6 | 41.1 | 8 x 1.5 | inboard | 2.48 | 3.28 | False | - / - |
| im2 (x2) | alu_7075_t6 | 41.1 | 8 x 1.5 | inboard | 2.48 | 3.28 | False | - / - |
| im3 (x2) | alu_7075_t6 | 41.1 | 8 x 1.5 | inboard | 2.48 | 3.28 | False | - / - |

The US1 7075 pin reads 0.97 in fatigue only on the dy 95 sensitivity row; a Ti pin there (+1.0 g each) would clear it (owner option, not applied). Test PIN-RET:

- (a) every pin in, clip seated: a 50 N push on the pin's tail along its axis (spring scale) moves it < 0.5 mm
- (b) after the T9 walk and the MT-1cr / CLEVIS-SHARE cycles: every pin home, every clip fully seated, no wire wear groove deeper than 0.1 mm
- (c) bag-off: each hinge pin out and back in by hand, gloved, clip off and on, <= 8 s each

## 6. Printability (B-1)

Each part voxelised (1 mm) in its print orientation; a voxel needs support when nothing of the layer below lies within one voxel sideways (45 deg). Plate contact, supported down area by region, support column to the plate or the part below (`support_map`).

| file (as exported) | plate contact mm2 | supported mm2 (stay / lug / other) | part g | support g (est / high) | print h (est) |
|---|---:|---|---:|---|---:|
| h1_lower_flat.stl | 739 | 11136 (2224 / 6946 / 1966) | 477.6 | 49.0 / 94.3 | 18.6 |
| h1_upper_flat.stl | 223 | 18044 (8755 / 3030 / 6259) | 544.2 | 55.3 / 102.7 | 21.2 |
| us2_clevis_R.stl / us2_clevis_L.stl | 580 | 74 (0 / 0 / 74) | 13.8 | 0.1 / 0.2 | 0.5 |
| test_pieces/us_route_stay_R.stl | 9 | 3684 (168 / 2669 / 286) | 164.8 | 13.0 / 24.6 | 6.3 |
| test_pieces/hefit_hinge_fairlead_R.stl | 15 | 864 (218 / 646 / 0) | 43.1 | 1.6 / 2.8 | 1.6 |
| test_pieces/im3ec_cheek_R.stl | 729 | 886 (495 / 375 / 16) | 68.8 | 1.8 / 3.2 | 2.5 |

Flipped (bag face down) for comparison: lower supported 13829 mm2 (stay 2497), upper 19915 mm2 (stay 8503): no less support, and the scars move to the stays' bag faces and the fairlead tips (eye bearing, HE fit). **Chosen: as exported, wearer face down, for every file**, test pieces included (they must carry the frame's surfaces). Settings: tree supports from the build plate only ('on build plate only'), auto, threshold 45 deg; PAHT-CF itself (single nozzle H2S), no breakaway material; top Z [0.2, 0.25] mm; 3 interface layers; blockers: every pin hole and fairlead throat (12 stations); both z 234 joint bores, counterbores and nut traps; the two US2 clevis bolt holes, counterbores and hex nut traps (body side); the 18 mm stay sleeve bores; the pawl bore and the spine channel.

**Scars on fatigue-critical faces: yes.** support contact lands on wearer-facing (-y) surfaces only: the stays' wearer faces (2224 + 8755 mm2) and the undersides of the lugs, fairlead roots and lane blocks; the lugs' governing spots (US1 outer cheek / floor corner, US2 arm root bag face, hinge inboard cheek corner) face up or sideways and carry no scar. Finish: sand the support witness on the stays' wearer faces and the lug undersides flat with 240 then 400 grit, removing at most 0.2 mm (SAND-ALLOW); deburr every bore edge. 0.2 mm off one face of an 18 mm deep stay (ASSUMPTION: rectangular-equivalent) costs about 2.2 % of its bending section modulus; the body's fatigue minimum on the sim bases (1.258, h1_crown) becomes about 1.23. CA-1 gets 2 XY bars printed over tree supports and sanded the same way (SCAR-KD).

## 7. Checks on the re-exported print

- `h1_lanes.slice_checks`: fairleads True, spine channel True, pawl True, test pieces True.
- `h1_bedfit.joint_slices` (US2 holes, traps open to the wearer face, joint face closed): True.
- `h1_crown.crown_continuity`: True.
- Bed (H2S 340 x 320, 8 mm brim): lower [321.05, 299.58, 76.7] spare [2.95, 4.42]; upper [309.39, 280.12, 64.38] spare [14.61, 23.88].
- Strap clearance to hinge / HE / other US on the 12 drape rows (`us_route.run_layout('now')`): US1 12.4 / US2 14.6 mm (>= 10: True).
- Every file a closed single shell (`h1_buckling.export_print` asserts it).

## 8. Mass

| item | g | oz |
|---|---:|---:|
| print, assembled BL-053 1050.6 - BL-051 996.6 | +54.0 | +1.90 |
| of which lug fixes us1_L | 20.93 | 0.74 |
| of which lug fixes us1_R | 20.99 | 0.74 |
| of which lug fixes us2_L | 6.99 | 0.25 |
| of which lug fixes us2_R | 7.15 | 0.25 |
| pin retention: 12 pins as now specified 33.32 + 12 clips and tethers 9.6 - pins booked 31.75 | +11.17 | +0.39 |

Ledger row BL053 (`huntkit/mass/ledger.py`, from this json; H1 configs). Printed body now lower 479.7 g, upper 543.4 g, clevises 13.74 g each.

**Mass reductions that keep the SF (not applied):** (1) US1 block: it is the full convex hull of the lug block and the branch (about 15 g a side of the 21 g); a web only under the fairlead floor, pocketed in z, is the obvious trim, but the column-fill variant that tried it moved the notch to the branch (fatigue 0.56), so any trim needs a smooth fillet and a re-run (`lug_check` with `extra`); (2) US2 has 0.35 of fatigue margin at the design rows (1.50) but the dy 95 sensitivity sits at 1.15: the flare is the only removable item, worth about 1 g; (3) 7075 pins for the hinge are not possible (BL-049).

## 9. Assumptions

- ASSUMPTION QUARTER-CONTACT: The under-strap meets the quarter 0-50 mm aft of the pin line (taut strap on the front edge against the spreader; a rounder bottom further aft): the design rows. 95 mm (half the quarter proxy's 190 mm depth) is run as a sensitivity. Settled by: MT-1cr with a >= 50 kg quarter-shaped load: photograph the strap contact line from the side and measure its distance aft of the pin line.
- ASSUMPTION QUARTER-WIDTH: The load in the cradle is the 280 mm wide R-08 quarter proxy (huntkit/viz3d/params.py): US1's legs run outboard to its edges, US2's straight down at its edge; a narrow load takes both legs inboard to x 0. Settled by: MT-1cr: legs' lateral direction at each pin, narrow (boned bag) and wide (bone-in) loads.
- ASSUMPTION BELLY-40: The cradle is designed down to a 40 mm belly at the 53 kg float limit; flatter is not credited. A hand can reach it (5th-percentile male one-arm pull 178-199 N, FAA HFDS Ch. 14 Exh. 14.5.2.1; a strong user, both hands or a braced foot pull more), so no strength cap on the hand is used. Settled by: MT-1cr: cam each strap as hard as a strong user can, gloved, with the 53 kg load: belly measured >= 40 mm.
- ASSUMPTION SUB-BC: The print submodel is fixed where its box cuts the frame (US1: x -6..140 incl. the lumbar hub; US2: x 80..192); the smaller boxes gave LESS severe US1 numbers (sensitivity in the record). Settled by: Strain gauges at the arm roots in MT-1cr (gauge table): measured <= the pass line.
- ASSUMPTION CLEVIS-SHARE: Outer cheek's share of the pin's y-z load 0.6 (1.0 as sensitivity); the inboard leg's x pull bears on the INNER (body) cheek and loads no clevis bolt. Settled by: CLEVIS-SHARE A and B (gauge table).
- ASSUMPTION GAUGE-LOCAL: T1 gauge values carry only the local bag-on pin load (the submodel has no global stay stress); the T1 pass line is advisory, MT-1cr and CLEVIS-SHARE (pin loads only) are the gates. Settled by: Record T1 anyway; compare with the whole-body model when it is re-run on the BL-053 body.
- ASSUMPTION TREE-FILL: Tree supports use 12 % of the column volume they span (+ 3 dense 0.2 mm interface layers); high estimate 25 %. Settled by: Bambu Studio plate preview of each file with the README's support settings: filament and time.
- ASSUMPTION SAND-ALLOW: Sanding the support witness off the stays' wearer faces removes <= 0.2 mm (about 2.2 % of the stay's bending section modulus). Settled by: Caliper the stay depth at 5 points before / after sanding on the first article.
- ASSUMPTION SCAR-KD: Support witness sanded flat costs no more fatigue strength than the 2.2 % section loss. Settled by: CA-1: add 2 XY bars printed over tree supports and sanded as the README says, against 2 printed flat.
- ASSUMPTION WRAP-TENSION: The strap's wrap over its own lug carries the bag-on cam-tight tension (US1 444 N, US2 296 N, factored 3.0) on the recorded meat drapes; the eye is necked to 18 mm in the throat. Settled by: FIT-US: inspect the lip and strap for fuzz or whitening after the crank cycles.
- ASSUMPTION CLIP-MASS: R-clip 0.6 g, tether 0.2 g each. Settled by: Weigh one set.
- ASSUMPTION BODY-NOT-RERUN: The whole-body check (h1_buckling.full_check) was not re-run on the BL-053 body: the fixes are local lug blocks (+56 g) away from the governing body regions (lumbar struts, stay L lower sleeve z 160-240). Settled by: Re-run h1_crown --body on the BL-053 print body (heavy job, about an hour) before P1.
- ASSUMPTION Carried: CLEVIS-DRY, CLEVIS-PRINT, HEAD-BEAR, CLEVIS-FACE (h1_crown.md / h1_bedfit.md); US-FLEET, DRAPE-US (us_route.json); FI99-RULE (h1_lanes.md).

## 10. Owner decisions

- Accept +54.0 g of print (US1 block and buttresses, US2 buttress and flare) for a cradle that needs no minimum belly. The alternative, keeping the BL-051 print and the 60 mm belly rule, does not hold on the 3D model either (BL-051 print at 60 mm: US1 1.21, US2 1.05, goal 1.15) and the belly cannot be held by feel.
- Accept sanded support scars on the stays' wearer faces (about 2 % section) pending CA-1's over-support bars.
- US1 pins in Ti for the dy 95 sensitivity (+2 g), or keep 7075.

## 11. Screenshots

- `outputs/screens/20261113_BL053_1.png`
- `outputs/screens/20261113_BL053_2.png`
- `outputs/screens/20261113_BL053_3.png`
- `outputs/screens/20261113_BL053_4.png`
