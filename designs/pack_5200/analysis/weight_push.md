# BL-037 weight push: the last 220 g after tests

Owner: pack-designer. Date: 2026-11-13. Code: `designs/pack_5200/weight_push.py` (tests `tests/test_weight_push.py`); numbers: `analysis/weight_push_results.json`. Every mass is a ledger / roll-up row, a record, another module's code, or an ASSUMPTION named below. Base configuration, belt M, crown kit M, as the roll-up. **Do not quote these numbers after the code changes: re-run it.**

## 0. Answer

- **After tests before BL-037: 3211.4 g (7.08 lb); 6.6 lb is 217.7 g away.**
- **Picked (low and medium risk, every rev C factor kept): -119.1 g** (low -64.6, medium -54.5). After tests with the picks: **3092.3 g (6.82 lb)**, still **98.6 g** over 6.6 lb.
- **Target not met: 119 g found against the ticket's 220 g.** No combination of checked, gated technical levers reaches it. The frame-side levers the backlog counted on are smaller than booked: the spreader load share returns at most the upper-branch growth (the mid bar fails in a fill case whatever the spreader does), and CA-1 at 0.40 does not give -70 g on H1 as adopted (section 3).
- The lowest-risk route to 6.6 lb from here is an owner choice: move O-FP-L/R, O-IMP-4, O-IMP-6 to add-ons (-68.5 g) on top of the picks: 3023.8 g (still misses 6.6 lb). These are features, not frozen and not DESIGN requirements; listed, not adopted.
- The 30.1 g left after that is closed by any one of: O-IMP-2 (-32.6 g, owner: hydration (DESIGN requirement); margin +2.5 g, -2.8 g if the cheek risk lands). Every one is an owner-rule or DESIGN-requirement change, or a frame option that needs CA-1 >= 0.40 and a re-run (F-1 fails buckling as run).
- Open booking risk: the 28 mm IM3 cheek may weigh up to +5.3 g more than booked (adds only).
- The picks are a new after-tests step `A_bl037` in the roll-up (`weight_rollup_v2.md`, regenerated). Each is gated by a named test with today's part as the fallback, so proven now and the ledger are unchanged (BL-014 rule).

## 1. Lever list: where we are heaviest per function (after tests before BL-037, base)

| system | g |
|---|---:|
| frame | 1071.8 |
| belt | 441.9 |
| back | 369.0 |
| bag_shell | 359.5 |
| straps_meat | 283.3 |
| harness | 225.1 |
| attachment | 186.4 |
| straps_compression | 140.0 |
| bag_pockets | 102.9 |
| misc | 25.8 |
| fly | 5.9 |
| pouch | 0.0 |

BL-008 split (`weight_configs_proposal.md` section 5): frame side 2375.9 g, bag side 794.7 g, unsplit (thread, labels, IMP-5L) 41.0 g.

| function | ours g | leader | leader g | over g | ratio | source |
|---|---:|---|---:|---:|---:|---|
| frame side (frame, back, belt, harness, meat carry) | 2375.9 | Stone Glacier Krux, M belt | 1247 | +1129 | 1.91 | docs/research/published_weight_definitions.md 2.1 (Gearfool Krux) |
| frame side (frame, back, belt, harness, meat carry) | 2375.9 | Exo K4 frame system | 1332 | +1044 | 1.78 | docs/research/published_weight_definitions.md 2.1 (Exo K4 frame) |
| frame side (frame, back, belt, harness, meat carry) | 2375.9 | Kifaru ARK, M belt | 1400 | +976 | 1.70 | docs/research/published_weight_definitions.md 2.1 (goHunt ARK) |
| bag side (shell, pockets, compression, attachment) | 794.7 | Stone Glacier Sky 5900 bag | 1026 | -231 | 0.77 | docs/research/published_weight_definitions.md 2.1 (SG Sky 5900) |
| bag side (shell, pockets, compression, attachment) | 794.7 | Exo K4 5000 bag only | 1077 | -282 | 0.74 | docs/research/published_weight_definitions.md 2.1 (Exo K4 5000, 'Bag Only: 2lb, 6oz') |
| bag side (shell, pockets, compression, attachment) | 794.7 | KUIU ICON 6 6000 bag | 1350 | -555 | 0.59 | docs/research/published_weight_definitions.md 2.1 (KUIU whitepaper) |
| hipbelt | 441.9 | Stone Glacier 3-piece belt | 363 | +79 | 1.22 | docs/research/hipbelt_fit.md 3 (SG 3-Piece Belt) |
| load spreader / cross stays | 162.3 | Seek Outside 7075 cross stays (pair) | 113 | +49 | 1.44 | docs/research/spreader_research.md (Seek Outside Revolution, fetched) |
| frame structure (stays, crown, torso adjust; no belt, harness, back) | 1071.8 | KUIU ICON 6 frame, tall | 388 | +684 | 2.76 | docs/research/bag_attachment_research.md (KUIU ICON 6: 13.7 oz tall) |

Ranked against the lightest leader per function: frame structure (stays, crown, torso adjust; no belt, harness, back) x2.76 (+684 g vs KUIU ICON 6 frame, tall); frame side (frame, back, belt, harness, meat carry) x1.91 (+1129 g vs Stone Glacier Krux, M belt); load spreader / cross stays x1.44 (+49 g vs Seek Outside 7075 cross stays (pair)); hipbelt x1.22 (+79 g vs Stone Glacier 3-piece belt); bag side (shell, pockets, compression, attachment) x0.77 (-231 g vs Stone Glacier Sky 5900 bag).

Reading: after tests the bag side is lighter than the leaders' bags (0.74-0.77 x SG / Exo; attachment booked on the bag side as BL-008 did), so the bag is not where the grams are; the excess is the frame structure (printed body, carbon crown with three kits, Ti pivot mount), the back system and the belt. The frame structure is about 2.8 x a carbon-stay frame. Those parts are fixed by the owner rules (adjustable torso with three crown kits) and by rev C margins that sit near 1.0 (buckling 1.22, fatigue 1.175, spreader fatigue 1.09), so the levers left there are gated by physical tests (CA-1, MT-1, SPREADER_MAP).

## 2. Candidates

Status: **pick** (implemented as `A_bl037`), **option** (needs a run, a record or a passing test first; not booked), **owner** (a feature or owner-rule change; listed, not adopted), **rejected**, **risk** (can only add). g: base, belt M, negative saves.

| key | system | status | risk | change | g | gate | check | owner rules | build hours | source |
|---|---|---|---|---|---:|---|---|---|---|---|
| B-1 | belt | pick | low | wing load foam + lumbar firm foam EVA 45C 6 mm -> XLPE L200 6 mm (BL-006 d2 + d4, the 'belt-foam reserve') | -31.9 | HB-1 (3 testers) + CS-1 compression set of L200 at 50 % for 22 h | hipbelt fit model, 16 ANSUR II forms, package + BL-037: worst wing 56.5 kPa (limit 56.5), worst hold 0.64 (>= 0.64), lumbar worst 44.7 (watch 48.6): PASS | none | 0 (same pieces and ops; a material or bought-part swap) | hipbelt_diet._mass_delta('d2'/'d4'); xlpe_foam_l200 record (datasheet) |
| B-2 | belt | pick | medium | wing stiffener HDPE 0.75 -> 0.5 mm (BL-006 c3 in place of c2) | -9.7 | HB-D2 wing roll-over, built at 0.5 and 0.75 mm side by side; keep the thinner that passes | same fit-model run (c3 in the package): PASS; 0.5 mm keeps 12.5 % of 1.0 mm's bending stiffness, which the model cannot judge (hence the gate) | none | 0 (same pieces and ops; a material or bought-part swap) | hipbelt_diet._mass_delta('c3') - _mass_delta('c2') |
| B-3 | belt | pick | low | wing comfort foam EVA 30C 5 -> 4 mm (BL-006 d3) | -2.4 | HB-1 | same fit-model run: PASS | none | 0 (same pieces and ops; a material or bought-part swap) | hipbelt_diet._mass_delta('d3') |
| K-1 | back | pick | low | BL-005 backer strip core ROHACELL 71 3 mm -> 2 mm (row b_swR71c2_70) | -5.3 | BP-1 three-point bend coupon at the 2 mm core + BP-2 (already planned for the strip) | back_system2 row b_swR71c2_70: skin 13.49 kPa (<= 13.8), strip SF 1.89 factored, fatigue 4.42, air walk / factored / lean 14.5 / 8.6 / 5.1 mm, gutter 110: PASS (back_system_integration.md 4) | none | 0 (same pieces and ops; a material or bought-part swap) | back_system2.mass_delta_g (both rows) |
| H-1 | harness | pick | medium | J-strap load foam EVA 45C 5 mm -> XLPE L200 5 mm (comfort layer, shell and mesh unchanged) | -22.3 | HS-1 shoulder pressure strips (kit D FSRs) at 30 kg and 68 kg, 3 testers, against today's EVA strap on the other shoulder; + CS-1 compression set | no paper model of shoulder pressure exists in huntkit (stated, not run); the belt model shows XLPE L200 lowering peaks as a load layer (BL-006 d2), the same record | none | 0 (same pieces and ops; a material or bought-part swap) | j_strap_breakdown(): build_geometry strap outline x eva_foam_45c / xlpe_foam_l200 density |
| H-2 | harness | pick | low | sternum buckle Fidlock 25 mm magnetic -> 25 mm side-release (records) | -6.0 | ST-1 gloved one-hand sternum clip-on, 10 tries (R-06 fit trial session); fallback the Fidlock | side-release break 450 N vs Fidlock 300 N (stronger); the sternum is not on an HA-LS-1 load path | QUICK hardware family (build_geometry) loses its magnetic sternum; quiet rule unaffected (both click) | 0 (same pieces and ops; a material or bought-part swap) | fidlock_magnetic_buckle_25mm, buckle_side_release_25mm records |
| G-1 | bag_shell | pick | low | D2 door sliders: #10 slider body with the door cord pull in place of the metal tab (2) | -8.0 | SL-1 weigh 5 sliders on receipt; gloved open / close x 20 | mass only (the door zip is unloaded: strap_arch 0.45 N/mm vs 35.4 N/mm crosswise); quieter (record: a bare metal pull taps the body) | none (quiet rule helped) | 0 (same pieces and ops; a material or bought-part swap) | slider_10 record 19.0 g; ASSUMPTION SLIDER-CORD 15.0 g |
| G-2 | bag_shell + belt | pick | medium | camo accents 630D printable -> HyperD 300 printable on B-02u blades, SH-07 garage, SH-05 belt shards (kick bands SH-01b stay 630D) | -22.5 | AB-1: Martindale (ASTM D4966) both fabrics to 8000 rev + a brush-drag strip on the blade edge; owner print swatch of the camo on HyperD 300; fallback 630D | the zip is sewn to the blade but carries no load (SF 78 on the #10 chain); HyperD 300 seam 42-52 lbf (record) is above any blade load; 630D record is an ESTIMATE | camo stays an accent (rule unchanged); colour match to be judged on the swatch | 0 (same pieces and ops; a material or bought-part swap) | polyester_300d_printable / polyester_ht_630d_printable gsm x corrie_f rows |
| F-3 | frame | pick | low | crown UHMWPE bushings 70 -> 50 mm (crown_diet (e)) | -4.0 | BU-1 slide trial: kit change and pawl travel with 50 mm bushings (L/D 2.8), 20 cycles gloved; fallback 70 mm | crown_diet (e): ring crush SF 1.67 (from 2.33), bearing 12.6; beam loads unchanged; the voxel body spreads each bushing force over 40 mm, so the body is unchanged | none (crown kits unchanged) | 0 (same pieces and ops; a material or bought-part swap) | crown_diet.bushing_g (pack5200.hardware_mass formula) |
| X-1 | misc | pick | low | woven label set -> one printed label on the liner | -7.0 | SL-1 weigh the label set | mass only; both masses are ASSUMPTIONs | none | -0.1 h (one heat press instead of three sewn labels; ASSUMPTION) | geometry.yaml labels_g 8.0 g (ASSUMPTION); ASSUMPTION LABEL 1.0 g |
| F-1 | frame | option | high | CA-1 >= 0.40: take BL-024's G0.55 growth off (BL-027 members and 28 mm cheeks kept, members re-grown) | -9.9 | CA-1 at 0.40 AND MT-1 shows the cinch static (cycled bound below) AND a converged member re-sizing | run here (h1_buckling.full_check, 4 bases) on plain H1 + BL-027 members: -24.9 g gross, fatigue at 0.40 1.33 static, 0.922 cinch cycled (fails if MT-1 shows cycling); Euler buckling 0.965 (mirrored 0.859) < 1.0: FAILS as it stands. re-grown mid +1.4 / upper +3.5 mm: -9.9 g, min 0.952 (fails: the load moves to the lower branches). So the net is at most the figure shown, not -50 to -70 g | none | 0 (same pieces and ops; a material or bought-part swap) | outputs/h1_buckling/check_bl037_h1a0_m1_u2.5_im3.json and axial_bl037_a0_*.pkl (this ticket) |
| F-2 | frame | option | high | spreader load share: take the BL-027 upper-branch growth off (the mid-bar growth must stay) | -13.9 | SPREADER_MAP: a Sandwich v2 plate run on the H1 supports with the cinch preload, then puck load cells / branch strain gauges in the T2 meat test | the mid bar needs its growth whatever the spreader does: the fill hipbelt-off abuse set (no cinch) gives 0.66 on the H1-G0.55 mid bar; so at most the upper-branch 13.9 g of the 22.2 g comes back, and only if the plate run shows the share | none | 0 (same pieces and ops; a material or bought-part swap) | analysis/h1_buckling.json task1 decomposition + chosen member masses |
| F-4 | frame | option | medium | z 234 joint: A2 washers and nuts -> Ti 6Al-4V (8 washers, 4 nuts) | -4.5 | needs Ti washer / nut records (materials-engineer) and a joint re-check (frame_h1.joint_check, bearing on PAHT); anti-seize for Ti on Ti | not run (no record) | none | 0 (same pieces and ops; a material or bought-part swap) | frame_mass_h1.json joint_hardware_g x (1 - rho Ti / rho A2) (ti_6al_4v, sst_304 records) |
| F-5 | frame | option | high | frame print parameters: sparse (gyroid) infill inside thick low-stress regions of the H1 body | - | new coupon series (CA-1 style) at the chosen infill, then the whole body FEA with the reduced stiffness and allowables | not estimable without coupons; the booked body is solid raster x 1060 kg/m3 (record) and the roll-up already bands it +-5 %; weighing the printed halves settles the booking, it is not a lever | none | 0 (same pieces and ops; a material or bought-part swap) | pa12_cf_fdm_paht record; weight_rollup_v2 section 6 |
| F-6 | frame | option | high | stays: BL-017 OD 17 x 7 crown legs in a 19 mm bore (retired at 0.30) back with CA-1 >= 0.40 | -20.6 | CA-1 >= 0.40 and a body re-run with F-1 (not stacked here) | retired: body fatigue 0.97-0.99 on the sim loads at 0.30 (BL-021 (4)); x 1.33 at 0.40 if CA-1 passes; not re-run with F-1 | none | 0 (same pieces and ops; a material or bought-part swap) | crown_diet.option_mass via weight_rollup_v2.crown |
| G-3 | bag_shell | option | low | door chain #10 -> #8 coil (sliders unchanged until a #8 slider record exists) | -7.1 | needs a slider_8 record (materials-engineer) and PT-7 door zip proof on #8 | #8 crosswise 700 N vs #10 900 N (records, ESTIMATE); the door zip is unloaded (SF 78 on #10, about 61 on #8) | none | 0 (same pieces and ops; a material or bought-part swap) | coil_zipper_10 / coil_zipper_8 records x door zip length |
| O-IMP-2 | feature | owner | low | move to an add-on: hydration sleeve (SG sells it separately) | -32.6 | owner decision | no structural effect | hydration (DESIGN requirement) | -1.1 h (build_effort_rev3 ops naming IMP-2) | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-FP-L/R | feature | owner | low | move to an add-on: hip-reach pockets (the BL-002 access fix for the sheep-load 2nd bottle) | -33.5 | owner decision | no structural effect | feature loss (not frozen, not a DESIGN requirement) | not in the bag op list | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-IMP-5L | feature | owner | low | move to an add-on: hipbelt pocket (SG, Exo, Seek sell them separately) | -15.2 | owner decision | no structural effect | hipbelt pockets (DESIGN requirement) | not in the bag op list | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-IMP-4 | feature | owner | low | move to an add-on: kill-kit / first-aid door pocket | -23.9 | owner decision | no structural effect | feature loss (not frozen, not a DESIGN requirement) | -3.0 h (build_effort_rev3 ops naming IMP-4) | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-IMP-6 | feature | owner | low | move to an add-on: shoulder-strap phone pocket | -11.1 | owner decision | no structural effect | feature loss (not frozen, not a DESIGN requirement) | not in the bag op list | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-B-11 | feature | owner | low | move to an add-on: lash tabs + muzzle keepers (rifle carry) | -12.0 | owner decision | no structural effect | rifle carry (DESIGN requirement) | -1.1 h (build_effort_rev3 ops naming B-11) | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-E-5 | feature | owner | low | move to an add-on: pole quiver (trekking pole / tripod leg carry) | -5.4 | owner decision | no structural effect | trekking pole / tripod carry (DESIGN requirement) | not in the bag op list | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-IMP-8 | feature | owner | low | move to an add-on: bow cam / limb cup (bow carry: owner-frozen) | -7.5 | owner decision | no structural effect | bow carry (owner-frozen) | -1.6 h (build_effort_rev3 ops naming IMP-8) | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-US- | feature | owner | low | move to an add-on: under-straps (owner-frozen) | -105.4 | owner decision | no structural effect | under-straps (owner-frozen) | not in the bag op list | weight_rollup_v2.feature_costs (CORRIE F base rows) |
| O-cams | straps_meat | owner | medium | IM1-IM3 and US1/US2 aluminium cams -> heavy 25 mm ladder locks | -26.0 | owner decision (aluminium cams are owner-fixed) + MT-1..3 with ladder locks | ladder_lock_25mm_heavy mass is an ASSUMPTION in its record | changes 'aluminium cams' (DECISIONS) | 0 (same pieces and ops; a material or bought-part swap) | cam_25mm_al, ladder_lock_25mm_heavy records |
| O-cord | frame | owner | low | drop the torso release cord + toggle (adjust with the pack off) | -3.2 | owner decision | no structural effect (crown_diet section 7) | no on-body lengthening | 0 (same pieces and ops; a material or bought-part swap) | crown_diet.TORSO_ADJUST_ROW_G - webbing - cam |
| O-slider | bag_shell | owner | low | D2 door with one slider instead of two (on top of G-1) | -15.0 | owner decision | no structural effect | door opens from one side only (no top peek) | 0 (same pieces and ops; a material or bought-part swap) | ASSUMPTION SLIDER-CORD |
| R-1 | straps_meat | rejected | - | IM fairlead eyes 38 -> 25 mm webbing | - | - | the eyes are captive in the printed fairlead slots (released H1 print) and take the 38 mm bag hooks | - | - | - |
| R-2 | bag_shell | rejected | - | roll-top HDPE strip thinner | - | - | already 0.8 mm (bag_concepts.HDPE_T) | - | - | - |
| R-3 | back | rejected | - | lighter spreader core | - | - | Sandwich v2 is at FPF 1.25 / fatigue 1.09 / sandwich 1.11 (owner decision, 7 mm core); no lighter row passes | - | - | - |
| R-4 | bag | rejected | - | DCF hybrid / laminates on the shell | - | - | crinkle: breaks the quiet rule (owner-frozen) | - | - | - |
| R-5 | harness + back | rejected | - | lighter spacer mesh on straps and back | - | - | no lighter breathable spacer record; ask the materials-engineer for one (back mesh 67.6 g, strap faces 29.7 g) | - | - | - |
| R-6 | harness + belt | rejected | - | yoke plate / 7075 belt plate thinner | - | - | both are rev C fixes (C-7, C-1..3) | - | - | - |
| R-7 | frame | rejected | - | fixed torso | - | - | retired: fatigue below 1.0 on the sim loads; owner keeps three crown kits | - | - | - |
| RISK-cheek | frame | risk | - | 28 mm IM3 cheek booking: stand-alone fairlead volume vs the raster share | +5.3 | weigh the two printed halves against the slicer | adds up to this much; never saves | - | - | weight_rollup_v2.cheek_g - ledger.h1_body_update im3_cheek_28_g |

## 3. The items the ticket named

- **Spreader load share (about 22 g):** BL-027's +22.2 g is the mid bar (+8.3 g) and the upper branches (+13.9 g). Re-reading BL-027's own decomposition: the mid bar needs its growth whatever the spreader does: the fill hipbelt-off abuse set (no cinch) gives 0.66 on the H1-G0.55 mid bar (set `S_fill@a_L_fine_sm8_23:hipbelt_off_abuse|23`, compression 126 N factored). So a spreader share can return at most the upper-branch 13.9 g, and only after a plate run shows it (option F-2). BL-027's '22 g could come back off' is not right (Found, not fixed: the sentence is in h1_buckling.md 4.2).
- **CA-1 at 0.40 (the -70 g lever):** the -50 to -70 g came from team A's unconverged estimate on the older body (frame_comp_A). On H1 as adopted, the only growth a better fatigue ratio can release is BL-024's G0.55 offset. Run here: BL-027 members + 28 mm cheeks on plain H1, 775.7 g (-24.9 g). Fatigue at 0.30 / 0.40: fine_sm8 0.995 / 1.326, cinch cycled 0.692 / 0.922, strength 1.50, creep 1.48; **Euler buckling 0.965, mirrored 0.859: fails** (BL-024's lower-body offset was carrying part of the member load; not split here). One re-growth step (fine_sm8 axial run): mid +1.4 / upper +3.5 mm, 790.8 g (-9.9 g), buckling min 0.952 on branch lower (z 165-330) L. So the net is under 10 g and still not converged, and it needs CA-1 >= 0.40 and MT-1 static (cinch cycled 0.922 at 0.40). Option F-1, not picked. The TEST_PLAN line 'CA-1 at 0.40: body about -50 to -70 g' is corrected there.
- **28 mm cheek booking:** up to +5.3 g unbooked (stand-alone fairlead volume 7.3 g vs 2.0 g in the raster); weigh the printed halves.
- **Harness and belt foam / fabric:** B-1, B-3 (belt foam), B-2 (stiffener), H-1 (strap foam) picked; strap and back meshes have no lighter record (R-5); the yoke and belt plates are rev C fixes (R-6).
- **Frame print parameters:** not a lever without coupons (F-5); the booked body is a solid raster at the record density, banded +-5 % in the roll-up; weighing the printed halves settles the booking.
- **Stays:** the OD 17 crown legs come back only with CA-1 >= 0.40 and a re-run (F-6); fixed torso stays retired.
- **Lighter primary fabrics:** the shell swaps are already in after tests (BL-011); DCF breaks the quiet rule (R-4); the camo accents are the remaining fabric lever (G-2).

## 4. Checks run for the picks

- **Belt (B-1, B-2, B-3):** hipbelt fit model, 16 ANSUR II forms, one combined run. Package (BL-006): {"worst_wing_kpa": 56.5, "median_wing_kpa": 50.7, "worst_lumbar_kpa": 45.4, "median_lumbar_kpa": 29.45, "median_hold": 0.715, "worst_hold": 0.64, "min_asis_clear_mm": 3.0, "median_T_req_n": 320.5}. Package + BL-037: {"worst_wing_kpa": 56.5, "median_wing_kpa": 49.9, "worst_lumbar_kpa": 44.7, "median_lumbar_kpa": 29.3, "median_hold": 0.725, "worst_hold": 0.64, "min_asis_clear_mm": 3.0, "median_T_req_n": 320.5}. Limits {"worst_wing_kpa": 56.5, "worst_hold": 0.64, "lumbar_watch_kpa": 48.6}. **PASS.** The belt is outside every HA-LS-1 load path except the plate and webbing, which do not change.
- **Back (K-1):** back_system2 row `b_swR71c2_70` passes every BL-005 gate; -5.3 g against `b_swR71c3_70`. Spreader unchanged (FPF 1.25, fatigue 1.09).
- **J-strap (H-1):** the pair as booked: shell 14.0 + mesh 29.7 + load foam 31.5 + comfort 15.7 = 90.9 g (geometry.yaml 91.0 g). XLPE L200 load foam 9.2 g. No shoulder-pressure model exists: physical gate HS-1.
- **Frame (F-3):** crown_diet (e) check, ring crush 1.67. **No frame body change is picked**, so H1's rev C results (buckling 1.22, fatigue 1.175, strength 1.58) stand; the H1 print files are unchanged.
- **Bag (G-1, G-2):** no load path; the door zip is unloaded (SF 78). Mass and look gates only.

## 5. Effect on the owner rules (DECISIONS.md)

Adjustable torso with three crown kits: kept. No wings, no hood: kept (nothing added back). Rev 3 top, 25 mm crown straps, aluminium cams: kept (the cam swap is listed as an owner option only). Quiet bag: kept (G-1 quieter; no hook-and-loop, coil zips). Camo as accents: kept (G-2 changes the base cloth under the print). Internal meat straps, under-straps pin to pin, bow and rifle carry, rain fly pocket, 85 L, width: untouched.

## 6. Build hours

Every pick is a material or bought-part swap on the same pieces and operations: build hours unchanged (ASSUMPTION; X-1 saves about 0.1 h). Owner feature moves save the hours listed in section 2 (build_effort_rev3 op names).

## 7. Assumptions that govern

- ASSUMPTION SLIDER-CORD: a #10 slider body with the cord pull weighs 15.0 g (record notes 12-15 g). Settled by SL-1 (weigh 5).
- ASSUMPTION LABEL: one printed label 1.0 g in place of the 8 g woven set (both ASSUMPTIONs). SL-1.
- ASSUMPTION XLPE-SHOULDER: XLPE L200 5 mm under the perforated EVA comfort layer carries the shoulder load without bottoming at 68 kg (no model). Settled by HS-1 (pressure strips, 3 testers) + CS-1.
- ASSUMPTION XLPE-SET: L200 compression set 12 % (datasheet) holds after a season of sweat and heat. CS-1 (50 % for 22 h at 40 C, recovery 24 h).
- ASSUMPTION HYPERD-ABRASION: HyperD 300 (Martindale > 8000, datasheet) wears at least as well as the 630D ESTIMATE record on the blades. AB-1.
- ASSUMPTION BUSHING-LD: L/D 2.8 slides without binding (crown_diet). BU-1.
- Every BL-006, BL-005 and roll-up ASSUMPTION the picks rest on stays as written there.

## 8. Physical gates added (TEST_PLAN.md, BL-037 section)

HS-1 shoulder pressure (H-1), CS-1 XLPE compression set (B-1, H-1), AB-1 HyperD 300 abrasion + print swatch (G-2), SL-1 weigh sliders and labels (G-1, X-1), ST-1 gloved sternum (H-2), BU-1 bushing slide (F-3); HB-1 and HB-D2 extended to the XLPE belt and the 0.5 mm stiffener; BP-1 run at the 2 mm core (K-1).

## 9. Screenshots

- `outputs/screens/20261113_BL037_1.png`
- `outputs/screens/20261113_BL037_2.png`
- `docs/screens/20261113_BL037_1.png`
