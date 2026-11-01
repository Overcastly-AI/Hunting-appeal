# HA-LS-1: Pack 5200 frame load standard (calibrated, "match the leaders")

Owner: structural-fea-engineer. Status: **adopted for frame v2** (owner decision 2026-11-01, docs/DECISIONS.md:
"Frame strength standard: MATCH THE LEADERS. Realistic field loads, verified by physical prototype load tests").
Executable form: `huntkit/fea/load_standard.py` (cases + factors), applied by `huntkit/fea/sizing5200v2.py`.
Results: [frame_sizing.md](frame_sizing.md).

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
| C1 | static carry (`static_carry`) | 68 kg in the bag, CG 180 mm aft, hips 80 % | 1.0 | **2.0** yield/FPF | 2.0 | limit (= the leaders' 2x static proof) | T1 |
| C2 | stumble / drop-step (`drop_2p5g` code name kept) | as C1 | **2.0** | **1.5** | 3.0 | limit | T1 (300 lb), T4a |
| C3 | side-hill torsion | 25 deg tilt, 30 % downhill bias, downhill strap + lifter slack | **1.6** | **1.5** | 2.4 | limit | T3 |
| C4 | single-stay set-down | impact on one foot + 0.2 friction, inertia relief | **2.0** | **1.5** | 3.0 | limit | T4b |
| C5 | meat shelf heavy-low | 68 kg on the shelf, CG 120 mm aft | **2.0** | **1.5** | 3.0 | limit, primary mission | T2 |
| C6 | tall load | quarter on the shelf, CG 250 mm aft, lashed to the crown | **2.0** | **1.5** | 3.0 | limit | T2 |
| C6p | tall load on extension posts | lashed 220 mm above the crown | **2.0** | **1.5** | 3.0 | limit (accessory) | T2 (posts) |
| C7 | overload haul | **91 kg** on the shelf | **1.6** | **1.0** | 2.1 | **ultimate, no collapse** | T2u |
| C8 | hipbelt-off abuse | 68 kg, 100 % on shoulders + lifters (creek crossing) | 1.5 | **1.0** | 1.5 | ultimate, no damage, no crown slip | T1 variant |

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
| **T2 shelf / tall-load proof** (C5, C6, C6p) | Frame-only / shelf mode: 300 lb on the shelf (meat bags or sandbags in game bags), strapped as in the field. Tall-load variant: 300 lb stacked tall, top lashed to the crown top bar (and to the post bar if posts fitted) | **300 / 136** | Same as T1 |
| **T2u ultimate demo** (C7, and 1.5 x C5) - **P1 only, last test** | Shelf load stepped to **450 lb / 204 kg** (1.5 x 300) and held 30 s. Outdoors, back-up sling, exclusion zone | 450 / 204 | **No collapse**: still carries the load at 30 s. Damage allowed (it's the sacrificial frame). Record first noise / first visible damage load: that is the measured margin |
| **T3 side-hill** (C3) | Rig tilted 25 deg (shim one end of the log or tilt the A-frame), downhill shoulder strap slackened to ~25 % of the uphill tension (crane scale), load pushed 30 % downhill. **240 lb / 109 kg** (1.6 x 150) | 240 / 109 | Same as T1; also crown legs slide freely after unload (no binding = no permanent twist) |
| **T4a drop-step** (C2) | 150 lb in the bag, pack hung on the log. Lift the whole pack by its haul loop with the ratchet strap h mm off the log, release with the snap shackle. Increase h from 10 mm in 5 mm steps until phyphox reads a **2.0 g peak** at the crown (expect 15-40 mm). Then **20 drops** at that height | 150 / 68 at 2.0 g | No damage, tap test clean, crown slip 0, T1(a) re-check within 10 %. **Also record the g-level at each h**: if 2.0 g needs < 10 mm, the 2.0 g limit is too low and the standard must be revisited |
| **T4b set-down** (C4) | 150 lb pack held upright, raised **50 mm (2 in)** and dropped onto ONE stay foot on the gym mat, 5 x each foot. Phone on the crown | 150 / 68 | No damage at the foot boot / wrap / lumbar pan, tap test clean. Record the peak g |
| **T4c empty abuse drop** (MIL-STD-810 Proc IV style) | Empty pack (bag on) dropped from **48 in / 122 cm** onto 19 mm plywood over concrete, 6 orientations: each foot, each side, crown top, back panel | empty | Functional: crown still telescopes and locks, no cracks, tap test clean. Cosmetic scuffs OK |
| **T5 cycle / fatigue** | Dead load 60 lb (0.4 W) in the bag + crank/bungee pulling the bag down 0 -> 180 lb (1.2 W, set with the crane scale at the crank's bottom dead centre): **0.4 -> 1.6 g**. **100,000 cycles** at ~50/min (~33 h; can be split over days). Stop every 25,000 cycles: T1(a) re-check + tap test | 60 -> 240 lb peak | No crack, no debond, **stiffness change <= 10 %** at each stop, crown slip < 1 tooth, pulley webbing not cut by its guides |
| **T6 joint coupons** (before bonding the frame) | 3 x each joint type, made exactly like the frame: (a) bar coped to a stay and carbon-wrapped (T joint), (b) wrap collar over a stay end. Pull the bar out along its axis (a) / the stay out of the collar (b) with the rig (come-along + crane scale) to failure | to failure | Mean failure load >= 1.5 x the largest FEA limit end force for that joint (frame_sizing_cases_19in.md, bonded joints table) and lowest >= 1.25 x. Failure should be cohesive / in the laminate, not a clean adhesive peel (= bad prep) |
| **T7 bushing crush coupon** (before release) | 150 mm stay offcut with the wrap collar + UHMWPE bushing; leg offcut through it; press the leg sideways at the bushing centre (lever or bench vise + crane scale) | 1.5 x the max FEA bushing force, then to failure | No crack, ovalisation <= 0.2 mm after unload at 1.5 x. **This earns the 120 deg contact credit** used in the sizing |

Test order: T6, T7 -> bond P1, P2 -> T1 -> T3 -> T2 -> T4a/b -> T4c -> T5 (P2) -> T2u (P1 last).
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
