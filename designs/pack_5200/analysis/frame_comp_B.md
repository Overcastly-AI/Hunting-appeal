# Frame competition, Team B: SEG (segmented, bolted printed joints)

Owner: structural-fea-engineer (Team B), 2026-11-10. Rules: `designs/pack_5200/frame_comp/RULES.md`.
Code: `huntkit/gendesign/frame_comp_B.py` (`python -m huntkit.gendesign.frame_comp_B`, about 2 min).
Tests: `tests/test_frame_comp_B.py`. Results: `designs/pack_5200/frame_comp/B/result.json`, full record
`designs/pack_5200/frame_comp/B/analysis_results.json`. Research: `docs/research/frame_comp_B.md`.
Units mm, N, MPa, g (imperial in brackets where it helps).

## 0. Verdict (honesty rule)

**SEG cannot beat the baseline.** The best SEG entry, SEG-2T, passes HA-LS-1 rev C but weighs **1136 g frame /
1299 g with the spreader (2.86 lb)**, **+74 g (+2.6 oz)** over today's 1063 g. Against today's frame with its 8
carbon dowels booked (17 g, missing from today's mass record, see §4) the penalty is still **+57 g**.

Why, in one line: today's body is **already printed flat with the stays in the print plane**, so the interlayer
(Z) weakness the SEG idea set out to avoid is not what governs; even an impossible print with every 2 mm voxel at its
own best layer orientation gains only +2 % strength and +4 % fatigue, while every segment boundary costs a bolted
joint of about 37 g per stay.

## 1. Method

- Body: the released socket-free PAHT-CF branch body (`spreader_layout.raster(None, 2.0)`, 823.2 g, 97 080 voxels).
- Loads: HA-LS-1 rev C, every case at torso 15 / 19 / 23 in, bag couple on the crown bar (tag C, 27 sets) and on
  the IM3 hooks (tag C_im3, 15 sets), from the v2 beam model (`rev_c_verification.beam_runs`). One PARDISO solve,
  the same exclusion of clamp and load-patch voxels as `frame_cg_recheck.verify_sets`.
- Failure rule: the repo's layered FI (`frame_topopt.layer_failure_index`): in-plane VM / (0.8 × 88),
  layer-normal / (0.8 × 47), interlayer shear / (0.8 × 0.6 × 47); margin = 1 / FI99. Fatigue: C1 at 1.6 g with
  FI ≤ 0.3; creep-rupture: C1 at 1 g with FI ≤ 0.4. `layer_terms` is tested equal to the shared rule.
- **Check against the record:** with the layer normal along y the module reproduces `rev_c_verification` exactly:
  min SF 1.51 (hipbelt_off_abuse|15), fatigue 1.044 (C_im3:static_carry|15), creep 2.23. The voxel solver itself
  is the shared one, verified against closed forms in the existing suite; it was not modified.

## 2. How much does printing along the load path buy? (cited XY vs Z, then the FE)

Published data (research §1–2): PAHT-CF Z/XY = 0.51 (47/92 MPa) or 0.73 (64/88), modulus 0.56; PA6-CF 0.64 dry,
0.79 conditioned; a PA12-CF vendor sheet ≈ 0.3. In-plane raster alignment adds about +25 % for PA6-CF (90° → 0°).
Fatigue of printed short-fibre PA is matrix-dominated (Panerai 2023); no Z-direction fatigue data was found for any
of these materials (CT-B1).

Re-run of the whole rev C set with each layer orientation (min margin over torsos and both couple variants):

| case (factor) | x: stay on its side | **y: flat (today)** | z: stay upright | best per voxel (upper bound) |
|---|---:|---:|---:|---:|
| C1 static_carry (2) | 2.42 | **2.78** | 1.60 | 2.90 |
| C2 drop_2p5g (1.5) | 1.61 | **1.86** | 1.07 | 1.93 |
| C3 side_hill_torsion (1.5) | 1.50 | **2.16** | 1.36 | 2.20 |
| C4 single_stay_setdown (1.5) | 2.13 | **3.37** | 2.32 | 3.42 |
| C5 meat_straps (1.5) | 1.71 | **2.39** | 1.32 | 2.42 |
| C6 tall_load (1.5) | 2.05 | **2.94** | 2.14 | 3.10 |
| C6p tall_load_posts (1.5) | 1.95 | **2.85** | 2.18 | 3.01 |
| C7 overload_haul (1) | 2.39 | **3.36** | 1.86 | 3.40 |
| C8 hipbelt_off_abuse (1) | 0.83 | **1.51** | 1.53 | 1.54 |
| fatigue (1.6 g) | 0.91 | **1.04** | 0.60 | 1.09 |
| creep-rupture | 1.94 | **2.23** | 1.28 | 2.32 |

- In the top 1 % of voxels today, 60–97 % are governed by the **in-plane** term (XY), 3–40 % by interlayer shear
  and none by layer-normal tension. The flat print is already the right orientation.
- The "best per voxel" column is not printable (it changes orientation voxel by voxel and per load case); it is the
  ceiling for any segmentation: **+2 % strength, +4 % fatigue**.
- SEG-7 (lower U, both upper sleeves printed on their side, upper bar, mid bar, two inboard branches, ten joint
  interfaces) gives **exactly today's margins** (1.51 / 1.04): the reoriented sleeves are not where FI99 sits.
  Ten joints at the SEG-2T per-stay joint mass would add **about +180 g to +370 g** (ASSUMPTION: 5–10 joints
  equivalent to one 36.8 g stay joint; the cross-bar joints were not sized because nothing they could buy back
  exceeds the +4 % ceiling).

## 3. Where the segments split, and the joint

The 540 mm body cannot print in one piece on the H2S (340 × 320 × 340 mm), so **both stays must be cut once,
between z 200 and 340**. Every other cut is optional and buys nothing (§2). The cut always passes through the
crown-leg sleeve (sleeves start at z 160; the leg-end bushing reaches z 171 at 15 in), so the bore must stay
continuous and the joint must keep its bolts out of it.

**SEG-2T joint (per stay):** a bolted butt flange at **z 220** (upper segment 324 mm + boss, fits the 340 mm bed
axis). Four Ti Gr5 **M5 × 30** socket-head bolts parallel to the stay (in the print plane), two in a fore row
6.2 mm outside the wearer face (y −24.2) and two in an aft row clamped inside the bag-side envelope (y +8.65,
envelope 14.8). Each bolt sits in a printed Ø12.3 × 12 mm boss on each segment with a small gusset, through-bolted
with a washer and an A2 nylon-insert lock nut (no insert in tension). A printed 3 × 3 mm tongue (lower) / groove
(upper) round the sleeve section takes Vx, Vy and the torque. Bolt-hole-to-bore ligament 8.1 mm (≥ 2.6).

Section loads at z 220 (worst set): Mx 66.5 N·m (49 lbf·ft) factored in C_im3:drop_2p5g|23, Vx 593 N, N −203 N;
torque up to 11 N·m in side-hill. Bolt tension by the elastic bolt group (tested against the closed form), × 1.25
prying.

| check (SEG-2T) | margin | governing set | basis |
|---|---:|---|---|
| washer bearing on boss face | 3.07 | C_im3:side_hill_torsion|23 R | XY 88 × 0.8 |
| Ti bolt tension (0.7 UTS × As) | 6.87 | C_im3:side_hill_torsion|23 R | ASTM F136 895 MPa |
| boss bending, across the layers | 1.73 | C_im3:side_hill_torsion|23 R | Z 47 × 0.8 |
| shear key bearing | 9.42 | C_im3:side_hill_torsion|15 R | XY 88 × 0.8 |
| bolt bearing if the key is lost (info) | 26.2 | | |
| **fatigue: boss bending at 1.6 g** | **1.03** | C_im3:static_carry|23 L | 0.3 × Z × 0.8 |
| fatigue: washer bearing at 1.6 g | 1.82 | C_im3:static_carry|23 L | 0.3 × XY × 0.8 |
| fatigue: shear key at 1.6 g | 5.61 | | |
| fatigue: Ti thread at 1.6 g | 4.86 | | 0.25 UTS (ASSUMPTION) |
| geometry: bore ligament / boss pitch | 3.10 / 3.08 | | ≥ 1 |

**The brief's insert version (SEG-2I) fails.** With brass M5 inserts in the upper bosses (record
`insert_heatset_brass_m5`, 1200 N ASSUMPTION × 0.8 hot/wet, fatigue 0.3 ×), two bolts per row give an insert
fatigue margin of **0.44**; three or more per row do not fit (aft bosses hit the crown-leg bore: 1.7 mm ligament,
bosses overlap). Best insert layout tried: margin 0.66 at 153 g. Inserts are fine for static pull-out (1.58)
but not for 1e5 cycles at 1.6 g. Cut-height scan (lightest passing through-bolt / best insert):

| z cut | through-bolt: bolts/row, boss, min margin, g | insert: min margin |
|---:|---|---:|
| 206 | 2, 14 mm, 1.30, 78 g | 0.71 |
| **220** | **2, 12 mm, 1.03, 74 g** | 0.66 |
| 234 (today) | 2, 14 mm, 1.26, 78 g | 0.77 |
| 250 | 2, 14 mm, 1.16, 78 g | 0.75 |

## 4. Mass of every load-path member

| member | today, g | SEG-2T, g |
|---|---:|---:|
| printed body (2 mm raster) | 823.2 | 823.2 |
| carbon crown, rack, pawl, bushings, Ti hip mount, inserts (non-body + rev C fix) | 239.4 | 239.4 |
| z 234 joint: 8 carbon dowels 5 × 70 mm + MMA | 17.0 (**not booked** in 1062.6: `frame_branch.pack_numbers` says "dowels are gone") | – |
| z 220 flange bosses + gussets (8 per stay side pair) | – | 14.6 |
| shear key | – | 1.3 |
| 8 Ti M5 × 30 | – | 13.5 |
| 8 lock nuts + washers | – | 7.4 |
| **frame** | **1062.6** (1079.6 with dowels) | **1136.2** |
| spreader, Sandwich v2 7 mm | 162.3 | 162.3 |
| **frame + spreader** | **1225** | **1298.5** |
| CORRIE B.2 pack at belt M | 3964.5 | 4038.0 |

Mass reductions that keep the margins: none worth having. Shorter bolts (M5 × 25, −2.7 g) and a shared boss bar
per row (−3 g) are second-order; the boss-bending fatigue margin (1.03) blocks thinner bosses. The real
recommendation is in §7.

## 5. Build (beginner, simple jigs)

1. Print the two segments flat, wearer face on the plate, as today (§ PRODUCTION.md settings), split at z 220;
   bosses and the tongue/groove are printed in. Dry, anneal 90 °C 6 h with a 16 mm rod through each sleeve.
2. Jig: the flat board and the two 16 mm rods already used for annealing. Slide both segments onto the rods so the
   bores line up, engage the tongue, clamp to the board.
3. Drill the 8 bolt holes 5.3 mm through both bosses with a drill guide (printed drill bushing that clips over the
   boss pair), insert bolts, washers, nuts; torque 2.5 N·m with threadlocker (insert record guidance).
4. Ream both bores 18.0 mm through the assembled joint so the crown-leg bushing passes the joint without a step.
5. Pencil-mark across the joint before T1; pass ≤ 0.5 mm step after unload (as today). Hands-on ≈ 5 h total
   (ASSUMPTION), no adhesive, no cure time, field-repairable (a broken segment is reprinted and bolted on).

## 6. Coupon tests tied to the governing assumptions

| id | test | ties to |
|---|---|---|
| CT-B1 | PAHT-CF XY, Z and ±45 tension-tension fatigue, R 0.1, 2 Hz, 23 °C/50 % RH and 40 °C wet, 5 per level, run-out 1e5 at 0.30 × UTS | fatigue ratio 0.3 (body and joint) |
| CT-B2 | interlayer shear (short-beam or V-notch), annealed PAHT-CF, 5 dry + 5 wet, pass ≥ 0.6 × 47 × 0.8 | interlayer shear 0.6 × Z |
| CT-B3 | one-boss pull-through coupon as built (boss, Ti M5, washer): 5 static, 3 at the 1.6 g bolt load for 1e5 cycles | boss bending (governs, 1.03), prying 1.25, washer bearing |
| CT-B4 | z 220 joint stub pair (250 mm each side) in 4-point bending to Mx 66.5 N·m factored, then 1e5 cycles at the 1.6 g Mx; rotation stiffness, slip ≤ 0.5 mm, preload loss | joint rigidity, torsion 0.97, Ti thread fatigue |
| CT-B5 | (insert variant only) 5 inserts in printed bosses, axis in the print plane, static ≥ 1.5 kN, 3 at 0.3 × 960 N for 1e5 | insert pull-out 1200 N, insert fatigue |

## 7. Recommendations

1. **Do not pursue SEG for mass.** The orientation ceiling (+4 % fatigue) is far below what one extra joint costs.
2. If the owner wants **no adhesive in the load path** (field repair, no MMA handling), SEG-2T is a drop-in for the
   z 234 dowel joint at **+57 g** against honestly booked dowels, with the same body, crown and interfaces.
3. Book the 17 g of z 234 dowels in today's frame mass record (`frame_mass_production.json` omits them).
4. The fatigue margin of the body (1.04) is unchanged and remains the frame's weak point; Team A/D/E-type
   material or topology changes, not segmentation, are what can move it.

## 8. Assumptions

- ASSUMPTION: the 2 mm voxel body FE (isotropic stiffness, XY modulus) gives the joint section loads; the joint is
  treated as rigid in that FE (CT-B4).
- ASSUMPTION: bolt preload is not credited (printed nylon creeps); all external tension goes to the bolts.
- ASSUMPTION: prying factor 1.25; boss as a cantilever of length 6.2 mm, section Ø12.3 × boss height.
- ASSUMPTION: gusset 300 mm³ per boss; lock nut + washer 0.92 g each; Ti bolt $1.5 each.
- ASSUMPTION: torsion stiffness 0.97 × today (joint compliance not modelled).
- ASSUMPTION: cost at 10 / 100 units −7 % / −14 % (bulk filament and hardware packs).
- ASSUMPTION: print time scales with mass (+16 g of bosses → 27.9 h).

## Screenshots

- `outputs/screens/20261110_compB_1.png`: today's body next to SEG-2T, and the joint section at z 220.
- `outputs/screens/20261110_compB_2.png`: utilization envelope, the orientation study, the joint margins.
