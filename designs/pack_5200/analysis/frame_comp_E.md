# Frame competition, Team E (FIBRE): LOOM, a continuous-fibre printed ladder

Owner: structural-fea-engineer (Team E), 2026-11-10. Rules: [RULES.md](../frame_comp/RULES.md). Standard:
HA-LS-1 rev C ([load_standard.md](load_standard.md)). Research and every allowable: [docs/research/frame_comp_E.md](../../../docs/research/frame_comp_E.md).
Code: `huntkit/gendesign/frame_comp_e.py` (`python -m huntkit.gendesign.frame_comp_e`, about 25 s on 1 core).
Tests: `tests/test_frame_comp_E.py` (12 pass). Results: `designs/pack_5200/frame_comp/E/result.json`,
`analysis_results.json`, `rows.json`. Margin = SF / requirement, pass >= 1.00.

## 0. Verdict

**LOOM passes every HA-LS-1 rev C check at beam level on assumed allowables, but it does not beat today's frame.**
Frame **1124 g vs 1063 g (+61 g)**, frame + spreader 1286 g, CORRIE B.2 pack (M) **4025.6 g**. Worst margins:
strength 1.07, fatigue **1.01**, joint 1.06; twist stiffness **1.32 x today**. It costs about **$3,974** for the
first frame (printer included) against about $427 today, and needs about **77 machine hours** on a printer that is
still in pre-sale. The honest reading: continuous fibre makes the members stiffer and the bending efficient, but this
frame's mass is set by things fibre does not help: the 18 mm crown-leg sleeve bore over the whole leg travel, the
interlayer shear of a flat print, and a matrix (PA6-CF, 1.2 g/cm3, 40 MPa) that is denser and weaker than PAHT-CF
(1.06 g/cm3, 88 MPa). Sensitivity: with a PAHT-CF-density matrix the frame would be about 1059 g (-4 g), i.e. a draw.

## 1. Concept

- **Topology:** the frame.yaml v2 ladder (two straight stays at x +-115, mid bar z 330, upper bar z 520 with the
  pawl, lumbar lattice z 50-190 with the hip pivot at z 120), planar so it prints **flat** (wearer face on the bed,
  layer normal = frame y). Today's branch body cannot carry continuous fibre: its limbs curve through 73 mm of y, so
  each layer would cut their fibre into short pieces (research section 5).
- **Fibre:** out-of-plane bending (the dominant load: bag CG 205 mm aft) is carried by **flange layers** of
  concentric CCF at the bag and wearer faces of every member; in-plane bending and the corners by **concentric rings**
  that run round each ladder window without a cut. Matrix-only regions carry the fixed interfaces.
- **Segments:** two prints <= 300 mm (FibreSeeker 3 bed 300 x 300): lower z 0-290, upper z 290-545. Joined on each
  stay by a **bolted clamshell splice** (half-shells stacked in y, 4 x M5 Ti through the side walls, two rows 40 mm
  apart). No adhesive anywhere in the load path.
- **Fixed interfaces unchanged:** carbon crown with the rev C fix, rack / pawl (304 bushing), bushings, Ti hip pivot
  with 4 x M5 inserts, Sandwich v2 spreader, 8 fairleads and the bag hard points; P-1 0.8 mm post-socket bondline.

| member | b x h mm (in-plane x depth) | fibre | core | g / mm | fibre mm2 |
|---|---|---|---|---:|---:|
| stay lower z 0-130 | 16 x 22 | flanges 1.0, 1 ring | 20 % | 0.205 | 63 |
| stay upper z 130-520 (sleeve, 18 mm bore) | 26 x 23 | flanges 1.25, 2 rings | solid | 0.438 | 131 |
| stay top z 520-530 (top bushing cuff) | 30 x 22 | flanges 0.5, 1 ring | solid | 0.500 | 64 |
| mid bar | 16 x 10 | flanges 0.25, 2 rings | 20 % | 0.111 | 38 |
| upper bar (pawl) | 26 x 26 | flanges 2.5, 1 ring | 20 % | 0.409 | 158 |
| lumbar ribs z 50 / 120 / 190 | 20 x 16 | flanges 1.5, 1 ring | 35 % | 0.244 | 77 |
| lumbar centre column | 20 x 16 | flanges 0.25, 1 ring | 35 % | 0.203 | 35 |
| lumbar ties | 6 x 5 | flanges 0.25, 1 ring | solid | 0.038 | 9 |

Sizing: discrete fully-stressed search (`size`), 4 passes, the lightest section per group reaching 1.05 on strength,
fatigue, creep and the sleeve ring, re-solving the beam model each pass (stiffness redistributes load).

## 2. Method

- **Loads:** the frame.yaml v2 beam model (the load source of every production check), every rev C set: 9 cases with
  the bag couple on the crown bar plus 5 bag cases with it on IM3, torso 15 / 19 / 23 in (42 sets), extension posts
  for C6p. Stays, bars and lumbar strips are replaced by `PrintedSection`.
- **Section model:** discretised transformed section (0.1 mm grid) of fibre strands (E 60 GPa, 1.4 g/cm3) and
  matrix (E 2.4 GPa x core density, 1.2 g/cm3), 2 matrix walls (0.8 mm) and 4 roof / floor layers (0.5 mm).
  Checks per element end: fibre tension / compression; matrix normal stress; **interlayer shear** = Vz Q / (EI w) on
  the layer planes plus torsion (Bredt round a bore, Saint-Venant solid); in-plane shear = Vy Q / (EI w) plus
  torsion. Sparse core counts by its density in the shear width.
- **Allowables:** fibre 800 / 320 MPa x 0.85 part x 0.8 hot/wet (x 0.65 impact on compression) = 544 / 141 MPa;
  ILSS 14 x 0.6 = 8.4 MPa; in-plane shear 20 x 0.6 = 12 MPa; matrix 40 x 0.6 = 24 MPa; Z 30 x 0.6 = 18 MPa.
- **Fatigue:** C1 (1 g) x 1.6, 1e5 cycles: fibre FI <= 0.5, matrix / interlayer / bearing <= 0.3. **Creep:** C1 at
  1 g, matrix <= 0.4. **Buckling:** beam eigenvalue >= 1.5 x factor. **Crown:** `frame_cg_recheck._crown_rows` on the
  new stiffness.
- **Verification (tests):** homogeneous section = b h, b h^3/12 (0.1 %); rectangular shear 1.5 V / A (2 %);
  flange EI by parallel axis (1 %); flange stress M z / EI; Bredt box J and q / t; cantilever tip deflection P L^3 / 3EI
  with the printed section in the solver (1 %); Euler fixed-free pi^2 EI / 4L^2 (2 %); ring moment 0.318 F R.

## 3. Results, worst torso and couple variant

| member | strength | mode, set | fatigue | mode | creep |
|---|---:|---|---:|---|---:|
| stay lower | 1.15 | interlayer, C_im3 side_hill_torsion 23 | 1.08 | interlayer | 2.30 |
| stay upper | 1.20 | fibre compression, C_im3 stumble 23 | 1.13 | fibre c | 3.03 |
| stay top cuff | 1.25 | interlayer, C_im3 hipbelt_off 15 | 1.19 | interlayer | 2.55 |
| mid bar | 1.12 | fibre c, C side_hill_torsion 15 | 17.2 | matrix | 36.7 |
| upper bar | 1.09 | fibre c, C hipbelt_off 15 | 1.89 | interlayer | 4.04 |
| lumbar ribs | 1.21 | fibre c, C_im3 stumble 15 | 1.13 | fibre c | 2.52 |
| lumbar column | **1.07** | interlayer, C_im3 side_hill_torsion 15 | 1.01 | fibre c | 2.27 |
| lumbar ties | 1.07 | fibre c, C_im3 stumble 15 | **1.01** | fibre c | 4.43 |

| joint / interface | margin | set |
|---|---:|---|
| splice bolts, bearing (factored) | 2.49 | C_im3 stumble 23 (3698 N flange force, 939 N per bolt) |
| splice bearing fatigue | 1.40 | C_im3 static carry 23 |
| sleeve ring, low bushing (Z across layers) | 1.47 / fatigue **1.06** / creep 2.27 | C_im3 hipbelt_off 23 / static carry 23 |
| sleeve ring, top bushing | 1.41 / fatigue 1.34 / creep 2.87 | |
| pawl cheek (fibre loop + 304 bushing bearing) | 1.41 / fatigue 2.28 | C hipbelt_off 15 |
| buckling (>= 1.5 x factor) | 1.21 | C side_hill_torsion 15 |
| crown legs / top bar / spine | 1.12 / 1.14 / 1.18 | C_im3 hipbelt_off (same as released: 1.12 / 1.25 / 1.18) |
| crown corner bond avg / Volkersen peak | 2.46 / 1.28 | C tall_load_posts 15 |
| post socket Volkersen peak (P-1 0.8 mm) | 1.20 | C tall_load_posts 15 |
| twist stiffness | 5.74 N m/deg = 1.99 x tube frame = **1.32 x today** | record test (HP clamped) |

Charts: `outputs/screens/20261110_compE_1.png` (today vs LOOM), `outputs/screens/20261110_compE_2.png` (member
utilization and every margin).

## 4. Mass

| item | g |
|---|---:|
| stays lower / upper / top | 53.4 / 342.1 / 10.0 |
| mid bar / upper bar | 25.6 / 94.0 |
| lumbar ribs / column / ties | 176.0 / 28.5 / 39.2 |
| interface features (ASSUMPTION: pawl housing 22, hip boss 16, fairlead cheeks and hook bosses 30, clip lands 10, feet and cuffs 14, corner fillets and splice collars 24) | 116.0 |
| **printed body** (fibre 234 cm3 = 2.13 km of strand, matrix 557 g) | **884.8** |
| Ti splice bolts 8 x M5 | 20.8 |
| kept hardware (crown, rack, pawl, bushings, Ti mount; today's 240 g less dowels 17.5 and MMA 4) | 218.5 |
| **frame** | **1124.1** (today 1063) |
| frame + Sandwich v2 spreader 162 | 1286.1 (today 1225) |
| CORRIE B.2 pack, belt M | 4025.6 (today 3964.5) |

Mass reductions that keep the margins (not taken, unverified):
1. **Lumbar as a planar X of fibre struts** from the hip boss to the stays (like today's branch X) instead of three
   ribs: the ribs carry the hip load in in-plane bending over 230 mm; struts carry it axially. Estimate -80 to -110 g.
   Needs nodes the frame.yaml grillage does not have; not modelled.
2. **PAHT-CF as the FFF matrix** on the FibreSeeker (it lists PA-CF): -65 g at equal volume, if X-CCF bonds to it
   (E-2 on that pair). With 1 and 2, about 950-980 g frame, i.e. -80 to -110 g vs today.
3. **Sleeve only where the leg bushing travels** (z 136-410) plus the top cuff; an open channel between: about -30 g.

## 5. Cost, hours, build

- Machine: FibreSeeker 3 (home; $3,199 US pre-sale, ship date not stated). Print **76.6 h** (2.13 km of fibre at an
  ASSUMED 10 mm/s plus 557 g matrix at 8 mm3/s), two segments.
- Unit cost $775 (fibre $258 at $55 / 500 m, matrix $48, 20 % reprint allowance $61, machine $77, Ti bolts $20,
  inserts $3, kept hardware $101, spreader $207). First frame $3,974; per frame at 10 $1,095, at 100 $807 (100 frames
  is 7,700 machine hours: several printers).
- Owner hands-on about 8 h: fibre layout in the slicer per segment, two prints, ream the sleeve bores, inserts, splice,
  crown and hardware as PRODUCTION.md. **Intermediate**: fibre-path set-up and a new machine class. Easier than
  wet layup, harder than the H2S body (two filaments, fibre cuts, bridging the bore roof as a 45 deg teardrop).
- Service alternative: no listed machine prints the frame in one piece (FX20 525 mm < 540 mm), so a service build is
  also two segments; at the published $3 / cm3 CCF rate the fibre alone is about $700.

## 6. Risks

1. **Interlayer shear is unproven.** Published printed CF/PA6 ILSS spans 2.8 to 34 MPa; the design uses 14 x 0.6.
   Stay lower and lumbar column strength are interlayer-governed (1.15, 1.07). A 30 % low E-2 result fails rev C.
2. **Fatigue rule is borrowed.** No endurance data exist for printed CCF; fatigue governs at 1.01 (ties, column) and
   1.06 (sleeve ring). E-5 / E-6 decide it.
3. **Platform risk.** FibreSeeker 3 is in pre-sale with no datasheet for X-CCF; the analysis uses Markforged coupon
   data x 0.85. The Markforged route is quote-only and still two segments.

## 7. Assumptions

- ASSUMPTION: the frame.yaml v2 beam model is the load path; stays printed planar (beam nodes y 0 to -10 are kept);
  lumbar grid kept as an open lattice with the lumbar-pad springs on its nodes; no voxel FE of the junctions.
- ASSUMPTION: fibre-region properties = Markforged UD coupons x 0.85 (Pertuz 2020 mixed specimens: 165 MPa).
- ASSUMPTION: ILSS 14 MPa dry, in-plane shear 20 MPa, bolt bearing 60 MPa dry, matrix hot/wet 0.6.
- ASSUMPTION: fatigue ratios 0.5 (fibre) / 0.3 (matrix, interlayer, bearing); creep 0.4.
- ASSUMPTION: corner turn radius >= 10 mm (E-7), 0.6 mm matrix liner in every bore.
- ASSUMPTION: interface features 116 g; hip inserts in PA6-CF as good as in PAHT-CF (E-4 type pull-out on the first
  article).
- ASSUMPTION: Ti-6Al-4V M5 single shear 0.6 x 900 x 14.2 x 0.6; no clamp-friction credit (nylon creep relaxes preload).
- ASSUMPTION: fibre lay rate 10 mm/s; matrix filament $80/kg; reprint allowance 20 %.
