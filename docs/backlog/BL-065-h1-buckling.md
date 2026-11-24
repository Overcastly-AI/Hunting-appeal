# BL-065 H1 buckling: eigenvalue check on the released print

**Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-061 (finding 1), BL-058 / BL-060 (print md5 `7bd47cbd…`) · **Date:** 2026-11-24

Ask (orchestrator, DECISIONS 2026-11-24): BL-061 found H1's member buckling 0.85 / 0.87 on each member's real I_min instead of the 1.05 / 1.02 of record. Run a linear eigenvalue check (and a side-squeeze case) on the exported print, report the real margin, the governing mode, which number was closer and why; if below 1.0, size the smallest fix to >= 1.15 without dropping any other row.

## Deliverables
- Code: `huntkit/fea/voxel_buckling.py` (H8 initial-stress stiffness, Lanczos, member isolation, eigen-only bracing), `huntkit/gendesign/bl065_h1_buckling.py` (runs), `bl065_report.py` / `bl065_text.py` (record, figures). `frame_iter1.check` takes a prebuilt body (`con=`).
- Tests: `tests/test_voxel_buckling.py` (closed-form Euler), `tests/test_bl065.py` (record).
- Record: `designs/pack_5200/analysis/bl065.{md,json}`; `bl058.json` `bl065_eigen` block (code).
- Screenshots: `outputs/screens/20261124_bl065_1.png`, `outputs/screens/20261124_bl065_2.png`.

## Result

| reading | static-cinch | cinch-cycled |
|---|---:|---:|
| record rule (bl058.json) | 1.05 | 1.02 |
| BL-061 section rule (K 1) | 0.85 | 0.86 |
| eigen, members (stay tops free) | 1.47 | 1.49 |
| eigen, whole frame (crown held) | 1.34 | 1.34 |
| **real margin** (min of the two above) | **1.34** | **1.34** |
| record model as is (no wearer, top free; support artefact) | 0.16 | 0.19 |

- Governing mode: stay lower L (stay lower L 51%, lumbar strut L 43%), `S_meat@a_L_fine_sm8_23:side_hill_torsion|23`, fine_sm8.
- Upper branch R: eigen 1.47, K_eff 0.76. The record rule was closer (1.05 vs section 0.85): end fixity (1/K^2 = 1.72) outweighs the flat section's 0.81 x I.
- Side-squeeze 416 N a side: 3.71 (crown held), 2.68 (top free).
- **Verdict:** no fix required: the real buckling margin is >= 1.0 on every basis and >= 1.15 (BL-061 goal). Fix: none; mass change 0 g.

## Open
- The record model's whole-frame pitch about the hip boss (support artefact) is only closed physically: T1 rig / side-squeeze test with the harness on (ASSUMPTION BRACE-TOP).
- The spine-channel lip (upper bar underside) buckles locally in hipbelt-off abuse; not load-path (frame reads well above 1 with it deleted). Trim it in the next CAD revision.
- The lumbar strut / stay lower leg by the hip boss governs the frame reading and is not in the record rule's member list; add it to any future rule-based check.
