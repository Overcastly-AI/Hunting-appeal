# BL-020: render-only cloth pass (roll-top, top pouch, part-full loads)

Date 2026-11-11. Code: `huntkit/viz3d/cloth_pass.py`. Tests: `tests/test_viz3d_cloth_pass.py`. How to call it:
`huntkit/viz3d/README.md`, section "Cloth pass". Shell: S15 (BL-009), wings deleted (owner, 2026-11-11), W1-W3 the
only outside straps, 19 in torso, CORRIE B.2 fittings.

**Nothing here is an engineering number.** The pass makes presentation geometry for renders. Volumes, CG, seam loads
and strains stay with the huntkit cloth sim (`huntkit/clothsim`, `analysis/shell_sweep.md`). No design changed.

## 1. Result in one paragraph

The three load states now differ the way a real pack does. Full is a taut bag with the collar standing 250 mm
(9.8 in) above the collar seam and a three-turn roll on top. The 6-day load has the collar rolled down to the body
(five turns, a fatter roll) and the bag ends 190 mm (7.5 in) lower. The day load is slack cloth cinched flat to the
frame by W1-W3, with long gathered folds, about 60 mm deep above the contents. The roll is no longer a tube with a
spiral drawn on its end: it is the collar's own length wound flat round the 20 mm hem stiffener, bent down at the ends
and clipped to the gussets. The pouch is draped cloth, but it still reads as a box (open defect 6). At the full load
the cloth stays on the huntkit drape: mean 2.2 mm, 99 % of vertices within 9.9 mm, away from the roll and the strap
lines; 0.24 % of those vertices are over the 15 mm limit (worst 21.6 mm), so the limit is **not met everywhere**
(section 4).

## 2. Method

Two stages, like the studio layer. Stage 1 runs in the repo's Python (numpy); stage 2 is Blender's cloth solver in the
bpy venv (`python -m huntkit.viz3d.cloth_pass --job <json>`).

| Ticket item | What the pass does | Where |
|---|---|---|
| Seed from the huntkit drape | The converged BL-009 full drape (`outputs/clothsim/shell_sweep_render/S15_PR19_fine/skin_full.pkl`, h 25 mm, rounding 3 mm) is the start for every state. Body nodes are the same nodes in every state, so they start exactly on it. The part-full meshes differ only in collar height (BL-009's `dome_h`: 70 mm day, 90 mm 6-day); the rest of the collar is in the roll. The huntkit day and 6-day drapes did not converge and are not used. The mesh is subdivided twice (6.3 mm edges, 28 000-36 000 vertices). The rest shape is the flat-panel assembly X0, so the cloth has its true area. | `seed`, `state_mesh`, `subdivide` |
| Pin to the frame interface | Every vertex of the frame-face panel B-01 is pinned where the huntkit drape left it. At the full load the floor B-05 is pinned too (it sits in the under-strap cradle). | `prepare` |
| Contents proxy | Full: the huntkit drape itself, 5 mm inside, cut flat 20 mm under the roll and narrowed there so the closure's ears are cloth, not contents: 83.8 L. Day and 6-day: a rounded block on the frame face from the floor up, its depth solved for the volume: 12.0 L (330 wide, to z 470, 114 mm deep) and 45.0 L (372 wide, to z 790, 187 mm deep). | `drape_proxy`, `block_proxy` |
| Cinch W1-W3 | Each strap is a 25 mm wide slab collider. It starts on the taut line round the seed and closes, over 70 frames, to the taut line round the contents plus a cloth-pile allowance (2.5 / 4 / 12 mm for full / 6-day / day). The taut line is the convex hull in plan of whatever lies under the strap; the strap climbs evenly from its right frame anchor to its left one (W1 z 80 to 250, W2 z 250 to 420, W3 level at z 702.6, from the BL-009 scenario). The cloth under and between the straps is free and folds by itself. | `taut_path`, `strap_slab` |
| Roll clips | The closure line (the top line of the collar, 555 mm long) is carried from where the huntkit drape has it to the line where the roll starts: level over the middle 300 mm, then bent down at R 60 toward the clip tabs on the gussets (60 mm below the collar seam). The bend is 75 deg at full, 45 deg at 6-day and 18 deg at day: the ends stop 45 mm above the tab. | `arch`, `bend_for_drop` |
| Rolled collar | Not solved as cloth (section 6). The collar length that is not standing (175 mm at full = fabric height 494.8 less the 319.8 to the fill line; 405 and 425 mm part-full) is wound as a flat-folded spiral: flats of 20 mm (the HDPE hem stiffener), half-thickness 1 mm at the core, growing 2 mm a turn. That gives 2.8 turns, 31 x 11 mm at full; 5.2 turns, 41 x 21 mm at 6-day; 5.3 turns at day. The spiral is swept along the lip line, given cloth thickness, and goes through the fabric pass. | `roll_section`, `roll_mesh` |
| Pouch on the roll | A second small solve: the pouch's six flat panels (280 x 190 x 60, `corrie.POUCH`) start as the drafted box and drape under gravity, with self collision, over a contents block (1.6 L) and a height field of the roll and collar under it. | `pouch`, `box_mesh` |
| Fittings | The solved cloth goes back in vertex order, so it is handed to the existing CORRIE B.2 builders as their `sim_skin`: door, kick plate, floor, seams, zip, tabs and the open-door view are all built on the solved cloth. Wings, the lofted roll and the lofted pouch are dropped. W1-W3 are redrawn on the taut line round the solved cloth, with a ladder lock each. | `s15_scene` |

Solver settings (`ClothParams`, all picture choices): tension and compression 40, shear 12, bending 0.9, self clearance
1.6 mm, collider clearance 2 mm, 8 substeps, 70 frames of cinch and 25 of settling.

## 3. Load states (level 2, 19 in)

| State | Contents proxy | Collar standing | Collar in the roll | Roll turns, section | Roll-end bend | Closed volume of the solved cloth | W1 / W2 / W3 taut length, seed to cinched | Solve time |
|---|---|---|---|---|---|---|---|---|
| Day | 12.0 L (732 cu in) | 70 mm (2.8 in) | 425 mm (16.7 in) | 5.3, 42 x 22 mm | 18 deg | 24.4 L | 700 to 504, 731 to 503, 736 to 540 mm | 149 s |
| 6-day | 45.0 L (2746 cu in) | 90 mm (3.5 in) | 405 mm (15.9 in) | 5.2, 41 x 21 mm | 45 deg | 53.4 L | 700 to 648, 731 to 662, 736 to 773 mm | 173 s |
| Full | 83.8 L (5114 cu in) | 320 mm (12.6 in) | 175 mm (6.9 in) | 2.8, 31 x 11 mm | 75 deg | 89.8 L (seed 91.3 L) | 700 to 711, 731 to 711, 736 to 755 mm | 492 s |

The closed volume of the solved cloth is larger than the contents because slack cloth holds air; it is a property of
the picture, not a capacity. "Taut length" excludes the two legs to the frame anchors. At full the straps do not
shorten (the bag is full); W3 at 6-day reads longer because the shortened collar starts from its drafted shape.

ASSUMPTIONS that shape the picture, and what settles each:
- RS-1 (from BL-009): day is about 12 L and 6 kg, 6-day about 45 L and 22 kg. Settled by photographs of the prototype
  packed to the loadouts.
- Proxy footprints (330 x 425 mm day, 372 x 749 mm 6-day) and the 12 mm cloth pile under a day-load strap. Same test.
- Roll: 2 mm a turn of loose lay; ends bend at R 60; ends stop 45 mm above the clip tab. Settled by rolling the
  prototype's collar and measuring the roll.
- Cloth stiffness (bending 0.9) and the pouch's limpness. Settled by the same photographs.

## 4. Departure from the huntkit drape at the full load

Distance of each vertex of the solved cloth from the same vertex of the seed (35 778 vertices). "Body" leaves out
vertices within 40 mm of a strap line and within 150 mm of the closure line (65 % of the vertices remain).

| Region | Mean | 99th percentile | Max | Share over 15 mm |
|---|---|---|---|---|
| Everything | 4.6 mm (0.18 in) | - | 139.6 mm (5.5 in) | - |
| Body (away from roll and straps) | 2.2 mm (0.09 in) | 9.9 mm (0.39 in) | 21.6 mm (0.85 in) | 0.24 % |
| Body, with tripod and scope pod carried | 2.4 mm | 10.2 mm | 24.6 mm | 0.35 % |

- The 139.6 mm is at the roll: the huntkit drape closes the collar as a level line with ears; the pass bends the ears
  down to the clips.
- The ticket's limit is 15 mm. It is met by 99.76 % of the body vertices and missed by 0.24 % (worst 21.6 mm). Before
  the floor was pinned the miss was 1.1 % (worst 37.5 mm), mostly at the floor corners. What is left is near the B-22
  guy tabs and the hinge band (z 500-700): the huntkit drape has tie and hook forces there that the pass does not
  model, so the cloth relaxes outward. Closing it means adding those ties as pins.
- Part-full states depart by design (day: mean 74 mm, max 250 mm): the huntkit sim has no converged shape to compare.

## 5. BL-018 open defects (task 2)

| BL-018 # | Defect | Status now |
|---|---|---|
| 10 | Grey shard floating under the phone pocket on the chest | **Fixed.** It was the legacy phone slab `imp6_phone@t19` (75 x 26 x 14 mm, drawn lying flat below the pocket) and its cord. Both are dropped in `studio.corrie_b2_scene` and in `s15_scene`. |
| 11 | Mottled band beside the door seam and under the hinge-band strap | **Not traced, not fixed.** Not looked at in this ticket beyond the full-pack frames, where it is not visible at 1600 px. It needs a zip macro on the new skin. |
| 12 | Dimples under the pouch G-hooks | **Fixed by removal of the cause.** The dimples were strap dent lines of parts that were later dropped, plus hooks placed on the cloth. `s15_scene` rebuilds the dent list from the straps that are still there, and the pouch straps and hooks now hang clear of the cloth and leave no dent. |
| 14 | No webbing through the 50 mm belt buckle | **Partly.** A 38 mm tab now runs from each heavy ladder lock into the buckle's ends (`belt_tabs`), so the buckle no longer sits on a gap. The webbing ends inside the buckle body; it is not wrapped round the bars. |
| 14 | Belt ladder locks and sternum buckle without wraps | **Open.** Not touched. |

## 6. Defect log for this ticket

| # | Seen in | Defect | Status |
|---|---|---|---|
| 1 | first solve | cloth collapsed inward through the contents | fixed: colliders wound outward (`outward`) |
| 2 | first full solve | W1 dug a 30 mm notch in the right side | fixed: straps are helices (climb evenly between anchor heights), not planes |
| 3 | full, level 1 | a flat shelf and a thin tent under the roll | fixed: contents run to 20 mm under the roll and narrow there |
| 4 | day, pouch | pouch thrown 130 mm and the solve slowed to minutes | fixed: pouch drapes on one height field of what is under it; 9-17 s |
| 5 | day | the 280 x 190 pouch overhangs the flattened top by about 110 mm and tips | not solved: the day shots show the pouch off (it is removable). Owner note in the report. |
| 6 | roll macro, heroes | the pouch still reads as a box with a flat top and sharp edges, and its middle hides the roll | OPEN. A limper setting (vertex mass 0.012, bending 0.18) sags properly but tips over; it needs its four straps as pins. The carry scene uses that limper pouch, so the pouch differs slightly between scenes. |
| 7 | all | the roll is geometry, not solved cloth: clean spiral, no pinched gusset cloth at its ends | OPEN (section 7) |
| 8 | 6-day | reads a little boxy: the contents proxy is one rounded block | open, cosmetic. Several smaller proxies would fix it. |
| 9 | day | the kick plate and floor fold diagonally; the frame's lower bar shows under the bag | left as is: that is what an 85 L shell on a 12 L load does. Check against the prototype. |
| 10 | door open | W1 and W2 cross the door | handled: they are hidden in the door shot (they are unhooked to open the door); their dents in the cloth remain |
| 11 | belt | the 50 mm buckle sits about 20 mm off centre | open (legacy placement) |
| 12 | carry | tripod and scope are the legacy shapes; the pod is a plain capsule sleeve; W3 does not touch the pod (it ends below it) | open, cosmetic |
| 13 | all | W1-W3 tails (150 mm, in keeper loops) are not drawn beyond the 34 mm at the lock; the legs to the frame anchors are not drawn | open |
| 14 | cache | a changed input was once reused from cache | fixed: the cache key is a hash of the job inputs |

## 7. Honest limits

- **The roll is not simulated.** Rolling a collar three to five turns with self contact is beyond what was stable in
  the time. The roll's size comes from the collar length and three stated numbers; its ends are a clean spiral, where a
  real one shows pinched gusset cloth.
- **Part-full shapes are plausible, not validated.** They come from a contents block and a cloth stiffness chosen by
  eye. No number should be read off them.
- **Blender's solver units are not SI.** Stiffness and vertex mass are tuning values. The areal mass (0.21 kg/m2, from
  the 180 g/m2 record plus coat) has almost no effect because the cloth is stiff against its own weight.
- **One torso, one shell.** Run at 19 in on S15. Other torsos and shells go through the same functions
  (`shell=`, `torso=`) but were not run.
- **Level 2 is 6.3 mm edges**: folds under about 15 mm wavelength come from the BL-018 fabric pass (5 mm clamp), not
  from the solve.

## 8. Shots

`outputs/screens/20261111_BL020_<n>.png`; the five marked * are copied to `docs/screens/`.

1. * hero, 3/4 rear, full
2. side, full
3. * hero, same camera, 6-day
4. * hero, same camera, day
5. door open, full
6. * macro of the rolled closure, full
7. * side carry: tripod under W1-W3 (right)
8. side carry: scope pod under W1-W2 (left)
9. hipbelt front (buckle tabs)
10. side, day
11. the three load states side by side (sheet of 4, 3 and 1)
