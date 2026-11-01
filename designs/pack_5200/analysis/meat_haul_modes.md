# Meat haul, both modes required

Owner, 2026-11-01: both modes are requirements. The eight B-01 swells are accepted.
IM1 stays a meat anchor only, for now. The hook proof test is still open.
Code: `huntkit/gendesign/meat_haul.py`.

The bearing face in every mode is the **2.0 mm QI carbon spreader** on the bag side of the
stays. Bone and the cinch land on the sheet. The sheet delivers them to the stay rails.
The mesh over the air gap is not a meat support. The wearer stays on the XLPE rails.

Spreader, from the comfort check (20 % of 68 kg on a 22 mm bone, factored): stress SF **1.95**,
peak skin pressure **10.6 kPa**, factored deflection **7.8 mm**.
A 36 kg quarter is inside that check.

## A. Bag on (required)

Meat stays in the bag. IM1–IM3 pass through the B-01 ports, hook to the eyes on the cleat pins,
and cam tight. The meat is squeezed against the spreader. The bag floor carries the vertical
share into the hinge pins at z 60.

Load path: meat → strap → hook → eye → pin → fairlead → stay. Face pressure → spreader → stay rails.

This is the HA-LS-1 `meat_straps` resolution. The cleat FEA was run on these forces.
Branch-frame SF on that case is **2.49**.

| station | force N | strength SF | fatigue SF |
|---|---:|---:|---:|
| hinge | 726 | 2.97 | 1.67 |
| im1 | 267 | 8.10 | 4.56 |
| im2 | 403 | 5.37 | 3.02 |
| im3 | 554 | 3.91 | 2.20 |

Hook and cam are checked against the larger of the factored cleat force and the published
605 N strap demand (2 × the 303 N service leg). Hook SF **2.48**. Cam SF **1.82**.
Webbing SF **33**. Bartack SF **3.72**. The cam rating is an assumption.

### A2. Between the bag and the frame (viable, part of bag-on)

Bulk meat does not have to go inside the tube of the bag. Release the four bag hooks at IM2 and
IM3. Leave the hinge pins in. The bag swings open about z 60. At IM3 the opening used here is
250 mm, which is **29°**. The wedge is then 71 mm at IM1,
147 mm at IM2 and 250 mm at IM3. A quarter fits,
thick end high, where the wedge is widest. The narrow end at the lumbar is the hock.

The captive eyes stay on the pins. The meat straps hook to those eyes across the meat, and the
meat bears on the spreader, not on the wearer's back. W1–W3 close the bag onto the wedge.
They are the outer clamp. They are not the meat anchor.

Head clearance gets easier: the bag moves aft, away from the head. The head setback on B-01
is for the closed bag.

Load path: meat → spreader for the face, → IM straps for the cinch and the overturning,
→ hinge pins for the share that still sits on the tilted floor.
ASSUMPTION: floor share 0.40 (the closed bag uses 0.70) and the CG is 110 mm aft of the frame,
because the wedge is shallower than the full bag.

| station | force N | strength SF | fatigue SF |
|---|---:|---:|---:|
| hinge | 444 | 4.84 | 2.72 |
| im1 | 309 | 7.01 | 3.95 |
| im2 | 388 | 5.58 | 3.14 |
| im3 | 496 | 4.37 | 2.46 |

Minimum cleat fatigue SF **2.46**. Hook SF **3.03**.
The hinge sees 444 N, under the 726 N it was checked at.
IM1 sees 309 N against 267 N with the bag closed. Both sit under the
cleat that was checked at 554 N aft. **Viable.** A bone-in quarter rides here with the bag
still on the frame.

## B. Bag off (required)

The bag comes off. A quarter lies on the spreader. IM1, IM2 and IM3 hook eye-to-eye over it
and cam tight. There is no bag floor, so the weight is held by friction between the meat and
the sheet. μ 0.4 is the wet game-bag assumption already in `geometry.yaml`.

### Procedure (gloves, about 34 s, limit 2 min)

1. Unhook the four bag hooks (IM2 and IM3, both sides). IM1 has no bag hook.
2. Pull the two tethered hinge pins at z 60. The eyes for the meat straps stay on the other six pins.
3. Lift the bag clear and set it aside.
4. Lay the quarter on the spreader, bone against the sheet. The open window is mesh and air. It is not the bed.
5. Hook IM1, IM2 and IM3 from eye to eye over the meat. Cam tight. A hock can sit on IM1.
6. W1 and W2 can go over the top as a second clamp. They are not required for the friction sum below. W3 lashes a tall load to the crown.

Walking peak of 36 kg is **565 N**. With only the three IM straps, each leg needs **235 N**
so the cinch does not slip. Adding W1 and W2 drops that to **141 N**, which is the
141 N figure already in `geometry.yaml`. The strength check uses 1.5 times the three-strap tension,
**353 N** per leg, aft, on each cleat.

| station | force N | strength SF | fatigue SF |
|---|---:|---:|---:|
| im1 | 353 | 6.14 | 3.45 |
| im2 | 353 | 6.14 | 3.45 |
| im3 | 353 | 6.14 | 3.45 |

Hook SF **4.25**. Cam SF **3.12**. Webbing SF **57**.
Cleat fatigue SF **3.45**, scaled from the IM3 fairlead because the pull is aft.
The factored leg, 353 N, is under the 554 N aft load that cleat was
checked at. IM1 in this mode is 353 N, which is above the 267 N
that station sees with the bag closed, and still under that checked cleat. The branch-frame
`meat_straps` SF **2.49** is the bag-on number. This bare-frame pull does not add a
heavier case than that check at IM3 or the hinge. The spreader check above was run on a heavier
bone than a 36 kg quarter.

To put the bag back: set the hinge eyes on the pins, clip IM2 and IM3, about 70 s.

## What is still open

- Hook break strength is an assumption (1500 N). Proof-test five to 830 N before the first sewn bag.
- IM1 does not get a bag clip yet. It is a meat anchor only until the owner says otherwise.

## Screenshots

- `/workspace/docs/screens/20261101_attach_5_bag_on.png`
- `/workspace/docs/screens/20261101_attach_6_between.png`
- `/workspace/docs/screens/20261101_attach_7_bag_off.png`
