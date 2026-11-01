# Materials overview

Source of truth: `data/materials/<category>/<id>.yaml` (contract: `docs/CONTRACTS.md` §1).
Browse with `python -m huntkit.materials.cli list | show <id> | compare <id> <id> ... | validate`.
The tables below were generated from the database (84 records). Units are SI. The quick imperial
conversions are 1 MPa = 145 psi, 1 N = 0.225 lbf, 1 gsm = 0.0295 oz/yd², 1 kg/m³ = 0.0624 lb/ft³.

These picks reflect the owner decisions of 2026-11-01 in `docs/DECISIONS.md`:
- the frame is **carbon**, built without an autoclave from bought tubes and plate with bonded joints;
- the **primary mission is meat hauling**;
- the colorways are **mostly solids, with camo accent panels** in high-wear zones;
- the pack must give a **universal fit**;
- the builder is a **beginner**.

**How far to trust the numbers.** `confidence` is set honestly in each record:
- **handbook**: metals, E-glass and T300 weave, the polymers and bonded nylon thread. These come
  from MMPDS/ASM/CMH-17-class tables.
- **datasheet**: T700/M40J ply data, POM, PA66-GF30, 850 FP down and the DP460-class epoxy.
- **estimate**: most fabrics, laminates, foams, webbing, hardware, carbon tube/plate stock,
  methacrylate adhesive and inserts. **Before release, coupon-test or get certificates** for
  everything in the load path:
  - bonded joints;
  - a tube 3-point bend test per batch;
  - webbing, buckles, thread and seam strength.

Hunting and meat properties:
- `quietness_1to5` (5 = silent against brush) and `uv_brighteners` (every dyed fabric must be
  bought optical-brightener-free);
- `ir_notes`;
- `coating`, `hydrolysis_resistance_1to5`, `washability_1to5` and `stain_odor_resistance_1to5`.
  These four are engineering-judgment rankings, marked as estimates.

Adhesives sit under `polymers` because the contract has no adhesives category.

## Property tables

### Metals (5)

| id | rho kg/m3 | E MPa | Sy MPa | Su MPa | Se MPa | cost | conf. |
|---|---|---|---|---|---|---|---|
| `alu_6061_t6` | 2700 | 68900 | 276 | 310 | 96.5 | $8/kg | handbook |
| `alu_7001_t6_tube` | 2840 | 71000 | 627 | 676 | 150 | $6/m | handbook |
| `alu_7075_t6` | 2810 | 71700 | 503 | 572 | 159 | $15/kg | handbook |
| `ti_3al_2_5v_tube` | 4480 | 100000 | 724 | 862 | - | $80/kg | handbook |
| `ti_6al_4v` | 4430 | 113800 | 880 | 950 | 510 | $60/kg | handbook |

### Composites (per ply) (9)

| id | rho kg/m3 | E lam. MPa | Su lam. MPa | E1 MPa | E2 MPa | Xt MPa | Xc MPa | t_ply mm | cost | conf. |
|---|---|---|---|---|---|---|---|---|---|---|
| `cfrp_m40j_ud_epoxy_ply` | 1600 | - | - | 230000 | 7000 | 2450 | 1270 | 0.125 | $180/kg | datasheet |
| `cfrp_plate_0_90_woven` | 1500 | - | - | 55000 | 55000 | 580 | 500 | - | $250/m2 | estimate |
| `cfrp_plate_pm45` | 1550 | 17000 | 180 | - | - | - | - | - | $350/m2 | estimate |
| `cfrp_plate_quasi_iso` | 1550 | 45000 | 550 | - | - | - | - | - | $350/m2 | estimate |
| `cfrp_pultruded_rod_tube` | 1550 | - | - | 125000 | 7000 | 2000 | 1200 | - | $8/m | estimate |
| `cfrp_rollwrapped_tube` | 1550 | 75000 | 650 | - | - | - | - | - | $30/m | estimate |
| `cfrp_t300_3k_woven_epoxy_ply` | 1500 | - | - | 58000 | 58000 | 600 | 570 | 0.22 | $45/m2 | handbook |
| `cfrp_t700_ud_epoxy_ply` | 1580 | - | - | 135000 | 8800 | 2550 | 1470 | 0.125 | $70/kg | datasheet |
| `gfrp_eglass_ud_epoxy_ply` | 1800 | - | - | 38600 | 8270 | 1062 | 610 | 0.125 | $20/kg | handbook |

### Polymers and structural adhesives (7)

| id | rho kg/m3 | E MPa | Sy MPa | Su MPa | elong % | lap shear MPa | peel N/mm | T max C | cost | conf. |
|---|---|---|---|---|---|---|---|---|---|---|
| `adhesive_epoxy_toughened_2part` | 1150 | - | - | - | 4 | 30 | 5 | 80 | $25/unit | datasheet |
| `adhesive_methacrylate_ma` | 980 | - | - | - | 20 | 24 | 8 | 120 | $35/unit | estimate |
| `hdpe_sheet` | 955 | 1100 | 26 | - | 600 | - | - | - | $6/kg | handbook |
| `pa66_gf30` | 1370 | 9500 | - | 185 | 3 | - | - | - | $5/kg | datasheet |
| `pom_acetal` | 1420 | 3100 | 70 | - | 25 | - | - | - | $15/kg | datasheet |
| `tpu_sheet_film` | 1200 | - | - | 40 | 550 | - | - | - | $20/kg | estimate |
| `uhmwpe_sheet` | 935 | 690 | 21 | - | 350 | - | - | - | $12/kg | handbook |

### Textiles (pack and apparel) (21)

| id | gsm | denier | grab warp N | tear warp N | stretch % | quiet 1-5 | hydrol. 1-5 | wash 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|---|---|---|
| `brushed_poly_knit_shell` | 230 | - | - | - | 20 | 5 | - | - | $14/yd | estimate |
| `cordura_1000d_nylon66` | 340 | 1000 | 2200 | 200 | - | 2 | 2 | 4 | $17/yd | estimate |
| `cordura_330d_nylon66` | 180 | 330 | 1000 | 90 | - | 3 | 2 | 4 | $14/yd | estimate |
| `cordura_500d_nylon66` | 255 | 500 | 1550 | 130 | - | 3 | 2 | 4 | $15/yd | estimate |
| `grid_fleece_poly` | 160 | - | - | - | 40 | 5 | - | - | $18/yd | estimate |
| `hypalon_coated_nylon` | 1000 | - | 1800 | - | - | 4 | 4 | 4 | $35/yd | estimate |
| `merino_150_jersey` | 150 | - | - | - | 30 | 5 | - | - | $25/yd | estimate |
| `merino_190_jersey` | 190 | - | - | - | 30 | 5 | - | - | $28/yd | estimate |
| `merino_250_interlock` | 250 | - | - | - | 35 | 5 | - | - | $32/yd | estimate |
| `merino_synthetic_blend_core_spun` | 170 | - | - | - | 35 | 5 | - | - | $24/yd | estimate |
| `poly_spandex_stretch_woven_printable` | 180 | - | - | - | 20 | 4 | - | - | $18/yd | estimate |
| `polyester_ht_630d_printable` | 290 | 630 | 1500 | 120 | - | 3 | 4 | 5 | $18/yd | estimate |
| `power_mesh_nylon_spandex` | 170 | - | - | - | 150 | 5 | 5 | 3 | $10/yd | estimate |
| `pvc_coated_polyester_18oz` | 610 | - | 1800 | 450 | - | 1 | 4 | 5 | $12/yd | estimate |
| `robic_100d_ripstop` | 90 | 100 | 550 | 45 | - | 3 | 2 | 4 | $16/yd | estimate |
| `robic_210d_ripstop` | 140 | 210 | 900 | 80 | - | 3 | 2 | 4 | $18/yd | estimate |
| `silicone_coated_poly_ripstop_40d` | 45 | 40 | - | 25 | - | 3 | 5 | 4 | $10/yd | estimate |
| `softshell_nylon_spandex_stretch_woven` | 170 | - | - | - | 25 | 3 | - | - | $20/yd | estimate |
| `spacer_mesh_3d` | 380 | - | - | - | 10 | 5 | 5 | 4 | $15/yd | estimate |
| `tpu_coated_nylon_840d` | 480 | 840 | 2400 | 220 | - | 2 | 4 | 5 | $22/yd | estimate |
| `ultragrid_210d_uhmwpe_ripstop` | 155 | 210 | 1300 | 180 | - | 3 | 2 | 4 | $20/yd | estimate |

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

### Hardware (15)

| id | width mm | zip # | break N | crosswise N | g | g/m | pull-out N | quiet 1-5 | cost | conf. |
|---|---|---|---|---|---|---|---|---|---|---|
| `aquaguard_zipper_5` | - | 5 | - | 450 | - | 14 | - | 3 | $6/m | estimate |
| `aquaguard_zipper_8` | - | 8 | - | 650 | - | 19 | - | 3 | $8/m | estimate |
| `buckle_side_release_25mm` | 25 | - | 450 | - | 9 | - | - | 3 | $0.8/unit | estimate |
| `buckle_side_release_38mm` | 38 | - | 900 | - | 18 | - | - | 3 | $1.5/unit | estimate |
| `buckle_side_release_50mm` | 50 | - | 1500 | - | 35 | - | - | 3 | $3/unit | estimate |
| `coil_zipper_10` | - | 10 | - | 900 | - | 20 | - | 4 | $4/m | estimate |
| `coil_zipper_5` | - | 5 | - | 500 | - | 10 | - | 4 | $2/m | estimate |
| `coil_zipper_8` | - | 8 | - | 700 | - | 15 | - | 4 | $3/m | estimate |
| `cord_lock_spring` | - | - | - | - | 2.5 | - | - | 4 | $0.4/unit | estimate |
| `dyneema_cord_2mm` | - | - | 1800 | - | - | 2.5 | - | 5 | $0.6/m | estimate |
| `dyneema_cord_3mm` | - | - | 3500 | - | - | 5.5 | - | 5 | $0.9/m | estimate |
| `fidlock_magnetic_buckle_25mm` | 25 | - | 300 | - | 15 | - | - | 4 | $6/unit | estimate |
| `insert_al_7075_bonded` | - | - | - | - | 4 | - | 3000 | 5 | $4/unit | estimate |
| `insert_ti_6al_4v_bonded` | - | - | - | - | 6 | - | 3000 | 5 | $15/unit | estimate |
| `ladder_lock_25mm` | 25 | - | 600 | - | 4 | - | - | 4 | $0.4/unit | estimate |

## Recommended picks

### (a) Pack frame: carbon, beginner-buildable
The frame is made of straight bought tubes, bonded into plate/sleeve nodes, with metal inserts at
every hard point. It needs no autoclave, no tube bending and no layup tooling.

| Part | Pick | Why | Notes |
|---|---|---|---|
| Stays, cross members, extension | `cfrp_rollwrapped_tube` (Rock West / DragonPlate / Clearwater class) | Woven/±45 wraps give hoop and torsion strength that pultruded tube lacks. Bought ready-made, so it is consistent | Straight only. Get the vendor's layup and model it with `composite_tube(od, layup, ply id)` (`cfrp_t700_ud_epoxy_ply` and `cfrp_t300_3k_woven_epoxy_ply`) |
| Nodes, gussets, load-lifter and hipbelt-pivot plates | `cfrp_plate_quasi_iso` ~3 mm | Same stiffness in every direction, best bolt/pin bearing strength | Use sandwich gussets bonded on both sides of the tube with a saddle filler. Cut wet, with a dust mask |
| Shear/torsion webs | `cfrp_plate_pm45` | Highest shear stiffness | — |
| Load shelf plate, framesheet stiffeners | `cfrp_plate_0_90_woven` | Cheapest carbon plate. Orient 0/90 along the load | Or `hdpe_sheet` framesheet (tough, quiet) |
| Bonded joints | `adhesive_epoxy_toughened_2part` (3M DP460 / Loctite EA 9460 class) | ~30 MPa lap shear and a forgiving 60 min work life for a first-timer | Design shear joints with ≥ 25 mm overlap and no peel. Allow ≤ 1/3 of lap shear in design. 0.2 mm glass-bead bondline. Sand + solvent prep, then post-cure at 65 °C |
| Repairs / backup adhesive | `adhesive_methacrylate_ma` (Plexus MA class) | Minimal prep, tough in peel and impact | ~10 min work life is too short for a full frame dry-fit |
| Hard points that are highly loaded or sit in the wet meat zone | `insert_ti_6al_4v_bonded` | Galvanically compatible with carbon, good fatigue | Shelf-strap anchors, hipbelt pivot |
| Lighter-duty hard points | `insert_al_7075_bonded` | Lighter, cheaper | Must be **hard-anodized and isolated** (bondline or E-glass ply / G10 washer). Bare Al touching carbon corrodes, and salty blood speeds it up |
| Galvanic barrier ply | `gfrp_eglass_ud_epoxy_ply` | Electrically insulating, tough | One ply wherever metal meets carbon |
| Avoid | `cfrp_pultruded_rod_tube` as frame members (splits in hoop at joints); `cfrp_m40j_ud_epoxy_ply` (brittle under rock strikes) | | |
| Comparison baseline only | `alu_7001_t6_tube`, `alu_7075_t6`, `alu_6061_t6`, `ti_3al_2_5v_tube` | Specific stiffness: Al ≈ 25 vs roll-wrapped carbon ≈ 48 MPa·m³/kg, so carbon is ~1.9x Al at equal stiffness | Al stays work for quick prototype mock-ups |

The structural-FEA checks size the members: SF ≥ 2.0 on yield at 68 kg × 2.5 g, plus SF ≥ 1.5
in the 91 kg overload case. Bondline shear and insert pull-out must be checked as separate failure
modes. Hot-car temperature matters: epoxy loses strength above ~60 °C.

### (b) Pack body, load shelf and meat zone
**Meat-hauling ranking.** Hydrolysis life by coating, best first: silicone > ether-TPU ≈ CSM > PVC
> ester-TPU > standard PU. Wash blood with cold water and an enzyme cleaner (hot water sets blood
protein). Don't use chlorine bleach on nylon or PU. Air-dry.

| Fabric | Coating | Hydrolysis | Wash | Stain/odor | Abrasion (Taber) | Use |
|---|---|---|---|---|---|---|
| `tpu_coated_nylon_840d` | ether-TPU | 4 | 5 | 4 | ~4000 | **Load shelf, bag bottom, meat-side panels** |
| `hypalon_coated_nylon` | CSM | 4 | 4 | 4 | ~5000 | Lash tabs, wear patches |
| `pvc_coated_polyester_18oz` | PVC | 4 | 5 | 5 | high | Removable shelf liner only (heavy, loud, cracks in cold) |
| `silicone_coated_poly_ripstop_40d` | silicone | 5 | 4 | 4 | low | Removable washable quarter sleeve / shelf liner |
| `polyester_ht_630d_printable` | ether-TPU | 4 | 5 | 3 | ~1000 | Camo accent panels |
| `cordura_1000d_nylon66` / `cordura_500d_nylon66` | standard PU | 2 | 4 | 3 | ~3000 / ~1500 | Body away from the meat zone (order TPU-coated if offered) |
| `xpac_vx21`, `challenge_ultra_200` | film laminate | 3 | 3 | 4 | — | Lid/pockets only. Repeated washing risks delamination |
| `dcf_*` | film | 3 | 2 | 3–4 | low | Not recommended (loud, punctures) |

| Zone | Pick | Why |
|---|---|---|
| **Load shelf fabric** | `tpu_coated_nylon_840d` (specify **ether** TPU), with a removable `silicone_coated_poly_ripstop_40d` liner as an option | Highest abrasion and tear among the washable fabrics. Survives blood plus repeated washing. Wipes clean. RF-weldable. Add drain grommets |
| Main body (solid color) | `cordura_500d_nylon66` (TPU-coated version if the mill offers it) | Abrasion, quietness and sewability. Away from direct meat contact |
| Bottom and frame-side panel | `tpu_coated_nylon_840d` | Meat, mud and rock contact |
| Lid, side pockets (weight-saving) | `robic_210d_ripstop` / `ultragrid_210d_uhmwpe_ripstop` | Light and strong |
| Camo accent panels (lid, pocket faces, hipbelt wings) | `polyester_ht_630d_printable` (sublimation, small batch) → rotary-printed `cordura_500d_nylon66` at production MOQ (~1000 m) | Printable in small runs. Add 1000D/840D overlays on corners. Match NIR across the solid nylon and printed polyester panels |
| Linings, dividers | `robic_100d_ripstop` | — |
| Thread | `bonded_nylon_tex90` body; `bonded_nylon_tex135` webbing and bartacks; `bonded_poly_tex70`/`tex90` for exposed and meat-zone seams | Polyester takes up less water and resists UV |
| Zippers | `coil_zipper_10` main, `coil_zipper_8` pockets, `aquaguard_zipper_8` lid | Coil is quieter. Rinse grit and blood out of the coils |
| Antimicrobial | ASSUMPTION: wash-durable zinc/silver-salt odor treatment (Polygiene/HeiQ class) on the mesh and liners only. No triclosan | Washability is the primary control. Treatments are secondary |

### (c) Hipbelt and harness (universal fit)
| Part | Pick | Why |
|---|---|---|
| Foam in the meat zone and the whole harness | **Closed-cell only**: `eva_foam_45c` load layer + `eva_foam_30c` / `eva_foam_perforated` comfort layer; `xlpe_foam` for the back panel | Doesn't take up blood or water. Rinseable. **No `pu_memory_foam`** |
| Body face | `spacer_mesh_3d` (polyester) | Open structure rinses clean and dries fast |
| Harness/belt shell, wear faces | `tpu_coated_nylon_840d` outer, `cordura_500d_nylon66` elsewhere | Washable |
| Belt stiffener | `hdpe_sheet` 1.5 mm or `cfrp_plate_0_90_woven` 1 mm | Transfers load to the iliac crest |
| Hipbelt strap / buckle | `nylon_webbing_50mm` + `buckle_side_release_50mm` | Shock absorption, big margin |
| Load lifters, compression (wide, load-spreading, meat-safe) | `poly_webbing_38mm` / `poly_webbing_50mm` + `ladder_lock_25mm` | Polyester doesn't sag when wet with blood or rain |
| Sternum, lid | `fidlock_magnetic_buckle_25mm` | Quiet, one-handed |
| **Torso-adjust track** | Rail in `pa66_gf30` (design to the *conditioned* values) or a `cfrp_plate_0_90_woven` track, with sliders and shoes in `uhmwpe_sheet` | UHMWPE runs on GF-nylon or carbon with low friction, no squeak and no wear. Holds 15–23 in continuous range |
| Detents, latches, quick-release pins | `pom_acetal` spring detents; `insert_ti_6al_4v_bonded` + Ti pin for the interchangeable-hipbelt interface | Ti tolerates wet and cyclic loads. POM gives a clean snap |
| Sternum sliding rail | `pom_acetal` or `pa66_gf30` rail | — |
| Avoid | Hook-and-loop (noise; quiet-hunt mode bans it), `pu_memory_foam` | |

### (d) Apparel layers (solids + camo accents)
| Layer | Solid body pick | Camo accent panels (knees, seat, forearms, yokes) |
|---|---|---|
| Base | `merino_synthetic_blend_core_spun` ~170 gsm (`merino_150_jersey` / `merino_190_jersey` / `merino_250_interlock` by season) | none (base layer) |
| Active mid | `grid_fleece_poly` | — |
| Active insulation | `active_insulation_alpha_class` | — |
| Soft shell pants/jacket | `softshell_nylon_spandex_stretch_woven` | `poly_spandex_stretch_woven_printable`: Martindale ~50k, stretch, sublimation-printable |
| Quiet outer (bow) | `brushed_poly_knit_shell` | Same fabric printed (sublimation) |
| Rain shell | `laminate_3l_pu_nanofiber` (active), `laminate_3l_quiet_tricot` (quiet) | Printed-face quiet tricot at mill MOQ |
| Insulation | `down_850fp_hydrophobic` (dry cold), `synthetic_insulation_100gsm` / `_60gsm` (wet; better with meat-hauling sweat and blood) | — |

On accents: in apparel, nylon solids next to polyester printed accents dye differently (metamerism and
NIR). Specify color and NIR targets per fiber, and print before applying DWR.

## Open questions / caveats
- Carbon tube and plate properties are **estimates** until the vendor gives the layup. Coupon-test
  bonded lap joints (ASTM D1002-style) and insert pull-out with the chosen adhesive and prep before
  finalizing the FEA allowables.
- The meat-zone ratings (hydrolysis, wash, stain) are engineering-judgment estimates. Confirm TPU is
  ether-based from the mill.
- Textile, foam and hardware values are mostly estimates; get mill test reports. Webbing mil-spec
  Type/Class needs confirming when you buy.
- Rotary-printed nylon camo needs a mill partner (MOQ ~1000 m). Sublimation on polyester works in
  small batches.
