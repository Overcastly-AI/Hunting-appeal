# Frame competition, team C: ROD (printed clamshells on stock carbon tubes, no adhesive)

Owner: structural-fea-engineer (team C), 2026-11-10. Rules: [RULES.md](../frame_comp/RULES.md). Research: [docs/research/frame_comp_C.md](../../../docs/research/frame_comp_C.md). Code: `huntkit/gendesign/frame_comp_C.py`. Tests: `tests/test_frame_comp_C.py` (12 pass). Results: [`frame_comp/C/result.json`](../frame_comp/C/result.json), detail [`frame_comp/C/rod_results.json`](../frame_comp/C/rod_results.json).

```
python -m huntkit.gendesign.frame_comp_C      # 4 candidates x 42 solves, about 2 min on 2 cores
```

## Summary

| | ROD | today |
|---|---:|---:|
| frame g | **948** | 1063 |
| frame + spreader g | **1110** | 1225 |
| CORRIE B.2 pack at belt M, g | **3849** (8.49 lb) | 3964.5 |
| passes HA-LS-1 rev C (all cases, 15 / 19 / 23 in, both couple variants) | **yes** | yes |
| worst strength margin | 1.12, crown legs (unchanged part), hipbelt_off_abuse, 23 in, IM3 | 1.12 (crown legs) |
| worst joint margin | 1.12, upper bar pin bearing on the CFRP wall, side_hill_torsion, 15 in | 1.20 (post socket) |
| worst fatigue margin | 1.14, lumbar pan (beam-model plate) | 1.04 (printed body) |
| worst creep-rupture margin | 1.74, cap washer under preload | 2.23 |
| torsion stiffness | 2.70 N m/deg (6.1 x today) | 0.44 |
| print time (H2S) | 12.6 h, 13 pieces | about 27 h |
| cost 1 / 10 / 100 frames | $477 / $340 / $321 | about $427 incl. spreader |

**Verdict:** ROD passes rev C with no adhesive in the frame load path and saves **115 g** over today. It is still 146 g heavier than the rejected TENDON (bonds plus wet tendon wraps): fasteners (88 g) and the full-perimeter clamshells cost more than glue. Every margin above depends on ASSUMPTIONS A1 to A8 and has a coupon test (section 6). The governing joint, bar-pin bearing, breaks even at 214 MPa design bearing (268 MPa ultimate).

## 1. Concept

ASSUMPTION: the beam topology is the v2 tube ladder (`huntkit.fea.pack5200`, as in frame_light2): two straight stays, a mid bar at z 330, an upper bar at z 520 (pawl), the lumbar plate z 50-190, the Ti pivot at z 120, and the carbon crown with the rev C fix.

| part (per side unless noted) | what it is | load path |
|---|---|---|
| stays (2) | Rock West 46710, 20 x 18, stock, 530 mm | long-member bending and axial |
| mid bar | Rock West 46710, 180 mm | bar ends in 55 mm sockets |
| upper bar | custom OD 22 RW45 k5, 180 mm (stock 20 x 18 fails, 0.81) | as above, carries the pawl |
| foot-saddle z 0-205 | printed body + cap. Boot with a 20 x 1.5 Al end disc, foot pin M4 at z 20, hinge-pin boss z 60, US pins, z 80 / 110 / 190 hard points, 5 pan tabs | stay end bears on the disc (compression); the foot pin takes uplift and torque; pan by M4 bearing |
| mid knuckle z 205-355 | printed body + cap. Spliced to the saddle at z 205 (2 x M4), z 250 lash, IM2 seat, bar socket | the rail carries the knuckle's axial share down to the foot. **No hole in the stay here** (the crown leg telescopes inside) |
| upper knuckle z 410-530 | printed body + cap. Stay-top bushing collar, z 420 lash, IM3 and B-24 eyes, bar socket | two 3 mm Ti radial pins at z 525 through ONE wall each, flush with the bore, engaging the top bushing |
| bar ends | 55 mm socket channel, M4 Ti pin along y, 12 mm from the bar tip (e/d 3) | bending by the contact couple; axial and torque by the pin |
| caps | 3-5 M3 Ti bolts, penny washers, Belleville pair | keep the channels closed. **No friction credit** |
| lumbar pan | flat 1.5 mm QI CF sheet 250 x 140, cut and drilled | 5 x M4 per side into the saddle tabs |
| hip node | printed, 4 x M5 heat-set inserts (fixed interface), 4 x M4 through the pan | |

Generative look: the long sleeves are 50 % windowed (organic staggered windows), so the carbon shows through the printed bone, with root fingers from each socket onto the sleeve. **Honest read of screenshot 1:** next to today's branching body, ROD reads as a carbon ladder with perforated printed sleeves, not as a generative printed frame. `looks_generative` is therefore false. The silhouette is set by the straight tubes. Only the nodes can carry the organic language.

## 2. Load cases and method

- HA-LS-1 rev C `ls1_envelope("C")`: 9 cases with the couple on the crown bar (C6p on the posts model) plus 5 bag cases with the couple on IM3, at torsos 15 / 19 / 23 in (42 solves per candidate).
- Each bar end is split into a printed PAHT neck member (stay axis to the bar tip, 25 mm, annulus t 4 mm; ASSUMPTION A7). The neck's compliance and stress come out of the solve.
- Solver verification (`tests/test_frame_comp_C.py`) on the Rock West section: cantilever deflection, Euler buckling of a 530 mm stay, thin-wall torsion (all within 2 %); socket contact equilibrium against the closed form 4V/L + 6M/L^2.
- Margin = SF / case factor. Buckling / (1.5 x factor). Fatigue at 1e5 x 0 -> 1.6 g from the C1 solve: CFRP FI <= 0.5; PAHT <= 0.3 x allowable; bearing CFRP 0.5 x static (ASSUMPTION A4). Creep-rupture: 0.4 x the PAHT SF at 1 g (record ratio).

Joint checks (all bearing or interlock):

| check | formula | allowable |
|---|---|---|
| bar pin, CFRP wall bearing | F_w = hypot(N/2, T/d_m) per wall, sigma = F_w / (d t) | 240 MPa (A1) |
| bar pin shear-out | F_w / (2 (e - d/2) t) | 62.5 x 0.8 MPa (Rock West published shear) |
| bar net section at the pin | hole-edge running loads from the full moment vector at the pin (moment decayed by the linear socket contact), both signs, Tsai-Wu FPF (knocked down) x 0.55 | (A2) |
| socket and sleeve contact | q = 4V/L + 6M/L^2 over OD | PAHT Z 47 x 0.8 |
| radial stay pins | as the bar pin, one wall each | 240 MPa; net section 3 mm hole x 0.55 |
| PAHT pin bosses | F / (d x 6 mm) | XY 88 x 0.8 (A3) |
| cap bolts | (preload 600 N + transverse node force / n) on Ti M3 and on the washer in Z | Ti yield 880, PAHT Z |
| rail compatibility | E_paht x stay curvature x rail radius x Kt 1.5 | PAHT XY |
| foot | stay force from above the rail on the Al disc (PAHT Z over 314 mm2) and on the foot pin | |
| pan, hip | M4 bearing in QI (record 500 x 0.8) and printed tabs 9 mm | |

## 3. Results

Worst margin per case (worst torso, check and couple variant):

| case | crown bar | IM3 couple |
|---|---:|---:|
| C1 static_carry | 1.82 | 1.83 |
| C2 drop_2p5g | 1.21 | 1.22 |
| C3 side_hill_torsion | 1.12 | 1.12 |
| C4 single_stay_setdown | 2.49 | 2.49 |
| C5 meat_straps | 1.24 | - |
| C6 tall_load | 1.38 | - |
| C6p tall_load_posts | 1.20 | - |
| C7 overload_haul | 1.74 | - |
| C8 hipbelt_off_abuse | 1.13 | 1.12 |

Lowest checks (all pass):

| margin | check | where |
|---:|---|---|
| 1.12 | crown legs FPF (unchanged part) | hipbelt_off_abuse, 23 in, IM3 |
| 1.12 | bar pin, CFRP wall bearing (upper bar) | side_hill_torsion, 15 in |
| 1.13 | upper bar member FPF | hipbelt_off_abuse, 15 in |
| 1.14 | fatigue, lumbar pan | 15 in |
| 1.17 | bar pin shear-out | side_hill_torsion, 15 in |
| 1.18 | fatigue, stays | 23 in, IM3 |
| 1.21 | stay stub net section at the radial pins | hipbelt_off_abuse, 15 in, IM3 |
| 1.22 | fatigue, pan bolt in the saddle tab | 23 in, IM3 |
| 1.24 | stays FPF | meat_straps, 23 in |
| 1.43 | fatigue, printed rail compatibility strain | 23 in, IM3 |
| 1.74 | creep-rupture, cap washer under preload | |
| 1.82 | frame buckling | side_hill_torsion, 15 in |
| 2.35 | printed neck | side_hill_torsion, 15 in |
| 2.36 | bar net section at the pin | side_hill_torsion, 15 in |
| 2.43 | foot pin | side_hill_torsion, 15 in |

The full table is in `rod_results.json` and screenshot 3.

Candidates tried (upper bar):

| upper bar | worst | pass | frame g |
|---|---|---|---:|
| **custom OD 22 RW45 k5** | 1.12 | **yes** | 948 |
| stock Rock West 20 x 18 | 0.81 (upper bar FPF) | no | 941 |
| custom OD 20 RW45 k5 | 0.96 | no | 943 |
| custom OD 22 RW45 k4 | 0.94 | no | 945 |

Design iterations that were found and fixed (recorded for the reviewer):
1. Cross pins through the stays at the knuckles were the first idea. The net section failed (0.45 in side-hill), and the telescoping crown leg occupies the bore. The fix was to move the axial path down the printed rail to the foot and to use radial single-wall pins above the upper hub.
2. A 40 mm socket put the pin at 22 % of the mouth moment. A 55 mm socket puts it at 12 %.

## 4. Mass by load-path member (g)

| member | g |
|---|---:|
| stays (2), Rock West 91 g/m | 96.4 |
| mid bar | 16.4 |
| upper bar (custom) | 19.5 |
| mid knuckles (2 x 57.9) | 115.8 |
| upper knuckles (2 x 57.4) | 114.8 |
| foot-saddles (2 x 53.0) | 106.0 |
| hip node | 22.1 |
| Ti pins, M3 / M4 sets, Belleville pairs, Al discs (56 sets) | 87.6 |
| flat QI pan 1.5 mm + pad-up | 93.9 |
| crown + torso adjust (unchanged) | 250.0 |
| Ti pivot mount + inserts (unchanged) | 25.0 |
| **frame** | **947.6** |
| Sandwich v2 spreader (unchanged) | 162.3 |

ASSUMPTION: the printed volumes are estimated from shell geometry (2.4 mm wall, 50 % windows on the long sleeves, +25 % fillets and fingers, bosses 10 x 10 x 8 mm per bolt). A CAD body will move them by +/-15 %.

Mass reductions that keep the margins (not applied):
- Fewer M3 cap bolts: cap pull-off margin is >= 2.0 with 3 bolts. Moving the cap to a snap hinge plus 1 bolt saves about 15 g. Needs RC-4.
- Window the knuckles near the hubs (now solid): socket and sleeve contact margins are > 3. About -20 g. Needs RC-4.
- Pan bolts down to 3 per side fails pan-tab fatigue (0.73). Keep 5.
- No margin is left to thin the tubes (stays FPF 1.24, fatigue 1.18; upper bar 1.13).

## 5. Build (owner, home H2S)

1. Order one Rock West 46710 (2 m) and the custom upper bar. Cut with a diamond disc. Weigh, and run RC-1.
2. Print 13 pieces flat (wearer face on the plate), PAHT-CF as PRODUCTION.md, 100 % infill in the bosses. Anneal.
3. Drill through the printed drill jig: bar ends (4.0, reamed H8, 12 mm from the tip), radial stay holes (3.0, one wall, depth stop) at z 525, foot holes at z 20. Use a carbide drill, wet, with a mask.
4. Assemble dry: stays into the saddles (Al disc first), bars into the knuckle sockets, Ti pins, caps with Belleville pairs torqued to 0.5 N m (M3) and 1.2 N m (M4). Bolt the pan and the hip node, then fit the crown as today.
5. Re-torque the caps after 24 h and after the first hot trip. Inspect at every T5 stop.

Skill: intermediate (accurate drilling of carbon). Build time about 9 h, without print time.

## 6. Assumptions and coupon tests

- ASSUMPTION A1: CFRP pin bearing 300 MPa ultimate x 0.8. **RC-2**: 5 pin-bearing pulls on a 20 mm tube with a reamed 4.0 hole and a printed boss; mean >= 300, min >= 240.
- ASSUMPTION A2: filled-hole ratio 0.55. **RC-3**: notched 4-point bends, 4 mm cross hole and 2 x 3 mm single-wall holes.
- ASSUMPTION A3: PAHT pin bearing >= XY tensile x 0.8; contact at Z. **RC-4**: knuckle proof at 1.5 x the largest factored end load, then to failure.
- ASSUMPTION A4: bearing fatigue ratios 0.5 (CFRP) and 0.3 (PAHT). **RC-2f**: 1e5 cycles, hole elongation <= 0.1 mm.
- ASSUMPTION A5: no friction credit, Belleville preload. **RC-5**: 40 C 8 h hold plus 7 days, residual torque >= 50 %.
- ASSUMPTION A6: Rock West modelled at 0.845 mm (vendor 1.0 mm). **RC-1**.
- ASSUMPTION A7: printed neck annulus t 4 mm. **RC-4**.
- ASSUMPTION A8: flat QI pan plus saddles at the beam-model plate (formed flanges dropped). **RC-6** and HA-LS-1 T1 deflection.
- ASSUMPTION: rail compatibility Kt 1.5 at window corners; Belleville pair 1.2 kN/mm; long-term creep 3 x the 8 h value.
- ASSUMPTION: spreader clips on the 20 mm stays at the same x / z as today (re-run `spreader.evaluate` before release).
- Then HA-LS-1 T9, T1-T5 and T2u on P1 / P2.

## Screenshots

- `outputs/screens/20261110_compC_1.png`: ROD next to today's frame (Cycles)
- `outputs/screens/20261110_compC_2.png`: mid knuckle and rail close-up (Cycles)
- `outputs/screens/20261110_compC_3.png`: the 24 lowest margins
- `outputs/screens/20261110_compC_4.png`: member utilisation and deformed shape
