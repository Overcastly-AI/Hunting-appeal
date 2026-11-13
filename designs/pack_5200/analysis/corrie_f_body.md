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
- **Guy routing (BL-028, section 13):** the straight guy in every sim passes through the bag. On its real path, round the
  bag's side, rev 1's 15 in meat CG is **194.9 mm, over rev C**; the lifters are clear (≥ 48 mm). **Rev 2 (proposed):**
  guy through a lapped port B-27 in B-01 and inside to B-22: 181.9 mm (1.9 mm over the 180 acceptance, inside rev C),
  R-28 34°, +2.7 g.
- **Top anchor and lid (BL-029, section 14):** the Exo way (crown straps from the bar over a lid) holds the lid but not
  the load: 15 in meat CG **194.0 mm, over rev C**. **Rev 3 (recommended) = rev 2's port guys + a 5.0 L B-29 crown lid
  on two B-28 crown straps**, replacing the 2.7 L pouch: **181.3 mm** (target 185), R-28 34°, lifter gap ≥ 57 mm,
  +59.0 g as hunted over rev 2 (base unchanged). BL-028's rev 1 wrap re-run with its eyelets in order: 198.1 mm.
- **Rev 3 adopted (owner, 2026-11-12) and made the design of record by BL-030 (section 15):** rev 3 is the module
  default, the ledger's adopted bag (`ledger.ADOPTED_BAG`) and the roll-up's CORRIE F. The B-28 crown straps go to
  **20 mm, cut 1138 mm, 49.1 g the pair (−18.4 g)**, sized from the strap's path over the rolled top with the lid;
  ladder-lock slip 319 N against the 288 N factored envelope (1.11, on an assumed slip ratio: B-28 slip gate). Bag
  side belt M D2: **base 1112.8 g, as hunted 1362.4 g, meat trip 1494.6 g**.

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

## 13. Guy routing: the real path and CORRIE F rev 2 (BL-028)

pack-designer, 2026-11-12. Ticket `docs/backlog/BL-028-guy-routing.md`, from BL-026's 3D finding (`corrie_f_renders.md`
§8.4). Code: `corrie_f.py` section BL-028 (`ClothSurface`, `taut_path`, `path_metrics`, `real_guy_path`, `path_vias`,
`ROUTES`, `bl028_paths`, `bl028_table`, `guy_port`, `guy_length_check`, `plot_bl028`, `plot_bl028_port`, `REVS[2]`; CLI
`python designs/pack_5200/concepts/corrie_f.py --bl028`). `corrie_f_sim.py` gains `--route` (the guy re-threaded
through frictionless eyelets on the cloth, internal bag-to-bag ties, or a deleted guy; huntkit not edited, swapped in at
run time like the shell) and a `sixday` case. Results: `corrie_f_sim/corrie_f_guy_paths.json` and the stored rows
`F_PR{t}_fineFM_<route>` in `corrie_f_sim_results.json`. Tests: `tests/test_corrie_f_guy.py`. All runs fine mesh
(h 25 mm), one at a time. **Rev 1 stays the module default; rev 2 is `with corrie_f.revision(2):` and is a proposal
(13.7).**

**In one paragraph.** The straight guy that every cloth sim has used since the attachment phase (2026-11-05: hood ears,
then BL-004's bar loops, then BL-022's x ±52 bridle) passes through the packed bag. It is a model artefact. A real guy
has to go round the bag's side to reach B-22, and on that path it pulls the bag sideways, not forward. With the guy
re-threaded on its real path, **the 15 in meat CG is 194.9 mm (7.67 in), over the rev C limit of 190 mm (7.48 in)**
(the straight model said 178.1 mm). The lifter clash that BL-026 drew does not happen on the real path: the strap
leaves the bar aft, onto the bag's frame face, and stays **≥ 48 mm (1.9 in)** from the lifter webbing. The fix that
works is to take the guy **inside**: through a lapped port (B-27) in the frame face B-01 where the bar meets it, then
straight across the inside of the bag to B-22. That gives **181.9 mm (7.16 in) at 15 in meat: inside rev C, but 1.9 mm
over the 180 mm (7.09 in) acceptance**. R-28 stays at 34° at 15 / 19 / 23 in. +2.7 g (0.10 oz).

### 13.1 Method: the guy as a taut strap

`taut_path` pulls a string tight from the bridle sleeve (x ±52 on the bar's bag face, where every scenario puts the
guy's bar end) to B-22 (the scenario's tie node, at its loaded position), keeping it `PATH_CLEAR` = 2 mm outside the
fine cloth drape and outside the crown tubes (`crown_tubes`: the bar with the corner wraps, both legs and the spine,
placed as the cloth sim's crown field places them). It starts from a polyline round the bag's outboard side, then
relaxes (each sweep moves a point toward its neighbours' mid-point and pushes it back out of the obstacles). Checked
against the closed form for a strap round a cylinder (length within 1 %, wrap within 3°;
`test_taut_path_round_a_cylinder_matches_the_closed_form`). Per path, `path_metrics` reports:

- **wrap angle** = total turning where the strap bears on the cloth; **friction share** = 1 − e^(−μθ), the part of the
  cinch tension the wrap holds back (capstan), μ = `MU_WEB_FAB` 0.30 (ASSUMPTION, band 0.20–0.40);
- **pull on the bag** = along the first free run, from the bag toward the bar. The wrapped part and B-22 move with the
  bag, so this direction is what holds the bag. Its forward (−y) part is what holds the CG;
- **pull on B-22** = back along the last run, between T·e^(−μθ) (being cinched) and T (load creeping out), with T = the
  run's simulated guy tension at 1 g;
- **lifter gap** = edge-to-edge gap between the guy ribbon (25 mm, lying on the cloth) and the lifter ribbon (25 mm,
  from the lug at x 105 on the crown corner toward the shoulder strap at the setting's lifter angle).

### 13.2 Rev 1's real path (task 1)

On the BL-022 fine drapes (`F_r1_PR{t}_fineFM`, guys as simulated), right / left:

| Torso, load | length (straight) mm | wrap ° | friction share | forward pull share: real (straight) | B-22 pull, N at 1 g | lifter gap mm |
|---|---|---|---|---|---|---|
| 15 in full | 401 / 401 (250) | 199 / 186 | 0.65 / 0.62 | 0.39 / 0.29 (0.98) | 18.8–53.3 / 19.3–51.1 | 56 / 55 |
| 15 in meat | 392 / 400 (250) | 183 / 208 | 0.62 / 0.66 | **0.22 / 0.03** (0.98) | 14.6–38.1 / 12.6–37.4 | 53 / **48** |
| 19 in full | 370 / 387 (239) | 178 / 185 | 0.61 / 0.62 | 0.62 / 0.47 (0.88) | 30.3–77.0 / 28.9–75.9 | 60 / 60 |
| 19 in meat | 359 / 363 (239) | 179 / 175 | 0.61 / 0.60 | 0.56 / 0.45 (0.89) | 20.8–53.3 / 21.9–54.8 | 60 / 60 |
| 23 in full | 374 / 386 (269) | 171 / 181 | 0.59 / 0.61 | 0.28 / 0.14 (0.73) | 36.3–88.9 / 38.1–98.4 | 58 / 54 |
| 23 in meat | 377 / 383 (269) | 184 / 179 | 0.62 / 0.61 | 0.20 / 0.14 (0.73) | 23.1–60.3 / 27.0–69.0 | 55 / 51 |
| 15 in 6-day ¹ | 414 / 414 (311) | 163 / 109 | 0.57 / 0.43 | 0.56 / 0.53 (0.82) | – | 55 / 54 |

¹ 6-day = 45 L / 22 kg (ASSUMPTION RS-1, `shell_sweep.RENDER_STATES`), wraps cinched, guys on their real path. The run
did **not converge** in its 240 s cap (residual 7.8 N, closed 72 L: the sim cannot roll the collar down), so this row
is geometry only. 19 and 23 in 6-day were not run (same set-up, same outcome expected; stopped to save time). The full
and meat rows bracket the 6-day shape near the bar (the strap lies on the frame face at bar height in every case).

What this means:

- **Length** 359–414 mm (14.1–16.3 in) against the 239–269 mm straight line; BL-026's 3D model measured 363–375 mm.
  Rev 1 booked the guy at the straight length: the real path needs **114–150 mm more webbing a side, +4.1–5.4 g a pair**
  (`guy_length_check`). Moot if rev 2 is adopted (its inside path is the straight length).
- **Wrap** 171–208° round the bag's side: 59–66 % of the cinch tension is held back by friction before it reaches
  B-22. The strap cannot be cinched snug from the bar end.
- **Pull.** At B-22 the pull now runs along the aft face toward the corner (outboard), not toward the bar. The bag as a
  whole is pulled along the strap's first run, which leaves the bar outboard along the frame face: **75–98 % of it is
  sideways** (left and right cancel), and the forward share at 15 in meat is 0.03–0.22 against 0.98 in the straight model.
- **The bar end slides.** The strap leaves the sleeve with 0.75–0.98 of its tension along the bar (outboard), against
  `MU_WEB_BAR` 0.30: the B-25 bridle still has to hold it (as BL-022 found for the straight line).

### 13.3 Lifter clearance on the real path

The strap leaves the sleeve aft, onto the bag's frame face just behind the bar (y 25–47 mm against the bar's bag face at
y 19–23), runs outboard on the frame face to the bag's front corner and round the gusset. The lifter leaves its lug on
the **wearer's** side of the crown corner (15 mm forward of the leg axis) and runs forward and down. The frame tube is
between them. **Worst edge gap 48 mm (1.9 in), 15 in meat, left; ≥ 10 mm at every torso and load.** The three crown
kits share the bar (BL-022 `guy_lifter_check`), and 15 / 19 / 23 in are both ends and the middle of the S–L range.

BL-026's picture ran the guy along the top of the bar to the crown corner, because the render's frame face sits 0–17 mm
inside the bar (defect D-9), so the strap could not pass between bag and bar there. On the sim drape the bag face is aft
of the bar where the strap leaves. **There is no lifter clash to fix; the problem is the pull.** The prototype crown
fit with the bag packed full (gate in §12.5) still settles it.

### 13.4 What the real path does to the CG

`corrie_f_sim.py finerun F --torso 15 --cases meat --route <name>` re-threads each guy through eyelets (sim via nodes,
frictionless) on the nodes its real path bears on, every 40 mm (`path_vias`), same fixed-length rule as before (snug at
the drafted shape, 30 N). 15 in meat, fine mesh, all converged:

| Guy model / routing | CG y mm (in) | guy N at 1 g | IM3 N at 1 g |
|---|---:|---:|---:|
| straight line through the bag (BL-022, `F_PR15_fineFM`; 3 mm rounding, +2 bias) | 178.1 (7.01) | 38.1 | 562 |
| **rev 1 real: round the bag (`_wrap`)** | **194.9 (7.67)** | 11.7 | 442 |
| internal depth tie B-22 → B-01 plus the real wrap (`_tie_wrap`) | 194.8 | 10.4 + 13.5 | 435 |
| no outside guy; internal guy B-22 → IM3 bag-hook eye (`_im3`) | 198.7 | 26.7 | 442 |
| **rev 2: B-01 port at the bar, inside to B-22 (`_port`)** | **181.9 (7.16)** ² | 40.7 | 425 |
| port, inside tab at the collar seam, x 149 (`_port_hi`) | 183.9 | 36.6 | 446 |
| port, inside tab at the collar seam, x 100 (`_port_hi_in`) | 183.1 | 34.9 | 438 |
| guys off (BL-022, `F_PR15_fineFM_goff_sm8`) | 201.7 (7.94) | 0 | 436 |

² from the fill run's end state (stored row); the same routing started from the packed bag (meat only) gave 183.4 mm.
Two starts, 1.5 mm apart: read 181.9–183.4 mm.

- **Rev 1 as it would be built fails rev C at 15 in meat (194.9 > 190).** It recovers only 6.8 mm of the 23.6 mm the
  straight model credited to the guys. Every "guys on" CG since 2026-11-05 carries this artefact (found, not fixed: the
  older concepts are not re-run here).
- The guy works by tying the bag's **upper aft corner to the bar**, against the top tipping aft. A tie that only
  limits depth does nothing (194.8). A tie to the IM3 eye is worse (198.7), because IM3 sits low (z 520) and swings
  with the bag. Only a line from the **bar** to the **aft top** does the job, and from outside the bag that line does
  not exist.
- Moving the inside tab higher or inboard does not help (183.1–183.9): the port is the limit, not the tab.
- IM3 at 1 g, 15 in meat, is 425–446 N on every real routing against 562 N on the straight model. With rev 2 it is
  425 / 393 / 517 N at 15 / 19 / 23 in meat, against 562 / 554 / 522 N on the straight model. Every rev 2 value is
  under the basis BL-021 / BL-024 used (found, not fixed).

### 13.5 Rev 2: the guy goes inside (B-27 guy port)

- **B-27 guy port, one each side:** a vertical slit in B-01 at **x ±52**, **z 595–745** (150 mm, 5.9 in: from 6 mm
  below the lowest bar, 15 in at z 601, to B-01's top edge at the collar seam). The outboard edge laps 20 mm over the
  inboard edge, on a 50 × 170 mm facing of B-01 fabric sewn inside along the inboard edge. Both edges are turned 6 mm and
  edge-stitched, with bartacks at both ends. It crosses the setback fold seam at z 631 (the facing follows the fold).
  No hook-and-loop, no zip, fabric on fabric: quiet. **2.74 g (0.10 oz) the pair** (`guy_port`, challenge_ultra_200
  record × area; `PORT_FACING_W`, `PORT_TURN` are ASSUMPTIONS).
- **Guy:** from the B-25 bridle tab (toggle, unchanged) straight aft through the port, across the inside of the bag to
  **B-22, turned to the inside** of the hinge band (same tab, same seam, same place, x ±149, z 695). The heavy ladder
  lock sits on its LLT tab at B-22, INSIDE the hinge band (BL-040 DECISION GUY-LOCK-IN, section 20; this line said
  "just outside the port", which the pattern, the ops and the load table never drew). The guy length is set with the
  roll top open, per crown kit and load (the "fixed length" rule), not on the move. Bag-off: the toggle comes out of the bridle tab as in rev 1, and the guy stays with the bag.
- **Bar heights:** S kit z 601–677 and M kit z 664–741 meet the slit. The L kit's bar (z 728–804) is above B-01's top
  edge from about 20.5 in, so the guy comes down to the slit's top end. The 23 in run includes this.
- **Lifters:** outside the bag the guy runs only from the sleeve to the port (8–23 mm at 15 and 19 in, 77–81 mm at 23 in
  where it comes down to the slit's top), never outboard of the bridle band
  x 39.5–64.5 (the lifter band starts at x 92.5; BL-022 `guy_lifter_check`, 28 mm). In 3D the gap is 58–64 mm on every
  rev 2 drape. Patent guardrail: the lifters stay on the crown top bar at x ±105.

Rev 2 fine runs (`F_PR{t}_fineFM_port`, fill then meat, all converged):

| Torso | full CG y mm (+bias) | meat CG y mm (+bias) | R-28 ° (gap at 30°) | guy N at 1 g, max | IM3 N at 1 g |
|---|---|---|---|---:|---:|
| 15 in | 186.4 (188.4) | **181.9** (181.9) | **34** (6.8 mm) | 57.3 | 425 |
| 19 in | 166.2 (167.5) | 160.1 (160.8) | **34** (6.8) | 77.5 | 393 |
| 23 in | 154.8 (156.8) | 149.0 (151.0) | **34** (6.8) | 96.1 | 517 |

- **Inside rev C everywhere** (full ≤ 205, meat ≤ 190). At 23 in it is 13 mm further aft than the straight model
  (135.7), because the port is 59 mm below the bar there. That is far inside the limit.
- **R-28 34° at all three torsos**, the frame-only limit. The bag wall moves 9–19 mm toward the head above the bar at
  19 and 23 in, but the bare bar and back pad still make first contact.
- **Top bar:** largest guy load 96.1 N at 1 g (23 in full), **288 N factored** (× 3.0) against the 312 N that BL-021
  checked the bar with (strength 1.36). That 1.36 is the bar's **bending** check, not the wall (ring crush) under the
  loop. The guy now pulls the bar aft (into the bag) instead of outboard along it, so the bridle's outboard load drops.
  **BL-041 (2026-11-13):** the ring check under the B-25 sleeve is `crown_tube_guy_loop.md` (structural): the guy and
  the B-28 crown strap share one B-25 tab, **323 N** envelope; the 25 mm sleeve fails it (basis A SF 0.90 / 0.85
  fatigue), so rev 3 builds **B-25 in 38 mm webbing, sleeves x 26.5–64.5, tab at the sleeve centre x 45.5** (SF 1.36 /
  1.27, +3.4 g); TL-1 proves it at 494 N on real bar stock (section 21).
- **Volume:** closed 81.9–84.0 L on the fine mesh, as rev 1 (82.4–84.0).

### 13.6 Options considered

| Option (ticket list first) | Result | Kept? |
|---|---|---|
| Guide loop or channel on the bag's top corner, guy inboard of the lifters | The real path is already ≥ 48 mm from the lifters. A loop holds the strap on the bag but does not change the first run from the bar, so the pull stays sideways (geometry, 13.2). Not simulated | no |
| Move B-22 so the straight path clears the bag | Every bag point the bar can see is on the frame face or its front corner, nearly in the bar's plane. Forward share is ≤ about 0.4 even with the top sagged aft (13.2). Not simulated | no |
| Route the guy under the lifter with a sleeve | No clash to avoid, and the pull problem is the same | no |
| Internal depth tie (B-22 to B-01, inside) | 194.8 mm | no |
| Internal guy to the IM3 eye (no frame change) | 198.7 mm, and adds load to the IM3 cheek, the fatigue-critical part | no |
| **Guy port B-27, guy inside (rev 2)** | **181.9 mm; R-28 34°; +2.7 g** | **proposed** |
| Port with the inside tab higher or inboard | 183.1–183.9 mm | no |

### 13.7 Acceptance and decisions

| Acceptance | Rev 1 (real path) | Rev 2 |
|---|---|---|
| Guy to lifter webbing ≥ 10 mm at every crown kit, on the real path | 48 mm: **pass** | 58 mm: **pass** |
| 15 in meat CG ≤ 180 mm, fine mesh | 194.9 mm: **fail** (over rev C 190) | 181.9 mm (183.4 from the other start): **fail by 1.9 mm**, inside rev C |
| R-28 ≥ 31° | 34° (BL-022) | 34° at 15 / 19 / 23 in: **pass** |

**Owner decisions needed:**
1. **Rev 1 as drawn does not hold the 15 in meat load inside rev C** once the guy is on its real path (194.9 mm).
   Something has to change before the bag is cut.
2. **Adopt rev 2 (guy port, guy inside)?** It is the only routing tried that gets back inside rev C. It puts two 25 mm
   straps across the top of the main compartment, from the frame face at x ±52 to the aft top corners at x ±149. Pack
   under them, and the meat goes in through the door below them. It adds two lapped slits in the frame face.
3. **Accept 182 mm at 15 in meat** (rev C 190 met, BL-011's 180 missed by 2 mm, inside the 1.5 mm start-to-start
   scatter plus the ±4 % mesh scatter), or ask for more. The next lever is outside the guy, for example a lower scope
   pod or top-pouch position at the S kit, which is a new ticket.

### 13.8 Assumptions that govern (new)

- ASSUMPTION `MU_WEB_FAB` 0.30, webbing on the PU face fabric (band 0.20–0.40). Only the friction share depends on it.
  Settled by **GT-1**: 5 kg hung on the guy over the packed bag's corner, pull to start it moving.
- ASSUMPTION `PATH_CLEAR` 2 mm, strap centre off the simulated cloth. Settled by the prototype crown fit (lifter gap).
- ASSUMPTION INT-1: contents packed round the inside guy do not slacken it or bend it out of line. The sim's contents
  are a pressure field, so the cable passes through them. Settled by the **T9 loaded-CG test at the S kit, rev 2,
  with the top packed full above the guys**.
- ASSUMPTION `PORT_FACING_W` 50 mm / `PORT_TURN` 6 mm (port construction). Settled by the first port mock-up: hose from
  above for 1 min with the guy pulled at 45° through it, then look for water inside, and check that the lap does not open
  under a 100 N guy pull.
- The eyelets in the sim are frictionless (huntkit `Cable`). Wrap friction (13.2) is not in the CG runs. It would hold
  the rev 1 wrap a little tighter, but it cannot turn a sideways pull into a forward one.
- 6-day: ASSUMPTION RS-1 (45 L / 22 kg), geometry only (not converged).

### 13.9 New gates

| Gate | Settles |
|---|---|
| GT-1 capstan pull test, guy over the packed bag's corner | `MU_WEB_FAB` (13.2) |
| Port mock-up: hose test, 100 N guy pull through the lap, glove use of the ladder lock at the port | B-27 construction |
| T9 at the S kit (15 in), rev 2, meat load: plumb-line CG ≤ 190 mm; record against 182 mm | 13.5, INT-1 |
| Crown fit with the bag packed full: guy at the port, no contact with the lifter or the corner wrap | 13.3 / 13.5 |

### 13.10 Found, not fixed

- Every guys-on CG since 2026-11-05 (attachment phase, BL-004, BL-011, BL-022, CORRIE B.2) modelled the guy as a
  straight line through the bag, so the guys' benefit is over-credited by about 17 mm at 15 in meat (on CORRIE F). Only
  CORRIE F is re-run here.
- IM3 at 1 g: rev 2 gives 425 / 393 / 517 N (15 / 19 / 23 in meat) against the straight model's 562 / 554 / 522 N,
  so BL-021's and BL-024's bases stay conservative. Not re-checked by the structural-fea-engineer.
- Rev 1's guy webbing is booked at the straight length: short by 114–150 mm a side on the real path.
- `REVISION` stays 1. Making rev 2 the default breaks `tests/test_corrie_f_run_dirs.py` (BL-025, asserts
  `REVISION == 1`) and `tests/test_corrie_f.py::test_rev0_is_reproducible_and_rev1_adds_only_its_parts`; on adoption,
  update both and the run-folder naming (rev 2 runs are stored as `F_r1_PR{t}_fineFM_port`, rev 1 bag + port routing).
- The 3D model (`huntkit/viz3d/corrie_f.py` `guys_rev1`) draws the guy along the top of the bar. That is a picture
  choice forced by D-9, and rev 2 needs a redraw (viz3d not edited here).
- The 6-day sim case does not converge without the collar rolled down (it needs `shell_sweep`'s dome swap and wrap
  take-up).
- `write_scenarios` now writes a `sixday` case into the generated `cf_PR*.yaml`.

Screens: `outputs/screens/20261112_BL028_1.png` (paths, CG by routing, lifter gap), `_2.png` (B-27 port).

### 13.11 Note added by BL-030: the `wrap` and `tie_wrap` eyelets were reversed

BL-029 found (14.8) that the `wrap` route above passed its eyelets to the cable bar-first:
`corrie_f_sim._install_route` builds the cable as [B-22] + vias + [bar], and `path_vias` lists the nodes from the bar,
so the stored cable crossed the bag twice. `tie_wrap` used the same vias. **Corrected rev 1 (`wrapfix`, eyelets in cable
order): 15 in meat CG 198.1 mm** (stored row `F_PR15_fineFM_wrapfix`), against the 194.9 mm in 13.2 and the table in
13.7. **Rev 1 still fails rev C (190 mm)**, by more than 13.2 says; the conclusions of this section stand, its 194.9 mm
does not. The port routes have one via and are not affected, so rev 2 (181.9 mm) and rev 3 (181.3 mm) stand.
`corrie_f._vias_head_first` now orders vias for every new route. The text above is left as BL-028 wrote it.

## 14. Top anchor and lid: CORRIE F rev 3 (BL-029)

pack-designer, 2026-11-12. Ticket `docs/backlog/BL-029-top-anchor-and-lid.md`. Owner: "Look at the exo bags. Our pouch
does not look right on this bag." Research: `docs/research/top_anchor_and_lids.md`. Code: `corrie_f.py` section BL-029
(`LID`, `lid_geometry`, `crown_lid`, `crown_path`, `crown_strap_length`, `crown_straps`, `rev3_addons`, `bl029_paths`,
`bl029_table`, `bl029_concepts`, `plot_bl029`, `plot_bl029_concepts`, `REVS[3]`, routes `over`, `over_port`, `wrapfix`;
CLI `python designs/pack_5200/concepts/corrie_f.py --bl029`). `corrie_f_sim.py` `--route` now takes a cinched routed
strap and a second frame-anchored cable (`_set_rest`, route keys `mode`, `pretension_n`, `anchor`, `extra`). Renders:
`corrie_f_rev3_viz3d.py`. Stored rows `F_PR{t}_fineFM_over*`, `F_PR15_fineFM_wrapfix`; paths
`corrie_f_sim/corrie_f_crown_paths.json`. Tests `tests/test_corrie_f_top_anchor.py`. All sims fine mesh (h 25 mm), one at
a time. **Rev 1 stays the module default; rev 3 is `with corrie_f.revision(3):` and is a recommendation (14.7).** *(BL-030: the owner adopted rev 3 on 2026-11-12 and it is now the module default, section 15.)*

**In one paragraph.** Every peer that carries a lid holds it with straps from the frame side, over the load, to the bag's
front, and three of them sell that strap path without the lid as top compression (Exo Packout Straps, Stone Glacier's
extender kit, Seek Outside's lid straps; research section 8). So the Exo answer is "the lid's straps are the top
anchor". On CORRIE F that answer **does not hold the 15 in meat load**: crown straps from the bar over the roll give
**194.0 mm (7.64 in), over rev C (190)**, because at the S kit the bar (z 601) sits 130+ mm below the bag top and an
outside strap pulls the bag only along its first run from the bar, which climbs the frame face (mostly down). What works
is rev 2's inside guy. **Rev 3 = rev 2's B-27 port guys + the B-29 crown lid on two B-28 crown straps**: the lid gets the
peer look (one strap line from the bar, over the lid, to the bag) and the port guys do the anchoring. **15 in meat CG
181.3 mm (7.14 in) against the 185 mm target; R-28 34° at 15 / 19 / 23 in; lifter gap ≥ 57 mm.** The lid is 5.0 L
(304 cu in), 45.9 g (1.62 oz); with its straps it costs +59.0 g (2.08 oz) as hunted over rev 2 (base unchanged).

### 14.1 What the research says (summary; sources in the research file)

| Brand | Lid | How the lid / top holds | Takeaway for CORRIE F |
|---|---|---|---|
| Exo K4 | 10.6 L (648 cu in), 230 g (8.1 oz), 305 × 279 × 127 mm | front and back straps, ladder locks for no play; Packout Straps frame top → bag top without the lid | the lid's strap path is the anchor; ladder locks at the rear |
| Stone Glacier | EVO lid: buckles front, tension locks back | extender kit replaces the lid for top compression | same path, lidless option |
| Kifaru | Guide Lid on the Duplex frame, 4 × 30 in K-clip straps | lid hangs on the frame, height adjustable | lid on the frame, not the bag |
| Seek Outside | 8.2 L (500 cu in), 170 g (6 oz) | 2 long straps to the bottom of the pack | lid strap = full-height compression |
| Mystery Ranch | removable lid, zipped pockets | lid buckles designed with the roll closure | lid and roll designed together |

Look rules (research section 7): footprint = the bag top; a crown, not a box; one strap line runs through; lid edge on a
bag seam; the bag's two fabrics in the bag's proportions with camo only where the bag already has it; no hardware of its
own. The old 2.7 L pouch breaks rules 1, 2, 3 and 6 (a 280 × 190 × 60 mm box, four short G-hook straps).

### 14.2 The lid B-29 and the crown straps B-28

- **B-29 crown lid** (`LID`, `crown_lid`): plan 350 × 210 mm (13.8 × 8.3 in), superellipse n 4 (the bag's rounded
  corner language), 30 mm wall + 55 mm dome (85 mm, 3.3 in). Width is 10 mm inside the 360 mm collar seam; depth covers
  the closed top (collar depth 165 mm) with the aft wall over the hinge band seam. **Volume 4.98 L (304 cu in)**,
  computed from the shape (`lid_geometry`, numerical; checked against the closed-form plan area), **counted outside the
  85 L main bag** like every peer lid. Crown and wall ULTRAGrid (body colour), base 70D (it lies on the roll), two camo
  corner caps (630D printable) over the D2 blades, a #5 coil zip (quiet, no hook-and-loop) along the aft wall and round
  both aft corners (470 mm), two 30 mm strap channels on the crown at x ±52. **45.9 g (1.62 oz)** from the records ×
  cut area + zip record; `LID_SLIDER5_G` 3 g and `LID_THREAD` 3 % are ASSUMPTIONS. Today's fabrics: 56.8 g.
- **B-28 crown straps** (`crown_straps`): one 25 mm strap each side at x ±52: a POM toggle into a second fold on the
  B-25 bridle tab (the guy keeps its own tab), up the frame face, through the lid channel, down the aft face to a heavy
  ladder lock on a 60 mm tab in the hinge band seam at z 700 (drafted), above the D2 door top (z 650), so the straps
  never cross the door. Cut 1198 mm (47.2 in): the longest taut path over the stored drapes (818 mm, 15 in full) + 2 ×
  lid height + 150 mm tail + 60 mm loop. **67.5 g (2.38 oz) the pair.** Cinched by hand on the packed bag (80 N,
  the W1–W3 ASSUMPTION).
- Ledger (belt M, D2; `weight_table`): **base 1112.8 g, as hunted 1380.8 g, meat trip 1513.0 g** bag side at rev 3,
  against rev 2 1112.8 / 1321.8 / 1454.0 g and rev 1 1110.1 / 1319.1 / 1451.3 g. Pack on H1 as hunted 3682.1 g
  (rev 2 3623.1 g). The lid and its straps are as hunted (`pouch` and `straps_compression`): lid off, the straps come
  off with it, the roll's own side clips close the bag, and the port guys (base) still hold the top.
- Build hours (`bag_concepts.HOURS` model): lid 7.8 h against the pouch's 3.3 h (two curved perimeter seams). 9 pieces.

### 14.3 The three concepts

Sketches: `outputs/screens/20261112_BL029_5.png`. Outside the bag all three look the same (the lid close-up render,
`_3.png`, shows it); T3 adds two port stubs at the bar.

| | T1 anchor lid | T2 crown straps + captured lid | **T3 = rev 3** |
|---|---|---|---|
| What it is | the lid's own 4 straps (rear to the B-25 tabs, front to the hinge band) are the top anchor; guys deleted | B-28 straps belong to the bag (base); lid slides onto them; guys deleted | rev 2's B-27 port guys inside + B-28 / B-29 as hunted |
| 15 in meat CG, fine | **194.0 mm: fails rev C** (run `over`) | **194.0 mm: fails rev C** (same strap path) | **181.3 mm: pass** (run `over_port`) |
| Lid off | top anchor off: guys-off case, 201.7 mm | straps stay: 194.0 mm | port guys hold: 181.9 mm (rev 2 run) |
| Mass vs rev 1, base / as hunted | −59.7 / −0.7 g | +7.7 / −0.7 g | **+2.7 / +61.8 g** |
| Gloved actions to open the main bag (ASSUMPTION GLOVE-T) | 6 | 6 | 6 (rev 1 with the pouch: 7) |
| Patent check | no strap to the lifters or shoulder straps; lifters on the crown top bar; no pop-up pole (US 10,952,523 claim 1); strap over the closure is expired prior art (US 4,213,549); no frame-top pocket (US 8,579,171) | same | same; the port guy is BL-028's |

Gloved sequence (T2 / T3): lift the two front ladder locks (2), turn the lid back over the bar (1), unclip the two roll
buckles (2), unroll (1). Closing adds two cinch pulls. The lid pocket opens with one zip pull under the strap runs
(the zip is on the aft wall, the straps cross it on the crown).

### 14.4 Why the outside strap cannot do it at 15 in

A strap anchored on the bag and pulled at the bar puts one net force on the bag: its tension along the strap's first
free run from the bar. Its forward part is what holds the top. The crown strap's forward share at the bar is 0.59–0.66
on its own drape (15 in), but the strap is cinched to 80 N on the packed bag and then relaxes to 14–18 N at 1 g as the
loaded top settles (soft cinch compliance, `cinch_strain` 3 %, ASSUMPTION). Rev 2's port guy runs from the bar straight
aft through B-01 to the aft top corner and carries 34–96 N. At 19 and 23 in (bar z 703 / 804) the crown strap's
forward share rises to 0.55–0.74; at 15 in the bar is the problem, not the strap. The levers outside the bag are a
lash point higher on the S crown (a frame change; DECISIONS 2026-11-01 allows posts as lash points only) or a stiff lid
that bears on the frame: both new work, not tried.

### 14.5 Rev 3 on the fine mesh (real strap paths: eyelets on the cloth, crown strap cinched, port guy fixed length)

| Torso | fill CG y mm (+bias) | meat CG y mm (+bias) | R-28 ° | crown strap / port guy N at 1 g, max | IM3 N at 1 g | lifter gap crown / port mm | closed L fill / meat |
|---|---|---|---|---|---|---|---|
| 15 in | 184.1 (186.1) | **181.3** (181.3) | **34** | 12 / 51 | 428 | 60 / 60 | 82.7 / 81.8 |
| 19 in | 165.1 (167.1) | 159.1 (159.8) | **34** | 7 / 74 | 420 | 60 / 59 | 83.5 / 81.7 |
| 23 in | 152.7 (154.7) | 146.8 (148.1) | **34** | 7 / 96 | 475 | 61 / 57 | 83.4 / 81.5 |

All converged. Inside rev C everywhere (fill ≤ 205, meat ≤ 190). Against rev 2: −0.6 / −1.0 / −2.2 mm (meat), the
crown straps help a little. The lifter gap is the 3D edge gap between the strap ribbons and the lifter webbing on every
drape (`bl029_paths`); the three crown kits share the bar layout (BL-022), and 15 / 19 / 23 in are both ends and the
middle of the S–L range, so every kit has ≥ 57 mm against the 10 mm gate. The port guy's 96 N at 23 in full is 288 N
factored, inside the 312 N BL-021 checked the bar with. Closed volumes on the fine mesh are under rev 2's
(0.1–1.2 L; the cinched straps press the top); fill 82.7–83.5 L is inside 85 ±3; the 81.5–81.8 L meat values are the cinched bag
with meat, not the capacity (the sewn bag is unchanged; coarse mesh not re-run). The 6-day case was not run: it does not
converge without the collar rolled down (BL-028, 13.10).

ASSUMPTION LID-SIM: the sim carries the lid as a 1.054 kg dead load on the collar top (the rev 1 pouch + straps + 1 kg),
not the 1.113 kg of rev 3 (lid + straps + 1 kg). The 59 g sit at y ≈ 117 mm, forward of the 181 mm CG, in a 68 kg
meat case (30 kg meat + 38 kg fill, pack5200_v31): 0.059 × (181 − 117) / 68 ≈ 0.06 mm forward, so leaving it out is
conservative. Settled by T9 with the sewn lid. The strap bears on the
cloth, not on a lid solid: in the sim the eyelets sit on the collar.

### 14.6 Renders

`corrie_f_rev3_viz3d.py --render` builds the rev 1 scene with the pouch off and adds rev 3: port stubs and slits, the
lid as cloth seated on the roll (its crown follows the roll's ridge, ASSUMPTION LID-SEAT, a picture choice), the crown
straps on their taut path (the hull of bag, roll and lid at x ±52), ladder locks and tails, channels and toggles.
`outputs/screens/20261112_BL029_1.png` hero on the 6 ft hunter (6-day), `_2` side, `_3` lid close-up, `_4` lid open
(front locks unhooked, lid turned back over the bar onto the form's shoulders; on a hunter it rests on the head).

### 14.7 Acceptance and decisions

| Acceptance | T1 / T2 | **Rev 3 (T3)** |
|---|---|---|
| 15 in meat CG ≤ 185 mm, fine mesh, real strap paths | 194.0: **fail** (over rev C) | **181.3: pass** |
| R-28 ≥ 31° | 34° (15 in) | 34° at 15 / 19 / 23 in: **pass** |
| Lifter gap ≥ 10 mm at every kit | 60 mm | ≥ 57 mm: **pass** |
| Lid reads as part of the bag | same lid | renders `_1`–`_4` |

**Owner decisions needed:**
1. **The Exo way alone does not work on this frame.** Straps from the bar over the lid hold the lid and look right, but
   at the S kit they leave the 15 in meat CG at 194 mm, over rev C. Something inside the bag has to tie the top to the
   bar: rev 2's port guys. Accept the port guys (they are the anchor; nobody touches them)?
2. **Adopt rev 3's crown lid in place of the 2.7 L pouch?** 5.0 L, 45.9 g lid + 67.5 g straps, +59 g as hunted over
   rev 2, +4.5 build hours.
3. If the port guys are refused: the next lever is a lash point higher on the S crown kit (frame work, a new ticket).

### 14.8 Found, not fixed

- **BL-028's `wrap` route passed its eyelets bar-first.** `corrie_f_sim._install_route` builds the cable as
  [B-22] + vias + [bar], and `path_vias` lists the nodes from the bar, so the stored rev 1 "real path" cable crossed the
  bag twice. Re-run with the eyelets in cable order (`wrapfix`): **198.1 mm** at 15 in meat (BL-028 stored 194.9). Rev 1
  fails rev C either way; the BL-028 conclusion stands, its number does not. `_route_tie` (`tie_wrap`) used the same
  vias. The port routes have one via and are not affected. Section 13 is not edited.
- The crown-strap cut (1198 mm) is set by the sim's unrolled collar at 15 in full; on a rolled 6-day top the path is
  about 505 mm. 20 mm webbing or a shorter cut with an extender would save 15–25 g; not designed.
- Lid build hours (7.8 h) come from the generic curved-seam rate; the pattern-maker should check them.
- `huntkit/viz3d/corrie_f.py` still draws rev 1's outside guys and the pouch; rev 3's renders swap them at run time.

### 14.9 Assumptions that govern (new)

- LID-SIM (above): lid as a dead load, 59 g light. Settled by T9 at the S kit with the sewn lid.
- `CROWN_PRE_N` 80 N hand cinch and `cinch_strain` 3 %: only T1 / T2's CG depends on them. Settled by T9 with a spring
  scale on the cinched crown strap.
- `LID_SLIDER5_G` 3 g, `LID_THREAD` 3 %: settled by weighing the first lid.
- GLOVE-T: gloved action counts. Settled by the FT glove test.
- LID-SEAT (render only): the lid's base bridges the roll like cloth. Settled by a photograph of the sewn lid.

### 14.10 New gates

| Gate | Settles |
|---|---|
| T9 at the S kit, rev 3, meat load, lid on with 1 kg: plumb-line CG ≤ 190 mm, record against 181 mm | 14.5, LID-SIM |
| Lid fit on a packed 6-day bag: lid edge on the hinge-band seam, camo caps over the blades, zip runs under the straps | 14.2 |
| Gloved open / close of the main bag through the lid, timed (FT) | 14.3 |
| Crown strap ladder lock slip at 300 N on the hinge-band tab | B-28 |

Screens: `outputs/screens/20261112_BL029_5.png` (concepts), `_6.png` (CG, sections, rev 3 table), `_1`–`_4` (renders).

## 15. Rev 3 as the design of record (BL-030)

pack-designer, 2026-11-12. Ticket `docs/backlog/BL-030-adopt-rev3.md` (owner adopted rev 3 on 2026-11-12, DECISIONS).
Code: `corrie_f.py` (`REVISION = 3`, `sim_rev`, `crown_strap_w`, `crown_straps(width)`, `crown_strap_diet`,
`lid_hold`, `lid_seam_list`, `CROWN_ROLLED`); `huntkit/mass/ledger.py` (`ADOPTED_BAG`, `adopted_bag_rows`);
`weight_rollup_v2.py` (reads the revision from the ledger); `huntkit/viz3d/corrie_f.py` (rev 3 drawn natively:
`_port_stub`, `lid_mesh`, `crown_lid`, `crown_rolled_paths`, shots `lid` / `open`); `corrie_f_sim.run_dir` (folders by
`sim_rev`). Data: `concepts/corrie_f_sim/corrie_f_crown_rolled.json` (`python -m huntkit.viz3d.corrie_f --crown-paths`).
Tests: `tests/test_corrie_f_adopt_rev3.py` (new) and the rev-default asserts in `test_corrie_f.py`,
`test_corrie_f_guy.py`, `test_corrie_f_run_dirs.py`, `test_corrie_f_top_anchor.py`, `test_weight_rollup_v2.py`,
`test_viz3d_corrie_f.py`.

**What "default everywhere" means now.** `corrie_f.REVISION` is 3; `with revision(0 | 1 | 2):` gives the earlier revs
back exactly (tested), and BL-029's 25 mm crown straps are `crown_straps(25.0)` (67.46 g, tested). The cloth-sim run
folders follow `sim_rev()`: revs 1-3 share the rev 1 simulated shell (rev 2's port and rev 3's crown straps are
ROUTES on it), so every stored `F_r1_*` run keeps its name and new rev 3 runs land beside them. The ledger's configs
still book CORRIE B.2 (their names are quoted elsewhere); `ledger.ADOPTED_BAG` names the adopted bag (CORRIE F rev 3,
D2) and `adopted_bag_rows` books it; the roll-up reads its revision from there.

### 15.1 Weight statement (belt M, door D2, ULTRAGrid / 70D / 200X fabrics, ledger basis)

| bag side, g (oz) | base | as hunted | meat trip | pack on H1, as hunted (ledger) |
|---|---:|---:|---:|---:|
| rev 1 (BL-022) | 1110.1 (39.16) | 1319.1 (46.53) | 1451.3 (51.19) | 3620.4 |
| rev 2 (BL-028) | 1112.8 (39.25) | 1321.8 (46.62) | 1454.0 (51.29) | 3623.1 |
| rev 3 as BL-029 proposed (25 mm crown straps, section 14.2) | 1112.8 | 1380.8 | 1513.0 | 3682.1 |
| **rev 3 as adopted (20 mm crown straps)** | **1112.8 (39.25)** | **1362.4 (48.06)** | **1494.6 (52.72)** | **3663.7 (8.08 lb)** |

Rev 3 against rev 1: base +2.7 g (the B-27 ports), as hunted +43.3 g (lid 45.9 g + crown straps 49.1 g − the
2.7 L pouch and its straps). Today's fabrics: 1173.6 / 1423.2 / 1555.4 g. D1 door: 1195.2 / 1442.6 / 1574.8 g.
Ledger bag system (BAG_SYSTEM) at rev 3: 599.4 / 849.0 / 910.7 g. With the BL-005 / BL-006 packages
(`pack_with_adopted`): 3273.2 / 3561.6 / 3693.8 g.

Whole pack (`analysis/weight_rollup_v2.md`, re-run with rev 3, belt M, crown kit M): **proven now 3683.4 g base
(8.12 lb), 3969.6 g as hunted, 4101.6 g meat trip; after tests 3211.6 / 3497.8 / 3629.9 g** (rev 1 was
3680.6 / 3926.1 / 4058.2 and 3208.9 / 3454.4 / 3586.5 g). The leaders' "lid in" basis now takes the crown lid and its
straps (`weight_rollup_v2._item`, key `pouch`). 6.6 lb is still not reached (the roll-up says by how much).

### 15.2 B-28 crown strap diet

BL-029 cut the strap from the longest **sim** path (818 mm, 15 in full), but the sim never rolls the collar. With the
lid on, the top is rolled, so the cut is sized here from the strap's path over the **rolled** top with the lid (cloth
pass at 19 in, `crown_rolled_paths`), shifted by the torso change of the path from the sims (`_crown_torso_delta`:
same bag, bar at z 601 / 703 / 804).

| | day (lid on) | 6-day | full (collar standing) |
|---|---:|---:|---:|
| crown strap path, 19 in, rolled top over the lid (mm) | 413.8 | 495.7 | **830.2** |
| wrap over the lid (min of R / L) | 178° | 203° | 151° |

Torso change of the path (sims, R and L, fill and meat): +58.9 to **+97.9 mm at 15 in**, −88.8 to **−92.4 mm at
23 in**. **Longest path 928.1 mm** (15 in, full), shortest 320.6 mm (23 in, day, lid on): **607.5 mm of adjustment**.
Cut = 928.1 + 150 tail + 60 loop = **1138.1 mm (44.8 in)**, against BL-029's 1198.3 mm.

**The ticket's premise only half holds.** The rolled 6-day path is the ~505 mm BL-029 measured (495.7 mm here), but a
full bag with the collar standing puts the lid 182 mm higher (lid top z 1060 against 878) and its path is 830 mm,
longer than the sim's. So a shorter cut alone saves only 2.2 g (60 mm of webbing). The saving is in the width:

| option (pair) | cut mm | mass g | vs BL-029 | ladder lock | slip / tensile N | margin on 288 N (slip / tensile) | tail at the shortest path |
|---|---:|---:|---:|---|---:|---:|---:|
| 25 mm, rolled cut | 1138.1 | 65.29 | −2.17 | 25 mm heavy (record) | 490 / 981 | 1.70 / 3.41 | 758 mm |
| **20 mm, rolled cut (adopted in rev 3)** | **1138.1** | **49.07** | **−18.39** | ITW Classic Ladderloc 20 mm | **319 / 637** | **1.11 / 2.21** | 758 mm |
| 20 mm, cut for day / 6-day + 2 extenders for full loads | 803.6 | 39.43 (+18.91 extenders) | −28.03 (−9.12 with the extenders) | same | 319 / 637 | 1.11 / 2.21 | 423 mm |

Mass = 2 × cut × webbing g/m + 2 × (POM toggle 3.0 g + ladder lock + 60 mm front tab + the second 60 mm fold on the
25 mm B-25 tab). Loads on the strap (`crown_strap_diet()["loads"]`): crown strap at 1 g max 11.6 N on the rev 3 sims
(× 3.0 = 34.8 N), hand cinch 80 N (ASSUMPTION, the W1-W3 value), the loaded lid at 3 g 30.8 N, and as the governing
envelope the port guy's 96 N × 3.0 = **288 N**, in case a crown strap ever has to hold the top alone (it does not in
rev 3: the port guys do). 20 mm webbing break (width-scaled ASSUMPTION) 10.7 kN: margin 37.

- 20 mm passes the target (−15 to −25 g): **−18.4 g**. Its margin on the 288 N envelope is thin, **1.11 on slip**,
  and that slip is the record basis's 0.5 × the reseller's 65 kg tensile, not a measured value. On the real rev 3
  loads (80 N cinch, 35 N factored) the margin is 4.0. The B-28 slip gate (15.6) is at 288 N for that reason.
- **Tail:** with one cut for every fill and torso, the tail is 758 mm on a lid-on day load at 23 in (484 mm on a
  6-day load at 15 in). It needs managing: roll it and hold it with a webbing keeper on the strap, or take the
  extender option (owner decision 15.5). Neither keeper nor extender is drawn.
- The lid's 30 mm channels were drawn for 25 mm webbing; a 20 mm strap has 10 mm of side play in them. Left as drawn
  (BL-029's lid); the pattern-maker can narrow them to 25 mm when the lid pattern is drafted (about −1 g).

### 15.3 Lid hold on paper (`lid_hold`, loaded lid 45.9 g + 1 kg = 1.046 kg)

| case | 1 g | 3 g |
|---|---:|---:|
| inertia of the loaded lid, N | 10.3 | 30.8 |
| lid thrown outward (pack dropped on its top or swung): added tension per strap, N (wrap 203°, 2 sin(θ/2) capped at 2.0) | 2.6 | 7.7 |
| ladder lock load with the 80 N cinch, N; margin on the 319 N slip | 82.6; 3.9 | 87.7; 3.6 |
| fore-aft / side slide: friction hold μ 0.20 (m g + clamp) at the 80 N cinch, N | 66.1: **holds** | 66.1: **holds** |
| same at the relaxed tension the sims show at 1 g (5.2 N at the bar), N | 6.2: **does not hold** | 6.2: **does not hold** |
| drop on the base (3 g down) | lid bears on the roll; straps unloaded | same |

On a 6-day (203°) or day (178°, marginal) top both strap runs leave the lid downward, so a fore-aft shift has to
stretch the strap: the lid is captured, not held by friction. On a **full** top (151°) it is not: if the cinch relaxes
to what the sims show (5-18 N), a 1 g jolt can slide the lid along the straps. It cannot leave the bag (the channels
keep it on the straps, and the straps are anchored at both ends), but it can shift. Re-cinching after loading is part
of the carry routine; T9 measures how much of the 80 N cinch survives (15.6). The sim's relaxed value is at the bar,
after friction over the top, so it under-states the tension over the lid: the friction row is conservative.

### 15.4 Lid build hours (`lid_seam_list`)

A pattern-maker style check from the lid's seam list, operation by operation on the same `bag_concepts.HOURS` rates.
**8.94 h, against BL-029's 7.76 h (+1.18 h)**, and 5.64 h more than the 2.7 L pouch (3.3 h). The difference: the two
perimeter seams are closed rings and each takes the HOURS "ring" handling (2 × 0.5 h, left out in BL-029); the zip
splits the aft wall into an upper and a lower strip (10 pieces, not 9: +0.12 h); the wall ring needs two short closing
seams (+0.06 h). The two curved perimeters (989 mm each at 1.8 h/m, 3.56 h) are 40 % of the lid. This check was done
by the pack-designer (no pattern-maker agent in this run, and no drafted lid pattern yet); `build_metrics` still books
BL-029's 7.76 h until the pattern-maker confirms on the drafted B-29 pattern.

### 15.5 Renders (rev 3 drawn natively)

`huntkit/viz3d/corrie_f.py` draws rev 3 itself: outside, the port guy is only the stub from the B-25 sleeve to the B-27
port (lapped slits drawn on the frame face); no outside guys, no pouch; the B-29 lid seated on the roll and the 20 mm
B-28 straps on their taut path, ladder locks and tails at the hinge-band tabs, channels on the crown, toggles in the
bridle tabs. Lid and straps are `variant="lid"` (as-hunted add-on: an add-ons-off shot drops them). The run-time swap in
`corrie_f_rev3_viz3d.py` is retired; that script now only calls the module (and re-exports `lid_mesh`). Fixes: the lid
close-up framed a 470 mm cube around z 790, which left the bag low under empty backdrop; it now frames the bag top
(`LID_BOX`, z 590-850); the lid-open shot had the same fault and now frames the bag top and the turned-back lid (`OPEN_BOX`). The lid wall was UV-mapped from plan x, y, which stretched the camo caps into stripes; it is now
mapped by perimeter and height. Picture note: the ladder locks are drawn with the 25 mm heavy lock model.
`outputs/screens/20261112_BL030_1.png` hero (6 ft hunter, 6-day), `_2` side, `_3` lid close-up, `_4` lid open. Copies in `docs/screens/`. Whole-pack waterfall re-run: `docs/screens/20261112_rollup_1.png`.

### 15.6 Owner decisions, assumptions, gates, found not fixed

**Owner decisions needed:**
1. **Crown strap tail or extender.** One 1138 mm cut works at every torso and fill but leaves up to 758 mm of tail
   (day load, lid on, 23 in) to roll and keep. Or cut for day / 6-day loads (804 mm, 39.4 g) and carry two 435 mm
   extenders (18.9 g) for a full load with the collar standing. Recommendation: the one cut plus a sewn tail keeper
   (no part to lose in the field).
2. **20 mm crown straps** rest on a 1.11 slip margin against a load case the crown straps do not carry in rev 3 (the
   288 N guy envelope). If the owner wants the crown straps rated as a back-up top anchor, keep 25 mm (−2.2 g only).

**Assumptions that govern (new):**
- ROLL-PATH: the cloth pass's rolled top stands in for the sewn bag's, and the torso change on the rolled top equals the
  sim's on the unrolled top. Settled by T9: the cinched crown strap's free length at the S kit full and at the L kit
  6-day on the first sewn bag.
- WEB20_GM 14.4 g/m and WEB20_BREAK_N 10.7 kN (25 mm record scaled by width); LL20 slip 0.5 × 637 N and mass 3.2 g.
  Settled by weighing 1 m of the bought webbing and one lock, and by the B-28 slip gate. A materials-engineer record
  for both parts is the clean fix.
- EXT_LAP 40 mm (extender option only): settled by the pattern.
- MU_LID 0.20 (low end of the MU_WEB_FAB band): only the friction rows of 15.3 depend on it. Settled by T9's cinch
  retention reading.

**Gates (changed or new):** *(BL-031: the B-28 20 mm slip gate is dropped; the crown straps are 25 mm again on the
heavy lock, whose slip is covered by BL-010's LL-H qualification at 366 N, above the 288 N envelope; section 16.)*

| gate | settles |
|---|---|
| T9 rev 3 additions (TEST_PLAN, test register): port guys at the S kit, top full, lid on with 1 kg; crown strap cinch force with a spring scale, at cinch and after the carry; crown strap free length (S full, L 6-day); sewn lid weighed and photographed | LID-SIM, CROWN_PRE_N, ROLL-PATH, LID-SEAT, LID_SLIDER5_G, LID_THREAD |

**Found, not fixed:**
- `concepts/corrie_f_result.json` (BL-011's result file) is not regenerated; its CG and R-28 rows are from the rev 0
  / rev 1 straight-guy sims.
- No 20 mm webbing or 20 mm ladder-lock record in `data/materials/` (materials-engineer).
- The crown strap tail keeper and the extender are not drawn or booked.
- The lid channels are 30 mm wide for a 20 mm strap (15.2).

## 16. Crown straps per kit and the strap tail rule (BL-031)

pack-designer, 2026-11-12. Ticket `docs/backlog/BL-031-strap-tails.md`. Owner: crown straps stay **25 mm**; "Different
sizes. We don't want straps hanging everywhere." Code: `corrie_f.py` (`REVS[3]` `crown_w` 25 / `crown_kits`,
`crown_straps(width, kit)`, `crown_kit_straps`, `crown_kit_table`, `crown_straps_bl029`, `_crown_delta_at`,
`TAIL_RULE_MM`, `KEEPER_OVER_MM`, `TAIL_GRIP_MM`, `TAIL_KEEPER_G`); new `concepts/strap_tails.py` (the audit and its
mass rows); `huntkit/mass/ledger.py` (correction `BL031`); `weight_rollup_v2.py` (step `BL031`, A_b compensation);
`huntkit/viz3d/corrie_f.py` (`rolled_tail`, `roll_clip_tails`, `roll_clip_paths`, shot `tails`);
`huntkit/viz3d/cloth_pass.py` (records each roll-clip path length). Data: `corrie_f_sim/corrie_f_roll_clips.json`
(`python -m huntkit.viz3d.corrie_f --roll-clips`). Tests: `tests/test_strap_tails.py` (new) plus updated asserts in
`test_corrie_f_adopt_rev3.py`, `test_corrie_f_top_anchor.py`, `test_corrie_f.py`, `test_mass_ledger.py`,
`test_weight_rollup_v2.py`, `test_viz3d_corrie_f.py`. BL-030's 20 mm diet stays callable as history
(`crown_straps(20.0)`, `crown_strap_diet()["chosen"]`).

### 16.1 The rule

- **TAIL RULE (DECISION):** the free tail past every adjuster is **≤ 100 mm (4 in) at the most-used setting**: 6-day
  load (45 L), mid torso of the crown kit, mid waist of the belt size, tripod on (as hunted) for W1 / W2.
- **KEEPER RULE (DECISION):** any strap whose tail can pass **150 mm (6 in)** at some setting carries a keeper (a
  25 mm elastic loop that slides on the strap and holds the rolled tail, or the gore-seam keeper loops W1–W3
  already have).
- **Grip:** every cut leaves **50 mm (2 in)** of tail at its longest path (ASSUMPTION TAIL_GRIP: two gloved finger
  widths + 10 mm; settled by a gloved cinch trial in T9).

### 16.2 B-28 crown straps per crown kit (25 mm, a heavy ladder lock at each end)

Paths from BL-030's rolled-top cloth pass (19 in, day / 6-day / full with the collar standing), moved to each kit's
own torso range by the sim's torso change, interpolated linearly between 15 / 19 / 23 in (ASSUMPTION TORSO-LIN).
Cut = longest path + 2 × 50 mm; the two locks (front on the hinge-band tab, rear on a tab through the POM toggle in
the B-25 second fold) share the take-up, so each tail = 50 + (longest − path) / 2.

| kit (torso) | longest path (full, short end) | shortest (day, long end) | 6-day mid torso | **cut** | tail 6-day mid (each end) | worst tail (day, long end) | pair mass |
|---|---:|---:|---:|---:|---:|---:|---:|
| S (15–18 in) | 928.1 | 427.7 | 543.3 | **1028 mm (40.5 in)** | 242 mm (9.5 in) | 300 mm (11.8 in) | 79.9 g (2.82 oz) |
| M (17.5–20.5 in) | 866.9 | 378.4 | 495.7 | **967 mm (38.1 in)** | 236 mm (9.3 in) | 294 mm (11.6 in) | **77.7 g (2.74 oz)** |
| L (20–23 in) | 808.0 | 320.6 | 438.8 | **908 mm (35.7 in)** | 235 mm (9.2 in) | 294 mm (11.6 in) | 75.6 g (2.67 oz) |

Tails at the other settings (kit M, each end): full 54 / 68 / 86 mm at the kit's short / mid / long torso; 6-day
221 / 236 / 253 mm; day 263 / 277 / 294 mm. **The crown straps do not meet the 100 mm rule at the 6-day setting,
in any kit.** The spread is the lid's own height range: the path over a full bag with the collar standing is 830 mm
against 496 mm on a 6-day top (CROWN_ROLLED), and per-kit sizing only removes the torso part of the range (BL-030's
single cut left 582 mm of tail at the 6-day, 700 mm worst). Two locks halve what is left; the rest is rolled into a
keeper at each lock (drawn, 21 mm roll). The one-lock version (rear sewn toggle loop) is 17 g lighter (60.7 g at M)
but leaves 421 mm at the 6-day and 539 mm worst at M. Load: the heavy lock's 490 N slip (record basis) on BL-030's
288 N envelope gives **1.70** (same as BL-029's), webbing 46; the B-28 20 mm slip gate (15.6) is dropped.

Against BL-030's 20 mm straps (49.1 g) the kit-M pair is **+28.6 g as hunted**; against BL-029's 25 mm single cut
(67.5 g) +10.2 g (two more locks, two more tabs, four keepers, a shorter cut). Ledger books kit M.

**BL-039 (2026-11-13): 40 mm spare on every kit.** The cuts above equal the longest simulated path + 2 × 50 mm grip:
zero spare, so any path longer than the sim (ROLL-PATH, TORSO-LIN: the per-side / per-case delta at 15 in already
spreads 58.9–97.9 mm; tab fold ± 5 mm) eats the gloved grip. Cut = longest + **40 mm** (CROWN_SPARE_MM, ASSUMPTION
CROWN-SPARE, settled by T9-R3c) + 2 × 50 mm, for S, M and L alike (all three had the same zero spare). Each tail gains
20 mm; the keepers stay (every worst tail was already over 150 mm). Live values from `corrie_f.crown_kit_table()`:

| kit (torso) | longest path | path limit (cut − 2 grips) | **cut** | tail 6-day mid (each end) | worst tail | pair mass |
|---|---:|---:|---:|---:|---:|---:|
| S (15–18 in) | 928.1 | 968.1 | **1068 mm (42.1 in)** | 262 mm (10.3 in) | 320 mm (12.6 in) | 81.7 g (2.88 oz) |
| M (17.5–20.5 in) | 866.9 | 906.9 | **1007 mm (39.6 in)** | 256 mm (10.1 in) | 314 mm (12.4 in) | **79.5 g (2.81 oz)** |
| L (20–23 in) | 808.0 | 848.0 | **948 mm (37.3 in)** | 255 mm (10.0 in) | 314 mm (12.4 in) | 77.4 g (2.73 oz) |

Kit M tails (each end): full 74 / 88 / 106 mm at the short / mid / long torso; 6-day 241 / 256 / 273; day 283 / 297 /
314. +1.44 g a pair as hunted (2 × 40 mm of 25 mm webbing); base mass unchanged (the crown straps are as hunted).
The table above this note is BL-031's and is kept as history; its mass column predates BL-034's keeper re-weigh.

**Option that meets the rule outright (owner decision 16.6-1):** cut each kit for day and 6-day only and add a
25 mm extender for a full load with the collar standing (as BL-030's 20 mm extender option, at 25 mm). Each tail is
then ≤ 100 mm at the 6-day and no keeper is needed, at the cost of a loose part to carry.

### 16.3 Audit of every adjustable strap (belt M, crown kit M; tail per adjuster, mm)

| strap | path source | cut before → after | 6-day tail before → after | worst tail before → after | tail management after | rule |
|---|---|---:|---:|---:|---|---|
| B-28 crown straps (2) | cloth pass + sims | 1138 (20 mm) → 967 | 582 → 236 | 700 → 294 | elastic keeper at each lock | keeper |
| load lifters (2) | crown settings: 140 / cos 40.6° = 184 mm; ±let-out / cinch (ASSUMPTION) | 450 → **340** | 206 → **96** | 236 → 126 | tri-glide keeper (kept) | **meets** |
| sternum (each side) | strap gap 100 / 150 / 220 mm (ASSUMPTION) | 400 → **170** | 315 → **85** | 340 → 110 | none needed | **meets** |
| hip stabilizers (2) | 140 mm at M ± 30, grades with the wing (ASSUMPTION) | 400 → **280** (S 260, L 295, XL 310, XXL 330) | 200 → **80** | 230 → 110 | none needed | **meets** |
| hipbelt 2:1 pull (each side) | `hipbelt_diet.closure` | tail at max waist 150 → **50** | 201 → 101 | 252 → 152 | elastic keeper on the wing tip | keeper (1 mm over; the 2:1 doubles the 51 mm leg range; XXL 114 / 178) |
| W1 | geometry.yaml carry / haul; tripod +70, day −200 (ASSUMPTIONS) | 1340 → **750** | 640 → **50** | 910 → 320 | 2 gore keeper loops (kept) | **meets** (bow hunt, no tripod: 120) |
| W2 | same | 1412 → **822** | 640 → **50** | 910 → 320 | same | **meets** (no tripod: 120) |
| W3 (kit M; S 1034, L 935) | same + crown torso change | 1618 → **987** | 710 → **79** | 944 → 313 | same | **meets** |
| IM1 / IM2 / IM3 | geometry.yaml; most used = stowed port to port (280 mm) | 990 / 1023 / 1083 unchanged | 590 / 623 / 683 | same | elastic keeper at each cam | keeper |
| US1 / US2 | meat_haul cradle 269 mm; bag-on path not modelled | 550 unchanged | 221 (cradle) | 221 | tri-glide keeper (kept) | keeper |
| roll-top clips (2) | `corrie_f_roll_clips.json`: day 166, 6-day 180, full 375 mm | 350 → **510** | 85 → 245 | 99 → 259 | elastic keeper below each buckle | keeper |
| port guys (inside) | attach_system | unchanged | 100 | 100 | elastic keeper (kept) | meets |
| torso pull strap (d2) | ±1.5 in per kit on 1:1 | cut rule: grip at the kit's longest setting | 88 | 126 | none needed | meets |
| B-24 links; B-25 bridle; B-26 cord; shoulder straps; bow riser strap | no adjuster / sewn loops | – | 20 / 0 | 20 / 0 | – | meets |

**Every adjustable strap now meets the rule at the most-used setting or has a keeper** (`strap_tails.audit` →
`all_pass`). Nine strap types meet the 100 mm rule outright; the crown straps, the belt 2:1, IM1–IM3, US1 / US2 and
the roll clips rely on a keeper. **Found on the way:** the 350 mm roll-clip cut does not reach a full bag with the
collar standing on the cloth-pass roll (375 mm path against 260 mm of webbing): the clip strap goes to 510 mm.
W1–W3 were cut for the meat haul and carried 640–710 mm of tail on every hunt: they are now cut for carry, and the
meat haul, float clamp and antler / cape lash take **three 740 mm haul extenders** in the meat-trip kit (25 mm, a
sewn loop for the W's own G-hook and a rated 25 mm G-hook to the lash point; at the 225 N float clamp × 1.5 proof,
the G-hook no-set 900 N and a 25 mm box-X 1776 N (strap_arch ASSUMPTION) hold with margin ≥ 2.6).

### 16.4 Mass (belt M, crown kit M, D2, B fabrics; ledger basis)

| change | cfg | g |
|---|---|---:|
| W1–W3 cut for carry | base | −32.6 |
| W1–W3 haul extenders (3) | meat trip | +64.0 |
| IM1–IM3 tail keepers (3) | base | +1.8 |
| roll-clip straps 350 → 510 mm (2) | base | +5.8 |
| roll-clip tail keepers (2) | base | +1.2 |
| B-28 25 mm per kit vs BL-030 20 mm | as hunted | +28.6 |
| lifters, sternum, stabilizers cut to length (ledger `BL031`) | base | −16.6 |
| belt 2:1 tail 150 → 50 mm, 2 keepers (ledger `BL031`) | base | −2.4 |

Bag side (D2): **base 1089.0 g (38.41 oz), as hunted 1367.2 g, meat trip 1563.3 g** (BL-030: 1112.8 / 1362.4 /
1494.6). D1: 1171.4 / 1447.4 / 1643.5 g; D1's meat trip is now 17.9 g over CORRIE B.2's (the extenders).
Whole pack (`weight_rollup_v2.md`, re-run): **proven now 3640.6 g base (8.03 lb), 3955.4 g as hunted, 4151.4 g meat
trip; after tests 3173.1 / 3487.9 / 3684.0 g** (BL-030: 3683.4 / 3969.6 / 4101.6 and 3211.6 / 3497.8 / 3629.9). The
after-tests stabilizer deletion (BL-006 b) takes the shortened straps, so BL-031's stabilizer saving is not counted
twice.

### 16.5 Assumptions that govern (new)

- TAIL_GRIP 50 mm: T9 gloved cinch trial (5 users, winter gloves, each strap at its longest setting).
- TORSO-LIN (crown path linear in torso between the sims): T9 free length at both ends of each kit.
- TAIL_KEEPER_G 0.6 g (attach_system's guy keeper): weigh 10 cut keepers. **BL-034: now 1.35 g from the `elastic_25mm` record (15 g/m x 90 mm); section 17.**
- Lifter let-out 50 / cinch 30 mm, sternum gap 100–220 mm and buckle 60 mm, stabilizer path 140 ± 30 mm: T9 lifter
  readings, the R-06 fit trial (≥ 3 men, ≥ 3 women), HB-D1.
- W_DAY_SQUEEZE 100 mm and W_TRIPOD 70 mm (W paths on a day load and over the tripod): T9 W free lengths.
- ROLL-CLIP-PATH (the cloth-pass roll stands in for the sewn roll): T9 clip free length at the three loads.
- The W carry / haul paths are geometry.yaml's (v3.1 teardrop), as CORRIE F has always booked them; not re-measured
  on S15.

### 16.6 Owner decisions, renders, found not fixed

**Owner decisions needed:**
1. Crown straps: keep one cut per kit with a lock at each end and rolled tails in keepers (as built, 77.7 g at M), or
   cut for day / 6-day and carry a 25 mm extender for the full-with-collar-standing load (meets the 100 mm rule with
   no keeper; one more loose part).
2. W1–W3 haul extenders in the meat-trip kit (−32.6 g base, +64.0 g meat trip), against today's one long cut with
   640–710 mm of tail on every hunt.

**Renders** (`huntkit/viz3d/corrie_f.py`, crown kit M at 19 in): `outputs/screens/20261112_BL031_1.png` hero on the
6 ft hunter (6-day), `_2` lid close-up (25 mm straps, a lock at each end, tails rolled in keepers), `_3` the worst
remaining tails (crown strap front lock and roll clip, both rolled in keepers). W1–W3 tails are not drawn (they never
were); at the 6-day they are 50–79 mm.

**Found, not fixed:**
- D1's lid straps H1–H3, the lumbar pad-seat strap and cord-lock tails are not audited (D1 is not the default; the
  pad-seat strap path is not modelled and BL-006 f1 replaces it after HB-D3).
- The under-strap bag-on path is not modelled anywhere (meat_haul has only the cradle).
- The shoulder straps have no lower webbing adjuster in any file (DESIGN.md 5.3: fixed to the z 110 anchor); fit
  rides on the crown kit alone. Fine if intended; worth a line in the fit trial.
- `corrie_f_result.json` is still BL-011's (as noted in 15.6).

## 17. BL-034 part A: rev 3 package cleanup (pack-designer, 2026-11-13)

### 17.1 What changed in the bag's numbers

Every figure below comes from code: `huntkit.mass.ledger.adopted_bag_rows` (= `corrie_f.parts`, rev 3, D2, crown kit M,
team B fabrics), `weight_rollup_v2.py --write` and `build_effort_rev3.py --write`.

| Change | Source | base g | as hunted g | meat trip g |
|---|---|---:|---:|---:|
| #10 door sliders 2 x 6 -> 2 x 19.0 g | `slider_10` record via `bag_concepts.SLIDER_G` | +26.0 | +26.0 | +26.0 |
| US1/US2 backstop tri-glides -> stainless 25 mm, 2 x 11 g, 3.75 kN (orchestrator: stops cradle slip) | `triglide_25mm` stainless_alt; `meat_haul.cradle_parts_g` | +16.0 | +16.0 | +16.0 |
| #5 sliders 3.0 -> 4.9 g (IMP-4; lid and F-02 as hunted) | `slider_5` via `corrie.SLIDER5_G`, `LID_SLIDER5_G` | +1.9 | +5.7 | +5.7 |
| 25 mm elastic keepers 0.6 -> 1.35 g (IM x3, roll clip x2, guy x2; crown strap x4 as hunted) | `elastic_25mm` 15 g/m x 90 mm, `TAIL_KEEPER_G` | +5.25 | +8.25 | +8.25 |
| POM toggles 3.0 -> 1.7 g (guy bar loops x2; B-28 rear x2 as hunted) | `pom_toggle`, `attach_system.TOGGLE_G` | -2.6 | -5.2 | -5.2 |
| nylon tri-glides 3.0 -> 2.6 g (guy x2, lifter keepers x2) | `triglide_25mm`, `attach_system.TRIGLIDE_G` | -1.6 | -1.6 | -1.6 |
| thread from the op stitch lengths (no cone waste) replaces the 2 + 2 g rows | `build_effort_rev3.json` | +9.6 | +14.35 | +14.29 |
| **Bag side, net** | | **+54.55** | **+63.5** | **+63.44** |

Bag side (D2): **base 1119.8 g (39.50 oz), as hunted 1400.3 g (49.39 oz), meat trip 1596.3 g (56.31 oz)** (before:
1065.2 / 1336.8 / 1532.9). The hipbelt's two BL-031 tail keepers move +1.5 g on the suspension side.

Whole pack (`weight_rollup_v2.md`, belt M): **proven now 3687.7 g base (8.13 lb), 4004.9 g as hunted (8.83 lb),
4200.9 g meat trip (9.26 lb); after tests 3217.6 / 3534.8 / 3730.8 g (7.09 / 7.79 / 8.23 lb)** (BL-033: 3640.6 /
3955.4 / 4151.4 and 3173.1 / 3487.9 / 3684.0). The 6.6 lb base target is now 224 g away after tests (694 g proven now).

### 17.2 Build hours and thread (`build_effort_rev3.py`)

The ledger and `build_metrics` now book the operation sequence of the released package (`mfg_corrie_f_rev3.ops`),
which counts the webbing parts, the drafted lid and the drafted fly:

- **Beginner hours: 70.8 h a bag** (base 50.7 h, as hunted 16.6 h, meat trip 3.5 h) **+ 4.1 h one-off set-up** (test
  square, swatches, first-article load samples). The HOURS body model gave 44.5 h (kept as
  `beginner_hours_hours_model` for the competition comparisons). D1 is the D2 sequence plus its HOURS-model shell
  difference: 72.2 h.
- **Thread in the bag: 18.3 g** (base 11.6, as hunted 4.75, meat trip 1.9): op stitch length x 2.75 (ASSUMPTION
  THREAD-FACTOR) x the bonded nylon tex 70 / 90 / 135 records. The BOM's 21.5 g "in the bag" includes the 15 % cone
  waste (not in the bag) and three ops the package sews twice (IME, T3, LLT: 0.9 g, 1.2 h); both are left out here.

### 17.3 Pattern marks (`patterns_corrie_f_rev3.py`, release `patterns/pattern_checks.md` section 8)

- **B-11 lash tabs, 4 per gusset (8 a bag)**, ASSUMPTION B11-PLACE: bow riser / lash tabs stacked at z 470 and 560,
  40 mm forward of the aft corner seam (the cam sits in IMP-8 at the right gusset's aft foot; on the left gusset the
  same marks are antler / cape lash points); muzzle keeper tabs side by side at z 650, 60 and 130 mm aft of the frame
  seam (a keeper loop runs between them round the barrel). Clear of FP (top z 380), the B-26 cord (z 600), the IMP-2
  hose slot (z 680-720 at the frame seam), W3 (z ~703) and the hard-point loops. Settled by the archery and rifle fit
  checks. Releases op 4.07.
- **DECISION B28-FACE: the B-28 front lock tab goes on the OUTSIDE of the hinge band**, box-X 21 x 20 (the B-28t box,
  sewn through tab and band in one pass), centre 15 mm under the lock bar at z 700. The crown strap's taut path
  (`crown_path`, the T9 route) comes over the lid and down the band's outer face; an inside tab would drag the strap
  through the band. A 25 x 25 box would run off a 25 mm tab.
- Box-X drawn: W3 (21 x 25, per kit), IM1-IM3 end loops (21 x 25, 60 mm fold), US eyes (21 x 25, 50 mm fold,
  ASSUMPTION US-EYE), B-24 from `attach_system.link_piece` (34 x 30 hook + 3 x 34 x 20 loops at the 120 / 170 / 220 mm
  stations; the earlier piece had folds at the gap values, not the loop stations).
- **DECISION B25-BOX: 21 x 15** at the tip end of each B-25 toggle tab, so the 2 x 30 mm tab keeps a 13 mm loop that
  passes the 30 x 8 x 5 POM toggle (26 mm perimeter); 21 x 20 would leave 8 mm. Capacity 2504 N against 288 N.
  B-25 layout (ASSUMPTION B25-LAYOUT): tab | bar sleeve | run + spine wrap | bar sleeve | tab.
- K-W keeper notches on the aft corner seams where each wrap crosses it (ASSUMPTION KW-PATH, geometry.yaml anchors):
  W1 R z 128 / L z 202, W2 R z 300 / L z 370, W3 z 703 both sides. The BL-032 package had assumed z 80 / 250 / 420
  (the frame anchor heights).
- F-02 placement drawn on B-05 (outside, centred, zip edge aft).
- Door D1: the three self-paired placeholder seams are real pairs (gusset aft edge split at the zip corner tangent
  z 590). The legs and band tongues match to 0.0 mm; the zip seam is 6.0 mm long on the lid side, which is team C's
  3 mm-a-side lid ease (`tailgate.LID ease_mm`), as is the hinge seam's 6.0 mm.


## 18. BL-035: record masses everywhere, small pattern and ledger fixes (pack-designer, 2026-11-13)

### 18.1 Constants moved onto the records (one mass basis)

| Constant | Was | Now | Source |
|---|---:|---:|---|
| `crown_diet.CAM_G` + `build_geometry` torso-adjust cam | 12 g | 12.2 g | `cam_25mm_al`; no pull tab (ASSUMPTION TA-CAM: set once per fit, bag off) |
| `crown_diet.TOGGLE_G` + torso-adjust release toggle | 3 g | 1.7 g | `pom_toggle` |
| torso-adjust row (`TORSO_ADJUST_ROW_G`, now computed) | 41.7 g | 40.6 g (1.43 oz) | web 25.2 + cam 12.2 + cord 1.5 + toggle 1.7 |
| `bag_attach` lifter tri-glide keepers | 2 x 3.0 g | 2 x 2.6 g | `triglide_25mm` |
| `bag_attach` "elastic keepers" (6 hook keepers) | 6 x 0.6 g | 6 x 1.35 g | `elastic_25mm` 15 g/m x 90 mm cut (ASSUMPTION, = `TAIL_KEEPER_CUT_MM`) |
| `strap_arch.CAM25_G` (IM1-IM3, US1/US2) | 13.0 g | 13.2 g | `cam_25mm_al` 12.2 g + 1 g glove pull tab (ASSUMPTION CAM-TAB) |

`bag_attachment_results.json` was re-booked with `python -m huntkit.gendesign.bag_attach --refresh-mass` (mass budget
only, FEA rows unchanged), then `geometry.yaml` (`build_geometry.py`), the bag-competition `result.json` files and
`crown_diet_results.json` were re-run.

`corrie.weight_table` gets one new row, **SPINE shared rows re-booked on material records since 2026-11-09**
(`spine_rebooked_g` = geometry.yaml total - 3523.7 g, now +18.6 g). Without it the ledger's booking reconciliation
row (which should be about 1 g) absorbed the BL-034 stainless US tri-glides and the BL-035 rows (-17.4 g).

### 18.2 What moved (belt M)

| Quantity | Before | Now | Delta and why |
|---|---:|---:|---|
| CORRIE B.2 on today's frame (ledger) | 3982.9 | 4029.5 | +26.0 #10 door sliders, +16.0 stainless US tri-glides, +1.9 IMP-4 #5 slider (BL-034); +4.5 hook keepers, -0.8 lifter tri-glides, -1.1 torso adjust (BL-035) |
| CORRIE B.2 on H1 (ledger, crown diet basis) | 3927.0 | 3973.5 | same +46.5 |
| BL-008 B.2 base / as hunted | 3700.4 / 3872.4 | 3747.1 / 3919.1 | same +46.5 (B-24 54.4 unchanged) |
| CORRIE B.2 bag system (bag-comp metric) | 710.6 (A), 716.5 (lean) | 738.5, 744.4 | +26.0 door sliders + 1.9 IMP-4 slider |
| CORRIE B.2 body group | 533.1 | 559.1 | +26.0 door sliders |
| Team D bag system | 991.0 | 1017.0 | +26.0 its door sliders |
| Team B FELL (max) | 583.1 | 598.0 | +13.0 one #10 slider in its body, +1.9 A3 lid pod #5 slider |
| BL-017 (d1) pulley delete | -45.2 | -45.4 | cam 12.0 -> 12.2 |
| BL-029 B-28 (history) | 67.46 | 64.86 | 2 toggles 3.0 -> 1.7 g (moved on purpose: one basis; the 67.46 g booking is reproduced in the test as 64.86 + 2 x 1.3) |
| BL-004 REC with heavy guy locks | 218.1 (after BL-034) | 220.3 | keepers +3.0, lifter tri-glides -0.8; still over the 220 g bar by 0.3 g |
| BL-003 REC saving with the 14 g hook fallback | 200.5 | **199.5** | 5 cams x +0.2 g: **the fallback now misses 200 g by 0.5 g** (history; REC adopted, fallback only if the 25 mm hook fails 910 N) |

### 18.3 Adopted bag (CORRIE F rev 3, D2, team B fabrics, crown kit M)

- +1.0 g IM/US cams (5 x 0.2), +3.0 g hook keepers (4 left after BL-004 REC x 0.75), +8.7 g **rifle muzzle keepers**
  (new row, `corrie_f.muzzle_keeper`): one 3 mm shock-cord loop per gusset through the two B-11 muzzle tabs (70 mm
  apart), round the barrel, closed by a spring cord lock. Cut 309 mm = 70 + 2 x 40 stand-off + pi x 25 barrel + 2 x 40
  tails (ASSUMPTION MUZZLE-CORD, settled by the R-18 rifle fit check), 4.35 g each.
- Bag side: **base 1132.6 g (39.95 oz), as hunted 1413.1 g (49.85 oz), meat trip 1609.0 g (56.75 oz)** (BL-034:
  1119.8 / 1400.3 / 1596.3), after `build_effort_rev3.py --write` on the part C package (thread base 11.6 -> 11.7 g,
  as hunted 4.75 -> 4.63 g; beginner hours 70.8 -> 70.5 h a bag: part C removed the duplicate ops from the package and
  the duplicate-op heuristic from `build_effort_rev3`, reviewed: `duplicates` is empty and B-28s / MK-cord are sewn by
  their own step-7 ops).

### 18.4 Whole pack (`weight_rollup_v2.md`)

The bag's thread was booked twice: CORRIE F books it from the op stitch lengths (BL-034) and the misc line still held
3 % of the B.2 bag's soft goods. `build_geometry` now writes the split (`weight.misc_thread`: bag 15.0 g, suspension
19.2 g, labels 8 g); `weight_rollup_v2.corrie_f_step` removes the bag share with the B.2 bag (misc 43.5 -> 28.5 g).

**Proven now 3684.7 g base (8.12 lb), 4001.8 g as hunted (8.82 lb), 4197.8 g meat trip (9.25 lb); after tests
3214.1 / 3531.2 / 3727.2 g (7.09 / 7.78 / 8.22 lb)** (BL-034: 3687.7 / 4004.9 / 4200.9 and 3217.6 / 3534.8 / 3730.8).
P base -3.0 g (-3.1 before the build-effort refresh, +0.1 thread) = misc thread -15.0, muzzle keepers +8.7, hook keepers +4.5 (P keeps all 6 until PT-1), torso adjust
-1.1, (d2) cam -0.2; the lifter tri-glides net 0 (BL-034 had already applied 2.6 g as a record row). After tests -3.6 g:
also 25 mm cams +1.0 and REC removes 2 of the heavier keepers -1.5. The 6.6 lb base target
is 220 g away after tests (691 g proven now).

### 18.5 Pattern fixes (release `patterns/pattern_checks.md` 8.2)

- **B-28t split.** B-28t is now the 4 lock tabs (front on the hinge band, rear carrying the POM toggle), box 21 x 20.
  The B-25 second fold the rear toggle enters is its own piece **B-28s** (2), box **21 x 15 at the tip end**: the folded
  loop is 13 mm, which passes the 30 x 8 x 5 toggle (26 mm perimeter). The old 21 x 20 box at 0.75 x tab left 5 mm.
  ASSUMPTION B28-TOGGLE: the rear tab carries the toggle sewn across its tip (corrie_f says "the POM toggle into the
  second fold of the B-25 tab"); settled by the T9 fit and TL-1 toggle-loop pull.
- **LLT box.** The B-02h "B-22 / guy LLT" mark is 21 x 25 (`LLT_BOX`), the same box as the LLT piece (was 25 x 25).
- **B-24 boxes.** DECISION B24-BOX: the drawn boxes are the capacity basis. `attach_system.LINK_HOOK_BOX` 34 x 30
  (fits inside the 45 mm hook fold; a 38 x 38 box runs off the 38 mm webbing and onto the hook bed) and
  `LINK_LOOP_BOX` 34 x 20. Box-X capacity 4430 N (hook) and 3786 N (loops) against the 941 N misuse load; the 2200 N
  rated hook still governs.
- B-28t / B-28s labels shortened and the webbing screenshot reordered, so no label covers the B-24 hook box.

## 19. BL-036: small cleanups after BL-034/035 (pack-designer, 2026-11-13)

### 19.1 Attachment boxes and the tri-glide booking

- **B-24** in `attach_system_results.json`, `bag_attachment.md` and `cut/attachment/README.md` now reads the drawn
  boxes (hook box-X 34 x 30, loops 34 x 20; capacities 4430 / 3786 N, hook 2200 N governs, SF 2.34 unchanged).
- **B-22** was checked on a 25 x 25 box-X. The box that holds it is the LLT box, sewn through LLT + B-22 + B-02d in
  one pass on 25 mm webbing: 21 x 25 (`attach_system.LLT_BOX`, = `patterns_corrie_f_rev3.LLT_BOX`). Capacity
  3458 -> 3186 N against a 112 N factored guy; the 50 mm perimeter seam (1024 N) still governs, SF 9.15 unchanged.
  The B-22 drawing in `attachment_parts.pdf/.dxf` shows the same 21 x 25 box.
- `python -m huntkit.gendesign.attach_system --refresh` now also re-books the phase mass rows on today's records
  (`mass_delta`: `triglide_25mm` 2.6 g, `pom_toggle` 1.7 g). Guy lock row 16.5 -> 15.7 g, hood tongues + toggles
  10.3 -> 7.7 g, phase delta 131.5 -> 128.1 g. `corrie_f.BOOKED_TRIGLIDE_G` = 2.6, so the BL-034 guy tri-glide row is
  0.0 (was -0.8): the tri-glides are corrected once.

### 19.2 Misc thread

- `build_geometry` counted the thread of both harness strap sets (harness_J + harness_S); the pack carries the J set.
  harness_S is out of the thread base (`weight.misc_thread.excluded_g`): misc 42.2 -> 39.5 g (-2.7 g).
- `corrie_f.weight_table` (and so `pack_with_adopted`) now takes the bag share of the misc thread line
  (`misc_bag_thread_g`, 15.0 g) out of CORRIE F's pack, as `weight_rollup_v2.corrie_f_step` does: CORRIE F on H1 base
  3394.0 -> **3376.3 g** (-15.0 thread, -2.7 S-strap thread), with adopted packages 3291.9 -> 3274.2 g.

### 19.3 What moved (belt M)

| Quantity | BL-035 | BL-036 | Why |
|---|---:|---:|---|
| CORRIE B.2 on H1 (ledger) | 3973.5 | **3967.4 (8.75 lb)** | -2.6 hood toggles, -0.8 guy tri-glides (records), -2.7 S-strap thread |
| CORRIE F bag side base / as hunted / meat trip | 1132.6 / 1413.1 / 1609.0 | same | the tri-glide and toggle rows only moved from the correction rows into the ledger rows |
| Proven now base / as hunted / meat trip | 3684.7 / 4001.8 / 4197.8 | **3679.4 / 3996.5 / 4192.5** (8.11 / 8.81 / 9.24 lb) | -2.6 hood toggles (P keeps the hood), -2.7 S-strap thread |
| After tests | 3214.1 / 3531.2 / 3727.2 | **3211.4 / 3528.5 / 3724.5** (7.08 / 7.78 / 8.21 lb) | -2.7 S-strap thread (A deletes the hood, so its toggles net out) |
| BL-004 REC step (A_att) | -107.1 | -104.5 | the hood toggles it deletes are 1.7 g now |
| Crown diet: recommended pack at M | 3879.9 | 3873.8 | ledger basis; savings 112.6 / 93.6 / 74.6 g unchanged |
| BL-004 REC attachment with heavy guy locks | 220.3 | **219.5** | guy tri-glides on the record (attach_diet had kept 3.0 g): **now meets the 220 g bar by 0.5 g** |

The 6.6 lb (2993.7 g) base target is **218 g** away after tests (686 g proven now).

### 19.4 Stale numbers and tags

- `bag_weight_plan.py` / `.md` marked HISTORICAL (the 2026-11-05 plan; its 12.0 g cam is that day's ASSUMPTION, the
  record is 12.2 g). Not re-run.
- Bag-competition write-ups (A, C, D, form, lean) and the verdict carry a "masses superseded" note with today's
  `result.json` / `ledger.teams()` numbers. Team E's `form_numbers.json` and `result.json` were re-run (BL-035 had
  missed them: bag system 739.3 -> 767.2 g, CORRIE B.2 721.7 -> 749.6 g, pack unchanged 3960.6 g).
- `crown_diet_results.json` re-run on the new ledger; `crown_diet.md` notes that its table masses are superseded.
- `mfg_corrie_f_rev3.py`: the volatile op tags read `pattern: <value>` (was `BL-033 <value>`), RD-16 / RD-23 texts no
  longer cite BL-033 as pending, two unused locals and one placeholder-free f-string removed.

## 20. BL-040: pre-cut review fixes (pack-designer, 2026-11-13)

Source: `review_20261113_rev3_release.md` (3 blockers, 13 majors, 21 minors). Code: `patterns_corrie_f_rev3.py`,
`mfg_corrie_f_rev3.py`, `physical_test_kit.py`; sketches SK-8 (hinge eye), SK-9 (aft corner keeper stack), SK-10
(roll-top clip) in the manufacturing release.

- **DECISION HE-ONE (B-1).** One hinge eye: HE 38 x 150 mm folded in half (eye fold at 75 mm), both raw ends on the
  B-01 cut edge, so the floor seam catches both plies; box-X 34 x 34 mm (38 mm webbing less 2 mm a side), its lower
  edge 4 mm above the floor seam line (ASSUMPTION HE-GAP), through HE (2 plies) + B-01 + B-18. Free eye 25 mm. Neck:
  each long edge folded 10 mm in (18 mm, the fairlead throat), one BT-M per leg, sewn flat before the fold. B-18 is
  90 x 62 mm (was 90 x 45), z -12 to +50 about the floor seam line, rows on the top and sides only. The same box is
  drawn on HE, B-18 and B-01, and `box_mismatches` now checks every webbing / panel stack. Load 1019 N factored
  (load_standard rev C), SF 2.31 on the B-18 seam; PT-3 1530 N on specimens sewn as op 4.05.
  ASSUMPTION HE-REACH: the 25 mm free eye (box top 38 mm, fold 63 mm above the seam line) reaches the z 60 pin
  (25 mm above the floor seam line, frame z); settled by QC-20. Alternative not taken: the eye pointing down past the
  floor (needs the tail out of the floor seam).
- **DECISION RT-MATE (B-2).** RTM tab (25 mm x 70, folded round the female buckle bar, box-X 21 x 25) on each gusset
  at mid depth, 150 mm under the collar seam (the cloth-pass roll model's clip tab, `corrie_f_roll_clips.json`); the
  RT strap's first 60 mm box-X'd (25 x 21) on the flat hem B-07 on the frame-side half of each gusset, free end
  through the adjustable male half. Unrated (hand cinch). ASSUMPTION RT-HEM (strap height on the hem). New ledger
  gap: 2 RTM tabs (2 x 70 mm of 25 mm webbing) are not booked.
- **B-3 / KW-OVER-FP.** Keepers L z 202 (W1), R z 300 (W2), L z 370 (W2) sit on the FP aft edge. Op 4.13 states the
  stack (gusset, FP mesh edge, K-W loop, blade U), sketch SK-9; the FP aft edge is basted in the allowance only. The
  pack-designer confirms W1 / W2 are meant to cinch OVER the hip pockets in haul mode (the pocket mouth stays
  reachable under a strap); moving FP 10 mm forward was rejected because it eats the 9 mm frame-seam clearance.
- **DECISION GUY-LOCK-IN (M-5, option a).** The guy ladder lock stays on LLT at B-22 inside the hinge band; PORT-1's
  gloved check is done there. Option b (lock outside at the port, LLT deleted) was not taken: it needs a new
  B-01 tab and a re-run of the guy-path sim.
- **Collar ring (M-3).** The ring now runs one way round the bag; the gusset carries one notch set (50 / 100 mm from
  the frame end + the two corners).
- **Levels (M-7, M-8, M-9).** LL-H 432 N (1.5 x 288 N) dry, wet and cold; MT-3 dry, wet and cold; SEW-F (box-X
  fatigue, 3 loops, 38 -> 384 N, 1e5) added to the G4 lever rig.
- **Mass (M-6).** QC-14 is now on the primary fabrics: ledger + the primary pattern delta per kit (base +64.1 g).
  B-18's growth adds 3.1 g of Hypalon the ledger does not yet book.
- **Colourway (orchestrator 2026-11-13).** The pack body is Krummholz Sage #6E745B, now the named primary pairing
  `krummholz` in `designs/apparel/colorways.yaml` (Owner Base accents, Deadfall Shadow trim, Elk Wallow harness);
  `huntkit.viz3d.export.colorway` reads it (no hard-coded fallback in use) and the BOM names it on every coloured line.


## 21. BL-041: re-check fixes (pack-designer, 2026-11-13)

Source: `review_20261113_rev3_recheck.md` (2 blockers, 5 majors, 15 minors) and the structural result
`crown_tube_guy_loop.md` (Y-4, adopted by the orchestrator). Code: `patterns_corrie_f_rev3.py` (`he_geometry`,
`he_pin_z`, `rt_layout`, `rt_clearances`), `mfg_corrie_f_rev3.py` (`he_405_text`, `box_positions`, `RECHECK_STATUS`,
SK-8 / SK-10 / SK-11), `physical_test_kit.py` (HE-FIT, PT-3, TL-1, TL-1b), `concepts/corrie_f.py` (`bl041_rows`,
`guy_bridle(wide=True)`). Tests: `tests/test_bl041_recheck_fixes.py`. Every number below is printed by that code.

- **DECISION HE-PIN (X-2).** BL-040 put the eye 13-38 mm above the z 60 pin and relied on it folding down
  (ASSUMPTION HE-REACH, withdrawn). The eye now points UP with the box BELOW the fairlead cheeks:
  - pin at frame z 60 = **+25 mm** above the floor seam line (BC.Z0 35); cheeks z 51-69 = +16..+34
    (`bag_attach.HALF_Z` 9);
  - box top = cheek bottom - 2 mm (ASSUMPTION HE-CHEEK) = +14; box bottom +4 (HE-GAP) → **box-X 34 x 10 mm**
    (0.39 in tall) [BL-044 §23.3: the 'in line, no peel' claim is withdrawn; the box peels and is rated by PT-3 / SEW-F];
  - eye length from the section (`he_geometry`): both legs from the box top (ply midline) round the 5 mm pin
    (centreline r 3.25 mm), pin 15.85 mm from the stay centre, B-01 face 20.0-23.45 mm (nominal / pushed by the
    cheeks), webbing 1.5 mm (ASSUMPTION HE-T, bracket 1.2-2.0): **eye 17 mm**, HE cut **86 mm** (was 150);
  - loaded pin centre **+24.6 mm** design, **+23.4..+25.3 mm** over the bracket: inside 25 +/- 3 (test);
  - only the 18 mm neck is in the 18 mm throat; B-18 stays 90 x 62 (it now backs the cheeks, +16..+34);
  - settled by **HE-FIT**, a 1:1 dry fit on a printed z 60 fairlead, a BAG-CUT gate run before PT-3 (not QC-20).
  - Alternative not taken: eye pointing down with the box above (the pin would bear on the box edge, a peel).
- **X-1.** Op 4.05 order: NECK, **B-18 ROWS (through B-18 + B-01 only)**, PLACE HE, BOX, BASTE. Geometrically the rows
  (+41 / +47) are also above the eye (fold +31), and the side rows (x 3 / 9 mm in) are 17 mm outside the HE.
- **Y-1 PT-3 rig.** Pin in an 18 mm slot fixture, B-05 strip alone in the clamp, B-01 top free, pull down B-01;
  specimen text built from the pattern constants in the op 4.05 order.
- **DECISION RT-FWD / RT-OVER-W3 (Y-2).** The clip path hangs straight down the gusset at flat x 91 (hose slot
  + 10 mm + half a strap); the RTM bar sits 10 mm above the B-26 cord (z 611.5, 133.5 mm under the collar seam,
  ASSUMPTION RT-CLIP-Z: 16.5 mm higher than the roll model's 150, the 510 mm RT cut unchanged, its tail 16.5 mm
  longer); the muzzle tabs move aft to 111 / 171 mm (60 apart, ASSUMPTION MK-GAP). Clearance from the buckle
  envelope (35 x 35, ASSUMPTION BUCKLE-ENV) and the strap corridor to the muzzle tabs, their cord, the hose slot,
  the bow tabs and the B-26 cord: **min 10.0 mm**. The B-26 cord lies over the flat sewn RTM tab (accepted). W3
  crosses every vertical path at z 702.6, so it runs through a **W3G guide** (2 x 60 mm, two BT-S tacks) under the
  RT strap. The rifle (keeper centre) sits about 46 mm further aft than in BL-040 (owner decision below).
- **Y-3.** Machine minimum adds a 304 zigzag; BT-301 fallback (4 passes at 2 mm, unrated; every 304 tack in the
  release is unrated).
- **Y-4 (structural, adopted).** B-25 in 38 mm, sleeves x 26.5-64.5 (11.5 mm from the spine clamp), cut 386.5 mm,
  tab at the sleeve centre (DECISION B25-TAB-CENTRE); load row 323 N, bar wall SF 1.36 / 1.27; TL-1 494 N on real bar
  stock with both toggles, TL-1b bare-bar data test; GBL deleted (it carried nothing in rev 3).
- **Y-5 (orchestrator).** First build: solid 630D on the camo pieces (DECISION CAMO-FIRST); the HyperD print yard and
  its shipping are a test-kit specimen (AB-1 / FRAY-1).
- **DECISION IM-CAM-TAB (m-19 / n-15).** Each IM cam is sewn to an IMC dog-bone (25 x 180 mm, 21 x 25 box-X each end,
  18 mm loops) that carries the G-hook (IM1 / IM2) or the carabiner (IM3); SK-11; load row 605 N; 2 IMC tabs in MT-1.
- **Ledger (base, belt M), rows `BL-041: ...` in `corrie_f.parts`:** B-18 +3.06 g, HE -3.58 g, RTM +2.52 g,
  W3G +2.16 g, IMC +9.72 g, B-25 38 mm +3.39 g, GBL -6.12 g = **+11.15 g** (muzzle cords -0.1 g); the bag
  reconciles 1:1 (0 unmatched rows, 0 pieces without a row).


## 22. BL-043: third-review fixes, bag side (pack-designer, 2026-11-13)

Source: `review_20261113_rev3_third.md` (2 blockers, 4 majors, 14 minors). BL-043 takes M-1, M-2, M-4 and the minors
not tied to the hinge eye; Z-1, Z-2, M-3, m-1 and m-11 wait for BL-042 (frame print files, hinge fairlead) and BL-044
(HE on BL-042's envelope). Code: `patterns_corrie_f_rev3.py` (`w3_sweep`, `rt_layout`, `rt_clearances`, `w3_corners`,
RT-ORIGIN on B-07, B-25 piece), `concepts/corrie_f.py` (`b25_topology`, `bl043_rows`),
`huntkit/viz3d/cloth_pass.py` (`roll_clip_path`), `huntkit/viz3d/corrie_f.py` (`roll_clip_paths`),
`mfg_corrie_f_rev3.py` (ops 4.05 / 4.08 / 4.11 / 5.02 / 5.03 / 7.13 / 7.17 / 7.23, SK-8 (c), SK-10, SK-12,
`THIRD_STATUS`), `physical_test_kit.py` (TL-1, TL-1b, MT-1, FIT-R3). Tests: `tests/test_bl043_third_review_fixes.py`
(21). Every number below is printed by that code; each fix was checked at all six crown-kit ends (S 15 / 18, M 17.5 /
20.5, L 20 / 23 in), not at 19 in only.

**M-1: DECISION W3-OVER (supersedes BL-041 RT-OVER-W3).** Both W3 anchors are on the crown top bar, so W3 runs level
at the bar height while the bag stays on the hinge:

| kit end | W3 z (mm) | W3 band on the bag | closest hard part | what W3 lies on |
|---|---:|---|---:|---|
| S 15 in | 601.0 | gusset z 588.5-613.5 | buckle 10.0 mm, hose slot 10.5 mm | B-26 cord, RT strap |
| S 18 in | 677.2 | gusset | 86.6 mm | muzzle tabs, RT strap |
| M 17.5 in | 664.5 | gusset | 73.7 mm | muzzle tabs + cord, RT strap |
| M 20.5 in | 740.7 | gusset / collar seam (8 mm above it) | 150.8 mm | RT strap; the roll at day / 6-day loads |
| L 20 in | 728.0 | gusset | 137.9 mm | RT strap; the roll at day / 6-day loads |
| L 23 in | 804.2 | 72 mm above the collar seam | - | on the 6-day roll; above the day roll's top |

- No guide sewn on the gusset can span the sweep (z 588-817 against a collar seam at 745). The re-run roll model puts
  the roll and its bent-down ends at z 681-790 (day) and 718-827 (6-day), so at kit M and L settings W3 lies on the
  roll itself. The roll can only be opened with W3 slack at those settings, whatever the gusset carries.
- So W3 is the outer layer. It may cross the RT strap, the RTM tab, the B-26 cord, the muzzle tabs and the roll. The
  user slackens W3 (G-hook off) before opening the top. **The W3G guide and its two unrated BT-S tacks are deleted**,
  so nothing W3 bears on is a tack.
- The RTM buckle body sits 10 mm under the lowest W3 edge: bar **z 543.5** (201.5 mm under the collar seam, 59.6 mm aft
  of the frame seam), envelope 35 x 35 (ASSUMPTION BUCKLE-ENV). The B-26 cord (z 600) now crosses the strap above the
  buckle (soft on soft, accepted), 20 mm clear of the buckle body.
- Clip path to the other gusset placements: min **10.4 mm** (buckle envelope to the hose slot). The strap's flat
  shadow is now a slant from the buckle to the roll end, so the muzzle tabs move to **113 / 173 mm** (were 111 / 171).
  That keeps 10 mm perpendicular to the slant; the aft tab is 10.3 mm inside the aft seam line (FP-CLEAR 9 mm).
- The K-W keeper loops for W3 (aft corner seams, z 702.6) have the same torso dependence. They were parked on T9 by
  the review and are not changed here (see Found, not fixed).

**m-9: DECISION HOSE-LOW.** At z 700 the hose slot was under W3 from 16.6 to 20.3 in, and a cinched W3 pinched the
hose. The slot moves to **z 558**, its top 10.5 mm under the lowest W3 edge. The hose leaves below W3 at every
setting and goes forward to the shoulder strap without crossing it. ASSUMPTION HOSE-LOW: the bladder outlet sits at the
IMP-2 sleeve foot (keeper tabs z 560), so the inside run is shorter. Settled by the hydration fit (FIT-R3 row 7 at both
kit ends).

**M-2: DECISION RT-ORIGIN (fall back to the roll end).** The hem (1049.7 mm) is stiffened by two B-07s strips of
hem/2 - 40, so it folds flat at the two 40 mm strip gaps. The ring halves are equal (front layer 524.8 mm) only when
those gaps sit at the gusset centres. BL-041's origin (27 % of the gusset from the frame corner) gives a 448.6 mm front
layer against a 601.1 mm back layer. That folds flat only with a **76.2 mm tuck of each gusset**, and its sewn 60 mm
and box-X lay across the fold gap. So the strap is sewn at the roll end again:
- the sewn 60 mm is on the frame-side half, on the strip, its box 7.5 mm clear of the gap;
- 'roll end' and 'B-07s strip end' notches go on B-07;
- the free strap leaves the roll at its end.

The cloth-pass roll model was re-run with this origin and the new tab (`cloth_pass.roll_clip_path`, tab at z 543.5,
26.6 % of the gusset depth). The cloth is the cached solve: the tab is not in the cloth job, and the roll-end bend is
at its 75 deg cap in all three states.

| load | BL-031 path (mm, R / L) | BL-043 path (mm, R / L) |
|---|---|---|
| day | 165.5 / 161.3 | 210.8 / 202.3 |
| 6-day | 170.5 / 179.7 | 222.8 / 222.0 |
| full | 369.1 / 374.9 | 424.2 / 421.1 |

- **RT cut 510 -> 560 mm** (floor5 of 90 + 424.2 + 50), +1.8 g. BL-041's "510 unchanged" did not hold.
- The strap bears on the cloth only within about 80 mm above the buckle (z 502-584). Above that it stands 27-40 mm off
  the gusset at the muzzle-tab height. That is less than the rifle barrel's 40 mm stand-off (ASSUMPTION MUZZLE-CORD),
  so FIT-R3 row 5 keeps the gloved open / close check with the rifle in the keeper.

**M-4: DECISION B25-TOPO (SK-12).** The 90 deg turn of a 38 mm strip in its own plane is a 45 deg mitre that fills
38 x 38 mm. The bar has 11.5 mm between the sleeve and the clamp, so the turn sits **under the sleeve**:
1. tab;
2. sleeve round the bar;
3. the strip leaves DOWN on the aft (bag) side and drops 33 mm below the bar to clear the clamp collar;
4. 45 deg mitre inside the sleeve band (x 26.5-64.5);
5. run inboard on edge, **necked to 25 mm** (lower edge folded 13 mm up);
6. one wrap round the spine under the clamp collar, continuous to the other side.

Nothing sits on the wearer side of the bar. Cut **386.5 -> 479.4 mm** (+2.60 g).

The frame files draw no spine clamp: frame.yaml has only its 6 g mass and print/ has no part. ASSUMPTIONS:
- B25-CLAMP: half-width 15 mm along the bar, collar 12 mm down the spine.
- PAWL-TOP: the housing reaches 20 mm above the pawl line, 18 mm either side of the spine.

Governing case, kit S at 15 in (the shortest spine above the pawl, 81 mm):

| check | clearance |
|---|---:|
| necked spine wrap to the pawl housing | **13 mm** |
| mitre to the upper bar | 9 mm |
| mitre to the housing side | 8.5 mm |

The un-necked 38 mm wrap would touch the housing (0 mm), which is why the run is necked. The clamp drawing must stay
inside x +/-16.5 mm along the bar and 25 mm down the spine (`clamp_envelope`). Settled by:
- gate **B25-FIT** in op 7.17: dry fit on the crown at kit S 15 in before the laps are tacked;
- **TL-1**, whose specimen is now the as-built half bridle: sleeve, mitre, necked run, wrapped round a 20 mm spine stub
  on the rig.

**Minors done.**

| # | fix |
|---|---|
| m-2 | per-step machine / needle / thread / stitch on ops 4.05 / 4.08 (`step_spec`, BT-301 on the 304 tacks) |
| m-3 | BT-S is 10 x 2 everywhere (the 16 mm W3G tacks are gone) |
| m-4 | IMC 192 mm (48 mm folds, 18 mm loops, each box 5 mm in from its raw end), +0.65 g; MT-1 specimens cut to it |
| m-5 | op 7.13 threads the cam and G-hook bars before the boxes and lists them |
| m-6 | B25-BOX exception stated on the piece and on SK-1 |
| m-7 | TL-1 / TL-1b read ovalisation at the loop centre with a bore gauge, where basis A predicts it |
| m-8 | bar stock 2.0 m (5 x 200 + control 200 + 2 x 160 + 10 %); TL-1b steps include 288 N; TL-1b count 2 |
| m-9 | HOSE-LOW (above) |
| m-10 | camo print BOM line production-only, prototype qty 0 |
| m-12 | webbing pages: a leader label on every line; B-25 and RT added; W3G removed |
| m-13 | SK-8 (c) names the printed PAHT-CF stay and draws the throat floor with its gap under the pin; the HE redraw is BL-044 |
| m-14 | ledger row relabelled 'BL-004 REC: guy toggles x2', mapped by prefix |

**Ledger (base, belt M, kit M).**

| change | g |
|---|---:|
| B-25 topology | +2.60 |
| IMC | +0.65 |
| RT cut | +1.80 |
| W3G deleted (its BL-041 row removed) | -2.16 |
| **net** | **+2.89** |

The bag reconciles 1:1 (0 unmatched, 0 pieces without a row). Thread is re-booked from the ops
(`build_effort_rev3.py --write`).

**Status.** M-1, M-2, M-4 and 12 minors are fixed. Z-1, Z-2, M-3, m-1 and m-11 stay open for BL-042 / BL-044, so
the release reads **NOT ready to cut**.

**Owner decision needed.** W3-OVER changes how the bag is used: W3 must be slackened (G-hook off) before the roll
top opens, at every kit, because at kit M / L settings W3 sits on the roll. The alternative was moving W3's anchors off
the crown bar, a frame change that is not proposed here.


## 23. BL-044: hinge eye on the BL-042 fairlead, and the bag-side loose ends (pack-designer, 2026-11-13)

Source: `review_20261113_rev3_third.md` Z-1, M-3, m-1, m-11 (with BL-042 `h1_fairleads.md`), and BL-043's found-not-fixed
list. Code: `patterns_corrie_f_rev3.py` (`he_envelope`, `he_loop`, `he_geometry`, `he_pin_z`, `he_bracket`, `he_band`,
`he_peel`, `kw_w3_kink`, `rt_rifle_clearance`), `he_stl_check.py` (the eye laid into slices of the HE-FIT test-piece
STL), `concepts/corrie_f.py` (`hinge_standoff`, `hinge_pin`, `bl044_rows`), `huntkit/viz3d/attach.py`
(`fairlead_geom`, `pin_y`, `he_section`), `huntkit/viz3d/corrie_f.py` (`rev3_clips`, `rev3_hose_ports`, `rev3_b25`),
`mfg_corrie_f_rev3.py`, `physical_test_kit.py`, `patterns_corrie_f_rev3_export.py` (`fit_label`). Tests:
`tests/test_bl044_hinge_eye.py`. Every number below is printed by that code (`analysis/he_stl_check.json` for the
slices).

### 23.1 DECISION HE-ENV (Z-1): the eye on `bag_attach.HINGE_EYE_ENVELOPE`

The section model now reads the BL-042 hinge fairlead (pin 10.1 mm above the stay surface, 19.45 mm from the stay
centre; throat floor 5.5 mm under the pin; throat 20 mm; cheeks +/-9 mm about the pin; cheek tips 17.7 mm proud). The
BL-041 model read the legacy constants (pin 3.6 mm nearer the stay, 18 mm throat) and wrapped one ply.

- **The wrap is the folded neck.** The neck folds lie inside the loop, so the main ply wraps the pin over the fold
  plies: 2 where the two 10 mm folds overlap (the middle 2 mm ridge, which the taut main ply rides), 1 on the flanks.
  Main-ply centreline radius 2.5 + 2 x 1.5 + 0.75 = **6.25 mm** (BL-041: 3.25).
- **Box 34 x 7 at +4..+11** (was 34 x 10 at +4..+14): box top 5 mm under the cheeks at the design pin (HE_CHEEK_CLEAR),
  so it stays >= 2 mm under them (HE-CHEEK) over the whole HE-FIT band. Box-X capacity 3067 N (thread path); the B-18
  seam (2355 N) still governs the hinge row.
- **Eye 25 mm, HE cut 96 mm** (was 17 / 86). Loaded pin centre **25.09 mm** above the floor seam line at the design
  corner (B-01 in line, ply 1.5 mm, 2 fold plies); **23.12-28.86 mm** over the bracket: B-01 at 20 / 20.95 / 27.05 mm
  from the stay centre x ply 1.2 / 1.5 / 1.6 mm x 1 or 2 fold plies (18 corners).
- **Webbing gate:** HE_T_RANGE 1.2-1.6 mm. 3 plies of 1.6 mm leave 0.7 mm under the pin (review rule: wrap <= gap - 0.5);
  a roll over 1.6 mm is rejected at the caliper (HE-FIT step 1). BL-041's 2.0 mm bracket would not fit (6.0 in 5.5).
- **Neck in the throat:** the widest neck (19 mm, HE-NECK-TOL) clears the 20 mm throat by 0.5 mm a side; the test that
  asserted `neck_w == throat` (`test_bl041_recheck_fixes.py:55`) is replaced by this clearance test.

**m-1 (HE-FIT band).** Band **22-29 mm**: the low end keeps the box top 2 mm under the cheeks (11 + 9 + 2); the high
end is ASSUMPTION HE-PIN-HI (the floor hangs at most 4 mm below the z 35 every sim assumes; settled by QC-20 / T9). The
solved bracket (23.1-28.9) sits inside it with 1.1 / 0.1 mm to spare. HE-FIT also measures the box-to-cheek gap with a
feeler (>= 2 mm) and the webbing ply (<= 1.6 mm).

**B-01 stand-off.** The hinge cheek tips stand 27.05 mm from the stay centre, so with no swell (DECISION H-1) they lift
B-01 **7.05 mm** over the 20 mm PANEL_OFFSET (8.05 mm with B-18), not the 3.45 mm BL-033 recorded (`hinge_standoff`
now reads the envelope; US2 keeps the legacy 3.45). That is under the 16 mm swell the IM stations are given; the tent
is local (36 x 18 mm of cheek tips). ASSUMPTION HE-TENT: B-01 / B-18 tents over the cheek tips without pulling the
box off line; settled by HE-FIT (the specimen offcut lies over the printed cheeks).

### 23.2 The eye on the real STL

`he_stl_check.py` slices `print/frame_h1/test_pieces/hefit_hinge_fairlead_R_frame_coords.stl` (the file HE-FIT
prints) and lays the eye into it at all 18 corners, each with the bag at its own height on the printed pin.

| check (STL) | result | required |
|---|---:|---:|
| loop (legs + wrap) overlapping printed material, any corner, planes x across the neck | 0.000 mm2 | 0 |
| stack to floor under the pin, neck centred, ply 1.2 / 1.5 / 1.6 | 1.91 / 1.01 / 0.71 mm | >= 0.5 |
| same, neck slid against a cheek, outside the last 0.1 mm at the cheek face | >= 0.71 mm | >= 0.5 |
| same, in the throat-corner fillet (last 0.1 mm), ply 1.2 / 1.5 / 1.6 | 0.61 / **0.29** / **0.19** mm | > 0 |
| throat, printed | 19.97 mm: 0.49 mm a side on the 19 mm neck | 0.5 |
| box top to the cheeks' lower edge, any corner | >= 3.12 mm | >= 2 |
| box stack to printed material | >= 2.98 mm | > 0 |

ASSUMPTIONS HE-STACK (3 plies over the +/-2 mm ridge, falling to 2 at the neck edge, where the main ply turns into its
fold) and HE-FOLD-R (the folded edge is round, radius one ply). **Not met in full:** where the neck slides against a
cheek, its round folded edge meets the printed throat-corner fillet (the floor rises 3.5 mm in the last 0.5 mm to the
cheek face). There the 0.5 mm rule is not met (0.29 mm at the design ply, 0.19 mm at the 1.6 mm gate); the eye still
does not touch. It is checked physically: HE-FIT slides the neck against each cheek in turn with the pin in. The
frame-side fix (relieve the floor 1 mm deep within 1.5 mm of each cheek face, or a smaller corner fillet) is a frame
change for the structural-fea-engineer (Found, not fixed; owner decision below).

### 23.3 M-3: the box peels; rated instead

The stay-side leg must pass under a pin that sits 1.5 mm (in line) to 7.6 mm (B-01 held at the cheek tips) toward
the frame from B-01, so the two legs leave the box top at an included angle. In line, leg B leaves **23 deg** off the
box line (peel across the top row = 0.20 x the hinge load); with B-01 held at the cheek-tip plane, **50 deg** (0.38 x).
It cannot be avoided with a box on B-01 (a lower box is limited by the floor seam and HE-GAP). "No peel" is dropped.
Rated by test:

- **PT-3** pulls on a fresh print of the HE-FIT fairlead, eye on the pin, with a spacer plate holding B-01 at the
  cheek-tip plane (the 50 deg worst peel), B-05 alone in the clamp, to 1530 N for 60 s; box top row checked first
  (ASSUMPTION PT3-PRINT: a cracked print voids the specimen; re-run in machined aluminium of the same section).
- **SEW-F** adds 3 HE specimens on the same fixture at **625 N peak** (1.15 x 1.6 g x 1019 N / 3), R 0.1, 1e5 cycles,
  then the PT-3 proof (ASSUMPTION SEWF-HE-RIG: the lever rig carries 625 N on the eye).
- The hinge load row lists the 34 x 7 box capacity and its peel; no peel capacity is credited.

### 23.4 m-11: the B-18 label

The step 2 tiled print re-flows each label block into a clear spot (`fit_label`: wrapped, shortened, moved up or down
by blank lines) so it touches no internal line, drill mark or notch and stays inside the seam line. B-18 and B-22 now
clear every mark (0.0 mm2). The full label of every shortened piece is on the NOTES page. B-12 and B-27f are so small
that even their ID crosses a mark (6.4 mm2 each); recorded, not fixed.

### 23.5 DECISION KW-W3-OFF (BL-043 found-not-fixed)

A W3 K-W loop fixed at the 19 in crossing (z 702.6) would make W3 climb or drop along the 180 mm gusset to it at every
other setting: **29.5 deg and 114 N** across an unrated seam-caught loop at kit S 15 in and kit L 23 in (101.6 mm off),
8-12 deg at the other kit ends. Nothing on the bag can follow W3's 203 mm sweep (the collar seam is at 745), so the two
W3 loops are deleted; W3 is located by its two crown-bar anchors at one height and runs level at every kit end. W1 / W2
keep theirs (frame-fixed anchors). K-W 6 -> 4 loops, **-2.88 g**.

### 23.6 RT strap vs the rifle barrel (recorded)

ASSUMPTION RIFLE-LINE: the barrel (25 mm OD, on the cloth) runs from the butt boot (frame seam line at the floor,
+/-60 mm) through the muzzle keeper and 300 mm on. In the flat gusset the roll-clip strap and buckle stay **27.1 mm**
or more clear of it at every boot position (RT_CLEAR 10); where the strap stands off the cloth at the muzzle tabs
(27.3-40.4 mm, cloth-pass roll model) it is also outboard of a barrel lying on the cloth. Recorded; FIT-R3 row 5 keeps
the gloved open / close check with the rifle in the keeper.

### 23.7 Stale text and marks

- "Hose ports at the collar seam" (`corrie.py`, `build_geometry.py`, `corrie_loadout.py`): now the gusset slots,
  CORRIE B z 700, CORRIE F rev 3 z 558 (HOSE-LOW).
- The L hem's 'B-07s strip end' notch had been merged by `_dedupe_notches` into the 'hem ring' slit 2.7 mm away (drawn
  at 950.0 for 947.3). The strip ends are now placement lines across the hem at their exact x.
- Test-kit screenshots are named for the ticket that regenerates the kit (`20261113_BL044kit_<n>`, was `BL041kit`).

### 23.8 Hinge pin, weights

- Hinge pin spans 8 + 20 + 8 = 36 mm (IM / US 34): shank 36 -> **38 mm**, drawn pin 50 -> **52 mm**, BOM line split
  (6 x 36 mm + 2 x 38 mm shank); **+0.22 g** for the pair (7075 record density).
- Ledger rows (base): HE 86 -> 96 mm **+0.56 g**, hinge pins **+0.22 g**, W3 K-W loops **-2.88 g**. Thread re-booked
  from the ops. Roll-up regenerated with H1F (+37.2 g, BL-042): **proven now, base 3690.7 -> 3728.7 g (8.22 lb)**;
  after tests 3141.5 g.

### 23.9 Renders

`huntkit.viz3d.corrie_f` now draws the release's roll clips (strap from the roll end to the RTM buckle, bar z 543.5,
26.6 % of the gusset depth), the HOSE-LOW ports (both gussets, z 558, the hose routed forward below W3), the 38 mm
B-25 topology (sleeves x 26.5-64.5, drop, necked run, spine wrap) and W3 level at the crown bar (19 in). Hero and side
re-rendered as `20261113_BL044_3/4.png`.

**Status.** Z-1, M-3, m-1, m-11 are fixed (with the corner-fillet exception in 23.2); Z-2 by BL-042. All three
reviews have 0 blockers and 0 majors open, but the release stays **NOT ready to cut** until a fourth independent
review (`mfg_corrie_f_rev3.FOURTH_REVIEW_DONE`).
