# Pack 5200: alternative main-bag bodies vs SPINE (study, 2026-11-07)

Owner: pack-designer. **Study only.** The released v3.1 SPINE geometry, patterns and YAML are unchanged
(`geometry.yaml`, `panels.yaml`, `patterns_v31.py` are only read). Concepts live in
`designs/pack_5200/concepts/` (`bag_concepts.py` = geometry, flat patterns, metrics, scores; `render_concepts.py` =
run + renders; numbers in `concepts_results.json`). Tests: `tests/test_bag_concepts.py`.
Research first: `docs/research/bag_body_architectures.md` (cited as **[BA §n]**, pain points **A1..A6**).

Owner brief: "keep optimising, still simple to build; show me other designs of the bag". Beginner sewist, no machine
yet. Build simplicity is a top criterion next to performance.

## UPDATE 2026-11-07 (owner reaction): 13 bodies to choose from

Owner on the first 5-concept sheet: product body "Give me multiple to choose from"; prototype "Multiple designs";
simplifications "n/a. Look at other bags". So: **all build-simplification decisions are ON HOLD** (the SLAB-first
recommendation and the boxed-swell-for-SPINE proposal below are parked, not withdrawn), the research is widened
(`docs/research/bag_body_architectures.md` §6: KUIU, Stone Glacier, Exo, Mystery Ranch incl. Metcalf, Kifaru, Seek
Outside, Initial Ascent, Eberlestock, Argali, Paradox, Hyperlite, ULA, Granite Gear, Sitka, ROKMAN, cottage / MYOG)
and **eight more, clearly different concepts** are drawn (`designs/pack_5200/concepts/bag_concepts_wide.py`, run
`render_wide.py`; numbers in `concepts_results.json`, tests `tests/test_bag_concepts_wide.py`).

Galleries: `outputs/screens/20261107_bagalt_16.png` (1–7) and `_17.png` (8–13); score table `_18.png`; hours `_19.png`.
Concept sheets (3/4 rear + side view on the frame and mannequin, pieces to scale, numbers): 1–5 = `_1`..`_5`,
6–13 = `_8`..`_15`.

### U.1 The new eight (research hook in brackets, no look copied)

| # | Name | What it is | Access | Frame interface change |
|---|---|---|---|---|
| 6 | **SPIRE** | tall slim torpedo top-loader: round D section (n 2.5), 10.9 in deep, 47.1 in to the fill line; camo storm flap on a short front zip [UL tube packs, §6] | roll-top + 447 mm straight centre zip, z 120–560 | none (bottom 272 mm wide as SPINE) |
| 7 | **CRADLE** | open harness (B-01 + two side wings + bottom cup) holding **four horizontal roll-top drybags** D 250/290/300/300 × 330 mm; drop one drybag and cinch meat in its place [Eberlestock / Sitka / ROKMAN dry-bag systems] | lift any drybag out; IM1–IM3 run across drybags or meat | B-01 becomes the harness back to z 1175; B-22 guy tabs move to the wing aft edges at z 752 |
| 8 | **DUO** | two-zone: lower sleep-kit compartment with its own 508 mm horizontal zip (z 330) and a **removable** divider on 3 G-hook tabs (meat mode: unhook) [sleeping-bag-compartment debate, §6.1] | roll-top (main) + lower-zone zip | none |
| 9 | **GULP** | giant 4-way-stretch shove-it pocket over the whole aft face (z 80–630, ~9 L ASSUMPTION, not counted) + side zip [Exo / ULA / Seek front pockets] | roll-top + 455 mm right-side zip, z 150–600 | none |
| 10 | **MAW** | clamshell duffel hauler: closed top panel, one 2.06 m zip up both aft corners and across the top; the aft face drops open; **no roll-top** [MR 3-ZIP / duffel] | full opening | no collar / hem / roll buckles (−48.5 g common); compression only by W1–W3 |
| 11 | **CAIRN** | roll-top + integrated **6.4 L lid** that comes off as a summit / stalk pack (2 stowable 25 mm straps), camo lid top [MR / Exo / Granite Gear lids] | roll-top + 450 mm left-side zip; lid zip | lid rear straps to the frame-side hem (as today's optional lid) |
| 12 | **WISP** | minimalist ultralight tube: roll-top only, no lid, no zip, no body pockets [Hyperlite Porter, Kifaru Gnargali] | roll-top only (A2) | none |
| 13 | **MANTLE** | expedition hauler: box body + two full-height **side compression wings** (230–250 mm, 3 G-hook straps each) for tripod, pads, antlers or a small-load squeeze [Kifaru bellowed sides, Seek strap systems] | roll-top + 520 mm centre zip | wing roots in the B-01 / gusset seams |

All 13 keep: 85.2 L ±3 (CRADLE 84.65 L), 15.5 in width, depth ≤ 12 in, coil zips and no hook-and-loop, solid body
with camo accents only at wear lines / edges (accents < 35 % of body mass, tested), fly in its base pocket and bow
riser carry (common, not drawn), patent guardrails H1–H4 (CRADLE's harness IS the bag's frame-side panel on the
fairleads, not a sling between frame and bag, so H1 holds).

### U.2 Score table, all 13 (same metric code; weights unchanged; computed criteria now scaled to the best of 13)

| # | Concept | L | Fill in | Mass Δ g | Pack lb | Pieces | Curved | Zips (mm) | Hours | Access | CG y/z | Look / feature | Score |
|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|---:|
| 1 | SPINE | 85.1 | 42.0 | 0 | 7.71 | 37 | 14 | 1 (509) | 35 | 3.5 | 148/592 | slim teardrop, band pocket, best look | 2.45 |
| 2 | SLAB | 85.2 | 40.2 | +34 | 7.78 | 25 | 0 | 1 (520) | 20 | 3.5 | 149/558 | boxy, no overload pocket | 3.14 |
| 3 | TWIN | 85.2 | 40.2 | +60 | 7.84 | 24 | 0 | 2 (1160) | 20 | 4.5 | 149/558 | boxy, stretch pocket | 3.16 |
| 4 | WRAP | 85.2 | 42.4 | +30 | 7.77 | 24 | 4 | 1 (646) | 22 | 3.5 | 142/590 | SPINE-like, band pocket | 2.85 |
| 5 | HATCH | 85.2 | 40.2 | +50 | 7.82 | 25 | 1 | 1 (1426) | 23 | 5.0 | 149/558 | boxy, full view, long zip | 2.79 |
| 6 | SPIRE | 85.2 | 47.1 | +13 | 7.73 | 20 | 2 | 1 (447) | 19 | 3.0 | **132**/659 | torpedo, tall, closest CG | 3.48 |
| 7 | CRADLE | 84.7 | 45.5 | +161 | 8.06 | 33 | 0 | 0 | 27 | 4.0 | 168/632 | modular drybags, open sides | 2.41 |
| 8 | DUO | 85.2 | 42.4 | +37 | 7.79 | 23 | 7 | 1 (508) | 26 | 4.0 | 142/590 | sleep zone + door | 2.25 |
| 9 | GULP | 85.2 | 43.9 | +52 | 7.82 | 21 | 4 | 1 (455) | 23 | 4.0 | 139/611 | 9 L stretch pocket | 2.68 |
| 10 | MAW | 85.2 | 36.7 | **−30** | 7.64 | 19 | 1 | 1 (2056) | 17 | 5.0 | 154/**554** | duffel opening, no roll-top | 3.81 |
| 11 | CAIRN | 85.2 | 43.0 | +166 | 8.07 | 22 | 4 | 2 (1055) | 26 | 3.5 | 141/598 | 6 L summit-pack lid | 2.38 |
| 12 | WISP | 85.2 | 44.2 | **−26** | 7.65 | 18 | 5 | 0 | 20 | 1.5 | 139/619 | UL minimal, no zip | 3.19 |
| 13 | MANTLE | 85.2 | 40.2 | +207 | 8.16 | 28 | 0 | 1 (520) | 25 | 3.5 | 149/558 | side wings, heavy | 2.69 |

Pack lb = 3495.6 g production pack (geometry.yaml) + the body delta (CAIRN's lid and MANTLE's wings are counted; the
current optional lid is not). Mass deltas include common-item changes (MAW and CRADLE drop the 48.5 g roll-top
hardware; CRADLE's four drybag clips are booked instead). Scores rank, they do not choose: with 13 options the
"best" mass (MAW) and CG (SPIRE y, MAW z) set the scale, so the carry column now spreads 1–2.4 for everyone.

### U.3 What each one is good and bad at (judgement, for the owner's pick)

- **SPIRE**: the most "alpine" look and the closest load to the back (CG 16 mm closer than SPINE), light (+13 g),
  quick to sew; but 47 in tall (5 in over SPINE, the full bag stands higher behind the head: re-run R-28 before use)
  and the round section holds less in its corners.
- **CRADLE**: the most modular and the most original look; drybags are waterproof without a fly and meat swaps in
  cleanly; but +161 g, CG 168 mm aft (round drybags push the load out) and 45.5 in tall, and the open sides snag brush.
- **DUO**: real organisation (sleep kit stays dry and reachable), same shape as WRAP; 7 curved seams and the most
  hours; the divider must come out for meat.
- **GULP**: the feature users ask for most (big front stretch pocket, ULA / Exo reviews) on a SPINE-like body; the
  pocket fabric snags on brush (durability 3).
- **MAW**: the widest opening and the lightest (−30 g) and fastest to sew; but no roll-top: no volume adjustment, a
  2 m zip carrying the full hoop load (A1), rain on the top zip. Shortest bag (36.7 in, lowest CG z).
- **CAIRN**: a summit / stalk pack in the system (the owner already has the 4.9 L lid / hip pack idea); +166 g.
- **WISP**: lightest real roll-top (−26 g), quiet and waterproof-friendly; but reaching IM1 means unpacking (A2).
- **MANTLE**: best external carry (tripod, pads, antlers, cape) and squeeze for small loads; +207 g, heaviest.

### U.4 What I suggest the owner looks at first (not a decision)

Shortlist by what the owner valued so far (slim modern look, meat hauling, quiet, ~6.6 lb): **SPIRE** (look + CG),
**GULP** (pocket users want), **CAIRN** (summit pack) and **SPINE** as released, with **CRADLE** as the "different
idea" if modularity matters. All simplification choices stay on hold until the owner picks a body.

### U.5 Hand-offs for the wider set (none applied)
- pack-designer / cloth sim: SPIRE and CRADLE are taller than SPINE: head clearance R-28 and the top-anchor sims must be
  re-run on whichever is chosen; CRADLE moves B-22.
- structural-fea-engineer: CRADLE CG 168 / 632 mm is inside the rev C 190 mm meat / 205 mm bag envelope but the
  highest of the set; re-measure (T9) on the chosen body.
- materials-engineer: GULP / TWIN stretch pocket fabric abrasion (no Martindale vs brush data in the stretch record
  beyond 50 000 cycles); CRADLE drybag fabric (100D PU assumed; ULTRA 200 option).

### U.6 Assumptions added
CRADLE drybag diameters, 330 mm body length, 5 mm stack gap; GULP pocket 9 L; CAIRN lid shape (400 × 290 superellipse
n 3, 80 mm gusset) and harness lengths; MANTLE wing size and strap count; DUO divider on 3 G-hook tabs; G-hook 4 g;
SPIRE envelope (n 2.5, nominal depth 290 mm); every judged access / durability / look score in
`bag_concepts_wide.JUDGED_WIDE`.

---

# First study (5 concepts, earlier the same day)

Scores below are the 5-concept run (scaled to the best of 5). Sheets `_1`..`_7` now carry the 13-concept
re-scoring of U.2; measured values (L, g, pieces, seams, hours, CG) are unchanged.

## Decision asked of the owner (first study; ON HOLD per the owner update above)

1. **Which body do you want to sew first?** Recommendation: **SLAB** as prototype 1 (the cheapest way to prove the frame
   interface, fit and meat haul), then choose the product body.
2. **Does the box look pass?** You rejected the first bag as "too boxy/dated" (DECISIONS 2026-11-01). SLAB, TWIN and
   HATCH are boxes. If the answer is no, the product body is **WRAP** (keeps the SPINE look and diagonal zip, 36 %
   fewer sewing hours) or SPINE as released.
3. Take the **boxed swell** into SPINE whatever you choose (−5.6 h of the hardest sewing, +8.5 g).

## 1. What the research says (short, [BA])

- The leaders build **roll-top + one front zip**: Exo K4 (straight full-length zip on 3600/7200, horseshoe panel on
  the 5000), Stone Glacier Sky (front U-zip panel), KUIU Pro (horseshoe) [BA §1, §2.2]. Exo: "the straight zipper
  offers great access, a simple design, and helps keep weight to a minimum" [BA §1.3].
- **Clamshell / side zips** are mostly Mystery Ranch (3-ZIP, Marshall dual side zips) [BA §2.3]. A single side zip
  "might become just a narrow slit" on a full bag (A3).
- **Rear entry** is a day-pack / camera-bag idea; no framed meat hauler uses it [BA §2.4]. On Pack 5200, B-01 carries
  every load path (fairleads, ports, hood ladder, hinge eyes). **Not a candidate.**
- Zip blow-outs on full bags are the recurring field complaint (A1). Roll-top-only bags make you go "armpit deep"
  (A2). Bottom seams fray / leak (A5).
- Cottage makers keep bodies to straight seams on flat panels, a straight tube collar, bound seams, a heavier bottom
  [BA §4]. Curves (gores, ovals) and horseshoe corners are what a first-time builder struggles with; our own
  BUILD_PLAN §2 lists SPINE's curved gores and bottom oval as the two hard operations.

## 2. What every concept keeps (constraints)

| Kept | How |
|---|---|
| Frame interface | Same frame-side face line: stay + 20 mm, **30 mm head setback** between z 560 and z 631.2 (now two straight creases in one flat B-01 instead of two ring seams and 3 tiers). Hinge eyes HE + B-18 in the B-01 / B-05 seam at z 60; 8 fairlead swells over the same cleats; IM1–IM3 ports at the swell crests; B-17 / B-23 hook tabs and T2 / T3 tongues; B-20 ladders x ±60, z 545–795; under-strap channels; B-24 float links unchanged (they clip to T3). |
| Patent guardrails | H1–H4 (`analysis/meat_carry_alternatives.md` §2, `bag_attachment.md` §8): no fabric panel between frame and bag, under-straps pin to pin, lifters on the crown, nothing between the spreader and the z 330 bar. Only the bag body changes: no concept touches them. |
| Owner freezes | 85.2 L main bag counted alone; **15.5 in** width; depth ≤ 12 in; fill ~42 in or less; roll-top; fly in its base pocket (common, not drawn); floating side pockets, wraps W1–W3, bow riser carry, hydration sleeve (common); no spotter pocket, no meat sleeve; **no hook-and-loop**; mostly solid with camo accents at wear zones; ~6.6 lb published target (see §5.3). |
| Materials | As SPINE: B-01 and swells `challenge_ultra_200`, face / gores `cordura_330d_nylon66`, bottom `cordura_500d_nylon66`, collar `robic_100d_ripstop`, accents `polyester_ht_630d_printable`, stretch `poly_spandex_stretch_woven_printable`, #10 coil zips. |

## 3. The concepts

Renders: `outputs/screens/20261107_bagalt_1.png` (SPINE) to `_5.png`, comparison `_6.png`, hours `_7.png`.

**1 SPINE (baseline, released v3.1).** Teardrop roll-top, frame panel in 3 tiers, 2 curved side gores, 4-piece face
split by the 509 mm diagonal zip, oval bottom, 8 cone swells (16 cap pieces), stretch band over the zip.

**2 SLAB (beginner build).** A **tapered flat-panel box**: one flat B-01 with a Z-fold for the setback, one trapezoid
aft face split down the centre by a **520 mm straight #10 zip (z 140–660, 2 sliders)** under a camo storm flap, two
flat side gussets, a 272 × 190 mm rectangular bottom, a straight-seam tapered collar. **0 curved seams.** Small stretch
cam cup for the bow. No stretch overload pocket (overload goes under W1–W3).

**3 TWIN (beginner +).** SLAB body; the zips go **into the two aft corner seams** (580 mm each, z 120–700), so the aft
face stays one piece and carries a **flat stretch overload pocket** (cam cup, poles, jacket), camo-bound mouth.
Ambidextrous by having one zip each side. 0 curved seams.

**4 WRAP (SPINE-lite).** Flat B-01 + **one developed wrap panel** (aft face and both sides, D section, outer exponent
4) cut on a **diagonal zip that is a straight line on the flat pattern** (646 mm, right hip z 248 to the left shoulder
seam z 631.2, as SPINE). Wrap = 3 pieces (lower, above the zip, shoulder band); D-shaped bottom. Stretch band, storm
strip and camo mouth binding as SPINE. Strain p99 1.29 % (patterns_v31 acceptance ≤ 2 %). 4 curved seams.

**5 HATCH (panel loader).** SLAB body; the aft face becomes a **horseshoe-zip door** (U-surround + door + hinge
band; 1426 mm zip, z 100–720, R 60 corners, 40 mm inside the corners) under the roll-top. Best visibility.

Concepts considered and dropped: rear entry (§1); a full clamshell (face released on 3 sides) because the roll-top
collar and the guys B-22 hang on the face top; a no-zip roll-top only (fails A2: IM1 is 155 mm above the floor).

## 4. Method (every number traces here)

- **Volume** (R-01 rule): body to the collar seam integrated exactly from the sections (box: 2a·d; D: 2a·d·F(n);
  F(n) = Γ(1+1/n)²/Γ(1+2/n)). Above the collar seam the stuffed collar forms a dome to the fill line by the **SPINE
  dome law** (depth 62 + (d_c − 62)·√(1−u²), width × (1 − 0.184 u²), shape factor blending to SPINE's at the roll),
  over the SPINE collar-to-fill height 319.8 mm. ASSUMPTION: every collar rolls into the same dome. **Calibrated on
  SPINE:** the raw law over-predicts SPINE's dome by 1.09 L (1.3 % of the bag); `DOME_CAL` 0.957 removes that, the
  1.3 % is the stated uncertainty. The collar-seam height is bisected so each concept holds **85.2 L (5200 cu in)**.
  Integrator check on SPINE's own stations: 85.09 L (released 85.14), CG y 148.2 / z 592.2 (released 148.2 / 592.5).
- **Envelope (concepts):** half-width 136 mm at the bottom (SPINE) to 197 mm (15.5 in) at the shoulder crease z 631.2,
  then constant; depth from SPINE's 190 mm at the bottom to 302 mm nominal at z 631.2, measured from the face
  WITHOUT the setback, so the aft face has one crease only and the depth above the setback is 272 mm (10.7 in).
  DECISION: a jog in the aft face would add 2 creases for no volume.
- **Flat patterns:** box faces are planar facets that contain the x (or y) direction, so they unfold exactly
  (`test_box_unfold_is_exact`). WRAP is flattened with `huntkit.patterns.develop_region` (the tool that drafted
  SPINE); the lower and mid pieces are cut from **one** development so the zip edges match. All structural seams
  match to ≤ 0.91 mm (`check_seams`, 1 mm tolerance). SPINE is measured on the released pattern set
  (`patterns_v31.build()`), through the same metric code (`bag_concepts.spine_build`).
- **Curved vs straight:** a seam is curved if either flat edge bows > 5 mm off its chord between pivots (ASSUMPTION:
  a beginner can ease 5 mm). A crease kink (> 2° between two straight runs > 12 mm) is a pivot, not a curve.
- **Mass scope ("bag body group"):** shell, collar + hem + HDPE strip, swells, band / storm strip / pockets on the
  face, camo accents, zips (`coil_zipper_10` × (L + 60 mm) + 2 sliders × 6 g ASSUMPTION, the `build_geometry` rule).
  Cut area × record gsm. Everything else (fly, side pockets, IM harness, attachment, wraps, roll-top buckles, keepers,
  bow carry, B-09, B-11, B-12, B-16) is common and excluded. Pack total = `geometry.yaml` 3495.6 g + the delta.
- **Beginner hours: ASSUMPTION model** (`bag_concepts.HOURS`): cut 0.12 h/piece; straight seam 0.6 h/m and curved
  1.8 h/m (incl. binding); pivot 0.05 h; closed ring seam 0.5 h; zip 0.5 h + 1.0 h/m + 0.4 h per curved corner;
  cone swell 1.2 h, boxed swell 0.5 h; camo appliqué 0.8 h/m of turned edge. Not calibrated on a real build: it gives
  SPINE 35 h against the BUILD_PLAN step-9 guess of 2–3 weekends (16–24 h). **Use it to rank, not to plan evenings.**
- **Load CG:** uniform-fill centroid, FCS y (aft) and z, like `build_geometry.bag_cg`. The cloth sim was not run (not
  cheap: ~10 scenarios × 3 torsos per body); the box bodies keep SPINE's frame face, so the hood / guy / hook loads
  should move little, but this is a hand-off (§8).

## 5. Results

### 5.1 Measured

| | 1 SPINE | 2 SLAB | 3 TWIN | 4 WRAP | 5 HATCH |
|---|---:|---:|---:|---:|---:|
| Main bag, L / cu in | 85.14 / 5195 | 85.20 / 5199 | 85.20 / 5199 | 85.20 / 5199 | 85.20 / 5199 |
| Fill height, in (mm) | 42.0 (1066) | 40.2 (1021) | 40.2 (1021) | 42.4 (1076) | 40.2 (1021) |
| Max depth, in; depth at top, mm | 11.9; 290 | 11.4; 272 | 11.4; 272 | 11.4; 272 | 11.4; 272 |
| Width, in | 15.5 | 15.5 | 15.5 | 15.5 | 15.5 |
| Load CG y / z, mm | 148 / 592 | 149 / 558 | 149 / 558 | **142 / 590** | 149 / 558 |
| Cut pieces (body group) | 37 (16 swell caps) | 25 | 24 | 24 | 25 |
| Seam length, m | 10.7 | 9.2 | 8.5 | 8.9 | 9.2 |
| Curved seams (m) | **14 (7.1)** | **0** | **0** | 4 (3.4) | 1 (1.4) |
| Pivots | 26 | 12 | 11 | 6 | 13 |
| Zips (#10) | 1 × 509 mm | 1 × 520 | 2 × 580 | 1 × 646 | 1 × 1426 horseshoe |
| Swells | 8 cone | 8 boxed | 8 boxed | 8 boxed | 8 boxed |
| Bag-body group, g | 333 | 367 | 394 | 363 | 383 |
| **Mass delta vs SPINE** | 0 | **+34 g (+1.2 oz)** | +60 g (+2.1 oz) | +30 g (+1.1 oz) | +50 g (+1.8 oz) |
| Pack total, g (lb) | 3496 (7.71) | 3530 (7.78) | 3556 (7.84) | 3526 (7.77) | 3546 (7.82) |
| **Beginner hours (ASSUMPTION)** | **35** | **20** | **20** | **23** | **23** |
| Access to IM1 (z 190) / low gear | zip low end z 248, under the band mouth | zip to z 140, centre | zips to z 120, either side; open both and the face drops | as SPINE | door to z 100, full view |

Why the alternatives are heavier: a flat B-01 and box section have more fabric per litre than the rounder SPINE
section (+9 g shell), boxed swells are 13.5 g vs 5.0 g of cone caps (+8.5 g), the box concepts carry an ULTRA
frame-side collar strip B-06f (+8 g, the B-20 ladder top would otherwise land 59 mm up the 100D collar) and the
kick plate is a larger camo area than SPINE's corner shards. Extra zip length costs the rest (TWIN, HATCH).

### 5.2 Score (1–5, weights: build 0.35, mass 0.15, access 0.15, carry 0.15, durability / quiet 0.10, look 0.10)

Computed criteria use absolute scales (`bag_concepts.score`): build = mean of 5 − (hours − best)/2 h and 5 − 0.5 ×
curved seams; mass = 5 − (g − best)/20 g; carry = 5 − (CG y − best)/5 mm − (CG z − best)/40 mm. Access, durability and
look are judgements (reasons below).

| | build | mass | access | carry | durability / quiet | look | **weighted** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 SPINE | 1.0 | 5.0 | 3.5 | 3.0 | 4.0 | 5.0 | **2.97** |
| 2 SLAB | 4.9 | 3.3 | 3.5 | 3.8 | 4.0 | 2.0 | **3.90** |
| 3 TWIN | 5.0 | 2.0 | 4.5 | 3.8 | 3.0 | 2.5 | **3.84** |
| 4 WRAP | 3.3 | 3.5 | 3.5 | 4.2 | 4.0 | 4.0 | **3.62** |
| 5 HATCH | 3.9 | 2.5 | 5.0 | 3.8 | 2.5 | 2.5 | **3.55** |

Sensitivity: with look weighted 0.20 (build 0.25) **WRAP 3.69** leads SLAB 3.61 and SPINE 3.37; with build simplicity
ignored (performance only) **SPINE 4.05** leads WRAP 3.83 and SLAB 3.37. The ranking is a statement about weights:
simplicity favours SLAB, the product favours SPINE / WRAP.

Judgements: **access** SPINE / WRAP 3.5 (one zip, low end 58 mm above IM1, under the band), SLAB 3.5 (central zip
reaches IM1 directly but no overload pocket), TWIN 4.5 (either side, wide when both open), HATCH 5 (full view, [BA §2.2]).
**Durability / quiet** HATCH 2.5 (1.4 m zip in hoop tension on a full bag, A1; blocked by wraps over the face, A6),
TWIN 3 (two zips = two failure points, no storm flap, corner seams take brush and wrap tension), others 4 (short zip
under a flap, coil, no hook-and-loop). **Look** SPINE 5, WRAP 4 (same silhouette family, fewer seam lines), the three
boxes 2–2.5 (owner rejected a boxy bag on 2026-11-01; the chevron kick plate and centre zip help a little).

### 5.3 Weight target
The owner's published target is ~6.6 lb (2976 g with the low-risk cuts, DECISIONS 2026-11-05). The production pack is
now 3496 g (7.71 lb) after the attachment, back-panel and frame bookings of 2026-11-05/06. **No body concept helps
weight:** all add 30–60 g. Body choice is about build time, look and access, not mass.

## 6. Notes per concept

- **SLAB.** Every piece is a rectangle or trapezoid; the only 3D handling is the bottom box and two ring seams.
  Setback = two fold lines marked on B-01 and two pivots on each gusset edge. Load CG 35 mm lower than SPINE (shorter
  bag: 40.2 in fill), same distance aft. Camo: chevron kick plate across the bottom 70–140 mm of the face and gussets
  (the wear line, A5), centre storm flap, roll hem band. Gap: no overload / shove-it pocket.
- **TWIN.** The easiest zips there are (straight, set into seams you sew anyway, [BA §2.3]). Two zips cost +26 g over
  SLAB. Both corner seams are under W1–W3 tension: the wrap keepers must sit on the gusset side so the zip stays
  reachable (A4).
- **WRAP.** Keeps the diagonal zip and the stretch band (owner confirmed both on 2026-11-01), and the slim, rounded
  silhouette. The zip is a straight cut on the flat: the easiest way to sew a diagonal zip. The 4 curved seams are a
  shoulder ring, the D bottom (the stuff-sack drill, BUILD_PLAN step 2), the collar ring (5.1 mm, borderline) and the
  wrap's shoulder edge; the two long B-01 seams come out straight (sagitta 0.5 mm). Best load CG of the five (142 mm
  aft, z 590). 42.4 in fill, 0.4 in over SPINE.
- **HATCH.** Best access, worst durability and the most zip. The horseshoe corners are the hardest zip operation in the
  study. It also conflicts with W1–W3 crossing the face: the wraps must be opened before the door.

## 7. Recommendation (honest)

- **Does any concept beat SPINE?** On **build simplicity**, yes, clearly: SLAB and TWIN halve the curved work (0 curved
  seams vs 14, ~20 h vs ~35 h, 25 pieces vs 37). On **performance**, no: every alternative is 30–60 g heavier, the boxes
  give up 0.5 in of depth and the teardrop look, and HATCH / TWIN add zip risk. WRAP beats SPINE on load CG (6 mm closer,
  3 mm lower) and on hours (−36 %) but loses 30 g.
- **Recommendation:** sew **SLAB as prototype 1**. It uses the identical frame interface, so it proves the fairleads,
  hood, hooks, IM straps, float links and fit for the least sewing, and it is a full, usable 85 L pack. Decide the
  product body after that bag has carried meat: **WRAP** if the owner wants the SPINE look with a simpler build (my
  pick for production), **SPINE** if the extra ~13 h of sewing is acceptable for −30 g and the released patterns.
- **Take now, whatever the body:** the **boxed swell** (one rectangle, four boxed corners, straight seams) can replace
  SPINE's cone swells: −5.6 h, +8.5 g, 29 cut pieces instead of 37. It needs a pattern-maker change to B-01 windows only.

## 8. Hand-offs (none applied; study only)

- **pattern-maker:** if SLAB is chosen, draft it from `bag_concepts.py` (pieces already exist as `huntkit.patterns`
  Pieces with seams and allowances); add notches every 50 mm and the B-01 crease lines. Boxed swell option for SPINE.
- **pack-designer / cloth sim:** box concepts have the collar seam at z 736, below the B-22 guy tabs (z 752 on SPINE).
  Move B-22 to z ≤ 716 on the aft face and re-run the top-anchor sims (PR15/19/23) before release; the hood and the
  B-20 ladders are unchanged (top rungs on the new ULTRA B-06f strip).
- **structural-fea-engineer:** nothing new. Concept CGs (y 142–149, z 558–592) are inside the HA-LS-1 rev C envelope
  (bag 205 mm, meat 190 mm); cloth-sim CGs must be re-measured on the chosen body.
- **materials-engineer:** none new (all records exist).
- **manufacturing-engineer:** beginner-hour rates are an ASSUMPTION; time the prototype-1 operations to calibrate.

## 9. Assumptions (new in this study)

Dome law and its SPINE calibration (§4); every collar forms the same dome over 319.8 mm; aft face without a setback
jog (depth 272 mm above z 631); 5 mm sagitta = curved; pivot rule; beginner hour rates; slider 6 g; boxed swell gives
the same 2 mm cleat air as the cone caps; HATCH door inset 40 mm, R 60, z 100–720; TWIN pocket z 60–420, 40 mm inside
the zips; WRAP outer exponent 4; judged scores (§5.2); score weights (owner can change them: `bag_concepts.WEIGHTS`).
Filled-bag bulge and corners ±5 % as R-01.

## 10. Open questions for the owner

1. Is a box silhouette acceptable for the first bag you sew (SLAB), knowing it is the look you rejected on 2026-11-01?
2. Product body after prototype 1: WRAP (SPINE look, ~23 h, +30 g) or SPINE as released (~35 h)?
3. One zip in the centre (SLAB) or one in each corner (TWIN, +26 g, adds the stretch overload pocket)?
4. Approve the boxed swell for SPINE now (−5.6 h, +8.5 g)?
5. Should build simplicity stay at 35 % of the score? At 25 % with look at 20 %, WRAP comes first.

## Screenshots

- `outputs/screens/20261107_bagalt_1.png` SPINE (baseline) · `_2` SLAB · `_3` TWIN · `_4` WRAP · `_5` HATCH: 3/4 and
  side views on the frame (19 in torso) + body pieces to scale + key numbers
- `outputs/screens/20261107_bagalt_6.png` side-by-side comparison + table
- `outputs/screens/20261107_bagalt_7.png` beginner hours by operation
- Copied to `docs/screens/`: `_6`, `_7`, `_4`, `_2`
