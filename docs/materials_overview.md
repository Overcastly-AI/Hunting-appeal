# Materials overview

Source of truth: `data/materials/<category>/<id>.yaml` (contract: `docs/CONTRACTS.md` §1).
Browse with `python -m huntkit.materials.cli list | show <id> | compare <id> <id> ... | validate`.
The tables below were generated from the database (72 records). Units are SI. The quick
imperial conversions are 1 MPa = 145 psi, 1 N = 0.225 lbf, 1 gsm = 0.0295 oz/yd², 1 kg/m³ = 0.0624 lb/ft³.

**How far to trust the numbers.** `confidence` is set honestly in each record:
- **handbook**: metals, E-glass and T300 weave, the polymers and bonded nylon thread. These come
  from MMPDS/ASM/CMH-17-class tables and you can design to them. Use the MMPDS S-basis
  values for load-path metal parts.
- **datasheet**: T700/M40J (fiber-maker composite data, with transverse values estimated as
  noted), POM, PA66-GF30 and 850 FP down (the IDFB purchase spec).
- **estimate**: most fabrics, laminates, foams, webbing, zippers, buckles and cord. These are
  typical vendor or mill ranges and the exact numbers vary by lot and supplier. **Before release,
  pull-test or get mill certificates** for anything in the load path (webbing, buckles, thread,
  body fabric seam strength). Buying mil-spec webbing with a certificate turns its value into a
  datasheet value.

Hunting-specific properties: `quietness_1to5` (5 = silent against brush) and `uv_brighteners`
(every dyed fabric must be bought optical-brightener-free, because ungulates see UV). Where it
matters there is also `ir_notes` (NIR contrast of dyes and films).

## Property tables

### Metals (5)

| id | rho kg/m3 | E MPa | Sy MPa | Su MPa | Se MPa | cost | conf. |
|---|---|---|---|---|---|---|---|
| `alu_6061_t6` | 2700 | 68900 | 276 | 310 | 96.5 | $8/kg | handbook |
| `alu_7001_t6_tube` | 2840 | 71000 | 627 | 676 | 150 | $6/m | handbook |
| `alu_7075_t6` | 2810 | 71700 | 503 | 572 | 159 | $15/kg | handbook |
| `ti_3al_2_5v_tube` | 4480 | 100000 | 724 | 862 | - | $80/kg | handbook |
| `ti_6al_4v` | 4430 | 113800 | 880 | 950 | 510 | $60/kg | handbook |

### Composites (per ply) (5)

| id | rho kg/m3 | E1 MPa | E2 MPa | Xt MPa | Xc MPa | t_ply mm | cost | conf. |
|---|---|---|---|---|---|---|---|---|
| `cfrp_m40j_ud_epoxy_ply` | 1600 | 230000 | 7000 | 2450 | 1270 | 0.125 | $180/kg | datasheet |
| `cfrp_pultruded_rod_tube` | 1550 | 125000 | 7000 | 2000 | 1200 | - | $8/m | estimate |
| `cfrp_t300_3k_woven_epoxy_ply` | 1500 | 58000 | 58000 | 600 | 570 | 0.22 | $45/m2 | handbook |
| `cfrp_t700_ud_epoxy_ply` | 1580 | 135000 | 8800 | 2550 | 1470 | 0.125 | $70/kg | datasheet |
| `gfrp_eglass_ud_epoxy_ply` | 1800 | 38600 | 8270 | 1062 | 610 | 0.125 | $20/kg | handbook |

### Polymers (5)

| id | rho kg/m3 | E MPa | Sy MPa | Su MPa | elong % | cost | conf. |
|---|---|---|---|---|---|---|---|
| `hdpe_sheet` | 955 | 1100 | 26 | - | 600 | $6/kg | handbook |
| `pa66_gf30` | 1370 | 9500 | - | 185 | 3 | $5/kg | datasheet |
| `pom_acetal` | 1420 | 3100 | 70 | - | 25 | $15/kg | datasheet |
| `tpu_sheet_film` | 1200 | - | - | 40 | 550 | $20/kg | estimate |
| `uhmwpe_sheet` | 935 | 690 | 21 | - | 350 | $12/kg | handbook |

### Textiles (pack and apparel) (17)

| id | gsm | denier | grab warp N | tear warp N | stretch % | quiet 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|---|
| `brushed_poly_knit_shell` | 230 | - | - | - | 20 | 5 | $14/yd | estimate |
| `cordura_1000d_nylon66` | 340 | 1000 | 2200 | 200 | - | 2 | $17/yd | estimate |
| `cordura_330d_nylon66` | 180 | 330 | 1000 | 90 | - | 3 | $14/yd | estimate |
| `cordura_500d_nylon66` | 255 | 500 | 1550 | 130 | - | 3 | $15/yd | estimate |
| `grid_fleece_poly` | 160 | - | - | - | 40 | 5 | $18/yd | estimate |
| `hypalon_coated_nylon` | 1000 | - | 1800 | - | - | 4 | $35/yd | estimate |
| `merino_150_jersey` | 150 | - | - | - | 30 | 5 | $25/yd | estimate |
| `merino_190_jersey` | 190 | - | - | - | 30 | 5 | $28/yd | estimate |
| `merino_250_interlock` | 250 | - | - | - | 35 | 5 | $32/yd | estimate |
| `merino_synthetic_blend_core_spun` | 170 | - | - | - | 35 | 5 | $24/yd | estimate |
| `power_mesh_nylon_spandex` | 170 | - | - | - | 150 | 5 | $10/yd | estimate |
| `robic_100d_ripstop` | 90 | 100 | 550 | 45 | - | 3 | $16/yd | estimate |
| `robic_210d_ripstop` | 140 | 210 | 900 | 80 | - | 3 | $18/yd | estimate |
| `softshell_nylon_spandex_stretch_woven` | 170 | - | - | - | 25 | 3 | $20/yd | estimate |
| `spacer_mesh_3d` | 380 | - | - | - | 10 | 5 | $15/yd | estimate |
| `tpu_coated_nylon_840d` | 480 | 840 | 2400 | 220 | - | 2 | $22/yd | estimate |
| `ultragrid_210d_uhmwpe_ripstop` | 155 | 210 | 1300 | 180 | - | 3 | $20/yd | estimate |

### Laminates and membranes (7)

| id | gsm | HH mm | RET | tear warp N | quiet 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|
| `challenge_ultra_200` | 125 | 20000 | - | 250 | 2 | $50/yd | estimate |
| `dcf_ct9hk_18` | 48.5 | 20000 | - | - | 1 | $45/yd | estimate |
| `dcf_hybrid_150d` | 99 | 20000 | - | - | 2 | $55/yd | estimate |
| `laminate_3l_eptfe` | 150 | 28000 | 6 | - | 2 | $35/yd | estimate |
| `laminate_3l_pu_nanofiber` | 140 | 15000 | 4 | - | 3 | $28/yd | estimate |
| `laminate_3l_quiet_tricot` | 260 | 10000 | 12 | - | 4 | $30/yd | estimate |
| `xpac_vx21` | 200 | 20000 | - | 120 | 2 | $25/yd | estimate |

### Insulation (4)

| id | gsm | FP in3/oz | loft mm | clo | quiet 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|
| `active_insulation_alpha_class` | 100 | - | 6 | 0.9 | 5 | $28/yd | estimate |
| `down_850fp_hydrophobic` | - | 850 | - | - | 5 | $450/kg | datasheet |
| `synthetic_insulation_100gsm` | 100 | - | 13 | 1.5 | 5 | $14/yd | estimate |
| `synthetic_insulation_60gsm` | 60 | - | 8 | 0.9 | 5 | $12/yd | estimate |

### Foams (5)

| id | rho kg/m3 | Shore C | CFD 25% kPa | set % | closed | cost | conf. |
|---|---|---|---|---|---|---|---|
| `eva_foam_30c` | 65 | 30 | 45 | 20 | yes | $20/m2 | estimate |
| `eva_foam_45c` | 110 | 45 | 120 | 15 | yes | $25/m2 | estimate |
| `eva_foam_perforated` | 55 | 35 | 35 | 20 | yes | $28/m2 | estimate |
| `pu_memory_foam` | 64 | - | 3 | 5 | no | $30/m2 | estimate |
| `xlpe_foam` | 33 | - | 60 | 20 | yes | $15/m2 | estimate |

### Webbing (6)

| id | width mm | break N | g/m | fiber | cost | conf. |
|---|---|---|---|---|---|---|
| `nylon_webbing_25mm` | 25 | 17792 | 18 | nylon 6,6 | $0.7/m | estimate |
| `nylon_webbing_38mm` | 38 | 26688 | 28 | nylon 6,6 | $1/m | estimate |
| `nylon_webbing_50mm` | 50 | 31136 | 38 | nylon 6,6 | $1.5/m | estimate |
| `poly_webbing_25mm` | 25 | 13344 | 18 | polyester | $0.7/m | estimate |
| `poly_webbing_38mm` | 38 | 20016 | 28 | polyester | $1/m | estimate |
| `poly_webbing_50mm` | 50 | 26688 | 38 | polyester | $1.5/m | estimate |

### Thread (5)

| id | tex | ticket | break N | fiber | cost | conf. |
|---|---|---|---|---|---|---|
| `bonded_nylon_tex135` | 135 | 138 | 98 | bonded continuous-filament nylon 6,6 | $0.0081/m | handbook |
| `bonded_nylon_tex70` | 70 | 69 | 49 | bonded continuous-filament nylon 6,6 | $0.0052/m | handbook |
| `bonded_nylon_tex90` | 90 | 92 | 64 | bonded continuous-filament nylon 6,6 | $0.0061/m | handbook |
| `bonded_poly_tex70` | 70 | 69 | 45 | bonded continuous-filament polyester | $0.0052/m | estimate |
| `bonded_poly_tex90` | 90 | 92 | 58 | bonded continuous-filament polyester | $0.0061/m | estimate |

### Hardware (13)

| id | width mm | zip # | break N | crosswise N | g | g/m | quiet 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|---|---|
| `aquaguard_zipper_5` | - | 5 | - | 450 | - | 14 | 3 | $6/m | estimate |
| `aquaguard_zipper_8` | - | 8 | - | 650 | - | 19 | 3 | $8/m | estimate |
| `buckle_side_release_25mm` | 25 | - | 450 | - | 9 | - | 3 | $0.8/unit | estimate |
| `buckle_side_release_38mm` | 38 | - | 900 | - | 18 | - | 3 | $1.5/unit | estimate |
| `buckle_side_release_50mm` | 50 | - | 1500 | - | 35 | - | 3 | $3/unit | estimate |
| `coil_zipper_10` | - | 10 | - | 900 | - | 20 | 4 | $4/m | estimate |
| `coil_zipper_5` | - | 5 | - | 500 | - | 10 | 4 | $2/m | estimate |
| `coil_zipper_8` | - | 8 | - | 700 | - | 15 | 4 | $3/m | estimate |
| `cord_lock_spring` | - | - | - | - | 2.5 | - | 4 | $0.4/unit | estimate |
| `dyneema_cord_2mm` | - | - | 1800 | - | - | 2.5 | 5 | $0.6/m | estimate |
| `dyneema_cord_3mm` | - | - | 3500 | - | - | 5.5 | 5 | $0.9/m | estimate |
| `fidlock_magnetic_buckle_25mm` | 25 | - | 300 | - | 15 | - | 4 | $6/unit | estimate |
| `ladder_lock_25mm` | 25 | - | 600 | - | 4 | - | 4 | $0.4/unit | estimate |

## Recommended picks

### (a) Pack frame
Specific yield strength in MPa/(g/cm³): 7001-T6 **221**, Ti-6Al-4V 199, 7075-T6 179 (S-basis 164),
Ti-3Al-2.5V 162, 6061-T6 102. Specific stiffness is about the same (~25) for every Al and Ti alloy.

| Part | Pick | Why | Alternates |
|---|---|---|---|
| Stays / perimeter rods | `alu_7001_t6_tube` | Best strength-to-weight metal tube, isotropic so FEA is straightforward, field-repairable, cheap | `cfrp_t700_ud_epoxy_ply` core + `cfrp_t300_3k_woven_epoxy_ply` hoop/outer wrap for a premium carbon stay (~35-45% lighter at equal stiffness; needs layup tooling and impact knockdowns); `ti_3al_2_5v_tube` for a bent, weldable premium frame |
| Hubs, load-lifter and hipbelt pivots | `alu_7075_t6` machined (`ti_6al_4v` pins) | High S-basis strength, machinable, can be dark-anodized (no glint) | `pa66_gf30` molded in production (design to the conditioned values) |
| Framesheet | `hdpe_sheet` 1.6-2.0 mm | Tough to below -40 °C, quiet, cheap; spreads load into the back panel | `gfrp_eglass_ud_epoxy_ply` ribs where you need local stiffness |
| Wear strips / stay pockets | `uhmwpe_sheet` | Best abrasion, lowest friction | — |
| Avoid | `cfrp_pultruded_rod_tube` for bent or pinned stays (splits in hoop); `cfrp_m40j_ud_epoxy_ply` alone (brittle under rock strikes) | | |

The final stay section and material are decided by the structural-FEA checks: SF ≥ 2.0 on
yield, 68 kg × 2.5 g, with fatigue checked separately against `fatigue_limit_mpa` plus notch factors.

### (b) Pack body (5200 cu in)
| Zone | Pick | Why |
|---|---|---|
| Main body | `cordura_500d_nylon66` | Best balance of abrasion, quietness (3/5), sewability and price. Available in NIR-managed solid colors and printable |
| Bottom, load-shelf, hipbelt outer face | `cordura_1000d_nylon66` or `tpu_coated_nylon_840d` | Rock and scree abrasion. TPU-840D resists hydrolysis and can be welded |
| Lid, side pockets (weight-saving) | `robic_210d_ripstop` / `ultragrid_210d_uhmwpe_ripstop` | ~40% lighter than 500D. Ultragrid gives ~2x the tear strength |
| Linings, dividers, meat-bag sleeve | `robic_100d_ripstop` | Light and strong enough |
| Lash tabs, daisy plates | `hypalon_coated_nylon` (laser-cut) | Doesn't fray, quiet. `tpu_coated_nylon_840d` is the lighter option |
| Stretch pockets | `power_mesh_nylon_spandex` | |
| Thread | `bonded_nylon_tex90` body seams; `bonded_nylon_tex135` webbing and bartacks; `bonded_poly_tex70` exposed topstitch | Nylon for strength. Polyester resists UV where seams sit in the sun |
| Zippers | `coil_zipper_10` main access, `coil_zipper_8` pockets, `aquaguard_zipper_8` lid/top-loader if you want weather resistance | Coil is quieter than molded teeth. Use cord pulls |
| UL premium variant | `challenge_ultra_200` | Best abrasion-per-gram, waterproof. Costly, few colors, louder |
| Avoid as outer fabric | `dcf_ct9hk_18`, `dcf_hybrid_150d` | Crinkle noise (1-2/5) and poor puncture/abrasion against brush |

### (c) Hipbelt and harness
| Part | Pick | Why |
|---|---|---|
| Load layer | `eva_foam_45c` (8 mm, heat-formed) | Firm, low compression set, closed-cell (won't take up water or blood) |
| Comfort layer | `eva_foam_30c` (6 mm) or `eva_foam_perforated` | Soft against the body. The perforated version vents |
| Body-contact face | `spacer_mesh_3d` | Ventilated, silent |
| Belt stiffener | `hdpe_sheet` 1.5 mm or `gfrp_eglass_ud_epoxy_ply` strip | Transfers load from the frame to the iliac crest |
| Hipbelt strap / buckle | `nylon_webbing_50mm` + `buckle_side_release_50mm` | Strength margin is large. Nylon's stretch absorbs shock |
| Shoulder straps, load lifters, compression | `poly_webbing_25mm` / `poly_webbing_38mm` + `ladder_lock_25mm` | Polyester doesn't sag when wet. Holds adjustment |
| Sternum, lid | `fidlock_magnetic_buckle_25mm` | One-handed, quieter. Not for primary load |
| Lashing / bow-rifle carry | `dyneema_cord_2mm` + `cord_lock_spring` | Specify no reflective tracer |
| Avoid | `pu_memory_foam` (soaks up water, stiffens in cold), `xlpe_foam` as the only belt layer (compression set) | |

### (d) Apparel layers
| Layer | Pick | Why |
|---|---|---|
| Base (all-season) | `merino_synthetic_blend_core_spun` ~170 gsm | Merino's odor control with ~2x the abrasion life under pack straps |
| Base (early / late season) | `merino_150_jersey` / `merino_250_interlock` | Weight steps for the temperature range. `merino_190_jersey` covers the middle |
| Active mid | `grid_fleece_poly` | Silent, breathable, cheap |
| Active insulation (move in the cold) | `active_insulation_alpha_class` | Lofts under air-permeable shells, dumps heat on climbs |
| Soft shell (pants, active jacket) | `softshell_nylon_spandex_stretch_woven` | Rock/scree abrasion, stretch, DWR |
| Quiet outer (bowhunting) | `brushed_poly_knit_shell` | Quietness 5/5; sublimation-printable for original camo |
| Rain shell (active) | `laminate_3l_pu_nanofiber` | Free of PFAS, most breathable on climbs |
| Rain shell (quiet) | `laminate_3l_quiet_tricot` | Quietness 4/5 for stalking in rain. Heavier and less breathable |
| Insulation: glassing parka (dry cold) | `down_850fp_hydrophobic` (PFC-free treatment) | Best warmth-to-weight and packability |
| Insulation: wet climates, vest | `synthetic_insulation_100gsm` / `synthetic_insulation_60gsm` | Keeps ~90% of its warmth when wet |
| Benchmark only | `laminate_3l_eptfe` | Highest HH, but it is PFAS (being phased out) and its woven face is loud |

## Open questions / caveats
- Textile, foam and hardware values are mostly **estimates**. Get mill test reports (grab/tear,
  Martindale, HH, RET) and supplier certificates for the chosen SKUs, then update the YAML and
  raise `confidence`.
- Webbing mil-spec Type/Class numbers in `sources` name the spec family. Confirm the exact
  Type/Class and minimum breaking strength when you buy.
- The carbon stay option needs a defined layup and tooling, plus impact/hot-wet knockdowns in the
  FEA (the notes in the records give suggested factors).
- Printing original camo onto CORDURA/UHMWPE needs a mill partner with MOQs, typically 500-1000 m.
  Brushed polyester knit can be sublimation-printed in small batches.
