# Bag competition, Team A EVOLVE: CORRIE E

> **Masses superseded (BL-035 records, checked BL-036, 2026-11-13).** The mass figures in this write-up are the 2026-11-10 entry. BL-034/035 put the hardware on the material records (two #10 door sliders +26.0 g, IMP-4 #5 slider +1.9 g where the bag has them); `result.json` holds the current numbers, on the same definitions: bag system **762.5 g** (was 734.6), CORRIE B.2 **738.5 g** (was 710.6), so the difference (+24.0 g) and the pack on the RULES.md 3943 g basis (**3967.0 g**) do not move.

Owner request 2026-11-10 (bag design competition, `designs/pack_5200/bag_comp/RULES.md`). Team A brief: the best
possible evolution of CORRIE B.2. Fix its known weak spots: the snacks miss on S-L belts, the 8-day sheep load
pushing the trekking poles out of reach, the boxy look, and the bulge strain at the side-panel | floor seam.

Code (team folder only, CORRIE and huntkit are imported, never edited): `designs/pack_5200/bag_comp/A/`
- `evolve.py`: envelope, change ledger, mass, hours.
- `evolve_bag.py`: cloth-sim loader. It subclasses `huntkit/clothsim/corrie_bag.BoxSurface` and reuses its helpers.
- `evolve_loadout.py`: re-points `concepts/corrie_loadout.py`.
- `evolve_viz.py`: re-points `huntkit/viz3d/corrie_b2.py`.
- `make_result.py` writes `result.json`.

Research: `docs/research/bag_comp_A.md` ([A1]-[A16]). Tests: `tests/test_bag_comp_A.py`.

## 1. What CORRIE E is

CORRIE E is CORRIE B.2 with these parts unchanged:
- the horseshoe #10 door;
- the side compression wings;
- the 2.7 L pouch;
- IMP-1/2/4/8;
- every frame-interface part (hood B-19, B-20 ladders, B-22 guys at z 695, IM2/IM3 hooks, hinge pins, B-24, US1/US2, IM1-IM3, fairleads, bow riser carry, fly pocket).

On top of that, seven changes:

| Id | Change | Weak spot it fixes | Basis |
|---|---|---|---|
| E-1 | **Rounded aft corners, R 40 mm.** The aft panels wrap both vertical aft corners. The gusset \| aft seam moves to the side tangent, so the gusset stays a flat, straight-seamed panel and the wing loops stay in that seam. | Boxy look. Door width as a bonus. | [A10-A11] |
| E-2 | **Shoulder taper.** Width 394 mm at z 631 to 370 mm at the collar seam (15.5 to 14.6 in). | Boxy look | [A10-A11] |
| E-3 | **Camo tub base.** A 60 mm tub wall in camo-printed 500D runs round the three outer sides (z 35 to 95). It replaces the two-layer chevron kick plate SH-01a/b with one layer, and the gussets and surround start at z 95. Door sill z 110 to 130. | Side \| floor seam strain. Camo where the wear is. | [A13-A16], [A12] |
| E-4 | **Hip-reach pockets FP-L / FP-R** on the lower front corner of each wing (z 150-380): power mesh 180 x 230 mm with 2 box pleats, a shock-cord top and a 25 mm camo mouth band, mouth angled forward. FP-L takes the snacks and GPS; FP-R takes the 2nd bottle. | Snacks miss on S-L. Sheep GPS and 2nd-bottle misses. | [A1-A5], [A7] |
| E-5 | **Pole quiver.** The pole tips go into a 40 mm boot stitched in FP-R's front pleat; the grips go into a 3 mm shock-cord loop with a cord lock at the wing's top front corner. | Sheep load pushing the poles into the bag | [A6-A9] |
| E-7 | **Wider base.** Floor half-width 136 to 160 mm (272 to 320 mm, 12.6 in), linear to 197 at the shoulder crease as before. | Puts back the volume E-1/E-2/E-3 removed, low and on the frame line, so the collar stays at z 736.3 | iteration log, section 3 |
| E-6 | Everything else as CORRIE B.2. | | |

**Best idea: the hip-reach pockets with the pole quiver (E-4 / E-5).** The S-L snacks miss came from the belt pocket's
length, which grades down with the belt (57 / 97 / 132 mm interiors). E-4 moves the snack and GPS home off the graded
belt onto the bag, at the belt root, facing forward (Exo's lower forward compartment [A7]). It is the same part on
every size, so S-XXL all pass. The same pocket on the right gives the 2nd bottle a pack-on home and the poles a boot.
The poles never compete with the tripod or the rain jacket for a wing, so the B.2 sheep regression is gone.

## 2. Numbers (result.json)

| Quantity | CORRIE E | CORRIE B.2 (same code) | Basis |
|---|---:|---:|---|
| Bag system g (bag + pockets + pouch + wings + fly, belt-free) | **734.6** | 710.6 | `evolve.system()`: corrie.build on the E envelope + ledger + IMP-1/2/4/8 + fly scaled to the outer shell |
| Pack, belt M, on H1 | **3967 g (8.75 lb)** | 3943 g | 3943 - 710.6 + 734.6 |
| Main bag, cloth sim fill case | **85.2 / 85.3 / 84.5 L** (mean 85.0 L, 5187 cu in) at 15 / 19 / 23 in | 88.1 / 88.4 / 87.0 | `outputs/clothsim/bagA_evolve_PR{15,19,23}/results.json` |
| Packed (0.5 kPa) | 89.9 / 90.0 / 88.8 L | 92.7 / 92.9 / 91.2 | same |
| Pouch (not counted) | 2.7 L | 2.7 L | corrie B.2 |
| Hip-reach pockets (not counted) | 2 x ~2.0 L (stretch, ASSUMPTION) | none | |
| Width max / at collar; depth max | 394 / 370 mm; 258 mm (10.2 in) | 394 / 394; 258 | `evolve.volumes()` |
| Fill height | 40.2 in (z 1056) | 40.2 in | collar seam z 736.3 unchanged |
| Pieces (body + IMP pockets) | 42 | 42 | kick plates -3, tub +1, pockets +2 |
| Curved seams | 2 (door U, floor \| tub ring with 2 R 40 arcs) | 1 | |
| Zips | 1476 mm (door #10 1216 + pouch #8 260) | 1514 mm (1254 + 260) | door sill raised and corners rounded, so the U is shorter |
| Beginner hours | 38.3 h | 35.6 h | `bag_concepts.HOURS` model, ASSUMPTION |
| Door clear width at IM1 / IM2 / IM3 | **294 / 311 / 334 mm** | 214 / 242 / 281 | the zip sits 45 mm along the surface from the side tangent, on the R 40 arc |

Mass ledger (g, against corrie.build on the E envelope; all cut area x record gsm, `evolve.ledger()`):

| Row | g |
|---|---:|
| E-1 corners (aft panels and zip 34 mm narrower, floor corners) | -4.1 |
| E-3 tub wall in, kick plates SH-01a/b out (19.3 g), gusset / surround bottoms out | -13.5 |
| E-7 floor 272 to 320 mm (the rest of the widening is in the build) | +2.1 |
| E-4 two pockets: mesh 23.1 + shock cord 3.8 + camo bands 6.6 | +33.5 |
| E-5 pole loop + cord lock + tab | +5.4 |
| Envelope (taper, wider base) inside corrie.build | +1.4 |
| Fly scaled to the outer shell | -0.8 |
| **Net vs CORRIE B.2** | **+24.0** |

## 3. Cloth sim (huntkit/clothsim, CORRIE's c-run settings, coarse h 40 mm)

The scenarios `bag_comp/A/scenarios/evolve_PR{15,19,23}.yaml` extend CORRIE's `corrie_PR{t}c` runs:
- 1 kg pouch on the closure;
- 85 mm spotter in the left wing sleeve;
- contact-rounding continuation.

The only change is `max_iter` 400 to 1200, because the first E runs stalled in the re-cinch stage. All 12 cases
converged (residual < 0.5 N). Fill and meat cases were reported at 4-6 mm contact rounding; read them +<= 4 mm,
as for CORRIE.

| Torso | Fill CG y, mass-weighted with pouch + scope (limit 205) | CORRIE B.2 | Meat CG y (limit 190) | CORRIE B.2 | CG z fill / meat |
|---|---:|---:|---:|---:|---|
| 15 in | **186.8** (margin 18.2) | 191.3 (13.7) | **179.6** (margin 10.4) | 184.4 (5.6) | 485 / 494 |
| 19 in | **165.3** | 172.4 | **160.1** | 167.2 | 498 / 505 |
| 23 in | **130.3** | 131.2 | **129.9** | 134.1 | 504 / 514 |

With the <= 4 mm rounding bias, the 15 in meat case is <= 183.6 mm (margin >= 6.4). CORRIE's equivalent was a margin
>= 1.6 mm.

**Seams (the B.2 bulge-strain weak spot).** The side-panel | floor seam (CORRIE B-03 | B-05, now B-03 | B-05w, the
gusset to tub wall):

| Case | CORRIE B.2 N/mm | CORRIE E N/mm |
|---|---|---|
| Fill 15 / 19 / 23 in | 1.50 / 1.36 / 1.14 | **0.55 / 0.62 / 0.65** |
| Meat 15 / 19 / 23 in | 1.99 / 1.83 / 1.59 | **0.64 / 0.58 / 0.60** |

That is 57-68 % lower. The worst seam anywhere is now:
- 1.18 N/mm on B-01 | B-05 (19 in meat, SF 23), against CORRIE's 1.99 (SF 10.3);
- 1.02-1.04 N/mm on the new B-02u | B-05w (tub to surround) on fill cases;
- 0.83 N/mm on B-02h | B-06 at 15 in fill (SF 14).

Peak shear e_max is 21-24 % in the buckled floor corners, against 14-19 % for CORRIE. That is a buckle read-out, not
warp/weft stretch.

**Iteration log (honest):** the first run had the collar at z 736.3 with CORRIE's base and gave 81.7 L (out of
tolerance). Raising the collar to z 776 gave 85.5 L, but the 15 in CG went to 198.2 fill and 188.8 meat (margin 1.2).
A taller bag peels more on a short torso, so the volume went back in low and wide (E-7) and the collar stayed. Those
runs are in the scratchpad, not in `outputs/`.

**Pattern strain.** A rounded corner that follows the curved frame line is not exactly developable. The flattening
leaves p99 strain of 4.4 % on the hinge band B-02h, 1.7 % on the U-surround and 1.1 % on the door. The pattern-maker
must ease it (cut-and-check on the proto).

## 4. Access (`evolve_loadout.py`, all loadouts x belts S-XXL)

The hourly, glassing and weather items not reachable at their required class:

| Loadout | S | M | L | XL | XXL | CORRIE B.2 |
|---|---|---|---|---|---|---|
| Day hunt | 0 | 0 | 0 | 0 | 0 | snacks on S-L |
| 6-day elk (rifle, archery) | 0 | 0 | 0 | 0 | 0 | snacks on S-L |
| 8-day sheep | 0 | 0 | 0 | 0 | 0 | GPS, 2nd bottle, snacks on S-L; poles in the bag (B-5 regression) |

The packing rule (`evolve_loadout.PREFS`):
- snacks and GPS go to FP-L;
- the 2nd bottle goes to FP-R;
- the poles go to the quiver;
- everything else stays as CORRIE's loadouts.yaml.

The day-hunt kill kit still reads class 5 in the model. This is the packing-order artifact inherited from B.2
(corrie_body.md 12.3): packed by the IMP-4 rule it is class 4. The worst loadout bag CG plus peel (the corrie_loadout
method) is 164 / 143 / 108 mm fill and 150 / 131 / 102 mm meat at 15 / 19 / 23 in.

## 5. Build (beginner, one walking-foot machine)

- Every new seam is straight except the floor | tub ring. Clip the two R 40 arcs to the notches.
- The pockets are flat-work: pleat, then sew three sides to the wing before the wing is hemmed (the same step order as IMP-1).
- The tub wall is one strip:
  1. Sew it to the gusset and surround bottoms as a straight ring.
  2. Set the floor into it.
  3. Sew the two short ends into the B-01 side seams.
- IMP-8 (cam cup) is now caught in the gusset | tub seam at the aft corner instead of the gusset | floor seam.

## 6. Risks and gates (also in result.json)

1. **Mass +24 g** on CORRIE B.2. The pockets cost more than the corners and the tub save.
2. **More work:** +2.7 h and one more curved seam.
3. **Corner ease:** up to 4.4 % on B-02h (section 3).
4. **Wider base:** 320 mm at hip level. Gate EV-1: elbow swing and rifle-butt walk test on the prototype.
5. **Reach is assumed.** Pocket reach is an ASSUMPTION (class 1). Gate EV-3: S/M/L testers, loaded, gloved.
6. **Bottle load on the wing root.** A full bottle (1.18 kg) in FP-R loads the wing root seam. Gate EV-4: bartack plus a 25 mm tape behind the pocket corners, and a pull test.
7. **No record for the tub fabric.** Printed 500D has no material record (ASSUMPTION: the record gsm). The materials-engineer should add the record and a Taber test on the printed face.
8. **Pocket moves with the wing.** Unclipping a wing swings its pocket out. Contents stay in under the shock cord, but wrappers can rustle (user guide: quiet wrappers).

## 7. Renders (Blender Cycles, `evolve_viz.py`, `huntkit/viz3d/cycles_render.py`, 1600 x 1200, 64 samples)

The bag skin is CORRIE E's own fine cloth-sim drape: `bagA_evolve_PR19_fine`, packed case, h 25 mm, converged. The
camo tub is the sim's own B-05w piece. The meat-haul shot uses a baked float GLB (`bagA_float.glb`), because
cycles_render does not apply the viewer's float offsets.

| # | File | View |
|---|---|---|
| 1 | `outputs/screens/20261110_bagA_1.png` | hero 3/4 rear (wearer's right): rounded corners, taper, camo tub, both pockets |
| 2 | `outputs/screens/20261110_bagA_2.png` | side profile, wearer's right |
| 3 | `outputs/screens/20261110_bagA_3.png` | access: horseshoe door open, IM1-IM3 and the floor in reach |
| 4 | `outputs/screens/20261110_bagA_4.png` | feature: hip-reach pocket and pole quiver |
| 5 | `outputs/screens/20261110_bagA_5.png` | meat haul, float mode 170 mm |
