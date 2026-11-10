# Printed-frame competition, Team A: MONO

Owner: structural-fea-engineer (team A), 2026-11-10. Rules: [frame_comp/RULES.md](../frame_comp/RULES.md). Research:
[docs/research/frame_comp_A.md](../../../docs/research/frame_comp_A.md). Code: `huntkit/gendesign/frame_comp_A.py`.
Results: [frame_comp/A/result.json](../frame_comp/A/result.json), full data
[frame_comp/A/frame_comp_A_results.json](../frame_comp/A/frame_comp_A_results.json), booked summary
[frame_comp/A/frame_comp_A_summary.json](../frame_comp/A/frame_comp_A_summary.json), body
`frame_comp/A/mono_body_assembled.stl`. Tests: `tests/test_frame_comp_A.py`. Standard: HA-LS-1 rev C
([load_standard.md](load_standard.md)).

## 0. Verdict (honest)

- **MONO passes HA-LS-1 rev C, but it is only about 20 g lighter than today.** Printed body **767 g** (today 823 g,
  -56 g), frame **1043 g** (today 1063 g), frame + spreader **1206 g** (today 1225 g). CORRIE B.2 at belt M:
  **3945 g (8.70 lb)**, against 3964.5 g today.
- The body saving is eaten by the **dry joint**. Today's z 234 splice uses carbon dowels bonded with MMA; the rules
  allow only dry assembly, so MONO uses four Ti M5 bolts in printed nut traps. Bosses, bolts and nuts add 36.5 g. If
  the owner kept today's bonded dowels, MONO would weigh 1007 g (-56 g).
- **Worst margins:** frame strength **1.12** (the unchanged crown legs; body strength 1.28), fatigue **1.046** (body,
  governs), joint **1.22** (dry splice, nut-trap bearing in fatigue), creep 2.23, body buckling 1.27 (branch).
- **Why a monolithic PAHT-CF body cannot go much lighter.** Fatigue governs at the stay below the sleeve. The sleeve
  limbs, which have to wrap the 18 mm crown bore, are about 40 % of the mass and already sit at the fatigue limit.
  The fully stressed loop drives every member family to the same utilisation. After that only the material data can
  move the result.
  - **Better material: no.** PPA-CF is 18 % denser, and its hot/wet and Z allowables are weak. PA6-CF is 10 %
    denser and loses strength wet. On today's geometry both are heavier (966 g and 904 g).
  - **Better orientation: no.** Today's face-down orientation (layer normal y) is already the only one that passes.
  - **Annealing: no credit.** The TDS values are already for annealed bars.
- **Upside if a coupon proves it.** If coupon CA-1 shows PAHT-CF holds 0.40 × UTS for 1e5 cycles (the Stratasys
  Nylon 12CF result), a body of about 686 g passes. That gives a frame of about 962 g and a pack of about 3864 g.
  This is **not** claimed here: the conservative published PA12-CF data (Siebert 2025) supports only about 0.29 ×
  UTS at 1e6 cycles.

## 1. Concept

The released branch body with the same topology and look: split sleeve limbs, inboard branches, lumbar X-struts into
the hip pivot, mid bar, upper bar with the pawl housing, and the eight fairleads. Each member family is re-sized
separately, so the shape reads the same and the members are thinner where the load is low (render
`outputs/screens/20261110_compA_1.png`).

| member family (radius scale; today 1.05) | MONO | change |
|---|---:|---|
| stay foot ball | 0.851 | -19 % (hinge-pin boss and boot floor) |
| stay below the sleeve (z < 160), the fatigue hot spot | **1.143** | **+9 %** |
| sleeve limb (outer, z 160-470); wall over the 18 mm bore | 0.991; 4.58 mm (4.41) | about the same |
| stay top, upper bar, pawl bulge | 0.995 | -5 % |
| inboard branches | 0.850 | -19 % (buckling floor, section 4) |
| lumbar struts | **1.112** | +6 % |
| mid bar | 0.770 | -27 % (r 5.0 mm floor) |

Interfaces unchanged: the crown and lifters, rack, pawl housing with its 304 bushing, the 18.0 mm reamed bores, the
spine channel, the hip-pivot boss (4 × M5 inserts, Ti mount), the eight fairleads (bag hard points, hinge pins, IM2 /
IM3, B-24 eyes), and the lumbar pan. All of these are passive, or are kept at the released size in
`frame_comp_A.body_sdf`. Sandwich v2 clips over the stays at z 166 / 260 / 400 sit where the radius is unchanged
(sleeve floor). The pucks on the thinner branches need re-printed seats (ASSUMPTION: the spreader result is
unchanged; re-run `spreader.evaluate` before release).

## 2. Method

- **Loads.** `rev_c_verification.beam_runs`: 9 cases with the bag couple on the crown bar, plus 5 with it on the
  IM3 hooks, at 15 / 19 / 23 in (42 factored sets). This is the same load path as every production check.
- **Body model.** 2 mm voxel FE (`frame_topopt`), hip pivot clamped, one PARDISO factorisation per geometry. The
  model is linear and isotropic and every load is applied, so the stress field does not depend on E: one solve serves
  every material.
- **Pass rule.** As `frame_cg_recheck.verify_sets`: layer failure index (in-plane von Mises / XY, normal / Z,
  interlayer shear / 0.6 Z, all × hot/wet), 99th percentile with clamp and load-patch elements excluded.
  - Fatigue: C1 at 1.6 g, compared with the fatigue ratio × the knocked-down strength.
  - Creep: C1 at 1 g, compared with the creep-rupture ratio.
- **Reproduction.** With every scale at 1.05 the code reproduces today's record: strength **1.508** (record 1.51),
  fatigue **1.040** (1.04), creep 2.219 (2.23), raster mass 819.4 g (record 823.2 g; MONO masses are booked as
  823.2 − Δ).
- **Fully stressed loop** (`fully_stressed`). Each member family gets the 99th percentile of max(strength FI, fatigue
  use) over its elements. Radii are updated as (u / T)^(1/3), step-limited to ±10 %, with size floors. The family
  target T is re-scaled every iteration so that the global rule lands at margin 1.03 (ASSUMPTION: a 3 % reserve for
  voxel / FI99 noise). Every iterate is re-verified on all 42 sets.
- **Solver checks.** The voxel solver matches closed forms in `tests/test_frame_topopt.py` (Timoshenko cantilever,
  Saint-Venant torsion, rod in parallel). `tests/test_frame_comp_A.py` re-checks a voxel cantilever against
  Euler-Bernoulli + shear (< 10 %), the FI per layer direction, the joint hand calculation, the resize rule, the mass
  bookkeeping, and that the parametric body equals today's SDF.

Loop history (PAHT-CF, record allowables; `outputs/screens/20261110_compA_4.png` panel a):

| iterate | body g (raster) | strength | fatigue | creep |
|---|---:|---:|---:|---:|
| it0 = today | 819.4 | 1.508 | 1.040 | 2.219 |
| it1 | 713.6 | 1.167 | 0.861 | 1.837 |
| it2 | 735.3 | 1.191 | 0.972 | 2.073 |
| it3 | 748.8 | 1.262 | 1.005 | 2.144 |
| it4 | 758.2 | 1.274 | 1.039 | 2.217 |
| it5 / it6 | 757.6 / 770.3 | 1.299 / 1.350 | 1.015 / 1.053 | 2.17 / 2.25 |
| **MONO** = it4 with the branch at 0.85 | **763.2** (booked **767.0**) | **1.278** | **1.046** | **2.232** |

## 3. Rev C checks (MONO, PAHT-CF, layer normal y)

Margin = SF / requirement; a check passes at ≥ 1.00.

| case | factor | couple on crown bar (torso, where) | couple on IM3 (torso) |
|---|---:|---|---|
| C1 static carry | 2.0 | 3.42 (15, stay below the sleeve) | 2.79 (23) |
| C2 stumble 2.0 g | 1.5 | 2.28 (15, stay below the sleeve) | 1.86 (23) |
| C3 side-hill | 1.5 | 2.22 (15, stay R below the sleeve) | 2.09 (23) |
| C4 set-down | 1.5 | 3.22 (23, upper bar) | 3.18 (23) |
| C5 meat straps | 1.5 | 2.19 (23, sleeve wall) | – |
| C6 tall load / C6p posts | 1.5 | 3.07 / 2.93 (15) | – |
| C7 overload | 1.0 | 3.07 (23, sleeve wall) | – |
| C8 hipbelt-off | 1.0 | **1.28** (15, upper bar / pawl housing) | 1.30 (15) |
| **fatigue** (C1 at 1.6 g, 1e5, 0.30) | | 1.28 | **1.046** (23, stay below the sleeve) |
| creep-rupture (C1 at 1 g, 40 C 8 h, 0.40) | | 2.74 | 2.23 |

| other check | margin | basis |
|---|---:|---|
| body member buckling, lower branch (Euler, K 1, E × 0.6 × 0.7, 1.5 × factored) | **1.27** (C4, 15) | `member_buckling`; at the 0.81 loop floor it was **0.97**, so the floor was raised to 0.85 (+5 g); today 1.50 |
| upper branch / mid bar buckling | 1.81 / 2.23 | same |
| dry z 234 joint, tension (2894 N, C2 IM3 23 in, per flange) | 2.17 | M5 nut-trap bearing 6.29 kN (washer 12 mm), bolt 6.39 kN, shear-out 13.5 kN |
| dry joint fatigue (1543 N at 1.6 g) | **1.22** | 0.30 × bearing 1.89 kN; bolt 0.30 × proof 1.92 kN |
| dry joint shear (580 N per stay) | 4.06 | 2 dry press-fit 5 mm carbon dowels, 60 MPa |
| split height | z 234 best | flange force 2894 / 3000 / 3218 N at z 234 / 262 / 290 |
| crown (unchanged, rev C): legs FPF / spine / corner bond peak / buckling | 1.12 / 1.18 / 1.22 / 1.85 | rev_c_verification.md |
| P-1 post socket bond peak (0.8 mm bondline) | 1.20 | frame_light2.md |
| pawl cheek (304 bushing), fairlead hinge cheek fatigue | 1.40, 1.67 | unchanged parts |
| hip pivot 4 × M5 inserts | 3.00 | unchanged boss (insert pull-out ASSUMPTION 1500 N, test pending) |
| spreader FPF / fatigue | 1.25 / 1.09 | unchanged; support re-check pending |

**Material and orientation on the MONO geometry** (same stress field; strength / fatigue / creep):

| material | body g | normal y (face on plate) | normal x (side on plate) | normal z (standing) |
|---|---:|---|---|---|
| PAHT-CF (design) | 763 | **1.28 / 1.05 / 2.23** | 0.71 / 0.98 / 2.09 | 1.01 / 0.57 / 1.21 |
| PAHT-CF, fatigue 0.40 (not credited) | 763 | 1.28 / 1.40 / 2.23 | | |
| PPA-CF (wet 0.73, Z 45) | 900 | 1.72 / 1.47 / 4.31 | 0.62 / 0.90 / 2.65 | 0.88 / 0.50 / 1.46 |
| PA6-CF (wet 0.75) | 842 | 1.40 / 1.15 / 2.45 | | |

Re-sizing loops started from MONO (3 iterations each, not converged; CPU budget):

| material | lightest passing iterate | next iterate (fails) | reading |
|---|---|---|---|
| PAHT-CF at fatigue 0.40 | 681.9 g raster (≈ **686 g** booked), S 1.11, F 1.13 | 617.6 g, F 0.94 | converged ≈ 650-680 g, *if* CA-1 proves 0.40; branch buckling not re-checked |
| PPA-CF | 790.7 g, S 1.41, F 1.10 | 705.7 g, F 0.88 | converged ≈ 740-760 g: no lighter than PAHT, and brittle across the layers (Z 0.9 %, 4.3 kJ/m²) |

## 4. Stiffness and look

| | today | MONO |
|---|---:|---:|
| torsion (±100 N at the stay tops, hip clamped), relative | 1.00 | **0.99** |
| stay-top aft deflection, C1 at 1 g, 19 in (voxel, 23 C) | 17.9 mm | 17.0 mm |
| deformed shape | | `outputs/screens/20261110_compA_3.png` |

The feel is the same as today's, including the softening in heat (PAHT-CF at 40 C wet is at 0.6 E). PPA-CF would be
3.0× as stiff (4.3× hot), the one real benefit of that material, at about +0 to +100 g and with brittle Z.
The look is unchanged: the same generative branch body. The branches and mid bar are slimmer, and the lower stays and
struts slightly fuller. The four bolt bosses at z 234 are not yet in the STL or the render; they are booked in the
mass.

## 5. Mass, print, cost, build

| item | g |
|---|---:|
| printed body (PAHT-CF, booked) | 767.0 |
| joint bosses (4 × Ø16 × 50 mm, 60 % outside the wall) | 25.6 |
| 4 Ti gr5 M5 × 50 + nuts, minus 4 of the 8 dowels and the MMA | +10.9 |
| crown (rev C fix), rack, pawl, bushings, Ti mount, inserts, 4 dowels (today's non-body parts) | 239.8 |
| **frame** | **1043.3** |
| Sandwich v2 spreader | 162.3 |
| **frame + spreader** | **1205.6** |
| CORRIE B.2, belt M | **3945.1 (8.70 lb)** |

- **Print:** H2S at home, 2 segments split at z 234, face down (as today). About 28.3 h at 8 mm³/s with 8 % waste.
  Settings as PRODUCTION.md: dry the spool 80 C 10-12 h, 0.6 mm hardened nozzle, 6 walls, 100 % infill on the limbs.
- **Cost per frame** (frame only; Sandwich v2 $207 and rails extra): **$291 / $224 / $193** at 1 / 10 / 100.
  - Includes filament + 15 % reprints, machine $1/h and bought parts from PRODUCTION.md.
  - Includes Ti bolts at an ASSUMPTION of $4.50 each.
  - Includes a $60 one-off coupon programme spread over the batch.
  - ASSUMPTION: 10 % and 25 % discounts on bought parts at 10 / 100 units.
- **Build (beginner, about 5 h hands-on; no adhesive in the body):**
  1. Print both segments.
  2. Anneal at 90 C for 6 h on a flat plate, with rods through the bores.
  3. Ream the bores to 18.0 mm and press in the pawl sleeve.
  4. Press the 4 carbon dowels dry into the reamed holes.
  5. Drop the M5 nuts into the side traps, insert the 4 Ti bolts and torque them to 1.5 N m.
  6. Heat-set the M5 inserts and fit the Ti mount.
  7. Fit the crown, rack and pawl as today.

  This is simpler than today: no flame treatment, no MMA and no 24 h clamp.

## 6. Patents

The design is unchanged in every respect the guardrails cover:
- Lifters stay on the crown top bar (US 10,952,523).
- The body is a printed branching lattice, not KUIU's one-piece slotted sheet (USRE48,093, US 9,095,203,
  US 9,636,875).
- There is no adhesive port and no tube joint (Divergent US 10,668,965, US 10,605,285 family).

This is not legal advice; get a freedom-to-operate opinion before tooling.

## 7. Assumptions and coupon tests

| ASSUMPTION | governs? | coupon |
|---|---|---|
| PAHT-CF fatigue at 1e5 = 0.30 × hot/wet strength (published PA12-CF: 0.25-0.32 × UTS at 1e6 Siebert 2025; 0.40 Stratasys) | **yes** (body, 1.046) | **CA-1**: 6 XY + 6 Z ISO 527-1A bars from the owner's H2S, annealed 90 C 6 h, conditioned 7 days at 50 % RH; 3 + 3 to UTS, then R 0.1, 5 Hz, max 0.30 × 0.8 × UTS for 1e5 cycles (pass: no failure, stiffness loss ≤ 10 %); repeat at 0.40 to earn the lighter body |
| hot/wet 0.8 on PAHT-CF strength; Z 47 MPa; interlayer shear 0.6 × Z | yes | **CA-3**: 3 Z bars + 3 short-beam-shear blocks after a 48 h 40 C water soak; pass Z ≥ 37.6 MPa |
| creep-rupture 8 h 40 C = 0.40 | no (2.23) | **CA-4**: 2 XY bars at 0.40 × 0.8 × UTS, 40 C oven, 8 h dead load |
| annealing: no extra credit | no | **CA-2**: 90 C vs 120 C, 3 XY + 3 Z bars each; credit only a measured gain |
| dry joint: nut-trap bearing at 0.8 × 88 MPa, fatigue 0.30 of it; stay bolts carry the whole side resultant at a 24 mm lever; branch faces in dry contact | **yes** (1.22) | **CA-5**: 3 printed z 234 stubs pulled to failure (mean ≥ 1.5 × 2894 N, lowest ≥ 1.25 ×); 1 cycled 0 → 1543 N × 1e5 on the T5 rig |
| branch Euler K = 1 with hot + creep E | yes (1.27) | frame test T4b (set-down) with a dial on the branch |
| beam-model load path unchanged by the body; crown, spreader and fairlead margins as rev C | | T9, T1-T5 |
| voxel / FI99 noise reserve 3 % (loop target 1.03) | | |
| size floors: branch and strut r ≥ 5 mm, foot ball ≥ 8.4 mm, sleeve wall ≥ 3.6 mm | | |
| spreader pucks re-seated on the slimmer branches, comfort and FPF unchanged | | re-run `spreader.evaluate` |

Then HA-LS-1 T9, T1-T5 and T4c at -20 C on the first MONO frame, with the pencil-mark check across z 234.

## 8. Owner decisions

1. Is about -20 g worth a new print file and a new joint? On mass alone, MONO hardly beats today. Its real gain is
   the dry, glue-free splice and the slightly higher body fatigue margin (1.046 against 1.040; C-9 sits at 1.020).
2. Run coupon CA-1 at 0.40 × UTS first. It is the only route by which a monolithic printed body gets clearly lighter
   (about -80 g more).
3. PPA-CF is not recommended. It is no lighter, it is brittle across the layers, and it needs a 120-140 C forced-air
   anneal. Its only gain is 3× the stiffness.

## Screenshots

- `outputs/screens/20261110_compA_1.png`: Cycles render, MONO (left) next to today's body (right), bag side.
- `outputs/screens/20261110_compA_2.png`: utilisation, today vs MONO, front and side.
- `outputs/screens/20261110_compA_3.png`: MONO deformed shape, C1 at 1 g, ×5.
- `outputs/screens/20261110_compA_4.png`: resizing loop, materials, layer orientation.
