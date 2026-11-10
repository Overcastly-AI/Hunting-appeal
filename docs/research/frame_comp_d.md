# Frame competition, team D (SERVICE): industrial powder-bed print, research

Date 2026-11-10. Owner: structural-fea-engineer (team D). Rules: `designs/pack_5200/frame_comp/RULES.md`.
Analysis: `designs/pack_5200/analysis/frame_comp_d.md`. Every property has a URL. Anything without one is an
**ASSUMPTION** with a coupon test (section 7).

## 1. Question

Can a service-printed (MJF / SLS / industrial FDM) branch body beat today's 823 g PAHT-CF body and pass HA-LS-1 rev C,
fatigue included? Powder-bed nylon is near-isotropic, so the FDM Z-weakness is gone. The cost is that powder-bed
nylon has about half the strength and modulus of annealed PAHT-CF in its layer plane, and the release body is
already loaded mostly in that plane (layer normal = frame y, stays bending about x).

## 2. Candidate materials (static)

| material | process | tensile MPa (XY / Z) | E MPa | elong. % | density | source |
|---|---|---|---|---|---|---|
| PAHT-CF (today) | FDM, home | 88 / 47 | 3860 / 2180 | 10 / 5 | 1.06 | [Bambu TDS](https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PAHT-CF_Technical_Data_Sheet.pdf), [U Waterloo mirror](https://uwaterloo.ca/rapid-prototyping-centre/sites/default/files/uploads/documents/bambu_paht-cf_technical_data_sheet_v2.pdf) |
| HP 3D HR PA12 | MJF | 48 / 48 | 1700 / 1800 | 20 / 15 | 1.01 | [HP spec sheet](https://hlhrapid.com/wp-content/uploads/2022/06/HP-MJF-PA12-Spec-Sheet.pdf), [JLC3DP PA12-HP](https://jlc3dp.com/help/article/pa12-hp-nylon) (48 MPa, 1800 MPa) |
| HP 3D HR PA11 | MJF | 52 / 50 | 1800 | 50 | 1.05 | [HP PA11 TDS](https://3dprinting.com/wp-content/uploads/2019/02/HP-PA-11-TDS-4AA7-0715ENE.pdf), [JLC3DP PA11-HP](https://jlc3dp.com/help/article/PA11-HP-Nylon) (52 MPa XY and Z, 1800 MPa, 50 %) |
| PA12-CF | SLS | 85 x / 55 y / 45 z | 7900 (x) | ~4 | 1.10 | [Protolabs PA12-CF sheet](https://www.protolabs.com/media/kuylbdiz/pa12-cf-smooth-black-en-28_02.pdf) |
| Windform XT 2.0 | SLS (CRP) | 83.8 | 8928 | 3.8 | 1.10 | [windform.com](https://www.windform.com/sls-materials/windform-xt-2-0/), [Knowde TDS](https://knowde.com/stores/crp-technology/products/windform-xt-2-0) |
| PA12 Glass Beads | MJF | 30 | 2500 | 10 | 1.30 | [Protolabs PA12-GB](https://www.protolabs.com/media/ijunlcie/hp-mjf-pa12gb-datasheet.pdf) (rejected: lower strength, heavier) |

Avanzini et al. measured MJF PA12 at **43 ± 2.7 MPa, E 1640 ± 31 MPa, 10 % elongation** on dumbbells (below the
48 MPa sheet) ([Avanzini 2022, IRIS preprint](https://iris.unibs.it/bitstream/11379/556537/1/PA12%20fatigue%20-%20IJF%20-%20Revision01%20-%2020220405%20-%20IRIS.pdf)).
The design uses the sheet value 48 MPa with the HA-LS-1 0.8 hot/wet knockdown (38.4 MPa allowable), which is
**below** the measured 43 MPa. ASSUMPTION, coupon D-C1 checks the service's real lot.

Specific strength in the governing direction (MPa per g/cc): PAHT-CF 83, SLS PA12-CF 77 (x only, 50 in y),
Windform XT 76, PA11 MJF 48, PA12 MJF 48. **No service powder-bed nylon beats PAHT-CF per gram in the frame plane.**
The carbon-filled SLS grades come close along the recoater but are weaker across it.

## 3. Fatigue (the gate today: body fatigue margin 1.04)

- **MJF PA12, Avanzini et al., Int. J. Fatigue 2022** ([preprint](https://iris.unibs.it/bitstream/11379/556537/1/PA12%20fatigue%20-%20IJF%20-%20Revision01%20-%2020220405%20-%20IRIS.pdf)):
  tension, **R ≈ 0.05**, 5 Hz (to avoid self-heating), RT, 35 specimens. Basquin on Smax, smooth specimens:
  **Smax = 44 N^-0.034** MPa; 27.7 MPa at 1e6; scatter index T(1e6) = UCL/LCL = **1.84**. R-notch: no reduction
  (27.8 MPa); V-notch: 19.1 MPa.
  - Mean Smax at 1e5 = 44 × 1e5^-0.034 = **29.7 MPa**. Lower bound mean/√T = **21.9 MPa** (`frame_comp_d.fatigue_lower_bound`).
  - HA-LS-1 checks fatigue as 0 → 1.6 g (R = 0), which matches R ≈ 0.05.
  - In the repo rule (allowable = ratio × knock × s): PA12 ratio = 21.9 / 48 = **0.457**; PA11 (s = 50) **0.439**.
    The fatigue allowable after the 0.8 hot/wet knock is **17.5 MPa**. Today's PAHT-CF uses 0.3 × 0.8 × 88 =
    **21.1 MPa**, and that is an ASSUMPTION with no published PAHT-CF fatigue data behind it.
  - The same paper cites a thermographic fatigue limit of 29.4 ± 1.6 MPa (R = 0.1, 2e6 run-out) for MJF PA12, and
    an SLS PA12 HCF limit of 18 MPa amplitude at R = -1.
- **PA11 vs PA12, SLS** (Salazar et al., *Eur. Polym. J.* 2014, doi:10.1016/j.eurpolymj.2014.07.016, summary via
  [IMDEA](https://materiales.imdea.org/monotonic-loading-and-fatigue-response-of-a-bio-based-polyamide-pa11-and-a-petrol-based-polyamide-pa12-manufactured-by-selective-laser-sintering/)):
  "PA11 showed better mechanical and fatigue behaviour than PA12". ASSUMPTION: PA11 gets the PA12 curve in
  absolute MPa (conservative).
- **SLS density governs fatigue life** ([FISITA 2010](https://go.fisita.com/store/papers/FISITA2010/F2010C083)).
  Section thickness has no significant effect under tension-only loading
  ([Sheffield, LS nylon 12](https://eprints.whiterose.ac.uk/id/eprint/113650/1/Effect%20of%20section-thickness%20on%20fatigue%20performance%20of%20LS%20nylon%2012.pdf)).
- **Crystallinity / cooling** changes MJF PA12 fatigue ([De Biasi et al. 2026, JMRT](https://iris.unitn.it/retrieve/0c6e9085-e184-440e-b140-d6806e213da3/JMRT2026.pdf)).
  Service parts get the service's own cooling, so the D-F1 coupons must come from the same order.
- **Carbon-filled SLS (PA12-CF, Windform XT 2.0): no published S-N data found** (search 2026-11-10). ASSUMPTION
  ratio 0.3, the same as PAHT, coupon D-F2.

**Reading:** per gram, powder-bed PA12 has a better **fatigue / static** ratio than PAHT-CF does on paper (0.46 vs
0.30). In absolute terms its fatigue allowable is still 17 % below what the release body is sized to (17.5 vs
21.1 MPa), and its strength allowable is 45 % below. Fatigue alone would need about 1.2× lower stress, strength about
1.8× (C8 at 1.51 today: about 1.2× needed).

## 4. Moisture, hot/wet, creep, cold

- Water absorption: PA12 MJF 0.5 %, PA11 0.4 %, vs PAHT-CF 0.88 % (sheets above). PA12 has the lowest water
  uptake of the polyamides ([Xometry PA12 SLS/MJF sheet](https://xometry.pro/wp-content/uploads/2023/07/Nylon-PA12-SLS-MJF.pdf)).
- Aging of MJF PA12 at ambient humidity for 474 days: modulus and UTS change more in ambient than in dry storage
  ([Kenne 2024, ETS thesis](https://espace2.etsmtl.ca/29437/1/Kenne-JP-2024-29437.pdf), [Peeref](https://peeref.com/works/28432693)).
  No wet-conditioned retention figure was found, so the HA-LS-1 knock 0.8 is kept. ASSUMPTION, coupon D-C2
  (tensile after 7 days at 40 °C / 85 % RH).
- Glass transition: DMA on laser-sintered PA12 shows a Tg onset at **27 °C**, with E' falling from 1438 MPa to
  about 500 MPa through the transition ([NETZSCH](https://analyzing-testing.netzsch.com/en/blog/2021/estimating-residual-stresses-in-sls-parts-using-dma)).
  **A 40 °C hot day is inside the transition for PA12.** Stiffness at 40 °C wet is taken as 0.55 × RT (DB record
  `pa12_mjf_hp`, ASSUMPTION).
- Creep: SLS PA12 creep at 5–20 MPa, 10 h / 1000 h, Burgers model, RT only (Kroenert et al., IJAMT 2022,
  doi:10.1007/s00170-022-09446-z). Sintered PA12 creeps more than most thermoplastics but less than moulded PA12, at
  60 °C and 100 °C ([Moeskops 2004](https://utw10945.utweb.utexas.edu/Manuscripts/2004/2004-07-Moeskops.pdf)).
  Plasticity-controlled failure vs temperature and RH of sintered PA12: [Paolucci, Peters & Govaert 2020](https://research.tue.nl/en/publications/plasticity-controlled-failure-of-sintered-and-molded-polyamide-12/).
  **Creep-rupture ratio 0.35 at 40 °C 8 h is an ASSUMPTION** (DB record), coupon D-K1.
- Cold: PA11 keeps its ductility (50 % elongation at RT, the [JLC3DP page](https://jlc3dp.com/help/article/PA11-HP-Nylon)).
  It is the better choice for the −20 °C T4c empty drop. **PA11 is preferred over PA12** for the same mass.

## 5. Build volume, split, service

| service / process | max part mm | body fits whole? | source |
|---|---|---|---|
| JLC3DP MJF PA12-HP / PA11-HP | **370 × 276 × 360** | **no**: the body is 265 × 65 × 545 mm. Split at z 234 (lower 234 tall, upper 309 tall, each fits) | [PA12-HP](https://jlc3dp.com/help/article/pa12-hp-nylon), [PA11-HP](https://jlc3dp.com/help/article/PA11-HP-Nylon) |
| JLC3DP PA12-CF | 580 × 480 × 480, but listed **under FDM**, not SLS | fits, but it is an FDM part (Z-weak, the same constraint as home) | [JLC3DP design guideline](https://jlc3dp.com/help/article/3d-printing-design-guideline) |
| JLC3DP SLS 3201PA-F nylon (44 MPa, $0.18/g in Nov 2024) | 350 × 350 × 400 | no (the 350 × 400 face diagonal is 531 mm, under 545) | [JLC3DP 3201PA-F](https://jlc3dp.com/help/article/3201pa-f-nylon), [price notice](https://jlc3dp.com/blog/3201pa-f-nylon-price-adjustment-notice-23off) |
| Materialise PA 12 (SLS): 48 MPa, E 1650 MPa, 20 %, **0.95 g/cc** | **630 × 330 × 550** (a different page says 500 × 280 × 345) | **yes, one piece**, laid flat | [Materialise PA 12 SLS](https://www.materialise.com/en/manufacturing/materials/pa-12-sls), [laser sintering](https://www.materialise.com/en/manufacturing/3d-printing-technology/laser-sintering) |
| HP 5200 / 5420W class (MJF) | 380 × 284 × 380 machine | split, as JLC | HP spec (same as the JLC envelope) |

Cost:
- JLC3DP MJF-PA12 **$0.275/g** (cut from $0.35, Aug 2025) ([JLC3DP pricing](https://jlc3dp.com/blog/drastic-material-price-cuts-and-adjusted-post-processing-service-fees)).
- JLC3DP PA11 **$0.30/g** from 15 Nov 2025 ([JLC3DP PA11 notice](https://jlc3dp.com/news/pa11-nylon-powder-price-adjustment)).
- JLC3DP SLS PA12-CF: −24 % on 24 Jul 2026, no absolute figure published ([JLC3DP July 2026](https://jlc3dp.com/news/materials-finishing-pricing-update-july2026)).
  ASSUMPTION $0.60/g (DB record).
- No quantity breaks are published (per-gram instant quote). ASSUMPTION: the same rate at 10 units, −15 % at 100
  (volume quote), $30 shipping per order.
- SLS benchmark: a UK SLS service prices part volume at **30p per cm³** (or 11p per cm³ of bounding box, whichever is cheaper) ([pricing page](https://felix-manley-n4jm.squarespace.com/pricing-information)). That is 0.30 / 0.95 = £0.32/g, about **$0.40/g** (ASSUMPTION 1.27 USD/GBP), used for the Materialise-class one-piece body. Materialise publishes no price (instant quote only).
- MJF service cost comparison across five projects: [All3DP / RapidObject](https://all3dp.com/1/mjf-3d-printing-price-comparison-charts-5-sample-projects/).

Turnaround and finishing:
- JLC3DP MJF build time 72 h; "big size parts or bulk orders will be longer" (PA11 page above). ASSUMPTION: about
  7–12 days door to door with shipping.
- Colours: MJF prints grey and is usually dyed black. JLC3DP PA11 comes in black and natural grey. Vapour smoothing
  is the costliest finish, about +30 % ([Xometry](https://xometry.pro/en/topic/vapor-smoothed-and-dyed-black-part-mjf-vs-sls/)).
  General post-processing: [Hubs](https://hubs.com/knowledge-base/post-processing-sls-and-mjf-printed-parts).
  Vapour smoothing seals the surface and may help fatigue (fewer surface pores). **No credit is taken.**
- Materialise finishes: black dye only up to 400 × 330 × 360 mm (the body does not fit); vapour smoothing ("extra smooth") up to 560 × 360 × 330 mm (it fits) ([Materialise PA 12 SLS](https://www.materialise.com/en/manufacturing/materials/pa-12-sls)).
- Ordering is simple: upload the 2 STLs, pick PA11-HP black, pay. No printer, drying, annealing or nozzle.

## 6. Patents checked

The topology is today's socket-free branch body, only re-sized: the same patent position as the release body
(`docs/DECISIONS.md` guardrails, Mystery Ranch US 10,952,523 at the crown/lifters, which is unchanged). Powder-bed
printing of a frame part adds no claim element. No new search was needed for a material change.

## 7. Coupon tests (each governing assumption)

| id | what | why |
|---|---|---|
| D-C1 | 5 ISO 527 tensile bars **from the same order and build**, XY and Z | design 48/50 MPa vs measured 43 MPa (Avanzini) |
| D-C2 | 5 bars after 7 d at 40 °C / 85 % RH, tested at 40 °C | the 0.8 hot/wet knock (no published wet MJF data) |
| D-F1 | 6 smooth bars, R = 0.05, 5 Hz, 2 at each of 24 / 20 / 17.5 MPa max, to 1e5 | the 21.9 MPa lower bound and 17.5 MPa allowable |
| D-F2 | (only if SLS-CF is chosen) the same on PA12-CF along x and y | no published data |
| D-K1 | 3 bars at 40 °C under 0.35 × 0.8 × s for 8 h, then a residual tensile test | creep-rupture ratio 0.35 |
| D-J1 | 3 split-joint coupons (bolted half-lap, 2 × M5) pulled to failure | PA bearing ratio 1.0 (no data) |
| D-I1 | 4 M5 heat-set inserts in an MJF boss, pull-out and torque-out | insert retention in MJF (hip pivot, 4 × M5) |
