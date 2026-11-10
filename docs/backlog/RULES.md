# Backlog rules (apply to every BL ticket)

Read this file and `CLAUDE.md` before starting any ticket.

## Working rules
1. **Scope:** do exactly the ticket. If you find a problem outside it, write it under "Found, not fixed" in your report; do not fix it.
2. **Files:** write only the files the ticket lists under "Deliverables". Never edit: released files (`outputs/release/`, `designs/pack_5200/print/frame/`, `patterns_v31*.py`), `docs/DECISIONS.md` (the orchestrator adds rows), other tickets' deliverables, or shared modules under `huntkit/` unless the ticket says so. New code goes in the path the ticket names.
3. **Do not commit or push.** The orchestrator commits.
4. **Numbers:** every number traces to a material record (`data/materials/`), a calculation in code, or a line marked `ASSUMPTION:` with a test that would settle it. Units mm, N, MPa, g internally; show imperial next to metric in documents.
5. **Masses:** after BL-001 lands, take every mass from `huntkit/mass/ledger.py`. Never hand-type a total, and never invent your own "bag system" definition.
6. **Research first** where the ticket says so: cited sources with a URL on every claim, written to the `docs/research/` file the ticket names. If a site blocks fetching, say so and mark the claim "secondary".
7. **Honesty:** if the target in the ticket cannot be met, say so with the numbers. A truthful "no" is a pass; an optimistic "yes" is a fail. Report every test you ran and its result, including failures.
8. **Hard limits (never trade these away):** HA-LS-1 rev C loads and factors (`designs/pack_5200/analysis/load_standard.md`); the patent guardrails and owner decisions in `docs/DECISIONS.md`; original IP only (never copy a brand's look).
9. **Owner-frozen features:** internal meat straps IM1–IM3, no fabric meat shelf, under-straps pin to pin, lifters on the crown top bar, bow riser carry, rain fly in a base pocket, quiet bag (no hook-and-loop, coil zips), mostly solid colours with the owner's camo as accents, 85 L ±3, width ≤ 394 mm (15.5 in). A ticket may PROPOSE changing one, as an owner decision, but never applies it.
10. **CPU and usage:** 4 cores, shared. Run only your own tests unless the ticket says "full suite". Cloth sims: coarse mesh (h 40 mm) for numbers, one fine drape for renders. Do not start more than one long job at a time.
11. **Renders:** Blender Cycles via `huntkit/viz3d/cycles_render.py`. The bpy venv lives in the session scratchpad and may be gone: reinstall it by following `huntkit/viz3d/README.md`, outside the repo. Quality bar: `docs/screens/20261109_corrie_b2_1.png`. Look at every image you produce (Read it) before reporting; fix or re-render anything with floating parts, z-fighting, pixel camo or placeholder blocks. PNG ≤ 1.5 MB, to `outputs/screens/20261111_<ticket>_<n>.png`.
12. **Tests:** every new module gets a `tests/test_<name>.py`. Tests must check results, not just that code runs.

## `outputs/` is not tracked by git
A new session starts without `outputs/` (cloth-sim results, GLBs, scratch screenshots) and without the Blender venv. Regenerate what you need with the scripts named in the ticket, and budget time for it. Screenshots you want kept go in `docs/screens/`. The competition renders are kept in `docs/screens/20261110_bag*.png`.

## Report format (your final reply)
```
TICKET: BL-0xx
STATUS: done | partly done | blocked (say why)
RESULT: 3–8 lines with the key numbers
TARGET MET: yes/no (numbers)
FILES: list
TESTS: command + result
ASSUMPTIONS THAT GOVERN: list, each with the test that settles it
OWNER DECISIONS NEEDED: list (plain language)
FOUND, NOT FIXED: list
SCREENSHOTS: list
```

## Key references
- Whole-pack mass breakdown: `designs/pack_5200/analysis/weight_pass_corrie.md` / `.json` (script `designs/pack_5200/weight_pass_corrie.py`).
- Current bag: CORRIE B.2, `designs/pack_5200/concepts/corrie.py`, `designs/pack_5200/analysis/corrie_body.md` (§11 B.1, §12 B.2).
- Bag competition entries: `designs/pack_5200/bag_comp/{A,lean,C,D,form}/` with `result.json` each; rules in `bag_comp/RULES.md`; write-ups `designs/pack_5200/analysis/bag_comp_*.md`.
- Frame: H1, `designs/pack_5200/analysis/frame_h1.md`, `huntkit/gendesign/frame_h1.py`, GLB `outputs/pack3d_h1/h1_frame.glb` (not tracked; regenerate with `frame_h1.py`).
- Hipbelt B: `designs/pack_5200/analysis/hipbelt_fit.md`, `hipbelt_structural.md`, `huntkit/gendesign/hipbelt.py`, `hipbelt_structure.py`.
- Attachment and meat haul: `designs/pack_5200/analysis/bag_attachment.md`, `meat_haul_modes.md`, `float_fea.md`, `huntkit/gendesign/attach_system.py`, `meat_haul.py`, `bag_attach.py`.
- Back system: `designs/pack_5200/analysis/back_rail.md`, `spreader_layout.md`, `huntkit/gendesign/back_rail.py`, `spreader.py`.
- Loadouts and access: `designs/pack_5200/loadouts.yaml`, `designs/pack_5200/analysis/loadout_study.md`, `designs/pack_5200/concepts/corrie_loadout.py`.
- Cloth sim: `huntkit/clothsim/` (CLI `python -m huntkit.clothsim.cli`), CORRIE loader `huntkit/clothsim/corrie_bag.py`, converged scenarios `huntkit/clothsim/scenarios/corrie_PR{15,19,23}c.yaml`.
- Review that created this backlog: `designs/pack_5200/analysis/bag_weight_review_20261110.md`.
