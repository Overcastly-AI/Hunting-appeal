# H1 hinge for the inboard-up pull, and the US stations on lane lugs (BL-049)

> **SUPERSEDED (2026-11-13) for the print, the bed fit and the US2 lug: see `h1_bedfit.md` (BL-050 A: bolt-on US2 outer clevis, the halves fit the H2S bed) and `h1_crown.md` (BL-051: the stay crown that `strip_old_us` cut away over the old US1 / US2 stub sites is restored; lug FEA on the real stay section; body re-checked).** The hinge fairlead, hinge pin and lane positions below still stand. Print masses, bed footprints, slice checks and the body numbers in this file are the BL-049 print (lower half 367.5 mm wide, crown cut): do not build from them.

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-049-hinge-and-us-lanes.md`. Code `huntkit/gendesign/h1_lanes.py` (`python -m huntkit.gendesign.h1_lanes --fea | --body | --export`), geometry `bag_attach.HINGE_GEOM` (BL-049) and `h1_fairleads.placed` (lanes), print `frame_h1.print_mesh`; tests `tests/test_h1_lanes.py`. Results `h1_lanes.json`. Units mm, N, g (imperial in brackets).

## Summary

- **Hinge fairlead: fatigue in the sims' inboard-up direction 0.62 -> 1.30 at the 1019 N row** (goal 1.15, worst row 23 fill L, unit (0.917, 0.034, 0.397)); 0.75 mm voxels 1.27. Strength 2.30, creep 2.77; on the pin's 2.4 g basis 1.04. Rev C direction: strength 6.22, fatigue 3.50. The ticket's 0.86 (BL-047) left out BL-047's own relief groove: the print as it was reads **0.62** (no groove 0.81).
- **What changed:** cheeks 8 -> **10 mm**, reaching **27 mm up the stay** above the pin (was 9; below the pin unchanged at 9, so the HE box keeps its 5 mm); throat floor lowered 1 mm over the whole throat (2.1 -> 1.1 mm above the stay; gap under the pin 5.5 -> **6.5 mm**) in place of BL-047's relief groove, which sat at the hot corner. Pin centre, throat (20) and tip unchanged.
- **Hinge pin: one check load, 1019 N.** 5 mm 7075-T6 fails it (yield 1.11, fatigue 0.83 on the 2.4 g basis; BL-042 span 0.92). **5 mm Ti-6Al-4V, 44 mm long: yield 1.99, fatigue 2.24** (3.0 basis 2.80), 3.8 g a pin. The eye, sleeve and hole stay 5 / 7.2.
- **US lanes on lugs:** US1 at x +/-70, z 95 (inboard), US2 at x +/-165, z 142 (outboard), each fairlead (BL-045 eye geometry, `imus_eye_envelope` unchanged) on a tapered printed arm from the stay. Lug FEA (stub model, conservative): US1 strength 1.78, fatigue 0.80; US2 2.31 / 1.04 (governing: the bag-off cradle at the arm-stay junction). Bag-on (444 / 296 N) passes with margin.
- **Print re-exported**, slice checks pass (12 / 12 fairleads with eye stacks, spine channel, pawl swing). **But the lower half is now 368 mm wide and does not fit the H2S bed** (best rotation 343 x 323 mm against 340 x 320, before the 8 mm brim). See owner decisions.
- **Mass:** printed body 886.2 -> **974.2 g (+88.0 g, +3.10 oz)**: lug arms +71.2 g, the rest (hinge growth, lane fairleads, old US stubs out) +16.8 g; Ti hinge pins +2.83 g. Ledger rows BL049.

## 1. Hinge: what the sims pull, and where it bites

The 12 rev 3 fine sim rows (`hinge_eye_vectors.json`) all pull the frame's hinge pin inboard (0.47-0.92 of the force) and up. The sideways part is carried by the eye's edge on the inboard cheek's inner face (`fairlead_fea` rule), so the critical spot is the corner where that cheek meets the throat floor (peak at x -9.5..-10.5 from the throat centre, 1 mm above the floor). BL-047's m-1 relief groove (1 mm deep, 1.5 mm wide, along each cheek) was cut exactly there.

| hinge (1 mm voxels, unit directions scaled to 1019 N) | sim worst row | strength | fatigue | fatigue 2.4 g basis | creep | hottest voxel fatigue | rev C strength / fatigue |
|---|---|---:|---:|---:|---:|---:|---|
| BL-047 print (BL-042 hinge + groove) | 23 fill L | 1.10 | 0.62 | 0.50 | 1.32 | 0.33 | 2.38 / 1.34 |
| BL-042 hinge, no groove | 23 fill L | 1.44 | 0.81 | 0.65 | 1.73 | 0.43 | 2.65 / 1.49 |
| **BL-049** | 23 fill L | 2.30 | 1.30 | 1.04 | 2.77 | 0.56 | 6.22 / 3.50 |
| bl049, stay as a 6 mm ellipse (STAY-AX) | 23 fill L | 2.19 | 1.23 | 0.99 | 2.63 | 0.56 | 5.93 / 3.33 |
| bl047_print, 0.75 mm voxels | 23 fill L | 0.87 | 0.49 | 0.39 | 1.04 | 0.22 | 2.19 / 1.23 |
| bl049, 0.75 mm voxels | 23 fill L | 2.25 | 1.27 | 1.01 | 2.71 | 0.54 | 5.59 / 3.15 |

Requirement: strength >= 1.0 on the factored row, fatigue >= 1.0 (goal 1.15, BL-021 scatter), creep >= 1.0. Fatigue: 1e5 x 1.6 g on the 1 g force (1019 / 3.0 = 340 N; 543 N peak). The groove is mesh-sensitive (a notch; 0.62 at 1 mm, 0.49 at 0.75 mm); the BL-049 hinge is not (1.30 / 1.27).

**Sweep (1 mm voxels, all 12 rows; `outputs/h1_lanes`):** thicker cheeks alone barely help (8 -> 12 mm: 0.81 -> 0.88), height helps (cheek +/-13 symmetric: 1.17), but the cheek cannot grow down (the HE box sits 5 mm under it). Lowering the floor 1 mm in place of the groove costs a little lever (0.81 -> 0.67 at the old height) and removes the notch; with the cheek 27 mm up and 10 mm thick it reaches 1.30.

**What the bag must meet (import `bag_attach.HINGE_EYE_ENVELOPE`):** gap under the pin 6.5 mm (was 5.5: 1 mm more at the throat centre; the HE-FIT worst corner goes 0.68 -> 1.09 mm at a 1.6 mm ply, corrie_f_body 24.6), floor 1.1 mm above the stay surface, cheek reach below the pin 9 mm (unchanged; `cheek_half_z_mm`), new keys `cheek_up_mm` 27 and `cheek_thickness_mm` 10 (outer faces at +/-20 mm from the stay: 2 mm more a side). Pin centre, throat and tip heights unchanged.

Bag-side HE check on the re-cut HE-FIT piece (`he_stl_check` via `bl047_frame_items.he_check`): pass True; worst under-pin clearance 1.09 mm, at the 0.15 mm print tolerance 0.99 mm (>= 0.5: True), box top to cheek 3.12 mm.

### Hinge pin, one number

| pin | span mm | M N mm | sigma MPa | yield SF | fatigue SF (2.4 g: 679 N) | fatigue SF (3.0: 543 N) | g |
|---|---:|---:|---:|---:|---:|---:|---:|
| bl042, alu_7075_t6 | 28 | 4586 | 374 | 1.24 | 0.92 | 1.15 | 2.21 |
| bl042, ti_6al_4v | 28 | 4586 | 374 | 2.21 | 2.48 | 3.11 | 3.48 |
| bl049, alu_7075_t6 | 30 | 5095 | 415 | 1.11 | 0.83 | 1.03 | 2.43 |
| bl049, ti_6al_4v | 30 | 5095 | 415 | 1.99 | 2.24 | 2.80 | 3.83 |

M = F (2L - b) / 8 (load spread over the throat, reacted at the cheek centres). **Chosen: 5 mm Ti-6Al-4V** (record `ti_6al_4v`: S-basis yield 827 MPa, fatigue limit 510 MPa x 0.9). The 7075 pin fails at 1019 N on both spans; a 6 mm 7075 pin would need a bigger hole, sleeve and eye envelope.

## 2. US lanes on lug arms

Stations (published in `h1_lanes`, for BL-050): `US1_X` 70, `US1_Z` 95; `US2_X` 165, `US2_Z` 142 (mirror x for L); B-16 channel ends at the lane x (`CHANNEL_ENTRY_X`). The pin, floor and tip heights in y are the station's `imus_eye_envelope` values above the stay surface at that z, as before.

| arm | root section (at the stay) | tip section (at the fairlead) |
|---|---|---|
| us1 | y from yc -13 to the stay's bag face, z -5 / +11 | y from yc -10 to the fairlead floor, z -5 / +11 |
| us2 | y from yc -11 to the stay's bag face, z -15 / +15 | y from yc -8 to the fairlead floor, z -9 / +9 |

Linear taper (hull), 3 mm edge radius. US1 runs at z 90-106: 3 mm over the BL-049 hinge cheek top (z 87), 6 mm under the spreader sheet's bottom edge (z 112); its underside merges into the lower branch at x 74-93. US2's root (z 127-157) fills the spreader's US2 notch.

**Loads** (frame side, factored): bag-off cradle 720 N at 2.4 (1.6 g x 1.5; fatigue at 480 N), aft and down at the cradle angle; bag-on cam-tight US1 444 N / US2 296 N at 3.0, straight down, down + 30 deg towards the wearer and along the drape's first path segment off the pin; each also +/-10 deg out of plane (US-FLEET).

| lug | load | strength | fatigue | creep | governing region |
|---|---|---:|---:|---:|---|
| us1 | cradle (720 N) | 1.88 | 0.84 | 1.80 | root |
| us1 | cradle fleet_in (720 N) | 2.06 | 0.93 | 1.97 | root |
| us1 | cradle fleet_out (720 N) | 1.78 | 0.80 | 1.71 | root |
| us1 | bagon_down (444 N) | 3.00 | 1.69 | 3.61 | root |
| us1 | bagon_fore30 (444 N) | 2.80 | 1.58 | 3.36 | root |
| us1 | bagon_drape (444 N) | 3.27 | 1.84 | 3.92 | root |
| us2 | cradle (720 N) | 2.44 | 1.10 | 2.34 | root |
| us2 | cradle fleet_in (720 N) | 2.31 | 1.04 | 2.22 | root |
| us2 | cradle fleet_out (720 N) | 2.64 | 1.19 | 2.54 | root |
| us2 | bagon_down (296 N) | 7.44 | 4.19 | 8.93 | fairlead |
| us2 | bagon_fore30 (296 N) | 7.30 | 4.11 | 8.76 | arm |
| us2 | bagon_drape (296 N) | 5.50 | 3.09 | 6.60 | root |

Regions: FI99 over the fairlead, over the arm, and over the arm's first 6 mm off the stay ('root'); the record's whole-yoke FI99 is higher. The stub leaves out the lower branch (US1) and the frame beyond +/-22 mm (ASSUMPTION STAY-STUB), so 'root' is a lower bound; **US1 0.80 at the root is below 1.0 on this model** (US2 1.04); on the arm itself US1 reads 1.19 and US2 1.38, the fairleads 1.62 / 1.62. On the whole voxel body (the branch in, section 3) the US1 junction governs the cradle at fatigue 1.14. Fairlead pins (5 mm 7075) at the 720 N cradle: yield 1.75, fatigue 1.30.

## 3. Body checks on the lanes body

h1_buckling.full_check on the voxel body as printed (BL-046 body + the old US stubs stripped + the lug arms in), loads from the real crown (BL-046 `_real`), the sim sets' under-strap loads moved to the lanes (ASSUMPTION LANE-MOMENT). Before = `check_m1_u2.5_im3_bl046_real`.

| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after | joint S / F after |
|---|---|---|---|---|---|
| fine_sm8 | 1.671 / 1.678 | 1.205 / 1.247 | 2.570 / 2.660 | 1.143 / 1.171 | 2.09 / 1.72 |
| fine | 1.671 / 1.678 | 1.227 / 1.263 | 2.618 / 2.694 | 1.129 / 1.138 | 2.09 / 1.72 |
| beam | 1.595 / 1.611 | 1.219 / 1.223 | 2.601 / 2.610 | 1.175 / 1.250 | 1.96 / 1.25 |
| fine_sm8.cyc | 1.671 / 1.678 | 0.797 / 0.829 | 1.699 / 1.768 | 1.045 / 1.106 | 2.12 / 1.09 |

Bag-off cradle as its own sets (720 N at each of the four US pins, aft and down, +/-10 deg fleet; the aft pull reacted by the meat bearing on the stay faces z 60-155, the rest at the hip pivot; never part of the body record before; governing spot: the US1 arm root on the stay, z 107): on the lanes strength 2.54, fatigue 1.14, buckling 5.14; same loads on the stays (BL-045 print) 2.70 / 1.22 / 11.32.

`fine_sm8.cyc` fatigue stays below 1 (BL-024 cinch-cycled set, R1 hold for MT-1), as before this ticket.

## 4. Print files and checks

| file | g | watertight | shells | footprint mm | bed (best rotation) |
|---|---:|---|---:|---|---|
| h1_assembled.stl | 974.2 | True | 1 | | |
| h1_lower_flat.stl | 430.7 | True | 1 | 368 x 234 x 77 | 343 x 323 at 66 deg: **does not fit** (brim does not fit) |
| h1_upper_flat.stl | 543.5 | True | 1 | 280 x 309 x 64 | 309 x 280 at 90 deg: fits (brim fits) |

Slice checks on `h1_assembled.stl`: fairleads 12 / 12 pass (eye stacks included); spine channel pass True (clear 0.96 mm, fore wall 3.67); pawl pass True (low-profile pawl min 0.51 mm over its 10 deg swing). Test pieces sliced the same way: 5 / 5 stations pass (us_route_stay_R|hinge_R, us_route_stay_R|us1_R, us_route_stay_R|us2_R, hefit_hinge_fairlead_R|hinge_R, im3ec_cheek_R|im3_R).

| station | x | gap under pin | throat | cheek | cheek height | eye fits | pass |
|---|---:|---:|---:|---:|---:|---|---|
| hinge_L | -115 | 6.49 | 20.0 | 9.99 | 36.0 | True | True |
| hinge_R | 115 | 6.50 | 20.0 | 9.99 | 36.0 | True | True |
| im1_L | -115 | 5.50 | 20.0 | 7.99 | 18.0 | True | True |
| im1_R | 115 | 5.50 | 20.0 | 7.99 | 18.0 | True | True |
| im2_L | -115 | 5.50 | 20.0 | 7.99 | 18.0 | True | True |
| im2_R | 115 | 5.50 | 20.0 | 7.99 | 18.0 | True | True |
| im3_L | -115 | 5.50 | 20.0 | 7.98 | 28.0 | True | True |
| im3_R | 115 | 5.50 | 20.0 | 7.98 | 28.0 | True | True |
| us1_L | -70 | 5.50 | 20.0 | 8.00 | 18.0 | True | True |
| us1_R | 70 | 5.50 | 20.0 | 8.00 | 18.0 | True | True |
| us2_L | -165 | 5.50 | 20.0 | 8.00 | 18.0 | True | True |
| us2_R | 165 | 5.50 | 20.0 | 8.00 | 18.0 | True | True |

'now' = the print with the bag's B-16 channel ends where the pattern has them today (x +/-95): fails, as BL-048 found; 'print_lanes' = the same print with the channel ends at the lane x (BL-048 'lanes_wide', for BL-050): passes. 'lanes' / 'lanes_wide' are BL-048's layouts recomputed off the BL-049 hinge (2 mm wider cheeks), kept as sensitivities.


**us_route re-run on this STL** (`designs/pack_5200/us_route.py`, the strap ribbon against the sliced print on the 15 / 19 / 23 in meat drapes, >= 10 mm required):

| layout | US1 x | US2 x | channel entry | worst clear US1 / US2 mm | pass |
|---|---:|---:|---|---|---|
| now | 70.0 | 165.0 | 95 / 95 | 4.9 / -3.2 | False |
| print_lanes | 70.0 | 165.0 | 70 / 165 | 12.4 / 14.6 | True |
| lanes | 72.5 | 157.5 | 72 / 158 | 9.9 / 8.0 | False |
| lanes_old_channel | 72.5 | 157.5 | 95 / 95 | 4.5 / -4.7 | False |
| lanes_wide | 68.0 | 167.0 | 68 / 167 | 14.5 / 15.5 | True |

Test piece `designs/pack_5200/print/frame_h1/test_pieces/us_route_stay_R.stl`: R stay z 40-160, x 46-189 (hinge, US1 lug, US2 lug), 129.6 g, watertight True, 1 shell. HE-FIT (`hefit_hinge_fairlead_R`) and IM3-EC re-cut from the new print too.

## 5. Mass

| item | g | oz |
|---|---:|---:|
| lug arms (4) | +71.2 | +2.51 |
| hinge growth, lane fairleads, old US stubs out, no groove | +16.8 | +0.59 |
| **printed body, net** | +88.0 | +3.10 |
| Ti hinge pins (2) vs 7075 as booked | +2.8 | +0.10 |
| **frame, net** | +90.8 | +3.20 |

Printed body 974.2 g (2.15 lb): lower 430.7, upper 543.5. Ledger rows BL049 (`huntkit/mass/ledger.py`, source this json).

**Mass reductions that keep the SF (not applied):** (1) the lug arms as I-sections (3 mm webs, flanges top and bottom): the arm region has margin (US1 1.19, US2 1.38), the root does not, so only outboard of the root, about -15 g for four arms (estimate, needs the lug FEA re-run); (2) the US1 arm onto the lower branch it already touches (a short web down to the branch instead of the full-depth root), which also lifts its root SF.

## 6. Assumptions

- ASSUMPTION HINGE-ROW: The hinge eye's factored row is 1019 N (bl047_frame_items.HINGE_ROW_N, 3.0 x the 1 g sim eye); the fairlead fatigue is judged at 1.6 / 3.0 of it (543 N, the load standard's walking peak) and also shown on the pin's 2.4 g basis (679 N). Settled by: SEW-F HE rows and the T2 meat test with a load pin at one stay foot (FLOOR_SPAN).
- ASSUMPTION FI99-RULE: Cheek and lug strength / fatigue use the record's FI99 rule (99th percentile of the PAHT-CF layer failure index over the fairlead / lug, 1 mm voxels). The single hottest voxel is lower (BL-049 hinge: 0.56 on the governing direction, BL-047 print 0.33): a 1 mm voxel corner is not a real fillet, but it is not proven either. Settled by: HE-FIT re-cut piece pulled to 1.6 x 340 N inboard-up for 1e5 cycles on the CA-1 rig (or CA-1 coupons with the cheek-root corner).
- ASSUMPTION STAY-STUB: The lug FEA fixes a stay stub (+/-22-23 mm) at its ends and leaves out the lower branch the US1 arm merges into: its junction numbers are a lower bound. The whole-body check carries the lane moment at the stay node. Settled by: Strain gauge at the US2 arm root in the T1 carry test; MT-1 cradle pull on the first article.
- ASSUMPTION LANE-MOMENT: In the body check each under-strap pin load stays on its stay node and gains the moment of the lateral lane offset (beam sets carry no under-strap load; their z 90 / 130 node loads are the meat-strap reactions). Settled by: Same as STAY-STUB.
- ASSUMPTION PIN-KS: Hinge pin fatigue: rotating-beam limit x 0.9 (machined / ground), Goodman to R 0 on the UTS, as h1_fairleads.pin_bending. Settled by: Supplier fatigue figure for the Ti-6Al-4V pin stock.
- ASSUMPTION PIN-L: Hinge pin length = throat + 2 cheeks + 4 mm (head / clip groove), 44 mm. Settled by: The bought pin.
- ASSUMPTION SUPPORTS: The lug arms' undersides overhang (cantilevers off the stay, layer normal y): tree supports under the four arms; the rest of the body prints as before. Settled by: First article: slicer preview and the arm underside finish.
- ASSUMPTION SHEET-CLEAR: The US1 arm (z 90-106) stays 6 mm under the spreader sheet's z 112 edge; the US2 arm root (z 127-157) fills the sheet's US2 notch, which kept NOTCH_CLEAR 6 mm round the old fairlead. Settled by: Spreader dry fit on the first article (the notch may be trimmed; the spreader is not re-cut here).
- Also carried: HE-T, HE-GAP-MARGIN, HE-NECK-TOL, HOLE_REAM, STAY-AX, SIM_BODY, THROAT-Z (h1_fairleads.md 8); US-FLEET, US-TOPO, DRAPE-US (us_route.json).

## 7. Screenshots

- `outputs/screens/20261113_BL049_1.png`
- `outputs/screens/20261113_BL049_2.png`
- `outputs/screens/20261113_BL049_3.png`
- `outputs/screens/20261113_BL049_us_1.png`
- `outputs/screens/20261113_BL049_us_2.png`
