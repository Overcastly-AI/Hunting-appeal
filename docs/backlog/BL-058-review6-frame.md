# BL-058 Review-6 frame and hardware findings (M-1, M-2, M-3, M-5; m-2, m-3, m-8)

**Agent:** structural-fea-engineer · **Size:** M · **Date:** 2026-11-21 · **Review:** `designs/pack_5200/analysis/review_20261121_sixth.md`

**Scope.** Fix the frame and hardware side of review 6. BL-057 runs in parallel and owns `docs/backlog/README.md`,
`frame_h1_build.py`, `physical_test_kit.py` and `outputs/release/`. This ticket does not edit those files. It publishes
everything they need in `designs/pack_5200/analysis/bl058.json` for a later wiring pass (see "Hand-off" below).

**Code:** `huntkit/gendesign/bl058_frame.py` (CLI `python -m huntkit.gendesign.bl058_frame [--heavy]`),
**tests:** `tests/test_bl058_frame.py`. Units: mm, N, MPa, g, with imperial in brackets.

## Orchestrator calls and what came back

| Item | Call | Result (numbers from `bl058.json`) |
|---|---|---|
| M-1 nut | DIN 934 M5 (m 4.0), no geometry change | The trap pockets were measured on the STL, not taken from the model. US2 hex pocket: 4.00 mm (R) and 4.05 mm (L), plus a 1.2 mm washer slot. A DIN 934 nut has room left of +0.20 to +0.25 mm at m 4.0 and +0.50 to +0.55 mm at m 3.7. ISO 4032 has -0.45 to -0.50 mm at m 4.7 and -0.15 to -0.20 mm at m 4.4, so **it does not seat at US2 at any thickness in its range.** At z 234 the pocket is 4.38 to 4.44 mm: DIN 934 has +0.58 to +0.94 mm; ISO 4032 seats only for m <= 4.58 to 4.64 (-0.12 / -0.06 at 4.7). The M5 x 35 tip ends 1.0 mm (1.25 pitch) past a DIN 934 nut. Across corners: the hex slot is 8.2 AF (corner circle 9.47 mm), and the nut is 8.0 AF (9.24 mm sharp-cornered), so the nut is held by its flats. **Agreed. The caliper check matters (m <= 4.1).** |
| M-1, found | - | US2 bolt-length window. The tail-hole end sits 0.5 mm past the nominal tip. An M5 x 35 at the +0.5 mm end of the length tolerance (ISO 4759-1 js15) bottoms in the tail hole, and one at -0.5 mm ends only 0.5 mm (0.6 pitch) past the nut. Caliper every M5 x 35 to 34.7-35.3 mm. Fixing it in the print would mean reprinting the lower half, which is out of scope. |
| M-2 retainers | A named part and an orientation per station; groove + ring at US2; cross hole 1.5-1.6 mm | **Hinge, US1, IM1-IM3:** McMaster-Carr 90153A214, an 18-8 hairpin clip for a 3/16 in (4.76 mm) shaft: wire 0.79 mm (1/32 in), length 12.7 mm (1/2 in). It goes in a D1.5 mm cross hole 2.5 mm past the far cheek, hole axis along y, clip body pointing fore (-y). The shanks are unchanged (hinge 45.1 mm, others 41.1 mm), leaving a 1.9 mm end wall past the hole (it was 2.0). Wire double shear is 303 N against a walking pin (BL-053's 1.2 mm wire gave 699 N). No DIN R-clip exists for a 5 mm pin: DIN 11024 starts at 9 mm pins. **US2:** groove D4.0 x 0.74 mm, 0.3-1.04 mm past the inner cheek face, with a DIN 6799 RS 4 E-clip (1.4122 stainless: OD 8.85, 0.7 thick, thrust 934 N (210 lbf)). The US2 shank is 39.1 mm from the counterbore floor. The tether runs from a D1.6 tail hole. Every envelope is 0.5 mm clear of the print (worst 0.02 mm3, the head seat). Every envelope sits under the cheek-tip plane that B-01 rests on: 2.1 mm for the hairpins, 2.88 mm at US2 (rule >= 1). Strap ribbons: US1 13.8 mm, US2 12.9 mm (rule >= 10). Hinge eye: 10.2 mm clear. Fore room on the STL is 18.2-60+ mm against the 13.5 mm needed. |
| M-2 groove | Effect on pin bending / fatigue (Ti, 7075) | The groove is outboard of every bearing, so **its bending moment and shear are 0** for any eye position: the groove costs the pin nothing. US2 pin mid-span: design row 7075 SF 3.16 / fatigue 2.35, Ti 5.66 / 6.35. dy 95 row: 7075 1.96 / 1.46, Ti 3.51 / 3.94 (the counterbore moves the outer reaction inboard, -0 to -1.3 %). If the groove were cut 1 mm inside the cheek by mistake: 7075 yield SF >= 55 (Kt 2.5). Ring thrust SF 7.3 against a walking pin (0.2 x 643 N). |
| M-2 tether at US2 | Define the route | A 180 mm cord (1.5 mm Dyneema) runs from the tail hole (abs x 143.7, z 142) 7 mm inboard along the buttress slot onto the lug arm. It larks-heads round the arm at abs x 132 (section y -12.9..9.3, z 124..160, perimeter 121 mm). It never goes outboard of the clevis face, aft of the tip plane, or across the throat. The free drapes reach the strand on the arm's bag face (**-0.6 mm**): the bag lies on the arm there. PIN-RET (d) and the FIT-US marks settle this, and the owner may drop the tether (see Owner decisions). |
| M-2 PIN-RET (d) | Publish the row | `bl058.json kit.PIN-RET_d`: bag on and loaded (the 20 kg FIT-US stand-in, cam-tight) for 10 min. Pass: no marks from a retainer, tether or pin head on B-01 or the side panel. |
| M-3 | D9 x 2 counterbore, clevis reprint only | `h1_bedfit.pin_cbore_cut` cuts it into both clevises. Head D8 x 1.5 sits **0.5 mm below the face**, the same rule as the bolt heads (head_recess 4.0 - head 3.5). Cloth that can actually be there (outside the clevis solid) clears the pin head by **+1.4 mm** (23 in fill R), +1.7 (19 R), +2.5 (23 L), +6.7 (19 L), and >= 1.4 mm on all 12 drapes. Review 6 measured -0.6 / -0.3 / +0.9 mm with the head proud. E-clip: +4.1 mm. Only the clevis pieces changed (-0.053 g each). The halves keep their volume (lower 494.58 g, upper 543.40 g). |
| M-3, cost | - | The outer cheek's pin bearing drops from 8 to 6 mm, and its UHMWPE sleeve is cut to 6 mm. Sleeve bearing on the design rows: SF >= 2.63 at share 0.6 and 1.58 at share 1.0. The dy 95 sensitivity row at share 1.0 reads **0.98** (it was 1.31). See "Found, not fixed". The US2 lug submodel sees no loss (below). |
| M-5 | `--body` and the US2 lug on the current STL | The assembled STL after the clevis change was re-rastered on the H1 2 mm grid; the boss, the BL-056 blocks and the fairleads are all in it. Boss voxels: 3867 (the BL-053 body had 2626). **Whole body, sanded (governing), static-cinch bases:** strength 1.63, fatigue 1.25, creep 2.66, buckling **1.05**, z 234 joint 1.98 / 1.16. **Cinch-cycled fine_sm8.cyc:** fatigue **0.86** (BL-055: 0.84), buckling 1.02, joint 2.00 / 1.05. BL-055 record (sanded): 1.64 / 1.19 / 2.55 / 1.18, and .cyc fatigue 0.84. **US2 lug submodel:** strength 3.35 / fatigue 1.51 (BL-053: 3.33 / 1.50). BOSS-LOCAL now points at this run. |
| M-5, found | - | Buckling drops from 1.18 to 1.05 because the print's members are 3-8 % thinner than the voxel body. The upper branch's STL slice is 144-147 mm2 (0.223-0.228 in2) against 152-160 mm2 of voxels, so P_cr is 14 % lower. The minimum is still >= 1 (R1), now with a 5 % margin. Every member (fine_sm8): mid bar 1.11 (1.23), upper branch R 1.07 (1.24), lower branch R 1.14 (1.27). |
| m-2 | M5 x 12 | Engagement 8.8-9.0 mm (1.76 d) in the 9.5 mm insert. The tip stops 0.5 mm short of the insert end and 2.5 mm above the measured pilot floor. The old M5 x 14 put its tip 1.5 mm into the melt reservoir, 0.5 mm above the floor. Changed in `h1_closeout.HIP_SCREW_L` and `hip_mount.SCREW_L`. |
| m-3 key | 3 mm | DIN 7984 M5 takes a 3 mm socket (Westfield, Boellhoff), so use a 3 mm hex screwdriver. `KEY_D` is now 4.0 mm (3.46 across corners + 0.5). Driver access is clear of the part and the frame. |
| m-3 holes | D5.5 or D5.8; is a guide needed? | Fixed-fastener budget: H - F = T_mount (0.2 diametral, ASSUMPTION) + T_inserts. D5.5 leaves +/-0.15 mm per insert and D5.8 leaves +/-0.30 mm. Insert scatter (ASSUMPTION INSERT-SCATTER) is +/-0.2 mm with a guide and +/-0.4 mm freehand. Cited bound: FDM prototyping +/-0.5 mm (Hubs, Formlabs); no published figure for hand-set inserts was found. **Result: D5.8 plus a printed guide.** Mount re-exported: FE min SF/goal 1.79 (was 1.80), strip 3.25, -0.28 g. Guide: `test_pieces/hip_insert_guide.stl/.3mf`, D56.3 x 8.5 mm, 8 bores of D7.25 on the pattern, skirt over the D50 boss, 13 g PAHT-CF. Procedure: start each insert through the guide, then finish it flush. |
| m-8 | Regenerate us_route.json | Done on the BL-058 STL (md5 f4994b26). `clevis_heads.head_z_mm` now reads [135, 149]. Route unchanged: US1 12.4 / US2 14.6 mm, pass. |

## Files written
- New: `huntkit/gendesign/bl058_frame.py`, `tests/test_bl058_frame.py`, `designs/pack_5200/analysis/bl058.json`,
  `designs/pack_5200/print/frame_h1/test_pieces/hip_insert_guide.{stl,3mf}`, this file.
- Geometry: `h1_bedfit.py` (counterbore, DIN 934 note), `frame_h1.py` (DIN 934 note), `hip_mount.py` (D5.8, x 12, 3 mm key).
- Re-exported: `print/frame_h1/h1_assembled.stl`, `us2_clevis_{L,R}.{stl,3mf}`, `h1_{lower,upper}_flat.*` (same volume, re-written), `test_pieces/us_route_stay_R*`, `print/lug_hip_pivot_mount_slm_ti.{stl,3mf}`.
- Analysis: `us_route.py` (`head_clearance`: pin head, E-clip, tether), `us_route.json`; `h1_closeout.py` (pins overlay, M5 x 12, BOSS-LOCAL, `body()` takes another solid), `h1_closeout.json/.md` (its `mass` block stays as BL-055 booked it).
- Mass: `huntkit/mass/ledger.py` gets a BL058 row; `weight_rollup_v2.py` gets a step; `tests/test_mass_ledger.py`, `tests/test_weight_rollup_v2.py` and `tests/test_hip_mount.py` were updated.

## Mass (ledger BL058, from `bl058.json mass`)
Frame **-1.23 g** (print -0.11, mount -0.28, 6 hip screws -0.85). Attachment **-5.71 g** (pins -0.24, retainers and tethers
-5.40, US2 outer sleeves -0.07). Total **-6.95 g (-0.25 oz)**. Ledger default config (corrie_b2_h1_v2, belt M) total: 4274.2 g (9.42 lb), from `huntkit/mass/ledger.py`.

## Hand-off to the wiring pass (BL-057 owners), all in `bl058.json`
- `kit.nut`: the DIN 934 line, caliper m <= 4.1, and the US2 M5 x 35 length window 34.7-35.3 mm.
- `kit.hip_screw`: M5 x 12 with a 3 mm key. Today BUILD_H1 / the kit still say M5 x 14 and a 4 mm key, and they read `h1_closeout.json mass.hip_screw`, which keeps the BL-055 booking.
- `kit.pins_bom` (= `h1_closeout.json pins.bom`): a retainer per station and the US2 groove; the HW-PIN-RET line becomes two lines, HW-PIN-RET-H (hairpin) and HW-PIN-RET-E (E-clip).
- `kit.PIN-RET_d`, `kit.FIT-US_marks` (6 items: bolt heads, pin head, clevis face edges, E-clip, tether strand, US1 clip).
- `kit.hip_guide` (file and the 6-step procedure; it goes in BUILD_H1 before HB-6b and the lower-half print).
- `hip_mount` (D5.8 holes) supersedes `hip_mount_bl056.json` geometry for the build text; BL-056's record is kept as is.

## Assumptions (each with its test)
BOLT-LEN, CLIP-FIT, CLIP-ENV, CLIP-MASS, GROOVE-LAND, WALK-MU, KT-GROOVE, TETHER-US2, INSERT-SET, SLM-POS, INSERT-SCATTER,
GUIDE-HEAT, KEY-D and RASTER-2MM. Text and settling tests are in `bl058.json assumptions`.

## Tests
`python -m pytest -q tests/test_bl058_frame.py` covers: probe() against a drilled block (closed form); pin moment
against F(2L - n)/8, and zero at the groove; DIN 934 / ISO 4032 seat on the STL; the counterbore on the STL;
retainers per station; pin rows; groove; hip screws and holes; the insert guide; the published record; the ledger rows.
Full suite: see the ticket report. Two BL-057 tests read the BL-056 masses (`clevis_bl056.json` 1069.4 g;
the print README's 34.3 g mount and its SLM cost). They now see 1069.3 g and the 33.98 g D5.8 mount, and they stay
red until the wiring pass regenerates the print README and reads `bl058.json stl` / `hip_mount`.

## Owner decisions
1. **US2 tether: keep it or drop it?** The US2 pin comes out only at the bench (bag off; the E-clip needs a screwdriver). The tether keeps the pin from being lost then, but one 1.5 mm strand lies between B-01 and the lug arm. Recommended: keep it until PIN-RET (d) shows a mark, then drop it (-0.27 g a side).
2. **US2 outer sleeve at the dy 95 / share 1.0 corner (SF 0.98).** Either accept it as a sensitivity corner (CLEVIS-SHARE B on the reprinted clevis measures the split), or choose a 1.0 mm pin head with a 1.5 mm counterbore (6.5 mm bearing, SF about 1.06).

## Found, not fixed
1. US2 outer sleeve bearing at the dy 95 / share 1.0 corner reads SF 0.98 with 6 mm of bearing (1.31 at 8 mm). Options are an owner decision: a thinner head (1.0 mm) with a 1.5 mm counterbore gives 6.5 mm of bearing; moving the clevis outer face out 2 mm is a bigger clevis change.
2. M5 x 35 tail-hole room is 0.5 mm. A long bolt bottoms. The fix is a caliper window, or a lower-half reprint (tail hole +1 mm).
3. Member buckling on the print is 1.05 (R1 pass). The voxel-body records overstate member sections by 3-8 %.
4. `he_stl_check.py` itself does not read the retainer envelopes. BL-058 checks the hinge clip against the same HE geometry (`us_route.he_shapes`).

## Screenshots
`outputs/screens/20261121_BL058_1.png` (retainers per station), `_2.png` (US2 pin head vs drape), `_3.png` (whole body).
