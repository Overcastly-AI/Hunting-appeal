# CA-1: PAHT-CF fatigue coupon and a DIY fatigue rig

Owner: structural-fea-engineer, 2026-11-10; release rule and IM3 eye coupon revised 2026-11-11 by BL-023
(manufacturing-engineer, from BL-014 B1 / B2). Frame: **H1** (`designs/pack_5200/analysis/frame_h1.md`).
Judge's order of tests: `analysis/frame_comp_verdict.md` §6. Units mm, N, MPa (imperial in brackets).

## 1. Why this test comes first

H1's body is sized by **fatigue**: C1 static carry at 1.6 g, 1e5 cycles, bag couple on the IM3 hooks, 23 in torso,
at the strut-to-stay junction and the lower sleeve wall. Every printed-frame margin rests on one unmeasured number,
`fatigue_1e5_ratio = 0.30` in `data/materials/polymers/pa12_cf_fdm_paht.yaml`. It is the 1e5-cycle maximum stress
divided by the hot/wet-knocked-down strength (0.8 × UTS), at R = 0.1.

- Published PA12-CF data disagree. FFF PA12-CF15 survived 1e6 cycles at about 0.25–0.32 × UTS (Siebert et al.,
  TU Sofia 2025, [paper][sofia]). Stratasys FDM Nylon 12CF had 3/3 run-outs to 1e6 at 0.40 × UTS, R 0.1, in-plane
  and across the layers ([white paper][ss-fat]). Neither is Bambu PAHT-CF from the owner's H2S.
- **Flip points on the adopted bases** (flip = 0.30 / fatigue margin at 0.30; the lowest governs):

  | part | fatigue margin at 0.30 | flip point | source |
  |---|---:|---:|---|
  | H1 body, per-torso basis (BL-017) | 1.150 (1.144 with BL-004 loads) | 0.261 (0.262) | `crown_diet_results.json` body.h1; `review_20261111.md` B1 |
  | **IM3 fairlead eye, 27 mm cheek** (BL-010 A1-CF, 15 in, 1.6 × 552.4 N) | **1.036** | **0.290** | `loadpath_verification.md` §4.1; `review_20261111.md` R3 |
  | z 234 joint | 1.22 | 0.246 | `frame_h1.md` §3 (CA-5 tests the joint itself) |
  | **governing** | | **0.290** | IM3 eye |

  The earlier rule on the H1 body alone (margin 1.28 on the recorded basis) is superseded: it would release an H1
  whose IM3 eye is below 1.0 in fatigue (BL-014 B1).
- **Release rule: H1 is released only if the measured ratio ≥ the governing flip point + 0.02 = 0.310.**
  `FLIP_GOV = 0.290` and `RELEASE = 0.310` are **placeholders until BL-021** (IM3 eye and body re-checked on the
  cloth-sim forces, target fatigue ≥ 1.15) sets the final flip point; replace both numbers here, in `TEST_PLAN.md` and in
  `test_register.csv` when it lands. With BL-021's target of 1.15 on every part, the flip would be 0.261 and the
  release level 0.281.
- The record's assumed 0.30 is **below** today's release level: on today's design H1 needs a material better than the
  record, or BL-021's re-size, before it prints.
- The OD 17 legs (BL-017 c17) and the fixed-torso variants (BL-007) have no per-torso flip point yet (BL-014 S3); they
  are not released by this test until the structural-fea-engineer states one.
- At 0.40 the body margin becomes 1.150 × 0.40 / 0.30 = **1.53** and the IM3 eye 1.38, and the body can be re-sized
  lighter (§6).

## 2. Coupons

Print every coupon in the same job as a frame half where possible, from the same dried spool and the same profile as
`designs/pack_5200/print/frame_h1/README.md` (0.6 mm hardened nozzle, 290 °C, bed 100 °C, 0.20 mm layers, 6 walls,
6 top/bottom, 100 % infill, part cooling ≤ 30 %, seam on one face).

| coupon | count | printed | geometry (mm) | why |
|---|---:|---|---|---|
| **XY bar** | 12 | **flat, face down, like the frame** (layer normal = coupon thickness = frame y) | dog-bone: 170 long, tabs 20 wide × 35 long, gauge 10.0 wide × 4.0 thick × 60 parallel, R 30 fillets | the frame's stays and bars carry bending along the layers. A 10 × 4 gauge with 6 walls is all perimeter, like the 10–14 mm H1 members. |
| **Z bar** | 4 | standing (gauge axis along the build = layer normal) | 100 long, tabs 20 × 25, gauge 10 × 6 × 30, R 20 | interlayer term of the failure index |
| spare | 2 + 1 | as above | | replace a coupon that breaks in the grip |

- **Orientation check.** On the plate, the XY bar's 4 mm thickness must be the print height (it lies on its 10 mm face).
  The frame lies wearer face down, so its member thickness is also along the print height.
- **Anneal and condition** exactly like the frame: 90 °C for 6 h on a flat plate, cool in the oven, then 7 days at
  23 °C and about 50 % RH. ASSUMPTION: a sealed box with saturated magnesium nitrate solution gives about 53 % RH.
- Measure the gauge width and thickness of each bar with calipers at 3 points. Use the smallest area.
- ASSUMPTION: filament for 18 bars is about 180 g, about $15 (PAHT-CF at $80/kg, `frame_comp_A.MATS`).

## 3. Load levels

`S = ratio × 0.8 × UTS_meas`, R = 0.1 (S_min = 0.1 S). UTS_meas is the mean of 3 static XY bars from the same batch,
capped at the 88 MPa TDS value used in the analysis. Nominal values at the 40 mm² XY gauge:

| level | XY S_max MPa (ksi) | XY F_max N (lbf) | F_min N | link force (÷ 4) N | Z S_max (47 MPa basis) | Z F_max at 60 mm² |
|---|---:|---:|---:|---:|---:|---:|
| 0.30 | 21.1 (3.06) | 845 (190) | 84 | 211 | 11.3 MPa | 677 N |
| 0.40 | 28.2 (4.09) | 1126 (253) | 113 | 282 | (not needed) | |
| static UTS | 88 (12.8) | ≈ 3520 (791) | | ≈ 880 | 47 MPa | ≈ 2820 N |

## 4. The rig: motor, eccentric, spring and lever (about one weekend to build)

```
                 load cell (S-type, 100 kg) in the drive link
   motor + crank ──► rod ──► [spring cage] ──► [LC] ──► lever end (480 mm from pivot)
   (eccentric e)                                           │
                                                           │  lever 6061 40 x 10 x 600 flat bar
   pivot (M8 shoulder bolt, 2 x 608 bearings) ●────────────┴──────────────────
                                                │ 120 mm
                                          upper grip
                                          [coupon]      ratio 480 / 120 = 4
                                          lower grip ── turnbuckle ── base (18 mm plywood on a 2x4 frame)
   AS5600 magnet + encoder on the pivot: lever angle -> coupon stretch
   hall sensor + magnet on the crank: one count per cycle
```

- **Load control by a soft spring.** The spring (about 10–12 N/mm) is about 15 times softer than the coupon seen at
  the lever end (E 3860 × 40 / 60 / 16 ≈ 160 N/mm). If the coupon creeps or cracks, the force barely changes, so
  this is a constant-load test, as the standard asks.
- **Setting the levels.**
  - The link force swings by k × 2e. For 0.30: 211 − 21 = 190 N gives e ≈ 8–10 mm on a 10–12 N/mm spring.
  - The turnbuckle sets F_min. Use a slotted crank disc so e is adjustable from 5 to 15 mm.
  - Peak motor torque is about F × e = 282 N × 12 mm ≈ 3.4 N m, well inside an 8 N m worm-gear motor.
- **Speed.** A 60 rpm motor gives 1 Hz, so 1e5 cycles take **27.8 h**. One coupon per day and night. PAHT-CF at
  21–28 MPa and 1 Hz does not self-heat measurably (ASSUMPTION; touch-check the gauge, it must stay below 30 °C).
- **Grips.** Two aluminium plates per grip, M6 bolts, 120-grit cloth on the faces, 35 mm of tab clamped. The grip
  pins sit in line with the coupon axis (rod ends at both ends, so no bending).
- **Lever check.** 6061-T6 40 × 10 mm on edge: at the static UTS pull (880 N at 480 mm) the bending stress is
  158 MPa < 276 MPa yield. At the 0.40 fatigue level it is 51 MPa, below the aluminium endurance limit (ASSUMPTION,
  96 MPa at 5e8 for 6061-T6, MMPDS-class value).
- **Electronics.**
  - Arduino Nano Every with an HX711 at 80 samples/s (RATE pin high) reads the peak and valley of the link force
    each cycle.
  - The AS5600 gives the coupon stretch (lever angle × 120 mm) at each peak.
  - A hall sensor counts cycles.
  - A MOSFET module switches the motor off on a stop condition.
  - Log every 100 cycles over USB to a laptop (a CSV of cycles, F_max, F_min, stretch and stiffness).
  - Stop rules: the coupon breaks, the stiffness drops by more than 10 % from the value at cycle 1000, or F_max
    drifts more than ±5 %.
- **Calibration** (before each level): hang a 20.0 kg water jug (196 N) in place of the coupon. The load cell
  should read 196 / 4 = 49 N. Fix the lever ratio from the reading, not from the drawing.

## 5. Parts list (quantity 1)

| part | spec | price USD | source |
|---|---|---:|---|
| S-type load cell | 100 kg, tension/compression | 23.60 | [Makerfabs][lc] |
| load-cell amplifier | SparkFun HX711 | 11.50 | [SparkFun][hx] |
| microcontroller | Arduino Nano Every | ≈ 17 (€14.50) | [Arduino Store][nano] |
| gear motor | 12 V 60 W 60 rpm 8 N m worm gear (uxcell) | 54.99 | [eBay listing][motor] |
| 12 V 10 A power supply | | 20 | ASSUMPTION |
| MOSFET motor switch module, hall sensor + magnets, AS5600 encoder board | | 15 | ASSUMPTION |
| 6061-T6 flat bar 40 × 10 × 600 | lever | 18 | ASSUMPTION |
| 2 × 608 bearings, M8 shoulder bolt, 2 × M8 rod ends, M8 rod 300 | pivot and links | 25 | ASSUMPTION |
| compression spring ≈ 10–12 N/mm, ≥ 350 N, with a 2-washer cage | load-control spring | 10 | ASSUMPTION |
| turnbuckle M8, aluminium grip plates (4 × 50 × 40 × 6), M6 bolts | grips, F_min | 20 | ASSUMPTION |
| plywood 18 mm + 2x4, screws | base and upright | 20 | ASSUMPTION |
| PAHT-CF for 18 coupons + 2 grip spacers | 0.2 kg | 15 | `frame_comp_A.MATS` $80/kg |
| **total** | | **≈ 250** | the judge's estimate was $250 |

The cited items total $107. The rest are ASSUMPTION shop prices; check them at purchase.

## 6. Procedure, pass/fail and what each result unlocks

1. **Static, same batch.** Pull 3 XY bars and 2 Z bars to failure: put the turnbuckle in place of the spring and turn
   it slowly, about 1 turn every 10 s. Record the peak link force × 4 / area. UTS_meas = mean.
   - Pass: XY ≥ 0.9 × 88 MPa and Z ≥ 0.9 × 47 MPa.
   - Otherwise stop and report: the analysis allowables are too high for this printer and spool.
2. **Release level (0.310, placeholder).** 3 XY bars at S_max = 0.310 × 0.8 × UTS_meas, R 0.1, 1 Hz, to 1e5
   cycles. Then 2 Z bars at 0.310 × 0.8 × UTS_Z. (Use the release level in force when you start: BL-021 may lower it.)
3. **0.40 level** (only if every release-level bar passed). 3 XY bars at 0.40 × 0.8 × UTS_meas.
4. After each run-out, look at the gauge and the fillets with a 10× loupe. Pull the run-out bar to failure: a
   residual strength of at least 0.9 × UTS_meas confirms that no damage was hidden.

| outcome | rule | what it unlocks |
|---|---|---|
| **pass at the release level (0.310)** | 3/3 run-outs to 1e5, stiffness loss ≤ 10 %, no crack | The H1 print files are released as designed, **together with IM3-EC (§6a) and CA-5**. Governing margin ≥ 0.310 / 0.290 = 1.07 at the IM3 eye. |
| **pass at 0.40** | as above at 0.40 | Credit 0.40 in `pa12_cf_fdm_paht.yaml` and re-run `frame_h1.push` with the higher ratio. Team A's estimate is a **≈ 686 g body** (about −72 g vs H1, frame ≈ 953 g), unconverged and without a buckling re-check. The A floors and the branch buckling rule then govern, so expect 690–710 g. Re-check the joint, which does not get lighter. |
| 2/3 at a level | | inconclusive: test 3 more. A level passes only with ≥ 5/6 run-outs. |
| fail at the release level | find the level by testing 3 bars at 0.27, then 0.25 | **H1 is not released.** Credit the measured ratio in the record; BL-021 re-sizes the IM3 cheek (first: it governs) and, below 0.281, the body. Sizing the cheek to fatigue about 1.25 costs about 1-3 g a pair (BL-014 B2, `loadpath_check.FROZEN`). |
| ratio below the body flip (0.261) | | the body fails fatigue as well. Re-run `frame_h1.push` with the measured ratio; the body grows (about +20 g for each −0.02 of ratio, ASSUMPTION from the push history). |
| Z fails at 0.30 | | the interlayer term governs locally: run CA-3 first and re-check the boss bending (B-style, across the layers). |

## 6a. IM3-EC: IM3 eye cycle coupons (BL-023, from BL-014 B2 (d))

The IM3 fairlead eye governs the release (fatigue 1.036 at the 27 mm cheek, 15 in). One coupon at the demand × 1.00
(BL-010's 0 → 812 N) cannot show a margin above 1.0, so the coupon count and load are raised:

- **Specimens: 3** eye coupons. A 120 mm stay segment round z 520 with the IM3 eye and the 27 mm cheek, cut from the
  H1 STL, printed in the same job, spool and profile as the CA-1 bars, annealed and conditioned with them.
- **Load: ≥ 1.15 × 884 N = 1017 N** (884 N = 1.6 g × 552.4 N, the CORRIE F 15 in cloth-sim IM3 force,
  `loadpath_verification.md` §4.1). R 0.1 like the bars: 102 → 1017 N, 1 Hz, 1e5 cycles. The force goes in through a
  sewn T3 tongue and the IM3 carabiner on the eye, the coupon clamped by its stay ends; 1017 N is 104 kg at the eye,
  about 26 kg at the 100 kg cell through the 4:1 lever.
- Loupe check every 25,000 cycles. After the run-out, pull each coupon to 2553 N (IM3-EP's proof) on the pull bench.
- **Pass:** 3/3 run-outs, no crack at 10×, and each holds 2553 N with no crack. **Fail:** the cheek grows (BL-021)
  and the coupons are re-printed at the new size. If BL-021 changes the force or the cheek, the load and geometry
  here follow it.
- The same coupons carry the throat check: two carabiner rods side by side, each ≤ 8.5 mm (ASSUMPTION,
  `loadpath_verification.md` §4.1).
- Machine time 3 × 27.8 h. Run them after the release-level CA-1 bars, on the same rig.

## 7. Order after CA-1: IM3-EC, CA-5, then CA-3, then CA-4

All five use the same rig, so build it once.

1. **CA-5, dry z 234 joint stubs** (next, because it now governs H1; see `frame_h1.md` §3).
   - Print 4 stub pairs: one stay, 60 mm each side of z 234, with the H1 bosses, traps and bolts. Use the same
     settings and anneal as the frame.
   - Pull 3 to failure with the turnbuckle. Pass: mean ≥ 1.5 × the worst factored bolt force (2933 N per
     bolt, prying included, `frame_h1_results.json`) and the lowest ≥ 1.25 ×.
   - 1.5 × 2933 N = 4.4 kN at the stub is above the 3.9 kN that the 100 kg cell reads through the 4:1 lever. Fit a
     200 kg S-type cell for the CA-5 static pulls (about +$25, ASSUMPTION), or pull through a 6:1 lever hole.
   - Cycle 1 at the 1.6 g static-carry stub force for 1e5 cycles. Pass: no crack at the boss root and a joint step of
     ≤ 0.1 mm under a dial gauge.
   - The stub force is applied as an eccentric pull, the moment-dominated case: pull through a clevis offset by the
     contact-model lever. The offset is recorded in `frame_h1_results.json` (joint section).
   - CA-5 checks the prying factor 1.25 and the boss-bending cantilever, both ASSUMPTIONS.
2. **CA-3, interlayer.** Soak 3 Z bars and 3 short-beam-shear blocks (24 × 8 × 6 mm, span 5 × thickness) in 40 °C
   water for 48 h. Test statically on the rig with a 3-point fixture under the lever.
   - Pass: Z ≥ 0.8 × 47 = 37.6 MPa, and interlayer shear ≥ 0.6 × 37.6 = 22.6 MPa.
   - It feeds the FI interlayer term and the boss plug shear-out.
3. **CA-4, creep-rupture.** 2 XY bars at 0.40 × 0.8 × UTS_meas as a dead load (weights on the lever end: 282 N /
   9.81 ≈ 29 kg at the 4:1 ratio). Put them in a 40 °C box (a cooler with a 60 W heater and a thermostat), 8 h.
   - Pass: no rupture. Record the creep strain from the AS5600.
   - Creep margins are 2.2–2.7, so this is the cheapest to close and the least likely to change anything.
4. Then the first article: HA-LS-1 T9, T1–T5, T4b with a dial on the branch, T4c at −20 °C, and pencil marks across
   z 234.

## Assumptions

- ASSUMPTION: a test at room temperature on conditioned bars, with the 0.8 hot/wet knockdown applied to the load
  level, represents the 40 °C wet allowable. This is the same convention as the record. A 40 °C chamber run of one
  0.30 bar is optional confirmation.
- ASSUMPTION: 1 Hz gives the same life as the 5–10 Hz of the published tests. Low frequency is, if anything,
  conservative for polymers because of creep–fatigue interaction.
- ASSUMPTION: shop prices for uncited parts (§5).

[sofia]: https://e-university.tu-sofia.bg/e-conf/files/169/paper_10.47978@TUS.2025.76.03.004.pdf
[ss-fat]: https://cdn.goengineer.com/fatigue-behavior-select-stratasys-fdm-materials-whitepaper.pdf
[lc]: https://www.makerfabs.com/s-type-load-cell-100kg-200kg-300kg-500kg-1.html
[hx]: https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html
[nano]: https://store.arduino.cc/products/arduino-nano-every
[motor]: https://www.ebay.com/itm/266938738081
