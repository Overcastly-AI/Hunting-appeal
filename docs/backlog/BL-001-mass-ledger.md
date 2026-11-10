# BL-001 One mass ledger for the whole pack

**Wave:** 0 (run first, alone) · **Agent:** pack-designer · **Size:** M · **Depends on:** none

## Why
Pack mass is booked in several scripts with different definitions. The five bag-competition teams used four different numbers for the same CORRIE B.2 bag system (710.6, 716.5, 721.7 and 892.1 g), so their results cannot be compared. The earlier weight pass also compared our bag fabric against the leaders' complete bags (see `designs/pack_5200/analysis/bag_weight_review_20261110.md` §2).

## Goal
One module that every later ticket reads masses from, with fixed group definitions.

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/weight_pass_corrie.py` and its `.json`; `designs/pack_5200/concepts/corrie.py` (`weight_table`, `package_c_rows`); `designs/pack_5200/build_geometry.py` (weight rows); `designs/pack_5200/analysis/frame_h1.md` and `frame_mass_h1.json`; how each team computed its baseline: `bag_comp/A/make_result.py`, `bag_comp/lean/fell_results.py`, `bag_comp/C/make_result.py`, `bag_comp/D/result.py`, `bag_comp/form/form_result.py`.

## Tasks
1. Create `huntkit/mass/ledger.py` (new package, with `__init__.py`). It must not copy numbers: it calls the existing sources (`corrie.weight_table`, the weight-pass part list, `frame_mass_h1.json`).
2. Expose `parts(config)` returning a list of rows `{id, name, group, system, g, source, load_path: bool, base: bool}` for configs `"corrie_b2_today"`, `"corrie_b2_h1"`, `"corrie_b2_h1_c"` at belt sizes S–XXL.
3. Define these **systems** once, and document them in the module docstring:
   - `frame` (printed body, crown, torso adjust, pivot mount);
   - `back` (spreader, back panel);
   - `belt`; `harness`;
   - `bag_shell` (body, collar, door, roll-top, zips);
   - `bag_pockets`; `pouch`; `fly`;
   - `straps_meat` (IM1–IM3, under-straps, float links);
   - `straps_compression` (haul wraps, wings and wing straps, roll-top and pouch straps);
   - `attachment` (fairleads, pins, hooks, hood, ladder, guys, tabs);
   - `misc`.
4. Add `like_for_like()` returning two totals: `bag_side` (bag_shell + bag_pockets + pouch + fly + straps_meat + straps_compression + attachment) and `suspension` (frame + back + belt + harness).
5. Add `bag_system(parts)` giving the single definition of "bag system" used to compare bag entries: bag_shell + bag_pockets + pouch + fly + straps_compression. State it in the docstring.
6. Re-compute each team's bag-system mass on this one definition (import their modules; do not edit them) and write the table to the deliverable doc. Say which teams' published numbers move, and by how much.
7. Tests: totals reproduce `corrie.weight_table` to ±0.5 g for every belt size; every part belongs to exactly one system; `like_for_like` sums to the total.

## Deliverables
- `huntkit/mass/__init__.py`, `huntkit/mass/ledger.py`, `tests/test_mass_ledger.py`
- `designs/pack_5200/analysis/mass_ledger.md` (system table for the three configs; the five teams on one basis)
- `outputs/screens/20261111_BL001_1.png` (stacked bar: systems, three configs)

## Acceptance
- Tests pass. The doc states the CORRIE B.2 bag-system mass as one number and shows each team's entry against it.
- No hand-typed totals anywhere in the module.

## Out of scope
Changing any design. Editing the teams' files or `corrie.py`.
