# Production frame — pawl, joint, barrier, surface, heat

Owner: structural-fea-engineer. Load standard HA-LS-1 rev B (no meat shelf). Code: `huntkit/gendesign/frame_production.py`. The SIMP study is `printed_frame_study.md`.

## Verdict

- **Pawl.** A pressed-in 304 bushing, OD 8 mm, ID 4.2 mm, cheek 8 mm. Hole-region layer FI99 0.64 (bare D4.2 hole on the same load: 1.11). Plastic bearing SF 2.30. Metal bearing SF 6.9.
- **Joint.** 2 × 5 mm pultruded carbon dowels per flange, 35 mm embed each side (8 dowels, 70 mm). Worst SF 1.44 (study baseline pull-out 1.03).
- **Barrier.** UHMWPE film, 1.20 mm, bag-side, spanning. Mass 89 g. Factored deflection 14.4 mm vs stand-off 30 mm. Walking skin pressure 0.0 kPa (limit 14). Sheet SF 1.41.
- **Surface.** The print file is the SIMP body, Taubin-faired. An elliptical loft was drawn and rejected: it cut the ligaments between the lumbar web and the stays.
- **FEA.** The 2 mm verification of this file (printed_frame_study.md) stands: strength SF 1.45, fatigue 1.03, cold torsion 0.94 of the tube frame. A 4 mm re-check is in the table below. Its minimum is 0.59 at single_stay_setdown|15, with a one-voxel skin reading hundreds of MPa; that spike is not in the 2 mm model, and the body was not thickened to chase it. Fatigue on the 4 mm mesh is 0.54; creep-rupture SF 1.16.
- **Mass.** Frame 799 g. Pack 2454 g (5.41 lb). Target 2268 g (5.0 lb). Gap +186 g.
- **Material.** PAHT-CF stays the production filament. PPA-CF is below its glass transition at 60 C, so the same geometry stays near or above the tube frame's torsional stiffness in a hot cab, while PAHT (Tg 45 C) does not. That is a feel difference the owner already accepted, not a strength failure, as long as the creep-rupture SF is at least 1. PPA costs the density ratio in mass, its Z elongation is 0.9 % (a cold-drop risk), it absorbs more water, and the TDS warns that annealing a large flat part can warp it. Use PPA only as a hot-climate alternate.

## Safety factors by load case

Strength SF is 1 / 99th-percentile layer failure index on the factored load, clamp and load-patch elements excluded (same rule as the study). Layer normal is frame y. This table is the 4 mm re-check. It runs low where a stay skin is a single voxel (set-down, and the 15 in hipbelt-off case). The 2 mm study of the same STL is the number the release uses: strength SF 1.45, fatigue 1.03.

| case | worst torso (in) | strength SF | FI99 |
|---|---:|---:|---:|
| static_carry | 15 | 1.45 | 0.69 |
| drop_2p5g | 15 | 0.97 | 1.03 |
| side_hill_torsion | 15 | 1.12 | 0.89 |
| single_stay_setdown | 15 | 0.59 | 1.69 |
| meat_straps | 23 | 1.97 | 0.51 |
| tall_load | 15 | 1.68 | 0.59 |
| overload_haul | 23 | 2.76 | 0.36 |
| tall_load_posts | 15 | 1.54 | 0.65 |
| hipbelt_off_abuse | 15 | 0.95 | 1.05 |

Fatigue SF uses the static-carry FI scaled from the factor-2.0 case down to 1.6 g, then divided into the fatigue ratio (0.3). Creep rupture uses the 1 g stress and `creep_rupture_8h_40c_ratio`.

## Pawl bushing

Governing link: **hipbelt_off_abuse|15**, factored force 0, 1913, 850 N (x, y, z). The cheek model uses the y-z resultant, split across two cheeks. ASSUMPTION: the pin is lateral (frame x), so a fore-aft load bears on the layer normal. The global voxel model smears this force over the whole housing, which is why the study's patch FI of ~1.25 was a warning and not the 99th-percentile check.

| option | cheek mm | hole mm | FI99 | bearing SF | metal SF | mass g | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| bare hole | 5 | 4.2 | 1.11 | 0.75 | — | 0.0 | no |
| bushing | 5 | 8.0 | 0.99 | 1.44 | 4.3 | 2.9 | yes |
| bushing | 8 | 8.0 | 0.64 | 2.30 | 6.9 | 9.9 | yes |
| bushing | 8 | 10.0 | 0.69 | 2.87 | 6.9 | 13.5 | yes |
| bushing | 10 | 12.0 | 0.56 | 4.31 | 10.3 | 23.7 | yes |

Bearing allowable is 0.8 × Z tensile (47 MPa), because the fore-aft pin load is normal to the layers. Metal allowable is annealed 304 yield (`sst_304_annealed`).

## Segment joint

The study's butt joint was one 5 mm × 50 mm-embed dowel per flange. Pull-out on meat_straps was SF 1.03. Production uses the same 6 MPa hot/wet MMA shear and adds dowels rather than raising the allowable. Shear SF below is dowel cross-shear only (the bonded butt, which the study also credited, is extra).

| set | side | flange N | pull-out SF | dowel shear SF |
|---|---|---:|---:|---:|
| drop_2p5g|19 | L | 3917 | 1.68 | 15.10 |
| drop_2p5g|19 | R | 3917 | 1.68 | 15.10 |
| side_hill_torsion|15 | L | 3572 | 1.85 | 16.19 |
| side_hill_torsion|15 | R | 2376 | 2.78 | 30.40 |
| meat_straps|23 | L | 4596 | 1.44 | 25.89 |
| meat_straps|23 | R | 4596 | 1.44 | 25.89 |
| hipbelt_off_abuse|19 | L | 1796 | 3.67 | 16.83 |
| hipbelt_off_abuse|19 | R | 1796 | 3.67 | 16.83 |

Section forces from this FEA at z = 234 mm (factored), flange force with a 24 mm lever (0.8 × 30 mm depth):

| set | side | N | M N·m | V | flange N |
|---|---|---:|---:|---:|---:|
| side_hill_torsion|15 | L | -458 | 61.1 | 203 | 2775 |
| side_hill_torsion|15 | R | -114 | 64.1 | 241 | 2727 |
| drop_2p5g|19 | L | -402 | 81.4 | 314 | 3594 |
| drop_2p5g|19 | R | -406 | 81.7 | 315 | 3607 |
| hipbelt_off_abuse|19 | L | 601 | 30.9 | 303 | 1589 |
| hipbelt_off_abuse|19 | R | 599 | 31.4 | 301 | 1608 |
| meat_straps|23 | L | -2 | 102.3 | 195 | 4262 |
| meat_straps|23 | R | -4 | 102.0 | 195 | 4251 |

The dowel count was checked against the larger of the study flange force and these FEA flange forces.

## Barrier

14 kPa is the prolonged-carriage interface-pressure limit quoted by Golriz et al., Work 58(4) (2017), doi:10.3233/WOR-172651. Wettenschwiler et al., PLOS ONE (2015), doi:10.1371/journal.pone.0142004, report that 20 kPa average shoulder pressure was uncomfortable for 90 % of soldiers (Bryant et al.) and that Holloway et al. saw occlusion near 16 kPa. The back panel can sit loaded for hours, so the design uses the lower pack-carriage figure, 14 kPa, on the walking case. Landis's 32 mmHg (4.3 kPa) capillary number is a bed-sore reference, not a pack limit.

Window from the SIMP mesh: 208 mm wide × 330 mm tall, cavity 30 mm (y), foam 6 mm (BP-02 XLPE). inner-edge gap and y-depth measured on genframe_assembled.stl; foam is panels.yaml BP-02.

Bone-end case, ASSUMPTION: 20% of 68 kg on one 22 mm patch. Walking (1.6 g) 213 N for skin pressure. Factored C5 (2.0 g × 1.5) 400 N for deflection and sheet stress. A 30 % share is in the results JSON as `sensitivity_share`.

Spanning mode: simply-supported plate (Navier, patch load) or a one-mode membrane, deflection under the factored load less than the stand-off, so the bone never reaches the foam. Bag-side stand-off is the cavity; wearer-side stand-off is the foam. Foam-backed mode: infinite plate on the XLPE Winkler foundation (k from 25 % compression at 60 kPa). Pass if the factored deflection stays inside the foam, the walking deflection uses less than half the foam, and the walking pressure is ≤ 14 kPa.

The membrane model multiplies deflection and stress by 1.5 because in-plane displacement was not freed (ASSUMPTION). Ripstop modulus 500 MPa and allowable 40 MPa are ASSUMPTIONS (crimp, not the yarn).

| concept | build | mount | mode | defl mm | pressure kPa | SF | mass g | pass |
|---|---|---|---|---:|---:|---:|---:|---|
| printed web | PAHT-CF web 3.20 mm | bag | spanning | 22.2 | 0.0 | 1.49 | 233 | yes |
| clip-in sheet | QI carbon sheet 2.00 mm | bag | spanning | 8.1 | 0.0 | 1.94 | 233 | yes |
| tensioned panel | UHMWPE film 1.20 mm | bag | spanning | 14.4 | 0.0 | 1.41 | 89 | yes |
| printed web | PAHT-CF web 4.00 mm | bag | spanning | 11.4 | 0.0 | 2.33 | 291 | yes |
| printed web | PAHT-CF web 5.00 mm | bag | spanning | 5.8 | 0.0 | 3.63 | 364 | yes |
| printed web | PAHT-CF web 5.00 mm | wearer | spanning | 5.8 | 0.0 | 3.63 | 364 | yes |
| clip-in sheet | QI carbon sheet 2.50 mm | bag | spanning | 4.1 | 0.0 | 3.03 | 286 | yes |
| clip-in sheet | QI carbon sheet 2.50 mm | wearer | spanning | 4.1 | 0.0 | 3.03 | 286 | yes |
| clip-in sheet | QI carbon sheet 3.20 mm | bag | spanning | 2.0 | 0.0 | 4.96 | 360 | yes |
| clip-in sheet | QI carbon sheet 3.20 mm | wearer | spanning | 2.0 | 0.0 | 4.96 | 360 | yes |
| tensioned panel | UHMWPE film 1.60 mm | bag | spanning | 14.5 | 0.0 | 1.38 | 115 | yes |
| tensioned panel | UHMWPE film 1.60 mm | bag | spanning | 13.2 | 0.0 | 1.68 | 115 | yes |

**Chosen:** UHMWPE film, 1.20 mm, bag side, spanning, 89 g. It is the lightest variant that passes.

## Surface and FEA

An elliptical loft of the SIMP sections was built and then rejected as the solid: on the slices the lumbar web and the stays are separate polygons about 30 mm apart, so the loft deleted the ligaments that carry the stay load into the hip pivot. The FEA solid is the SIMP mesh itself (element centers inside the STL) at 4 mm, with a one-voxel closing fillet and the sleeve bores re-cut. The section figure still shows the ellipse reading of each blob. Solved volume 441.5 cm³, 468 g in PAHT-CF. The print surface is that body with a longer Taubin smooth so the voxel steps of the original marching-cubes file are knocked down without moving the load path.

Cold torsion 0.44 N·m/deg vs tube 2.87 (ratio 0.15; feel limit 0.80). Mesh spacing is 4 mm. The study's sign-off mesh was 2 mm, so this check is coarser; the release gate is still the physical proof load in PRODUCTION.md.

## Heat

PAHT-CF stays the production filament. PPA-CF is below its glass transition at 60 C, so the same geometry stays near or above the tube frame's torsional stiffness in a hot cab, while PAHT (Tg 45 C) does not. That is a feel difference the owner already accepted, not a strength failure, as long as the creep-rupture SF is at least 1. PPA costs the density ratio in mass, its Z elongation is 0.9 % (a cold-drop risk), it absorbs more water, and the TDS warns that annealing a large flat part can warp it. Use PPA only as a hot-climate alternate.

The material call uses the 2 mm study torsion (0.94 of the tube frame cold). The 4 mm re-check measures a much softer frame because the sleeve wall is one voxel; that reading is not used here.

| | PAHT-CF | PPA-CF |
|---|---:|---:|
| Tg (C) | 45 | 85 |
| HDT 0.45 MPa (C) | 170 | 227 |
| cold torsion / tube | 0.94 | 2.87 |
| 40 C, 8 h creep / tube | 0.39 | 2.08 |
| 60 C, no creep / tube | 0.33 | 2.16 |
| plastic mass, this geometry (g) | 468 | 552 |
| Z elongation (%) | 5.2 | 0.9 |

PPA hot ratios are ASSUMPTIONS (no published E(T)): both 40 C and 60 C are below Tg 85 C. PAHT `modulus_60c_ratio` 0.35 is an ASSUMPTION above Tg, from the DMA note in the study.

## Mass

| part | g |
|---|---:|
| printed body | 468.0 |
| segment dowels | 17.0 |
| pawl bushings and wall | 9.9 |
| meat barrier | 89.0 |
| kept crown, rack, pawl, guides, Ti mount, UHMWPE bushings | 204.6 |
| inserts and screws | 10.8 |
| **frame** | **799** |
| soft goods (2224.1 − 569.2) | 1654.9 |
| **pack** | **2454 (5.41 lb)** |

Study headline was 718 g and 2373 g (5.23 lb). Target 2268 g.

## Screenshots

- `/workspace/outputs/screens/20261101_prodframe_1_pawl_joint.png`
- `/workspace/outputs/screens/20261101_prodframe_2_barrier.png`
- `/workspace/outputs/screens/20261101_prodframe_3_surface_sections.png`
- `/workspace/outputs/screens/20261101_prodframe_5_fea.png`
- `/workspace/outputs/screens/20261101_prodframe_6_heat_mass.png`
- `/workspace/outputs/screens/20261101_prodframe_4_surface_3d.png`

## Assumptions

- ASSUMPTION: pawl pin is lateral (frame x); the factored y-z force is split across two cheeks.
- ASSUMPTION: MMA on treated nylon is 6 MPa hot/wet (study). T6 coupons still have to confirm it.
- ASSUMPTION: dowel shear SF ignores the bonded butt face, so it is a lower bound.
- ASSUMPTION: bone end is 20 % of 68 kg on a 22 mm patch. Walking pressure uses 1.6 g; strength uses C5's 2.0 g x 1.5.
- ASSUMPTION: XLPE is a linear Winkler foundation up to 50 % compression, k from the 25 % stress in xlpe_foam.
- ASSUMPTION: membrane deflection and stress are 1.5 x the one-mode von Karman result.
- ASSUMPTION: 210D ripstop membrane modulus 500 MPa and allowable 40 MPa.
- ASSUMPTION: PAHT modulus at 60 C is 0.35 of room temperature (above Tg). PPA ratios are in ppa_cf_fdm.yaml.
- ASSUMPTION: insert and screw mass 10.8 g; bushing price $4 each; machine $1/h; reprint allowance 15 %.
- ASSUMPTION: effective print flow 8 mm3/s and 8 % waste, carried over from the study.
- The 4 mm inside-test uses a quadric-decimated copy of the STL (about 9k faces). It agrees with the full mesh on a spot check and its volume is within a few percent.
- A one-voxel skin on a stay in that 4 mm mesh produces a false set-down spike (hundreds of MPa). The body was not grown to erase it. The 2 mm study remains the strength sign-off.
