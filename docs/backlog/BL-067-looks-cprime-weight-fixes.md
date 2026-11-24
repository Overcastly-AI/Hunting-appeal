# BL-067 Looks concept C′ and iteration-1 weight fixes (review 7: M5-M8, m1, m2, m6, m7, m9)

**Agent:** pack-designer · **Size:** M · **Depends on:** review 7 (`designs/pack_5200/analysis/review_20261124_seventh.md`),
DECISIONS 2026-11-24 (C → C′; weights on the 350 g/m² mesh), BL-063, BL-062, BL-064 · **Date:** 2026-11-24

Not touched (another agent's work): `huntkit/gendesign/frame_iter1.py`, `huntkit/fea/*`, H1 frame files.

## Deliverables

| File | What |
|---|---|
| `designs/pack_5200/iter1/looks/looks_render.py` | concept `Cp` (C′): paint + two geometry proposals in the cloth pass (own cache), stowed tails, olive mesh, tonal hardware, rear lid locks off, roll hem drawn as built (B-07 330D at the core, B-06 ripstop outside); `bagoff` view; `--cp-checks`; `sheets_bl067` |
| `designs/pack_5200/iter1/looks/concepts_mass.py` / `.json` | `ledger_concepts()`: every concept on the ledger scenarios (base P / base A / as hunted P / A); C′ geometry masses (taper, RT re-cut, lid locks); collar volume loss |
| `designs/pack_5200/iter1/looks/cp_checks.json` | roll-clip path re-run (3 states) on C′, RT cut by the strap_tails rule, W1 / W2 paths |
| `designs/pack_5200/iter1/looks/design_language.md` | m6 contradictions fixed (rules 5.1, 5.2, 6.1; stale buckling line); new section 10 (C′, masses, checks, pattern follow-ups P1-P3, score) |
| `designs/pack_5200/mfg_corrie_f_rev3.py` | m9: RT / RTM rated on ASSUMPTION RT-LOAD 225 N, gate RT-PULL 338 N |
| `designs/pack_5200/iter1/system/iter1_weight.py` / `.md` / `.json` | M8 mesh deltas from 350 g/m²; BL-064 records wired (Ti USD 4.25, Dyneema 12 000 N, slider_8 on G-3, mesh 4.0 mm); MESH-320 / MESH-ROLL / TI-TG-COST settled; m1 KUIU arithmetic |
| `docs/research/weight_iter1.md` | m1: 1358 g, suspension 826-1044 g, no "ours lighter" |
| `docs/RUBRIC.md` | m2: baseline line 4038.1 g proven now / 3450.9 g after tests |
| `designs/pack_5200/analysis/weight_rollup_v2.md` / `.json`, `docs/screens/20261112_rollup_1.png` | m2: re-run (`--write`) |
| `tests/test_iter1_weight.py`, `tests/test_looks_iter1.py`, `tests/test_bl040_review_fixes.py` | new / adjusted tests |
| `outputs/screens/20261124_bl067_{1..4}.png` | 1 today vs C vs C′; 2 C′ 6-day 4 views; 3 C′ day load 4 views; 4 bag on / bag off |

## Result

**C′** (camo on the lid crown B-29a only, A's olive trim, no plinth, B-06 solid; plus level W1 / W2, roll tapered to
384 mm flattened, 2 lid locks instead of 4, tonal hardware, olive mesh, stowed tails):

| | base P | base A | as hunted P | as hunted A |
|---|---:|---:|---:|---:|
| C (review 7, reproduced) | +3.0 | +15.2 | -5.2 | +7.0 |
| C′ colour / print | 0.0 | 0.0 | -5.0 | -5.0 |
| C′ + geometry proposals | -15.4 | -12.9 | -34.4 | -31.9 |

- Strong: no load piece changes fabric; `--check` 32 points, min SF 1.36 (B-25), no holds. RT / RTM now rated: SF 2.28,
  buckle 2.0, proof RT-PULL 338 N (ASSUMPTION RT-LOAD).
- Roll-clip path re-run: longer on the tapered roll (day / 6-day / full 261 / 291 / 491 mm vs 202 / 222 / 424): RT cut
  565 → 635 mm with the RTM tab where it is, or raise the tab ~60-70 mm. Muzzle-tab stand-off 14-15 mm (was 33-37).
- Collar volume -0.8 L (85 L ± 3 holds); top opening -27 % perimeter.
- Looks (my pass/fail): **3/5 as drawn** (2, 3, 4 pass; 1 and 5 fail on D-4 overhang and frame), **2/5** with the
  build-1 matte black hardware and grey mesh.

**Weights** (`iter1_weight.py`, belt M, crown kit M): proven now 4038.1 g, after tests 3450.9 g (unchanged).
Option A **-70.2 g** (was -82.3; N1 -36.1, N2 -3.2 on the 350 g/m² basis), cost -7.13 USD (Ti now USD 4.25 each);
B -127.1 g base / -36.5 g as hunted; C -233.0 / -83.6 (G-3 now -20.1 g with slider_8 against G-1's 15 g cord-pull
sliders, not -21 against 19 g). Mesh booking correction (not a lever) -12.2 g once the bought mesh is weighed.
KUIU suspension 826-1044 g against our 954 g: no "ours lighter" claim.

## Pattern / test follow-ups (for other agents)

See `design_language.md` 10.4: **P1 W-LEVEL** (geometry.yaml anchors, kw_heights, W tails, tripod low hold, mirror
lash points for structural), **P2 ROLL-TAPER** (B-06 / B-06f wedge 70.4 mm per edge at the mouth, B-07 -281.8 mm,
B-07s, RT notch, RT cut 635 or RTM tab up, muzzle stand-off, LOADOUT), **P3 LID-LOCK** (B-28 rear end box-X'd on B-28t,
strap_tails B-28). manufacturing-engineer: RT-PULL into the register / kit and the release README on the next regen.
materials-engineer: a stocked, brightener-free olive power mesh (MESH-COL).

## How to regenerate

```
export HUNTKIT_BPY=$SCRATCH/bpyenv/bin/python HUNTKIT_HUMAN_ASSETS=$SCRATCH/human_assets
python designs/pack_5200/iter1/looks/looks_render.py --concept Cp --states sixday --views back,q34,side,front,bagoff
python designs/pack_5200/iter1/looks/looks_render.py --concept Cp --states day
python designs/pack_5200/iter1/looks/looks_render.py --cp-checks --sheets
python designs/pack_5200/iter1/looks/concepts_mass.py
python designs/pack_5200/iter1/system/iter1_weight.py
python designs/pack_5200/weight_rollup_v2.py --write
```
C′ cloth solves (3 states) about 4-10 min each; 9 frames at 1600 × 1200 / 48 samples about 3.3 min each.
