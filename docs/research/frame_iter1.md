# Frame iteration 1: research (BL-061, 2026-11-24)

Owner: structural-fea-engineer. Purpose: the cited basis for the iteration-1 frame concepts
([frame_iter1.md](../../designs/pack_5200/iter1/frame/frame_iter1.md)). It builds on, and does not repeat,
[light_frame_architectures.md](light_frame_architectures.md) (2026-11-09: printed nodes on carbon tubes, bonds to
printed polyamide, patents) and the frame-competition research `frame_comp_*.md`. Benchmarks come from the sources
below, not memory. Sites that would not load are marked "secondary" (the claim is the search engine's summary of the page).
Original IP only: nothing here is copied; the leaders are mass and construction benchmarks.

## 1. Production meat-hauling frames: mass and construction

| Frame | Construction | Published mass | Rating | Source |
|---|---|---|---|---|
| Stone Glacier Krux Evo | four straight carbon-composite stays, 500D Cordura / X-Pac frame sheet, integrated load shelf | **2 lb 7 oz (1105 g) with M belt** | 150+ lb | [goHUNT][sg-evo], [1 Shot Gear][sg-evo2] (secondary) |
| Stone Glacier Krux | same, heavier sheet | 2 lb 12 oz (1247 g) with M belt | 150+ lb | [BlackOvis][sg-krux] (secondary); light_frame_architectures.md section 3 |
| Exo Mtn Gear K4 | custom carbon-fibre stays, plastic-backed hip belt and harness | 2 lb 15 oz (1332 g); measured 1361 g | 150+ lb | [Exo K4][exo-k4], [Packstack][ps-k4] |
| Kifaru ARK | one carbon-fibre sheet with cross support | 3.1 lb (1406 g) with M belt | | light_frame_architectures.md section 3 ([goHUNT][kif-gh]) |
| Seek Outside Revolution | 6061 Al U-frame, 7075 cross stays, belt bolted on | 2 lb 9 oz (1162 g) at 24 in | 200+ lb | [Seek Outside][seek-rev] |
| Mystery Ranch Guide Light MT | **sources disagree**: MR's own workbook says a removable 7000-series aluminium frame; a goHUNT article says three flat composite stays | no frame-only mass published; Metcalf on Guide Light 6.1 lb complete | | [MR workbook][mr-wb] (secondary), [goHUNT 2022][gh-2022] (secondary) |

All of these masses **include the belt and harness** (frame system). Our like-for-like "frame" in the ledger is the
structure only (body, crown, torso adjust, hip mount): 1391.1 g proven now / 1387.1 g after tests
(`designs/pack_5200/iter1/system/iter1_weight.json` totals, BL-062; the 1453 g quoted here before predates BL-062's re-roll, BL-066 m2), plus belt 536 g and harness 217 g
(`huntkit/mass/ledger.py`, BL-058). The H1 print alone (1069 g) is about the leaders' whole frame system. That gap is
the case for this track: the leaders carry the load on **straight carbon stays** (SG, Exo) or a **carbon sheet**
(Kifaru), and spend their mass on soft goods.

## 2. Printed or AM nodes on carbon tubes (production)

| Product | Node | Tube joint | Source |
|---|---|---|---|
| Atherton Bikes A-range | SLM Ti-6Al-4V lugs (about 16 h, 3500 layers per frame set); S-range CNC 7075 lugs | carbon tubes **bonded** into the lugs with aerospace adhesive | [BikeRadar][ath-br] (secondary), [3DPrinting.com][ath-3d] (secondary), [Pinkbike][ath-pb] (secondary) |
| Robot Bike Co, Bastion, Burton | AM Ti lugs | double-lap bonded carbon tubes | light_frame_architectures.md section 1 |

Every load-bearing production example uses a **metal** lug. No pack frame with printed polymer nodes was found
(search 2026-11-24, same result as 2026-11-09). Atherton publishes no frame mass. Reading for us: a printed PAHT-CF
node is only acceptable where the node is a **long through-sleeve** (the tube runs through it, so the joint transfers
only the local branch load, and bending goes in by bearing) and has a mechanical fail-safe. A short end socket in printed
nylon failed rev C in frame_light2 (NODE, Volkersen peak 0.16).

## 3. Off-the-shelf carbon tubes for a stay

| Tube | Mass | Source |
|---|---|---|
| 22 x 18 mm roll-wrapped, 1 m | stocked; no mass listed | [Lindinger (R&G VEC pipe 22/18)][rg-2218] |
| 22 x 19 mm, 1.5 mm wall | 0.14 kg/m (implies about 1.45 g/cm3) | [EC Fibreglass][ec-2219] |
| 25 x 22 mm roll-wrapped UD | 178 g/m | [EC Fibreglass][ec-2522], [Easy Composites 25 mm range][ez-25] |

ID 18 mm = today's reamed crown-leg bore (`frame_h1.SLEEVE_WALL_FLOOR` comment, 18.0 mm), so the crown legs, bushings
and pawl are unchanged. Design mass: 22/18 at the record's 1550 kg/m3 = **0.195 g/mm**
(`cfrp_rollwrapped_tube.yaml`); the 22/19 listing's 1.45 g/cm3 would give 0.182 g/mm, so the record value is the
conservative one. Properties: the record (E 75 GPa, 650 / 450 MPa, ESTIMATE): ask the vendor for the layup, and
3-point-bend one offcut per batch (the record says so).

## 4. Print strategy on the H2S

- **Printer:** Bambu Lab H2S, build volume **340 x 320 x 340 mm**, nozzle to 350 C, heated bed 120 C, actively heated
  chamber (65 C, retailer), **single nozzle** ([Bambu][h2s], [Bambu FAQ][h2s-faq], [Tom's Hardware][h2s-th]).
  A single nozzle rules out a two-material (PAHT + PPA) part in one print.
- **Material:** PAHT-CF stays the filament. PPA-CF (E 11.8 GPa, 3x PAHT) was rejected for the whole body in the
  frame competition: 18 % denser, Z elongation 0.9 %, Charpy Z 4.3 kJ/m2, converged no lighter
  ([frame_comp_A.md](frame_comp_A.md), DECISIONS 2026-11-01). Not reopened here.
- **Gyroid infill stiffness and strength.** Bean, Lopez-Anido and Vel (*Appl. Sci.* 12(4):2180, 2022) homogenised FDM
  gyroid infill and validated it in compression: nearly isotropic (low anisotropy index), and the Gibson-Ashby power law
  **fits poorly over the full density range** ([UMaine summary][bean22], [MDPI][bean22b]: 403 to the fetcher, secondary).
  The follow-up gives a semi-empirical yield-strength relation ([Prog. Addit. Manuf. 2025][bean25], secondary). No
  numbers could be read. **ASSUMPTION GYROID**: Gibson-Ashby bending-dominated cell, E*/E = rho^2, strength = 0.3
  rho^1.5 (Gibson and Ashby, *Cellular Solids*, 2nd ed., 1997, ch. 5, from engineering knowledge, not fetched). At 15 %:
  E 2.25 %, strength 1.74 %. Coupon GY-1 (compression and 3-point bend of a printed shell + core beam) settles it.
- The H1 build sheet says "100 % infill (never a gyroid in place of the limbs)" (BUILD_H1.md) and the generative-branch
  study rejected a *visible* gyroid as a look ([generative_branch.md](../../designs/pack_5200/analysis/generative_branch.md)).
  An internal core is invisible; the FE must show whether the walls carry it.

## 5. Adhesive on carbon

- 3M Scotch-Weld DP490: **19 MPa overlap shear on carbon-fibre-reinforced epoxy** (IPA wipe, ASTM D1002 / ISO 4587,
  mixed adhesive / cohesive failure); 90 min work life; 24 h to 6.9 MPa ([3M DP490 TDS][dp490]). It agrees with the
  record's MMA on CFRP (20 MPa, `adhesive_methacrylate_ma.yaml`).
- On printed polyamide the weak side governs: 3.7-5.0 MPa with interface failure (Sedlacek et al. 2025, in
  light_frame_architectures.md section 2). Design value 5.0 x 0.8 = **4.0 MPa** (ASSUMPTION BOND-PA, unchanged),
  coupon T6p.

## 6. Gaps

- No published frame-only mass for Mystery Ranch or Atherton.
- No published strength for a carbon tube bonded through a printed PAHT-CF sleeve (T6p coupons).
- No published FDM PAHT-CF gyroid property (GY-1 coupon).
- No published pin-bearing strength for a roll-wrapped 22 x 18 tube (ASSUMPTION TUBE-BEARING 250 MPa; coupon T6b).

## Sources

[sg-evo]: https://shop.gohunt.com/products/krux-evo-frame
[sg-evo2]: https://1shotgear.com/products/stone-glacier-krux-evo-frame
[sg-krux]: https://blackovis.com/stone-glacier-krux-frame
[exo-k4]: https://exomtngear.com/products/k4-frame-system
[ps-k4]: https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system
[kif-gh]: https://shop.gohunt.com/products/kifaru-ark-frame
[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[mr-wb]: https://issuu.com/mysteryranch/docs/f23_hunt_mr_2022_final_digital
[gh-2022]: https://www.gohunt.com/browse/gear-lists-and-reviews/hunting-backpack-options-for-2022
[ath-br]: https://www.bikeradar.com/features/atherton-bikes
[ath-3d]: https://3dprinting.com/metal/atherton-bikes-3d-printed-titanium-lugs
[ath-pb]: https://m.pinkbike.com/news/the-tech-behind-the-new-atherton-bikes.html
[rg-2218]: https://lindinger.at/en/SUPPLIES-MISC/BUILDING-MATERIALS/Rods-Tubes-Solid-Strips-Panels/Tubes/R-G-VEC-PIPE-22-18MM-1M-WRAPPED/96336
[ec-2219]: https://ecfibreglasssupplies.co.uk/carbon-fibre-tube-22mm-19mm
[ec-2522]: https://ecfibreglasssupplies.co.uk/carbon-wrapped-tube-ud-22mm-x-25mm
[ez-25]: https://www.easycomposites.co.uk/25mm-roll-wrapped-carbon-fibre-tube-metric
[h2s]: https://bambulab.com/en-gb/h2s
[h2s-faq]: https://wiki.bambulab.com/en/h2/manual/h2s-faq
[h2s-th]: https://www.tomshardware.com/3d-printing/bambu-lab-h2s-review-the-one-we-wanted
[bean22]: https://composites.umaine.edu/?p=38466
[bean22b]: https://www.mdpi.com/2076-3417/12/4/2180
[bean25]: https://link.springer.com/article/10.1007/s40964-025-01200-7
[dp490]: https://multimedia.3m.com/mws/media/2534142O/3m-scotch-weld-epoxy-adhesive-dp490-technical-data-sheet.pdf
