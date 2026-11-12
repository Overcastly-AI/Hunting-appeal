# CORRIE F, the merged bag (BL-011)

pack-designer, 2026-11-11. Ticket `docs/backlog/BL-011-merged-bag.md`, updated by the DECISIONS rows of 2026-11-10 and
2026-11-11. Code: `designs/pack_5200/concepts/corrie_f.py` (concept, ledger booking, metrics, plots, result file),
`corrie_f_loadout.py` (access), `corrie_f_sim/corrie_f_sim.py` (cloth-sim loader, scenarios, R-28). Result file
`concepts/corrie_f_result.json`. Tests `tests/test_corrie_f.py`. Every mass below is a `huntkit.mass.ledger` row
(config `corrie_b2_h1`, belt M) that is kept, removed or replaced. Each replacement is cut area × record gsm, a record,
or a named ASSUMPTION. Units: g (1 oz = 28.35 g), mm (1 in = 25.4 mm), L (1 L = 61.0 cu in).

## 0. Result in short

- **Mass goal not met.** Like for like (ledger `bag_side`, every item CORRIE B.2 has, meat-trip configuration),
  **D2 saves 244.7 g and D1 saves 165.5 g** against the 350 g target. **D2 falls 105 g short.** Section 2 names the
  ingredients behind the gap. Base against base, D2 saves 336.5 g (1101.5 against 1438.0 g) and D1 saves 255.2 g.
- **CG passes.** Measured at 15 / 19 / 23 in with the add-ons fitted. Fill CG is 177.2 / 155.2 / 135.9 mm (limit
  205). Meat CG is **173.8** / 145.5 / 132.5 mm (limit 190). Adding the rounding bias gives at most 181.2 / 177.8 mm.
  The **15 in meat CG is 173.8 mm against the 180 mm acceptance**. All 9 coarse cases converged.
- **R-28 passes at 15, 19 and 23 in** (34 / 34 / 32° against > 30°), using the method fix and a **30 mm top setback**.
  The setback adds a second Z-fold in B-01 between z 631 and z 745. On S15 with these fabrics and no setback, 23 in
  reads 24° (meat) with the method fixed and 18° as originally coded.
- **Access: no pack-on misses** for hourly items on day, 6-day and sheep loads, on every belt S–XXL, with either
  door. The 2nd sheep bottle sits in FP-R. The one remaining miss with D2 is the day hunt's kill kit, which is
  not an hourly item (section 6).
- **Volume** (simulated fill) is 84.0 / 84.3 / 85.1 L, mean **84.5 L (5155 cu in)**. That is inside 85 ±3 but
  0.5 L under nominal, because the setback takes about 2 L.
- **New safety finding, not fixed (frame part):** the IM3 bag-hook force at 1 g is **552 N at 15 in meat**,
  against the 507 N basis BL-010 used to size the 25 mm IM3 fairlead cheek. On BL-010's own numbers, cheek fatigue
  becomes 834.5 / (1.6 × 552.4) = **0.94** (it was 1.03). See section 5.3.
- **Doors:** both are complete. D2 is lighter, has fewer pieces and fewer hours. D1 opens 60–70 mm wider. The owner chooses (section 3).

- **Rev 1 (BL-022, section 12):** fine-mesh R-28 is 34° at 15 / 19 / 23 in (the frame-only limit), so the 30 mm setback stays; guys moved to x ±52 on a B-25 bridle, clear of the lifters at every crown kit; B-26 tripod keeper; guys-off 15 in meat CG 201.7 mm (over rev C: "GUYS ON" carry rule); +8.6 g (D2).

Screens: `outputs/screens/20261111_BL011_1.png` (mass), `_2.png` (doors and setback), `_3.png` (CG and R-28).

## 1. What CORRIE F is (ingredients)

| Ingredient | Source | In CORRIE F | Note |
|---|---|---|---|
| Shell | BL-009 S15 | yes, plus a 30 mm top setback | 394 mm full width, tapering to 360 mm at the collar seam (z 745). Depth 160 / 205 mm. The aft face is unchanged. The frame face steps aft 30 mm from z 631 to z 745, so the gusset top depth goes 195 → 165 mm. No curved seam is added. |
| Fabrics | team B (FELL) | yes | ULTRAGrid 210D for gussets, door / lid, hinge band and hem. 70D ripstop collar B-06. ULTRA 200X floor. B-01 and B-06f stay ULTRA 200. Camo accents are 630D printable (O-6: wear zones). Gates are in section 4. |
| Straps | BL-003 REC | yes | IM1–IM3 and US1/US2 at 25 mm with 25 mm cams. The IM left end is a sewn loop girth-hitched on the eye. No wings: W1–W3 are the only external set (owner, 2026-11-11). |
| Attachment | BL-004 REC | yes | No hood B-19, no ladders B-20, no IM2 bag hooks. Guy loops with toggles on the top bar. B-17 is 70 mm. "Guys on" is a carry rule (bright toggle + hang-tag). |
| Hardware | BL-010 | yes | 22 g wiregate carabiners at the IM3 bag hooks, the IM3 meat free end and B-24. Rated 25 mm G-hooks + heavy ladder locks on W1–W3. Heavy ladder locks on the guys. The 25 mm IM3 fairlead cheek is a frame part. Only BL-010's PASS / PASS-after-test rows are used; the gated rows are listed in section 8. |
| Door | team C (D1), team E (D2) | both, owner picks | Section 3 |
| Hip-reach pockets | team A E-4 / E-5 | yes | The same part (`evolve.FP`), moved from the deleted wings to each gusset's lower front corner (z 150–380). Pole quiver in FP-R. |
| Strap pocket | IMP-6 (harness) | yes, unchanged | IMP-6 is the shoulder-strap phone pocket. Snacks and GPS go in FP-L, so no second strap pocket is needed (the loadout check confirms this on S–XXL). |
| 2nd bottle (sheep) | team A | yes | FP-R |
| Meat liner | team D SWAP slab | yes, meat-trip add-on | 61.7 g |
| Look | team E rule | yes | D2: the camo blade carries the door zip. D1: camo storm flaps sit on the zip legs in the corner seams. Either way, panel line = camo break = zip. |
| Scope pod | team B A1 glass pod | yes, as-hunted add-on, **left gusset** | Hangs from 4 hard points at z 420 / 640, above FP-L |
| Tripod straps | team B A2 | **dropped** | Reason: the owner made W1–W3 the only external strap set (DECISIONS 2026-11-11). BL-010 row S10 passes W1/W2 for side carry. The tripod rides under W1/W2 on the right gusset, feet on FP-R's top edge. This saves 32.2 g and 4 loops. |
| Top pouch | team B A3 lid pod | yes, as-hunted add-on | 2.7 L, ULTRAGrid / 70D. The straps are booked in `straps_compression`. |
| Float kit | B-24 | yes, meat trip | carabiners per BL-010 |
| Bottle holster | IMP-3 (belt) | as-hunted | ledger `belt`; outside bag side |

## 2. Mass on the ledger basis (belt M)

Configurations follow BL-008's rule (`weight_configs_proposal.md`). **Base** is everything sewn or pinned plus meat
carry and compression. **As hunted** adds the top pouch and its straps, the scope pod and the fly (F-02 stays in base).
**Meat trip** adds B-24 and the meat liner. CORRIE B.2 is tagged by the same rule (`corrie_f.corrie_b2_rows`), and
its bag-side rows reconcile to the ledger's 1625.7 g within rounding (test).

| Bag side, g (oz) | CORRIE B.2 | CORRIE F · D1 | CORRIE F · D2 |
|---|---:|---:|---:|
| Base | 1438.0 (50.7) | 1182.8 (41.7) | **1101.5 (38.9)** |
| As hunted | 1571.2 (55.4) | 1389.6 (49.0) | **1310.4 (46.2)** |
| Meat trip (everything) | 1625.6 (57.3) | 1521.8 (53.7) | **1442.6 (50.9)** |
| Meat trip without the meat liner (like for like: CORRIE B.2 has no liner) | 1625.6 | 1460.1 | **1380.9** |
| **Saving, like for like (target ≥ 350)** | – | **165.5** | **244.7** |
| Same, today's fabrics (if the owner declines the swaps): base / as hunted / meat trip | – | 1249.1 / 1455.9 / 1588.1 | 1162.3 / 1371.2 / 1503.4 |

By system, meat trip (g): CORRIE B.2 → D2 (D1)

| System | CORRIE B.2 | D2 | D1 | What moved |
|---|---:|---:|---:|---|
| bag_shell | 377.0 | 328.4 | 351.5 | B fabrics (−61 g against today's fabrics) on the larger S15 area. The D2 camo blade U is 32.0 g of 630D. D1 adds flaps, boots and 6 lid-strap loops. |
| bag_pockets | 124.3 | 246.4 | 246.4 | IMP-1 (54.5) out. Scope pod 83.7, FP-L/R 33.5, quiver 5.4 and meat liner 61.7 in. IMP-2 in 70D is −7.7. |
| pouch | 39.6 | 29.7 | 29.7 | lid pod in ULTRAGrid / 70D |
| fly | 74.9 | 76.8 | 74.6 | F-01 re-cut to the larger outer shell (G-2 rule) |
| straps_meat | 424.0 | 337.1 | 337.1 | BL-003 REC, plus BL-010 +14 (IM3 free end) and +16 (B-24) |
| straps_compression | 268.1 | 187.5 | 245.8 | wings deleted; BL-010 +21 (W1–W3). D1 adds the H1–H3 lid straps (58.2) |
| attachment | 317.7 | 236.7 | 236.7 | BL-004 REC −103.0, BL-010 +16 (IM3 carabiners), heavy guy locks +6 |

**Why the goal is missed (D2, 105 g short).** The 350 g target assumed the raw savings of BL-003 (218.5), BL-004
(103.0) and team B's fabrics. These ingredients gave some of it back:

| Ingredient | g | Status |
|---|---:|---|
| BL-010 load-path fixes (IM3 free end 14, W1–W3 21, B-24 16, IM3 bag hooks 16, guy locks 6) | +73 | safety. Not negotiable. |
| Team A hip-reach pockets + pole quiver (ticket's access requirement; they fix the sheep bottle) | +38.9 | required |
| Scope pod as a hook-on add-on instead of the sewn IMP-1 sleeve | +29.2 | owner option: a sewn IMP-1 on the left gusset (team C's way) saves 29.2 g but goes into base weight |
| S15's larger cut area (full-width base, 394 mm floor) eats much of the fabric saving: the shell in today's fabrics is about CORRIE B.2's mass | ≈ +0 net on the shell | BL-009 chose S15 for CG |
| Fly re-cut to the larger shell | +1.9 | |

Without the BL-010 fixes D2 would save about 318 g; with a sewn IMP-1 as well, about 347 g. **No honest path gets to
350 g without trading access or safety.** An owner option that does reach it: **D1-lite**, where W1–W3 replace the
H1–H3 lid straps (W1–W3 already cross the lid at z 80 / 250 / 420). That makes D1 58.2 g lighter (saving 224 g),
still below D2.

**Pack on H1, belt M (D2):** 3364.0 g base / 3611.7 g as hunted / 3743.9 g meat trip (7.42 / 7.96 / 8.25 lb), with
suspension and misc as the ledger books them today. BL-013 has not rolled up the adopted suspension packages. With
them, read from their own code (`corrie_f.pack_with_adopted`: hipbelt B diet −57.4 g, BL-006; sandwich backer −44.6
g, BL-005): **3261.9 / 3509.6 / 3641.8 g (7.19 / 7.74 / 8.03 lb)**. The crown kits (BL-017) are not included: their
mass waits for CA-1. The 6.6 lb (2994 g) base target is still 268 g away.

## 3. Door options

| | D1: team C full-face tailgate | D2: team E camo-blade door on S15 |
|---|---|---|
| What | The lid is the whole aft face, sewn to the floor (hinge = floor seam). #10 zip legs run in the aft corner seams from the floor to z 590, with R 60 arcs and a top run under the hinge band at z 650 (2 sliders). Lid straps H1–H3 sit at z 190 / 330 / 520 (25 mm, G-hook + ladder lock, loops 15 mm forward of the zip). Camo storm flaps cover the zip legs. | The door is the aft face between two flat camo blades, z 110–650, with R 55 corners. The blades run 40 mm wide at the floor to 25 mm at the collar seam, beside each corner seam. Blades and the 75 mm kick strip are one camo piece (B-02u). The zip runs in the blade \| door seam (2 sliders). |
| Body-group mass (bag_shell) | 351.5 g | 328.4 g |
| Bag side, meat trip | 1521.8 g | 1442.6 g |
| Door zip | 1584 mm | 1358 mm |
| Clear width IM1 / IM2 / IM3 (less 2 × 9 mm chain) | **376 / 376 / 376 mm** | 302 / 308 / 316 mm |
| CORRIE B.2 / team A, same rule | 196 / 224 / 263; A 294 / 311 / 334 | |
| Floor access | from the floor (the lid drops) | sill at z 110, kick strip below |
| Pieces (base / with add-ons) | 40 / 53 | 35 / 48 |
| Curved seams | 1 (the zip run with its two R 60 arcs) | 1 (door zip with R 55 corners) |
| Beginner hours (base / with add-ons / CORRIE B.2 basis) | 28.6 / 39.1 / 34.9 h | 27.2 / 37.7 / 33.5 h (B.2 35.6 h) |
| Procedure | unhook W1–W3, open the H1–H3 cams, unzip, lid down. Closing: **cinch H1–H3 first, then zip** (the slider never pulls a loaded chain) | unhook W1–W3, unzip |
| Access result | no misses on any loadout or belt | no hourly misses; the day hunt's kill kit packs below the sill (half point in the BL-002 scoring) |
| Risks | the lid drops into the dirt; 3 more cams to handle gloved | zip beside a 630D blade on a square corner (E's sat on a fold); narrower than A at IM3 |

**Headline door: D2** (`corrie_f.DOOR_DEFAULT`), because it is lighter, quicker to build and meets team A's width at
IM1. The owner decides. If D1 is chosen, consider D1-lite (section 2).

## 4. Pieces list (body group, D2; D1 differences after)

| Id | Piece | Material (record) | g | Gate / note |
|---|---|---|---:|---|
| B-01 | frame-side panel, flat, **two Z-folds** (30 mm head setback z 560–631, 30 mm top setback z 631–745) | challenge_ultra_200 | 40.96 | frame interface unchanged |
| B-03 ×2 | side gusset (frame edge follows both setbacks) | ultragrid_210d_uhmwpe_ripstop | 42.14 | O-4: owner sees a swatch |
| B-05 | floor 394 × 160 | challenge_ultra_200 (ULTRA 200X) | 10.22 | O-5: PT-3 + 50 mm strip test (≥ 36.8 N/mm) |
| B-02u | camo blade U (blades + kick strip) | polyester_ht_630d_printable | 31.96 | carries the door zip |
| B-02door | door z 110–650 | ULTRAGrid | 25.72 | O-4 |
| B-02h | hinge band z 650 → collar seam (B-22 guy tabs at x ±149, z 695) | ULTRAGrid | 5.46 | O-4 |
| SH-07 | slider garage | camo 630D | 1.23 | |
| SH-01b ×2 | gusset kick bands | camo 630D | 8.78 | |
| B-06f | collar, frame side | challenge_ultra_200 | 26.50 | |
| B-06 | collar | nylon_ripstop_70d | 34.06 | O-3: weigh the stock |
| B-07 / B-07s | roll-top hem / HDPE strip ×2 | ULTRAGrid / hdpe_sheet | 13.32 / 14.82 | |
| zip | #10 coil 1358 mm, 2 sliders, 2 cord pulls | coil_zipper_10 | 40.36 + 3.00 | |
| loops | 4 hard points 25 × 80 mm, left gusset corners at z 420 / 640 | poly_webbing_25mm | 5.76 | scope pod |
| B-11, bow carry | lash tabs, riser loops | ledger rows | 24.10 | owner freeze |
| B-13x | boxed fairlead swells | ledger attachment row | 14.39 | unchanged |

D1 instead of B-02u / B-02door / B-02h / SH-07: B-02L lid 35.18, B-02h hinge band with corner tongues 6.69, SH-07
1.65, SH-10 zip-foot boots 0.98, SH-09 camo storm flaps 16.98, SH-11 top-run flap 1.91, SH-01a V-notch kick 8.80, zip
1584 mm 44.89, 6 lid-strap loops 10.80, plus H1–H3 straps 3 × 19.41 (`straps_compression`).

Pockets (base): IMP-2 hydration sleeve, 70D tube, 32.6 g. IMP-4 kill-kit pocket inside the D2 door (D1: inside the
lid), 22.0 g. IMP-8 bow cam cup at the right gusset foot, 7.5 g. FP-L / FP-R hip-reach pockets, 33.5 g. Pole quiver,
5.4 g. Add-ons: scope pod 83.7 g, top pouch 29.7 g + straps 24.6 g, meat liner 61.7 g, fly F-01 55.1 g + hem 15.8 g;
F-02 base pocket 5.9 g in base.

## 5. Cloth sims (`corrie_f_sim.py`, coarse h 40 mm, one run at a time)

Scenarios `corrie_f_sim/cf_PR{15,19,23}.yaml` extend CORRIE's converged `corrie_PR{t}c`. They use BL-004 REC
attachment (no hood, IM3 hooks only, guys round the bar). Team B's fabrics are modelled the way FELL modelled them:
ULTRAGrid on the 330D model ×1.30 / 1.375 stiffness and ×0.733 areal, 70D on the Robic model, the ULTRA 200X floor
set by the loader, and the camo blade at 290/180 areal. The S15 shell and top setback are swapped in at run time
(huntkit not edited). Add-ons fitted: top pouch with 1 kg of goods (1.054 kg) on the roll, and the 85 mm spotter in the scope pod (1.994 kg) on the
left gusset at z 400–640. The tripod and the FP contents are not in the sim, as for CORRIE B.2. Those items sit
forward, so leaving them out is conservative for the CG. ASSUMPTION DOOR-SIM: the closed door is modelled on
CORRIE's cut lines for both options (team C's sim: a closed zip carries ≤ 0.45 N/mm).

### 5.1 CG and volume (mass-weighted with the add-ons; bias = 4 mm × rounding / 6, BL-002)

| Torso | Fill CG y (rounding) | + bias | Meat CG y (rounding) | + bias | Fill L (cu in) | Worst seam |
|---|---:|---:|---:|---:|---:|---|
| 15 in | 177.2 (6 mm) | 181.2 | **173.8** (6 mm) | 177.8 | 84.0 (5126) | B-01 \| B-05 1.93 N/mm, SF 14.2 |
| 19 in | 155.2 (6) | 159.2 | 145.5 (6) | 149.5 | 84.3 (5146) | B-01 \| B-05 2.24, SF 12.2 |
| 23 in | 135.9 (4) | 138.6 | 132.5 (2) | 133.8 | 85.1 (5196) | B-01 \| B-05 2.02, SF 13.6 |

Limits are rev C: fill ≤ 205 mm, meat ≤ 190 mm. All cases converged. CORRIE B.2 at 15 in reads 191.3 / 184.4 mm. S15
on CORRIE fabrics with REC reads 178.4 / 171.0 mm. The worst seam load (2.24 N/mm) is about twice S15 on CORRIE
fabrics (1.05). The softer ULTRAGrid / ULTRA 200X models carry more of the hoop into the B-01 | B-05 seam. The SF
stays ≥ 12.

### 5.2 R-28 head clearance and the method fix

`huntkit/gendesign/attach_system.py` `r28_loaded` gains an optional `design_face=[(z, y), ...]`. When it is given,
the wall is the caller's own drafted face minus the simulated move, which equals the loaded face. When it is left
out, the function behaves as before (SPINE's `build_geometry.y_frame` for every shell). This is the bug BL-010 found at
line 158. A test checks that the default is unchanged and that the caller's face is used. With the fix, BL-004's
REC_S15_PR23 reproduces BL-010's corrected 28 / 25° (fill / meat).

| Run (23 in) | as coded (old) | method fixed | wall toward the head above the bar |
|---|---:|---:|---:|
| F0 = S15 + B fabrics, no setback | 21 / 18° | **27 / 24° FAIL** | 51 / 57 mm |
| **F = CORRIE F (30 mm top setback)** | 13 / 13° | **33 / 32° pass** | 67 / 67 mm (measured from the set-back face) |
| F at 15 in / 19 in | 34 / 34° and 30 / 24° | 34 / 34° and 34 / 34° pass | 5–9 / 32–45 mm |

The setback is a bag feature, active at every torso. At 23 in the crown bar is at z 804, so only about 260 mm of bag
sits above it. That part of the bag is now drafted 30 mm further aft and is 30 mm shallower at the collar seam.
Cost: about 2 L of volume (F0 fill 87.2 L → F 85.1 L at 23 in). The CG gets better rather than worse (less volume
up high and aft). The ticket suggested putting it "on the L crown kit". A bag-side step does the same job on every
kit and needs no frame part. The margin is 2–3°: protractor check at the L crown kit on the first prototype.

### 5.3 Attachment loads at 1 g (new finding)

| Torso / case | IM3 bag hook max (R/L) | Guy max | Hinge max |
|---|---:|---:|---:|
| 15 meat | **552 N** | 40 N | (sim) |
| 19 meat | 516 N | 49 N | |
| 23 meat | 460 N | 52 N | |
| 19 fill | 364 N | 80 N | |

BL-010 sized the 25 mm IM3 fairlead cheek on 507 N at 1 g (S15 REC, CORRIE fabrics, scope at z 165–595), with
fatigue 1.03. On CORRIE F the force is 552 N at 15 in. Pro rata, fatigue is **0.94 at 15 in and 1.01 at 19 in**. The
carabiner (minor-axis proof 4000 N) and the B-17 seam keep their margins. Likely causes: the lighter, softer B fabrics,
the scope pod moved up to z 400–640, and the setback. **For the structural-fea-engineer:** re-run BL-010 row A1
fatigue on these forces (`outputs/clothsim/corrie_f/F_PR15/results.json`). The likely fix is the frame-side cheek, a
few mm taller. Not fixed here (frame part, outside scope).

### 5.4 Fine drape

Not run. Renders are BL-012 (out of scope), and the coarse runs carry every number. `corrie_f_sim.py fine --torso
19` produces the packed fine drape when BL-012 needs it.

## 6. Access (`corrie_f_loadout.py`, corrie_loadout model, add-ons fitted)

Belts S, M, L, XL, XXL × day / elk 6-day / sheep 8-day × rifle (and archery where the loadout has it) × D1 / D2.
Peels come from CORRIE F's own sims (fill 52.6 / 31.0 / 12.8 mm; meat 51.8 / 24.5 / 11.7 mm).

| | Day | Elk 6-day | Sheep 8-day |
|---|---|---|---|
| Hourly misses, every belt, D1 | 0 | 0 | **0** |
| Hourly misses, every belt, D2 | 0 | 0 | **0** |
| Any miss, belt M, D1 | none | none | none |
| Any miss, belt M, D2 | kill kit (class 5: it packs below the D2 sill; CORRIE B.2's IMP-4 packing-order artefact) | none | none |

Where the hourly items go: phone in IMP-6, inReach on the strap clip, GPS and snacks in FP-L, bottle 1 in the IMP-3
holster, **bottle 2 in FP-R**, poles in the quiver, spotter in the scope pod, tripod under W1/W2. Worst geometric 15
in CG with the peel: 166.1 mm loaded, 144.9 mm pack-out.

## 7. Build metrics (`bag_concepts.metrics` HOURS model, as every competition entry)

| | CORRIE B.2 | D1 | D2 |
|---|---:|---:|---:|
| Pieces, B.2 basis (body + pouch + IMP pockets / pod) | 42 | 46 | 41 |
| Curved seams | 1 | 1 | 1 |
| Body seam length | – | 7.61 m | 9.02 m |
| Zip total with the pouch | 1514 mm | 1844 mm | 1618 mm |
| Beginner hours, B.2 basis | 35.6 | 34.9 | 33.5 |
| Beginner hours, everything incl. liner and fly (ASSUMPTION fly 1.0 h, F-02 0.3 h) | – | 39.1 | 37.7 |

## 8. Gates and prototype tests

| Gate | Settles | Source |
|---|---|---|
| Owner sees the ULTRAGrid swatch (O-4) | body fabric | fabric_swap_evidence.md |
| PT-3 + 50 mm strip test on ULTRA 200X, ≥ 36.8 N/mm (O-5) | floor | same |
| Weigh the 70D stock (O-3) | collar | same |
| **A1 re-check at 552 N (IM3 fairlead cheek fatigue 0.94)** | frame cheek | section 5.3 |
| BL-010 PASS-after-test rows: MT-1, MT-3, SEW-F, IM2 notch fit, LL-slip and LL-slip heavy, W-pull, IM3 eye pull, PT-1 at 2553 N, PT-2 on the 70 mm tab, PT-3 hinge eye, toggle-loop pull 366 N | straps, hooks, guys | loadpath_verification.md |
| 15 in plumb-line CG test, 30 kg on IM1–IM3 | CG bias, DOOR-SIM | BL-002 |
| R-28 protractor check at the L crown kit (23 in), loaded | top setback | section 5.2 |
| EV-3 reach test of FP-L / FP-R on the S15 gusset (S/M/L testers, loaded, gloved) | hip-reach ASSUMPTION | team A, section 6 |
| BL-009 elbow-swing and rifle-sling check (S15 is 16–17 in wide loaded) | shell width | shell_sweep.md |
| FT-S2 5 km side-hill (tripod and spotter shift ≤ 20 mm under W1/W2, no wings) | wing deletion, tripod carry | DECISIONS 2026-11-11 |
| Right-gusset fit: FP-R + tripod under W1/W2 + IMP-8 bow cam cup | layout | section 1 |
| D1 only: close with H1–H3 first, then zip, 10 cycles loaded | procedure | team C |
| D2 only: zip run beside the 630D blade on a square corner, 10 open/close cycles loaded | zip seam | team E risk |

## 9. What the pattern-maker needs

1. Shell S15 flat pieces from `corrie_f.build()` / `shell_sweep.flat_dims` with the **second B-01 Z-fold** (30 mm, z 631 → 745). The gusset frame edge follows it, so the gusset gets one more frame-edge kink.
2. Floor 394 × 160 (full S15 width), not CORRIE's 272.
3. The chosen door. D2: blade U as one piece (blades 40 → 25 mm wide, plus the 75 mm kick strip), door with R 55 corners, hinge band; zip 1358 mm with the notch at each corner tangent. D1: lid with R 60 top corners and 3 mm ease a side, hinge band with corner tongues, storm flaps, boots, 6 loop positions.
4. Notches for the 4 scope-pod hard points (left corner seams, z 420 / 640) and the pole-grip tab (right B-01 | gusset, z 640).
5. FP-L / FP-R placement on the gusset lower front corner (z 150–380), mouth band, pleat folds; the IMP-8 cup below on the right.
6. IMP-4 inside the D2 door (or the D1 lid), IMP-2 in the 70D tube.
7. B-22 guy tab and guy bar-loop lengths per BL-004. B-17 is cut 90 × 70.
8. Fly F-01 re-cut to the CORRIE F outer shell (area from `corrie_f.fly_rows`).
9. Add-on patterns: scope pod (team B A1), lid pod (A3), meat liner (team D SWAP slab).

## 10. Assumptions that govern

- ASSUMPTION DOOR-SIM: one sim serves both doors (closed zip ≤ 0.45 N/mm). Settled by the 15 in plumb-line CG test on the chosen door.
- ASSUMPTION CAMO-K: the camo blade U keeps the 330D stiffness model, with mass scaled. Settled by the same CG test plus a seam strain check.
- Fabric models scaled from records (team B's method). Settled by the prototype volume and the CG test.
- Side carry under W1/W2 = 6 L, class 3, as a wing (corrie_loadout). Settled by FT-S2.
- FP reach (team A EV-3). Settled by the EV-3 reach test.
- Hours: fly 1.0 h and F-02 0.3 h added to the HOURS model. Settled by timing the first build.
- Fly hem length unchanged within 5 %. Settled by cutting the first fly.
- `G_HOOK` 4 g on add-on straps only (no load path).

## 11. Found, not fixed

- IM3 bag-hook force 552 N > the 507 N BL-010 basis; cheek fatigue 0.94 (section 5.3; frame, structural-fea-engineer).
- `pack_with_adopted` books IMP-3 as a whole as-hunted row (BL-008), whereas BL-006 keeps 2.16 g of wing tabs in base. Ledger detail for BL-013.
- The like-for-like comparison still includes BL-004's ledger flags: fairleads possibly double-booked (49.4 g) and swell patches booked twice. If BL-013 confirms them, both packs drop equally.

## 12. CORRIE F rev 1 (BL-022)

pack-designer, 2026-11-12. Ticket `docs/backlog/BL-022-r28-guys-sidecarry.md` (review BL-014 items B3, S6, S7, S11).
Code: `corrie_f.py` (`REVS`, `revision(n)`, `guy_lifter_check`, `guy_geometry`, `guy_bridle`, `tripod_keeper`,
`top_bar_guy_moment`, `bl022_table`, `bl022_summary`; CLI `python designs/pack_5200/concepts/corrie_f.py --bl022`),
`corrie_f_sim/corrie_f_sim.py` (`finerun`, `--guys`, `--smooth`, `r28sweep`), stored rows
`corrie_f_sim/corrie_f_sim_results.json`, sweep `corrie_f_sim/corrie_f_r28_sweep.json`. Rev 0 (BL-011, sections 0–11)
stays reproducible with `with corrie_f.revision(0):`. Owner decision 2026-11-12: the hood and the IM2 bag hooks stay
removed, so every R-28 run here is hood-off.

**Rev 1 in one line:** top setback unchanged at 30 mm (the fine mesh does not need more), guys moved inboard to
x ±52 on a B-25 bridle (clear of the lifter lugs), and a B-26 shock-cord tripod keeper. +8.6 g (D2) / +9.7 g (D1)
on the ledger basis (belt M: D2 1442.5 → 1451.1 g, D1 1521.7 → 1531.4 g, `corrie_f.parts`).

### 12.1 R-28 on the fine mesh (B3)

Rev 1 runs at h 25 mm (fill and meat, all converged) at 15, 19 and 23 in. The wall is measured from the fine
mesh's own drafted face (`drafted_face(..., fine=True)`), so the wall in `r28_loaded(..., design_face=...)` is the
fine loaded face itself.

| Torso | rev 0 coarse | rev 0 fine | rev 1 coarse | **rev 1 fine** |
|---|---:|---:|---:|---:|
| 15 in | 34° | not run | 32° | **34°** |
| 19 in | 34° | not run | 34° | **34°** |
| 23 in | 32° | 34° | 34° | **34°** |

(worst of fill / meat, wall allowance `R28_ALLOW` 3 mm as coded). **Target ≥ 31° met at all three torsos on the
fine mesh, so the setback stays at 30 mm. Volume, CG and access do not change because of R-28.**

Why the review's 30° did not happen: R7 compared the packed case at 19 in. In the loaded cases at 23 in the fine
loaded face sits **4–11 mm further aft** (away from the head) than the coarse face at z 735–835 (meat −11.7 / −3.8 /
+9.0 mm coarse against −1.6 / +6.0 / +19.7 mm fine, rev 0). 34° is the **frame-only limit**: with the bag wall moved
3 m aft, `r28_loaded` still gives 34° (male p50 head on the bare bar and back pad, gap 6.8 mm at 30°; test
`test_r28_frame_only_ceiling_is_34_deg`). So on the fine mesh the bag wall is not the first contact.

Sensitivity to the wall allowance (fabric thickness + mesh scatter; `corrie_f_sim.py r28sweep`, worst of fill / meat):

| Row | 3 mm | 6 | 9 | 12 | 20 mm |
|---|---:|---:|---:|---:|---:|
| rev 0 coarse 23 in | 32 | 31 | **30** | 28 | 25 |
| rev 1 coarse 23 in | 34 | 34 | 32 | 31 | 27 |
| rev 0 fine 23 in | 34 | 34 | 34 | 33 | 29 |
| rev 1 fine 15 in | 34 | 34 | 33 | 32 | 28 |
| rev 1 fine 19 in | 34 | 34 | 34 | 34 | 34 |
| rev 1 fine 23 in | 34 | 34 | 34 | 34 | 31 |

The review was right that the rev 0 coarse margin was thin (30° at 9 mm). On the fine mesh rev 1 holds ≥ 31° up to
a 12 mm allowance at every torso (4× the coded value) and up to 20 mm at 19 and 23 in. The 15 in meat case is the
most sensitive (28° at 20 mm). The prototype protractor check (section 8) stays, now at all three crown kits.

### 12.2 Guys-off misuse at 15 in, meat (S11)

| Run (rev 1 bag, guys off) | converged | rounding | CG y | + bias | closed L | IM3 hook max, 1 g | × 3.0 factored |
|---|---|---:|---:|---:|---:|---:|---:|
| coarse h 40, 6 mm start (`F_PR15_goff`) | **no** (stalled) | – | 199.7 | – | 85.1 | 567 N | 1701 N |
| coarse h 40, 8 mm start (`F_PR15_goff_sm8`) | yes | 2 mm | 186.6 | 187.9 | 87.5 | **970 N** | **2911 N** |
| **fine h 25, 8 mm start (`F_PR15_fineFM_goff_sm8`)** | yes | 0 mm | **201.7** | 201.7 | 85.0 | 436 N | 1308 N |
| guys on, fine h 25 (`F_PR15_fineFM`) | yes | 3 mm | 178.1 | 180.1 | 82.5 | 562 N | 1687 N |

- **CG:** the fine run governs (finest mesh, zero rounding, and it agrees with the stalled coarse run). Guys off, the
  15 in meat CG is **201.7 mm, 11.7 mm over the rev C 190 mm limit** (guys on: 178.1 mm). Like CORRIE B.2 and S15
  (attachment_diet.md: 199.5 mm), CORRIE F stays inside rev C only with the guys on.
- **IM3 load:** the two converged runs disagree. The coarse 8 mm run settled on a different equilibrium (bag swung
  ~50 mm aft, hinges 970 N, closed volume +3 L, IM3 970 N at 1 g). The fine run reads 436 N, *lower* than guys on.
  Until it is resolved, the conservative basis is the worst converged run: **2911 N factored, 71 % over the BL-004
  1702 N basis** It stays under the B-17 seam (3277 N), the box-X (5256 N; attachment_diet.md section 5) and the BL-010
  wiregate carabiner (minor-axis proof 4000 N, section 5.3). The fine run is below the basis (1308 N). Not resolved here: for the structural-fea-engineer (section 12.6).
- **Carry rule and hang-tag.** Section 1 says "guys on is a carry rule (bright toggle + hang-tag)", but no wording was
  written. Rev 1 wording, for the hang-tag on the right guy and the manual:

  > **GUYS ON.** Clip both guys to the crown before you load meat. Without them the load sags away from your back
  > and the pack is outside its rated carry. Check: both bright toggles through the bar tabs.

  The rule covers the CG case. It does not cover the coarse-run IM3 load, because misuse must not overload a part:
  that needs the structural answer in 12.6.

### 12.3 Guy loops against the lifter lugs (S6)

All three BL-017 crown kits (`crown_diet` specs acb_S / acb_M / acb_L, each checked at both ends of its torso
range: S 15–18, M 17.5–20.5, L 20–23 in) put the legs at x ±115 on a straight top bar (z 601–804 mm). So one layout
check covers every kit (`guy_lifter_check`, right half; the left mirrors it):

| Band on the bar (x, mm) | from | rev 0 guys x ±92 | rev 0 guys x ±100 | **rev 1 guys x ±52** |
|---|---|---|---|---|
| lifter webbing 92.5–107 | LIFTER_X 105, 25 mm webbing, clipped at the leg face | **overlap 12 mm** | **overlap 14.5 mm** | clear **28 mm** |
| crown-corner wrap 69–107 | frame.yaml wrap 30 mm + 8 mm scarf | inside the wrap | inside the wrap | clear 4.5 mm |
| spine clamp 0–15 | ASSUMPTION ±15 | – | – | clear 24.5 mm |
| guy band | 25 mm webbing | 79.5–104.5 | 87.5–112.5 | **39.5–64.5** |

Rev 0 clashed at every kit. **Rev 1 moves the guys, not the lifters** (lifters stay on the crown top bar at x ±105,
patent guardrail). The guy line also moves further from the lifter webbing in 3D: 59.7 mm against 36.8 mm
(`guy_geometry`, at 15 / 19 / 23 in).

An inboard loop on a smooth bar would slide outboard: the guy's outboard share of its tension is 0.37–0.41 against
MU_WEB_BAR 0.30 (ASSUMPTION, settled by a pull test). So rev 1 uses the **B-25 guy bridle**: one 25 mm webbing piece
sewn round the bar at x ±52 (two sleeves), joined along the bar and round the spine below its clamp, so the spine
locates it and the two outboard pulls cancel in the webbing. A folded tab at each sleeve takes the guy's toggle loop.
It is fitted on the bar before the crown corners are bonded (build step). 412.5 mm, **7.43 g** (poly_webbing_25mm
record; BAR_WRAP_MM, SPINE_WRAP_MM, BRIDLE_TAB_MM are ASSUMPTIONs settled by the first bridle cut).

**Re-run of the 15 in meat CG with the guys at x ±52** (coarse h 40, `F_PR15`): **174.0 mm** (178.0 with bias),
against 173.8 mm at x ±100. Guy load 35 N against 40 N. The full rev 1 table:

| Torso / case | rev 0 coarse CG y | **rev 1 coarse CG y (+bias)** | rev 1 fine CG y (+bias) | rev 1 fine L | rev 1 fine IM3 / guy, 1 g |
|---|---:|---:|---:|---:|---:|
| 15 fill | 177.2 | 180.2 (184.2) | 184.2 (186.2) | 83.2 | 402 / 53 N |
| 15 meat | 173.8 | **174.0 (178.0)** | 178.1 (180.1) | 82.5 | 562 / 38 N |
| 19 fill | 155.2 | 163.4 (167.4) | 170.0 (171.3) | 83.2 | 330 / 77 N |
| 19 meat | 145.5 | 158.6 (162.6) | 163.4 (165.4) | 82.6 | 554 / 55 N |
| 23 fill | 135.9 | 138.8 (142.8) ¹ | 141.3 (142.0) | 84.0 | 307 / 98 N |
| 23 meat | 132.5 | 136.6 (138.6) | 135.7 (137.0) | 82.4 | 522 / 69 N |

¹ the standard 6 mm start stalled; retried from 8 mm rounding (`F_PR23_sm8`, converged at 6 mm).

All inside rev C (fill ≤ 205, meat ≤ 190). Moving the guys inboard costs CG at 19 in (+8 mm fill, +13 mm meat,
coarse), because the guy line pulls the crown less directly forward; at 15 in, the governing torso, it is +0.2 mm.
The fine mesh reads −1 to +7 mm further aft than the coarse mesh, and the fine 15 in meat CG (178.1 mm; 180.1 with bias)
sits on the BL-011 180 mm acceptance. Fine volumes are 82.4–84.0 L, 1.0–1.7 L below coarse; the coarse fill mean is
84.7 L (inside 85 ±3). Volume and access do not change because of rev 1's parts.

**Top bar bending:** with the guys inboard the bar arm grows from 20 to 63 mm. At the largest factored guy load in
any rev 1 run (104 N × 3.0 = 312 N, fine 23 in fill), fixed-fixed bar bending gives **69.9 MPa against 27.9 MPa** at
x ±95 (`top_bar_guy_moment`, I = 1838 mm⁴ from frame.yaml bar_section). This adds to the lifter load case on the same
bar: for the structural-fea-engineer (12.6).

### 12.4 Side carry: the tripod keeper (S7)

The scope pod hangs from its own 4 hard points (left gusset, z 420 / 640) and does not depend on W1/W2, so opening
the door never frees it. The tripod did. Rev 1 adds **B-26: one 3 mm shock cord across the right gusset** at z 600
(ASSUMPTION TRIPOD_KEEPER_Z, upper legs; feet on FP-R's top edge at z 380). The ends are caught 15 mm in the B-01 |
gusset R seam and the aft corner seam (D2: blade U | gusset R). On D1 the aft corner seam carries the zip, so the aft
end goes in a 25 × 60 mm webbing tab 20 mm forward of the zip.

| | D2 | D1 |
|---|---:|---:|
| gusset span at z 600 | 214.2 mm | 214.2 mm |
| cut (80 % of span + 2 × 15 mm catch) | 201.4 mm | 201.4 mm |
| stretch with a 70 mm tripod bundle (ASSUMPTION TRIPOD_D) | 48 % | 48 % |
| **mass** (shock_cord_3mm record 6 g/m; tab poly_webbing_25mm) | **1.21 g** | **2.29 g** (tab 1.08) |
| glove time per door cycle | **0 s** (not touched) | 0 s |
| glove time per packing (slide the tripod in head first) | 6 s (ASSUMPTION, FT-S2) | 6 s |

Compared with team B's A2 tripod straps (32.2 g, 4 loops) this is 31 g lighter, and W1/W2 still compress the tripod
when closed. A W-strap re-routing (0 g) was rejected: W1/W2 cross the door, so any routing that holds the tripod is
also unhooked to open it. FT-S2 gains a step: **door open / close × 5 with the tripod loaded, tripod shift ≤ 20 mm.**

### 12.5 New and changed gates

| Gate | Settles |
|---|---|
| R-28 protractor check, loaded, at **all three crown kits** (was L only) | 12.1 |
| Pull test, 25 mm poly loop on the clear-coated bar (MU_WEB_BAR) and B-25 bridle slip at 312 N | 12.3 |
| Crown fit of B-25 at x ±52: 4.5 mm to the corner wrap, ≥ 10 mm (MIN_CLEAR_MM) gloved toggle room to the lifter | 12.3 |
| FT-S2 + door open / close × 5 with the tripod under B-26 (shift ≤ 20 mm); time the packing (6 s ASSUMPTION) | 12.4 |
| Right-gusset fit: B-26 height over the tripod legs (TRIPOD_KEEPER_Z, TRIPOD_D) | 12.4 |
| Hang-tag "GUYS ON" printed and fitted to the right guy | 12.2 |

### 12.6 For the structural-fea-engineer (found, not fixed here)

1. **Guys-off IM3 load:** a converged coarse run gives 970 N at 1 g (2911 N factored, above the 1702 N basis; under the
   B-17 seam 3277 N and the carabiner's 4000 N minor-axis proof); the fine run gives 436 N. Decide which equilibrium is real (a fine run from 6 mm rounding,
   or a pull-down test with the guys off) before the misuse basis is closed.
2. **Top bar with inboard guys:** 69.9 MPa from the guys alone at 312 N factored, x ±52; combine with the lifter
   case in the frame model.
3. IM3 at 1 g on the fine mesh: 562 N (15 in meat), slightly above the coarse 552 N used for the 27 mm cheek.
