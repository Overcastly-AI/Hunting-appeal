# BL-069 "Work with a PPU 3D printed frame": what PPU is, and what it does to H1

**Agent:** materials-engineer · **Size:** M · **Depends on:** BL-058 (H1 body record), BL-065 (eigen buckling), research/frame_comp_A.md · **Date:** 2026-11-25

Ask (owner, 2026-11-25): "Work with a ppu 3d printed frame". Find what "PPU" filament means (cited), write the material
record(s) for the intended material and the top alternative, compare against the PAHT-CF record H1 is printed in, say
what it does to the frame (mass, stiffness / buckling, strength, fatigue, creep, heat, moisture), whether it can lift
the cinch-cycled fatigue hold R1 (0.86) or make the frame lighter, and whether the owner's Bambu Lab H2S can print it.

## Deliverables
- Records: `data/materials/polymers/ppa_cf_fdm.yaml` (updated: full TDS, conditioned data, design values, H2S
  settings, current price), `data/materials/polymers/pps_cf_fdm_bambu.yaml` (new, the alternative).
- Test: `tests/test_materials_bl069.py` (5 tests).
- Re-evaluation run (scratch, not tracked): `outputs/bl069/run_ppa.py`, `run_pps.py`, `result_ppa_all.json`,
  `run.log`, `run_pps.log`, `chart.py`.
- Screenshot: `outputs/screens/20261125_bl069_1.png`.

## Result

| row | PAHT-CF (H1 today) | PPA-CF, design values | PPA-CF, TDS mean | PPS-CF |
|---|---:|---:|---:|---:|
| strength (min of 3 static bases) | 1.63 | 1.71 | 2.34 | 1.14 |
| fatigue, static carry | 1.25 | 1.48 | 1.96 | 0.97 |
| **fatigue, cinch-cycled (R1)** | **0.86** | **0.94** | 1.27 | 0.62 |
| creep (static / cinch-cycled) | 2.66 / 1.83 | 4.35 / 2.75 | 5.75 / 3.72 | 2.84 / 1.81 |
| buckling, eigen (BL-065: 1.34) | 1.34 | about 7.0 (x 5.26, scaled) | about 7.0 | about 5.2 (scaled) |
| printed body (halves + clevises) | 1069 g (2.36 lb) | **1261 g (2.78 lb), +192 g** | 1261 g | 1271 g |
| filament per frame, high bound | 1235 g, about $99 | 1456 g, about $291 | | 1468 g, about $254 |

Same print, same loads, same BL-058 rules; only the allowables change (method below). PPS-CF run on fine_sm8 and
fine_sm8.cyc only.

- **"PPU" is not a filament anyone sells.** The intended material is almost certainly **Bambu PPA-CF**.
- **PPA-CF does not lift R1 on design values (0.94),** and at the same margins **it cannot make the frame lighter:** the
  same geometry is 192 g heavier, and once PPA is in, interlayer shear governs, where PPA is weaker than PAHT.
- It lifts R1 only if the owner's H2S prints reach the TDS Z strength wet (1.27). The coupon decides: break-even is a
  knocked-down Z of about **35 MPa** (dry Z about 48 MPa at the 0.73 wet ratio).
- Real gains: heat (Tg 85 C against 45-70 C), creep, buckling (E x 3) and static fatigue.
- Real losses: +18 % mass, about 2.5x the price per kg, brittle across the layers (Z Charpy 4.3 against 13.3 kJ/m2,
  Z elongation 0.9 %): the -20 C drop T4c is the risk. It also needs a 100-140 C dryer, and the upper half no longer
  fits on one 0.75 kg spool.

## 1. What "PPU" means (research, 2026-11-25)

| reading | sold as a filament? | evidence | fit for a load-carrying frame on the H2S |
|---|---|---|---|
| "PPU" itself | **No product found** | Web searches for "PPU" filament, "PPU-CF" and "PU-CF" (general, Bambu forum, Reddit) return only PP, PPA-CF, PPS-CF and TPU products ([search 1: PP results only][pp-mh]; [Bambu forum PP / PPS / PPA threads][bbl-forum-pp]). | n/a |
| **PPA-CF** (polyphthalamide + CF), Bambu | yes, 0.75 kg spool | Bambu TDS V1.0 ([TDS][ppa-tds]); SimplyPrint lists H2S / H2D / X1C as printers that print it well and asks for a hardened steel nozzle ([SimplyPrint][sp-ppa]) | **most likely intent:** Bambu's flagship engineering CF filament, H2S profile, and the only reading that is stronger than PAHT-CF |
| PPS-CF (polyphenylene sulfide + CF), Bambu | yes | Bambu TDS V1.0 ([TDS][pps-tds]); JP store snippet: X1E / H2D / H2S only, no AMS ([Bambu JP][pps-jp]) | printable, but Z 24 MPa (PAHT 47): fails the frame (table above) |
| PP / PP-CF (polypropylene) | yes | Polypropylene filaments ([MatterHackers][pp-mh]); Nanovia PP-CF, about 100 C ([Filament2Print][pp-cf]) | no: soft matrix, poor adhesion, not a structural frame material |
| PU-based "rigid" filament (TPU) | only TPU | Bambu TPU for AMS, 68D: XY 22.4 MPa, Z 11.2 MPa, elongation > 650 % ([Bambu TPU for AMS TDS][tpu68d]); CF-TPU is an energy-absorber research topic ([PMC12251667][cftpu]) | no: about 1/4 of PAHT's strength, flexible |
| rigid polyurethane | **resin only** | Carbon RPU is a UV-cured resin for its CLIP process, not FDM ([Sculpteo][rpu]) | no: not printable on the H2S |
| PPSU (polyphenylsulfone) | yes | ThermaX PPSU: nozzle 360-390 C, bed 140-160 C, heated chamber ([3DXTech][ppsu]); Prusa: 370-410 C, chamber >= 65 C ([Prusa][ppsu-prusa]) | no: the H2S hotend stops at 350 C ([research/frame_comp_A.md 1][fca]) |

**Reading:** no "PPU" product exists. The owner prints on a Bambu H2S, and Bambu's high-performance CF line is
PAHT-CF / PA6-CF / **PPA-CF** / PPS-CF. PPA-CF is the only one of them stronger than today's PAHT-CF, so "PPU" is
taken as **PPA-CF**. The top alternative is **PPS-CF**. **Owner to confirm** (question 1 below).

## 2. Records

`ppa_cf_fdm.yaml` (updated; it already existed from frame_comp_A, 2026-11-01):
- Added from the TDS: Z flexural modulus 3240 MPa, Vicat 232 C, crystallisation 178 C, chamber window 50-80 C (Z is
  better at 70-80 C).
- Added the Raise3D **conditioned** data (XY 122 MPa, E 7800 MPa, mono-layer Z 30.2 MPa) as `_conditioned_` keys.
- Added the design Z, 45 MPa (57 - 2.4 SD).
- H2S process: 0.6 mm hardened nozzle, 290 C, bed 110 C, chamber 65 C.
- Price: $149.99 / 0.75 kg = $200/kg ($91/lb).
- **Changed `env_knockdown_ratio` 0.8 -> 0.73** to match the rule research/frame_comp_A.md 2.1 already used for PPA
  (Raise3D conditioned / Bambu dry).
- **Changed the price** $120 -> $200/kg (the 2026-11-01 read was $89.99 a spool).

`pps_cf_fdm_bambu.yaml` (new): the full Bambu TDS, the H2S process and $173/kg ($79/lb). Ratios are ASSUMPTIONS
(notes).

Dry vs conditioned: Bambu publishes only dry, unannealed values. The only conditioned PPA-CF data is Raise3D's (a
different brand): XY 122/168 = 0.73. PA6-CF loses 22-37 % on conditioning ([PolyMide PA6-CF][polymide];
[Jabil PA4535CF][jabil]), so 0.73 is in family. No PPA-CF fatigue or creep data exists for the Bambu grade. The one
FFF PPA-CF fatigue paper (Fiberlogy PPA CF15, Tg 60.5 C) gives run-outs at 1e6 and a "60-70 % UTS" window. Its own 20 C
maximum stress (65.5 MPa) is above its 20 C UTS (64.5 MPa), so it is not credited ([Polymers 18(12):1422][ppa-hot]).
That paper's E(T) (0.89 at 40 C, 0.61 at 60 C) is used only as a cross-check on the record's 0.85 / 0.75 ASSUMPTIONS.

## 3. Comparison (records)

| property | PAHT-CF (`pa12_cf_fdm_paht`) | PPA-CF (`ppa_cf_fdm`) | ratio PPA / PAHT |
|---|---:|---:|---:|
| density kg/m3 | 1060 | 1250 | **1.18** |
| E XY / Z MPa | 3860 / 2180 | 11800 / 4300 | 3.06 / 1.97 |
| tensile XY / Z MPa (dry TDS) | 88 / 47 | 168 / 57 | 1.91 / 1.21 |
| design XY / Z MPa (x hot/wet knock) | 70.4 / 37.6 (x 0.8) | 122.6 / 32.9 (x 0.73, Z 45) | **1.74 / 0.875** |
| specific design strength XY / Z (MPa per g/cm3) | 66 / 35 | 98 / 26 | 1.48 / 0.74 |
| specific stiffness E_xy / rho (MPa per g/cm3) | 3640 | 9440 | 2.59 |
| flexural XY / Z MPa | 140 / 68 | 208 / 63 | 1.49 / 0.93 |
| elongation XY / Z % | 10.4 / 5.2 | 3.2 / 0.9 | 0.31 / 0.17 |
| Charpy Z kJ/m2 | 13.3 ([fca]) | 4.3 | **0.32** |
| Tg C / HDT 1.8 MPa C | 45 record (70 TDS) / 170 | 85 / 196 | |
| E at 60 C (ratio, ASSUMPTION) | 0.35 | 0.75 | 2.1 |
| saturated water (25 C, 55 % RH) | 0.88 % | 1.30 % | 1.48 |
| creep-rupture 8 h 40 C (ASSUMPTION) | 0.40 | 0.55 | |
| fatigue 1e5 ratio (ASSUMPTION) | 0.30 | 0.30 | |
| drying | 80 C, 8-12 h | **100-140 C, 8-12 h**, forced-air oven | |
| price | $80/kg | $200/kg | 2.5 |

## 4. Effect on the H1 frame (computed)

**Method.** The BL-058 whole-body check (`frame_iter1` "h1": released `h1_assembled.stl` md5 7bd47cbd..., 2 mm grid,
lane kits, real crown, stays sanded k 1.0416, 4 bases) was re-run with the layer rule's allowables swapped
(`outputs/bl069/run_ppa.py`). The stress fields are unit-modulus isotropic solves, so they do not depend on the
material; only s_xy, s_z, knock, fat and rup change. **Control: PAHT reproduces bl058.json exactly** (1.692 / 1.298 /
2.769 fine_sm8; cinch-cycled 0.856; beam 1.630 / 1.249 / 2.664). The script also records which term of the layer
rule governs the top 1 % of the governing fatigue set.

| basis | PAHT: in-plane / interlayer shear share | PPA design: in-plane / interlayer shear share |
|---|---|---|
| fine_sm8.cyc (R1) | 61 % / 39 % | 2 % / **98 %** |
| fine_sm8 | 69 % / 31 % | 7 % / 92 % |
| beam | 98 % / 2 % | 48 % / 49 % |

- **Mass:** same geometry, x 1.179: 1069 -> 1261 g (+192 g, +6.8 oz) printed body. Filament with supports
  1235 -> 1456 g (high bound).
- **Stiffness / buckling:** E_xy x 3.06. The BL-065 rule's E is E_xy x hot x creep: 3860 x 0.6 x 0.7 = 1621 MPa
  against 11800 x 0.85 x 0.85 = 8526 MPa = **x 5.26**. Linear eigen buckling scales with E, so 1.34 becomes about 7.0
  (ASSUMPTION E-SCALE: BL-065's frame is one material and the prestress does not change).
  - Even on the Fiberlogy-like 0.61 hot ratio with PAHT's 0.7 creep ratio it is x 3.11 (about 4.2). Buckling stops
    mattering.
  - The frame also feels about 3x stiffer in torsion (DECISIONS 2026-11-01 was about this).
- **Strength:** 1.63 -> 1.71 (design) / 2.34 (TDS). Small on design values, because interlayer shear (0.6 x knocked Z)
  takes over.
- **Fatigue:** static carry 1.25 -> 1.48. **Cinch-cycled 0.86 -> 0.94 (design), 1.27 (TDS mean, 0.8 knock).**
- **Creep:** 2.66 -> 4.35 (Tg 85 C; ratio 0.55 is an ASSUMPTION).
- **Heat:** the big real gain. At 60 C in a truck cab E stays about 0.75 (PAHT 0.35, above its Tg). HDT 196 against
  170 C.
- **Moisture:** worse. 1.30 % against 0.88 % saturated; wet knock 0.73 against 0.8.
- **Cold / impact (not in the FI check):** worse. Z Charpy 4.3 against 13.3 kJ/m2, Z elongation 0.9 % against 5.2 %.
  T4c (-20 C empty drop) and any rock strike on a stay are the risks.
- **Joints and inserts (not re-run; ASSUMPTION JOINT-Z):** plug shear-out, hole bearing across the layers and insert
  pull-out use Z. These capacities scale by about 0.875 on design values:
  - the hip-mount insert reading (0.796 on the insert record, h1_closeout) drops further;
  - the cinch-cycled joint fatigue 1.05 could go to about 0.92 if Z governs it.
  - Must be re-run with `frame_h1.PAHT` swapped before any PPA build.

**Can PPA lift R1 (0.86)?** Not on design values: 0.94. The hot spot is 98 % interlayer-shear governed, so the
margin is about linear in knock x s_z. It reaches 1.0 at knock x s_z >= 32.9 / 0.937 = **35.1 MPa** (ASSUMPTION
LINEAR-Z), for example:
- dry Z >= 48 MPa at the 0.73 wet ratio; or
- a wet ratio >= 0.78 at Z 45; or
- a fatigue ratio >= 0.32.

The H2S's 65 C chamber is above Bambu's 52 C specimen chamber, and Bambu says a hotter chamber raises Z, so it is
plausible. It is not shown. **Settled by coupons:** CA-3-PPA (Z tensile and short-beam interlayer shear on H2S prints,
dry and after 14 d at 23 C / 50 % RH) and CA-1-PPA (R 0.1 fatigue). BL-066's CF-LITE already reads 1.15 cinch-cycled
in PAHT-CF.

**Lighter at the same margins?** No. With PPA, 92-98 % of the governing top 1 % is interlayer shear, where PPA's
design allowable is 0.875x PAHT's. Thinning a member raises exactly that stress. R1 is already below 1, so there is no
fatigue reserve to trade. Only the beam basis has in-plane headroom. This agrees with frame_comp_A (2026-11-01: PPA
converged at 740-760 g, "no lighter than PAHT").

## 5. Can the H2S print it?

| item | PPA-CF needs (TDS) | H2S | verdict |
|---|---|---|---|
| nozzle | hardened, 0.6 recommended, 280-310 C | 350 C hotend ([fca]); hardened-steel H2 hotends in 0.2-0.8 mm ([MatterHackers H2 HS hotend][h2-hs]); tungsten carbide option, about 50 % more life on CF ([Bambu TC nozzle][h2-tc]) | yes: the owner already runs a hardened 0.6 for PAHT-CF (BUILD_H1 3); expect faster wear, keep a spare |
| bed | 100-120 C, glue, smooth or textured PEI | 120 C max ([3DPI H2S specs][h2s-3dpi]) | yes, 110 C |
| chamber | 50-80 C; 70-80 C for better Z | actively heated to 65 C ([fca]) | yes, inside the window; it cannot reach the 70-80 C Z optimum |
| drying | 100-140 C, 8-12 h, forced-air oven (or an X1 heatbed at 110-120 C for 12 h, "not as good") | PAHT needs only 80 C | **new kit:** a forced-air oven at 120 C, or the heatbed method (ASSUMPTION BED-DRY: it carries over to the H2S bed); print from a sealed box < 20 % RH |
| spool | 0.75 kg | | **upper half needs 706-762 g** with supports (599-646 g x 1.179, BUILD_H1 table), the lower 642-695 g: start each half on a full, fresh spool and stage a second dried spool for a run-out swap. AMS feeding of PPA-CF on the H2S is not verified (ASSUMPTION SPOOL-SWAP) |
| plate adhesion / warp | glue; overhang about 70 deg; support "for PA/PET" | | higher risk than PAHT: 3x the modulus and it crystallises at 178 C on cooling, and the upper half touches the plate on only 223 mm2. Keep the chamber preheated 30 min at 65 C, glue, brim 8 -> 15 mm (ASSUMPTION WARP; first article settles it) |
| supports | same-material tree supports (single nozzle) | | PPA-CF supports are stiffer and more brittle to remove. Scars land on the stays' wearer faces (fatigue faces, SCAR-KD); sand as BUILD_H1. A PA/PET interface material would need filament swaps every interface layer on an 18-21 h print: not recommended |
| anneal | 120-140 C, 6-12 h, may warp, cuts toughness | | **do not anneal** the halves; no annealing credit is taken |
| time | < 100 mm/s | | about the same as PAHT, 18-21 h per half (ASSUMPTION; slicer settles it) |

PPS-CF on the H2S: chamber 60-90 C wanted (65 C available), nozzle 310-340 C (OK), no AMS. It prints, but it is
weaker; see the table.

## Pick

**If "PPU" means a better filament for H1: Bambu PPA-CF, but only as the hot-climate / stiffness alternate. Do not
switch the production frame on paper.** The switch costs +192 g and about $190 more filament per frame. It is brittle
across the layers. On design values it does not clear R1 (0.94).

The switch is worth making only if coupons on owner H2S prints show a wet knocked-down Z of at least 35 MPa, with fatigue
ratio >= 0.30, **and** a -20 C drop of a printed stay coupon passes. PPS-CF is ruled out (R1 0.62, strength 1.14).

## ASSUMPTIONS THAT GOVERN
- ASSUMPTION PPU=PPA: "PPU" means Bambu PPA-CF. Settled by: owner confirmation.
- ASSUMPTION WET-PPA: wet knock 0.73 (Raise3D conditioned / Bambu dry, cross-brand); design Z 45 MPa. Settled by:
  CA-3-PPA, Z tensile and interlayer shear on H2S prints, dry and 14 d at 23 C / 50 % RH.
- ASSUMPTION FAT-PPA: fatigue_1e5_ratio 0.30 (the PA12-CF lower bound). Settled by: CA-1-PPA, R 0.1 coupons in both
  build directions.
- ASSUMPTION LINEAR-Z: the R1 margin scales with knock x s_z (98 % interlayer-shear governed). Settled by: rerun
  `outputs/bl069/run_ppa.py` with the coupon values.
- ASSUMPTION E-SCALE / hot ratios 0.85 (40 C wet), 0.75 (60 C), creep 0.85: Tg 85 C; Fiberlogy CF15 grade gives 0.89 /
  0.61. Settled by: 3-point bend at 40 C wet and 60 C (CA-4).
- ASSUMPTION JOINT-Z: joint and insert capacities scale 0.875 on the Z rule. Settled by: rerun `frame_h1.joint_check` /
  `h1_closeout` with PPA, and HB-6 insert pull-out in PPA.
- ASSUMPTION COLD: impact_minus20c_ratio 0.5. Settled by: T4c and a -20 C drop of a printed stay coupon.
- ASSUMPTION WARP, SPOOL-SWAP, BED-DRY (printing). Settled by: first article.

## OWNER DECISIONS NEEDED
1. Is "PPU" Bambu **PPA-CF**? (No filament is sold as "PPU". If you meant something else, a brand or a link settles it.)
2. If PPA-CF: switch only after coupons? (Recommended: print CA-1 / CA-3 coupons in PPA-CF next to PAHT; about one
   0.75 kg spool, about $150.) Or print a full PPA frame now as a second article (+192 g, about $290 of filament, brittle
   in the cold)?
3. Equipment: a dryer or oven that holds 120 C (PPA needs 100-140 C; the PAHT setup is 80 C).

## FOUND, NOT FIXED
- `ppa_cf_fdm` env_knockdown_ratio was 0.8 in the record but 0.73 in frame_comp_A's own table. The record now says
  0.73, so any regenerated study that reads the record (frame_topopt `load_print_materials`) will show PPA slightly
  lower than before. frame_comp_A uses its own constants and is unchanged.
- PAHT-CF record keeps Tg 45 C, while the TDS v2 says 70 C (noted in frame_comp_A).

## Sources
[ppa-tds]: https://www.additive-x.com/shop/mpattachments/file/viewonline/id/916/product_id/2729
[pps-tds]: https://www.additive-x.com/shop/mpattachments/file/viewonline/id/918/product_id/2730
[pps-jp]: https://jp.store.bambulab.com/en/products/pps-cf
[sp-ppa]: https://simplyprint.io/filaments/bambu-lab/ppa-cf
[ppa-hot]: https://pmc.ncbi.nlm.nih.gov/articles/PMC13306934/
[r3d]: https://cdn.shopify.com/s/files/1/2104/4351/files/Raise3D-Industrial-PPA-CF_TDS.pdf
[polymide]: https://cdn.shopify.com/s/files/1/0607/4289/files/PolyMide-PA6-CF-ProductDescription-V6.pdf
[jabil]: https://www.jabil.com/dam/jcr:b08bf9d4-e9c1-46cd-9592-3150ac22dd32/Jabil_PA4535CF_Filament_TDS_030623.pdf
[pp-mh]: https://www.matterhackers.com/store/c/polypropylene-3d-printer-filament
[pp-cf]: https://filament2print.com/en/pp-polypropylene/1665-pp-cf.html
[bbl-forum-pp]: https://forum.bambulab.com/t/printing-with-pps-cf/104531
[tpu68d]: https://cdn.shopify.com/s/files/1/1339/4265/files/Bambu_TPU_for_AMS_Technical_Data_Sheet.pdf
[cftpu]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12251667/
[rpu]: https://www.sculpteo.com/en/materials/clip-resin-material/rigid-polyurethane-clip-resin-material/
[ppsu]: https://www.3dxtech.com/ppsu-ppsf/
[ppsu-prusa]: https://help.prusa3d.com/article/ppsu-polyphenylsulfone_789273
[fca]: ../research/frame_comp_A.md
[h2-hs]: https://www.matterhackers.com/store/l/bambu-lab-hardened-steel-nozzle-for-h2p2s-series/sk/M8JLX3S3
[h2-tc]: https://asia.store.bambulab.com/en/products/tungsten-carbide-nozzle-h2-p2s
[h2s-3dpi]: https://3dprintingindustry.com/news/bambu-lab-launches-the-new-h2s-technical-specifications-and-pricing-243603/

Prices are from search snapshots on 2026-11-25 (Bambu and MatterHackers store pages refuse fetching; marked
secondary): PPA-CF $149.99 (Bambu US, Ultimate 3D Printing Store), $198 (MatterHackers); PPS-CF $129.99-$189.99.
The two Bambu TDS PDFs were read with pdftotext.
