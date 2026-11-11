# BL-021 IM3 eye and frame body on the cloth-sim loads, with margin for scatter

**Wave:** 5 · **Agent:** structural-fea-engineer · **Size:** M · **Depends on:** BL-010, BL-011, BL-014

## Why
BL-014 (`designs/pack_5200/analysis/review_20261111.md`) found:
- **B2:** the 27 mm IM3 cheek's fatigue margin (1.04) is smaller than its own input scatter:
  - mesh sensitivity: 1.036 / 1.025 / 1.116 at h 1.0 / 0.8 / 0.7 mm;
  - the hook force comes from a coarse cloth mesh, and the left and right hooks differ by 4 %;
  - the load direction is assumed;
  - the bag hook and the IM3 meat strap acting on the same eye together were never checked.
- **B2:** the H1 body fatigue (1.150, governing at the IM3 couple) uses beam loads of 143–190 N at 1 g, against 460–552 N in the cloth sims.
- **S3:** BL-007 and BL-017 fatigue figures were not restated per torso setting.

## Goal
An IM3 eye and a frame body that pass rev C on the cloth-sim forces with **fatigue ≥ 1.15** (to cover scatter), each number shown with its sensitivity.

## Tasks
1. Run CORRIE F's 15 in meat case on the fine cloth mesh (`designs/pack_5200/concepts/corrie_f_sim/corrie_f_sim.py`, fine) and take the IM3 hook force **vector** (magnitude and direction) per side. Report coarse vs fine.
2. Apply that vector, and the IM3 meat-strap load acting at the same time on the same eye (worst rev C combination), to the fairlead FEA (`huntkit/gendesign/loadpath_check.py`). Run a mesh convergence study (state the converged value and how you judged it). Size the cheek for fatigue ≥ 1.15 and strength ≥ 1.5. Give the mass and clearances.
3. Put the per-side cloth-sim forces (bag hooks, hinge pins, guys) into the H1 body check in place of the beam bag couple, per torso setting. Report body strength, fatigue and creep. If anything is under 1.15 fatigue, give the smallest local fix.
4. Restate BL-007 (a)/(c) and BL-017 (c17, OD 17 legs) fatigue per torso setting in an addendum section of your own doc (don't edit theirs).
5. Give the CA-1 flip points (the fatigue ratio at which each part reaches 1.0) for the final body and cheek.

## Deliverables
- `huntkit/gendesign/im3_body_simloads.py`, `tests/test_im3_body_simloads.py`
- `designs/pack_5200/analysis/im3_body_simloads.md` and `.json`

## Acceptance
- Every margin is stated with its mesh and input sensitivity.
- The recommendation is ≥ 1.15 fatigue on the sim loads, or the doc says plainly what cannot reach it.
