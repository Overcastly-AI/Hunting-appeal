# Bag competition, Team B LEAN: FELL

Owner: pack-designer (Team B). Date 2026-11-10. Rules: `designs/pack_5200/bag_comp/RULES.md`.
Research: `docs/research/bag_comp_lean.md` (cited). Code: `designs/pack_5200/bag_comp/lean/`
(`fell.py` build + masses + CORRIE baseline, `fell_clothsim.py` + `scenarios/` cloth sim, `fell_loadout.py` access,
`fell_viz.py` renders, `fell_results.py` -> `result.json`). Tests: `tests/test_bag_comp_lean.py`.
Name: FELL (a bare upland hillside; original).

## 1. The idea in one paragraph

Keep CORRIE's cloth-sim-proven box shell and frame interface, make it 3 % shallower, and take out everything a
lean hunter does not carry every day. The roll-top is the main opening. One straight 540 mm #10 coil zip in the aft
centre seam (z 110-650) reaches IM1-IM3 and low gear. There are no wings: W1/W2, the haul wraps the pack already
carries, do the carry compression (geometry.yaml lists that as their carry-mode job). Eight 25 mm webbing loops sewn
into the four corner seams (z 260 / 490) take **G-hook add-on modules** (HAUL family, the same hook as W1-W3): a
glass pod (padded spotter sleeve), a side strap pair (tripod, poles, jacket), a lid pod (2.7 L) and a strap pod
(snacks, GPS). Each add-on only goes on when the loadout needs it. The body is ULTRAGrid, the collar 70D, the floor
ULTRA 200X, all from cited records with their gates.

## 2. Mass: FELL vs CORRIE B.2, booked by the same code

Scope (belt-independent bag system): bag body group + bag-side pockets + lid/pouch + wings/compression + rain fly
+ fly pocket. Out of both: the belt and its pockets, IMP-6 (sewn to the harness, same part on both), W1-W3, IM1-IM3
and the B-11..B-24 interface parts (identical on both packs). Every row is cut area x record gsm or a hardware record
through `bag_concepts.metrics` / `corrie._imp`, the code CORRIE itself is booked with.

**CORRIE B.2 bag system = 716.5 g** (`fell.corrie_bag_system()`): body group 533.1 (shell, collar, swells, wings,
2.7 L pouch, camo, 1.51 m of zip, hardware) + IMP-1 54.5 + IMP-2 40.3 + IMP-4 22.0 + IMP-8 7.5 + fly re-cut 53.2 +
F-02 5.9.

| FELL row | g | Source |
|---|---:|---|
| Body group: shell 126.1, collar 100.1, swells 14.4, camo 16.5, zip 18.0, hard points + pull 13.0 | 288.1 | `fell.build()` |
| Hydration sleeve (CORRIE IMP-2 geometry, tube 100D -> 70D) | 32.6 | `fell.fixed_pockets()` |
| Cam / tripod-foot cup (IMP-8, unchanged) | 7.5 | same |
| Rain fly scaled to FELL's shell (0.684 m2) + F-02 pocket | 56.7 | `fell.fly_g()` |
| A1 glass pod (back panel ULTRAGrid, 70D sleeve, XLPE, 4 hook straps) | 83.7 | `fell.addons()` |
| A2 side strap pair | 32.2 | same |
| A3 lid pod 2.7 L (ULTRAGrid top, 70D, #5 zip) | 54.3 | same |
| A4 strap pod (power mesh, 70D bellows, 2 wraps) | 28.0 | same |

| Config (fell.CONFIGS) | Add-ons | Bag system g | vs CORRIE | Pack at belt M on H1 (3943 - 716.5 + x) |
|---|---|---:|---:|---:|
| day | A2, A4 | **445.1** | **-271.4** | 3672 g (8.10 lb) |
| elk 6-day | A1, A2, A4 | 528.8 | -187.7 | 3756 g (8.28 lb) |
| sheep 8-day = max (all four) | A1-A4 | **583.1** | **-133.4** | **3810 g (8.40 lb)** |

`result.json` reports the max config (583.1 g, 1.29 lb) so the comparison never flatters FELL. Where the -133.4 g
comes from (max config vs CORRIE): body group -245.0 (no wings, bars and wing straps -101.6; pouch moved out to A3
-55.4; zip 1.51 -> 0.54 m -29.1; the rest is fabric), IMP-1 -54.5 and IMP-4 -22.0 (gone), hydration sleeve -7.7,
fly -2.4, add-ons +198.2.

## 3. Volume, CG and the cloth sim (cg_method: clothsim)

FELL's own sewn pieces in `huntkit.clothsim` (loader `fell_clothsim.load_fell_patterns`, swapped in at run time; huntkit
not edited). Settings = CORRIE's converged `corrie_PR{15,19,23}c` (6 mm contact rounding + continuation, the 1 kg pod on
the roll, the 85 mm spotter, 1.995 kg, hung 50/50 on the glass pod's frame-corner and aft-corner loops). Fabric models:
ULTRAGrid = 330D model x grab ratios 1.30 / 1.375, areal x 0.733; 70D = Robic model x 0.44 / 0.387, x 0.736; ULTRA 200X
modelled directly (ASSUMPTION: same break elongations as the proxy fabrics). Coarse mesh h 40 mm (RULES item 4).

First run on CORRIE's exact depth: 89.7 L at 15 in fill, over the 85 +/- 3 L rule (the 70D collar is softer than
Robic and bulges more). **DECISION: depth x 0.97** (bottom 170 -> 165, shoulder nominal 270 -> 262 mm), width,
collar seam z 736.3 and fill line unchanged. Re-run:

| Torso | Case | Converged (rounding) | Closed vol L (cu in) | CG y incl. pod + spotter mm (limit) | CORRIE B.2 same case | CG z | worst seam N/mm (SF) |
|---|---|---|---:|---:|---:|---:|---|
| 15 in | fill | yes (6 mm) | 87.8 (5358) | **186.8** (205, margin 18.2) | 191.3 | 509 | 1.16 B-03L/B-05 (17.7) |
| 15 in | meat | yes (4 mm) | 87.6 (5346) | **175.4** (190, margin 14.6) | 184.4 (margin 5.6) | 520 | 1.13 B-03R/B-05 (18.1) |
| 19 in | fill | yes (6 mm) | 87.6 | 167.2 | 172.4 | 518 | 1.22 (16.8) |
| 19 in | meat | yes (2 mm) | 87.4 | 158.8 | 167.2 | 527 | 1.07 (19.0) |
| 23 in | fill | yes (6 mm) | 86.3 | 132.7 | 131.2 | 527 | 1.35 (15.2) |
| 23 in | meat | yes (2 mm) | 85.8 | 132.3 | 134.1 | 533 | 1.24 (16.6) |

Mean fill volume **87.2 L (5320 cu in)**, inside 85 +/- 3 (packed, 0.5 kPa: 89.1-90.8 L). Add the <= 4 mm rounding
bias CORRIE measured: 15 in meat <= 179.4 mm, still 10.6 mm inside rev C; **the 15 in meat case that was CORRIE's
1.6-5.6 mm margin is 10.6-14.6 mm on FELL** (shallower shell + stiffer ULTRAGrid faces). Seam SF >= 15 on every
case; the seam strength there is the 330D proxy's (fabric-governed 20.5 N/mm), so the real ULTRAGrid seam is not
weaker on the data we have (its grab estimate is higher). Volume note: the lid pod (2.7 L) is extra and not counted.
Runs: `outputs/clothsim/fell_PR{15,19,23}/results.json`; render drape `fell_PR19_fine` (packed, h 25 mm, 91.3 L).

## 4. Access (loadout check re-run, `fell_loadout.py`, the corrie_loadout model with FELL's zones and sim peel)

Zones: no door pocket; wing_L = under the glass pod, scope_sleeve_L = its sleeve, wing_R = under the side strap pair
(both 6 L / class 3 as CORRIE's wings); top_pouch = lid pod only where fitted; new `strap_pod_R` (class 1, 1.0 L).
The straight zip spans z 110-650 like CORRIE's door, so aft-half items in that span count class 4. Packing rules
(DECISION, user guide): snacks and GPS go in the strap pod; the kill kit sits mid-aft behind the zip.

| Loadout (belt M) | FELL misses | CORRIE B.2 misses (corrie_loadout re-run) |
|---|---|---|
| Day hunt (A2 + A4) | **0** | 2 (snacks hourly, kill kit) |
| Elk 6-day (A1 + A2 + A4) | **0** | 1 (snacks hourly) |
| Sheep 8-day (all four) | 4: bottle #2 (hourly), trekking poles, beanie / gloves, first-aid light (glassing / emergency) | 4: GPS, bottle #2, snacks (all hourly), trekking poles |

Same at belts S-L; XL / XXL sheep drops the beanie miss. Hourly misses: FELL 1 (sheep bottle #2) against CORRIE's
3-5 across the loadouts. The sheep cost is real: no door pocket and full side straps push the beanie, the light
first-aid kit and the poles into the bag top. Fix if the owner wants it: a second strap pair on the left over the
glass pod (+32 g) takes the poles. Rev C on every loadout x belt: worst carry 179.4 mm (limit 205), worst pack-out
145.4 mm (limit 190), with FELL's own sim peel.

## 5. Build (beginner, one walking-foot machine)

39 cut pieces (max config, CORRIE 42), **0 curved seams** (CORRIE 1), 7.9 m of body seam, 3 ring seams, one straight
zip set into a straight centre seam (the easiest zip there is) plus the #5 lid-pod zip: **800 mm of zip** (CORRIE
1514 mm, two curved corners). Beginner hours 27.9 (CORRIE 35.6, same `BC.HOURS` model). The add-ons are separate
flat-work projects, so the bag can be finished and used before any pod is sewn. All seams straight; body seams use
CORRIE B.2's seared allowance (WP-1 wash-swatch gate applies, with ULTRAGrid swatches added).

## 6. Fixed list check

| Item | FELL |
|---|---|
| Frame interface | unchanged: hood B-19 on the crown bar, B-20 ladders on the ULTRA collar strip, B-22 at z 695 (now on the aft halves), IM2/IM3 hooks with B-17/B-23, hinge pins + B-18, B-24, US1/US2, IM1-IM3, fairleads (8 boxed swells), bow riser carry (B-11 loops + cam cup), fly in the base pocket |
| Volume / size | 87.2 L sim (85 +/- 3), width 15.5 in (393.6 mm), max depth 9.9 in drafted / sim bulge inside 12 in |
| Look and sound | solid body; owner camo on the V-notch kick band, pod leading-edge bar, zip garage, lid-pod tab, strap-pod binding; no hook-and-loop; coil zips with cord pulls |
| Loads | rev C: section 3 (cloth sim) |
| Access | section 4 |
| IP | generic mechanisms only; frame interface (H1-H4 guardrails) untouched |
| Build | section 5 |

## 7. Weaknesses (plainly)

1. **Durability is traded for grams.** ULTRAGrid only matches 330D on abrasion (Taber 1100 vs the 330D's inferred
   ~950-1070) and is about 55-60 % of 500D. The 70D collar tears at 37-52 N. FELL is lighter, not tougher.
2. **Fabric gates.** ULTRAGrid needs the owner's swatch approval (visible grid on the solid colourway); ULTRA 200X
   floor needs PT-3 plus a 50 mm strip test (its strip strength is not published); weigh the Robic before trusting
   the collar saving.
3. **Noise.** ULTRA 200X is a film laminate (quietness 2/5 in the record; no published hunting test). It is only on
   the floor and the (already ULTRA) frame side, but it can crinkle when the pack is set down.
4. **Access.** A straight slit opens narrower than a horseshoe (about a 210 mm lens at mid-height in the render), and
   W1/W2 cross it: two G-hooks come off before it opens. No door pocket.
5. **Modules only save weight if they stay home.** With every add-on fitted the saving is 133 g, not the 271 g of the
   day config; loose G-hook pods can be lost.
6. **Sheep load** keeps 4 misses (section 4).
7. **Model limits.** Coarse-mesh CG (h 40 mm), proxy fabric stiffness for ULTRAGrid / 70D, the 3 % shallower shell not
   yet checked against hood / B-20 fit on a prototype; renders place pods, straps and the open zip as geometry on the
   drape (not simulated).

## 8. Renders (Blender Cycles via huntkit/viz3d/cycles_render.py, 1600 x 1200, 64 samples)

Builder `bag_comp/lean/fell_viz.py`: CORRIE B.2's scene (frame, harness, padded belt B, display form) with every CORRIE
bag part removed and FELL's parts placed on FELL's own fine drape. Float-mode copies are pre-translated 170 mm because
the Cycles path does not apply the viewer's float offset.

| # | File | Shot |
|---|---|---|
| 1 | `outputs/screens/20261110_bagB_1.png` | hero 3/4 rear |
| 2 | `outputs/screens/20261110_bagB_2.png` | side profile, wearer's right, lid pod on |
| 3 | `outputs/screens/20261110_bagB_3.png` | access: the centre zip open, IM1-IM3 inside |
| 4 | `outputs/screens/20261110_bagB_4.png` | feature: hard points + glass pod with the 85 mm spotter |
| 5 | `outputs/screens/20261110_bagB_5.png` | meat haul, float mode, quarter between frame and bag |
