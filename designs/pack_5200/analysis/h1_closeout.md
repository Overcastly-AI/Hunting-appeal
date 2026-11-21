# H1 close-out before review 6 (BL-055 Part A)

structural-fea-engineer, 2026-11-21 (resumed from the 2026-11-14 WIP). Ticket `docs/backlog/BL-055-close-out.md` Part A. Code `huntkit/gendesign/h1_closeout.py` (`python -m huntkit.gendesign.h1_closeout --body` for the whole body, the report with no flag); print hook `frame_h1.print_mesh` (`h1_closeout.add_hip_pilots`); tests `tests/test_h1_closeout.py`. Results `h1_closeout.json`. Units mm, N, MPa, g (imperial in brackets). Supersedes the body margins of `h1_crown.md` and the hip-insert row of `hipbelt_structural.md` section 4.

## Summary

- **Whole body, BL-053 print, sanded 0.2 mm (governing):** strength 1.64, fatigue 1.19 on the three static-cinch bases and **0.84 on fine_sm8.cyc** (below R1, as on every body since BL-024: R1 hold for MT-1), creep 1.80, buckling 1.17, z 234 joint 1.90 / 1.19 (1.05 on .cyc). The sanding costs at most 4.2 % (k 1.042, worst section z 40 R); the BL-053 lug fixes gain 1-3 % on every basis against BL-051.
- **Hip boss:** 8 x M5 brass heat-set inserts on r 19 in two groups of 4 at the sides (angles -42, -14, 14, 42, 222, 194, 166, 138 deg from +x), boss and mount flange D50, pilot D6.4 x 11.5 deep. SF strength **2.15** (goal 1.5), fatigue **1.21** (goal 1.15), creep 2.58, with the layer-normal pull-out. The 2-insert record was 0.995 on an assumed 1500 N insert; on the insert record (1200 N) and the layer-normal ratio it is 0.42.
- **Change from the 2026-11-14 WIP:** the WIP chose 9 inserts equally spaced on a D44 boss; the holes next to the mount's two legs put screw heads on them ( head-to-leg -4.2 mm). With the legs kept, no pattern under the drawn D44 disc reaches fatigue 1.15 (best 8 split, 1.07); the mount base must be redrawn anyway (it is a 1.2 mm disc with no screw holes), so it grows to D50 x 3 mm.
- **Pins:** US1 pins in Ti-6Al-4V (orchestrator call): dy 95 fatigue 0.97 -> **2.63**, +2.86 g.
- **Mass:** print +10.5 g (assembled 1061.1 g), 6 more inserts and screws +22.46 g, Ti mount flange +13.82 g, US1 Ti pins +2.86 g: **+49.6 g (1.75 oz)**, booked in the ledger (BL055).
- **Print:** re-exported; slice check of the pilots passes; every STL a closed single shell: True.

## 1. Whole body on the BL-053 print

`h1_buckling.full_check` (H1's FI99 rule per kit and setting, member Euler margins, the z 234 joint) on the lane kit sets with the real crown models, as `h1_crown.body` ran it, on `h1_lanes.body_solid` plus the BL-053 lug fixes voxelised on the 2 mm grid (46.9 g of fix voxels). Sanded: every stay element's stress x k (below). All values SF / req; R1 needs >= 1.

| basis | strength | fatigue | creep | buckling | joint str / fat | governing |
|---|---|---|---|---|---|---|
| fine_sm8 | 1.679 / 1.706 / **1.706** | 1.258 / 1.298 / **1.272** | 2.683 / 2.770 / **2.713** | 1.171 / 1.228 / **1.228** | 1.99 / 1.63 | S_meat@a_L_fine_sm8_23 |
| fine | 1.679 / 1.706 / **1.706** | 1.271 / 1.311 / **1.288** | 2.712 / 2.796 / **2.749** | 1.138 / 1.180 / **1.180** | 1.99 / 1.63 | S_meat@a_L_fine_23 |
| beam | 1.613 / 1.638 / **1.638** | 1.235 / 1.243 / **1.193** | 2.635 / 2.652 / **2.546** | 1.256 / 1.404 / **1.404** | 1.90 / 1.19 | C_im3@a_L_beam_23 |
| fine_sm8.cyc | 1.679 / 1.706 / **1.706** | 0.834 / 0.851 / **0.842** | 1.778 / 1.815 / **1.796** | 1.095 / 1.173 / **1.173** | 2.01 / 1.05 | S_meat@a_L_fine_sm8_cyc_23 |

Each cell: BL-051 record / BL-053 as printed / BL-053 sanded 0.2 mm.

Margins against R1 (sanded): strength +64 %, fatigue +19 % (static-cinch bases), -16 % on fine_sm8.cyc, buckling +17 %, joint +90 % / +19 % (+5 % on .cyc). Raster 892.8 -> 939.6 g.

**Sanding factor.** The print's stay sections at 15 heights, both stays, each with 0.2 mm taken off every wearer-facing edge (bores and traps not sanded): worst ratio k = **1.0416** (z 40 R, 112.4 mm2, 11.77 mm deep), against 2.2 % for an 18 mm rectangle (the BL-053 estimate). Applied as a uniform factor on every stay element (ASSUMPTION SAND-K), so buckling and the joint see it too (conservative).

The cache was resumed: the 2026-11-14 run had finished 7 of the 8 basis runs before the stop; the last (sanded fine_sm8.cyc) was re-run on 2026-11-21. A fresh beam-basis run reproduced the cached nominal result (test `test_whole_body_cache_reproduces`).

## 2. Hip boss insert pattern

Prying model of `hipbelt_structure.pivot_check` (the mount tips about the boss edge; V at the 21 mm pin stand-off plus e H, less H R), generalised to any pattern and to every tipping direction (72 directions; the worst is reported). Insert tension in proportion to the distance from the tipping line (rigid flange). Capacity per insert: 1200 N (insert record) x hot 0.8 x layer-normal 0.534 (47 / 88 MPa) = **512.7 N** static, 153.8 N at 1e5 (x 0.3), 205.1 N sustained (x 0.4). Hole axis = the print's build z (the boss face is on the plate), so the pull is along the layer normal.

| pattern | walls ok | head to leg (mm) | strength | fatigue | creep | pass |
|---|---|---|---|---|---|---|
| 2 ring r11 D32 | False | 10.0 | 0.35 | 0.20 | 0.42 | False |
| 4 ring r10 D32 | True | 2.0 | 0.63 | 0.35 | 0.75 | False |
| 6 ring r10 D32 | False | -0.5 | 0.94 | 0.53 | 1.13 | False |
| 6 ring r16 D44 | False | -0.5 | 1.47 | 0.83 | 1.77 | False |
| 9 ring r16 D44 | False | -4.2 | 2.21 | 1.24 | 2.65 | False |
| 10 ring r16 D44 | False | -3.6 | 2.46 | 1.38 | 2.95 | False |
| 8 split r16 D44 | True | 2.1 | 1.90 | 1.07 | 2.28 | False |
| 10 split r16 D44 | False | -2.1 | 2.42 | 1.36 | 2.90 | False |
| 8 split r17 D46 | True | 3.4 | 1.98 | 1.12 | 2.38 | False |
| 8 split r18 D48 | True | 4.7 | 2.06 | 1.16 | 2.48 | True |
| 6 split r19 D50 | True | 9.2 | 1.65 | 0.93 | 1.98 | False |
| 8 split r19 D50 | True | 5.7 | 2.15 | 1.21 | 2.58 | True |
| 10 split r19 D50 | True | 2.0 | 2.70 | 1.51 | 3.23 | True |

**Chosen: 8 split, r 19, boss D50** (the fewest inserts that pass on the smallest boss that keeps the fatigue row >= 5 % over its goal; 8 at D48 passes at 1.16).

| item | value |
|---|---|
| insert | `insert_heatset_brass_m5`, 7.1 OD x 9.5 long, 1.5 g |
| pilot hole | D6.4 x 11.5 deep from the boss face (insert + 2) |
| positions (frame x, z) | (14.12, 107.29); (18.44, 115.4); (18.44, 124.6); (14.12, 132.71); (-14.12, 107.29); (-18.44, 115.4); (-18.44, 124.6); (-14.12, 132.71) |
| walls (rule 2.6) | edge_mm 2.8, between_mm 2.79, to_pin_bore_mm 10.8, head_to_leg_mm 5.71, head_to_head_mm 0.69, floor_mm 4.5 |
| boss | D50, solid 16 mm from the face (was D32) |
| screws | 8 x Ti gr5 M5 x 14 DIN 7984 (2.24 g each), torque <= 2.5 N m |
| mount base (redraw) | D50 x 3 mm Ti disc, 8 x D5.5 on the same positions (drawn: D44 x 1.2 mm disc, no screw holes (designs/pack_5200/print/lug_hip_pivot_mount_slm_ti.stl)); flange bending leg root to screw row min SF / goal 3.27 |

| row | V (N) | H (N) | T max (N) | capacity (N) | SF | goal |
|---|---|---|---|---|---|---|
| C2|H_pin | 1601.0 | 1239.4 | 194.7 | 512.7 | 2.63 | 1.5 |
| C1|H_pin | 1067.3 | 826.3 | 129.8 | 512.7 | 3.95 | 1.5 |
| walk|H_pin | 853.9 | 661.0 | 103.8 | 153.8 | 1.48 | 1.15 |
| carry|H_pin | 533.7 | 413.1 | 64.9 | 205.1 | 3.16 | 1.5 |
| C2|H_frame | 1601.0 | 0.0 | 238.6 | 512.7 | 2.15 | 1.5 |
| C1|H_frame | 1067.3 | 0.0 | 159.1 | 512.7 | 3.22 | 1.5 |
| walk|H_frame | 853.9 | 0.0 | 127.3 | 153.8 | 1.21 | 1.15 |
| carry|H_frame | 533.7 | 0.0 | 79.5 | 205.1 | 2.58 | 1.5 |

Record reproduced: 2 x M5 at x +/-11 on D32, C2 with H on the pin T = 1205.6 N, SF 0.995 on the record's assumed 1500 N x 0.8 (hipbelt_structural 0.995); on the insert record 0.796, with the layer normal 0.425.

**Slice check of the exported print** (`hip_slices`, sections normal to y from the boss face):

| slice | pilot holes (D eq) | boss outer bounds x/z | pass |
|---|---|---|---|
| y_face+1 | 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39 | [-25.0, 95.0, 25.0, 145.0] | True |
| y_face+6 | 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39 | [-35.53, 95.0, 34.21, 145.0] | True |
| y_face+10.5 | 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39, 6.39 | [-49.42, 95.0, 48.88, 145.0] | True |
| y_face+13.5 | -, -, -, -, -, -, -, - | [-55.55, 95.0, 54.72, 145.0] | True |

Flat lower half (as it goes to the slicer), round D6.4 holes counted at 0.6 / 6 / 10.5 mm above the plate: {'z0.6': 8, 'z6': 8, 'z10.5': 8}. The holes print as vertical blind holes open to the plate: no support.

## 3. Pins

| station | qty | material | pin g | set g | design SF yield / fatigue | dy 95 SF yield / fatigue |
|---|---|---|---|---|---|---|
| hinge | 2 | ti_6al_4v | 4.26 | 5.06 | 1.99 / 2.24 | - / - |
| us1 | 2 | ti_6al_4v | 3.91 | 4.71 | 3.76 / 4.23 | 2.34 / 2.63 |
| us2 | 2 | alu_7075_t6 | 2.48 | 3.28 | 3.15 / 2.34 | 1.96 / 1.46 |
| im1 | 2 | alu_7075_t6 | 2.48 | 3.28 | - / - | - / - |
| im2 | 2 | alu_7075_t6 | 2.48 | 3.28 | - / - | - / - |
| im3 | 2 | alu_7075_t6 | 2.48 | 3.28 | - / - | - / - |

Pins total 36.18 g, clips + tethers 9.6 g; US1 in Ti +2.86 g against BL-053. BOM rows in `h1_closeout.json` `pins.bom`.

## 4. Cleanup

- `us_route.section_bearing`: the hull kept the -y (lower) chain; it now keeps the bag-side hull (test `test_section_bearing_keeps_the_bag_side_hull`).
- Superseded notes at the head of `h1_crown.md`, `h1_bedfit.md`, `h1_lanes.md` (and their generators).
- `bag_attach.THROAT` 18 -> 20 (as printed on all 12 stations); the 2026-11-01 value kept as `THROAT_LEGACY` for the legacy fairlead model, the eye FEA and the voxel stubs. The US1 wrap text no longer says 'pin sleeve'.

## 5. Mass

| item | g | source |
|---|---|---|
| print (assembled 1050.6 -> 1061.1 g) | +10.5 | export |
| 6 more inserts + screws | +22.46 | insert record, frame_comp_B.bolt_mass_g |
| Ti mount base D50 x 3 (was D44 x 1.2) | +13.82 | ti_6al_4v density |
| US1 pins in Ti | +2.86 | pins() |
| **total BL-055** | **+49.6 (1.75 oz)** | ledger BL055 |

Mass reductions that keep the SF: (1) D48 boss / flange with the same 8 inserts passes at fatigue 1.16 (about -4 g, 1 % margin); (2) a measured layer-normal pull-out (HB-6) above 0.534 x the record would allow 6 inserts (-3 g + screws).

## 6. Assumptions

- ASSUMPTION MOUNT-ORIENT: The SLM mount's local y is frame z: its two legs stand above and below the pin (along V), so the inserts split into two groups at the sides. Settled by: First-article fit of the mount on the boss; the mount drawing.
- ASSUMPTION FLANGE-RIGID: The mount base is redrawn as a 3 mm Ti disc (drawn: 1.2 mm) and acts as a rigid flange in the prying model (tipping about the boss edge, tension in proportion to the distance). Settled by: HB-6b hip-mount proof on the frame with the redrawn mount, a gauge on the most-loaded screw.
- ASSUMPTION INS-Z: Insert pull-out along the layer normal = record pull-out x hot 0.8 x PAHT-CF z / xy tensile ratio (47 / 88). Settled by: HB-6 insert pull-out on printed coupons, hole axis along the build z, at 60 C.
- ASSUMPTION INS-DEPTH: Pilot hole = insert length + 2 mm for displaced melt. Settled by: Section one HB-6 coupon: no melt plug under the insert.
- ASSUMPTION HIP-LAND: >= 1 mm flange between an insert hole and the mount's D10 pin bore. Settled by: Mount drawing.
- ASSUMPTION HEAD-LEG: >= 1 mm between a DIN 7984 head (D8.5) and a leg root, for the driver. Settled by: First-article assembly with a 4 mm hex key.
- ASSUMPTION HIP-BOOKED: The frame's fixed lump books 2 hip inserts and 2 screws; BL-055 books the rest. Settled by: Ledger audit.
- ASSUMPTION BOSS-LOCAL: The grown boss (solid, at the hard point x 0, z 120) is not in the 2 mm voxel body of the whole-body run: it adds material at a hard point the body already treats as fixed and the pilots stay inside it. Settled by: Next whole-body re-raster (review 6) from the exported print.
- ASSUMPTION SAND-K: The 0.2 mm sanding of the stays' wearer faces is a uniform stress factor k on every stay element (worst section ratio over 15 stations, both stays). Settled by: CA-1 bars printed over supports and sanded (BL-053 SCAR-KD).

## 7. Screenshots

- `outputs/screens/20261121_BL055_1.png`
- `outputs/screens/20261121_BL055_2.png`
- `outputs/screens/20261121_BL055_3.png`
