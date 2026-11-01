# Back comfort and the smooth frame

Owner priority (PR #2): the open window still lets meat, bone ends and lumpy gear push on the back. Comfort outranks mass. Code: `huntkit/gendesign/frame_smooth.py`.

## Comfort criterion

Peak skin pressure ≤ **14 kPa** and pad average ≤ **8 kPa** at the 1.6 g walking peak. A point load must spread at least **40 mm** at the skin (half-width of the foam patch or the foundation length). Under the factored bone load the hard sheet must not deflect through the pad standoff (foam thickness + 4 mm). Cases: meat-strap normal force, a bone end (20% of 68 kg on a 22 mm patch), and a lumpy corner (ASSUMPTION 8 kg on 40 mm).

14 kPa is the prolonged-carriage limit quoted by Golriz et al., Work 58 (2017). 20 kPa was uncomfortable for 90 % of soldiers (Bryant, via Wettenschwiler, PLOS ONE 2015). The old check only asked whether the sheet moved less than the frame depth. A soft sheet can pass that and still print a point load into the back. This check uses the pressure.

Walking meat normal force on the frame face: **679 N**. Bone, walking: **213 N**. Bone, factored: **400 N**. Lumpy corner, walking: **126 N**.

## Recommendation

**QI carbon 2.0 mm, full span, 10 mm stay pads.** Bought framesheet. Air gap between the two pad rails.

- Peak skin pressure **10.6 kPa** (limit 14). Pad average **8.1 kPa**.
- Bone-load spread at the skin **100 mm**.
- Factored sheet deflection **7.8 mm**. Mode: load into the stay pads.
- Added mass **218 g** (sheet 193 g, foam 28 g). The 8.1 kPa average is the meat normal spread over the two rails, on the 8 kPa target.
- Ventilation: about **42 %** of the lower back is an open channel (mesh over an air gap), not foam clamped on the spine.

The 1.2 mm UHMWPE sheet is retired. On a foam foundation its walking bone pressure is the first row below, far over 14 kPa. The cavity argument (14 mm deflection, 30 mm of air) does not describe what the back feels: the panel is a hammock across the window.

Construction:

- Two **stay pads**, 100 mm wide, 10 mm XLPE, on the wearer face of the stays, about 420 mm long. Spacer mesh over the pads only.
- A **light center strip** of 6 mm foam is not used as the structure. The lumbar pad on the hipbelt still carries the belt. Between the stay pads the back panel is open spacer mesh over the air gap.
- The **spreader** sits recessed on the bag side of the stays, clipped at the stay nodes (the meat anchors are already there). Strap cinch and a bone end both land on the spreader, which delivers them to the stays. The pads, not the window, touch the wearer.
- Meat straps stay on IM1–IM3 at the stay nodes. The change is the panel behind the meat: it is no longer a single 6 mm foam sheet spanning the hole.

## Options

| option | peak kPa | avg kPa | spread mm | defl mm | mass g | vent | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| UHMWPE 1.2 mm on 6 mm foam (current, foam in the window) | 475.2 | 20.2 | 19 | 11.9 | 78 | 0.05 | no |
| Stay pads only, open window | 561.4 | 10.1 | 22 | — | 19 | 0.55 | no |
| QI carbon 1.6 mm, full span, 10 mm stay pads | 31.8 | 8.1 | 72 | 15.2 | 179 | 0.42 | no |
| QI carbon 2.0 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 7.8 | 218 | 0.42 | yes |
| QI carbon 2.5 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 4.0 | 266 | 0.42 | yes |
| QI carbon 3.2 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 1.9 | 334 | 0.42 | yes |
| PAHT web 2.5 mm, full span, 10 mm stay pads | 54.6 | 8.1 | 55 | 44.9 | 190 | 0.42 | no |
| PAHT web 3.2 mm, full span, 10 mm stay pads | 37.7 | 8.1 | 66 | 21.4 | 236 | 0.42 | no |
| PAHT web 4.0 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 11.0 | 289 | 0.42 | yes |
| PAHT web 5.0 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 5.6 | 355 | 0.42 | yes |
| 6061 sheet 2.0 mm, full span, 10 mm stay pads | 10.6 | 8.1 | 100 | 5.0 | 361 | 0.42 | no |
| HDPE 3.2 mm, full span, 10 mm stay pads | 68.4 | 8.1 | 49 | 70.6 | 215 | 0.42 | no |
| QI carbon 1.2 mm + center rib (span 104 mm) | 10.6 | 8.1 | 100 | 9.9 | 195 | 0.42 | no |
| QI carbon 1.6 mm + center rib (span 104 mm) | 10.6 | 8.1 | 100 | 4.2 | 234 | 0.42 | yes |
| QI carbon 2.0 mm + center rib (span 104 mm) | 10.6 | 8.1 | 100 | 2.1 | 273 | 0.42 | yes |
| PAHT 2.5 mm + center rib (span 104 mm) | 10.6 | 8.1 | 100 | 12.3 | 245 | 0.42 | no |
| PAHT 3.2 mm + center rib (span 104 mm) | 10.6 | 8.1 | 100 | 5.8 | 291 | 0.42 | yes |

A row fails when the skin peak is over 14 kPa, the factored sheet deflection exceeds the pad standoff (foam thickness + 4 mm), the load spreads less than 40 mm, or the sheet stress safety factor is under 1.3. The 6061 sheet meets the pressure numbers and still fails on yield. Carbon at 1.6 mm clears the stress check and still bottoms into the foam (15 mm against a 14 mm standoff).

## Smooth frame

Stays are superellipses on the crown-sleeve centerline, filleted into an 8 mm lumbar pan, a mid bar and an upper bar. Sections are solid: at least 20 mm across, and 34 mm across where the 9 mm sleeve bore passes, so the wall is 8 mm (two 4 mm voxels, not a one-voxel skin). The print surface is marching cubes on that smooth field at 2 mm, then a short Taubin pass.

Printed body **1291 g**. Frame **1734 g**. Pack **3406 g (7.51 lb)**.

### Safety factors (4 mm, worst torso)

| case | SF |
|---|---:|
| static_carry | 6.07 |
| drop_2p5g | 4.05 |
| side_hill_torsion | 5.21 |
| single_stay_setdown | 5.01 |
| meat_straps | 4.87 |
| tall_load | 4.94 |
| overload_haul | 6.83 |
| tall_load_posts | 4.50 |
| hipbelt_off_abuse | 1.39 |

Minimum strength SF **1.39** (hipbelt_off_abuse|15). Fatigue SF **2.28**. Creep-rupture SF **4.85**. Cold torsion 1.88 of the tube frame.

Fatigue uses the same definition as the production pass: 0.3 × knocked-down strength against the 1.6 g walking stress taken from the factored static case.

## Mass

Comfort was not traded away to save grams. Savings outside that system: the SIMP lumps and the 1.2 mm UHMWPE sheet are gone; the new sheet replaces the UHMWPE. The smooth stays are thicker than the one-voxel skins, which is why the body mass moved.

| part | g |
|---|---:|
| smooth printed body (stays, lumbar pan, bars) | 1291 |
| segment dowels | 17 |
| pawl bushings and cheek | 10 |
| spreader sheet | 193 |
| foam pads minus the old full sheet | 16 |
| kept crown, rack, pawl, guides, Ti mount | 205 |
| inserts and screws | 19 |

## Screenshots

- `/workspace/docs/screens/20261101_back_1_comfort_options.png`
- `/workspace/docs/screens/20261101_back_2_pressure_maps.png`
- `/workspace/docs/screens/20261101_frame_4_fea.png`
- `/workspace/docs/screens/20261101_frame_2_smooth_views.png`
- `/workspace/docs/screens/20261101_frame_3_before_after.png`

## Assumptions still in force

- Bone end is 20 % of 68 kg on a 22 mm patch. A larger share thickens the sheet.
- 5.41 lb was not accepted. The pack mass above replaces it; it is still over 5.0 lb.
- Production filament stays PAHT-CF. The sheet may be carbon (bought) or PAHT (printed); the table is the choice.
- The pawl pin runs side to side.
- Lumpy-gear corner is 8 kg on 40 mm (ASSUMPTION).
- Pad pressure uses the rev B overturning couple and two strap levers (80 mm and 280 mm).
- Foam is linear up to 25 % compression (`xlpe_foam`, 60 kPa).
