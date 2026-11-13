# Pre-cut review: CORRIE F rev 3 bag release (independent, adversarial)

design-reviewer, 2026-11-13. Scope: `outputs/release/pack5200_corrie_f_rev3/` (patterns + manufacturing),
`outputs/release/test_kit/`, the generating code (`designs/pack_5200/patterns_corrie_f_rev3.py`,
`mfg_corrie_f_rev3.py`, `concepts/corrie_f.py`), `analysis/corrie_f_body.md` sections 12-19,
`analysis/load_standard.md`, and `data/materials/`. The BL-039 churn (S crown-strap length, stale docs) is not
reviewed.

At stake: about $370 of materials, about 75 h of beginner sewing and about $2,350 of physical tests.

**Counts: 3 blockers, 13 majors, 21 minors.** No finding here needs new analysis. Each one is a pattern, op-text,
test-level or document fix. Fix the blockers before any bag fabric is cut. Fix the majors before the step they gate.

## What I ran and checked

- `python designs/pack_5200/mfg_corrie_f_rev3.py --check`: 90 ops, 26 load points, `box_mismatches: []`,
  `holds: []`. (That checker only looks at B-02h; see B-1 and M-2.)
- Full `python -m pytest -q -x`, started first: **965 passed, 10 skipped** (13.5 min). A targeted re-run about
  10 min later (`tests/test_patterns_corrie_f_rev3.py tests/test_mfg_corrie_f_rev3.py tests/test_physical_test_kit.py
  tests/test_corrie_f_bl033.py`): 57 passed, **1 failed**
  (`test_physical_test_kit.py::test_ca1_release_level_from_the_adopted_results`, see m-1). Concurrent edits
  between the two runs probably caused the failure.
- Rebuilt the pattern set (`patterns_corrie_f_rev3.build("today")` and `("B")`). Measured every edge pair. Walked
  the notches on every shell, collar, lid and fly seam. Computed primary vs alternate pattern mass for each kit.
- Opened every primary DXF with ezdxf. Units are mm (INSUNITS 4) and every block is inserted at scale 1. Every piece
  has a closed CUT outline and a GRAIN arrow. Dumped B-17, B-18, B-22, B-09p, HE and B-24 entity by entity.
- Measured the PDFs with pdfplumber: the test square is 100.00 mm and 4 in = 101.60 mm. B-17 (90 x 70), B-22
  (50 x 60) and B-11 (30 x 50) print at 1:1. Page sizes and page counts match the README. Rasterised the step 4 map
  and page A1 to check them by eye.
- Compared the BOM hardware with the load-check assumptions and the material records. Compared every test the
  release depends on with `test_kit/results_template.csv`.

## Verified correct (no action)

- **Seam lengths:** all 30 reported seams match to within 0.31 mm. The same holds for the seams the report leaves
  out: IMP4-b 760 = 280 + 200 + 280, MS-a 550 = MS-c 110 + 330 + 110, the collar ring 1050.0 vs 1049.7, and
  B-02u inner 1550.4 = door zip 1357.9 + 2 x 96.3.
- **Notch counts pair on every shell seam:** B-01 | B-03 14/14, blade | B-03 13/13, door zip 26/26, hinge 6/6,
  crown | wall 25/25, wall | base 20/20, fly 13/13. The **positions** are wrong on one seam (M-3).
- **Grain:** every cut piece in every primary DXF has a grain arrow. FP-a is turned 90 deg for stretch across.
- **Print scale:** the PDFs print true to scale on US Letter at 100 %, with 8 mm margins and 12 mm overlaps.
- **Hardware against the load checks:** these BOM records are the parts the loadpath checks assume: carabiner
  CAMP Nano 22 (minor axis 8 kN, so 4000 N proof basis), G-hook AustriAlpin DY25K-G (no-set 900 N), ITW Superloc
  heavy ladder lock, Austere 25 mm cam, stainless 25 mm tri-glide backstop.
- **Ledger reconciliation:** 1:1, 102 rows. Pattern mass is -0.08 % against the ledger, **on the team-B
  (alternate) fabric basis** (see M-6).

---

## BLOCKERS (fix before cutting fabric)

### B-1 The hinge eye (HE + B-18), the bag's bottom anchor, is defined three different ways. PT-3 cannot be built "exactly as the bag".

The hinge eye takes the bag-on load (1019 N factored per `load_standard.md:184` and `bag_attachment.md:135`). PT-3
(1530 N) must pass on specimens sewn exactly like the bag before any fabric is cut. The release disagrees with
itself on how to sew it:

| Item | Pattern piece (DXF / PDF) | Op 4.05 / load table / SK-1 |
|---|---|---|
| HE box-X through B-18 | **38 x 38 mm** drawn on B-18 (`huntkit/gendesign/attach_system.py:726`, `_box_x_lines(b18, 45, 22.5, 38, 38, ...)`; DXF `hypalon_coated_nylon.dxf` block B-18_1) | **34 x 34 mm** (HE piece; `load_points.csv:16`; `op_sequence.md:132-134`) |
| HE fold | folds at 50 and 100 mm, box at 108-142 mm (HE DXF block) | "50 mm back, 25 mm eye; first 30 mm tri-folded to an 18 mm neck, 304 bartack across the neck" (`op_sequence.md:133`, `mfg_corrie_f_rev3.py:966-967`). Not drawn and not in SK-1 |
| B-18 lower edge | B-01 placement starts **at the floor seam line** (`patterns_corrie_f_rev3.py:401-402`: `s01(BC.Z0)` to `s01(BC.Z0 + 45)`), so B-18 never reaches into the allowance | "lower edge in the B-01 \| B-05 seam" (B-18 label); "the 4th side goes in the floor seam" (op 4.05). The capacity row "B-18 seam (80 mm, **B-05 strip**) 2355 N" assumes the floor seam grips B-18 |
| B-18 perimeter rows | double row on **all four** sides (B-18 DXF: rectangles at 3 and 9 mm) | "perimeter rows on 3 sides" (op 4.05) |

On 38 mm webbing a 38 x 38 box has its sides on the webbing edges. If B-18 stops at the seam line, the floor seam
catches only its raw edge, and the 2355 N capacity has no physical basis.
`mfg_corrie_f_rev3.py:1431-1442` (`box_mismatches`) checks only B-02h, so the README (`manufacturing/README.md:48`)
reports "Box-X mismatches: none".

**Fix:**
1. Pick one HE construction. Draw it on the HE piece (folds, neck bartack, box), redraw B-18's box to match
   (34 x 34), and add an HE detail to SK-1.
2. Extend the B-18 placement and the piece 12 mm below the floor seam line, so the seam catches it. Drop the
   bottom perimeter rows from the B-18 piece.
3. Make `box_mismatches` compare every webbing piece with the panel it is box-X'd through (HE/B-18, T3/B-17,
   LLT/B-22/B-02h, B-28t/B-02h).
4. Re-issue PT-3's specimen description from the fixed drawing.

### B-2 The roll-top closure has nothing to clip to: no mating buckle half and no strap placement

The BOM buys 2 x 25 mm side-release buckles, and op 5.02 sews the RT clip straps "at each roll end, 30 mm round the
side-release buckle bar" (`op_sequence.md:179-181`; `patterns_corrie_f_rev3.py:1025-1028`, `:1112`). The design
has the roll end clip to "25 mm side-release on the **gusset tab**" (`concepts/strap_tails.py:278`). The original
gore flat work includes a "roll-top clip" (`panels.yaml:444`), and geometry.yaml puts the ROLL family "high on the
side gores".

The rev 3 release has none of this:
- no gusset buckle-tab piece in `cutlist.csv` or the webbing table;
- no placement mark on B-03, and no op in the gusset flat work (4.07-4.10);
- no placement mark on B-06/B-07 for where the RT strap sews to "the roll end".

The bag as released cannot be closed at the top. The parts that would fix it have to be sewn on the gusset while
it is still flat (before op 4.11).

**Fix:**
- Add an RT-mate webbing piece (25 mm tab round the second buckle half, box-X) to the cut list, and its placement
  and box on B-03 near the top. Source its height from the roll-clip paths (`corrie_f_roll_clips.json`) or mark it
  ASSUMPTION.
- Add a B-07/B-06 placement for the RT strap.
- Add a flat-work op before 4.11, and an RT row in `load_points.csv` (unrated, hand load).

### B-3 Three of the six K-W keeper loops share a seam with the hip-reach pocket edge. Which one goes on top is not stated, and getting it wrong traps W1/W2 under the mesh.

FP-L/R sit at z 150-380 with their aft edge **on** the aft corner seam line. The pattern draws the placement from
`ga(z)`, the seam line (`patterns_corrie_f_rev3.py:416-427`). Op 4.09 sews "bottom and sides". The K-W keepers are
caught in the same aft corner seam at R z 300 (W2), L z 202 (W1) and L z 370 (W2) (`README` volatile line;
`patterns_corrie_f_rev3.py:445-451`; op 4.12 at `op_sequence.md:160-162`). Op 4.12 does not say whether a keeper
goes over or under the mesh pocket's edge. Under the mesh, the haul wrap would have to thread inside the hip pocket,
and the pocket cannot be fixed without unpicking the 715 mm corner seam. The wraps also cross the pockets in any
case, which is a design question for the pack-designer.

**Fix:**
- State the stack order at those three keepers in op 4.12, with a sketch: keeper loop outermost, mesh edge under
  it.
- Or move FP's aft edge 10 mm forward of the seam line so the keeper is clear.
- Have the pack-designer confirm that W1 and W2 are meant to cinch over the FP pockets.

---

## MAJORS

### M-1 The B-26 tripod-keeper cord has no op that sews its second end

`corrie_f.tripod_keeper` (`concepts/corrie_f.py:1400-1403`) puts one end in the B-01 | gusset R seam and the other
in the **aft corner seam** (blade U | gusset R). The pattern notches both edges (`patterns_corrie_f_rev3.py:413-415`;
B-02u `outer_right` notch). Op 4.11 says "the B-26 shock-cord **ends** (15 mm in) inserted" into the frame seam,
plural (`op_sequence.md:156-158`; `mfg_corrie_f_rev3.py:1012`). Op 4.12 does not mention B-26.
**Fix:** op 4.11 should say "one end at the frame seam, the other end left loose". Op 4.12 should say "catch the
B-26 free end at the 'B-26 keeper' notch".

### M-2 The T3 box on the B-17 pattern is 38 x 38. T3, op 2.03 and the load table say 34 x 34.

`patterns_corrie_f_rev3.py:534` (`_box_x(b17, ..., 38, 38, "T3 tongue")`) against the T3 piece and
`load_points.csv` row "IM3 bag-hook tongue, box-X to B-17 34x34". The PDF shows the 38 x 38 box (step2 page A3).
This is the IM3 bag hook, 1702 N factored, proven by PT-2 at 2553 N.
**Fix:** draw 34 x 34 on B-17. Include this pair in the widened `box_mismatches` check from B-1.

### M-3 The collar-ring notches on the gusset top are mirrored for one side and end up 10 mm off

`patterns_corrie_f_rev3.py:361` passes `E(G, "top")` **unreversed for both gussets** in the ring. B-03's top edge
runs aft to frame. Going round the ring, one gusset is traversed aft to frame and the other frame to aft, so one
pass is reversed. The frame, aft and floor seams handle this correctly (the L side is reversed on B-01/B-05), but
the ring does not.

Result on the gusset top (from the aft end): 0, 15, 40, 65, 90, 115, 140 mm. The correct R set is 25, 75, 125. B-06
has notches 40, 90 and 140 mm from its R frame-side junction, and the nearest gusset notches are 10 mm away.
QC-08's limit is 2 mm. The beginner sees six slit notches where three apply.
**Fix:** reverse the gusset pass on the side where the ring runs frame to aft (as the frame seams already do).
Add a test that every notch on the shared gusset pattern has a partner within 1 mm on its mate.

### M-4 The B-22 label is self-contradictory and gives stale coordinates, on the tab the defect list rates critical for wrong-face sewing

The DXF/PDF label reads "laser-cut, no seam allowance; **OUTSIDE** B-02h (**INSIDE**, rev 2 turned in) at x
+/-**149** z **752**" (step2 PDF; `hypalon_coated_nylon.dxf` B-22_2). The correct placement is INSIDE, x ±130.3,
z 695. The string comes from `patterns_corrie_f_rev3.py:536-539`, which runs `.replace("B-02d", "B-02h (INSIDE,
rev 2 turned in)")` on the attach_system note (`attach_system.py:784`). The defect list rates "Load tab on the wrong
face (B-18 / B-22 in)" **critical** and says "placement labels say INSIDE / OUTSIDE".
**Fix:** overwrite the B-22 note in the rev 3 module: "INSIDE B-02h at x ±130.3, z 695; coated face to the band".

### M-5 The guy ladder lock is placed in two different spots, so the PORT-1 gloved-adjustment check tests a lock position the sewn bag does not have

`corrie_f_body.md:601-602`: "The heavy ladder lock sits **just outside the port** so the length is set from the
frame side on the packed bag". PORT-1 (`release_tests.csv:14`; `test_register.csv:100`) tests "with winter gloves
thread and adjust the guy ladder lock **at the port**". The pattern and ops box-X the lock tab LLT through B-22 +
B-02h **inside the hinge band at the aft top corner** (op 3.05, `op_sequence.md:97-100`; `load_points.csv:3`). The
TG free end feeds that lock. On a packed bag that lock is under the load, across the bag from the port.
**Fix:** the pack-designer decides. Either (a) the lock sits at B-22 inside: update 13.5 and PORT-1, and accept
in-bag adjustment; or (b) the lock sits outside the port: the guy end at B-22 becomes a fixed box-X (LLT deleted),
a lock tab goes on the B-01 outside at the port, and the B-22 box and load row are redrawn.

### M-6 QC-14 fails every primary-fabric bag

QC-14 (`qc_sheet.md:20`; `mfg_corrie_f_rev3.py:1238`) passes a bag within ±3 % of the **ledger** base mass, 1133 g
(±34 g). The ledger is on the team-B fabrics. The owner is building the **primary** fabrics. I rebuilt both sets:
base-kit pattern pieces weigh **456.9 g primary vs 392.8 g alternate, +64.1 g = +5.7 %**, before thread or anything
else. The QC row says "see costing.md", but `costing.md` has no mass figure.
**Fix:** give QC-14 a primary target (ledger + the primary pattern delta per kit, as computed here) and publish
the primary base / as-hunted / meat-trip masses in costing.md and the README.

### M-7 The guy and crown-strap lock gate (LL-H) runs at 1.27 x the factored load. The project proof rule is 1.5 x.

The project rule: "Proof rule: 1.5 x factored" (`loadpath_verification.md:3`). LL-H holds 366 N (1.5 x the old A3
guy load of 244 N). Rev 2/3 raised the guy envelope to **288 N** (`corrie_f_body.md` 13.5). The release still
releases the port-guy locks and all four B-28 locks on LL-H 366 N, with the note "366 N covers 288 N"
(`load_points.csv:2-7`; `qc_sheet.md` LL-H row; `test_kit/guides/G2.md:307-338`). The proof should be **432 N**.
The lock slip value (490 N) is itself an ASSUMPTION, 0.5 x the reseller tensile (`ladder_lock_25mm_heavy.yaml`).
`load_points.csv` lists only the box-X stitch SF (8.7-11) and never shows the governing hardware margin (490/288 =
1.70, assumed).
**Fix:** raise LL-H to 432 N (44.1 kg) or carry a recorded waiver from the owner. Add a "hardware slip" capacity
column to `load_points.csv` so the governing part shows.

### M-8 The cam and ladder-lock qualifications drop the cold and wet conditions their own records require

`cam_25mm_al.yaml:28`: slip 1100 N is an ASSUMPTION, "settled by: 5 cams ... **dry, wet and at -20 C**".
`ladder_lock_25mm_heavy.yaml:44`: "at 20 C and at **-20 C, wet and dry**". MT-3 and LL-H in the kit
(`test_kit/guides/G2.md:151-177, 307-331`) run room-temperature, dry, 1-minute or 1-hour holds only. The US cradle
cam margin is 1.02 (1080 proof / 1100 assumed). The kit already has a freezer and a hose (kit E).
**Fix:** add a wet sample and a -20 C (freezer, pulled within 2 min) sample to MT-3 and LL-H, as the records
specify.

### M-9 The release relies on SEW-F (box-X fatigue), which is not in the test kit

`loadpath_verification.md:18, 23, 36` (S1 IM end loops, S6 US eyes, H1 belt tabs) say "PASS after ... **SEW-F
(lever rig)**". The checks use ASSUMPTION SEW_FAT (0.40 x box strength) with ratios down to 1.48 (`:113`). There is
no SEW-F in `results_template.csv`, the guides or the order of work. The lever rig in G4 already exists.
**Fix:** add SEW-F to G4 (25 mm box-X, 1e5 cycles at 1.6 g x the S1/S6 1 g loads), or record why it is waived.

### M-10 The camo for B-02u, the largest camo panel and a structural one, cannot be bought from this release

B-02u (blade U + kick strip) carries two 715 mm corner seams, the floor seam and the #10 door zip, and it is cut
from `polyester_ht_630d_printable`. The BOM prices **unprinted** 630D at $18/yd (`bom.csv` fabric row; record
`polyester_ht_630d_printable.yaml`, "mill direct (printed, MOQ)"). No print file, colorway, repeat, print bureau,
print cost or lead time is named anywhere in the release (`grep -i camo` hits only the README fabric line). The
test kit buys a different custom print (HyperD 300, RBTR 1 yd minimum). The record's base is TPU-coated, and
sublimation runs at about 200 C, so check the coating survives. Nothing in the release lets anyone confirm the camo
is original (CLAUDE.md IP rule).
**Fix:**
- Name the released camo file (from `huntkit/camo`), its colorway and repeat, the vendor, MOQ and lead time, and
  add a print-cost line to the BOM.
- Or allow a solid-colour 630D fallback for the first build.
- Have the camo-designer sign the originality note into the release.

### M-11 The $367 material cost is a production figure, not what a one-off build costs

`costing.md:3` and README:25 use BOM `qty`, the production markers at 10 bags with waste. The prototype (1-bag)
marker quantities in the same BOM (`proto_qty`) give fabric **$131 instead of $88** (ULTRA 200 0.743 m vs 0.487 m;
camo 0.738 m vs 0.305 m). That is before retail minimum cuts (most shops sell whole or half yards, and Hypalon by
the yard) and before the camo print in M-10. Hardware is roughly 60 % of the cost and does not change.
**Fix:** publish a "prototype buy" column (rounded to shop increments) and its total next to the production cost.

### M-12 The needles and thread the release specifies do not match the machine the build plan tells the owner to buy

The owner has no machine yet (`docs/DECISIONS.md:95`; `BUILD_PLAN.md:26`). `BUILD_PLAN.md:37` budgets "a
walking-foot ... or a heavy-duty domestic machine that handles tex 90-135 thread and a **110/18-120/19** needle".
The release specifies **Nm 140/22 DPx17** with tex 135 for every box-X (`load_points.csv`, op presets). DPx17 is an
industrial or portable walking-foot system; domestic 130/705H machines cannot take it. Every load point, and PT-1,
PT-2, PT-3, MT-1 and PT-6, is specified on that set-up.
**Fix:** before the owner buys a machine, state the minimum prototype machine: walking foot, takes 135x17/DPx17
needles to size 22, sews tex 135, clears about 6 mm under the foot. Alternatively, re-specify the box-X for Nm
120/19 + tex 90 and re-rate the load points.

### M-13 Op 1.01 contradicts op 1.02 and the pattern, in the very first sewing op

Op 1.01 says "Fold the 2 box pleats on each FP-a ... baste across **top and bottom**" (`op_sequence.md:35-38`;
`mfg_corrie_f_rev3.py:845`). The pleat fold lines are drawn only 40 mm up from the bottom edge
(`patterns_corrie_f_rev3.py:589-595`). Op 1.02 sews the 260 mm FP-b band to the FP-a **top (260 mm)**. If the top
is basted it is 165 mm wide and the band cannot fit. The first op a beginner sews would end in unpicking.
**Fix:** op 1.01 should say "baste across the bottom only; the top stays 260 mm and is gathered by the cord".

---

## MINORS

| # | File:line | Finding | Fix |
|---|---|---|---|
| m-1 | `tests/test_physical_test_kit.py:32` | Fails: `flip_gov` 0.2556 (now governed by `flip_cheek_dir`) vs the asserted `max(flip_body, flip_cheek)` 0.2553. The test kit README still says "governing flip 0.2553". The CA-1 release level rounds to 0.276 either way | Update the test and the README text to the three-way max |
| m-2 | `load_points.csv:16`, `mfg_corrie_f_rev3.py:706` | Hinge load 795 N (loadpath A5) vs 1019 N factored in `load_standard.md:184`, `bag_attachment.md:135-136` and `attachment_diet.md:93`. PT-3's 1530 N = 1.5 x 1019. The SF shown (2.96) is optimistic; at 1019 N it is 2.31 | Use 1019 N, or reconcile the two records |
| m-3 | `load_points.csv:14` | B-17 perimeter capacity 3277 N is "from the 90 x 110 basis", but the tab is 70 mm tall. The release's lowest SF (1.93) rests on a superseded geometry; PT-2 settles it | Recompute `patch_seam` for 90 x 70, or label the SF "pending PT-2" |
| m-4 | `tpu_coated_nylon_840d.dxf` B-09p; `concepts/corrie.py:361` | B-09p is named "slot 12 x 40", but no slot is drawn. A laser operator cuts a blank patch over the hose slot | Draw the slot as `cut_inside` |
| m-5 | `op_sequence.md:43-46, 55-57, 168-170` | IMP-4: the zip sits on the face top only, so the 60 mm bellows ends at the mouth stay open and the second zip tape's anchor is undefined. F-02: one panel with a zip "on the aft edge", then a "perimeter row" that would sew the zip shut | Give each pocket a zip-construction sketch (which tape goes to which panel) |
| m-6 | `op_sequence.md:353-355` vs `:379-381` | Op 7.29 tells the beginner to lap the 2436 mm fly elastic "into a loop round its strap" (keeper text copied over). Op 9.02 threads it into the hems, but gives no length per channel | Give per-channel cut lengths and delete the lap text |
| m-7 | `op_sequence.md:62-64`, `patterns/README.md:45` | Op 2.01 says cut the B-12 / B-13x port slot **after** sewing, through both layers. Both DXFs draw it on CUT, and the README says "solid black inside = cut it out ... cut these first" | Move the slot to a placement layer on one of the two pieces |
| m-8 | `op_sequence.md:198-204, 230-234`; `mfg_corrie_f_rev3.py:758-759` | Op 6.03 says "BT-M tex 90, 304" but the machine row says box-X tex 135 / Nm 140. Op 6.04 turns the cap ends 10 mm, but the pattern allowance is 8 mm (the cap misses its placement by 2 mm a side). Op 6.11's seam is listed as "ZIP" | Correct the op presets and text |
| m-9 | `op_sequence.md:390` | "QC sheet sections F and M": the QC sheet has no such sections | Point to QC-12..QC-20 |
| m-10 | `op_sequence.md:273-352` | Webbing ops 7.09 (K-W), 7.22 (HPL), 7.23 (E5), 7.24 (I2T), 7.25 (I2K) and 7.10 (RT) come after the ops that sew those parts in (4.06, 4.11, 4.12, 5.01, 5.02), and some carry 0.2-0.6 h of bartack time that cannot happen after insertion | Move them to step 0 / before 4.06, or mark them "prepared in 0.05" |
| m-11 | `B-11` piece, `patterns_corrie_f_rev3.py:540-545` | Slot 25 x 5 mm for 25 mm webbing (BRL) has no clearance. The POM toggle record uses 27 x 5 | Make the slot 27 x 5 |
| m-12 | `op_sequence.md:141-143`; `load_points.csv` | B-11 tabs on the left gusset are labelled "antler / cape lash points" but have no load case or load-table row | Give them a load (pack-designer) or label them "light lash only, no load rating" |
| m-13 | `patterns/pattern_checks.md:7-38` | The seam table breaks in Markdown: seam names contain `\|`, so every column shifts ("Stitch" shows the name, "A mm" shows 301) | Escape the pipe or use another separator |
| m-14 | `patterns/README.md:9`, `cutlist.md` hardware table | "76 piece types" vs 45 cut-list rows (the count includes webbing). The cutlist hardware table lists 6 G-hooks and no cams, carabiners or tri-glides, while the BOM lists 9 G-hooks, 5 cams, 5 carabiners and 4 tri-glides | Say "45 fabric/sheet types + 31 webbing types". Make the cutlist hardware table a copy of the BOM |
| m-15 | `B-24` label (`poly_webbing_38mm.dxf`); `sketches/SK-3_B-01_flat_work.png` caption | Stale text: B-24 "rated 38 mm hook (same part as the bag hook)" (it is a carabiner now). SK-3: "+ 2 hinge (B-13xh)" (deleted by H-1) | Regenerate the labels |
| m-16 | step PDFs, every tile (e.g. step4 page A1) | The 100 mm test square is drawn on top of pattern lines, which makes it hard to measure and invites a wrong cut | Put the square in a reserved corner clear of geometry, or on the map page only |
| m-17 | `qc_sheet.md:19` | QC-13 passes 85 ± 3 L (82-88 L). The fine-mesh closed volume is 81.9-84.0 L (`corrie_f_body.md` 13.5), so the low end can fail | Check the band against the design volume, or record the expected value |
| m-18 | `test_register.csv`, guides | Assumptions are settled by fits that are not in the kit: LID-DART (lid filled with 5 L rice), B11-PLACE (archery / rifle loadout fit), IM2 notch fit, carabiner gate fit on the T3 loop (`carabiner_wiregate_22kn.yaml` gives a 17 vs 21 mm gate) | Add them to G7 as yes/no rows |
| m-19 | `op_sequence.md:357-359` | The IM strap topology is unclear. "G-hook right end, cam threaded": the cam has no sewn anchor, and the pattern draws one end loop while geometry.yaml says "2 x 60 mm end loops". The W1-W3 "ladder lock on the gusset side" has no tab piece (the anchor is a frame lash point) | Add an SK-7 assembly view per strap |
| m-20 | `B-22` placement, `patterns_corrie_f_rev3.py:459-461` | B-22 sits 6 mm inside the band \| blade seam line, so the SSa2 second row over the turned 12 mm allowance lands on the Hypalon edge | Note it in op 3.08 (sew the second row clear of B-22), or move B-22 a further 6 mm inboard after checking the guy-path sim |
| m-21 | `manufacturing/preview/*.png` | 60 dpi previews are unreadable on a phone (CLAUDE.md screenshot rule) | Rasterise at 100-120 dpi, or crop the key tables |

Not reviewed (BL-039, in progress by the pack-designer): the T9 crown-strap free-length criterion in
`qc_sheet.md` still quotes the BL-030 20 mm cut ("1138 - 150 - 60 = 928 mm"). Flagged only so it is caught when
BL-039 lands.

## Suggested order of fixes

1. B-1, M-2 and the widened `box_mismatches` check. Then re-issue the PT-2 and PT-3 specimen sheets.
2. B-2 and B-3, plus M-1 and M-13. These are all gusset or first-op changes, so they must land before 4.07-4.12.
3. M-7 to M-9 (test levels and missing tests). These must land before the G2 / G4 sessions the owner runs first.
4. M-6, M-10, M-11 and M-12. The owner needs these before ordering the machine, fabric and print.
5. M-3, M-4, M-5 and the minors at the next pattern regeneration.
