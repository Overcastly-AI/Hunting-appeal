# BL-005 Back system: can one structure do two jobs?

**Wave:** 1 · **Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-001

## Why
The back system weighs 414 g: back panel 251 g (mesh, two 120 × 420 × 10 mm XLPE rails, two 80 × 420 × 1 mm carbon backer strips, sleeves, pad) and the Sandwich v2 spreader 162 g. The spreader sits on the bag side of the stays and stops meat and bone pressing through; the rail backers sit on the wearer side and spread pressure on the skin. Nobody has tested whether one stiff structure can do both.

## Goal
Meet the same skin-pressure and bone-punch rules with **≤ 320 g** (stretch 290 g).

## Read first
`docs/backlog/RULES.md`; `designs/pack_5200/analysis/back_rail.md`, `spreader_layout.md`, `spreader_results.json`, `load_standard.md`; `huntkit/gendesign/back_rail.py`, `spreader.py`; `designs/pack_5200/analysis/frame_h1.md` (H1 changes one stand-off pad); `designs/pack_5200/analysis/weight_c_structural.md` (pad-seat backer result).

## Tasks
1. Reproduce today's governing numbers with the existing code: skin pressure 13.8 kPa against the 14 kPa limit at CG 190 mm; the spreader's bone rule and fatigue margin 1.09. State the mass of each layer from the ledger.
2. Research (cited, `docs/research/back_panel_structures.md`): how framed packs carry back-panel pressure (tensioned mesh, framesheets, foam on stays); skin-pressure comfort data already used in `back_rail.md`.
3. Evaluate at least these with the existing pressure and spreader models:
   - **(a)** spreader moved or extended so it also backs the rails (delete the carbon backer strips);
   - **(b)** rail backers in a lighter section (ribbed print, thinner carbon on a foam core, or the H1 stays reshaped to carry the rail directly);
   - **(c)** narrower or shorter rails where the pressure map shows low contact;
   - **(d)** a thinner spreader core or skins if (a) changes its span.
4. For each: mass, skin pressure in the rev C meat case at 15/19/23 in, bone rule, spreader strength and fatigue, clearance to the H1 frame and the hipbelt pad seat, build steps.
5. Recommend one, or state that today's design is already near the minimum, with the numbers.

## Deliverables
- `huntkit/gendesign/back_system2.py`, `tests/test_back_system2.py`
- `designs/pack_5200/analysis/back_system_integration.md`, `docs/research/back_panel_structures.md`
- `outputs/screens/20261111_BL005_1.png` (pressure maps, today vs recommended), `_2.png` (section drawings and mass)

## Acceptance
- Today's numbers are reproduced within 2 % before any variant is judged.
- No variant is recommended above 14 kPa skin pressure or below 1.0 on any spreader check.

## Out of scope
Editing `back_rail.py`, `spreader.py`, `build_geometry.py` or release files.
