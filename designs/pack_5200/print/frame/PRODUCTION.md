# Production frame — print, bond, proof, cost

Pack 5200 frame. The product is the **branching PAHT-CF print** (`genframe_assembled.stl`), not the carbon-tube ladder and not the solid 34 mm ladder. The back system: the **Sandwich v2 spreader** (BP-06 **rev C**, owner 2026-11-06: 200 g twill carbon skins on **7 mm** ROHACELL 110, 162 g installed; rev B had a 6 mm core) clipped to the bag side of the stays, and **10 mm XLPE rails** on the stay lines, with mesh over the air gap. The print files in this folder are the **socket-free** body the sandwich was checked on. Records: `designs/pack_5200/analysis/generative_branch.md` (frame), `designs/pack_5200/analysis/spreader.md` (spreader). Units mm unless noted.

## What you are printing

- Material: **Bambu PAHT-CF** (`pa12_cf_fdm_paht`).
- Printed body: **823 g** on the production 2 mm raster of the files in this folder (`analysis/frame_mass_production.json`; the earlier 774 g was the 1.05-scale study body in `generative_branch.md`). Frame with the carbon crown (rev C fix included), rack, pawl, bushings and Ti mount **1063 g**; with the 7 mm Sandwich v2 installed (162 g) **1225 g**. Pack: `DESIGN.md` §6.
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
5. Spreader: **Sandwich v2, BP-06 rev C**, 242 × 318 × **7.44 mm** (7 mm core), built from `designs/pack_5200/cut/spreader/` (see `README.md` there). Six MJF PA12 snap clips over the stays at z 166, 260, 400, the bottom tab on bonded PAHT-CF pads at z 119, 11 PAHT-CF pucks bonded to its wearer face. Toolless, nothing bonded to the frame. Do not substitute the old 2.0 mm QI sheet (fails on this frame: FPF SF 0.66, bottoms) or a printed plate.
6. Rails: two XLPE pads, 100 × 420 × 10 mm, wearer face of the stays. Mesh over the rails only.

## Carbon crown (HA-LS-1 rev C fix, owner 2026-11-06)

The crown is bought roll-wrapped tube, bonded at two corners. Rev C adds **inner** 0° UD plies so the outer diameters
do not change: the printed sleeves, the 18.0 mm bores, the spine channel, the bushings and the crown hood all fit as
before. Record: `analysis/frame_cg_recheck.md` §4, verified in `analysis/rev_c_verification.md`. Definition:
`designs/pack_5200/frame.yaml` (`leg_section`, `spine_section`, `top_bar_section`, `crown_joint`).

| part | qty | OD mm | layup (outside → inside → outside) | wall mm | change | Δ g |
|---|---:|---:|---|---:|---|---:|
| crown leg, 430 mm | 2 | 16.0 | twill ±45 / **UD 0 × 8** / twill ±45 | **1.44** (ID 13.1) | +2 UD (was × 6, wall 1.19, ID 13.6) | +14.3 |
| crown top bar, 214 mm | 1 | 18.0 ± 0.3 | twill ±45 / **UD 0 × 5** / twill ±45 | **1.065** | +1 UD (was × 4) | +2.1 |
| crown spine tube, 300 mm | 1 | 20.0 | twill ±45 / **UD 0 × 5** / twill ±45 | **1.065** | +1 UD (was × 4) | +3.3 |
| crown-corner bondline | 2 | | MMA (`adhesive_methacrylate_ma`) with **0.8 mm glass beads** | **0.8** | was 0.5 mm | +2.2 |
| **total** | | | | | | **+22.0** |

Layup (order from the tube vendor; the same special-order wrap as the existing legs):
1. Specify the **OD** (16.0 / 18.0 / 20.0 mm), the ply schedule above and that the extra UD goes in the **core**, so
   the mandrel gets smaller and the OD stays. T700-class UD, 0.125 mm per ply (`cfrp_t700_ud_epoxy_ply`). Reject any
   tube with OD outside ±0.1 mm (bar: the hood needs 18.0 ± 0.3).
2. Before bonding, check that the extension-post plug and the corner-wrap liner still slide into the **13.1 mm leg
   ID**. ASSUMPTION: the vendor holds the ID to ±0.1 mm; sand the plug if it is tight, never the tube.

Corner wrap (both crown corners):
1. Cope the leg top and the bar end as before. Sand both bond areas (120 grit), wipe with IPA.
2. Mix **0.8 mm glass beads** into the MMA (about 1 % by volume; ASSUMPTION, the usual bead-spacer practice; the
   adhesive record names 0.2 mm beads for 0.15–0.3 mm bondlines). Butter both faces and assemble; the beads set the
   **0.8 mm** bondline. ASSUMPTION: MA300-class MMA gap-fills 0.8 mm (TDS gap fill is larger); confirm on the T6 coupon.
3. Wrap 0.75 mm (3 plies 3k twill, 0/90 and ±45), **30 mm onto each tube**. Do **not** shorten the bar-side wrap to
   clear the hood: at 20 mm overlap the corner peak falls to 0.97 and at 11 mm to 0.79 (`frame_cg_recheck.md` §5.1).
   The hood fits over the wrap ends (pack-designer B-19).
4. Ply-drop the wrap ends over 8 mm, peel ply, shrink tape, RT cure + 65 °C post-cure.

**T6 coupon note:** the crown-corner T6 coupons must be made **with the 0.8 mm bondline and the glass beads**, exactly
like the frame. The rev C corner check credits the Volkersen-peak rule (`load_standard.md` §4); a 0.5 mm coupon does not
qualify the frame.

## QC proof load

HA-LS-1 rev C tests in `analysis/load_standard.md` (T9 loaded CG first, then T1–T5). On the first article add:

| check | load | pass |
|---|---|---|
| T1 static | 300 lb in the bag | no crack, crown set ≤ 1 mm |
| T1(c) hipbelt off | 225 lb | no whitening at the pawl bushing or the upper bar |
| Bone end | 400 N (90 lbf) through a 22 mm dowel, normal to the spreader, toward the wearer, at the window centre, at the US2 corner relief and at the IM1 notch root (governing points, `spreader.md`) | no crack, no skin-core disbond (coin tap before and after); deflection stays inside the 14 mm pad standoff |
| Joint | read during T1 | pencil marks across z = 234 do not step more than 0.5 mm after unload |

## Unit cost (one frame, USD)

| item | USD |
|---|---:|
| PAHT-CF filament, 823 g plus 8 % waste | 71.1 |
| reprint allowance, 15 % of filament | 10.7 |
| machine, 27 h at $1/h | 27.4 |
| carbon dowels | 4.5 |
| two 304 bushings | 8.0 |
| MMA | 2.0 |
| inserts | 3.0 |
| carbon crown tubes (record, scaled by diameter; rev C extra UD plies ASSUMPTION +$6 special order) | 50.3 |
| SLM Ti hip mount (ASSUMPTION) | 35.0 |
| UHMWPE bushings (ASSUMPTION) | 5.0 |
| Sandwich v2 spreader 7 mm core, installed (`spreader_results.json` cost) | 207.2 |
| XLPE rails (ASSUMPTION) | 3.0 |
| **total** | **about 427** |

## Do not

- Do not build the carbon-tube ladder as the frame. It is lighter and it is not the product.
- Do not print a gyroid in place of the limbs.
- Do not leave the frame strapped under a meat load in a closed hot vehicle. PAHT is above its glass transition at 60 C.
- Do not skip the −20 C empty drop on the first article.

## Spreader decision (owner, 2026-11-05)

Production spreader: **Sandwich v2**, 7 mm core since HA-LS-1 rev C (2026-11-06, `analysis/rev_c_verification.md`; `designs/pack_5200/analysis/spreader.md` is the rev B 6 mm record), re-checked with the lumbar pan in
the skin model (`designs/pack_5200/analysis/spreader_layout.md`: factored lean-torso air 8.4 mm). The print files in
this folder (`genframe_assembled.stl`, `genframe_lower_flat.*`, `genframe_upper_flat.*`, split at z = 234) are the
**socket-free** branch body, restored from the commit before the layout study. `genframe_barrier.stl/.json` is the
sandwich (viz3d). Frame on this body, all HA-LS-1 rev B cases (2 mm): min SF 1.69 (hipbelt_off_abuse), fatigue 1.19,
creep-rupture 2.55 (`spreader_layout.md` §3, "today" column).
Under **HA-LS-1 rev C** (2026-11-06, both bag-couple variants, `analysis/rev_c_verification.md`): min SF 1.51
(hipbelt_off_abuse, 15 in), fatigue 1.04 (IM3 couple), creep-rupture 2.23; the crown fix and the 7 mm spreader
core are what make rev C pass.

Rejected for production, kept as a documented alternative: **d6L** (1.5 mm HDPE on 6 removable carbon cross stays in
printed sockets, 217 g, about $60, barrier rule + T8). Code: `huntkit/gendesign/spreader_layout.py` (layout
`d6L_tubes`). `spreader_layout_report.write_print_files` writes its socketed body to
`outputs/spreader_layout/print_d6L/` (scratch) and never to this folder. Its sheet files are
`designs/pack_5200/cut/spreader/spreader_v3_*`; do not cut them for the production build.
