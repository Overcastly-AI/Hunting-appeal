# BL-013 Whole-pack weight roll-up, version 2

**Wave:** 3 · **Agent:** pack-designer · **Size:** M · **Depends on:** BL-001, BL-005, BL-006, BL-007, BL-008, BL-010, BL-011

## Goal
One honest answer to "what does the pack weigh now, and what can it reach?", built only from the ledger and the verified results of the other tickets.

## Tasks
1. Extend the ledger with configs for: CORRIE F base and as-hunted; the BL-005 back system; the BL-006 belt package; each BL-007 frame variant. Import the tickets' modules; type no totals.
2. Build three scenarios at belt M and report S–XXL:
   - **proven now:** only changes with PASS verdicts and no open test gate;
   - **after tests:** adds changes gated by a named test (list the tests);
   - **owner options:** adds the fixed-torso frame and anything needing an owner decision.
3. Waterfall chart from 3927 g (CORRIE B.2 on H1) to each scenario, against 2994 g (6.6 lb) and the leaders' range, on BL-008's like-for-like basis.
4. State plainly whether 6.6 lb is reachable, with what, and what it costs in features.
5. List every mass in the roll-up that is still an estimate, with its uncertainty.

## Deliverables
- `designs/pack_5200/weight_rollup_v2.py`, `tests/test_weight_rollup_v2.py`
- `designs/pack_5200/analysis/weight_rollup_v2.md` and `.json`
- `outputs/screens/20261111_BL013_1.png` (waterfall), `_2.png` (like-for-like bars against the leaders)

## Acceptance
- Every bar in the waterfall traces to a ticket deliverable and a ledger row.
- The three scenarios are kept separate everywhere; no "after tests" saving appears in "proven now".
