# BL-075 H1-P hip through-bolt stack: clearance to bag, lumbar pad and hipbelt

**Agent:** pack-designer · **Size:** S · **Depends on:** BL-073 (`iter1/frame/bl070_h1p.json` `h1p.hip_mount`) · **Date:** 2026-11-25

Ask: check whether the BL-073 hip stack (6061 ring 2 mm, A2 M5 nuts, printed nut keeper, Ti M5 x 35 tails, about
10 mm aft of the D50 boss's flat back) clears CORRIE F rev 3's bag body and frame interface, the lumbar pad foam and
the hipbelt wrap. Check whether any tail can press into the wearer or wear through fabric, and pick the lightest fix
that works.

## Result (pack-designer, 2026-11-25)

- **Clears. Fix: none, 0 g. Keep the stock Ti M5 x 35.** Record: `designs/pack_5200/iter1/system/bl075_hip_clearance.md`.
- Aft (+y, FCS) is away from the wearer. The tails point into the frame window toward the bag. 25 mm of PPA-CF boss
  and Ti base lie between them and the belt, the lumbar pad and the wearer. BL-073 did not change the screw heads
  (21.6 mm below the hub face).
- Tail tips at y -16.5 sit 22.0 mm from the spreader (18.5 mm after its 3.53 mm factored sag at x 0, z 124) and
  33.9 mm from bag panel B-01. For B-01 to bulge that far into the bay below the spreader it would need 46 % strain.
  The frame body is 6.1 mm from the tails, 1.9 mm from the nuts and 0.95 mm from the keeper.
- The hipbelt bow-tie, its wrap and its ±8 deg roll all stay wearer-side of the mount face. The pad-seat top sleeve
  sits 45 mm above the stack. **DECISION BL075-CORD:** the f1 cord tie runs round the lower struts outboard of
  |x| 35 and never across the boss back.
- Alternatives: M5 x 30 does not fully engage the nut. Cutting to 34 mm saves 0.53 g, which is not worth the
  extra step. 8 TPU caps (+1.45 g) are the fallback if T1 leaves a witness mark. A closed keeper cover is +3.65 g.
  A B-01 doubler is +0.48 g. A lumbar foam relief cut does nothing, because the foam is on the wrong side.
- Found, not fixed: the keeper (OD 48.5) sits in the D49 spot face with about 0.25 mm radial play against the strut
  lip, so dry fit it or sand it. The pad seat (`corrie.PAD_SEAT`) is still sized for the v2 CF pan and needs an H1
  fit check (HB-D3).
- Files: `designs/pack_5200/iter1/system/bl075_hip_clearance.{py,json,md}`, `tests/test_bl075_hip_clearance.py`
  (4 passed), `outputs/screens/20261125_bl075_1.png`.
