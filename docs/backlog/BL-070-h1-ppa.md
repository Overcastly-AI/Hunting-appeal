# BL-070 H1 on PPA-CF: the checks BL-069 skipped, and H1-P (H1 re-tuned for PPA-CF)

**Agent:** structural-fea-engineer · **Size:** L · **Depends on:** BL-069 (PPA-CF record), BL-058 (H1 print + whole-body
rules), BL-065 (eigen buckling), BL-066 (export lesson), BL-068 (lash loads) · **Date:** 2026-11-25

Ask (owner, 2026-11-25): "Work with a ppu 3d printed frame." BL-069 read this as Bambu PPA-CF and swapped only the
allowables on the released H1 print. This ticket makes the best PPA-CF frame:
1. Re-run on PPA what BL-069 skipped: the z 234 joint, the US2 lug and clevis, the hip-mount inserts on the HB-6 basis,
   and a real eigen re-solve (BL-065 supports).
2. Re-tune the geometry for PPA (H1-P) with every bag and hardware interface frozen. Target: every HA-LS-1 row >= its
   goal, including cinch-cycled >= 1.0 on PPA design values, and body <= 1069 g.
3. Check printability on the H2S.
4. Specify the PPA coupons as register rows.
5. Export the H1-P STLs and check them on the exported geometry.

## Deliverables
- Code: `huntkit/gendesign/bl070_h1p.py`. It covers the PPA material swap, the layer rule per axis, the
  whole-body check with term shares and the orientation study, the interface checks, the H1-P resize rules, the
  export-space design step, printability, the coupon rows and the record.
- Tests: `tests/test_bl070_h1p.py` (13 tests). They cover the record-rule reproduction, the PAHT controls, hand values
  for the capacities, the frozen-voxel rules, the record rows against their goals, and the exported raster being the
  checked one.
- Record: `designs/pack_5200/iter1/frame/bl070_h1p.{json,md}`.
- STLs (STL only, for review): `designs/pack_5200/iter1/frame/h1p/`. Files: `h1_assembled.stl`,
  `h1_lower_flat.stl`, `h1_upper_flat.stl`, `us2_clevis_L.stl`, `us2_clevis_R.stl`. All are watertight and on the
  H2S bed.
- Scratch, untracked: everything in `outputs/bl070/`, including the check caches, utilisation fields, eigen runs,
  logs and the loop scripts `run_design*.py` / `run_export_loop.py`.
- Screenshots: `outputs/screens/20261125_bl070_{1,2,3,4}.png`.

## Result

| row (goal) | PAHT-CF H1 (record) | PPA-CF H1 (same print) | **PPA-CF H1-P (exported)** |
|---|---:|---:|---:|
| strength, min of 3 static bases (1.0) | 1.63 | 1.71 | **1.70** |
| fatigue, static carry (1.0) | 1.25 | 1.48 | **1.87** |
| **fatigue, cinch-cycled R1 (1.0)** | 0.86 | 0.94 | **1.08** |
| creep (1.0) | 1.83 | 2.75 | **3.16** |
| z 234 joint strength / fatigue (1.0) | 1.98 / 1.05 | 1.89 / 1.04 | **1.65 / 1.05** |
| US2 lug strength / fatigue (1.5 / 1.15) | 3.34 / 1.50 | 3.25 / 1.46 | **3.18 / 1.43** |
| US2 clevis joint, share 1.0 (1.5 / 1.15) | 3.02 / 1.36 | 2.69 / 1.21 | **2.69 / 1.21** |
| hip mount strength / fatigue / creep (1.5 / 1.15 / 1.5) | 2.15 / 1.21 / 2.58 (inserts) | 1.88 / **1.06** / 3.10 (inserts) | **7.54 / 4.24 / 12.45** (through-bolts) |
| lash pulls W1 / W2, p99 (1.0) | 4.18 | 3.76 | **5.15** |
| buckling eigen, frame crown held (1.0; bonus 1.15) | 1.34 | 7.03 | **3.72** |
| buckling eigen, set-down, foot + crown held (1.0) | 4.11 | 21.6 | **20.6** |
| buckling eigen, members, stay tops free (1.0) | 1.47 | 7.81 | **6.48** |
| **printed body (halves + US2 clevises)** | **1069.3 g (2.36 lb)** | 1261.0 g (2.78 lb) | **1268.1 g (2.80 lb)** |

- **H1-P passes every HA-LS-1 row on PPA design values, on the exported STL re-rastered.** It lifts R1 from 0.94 to
  **1.08**. The minimum margin over the rubric's Strong rows is 1.05 (z 234 joint fatigue), against PAHT H1's 0.86.
- **It cannot reach 1069 g.** The lightest passing H1-P is **1268.1 g, +198.8 g (+7.0 oz) against PAHT H1** and
  +7.1 g against H1 printed in PPA. Reasons are in section 2.
- **H1 printed in PPA as released is not buildable on design values.** R1 is 0.94. The hip-mount inserts read
  fatigue 1.06 on the HB-6 basis scaled by knocked Z, and 0.70 on the record's INS-Z rule as written (goal 1.15).
- **The PAHT controls reproduce the record.** Whole body cinch-cycled: 1.692 / 0.856 / 1.825, z 234 joint 2.001 / 1.05,
  record buckling 1.02. Hip pattern: 2.149 / 1.208 / 2.58. Clevis share 1.0: 3.02 / 1.36. Lash: 4.18.
- **The release export path reproduces the released print.** The H1 voxel source sent through
  `h1_buckling.export_print` gives exactly the released `h1_assembled.stl` volume (1 008 794 mm3).

## 1. H1 on PPA: what BL-069 skipped

- **Why R1 fails on PPA.** 92 % of the R1 top 1 % is interlayer shear, almost all of it tau_xy (92 %). The lumbar
  struts (60 % of the top 1 %) and the hip-boss ring (33 %) run along x and carry the fore-aft load into the hip
  clamp. That makes horizontal shear on the layer planes. PAHT was 61 % in-plane there.
- **z 234 joint (ASSUMPTION JOINT-Z retired).** The joint fatigue is 1.04, not the ~0.92 BL-069 feared. The governing
  rows:
  - strength: boss bending + prying, 1.95 cinch-cycled;
  - fatigue: boss bending + prying, 1.04 (fine_sm8.cyc), and plug shear-out (interlayer) 1.51.
- **US2 lug and clevis.** The lug reads 3.25 / 1.46 and the clevis 2.69 / 1.21 at share 1.0. Both pass.
- **Hip mount, HB-6 basis.** The capacity per insert depends on the reading:
  - record rule (1200 N x hot 0.73 x Z/XY TDS 0.339): 297 N;
  - absolute knocked Z (1200 x 0.73 x 45 / 88): 448 N.
  - The 8-insert pattern needs **488 N** (fatigue goal 1.15 x T_walk 127 N / 0.30), so it fails on PPA either way.
- **Lash pulls.** The BL-068 lash loads read p99 3.76 (levelled) and 2.45 (helix).
- **Eigen, a real re-solve at E 8526 MPa.** The frame with the crown held reads **7.03** (stay lower L, side-hill).
  That is 1.336 x 5.26 to the digit: BL-069's scaling holds because the voxel solve is isotropic and linear in E.
  - Set-down with the foot and crown held: 21.6. Members: 7.81.
  - The record model as is (top free) reads 0.84, against PAHT's 0.16. That is the BL-065 artefact: no wearer and
    no crown bar holding the frame.
  - Lower bound: if the layer-normal modulus governed (x E_z / E_xy = 0.364), the frame would still read 2.6.
- **Print orientation per half.** Every set was re-read with the layer normal along frame x or z for the lower half or
  the upper half. Face down (as released) is best for both halves on every basis. R1 on H1 is 0.94 face down, against
  0.53-0.69 with either half on its edge or end (table in `bl070_h1p.md`). Standing a half up moves the frame's
  in-plane bending across the layers. **Keep both halves face down.**

## 2. H1-P: what changed and why it is not lighter

Every interface is frozen: pins, clevises, hip boss face and its 8 screw positions, crown sleeves and bores, pawl
housing, spine channel, z 234 bosses, nut traps, fairleads, lug blocks, the BL-053 lug-fix hulls, the stay feet, the
BL-068 lash points (12 mm round each) and the wearer face (the plate face). Team A's member floors stay.

**Changes, all on the H1 2 mm grid, net +7.1 g against H1 in PPA:**

| region | added g | removed g | net g |
|---|---:|---:|---:|
| lumbar struts / pan (the R1 hot spot: wider and deeper struts at the hip-boss ring) | +24.2 | -0.6 | **+23.6** |
| hip-boss ring (outside the D50 face, not under the mount) | +8.7 | -3.5 | +5.2 |
| stay roots z 160-240 (branch / strut roots) | +5.0 | 0.0 | +5.0 |
| mid bar / upper bar (in-plane governed, PPA XY x 1.74) | +5.7 | -20.4 | **-14.6** |
| stays below the sleeve | +3.8 | -10.0 | -6.1 |
| inboard branches | 0 | -4.6 | -4.6 |

- **Hip mount: M5 through-bolts with hex nuts.** The Ti mount, the D50 face and the 8 screw positions are unchanged.
  - The 8 pilot holes become D5.5 through holes, with a hex trap (8 AF, DIN 934 M5) from the boss's back face down to a
    seat 13 mm behind the mount face.
  - Hardware: 8 x Ti gr5 M5 x 20 DIN 7984 + 8 x A2 nuts with Loctite 243, replacing 8 brass inserts + 8 x M5 x 12.
    That is about +2.4 g of hardware (ASSUMPTION: 1.1 g per nut, 0.7 g per extra 8 mm of Ti screw).
  - The screw load bears on the layers in compression: 1800 N per nut seat on knock x Z design. The pull-out row is
    gone, and the mount reads 7.54 / 4.24 / 12.45.
  - The traps open upward on the face-down print, and the holes print vertical from the plate face, so neither needs
    support.
- **Why not <= 1069 g.**
  - About 79 % of H1's voxels are frozen interface or floor material: the keep mask (crown sleeves, bores, pawl, spine channel) is 53 k of 115 k
    voxels, and the hard points dilated 6 mm are 46 k (the two overlap).
  - The exact export features (US1 lug-fix hulls, D50 boss) put back what the voxel model took off. Voxel step c3 read
    1225.5 g, but exported as is it came out at 1256.2 g, and its R1 fell from 1.035 to 0.987.
  - Below a utilisation of 0.3, about 19 k voxels (190 g) are thinnable at most, and member depth caps that.
  - Meanwhile R1 needs about +24 g of interlayer-shear area at the lumbar struts.
  - PPA's in-plane strength and stiffness pay off only where in-plane stress governs (the mid and upper bars, -15 g).
    Everywhere that matters the frame is interlayer-shear limited, and PPA's design Z is 0.875 x PAHT's while its
    density is 1.18 x.
  - Getting to 1069 g needs an architecture change, not a re-tune.
- **Design path** (record table "Design steps"):
  - Seven voxel-model steps (b1-c3).
  - Then, after the export showed the loss, three steps designed and checked on the export itself: e1 1294.6 g / R1
    1.15, f1 1275.1 / 1.10, g1 1268.1 / 1.08.
  - **g1 is H1-P.** It is the lightest export step that passes.
  - One 4-face pinch at (-114, 9, 113) in the grown export was fused, adding 20 voxels in the allowed space.

## 3. Printability on the H2S (PPA-CF, both halves face down, as released)

| half | plate contact | supported area | support (est / high) | filament, high + 8 % | 0.75 kg spools | time |
|---|---:|---:|---:|---:|---:|---:|
| H1-P lower | 1773 mm2 | 12 828 mm2 | 67 / 129 g | 799 g | 1.07: **swap** | 20.3 h |
| H1-P upper | **163 mm2** | 17 723 mm2 | 66 / 122 g | 802 g | 1.07: **swap** | 20.6 h |

- **Plate contact.** The upper half touches the plate on 163 mm2, measured on the current mesh with the
  `frame_h1_build` flat-face rule. The released H1 upper half reads the same 163 mm2. BL-069's 223 mm2 was an older
  reading. H1-P does not change the plate face, which is frozen. With PPA's 3x modulus and crystallisation at 178 C
  this is the warping risk:
  - pre-heat the chamber 30 min at 65 C;
  - glue stick on textured PEI;
  - brim 15 mm, plus 20 mm mouse-ear discs at both stay feet and both upper stay ends;
  - no part cooling below z 3 mm (ASSUMPTION WARP; the first article settles it).
- **Supports.** Same-material tree supports, the same plan as BUILD_H1 section 3. The scars land on the wearer faces
  of the stays. Sand them as in BUILD_H1.
- **Spool.** Each half can need just over one 0.75 kg spool. Start each half on a fresh dried spool and stage a
  second dried spool for the run-out swap (ASSUMPTION SPOOL-SWAP). Two halves plus coupons need about 3 spools, about
  $450.
- **Time.** About 20 h a half by the BL-053 rule at the PAHT volume rate (ASSUMPTION PPA-TIME; the slicer preview
  settles it).
- **Bed.** Both halves fit 340 x 320 with the brim, as released.

## 4. Coupons: register rows (not written into the kit or register)

The pass lines tie to H1-P's margins. Where interlayer shear governs, a margin M on the knocked design Z (32.85 MPa)
holds while the measured knocked Z is >= 32.85 / M (ASSUMPTION LINEAR-Z). The tightest H1-P row on Z is the z 234
joint fatigue, 1.051, so **H1-P needs a conditioned Z of 31.3 MPa.** BL-069's H1 needed 35.1.

| id | coupons | pass line | settles |
|---|---|---|---|
| **CA-1-PPA** | R 0.1 tension fatigue. 6 Z-built + 6 XY-built ISO 527-2 1A bars, plus 3 static of each from the same plate. Conditioned 14 d at 23 C / 50 % RH | Every coupon runs out to 1e5 cycles at Smax = **0.279 x** the batch's conditioned mean UTS (= 0.30 / R1 1.076) | FAT-PPA |
| **CA-3-PPA** | Z tensile (printed standing) and short-beam shear (ASTM D2344, mid-plane on a layer interface), 6 + 6 dry (as printed, sealed) and 6 + 6 conditioned | (a) conditioned Z, mean - 2.4 SD, **>= 31.3 MPa**; (b) conditioned SBS, mean - 2.4 SD, **>= 18.8 MPa**; (c) for the record: dry Z mean >= 45 MPa, conditioned / dry >= 0.73 | WET-PPA, design Z, INTERLAYER-0.6 |
| **CA-4-PPA** | ISO 178 3-point bend, XY bars 80 x 10 x 4, 5 per condition: 23 C dry, 40 C after 14 d at 23 C / 50 % RH, 60 C dry | E(40 C wet) / E(23 C) **>= 0.85**; E(60 C) / E(23 C) **>= 0.75**; flexural strength at 60 C **>= 152 MPa** (0.73 x 208). Buckling alone would accept 0.23 | E-SCALE |
| **T4c-PPA** | H1-P lower stay z 0-240 (R) cut from the lower-half file, 3 in PPA-CF + 1 PAHT-CF control, 2.0 kg slug pinned through the hinge eye. Soak >= 4 h at -20 C | Drop 1.22 m (48 in) onto 19 mm plywood over concrete, foot first then side-on (about 24 J each), within 60 s of removal. **No crack or whitening** (10x loupe, dye penetrant), tap test clean. Then 3-point bend at 1.5 x its C4 set-down stay moment without a crack. **Any crack along a layer fails** | COLD (Z Charpy 4.3 against PAHT 13.3 kJ/m2) |

- If inserts are kept instead of through-bolts, an **HB-6-PPA** row is needed: 6 PPA coupons, pull along the build z
  at 60 C, each >= **488 N**. On design values that is not expected to pass (448 N). With the through-bolts, the
  existing HB-6b hip-mount proof on the frame covers the mount.
- If CA-3-PPA reads between 31.3 and 28 MPa, R1 would be 0.9-1.0: hold the PPA build and add another hot-spot growth
  step. Below that, stay on PAHT-CF.

## ASSUMPTIONS THAT GOVERN
All of these are listed in `bl070_h1p.json` with what settles each. They are:
- PPU=PPA, WET-PPA, FAT-PPA and INTERLAYER-0.6;
- LINEAR-Z and E-ISO / E-SCALE;
- JOINT-Z (now an input, not a scaling), INS-PPA and NUT-BEAR;
- H1P-RULES;
- PPA-TIME, WARP, COLD and SPOOL-SWAP.

The FE is isotropic and unit-modulus, so stresses do not redistribute for PPA's 3x stiffer layers (E_z / E_xy 0.36).
The layer rule takes the anisotropy only in the strengths.

## OWNER DECISIONS NEEDED
1. **Material.** Options:
   - **(A) Stay on PAHT-CF H1:** 1069 g, R1 hold 0.86.
   - **(B) PPA-CF H1-P after the coupons:** recommended if PPA is wanted. Body +199 g (+7.0 oz). R1 1.08. Creep,
     buckling and 60 C truck-cab stiffness are much better. It needs a 120 C dryer and about $450 of filament.
     Brittle in the cold until T4c-PPA passes.
   - **(C) PPA-CF H1 as released:** not recommended (R1 0.94, inserts fail).
2. **If B:** print CA-1/3/4-PPA and T4c-PPA first, about one spool. Then the H1-P halves.
3. **Hip mount hardware change** (through-bolts + nuts for inserts): mount, face and positions unchanged. This
   applies to any PPA frame.

## FOUND, NOT FIXED
- BL-069's upper-half plate contact (223 mm2) does not match the released file: 163 mm2 on the `frame_h1_build` rule.
  It is the same for H1 and H1-P.
- The voxel-model concept checks used since BL-061 (`frame_iter1.build`) can over-credit thinning wherever the export
  re-adds exact features: the US1 lug-fix hulls, the D50 hip boss, the fairleads. `bl070_h1p.feature_mask` (scratch)
  marks them. Concepts should be checked on the export (RUBRIC 1), as here.
- H1-P's crown-held frame buckling mode moved to the stay top / upper bar in hipbelt-off abuse (3.72), after the
  upper bar was thinned. It is far above 1.15, but the next re-tune should not thin the upper bar further.
