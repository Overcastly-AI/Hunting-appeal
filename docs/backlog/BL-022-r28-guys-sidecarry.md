# BL-022 CORRIE F: head clearance on the fine mesh, guys-off case, crown-bar clash, side carry

**Wave:** 5 · **Agent:** pack-designer · **Size:** M · **Depends on:** BL-011, BL-014

## Why
BL-014 (`designs/pack_5200/analysis/review_20261111.md`) found:
- **B3:** CORRIE F's R-28 pass at 23 in (32°) holds only on the coarse mesh. The one coarse/fine pair moves the frame-side face 5.3–6.4 mm toward the head; with 6 mm more wall the result is 30°, a fail.
- **S6:** the guy loops at x ±(92–100) may clash with the lifter lugs at x ±105 on the crown bar (`attach_system.py` around line 1445 already flags it). The lifters are a patent guardrail.
- **S7:** side carry (F5) gets worse without wings: opening the door unhooks W1/W2 and frees the tripod.
- **S11:** the guys-off misuse case was never simulated on CORRIE F.

## Tasks
1. Run CORRIE F at 23 in on the fine cloth mesh (meat and fill) and compute R-28 with `attach_system.r28_loaded(..., design_face=...)`. If it is under 31° (≥ 1° margin), increase the top setback in steps until the fine-mesh R-28 is ≥ 31° at 15, 19 and 23 in. Report volume, CG and access effects.
2. Simulate the guys-off case on CORRIE F at 15 in (meat). Report the CG and the IM3 load. Confirm that the carry rule and hang-tag wording in `corrie_f_body.md` cover it.
3. Check the guy loop and lifter lug positions on the crown bar for the three crown kits. If they clash, move the guy loops (keeping the lifters on the top bar) and re-run the 15 in meat CG.
4. Side carry: propose the lightest way to keep the tripod and scope pod held when W1/W2 are unhooked to open the door, for example a short keeper strap or a W-strap routing that holds the tripod independently. Give its mass and glove time.
5. Put the results into `designs/pack_5200/concepts/corrie_f.py` as **CORRIE F rev 1** (keep rev 0 reproducible) and update `corrie_f_body.md` with a rev 1 section. Update the tests.

## Deliverables
- Changes to `designs/pack_5200/concepts/corrie_f.py`, `corrie_f_sim/`, `tests/test_corrie_f.py`
- `designs/pack_5200/analysis/corrie_f_body.md` (rev 1 section)
- `outputs/screens/20261111_BL022_1.png` (R-28 coarse vs fine, before and after)

## Acceptance
- R-28 is ≥ 31° on the fine mesh at all three torsos, or the doc states the remaining shortfall.
- No clash between guys and lifters at any crown kit.
