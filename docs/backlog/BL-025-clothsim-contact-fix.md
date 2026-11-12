# BL-025 Cloth-sim contact-field fix and re-runs

**Agent:** pack-designer · **Size:** M · **Depends on:** none

## Why
BL-021 found that when the contact-rounding continuation stops early, `huntkit/clothsim` restores x to the last converged stage but leaves the contact fields on the last stage tried. Reported `contact_*` forces and spreader pressures are then computed on the wrong field: F_PR15_fineFM meat reports 1327 N where its kept stage gives 1087 N. Also:
- BL-022 overwrote the coarse `outputs/clothsim/corrie_f/F_PR{15,19,23}` folders with rev 1 runs, so `tests/test_loadpath_check.py::test_a1_cf_per_torso_cheek` fails (547.7 vs 552.4);
- the guys-off IM3 load disagrees between meshes (coarse 970 N vs fine 436 N);
- the H1 body result depends strongly on the cloth mesh (coarse 1.29 vs fine 1.00), and only one fine 23 in meat run exists.

## Tasks
1. Fix the contact-field restore in `huntkit/clothsim/pack.py` / `report.py`: after a stopped continuation, the fields and every reported force must come from the kept stage. Add a regression test. Keep existing tests passing.
2. List every analysis that used reported contact forces (spreader pressures, BL-004, BL-009, BL-011, BL-022, BL-021 inputs) and re-compute the affected numbers from the stored states where possible; state any that change by more than 2 %.
3. Store rev 0 and rev 1 CORRIE F runs in separate folders (`F_r0_*`, `F_r1_*`) and update `loadpath_check` and `corrie_f_sim` to read the right one, so the failing test passes for the right reason.
4. Run a second fine 23 in meat case (different start rounding) and a fine guys-off 15 in case from 6 mm rounding. Report the scatter in IM3 and CG.

## Deliverables
Fix plus tests in `huntkit/clothsim/`, `designs/pack_5200/analysis/clothsim_contact_fix.md`, updated run folders and readers. Run the full test suite once at the end.
