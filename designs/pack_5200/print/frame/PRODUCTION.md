# Production frame — print, bond, proof, cost

Pack 5200 frame. The product is the **branching PAHT-CF print** (`genframe_assembled.stl`), not the carbon-tube ladder and not the solid 34 mm ladder. The back system: the **Sandwich v2 spreader** (BP-06 rev B, owner 2026-11-05: 200 g twill carbon skins on 6 mm ROHACELL 110, 154 g installed) clipped to the bag side of the stays, and **10 mm XLPE rails** on the stay lines, with mesh over the air gap. The print files in this folder are the **socket-free** body the sandwich was checked on. Records: `designs/pack_5200/analysis/generative_branch.md` (frame), `designs/pack_5200/analysis/spreader.md` (spreader). Units mm unless noted.

## What you are printing

- Material: **Bambu PAHT-CF** (`pa12_cf_fdm_paht`).
- Printed body: **774 g**. Whole frame **1194 g** with the carbon crown, the old 193 g QI sheet and the pawl bushings (`generative_branch.md`); with the Sandwich v2 installed (154 g) about **1155 g** (1194 − 193 + 154). Pack with fairleads, under-straps and the sandwich **3052 g (6.73 lb)** (`DESIGN.md` §6).
- File: `genframe_assembled.stl`. Each stay is split into a sleeve limb and an inboard branch. The surface is smooth.
- The part is about 540 mm tall. An H2S build volume is 340 mm tall, so split the mesh in the slicer at **z = 234 mm** (lower and upper). Wearer face on the plate (layer normal = frame y).
- The 2 mm check is of the **continuous** body. The joint across z = 234 is the same 8-dowel spec as the previous printed frame (2 × 5 mm carbon dowels per flange, 35 mm embed). Confirm it on the first article with the pencil-mark check below. That joint was not re-solved on this body.

## Printer (Bambu H2S)

- Dry the spool **80 C for 10–12 h**. Print from a dry box. Hardened **0.6 mm** nozzle.
- Nozzle **290 C**, bed **100 C**, chamber closed, part cooling **≤ 30 %**, aux fan off.
- Layer **0.20 mm**, **6 walls**, **6** top and bottom layers, infill **100 %** on the limbs. The limbs are the structure. Do not use a gyroid core in place of them.
- Seam on the wearer face. Brim 8 mm.
- Sleeve bores are drilled or reamed after printing. A rough bridge inside a bore is acceptable.
- Expected print time about **27 h** for both segments at 8 mm³/s and 8 % waste.

## Anneal

**90 C for 6 h**, on a flat plate, a 16 mm rod through each sleeve bore so the bores stay coaxial, then cool in the oven. Dry again before bonding.

## Bond and hardware

1. Ream sleeve bores to **18.0 mm** for the UHMWPE crown bushings.
2. Pawl: ream each cheek to **8.0 mm** and press a 304 sleeve, OD 8.0 mm, ID 4.2 mm, length 8 mm. Pin is a 4 mm slip fit, side to side.
3. Segment joint at z = 234: **8 carbon dowels**, 5 mm × 70 mm, 2 in each flange of each stay, 35 mm into each segment. Scuff, abrade, flame-treat, MMA, 24 h, clamped on a flat board with a rod through both sleeves.
4. Hip mount: M5 heat-set inserts, SLM Ti pivot mount.
5. Spreader: **Sandwich v2**, 242 × 318 × 6.44 mm, built from `designs/pack_5200/cut/spreader/` (see `README.md` there). Six MJF PA12 snap clips over the stays at z 166, 260, 400, the bottom tab on bonded PAHT-CF pads at z 119, 11 PAHT-CF pucks bonded to its wearer face. Toolless, nothing bonded to the frame. Do not substitute the old 2.0 mm QI sheet (fails on this frame: FPF SF 0.66, bottoms) or a printed plate.
6. Rails: two XLPE pads, 100 × 420 × 10 mm, wearer face of the stays. Mesh over the rails only.

## QC proof load

HA-LS-1 rev B tests in `analysis/load_standard.md` (T1–T5). On the first article add:

| check | load | pass |
|---|---|---|
| T1 static | 300 lb in the bag | no crack, crown set ≤ 1 mm |
| T1(c) hipbelt off | 225 lb | no whitening at the pawl bushing or the upper bar |
| Bone end | 400 N (90 lbf) through a 22 mm dowel, normal to the spreader, toward the wearer, at the window centre, at the US2 corner relief and at the IM1 notch root (governing points, `spreader.md`) | no crack, no skin-core disbond (coin tap before and after); deflection stays inside the 14 mm pad standoff |
| Joint | read during T1 | pencil marks across z = 234 do not step more than 0.5 mm after unload |

## Unit cost (one frame, USD)

| item | USD |
|---|---:|
| PAHT-CF filament, 774 g plus 8 % waste | 66.9 |
| reprint allowance, 15 % of filament | 10.0 |
| machine, 27 h at $1/h | 27.4 |
| carbon dowels | 4.5 |
| two 304 bushings | 8.0 |
| MMA | 2.0 |
| inserts | 3.0 |
| carbon crown tubes (record, scaled by diameter) | 44.3 |
| SLM Ti hip mount (ASSUMPTION) | 35.0 |
| UHMWPE bushings (ASSUMPTION) | 5.0 |
| Sandwich v2 spreader, installed (`spreader.md` cost table) | 188.0 |
| XLPE rails (ASSUMPTION) | 3.0 |
| **total** | **about 381** |

## Do not

- Do not build the carbon-tube ladder as the frame. It is lighter and it is not the product.
- Do not print a gyroid in place of the limbs.
- Do not leave the frame strapped under a meat load in a closed hot vehicle. PAHT is above its glass transition at 60 C.
- Do not skip the −20 C empty drop on the first article.

## Spreader decision (owner, 2026-11-05)

Production spreader: **Sandwich v2** (`designs/pack_5200/analysis/spreader.md`), re-checked with the lumbar pan in
the skin model (`designs/pack_5200/analysis/spreader_layout.md`: factored lean-torso air 8.4 mm). The print files in
this folder (`genframe_assembled.stl`, `genframe_lower_flat.*`, `genframe_upper_flat.*`, split at z = 234) are the
**socket-free** branch body, restored from the commit before the layout study. `genframe_barrier.stl/.json` is the
sandwich (viz3d). Frame on this body, all HA-LS-1 rev B cases (2 mm): min SF 1.69 (hipbelt_off_abuse), fatigue 1.19,
creep-rupture 2.55 (`spreader_layout.md` §3, "today" column).

Rejected for production, kept as a documented alternative: **d6L** (1.5 mm HDPE on 6 removable carbon cross stays in
printed sockets, 217 g, about $60, barrier rule + T8). Code: `huntkit/gendesign/spreader_layout.py` (layout
`d6L_tubes`). `spreader_layout_report.write_print_files` writes its socketed body to
`outputs/spreader_layout/print_d6L/` (scratch) and never to this folder. Its sheet files are
`designs/pack_5200/cut/spreader/spreader_v3_*`; do not cut them for the production build.
