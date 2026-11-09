# CORRIE weight pass: package C structural gates (C-1..C-4, C-7, C-9)

Owner: structural-fea-engineer, 2026-11-09. Requested by: DECISIONS 2026-11-09 "Owner: 'Yes' to the weight-pass
recommendation", item (3). Item definitions: [weight_pass_corrie.md](weight_pass_corrie.md) section 3.3.
Standard: HA-LS-1 rev C ([load_standard.md](load_standard.md)). **SF/req** = capacity / factored demand; **>= 1.0 passes**.
Code: `huntkit/gendesign/weight_c.py` (engines: `hipbelt_structure` grillage, `huntkit.fea.plate_grid` ACM plates + CLT,
the rev C voxel verification). Results: [weight_c_structural_results.json](weight_c_structural_results.json),
C-9 detail `outputs/weight_c/c9_body.json`. Tests: `tests/test_weight_c.py` (12 pass: springback and residual stress
vs direct through-thickness integration, Goodman reduction, Heywood limits, ACM clamp patch vs cantilever strip, CLT
FI linearity and QI in-plane modulus, backer equilibrium, C-1 record reproduction).

```
python -m huntkit.gendesign.weight_c          # C-1..C-7 (2 min) + figures; C-9 from the cached json
python -c "from huntkit.gendesign import weight_c as W; W.c9()"   # C-9 voxel study, ~6 min on 4 cores
```

Nothing released was edited (no YAML, pattern or `corrie.py` change). Mass is size M, grams real.

## 0. Verdicts

| Item | Change | Verdict | Real g saved | Governing SF/req (today -> C) | Test |
|---|---|---|---:|---|---|
| **C-1** | belt plate 6061-T6 1.5 -> **7075-T6 1.2**, **cold slip-rolled to a template** | **PASS** | **13.0** | walking fatigue at the hub edge 1.20 -> **1.07** (residual stress counted adverse, end slope +/-2 deg); best estimate 1.40 | HB-5 on a 7075 plate (proof + 1e5 cycles); template check of the end slope |
| **C-2** | PA66 hub D36x12 -> **D28x10** | **PASS** (with the pad on the frame) | **7.2** | plate at the hub rim 1.20 -> **1.19**; bore bearing walk 5.3 -> 4.4 | HB-5 |
| **C-3** | 2 lightening holes in the bow-tie spine | **PASS** | **5.0** (Ø28 at x ±42.5, z 0, 6061) / 5.1 (Ø31 on the 7075 plate) | net section + Heywood Kt, walking: **1.14** (6061) / 1.21 (7075) | HB-5 with the holes |
| **C-4** | HDPE pad backer 1.0 -> 0.8 mm | **FAIL** | 0 (the fix costs +8.1) | creep / fatigue over the channel 0.63 / 0.53 -> **0.55 / 0.44**; sags onto the bow-tie spine | sag test of the pad seat, 413 N held 8 h |
| **C-7** | CFRP yoke plate 1.5 -> 1.2 mm | **FAIL** | 0 (the fix costs +8.5) | first ply, C8 hipbelt-off pad push **0.90 -> 0.65** | T1(c) with a dial on the yoke tip |
| **C-9** | printed body: inward offset of low-stress ligaments, max 1.75 mm | **PASS** | **45.6** | fatigue (C_im3 static carry) 1.044 -> **1.020**; strength 1.51 -> 1.47; creep 2.23 -> 2.18 | T5 cycle test (fatigue still governs at ~1.0) |

**Package C as gated:** C-1 + C-2 + C-3 on one plate: 7075-T6 1.2, D28 hub, 2 x Ø31 holes: **min SF/req 1.08,
-25.0 g**; C-9 **-45.6 g**. Total **-70.6 g** vs the booked -66.3 g for these four (13.0 + 7.1 + 5.0 + 41.2); the booked package
also counted C-4 and C-7 (5.4 + 8.5 g), which fail. **C-4 and C-7 fail and also flag the released parts** (sections 4, 5): fixing them costs
**+8.1 g** (CFRP 0.8 mm backer) and **+8.5 g** (1.8 mm yoke). Net of the fixes: **-54.0 g** vs today's booking.

Charts: `outputs/screens/20261109_weightC_1.png` (governing SF/req, today vs C, per item) and
`outputs/screens/20261109_weightC_2.png` (C-1 forming routes, C-4 thickness sweep, C-9 grams vs margin).

## 1. Loads

Belt plate, backer: `hipbelt_structure.load_sets()` (rev C): C2 stumble 2.0 g x 1.5 (T 1000 N/side, H 1239 N, V 1601 N),
C1 1.0 g x 2.0, walking 0 -> 1.6 g x 1e5 (T 483, H 661, V 854), carry 1 g sustained (H 413 N at 15 in).
Yoke: the `shoulder` reaction of the frame.yaml beam model, every rev C case x torso 15/19/23, both bag-couple variants,
x the case factor. Printed body: every rev C set (27 crown-bar + 15 IM3 couple) on the 2 mm voxel model, FI99 rule,
fatigue and creep from C1 (`frame_cg_recheck.summarize_body`), as rev_c_verification.md.

## 2. C-1 7075-T6 1.2 mm bow-tie and how to form it

Same grillage-on-foundation model and load sets as hipbelt_structural.md (record reproduced: C2 1.21, walk 1.20).
New here: the forming route sets the allowables, and the end slope is checked at nominal and at ± the route tolerance.

**Forming numbers (elastic-perfectly-plastic springback, verified against direct integration):**

| | 6061-T6 1.5 (today) | 7075-T6 1.2 |
|---|---:|---:|
| elastic-limit radius E t / 2 sy (no permanent set above it) | 187 mm | 86 mm |
| tool radius that springs back to R 417 (14.6 deg end slope) | **104 mm** | **58 mm** |
| outer-fibre strain at the tool / elongation | 0.71 % / 12 % | 1.02 % / 11 % |
| plastic strain | 0.32 % | 0.33 % |
| residual surface stress after springback | 95 MPa | 136 MPa |
| end slope if the yield is 5 % low / high (same tool) | 16.4 / 12.9 deg | 17.7 / 11.8 deg |

Two corrections to the item text and to hipbelt_structural.md:
- **7075-T6 can be cold-rolled at this radius.** "Cannot be cold-formed" applies to tight bends (min bend radius ~5 t);
  here the strain is 1 %, a tenth of the elongation. What makes it hard is springback (tool R 58 for a final R 417) and
  its sensitivity to yield scatter (±3 deg). Use a **3-roll slip roll** and a **paper / plywood template** of the
  R 417 arc; roll, check, re-roll until it fits (ASSUMPTION: ±2 deg achievable).
- The 6061 instruction "roll by hand over a ~400 mm form" leaves **no permanent set** (400 > R_e 187 mm). It also needs
  a slip roll (or a ~104 mm form, then check against the template).

| Route (7075-T6 1.2) | static | fatigue | slope tol. | min SF/req | note |
|---|---|---|---|---:|---|
| **cold slip-roll to template**, residual counted adverse | S-basis 462 | Goodman with 136 MPa mean, shakes down to yield | ±2 deg | **1.07** | recommended; $0 service; conservative |
| same, best estimate (residual compressive on the convex face, which is the tension face at the hub-edge peak) | 462 | no residual | ±2 deg | 1.40 | |
| W-temper form + age (T62), heat-treat service | 462 | no residual | ±3 deg (quench) | 1.27 | $25 / plate ASSUMPTION; owner cannot do it |
| creep-age form (clamped over an over-bent form, 160-175 C 8-24 h) | x0.865 (T73) | x0.95 | ±2 deg | 1.28 | kitchen-oven class; check hardness after |
| hot form > 250 C | ~103 (annealed) | | | **0.33** | reject |
| flat + 1 brake bend per side at x 75 | 462 | bend line x0.8 | ±1 deg | **0.83** | **fails**: the kink load at x 75 adds hub bending |
| flat + 2 brake bends (x 50, 75) | | | | 1.19 | |
| flat + 3 bump bends (x 37.5, 62.5, 87) | | | | 1.31 | press-brake alternative if no slip roll; bend R >= 6 mm |

Kink model: at each bend line the plate tension T cos θ turns by β and presses the line toward the body with
T cos θ sin β, reacted by the foundation. A kink outboard of about half the half-width adds hub-edge bending, one
inboard relieves it, so a single sharp bend at the ear root is the worst choice. Model-form check: the smooth arc
built from 6 kinks gives 2.6 (6061) vs 1.20 for the hipbelt_structure simplification (arch normal load ignored): the
recorded model is conservative and is kept.

**Same treatment applied to today's 6061 plate:** cold-rolled with the residual counted adverse it drops to 0.65, and
with the slope tolerance alone (best estimate) to 0.94. The released 6061 plate is therefore **marginal once forming
is counted**; 7075 is the better part, not only the lighter one. Pin bearing on the reamed plate hole: 7075 1.2 C2 5.2.
Other plate results: C2 1.50, C1 2.42, creep 4.85 (cold roll).

Mass: plate 77.5 -> 64.5 g, **-13.0 g**. Cost: no heat-treat service on the recommended route (the $25 ASSUMPTION in
the weight pass falls away); 7075 sheet ~$15/kg vs $8/kg (records), < $1 per plate.

## 3. C-2 hub D28 x 10 and C-3 holes

**C-2.** The grillage was re-run with the smaller rigid hub (rim line at r 14): plate 1.21 / 1.19 (C2 / walk) vs
1.21 / 1.20. PA66 bore bearing on the 10 mm Ti pin with 10 mm engagement: walk 4.39, C2 6.25 (pad on the frame, H off
the pin). **With H on the pin the D28 hub fails walking bearing (0.86)**: C-2 is valid only while the lumbar push stays
off the pin, i.e. the pad seat on the frame **and** a backer that never touches the plate spine (C-4). Hub
13.5 -> 6.2 g, **-7.2 g**.

**C-3.** One hole per side at (x ±42.5, z 0) in the 60 mm spine band. Net-section check at the hole: grillage section
moment over the net width + membrane (T cos θ on the net area, wing V share as in-plane bending on the net I), fatigue
with Heywood Kt_net = 2 + (1 - d/D)^3:

| d mm | g saved (6061 1.5) | SF/req (6061) | g saved (7075 1.2) | SF/req (7075, cold roll) |
|---:|---:|---:|---:|---:|
| 20 | 2.5 | 1.29 | 2.1 | 1.43 |
| 25 | 4.0 | 1.20 | 3.3 | 1.34 |
| 28 | **5.0** | **1.14** | 4.2 | 1.26 |
| 31 | 6.1 | 1.06 | **5.1** | **1.18** (1.21 on the D28 plate) |

The hole section never goes below the hub-edge governing value until Ø31 on 6061. Ø28 slightly overruns the x 30..55
window (28.5..56.5); that is inside the spine band (flare at 62.5). Water-jet the holes with the plate, deburr, radius
>= 1 mm on the edge.

**Plate package (C-1 + C-2 + C-3 Ø31):** min SF/req **1.08** (walking, residual adverse), **-25.0 g** vs the released
94.6 g plate + hub + latch.

## 4. C-4 pad backer: FAIL (and today's 1.0 mm fails too)

Model: the backer (190 x 150) as an ACM plate between two Winkler foundations: the body side (B lumbar stack EVA 30C 6 +
EVA 45C 6 + 25 mm tissue, k 0.0022 N/mm³, the fit model's value) driven to the total lumbar push H, and the two EVA 45C
6 mm rails (k 0.08 N/mm³, x ±35..90, 140 tall). Unilateral contact with the bow-tie spine band in the channel at
**4.5 mm** depth play. Creep: HDPE at 0.35 x E (ASSUMPTION, 1000 h). Allowables: HDPE yield 26 x 0.8 hot (C2), 10 MPa
range (walk), 5 MPa sustained (carry) (hipbelt_structure ASSUMPTIONS).

| Backer | g | C2 | walk (fatigue) | carry (creep) | channel sag, walk after creep | share of H into the plate spine | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| HDPE 0.8 (C-4) | 21.8 | 0.50 | **0.44** | 0.55 | 15.0 mm | 11 % | FAIL |
| **HDPE 1.0 (released)** | 27.2 | 0.61 | **0.53** | 0.63 | 13.9 mm | 11 % | **FAIL** |
| HDPE 2.0 | 54.4 | 1.30 | 1.00 | 1.16 | 7.5 mm | 6 % | fails contact |
| HDPE 3.0 | 81.7 | 1.80 | 1.63 | 1.71 | 4.6 mm | 0 | passes, heavy |
| 6061-T6 0.8 | 61.6 | 1.48 | 1.37 | 4.45 | 2.7 mm | 0 | passes |
| **CFRP quasi-iso 0.8** | **35.3** | 1.73 | **1.50** | 4.81 | 3.3 mm | 0 | **passes, lightest** |

Hand check: a 1.0 mm HDPE strip over a 70 mm clamped span has k_eq = 384 D / L⁴ = 0.0018 N/mm³, the same order as the
body foundation, so it sags until the body pressure over the channel halves; at 14.5 kPa mean that is several mm.
**Consequence:** the released pad seat lets the backer creep onto the bow-tie spine, which puts ~10 % of H (about
70 N walking) back on the pin, the opposite of the pad-on-frame decision, and drags on the belt roll.
**Recommendation (pack-designer):** backer **CFRP quasi-iso 0.8 mm** (record `cfrp_plate_quasi_iso`, smeared values;
ASSUMPTION first ply = compressive x 0.8 x 0.65), 35.3 g, **+8.1 g** vs the booked 27.2 g, keep the HDPE slip liner on
its channel face. Or narrow the channel. C-4 as proposed is withdrawn.

## 5. C-7 yoke plate: FAIL (and today's 1.5 mm fails the C8 abuse case)

Model: ACM plate on the YOKE_OUTLINE polygon (216 x 96, 18 200 mm²), clamped (w and slopes) on the 46 mm crown spine,
CLT [0/45/-45/90]s T700 UD (ply t / 8, 0 deg along the wing), Tsai-Wu first ply with hot/wet 0.8 and impact 0.65 on
compression. Strap pull (frame reaction y < 0): split to the two strap pins (x ±46, z -10; C3: 25/75 for the slack
downhill strap). Pad push (y > 0): the body pushes the yoke pad through a Winkler foundation (EVA 45C 10 mm + 15 mm
tissue, k 0.0037 N/mm³), plus a uniform-pressure bound and k x0.5 / x2. In-plane strap loads: running loads at the
clamp line, Ti pin bearing (Ø6) and shear-out.

The lifters anchor on the crown (DESIGN.md D-2), not on the yoke. The yoke takes the shoulder-harness reaction only.

| t | g (plate) | strength min (case) | uniform bound / k x0.5 / k x2 | fatigue (FI <= 0.5 at 1.6 g) | pin bearing |
|---|---:|---|---|---:|---:|
| **1.5 (released)** | 42.3 | **0.90** (C8 hipbelt-off, 23 in) | 0.75 / 0.83 / 1.03 | 1.84 | 3.9 |
| 1.2 (C-7) | 33.8 | **0.65** | 0.48 / 0.57 / 0.80 | 1.17 | 3.1 |
| 1.8 | 50.8 | 1.21 | | 2.65 | 4.6 |
| 2.0 | 56.4 | 1.46 | | 3.28 | 5.1 |

Why: with the belt off (C8, 68 kg x 1.5 g, factor 1.0) the 205 mm CG couple is held only by the lifters at the crown
top and the back pushing on the frame at the yoke: **1.40-1.43 kN aft** at the yoke node, against 0.10-0.46 kN in every
other case. The yoke wings (85 mm outboard of the spine) bend under that push; the peak is at the lower corner of the
spine clamp. Fatigue (walking strap pull) is not the issue. The beam model puts all of that back contact on the yoke;
in reality part goes into the back panel and spreader, so this is conservative, and the clamp corner peak is a local
singularity of the patch clamp model. Still, nothing on file shows the 1.5 mm plate holds it.
**Recommendation:** C-7 withdrawn. Released yoke: go to **1.8 mm (+8.5 g)** or add a 60-70 mm wide spine saddle
under the yoke, then confirm in **T1(c)** (225 lb hipbelt-off hang) with a dial on the yoke tip: if the measured yoke
push is under ~1 kN, 1.5 mm stands.

## 6. C-9 printed body mass pass

Method (a mass-objective re-run restricted to low-stress ligaments, not a new topology): voxel FE of the production
branch body under every rev C set; per-voxel utilisation = max(strength FI envelope, static-carry FI x 1.6 / 2.0 / 0.3);
max-filtered over 8 mm; the body SDF is offset inward by up to δ where that utilisation is below 0.30 (tapering to 0 at
0.55), **never more than 30 % of the local radius** (no ligament disappears, the generative look stays), and **never
within 4 mm of** the crown sleeve walls / bores, pawl housing, hip-pivot boss (inserts), load pads and spine channel.
Each candidate is re-verified with the full FI99 rule (the 99th percentile rises when low-stress volume goes, which
the re-verification counts).

| δ max | body g | saved g | strength | fatigue | creep |
|---:|---:|---:|---:|---:|---:|
| 0 (released) | 823.2 | 0 | 1.510 | 1.044 | 2.228 |
| 1.25 | 788.4 | 34.8 | 1.482 | 1.025 | 2.188 |
| **1.75** | **777.6** | **45.6** | **1.468** | **1.020** | **2.176** |
| 2.5 | 766.0 | 57.2 | 1.455 | 1.016 | 2.167 |
| 3.5 | 756.6 | 66.6 | 1.450 | 1.006 | 2.147 |

Pick: the deepest offset that keeps fatigue >= 1.02 (ASSUMPTION: 2 % for voxel / FI99 noise): **δ 1.75 mm, -45.6 g**.
Where it comes from: lumbar struts / pan 10.0 g, stay feet 9.1, stays below the sleeve 11.1, outer sleeve walls 8.8,
mid bar 3.1, upper bar / pawl region outside the housing 1.9, others 1.4. The governing spot does not move (C_im3 static
carry, stay below the sleeve, z 153). **Pack-designer / printing:** the lumbar-pan face moves in by up to 1.75 mm, so
the pad-seat rails and the 4.5 mm depth play must be re-measured on the new STL; the stay-foot boots need a fit check.
Re-export the STL from `spreader_layout.frame_sdf_layout` + this offset (`weight_c.offset_field`).

## 7. Prototype tests

- **HB-5** (hipbelt_structural.md) on the 7075 1.2 plate with the D28 hub and the Ø31 holes: proof at 1.0 kN per ear +
  1.6 kN vertical, then 1e5 walking cycles. Check the end slope against the template before and after.
- **Pad-seat sag test** (new): pad seat on a pan offcut, 413 N on a 150 x 190 foam block held 8 h at room temperature,
  then 661 N; measure the backer sag in the channel. Pass: < 3 mm, no contact with a dummy plate spine at 4.5 mm.
- **T1(c)** with a dial indicator on the yoke wing tip and, ideally, a pressure film under the yoke pad (measures the
  share of the back push the yoke takes).
- **T5** cycle test on the C-9 body (fatigue governs at 1.02).

## 8. Assumptions (new here; also tagged in the code)

- ASSUMPTION: end-slope tolerance ±2 deg (template / re-roll), ±3 deg (quench distortion), ±1 deg (brake).
- ASSUMPTION: forming residual stress kept in full as an adverse mean stress, shaken down to yield (conservative route).
- ASSUMPTION: creep-aged 7075 = T73 (x0.865 yield, x0.95 fatigue); cold brake-bend line fatigue x0.8.
- ASSUMPTION: Al pin bearing yield 1.5 x S-basis yield, pin hole reamed to the 10 mm pin.
- ASSUMPTION: Heywood tension Kt_net also used for the out-of-plane bending at the hole (conservative).
- ASSUMPTION: HDPE creep modulus 0.35 x E; hot 0.8 on HDPE yield; the pad wedge is not in the body foundation.
- ASSUMPTION: CFRP backer first ply = smeared compressive strength x 0.8 x 0.65 (no CLT layup for a 0.8 mm plate yet).
- ASSUMPTION: yoke layup [0/45/-45/90]s T700 with the 0 plies along the wing (an 8-ply QI is 3.9x stiffer in D11 than
  D22: the orientation matters, put it on the DXF); Ti pin Ø6; strap load disc 14 mm; yoke pad EVA 45C 10 mm;
  15 mm tissue over the upper back; yoke clamped (bonded + bolted) over the full spine width.
- ASSUMPTION: C-9 utilisation thresholds 0.30 / 0.55, 8 mm max filter, 30 % local-radius cap, 4 mm keep-out,
  2 % fatigue reserve.
- Records missing (materials-engineer): 7075-T6 forming / springback data and a 7075-T73 (or T62) record; HDPE creep
  modulus and creep-rupture fields in `hdpe_sheet`; a CLT layup record for thin QI plate (backer, yoke).

## Screens

- `outputs/screens/20261109_weightC_1.png`: governing SF/req per item, today vs package C, with PASS / FAIL.
- `outputs/screens/20261109_weightC_2.png`: C-1 by forming route; C-4 margin and channel sag vs backer thickness; C-9
  grams removed vs fatigue / strength margin.
