# Mass cut: keep the back, drop the solid nylon stays

Superseded the same day. The owner rejected the carbon-tube ladder: the product has to read as a generative print. Production is `generative_branch.md`. The numbers below stay as the comparison.

The back system does not change: 2.0 mm QI carbon spreader, two 100 × 420 × 10 mm XLPE rails, mesh over the air gap. Peak skin pressure **10.6 kPa**, spread **100 mm**. Code: `huntkit/gendesign/frame_light.py`.

The solid smooth ladder (1291 g of PAHT, pack 7.51 lb, about 46 h to print) is retired as the structure. Hollowing that same outer shape saves almost nothing: the section is already about as thick as an 8 mm wall. A real hollow stay is a smaller tube, checked here as a beam.

## Recommendation

**Carbon-tube ladder.** v2 stays, bars, lumbar plate and crown, plus the carbon spreader and the foam rails. The wrapped nodes and foot boots are the fairing. Nothing extra is printed to imitate the solid ladder.

- Frame **763 g**. Pack **2434 g (5.37 lb)**.
- Minimum SF/required **1.04** (hipbelt_off_abuse). Fatigue SF **1.18**.
- Comfort peak **10.6 kPa**, spread **100 mm**.
- Print time about **1.6 h** (the rack, pawl and guides, not the stays).
- Material cost about **$206**. Most of that is tubes, the lumbar plate, the Ti mount and the spreader, not filament.

5.0 lb (2268 g) is still missed, by about **166 g**. The tube frame was already 569 g before the spreader. The spreader is 193 g and the comfort check does not let it get thinner. Soft goods are 1655 g. Those three lines are the pack. A lighter frame than the carbon tubes did not pass.

## Options

| option | frame g | pack lb | min SF/req | fatigue | peak kPa | spread mm | print h | cost USD | pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Solid PAHT ladder (retired) | 1734 | 7.51 | 1.39 | 2.28 | 10.6 | 100 | 45.7 | 206 | yes |
| PAHT stays OD 26 × 3.5 mm | 961 | 5.80 | 1.06 | 0.98 | 10.6 | 100 | 11.4 | 190 | no |
| PAHT stays OD 28 × 4 mm | 1022 | 5.94 | 1.07 | 1.19 | 10.6 | 100 | 13.5 | 196 | yes |
| Carbon tubes + 1.2 mm fairing | 905 | 5.68 | 1.04 | 1.18 | 10.6 | 100 | 6.6 | 218 | yes |
| Carbon-tube ladder | 763 | 5.37 | 1.04 | 1.18 | 10.6 | 100 | 1.6 | 206 | yes |

SF/req is the beam-model member safety factor divided by the HA-LS-1 factor, worst of 15, 19 and 23 in. The retired solid ladder's 1.39 was a 4 mm voxel layer-index on factored loads, a different model of a different frame. Both numbers mean the same thing when they are above 1: the factored allowable is met. Fatigue for carbon is half the knocked-down first-ply strength at the 1.6 g walking stress. Fatigue for a PAHT stay is 0.3 of the knocked-down tensile strength.

### Carbon-tube ladder by case

| case | SF/req | where |
|---|---:|---|
| static_carry | 1.88 | lumbar_plate (15 in) |
| drop_2p5g | 1.26 | lumbar_plate (15 in) |
| side_hill_torsion | 1.54 | lumbar_plate (19 in) |
| single_stay_setdown | 2.77 | mid_bar (19 in) |
| meat_straps | 1.46 | crown_leg_R (23 in) |
| tall_load | 1.42 | lumbar_plate (15 in) |
| overload_haul | 2.04 | crown_leg_L (23 in) |
| tall_load_posts | 1.38 | lumbar_plate (15 in) |
| hipbelt_off_abuse | 1.04 | upper_bar (15 in) |

## Why the others lose

- **Solid PAHT ladder (retired).** The current print. Every case passes and it is the heaviest, slowest option. Pack 7.51 lb, SF/req 1.39, fatigue 2.28.
- **PAHT stays OD 26 × 3.5 mm.** Thinner than the stay that passes. Fatigue of the upper stay is under 1. Pack 5.80 lb, SF/req 1.06, fatigue 0.98.
- **PAHT stays OD 28 × 4 mm.** Lightest hollow PAHT stay that clears strength and fatigue. The carbon tubes it replaces weigh 80 g; these weigh more, so the pack goes up. Pack 5.94 lb, SF/req 1.07, fatigue 1.19.
- **Carbon tubes + 1.2 mm fairing.** Same structure as the carbon ladder. The skin is not in the strength check. It adds mass to hide a tube that is already round. Pack 5.68 lb, SF/req 1.04, fatigue 1.18.

## Cost (production frame)

| item | USD |
|---|---:|
| stays OD 20, 2 x 525 mm | 39.38 |
| crown legs OD 16, 2 x 430 mm | 25.80 |
| mid bar OD 18 | 7.09 |
| upper bar OD 22 | 8.66 |
| crown top bar OD 18 | 7.22 |
| spine OD 20 | 11.25 |
| lumbar plate material (record, scaled by thickness) | 8.31 |
| wrap fabric, epoxy, shrink tape (ASSUMPTION) | 25.00 |
| MMA | 2.00 |
| 7075 foot boots (ASSUMPTION) | 8.00 |
| UHMWPE bushings (ASSUMPTION) | 5.00 |
| SLM Ti hip mount, 20 g (ASSUMPTION $35) | 35.00 |
| PAHT rack, pawl, guides | 3.80 |
| machine, rack only | 1.56 |
| QI carbon spreader, 2.0 mm | 14.56 |
| XLPE rails | 3.00 |
| **total** | **205.63** |

Tube price starts at the `cfrp_rollwrapped_tube` record, $30/m at about 16 mm, and scales with diameter. That is an estimate, not a quote. The wrap kit, boots, bushings and the Ti mount are marked ASSUMPTION. Print time is the 44 g rack at 8 mm³/s.

## Screenshots

- `/workspace/docs/screens/20261101_light_1_options.png`
- `/workspace/docs/screens/20261101_light_2_frame_views.png`
- `/workspace/docs/screens/20261101_light_3_mass.png`
- `/workspace/docs/screens/20261101_light_4_fea.png`

## Assumptions still in force

- Bone end is 20 % of 68 kg on a 22 mm patch. The spreader thickness hangs on it.
- 5.36 lb is not 5.0 lb. The gap is real.
- Small printed parts (rack, pawl, guides) stay PAHT-CF. The stays are not printed.
- The pawl pin runs side to side.
- Lumpy-gear corner is 8 kg on 40 mm.
- MMA bond shear stays 6 MPa hot/wet until the T6 coupons exist. The tube-frame joint screen is above 1; the coupon still governs the release.
- PAHT fatigue ratio 0.3 and the carbon half-strength fatigue screen are the study assumptions, not a measured S-N curve for this layup.
