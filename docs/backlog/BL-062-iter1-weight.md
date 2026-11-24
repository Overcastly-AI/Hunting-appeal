# BL-062 Iteration 1, system weight track (everything but the frame)

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-058 roll-up state, docs/RUBRIC.md · **Date:** 2026-11-24

Goal: under the owner's rubric (strong is a gate, then lighter, then looks), find the lighter alternatives for the
~4.0 kg base outside the frame body and its pins and hardware, which the structural track is working in parallel.
That covers the bag shell and pockets (CORRIE F rev 3), straps, harness, hipbelt, back panel, roll-top / lid,
fly pocket, hardware, thread, and the base vs add-on split. The output is proposals only. No released pattern, ledger
config or roll-up step changes.

## Deliverables
- `docs/research/weight_iter1.md`: cited research on leader line items, lighter fabrics, webbing, mesh, hardware
  and modularity.
- `designs/pack_5200/iter1/system/iter1_weight.py` (+ `.md`, `.json` written by it) and `tests/test_iter1_weight.py`.
- Screenshots: `outputs/screens/20261124_iter1_weight_1.png` (mass waterfall, today to each option) and `_2.png`
  (top-15 Pareto with the best lever on each).

## Result (re-run the code for current numbers)
- Today, belt M, base: proven now 4038.1 g, after the gated tests 3450.9 g. The frame accounts for 1387.1 g of that,
  and this ticket's scope for 2063.8 g.
- In scope we are already level with the leaders. Back panel + spreader + belt + harness come to 954 g, against
  KUIU ICON 6's belt + harness + hip pouches at about 1052 g (inference). The 6.6 lb gap is the frame body.
- Option A, the same look with lighter hidden materials (N1-N5): **−82.3 g**, +$8.37 a pack. Recommended.
- Option B, A plus three unfrozen pockets as shipped clip-on modules: −139.2 g base, but only −48.6 g as hunted.
- Option C, the aggressive package: −232.1 g base, −82.7 g as hunted. The N6 Dyneema wraps are pending a
  ladder-lock slip test.
- No option reaches 6.6 lb. Even C is 225 g over.

## Owner decisions (in the analysis doc, section 4)
1. Adopt option A into after tests, gated by MESH-1/2, US-BS on Ti, AB-2 and SLV-1.
2. Make the pockets modules (FP-L/R, IMP-4, IMP-6; and, as DESIGN-requirement owner calls, IMP-2 and IMP-5L)?
   Recommendation: not now. It cuts base mass but adds mass as hunted.
3. Run LL-D (Dyneema in heavy ladder locks) and SH-1 (ULTRAGrid strap seams) in the same test lot as option A?
   Recommendation: yes, because they are cheap tests for −28.8 g.

## Follow-ups (materials-engineer records)
`spacer_mesh_3d_230`, `spacer_mesh_3d_320`, `triglide_25mm_ti`, `dyneema_webbing_25mm_thin`, `slider_8`.
