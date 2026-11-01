# Pack 5200 - whole-frame generative design: one topology-optimized 3D-printed frame

Owner: structural-fea-engineer. Owner direction (2026-11-01, DECISIONS.md): generative design applies to the WHOLE FRAME as one topology-optimized 3D-printed structure; fully plastic is acceptable. Code: `huntkit/gendesign/frame_topopt.py` (domain, loads, SIMP, verification), `frame_study.py` (sweep driver), `frame_eval.py` (materials), `frame_report.py` (this file, print files, renders). Tests: `tests/test_frame_topopt.py`. Load standard: **HA-LS-1 rev B** (no meat shelf; meat on the internal straps, load_standard.md). Interfaces: geometry.yaml v3.1 (read-only here).

## 0. Verdict (honest)

- **An all-plastic printed frame CAN meet HA-LS-1 (strength, fatigue, 8 h creep rupture) and the room-temperature stiffness limit, but NOT at a competitive weight.** Lightest passing all-plastic frame: **FDM PAHT-CF / PA12-CF (H2S), 710 g** whole frame (interpolated over the sweep; governed by fatigue); FDM PA6-CF 715 g. The v2 carbon-tube frame is **569 g**: plastic is **+141 g (+25 %)**. About 159-176 g of every printed body is fixed overhead (crown-leg sleeves, pawl housing, pivot boss, anchor pads: 151 cm3) that carbon tubes get for free.
- **Heat is the real problem.** At 40 C and moisture-conditioned, nylon is at/above its glass transition: the 8 h creep-softened torsional stiffness of the recommended printed frame is ~39 % of the tube frame (limit 80 %). The pack will feel noticeably softer on a hot afternoon, and recover when cool. Strength and creep rupture still pass (sustained stresses are low).
- **Best hybrid tested: PA6-CF body + 4 pultruded carbon rods (4 mm) along the stays: 772 g**, torsion 86 % cold / 33 % hot (matrix softened). The rods cut the static-carry sag and its creep but do not fix the hot torsion, because the frame's twist is carried by the printed lumbar web and nodes, not the stays. It is not lighter than the all-plastic body. The hybrid that WOULD be competitive is the v2 frame itself (carbon tubes where bending/torsion lives, wraps at the nodes): printing the nodes instead was +80 to +190 g in generative_design.md.
- Continuous-fiber printing (Onyx matrix + 14 mm2 CCF bundles on the same 4 principal-stress paths): 785 g, torsion 46 %, matrix strength SF/req 0.48: **fails**: Onyx (40 MPa, 2.4 GPa) is too weak/soft for the nodes and lumbar web where the fibers cannot go; the fiber helps only along the stays. Est. $697 at a service.
- **Recommendation.** Production: **keep the v2 carbon-tube frame (569 g)**. Printed frame: build the **FDM PAHT-CF generative body (pure_0.032, 718 g whole frame, SF/req 1.45, fatigue 1.03, torsion 94 %)** on the H2S as a low-cost, no-layup prototype / fit-and-feel frame and as a backup frame. Print files: `designs/pack_5200/print/frame/` (2 segments, ~17 h, ~$40 of filament). Proof-test it (load_standard.md T1-T5) plus a 40 C / 8 h hold before trusting it in the field.

## 1. Design domain, non-design regions, crown decision

| item | value | source |
|---|---|---|
| domain | x +-152, y -48 .. bag frame-side panel - 1 mm (v3.1 profile stations, 57-64 mm deep), z 0..544 mm | geometry.yaml bag.profile.stations, hard points |
| back clearance | y >= -48 (hip-pivot face y -48.1; back-pad foam + mesh in front) | ASSUMPTION |
| head clearance | no printed material above z 544 (stay tops): the crown, its 25 mm aft-swept top bar and the stepped bag panel above it are untouched (geometry.yaml head_clearance all_pass) | geometry.yaml v3.1 |
| crown-leg sleeves | bore 18 mm (leg OD 16 + 1 mm UHMWPE bushing), printed wall 2.5 mm, z 160..544 on the crown axis (slope -0.0189) | frame.yaml, geometry.yaml crown |
| spine channel (void) | x +-20, y -34..-16, z 296..544 (spine + rack travel, 15-23 in) | geometry.yaml crown_retention |
| pawl housing (solid) | x +-25, y -39..-11, z 506..536 around the channel | rack_lock_pawl_upper_bar |
| hip-pivot boss (solid, clamp) | D32 at (0, -48.1, 120), 2 x M5 to the SLM Ti mount | hipbelt_pivot |
| pads (solid, r 6 mm) | bag anchors low/mid, meat anchors z190/z330/z520, hip stabilizers, shoulder-strap lower anchors, load-wing/haul-wrap lash z80/250/420, pulley guides, cam buckle, stay feet | geometry.yaml hard_points |

**Crown decision: keep the v2 CARBON telescoping crown (legs OD 16, top bar, spine; 118 g) sliding in printed sleeves.** The crown legs are up to 274 mm free cantilevers above the stay tops (23 in setting); printed nylon (E 1.7-7.9 GPa vs ~100 GPa carbon) would need ~4x the section to match, and a printed rail would put all crown loads (hipbelt-off abuse 850 N extension at the pawl) into one sliding joint in creep-prone plastic. The pulley + rack/pawl adjuster is unchanged: continuous 15-23 in.

## 2. Loads (HA-LS-1 rev B, 9 cases x 15/19/23 in)

The v2 beam model (frame.yaml) is solved for every case and torso; every load, body-spring reaction and d'Alembert load on a fixed-frame node plus the crown link forces (top bushing, leg-end bushing at z 171/273/375, pawl) are the printed body's loads; the hip pivot is the clamp. Loads x required factor. The optimization uses the 7 distinct load shapes x 3 torsos (static carry = stumble shape x 2/3; overload ~ meat shape); verification re-checks all 27 sets.

Tube frame (v2) under rev B, member first-ply SF / required, worst torso (`outputs/genframe/tube_baseline.json`):

| case | SF/req | where |
|---|---|---|
| static_carry | 1.88 | lumbar_plate (15 in) |
| drop_2p5g | 1.26 | lumbar_plate (15 in) |
| side_hill_torsion | 1.53 | lumbar_plate (19 in) |
| single_stay_setdown | 2.76 | mid_bar (19 in) |
| meat_straps | 1.46 | crown_leg_L (23 in) |
| tall_load | 1.42 | lumbar_plate (15 in) |
| overload_haul | 2.04 | crown_leg_L (23 in) |
| tall_load_posts | 1.38 | lumbar_plate (15 in) |
| hipbelt_off_abuse | 1.05 | upper_bar (15 in) |

Tube frame stiffness (same tests as the printed bodies, hip pivot clamped): static carry 150 lb stay-top aft displacement **6.3 mm**, frame torsion **2.87 N m/deg** (+-100 N fore-aft at the stay tops).

**Stiffness limit (-20 %).** Jones & Hunter (1990, Exp Brain Res 79:150) measured a Weber fraction of 0.23 for stiffness; Tan et al. (1995) ~0.22 for compliance. A frame within 20 % of the tube frame's torsional and bending stiffness is at the threshold of what a wearer can tell apart by feel; a frame softer than that will be felt as sway ("sloppy"). This is a perceptual limit, not a strength one.

## 3. Method and verification

- SIMP p = 3, hat filter r = 1.5 voxels (min member ~2 voxels: 8 mm at 4 mm voxels, i.e. >= 4 FDM perimeters), Heaviside continuation (beta 1-2-4 coarse, 2-4-8 fine), x-mirror symmetry, weighted multi-load compliance (weights 1/c_i at iteration 1), OC update.
- Coarse-to-fine: 8 mm voxels (38 x 8 x 68, all 21 shapes), then 4 mm (76 x 16 x 136) in a 16 mm band around the coarse structure with the governing sets (>= 97 % of the weighted compliance). Each iteration is one MKL PARDISO factorization of the reduced (active-DOF) system for all load cases (pypardiso; SuperLU fallback).
- Stress constraint: p-norm (p = 8) / 99th-percentile von Mises of the verified body vs the knocked-down allowable, enforced by a volume-fraction sweep (volume minimization subject to stress, stiffness, creep and fatigue, solved by interpolation over the sweep per material). For one linear isotropic material the stress field is E-independent, so one sweep serves every material.
- **Independent verification** of every result: density up-sampled 2x (2 mm voxels), thresholded at 0.5, passive regions re-imposed, largest body kept, re-solved as a solid-only FE model for all 27 sets; stiffness tests on the same mesh. SIMP benchmark: the frame SIMP reproduces the validated `simp.run_simp` 3D-cantilever optimum (test); the voxel solver matches a Timoshenko cantilever (6 %), Saint-Venant square-bar torsion (8 %) and rod-in-parallel axial stiffness (3 %) (tests/test_frame_topopt.py).

Sweep (verified bodies; stresses for E-normalized factored loads):

| design | vol. frac. | verified volume (cm3) | governing set | 99th pct vM (MPa, factored) | torsion (N m/deg per GPa) |
|---|---|---|---|---|---|
| pure_0.015 | 0.015 | 318 | hipbelt_off_abuse|15 | 116.6 | 0.14 |
| pure_0.022 | 0.022 | 385 | hipbelt_off_abuse|15 | 53.8 | 0.47 |
| pure_0.032 | 0.032 | 473 | drop_2p5g|15 | 39.9 | 0.73 |
| pure_0.050 | 0.050 | 649 | hipbelt_off_abuse|15 | 19.9 | 1.21 |
| hybrid_0.016 | 0.016 | 411 | hipbelt_off_abuse|15 | 108.0 | 0.23 (hybrid, PA6-CF ratio) |
| hybrid_0.020 | 0.020 | 439 | hipbelt_off_abuse|15 | 61.3 | 0.56 (hybrid, PA6-CF ratio) |
| hybrid_0.030 | 0.030 | 530 | hipbelt_off_abuse|15 | 36.9 | 0.87 (hybrid, PA6-CF ratio) |

## 4. Recommendation table

Whole-frame mass = printed body at the lightest volume fraction that passes everything + 205 g kept (carbon crown 118, rack/pawl/guides 44, bushings 17, spine clamp 6, SLM Ti hip mount 20) + 12 g inserts/bolts. Tube frame: **569 g**.

| material / process | whole frame (g) | governing requirement | printed body (g) | cost body (USD) | creep 8 h 40 C | cold -20 C | buildability |
|---|---|---|---|---|---|---|---|
| FDM PAHT-CF / PA12-CF (H2S) | 710 | fatigue | 505 | 40 | E_c/E 0.42 | no published notched value | FDM, owner's H2S: PA12 base: 0.9 % water, keeps properties wet; weakest Z (47 MPa) |
| FDM PA6-CF (Bambu, owner's H2S) | 715 | fatigue | 510 | 22 | E_c/E 0.39 | notched Charpy ~8.0 kJ/m2 at -20 C (est.) | FDM, owner's H2S: absorbs 2.4 % water: conditioned strength -22 %; anneal; seal/paint for UV |
| SLS PA12-CF (service) | 738 | fatigue | 534 | 320 | E_c/E 0.49 | notched Charpy ~2.4 kJ/m2 at -20 C (est.); brittle-risk | SLS service: stiffest unreinforced powder (7.9 GPa XY), anisotropic, estimate-grade data |
| Onyx matrix only (no fiber) | 917 | fatigue | 712 | 855 | E_c/E 0.42 | no published notched value | Markforged-class: matrix only here (no fiber): weak 40 MPa / 2.4 GPa |
| MJF PA12 (HP, service) | 918 (extrap.) | torsion | 714 | 196 | E_c/E 0.33 | notched Charpy ~2.1 kJ/m2 at -20 C (est.); brittle-risk | MJF service: isotropic, no Z weakness; Tg onset ~27-50 C: soft when hot |
| MJF PA11 (HP, service) | 920 (extrap.) | torsion | 716 | 251 | E_c/E 0.33 | notched Charpy ~4.8 kJ/m2 at -20 C (est.) | MJF service: ductile (50 % elongation), best cold impact of the nylons |
| MJF PA12 glass-bead (service) | 983 | strength | 778 | 233 | E_c/E 0.39 | notched Charpy ~1.8 kJ/m2 at -20 C (est.); brittle-risk | MJF service: glass beads add stiffness but cut strength to 30 MPa |
| SLM AlSi10Mg (reference) | 1,065 | strength | 861 | 775 | E_c/E 1.00 | no published notched value | SLM service: reference only: metal, needs no creep/UV caveats; galvanic-isolate from carbon |
| HYBRID: FDM PA6-CF + 4 x 4 mm pultruded CF rods | 772 | all pass at hybrid_0.020 | 567 (rods 41) | 37 | hot torsion 33 % | notched Charpy ~8.0 kJ/m2 at -20 C (est.) | owner's H2S, 2 segments, rods + MMA |
| Continuous CF printing (Onyx + 14 mm2 CCF bundles x 4 paths) | 785 | SF/req 0.48, torsion 46 % | 580 (fiber 42) | 697 (est.) | 9.1 mm | Onyx (PA6-based) | Markforged-class service or FibreSeeker-class printer |
| v2 carbon-tube frame (reference) | 569 | rev B min SF/req 1.05 | - | ~250 (tubes + prepreg wraps) | none (CFRP) | good | wet wraps, jigs, skill |

Per-material detail (every verified body; SF = strength SF/req incl. knockdowns, fat = fatigue SF, rup = 8 h creep-rupture SF, tors / carry = stiffness vs tube):

| material | design | body g | SF | fat | rup | tors | carry | creep defl mm | orientation |
|---|---|---|---|---|---|---|---|---|---|
| FDM PA6-CF (Bambu, owner's H2S) | pure_0.015 | 384 | 0.62 | 0.75 | 1.60 | 0.21 | 0.28 | 59.5 | y (frame face on the plate) |
| FDM PA6-CF (Bambu, owner's H2S) | pure_0.022 | 463 | 1.14 | 0.82 | 1.76 | 0.69 | 5.99 | 2.7 | y (frame face on the plate) |
| FDM PA6-CF (Bambu, owner's H2S) | pure_0.032 | 566 | 1.70 | 1.21 | 2.58 | 1.08 | 1.58 | 10.4 | y (frame face on the plate) |
| FDM PA6-CF (Bambu, owner's H2S) | pure_0.050 | 772 | 2.86 | 3.12 | 6.66 | 1.78 | 2.19 | 7.5 | y (frame face on the plate) |
| FDM PAHT-CF / PA12-CF (H2S) | pure_0.015 | 349 | 0.54 | 0.65 | 1.39 | 0.18 | 0.24 | 62.6 | y (frame face on the plate) |
| FDM PAHT-CF / PA12-CF (H2S) | pure_0.022 | 421 | 0.95 | 0.69 | 1.46 | 0.60 | 5.22 | 2.9 | y (frame face on the plate) |
| FDM PAHT-CF / PA12-CF (H2S) | pure_0.032 | 514 | 1.45 | 1.03 | 2.20 | 0.94 | 1.38 | 11.0 | y (frame face on the plate) |
| FDM PAHT-CF / PA12-CF (H2S) | pure_0.050 | 700 | 2.32 | 2.53 | 5.40 | 1.55 | 1.91 | 7.9 | y (frame face on the plate) |
| MJF PA12 (HP, service) | pure_0.015 | 333 | 0.33 | 0.40 | 0.74 | 0.08 | 0.11 | 172.0 | any (isotropic powder bed) |
| MJF PA12 (HP, service) | pure_0.022 | 401 | 0.71 | 0.51 | 0.96 | 0.28 | 2.42 | 7.9 | any (isotropic powder bed) |
| MJF PA12 (HP, service) | pure_0.032 | 490 | 0.96 | 0.68 | 1.28 | 0.43 | 0.64 | 30.1 | any (isotropic powder bed) |
| MJF PA12 (HP, service) | pure_0.050 | 668 | 1.93 | 2.11 | 3.94 | 0.72 | 0.88 | 21.7 | any (isotropic powder bed) |
| MJF PA11 (HP, service) | pure_0.015 | 346 | 0.36 | 0.43 | 0.80 | 0.09 | 0.12 | 162.4 | any (isotropic powder bed) |
| MJF PA11 (HP, service) | pure_0.022 | 417 | 0.77 | 0.56 | 1.04 | 0.30 | 2.56 | 7.5 | any (isotropic powder bed) |
| MJF PA11 (HP, service) | pure_0.032 | 509 | 1.04 | 0.74 | 1.38 | 0.46 | 0.68 | 28.4 | any (isotropic powder bed) |
| MJF PA11 (HP, service) | pure_0.050 | 694 | 2.09 | 2.28 | 4.26 | 0.76 | 0.94 | 20.5 | any (isotropic powder bed) |
| MJF PA12 glass-bead (service) | pure_0.015 | 425 | 0.21 | 0.25 | 0.46 | 0.12 | 0.16 | 99.0 | any (isotropic powder bed) |
| MJF PA12 glass-bead (service) | pure_0.022 | 513 | 0.45 | 0.32 | 0.60 | 0.41 | 3.56 | 4.6 | any (isotropic powder bed) |
| MJF PA12 glass-bead (service) | pure_0.032 | 627 | 0.60 | 0.43 | 0.80 | 0.64 | 0.94 | 17.3 | any (isotropic powder bed) |
| MJF PA12 glass-bead (service) | pure_0.050 | 856 | 1.21 | 1.32 | 2.46 | 1.06 | 1.30 | 12.5 | any (isotropic powder bed) |
| SLS PA12-CF (service) | pure_0.015 | 362 | 0.52 | 0.63 | 1.34 | 0.37 | 0.49 | 26.4 | y (frame face on the plate) |
| SLS PA12-CF (service) | pure_0.022 | 436 | 0.92 | 0.66 | 1.41 | 1.24 | 10.68 | 1.2 | y (frame face on the plate) |
| SLS PA12-CF (service) | pure_0.032 | 532 | 1.40 | 0.99 | 2.11 | 1.92 | 2.82 | 4.6 | y (frame face on the plate) |
| SLS PA12-CF (service) | pure_0.050 | 726 | 2.23 | 2.43 | 5.19 | 3.17 | 3.90 | 3.3 | y (frame face on the plate) |
| Onyx matrix only (no fiber) | pure_0.015 | 394 | 0.25 | 0.30 | 0.65 | 0.11 | 0.15 | 100.8 | y (frame face on the plate) |
| Onyx matrix only (no fiber) | pure_0.022 | 475 | 0.47 | 0.34 | 0.72 | 0.38 | 3.25 | 4.6 | y (frame face on the plate) |
| Onyx matrix only (no fiber) | pure_0.032 | 580 | 0.69 | 0.49 | 1.05 | 0.58 | 0.86 | 17.6 | y (frame face on the plate) |
| Onyx matrix only (no fiber) | pure_0.050 | 791 | 1.19 | 1.30 | 2.78 | 0.96 | 1.19 | 12.7 | y (frame face on the plate) |
| SLM AlSi10Mg (reference) | pure_0.015 | 861 | 1.58 | 2.06 | 10.12 | 3.48 | 4.60 | 1.4 | any (isotropic powder bed) |
| SLM AlSi10Mg (reference) | pure_0.022 | 1041 | 3.42 | 2.68 | 13.13 | 11.53 | 99.64 | 0.1 | any (isotropic powder bed) |
| SLM AlSi10Mg (reference) | pure_0.032 | 1275 | 4.61 | 3.56 | 17.46 | 17.88 | 26.28 | 0.2 | any (isotropic powder bed) |
| SLM AlSi10Mg (reference) | pure_0.050 | 1745 | 9.25 | 10.98 | 53.89 | 29.57 | 36.38 | 0.2 | any (isotropic powder bed) |
| HYBRID PA6-CF + rods | hybrid_0.016 | 534 | 0.69 | 1.16 | 2.47 | 0.35 | 0.54 | 20.9 | y (frame face on the plate) |
| HYBRID PA6-CF + rods | hybrid_0.020 | 567 | 1.18 | 1.63 | 3.49 | 0.86 | 2.18 | 5.2 | y (frame face on the plate) |
| HYBRID PA6-CF + rods | hybrid_0.030 | 674 | 1.90 | 2.94 | 6.28 | 1.34 | 1.77 | 6.4 | y (frame face on the plate) |

**Hybrid rods (pultruded CF, cfrp_pultruded_rod_tube, hybrid_0.020):** max factored tension 146 MPa (meat_straps|23) vs Xt x 0.8 = 1600 -> SF 10.9; max compression 155 MPa (meat_straps|23) vs Xc x 0.8 x 0.65 = 624 -> SF 4.0. Embedded along their full length, so no column buckling; pull-out at the ends is carried over the whole bonded length (shear lag).

## 5. Creep, heat, cold, fatigue, UV and chemicals

- **8 h at 40 C under 150 lb:** stay-top deflection = elastic deflection / (E(40 C, wet)/E x E_creep(8 h)/E) (record fields `modulus_40c_wet_ratio`, `creep_modulus_8h_40c_ratio`); sustained stress <= creep-rupture ratio x knocked-down strength. 40 C sits AT or ABOVE the glass transition of conditioned PA6 and PA12 (NETZSCH DMA: LS-PA12 Tg onset 27 C, E' 1438 -> ~500 MPa through the transition), which is why all-plastic frames are stiffness-governed. In the hybrid the rods (no creep) carry the stay bending; only the matrix share creeps (ASSUMPTION 50 % share).
- **Hot truck, 60 C, unloaded:** every candidate's HDT at 0.45 MPa is 145-186 C, so an unloaded frame does not distort. FDM parts must be ANNEALED (80-100 C, dry) before use or locked-in print stresses relax and the frame warps at 60 C. Do not leave the frame strapped under load in a hot vehicle.
- **Cold, -20 C:** nylons stiffen (~+30 %) but lose notched toughness; PA11 keeps it best, PA12-GB/PA12 worst (< 3 kJ/m2 estimated). Required: the T4c empty-pack drop at -20 C after a 4 h cold soak on the first printed frame.
- **Fatigue 1e5 x 0 -> 1.6 g:** fatigue strength taken as 0.3 x static (ASSUMPTION, no printed-PA fatigue data for these grades); shown as `fat` above.
- **UV:** carbon-black-filled CF nylons resist UV far better than natural PA; unfilled MJF/SLS PA12/PA11 yellow and embrittle: dye black + UV-stable paint/clear coat. **Gasoline:** PA12/PA11 are rated excellent for fuels (< 2 % swell after 1000 h, PatSnap summary; generic nylon chart rates gasoline A). **Blood:** water + salts: PA6 absorbs water (2.4 %, -22 % strength): seal or prefer PA12. **DEET:** no polyamide-specific DEET data found; DEET attacks plastics such as polycarbonate and some coatings: coupon-soak test required (24 h, then flex). 

## 6. Printability (recommended printed design)

Segmented at **z = 234 mm** (lowest-stress slab between the meat-anchor and bag-anchor rows) so each segment lies flat on the 340 x 320 mm plate. Layer normal = frame y (wearer face down): the stay bending stresses run IN the layers; the Z (interlayer) strength only sees through-thickness shear and the anchor pull-outs. Layer failure index (99th pct) by layer normal:

| segment | mass g | print h | filament g | filament USD | plate footprint (mm) | FI layer normal y / x / z | supports (mm2, plate face) | files |
|---|---|---|---|---|---|---|---|---|
| lower | 211 | 7.5 | 228 | 18.25 | 256 x 234 x 64 | 0.75 / 1.01 / 1.05 | 13922 (+y) | genframe_lower_flat.stl, genframe_lower_flat.3mf |
| upper | 257 | 9.1 | 277 | 22.18 | 257 x 310 x 58 | 0.63 / 0.94 / 0.96 | 21964 (-y) | genframe_upper_flat.stl, genframe_upper_flat.3mf |

ASSUMPTIONS: effective flow 8 mm3/s (0.6 mm hardened nozzle, CF-nylon), +8 % purge/brim/support; filament $80/kg (PAHT-CF record; PA6-CF $43/kg).

**Joint (FEA check).** Doweled + bonded butt splice: per side, one 5 mm pultruded carbon dowel in the fore and one in the aft flange of the section (100 mm long, 50 mm into each segment, MMA-bonded; holes are in the STLs), plus the MMA-bonded butt face. Section resultants from the verified stress field of the 4 governing sets (factored), tension-flange force F = |N|/2 + M / dowel separation:

| set | side | N (N) | M (N m) | V (N) | lever (mm) | flange force (N) | pull-out SF | shear SF |
|---|---|---|---|---|---|---|---|---|
| drop_2p5g|19 | L | -404 | 81.7 | 312 | 22 | 3917 | 1.20 | 14.85 |
| drop_2p5g|19 | R | -404 | 81.7 | 312 | 22 | 3917 | 1.20 | 14.85 |
| side_hill_torsion|15 | L | -291 | 75.4 | 291 | 22 | 3572 | 1.32 | 15.94 |
| side_hill_torsion|15 | R | -281 | 49.2 | 155 | 22 | 2376 | 1.98 | 29.83 |
| meat_straps|23 | L | -3 | 101.1 | 182 | 22 | 4596 | 1.03 | 25.42 |
| meat_straps|23 | R | -3 | 101.1 | 182 | 22 | 4596 | 1.03 | 25.42 |
| hipbelt_off_abuse|19 | L | 600 | 32.9 | 280 | 22 | 1796 | 2.62 | 16.58 |
| hipbelt_off_abuse|19 | R | 600 | 32.9 | 280 | 22 | 1796 | 2.62 | 16.58 |

ASSUMPTIONS: MMA on flame/plasma-treated nylon 6 MPa hot/wet over the dowel surface (coupon T6 must confirm), dowel transverse shear 60 MPa; the bonded butt face is credited in shear only. Loads are factored, so SF >= 1 is the requirement.

**Local hot spot (read before printing):** inside the pawl-housing load patch the layer failure index reaches ~1.25 under the factored hipbelt-off abuse case (850 N crown extension + ~1 kN fore-aft through the pawl); the patch is a load-introduction region excluded from the 99th-percentile check (the real load enters through the Ti pawl pivot and the rack teeth). Detail it at part level: press a Ti/steel pivot bushing into the housing with 3 mm extra wall around it, and watch the housing in proof test T1(c).

**Service cost (cited basis):** MJF PA12 at JLC3DP $0.275/g (Aug 2025 price cut, still current); PA11 and PA12-CF were cut further on 24 Jul 2026 (PA12-CF -24 %), absolute rates not published: get instant quotes with the STLs. Continuous-fiber: no public per-cm3 service price; the owner option is a FibreSeeker 3 printer (US$2,449) with X-CCF at US$55 per 500 m. SLM AlSi10Mg: quote by volume (see generative_design.md).

## 7. Continuous-fiber paths

`designs/pack_5200/print/frame/fiber_paths_principal_stress.csv` (+ screenshot 7): trajectories of the major in-plane principal stress (2.0 g stumble) on the fore and aft fiber planes of the flat-printed body. In the stays they run straight along the stay (which is why straight pultruded rods capture most of the benefit), and fan from the stays into the hip-pivot boss in the lumbar web. Markforged Eiger and Anisoprint Aura lay concentric/isotropic fiber rings, not arbitrary curves: use the CSV as the target and approximate it with concentric rings around the stay and web outlines.

## 8. Assumptions

- ASSUMPTION: Loads at the printed-body interfaces come from the v2 tube-frame beam model (interface forces depend weakly on the frame stiffness).
- ASSUMPTION: Hip pivot = clamp (32 mm boss); every other body reaction is applied as a load; the same clamp is used for the tube-frame stiffness tests.
- ASSUMPTION: FDM stiffness uses 0.95 x E_XY (flat printing, bending in the layer plane); strength uses the layer failure index with the Z strength and interlayer shear = 0.6 x Z strength.
- ASSUMPTION: Environmental knockdowns: 0.75-0.8 on strength (record field env_knockdown_ratio); creep/fatigue ratios as the material records (estimates, no published creep data for printed CF nylon: coupon creep test required).
- ASSUMPTION: Stress = 99th percentile element von Mises of the 2 mm verification mesh, clamp and load-patch elements excluded; envelopes of different load sets are combined (conservative).
- ASSUMPTION: No buckling check on the voxel body (minimum member >= 8 mm, compact sections); the rods are embedded (continuous support) so they cannot buckle as columns.
- ASSUMPTION: Kept parts and masses from frame.yaml / geometry.yaml weight budget; inserts + bolts 12 g.

## Screenshots

- `outputs/screens/20261101_genframe_1.png` - recommended hybrid frame, front 3/4 / back / side
- `outputs/screens/20261101_genframe_2.png` - on the pack
- `outputs/screens/20261101_genframe_3.png` - utilization map
- `outputs/screens/20261101_genframe_4.png` - segments on the build plate
- `outputs/screens/20261101_genframe_5.png` - mass / stiffness comparison
- `outputs/screens/20261101_genframe_6.png` - optimization evolution
- `outputs/screens/20261101_genframe_7.png` - continuous-fiber paths (principal stress)
