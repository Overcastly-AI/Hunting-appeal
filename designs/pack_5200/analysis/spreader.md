# Spreader v2 (BP-06 rev B)

Supersedes the spreader rows in `back_comfort.md`. Code: `huntkit/gendesign/spreader.py` (model), `huntkit/gendesign/spreader_report.py` (this record), solver `huntkit/fea/plate_grid.py`. Research: `docs/research/spreader_research.md`. Tests: `tests/test_spreader.py`.

## Recommendation

**Sandwich: twill / 6 mm ROHACELL 110, notch doublers**, 154 g (5.4 oz) as installed (sheet 99 g, edge tubes 21 g, clips, pucks, doublers and edge seal 34 g). The current part is 203 g with its M4 hardware, so this saves **49 g**. The current part also fails the checks below.

- First-ply SF (Tsai-Wu, factored 3.0 g, hot/wet 0.8, impact 0.65): **1.21**, at US2 corner relief
- Fatigue SF (FI ≤ 0.5 at the 1.6 g walking peak): **1.04**
- Sandwich local SF (core shear, bone crush, crown crush, puck crush, wrinkling): **1.06**. Core shear 1.17, bone crush 2.28, crown crush 1.89, puck crush 10.69, wrinkling 1.18
- Air to the skin: walking minimum **10.1 mm** (limit 3 mm of mesh). Factored minimum **4.0 mm** (limit 0). Lean-torso sensitivity (R 150 mm) -0.9 mm
- Peak skin pressure, walking, worst bone: **13.0 kPa** (limit 14). Meat only 9.5 kPa
- Max factored deflection 3.8 mm. Bone at the centre, walking: 2.0 mm
- Clip lift-off, factored: 2 N, clip SF 66.3
- Cost per part about **$188** (table below)

**The ≤ 100 g target is not met.** The lightest option that passes every check is 154 g. No option in the table comes in under 126 g. Every option under 150 g fails at least one check. Reaching 100 g needs an architecture change, not a material swap (see the next steps in `docs/RESUME.md`). The governing cases are a bone end at a notch root and on the free top and bottom edges. The bottom bay (z 112–165) also has no branch under it.


## 1. The current part, checked properly

Current part: 208 × 300 × 2.0 mm QI, z 130–430, square corners, 4 × M4 holes at IM1 and IM2. It rests on the real branch frame: stay crowns, the inboard branches and the z 330 bar, all as unilateral contacts with the gaps taken from the frame's distance field. M4 bolts go into the bar.

| check | result | requirement | |
|---|---:|---:|---|
| first-ply SF, factored | 0.66 at near M4 hole (IM1) | ≥ 1.0 | **fail** |
| fatigue SF, walking | 0.38 | ≥ 1.0 | **fail** |
| air to skin, walking | -14.7 mm | ≥ 3 | **fail** |
| air to skin, factored | -24.1 mm at bottom edge | ≥ 0 | **fail (bottoms)** |
| peak skin pressure | 13.2 kPa at over the rail, mid | ≤ 14 | ok |
| M4 bearing, factored 253 N | SF 14.2 | ≥ 1.0 | ok |
| M4 shear-out | SF 13.6 | ≥ 1.0 | ok |
| M4 edge distance e/d | 1.78 | ≥ 3.0 (CMH-17 practice) | **fail** |
| hole at x 96, z 190 lands on frame | 11.2 mm of air below | ≤ 2 mm | **fail: nothing to bolt to** |
| hole at x 96, z 330 lands on frame | 6.8 mm of air below | ≤ 2 mm | **fail: nothing to bolt to** |

Why the old record said it passed: `back_comfort.md` treated the sheet as simply supported on all four edges. It also compared the 7.8 mm deflection with the 10 mm rail and nothing else. On the real frame the 208 mm sheet only reaches the stay crowns (x 101–129) by 3 mm. The bottom 35 mm overhangs the window with nothing under it (the branches start at z 165), and that edge governs. The rails are not the clearance either. The sheet sits on the bag face of 28 mm stays, so the air to the skin is the stay depth plus the aged rail, less the rail indentation and the torso bulging into the 130 mm gutter.

Load model (HA-LS-1 rev B, C5): the overturning meat pressure is triangular from z 60 to z 330. The cinch preload is 6 × 150 N spread over z 60–560. A bone end, 20 % of 68 kg on a 22 mm patch, is tested at every named position and on a 24 mm grid. Walking is 1.6 g. Factored is 2.0 g × 1.5. ASSUMPTION: the bone is part of the meat, so its force comes out of the overturning resultant. The v1 study added it on top.

Skin model: the stay is a hot/wet PAHT beam on the rail. The rail is aged L200 XLPE (cited curve, 12 % set) over a 1 mm twill backer, with soft tissue in series (60 kPa, 25 mm column, ASSUMPTION; 20 kPa is the soft-tissue sensitivity). Clearance is the plane of the sheet less its deflection, measured to the skin, which includes the rail indentation and the torso bulge into the gutter (R 230 mm, ASSUMPTION; 150 mm lean sensitivity).

## 2. Options (v2 outline, real supports, bone grid 48 mm + named positions)

| key | option | mass g | FPF SF | fatigue SF | sandwich SF | air walk mm | air fact mm | skin kPa | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| sw71c5 | Sandwich: 200 g twill skins on 5 mm ROHACELL 71 | 126 | 0.76 | 0.68 | 0.67 | 9.8 | 3.4 | 13.0 | no: fpf, fatigue, sandwich_local |
| sw110c3d | Sandwich: twill / 3 mm ROHACELL 110, notch doublers | 128 | 0.87 | 0.76 | 0.57 | 9.0 | 2.0 | 13.1 | no: fpf, fatigue, sandwich_local |
| sw110c4d | Sandwich: twill / 4 mm ROHACELL 110, notch doublers | 136 | 1.06 | 0.93 | 0.87 | 9.5 | 3.0 | 13.1 | no: fatigue, sandwich_local |
| sw110c5 | Sandwich: 200 g twill skins on 5 mm ROHACELL 110 | 139 | 0.76 | 0.68 | 1.10 | 9.9 | 3.6 | 13.0 | no: fpf, fatigue |
| sw110c5d | Sandwich: twill / 5 mm ROHACELL 110, notch doublers | 145 | 1.23 | 1.08 | 0.92 | 9.9 | 3.7 | 13.0 | no: sandwich_local |
| tw10 | Twill carbon 1.0 mm (4 x 200 g 2x2 twill) | 151 | 0.23 | 0.20 | — | -9.3 | -38.4 | 13.2 | no: fpf, fatigue, no_bottoming |
| sw110c6d | Sandwich: twill / 6 mm ROHACELL 110, notch doublers | 154 | 1.38 | 1.21 | 1.17 | 10.3 | 4.2 | 13.0 | yes |
| qi10 | QI carbon 1.0 mm | 157 | 0.26 | 0.23 | — | -7.8 | -31.9 | 13.2 | no: fpf, fatigue, no_bottoming |
| b10 | Span-biased carbon 1.0 mm [0/90/0/0]s | 157 | 0.31 | 0.27 | — | -7.7 | -33.5 | 13.2 | no: fpf, fatigue, no_bottoming |
| bd10 | QI carbon 1.0 mm + 3 span beads (5 mm) | 161 | 0.27 | 0.23 | — | 6.4 | -3.1 | 13.1 | no: fpf, fatigue, no_bottoming |
| pf15 | QI carbon 1.5 mm, SIMP cut-outs <= 20 mm | 202 | 0.37 | 0.34 | — | 6.6 | -2.5 | 13.2 | no: fpf, fatigue, no_bottoming |
| qi15 | QI carbon 1.5 mm | 214 | 0.61 | 0.52 | — | 6.6 | -2.4 | 13.2 | no: fpf, fatigue, no_bottoming |
| qi20 | QI carbon 2.0 mm (current material) | 270 | 0.88 | 0.78 | — | 8.8 | 1.7 | 13.1 | no: fpf, fatigue |
| g20 | Glass (G10-class) QI 2.0 mm | 302 | 0.25 | 0.21 | — | 6.0 | -3.5 | 13.2 | no: fpf, fatigue, no_bottoming |
| g30 | Glass (G10-class) QI 3.0 mm | 431 | 0.40 | 0.36 | — | 9.0 | 2.1 | 13.1 | no: fpf, fatigue |

Notes on the families:

- **Thinner QI with beads.** Beads stiffen the span direction only. The bone at a notch root and on the free edges is still a 1 mm laminate. Beads also need a matched press tool.
- **SIMP cut-outs.** Holes come from a bending SIMP density on the real supports. They sit on a 30 mm hex and are capped at 20 mm, so a 22 mm bone end cannot pass. A Kt of 1.8 applies at each hole edge. Mass drops, and the strength drops at the same places. The holes also drain meat juice onto the back gap (research §2).
- **Biased layup.** The span is not one-way: the bar, the branches and the notches load the sheet both ways. A 0-heavy stack loses on the 90 and shear plies at the notch roots.
- **Sandwich.** Stiffness comes almost free. The limits are local: core shear and crush under the bone and at the supports, and the skins at the notch roots. ROHACELL 71 fails bone crush and core shear. ROHACELL 110 with a 45° doubler ply around the notches passes.
- **G10.** Cheap, but heavy for the same stiffness, and E-glass has lower compression strength after the impact knockdown.

Mesh check: the chosen part was re-run at the named positions on a 2 mm grid. The results are in the next table. A notch root on a 4 mm grid is close to square, so the 2 mm FI is the number to trust there.

| grid | FPF SF | fatigue SF | sandwich SF | air fact mm |
|---|---:|---:|---:|---:|
| 4 mm | 1.38 | 1.21 | 1.17 | 4.0 |
| 2 mm | 1.21 | 1.04 | 1.06 | 5.0 |

## 3. The part, detailed for manufacture

- Outline 242 × 318 mm, z 112–430. The long edges land on the stay crowns, which is what the 208 mm sheet did not do. Corners R20 at the top and R8 at the bottom.
- Fairlead notches at the cleat stations in `bag_attachment.md` that fall inside the sheet: US2 z 142, IM1 z 190, IM2 z 330. Each is 30 mm tall to a root at x ±92, with R6 root corners, which leaves 6 mm of air round the cheek (tested). The hinge, US1 and IM3 cleats are outside the sheet.
- 6 removable MJF PA12 snap clips over the stays at z 166, 260, 400. The inboard post passes through a 4 × 16 mm slot, and the outboard post passes outside the sheet edge. To wash, pop six clips and lift the sheet out. No tools, and no bonded joint to the frame. The bottom tab sits on bonded PAHT stand-off pads at z 119, where the stay is thinner.
- Bonded pucks on the wearer face where the sheet crosses a branch or the bar (11). Each is cut to the local gap less 0.3 mm, so the sheet bears on the branch straight away. Heights are on the drawing.
- Edge sealing: two brushed epoxy coats on every cut PMI edge. ROHACELL is closed-cell, so this seals out grime and blood and protects against abrasion. It is not a structural closure.
- Ventilation: the sheet stays solid on purpose. It is the blood and sweat barrier on the bag side, and the air path is the 130 mm gutter between the rails under the open mesh (42 % of the lower back). Nothing on the sheet touches the wearer.
- A 1 mm EVA rub strip, 8 mm wide, runs on the wearer face along each stay crown line. It stops carbon-on-PAHT chafe and spreads the crown line load.

Files:

- water-jet / CNC cut file (DXF, mm, layers CUT / MARK / TEXT): `designs/pack_5200/cut/spreader/spreader_v2_cut.dxf`
- clip profile (DXF, extrude 10 mm): `designs/pack_5200/cut/spreader/spreader_v2_clip.dxf`
- dimensioned drawing, 1:1 on A3 (PDF): `designs/pack_5200/cut/spreader/spreader_v2_drawing.pdf`
- viz3d mesh (STL, frame coordinates): `designs/pack_5200/print/frame/genframe_barrier.stl`

### Cost per part

| item | USD | source |
|---|---:|---|
| ROHACELL 110 IG-F 6 mm, one 625 x 312 sheet | 117 | Easy Composites EUR 41.60 per 3 mm 625 x 312 sheet; thicker/denser pro rata (ASSUMPTION) |
| 200 g 2x2 twill, 0.4 lm (two skins + doublers) | 12 | Easy Composites EUR 27.50 / lm, 1000 mm wide |
| laminating epoxy, peel ply, bag film, breather | 9 | ASSUMPTION |
| CNC router cut from DXF (local shop) | 25 | ASSUMPTION |
| 2 x 250 mm pultruded tube 10 x 8 mm | 4 | cfrp_pultruded_rod_tube record USD 8 / m (electronicscomp lists Rs 967 / m) |
| 6 MJF PA12 clips + pucks + pads (print bureau) | 18 | ASSUMPTION |
| EVA rub strip, edge coat, adhesive | 3 | ASSUMPTION |
| **total** | **188** | |

Process: lay up twill, the doublers (45°), routed ROHACELL, then the doublers and twill again. Vacuum bag on a flat plate, room-temperature cure, post-cure at 60 °C (below the 130 °C core limit). CNC-route the outline and slots from the DXF with a compression bit. Brush the edges. Bond the tubes, pucks, pads and rub strips with a jig made from the 1:1 PDF.

## 4. Mass

| item | g |
|---|---:|
| current part (sheet 193 + 4 M4 sets) | 203 |
| v2 sheet | 99 |
| v2 edge tubes | 21 |
| v2 clips, pucks, pads, doublers, edge seal | 34 |
| **v2 total** | **154** |
| saved | 49 |

## Screenshots

- `outputs/screens/20261104_spreader2_1.png`
- `outputs/screens/20261104_spreader2_2.png`
- `outputs/screens/20261104_spreader2_3.png`
- `outputs/screens/20261104_spreader2_4.png`
- `outputs/screens/20261104_spreader2_5.png`
- `outputs/screens/20261104_spreader2_6.png`

## Assumptions

- ASSUMPTION: Bone end is 20 % of 68 kg on a 22 mm patch (HA-LS-1), and is part of the meat, not added to it.
- ASSUMPTION: Soft tissue 60 kPa over a 25 mm column (20 kPa sensitivity); torso radius at the spine 230 mm (150 mm lean sensitivity).
- ASSUMPTION: The spacer mesh is 3 mm and lies on the skin; walking clearance must exceed it; factored clearance must be >= 0.
- ASSUMPTION: The L200 curve below 25 % and above 50 % (5, 10, 70, 80 % points) and its shear modulus.
- ASSUMPTION: Stay crowns rigid; crown line load resolved over max(20 mm, 2 sqrt(D/S)) for the sandwich (core-shear spreading length).
- ASSUMPTION: PA12 MJF clip allowable 0.6 x tensile; hook arm 4 mm.
- ASSUMPTION: Puck and pad PAHT-CF density from the record; pucks carry a 1 mm bond flange.
- ASSUMPTION: ROHACELL 110 and 5 mm prices pro rata from the published 3 mm ROHACELL 71 sheet price; EUR/USD 1.08.
- ASSUMPTION: Twill skin resin uptake into cut PMI cells 0.06 kg/m2.
- ASSUMPTION: Edge coat 0.3 mm epoxy on the cut edge.
