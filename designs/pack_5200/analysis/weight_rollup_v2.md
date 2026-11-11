# Whole-pack weight roll-up, version 2 (BL-013)

Owner: pack-designer. Date: 2026-11-11. Code: `designs/pack_5200/weight_rollup_v2.py` (tests `tests/test_weight_rollup_v2.py`); numbers: `analysis/weight_rollup_v2.json`. Every mass below is a ledger row (`huntkit.mass.ledger`, config `corrie_b2_h1`) or a row produced by the named ticket's own code, called live. **Do not quote the numbers from this file after the code changes: re-run it.**

## 0. Answer

| Belt M, crown kit M | base | as hunted | meat trip |
|---|---:|---:|---:|
| CORRIE B.2 on H1 (ledger start) | 3700.5 (8.16 lb) | 3872.6 | 3927.0 |
| **proven now** | **3414.4 (7.53 lb, 7 lb 8.4 oz)** | 3659.9 (8.07 lb) | 3792.0 (8.36 lb) |
| **after tests** | **3142.0 (6.93 lb, 6 lb 14.8 oz)** | 3387.5 (7.47 lb) | 3519.6 (7.76 lb) |
| **owner options** | **3144.9 (6.93 lb, 6 lb 14.9 oz)** | 3390.4 (7.47 lb) | 3522.5 (7.77 lb) |
| target (base) | 2993.7 (6.60 lb) | | |

- **6.6 lb is not reachable with what is adopted or under test.** Proven now misses it by **421 g**, after tests by **148 g**, owner options by **151 g**.
- Closing the last 151 g would take deleting or moving to add-ons: IMP-2 (33 g), FP-L/R (34 g), IMP-5L (15 g), IMP-4 (22 g), IMP-6 (11 g), B-11 lash (12 g), E-5 (5 g) = 132 g. Even every unfrozen candidate (132 g) does not reach it; only with the belt-foam reserve on top (164 g in all) does it, i.e. a pack with no pockets, no hip-reach access, no hydration sleeve and a softer belt; see section 5.
- The BL-011 headline (base 3262 g, `corrie_f.pack_with_adopted`) was -152 g against proven now and +120 g against after tests: it took the gated BL-005/006 items and the fabric swaps as done, left package C and the IM3 cheek out, and had the ledger's booking errors in it (section 2).

## 1. Rules

- **Start:** ledger `corrie_b2_h1`, belt M, every item booked: 3927.0 g. BL-008 tags (owner-adopted 2026-11-10): add-ons (top pouch, scope pod, IMP-3 holster, rain fly) are as hunted; float links B-24 and the meat liner are meat trip. Taking the add-ons out of base is a reporting rule, not a saving; it is its own grey bar in the waterfall.
- **Proven now (P):** PASS verdicts with no open decision gate, plus every booking correction and safety addition. **After tests (A):** each change has its own named test, and failing it sends the part back to a known heavier part. **Owner options (O):** needs an owner decision not yet made. A scenario includes the ones before it (P, then P + A, then P + A + O).
- DECISION: a first-article check of the whole prototype with no mass fallback (S15 elbow swing, the IM3 cheek re-run, the lifter protractor check) does not move a change out of P; it is listed in the gate column. The owner's wing removal has its own field test FT-S2 with a known fallback (the wing parts), so the wing saving (101.6 g) is in A, and P carries the wing parts. If FT-S2 were treated as first-article verification, proven now would be 3312.8 g.
- CORRIE F is door D2 (orchestrator call 2026-11-11). P uses today's fabrics on CORRIE F's pieces; A adds the swaps (owner swatch + strip test). BL-007's fixed torso is only in O, and replaces the crown kits there.

## 2. Steps (belt M; base / as hunted / meat trip deltas, g)

| # | class | ticket | change | base | as hunted | meat trip | gate (test or check) |
|---|---|---|---|---:|---:|---:|---|
| C1 | proven now | BL-004 flag | fairleads booked twice (correction) | -49.4 | -49.4 | -49.4 | - |
| C2 | proven now | BL-004 flag | swell patches booked twice (correction) | -12.3 | -12.3 | -12.3 | - |
| C3 | proven now | BL-017 flag | crown-corner wraps unbooked (correction) | +24.2 | +24.2 | +24.2 | - |
| C4 | proven now | BL-017 flag | POM pawl housing booked twice (correction) | -8.0 | -8.0 | -8.0 | weigh pawl + spring |
| C5 | proven now | BL-017 flag | non-body lump short (correction) | +9.1 | +9.1 | +9.1 | - |
| C6 | proven now | BL-004 flag | lifter keepers -> harness (correction) | +0.0 | +0.0 | +0.0 | - |
| C7 | proven now | BL-006 e | holster tabs stay on belt (correction) | +2.2 | +0.0 | +0.0 | - |
| C8 | proven now | BL-006 a2 | belt webbing re-booked (correction) | -12.7 | -12.7 | -12.7 | HB-7 (planned lock-slip test) |
| P_pkgC | proven now | package C (2026-11-09) | 7075 belt plate; C-4 / C-7 rev C fixes (safety) | -8.4 | -8.4 | -8.4 | HB-5 plate, pad-seat sag test, T1(c) yoke dial (verification; the 6061 fallback fails rev C too) |
| P_F | proven now | BL-011/003/004/010 | CORRIE F D2, today's fabrics, wing parts kept (design) | -174.1 | -98.5 | -20.8 | first-article: S15 elbow-swing / sling check (BL-009) |
| P_cheek | proven now | BL-010 A1 | IM3 fairlead cheek 25 mm (safety) | +5.3 | +5.3 | +5.3 | A1 re-run on CORRIE F loads in progress |
| P_d2 | proven now | BL-017 d2 | 1:1 pull strap (no 3:1 pulley) (design) | -34.4 | -34.4 | -34.4 | - |
| P_kits | proven now | BL-017 a (owner) | three crown kits, size M (design) | -27.6 | -27.6 | -27.6 | - |
| A_back | after tests | BL-005 | sandwich backer strip (design) | -44.6 | -44.6 | -44.6 | 3-point bend coupon + pressure-film check |
| A_b | after tests | BL-006 b | no belt stabilizers (design) | -22.4 | -22.4 | -22.4 | HB-D1 side-hill stability |
| A_c2 | after tests | BL-006 c2 | 0.75 mm wing stiffener (design) | -9.8 | -9.8 | -9.8 | HB-D2 wing roll-over (+ HB-1) |
| A_f | after tests | BL-006 f1+f2 | pad-seat cord tie + 1000D sleeve (design) | -12.6 | -12.6 | -12.6 | HB-D3 pad-seat retention |
| A_fab | after tests | BL-011 swaps | ULTRAGrid / 70D / ULTRA 200X fabrics (design) | -60.8 | -60.8 | -60.8 | owner swatch look (ULTRAGrid) + PT-3 and 50 mm strip test (ULTRA 200X) |
| A_wings | after tests | BL-003 (owner) | side wings deleted (design) | -101.6 | -101.6 | -101.6 | FT-S2 5 km side-hill, pod shift <= 20 mm |
| A_c17 | after tests | BL-017 c17 | OD 17 legs, 19 mm bore (design) | -20.6 | -20.6 | -20.6 | coupon CA-1 (body fatigue 1.150 -> lower) |
| O_fixed | owner options | BL-007 (a) | fixed torso instead of the kits (design) | +2.9 | +2.9 | +2.9 | owner (narrows universal fit) + CA-1 + per-torso fatigue restatement |

### 2.1 Ledger clean-ups, each resolved against the source files

- **C1 fairleads (49.4 g): double-booked, removed.** `frame_branch.frame_sdf` adds `bag_attach.attachment_field` (the 8 fairleads) to the body SDF, so the 823.2 g production raster and the 757.7 g H1 raster (`frame_comp_d.restore_hardpoints`, `frame_h1.md` section 4: 'bag fairleads (8) 100 % present') already hold them; 823.2 - 774.3 (study body without fairleads) = 48.9 g matches. The ledger's attachment row came from `bag_attach._mass_budget`, the added mass of the same features.
- **C2 swell patches (12.3 g): booked twice, removed.** `bag_attach` booked the 8 swells as 2-ply 200 gsm patches (ASSUMPTION there); CORRIE books the same 8 swells as cut piece B-13x (14.4 g, 'replaces the cone caps'). B-13x stays.
- **C3 crown-corner wraps: 17.6 g wraps + gussets and 6.6 g bond, unbooked, added (24.2 g).** `frame_eval.REPLACED_G` drops all of frame.yaml's 'carbon wraps + gussets' (64.6 g) and 'adhesive' as replaced by the printed body, but the two crown corners stay carbon. Their share comes from `pack5200.hardware_mass` run with and without the crown_corner joints; the rev C 0.8 mm line already booked (2.21 g) is taken off. Cross-check: `frame_light2.py` books 'crown corner wraps + 0.8 mm bondline' at 24.0 + 2.21 g.
- **C4 POM pawl housing (8.0 g): double-booked, removed.** The printed body forms the pawl housing and cheeks (`frame_branch.frame_sdf` 'pawl housing bulge'; `print/frame/PRODUCTION.md` step 2: pin through the printed cheeks in 304 sleeves, booked separately at 9.94 g). The 14 g 'pawl housing + spring + Ti pawl' row is 8 g housing + 6 g pawl and spring (`crown_diet` ASSUMPTIONs); BUILD_PLAN's 'POM housing' is from the tube frame. ASSUMPTION settled by weighing the pawl + spring.
- **C5 non-body lump: 9.1 g short, added.** `frame_mass_production.non_body_g` = generative frame_g - body_g - 202.6 g (`spreader_results.old_part_g`: QI sheet + M4 sets). frame_g held the sheet but not the M4 sets, so the lump is below its own sources: KEPT_G + pawl bushings + inserts = 226.5 g against 217.4 g. Open: the 12 g inserts ASSUMPTION also names 'rod/dowel bond, joint bolts', which H1 books separately (Ti M5 set); up to a few grams may still be double (estimate list).
- **C6 lifter keepers (6.0 g): moved attachment -> harness** (bag_attach: 'lifter backup'); no total change; the bag side gets 6 g lighter on the like-for-like split.
- **C7 IMP-3 holster tabs (2.2 g): base.** The two wing tabs stay sewn to the belt (`hipbelt_diet.holster_split`); BL-011 had the whole 38.8 g holster in as hunted.
- **C8 old 50 mm belt strap and the under-booked 25 mm 2:1 webbing: re-booked** (`hipbelt_diet.closure`, BL-006 a2): 0.9 m 50 mm strap -> two 140 mm buckle tabs; 25 mm webbing 0.6 -> 1.20 m. Net -12.7 g at M.
- **Package C was missing from BL-011's pack.** The ledger books it as config `corrie_b2_h1_c` (7075 plate -25.0 g; C-4 pad backer +8.1 g and C-7 yoke +8.5 g, both fixes for parts that fail rev C as released). It is adopted (DECISIONS 2026-11-09) and in P here.

## 3. Scenarios by belt size (crown kit M; base / as hunted / meat trip, g)

| belt | B.2 | proven now | after tests | owner options |
|---|---|---|---|---|
| S | 3673 / 3845 / 3899 | 3387 / 3632 / 3764 | 3116 / 3362 / 3494 | 3119 / 3365 / 3497 |
| M | 3700 / 3873 / 3927 | 3414 / 3660 / 3792 | 3142 / 3388 / 3520 | 3145 / 3390 / 3522 |
| L | 3725 / 3897 / 3951 | 3439 / 3684 / 3816 | 3164 / 3410 / 3542 | 3167 / 3413 / 3545 |
| XL | 3761 / 3933 / 3987 | 3475 / 3720 / 3853 | 3199 / 3444 / 3576 | 3202 / 3447 / 3579 |
| XXL | 3789 / 3961 / 4015 | 3504 / 3750 / 3882 | 3226 / 3471 / 3603 | 3229 / 3474 / 3606 |

Crown kit by torso size (change against H1, g): S: kits -81.3, with OD 17 legs -101.6; M: kits -62.0, with OD 17 legs -82.6; L: kits -42.8, with OD 17 legs -63.6. Kit S is lighter and kit L heavier than the M figures used above.

### 3.1 Base by system (belt M)

| system | B.2 base | proven now | after tests | owner options |
|---|---:|---:|---:|---:|
| frame | 1066.8 | 1035.5 | 1014.9 | 1017.8 |
| back | 413.6 | 413.6 | 369.0 | 369.0 |
| belt | 515.0 | 487.5 | 442.8 | 442.8 |
| harness | 223.6 | 238.1 | 238.1 | 238.1 |
| bag_shell | 377.0 | 381.5 | 328.4 | 328.4 |
| bag_pockets | 124.3 | 108.7 | 101.0 | 101.0 |
| pouch | 0.0 | 0.0 | 0.0 | 0.0 |
| fly | 5.9 | 5.9 | 5.9 | 5.9 |
| straps_meat | 369.6 | 266.6 | 266.6 | 266.6 |
| straps_compression | 243.5 | 264.5 | 162.9 | 162.9 |
| attachment | 317.7 | 169.0 | 169.0 | 169.0 |
| misc | 43.5 | 43.5 | 43.5 | 43.5 |

Like-for-like split (BL-001 groups, base): proven now bag side 1196 g, suspension 2175 g; after tests bag side 1034 g, suspension 2065 g; owner options bag side 1034 g, suspension 2068 g.

## 4. Against the leaders (BL-008 like-for-like basis)

Leader figures and inclusions: `docs/research/published_weight_definitions.md` section 2.1 (a URL on every figure there); the basis rule per leader: `weight_configs_proposal.md` section 4.

| leader | published g | our basis | B.2 | proven now | after tests | owner options |
|---|---:|---|---:|---:|---:|---:|
| Stone Glacier Sky 5900 + Krux, M belt | 2308 | base - hip_pocket - hydration | 3645 (+1337, +58 %) | 3359 (+1051, +46 %) | 3094 (+786, +34 %) | 3097 (+789, +34 %) |
| Stone Glacier Sky 5900 + Xcurve, M belt | 2396 | base - hip_pocket - hydration | 3645 (+1249, +52 %) | 3359 (+963, +40 %) | 3094 (+698, +29 %) | 3097 (+701, +29 %) |
| Exo K4 5000 (bag + frame + lid) | 2637 | base + pouch - hip_pocket | 3750 (+1112, +42 %) | 3454 (+816, +31 %) | 3181 (+544, +21 %) | 3184 (+547, +21 %) |
| KUIU ICON 6 6000 full kit | 2790 | base | 3700 (+910, +33 %) | 3414 (+624, +22 %) | 3142 (+352, +13 %) | 3145 (+355, +13 %) |
| KUIU PRO 6000 full kit (secondary) | 2639 | base | 3700 (+1062, +40 %) | 3414 (+775, +29 %) | 3142 (+503, +19 %) | 3145 (+506, +19 %) |
| Mystery Ranch Beartooth 85 | 2812 | base + pouch | 3765 (+953, +34 %) | 3469 (+657, +23 %) | 3196 (+384, +14 %) | 3199 (+387, +14 %) |
| Mystery Ranch Metcalf 100 (secondary) | 2708 | base + pouch | 3765 (+1057, +39 %) | 3469 (+761, +28 %) | 3196 (+488, +18 %) | 3199 (+491, +18 %) |
| Kifaru ARK + Absaroka | 2835 | base + holster | 3739 (+904, +32 %) | 3451 (+616, +22 %) | 3179 (+344, +12 %) | 3182 (+346, +12 %) |
| Seek Outside Unaweep 6300 (shipped) | 1673 | base + pouch - hip_pocket | 3750 (+2076, +124 %) | 3454 (+1780, +106 %) | 3181 (+1508, +90 %) | 3184 (+1511, +90 %) |
| Initial Ascent IA5K | 2722 | base + pouch | 3765 (+1043, +38 %) | 3469 (+747, +27 %) | 3196 (+474, +17 %) | 3199 (+477, +18 %) |

After tests, we are +344 to +786 g against the framed leaders (Seek Outside excluded: a 1.7 kg system is another class).

## 5. Is 6.6 lb (2994 g, base) reachable?

**No.** The lightest scenario is 3142 g. Gap after owner options: **151 g (5.3 oz)**.

What closing it would cost in features (CORRIE F base rows; frozen features cannot be traded, RULES.md rule 9):

| item | g | what the hunter loses | owner-frozen |
|---|---:|---|---|
| US- | 93.4 | under-straps (owner-frozen) | yes |
| FP-L/R | 33.5 | hip-reach pockets (the BL-002 access fix for the sheep-load 2nd bottle) | no |
| IMP-2 | 32.6 | hydration sleeve (SG sells it separately) | no |
| IMP-4 | 22.0 | kill-kit / first-aid door pocket | no |
| IMP-5L | 15.2 | hipbelt pocket (SG, Exo, Seek sell them separately) | no |
| B-11 lash | 12.0 | lash tabs + muzzle keepers (rifle carry) | no |
| IMP-6 | 11.1 | shoulder-strap phone pocket | no |
| IMP-8 | 7.5 | bow cam / limb cup (bow carry: owner-frozen) | yes |
| E-5 | 5.4 | pole quiver (trekking pole / tripod leg carry) | no |

- Taking the largest unfrozen items first: FP-L/R, IMP-2, IMP-4, IMP-5L, B-11 lash, IMP-6, E-5 = 132 g does not reach it; all unfrozen candidates together are 132 g. With the belt-foam reserve as well, 164 g against the 151 g gap: 6.6 lb is reached only by deleting every one of these features and softening the belt.
- Not in any scenario: the belt-foam reserve (BL-006 d2 + d4, -31.9 g, gated by HB-1 and a compression-set check). On its own it does not close the gap.
- BL-007 fixed torso does not help once the kits are in: (a) -87.7 g against H1, kits with OD 17 legs -82.6 g, and BL-007 removes a pawl housing that C4 already took out: net +2.9 g. (c) would be -14.8 g more. **Neither has been restated on the per-torso fatigue basis adopted in BL-017** (old basis (a) 1.084, (c) 1.037; H1 dropped 1.279 -> 1.150 on restatement). Scaled by the same ratio they would be 0.97 and 0.93, below 1.0; that is an estimate, not a result. The structural-fea-engineer should restate them before the owner is asked.
- The lever the 6.6 lb target needs is on the frame side (BL-008: frame side about double the leaders'), which no open ticket reaches: after tests the suspension is 2065 g.

## 6. Estimates and uncertainty

Nothing in the roll-up has been weighed. Each row is banded by its source class. The bands are ASSUMPTIONs, settled by weighing every part of prototype 1 on a 0.1 g scale against its ledger row.

| scenario (base) | total g | typed ASSUMPTION | printed body | frame lumps / carbon | area x gsm, records | worst case | RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| proven now | 3414 | 300 +- 98 (30%) | 763 +- 38 (5%) | 514 +- 64 (10%) | 1837 +- 176 (8%) | +- 376 | +- 66 |
| after tests | 3142 | 300 +- 98 (30%) | 763 +- 38 (5%) | 494 +- 66 (10%) | 1586 +- 186 (8%) | +- 389 | +- 66 |
| owner options | 3145 | 300 +- 98 (30%) | 763 +- 38 (5%) | 497 +- 84 (10%) | 1586 +- 186 (8%) | +- 407 | +- 68 |

Single typed ASSUMPTION masses >= 5 g in after tests (base):

| row | g | band g |
|---|---:|---:|
| harness: load lifters 25 mm poly + ladders, sternum Fidlock (QUICK family) + POM rails | 65.6 | 19.7 |
| misc: thread (~3 % of soft goods) + labels | 42.2 | 12.7 |
| torso adjust: 3:1 pulley webbing 25 mm x 1.4 m, metal cam buckle, pawl release cord + stra | 41.7 | 12.5 |
| D2 door zip #10 in the blade | door seam, 2 sliders | 40.4 | 12.1 |
| IM-cams: 3 x 25 mm Al cams | 39.0 | 11.7 |
| US-cams: US1/US2 25 mm Al cams (2) | 26.0 | 7.8 |
| IM-hooks: 3 x 25 mm rated Al G-hooks (right end only) | 24.0 | 7.2 |
| BL-004 REC: guy bar loops x2: 25 mm webbing x 170 mm + POM toggle | 12.1 | 3.6 |
| belt B 2:1 pull: 2 x 25 mm Al D-ring (no record, ASSUMPTION 5 g, $1) | 10.0 | 3.0 |
| POM pawl housing double-booked (the printed body forms the housing and its cheeks) | -8.0 | 2.4 |
| belt B cant snap deleted (2 POM 3-position detents, ASSUMPTION -6 g) | -6.0 | 1.8 |
| 4 hard-point loops: 25 mm webbing 0.08 m each, in the left gusset's corner seams at z 420  | 5.8 | 1.7 |
| belt B silicone-dot grip print on lumbar + wing faces (ASSUMPTION 5 g, outsourced $3) | 5.0 | 1.5 |

Other open estimates:

- IM3 fairlead cheek booked at 25 mm (+5.3 g); BL-010 row A1 is being re-run on CORRIE F loads (552 N vs 507 N, fatigue about 0.94 at 25 mm). A larger cheek adds about 0.25 g per mm a side (`loadpath_check.FROZEN`).
- Risk not in any scenario: BL-010 front-strap pad pair, booked only if HB-1 fails: +42.9 g.
- Misc (thread ~3 % of soft goods, ASSUMPTION in geometry.yaml) is kept at the B.2 figure; the lighter bag would trim it by a few grams.
- Crown kit masses are for kit M (torso 17.5-20.5 in); belt sizes S-XXL keep kit M (torso and belt are separate).

## 7. Configs added to the ledger basis (task 1)

`weight_rollup_v2.configs(size)` returns ledger-schema rows; `ledger.total / by_system / like_for_like` take them. `huntkit/mass/ledger.py` is not edited (RULES.md rule 2); folding these into `ledger.CONFIGS` is for the orchestrator.

| config | total g (belt M) | bag side | suspension |
|---|---:|---:|---:|
| corrie_f_base | 3317.1 | 1033.8 | 2239.8 |
| corrie_f_as_hunted | 3562.6 | 1242.7 | 2276.4 |
| bl005_back | 3655.9 | 1438.0 | 2174.4 |
| bl006_belt | 3643.1 | 1438.0 | 2161.6 |
| bl007_a | 3612.8 | 1438.0 | 2131.3 |
| bl007_c | 3598.0 | 1438.0 | 2116.5 |

## 8. Screenshots

- `outputs/screens/20261111_BL013_1.png`
- `outputs/screens/20261111_BL013_2.png`
