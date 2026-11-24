# BL-063 Iteration 1, looks track: design-language brief and A/B/C colour concepts

**Agent:** pack-designer · **Size:** M · **Depends on:** BL-058 (rev 3 frame), camo release rev 3 · **Date:** 2026-11-24

Goal (owner rubric `docs/RUBRIC.md`, axis 3 "looks better"): research what makes premium mountain-hunting packs read
as high-end, render CORRIE F rev 3 as it is today on the figure, write a design-language brief, and offer 2 to 3
visual concepts that cost about 0 g or save mass and keep every structural interface. Parallel tracks own frame mass
and system mass; this ticket changes **no geometry and no pattern outline**.

## Deliverables

| File | What |
|---|---|
| `docs/research/design_language_iter1.md` | cited research, principles P1 to P8 (sources S1 to S14) |
| `designs/pack_5200/iter1/looks/design_language.md` | the brief: silhouette, line language, seam rules, colour blocking, hardware / tails, mark, frame surface rules; critique of today; concepts A/B/C with changes, mass, risks, scores, recommendation |
| `designs/pack_5200/iter1/looks/looks_render.py` | renders today and the concepts on the 6 ft hunter (paint-over of the rev 3 picture model by real pattern piece), contact and comparison sheets |
| `designs/pack_5200/iter1/looks/concepts_mass.py` (+ `concepts_mass.json`) | mass delta per concept from the release cut list and the material records |
| `tests/test_looks_iter1.py` | mass deltas match the records; concept C keeps load pieces on 330D; no concept adds mass |
| `outputs/screens/20261124_iter1_looks_<n>.png` | sheets: 1 today loaded, 2 today day load, 3 A, 4 B, 5 C, 6 comparison |
| `outputs/screens/20261124_iter1_looks_<concept>_<state>_<view>.png` | the single renders behind the sheets |

Status, results and the recommendation: see `designs/pack_5200/iter1/looks/design_language.md` section 9 and the
ticket report. Not done here (by scope): pattern edits, print-file edits, frame surface changes, the back-panel width.

## How to regenerate

```
export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets
python designs/pack_5200/iter1/looks/looks_render.py --concept base --states sixday,day
for c in A B C; do python designs/pack_5200/iter1/looks/looks_render.py --concept $c; done
python designs/pack_5200/iter1/looks/looks_render.py --sheets
python designs/pack_5200/iter1/looks/concepts_mass.py
python -m pytest -q tests/test_looks_iter1.py
```
About 3 min per scene build and 2.5 to 3 min per 1600 x 1200 frame (48 samples) on the 4 shared cores.
