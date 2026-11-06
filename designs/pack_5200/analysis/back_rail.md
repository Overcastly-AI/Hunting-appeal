# Back-rail skin pressure at the rev C meat case

Owner: pack-designer, 2026-11-06. Code: `huntkit/gendesign/back_rail.py` (`python -m huntkit.gendesign.back_rail`). Numbers: `analysis/back_rail_results.json`. Model: the rail-and-tissue model of `huntkit/gendesign/spreader.py` (`rail_backed`, Hetenyi spread along the stay), unchanged; only the rail build is a parameter here. Comfort limit 14 kPa peak at the 1.6 g walking peak (Golriz et al. 2017, `back_comfort.md`). Load: HA-LS-1 rev C C5, meat CG 190 mm, worst bone end on the production spreader `sw110c7d` (204 N side reaction, bone at position 'at a clip'). `spreader._SKIN_CACHE` is cleared before and after every full evaluation.

## Decision

- **Widen the stay rails 100 -> 120 mm and the backer strips 60 -> 80 mm** (same 10 mm Minicel L200-class XLPE, same 1 mm 2x2 twill backer, same 420 mm length, still centred on the stay lines).
- Peak skin pressure at the rev C meat case: **15.4 -> 13.8 kPa** (limit 14; full `spreader.evaluate`, worst bone position 'at a clip'). Meat only 12.0 -> 10.6 kPa.
- Mass **+37.0 g** for the pair (104.0 -> 141.0 g: foam, backer, the wider sleeves and mesh). Cost **+4.68 USD** per pack (records' prices).
- Air gutter between the rails 130 -> 110 mm. Air to the skin, walking: 9.6 -> 13.0 mm (limit 3); factored 2.9 -> 6.9 mm (limit 0). The sheet checks do not change (FPF SF 1.25, fatigue 1.09, sandwich 1.11).
- **Found on the way: the backer strip is in the model but not in the build.** Every skin number since 2026-11-04 (13.0 kPa at rev B) assumes a 1 mm twill strip between each stay and its foam rail (`spreader.RAIL_DESIGN`). The released v3.1 patterns, `panels.yaml` and the weight table have only the foam. As patterned the rail gives **49 kPa** at the rev C meat case. The strips are now a cut part, BP-08 (77 g for the pair at 60 mm, 103 g at 80 mm), and are in the weight table.

## Options (same model, worst bone, CG 190 mm)

Choice rule: lightest with peak <= 13.8 kPa and gutter >= 110 mm (margin and gutter are ASSUMPTIONs below).

| key | build | peak kPa | meat share without the bone kPa | gutter mm | mass change g | cost change USD | <= 14 | meets the rule |
|---|---|---:|---:|---:|---:|---:|---|---|
| r100_nobacker | as patterned in v3.1 and booked: 100 mm rail, NO backer strip | 48.94 | 34.49 | 130 | -77.1 | -12.60 | no | no |
| r100_b60 | current: 100 mm L200 rail, 60 mm 1 mm twill backer | 15.42 | 9.03 | 130 | +0.0 | +0.00 | no | no |
| r100_b60_f12 | 100 mm rail, 12 mm L200 foam | 15.23 | 8.91 | 130 | +5.4 | +0.00 | no | no |
| r100_b60_f14 | 100 mm rail, 14 mm L200 foam | 15.08 | 8.82 | 130 | +10.8 | +0.00 | no | no |
| r100_b70 | 100 mm rail, 70 mm backer | 14.97 | 8.73 | 130 | +12.9 | +2.10 | no | no |
| r100_b60_f16 | 100 mm rail, 16 mm L200 foam | 14.95 | 8.74 | 130 | +16.1 | +0.00 | no | no |
| r100_b60_L460 | 100 mm rail, 460 mm long (z 30-490) | 14.64 | 8.24 | 130 | +16.9 | +1.45 | no | no |
| r110_b70 | 110 mm rail, 70 mm backer | 14.42 | 8.37 | 120 | +18.5 | +2.34 | no | no |
| r100_b60_t1.32 | 100 mm rail, 60 mm 1.3 mm backer | 15.03 | 8.77 | 130 | +22.7 | +0.00 | no | no |
| r120_b70 | 120 mm rail, 70 mm backer | 14.12 | 8.18 | 110 | +24.2 | +2.58 | no | no |
| r100_b80 | 100 mm rail, 80 mm backer | 14.78 | 8.61 | 130 | +25.7 | +4.20 | no | no |
| r100_b60_eva | 100 mm rail, 4 mm EVA 45C over 6 mm L200 | 15.07 | 8.79 | 130 | +26.2 | +0.00 | no | no |
| r100_b60_eva30 | 100 mm rail, 10 mm EVA 30C (softer grade) | 15.59 | 9.13 | 130 | +27.7 | +0.42 | no | no |
| r115_b75 | 115 mm rail, 75 mm backer | 14.03 | 8.12 | 115 | +27.8 | +3.51 | no | no |
| r130_b70 | 130 mm rail, 70 mm backer | 13.89 | 8.03 | 100 | +29.8 | +2.83 | yes | no |
| r110_b80 | 110 mm rail, 80 mm backer | 14.16 | 8.20 | 120 | +31.4 | +4.44 | no | no |
| r115_b80 | 115 mm rail, 80 mm backer | 13.90 | 8.04 | 115 | +34.2 | +4.56 | yes | no |
| **r120_b80** | 120 mm rail, 80 mm backer | 13.76 | 7.94 | 110 | +37.0 | +4.68 | yes | yes |
| r100_b90 | 100 mm rail, 90 mm backer | 14.73 | 8.58 | 130 | +38.6 | +6.30 | no | no |
| r110_b90 | 110 mm rail, 90 mm backer | 14.03 | 8.12 | 120 | +44.2 | +6.54 | no | no |
| r100_b100 | 100 mm rail, 100 mm backer | 14.73 | 8.57 | 130 | +51.4 | +8.40 | no | no |
| r130_b90 | 130 mm rail, 90 mm backer | 13.23 | 7.61 | 100 | +55.5 | +7.03 | yes | no |
| r120_b100 | 120 mm rail, 100 mm backer | 13.49 | 7.77 | 110 | +62.7 | +8.88 | yes | yes |
| r100_b90_t1.32 | 100 mm rail, 90 mm 1.3 mm backer | 14.08 | 8.15 | 130 | +72.6 | +6.30 | no | no |
| r100_b60_t2.04 | 100 mm rail, 60 mm 2 mm backer | 14.75 | 8.59 | 130 | +77.1 | +0.00 | no | no |
| r100_b90_t2.04 | 100 mm rail, 90 mm 2 mm backer | 13.60 | 7.84 | 130 | +154.2 | +6.30 | yes | yes |

Reading the table:

- **Foam grade and thickness hardly move the peak** (16 mm L200 still 15 kPa; EVA 45C over L200 15.1). The tissue column (60 kPa over 25 mm) is far softer than any closed-cell foam on file, so the pressure is set by how wide the stiff part spreads the stay load, not by the foam. PU memory foam (`pu_memory_foam`, 3 kPa at 25 %, open cell, 500 % water uptake) would bottom and soak blood and sweat; not a candidate.
- **A wider backer alone saturates at about 14.7 kPa**: inside a 100 mm rail there is no foundation left to spread onto. A stiffer backer (2 mm twill) passes only at 90 mm width and costs about 150 g.
- **The foundation width is the lever.** A 120 mm rail with an 80 mm backer keeps the same 20 mm soft foam margin each side of the hard strip as today (no hard edge printing into the back) and passes with the most margin for its mass. 115 / 80 is about 3 g lighter but leaves only 0.1 kPa. 130 / 70 is about 7 g lighter and passes, but narrows the air gutter to 100 mm and puts the rail edge at x +/-180, onto the rib curve.
- **A longer rail is not credited.** The model spreads the meat force uniformly over the rail length; in reality the overturning pressure peaks low (z 60-330) and the back curves away above the shoulder blades, so length above z 470 would not carry its share.

## Peak vs meat CG

| meat CG mm | r100_b60 | r120_b80 |
|---:|---:|---:|
| 150 | 12.9 | 11.5 |
| 165 | 13.8 | 12.4 |
| 175 | 14.5 | 12.9 |
| 181 | 14.9 | 13.3 |
| 190 | 15.4 | 13.8 |
| 205 | 16.4 | 14.6 |
| 223 | 17.5 | 15.6 |

Soft-tissue sensitivity (20 kPa column): current 12.8 kPa, chosen 11.1 kPa. The 205 and 223 mm rows are bag-case CGs (C1); skin is a meat-case limit, shown for reference. The chosen rail keeps 14 kPa up to about 194 mm.

## Mass and cost (both rails)

| item | current g | chosen g |
|---|---:|---:|
| foam | 26.9 | 32.3 |
| backer | 77.1 | 102.8 |
| sleeve extra | 0.0 | 2.4 |
| mesh extra | 0.0 | 3.5 |
| total | 104.0 | 141.0 |

Cost: current 15.26 USD, chosen 19.94 USD (foam `xlpe_foam_l200` 15 USD/m2, backer `cfrp_plate_0_90_woven` 250 USD/m2 bought 1 mm plate, sleeve `robic_210d_ripstop`).

## Pattern-maker hand-off

- **BP-02 stay-rail foam x2**: 100 x 420 -> **120 x 420 x 10 mm**, buy Minicel L200 class (the comfort model uses record `xlpe_foam_l200`; the `panels.yaml` row keeps the generic `xlpe_foam` id, the same L200 class, so the frame studies that read it do not move). Die-cut, 3 mm bevel on the long edges.
- **BP-08 rail backer x2 (new piece)**: **80 x 420 x 1.0 mm** 2x2 twill carbon plate, water-jet, R10 corners, edges sanded. Sits in the sleeve between the stay and the foam, centred on the stay line. Hot-melt two dots to the foam so it cannot shift in the sleeve.
- **BP-05 rail sleeve x2**: 120 x 420 -> **140 x 420** (rail + 20), top open, same seam allowances.
- **BP-01 back panel mesh**: 350 -> **370 mm** wide x 440 (the sleeve outer edges at x +/-185 stay on the panel); sleeve stitch lines move to stay CL +/-70. Stay-clip drill holes keep their 20 mm inset from the new edges.
- **check**: the hipbelt wing and shoulder-strap roots must clear the wider mesh edge (x +/-185); flag any overlap.

## Assumptions

- Rail model as spreader.py (structural-fea-engineer): stay hot/wet PAHT beam, aged L200 (12 % set), tissue 60 kPa over 25 mm (20 kPa sensitivity), 1-D lateral section, flat back under the rail. No new physics here.
- Foams without a compression curve (EVA 30C) use the L200 curve shape scaled to their 25 % point, as spreader.eva_curve.
- Wider rails stay centred on the stay line; the model puts the stay load at the strip centre.
- Choice margin 0.2 kPa under the limit (model resolution) and an air gutter of at least 110 mm (85 % of today's 130 mm channel). A pressure-mat check on the first prototype (T9 day, meat case) replaces both.
- Sleeve = rail + 20 mm; mesh grows with the outer sleeve edge (2 x the width change x 460 mm of 380 gsm mesh).
- Backer price from cfrp_plate_0_90_woven (estimate, 250 USD/m2); stiffness from cfrp_t300_3k_woven_epoxy_ply, as the record.

## Screenshots

- `outputs/screens/20261106_backpanel_1.png`
- `outputs/screens/20261106_backpanel_2.png`
- `outputs/screens/20261106_backpanel_3.png`
