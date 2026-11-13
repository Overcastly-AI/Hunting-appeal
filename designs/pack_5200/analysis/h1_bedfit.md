# H1 print-bed fit with the US2 lanes: bolt-on US2 outer clevis (BL-050 Part A)

> **BL-051 (2026-11-13):** the print described here had the stay crown cut 2 mm low over z 86-104 and z 131-152 (`h1_lanes.strip_old_us`); it is restored and re-exported, see `h1_crown.md` for the current print masses (assembled 997.7 g), slice checks, US2 lug (real stay section) and the z 142 notch, whose 'root air' below was the cut-away crown (rule now: nothing proud of the support line). The ledger's pins / sleeves row (A4) is retired: the US1 / US2 pins + sleeves were already booked by `meat_haul.cradle_parts_g` (a double count, -10.8 g).

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-050-bed-fit-and-bag-lanes.md` Part A. Code `huntkit/gendesign/h1_bedfit.py` (`python -m huntkit.gendesign.h1_bedfit --probe 147 | --joint`; the report with no flag), hooked into `h1_buckling.export_print` (`US2_CLEVIS`); I-section option in `h1_lanes` (`ISECT`, `ARM_ISECT`); spreader check `spreader.us2_notch_check`; tests `tests/test_h1_bedfit.py`. Results `h1_bedfit.json`. Units mm, N, g (imperial in brackets).

## Summary

- **Option (c) fails.** The largest US2 x whose lower half fits the H2S with the 8 mm brim is about 147 mm (real export: 322.33 x 301.99 mm at its best rotation). There the US2 strap hits the hinge fairlead: worst clearance **-3.2 mm** against >= 10 (23 in R); every torso and side is below 10 mm.
- **Option (a) adopted: bolt-on US2 outer clevis.** US2 stays at x +/-165 (z 142). The US2 fairlead is split at |x| 163 in the throat floor; the outer floor + outer cheek print as `us2_clevis_R` / `_L` (14.1 g each) and bolt to the body with two Ti M5 x 40 along x (the z 234 joint's screw type), nuts in side traps. Joint (outer cheek share 0.6): strength **3.85** (net_section, cradle), fatigue **1.73** (net_section_paht); at share 1.0 2.31 / 1.04.
- **Bed:** lower half as written **321.1 x 299.6 mm** (turned 163.5 deg on the plate), + 8 mm brim: 3.0 / 4.4 mm spare; upper 309.4 x 280.1 (14.6 / 23.9 spare). `test_print_halves_fit_the_h2s_bed` passes (xfail removed).
- **Strap route on the new STL** (`us_route.py`, 'print_lanes'): worst US1 12.4 / US2 14.6 mm, every torso and side >= 10: pass True. US2 lug (BL-049 lug FEA, geometry unchanged at x 165): strength 2.31, fatigue 1.04 (cradle|fleet_in, root).
- **Lug arms (A2): kept solid.** I-section (3 mm web / flanges, about -14 g) drops the US1 arm fatigue 1.19 -> 0.54 and the roots too (open section, the arm twists); closed box variants also lower the roots. No variant holds every margin.
- **Spreader (A3):** the z 142 notch is 0 mm from the US2 arm root in plan (by construction), but the root lies under the sheet: measured air **2.31 mm** below the crown line the sheet bears on (>= 1.5): pass. Clearance rule fixed (3D, `spreader.us2_notch_check`); the sheet is not re-cut.
- **Ledger (A4):** pins + sleeves booked for 8 stations, 12 placed: +10.80 g (every config). Print +20.9 g (joint blocks), joint hardware +24.4 g: frame **+45.3 g (+1.60 oz)** against BL-049. Rows BL050.

## 1. Option (c): bring US2 in

Footprint sweep on the BL-049 lower half (the US2 lug and fairlead moved in rigidly), best rotation, 8 mm brim:

| US2 x | best rotation deg | footprint mm | over the bed with brim, mm |
|---:|---:|---|---:|
| 165 | 155.75 | 342.9 x 322.1 | +18.9 |
| 161 | 157.25 | 338.9 x 317.5 | +14.9 |
| 157 | 158.75 | 334.5 x 313.4 | +10.5 |
| 153 | 70.25 | 329.9 x 309.1 | +5.8 |
| 151 | 161.25 | 327.3 x 306.1 | +3.3 |
| 149 | 72 | 324.7 x 303.8 | +0.7 |
| 148 | 72.25 | 323.5 x 303.0 | -0.5 |
| 147 | 72.75 | 322.1 x 301.5 | -1.9 |
| 145 | 163.5 | 319.4 x 299.1 | -4.6 |
| 141 | 75.25 | 313.6 x 293.3 | -10.3 |

Real export with US2 at x 147 (`probe`, outputs/h1_bedfit/probe_147): lower half 331.5 x 234.49 mm as laid flat, best rotation 322.33 x 301.99 at 162.75 deg, over -1.7 mm with the brim: fits. Strap route on that STL:

| torso | side | US2 least clearance mm (hinge / HE / US1) | pass |
|---:|---|---:|---|
| 15 | R | 1.9 | False |
| 15 | L | 2.5 | False |
| 19 | R | 1.4 | False |
| 19 | L | 1.0 | False |
| 23 | R | -3.2 | False |
| 23 | L | -2.1 | False |

The strap's 25 mm ribbon comes off a pin 32 mm outboard of the stay and runs past the hinge fairlead's outer cheek (x 135): the BL-048 lane offset (throat / 2 + cheek + 10 + strap / 2 = 42.5 mm, 157.5) is already more than the bed allows. Option (c) is out.

## 2. Option (a): bolt-on US2 outer clevis

- Split plane |x| 163: in the US2 throat floor (throat 155-175), so the body prints the arm, the inner cheek and 8 mm of floor; the clevis is the outer 12 mm of floor and the outer cheek (175-183).
- Joint blocks under the throat floor: y -9.8 from the stay centre (y -12.5) to the floor (y 8.4), z +/-14.5 about the pin; body block |x| 141-163, clevis 163-183. Above the floor nothing changes (throat, cheeks, pin, eye envelope).
- Two Ti gr5 M5 x 40 DIN 7984 along x at y -4.3 from the stay centre, z +/-8; DIN 433 washers (OD 10); head on the clevis's outer face, nut + washer in a side trap in the body (|x| 145.8-151) that opens to the wearer face. Holes printed 4.8, reamed 5.1. Plugs: body 12 mm, clevis 20 mm.
- Loads: every US2 row of `h1_lanes.lug_loads` (bag-off cradle 720 N at 2.4, bag-on 296 N at 3.0, +/-10 deg fleet); fatigue at 1.6 g (row x 1.6 / basis). The clevis gets the outer cheek's share (CLEVIS-SHARE) at the outer cheek centre on the pin line. Face: rigid dry contact, tension-only bolts, no preload (`frame_h1.contact_solve`, as the z 234 joint); bolt shear = direct + the torsion couple; capacities by the z 234 joint's rules (`frame_h1.joint_capacities`; hole bearing on the interlayer strength, conservative). Body net section through the traps: biaxial bending + axial (magnitudes added), torsion and shear, layer rule.

| load | on clevis N (x, y, z) | bolt T N | bolt V N | contact MPa | net-section FI | min SF | min fatigue |
|---|---|---|---|---:|---:|---:|---:|
| cradle | 0, 369, -225 | 136 / 375 | 525 / 182 | 4.1 | 0.259 | 3.85 | 1.73 |
| cradle|fleet_out | 125, 363, -221 | 65 / 315 | 517 / 179 | 2.64 | 0.225 | 4.44 | 2.0 |
| cradle|fleet_in | 0, 363, -221 | 134 / 370 | 517 / 179 | 4.03 | 0.255 | 3.91 | 1.76 |
| bagon_down | 0, 0, -178 | 0 / 163 | 274 / 274 | 2.38 | 0.07 | 8.39 | 4.72 |
| bagon_down|fleet_out | 52, 0, -175 | 47 / 308 | 270 / 270 | 5.51 | 0.069 | 8.52 | 4.79 |
| bagon_down|fleet_in | 0, 0, -175 | 0 / 160 | 270 / 270 | 2.34 | 0.069 | 8.52 | 4.79 |
| bagon_fore30 | 0, -89, -154 | 65 / 294 | 196 / 280 | 6.11 | 0.087 | 8.22 | 4.62 |
| bagon_fore30|fleet_out | 52, -88, -152 | 239 / 465 | 193 / 276 | 10.38 | 0.102 | 6.79 | 4.69 |
| bagon_fore30|fleet_in | 0, -88, -152 | 64 / 290 | 193 / 276 | 6.02 | 0.086 | 8.34 | 4.69 |
| bagon_drape | 0, -178, -9 | 350 / 363 | 76 / 102 | 10.23 | 0.101 | 6.88 | 5.59 |
| bagon_drape|fleet_out | 52, -175, -9 | 520 / 533 | 75 / 100 | 14.43 | 0.115 | 4.88 | 4.32 |
| bagon_drape|fleet_in | 0, -175, -9 | 345 / 358 | 75 / 100 | 10.08 | 0.099 | 6.99 | 5.68 |

Capacities (N): washer_bearing_n 4091.1, plug_shear_out_n 5414.4, bolt_tension_n 8896.3, bolt_fatigue_n 3177.2, hole_bearing_n 2301.1, bolt_shear_n 7193.9, contact_mpa 70.4.

Governing: strength 3.85 (net_section), fatigue 1.73 (net_section_paht), both on the cradle row. With the whole pin load on the clevis (share 1.0): 2.31 / 1.04. The Ti bolts are far from their limits (tension SF >= 17); the PAHT round the fitted holes governs.

**Slice check of the joint on the print** (`joint_slices`, both sides pass True): at |x| 170 the clevis section has two holes of d_eq 4.79, 4.79 mm on the bolt axes; at the trap plane the traps open to the wearer face and the block top is whole; the joint face is a closed 605 mm2 section.

## 3. Print files and checks

| file | g | watertight | shells | as written mm | + 8 mm brim on 340 x 320 |
|---|---:|---|---:|---|---|
| h1_assembled.stl (body + clevises, frame coordinates) | 995.1 | True | 1 | | |
| h1_lower_flat.stl | 423.4 | True | 1 | 321.1 x 299.6 x 76.7 | fits True, spare 3.0 / 4.4 |
| h1_upper_flat.stl | 543.5 | True | 1 | 309.4 x 280.1 x 64.4 | fits True, spare 14.6 / 23.9 |
| us2_clevis_R.stl | 14.14 | True | 1 | 20.7 x 29.0 x 36.5 | fits |
| us2_clevis_L.stl | 14.14 | True | 1 | 20.7 x 29.0 x 36.5 | fits |

Slice checks on `h1_assembled.stl` (`h1_lanes.slice_checks`): fairleads 12 / 12 pass True (eye stacks included; US2 R/L gap under pin 5.5 / 5.5, cheeks 8.0); spine channel pass True (clear 0.964 mm); pawl pass True; test pieces pass True (us_route_stay_R|hinge_R, us_route_stay_R|us1_R, us_route_stay_R|us2_R, hefit_hinge_fairlead_R|hinge_R, im3ec_cheek_R|im3_R).

Test piece `print/frame_h1/test_pieces/us_route_stay_R.stl` re-cut: 125.9 g as printed (the US2 outer clevis is not in it: bolt `us2_clevis_R` from the frame folder onto it, 140.0 g assembled); the `_frame_coords` copy is the piece as assembled (the slice checks read it).

**Strap route on the new STL** (`designs/pack_5200/us_route.py`, 'print_lanes', channel ends at the lane x):

| torso | side | US1 mm | US2 mm |
|---:|---|---:|---:|
| 15 | R | 12.4 | 19.2 |
| 15 | L | 13.0 | 21.5 |
| 19 | R | 14.0 | 14.6 |
| 19 | L | 12.4 | 15.5 |
| 23 | R | 14.0 | 18.8 |
| 23 | L | 12.4 | 16.4 |

## 4. Lug arms as I-sections (A2)

Same lug FEA as BL-049 (`h1_lanes.lug_fea`, stay stub, 1 mm voxels, every US load), arm pocketed from |x - stay| = stay radius + 6 mm to 2 mm short of the fairlead. Lowest fatigue per region over the loads (strength in brackets):

| arm | g saved (4 arms) | US1 fairlead / arm / root | US2 fairlead / arm / root | every margin holds |
|---|---:|---|---|---|
| solid | 0.0 | 1.62 / 1.19 / 0.8 (1.78) | 1.62 / 1.38 / 1.04 (2.31) | - |
| I_w3_f3 | 13.6 | 1.57 / 0.54 / 0.66 (1.2) | 1.58 / 0.65 / 0.97 (1.44) | False |
| box_w3_f3 | 13.6 | 1.61 / 0.91 / 0.76 (1.69) | 1.62 / 0.86 / 1.01 (1.92) | False |
| box_w4_f4 | 11.0 | 1.62 / 1.04 / 0.77 (1.72) | 1.62 / 1.08 / 1.02 (2.28) | False |
| box_w5_f5 | 8.6 | 1.62 / 1.11 / 0.78 (1.73) | 1.62 / 1.21 / 1.03 (2.29) | False |

The cradle pulls the pin aft and down 17-23 mm above the arm's centre line, so the arm carries torsion as well as bending; an open I-section has a small fraction of the solid arm's torsion stiffness, the arm twists and the stress moves into the web and the root. A closed box keeps the torsion but the thin walls still raise the root (US1 0.80 -> 0.76-0.78). **Arms stay solid** (`h1_lanes.ARM_ISECT` all False); the -15 g is not available at these margins.

## 5. Spreader US2 notch (A3)

In plan the notch (z 127-157) and the US2 arm root (z 127-157) coincide: plan clearance 0 mm. The notch cannot grow (z 121 would cut the z 119 clip tab and the z 118.5 bottom edge tube) and the root cannot shrink (it governs the US2 lug). But NOTCH_CLEAR is the air round a cleat that stands up through the sheet, and the arm root does not: its top is the stay crown line, and on the print it sits under it. Measured on `h1_assembled.stl` (`spreader.us2_notch_check`): the sheet's support (stay crown) is y 10.0 at z 127 and y 11.84 at z 160; the highest print inside the notch footprint is **2.31 mm** below that line (required 1.5): pass. The rule is now the 3D one; the sheet is not re-cut. Owner option: close the z 142 notch (no cleat there any more), which needs the spreader re-run.

## 6. Mass

| item | g | oz |
|---|---:|---:|
| print: joint blocks + bolt / trap cuts (assembled BL-050 995.1 - BL-049 974.2) | +20.9 | +0.74 |
| 4 Ti gr5 M5 x 40 DIN 7984 | +16.30 | +0.575 |
| 4 A2 M5 hex nuts ISO 4032 | +4.52 | +0.159 |
| 8 A2 M5 x 10 x 1 washers DIN 433 | +3.57 | +0.126 |
| **frame, net (BL050 H1 rows)** | **+45.3** | **+1.60** |
| attachment: 7075 pins (2.413 g) + UHMWPE sleeves (0.287 g) for 4 more stations | +10.80 | +0.381 |

Printed: lower 423.4 g, upper 543.5 g, clevises 28.3 g (995.1 g, 2.19 lb). Ledger rows BL050 (`huntkit/mass/ledger.py`, from this json).

**Mass reductions that keep the SF (not applied):** (1) the joint blocks are sized by the M5 washer and the trap: the clevis block outboard of the outer cheek root could be chamfered under the cheek (about -2 g, needs the net-section re-check only); (2) the US1 arm onto the lower branch it touches (BL-049 proposal 2) - it would also lift the US1 root (fatigue 0.80 on the stub model), which is what blocks every lighter arm.

## 7. Assumptions

- ASSUMPTION CLEVIS-SHARE: The outer cheek (the bolt-on clevis) takes 0.6 of the pin's y-z load and the whole fleet x load when it pushes outboard (eye 18-19 mm in a 20 mm throat; centred = 0.5); the whole load on the clevis (1.0) is the sensitivity (json joint_share_1, section 2). Settled by: US2 clevis joint pull on the CA-1 rig: us_route_stay_R + us2_clevis_R bolted, 720 N cradle direction, eye off-centre against the outer cheek, then 1e5 cycles at 480 N.
- ASSUMPTION CLEVIS-DRY: Dry butt joint, no preload credited (snug, as the z 234 joint), fitted bolts take the shear; no friction credited; the lug FEA (BL-049 stub, monolithic) stands for the cheeks and arm because the joint face sits under the throat floor, away from the cheek roots. Settled by: Same pull test: no joint opening at 720 N (feeler 0.05 mm), strain gauge at the arm root as STAY-STUB.
- ASSUMPTION CLEVIS-PRINT: The clevis prints in the body's orientation (wearer face on the plate, layer normal frame y), so its cheek is the cheek the BL-049 lug FEA checked; holes printed 4.8 and reamed 5.1 like every other bolt hole. Settled by: First article: ream fit, slicer preview of the clevis.
- ASSUMPTION SEAM-FLOOR: The joint line crosses the US2 throat floor 8 mm from the inner cheek; the eye sits 5.5 mm above the floor (gap under the pin) and does not ride on it. Settled by: FIT-US / HE-FIT step 0: slide the US eye across the seam under load; chamfer 0.3 mm both edges if it catches.
- ASSUMPTION HEAD-PROUD: The bolt heads stand 4.5 mm proud of the clevis's outer face (x +/-187.5 at z 134 / 150), inside the 394 mm pack width; the bag's side panel is outboard. Settled by: FIT-US on P1: nothing rubs the heads.
- ASSUMPTION BED-ROT: The flat halves are written turned on the plate (lower 163.5 deg) so the slicer needs no rotation; the 8 mm brim is from print/frame_h1/README.md. Settled by: Slicer plate preview on the H2S profile, first article.
- ASSUMPTION ROOT-AIR: The spreader sheet rests on the stay crowns each side of the z 142 notch; the US2 arm root under it is >= 1.5 mm below that line (spreader.us2_notch_check). Settled by: Spreader dry fit on the first article: 1.5 mm feeler between sheet and root.
- ASSUMPTION PROBE-X: Option (c) used US2 x 147 (largest x with the brim on the real export; the footprint sweep puts 149 0.7 mm over). Settled by: Not needed: the strap fails by 13 mm at 147.
- Carried: HINGE-ROW, FI99-RULE, STAY-STUB, LANE-MOMENT, PIN-KS, PIN-L, SUPPORTS, SHEET-CLEAR (now ROOT-AIR) (h1_lanes.md 6); US-FLEET, US-TOPO, DRAPE-US (us_route.json); the z 234 joint rules (frame_h1).

## 8. Screenshots

- `outputs/screens/20261113_BL050_1.png`
- `outputs/screens/20261113_BL050_2.png`
- `outputs/screens/20261113_BL050_3.png`
- `outputs/screens/20261113_BL050_4.png`
- `outputs/screens/20261113_BL050_us_1.png`
- `outputs/screens/20261113_BL050_us_2.png`
