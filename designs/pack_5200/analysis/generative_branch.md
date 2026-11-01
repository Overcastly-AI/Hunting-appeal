# Generative branch frame

The production frame is printed again. The carbon-tube ladder is not the product. Code: `huntkit/gendesign/frame_branch.py`.

## Recommendation

One **PAHT-CF branching body**. Each stay splits into the sleeve limb and an inboard branch, filleted back together. Lumbar struts run from the hip pivot into the stays. The surface is a smooth distance field, not a voxel lattice.

- Printed body **774 g**. Frame **1194 g**. Pack **2865 g (6.32 lb)**.
- Fine check is the **2 mm** mesh (a 4 mm wall is two elements, not a one-voxel skin). Minimum SF **1.66** (hipbelt_off_abuse|15). Fatigue **1.10**. Creep-rupture **2.35**.
- Comfort unchanged: carbon spreader, peak **10.6 kPa**, spread **100 mm**.
- Print time about **27 h**. Material cost about **$208**.

5.0 lb is missed by **597 g**. The floor under this architecture is the soft goods (1655 g), the carbon crown and rack (205 g), the spreader (193 g) and a printed sleeve that has to wrap an 18 mm bore. Those four lines already sit on the target before the branches and the lumbar struts. Closing the gap means a lighter spreader that still meets 14 kPa, or a lighter crown, not a thinner stay skin.

## Why this and not the others

- The solid ladder passes and looks smooth, and it is 1734 g because the stays are ~34 mm across.
- The tube ladder is lighter and was rejected. The frame has to read as a generative print.
- A printed plate can replace the carbon spreader. The lightest one that still spreads a bone is PAHT web 4.0 mm, full span, 10 mm stay pads, at 289 g added versus 193 g for the carbon sheet. It is the heavier comfort part.
- A gyroid core inside a thick stay does not remove the wall that carries bending, and it reads as fill, not as a branch. It was not used.
- Annealing does not change density. PPA-CF is stiffer when hot and about 18 % denser, so it is not a mass path. The filament stays PAHT-CF.
- A carbon liner inside the sleeve was looked at. The crown leg already fills the 18 mm bore, so a liner only thickens that wall. It does not remove the printed socket.

## Safety factors (2 mm, worst torso)

| case | SF |
|---|---:|
| static_carry | 2.93 |
| drop_2p5g | 1.95 |
| side_hill_torsion | 2.66 |
| single_stay_setdown | 3.24 |
| meat_straps | 2.49 |
| tall_load | 2.73 |
| overload_haul | 3.50 |
| tall_load_posts | 2.70 |
| hipbelt_off_abuse | 1.66 |

Fatigue SF **1.10**. Creep-rupture SF **2.35**.

## Options

| option | frame g | pack lb | min SF | fatigue | peak kPa | spread mm | print h | pass |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Solid PAHT ladder | 1734 | 7.51 | 1.39 | 2.28 | 10.6 | 100 | 45.7 | yes |
| Carbon-tube ladder (rejected) | 763 | 5.37 | 1.04 | 1.18 | 10.6 | 100 | 1.6 | no |
| Branch frame + carbon spreader | 1194 | 6.32 | 1.66 | 1.10 | 10.6 | 100 | 27.4 | yes |
| PAHT web 4.0 mm, full span, 10 mm stay pads | 1265 | 6.47 | 1.66 | 1.10 | 10.6 | 100 | 36.8 | yes |

## Screenshots

- `/workspace/docs/screens/20261101_gen_1_options.png`
- `/workspace/docs/screens/20261101_gen_2_views.png`
- `/workspace/docs/screens/20261101_gen_3_mass.png`
- `/workspace/docs/screens/20261101_gen_4_fea.png`

## Assumptions

- Bone end is 20 % of 68 kg on a 22 mm patch. The carbon spreader hangs on it.
- The crown stays the carbon telescoping crown. A printed crown was already rejected on creep and stiffness.
- Pawl pin runs side to side. The 304 sleeve in the cheek still stands.
- No segment joint: the body is printed as two pieces only if the slicer has to split it. The check is of the whole body.
- Fatigue ratio 0.3 and the 0.8 hot/wet knockdown are the PAHT study assumptions.
