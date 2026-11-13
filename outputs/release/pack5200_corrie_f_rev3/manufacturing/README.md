# CORRIE F rev 3 (door D2) - 5200 cu in hunting pack bag: manufacturing package (BL-032 part B, BL-034 part C)

Generated 20261113 by `designs/pack_5200/mfg_corrie_f_rev3.py` from `patterns_corrie_f_rev3.build()` and the part A markers. **Do not edit by hand: re-run the script.** Patterns: `../patterns/`.

## Files

| File | What |
|---|---|
| `techpack_corrie_f_rev3.pdf` | the tech pack a contract factory quotes from (all sections below) |
| `preview/` | raster preview of every tech-pack page (60 dpi) |
| `bom.csv` | BOM: primary and alternate fabric, webbing, hardware, thread, consumables, waste %, cost |
| `cutting_plan.csv` | per material: markers, utilisation, lay, ply height, cutting method; webbing cut lengths |
| `op_sequence.csv` / `op_sequence.md` | sewing operations in build order (machine, needle, thread, SPI, stitch, seam, time) |
| `load_points.csv` | every load bartack / box-X: size, stitch count, load, capacity, SF, proof test |
| `qc_sheet.md` / `qc_sheet.csv` / `release_tests.csv` / `defects.csv` | QC points, release gates, defect list |
| `costing.md` / `costing.json` | material cost, beginner hours, factory SAM, CMT estimates |
| `delta_register_rev3.csv` / `.md` | RD rows this release closes or restates |
| `sketches/SK-*.png` | sketches the ops refer to |

## Key numbers

- Pieces: 76 piece types; 77 fabric / sheet pieces + 75 webbing / cord / elastic pieces (crown kit M).
- Ledger 1:1: 102 rows, 0 unmatched, 0 pieces without a row. Mass from pattern areas (ledger basis, team B fabrics): 567.2 g vs 567.7 g (-0.08 %, limit +/-3 %). Primary fabrics weigh +94.9 g more on the same pieces.
- Operations: 90; beginner hours 74.6 h (one-off set-up 4.1 h of it); factory SAM 508 min (8.5 h, ASSUMPTION SAM-RATIO).
- Material cost a bag (record prices): primary $367, alternate $367. CMT + materials: US contract $907, Asia $443 (ASSUMPTION LABOUR).
- Load points: 26; lowest SF 1.93 (B-17 IM3 tab perimeter (double row)).

## Volatile operations (re-run when the pattern changes)

These ops read their numbers from the pattern; re-run `python designs/pack_5200/mfg_corrie_f_rev3.py` after the pattern module changes and they update (tags name the pattern value each op reads; BL-033, which last moved them, has landed):

- **pattern: B-22 x**: ops 3.04, 3.05; load points port guy, bag end
- **pattern: F-01**: ops 1.06, 9.01, 9.02
- **pattern: FP width**: ops 1.01, 1.02, 4.09
- **pattern: hinge window vs B-18**: ops 2.02, 4.01, 4.02, 4.05; load points hinge eye
- **pattern: ledger**: ops 7.16
- **pattern: ledger (US-chan)**: ops 4.13

Current values: B-22 at x +/-130.3 mm (drawn 149.0); FP flat width 260.0 mm (finished 165.0); 6 swell windows; F-01 drafted: True; B-11 tabs on the gussets: 8; K-W keeper z: {'W1': {'R': 128.2, 'L': 201.8}, 'W2': {'R': 299.9, 'L': 370.1}, 'W3': {'R': 702.6, 'L': 702.6}}.

## On HOLD (cannot be sewn from the pattern as released)

- none

## Pattern / ledger flags

- Thread in the bag (all ops, no cone waste): 18.28 g; booked on the ledger: 18.27 g (build_effort_rev3.json; re-run `python designs/pack_5200/build_effort_rev3.py --write` when they differ).
- Box-X mismatches between a panel and its tab: none.
- Ledger hardware rows mapped by keyword (confirm): none.
- Unmapped ledger hardware rows: none.

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
| PRICES | Items with no material record use PRICE_ASSUMED (TPU hook sleeve, rubber pull sleeve, basting tape, seam sealer, labels, packaging). Hardware and elastic use their records since BL-034. | supplier quotes |

## Packaging

1. Bag: collar unrolled, door zipped, straps coiled inside the bag (keepers on), folded flat to about 450 x 350 mm.
2. Base kit inside the bag: IM1-IM3, US1/US2, W1-W3 fitted; guys fitted to B-22 with the toggle end coiled.
3. As-hunted kit bag (poly bag 1, labelled): B-29 lid with the B-28 straps for the ordered crown kit (S / M / L), scope pod.
4. Meat-trip kit bag (poly bag 2, labelled 'MEAT TRIP KIT'): 3 WX extenders with G-hooks, 2 B-24 links with carabiners, meat liner MS.
5. Card on top: load limits (53 kg / 116 lb frame meat in float mode, RD-02), guy rule (port guys fitted for every carry, RD-23), the strap tail rule, wash cold / line dry, no hook-and-loop.
6. Outer: recycled poly bag 600 x 800 mm, 10 bags per carton; carton label: rev 3, door D2, crown kit, fabric set (primary / alternate), date, lot.
