# BL-016 One physical test plan for the owner

**Wave:** 1 (independent, low CPU) · **Agent:** manufacturing-engineer · **Size:** M · **Depends on:** none

## Why
More than 40 coupon and prototype tests are defined across a dozen analysis documents (CA-1…5, HB-1…7, PT-1…7, T1…T9, RC-, WP-, MOD-, D- and E- series). Many design margins and weight savings are gated on them. The owner is a beginner and needs one ordered, costed plan.

## Goal
One document that tells the owner what to test first, what each test needs, and what each result unlocks.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/tests_physical/CA1_fatigue_rig.md`; test sections in `frame_h1.md`, `frame_comp_verdict.md`, `hipbelt_fit.md`, `hipbelt_structural.md`, `weight_c_structural.md`, `corrie_body.md` §12.4, `float_fea.md`, `bag_attachment.md`, `fabric_swap_evidence.md`, `load_standard.md` (T1–T9), `build_simplicity.md` (the shared rig proposal S-14).

## Tasks
1. Collect every defined test into one table: `id, what it proves, design item it gates, grams or safety at stake, specimen, equipment, steps in plain language, pass/fail number, cost (cited or ASSUMPTION), hours`.
2. Remove duplicates and flag tests that two documents define differently.
3. Group into kits that share equipment (for example one lever rig and load cell for CA-1, CA-5, HB-5, PT-1 and PT-6).
4. Order by value: safety first, then grams unlocked per dollar and hour. Give a first-weekend list.
5. Write the equipment shopping list with cited prices and totals per kit.
6. Mark tests that only apply to superseded designs (SPINE-only, TENDON, competition entries not adopted) as retired.

## Deliverables
- `designs/pack_5200/tests_physical/TEST_PLAN.md` and `test_register.csv`
- `outputs/screens/20261111_BL016_1.png` (tests ranked by value, one page, phone readable)

## Acceptance
- Every test in the plan cites the document that defined it.
- A beginner could run the first-weekend list from this document alone.
