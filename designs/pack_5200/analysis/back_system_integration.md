# Back system integration (BL-005): can one structure do both jobs?

Owner: structural-fea-engineer, 2026-11-10/11. Code: `huntkit/gendesign/back_system2.py`
(`python -m huntkit.gendesign.back_system2`; cached numbers in `outputs/back_system2/results.json`, not tracked).
Tests: `tests/test_back_system2.py`. Research: `docs/research/back_panel_structures.md`.
Load: HA-LS-1 rev C C5 meat case, CG 190 mm aft (covers 15 / 19 / 23 in), walking 1.6 g, factored 2.0 g × 1.5,
bone end 20 % of 68 kg on a 22 mm patch. Comfort limit 14 kPa peak (Golriz et al. 2017, `back_comfort.md`).

## Verdict

- **No: the spreader cannot also be the rail backer.** The two jobs sit on opposite faces of the stays, 28 mm apart.
  (a1) widening the spreader on the bag side backs nothing: skin **30.6 kPa**. (a2) moving it to the wearer face as a
  framesheet fails first-ply (SF **0.94**), fatigue (**0.85**) and skin (**24.7–32.2 kPa**), needs **36–54 mm** of
  rail foam to keep air to the back, collides with the lumbar pan below z 190, and is **15–33 g heavier**, not lighter.
- **Yes, the backer strip can be much lighter.** Replace BP-08 (1 mm twill plate, 80 mm, 102.5 g pair) with a
  **sandwich strip: 200 g 2×2 twill / 3 mm ROHACELL 71 IG-F / 200 g twill, 70 × 420 mm**, the same in-house process
  as the spreader. Skin **13.76 → 13.29 kPa** (1-D) and **13.77 → 13.31 kPa** in the full `spreader.evaluate`
  (named positions, 2 mm). Strip SF **2.73** factored, fatigue **6.48** (today's strip, never checked before: 1.70 /
  1.60). Spreader unchanged: FPF **1.25**, fatigue **1.09**, sandwich **1.11**. Air to the back walking / factored /
  lean torso **13.2 / 7.3 / 3.8 mm** (full check, which ignores the strip thickness; 15.6 / 9.7 / 6.2 mm with the 2.4 mm
  thicker stack; today 13.0 / 6.9 / 3.4).
- **Mass: back system 413.6 → 369.0 g (−44.6 g, −1.6 oz).** Ledger 413.6 g (14.6 oz); recommended 369.0 g (13.0 oz).
- **The 320 g target (stretch 290 g) is not met, and cannot be met by the structure alone.** Deleting both backer
  strips outright leaves 311 g, and no passing build gets the strips below ~45 g. The lightest passing row in the
  study is 360.6 g (2 mm core, 380 mm rail, see why it is not recommended). The rest of the 320 g gap is in the soft
  parts (mesh 67.6 g, upper pad 29.1 g, sleeves 19.3 g) and the spreader (162.3 g), which today's rules hold.

## 1. Today reproduced (task 1)

| number | target | reproduced | difference |
|---|---:|---:|---:|
| peak skin, rev C meat case, CG 190 mm (`back_rail.skin`, worst bone "at a clip", 203.6 N side) | 13.8 kPa | **13.76 kPa** | −0.3 % |
| peak skin, full `spreader.evaluate` sw110c7d, 2 mm, named positions | 13.8 kPa | **13.77 kPa** | −0.2 % |
| spreader fatigue (FI ≤ 0.5 rule) | 1.09 | **1.088** | −0.2 % |
| spreader first ply / sandwich local | 1.25 / 1.11 | **1.255 / 1.114** | 0 % |
| bone side reaction, production spreader, h 2 mm | 203.6 N | **203.6 N** | 0 % |

Bone rule: the spreader passes HA-LS-1's strict bone rule (no first-ply failure at 3.0× the static bone, factored
FPF SF 1.25 at the US2 corner relief; fatigue 1.09). Re-run 2026-11-10, 2 mm, named positions (the 68-position grid
record in `spreader_results.json` gives the same SFs: the worst positions are named ones).

### Layer masses (ledger, `huntkit.mass.ledger`, config `corrie_b2_h1`, belt M)

| layer | g | oz | source of the split |
|---|---:|---:|---|
| **back system (ledger `back`)** | **413.6** | **14.6** | ledger |
| spreader (ledger row) | 162.3 | 5.7 | ledger |
| · sheet, twill / 7 mm R110 / twill | 106.6 | 3.8 | `spreader_results.json` chosen.sheet_g |
| · edge tubes | 21.0 | 0.7 | chosen.tubes_g |
| · clips, pucks, pads, doublers, seal | 34.7 | 1.2 | chosen.fittings_g |
| back panel (ledger row) | 251.3 | 8.9 | ledger |
| · BP-08 rail backer strips, 1 mm twill, 80 × 420, pair | 102.5 | 3.6 | `panels.yaml` |
| · BP-01 back-panel spacer mesh | 67.6 | 2.4 | `panels.yaml` |
| · BP-02 stay-rail foam, 120 × 420 × 10 L200, pair | 32.8 | 1.2 | `panels.yaml` |
| · BP-05 rail sleeves, pair | 19.3 | 0.7 | `panels.yaml` |
| · BP-03 / BP-04 / BP-07 upper back pad (face, foam, back) | 29.1 | 1.0 | `panels.yaml` |

The `panels.yaml` and `spreader_results.json` splits add to the ledger rows (tested). Variant masses are the ledger
total plus the change computed by the `back_rail.mass_g` method.

## 2. Research (task 2)

`docs/research/back_panel_structures.md`. In short: packs that use one sheet for barrier and back spread put the sheet
on the **body side** of the stays with a dense foam or lumbar stack on it (Mystery Ranch HDPE + XPE, Kifaru, KUIU/ARK
carbon shells). Open frames (Seek Outside cross stays, Exo, Stone Glacier) separate the jobs as we do. No published
pressure map of a framed hunting pack's back exists; the 14 kPa rule (Golriz 2017) and the tissue data are the ones
in `back_comfort.md`.

## 3. Method

- **Skin:** the released 1-D rail section (`spreader.rail_backed`: stay on a strip on aged L200 on a 25 mm, 60 kPa
  tissue column, Pasternak shear from the foam) with the bone reaction spread along the stay (Hetenyi, peak Pβ/2),
  exactly as `back_rail.skin`. `section2` copies it and adds a Timoshenko strip (core shear S = G_c d²/t_c) and the
  strip's moment and shear. With a shear-rigid strip it equals `rail_backed` to 1e-6 (test).
- **Strip strength:** Tsai-Wu first ply (hot/wet 0.8, impact 0.65 on compression) at factored loads; fatigue FI ≤ 0.5
  at walking (the spreader's CFRP rule); sandwich core shear Q/d and core crush under the stay line load.
- **Spreader and clearance for the recommendation:** full `spreader.evaluate` (sw110c7d, h 2 mm, named positions) with
  the sandwich-strip rail patched in (`back_system2.confirm`). For the other rows, air is today's full-check value
  shifted by the change in rail indentation, aged foam height, strip thickness and gutter bulge (the sheet field does
  not depend on the rail, `back_rail.md`).
- **Framesheet (a2):** `huntkit.fea.plate_grid.GridPlate` (5 mm ACM) on a secant, unilateral Winkler foundation (the
  same foam + tissue column) over the rail bands, stays as free PAHT beams tied to the sheet, meat share spread
  uniformly (as the 1-D model), cinch self-equilibrated through the stays, bone at 9 positions. Verified: foundation
  reaction = applied meat share to 0.1 % (test); the plate solver's own verification is in `tests/test_spreader.py`.
- Torso: the rail model depends on torso only through the meat CG. Rev C 190 mm covers all three; the per-torso meat
  runs 181 / 173 / 165 mm (15 / 19 / 23 in, `load_standard.md` rev C table) are shown as well.
- Recommendation rule (ASSUMPTION): passes all checks with ≥ 0.2 kPa skin margin and gutter ≥ 110 mm (as
  `back_rail.py`), a core sold as stock sheet (thinnest ROHACELL 71 IG-F is 3 mm), released rail foam / sleeve / mesh
  patterns unchanged, full 420 mm rail.

## 4. Options (task 3 and 4)

Pass = skin ≤ 13.8 kPa (limit 14, 0.2 margin), gutter ≥ 110 mm, strip SF ≥ 1 factored and fatigue, walk air ≥ 3 mm,
factored ≥ 0, factored lean torso (R 150) ≥ 0. Air columns: today's full check shifted (see method). Bold: recommended.

| key | build | skin kPa 190 mm | 15 / 19 / 23 in (181 / 173 / 165 mm) | backer SF factored / fatigue | air walk / fact / lean mm | gutter mm | stack mm | mass change g | back system g | passes |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|
| today | today: 120 mm rail, 80 mm 1 mm twill backer, sw110c7d spreader | 13.76 | 13.3 / 12.8 / 12.4 | 1.70 / 1.60 | 13.0 / 6.9 / 3.4 | 110 | 11.0 | +0.0 | 413.6 | yes |
| a1_wide_bagside | (a1) spreader widened to x +/-155 on the bag side, backers deleted | 30.59 | 29.5 / 28.4 / 27.4 | — (no strip) | 4.4 / -8.7 / -12.2 | 110 | 10.0 | -70.6 | 343.0 | no: skin, no_bottoming |
| b_tw051_80 | (b) 0.5 mm twill plate (2 plies), 80 mm | 18.07 | 17.4 / 16.8 / 16.2 | 0.74 / 0.69 | 10.6 / 2.8 / -0.7 | 110 | 10.5 | -51.4 | 362.2 | no: skin, backer_fpf, backer_fatigue, no_bottoming |
| b_tw051_100 | (b) 0.5 mm twill plate (2 plies), 100 mm | 17.96 | 17.3 / 16.7 / 16.1 | 0.75 / 0.71 | 10.6 / 2.9 / -0.6 | 110 | 10.5 | -38.6 | 375.0 | no: skin, backer_fpf, backer_fatigue, no_bottoming |
| b_swR71c2_60 | (b) sandwich strip: 200 g twill / 2 mm R71 / twill, 60 mm | 14.31 | 13.8 / 13.3 / 12.9 | 1.91 / 4.95 | 14.1 / 7.9 / 4.4 | 110 | 12.4 | -57.3 | 356.3 | no: skin |
| b_swR71c2_70 | (b) sandwich strip: 200 g twill / 2 mm R71 / twill, 70 mm | 13.49 | 13.0 / 12.6 / 12.1 | 1.89 / 4.42 | 14.5 / 8.6 / 5.1 | 110 | 12.4 | -50.0 | 363.6 | yes |
| b_swR71c2_80 | (b) sandwich strip: 200 g twill / 2 mm R71 / twill, 80 mm | 12.90 | 12.4 / 12.0 / 11.6 | 1.88 / 4.04 | 14.8 / 9.0 / 5.5 | 110 | 12.4 | -42.6 | 371.0 | yes |
| b_swR71c3_60 | (b) sandwich strip: 200 g twill / 3 mm R71 / twill, 60 mm | 14.14 | 13.6 / 13.2 / 12.7 | 2.75 / 7.28 | 15.2 / 9.0 / 5.5 | 110 | 13.4 | -52.6 | 361.0 | no: skin |
| **b_swR71c3_70** | (b) sandwich strip: 200 g twill / 3 mm R71 / twill, 70 mm | 13.29 | 12.8 / 12.4 / 12.0 | 2.73 / 6.48 | 15.6 / 9.7 / 6.2 | 110 | 13.4 | -44.6 | 369.0 | yes |
| b_swR71c3_80 | (b) sandwich strip: 200 g twill / 3 mm R71 / twill, 80 mm | 12.66 | 12.2 / 11.8 / 11.4 | 2.71 / 5.90 | 15.9 / 10.2 / 6.7 | 110 | 13.4 | -36.7 | 376.9 | yes |
| b_swR110c2_60 | (b) sandwich strip: 200 g twill / 2 mm R110 / twill, 60 mm | 14.19 | 13.7 / 13.2 / 12.8 | 3.50 / 4.92 | 14.2 / 8.0 / 4.5 | 110 | 12.4 | -53.8 | 359.8 | no: skin |
| b_swR110c2_70 | (b) sandwich strip: 200 g twill / 2 mm R110 / twill, 70 mm | 13.36 | 12.9 / 12.4 / 12.0 | 3.47 / 4.39 | 14.6 / 8.7 / 5.2 | 110 | 12.4 | -45.8 | 367.8 | yes |
| b_swR110c2_80 | (b) sandwich strip: 200 g twill / 2 mm R110 / twill, 80 mm | 12.76 | 12.3 / 11.9 / 11.5 | 3.45 / 4.00 | 14.8 / 9.2 / 5.7 | 110 | 12.4 | -37.9 | 375.7 | yes |
| b_swR110c3_60 | (b) sandwich strip: 200 g twill / 3 mm R110 / twill, 60 mm | 14.06 | 13.5 / 13.1 / 12.6 | 5.05 / 7.26 | 15.2 / 9.1 / 5.6 | 110 | 13.4 | -47.3 | 366.3 | no: skin |
| b_swR110c3_70 | (b) sandwich strip: 200 g twill / 3 mm R110 / twill, 70 mm | 13.20 | 12.7 / 12.3 / 11.9 | 5.01 / 6.46 | 15.6 / 9.8 / 6.3 | 110 | 13.4 | -38.5 | 375.1 | yes |
| b_swR110c3_80 | (b) sandwich strip: 200 g twill / 3 mm R110 / twill, 80 mm | 12.56 | 12.1 / 11.7 / 11.3 | 4.98 / 5.88 | 15.9 / 10.3 / 6.8 | 110 | 13.4 | -29.6 | 384.0 | yes |
| b_paht_rib_80 | (b) printed PAHT-CF ribbed strip (1.0 base + 1.2 x 4 ribs at 8 mm), 80 mm | 13.36 | 12.9 / 12.4 / 12.0 | 1.16 / 0.65 | 17.1 / 11.2 / 7.7 | 110 | 15.0 | +12.1 | 425.7 | no: backer_fatigue |
| c_swR71c3_80_r100 | (c) 100 mm rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 80 mm | 13.89 | 13.4 / 12.9 / 12.5 | 2.74 / 6.36 | 12.7 / 6.6 / 1.7 | 130 | 13.4 | -48.0 | 365.6 | no: skin |
| c_swR71c3_80_r110 | (c) 110 mm rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 80 mm | 13.15 | 12.7 / 12.3 / 11.8 | 2.72 / 6.09 | 14.4 / 8.6 / 4.4 | 120 | 13.4 | -42.3 | 371.3 | yes |
| c_swR71c3_80_L380 | (c) 380 mm long rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 80 mm | 13.43 | 12.9 / 12.5 / 12.0 | 2.56 / 5.57 | 15.5 / 9.6 / 6.1 | 110 | 13.4 | -47.6 | 366.0 | yes |
| c_swR71c3_80_L340 | (c) 340 mm long rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 80 mm | 14.37 | 13.8 / 13.3 / 12.8 | 2.39 / 5.20 | 15.1 / 8.8 / 5.3 | 110 | 13.4 | -58.5 | 355.1 | no: skin |
| c_swR71c3_70_r100 | (c) 100 mm rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 70 mm | 14.25 | 13.7 / 13.3 / 12.8 | 2.75 / 6.81 | 12.6 / 6.3 / 1.4 | 130 | 13.4 | -55.9 | 357.7 | no: skin |
| c_swR71c3_70_r110 | (c) 110 mm rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 70 mm | 13.61 | 13.1 / 12.7 / 12.2 | 2.73 / 6.56 | 14.2 / 8.2 / 4.0 | 120 | 13.4 | -50.3 | 363.3 | yes |
| c_swR71c3_70_L380 | (c) 380 mm long rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 70 mm | 14.09 | 13.6 / 13.1 / 12.6 | 2.57 / 6.11 | 15.2 / 9.0 / 5.5 | 110 | 13.4 | -54.8 | 358.8 | no: skin |
| c_swR71c3_70_L340 | (c) 340 mm long rail, sandwich strip: 200 g twill / 3 mm R71 / twill, 70 mm | 15.09 | 14.5 / 14.0 / 13.4 | 2.40 / 5.71 | 14.8 / 8.2 / 4.7 | 110 | 13.4 | -64.9 | 348.7 | no: skin |
| c_swR110c2_80_r100 | (c) 100 mm rail, sandwich strip: 200 g twill / 2 mm R110 / twill, 80 mm | 13.96 | 13.5 / 13.0 / 12.6 | 3.48 / 4.31 | 11.7 / 5.6 / 0.7 | 130 | 12.4 | -49.2 | 364.4 | no: skin |
| c_swR110c2_80_r110 | (c) 110 mm rail, sandwich strip: 200 g twill / 2 mm R110 / twill, 80 mm | 13.24 | 12.8 / 12.3 / 11.9 | 3.46 / 4.13 | 13.4 / 7.5 / 3.3 | 120 | 12.4 | -43.6 | 370.0 | yes |
| c_swR110c2_80_L380 | (c) 380 mm long rail, sandwich strip: 200 g twill / 2 mm R110 / twill, 80 mm | 13.53 | 13.0 / 12.6 / 12.1 | 3.25 / 3.78 | 14.5 / 8.5 / 5.0 | 110 | 12.4 | -48.7 | 364.9 | yes |
| c_swR110c2_80_L340 | (c) 340 mm long rail, sandwich strip: 200 g twill / 2 mm R110 / twill, 80 mm | 14.48 | 13.9 / 13.4 / 12.9 | 3.04 / 3.53 | 14.1 / 7.7 / 4.2 | 110 | 12.4 | -59.5 | 354.1 | no: skin |
| c_swR71c2_80_r100 | (c) 100 mm rail, sandwich strip: 200 g twill / 2 mm R71 / twill, 80 mm | 14.09 | 13.6 / 13.1 / 12.7 | 1.90 / 4.34 | 11.6 / 5.5 / 0.6 | 130 | 12.4 | -53.9 | 359.7 | no: skin |
| c_swR71c2_80_r110 | (c) 110 mm rail, sandwich strip: 200 g twill / 2 mm R71 / twill, 80 mm | 13.37 | 12.9 / 12.5 / 12.0 | 1.89 / 4.16 | 13.3 / 7.4 / 3.2 | 120 | 12.4 | -48.3 | 365.3 | yes |
| c_swR71c2_80_L380 | (c) 380 mm long rail, sandwich strip: 200 g twill / 2 mm R71 / twill, 80 mm | 13.68 | 13.2 / 12.7 / 12.2 | 1.77 / 3.81 | 14.4 / 8.4 / 4.9 | 110 | 12.4 | -53.0 | 360.6 | yes |
| c_swR71c2_80_L340 | (c) 340 mm long rail, sandwich strip: 200 g twill / 2 mm R71 / twill, 80 mm | 14.64 | 14.1 / 13.6 / 13.0 | 1.66 / 3.56 | 14.0 / 7.6 / 4.1 | 110 | 12.4 | -63.3 | 350.3 | no: skin |


### (a2) the spreader moved to the wearer face as a framesheet (and (d), thinner core)

Sheet clipped to the stays' wearer face, x ±155 or ±175, z 195–470 (it cannot go lower: the lumbar pan and its z 190
top flange and the lumbar struts occupy the stays' wearer side below that). The rail below z 195 keeps short 80 mm
twill backers (35.5 g pair). The air column is what the gutter needs for walk ≥ 3 mm, factored ≥ 0 and lean ≥ 0,
iterated on the foundation.

| key | sheet | FPF SF (fact) | fatigue SF (walk) | sandwich local SF | peak skin kPa | aged foam needed for air mm (new) | mass change g | back system g | passes |
|---|---|---:|---:|---:|---:|---|---:|---:|---|
| a2_fs_c7_w310 | twill / 7 mm R110 / twill, 310 x 275 mm (z 195-470) | 0.94 | 0.85 | 2.28 | 27.9 | 35.9 (40.8) | +14.6 | 428.2 | no: fpf, fatigue, skin |
| a2_fs_c4_w310 | twill / 4 mm R110 / twill, 310 x 275 mm (z 195-470) | 0.54 | 0.50 | 1.40 | 32.2 | 47.4 (53.9) | +26.4 | 440.0 | no: fpf, fatigue, skin |
| a2_fs_c7_w350 | twill / 7 mm R110 / twill, 350 x 275 mm (z 195-470) | 0.91 | 0.82 | 2.28 | 24.7 | 32.7 (37.2) | +19.5 | 433.1 | no: fpf, fatigue, skin |
| a2_fs_c4_w350 | twill / 4 mm R110 / twill, 350 x 275 mm (z 195-470) | 0.53 | 0.49 | 1.40 | 30.9 | 45.6 (51.8) | +32.6 | 446.2 | no: fpf, fatigue, skin |

Why the framesheet fails: on the wearer face the sheet no longer spans stay to stay with the branches under it; it
floats on soft foam, so a bone end in the gutter or near its free top / bottom edge bends it into the back. Worst
positions are the free edges (z 207 and 458, FI 1.06 at 7 mm); at mid-height (z 330) it would pass first ply (FI 0.60)
but still needs **22 mm aged (25 mm new) rail foam** for air and gives 12.7–13.9 kPa. Best case, with edge tubes added
(+21 g) to fix the edges, it still needs ~25 mm rails (+48 g foam): net about −15 g against −44.6 g for the sandwich
strip, with the gutter air channel halved and a lumbar-zone clash. **A thinner core (d) makes it worse** (4 mm: FPF
0.54, fatigue 0.50, core shear 1.40, 54 mm of foam). For (b) and (c) the spreader's span and supports do not change,
so (d) does not apply: the 7 mm core is set by the sheet's own FPF / fatigue / sandwich-local checks, which do not
depend on the rail (full re-check above: identical SFs).

### Reading the rail table

- **(a1)** A bag-side extension never touches the rail: the stay sits between. As "no backer" the rail gives
  **30.6 kPa** and the air columns go negative (the 1 mm strip thickness is lost). Fails.
- **(b) thin twill (0.5 mm)**: half the mass, one eighth of the stiffness: 18 kPa and the strip itself fails first ply
  (SF 0.74). A plain plate cannot be thinned.
- **(b) sandwich strips** are the lever. A 3 mm core with 0.22 mm skins is **13×** as stiff in lateral bending as the
  1 mm plate (D 66,600 vs 5,180 N·mm) at **56 %** of the mass. Once the strip is that stiff the pressure under it is
  nearly flat (screen 1) and the width sets the peak: 60 mm fails (14.1–14.3), 70 mm passes (13.2–13.5), 80 mm passes
  with more margin (12.6–12.9). Core shear governs the strip (SF 1.9–5.0); the core-crush check under the stay uses an
  8 mm contact width (ASSUMPTION, as the spreader's crown check).
- **(b) printed PAHT-CF ribbed strip**: heavier than today (+12 g) and fails fatigue (0.65): hot/wet PAHT is 25× softer
  than carbon. The same applies to **reshaping the H1 stays to carry the rail** (a printed flange is this strip fused
  to the stay, and it would reopen the frame print): not pursued.
- **(c) narrower rails** with a sandwich strip: 110 mm passes (−5.7 g more, gutter 120 mm, skin margin 0.39 kPa);
  100 mm fails (13.9–14.3). **Shorter rails** pass at 380 mm in the uniform-along-rail model, but that model is the
  weakest link here (§6): it cannot say which 40 mm of rail carry less, and the lumbar-pad overlap suggests the lower
  rail may carry *less* than it is credited, not more. Not recommended until the T9 pressure-mat test.
- The lightest passing row, `c_swR71c2_80_L380` (360.6 g), needs a 2 mm R71 core (not a stock sheet; 3 mm is the
  thinnest offered) and a shorter rail; it saves 8.4 g more than the recommendation.

## 5. Recommendation (task 5)

**Replace BP-08 with a sandwich strip, keep everything else.** `b_swR71c3_70`:

| item | today | recommended |
|---|---|---|
| BP-08 rail backer, pair | 1.02 mm 2×2 twill plate, 80 × 420, 102.8 g (model) / 102.5 g (panels.yaml) | 200 g twill / 3 mm ROHACELL 71 IG-F / 200 g twill, 70 × 420 × 3.44 mm, sealed edges, **57.6 g** |
| skin, CG 190 (15 / 19 / 23 in runs) | 13.76 (13.3 / 12.8 / 12.4) kPa | **13.29 (12.8 / 12.4 / 12.0) kPa** |
| skin, full spreader check | 13.77 kPa | **13.31 kPa** (at a clip) |
| strip SF factored / fatigue | 1.70 / 1.60 | **2.73 / 6.48** (core shear governs) |
| spreader FPF / fatigue / sandwich | 1.25 / 1.09 / 1.11 | 1.25 / 1.09 / 1.11 (unchanged) |
| air walk / factored / lean, full check (strip thickness not in the model) | 13.0 / 6.9 / 3.4 mm | **13.2 / 7.3 / 3.8 mm** |
| same, with the 2.4 mm thicker stack credited | 13.0 / 6.9 / 3.4 mm | 15.6 / 9.7 / 6.2 mm |
| rail stack (foam + strip) | 11.0 mm | 13.4 mm (sleeve +2.4 mm girth, +0.6 g) |
| back system | 413.6 g (14.6 oz) | **369.0 g (13.0 oz), −44.6 g (−1.6 oz)** |

Optional, owner's call: the 110 mm rail with the same strip (`c_swR71c3_70_r110`) saves 5.7 g more (363.3 g) and widens
the air gutter to 120 mm, but changes BP-02 / BP-05 / BP-01 patterns and leaves 0.39 kPa of margin.

**Clearances.**
- H1 frame: the strip sits in the sleeve on the stay's wearer face, x 80–150. H1's bosses never stand proud of the
  wearer face (`frame_h1.md` §3.2), so nothing changes there; the stack is 2.4 mm thicker, which moves the back away
  from the frame (more air, above).
- Hipbelt pad seat: the rail band (x 55–175, z 50–470) overlaps the lumbar pan / pad seat in plan at x 55–125,
  z 50–190. At z 119 the rail's wearer face is at y −22.3 today and **−24.7** recommended; the pad-seat stack face is at
  y −27 (`corrie.PAD_SEAT` zone_y), so the pad seat still stands **2.3 mm** proud of the rail face (4.7 today) and the
  rail does not reach it. The sandwich strip ends at z 470 like today and does not enter the 70 mm pad-seat channel.
- Spreader: bag side, unchanged; its z 119 stand-off pads and clips are not touched.

**Build steps (owner, in-house, same kit as the spreader):**
1. Cut one 160 × 440 mm blank of 3 mm ROHACELL 71 IG-F and two 200 g 2×2 twill plies 170 × 450 mm.
2. Lay up twill / core / twill (0° along the strip), wet out with the spreader's laminating epoxy, vacuum-bag,
   cure as the spreader (cut/spreader/README.md process).
3. Cut two strips **70 × 420 mm** with a fine-tooth or diamond saw / router; R10 corners; sand edges.
4. Seal the cut core edges with two brushed coats of epoxy (0.3 mm, as the spreader edge seal).
5. Lightly radius (2 mm) the long edges of the wearer skin so the strip edge does not print through 10 mm of foam.
6. Slide into the BP-05 sleeve between the stay and the foam, centred on the stay line; two hot-melt dots to the foam,
   as BP-08 today. Sleeve girth +2.4 mm (cut BP-05 145 wide instead of 140, or check the existing sleeve fits 13.4 mm).
7. Weigh the pair: 57.6 g expected (pass ≤ 62 g).

## 6. Assumptions that govern

- ASSUMPTION: the strip's core shear stiffness S = G_c d²/t_c (Zenkert) and Timoshenko strip behaviour in the rail
  section. Settles with: a 3-point bend of a 70 × 200 mm offcut on a 100 mm span to 30 N; deflection within 15 % of
  the model's.
- ASSUMPTION: the stay bears on ≥ 8 mm of strip width (core crush SF 3.8). Settles with: pressure-indicating film
  between a printed stay segment and the strip at 2.5 N/mm.
- ASSUMPTION (inherited, `spreader.py` / `back_rail.py`): tissue 60 kPa over 25 mm, aged L200, the meat force spread
  uniformly over the 420 mm rail length. Settles with: T9-day pressure mat, rev C meat case, at 15 / 19 / 23 in.
- ASSUMPTION: for rows other than the recommendation, air is today's full check shifted by rail indentation, strip
  thickness, aged foam and gutter bulge. The full re-run of the recommendation agrees to 0.0 mm once the strip
  thickness, which `spreader.clearance_field` does not model, is added back (13.2 + 2.4 = 15.6 mm walking).
- ASSUMPTION (framesheet only): sheet held at z 195–470 by the lumbar pan below; meat share spread uniformly; foundation
  without foam shear (slightly conservative on skin). None of these changes the verdict: it fails at mid-height on air
  alone.
- Recommendation rule margins (0.2 kPa, 110 mm gutter) as `back_rail.py`.

## 7. Stand-off pad thickness (BL-015 question)

**4.9 mm is right for today's frame; 4.5 mm is a stale comment.** The pad height in code is
`spreader.stay_r(260) − spreader.stay_r(119)` = 13.94 − 9.07 = **4.87 mm** (used by `spreader.fittings_mass_g` and in
`cut/spreader/README.md`, 16 × 10 × 4.9 mm). The "4.5 mm" in `frame_h1.md` comes from the comment at
`spreader.py` lines 340–343 ("the stay is r 9 there, 4.5 mm below the sheet"), which rounds the stay radius to 13.5.
On H1, with the stay 4.0 mm fuller on the bag side at z 119 (`frame_h1.md` §4, interface keep-outs), the pad becomes **4.9 − 4.0 =
0.9 mm**, not 0.5 mm, if that 4.0 mm is right; it should be measured on the H1 STL before cutting. The recommendation
here does not touch the pads.

## 8. Found, not fixed

- **The rail's lower 140 mm may not bear on the back.** The rails run z 50–470; the lumbar pan / pad seat occupies
  x ±125, z 50–190 and its face (y −27) stands 2–5 mm proud of the rail face. If the rails bear only above z 190 (280 mm),
  the same model gives **17.7 kPa today and 17.1 kPa recommended**, both over 14. The lumbar pad then carries part of
  the forward meat force, which the skin model also ignores, so the two errors partly cancel. Owner of the skin model
  (structural) + pack-designer: settle with the T9 pressure mat before release.
- The released BP-08 strip had never had a strength check. It passes (SF 1.70, fatigue 1.60).
- `spreader.py` lines 340–343: stale "4.5 mm" comment (§7).
- `back_rail.mass_g` and `panels.yaml` book BP-08 at 102.8 / 102.5 g (rounding of the 1.02 mm thickness); harmless.

## Screenshots

- `outputs/screens/20261110_BL005_1.png`: skin pressure over one rail, today vs recommended, and the section at the bone.
- `outputs/screens/20261110_BL005_2.png`: rail sections and the back-system mass by layer.
