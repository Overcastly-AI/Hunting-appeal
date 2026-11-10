# Frame competition, Team B (SEG): research

Date 2026-11-10. Owner: structural-fea-engineer (Team B). Rules: `designs/pack_5200/frame_comp/RULES.md`.
Direction: a segmented printed body, each segment printed along its own load path, joined by bolted printed lap
joints (inserts plus bolts, no adhesive in the load path). Every property below carries a URL; anything not
published is an `ASSUMPTION` with a coupon test (CT-B1 … CT-B5, defined in
`designs/pack_5200/analysis/frame_comp_B.md` §6).

## 1. XY vs Z (interlayer) strength of carbon-filled nylons

| material | XY tensile, MPa | Z tensile, MPa | Z / XY | source |
|---|---:|---:|---:|---|
| Bambu PAHT-CF (TDS v2, Waterloo mirror) | 92 ± 7 | 47 ± 5 | 0.51 | https://uwaterloo.ca/rapid-prototyping-centre/sites/default/files/uploads/documents/bambu_paht-cf_technical_data_sheet_v2.pdf |
| Bambu PAHT-CF (TDS V2.0, Bambu CDN) | 88 ± 7 | 64 ± 3 | 0.73 | https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PAHT-CF_Technical_Data_Sheet.pdf |
| Bambu PAHT-CF modulus | 3860 | 2180 | 0.56 | same TDS |
| PolyMide PA6-CF, dry annealed | 105.0 ± 5.0 | 67.7 ± 4.7 | 0.64 | https://cdn.shopify.com/s/files/1/0151/1735/files/PolyMide__PA6-CF_TDS_EN_V4.1.pdf |
| PolyMide PA6-CF, conditioned 70 % RH | 81.7 | 64.4 | 0.79 | same TDS |
| FlashForge PA12-CF (vendor, no method stated) | 80–95 | 25–30 | ≈ 0.3 | https://enterprise.flashforge.com/products/pa12-cf |

Design values (repo record `pa12_cf_fdm_paht`): XY 88, Z 47 (the lower of the two sheet revisions), hot/wet × 0.8,
interlayer shear 0.6 × Z (ASSUMPTION in `frame_topopt.layer_failure_index`, CT-B2).

Raster direction inside the XY plane:
- PA6-CF: about +25 % tensile strength from 90° to 0° raster at the same build orientation, and 42 → 73 MPa from
  layer temperature alone (cited in a Cambridge open-access review): https://www.cambridge.org/core/product/C921F564CEEC2122D079C0EF30F4B4B0/core-reader
- Unidirectional raster stronger and stiffer than alternating; weakest with load along the build direction (TUM
  thesis): https://mediatum.ub.tum.de/doc/1750546/1750546.pdf

## 2. Fatigue of short-fibre printed nylon (XY vs raster, no Z data found)

- Panerai et al., Int J Fatigue 174 (2023) 107711 (open access, Onyx short-CF PA, R 0.1, 2 Hz, run-out 1e6): UTS
  0/90 = 20.9 MPa and ±45 = 23.9 MPa, similar; fatigue is **matrix-dominated** (self-heating, thermal and mechanical
  regimes); ±45 rasters showed higher fatigue strength than 0/90 in earlier work.
  https://re.public.polimi.it/retrieve/df86332b-3647-45b0-992d-065f5f202619/1-s2.0-S0142112323002128-main.pdf
- Fatigue-limit optimisation of FDM short-CF polyamide (Taguchi; predicted ≈ 69–70 MPa fatigue limit, confirmed
  experimentally): https://repository.lsu.edu/mechanical_engineering_pubs/2404
- **No published interlayer (Z) fatigue data for PAHT-CF, PA6-CF or PA12-CF was found.** The design keeps the
  record ASSUMPTION `fatigue_1e5_ratio` 0.3 for every direction, which is conservative against the in-plane data
  above but unproven across layers. CT-B1 (XY, Z and ±45, dry and 40 °C wet).

What this means for SEG: the fatigue gain of a raster aligned to the member is matrix-limited and small, and the
only published orientation gains are in-plane (raster angle), which a monolithic print can also get with slicer
modifier volumes. SEG can only add value where the monolith is forced to load layers in Z. §3 of the analysis
shows the monolith already is not.

## 3. Bolted joints in printed short-fibre nylon

- Printed-in holes with fibres wrapped round the hole gave about +31 % bearing stress over drilled holes (Nylon X
  pin-bearing): https://scholars.csus.edu/esploro/outputs/graduate/Using-additive-manufacturing-techniques-to-increase/99257831365101671
- Bearing jig for thick low-infill short-CF/PA6; twin-hole layout −36 %, print-axis rotation +30 %:
  https://www.jstage.jst.go.jp/article/agorajams/2024/0/2024_paper24004/_article/-char/en
- Short-CF nylon pin-bearing optimum: gyroid, 50 %, 45° raster: https://link.springer.com/article/10.1007/s40964-025-00975-z
- No published fatigue bearing data for FDM PAHT-CF. Bearing and washer-bearing allowables use XY × 0.8 and the
  0.3 fatigue ratio (ASSUMPTION, CT-B3).

## 4. Heat-set inserts

- Record `insert_heatset_brass_m5`: 1200 N pull-out is an ASSUMPTION (PEM IUTA-M5 in ABS 1197 N,
  https://www.pemnet.com/products/product-finder/iuta-m5/ ); MJF PA12 > 1800 N (Sculpteo,
  https://www.sculpteo.com/en/3d-learning-hub/design-guidelines/pull-out-resistance-of-threaded-inserts-testing-and-results/ ).
- Layer direction: no peer-reviewed study isolates it. CNC Kitchen-based summaries report inserts perpendicular to
  the layers often doing better; forum practice recommends the axis parallel to the layers; perimeter count around
  the hole dominates retention: https://www.sovol3d.com/blogs/news/3d-printing-with-heat-set-inserts-design-strong-screw-bosses-that-last ,
  https://xometry.pro/en/topic/improving-heat-set-insert-retention-in-fdm-printed-abs-brackets/ . Conflicting
  evidence → CT-B5 in the actual orientation.
- No published insert fatigue in FDM nylon: ASSUMPTION 0.3 × static (CT-B5).

## 5. Bolts

- M5 stress area 14.2 mm² (ISO 898-1 / ISO 724 thread table): https://www.engineeringtoolbox.com/metric-threads-d_777.html (standard value; URL not re-fetched this session)
- Ti-6Al-4V (Gr5) UTS ≥ 895 MPa (ASTM B348 / F136 minimum): https://www.astm.org/f0136-13r21.html (standard minimum; URL not re-fetched this session)
- Rolled-thread Ti fastener endurance ≥ 0.25 UTS on As at R ≈ 0: ASSUMPTION (CT-B4 runs the bolts in the joint).

## 6. Printer

- Bambu H2S build volume 340 × 320 × 340 mm (retailer listings; no Bambu spec page found in the search):
  https://core-electronics.com.au/bambu-lab-h2s-3d-printer-machine-only.html ,
  https://top3dshop.com/product/bambu-lab-h2s-3d-printer . The 540 mm body must be cut once across both stays at
  z 200–340.

## 7. Patents

The SEG entry keeps the released branch body, the crown and every fixed interface. The flange joint is an internal
frame joint (bolted butt flange), not a frame-to-bag or lifter feature, so the Mystery Ranch crown/lifter guardrail
(US 10,952,523) and the `docs/DECISIONS.md` guardrails are not touched. Bolted flange joints of tubes are generic
prior art; no claim search beyond the repo guardrails was run (ASSUMPTION: no freedom-to-operate issue for a
generic bolted flange).
