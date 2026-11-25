# BL-066 CF-LITE rework on a buildable model (review 7 B1, B2, M1-M4, m3, m4, m5, m8, m10)

Data: `bl066_cflite.json` (written by `python -m huntkit.gendesign.bl066_report`). Code: `huntkit/gendesign/bl066_cflite.py`,
`bl066_report.py`. Tests: `tests/test_bl066_cflite.py`. Parts: `print_cflite/cflite_p/cflite_P{1,2,3}.stl`. Date 2026-11-24.
Units N, mm, MPa, g (imperial in brackets).

## Verdict

**CF-LITE fails the Strong gate on the buildable model. Recommendation: stay on H1.**

- As drawn: frame line **1363.7 g (3.01 lb)**, -23.4 g (-0.8 oz) vs H1's 1387.1 g (3.06 lb), but three HA-LS-1 rows are below 1.0:
  bond Volkersen peak **0.41** (P3 top node, C8 hipbelt-off torque), fail-safe printed-sleeve bearing **0.68**, and
  eigen buckling **0.41-0.46** on the exported STLs (lower branch L root at the P1|P2 cut, an export loss: 1.52 on the
  pre-export geometry, see 4).
- Smallest fix, bonded: **not feasible**. P3 reaches only 0.72 at the search limits (10 mm sleeve wall, 1.5 mm bondline,
  3 x D6 fail-safe); it would need 5.15 MPa dry bond against the cited 3.7. P1 alone costs +91.0 g.
- Smallest fix, re-jointed: P1 and P3 unbonded and pinned (2 x D5 steel pins a side, 8 mm printed bosses) +38.7 g, plus
  the lower-branch root about +4.6 g (ASSUMPTION LB-FIX), gives **1407.0 g (3.10 lb), 19.9 g (0.7 oz) heavier than H1**.
  It is a first-order screen only (no contact FE, backlash or PA creep under the pins).
- Neither fix is lighter than 1387.1 g, so per the ticket: **not lighter, stay on H1** (H1 + BL-065: buckling 1.34, no fix).
- Even passing every row, CF-LITE's strength score would be set by the tube beam row 1.18 (z 192 cut, side-hill), below
  H1's 1.63.

## 1. Parts (B1)

- Part boundary planes z 193 (P1|P2) and z 469 (P2|P3) cut every printed voxel (176 voxels, 1.5 g, removed). P1 is one
  closed sleeve z 30-190. Orphans deleted (8 crumbs at the z 420 pads, 0.25 g each).
- Each part exported as a watertight STL: P1 318.6 g, P2 231.4 g, P3 199.5 g (exact volumes x 1.06 g/cm3). The check
  runs on the STLs re-read from disk and re-rastered on the H1 2 mm grid.
- Re-rastered: **3 separate 26-connected printed bodies** (P1 39 061, P2 28 823, P3 24 400 voxels), no voxel in a gap
  layer, no raster clash. Tested: `test_printed_parts_are_separate_components`, `test_exported_stls_rerastered_are_separate`.
- **Fixed in this pass (v3):** the previous export (v2) cut the tube-OD bore from z -100 to 700, drilling it through the
  solid stay foot below the tube seat (z 0-30: 2-10 voxels a layer left of 26-92). That made the v2 set-down eigen
  0.12 and the side-hill 0.42 (stay foot modes). The bore now runs over the tube length only (`BORE_TOP`, tube z0 up);
  test `test_exported_stls_keep_the_stay_foot`. v2 results are kept in `outputs/iter1_frame/bl066/v2_boredfoot/`.
- The z 420 lash collar is a C (62.5 % of the circumference): a keep-out lane runs behind the tube. Every other bonded
  band is a closed ring (`bond_coverage`, tested). The bond shears of the collar are divided by 0.625.

## 2. Whole-body check on the exported parts (frame_iter1.check, tube resultants at the ring's own stiffness)

| basis | printed strength | fatigue | creep | tube p99 strength | tube fatigue |
|---|---:|---:|---:|---:|---:|
| fine_sm8 | 1.78 | 2.01 | 4.30 | 1.57 | 1.68 |
| fine | 1.78 | 2.01 | 4.30 | 1.58 | 1.68 |
| beam | 1.74 | 2.62 | 5.58 | 2.11 | 2.03 |
| fine_sm8.cyc (R1) | 1.78 | **1.15** | 2.46 | 1.57 | 1.34 |

- Tube on resultants (beam theory, real 22 x 18 section, knock-downs kept): **1.18** at the z 192 cut (P1|P2 gap),
  `S_meat@a_S_fine_sm8_15:side_hill_torsion|15`. The single-voxel tube max reads 0.26 in set-down (a 2 mm-ring
  hot spot, not located; the p99 rule of record reads 1.57). m8 (Tsai-Wu on the layup) is not done; max-stress stays.
- Tube open hole (M2, OHT knock-down 0.55, 2 holes): P1 bolt z 60 **3.69**, P3 pins **1.89**.

## 3. Bonds (B2, M1, M2)

Allowable 3.7 x 0.8 = **2.96 MPa** (ASSUMPTION BOND-PA-3.7) until T6p-T reads. Axial shear with E t adherends, torque
shear with G t (G_PAHT 1430 MPa), combined as a vector at the peak. Transfers from the tube resultants at the ring's own
stiffness (B2 b). Torque: the lower of the main run and the GJ-matched run (`check_gj`); here the main run is lower on
every sleeve. Peak judged at limit; C7 / C8 at the factored load (= limit, M1). Adherend = max(design wall, measured mean).

| sleeve | L mm | line mm | wall mm | k ax / k T | avg | **peak** | C8 peak | fatigue | fail-safe print bearing | fail-safe tube bearing |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| P1 lower node | 40 | 0.8 | 4.6 | 5.5 / 8.5 | 4.02 | **0.48** | 0.48 | 2.91 | **0.69** | 1.99 |
| P2 lower-branch root | 50 | 0.5 | 3.7 | 9.9 / 15.3 | 14.1 | 1.52 | 1.52 | 6.60 | - | - |
| P2 mid-bar knuckle | 36 | 0.5 | 4.6 | 6.3 / 9.6 | 10.2 | 1.25 | 1.25 | 16.2 | - | - |
| P2 z 420 collar (C, 0.625) | 18 | 0.5 | 4.0 | 3.4 / 5.2 | 7.93 | 3.44 | 5.77 | 11.6 | - | - |
| P2 upper-branch root | 26 | 0.5 | 4.4 | 4.6 / 7.2 | 6.91 | 1.53 | 1.53 | 6.60 | - | - |
| P3 top node | 71.5 | 0.8 | 6.9 | 7.8 / 11.7 | 4.80 | **0.41** | 0.41 | 3.90 | **0.68** | 1.31 |

P1 and P3 are governed by the C8 hipbelt-off torque (limit 21.9 and 33.4 N m). For a long lap the Volkersen peak tends to
T omega / (2 pi r^2), independent of length, so a longer bond does not help; only a softer line or stiffer adherends
lower omega, and they run out (P3 0.72 at the limits).

## 4. Buckling (M4: voxel_buckling eigen, BL-065 supports and assumptions)

Carbon ring at its own EI-matched weight / (0.6 x 0.7) (the PAHT knock-down not applied to CFRP).

| basis | members, stay tops free (min) | frame, crown held | set-down, foot + crown held | **of record** |
|---|---|---|---:|---:|
| fine_sm8 | 0.464 lower branch L (K 1.82) | 0.468 lower branch L, drop | 2.75 | **0.46** |
| fine_sm8.cyc | 0.464 | 0.415 lower branch L, static carry | not run | **0.41** |

- Upper branch R 1.72, upper branch L 2.78, lower branch R 1.29, mid bar 4.44 (fine_sm8).
- **The lower branch L reading is an export loss, not the design:** the same member eigen on the pre-export voxel split
  of the same parts reads **1.52** (K 1.08); R 1.29. The STL smoothing (Gaussian 0.7 + Taubin) erodes the thin root
  next to the cut face (z 195: 13 -> 9 voxels, z 205: 41 -> 33, neck z 209: 25 -> 14). As exported the part buckles;
  an export that keeps the root (0 g class, or the LB-FIX gusset) would read about 1.29 (lower branch R). Not re-run.
- The v2 stay-foot modes (0.12 set-down) are gone with the foot restored.

## 5. Lash loads (BL-068, after = W1 z 250, W2 z 420 levelled; before = helix)

| | after p99 / max voxel | before p99 / max voxel |
|---|---|---|
| H1 (`lash_h1.json`) | 4.18 / 1.38 | 2.08 / 0.64 |
| CF-LITE (`lash_cflite.json`) | 4.15 / 1.41 | 1.99 / 0.70 |

Factor 2.0 (ASSUMPTION W-FACTOR). The max voxel sits at the lumbar root by the hip boss (x +-39, z 101-111) in both
frames. The levelled W1 / W2 (after) roughly halve the load there: the max-voxel margin is 1.38 / 1.41 after and
0.64 / 0.70 before, so the levelled layout passes on both frames and the old helix would not.
On CF-LITE the off-axis pulls also twist the sleeves about the tube (225 N x 14.3 mm): bond peak at limit 1.63 (z 420
C-collar), 2.05 (z 250 root); average at 2.0 x design 3.6 / 13.9. Pass.

## 6. T6p-T pass lines (M3, register-ready spec; not entered in the register: CF-LITE is not adopted)

T6 rule (load_standard.md): coupon mean failure >= 1.5 x the largest FE limit transfer, lowest >= 1.25 x; fatigue 1e5
cycles 0 -> the 1.6 g transfer, no debond, stiffness change <= 10 %. 3 pull + 3 torsion + 1 fatigue per coupon type.

| coupon | pull mean / lowest N (lbf) | torque mean / lowest N m (lbf in) | fatigue 1e5: pull N / torque N m | dry bond it must show |
|---|---|---|---|---:|
| T6p-T1 P1 band, 40 mm, 0.8 line | 1548 / 1290 (348 / 290) | 32.8 / 27.4 (290 / 243) | 826 / 8.8 | 7.6 MPa |
| T6p-T2a P2 root, 50 mm, 0.5 | 988 / 823 (222 / 185) | 6.9 / 5.8 (61 / 51) | 325 / 5.4 | 3.7 |
| T6p-T2b P2 knuckle, 36 mm, 0.5 | 702 / 585 (158 / 132) | 10.1 / 8.4 (89 / 74) | 98 / 1.7 | 3.7 |
| T6p-T2c P2 C-collar, 18 mm, 62 % arc | 286 / 238 (64 / 54) | 0.6 / 0.5 (5 / 4) | 75 / 0.2 | 3.7 |
| T6p-T2d P2 upper root, 26 mm, 0.5 | 997 / 831 (224 / 187) | 4.5 / 3.7 (40 / 33) | 302 / 0.9 | 3.7 |
| T6p-T3 P3 node, 71.5 mm, 0.8 | 1498 / 1249 (337 / 281) | 50.2 / 41.8 (444 / 370) | 800 / 13.2 | 9.0 MPa |

Governing sets per row are in the json (`t6p_t_spec`). "Dry bond it must show" = 3.7 / peak margin: what the bond on PAHT-CF
would have to be for the as-drawn sleeve to pass. No cited epoxy or MMA on PA reaches 7.6-9.0 MPa.

## 7. Mass (exported parts)

| row | g |
|---|---:|
| released H1 print (bl058.json) | 1069.3 |
| P1 + P2 + P3 STLs - H1 STL inside the FE box (exact volumes) | -227.9 |
| 2 carbon tubes 22 x 18 x 514 | 200.0 |
| MMA, every band both sides | 25.2 |
| P1 Ti M4 cross bolts + nuts / P3 D4 pins | 4.9 / 2.4 |
| z 234 joint hardware deleted | -28.0 |
| **frame line** | **1363.7 (3.01 lb)** vs H1 1387.1 (3.06 lb) |

Fixes: bonded sizing +184.9 g (P3 still fails) -> 1553.2 g; pinned P1 + P3 + LB-FIX +43.3 g -> **1407.0 g**.

## 8. Review-7 minors

- **m3:** the "+55 g H1 box members" (DECISIONS 2026-11-24) had no source. Recomputed: `frame_iter1.grow_members` on the
  released print = **+57.5 g** (2 mm raster x 1.06 g/cm3), as BL-065 quotes. The DECISIONS row is the orchestrator's to amend.
- **m4:** non-print share of H1's frame line from `iter1_weight.py rows('A')`: 1387.1 - 1058.7 print rows = **328.4 g**
  (frame_iter1.md carries 328). The reviewer's ~336 g is 328.4 + 8.0: it counts the "-8.0 g POM pawl housing double-booked"
  row as print, but that row removes non-print hardware from the crown / rack / pawl lump, so 328.4 g stands.
- **m10:** frame_iter1.md states CF-LITE's cinch-cycled 1.14 is its own reading and H1's R1 hold stays on H1 (applied).
  Here CF-LITE's R1 reads 1.15; moot while CF-LITE fails.
- **1453 g** (docs/research/frame_iter1.md) is replaced by the BL-062 totals (applied before this pass).
- m5: tests for tube mass, torque path, part separation, foot, coverage, lash arm, pinned bearing in `tests/test_bl066_cflite.py`.

## Assumptions

- ASSUMPTION BOND-PA-3.7: 3.7 MPa dry x 0.8 hot / wet = 2.96 MPa on PAHT-CF. Settled by: T6p-T.
- ASSUMPTION MMA-G: MMA shear modulus 300 MPa in Volkersen. Settled by: T6p-T stiffness.
- ASSUMPTION BONDLINE-VOXEL: the 0.5 / 0.8 mm line is carried in the first 2 mm voxel layer as print. Settled by: n/a (sub-grid).
- ASSUMPTION P1-BANDS: one P1 band may take all the transfer. Settled by: T6p-T1.
- ASSUMPTION OHT: open-hole strength 0.55 x unnotched. Settled by: T6b.
- ASSUMPTION SHEAR-LAG: printed wall beyond 10 mm off the bore is not adherend. Settled by: sleeve submodel.
- ASSUMPTION GAP-FILL: bondline up to 1.5 mm in the sizing search. Settled by: T6p-T at that line.
- ASSUMPTION W-FACTOR: lash pulls x 2.0 (C1 static factor). Settled by: W-PULL / RT-PULL.
- ASSUMPTION LB-FIX: lower branch L root +30 % depth (+2.3 g a side) lifts 0.46 to >= 1.0. Not run.
- ASSUMPTION PIN-FAT / BOSS: pin fatigue bearing <= 0.3 x 37.6 MPa; boss 3d x 3d x 8 mm per pin. Settled by: a pinned T6b coupon.
- BL-065's DEAD-LOAD, BRACE-TOP, H8-STIFF, FOOT-GROUND, SCREEN carry over unchanged.

## Screenshots

- `outputs/screens/20261124_bl066_1.png`: P1 / P2 / P3 exploded on the tubes.
- `outputs/screens/20261124_bl066_2.png`: H1 vs CF-LITE per HA-LS-1 row.
- `outputs/screens/20261124_bl066_3.png`: printed utilisation and bond peak margin per sleeve.
