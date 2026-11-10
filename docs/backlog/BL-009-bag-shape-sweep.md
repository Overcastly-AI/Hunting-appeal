# BL-009 Bag shape sweep for CG margin and a better silhouette

**Wave:** 1 · **Agent:** pack-designer · **Size:** L · **Depends on:** none

## Why
On a 15 in torso the meat-case load CG is close to the 190 mm limit for every bag so far (175–187 mm before a +4 mm sim bias). Only team B's shell, 3 % shallower, has real margin (175.4 mm). All five competition renders also read as an inflated sack that mushrooms above the shoulders. Shape, not features, drives both.

## Goal
A box-family shell with zero or one curved seam that holds 85 L ±3 and gives **15 in meat CG ≤ 176 mm and fill CG ≤ 190 mm as simulated** (so ≥ 10 mm margin after the +4 mm bias), with a cleaner silhouette.

## Read first
`docs/backlog/RULES.md`; `huntkit/clothsim/corrie_bag.py` and scenarios `corrie_PR{15,19,23}c.yaml`; `designs/pack_5200/concepts/corrie.py` (shell parameters); team B's shell and sims (`bag_comp/lean/fell.py`, `fell_clothsim.py`, `result.json` key `sims`); team A's taper and wider base (`bag_comp/A/evolve.py`); `designs/pack_5200/analysis/corrie_body.md` §5a and §11.4 (convergence fix, rounding bias, the side-gusset wrinkling finding).

## Tasks
1. Build a parametric shell generator in your own file by importing the CORRIE loader (do not edit it). Parameters: depth at base and shoulder, height to the collar seam, width taper toward the roll, gusset length, base width.
2. Run a coarse-mesh sweep (h 40 mm) of at least 12 shells at 15 in, fill and meat cases, with the 1 kg pouch and 85 mm scope as in `corrie_PR15c`. Record volume, CG y and z, max warp/weft strain, wrinkle area on the gussets, worst seam load. One sim at a time.
3. Take the best three to 19 and 23 in. Check head clearance against requirement R-28 (use `huntkit.gendesign.attach_system.r28_loaded`; results format in `bag_attachment.md` §1).
4. Pick one shell. Confirm the frame interface heights still land on laminate (hood ladder, B-22 guy tabs below the collar seam).
5. Render the chosen shell with Cycles at three load states: day (about 12 L, rolled and cinched), 6-day (45 L) and full (85 L), same camera, so the owner sees what it looks like when not stuffed.

## Deliverables
- `designs/pack_5200/concepts/shell_sweep.py`, scenarios under `designs/pack_5200/concepts/shell_sweep_scenarios/`, `tests/test_shell_sweep.py`
- `designs/pack_5200/analysis/shell_sweep.md` (sweep table, chosen parameters, flat piece dimensions)
- `outputs/screens/20261111_BL009_1.png` (CG vs depth plot), `_2.png`–`_4.png` (three load states)

## Acceptance
- Every sweep row states convergence and rounding stage. Unconverged rows are not used for the choice.
- The chosen shell meets the goal numbers, or the doc shows the best achievable and what it costs in height.

## Out of scope
Pockets, doors, straps (BL-011). Editing `huntkit/clothsim/`.
