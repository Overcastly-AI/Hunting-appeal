# BL-056 SLM Ti hip pivot mount base for the 8-insert pattern

structural-fea-engineer, 2026-11-21. Ticket `docs/backlog/BL-056-hip-mount.md` plus the orchestrator's two additions (US2 clevis at the CLEVIS-SHARE B bound; HB-6 / HB-6b test data). Code `huntkit/gendesign/hip_mount.py` (`python -m huntkit.gendesign.hip_mount --export`), `huntkit/gendesign/clevis_bl056.py`; tests `tests/test_hip_mount.py`, `tests/test_clevis_bl056.py`. Results `hip_mount_bl056.json`, `clevis_bl056.json`. Units mm, N, MPa, g (imperial in brackets). Supersedes the hip-insert row of `hipbelt_structural.md` section 4 (with `h1_closeout.md`) and the share-1.0 rows of `h1_rev5.md` section 3.

## Summary

- **Redrawn:** `designs/pack_5200/print/lug_hip_pivot_mount_slm_ti.stl` / `.3mf`: base D49.99 x 3 mm (1.97 x 0.118 in), 8 x D5.5 on the BL-055 positions (position error 0 mm), D10 pin hole; legs and hub kept (sections above the fillets identical to the drawn part: True); 1.2 mm 45 deg fillet round each leg root. One closed shell: True. The drawn part is kept as `print/legacy/lug_hip_pivot_mount_slm_ti_D44_drawn.stl` (h1_closeout reads it).
- **Clearances:** head-to-leg 5.23 mm (rule >= 1), head-to-head 0.69 mm, hole edge to rim 3.24 mm, hole to pin hole 11.25 mm; a D5 driver envelope straight above every head clears the part and the frame.
- **Frame fit (sliced):** boss face measured at y -48.55 (h1_closeout's -48.4 is a slice level 0.15 mm inside it); clash -0.0 mm3; 8 pilots under the 8 holes at face +1 / +6 / +10.5 (offset 0.00 mm); screw M5 x 14 tip 0.50 mm above the measured pilot floor (11.5 mm); full 9.5 mm insert engagement; base bears on the boss over its whole area. **Pass: True.**
- **Strength (part FE, bolt-only bound):** min SF / goal **1.80** on C2|H_pin at the **leg root** (p99.5 290.3 MPa, SF 2.7 / 1.5); the base itself 3.55 x its goal. Walk fatigue (as-built HIP, Goodman) leg root 2.09 / 1.15. **Sensitivity:** the same 20 mm pad offset put SIDEWAYS (not a fit-model case) bends the legs about their thin axis: min SF / goal 1.01 at the leg root (C2 / walk with H on the pin). The legs (kept from the drawing, as the ticket says) are the part's weak point; the 3 mm base is not.
- **BL-055 strip formula on the SLM allowables:** min SF / goal 3.25 (BL-055 3.27 on wrought allowables).
- **Mass:** 34.26 g (1.21 oz), drawn 20.17 g: +14.09 g against the +13.82 g BL-055 booked: ledger row BL056 +0.27 g.
- **US2 clevis (addition 1):** blocks grown upward only, pin +14.5 -> +19 mm, and the nut face moved 1 mm inboard (body plug 12 -> 13 mm, same M5 x 35); share 1.0 on every row: strength 3.02 (>= 1.5), fatigue 1.36 (>= 1.15) (was 1.90 / 0.86); legacy 2D rows 2.73 / 1.23 (was 2.52 / 1.14); print +8.3 g.
- **Tests for the kit (addition 2):** HB-6 pass line 513 N per insert (6 coupons, along the build z, 60 C); HB-6b screw-gauge pass lines in section 6.

## 1. Geometry

| check | value |
|---|---|
| base D eq (sliced at z 1.5) | 49.99 mm |
| base top (first slice off the disc) | 2.95 mm |
| holes (D eq) | 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 10 |
| hole position error vs h1_closeout.json | 0 mm |
| legs + hub kept (sections z 4.7..27 vs drawn) | True |
| hub top | 28.1 mm (pin stand-off unchanged) |
| head to leg (z 3..6.5, fillets incl.) | 5.23 mm |
| head to head | 0.69 mm |
| head inside the rim by | 1.74 mm |
| driver envelope clash | 0 mm3 |

## 2. Fit on the frame print

Frame `designs/pack_5200/print/frame_h1/h1_assembled.stl`; mount placed by `hip_mount.frame_matrix` (local z = frame -y, local y = frame z, ASSUMPTION MOUNT-ORIENT).

| slice | pilots | D eq | offset to the mount hole (mm) |
|---|---|---|---|
| face+1 | 8 | 6.39 | 0.0 |
| face+6 | 8 | 6.39 | 0.0 |
| face+10.5 | 8 | 6.39 | 0.0 |
| face+11 | 8 | 6.39 | 0.0 |

Clash mount / frame -0.00 mm3; screw shanks, heads and the driver envelopes: 0 / 0 / 0 mm3 in the frame. Tip depth 11 mm, pilot floor 11.5 mm.

## 3. Strength

Solver verification (`cantilever_check`, the same voxel H8 code): tip deflection FE / Timoshenko 0.980, bending stress 0.991.

Part FE: 61843 voxels of 0.5 mm (34.25 g), ti_6al_4v_slm (design yield 785, Su 850, as-built HIP fatigue 200 MPa R -1); BC bolt-only bound: head annuli clamped, no boss bearing (ASSUMPTION FE-BOLT-ONLY). Loads per h1_closeout hip row: V along the legs at the hub bore, H on the hub face with the pad offset e = +/-20 mm vertical (frame z, hipbelt E_PAD_MM) or 0, and V up and down (worst kept); the same offset sideways is the sensitivity below. Stress p99.5 per region (peak in brackets, voxel steps), elements under the clamped heads left out.

| row | kind | goal | base | leg root | legs | hub | min SF / goal |
|---|---|---|---|---|---|---|---|
| C2|H_pin | strength | 1.5 | 147.7 (233.3) SF 5.32 | 290.3 (348.3) SF 2.7 | 180.2 (215.8) SF 4.36 | 235.5 (326.1) SF 3.33 | 1.80 |
| C1|H_pin | strength | 1.5 | 98.5 (155.5) SF 7.97 | 193.6 (232.2) SF 4.06 | 120.2 (143.9) SF 6.53 | 157 (217.4) SF 5 | 2.71 |
| walk|H_pin | fatigue | 1.15 | 78.8 (124.4) SF 4.11 | 154.9 (185.8) SF 2.09 | 96.1 (115.1) SF 3.37 | 125.6 (173.9) SF 2.58 | 1.82 |
| carry|H_pin | creep | 1.5 | 49.2 (77.8) SF 15.95 | 96.8 (116.1) SF 8.11 | 60.1 (71.9) SF 13.07 | 78.5 (108.7) SF 10 | 5.41 |
| C2|H_frame | strength | 1.5 | 69.7 (116.9) SF 11.26 | 98.7 (117.6) SF 7.96 | 57.7 (65.3) SF 13.61 | 52.2 (87.3) SF 15.05 | 5.31 |
| C1|H_frame | strength | 1.5 | 46.5 (78) SF 16.88 | 65.8 (78.4) SF 11.93 | 38.5 (43.6) SF 20.41 | 34.8 (58.2) SF 22.57 | 7.95 |
| walk|H_frame | fatigue | 1.15 | 37.2 (62.4) SF 8.7 | 52.6 (62.7) SF 6.15 | 30.8 (34.8) SF 10.52 | 27.8 (46.6) SF 11.64 | 5.35 |
| carry|H_frame | creep | 1.5 | 23.2 (39) SF 33.76 | 32.9 (39.2) SF 23.87 | 19.2 (21.8) SF 40.81 | 17.4 (29.1) SF 45.13 | 15.91 |

Strip formula (BL-055) at the redrawn leg roots (half width 4.82 mm, arm 9.3 mm, strip 9.19 mm): min SF / goal 3.25.

Lateral-offset sensitivity (e = +/-20 mm along frame x; the fit model gives a vertical offset only):

| row | min SF (region) | goal | SF / goal |
|---|---|---|---|
| C2|H_pin | 1.51 (leg_root, 518.8 MPa) | 1.5 | 1.01 |
| C1|H_pin | 2.27 (leg_root, 345.9 MPa) | 1.5 | 1.51 |
| walk|H_pin | 1.17 (leg_root, 276.7 MPa) | 1.15 | 1.02 |
| carry|H_pin | 4.54 (leg_root, 172.9 MPa) | 1.5 | 3.03 |
| C2|H_frame | 7.96 (leg_root, 98.7 MPa) | 1.5 | 5.31 |
| C1|H_frame | 11.93 (leg_root, 65.8 MPa) | 1.5 | 7.95 |
| walk|H_frame | 6.15 (leg_root, 52.6 MPa) | 1.15 | 5.35 |
| carry|H_frame | 23.87 (leg_root, 32.9 MPa) | 1.5 | 15.91 |

Fillet sensitivity (on the lateral case): a 2.0 mm fillet (head-to-leg 4.36 mm, +0.3 g) leaves the leg-root p99.5 at 517 MPa (1.2 mm: 519): the root stress is the leg's own section bending, not the corner. Mesh: h 0.5 against the 1 % / 2 % cantilever check; an h 0.4 run was stopped for time (not done).

## 4. SLM print notes (for the print service)

| build direction | support area mm2 (45 deg rule) |
|---|---|
| +z | 71.3 |
| -z | 1650 |
| +x | 621.3 |
| -x | 620.4 |
| +y | 602.8 |
| -y | 603 |

**Chosen: +z (base on the plate).** base down on the plate: the 8 holes and the pin hole print as vertical round holes (no support, no drift), the base face is the datum face and is faced flat after the cut-off; the leg-root fillets are 45 deg; the supports left are under the hub's lower face between the legs (removed by hand, the hub face is not a bearing face). -z (hub down) puts the base's whole underside on supports; +/-x and +/-y lay the holes sideways (oval, supported bores).
- Material and process: Ti-6Al-4V (grade 5 powder) L-PBF, stress relief before removal from the plate, HIP 920 C / 100 MPa / 2 h (ASTM F3001), per `data/materials/metals/ti_6al_4v_slm.yaml`.
- Plate side: print the base on 2-3 mm of block supports (not fused flat to the plate), wire-cut off, face the base underside flat (0.05 mm) as the datum: it is the face that bears on the boss.
- Holes: 8 x D5.5 and D10 printed vertical, no support; ream the D10 pin bore to the pin fit (the drawn part's note); the D5.5 holes as printed (clearance), deburr.
- Supports to remove by hand: under the hub's lower face between the legs (not a bearing face).
- Do not machine or blast the leg roots beyond the vendor's standard bead blast (the fatigue check uses the as-built HIP limit).
- Inspect: base 3.0 +/- 0.1 mm, D50 +/- 0.2, 8 holes on the pattern (drill gauge from the boss), no crack at the leg roots (dye penetrant if the vendor offers it).

## 5. Mass

| item | g | source |
|---|---|---|
| drawn mount (D44 x 1.2) | 20.17 | STL volume x 4430 kg/m3 |
| BL-056 mount (D50 x 3, fillets) | 34.26 (1.21 oz) | STL volume x 4430 kg/m3 |
| delta | +14.09 | |
| booked by BL-055 | +13.82 | h1_closeout.mount_flange |
| **ledger BL056 (mount)** | **+0.27** | hip_mount_bl056.json mass |
| **ledger BL056 (print, US2 blocks)** | **+8.32** | clevis_bl056.json mass |

Mass reductions that keep the SF: the base is at 3.5 x its goal or more (part FE, bolt-only) and could thin to about 2.2 mm (sigma ~ 1/t^2: 3.0 -> 2.2 mm keeps >= 1.8 x) for about -3.5 g, but the prying model's rigid flange (FLANGE-RIGID) is the reason for 3 mm: hold it until HB-6b reads the screw; pocketing the base between the screw groups (above and below the legs, where no screw is) saves about 2 g with the same caveat. Not applied.

## 6. Test data for the kit (addition 2)

**HB-6 insert pull-out:** PAHT-CF block 30 x 30 x 20 mm printed flat with the H1 settings (BL-053 profile), the pilot D6.4 x 11.5 deep cut along the BUILD Z (layer normal), insert 7.1 OD x 9.5 set with the iron at the vendor temperature; 6 coupons; 60 C (140 F) for >= 2 h, pulled at 60 C in the chamber or within 60 s of removal; M5 bolt through a rigid steel bridge with a D14 clearance ring round the insert (ring reacts on the coupon face), pull at 5 mm/min to failure. **Pass: every coupon >= 513 N (115 lbf)** (1200 N (insert record) x hot 0.8 x layer-normal 0.534 (47 / 88 MPa) = the static design value the BL-055 pattern was sized on). Minimum for the 8-insert pattern to keep its goals: 488 N. between the 8-insert minimum (fatigue row: 1.15 x T_walk / 0.3) and the pass line: the pattern still passes but with no margin, report it; below the minimum: the 10-split pattern on the same D50 boss (BL-055 sweep fatigue 1.51) needs about 0.8 x the minimum; below that, stop and re-open the hip joint.

**HB-6b hip-mount proof:** frame lumbar hub clamped on the stays; mount screwed with 8 x M5 x 14 Ti DIN 7984 SNUG (0.3 N m, no preload: the prying model credits none), gauge zeroed after snugging; a repeat at the 2.5 N m service torque is recorded for information only (preload hides the prying); a dummy pin in the D10 hub; load V along frame -z through the pin at its 21 mm stand-off (no H: the H_frame rows, the inserts' governing case). Gauge: one 1 mm foil gauge on the shank of the most-loaded screw (the lower group, outermost: frame (+/-14.12, 107.29); the shank turned to D4.2 over 4 mm for the gauge, the same screw on the bench first: calibrate microstrain vs tension in a tensile rig 0-400 N).

| step | pin load V N (lbf) | model screw tension N | model microstrain | pass if <= |
|---|---|---|---|---|
| carry 1 g | 534 (120) | 80 | 52 | 60 |
| walk 1.6 g | 854 (192) | 127 | 84 | 96 |
| C2 proof | 1601 (360) | 239 | 157 | 180 |

at every step the measured screw microstrain <= the pass line (model x 1.15); after the C2 proof (hold 60 s): no screw loosened (torque marks), no insert moved (dial < 0.1 mm), no crack on the boss under a 10x loupe; then 1e5 cycles 0 -> walk step at <= 3 Hz, same checks. A reading above the pass line means the flange is not rigid (FLANGE-RIGID wrong): stop and re-run the prying model with the measured split. (Ti gr5 E 110000 MPa (ti_6al_4v_slm record E; gr5 bar 110-114 GPa), tensile gauge section D4.2 = 13.85 mm2 (shank turned down over 4 mm)). Published as JSON in `hip_mount_bl056.json` `tests`.

## 7. US2 clevis at the CLEVIS-SHARE B bound (addition 1)

Blocks (body and clevis): z pin -14.5 / +19 (was +/-14.5); nut face |x| 150 (was 151; trap 144.8-150): body plug 13 mm for the hole bearing (the M5 x 35 grip 29 + washer 1 + nut 4 + 1 still fits). Lower edge, strap lip (r 3), bolts (z pin +/- 7), trap shapes and head counterbores unchanged. Code: `h1_bedfit.BLOCK_UP_Z`, `ClevisJoint.nut_face / trap_x0`.

The legacy BL-050/051 row set (h1_lanes.lug_loads, the 2D cradle rows the 3D rows replaced) at share 1.0: strength 2.73, fatigue 1.23 (cradle, hole_paht); at 12 mm body plug it read 1.14 on hole bearing.

| share | all rows strength | all rows fatigue | net section strength / fatigue | worst fatigue row |
|---|---|---|---|---|
| 0.6 | 5.03 | 2.26 | 5.03 / 2.26 | cradle_lane_b50 (net_section_paht) |
| 1 | 3.02 | 1.36 | 3.02 / 1.36 | cradle_lane_b50 (net_section_paht) |

BL-053 at share 1.0: strength 1.90, fatigue 0.86 (cradle_lane_b50, net section); design rows 2.54 / 1.14. Share-1.0 pass (>= 1.5 / >= 1.15 on every row): **True**.

Trap walls min 2.3 mm (>= 2: True); joint slices pass True; bed: lower fits with brim True (spare [2.14, 3.61]), upper fits with brim True (spare [14.61, 23.88]); strap clearance US1 12.4 / US2 14.6 mm (>= 10: True; BL-053 12.4 / 14.6).
Counterbored heads (unchanged: |x| 179-182.5, z 135-149, below the 183 outer face) vs the free drapes: min -1.7 mm, the same as BL-053 (the heads did not move).
Strap wrap on the new print: US2 38.0 deg on the lip r 3.0; US1 0.0 deg.

CLEVIS-SHARE kit loads (JSON `clevis_bl056.json` `kit`):

| test | pull unit vector (R) | proof N (lbf) | cycle peak N, 1e5, R 0.1 | eye bears on | model min SF / fatigue at the share |
|---|---|---|---|---|---|
| A: CLEVIS-SHARE|us2_inboard | [-0.9322, 0.2825, -0.226] | 1103.9 (248) | 735.9 | inner (body) cheek: PTFE shim between the eye and the inner cheek's throat face | 5.03 / 2.26 (share 0.6) |
| B: CLEVIS-SHARE|us2_yz | [0.0, 0.9216, -0.3881] | 642.9 (145) | 428.6 | outer (clevis) cheek, PTFE shim between the eye and the outer cheek (share 1.0 case) | 3.02 / 1.36 (share 1) |

Gauge lines on the new print (US2 arm-root gauge, h1_rev5.gauge_values; pass if |microstrain| <= the line):

| test | pull unit vector (frame, R) | pin load N | microstrain | pass if abs <= | BL-053 line |
|---|---|---|---|---|---|
| MT-1cr|us2 | [-0.9322, 0.2825, -0.226] | 240 | -697 | 904 | 904.0 |
| MT-1cr|us2 | [-0.9322, 0.2825, -0.226] | 480 | -1395 | 1807 | 1808.0 |
| MT-1cr|us2 | [-0.9322, 0.2825, -0.226] | 720 | -2092 | 2711 | 2713.0 |
| MT-1cr|us2 | [-0.9322, 0.2825, -0.226] | 1103.9 | -3208 | 4156 | 4159.0 |
| CLEVIS-SHARE|us2_inboard | [-0.9322, 0.2825, -0.226] | 1103.9 | -3208 | 4156 | 4159.0 |
| CLEVIS-SHARE|us2_inboard | [-0.9322, 0.2825, -0.226] | 735.9 | -2139 | 2771 | 2773.0 |
| CLEVIS-SHARE|us2_yz | [0.0, 0.9216, -0.3881] | 642.9 | -2049 | 2679 | 2681.0 |
| CLEVIS-SHARE|us2_yz | [0.0, 0.9216, -0.3881] | 428.6 | -1366 | 1786 | 1787.0 |

Mass (PAHT-CF 1.06 g/cm3): assembled 1061.09 -> 1069.4 g (+8.32 g); clevis R 13.73 -> 15.71 g; lower half 490.22 -> 494.58 g. Ledger row BL056.

## 8. Assumptions

- ASSUMPTION MOUNT-ORIENT: Carried from BL-055: the mount's local y is frame z (legs above and below the pin). Settled by: First-article fit of the mount on the boss.
- ASSUMPTION FE-BOLT-ONLY: The part FE clamps only the screw-head annuli and gives no bearing on the boss: an upper bound on base and leg-root bending (the real base also bears on the boss on the compression side). Settled by: HB-6b screw gauge (if the screw reads below the model, the bound holds).
- ASSUMPTION FLANGE-RIGID: Carried from BL-055: the insert tensions come from the rigid-flange prying model; the 3 mm base is checked for its own bending with the bound above. Settled by: HB-6b.
- ASSUMPTION HEAD-LEG: >= 1 mm between a DIN 7984 head (D8.5) and a leg root (fillet included), for the driver. Settled by: First-article assembly with a 4 mm hex key.
- ASSUMPTION KEY-D: A 4 mm hex key / bit sweeps a D5 envelope straight above the head (checked clear of the part and the frame for 60-80 mm). Settled by: First-article assembly.
- ASSUMPTION SLM-FAT: Fatigue on the as-built HIP limit 200 MPa (R -1, 1e7) with Goodman on Su 850 for the 0 -> peak walk cycle; the base faces are not machined except the datum face. Settled by: Vendor coupon (ti_6al_4v_slm record note).
- ASSUMPTION SCREW-GAUGE: Screw tension from the strain on a D4.2 turned gauge section (13.85 mm2) and E 110 GPa, screws snug (no preload); calibrated on the bench before HB-6b. Settled by: Bench calibration of the gauged screw.
- ASSUMPTION CLEVIS-SHARE: Carried (BL-053): outer-cheek share 0.6, 1.0 as the bound; BL-056 makes the bound pass on every row. Settled by: CLEVIS-SHARE A and B (gauge lines here).
- ASSUMPTION BLOCK-UP: Growing the blocks upward adds no new strap contact: the strap wraps the lower lip only (strap_wrap re-run on the new print). Settled by: FIT-US on the re-printed us_route_stay_R piece.

## 9. Screenshots

- `outputs/screens/20261121_BL056_1.png`
- `outputs/screens/20261121_BL056_2.png`
- `outputs/screens/20261121_BL056_3.png`
- `outputs/screens/20261121_BL056_4.png`
