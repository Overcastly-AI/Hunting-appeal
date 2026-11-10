# BL-010 Structural verification of the changed load paths

**Wave:** 2 · **Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-003, BL-004, BL-006

## Why
BL-003 (straps), BL-004 (attachment) and BL-006 (hipbelt) each recommend lighter parts and hand over a table of changed load paths. None of them certifies strength.

## Goal
A pass or fail for every changed load path under HA-LS-1 rev C, so BL-011 only integrates what passes.

## Read first
`docs/backlog/RULES.md`; the "load paths for BL-010" tables in `designs/pack_5200/analysis/strap_architecture.md`, `attachment_diet.md`, `hipbelt_diet.md`; `designs/pack_5200/analysis/load_standard.md`, `float_fea.md`, `rev_c_verification.md`, `hipbelt_structural.md`; `huntkit/gendesign/float_fea.py`, `rev_c_verification.py`, `hipbelt_structure.py`; hardware and webbing records in `data/materials/`.

## Tasks
1. For each row in the three tables: confirm the factored load from the rev C cases (do not accept the ticket's number unchecked), then check the part, its stitching or bartack, and the frame-side feature it loads (fairlead cheek, pin, eye, H1 body locally).
2. Report strength, fatigue (1e5 cycles of 0 to 1.6 g) and creep where a polymer or printed part carries sustained load. Use the existing solvers; reproduce one existing released result first as a check.
3. Where a record has no rated value, mark the margin "assumed" and define the coupon or pull test.
4. Give each row a verdict: PASS, PASS after test X, or FAIL with the smallest change that passes and its mass.

## Deliverables
- `huntkit/gendesign/loadpath_check.py`, `tests/test_loadpath_check.py`
- `designs/pack_5200/analysis/loadpath_verification.md` and `.json`
- `outputs/screens/20261111_BL010_1.png` (margin per row)

## Acceptance
- Every row from all three tables has a verdict. No row is dropped.
- Net mass after FAIL fixes is stated per source ticket.

## Out of scope
Re-designing the architectures. Editing the source tickets' files.
