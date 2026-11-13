# BL-038 Physical test kit: what to buy, build and do, in order

**Agent:** manufacturing-engineer · **Size:** M · **Depends on:** BL-037

The owner runs the physical tests. Turn `designs/pack_5200/tests_physical/TEST_PLAN.md` into a kit they can follow.

1. **Register:** add rows to `test_register.csv` for every gate in TEST_PLAN.md that has none: the BL-037 gates (HS-1, CS-1, AB-1, SL-1, ST-1, BU-1), the T9 rev 3 items, US-BS, PORT-1, GT-1, the B-28 slip gate (LL-H) and FRAY-1. Re-score the §5 value ranking: CA-1 is no longer worth 60 g (BL-037).
2. **Order of work:** put the gates in an order that releases the most first, in this sequence:
   - frame release R1 (MT-1, CA-1, T1/T2);
   - bag release;
   - the BL-037 weight gates.
   Group tests that share a rig or specimen batch.
3. **Shopping list:** one CSV and one markdown file covering every specimen, rig part, gauge and tool, with quantity, supplier and price from the material records or cited, and the total cost. Mark long-lead items (the cams and sliders were out of stock on 2026-11-13).
4. **Step-by-step guides** for each test group, written for a beginner. Each guide covers the rig sketch, the loads (N and lb), the pass criteria, what to record, and safety. Where rig docs already exist (e.g. `CA1_fatigue_rig.md`), reuse them.
5. **Results sheet:** one results template (CSV) that the owner fills in, and that `huntkit` can read back to flip ASSUMPTION rows. Add a small reader, plus a test for it.
6. **Output:** put everything in `outputs/release/test_kit/`. Screenshots prefix `20261113_BL038_`.
