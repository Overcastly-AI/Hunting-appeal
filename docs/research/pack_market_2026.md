# Premium framed hunting / meat-hauling packs: market research (Nov 2026)

Owner: research analyst. Date: 2026-11-01. Status: **v1, for the pack-designer and the owner.**

**Why this exists.** The owner rejected Pack 5200 v2 (`designs/pack_5200/DESIGN.md`,
`outputs/screens/20261101_pack3d_hero.png`). Feedback: (1) too boxy and dated-looking, (2) wrong bag
shape and profile, (3) wrong features and layout. The frame and suspension concept was **not**
rejected. The owner's favourite benchmarks are **Stone Glacier (SG)** and **Exo Mountain Gear (Exo)**,
so those two get the deepest treatment (§3.1, §3.2).

**Method and honesty notes.**
- Specs come from manufacturer pages first, then retailers and reviews. Every row is linked.
- Rokslide **articles** and some forum pages returned HTTP 403 to the fetch tool. Where I cite a Rokslide
  thread, the claim came from the search-engine summary of that thread, so treat it as "reported" and
  not as a verified quote.
- Weights are published figures. Brands weigh different things (with or without lid, belt size,
  frame height). Treat differences under ~3 oz as noise.
- "Rated load" is marketing. Nobody publishes a test standard. Most say "150+ lb".
- Visual descriptions in §6 come from me looking at the official product photos (links given). The
  images were viewed, not copied into the repo.
- Units: imperial first here because that's how the market talks. 1 lb = 453.6 g, 1 cu in = 16.39 mL.

Chart: `outputs/screens/20261101_research_1.png` (script: `docs/research/pack_market_chart.py`).

---

## 1. Top findings (read this if nothing else)

1. **The class weight is ~5.1–5.9 lb for a complete ~5,500–6,000 cu in system. Our v2 is 6.64 lb.**
   SG Sky 5900 + Krux is 5 lb 1.4 oz and Exo K4 5000 is 5 lb 13 oz with its lid ([SG][sg-sky], [Exo][exo-5000]).
   The gap is almost entirely suspension. Our frame + lock + belt + harness + back panel + shelf is
   ~4.12 lb (DESIGN.md §11). SG Krux with belt, harness and shelf is 2 lb 7 oz ([SG blog][sg-frames]), and the
   Exo K4 frame system is 2 lb 15 oz ([Exo][exo-frame]). Our 532 g shelf + wings is the biggest single offender.
2. **Nobody sells a boxy bag any more.** Every current leader uses a tall, rounded, **tapered** bag
   (narrow at the hips, fullest at the shoulder blades, domed top). Exo's 5000 is **39 in tall × 10.5 in
   wide × 9.5 in deep** expanded ([Exo][exo-5000]). Ours is 31 × 13.4 × 12.6 in. They get their volume
   from **height and a roll-top**, not from depth. That is the "wrong profile" the owner sees.
3. **The universal meat-hauling method is "bag pulls back, load rides in a sling/shelf against the
   frame."** SG Load Shelf (+2,500 cu in), Exo frame straps in a V, Mystery Ranch Overload, KUIU's
   new Load Sling Mode, Seek Outside load shelf. It's table stakes, not a differentiator. Mystery
   Ranch's original sling patent has **lapsed** (§7).
4. **The biggest complaints are about details, not frames.** SG: a floppy lid on long straps
   ([GearJunkie][gj-sky]), too many straps to rig the shelf, belt pressure points for some hips. Exo:
   identical-looking buckles (8 pairs), thin pocket fabric that tears, a soft lumbar above ~65 lb, belt
   creep or slip for some users, and no rain fly ([Western Hunter][wh-exo], [HuntTalk][ht-sucks]).
5. **"Universal fit" is an open gap, and Exo says so explicitly.** Exo sells 4 frame heights × 5
   belts and argues that "changing the torso setting does not change how tall the frame sits above your
   shoulder" ([Exo][exo-heights]). Our telescoping crown, which moves the lifter anchors with the yoke
   at a constant 41°, **answers that exact objection**. That's our strongest, defensible
   differentiator. Keep it.
6. **2025–26 brought a new generation of frames.** KUIU **ICON 6** has a 13.7 oz thermoplastic
   "3D corrugated" carbon frame, "Flex-Forward" geometry and a Load Sling Mode, and is patent-pending
   ([KUIU whitepaper][kuiu-wp]). SG **Terminus** has its bag sewn to the frame, at 3 lb 15 oz for 7,000 cu in.
   Mystery Ranch has the **MYSTERIUM** frame (Beartooth 85, 6.2 lb), Eberlestock the **Modframe**
   (a flat load panel instead of an L-shelf, "unlimited" torso adjust), Kifaru the **ARK** (a full carbon sheet),
   and **AKEK** is a new carbon-frame entrant.
7. **IP hazard to fix in our design:** Mystery Ranch **US 10,952,523 B2** ("Backpack with pop up
   frame", active to ~2038) claims a frame whose top extends between heights, with load lifters that re-anchor to the
   frame top in extended mode, plus an adjustable shelf between frame and bag. Our **extension-post
   accessory with lifters moved to the post bar** sits close to claim 1 and needs a design-around
   (§7). KUIU's unitary-frame patents (to ~2031) cover one-piece slotted frames, which we don't use.
8. **The premium look is quiet.** Solid earth tones (Ranger Green, Coyote, Graphite), black or
   tone-matched hardware, laser-cut MOLLE, a domed silhouette, and a few angled seam lines. Camo is
   offered as a full colorway by KUIU and Mystery Ranch. SG and Exo sell **no camo at all**, which matches
   the owner's "solid with accents" direction.

---

## 2. Comparison table

Weights are complete systems (frame + suspension + bag, plus lid where noted) unless stated. "Frame wt" =
frame + harness + belt where the brand sells it that way.

| Pack (bag + frame) | Volume cu in | System wt | Frame wt | Rated load | Frame material / architecture | Torso adjust | Meat method | Price (USD) | Sources |
|---|---|---|---|---|---|---|---|---|---|
| **Stone Glacier Sky 5900 + Krux** | 5,400 main / 5,900 w/ lid; up to 8,000 w/ shelf | 5 lb 1.4 oz (M belt) | 2 lb 7 oz | 150+ (tested to 340 lb, no damage) | 4 carbon-composite stays, straight (Krux); fabric frame sheet; 26 in tall | Hook-and-loop harness on frame sheet, "infinitely adjustable" height and strap angle | Integrated Load Shelf: bag pulls off the frame, +2,500 cu in between bag and frame; or frame-only | 725 | [SG][sg-sky], [SG frames][sg-frames], [SG one frame][sg-oneframe], [goHunt][gohunt-sky] |
| **Stone Glacier Sky 5900 + Xcurve** | same | 5 lb 4.5 oz | 3 lb 1 oz | 150+ | 4 curved carbon stays (S-curve for curvier backs) | same | same | 725 | [SG][sg-sky], [SG frames][sg-frames] |
| **Stone Glacier Terminus 7000** | 7,000 + 500 lid; 4,300 bivy | 3 lb 15 oz | integrated | 150+ | 4 carbon stays, **bag sewn to frame**, X-Pac frame sheet | Strap height on frame sheet + lifters | 2,200 cu in **internal** collapsible load cell next to the frame (boned meat only) | 699 | [SG][sg-term], [GearJunkie][gj-best] |
| **Exo K4 5000** | 5,010 bag / 5,658 w/ lid | 5 lb 5 oz; **5 lb 13 oz w/ lid** | 2 lb 15 oz | 150+ | 2 carbon stays + carbon links joined by sewn Cordura; narrow frame; plastic sheet runs from lumbar into belt | **4 frame heights** (22/23.5/25/26.5 in) + micro-adjust harness and lifters | Bag unclips top/sides and hinges ("taco"); load placed high in a V between bag and frame, held by dedicated frame straps; frame-only possible | 699.99 | [Exo 5000][exo-5000], [Exo frame][exo-frame], [Carryology][carry-exo], [Western Hunter][wh-exo], [Packstack][ps-exo] |
| **Exo K4 3600** | 4,268 w/ lid | 5 lb 8 oz | 2 lb 15 oz | 150+ | as above | as above | as above | ~675 | [Carryology][carry-exo] |
| **KUIU ICON 6 6000** (2026) | 6,000 + 700 lid | 6 lb 2.4 oz | **13.7 oz frame only** (Tall) | not published (tested to 125 lb) | Toray **thermoplastic carbon, 3D corrugated** one-piece sheet, "Flex-Forward" geometry, dual bottom stays; made by Re:Build, CO | 2 frame lengths (24.5 / 26.5 in) + ½ in harness steps (hook-and-loop + T-lock) | **Load Sling Mode** (bag + frame become a V compression sleeve), internal meat sleeve, Pack Load Hauler accessory | 599–749 range | [KUIU whitepaper][kuiu-wp], [Bowhunter][bh-icon], [Grand View][gv-icon] |
| **KUIU ICON 6 4500 Divide** | 4,500 + 500 lid | 5 lb 14.2 oz | 13.1–13.7 oz | — | as above | as above | as above | — | [KUIU whitepaper][kuiu-wp] |
| KUIU PRO 6000 (legacy) | 6,000 | ~6 lb 0.8 oz | 11 oz frame + 1 lb 12.8 oz suspension (S/M) | 150 | Patented unitary carbon frame with sliding harness tracks | Slotted harness tracks | Bag between frame and load | — | [KUIU suspension][kuiu-pro], [GearJunkie][gj-pro], [Huntin' Fool][hf-pro] |
| **Mystery Ranch Beartooth 85** | 5,095 | 6.2 lb | n/p | not published | **MYSTERIUM** frame (successor to Guide Light MT) | Telescoping adjustable yoke | **Overload**: bag separates, load in sling against frame | 650 | [MR][mr-bt85], [Rokslide thread][rs-myst] |
| **Mystery Ranch Metcalf 100** | 6,100 | 6.1 lb (MR workbook: 5.97, stripped 5.1) | n/p | not published | Ultra Light MT frame, 26 in | Telescoping yoke (patented fit system) | Overload | 625 | [MR][mr-met], [goHunt][gohunt-met] |
| **Seek Outside Unaweep 6300** | 6,300 + pockets | **3 lb 11 oz** (Ultra 200X) | Revolution 24 in: 2 lb 9 oz | **200+** (frame >300 vertical) | 6061-T6 aluminium U-frame, "patented articulating", 7075 cross stays; hipbelt bolted to the frame | Frame height 24–28 in; harness micro-adjust | Load shelf between frame and bag; XL load shelf option | 621 | [Seek 6300][seek-6300], [Seek Revolution][seek-rev] |
| **Kifaru ARK + Absaroka** | 6,580 + shelf | 6 lb 4 oz | ARK advertised 3.1 lb | not published (82 lb test reported) | **Full carbon sheet** with laser-cut MOLLE, 22 / 25 in | Simple strap re-position | Load sling / shelf between bag and frame | 877 (frame 500) | [GearJunkie][gj-best], [GJ ARK][gj-ark], [Rokslide search][rs-ark] |
| **Initial Ascent IA5K** | 4,650 / 5,200 w/ lid | n/p ("1877", unit unclear) | frame ~18 oz (reported, IA4K) | not published ("150 lb of meat" user claims) | Triaxial carbon "Integrous" frame, wider than most, curved to the spine | 18–22 in torso; women's Invictus 13–17 in | Quarters on frame sides; Pannier Load Carrier accessory | 749.99 | [Gearfool][gf-ia], [IA physics][ia-phys], [Born Hunting][bh-ia] |
| Sitka Mountain Hauler 6200 | 6,200 | 6.4 lb | n/p | 150 | 6061-T6 aluminium tube frame | Waist sizes only | Built-in meat shelf | ~590 (4000) | [Sitka][sitka], [Ecotone][sitka-6200] |
| Eberlestock Modframe (2025) | frame pack, 26 × 10 in | 4 lb 8 oz | — | n/p | Aluminium + polycarbonate | "Unlimited" torso height | **Low-profile load panel replaces the L-shelf** | 349 | [Kenetrek][eb-mod], [Eberlestock][eb-intro] |
| Eberlestock Brute 6500 (2026) | 6,500 | 6 lb 13 oz | — | n/p | Modframe-derived internal | n/p | n/p | ~863 CAD | [Hero][eb-brute] |
| AKEK Alpha 3200 (new) | 3,200 + meat shelf | 5 lb 10–11 oz | — | 150 (frame) | Curved carbon, 25 in, 3 sizes; made in Vietnam, frames moved to USA after a cliff-test crack | — | 2 shelves (bag/frame, daypack/bag) | 399–570 | [GearJunkie][gj-akek], [GJ best][gj-best], [Rokslide][rs-akek] |
| Hill People Gear Ute Light | ~3,170 (52 L) | 3.75 lb | — | 150 (Ute chassis "300 lb capable") | Framesheet + stays | — | — | — | [Carryology][carry-hpg], [SSD][ssd-hpg] |
| Barney's (Frontier Gear of Alaska) Freighter + bag | — | n/p | n/p | n/p | Classic aluminium freighter frame + folding shelf | Fixed | Folding shelf; the bag takes the heavy load | n/p | [Rokslide][rs-barneys], [Rokslide 2026 listing][rs-barneys2] |
| **Our Pack 5200 v2 (rejected)** | 5,200 + 507 lid | **6.64 lb** | **4.12 lb** (frame + lock + belt + harness + back + shelf) | 150 / 200 overload | Bonded carbon tubes, telescoping crown | Continuous 15–23 in, while worn | 250 mm pull-back bay + wings, frame-only | — | `designs/pack_5200/DESIGN.md` §11 |

n/p = not published. **Paradox Packs** is the predecessor of Seek Outside's frame (the Evolution frame,
2 lb 8 oz, torso adjustable while worn), since replaced by the Revolution ([Rokslide][rs-paradox], [BPL][bpl-paradox]).
**Argali** sells game bags, tents and knives, not frame packs ([onX][onx-argali], [Scheels][scheels-argali]).
**Sitka / Mystery Ranch "collab"**: I found no evidence of a current joint pack. Sitka's Mountain
Hauler uses Sitka's own aluminium frame ([Sitka][sitka]). One forum seller's "Guide Lite MT"
attribution looks like an error.

---

## 3. Per-brand summaries

### 3.1 Stone Glacier (owner favourite): deep dive

**Line-up (2026).** Frames: **Xcurve** (curved stays, 3 lb 1 oz with M belt), **Krux** (straight stays,
2 lb 7 oz; the Krux EVO was discontinued and replaced by a renamed Krux), and R3 (military). Bags from the
Approach 2800 up to the Sky Guide 7900, plus the **Terminus 7000/8700**, which has an integrated frame
([SG frames][sg-frames], [goHunt EVO][gohunt-evo], [Rokslide EVO thread][rs-evo]).

**Frame and fit.** Four carbon-composite stays sewn into a fabric frame sheet. The harness attaches by
hook-and-loop, so its height and strap angle are "infinitely" adjustable. SG fits Krux to torsos of 19 in and
under and to flatter backs, and Xcurve to curvier backs ([SG one frame][sg-oneframe]). Frame height is a
fixed 26 in. Rated 150+. The final design survived 340 lb in test ([SG][sg-sky]).

**Bag silhouette and how it mates to the frame** (from the official photos [Sky 5900 gallery][sg-sky]):
- Side view: a **teardrop**. It's thin at the hipbelt, swells to its deepest point at the shoulder blades,
  and the top **domes** over into the lid. The front face is a smooth convex curve, with no flat
  faces and no hard vertical corners.
- Front view: an **inverted taper**. It's narrowest at the bottom, so it clears the arms and the butt of a
  slung rifle, and widest high up.
- The bag hangs from the frame's top and sides and pulls back off the frame. With the shelf loaded
  (photo 1 shows a white dry bag in the gap), the bag hinges at the bottom and stays on the shelf straps.
- Compression is a dense black-webbing cage: about 4 horizontal straps per side plus verticals over
  the top. It reads technical but busy.
- Lid: a separate floating lid on long straps, needed because the bag expands off the frame.

**Access and pockets.** Full front-panel zip (YKK #10), a 22 in vertical front pocket (spotting scope), a
front zip pocket, large open-top side pockets (tripod or rifle stock), and attachment points for the
"Swing Out" pockets. Hydration sleeve is an add-on ([SG][sg-sky]).

**Fabrics.** 500D Cordura bag. X-Pac on high-wear areas, the shelf and bag backs (a waterproof film, so blood
doesn't wick into the bag). Duraflex 1 in hardware ([SG one frame][sg-oneframe]).

**Praise.** "Carries like a dream with heavy weight" (~110 lb of elk + gear) ([GearJunkie][gj-sky]).
Compresses to a day pack yet hauls 100+ lb. Durable, made in the USA, good customer service. GearJunkie's best
overall for 2026, 9.2/10 ([GJ best][gj-best]). Used from 20 lb day loads up to 115 lb pack-outs
([Rokslide review summary][rs-sky]).

**Complaints and wishes.**
- **Lid**: floppy, long-strapped, must be repositioned, awkward when the pack is empty ([GearJunkie][gj-sky], [Rokslide][rs-sky]).
- **Outer pockets** get squeezed to nothing when the bag is full ([Rokslide][rs-sky]).
- **Capacity**: 5900 is tight for solo meat plus camp, or 10 days ("wished for the 6900") ([Rokslide][rs-sky]).
- **Shelf and bag swap** means "many straps to adjust". The belt is hard to loosen (fixed on newer belts). It feels rigid
  with light loads compared with Exo. Hipbelt pressure on the hip points for some users ([HuntTalk][ht-sucks], [Rokslide][rs-exo-sg]).
- **Price creep**: frame, bag, lid and pockets are all extra (Sky 5900 $725, lid $42) ([GearJunkie][gj-sky]).

### 3.2 Exo Mountain Gear (owner favourite): deep dive

**Line-up.** One frame (K4) in **4 heights** × **5 belt sizes** (XS–XL), plus the EXS short/women's/youth
system. Bags: 2200 (panel loader), 3600, 5000, 7200 (roll-tops). The K3 had a formed **titanium** frame. The K4 moved
to carbon stays ([Exo frame][exo-frame], [Carryology][carry-exo], [Rokslide search][rs-k4]).

**Frame and fit.** Two vertical carbon stays plus carbon links, joined by sewn Cordura into one
unit with some designed-in flex. A plastic reinforcement runs from behind the lumbar pad into the
hipbelt. The frame is deliberately **narrow** so the shoulders and hips can counter-rotate (off-trail, shooting with
the pack on) ([Exo narrow][exo-narrow]). Exo's fit philosophy: the frame top should sit **2–4 in above the
shoulder** for a positive lifter angle, and "pack frames offered in one height may not fit you well, even if
those frames have an adjustable torso range" ([Exo heights][exo-heights]). Steve Speck: "The number one
component of a pack's performance is the hipbelt." Belts are sized at the iliac crest ([Exo belts][exo-belts]).
On the K4 the shoulder straps reportedly anchor to the belt, not the frame ([Rokslide search][rs-k4]).

**Bag silhouette and mating** (from the official photos [K4 5000][exo-5000-img], [K4 frame][exo-frame-img]):
- A **tall, slim, near-cylindrical** roll-top: 39 × 10.5 × 9.5 in expanded, compressing to 25 in tall
  and 3 in deep ([Exo 5000][exo-5000]). The top is rounded with a two-compartment lid. A full-height
  **stretch front pocket** gives a clean vertical "spine" on the front. Long pleated side pockets
  run the full height.
- The frame alone looks like a **ladder**: a narrow coyote/green panel with 4 pairs of buckled
  cross-straps (these are the meat-haul straps) and laser-cut MOLLE on the belt wings.
- The bag attaches at the top and sides. With the bottom left attached, it **hinges open "like a taco"**.
  Meat goes **high** in the V between bag and frame on its own straps. Remove the bottom strap for
  a wider shelf if needed ([Carryology][carry-exo], [Western Hunter][wh-exo]).

**Access and pockets.** Roll-top + horseshoe front zip (5000) or lengthwise zip (7200). Zippered stretch front
panel. Full-length pleated side pockets for a spotting scope. Top-entry stretch side pockets. An angled
insulated Nalgene pouch between belt and bag. PALS on the belt and harness ([Exo 5000][exo-5000], [Carryology][carry-exo]).

**Praise.** Hipbelt comfort (big contact area, doesn't creep). Quiet. Scales from a day pack to 90–100 lb
mule-deer-plus-camp pack-outs ([Western Hunter][wh-exo]). "Harness is freaking outstanding"
([Rokslide search][rs-exo-sg]). Finish more refined than SG. Narrower and more tapered than the K3, with better head
clearance ([Packstack][ps-exo]). Comfortable at 70–80 lb ([Packstack][ps-exo]).

**Complaints and wishes.**
- **8 pairs of look-alike compression buckles**: users clip the wrong ones. Wish: colour-coded or keyed buckles ([Western Hunter][wh-exo]).
- **No proper rain fly**: the dry-bag liner is $99.99 and 9.5 oz ([Western Hunter][wh-exo]).
- Wish: a lid that converts to a hip pack ([Western Hunter][wh-exo]).
- **Thin pocket fabric** tears on rock. Belt buckle tails are hard to grab from fully loose. A **soft
  lumbar** struggles above ~65 lb ([HuntTalk][ht-sucks]).
- Some report the belt **slipping or settling**, frame movement, and creaks on first-generation units ([Rokslide search][rs-exo-sg]).
- **Narrow bag bottom** is awkward for a bulky sleeping bag. The 5000 is tight past a week of winter kit ([Packstack][ps-exo]).
- You must guess a frame height × belt size online, which is a fit risk ([Packstack][ps-exo]).
- Seams seep in long downpours ([Carryology][carry-exo]).

### 3.3 KUIU
- **ICON 6 (2026)** is a clean-sheet frame: a 13.1–13.7 oz Toray **thermoplastic** carbon sheet with **3D
  corrugations** (ridges and channels). KUIU claims a flat 0/90 laminate would need to be 5× thicker. It "yields
  rather than shatters". Flex-Forward: vertically stiff, laterally compliant. Taller and wider than the old ICON,
  with dual bottom stays. **Patent-pending** ([KUIU whitepaper][kuiu-wp]).
- Meat: **Load Sling Mode** turns the bag + frame into a V-shaped compression sleeve, so the load isn't
  point-loaded on a shelf. There's an internal meat sleeve and a **horseshoe zip** big enough for a quarter or an assembled rifle
  ([KUIU whitepaper][kuiu-wp]).
- Fit: 2 frame lengths. Harness in ½ in steps with hook-and-loop + T-lock. Belts S/M to XXL/3XL plus a women's belt.
  KUIU asks for a lifter angle of ≤ 45°.
- Bag dims: the 4500 is 31.1 × 12.5 × 12.25 in. The 6000 is 32.5 × 21 (incl. pockets) × 13.5 in.
- Reviews: Bowhunter carried 125 lb with "no sway, creak or rock". The lumbar needed one re-adjust ([Bowhunter][bh-icon]).
- Legacy PRO: an 11 oz unitary carbon frame (the patented slotted design, §7) rated 150 lb. Forum users report
  squeaks and occasional cracks ([search summary][kuiu-legacy]).

### 3.4 Mystery Ranch
- Philosophy: the bag shapes the load, and a separate mainframe transfers it. Frames are built **flat** and arc under
  lifter tension ("active framing"). The ideal load is "about twice as wide as it is thick". Telescoping yoke.
  Lumbar wrap and fit system are patented ([MR architecture][mr-arch]).
- **Beartooth 85** (MYSTERIUM frame, 6.2 lb, 270° duffel zip, Overload, $650). **Metcalf 100** (6.1 lb, 3-zip,
  Ultra Light MT 26 in frame, $625) ([MR][mr-bt85], [MR][mr-met]).
- Complaints: heavy, "old-school, clunky", weak lifters, hot spots from the belt, a lid that isn't bladder-compatible.
  Praise: GearJunkie's "most durable", and Overload works ([HuntTalk][ht-sucks], [GJ best][gj-best]).

### 3.5 Kifaru
- **ARK** frame: full carbon sheet, laser-cut MOLLE attachment, fold-over top hang point, 22 / 25 in, ~3.1 lb,
  $500 ([GJ ARK][gj-ark], [Rokslide search][rs-ark]). Duplex frames (aluminium stays) are the older platform.
- Praise: hauls 80–140 lb ("140 doesn't feel bad"). Complaints: heavy, too many straps, floppy hip pockets,
  a thin lumbar for some, a tall user found the lifter angle insufficient ([HuntTalk][ht-sucks], [Rokslide search][rs-ark]).

### 3.6 Seek Outside (and Paradox)
- **Revolution** frame: 6061-T6 aluminium U-frame, height adjustable 24–28 in, 7075 cross stays, rated 200+
  lb. "Patented articulating frame" (number not published). Hipbelt **bolted to the frame**, 4-way forward pull
  ([Seek Rev][seek-rev], [Seek 6300][seek-6300]).
- Lightest high-capacity system in the market (Unaweep 6300 at 3 lb 11 oz) and the highest rating.
- Complaints: Gatekeeper clips are fiddly with gloves, the laminate is loud in the cold, the lid is weak, the bag-to-frame
  interface looks less clean, and the belt wrap causes hip-flexor discomfort for some ([HuntTalk][ht-sucks]).

### 3.7 Others
- **Initial Ascent**: wide, spine-curved triaxial carbon frame, "rectangular wedge" bags, and a 2-stage
  adjustable lumbar with "Slip-not" grip. The IA5K is exactly 5,200 cu in with lid, $749.99. New bags slip over frame
  slots ([IA physics][ia-phys], [Gearfool][gf-ia], [Born Hunting][bh-ia]).
- **Eberlestock**: the 2025 Modframe swaps the L-shelf for a **flat load panel** to keep weight close, with "unlimited"
  torso height ([Kenetrek][eb-mod]). The Mainframe is the heavy-hauler classic (static-tested to 1,300+ lb).
- **Hill People Gear**: Ute / qui-Ya chassis billed as "300 lb capable". The Ute Light is 3.75 lb and 150 lb ([SSD][ssd-hpg], [Carryology][carry-hpg]).
- **Barney's / Frontier Gear of Alaska**: an aluminium freighter frame + bag, the Alaskan guides' standard for moose.
  Durable for 20+ years but pricey, and "fits bigger guys better" ([Rokslide][rs-barneys]).
- **New entrants since 2023**: KUIU ICON 6, SG Terminus, MR MYSTERIUM, Kifaru ARK, Eberlestock Modframe/Brute, **AKEK**
  (carbon, Vietnam-made; its first frames cracked in a cliff test and production moved to the USA), **Latitude Praxis**
  (carbon + 7075, whitetail), and a Browning carbon pack that a forum user says looks like the AKEK frame
  ([GJ best][gj-best], [Rokslide][rs-akek]).

---

## 4. Pain-point synthesis (ranked by how often they recur)

| # | Pain point | Who it hits | Evidence | Our opportunity |
|---|---|---|---|---|
| P1 | **Hipbelt / lumbar**: slipping, hot spots on the iliac crest, a soft lumbar above ~65 lb, belt hard to loosen | Exo, SG, MR, Kifaru, Seek | [HuntTalk][ht-sucks], [Rokslide][rs-exo-sg], [Packstack][ps-exo] | Firm 2-stage lumbar + wing cant (we have the 0/5/10° cant) + a grippy lumbar face; **a pull-forward belt with a gloved tab** |
| P2 | **Fit risk when buying online**: guessing a frame height × belt size | Exo (4×5 grid), SG (Krux vs Xcurve), KUIU (2 lengths) | [Exo heights][exo-heights], [Packstack][ps-exo] | **One frame, continuous torso, lifters that track**: the crown is the answer. Market it as "no wrong size" |
| P3 | **Meat-mode rigging is fiddly**: many straps, look-alike buckles | SG, Exo | [HuntTalk][ht-sucks], [Western Hunter][wh-exo] | **Colour/shape-keyed buckles**, 3-step meat mode, straps that stay attached to the frame |
| P4 | **Lids**: floppy, long straps, not bladder-compatible | SG, MR, Seek | [GearJunkie][gj-sky], [HuntTalk][ht-sucks] | Lid with **short self-adjusting rear straps on frame-mounted sliders**, so it rides the bag as it expands |
| P5 | **Pockets collapse when full, or tear** | SG (squeezed), Exo (thin stretch) | [Rokslide][rs-sky], [HuntTalk][ht-sucks] | Pockets mounted to the **frame wings or belt**, not the bag skin. Abrasion panels on the stretch pockets |
| P6 | **Capacity cliff**: 5,500–6,000 cu in is "tight" with meat + camp | SG 5900, Exo 5000 | [Rokslide][rs-sky], [Packstack][ps-exo] | Roll-top or extension collar + a shelf bay. Effective volume 5,200 base → ~8,000 with the bay |
| P7 | **Weather**: no rain fly, seams seep, $100 dry-bag liner | Exo, IA, KUIU (not seam-taped) | [Western Hunter][wh-exo], [Carryology][carry-exo] | Integrated stowable fly in the base, or laminate + taped bottom |
| P8 | **Women / short torsos** underserved; "pink-it-and-shrink-it" fails | all | [Rokslide][rs-women], [BPL][bpl-women] | Continuous 15–23 in torso + S-strap + conical belt cant. Already in our spec |
| P9 | **Frame noise / creak / cracking** | early K4, KUIU PRO, AKEK gen 1 | [Rokslide search][rs-exo-sg], [Rokslide][rs-akek] | Bonded joints in shear, UHMWPE bushings. Publish a **drop/cliff test** video (the Rokslide norm) |
| P10 | **Price creep**: frame, bag, lid, pockets, fly all sold separately | SG, Exo, Kifaru | [GearJunkie][gj-sky], [GJ best][gj-best] | Sell a complete kit (lid, fly, belt pouches included) |

**Meat hauling specifically.** The consensus in 2026 is **load against the frame, high and tight, between the
frame and the bag** (Exo says "place the load high". MR says "bulk of the weight closest to your back"). There are two
schools of thought on how the load is supported:
- **Shelf** (SG, Seek, MR Overload, Barney's): the load sits on a floor.
- **Sling or V-compression** (Exo, KUIU ICON 6, Eberlestock Modframe panel): the load is squeezed against the frame, with no
  point load on a shelf.

Users increasingly prefer the second for boned meat, and want a shelf for bone-in quarters. **A design that does both
with the same straps** is the best of both.

**Universal fit specifically.** Today "universal" is sold as a matrix of SKUs (Exo has 20 frame × belt combos).
Mystery Ranch and Eberlestock adjust the yoke on a fixed frame, which is exactly the case Exo criticises,
because the lifter angle collapses for short users. Nobody in this segment sells a **frame whose lifter anchor moves
with the yoke**. That is our white space.

---

## 5. Design-language analysis: what reads "modern premium" in 2026

Observed from official product imagery: [SG Sky 5900 gallery][sg-sky], [SG Terminus][sg-term], [SG Xcurve frame][sg-xcurve],
[Exo K4 5000][exo-5000-img], [Exo K4 frame][exo-frame-img], [KUIU ICON 6 4500][kuiu-4500], [KUIU ICON 6 6000][kuiu-6000].

1. **Silhouette: a tapered teardrop, never a box.** Narrow at the hipbelt (so arm swing and a slung rifle butt
   clear it), fullest around the scapulae, domed top. KUIU says the shape "moves weight higher and closer to the
   body" ([KUIU whitepaper][kuiu-wp]). Seek's 6300 is 47 in circumference at the top and 45 at the bottom ([Seek 6300][seek-6300]).
2. **Slim depth.** Exo 9.5 in, KUIU 4500 12.25 in, SG roughly 11–12 in (photo estimate, not published).
   Volume comes from **height** (Exo 39 in expanded, Seek 45 in unrolled) and a roll-top or collar. **Our 12.6 in-deep,
   31 in-tall box is the outlier.**
3. **Curved back and S-profile.** The SG Xcurve stays are visibly S-curved. KUIU's frame bends forward at the top
   ("Flex-Forward"). IA's frame "follows the spine". The bag's back panel follows that curve, so in side view the
   whole pack hugs the body like a shell.
4. **Front face as one clean element.** Exo uses a full-height stretch "spine" pocket. SG uses a long vertical scope
   pocket with a full front zip. KUIU uses a horseshoe zip with angled seams. A single dominant vertical gesture on the
   front, not a grid of patches.
5. **Panel lines that follow load paths.** KUIU's front uses angled seams converging toward the frame. Our owner's "angular
   functional seam lines" fit here, provided they **run with the taper** (converging downwards), not as
   horizontal bands.
6. **Hardware is tone-on-tone or black.** No contrast buckles except a single accent. SG uses black webbing on Ranger
   Green. KUIU uses grey webbing on Ash.
7. **Colour.** Solid earth tones dominate: SG Ranger Green, Foliage, Graphite (Terminus). Exo Coyote, Ranger.
   KUIU Ash, Evergreen. Camo is a **colourway option** at KUIU and MR (Vias/Valo, Optifade) and **absent** at SG and Exo.
   Camo as accents is therefore unclaimed territory, but keep it to 2–3 shards that sit on wear zones.
8. **Laser-cut MOLLE** (Exo belt, Kifaru ARK sheet) replaces sewn PALS. It reads modern and saves weight.
9. **Frame as a visible design object.** Exo's "ladder" frame and KUIU's corrugated sheet with "ICON 6000"
   moulded lettering. The frame is part of the brand look.

What made our v2 look dated: flat faces with hard vertical edges, a deep square section, a separate box-shaped lid sitting on a
flat top, horizontal strap bands, and camo shards placed as decoration across flat panels.

---

## 6. IP notes (not legal advice: get a patent attorney's freedom-to-operate opinion before tooling)

| Patent | Owner | Status (Google Patents estimate) | What it claims (plain words) | Risk to us | Design-around |
|---|---|---|---|---|---|
| **US 10,952,523 B2** "Backpack with pop up frame" ([GP][pat-523]) | Mystery Ranch | **Active, to ~2038-10** | Claim 1: external frame + ≥1 adjustable pole moving the frame top between a daypack height and an extended height; a load lifter that attaches to the bag top in daypack mode and to the **frame top in extended mode**; **adjustable shelf** between frame and bag. Claim 9: same without the shelf. Claim 13: telescoping poles | **HIGH for our extension-post accessory** (posts raise the frame top, and the lifters move to the post bar), and moderate for the crown itself if its role is described as raising the frame for loads | Lifters **never move** to the post bar (they stay on the crown, which tracks the torso, not the load height). Posts are pure lash points that don't change the frame top used by the harness. Get an opinion on whether a torso-tracking crown is a "frame top height" change under claim 1 |
| US 8,579,171 B2 "Backpack frame and bag system" (the sling between frame and bag) ([GP][pat-171]) | Mystery Ranch | **Expired** (fees; nominal 2025-03) | Adjustable sling between frame back and bag front, with a pass-through cutout | None now | Free to use the sling / pull-back concept |
| US 8,561,866 B2 / US 8,950,644 B2 "Backpack frame system" ([GP][pat-866]) | Mystery Ranch | 8,561,866 **expired**; check 8,950,644 | Yoke sliding on the frame, held by hook-and-loop, released with an adjuster sheet | Low (we use a crown + rack, no hook-and-loop) | — |
| US 2014/0263519 "Backpack frame system with slotted frame" ([FPO][pat-519]) | Mystery Ranch | Unknown; check grant status | Slotted frame gap receiving a sling | Low–medium if our shelf straps pass through a frame slot | Anchor straps to nodes, not through slots |
| US 8,162,194 "Backpack with side bolsters" | Mystery Ranch | 2012 grant, likely expiring ~2028–30 | Side bolsters in sleeves stabilising the load | Low | — |
| **USRE48,093 E1** "Backpack frame" ([GP][pat-re093]) | KUIU | **Active, to ~2031-07** | **One-piece** frame with elongated slots for sliding shoulder straps, a U-shaped lower tongue to the belt, side stays curving up and out | Low: we're a multi-part bonded tube frame with a crown, not a unitary slotted sheet | Don't adopt a one-piece slotted sheet with a U-tongue |
| US 9,095,203 B2 "Unitary composite backpack frame with upper stays" ([GP][pat-203]) | KUIU | **Active, to ~2031-07** | Unitary laminated frame with a core, central opening, open tracks for strap sliding, U-tongue, narrowing downwards | Low (same reason) | same |
| US 2018/0125210 "Pack frame" ([GP][pat-210]) | KUIU | **Abandoned** 2019 | Stays flaring up and out; bottom slides into a belt pocket | None | — |
| KUIU ICON 6 "3D corrugated" frame | KUIU | **Patent-pending** ([KUIU whitepaper][kuiu-wp]) | Corrugated thermoplastic carbon sheet | Medium if we went to a corrugated sheet | Avoid corrugated-sheet frames. Our tube frame is clear |
| Seek Outside "patented articulating frame" | Seek Outside | Number not published; not found in search | Aluminium U-frame with articulating hipbelt bolted on | Unknown; **our centre-pivot hipbelt should be cleared** | Ask counsel to search the assignee "Seek Outside" / inventor; check A45F 3/08 and 3/10 |
| US 2015/0157115 "Backpack external frame and suspension system" ([uspto.report][pat-115]) | Patrick Smith (Kifaru founder); assignee not shown | Application; check status | Torso pads pivot/slide relative to upright members | Low–medium if our lumbar or back pads pivot on the stays | Keep pads fixed; pivot only at the belt |
| SG, Exo | — | **No patents found** for assignee "Stone Glacier" or "Exo" | — | Low (but trade dress: don't copy the SG X-pattern webbing cage or Exo's ladder frame look) | Original visual language (§8) |

Prior art that helps us: telescoping frame bars with detents, US 4,286,739. Hip-tube posts set for
torso length, US 3,889,859 ([search summary][pat-search]). Telescoping torso adjustment is old. The specific
claim combinations above are what to avoid.

---

## 7. What a state-of-the-art 5,200 cu in meat hauler should be in 2026

Each recommendation cites the evidence it rests on.

### 7.1 Targets

| Item | Target | Our v2 | Rationale / source |
|---|---|---|---|
| Complete system (frame + belt M + harness + bag + lid) | **4.9–5.5 lb (2.2–2.5 kg)**; stretch 4.75 lb | 6.64 lb | Leaders sit at 5.1 lb (SG Krux) to 5.8 lb (Exo 5000 + lid); [SG][sg-sky], [Exo][exo-5000] |
| Frame + suspension + shelf, no bag | **≤ 2.75 lb (1.25 kg)** | 4.12 lb | SG Krux 2.44, KUIU PRO 2.49, Seek 2.56, Exo 2.94 |
| Bag + lid + pockets | ≤ 2.4 lb (1.09 kg) | 2.39 lb (1.08 kg) | SG Sky bag 2 lb 4 oz; Exo 5000 bag 2 lb 6 oz. Already OK |
| Shelf / sling + meat straps | ≤ 7 oz (200 g) | 18.8 oz (532 g) | SG's shelf is integral to 2 lb 7 oz |
| Rated load | 150 lb rated; publish a **drop/cliff test** and a 300+ lb static test | 150/200 | SG 340 lb test; Seek 200+; the Rokslide cliff test is the de facto public standard ([Rokslide][rs-akek]) |
| Main bag | 5,200 cu in (85 L) **incl. collar**, depth **≤ 10.5 in (270 mm)** at mid-height, ~36–38 in tall packed | 12.6 in deep, 31 in tall | Exo 9.5 in, KUIU 12.25 in |
| Meat bay | +2,000–2,500 cu in between bag and frame | 40 L ≈ 2,440 cu in | SG +2,500 |
| Torso range | 15–23 in continuous, lifter angle 35–45° at all settings | ✓ | KUIU ≤ 45°; Exo frame top 2–4 in above shoulder |

### 7.2 Frame architecture options, ranked

1. **Keep the v2 concept, but slim it: two bonded carbon stays + telescoping crown + lumbar plate,
   with a fabric frame sheet replacing the mid bar and wings.** Our crown is the only thing that solves P2. Go
   from three cross members to crown + lumbar plate, and let a tensioned X-Pac-class frame sheet
   take the shear, as SG's sewn sheet and Exo's sewn-Cordura links do. Size to **~400 g frame + ≤ 60 g lock**. It's
   buildable without an autoclave and the owner already approved it. **Recommended.**
2. **Narrow "spine" frame**: two stays converging toward the lumbar (Exo-like narrow waist) with the crown
   on top. Better counter-rotation ([Exo narrow][exo-narrow]) and a natural taper for the bag. It costs some
   torsional stiffness for frame-only quarters, so the FEA must check that. A good variant of #1. The FEA decides.
3. **Corrugated or moulded carbon sheet** (ICON 6 / Kifaru ARK style). The lightest frame mass, but it needs
   thermoforming tooling, isn't beginner-buildable, and runs into KUIU's patent-pending. Not now.
4. **Aluminium U-frame** (Seek). The cheapest and highest rated, but it contradicts the owner's carbon decision and Seek's
   patent is uncleared. Fallback only.

### 7.3 Bag silhouette (the owner's main objection)

- **Tapered teardrop in both views**: bottom width ~9 in (230 mm) at the belt, rising to ~12 in (305 mm)
  at the shoulder blades. Side profile 7 in deep at the bottom swelling to ~10.5 in, then **domed** into the top.
- Volume from **height**: ~34 in body + an ~8 in **roll-top or extension collar** (both Exo and Seek use
  roll-tops; it also kills the floppy-lid problem).
- Back panel follows the stay curve. **No hard vertical corners**: radius every edge ≥ 40 mm, or use a
  3-panel "boat" section (front + 2 side gores) instead of a 6-panel box.
- **One dominant front gesture**: a full-height vertical pocket or a horseshoe zip, plus angled seam lines converging
  downward that carry the camo accents.

### 7.4 Suspension features

- Firm **2-stage lumbar**, swappable or adjustable (IA, KUIU, and the Exo complaint P1). Grippy face fabric.
- Belt: **pull-forward** with gloved tab ends (fixes Exo's tail complaint). Keep the 0/5/10° wing cant and the S/M/L/XL swap.
- Lifter anchors on the crown at 40–45° (keep). Two-way rack lock (keep), and add a **visible torso scale**.
- Harness J/S straps (keep).
- **Keyed meat-mode buckles**: a different buckle shape or colour for bag straps vs meat straps (fixes Exo's 8-pair confusion).
- Lid on **frame-mounted sliders**, so it re-centres automatically as the bag pulls back (fixes SG's floppy lid). It
  converts to a hip pack (Exo wish).
- **Stowable rain fly** in a base pocket (Exo wish), or a taped laminate base.
- Pockets on frame wings or belt so they don't collapse with a full bag (SG complaint).

### 7.5 Meat mode

- **One strap set, two uses**: wide (38 mm) frame-mounted straps make a **V-sling** for boned meat (the KUIU/Exo
  approach), and the same straps clip to a **fold-down shelf lip** for a bone-in quarter (the SG approach). The sling
  concept is free to use (MR '171 expired). Keep it clear of the '523 claim combination (§6).
- 3 steps: unclip 2 top + 2 side bag straps, hinge the bag back on its bottom, load high and tight, cinch.
- Blood side: TPU/X-Pac frame face and bag back, plus drain grommets (already in spec).

---

## 8. Three design directions (each beats SG and Exo while looking original)

All three keep the approved frame/suspension concept (telescoping crown, rack lock, pivot belt,
interchangeable belts and straps). They differ in bag, meat mode and look.

### Direction A: **"Spine"** (the slim alpine hauler)
- **Look**: a narrow, tall teardrop roll-top (≈ 10 in deep, 36 in packed height) on a visibly narrow waisted frame.
  The front is one full-height **asymmetric** stretch-and-laminate panel running from the right hip to the left
  shoulder. That diagonal is the brand signature and isn't Exo's centred spine. Camo appears only on the diagonal
  panel edge and the belt wings. Colorways: solid earth tone with matched hardware.
- **Beats Exo**: one frame for every torso (no 4 × 5 SKU guess), keyed buckles, an abrasion-faced stretch pocket, a firm 2-stage lumbar.
- **Beats SG**: no floppy lid (roll-top + slider lid/hip-pack), lighter than the Xcurve, narrow waist for arm swing.
- **Meat**: V-sling high against the frame. The bag hinges back on its bottom.
- **Target**: 5.0 lb. **Risk**: narrow bottom is bad for bulky sleeping bags (the Exo complaint) → flare the lowest 6 in slightly.

### Direction B: **"Shell"** (the curved-back clamshell, max meat)
- **Look**: a clamshell bag whose frame-side face is a **rigid-ish curved shell** (laminate + 1 mm HDPE) following the
  stay S-curve. In side profile the whole pack reads as one smooth arc hugging the back. A horseshoe front zip
  opens the full bag, like a suitcase. Wide-radius edges, angled seams converging to the belt, camo on the lower
  side gores (brush-strike zone).
- **Beats SG and Exo** on meat: the bag **hinges back on its bottom like a clamshell** and the space against the frame is
  a sealed, washable TPU **"meat cradle"** (V-sling + fold-down shelf lip, same straps). Loading takes 3 steps, with no strap
  re-routing. The clamshell zip gives full gear access with meat aboard (neither competitor allows that).
- **Target**: 5.3–5.5 lb. **Risk**: shell stiffness vs weight. Check the patent opinion on shelf + extension combos (§6).

### Direction C: **"Modular Core"** (one frame, two bag lengths, complete kit)
- **Look**: a mid-depth teardrop with a removable **front "saddle" panel** (a zipped-on outer pocket shell in camo or solid).
  The core bag stays solid colour. The owner gets an "edgy" accent that's swappable, and colourways become cheap SKUs.
  Panel lines are a chevron that points down to the belt.
- **Beats both** on value and fit: sold as a **complete kit** (lid-hip-pack, fly, belt pouches, rifle boot included). The
  continuous torso + 2 bag heights (5200 / short 4200) cover 15–23 in torsos. SG and Exo need separate frames,
  belts and bags for that.
- **Meat**: the saddle comes off, the core bag pulls back, V-sling. Frame-only mode keeps the saddle as a lid.
- **Target**: 5.5 lb kit. **Risk**: most sewing ops. Zip-on panels add weight → use 4 Hypalon tabs + 1 zip.

**Recommendation:** start from **A** for the base pack (it fixes all three owner objections at the lowest weight and
the fewest build steps). Fold in B's clamshell meat cradle as the meat-mode spec. Keep C's swappable accent panel
as the later colourway strategy.

### Actions for the pack-designer
1. Replace the 340 × 788 × 320 box with a tapered roll-top (≤ 270 mm deep, ~860 mm body + 200 mm roll), still 85 L.
2. Cut suspension mass: 532 g shelf/wings → ≤ 200 g sling + lip; mid bar → frame sheet. Re-run R-14 at ≤ 2.45 kg.
3. Remove the lifters-to-post-bar feature (US 10,952,523 risk). Posts become lash points only.
4. Add keyed buckles, a slider lid / hip-pack, a stowed fly, and a firm 2-stage lumbar.

---

## Sources

Rendered list (the reference-link keys used in the text):

- `sg-sky`: <https://www.stoneglacier.com/products/sky-5900-xcurve-krux>
- `sg-frames`: <https://www.stoneglacier.com/blogs/the-vestibule/stone-glacier-frames-bags>
- `sg-oneframe`: <https://www.stoneglacier.com/blogs/the-vestibule/one-frame-for-every-hunt>
- `sg-term`: <https://www.stoneglacier.com/products/terminus-7000>
- `sg-xcurve`: <https://www.stoneglacier.com/products/xcurve-frame-foliage-tan>
- `gohunt-sky`: <https://shop.gohunt.com/products/stone-glacier-sky-5900-backpack>
- `gohunt-evo`: <https://shop.gohunt.com/products/krux-evo-frame>
- `rs-evo`: <https://rokslide.com/forums/threads/new-krux-evo-pack-frame-from-stone-glacier.85592/>
- `gj-sky`: <https://gearjunkie.com/outdoor/hunt-fish/stone-glacier-sky-5900-hunting-backpack-review>
- `rs-sky`: <https://rokslide.com/forums/threads/stone-glacier-sky-5900-and-sky-guide-7900-live-review.223003/page-3>
- `gj-best`: <https://gearjunkie.com/outdoor/hunt-fish/best-hunting-backpack>
- `exo-5000`: <https://exomtngear.com/4800>
- `exo-5000-img`: <https://exomtngear.com/products/k4-5000-pack-system>
- `exo-frame`: <https://exomtngear.com/frame>
- `exo-frame-img`: <https://exomtngear.com/collections/k4-pack-systems/products/k4-frame-system>
- `exo-narrow`: <https://exomtngear.com/blogs/article/why-is-the-k4-frame-narrow>
- `exo-heights`: <https://exomtngear.com/blogs/article/why-do-we-offer-the-k4-frame-in-4-heights>
- `exo-belts`: <https://exomtngear.com/blogs/article/why-do-we-make-the-k4-hipbelt-in-5-sizes>
- `carry-exo`: <https://www.carryology.com/reviews-2/exo-mtn-gear-k4-review/>
- `wh-exo`: <https://westernhunter.net/gear-reviews/exo-mtn-gear-k4-7200-pack-system/>
- `ps-exo`: <https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system>
- `rs-k4`: <https://rokslide.com/forums/threads/exo-mountain-k4.279017/page-5>
- `rs-exo-sg`: <https://rokslide.com/forums/threads/stone-glacier-vs-exo.457849/>
- `ht-sucks`: <https://www.hunttalk.com/threads/why-my-pack-sucks-kifaru-stone-glacier-exo-seek-mystery-ranch-kuiu-etc.290968/page-12>
- `kuiu-wp`: <https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper>
- `kuiu-4500`: <https://www.kuiu.com/products/icon-6-4500-divide-pack-ash>
- `kuiu-6000`: <https://www.kuiu.com/products/icon-6-6000-pack-vias>
- `bh-icon`: <https://www.bowhunter.com/editorial/field-test-kuiu-icon-6-6000/558323>
- `gv-icon`: <https://www.grandviewoutdoors.com/product-profile/kuiu-icon-6-pack-system>
- `kuiu-pro`: <https://kuiu.com/products/pro-suspension-phantom>
- `gj-pro`: <https://gearjunkie.com/product/kuiu-pro-pack-system>
- `hf-pro`: <https://new.huntinfool.com/blog/kuiu-pro-pack>
- `kuiu-legacy`: <https://rokslide.com/forums/threads/review-new-kuiu-pro-pack-with-ultra-4000-bag.142413/>
- `mr-bt85`: <https://www.mysteryranch.com/beartooth-85-mens-pack>
- `mr-met`: <https://www.mysteryranch.com/metcalf-100-womens-pack>
- `mr-arch`: <https://www.mysteryranch.com/load-carriage-architecture-of-a-mystery-ranch-pack>
- `gohunt-met`: <https://gohunt.com/browse/gear-lists-and-reviews/new-2024-mystery-ranch-metcalf-hunting-backpacks-just-released>
- `rs-myst`: <https://rokslide.com/forums/threads/mystery-ranch-mysterium-series.390101/>
- `seek-6300`: <https://checkout.seekoutside.com/unaweep-6300/>
- `seek-rev`: <https://checkout.seekoutside.com/revolution-suspension-and-frame/>
- `gj-ark`: <https://gearjunkie.com/outdoor/hunt-fish/first-look-kifaru-ark-frame>
- `rs-ark`: <https://rokslide.com/forums/threads/kifaru-ark-frame-review.346570/latest>
- `gf-ia`: <https://www.gearfool.com/collections/all/products/initial-ascent-ia5k-pack-system>
- `ia-phys`: <https://initialascent.com/blogs/hunting-gear/its-just-physics>
- `bh-ia`: <https://bornhunting.com/tested-initial-ascent-backpacks/>
- `sitka`: <https://checkout.sitkagear.com/mountain-hauler-4000-pack>
- `sitka-6200`: <https://ecotonelamisport.ca/en/products/sitka-mountain-hauler-6200-backpack>
- `eb-mod`: <https://kenetrek.com/products/eberlestock-mod-frame-pack>
- `eb-intro`: <https://eberlestock.com/blogs/blog-1/introducing-the-modframe>
- `eb-brute`: <https://www.herooutdoors.com/brute-6500>
- `gj-akek`: <https://gearjunkie.com/outdoor/hunt-fish/akek-alpha-3200-hunting-pack-review>
- `rs-akek`: <https://rokslide.com/forums/threads/lets-debate-akek-is-the-better-hunting-pack-system.442862/page-3>
- `carry-hpg`: <https://www.carryology.com/reviews-2/hill-people-gear-ute-light-review>
- `ssd-hpg`: <https://soldiersystems.net/2019/02/13/hill-people-gear-decker-pack-frame/>
- `rs-barneys`: <https://rokslide.com/forums/threads/anything-compare-to-a-barneys.255429/post-2509637>
- `rs-barneys2`: <https://rokslide.com/forums/threads/barneys-sports-chalet-frontier-gear-of-alaska-yukon-ul-ultra-bag-freighter-frame-combo.455276/>
- `rs-paradox`: <https://rokslide.com/forums/threads/paradox-packs.11570/page-3>
- `bpl-paradox`: <https://backpackinglight.com/paradox-evolution-review-chenault>
- `onx-argali`: <https://www.onxmaps.com/hunt/elite/pro-deals/argali-outdoors>
- `scheels-argali`: <https://www.scheels.com/p/19077-HICNTRY-UL>
- `rs-women`: <https://rokslide.com/forums/threads/good-hunting-pack-options-for-small-framed-woman.152068/>
- `bpl-women`: <https://backpackinglight.com/forums/topic/80293/>
- `pat-523`: <https://patents.google.com/patent/US10952523B2/en>
- `pat-171`: <https://patents.google.com/patent/US8579171>
- `pat-866`: <https://patents.google.com/patent/US8561866>
- `pat-519`: <https://www.freepatentsonline.com/y2014/0263519.html>
- `pat-re093`: <https://patents.google.com/patent/USRE48093>
- `pat-203`: <https://patents.google.com/patent/US9095203>
- `pat-210`: <https://patents.google.com/patent/US20180125210A1/en>
- `pat-115`: <https://uspto.report/patent/app/20150157115>
- `pat-search`: <https://patents.google.com/patent/US4286739>

[sg-sky]: https://www.stoneglacier.com/products/sky-5900-xcurve-krux
[sg-frames]: https://www.stoneglacier.com/blogs/the-vestibule/stone-glacier-frames-bags
[sg-oneframe]: https://www.stoneglacier.com/blogs/the-vestibule/one-frame-for-every-hunt
[sg-term]: https://www.stoneglacier.com/products/terminus-7000
[sg-xcurve]: https://www.stoneglacier.com/products/xcurve-frame-foliage-tan
[gohunt-sky]: https://shop.gohunt.com/products/stone-glacier-sky-5900-backpack
[gohunt-evo]: https://shop.gohunt.com/products/krux-evo-frame
[rs-evo]: https://rokslide.com/forums/threads/new-krux-evo-pack-frame-from-stone-glacier.85592/
[gj-sky]: https://gearjunkie.com/outdoor/hunt-fish/stone-glacier-sky-5900-hunting-backpack-review
[rs-sky]: https://rokslide.com/forums/threads/stone-glacier-sky-5900-and-sky-guide-7900-live-review.223003/page-3
[gj-best]: https://gearjunkie.com/outdoor/hunt-fish/best-hunting-backpack
[exo-5000]: https://exomtngear.com/4800
[exo-5000-img]: https://exomtngear.com/products/k4-5000-pack-system
[exo-frame]: https://exomtngear.com/frame
[exo-frame-img]: https://exomtngear.com/collections/k4-pack-systems/products/k4-frame-system
[exo-narrow]: https://exomtngear.com/blogs/article/why-is-the-k4-frame-narrow
[exo-heights]: https://exomtngear.com/blogs/article/why-do-we-offer-the-k4-frame-in-4-heights
[exo-belts]: https://exomtngear.com/blogs/article/why-do-we-make-the-k4-hipbelt-in-5-sizes
[carry-exo]: https://www.carryology.com/reviews-2/exo-mtn-gear-k4-review/
[wh-exo]: https://westernhunter.net/gear-reviews/exo-mtn-gear-k4-7200-pack-system/
[ps-exo]: https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system
[rs-k4]: https://rokslide.com/forums/threads/exo-mountain-k4.279017/page-5
[rs-exo-sg]: https://rokslide.com/forums/threads/stone-glacier-vs-exo.457849/
[ht-sucks]: https://www.hunttalk.com/threads/why-my-pack-sucks-kifaru-stone-glacier-exo-seek-mystery-ranch-kuiu-etc.290968/page-12
[kuiu-wp]: https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper
[kuiu-4500]: https://www.kuiu.com/products/icon-6-4500-divide-pack-ash
[kuiu-6000]: https://www.kuiu.com/products/icon-6-6000-pack-vias
[bh-icon]: https://www.bowhunter.com/editorial/field-test-kuiu-icon-6-6000/558323
[gv-icon]: https://www.grandviewoutdoors.com/product-profile/kuiu-icon-6-pack-system
[kuiu-pro]: https://kuiu.com/products/pro-suspension-phantom
[gj-pro]: https://gearjunkie.com/product/kuiu-pro-pack-system
[hf-pro]: https://new.huntinfool.com/blog/kuiu-pro-pack
[kuiu-legacy]: https://rokslide.com/forums/threads/review-new-kuiu-pro-pack-with-ultra-4000-bag.142413/
[mr-bt85]: https://www.mysteryranch.com/beartooth-85-mens-pack
[mr-met]: https://www.mysteryranch.com/metcalf-100-womens-pack
[mr-arch]: https://www.mysteryranch.com/load-carriage-architecture-of-a-mystery-ranch-pack
[gohunt-met]: https://gohunt.com/browse/gear-lists-and-reviews/new-2024-mystery-ranch-metcalf-hunting-backpacks-just-released
[rs-myst]: https://rokslide.com/forums/threads/mystery-ranch-mysterium-series.390101/
[seek-6300]: https://checkout.seekoutside.com/unaweep-6300/
[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[gj-ark]: https://gearjunkie.com/outdoor/hunt-fish/first-look-kifaru-ark-frame
[rs-ark]: https://rokslide.com/forums/threads/kifaru-ark-frame-review.346570/latest
[gf-ia]: https://www.gearfool.com/collections/all/products/initial-ascent-ia5k-pack-system
[ia-phys]: https://initialascent.com/blogs/hunting-gear/its-just-physics
[bh-ia]: https://bornhunting.com/tested-initial-ascent-backpacks/
[sitka]: https://checkout.sitkagear.com/mountain-hauler-4000-pack
[sitka-6200]: https://ecotonelamisport.ca/en/products/sitka-mountain-hauler-6200-backpack
[eb-mod]: https://kenetrek.com/products/eberlestock-mod-frame-pack
[eb-intro]: https://eberlestock.com/blogs/blog-1/introducing-the-modframe
[eb-brute]: https://www.herooutdoors.com/brute-6500
[gj-akek]: https://gearjunkie.com/outdoor/hunt-fish/akek-alpha-3200-hunting-pack-review
[rs-akek]: https://rokslide.com/forums/threads/lets-debate-akek-is-the-better-hunting-pack-system.442862/page-3
[carry-hpg]: https://www.carryology.com/reviews-2/hill-people-gear-ute-light-review
[ssd-hpg]: https://soldiersystems.net/2019/02/13/hill-people-gear-decker-pack-frame/
[rs-barneys]: https://rokslide.com/forums/threads/anything-compare-to-a-barneys.255429/post-2509637
[rs-barneys2]: https://rokslide.com/forums/threads/barneys-sports-chalet-frontier-gear-of-alaska-yukon-ul-ultra-bag-freighter-frame-combo.455276/
[rs-paradox]: https://rokslide.com/forums/threads/paradox-packs.11570/page-3
[bpl-paradox]: https://backpackinglight.com/paradox-evolution-review-chenault
[onx-argali]: https://www.onxmaps.com/hunt/elite/pro-deals/argali-outdoors
[scheels-argali]: https://www.scheels.com/p/19077-HICNTRY-UL
[rs-women]: https://rokslide.com/forums/threads/good-hunting-pack-options-for-small-framed-woman.152068/
[bpl-women]: https://backpackinglight.com/forums/topic/80293/
[pat-523]: https://patents.google.com/patent/US10952523B2/en
[pat-171]: https://patents.google.com/patent/US8579171
[pat-866]: https://patents.google.com/patent/US8561866
[pat-519]: https://www.freepatentsonline.com/y2014/0263519.html
[pat-re093]: https://patents.google.com/patent/USRE48093
[pat-203]: https://patents.google.com/patent/US9095203
[pat-210]: https://patents.google.com/patent/US20180125210A1/en
[pat-115]: https://uspto.report/patent/app/20150157115
[pat-search]: https://patents.google.com/patent/US4286739
