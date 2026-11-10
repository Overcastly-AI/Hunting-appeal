# BL-007 Study: print-to-size frame without the telescoping crown

**Wave:** 1 · **Agent:** structural-fea-engineer · **Size:** L · **Depends on:** none

## Why
The H1 frame is 1025 g. A large fixed block exists only to make torso length adjustable: the carbon crown legs, the long sleeves in the printed stays they slide in (team E measured the upper stays at 342 g), the rack, pawl, guides and four bushings, and the 3:1 pulley adjust (42 g). The frame is printed per unit, so the torso length could be printed in, with a small fine adjustment at the harness yoke. This has never been studied. It is the largest lever left on the frame.

## Goal
Find out how much a fixed-torso printed frame saves while passing rev C, and what the owner gives up. This is a study for an owner decision, not a design change.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/frame_h1.md`, `frame_h1_results.json`; `huntkit/gendesign/frame_h1.py`; `designs/pack_5200/frame.yaml` (crown, torso adjust); `designs/pack_5200/analysis/frame_comp_verdict.md` (the "keep-out zones limit the body" finding); `designs/pack_5200/analysis/rev_c_verification.md`; `docs/DECISIONS.md` (lifters on the crown top bar: Mystery Ranch US 10,952,523 guardrail; the owner keeps the top bar and the spine tube); `designs/pack_5200/analysis/bag_attachment.md` (hood B-19 over the top bar, ladder B-20 has one rung per crown setting).

## Tasks
1. Research (cited, `docs/research/fixed_vs_adjustable_frames.md`): which leaders sell fixed-length frames in sizes and which adjust, how much adjustment the harness yoke gives on each, typical torso-length size steps, and return or resale notes if published.
2. Define variants and re-run the H1 pipeline (same checks, all 42 rev C sets):
   - **(a) fixed crown:** crown legs bonded or bolted at one height per unit; no rack, pawl or pulley; sleeves only as long as the joint needs;
   - **(b) printed upper frame:** stays printed to full height with a carbon or printed top bar; the bed is 340 × 320 mm, so state the number of segments and joints, using the H1 bolted-joint method;
   - **(c) (a) plus stays re-sized now that the sleeve keep-outs are gone.**
   Keep the top bar and the harness spine function. Keep the lifter position on the top bar.
3. For each: frame mass, every margin, torsion stiffness against H1, print time, part count, build steps, cost.
4. State the fit consequences plainly: fine-adjust range left at the yoke (mm), how many torso sizes cover 15–23 in, what a customer does if the size is wrong, and what changes in the bag attachment (the hood ladder B-20 may shrink to one rung).
5. Give the pack mass with each variant from the ledger basis (CORRIE B.2 on H1 = 3927 g).

## Deliverables
- `huntkit/gendesign/frame_fixed.py`, `tests/test_frame_fixed.py`
- `designs/pack_5200/analysis/frame_fixed_torso.md`, `docs/research/fixed_vs_adjustable_frames.md`
- `outputs/screens/20261111_BL007_1.png` (Cycles render next to H1), `_2.png` (mass and margins per variant)

## Acceptance
- H1's own numbers are reproduced first (strength 1.45, fatigue 1.28).
- Every variant has all rev C margins reported, pass or fail.
- The doc ends with a one-paragraph plain-language trade-off for the owner.

## Out of scope
Editing `frame_h1.py`, print files or the crown release data. Adopting anything.
