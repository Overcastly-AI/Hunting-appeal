# Pre-cut RE-CHECK: CORRIE F rev 3 bag release after BL-040 (independent, adversarial)

design-reviewer, 2026-11-13. Re-check of `review_20261113_rev3_release.md` (3 blockers, 13 majors, 21 minors)
against the regenerated release (`outputs/release/pack5200_corrie_f_rev3/`, `outputs/release/test_kit/`) and the
code (`designs/pack_5200/patterns_corrie_f_rev3.py`, `mfg_corrie_f_rev3.py`, `physical_test_kit.py`), not against
the BL-040 status table in `manufacturing/README.md:58-100`. The concurrent ledger booking (B-18 +3.1 g, RTM tabs) is
ignored.

**Counts: 2 blockers, 5 majors, 15 minors (new or carried).**
**Verdict: NOT ready to cut.** The hinge eye (HE-ONE) cannot be sewn in the stated op order without stitching the
eye shut, and it no longer reaches the z 60 hinge pin. Both have to be fixed before PT-3 specimens are sewn,
because PT-3 must be sewn "exactly as op 4.05".

## What I ran and checked

- `python designs/pack_5200/mfg_corrie_f_rev3.py --check`: 86 ops, 28 load points, min SF 1.93, `box_mismatches: []`,
  `holds: []`, `unsequenced: []`, thread 18.38 g = ledger.
- Full `python -m pytest -q -x`: **1006 passed, 10 skipped**, exit 0 (13 min 57 s). Green tests do not catch X-1, X-2, Y-2 or Y-4: no test checks the B-18 rows against the HE footprint, the eye against the pin, the buckle envelope or the bar wall at 288 N.
- Rebuilt the pattern set via `mfg_corrie_f_rev3.build_ctx()` and dumped `rs.geo` (`he`, `rtm`, `rt_on_b07`, `b11`,
  `kw_z`, `collar_ring`) plus every internal line on B-03, B-07, B-11, B-18 and HE.
- DXF (ezdxf): every primary DXF is INSUNITS 4 (mm), every INSERT is at scale 1, and every piece has a CUT outline
  and a GRAIN arrow. The only open CUT polylines are the two B-27 slits on B-01 (156.2 mm, x +/-52). Those are
  slits by design. **All piece outlines are closed.**
- PDF (pdfplumber): every file is US Letter 215.9 x 279.4 mm. The test square is 100.00 mm and 101.60 mm (4 in) on
  `00_PRINT_FIRST` and on every page of step 2. B-18 prints at 90.00 x 62.00 mm, B-17 at 90 x 70, B-22 at 50 x 60
  and B-11 at 30 x 50. **Scale is 1:1.** I rasterised step 2 page 2 at 110 dpi and read it by eye (see n-6).
- I viewed SK-1, SK-8, SK-9 and SK-10 and compared them with the geometry. I also read G2 (PT-3, LL-H, PORT-1, TL-1),
  G4 (CA-1, IM3-EC, SEW-F), G6 (MT-1c), G7 (FIT-R3), `ca1_mt1c_confirm.md` (structural countersign), `costing.md`,
  `costing.json`, `camo/README.md`, `cost_1_and_10_bags.csv`, `BUILD_PLAN.md`, `load_points.csv` and `qc_sheet.md`.

---

## BLOCKERS

### X-1 Op 4.05 sews the B-18 top rows straight across the hinge eye: the 25 mm eye is stitched shut

- `outputs/release/pack5200_corrie_f_rev3/manufacturing/op_sequence.md:137`
- `designs/pack_5200/mfg_corrie_f_rev3.py:1110-1125`
- `designs/pack_5200/patterns_corrie_f_rev3.py:138, 647-649`

The order in op 4.05 is: (3) place B-18 inside, (4) lay the folded HE outside, (5) box-X, and only then
(6) "B-18 perimeter rows 3 and 9 mm in, on the TOP and BOTH SIDES".

The B-18 top rows run the full width of B-18 (x 3-87 and x 9-81). Their heights are **47 and 41 mm above the floor
seam line**: B-18 top is at +50, minus 3 and 9 mm. The free eye and its 18 mm neck occupy **+38 to +63 mm**, at
x 36-54 on B-18. So in step 6 both rows cross both eye legs. They sew the legs to each other and to B-01/B-18:

- The free loop shrinks to about 16 mm (+47 to +63).
- The neck tacks at +44 end up between two 301 rows.
- The first stitching the pin load reaches is two tex 90 rows across an 18 mm neck, not the 34 x 34 box.

The eye that HE-REACH relies on no longer exists. Nothing tells the sewer to fold the eye out of the way. SK-8
(b)/(c) does not draw the rows. The PT-3 specimen text (`test_kit/guides/G2.md:241`) does not mention them. So the
specimens either carry the same defect, or they differ from the bag.

**Fix:**
- Reorder op 4.05:
  1. Neck + tack HE.
  2. B-18 inside, then sew its rows (top + sides) through B-18 + B-01 **only**.
  3. Fold HE, lay it outside, box-X.
  4. Baste.
- Draw the rows on SK-8, and add "rows first, before HE" to the PT-3 specimen line in `physical_test_kit.py`.
- Add a test that no B-18 stitch line crosses the HE neck footprint (x +/-9 about the CL, z +38 to +63) after the HE
  is placed.

### X-2 HE-ONE moved the eye 38 mm above the frame's hinge pin; the fit is only "settled" by QC-20 on a finished bag

- `designs/pack_5200/patterns_corrie_f_rev3.py:126-139` (HE_FOLD 75, HE_BOX_GAP 4, ASSUMPTION HE-REACH)
- `designs/pack_5200/analysis/corrie_f_body.md:1387-1389`
- `designs/pack_5200/analysis/bag_attachment.md:118, 181`
- `huntkit/gendesign/bag_attach.py:30` (THROAT 18)

The frame pin and fairlead are at **frame z 60**, which is +25 mm above the floor seam line (BC.Z0 = 35). The
attachment design put the **eye top at z 60** (`bag_attachment.md:118`), and the bag goes on by tipping the eyes
"between the cheeks of the z 60 fairlead" (`:181`).

HE-ONE now places:
- the box at +4 to +38 (frame z 39-73);
- the eye at +38 to +63 (frame z 73-98).

The pin sits behind the box, where the stack is 38 mm wide. It is not behind the 18 mm neck that fits the 18 mm
throat.

HE-REACH says the eye "folds out and down onto the pin". That is a 180-degree reversal at the box top. It loads the
box's top row in peel, and it puts the cleat cheeks against the 38 mm box stack. PT-3 (`G2.md:247-251`) pulls in line
"up B-01", and SK-8 (b) labels the upright eye "the pin goes here". The test therefore proves a geometry the bag will
not use on the frame.

The other reading is that the bag sits 25-38 mm lower on the frame. Every sim and placement assumes the floor at
z 35: US channels at z 95/142, the B-12 ports on the IM eyes, the B-27 ports, the CG cases. QC-20 is a final
inspection, done after about 70 h of sewing.

**Fix (pack-designer + structural, before PT-3 is sewn):**
- Choose an HE geometry in which the pin at +25 sits inside the free eye, in the loaded direction, with the 18 mm
  neck in the throat. Examples: a shorter box below a lower eye, or the eye pointing down with the box above it (the
  "alternative not taken").
- Prove it with a 1:1 dry fit: scrap HE + B-01 offcut pinned in a printed z 60 fairlead. Record the result as a
  gate before bag cut, not as QC-20.
- Re-issue PT-3 to pull in that direction through a 5 mm pin in a fairlead-width (18 mm) slot.

---

## MAJORS

### Y-1 PT-3's rig cannot be set up as written, and one reading bypasses the rated floor-seam path

- `outputs/release/test_kit/guides/G2.md:238-262`
- `designs/pack_5200/physical_test_kit.py:505`

The steps call for a pin through the eye **and** two bar clamps: one on the B-05 strip and one on the B-01 top edge.
The G2 rig has two ends (`G2.md:23-26`). If the B-01 top is clamped on the reaction side, B-01 carries the load in
parallel and the B-18 floor seam is unloaded. That seam is the governing capacity, 2355 N, SF 2.31
(`load_points.csv:16`). The specimen text also leaves out the B-18 rows, their order and the step-7 baste (see X-1).

**Fix:**
- Pin in the pin fixture, B-05 strip alone in the bar clamp, B-01 top free.
- State the pull direction from X-2.
- Write the specimen from the reordered op 4.05.

### Y-2 The roll-top clip path (RT/RTM) runs through the rifle muzzle keeper and under W3; the clearance test only looks at the tab

- `designs/pack_5200/patterns_corrie_f_rev3.py:110` (B11_MUZ_X 60 / 130), `:535-544` (RTM)
- `tests/test_bl040_review_fixes.py:106-115`

On the gusset (flat x = depth from the frame seam, y = sigma):
- **RTM tab:** x 99.5-124.5, its bar at sigma 560 (z 595). The female buckle stands about 35 mm above the bar
  (socket UP, op 4.08), to about sigma 595.
- **Muzzle-keeper tabs:** x 68.4-98.4 and x 138.4-168.4, from sigma 590.2 (z 650). The MK shock-cord loop runs
  between them (op 7.22).
- **RT strap:** comes down from the roll end at the gusset centre (z >= 745) to the buckle. It must pass through the
  40 mm gap between the muzzle tabs and across the MK cord.
- **W3:** crosses the gusset at z about 703 (K-W keeper, `README` volatile line).

Results:
- A rifle muzzle in the keeper sits on the roll-clip strap.
- W3 cinched traps the strap, so the roll top cannot be opened without letting W3 off.
- The buckle body comes within 0-3 mm of the forward muzzle tab.

`test_rtm_clear_of_the_other_gusset_placements` checks only the 25 x 35 mm tab rectangle. It ignores the buckle
envelope and the strap path. FIT-R3 (G7 `#4`) does not test the rifle and the roll clip together.

**Fix:**
- Pack-designer: move the muzzle-keeper pair clear of the gusset centre, or move RTM, or route RT outside W3.
- Extend the test to the buckle envelope (25 x 35 mm above the bar) and to the strap corridor from the hem to the
  buckle.
- Add a FIT-R3 row: "roll clip opens and closes with the rifle in the muzzle keeper and W3 cinched".

### Y-3 The minimum prototype machine cannot sew the 304 bartacks the ops (and PT-3) call for

- `designs/pack_5200/mfg_corrie_f_rev3.py:81-98`
- `designs/pack_5200/BUILD_PLAN.md:37`
- `manufacturing/README.md:29`

The spec is "a walking-foot lockstitch, DPx17 to 140/22, tex 135, 6 mm clearance". It does not require zigzag. A
straight-stitch-only walking foot meets it, for example the WF2 class the tech pack names (DNU-1541S).

ISO 304 is called for in:
- the HE neck BT-M tacks (op 4.05, and therefore every PT-3 specimen);
- B-27 slit ends (4.03), I2K (4.06), FP mouth corners (4.10), B-16 corners (4.14);
- lid channel ends (6.03), BRL/BRS (7.20/7.21);
- the four elastic-keeper laps (7.04, 7.09, 7.13, 7.18);
- the B-25 laps.

The prototype fallbacks cover only box-X ("BT ... Prototype: box-X on WF2 with the J1 template"). Nothing covers a
304 tack. The owner has not bought a machine yet, so this is the moment to get it right.

**Fix:** either add "and sews a 304 zigzag up to 5 mm wide (e.g. a portable straight / zigzag walking foot)" to
PROTO_MACHINE_MIN and BUILD_PLAN, or define a 301 substitute tack (e.g. 4 passes, 16 mm, at 2 mm stitch) for every BT
and ZZ op. Sew the PT-3 neck tacks the same way.

### Y-4 M-7 raised TL-1 to 432 N without re-running the crown-bar wall check: the proof will likely crush the tube

- `designs/pack_5200/analysis/loadpath_verification.md:213-216`
- `designs/pack_5200/tests_physical/test_register.csv:26`
- `outputs/release/test_kit/guides/G2.md:378-399`
- `designs/pack_5200/analysis/frame_cg_recheck_results.json` (`bar_local`)

TL-1 pulls a 25 mm loop round a bare OD 18 CF tube to 432 N. Its pass criterion includes "no crush mark on the tube".
The release's own local check of that geometry, "crown bar wall under a 25 mm loop (bare bar)", has a **capacity of
295 N**: demand 244.5 N, ratio 1.21. The register still quotes "bar wall 1.21" on the old 244 N basis.
`frame_cg_recheck` `bar_local` gives a 25 mm tie an SF of 1.08 at 210 N, which is about 228 N.

So:
- At the new **288 N** factored guy envelope the bar wall is at about 1.0 (or below on the 228 N basis).
- The 432 N proof is 1.5-1.9 x the computed capacity.

TL-1 is a BAG-CUT gate (`order_of_work.csv:20`). The test is expected to fail, and the frame margin it should prove
is not there on paper. `corrie_f_body.md:624` ("288 N against 312 N, strength 1.36") is the bar's bending check, not
this local ring-crush.

**Fix:** have the structural-fea-engineer re-run A3 bar-local at 288 N / 432 N, before G2. Either widen the GBL loop
or the B-25 sleeve bearing (the `bar_local_width_sweep` shows SF 1.65 at 38 mm and 2.17 at 50 mm at 210 N), or credit
the corner wrap. Then set TL-1 to the geometry actually built, and update `loadpath_verification.md` A3 and the
register margins.

### Y-5 Camo: the only buyable print is on a different base fabric (HyperD 300) than the one the patterns, BOM and QC-14 use (630D), and its gate is not a bag-cut gate

- `manufacturing/README.md:30`
- `bom.csv:23`
- `camo/README.md:84-90, 113-119`
- `test_kit/order_of_work.csv:42`

For 1-10 bags the camo release gives one orderable route: **A**, RBTR HyperD 300 (`polyester_300d_printable`,
133 gsm), "gated by AB-1". The 630D the patterns, cut list, `fabric` BOM line and QC-14 assume has "no small-batch
custom-print source" (route C, $1,362 MOQ).

The manufacturing release never says which base the owner should cut B-02u, SH-07, SH-01b, FP-b, B-29f and A1-d from.
B-02u is a structural panel: two 715 mm corner seams, the floor seam and the #10 door zip.

AB-1 sits in G5 as a "grams" / BL-037 test, not a BAG-CUT gate. A HyperD bag weighs about 0.201 m2 x (290 - 133)
gsm = **about 32 g less** than the QC-14 primary target of 1197 g (-2.6 %, close to the +/- 3 % limit). The $498 buys
1 yd of 630D ($18) **and** 1 yd of HyperD print ($30.25).

**Fix:** state the first-build base in the manufacturing README and BOM. Either:
- (a) solid 630D (route D) for B-02u, with camo accents only on the non-structural pieces; or
- (b) HyperD for the camo pieces, after AB-1 + FRAY-1 (HyperD | 330D) pass. In that case move AB-1 to BAG-CUT, give
  QC-14 a HyperD target and drop the duplicate yard from the prototype buy.

---

## MINORS

| # | File:line | Finding | Fix |
|---|---|---|---|
| n-1 | `test_kit/guides/G4.md:110-111`; `physical_test_kit.py:474`; `results_template.csv:145-147` | IM3-EC says "R <= 0.02", but 24 -> 1178 N is R 0.0204. The countersign says "F_min about 24 N" | F_min 23 N (R 0.0195), or write "R about 0.02" |
| n-2 | `test_register.csv:14`; `order_of_work.csv:1,27`; `G4.md:55` | CA-1 is still titled "0.30 then 0.40". The fallback table lists 0.429 / 0.469 for swings above 117 %. Those levels are above the failed 0.40, so they cannot be fallbacks, and the countersign (`ca1_mt1c_confirm.md:102`) says that case needs a cinch re-run instead | Retitle "0.40 (fallback >= 0.313)". Cut the table at 115 % and add "swing > 117 %: stop, structural re-run" |
| n-3 | `physical_test_kit.py:486`; `G2.md:322-324` | LL-H's COLD step breaks across steps 3/4 at a parenthesis, so the "hold 10 min" instruction is buried in step 4. The record asks for -20 C; a home freezer gives -18 C (FREEZER_MAX_C) and no allowance is stated. Cold holds 10 min against 1 h dry / wet | Make COLD its own step. State that -18 C is accepted as the record's -20 C (or use dry ice) |
| n-4 | `mfg_corrie_f_rev3.py:1245, 1308`; `op_sequence.md:188, 254` | Points to "op 7.end", which does not exist (fitting is op 7.23) | Use the real op number |
| n-5 | `manufacturing/sketches/SK-10_roll_top_clip.png` (b); `SK-1_load_point_patterns.png` | SK-10 (b): the RTM callout overprints the y-axis label ("8RTM"), and the axis is sigma while the callout says "z 595". SK-1: the right column is clipped (the 34 x 20 label, the B-24 stitch text and the BT-M text are cut off) | Re-layout both. Label the SK-10 axis "sigma (mm along the gusset)" |
| n-6 | `patterns/print_letter/step2_small_parts.pdf` p.2 (tile A1) | On paper, the B-18 NOTE prints over the B-22 NOTE, and the B-22 NOTE is clipped at the tile edge. The M-4 text ("INSIDE B-02h ... coated face to the band") and B-18's "lower edge ON the B-01 cut edge" cannot be read on the printed pattern. The DXFs are correct | Wrap the notes, or move them into the piece and the step map |
| n-7 | `patterns/print_letter/*.pdf` (no `poly_webbing` piece in any) | The HE neck lines, neck-tack lines, EYE FOLD and box, the RTM fold and box, and the RT 60 mm zone exist only in the DXFs and the SK-8 / SK-10 sketches. The beginner gets no 1:1 webbing template for op 4.05 | Add a 1:1 webbing-marks page to step 2 (HE, RTM, T3, LLT, US) |
| n-8 | `load_points.csv:2, 11`; `manufacturing/README.md:32` | (a) Row 2 (TG toggle end) names the heavy ladder lock as its hardware; that end carries the POM toggle (670 N, loadpath A3). (b) Row 11 GBL is still 244 N while B-25 / TG use 288 N. (c) The README gives "lowest SF 1.93" without the "pending PT-2" label row 14 carries (m-3) | Correct the hardware column and the load. Add "(pending PT-2)" to the README line |
| n-9 | `BUILD_PLAN.md:39, 60, 80` | The thread list omits `bonded_nylon_tex70`, which 13 ops use (1.01-1.05, 3.02, 5.01, 6.11-6.12, 8.02, 9.01-9.02), and lists the unused `bonded_poly_tex90`. Lines 60 and 80 still say box-X on "120/19", against line 37 (140/22) | List tex 70 / 90 / 135 bonded nylon. Change 120/19 to 140/22 |
| n-10 | `costing.md:30, 68-73`; `costing.json` `prototype_buy` | The $497.72 adds up (41 rows, checked), but a one-off buyer cannot buy it: thread is priced per metre (31.6 / 82 / 123.8 m = $1.45) when it comes in cones, and seam sealer and basting tape are priced as fractions. The $12 print shipping in `camo/cost_1_and_10_bags.csv` is left out | Round thread, sealer and tape to the smallest purchasable unit. Add the print shipping. Report the corrected one-bag total |
| n-11 | `analysis/bag_attachment.md:118-119`; `huntkit/gendesign/attach_system.py:381-383, 726` | The old HE / B-18 definition is still live in the design sources: fold back 50, tri-fold neck, box-X 38 x 38, B-18 90 x 45, rows on four sides, "eye top at z 60". PT-3's "Defined in" points to `bag_attachment.md` | Mark those rows superseded by HE-ONE, or regenerate them from the rev 3 module |
| n-12 | `tests/test_bl040_review_fixes.py:41`; `mfg_corrie_f_rev3.py:1727-1734` | `assert ... or True` is a tautology. `box_mismatches` compares box sizes only (not position), and silently `continue`s when a piece id is missing, so a renamed piece passes | Delete the tautology. Make a missing piece an error. Compare the box centre to the placement (+/- 1 mm) |
| n-13 | `test_kit/guides/G4.md:155-170` | SEW-F's peak is 1.0 x the 1.6 g S6 load (384 N). Every other fatigue proof in the kit carries the 1.15 scatter factor (IM3-EC 1.15 x 1024 N) | 1.15 x 384 = 442 N peak, or record why box-X fatigue gets no scatter factor |
| n-14 | `op_sequence.md:177`; `patterns_corrie_f_rev3.py:130` (ASSUMPTION HE-GAP) | The floor seam runs 4 mm from the edge of the HE box stack (2 plies of 38 mm webbing + Hypalon). A walking foot (about 5-6 mm half-width) will ride up on that stack exactly at the rated seam | State in op 4.15 to sew the hinge-eye spans with the zipper / edge foot, and sew the PT-3 floor seams the same way |
| n-15 | `manufacturing/README.md:98` (m-19 accepted) | Accepting "no strap topology sketch" leaves the IM1 / IM2 cam with no sewn anchor ("cam threaded") on an MT-3-rated meat path | Pack-designer draws SK-7 per strap before step 7 (not before cutting) |

---

## Status of every earlier finding (verified in the files, not taken from the README table)

| ID | Status | Evidence / remaining issue |
|---|---|---|
| B-1 | **fixed, new problem** | One box (34 x 34) on HE / B-18 / B-01 / op 4.05 / load row / PT-3. `box_mismatches` now covers 8 stacks. B-18 is 90 x 62, its lower 12 mm in the floor seam, rows on three sides. New: X-1 (rows cross the eye), X-2 (eye off the pin), Y-1 (PT-3 rig and specimen), n-11 (stale source), n-14 |
| B-2 | **fixed, new problem** | RTM piece (25 x 70, x2) and BOM pairs. Placement on B-03 at z 595, 107.8 / 215.7 mm depth. RT boxes on B-07 (L x 967-1027, R x 382-442). Op 4.08 comes before 4.12 (so early enough for the gusset seams) and 5.02 before 5.03. Load rows are unrated. New: Y-2 (path clash), n-4, n-5 |
| B-3 | fixed | Op 4.13 states the stack. SK-9 matches it: gusset, mesh, K-W loop, blade U; loop ON TOP, pointing into the gusset; it turns out over the pocket. Op 4.10 bastes the FP aft edge in the allowance only |
| M-1 | fixed | Op 4.12: one B-26 end at the frame seam. Op 4.13: free end at the 'B-26 keeper' notch. Both notches are on the gusset |
| M-2 | fixed | B-17 box 34 x 34 (`patterns_corrie_f_rev3.py:638`). It matches T3 and load row 13 |
| M-3 | fixed | Gusset ring notches 0 / 50 / 100 / Lg from the frame end. B-06 partners within 1 mm from both frame corners (test) |
| M-4 | **partly fixed** | DXF/label text is correct (INSIDE B-02h, x 130.3, z 695, coated face to the band), but it cannot be read on the printed tile (n-6) |
| M-5 | fixed | DECISION GUY-LOCK-IN. Body 13.5 (line 602), PORT-1 step 6 and release_tests all updated |
| M-6 | fixed (see Y-5) | QC-14 primary 1197 / 1501 / 1706 g; costing.md publishes them. Only valid if the camo pieces are 630D |
| M-7 | **fixed, new problem** | LL-H, TL-1 and the B-28 rows at 432 N. Hardware columns are added (490 N lock, margin 1.70). New: Y-4 (bar wall), n-8 |
| M-8 | fixed (n-3) | MT-3 and LL-H are dry / wet / cold. The cold step text is mangled and the freezer temperature has no stated allowance |
| M-9 | fixed (n-13) | SEW-F is in G4 (3 loops, 38 -> 384 N, 1e5, then 1080 N) and in the register / results |
| M-10 | **partly fixed** | camo/ release, BOM print line, sublimation caveat and originality note are all there. Which base fabric to cut is unresolved (Y-5) |
| M-11 | **partly fixed** | Prototype-buy column and total are published and the arithmetic checks. The total is understated (n-10) and double-buys the camo base (Y-5) |
| M-12 | **partly fixed** | Needle system / size / thread match the ops (DPx17, 90/110/140, tex 70/90/135). The zigzag requirement is missing (Y-3), and BUILD_PLAN contradicts itself (n-9) |
| M-13 | fixed | Op 1.01: "baste across the BOTTOM edge only ... top stays 260 mm" |
| m-1 | fixed | `test_physical_test_kit.py` passes in the full run |
| m-2 | fixed | Hinge 1019 N, SF 2.31, PT-3 1530 N |
| m-3 | fixed (n-8c) | Row 14 note says pending PT-2. The README headline does not |
| m-4 | fixed | B-09p slot is a `cut_inside` |
| m-5 | accepted | Agree: pockets, no load |
| m-6 | fixed | Per-channel elastic 325 / 289 / 2 x 151 / 2 x 761 = 2438 mm; hems sum to 3248 mm; lap text removed |
| m-7 | fixed | Swell slot is a mark. The B-12 slot is the only cut |
| m-8 | fixed | 6.03 tex 90; 6.04 turns 8 mm; 6.11 is SSa2 |
| m-9 | fixed | Op 10.02 points to QC-12 to QC-20 |
| m-10 | fixed | Op 2.04 folds the seam-inserted loops before step 4; no stitching after insertion |
| m-11 | fixed | B-11 slot is 27 x 5 (DXF and PDF) |
| m-12 | fixed | Left gusset: "light lash only, no load rating" |
| m-13 | fixed | Pipes are escaped in `pattern_checks.md` |
| m-14 | fixed | Patterns README: 45 fabric types + 32 webbing types = 77; cut-list hardware matches the BOM (buckles x2, etc.) |
| m-15 | fixed | B-24 label says carabiner (test); SK-3 caption is regenerated |
| m-16 | accepted | Not re-measured. Squares are now 100.00 / 101.60 on every step 2 page |
| m-17 | fixed | QC-13 records the expected 81.9-84.0 L |
| m-18 | fixed (Y-2) | FIT-R3 in G7 covers LID-DART, B11-PLACE, IM2 notch and the carabiner gate. It does not cover rifle + roll clip |
| m-19 | accepted, I disagree | See n-15 |
| m-20 | fixed | Op 3.08 turns the allowances away from B-22 |
| m-21 | fixed | Previews 1210 x 935 at 110 dpi |

## Specific checks requested

- **HE-ONE (B-18 enlargement):** not sewable in the stated order (X-1). It does not meet the z 60 pin (X-2). PT-3
  matches the box, fold, B-18 size and seam capture, but leaves out the rows / order and has an ambiguous rig (Y-1).
- **RTM roll-top tabs:** the parts and placements are drawn, and op 4.08 comes before the gusset seams (4.12 / 4.13),
  so it is early enough. The placement clashes with the muzzle keeper and W3 (Y-2).
- **SK-8 / SK-9 / SK-10 against the patterns:**
  - SK-8 (a) matches the HE DXF: neck lines 50 / 100, tacks 56 / 94, boxes 16-50 / 100-134, seam lines 12 / 138.
    SK-8 does not show the B-18 rows, and its "pin goes here" contradicts HE-REACH.
  - SK-9 matches op 4.13.
  - SK-10 (a) matches the B-07 rectangles and boxes; (b) has a label clash and an axis mismatch (n-5).
- **R1 rule:** the test kit (G4 CA-1, G6 MT-1c, register, TEST_PLAN, CA1_fatigue_rig) matches the countersign: 0.40
  with 3/3 run-outs, swing <= 117 %, mean <= 150 N, fallback >= 0.313. Residue in n-2.
- **Test loads:**
  - LL-H 432 N / 44.0 kg and TL-1 432 N match 1.5 x 288 N, but TL-1 exceeds the computed tube capacity (Y-4).
  - IM3-EC: 1178 N, 32 deg aft, F_min 24 N and the R 0.1 alternative of 1272 N all match the countersign. R 0.0204 is
    over the stated 0.02 (n-1).
- **Cost and machine:** $497.72 is reproduced exactly from `costing.json`, but it is understated (n-10, Y-5). BUILD_PLAN
  matches the needles and the tex 90 / 135 thread, but leaves out tex 70 and zigzag (Y-3, n-9).
- **Scale and DXFs:** PDFs print 1:1 on Letter. DXFs are in mm at scale 1, with closed outlines and grain on every
  piece.
