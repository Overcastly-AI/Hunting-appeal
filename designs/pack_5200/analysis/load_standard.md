# HA-LS-1: Pack 5200 frame load standard (calibrated, "match the leaders") - revision C

Owner: structural-fea-engineer. Status: **adopted for frame v2** (owner decision 2026-11-01, docs/DECISIONS.md:
"Frame strength standard: MATCH THE LEADERS. Realistic field loads, verified by physical prototype load tests").
Executable form: `huntkit/fea/load_standard.py` (cases + factors), applied by `huntkit/fea/sizing5200v2.py`.
Results: [frame_sizing.md](frame_sizing.md) (v2 sizing, rev B); production check under rev C:
[rev_c_verification.md](rev_c_verification.md).

> **Revision C (2026-11-06, owner decision, `docs/DECISIONS.md`): CG offsets calibrated to the cloth simulator.**
> Bag cases (C1-C4, C8) **205 mm** aft at a CG height of **z 550**; meat cases (C5, C7) **190 mm**; tall cases (C6,
> C6p) **185 mm**; the bag CG couple is checked with its top on the crown top bar **and** on the IM3 hooks (z 520),
> the worse governs; the released top anchor (crown hood + 2 fixed guys) is applied in C5 / C7; ties on the crown bar
> must bear on **>= 25 mm** of webbing; new prototype test **T9** measures the loaded CG. Factors, g-levels and every
> other rule are unchanged. Section 4.2 has the table and the sources. Code: `huntkit/fea/load_standard.py`
> (`REVISION = "C"`, `REVISIONS`, `ls1_cases(rev=...)`, `ls1_envelope()`); `ls1_cases(rev="B")` reproduces the
> records made before 2026-11-06.

> **Revision B (2026-11-01, owner direction): there is NO meat shelf.** Meat (boned in game bags, or a bone-in
> quarter) rides INSIDE the bag and is cinched against the frame face by the internal meat harness
> (geometry.yaml `meat_harness`: straps IM1-IM3 at `meat_anchor_z190 / z330 / z520`, vertical load into the
> bag-bottom hinge pins `bag_anchor_low` z 60). The shelf pivots, shelf-strap anchors and the shelf-bending
> case are retired. C5 `meat_shelf_heavy_low` is replaced by **C5 `meat_straps`**; C6 / C6p / C7 use the same
> strap placement (section 4.1). Factors and g-levels are unchanged. Code: `huntkit/fea/load_standard.py`
> (`REVISION = "B"`, `MEAT`), placement `meat_straps` in `huntkit/fea/load_cases.py`.

> **Conflict to resolve (orchestrator):** CLAUDE.md "Hard rules" still states "SF >= 2.0 on yield at 150 lb
> under a 2.5 g dynamic factor". The owner's 2026-11-01 decision replaces that. This document defines the
> replacement. CLAUDE.md should be updated to point here; I have not edited it.

## 1. What the leaders actually do (benchmarks, cited)

Nobody in the hunting-pack market publishes a test standard. The research doc says so directly
("Rated load is marketing", [pack_market_2026.md](../../../docs/research/pack_market_2026.md) §0). What *is* published:

| Brand / frame | Rating | Published test | Ratio test / rating | Source |
|---|---|---|---|---|
| Stone Glacier Krux (carbon stays) | 150+ lb | Static: 1 in steel plates (~85 lb each) loaded in the pack up to **340 lb, "no damage, failure, or signs of stress"**; testing to failure was not reached | **2.27x**, static, no damage | [SG Solo 3600 Krux / COL 4800 listing][sg-test], [SG "One Frame"][sg-oneframe], [SG Sky 5900][sg-sky] |
| Hill People Gear Ute chassis | 150 lb | "300 lb capable" | 2.0x | [Soldier Systems][ssd-hpg], [Carryology][carry-hpg] |
| Seek Outside Revolution (6061 Al) | 200+ lb | frame ">300 lb vertical" (brand claim) | ~1.5x of 200 | research doc §2 table ([Seek Revolution][seek-rev]) |
| Eberlestock Mainframe | heavy hauler | static-tested to 1,300+ lb | n/a (outlier) | research doc §6 ([Kenetrek][eb-mod]) |
| KUIU ICON 6 (thermoplastic carbon sheet) | not published | field test 125 lb, "no sway, creak or rock" | < 1x of 150 | [Bowhunter][bh-icon], [KUIU whitepaper][kuiu-wp] |
| AKEK Alpha (carbon) | 150 lb (frame) | first frames **cracked in a cliff (drop) test**; production moved | the drop test found the failure, not the static one | [GearJunkie][gj-akek], [Rokslide][rs-akek] |

Reading: the credible static proof practice is **~2x the rated load, static, no damage**. Nobody claims a
5x (2.5 g x SF 2.0) no-yield capability, which is what our old standard demanded. AKEK's experience says the
**drop test is the one that catches real failures**, so HA-LS-1 makes drop and set-down physical tests mandatory.

## 2. Relevant test standards (what exists, what we borrow)

- **No EN/ISO standard covers load-carrying backpack frames.** EN/ISO drop tests exist for sacks and containers:
  ISO 7965-1 (paper sacks, progressive drop height) ([ANSI preview][iso7965]) and ASTM D5276 (drop test of loaded
  containers, height set per product) ([US 8,210,746 citing D5276][astm5276]). Kenya's consumer backpack standard
  KS 2660:2023 has a **1 m drop with a 3-10 kg load** ([WTO TBT notification][ks2660]). That is a school-bag-level
  load, useful only as a durability floor.
- **MIL-STD-810H Method 516.8, Procedure IV (transit drop):** items < 45 kg in a case < 91 cm are dropped from
  **122 cm (48 in)**, 26 drops (6 faces, 12 edges, 8 corners), which may be split across up to 5 test articles
  ([JOTP 01-1-011 table][jotp], [DES summary][des810], [Trenton][trenton810]). We borrow this as the **empty-pack
  abuse drop** (thrown off a truck tailgate or a ledge): T4c below.
- Military load-carriage reviews (Knapik, Reynolds & Harman, *Mil. Med.* 169:45-56, 2004; Knapik et al. 1996
  review) support the framed-pack + hipbelt architecture and the hip/shoulder load sharing: "hip belts ... reduce
  pressure on the shoulders"; framed packs with hip belts shift force from shoulders to hips
  ([Knapik 2004][knapik04]). Their specification drop tests for MOLLE frames were not found in public sources:
  ASSUMPTION, none used.

## 3. Biomechanics: how big are real pack loads?

- **Walking peak.** Rome et al. measured the force a fixed backpack load puts on the wearer: the hips rise and fall
  up to ~7 cm per step, and **a 50 lb load hits the wearer with ~80 lb of force on the downswing (1.6x) while
  walking, up to ~150 lb (3x) while running** (Rome et al., *Science* 309:1725, 2005; *Nature* 444:1023, 2006;
  figures as reported by [Scientific American][sciam] and [Nature News][nature06]). The frame sees this force: it
  is the pack-body interface force. **-> walking peak factor 1.6 g** (fatigue and the walking cases).
- **Running at 3x is not a design condition** at 150 lb. Nobody runs with a 150 lb meat load.
- **Stumble / drop-step** (stepping down off a rock or log, a slip caught by the legs) sits between walking and
  running. ASSUMPTION: **2.0 g limit**, i.e. 25 % above the measured walking peak, occurring a few hundred
  times in the frame's life. **T4a measures it** on the prototype with a phone accelerometer. The old standard used
  2.5 g for every dynamic case with no source.
- **Hip/shoulder split.** 80 % hips / 20 % shoulders (unchanged from v1, ASSUMPTION consistent with the Knapik
  reviews' hip-belt findings). The hipbelt-off case covers the 0 % hip extreme.
- **Compliance helps.** Compliant suspensions cut the peak interaction forces (Martin & Li, *Sci. Rep.* 8:13775,
  2018, [PMC6137106][martin18]; Rome 2006: ~80 % lower peak force with an elastically suspended load). Our hipbelt
  foam and the load's own compliance are NOT credited (conservative).

## 4. The standard

Rated load **W = 68 kg (150 lb)**. Overload **91 kg (200 lb)** (owner decision, meat hauling).

Definitions:
- **Limit load** = rated mass x case g-factor = the largest load expected in service.
- **Yield / first-ply factor** applies on the limit load: no yield (metals) and no first-ply failure (CFRP,
  Tsai-Wu) at factor x limit, **with the composite knockdowns kept** (hot/wet 0.8, impact damage 0.65 on
  compression, `huntkit.fea.composite`). HA-LS-1 lowers the *load*, not the material allowables.
- **Ultimate / no-collapse cases** (overload, abuse) use factor 1.0 on the knocked-down first-ply failure. For
  these +-45-wrapped UD tubes, first-ply failure comes well before collapse, so this is conservative against "no
  collapse".

| # | Case (code name) | Load | g | Factor | Equiv. x rated | Type | Covered by test |
|---|---|---|---|---|---|---|---|
| C1 | static carry (`static_carry`) | 68 kg in the bag, CG 205 mm aft at z 550 (rev B 180), hips 80 % | 1.0 | **2.0** yield/FPF | 2.0 | limit (= the leaders' 2x static proof) | T1 |
| C2 | stumble / drop-step (`drop_2p5g` code name kept) | as C1 | **2.0** | **1.5** | 3.0 | limit | T1 (300 lb), T4a |
| C3 | side-hill torsion | 25 deg tilt, 30 % downhill bias, downhill strap + lifter slack | **1.6** | **1.5** | 2.4 | limit | T3 |
| C4 | single-stay set-down | impact on one foot + 0.2 friction, inertia relief | **2.0** | **1.5** | 3.0 | limit | T4b |
| C5 | meat on internal straps (`meat_straps`, rev B) | 68 kg in the bag, CG 190 mm aft (rev B 150), face pressure + strap tension (4.1), crown hood + 2 guys (4.2) | **2.0** | **1.5** | 3.0 | limit, primary mission | T2 |
| C6 | tall load | bone-in quarter on the bag floor, cinched, CG 185 mm aft (rev B 160), top lashed to the crown top bar (4.1) | **2.0** | **1.5** | 3.0 | limit | T2 |
| C6p | tall load on extension posts | as C6, lashed 220 mm above the crown; load lifters STAY on the crown top bar (IP) | **2.0** | **1.5** | 3.0 | limit (accessory) | T2 (posts) |
| C7 | overload haul | **91 kg** in the bag on the internal straps, CG 190 mm aft (rev B 150), hood + guys x 91/68 | **1.6** | **1.0** | 2.1 | **ultimate, no collapse** | T2u |
| C8 | hipbelt-off abuse | 68 kg, 100 % on shoulders + lifters (creek crossing), bag CG 205 mm at z 550 (rev B 180) | 1.5 | **1.0** | 1.5 | ultimate, no damage, no crown slip | T1 variant |

Other rules:

| Check | Old (v1) | HA-LS-1 |
|---|---|---|
| Member yield / FPF | SF >= 2.0 at 2.5 g (5.0 x rated) | factor per case, above (3.0 x rated max) |
| Frame buckling eigenvalue | >= 3.0 (scaled for overload) | **>= 1.5 x case factor** (2.25 limit cases, 1.5 ultimate cases). Buckling is collapse, so it keeps a 1.5 margin over the strength factor |
| Bond, average shear | SF >= 2.0 | **>= case factor** (MMA lap shear on CFRP x 0.8 hot/wet) |
| Bond, Volkersen elastic peak | SF >= 2.0 (it governed v1) | **>= 1.0 at limit load**. Toughened MMA/epoxy yields at the peak and redistributes, so the average governs ultimate (Hart-Smith; `huntkit/fea/joints.py` docstring). **T6 coupons must confirm** |
| Lumbar plate shear buckling | >= 3.0 | >= 1.5 x case factor |
| Crown bushings (ring crush, bearing) | point-load ring 0.318 F R | factor per case. 120 deg contact land credited (0.154 F R, `huntkit/fea/rings.py`) **only with a passing T7 crush coupon** |
| Fatigue | 1e5 cycles at 0 -> 1.2 g | **1e5 cycles at 0 -> 1.6 g x 68 kg** (Rome walking peak), CFRP FI <= 0.5 at peak, bond <= 0.3 x lap shear, metal Basquin Kt 2. This envelopes the 1.2 g rule. ~1e5 strides = ~100 miles with 150 lb on, about 20 heavy pack-outs |
| Crown retention (pawl + rack) | 2.0 on drop, 1.0 abuse | limit loads from FEA x 1.5, abuse x 1.0 (rack rating 5328 N) |

**Old vs. new in one line:** dynamic cases go from 5.0x to 3.0x rated (no-yield, knocked-down allowables),
the Volkersen peak requirement goes from 2.0 to 1.0, and the drop/set-down/fatigue claims move from analysis to
**physical tests**. Static 2.0x is kept: it is the number the leaders publish.

### 4.1 Meat-load placement (rev B, internal straps)

Frame-side resolution of a meat load of weight P = m g (x case g), CG `e` aft of the frame axis
(`LoadCase._meat_straps`):

| item | value | basis |
|---|---|---|
| CG offset e | 150 mm (C5, C7), 160 mm (C6, C6p) | pack-designer `meat_harness.load_cases.bag_on_rated` ("CG 150 mm aft of the stay"); ASSUMPTION +10 mm for a stiff bone-in quarter that does not conform to the panel |
| vertical path | 70 % into the bag-bottom hinge pins (`bag_anchor_low`, z 60), 30 % by strap / panel friction into the three strap anchors | ASSUMPTION (pack-designer: "vertical into the bag bottom + hinge pins"; part is shared by friction) |
| overturning P e | aft (+y) pulls at the strap anchors in proportion to their lever above the pressure centroid (sum H_i (z_i - z_p) = P e); C6/C6p add the crown top-bar lash (posts bar for C6p) | pack-designer: "overturning reacted by the straps in proportion to height" |
| contact pressure | forward (-y) on the frame face, triangular over z 60-330 (peak at the bottom), on the stays, lumbar-pan grid and mid bar | ASSUMPTION |
| strap cinch | 150 N pretension per anchor, aft, balanced by uniform face pressure (self-equilibrated) | ASSUMPTION (hand-cinched 38 mm cam strap) |
| bag in carry cases | CG 180 mm aft kept (v3.1 uniform-fill CG is 148 mm: 180 is conservative) | geometry.yaml `bag.cg_uniform_fill` |

Effect on the v2 tube frame (member first-ply level, rev B, worst torso; `outputs/genframe/tube_baseline.json`):
see printed_frame_study.md section 2. The physical test T2 becomes: 300 lb of sandbags in game bags inside the
bag, cinched with IM1-IM3, instead of on a shelf.

### 4.2 Revision C: cloth-sim-calibrated CG (owner 2026-11-06)

Rev B's offsets came from a drafted bag shape. The sewn-bag simulation (validated to 0.5 % on closed forms,
[cloth_sim.md](cloth_sim.md) §2) shows the contents lean aft. No published offset was found to calibrate against
(search 2026-11-05, [frame_cg_recheck.md](frame_cg_recheck.md) §6), so rev C uses the sim now and **T9** measures it on
the prototype.

| item | rev B | **rev C** | source |
|---|---|---|---|
| bag CG aft, C1-C4 and C8 | 180 mm (C8 hard-coded 180) | **205 mm**, all five cases | [bag_top_anchor.md](bag_top_anchor.md) §7: 15 in fill CG 202 mm + sim scatter; hood + guys give 189 / 177 / 168 mm at 15 / 19 / 23 in ([bag_attachment.md](bag_attachment.md) §2) |
| bag CG height (lateral moment of C3) | at the attachment-node height (about z 212) | **z 550** (`LoadCase.cg_z_mm`) | [cloth_sim.md](cloth_sim.md) §3.2 (z 542) |
| meat CG aft, C5 / C7 | 150 mm | **190 mm** | covers the 15 in hood + guys fill case (189 mm) and the meat runs 181 / 173 / 165 mm ([bag_attachment.md](bag_attachment.md) §2) |
| tall-load CG aft, C6 / C6p | 160 mm | **185 mm** | ASSUMPTION: the same +25 mm as the bag cases; no sim run of a bone-in quarter. T9 (b) checks it |
| bag couple top | crown top bar | **both**: crown top bar, and the IM3 hooks at z 520 (`couple_top="strap_upper"`); the worse governs | [cloth_sim.md](cloth_sim.md) §3.5: the IM3 hooks carry 338-472 N per side at 1 g |
| top-anchor loads | none | C5 / C7: **crown hood 52.5 N aft per g**, spread over x -66..+66 of the top bar (the hood lip bears on bare bar only, relieved clear of the corner wraps, D-31), plus **2 guys of 37.3 N per g**, from the hood ears at x +/-95 toward the bag top corners (+/-149, z 752); x 91/68 on C7 (`TOP_ANCHOR_HOOD_GUYS`) | [bag_attachment.md](bag_attachment.md) §2 / §2.5, `attach_system_results.json` `factored_n` / 3.0 (runs PR15/19/23) |
| tie bearing on the crown bar | none | **>= 25 mm webbing** (38 mm preferred), or a sleeve / pocket; no cord or 20 mm straps on the bare bar (`tie_bearing_ok`) | [frame_cg_recheck.md](frame_cg_recheck.md) §5: 210 N on 20 mm gives ring crush SF 0.87 |
| factors, g-levels, rules | | unchanged | section 4 |

Pass rule under rev C: every case set in `ls1_envelope()` (9 cases with the couple on the crown bar plus the 5 bag
cases with the couple on the IM3 hooks) at torso 15 / 19 / 23 in. The production frame passes with the crown fix
(inner UD plies + 0.8 mm corner bondline, +22.0 g) and the 7 mm spreader core (+8.7 g):
[rev_c_verification.md](rev_c_verification.md).

ASSUMPTION: C6 / C6p get the same +25 mm as the bag cases (no sim data for a stiff quarter). ASSUMPTION: the IM3
couple variant puts the whole couple top on the IM3 anchors; reality lies between the two variants.

### 4.3 Rev C note: float meat mode (2026-11-06, additive)

The owner replaced the hinge swing ("between" mode) with the **float** (DESIGN.md D-33): meat in the US1/US2 cradle
with IM1-IM3 over it, the bag hung upright behind it on two B-24 stand-off links at the IM3 eyes. Nothing in sections
4-4.2 changes. The float is **not a new frame case**: at most 68 kg goes on the frame with the CG <= 190 mm aft
(`meat_haul_modes.md` C), inside C5. It adds three **attachment cases** (`load_standard.FLOAT_ATTACHMENT_CASES`),
checked by direct FE in [float_fea.md](float_fea.md):

| case | load | factored, per IM3 eye | rule |
|---|---|---|---|
| float design | 36 kg meat on the frame + 12 kg gear in the bag; link 30 deg below horizontal carries the whole bag | 559 N (531 aft, 177 down) | link x 3.0 (C5: 2.0 g x 1.5), hand cinch 150 N x 1.5; fatigue at cinch + 1.6 x link |
| float misuse | 36 kg meat + 32 kg in the bag | 1142 N (1040 aft, 471 down) | as above; must stay inside the bag-on IM3 hook case (1415 N) |
| float cradle | meat on the frame, all vertical in the cradle, **no friction credit** | US1 489 N at 36 kg | 1.6 g x 1.5 strength; fatigue 1e5 x 1.6 g. Sets the **float meat limit: 53 kg (116 lb)** on the frame |

The retired between case (hinge 264 N, IM3 496 N, CG 110 mm) is dropped; it is in no envelope. The bag-on hinge
case (1019 N factored, HE / B-18) is unchanged. Proposed prototype test **T5f**: 56 kg of wet sandbags in float, US1
share measured over 0 -> 1.6 g cycles; a measured share <= 0.95 x the no-friction value would earn 56 kg.

ASSUMPTIONS specific to HA-LS-1:
- ASSUMPTION: stumble limit 2.0 g (between Rome's 1.6 walking and 3.0 running); verify in T4a.
- ASSUMPTION: set-down at 2.0 g x 1.5 covers a deliberate hard set-down; a free drop of a 150 lb pack onto one
  foot is a test (T4b), not an analysis case.
- ASSUMPTION: the 1.5 limit factor is the aerospace ultimate factor (14 CFR 25.303). Composite one-offs normally add
  test factors for scatter. We cover scatter with the kept knockdowns (0.8 x 0.65 = 0.52 on compression) plus the
  physical proof tests.

## 5. Physical test plan (owner-run, prototype)

Build **two frames**: P1 is the test article, taken to the ultimate demonstration (T2u) at the end. P2 is
the field article and gets T1, T4a/b and T5 only at limit loads. Also make **coupons** (T6, T7) from tube offcuts
before you bond either frame.

### 5.1 DIY rig (see `outputs/screens/20261101_frame2_3.png`)

| Item | Use | ~Cost |
|---|---|---|
| 2x4 / 4x4 wall frame lag-screwed into studs (or a freestanding A-frame of 2x6 on sawhorses) | structure | $40 |
| "Hip log": 4x4 (or 4 in steel pipe) wrapped in closed-cell foam (yoga mat) to ~36 in circumference | the hipbelt buckles around it like a pelvis | $10 |
| Shoulder bar: 1 in steel pipe or a broom handle 16 in above the log, adjustable | yoke straps + lifters | $10 |
| 2 ratchet straps + 1 snap shackle (quick release) | shoulder tension, drop release | $30 |
| Crane / luggage scale, 300 kg (660 lb) | measure strap tension, lift force, total load | $30 |
| Load: 50 lb tube-sand bags, 5 gal water jugs (8.34 lb/gal, 41.7 lb each), or barbell plates | dead weight | $0-80 |
| Dial indicator 0-25 mm (0.01 mm) on a magnetic/clamp base, or a laser pointer taped to the crown top projecting on a wall 3 m away (optical lever: 1 mm at the crown ~ 6 mm on the wall at 0.5 m lever) | deflection | $20 |
| Phone with **phyphox** (free app), "Acceleration (without g)" or "with g" + peak readout, taped to the crown top bar | drop / cycle g-level | $0 |
| 12 V wiper motor (~50 rpm) + 12 V 10 A supply + 50 mm crank arm + bungee (k ~ 8 N/mm) + mechanical counter or reed switch + Arduino | T5 cycle | $70 |
| Rubber gym mat 10-20 mm on concrete | set-down surface | $30 |
| Safety: back-up sling under the load, safety glasses, gloves, no one under the load, outdoor exclusion zone for T2u | | |

### 5.2 Measurements on every test

1. Deflection at the **crown top bar** (fore-aft) and at the **lumbar pan centre** relative to the hip log, at
   each load step. Record load and reading at 0, 50, 100 % ... and again at 0 after unload (permanent set).
2. Listen. Creaks or cracks during a hold = stop. Mark the spot.
3. **Tap test** after each test: tap every joint, wrap and the lumbar pan with a coin. A dull or dead note vs. the
   same spot on the other side = delamination or a debond.
4. Crown: pencil mark on the leg at the stay-top collar. Slip > 4 mm (1 rack tooth) = fail.
5. Photos of every joint before/after, same angle.
6. Write it in a log (template at the end): date, test, load, readings, notes.

### 5.3 Tests and pass criteria

Loads in the bag unless stated. "Hold" = 10 min unless stated. Load in 25 % steps, hold 1 min per step.

| Test | What | Load (lb / kg) | Pass |
|---|---|---|---|
| **T1 static proof** (C1, C2 limit, C8) | Pack on the rig, hipbelt on the log, shoulder straps ratcheted to carry ~20 % (read on the crane scale). (a) 150 lb, (b) **300 lb / 136 kg** (= 2.0 x rated = static factor = stumble limit). (c) Hipbelt-off: unbuckle the belt and hang the pack from the shoulder bar by straps + lifters only, 150 lb x 1.5 = **225 lb / 102 kg**, 2 min | 150 / 300 / 225 | No crack sound, no visible damage, tap test clean. **Permanent set at the crown <= 1 mm** (or <= 5 % of peak deflection). Re-load to 150 lb: deflection within 10 % of the first 150 lb reading. Crown slip 0 teeth. At 150 lb, deflection within +-30 % of the FEA prediction (frame_sizing.md) |
| **T2 meat / tall-load proof** (C5, C6, C6p) | Rev B: 300 lb of sandbags in game bags INSIDE the bag, cinched with the internal straps IM1-IM3 as in the field. Tall-load variant: 300 lb stacked tall, top lashed to the crown top bar (and to the post bar if posts fitted) | **300 / 136** | Same as T1 |
| **T2u ultimate demo** (C7, and 1.5 x C5) - **P1 only, last test** | Shelf load stepped to **450 lb / 204 kg** (1.5 x 300) and held 30 s. Outdoors, back-up sling, exclusion zone | 450 / 204 | **No collapse**: still carries the load at 30 s. Damage allowed (it's the sacrificial frame). Record first noise / first visible damage load: that is the measured margin |
| **T3 side-hill** (C3) | Rig tilted 25 deg (shim one end of the log or tilt the A-frame), downhill shoulder strap slackened to ~25 % of the uphill tension (crane scale), load pushed 30 % downhill. **240 lb / 109 kg** (1.6 x 150) | 240 / 109 | Same as T1; also crown legs slide freely after unload (no binding = no permanent twist) |
| **T4a drop-step** (C2) | 150 lb in the bag, pack hung on the log. Lift the whole pack by its haul loop with the ratchet strap h mm off the log, release with the snap shackle. Increase h from 10 mm in 5 mm steps until phyphox reads a **2.0 g peak** at the crown (expect 15-40 mm). Then **20 drops** at that height | 150 / 68 at 2.0 g | No damage, tap test clean, crown slip 0, T1(a) re-check within 10 %. **Also record the g-level at each h**: if 2.0 g needs < 10 mm, the 2.0 g limit is too low and the standard must be revisited |
| **T4b set-down** (C4) | 150 lb pack held upright, raised **50 mm (2 in)** and dropped onto ONE stay foot on the gym mat, 5 x each foot. Phone on the crown | 150 / 68 | No damage at the foot boot / wrap / lumbar pan, tap test clean. Record the peak g |
| **T4c empty abuse drop** (MIL-STD-810 Proc IV style) | Empty pack (bag on) dropped from **48 in / 122 cm** onto 19 mm plywood over concrete, 6 orientations: each foot, each side, crown top, back panel | empty | Functional: crown still telescopes and locks, no cracks, tap test clean. Cosmetic scuffs OK |
| **T5 cycle / fatigue** | Dead load 60 lb (0.4 W) in the bag + crank/bungee pulling the bag down 0 -> 180 lb (1.2 W, set with the crane scale at the crank's bottom dead centre): **0.4 -> 1.6 g**. **100,000 cycles** at ~50/min (~33 h; can be split over days). Stop every 25,000 cycles: T1(a) re-check + tap test | 60 -> 240 lb peak | No crack, no debond, **stiffness change <= 10 %** at each stop, crown slip < 1 tooth, pulley webbing not cut by its guides |
| **T6 joint coupons** (before bonding the frame) | 3 x each joint type, made exactly like the frame: (a) bar coped to a stay and carbon-wrapped (T joint), (b) wrap collar over a stay end. Pull the bar out along its axis (a) / the stay out of the collar (b) with the rig (come-along + crane scale) to failure | to failure | Mean failure load >= 1.5 x the largest FEA limit end force for that joint (frame_sizing_cases_19in.md, bonded joints table) and lowest >= 1.25 x. Failure should be cohesive / in the laminate, not a clean adhesive peel (= bad prep). **Rev C: crown-corner coupons use the 0.8 mm bondline** (0.8 mm glass beads in the MMA), the same as the frame; a 0.5 mm coupon does not qualify the Volkersen-peak credit |
| **T7 bushing crush coupon** (before release) | 150 mm stay offcut with the wrap collar + UHMWPE bushing; leg offcut through it; press the leg sideways at the bushing centre (lever or bench vise + crane scale) | 1.5 x the max FEA bushing force, then to failure | No crack, ovalisation <= 0.2 mm after unload at 1.5 x. **This earns the 120 deg contact credit** used in the sizing |
| **T9 loaded CG** (rev C, P2, before T1) | Load the prototype to 68 kg (a) as T1 (uniform fill in the bag, hood + guys fitted) and (b) as T2 (game bags on IM1-IM3; a bone-in quarter for C6). Find the CG offset from the stay plane two ways: hang the pack from the haul loop and then from a pin through the hipbelt pivot and plumb both lines (CG = their intersection), or use two scales, one under the stay feet and one under the crown top bar, with the frame horizontal. Repeat at torso 15 / 19 / 23 in | 150 / 68 | Record the offset and height. **Pass:** bag CG <= 205 mm aft at a height z <= 590 (rev C uses 550; ASSUMPTION: 40 mm scatter); meat CG <= 190 mm; tall <= 185 mm. If a measured value is more than 10 mm below the rev C value the owner may relax it (re-run `rev_c_verification` at the measured CG first); if any is above, stop and re-run the check before T1 |

Test order: T6, T7 -> bond P1, P2 -> T9 -> T1 -> T3 -> T2 -> T4a/b -> T4c -> T5 (P2) -> T2u (P1 last).
If anything fails: stop, photograph, send the log and photos for re-analysis. Do not repair and continue.

### 5.4 Log template

```
date | frame P1/P2 | test | torso setting | load lb (scale) | crown defl mm | lumbar defl mm | g peak | sounds | tap test | crown slip | notes/photo #
```

## 6. Sources

[sg-test]: https://www.scheels.com/p/stone-glacier-col-4800-pack-with-krux-frame/18284-50106-TN
[sg-oneframe]: https://www.stoneglacier.com/blogs/the-vestibule/one-frame-for-every-hunt
[sg-sky]: https://www.stoneglacier.com/products/sky-5900-xcurve-krux
[ssd-hpg]: https://soldiersystems.net/2019/02/13/hill-people-gear-decker-pack-frame/
[carry-hpg]: https://www.carryology.com/reviews-2/hill-people-gear-ute-light-review
[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[eb-mod]: https://kenetrek.com/products/eberlestock-mod-frame-pack
[bh-icon]: https://www.bowhunter.com/editorial/field-test-kuiu-icon-6-6000/558323
[kuiu-wp]: https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper
[gj-akek]: https://gearjunkie.com/outdoor/hunt-fish/akek-alpha-3200-hunting-pack-review
[rs-akek]: https://rokslide.com/forums/threads/lets-debate-akek-is-the-better-hunting-pack-system.442862/page-3
[iso7965]: https://webstore.ansi.org/preview-pages/ISO/preview_ISO+7965-1-2024.pdf
[astm5276]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8210746
[ks2660]: https://members.wto.org/crnattachments/2023/TBT/KEN/23_09673_00_e.pdf
[jotp]: https://environmentalrequirementsandrelatedt.emilspec.com/JOTP-011/JOTP-01100088.html
[des810]: https://www.desolutions.com/resources/mil-std-810-method-516-shock-testing-procedure-iv-transit-drop
[trenton810]: https://www.trentonsystems.com/en-us/resource-hub/blog/mil-std-810-shock-testing-overview-method-516.8
[knapik04]: https://academic.oup.com/milmed/article-pdf/169/1/45/21870283/milmed.169.1.45.pdf
[sciam]: https://www.scientificamerican.com/article/a-parents-dream-bungee-po/
[nature06]: https://www.nature.com/news/2006/061218/full/news061218-8.html
[martin18]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6137106/

- Stone Glacier 340 lb static test: [Scheels listing quoting SG][sg-test]; SG blog "loaded more than 300 pounds ... no signs of stress, damage, or failure" ([SG][sg-oneframe]). Manufacturer claims, not independent.
- Rome L.C. et al., *Science* 309:1725-1728 (2005), doi:10.1126/science.1111063; Rome L.C. et al., *Nature* 444:1023-1024 (2006), doi:10.1038/4441023a. The 1.6x / 3x figures come from secondary coverage ([SciAm][sciam], [Nature News][nature06]). Check against the primary papers before publishing them externally.
- Martin J.-P., Li Q., *Scientific Reports* 8:13775 (2018), doi:10.1038/s41598-018-32175-x ([PMC][martin18]).
- Knapik J.J., Reynolds K.L., Harman E., *Military Medicine* 169(1):45-56 (2004), doi:10.7205/milmed.169.1.45 ([PDF][knapik04]).
- MIL-STD-810H Method 516.8 Procedure IV: secondary summaries ([JOTP][jotp], [DES][des810], [Trenton][trenton810]); confirm against the official text before claiming compliance.
- 14 CFR 25.303 (factor of safety 1.5 on limit loads), standard aerospace practice. Cited from engineering knowledge, not fetched.
