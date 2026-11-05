# Spreader layout study (BP-06 rev C): change the frame so a thin sheet works

## Decision (owner, 2026-11-05)

**Production spreader: Sandwich v2** (`spreader.md`): 154 g (5.4 oz), about $188, strict HA-LS-1 rule, re-checked here
with the lumbar pan in the skin model (factored lean-torso air **8.4 mm**, walking 19.3 mm). The frame stays the
socket-free branch body it was checked on (`designs/pack_5200/print/frame/`). Build files: `designs/pack_5200/cut/spreader/`
(`spreader_v2_*`, `README.md`).

**Rejected for production:** d6L, 1.5 mm HDPE on 6 removable carbon cross stays (217 g, about $60, barrier rule + T8). It
stays in code (`huntkit/gendesign/spreader_layout.py`, layout `d6L_tubes`) as a documented alternative. Its socketed frame
files are written to `outputs/spreader_layout/print_d6L/` (scratch), not to the production print folder. The study below is
kept unchanged as the record.

Earlier owner direction 2026-11-05 (superseded by the decision above): support the sheet the way the leaders do (Mystery Ranch 0.060 in HDPE, Kifaru 1/16 in, Seek Outside removable cross stays). Sandwich v2 (`spreader.md`, 154 g, $188) is the fallback. Code: `huntkit/gendesign/spreader_layout.py` (model), `spreader_layout_report.py` (this record). Solver: `huntkit/fea/plate_grid.py` (`solve_von_karman`, new: large deflection, verified in `tests/test_plate_vk.py`). Frame FEA: `frame_production.verify_solid`, 2 mm voxels, all HA-LS-1 rev B cases. Tests: `tests/test_spreader_layout.py`. Research: `docs/research/spreader_research.md` (leaders), §9 below (HDPE data).

## Recommendation

**Best thin-sheet layout: d6L_tubes, (d+e) 6 removable carbon cross stays (14/12 at z 124, 165, 225; 12/10 at z 280, 385, 420), sheet raised 6 mm on the clip saddles, with a HDPE 1.5 mm (0.060 in) sheet.** It is the only layout tested that keeps a 1/16 in-class sheet off the back on every bone position, the lean torso included.

- Installed mass **217 g (7.7 oz)**: frame +16 g (printed sockets), sheet 102 g, 6 clips with saddles 25 g, 6 removable carbon cross stays 73 g. Today's part is 203 g; sandwich v2 is 154 g.
- Cost about **$60** against about $188 for the sandwich. The sheet is cut by hand or CNC from framesheet stock; the carbon stays are bought tube cut to length.
- Frame, all HA-LS-1 rev B cases, 2 mm: min SF **1.70** (hipbelt_off_abuse|15), fatigue **1.20**, creep-rupture 2.56 (today's body 1.69 / 1.19).
- Carbon cross stays under the factored bone: SF **1.12**, fatigue **1.01** (tube z165).
- No bottoming: walking air **11.7 mm** (≥ 3), factored **5.7 mm**, factored on the lean torso **0.8 mm** (≥ 0). Worst at grid 14.
- Skin pressure 13.0 kPa (≤ 14). Sheet under the factored meat alone: SF 1.02 on the 40 °C yield (99th percentile).
- Washable: pop 6 clips, lift the sheet out, pull the 6 stays out of their sockets, hose the frame. Nothing bonded.

**It is heavier than the sandwich, and it needs an owner call on the bone rule.**

1. Mass: 217 g against 154 g. The carbon stays (73 g) are what a thin sheet costs on a ventilated back. Two or four stays are not enough: the factored meat pressure alone yields 1.5 mm HDPE in a 100–160 mm bay and bulges it onto the back (table 2). It takes about 50 mm pitch.
2. Bone rule: under a 22 mm bone end the HDPE stress is local to the patch and the layout cannot remove it. On a rigid support grid from 40 to 136 mm pitch the walking stress in 1.5 mm HDPE only moves from 33 to 31 MPa (yield 20.3 MPa at 40 °C, 1e5-cycle fatigue 11.7 MPa); 2.4 mm HDPE is still at 26–24 MPa. So no thin sheet passes HA-LS-1's bone rule as written (no yield at 3.0× the static bone). The leaders ship HDPE that dents under a bone and recovers; nobody publishes a bone rule (research §1, load_standard.md §1).
3. The sandwich's lean-torso miss (−0.9 mm) was in the lumbar zone (x 24, z 124), where the back rests on the lumbar pan, not in the free gutter. With the pan in the skin model (`spreader_layout.skin_ref`) the sandwich clears by **8.4 mm** (factored, lean), 19.3 mm walking. It now passes every check, the strict bone rule included.

So the choice is the owner's: **sandwich v2, 154 g, $188, strict rule** or **HDPE on 6 carbon stays, 217 g, $60, washable, barrier rule.** On mass alone the sandwich wins. The thin-sheet files below are complete; the sandwich files in `designs/pack_5200/cut/spreader/spreader_v2_*` are kept.

The barrier rule used for the thin sheet:

1. The frame, sockets and carbon stays are the load path: full HA-LS-1 (SF ≥ 1 factored, fatigue ≥ 1).
2. The sheet must not bottom (walking ≥ 3 mm, factored ≥ 0, factored lean torso ≥ 0), must keep skin pressure ≤ 14 kPa, must not yield under the factored meat pressure alone (99th percentile, as the frame FEA), and must not puncture: local strain at the bone-patch rim (Neuber, elastic-perfectly plastic, 40 °C yield) ≤ half the elongation at break.
3. Local yielding under a bone end is allowed. **Physical test T8 (new, before release):** 400 N through a 22 mm dowel at the worst bay centre and at the IM1 notch root, 10 min hold, then 10,000 cycles 0 → 213 N. Pass: no crack or craze line, residual dent ≤ 2 mm after 1 h, the dowel never reaches the rail plane.

## 1. Why the layout cannot fix the bone stress (pitch study)

Bone end at the centre of a square bay of a sheet on a rigid grid of line supports, held in-plane at the edges, von Kármán solve (`spreader_layout.pitch_study`).

| sheet | pitch mm | walking MPa | factored MPa | factored dimple mm |
|---|---:|---:|---:|---:|
| HDPE 1.5 | 40 | 32.9 | 47.2 | 3.3 |
| HDPE 1.5 | 64 | 32.2 | 45.4 | 5.3 |
| HDPE 1.5 | 96 | 31.3 | 44.4 | 7.4 |
| HDPE 1.5 | 136 | 30.9 | 44.0 | 9.5 |
| HDPE 2.4 | 40 | 24.0 | 38.5 | 2.0 |
| HDPE 2.4 | 64 | 26.9 | 40.3 | 3.8 |
| HDPE 2.4 | 96 | 26.9 | 39.5 | 5.7 |
| HDPE 2.4 | 136 | 26.4 | 38.7 | 7.5 |

Linear Kirchhoff plate theory over-predicts these by 2–6× at the wide pitches (membrane action carries the bone once the dimple is a few sheet thicknesses deep). That is why the old linear check said HDPE needs ribs every few cm. The large-deflection solve says the opposite: pitch matters for deflection, not stress.

## 2. Layout options (HDPE 1.5 mm, real frame, named + bay-centre bone positions)

Bone positions: centre, top and bottom edges, top and bottom corners, IM1 / IM2 notch roots, US2 corner relief, between the rails, over the rail, at a clip, and the four points of each layout furthest from any support (bay centres). Walking 1.6 g, factored 2.0 g × 1.5 (HA-LS-1 rev B C5).

| option | frame +g | sheet g | clips + tubes g | total g | frame SF | frame fat | rib SF | rib fat | air walk | air fact | air lean | sheet MPa walk / fact | skin kPa | cost $ | pass (barrier rule) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| (e) edges only | +57 | 102 | 11 | **170** | 1.91 | 1.26 | 1.20 | 0.59 | 1.4 | -7.0 | -11.9 | 117 / 176 | 12.9 | 26 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (a) 2 cross-ribs | +84 | 102 | 11 | **197** | 1.95 | 1.30 | 1.28 | 0.65 | 1.6 | -6.4 | -11.3 | 115 / 169 | 12.9 | 28 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (a) 3 cross-ribs | +100 | 102 | 11 | **213** | 1.97 | 1.31 | 1.23 | 0.54 | -0.1 | -8.1 | -13.0 | 112 / 161 | 12.9 | 30 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (a) 4 cross-ribs | +116 | 102 | 11 | **229** | 1.99 | 1.37 | 1.28 | 0.65 | 1.9 | -6.4 | -11.3 | 77 / 126 | 12.9 | 31 | no: ribs_fatigue, no_bottoming, no_bottoming_lean |
| (b) X ribs | +128 | 102 | 11 | **242** | 2.01 | 1.32 | 1.32 | 0.66 | 1.3 | -6.1 | -11.0 | 112 / 166 | 12.9 | 32 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (c) coarse grid | +122 | 102 | 11 | **235** | 2.00 | 1.35 | 1.33 | 0.68 | 1.7 | -6.2 | -11.1 | 92 / 145 | 12.9 | 32 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (d) 2 carbon stays | +61 | 102 | 32 | **195** | 1.92 | 1.26 | 1.06 | 0.67 | 2.1 | -6.2 | -11.1 | 116 / 167 | 12.9 | 38 | no: sheet_meat_only, ribs_fatigue, no_bottoming, no_bottoming_lean |
| (d+e) 4 carbon stays | +32 | 102 | 56 | **190** | 1.81 | 1.22 | 1.07 | 0.91 | 7.6 | 1.6 | -3.3 | 110 / 162 | 12.9 | 49 | no: sheet_meat_only, ribs_fatigue, no_bottoming_lean |
| (d+e) 6 carbon stays | +36 | 102 | 78 | **216** | 1.82 | 1.22 | 1.24 | 1.10 | 7.6 | 1.6 | -3.3 | 70 / 109 | 12.9 | 62 | no: no_bottoming_lean |
| (d+e) 6 carbon stays, no lands | +13 | 102 | 78 | **193** | 1.70 | 1.20 | 1.24 | 1.10 | 7.9 | 2.1 | -2.8 | 68 / 95 | 12.9 | 60 | no: no_bottoming_lean |
| no layout change | +0 | 102 | 11 | **113** | 1.69 | 1.19 | — | — | -15.5 | -23.9 | -23.9 | 129 / 169 | 12.9 | 21 | no: sheet_meat_only, no_bottoming, no_bottoming_lean |
| (d+e) 6 carbon stays, sheet +6 mm | +16 | 102 | 98 | **217** | 1.70 | 1.20 | 1.29 | 1.17 | 12.2 | 6.5 | 1.6 | 106 / 178 | 13.0 | 60 | yes |

Frame SF and fatigue are the whole-frame minimum over all HA-LS-1 rev B cases and the three torsos (2 mm). Rib SF is the cross members under the factored bone + meat (PAHT 0.8 knockdown; carbon tube hot/wet and impact knockdowns on compression). Airs are the minimum gap from the lowest part (sheet, rib bottom or tube) to the skin. Strict-rule sheet SFs are in the JSON (`sf_sheet_yield`, `sf_sheet_fatigue`); every HDPE row is below 1 there. This table is the named + bay-centre run (15 positions); the recommendation quotes the chosen layout's 33-position run (named + bays + a 48 mm grid), which is a little harsher.

What the families do:

- **Printed PAHT ribs are too soft.** A 7 × 14 mm rib in hot/wet PAHT (E 2.3 GPa) spanning branch to branch bends 9–11 mm under the factored bone. Its depth plus that bend is what eats the air to the skin. Deeper ribs hit the torso bulge on the lean case; wider ribs cost ~50 g each.
- **X ribs** span longer and shed the bone into the branches at mid-height, where the branches are softest.
- **A coarse grid** adds a spine rib in the gutter: it blocks the air path and adds mass for little deflection.
- **Carbon cross stays** are far stiffer per gram than printed ribs (E 75 GPa against 2.3 GPa hot/wet). A 12/10 mm roll-wrapped stay weighs about 11 g and bends 2–4 mm under the factored bone. This is the Seek Outside answer, in carbon instead of 7075. Two or four stays leave 100–160 mm bays that the meat pressure yields; six at about 50 mm pitch do not.
- **12 mm stays need 6 mm more room on a leaning torso.** With the sheet on the stay crowns, the stays' underside bottoms on the lean case by about 3 mm in the gutter. Raising the sheet 6 mm on the clip saddles (d6L) clears it. Branch and bar lands then do not touch the sheet and are left off.
- **Edges only (e)** is light, but the sheet spans the 160 mm bay between the branches and bottoms on the lean torso.

## 3. Frame re-check, chosen layout vs today (2 mm, worst torso)

| case | today | chosen |
|---|---:|---:|
| static_carry | 3.18 | 3.20 |
| drop_2p5g | 2.12 | 2.13 |
| side_hill_torsion | 2.88 | 2.91 |
| single_stay_setdown | 3.42 | 3.44 |
| meat_straps | 2.59 | 2.59 |
| tall_load | 2.94 | 2.92 |
| overload_haul | 3.64 | 3.63 |
| tall_load_posts | 2.89 | 2.88 |
| hipbelt_off_abuse | 1.69 | 1.70 |
| fatigue | 1.19 | 1.20 |
| creep-rupture | 2.55 | 2.56 |
| torsion vs tube frame | 1.51 | 1.52 |
| printed body g (2 mm raster) | 823 | 840 |

The ribs, lands and sockets are not on the main load paths of the frame cases. They change the case SFs very little and add a little torsional stiffness.

## 4. Sheet material on the chosen layout

| sheet | sheet g | MPa walk / fact (FI for G10) | strict SF yield / fatigue | air lean mm | Neuber strain | passes barrier rule | passes strict rule |
|---|---:|---:|---:|---:|---:|---|---|
| HDPE 1.5 mm (0.060 in) | 102 | 112.73 / 183.82 | 0.11 / 0.10 | 0.8 | 1.515 | yes | **no** |
| HDPE 1.0 mm (0.040 in) | 68 | 160.37 / 239.51 | 0.08 / 0.07 | 1.6 | 2.571 | **no** | **no** |
| UHMWPE 1.5 mm (1/16 in) | 100 | 100.66 / 163.52 | 0.10 / 0.09 | 1.6 | 2.366 | **no** | **no** |
| G10-class glass/epoxy 1.0 mm | 128 | 5.47 / 9.05 | 0.11 / 0.09 | 2.0 | — | **no** | **no** |

The chosen HDPE row was run on the named, bay-centre and a 48 mm grid of bone positions (33 in all). G10 is a brittle laminate, so it is held to the strict first-ply rule, and a 1.0 mm sheet fails it by a wide margin under the bone. It also weighs more than 1.5 mm HDPE. UHMWPE is softer and weaker than HDPE for the same mass. 1.0 mm HDPE saves grams and dents deeper.

## 5. Rib-layer topology optimisation

`spreader_layout.rib_simp`: a PAHT rib layer 14 mm deep under the HDPE sheet, 10 % volume (105 g if printed as a smeared web), SIMP p = 3 with a 10 mm filter, minimum compliance under the factored meat pressure plus a 48 mm grid of factored bone ends, on the real crowns, branch lands and bar. The material goes into the bottom bay below the branches (z 130–200), where the meat pressure peaks and nothing else supports the sheet, with thin ties up to the branches. It is not symmetric (no symmetry constraint, 30 iterations), so it is used to place members, not printed: the chosen layout puts two of its six stays there (z 124, 165), both at 14/12 mm. A printed web at that volume is heavier than carbon stays for the same stiffness.

## 6. Airflow, printing, cost, washing

| option | gutter crossings | worst blockage of the 20 mm air gap | rib length on tree supports mm |
|---|---:|---:|---:|
| (e) edges only | 2 | 70 % | 379 |
| (a) 2 cross-ribs | 4 | 70 % | 703 |
| (a) 3 cross-ribs | 5 | 70 % | 864 |
| (a) 4 cross-ribs | 6 | 70 % | 1063 |
| (b) X ribs | 6 | 70 % | 1182 |
| (c) coarse grid | 5 | 70 % | 1165 |
| (d) 2 carbon stays | 4 | 70 % | 379 |
| (d+e) 4 carbon stays | 4 | 60 % | 0 |
| (d+e) 6 carbon stays | 6 | 60 % | 0 |
| (d+e) 6 carbon stays, no lands | 6 | 60 % | 0 |
| no layout change | 0 | 0 % | 0 |
| (d+e) 6 carbon stays, sheet +6 mm | 6 | 70 % | 0 |

- Air: the air path stays the gutter between the rails under the open mesh. Horizontal members across the gutter choke the chimney flow up the back. Round 12 mm tubes block less than flat 14 mm ribs and leave the gutter fully open when they are out. The sheet stays solid: it is the bag-side blood and sweat barrier.
- Printing (H2S, wearer face down, split at z 234): the sockets are open-top cups (snap-in, about 220° wrap) grown on the branches and stays, printed with the frame; their undersides take tree supports like the existing branches (README: only where the slicer flags bridges > 15 mm). The segment footprints do not change. Printed ribs and lands (options a–c, e) would add 2–3 h of print and long supported spans.
- Cost: sheet stock $1, cutting $8, extra filament $1, carbon tube $37, clips $12: about **$60**.
- Washing: the sheet lifts out after the 6 clips; the carbon stays pull out of their sockets; the frame hoses clean.

## 7. Mass budget, before and after

| item | today (2.0 mm QI) | sandwich v2 | thin sheet on this layout |
|---|---:|---:|---:|
| sheet | 193 | 99 | 102 |
| fasteners (M4 / clips, pucks, doublers, seal) | 10 | 34 | 25 |
| bonded edge tubes / removable carbon stays | 0 | 21 | 73 |
| added frame (sockets) | 0 | 0 | 16 |
| **total** | **203** | **154** | **217** |

Mass reductions: 1.0 mm HDPE saves 34 g but fails the barrier rule here (table 4). 10/8 mm stays would save about 20 g but drop the stay SF below 1 under a bone on mid-span. Trimming the sheet's overhang outboard of the stay crowns saves about 6 g.

## 8. Files

- Frame print files with the six stay sockets (alternative only; regenerate with `write_print_files`, written to `outputs/spreader_layout/print_d6L/`): `genframe_assembled.stl`, `genframe_lower_flat.stl/.3mf`, `genframe_upper_flat.stl/.3mf`. The production files in `designs/pack_5200/print/frame/` have no sockets
- Sheet cut file (DXF, mm; CUT, MARK = support lines, TEXT): `designs/pack_5200/cut/spreader/spreader_v3_hdpe_cut.dxf`
- Sheet drawing, 1:1 A3: `designs/pack_5200/cut/spreader/spreader_v3_drawing.pdf`
- viz3d back-system mesh (sheet + carbon stays, alternative): `outputs/spreader_layout/print_d6L/genframe_barrier.stl`. The production `genframe_barrier.stl` is the sandwich
- Results: `designs/pack_5200/analysis/spreader_layout_results.json`

## 9. Sources added

- HDPE fatigue: Djebli et al., *Uniaxial Fatigue of HDPE-100 Pipe*, ETASR 4(2):600–604 (2014), R = 0, 2 Hz, Basquin Smax = 32.46 N^−0.067 MPa (Ps 50 %) → 15.0 MPa at 1e5 cycles ([ETASR](https://www.etasr.com/index.php/ETASR/article/view/422)). Fetched.
- HDPE yield vs temperature: PE-100 yield falls about linearly from 32 to 9 MPa between −10 and 70 °C ([KFUPM](https://pure.kfupm.edu.sa/en/publications/effect-of-temperature-on-tensile-properties-of-hdpe-pipe-material/)) *(reported, search summary)*; the 0.78 factor at 40 °C is interpolated from it. Amjadi & Fatemi, Polymers 12:1857 (2020) ([PMC7564066](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7564066/)) reports the same linear trend.
- Leaders' sheets and cross stays: `docs/research/spreader_research.md` §1 and §8 (Seek Outside fetched).

## Screenshots

- `outputs/screens/20261105_spreaderlayout_1.png`
- `outputs/screens/20261105_spreaderlayout_2.png`
- `outputs/screens/20261105_spreaderlayout_3.png`
- `outputs/screens/20261105_spreaderlayout_4.png`
- `outputs/screens/20261105_spreaderlayout_5.png`
- `outputs/screens/20261105_spreaderlayout_6.png`
- `outputs/screens/20261105_spreaderlayout_7.png`
- `outputs/screens/20261105_spreaderlayout_8.png`

## Assumptions

- ASSUMPTION: bone end 20 % of 68 kg on a 22 mm patch (HA-LS-1), part of the meat, not added to it.
- ASSUMPTION: a thin thermoplastic barrier may yield locally under a bone end (barrier rule above); the owner decides, and T8 checks it.
- ASSUMPTION: HDPE yield and fatigue at 40 °C = 0.78 × room temperature; UHMWPE fatigue scales with its yield.
- ASSUMPTION: Neuber's rule on an elastic-perfectly plastic curve for the local strain at the patch rim.
- ASSUMPTION: the sheet is held in-plane only at the 6 clip stations; it slides freely on lands, ribs and tubes.
- ASSUMPTION: below the upper lumbar strut line the back rests on the lumbar pan (skin reference = strut wearer face), blended to the free gutter skin over 60 mm of height.
- ASSUMPTION: the meat-only sheet check uses the 99th-percentile stress, as the frame FEA does, so single contact-edge elements at the clip saddles and stay ends do not govern.
- ASSUMPTION: printed ribs and lands top out 0.3 mm below the sheet plane (print tolerance); the sheet plane is the stay-crown plane, y = sleeve axis + 13.9 mm.
- ASSUMPTION: rib, land and branch stiffness at PAHT hot/wet (0.6 E); ribs fused where they cross a branch.
- ASSUMPTION: carbon stays are roll-wrapped 14/12 and 12/10 mm (record E 75 GPa, compression 450 MPa × 0.8 × 0.65), pinned in their sockets (no end moment).
- ASSUMPTION: the bone reaction reaches the stays by the lever rule between the stays (skin-pressure input).
- ASSUMPTION: the air gap in the gutter is 20 mm at rest for the blockage estimate.
- ASSUMPTION: sheet stock bought at 2× the part mass, $6/kg (record), $8 to CNC-cut one part; clips $12.
- Torso radius 230 mm (150 mm lean), soft tissue 60 kPa over 25 mm, 3 mm spacer mesh: as `spreader.md`.
