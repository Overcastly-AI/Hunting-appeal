# Bag competition, team C (OPEN): TAILGATE

Team C, 2026-11-10. Brief (bag_comp/RULES.md): a full-access hauler whose whole aft face opens, with the roll-top
and the fixed frame interface kept, and an answer to zip blowout under hoop load. Research:
`docs/research/bag_comp_C.md`. Code (team folder only): `designs/pack_5200/bag_comp/C/`
(`tailgate.py` geometry, pieces, mass, hoop check; `tailgate_clothsim.py` pattern loader + runs;
`tailgate_loadout.py` access / CG; `tailgate_viz3d.py` render model; `make_result.py` -> `result.json`).
Tests: `tests/test_bag_comp_C.py`. Nothing shared was edited: CORRIE B.2 (`concepts/corrie.py`) is imported and
everything not named below is CORRIE B.2 as built.

## 1. What it is

TAILGATE keeps CORRIE B.2's box body (B-01 frame panel, gussets, 500D floor, swells, collar, roll-top, 2.7 L pouch,
fly) and its whole frame interface (hood B-19, B-20 ladders, B-22 guys at z 695, IM2/IM3 hooks, hinge pins + B-18,
B-24 float links, US1/US2, IM1-IM3, fairleads, bow riser carry, fly pocket). It changes the aft face and the
compression:

| # | DECISION | Why |
|---|---|---|
| T1 | **The whole aft face below the hinge band is one 330D lid B-02L, hinged on the sewn floor seam.** It drops down like a tailgate. | The full box width is open from the floor to z 650 with no sill. The zip is never at the floor, where the meat weight, ground water and abrasion are. |
| T2 | **#10 coil zip, inverted U (1588 mm), in the two aft corner seams**, R 60 onto the face, top run under the hinge band at z 650. Two sliders, parked closed at the top-right corner under a camo garage SH-07; zip feet in 500D boots under the kick plate; cord pulls. | #10 is the record we hold and the leaders' main-zip size (research §3). The hinge band (z 650-736) keeps B-22 at z 695, 15 mm clear of the zip. |
| T3 | **Lid straps H1-H3 at z 190 / 330 / 520 (the IM heights)**, 25 mm polyester, G-hook into a gusset loop on the right, ladder lock on a loop on the left; loops 15 mm forward of the zip. Lid cut 6 mm full across. **Rule: cinch H1-H3 first, then zip.** | The straps bridge the zip, so closing the bag never uses the slider as the clamp (the over-stuffing failure, research §2). Hooks on one side: one sweep of the right hand opens the lid. |
| T4 | **Storm flaps**: camo 630D, 35 mm, hot-cut, over both zip legs; 330D over the top run. | Brush protection on the most abraded line (the aft corners), and the owner's camo used as an accent edge framing the lid. |
| T5 | **No wings.** 2 side straps a side (frame-corner seam to the same gusset loops): tripod right (IMP-8 cup at its foot), pad / decoy left; IMP-1 spotter sleeve sewn to the left gusset. | The wings tied to the aft corner seams, which now hold the zip. The side straps do the same carry with no panels. |
| T6 | **IMP-4 kill kit on the inside of the lid.** | The kit comes to you when the lid drops. |
| T7 | **IMP-C1 snack / GPS stretch sleeve, right J-strap** (power mesh over 330D, 130 x 210, 45 mm stretch; 15.8 g). | CORRIE's residual miss: snacks on S-L belts. Now reachable pack-on on every belt. |

## 2. Numbers

| Quantity | TAILGATE | CORRIE B.2 | Source |
|---|---|---|---|
| Main bag, sim closed volume, fill (15/19/23 in) | 88.5 / 88.8 / 86.9 L (5401 / 5419 / 5304 cu in), mean 88.1 L | 88.1 / 88.4 / 87.0 L | `outputs/clothsim/bagC_tg_PR*/results.json`, corrie_body.md 11.4 |
| Flat-panel rule volume | 75.9 L (same body: the rule under-counts the box, CORRIE REVS note) | 75.9 L | `bag_concepts.volumes` |
| Fill height / width / depth | 40.2 in, 15.5 in, 11.4 in max | same | same body |
| Opening | 0.229 m2 (lid) | 0.153 m2 (door) | `tailgate.numbers()` |
| Clear width at IM1 / IM2 / IM3 / floor | **286 / 314 / 353 / 254 mm**, no sill | 214 / 242 / 281 / 146 mm, sill z 110 | same |
| Bag system (bag + pockets + pouch + straps + fly) | **758.7 g** (1.67 lb) | 710.6 g | `tailgate.bag_system` (same definition for both) |
| Pack at belt M on H1 | **3991.1 g (8.80 lb)** = 3943 - 710.6 + 758.7 | 3943 g | RULES.md |
| Cut pieces / curved seams / zips | 32 / 1 (the lid zip) / 1.85 m (lid 1.59 + pouch 0.26) | 33 / 1 / 1.51 m | `bag_concepts.metrics` |
| Beginner hours (bag-body group, model) | 25.7 h (+ IMP-C1 1.1 h) | 28.6 h | `bag_concepts.HOURS` (ASSUMPTION, rank not plan) |

Mass, what moved (+48.1 g): longer zip (+0.33 m #10, +6.7 g), lid straps H1-H3 + 4 side straps + 6 loops
(112.5 g: 55.1 + 46.6 + 10.8, against CORRIE's 4 wing straps), storm flaps (19.8 g), lid + band (50.2 g vs door + surround + band
54.6 g), wings and bars deleted (-48.0 g), IMP-C1 (+15.8 g). The side straps are the item to cut first (-46 g if the
owner carries the tripod in the bag, or -23 g on the left only).

## 3. Hoop load and the zip (cloth sim, honest result)

Runs: `tg_PR15` (lid straps on), `tg_PR15_nostraps` (control), `tg_PR15_ease` (lid cut 6 mm full, straps on). Rated
68 kg Janssen fill and 30 kg meat + 38 kg gear (HA-LS-1 C1), 15 in, coarse h 40, all converged. The zip is modelled
closed as a sewn seam; the seam force across it is the zip's crosswise load.

| Case | Zip legs (lid / gusset R, L) N/mm | Top run (lid / band) N/mm | Hinge (lid / floor, sewn) | H1 / H2 / H3 N |
|---|---|---|---|---|
| fill, straps on | 0.345 / 0.325 | 0.451 | 0.647 | 25.6 / 20.1 / 12.3 |
| fill, straps off | 0.350 / 0.333 | 0.423 | 0.674 | - |
| fill, straps on + 6 mm ease | 0.332 / 0.340 | 0.437 | 0.645 | 26.8 / 21.4 / 13.9 |
| meat, straps on | 0.215 / 0.194 | 0.307 | 0.436 | 23.7 / 19.8 / 12.7 |
| meat, straps off | 0.238 / 0.230 | 0.287 | 0.465 | - |

Read-out:
1. **The zip carries very little hoop load in this body, straps or not**: 0.45 N/mm at worst against 35 N/mm
   (record 900 N per 25.4 mm, ESTIMATE): static SF 79, 26 at 3 g. The box's load goes into the floor seams (the
   critical seam is B-03L | B-05, 1.48 N/mm, as CORRIE). The corners of a box are not the hoop-tension line.
2. **The sim does NOT show the lid straps unloading the zip**: the legs drop 1-10 %, the top run rises 7 %, and the 6 mm ease changes nothing measurable.
   The claim "the straps carry the hoop load" is therefore not proven by this model. At 12-27 N the straps are
   lightly loaded (ladder-lock slip SF 11.7, stretch 0.2 mm < 6 mm ease).
3. What the straps do for the blowout risk is the **closing procedure and the dynamic case**, neither of which the
   static sim models: with H1-H3 cinched first, the lid edges are pulled to the gussets by webbing and the slider runs
   on a slack chain (the over-stuffing failure the forum reports, research §2); and the lid cannot bulge open past the
   straps under a drop or a point load (antler tine, knee on the pack). The prototype test below measures this.
4. Zip size: #10 stays (O-13 kept). #8 would carry the static case on paper, but the field failures are slider wear
   and closing force, where the larger slider helps.

Test added (ZP-1, prototype): bag at 68 kg, lid zipped with straps off vs on; drop 300 mm onto the floor 5 times;
then a 400 N point load on the lid at mid-span between H2 and H3; pass = no chain separation, slider still locks.

## 4. CG at 15 / 19 / 23 in (cloth sim)

Mass-weighted CG y incl. the 1 kg pouch and the 85 mm spotter on the left gusset (hung from the B-01 | B-03L seam,
not the zip). Coarse runs `bagC_tg_PR{15,19,23}`, residual <= 0.42 N; reported at contact rounding 4-6 mm, read
+4 mm for the rounding bias (corrie_body.md 11.4).

| Torso | Fill CG y (limit 205) | + 4 mm bias | Meat CG y (limit 190) | + 4 mm bias | CORRIE B.2 fill / meat |
|---|---|---|---|---|---|
| 15 in | 191.4 | 195.4 (margin 9.6) | **185.0** | **189.0 (margin 1.0)** | 191.3 / 184.4 |
| 19 in | 170.0 | 174.0 | 165.3 | 169.3 | 172.4 / 167.2 |
| 23 in | 136.6 | 140.6 | 134.5 | 138.5 | 131.2 / 134.1 |

CG z 499-528 mm (limit 590). TAILGATE carries like CORRIE (same shell); the 15 in meat case is marginal for both.
The lever is the same as CORRIE's: strap the pouch to the frame-side hem (about -4 mm).

## 5. Access (loadout check, `tailgate_loadout.py`, all loadouts x belts S-XXL)

Hourly / constant items not reachable pack-on:

| Loadout | S | M | L | XL | XXL | CORRIE B.2 (M) |
|---|---|---|---|---|---|---|
| Day hunt | 0 | 0 | 0 | 0 | 0 | snacks |
| 6-day elk (rifle, archery) | 0 | 0 | 0 | 0 | 0 | snacks |
| 8-day sheep | 2nd bottle | 2nd bottle | 2nd bottle | 2nd bottle | 2nd bottle | GPS, 2nd bottle, snacks |

Glassing / weather / kill items (required class 4): none missed at belt M (CORRIE B.2 sheep: trekking poles at class 5):
the lid reaches both bag columns below z 620, not only the aft half. Bag-load CG at 15 in (loadout model + TAILGATE
peel): day 172.2, elk 164.5, sheep 176.7 mm (limit 205); pack-outs 140.9 / 157.9 / 153.8 mm (limit 190).

## 6. Meat modes with IM1-IM3

- **A, meat in the bag (the TAILGATE case):** lay the pack frame-down or stand it on the frame; unhook H1-H3, unzip, the
  lid drops. The quarter goes straight onto B-01 with no sill to lift it over; IM1-IM3 come out of the B-01 ports
  across a 286-353 mm clear width (CORRIE 214-281), so the hooks at both ends are in plain view. Cinch IM1-IM3, close
  the lid, **cinch H1-H3, then zip**. The meat case CGs above (15 in 185.0 mm) and the elk 45 kg pack-out (157.9 mm at
  15 in, loadout model) are inside rev C. The bladder stays hung (IMP-2 above IM3).
- **B, bag off:** unchanged (frame interface unchanged).
- **C, float:** unchanged links and gaps (B-24 on the IM3 eyes, 120/170/220 mm). In float the bag holds gear only,
  so the lid stays zipped; W1-W3 close round bag and meat over the lid face, not over the zip legs (the lid straps
  stay on under them). To open the lid in float, slack W1-W3 first (same as CORRIE's door).

## 7. Build (beginner, one walking-foot machine)

Pieces are rectangles and the developed box panels of CORRIE. One curved seam: the lid zip's two R 60 corners
(CORRIE has the same count). Sequence for the lid: sew the camo flaps into the gusset aft edges; set the zip tape to
the gussets and the hinge band (flap caught in the same row); sew IMP-4 to the lid flat; set the lid to the zip;
close the hinge seam to the floor with 2 rows (sealed in the same pass as the floor ring). Loops and straps are
bartacked flat-work before assembly.

## 8. Weaknesses (stated plainly)

1. +48.1 g on CORRIE B.2 (pack 3991 g at belt M).
2. The hoop-strap claim is not shown by the static sim (section 3); the straps' value rests on the closing procedure
   and the dynamic case, to be shown by ZP-1.
3. 15 in meat CG margin 1.0 mm after the rounding bias (as CORRIE).
4. Opening the lid needs 3 G-hooks off first; a user who zips first and cinches second uses the slider as the clamp.
5. The zip legs are on the aft corners (the most abraded line); the flaps must stay down.
6. With the lid down on a slope or in snow the lid's inside face lies in the dirt or blood: lay the pack frame-down
   first, or use the lid as a mat on purpose.
7. Sim simplifications: zip modelled closed; R 60 corners modelled square; lid straps anchored on the frame plane, not
   on the gusset loops; one fine drape (19 in packed) for the renders.
8. Zip crosswise strength is a record ESTIMATE; patent search for a floor-hinged lid not done (flag for the attorney).

## 9. Renders (Blender Cycles, `huntkit/viz3d/cycles_render.py`; skin = TAILGATE's own fine drape `bagC_tg_PR19_fine`, packed)

| # | File | Shot |
|---|---|---|
| 1 | `outputs/screens/20261110_bagC_1.png` | hero 3/4 rear on the display form |
| 2 | `outputs/screens/20261110_bagC_2.png` | side, wearer's right |
| 3 | `outputs/screens/20261110_bagC_3.png` | access: lid down, the whole aft face open |
| 4 | `outputs/screens/20261110_bagC_4.png` | feature close-up: zip garage, H3 bridging the corner zip, camo flap |
| 5 | `outputs/screens/20261110_bagC_5.png` | meat haul: quarter on B-01 under IM1-IM3, loaded through the open face |

Render-only liberties: the lid, straps, flaps, roll, pouch, tripod and sleeve are placed geometry on the simulated
skin; the open lid is the simulated lid rotated rigidly 165 deg about its hinge seam; the meat quarter is the
viz3d bag-off quarter proxy moved onto B-01.
