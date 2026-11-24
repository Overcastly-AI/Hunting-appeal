# Frame iteration 1 (BL-061): lighter and at least as strong

structural-fea-engineer, 2026-11-24. Ticket `docs/backlog/BL-061-iter1-frame.md`. Research [frame_iter1.md](../../../../docs/research/frame_iter1.md). Rubric `docs/RUBRIC.md`. Code `huntkit/gendesign/frame_iter1.py` (concepts + check), `frame_iter1_report.py` (this record, figures), `frame_iter1_text.py` (prose); tests `tests/test_frame_iter1.py`; data `frame_iter1.json`. Units mm, N, MPa, g (imperial in brackets). Released print files untouched.

## Summary

- **Recommendation: CFLITE** (CF-STAY + box members + cavities sized on CF-STAY's own utilisation). Frame line **1353 g (2.98 lb)** against H1's 1387 g: **-34 g (-1.2 oz)**. Every HA-LS-1 rev C body row is at or above H1's: strength 1.69 (H1 1.63), fatigue 1.95 (1.25), creep 4.16 (2.66), **buckling 1.31 (1.05)** on the record rule and 1.38 (0.85) on the stricter section rule, and **cinch-cycled fatigue 1.14 (0.86)**: both rubric bonuses are met (buckling >= 1.15, cinch-cycled >= 1.0, which lifts the R1 hold). Carbon tube strength / fatigue 1.64 / 1.73, tube-to-node bonds min 1.10.
- **The mass target is not met.** The ticket aimed at >= 150 g off the frame; the best concept that keeps every margin saves 34 g. Section 3 shows where the rest of the mass sits: the three printed parts still carry every bag interface (lugs, fairleads, hinge eyes, hip boss with 8 inserts, pawl housing, spine channel), and on the 2 mm voxel grid a printed wall cannot go below 4 mm.
- **A 900 g frame line (the orchestrator's bold target) cannot be reached without losing margin** while the crown, the torso adjustment and the bag interfaces stay. Section 5.2 gives the arithmetic.
- **Found on H1 (not fixed, it is released):** with each member's real section (I_min of the cut) instead of the record rule's solid-round equivalent, H1's member buckling is **0.85**, not 1.05 (upper branch R: a 16 x 12 mm flat section has 81 % of the round's I). Only the record rule's K = 1 (pinned ends; the fused ends are stiffer) covers it. The printed-frame side-squeeze test in h1_buckling's EULER_RULE assumption, or a linear eigenvalue run, settles it. It is one more reason to adopt box members whatever concept is chosen.
- Side task: the T1 US1 ROOT gauge is now record only, and the second US1 gauge was re-run on the current STL and md5-locked (section 7).

## 1. Concepts and results

Frame line (print + crown + rack / pawl + pins + hardware) for H1: **1387.1 g** (3.06 lb), designs/pack_5200/iter1/system/iter1_weight.json totals.frame_after_tests_g (BL-062). Each concept changes it by its mass delta (section 3).

| concept | frame line g (lb) | delta g | strength | fatigue | creep | buckling record / section | cinch-cycled fatigue / buckling | joint z 234 | tube str / fat | bonds min | R1 | as strong as H1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| **H1** H1 today (released print) | 1387.1 (3.06) | +0.0 | 1.63 | 1.25 | 2.66 | 1.05 / 0.85 | 0.86 / 1.02 | 1.98 / 1.16 | - / - | - | pass | yes |
| **GRADED** same STL, shell + 15 % gyroid core | 1336.0 (2.95) | -51.1 | 1.36 | 1.18 | 2.51 | 0.98 / 0.84 | 0.80 / 0.99 | 1.98 / 1.16 | - / - | - | FAIL | no |
| **BOX** closed-box members + ribbed cavities | 1382.4 (3.05) | -4.7 | 1.51 | 1.30 | 2.78 | 1.68 / 1.78 | 0.89 / 1.69 | 2.03 / 1.23 | - / - | - | pass | no |
| **CFSTAY** carbon-tube stays + 3 printed nodes | 1343.8 (2.96) | -43.3 | 1.62 | 1.91 | 4.07 | 0.81 / 0.73 | 1.06 / 0.85 | - / - | 1.64 / 1.77 | 1.27 | FAIL | no |
| **CFBOX** CF-STAY + box members + ribbed node cavities | 1356.6 (2.99) | -30.5 | 1.50 | 1.92 | 4.09 | 1.28 / 1.36 | 1.12 / 1.30 | - / - | 1.73 / 1.84 | 1.66 | pass | no |
| **CFLITE** CF-STAY + box members + cavities sized on CF-STAY's own utilisation | 1352.6 (2.98) | -34.5 | 1.69 | 1.95 | 4.16 | 1.31 / 1.38 | 1.14 / 1.32 | - / - | 1.64 / 1.73 | 1.10 | pass | yes |

Margins are SF / requirement (R1: >= 1). Static-cinch = minimum over fine_sm8, fine and beam; cinch-cycled = fine_sm8.cyc. All with the stays' sanding factor 1.0416 on printed stay voxels (BL-055). 'Section' buckling uses each cut's real weighted I_min (section 2.1).

- **GRADED**: static buckling_record 0.978; static strength 1.359 < H1 1.63; static fatigue 1.175 < H1 1.249; static creep 2.507 < H1 2.664; static buckling_record 0.978 < H1 1.053; static buckling_section 0.836 < H1 0.855; cinch-cycled fatigue 0.799 < H1 0.856; cinch-cycled buckling_record 0.99 < H1 1.022; cinch-cycled buckling_section 0.847 < H1 0.865
- **BOX**: static strength 1.514 < H1 1.63
- **CFSTAY**: static buckling_record 0.808; static buckling_record 0.808 < H1 1.053; static buckling_section 0.727 < H1 0.855; cinch-cycled buckling_record 0.85 < H1 1.022; cinch-cycled buckling_section 0.734 < H1 0.865
- **CFBOX**: static strength 1.501 < H1 1.63

### What each concept is, and what it showed

- **C GRADED** (slicer only: released STL, 4 mm wall shell, 15 % gyroid core where H1's utilisation is below 0.55, 100 % at every hard point): -51 g, and weaker everywhere: strength 1.36, buckling 0.98 (below R1), cinch-cycled 0.80. The core carries part of the bending in the upper bar and the members; taking it out costs more margin than mass. Rejected.
- **A BOX** (branches and mid bar grown 2 mm and made closed boxes; low-utilisation thick zones hollowed into ribbed cavities with a 2 mm diaphragm every 40 mm; the cinch-cycled hot spot grown 2 mm): -5 g. Buckling 1.68 and cinch-cycled 0.89 improve, but strength falls to 1.51 (hipbelt-off abuse, upper bar / pawl housing: a cavity there). Not lighter; the box members are the useful part.
- **B CF-STAY** (two 22 x 18 roll-wrapped carbon tubes as the stays, crown legs sliding inside as today; printed P1 lower node, P2 branch X with three sleeves, P3 top node, slid on and bonded; the z 234 bolted split deleted): -43 g. Fatigue jumps to 1.91 and cinch-cycled to 1.06 (the tubes take the stay bending off the printed roots), strength holds (1.62), but member buckling falls to 0.81: the stiffer stays push more of the side-hill racking through the branches. Fails R1 as is.
- **D CF-BOX** (CF-STAY + A's box members, hot-spot growth and cavities sized on H1's utilisation): -30 g, buckling 1.28, but strength 1.50 (the same upper-bar cavity as BOX).
- CF-STAY and CF-BOX were solved before the full bond sleeve was added (their FE has a few windows in the printed sleeve, slightly conservative); their masses are booked with it.
- **E CF-LITE** (CF-STAY + box members + every printed stay voxel outside the 14 mm sleeve removed in P1 and P2 where CF-STAY used it below 0.4, + cavities where CF-STAY's own utilisation is below 0.6, none in the top node): the concept that keeps every margin. Its first version (also trimming P3 and deepening the members in y only) failed: strength 1.50 at the top bushing and upper branch R buckling 0.91 (record `outputs/iter1_frame/check_cflite_v1.json`); both were reverted. Its second version left windows in the printed sleeve where H1's lower legs were narrower than 28 mm; the full 3 mm sleeve over every bonded length is in the version reported here (+25 g).

## 2. Method

- **Geometry.** Every concept starts from the released print `print/frame_h1/h1_assembled.stl` (md5 7bd47cbdcc3b42c0f93d57ef041efc11), re-rastered on the H1 2 mm grid (`bl058_frame.body_stl`). Interfaces are not moved: hinge eyes, US1 / US2 lanes and clevises, the 12 fairleads, the crown bores (18 mm), the hip boss and its 8 insert pilots, the pawl housing and the spine channel are protected voxels in every concept (`frame_iter1.protected`, `hard_points`). The voxel envelope stops at y 16 and |x| 152; outside it (fairlead tops, US2 clevises) nothing changes.
- **Check.** The BL-055 / BL-058 whole-body check, unchanged: 42 rev C sets x 3 crown kits on the fine_sm8, fine and beam bases plus the cinch-cycled fine_sm8.cyc basis, lane kit sets, real crown models, H1's FI99 layer rule (PAHT-CF 88 / 47 MPa x 0.8), fatigue 0.30 x at 1e5 x 1.6 g, creep 0.40, stays sanded (k 1.0416). **The H1 run reproduces bl058.json exactly** (strength 1.630, fatigue 1.249, creep 2.664, buckling 1.053, cinch-cycled 0.856), so the concept numbers are on the record's basis.
- **Extensions** (`frame_iter1.check`): per-voxel stiffness weights (`h1_sleeve.solve_fields_w`); gyroid core E x 0.0225, its FI against the gyroid strength x 0.0174 (ASSUMPTION GYROID); carbon tube voxels: a 1-voxel ring r 9-11 mm with weight 20.7 that matches the tube's EI (EA 0.95 x, GJ 2.3 x the real tube: torsion is over-attracted, conservative for the tube and its bonds); tube stress = the voxel strain x 75 GPa; tube FI = max-stress with the knock-downs kept (Xt 650 x 0.8, Xc 450 x 0.8 x 0.65, S 90 x 0.8; p99 over the tube voxels outside the load patches; fatigue FI at 1.6 g <= 0.5); tube resultants (N, M, T) at bare cuts between the sleeves give each sleeve's transfer for the bond check (section 4). The z 234 joint check runs only where the split exists.
- **Solver verification.** The FE path is the record's (tests in `tests/test_h1_*`, `test_frame_h1.py`). New closed-form tests (`tests/test_frame_iter1.py`): voxel section I of a rectangle and a box against b d^3 / 12, Euler P_cr, Volkersen limits, the bond and pin margins on a synthetic resultant record.

### 2.1 Member buckling per member (fine_sm8 basis)

| concept | member | A_eff mm2 | I_min mm4 | P factored N | margin record | margin section |
|---|---|---:|---:|---:|---:|---:|
| H1 | branch lower (z 165-330) L | 108 | 907 | 235 | 1.30 | 1.27 |
| H1 | branch lower (z 165-330) R | 112 | 1017 | 288 | 1.14 | 1.16 |
| H1 | branch upper (z 330-495) L | 140 | 1403 | 113 | 4.55 | 4.09 |
| H1 | branch upper (z 330-495) R | 148 | 1415 | 538 | 1.07 | 0.86 |
| H1 | mid bar (x -115..115) all | 124 | 1109 | 223 | 1.11 | 1.00 |
| GRADED | branch lower (z 165-330) L | 108 | 907 | 239 | 1.28 | 1.25 |
| GRADED | branch lower (z 165-330) R | 112 | 1017 | 285 | 1.15 | 1.17 |
| GRADED | branch upper (z 330-495) L | 136 | 1400 | 116 | 4.19 | 3.98 |
| GRADED | branch upper (z 330-495) R | 144 | 1412 | 549 | 0.99 | 0.85 |
| GRADED | mid bar (x -115..115) all | 124 | 1109 | 220 | 1.12 | 1.01 |
| BOX | branch lower (z 165-330) L | 180 | 2570 | 372 | 2.28 | 2.27 |
| BOX | branch lower (z 165-330) R | 188 | 2745 | 276 | 3.36 | 3.28 |
| BOX | branch upper (z 330-495) L | 200 | 3631 | 117 | 8.98 | 10.24 |
| BOX | branch upper (z 330-495) R | 208 | 3641 | 670 | 1.69 | 1.79 |
| BOX | mid bar (x -115..115) all | 204 | 3069 | 237 | 2.81 | 2.61 |
| CFSTAY | branch lower (z 165-330) L | 108 | 907 | 321 | 0.95 | 0.93 |
| CFSTAY | branch lower (z 165-330) R | 112 | 1017 | 387 | 0.85 | 0.87 |
| CFSTAY | branch upper (z 330-495) L | 140 | 1403 | 306 | 1.68 | 1.51 |
| CFSTAY | branch upper (z 330-495) R | 148 | 1415 | 634 | 0.91 | 0.73 |
| CFSTAY | mid bar (x -115..115) all | 124 | 1109 | 253 | 0.97 | 0.88 |
| CFBOX | branch lower (z 165-330) L | 180 | 2570 | 471 | 1.80 | 1.80 |
| CFBOX | branch lower (z 165-330) R | 188 | 2745 | 470 | 1.97 | 1.92 |
| CFBOX | branch upper (z 330-495) L | 200 | 3631 | 428 | 2.45 | 2.79 |
| CFBOX | branch upper (z 330-495) R | 208 | 3641 | 874 | 1.30 | 1.37 |
| CFBOX | mid bar (x -115..115) all | 204 | 3069 | 278 | 2.40 | 2.23 |
| CFLITE | branch lower (z 165-330) L | 180 | 2570 | 469 | 1.81 | 1.80 |
| CFLITE | branch lower (z 165-330) R | 188 | 2745 | 464 | 2.00 | 1.95 |
| CFLITE | branch upper (z 330-495) L | 200 | 3631 | 424 | 2.47 | 2.82 |
| CFLITE | branch upper (z 330-495) R | 208 | 3641 | 858 | 1.32 | 1.40 |
| CFLITE | mid bar (x -115..115) all | 204 | 3069 | 277 | 2.42 | 2.24 |

Record rule (team A, used for every H1 record): member voxel area at the cut as a solid round, pinned-pinned K 1, E 3860 x 0.6 hot x 0.7 creep, margin = P_cr / (1.5 x factored compression). Section rule: the same but with the cut's real weighted I_min. On H1 the section rule is stricter (flat 16 x 12 and 14 x 12 mm members); on box members it credits the hollow section. The recommended concept passes both.

## 3. Mass (ledger style)

**H1**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) +0.0 = **1069.3 g** (-0.0 g; frame line 1387.1 g). Print about 38 h.

**GRADED**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) -51.1 = **1018.2 g** (-51.1 g; frame line 1336.0 g). Print about 36 h.

**BOX**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) -4.7 = **1064.6 g** (-4.7 g; frame line 1382.4 g). Print about 38 h.

**CFSTAY**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) -249.3; 2 carbon tubes 22 x 18 x 514 mm (record density) +200.0; MMA bond, 0.8 mm in P1 (2 x 40 mm bands) / P3, 0.5 mm in P2 (record density 0.98) +24.1; 4 fail-safe Ti M4 x 30 cross bolts (P1, P3) +9.9; z 234 joint hardware deleted (frame_mass_h1.json) -28.0 = **1026.0 g** (-43.3 g; frame line 1343.8 g). Print about 28 h.

**CFBOX**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) -236.5; 2 carbon tubes 22 x 18 x 514 mm (record density) +200.0; MMA bond, 0.8 mm in P1 (2 x 40 mm bands) / P3, 0.5 mm in P2 (record density 0.98) +24.1; 4 fail-safe Ti M4 x 30 cross bolts (P1, P3) +9.9; z 234 joint hardware deleted (frame_mass_h1.json) -28.0 = **1038.8 g** (-30.5 g; frame line 1356.6 g). Print about 29 h.

**CFLITE**: print (released STL, bl058.json stl) 1069.3; printed voxel delta (2 mm raster) -240.5; 2 carbon tubes 22 x 18 x 514 mm (record density) +200.0; MMA bond, 0.8 mm in P1 (2 x 40 mm bands) / P3, 0.5 mm in P2 (record density 0.98) +24.1; 4 fail-safe Ti M4 x 30 cross bolts (P1, P3) +9.9; z 234 joint hardware deleted (frame_mass_h1.json) -28.0 = **1034.8 g** (-34.5 g; frame line 1352.6 g). Print about 29 h.

Masses: printed parts from the 2 mm raster at 1.06 g/cm3 (deltas against H1's raster applied to the 1069.32 g released STL, so the raster-to-STL difference cancels); tubes 22 x 18 at the record's 1550 kg/m3 (0.195 g/mm; a 22 x 19 listing implies 1.45 g/cm3, research section 3); MMA 0.98 g/cm3 at its bondline; Ti M4 x 30 bolts (ASSUMPTION BOLT-G 0.8 g head and nut); the z 234 joint hardware from frame_mass_h1.json. Everything else in the frame line (crown legs, top bar, spine tube, corner wraps, rack, pawl, guides, bushings, Ti hip mount, inserts, pins, US2 clevis hardware, torso-adjust webbing) is unchanged in every concept.

**What besides the print each concept removes:** CF-STAY / CF-BOX / CF-LITE delete the z 234 split's 4 Ti M5 x 45, 4 nuts and 8 washers (28.0 g) and its two printed bolt bosses, and add 2 tubes, the bond and 4 Ti M4 fail-safe bolts. BOX and GRADED change the print only. No concept touches the crown, the rack / pawl or the pins (owner-frozen interfaces and lifters on the crown top bar).

Where CFLITE's printed mass is (raster): P1 lower node (z < 193) 293 g; P2 branch X (z 193-469) 234 g; P3 top node (z > 469) 208 g. P1 holds the lumbar X struts, the hip boss with 8 inserts, the US1 / US2 lug arms and clevis blocks, the hinge eyes, IM1 and the feet; P3 the upper bar, pawl housing, spine channel, crown bushing seats and IM3. Most thick zones are now 4 mm shells with ribs; the next grams need walls under 4 mm, which the 2 mm grid cannot represent (iteration 2: a 1 mm submodel of P1 and P3), or fewer printed features.

## 4. Tube-to-node joints (carbon-stay concepts)

| concept | sleeve | bonded L mm | Volkersen k | avg | peak (limit) | fatigue | bearing | fail-safe pin |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CFSTAY | P1 lower node | 40 | 6.9 | 5.87 | 1.27 | 3.66 | 2.38 | 3.19 |
| CFSTAY | P2 lower-branch root | 50 | 11.0 | 21.80 | 3.17 | 10.22 | 14.20 | - |
| CFSTAY | P2 mid-bar knuckle | 36 | 7.9 | 16.88 | 3.21 | 33.10 | 8.61 | - |
| CFSTAY | P2 upper-branch root | 26 | 5.7 | 11.20 | 2.94 | 11.27 | 6.81 | - |
| CFSTAY | P3 top node | 72 | 12.5 | 14.17 | 1.70 | 9.95 | 24.91 | 4.27 |
| CFBOX | P1 lower node | 40 | 6.9 | 7.69 | 1.66 | 4.82 | 2.71 | 4.17 |
| CFBOX | P2 lower-branch root | 50 | 11.0 | 31.49 | 4.76 | 14.76 | 16.06 | - |
| CFBOX | P2 mid-bar knuckle | 36 | 7.9 | 14.70 | 2.79 | 34.87 | 10.24 | - |
| CFBOX | P2 upper-branch root | 26 | 5.7 | 7.81 | 2.05 | 7.86 | 6.80 | - |
| CFBOX | P3 top node | 72 | 12.5 | 14.14 | 1.70 | 9.94 | 24.42 | 4.26 |
| CFLITE | P1 lower node | 40 | 6.9 | 6.16 | 1.33 | 4.63 | 2.49 | 2.29 |
| CFLITE | P2 lower-branch root | 50 | 11.0 | 24.41 | 3.82 | 11.44 | 12.74 | - |
| CFLITE | P2 mid-bar knuckle | 36 | 7.9 | 14.58 | 2.77 | 22.34 | 10.10 | - |
| CFLITE | P2 upper-branch root | 26 | 5.7 | 7.96 | 2.09 | 7.93 | 6.81 | - |
| CFLITE | P3 top node | 72 | 12.5 | 7.06 | 1.10 | 5.90 | 24.54 | 1.42 |

Rules (HA-LS-1 4): average shear >= 1 at the factored load; Volkersen elastic peak >= 1 at LIMIT load (limit cases; the ultimate cases C7 / C8 are judged on the average, the toughened MMA yields at the peak and redistributes); fatigue: 1.6 g static-carry average <= 0.3 x the dry allowable. Allowable 5.0 x 0.8 = 4.0 MPa (ASSUMPTION BOND-PA: the printed polyamide side governs, published 3.7-5.0 MPa with interface failure). Shear modulus 300 MPa (ASSUMPTION MMA-G). P1 and P3 at a 0.8 mm bondline (glass beads, as the rev C crown corners); P1 bonded in two 40 mm bands and checked as if one band took it all. Bending goes in by bearing over the sleeve (p = 6 M / (d L^2) against 47 x 0.8 MPa). Fail-safe: one Ti M4 cross bolt in P1 and in P3 carries the axial force and the torque alone at limit, bearing on the tube's two 2 mm walls at 250 MPa (ASSUMPTION TUBE-BEARING).

The tightest is the P3 Volkersen peak in side-hill torsion; in the hipbelt-off abuse case (ultimate) the P3 peak is below 1 as information (see the json `peak_ultimate_info`): that case is covered by the average and by the fail-safe bolt. The voxel tube over-attracts torsion by about 2.3 x, so all torsion-driven bond numbers are conservative. CF-STAY and CF-BOX were run before the torque column was added: their bond rows carry no torque (json `bond_torque_in_model`).

## 5. Rubric score and recommendation

| rubric axis | H1 | GRADED | BOX | CFSTAY | CFBOX | CFLITE |
|---|---|---|---|---|---|---|
| 1 Strong (gate: every row >= H1's) | baseline | FAIL | R1 only | FAIL | R1 only | pass |
| bonus: buckling >= 1.15 / cinch-cycled >= 1.0 | 1.05 / 0.86 | 0.98 / 0.80 | 1.68 / 0.89 | 0.81 / 1.06 | 1.28 / 1.12 | 1.31 / 1.14 |
| 2 Lighter (frame line) | 1387 g | 1336 g (-51) | 1382 g (-5) | 1344 g (-43) | 1357 g (-30) | 1353 g (-34) |
| 3 Looks (frame surfaces intentional) | printed branch body | same | same, ribbed inside | carbon stays + printed knuckles | same | same |
| print time (est.) | 38 h | 36 h | 38 h | 28 h | 29 h | 29 h |

### 5.1 Recommendation: CFLITE

It is the only concept that passes the strength gate against H1 on every row and is lighter (-34 g). It also takes both bonuses: buckling 1.31 (target 1.15) and cinch-cycled fatigue 1.14 (target 1.0, lifts the R1 hold for MT-1). It reads as carbon stays with printed knuckles (the look the owner asked frame_light2 for on 2026-11-09), and it removes the z 234 bolted split, the part of H1 with the most hardware and two review cycles.

**Build (beginner, home):** buy two 22 x 18 mm roll-wrapped tubes (1 m, cut to 514 mm with a fine hacksaw in a printed mitre jig, ends sealed with thin CA); print P1, P2, P3 flat on the H2S (each fits 340 x 320; no split, no joint bolts); scuff the tubes (120 grit) and the sleeve bores, flame-treat the PAHT-CF (as T6p), slide the parts on in order P1, P2, P3 in a printed alignment jig, MMA with 0.8 mm glass beads in P1 / P3, 0.5 mm in P2; drill the two fail-safe M4 holes through P1 / P3 using the printed part as the drill guide. Room-temperature cure. Printing about 29 h against H1's 38 h (estimate, same rule), plus one evening of bonding in a jig; no z 234 bolt fitting.

**Main risk:** the printed-PAHT-to-carbon bond at the P3 top node in torsion (Volkersen peak 1.10 in side-hill torsion, below 1 as information in the hipbelt-off abuse case), resting on an unpublished value (ASSUMPTION BOND-PA 4.0 MPa, published PA12 3.7-5.0 MPa).

**Test that retires it: T6p-T (new)**: 3 coupons of a 120 mm tube offcut bonded into a printed P3-style sleeve (72 mm, 0.8 mm bondline, the build's prep), pulled axially to failure and 3 twisted to failure on the pull bench (kit A). Pass: mean axial >= 1.5 x and torque >= 1.5 x the largest limit transfer (frame_iter1.json bonds), lowest >= 1.25 x, cohesive or substrate failure; plus 1e5 cycles at the 1.6 g fatigue transfer on one coupon. Then T1 / T3 on the bonded frame as HA-LS-1 5.3.

### 5.2 Why not 900 g

H1's frame line is 1387 g, of which 318 g is outside the print (crown, rack / pawl, bushings, Ti hip mount, inserts, pins, clevis hardware, torso-adjust webbing). Holding that, 900 g leaves about 582 g for the print-plus-tubes; CF-LITE's print-plus-tubes is 1035 g. The only architecture in the repo that gets there is the v2 ladder (frame_light2 TENDON: printed nodes 238 g + tubes 103 g + wraps 40 g + bonds 22 g + pan 123 g, about 526 g + 318 g = about 844 g with H1's crown and hardware), but its rev C minimum was strength 1.04 / fatigue 1.07 on the beam model, against H1's 1.63 / 1.25: it loses margin, and it lacks H1's lug arms, clevises and spine channel. So **no 900 g concept is offered as passing**. Iteration 2 could FE a TENDON-class ladder with H1's interfaces, sized to H1's margins (estimate 900-1000 g).

## 6. Assumptions

- ASSUMPTION GYROID: E* = rho^2, strength 0.3 rho^1.5 for 15 % PAHT-CF gyroid (Gibson-Ashby; Bean 2022 says the power law fits poorly). Only GRADED uses it. Settled by GY-1 (shell + core beam bend and compression).
- ASSUMPTION BOX-ENVELOPE: members grown 2 mm stay inside the stays' y span (-23..9) and clear of the spreader and back rails. Settled by a fit check of the re-exported print against the spreader / rail CAD (spreader clips, CLIP_Z) before release.
- ASSUMPTION CAVITY-PRINT: closed cavities with 2 mm diaphragms every 40 mm print with bridged roofs on the H2S (cavity roofs drawn as 45 deg diamonds in the CAD). Settled by a sectioned print of one P1 strut.
- ASSUMPTION TUBE: 22 x 18 roll-wrapped tube to the record (E 75 GPa, 650 / 450 MPa, ESTIMATE); ID 18.0 +/- 0.1. Settled by a 3-point bend of one offcut per batch and a bore gauge (record note).
- ASSUMPTION TUBE-VOXEL: the isotropic voxel ring matched on EI (EA 0.95 x, GJ 2.3 x). Settled by the T1 / T3 deflection readings against the model.
- ASSUMPTION BOND-PA (4.0 MPa design), MMA-G (300 MPa), P1-BANDS (one band may take all), SLEEVE-BEARING (47 x 0.8 MPa), TUBE-BEARING (250 MPa pin bearing), BOLT-G. Settled by T6p-T (bond, torsion) and T6b (M4 pin bearing in a tube offcut).
- ASSUMPTION CLIPS: the spreader clips and the hinge-eye / fairlead geometry re-seat on the 22 mm tube or on the printed sleeves unchanged (the fairleads stay on printed parts at their current positions).
- The H1 record's own assumptions (SUB-BC, EULER_RULE, PAHT_FAT, CINCH_STATIC, MESH, SAND-K) carry over.

## 7. Side task: T1 US1 ROOT record only; second US1 gauge re-run

- `physical_test_kit.py`: `T1_RECORD_ONLY = ('US1 ROOT',)`. Its T1 line (gauge_lines_bl060.json T1|us1) sits at a near-null point of the bag-on load and inside a PAHT-CF half-bridge's zero drift (BL-060), so the register's T1 pass / fail text lists it as RECORD ONLY with its model line, and its three results rows are `record` (no band). US2 ROOT and US1 OUTER CHEEK keep their pass lines.
- `us1_outer_gauge.py` re-run on the current STL (md5 `7bd47cbdcc3b42c0f93d57ef041efc11`), locked like gauge_lines_bl060.json (`g2_locked`, `g2_src_txt`; another print falls back to ASSUMPTION GAUGE-GEOM). Lines now / before (microstrain): MT-1cr|us1_outer [1718.0, 3437.0, 5155.0, 6356.0] / [1719.0, 3439.0, 5158.0, 6359.0]; T1|us1_outer [0.0, 261.0, 521.0] / [0.0, 260.0, 520.0]; MT-1cr|us1_outer_other_axis [411.0, 822.0, 1233.0, 1521.0] / [411.0, 822.0, 1233.0, 1521.0]. The outer cheek did not change since BL-055 (< 0.2 %).
- Kit regenerated: `test_register.csv`, `outputs/release/test_kit/` (results template, guide G6, PDF).

## 8. Screenshots

- `outputs/screens/20261124_iter1_frame_1.png`
- `outputs/screens/20261124_iter1_frame_2.png`
- `outputs/screens/20261124_iter1_frame_3.png`
- `outputs/screens/20261124_iter1_frame_4.png`
