# Pre-cut THIRD review: CORRIE F rev 3 bag release after BL-041 (independent, adversarial)

design-reviewer, 2026-11-13. I checked the BL-041 claims ("0 blockers, 0 majors", `corrie_f_body.md` §21,
`manufacturing/README.md:58-100`) against four sources: the regenerated release
(`outputs/release/pack5200_corrie_f_rev3/`, `outputs/release/test_kit/`), the code, the frame print files
(`designs/pack_5200/print/frame_h1/`, `designs/pack_5200/print/frame/`) and `frame.yaml` / `attachment.yaml` /
`geometry.yaml`. I did not take any README status as evidence.

**Counts: 2 blockers, 4 majors, 14 minors.**

**Verdict: NOT ready to cut.**
- As drawn, the hinge eye cannot wrap the pin inside the fairlead.
- The frame file that HE-FIT tells the owner to print has no working fairlead.
- HE-FIT, a bag-cut gate, will therefore fail or cannot be run.

Every review-2 item is fixed or carried as a minor, except X-2. Its fix (HE-PIN) brought in Z-1.

## What I ran

- **Full suite.** `HUNTKIT_BPY=.../bpyenv/bin/python python -m pytest -q`:
  **1044 passed, 4 skipped, 0 failed, exit 0 (16 min 06 s)**. The working tree is unchanged afterwards (`git status`
  clean). No test covers Z-1, Z-2, M-1, M-2 or M-3. One test enshrines the zero-clearance neck
  (`tests/test_bl041_recheck_fixes.py:55`, `neck_w == throat`).
- **Manufacturing check.** `python designs/pack_5200/mfg_corrie_f_rev3.py --check`:
  - 86 ops, 29 load points, min SF 1.36 (B-25);
  - `box_mismatches: []`, `holds: []`, `unsequenced: []`;
  - thread 18.56 g against 18.55 g in the ledger;
  - recon 0 unmatched.
- **Pattern geometry.** Rebuilt via `mfg_corrie_f_rev3.package()` / `build_ctx()`. Dumped `rs.geo` (`he`, `rtm`,
  `rt_layout`, `rt_clear`, `rt_on_b07`, `b11`, `kw_z`, `b25`) and the internal lines of HE, RTM, W3G, IMC, B-25,
  RT, B-18 and B-03.
- **HE section model.** Evaluated `he_geometry()` / `he_pin_z()` outside the tested bracket: wrap thickness 3.0 and
  4.5 mm, and leg angles at both B-01 faces.
- **Frame files.** Sectioned `print/frame_h1/h1_assembled.stl` and `print/frame/genframe_assembled.stl` with trimesh
  and shapely, rasterised at 0.5-1 mm in the z 60 hinge zone and at every fairlead station (z 95, 142, 190, 330,
  520). I compared each with `bag_attach.fairlead_local` placed by `attachment_field` (stay centre `_sleeve_y(60)`
  -1.12, `stay_radius(60, 1.05)` 9.35).
- **PDFs.** Rasterised `step2_small_parts.pdf` pp. 2, 8, 9 and 10 and read them:
  - pp. 9-10 are the new 1:1 webbing pages;
  - pdfplumber measures HE 38.00 x 86.00, box 34.00 x 10.00, RTM 25 x 70, W3G 25 x 60, LLT 25 x 70, IMC 25 x 180,
    T3 38 x 160, test squares 100.00 / 101.60. **Scale is 1:1.**
- **Sketches.** Viewed SK-1, SK-7, SK-8, SK-10 and SK-11.
- **Text.** Read op 4.05, 4.08, 4.15, 7.13-7.23, `load_points.csv`, `bom.csv`, `cutting_plan.csv`, `costing.md`,
  `BUILD_PLAN.md:37-39`, `crown_tube_guy_loop.md`, and G2 (HE-FIT, PT-3, TL-1, TL-1b) and G4 (SEW-F, IM3-EC,
  CA-1).

---

## BLOCKERS

### Z-1 The necked eye cannot pass between the pin and the fairlead's throat floor, and HE-PIN's section model leaves that floor out

- `designs/pack_5200/patterns_corrie_f_rev3.py:141, 151-177` (`HE_NECK_EDGE`, `he_geometry`: `r = PIN_D/2 + t/2`,
  single ply)
- `:1385-1390` (neck lines at 26 / 60 = the whole 17 mm eye is neck)
- `huntkit/gendesign/bag_attach.py:79-89` (`root_hi_y = y_hole - HOLE_D/2 - 0.8`)
- `tests/test_bl041_recheck_fixes.py:55`
- `outputs/release/test_kit/guides/G2.md:104-128` (HE-FIT)

**The throat has a floor.** The fairlead's root bridges the throat at `y_hole - 4.4 mm`. The 5 mm pin's underside is
at `y_hole - 2.5`, so the clear gap under the pin is **1.9 mm**. In the released frame mesh
(`print/frame/genframe_assembled.stl`, z 60) the floor is at y 10-11 and the pin underside at 12.24 (gap about
1.2-2.2 mm), which confirms it.

**The eye must go through that gap.** It is a closed loop round the pin, so one ply of it passes on the stay side
of the pin, between the pin and the floor.

**The eye is the neck.** Op 4.05 step 1 folds each long edge 10 mm in over the full span between the neck lines.
That span (26-60 mm on the 86 mm strip) is exactly the two 17 mm eye legs, so the wrap is folded webbing:
- 2 plies over most of the 18 mm width, 3 plies over the middle 2 mm;
- at HE-T 1.5 mm that is **3.0-4.5 mm in a 1.9 mm gap**;
- even a single 1.5 mm ply clears by only 0.4 mm.

**The model counts one ply.** `he_geometry` models the wrap as one ply (`t` 1.2-2.0 mm) and never models the root.
With the real wrap thickness the solved 17 mm eye puts the loaded pin at **21.5-23.8 mm** above the seam line (my
run of `he_pin_z(17, face, t=3.0 / 4.5)`), not 23.4-25.3.

**The cheek clearance goes too.** Box top +14 against cheek bottom (pin - 9) leaves no clearance once the pin is
below 23 mm. At 21.5 mm the 4-ply box stack sits 1.5 mm up into the cheeks: the "no peel / box below the cheeks"
premise is gone.

**Zero side clearance.** The 18 mm neck in the 18 mm throat has none, and a test now asserts that equality.

**Consequences.** HE-FIT, as specified, will fail:
- the pin cannot be pushed through cheek, sleeve, eye, cheek with the eye seated; or
- the pin reads below 23 mm with the box against the cheeks.

Its stated remedy ("re-solve HE_EYE from the measured webbing thickness") fixes neither.

**Fix (pack-designer + structural, before HE-FIT is sewn).** Make the wrap a single ply that fits the floor gap with
margin. For example:
- (a) neck only the straight legs below the pin line, with a separate 18-20 mm webbing (or a 1-ply Dyneema / thin
  tape) eye loop box-X'd into the 38 mm HE;
- (b) frame side: lower the throat floor / raise `HOLE_PROUD`, which is a fairlead change on every station.

Then:
- add the root floor to `he_geometry` (clearance check: wrap thickness <= floor gap - 0.5 mm);
- solve the eye on the real wrap thickness;
- give the neck >= 1 mm side clearance and replace the `neck_w == throat` test with a clearance test;
- redraw SK-8 (c) with the root floor.

### Z-2 The H1 frame STL (the file HE-FIT and IM3-EC print from) has no working fairleads: they are clipped at the bag envelope

- `designs/pack_5200/physical_test_kit.py:303` and `:1318` ("one hinge fairlead printed 1:1 **from the H1 STL**")
- `:584` (IM3-EC "cut from the H1 STL")
- `huntkit/gendesign/frame_topopt.py:157` (`void = y > env.y_hi(z)`; `Y_HI_GRID = 16`, `:65`)
- `huntkit/gendesign/frame_h1.py:313` (`fairleads present` counts only voxels **outside** `passive_void`)
- `huntkit/gendesign/frame_h1.py:721-770` (`print_mesh` cuts bores and bolts, no fairlead holes)
- `designs/pack_5200/print/frame_h1/README.md:34` (claims "IM3 eye holes printed at 7.0")

`h1_assembled.stl` bounds stop at **y = 15.46** everywhere. The fairleads should reach `_sleeve_y + stay_r + 14.1`,
about y 21-25. Measured sections:

| station | H1: material max y | designed pin y / cheek tip y | what is in the H1 file |
|---|---:|---|---|
| hinge z 60 | 15.5 | 14.74 / 22.34 | cheeks cut off at y 15.5; the pin hole is an **open slot facing the bag** (no front wall to bear the pin); the throat at the pin line is **solid** (x 110-121, y up to 15.4, z 54-64), so neither pin nor eye can pass |
| US1 z 95 / US2 z 142 | 10.1 / 10.2 | 13.9 / 12.8 | no hole |
| IM1 z 190 | 14.8 | 17.0 | no hole |
| IM2 z 330 | 11.8 | 14.1 | no hole |
| IM3 z 520 | 9.9 | 13.5 | cheeks y 3-10 only, **no eye hole**, contrary to the README |

For comparison, the released `print/frame/genframe_assembled.stl` at z 60 has:
- cheeks to y 21;
- a ring with a front wall at y 18-21;
- an open throat above y 11.

So the clipping is an H1 export regression. `keepouts()` reports "fairleads present 1.000" because the clipped voxels
are excluded from the denominator.

**Consequences.**
- HE-FIT (BAG-CUT gate, run order 9) prints a fairlead the eye cannot enter.
- IM3-EC (R1 gate) prints an eye coupon with no eye.
- The HE-PIN numbers that depend on the cheek tips pushing B-01 to y 23.45 (`faces_y`) do not describe the H1
  frame.

**Fix (structural-fea-engineer, frame side).**
- Union the full `fairlead_local` SDF after the envelope clip, and cut the pin holes as exact features in
  `print_mesh`.
- Add tests:
  - pin line clear;
  - cheek tip at `y_hole + 7.6`;
  - throat empty above the root on every station of the exported STL.
- Correct the H1 README.
- Until then, point HE-FIT at a fairlead generated from `bag_attach.fairlead_local` (or cut from
  `print/frame/genframe_assembled.stl`).

---

## MAJORS

### M-1 RT-OVER-W3 and the W3G guide hold at one torso setting only: W3 is anchored to the crown bar, which moves 25.4 mm per inch

- `designs/pack_5200/patterns_corrie_f_rev3.py:209-211, 226, 243` (`z_w3 = kw_heights(c)["W3"]["R"]` = 702.6)
- `designs/pack_5200/geometry.yaml:692` ("crown top bar R (moves with torso)")
- `geometry.yaml:100, 145, 172` (`crown_top_z` 601.0 at 15 in, 664.5 at 17.5, 702.6 at 19)
- `outputs/release/pack5200_corrie_f_rev3/manufacturing/op_sequence.md:149, 342`

**W3 moves with the torso setting.** Both W3 anchors are on the crown bar, so W3 runs level at the crown-bar height
while the bag stays fixed on the hinge. Its crossing on the gusset is:
- z 664-741 over crown kit M (17.5-20.5 in);
- z 601-677 for kit S.

**The guide fits only 19 in.** The W3G window (tacks 36 mm apart) is z 685-721, centred on 19 in only. Op 7.23 says
W3 "stays threaded" under W3G, so at any other setting:
- W3 is kinked through the guide;
- its 225 N factored haul tension loads the two W3G tacks sideways. These are unrated BT-S 304 tacks through one
  ULTRAGrid ply.

At kit S settings W3 lies across the RTM buckle envelope (z 611-646) and the B-26 cord (z 600). That is the Y-2 clash
again. `rt_clearances` and `test_bl041` evaluate W3 at 19 in only. The K-W keepers (z 703) have the same dependence,
which was already parked on T9.

**Fix.**
- Make the W3 crossing a function of the kit's torso range.
- Either:
  - replace W3G with a guide that spans the whole kit range (a tall channel, or two keepers), with its tacks rated
    for W3's deflection load; or
  - re-route RT outside W3's sweep.
- Add FIT-R3 rows at both ends of the owner's kit.

### M-2 The roll-clip path was moved off the roll end without re-running the roll model; "RT cut 510 unchanged" only accounts for the 16.5 mm rise

- `designs/pack_5200/patterns_corrie_f_rev3.py:587-605` (strap leaves the hem at `frac_top` 0.269 of the gusset
  depth)
- `:230-247` (tab at x 91, 80 mm / 211 mm = 38 % depth)
- `huntkit/viz3d/cloth_pass.py:1052-1064` (the model's strap runs from the roll END to the tab at gusset mid-depth,
  `ymid`)
- `corrie_f_body.md:1442-1449`

**What the roll model assumed.** The cloth-pass roll clips (`corrie_f_roll_clips.json`, 161-375 mm free length) were
solved with the strap at the gusset centre, which is where a flattened, rolled mouth puts its end.

**Where BL-041 put it.** The strap now leaves the hem 27 % of the gusset depth from the frame corner. On a mouth
flattened fore-aft with the gussets tucked in, that point sits about 0.23 x the top gusset depth (about 45-55 mm)
inboard of the roll end, inside the gusset tuck. The tab moved 12 % of the depth forward and 16.5 mm up.

**What was not checked.** The model does not solve the roll (`cloth_pass.py:18`), and no physical roll check gates
the B-07 and B-03 marks. Moving them later means unpicking two box-X's per side (op 5.02 and op 4.08).

**Fix.** Before cutting, do one of:
- re-run `cloth_pass` roll clips with the new strap origin and tab; or
- make a 1:1 paper / scrap-collar roll mock-up a BAG-CUT gate: strap exits the roll end, not the tuck, and the free
  length is measured.

Then update the RT cut and T9.

### M-3 The 34 x 10 box at the governing joint is neither "in line" nor fatigue-covered, and PT-3 does not load it as the frame will

- `designs/pack_5200/analysis/corrie_f_body.md:1430` ("in line with the pull: no peel")
- `outputs/release/test_kit/guides/G2.md:283-286` (PT-3: pin in an 18 mm slot, "pull in line DOWN B-01")
- `designs/pack_5200/physical_test_kit.py:448-450` (SEW-F covers 21 x 25 on 25 mm loops only)
- `load_points.csv:15`

**The legs pull out of plane.** Using BL-041's own section numbers:
- pin at y 15.85;
- B-01 face 20.0-23.45;
- box top 1.5 mm off the face at +14, pin at +25.

The two eye legs leave the box top at **-3 to 14 deg** (inner leg) and **30 to 44 deg** (outer leg) from the panel
plane. With the folded neck (Z-1) the angles grow. So the top row of a 10 mm-tall box carries a peel component of
about 0.5-0.7 of the outer leg's share.

**PT-3 does not reproduce it.** It pulls the specimen in line through a slot, with no offset toward the frame.

**No fatigue test covers it.** SEW-F covers only 21 x 25 boxes on 25 mm loops. At 1.6 g the hinge sees about
1.6 x 1019/3 = 544 N, so with the kit's 1.15 scatter the box needs **about 625 N peak**. That is above SEW-F's
442 N peak, on a box shape SEW-F does not cover.

**The row is unsupported.** `load_points.csv:15` gives no capacity for the 34 x 10 box itself. The static model
credits thread path only, not the three perforation lines in B-01 within 14 mm (seam, +4, +14).

**Fix.**
- PT-3 fixture: put the pin centre 4-6 mm toward the frame from the B-01 face and 11 mm above the box top (a printed
  fairlead segment, once Z-2 is fixed).
- Add 3 HE specimens to SEW-F at 1.15 x 1.6 g hinge load.
- List the 34 x 10 box capacity and its basis in the load row.
- Drop "no peel" from §21.

### M-4 The 38 mm B-25 has no drawn topology between the sleeve and the spine wrap, and TL-1 tests a sleeve the frame will not have

- `designs/pack_5200/concepts/corrie_f.py:1323` (`SPINE_CLAMP_HALF = 15.0 # ASSUMPTION ... settled by the clamp
  drawing`; no clamp drawing exists in `frame.yaml` / `print/`)
- `:1328-1330, 1443` (run = 2 x 11.5 mm)
- `outputs/release/test_kit/guides/G2.md:40, 417`
- `crown_tube_guy_loop.md` §5 (WIDE_SLEEVE)

**The bridle has to turn.** `guy_bridle()` runs the bridle round the bar (sleeve, webbing length circumferential,
width along x 26.5-64.5), then "along the bar and round the spine below its clamp".

**There is no room to turn.**
- Going from a circumferential sleeve to a run along x is a 90-degree turn. In a 38 mm strip a 45-degree fold
  takes up about 38 mm.
- The run from the sleeve's inner edge to the assumed clamp is **11.5 mm**.
- The 38 mm spine wrap also needs 38 mm of bare spine below the clamp. That is unchecked.

**Nothing shows it.** No sketch or 1:1 page shows B-25 on the bar (SK-7 shows only the flat strip), and B-25 is not
on the webbing marks pages.

**The test does not cover it.** TL-1 sews an isolated sleeve on a 160 mm bar, so it proves the 38 mm bearing
(WIDE_SLEEVE) on a geometry without the turn. The bar-wall SF 1.36 / 1.27 and the 11.5 mm clamp clearance both rest
on that bearing.

**Fix.**
- Draw B-25 on the crown (sleeve, turn, run, spine wrap) with the real clamp dimensions.
- Dry-fit it on the crown before the laps are tacked (a gate in op 7.17).
- Build the TL-1 specimen with the turn and run as on the frame.

---

## MINORS

| # | File:line | Finding | Fix |
|---|---|---|---|
| m-1 | `test_kit/guides/G2.md:121`; `physical_test_kit.py:917` | HE-FIT passes the pin at 22-28 mm, but the box top (+14) clears the cheek bottom (pin - 9) only when the pin is at 23 mm or more, and only keeps HE-CHEEK's 2 mm when it is at 25 mm or more. Criterion 2 catches a low pin; the number band contradicts it. | Set the band to 25-28 (or 23-28 with HE-CHEEK restated). |
| m-2 | `op_sequence.md:138, 150` | The op 4.05 / 4.08 headers give one spec for the whole op (BT/PS, 140/22, tex 135, 7 SPI, 301). The ops also contain the B-18 rows (rated as 8 SPI tex 90 rows, 3277 N), the BT-M neck tacks and the W3G BT-S tacks (304, tex 90). On the WF2 prototype these need the BT-301 fallback, and the ops do not say so. PT-3 is "sewn exactly as op 4.05". | Give per-step machine / needle / thread / stitch, and name BT-301 where it applies. |
| m-3 | `outputs/release/.../sketches/SK-1_load_point_patterns.png` (BT-S 10 x 2); `op_sequence.md:149`, `patterns_corrie_f_rev3.py:701` (W3G "BT-S (16 x 2)", 16 mm line) | The BT-S size is 10 mm in SK-1 and 16 mm on the W3G pattern and in the op. | Use one size (BT-M 16 x 2 for W3G) or redraw. |
| m-4 | `patterns_corrie_f_rev3.py` IMC piece (folds 45 / 135, boxes 63-88 / 92-117) | Both folded raw ends end only **2 mm** past their box (the strip end lands at 90 between the boxes). Every other tab keeps 5 mm or more (RTM, LLT). This is on a 605 N rated path. | IMC 190 mm with the boxes 5 mm in from each raw end, or move the boxes. MT-1 IMC specimens must match. |
| m-5 | `op_sequence.md:303` (7.13) vs `:342` (7.23, bench) | Op 7.13 closes both IMC loops. Op 7.23 then "fits" the cam and G-hook at the bench, but neither has a gate, so they must be in the loops before 7.13 sews. Op 7.13 does not say "thread the cam anchor bar and the G-hook bar into the loops before sewing" (the IM3 carabiner can go on later). | Add that sentence, with the hardware listed for op 7.13. |
| m-6 | `patterns_corrie_f_rev3.py:1226, 1240` | B-25 keeps the 21 x 15 box on 38 mm webbing, leaving 8.5 mm unsewn each edge. Strength is fine (2504 N against 323 N), but it breaks the box rule every other part uses, and SK-1 lists it under 25 mm parts. | State the exception on the piece and in SK-1, or use 34 x 15. |
| m-7 | `G2.md:431, 556` (TL-1 criterion 4) | The ovalisation limit of 0.40 mm is basis A **at the loop centre** (0.39 mm predicted), but the gauge sits on the bare tube 2 mm outboard of the sleeve, where the deflection is smaller. Criterion 4 can hardly fail. | Predict dD at the gauge position (ring + shell decay), or measure at the loop centre through a slot in the sleeve. |
| m-8 | `G2.md:40`; `shopping_list.csv:80, 95`; `G2.md:561` | Bar stock: "buy 1 m" is short. 5 TL-1 + 2 TL-1b + 1 control at 160 mm or more needs 1.28 m. TL-1b steps omit the 288 N step that the results sheet (`TL-1b-03`) asks for, and the prep says 2 TL-1b sleeves where the register says 1-2. | Buy 1.5 m; add 288 N to the step list; align the counts. |
| m-9 | SK-10 (b); `patterns_corrie_f_rev3.py:262-297` | At 19 in, W3 (z 690-715) crosses the IMP-2 hose slot (z 680-720, x 56-68). A cinched W3 closes the hose port. `rt_clearances` does not list W3 against the slot. Pre-existing, now drawn. | Add W3 / slot to the clearance set; move the slot or note that the hose is routed under W3. |
| m-10 | `manufacturing/bom.csv:23` | The camo print line still has `proto_qty` 1.0 yd and the note "costs ON TOP of the unprinted camo fabric line". That contradicts CAMO-FIRST and `costing.md:44` (0 in the prototype buy). | Set proto_qty 0 and change the note to "production only". |
| m-11 | `patterns/print_letter/step2_small_parts.pdf` p. 2 | n-6 is only partly fixed: on paper the B-18 label block overprints the HE 34 x 10 box and its drill marks, and the B-22 label runs past its outline. | Move labels clear of internal lines (label anchor outside the box footprint). |
| m-12 | `step2_small_parts.pdf` pp. 9-10 | The 1:1 webbing pages list labels in a legend but do not label the lines: a beginner cannot tell the HE "neck line" from the "floor seam line". B-25 (new, 6 folds + 2 boxes), RT, TG and B-24 are not on them. | Put leader labels on each line; add B-25 and RT. |
| m-13 | SK-8 (c) | The panel calls the stay at z 60 "carbon" (it is the printed PAHT-CF body) and omits the fairlead root / throat floor under the pin: the geometry Z-1 turns on. | Redraw from `fairlead_local`. |
| m-14 | `mfg --check` `hardware_rows_by_keyword`; `bom.csv:43` | The POM toggles (guy x 2) are still sourced to the ledger row "BL-004 REC: guy bar loops x2 ... + POM toggle", the part BL-041 deleted. The webbing row is gone; the toggle row label is stale. | Re-label the ledger row (guy toggles in B-25). |

---

## Status of every review-2 finding (checked against the files)

| ID | Status | Evidence / what remains |
|---|---|---|
| X-1 | **fixed** | Op 4.05 order NECK, B-18 ROWS (B-18 + B-01 only), PLACE HE, BOX, BASTE (`op_sequence.md:137`). The rows at +41 / +47 and the sides 17 mm outside the HE never cross the eye (+14..+31) anyway. The test checks the stitch lines against the eye footprint. PT-3 text matches. |
| X-2 | **replaced by Z-1 / Z-2** | Box +4..+14 below the cheeks (+16..+34) and eye UP; on paper the pin is at 24.6 mm. But the section model leaves out the throat floor and the folded-neck thickness (Z-1), and the H1 fairlead it is to be fitted on is clipped (Z-2). HE-FIT is now a BAG-CUT gate (good). |
| Y-1 | **fixed** (see M-3) | The PT-3 rig (B-05 alone in the clamp, B-01 top free, pin in an 18 mm slot) and the specimen order are correct. The pull is in line, not at the frame's leg angles (M-3). |
| Y-2 | **fixed at 19 in only** | Clip path at x 91, buckle 10.0 mm over the B-26 cord, muzzle tabs at 111 / 171, minimum gap 10.0 over the buckle envelope + corridor (`rs.geo['rt_clear']` reproduced). W3G added. It holds at the 19 in torso only (M-1), and the strap origin moved off the roll end unmodelled (M-2). FIT-R3 rows are added. |
| Y-3 | **fixed** | `BUILD_PLAN.md:37` and `PROTO_MACHINE_MIN` require a 304 zigzag up to 5 mm or the BT-301 fallback. Needles 90/14 R and SUK, 110/18, 140/22; threads tex 70 / 90 / 135 (`:38-39`). The op table uses only these. The per-op header ambiguity is in m-2. |
| Y-4 | **fixed on paper** (see M-4, m-7, m-8) | B-25 is 38 mm, sleeve x 26.5-64.5 (11.5 mm to the assumed clamp, 4.5 mm to the scarf), cut 386.5 mm, 10.82 g. The load row is 323 N, capacity 439 N, SF 1.36. TL-1 is 494 N on real bar stock with both toggles; TL-1b is a data test; GBL is deleted. All match `crown_tube_guy_loop.md`. Remaining: the topology (M-4) and the TL-1 criteria and quantities (m-7, m-8). |
| Y-5 | **fixed** (m-10) | CAMO-FIRST is stated in the README; the costing prototype buy has no print. The BOM `proto_qty` residue is m-10. |
| n-1 | fixed | "R about 0.02", 24 -> 1178 N. |
| n-2 | fixed | CA-1 retitled "0.40 (fallback >= 0.313)"; the table stops at 115 % with "STOP". |
| n-3 | fixed | COLD is its own sentence; FREEZER -18 C accepted. |
| n-4 | fixed | No "op 7.end" remains. |
| n-5 | fixed | SK-10 relabelled "sigma (mm along the gusset)"; SK-1 is no longer clipped. |
| n-6 | **partly** (m-11) | Notes are on the NOTES page (p. 8, readable). Tile labels still overprint B-18's box marks. |
| n-7 | **partly** (m-12) | 1:1 webbing pages exist and are 1:1 (HE, RTM, W3G, LLT, US, T3, IMC). Lines are unlabeled; B-25 and RT are missing. |
| n-8 | fixed | Row 2 hardware is the POM toggle; the GBL row is gone; the README labels B-17 "PENDING PT-2". |
| n-9 | fixed | BUILD_PLAN lists tex 70 / 90 / 135; box-X 140/22 throughout. |
| n-10 | fixed | $501.49 one-bag buy, thread by cone, sealer / tape by pack. |
| n-11 | fixed (fragile) | `bag_attachment.md:115` carries a SUPERSEDED note, but `attach_system` regeneration removes it (the note says so). |
| n-12 | fixed | Tautology removed; a missing piece is an error; box centres checked (`box_positions`, self-referential only). |
| n-13 | fixed | SEW-F 44 -> 442 N (1.15 x 384). It does not cover the HE box (M-3). |
| n-14 | fixed | Op 4.15 uses the zipper / edge foot on the hinge spans; PT-3 is the same. |
| n-15 | fixed | DECISION IM-CAM-TAB, SK-11, IMC rows. Residue in m-4 and m-5. |

## Answers to BL-041's own checklist

- **HE-PIN model against the fairlead geometry (frame_h1, frame.yaml).** Fails: Z-1 (throat floor, folded-neck
  wrap) and Z-2 (the H1 STL fairleads are clipped; the hinge throat is solid at the pin line). The `attachment.yaml`
  stations (hinge 60, throat 18, cheek 8, pin 5, hole 7.2) match `bag_attach`.
- **34 x 10 box-X at 1019 N.** On the thread-path model it is fine (about 3.2 kN, 48 stitches, SK-1). It is not
  in line (legs 30-44 deg on the outer leg), has no fatigue coverage, and PT-3 pulls it in line (M-3). The floor seam
  (2355 N, SF 2.31) still governs statically.
- **Forward roll-clip location against the cloth-pass roll model.** Not checked by BL-041 (M-2). The clearances
  reproduce at 19 in only (M-1).
- **IMC dog-bone.** The topology closes: two 18 mm loops, both plies in both boxes, 4 mm between the boxes. Raw-end
  margin 2 mm (m-4); hardware-before-sewing not stated (m-5).
- **NOTES and 1:1 webbing pages.** Rasterised and measured: 1:1 is correct, the NOTES page is readable, but there is
  overprint on the B-18 tile (m-11) and the lines are unlabeled (m-12).
- **38 mm B-25 against the spine clamp and `crown_tube_guy_loop.md`.** The numbers match the analysis (band,
  clearances, cut, mass, 323 N, 439 N, SF 1.36). The clamp half-width is an undrawn ASSUMPTION, and the 38 mm turn /
  spine wrap is undrawn (M-4).
- **TL-1 at 494 N and TL-1b.** Load, rig and specimen match §6. The ovalisation gauge position does not match the
  prediction (m-7); the stock quantity and step list are wrong (m-8).
- **BUILD_PLAN machine spec.** Covers every op's machine / needle / thread / stitch (zigzag or BT-301; 90/14 R and
  SUK, 110/18, 140/22; tex 70 / 90 / 135). Only the per-op header ambiguity (m-2) remains.
