# Float mode: frame-side FE check (IM3 eye, US1 cradle anchor)

Owner: structural-fea-engineer. 2026-11-06. Hand-off: `meat_carry_alternatives.md` §8. Code: `huntkit/gendesign/float_fea.py`; numbers: `float_fea_results.json`. Standard: HA-LS-1 rev C (`load_standard.md` §4.3, float note).

## Result

- **IM3 eye, design** (36 kg meat + 12 kg gear): 559 N factored. Strength SF **4.01**, fatigue SF **2.04**, creep SF 3.37. Pass.
- **IM3 eye, misuse envelope** (36 kg meat + 32 kg in the bag): 1142 N factored. Strength SF **2.08**, fatigue SF **1.11**, creep SF 2.02. Pass.
- **Inside the bag-on IM3 envelope: yes.** The printed cheek solved at the 1415 N bag-on hook case gives SF 1.54; the misuse float vector is smaller (1142 N) and its FI99 is lower (0.482 vs 0.650).
- **US1 cradle anchor at 56 kg of meat on the frame: fatigue SF 0.95, fails.** Friction is not credited (section 3).
- **Owner-facing limit: float meat on the frame <= 53 kg (116 lb)**, with the cradle cammed to the 70 mm belly. The 68 kg pack rating still applies to meat + gear together.

## 1. IM3 eye under the float vectors (direct, not scaled)

Each IM3 eye carries its meat-strap leg (150 N hand cinch, aft) and one B-24 link (aft and down at 30°). Factored: link x 3.0, cinch x 1.5 (the bag-off rule). Fatigue on the 1.6 g walking peak (cinch 150 N steady + link x 1.6, PAHT-CF FI <= 0.3); creep on 1 g (FI <= 0.4, 40 °C, 8 h). Fairlead stub, 1 mm voxels, layer normal +y (`bag_attach.solve_fairlead`).

| case | factored N (aft / down) | strength SF | was (scaled) | walk N | fatigue SF | was (scaled) | creep SF | bearing SF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| design | 559 (531 / 177) | **4.01** | 3.87 | 327 | **2.04** | 2.18 | 3.37 | 7.74 |
| misuse | 1142 (1040 / 471) | **2.08** | 1.90 | 636 | **1.11** | 1.07 | 2.02 | 3.79 |
| bag-on hook case (reference) | 1415 (1396 / 234) | 1.54 | | | | | | 3.06 |

Requirements: strength SF >= 1.0 on the factored load, fatigue SF >= 1.0, creep SF >= 1.0.

Direct vs scaled. Strength: the print layer normal is +y (aft), so the aft share pulls across the layers (47 MPa) and the downward share is carried more along them (88 MPa); the float vectors are more downward than the solved 554 N, and the direct SF comes out 4-9 % higher than the scaled one. Fatigue: the scaled figure took the walking peak as 1.6 / 3.0 of the whole factored vector. The cinch is a 150 N steady preload, so the walking peak is 150 N + 1.6 x the 1 g link: higher than scaled for the design case (cinch dominates: 2.04, was 2.18), lower for the misuse case (link dominates: 1.11, was 1.07).

Solver checks: the 554 N record vector reproduces SF 3.913 (record 3.913). 
Mesh: misuse vector at 0.75 mm voxels SF 2.03 vs 2.08 at 1 mm (-2.1 %); applied to fatigue, the misuse SF would be 1.08, still >= 1.0. 
The voxel solver is verified against the Timoshenko cantilever and Saint-Venant torsion (`tests/test_frame_topopt.py`) and the H8 cantilever / Q4 patch (`tests/test_gendesign.py`).

## 2. US1 cradle anchor and the float meat limit

The float meat path is the bag-off haul: all the meat's vertical in the two under-straps, US1 takes 60 %, side legs at 31° (70 mm belly over a 115 mm half-span). Strength case 1.6 g x 1.5. Solved directly at each meat mass (fixed direction, so the result is linear in the mass; the direct solves confirm it).

| meat on the frame | US1 tension N | strength SF | fatigue SF | cam SF | US2 fatigue SF |
|---:|---:|---:|---:|---:|---:|
| 36 kg (79 lb) | 489 | 3.28 | **1.47** | 2.25 | 2.21 |
| 53 kg (116 lb) | 720 | 2.23 | **1.00** | 1.53 | 1.50 |
| 56 kg (123 lb) | 760 | 2.11 | **0.95** | 1.45 | 1.42 |

Limit where US1 fatigue reaches 1.0: 53.1 kg, **set at 53 kg (116 lb)**. Strength and the cam keep margin past it; fatigue governs.

Sensitivity to the belly (the user cams to "about 70 mm"; a flatter cradle pulls harder):

| belly mm | tension vs 70 mm | meat limit kg |
|---:|---:|---:|
| 50 | 1.30 | 41 |
| 60 | 1.12 | 47 |
| 70 | 1.00 | 53 |
| 80 | 0.91 | 58 |

The user guide must say: cam the cradle until it hangs about a hand's width (70 mm, 2.75 in) below the straight line between the stays, not tight and flat. At 50 mm the limit drops to about 41 kg.

## 3. Wrap-strap friction: not credited

The hand-off offered to credit W1–W3 / IM friction (μ 0.4, five clamping straps) to lift the 56 kg case. Not done:

- μ 0.4 in `meat_haul.MU` has no source in `data/materials/` or `docs/research/`. A search for a measured wet-fabric coefficient found fabric-on-skin and fabric-on-fabric studies only; one reports a *slight decrease* when the fabric is water-wetted ([J. Eng. Sci., Egypt](https://jest.journals.ekb.eg/article_81022_c05bfb54d692cc3843c62f19788a9fd3.pdf)), another an increase against wet skin ([Kyushu Univ.](https://catalog.lib.kyushu-u.ac.jp/opac_download_md/4738575/2021_p109.pdf)). Nothing for a bloody knit game bag on carbon/ROHACELL or on nylon webbing.
- Even with a sourced μ, the clamp force is unknown: the 150 N cinch is an ASSUMPTION, and W1–W3 are ladder-locked by hand. Meat settles and drains on the trail, so the clamp falls with time.
- Fatigue is the governing check. A friction share has to hold for 1e5 strides; any slip puts the whole load back on the cradle, so it cannot be counted on in fatigue without a test.

Path to 56 kg if the owner wants it: measure it, do not assume it. Prototype test T5f (proposed): 56 kg of wet sandbags in game bags in float, cradle on a load cell or a luggage scale in series with US1, walk or crank 0 -> 1.6 g, record the US1 share. A measured share <= 0.95 x the no-friction value earns 56 kg. Or re-print US1 thicker (outside this task: the anchor geometry belongs to the frame).

## 4. Frame-global effect

The float puts at most 68 kg on the frame with the CG <= 190 mm aft (lever table, `meat_haul_modes.md` C), inside C5 `meat_straps` (68 kg, 190 mm). The vertical enters at US1/US2 (z 95 / 142) and IM3 instead of the z 60 hinge pins: all on the solid lower stay or at an eye already in the IM3 couple variant. ASSUMPTION: the C5 branch-frame result (SF 2.49 `meat_straps`, rev C body check) covers the float globally; the local anchors are the checks above. Not re-solved on the beam model.

## 5. Retired case

The hinge swing (`between`, hinge 264 N, IM3 496 N, CG 110 mm) is retired. It is in no envelope: not in `load_standard.py`, `meat_haul_modes.json`, `attach_system.PROCEDURES` or `rev_c_verification`. The 264.3 N in `frame.yaml` / `crown_loads.yaml` is the crown retention load of the retired rev A shelf case (`meat_shelf_heavy_low`), not the hinge. The bag-on hinge (1019 N factored, HE / B-18) is unchanged.

## Mass

No mass change from this check. Float hardware is the two B-24 links (54.4 g, `meat_haul_modes.json` float.link); the IM3 fairlead (6.1 g printed, each) and the US1 anchor (5.7 g) are unchanged. Mass cut: the IM3 cheek has strength margin 4.0 / fatigue 2.0 in the design case, but the eight fairleads are one shared geometry and the bag-on case governs the hinge one; no cut proposed.

## Assumptions

- ASSUMPTION: link at 30° below horizontal carries the whole bag (no W1–W3 help), as the hand-off.
- ASSUMPTION: the IM cinch is a 150 N steady preload; in fatigue it does not cycle with the stride.
- ASSUMPTION: both forces act on the same pin and load the cheek pair as one resultant on the bore (the meat-strap hook and the link hook sit side by side in the 18 mm throat).
- ASSUMPTION: the bag-on 1415 N hook case acts along the rev C governing IM3 direction (meat_straps).
- ASSUMPTION: US1 takes 60 % of the cradle, belly 70 mm (`meat_haul.py`).
- Fatigue rule: HA-LS-1, 1e5 cycles 0 -> 1.6 g (envelopes the 1.2 g carry rule).

## Screenshots

- `outputs/screens/20261106_float_fea_1.png`
- `outputs/screens/20261106_float_fea_2.png`
