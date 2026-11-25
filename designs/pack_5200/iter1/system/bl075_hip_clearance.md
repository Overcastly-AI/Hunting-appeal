# BL-075 H1-P hip through-bolt stack: clearance to the bag, the lumbar pad and the hipbelt

pack-designer, 2026-11-25. Code `designs/pack_5200/iter1/system/bl075_hip_clearance.py` (data
`bl075_hip_clearance.json`), test `tests/test_bl075_hip_clearance.py`. Inputs, read-only: the H1-P export
`iter1/frame/h1p/h1_assembled.stl`, `hip_bearing_ring.stl`, `hip_nut_keeper.stl`, `bl070_h1p.json` `h1p.hip_mount`
(BL-073), CORRIE F rev 3 bag geometry (`concepts/bag_concepts.y_frame`, `patterns_corrie_f_rev3.he_geometry`), the
spreader record (`analysis/spreader_results.json`, chosen `sw110c7d`), the Ti mount (`print/lug_hip_pivot_mount_slm_ti.stl`,
`analysis/hip_mount_bl056.md`), the hipbelt and pad seat (`concepts/corrie.py` `PAD_SEAT`, `analysis/hipbelt_diet.md` f1/f2).
Units mm, g (imperial in brackets).

## Answer

- **The stack clears everything. No screw tail can press into the wearer or wear through bag fabric.**
- **Aft means away from the wearer.** In the frame coordinate system, +y is aft: away from the wearer's back, toward
  the bag (`geometry.yaml` frame.coordinate_system). The boss's mount face (y -48.55) is its wearer face. The Ti
  mount, screw heads, belt pin, bow-tie plate and lumbar pad are all on that side. The ring, nuts, keeper and tails
  stand on the flat back (y -26.5) and point into the frame window toward the bag. Between the tails and anything on
  the wearer side there are 25 mm (0.98 in) of solid material: the 22 mm boss plus the 3 mm Ti base.
- **Fix: none needed. 0 g.** Keep the stock Ti M5 x 35. It is the shortest standard DIN 7984 length that keeps
  at least 2 full threads past the nut at the worst stack tolerance (section 5). The lumbar foam needs no relief cut
  because no tail faces it. Add two zero-mass rules: the pad-seat cord tie goes outboard of |x| 35, and protrusion is
  measured at build (section 6).

## 1. The stack on the exported body

| item | y range (FCS) mm | from the flat back |
|---|---|---|
| boss mount face (wearer face, Ti mount on it) | -48.55 | -22.05 |
| boss flat back (D49 spot face) | -26.5 | 0 |
| 6061 bearing ring 47 / 24 x 2 | -26.5 .. -24.5 | 0 .. 2 |
| PPA-CF nut keeper, OD 48.5 x 3 | -24.5 .. -21.5 | 2 .. 5 |
| A2 DIN 934 nuts, 8 AF x 4 | -24.5 .. -20.5 | 2 .. 6 |
| Ti M5 x 35 tails, 4.0 mm proud (5 threads) | -20.5 .. **-16.5** | 6 .. **10** |

Bolt circle r 19, positions (x, z) = (±14.12, 107.29), (±18.44, 115.4), (±18.44, 124.6), (±14.12, 132.71)
(`h1_closeout.hip_pattern`). Tails span z 104.8 to 135.2 and |x| up to 20.9.

## 2. Against the printed body (H1-P STL)

The STL surface was sampled (400 000 points plus the vertices), with the ring's seat on the flat back left out:

| stack part | min clearance to the body | where |
|---|---:|---|
| ring rim | 0.99 mm | rim lip of the spot face, r 24.5 |
| nut keeper | **0.95 mm** | lip at (21.8, -25.4, 108.8) |
| nuts (circumscribed hex) | 1.87 mm | same lip |
| screw tails | 6.06 mm | |

There is no frame material aft of the flat back inside r 24.49. The lumbar struts meet the boss at its rim and rise
up to 3.68 mm proud of the flat back outside r 24.5. So the keeper (OD 48.5) sits in a D49 pocket with about 0.25 mm
radial play at its tightest. It clears, but only on a clean print. See "Found, not fixed".

## 3. Bag side (aft): spreader, bag body B-01, frame sleeve, under-straps

| element (CORRIE F rev 3) | position | gap to the tail tips | clears |
|---|---|---:|---|
| BP-06 spreader, Sandwich v2 `sw110c7d`, 7.44 mm, clipped on the stays' bag face, z 112-430 | wearer face y 5.51 (lowest stay crown in z 112-145, ASSUMPTION SPREADER-REV-C) | **22.0 mm (0.87 in)** nominal; **18.5 mm (0.73 in)** after its 3.53 mm factored sag, which peaks at x 0, z 124, right over the boss | yes |
| B-01 frame-side panel (the bag's frame face, 20 mm aft of the stay line) | y 17.45-18.02 at z 104.8-135.2 | **33.9 mm (1.33 in)** | yes |
| B-01 bulging into the open bay below the spreader (floor seam z 35 to spreader edge z 112, 77 mm span) | a 33.9 mm bulge needs **46 %** strain (circular arc) | ULTRA 200X fails at a few % (ASSUMPTION B01-STRAIN, cap 5 % gives a 10.5 mm bulge) | yes |
| hinge eyes / HE, B-18 (x ±115, z 60), fairleads on the stays | x ±115 | > 90 mm lateral | yes |
| US1 / US2 under-straps (pins on inboard lugs x ±55-85, z 95; and x ±140-185, z 142), running aft and under the bag | strap leaves its pin aft (+y) | > 40 mm | yes |
| back panel BP-01 / stay-rail sleeves BP-05, rail foam BP-02 | wearer side of the stays, x 55-175 | behind the boss | yes |

CORRIE F rev 3 has no fabric sleeve round the frame at hip height. The bag's frame interface there is B-01 sitting on
the spreader and the stay crowns, held by the hinge eyes at z 60. B-01 cannot reach the tails: it would have to come
34 mm forward past the stay plane through a bay only 77 mm tall.

**Float and bag-off meat carry.** The meat (in its game bag) is cinched against the spreader. Below the spreader edge
it sits on the US1 under-straps, which leave their pins at z 95. The bay it could slump into in front of the boss is
therefore about z 95 to 112, roughly 17 mm tall. Reaching the tails from there means pushing 22 mm forward of the
spreader face, which is not credible for a bulge through a slot that short. The cost of a contact would also be low:
a consumable game bag against eight thread ends sunk 22 mm into the frame. Nothing is added for this case; the field
check is in section 6.

## 4. Wearer side: lumbar pad foam and the hipbelt wrap

- **Lumbar pad foam.** The pad (belt B: EVA 45C stage 1, 8 mm, plus the removable wedge, on the HDPE pad-seat backer)
  is wearer-side of the mount face. The tails are 32 mm (1.26 in) aft of the mount face, and there is solid PPA-CF
  and Ti in between. **No tail can press the foam or the wearer.** Only the screw heads face the wearer, and BL-073
  did not change them: same DIN 7984 M5 heads on the same 3 mm Ti base. The head tops are at y -55.05, which is
  **21.6 mm below the hub face** (hub top 28.1 mm off the boss face) and inside the mount legs (head-to-leg 5.23 mm,
  BL-056). A foam relief cut would remove nothing that is in the way.
- **Hipbelt wrap.** The belt's 6061 bow-tie plate sits on the Ti pin about 21 mm wearer-side of the mount face. Its
  ears curve forward round the hips (rolled R 420, 14.6 deg end slope), and the wing roll is ±8 deg in the pad-seat
  channel. All of it moves at y < -48.55, so the wrap cannot reach anything aft of the boss.
- **Pad-seat retention (the only "wrap" that goes round the frame).** The top sleeve (1000D, 190 x 40, f2) laps over
  the frame top at z about 190. That is 45 mm above the highest part of the stack (keeper edge z 144.25). The bottom
  2 mm Dyneema cord tie (f1) has no drawn route on H1-P. **DECISION BL075-CORD:** the tie goes round each lower lumbar
  strut **outboard of |x| 35** (14 mm clear of the nearest tail at |x| 20.9), **never across the boss back**. A cord
  laid across the boss back would saw on the thread crests whenever the belt is off and the pad hangs on the tie.
  (ASSUMPTION PADSEAT-ROUTE, settled by HB-D3.)

## 5. Fix options (8 screws, one frame)

| option | mass | works? | note |
|---|---:|---|---|
| **none: keep Ti M5 x 35, no part** | **0 g** | **yes** | nothing reaches the tails (sections 2-4) |
| shorter screw | -0.53 g (cut to 34 mm) | technically | no standard length between the 33.95 mm needed and 35. DIN 7984 M5 x 30 gives -1.85 to +0.15 mm protrusion and does not fully engage the nut. Cutting 8 Ti screws saves 1 mm of exposure and 0.53 g but adds a cut-and-chase step. Not worth it. |
| 8 TPU push-on caps (OD 7 x 6) | +1.45 g | yes | the lightest real cover if a witness mark ever shows; caps can be lost |
| nut keeper grown into a closed cover (PPA-CF, 1.2 mm wall and roof) | +3.65 g | yes | one part, hides nuts and tails; reprint the keeper |
| B-01 doubler 60 x 60 ULTRA 200X | +0.48 g | partly | protects B-01 only, and B-01 is already 34 mm away |
| lumbar foam relief cut-out | 0 g | no | wrong side: the foam faces the screw heads, not the tails |

Protrusion band (ASSUMPTION STACK-TOL): stack 31.0 nominal, 30.35-31.35. Need at least 2 full threads plus the end
chamfer, 2.1 mm. M5 x 35 (±0.5) gives **3.15-5.15 mm proud**, which passes. M5 x 30 fails. So 35 is the shortest
standard length, as BL-073 chose. (Ti density 4430 kg/m3, `ti_6al_4v.yaml`; TPU 1200, `tpu_sheet_film.yaml`; PPA-CF
1250, `ppa_cf_fdm.yaml`; ULTRA 200X 133 g/m2.)

## 6. Zero-mass rules for the build and the field test

1. Cord tie route: DECISION BL075-CORD (section 4).
2. BUILD_H1P hip step (manufacturing-engineer to add; not edited here): after torque, measure all 8 tails with
   calipers. Accept 3.1-5.2 mm proud, which is at least 2 full threads. Dry-fit the keeper in the D49 pocket first
   and sand its edge if it binds.
3. T1 / first carry: after the 150 lb (68 kg) load, look at B-01's inside face and the spreader's wearer face over
   the boss for witness marks. If any shows, fit the 8 TPU caps (+1.45 g).

## ASSUMPTIONS

- ASSUMPTION B01-STRAIN: B-01 (ULTRA 200X) strains at most 5 % before its face yarns fail. No elongation is published,
  and the record has none. It is used only to bound B-01's bulge into the bottom bay. Settled by: PT-3 strip pull on
  ULTRA 200X (record the elongation at break).
- ASSUMPTION SPREADER-REV-C: The spreader's wearer face is taken at the lowest stay crown in z 112-145 on the H1-P STL
  (y 5.51), with the factored deflection from `spreader_results.json` (3.53 mm). Settled by: first H1-P dry fit with
  the spreader clipped on, feeler gauge from a tail tip to the sheet.
- ASSUMPTION STACK-TOL: boss 22 ±0.2, ring 2 ±0.1, nut m 4.0 -0.3, Ti base 3 ±0.05, screw length js15 ±0.5, end
  chamfer 0.5. Settled by: caliper check of protrusion at build (rule 2).
- ASSUMPTION PADSEAT-ROUTE: the f1 cord tie on H1-P runs round the lower struts outboard of |x| 35. Settled by: HB-D3
  pad-seat retention fit on the first H1-P frame.
- ASSUMPTION (section 3, float mode): the meat's lower face rests on the US1 under-straps from their z 95 pins.
  Settled by: the float-mode carry in the T1 sequence, checking the game bag over the boss.

## Found, not fixed

- **Keeper in the spot face is tight:** keeper OD 48.5 in a D49 pocket. The strut lip rises 3.68 mm above the flat
  back from r 24.49, which leaves 0.95 mm in 3D and about 0.25 mm radially. A rough print or elephant's foot on the lip
  will bind it. Frame and keeper files are not edited here. Options for the frame owner: keeper OD 47.5, or sand to fit.
- The pad-seat retention (`corrie.PAD_SEAT`: rails, backer, channel) is still written for the v2 CF pan (zone y -48 to
  -27, a 6 mm channel). On H1-P the Ti mount stands 28.1 mm off the boss face inside that channel. The pad seat needs
  its own H1 fit check (HB-D3). This does not affect the tail clearance.

## Screenshots

- `outputs/screens/20261125_bl075_1.png`: section at x 18.44 (bolt column). It shows the frame, Ti mount, ring,
  keeper, nuts and tails, with the spreader (and its factored sag), B-01 and its bulge bound on the aft side and the
  wearer zone shaded.
