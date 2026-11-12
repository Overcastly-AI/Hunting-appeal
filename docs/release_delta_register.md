# Release delta register (BL-015)

Owner: manufacturing-engineer, 2026-11-10. Ticket: `docs/backlog/BL-015-release-delta-register.md`.
Machine-readable copy: `docs/release_delta_register.csv` (same rows, same text, columns
`id, area, released_state, decided_state, decision_date, decision_source, files_that_must_change, blocked_by,
safety_relevant, notes`).

**What "released" means here.** The files a builder can pick up today:
- the v3.1 beginner print set `outputs/release/pack5200_v3.1_patterns/` (README, cutlist, DXF, letter PDFs);
- the frame print folder `designs/pack_5200/print/frame/`;
- the build packages the release points to or sits beside: `designs/pack_5200/cut/spreader/`,
  `designs/pack_5200/cut/attachment/`, and `designs/pack_5200/BUILD_PLAN.md` (the release README section 4 sends the
  builder there).

**What "decided" means here.** Every `docs/DECISIONS.md` row from 2026-11-05 to 2026-11-10, plus the analysis records
those rows name. Nothing was edited in any released or source file by this ticket; this is a list for a later release
ticket. Units are mm, N, g, with inches / lb / oz in brackets where a builder needs them.

**Counts.** 22 deltas from BL-015, plus RD-23 / RD-24 added by BL-030 (CORRIE F rev 3, 2026-11-12; RD-24 restated by BL-031): 24 in all, 16 safety-relevant. BL-015's own count: **15 are safety-relevant** (a part built from today's files fails HA-LS-1 rev C, an
injury limit, or a load limit the user must know). Areas: frame 5, belt 3, back 2, harness 1, bag 4, attachment 1,
meat haul 2, docs 4.

## 1. Register (one line per delta)

| id | area | delta | decided | safety | blocked by (short) |
|---|---|---|---|---|---|
| RD-01 | bag | Orange flag sleeve F-03 removed | 2026-11-06 | **no** | none |
| RD-02 | meat haul | Swing ('between') mode replaced by float on B-24 links; 53 kg (116 lb) frame meat limit | 2026-11-06 | **yes** | PT-6; T5f only for 56 kg; BL-003 |
| RD-03 | meat haul | IM1 meat strap 973 -> 990 mm (38.3 -> 39.0 in) for float | 2026-11-06 | **no** | none |
| RD-04 | frame | H1 printed body replaces genframe_*; bolted z 234 joint (4 Ti M5), frame 1025 g (2.26 lb) | 2026-11-10 | **yes** | CA-1, CA-5; RD-11 first; BL-007/017 |
| RD-05 | frame | Released flat print halves (441.5 cm3) do not match the assembled body (737.9 cm3) | 2026-11-10 | **yes** | closed by RD-04 |
| RD-06 | frame | P-1: 0.8 mm bondline in the crown extension-post socket | 2026-11-09 | **yes** | T6 coupons at 0.8 mm bondline |
| RD-07 | belt | Lumbar pad backer HDPE 1.0 -> CFRP QI 0.8 mm (+8.1 g / 0.29 oz) | 2026-11-09 | **yes** | pad-seat sag test 413 N / 8 h; BL-006 |
| RD-08 | harness | Yoke plate CFRP 1.5 -> 1.8 mm (0.059 -> 0.071 in, +8.5 g); no yoke drawing exists | 2026-11-09 | **yes** | T1(c) with a yoke dial |
| RD-09 | belt | Belt centre plate: 7075-T6 1.2 mm rolled bow-tie package (released PA66 plate fails) | 2026-11-09 | **yes** | HB-5 on the 7075 plate; slope template; BL-006 |
| RD-10 | belt | Hipbelt B replaces the released belt (cone wings, 5 sizes, 2:1, stitched ear) | 2026-11-09 | **yes** | BL-006; HB-2, HB-3, HB-5; ladder-lock qualification; RD-07/09/11 |
| RD-11 | frame | Ti pivot mount 2 x M5 -> 4 x M5 heat-set inserts | 2026-11-09 | **yes** | insert pull-out test; re-check at 1200 N |
| RD-12 | attachment | Attachment parts B-17..B-24, rated >= 2200 N (495 lbf) bag hooks, hood relief | 2026-11-05 to 2026-11-06 | **yes** | PT-1..PT-6; BL-004, BL-010, BL-011 |
| RD-13 | back | Back rails 100 -> 120 mm (3.9 -> 4.7 in) on new BP-08 80 mm backers; mesh 370 x 440 | 2026-11-06 | **yes** | BL-005; pressure-map test (BL-016) |
| RD-14 | docs | Frame mass booking: z 234 dowels (18.5 g) never booked; H1 joint 28.0 g | 2026-11-10 | **no** | BL-001; weigh the corner wraps |
| RD-15 | docs | Corrected material records (Robic 100D, ULTRAGrid, ULTRA 200X) not in the release numbers | 2026-11-09 | **no** | swatch weights; ULTRA strip test + PT-3 |
| RD-16 | bag | Bag body: CORRIE (then CORRIE F) replaces SPINE | 2026-11-07 / 2026-11-09 | **no** | BL-011 (after BL-010); corrie_body.md 12.4 gates |
| RD-17 | bag | Pockets IMP-1..6, IMP-8; SH-03 band deleted; binding drop gated | 2026-11-09 | **no** | wash-swatch fray test; O-3/O-4 evidence; BL-011 |
| RD-18 | bag | Bow riser carry added (12.1 g / 0.43 oz) | 2026-11-05 | **no** | none (owner-frozen) |
| RD-19 | back | Spreader BP-06 rev C not in the release; z 119 pad and pucks must be re-fitted to H1 | 2026-11-05 / 2026-11-06 / 2026-11-10 | **yes** | spreader.evaluate on H1; bone-end 400 N; BL-005 |
| RD-20 | frame | Crown rev C fix lives only in the DO-NOT-PRINT PRODUCTION.md | 2026-11-06 | **yes** | T6 coupons; BL-017 |
| RD-21 | docs | BUILD_PLAN.md describes retired parts (stubs, bay mode, PA66 plate) | 2026-11-06 to 2026-11-10 | **yes** | RD-04, RD-10, RD-16 released first |
| RD-22 | docs | No user guide: float limit, belly rule, procedures, posts optional | 2026-11-06 / 2026-11-07 / 2026-11-09 | **yes** | none |
| RD-23 | attachment | Top anchor: crown hood B-19 + 2 outside guys -> B-25 bridle + B-27 port guys inside the bag (CORRIE F rev 3) | 2026-11-12 | **yes** | B-27 port pattern; T9 rev 3 at the S kit; LL-H |
| RD-24 | bag | Top pouch -> B-29 5.0 L crown lid on two 25 mm B-28 crown straps cut per crown kit; strap tail rule (CORRIE F rev 3, BL-031) | 2026-11-12 | **no** | B-29 pattern (pattern-maker); T9 lid weigh/photo, gloved cinch trial, free lengths |

## 2. Rows in full

Each row: released state, decided state, decision source (file and section or DECISIONS row), files that must change, what blocks it, safety. Text is identical to the CSV.

### RD-01 (bag): Orange flag sleeve F-03 removed

- **Released state:** F-03 orange flag sleeve (robic_210d_ripstop, 1 off, 6.3 g) is in cutlist.md/.csv, dxf/robic_210d_ripstop.dxf, print_letter/step5_collar_fly.pdf and the F-03 seam row of pattern_checks.md; the only warning is the 2026-11-06 banner in the release README
- **Decided state:** F-03 deleted; fly pocket F-02 holds the fly only; extension posts are lash points only; R-11 no longer asks for a flag sleeve; -6.5 g (pack 3447.2 -> 3440.7 g at that date)
- **Decision:** 2026-11-06. Source: docs/DECISIONS.md row 2026-11-06 'Owner: orange flag sleeve removed'
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/cutlist.md; outputs/release/pack5200_v3.1_patterns/cutlist.csv; outputs/release/pack5200_v3.1_patterns/dxf/robic_210d_ripstop.dxf; outputs/release/pack5200_v3.1_patterns/print_letter/step5_collar_fly.pdf; outputs/release/pack5200_v3.1_patterns/pattern_checks.md; outputs/release/pack5200_v3.1_patterns/README.md (drop the banner after regeneration). Source already changed: designs/pack_5200/patterns_v31.py, build_geometry.py
- **Blocked by:** none (regenerate the release set from patterns_v31.py)
- **Safety-relevant:** no. Weight and clutter only. Verified here: pdftotext finds F-03 on step5_collar_fly.pdf and grep finds it in the robic 210D DXF; neither file carries a warning.

### RD-02 (meat haul): Swing ('between') mode replaced by float on B-24 links; 53 kg (116 lb) frame meat limit

- **Released state:** Release set has no float parts and no meat-haul procedure. designs/pack_5200/BUILD_PLAN.md step 6 and its test list (lines 103-108) still describe girth-hitched frame stubs, 4 LINK toggles and a 'bay mode' where the bag hinges back on its bottom pins
- **Decided state:** Swing ('between' mode, 28.5 deg on the z 60 hinge pins) retired. Float: bag off its pins, meat in the US1/US2 cradle under IM1-IM3, bag hung upright on two B-24 stand-off links (38 mm poly webbing x 435 mm, three loops with apex at 120 / 170 / 220 mm, box-X 38 x 20 per loop, one rated >= 2200 N hook each) at the IM3 eyes; procedure about 128 s; hinge pins, HE eyes and B-18 kept for bag-on; meat on the frame <= 53 kg (116 lb) with the cradle cammed to about 70 mm (2.75 in) belly
- **Decision:** 2026-11-06. Source: docs/DECISIONS.md rows 2026-11-06 'replace the swing ... concept A', 'Float mode implemented (D-33)', 'Float mode structural check'; designs/pack_5200/analysis/meat_carry_alternatives.md status note + section 8; designs/pack_5200/analysis/float_fea.md section 2; designs/pack_5200/analysis/bag_attachment.md sections 5 and 7; designs/pack_5200/analysis/meat_haul_modes.md section C
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv (webbing: B-24 2 x 38 x 435 mm; hardware: 2 more rated hooks); outputs/release/pack5200_v3.1_patterns/README.md (parts list); designs/pack_5200/BUILD_PLAN.md step 6 and the meat-mode test list; new user guide (RD-23). B-24 1:1 drawing already exists in designs/pack_5200/cut/attachment/
- **Blocked by:** PT-6 (B-24 link proof, 1410 N; bag_attachment.md section 5); T5f only if 56 kg is wanted (float_fea.md section 2); BL-003 may move float parts into a meat-trip kit (owner decision)
- **Safety-relevant:** yes. Safety: the 53 kg limit and the belly rule must reach the user before anyone hauls in float mode.

### RD-03 (meat haul): IM1 meat strap 973 -> 990 mm (38.3 -> 39.0 in) for float

- **Released state:** Webbing cut list: internal meat strap IM1 = 973 mm
- **Decided state:** IM1 = 990 mm (+17 mm, +0.5 g) so it reaches over the meat in float mode
- **Decision:** 2026-11-06. Source: docs/DECISIONS.md row 2026-11-06 'Float mode implemented (D-33)' ('IM1 strap +17 mm'); designs/pack_5200/panels.yaml webbing_cut_list (IM1 length_mm 990)
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv webbing row 'internal meat strap IM1'
- **Blocked by:** none
- **Safety-relevant:** no. Fit only; a short IM1 cannot close over a full float load.

### RD-04 (frame): H1 printed body replaces genframe_*; bolted z 234 joint (4 Ti M5), frame 1025 g (2.26 lb)

- **Released state:** designs/pack_5200/print/frame/: genframe_assembled.stl, genframe_lower_flat.stl/.3mf, genframe_upper_flat.stl/.3mf (printed body 823 g booked, z 234 joint = 8 carbon dowels 5 x 70 mm + MMA); PRODUCTION.md and README.md describe that body. Both .md files carry the 2026-11-10 DO NOT PRINT banner
- **Decided state:** H1 body (owner, 2026-11-10): 757.7 g booked, split at z 234 and dry-bolted with 4 Ti gr5 M5 x 45 low-head screws (DIN 7984), A2 nuts in traps, 12 mm OD washers, 1.0 N m, bores printed 17.4 and reamed 18.0 through both halves. Frame 1025.1 g (2.26 lb), with spreader 1187.4 g (2.62 lb). Rev C: strength 1.45, fatigue 1.28, creep 2.73, buckling 1.31, joint 1.96 / 1.22
- **Decision:** 2026-11-10. Source: docs/DECISIONS.md row 2026-11-10 'Owner: ... proceed with the competition result H1'; designs/pack_5200/analysis/frame_h1.md sections 0, 3 and 7 items 1-4, 8; designs/pack_5200/analysis/frame_comp_verdict.md
- **Files that must change:** designs/pack_5200/print/frame/genframe_assembled.stl, genframe_lower_flat.stl/.3mf, genframe_upper_flat.stl/.3mf (replace with print/frame_h1/h1_*); print/frame/PRODUCTION.md (what you print, bond and hardware step 3, anneal, spreader step 5, QC joint rows, cost table); print/frame/README.md (assembly steps 1-3); designs/pack_5200/analysis/frame_mass_production.json; designs/pack_5200/geometry.yaml (regenerate with build_geometry.py); designs/pack_5200/analysis/rev_c_verification.md body row + joint and buckling rows; huntkit/viz3d generative_frame_dir
- **Blocked by:** coupon CA-1 (PAHT-CF fatigue ratio; H1 fails below 0.234) and joint stubs CA-5 (designs/pack_5200/tests_physical/CA1_fatigue_rig.md; print/frame_h1/README.md status note); RD-11 (4 x M5 boss) should be in the H1 geometry before the first print; BL-007 / BL-017 may change the crown
- **Safety-relevant:** yes. The H1 files are a release candidate in print/frame_h1/. Found while checking: h1_lower_flat.stl is not one watertight shell (see the register's 'Found, not fixed').

### RD-05 (frame): Released flat print halves (441.5 cm3) do not match the assembled body (737.9 cm3)

- **Released state:** print/frame flat halves do not match the assembled body: genframe_lower_flat 199.3 cm3 + genframe_upper_flat 242.2 cm3 = 441.5 cm3 against genframe_assembled.stl 737.9 cm3 (re-measured here with trimesh)
- **Decided state:** Print the H1 halves: h1_lower_flat 276.9 cm3 + h1_upper_flat 444.3 cm3 = 721.2 cm3 = h1_assembled.stl 721.2 cm3 (re-measured here)
- **Decision:** 2026-11-10. Source: designs/pack_5200/analysis/frame_h1.md section 7 item 1 (note on the flat halves); designs/pack_5200/print/frame/README.md banner 2026-11-10
- **Files that must change:** designs/pack_5200/print/frame/genframe_lower_flat.stl/.3mf, genframe_upper_flat.stl/.3mf (closed by RD-04)
- **Blocked by:** none beyond RD-04
- **Safety-relevant:** yes. Printing today's flats builds an older, unverified body. Folder warnings exist; STL/3MF cannot carry text.

### RD-06 (frame): P-1: 0.8 mm bondline in the crown extension-post socket

- **Released state:** Crown extension-post socket (7075 liner inside the corner wrap) has the default 0.5 mm bondline; PRODUCTION.md 'Carbon crown' sets 0.8 mm only for the two leg/bar corner joints; frame.yaml crown_joint covers the corners only; rev_c_verification.md summary table omits the post-socket check (0.957 in C6p)
- **Decided state:** P-1: the post socket gets the same 0.8 mm glass-bead MMA bondline as the corners; C6p bond-peak margin 0.957 -> 1.20; 0 g
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md row 2026-11-09 'P-1 adopted on today's crown'; designs/pack_5200/analysis/frame_light2.md Summary, finding P-1
- **Files that must change:** designs/pack_5200/print/frame/PRODUCTION.md 'Carbon crown' (corner wrap steps and T6 note); designs/pack_5200/frame.yaml (crown_corner / crown_joint: add the socket bondline); designs/pack_5200/analysis/rev_c_verification.md summary table (add the post-socket row); designs/pack_5200/print/frame_h1/README.md section 6
- **Blocked by:** T6 crown-corner coupons made with the 0.8 mm bondline and beads (PRODUCTION.md T6 note); extension posts are an optional accessory (DECISIONS 2026-11-07)
- **Safety-relevant:** yes. Only loaded when posts are fitted (C6p tall load), but the socket is on every frame.

### RD-07 (belt): Lumbar pad backer HDPE 1.0 -> CFRP QI 0.8 mm (+8.1 g / 0.29 oz)

- **Released state:** No lumbar backer exists in the released set (the released v3.1 belt puts the lumbar pad on a flat PA66-GF30 centre plate). The belt-B pad seat as booked (designs/pack_5200/concepts/corrie.py lumbar seat, backer = 190 x 150 x 1.0 mm HDPE, 27.2 g) fails: fatigue 0.53, creep 0.63, sags about 14 mm onto the bow-tie spine and puts about 10 % of H back on the pin
- **Decided state:** Lumbar pad backer CFRP quasi-isotropic 0.8 mm, 190 x 150 mm, 35.3 g (+8.1 g): C2 1.73, fatigue 1.50, creep 4.81, sag 3.3 mm; keep the 0.5 mm HDPE slip liner on the channel face
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-09 'Weight package C structural gates' (C-4 FAIL) and 'Package C adopted where it passes ... corrections'; designs/pack_5200/analysis/weight_c_structural.md section 4
- **Files that must change:** designs/pack_5200/concepts/corrie.py (lumbar seat 'backer' parameter and mass row; the +8.1 g correction is booked but the part is still defined as HDPE 1.0); belt-B pattern/DXF set (outputs/hipbelt/hipbelt_B_pieces.dxf from designs/pack_5200/concepts/hipbelt_concepts.py) when belt B is released; BOM; designs/pack_5200/analysis/corrie_body.md section 11.2a
- **Blocked by:** pad-seat sag test, 413 N held 8 h (weight_c_structural.md sections 4 and 7); BL-006 hipbelt diet
- **Safety-relevant:** yes. DECISIONS says the fix 'also affects the released SPINE frame and back system'. In the released files there is no backer to change: the delta lands in the belt-B release (RD-10).

### RD-08 (harness): Yoke plate CFRP 1.5 -> 1.8 mm (0.059 -> 0.071 in, +8.5 g); no yoke drawing exists

- **Released state:** Yoke plate CFRP 1.5 mm (build_geometry.py harness row 'shaped yoke plate (cfrp 1.5 mm)', DESIGN.md harness rows). No drawing of the yoke plate exists in the release (patterns_v31.py HS-05 note: 'yoke redesign pending'). 1.5 mm gives 0.90 in C8 hipbelt-off at 23 in
- **Decided state:** Yoke plate CFRP QI 1.8 mm, 216 x 96 mm outline (18 200 mm2), 50.8 g (+8.5 g): strength 1.21, fatigue 2.65, pin bearing 4.6. Alternative: 60-70 mm wide spine saddle under the yoke. T1(c) with a dial on the yoke tip may relax it back to 1.5 mm if the measured push is under about 1 kN
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-09 'Weight package C structural gates' (C-7 FAIL) and 'Package C adopted ... CFRP yoke plate 1.5 -> 1.8 mm'; designs/pack_5200/analysis/weight_c_structural.md section 5
- **Files that must change:** designs/pack_5200/build_geometry.py (yoke row, then regenerate geometry.yaml / panels.yaml); designs/pack_5200/DESIGN.md harness rows; new yoke plate drawing (DXF + layup note) in the release; outputs/release/pack5200_v3.1_patterns/cutlist.md sheet-goods section; designs/pack_5200/concepts/corrie.py already books +8.5 g
- **Blocked by:** T1(c) hipbelt-off hang 225 lb with a dial on the yoke tip (weight_c_structural.md section 7)
- **Safety-relevant:** yes. Gap: the release has never contained a yoke plate drawing, so a builder has nothing to cut from.

### RD-09 (belt): Belt centre plate: 7075-T6 1.2 mm rolled bow-tie package (released PA66 plate fails)

- **Released state:** Released v3.1 belt: flat PA66-GF30 centre plate on the pivot, 45 g booked as an ASSUMPTION (DESIGN.md hipbelt rows; BUILD_PLAN.md line 87). As drawn it fails: C2 0.61, walking fatigue 0.20 (hipbelt_structural.md section 3). The interim belt-B plate (6061-T6 1.5 mm rolled bow-tie, 95 g) drops to 0.94 with a +/-2 deg end-slope tolerance
- **Decided state:** Plate package C-1 + C-2 + C-3: 7075-T6 1.2 mm water-jet bow-tie, cold slip-rolled on a 3-roll slip roll to an R 417 mm template (no brake bend at the ear root, no hot forming), PA66 hub D28 x 10, two 31 mm spine holes at x +/-42.5; min SF/req 1.08; -25.0 g vs the 6061 plate; valid only while the lumbar push H stays off the pin (pad on the frame lumbar pan)
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-09 'Weight package C structural gates' (C-1, C-2, C-3 PASS) and 'Package C adopted where it passes'; designs/pack_5200/analysis/weight_c_structural.md sections 0, 2, 3; designs/pack_5200/analysis/hipbelt_structural.md sections 0 and 3
- **Files that must change:** huntkit/gendesign/hipbelt_structure.py and designs/pack_5200/concepts/corrie.py plate parameters (owners: structural-fea-engineer / pack-designer); new plate drawing: water-jet DXF + roll template (R 417) + end-slope gauge; designs/pack_5200/DESIGN.md centre-plate rows; designs/pack_5200/BUILD_PLAN.md line 87 (PA66 centre plate); BOM
- **Blocked by:** HB-5 on a 7075 plate (proof + 1e5 cycles, with the holes); template check of the end slope; pad-seat test (RD-07); BL-006 hipbelt diet
- **Safety-relevant:** yes. Walking fatigue 1.07 with the forming residual counted adverse (best estimate 1.40).

### RD-10 (belt): Hipbelt B replaces the released belt (cone wings, 5 sizes, 2:1, stitched ear)

- **Released state:** Released belt: print_letter/step8_hipbelt_{S,M,L,XL}.pdf, cutlist rows H-01..H-10, HP-01/HP-02, SH-05, R-03; dxf/hdpe_sheet.dxf (H-05 wing stiffeners), eva_foam_30c/45c, spacer_mesh_3d, cordura_330d DXFs. Straight wings (cylinder wrap), 4 sizes S-XL (26-42 in), 0/5/10 deg cant snap, 1:1 pull, flat pad on a PA66 centre plate that fails (RD-09). No warning on any belt file
- **Decided state:** Belt B: wings cut as a developed cone per size (7/6/5/3/2 deg), 5 sizes S 27-31 / M 30-34 / L 33-37 / XL 36-40 / XXL 39-44 in, dual-density lumbar with removable stepped wedge, crest relief, soft tips, fixed 'stitched ear' wing joint (2 x 22 holes of 2 mm, hand saddle-stitched tex 135, 1000D doublers; SF/req 1.82), HDPE stiffener floats (no rivet or stitch fixing it at the root), 2:1 pull routed anchor on buckle half -> D-ring on wing tip -> heavy ladder lock -> tail, lumbar pad bears on the frame lumbar pan, hipbelt pockets re-sized per wing (IMP-5), unprinted face until HB-2 (A-1)
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-09 'Owner delegated the open choices' (Hipbelt), 'Hipbelt B structural check', 'Belt-B structure choices'; designs/pack_5200/analysis/hipbelt_fit.md section 0; designs/pack_5200/analysis/hipbelt_structural.md sections 0, 2, 5; designs/pack_5200/analysis/corrie_body.md sections 11.2 and 11.2a; designs/pack_5200/analysis/weight_pass_corrie.md section 3.1 (A-1)
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/print_letter/step8_hipbelt_S/M/L/XL.pdf (replace, add XXL); outputs/release/pack5200_v3.1_patterns/print_letter/step3_hipbelt_pocket.pdf (IMP-5 pocket outline); outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv rows H-*, HP-*, SH-05, R-03 and the hipbelt webbing/binding rows; outputs/release/pack5200_v3.1_patterns/dxf/hdpe_sheet.dxf, eva_foam_30c.dxf, eva_foam_45c.dxf, spacer_mesh_3d.dxf, cordura_330d_nylon66.dxf; designs/pack_5200/BUILD_PLAN.md step 8 and line 87; a belt-B pattern generator in the release path (today only outputs/hipbelt/hipbelt_B_pieces.dxf)
- **Blocked by:** BL-006 hipbelt diet (may change the belt); HB-2 grip face, HB-3 slip/settle, HB-5 plate; heavy ladder lock test-qualify (slip 1.72 x lock leg); RD-07, RD-09, RD-11
- **Safety-relevant:** yes. Building the released belt today needs a centre plate the release does not draw and the design that does draw it fails.

### RD-11 (frame): Ti pivot mount 2 x M5 -> 4 x M5 heat-set inserts

- **Released state:** Ti hip-pivot mount held by 2 x M5 brass heat-set inserts in the printed boss (D32). Both print/frame and the H1 body carry today's pivot boss (frame_h1.md section 4: 'hip pivot ... as in today's printed body'); print/frame_h1/README.md section 6 says only 'press the M5 heat-set inserts'. 2 x M5 checks 1.14 (H on the frame) / 0.995 (H on the pin) at an ASSUMED 1500 N insert
- **Decided state:** 4 x M5 heat-set inserts (D40 boss suggested), with a pull-out test and a material record
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md row 2026-11-09 'Belt-B structure choices ... Ti mount goes to 4 x M5'; designs/pack_5200/analysis/hipbelt_structural.md sections 0 and 4
- **Files that must change:** huntkit/gendesign/frame_h1.py (pivot boss and 4 insert holes) -> designs/pack_5200/print/frame_h1/h1_*.stl/.3mf; print/frame_h1/README.md section 6; print/frame/PRODUCTION.md 'Bond and hardware' step 4; SLM Ti pivot-mount drawing (4-hole pattern); re-run of the insert check in huntkit/gendesign/hipbelt_structure.py
- **Blocked by:** insert pull-out test in a PAHT-CF boss; record data/materials/hardware/insert_heatset_brass_m5.yaml exists since 2026-11-09 but is an estimate (design value 1200 N)
- **Safety-relevant:** yes. The record's 1200 N is below the 1500 N the check assumed. Scaling the 2 x M5 margins by 1200/1500 gives about 0.91 / 0.80 (my linear estimate, not a re-run). Treat 2 x M5 as failing until re-checked.

### RD-12 (attachment): Attachment parts B-17..B-24, rated >= 2200 N (495 lbf) bag hooks, hood relief

- **Released state:** Release cut list has fairlead captive eyes (8 x 38 x 120), bag-hook straps IM2/IM3 '(hook + TPU sleeve)' 4 x 38 x 160 with no hook rating, hinge eyes 2 x 38 x 150, under-straps, lifter keepers. No B-17..B-24 pieces, no placement marks for B-23 / B-20 / B-22 on B-01, B-01b, B-01u, B-02d, no hood webbing (HT, TG, LLT, GT), no POM toggles, ladder locks or tri-glides for the guys. Hooks were on the 1500 N assumption (IM3 SF 1.06)
- **Decided state:** Sewn attachment as in designs/pack_5200/cut/attachment/README.md: B-17 IM3 hook tab (2 x 90 x 110 Hypalon), B-18 hinge-eye doubler (2 x 90 x 45), B-19 crown hood (rev 2026-11-06: lip, J-curl, hem only over x +/-66; B-19s HDPE 124 mm; B-19L XLPE 128 mm), B-20 ladder strips x2 (17 slots), B-22 guy corner tabs x2 at x +/-149 z 752, B-23 IM2 tongue backings x2, B-24 float links x2 (RD-02); tongues T2/T3, HT, TG, LLT, GT; all four bag hooks one rated part >= 2200 N (PT-1 at 2120 N); box-X 7 SPI tex 135, perimeters double row 8 SPI tex 90; every part SF >= 1.55. No part B-21 is assigned
- **Decision:** 2026-11-05 to 2026-11-06. Source: docs/DECISIONS.md rows 2026-11-05 'Specified: IM3 hook tab B-17 ...', 'Bag-to-frame attachment system', 'IM3 hook fixed', 'Sewn side specified'; 2026-11-06 'Owner: adopt HA-LS-1 rev C ... attachment system accepted', 'Crown hood relieved at the crown corner wraps'; designs/pack_5200/analysis/bag_attachment.md sections 2.5, 3, 5, 10, 11
- **Files that must change:** designs/pack_5200/patterns_v31.py placement marks per bag_attachment.md section 10 -> outputs/release/pack5200_v3.1_patterns/print_letter/step9_main_bag.pdf, dxf/challenge_ultra_200.dxf, dxf/cordura_330d_nylon66.dxf; outputs/release/pack5200_v3.1_patterns/dxf/hypalon_coated_nylon.dxf (+ B-17..B-23 pieces) and dxf/hdpe_sheet.dxf, dxf/xlpe_foam.dxf (B-19s, B-19L); outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv webbing and hardware rows (rated hooks, toggles, ladder locks, tri-glides); outputs/release/pack5200_v3.1_patterns/README.md; move designs/pack_5200/cut/attachment/attachment_parts.pdf/.dxf into the release
- **Blocked by:** proof tests PT-1..PT-6 (bag_attachment.md section 5); hook purchase spec >= 2200 N (14 g ASSUMPTION); BL-004 attachment diet and BL-010 load-path verification may change parts; BL-011 CORRIE F moves where the marks land (CORRIE puts B-22 at z 695)
- **Safety-relevant:** yes. A bag built from today's step9 PDF has no place for the rated attachment and runs the IM3 hook at SF 1.06.

### RD-13 (back): Back rails 100 -> 120 mm (3.9 -> 4.7 in) on new BP-08 80 mm backers; mesh 370 x 440

- **Released state:** Back panel in the release (print_letter/step7_back_panel_harness.pdf, cutlist, dxf/xlpe_foam.dxf, spacer_mesh_3d.dxf, robic_210d_ripstop.dxf): BP-02 stay-rail foam about 100 x 420 x 10 mm (cut area 0.0412 m2 each), BP-05 sleeves, BP-01 mesh 350 x 440, no BP-08 backer strips. print/frame/PRODUCTION.md step 6 also says '100 x 420 x 10 mm'. Without backers the rails give about 49 kPa skin pressure
- **Decided state:** BP-02 120 x 420 x 10 mm L200-class XLPE centred on the stays; new BP-08 2 x 80 x 420 x 1 mm 2x2 twill carbon backer strips; BP-05 sleeves 140 x 420; BP-01 mesh 370 x 440 with sleeve lines at stay CL +/-70; air gutter 110 mm; skin 13.8 kPa at meat CG 190 mm (limit 14 kPa); +37.6 g design change, back panel 251 g with the booking fix
- **Decision:** 2026-11-06. Source: docs/DECISIONS.md rows 2026-11-06 'Back rails for the rev C meat case' and 'Back-panel booking corrected'; designs/pack_5200/analysis/back_rail.md Decision and Pattern-maker hand-off
- **Files that must change:** designs/pack_5200/patterns_v31.py back-panel pieces -> outputs/release/pack5200_v3.1_patterns/print_letter/step7_back_panel_harness.pdf, dxf/xlpe_foam.dxf, dxf/spacer_mesh_3d.dxf, dxf/robic_210d_ripstop.dxf (BP-05), new carbon-sheet DXF for BP-08; outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv; designs/pack_5200/print/frame/PRODUCTION.md step 6 (and the H1 README)
- **Blocked by:** BL-005 back system integration (may replace the rails/backers); skin pressure is model-only until a physical pressure-map test (BL-016)
- **Safety-relevant:** yes. Skin pressure limit is an injury/comfort limit (14 kPa, Golriz 2017 per DECISIONS 2026-11-01).

### RD-14 (docs): Frame mass booking: z 234 dowels (18.5 g) never booked; H1 joint 28.0 g

- **Released state:** Frame mass basis: designs/pack_5200/analysis/frame_mass_production.json frame_g 1062.6 g omits the z 234 dowels and MMA (18.5 g); an interim key frame_g_with_dowels 1081.1 g was added beside it. PRODUCTION.md says 'frame 1063 g'. The fixed-part basis 239.4 g may also omit the crown corner wraps (about 26 g, 'probably missing')
- **Decided state:** With H1 the dowels are gone: printed_body_g 757.7 (H1 raster), new z234_joint_g 28.0 g (4 Ti M5 x 45, nuts, 8 washers), frame_g 1025.1 g; drop frame_g_with_dowels; geometry.yaml regenerated (CORRIE B.2 belt M expected 3926.9 g, 8.66 lb)
- **Decision:** 2026-11-10. Source: designs/pack_5200/analysis/frame_comp_verdict.md section 2 (dowel finding); designs/pack_5200/analysis/frame_h1.md sections 5 and 7 item 4; designs/pack_5200/analysis/frame_comp_B.md section 4
- **Files that must change:** designs/pack_5200/analysis/frame_mass_production.json; designs/pack_5200/geometry.yaml (regenerate with build_geometry.py, never hand-edit); designs/pack_5200/print/frame/PRODUCTION.md 'What you are printing'; designs/pack_5200/DESIGN.md section 6 frame rows
- **Blocked by:** BL-001 mass ledger (all masses from huntkit/mass/ledger.py); weigh the crown corner wraps on the first article to settle the 26 g question
- **Safety-relevant:** no. No DECISIONS row covers the dowel booking itself; it is carried by the H1 adoption row (2026-11-10).

### RD-15 (docs): Corrected material records (Robic 100D, ULTRAGrid, ULTRA 200X) not in the release numbers

- **Released state:** Release cutlist masses and yardage were computed from the 2026-11-04 records: robic_100d_ripstop 90 gsm, ultragrid_210d_uhmwpe_ripstop 155 gsm on a 56 in (1422 / 1397 mm) roll, challenge_ultra_200 125 gsm at $50/yd (ULTRA 200 is now discontinued). panels.yaml / geometry.yaml were regenerated 2026-11-09 (SPINE 3496 -> 3524 g); the release was not
- **Decided state:** Records corrected to published values: robic_100d 125 gsm (UTS coat); ultragrid 132 gsm, Taber 1100, roll 1500 / 1475 mm; ULTRA 200X 133 gsm (listings 119-155 gsm), tear 459 / 593 N, Taber 4400, $60/yd, tensile 3000 N/50 mm is an ASSUMPTION. Buy ULTRA 200X
- **Decision:** 2026-11-09. Source: designs/pack_5200/analysis/fabric_swap_evidence.md section 'Record changes that move other numbers'; data/materials/textiles/robic_100d_ripstop.yaml, ultragrid_210d_uhmwpe_ripstop.yaml, data/materials/laminates_membranes/challenge_ultra_200.yaml (sources fields); commit ec83099 message
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv (mass column for every robic 100D / ULTRA / ultragrid piece, ultragrid roll width and yardage, net area note); outputs/release/pack5200_v3.1_patterns/README.md section 5 yardage (8.1 yd per pack); cutting instructions name ULTRA 200X; dxf/challenge_ultra_200.dxf label
- **Blocked by:** weigh swatches of ULTRA 200X and robic 100D (listings disagree); 50 mm strip test + PT-3 for the ULTRA tensile ASSUMPTION
- **Safety-relevant:** no. No DECISIONS row records the record corrections; the orchestrator may want one. The ultragrid roll change moves the side-pocket marker yardage.

### RD-16 (bag): Bag body: CORRIE (then CORRIE F) replaces SPINE

- **Released state:** Released main bag is SPINE v3.1 (print_letter/step9_main_bag.pdf, B-01..B-16, D-01, SH-01..04, diagonal #10 zip)
- **Decided state:** Owner picked concept 13 MANTLE + U (horseshoe) door + roll-top + top pouch = CORRIE; door hinged at the top, 4 L top pouch, wing straps separate from W1-W3; B.2 applies weight packages A + B (owner 'Yes' 2026-11-09). CORRIE F (BL-011) is the next merged body. DECISIONS 2026-11-07: 'the released SPINE stays the baseline until the new body is engineered and released'
- **Decision:** 2026-11-07 / 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-07 'Owner picks the bag body: concept 13 MANTLE ...', 'CORRIE engineered'; 2026-11-09 'Owner delegated the open choices' (CORRIE), 'Owner: Yes to the weight-pass recommendation'; designs/pack_5200/analysis/corrie_body.md sections 1, 12.1, 12.4
- **Files that must change:** whole main-bag part of the release: outputs/release/pack5200_v3.1_patterns/print_letter/step6, step9 PDFs, all bag DXFs, cutlist.md/.csv, pattern_checks.md, README.md; a CORRIE pattern generator (patterns_v31.py covers SPINE only); designs/pack_5200/BUILD_PLAN.md step 9
- **Blocked by:** BL-011 CORRIE F (depends on BL-001, 002, 003, 004, 009, 010); CORRIE gates in corrie_body.md section 12.4; build-simplification S-items still held for the CORRIE pattern release (DECISIONS 2026-11-09)
- **Safety-relevant:** no. Not unsafe by itself: SPINE is a valid baseline. Its attachment load path is RD-12.

### RD-17 (bag): Pockets IMP-1..6, IMP-8; SH-03 band deleted; binding drop gated

- **Released state:** Released pockets: floating side pockets P-01..P-03, hipbelt pockets HP-01/02, fly pocket F-02; accents SH-01..SH-05 incl. SH-03 roll-top camo band; grosgrain binding on main-bag inside seams (3.96 m)
- **Decided state:** Pockets IMP-1 scope sleeve (left wing), IMP-2 hydration sleeve + 2 hose ports, IMP-3 1 L bottle holster on the belt, IMP-4 zipped kill-kit pocket inside the door, IMP-5 belt pockets per wing outline, IMP-6 shoulder-strap phone pocket, IMP-8 bow cam cup (IMP-7 not adopted); B-2: delete SH-03; B-1: drop body-seam binding only after a wash-swatch fray test; fabric swaps B-8 / B-9 (O-4 / O-3) and O-5, O-6, O-15 on hold
- **Decision:** 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-09 'Owner delegated the open choices' (Pockets) and 'Owner: Yes to the weight-pass recommendation' items (2); 2026-11-05 owner row (swaps on hold); designs/pack_5200/analysis/corrie_body.md sections 11.1 and 12.1; designs/pack_5200/analysis/weight_pass_corrie.md sections 3.1 and 3.2
- **Files that must change:** same as RD-16 (CORRIE pattern release); outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv binding rows; outputs/release/pack5200_v3.1_patterns/print_letter/step3_hipbelt_pocket.pdf (IMP-5)
- **Blocked by:** B-1 wash-swatch fray test (R-12, 3 cycles); O-4 swatch seen by the owner; O-3 record; BL-011
- **Safety-relevant:** no. Part of the CORRIE release.

### RD-18 (bag): Bow riser carry added (12.1 g / 0.43 oz)

- **Released state:** No bow riser carry in the release (owner feature freeze)
- **Decided state:** Bow riser carry: 2 x 25 mm webbing loops (0.10 m each) through B-11 + a 25 mm G-hook strap (0.25 m, 4 g hook), 12.1 g
- **Decision:** 2026-11-05. Source: docs/DECISIONS.md rows 2026-11-05 'Owner: weight target ... feature freeze accepted: bow riser carry' and 'Specified: IM3 hook tab B-17 ... Bow riser carry added (2 loops + G-hook strap, 12.1 g)'; designs/pack_5200/build_geometry.py BOW_RISER
- **Files that must change:** outputs/release/pack5200_v3.1_patterns/cutlist.md/.csv webbing and hardware rows; placement marks on the bag pattern (step9 / CORRIE)
- **Blocked by:** none (owner-frozen feature)
- **Safety-relevant:** no. Owner-frozen feature (RULES.md rule 9).

### RD-19 (back): Spreader BP-06 rev C not in the release; z 119 pad and pucks must be re-fitted to H1

- **Released state:** Spreader is not in the release set (RESUME.md 'Next' item 8). Its build package designs/pack_5200/cut/spreader/ (BP-06 rev C, 7 mm core, 162.3 g) is fitted to the old print/frame body: stand-off pads under the bottom tab at z 119 are 16 x 10 x 4.9 mm (README) and puck heights 3.0 / 1.5 / 1.2 / 2.2 / 6.7 mm come from that body. The rejected d6L files spreader_v3_drawing.pdf and spreader_v3_hdpe_cut.dxf sit in the same folder
- **Decided state:** Production spreader Sandwich v2 BP-06 rev C (200 g twill / 7 mm ROHACELL 110 IG-F / 200 g twill, 7.44 mm), on H1: the H1 stay is 4.0 mm fuller on the bag side at z 119, so the stand-off pad becomes 0.5 mm (frame_h1.md, from a 4.5 mm base) and spreader.evaluate must be re-run on the H1 body (0.75 x torsional stiffness); clip sections z 166 / 260 / 400 unchanged
- **Decision:** 2026-11-05 / 2026-11-06 / 2026-11-10. Source: docs/DECISIONS.md rows 2026-11-05 'Production spreader: Sandwich v2', 2026-11-06 'Owner: adopt HA-LS-1 rev C ... spreader core 6 -> 7 mm', 2026-11-10 H1 adoption; designs/pack_5200/analysis/frame_h1.md sections 4 and 7 item 7
- **Files that must change:** designs/pack_5200/cut/spreader/README.md (pad height, H1 frame reference), spreader_v2_drawing.pdf (pads, pucks); huntkit/gendesign/spreader.py PAD_Z / puck_table on the H1 body; outputs/release/pack5200_v3.1_patterns/README.md and cutlist (add BP-06 and its clips, pucks, pads, tubes)
- **Blocked by:** spreader.evaluate re-run on H1; bone-end proof 400 N with a 22 mm dowel (PRODUCTION.md QC); BL-005 back system integration
- **Safety-relevant:** yes. The pad base thickness disagrees between files: 4.9 mm (cut/spreader/README.md) vs 4.5 mm (frame_h1.md sections 4 and 7). If 4.9 is right the H1 pad is 0.9 mm, not 0.5 mm.

### RD-20 (frame): Crown rev C fix lives only in the DO-NOT-PRINT PRODUCTION.md

- **Released state:** Crown rev C fix (inner UD plies: legs UD x 8 wall 1.44 mm, top bar and spine UD x 5 wall 1.065 mm; 0.8 mm glass-bead corner bondline; +22.0 g) is written only in print/frame/PRODUCTION.md 'Carbon crown', which now sits under the DO NOT PRINT banner; print/frame_h1/README.md section 6 sends the builder back to that file
- **Decided state:** Same crown fix carried into the H1 release documents (ODs unchanged: 16.0 / 18.0 / 20.0 mm)
- **Decision:** 2026-11-06. Source: docs/DECISIONS.md row 2026-11-06 'Owner: adopt HA-LS-1 rev C ... crown inner UD plies plus a 0.8 mm corner bondline (+22.0 g)'; designs/pack_5200/analysis/frame_cg_recheck.md section 4
- **Files that must change:** designs/pack_5200/print/frame_h1/README.md section 6 (inline the crown spec or point at a released crown sheet); the rewritten print/frame/PRODUCTION.md (RD-04)
- **Blocked by:** T6 crown-corner coupons with the 0.8 mm bondline; BL-017 crown block diet may change the crown
- **Safety-relevant:** yes. Risk is a builder following the banner and skipping the only crown spec.

### RD-21 (docs): BUILD_PLAN.md describes retired parts (stubs, bay mode, PA66 plate)

- **Released state:** designs/pack_5200/BUILD_PLAN.md (last changed 2026-11-01, referenced by the release README section 4) still describes the v2 tube frame, 6 girth-hitched webbing stubs, 4 LINK toggles, a bay mode where the bag hinges back, and a PA66-GF30 hipbelt centre plate (line 87). No warning
- **Decided state:** Fairlead attachment (2026-11-01), float meat mode (2026-11-06), belt B with the 7075 plate (2026-11-09), H1 frame (2026-11-10)
- **Decision:** 2026-11-06 to 2026-11-10. Source: docs/DECISIONS.md rows 2026-11-06 float, 2026-11-09 belt B and package C, 2026-11-10 H1 (as cited in RD-02, RD-09, RD-10, RD-04)
- **Files that must change:** designs/pack_5200/BUILD_PLAN.md (steps 6, 8, 9, the test list at lines 103-108, the buy-out table line 87); outputs/release/pack5200_v3.1_patterns/README.md section 4
- **Blocked by:** RD-04, RD-10, RD-16 (rewrite once those are released)
- **Safety-relevant:** yes. Safety: it tells a builder to make the failing PA66 plate and a retired meat mode.

### RD-22 (docs): No user guide: float limit, belly rule, procedures, posts optional

- **Released state:** No user guide in the release
- **Decided state:** User guide with: float meat limit 53 kg (116 lb) on the frame, cradle cammed to about 70 mm belly, smallest B-24 loop that fits the meat; bag on 59 s / bag off 52 s / float 128 s / bag-off haul 108 s procedures; field repair kit; extension posts are an optional accessory (antlers / tall loads); day-hunt compression procedure; do not leave the frame loaded in a hot vehicle (PAHT above Tg at 60 C)
- **Decision:** 2026-11-06 / 2026-11-07 / 2026-11-09. Source: docs/DECISIONS.md rows 2026-11-06 'Float mode structural check' ('add the limit and the belly rule to the user guide'), 2026-11-07 'extension posts stay as an optional add-on', 2026-11-09 'Owner delegated' (day-hunt compression: user-guide procedure); designs/pack_5200/analysis/bag_attachment.md section 7; designs/pack_5200/analysis/float_fea.md section 2; print/frame/PRODUCTION.md 'Do not'
- **Files that must change:** new outputs/release/<next release>/USER_GUIDE.md (or equivalent)
- **Blocked by:** none (content exists in the records)
- **Safety-relevant:** yes. Load limits the user must know.

### RD-23 (attachment): Top anchor: crown hood B-19 + 2 outside guys -> B-25 bridle + B-27 port guys inside the bag (CORRIE F rev 3)

- **Released state:** The released attachment package designs/pack_5200/cut/attachment/ (README) anchors the bag top with the B-19 crown hood (lip over x +/-66 of the top bar) and two outside guys from the hood ears to B-22 corner tabs at x +/-149, z 752; the release patterns have no B-25, B-27 or inside guy
- **Decided state:** CORRIE F rev 3: no crown hood; B-25 guy bridle (25 mm webbing sleeved round the top bar at x +/-52, joined round the spine below its clamp, a folded tab each side for the guy's toggle and a second fold for the B-28 crown strap's toggle); each guy runs from its bridle tab through a B-27 lapped port in the frame face B-01 (x +/-52, z 595-745, 50 mm facing, edges turned 6 mm, bartacked) and INSIDE the bag to B-22 turned to the inside; outside the bag the guy is only the stub from the sleeve to the port. 15 in meat CG 181.3 mm (rev C limit 190), R-28 34 deg at 15/19/23 in, lifter gap >= 57 mm; port guy up to 96 N at 1 g (288 N factored, inside the 312 N the bar was checked with, BL-021)
- **Decision:** 2026-11-12. Source: docs/DECISIONS.md rows 2026-11-12 'BL-028 guy routing', 'BL-029 result', 'Owner adopts CORRIE F rev 3'; designs/pack_5200/analysis/corrie_f_body.md sections 13.5, 14.5, 14.7, 15
- **Files that must change:** designs/pack_5200/cut/attachment/README.md (drop B-19 and the outside guys; add B-25, B-27, B-22 inside); the CORRIE F pattern release (B-01 with the B-27 slits and facings; B-22 turned in); designs/pack_5200/BUILD_PLAN.md top-anchor step; user guide (RD-22): the port guys are fitted for every carry
- **Blocked by:** CORRIE F pattern release (pattern-maker); T9 rev 3 at the S kit; LL-H heavy guy lock slip; attorney review of the strap paths before tooling (DECISIONS 2026-11-01)
- **Safety-relevant:** yes. Safety: built from the released hood-and-outside-guy files, CORRIE F's 15 in meat CG is over rev C (194.9 mm BL-028, 198.1 mm with the eyelets in cable order, corrie_f_body.md 13.11).

### RD-24 (bag): Top pouch -> B-29 5.0 L crown lid on two 25 mm B-28 crown straps cut per crown kit; strap tail rule (CORRIE F rev 3, BL-031)

- **Released state:** The v3.1 release has a box lid L-01 / L-02 / L-03 (cutlist.csv); CORRIE F up to rev 2 carried the 2.7 L top pouch (team B lid pod, 4 short G-hook straps), never released
- **Decided state:** B-29 crown lid: 350 x 210 mm superellipse plan, 30 mm wall + 55 mm dome, 5.0 L (304 cu in) counted outside the 85 L bag, ULTRAGrid crown and wall, 70D base, two 630D camo corner caps over the D2 blades, #5 coil zip 470 mm on the aft wall, two strap channels on the crown at x +/-52; 45.9 g (1.62 oz). B-28 crown straps (pair), BL-031 (owner 2026-11-12: 25 mm, sized per kit): 25 mm polyester cut per crown kit S 1028 / M 967 / L 908 mm (40.5 / 38.1 / 35.7 in), a heavy 25 mm ladder lock at each end (front on a 60 mm tab in the hinge band at z 700, rear on a 60 mm tab through the POM toggle in the second fold of each B-25 tab), a 25 mm elastic tail keeper at each lock; 77.7 g (2.74 oz) at kit M. Both as hunted. Strap tail rule (BL-031): free tail <= 100 mm at the 6-day / mid setting or a keeper; lifters 450 -> 340 mm, sternum 400 -> 170 mm a side, hip stabilizers 400 -> 260-330 mm by belt size, belt 2:1 tail 150 -> 50 mm + 2 keepers, W1-W3 cut for carry (750 / 822 / 987 mm at kit M) + three 740 mm haul extenders in the meat-trip kit, roll-clip straps 350 -> 510 mm + 2 keepers, IM1-IM3 keepers. Bag side belt M D2: base 1089.0 g, as hunted 1367.2 g, meat trip 1563.3 g
- **Decision:** 2026-11-12. Source: docs/DECISIONS.md rows 2026-11-12 'Owner adopts CORRIE F rev 3' and 'Owner: crown straps stay 25 mm'; designs/pack_5200/analysis/corrie_f_body.md sections 14.2, 15.1-15.4, 16; docs/research/top_anchor_and_lids.md
- **Files that must change:** the CORRIE F pattern release (B-29 pieces: crown, base, front wall, aft wall upper / lower, 2 caps, 2 channels; B-28 cut list per crown kit; hinge-band and B-25 lock tabs); cutlist and BOM (25 mm webbing per kit, 4 heavy 25 mm ladder locks, 2 POM toggles, 25 mm elastic keepers, #5 coil zip 530 mm with slider; harness, belt, W1-W3, roll-clip cut lengths and the 3 haul extenders); designs/pack_5200/BUILD_PLAN.md; user guide (lid off: the straps come off with it; roll tails into their keepers; extenders for the meat haul)
- **Blocked by:** B-29 pattern and the build-hours confirmation (pattern-maker; 8.9 h on the seam list, corrie_f_body.md 15.4); T9 lid weigh and photo; T9 gloved cinch trial (50 mm grip) and free lengths (crown straps per kit, W1-W3, roll clips); R-06 fit trial (sternum); owner choices: crown strap keeper vs extender, W haul extenders (corrie_f_body.md 16.6). The 20 mm B-28 slip gate is dropped (25 mm heavy lock: LL-H)
- **Safety-relevant:** no. The lid is a pocket, not a load path: the port guys (RD-23) hold the bag top. No hook-and-loop; coil zip; camo only on the caps.

## 3. Released files that are unsafe to build from today, and their warnings

"Unsafe" = building from the file gives a part that fails HA-LS-1 rev C, breaks an injury limit, or leaves out a load
limit. "Superseded" = wrong or heavy, not dangerous. Warnings were checked in the file itself (text, PDF text via
`pdftotext`, DXF text via `grep`) and in the folder README. No file was edited.

| file | status | why (register row) | warning in the file? | warning in its folder README? |
|---|---|---|---|---|
| `designs/pack_5200/print/frame/genframe_lower_flat.stl/.3mf`, `genframe_upper_flat.stl/.3mf` | **unsafe** | older body than the one checked; 441.5 vs 737.9 cm³ (RD-05) | no (STL/3MF carry no text) | **yes**: README.md and PRODUCTION.md, DO NOT PRINT banner 2026-11-10 |
| `designs/pack_5200/print/frame/genframe_assembled.stl` | **unsafe** (superseded by H1, dowel joint never re-solved, 2 x M5 pivot) | RD-04, RD-11 | no (STL) | **yes** (same banner) |
| `designs/pack_5200/print/frame/PRODUCTION.md`, `README.md` | **unsafe** as build instructions (dowel joint, 100 mm rails, 2 x M5, no P-1) | RD-04, RD-06, RD-11, RD-13 | **yes** (banner) | n/a |
| `outputs/release/pack5200_v3.1_patterns/print_letter/step8_hipbelt_S.pdf`, `_M`, `_L`, `_XL` | **unsafe** | the belt they build rides on a flat PA66 centre plate that fails C2 0.61, fatigue 0.20; straight wings, 1:1 pull (RD-09, RD-10) | **no** | **no** (release README has only the F-03 note) |
| `outputs/release/pack5200_v3.1_patterns/dxf/hdpe_sheet.dxf` (H-05 belt stiffeners), `eva_foam_30c.dxf`, `eva_foam_45c.dxf` (belt + strap foams) | **unsafe** for the belt pieces | RD-10 | **no** | **no** |
| `outputs/release/pack5200_v3.1_patterns/print_letter/step7_back_panel_harness.pdf` | **unsafe** | 100 mm rails, no BP-08 backers: about 49 kPa skin pressure vs the 14 kPa limit (RD-13); no yoke plate drawing (RD-08) | **no** | **no** |
| `outputs/release/pack5200_v3.1_patterns/dxf/xlpe_foam.dxf` (BP-02 rails), `spacer_mesh_3d.dxf` (BP-01 350 wide) | **unsafe** for the back-panel pieces | RD-13 | **no** | **no** |
| `outputs/release/pack5200_v3.1_patterns/print_letter/step9_main_bag.pdf`, `dxf/challenge_ultra_200.dxf`, `dxf/cordura_330d_nylon66.dxf` | **unsafe as an attachment load path** (the SPINE body itself is a valid baseline) | no B-17 / B-20 / B-22 / B-23 marks, so the rated attachment cannot be sewn; IM3 hook at SF 1.06 on the old 1500 N assumption (RD-12) | **no** | **no** |
| `outputs/release/pack5200_v3.1_patterns/cutlist.md`, `cutlist.csv` | **unsafe** (unrated bag hooks, no B-24 / float limit, belt and back-panel rows above) and superseded (F-03, IM1 973 mm, old record masses) | RD-01, RD-03, RD-10, RD-12, RD-13, RD-15 | **no** (the F-03 row itself carries no mark) | partly: README warns about F-03 only |
| `outputs/release/pack5200_v3.1_patterns/README.md` | **unsafe** by omission (sends the builder to BUILD_PLAN.md; F-03 is the only warning) | RD-21 | F-03 only | n/a |
| `designs/pack_5200/BUILD_PLAN.md` | **unsafe** (PA66 centre plate, girth-hitched stubs, bay mode hinge-back) | RD-21 | **no** | n/a (release README points to it) |
| `designs/pack_5200/cut/spreader/spreader_v2_*` + `README.md` | **unsafe on H1 without a re-fit** (z 119 pads 4.9 mm and puck heights are for the old body); fine on the old body | RD-19 | **no** H1 note | **no** H1 note (README still names `print/frame/` as the frame under it) |
| `designs/pack_5200/cut/spreader/spreader_v3_drawing.pdf`, `spreader_v3_hdpe_cut.dxf` | rejected alternative (d6L, barrier rule) | DECISIONS 2026-11-05 Sandwich v2 row | **no**: the DXF label reads "BP-06 rev C SPREADER HDPE 1.5 mm", the PDF has no "do not cut" text | **yes**: `cut/spreader/README.md` "not production ... do not cut" |
| `outputs/release/pack5200_v3.1_patterns/print_letter/step5_collar_fly.pdf`, `dxf/robic_210d_ripstop.dxf` | superseded (contain F-03) | RD-01 | **no** | **yes** (release README F-03 banner) |
| `outputs/release/pack5200_v3.1_patterns/print_letter/00_PRINT_FIRST_test_square.pdf`, `step3_hipbelt_pocket.pdf`, `step4_shard_practice.pdf`, `step6_meat_ports_swells.pdf` | safe to practise from (step3 pocket outline changes with belt B, RD-10) | | n/a | n/a |
| `designs/pack_5200/cut/attachment/*` | current (matches decisions); not yet in the release; PT-1..PT-6 open | RD-12 | n/a | n/a |
| `designs/pack_5200/print/frame_h1/*` | release candidate; carries its own status note (print after CA-1 and CA-5) | RD-04 | n/a | **yes** (status note) |

**Unsafe files with no visible warning (report only; not edited):**
1. `outputs/release/pack5200_v3.1_patterns/print_letter/step8_hipbelt_S.pdf`, `step8_hipbelt_M.pdf`, `step8_hipbelt_L.pdf`, `step8_hipbelt_XL.pdf`
2. `outputs/release/pack5200_v3.1_patterns/dxf/hdpe_sheet.dxf`, `dxf/eva_foam_30c.dxf`, `dxf/eva_foam_45c.dxf` (belt pieces)
3. `outputs/release/pack5200_v3.1_patterns/print_letter/step7_back_panel_harness.pdf`
4. `outputs/release/pack5200_v3.1_patterns/dxf/xlpe_foam.dxf`, `dxf/spacer_mesh_3d.dxf` (back-panel pieces)
5. `outputs/release/pack5200_v3.1_patterns/print_letter/step9_main_bag.pdf`, `dxf/challenge_ultra_200.dxf`, `dxf/cordura_330d_nylon66.dxf` (attachment marks missing)
6. `outputs/release/pack5200_v3.1_patterns/cutlist.md`, `cutlist.csv`
7. `outputs/release/pack5200_v3.1_patterns/README.md` (warns about F-03 only)
8. `designs/pack_5200/BUILD_PLAN.md`
9. `designs/pack_5200/cut/spreader/README.md`, `spreader_v2_drawing.pdf`, `spreader_v2_cut.dxf` (no H1 re-fit note)

The cheapest fix is one STOP block at the top of the release README that names files 1-6 and 8, plus one line in
`cut/spreader/README.md`. Both are released or owned files, so that is an orchestrator / owner call (RULES.md rule 2).

## 4. Proposed release order

Releases are cut where a physical gate already separates the work, so nothing waits on an unrelated test. Each
release regenerates its files from code (`patterns_v31.py` or its successor, `build_geometry.py`, `frame_h1.py`); no
hand edits.

| step | release | rows | gates before it ships | why this place |
|---|---|---|---|---|
| R0 | **Warnings now** (text only, no geometry): STOP block in the release README naming the unsafe files in section 3; H1 re-fit line in `cut/spreader/README.md`; float meat limit 53 kg (116 lb) and the 70 mm belly rule as a one-page user note | 3 (warnings), RD-22 (limit only) | owner OK to touch released text | costs an hour, closes the safety gap while the rest waits on tests |
| R1 | **Frame H1 package** (`print/frame/` replaced): H1 halves with the 4 x M5 pivot boss, bolted joint, P-1 bondline, crown rev C spec inline, mass booking, spreader pad and pucks re-fitted to H1 | RD-04, RD-05, RD-06, RD-11, RD-14, RD-19, RD-20 | CA-1, CA-5, insert pull-out test, T6 coupons with the 0.8 mm bondline, spreader.evaluate on H1; then first-article T9, T1-T5, T1 joint, bone-end 400 N | longest lead item (27 h print + coupons); everything else bolts to it; RD-11 changes the H1 geometry, so it must go in before the first print |
| R2 | **Back system + harness**: rails 120 / BP-08, mesh 370, sleeves 140, yoke plate 1.8 mm drawing, spreader in the release BOM | RD-13, RD-08, RD-19 (BOM) | BL-005 result; T1(c) with the yoke dial (may relax 1.8 to 1.5) | depends only on the frame interface; test T1(c) runs on the R1 first article |
| R3 | **Hipbelt B**: belt-B patterns S-XXL, 7075 plate + roll template, CFRP backer, routing, pockets IMP-5 | RD-07, RD-09, RD-10 | BL-006 result; HB-5, pad-seat sag test, HB-2/HB-3, ladder-lock qualification | the pad seat bears on the R1 frame lumbar pan; the 4 x M5 mount is already in R1 |
| R4 | **Bag CORRIE F + attachment + meat haul**: CORRIE F patterns with B-17..B-24 marks, rated hooks, float parts, IM1 990, bow riser carry, pockets, corrected record masses, F-03 gone | RD-01, RD-02, RD-03, RD-12, RD-15, RD-16, RD-17, RD-18 | BL-011 (after BL-010), PT-1..PT-6, wash-swatch fray test for B-1, swatch weights | the bag changes most and is gated by the most open tickets; releasing it last avoids re-cutting attachment marks twice |
| R5 | **Docs**: BUILD_PLAN.md rewrite and the full user guide | RD-21, RD-22 | R1-R4 | describes what was actually released |

If the owner wants a buildable SPINE bag before CORRIE F, an interim **R4a** can apply RD-01, RD-03, RD-12 (marks
per `bag_attachment.md` section 10), RD-15 and RD-18 to `patterns_v31.py`; the register already lists every file.

## 5. Found while building the register (not fixed)

1. **H1 lower half is not one closed shell.** `designs/pack_5200/print/frame_h1/h1_lower_flat.stl` loads as 5 bodies
   (trimesh, vertices merged): the main body (276.35 cm³, watertight), a 0.57 cm³ island at x 219-228, y 0-17,
   z 42-54 mm, and three degenerate slivers. `print/frame_h1/README.md` says both halves are watertight. The upper
   half is one watertight body. The island would print as a loose piece or a blob. Owner: structural-fea-engineer.
2. **Spreader stand-off pad thickness disagrees:** 4.9 mm in `cut/spreader/README.md` against "4.5 mm" in
   `frame_h1.md` sections 4 and 7. On H1 the pad is then 0.9 mm, not 0.5 mm, if the README is right.
3. **Insert capacity:** the new record `insert_heatset_brass_m5.yaml` gives 1200 N (estimate), below the 1500 N the
   2 x M5 check used. By linear scaling the 2 x M5 margins fall to about 0.91 / 0.80 (not re-run). Adds weight to RD-11.
4. **`spreader_v3_hdpe_cut.dxf` is labelled "BP-06 rev C SPREADER"** inside the file, the same revision letter as the
   production sandwich; only the folder README says it is not production.
5. **H1 README section 6 sends the builder to `../frame/PRODUCTION.md`** for the crown, a file that now opens with
   DO NOT PRINT (RD-20).
6. **No yoke plate drawing has ever been released** (RD-08); `patterns_v31.py` still says "yoke redesign pending".
7. **No DECISIONS row records the material-record corrections** of 2026-11-09 (RD-15) or the dowel booking on its
   own (RD-14).
8. **Part number B-21 is unassigned** in the attachment series (B-17..B-24); harmless, but a release cut list should
   say so to stop a builder looking for it.

## 6. How this was checked

- Every `docs/DECISIONS.md` row dated 2026-11-05 to 2026-11-10 was read and each design change either has a row
  here or is already in the released files (head setback two ring seams: already in the v3.1 patterns; B-10 tabs:
  already omitted; spreader Sandwich v2 and the crown rev C fix: in `print/frame/PRODUCTION.md`, carried as RD-19 and
  RD-20 because that file is now DO NOT PRINT). Owner choices still open (lighter-frame TENDON, fixed-torso,
  fabric swaps on hold) are not deltas.
- Frame volumes re-measured with trimesh: `genframe_lower_flat` 199.3 + `genframe_upper_flat` 242.2 = 441.5 cm³,
  `genframe_assembled` 737.9 cm³; `h1_lower_flat` 276.9 + `h1_upper_flat` 444.3 = 721.2 cm³ = `h1_assembled` 721.2 cm³.
- F-03 search: `pdftotext` on every letter PDF (only `step5_collar_fly.pdf` has it), `grep` on every DXF (only
  `robic_210d_ripstop.dxf`).
- The CSV was written by one script from one row list and checked: 22 rows, every `decision_source` names a file,
  no row points to an analysis without naming the file and section, `safety_relevant` is yes/no on every row.
