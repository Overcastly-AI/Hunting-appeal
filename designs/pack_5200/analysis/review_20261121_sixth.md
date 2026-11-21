# Review 6: CORRIE F rev 3 bag + H1 printed frame (design-reviewer, 2026-11-21, commit 6b0cde1)

Saved verbatim by the orchestrator from the reviewer's report (the reviewer is read-only).

**Counts: 0 blockers, 5 majors, 11 minors.**

**Working tree note.** BL-057 committed 1cbc643 during this review, leaving BUILD_H1, the kit and the register modified. Geometry and code checks are against the 6b0cde1 STLs and code.

## Verdicts

**(1) Bag: ready to cut a first build? Yes, with two conditions.**
- Regenerate the release README first (M-4).
- Cut only after the bag-cut physical gates pass on test pieces printed per BUILD_H1 §3/§10: HE-FIT step 0 (US-ROUTE), PT-3 and SEW-F.

No pattern or operation blocker: 30 seams 0 mismatches at 1 mm; grain lines on 80/80 pieces; release regenerates byte for byte; HE, IM and US eyes pass on the real STL. The two new bag–frame contacts (M-2, M-3) are fixed on the frame/hardware side and change no cut piece.

**(2) Frame: ready to print P1? Test pieces: yes, now. Full frame: not yet.** Print the full frame when:
- (a) CA-1 (with the 2 scar bars), CA-5 and HB-6 have passed (HB-6 before the lower half: pilots are printed into it);
- (b) BL-057 has landed and the suite is green;
- (c) the nut spec is fixed before buying hardware (M-1);
- (d) the whole-body check and the US2 lug check are re-run on the 6b0cde1 STL (M-5).

## What was run
- Full suite: 1 failed, 1295 passed, 11 skipped. Failure `test_physical_test_kit.py::test_order_releases_r1_then_bag_then_bl037` (HB-6b in register but not order of work) from the mid-change BL-057 tree; re-run after BL-057.
- `mfg_corrie_f_rev3.py --check`: 89 ops, 32 load points, min SF 1.36, no holds, thread 18.89/18.88 g, recon 116/0. Regenerated release: 13 files identical.
- Patterns: 30 seams, 0 mismatches; grain lines 80/80.
- STLs watertight single shells. Assembled 1069.40 g; lower 494.58; upper 543.40; clevis 15.71 each. Hip mount 34.26 g, D49.99 × 3, 8 × D5.5 on pattern (0 error), D10 pin hole. Lower half first layer is the D50 boss face (1706 mm²).
- `he_stl_check` pass (worst 1.088 mm); `imus_stl_check` pass (min 0.68 mm, IM1); `us_route` reproduces 12.4 / 14.6 mm.

## MAJORS

### M-1 Shopping-list nut does not fit the printed nut traps (US2 clevis, z 234)
`BUILD_H1.md:30` (HW-M5-NUT "ISO 4032 (8 AF x 4 mm)", from `frame_h1_build.py:1111`); `h1_bedfit.py:81-82`, `frame_h1.py:80-81` (`nut_t = 4.0`). ISO 4032 M5 is 4.4–4.7 mm thick; 4.0 is DIN 934. US2 pocket |x| 144.8–148.8 = 4.0 mm; z 234 slot 4.4 mm. A spec nut won't seat; screw tip (|x| 144.0) barely reaches a 4.7 mm nut's end.
**Fix:** specify DIN 934 A2 M5, m = 4.0, caliper ≤ 4.1 in BUILD_H1 §7.2/§8.2; or lengthen pockets to 4.9 mm and re-check protrusion and walls.

### M-2 Pin R-clip has no drawn envelope/orientation; at US1/US2 it can only point into the bag
`h1_rev5.py:803-804` (cross hole 1.3 mm, 2.5 mm past far cheek); `BUILD_H1.md:33, :189`. Clip plane free space ±5.5 mm in z; fore 24–26 mm at US1 but 7.5 mm at US2; aft open → at US2 the clip lies aft past fairlead tips (y 24) into B-01 and the meat. Hinge/IM stations (26–30 mm free) unchecked. US2 tether route (head |x| 184.5 → stay x 115) undefined. 1.3 mm hole for 1.2 mm wire = 0.1 mm clearance.
**Fix:** pick a clip part number, draw it per station with orientation, add its envelope to us_route/HE/bag clearance checks. At US2 consider groove + external retaining ring or a ball-lock pin. Cross hole 1.5–1.6 mm. Add PIN-RET (d): bag on, loaded, no clip marks on B-01.

### M-3 US2 pin head stands proud of the clevis face in the free bag drape; unchecked
`us_route.py:813-873` (`head_clearance` covers only the bolt heads); FIT-US `physical_test_kit.py:483`. Head D8 × 1.5 at x 183–184.5, y 16.4, z 142, plus tether knot. Cloth-to-head: −0.6 mm (23 in fill R), −0.3 (19 in R), +0.9 (23 in L).
**Fix:** counterbore head into clevis face (D9 × 2, clevis reprint only) or flush head with moved tether hole. Add pin head + tether to `head_clearance` and FIT-US marks.

### M-4 Bag release README stale on cut status and belly rule; BOM frame-kit line stale
`outputs/release/pack5200_corrie_f_rev3/manufacturing/README.md:61` still "NOT ready to cut … a FIFTH review decides", N-1b open, no review-5/6 table. `:211`, `:222` present BELLY-MIN 60 mm as structural; BL-053 designs to 40 mm and BUILD_H1:285 calls it advice. op 7.25 (`op_sequence.md:350`) "minimum-belly gauge". `bom.csv:47` old pins (10 × 7075 36 mm, Ti 44 mm); now 4 Ti + 8 × 7075, 41.1/45.1 mm, headed, R-clips, tethers.
**Fix:** regenerate README with review-5/6 status and gated cut status; BELLY-MIN/GAUGE as advice; BOM frame-kit line from `h1_closeout.json` `pins.bom`.

### M-5 Real-geometry checks not run on the geometry being printed
`h1_closeout.md:16` body run on BL-053 + lug fixes; D50 boss excluded (BOSS-LOCAL "settled by review 6"). `clevis_bl056.py` re-ran joint + gauges only after US2 blocks grew; US2 lug submodel (h1_rev5 `sub_fea` 3.33/1.5) not re-run. Cinch-cycled basis already 0.84.
**Fix:** run `h1_closeout --body` and the h1_rev5 lug check on 6b0cde1 `h1_assembled.stl` before printing the halves; point BOSS-LOCAL at that run.

## MINORS

| # | Where | Finding | Fix |
|---|---|---|---|
| m-1 | `physical_test_kit.py:484` → `guides/G6.md:235` | FIT-US pass string missing `f` prefix; raw `{...}` printed | Add `f`; test no guide contains `{` |
| m-2 | `h1_closeout.py:587`, `hip_mount.py:54`, `BUILD_H1.md:42` | M5 × 14 tip 11.0 mm deep in 11.5 mm pilot whose bottom 2 mm is melt reservoir; can bottom, false torque | M5 × 12 (9 mm engagement) |
| m-3 | `hip_mount.py:53, 637`; `h1_closeout.py:689` | Heads 0.69 mm apart; D5.5 holes give 0.25 mm play vs hand-set inserts; DIN 7984 M5 takes a 3 mm key, not 4 | Printed insert-setting guide or D5.8 holes; correct key size |
| m-4 | `print/README.md:18-19`; `lug_hip_pivot_mount_fdm_pacf.stl` | FDM prototype hip mount still old D44, no holes | Mark superseded or regenerate |
| m-5 | `BUILD_H1.md` §3 | No chamber temperature for 18–21 h PAHT-CF prints | "chamber heater 50–60 °C" |
| m-6 | `data/materials/hardware/insert_heatset_brass_m5.yaml` | Note says HB-6 ≥ 1.5 kN with 5 inserts | Update to BL-056 |
| m-7 | `test_kit/guides/G2.md:107` | HE-FIT calls "Ti hinge pin 5 mm, 44 mm"; now 45.1, headed, cross hole | Read from `h1_closeout` pins |
| m-8 | `us_route.json` `clevis_heads` | Stored z [134,150]; code gives [135,149] | Regenerate |
| m-9 | `G1.md:32`, `G4.md:346` | HB-6 was Field release at 1.5 kN RT; must gate the lower-half print | Confirm in BL-057 |
| m-10 | `camo/originality_check.md` | Commercial-swatch check not run; provenance unsigned | Close before any printed/sold bag |
| m-11 | BUILD_H1 / README / kit | Stale masses, BL-053 support table (lower plate contact 739 → 1706 mm²), MASS-BAND | Regenerate in BL-057 |

## Review-5 findings status

| ID | Status | Evidence |
|---|---|---|
| B-1 | closed | Supports, blockers, scar sanding, plate-preview gate in BUILD_H1 §2–4 and kit; residue m-11 |
| M-1 | closed | 3D cradle rows h1_rev5 §1; MT-1cr along 3D vectors |
| M-2 | closed in geometry, new issue | Two-step trap on STL (8.2 AF, 2.3 mm walls); pocket length vs nut (M-1 here) |
| M-3 | closed on frame, not bag docs | 40 mm design belly; bag README/op 7.25 still 60 mm (M-4) |
| M-4 | closed | Numeric µε pass lines; CLEVIS-SHARE 3D rows |
| M-5 | partial | Scheme chosen; envelope, orientation, tether route open (M-2) |
| M-6 | closed | Lip r 3, wrap modelled; text bug m-1 |
| M-7 | mostly closed | Residue m-11 |
| m-1, m-2, m-4..m-8, m-10 | closed | |
| m-3 | partial | m-7 here |
| m-9 | accepted | Inspected under FIT-US |

## Assumptions without a physical test
- BOSS-LOCAL names a review as its test (M-5).
- SAND-K settled only indirectly via the CA-1 scar bars.

## Mass traceability
Print masses match STL × 1.06 g/cm³. Hip mount 34.26 g (ledger BL056 +0.27 g). BL-056 print +8.32 g → 1069.4 g. Bag ledger 570.9 vs 571.5 g (−0.10 %).

## Screenshots
- `outputs/screens/20261121_review6_1.png`: US2 nut pocket 4.0 mm vs ISO 4032 4.4–4.7 mm; R-clip plane at US2.
- `outputs/screens/20261121_review6_2.png`: US2 pin head against the 19 in and 23 in fill drapes.
