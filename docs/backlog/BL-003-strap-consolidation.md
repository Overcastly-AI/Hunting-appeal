# BL-003 One strap architecture (meat haul + compression)

**Wave:** 1 · **Agent:** pack-designer · **Size:** L · **Depends on:** BL-001

## Why
Straps and their hardware weigh 539 g (meat haul + compression), plus wing, pouch and roll-top straps booked in the bag body. Five systems overlap: IM1–IM3 internal meat harness 254 g, under-strap cradle US1/US2 122 g, haul wraps W1–W3 108 g, float links B-24 54 g, and the wing straps. See `bag_weight_review_20261110.md` §2.1.

## Goal
A strap architecture that keeps every function with **at least 200 g less** than today (stretch 300 g), and is simpler to use and sew.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/meat_haul_modes.md`, `float_fea.md`, `bag_attachment.md` §7 (procedures); `huntkit/gendesign/meat_haul.py`; `designs/pack_5200/analysis/loadout_study.md` (boned meat fits in the bag; float is rarely needed); team B's use of W1/W2 as compression (`bag_comp/lean/fell.py`, `analysis/bag_comp_lean.md`); team C's hoop-load lid straps (`bag_comp/C/tailgate.py`, `result.json` key `hoop`); hardware records in `data/materials/hardware/` and `webbing/`.

## Functions that must survive
- **F1** meat inside the bag, cinched against the spreader (owner-frozen: internal meat straps).
- **F2** bag-off haul: meat on the frame, limit 53 kg (`float_fea.md`).
- **F3** float: bag hung behind the meat, gaps 120/170/220 mm (owner decision 2026-11-06).
- **F4** carry compression for small loads.
- **F5** side carry (tripod, poles, scope pod).
- **F6** door zip carries no hoop load.
- **F7** roll-top closure, and pouch hold-down if a pouch stays.

## Tasks
1. Tabulate today's parts per system with mass, rated load, factored load and the governing margin, from the existing analyses. Mark where a part is over-strength by more than 2× its requirement.
2. Research (cited, `docs/research/strap_systems.md`): how Stone Glacier, Exo, Kifaru, Seek Outside and Mystery Ranch get meat carry and compression from one strap set; rated light hardware (25 mm cams, G-hooks, ladder locks, sewn loops over pins) with published strengths.
3. Generate at least three architectures. Required candidates:
   - **(a) lighten in place:** 38 → 25 mm where margins allow; sewn loops on the frame pins instead of sliding-gate hooks; lighter cams.
   - **(b) one external set:** three straps at the IM heights doing F4, F5, F6 and the F3 wrap; wings deleted; W1–W3 deleted.
   - **(c) meat-trip kit:** float links, and anything used only at F2/F3, leave the base pack and ride in the kill kit.
   Combinations are allowed.
4. For each: mass by part (from the ledger where parts exist), which function each strap serves, user steps and seconds for F1–F3 (same method as `meat_haul.DETACH_S`), hardware count, sewing operations, and every load path that changes with its new factored load. Do NOT certify strength: list the changed load paths for BL-010.
5. Check the patent guardrails for each architecture (no fabric shelf; under-straps pin to pin; no bag webbing between the spreader and the z 330 cross member).
6. Recommend one. State the saving against the ledger's `straps_meat + straps_compression`.

## Deliverables
- `designs/pack_5200/concepts/strap_arch.py` (parts tables and procedure times), `tests/test_strap_arch.py`
- `designs/pack_5200/analysis/strap_architecture.md` (with a "load paths for BL-010" table: location, direction, factored N, part, rated N)
- `docs/research/strap_systems.md`
- `outputs/screens/20261111_BL003_1.png` (side-view diagram of each architecture in the three modes), `_2.png` (mass bars by function)

## Acceptance
- All seven functions are shown working for the recommended architecture, with steps.
- The saving is stated against the ledger and is ≥ 200 g, or the doc explains with numbers why not.

## Out of scope
FEA or strength sign-off (BL-010). Changing `meat_haul.py`, `corrie.py` or any released file.

## Owner decisions this ticket should tee up
Float parts as a meat-trip kit outside base weight; deleting the wings.
