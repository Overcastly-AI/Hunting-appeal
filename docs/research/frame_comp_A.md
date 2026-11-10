# Team A (MONO): printed monolithic frame body, material, orientation and annealing on the home H2S (research, 2026-11-10)

Owner: structural-fea-engineer (competition team A). Rules: [RULES.md](../../designs/pack_5200/frame_comp/RULES.md).
Analysis: [frame_comp_A.md](../../designs/pack_5200/analysis/frame_comp_A.md). Scope: today's one-piece generative
branch body (printed in two segments), re-sized and re-specified for the material, the print orientation and annealing,
printed at home on a Bambu H2S, assembled dry.

Every property below has a URL. Values not published anywhere are marked **ASSUMPTION** with the coupon test that
decides them ([frame_comp_A.md](../../designs/pack_5200/analysis/frame_comp_A.md) section 7).

## 1. The printer: Bambu H2S

| item | value | source |
|---|---|---|
| build volume | 340 x 320 x 340 mm | [West3D H2S listing](https://west3d.com/products/bambu-lab-h2s-and-h2s-ams-combo-3d-printer), [Core Electronics](https://core-electronics.com.au/bambu-lab-h2s-3d-printer-machine-only.html.md) |
| chamber | actively heated, up to 65 C | [West3D](https://west3d.com/products/bambu-lab-h2s-and-h2s-ams-combo-3d-printer) |
| hotend | 350 C all-metal | [West3D](https://west3d.com/products/bambu-lab-h2s-and-h2s-ams-combo-3d-printer) |

Consequence: the 540 mm tall body does not fit in one piece in any orientation (the plate diagonal is 467 mm, the
height 340 mm). A monolithic body is always printed as **two segments** with a joint, as today (split at z 234).

## 2. Materials printable on the H2S

All values are the vendors' dry, 23 C data unless marked. "XY" = in the layer plane, "Z" = across the layers.

| property | PAHT-CF (Bambu) | PPA-CF (Bambu) | PA6-CF (Bambu) | source |
|---|---:|---:|---:|---|
| matrix | PA12 + long-chain PA | semi-aromatic PA (PPA) | PA6 | TDS below |
| density g/cm3 | 1.06 | 1.25 | 1.17 (record; one reseller 1.09) | [PAHT TDS v2][paht], [PPA TDS][ppa], [PA6 TDS][pa6] |
| tensile XY MPa | 92 +/- 7 (sheet v2 mirror); 88 used (record) | 168 +/- 4 | 102 +/- 7 | [PAHT TDS v2][paht], [PAHT TDS][paht1], [PPA TDS][ppa], [PA6 TDS][pa6] |
| tensile Z MPa | **47 +/- 5** (64 in another revision; 47 used) | 57 +/- 5 | 66 (0.645 x XY, PolyMide ratio) | [PAHT TDS v2][paht], [PPA TDS][ppa], [PolyMide PA6-CF][polymide] |
| modulus XY / Z MPa | 3860 / 2180 | 11800 / 4300 | 4430 / 2170 | [PAHT TDS v2][paht], [PPA TDS][ppa], [PA6 TDS][pa6] |
| elongation XY / Z % | 8.4 / 4.1 | 3.2 / **0.9** | | [PAHT TDS v2][paht], [PPA TDS][ppa] |
| impact Z (Charpy) kJ/m2 | **13.3** | **4.3** | | [PAHT TDS v2][paht], [PPA TDS][ppa] |
| Tg (DSC) C | 70 (TDS v2; the record keeps 45) | 85 | | [PAHT TDS v2][paht], [PPA TDS][ppa] |
| HDT 1.8 MPa C | 170 | 196 | | same |
| saturated water absorption | 0.88 % (25 C, 55 % RH) | 1.30 % | 2.4 % (record) | same |
| specimen state | annealed + dried 80 C 12 h | **not annealed** (X1C, chamber 52 C) | | same |
| anneal advice | 80-130 C, 6-12 h, forced-air oven, "some prints may deform and warp" | 120-140 C, 6-12 h, forced-air oven, "may deform, warp and get decreased in toughness"; a kitchen oven "is not compatible" | 80-100 C | same |
| chamber | 50 C (record) | 50-80 C; 70-80 C gives better Z | | [PPA TDS][ppa] |
| price | $80 / kg (record) | about $120 / kg (0.75 kg $89.99) | $43 / kg | records in `data/materials/polymers/` ([MatterHackers PA6-CF][mh-pa6]) |

### 2.1 Hot / wet

| material | evidence | design knockdown | source |
|---|---|---|---|
| PAHT-CF | PA12 base, 0.88 % saturated water; PA12-CF15 injection grade modulus dry 9600 vs conditioned 9000 MPa (-6 %); Intamsys: PA12-CF keeps properties after moisture conditioning (no numbers) | **0.8** on strength (record, kept) | [Arkema Rilsamid ASR 13 TDS][arkema], [Intamsys PA12-CF TDS][intamsys] |
| PPA-CF | Raise3D PPA-CF, **conditioned** (annealed 100 C 8 h, 3 days ambient): XY 122 +/- 4 MPa, modulus 7800, elongation 1.9 %, mono-layer Z **30.2 +/- 1.4** MPa | **0.73** = 122 / 168 (cross-brand: Raise3D conditioned over Bambu dry; conservative) | [Raise3D PPA-CF TDS][r3d], [Bambu PPA TDS][ppa] |
| PA6-CF | conditioned XY = 0.78 x dry (PolyMide) | 0.75 | [PolyMide PA6-CF TDS][polymide] |

**PPA-CF Z design value.** Bambu publishes 57 +/- 5 MPa (unannealed, chamber 52 C). Raise3D's mono-layer Z test gives
30.2 MPa conditioned. Team A uses **45 MPa** dry (57 - 2.4 SD) x 0.73 wet = 32.9 MPa, which sits at the Raise3D value.
ASSUMPTION: the H2S at 65 C chamber matches Bambu's specimens. Coupon test CA-3.

### 2.2 Fatigue (the check that governs today's body)

No vendor publishes an S-N curve for PAHT-CF, PPA-CF or PA6-CF. Published FDM data on PA12 with chopped carbon fibre:

| source | material | test | result | fraction of UTS at 1e6 |
|---|---|---|---|---:|
| Stratasys fatigue white paper | FDM Nylon 12CF (PA12 + 35 wt % CF), F900, ASTM D7791, R 0.1, 5 Hz, conditioned | XZ (in-plane): 40 % of strength (33.4 MPa max) 3 / 3 run-outs at 1e6; 50 % (41.7 MPa): 64 293 to 215 324 cycles, mean 135 769. ZX (across layers): 40 % 3 / 3 run-outs; 55 %: 211 055 to 1e6 | 0.40 (run-out) | [Stratasys / GoEngineer white paper][ss-fat] |
| Siebert et al., Proc. TU Sofia 76(3) (2025) | FFF PA12-CF15, UTS about 70 MPa | tension-tension R 0.1, 10-50 Hz, 60 / 50 / 40 % UTS levels | "specimens surviving up to 1e6 cycles at stress amplitudes around 8-10 MPa", i.e. max stress 17.8-22.2 MPa | **0.25-0.32** |
| Mohammadi, Azizian-Farsani, Khonsari, Int. J. Fatigue 211 (2026) | quasi-isotropic short-CF PA12 | | fatigue limit 48-54 MPa (abstract only; UTS not seen) | n/a |

Reading: the two data sets that give a fraction of UTS disagree, 0.40 against 0.25-0.32 at 1e6 cycles. **The
conservative published value is the Sofia one, about 0.29 x UTS at 1e6**, which matches the record's
`fatigue_1e5_ratio` 0.30 used at 1e5 (one decade of life margin). Team A therefore **keeps 0.30** (on the hot/wet
knocked-down strength, as HA-LS-1 applies it) as the design value for PAHT-CF, and uses 0.30 for PPA-CF and PA6-CF too
(no published data). A ratio of 0.40 (Stratasys) is shown in the analysis only as a sensitivity: it is not credited.
Coupon test CA-1 measures it on PAHT-CF from the owner's H2S.

Bending fatigue of PA6-CF (Onyx class) is reported by Ahmadifar et al. only as strain-controlled 3-point bending
([PMC9919798][ahm]) and is not usable as an R 0.1 stress allowable.

### 2.3 Creep

No creep or creep-rupture data for FFF short-carbon-fibre polyamide at 40 C was found. Reviews of printed PA/CF call
creep "a life-limiting issue" that "still needs to be evaluated" ([PMC8158755][creep-rev]); the PPA-CF15 elevated
temperature study says systematic data "remain limited" ([MDPI Polymers 18(12):1422][ppa-hot]). Team A keeps the record
ASSUMPTIONS: 8 h, 40 C creep-rupture 0.40 x knocked-down strength (PAHT, PA6), 0.55 (PPA, Tg 85 C). Creep does not
govern (margin > 2 in every candidate). Coupon test CA-4.

### 2.4 Annealing

- Bambu's PAHT-CF numbers are already for **annealed** specimens (80 C 12 h); no extra credit is available from
  annealing ([PAHT TDS v2][paht]).
- Published: annealing raised tensile, flexural modulus and strength of FFF PA12-CF15 by about 11 % with higher
  crystallinity ([Rapid Prototyping J., doi 10.1108/RPJ-10-2019-0278][rpj]); Onyx +18 % after 30 min, no gain from
  longer anneals ([MDPI Appl. Sci. 16(8):3791][onyx-ann]); oven annealing beat sand annealing for four CF composites,
  strength rising with annealing temperature for semi-crystalline matrices ([Butt et al., JMMP 8:252][butt]).
- Bambu warns the PPA-CF anneal (120-140 C) can warp parts and cut toughness, and needs a forced-air oven
  ([PPA TDS][ppa]).
- **Team A credits no annealing gain.** The production anneal stays 90 C / 6 h on a flat plate with rods through the
  bores (PRODUCTION.md). A 120 C anneal of PAHT-CF is a possible later gain (+0-11 %) only after coupon test CA-2.

### 2.5 Cold

Z Charpy at 23 C: PAHT-CF 13.3, PPA-CF **4.3** kJ/m2 ([PAHT][paht], [PPA][ppa]); PPA's Z elongation is 0.9 %. The pack
must pass the -20 C empty drop (HA-LS-1 T4c). PPA-CF is the brittle choice; this is a risk the FI check cannot see.

## 3. Print orientation

FDM strength is lowest across the layers (PAHT Z/XY = 0.53, PPA 0.34). Today's body lies wearer face on the plate
(layer normal = frame y), so the stays and bars bend in the layer plane. Stratasys' Nylon 12CF data show the same
ordering in fatigue (XZ run-outs at 33 MPa, ZX at 13 MPa) ([white paper][ss-fat]). Team A checks all three layer normals
on the same stress field (analysis section 3): y is best by a wide margin; x and z fail.

## 4. Real printed load-bearing products

No printed-polymer pack frame or bike frame carrying body loads was found; every load-carrying tube/lug product in the
lighter-frame research uses metal lugs (Robot Bike Co, Bastion, Burton) ([light_frame_architectures.md](light_frame_architectures.md)
section 1). Today's body (2026-11-01, DECISIONS) is itself the first; it rests on proof tests T1-T5 and the coupons.

## 5. Patents (not legal advice)

The MONO body keeps today's topology, crown, lifters and interfaces, so the guardrails of DECISIONS.md apply unchanged:
Mystery Ranch US 10,952,523 (lifters stay on the crown top bar), KUIU one-piece slotted sheet frames (USRE48,093 E1,
US 9,095,203 B2, US 9,636,875 B2: our body is a printed branching lattice, not a slotted sheet with a U-tongue),
Divergent node patents US 10,668,965 / US 10,605,285 (no adhesive ports or channels; the new joint is bolted, with no
adhesive at all). Freedom-to-operate opinion before tooling, as before.

## 6. Gaps

- No S-N curve for any Bambu CF filament; the two PA12-CF sources disagree by 0.1 x UTS. CA-1 decides.
- No hot/wet fatigue data for any printed polyamide.
- No creep-rupture data at 40 C for printed CF polyamide.
- No bolt-bearing / nut-trap pull-through data for PAHT-CF. CA-5 decides.

[paht]: https://uwaterloo.ca/rapid-prototyping-centre/sites/default/files/uploads/documents/bambu_paht-cf_technical_data_sheet_v2.pdf
[paht1]: https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PAHT-CF_Technical_Data_Sheet.pdf
[ppa]: https://www.additive-x.com/shop/mpattachments/file/viewonline/id/916/product_id/2729
[pa6]: https://polyalkemi.no/wp-content/uploads/2024/01/Bambu_PA6-CF_Technical_Data_Sheet-v2.pdf
[polymide]: https://cdn.shopify.com/s/files/1/0151/1735/files/PolyMide__PA6-CF_TDS_EN_V4.1.pdf
[mh-pa6]: https://www.matterhackers.com/store/l/bambu-lab-pa6-cf-filament/sk/MHUAEMPV
[arkema]: https://hpp.arkema.com/assets/arkema/TDS_RILSAMID%C2%AE%20ASR%2013_en_WW.pdf
[intamsys]: https://cdn.shopify.com/s/files/1/0022/2671/6784/files/INTAMSYS_PA12-CF_TDS_V1.pdf
[r3d]: https://cdn.shopify.com/s/files/1/2104/4351/files/Raise3D-Industrial-PPA-CF_TDS.pdf
[ss-fat]: https://cdn.goengineer.com/fatigue-behavior-select-stratasys-fdm-materials-whitepaper.pdf
[sofia]: https://e-university.tu-sofia.bg/e-conf/files/169/paper_10.47978@TUS.2025.76.03.004.pdf
[khonsari]: https://repository.lsu.edu/mechanical_engineering_pubs/2384
[ahm]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9919798/
[creep-rev]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8158755/
[ppa-hot]: https://www.mdpi.com/2073-4360/18/12/1422
[rpj]: https://emerald.com/insight/content/doi/10.1108/RPJ-10-2019-0278/full/html
[onyx-ann]: https://www.mdpi.com/2076-3417/16/8/3791
[butt]: https://www.open-access.bcu.ac.uk/15971/1/jmmp-08-00252.pdf

Sources for the fatigue table: Stratasys [white paper][ss-fat]; Siebert et al. [TU Sofia][sofia]; Mohammadi et al.
[LSU repository][khonsari].
