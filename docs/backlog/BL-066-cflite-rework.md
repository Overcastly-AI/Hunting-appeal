# BL-066 CF-LITE rework on a buildable model

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-061 (CF-LITE), BL-065 (eigen solver), review 7, BL-068 (lash loads) · **Date:** 2026-11-24

Ask (DECISIONS 2026-11-24): rework CF-LITE per review 7 (B1 real part cuts, B2 axial / torque bond split at real ring
stiffness and 2.96 MPa, M1 C8 peak >= 1.0, M2 printed-side bolt bearing + open hole, M3 numeric T6p-T lines, M4 eigen
buckling); if it fails, size the smallest fix and its mass, and recommend H1 if that is not lighter than 1387.1 g. Fix
m3, m4, m10 and the stale 1453 g. Check the BL-068 lash loads on H1 and on CF-LITE.

## Deliverables
- Code: `huntkit/gendesign/bl066_cflite.py` (parts, STL export, re-raster, resultants, bonds, coverage, sizing, pinned
  screen, lash checks), `huntkit/gendesign/bl066_report.py` (record, figures).
- Tests: `tests/test_bl066_cflite.py` (14).
- Record: `designs/pack_5200/iter1/frame/bl066_cflite.{md,json}`; parts `designs/pack_5200/iter1/frame/print_cflite/cflite_p/`.
- Runs: `outputs/iter1_frame/bl066/` (logs, lash, sizing, mass; v2 bored-foot runs kept in `v2_boredfoot/`), `outputs/bl065/cflite_p_*`.
- Screenshots: `outputs/screens/20261124_bl066_{1,2,3}.png`.

## Resume notes (container restart)
The previous pass's check had finished, the fine_sm8 eigen had finished, the cyc eigen was cut off, and `check_gj` was
from an older body. Its exported STLs drilled the tube bore through the solid stay foot (z 0-30), which gave the
0.12 / 0.42 stay-foot eigen modes. Fixed (bore over the tube length only), parts rebuilt, everything re-run on v3:
check (4 bases), check_gj (2), eigen fine_sm8 (basis, extra, set-down) + fine_sm8.cyc (basis), lash on CF-LITE.

## Result

| row | H1 | CF-LITE (exported parts) |
|---|---:|---:|
| printed strength / fatigue / creep | 1.63 / 1.25 / 2.66 | 1.74 / 2.01 / 4.30 |
| cinch-cycled fatigue (R1) | 0.86 | 1.15 |
| tube strength (beam, z 192) | - | 1.18 |
| **bond Volkersen peak (P3, C8)** | 1.16 (joint) | **0.41** (P1 0.48) |
| **fail-safe printed bearing** | - | **0.68** |
| **eigen buckling of record** | 1.34 | **0.41-0.46** (export loss; pre-export 1.29) |
| BL-068 lash, after: p99 / max voxel | 4.18 / 1.38 | 4.15 / 1.41 |
| frame line | 1387.1 g (3.06 lb) | 1363.7 g (3.01 lb) |

- **Verdict: CF-LITE fails the Strong gate. Stay on H1.** The bonded P3 cannot pass (0.72 at 10 mm wall / 1.5 mm line;
  needs 5.15 MPa dry bond vs 3.7 cited). The lightest fix that passes first-order, P1 + P3 pinned (2 x D5 a side) plus
  the lower-branch root, gives 1407.0 g, **+19.9 g (+0.7 oz) over H1**.
- T6p-T pass lines per sleeve are in the record (section 6), not registered, since CF-LITE is not adopted.
- m3: H1 box members +57.5 g (was an unsourced +55 g). m4: 328.4 g outside the print (the reviewer's 336 counts a
  non-print correction as print). m10 and 1453 g were already applied.

## Found, not fixed
- The STL export's smoothing erodes thin roots at part cut faces (lower branch L: eigen 1.52 -> 0.46). Any future
  multi-part print export should keep voxel-exact geometry within a few mm of cut faces.
- DECISIONS 2026-11-24 "+55 g" should read +57.5 g (orchestrator row).

## Open (only if CF-LITE is revived)
- Pinned-joint variant needs its own contact FE, backlash and PA creep check and a pinned T6b coupon.
- Tube Tsai-Wu on the real layup (m8); the set-down single-voxel tube hot spot (0.26) is not located.
- Cyc extra / set-down eigen steps not run (the record is already set by the static mode).
