# BL-004 Bag-to-frame attachment diet

pack-designer, 2026-11-11. Code: `designs/pack_5200/concepts/attach_diet.py`. Scenarios:
`designs/pack_5200/concepts/attach_diet_scenarios/ad_<variant>_PR{15,19,23}.yaml`. Stored results:
`attach_diet_scenarios/attach_diet_results.json`. Tests: `tests/test_attach_diet.py`. Sims (not tracked):
`outputs/clothsim/attach_diet/<variant>_<shell>_PR<torso>/`. To regenerate them, run
`python designs/pack_5200/concepts/attach_diet.py queue` (one sim at a time, `OMP_NUM_THREADS=2`).

## 1. Result

**Recommended: REC = (c) + (b) + B-17 trim.**
- **(c):** delete the IM2 bag hooks.
- **(b):** delete the crown hood and its ladders. Each guy's crown end becomes a 25 mm webbing loop round the crown top bar, closed by a POM toggle.
- **B-17 trim:** the IM3 tab goes from 110 to 70 mm tall. Its 80 mm loaded seam does not change.

**Mass.** The attachment system goes from **317.7 g (11.2 oz) to 214.7 g (7.6 oz), −103.0 g**.
- The basis is ledger system `attachment`, CORRIE B.2 on H1, belt M.
- The **≤ 220 g goal is met. The 200 g stretch is not.**

**CG at 15 in, meat case** (both converged at the 6 mm rounding stage):

| shell | REC | same-session control V0 | change |
|---|---:|---:|---:|
| S15 (merged bag) | 171.0 mm | 171.7 mm | −0.7 mm |
| CORRIE | 184.0 mm | 182.3 mm | +1.7 mm |

- CORRIE's +1.7 mm is inside the 2 mm re-run scatter that BL-009 measured.
- The ticket's "today" for CORRIE is 184.4 mm, and 184.0 mm is not worse than that.

**Fill CG at 15 in:** 178.4 mm on S15 and 192.1 mm on CORRIE, against 178.5 / 191.5 for V0. Both are inside the rev C limit of 205 mm.

**Times** (gloved, ASSUMPTION unit times as in BL-003): bag off **82 s** (today 85 s, R-08 limit 120 s), bag on 91 s, float 151 s.

**Head clearance (R-28).** At 15 and 19 in, removing the hood gains 1–3° (bare bar). R-28_23_RESULT

What the sims say about each part:
- **The hood carries nothing at 15 in, on both shells** (0 N in fill and meat). Deleting it gives a CG identical to V0
  to 0.1 mm (`B_guys`). The guys do the work at the top.
- **The IM2 bag hooks carry 158–189 N at 1 g, and they are not needed for the CG.** IM3 picks up their load: on
  S15 it goes from 491 to 507 N.
- **Forgetting to fit the guys (M_notop) is the real misuse case.**
  - The meat CG goes to 199.5 mm (S15) and 213.4 mm (CORRIE). That is over rev C's 190 mm.
  - The IM3 hook load goes to 567 N at 1 g, which is **1702 N factored**. That is above the 1415 N the rated hook and
    PT-1 were sized for (section 5).
  - Today's design has the same risk: the hood holds nothing at 15 in, so V0 with the guys not set is close to this case.

TABLE_19_23

## 2. Task 1: every attachment part, its load per rev C case, its margin

Beam-model factored load at each fairlead eye (N, max of L/R), rev C, both couple variants (`@IM3`).
`attach_diet._station_case_loads()` reproduces `rev_c_verification.attachments()`. Single-stay set-down loads the
foot, not these eyes.

| case | hinge z 60 | IM1 z 190 | IM2 z 330 | IM3 z 520 |
|---|---:|---:|---:|---:|
| C1 static_carry | 196 | - | 167 | - |
| C2 drop_2p5g | 294 | - | 250 | - |
| C3 side_hill_torsion | 524 | - | 512 | - |
| C5 meat_straps | 719 | 273 | 430 | 605 |
| C6 tall_load | 724 | 227 | 313 | 376 |
| C7 overload_haul | 511 | 185 | 296 | 421 |
| C6p tall_load_posts | 721 | 220 | 428 | 603 |
| C8 hipbelt_off_abuse | 147 | - | 125 | - |
| C1 static_carry@IM3 | 220 | - | 167 | 286 |
| C2 drop_2p5g@IM3 | 330 | - | 250 | 429 |
| C3 side_hill_torsion@IM3 | 535 | - | 512 | 311 |
| C8 hipbelt_off_abuse@IM3 | 165 | - | 125 | 215 |

The top parts (hood, guys) take rev C's C5 / C7 terms: hood 52.5 N/g, guys 34.6 N/g each. That is 158 / 84 N (hood)
and 104 / 55 N (guy) factored. The IM3 bag hook is designed on the cloth-sim hood-off case: 472 N × 3.0 = 1415 N
(bag_attachment.md section 3).

Columns:
- **Station:** where the part sits.
- **Worst factored N:** the worst rev C case at that station.
- **Margin:** capacity / factored load, from the records. The factored load already includes the required SF, so ≥ 1 passes and ≥ 2 is over twice the requirement.
- **Flag:** NO LOAD = the part carries no load in any case; > 2× = over twice its requirement.

| ledger row (attachment) | g | station | worst factored N (case) | margin | flag | basis |
|---|---:|---|---|---:|---|---|
| B-17 IM3 tabs + B-18 hinge doublers | 27.8 | IM3, hinge | 724 (tall_load) | 2.32 | > 2× | B-17 seam 3277 N / 1415; B-18 3277 / 1019 |
| printed fairleads (8) | 49.4 | all | 724 (tall_load) | 1.67 | | hinge cheek fatigue governs |
| 7075 pins (8) | 19.3 | all | 724 (tall_load) | 14.46 | > 2× | double shear (a 5 mm pin is the smallest sensible pull-pin; not a diet item) |
| UHMWPE sleeves (8) | 2.3 | all | 724 (tall_load) | 2.32 | > 2× | bearing (wear part) |
| bag hooks 38 mm, base mass (4) | 36.0 | IM2, IM3 | 605 (meat_straps) | 1.55 | | IM3 hood-off 1415 N |
| TPU hook sleeves (4) | 4.0 | - | - | - | NO LOAD | quiet |
| webbing eyes, net of old stubs | −6.7 | all | 724 | 2.31 | > 2× | HE / B-18 seam |
| bag-side straps T2 / T3 | 17.9 | IM2, IM3 | 605 | 1.55 | | T3 via the hook; T2 alone 5.45 |
| B-01 swell patches | 12.3 | - | - | - | NO LOAD | cleat clearance (see Found, not fixed) |
| elastic keepers | 3.6 | - | - | - | NO LOAD | quiet |
| lifter tri-glide keepers | 6.0 | - | - | - | NO LOAD | lifter backup (a lifter part, booked here) |
| hood B-19 | 24.3 | top | 158 (C5) | 14.18 | > 2× | **0 N in every 15 / 19 in sim** |
| hood stiffener B-19s | 3.9 | top | 158 | 14.18 | > 2× | |
| hood lining B-19L | 0.6 | - | - | - | NO LOAD | quiet |
| hood ladders B-20 | 20.0 | top | 158 | 4.00 | > 2× | |
| hood tongues + toggles | 10.3 | top | 158 | 8.51 | > 2× | |
| hood grab tab | 1.6 | - | - | - | NO LOAD | |
| top side guys | 18.0 | top | 104 (C5) | 2.68 | > 2× | **S15 sim: 64 N × 3 = 191 N, margin 1.57 on the 300 N ladder-lock slip** |
| guy ladder locks + tri-glides + tabs | 16.5 | top | 104 | 2.68 | > 2× | as above |
| guy corner tabs B-22 | 5.9 | top | 104 | 9.15 | > 2× | |
| guy tail keepers | 1.2 | - | - | - | NO LOAD | |
| IM2 tongue backings B-23 | 7.1 | IM2 | 512 (C3) | 9.00 | > 2× | |
| rated-hook upgrade (4 × +5 g) | 20.0 | IM2, IM3 | 605 | 1.55 | | |
| thread | 2.0 | all | - | - | | |
| B-13x boxed swells (8) | 14.4 | - | - | - | NO LOAD | cleat clearance |
| **total** | **317.7** | | | | | |

Reading the table:
- The heavy parts with no load or more than twice their requirement are the hood family (60.7 g) and the IM2 path
  (hooks, T2, B-23: 47.3 g).
- The no-load parts (sleeves, keepers, lining, swells; 43 g) are there for quiet or for clearance. They stay.
- The pins are over 2× only because a smaller pin cannot be handled with gloves.

## 3. Trials (coarse cloth sim, h 40 mm, 68 kg at 1 g, fill and meat cases)

Method:
- Every variant overrides CORRIE's converged scenarios `corrie_PR{t}c` (6 mm contact rounding, then the 4/3/2/1/0
  continuation, the pouch and the spotter).
- The same file runs S15 with `shell_sweep.install`, as in BL-009.
- CG is mass-weighted, including the pouch and the scope.
- "Rounding" is the contact-rounding stage the case converged at. A case above 0 mm reads up to +4 mm high, and the
  bias is the same for a variant and its control.
- V0 was re-run in this session as the control: CORRIE meat came out 182.3 mm (stored 184.4, BL-009 186.3), S15 171.7
  (stored 171.7).
- Anchor loads are at 1 g, worst of fill and meat, worst side.
- R-28 is `attach_system.r28_loaded` with the simulated wall (+3 mm), using BL-009's drafted-face method. The hood
  term is applied only when the variant keeps the hood.

STORED_TABLE

How to read the trials:
- **(a) Fewer anchor heights.**
  - **The hinge cannot go (`A_hinge`).** With the floor held only by the under-strap channels, the meat case does not
    converge on either shell. Its stalled CG is meaningless, so the variant is **unproven**. The IM2 hook load doubles
    (184 → 384 N) as the bag hangs from the hooks. Bag-on also loses its locator: the bag is tipped onto the hinge pins.
    Rejected; saves 40.9 g on paper.
  - **IM3 is the anchor that matters on CORRIE.** Without it (`A_im3`) the meat CG goes 182.3 → 187.8 mm.
  - **On S15, IM3 can go at 15 in** (170.2 against 171.7, with IM2 at 565 N). But T3 is the float-mode hanger: the
    B-24 links clip into T3. Removing it means redesigning float mode on the IM2 eye, and 19 / 23 in are not run.
    Not recommended this round (section 7).
  - **IM2 can go (`C_im2`):** 171.0 / 184.0 mm meat, fill unchanged.
  - **Anchor heights needed once the guys hold the top: hinge z 60, IM3 z 520, and the guys at the crown.** IM2 adds
    nothing measurable.
- **(b) Lighter top anchor.**
  - Guys alone (`B_guys`) equal V0 at 15 in, because the hood carried 0 N.
  - The ticket's example, two bar loops at x ±60 plus the guys (`B_loops`), is no better. Meat is 172.8 (S15) and
    186.9 (CORRIE, +4.6). The loops carry 3–8 N. Because they must follow the torso setting, they need their own ladder
    lock, so the variant saves only 21.3 g.
  - Guys toggled round the bar win: −48.6 g.
- **(c)** IM2 hooks deleted: −47.3 g, CG within scatter (above).
- **(d) Sewn eyes on the IM3 pins instead of hooks.** The sim is identical to REC (an eye on a pin and a hook on an eye
  are the same 38 mm leg in the model), so the CG is REC's. **Rejected on use.**
  - The 18 mm fairlead throat holds one necked 38 mm eye, so the bag's T3 eye has to replace the frame's IM3 captive
    eye on the pin. Every bag-off then swaps eyes and moves the IM3 strap's girth hitch: bag off **122 s, over R-08**.
  - Float mode then needs a second rated hook on each B-24 link (+28 g in `straps_meat`). The net pack saving is 28 g,
    not 58 g.
  - The bag is not "rarely removed": every meat haul takes it off.
- **Misuse `M_notop`:** see section 1. It sizes the IM3 hook (section 5).

## 4. Procedures (task 3)

Unit times are from `attach_system.PROCEDURES`, with BL-003's additions from `strap_arch.procedures()`. The POM toggle
times are ASSUMPTIONs (4 s off, 5 s on, gloved), settled by timing on the first sewn joint.

| variant | bag off s | bag on s | float s | R-08 (≤ 120 s) |
|---|---:|---:|---:|---|
| V0 today (BL-003 REC count) | 85 | 92 | 154 | pass |
| A_hinge | 77 | 80 | 146 | pass (rejected on the sim) |
| A_im3 | 77 | 84 | 146 | pass (float not workable as built) |
| C_im2 | 77 | 84 | 146 | pass |
| B_guys | 90 | 99 | 159 | pass |
| B_loops | 98 | 109 | 167 | pass |
| D_loops | **122** | 131 | 191 | **fail** |
| **REC** | **82** | **91** | **151** | **pass** |

**REC, bag off (82 s).**

1. Unhook W1–W3 at their G-hooks (12 s).
2. Set the pack on its back pad (3 s).
3. Pull the two guy toggles out of their loops at the crown bar. The guys stay on the bag, at their set length (8 s).
4. Unclip the two IM3 bag hooks and hang them on their keepers (8 s).
5. Unhook the three IM free ends and pull them out through the B-12 ports (21 s).
6. Pop the under-strap cams and slide the floor channels off (12 s).
7. Pull the two tethered hinge pins (8 s).
8. Lift the bag clear (10 s).

**REC, bag on (91 s).**

1. Stand the bag behind the frame (10 s).
2. Tip it onto the z 60 fairleads and pin both hinge eyes (12 s).
3. Lay US1/US2 in the floor channels and cam them (12 s).
4. Clip the two IM3 hooks (8 s).
5. Wrap each guy loop over the crown bar beside the leg and push its toggle through. Check the guy is snug. Its length
   was set once on the packed bag, so do not crank it: cinching fails R-28, bag_attachment.md 2.2 (16 s).
6. Feed the IM free ends in, hook and cam them; put W1–W3 on and snug them (33 s).

**REC, float (151 s):** bag off (82 s); cradle (12 s); IM free ends over the meat (12 s); B-24 pair out of the kit
(5 s); a B-24 on each IM3 eye (8 s); hang the bag by its T3 hooks (14 s); W1–W3 round bag and meat (18 s). Unchanged
from today except the bag-off.

**Gloves.** The toggle is the hood tongue's existing 30 × 8 × 5 mm POM part, a gloved-hand closure. Nothing is threaded
at the crown, and the guy's ladder lock is not touched in use.

**Quiet.** No hook-and-loop. The toggle sits buried in webbing on the bar, and the bar is bare carbon against B-01's
fabric. The XLPE hood lining that stopped the hood tapping is no longer needed, because nothing hard sits on the bar.

## 5. Changed load paths for BL-010 (REC)

Factored = 3.0 × the worst 1 g cloth-sim force over both shells and every torso run (`attach_diet.load_paths()`).

| location | direction | factored N | part | rated N |
|---|---|---:|---|---|
| IM3 eyes z 520, x ±115 | aft-up along T3 from the B-17 bridle to the eye | **1702** (guys-off misuse 567 N at 1 g, CORRIE 15 in; REC with guys 557 N → 1671) | rated 38 mm bag hook, T3 box-X, B-17 seam (80 mm loaded, tab 90 × 70) | hook 2200 (purchase spec); B-17 seam 3277; box-X 5256 |
| IM2 eyes z 330 | bag load removed; meat strap IM2 unchanged | 0 | none (T2, B-23, IM2 hooks deleted) | - |
| crown top bar, x ±(92–100), on the corner-wrap zone beside the leg | aft and outboard toward B-22 (x ±149, z 695); down-aft at 15 in, up-aft at 23 in | 191 (S15 15 in fill, 64 N) | 25 mm webbing loop + POM toggle; ladder lock + tri-glide on B-22 | toggle 670 (ASSUMPTION), ladder-lock slip 300, B-22 seam 1024 |
| crown top bar centre x ±66 | hood capture removed | 0 | none | - |
| hinge eyes z 60, x ±115 | down-aft into the pin, unchanged | 755 (3.0 × 252 N sim; beam 724) | HE on B-18, 5 mm 7075 pull-pin | B-18 seam 2355; bartack 2700 |

What BL-010 has to do with these:
- **IM3 hook.** At 1702 N the rated 2200 N hook is SF 1.29. The bag_attachment rule (proof at 1.5 × factored) asks for
  a **2553 N proof, above the hook's 2200 N rating**.
  - Today's S15 already needs 3 × 491 × 1.5 = 2210 N, above the 2120 N PT-1 proof.
  - So the hook spec has to go up whether or not the diet is adopted. The options are a ≥ 2600 N rated 38 mm hook
    (the mass delta goes to BL-010 / materials), or a misuse rule that accepts SF 1.29 for a top left off.
  - Owner decision 3 below.
- **Beam model.** It books the bag cases' `strap_mid` share on the IM2 nodes (512 N, C3 side_hill_torsion@IM3, SR330).
  With no IM2 bag hook, that share must move to the IM3 and hinge nodes in the rev C frame re-check.
- **Guy loops on the corner wraps.** They now bear on the bar at the corner-wrap / leg corner, as the lifters do,
  instead of through the hood. The 191 N factored is above rev C's guy term (112 N). The 30 mm bare-bar wall check
  (3.16 at 112 N) scales to about 1.85 at 191 N. That is ASSUMPTION-level; BL-010 checks it on the wrap.
- **Hood terms.** Drop rev C's hood term (52.5 N/g) for REC. Raise the guy term to the S15 sim value (64 N at 1 g).

## 6. Mass of REC (ledger rows, `attach_diet.mass_table()`)

| change | g | basis |
|---|---:|---|
| IM2 bag hooks × 2 (rated) | −28.0 | ledger hook rows / 4 (14 g each) |
| IM2 TPU sleeves × 2 | −2.0 | ledger row / 4 |
| T2 tongues × 2 | −8.95 | ledger "bag-side straps" / 4 |
| B-23 backings × 2 | −7.1 | ledger row |
| IM2 hook keepers × 2 | −1.2 | ledger row / 6 |
| hood B-19, B-19s, B-19L, ladders B-20, tongues + toggles, grab tab | −60.7 | ledger rows |
| guy bar loops × 2 (25 mm × 170 mm + POM toggle) | +12.1 | poly_webbing_25mm record; toggle 3 g ASSUMPTION (attach_system) |
| B-17 trimmed 110 → 70 mm (pair) | −7.2 | hypalon_coated_nylon record, cut area |
| **attachment system** | **317.7 → 214.7 (−103.0)** | |

Other variants: A_hinge 276.8, A_im3 257.8, C_im2 270.4, B_guys 269.1, B_loops 296.4, D_loops 184.5 (+28 g on B-24).

The 200 g stretch would need one of these:
- (d), which fails R-08;
- dropping the guy toggles for a girth hitch re-threaded at the ladder lock on every bag-on (−9 g), which resets the
  guy length each time and invites cranking, the R-28 failure mode;
- dropping IM3 on S15 with a float-mode redesign (about −40 g more, unproven).

## 7. ASSUMPTIONS that govern

- ASSUMPTION: guy bar loop 170 mm of 25 mm webbing + 3 g POM toggle, 670 N pull-through. Test: weigh the first sewn guy;
  pull the toggle loop on an 18 mm tube to 287 N (1.5 × 191).
- ASSUMPTION: toggle 4 s off / 5 s on with gloves. Test: the glove timing trial already planned for the PROCEDURES
  times.
- ASSUMPTION: B-17 at 70 mm keeps the 80 mm loaded seam strength. Test: PT-2 on the trimmed tab.
- ASSUMPTION: the sim's guy anchor at [±100, bar face, bar z] stands for the toggled loop beside the leg. Test: first
  prototype, measure where the loop settles on the bar under load.
- ASSUMPTION: the scope sleeve load stays as BL-009 placed it (B-03L, wing offset) after the wings were deleted. The
  owner moved the sleeve to the left gusset. The effect on the guys is second order; settled by FT-S2.
- The sim does not model 25 mm meat / under-straps (BL-003). The under-straps are cinched, so their effective stiffness
  is pretension / 3 % whatever the width.

## 8. Owner decisions needed

1. **Delete the crown hood and its ladders** (−60.7 g). Its job moves to the two guys, which get a toggle loop at the
   bar. This changes the "one lift releases the top" handling of 2026-11-06 to "two toggles". Recommended.
2. **Delete the IM2 bag hooks** (−47.3 g). The bag is held at the hinge, IM3 and the guys. Recommended.
3. **IM3 bag hook rating.** Today's S15 load is already above the PT-1 proof. Either buy a ≥ 2600 N rated hook, or
   accept SF 1.29 on the "guys left off" misuse case. Raised for BL-010 either way.
4. **"Guys on" becomes a carry rule.** With the guys off, the 15 in meat CG is 199.5 mm on S15, over rev C. That is
   true today as well. Consider a bright toggle or a hang-tag check.

## 9. Found, not fixed

- `huntkit/mass/ledger.py`: H1's printed body raster restores the 8 fairleads (`frame_h1.md` section 4), and the ledger
  also books "printed fairleads (8)" 49.4 g in `attachment`. This may be double-booked (BL-013).
- Ledger: "B-01 swell patches" 12.3 g (SPINE's two-ply patches) and CORRIE's B-13x boxed swells 14.4 g are both booked.
  B-13x "replaces the cone caps", so one may be stale (BL-013).
- Ledger: "lifter tri-glide keepers" 6.0 g are a harness/lifter part booked in `attachment`.
- `attach_system.py` `_case_metrics` reads the IM3 hook as `hook_im520_R/L`. That works only because the report also
  writes the summed bridle entry, and it would miss the load if that entry were dropped.
- The S15 guys (64 N at 1 g) and IM3 hooks (491 N at 1 g) are above the values rev C and PT-1 were set from
  (SPINE-era sims). That needs an update in BL-010 whatever happens to this diet.
- R-28 at 23 in (BL-009 open item): see section 1. CORRIE V0 fails at 17° / 20°.

## Screenshots

- `outputs/screens/20261111_BL004_1.png`: CG at 15 in and mass per variant.
- `outputs/screens/20261111_BL004_2.png`: the recommended attachment (side view with the loaded S15 profile; frame-side
  layout).
