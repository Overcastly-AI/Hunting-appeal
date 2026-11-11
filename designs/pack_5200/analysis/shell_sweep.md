# BL-009 Bag shape sweep: CG margin and a cleaner silhouette

pack-designer, 2026-11-10/11. Code: `designs/pack_5200/concepts/shell_sweep.py`. Scenarios and stored results:
`designs/pack_5200/concepts/shell_sweep_scenarios/` (`ss_PR{15,19,23}.yaml`, `shell_sweep_results.json`). Tests:
`tests/test_shell_sweep.py`. Sims: `outputs/clothsim/shell_sweep/<shell>_PR<torso>/` (not tracked; regenerate with
`python designs/pack_5200/concepts/shell_sweep.py run <shell> --torso <t>`).

## 1. Result in one paragraph

**Chosen shell: S15.** It is a full-width box: 394 mm (15.5 in) wide from the floor to the shoulder crease, tapering
to 360 mm (14.2 in) at the collar seam. Depth is 160 mm (6.3 in) at the base, 205 mm (8.1 in) at the shoulder crease
and 195 mm (7.7 in) at the collar seam. The collar seam sits at z 745 and the fill line at 40.5 in, 8.7 mm higher than
CORRIE. **Goal met at 15 in, as simulated:** meat CG **171.7 mm** (goal ≤ 176, rev C 190) and fill CG **178.5 mm**
(goal ≤ 190, rev C 205), both converged. Simulated fill volume is **86.1 L (5252 cu in)**, inside 85 ±3. Against the
CORRIE control in the same run (186.3 / 191.5 mm, 88.2 L), that is **−14.6 mm meat and −13.0 mm fill**. Meat margin
to rev C is 18.3 mm as simulated and ≥ 14.3 mm after the +4 mm rounding bias. The silhouette no longer mushrooms. On
the loaded fill case the upper body is 1 mm wider per side than the mid-body, against 58 mm on CORRIE. The cost is
width low on the bag: loaded, S15 is 415–434 mm (16.3–17.1 in) wide at hip and elbow height (z 85–235), against
334–367 mm on CORRIE. That is an owner call (section 7).

## 2. Method

**Generator.** `ShellParams(d_bot, d_sh, d_col, a_bot, a_top, z_c)` defines a `bag_concepts.Concept` subclass. Half-width
runs linearly from a_bot (z 35) to 196.8 (z 631.2, shoulder crease), then linearly to a_top at the collar seam. The aft
face is two planes with one crease at z 631.2. The frame face is CORRIE's (stay line + 20 mm + the 30 mm setback
Z-fold), so every frame-interface station is unchanged. Every piece is a flat panel, developed by the sim with p99
strain ≤ 0.25 %. The shell family adds no curved seam. The only curved seam is CORRIE's door U, which is out of scope
(BL-011). "Gusset length" is the side gusset's top edge, d_col.

**Sim.** The sims use CORRIE's own loader (`huntkit/clothsim/corrie_bag.py`), unedited: `install()` swaps
`corrie.make` for the shell at run time. The scenarios `ss_PR{t}` extend `corrie_PR{t}c` unchanged:
- h 40 mm;
- 6 mm contact rounding with a 4/3/2/1/0 continuation, each case reported at the lowest stage that converged;
- the 1 kg pouch (1.088 kg) on the closed roll;
- the 85 mm spotter (1.955 kg) in the left-wing sleeve;
- B-22 guys at x ±149, z 695, and the crown hood.

So each row differs from CORRIE only in shape. Cases: packed (0.5 kPa, sets the contents volume), fill 68 kg, meat
30 + 38 kg. CG is the mass-weighted CG including pouch and scope (`cg_with_external_mm`), as in corrie_body.md §11.4.
One sim was run at a time.

**Volume rule.** "85 L ±3" is checked on the **simulated closed volume of the fill case**, the same rule team B used
for FELL. The concept integrator's rule volume is used only to pre-size z_c. ASSUMPTION RATIO-1 put sim / rule at
1.161, measured on CORRIE. Round 1 showed full-width shells bulge more, at 1.20–1.21. Round 2 was sized on that
ratio, and each row reports its own simulated volume.

**Reproducibility.** The S00 control is CORRIE rev B, re-run here. Fill came out 191.5 mm (corrie_PR15c 191.3) and
volume 88.2 L (88.1). Meat came out 186.3 mm against corrie_PR15c's 184.4 mm, a re-run scatter of **1.9 mm** at the
same 6 mm rounding stage. The likely cause is the stalled-ramp path being sensitive to thread count (these runs use
`OMP_NUM_THREADS=2`). Read every CG here as ±2 mm on top of the +4 mm rounding bias.

**Silhouette numbers** (from the loaded `depth_by_z` profile, 50 mm bands):
- `mushroom`: widest half-width at z 585–735 minus the mean mid-body half-width at z 235–335;
- `lean`: furthest aft point at z 585–785 minus the furthest aft point at z 235–335.

The sim closes the collar flat at the fill line on every shell, so the collar ears are not counted.

## 3. Sweep at 15 in (coarse h 40 mm, fill and meat cases)

Columns:
- **d_bot / d_sh / d_col:** depth at the base, at the shoulder crease (z 631.2) and at the collar seam.
- **Width:** overall width at the base and at the collar seam.
- **Rounding:** the contact-rounding stage the case was reported at. A case at > 0 mm reads up to +4 mm higher.
- **Gusset wrinkle:** % of B-03 area in compression.
- **Seam:** the case's critical seam, with its SF against the fabric or seam strength.

Rows round 1 (S00–S13): z_c solved for 86 L at RATIO-1. Rows round 2 (S14–S17): z_c fixed at 745, depth sized at
1.205.

| Shell | Torso | d_bot / d_sh / d_col | base / top width | z_c (fill height) | Case | Converged (rounding) | Closed L (cu in) | CG y / z mm | warp / weft % | gusset wrinkle % | worst seam N/mm (SF) | mushroom / lean mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S00 | 15 | 170 / 240 / 240 | 272 / 394 | 736.3 (40.2 in) | fill | yes (6 mm) | 88.2 (5382) | 191.5 / 497 | 1.9 / 1.4 | 96 | 1.43 B-03L/B-05 (14) | 58 / 100 |
| S00 | 15 | 170 / 240 / 240 | 272 / 394 | 736.3 (40.2 in) | meat | yes (6 mm) | 88.2 (5385) | 186.3 / 507 | 1.9 / 1.2 | 95 | 1.77 B-03L/B-05 (12) | 50 / 96 |
| S01 | 15 | 165 / 232 / 232 | 272 / 394 | 736.3 (40.2 in) | fill | yes (6 mm) | 86.2 (5262) | 186.6 / 500 | 1.9 / 1.5 | 96 | 0.69 B-02h/B-06 (17) | 54 / 91 |
| S01 | 15 | 165 / 232 / 232 | 272 / 394 | 736.3 (40.2 in) | meat | yes (6 mm) | 86.1 (5253) | 178.2 / 510 | 1.5 / 1.0 | 95 | 1.30 B-01/B-05 (21) | 47 / 86 |
| S02 | 15 | 165 / 215 / 215 | 340 / 394 | 744.0 (40.5 in) | fill | yes (6 mm) | 87.8 (5356) | 185.3 / 482 | 3.5 / 2.6 | 97 | 1.52 B-02door/B-02u (14) | 34 / 94 |
| S02 | 15 | 165 / 215 / 215 | 340 / 394 | 744.0 (40.5 in) | meat | yes (6 mm) | 88.2 (5380) | 170.9 / 497 | 2.7 / 1.6 | 95 | 0.91 B-02door/B-02u (23) | 23 / 79 |
| S03 | 15 | 160 / 210 / 210 | 340 / 394 | 765.1 (41.3 in) | fill | NO (res 1.08 N) | 88.4 (5394) | 188.8 / 491 | 3.4 / 2.9 | 99 | 1.70 B-02door/B-02u (12) | 28 / 104 |
| S03 | 15 | 160 / 210 / 210 | 340 / 394 | 765.1 (41.3 in) | meat | yes (6 mm) | 88.3 (5386) | 181.4 / 502 | 2.8 / 1.9 | 96 | 1.10 B-02door/B-02u (19) | 24 / 103 |
| S04 | 15 | 150 / 195 / 195 | 340 / 394 | 828.1 (43.8 in) | fill | yes (4 mm) | 90.5 (5523) | 197.9 / 520 | 3.3 / 2.8 | 94 | 1.64 B-02door/B-02u (12) | 21 / 138 |
| S04 | 15 | 150 / 195 / 195 | 340 / 394 | 828.1 (43.8 in) | meat | yes (6 mm) | 90.6 (5531) | 179.5 / 539 | 2.7 / 1.7 | 91 | 0.95 B-02door/B-02u (22) | 17 / 114 |
| S05 | 15 | 155 / 205 / 205 | 394 / 394 | 751.3 (40.8 in) | fill | yes (3 mm) | 89.7 (5474) | 179.2 / 477 | 1.5 / 1.1 | 98 | 0.61 B-02h/B-06 (19) | 15 / 90 |
| S05 | 15 | 155 / 205 / 205 | 394 / 394 | 751.3 (40.8 in) | meat | yes (6 mm) | 89.6 (5470) | 170.4 / 487 | 1.0 / 0.9 | 94 | 0.47 B-02h/B-06 (25) | 11 / 85 |
| S06 | 15 | 160 / 210 / 210 | 272 / 394 | 810.6 (43.1 in) | fill | yes (4 mm) | 89.3 (5450) | 191.3 / 536 | 2.0 / 1.9 | 93 | 1.42 B-02door/B-02u (14) | 36 / 120 |
| S06 | 15 | 160 / 210 / 210 | 272 / 394 | 810.6 (43.1 in) | meat | yes (6 mm) | 89.5 (5464) | 176.6 / 552 | 1.8 / 1.5 | 90 | 1.10 B-02door/B-02u (19) | 28 / 104 |
| S07 | 15 | 160 / 210 / 210 | 394 / 350 | 762.5 (41.2 in) | fill | yes (3 mm) | 89.0 (5429) | 184.2 / 468 | 1.3 / 1.6 | 97 | 0.41 B-02h/B-06 (28) | -3 / 102 |
| S07 | 15 | 160 / 210 / 210 | 394 / 350 | 762.5 (41.2 in) | meat | yes (6 mm) | 89.1 (5439) | 172.6 / 481 | 1.0 / 1.1 | 96 | 1.03 B-01/B-05 (27) | -10 / 78 |
| S08 | 15 | 160 / 210 / 210 | 394 / 310 | 796.7 (42.6 in) | fill | yes (4 mm) | 88.1 (5376) | 186.5 / 469 | 1.5 / 1.6 | 99 | 0.42 B-01/B-06 (27) | -6 / 120 |
| S08 | 15 | 160 / 210 / 210 | 394 / 310 | 796.7 (42.6 in) | meat | yes (6 mm) | 88.0 (5373) | 179.7 / 481 | 1.2 / 1.1 | 98 | 1.04 B-01/B-05 (26) | -10 / 102 |
| S09 | 15 | 160 / 210 / 180 | 394 / 350 | 804.1 (42.9 in) | fill | yes (3 mm) | 91.2 (5562) | 179.8 / 485 | 1.3 / 1.4 | 95 | 0.81 B-02h/B-02u (25) | -9 / 94 |
| S09 | 15 | 160 / 210 / 180 | 394 / 350 | 804.1 (42.9 in) | meat | yes (6 mm) | 90.8 (5538) | 174.5 / 493 | 1.1 / 1.1 | 92 | 1.04 B-01/B-05 (26) | -11 / 84 |
| S10 | 15 | 175 / 215 / 160 | 394 / 350 | 799.2 (42.7 in) | fill | yes (4 mm) | 90.8 (5541) | 183.0 / 468 | 1.2 / 1.5 | 92 | 0.92 B-02h/B-02u (22) | -9 / 98 |
| S10 | 15 | 175 / 215 / 160 | 394 / 350 | 799.2 (42.7 in) | meat | yes (6 mm) | 90.1 (5499) | 177.6 / 476 | 1.1 / 1.2 | 95 | 1.12 B-01/B-05 (24) | -13 / 83 |
| S11 | 15 | 185 / 185 / 185 | 394 / 394 | 772.0 (41.6 in) | fill | yes (4 mm) | 90.1 (5498) | 178.3 / 466 | 1.4 / 1.3 | 98 | 0.74 B-02door/B-02u (28) | 6 / 100 |
| S11 | 15 | 185 / 185 / 185 | 394 / 394 | 772.0 (41.6 in) | meat | yes (6 mm) | 90.1 (5500) | 166.3 / 481 | 1.1 / 1.0 | 98 | 1.10 B-01/B-05 (25) | 1 / 83 |
| S12 | 15 | 210 / 190 / 170 | 394 / 350 | 777.6 (41.8 in) | fill | yes (4 mm) | 88.8 (5418) | 185.8 / 434 | 1.1 / 1.7 | 97 | 0.80 B-03L/B-05 (26) | -10 / 116 |
| S12 | 15 | 210 / 190 / 170 | 394 / 350 | 777.6 (41.8 in) | meat | yes (6 mm) | 89.2 (5441) | 175.5 / 452 | 1.0 / 1.3 | 97 | 1.08 B-01/B-05 (25) | -13 / 89 |
| S13 | 15 | 140 / 210 / 210 | 394 / 394 | 757.4 (41.0 in) | fill | yes (3 mm) | 89.7 (5475) | 180.8 / 487 | 1.4 / 1.3 | 94 | 0.97 B-01/B-05 (28) | 19 / 95 |
| S13 | 15 | 140 / 210 / 210 | 394 / 394 | 757.4 (41.0 in) | meat | yes (6 mm) | 89.3 (5447) | 178.2 / 494 | 1.2 / 1.3 | 93 | 1.05 B-01/B-05 (26) | 19 / 92 |
| S14 | 15 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | fill | yes (3 mm) | 87.2 (5318) | 180.6 / 472 | 1.4 / 1.2 | 99 | 0.66 B-02h/B-06 (17) | 16 / 98 |
| S14 | 15 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | meat | yes (6 mm) | 86.9 (5302) | 173.7 / 482 | 1.1 / 1.1 | 97 | 0.52 B-02h/B-06 (22) | 14 / 94 |
| S15 | 15 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | fill | yes (3 mm) | 86.1 (5252) | 178.5 / 460 | 1.4 / 1.2 | 99 | 0.49 B-02h/B-06 (24) | 1 / 92 |
| S15 | 15 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | meat | yes (6 mm) | 85.8 (5236) | 171.7 / 469 | 1.1 / 1.1 | 98 | 1.04 B-01/B-05 (26) | -4 / 76 |
| S16 | 15 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | fill | yes (3 mm) | 85.7 (5231) | 178.8 / 484 | 2.4 / 1.4 | 99 | 1.23 B-02door/B-02u (17) | 26 / 90 |
| S16 | 15 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | meat | yes (2 mm) | 85.6 (5221) | 169.6 / 495 | 1.9 / 1.0 | 96 | 0.93 B-02door/B-02u (22) | 22 / 85 |
| S17 | 15 | 155 / 205 / 205 | 394 / 350 | 745.0 (40.5 in) | fill | yes (3 mm) | 84.5 (5155) | 178.9 / 458 | 1.4 / 1.2 | 100 | 0.45 B-02h/B-06 (26) | 4 / 95 |
| S17 | 15 | 155 / 205 / 205 | 394 / 350 | 745.0 (40.5 in) | meat | yes (6 mm) | 84.6 (5161) | 171.8 / 469 | 1.2 / 1.0 | 100 | 1.03 B-01/B-05 (26) | 0 / 90 |

Unconverged rows are not used for the choice. There is one: S03 fill, residual 1.08 N.

**What the sweep says.**
1. **Height costs CG as much as depth buys it.** The loaded bag leans aft above the shoulders by 76–138 mm (`lean`).
   So every mm of height is carried at the worst lever. S04 (−45 mm depth, z_c 828) has a worse meat CG (179.5) than
   S02 (−25 mm, z_c 744, 170.9). The best shells are low (z_c 745–772), and the collar seam cannot go below about
   z 736 without putting the B-22 tabs into it (section 5).
2. **A wide base is the lever.** Putting volume low and on the frame line drops CG z by 20–60 mm and CG y by 10–15 mm.
   Every shell with a base ≥ 340 mm is under 176 mm meat when its height is kept low. With CORRIE's 272 mm base, the
   same depth cut (S06) needs z_c 811 and lands at 176.6.
3. **Full-width shells over-fill.** Flat 394 mm faces bulge more (sim / rule 1.20 against 1.16). Round 1's wide shells
   were 88.8–91.2 L, outside the band. Round 2 fixed that with 5–10 mm less depth at z_c 745.
4. **Width taper and gusset taper remove the mushroom.** Any taper to ≤ 360 mm at the collar seam gives
   mushroom ≤ 1 mm. CORRIE (S00) is 50–58 mm, a narrow base with a full-width top. The tapers cost nothing in CG
   (S07/S15/S17 against S05/S14).
5. **The gussets stay wrinkled on every shell (90–100 %).** Shape does not fix the side-gusset wrinkling finding
   (corrie_body.md §5a item 2). It is excess cloth at the box corners under the 68 kg fill, at warp/weft ≤ 4.6 %, and
   it is a property of the box family. The worst seam load moves off the B-03/B-05 corner, 1.77 N/mm on CORRIE, to
   B-01/B-05 at about 1.05 N/mm on the wide-base shells (SF 23–28 against 12). It does not get worse.

## 4. Best three at 19 and 23 in, and head clearance R-28

Picked from round 2: S15 (taper, best balance), S16 (350 mm base, the elbow-room option) and S14 (plain full-width
box). All three are converged at 15 in, in the volume band and meet the goal.

| Shell | Torso | d_bot / d_sh / d_col | base / top width | z_c (fill height) | Case | Converged (rounding) | Closed L (cu in) | CG y / z mm | warp / weft % | gusset wrinkle % | worst seam N/mm (SF) | mushroom / lean mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S15 | 19 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | fill | yes (4 mm) | 86.4 (5270) | 156.5 / 475 | 1.8 / 1.0 | 100 | 1.17 B-02h/B-02u (18) | -2 / 58 |
| S15 | 19 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | meat | yes (6 mm) | 85.9 (5244) | 152.6 / 482 | 1.1 / 0.9 | 99 | 1.01 B-01/B-05 (27) | -3 / 53 |
| S16 | 19 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | fill | yes (6 mm) | 85.6 (5224) | 156.1 / 498 | 4.6 / 1.2 | 99 | 1.21 B-02door/B-02u (17) | 18 / 64 |
| S16 | 19 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | meat | yes (6 mm) | 85.4 (5213) | 150.5 / 507 | 3.1 / 1.1 | 99 | 1.12 B-02door/B-02u (18) | 15 / 60 |
| S14 | 19 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | fill | yes (3 mm) | 87.6 (5348) | 153.9 / 490 | 1.5 / 1.3 | 99 | 1.07 B-02h/B-02u (19) | 6 / 57 |
| S14 | 19 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | meat | yes (6 mm) | 87.4 (5332) | 143.9 / 500 | 1.0 / 1.1 | 99 | 0.98 B-01/B-05 (28) | 2 / 52 |
| S15 | 23 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | fill | NO (res 0.54 N) | 84.7 (5169) | 126.6 / 483 | 1.5 / 1.2 | 99 | 1.22 B-02h/B-02u (17) | -4 / 8 |
| S15 | 23 | 160 / 205 / 195 | 394 / 360 | 745.0 (40.5 in) | meat | yes (6 mm) | 83.9 (5118) | 120.8 / 488 | 1.1 / 0.9 | 96 | 0.76 B-03L/B-05 (27) | -6 / 10 |
| S16 | 23 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | fill | yes (6 mm) | 83.4 (5090) | 111.5 / 502 | 4.1 / 1.3 | 94 | 1.21 B-02h/B-02u (17) | 10 / 10 |
| S16 | 23 | 155 / 205 / 205 | 350 / 394 | 745.0 (40.5 in) | meat | yes (6 mm) | 83.2 (5076) | 117.6 / 511 | 3.2 / 0.8 | 92 | 0.85 B-02h/B-02u (24) | 10 / 15 |
| S14 | 23 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | fill | yes (3 mm) | 84.5 (5158) | 109.4 / 485 | 1.3 / 1.7 | 90 | 0.90 B-01/B-03R (23) | 3 / 3 |
| S14 | 23 | 150 / 200 / 200 | 394 / 394 | 745.0 (40.5 in) | meat | yes (6 mm) | 84.9 (5180) | 118.5 / 503 | 1.1 / 1.0 | 95 | 0.96 B-01/B-05 (29) | 5 / 13 |

**R-28** uses `huntkit.gendesign.attach_system.r28_loaded`. The simulated wall is each shell's own drafted fore face
minus the loaded fore face, per 50 mm band (`attach_system.wall_move` logic). The shell's own drafted face is used
because SPINE's drafted face lies inside a box above the collar seam. Cells give first contact in deg (requirement
> 30) and the gap at 30 deg in mm (format of bag_attachment.md §1). The CORRIE control was computed the same way from
`corrie_PR{t}c`.

| Torso | Case | CORRIE (same method) | S15 | S16 | S14 |
|---|---|---|---|---|---|
| 15 | fill | 33 / 4.9 pass | 33 / 4.9 pass | 33 / 4.7 pass | 33 / 4.9 pass |
| 15 | meat | 33 / 4.9 pass | 33 / 4.9 pass | **27 / 0.0 FAIL** | 33 / 4.9 pass |
| 19 | fill | 33 / 4.9 pass | 33 / 4.9 pass | 33 / 4.9 pass | 32 / 3.7 pass |
| 19 | meat | 33 / 4.9 pass | 33 / 4.9 pass | **30 / 0.0 FAIL** | **26 / 0.0 FAIL** |
| 23 | fill | **17 / 0.0 FAIL** | **22 / 0.0 FAIL** (unconverged) | **4 / 0.0 FAIL** | **5 / 0.0 FAIL** |
| 23 | meat | **19 / 0.0 FAIL** | **20 / 0.0 FAIL** | **15 / 0.0 FAIL** | **17 / 0.0 FAIL** |

- At 15 and 19 in, S15 matches the published check (33 deg / 4.9 mm, where the bar on the crown governs). S16 and
  S14 let the upper wall come toward the head in the meat case.
- **At 23 in every shell fails by this method, CORRIE included** (17 / 19 deg). The 23 in sims carry the bag about
  50 mm toward the head relative to its drafted position at z 535–735, so either the bag really sits that far forward
  at the 23 in crown setting, or the drafted-to-loaded subtraction is wrong for a frame that moves with the torso
  setting. This is not a shape effect: S15 is the best of the four and 3–5 deg better than CORRIE. It is a CORRIE-wide
  open item, listed under "Found, not fixed".

19 / 23 in CG (all converged except S15 23 in fill, residual 0.54 N; a retry with one thread stalled the same way):

| Shell | 19 in fill / meat | 23 in fill / meat | Volume 19 / 23 in (fill) |
|---|---|---|---|
| CORRIE (corrie_PR19c / 23c) | 172.4 / 167.2 | 131.2 / 134.1 | 88.4 / 87.0 L |
| **S15** | **156.5 / 152.6** | 126.6 (unconverged) / **120.8** | 86.4 / 84.7 L |
| S16 | 156.1 / 150.5 | 111.5 / 117.6 | 85.6 / 83.4 L |
| S14 | 153.9 / 143.9 | 109.4 / 118.5 | 87.6 / 84.5 L |

Every case is far inside rev C at 19 and 23 in.

## 5. Chosen shell S15 and the frame interface (task 4)

DECISION: **S15**. S16 has the best 15 in meat number (169.6 mm, reported at 2 mm rounding), but it fails R-28 in the
meat case at 15 and 19 in, and its narrower base flares at the top again (mushroom 22–26 mm). S14 over-fills (87.2 L),
fails R-28 at 19 in meat, and has no taper. S15 meets every goal number, sits mid-band on volume, has the cleanest
silhouette, and its R-28 is the same as CORRIE's or better at every torso.

| Parameter | S15 | CORRIE rev B |
|---|---|---|
| Depth at base / shoulder crease / collar seam | 160 / 205 / 195 mm (6.3 / 8.1 / 7.7 in) | 170 / 240 / 240 mm |
| Width at base / shoulder crease / collar seam | 394 / 394 / 360 mm (15.5 / 15.5 / 14.2 in) | 272 / 394 / 394 mm |
| Collar seam / fill line | z 745.0 / 1064.8 (fill height 40.5 in) | z 736.3 / 1056.1 (40.2 in) |
| Height cost | +8.7 mm (+0.34 in) | — |
| Rule volume (integrator) / simulated fill / packed | 71.1 / 86.1 / 91.1 L | 75.9 / 88.2 / 92.8 L |
| 15 in meat / fill CG (sim) | 171.7 / 178.5 mm | 186.3 / 191.5 mm |
| CG z, meat case | 469 mm | 507 mm |

**Interface check.** Each check takes the S15 geometry from `shell_sweep.geometry()` and the limit from
bag_attachment.md / corrie.py:
- **B-22 guy tabs** (50 × 60, centre x ±149, z 695; span z 665–725):
  - 20.0 mm below the collar seam at z 745 (CORRIE: 11.3);
  - 15.0 mm above the door hinge at z 650 (unchanged);
  - 13.4 mm inside the aft corner seam at z 695 (half-width 187.4 there after the taper, against 22.8 on CORRIE).

  All three are ≥ 10 mm (ASSUMPTION TAB-1: 10 mm clear of a seam line for the double-row perimeter stitch and the
  binding). The tabs stay on the hinge band B-02h, a 330D shell piece, as on CORRIE. A taper to 175 (S17) leaves only
  10.6 mm at the corner. Do not taper further without moving the tabs inboard.
- **B-20 hood ladders** (frame side, x ±60, z 545–795) sit on B-01 (ULTRA 200 laminate) up to z 745, and on the
  frame-side collar quarter B-06f above z 745. `bag_concepts.frame_collar` cuts B-06f in ULTRA 200 whenever the
  collar seam is below the ladder top, so the top rungs land on laminate.
- Hinge eyes (z 60), IM2/IM3 hooks (z 330/520), under-straps and the 30 mm head setback all stay on the frame face,
  which is CORRIE's unchanged.
- The collar ring at the seam is 1110 mm, against 1267 on CORRIE. That is shorter than the 1171.6 mm SPINE roll
  width, so the collar becomes a straight tube and the roll is 157 mm shorter. The roll width is now set by the shell,
  not by the SPINE rule (`collar_set`): this is for BL-011 to confirm against the roll clips.

## 6. Flat piece dimensions (S15, net of seam allowance)

From `shell_sweep.flat_dims("S15")`: CORRIE's loader develops the pieces on the shell; develop strain p99 ≤ 0.24 %.

| Piece | Flat size mm (in) | Edges mm | CORRIE rev B |
|---|---|---|---|
| B-01 frame-side panel (ULTRA 200) | 394 × 716 (15.5 × 28.2) | bottom 393.6, top 360.0, sides 716.9 (with the setback Z-fold) | bottom 272.4, top 393.6, sides 710 |
| B-03 side gusset ×2 (330D) | 230 × 721 (9.1 × 28.4) bbox | bottom 160, top 195, frame edge 716.9, aft edge 715.3 (kink at the shoulder crease: 205 wide there) | bottom 170, top 240, 710 |
| B-05 floor (500D) | 394 × 160 (15.5 × 6.3) | rectangle | 272 × 170 |
| B-02u U-surround (330D) | 397 × 621 bbox | bottom 393.6, outer edges 618.7, zip edge 1338.3 | bottom 272.4, outer 624.6 |
| B-02door (330D) | 304 × 543 bbox | hinge 298.1 | 304 × 546 |
| B-02h hinge band (330D) | 388 × 97 | bottom 388.1, top 360.0, sides 96.6 | 394 × 86 |
| B-06 collar | tube 1110 perimeter × 320 to the fill line | straight tube (perimeter < 1171.6) | 1267 → 1171.6 tapered |

The door outline is CORRIE's construction on the new face (door inset 45 mm, R 60). Pockets, doors and straps are
BL-011. Masses are not quoted here: BL-011 books the S15 cut areas through `huntkit/mass/ledger.py` (RULES item 5).
The base area grows (floor +27 %, B-01 bottom +121 mm), and the gussets and collar shrink.

**Feeds BL-011 (merged bag on team B's shell family, bag_comp_verdict.md).** S15 is an envelope, not a construction,
and the envelope is portable. S01 isolates FELL's own depth (165 / 232 at CORRIE's base) on CORRIE fabrics:
178.2 / 186.6 mm, short of the 176 goal. FELL's published 175.4 mm used its softer fabrics and the centre zip. S15 on
FELL's construction (centre zip, ULTRAGrid / 70D) has **not** been simulated. The softer 70D collar bulged FELL by
about +1.5 L, so expect S15 at about 87–88 L there. Re-check volume and the 15 in meat CG in BL-011, and take 3–5 mm
off d_sh if it runs over 88 L.

## 7. Renders: three load states (task 5)

Blender Cycles through `huntkit/viz3d/cycles_render.py` as it is today (BL-018 is building the better layer). The scene
is CORRIE B.2's (`huntkit/viz3d/corrie_b2.corrie_b2_pack`): frame, harness, padded belt B, display form, wings,
door, roll, pouch and B-01 fittings. It is placed on **S15's own fine drapes** (h 25 mm, 19 in torso, the render torso
of every CORRIE and competition render). huntkit is imported, not edited: `render_model` swaps `corrie.make` and
points `sim_skin` at the state's drape for the duration of the build. All three states use one camera (az -38,
el 10, a fixed FCS box), so only the bag changes.

| State | Drape (render only) | Sim | Closed volume in the drape |
|---|---|---|---|
| Day | collar rolled to 70 mm above the collar seam; 12 L contents gas + 6 kg Janssen fill; W1-W3 take-up 45 % | NOT converged (residual 43 N, max_iter) | 30.4 L |
| 6-day | collar rolled to 90 mm; 45 L + 22 kg; take-up 30 % | NOT converged (residual 123 N, max_iter) | 53.4 L |
| Full | collar at the fill line; packed 0.5 kPa | converged (0.09 N, 3 mm rounding) | 91.3 L |

How to read them:
- The two part-full drapes did not converge and their volumes overshoot the targets (30 L for "12 L", 53 L for
  "45 L"). The cinched wraps cannot draw the bag in further, because the frame face and floor stay on the frame.
  These drapes show the shape class (a part-full box drawn in at W1-W3, with soft folds), not a number. No number in
  sections 1-6 comes from them.
- Render-only liberties: the skin is Taubin-smoothed and subdivided (as for every CORRIE render), and the wings, roll,
  pouch and straps are placed geometry. In the rolled states the B-20 ladder faces above the roll centre are not drawn,
  because they roll into the collar.
- What the owner should look at: the full bag is a straight-sided slab with no shoulder mushroom. The part-full bag
  pulls in toward the frame below a short roll, instead of standing up as an empty sack.

## 8. Assumptions that govern

- **ASSUMPTION RATIO-1:** sim / rule volume, used only to pre-size z_c. Settled: each row reports its simulated
  volume.
- **ASSUMPTION TAB-1:** ≥ 10 mm from a B-22 tab edge to any seam line. Settled by the B-22 pull test PT-4/PT-5 sewn on
  an S15 hinge-band swatch.
- **Rounding bias +4 mm** (corrie_body.md §11.4) and **re-run scatter ±2 mm** (S00 vs corrie_PR15c). Settled by the
  15 in plumb-line CG test with 30 kg on IM1–IM3 (verdict §7).
- **R-28 method:** shell drafted face minus loaded face plus 3 mm (attach_system R28_ALLOW). Settled by the 23 in
  investigation (Found, not fixed) and a head-clearance fit check on a 23 in tester.
- **ASSUMPTION RS-1** (renders only): day ≈ 12 L / 6 kg and 6-day ≈ 45 L / 22 kg, wraps taken up 45 % / 30 %, collar
  rolled to 70 / 90 mm above the collar seam. Settled by photographing the prototype at the three loadouts.

## 9. Owner decisions needed

1. **Width low on the bag.** S15 is the full 15.5 in from floor to shoulder. Loaded, it is about 16.3–17.1 in wide at
   hip / elbow height, against 13.1–14.4 in for CORRIE. Is that acceptable for arm swing and rifle sling clearance?
   The alternative is S16, with a 13.8 in base and loaded about 14.9–16.0 in at the same heights. It has an even better meat CG (169.6)
   but fails head clearance with meat at 15 and 19 in and flares at the top. Recommendation: S15, with an elbow /
   sling check on the first prototype (the same gate as the verdict's EV-1).
2. **Roll width.** The collar roll is about 1110 mm long, against 1172 mm for the SPINE roll rule, because the top is
   narrower. Accept the shorter roll (cleaner top, as asked) or keep the SPINE roll width with a flared collar.

## Screenshots

- `outputs/screens/20261111_BL009_1.png`: CG vs depth, 15 in, every sweep row.
- `outputs/screens/20261111_BL009_2.png`: S15, day load (rolled, cinched).
- `outputs/screens/20261111_BL009_3.png`: S15, 6-day load.
- `outputs/screens/20261111_BL009_4.png`: S15, full (85 L class).
