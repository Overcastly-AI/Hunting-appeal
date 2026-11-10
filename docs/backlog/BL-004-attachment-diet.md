# BL-004 Bag-to-frame attachment diet

**Wave:** 1 · **Agent:** pack-designer · **Size:** M · **Depends on:** BL-001

## Why
The attachment weighs 303 g: 8 printed fairleads 49 g, 8 pins 19 g, 4 rated hooks 56 g, load-spreader tabs 28 g, hood B-19 with stiffener, lining, tongues and toggles about 41 g, ladders B-20 20 g, guys with hardware about 42 g, and small parts. It grew in steps (2026-11-05 and 11-06) and was never reviewed as a whole.

## Goal
Keep the bag's load CG and security; reach **≤ 220 g** (stretch 200 g).

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/bag_attachment.md` (all), `bag_top_anchor.md`, `rev_c_verification.md`; `huntkit/gendesign/attach_system.py`, `bag_attach.py`; `docs/research/bag_attachment_research.md`; the converged CORRIE scenarios `huntkit/clothsim/scenarios/corrie_PR{15,19,23}c.yaml`.

## Tasks
1. List every attachment part with mass, the load it carries in each rev C case, and its margin. Mark parts that carry no load in any case, and parts over 2× their requirement.
2. Test deletions and merges with the coarse cloth sim at 15, 19 and 23 in, fill and meat cases. Required trials:
   - **(a)** 8 fairleads → fewer: which bag anchor heights are needed once the hood and guys hold the top?
   - **(b)** hood + ladder + guys → a lighter top anchor, e.g. two sewn webbing loops over the crown bar with one guy each;
   - **(c)** IM2 hooks deleted, IM3 and hinge pins kept;
   - **(d)** aluminium hooks → sewn webbing loops on the pins where the bag is rarely removed.
   Report the fill CG and meat CG for each against today (15 in meat 184.4 mm; limits 190 / 205) and the peak anchor loads.
3. Keep the bag-off time ≤ 120 s (requirement R-08) and the gloved procedures workable; give the steps for each variant.
4. Recommend one variant. List its changed load paths for BL-010 (location, direction, factored N, part, rated N).

## Deliverables
- `designs/pack_5200/concepts/attach_diet.py`, scenarios in `designs/pack_5200/concepts/attach_diet_scenarios/`, `tests/test_attach_diet.py`
- `designs/pack_5200/analysis/attachment_diet.md`
- `outputs/screens/20261111_BL004_1.png` (CG and mass per variant), `_2.png` (diagram of the recommended attachment)

## Acceptance
- Every variant has converged sims at 15 in (state rounding stage) or is marked unproven.
- No variant is recommended if the 15 in meat CG gets worse than today's.

## Out of scope
Editing `attach_system.py` or `huntkit/clothsim/`. Strength sign-off (BL-010).
