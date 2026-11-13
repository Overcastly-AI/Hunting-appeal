# Pre-cut FOURTH review: CORRIE F rev 3 bag release after BL-043 / BL-044 (independent, adversarial)

design-reviewer, 2026-11-13. Scope: the **bag** and its interfaces to the frame (hinge pin / fairlead, IM / US eyes,
crown bar / spine clamp). The H1 frame itself (crown buckling, pawl bore, BL-047) is out of scope. I took no README
status as evidence: I checked the regenerated release (`outputs/release/pack5200_corrie_f_rev3/`,
`outputs/release/test_kit/`), the code, and the print STL / test pieces in `designs/pack_5200/print/frame_h1/`.

**Counts: 1 blocker, 3 majors, 9 minors.**

**Verdict: NOT ready to cut, even once G2/G3 pass.** The under-strap route the release relies on (US-ROUTE) cannot
exist on the bag's own geometry. The real route lays the cam-tight under-strap over the hinge fairlead and the hinge
eye, and no gate has a pass criterion for it. The fix is a decision plus flat work on B-01 or F-02, so it has to be
made before cutting. Every third-review blocker and major is otherwise fixed or carried below.

## What I ran

- **Full suite.** `HUNTKIT_BPY=.../bpyenv/bin/python python -m pytest -q`: **1134 passed, 4 skipped, 0 failed, exit 0 (20 min 51 s)**. During the run a structural agent added untracked frame files (`huntkit/fea/gnl.py`, `huntkit/gendesign/crown_gnl.py`, `tests/test_fea_gnl.py`); `tests/test_fea_gnl.py` appeared at 13:55, after collection, so it was not run. There were no frame-side failures. No test covers N-1, M-A, M-B or M-C.
- **Manufacturing check.** `python designs/pack_5200/mfg_corrie_f_rev3.py --check`:
  - 87 ops, 31 load points, min SF 1.36 (B-25 toggle tab);
  - holds, unsequenced, unmapped hardware and box mismatches all empty;
  - thread 18.79 g against 18.78 g on the ledger;
  - recon 115 rows, 0 unmatched.
- **Regeneration diff.** I regenerated the manufacturing package into the scratchpad (`--out`, `--no-screens`) and
  diffed it against the release:
  - `op_sequence.md`, `load_points.csv`, `cutting_plan.csv`, `bom.csv`, `costing.md` and `qc_sheet.md` are identical;
  - `release_tests.csv` and the tech-pack test table are **stale** (m-7).
- **Test pieces against the print.** I sectioned `hefit_hinge_fairlead_R_frame_coords.stl` and
  `im3ec_cheek_R_frame_coords.stl` against `h1_assembled.stl` at 9 z-levels each:
  - symmetric difference <= 1.6 mm2 per slice (mesh noise);
  - one artefact at z 51 (the cheek's lower edge, a tangent slice);
  - so the HE-FIT and IM3-EC pieces are cut from the current print.
- **B-25.**
  - `corrie_f.b25_topology()`: cut 511.9 mm (tab 60, sleeve 79.1, drop 27.0, run 56.5, half wrap 33.3, per side);
    kit S wrap 23.4 mm above the pawl housing.
  - `python -m huntkit.gendesign.crown_spine_clamp`: clamp half 12.0, collar 6.0, spine 25.02 mm fore, webs 21.2 mm
    tall centred on the bar (s +/-10.6), socket s 0-15.
  - The run top (s 17) clears the socket by 2 mm and the webs by 6.4 mm.
- **RT strap.** `strap_tails.roll_row()`: cut 560; 6-day path 222.4 mm, tail **247.6 mm**, `rule_used: false`, grip at
  the longest path **45.8 mm** (m-2).
- **US route.** Evaluated `imus_stl_check.us_cradle_theta`, `h1_fairleads.placed()` (US1 / US2 / hinge) and
  `corrie_f.make().ring(z)` (B-01 frame face y 18.2-19.3 at x +/-115, z 35-142; bag half-width 196.8) (N-1).
- **Hinge pin.** Hand-checked `h1_fairleads.pin_bending` at the bag's hinge loads (M-C).
- **PDFs.** Rasterised `patterns/print_letter/step2_small_parts.pdf` pp. 2 and 9-13 at 72 dpi:
  - the 100 mm test square measures 283 px, so the pages are 1:1;
  - every line has a leader; B-25 and RT are present;
  - layout defect on p. 13 (m-8).
- **Sketches.** Viewed SK-1, SK-8 and SK-12.
- **Text.** Read ops 2.05, 4.01-4.15, 5.02-5.03 and 7.01-7.24. Read the G2 tests (HE-FIT, PT-3, TL-1, TL-1b), the
  G4 test SEW-F, `results_template.csv`, `order_of_work.csv`, `costing.md` / `costing.json`, and `corrie_f_body.md`
  §22-23. Read `crown_and_fairlead_checks.md`, `h1_spine_channel.md`, `meat_haul_modes.md` and `docs/DECISIONS.md`.
- **One-off buy.** `costing.json` `prototype_buy` rows sum to **$501.49**, matching the README. Shop rounding checks
  (0.743 m -> 1.0 yd, 1.135 -> 1.5, 1.715 -> 2.0, webbing whole yards, 1 cone per thread). Hardware counts match the
  ops: 5 cams (3 IMC + 2 USA), 6 + 3 G-hooks, 4 toggles, 2 SR buckles. **No finding** on the cost.

---

## BLOCKER

### N-1 US-ROUTE is geometrically impossible: in bag-on meat carry the cam-tight under-strap lies over the hinge fairlead and the HE box, and no gate has a pass criterion for it

- `designs/pack_5200/imus_stl_check.py:219-229` (`us_cradle_theta`, ASSUMPTION US-ROUTE)
- `designs/pack_5200/analysis/corrie_f_body.md:1786-1799` (US1 / US2 "cradle line", found not fixed)
- `docs/DECISIONS.md:176` (orchestrator: keep US-ROUTE, "if the first fit shows it drifting there, add a guide")
- `outputs/release/test_kit/guides/G2.md:113-114` (HE-FIT step 0: "record whether the box or strap touches")
- `designs/pack_5200/physical_test_kit.py:328`
- `designs/pack_5200/analysis/meat_haul_modes.md:11-13, 32-41` (bag on: the under-straps "cinch the floor up to the
  frame", 444 N)

**Where US-ROUTE puts the strap.** It takes the strap off its pin on the straight line to its B-16 channel:
- US1: pin (y 17.5, z 95) to the channel (y 66.2, z 35), -50.9 deg;
- US2: pin (y 16.4, z 142) to the channel (y 121.3, z 35), -45.6 deg.

**That line is inside the bag.** The bag's frame face (B-01) is at y 18.2-19.3 at x +/-115 over z 35-142
(`ring()`; the bag is +/-197 wide, so x 115 is mid-panel, not outboard of it). The straight line runs inside the
loaded bag:
- **US1, at z 60:** y 45.9, i.e. **19-27 mm inside B-01**. Here B-01 is held on the hinge pin by the HE and tented by
  the cheek tips to about y 27, so the bag cannot be pushed in.
- **US2:** **44 mm** inside at z 95 and **78 mm** inside at z 60.

A strap at 444 N (bag-on meat carry) therefore takes the other path: down B-01 along the stay, then round the floor
corner.

**What that path crosses.** At x 115 on the same stay:
- the hinge fairlead (cheeks x 97-133, tips y 25.9, z 51-69);
- the HE legs and its 34 x 7 box, which lie **outside** B-01 between it and the frame (op 4.05);
- for US2, the US1 fairlead as well.

`imus_stl_check` already shows the US1 eye box overlapping the fairlead below by 18-37 mm2 at -75 / -90 deg.

**The consequence.** A cam-cinched strap that slides at every cinch would ride over:
- the bag's governing 1019 N joint (HE box-X, rated by PT-3 / SEW-F with nothing pressing on it);
- the printed cheek tips.

**What the gates do with it.**
- HE-FIT step 0 only "records" the contact, so G2 can pass with it present.
- Step 0 also needs P1, the first printed frame, which `DECISIONS.md` holds for BL-047, so the BAG-CUT gate cannot
  be completed as written anyway.

**Fix (pack-designer, before cutting B-01 / F-02).**
1. Model the bag-on under-strap path on the loaded shell (it hugs B-01 to the floor corner). Drop US-ROUTE as the
   design case.
2. Choose and draw one of these:
   - (a) a webbing guide / channel on B-01, outboard of the hinge fairlead (x >= 140), in flat work before op 4.12,
     with the B-16 channel ends moved to match;
   - (b) move US1 / US2 off the hinge stay line (frame change; structural);
   - (c) prove a strap-over-HE stack by test: SEW-F / PT-3 variant with a 444 N x 1.6 g strap cinched over the HE box,
     plus abrasion cycles.
3. Give HE-FIT step 0 a pass criterion: the strap and box never touch the hinge fairlead or the HE at the cinched
   load.
4. Cut a US test piece (stay z 40-160 with the hinge, US1 and US2 fairleads) from `h1_assembled.stl`, as was done
   for HE-FIT, so the bag gate does not wait for P1.

---

## MAJORS

### M-A TL-1 (BAG-CUT gate) still proofs 494 N in an unspecified direction; the record moved it to 497 N with a defined pull, and the crown-tube check was not re-run on BL-046's geometry

- `outputs/release/test_kit/guides/G2.md:424-449` and `results_template.csv:106-121` (494 N; step 5 "pull the guy
  toggle aft and outward as in the field")
- `designs/pack_5200/physical_test_kit.py:268-273` (reads `crown_tube_guy_loop.json` `proof_n`) and `:590-602`
- `designs/pack_5200/analysis/crown_and_fairlead_checks.md:7, 54-60`

**What the record now says.** BL-045 re-checked the bar under the as-built mitre and run:
- the bound case (run tension in line with the guy) is SF **1.22 / 1.14**, not 1.36 / 1.27;
- it set **TL-1 = 497 N with the guy toggle 57 deg below horizontal and 14 % outboard, the run's spine end
  anchored**, so that the drop leg loads the sleeve as on the frame.

**The released gate does neither.**
- It reads the old JSON (494 N).
- It leaves the direction to the owner. A level aft pull does not load the drop or the run, which is the very
  combination the bound case is about.
- The crown-strap toggle's load in the test is not stated.

**BL-046 changed the geometry since.**
- The spine moved 15.85 -> 25.02 mm fore.
- The collar went 12.8 -> 6.0, so the drop is now 8 mm below the bar's underside, not 14.
- The run now pulls the mitre about 38 deg fore in plan, which swings the drop under the bar.

The 1.006 / 1.116 pull ratios and the 497 N proof were computed for BL-045's geometry and have not been re-run.

**Fix.**
- Re-run `crown_tube_guy_loop.b25_topology_recheck` on the BL-046 constants.
- Publish `proof_n` and the pull vector to the JSON that `physical_test_kit.crown_tube()` reads.
- G2 TL-1: give the pull angle (deg below horizontal, % outboard, fore component), the crown-strap toggle's load,
  and the rig sketch.
- Results rows at the new proof.

### M-B The HE caliper gate (ply <= 1.6 mm) rejects the webbing the BOM tells the owner to buy, after it is bought

- `designs/pack_5200/patterns_corrie_f_rev3.py:153-158` (ASSUMPTION HE-T 1.5, HE_T_RANGE gate 1.6)
- `data/materials/webbing/poly_webbing_38mm.yaml` (no thickness; "heavyweight", 20 kN, 28 g/m)
- `outputs/release/pack5200_corrie_f_rev3/manufacturing/bom.csv:27`
- `outputs/release/test_kit/shopping_list.csv:57` (Strapworks, no thickness)
- `designs/pack_5200/concepts/corrie_f.py:1541` (`B25_T = 1.2` for the same roll)

**The spec gap.** The whole hinge eye now rests on the webbing thickness:
- 3 plies must pass the 5.5 mm gap;
- the fillet clearance is 0.19 mm at 1.6 mm (m-1);
- the eye length is solved at 1.5 mm.

Yet neither buy line specifies a thickness. The record calls the roll "heavyweight 4500 lbf". Heavyweight mil-spec
class 38 mm polyester is commonly about 1.8-2.3 mm thick, so the likely first purchase fails HE-FIT step (1) after it
arrives, and the HE, IME, T3, B-24 and B-25 all come off that roll.

**The code disagrees with itself.** The same roll is modelled at 1.5 mm (HE) and at 1.2 mm (B-25 sleeve / wrap
lengths).

**Fix.**
- Name a purchasable 38 mm polyester at <= 1.5 mm nominal (with its rated break; the hinge row is governed by the
  2355 N seam, so a lighter web is fine) on the BOM, the shopping list and the material record (thickness_mm with a
  source).
- Use one thickness constant for every 38 mm part.
- Move the caliper check to the purchase step, not the test bench.

### M-C The PT-3 / SEW-F fixture pin is not specified and a 5 mm 7075 pin may yield at the PT-3 proof; SEW-F HE runs the pin at about its fatigue limit

- `huntkit/gendesign/h1_fairleads.py:483-501` (`pin_bending`, M = F (2L - b)/8, L = 28, b = 20)
- `outputs/release/test_kit/guides/G2.md:280-300` (PT-3 1530 N, "the 5 mm pin")
- `outputs/release/test_kit/guides/G4.md:155-185` (SEW-F HE 62 -> 625 N, 1e5 cycles)
- `outputs/release/test_kit/shopping_list.csv:5` (the only pins bought: hardened M5 x 22 dowels, too short for the
  36 mm cheek-throat-cheek span)

**The numbers.** On the frame's own pin-bending model:

| load | bending stress | allowable | SF |
|---|---:|---:|---:|
| PT-3 proof, 1530 N | **561 MPa** | S-basis yield 462 / typical yield 503 MPa | below 1 |
| SEW-F HE peak, 625 N (R 0.1) | 229 MPa | Goodman (record limit x 0.9) | **about 1.06** |

- At PT-3 the pin is just under the UTS of 572 MPa.
- Even crediting the support at the cheek's inner edge, PT-3 is about 375 MPa.
- SEW-F reuses the fixture for 3 x 1e5 cycles.

**The consequence.** A bent or fatigued fixture pin pinches the neck and moves the load. Either one voids a BAG-CUT
gate, and the beginner is told to use "the 5 mm hinge pin (38 mm shank)".

**Interface note for the structural-fea-engineer (frame scope).** The frame record checks the pin at the rev C
725 N / sim 905 N, while the bag's hinge row is 1019 N factored. At 1019 N:
- yield SF 1.24;
- fatigue at 1.6 g on 1019/3, about 1.15.

The basis should be one number.

**Fix.**
- PT-3 / SEW-F / HE-FIT fixtures: a hardened steel 5 x 40 mm dowel (h6) in the UHMWPE sleeves, bought in the kit
  (shopping list line).
- Add a "pin straight after test" check.
- Align the hinge-pin check load with the bag's 1019 N row.

---

## MINORS

| # | File:line | Finding | Fix |
|---|---|---|---|
| m-1 | `corrie_f_body.md:1652-1663`; `he_stl_check.py:204, 211`; `print/frame_h1/README.md` (0.6 mm nozzle) | **HE fold vs the throat-corner fillet.** It clears 0.61 / 0.29 / 0.19 mm at ply 1.2 / 1.5 / 1.6. The rule was relaxed from >= 0.5 to "> 0" inside a 0.1 mm band. The slice check assumes a 0.05 mm print tolerance; a 0.6 mm-nozzle PAHT-CF slot typically prints 0.1-0.2 mm off. HE-FIT on one test print cannot certify P1 or later prints. Risk is low (the loaded leg is in tension, not pressed on the floor), so this is minor. | The frame is reopened for BL-047 anyway: add the 1 mm-deep relief of the floor within 1.5 mm of each cheek face (`corrie_f_body.md:1662`). Re-run `he_stl_check` with a 0.15 mm tolerance. |
| m-2 | `concepts/strap_tails.py:292`; `cutting_plan.csv` RT | **RT 560 mm.** The tail is **248 mm** at the most-used (6-day) setting, against the DECISION TAIL RULE of <= 100 mm (`rule_used: false`, yet `pass: true`). `_floor5` leaves **45.8 mm** of grip at the full path against TAIL_GRIP 50. The roll-end bend sits at its 75 deg cap in all three states (`corrie_f_body.md:1519-1520`), so the paths are cap-driven. | Round the cut UP (565 mm). Record the TAIL-RULE exception, with the K-RT keeper as the mitigation, or step the strap. T9-R3c measures the free length at the three loads. |
| m-3 | `patterns_corrie_f_rev3.py:347` (ASSUMPTION BUCKLE-ENV 35 x 35 above the bar) | **Buckle envelope.** A mated 25 mm side-release buckle stands about 55-65 mm above the female bar and is about 38-40 mm wide. At kit S 15 in, W3's lowest edge (z 588.5) then lies on the male half: the hard part W3-OVER says W3 never bears on. The hose-slot gap (10.4 mm) also shrinks by about 2 mm. Only kit S is affected (kit M clears by about 50 mm). The caliper is "settled by", not a gate. | Caliper the bought buckle as step 0 of op 4.08, before the RTM placement is chalked. Recompute `rt_layout` from it. |
| m-4 | `concepts/corrie_f.py:1576-1581`; `huntkit/gendesign/crown_spine_clamp.py:452-458` | **B-25 cut 512.** The spine wrap is booked as exactly 2 pi r, but the runs now arrive at about 27-48 deg in plan (spine 25 mm fore). The wrap is 2 pi r +/- 2 alpha r, so the cut is uncertain by **+/-10-18 mm**. BL-047's fallback (b) (top bar into the legs' plane) would remove the +22.25 mm a side. | Cut B-25 last. Dry-fit a paper or scrap strip at B25-FIT before cutting the webbing. Re-derive the wrap arc for the diagonal entry. |
| m-5 | `op_sequence.md:322` (op 7.18; generator `mfg_corrie_f_rev3.py:1445, 1450`); `physical_test_kit.py:356` | **Op 7.18 text.** (a) "Nothing on the wearer side of the bar" contradicts "the run reaches the spine 25.02 mm FORE": the wrap is on the wearer side. (b) "design 23 mm on the BL-045 clamp" and TL-1's "25.0 mm ... (the printed spine channel, BL-045)" are BL-046 values. (c) Nothing secures the 13 mm NECK fold or the mitre. (d) How to sew the sleeve-lap bartacks "at frame assembly" round a bar on the machine is not stated. (e) SK-12 (c) and the README (rows M-4 and B25-TOPO) send the owner to "op 7.17" for B25-FIT, but op 7.17 is now B-24 and B-25 is op 7.18. | Correct the labels and the op number. Add one BT-M on the neck fold (or delete the neck: at collar 6.0 the 38 mm wrap clears the housing by 10.4 mm). Say: sew each lap off the bar round an 18 mm dowel, then slide the sleeve on from the bar end before the corners are bonded. |
| m-6 | `results_template.csv:192-200`; `G4.md:155-185`; `G2.md:280-300`; `shopping_list.csv:94` | **SEW-F HE and fixture prints.** (a) SEW-F HE's pass criterion includes "then hold 1530 N 60 s" and "no broken stitch in the box top row", but the results sheet has no row for either; SEW-F-07..09 cover the loops only. (b) The HE fixture's mounting on the lever rig (coupon station, which grip holds the fairlead) is not described. (c) The HE-FIT / PT-3 / SEW-F prints do not state material or settings (PAHT-CF, dried, H1 settings, annealed). (d) Filament is booked for one 32 g print, but three are needed. | Add SEW-F-10..15 rows (HE proof, box-top row). Add a rig sketch for the HE station. State "print as H1, PAHT-CF" on each fixture. Book about 100 g of filament. |
| m-7 | `manufacturing/release_tests.csv:8`; `techpack_corrie_f_rev3.pdf` (release-test table) | **Stale release files.** Regenerating gives a different HE-FIT step 0 from the released one. The release still says "one necked US eye on the first printed frame (P1, US1 R)", but US1 R is the USA station, and it omits the USA loop and the route pull. `G2.md` has the new text. | Re-run `mfg_corrie_f_rev3.py` and commit. |
| m-8 | `patterns/print_letter/step2_small_parts.pdf` p. 13 (webbing page 5 of 5) | **Webbing page layout.** The USA strip (25 x 202) is drawn across the 100 mm test square: its lower 65 mm (the RIGHT-PIN fold, the neck lines and a neck tack) lies inside the square. The owner measures the square and chalks the strip from the same paper. | Lay the USA strip out clear of the test square, or move the square. |
| m-9 | `sketches/SK-1_load_point_patterns.png` | **SK-1.** The B25-BOX exception note overprints the "box-X 34 x 20" title. BT-M "used on" omits the IME, US and USA neck tacks added in BL-044 / BL-045 (ops 2.05, 7.15, 7.16). | Re-flow the note and add the users. |

---

## Status of every third-review finding (checked against the files)

| ID | Status | Evidence / what remains |
|---|---|---|
| Z-1 | **fixed** (m-1 residue) | Solved on `HINGE_EYE_ENVELOPE` (pin 10.1 mm above the stay, 5.5 mm gap, 20 mm throat), folded-neck wrap (r_c 6.25), box 34 x 7 at +4..+11, eye 25, HE 96. `he_stl_check` slices the HE-FIT piece, which matches the current print. The neck clearance test replaced the `neck_w == throat` assertion (`tests/test_bl041_recheck_fixes.py:57-60`). Webbing gate: M-B. |
| Z-2 (bag side) | **fixed** | The HE-FIT and IM3-EC pieces match `h1_assembled.stl`. Pin holes, throats and floors are present (BL-042 / BL-045 slices, `imus_stl_check.json` `eye_pass_all: true`). |
| M-1 | **fixed** by DECISION W3-OVER (orchestrator call, `DECISIONS.md:172`) | W3G deleted. RTM buckle at z 543.5, 10 mm under W3 at kit S 15 in on the assumed envelope (m-3). KW-W3-OFF removes the kinked W3 loops (op 2.04 K-W x4, op 4.13 W1 / W2 only). Usability: unhooking W3 for every top opening is a common roll-top pattern; it is covered by WP-3 only for the ladder lock, not the G-hook. Acceptable. |
| M-2 | **fixed** | RT-ORIGIN at the roll end (hem strip-gap argument holds), roll model re-run, RT 560. Residue m-2. |
| M-3 | **fixed by rating** | "No peel" dropped. PT-3 on the printed fairlead with B-01 held at the tip plane (50 deg peel). SEW-F adds 3 HE at 625 N (1.15 x 1.6 x 1019 / 3, checked). Residue M-C, m-6. SEW-F is BAG-BATCH, so the first bag is cut without HE fatigue data (accepted). |
| M-4 | **fixed** | SK-12 drawn. B25-FIT gate in op 7.18 at kit S 15 in. TL-1 specimen is the as-built half bridle on a stub 25 mm fore under a 6.0 mm collar. Clamp constants are imported live: 511.9 mm reproduced; band to clamp 14.5; wrap 23.4 above the housing. Residue M-A, m-4, m-5. |
| m-1 | fixed | Band 22-29; box top +11 keeps 2 mm under the cheeks at a 22 mm pin; bracket 23.1-28.9 inside it. |
| m-2 | fixed | Per-step machine / needle / thread / stitch in ops 4.05 / 4.08, with BT-301 named. |
| m-3 | fixed | BT-S 10 x 2 everywhere (W3G gone). |
| m-4 | fixed | IMC 192, boxes 5 mm from each raw end (1:1 page 2). |
| m-5 | fixed | Op 7.13 hardware first, listed. |
| m-6 | fixed | B25-BOX on the DXF note and SK-1 (overprint m-9). |
| m-7 | fixed | Bore gauge at the loop centre. |
| m-8 | fixed | 2.0 m bar stock; 288 N step; TL-1b x 2. |
| m-9 | fixed | HOSE-LOW z 558 (op 4.11). |
| m-10 | fixed | BOM camo `proto_qty` 0.0, "PRODUCTION ONLY". |
| m-11 | fixed | B-18 label clear on step 2 p. 2. |
| m-12 | fixed (m-8 residue) | Leaders on every line; B-25 and RT added; 1:1 verified. |
| m-13 | fixed | SK-8 (c) names the printed stay and draws the floor with its 5.5 mm gap. |
| m-14 | fixed | Toggle row "BL-004 REC: guy toggles". |

## Answers to the orchestrator's checklist

- **Hinge eye fold vs the throat-corner fillet.** 0.19-0.29 mm in the 0.1 mm corner band, against a slice check
  that assumes 0.05 mm print tolerance. A frame relief is the right fix and costs nothing now that BL-047 reopens the
  print (m-1).
- **Necked IME / US / USA eyes on the sliced print.** All ten stations pass the eye check:
  - under the pin 0.44-1.34 mm;
  - throats 19.96-20.0 mm, with 0.5 mm a side to the 19 mm neck within 0.05 mm.

  The US / USA eyes pass only on the US-ROUTE directions; on the real path they meet the fairlead below (N-1).
- **US-ROUTE.** Not physical. The straight line runs 19-78 mm inside the loaded bag. N-1, blocker.
- **W3-OVER usability.** Acceptable as an owner-overridable call. The buckle envelope under W3 is optimistic at
  kit S (m-3).
- **RT strap from the roll end at 560 mm.** The origin is right; the cut breaks the tail rule and the grip rule
  (m-2).
- **B-25 at about 512 mm on the BL-046 clamp constants.**
  - Reproduced 511.9 mm. Clearances hold (run 2 mm under the socket, 6.4 mm under the webs, 14.5 mm band to clamp,
    23.4 mm to the housing at kit S).
  - The wrap arc is approximate and the cut depends on BL-047 (m-4).
  - The op text is stale or contradictory (m-5).
- **TL-1 at 497 N with the as-built half bridle.** The release still proofs 494 N with no pull direction. The
  BL-046 geometry has not been re-checked (M-A).
- **PT-3 / SEW-F at 625 N.** The loads trace correctly (1530 = 1.5 x 1019; 625 = 1.15 x 1.6 x 1019 / 3). The
  fixture pin is under-specified and marginal (M-C). Results rows and mounting are incomplete (m-6).
- **Op order 4.05-4.13 and 7.x.**
  - Op 4.05 order holds: neck, B-18 rows, place HE, box, baste. The B-18 side rows (x 115 +/- 36 / 42) never cross
    the HE box (x 115 +/- 17).
  - Ops 4.07-4.11 are all on flat gussets before 4.12 / 4.13.
  - K-W loops: 4.
  - B-16 before F-02 goes on (4.14 / 4.15).
  - RT is boxed on the flat hem before 5.03 closes it.
  - IMC and USA have their hardware first; the USA pin loop is closed empty.
  - B-25 laps at frame assembly.
  - No seam becomes unreachable. Text issues: m-5.
- **1:1 webbing pages.** Scale verified (test square 283 px at 72 dpi = 100 mm). Every line is labelled, with B-25
  and RT added. USA overprints the test square (m-8).
- **One-off buy cost.** $501.49 reproduced from the rows. Shop rounding is right and hardware counts match the ops.
  No finding. If M-B forces a second webbing roll or M-C adds steel dowels, add about $5-15.
