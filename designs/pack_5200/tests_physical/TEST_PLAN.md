# Pack 5200 physical test plan (one plan for every coupon and prototype test)

Owner: manufacturing-engineer, 2026-11-10, backlog ticket BL-016. Frame **H1** (owner adopted 2026-11-10), bag
**CORRIE B.2**, hipbelt **B** with the 7075 plate (package C), load standard **HA-LS-1 rev C**.

- Register (one row per test, every column the ticket asks for): [`test_register.csv`](test_register.csv)
- One-page ranking for the phone: `outputs/screens/20261111_BL016_1.png` (same image as `20261110_BL016_1.png`)
- The fatigue rig and the CA coupons are described in full in [`CA1_fatigue_rig.md`](CA1_fatigue_rig.md). This plan
  does not repeat that procedure; it puts CA-1 in order with everything else.

Units: N, kg, mm, with lb and in in brackets. The crane scale reads kg: **N = kg × 9.81**.

## 0. The plan in one screen

1. **83 test IDs** were found across the analysis, build and research documents listed in §10. **48 are active.** 35 are retired (they belong to a frame or bag
   entry that was not adopted, or to a superseded part) or merged into another test (§6, §7).
2. **Four kits** cover all 48 tests: **A** pull bench, **B** lever fatigue rig, **C** frame test stand, **D** measuring
   tools, plus **E** (things you already own: washing machine, gloves, freezer). Kits cost about **$875** in all
   (§4). Test samples add about **$409**, plus the sacrificial P1 frame for T2u ($437, `frame_h1.md` §5).
3. **Order: safety first.** Nothing gets carried until the hooks, bartacks, cams and seams have held their proof
   load (weekend 1), the frame material and joint coupons have passed (CA-1, CA-5), and the first-article frame has
   passed T9, T1, T3, T2 and T4.
4. **Then grams.** Eight tests unlock or protect mass. Ranked by grams per dollar (parts + $15 per owner hour,
   ASSUMPTION): WP-3, WP-1, WP-5, CA-1, WP-2, HB-5, RF-1, FS-O5 (§5). Together they are worth **160 g** (if CA-1
   proves 0.40; 100 g without it). WP-1, WP-3 and WP-5 protect 54.6 g that CORRIE B.2 already took.
5. **First weekend:** build the pull bench and run 11 tests in about **13 h hands-on, $116 of samples** (§2). They
   gate every sewn load point on the bag and harness. Start printing the CA-1 coupons the same weekend, because they
   need 7 days of conditioning before the fatigue rig can use them.
6. **Hours:** about **108 h hands-on** and about **409 h of unattended machine time** (mostly CA-1 at 1 Hz) for the
   whole plan.

## 1. Safety rules (read before every session)

- **Stand to the side of the load line, never in line with it.** A hook gate or a pin can leave at speed when a
  sample lets go. Lay a moving blanket or an old sleeping bag over the sample before you pull.
- Safety glasses and gloves on. Nobody near the line while it is loaded.
- **Never put a ratchet strap in the load line above 1480 N (151 kg on the scale).** The Haul-Master straps are sold
  as "1000 lb capacity" ([Harbor Freight][hf-strap]). ASSUMPTION: that is the break strength and the working limit is
  a third of it, 333 lb (1480 N). The come-along (2 ton, [Home Depot][hd-come]) and steel pins carry the high loads.
- The crane scale is 300 kg (2943 N). **Stop at 280 kg (2750 N).** Tests that need more (CA-5 static pulls,
  4.4 kN) use the lever rig with the 200 kg cell (§4 kit B).
- Frame tests (phase 4) follow `load_standard.md` §5: back-up sling under the load, no one under the load, T2u
  outdoors with an exclusion zone.
- **If anything fails: stop, photograph it, write it in the log and send the log.** Do not repair and continue.
  A failure is a result, not a mistake.

## 2. First weekend (beginner, about 13 h hands-on)

Everything here uses kit A (pull bench), kit E and three items from kit D (caliper, phyphox, loupe). Each test cites
the document that defined it; the numbers here are copied from those documents.

### 2.0 Before the weekend: buy and sew

**Buy:** all of kit A (§4.1), the caliper and loupe from kit D, and the samples:

| sample | qty | for |
|---|---:|---|
| rated 38 mm bag hooks (the production part, ≥ 2200 N) | 5 | PT-1 |
| meat-strap 38 mm hooks | 5 | MT-2 |
| 38 mm cam buckles (the IM cam and the under-strap cam) | 5 | MT-3 |
| heavy 25 mm ladder locks + 25 mm D-rings | 5 + 5 | HB-7 |
| 25 mm ladder lock + tri-glide keeper | 1 + 1 | PT-5 |
| 38 mm ladder lock (W1-W3 type) | 1 | WP-3 |
| 38 mm poly webbing, 25 mm webbing | about 4 m + 3 m | all |
| Hypalon, B-01 laminate, B-05 500D, 330D, ULTRA 200, 100D Robic offcuts | scraps | PT-2, PT-3, WP-1 |

**Sew (about 5 h, counted in the 13 h)** on the same machine, thread and needle as the pack:
- **MT-1:** 5 loops of 38 mm webbing, each end folded into a 20 mm loop and closed with a 38 × 38 box-X, stitch 301,
  7 SPI, bonded nylon tex 135 (`bag_attachment.md` §5 sewn-side spec).
- **PT-2:** 5 × T3 tongue on a B-17 tab on a B-01 swatch about 200 × 200 mm, exactly as `bag_attachment.md` §5 T3.
- **PT-3:** 5 × HE eye on B-18 + B-01 + B-05 seam swatch, **without binding** (CORRIE B.2 as sewn,
  `corrie_body.md` §12.4).
- **WP-1:** one 200 mm seam swatch per pairing: 330D|330D, 330D|ULTRA 200, 500D|330D, 100D|ULTRA. Stitch 301, then a
  second row 6 mm into the allowance, trim, sear the raw edge with the hot knife.
- Label every sample with a paint pen: test ID and sample number (PT-2-1 ... PT-2-5).

### 2.1 Saturday morning: build the pull bench (2 h)

The bench pulls **horizontally along the floor**, so nothing hangs over you.

```
 ANCHOR 1 ── chain/round sling ── COME-ALONG ── CRANE SCALE ── PIN FIXTURE ── SAMPLE ── PIN/CLAMP ── sling ── ANCHOR 2
 (tow hitch, tree,                 (2 ton)       (300 kg)       (5 mm pin)              (5 mm pin, or bar clamps)
  or lagged 4x4)                                  on a board
```

1. **Anchors.** Two fixed points 2–3 m apart, each good for far more than 3 kN: a vehicle tow hitch, a tree, a
   steel post, or a 4x4 lag-screwed into wall studs (the kit C wall frame, `load_standard.md` §5.1). ASSUMPTION: a
   lag-screwed 4x4 into two studs holds 3 kN; check that it does not move during the calibration pull.
2. **Pin fixture.** A steel flat bar (40 × 6 mm) with a 5.0 mm hole near one end and a bolt hole at the other.
   Push a hardened 5 mm dowel pin through the hole: the hooks, eyes and loops go over this pin, like the frame's
   5 mm eyes (`bag_attachment.md` §5 "hook on a 5 mm pin").
3. **Bar clamps** for swatches: two pairs of aluminium bars, 150 mm long, with three M6 bolts each, and 120-grit
   cloth glued to the faces. Clamp a swatch 120 mm wide (PT-2) between one pair.
4. **Scale on a board.** The crane scale lies on a flat board so it does not drag on the floor. Zero it lying down.
5. **Calibrate** (15 min). Hang the scale from a beam and hang a full 20 L water jug from it: 20.0 kg (196 N). The
   scale must read 20.0 ± 0.2 kg. Write the reading in the log. Then lay it back on its board and zero it.
6. Dry run: a loop of 38 mm webbing over the pin, pull to 50 kg, hold, release. Check the anchors did not move.

### 2.2 Saturday: bought parts (about 3.5 h)

For every pull: **load slowly** (about one come-along click per second), stop at the target, **hold** for the
stated time, re-tension if the reading drops (webbing stretches), then release. Write the peak and the result.

| order | test | set-up | target on the scale | hold | pass | defined in |
|---:|---|---|---|---|---|---|
| 1 | **PT-1** rated bag hook | hook over the 5 mm pin; 38 mm webbing loop on the hook bed | **216 kg** (2120 N) | 60 s | 5 of 5 hold, **gate closes** after release | `bag_attachment.md` §3, §5 |
| 2 | **MT-2** meat-strap hook | as PT-1 | **92.8 kg** (910 N) | 1 min | 5 of 5 hold, gate closes | `BUILD_PLAN.md` §5a.0 |
| 3 | **MT-3** cam buckle | webbing threaded as in the pack; paint-pen mark at the cam mouth | **92.8 kg** (910 N) | 1 min | mark moved **< 3 mm**, 5 of 5 | `BUILD_PLAN.md` §5a.0 |
| 4 | **HB-7** belt ladder lock | anchor on the buckle half → round the D-ring → back through the lock (corrected routing, `hipbelt_structural.md` §5); mark the webbing | **43.4 kg** (426 N), then keep pulling until it slips | 1 min at 43.4 kg | no slip at 43.4 kg; slip load ≥ **50.0 kg** (490 N) keeps the record | `hipbelt_structural.md` §5, §8 |
| 5 | **PT-5** guy ladder lock + keeper | 25 mm webbing; mark at the lock | 0 → **17.3 kg** (170 N) → 0, **10 times** | – | total slip **< 5 mm** | `bag_attachment.md` §5 |
| 6 | **WP-3** gloved tail | 38 mm ladder lock, 150 mm tail, 10 kg hanging | – | – | winter gloves on: release and re-tension **in one grab**, 5 of 5, loaded and slack | `corrie_body.md` §12.4 |

Notes:
- MT-2 and MT-3: `meat_haul_modes.md` says 830 N; `BUILD_PLAN.md` says 910 N. This plan uses **910 N** (the higher,
  = 1.5 × the 605 N meat-leg load). See §6.
- HB-7: the source only says "as the record notes". The 426 N number is derived here: 1.5 (the doc's slip
  criterion) × 284 N (walking-peak lock load, `hipbelt_structural.md` §5).

### 2.3 Saturday evening: start the wash and the printer (1 h)

- **WP-1:** put the 4 seam swatches in a mesh laundry bag with a towel. Normal cycle, cold (ASSUMPTION: the R-12 wash
  is a normal cold cycle), dry on a line. **3 cycles** across the weekend (about 1.5 h machine time each).
- **CA-1 coupons:** print the 12 XY + 4 Z + 3 spare bars, the 3 Z bars and 3 short-beam blocks for CA-3 and 5 insert
  blocks for HB-6, from the same dried spool and profile as the frame (`CA1_fatigue_rig.md` §2). Sunday: anneal
  90 °C 6 h, then into the conditioning box (saturated magnesium nitrate, about 53 % RH, ASSUMPTION in
  `CA1_fatigue_rig.md` §2) for **7 days**. This is the critical path for the frame, which is why it starts now.

### 2.4 Sunday: sewn samples (about 4 h)

| order | test | set-up | target on the scale | hold | pass | defined in |
|---:|---|---|---|---|---|---|
| 7 | **MT-1** 38 mm box-X | loop over the 5 mm pin, other loop over a second pin on the anchor side | **92.8 kg** (910 N) | 1 min | 5 of 5 hold, no broken stitch | `BUILD_PLAN.md` §5a.0 |
| 8 | **PT-2** T3 tongue on B-17 | B-01 swatch clamped 120 mm wide in the bar clamps; tongue loop on the pin | **216 kg** (2120 N) | 60 s | 5 of 5 hold, no stitch break, no laminate tear | `bag_attachment.md` §5 |
| 9 | **PT-3** HE eye, no binding | 5 mm pin through the eye; swatch clamped | **156 kg** (1530 N) | 60 s | 5 of 5 hold | `bag_attachment.md` §5, `corrie_body.md` §12.4 |
| 10 | **WP-1** wash fray | after the third wash, look at each seared edge with the loupe | – | – | **no fray past the second row** on any swatch | `corrie_body.md` §12.4 |
| 11 | **HB-2** belt-face friction | see below | – | – | μ ≥ 0.45 credits the grip print | `hipbelt_fit.md` §10 |

**HB-2 without a force gauge** (ASSUMPTION: a tilt-board static μ stands in for the ASTM D1894-style sled pull).
Tape the base layer (polyester, then merino) flat on a smooth board. Wrap the belt face fabric round a 500 g sled
(a flat block with a weight on it). Put the phone on the board with phyphox "Inclination". Raise one end slowly until
the sled starts to slide; read the angle. **μ = tan(angle)**: 24.2° gives 0.45. Five runs each: with and without the
grip print, both base layers, dry and sprayed damp (sweaty). Pass to credit the print: **mean μ ≥ 0.45**
([phyphox][phyphox] is free).

### 2.5 After the weekend

- Write the log (§8 template) and send it with photos of every failed or doubtful sample.
- **Any failure in PT-1, MT-1, MT-2, MT-3 or PT-2/PT-3: change the hardware or the sewing and re-test 5 new samples
  before you cut the bag.** These parts carry the meat.
- Order kit B parts (lever rig) for weekend 2: the coupons will be ready on day 8.

## 3. Full run order (all 48 active tests)

Tiers: **safety** = a strength, fatigue or retention margin depends on it; **grams** = it protects or unlocks a
mass saving; **function** = fit, comfort, noise or a user procedure. Gram tests that cost under an hour are run in
the same session as the safety tests on the same kit (WP-3, WP-1 on weekend 1).

Phases: **1** weekend 1 (bench); **2** coupons and lever rig (weeks 2–4); **3** sewn parts; **4** first-article
frames P1 / P2 (only after CA-1 and CA-5 pass: `print/frame_h1/README.md`); **5** complete pack and field.
Full steps, specimens, pass numbers and notes for every row are in `test_register.csv`.

| # | id | test | tier | gates | g at stake | kit | hands-on h | machine h | samples $ | defined in |
|---:|---|---|---|---|---:|---|---:|---:|---:|---|
| 1 | **PT-1** | 38 mm rated bag hook proof | safety | all 4 bag hooks (IM2/IM3, B-24 links) | – | A | 1.0 | – | 30 | analysis/bag_attachment.md §3, §5 |
| 2 | **MT-2** | meat-strap hook proof (R-29) | safety | IM1-IM3 meat straps, under-straps (R-29) | – | A | 0.5 | – | 15 | BUILD_PLAN.md §5a.0; analysis/meat_haul_modes.md (assumptions) |
| 3 | **MT-3** | cam buckle slip on 38 mm webbing (R-29) | safety | IM cams and the under-strap cam | – | A | 0.7 | – | 20 | BUILD_PLAN.md §5a.0; analysis/meat_haul_modes.md |
| 4 | **HB-7** | hipbelt heavy ladder-lock slip, corrected 2:1 routing | safety | belt B 2:1 pull | – | A | 0.7 | – | 7.5 | analysis/hipbelt_structural.md §5, §8 |
| 5 | **PT-5** | guy ladder lock + tri-glide keeper slip | safety | TG guys (top anchor) | – | A | 0.5 | – | 5 | analysis/bag_attachment.md §5 |
| 6 | **WP-3** | gloved tail on W1-W3 ladder locks | grams | A-2 wrap tails 250 -> 150 mm | 5.4 | E | 0.3 | – | 0 | analysis/corrie_body.md §12.4 |
| 7 | **MT-1** | 38 mm box-X bartack proof (R-29) | safety | every 38 mm box-X on the meat harness | – | A | 1.0 | – | 3 | BUILD_PLAN.md §5a.0 |
| 8 | **PT-2** | T3 tongue on B-17 on a B-01 swatch | safety | IM3 bag attachment | – | A | 2.5 | – | 15 | analysis/bag_attachment.md §5 |
| 9 | **PT-3** | HE eye on B-18 + B-01 + B-05 seam, built without binding | safety | hinge eyes; B-1 (no binding); C-5 if on ULTRA 200X | – | A | 2.5 | – | 15 | analysis/bag_attachment.md §5; analysis/corrie_body.md §12.4 (rebuilt); analysis/fabric_swap_evidence.md O-5 |
| 10 | **WP-1** | wash-swatch fray, seams without binding | grams | B-1 (no binding on body seams) | 36.4 | E | 2.0 | 4.5 | 5 | analysis/corrie_body.md §12.4; analysis/weight_pass_corrie.md B-1; analysis/build_simplicity.md S-03 |
| 11 | **HB-2** | belt face friction | function | silicone grip print (A-1; OD-HB4) | – | D | 1.5 | – | 0 | analysis/hipbelt_fit.md §10 |
| 12 | **CA-1** | PAHT-CF fatigue coupons, 0.30 then 0.40 | safety | H1 print release; body re-size at 0.40 | 60 | B | 6 | 222 | 15 | tests_physical/CA1_fatigue_rig.md; analysis/frame_comp_verdict.md §6 |
| 13 | **PT-6** | B-24 float stand-off link | safety | float mode (D-33) | – | A | 2.0 | – | 33 | analysis/bag_attachment.md §5 |
| 14 | **WP-2** | TPU 840D lash-tab slot pull (C-6 / O-15) | grams | C-6 lash tabs Hypalon -> TPU 840D | 6.2 | A | 0.7 | – | 5 | analysis/corrie_body.md §12.4; analysis/weight_pass_corrie.md C-6 |
| 15 | **FS-O5** | ULTRA 200X 50 mm strip tensile (C-5 / O-5) | grams | C-5 bag bottom 500D -> ULTRA 200X | 7.0 | A | 3.5 | – | 35 | analysis/fabric_swap_evidence.md O-5 |
| 16 | **HB-6** | M5 heat-set insert pull-out in printed PAHT-CF | safety | hip pivot mount on H1 | – | A | 1.5 | – | 5 | analysis/hipbelt_structural.md §8; analysis/fabric_swap_evidence.md (release gate) |
| 17 | **CA-5** | dry z 234 joint stub pulls + 1e5 cycle | safety | H1 print release | – | B | 4 | 27.8 | 40 | tests_physical/CA1_fatigue_rig.md §7; analysis/frame_h1.md §8; analysis/frame_comp_verdict.md §6 |
| 18 | **CA-3** | interlayer after 40 C water soak | safety | FI interlayer term; plug shear-out | – | B | 3 | 48 | 5 | tests_physical/CA1_fatigue_rig.md §7; analysis/frame_comp_A.md |
| 19 | **CA-4** | creep-rupture 40 C 8 h | safety | creep margin | – | B | 2 | 8 | 10 | tests_physical/CA1_fatigue_rig.md §7 |
| 20 | **CA-2** | anneal 90 C vs 120 C | function | nothing until a gain is measured | – | B | 3 | – | 10 | analysis/frame_comp_A.md; docs/research/frame_comp_A.md |
| 21 | **HB-4** | hipbelt stitched-ear joint | safety | belt B wing joint | – | A | 2 | – | 15 | analysis/hipbelt_structural.md §8 |
| 22 | **HB-5** | 7075-T6 1.2 bow-tie plate proof + 1e5 cycles | safety | C-1 + C-2 + C-3 | 25.0 | B | 4 | 27.8 | 45 | analysis/weight_c_structural.md §7 (supersedes analysis/hipbelt_structural.md §8 6061 version) |
| 23 | **PS-1** | pad-seat backer sag | safety | C-4 correction (pad seat) | – | D | 2 | 8 | 5 | analysis/weight_c_structural.md §7; analysis/corrie_body.md §12.4 |
| 24 | **T6** | crown-corner bond coupons (0.8 mm bondline) | safety | carbon crown corners + extension-post socket (P-1) | – | A | 4 | 24 | 30 | analysis/load_standard.md §5.3; print/frame/PRODUCTION.md (T6 note) |
| 25 | **T7** | bushing crush coupon | safety | crown bushing ring crush credit | – | A | 2 | – | 10 | analysis/load_standard.md §5.3 |
| 26 | **PT-4** | crown hood on an 18 mm tube, room and -10 C | safety | top anchor (B-19) | – | A | 3 | – | 10 | analysis/bag_attachment.md §5 |
| 27 | **T9** | loaded CG (+ 15 in, 30 kg meat check) | safety | HA-LS-1 rev C basis; before T1 | – | C | 4 | – | 0 | analysis/load_standard.md §5.3; analysis/corrie_body.md §11.4 |
| 28 | **T1** | static proof 150 / 300 / 225 lb (+ joint marks, yoke dial) | safety | first loaded carry | – | C | 4 | – | 0 | analysis/load_standard.md §5.3; analysis/frame_h1.md §8; analysis/weight_c_structural.md §7 |
| 29 | **CR-1** | crown retention hang 136 kg | safety | torso adjust | – | C | 1 | – | 0 | BUILD_PLAN.md §5 |
| 30 | **T3** | side-hill 240 lb at 25 deg | safety | first loaded carry | – | C | 3 | – | 0 | analysis/load_standard.md §5.3 |
| 31 | **T2** | meat / tall-load proof 300 lb | safety | first meat haul | – | C | 3 | – | 0 | analysis/load_standard.md §5.3 |
| 32 | **SP-1** | spreader bone-end proof 400 N | safety | spreader release | – | C | 1.5 | – | 5 | print/frame/PRODUCTION.md (QC proof load) |
| 33 | **T4a** | drop-step 2.0 g, 20 drops | safety | HA-LS-1 stumble level | – | C | 3 | – | 0 | analysis/load_standard.md §5.3 |
| 34 | **T4b** | single-foot set-down (+ dial on the branch) | safety | branch buckling | – | C | 2 | – | 0 | analysis/load_standard.md §5.3; analysis/frame_h1.md §8 |
| 35 | **T4c** | empty abuse drop 122 cm at -20 C | safety | cold-weather use | – | C | 2 | 4 | 0 | analysis/load_standard.md §5.3; analysis/frame_comp_verdict.md §6; analysis/printed_frame_study.md |
| 36 | **T5** | cycle 0.4 -> 1.6 g, 1e5 cycles (H1 body) | safety | frame release | – | C | 6 | 33 | 0 | analysis/load_standard.md §5.3; analysis/weight_c_structural.md §7 |
| 37 | **HB-1** | hipbelt pressure map, 3 testers | function | belt B fit (OD-HB1) | – | D | 4 | – | 0 | analysis/hipbelt_fit.md §10 |
| 38 | **RF-1** | back rail fit 130/70 on 3 backs (C-8) | grams | C-8 | 7.2 | D | 3 | – | 10 | analysis/corrie_body.md §12.4; analysis/weight_pass_corrie.md C-8 |
| 39 | **PT-7** | door zip proof | safety | CORRIE door | – | C | 2 | – | 0 | analysis/corrie_body.md §6 |
| 40 | **WP-4** | rain-fly fit | function | G-2 | – | E | 1 | – | 0 | analysis/corrie_body.md §12.4 |
| 41 | **WP-5** | TPU trim tick | grams | B-10 trims Hypalon -> TPU 840D | 12.8 | E | 0.5 | – | 5 | analysis/corrie_body.md §12.4 |
| 42 | **MH-1** | bag-on meat mode walk | function | R-09 | – | E | 1.5 | – | 0 | BUILD_PLAN.md §5a.2 |
| 43 | **MH-2** | frame-only meat haul (float / bag-off) | function | R-08, float meat limit 53 kg | – | E | 1.5 | – | 0 | BUILD_PLAN.md §5a.4 |
| 44 | **MH-3** | meat strap wash | function | R-12 | – | E | 0.5 | 2 | 0 | BUILD_PLAN.md §5a.5; DESIGN.md R-12 |
| 45 | **R28-1** | head-clearance photo | function | R-28 | – | E | 0.3 | – | 0 | BUILD_PLAN.md §5a.6; DESIGN.md R-28 |
| 46 | **HB-3** | hipbelt slip / settle hike | function | belt B | – | E | 1.5 | – | 0 | analysis/hipbelt_fit.md §10 |
| 47 | **T5f** | float US1 share 56 kg | safety | float meat limit 53 -> 56 kg | – | C | 4 | – | 0 | analysis/float_fea.md §3; analysis/load_standard.md §4.3 |
| 48 | **T2u** | ultimate demo 450 lb on P1 (destroys P1) | safety | none after it (last test) | – | C | 3 | – | 437 | analysis/load_standard.md §5.3 |
| | | **total** | | | | | **108.2** | **409** | **845.5** | |

Order inside phase 4 follows `load_standard.md` §5.3: T9 before T1, then T3, T2, T4a/b, T4c, T5 on P2, and T2u on P1
last. CR-1 (crown hang, `BUILD_PLAN.md` §5) and SP-1 (spreader bone end, `PRODUCTION.md` QC) go in the same sessions.

### What each result unlocks (the big ones)

| test | pass unlocks | fail means |
|---|---|---|
| PT-1, PT-2, PT-3, PT-6, MT-1..3 | sew the bag and harness as drawn | change the part or the sewing; re-test |
| CA-1 at 0.30 | print H1 as designed (body fatigue 1.28) | ratio ≥ 0.234: H1 still passes; < 0.234: re-size, about +20 g per −0.02 (`CA1_fatigue_rig.md` §6) |
| CA-1 at 0.40 | re-run the push: body about −50 to −70 g (`frame_h1.md` §6) | stay at 0.30 |
| CA-5 | print H1 with the bolted z 234 joint | B's 8-bolt flange, frame about 1058 g (+33 g, `frame_comp_verdict.md` §6) |
| HB-5 (7075 1.2) | keep package C plate, −25.0 g | back to 6061 1.5 (fails at ±2° slope, 0.94; use the ribbed 7075 fallback, 121 g) |
| T9 | rev C CG basis confirmed; > 10 mm below rev C lets the owner relax it | above rev C: stop, re-run `rev_c_verification` before T1 |
| T1–T5 | first loaded carry | stop, send the log |
| WP-1 / WP-3 / WP-5 | keep B-1 / A-2 / B-10 (54.6 g already taken in B.2) | add the grams back (binding, longer tails, Hypalon trims) |
| FS-O5 + PT-3 on ULTRA 200X | C-5 floor swap, −7.0 g | keep 500D |

## 4. Kits and shopping list

Prices: cited where a URL is given, otherwise **ASSUMPTION** (shop price, check at purchase). Prices checked
2026-11-10; several retailer pages show promotions, so the cited figure is the regular price where one was shown.

### 4.1 Kit A: pull bench (shared proof-test bench, `build_simplicity.md` S-14)

| item | spec | USD | source |
|---|---|---:|---|
| crane scale | 300 kg / 660 lb, 0.1 kg, tare | 59.00 | [Fruugo US listing][crane] (budget unit; PCE-CS 300 industrial at $193, [TestEquity][pce]) |
| come-along | 2 ton cable puller | 30.30 | [Home Depot, Big Red TR8021][hd-come] |
| ratchet straps | 1-1/2 in × 10 ft, 4-pack | 17.99 | [Harbor Freight 61303][hf-strap] |
| 5 mm hardened dowel pins | 50-pack, 22 mm | 11.79 | [Zoro][pins] |
| anchors | 4x4 lag-screwed into studs, or a tow hitch / tree | 40.00 | ASSUMPTION (`load_standard.md` §5.1 wall frame) |
| pin fixture | steel flat bar 40 × 6 × 300, M8 bolts | 20.00 | ASSUMPTION |
| bar clamps | 2 pairs aluminium 150 × 25 × 10, M6 bolts, grit cloth (PT-2, FS-O5) | 15.00 | ASSUMPTION |
| safety | glasses, gloves, moving blanket, back-up sling | 20.00 | ASSUMPTION |
| calibration jug | 20 L water container | 10.00 | ASSUMPTION |
| **kit A total** | | **224.08** | cited 119.08 |

Note: `build_simplicity.md` S-14 assumed **$60** for this bench. The cited parts alone are $119; the realistic total is
about $224 (§6, conflict 11).

### 4.2 Kit B: lever fatigue rig (CA-1, CA-3, CA-4, CA-5, CA-2, HB-5 cycles)

| item | USD | source |
|---|---:|---|
| the CA-1 rig as listed in `CA1_fatigue_rig.md` §5 (S-type 100 kg cell, HX711, Nano Every, 60 rpm worm motor, lever, pivot, spring, grips, base, coupon filament) | 250.00 | `CA1_fatigue_rig.md` §5 ($107 cited there, rest ASSUMPTION) |
| 200 kg S-type load cell for the CA-5 static pulls | 23.60 | [Makerfabs][lc] (same listing, 200 kg option) |
| 40 °C box: cooler + 60 W heater + thermostat (CA-4, CA-3 soak) | 35.00 | ASSUMPTION |
| 3-point bend fixture for the short-beam blocks (CA-3) | 10.00 | ASSUMPTION |
| **kit B total** | **318.60** | |

### 4.3 Kit C: frame test stand (`load_standard.md` §5.1; uses kit A's scale, come-along, straps and anchors)

| item | USD | source |
|---|---:|---|
| hip log (4x4 in closed-cell foam to ~36 in) | 10.00 | `load_standard.md` §5.1 (ASSUMPTION) |
| shoulder bar | 10.00 | `load_standard.md` §5.1 (ASSUMPTION) |
| snap shackle, 316 stainless swivel (drop release, T4a) | 14.39 | [Better Boat][shackle] |
| sand tube bags, 8 × 60 lb (450 lb for T2u) | 48.00 | ASSUMPTION ($6 each) |
| rubber gym mat 10–20 mm | 30.00 | `load_standard.md` §5.1 (ASSUMPTION) |
| 19 mm plywood sheet (T4c) | 40.00 | ASSUMPTION |
| T5 crank: 12 V wiper motor, supply, crank, bungee, counter | 70.00 | `load_standard.md` §5.1 (ASSUMPTION) |
| 22 mm hardwood dowel (SP-1 bone end) | 5.00 | ASSUMPTION |
| phone with phyphox | 0.00 | [phyphox][phyphox] (free) |
| **kit C total** | **227.39** | |

### 4.4 Kit D: measuring

| item | USD | source |
|---|---:|---|
| dial indicator 0–1 in with magnetic base | 39.95 | [Penn Tool, iGaging 34-101][dial] |
| digital caliper 6 in | 9.99 | [Harbor Freight 63586][caliper] |
| 8 force-sensitive resistors (HB-1, RF-1 pressure strips; read with the kit B Arduino) | 31.60 | [Adafruit 166][fsr] ($3.95 each) |
| 10× loupe | 8.00 | ASSUMPTION |
| conditioning box + magnesium nitrate | 15.00 | ASSUMPTION |
| **kit D total** | **104.54** | |

Pressure film instead of FSRs (Fujifilm Prescale LLLW) is about **€1275 per roll** ([listing][film]); not recommended
for a one-off.

### 4.5 Totals

| kit | USD | first needed |
|---|---:|---|
| A pull bench | 224.08 | weekend 1 |
| B lever fatigue rig | 318.60 | weekend 2 |
| C frame test stand | 227.39 | phase 4 (first-article frames) |
| D measuring | 104.54 | caliper + loupe weekend 1; the rest phase 2 |
| **all kits** | **874.61** | |
| test samples (48 active tests, from the register) | 408.50 | spread over all phases |
| sacrificial P1 frame (T2u) | 437.00 | `frame_h1.md` §5 |

## 5. Value ranking of the gram tests

Score = grams ÷ (sample cost $ + hands-on hours × $15). ASSUMPTION: $15 per owner hour, used only to rank. The top four
are the same four at $0 and at $30 per hour; only their order inside the group moves (at $0 CA-1 moves to 3rd, at $30
WP-5 moves to 1st). The bottom four keep their places except RF-1 / HB-5 swapping at $0.

| rank | test | grams | samples $ | hands-on h | g per $-eq | note |
|---:|---|---:|---:|---:|---:|---|
| 1 | WP-3 gloved tail | 5.4 | 0 | 0.3 | 1.20 | protects A-2 (already in B.2) |
| 2 | WP-1 wash fray | 36.4 | 5 | 2.0 | 1.04 | protects B-1 (already in B.2) |
| 3 | WP-5 trim tick | 12.8 | 5 | 0.5 | 1.02 | protects B-10 (already in B.2) |
| 4 | CA-1 at 0.40 | 60 | 15 | 6 | 0.57 | also the top safety gate; 60 g only if 0.40 passes |
| 5 | WP-2 slot pull | 6.2 | 5 | 0.7 | 0.40 | C-6 lash tabs |
| 6 | HB-5 7075 plate | 25.0 | 45 | 4 | 0.24 | also a safety gate |
| 7 | RF-1 rail fit | 7.2 | 10 | 3 | 0.13 | C-8 rails |
| 8 | FS-O5 ULTRA strip | 7.0 | 35 | 3.5 | 0.08 | C-5 floor; needs PT-3 on ULTRA too |

Grams are from `weight_pass_corrie.md` (package rows A-2, B-1, B-10, C-5, C-6, C-8), `weight_c_structural.md`
(C-1+C-2+C-3 = 25.0 g) and `frame_h1.md` §6 (CA-1, midpoint of −50 to −70 g).

## 6. Duplicates and conflicting definitions

| # | test | documents | difference | resolved here as |
|---:|---|---|---|---|
| 1 | MT-1..3 (R-29 meat proof) | `BUILD_PLAN.md` §5a.0 vs `meat_haul_modes.md` | 910 N vs 830 N | **910 N** (higher; = 1.5 × 605 N) |
| 2 | CA-5 static pass | `CA1_fatigue_rig.md` §7 vs `frame_comp_verdict.md` §6 | 1.5 × 2933 N (H1) vs 1.5 × 2894 N (team A) | **2933 N** (H1 `frame_h1_results.json`): mean ≥ 4400 N, lowest ≥ 3666 N |
| 3 | CA-5 cycle force | same two | "1.6 g static-carry stub force" (no number) vs 0 → 1543 N (team A) | **1543 N** until the structural-fea-engineer states the H1 value |
| 4 | CA-5 cycle rig | same two | CA lever rig vs "the T5 rig" | **CA lever rig** (it has the load cell and the dial) |
| 5 | T4c temperature | `load_standard.md` §5.3 vs `frame_comp_verdict.md` §6, `printed_frame_study.md`, `print/frame_h1/README.md` | room temperature vs −20 °C after a 4 h soak | **−20 °C** (stricter; printed nylon is brittle cold) |
| 6 | pad-seat sag (PS-1) | `corrie_body.md` §12.4 vs `weight_c_structural.md` §7 | 413 N 8 h, "no contact" vs 413 N 8 h then 661 N, sag < 3 mm, no contact at 4.5 mm | **weight_c version** (superset) |
| 7 | HB-5 | `hipbelt_structural.md` §8 vs `weight_c_structural.md` §7 | 6061-T6 1.5 plate vs 7075-T6 1.2 with D28 hub and 2 × Ø31 holes | **7075 1.2** (adopted 2026-11-09) |
| 8 | T7 specimen | `load_standard.md` §5.3 | CFRP stay offcut with a wrap collar; H1 carries the bushing in a printed PAHT-CF sleeve | **printed H1 sleeve segment** |
| 9 | T6 joint types | `load_standard.md` §5.3 | (a) bar coped to a stay, (b) collar on a stay end | only the **crown corner** (0.8 mm bondline, incl. the P-1 post socket); (b) retired |
| 10 | T5 article | `weight_c_structural.md` §7 | "on the C-9 body" | **H1 body** (H1 replaced C-9) |
| 11 | S-14 bench cost | `build_simplicity.md` | $60 ASSUMPTION | about **$224** (§4.1, $119 cited) |
| 12 | HB-1 pass | `hipbelt_fit.md` §10 | "B peak ≤ current − 15 %" needs the old belt built too | kept; flagged (owner decision, §9) |
| 13 | HB-4 sample count | `hipbelt_structural.md` §8 | one ear | kept at 1; 3 recommended for scatter |
| 14 | 15 in CG check | `corrie_body.md` §11.4, `bag_comp_D.md` MOD-5, `load_standard.md` T9 | same measurement, 30 kg vs 68 kg | **merged into T9**: add a 30 kg IM1-IM3 run at 15 in |
| 15 | WP-1 / R-12 / S-03 gate | `corrie_body.md`, `weight_pass_corrie.md`, `build_simplicity.md` | same wash-swatch test under three names | **WP-1** |
| 16 | fatigue, interlayer, boss and insert coupons | `frame_comp_B.md` CT-B1/2/3/5, `frame_comp_d.md` D-I1, `frame_comp_A.md` CA list | same quantities as CA-1, CA-3, CA-5, HB-6 | **merged** (§7) |

## 7. Retired and merged tests (not to be run)

| id | status | what | defined in | why |
|---|---|---|---|---|
| T6(b) | RETIRED | wrap collar over a stay end | analysis/load_standard.md §5.3 | H1 stays are printed; no collar on a stay |
| T8 | RETIRED | d6L barrier bone-end | analysis/spreader_layout.md | d6L rejected 2026-11-05; SP-1 covers Sandwich v2 |
| MH-0 | RETIRED | girth-hitch 6 stubs | BUILD_PLAN.md §5a.1 | stubs became fairlead eyes |
| MH-bay | RETIRED | bay (between) mode | BUILD_PLAN.md §5a.3 | between mode retired for float (D-33) |
| CORRIE-11.4 | MERGED->T9 | 15 in plumb-line CG, 30 kg | analysis/corrie_body.md §11.4, §12.4 | same measurement as T9 |
| CT-B1 | MERGED->CA-1 | PAHT-CF fatigue (frame B) | analysis/frame_comp_B.md §6 | same quantity |
| CT-B2 | MERGED->CA-3 | interlayer shear (frame B) | analysis/frame_comp_B.md §6 | same quantity |
| CT-B3 | MERGED->CA-5 | one-boss pull-through (frame B) | analysis/frame_comp_B.md §6 | same failure mode on H1 |
| CT-B4 | RETIRED | z 220 stub 4-point bend (frame B) | analysis/frame_comp_B.md §6 | frame B not adopted |
| CT-B5 | MERGED->HB-6 | insert pull-out (frame B) | analysis/frame_comp_B.md §6 | same part type |
| D-I1 | MERGED->HB-6 | M5 insert pull-out (frame D, SLS) | analysis/frame_comp_d.md §4 | frame D not adopted; HB-6 covers PAHT-CF |
| D-C1 | RETIRED | SLS PA12 coupon (frame D) | analysis/frame_comp_d.md | frame D not adopted |
| D-F1 | RETIRED | SLS PA12 coupon (frame D) | analysis/frame_comp_d.md | frame D not adopted |
| D-J1 | RETIRED | SLS PA12 coupon (frame D) | analysis/frame_comp_d.md | frame D not adopted |
| RC-1 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-2 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-2f | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-3 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-4 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-5 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| RC-6 | RETIRED | frame C ROD coupon | analysis/frame_comp_C.md | frame C not adopted |
| E-1 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-2 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-3 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-4 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-5 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-6 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| E-7 | RETIRED | frame E LOOM coupon | docs/research/frame_comp_E.md | frame E not adopted |
| MOD-1 | RETIRED | bag comp D module test | analysis/bag_comp_D.md | entry not adopted; reactivate if BL-011 merges it |
| MOD-2 | RETIRED | bag comp D module test | analysis/bag_comp_D.md | entry not adopted; reactivate if BL-011 merges it |
| MOD-3 | RETIRED | bag comp D module test | analysis/bag_comp_D.md | entry not adopted; reactivate if BL-011 merges it |
| MOD-4 | RETIRED | bag comp D module test | analysis/bag_comp_D.md | entry not adopted; reactivate if BL-011 merges it |
| MOD-5 | MERGED->T9 | 15 in CG, 30 kg (bag comp D) | analysis/bag_comp_D.md | same as T9 add-on |
| ZP-1 | RETIRED | lid zip drop (bag comp C) | analysis/bag_comp_C.md | entry not adopted; reactivate if BL-011 merges it |
| C9-fit | RETIRED | C-9 stay-foot boot fit | analysis/corrie_body.md §12.5 | C-9 body superseded by H1; boot fit is an assembly step |

A retired bag-competition test comes back only if BL-011 ("CORRIE F") merges that entry's feature.

## 8. Log template (one line per pull or step)

```
date | test id | sample # | set-up note | target (kg on scale / N) | peak reached | hold s | result (hold / slip mm / break) | where it broke | photo #
```

For frame tests use the `load_standard.md` §5.4 template. For CA coupons, the rig writes its own CSV
(`CA1_fatigue_rig.md` §4).

## 9. Assumptions that govern this plan

| assumption | where | test that settles it |
|---|---|---|
| ratchet strap working limit = 1/3 of "1000 lb capacity" (1480 N) | §1 | read the strap's label; keep straps out of high loads regardless |
| a lag-screwed 4x4 into two studs holds 3 kN | §2.1 | calibration pull: the anchor must not move at 280 kg |
| the budget crane scale is linear to 280 kg | §2.1, §4.1 | 20 L jug check at 20 kg; cross-check at about 136 kg with 7 jugs if available |
| tilt-board static μ stands in for the D1894 sled pull | §2.4 HB-2 | if the result is within ±0.05 of 0.45, repeat with a sled pulled through the 100 kg cell of kit B |
| R-12 wash = normal cold cycle | §2.3 | none (owner's call; a hot wash is harsher) |
| household freezer reaches −20 °C (T4c) / −10 °C (PT-4) | §6 | freezer thermometer; if it only reaches −18 °C, record it |
| $15 per owner hour (ranking only) | §5 | none; the top-four group is the same from $0 to $30 |
| HB-7 pass 426 N = 1.5 × 284 N | §2.2 | structural-fea-engineer to confirm |
| CA-5 cycle force 1543 N (team A value) | §6 | structural-fea-engineer to state the H1 value |
| sample prices ($3–6 per hook, $4 per cam, offcuts) | register | receipts |

## 10. Sources

Test definitions (internal): `designs/pack_5200/tests_physical/CA1_fatigue_rig.md`; `designs/pack_5200/analysis/`
`load_standard.md`, `frame_h1.md`, `frame_comp_verdict.md`, `frame_comp_A.md`, `frame_comp_B.md`, `frame_comp_C.md`,
`frame_comp_d.md`, `hipbelt_fit.md`, `hipbelt_structural.md`, `weight_c_structural.md`, `weight_pass_corrie.md`,
`corrie_body.md`, `float_fea.md`, `bag_attachment.md`, `meat_haul_modes.md`, `fabric_swap_evidence.md`,
`build_simplicity.md`, `spreader_layout.md`, `printed_frame_study.md`, `bag_comp_C.md`, `bag_comp_D.md`;
`docs/research/frame_comp_E.md`; `designs/pack_5200/BUILD_PLAN.md`; `designs/pack_5200/print/frame/PRODUCTION.md`;
`designs/pack_5200/print/frame_h1/README.md`.

Prices (fetched 2026-11-10 through search results; retailer pages, not quotes):

[crane]: https://www.fruugo.us/300-kg-660-lbs-digital-lcd-hanging-scale-mini-industrial-crane-scale-with-hook-and-tare-function/p-376963170
[pce]: https://www.testequity.com/product/20000641-PCE-CS-300
[hd-come]: https://homedepot.com/p/Big-Red-2-Ton-Come-Along-Cable-Puller-with-2-Hooks-TR8021/100594355
[hf-strap]: https://go.harborfreight.com/61303/
[pins]: https://www.zoro.com/zoro-select-dowel-pin-harden-stl-m5x22mm-pk50-dp5005022-050p1/i/G3163027
[lc]: https://www.makerfabs.com/s-type-load-cell-100kg-200kg-300kg-500kg-1.html
[shackle]: https://betterboat.com/products/stainless-steel-swivel-snap-shackle
[dial]: https://www.penntoolco.com/igaging-digital-indicator-w-magnetic-base-set-34-101/
[caliper]: https://go.harborfreight.com/63586
[fsr]: https://www.adafruit.com/products/166
[film]: https://www.desertcart.hr/products/445149960-fujifilm-prescale-ultra-low-lllw-3lw-surface-pressure-mapping-pressure.md
[phyphox]: https://apps.apple.com/app/phyphox/id1127319693

- Crane scale: [Fruugo US][crane] $59.00; [TestEquity PCE-CS 300][pce] $193.00.
- Come-along: [Home Depot Big Red 2 ton][hd-come] $30.30.
- Ratchet straps: [Harbor Freight 61303][hf-strap] $17.99 per 4-pack, "1000 lb capacity".
- Dowel pins: [Zoro M5 × 22 hardened, 50-pack][pins] $11.79.
- 200 kg S-type cell: [Makerfabs][lc] $23.60 (multi-capacity listing; the page carried a 2025 holiday notice, so
  confirm the price).
- Snap shackle: [Better Boat 316 swivel][shackle] $14.39 sale ($17.99 regular).
- Dial indicator: [Penn Tool iGaging 34-101][dial] $39.95.
- Caliper: [Harbor Freight 63586][caliper] $9.99.
- FSR: [Adafruit 166][fsr] $3.95.
- Pressure film: [Fujifilm Prescale LLLW roll][film] €1274.88 (secondary: retailer, not Fujifilm).
- phyphox: free, open source ([App Store][phyphox]).
