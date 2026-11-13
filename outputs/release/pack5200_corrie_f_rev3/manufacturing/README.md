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

- Pieces: 78 piece types; 77 fabric / sheet pieces + 78 webbing / cord / elastic pieces (crown kit M).
- Ledger 1:1: 115 rows, 0 unmatched, 0 pieces without a row. Mass from pattern areas (ledger basis, team B fabrics): 570.2 g vs 570.7 g (-0.10 %, limit +/-3 %). Primary fabrics weigh +94.8 g more on the same pieces.
- Operations: 87; beginner hours 74.4 h (one-off set-up 4.1 h of it); factory SAM 506 min (8.4 h, ASSUMPTION SAM-RATIO).
- Material cost a bag, PRODUCTION (10-bag markers, record prices): primary $380, alternate $380. CMT + materials: US contract $918, Asia $456 (ASSUMPTION LABOUR).
- **What ONE bag costs to buy (prototype, 1-bag markers rounded to shop steps): $501** (fabric $185 vs $88 in production; ASSUMPTION SHOP-INCR; thread by the 4 oz cone, sealer and tape by the smallest pack, ASSUMPTION SHOP-UNIT; no camo print: DECISION CAMO-FIRST; table in costing.md).
- **Mass targets, PRIMARY fabrics (the set you build): base 1217 g (2.68 lb), as hunted 1521 g, meat trip 1726 g** (QC-14, +/- 3 %); ledger (team B basis) 1153 / 1435 / 1631 g.
- **Sewing machine:** MINIMUM PROTOTYPE MACHINE (buy this or better): a walking-foot (compound or upper-and-lower feed) lockstitch that takes the 135x17 / DPx17 needle system up to size 140/22, sews tex 135 (V-138 / No. 138) bonded nylon top and bobbin, and clears at least 6 mm under the raised foot (38 mm webbing folded in half + Hypalon + laminate is about 5 mm), AND sews a 304 zigzag up to 5 mm wide (BL-041 Y-3: the BT-S / BT-M tacks and elastic laps are ISO 304; e.g. a portable straight / zigzag walking foot). A straight-stitch-only walking foot (the WF2 class) may be used if every 304 tack is sewn as the BT-301 fallback below. A domestic or 'heavy-duty domestic' machine (130/705H needles, tex 90 max) CANNOT sew the load points as specified. The alternative, re-rating every box-X for Nm 120/19 + tex 90 and re-running MT-1 / PT-1..PT-6 on it, is an owner decision, not taken here. Fallback for the 304 tacks: BT-301 (prototype, straight stitch only): 4 passes over the tack length (16 mm for BT-M, 10 mm for BT-S and slit ends, the full lap width for elastic laps) at 2 mm stitch, needle down and pivot at each end, 3-stitch backtack, same thread and needle as the 304 tack it replaces. UNRATED, like every 304 tack in this release (none is on a load-table path); the PT-3 neck tacks are sewn the same way as the bag's.
- **First build fabric for the camo pieces (DECISION CAMO-FIRST, orchestrator 2026-11-13):** solid 630D (polyester_ht_630d_printable, unprinted) on B-02u, SH-07, SH-01b, FP-b, B-29f and A1-d. B-02u is structural (two 715 mm corner seams, the floor seam and the #10 door zip): it is cut from 630D, the base the patterns, the BOM `fabric` line and QC-14 assume. The HyperD 300 print yard is a test-kit specimen only (AB-1 / FRAY-1, not a bag-cut gate); a printed bag waits for AB-1, FRAY-1 (HyperD | 330D) and a QC-14 target on that base.
- **Camo (later builds):** the print comes from the camo-designer's release: read `../camo/README.md` first (print file `../camo/print/`, colours, placement, vendors, 1- and 10-bag costs). BOM section `fabric_print` (production only). **Caveat:** 630D printable base is TPU-coated and sublimation transfer runs at about 200 C: print BEFORE the coating is applied (mill print), or order a strike-off and check the coat survives, before buying yardage.
- **Colourway:** Krummholz = body Krummholz Sage #6E745B (HA 17-0312), trim Deadfall Shadow #313120 (HA 19-0510), harness Elk Wallow #5E5A40 (HA 18-0612), owner_base camo accents (designs/apparel/colorways.yaml accent_pairings id 'krummholz'); the BOM notes name it on every coloured line.
- Load points: 31; lowest SF 1.36 (B-25 bridle toggle tab); the B-17 perimeter row is labelled SF PENDING PT-2 (load_points.csv).

## Volatile operations (re-run when the pattern changes)

These ops read their numbers from the pattern; re-run `python designs/pack_5200/mfg_corrie_f_rev3.py` after the pattern module changes and they update (tags name the pattern value each op reads; BL-033, which last moved them, has landed):

- **pattern: B-22 x**: ops 3.04, 3.05; load points port guy, bag end
- **pattern: F-01**: ops 1.06, 9.01, 9.02
- **pattern: FP width**: ops 1.01, 1.02, 4.10
- **pattern: HE / B-18**: ops 2.02, 4.01, 4.02, 4.05; load points hinge eye
- **pattern: ledger**: ops 7.15
- **pattern: ledger (US-chan)**: ops 4.14

Current values: B-22 at x +/-130.3 mm (drawn 149.0); FP flat width 260.0 mm (finished 165.0); 6 swell windows; F-01 drafted: True; B-11 tabs on the gussets: 8; K-W keeper z: {'W1': {'R': 128.2, 'L': 201.8}, 'W2': {'R': 299.9, 'L': 370.1}}.

## On HOLD (cannot be sewn from the pattern as released)

- none

## Pattern / ledger flags

- Thread in the bag (all ops, no cone waste): 18.79 g; booked on the ledger: 18.78 g (build_effort_rev3.json; re-run `python designs/pack_5200/build_effort_rev3.py --write` when they differ).
- Box-X mismatches between a panel and its tab: none.
- Ledger hardware rows mapped by keyword (confirm): none.
- Unmapped ledger hardware rows: none.

## Pre-cut FOURTH review status (BL-048)

design-reviewer fourth review `analysis/review_20261113_rev3_fourth.md` (1 blocker, 3 majors, 9 minors), bag side fixed by BL-048 (tests/test_us_route.py, tests/test_bl048_fourth_review_fixes.py). Open: 1 blockers, 0 majors. **NOT ready to cut**: N-1 needs the US station move on the frame (BL-047) and HE-FIT step 0 passing on the re-cut US test piece; a FIFTH independent review decides.

| Finding | Class | Status | How |
|---|---|---|---|
| N-1 | blocker | open (frame side) | BL-048 us_route.py: the real US path modelled on the 15/19/23 in meat drapes and the sliced print: it lies over the hinge cheeks and the HE (1-4.5 mm into them) and US2 over US1's fairlead. No bag-side guide can clear (US1 has 7 mm of height to move 40.5 mm sideways). US-ROUTE dropped. BL-047 asked to move US1 inboard / US2 outboard onto their own lanes (us_route.json station_move, >= 10 mm at every drape on the model); HE-FIT step 0 has a pass criterion and a US test piece in the kit |
| M-A | major | fixed | TL-1 reads BL-047's crown re-run on the BL-046 geometry (bl047_frame_items.json tl1): proof 497 N, rig A (guy 22 deg below horizontal) and rig B (58 deg, 13.6 % outboard), crown strap 43 N, run anchored on a spine stub 25 mm fore under the 6.0 mm collar |
| M-B | major | fixed | poly_webbing_38mm: purchase spec ply 1.2-1.6 mm (1.5 nominal), break >= 6 kN, sample calipered before the roll, fallback in the record; BOM + shopping list carry it; HE and B-25 read one thickness |
| M-C | major | fixed | PT-3 / SEW-F / HE-FIT fixture pin: hardened steel M5 x 40 dowel (DIN 6325), bought in kit A, pin-straight check; the frame pin check at the bag's 1019 N row is flagged to BL-047 |
| m-1 | minor | frame | BL-047 (fillet relief) |
| m-2 | minor | fixed | RT cut rounded UP to 565 mm (grip 50.8); DECISION RT-TAIL-EXC with the K-RT keeper |
| m-3 | minor | fixed | op 4.08 step 0: caliper the mated buckle before chalking; re-run rt_layout if larger |
| m-4 | minor | fixed | op 7.18: B-25 cut last from a scrap-strip dry fit at B25-FIT |
| m-5 | minor | fixed | op 7.18 text: wearer-side wording, BL-046 labels, neck-fold and mitre BT-M, laps sewn off the bar round an 18 mm dowel; op number 7.18 everywhere |
| m-6 | minor | fixed | SEW-F HE results rows (top row, proof), HE mounting on the lever rig, PAHT-CF print notes, about 100 g filament booked |
| m-7 | minor | fixed | release regenerated (release_tests.csv and the tech pack carry the new HE-FIT step 0) |
| m-8 | minor | fixed | webbing pages: the test square is placed clear of every strip (test_square_spot) |
| m-9 | minor | fixed | SK-1: the B25-BOX note moved to the footer; BT-M users include the IME / US / USA necks |

## Pre-cut THIRD review status (BL-043 / BL-044)

design-reviewer third review `analysis/review_20261113_rev3_third.md` (2 blockers, 4 majors, 14 minors). BL-043 fixed the bag-side items and checked each against every crown kit and torso end (tests/test_bl043_third_review_fixes.py); BL-042 fixed the frame print files and BL-044 the hinge eye on the BL-042 fairlead, checked by slicing the HE-FIT test-piece STL (tests/test_bl044_hinge_eye.py). Open: 0 blockers, 0 majors. **NOT ready to cut**: a FOURTH independent review of BL-042 / 043 / 044 is due first (three rounds found fixes that passed their own checks but failed on the real geometry).

| Finding | Class | Status | How |
|---|---|---|---|
| Z-1 | blocker | fixed | BL-042 hinge fairlead (5.5 mm under the pin, 20 mm throat) + BL-044 DECISION HE-ENV: the eye is solved on the real 3-ply neck wrap against bag_attach.HINGE_EYE_ENVELOPE and checked by slicing the HE-FIT test-piece STL at every bracket corner (he_stl_check: no overlap, gap and throat clearances); the test at test_bl041:55 (neck == throat) is replaced by a clearance test; SK-8 (c) redrawn on the envelope |
| Z-2 | blocker | fixed | BL-042: H1 print files carry the whole fairleads (12 / 12 pass the STL slice check); HE-FIT and IM3-EC print the BL-042 test pieces |
| M-1 | major | fixed | DECISION W3-OVER: W3 rides at the crown-bar height (z 601-804 over kits S / M / L); W3G deleted; RTM buckle and the hose slot (HOSE-LOW) 10 mm under the lowest W3 edge; W3 lies only on webbing, cord and the roll at all 6 kit-end corners (test); W3 crosses the roll at kit M / L part loads, so W3 is slackened to open the top; FIT-R3 row 7 at both ends of the owner's kit |
| M-2 | major | fixed | DECISION RT-ORIGIN: BL-041's origin needed a 76 mm gusset tuck to fold flat and put the box across the hem fold gap: fall back to the roll end; cloth-pass roll model re-run with the new tab (corrie_f_roll_clips.json): paths 202-424 mm, RT cut 510 -> 560 mm |
| M-3 | major | fixed | peel cannot be avoided (the stay-side leg passes under a pin 1.5-7.6 mm toward the frame from B-01: leg B leaves the box 23 deg off the box line in line, 50 deg held at the cheek-tip plane; he_peel); 'no peel' dropped; rated instead: PT-3 on the printed BL-042 fairlead with B-01 held at the cheek-tip plane (worst peel) to 1530 N, and 3 HE specimens added to SEW-F at 625 N peak (1.15 x 1.6 g x 1019 / 3); load row lists the 34 x 7 box capacity and its peel |
| M-4 | major | fixed | DECISION B25-TOPO drawn (SK-12, corrie_f.b25_topology): mitre under each sleeve, run and spine wrap necked to 25 mm, 13 mm over the (assumed) pawl housing at kit S 15 in; clamp undrawn in the frame files: ASSUMPTIONS B25-CLAMP / PAWL-TOP, gate B25-FIT in op 7.18; TL-1 specimen carries the turn and run |
| m-1 | minor | fixed | box top +11 (5 mm under the cheeks at the design pin); HE-FIT band 22-29 keeps the box >= 2 mm under the cheeks over the whole band; the solved bracket 23.1-28.9 sits inside it (test) |
| m-2 | minor | fixed | ops 4.05 / 4.08 give machine / needle / thread / stitch per step (step_spec), BT-301 named on the 304 tacks |
| m-3 | minor | fixed | W3G (the only 16 mm BT-S) deleted; every BT-S is 10 x 2 (SK-1) |
| m-4 | minor | fixed | IMC 192 mm, 48 mm folds, boxes 5 mm in from each raw end; MT-1 IMC specimens cut to it |
| m-5 | minor | fixed | op 7.13 (IMC): cam and G-hook bars threaded before the boxes, hardware listed |
| m-6 | minor | fixed | B25-BOX exception stated on the piece and on SK-1 |
| m-7 | minor | fixed | TL-1 / TL-1b read ovalisation at the loop centre with a bore gauge |
| m-8 | minor | fixed | bar stock 2.0 m (5 x 200 + control 200 + 2 x 160 + 10 %); TL-1b steps include 288 N; TL-1b count 2 everywhere |
| m-9 | minor | fixed | W3 / hose slot in the clearance set at all 6 corners; DECISION HOSE-LOW moves the slot below W3's sweep |
| m-10 | minor | fixed | camo print BOM line proto_qty 0, 'production only' |
| m-11 | minor | fixed | step 2 tiled print: every label block re-flowed into a clear spot (export.fit_label); B-18 and B-22 labels clear every mark and stay inside the outline (test); shortened labels in full on the NOTES page |
| m-12 | minor | fixed | webbing pages: leader label on every line; B-25 and RT added; W3G removed |
| m-13 | minor | fixed | SK-8 (c): stay labelled printed PAHT-CF, throat floor drawn with its gap under the pin (the HE redraw itself is BL-044) |
| m-14 | minor | fixed | ledger row relabelled 'BL-004 REC: guy toggles x2', mapped by prefix (no keyword rows) |

## Pre-cut re-check status (BL-041)

design-reviewer re-check `analysis/review_20261113_rev3_recheck.md` (2 blockers, 5 majors, 15 minors), fixed by BL-041 and re-checked geometrically (tests/test_bl041_recheck_fixes.py). A third independent review is still due before the fabric is cut.

| Finding | Class | Status | How |
|---|---|---|---|
| X-1 | blocker | fixed | op 4.05 reordered: NECK, B-18 ROWS (through B-18 + B-01 only), PLACE HE, BOX, BASTE; test: no B-18 / B-01 stitch line crosses the eye footprint and the rows precede the HE in the op text; PT-3 specimen built from the same order |
| X-2 | blocker | fixed | DECISION HE-PIN: eye UP on the z 60 pin, box-X 34 x 10 at +4..+14 (2 mm under the cheeks), eye 17 mm solved by he_geometry, HE 86 mm; loaded pin +23.4..+25.3 over the B-01 / webbing bracket (target 25 +/- 3, test); HE-FIT dry fit is a BAG-CUT gate before PT-3; SK-8 redrawn with the rows and the real pin [superseded by BL-044 DECISION HE-ENV: box 34 x 7 at +4..+11, eye 25 mm, HE 96 mm on the BL-042 fairlead] |
| Y-1 | major | fixed | [BL-044: the rig is now the printed BL-042 fairlead with a spacer, see M-3] PT-3 rig: pin in an 18 mm slot fixture, B-05 strip alone in the clamp, B-01 top free, pull down B-01; specimen = reordered op 4.05 with the B-18 rows and the baste |
| Y-2 | major | fixed | DECISION RT-FWD: clip path on the gusset at 10.9 mm from the hose slot, buckle bar 10 mm over the B-26 cord, muzzle tabs aft (111 / 171 mm, 60 apart); min clearance 10.0 mm over tabs, keeper cord, hose slot, bow tabs, B-26 cord (test on the buckle envelope + strap corridor); W3 through a W3G guide under the RT strap (DECISION RT-OVER-W3); FIT-R3 rows 5-6 |
| Y-3 | major | fixed | machine minimum adds a 304 zigzag; BT-301 straight-stitch fallback, unrated (every 304 tack in the release is unrated); BUILD_PLAN 140/22 and tex 70 / 90 / 135 |
| Y-4 | major | fixed | structural result adopted (crown_tube_guy_loop.md): B-25 in 38 mm, sleeves x 26.5-64.5, load row 323 N, bar wall SF 1.36 / 1.27 fatigue; TL-1 at 494 N on real bar stock with both toggles, TL-1b data test; GBL deleted; ledger booked |
| Y-5 | major | fixed | DECISION CAMO-FIRST: first build solid 630D on the camo pieces (README, BOM print line production-only, prototype buy without the print); HyperD yard + shipping in the test kit only |
| n-1 | minor | fixed | IM3-EC text says 'R about 0.02' (24 / 1178 = 0.0204, the countersign's F_min kept) |
| n-2 | minor | fixed | CA-1 retitled 0.40 (fallback >= 0.313); table cut at 115 %, above: stop, structural re-run |
| n-3 | minor | fixed | LL-H / MT-3 COLD is its own step; -18 C freezer accepted as the record's -20 C (ASSUMPTION FREEZER) |
| n-4 | minor | fixed | op 7.end replaced by the real op number of 'Fit the hardware' |
| n-5 | minor | fixed | SK-10 (b) axis 'sigma (mm along the gusset)', callout moved; SK-1 columns re-laid |
| n-6 | minor | fixed | B-18 / B-22 notes wrapped inside the pieces on the printed tiles (export) |
| n-7 | minor | fixed | 1:1 webbing-marks page added to step 2 (HE, RTM, W3G, IMC, T3, LLT, US) |
| n-8 | minor | fixed | TG toggle end: POM toggle hardware; GBL row gone (deleted); README lowest SF notes PENDING PT-2 |
| n-9 | minor | fixed | BUILD_PLAN thread list tex 70 / 90 / 135, needles 140/22 |
| n-10 | minor | fixed | one-off buy: thread by the 4 oz cone, sealer and tape by the pack; print shipping in the test kit |
| n-11 | minor | fixed | bag_attachment.md HE / B-18 rows marked superseded by HE-ONE / HE-PIN |
| n-12 | minor | fixed | tautology removed; a missing stack piece is an error; HE and RTM box centres checked to +/-1 mm |
| n-13 | minor | fixed | SEW-F peak 1.15 x 384 = 442 N |
| n-14 | minor | fixed | op 4.15: hinge-eye spans with the zipper / edge foot; PT-3 floor seams the same |
| n-15 | minor | fixed | DECISION IM-CAM-TAB: IMC dog-bone sews each cam to its hook / carabiner; SK-11 per strap; load row; MT-1 specimens |

## Pre-cut review status (BL-040)

Open after BL-044 (all three reviews): 0 blockers, 0 majors. **NOT ready to cut.**

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
| m-19 | minor | fixed | BL-041 (re-check n-15): IMC cam anchor tab + SK-11 per strap |
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
| HE-ONE / HE-PIN / HE-ENV / HE-GAP / HE-CHEEK / HE-T / HE-PIN-HI | BL-040 B-1 + BL-041 X-1 / X-2 + BL-044 Z-1 / M-3 / m-1: one hinge-eye construction (HE 96 mm folded in half, both raw ends and the B-18 edge in the floor seam, B-18 rows sewn first through B-18 + B-01 only); eye UP on the z 60 pin of the BL-042 hinge fairlead (bag_attach.HINGE_EYE_ENVELOPE: pin 10.1 mm above the stay, 5.5 mm under it, 20 mm throat); box-X 34 x 7 at +4..+11 mm, 5 mm under the cheeks at the design pin and >= 2 mm over the HE-FIT band; eye 25 mm solved on the real 3-ply neck wrap for webbing 1.5 mm (bracket 1.2-1.6 mm, thicker rejected). The box PEELS (leg B 23-50 deg off the box line): rated by PT-3 on the printed fairlead and SEW-F HE specimens. | caliper gate on the roll (ply <= 1.6 mm); HE-FIT on the BL-042 test piece (pin 22-29 mm above the seam line, box >= 2 mm under the cheeks), then PT-3 and SEW-F HE on specimens sewn as op 4.05 / SK-8 |
| RT-MATE / RT-HEM / RT-FWD / RT-ORIGIN / W3-OVER / HOSE-LOW / BUCKLE-ENV / MK-GAP | BL-040 B-2 + BL-041 Y-2 + BL-043 M-1 / M-2 / m-9: the RT strap is sewn at the roll end (gusset centre of the hem); its buckle's female half on an RTM tab forward on the gusset (hose slot + 10 mm + half a buckle), the buckle body 10 mm under the lowest W3 edge of every crown kit (W3 rides at the crown-bar height, z 601-804); W3 is the outer layer (slacken it to open the top); the hose slot also sits under W3's sweep; muzzle tabs 10 mm clear of the strap's line to the roll end; buckle envelope 35 x 35; RT cut from the cloth-pass roll model re-run with this tab and origin. | FIT-R3 rows 5-7 (rifle + roll clip + W3, at both ends of the owner's crown kit); T9 roll-clip free length; hydration fit (HOSE-LOW); caliper on the buckle |
| IM-CAM-TAB / IMC-LOOP | BL-041 m-19: each IM cam sewn to an IMC dog-bone (21 x 25 box-X each end, 18 mm loops) carrying the G-hook / carabiner. | MT-1 (2 IMC tabs at 908 N); threading the bought cam and hook |
| B25-TAB-CENTRE / WIDE_SLEEVE | BL-041 (crown_tube_guy_loop.md): B-25 in 38 mm webbing, sleeves x 26.5-64.5, toggle tab at the sleeve centre x 45.5; the 25 mm tab pull spreads over the 38 mm sleeve. | TL-1 at 497 N on real bar stock, specimen WITH the mitre turn and run (BL-043), rigs A / B per BL-047 (BL-048) |
| B25-TOPO / CLAMP (BL-045) | BL-043 M-4: B-25 = tab | sleeve | 45 deg mitre under the sleeve | run necked to 25 mm | one wrap round the spine under the clamp. BL-044: on the sized clamp (crown_spine_clamp: half 12 along the bar, collar 6) and the measured pawl housing (15.62 up, +/-24.82); the run reaches the printed spine 25.02 mm fore of the bar (+44.5 mm run). Was ASSUMED (B25-CLAMP / PAWL-TOP / SPINE_CLAMP_HALF). | BL-045 clamp T6 coupon (CLAMP-TYPE); op 7.18 gate B25-FIT at kit S 15 in; TL-1 specimen |
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
