# CORRIE F rev 3 (door D2) - 5200 cu in hunting pack bag: manufacturing package (BL-032 part B, BL-034 part C)

Generated 20261113 by `designs/pack_5200/mfg_corrie_f_rev3.py` from `patterns_corrie_f_rev3.build()` and the part A markers. **Do not edit by hand: re-run the script.** Patterns: `../patterns/`.

## Files

| File | What |
|---|---|
| `techpack_corrie_f_rev3.pdf` | the tech pack a contract factory quotes from (all sections below) |
| `preview/` | raster preview of every tech-pack page (110 dpi, phone-readable) |
| `../camo/` | camo print file, colours, placement, vendors, costs (camo-designer release; BOM line 'fabric_print') |
| `bom.csv` | BOM: primary and alternate fabric, webbing, hardware, thread, consumables, waste %, cost |
| `cutting_plan.csv` | per material: markers, utilisation, lay, ply height, cutting method; webbing cut lengths |
| `op_sequence.csv` / `op_sequence.md` | sewing operations in build order (machine, needle, thread, SPI, stitch, seam, time) |
| `load_points.csv` | every load bartack / box-X: size, stitch count, load, capacity, SF, proof test |
| `qc_sheet.md` / `qc_sheet.csv` / `release_tests.csv` / `defects.csv` | QC points, release gates, defect list |
| `costing.md` / `costing.json` | material cost, beginner hours, factory SAM, CMT estimates |
| `delta_register_rev3.csv` / `.md` | RD rows this release closes or restates |
| `sketches/SK-*.png` | sketches the ops refer to |

## Key numbers

- Pieces: 77 piece types; 77 fabric / sheet pieces + 77 webbing / cord / elastic pieces (crown kit M).
- Ledger 1:1: 102 rows, 0 unmatched, 0 pieces without a row. Mass from pattern areas (ledger basis, team B fabrics): 570.2 g vs 567.7 g (+0.44 %, limit +/-3 %). Primary fabrics weigh +94.8 g more on the same pieces.
- Operations: 86; beginner hours 73.6 h (one-off set-up 4.1 h of it); factory SAM 501 min (8.3 h, ASSUMPTION SAM-RATIO).
- Material cost a bag, PRODUCTION (10-bag markers, record prices): primary $380, alternate $380. CMT + materials: US contract $912, Asia $455 (ASSUMPTION LABOUR).
- **What ONE bag costs to buy (prototype, 1-bag markers rounded to shop steps): $498** (fabric $185 vs $88 in production; ASSUMPTION SHOP-INCR; table in costing.md).
- **Mass targets, PRIMARY fabrics (the set you build): base 1197 g (2.64 lb), as hunted 1501 g, meat trip 1706 g** (QC-14, +/- 3 %); ledger (team B basis) 1133 / 1415 / 1611 g.
- **Sewing machine:** MINIMUM PROTOTYPE MACHINE (buy this or better): a walking-foot (compound or upper-and-lower feed) lockstitch that takes the 135x17 / DPx17 needle system up to size 140/22, sews tex 135 (V-138 / No. 138) bonded nylon top and bobbin, and clears at least 6 mm under the raised foot (38 mm webbing folded in half + Hypalon + laminate is about 5 mm). A domestic or 'heavy-duty domestic' machine (130/705H needles, tex 90 max) CANNOT sew the load points as specified. The alternative, re-rating every box-X for Nm 120/19 + tex 90 and re-running MT-1 / PT-1..PT-6 on it, is an owner decision, not taken here.
- **Camo:** the print comes from the camo-designer's release: read `../camo/README.md` first (print file `../camo/print/`, colours, placement, vendors, 1- and 10-bag costs). BOM section `fabric_print`. **Caveat:** 630D printable base is TPU-coated and sublimation transfer runs at about 200 C: print BEFORE the coating is applied (mill print), or order a strike-off and check the coat survives, before buying yardage. Solid 630D is the no-camo fallback.
- **Colourway:** Krummholz = body Krummholz Sage #6E745B (HA 17-0312), trim Deadfall Shadow #313120 (HA 19-0510), harness Elk Wallow #5E5A40 (HA 18-0612), owner_base camo accents (designs/apparel/colorways.yaml accent_pairings id 'krummholz'); the BOM notes name it on every coloured line.
- Load points: 28; lowest SF 1.93 (B-17 IM3 tab perimeter (double row)).

## Volatile operations (re-run when the pattern changes)

These ops read their numbers from the pattern; re-run `python designs/pack_5200/mfg_corrie_f_rev3.py` after the pattern module changes and they update (tags name the pattern value each op reads; BL-033, which last moved them, has landed):

- **pattern: B-22 x**: ops 3.04, 3.05; load points port guy, bag end
- **pattern: F-01**: ops 1.06, 9.01, 9.02
- **pattern: FP width**: ops 1.01, 1.02, 4.10
- **pattern: HE / B-18**: ops 2.02, 4.01, 4.02, 4.05; load points hinge eye
- **pattern: ledger**: ops 7.14
- **pattern: ledger (US-chan)**: ops 4.14

Current values: B-22 at x +/-130.3 mm (drawn 149.0); FP flat width 260.0 mm (finished 165.0); 6 swell windows; F-01 drafted: True; B-11 tabs on the gussets: 8; K-W keeper z: {'W1': {'R': 128.2, 'L': 201.8}, 'W2': {'R': 299.9, 'L': 370.1}, 'W3': {'R': 702.6, 'L': 702.6}}.

## On HOLD (cannot be sewn from the pattern as released)

- none

## Pattern / ledger flags

- Thread in the bag (all ops, no cone waste): 18.38 g; booked on the ledger: 18.38 g (build_effort_rev3.json; re-run `python designs/pack_5200/build_effort_rev3.py --write` when they differ).
- Box-X mismatches between a panel and its tab: none.
- Ledger hardware rows mapped by keyword (confirm): none.
- Unmapped ledger hardware rows: none.

## Pre-cut review status (BL-040)

Open after BL-040: 0 blockers, 0 majors. **Ready to cut** the bag fabric once the G2 proof tests and the G3 wash have passed (the physical gates in qc_sheet.md still apply).

| Finding | Class | Status | How |
|---|---|---|---|
| B-1 | blocker | fixed | DECISION HE-ONE: one hinge eye on HE / B-18 / B-01 / op 4.05 / load table / PT-3; SK-8; box_mismatches covers every stack |
| B-2 | blocker | fixed | RTM buckle tabs on both gussets (op 4.08) + RT strap placements on the flat hem (op 5.02); SK-10; load rows (unrated) |
| B-3 | blocker | fixed | op 4.13 states the keeper / mesh stack; SK-9; FP aft edge basted only; W1/W2 over FP confirmed |
| M-1 | major | fixed | B-26: one end in op 4.12, the free end caught in op 4.13 |
| M-2 | major | fixed | B-17 box 34 x 34 |
| M-3 | major | fixed | collar ring one way round; one notch set on the gusset (test) |
| M-4 | major | fixed | B-22 label: INSIDE B-02h, x placed, z 695, coated face to the band |
| M-5 | major | fixed | DECISION GUY-LOCK-IN: lock at B-22 inside; corrie_f_body 13.5 and PORT-1 updated |
| M-6 | major | fixed | QC-14 on the primary fabrics per kit; costing.md + README publish them |
| M-7 | major | fixed | LL-H 432 N; load_points.csv hardware columns |
| M-8 | major | fixed | MT-3 and LL-H dry / wet / cold |
| M-9 | major | fixed | SEW-F in the kit (G4 lever rig) |
| M-10 | major | fixed | camo/ referenced; BOM fabric_print line from camo/bom_print_line_proposed.csv; sublimation caveat |
| M-11 | major | fixed | prototype buy vs production in costing.md / README |
| M-12 | major | fixed | minimum prototype machine stated (README, tech pack section 2, BUILD_PLAN pointer) |
| M-13 | major | fixed | op 1.01 bastes the bottom only |
| m-1 | minor | fixed | already three-way max since BL-039 (test + README) |
| m-2 | minor | fixed | hinge 1019 N |
| m-3 | minor | fixed | B-17 perimeter SF labelled pending PT-2 |
| m-4 | minor | fixed | B-09p slot drawn |
| m-5 | minor | accepted | IMP-4 / F-02 zip-construction sketch not drawn this ticket: pockets are sewn first on cheap fabric and do not gate any load or other step; next pattern ticket |
| m-6 | minor | fixed | fly elastic per channel, lap text removed |
| m-7 | minor | fixed | swell slot is a mark; cut through the B-12 slot |
| m-8 | minor | fixed | lid presets / cap turn / seam label |
| m-9 | minor | fixed | QC-12..QC-20 |
| m-10 | minor | fixed | seam-inserted loops folded in step 2 |
| m-11 | minor | fixed | B-11 slot 27 x 5 |
| m-12 | minor | fixed | left-gusset B-11: light lash only, no load rating |
| m-13 | minor | fixed | seam table pipes escaped |
| m-14 | minor | fixed | piece-type split; cut-list hardware = BOM quantities |
| m-15 | minor | fixed | B-24 label, SK-3 caption |
| m-16 | minor | accepted | test square placement is in the shared huntkit/patterns/export_pdf (pattern-maker); it already picks a free corner when one exists |
| m-17 | minor | fixed | QC-13 records the expected 81.9-84.0 L |
| m-18 | minor | fixed | FIT-R3 in G7 |
| m-19 | minor | accepted | IM strap assembly views (SK per strap) need the strap topology drawn by the pack-designer; next ticket; the fitting op names each part |
| m-20 | minor | fixed | op 3.08 turns the allowances away from B-22 |
| m-21 | minor | fixed | previews 110 dpi |

## Assumptions that govern

| ID | Assumption | Settled by |
|---|---|---|
| NO-BIND | Body seams are SSa2 (second row over the turned allowances), not bound: the ledger books no binding (RD-17 B-1). | FRAY-1 wash-swatch test (3 cycles); if it fails, bind with 20 mm grosgrain via a binder |
| NO-TAPE | No taped seams: the bag is water resistant, contents in the user's dry bag. | owner decision if a waterproof bag is wanted (seam-tape machine + taped ULTRA seams) |
| SAM-RATIO | Factory SAM = 0.12 x beginner hours (bag_concepts.HOURS basis). | time study on the first 10-bag lot |
| LABOUR | Loaded CMT minute: US contract $0.85/min, Asia $0.12/min; overhead + margin 25%. | two contract quotes from this tech pack |
| THREAD-FACTOR | 2.75 m of thread per m of 301 stitching (both threads, ends). | weigh the cones before / after the first bag |
| SPI-LIGHT | 10 SPI on 40D-100D and mesh. | QC-05/06 swatch: no puckering, no perforation |
| THREAD-NEEDLE | Tex 70 / Nm 90, tex 90 / Nm 110, tex 135 / Nm 140, round point (attach_system.NEEDLE for 90 / 135). | swatches in op 0.02: no skipped stitches, no shredding |
| UTIL-SMALL | Small and sheet pieces nest at 70% across bags in production. | first production markers |
| UTIL-ALT | Alternate-set body fabrics nest at 85% in production (no 10-bag alternate marker). | alternate 10-bag markers if the alternate set passes its gates |
| B11-PLACE / KW-PATH / F02-CENTRE / US-EYE | Pattern placements read by this package (patterns_corrie_f_rev3, BL-034 part A): B-11 tab heights, K-W keeper heights from the W path, F-02 fore-aft on B-05, the US eye fold. | archery / rifle loadout fits; T9 W free lengths (keeper within +/-15 mm of the wrap); fly fit; MT-1 specimens |
| WX-LOAD | Haul extenders carry the S9 float-clamp load (225 N). | pack-designer load case; LL-H |
| US-BS | The stainless 25 mm tri-glide behind each US cam stops cradle slip (record: 3.75 kN break, no slip rating). | gate US-BS: cam slipped on purpose, backstop holds |
| TG-SS-PRICE | Stainless tri-glide USD 2.84 from the record's EUR source line, converted as the record does (ex VAT x 1.09 USD/EUR). | supplier quote |
| BT-STD | Slit-end bartack 10 x 2 mm, 28 stitches; standard tack 16 x 2 mm, 42 stitches (LK-1900 patterns). | QC-07 |
| HE-ONE / HE-GAP / HE-REACH | BL-040 B-1: one hinge-eye construction (HE folded in half, both raw ends and the B-18 edge in the floor seam, box-X 34 x 34 4 mm above the seam line); the 25 mm free eye reaches the z 60 pin. | PT-3 on specimens sewn as op 4.05 / SK-8; QC-20 fit on the frame |
| RT-MATE / RT-HEM | BL-040 B-2: roll-clip buckle female half on an RTM tab at the gusset mid depth 150 mm under the collar seam (the cloth-pass roll model's tab); RT strap boxed on the flat hem, frame-side half of the gusset. | T9 roll-clip free length (ROLL-CLIP-PATH) and the first collar |
| GUY-LOCK-IN | BL-040 M-5: the guy ladder lock stays on its LLT tab at B-22 inside the hinge band; the guy length is set with the roll top open (per crown kit / load), not on the move. | PORT-1 gloved adjustment at B-22 |
| KW-OVER-FP | BL-040 B-3: haul wraps W1 / W2 cross the FP hip pockets, over the mesh (keeper loop on top). | T9 W free lengths; first loaded haul: pocket still reachable with the wraps cinched (owner) |
| SHOP-INCR | Prototype buy: roll goods in 0.5 yd steps at full width, webbing whole yards, HDPE one 0.25 m2 sheet. | the owner's actual order |
| PRICES | Items with no material record use PRICE_ASSUMED (TPU hook sleeve, rubber pull sleeve, basting tape, seam sealer, labels, packaging). Hardware and elastic use their records since BL-034. | supplier quotes |

## Packaging

1. Bag: collar unrolled, door zipped, straps coiled inside the bag (keepers on), folded flat to about 450 x 350 mm.
2. Base kit inside the bag: IM1-IM3, US1/US2, W1-W3 fitted; guys fitted to B-22 with the toggle end coiled.
3. As-hunted kit bag (poly bag 1, labelled): B-29 lid with the B-28 straps for the ordered crown kit (S / M / L), scope pod.
4. Meat-trip kit bag (poly bag 2, labelled 'MEAT TRIP KIT'): 3 WX extenders with G-hooks, 2 B-24 links with carabiners, meat liner MS.
5. Card on top: load limits (53 kg / 116 lb frame meat in float mode, RD-02), guy rule (port guys fitted for every carry, RD-23), the strap tail rule, wash cold / line dry, no hook-and-loop.
6. Outer: recycled poly bag 600 x 800 mm, 10 bags per carton; carton label: rev 3, door D2, crown kit, fabric set (primary / alternate), date, lot.
