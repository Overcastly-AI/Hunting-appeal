# Production frame — print, bond, proof, cost

Pack 5200 frame, PAHT-CF. The print file is the **smooth ladder** (`genframe_assembled.stl`), not the lumpy SIMP mesh. Engineering record for comfort and the new safety factors: `designs/pack_5200/analysis/back_comfort.md`. The earlier pawl and joint record is `production_frame.md`. Units mm unless noted.

The 1.2 mm UHMWPE window sheet is retired. The back system is a **2.0 mm quasi-isotropic carbon spreader** clipped to the stays, with **10 mm XLPE rails** on the stay lines. See back_comfort.md.

## What you are printing

- Material: **Bambu PAHT-CF** (`pa12_cf_fdm_paht`). PPA-CF is not the production choice; see the heat section of the analysis.
- Printed body: **1291 g** (1218 cm³ of solid PAHT-CF). Whole frame **1734 g**, including the bought carbon spreader. Pack **7.51 lb**. The 468 g / 5.41 lb figures from the SIMP body are retired.
- Files: `genframe_assembled.stl` in frame coordinates. Split in the slicer at **z = 234 mm** (lower and upper), wearer face on the plate (layer normal = frame y), same orientation as the study.
- Do not print a tube-frame stand-in. This STL is the smooth ladder. Do not print the old SIMP skeleton.

## Printer (Bambu H2S)

- Dry the spool **80 C for 10–12 h**. Print from a dry box. Hardened **0.6 mm** nozzle.
- Nozzle **290 C**, bed **100 C** with glue, chamber closed, part cooling **≤ 30 %**, aux fan off.
- Layer **0.20 mm**, **6 walls**, **6** top and bottom layers, infill **100 %**. Line width 0.62. The stays are solid sections (about 34 mm across where the sleeve bore passes). 100 % infill is the structure; a sparse infill would put a one-voxel skin back in.
- Seam on the wearer face. Brim 8 mm. Speeds moderate (the TDS range, not the draft preset).
- Tree supports only where a bridge exceeds about 15 mm. Sleeve bores are drilled after, so a rough bridge inside a bore is acceptable.
- Expected print time about **45.7 h** for both segments at 8 mm³/s effective flow and 8 % waste (ASSUMPTION, same flow as the study, scaled to the 1218 cm³ solid).

## Anneal

TDS anneal window is 80–130 C. Use the low end on a part this size: **90 C for 6 h**, supported on a flat plate, a 16 mm rod through each sleeve bore so the two bores stay coaxial, then cool in the oven. Dry again before bonding. A higher anneal (120 C) is inside the TDS and not required; it raises the chance of a warp you cannot fixture out.

## Bond and hardware

1. Ream sleeve bores to **18.0 mm** for the UHMWPE crown bushings.
2. Pawl: ream each cheek to **8.0 mm** and press a 304 sleeve, OD 8.0 mm, ID 4.2 mm, length 8 mm (one each cheek). Pin is a 4 mm slip fit. Cheek wall as printed is 8 mm including the added wall.
3. Segment joint at z = 234: **8 carbon dowels**, 5 mm × 70 mm, 2 in each flange of each stay, 35 mm into each segment. Scuff the dowels. Abrade and flame-treat the nylon. MMA (`adhesive_methacrylate_ma`), 24 h, segments clamped on a flat board with a 16 mm rod through both sleeves.
4. Hip mount: M5 heat-set inserts, SLM Ti pivot mount, as on the tube frame.
5. Spreader: **bought quasi-isotropic carbon plate, 2.0 mm**, cut 208 × 300 mm, clipped to the stay nodes on the bag side of the window. Do not print a PAHT sheet in its place unless you accept the 4.0 mm web in `back_comfort.md` (289 g, and it only just clears the pad standoff). The 1.2 mm UHMWPE film is retired.

## QC proof load

Do the HA-LS-1 rev B tests in `analysis/load_standard.md` (T1–T5, T2 with game bags on the internal straps, T4c empty drop at −20 C). Add three frame-specific checks on the first article:

| check | load | pass |
|---|---|---|
| T1 static, already in the standard | 300 lb in the bag | no crack, crown set ≤ 1 mm |
| T1(c) hipbelt off | 225 lb | no whitening at the pawl bushing |
| Bone end | 400 N (90 lbf) through a 22 mm dowel, normal to the carbon spreader, at the window center, toward the wearer | no crack; spreader deflection stays inside the 14 mm pad standoff (10 mm rail + 4 mm); the window mesh does not go hard against the back |
| Joint | read during T1 | pencil marks across z = 234 do not step more than 0.5 mm after unload |

The 300 lb T1 is the release proof. A frame that passes the screen FEA and fails T1 is a no, not a print-setting tweak to argue with.

## Unit cost (one frame, USD)

| item | USD |
|---|---:|
| PAHT-CF filament, including 8 % waste | 111.51 |
| reprint allowance, 15 % of filament (ASSUMPTION) | 16.73 |
| carbon dowels | 4.48 |
| two 304 bushings (ASSUMPTION $4 each) | 8.00 |
| MMA | 2.00 |
| inserts and screws | 3.00 |
| QI carbon spreader, 2.0 mm (record $350/m² at 3 mm, scaled by thickness) | 14.56 |
| machine, 45.7 h at $1/h (ASSUMPTION) | 45.66 |
| **total** | **205.93** |

Filament price is the material record, $80/kg. Labor is not in the total; the hours are below.

## Print farm

A batch of 20 frames is 913 printer-hours. The solid stays are why this is no longer a one-week job.

| printers | calendar, at 16 h/day |
|---|---|
| 1 | 57.1 days |
| 3 | 19.0 days |
| 5 | 11.4 days |

Anneal 4 frames at a time, 6 h + slow cool, one shelf oven. Three H2S machines and one oven cover a 20-frame batch in about three weeks of printing, then annealing and bonding. Failed prints are why the cost table carries a 15 % filament allowance.

## Do not

- Do not anneal unsupported. The sleeve bores are a fit.
- Do not leave the frame strapped under a meat load in a closed vehicle. PAHT is above its glass transition at 60 C; it will creep. Strength for a short carry still meets the rupture check; a hot afternoon of sitting loaded does not have to.
- Do not skip the −20 C empty drop on the first article.
