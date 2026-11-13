# FIFTH review: CORRIE F rev 3 bag release + H1 frame print files (independent, adversarial)

design-reviewer, 2026-11-13. Scope: the bag release (`outputs/release/pack5200_corrie_f_rev3/`, `outputs/release/test_kit/`)
and the H1 frame print package (`designs/pack_5200/print/frame_h1/`) together, after BL-047 to BL-052. I took no README
or record status as evidence. I checked against the regenerated release, the STLs (sliced and ray-mapped myself with
trimesh / shapely, scripts in the session scratchpad), and the source code.

**Counts: 1 blocker, 7 majors, 10 minors.** Suite: **1239 passed, 4 skipped, 0 failed, exit 0 (23 min 42 s)**; no test covers B-1, M-1, M-2 or M-6.

**Verdicts (each assumes its own physical gates pass):**

- **Frame, print P1: NO.** The print files are watertight single shells that match the FEA body, but the README
  tells a beginner to print them with no supports, while ~70 % of each half's footprint floats 10-50 mm above the
  plate (B-1). The R1 gates on the new lanes also have no numeric pass line and load in a direction the FEA did not
  analyse (M-1, M-4), and the build path is not complete (M-5, M-7).
- **Bag, cut: NOT YET, but close.** No pattern or op blocker is left: N-1, M-A, M-B and M-C are closed on the real
  geometry, and the release regenerates byte for byte. But the BAG-CUT gate (HE-FIT step 0, PT-3) prints test pieces
  from the same "H1 settings, no supports" text, and they touch the plate over 10-30 mm² (B-1). Once B-1's print text
  is fixed and G2/G3 pass, the bag can be cut. M-3 and M-6 are bag-adjacent, but they change frame and user-card
  items, not the cut pieces.

## What I ran

- **Full suite.** `HUNTKIT_BPY=.../bpyenv/bin/python python -m pytest -q`: **1239 passed, 4 skipped, 0 failed, exit 0 (1421.65 s)**, 134 warnings (numpy / skimage deprecation, one trimesh divide). The suite is green, but the slice checks it runs test fairlead geometry, not printability or the clevis nut fit.
- **Manufacturing.**
  - `python designs/pack_5200/mfg_corrie_f_rev3.py --check`:
    - 89 ops, 32 load points, min SF 1.36 (B-25 toggle tab);
    - holds, unsequenced, unmapped hardware and box mismatches all empty;
    - thread 18.89 g against 18.88 g on the ledger;
    - recon 116 rows, 0 unmatched.
  - Regenerated into the scratchpad (`--out --no-screens`). `op_sequence.md/.csv`, `load_points.csv`,
    `cutting_plan.csv`, `bom.csv`, `costing.md`, `qc_sheet.md`, `release_tests.csv` and `README.md` are **identical**
    to the release (fourth-review m-7 closed).
- **Print files.** For every STL in `print/frame_h1/` and `test_pieces/` I checked watertight, winding, shell count,
  volume and mass at 1.06 g/cm³:
  - all are watertight single shells;
  - lower 401.56 + upper 512.71 + 2 × clevis 12.98 cm³ = 940.23 cm³, against `h1_assembled.stl` at 940.22 cm³. The
    halves and clevises are exactly the assembled frame.
- **Test pieces against the print.** Symmetric difference of z-slices against `h1_assembled.stl`, 9 levels each:
  - HE-FIT ≤ 0.9 mm²;
  - IM3-EC ≤ 1.4 mm²;
  - US route ≤ 2.8 mm² (one tangent-slice artefact at z 55.6 that disappears at ±0.4 mm).
- **Geometry slices** (independent of `h1_lanes.slice_checks`):
  - hinge z 60: cheeks x 95-105 / 125-135 (10 mm), throat 20, pin hole 7.0 at y 18.5, floor y 9.5, cheek z 50-87
    (36 mm, 27 up);
  - stay crown at x 112 / 115 / 118 / -115 over z 92-152: y 9.6-10.4, continuous (BL-051 fix holds);
  - pawl bore 7.6 mm at (y -29.6, z 500), present through both cheeks;
  - US2 joint sections at |x| 146-181 (counterbores 9 mm, traps; see M-2);
  - strap traces from `us_route.json` against the whole print (M-6);
  - underside height and overhang maps of every flat file (B-1).
- **Read:**
  - the frame records `h1_lanes.md`, `h1_bedfit.md`, `h1_crown.md` and `crown_gnl.md` (summary), plus
    `h1_spine_channel.md` (summary);
  - `corrie_f_body.md` §24-26, `us_route.json`, `print/frame_h1/README.md`, and G1, G2 (HE-FIT, PT-3, TL-1), G4
    (CLEVIS-SHARE) and G6 (MT-1cr, FIT-US);
  - ops 4.05-4.15 and 7.15-7.26, the BOM frame lines, and SK-1;
  - webbing PDF pages 9-15 of `step2_small_parts.pdf`, rasterised.
- **Code paths read:**
  - `h1_bedfit.ClevisJoint` / `cuts`;
  - `frame_h1` joint traps and `lay_flat`;
  - `h1_lanes.lug_loads`;
  - `us_route` (`occupancy`, `stays`, `strap_path`, `clearances`);
  - `meat_haul` belly text;
  - `bag_attach.pin_check`;
  - `h1_pawl` constants;
  - `physical_test_kit` step splitter.

---

## BLOCKER

### B-1 The H1 halves and every test piece float above the plate, but the print instructions say "no supports" (frame and bag gate)

- `designs/pack_5200/print/frame_h1/README.md:144-151` (step 6: "Supports: none, except tree supports under the four
  US lug arms"; "the rest of the body prints as before")
- `designs/pack_5200/analysis/h1_lanes.md:155` (ASSUMPTION SUPPORTS)
- `huntkit/gendesign/frame_h1.py:845-854` (`FLAT_R` / `lay_flat`: "wearer face, min y, on the plate")
- `outputs/release/test_kit/guides/G2.md:118` (HE-FIT step 0: "print both as the H1 frame ... H1 settings")
- `outputs/release/test_kit/guides/G2.md:317` (PT-3: "the H1 slicer settings")
- `outputs/release/test_kit/guides/G4.md:159` (CLEVIS-SHARE)

`lay_flat` puts the frame's minimum y on the plate. The minimum y is not the wearer face of the stays: it is a single
protruding feature on each half.

**Lower half.** The lumbar hub at x ≈ 0, z ≈ 114 in frame coordinates, y -48.5.
- The section area at print z 0.1 / 1 / 5 / 15 mm is 571 / 812 / 1161 / 2953 mm². It is one island, x 140-168 and
  y 137-163 on the plate.
- The stays' wearer face is at frame y -18.5 (z 200) and -20.5 (z 300), so the stays start **27-30 mm above the
  plate**. Their undersides are round (min y at the stay centreline, rising to -7 at the edges), not flat.

**Upper half.** It rests only on the pawl housing (frame y -39.1 at z 535). The stays' wearer face is at y -22.6
(z 444), so they start **16-30 mm above the plate**.

**Overhang maps.** These show the first surface from below, 1 mm cells.
- **Lower:** 762 of 24 537 footprint cells on the plate; 18 050 cells (74 %) are a > 45° overhang off the plate.
- **Upper:** 943 of 33 210 on the plate; 22 850 (69 %) overhang.
- **Test pieces:**

| piece | plate contact | > 45° overhang |
|---|---|---:|
| `us_route_stay_R` | about 10 mm² (38 half-mm cells) | 79 % |
| `hefit_hinge_fairlead_R` | about 29 mm² | 77 % |
| `im3ec_cheek_R` | 23 % on the plate | |

- Only the US2 clevis prints flat (94 % on the plate).

A beginner who follows step 6 gets a hub printed into thin air and then spaghetti. A slicer that auto-supports will
put tree supports under the full length of both stays. That support is not described anywhere:
- not the print time (volume / 8 mm³/s);
- not the filament (1.08 kg);
- not the support/interface settings for PAHT-CF on a single-nozzle H2S;
- not the finish of the support-scarred wearer face.

The FEA's layer orientation (layer normal = frame y) is right and must be kept, so re-orienting is not the fix.

**Fix (structural-fea-engineer + whoever owns the print README; frame and kit text):**
1. Rewrite README §1 step 6:
   - tree supports from the build plate under the whole body;
   - support material PAHT-CF itself, top Z distance 0.2-0.25 mm, interface 2-3 layers, 45° threshold;
   - "do not support inside the bores, pin holes or nut traps" (set blockers).
2. Re-state the plate preview, print time and filament with supports (add about 15-25 % on the filament line), and
   add a removal and clean-up step to §3.
3. Optional but better:
   - flatten the stays' wearer face to a 6-8 mm land, or add printed sacrificial pads/feet down to the plate under
     each stay;
   - or put the hub on its own split.

   Either change needs the FEA body re-run.
4. Check whether support scars on the stays' wearer (tension/compression) face change fatigue. CA-1 bars print flat on
   the plate, so they carry no scar. Add 2 XY bars printed over tree supports to CA-1, or state why the face is not
   fatigue-critical.
5. G2 HE-FIT step 0, PT-3 and SEW-F, and G4 CLEVIS-SHARE / IM3-EC: say "supports as README §1 step 6" for the test
   pieces.

---

## MAJORS

### M-1 The bag-off cradle leg angle is computed in the x-z plane but applied to the lugs in the y-z plane; MT-1cr pulls the third way

- `huntkit/gendesign/h1_lanes.py:614` and `:630-640` (`lug_loads`: `a = atan2(belly, half)`, with `half` = lane x
  half span 70 / 165, applied as `[0, cos a, -sin a]`, i.e. aft and down)
- `designs/pack_5200/us_route.py:570-616` (`cradle_span`: `T = V / (2 sin theta)`, theta from the x half span)
- `huntkit/gendesign/meat_haul.py:38-39` ("below the straight line between the stays")
- `outputs/release/test_kit/guides/G6.md:130` (MT-1cr B: "the strap led along its lane leg, 45 deg below the pin
  line for US1, 23 deg for US2")

**What the tension model assumes.** The belly is a sag below the line joining the two pins, which runs along frame x.
So each leg leaves its pin inboard (toward x = 0) and down. For US2 at the 60 mm minimum belly (20°), 0.94 of the
tension, about 690 N factored, acts **along the pin axis**, pressing the eye's edge on the INNER cheek face. At 50 mm
it is about 823 N.

**What the lug, clevis and body checks apply.** The same magnitude acting aft and down with zero x. Only the ±10° fleet
adds about 0.17 T in x. The inboard component on the cheek face is exactly the mechanism that failed the hinge (0.62)
until BL-049 grew it to 10 x 36 mm cheeks. The US cheeks are 8 x 18 mm and were never run that way.

**The test disagrees with the analysis.** MT-1cr (B) pulls along the x-z leg, and its pass line is "≤ the lug model's
root stress", which was computed for a different direction. CLEVIS-SHARE then puts the eye on the OUTER cheek with a
PTFE shim. Yet an inboard leg loads the INNER (body) cheek and unloads the clevis.

**The likely real geometry is 3D.** The leg leaves aft (round the quarter), inboard or outboard (quarter width against
the 140 / 330 mm pin span) and down.

**Fix (structural-fea-engineer, with pack-designer for the cradle geometry):**
1. Build the cradle as a 3D string from the R-08 quarter envelope (width, depth) and the two lane pins. Take the leg
   unit vectors and the tension from it at 50 / 60 / 70 mm belly.
2. Run `lug_fea` and `h1_bedfit.joint_check` on those vectors. Include the eye-edge bearing on the cheek face, as for
   the hinge (`fairlead_fea` rule).
3. Put MT-1cr (B) and CLEVIS-SHARE on the same vectors, with the shim on whichever cheek the real leg loads.

### M-2 US2 clevis nut traps do not hold the nut, and their outer walls are 1.1-1.3 mm

- `huntkit/gendesign/h1_bedfit.py:166-177` (`cuts`: one box `slot_w` = 10.4 mm square about the bolt axis over
  |x| 145.8-151 for washer + nut)
- compare `huntkit/gendesign/frame_h1.py:792-799` (the z 234 trap: 12.4 washer slot, then a hex pocket and an
  AF + 0.2 slot for the nut)
- `designs/pack_5200/print/frame_h1/README.md:201` ("the nut is held by its flats")

**The trap is too wide.** On the STL at |x| 146-150 each trap is 10.4 mm wide (z 128.8-139.2 and 144.8-155.2), open to
the wearer face. An ISO 4032 M5 nut is 8 AF and 9.24 across corners, so it **spins freely**. With the screw head down
a 9 mm counterbore on the other side and blue threadlocker on the thread, a beginner cannot snug the joint. No slot
remains for a spanner: the trap is 5.2 mm long for a 4 mm nut plus a 1 mm washer.

**The outer walls are thin.** The traps' outer z walls are 127.5-128.8 and 155.2-156.5, about 1.1-1.3 mm after the
r 1.5 edge round. That is two perimeters at a 0.6 mm nozzle, beside the nut.

**Fix (structural-fea-engineer):**
1. Cut the trap in two steps, as at z 234:
   - a washer slot 10.4 wide, 1.2 mm long at the nut face;
   - an AF + 0.2 = 8.2 mm hex slot for the nut.
2. Re-check `net_section` and the wall (≥ 2 mm, or move the bolt axes to dz ±7).
3. Re-export, re-slice (`joint_slices`), and fix the README text.

### M-3 The 60 mm minimum belly is a user rule standing in for a fatigue margin, and it is not holdable as specified

- `designs/pack_5200/analysis/h1_crown.md:84-91` and `:157` (BELLY-MIN)
- `designs/pack_5200/analysis/corrie_f_body.md:2119-2133` (BELLY-GAUGE)
- `outputs/release/pack5200_corrie_f_rev3/manufacturing/README.md:222` (card)
- `outputs/release/test_kit/guides/G6.md:126-129` (MT-1cr A)
- `huntkit/gendesign/meat_haul.py:620` (instruction still "about 70 mm", no minimum)

**Margins at the 60 mm minimum.**
- US1 root fatigue 1.03, against the 1.15 scatter goal the hinge was designed to.
- US2 clevis joint at share 1.0, scaled from 0.84 at 860 N to 730 N: about 0.99.
- 50 mm is still called "the governing check case", and US1 fails it (0.95).

**The belly is hypersensitive to the cam.** On the record's own straight-leg model, going from 60 to 50 mm belly takes
only **6.3 mm of strap at US2** (2·√(165² + b²)) and 12.4 mm at US1. That is one tug on a cam, so the user cannot
"hold" 60 mm by feel.

**The gauge cannot be used where it is needed.**
- The ruler is two tacks on the strap TAIL at the cam. The belly is at mid-span, under the quarter, below a "pole
  across the pins" that would pass through the meat.
- The straight-leg model also ignores the quarter's round bottom: at the same mid-span belly the legs leave the pins
  flatter, so tension is higher.

**The gate does not settle it.** MT-1cr (A) uses a 20 kg sand bag, not the 53 kg float-limit quarter, so passing (A)
does not show 60 mm is held under the design load.

**Fix (orchestrator call, structural):**
- Take the frame-side fix now: BL-049 proposal 2, the US1 arm onto the lower branch, plus whatever M-1's US2 cheek and
  clevis check needs. Make **50 mm (or 40 mm) the design case**, with US1, US2 and the clevis at share 1.0 all ≥ 1.0
  in fatigue.
- Keep the card as advice, not as the structural control.
- If the rule stays:
  - run MT-1cr (A) with a ≥ 50 kg quarter-shaped load;
  - define how the gauge is read (a cord jig hung from both pins);
  - update `meat_haul.py:620`.

### M-4 The R1 frame gates on the lanes cannot be judged (no numbers) and CLEVIS-SHARE loads below the governing row

- `outputs/release/test_kit/guides/G6.md:137` (MT-1cr pass: "≤ the h1_crown lug model's root stress ... the
  structural-fea-engineer reads it off")
- `outputs/release/test_kit/guides/G4.md:176` (same)
- T1 gauge text (`corrie_f_body.md:2105-2107`)
- `designs/pack_5200/analysis/h1_crown.json` (no root stress or strain at the gauge site anywhere; only
  `capacities_n.contact_mpa`)
- `outputs/release/test_kit/guides/G4.md:156-176` (CLEVIS-SHARE 720 N static, 48 → 480 N × 1e5 at 31°)

**No numbers for the gauges.** Three R1 gates rest on a strain gauge compared with a model value that is not
published. On top of that, a 1 mm foil gauge "3 mm off the stay surface" needs the model stress *at that spot, in
that direction*, not a FI99 region value. BL-052 lists this as open; it is a gate without a pass line, so the owner
cannot run R1.

**CLEVIS-SHARE is under-loaded.** It proofs and cycles at the legacy 720 N / 480 N envelope at meat_haul's 31.3°. The
governing rows are:

| belly | factored | cycle |
|---|---:|---:|
| 50 mm | 860 N | 573 N |
| 60 mm minimum | 730 N | 487 N |

The share-1.0 fatigue at 50 mm is 0.84 (`h1_crown.json joint_share_1`), so the test that "settles CLEVIS-SHARE" runs
below the case that governs it, and at the wrong angle (M-1).

**Fix:**
- Publish, per gauge site and per load step (240 / 480 / 720 N and the T1 steps), the model's strain in µε along the
  gauge axis, with a ± band.
- Write it into the results rows as `pass if at most X`.
- Raise CLEVIS-SHARE to the governing row on M-1's vector: static 860 N (or the 60 mm row, if M-3 keeps the rule),
  cycles to 573 N / 487 N.

### M-5 Under-strap and fairlead pin retention is not designed

- `outputs/release/pack5200_corrie_f_rev3/manufacturing/bom.csv:47` (Ti hinge pins "clip groove"; 7075 pins "36 mm
  shank")
- `designs/pack_5200/print/frame_h1/README.md:115` ("with a clip groove (or a 5 x 44 Ti clevis pin)")
- `huntkit/gendesign/bag_attach.py:593-595` (7075 pin = 36 mm shank + an 8 mm head)
- `designs/pack_5200/analysis/bag_attachment.md:183, 196` ("Push the pull-pin ... Seat the silicone washer"; "Pull
  the two hinge pins. They stay tethered")
- `huntkit/gendesign/h1_lanes.py:577` (PIN-L: + 4 mm "head / clip groove")

**Three incompatible retention schemes.** The release has a ground pin with a clip groove (tool-held clip, not
tool-free), a headed pin, and a tethered pull-pin with a silicone washer (friction only). Twelve pins carry the bag's
governing rows: hinge 1019 N inboard-up, US cradle up to 860 N.

**Nothing is specified or bought:**
- no clip type or size, no detent;
- no tether;
- no head geometry on the Ti pin;
- no check that a 2 mm stub each side (44 - 40) takes a head plus a groove.

The bag-off procedure needs the hinge pins out by hand in 8 s. The hinge eye's load is mostly along the pin axis (the
sims pull 0.47-0.92 inboard), so a friction-held pin is the one that walks.

**Fix (pack-designer + structural):**
1. Choose one scheme: for example a 5 mm ball-lock or detent pin (bought, rated), or a headed pin with a
   tethered R-clip / lynch pin on the inboard side.
2. Draw it with its stack length per station (hinge 40 + head + retainer; US / IM 36 + head + retainer; US2 across
   the clevis).
3. Put it on the BOM and shopping lists with a source.
4. Add a retention check to FIT-US / T9 (pins still home after the crank cycles).

### M-6 The strap route model passes the strap through its own lug, fairlead and clevis block

- `designs/pack_5200/us_route.py:251-258` (`stays`: the only taut-path obstacle is the stay tube at x ±115)
- `designs/pack_5200/us_route.py:261-272` (`strap_path`)
- `designs/pack_5200/us_route.py:286-299` (`clearances`: `own` skipped)
- `designs/pack_5200/analysis/us_route.json` `layouts.now.rows[*].trace`

**Where the traces go.** I sectioned `h1_assembled.stl` at each traced z and tested the 25 mm ribbon. On all 12 rows
the trace runs from the pin through solid print:
- **US1:** at z 90 and 86, y 0.2-1.0, it overlaps **22-25 mm** of 25 mm with the US1 fairlead / arm (solid y -21 to
  +25 there);
- **US2:** at z 135 and 130, y -3 to -5, it overlaps **20-24 mm** with the clevis joint block (solid y -12.5 to
  +8.4).

**What the real strap does.** It must leave the throat over the fairlead floor's lower end (US1, z 86) or over the
clevis block's lower aft edge (US2, z 127.5, r 1.5 edge round) before it can follow the bag down to y ≈ 0. That makes a
wrap of about 40-60° on a printed edge at up to 444 N (bag-on) every time the cam is worked.

**What is missing:**
- an abrasion point on the strap;
- a strap bearing load into the clevis block that `joint_check` does not carry;
- a lip edge that no gate looks at.

The ≥ 10 mm lateral clearances to the hinge / HE are probably unaffected (they are mostly in x).

**Fix (pack-designer):**
1. Add every station's own fairlead, arm and joint block to the taut-path obstacles (keep the throat as the exit).
2. Report the wrap angle and the bearing at the lip.
3. Give the US1 floor's lower end and the US2 block's lower aft edge a ≥ 3 mm radius (frame).
4. Add the lip to FIT-US: strap and lip inspected for fuzz or whitening after the crank cycles.
5. Hand the bearing vector to `h1_bedfit.joint_check`.

### M-7 Frame build path is not complete or current for a beginner

- `designs/pack_5200/print/frame_h1/README.md:101-105`
  - "IM3 cheeks 28 mm tall, the others 18 mm; all 8 mm thick": the hinge is 10 mm / 36 mm since BL-049;
  - "Footprints 280 × 235 × 77 mm and 280 × 309 × 64 mm": the lower is 321.1 × 299.6 since BL-050.
- `README.md:218-219` ("Expect about 846 g ... More than 880 g means over-extrusion"). The body is 969.1 g as
  printed (425.6 + 543.5), so the owner's correct print reads as a failure.
- `README.md:209` ("Fit the carbon crown (rev C), the rack, the pawl and the pulley guides, as in
  `../frame/PRODUCTION.md`"). That folder is marked "DO NOT PRINT FROM THIS FOLDER" and predates the BL-045 / BL-046
  spine clamp and the OD 20 spine tube.
- `README.md:110-123` (shopping list) is missing:
  - the 10 × 7075 fairlead pins and the UHMWPE pin sleeves;
  - the 4 mm pawl pin (length about 50 mm across the 13.8 mm cheeks) and two 304 sleeves 8 × 4.2 × 8;
  - the 0.5 mm torsion spring (no drawing);
  - the M5 heat-set inserts (count);
  - the 70 mm UHMWPE crown bushings;
  - the spine tube and the rack (which file: `print/crown_rack_*`?);
  - MMA plus 0.8 mm glass beads;
  - pin retention (M-5).
- **Spine clamp:** `huntkit/gendesign/crown_spine_clamp.py` sizes a machined 7075 T-fitting (14.2 g), but no drawing,
  STEP or DXF exists in the repo (a glob for `*clamp*` returns only the .py). The H1 README never mentions the clamp,
  and its saddle bond peak of 0.81 rests on a T6 coupon.
- **Order with the bag:** op 7.19 (B-25) needs the sleeves slid onto the top bar before the crown corners are bonded.
  The frame README's assembly order does not say so.
- `README.md:192`: "press in the 304 sleeve (OD 8.0)" into a bore reamed to 8.0 has no interference. Give a ream
  size (7.95) or say "bond".
- `README.md:197` against BOM `bom.csv:47` and `bag_attach.py:201`: the UHMWPE sleeves are "pressed into the cheek"
  (2 per station, 24) but booked as 12, and the eye is said to wrap "the pin sleeve" (1 long sleeve per station).
  Choose one and draw it.

**Fix:** regenerate `print/frame_h1/README.md` from the code constants (masses, footprints, cheek sizes) and add:
1. a complete frame hardware BOM with sources;
2. a spine-clamp drawing (or STEP) with its bond procedure and the T6 coupon;
3. one ordered assembly list, including the B-25 sleeve-before-bond step;
4. no references to the superseded folder.

---

## MINORS

| # | File:line | Finding | Fix |
|---|---|---|---|
| m-1 | `designs/pack_5200/physical_test_kit.py:1822` (`split(";")`); G2.md:115-143 (HE-FIT), :460-470 (TL-1), :390-391 (LL-H); G4.md:165-166; G6.md:130-131 | **The step splitter cuts inside parentheses.** HE-FIT's (0)-(8) become 29 numbered fragments ("2. Pass criterion below): print ...", "6. Shopping list), blue threadlocker"). TL-1, LL-H, CLEVIS-SHARE and MT-1cr have the same fault. "the the hardened" appears at G2.md:107 and :310. A beginner follows the numbers. | Split on "; (n)" markers or keep steps as lists in the source; fix the typo. |
| m-2 | `mfg_corrie_f_rev3.py:2173, 2332, 2389-2390, 2747, 3284`; `physical_test_kit.py:486`; release README rows m-4 / m-5 / M-4 / B25-TOPO; SK-1; G2.md:124 | **Op numbers are stale again** (fourth-review m-5 (e) regressed). B-25 is op **7.19** (7.18 is now B-24); USA is **7.17** (G2 says "as op 7.16", now US2); SK-1 says "US neck (op 7.15), USA neck (op 7.16)". | Generate op cross-references from the op list, not literals. |
| m-3 | `physical_test_kit.py:486`; `data/materials/webbing/poly_webbing_38mm.yaml:44`; `shopping_list.csv:104`; G2.md:104 | **Stale hinge numbers in the kit.** "0.3 mm clear on the model, BL-044" (now 1.09 mm); "3 plies of a thicker web leave < 0.7 mm under the pin" and "must pass the 5.5 mm gap" (gap 6.5 since BL-049); title "printed BL-042 ... fairlead"; HE-FIT filament "31.9 g" (piece 41.6 g). | Read them from `he_stl_check.json` and `HINGE_EYE_ENVELOPE`. |
| m-4 | `shopping_list.csv:6`; G2.md:107, :310 | **The fixture dowel is M5 × 40, but the hinge span is 40 mm since BL-049** (cheeks 95-135). It sits flush, with nothing to grip for removal or for the "roll it straight" check. Fine for the 36 mm US / IM spans. | Buy M5 × 50 (DIN 6325) for HE-FIT, PT-3 and SEW-F HE. |
| m-5 | G2.md:126-130 (US-ROUTE PASS); G6.md:208-228 (FIT-US) | **The US-ROUTE bench check is tautological.** The dowel is set "straight under its pin", so the 10 mm feeler measures lane offset minus cheek (12.5 mm by construction). FIT-US on the real bag never re-checks strap-to-hinge / HE clearance. | Add to FIT-US: bag on, 30 kg meat, cams tight, 10 mm feeler between each US strap and the hinge cheeks / HE, at S / M / L. |
| m-6 | op 7.25 (`op_sequence.md:350`, `mfg_corrie_f_rev3.py:1582`); `corrie_f_body.md:2122`; SK-1 | **Belly gauge tack spec.** The op renders BT-S as "16 x 2 mm zigzag" (the BT-M spec); the record and SK-1 say BT-S is 10 × 2; SK-1's BT-S "used on" omits the gauge tacks. | Pass the BT-S spec to `step_spec`; add the users. |
| m-7 | G1.md:22-46 | **G1's print list omits the CLEVIS-SHARE pieces** (`us_route_stay_R` + `us2_clevis_R`, a second print as G4's note requires), although CLEVIS-SHARE sits in G1's test table and needs the 7-day conditioning. | Add the row. |
| m-8 | G4.md:159; G6.md:115 | **Quarter-bridge gauges on PAHT-CF without temperature compensation.** PAHT-CF's CTE gives tens of µε per °C of apparent strain over a 1e5-cycle CLEVIS-SHARE run. | Add a dummy gauge on an unloaded coupon (half bridge) or re-zero at every stop; record the temperature. |
| m-9 | `h1_crown.md:159` (CLEVIS-FACE); FIT-US step 7 | **Clevis face contact accepted.** The bag panel rests 3.3-4.0 mm into the free drape on the flat clevis face (z 127-157). An inspection gate exists. Residual risk: with M-6 the US2 strap also passes that block's lower edge. | Inspect strap and panel together (see M-6). |
| m-10 | `print/frame_h1/README.md:58-59, 143`; `h1_lanes.py:831-832` | **Bed margin.** The 3.0 / 4.4 mm "spare with brim" assumes a brim round the whole footprint, but the first layer is only the hub (B-1). The 340 × 320 figure is retailer-sourced (`docs/research/frame_comp_A.md:15`). With supports, the support base and any skirt / purge exclusion must fit. | Settle it with an H2S plate preview with supports on (ASSUMPTION BED-ROT already asks for it); make that a README step before the 15 h print. |

---

## Status of every fourth-review finding (checked against the files)

| ID | Status | Evidence / what remains |
|---|---|---|
| N-1 | **fixed in design** | Stations on lanes (US1 x ±70 z 95, US2 x ±165 z 142, `h1_bedfit.json published`). Channels B-16 / B-16b end at the lane x (op 4.14 / 4.15). US2 cut 925 mm. Model clearance to hinge / HE / other US ≥ 12.4 / 14.6 mm on all 12 rows. Test piece cut from the print (it matches). Residue: M-6 (own lug transparent), m-5 (bench check tautological), M-1 (cradle direction). |
| M-A | **fixed** | TL-1 rigs A (22° below, 0.5 % outboard, the BL-046 vector) and B (58°, 13.6 %), anchor coordinates given, crown-strap toggle 43 N, proof 497 N (max of 462 / 497) (G2.md:465-472). Text fragmenting: m-1. |
| M-B | **fixed** | Record `thickness_mm` 1.5, `min` 1.2, `max` 1.6; purchase spec on the shopping line; `corrie_f.WEB38_T`, `HE_T` and `crown_spine_clamp.B25_T` all read the record (1.5 checked at runtime). Stale gap text: m-3. |
| M-C | **fixed** | Hardened M5 × 40 DIN 6325 dowel bought (×3), "pin straight" check in PT-3 and SEW-F-13..15; the hinge pin is Ti-6Al-4V 5 × 44 on the single 1019 N row (yield 1.99, fatigue 2.24). Residue m-4 (40 mm span since BL-049) and M-5 (retention). |
| m-1 | **fixed** | BL-049 lowered the whole floor 1 mm (gap 6.5), no groove; HE worst 1.09 mm, 0.99 at 0.15 mm tolerance. My slice: floor y 9.5, hole y 15-22. |
| m-2 | **fixed** | RT 565 mm (op 5.02); RT-TAIL-EXC accepted by the orchestrator. |
| m-3 | **fixed** | Op 4.08 step (0): caliper the mated buckle before chalking, with a stop rule. |
| m-4 | **fixed** | Op 7.19: "CUT LAST" with a scrap-strip dry fit. |
| m-5 | **fixed except (e)** | Wording, BT-M on the neck fold and mitre, laps off the bar on an 18 mm dowel. Op numbers stale again: m-2. |
| m-6 | **fixed** | SEW-F-10..15 rows; print-as-H1 text; filament booked (piece mass stale, m-3). The "H1 settings" it points to are wrong (B-1). |
| m-7 | **fixed** | Release regenerates identically. |
| m-8 | **fixed** | Webbing pages 9-15: the test square sits clear of every strip. |
| m-9 | **fixed except op numbers** | Note re-flowed, users added; op numbers stale (m-2). |

## Answers to the checklist

- **US lanes, lug arms, bolt-on US2 clevis.**
  - **Joint:** strength 3.11 / fatigue 1.40 at share 0.6; 1.87 / 0.84 at share 1.0 (50 mm belly). The direction basis
    is wrong (M-1) and the test is under-loaded (M-4).
  - **Counterbore:** 9 × 4 mm, heads 0.5 mm below the face, M5 × 35 tip at |x| 144 against a hole end of 143.5 (as
    designed). Washer and nut stack checks.
  - **Nut trap:** does not hold the nut (M-2).
  - **Bed fit with brim:** 321.1 × 299.6 mm as written, 3.0 / 4.4 mm spare. Real contact is the hub only (B-1, m-10).
  - **Clevis-to-bag contact:** 3.3-4.0 mm into the free drape on the flat face, accepted with inspection (m-9); the
    strap also wraps the block (M-6).
- **Hinge fairlead regrowth and Ti pin.** On the STL: 10 mm cheeks, 36 mm tall (27 up), 20 mm throat, gap 6.5. Ti pin
  numbers check by hand: M = 1019 × (60 - 20) / 8 = 5095 N·mm, σ = 415 MPa, 827 / 415 = 1.99. Retention: M-5.
- **Restored stay crown.** Continuous within 0.3-0.6 mm over z 92-152 at x 112-118 on both sides (my slices agree
  with `h1_crown.md` §1).
- **Low-profile pawl and its bore.** The bore is 7.6 mm through both cheeks at z 500. The LP pawl is 16 mm wide in an
  18 mm window, pivot hole 4.1. The pin, sleeves and spring are not on any list (M-7).
- **Spine channel.** Not re-sliced over travel by me. The record's 21-setting check passes and the clamp has no
  drawing (M-7).
- **B-16 / B-16b and US2 at 925 mm.** These are consistent:
  - channel ends ±70 / ±165, read from `h1_bedfit.json`;
  - B-16b tails on B-05, 31.8 mm inside the side seam, sealed with urethane;
  - US2 925 mm leaves 54 mm of grip at the worst drape;
  - the op order 4.14 → 4.15 keeps every seam reachable.
- **60 mm belly gauge.** Not holdable as specified (M-3).
- **MT-1cr, CLEVIS-SHARE, FIT-US.** MT-1cr and CLEVIS-SHARE have no numeric gauge pass (M-4) and load other directions
  than the FEA (M-1). FIT-US checks heads and the face, not the strap route or the lip (m-5, M-6).
- **Frame and bag constants.** Stations, channel ends, `HINGE_EYE_ENVELOPE`, webbing thickness and clevis hardware
  agree in code, BOM and kit. They disagree in:
  - the print README (cheek sizes, footprints, mass: M-7);
  - `meat_haul.py:620` (70 mm, no minimum: M-3);
  - the kit's stale hinge numbers (m-3).
- **Watertight, one shell, matches FEA.** Every print file and test piece is a closed single shell; halves +
  clevises = assembled to 0.01 cm³; test pieces match the assembled print. The lug FEA analysed a load direction the
  frame does not see (M-1).
- **Frame build path.** Supports wrong (B-1); hardware, clamp drawing, retention and assembly order missing or stale
  (M-5, M-7).
