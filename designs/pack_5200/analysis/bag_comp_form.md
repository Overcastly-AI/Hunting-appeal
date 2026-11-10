# Bag competition, Team E FORM: CHERT (2026-11-10)

Entry for `designs/pack_5200/bag_comp/RULES.md`. Code: `designs/pack_5200/bag_comp/form/` (form.py envelope, pieces,
mass and build metrics; form_sim.py cloth sim; form_loadout.py access; form_viz.py renders; form_patterns.py pattern
sheet; form_result.py writes `result.json`). Research: `docs/research/bag_comp_form.md`. Tests:
`tests/test_bag_comp_form.py` (6 pass). Nothing shared was edited. The CORRIE modules are re-pointed at CHERT only
inside the CHERT processes (pattern loader and skin/concept references).

## 1. The idea

**CHERT** is CORRIE B.2's box, roll-top, wings, pouch, pockets and frame interface. Each of the two aft vertical
corners is cut off by a **chamfer blade** in the owner's camo. The blade tapers from 60 x 55 mm at the floor to
32 x 26 mm at the collar seam. The door zip (#10 coil, two sliders) runs **in the blade | door seam**, so the panel
line, the camo break and the door edge are one line. The door is the whole aft face from z 110 to the hinge at z 650,
as on CORRIE. Below the door, the blades join a 75 mm camo kick strip. Blades and kick strip are cut as **one camo U
piece**, B-02u, which is creased at the facet lines rather than seamed. A camo **fang** inset low on each gusset
(one straight seam, from the frame edge at z 60 to the blade at z 260) wraps the camo round the lower corner.

Solid two-tone colour blocking: olive faces, a dark collar, hinge band and roll, and camo only on the outline. That
puts the camo where disruptive patches do their optical work and keeps the owner's "mostly solid" rule
(research items 6-7).

DECISIONS (this entry): blade taper; door width at z 110 >= 160 mm (it is 163 mm); fang line; base half-width 130
(CORRIE 136) for a stronger V in rear view; two-tone cap; IMP-6R strap snack pocket (section 5).

## 2. Volume, envelope and fixed list

| Item | CHERT | Limit / CORRIE | Source |
|---|---|---|---|
| Width max | 393.6 mm (15.5 in) | <= 394 | form.py |
| Depth max | 257.8 mm (10.2 in) | <= 305 (12 in) | form.py |
| Collar seam z | 771.9 mm | CORRIE 736.3 | solved for the rule volume below |
| Design-rule volume | 76.94 L | CORRIE 75.87 L | form.Knap.volume_L (chamfered section + SPINE dome law) |
| **Sewn fill volume (sim)** | **86.7 / 86.7 / 85.0 L at 15/19/23 in (5291 / 5291 / 5187 cu in), mean 86.1 L** | 85 +/- 3 L | outputs/clothsim/chert_PR{15,19,23}c |
| Packed volume (sim, 0.5 kPa) | 90.4 / 90.3 / 88.7 L | CORRIE 92.7 / 92.9 / 91.2 | same |
| Fill height (floor to fill line) | 41.6 in | CORRIE 40.2 in | form.py |
| Uniform-fill CG y, z | 134.1, 582.8 mm | CORRIE 134.7, 557.1 | form.Knap.cg |

How volume counts: main bag only, to the roll-top fill line, with the collar closed flat (the cloth-sim closure). The
2.7 L pouch, the wings, the sleeves and the hipbelt pockets are not counted.

**Calibration note (honest).** The first run (the pilot, kept in `outputs/clothsim/chert_pilot`) used CORRIE's
sim / rule ratio. It stuffed to only 82.5 L at 19 in, because chamfers bulge less than box corners. The body was
re-solved with CHERT's own ratio (82.5 / 73.81) and made 33.9 mm taller, then all cases were re-run.

Fixed list: frame interface unchanged (B-01 is CORRIE's flat panel on the same y_frame; hinge eyes, hooks, hood,
B-20, B-22 tabs at x +/-149, z 695 on the hinge band, IM1-IM3, under-straps, fairleads, float links). Fly stays in the
base pocket and is re-scaled to the shell. No hook-and-loop. Coil zips only. Beginner build: one walking-foot machine,
all body seams straight, plus CORRIE's two R 55 door corners.

## 3. Cloth sim CG (HA-LS-1 rev C), `form_sim.py`

The scenarios are CORRIE's rev C integration scenarios (corrie_PR{15,19,23}c, with the 1 kg pouch and the 85 mm spotter
in the left sleeve) with CHERT's flat pieces. Mesh h 40 for the CG runs; h 25, packed, at 19 in for the render
drape. Every case converged.

| Torso | Fill CG y (limit 205) | Rounding | Meat CG y (limit 190) | Rounding | CG z fill / meat |
|---|---|---|---|---|---|
| 15 in | 194.9 (margin 10.1; <= 198.9 with the 4 mm rounding bias) | 6 mm | **187.4 (margin 2.6; ~<= 188 raw)** | 1 mm | 533 / 541 |
| 19 in | 176.3 (28.7) | 6 mm | 169.0 (21.0) | 2 mm | 542 / 549 |
| 23 in | 135.9 (69.1) | 6 mm | 133.3 (56.7) | 2 mm | 550 / 555 |

Compared with CORRIE (11.4): fill 15 in 191.3 -> 194.9 and meat 15 in 184.4 -> 187.4. The chamfers move the
uniform-fill centroid forward, but the extra 34 mm of height needed to keep 85 L costs more than that. **Pass at every
torso, with a thinner 15 in meat margin than CORRIE.** The 15 in plumb-line CG test (corrie_body.md 12.4) is
mandatory for CHERT.

## 4. Mass (`form.knap_mass`, belt-independent bag system)

| Row | g |
|---|---:|
| CORRIE B.2 bag system: body group 533.1 + IMP-1 54.5 + IMP-2 40.3 + IMP-4 22.0 + IMP-6 11.1 + IMP-8 7.5 + fly 53.2 | 721.7 |
| - CORRIE shell (B-01, B-03 x2, B-05, B-02u, door, B-02h) + SH-01a/b kick appliques | -188.4 |
| + CHERT shell: B-01 37.1, B-03 x2 50.3, SH-F fangs 14.4, blade U 42.2 (630D), door 27.1, hinge band 9.2, hexagon floor 13.0 | +193.2 |
| collar pieces x perimeter 1234 / 1267 mm | -3.2 |
| #10 door zip 1227 vs 1254 mm | -0.5 |
| IMP-6R right-strap snack / GPS pocket (ASSUMPTION 17 g) | +17.0 |
| rain fly re-scaled to the CHERT shell (G-2 rule) | -0.4 |
| **CHERT bag system** | **739.3 g (1.63 lb)** |
| **Pack at belt M on H1: 3943 - 721.7 + 739.3** | **3960.6 g (8.73 lb)** |

The CORRIE number used is 721.7 g (corrie.py B.2, computed by `form.corrie_parts_g`).

## 5. Access (`form_loadout.py`, the corrie_loadout model, calibrated on CHERT's sims, belt M)

CHERT adds **IMP-6R**: a stretch pocket on the right J-strap, 110 x 210 mm face with a 50 mm bellows (about 0.9 L),
for snacks and GPS. It fixes CORRIE's snack miss on S-L belts.

| Loadout | Misses at belt M | Notes |
|---|---|---|
| Day hunt | 1: kill kit (kill class) | the CORRIE packing-order artifact (kill kit owns the door pocket by the IMP-4 rule) |
| 6-day elk | **0** | all belt sizes S-XXL: 0 |
| 8-day sheep | 3: bottle #2 (hourly), beanie/gloves and poles (glassing) | the taller body stacks them above the z 650 door hinge |

Phone, water bottle 1, snacks, inReach and the spotter/tripod are reachable with the pack on (or at glassing) on every
loadout. Bag CG with gear + 15 in peel: day 174.1, elk 167.1, sheep 179.5 mm (limit 205).

## 6. Build

32 cut pieces (CORRIE 33: +2 fangs, -3 kick appliques), 1 curved seam (the door U, as CORRIE), 1487 mm of zip,
**27.7 beginner hours** (CORRIE 28.6): about -1.3 h of camo applique, +0.4 h of fang and floor seams,
+0.2 h of hexagon pivots. Flat pieces develop with p99 strain <= 1.5 % (crease-crossing triangles in a planar-facet
development); see the true-scale pattern sheet `outputs/screens/20261110_bagE_6.png`
(SVG: `outputs/bag_comp_form/chert_pattern_sheet.svg`). Sewing order for the blade: sew the zip to the flat U and the
door first, then the U to the gussets. The creases form when the floor and the gussets go in. Notches mark the creases.

## 7. Renders (Blender Cycles, 1600 x 1200, 64 samples, `form_viz.py`)

| # | File | Shot |
|---|---|---|
| 1 | outputs/screens/20261110_bagE_1.png | hero 3/4 rear on the display form |
| 2 | outputs/screens/20261110_bagE_2.png | side profile, wearer's right |
| 3 | outputs/screens/20261110_bagE_3.png | access: door open |
| 4 | outputs/screens/20261110_bagE_4.png | feature: blade = camo break = door zip |
| 5 | outputs/screens/20261110_bagE_5.png | meat haul, bag floated 170 mm |
| 6 | outputs/screens/20261110_bagE_6.png | flat pattern sheet, true scale, owner camo at repeat |

The body is the h 25 cloth-sim drape of CHERT's own pieces, with the colour split cut exactly on the sim seams. The
wings, roll, pouch, tripod, sleeves and straps are placed geometry, the same method as CORRIE. In the float render the
170 mm shift is baked into a second GLB (`outputs/pack3d_chert/chert_haul.glb`), because the Cycles port does not
apply the viewer's float slide.

## 8. Weaknesses and risks

See `result.json` `risks`. The main ones: the 15 in meat CG margin is 2.6 mm; the door is narrower low down (163 vs
198 mm at z 110); the zip sits on a fold and is untested; the camo is 630D (heavier and stiffer, modelled as 330D);
the system is +17.6 g over CORRIE; there are sheep glassing misses above the hinge; the roll is 36 mm higher; and the
name and construction have had no legal clearance.

## 9. Assumptions (new)

- ASSUMPTION: the sim / rule volume ratio of the pilot (1.118) holds for the 34 mm taller body. Checked: the final runs
  give 85.0-86.7 L.
- ASSUMPTION: the camo 630D pieces behave like 330D in the cloth sim.
- ASSUMPTION: IMP-6R mass 17 g (IMP-6 11.1 g scaled by face area 1.47).
- ASSUMPTION: the fly scales with the cut outer-shell area (CORRIE's G-2 rule).
