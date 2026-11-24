# BL-061 Iteration 1, frame track: lighter and at least as strong

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-058 / BL-060 (current print, md5 `7bd47cbd…`) · **Date:** 2026-11-24 · **Rubric:** `docs/RUBRIC.md`

Goal (orchestrator): frame concepts at least as strong as H1 (ideally buckling >= 1.15 and cinch-cycled fatigue >= 1.0)
and materially lighter (aim >= 150 g off the frame; BL-062 follow-up: size against the whole 1387.1 g frame line, say
what else each concept removes, and try a bold <= 900 g concept without losing margin). Research first; every bag
interface stays where it is; buildable at home on the H2S; released print files untouched.

## Deliverables
- Research: `docs/research/frame_iter1.md` (new; production frame masses and constructions, printed / AM nodes, tubes,
  H2S, gyroid, adhesive on carbon, gaps).
- Code: `huntkit/gendesign/frame_iter1.py` (concept builders on the exported print, the extended BL-058 body check,
  section-rule buckling, carbon-tube checks, tube-to-node bonds, ledger-style mass), `frame_iter1_report.py` (record,
  figures, Cycles render), `frame_iter1_text.py` (prose from the JSON). Tests: `tests/test_frame_iter1.py`.
- Record: `designs/pack_5200/iter1/frame/frame_iter1.md` and `.json`.
- Side task: `designs/pack_5200/physical_test_kit.py` (T1 US1 ROOT record only; `g2_locked`, `g2_src_txt`),
  `designs/pack_5200/us1_outer_gauge.py` (md5 lock + `was`), `designs/pack_5200/tests_physical/us1_outer_gauge.json`
  (re-run on the current STL), regenerated `test_register.csv` and `outputs/release/test_kit/`.
- Screenshots: `outputs/screens/20261124_iter1_frame_{1..4}.png`.

## Result (frame line, H1 = 1387.1 g, BL-062 roll-up)

| concept | frame line | delta | strength | fatigue | buckling (record) | cinch-cycled fatigue | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| H1 today | 1387.1 g (3.06 lb) | 0 | 1.63 | 1.25 | 1.05 | 0.86 | baseline (bl058.json reproduced exactly) |
| **E CF-LITE** (carbon-tube stays, 3 printed parts, box members, ribbed cavities) | **1352.6 g (2.98 lb)** | **-34.5** | **1.69** | **1.95** | **1.31** | **1.14** | **every row >= H1; recommended** |
| D CF-BOX | 1356.6 g | -30.5 | 1.50 | 1.92 | 1.28 | 1.12 | R1 pass, strength below H1 |
| B CF-STAY | 1343.8 g | -43.3 | 1.62 | 1.91 | 0.81 | 1.06 | fails R1 (buckling) |
| A BOX (refined print) | 1382.4 g | -4.7 | 1.51 | 1.30 | 1.68 | 0.89 | R1 pass, strength below H1, not lighter |
| C GRADED (slicer gyroid core) | 1336.0 g | -51.1 | 1.36 | 1.18 | 0.98 | 0.80 | fails R1 |

CF-LITE: carbon tube strength / fatigue 1.64 / 1.73; tube-to-node bonds min 1.10 (P3 Volkersen peak, side-hill torsion;
0.57 in the hipbelt-off ultimate case, judged on the average 7.1 and the fail-safe bolt 1.42). Print about 29 h vs 38 h.

**Target met: partly.** Strength gate and both bonuses: yes. Mass: **no**, -34.5 g against the >= 150 g aim; <= 900 g:
no (not reachable without losing margin; frame_iter1.md 5.2).

## Found, not fixed
1. H1's member buckling on each cut's real I_min is 0.86 (static) / 0.87 (cinch-cycled), not 1.05 / 1.02: the record
   rule's solid-round equivalent over-credits the flat 16 x 12 mm upper branch R (I_min 0.81 x the round's). Only
   K = 1 (pinned ends) covers it. Settle with a linear eigenvalue run of the voxel body or the side-squeeze test in
   h1_buckling EULER_RULE.
2. The test register still says T1 has "three gauges" in its steps; US1 ROOT is now read and logged only (the
   pass/fail text says so). No step change made.

## Owner decisions
See frame_iter1.md section 5 and the ticket report: adopt CF-LITE for iteration 2 (build T6p-T coupons first), or keep
H1 and add box members only.
