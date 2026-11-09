# Held fabric swaps: material evidence and verdicts (O-3, O-4, O-5, O-6, O-15)

Owner: materials-engineer. Date 2026-11-09. Inputs: `bag_weight_plan.md` (options), `weight_pass_corrie.md`
(CORRIE rows B-8, B-9, C-5, C-6, and the O-6 note), `bag_attachment.md` / `huntkit/gendesign/attach_system.py`
(B-18 seam), `panels.yaml` (B-11). Records: `data/materials/` (all values carry a URL, or are marked ASSUMPTION).
Tests: `tests/test_materials_fabric_swaps.py`. Units: 1 lbf = 4.448 N; 1 oz/yd² = 33.9 g/m².

## Summary

| Swap | CORRIE row | Verdict | Mass saving on CORRIE (new records) | Key number |
|---|---|---|---|---|
| O-3 collar 100D Robic -> 70D ripstop | B-9 | **Proceed** (RBTR 1.9 oz stock); C0 version only after a tear check | **~15 g** (was 9.1 g) | 70D tear 51.6 / 37.4 N (D1424) >= the 35 N the plan asked for |
| O-4 body 330D -> ULTRAGrid | B-8 | **Proceed after the owner sees a swatch** (the abrasion gate is met) | **~41 g** (was 21.6 g) | ULTRAGrid Taber 1100 cycles (Challenge, D3884) vs the 330D record's 800 |
| O-5 bottom 500D -> ULTRA 200X | C-5 | **Proceed after PT-3 plus a 50 mm strip test** | ~7.0 g (was 7.5 g) | needs strip >= 36.8 N/mm (1840 N/50 mm) to keep SF 2.31; >= 23.9 N/mm for SF 1.5 |
| O-6 camo shards on 300D printable | (none left) | **Material OK, but nothing to swap on CORRIE.** Close as moot; keep the record for future accent trims | 0 g on CORRIE (B-2 / B-4 already remove the targets) | HyperD 300: 133 gsm, tear 31.6 / 24.5 N: trim only |
| O-15 lash tabs Hypalon -> TPU 840D | C-6 | **Proceed after the 5-sample slot pull test (>= 450 N each), and confirm the slot orientation first** | 6.2 g (unchanged) | if the 25 mm slot runs across the 30 mm tab, the 2.5 mm side ligaments give about 320 N (TPU) / 256 N (Hypalon), below 450 N for BOTH |

## Record changes that move other numbers (re-run the weight pass)

These records changed from estimates to published values. The weight-pass, bag-plan and BOM scripts read them, so
their numbers move on the next run. Nothing was re-run here, because other agents own those files.

| Record | Field | Was (estimate) | Now (published) | Source |
|---|---|---|---|---|
| `robic_100d_ripstop` | areal_density_gsm | 90 | **125** (UTS-coated stock, 3.7 oz/yd²) | RBTR listing |
| `ultragrid_210d_uhmwpe_ripstop` | areal_density_gsm | 155 | **132** | Challenge EcoPak guide, Extremtextil |
| | abrasion_taber_cycles | (none) | **1100** (ASTM D3884) | Challenge EcoPak guide |
| | roll / usable width | 1422 / 1397 | 1500 / 1475 | Extremtextil, EcoPak (150 cm) |
| `challenge_ultra_200` | areal_density_gsm | 125 | **133** (200X; listings range 119-155) | Extremtextil (maker spec) |
| | tear warp / weft | 250 / - | **459 / 593 N** (D2261) | EcoPak, Extremtextil, Rockywoods |
| | abrasion_taber_cycles | 2000 | **4400** (D3884) | same |
| | tensile_*_n_50mm | (none) | 3000 **ASSUMPTION** (not published anywhere) | yarn-count basis in the record |
| | cost_usd | 50 / yd | 60 / yd | RBTR $30 per half yd |

Rough mass effect, from `panels.yaml` cut areas: Robic +35 gsm × ~0.88 m² ≈ **+31 g** pack-wide (the biggest change);
ULTRA 200X +8 gsm on every ULTRA piece; ULTRAGrid −23 gsm where it is already used. The shock-cord record adds
**+3.5 g per metre** of shock cord over the 2 mm Dyneema proxy (6.0 vs 2.5 g/m).

## O-3. Roll-top collar B-06: 100D Robic -> 70D ripstop

New record `nylon_ripstop_70d` (RBTR 1.9 oz Coated Ripstop Nylon data sheet):
92 gsm finished (60 gsm base), tear 51.6 / 37.4 N (ASTM D1424), grab 242 / 174 N (D5034), seam 233 / 266 N (D1683),
hydrostatic head 8000 mm new and 1000 mm after 10 washes, PU back, fluorinated DWR face, UV and FR finish, $10.75/yd.

- Mass: the plan assumed 70 gsm against a 90 gsm Robic. Both were wrong. The fabrics are 92 vs **125** gsm (Robic
  corrected), so the saving on CORRIE's collar (B-9 area 9.1 g / 20 gsm = 0.455 m²) is **33 gsm × 0.455 = ~15 g**.
  If the Robic you actually buy weighs 90 gsm (older PU stock), the swap saves **nothing** (+0.9 g). **Weigh a Robic
  swatch before cutting.**
- Strength: tear 51.6 / 37.4 N meets the plan's 35 N threshold. The Robic tear (45 / 40 N) is an unsourced estimate,
  so the 70D is at least as good on the data we have. Grab 242 N is far above a collar's roll load.
- Hunting: fluorinated DWR and an FR finish on the RBTR stock. The PFAS-free alternative is Extremtextil Robic Ocean
  70den UTS C0 (100 gsm, 2000 mm, tear not published): saving ~11 g, after a tongue-tear check on a swatch.
- **Verdict: PROCEED** with the RBTR 1.9 oz, after weighing the Robic stock. Take the C0 Extremtextil cloth only after a
  5-sample tear check that meets >= 35 N.

## O-4. Body (gussets, U-surround, door, hinge band, wings): 330D CORDURA -> ULTRAGrid

`ultragrid_210d_uhmwpe_ripstop` now carries Challenge's published **Taber 1100 cycles (ASTM D3884)**, 132 gsm, and
a tongue tear reported as "does not tear" (the UHMWPE grid stops the tear).

- Plan criterion (bag_weight_plan.md O-4): "YES if a supplier abrasion figure is >= the 330D (800 Taber cycles)". It
  is: **1100 >= 800**.
- Calibration (do not over-read it): the 330D 800 figure is an unsourced estimate. On Challenge's own scale, 500D
  CORDURA sits at about 1800-2000 cycles (the guide calls EPX600 at 2000 "comparable to 500d Cordura", and ULTRA100 at
  3600 "twice" 500D). The records' 330D/500D ratio (800/1500 = 0.53) puts 330D at about 950-1070 on that scale. So
  ULTRAGrid **matches** 330D on abrasion. It is not clearly better, and it is still ~55-60 % of 500D.
- Mass: 180 -> 132 gsm = 48 gsm × 0.864 m² (B-8 area) = **~41 g** saved (the weight pass booked 21.6 g at 155 gsm).
- Tear: higher than 330D (does not tear vs 90 / 80 N). Waterproofing 1500 vs 1000 mm. Same PU hydrolysis class.
- Sewing: the UHMWPE grid yarns are slippery. Use a tighter SPI and bartacks; no seam on file for the grid at the wing
  roots. B-8 says that tear going up means no SF falls.
- **Verdict: PROCEED after the owner approves a swatch** (the visible grid on the solid colourway). The abrasion
  evidence is in. Optional extra: a side-by-side Martindale/rock-rub of 330D vs ULTRAGrid on the owner's machine,
  since the parity estimate is inferred.

## O-5. Bag bottom B-05: 500D CORDURA -> Challenge ULTRA 200X

`challenge_ultra_200`: tear **459 / 593 N** (D2261) vs 500D 130 / 110 N; Taber **4400** vs 1500; waterproof film.
Buy **200X**: ULTRA 200 is discontinued.

- The governing check is the HE / B-18 bag-on seam: `attach_system.patch_seam(80, B-05, B-18 Hypalon)` =
  0.8 × 80 mm × min(strip B-05, strip Hypalon). On 500D the strip is 1150 / 31.25 = 36.8 N/mm, so 2355 N and
  **SF 2.31** on the 1019 N factored load.
- ULTRA 200's tensile / grab / strip strength is **not published** by Challenge or any retailer (searched 2026-11-09).
  The record carries 3000 N/50 mm (60 N/mm) as an ASSUMPTION, from yarn count × blend tenacity × 0.6 weave efficiency.
  That matches the clothsim value. At 60 N/mm, Hypalon (51.2 N/mm) governs and the seam rises to 3277 N (SF 3.22).
- Break-even values for a strip test:
  - **>= 36.8 N/mm (1840 N per 50 mm)**: the seam SF does not drop below today's 2.31.
  - **>= 23.9 N/mm (1195 N per 50 mm)**: SF 1.5, the PT-3 proof (1530 N / (0.8 × 80 mm)).
  - The published tear (3.5-5× the 500D) makes a strip below 37 N/mm unlikely, but tear is not strip strength.
- Mass: 255 -> 133 gsm on 0.0577 m² = **~7.0 g** (7.5 g booked at 125 gsm). Extremtextil advises backing point loads
  with an extra layer; B-18 already does that at the hinge eyes.
- **Verdict: PROCEED after PT-3** (5 of 5 hold at 1530 N, swatches built without binding per S-03) **plus a 50 mm
  strip test** (ISO 13934-1 or ASTM D5035, 5 warp + 5 weft on ULTRA 200X). Pass: mean >= 1840 N/50 mm, minimum >= 1195.
  If the strip lands between the two, the swap is still allowed: SF falls but stays >= 1.5. Report it to the
  structural-fea-engineer.

## O-6. Camo shards SH-02..04 on a 300D printable base

New record `polyester_300d_printable` (RBTR HyperD 300, custom digital print): 133 gsm (base 111), 100 % polyester,
tear 31.6 / 24.5 N (D1424), grab 351 / 236 N, seam 189 / 230 N, 19000 mm new / 1000 mm after 10 washes, light
fastness 4, print shrinkage < 1 %, printed $30.25/yd, 1 yd minimum (original artwork, no mill MOQ).

- Against the 630D printable record (290 gsm): −157 gsm (the plan assumed 170 gsm for the 300D, so the real cloth is
  lighter than planned).
- Tear 32 / 25 N is low (630D record 120 / 100 N). Use it only for trims that carry no load and see little wear,
  never as an abrasion doubler. SH-01 stays 630D.
- On CORRIE the targets are gone: weight_pass_corrie.md says O-6 would only touch the pouch top and the roll-hem
  band, and B-2 (delete SH-03 hem band) and B-4 (pouch top to 330D) remove both. The remaining camo (kick plates, wing
  bars, door garages) is in wear zones and should stay 630D.
- **Verdict: no CORRIE swap (moot; 0 g).** The material itself is approved for future accent trims, after a printed
  swatch passes the camo-designer's colour, UV-brightener and NIR check. The ink NIR is not published, and the stock
  DWR is fluorinated.

## O-15. Lash tabs B-11: Hypalon -> laser-cut TPU-coated 840D

Records: `tpu_coated_nylon_840d` (grab 2400 / 2000 N, estimate) and `hypalon_coated_nylon` (1800 / 1600 N, estimate).
No published slot or bearing data exists for either. B-11 in panels.yaml: 30 × 50 mm, laser-cut slot 25 × 5 mm,
8 per pack, rated to the 450 N buckle class.

- Ligament check (strip = min grab / 31.25, the attach_system convention: TPU 840D 64.0 N/mm, Hypalon 51.2 N/mm):
  - **Slot across the 30 mm width**: two 2.5 mm side ligaments, so **TPU ~320 N, Hypalon ~256 N, both under 450 N.**
  - **Slot along the 50 mm length**: two 12.5 mm end ligaments, so TPU ~1600 N, Hypalon ~1280 N. Both are fine.
  - panels.yaml does not give the slot orientation (ASSUMPTION either way).
- **Verdict: PROCEED after the 5-sample slot pull test** (each >= 450 N, laser-cut edge, as built). **First confirm the
  slot runs along the 50 mm length.** If it runs across the width, widen the tab to >= 40 mm (7.5 mm ligaments,
  ~960 N in TPU). That applies to the current Hypalon tab too. FLAG to the pack-designer. Quietness drops 4 -> 2
  (records), so the owner trades 6 g for a stiffer, louder tab edge.

## Supporting records added (same change)

- `insert_heatset_brass_m5` (hardware): ruthex M5 × 9.5, OD 7.1 mm, hole 6.4 mm, wall >= 2.6 mm. Published
  references: Sculpteo MJF PA12 pull-out > 1800 N (5 specimens); PEM IUTA-M5 (same 6.43 × 9.52 envelope) 1691 N /
  7.7 N·m in PC and 1197 N / 5.4 N·m in ABS. **Design pull-out 1200 N (ASSUMPTION** for FDM PAHT-CF, which has no
  published data; ABS value), torque-out 5.4 N·m, tighten <= 2.5 N·m, 1.5 g. hipbelt_structural.md assumed 1500 N ×
  0.8 hot: with 1200 N its 2-insert SF scales by 0.8 (1.14 -> ~0.91), and 4 × M5 roughly doubles capacity if prying
  shares evenly. The structural-fea-engineer should re-run it; HB-6 (5 inserts, >= 1.5 kN) stays the release gate.
- `shock_cord_3mm` (hardware): 6.0 g/m, break 280 N (Robline; LIROS 400 N). Replaces the 2 mm Dyneema mass proxy
  (`corrie.py SHOCK_NOTE`).
- Validator / contract: torque suffix `_n_m` (N·m) added to `huntkit/materials/validate.py` and `docs/CONTRACTS.md`
  §1 (backward compatible).

## Sources

- Challenge Outdoor 2023 EcoPak Outdoor Fabric Guide v3 (ULTRA, ULTRAGrid data): https://static1.squarespace.com/static/62018e9b29f2cd0fc23c3a0c/t/63d8117224b90b2859f159a4/1675104626522/2023_EcoPak-Guide_v3.pdf
- Extremtextil ULTRA 200 X: https://www.extremtextil.de/en/ultra-200-x-backpack-laminate-with-uhmwpe-133g-sqm/72682 ; ULTRA overview: https://www.extremtextil.de/en/challengeultra ; ULTRAGrid: https://www.extremtextil.de/en/ultragrid-210den-recycled-nylon-with-black-uhmw-pe-ripstop-132g-sqm/72602
- Rockywoods Ultra 200: https://rockywoods.com/products/ultra-200-fabric-sold-per-foot ; RBTR ULTRA 200X: https://ripstopbytheroll.com/products/challenge-ultra-200
- RBTR 1.9 oz coated ripstop nylon data sheet: https://ripstopbytheroll.com/cdn/shop/products/1.9ozPUCoatedRipstopNylon-FabricDataSheeta_5000x.png?v=1631631608 ; listing https://ripstopbytheroll.com/products/1-9-oz-pu-coated-ripstop-nylon
- RBTR 100D Robic: https://ripstopbytheroll.com/products/100d-robic-ripstop-nylon ; Extremtextil Robic 70den C0: https://www.extremtextil.de/en/diamond-ripstop-nylon-robic-ocean-recycling-70den-uts-coated-100g-sqm/73078
- RBTR HyperD 300 data sheet: https://cdn.shopify.com/s/files/1/0261/6507/files/HyperD_300.pdf?v=1637101064 ; custom print listing https://ripstopbytheroll.com/collections/design-your-own-fabric/products/hyperd-300
- ruthex M5 inserts (3DJake): https://www.3djake.com/ruthex/threaded-inserts-m5-50-pieces?sai=15210 ; Sculpteo insert pull-out test: https://www.sculpteo.com/en/3d-learning-hub/design-guidelines/pull-out-resistance-of-threaded-inserts-testing-and-results/ ; PEM IUTA-M5: https://www.pemnet.com/products/product-finder/iuta-m5/
- Robline shock cord: https://www.roblineropes.com/en/products/mini-spools/product/detail/minispools-shockcord/ ; LIROS Sandow 3 mm: https://www.liros.com/catalog/en/sandow-3-mm-p3369/
