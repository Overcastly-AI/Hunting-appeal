# Whole-pack weight roll-up, version 2 (BL-013, revised by BL-023, brought up to date 2026-11-12)

Owner: pack-designer (BL-013, 2026-11-12 update); revision: manufacturing-engineer (BL-023). Date: 2026-11-12. Code: `designs/pack_5200/weight_rollup_v2.py` (tests `tests/test_weight_rollup_v2.py`); numbers: `analysis/weight_rollup_v2.json`. Every mass below is a ledger row (`huntkit.mass.ledger`, config `corrie_b2_h1`, plus the C1-C8 and H1B corrections that the ledger holds as config `corrie_b2_h1_v2`) or a row produced by the named ticket's own code, called live. CORRIE F is booked at rev 3 (the ledger's `ADOPTED_BAG`, BL-030), door D2. **Do not quote the numbers from this file after the code changes: re-run it.**

**2026-11-12 changes (everything adopted since BL-013 / BL-023, DECISIONS rows of 2026-11-12):** (1) **H1 body 757.7 -> 800.7 g** (H1-G0.55-B1/2.5), booked in the ledger as correction H1B from `analysis/h1_buckling.json`: BL-024 grow-only offset +18.8 g, BL-027 buckling members +22.2 g, BL-021 28 mm IM3 cheeks +2.0 g (as rastered into the body). (2) The separate cheek step (27 mm, +6.80 g) is gone: the 28 mm cheek is inside the H1B raster. (3) **CORRIE F rev 3** (BL-022 B-25 guy bridle and B-26 tripod keeper; BL-028 B-27 port guys inside; BL-029 / BL-030 B-29 crown lid on 20 mm B-28 crown straps in place of the 2.7 L top pouch, as hunted), door D2. (4) **Retired, booked in no scenario:** BL-017 OD 17 legs and BL-007 fixed torso (both below 1.0 on the cloth-sim loads, BL-021); the 'owner options' scenario held only the fixed torso and is dropped. Wings, hood and IM2 hooks stay deleted in after tests (owner decisions 2026-11-11 / 2026-11-12); proven now still books them, because each deletion passes only after a named test with the part as its fallback (BL-014 S1). (5) The fabric swaps stay in after tests.

## 0. Answer

| Belt M, crown kit M | base | as hunted | meat trip |
|---|---:|---:|---:|
| CORRIE B.2 on H1 (ledger start) | 3747.0 (8.26 lb) | 3919.1 | 3973.5 |
| **proven now** | **3684.7 (8.12 lb, 8 lb 2.0 oz)** | 4001.8 (8.82 lb) | 4197.8 (9.25 lb) |
| **after tests** | **3214.1 (7.09 lb, 7 lb 1.4 oz)** | 3531.2 (7.78 lb) | 3727.2 (8.22 lb) |
| target (base) | 2993.7 (6.60 lb) | | |

- **6.6 lb is not reachable with what is adopted or under test.** Proven now misses it by **691 g**, after tests by **220 g**.
- Closing the last 220 g would take deleting or moving to add-ons: IMP-2 (33 g), FP-L/R (34 g), IMP-5L (15 g), IMP-4 (24 g), IMP-6 (11 g), B-11 lash (12 g), E-5 (5 g) = 134 g. Even every unfrozen candidate (134 g) does not reach it; with the belt-foam reserve on top (166 g in all) it is still short; see section 5.
- The BL-011 headline (`corrie_f.pack_with_adopted`, rev 3: base 3292 g) is -393 g against proven now and +78 g against after tests: it takes the gated BL-005/006 items and the fabric swaps as done, leaves package C out, books the H1 body at 757.7 g and has the ledger's booking errors in it (section 2).

## 1. Rules

- **Start:** ledger `corrie_b2_h1`, belt M, every item booked: 3973.5 g. BL-008 tags (owner-adopted 2026-11-10): add-ons (top pouch / crown lid, scope pod, IMP-3 holster, rain fly) are as hunted; float links B-24 and the meat liner are meat trip. Taking the add-ons out of base is a reporting rule, not a saving; it is its own grey bar in the waterfall.
- **Proven now (P):** PASS verdicts with no open decision gate, plus every booking correction and safety addition. **After tests (A):** BL-014's rule: a change gated by a named test, where failing the test sends the part back to a known heavier part, is in A even when its fallback is known (BL-014 S1); its safety hardware (BL-010) stays in P (ASSUMPTION: conservative, settled when the gate passes). A scenario includes the one before it (P, then P + A). **Retired (R):** not adopted; in no scenario.
- DECISION: a named test that can only add mass (the H1 release tests MT-1 / CA-1 / T1 / T2, the IM3 eye pull and coupon, the lifter protractor check, HB-7 lock slip) does not move a change out of P: there is no lighter outcome to wait for. BL-014 notes that the S15 elbow-swing check does have a fallback shell (S16 / CORRIE); CORRIE F's shell is kept in P here because P_F also carries today's fabrics and every part a failed gate would restore (P_F is +29.8 g on base: moving the whole of it to A would make proven now 3654.9 g). The owner's wing removal has its own field test FT-S2 with a known fallback (the wing parts), so the wing saving (101.6 g) is in A, and P carries the wing parts. If FT-S2, PT-1 / TL-1 / LL-H were treated as first-article verification of owner decisions, proven now would be 3476.0 g.
- CORRIE F is door D2 (orchestrator call 2026-11-11), rev 3 (ledger `ADOPTED_BAG`). P uses today's fabrics on CORRIE F's pieces; A adds the swaps (owner swatch + strip test). P books the B-25 bridle even with the hood fallback (conservative, 7.4 g).

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
| H1B | proven now | BL-024/027/021 | H1 body (sleeve growth, buckling members, 28 mm IM3 cheeks) (safety) | +42.9 | +42.9 | +42.9 | MT-1 cinch, CA-1 PAHT ratio >= 0.255, T1/T2 gauges (release R1; failing adds mass, never removes) |
| BL031 | proven now | BL-031 (owner) | strap tails: lifters, sternum, stabilizers cut to length; belt tail + keepers (design) | -17.5 | -17.5 | -17.5 | T9 gloved cinch trial (TAIL_GRIP 50 mm), R-06 fit trial (sternum), HB-D1 (stabilizers) |
| P_pkgC | proven now | package C (2026-11-09) | 7075 belt plate; C-4 / C-7 rev C fixes (safety) | -8.4 | -8.4 | -8.4 | HB-5 plate, pad-seat sag test, T1(c) yoke dial (verification; the 6061 fallback fails rev C too) |
| P_F | proven now | BL-011/010/022/029/030 | CORRIE F rev 3, D2, today's fabrics; wings, 38 mm IM/US and hood kept (design) | +29.8 | +176.9 | +318.5 | first-article: S15 elbow-swing / sling check (BL-009) |
| P_d2 | proven now | BL-017 d2 | 1:1 pull strap (no 3:1 pulley) (design) | -34.6 | -34.6 | -34.6 | - |
| P_kits | proven now | BL-017 a (owner) | three crown kits, size M (design) | -27.6 | -27.6 | -27.6 | - |
| A_imus | after tests | BL-003 (a) | IM/US straps 38 -> 25 mm, 25 mm cams + rated hooks (design) | -116.0 | -116.0 | -116.0 | MT-1 / MT-2 / MT-3 at the BL-010 per-row loads; fallback 38 mm webbing, cams and hooks |
| A_att | after tests | BL-004 REC | hood + IM2 bag hooks deleted, guy toggle loops (design) | -107.1 | -107.1 | -107.1 | PT-1 / PT-2 at 2553 N, TL-1 toggle loop 366 N, LL-H heavy lock 366 N; fallback hood + IM2 hooks (owner kept them removed 2026-11-12) |
| A_back | after tests | BL-005 | sandwich backer strip (design) | -44.6 | -44.6 | -44.6 | BP-1 3-point bend coupon + BP-2 stay contact width; BP-3 back pressure below z 190 |
| A_b | after tests | BL-006 b | no belt stabilizers (design) | -18.1 | -18.1 | -18.1 | HB-D1 side-hill stability |
| A_c2 | after tests | BL-006 c2 | 0.75 mm wing stiffener (design) | -9.8 | -9.8 | -9.8 | HB-D2 wing roll-over (+ HB-1 front-strap sensor) |
| A_f | after tests | BL-006 f1+f2 | pad-seat cord tie + 1000D sleeve (design) | -12.6 | -12.6 | -12.6 | HB-D3 pad-seat retention |
| A_fab | after tests | BL-011 swaps | ULTRAGrid / 70D / ULTRA 200X fabrics (design) | -60.8 | -60.8 | -60.8 | owner swatch look (ULTRAGrid) + PT-3 and 50 mm strip test (ULTRA 200X) |
| A_wings | after tests | BL-003 (owner) | side wings deleted (design) | -101.6 | -101.6 | -101.6 | FT-S2 5 km side-hill + door open/close x 5, pod shift <= 20 mm |
| A_c17 | retired (not booked) | BL-017 c17 | OD 17 legs, 19 mm bore (design) | -20.6 | -20.6 | -20.6 | retired: body fatigue 0.97-0.99 on the cloth-sim loads (BL-021 (4)); not booked |
| O_fixed | retired (not booked) | BL-007 (a) | fixed torso instead of the kits (design) | +4.2 | +4.2 | +4.2 | retired: body fatigue below 1.0 on the cloth-sim loads (BL-021 (4)); adjustable torso kept; not booked |

### 2.1 Ledger clean-ups, each resolved against the source files (now ledger rows, BL-023)

- **C1 fairleads (49.4 g): double-booked, removed.** `frame_branch.frame_sdf` adds `bag_attach.attachment_field` (the 8 fairleads) to the body SDF, so the 823.2 g production raster and the 757.7 g H1 raster (`frame_comp_d.restore_hardpoints`, `frame_h1.md` section 4: 'bag fairleads (8) 100 % present') already hold them; 823.2 - 774.3 (study body without fairleads) = 48.9 g matches. The ledger's attachment row came from `bag_attach._mass_budget`, the added mass of the same features.
- **C2 swell patches (12.3 g): booked twice, removed.** `bag_attach` booked the 8 swells as 2-ply 200 gsm patches (ASSUMPTION there); CORRIE books the same 8 swells as cut piece B-13x (14.4 g, 'replaces the cone caps'). B-13x stays.
- **C3 crown-corner wraps: 17.6 g wraps + gussets and 6.6 g bond, unbooked, added (24.2 g).** `frame_eval.REPLACED_G` drops all of frame.yaml's 'carbon wraps + gussets' (64.6 g) and 'adhesive' as replaced by the printed body, but the two crown corners stay carbon. Their share comes from `pack5200.hardware_mass` run with and without the crown_corner joints; the rev C 0.8 mm line already booked (2.21 g) is taken off. Cross-check: `frame_light2.py` books 'crown corner wraps + 0.8 mm bondline' at 24.0 + 2.21 g.
- **C4 POM pawl housing (8.0 g): double-booked, removed.** The printed body forms the pawl housing and cheeks (`frame_branch.frame_sdf` 'pawl housing bulge'; `print/frame/PRODUCTION.md` step 2: pin through the printed cheeks in 304 sleeves, booked separately at 9.94 g). The 14 g 'pawl housing + spring + Ti pawl' row is 8 g housing + 6 g pawl and spring (`crown_diet` ASSUMPTIONs); BUILD_PLAN's 'POM housing' is from the tube frame. ASSUMPTION settled by weighing the pawl + spring.
- **C5 non-body lump: 9.1 g short, added.** `frame_mass_production.non_body_g` = generative frame_g - body_g - 202.6 g (`spreader_results.old_part_g`: QI sheet + M4 sets). frame_g held the sheet but not the M4 sets, so the lump is below its own sources: KEPT_G + pawl bushings + inserts = 226.5 g against 217.4 g. Open: the 12 g inserts ASSUMPTION also names 'rod/dowel bond, joint bolts', which H1 books separately (Ti M5 set); up to a few grams may still be double (estimate list).
- **C6 lifter keepers (6.0 g): moved attachment -> harness** (bag_attach: 'lifter backup'); no total change; the bag side gets 6 g lighter on the like-for-like split.
- **C7 IMP-3 holster tabs (2.2 g): base.** The two wing tabs stay sewn to the belt (`hipbelt_diet.holster_split`); BL-011 had the whole 38.8 g holster in as hunted.
- **C8 old 50 mm belt strap and the under-booked 25 mm 2:1 webbing: re-booked** (`hipbelt_diet.closure`, BL-006 a2): 0.9 m 50 mm strap -> two 140 mm buckle tabs; 25 mm webbing 0.6 -> 1.20 m. Net -12.7 g at M.
- **H1B H1 body (+42.9 g), a ledger correction since 2026-11-12.** `frame_mass_h1.json` still books BL-007's 757.7 g H1 raster; `ledger.h1_body_update()` reads `h1_buckling.json` `chosen` and adds three signed rows: BL-024 +18.77, BL-027 members +22.17, 28 mm IM3 cheeks +2.00 g (sum 42.93 g on the 757.7 g base; the json's own raster total is 800.66 g). The cheek is the 28 mm cheek mask minus the body it overlaps; the stand-alone fairlead volume (`loadpath_check.FROZEN`, 18 -> 28 mm, both sides) is 7.3 g, so up to the difference may be printed mass the 2 mm raster does not see (estimate list).
- **Package C was missing from BL-011's pack.** The ledger books it as config `corrie_b2_h1_c` (7075 plate -25.0 g; C-4 pad backer +8.1 g and C-7 yoke +8.5 g, both fixes for parts that fail rev C as released). It is adopted (DECISIONS 2026-11-09) and in P here.

## 3. Scenarios by belt size (crown kit M; base / as hunted / meat trip, g)

| belt | B.2 | proven now | after tests |
|---|---|---|---|
| S | 3719 / 3891 / 3946 | 3656 / 3973 / 4169 | 3189 / 3506 / 3702 |
| M | 3747 / 3919 / 3974 | 3685 / 4002 / 4198 | 3214 / 3531 / 3727 |
| L | 3771 / 3943 / 3998 | 3710 / 4027 / 4223 | 3236 / 3554 / 3750 |
| XL | 3807 / 3979 / 4034 | 3746 / 4064 / 4260 | 3271 / 3588 / 3784 |
| XXL | 3835 / 4007 / 4062 | 3776 / 4093 / 4289 | 3298 / 3615 / 3811 |

Crown kit by torso size (change against H1, g): S: kits -81.5; M: kits -62.2; L: kits -43.0. Kit S is lighter and kit L heavier than the M figures used above (today's 16 x 8 legs; the OD 17 legs are retired).

### 3.1 Base by system (belt M)

| system | B.2 base | proven now | after tests |
|---|---:|---:|---:|
| frame | 1065.7 | 1071.8 | 1071.8 |
| back | 413.6 | 413.6 | 369.0 |
| belt | 515.0 | 482.3 | 441.9 |
| harness | 223.6 | 225.1 | 225.1 |
| bag_shell | 403.0 | 412.6 | 359.5 |
| bag_pockets | 126.2 | 110.6 | 102.9 |
| pouch | 0.0 | 0.0 | 0.0 |
| fly | 5.9 | 5.9 | 5.9 |
| straps_meat | 385.6 | 399.2 | 283.3 |
| straps_compression | 243.5 | 241.5 | 140.0 |
| attachment | 321.4 | 293.6 | 186.4 |
| misc | 43.5 | 28.5 | 28.5 |

Like-for-like split (BL-001 groups, base): proven now bag side 1464 g, suspension 2193 g; after tests bag side 1078 g, suspension 2108 g.

## 4. Against the leaders (BL-008 like-for-like basis)

Leader figures and inclusions: `docs/research/published_weight_definitions.md` section 2.1 (a URL on every figure there); the basis rule per leader: `weight_configs_proposal.md` section 4.

| leader | published g | our basis | B.2 | proven now | after tests |
|---|---:|---|---:|---:|---:|
| Stone Glacier Sky 5900 + Krux, M belt | 2308 | base - hip_pocket - hydration | 3692 (+1384, +60 %) | 3629 (+1321, +57 %) | 3166 (+858, +37 %) |
| Stone Glacier Sky 5900 + Xcurve, M belt | 2396 | base - hip_pocket - hydration | 3692 (+1296, +54 %) | 3629 (+1233, +51 %) | 3166 (+770, +32 %) |
| Exo K4 5000 (bag + frame + lid) | 2637 | base + pouch - hip_pocket | 3796 (+1159, +44 %) | 3795 (+1158, +44 %) | 3325 (+688, +26 %) |
| KUIU ICON 6 6000 full kit | 2790 | base | 3747 (+957, +34 %) | 3685 (+895, +32 %) | 3214 (+424, +15 %) |
| KUIU PRO 6000 full kit (secondary) | 2639 | base | 3747 (+1108, +42 %) | 3685 (+1046, +40 %) | 3214 (+575, +22 %) |
| Mystery Ranch Beartooth 85 | 2812 | base + pouch | 3811 (+999, +36 %) | 3811 (+999, +36 %) | 3340 (+528, +19 %) |
| Mystery Ranch Metcalf 100 (secondary) | 2708 | base + pouch | 3811 (+1103, +41 %) | 3811 (+1103, +41 %) | 3340 (+632, +23 %) |
| Kifaru ARK + Absaroka | 2835 | base + holster | 3786 (+951, +34 %) | 3721 (+886, +31 %) | 3251 (+416, +15 %) |
| Seek Outside Unaweep 6300 (shipped) | 1673 | base + pouch - hip_pocket | 3796 (+2123, +127 %) | 3795 (+2122, +127 %) | 3325 (+1652, +99 %) |
| Initial Ascent IA5K | 2722 | base + pouch | 3811 (+1089, +40 %) | 3811 (+1089, +40 %) | 3340 (+618, +23 %) |

After tests, we are +416 to +858 g against the framed leaders (Seek Outside excluded: a 1.7 kg system is another class).

## 5. Is 6.6 lb (2994 g, base) reachable?

**No.** The lightest scenario is 3214 g. Gap after tests: **220 g (7.8 oz)**.

What closing it would cost in features (CORRIE F base rows; frozen features cannot be traded, RULES.md rule 9):

| item | g | what the hunter loses | owner-frozen |
|---|---:|---|---|
| US- | 105.4 | under-straps (owner-frozen) | yes |
| FP-L/R | 33.5 | hip-reach pockets (the BL-002 access fix for the sheep-load 2nd bottle) | no |
| IMP-2 | 32.6 | hydration sleeve (SG sells it separately) | no |
| IMP-4 | 23.9 | kill-kit / first-aid door pocket | no |
| IMP-5L | 15.2 | hipbelt pocket (SG, Exo, Seek sell them separately) | no |
| B-11 lash | 12.0 | lash tabs + muzzle keepers (rifle carry) | no |
| IMP-6 | 11.1 | shoulder-strap phone pocket | no |
| IMP-8 | 7.5 | bow cam / limb cup (bow carry: owner-frozen) | yes |
| E-5 | 5.4 | pole quiver (trekking pole / tripod leg carry) | no |

- Taking the largest unfrozen items first: FP-L/R, IMP-2, IMP-4, IMP-5L, B-11 lash, IMP-6, E-5 = 134 g does not reach it; all unfrozen candidates together are 134 g. With the belt-foam reserve as well, 166 g against the 220 g gap: still short.
- Not in any scenario: the belt-foam reserve (BL-006 d2 + d4, -31.9 g, gated by HB-1 and a compression-set check). On its own it does not close the gap.
- Retired, not booked: BL-007 fixed torso ((a) -86.6 g against H1 on its own, +4.2 g once the kits it replaces are undone) and the BL-017 OD 17 legs (-20.6 g). Both fall below fatigue 1.0 on the cloth-sim loads (BL-021 (4), 0.97-0.99), so neither is a lever.
- The lever the 6.6 lb target needs is on the frame side (BL-008: frame side about double the leaders'), which no open ticket reaches: after tests the suspension is 2108 g.

## 6. Estimates and uncertainty

Nothing in the roll-up has been weighed. Each row is banded by its source class. The bands are ASSUMPTIONs, settled by weighing every part of prototype 1 on a 0.1 g scale against its ledger row.

| scenario (base) | total g | typed ASSUMPTION | printed body | frame lumps / carbon | area x gsm, records | worst case | RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| proven now | 3685 | 426 +- 142 (30%) | 751 +- 42 (5%) | 514 +- 64 (10%) | 1994 +- 203 (8%) | +- 451 | +- 70 |
| after tests | 3214 | 361 +- 167 (30%) | 751 +- 42 (5%) | 514 +- 64 (10%) | 1588 +- 227 (8%) | +- 500 | +- 72 |

Single typed ASSUMPTION masses >= 5 g in after tests (base):

| row | g | band g |
|---|---:|---:|
| D2 door zip #10 in the blade | door seam, 2 sliders | 66.4 | 19.9 |
| harness: load lifters 25 mm poly + ladders, sternum Fidlock (QUICK family) + POM rails | 65.6 | 19.7 |
| misc: thread (~3 % of soft goods) + labels | 42.2 | 12.7 |
| torso adjust: 3:1 pulley webbing 25 mm x 1.4 m, metal cam buckle, pawl release cord + stra | 40.6 | 12.2 |
| IM-cams: 3 x 25 mm Al cams | 39.6 | 11.9 |
| 38 mm IM/US kept until MT-1/MT-2/MT-3 (BL-003 (a) undone): IM-hooks 3 x 25 mm rated Al G-h | 30.0 | 9.0 |
| BL-003 (a) IM/US: IM-hooks 3 x 25 mm rated Al G-hooks (right end only) | -30.0 | 9.0 |
| US-cams: US1/US2 25 mm Al cams (2) | 26.4 | 7.9 |
| 38 mm IM/US kept until MT-1/MT-2/MT-3 (BL-003 (a) undone): IM-cams 3 x 25 mm Al cams | 26.4 | 7.9 |
| BL-003 (a) IM/US: IM-cams 3 x 25 mm Al cams | -26.4 | 7.9 |
| IM-hooks: 3 x 25 mm rated Al G-hooks (right end only) | 24.0 | 7.2 |
| BL-004 REC: guy bar loops x2: 25 mm webbing x 170 mm + POM toggle | 19.0 | 5.7 |
| 38 mm IM/US kept until MT-1/MT-2/MT-3 (BL-003 (a) undone): US-cams US1/US2 25 mm Al cams ( | 17.6 | 5.3 |
| BL-003 (a) IM/US: US-cams US1/US2 25 mm Al cams (2) | -17.6 | 5.3 |
| belt B 2:1 pull: 2 x 25 mm Al D-ring (no record, ASSUMPTION 5 g, $1) | 10.0 | 3.0 |
| BL-034 thread: base ops, 11.7 g from the op stitch lengths (booked 2.0 g) | 9.7 | 2.9 |
| hood + IM2 hooks kept until PT-1/TL-1/LL-H (BL-004 REC undone): guy bar loops x2: 25 mm we | -9.5 | 2.9 |
| BL-035: rifle muzzle keepers (2, 3 mm shock cord x 309 mm + spring cord lock, through the  | 8.7 | 2.6 |
| POM pawl housing double-booked (the printed body forms the housing and its cheeks) | -8.0 | 2.4 |
| BL-022 rev 1: B-25 guy bridle on the top bar at x +/-52 | 7.4 | 2.2 |
| belt B cant snap deleted (2 POM 3-position detents, ASSUMPTION -6 g) | -6.0 | 1.8 |
| 4 hard-point loops: 25 mm webbing 0.08 m each, in the left gusset's corner seams at z 420  | 5.8 | 1.7 |
| belt B silicone-dot grip print on lumbar + wing faces (ASSUMPTION 5 g, outsourced $3) | 5.0 | 1.5 |

Other open estimates:

- IM3 fairlead cheek 28 mm: booked inside the H1B raster at 2.0 g; the stand-alone fairlead volume is 7.3 g a pair, so up to +5.3 g may be unbooked (ASSUMPTION: the raster overlap is right; settled by weighing the two printed halves against the slicer).
- H1 body on the 2 mm raster (800.7 g); BL-027's print halves (lower 310.5 g, upper 497.4 g, `h1_buckling.json` print) are +7.2 g against the raster, as BL-007's H1 mesh was heavier than its raster; the ledger keeps the raster basis for every body (ASSUMPTION MESH, h1_buckling.md; settled by weighing the printed halves).
- Risk not in any scenario: BL-010 front-strap pad pair, booked only if HB-1 fails: +42.9 g.
- Misc: thread ~3 % of soft goods + labels (ASSUMPTION in geometry.yaml). BL-035: the bag's share (15.0 g) comes out with the B.2 bag, because CORRIE F books its own thread from the op stitch lengths; the suspension share (19.2 g) and the 8 g labels stay.
- Crown kit masses are for kit M (torso 17.5-20.5 in); belt sizes S-XXL keep kit M (torso and belt are separate).

## 7. Configs added to the ledger basis (task 1)

`weight_rollup_v2.configs(size)` returns ledger-schema rows; `ledger.total / by_system / like_for_like` take them. BL-023 folded the C1-C8 corrections into `huntkit/mass/ledger.py`, and the H1 configs carry H1B since 2026-11-12 (configs `corrie_b2_today_v2`, `corrie_b2_h1_v2`, `corrie_b2_h1_c_v2`; `DEFAULT_CONFIG` = `corrie_b2_h1_v2`; the BL-001 names stay unchanged). The design configs below are still roll-up row sets; bl007_a / bl007_c are retired designs, kept for reference.

| config | total g (belt M) | bag side | suspension |
|---|---:|---:|---:|
| corrie_f_base | 3369.8 | 1078.0 | 2263.4 |
| corrie_f_as_hunted | 3686.9 | 1358.4 | 2300.0 |
| bl005_back | 3702.4 | 1485.6 | 2173.3 |
| bl006_belt | 3689.6 | 1485.6 | 2160.5 |
| bl007_a | 3660.4 | 1485.6 | 2131.3 |
| bl007_c | 3645.6 | 1485.6 | 2116.5 |

## 8. Screenshots

- `docs/screens/20261112_rollup_1.png`
- `outputs/screens/20261112_rollup_1.png`
- `outputs/screens/20261112_rollup_2.png`
