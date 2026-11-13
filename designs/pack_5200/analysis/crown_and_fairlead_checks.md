# Crown tube with the B-25 mitre, spine clamp, IM / US fairleads, loose island (BL-045)

structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-045-crown-and-fairlead-checks.md`. Code: `huntkit/gendesign/bl045_checks.py` (`python -m huntkit.gendesign.bl045_checks`) collecting `crown_tube_guy_loop.b25_topology_recheck`, `crown_spine_clamp.py` (new), `bag_attach.eye_geom / imus_eye_envelope` (new), `h1_fairleads`, `frame_h1.print_mesh`. Tests: `tests/test_bl045_crown_fairleads.py`. Results: `crown_and_fairlead_checks.json`. Checked on the real geometry: the H1 print STL (sliced), the frame beam model (rev C sets on the three crown kits), `corrie_f.b25_topology` and SK-12.

## Result in short

1. **Crown tube: BL-041's 1.36 / 1.27 is confirmed** (re-run: 1.35 static, 1.27 fatigue on the real pull vectors). The 45 deg mitre, the drop and the necked run all sit 14 mm or more below the bar's underside, so only the 38 mm sleeve bears on the bar. The run's tension (the guy's outboard part, up to 14%) pulls the sleeve down through the drop; with the real directions the radial load is 1.006 x BL-041's scalar sum. Taking that run pull in line with the guy (a bound) gives 1.22 / 1.14. TL-1's proof moves 494 -> **497 N**.
2. **Spine clamp: real dimensions published** (`crown_spine_clamp`). The joint carries 55 N m and 749 N factored (never checked before). Sized as the frame's own bonded joint: 7075 T-fitting, saddle **24 mm along the bar (half-width 12.0, was 15 assumed)**, socket 15 mm, **collar 12.8 mm below the bar (was 12 assumed)**, 10.4 g (frame.yaml books 6.0). Real pawl housing from the STL: **15.6 mm above the pawl line (was 20), |x| 24.8 (was 18)**. **B-25's clearances hold**: band to clamp 14.5 mm (>= 10), spine wrap 16.6 mm above the housing at kit S 15 in (BL-043: 13), mitre 20.0 mm above the printed body. **But the spine sits 15.8 mm fore of the bar** (the printed channel), so B-25's run is 17 mm longer a side (cut +34 mm), and **the OD 20 spine tube does not fit the printed channel** (18.3 mm deep; see Found, not fixed).
3. **IM / US fairleads: webbing wraps all ten pins** (IME 38 mm eyes at IM1-IM3, the US 25 mm eye and the cam anchor at US1-US2; hooks and carabiners clip the eyes, never a pin). A necked 38 mm eye is 3 plies (4.5 mm) and could not pass the 1.9 mm gap. **All ten now carry the hinge's clearance** (gap 5.5, throat 20, saddle; on the crown sleeve the root stops 1 mm above the bore), in the print files, slice-checked **12 / 12 with the eye stack**. Every station passes. The US fairleads gain most: their fatigue was below 1.0 at the cradle load before (0.93) and is 1.77 now (saddle on a solid stay). IM1 / IM2 lose margin (the pin rises 3.6 mm and the bore limits the root): IM2 fatigue 2.15 -> 1.40; IM3 on the sim loads 1.70 -> 1.49 (goal 1.15).
4. **Loose island: found and fixed.** The 571 mm3 piece at (84, -0.4, 226) is the tip of the right lower branch. The 2 mm voxel body (and so every FEA) joins it to the inboard bolt boss below z 234; the print export took the whole voxel boss out of the smoothing field before adding the exact boss, which opened a one-voxel gap. The field now keeps the boss voxels up to 2 mm inside the capsule (`frame_h1.BOSS_CORE_MM`): no half drops anything.
5. **Stale records re-run:** rev C hinge cheek 2.97 -> **3.73** (fatigue 2.10) on the BL-042 geometry; IM3 3.60 -> 6.03; 'fairleads present 1.000' removed from `h1_buckling.md` (now the voxel stub fraction + the STL slice check) and from `frame_fixed.py`.

**Mass:** printed body 861.6 g (30.39 oz; was 845.7): fairleads +50.4 g net (was +37.2; the ten new saddles +13.3 g), island fix +2.6 g. Spine clamp 10.4 g against 6.0 booked (+4.4 g, not in the ledger yet). B-25 cut +34 mm of 38 mm webbing (+0.95 g).

## 1. Crown tube under B-25 as BL-043 built it

**What bears on the bar** (`corrie_f.b25_topology`, s = down the spine from the bar centre, bar radius 9):

| part | x mm | s mm | on the bar? |
|---|---|---|---|
| sleeve (1 wrap + 15 mm lap, 38 mm) | 26.5-64.5 | round the bar | **yes, 38 mm** |
| drop | band | 9.0-23.0 | no (0 mm below the underside) |
| mitre | band | 23.0-61.0 | no (14 mm below the underside) |
| necked run + spine wrap | 11.2-26.5, round the spine | 23.0-48.0 | no (14 mm below the underside) |

The mitre's extra layers lie on the aft face of the drop, below the bar: they add no bearing and take none away. The toggle tab is now the full 38 mm strip (BL-041 had a 25 mm tab on a 38 mm sleeve); the 30 mm POM toggle spreads into it.

**Pull direction.** Per sim run and side: the guy's direction at the bar (port routing), the crown strap's, and the run tension = guy x its outboard share (the drop pulls the sleeve straight down). Radial (y-z) resultant against BL-041's scalar sum (guy + strap):

| torso | case | side | guy 1 g N | strap 1 g N | guy below horizontal | outboard share | run tension N | radial N | / scalar |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 15 | fill | R | 51.3 | 11.6 | 2 deg | -0.004 | 0.0 | 58.5 | 0.930 |
| 15 | fill | L | 51.3 | 11.6 | 21 deg | -0.429 | 0.0 | 50.1 | 0.796 |
| 15 | meat | R | 33.7 | 11.1 | -2 deg | -0.010 | 0.0 | 40.9 | 0.913 |
| 15 | meat | L | 33.7 | 11.1 | 29 deg | -0.509 | 0.0 | 31.3 | 0.699 |
| 19 | fill | R | 74.5 | 7.0 | 21 deg | -0.188 | 0.0 | 75.5 | 0.926 |
| 19 | fill | L | 74.5 | 7.0 | 22 deg | +0.005 | 0.4 | 76.6 | 0.939 |
| 19 | meat | R | 54.9 | 6.1 | 23 deg | -0.228 | 0.0 | 54.9 | 0.901 |
| 19 | meat | L | 54.9 | 6.1 | 23 deg | -0.023 | 0.0 | 56.2 | 0.922 |
| 23 | fill | R | 95.8 | 6.8 | 57 deg | +0.052 | 5.0 | 98.8 | 0.963 |
| 23 | fill | L | 95.8 | 6.8 | 57 deg | +0.114 | 10.9 | 103.2 | 1.006 |
| 23 | meat | R | 68.3 | 6.5 | 59 deg | +0.029 | 2.0 | 68.7 | 0.918 |
| 23 | meat | L | 68.3 | 6.5 | 59 deg | +0.136 | 9.3 | 74.0 | 0.989 |

At 23 in the guy runs 57-59 deg below horizontal and the drop pulls down too, so they add; the crown strap pulls up and aft and takes some back. Worst ratio **1.006** (23 in fill, left). With the run tension put in line with the guy (bound) 1.116. An inboard pull (up to 51% at 15 in) slackens the run; the sleeve is then held by its own grip, 14.5 mm short of the clamp.

**Ring check (basis A, rev C bar, envelope 323 N static / 172 N fatigue peak x the ratio):**

| case | width mm | static N | capacity N (kd) | static SF | fatigue SF |
|---|---:|---:|---:|---:|---:|
| BL-041 scalar sum (record) | 38 | 323 | 439 | **1.36** | **1.27** |
| real pull vectors | 38 | 325 | 439 | **1.35** | **1.27** |
| run tension in line (bound) | 38 | 360 | 439 | **1.22** | **1.14** |
| vectors, 30 mm (toggle only) | 30 | 325 | 348 | **1.07** | **1.00** |
| bound, 30 mm (toggle only) | 30 | 360 | 348 | **0.97** | **0.91** |

- **Confirmed: 1.36 / 1.27 stands** (1.35 / 1.27 on the vectors). The bound still passes (1.22 / 1.14).
- The only way it fails is if the 30 mm toggle's pull did not spread over the 38 mm sleeve AND the run pulled in line (0.97 / 0.91). ASSUMPTION WIDE_SLEEVE stays (spread 4 mm a side over the 30 mm tab leg, milder than BL-041's 6.5 mm from a 25 mm tab); TL-1 tests the as-built part and settles it.
- Spine wall under the 25 mm spine wrap: run tension 39 N factored, basis A capacity 265 N: SF 6.8.
- **TL-1 proof 497 N** (323 x 1.006 / 0.654; 494 before). The rig pulls the guy toggle 57 deg below horizontal and 14 % outboard (the worst measured), with the run's spine end anchored: then the drop leg loads the sleeve as on the frame.

## 2. Spine clamp: real dimensions

**Loads** at the spine-to-bar node TB1 of the frame model (`huntkit.fea.pack5200`, built by `crown_diet.build` for kits S / M / L at both ends of their range, every HA-LS-1 rev C set, both couple variants; factored):

- spine end: N 749 N, V 735 N, M **55.1 N m** (a_S 15 in side_hill_torsion (crown_bar));
- jump in the bar across TB1: torsion 39.6 N m, bending 54.9 N m.

A 6 g split collar that only grips has no rated slip under 55 N m, so the clamp is sized as the frame's own joint (ASSUMPTION CLAMP-TYPE): a machined 7075-T6 T-fitting bonded with MMA at the crown corners' 0.8 mm bondline, checked by `huntkit.fea.joints.bond_check` with HA-LS-1 rev C's bond rule (average >= case factor, Volkersen peak >= 1.0 at limit, fatigue <= 0.3 x lap shear at 1.6 g):

| bond | length mm | average | peak (limit) | fatigue avg | fatigue peak | with transverse shear (avg / peak) |
|---|---:|---:|---:|---:|---:|---|
| socket on the spine | 15 | 1.28 | 1.09 | 2.29 | 1.32 | 1.28 / 1.04 |
| saddle on the bar | 24 | 1.77 | 1.03 | 6.28 | 1.32 | 1.75 / 0.78 |

The bond rule alone asks 12 mm of socket and 19 mm of saddle; the socket is set to 15 mm (ASSUMPTION SOCKET-MIN) and the saddle to the socket's OD (24 mm). The wall is 0.8 mm: a 1.5 mm saddle is stiffer and its Volkersen peak on the bar never reaches 1.0 (0.93 plateau). Socket bending: 194 MPa factored, yield SF 2.38; fatigue (Kt 2) 2.44. With the transverse shear added to the bond (the joints module sends it to bearing at the lip), the saddle's peak is 0.78: the T6 coupon of the fitting must cover it.

**Geometry measured on the H1 print STL** (`h1_crown_interfaces`):

| item | BL-043 assumed | real | source |
|---|---:|---:|---|
| pawl housing top above the pawl line | 20 | **15.6** (z 535.6) | STL vertices |
| pawl housing half-width | 18 | **24.8** | STL sections z 520.5-536 |
| body top in the B-25 band (|x| 26.5-64.5) | 531 (OD 22 upper bar) | **519.2** | STL vertices |
| spine channel (x by y) | - | 40.2 x **18.3** mm, centre y -25.7 | STL sections z 510-530 |
| spine axis to bar axis (fore) | 0 (coplanar) | **15.85** | channel centre vs frame model |
| clamp half-width along the bar | 15 | **12.0** | size_clamp |
| clamp collar below the bar | 12 | **12.8** | size_clamp (socket from s 6.8 for 15 mm) |
| clamp fore / aft faces from the bar axis | - | 27.4 fore / 10.6 aft | size_clamp |
| clamp mass | 6.0 | **10.4 g** | 7075 + MMA volumes |

**B-25 on the real clamp and housing** (corrie_f.b25_topology's checks, each crown kit at its shortest torso):

| kit | torso in | spine wrap to housing mm | run to body mm | mitre to body in band mm | mitre to housing side (x) mm | ok |
|---|---:|---:|---:|---:|---:|---|
| S | 15 | 16.6 | 16.6 | 20.0 | 1.68 | yes |
| M | 17.5 | 80.1 | 80.1 | 83.5 | 1.68 | yes |
| L | 20 | 143.6 | 143.6 | 147.1 | 1.68 | yes |

Band to clamp: **14.5 mm** (>= 10). The run top moves to s 23.8 (BL-043: 23.0). The mitre ends 1.7 mm outboard of the housing's side; in height it is 3.6 mm above the housing top and it lies on the bar's aft face, about 13 mm aft of the housing, so the real 3D gap is larger than either number.

**The run is longer than drawn.** SK-12 draws the spine in the bar's plane. The printed channel puts the spine axis 15.85 mm fore of the bar, so the run from the mitre (on the bar's aft face) to its tangent on the spine wrap is 51.3 mm in plan, not 34.3: **B-25 cut +34 mm** (`crown_spine_clamp.B25_CUT_CHANGE_MM`). The run then crosses below the clamp collar toward the wearer side to reach the spine; nothing of it is above the bar.

**Constants for the pack-designer** (import from `huntkit.gendesign.crown_spine_clamp`; corrie_f is not edited here):

```
SPINE_CLAMP_HALF_X = 12.0
SPINE_CLAMP_COLLAR = 12.8
SPINE_AXIS_FORE_MM = 15.85
SPINE_CLAMP_MASS_G = 10.4
PAWL_HOUSING_UP = 15.62
PAWL_HOUSING_HALF_W = 24.82
BODY_TOP_Z_IN_B25_BAND = 519.18
B25_RUN_EXTRA_PER_SIDE_MM = 17.0
B25_CUT_CHANGE_MM = 34.1
```
They replace corrie_f's SPINE_CLAMP_HALF (15), SPINE_CLAMP_COLLAR (12), PAWL_HOUSING_UP (20), PAWL_HOUSING_HALF_W (18) and the OD 22 upper-bar top. With them, `b25_topology`'s `clamp_envelope` (half_x <= 16.5, collar <= 25) holds.

## 3. IM / US fairleads: what passes round each pin

| station | wraps the pin | clips the eye (not the pin) |
|---|---|---|
| IM1 | IME eye, 38 mm poly webbing (frame kit, op 'IME fairlead eyes', pattern IME 200 mm folded at 100 mm, box-X 34 x 30) | IM1 strap girth hitch (L); IM1 G-hook (R) |
| IM2 | IME eye, 38 mm (as im1) | IM2 strap girth hitch (L); IM2 G-hook (R); T2 bag hook |
| IM3 | IME eye, 38 mm (as im1) | IM3 strap girth hitch (L); IM3 wiregate carabiner (R); T3 bag carabiner; B-24 float-link carabiner |
| US1 | L pin: US1 sewn eye, 25 mm poly webbing (pattern US, 50 mm eye fold round the pin sleeve). R pin: the US1 cam's anchor (BOM 'US-anchor', no drawn part: a webbing loop is the only thing that fits the throat; the 32 mm cam body does not) | - |
| US2 | as us1 (US2 strap) | - |

Sources: `patterns_corrie_f_rev3` pieces IME (6 x 200 mm, 38 mm) and US (2 x 550 mm, 25 mm, 50 mm eye fold 'round the left pin sleeve'); `mfg_corrie_f_rev3` load points ('IM fairlead eyes (6) ... captive in the printed fairleads', 'US1/US2 sewn eye on the left pin', BOM 'US-anchor'), SK-11, `attach_system` ('captive eyes sit on pins in UHMWPE sleeves in an 18 mm throat'). Every pin carries webbing, so every one gets an envelope like the hinge's.

**Envelope** (`bag_attach.imus_eye_envelope(station)`, same keys as `HINGE_EYE_ENVELOPE`): neck 18 mm (the 38 mm IME with each edge folded 10 mm in, as the HE; the 25 mm US eye and cam anchor with each edge folded 3.5 mm in), gap under the pin **5.5 mm** (3 plies x 1.5 + 1.0; the 2-ply US eye has 2.5 mm spare), throat **20 mm** (19 mm widest neck + 1). One geometry for all ten (`bag_attach.eye_geom`): the hinge's section with a saddle on the station's own stay; on the crown sleeve (IM1-IM3) the root stops 1 mm above the 18 mm reamed bore (ASSUMPTION EYE-ROOT), so the bore stays open (checked on the STL at z 190 / 330 / 520).

**Strength** (`h1_fairleads.fairlead_fea`, 1 mm voxels, crown bore empty at IM1-IM3; rev C governing factored vectors from `rev_c_verification`; US = the 720 N cradle load of loadpath S5-S7, aft and down at the cradle angle):

| station | load N (case) | BL-042 print: 1/FI99 / fatigue / creep | **BL-045: 1/FI99 / fatigue / creep** | pin yield / fatigue (BL-045) | sim worst (BL-045) |
|---|---|---|---|---|---|
| US1 z 95 | 720 (US cradle, 53 kg float limit (loadpath S5-S7)) | 2.22 / 1.00 / 2.14 | **4.04 / 1.82 / 3.88** | 1.75 / 1.30 | - |
| US2 z 142 | 720 (US cradle, 53 kg float limit (loadpath S5-S7)) | 2.06 / 0.93 / 1.98 | **3.93 / 1.77 / 3.77** | 1.75 / 1.30 | - |
| IM1 z 190 | 273 (meat_straps) | 7.25 / 4.08 / 8.70 | **5.68 / 3.20 / 6.82** | 4.61 / 4.29 | - |
| IM2 z 330 | 512 (side_hill_torsion) | 4.77 / 2.15 / 4.58 | **3.12 / 1.40 / 2.99** | 2.46 / 1.83 | - |
| IM3 z 520 | 605 (meat_straps) | 5.01 / 2.82 / 6.01 | **6.03 / 3.39 / 7.23** | 2.08 / 1.93 | strength 2.66, fatigue 1.49 (F_PR15_fineFM|meat|L; BL-042 1.70) |

Requirements: 1/FI99 >= 1.0 on the factored load, fatigue >= 1.0 (rev C), >= 1.15 on the sim loads (BL-021 goal), creep >= 1.0. The longer pin span (throat 20) costs the pin a little; it stays above 1.

**Print files re-exported** (`h1_buckling.export_print`) and slice-checked with each station's eye stack (`h1_fairleads.check_stl`, the eye polygon shrunk by the 0.05 mm simplify tolerance, `EYE_MESH_TOL`):

| station | gap under pin mm | throat mm | eye stack clear | pass |
|---|---:|---:|---|---|
| hinge_L | 5.50 | 20.0 | True | yes |
| hinge_R | 5.50 | 20.0 | True | yes |
| us1_L | 5.47 | 20.0 | True | yes |
| us1_R | 5.50 | 20.0 | True | yes |
| us2_L | 5.50 | 20.0 | True | yes |
| us2_R | 5.50 | 20.0 | True | yes |
| im1_L | 5.49 | 20.0 | True | yes |
| im1_R | 5.49 | 20.0 | True | yes |
| im2_L | 5.50 | 20.0 | True | yes |
| im2_R | 5.50 | 20.0 | True | yes |
| im3_L | 5.49 | 20.0 | True | yes |
| im3_R | 5.50 | 20.0 | True | yes |

Body checks on the voxel body as printed (throats cleared, holes emptied, all twelve saddles added inside the envelope; `h1_fairleads.body_recheck`):

| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after |
|---|---|---|---|---|
| fine_sm8 | 1.677 / 1.682 | 1.175 / 1.194 | 2.507 / 2.546 | 1.223 / 1.227 |
| fine | 1.677 / 1.682 | 1.196 / 1.212 | 2.551 / 2.585 | 1.223 / 1.227 |
| beam | 1.578 / 1.581 | 1.205 / 1.204 | 2.571 / 2.568 | 1.358 / 1.349 |
| fine_sm8.cyc | 1.677 / 1.682 | 0.782 / 0.787 | 1.668 / 1.679 | 1.035 / 1.024 |

**The bag side must change** (pack-designer, BL-044's files): the IME eyes (op 'IME fairlead eyes') and the US eyes need the 18 mm neck where they pass the throat, as op 4.05 does for the HE; the US cam needs a drawn anchor (a necked 25 mm loop round the right pin, box-X to the cam bar, as IMC does for the IM cams). HE-FIT's dry fit should be repeated on one IM and one US fairlead.

## 4. Lower-half export: the loose island

| | before (git 5c54df9) | after |
|---|---|---|
| lower-half shells after the z 234 split | 2 | 1 |
| dropped piece | 571 mm3 at (84.4, -0.4, 225.5), bounds [[80.0, -6.1, 217.0], [88.9, 5.3, 234.0]] | none |
| printed body g | 845.7 | 861.6 |

**What it was.** The tip of the right lower inboard branch, x 80-89, z 217-234. In the 2 mm voxel body the lower half (z < 234) is one 6-connected piece: the tip is joined to the inboard bolt boss (axis x 96) over z 217-233. `frame_h1.print_mesh` removed every boss voxel from the smoothing field and then added the exact r 8 capsule; the 0.7-voxel Gaussian and the 0.5 level pulled the branch surface back about one voxel from the capsule, so in the mesh the tip touched nothing below z 234 and the split dropped it (it carried load in the FEA: the joint check takes the cut through stay + bosses + branch). The left side happened to stay fused.

**Fix.** Only the boss core (deeper than `BOSS_CORE_MM` = 2 mm inside the capsule) leaves the field, so the smooth body overlaps the exact capsule and fuses where the voxels do. Side effects measured: +2.6 g (thin skins round the four bosses), the outboard boss stands up to 1.2 mm proud of its capsule on the left (|x| 140.6, inside the 152 limit), the wearer and bag faces unchanged, the nut pockets keep their hex (they are cut after). `h1_buckling.md` now says so instead of 'carries nothing'.

## 5. Stale records

- `rev_c_verification` attachments re-run on the printed geometry (`refresh_attachments`; the cheek FE is `h1_fairleads.fairlead_fea` with the crown bore empty at IM3): hinge 2.97 -> **3.73** (fatigue 2.10, creep 4.48), IM3 3.60 -> **6.03**. Nothing else in that record depends on the fairlead geometry.
- `h1_buckling.md` keep-outs: 'fairleads present 1.000' is gone; the record prints the voxel stub fraction under its real name and the STL slice check. The generator now also prints BL-039's corrected spreader-share text (a re-run had been restoring BL-037's wrong sentence).
- `frame_fixed.py` (fixed-torso study) labels the same number 'fairlead stubs inside the envelope present (voxel)'. Its stored `frame_fixed_results.json` (not re-run: a study, not adopted) and `frame_h1_results.json` keep the old key.

## Assumptions that govern

- ASSUMPTION CLAMP-TYPE: The spine clamp is built as the frame's own bonded joint (a socket on each tube, as the stay hubs and crown corners), machined 7075-T6, MMA with the crown corners' 0.8 mm bondline; no clamp friction is credited. A split collar that only grips was not sized: it has no rated slip under a 55 N m joint moment. Settled by: T6 joint coupon of the fitting (as the crown-corner coupons), before bonding.
- ASSUMPTION CLAMP-WALL: 0.8 mm 7075 wall on the socket and the saddle (thinner = lower Volkersen peak on the bar); the two webs joining saddle and socket are 1.5 mm and are not stress-checked here. Settled by: Socket bending SF in the record; the T6 coupon of the fitting loads the webs.
- ASSUMPTION SOCKET-MIN: Socket depth >= 0.75 x spine OD (15 mm) for alignment while the MMA cures; the bond rule alone asks 12 mm. Settled by: -
- ASSUMPTION SPINE-AXIS: The spine axis runs through the centre of the printed spine channel (H1 STL, z 510-530), parallel to the legs; the frame model's spine (in the bar plane) is a beam idealisation. Settled by: Crown dry fit on the printed H1 body (op 7.17 B25-FIT is at the same fit).
- ASSUMPTION TRANSVERSE-SHEAR: As huntkit.fea.joints: transverse shear goes into bearing at the socket lip, not bond shear. A sensitivity with it added to the bond shear is reported. Settled by: T6 coupon.
- ASSUMPTION GUY-DIR: rev 3's guy direction at the bar = the rev 2 port runs' (same B-27 -> B-22 routing). Settled by: PORT-1 / T9 guy angle at each kit.
- ASSUMPTION RUN-TENSION: the run carries the guy's outboard part with no sleeve friction. Settled by: TL-1 pulled at the worst measured angle.
- ASSUMPTION WIDE_SLEEVE (kept): the 30 mm toggle's pull spreads over the 38 mm sleeve. Settled by: TL-1.
- ASSUMPTION EYE-ROOT: on IM1-IM3 the saddle root stops 1 mm above the reamed bore. Settled by: IM3-EC coupon (re-cut from the new file) and first-article bore ream.
- ASSUMPTION HE-T / HE-GAP-MARGIN / HE-NECK-TOL (BL-042) now also govern the IM / US eyes. Settled by: HE-FIT repeated on one IM and one US fairlead.

## Found, not fixed

- **The OD 20 spine tube does not fit the printed spine channel** (40.2 x 18.3 mm through the pawl housing, z 510-530). The channel was sized for the old 30 x 3 mm plate spine; the tube plus the 6 mm rack needs at least 26 mm one way. A frame change (channel and housing) or a spine change; it also fixes where the spine axis really is (here: the channel centre).
- The frame model (`pack5200`) puts the spine in the bar plane; the print puts it 15.85 mm fore. The 15.85 mm offset adds about 750 N x 15.85 mm = 12 N m to the clamp in the worst set; the model does not carry it.
- The spine clamp (10.4 g) and the B-25 cut (+34 mm) are not in the ledger; frame.yaml still books 6 g.
- The US cam on the right pin has no drawn anchor part (BOM 'US-anchor' only).
- `frame_fixed_results.json` and `frame_h1_results.json` keep the old 'fairleads present' key (not re-run).
- Ledger H1F now reads 50.4 g from `h1_fairleads.json`; the print mesh (861.6 g) is still 10 g above raster + H1F (smoothing).

## Screenshots

- `outputs/screens/20261113_BL045_1.png`
- `outputs/screens/20261113_BL045_2.png`
- `outputs/screens/20261113_BL045_3.png`
- `outputs/screens/20261113_BL045_4.png`
