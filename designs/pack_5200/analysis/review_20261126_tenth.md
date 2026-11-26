# Tenth independent review (BL-087): B86 aluminium tube-ladder frame

Reviewer: design-reviewer, 2026-11-26. Scope: `designs/pack_5200/iter2/frame_b85/bl085.md|json`,
`huntkit/gendesign/bl085_*.py` (tees), `designs/pack_5200/iter2/frame_b86/bl086.md|json`, `print/*.stl`,
`huntkit/gendesign/bl086_*.py`, `data/materials/metals/alu_6061_t6*.yaml`, `huntkit/fea/tube_solid.py`, against
HA-LS-1 rev C (`load_standard.md`), `docs/RUBRIC.md` and review 9 (`review_20261125_ninth.md`). No design file was
edited. Units mm, N, MPa, g, USD (imperial in brackets where the owner reads it).

What I ran:
- `python -m pytest -q tests/test_bl085_tees.py tests/test_bl086_frame.py`: **18 passed** (1.9 s). The tests check the
  allowables, the wiring and the stored record. They do not check any finding below.
- I re-ran `bl086_global.evaluate` (the authors' B86 model, full rev C envelope) with an extra station band
  z 379-471 so that I could read the stay section forces between the leg-end zone and the upper tee. The global
  reproduces the record (stays 1.743, 14 cases x 3 torsos = 42 runs, C6p included).
- From the cached global (`outputs/bl086/global_b86.json`) I rebuilt the stay beam-stress profile, factored and walk,
  at every station.
- I recomputed the upper-tee fatigue rows with the beam stress at the real clamp edge. The hoop terms come from the
  record, because `kb` enters the Goodman sums additively (`bl085_tee.py:288`).
- I loaded all 10 B86 STLs with trimesh: all watertight, and their masses match the record. I recomputed the mass
  sum (2088.7 g) and the cost sums (157.42 / 148.79), and they match. I also read the B81 jig generator, the bill and
  the cut list.

## Verdict

| option | verdict | why, in one line |
|---|---|---|
| **B86** | **NOT READY for a coupon round** | The governing upper-tee fatigue row is computed with the stay beam stress at z 520 (9.7 MPa walk). The as-built clamp's lower edge is at z 430, where the walk stress is 48.2 MPa. On the record's own basis that row is **0.53-0.58**, and 0.95 even on the mean curve without fretting (B1). KF-T as specified would not load that edge (B1). A second metal contact edge, the gusset plate tip at z 170, sits in the 62-69 MPa plateau and is not checked (B2). |

"Ready after fixes" would need a **redesigned upper tee**, not a parameter tweak. The frame-wide basis that BL-085 and
BL-086 adopted (Kt 2 + fretting 0.6 at any metal clamp edge) allows a clamp edge on this stay only where the walk beam
stress is under about 30 MPa, even with zero preload mean. Here that means about z 480 and up. The stay moment comes
from the crown-leg reaction at the stay top, so it cannot be designed out. Any fix adds mass, and the frame is at 2089 g
against the 2.1 kg stop rule (DECISIONS 2026-11-26), so a fix will very likely break it. The zone-5 cost pass has
USD 1.22 of headroom, and the booked shipping box cannot hold the 12 x 12 in sheet (M4). On the DECISIONS stop rule,
the orchestrator should weigh **parking the metal track** against one more tee round.

## Blockers

**B1. The upper-tee clamp edge is checked at the wrong station: the real lower edge (z 430) carries 5x the walk beam
stress used.**
- Where: `huntkit/gendesign/bl085_tee.py:47` (shells 100 mm, top z 530, so the edge is at z 430, and the lower backer
  pair at z 430-455 clamps it); `:226` `ld = tee_loads(g, 520.0)`; `:203` reads the stay stress at the tee **node** z 520;
  `:288` `kb = Kt 2 x sb_w / 2`. Same in `bl086_report` stage `tee` (B86 rows 135-146 of `bl086.md`). ASSUMPTION GEOM-85
  (`bl085.md:226`) keeps the global's point link at z 520. Rationale `bl085.md:27`: "At z 520 the beam stress is low, so a
  clamp works".
- Failure: the stay shear is constant between z 380 and z 520 (303 N walk, static_carry | strap_upper | 23 in), so the
  moment falls linearly from 47.5 N m at z 380 to 5.2 N m at z 520. My re-run of the authors' global gives, at z 430:
  **walk 48.2 MPa** (static_carry | strap_upper | 23) and factored 90.3 MPa (drop_2p5g | strap_upper | 23). At z 520 the
  values are 9.7 / 89. Put 48.2 into the record's fatigue rows (Kt 2, Yahr design x FRET-METAL 0.6 = Sa 42.7, Goodman
  Su 290, hoop terms unchanged):

  | preload | record (z 520) | at the real edge z 430 | z 430, mean curve, no fretting |
  |---|---:|---:|---:|
  | lo (-30 %) | 1.46 | **0.58** | 1.16 |
  | nom | 1.30 | **0.55** | 1.05 |
  | hi (+30 %) | 1.16 | **0.53** | **0.95** |

  With zero preload the edge alone gives Kt 2 x 48.2 = 96 MPa (R 0) against the metal-edge R 0 allowable of 74.4: **0.77**.
  So no preload window fixes it. The static row hardly moves (90 vs 89 MPa beam, 1.03).
- KF-T (`bl085.md:179`) does not catch this either. The coupon is loaded only by the bar couple (5.8 N m), the bar push
  (253 N) and the IM3 loop. The 48 MPa at z 430 comes from the **crown-leg reaction at the stay-top bushing** (about
  300 N walk at about 100 mm), and the coupon has no leg or bushing load. So the coupon loads the governing edge at a
  fraction of 1.2 x walk.
- Fix: redesign the upper tee so that no clamped metal edge sits below about z 480-500. Then re-run the rows with
  the beam stress interpolated at **each** clamp edge, not at the bar node. Options to evaluate:
  1. a short top clamp above z ~495 with more preload area (but slip at -30 % then needs about 2x the hoop; check it);
  2. a lower edge that stays out of contact (a relieved or flared shell skirt with a measured gap) plus a polymer
     contact, with preload carried only above z ~495;
  3. a different bar load path into the stay top region that does not clamp the stressed span.

  Also give KF-T a leg offcut and bushing loaded so that the z 430 edge sees 1.2 x 48 MPa. Then model the tee in the
  global as a distributed 100 mm link (GEOM-85 retired).

**B2. The gusset-plate tip on the stay (z 170) is an unchecked metal contact edge in the 62-69 MPa plateau.**
- Where: `huntkit/gendesign/bl086_parts.py:36` (`GUSSET_Z = (68, 170)`), `:123-138` (the plates "lie on the stay
  crowns", front and back, which is the extreme fibre of the fore-aft bending), `bl086.md:25` (z 155-380 plateau about
  70 MPa). Screen `outputs/screens/20261126_bl086_1.png`: the blue spine overlays the stay up to z 170. The global
  models the gusset spine only from z 78 to 155 (`bl081_concept_b.py:343-350`), and no row looks at the plate end.
- Failure: the bolts (crush sleeve, 1.5-2.6 kN) are at z 78 / 95 only. Above them the 2.3 mm plate rests on the stay
  crown for 75 mm, and the stay strains by about +/-0.1 % at walk under it. That is a lap-plate fretting
  configuration. At the tip the walk beam stress is 62.5 MPa (z 171) to 69.1 MPa (z 155). On the frame-wide rule
  BL-085 itself applies (Kt 2, design curve x 0.6): 2 x 62.5 = 125 vs 74.4, so **0.60** (0.54 at 69 MPa); 0.91 even
  without fretting. That is the same class of detail that BL-085 called unpassable at z 330. No coupon covers it:
  KF-1 re-targeted loads only 31 MPa at z 95, and KF-P has no plates.
- Fix: stop the plates' stay contact above z ~105. Either joggle or relieve the spine by 0.5 mm, or trim the spine to
  end below z 110 and let the rung arms carry the node, or put a polymer liner under the spine above the bolts (no
  preload there, so BL-082 allows it). A polymer contact gives 1.15 x 69 = 79 vs 100.1, so **1.26**. Then add the
  plate-tip row, and put plates into KF-P.

## Major

**M1. Preload control: the K that sets the window is not tied to a thread condition, and the build notes push it out of
the window.**
`bl085_tee.py:48` (1500 N at 1.5 N m, K 0.2); `bl085_report.py:615` ("grease the screw shanks (tef-gel class)");
bill: threadlocker share; A4 screw into A4 nut (`bl086_parts.py:194` ff.). The window "every row >= 1 from 896 to
2071 N" corresponds to K 0.145-0.335 at 1.5 N m. Typical nut factors for stainless fasteners span that whole range:
anti-seize or Tef-Gel on the threads about 0.12-0.15 (over the top; static wall 0.96 at 2250 N), and dry A4-on-A4
about 0.3 and above, with galling risk (slip at about 1.0). The hand method (4 mm hex key marked at 50 mm, hanging
scale 30 N, `bl085_parts.py:320`) adds about +/-10 %. The row text still says "torque screwdriver"
(`bl085_tee.py:29,377`). CL-T measures mu x P/K together only at the low limit. Fix: specify the thread condition
(clean, dry, medium threadlocker on the threads; Tef-Gel on the shanks only, kept off the threads). Run CL-T and KF-T
in that condition, and add a high-limit preload check (for example a strain-gauged or load-washer bolt on one coupon,
or a disc-spring stack set to a gauge height). Fix the row text.

**M2. ASSUMPTION FRET-HOLE is inconsistent with the frame-wide rule. The bigger risk is that the crush sleeves cannot
be fitted as specified (review 9 m4, still open).**
- A crush-sleeved hole clamps the plate onto the tube wall around the bore, which makes it a clamped metal contact. The
  record applies 0.6 at clamp edges but not here (`bl086.md:306`). Physically the hole Kt peak and the fretting
  periphery do not coincide, so I would accept FRET-HOLE **if** a separate contact-periphery row is added. That row is
  Kt 2 x nominal x design curve x 0.6. On my numbers it passes: z 95 2 x 26 = 52 vs 74.4, so 1.43.
- The sleeve is cut 22.1 mm long, which equals the bore (`bl086_parts.py:238`, BL-085 cut list). A flat-ended
  7.94 mm sleeve meets the bore at its x-edges, where the wall-to-wall distance is 2 sqrt(11.05^2 - 3.97^2) =
  **20.62 mm**. A 22.1 mm sleeve does not fit square. A beginner will file it down until it does, and then it bears on
  two edge lines with a 0.73 mm gap at the hole on each side. The clamp then dents the wall at the governing stay hole
  (1.09). The checks also use ID 5.5 mm (`bl081_concept_b.py:67`), but 5/16 x .035 stock is ID 6.16 mm, so the
  annulus is 19.7 mm2, not 25: crush 3.75 becomes 2.95 and the column 2.34 becomes 1.83.
- Fix: saddle-cope both sleeve ends to R 11.05 with a printed coping and filing guide. Specify length 22.1 +0/-0.1 at
  the centre line, and a go/no-go gauge. Correct the sleeve ID. Make KF-1 / KF-LT use as-fitted sleeves.

**M3. The drill jigs on file put the stay holes at the failing B85 positions, and the new metal details have no jigs.**
`bl081_parts.py:224-227`: `jig_stay_foot` drills `stay_bolt_z` from `CFG0` = (105, 135) (`bl081_concept_b.py:170`), which
are the rows that fail at 0.63 / 0.81. `jig_rung_half` drills tie holes in both rungs, but B86's upper rung must have
none. Neither BL-085 nor BL-086 emits jigs for: the half-shell lengthwise saw cut, the backers (4 clamp holes + 2 bar
holes at 16 mm pitch), the upper-bar end double-shear holes, the doubler strips, or the R 13.7 x 6 mm stem notches.
Fix: regenerate the jig set from `cfg86()`, add a sawing guide for the shells and a notch template, and delete or
rename the B81 jigs so they cannot be mistaken for B86.

**M4. The cost-gate pass is inside the noise of unread lines, and the shipping box cannot hold the sheet.**
`bl085_parts.py:43-46`: one 36 x 6 x 6 in box, 10 lb dimensional. The bill includes the 12 x 12 in .090 sheet, which
does not fit a 6 x 6 in cross-section. A box that does (for example 36 x 13 x 4 in) is about 14 lb dimensional. The
zone-5 headroom is USD 1.22. Other lines that are still ASSUMPTION or secondary: SCREW-LEN (M5 x 50 / x 80 A4 at the
x 35 price; nylon-insert locknuts at the plain nut price), WASHER-PRICE, SLEEVE-PRICE, angle price (search snippet),
FedEx table (secondary) + FUEL-20, UHMWPE at USD 0 while its 43.4 g is in the mass, TPU foot pads not costed. Fix: get a
real Speedy checkout quote for the actual parcel (DECISIONS 2026-11-26 item 3) and read the fastener listings before
calling the cap. As booked, the zone-5 pass is not demonstrated.

**M5. The coupon round is neither costed nor buildable as written.**
`bl086.md:285` ("offcuts plus about USD 8 of extra tube"), BL-085 proving USD 63.55 (36 in of stay tube, 15 in of
shell). A count of the specs gives:
- KF-T 3, KF-S 3, KF-TS 3, KF-LT 3, KF-P 3, KF-1 3 and FL-D (n not stated): **about 21 fatigue coupons at 2e5 cycles**.
  At the T5 rig's ~50/min that is about 67 h each, so **about 1400 rig-hours** (about 58 days of 24/7) on one wiper-motor
  rig.
- About 7-8 m (300 in) of 1 x .065 tube.
- At least 8 shell sets (KF-T + CL-T n 5), so at least 32 in of p-4573 (about USD 48 vs 22 booked).
- 4x the backers and screws.

That puts the proving bill at roughly USD 180-220 against the USD 150 proving cap. The T5 rig is a crank and bungee
that pulls a bag. The specs need 4-point bending fixtures with an in-phase second load (KF-LT tie pull, KF-P plug push,
KF-TS a load cell), and none of these is designed, priced or drawn. Fix: cut the matrix, either n 2 on screening
coupons, or combine KF-P, KF-1 and the gusset tip into one lumbar-node coupon. Design and draw a 4-point bending
fixture and a multi-station rig, book the load cell, and re-price.

**M6. As-built geometry is still not in the global (GEOM-85).** The model has a stay of 530 mm (built 545), the tee as
a point link at z 520 (built: clamp z 430-530), and IM3 at z 520 (built: loop on the shells z 466-494, `bl085_tee.py:15`).
The IM3 move is 40 mm down. Under the HA-LS-1 4.1 rule (overturning shared in proportion to lever above the pressure
centroid z ~150), that raises the IM3 share by about 7 %, and the 1415 N IM3 hook value (cloth sim at z 520) no longer
describes the built frame. The IM3 float row is at 1.24. B1 is a direct consequence of GEOM-85. Fix: rebuild the
global on the as-built nodes, then re-run the tee, IM3 and float rows.

**M7. Hipbelt-lift / donning reversal: B86 removed the only tension path at the upper tie.** `bl086_local.py:12-15`,
`bl086_parts.py:42-57`: the upper tie is now compression-only (snap arms "positioning only"). HA-LS-1 has no case where
the post pulls away from the upper rung. But lifting a loaded pack by the belt wings, or swinging it onto a knee, is
routine field use, and B81 / B85 had a bolt there. Fix: add a handling case (for example 68 kg x 1 g lifted by the belt,
x 1.5). Show either that the lower tie and gussets carry the post-tipping couple with the upper saddle unloaded, or
that the snap arms hold it. Or the orchestrator documents it as out of scope with the owner.

## Minor

- m1 Finish (review 9 M5) is not on the B86 record. `bl086.json` has no anodise or bare note; it lives only in
  `bl085.md:217`. On the design curve every B86 fatigue row from 1.04 to 1.16 fails anodised (x 0.7). Put "stays,
  rungs, shells, backers, gussets bare 6061; no anodise" on the B86 cut list.
- m2 Lower tie "snug 0.5 N m + nylon-insert locknut" (`bl086_parts.py:283`). The locknut's own prevailing torque is of
  the same order or higher, so 0.5 N m cannot be felt. The printed saddle washer is in the bolt's clamp path (a stated
  departure from BL-082). A beginner will over-tighten it, and PAHT creeps at 40 C wet. Specify "nut down to contact,
  then 1/6 turn" with a witness mark, or put a metal sleeve through the saddle.
- m3 The mid-saddle band (1.5 N m on a 1.5 mm PAHT wall, `bl085_tee.py:53`) puts a sustained radial pressure of several
  MPa on PAHT across the layers at 40 C wet, near the wet Tg of 47 C. "Positioning only" is fine for strength, but the
  band will relax. Add a re-torque interval and a KF-S check at 40 C wet.
- m4 The PAHT creep and fatigue basis (`pa12_cf_fdm_paht.yaml`: creep_rupture_8h_40c 0.4, fatigue_1e5 0.3) is an
  ASSUMPTION with no data, on an 8 h duty, while the field duty is multi-day carry plus a permanent 150 N cinch.
  Margins are 10-26 (creep) and 2.0+ (fatigue), so this is not gating. But KF-TS / KF-P / KF-S should run conditioned
  wet at 40 C, or the PAHT rows stay unverified on the hot/wet basis they claim.
- m5 The spreader skin peak of 14.1 kPa against a limit of 14 is still labelled as passing ("(<= 14)",
  `bl081_local.py:874`; review 9 m3 is open). "Spreader supports unchanged" is not true either: the gusset spine, the
  50 mm plug head and the tie saddles all changed. Re-run `spreader.evaluate` on the B86 lands.
- m6 The hip-post stem notches (R 13.7 x 6 mm, filed, at both rung heights) have no strength or fatigue row and no
  template. The margins elsewhere on the post are large (3.44 / 6.13), but add the notched-section row.
- m7 CROWN-CLEAR (stay-top collar 15 mm higher at the 15 in torso) is still only a fit check (OV-2 b). The crown
  geometry exists, so check it in CAD now.
- m8 The record is inconsistent with itself: "Strong: PASS ... Stop rule: NOT MET ... best result; no further
  iteration" (`bl086.md:7-10`). The stop-rule outcome should read "park" or "continue", as DECISIONS defines it.
- m9 Gusset-bolt preload is 2.6 kN in `crush_rows` and the bolt rows, but 1.5 N m (about 1.5 kN) in KF-1. Pick one and
  put it on the build sheet.
- m10 The IM3 rows are labelled "z 520, loop under the upper tee", but the built loop is on the shells at z 466-494.

## Review 9 items: status

| item | status | note |
|---|---|---|
| B1 tee on the free end, parts collide | **partly closed; reopened as B1 above** | geometry fixed (15 mm tube above, interference 0), but the moved clamp edge is analysed at the old station |
| B2 band tee has no geometry | closed (by redesign) | bolted backers + double-shear bar; mid tee is a printed saddle |
| B3 preload window | **partly closed** | rows at +/-30 %, window -40 / +38 %; K is not tied to a thread condition (M1) |
| B4 mean curve, no fretting, no coupon | **partly closed** | design curve + fretting applied frame-wide; KF-T would not load the governing edge (B1); gusset tip missed (B2); FRET-HOLE (M2) |
| M1 mid tee unchecked | closed | pinned saddle 1.16 fatigue reproduced in method |
| M2 C6p skipped | closed | verified: 14 cases x 3 torsos incl. tall_load_posts |
| M3 / M4 D83 pan | closed by withdrawal | D83 out of play |
| M5 anodise routing / finish | partly closed | routed in BL-085; finish note missing from B86 (m1) |
| M6 unpriced cap pass | **partly closed** | Speedy pages read; fasteners, shipping, sleeves still secondary or ASSUMPTION; the box does not hold the sheet (M4) |
| M7 doubler leak | closed | B86 stations on t1000_065 |
| M8 socket only load path | closed | metal double-shear path, rows 1.48 / 1.68 / 4.52 |
| M9 HP-D torsion | closed by withdrawal | D83 |
| M10 CL-B torque | closed | CL-T at the low limit, KF-T at the high limit |
| m4 crush-sleeve length | **open, upgraded to M2** | |
| m3 skin pressure | **open** (m5) | |
| m5 tooling | partly closed | tubing cutter booked; torque by hand method (M1) |
| m8 PAHT creep rows | closed | rows present (basis caveat m4) |

## Checks that hold up

- Envelope coverage: all 9 crown-bar cases plus the 5 IM3-couple variants, at 15 / 19 / 23 in, C6p included. Buckling
  rule eigen / (1.5 x case factor) = 2.53. Stays 1.743 (C6p), as review 9 found.
- Design-curve arithmetic: Yahr fit / 2 at 1e5 = 71.1 MPa, which is lower than the fit at 20 N (103 MPa). R 0 Goodman
  gives 114.3 (open), 74.4 (metal edge) and 100.1 (polymer), matching `alu_6061_t6.yaml` and the tests.
- The B86 detail fixes do what they claim on the authors' model: stay holes at z 78 / 95 (walk 16 / 26 MPa at the hole
  fibre), no hole in the upper rung, the 110 mm leg bushing at 1.04, and the flared plug at 1.04. The F1 and F2
  findings (post stems overlapping the rungs by 5.2 mm, the foot-cup sleeve colliding with the plates) are real and
  fixed in the STLs.
- Polymer parts: the margins are large on the stated basis. Bearing 2.3-98, creep 10.6-26.6, fatigue 1.30-5.4 (the foot
  cup cheek is the lowest, at 1.30).
- Mass 2088.7 g (4.60 lb) and cost USD 157.42 (zone 8) / 148.79 (zone 5) recompute from the lines. The STL masses
  match. Every 6061 stock price on the metal lines was read on a Speedy page except the angle.
- Buildability, apart from M2, M3 and M5: every part is a straight cut, a jig-drilled hole, or a small PAHT-CF print
  well inside the H2S envelope. There is no welding, bonding or outsourced bending.

## What to re-run after the fixes

1. Redesign the upper tee (B1). Re-run `upper_tee_rows` with the stay stress at **each** clamp edge. Rebuild the global
   on the as-built nodes (M6). Re-specify KF-T with the stay-top bushing load.
2. Relieve or line the gusset spine above z ~105, and add the plate-tip row (B2).
3. Tie K to a thread condition and add a high-limit preload check (M1). Fix the sleeve coping, gauge and ID (M2).
   Regenerate the jigs from `cfg86` (M3).
4. Get a Speedy checkout quote for the real parcel (M4). Shrink and price the coupon matrix and the fixtures (M5).
   Add the hipbelt-lift handling case (M7).
5. Then check the 2.1 kg / USD 150 stop rule before opening any coupon purchase.
