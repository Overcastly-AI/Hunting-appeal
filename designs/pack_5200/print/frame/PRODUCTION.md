# Production frame — print, bond, proof, cost

Pack 5200 frame. The product is the **branching PAHT-CF print** (`genframe_assembled.stl`), not the carbon-tube ladder and not the solid 34 mm ladder. The back system is unchanged: a **2.0 mm quasi-isotropic carbon spreader** on the bag side of the stays, and **10 mm XLPE rails** on the stay lines, with mesh over the air gap. Record: `designs/pack_5200/analysis/generative_branch.md`. Units mm unless noted.

## What you are printing

- Material: **Bambu PAHT-CF** (`pa12_cf_fdm_paht`).
- Printed body: **774 g**. Whole frame **1194 g** with the carbon crown, the spreader and the pawl bushings. Pack **6.32 lb**.
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
5. Spreader: bought quasi-isotropic carbon, **2.0 mm**, 208 × 300 mm, clipped to the stay nodes on the bag side. Do not replace it with a printed plate. The printed plate that passes the bone check weighs more.
6. Rails: two XLPE pads, 100 × 420 × 10 mm, wearer face of the stays. Mesh over the rails only.

## QC proof load

HA-LS-1 rev B tests in `analysis/load_standard.md` (T1–T5). On the first article add:

| check | load | pass |
|---|---|---|
| T1 static | 300 lb in the bag | no crack, crown set ≤ 1 mm |
| T1(c) hipbelt off | 225 lb | no whitening at the pawl bushing or the upper bar |
| Bone end | 400 N (90 lbf) through a 22 mm dowel, normal to the spreader, at the window center, toward the wearer | no crack; deflection stays inside the 14 mm pad standoff |
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
| QI carbon spreader | 14.6 |
| XLPE rails (ASSUMPTION) | 3.0 |
| **total** | **about 208** |

## Do not

- Do not build the carbon-tube ladder as the frame. It is lighter and it is not the product.
- Do not print a gyroid in place of the limbs.
- Do not leave the frame strapped under a meat load in a closed hot vehicle. PAHT is above its glass transition at 60 C.
- Do not skip the −20 C empty drop on the first article.

## Spreader layout rev C (2026-11-05): thin-sheet option, owner to choose

Record: `designs/pack_5200/analysis/spreader_layout.md`. The print files in this folder (`genframe_assembled.stl`,
`genframe_lower_flat.*`, `genframe_upper_flat.*`, split at z = 234) now carry **six open-top stay sockets** (16 mm long,
2.5 mm wall, about 220 deg wrap) on the stays at z 124 and 165 and on the inboard branches at z 225, 280, 385, 420.
Printed body about 840 g on the 2 mm raster (+16 g). Lower segment about 265 x 237 x 79 mm, upper about 265 x 306 x 48 mm
on the plate: both fit the H2S. Socket undersides take tree supports like the branches.

- Cross stays: roll-wrapped carbon tube, 14/12 mm at z 124, 165, 225 and 12/10 mm at z 280, 385, 420, cut to the socket
  ends (DXF MARK lines), ends sanded square, edges broken. They snap into the sockets from the bag side.
- Sheet: 1.5 mm (0.060 in) HDPE, `designs/pack_5200/cut/spreader/spreader_v3_hdpe_cut.dxf`, drawing
  `spreader_v3_drawing.pdf`. Six PA12 clips with a 6 mm saddle hold it 6 mm above the stay crowns.
- New first-article test **T8**: 400 N through a 22 mm dowel at the worst bay centre and at the IM1 notch root, 10 min,
  then 10,000 cycles 0 to 213 N. No crack or craze, dent <= 2 mm after 1 h, dowel never reaches the rail plane.
- If the owner keeps the sandwich v2 instead, print the previous body without the sockets: the cups stand 1.8 mm proud
  of the crown plane, where the sandwich sits.
