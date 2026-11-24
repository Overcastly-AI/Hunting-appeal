# Iteration 1, system weight: options (BL-062)

Owner: pack-designer. Date: 2026-11-24. Code: `designs/pack_5200/iter1/system/iter1_weight.py` (tests `tests/test_iter1_weight.py`); numbers: `iter1_weight.json`. Research: `docs/research/weight_iter1.md`. Base configuration, belt M, crown kit M, as the roll-up (`analysis/weight_rollup_v2.md`). **Generated: re-run the code rather than quoting this file after any change.** Proposals only: no released pattern, ledger config or roll-up step is changed.

Scope: everything except the frame body and its pins and hardware (the structural track is working the frame). The spreader is listed but not touched (structural part, owner decision).

## 0. Answer

- Today: proven now **4038.1 g (8.90 lb)**; after the gated tests **3450.9 g (7.61 lb)**. Of that, the frame is 1387.1 g and everything in this ticket's scope is **2063.8 g**.
- In scope we are already level with the leaders (research section 2): back panel + spreader + belt + harness after tests 954 g against KUIU ICON 6's belt + harness + hip pouches at about 1052 g (inference). The bag side is lighter than SG / Exo bags. The 6.6 lb gap is the frame body, so these options can only shave it.
- **Option A, Same look, lighter hidden materials:** base **-82.3 g (-2.9 oz)** -> after tests 3368.6 g (7.43 lb); as hunted -82.3 g; cost +8.37 USD a pack; worst risk medium; strong: PASS on paper (each lever gated by its test). Still 375 g over 6.6 lb.
- **Option B, Modular: A + lighter base, pockets as shipped add-ons:** base **-139.2 g (-4.9 oz)** -> after tests 3311.7 g (7.30 lb); as hunted -48.6 g; cost +10.12 USD a pack; worst risk medium; strong: PASS on paper (each lever gated by its test). Still 318 g over 6.6 lb.
- **Option C, Aggressive: B + Dyneema wraps, ULTRAGrid straps / belt, #8 door, required pockets modular:** base **-232.1 g (-8.2 oz)** -> after tests 3218.8 g (7.10 lb); as hunted -82.7 g; cost +14.72 USD a pack; worst risk high; strong: PASS on paper; N6 pending its slip test. Still 225 g over 6.6 lb.
- **Recommendation: option A.** It is the only package whose grams are real (not a reporting move), it changes nothing the hunter sees except a better-matched collar colour, and every lever has a known fallback. Take B's pocket moves only if the owner wants the base headline; they cost grams as hunted.
- Proven now does not move for any material lever: each is gated by a test with today's part as the fallback (BL-014 rule). The modular moves are an owner decision with no test; adopted, they move proven now as well (B: 3981.2 g, C: 3939.2 g).

## 1. Pareto: top 15 non-frame items (after tests, base, belt M)

| # | item | after tests g | proven now g | best lighter alternative (keeps the strength gate) | g |
|---:|---|---:|---:|---|---:|
| 1 | back panel: mesh, rail foam, backer strip, sleeves, upper pad | 201.3 | 251.3 | N1: spacer mesh 380 -> 230 g/m2 on the back panel BP-01, crown pad face BP-03 and J-strap faces HS-J2 | -33.4 |
| 2 | internal meat straps IM1-IM3: webbing, cams, hooks, eyes, ports | 188.3 | 275.6 | none: 25 mm already (A_imus); the 38 mm eyes are captive in the print (R-1); aluminium cams owner-fixed (O-cams fails the gate: ladder-lock slip 490 N < 720 N) | +0.0 |
| 3 | back spreader, Sandwich v2 (structural) | 162.3 | 162.3 | none: structural, owner decision Sandwich v2 at FPF 1.25 / fatigue 1.09 (R-3); structural-fea-engineer | +0.0 |
| 4 | shell panels: B-01, gussets, door, hinge band, floor, camo blade + kick bands | 144.9 | 198.9 | none: already ULTRAGrid / ULTRA 200X / HyperD 300 in after tests; the only lighter Challenge cloth (ULTRA 100X, 122 g/m2) is a louder PET laminate only 8 % lighter (research 3.1); DCF breaks quiet | +0.0 |
| 5 | roll-top: collars, hem, HDPE strip, clips | 132.3 | 149.3 | N4: frame-side roll-top collar B-06f ULTRA 200X -> 70D ripstop (the aft collar B-06 is already 70D) | -8.2 |
| 6 | belt wings + lumbar: foams, stiffener, mesh faces, shells | 129.6 | 183.4 | N2: belt wing and lumbar mesh faces 380 -> 320 g/m2 (hip faces keep a dense mesh) | -6.3 |
| 7 | under-strap cradle US1/US2: webbing, cams, backstops, anchors | 120.1 | 148.7 | N3: US1/US2 tri-glide backstops stainless 11 g -> titanium 4 g (2) | -14.0 |
| 8 | haul wraps W1-W3: webbing, rated hooks, heavy ladder locks, keepers | 96.8 | 96.8 | N6: haul-wrap webbing W1-W3 (cut for carry) polyester 18 g/m -> thin Dyneema 25 mm 10.2 g/m | -20.0 |
| 9 | belt 50 mm closure, 2:1 pull, stabilizers | 92.4 | 110.4 | none: 50 mm buckle and 2:1 already re-booked (C8, BL-006 b); heavy lock legs are the HB-7 slip parts | +0.0 |
| 10 | belt plate, hub, latch, doublers (rev C load path) | 85.7 | 85.7 | none: rev C fixes C-1..3 (7075 plate) (R-6); structural | +0.0 |
| 11 | port guys, B-25 bridle, B-22 tabs, guy hardware | 68.9 | 59.4 | none: small parts at the 1.36 minimum (B-25 bridle tab): not touched | +0.0 |
| 12 | J-straps: shell, mesh face, foams | 68.7 | 91.0 | N1: spacer mesh 380 -> 230 g/m2 on the back panel BP-01, crown pad face BP-03 and J-strap faces HS-J2 | -11.7 |
| 13 | yoke plate + cover (rev C fix C-7) | 64.4 | 64.4 | none: rev C fix C-7 (R-6) | +0.0 |
| 14 | D2 door zip #10 + 2 sliders + cord pulls | 61.4 | 69.4 | O-slider: D2 door with one slider instead of two | -15.0 |
| 15 | lumbar pad seat | 56.4 | 69.0 | none: pad backer is a rev C fix (C-4); cord tie already in A_f | +0.0 |

Items come from the roll-up rows by a fixed rule list (`RULES`); every non-frame row lands in exactly one item (tested). Proven-now masses differ where a gated step (A) already changes the item: wings, hood, 38 -> 25 mm IM/US, fabric swaps, BL-037 picks.

## 2. Levers

| key | status | change | base g | as hunted g | cost USD | risk | strength | durability | test that retires the risk | look | records needed |
|---|---|---|---:|---:|---:|---|---|---|---|---|---|
| N1 | new | spacer mesh 380 -> 230 g/m2 on the back panel BP-01, crown pad face BP-03 and J-strap faces HS-J2 | -45.1 | -45.1 | -0.65 | medium | no load path (body-contact face); no HA-LS-1 row or bag load point touches it | thinner (3.0 vs 4.5 mm) face: less air gap, faster wear where the pack rubs. The record's own note says the mesh abrades in 1-2 seasons at the hip, so the hip faces are left out (N2) | MESH-1 Martindale (ASTM D4966) both meshes to 20 000 rev + MESH-2 3-tester 2 h sweat carry at 30 kg (BP-3 back-pressure strips under the rails); fallback today's mesh | none visible from outside (wearer face); finer texture on the back panel | spacer_mesh_3d_230 (3 mm, 230 g/m2): gsm, thickness, compression, abrasion, roll width, price |
| N2 | new | belt wing and lumbar mesh faces 380 -> 320 g/m2 (hip faces keep a dense mesh) | -6.3 | -6.3 | +0.28 | low | no load path (face fabric) | 320 g/m2 is a 3 mm inelastic mesh sold for backpacks; hip abrasion is the risk | MESH-1 (same lot) + HB-1 hipbelt pressure / hold with the 3 mm face; fallback today's mesh | none visible | spacer_mesh_3d_320 (3 mm inelastic): gsm (listing 320 vs page title 390), abrasion, roll width |
| N3 | new | US1/US2 tri-glide backstops stainless 11 g -> titanium 4 g (2) | -14.0 | -14.0 | +17.24 | medium | the US rows are governed by the 25 mm cam (1100 N slip, margin 1.53 on 720 N) and the box-X (4.43); the backstop is not credited in any SF row. It must still stop a slipping cam: same US-BS gate as the stainless part. Ti-6Al-4V (record) is stronger than 304 per section | titanium does not corrode; webbing wear on a thinner bar edge unknown | US-BS run on the Ti tri-glide (cam slipped to the backstop, 1080 N hold, dry / wet / -20 C, 5 samples) + weigh 5; fallback stainless | none (inside the cradle) | triglide_25mm_ti: mass (4 g secondary), bar section, rated hold |
| N4 | new | frame-side roll-top collar B-06f ULTRA 200X -> 70D ripstop (the aft collar B-06 is already 70D) | -8.2 | -8.2 | -7.60 | medium | no load point: the roll-top clips RT / RTM sit on the hem B-07 and the gusset B-03, not on B-06f | B-06f rides against the crown top bar and the B-25 bridle when rolled: 70D (Martindale >10 000) against ULTRA's Taber 4400 is a real abrasion step down | AB-2 crown-bar rub: a rolled 70D collar on a bar offcut with the bridle, 5 000 cycles of the pack's pitch swing, no hole; fallback ULTRA 200X | better: 70D comes in the solid house colours (ULTRA has few colours, record ir_notes) | - |
| N5 | new | rail sleeves BP-05 (pair) and crown pad back BP-07: Robic 210D -> 70D ripstop | -8.7 | -8.7 | -0.90 | low | no rated load: the sleeve holds the rail foam and the carbon backer on the stay line | the sleeve back sits between the backer strip and the stay; carbon-edge chafe on 70D is the risk | SLV-1: sleeve on the backer strip edge, 10 000 rub cycles at the rev C skin pressure, no wear-through; fallback 210D | none (hidden) | - |
| N6 | new | haul-wrap webbing W1-W3 (cut for carry) polyester 18 g/m -> thin Dyneema 25 mm 10.2 g/m | -20.0 | -20.0 | +6.30 | high | webbing break 11768 N vs 225 N factored (S9): x52; box-X 3186 N is the thread path (unchanged); the governing part is the heavy ladder lock slip (490 N ASSUMPTION on polyester): unknown on 0.7 mm UHMWPE, which the maker says suits buckles only in limited use. Gate before booking | UHMWPE creeps under constant load and is slick in a ladder lock; it twists; cuts need a hot knife | LL-D: 5 heavy ladder locks on the Dyneema webbing, 338 N proof (W-PULL) dry / wet / -20 C, slip < 5 mm; W-box pull to 338 N on a 0.7 mm specimen; fallback polyester | black only (Dyneema dyes poorly); thinner, slightly sheened straps on the outside of the bag | dyneema_webbing_25mm_thin: g/m, break, ladder-lock slip (Extremtextil art. 72979) |
| N7 | new | J-strap shells HS-J1 and belt wing / lumbar shells: 330D CORDURA -> ULTRAGrid 210D (the bag-body cloth) | -8.8 | -8.8 | +0.83 | medium | the strap and belt shells carry part of the strap and wing tension; ULTRAGrid's grab (1300 / 1100 N) is above 330D's (1000 / 800 N), but both are record ESTIMATEs / ASSUMPTIONs, so a seam pull decides | Taber 1100 vs 330D 800 (records): level or better; UHMWPE grid yarns need tighter SPI and bartacks | SH-1 strap-to-yoke and wing-root seam pulls on ULTRAGrid (1.5 x the HS-1 strap load), plus the owner swatch already gated for the bag body (A_fab); fallback 330D | grid lines visible on straps and belt; matches the bag body (one cloth language) | - |
| G-3 | BL-037 option | door chain #10 -> #8 coil (sliders unchanged) | -7.1 | -7.1 | -1.42 | low | door zip unloaded (SF 78 on #10, about 61 on #8; weight_push G-3) | #8 under gloved hands and grit; leaders use #10 on the main zip | PT-7 door zip proof on #8 + slider_8 record | slightly narrower zip line | slider_8 (#8 slider mass and pull) |
| M1 | modular (owner) | FP-L/R hip-reach pockets: sewn -> clip-on module shipped in the box (4 loops on the pack, 4 toggle tabs on the module) | -27.7 | +16.9 | +0.87 | low | no load path | a toggle can be lost; spare toggle in the box | MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first | cleaner base silhouette without the pocket; visible empty loops | - |
| M2 | modular (owner) | IMP-4 door kill-kit pocket: sewn -> clip-on module shipped in the box (2 loops on the pack, 2 toggle tabs on the module) | -21.0 | +8.4 | +0.44 | low | no load path | a toggle can be lost; spare toggle in the box | MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first | cleaner base silhouette without the pocket; visible empty loops | - |
| M3 | modular (owner) | IMP-6 phone pocket (clips to the J-strap): sewn -> clip-on module shipped in the box (2 loops on the pack, 2 toggle tabs on the module) | -8.2 | +8.4 | +0.44 | low | no load path | a toggle can be lost; spare toggle in the box | MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first | cleaner base silhouette without the pocket; visible empty loops | - |
| M4 | modular (owner) | IMP-2 hydration sleeve (hangs on 2 loops above IM3): sewn -> clip-on module shipped in the box (2 loops on the pack, 2 toggle tabs on the module) | -29.7 | +8.4 | +0.44 | low | no load path | a toggle can be lost; spare toggle in the box | MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first | cleaner base silhouette without the pocket; visible empty loops | - |
| M5 | modular (owner) | IMP-5L hipbelt pocket (removable, as KUIU): sewn -> clip-on module shipped in the box (2 loops on the pack, 2 toggle tabs on the module) | -12.3 | +8.4 | +0.44 | low | no load path | a toggle can be lost; spare toggle in the box | MOD-1 gloved fit / remove x 10 and a 5 km brush walk with no loss; owner decision first | cleaner base silhouette without the pocket; visible empty loops | - |
| O-cams | BL-037 owner option | IM1-IM3 and US1/US2 aluminium cams -> heavy 25 mm ladder locks | -26.0 | -26.0 | -117.00 | medium | IM / US hardware margin moves from the cam (1100 N, 1.82 / 1.53) to the ladder-lock slip (490 N ASSUMPTION): 490 / 720 = 0.68 on the US rows, BELOW 1.0. Fails the gate unless a rated lock is found; listed for completeness only | - | MT-1..3 with ladder locks | none | - |
| O-slider | BL-037 owner option | D2 door with one slider instead of two | -15.0 | -15.0 | -1.99 | low | no load path | - | owner decision | none | - |

Status: **new** = not in any earlier ticket; **BL-037 option / owner option** = listed in `weight_push.md`, not picked, repeated here only so the packages are complete (none of BL-037's 119 g of picks is re-proposed); **modular** = a sewn feature becomes a clip-on module shipped in the box (owner decision).

## 3. Strength gate (bag load points, `mfg_corrie_f_rev3.load_points`)

Baseline: 32 load points, min SF **1.36** at B-25 bridle toggle tab (rubric baseline 1.36). No lever touches the B-25 bridle, the hinge eye, the IM3 tongue or the B-17 tab. Rows a lever touches:

| lever | load point | factored N | SF (sewn) | hardware margin before | after | verdict |
|---|---|---:|---:|---:|---:|---|
| N3 | US cam anchor | 720 | 4.43 | 1.53 | 1.53 | PASS |
| N3 | US1 sewn eye | 720 | 4.43 | 1.53 | 1.53 | PASS |
| N3 | US2 sewn eye | 720 | 4.43 | 1.53 | 1.53 | PASS |
| N6 | W1 G-hook end | 225 | 14.16 | 2.18 | test | PENDING test |
| N6 | W2 G-hook end | 225 | 14.16 | 2.18 | test | PENDING test |
| N6 | W3 G-hook end | 225 | 14.16 | 2.18 | test | PENDING test |
| N6 | W haul extender | 225 | 14.16 | 4.0 | test | PENDING test |
| O-cams | IM1 end loop | 605 | 5.27 | 1.82 | 0.81 | FAIL |
| O-cams | IM2 end loop | 605 | 5.27 | 1.82 | 0.81 | FAIL |
| O-cams | IM3 end loop | 605 | 5.27 | 1.82 | 0.81 | FAIL |
| O-cams | IM cam anchor tab | 605 | 5.27 | 1.82 | 0.81 | FAIL |
| O-cams | US cam anchor | 720 | 4.43 | 1.53 | 0.68 | FAIL |
| O-cams | US1 sewn eye | 720 | 4.43 | 1.53 | 0.68 | FAIL |
| O-cams | US2 sewn eye | 720 | 4.43 | 1.53 | 0.68 | FAIL |

- N3: the backstop is not a credited part of any row; the cam governs (1.53) before and after.
- N6: the box-X and the webbing (x52 on 225 N) pass; the ladder-lock slip on 0.7 mm UHMWPE is unknown, so the verdict is PENDING LL-D with polyester as the fallback.
- O-cams fails (US rows 490 / 720 N = 0.68 on the ASSUMPTION slip): kept out of every option.
- Hipbelt and harness structure (plates, webbing, lock legs) is untouched by every option. N7 changes the strap and wing shell cloth, gated by SH-1 seam pulls; HA-LS-1 frame rows are out of scope and unchanged.

## 4. Options scored on the rubric

| | A | B | C |
|---|---|---|---|
| levers | N1, N2, N3, N4, N5 | N1, N2, N3, N4, N5, M1, M2, M3 | N1, N2, N3, N4, N5, M1, M2, M3, N6, N7, G-3, M4, M5, O-slider |
| **1 strong (gate)** | PASS on paper (each lever gated by its test) | PASS on paper (each lever gated by its test) | PASS on paper; N6 pending its slip test |
| **2 lighter, base g** | -82.3 (-2.9 oz) | -139.2 (-4.9 oz) | -232.1 (-8.2 oz) |
| of which materials / modular | -82.3 / +0.0 | -82.3 / -56.9 | -133.2 / -98.9 |
| after tests, base | 3368.6 (7.43 lb) | 3311.7 (7.30 lb) | 3218.8 (7.10 lb) |
| as hunted change | -82.3 | -48.6 | -82.7 |
| gap to 6.6 lb | 375 | 318 | 225 |
| cost per pack (USD) | +8.37 | +10.12 | +14.72 |
| worst durability risk | medium | medium | high |
| **3 looks** (visible changes) | N1: none visible from outside (wearer face); finer texture on the back panel; N4: better: 70D comes in the solid house colours (ULTRA has few colours, record ir_notes) | N1: none visible from outside (wearer face); finer texture on the back panel; N4: better: 70D comes in the solid house colours (ULTRA has few colours, record ir_notes); M1/M2/M3: cleaner base silhouette without the pocket; visible empty loops | N1: none visible from outside (wearer face); finer texture on the back panel; N4: better: 70D comes in the solid house colours (ULTRA has few colours, record ir_notes); M1/M2/M3/M4/M5: cleaner base silhouette without the pocket; visible empty loops; N6: black only (Dyneema dyes poorly); thinner, slightly sheened straps on the outside of the bag; N7: grid lines visible on straps and belt; matches the bag body (one cloth language); G-3: slightly narrower zip line |
| physical tests | AB-2, MESH-1, SLV-1, US-BS | AB-2, MESH-1, MOD-1, SLV-1, US-BS | AB-2, LL-D, MESH-1, MOD-1, PT-7, SH-1, SLV-1, US-BS, owner |

Looks is listed, not scored: the rubric scores it on renders with a design-reviewer pass, and none of A's changes is visible on a render. B's empty loops and C's black Dyneema wraps and grid-line straps need A/B renders before the owner picks.

**Recommendation: option A** (-82.3 g base, all real mass, +8.37 USD). Reasons: (1) it passes the strength gate with no load point touched except N3's uncredited backstop; (2) its grams survive the as-hunted view, while B's and C's pocket moves add +33.7 / +50.5 g as hunted (loops and toggles) for the base they take off; (3) no visible change except a collar that can now match the house colour. N6 (Dyneema wraps) and N7 (ULTRAGrid straps / belt) are worth testing in the same lot. If LL-D and SH-1 pass, they add -28.8 g with no feature loss.

## 5. Honest reading against the target

Even option C leaves 225 g over 6.6 lb after every test passes. The frame body (1387 g after tests, against KUIU's 388 g frame) is the lever, as BL-037 found. Outside the frame there is no architecture lever left that keeps the owner-frozen features: meat straps, under-straps, bow carry, the fly pocket and the quiet fabrics are where the remaining non-frame mass sits, and the leaders carry the same functions in their frame weights.

## 6. Assumptions that govern

- ASSUMPTION MESH-230: a 3 mm, 230 g/m2 spacer mesh exists at the listed weight and wears acceptably on the back and straps (secondary listing; no record). Settled by: materials record + MESH-1 / MESH-2.
- ASSUMPTION MESH-320: the 3 mm inelastic mesh is 320 g/m2 (category listing) not 390 (page title). Settled by: weigh a 1 m swatch.
- ASSUMPTION TI-TG: a 25 mm Ti tri-glide weighs 4 g (secondary) and holds a slipped cam like the stainless part. Settled by: weigh 5 + US-BS on Ti.
- ASSUMPTION TI-TG-COST: USD 12 each (price not found). Settled by: quote.
- ASSUMPTION TAB-L: a clip-on pocket's toggle tab is 25 mm webbing x 60 mm + one POM toggle. Settled by: pattern-maker draft.
- ASSUMPTION FX: USD 1.09 per EUR. Settled by: -.
- ASSUMPTION MESH-ROLL: the 320 g/m2 mesh roll is 1.6 m wide (not on the listing). Settled by: supplier.

## 7. Screenshots

- `outputs/screens/20261124_iter1_weight_1.png`
- `outputs/screens/20261124_iter1_weight_2.png`
