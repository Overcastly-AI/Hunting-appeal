# Pack 5200 - generative design of the carbon frame

Owner: structural-fea-engineer. Package: `huntkit/gendesign/` (SIMP 3D/2D, frame ground structure, surface extraction, printables). Run: `python -m huntkit.gendesign.cli stage lugs|plate|layout|printables|report` (cached per stage in outputs/gendesign/). Numbers in this file are generated into `designs/pack_5200/analysis/gendesign_results.yaml`; print/cut files are in `designs/pack_5200/print/`.

Load standard: **HA-LS-1** (`huntkit/fea/load_standard.py`, load_standard.md), all 9 cases at torso 15 / 19 / 23 in; frame model and member forces from `huntkit.fea` on `designs/pack_5200/frame.yaml` as it stood at run time (v1 crown topology, segmented stays). Fatigue: 1e5 cycles of 0 -> 1.6 g static carry.

## Result in one table

| item (per frame) | v1 frame (7075 sleeves, solid 4 mm plate) | generative | delta |
|---|---|---|---|
| crown corner x2 | 67 g | 82 g | +14 g |
| stay hub x4 | 167 g | 150 g | -17 g |
| lumbar elbow x2 | 69 g | 62 g | -7 g |
| stay foot x2 | 28 g | 57 g | +29 g |
| hip pivot mount x1 | 28 g | 20 g | -8 g |
| stay-top collar x2 | 35 g | 26 g | -8 g |
| lumbar plate | 217 g | 155 g | -62 g |
| **total of replaced items** | **611 g** | **553 g** | **-58 g (-2.0 oz)** |

Frame impact: the v1 frame.yaml total is 1103 g; with these parts it would be about **1045 g**. The same component deltas apply to the re-sized frame the other FEA run is producing (they replace hardware, not tubes), as long as it keeps the same joints.

## 0. Against the CURRENT frame (v2, 577 g)

While this study ran (on the v1 frame.yaml snapshot, 1103 g, 7075 sleeves), the frame was re-sized to the HA-LS-1 standard: straight stays (no lumbar elbow), **carbon-wrapped tube-to-tube joints** (65 g for every hub, corner and collar) and a 1.5 mm formed lumbar pan (110 g). Against v2:

| item | v2 (current frame.yaml) | printed Ti (this study) | delta |
|---|---|---|---|
| hubs + crown corners + stay-top collars | 65 g | 258 g | +194 g |
| foot boots (2) | 28 g | 57 g | +29 g |
| hipbelt pivot mount | 28 g | 20 g | -8 g |

**So, for the v2 frame: keep the carbon wraps at the hubs and corners** (printed Ti lugs are heavier than a 0.75 mm wrap; they win only against metal sleeves). Printed titanium earns its place where a wrap cannot go: the hipbelt pivot mount and the foot boot / shelf-pivot clevis (compare the rows above), and as a build aid: the PAHT-CF lugs are an accurate, jig-free way for a first-time builder to assemble the first prototype frame before learning to wrap. The same 2D SIMP run on the v2 1.5 mm pan web (cut-outs between the flanges) FAILS: web buckling SF/req 0.09 (need 1.5) with 4 cut-outs, so the thin formed pan stays solid; the cut-out plate below applies to a flat 3-4 mm plate only. 

## 1. Node lugs (3D SIMP, printed Ti-6Al-4V; PAHT-CF prototype)

Method (`huntkit/gendesign/simp.py`, `lugs.py`): voxel box around each frame node, 8-node hex elements, SIMP p = 3, hat density filter, Heaviside projection (beta 1-2-4-8), optimality-criteria update, weighted multi-case compliance with a volume constraint. Linear solves by CG with a pyamg smoothed-aggregation preconditioner (rigid-body near-null space). Non-design regions: the bond skin of every socket (solid) and the tube bores (void). Loads: frame-model member end forces [F, M] for every case/torso/side, left joints mirrored; each tube's resultant is spread over its bond-surface nodes as F/n + omega x r (exact force and moment). The anchor tube's bond surface is clamped. The 3 most severe load sets drive the optimization; ALL 9 cases are re-checked.

Verification (independent FEA): the density field is trilinearly up-sampled 2x, thresholded at 0.5, the exact socket geometry re-imposed, the largest connected body kept, and the solid-only voxel mesh re-solved with the real material (E, nu). Stress = element-centre von Mises, 99th percentile excluding elements on the clamped anchor (the clamp corner stands in for the bonded tube).

| lug | qty | grid (voxels, h) | vol. frac. | SLM Ti mass | 7075 baseline | SF/req (static) | governing case | fatigue SF | min wall | build dir / support |
|---|---|---|---|---|---|---|---|---|---|---|
| crown_corner | 2 | 25568 @ 1.93 mm | 0.025 | 40.9 g | 33.7 g | 9.1 | hipbelt_off_abuse | 29.7 | 1.9 mm | -x / 1948 mm2 |
| stay_hub | 4 | 25740 @ 1.67 mm | 0.025 | 37.5 g | 41.7 g | 15.1 | meat_shelf_heavy_low | 54.5 | 1.7 mm | -z / 1249 mm2 |
| lumbar_elbow | 2 | 25344 @ 1.67 mm | 0.025 | 31.0 g | 34.6 g | 6.1 | meat_shelf_heavy_low | 9.8 | 1.7 mm | +z / 493 mm2 |
| stay_foot | 2 | 25480 @ 1.48 mm | 0.025 | 28.5 g | 14.0 g | 22.8 | single_stay_setdown | 81.9 | 1.5 mm | -y / 1209 mm2 |
| hip_pivot_mount | 1 | 25432 @ 1.38 mm | 0.025 | 20.2 g | 28.0 g | 8.6 | side_hill_torsion | 19.7 | 1.4 mm | -y / 71 mm2 |

FDM prototype variants (PAHT-CF, 2 mm walls; strength check: von Mises vs 0.8 x XY strength AND stress normal to the layers vs 0.8 x Z strength 47 MPa, best of the 3 layer orientations):

| lug | mass | SF/req (all cases, full HA-LS-1 loads) | layer normal | fatigue SF | print time | filament cost |
|---|---|---|---|---|---|---|
| crown_corner | 38.0 g | 8.43 | x | 20.4 | 3.4 h | $3.50 |
| stay_hub | 34.1 g | 4.51 | x | 11.7 | 3.1 h | $3.14 |
| lumbar_elbow | 24.4 g | 5.32 | x | 6.0 | 2.2 h | $2.24 |
| stay_foot | 16.5 g | 5.78 | x | 20.9 | 1.5 h | $1.52 |
| hip_pivot_mount | 13.8 g | 6.45 | x | 4.5 | 1.2 h | $1.27 |

**Reading the lug results.** The frame-node loads are small for a titanium part, so every Ti lug is minimum-gauge governed: the volume fraction was walked down to the 2.5 % floor of the design box and the verified static SF/required is still 6.1 or more. What is left is mostly the bond sleeves themselves (1.0 mm Ti x 30-46 mm overlap per socket). Ti needs half the 7075 wall for about the same Volkersen stiffness E t, so the sleeve-dominated lugs get lighter: stay_hub, lumbar_elbow, hip_pivot_mount. Heavier: crown_corner, stay_foot - the crown corner carries a third (extension-post) socket that the 7075 baseline never costed, and the foot-boot baseline (14 g, a pack5200 hardware ASSUMPTION) is below what a 25 mm 2 mm 7075 sleeve alone weighs (14.5 g) before the shelf-pivot clevis and bumper. Voxel size 1.38-1.93 mm, so the measured minimum member is one voxel (>= the 1.0 mm SLM and 2.0 mm FDM rules); finer grids would thin the webs a little further but cannot remove the sleeves.

AlSi10Mg variant of the SAME STL files (scaled check, ASSUMPTION: geometry-driven stresses, so SF scales with the allowable: design yield 184 vs 785 MPa; fatigue as-built 60 vs 200 MPa; mass x 2670/4430):

| lug | AlSi10Mg mass | static SF/req (scaled) | fatigue SF (scaled) | vs 7075 baseline |
|---|---|---|---|---|
| crown_corner | 24.6 g | 2.14 | 8.9 | -9.0 g |
| stay_hub | 22.6 g | 3.54 | 16.4 | -19.1 g |
| lumbar_elbow | 18.7 g | 1.43 | 2.9 | -15.9 g |
| stay_foot | 17.2 g | 5.34 | 24.6 | +3.2 g |
| hip_pivot_mount | 12.2 g | 2.01 | 5.9 | -15.8 g |

AlSi10Mg lug set: 224 g per frame (vs 371 g Ti). It passes on paper and is lighter and ~1/3 the cost, BUT aluminium on carbon needs galvanic isolation (AlSi10Mg anodises poorly: use e-coat/chromate conversion plus a glass-bead bondline or E-glass ply), its lower E t raises the Volkersen peak slightly, and the fatigue margin is the thinnest. Ti stays the production recommendation for the hip-pivot mount and pawl (wear, fatigue, galvanic-neutral); AlSi10Mg is a valid cheaper option for the hubs once a vendor coupon confirms the as-built fatigue value.

Bonded sockets (huntkit.fea.joints.bond_check, MMA, 0.5 mm bondline, 30 mm / 40 mm overlap), worst factored load set per socket: average-shear SF / required factor and the elastic Volkersen peak SF (HA-LS-1 needs peak >= 1.0 at limit load; factored loads are used here, so it is conservative):

| lug / socket | 7075 2 mm: avg SF/req, peak SF | SLM Ti 1.0 mm: avg SF/req, peak SF |
|---|---|---|
| crown_corner / top_bar | 18.49, 3.58 | 18.49, 3.69 |
| crown_corner / post | 26.08, 24.78 | 26.08, 21.52 |
| stay_hub / stay | 3.13, 2.03 | 3.13, 2.16 |
| stay_hub / bar | 4.61, 3.79 | 4.61, 4.01 |
| lumbar_elbow / upper | 3.34, 2.73 | 3.34, 2.89 |

Stay-top collar (crown-leg bushing seat, not optimized: it is a plain ring): factored radial bushing load 1174 N (hipbelt_off_abuse|15|bush_top_L); Ti wall 1 mm gives ring-bending 432 MPa, SF 1.82 vs 785 MPa; 13.2 g each vs 17.3 g in 7075.

## 2. Lumbar / hipbelt plate (2D SIMP -> water-jet cut pattern)

Method (`huntkit/gendesign/plate.py`): Q4 plane-stress SIMP on the 250 x 140 mm plate (geometry.yaml x +-125, z 50-190), 1.25 mm pixels. Non-design: stay saddle-bond bands (stay OD wide) and the plate outboard of the stays, the D44 pivot-mount flange, pulley-guide/cam-buckle attachment pads, and 3t edge bands. Loads: the force each stay node puts into the plate in every case/torso (from the frame model's plate grillage), factored; anchor: the pivot insert (D30). Clean-up enforces the carbon-sheet rules: web >= 3t, edge distance >= 3t, cut-outs >= 3t clear of every bond band/insert/pad, inscribed cut-out >= 10 mm, internal corner radius >= 3 mm.

Checks on the cleaned plate (independent FEA at half the pixel size): CLT on a QI [0/45/-45/90]ns T700 laminate with Tsai-Wu first-ply failure and knockdowns (hot/wet 0.8, impact 0.65 compression); membrane stresses from the 2D FEA PLUS the frame model's plate bending moment divided by the remaining solid fraction of the weakest section; web buckling as a pinned column across the largest cut-out (HA-LS-1 buckling >= 1.5 x factor).

| option | mass | Tsai-Wu SF/req (membrane+bending) | web buckling SF/req | passes |
|---|---|---|---|---|
| t 4 mm, vol 0.3 | 155 g | 1.66 | 3.8 | yes |
| t 4 mm, vol 0.15 | 158 g | 1.48 | 4.2 | yes |
| t 3 mm, vol 0.3 | 105 g | 1.08 | 1.0 | no |
| t 3 mm, vol 0.15 | 105 g | 0.88 | 0.9 | no |

**Chosen: QI 4 mm, 4 cut-outs, 155 g vs 217 g solid 4 mm** (min web 13 mm >= 3t). Solid plate at the same thickness: Tsai-Wu SF/req 3.99. In-plane the plate is lightly loaded (membrane SF/req 16.8); bending of the free top edge sets the thickness, so the cut-outs go where in-plane SIMP says the web carries nothing and the bending check limits how big they get.
Cut file: `designs/pack_5200/print/cut/lumbar_plate_qi_t4_cut.dxf` (layers CUT, DRILL, TEXT; true scale, X = frame x, Y = frame z). Water-jet or CNC router (diamond-coated end mill, wet, dust extraction); seal cut edges with thin epoxy.

## 3. Frame layout (ground-structure optimization)

Method (`huntkit/gendesign/layout.py`): plastic lower-bound LP on a FRAME ground structure (tubes carry axial + bending + torsion): nodes = every joint and load/body-interface point of the frame model (26 nodes), candidate members = all pairs within the envelope (none through the wearer zone), each a thin round tube of fixed radius 11 mm with free wall area A; capacity |N|/N_p + (|M1| + |M2|)/M_p <= 1, |T| <= T_p (laminate first-ply allowables of the stay tube); loads = the frame model's self-equilibrated external loads + body reactions for all 9 cases, factored, at torso 15/19/23. The current topology is the same LP restricted to the existing members (contracted onto the nodes).

| layout | ideal tube mass (LP, worst torso) |
|---|---|
| current | 89 g |
| current + X upper bay | 89 g |
| current + X lower bay | 89 g |
| current + X both bays | 89 g |
| free ground structure | 71 g |

Discrete check on buyable roll-wrapped tubes (huntkit.fea, every case and torso, member first-ply SF of stays/bars/braces and frame buckling to HA-LS-1; braces OD 16 RW45 k3, each brace end a printed lug, X crossings a centre clamp):

| topology | lightest passing stay | tube mass | of which braces | brace lugs | member margin | buckling margin |
|---|---|---|---|---|---|---|
| current | OD 25 RW45 k3 | 218 g | 0 g | 0 | 1.18 | 2.48 |
| current + X upper bay | OD 25 RW45 k3 | 253 g | 36 g | 5 | 1.18 | 3.87 |
| current + X lower bay | OD 25 RW45 k3 | 250 g | 32 g | 5 | 1.22 | 2.77 |

Where the free ground structure puts its material (torso 19, top members by mass):

| member (node to node) | share of LP mass |
|---|---|
| HP - SP150 | 12 % |
| SP150 - TB2 | 7 % |
| SP150 - TB0 | 7 % |
| SL25 - SL520 | 7 % |
| SR25 - SR520 | 7 % |
| SL250 - SP150 | 6 % |
| SP150 - SR250 | 5 % |
| SR420 - TB2 | 5 % |

**Verdict: keep the current ladder topology.** The best braced option (current + X lower bay) is +82 g against the current frame once its 5 extra printed joints (~10 g each, ASSUMPTION from the lug study) are counted.  Why: the governing loads are OUT-OF-PLANE (bag CG 180-250 mm aft, shelf and tall-load lashing, hipbelt reaction at the pivot), which the stays and the lumbar plate carry in bending; in-plane X-bracing does nothing for those, so the LP gives the added X members zero area (identical LP mass with and without them) and the discrete check only adds their tube and joint mass. Torsion (side-hill, single-stay set-down) is already closed by the lumbar-plate torsion box and the bars.

Different stay arrangement: the free layout is 20 % lighter than the current one in this idealized sense, and it gets there with a CENTRAL load path: about 12 % of its mass is a member from the hipbelt pivot straight up to the yoke / crown top bar (a spine along the wearer's back), plus the outer stays above the mid bar. That is the internal-spine architecture, not X-bracing. It is NOT recommended now: the yoke and top bar move 203 mm with the torso adjustment, so that spine would have to telescope and lock (a second sliding joint carrying the main load), and the LP's ideal masses ignore buckling, minimum gauge and joints (the absolute grams are far below buyable tubes; only the ratio is meaningful). Worth a dedicated concept study if the crown is ever redesigned.

## 4. Allowables and knockdowns

- `data/materials/metals/ti_6al_4v_slm.yaml` (new, confidence estimate): HIP'd L-PBF YS 930 / UTS 1000 MPa ([LPBF Ti-6Al-4V ELI after HIP: YS 928 / UTS 1003 MPa](https://bohrium.dp.tech/paper/arxiv/992967918188757003)); **design yield 785 MPa** (= wrought S-basis 827 x 0.95 process knockdown, ASSUMPTION), design UTS 850. Fatigue 1e7, R = -1: machined + HIP 500 MPa, **as-built surface + HIP 200 MPa** (machining raises the AM fatigue limit ~3x, HIP adds 10-20 %: [Preprint 202601.0826 (2026): as-printed vs machined vs HIP fatigue of AM Ti-6Al-4V](https://www.preprints.org/manuscript/202601.0826)), as-built no HIP 160 MPa. HIP per [ASTM F3001-14(2021)](https://webstore.ansi.org/standards/astm/astmf300114). Lugs use the 200 MPa as-built value with Goodman for the mean stress.
- `alsi10mg_slm.yaml` (new): YS 230 as-built, design 184 MPa stress-relieved ([EOS AlSi10Mg MDS](https://eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg), [Granges GPM AlSi10Mg (stress-relieved YS min 184 MPa)](https://www.granges.com/globalassets/09.-kampanjer/01.-trillium/datasheet_gpm_alsi10mg_50um.pdf)).
- `pa12_cf_fdm_paht.yaml` (new): PAHT-CF XY 88 MPa, **Z 47 MPa used** (two revisions of the TDS disagree: 64 vs 47; [Bambu PAHT-CF TDS V2.0](https://cdn.shopify.com/s/files/1/0380/5149/files/Bambu_PAHT-CF_Technical_Data_Sheet.pdf), [Bambu PAHT-CF TDS v2 mirror, U Waterloo (Z 47 MPa)](https://uwaterloo.ca/rapid-prototyping-centre/sites/default/files/uploads/documents/bambu_paht-cf_technical_data_sheet_v2.pdf)); `pa6_cf_fdm.yaml` (new): PA6-CF XY 105 / Z 67.7 MPa dry, 81.7 / 64.4 conditioned ([PolyMide PA6-CF TDS V4.1](https://cdn.shopify.com/s/files/1/0151/1735/files/PolyMide__PA6-CF_TDS_EN_V4.1.pdf)).
- ASSUMPTION: FDM hot/wet knockdown 0.8 on both strengths; FDM 1e5-cycle limit 0.3 x static strength.
- Composite plate: CLT/Tsai-Wu with hot/wet 0.8 and impact 0.65 on compression (huntkit.fea.composite).

## 5. Cost, lead time, post-processing

- **Ti lug set per frame: ~$1221** (one-off, incl. HIP share and reaming; same files in AlSi10Mg ~$364 but re-run the check first). Basis: [JLC3DP, 3D Printing Titanium Cost in 2026 (Apr 2026): Ti SLM $5-20/cm3, 96 h service](https://jlc3dp.com/blog/titanium-3d-printing-cost) $5-20/cm3, reduced 47 % on 2026-07-24 ([JLC3DP pricing update, 24 Jul 2026: Titanium TC4 -47 %](https://jlc3dp.com/news/materials-finishing-pricing-update-july2026)); we use $8/cm3 + $25 HIP share + $12 per bore, min $30/part (ASSUMPTIONS). Xometry quotes Ti DMLS by RFQ ([Xometry DMLS (Ti Grade 5 on RFQ; Al/SS instant quote)](https://xometry.uk/direct-metal-laser-sintering/)); PCBWay lists TC4 and AlSi10Mg ([PCBWay metal 3D printing (AlSi10Mg, TC4; 2-3 business-day build)](https://www.pcbway.com/rapid-prototyping/3d-printing/metal/)). Get quotes with the STLs: the vendors' instant quoters are the source of truth.
- FDM prototype lug set: ~$28 of filament, ~28 h of printing.
- Lead time: Ti SLM 96 h build (JLC3DP) + batch HIP (1-2 weeks, often subcontracted: ask the vendor) + reaming -> plan **3-4 weeks**. AlSi10Mg 1-2 weeks. FDM same day.
- Post-processing chain (Ti): stress relief on plate -> wire-EDM off -> HIP -> support removal -> bead blast -> ream/bore the sockets to H9 (fixture on the opposite socket) -> grit blast + primer -> bond. A small shop can ream the sockets on a drill press with a fixture; the online vendor can also do it (CNC post-machining is listed by PCBWay).
- CF-nylon prototype note: print the PAHT-CF set first (one H2S plate, see the build-plate screenshot), bond it to scrap tube and proof-test (load_standard.md test plan) before ordering titanium.

## 6. Printable crown hardware (rack, pawl, pulley guides)

Geometry from geometry.yaml `crown_retention` (two-way trapezoid teeth, 4 mm pitch, 2 engaged, 20 mm wide rack, 230 mm long for the 203 mm travel; pawl with matching teeth, D4 pivot, release-cord eye, spring tang; 25 mm webbing guides with a rounded bar for a UHMWPE sleeve). Tooth-root shear check (the geometry.yaml method: teeth x width x 2 mm root x tau) against 1334 N x 1.5:

| part | qty | tier-1 file (SLM) mass | FDM PAHT-CF mass | SF/req SLM | SF/req FDM | FDM time | recommendation |
|---|---|---|---|---|---|---|---|
| crown_rack | 1 | 60.5 g | 24.0 g | 4.24 | 1.62 | 2.2 h | PAHT-CF (lighter than Al, adequate) |
| crown_pawl | 1 | 16.9 g | 5.4 g | 10.87 | 1.30 | 0.5 h | Ti SLM pawl |
| pulley_guide_fixed | 2 | 12.3 g | 4.9 g | - | - | 0.4 h | PAHT-CF (lighter than Al, adequate) |
| pulley_guide_moving | 1 | 10.8 g | 4.3 g | - | - | 0.4 h | PAHT-CF (lighter than Al, adequate) |

The FDM pawl is 16 mm wide (Ti: 12 mm) to keep the tooth shear above the requirement with the layer-plane strength. The SLM aluminium rack (60 g) is heavier than the PA66-GF30 molded rack it replaces (22 g); print the rack and guides in PAHT-CF for production too (or MJF PA12-GF at a service).

## Manufacturability caveats

- Voxel resolution is coarse (1.4-1.9 mm, ~25k voxels per lug): fine details are smoothed by marching cubes + Taubin smoothing; the socket sleeves are exact (boolean union), but the web shapes are approximate. Wall thickness >= 1.0 mm is checked on the verification mesh (min wall column).
- The study ran on the v1 frame snapshot (outputs/gendesign/frame_v1.yaml); re-run the lugs on v2 joint loads before ordering parts: `HUNTKIT_GENDESIGN_FRAME=designs/pack_5200/frame.yaml python -m huntkit.gendesign.cli stage lugs` (v2 has no elbows; loads are similar, margins are > 6x).
- Overhang is handled by choosing the build direction with the least > 45 deg down-facing area, not inside the optimization (no AM filter): expect some internal supports in the hubs; the vendor's DfAM check rules.
- Bond surfaces must be machined/reamed after HIP; sockets were modelled at final size.
- The Ti meshes carry a few sub-gram residual nubs on the sleeve OD (marching-cubes islands of grey density at the 2.5 % volume): harmless, remove at bead blast or in the vendor's DfAM review.
- Printed-Ti fatigue is surface-driven: the 200 MPa allowable assumes HIP; without HIP use 160 MPa (the lugs still pass because they are min-gauge governed).
- Galvanic: Ti on carbon is compatible (unlike Al): one less anodise step than the 7075 sleeves.
- FDM prototypes are not production parts: Z strength, moisture and creep; use them for fit, bonding practice and proof tests.

## Assumptions

- ASSUMPTION: frame-node loads from the linear beam model (huntkit.fea.pack5200) at the frame.yaml sizes current at run time; a re-sized frame changes them slightly; lugs have > 3x margin so the shapes stand.
- ASSUMPTION: socket overlap 30 mm (end) / 40-46 mm (through), bondline 0.5 mm, as frame.yaml joints.
- ASSUMPTION: the shelf-pivot boss on the foot boot sits 8 mm aft of the sleeve OD (the hard point shelf_pivot lies inside the tube).
- ASSUMPTION: stress = 99th percentile element von Mises (stair-step voxel corners excluded); clamped anchor elements excluded.
- ASSUMPTION: plate bending moments taken from the 4 mm (or 3 mm) grillage model and scaled by 1/phi for the cut sections (no moment redistribution credited).
- ASSUMPTION: cost and lead-time figures as listed in section 5.

## Screenshots

- `outputs/screens/20261101_gendesign_1.png` - crown_corner lug render
- `outputs/screens/20261101_gendesign_2.png` - stay_hub lug render
- `outputs/screens/20261101_gendesign_3.png` - lumbar_elbow lug render
- `outputs/screens/20261101_gendesign_4.png` - stay_foot lug render
- `outputs/screens/20261101_gendesign_5.png` - hip_pivot_mount lug render
- `outputs/screens/20261101_gendesign_6.png` - lumbar plate cut pattern
- `outputs/screens/20261101_gendesign_7.png` - layout optimization
- `outputs/screens/20261101_gendesign_8.png` - mass comparison
- `outputs/screens/20261101_gendesign_9.png` - FDM build plate
- `outputs/screens/20261101_gendesign_10.png` - SIMP benchmark + convergence
