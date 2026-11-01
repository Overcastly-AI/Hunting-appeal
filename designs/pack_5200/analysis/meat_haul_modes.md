# Meat haul, both modes required

Owner, 2026-11-01: both modes are requirements. The eight B-01 swells are accepted.
IM1 stays a meat anchor only, for now. The hook proof test is still open.
Code: `huntkit/gendesign/meat_haul.py`.

The bearing face in every mode is the **2.0 mm QI carbon spreader** on the bag side of the
stays. Two **38 mm under-straps** also run under the bag, from fairleads at z 95 and
z 142. With the bag on they cinch the floor up to the frame, and the bag shell shares
the vertical load with the hinge pins. With the bag off they are the cradle, so the quarter
does not hang on friction alone. IM1–IM3 still cinch the meat against the spreader.

Each strap is a sewn eye on the left pin, under the floor, and a 38 mm cam on the right pin.
A tri-glide sits behind the cam so a slip cannot lengthen the cradle. The belly under the
anchor line is specified at **70 mm**, which keeps the side legs at
**31°** and the cam inside its assumed slip rating.
25 mm webbing was set aside: its ladder lock slips at 300 N and its side-release breaks at
450 N, both under the factored cradle tension.

Spreader, from the comfort check (20 % of 68 kg on a 22 mm bone, factored): stress SF **1.95**,
peak skin pressure **10.6 kPa**, factored deflection **7.8 mm**.
A 36 kg quarter is inside that check.

Of the bag-floor vertical, **55%** moves onto the under-straps and the rest stays
on the hinge pins (ASSUMPTION). The lower strap takes 60% of that cradle load.

## A. Bag on (required)

Meat stays in the bag. IM1–IM3 hook to the cleat eyes and cam the meat against the spreader.
The two under-straps run through open channels in the bag floor and are cammed tight, so the
floor is a sling between the hinge pins and the cradle anchors.

Load path: meat → bag floor → under-straps and hinge pins for the vertical share. IM straps →
cleats for the cinch and the overturning. Face pressure → spreader → stay rails.

Branch-frame SF on `meat_straps` is **2.49**. Under-strap tension **444 N**,
cam SF **2.48**, webbing SF **45**.

| station | force N | strength SF | fatigue SF |
|---|---:|---:|---:|
| hinge | 368 | 5.85 | 3.29 |
| us1 | 444 | 3.60 | 1.62 |
| us2 | 296 | 5.41 | 2.43 |
| im1 | 267 | 8.10 | 4.56 |
| im2 | 403 | 5.37 | 3.02 |
| im3 | 554 | 3.91 | 2.20 |

Hook and cam on the IM straps are checked against the larger of the factored IM force and the
published 605 N strap demand. Hook SF **2.48**. IM-cam SF **1.82**.
The under-strap cam is the line above, not this one. Bartack SF **4.46**.

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
| hinge | 264 | 8.15 | 4.58 |
| us1 | 254 | 6.31 | 2.84 |
| us2 | 169 | 9.46 | 4.26 |
| im1 | 309 | 7.01 | 3.95 |
| im2 | 388 | 5.58 | 3.14 |
| im3 | 496 | 4.37 | 2.46 |

Minimum cleat fatigue SF **2.46**. IM hook SF **3.03**.
Under-strap tension **254 N**, cam SF **4.33**.
The hinge, after the cradle takes its share, sees 264 N.
**Viable.** The under-straps stay cammed, so the open bag floor does not dump the low end of the quarter.

## B. Bag off (required)

The bag comes off. The two under-straps stay on the frame and become the cradle. The quarter
sits in them. IM1–IM3 still hook eye-to-eye and cam the meat against the spreader so it cannot
tip off the cradle. Friction is only a reserve. μ 0.4 and the old 141 N leg (five straps) are
the reserve numbers, not the design path.

### Procedure (gloves, about 40 s, limit 2 min)

1. Pop the two under-strap cams and lift the bag floor out of the open channels. The straps stay on their pins. About 6 s.
2. Unhook the four bag hooks (IM2 and IM3, both sides). IM1 has no bag hook.
3. Pull the two tethered hinge pins at z 60.
4. Lift the bag clear.
5. Set the quarter in the cradle, bone toward the spreader. Cam the two under-straps until the belly is about 70 mm.
6. Hook IM1–IM3 eye-to-eye over the meat and cam them. A hock can sit on IM1.

Walking peak of 36 kg is **565 N**. The strength check is 1.5 times that,
**847 N**, all of it in the cradle. Lower strap tension
**489 N**. Cam SF **2.25**.
The IM cinch used here is the 150 N hand tension times 1.5, **225 N** per leg.
Hook SF on that cinch **6.67**.

| station | force N | strength SF | fatigue SF |
|---|---:|---:|---:|
| us1 | 489 | 3.28 | 1.47 |
| us2 | 326 | 4.91 | 2.21 |
| im1 | 225 | 9.63 | 5.42 |
| im2 | 225 | 9.63 | 5.42 |
| im3 | 225 | 9.63 | 5.42 |

The cradle anchors are the same fairlead as the hinge, on the solid lower stay. Their fatigue
SF is scaled from the fine-mesh solve of the governing cradle vector when that solve is on file,
and from the hinge solve otherwise (`cradle_fea`).

To put the bag back: pins in, bag hooks on, floor channels over the cradle straps, cams tight.
About 80 s.

## What is still open

- Hook and cam ratings are assumptions (hook 1500 N, cam slip 1100 N). Proof-test five of each to 830 N before the first sewn bag. The under-strap cam is in this test.
- IM1 does not get a bag clip yet. It is a meat anchor only until the owner says otherwise.

## Mass and cost of the under-straps

| part | g |
|---|---:|
| printed anchors (4) | 22.8 |
| 7075 pins (4) | 9.6 |
| UHMWPE sleeves (4) | 1.2 |
| 38 mm cams (2) | 44.0 |
| tri-glide keepers (2) | 6.0 |
| 38 mm webbing, 1.10 m | 30.8 |
| bag-floor channels | 8.0 |
| **added** | **122** |

About **$22** on top of the fairlead set. Detach time **40 s** (the two cam pops are about 6 s of that). Pack with the cradle is the previous 2979 g plus this added mass.

## Screenshots

- `/workspace/docs/screens/20261101_attach_8_cradle_anchors.png`
- `/workspace/docs/screens/20261101_attach_9_cradle_bag_on.png`
- `/workspace/docs/screens/20261101_attach_6_between.png`
- `/workspace/docs/screens/20261101_attach_10_cradle_bag_off.png`
- `/workspace/docs/screens/20261101_attach_11_cradle_fea.png`
