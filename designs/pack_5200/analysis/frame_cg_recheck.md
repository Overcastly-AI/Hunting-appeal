# Production frame re-check at the cloth-sim load CG

Owner: structural-fea-engineer, 2026-11-05. Standard: HA-LS-1 rev B ([load_standard.md](load_standard.md)), not changed
here. Inputs: [cloth_sim.md](cloth_sim.md) §3.2, [bag_top_anchor.md](bag_top_anchor.md) §3 and §7.
Code: `huntkit/gendesign/frame_cg_recheck.py` (runs) and `frame_cg_recheck_plots.py` (screens). Additive load options
are in `huntkit/fea/load_cases.py` (`LoadCase.cg_z_mm`, `params.couple_top_group`, `params.extra_nodal_1g`; the defaults
reproduce rev B exactly). Tests: `tests/test_frame_cg_recheck.py`. Results: [frame_cg_recheck_results.json](frame_cg_recheck_results.json).

```
python -c "from huntkit.gendesign import frame_cg_recheck as R; R.save(R.run())"   # ~20 min, 4 cores
```

## Verdict

1. **The printed PAHT-CF branch body passes every HA-LS-1 rev B case at every offset checked**, up to 250 mm. The worst
   result is C8 hipbelt-off at 15 in, at the upper bar / pawl housing:

   | scenario | body margin |
   |---|---:|
   | (a) rev B | 1.69 |
   | (b) envelope | 1.50 |
   | (c) as-is 223 mm | 1.39 |
   | (b) with the bag couple on the IM3 hooks | 1.53 |
   | (c) with the bag couple on the IM3 hooks | 1.42 |

   Fatigue is 1.19 → 1.14 → 1.11. With the couple on IM3 it drops to 1.04 / 1.01. Creep-rupture is ≥ 2.15 everywhere.
2. **The carbon crown as built does not pass past about 200 mm.**
   - **Envelope (b):** the spine fails at **0.96** (C8, 15 in).
   - **Couple on IM3:** the legs fail at **0.86 / 0.79** (C8, 23 in), and leg fatigue is 0.98 in (c).
   - **As-is (c):** the corner-bond Volkersen peak is **0.85** (C6p, 15 in).
3. **Minimum fix, crown only, +22.0 g.** Add 0° UD plies on the inside of the wall (OD unchanged, so no print-file change):
   - spine +1 ply;
   - legs +2 plies each;
   - top bar +1 ply;
   - crown-corner bondline 0.8 mm instead of 0.5 mm (glass-bead spacer).

   With the fix, every scenario passes. The worst crown result is 1.01 (c, corner peak) and 1.03 (c with IM3, leg).
   Crown fatigue is ≥ 1.26. The body re-run on the stiffer crown is unchanged within 0.01.
4. **Torso adjust is fine.**
   - Rack SF is 6.27 in every scenario: the C8 crown thrust is set by the shoulder share, not by the CG offset.
   - The printed pawl cheek, with its 304 bushing, goes from 1.57 to 1.39 to 1.29 (FI99).
   - The 3:1 pulley carries almost nothing with the pawl engaged. It does not change with the offset.
5. **Crown top-bar anchor, 210 N per side at C5: passes.**
   - Top-bar member ≥ 2.56, legs ≥ 1.47, corner ≥ 4.3.
   - The body on C5 *improves*, 2.40 → 2.55, because the aft pull offsets the meat's forward push.
   - The bar wall is only safe if the tie bears on **≥ 25 mm of webbing** (SF 1.08). Use 38 mm (1.65) or the crown pocket (4.34).
     A 20 mm guy strap fails ring crush (0.87).
6. **The Sandwich v2 spreader passes at 175 mm**, with fatigue 1.003 and sandwich-local 1.02. It fails at 206 / 223 mm
   (fatigue 0.96 / 0.93, sandwich-local 0.97 / 0.95). The meat CG has to be held at ≤ 175 mm. The pack-designer's IM3
   tab + crown tie does that (combined meat CG 163–174 mm, bag_top_anchor.md §3).
7. **HA-LS-1 should go to rev C with a cloth-sim-calibrated CG.** A draft is in section 6, **not applied**: the owner
   decides. The frame passes rev C as drafted **only with the +22 g crown fix**. The body and the spreader pass as they are.

## 1. What was run

- **Frame.** This is the production frame:
  - the socket-free PAHT-CF branch body, `spreader_layout.raster(None, 2.0)`. It is the same body as the
    `designs/pack_5200/print/frame/` files and the "today" column of [spreader_layout.md](spreader_layout.md) §3. Mass
    is 823 g on the 2 mm raster;
  - the carbon telescoping crown from `frame.yaml`: legs OD 16, top bar OD 18, spine tube OD 20, corner wraps;
  - the Sandwich v2 spreader.
- **Load path.** Every HA-LS-1 rev B case runs on the v2 beam model at 15 / 19 / 23 in. The loads on the fixed frame,
  the bushing forces and the pawl force go onto the 2 mm voxel body, as in `frame_production.verify_solid`. The pass
  rule is the same as the release: margin = 1 / FI99 on the factored load, ≥ 1.0. Clamp and load-patch elements are
  excluded, and the layer normal is y.
- **Validation.** Scenario (a) reproduces the release record exactly: 1.691 at hipbelt_off|15, fatigue 1.193, creep 2.546.
- **Crown.** Checked on the beam model: member first-ply failure with knockdowns, divided by the case factor. Also the
  corner bonds (average ≥ factor, Volkersen peak ≥ 1.0 at limit), bushing bearing, leg ring crush, buckling
  (≥ 1.5 × factor) and fatigue (FI ≤ 0.5 at 1.6 g).

| scenario | C1-C4, C8 (bag) | C5, C7 (meat) | C6, C6p (tall) | CG z (C3) | couple top |
|---|---:|---:|---:|---:|---|
| (a) rev B | 180 | 150 | 160 | node heights (≈ 212) | crown top bar |
| (b) envelope (bag_top_anchor.md §7) | 205 | 175 | 185 | 550 | crown top bar |
| (c) bag as-is worst | 223 | 223 | 223 | 550 | crown top bar |
| (b) / (c) with IM3 | as (b) / (c) | — | — | 550 | IM3 hooks, z 520 on the upper bar |
| sweep | 150 / 180 / 205 / 223 / 250, every case | | | 550 | crown top bar |

- ASSUMPTION: C8 hipbelt-off takes the bag offset. In rev B it is hard-coded at 180 mm.
- ASSUMPTION: C6 / C6p get the same +25 mm as C5 / C7. The envelope gives no number for them.
- (c) applies 223 mm to the meat and tall cases too. That is a bound, not data: the sim's as-is meat CG is 206 mm
  uniform and 181 mm combined.
- **The IM3 sensitivity is new and it matters.** The cloth sim puts most of the bag's overturning into the IM3 hooks
  (450–472 N per side at 1 g, meat), not the crown. Rev B puts the bag couple on the crown top bar. Moving it to z 520
  shortens the lever by about 28 %, loads the upper bar directly, and leaves the shoulder and lifter reactions to bend the legs.
- **CG height** only matters for C3. Rev B lets the lateral component act at the weighted node height (≈ 212 mm).
  The cloth-sim CG is at z ≈ 550. At an unchanged 180 mm offset, that alone drops C3 from 2.88 to 2.35 (sweep s180 vs (a)).
- **C4 set-down** does not change with the offset. With a massless frame, the load's reaction has to act along the
  impact line. ASSUMPTION: e only redistributes forces inside the bag, and that is not modelled.

## 2. Printed body, min margin per case (worst torso in brackets)

| case | factor | (a) rev B | (b) envelope | (c) as-is 223 | (b) couple on IM3 | (c) couple on IM3 | critical location |
|---|---:|---:|---:|---:|---:|---:|---|
| C1 static_carry | 2 | 3.18 (15) | 3.05 (15) | 2.97 (15) | 2.78 (15) | 2.69 (23) | stay below the sleeve |
| C2 stumble (drop_2p5g) | 1.5 | 2.12 (15) | 2.03 (15) | 1.98 (15) | 1.86 (15) | 1.80 (23) | stay below the sleeve |
| C3 side_hill_torsion | 1.5 | 2.88 (15) | 2.31 (15) | 2.26 (15) | 2.16 (19) | 2.10 (19) | stay R below the sleeve |
| C4 single_stay_setdown | 1.5 | 3.42 (23) | 3.42 (23) | 3.42 (23) | 3.37 (23) | 3.37 (23) | stay L below the sleeve |
| C5 meat_straps | 1.5 | 2.59 (23) | 2.40 (23) | 2.09 (23) | — | — | stay R below the sleeve |
| C6 tall_load | 1.5 | 2.94 (15) | 2.94 (15) | 2.87 (15) | — | — | stay below the sleeve |
| C6p tall_load_posts | 1.5 | 2.89 (15) | 2.84 (15) | 2.72 (15) | — | — | stay below the sleeve |
| C7 overload_haul | 1.0 | 3.64 (23) | 3.38 (23) | 2.94 (23) | — | — | stay R below the sleeve |
| **C8 hipbelt_off_abuse** | 1.0 | **1.69 (15)** | **1.50 (15)** | **1.39 (15)** | **1.53 (15)** | **1.42 (15)** | **upper bar / pawl housing** |
| fatigue (C1 at 1.6 g, ratio 0.3) | | 1.19 | 1.14 | 1.11 | 1.04 | 1.01 | |
| creep-rupture (C1 at 1 g, 40 °C 8 h) | | 2.55 | 2.44 | 2.37 | 2.23 | 2.15 | |
| info: fatigue with the meat at 1.6 g | | 1.46 | 1.35 | 1.18 | | | |

- **Location.** Below the sleeve means the stay just under the crown bore at z 140–160 (the top ends of the lumbar
  struts). C8 governs at the pawl housing on the upper bar: the pawl carries the crown thrust into the body there.
- **Hot spots.** `20261105_cgrecheck_1.png` shows a few single elements above FI 1.0 at the pawl load patch and the
  strut ends. These are above the FI99 rule and were treated the same way in the release.
- **Segment joint** (z 234 print split, 2 × 5 mm dowels per flange, 35 mm embed): worst pull-out SF is
  3.31 / 3.09 / 2.73 for (a) / (b) / (c), all on C5 meat at 23 in.

## 3. Carbon crown (beam model), margin = SF / required

| check | (a) rev B | (b) envelope | (c) as-is | (b) couple on IM3 | (c) couple on IM3 | **fix (b)** | **fix (c)** | **fix (c) IM3** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| spine SP81–SP150 (C8, 15) | 1.08 | **0.96** | **0.89** | **0.96** | **0.89** | 1.18 | 1.09 | 1.09 |
| legs (C8; 15 in, 23 in for IM3) | 1.22 | 1.07 | **0.99** | **0.86** | **0.79** | 1.39 | 1.28 | 1.03 |
| top bar TB1–TB2 (C8, 15) | 1.28 | 1.13 | 1.04 | 1.02 | **0.94** | 1.38 | 1.27 | 1.15 |
| corner bond average (C6p, 15) | 2.78 | 2.41 | 2.00 | 4.30 | 4.38 | 2.34 | 1.95 | 4.41 |
| corner bond Volkersen peak (C6p, 15) | 1.19 | 1.03 | **0.85** | 1.48 | 1.37 | 1.22 | 1.01 | 1.62 |
| leg ring crush at the bushings | 2.26 | 1.99 | 1.83 | 1.67 | 1.54 | 2.78 | 2.56 | 2.15 |
| UHMWPE bushing bearing | 23.6 | 20.8 | 19.2 | 17.5 | 16.1 | 20.9 | 19.3 | 16.2 |
| buckling (≥ 1.5 × factor) | 1.85 | 1.82 | 1.84 | — | — | 1.86 | 1.84 | — |
| fatigue (FI ≤ 0.5 at 1.6 g) | 3.0 spine | 2.7 | 2.5 | 1.05 leg | **0.98 leg** | 3.3 | 3.1 | 1.26 |

**Rev B itself (a) passes, but with little margin.** The spine is at 1.08 on C8. C8 is an ultimate case, no collapse,
with factor 1.0 on the knocked-down first-ply failure. Every crown member is governed by C8: 100 % of the load on the
shoulders, and the bag couple bends the legs and spine through the lifters and the yoke.

## 4. Minimum change (task 4): crown plies + corner bondline, +22.0 g

Fix study: `fix_study()`. Plies go on the inside of the wall, so the OD stays the same and the printed sleeves, bores
and spine channel are unchanged. **No print file is touched.**

| change | Δ g | worst (b) | worst (c) | worst (b) IM3 | worst (c) IM3 |
|---|---:|---:|---:|---:|---:|
| none | 0 | 0.96 | 0.85 | 0.86 | 0.79 |
| spine +1 UD | 3.3 | 1.02 | 0.85 | 0.86 | 0.79 |
| spine +2, legs +2 | 20.9 | 0.97* | 0.81* | 1.06 | 0.98 |
| spine +2, legs +2, bar +1, corner overlap 40 mm | 25.6 | 0.97* | 0.81* | 1.12 | 1.03 |
| **spine +1, legs +2, bar +1, corner bondline 0.8 mm** | **22.0** | **1.18** | **1.01** | **1.12** | **1.03** |

\* The corner-bond peak governs here. A stiffer crown sends more moment into the corner. A longer overlap does nothing,
because the Volkersen peak saturates at ω·n_max. The peak scales with ω ∝ √(G / t_a), so the bondline is the lever.

| part | stock today | change | Δ g |
|---|---|---|---:|
| crown spine, OD 20 × 300 | [±45 / 0×4 / ±45] | +1 UD 0° (T700, 0.125 mm), wall 0.94 → 1.07 mm | +3.3 |
| crown legs, OD 16 × 430 (×2) | [±45 / 0×6 / ±45] | +2 UD 0°, wall 1.19 → 1.44 mm, ID 13.6 → 13.1 | +14.3 |
| crown top bar, OD 18 × 214 | [±45 / 0×4 / ±45] | +1 UD 0° | +2.1 |
| crown corners (×2) | MMA, 0.5 mm bondline | 0.8 mm bondline, 0.8 mm glass beads in the MMA | +2.2 |
| **total** | | | **+22.0** |

- ASSUMPTION: the vendor rolls the extra UD into the core (special-order wrap, the same as the existing legs). Check
  that the extension-post plug and the corner-wrap liner still fit the 13.1 mm leg ID.
- **T6 coupons must use the 0.8 mm bondline.** The Volkersen-peak credit is an analysis rule (HA-LS-1 §4).
- ASSUMPTION: the beam model's `bar_section` also changes the beam mid bar. The mid bar is printed in production, so
  this changes the body loads only through stiffness. The body re-run on the fixed crown is unchanged within 0.01
  (min 1.70 / 1.51 / 1.40, IM3 1.54 / 1.43).

## 5. Torso adjust, top-bar anchor, spreader

**Rack + pawl** (geometry.yaml `crown_retention`, rack 5328 N):

| | (a) | (b) | (c) | (b) IM3 | (c) IM3 |
|---|---:|---:|---:|---:|---:|
| rack SF (worst: C8, 19 in, axial 850 N) | 6.27 | 6.27 | 6.27 | 6.27 | 6.27 |
| factored pawl force on the printed cheek, y / z N (C8, 15 in) | 1913 / 850 | 2170 / 850 | 2355 / 850 | 2155 / 850 | 2339 / 850 |
| cheek (304 bushing, hole 8 mm, cheek 8 mm): 1 / FI99 | 1.57 | 1.39 | 1.29 | 1.40 | 1.30 |
| plastic bearing SF / 304 metal SF | 2.30 / 6.9 | 2.07 / 6.2 | 1.92 / 5.8 | 2.08 / 6.2 | 1.93 / 5.8 |

The fore-aft pawl load grows with the offset because the crown leans on the pawl guide. The axial load does not.

**3:1 pulley** (Euler-Eytelwein, μ 0.10):
- ASSUMPTION: wraps at A and B are 180°, the redirect at C to the cam is 90°.
- **Static carry at 1 g:** the crown's axial load is only 32–34 N in every scenario. The bag top pulls down and the
  yoke pushes up. The tail pull to shorten while worn is **17 N**.
- **Shoulder and lifter loads.** These rise with the offset, but the extra is fore-aft and goes into the bushings. The
  pulley line does not feel it.
  - Shoulder strap: 175 → 188 → 199 N.
  - Both lifters together: 201 → 224 → 240 N, at 1 g, for (a) / (b) / (c).
- **Pawl released and walking (1.6 g):** the cam hold SF is ≥ 65 and the webbing SF is > 500.
- **Hipbelt off (567 N crown at 1 g):** the cam hold SF is 6.1. The tail pull to hoist is **293 N**, above the
  ASSUMPTION 200 N one-hand limit. That is unchanged by the offset. Keep the existing instruction: do not adjust the
  torso with the hipbelt off.

**Crown top-bar anchor.** C5 at 175 mm, plus 70 N per side at 1 g. At 2.0 g × 1.5 that is 210 N per side, the
bag_top_anchor.md §7 value. All torsos.

| placement | top bar | legs | spine | corner average / peak | max pawl axial N |
|---|---:|---:|---:|---:|---:|
| ties at x ±70, −20 / 0 / +20° | 3.14 / 3.18 / 3.15 | 1.47–1.51 | 2.12–2.18 | ≥ 10.3 / ≥ 4.37 | 190 / 267 / 344 |
| guys at x ±100, −20 / 0 / +20° | 2.57 / 2.58 / 2.56 | 1.47–1.51 | 2.11–2.17 | ≥ 10.4 / ≥ 4.43 | 190 / 267 / 344 |
| crown pocket, line load over x −100…+100 | 3.63 / 3.67 / 3.73 | 1.47–1.51 | 2.12–2.18 | ≥ 10.2 / ≥ 4.35 | 190 / 267 / 344 |

- **Printed body**, C5 + anchor: 2.55 for all three placements. The crown hands the same resultant to the sleeves.
  Without the anchor it is 2.40.
- **Local ring crush of the bar** under a tie, 210 N factored. This is a point-load ring (Roark 0.318 F R / L), which
  is conservative for a strap wrapped round the bar.

  | strap width | 20 mm | 25 mm | 30 mm | 38 mm | 50 mm |
  |---|---:|---:|---:|---:|---:|
  | SF | **0.87** | 1.08 | 1.30 | 1.65 | 2.17 |

  A crown pocket (2.1 N/mm) gives **4.34**.
- **Rule for the attachment phase:** ties and guys must bear on the bar over **≥ 25 mm** of webbing, 38 mm preferred,
  or through a sleeve or a pocket. Do not use 20 mm guy straps or cord directly on the bar.
- The anchor shares the bar with the lifter lugs at x ±105. The x ±100 guys must not stack on the same 25 mm of wrap.

**Sandwich v2 spreader** (`spreader.evaluate`, 2 mm, named positions). The C5 face load scales with e / 150. The bone is
20 % of 68 kg and is part of the meat.

| meat CG mm | FPF | fatigue | sandwich local | air factored mm | air lean (sensitivity) | skin kPa | pass |
|---:|---:|---:|---:|---:|---:|---:|---|
| 150 (rev B) | 1.21 | 1.04 | 1.06 | 5.0 | +0.10 | 12.9 | yes |
| **175 (envelope)** | 1.16 | **1.003** | **1.02** | 4.8 | −0.11 | 12.9 | **yes, barely** |
| 206 (as-is, uniform) | 1.11 | **0.96** | **0.97** | 4.5 | −0.37 | 12.9 | **no** |
| 223 | 1.08 | **0.93** | **0.95** | 4.4 | −0.51 | 12.9 | **no** |

- The governing positions are the US2 corner relief (FPF) and the bone patch at the notch roots (core shear).
- The as-is combined meat CG is 181 mm (bag_top_anchor.md §3). By interpolation, fatigue there is about 0.99.
- **The spreader is the part that needs the bag-side fix:** IM3 tab B-17 + a crown-bar tie (A or G) hold the meat at
  163–174 mm. If the owner keeps the bag as-is, the spreader needs a re-sizing, for example a 7 mm core. That is not
  designed here.

## 6. HA-LS-1 rev C (DRAFT, not applied: owner decision)

**Recommendation: yes, revise.** Rev B's CG offsets come from a drafted bag shape:
- bag 180 mm from `geometry.yaml bag.cg_uniform_fill`, 148 mm drafted, + margin;
- meat 150 mm from the pack-designer's harness note.

The sewn-bag simulation, validated to 0.5 % on closed forms ([cloth_sim.md](cloth_sim.md) §2), shows the contents
lean aft:
- 206 / 223 mm as-is;
- 174–192 mm with the top anchors studied ([bag_top_anchor.md](bag_top_anchor.md) §3).

The public load-carriage literature agrees on the direction but gives no number to calibrate against:
- Army studies rank packs by "horizontal location of pack center of mass" and by "center-of-mass distance from the
  carrier's back" ([USARIEM MOLLE/SPEAR biomechanics, DTIC ADA394891][spear]; [MOLLE vs ALICE, DTIC ADA365448][molle]);
- reviews say the load CG should sit as close to the body as possible ([Knapik et al. 2004][knapik]; [DoD Ergonomics
  WG rucksack training][denix]).

No published offset value was found (search 2026-11-05). So rev C should calibrate from the sim now and from a
**measurement on the prototype** before release.

Draft changes:

| item | rev B | rev C draft | source |
|---|---|---|---|
| bag CG aft, C1–C4 and C8 | 180 mm (C8 hard-coded 180) | **205 mm**, all five cases | bag_top_anchor.md §7: candidate 1 at 15 in, 202 mm + sim scatter |
| bag CG height (C3 lateral moment) | at the attachment-node height (≈ 212 mm) | **z 550** (`LoadCase.cg_z_mm`) | cloth_sim.md §3.2 (z 542, meat) |
| meat CG aft, C5 / C7 | 150 mm | **175 mm** | bag_top_anchor.md §3 combined column, 163–181 mm |
| tall load CG, C6 / C6p | 160 mm | **185 mm** (ASSUMPTION: same +25 mm) | none in the sim: flag for T2 |
| bag couple top | crown top bar | **envelope of crown top bar AND the IM3 hooks** (`couple_top_group: strap_upper`) | cloth_sim.md §3.5: IM3 hooks carry 338–472 N per side at 1 g |
| top-anchor loads | none | when a top anchor is fitted: **70 N per side at 1 g** on the crown bar, at the anchor station, −20…+20°, in C5 | bag_top_anchor.md §4.5 |
| tie bearing on the crown bar | none | ≥ 25 mm webbing (local ring rule) | section 5 here |
| **new T9: loaded-CG measurement** | none | Load the prototype to 68 kg as T1 (fill) and as T2 (game bags), then find the CG offset two ways: hang the pack from the haul loop and from a hipbelt-pivot pin and plumb both lines (offset = their intersection to the stay plane), or use a two-scale lever on the stay feet + crown bar. Repeat at 15 / 19 / 23 in. **If the measured CG is more than 10 mm below the rev C value, the owner may relax it; if above, re-run this check** | new |
| factors, g-levels, rules | | unchanged | rev B §4 |

**Does the frame pass rev C as drafted?**

| part | as built | with the +22 g crown fix |
|---|---|---|
| printed body | yes: min 1.50 (1.53 with the IM3 couple), fatigue 1.04 | yes |
| spreader (meat 175) | yes: fatigue 1.003, sandwich local 1.02 | yes |
| rack / pawl / pulley | yes | yes |
| top-anchor loads | yes, if ties are ≥ 25 mm webbing | yes |
| carbon crown | **no**: spine 0.96 (crown couple); legs 0.86 and leg fatigue 1.05 (IM3 couple) | **yes**: min 1.12 (legs, IM3), fatigue ≥ 1.36 |

## 7. Masses of the load-path members

| member | g | basis |
|---|---:|---|
| printed branch body (2 mm raster, socket-free) | 823 | `solid_mass_g` here |
| crown legs ×2 | 73.8 → **88.1** | frame.yaml mass_g + fix |
| crown top bar | 17.9 → **20.0** | as above |
| crown spine tube | 26.0 → **29.3** | as above |
| corner wraps + adhesive (crown share) | in the 64.6 / 29.1 g frame.yaml lines; +2.2 g | |
| rack + pawl housing + pulley guides | 44.0 | sizing5200v2 |
| UHMWPE bushings ×4 | 23.0 | sizing5200v2 |
| pawl 304 bushings + cheek wall | 9.9 | production_frame.md |
| Sandwich v2 spreader, installed | 153.7 | spreader_results.json |
| **change from this check** | **+22.0** | section 4 |

- **Flag for the pack-designer.** `geometry.yaml weight` books the printed body at 774 g, from
  generative_branch_results.json at scale 1.05. The production body on the 2 mm raster is **823 g**, the same figure as
  spreader_layout.md §3. Weight roll-up is not changed here.
- **No body mass cut is recommended.** Its C8 strength margin is 1.39–1.50, but body fatigue under the IM3 couple is
  1.01–1.04. Fatigue is now what limits thinning the stays.
- **Possible later reductions of the +22 g:**
  1. If only the crown-bar couple applies (no IM3 couple), the spine ply alone (+3.3 g) clears (b). But the cloth sim
     says the IM3 hooks take most of the couple, so all four changes are recommended.
  2. If T9 measures a bag CG ≤ 190 mm, the leg plies could drop to +1 (−7 g). At 205 mm with legs +1 the IM3 case
     reaches only 0.99, so re-run at the measured CG before cutting.

## 8. Assumptions and limits

- ASSUMPTION: the beam model supplies the load path into the printed body and the crown forces, as in every production
  check. Its fixed frame is the carbon-tube frame, not the printed one. Crown forces are close to statically determinate.
- ASSUMPTION: C8 takes the bag offset. C6 / C6p take +25 mm. (c) applies 223 mm to every case.
- ASSUMPTION: CG height z 550 is applied to the C3 lateral component only. Vertical entry points keep the rev B bag
  weights (0.35 / 0.25 / 0.25 / 0.15 at z 25 / 60 / 330 / crown).
- ASSUMPTION: the IM3 variant puts the whole bag couple top on the IM3 anchors. Reality lies between the two variants;
  the table brackets it.
- ASSUMPTION: top-anchor loads are the cloth-sim ≤ 70 N per side at 1 g, scaled by g. In the beam model they add to the
  full 68 kg meat load (conservative). Elevation is swept −20…+20°.
- ASSUMPTION: pulley wraps are 180° / 180° / 90°, μ 0.10. Cam slip is 700 N (build_geometry.py). The one-hand tail pull
  limit is 200 N.
- ASSUMPTION: the pawl cheek check is linear in force, and the production detail is unchanged (304 bushing, hole 8 mm,
  cheek 8 mm).
- The spreader face load scales linearly with e (`frame_smooth.meat_normal_n`). The cinch preload is unchanged.
- The crown fix plies are T700 UD at 0.125 mm (`cfrp_t700_ud_epoxy_ply`). The bondline mass uses MMA at 1.15 g/cm³.
- Not re-run: corner-bond fatigue (bond ≤ 0.3 lap shear) and the stay-top collar. The collar is the printed sleeve now
  and is in the voxel check.

[spear]: https://apps.dtic.mil/sti/tr/pdf/ADA394891.pdf
[molle]: https://apps.dtic.mil/sti/pdfs/ADA365448.pdf
[knapik]: https://academic.oup.com/milmed/article-pdf/169/1/45/21870283/milmed.169.1.45.pdf
[denix]: https://www.denix.osd.mil/ergo-wg/training/training-rucksack/

Sources were found by web search on 2026-11-05. The DTIC PDFs returned HTTP 403 to the fetch tool, so their findings
are quoted from the search summaries, not from the full text. Confirm against the PDFs before external use.

## Screenshots

- `outputs/screens/20261105_cgrecheck_1.png`: printed-body utilization at the worst offset, (c) 223 mm.
- `outputs/screens/20261105_cgrecheck_2.png`: margin vs CG offset, 150–250 mm. Three panels: body bag cases, body meat
  cases, and the crown as built.
- `outputs/screens/20261105_cgrecheck_3.png`: printed-body utilization at the envelope (b).
