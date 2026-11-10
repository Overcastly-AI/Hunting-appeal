# BL-011 Merged bag "CORRIE F"

**Wave:** 2 · **Agent:** pack-designer · **Size:** XL · **Depends on:** BL-001, BL-002, BL-003, BL-004, BL-009, BL-010

## Why
The bag competition produced five feature sets on one shell. The review recommends merging the best of each with the new strap architecture and the tuned shell.

## Goal
One bag concept, engineered to the level of CORRIE B.2, that beats CORRIE B.2 on the ledger's `bag_side` total by **≥ 350 g** (bag, pockets, pouch, fly, straps, attachment), with zero pack-on access misses on the day and 6-day loadouts and no more than one on the sheep loadout.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/bag_weight_review_20261110.md`; `bag_comp_verdict.md` (BL-002); `strap_architecture.md` (BL-003); `attachment_diet.md` (BL-004); `shell_sweep.md` (BL-009); `loadpath_verification.md` (BL-010: use only PASS rows, or "PASS after test" rows marked as gated); `designs/pack_5200/analysis/fabric_swap_evidence.md`; `corrie.py`; the five team folders.

## Ingredients (start from these; drop one only with a stated reason)
- **Shell:** the BL-009 shape, zero or one curved seam.
- **Fabrics:** team B's map (ULTRAGrid body, 70D collar, ULTRA 200X floor) with each swap's gate from `fabric_swap_evidence.md` written next to it. Also give the mass with today's fabrics, in case the owner declines the swaps.
- **Straps and attachment:** the BL-003 and BL-004 recommendations as verified by BL-010.
- **Door:** design two options to the same level and let the owner choose:
  - **D1** team C's full-face opening with the hoop-load straps;
  - **D2** team E's camo-blade door.
  Report mass, zip length, clear width at IM1/IM2/IM3 and beginner hours for both.
- **Access:** team A's hip-reach pockets; a shoulder-strap snack or phone pocket; a spot for the second bottle on the sheep loadout.
- **Meat liner:** team D's removable wipeable slab, as an add-on.
- **Look:** team E's rule that panel line, camo break and zip share one line.
- **Add-ons outside base weight:** scope pod, tripod straps, top pouch, bottle holster, meat liner, float kit. Book base and as-hunted separately (use BL-008's proposal if it exists).

## Tasks
1. Write the concept module with pieces, materials from records, masses via the ledger's systems, and a `weight_table(size, config)` for base and as-hunted.
2. Cloth sims at 15/19/23 in, fill and meat (coarse), with the add-ons on; one fine drape for renders. Report CG against rev C with the +4 mm bias.
3. Loadout check for all three loadouts and all belt sizes (pattern: `corrie_loadout.py`).
4. Build metrics: pieces, seam length, curved seams, zip length, beginner hours, with the same model as `bag_concepts`.
5. Write-up with a pieces list, the mass table against CORRIE B.2 on the ledger basis, gates and prototype tests, and a list of what the pattern-maker needs.

## Deliverables
- `designs/pack_5200/concepts/corrie_f.py`, `corrie_f_loadout.py`, clothsim loader and scenarios under `designs/pack_5200/concepts/corrie_f_sim/`, `tests/test_corrie_f.py`
- `designs/pack_5200/analysis/corrie_f_body.md`, `designs/pack_5200/concepts/corrie_f_result.json` (same keys as `bag_comp/RULES.md` rule 5, plus `bag_side_g_base` and `bag_side_g_as_hunted`)

## Acceptance
- The goal numbers are met, or the doc shows which ingredient fell short and by how much.
- 15 in meat CG ≤ 180 mm as simulated.
- Both door options are complete enough to choose between.

## Out of scope
Renders (BL-012). Editing `corrie.py` or team files. Pattern release.
