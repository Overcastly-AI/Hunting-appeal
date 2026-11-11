# BL-023 Bring the test plan and the mass ledger up to date

**Wave:** 5 · **Agent:** manufacturing-engineer · **Size:** M · **Depends on:** BL-013, BL-014

## Why
BL-014 found:
- **B1:** the CA-1 release rule still uses a flip point of 0.234 (`tests_physical/CA1_fatigue_rig.md`, `TEST_PLAN.md`, `frame_h1.md`). On the adopted bases it is 0.261 for the body and **0.290 for the 27 mm IM3 cheek**; BL-021 will refine this.
- **S8:** many "after tests" gates are missing from `TEST_PLAN.md`: FT-S2, HB-D1/D2/D3, the IM3 eye pull and cycle coupon, the toggle-loop pull, PT-1 and MT-2 per-row proof loads (BL-010), the backer-strip bend coupon and pressure film (BL-005), and a back-pressure test for whether the rails bear below z 190 (BL-005).
- **HB-1 pressure sensor:** HB-1 needs a sensor in front of the wing tip (BL-006, BL-010).
- **Ledger errors:** BL-013's clean-ups (fairleads, swell patches, crown-corner wraps, pawl housing, non-body lump, keepers, holster tabs, belt webbing) live only in `weight_rollup_v2.py`; `huntkit/mass/ledger.py` still has them, so every new ticket inherits them.

## Tasks
1. Update `designs/pack_5200/tests_physical/TEST_PLAN.md`, `test_register.csv` and `CA1_fatigue_rig.md`:
   - **CA-1 release rule:** the governing flip point is 0.290, and "release requires the measured ratio ≥ the governing flip point + 0.02"; leave a placeholder for BL-021's final value.
   - **New gates:** add every gate listed above with pass numbers from the source documents.
   - **Coupon count:** the IM3 eye cycle coupon uses 3 specimens at ≥ 1.15 × 884 N.
2. Fold BL-013's clean-ups into `huntkit/mass/ledger.py` as corrections with sources, keeping the existing configs reproducible behind a flag. Make sure `tests/test_mass_ledger.py` and `tests/test_weight_rollup_v2.py` both pass.
3. Re-classify the roll-up per BL-014: changes that pass only after a named test, even with a heavier fallback, move from "proven now" to "after tests" (BL-003 (a) IM/US −116.9 g, BL-004 −103 g). Book the IM3 cheek at 27 mm. Regenerate `weight_rollup_v2.md` / `.json` and the waterfall.

## Deliverables
- `designs/pack_5200/tests_physical/TEST_PLAN.md`, `test_register.csv`, `CA1_fatigue_rig.md`
- `huntkit/mass/ledger.py` (corrections), `designs/pack_5200/weight_rollup_v2.py` (re-classification), their tests
- `designs/pack_5200/analysis/weight_rollup_v2.md` / `.json`, and `docs/screens/20261111_BL023_1.png` (waterfall)

## Acceptance
- No test file references a flip point of 0.234.
- The ledger and the roll-up agree to 0.5 g.
