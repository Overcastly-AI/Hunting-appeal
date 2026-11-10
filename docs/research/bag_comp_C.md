# Bag competition, team C (OPEN): full-access hauler research

Date 2026-11-10. Team C brief (RULES.md): a clamshell or panel-loader whose whole aft face opens, keeping the roll-top
and the fixed frame interface, and answering the zip-blowout risk under hoop load. Reuses
`docs/research/bag_body_architectures.md` ([BA §n]) and `docs/research/hunting_loadouts.md`. Every claim carries a URL;
"(search summary)" means the claim comes from the search engine's summary of that page, not from a full read of it
(several forum pages return HTTP 403 to our fetcher).

## 1. Who opens the whole face, and how

| Maker / model | Access | Source |
|---|---|---|
| Exo K4 3600 / 7200 | roll-top + one straight full-length front zip | [Exo, K4 main bag access](https://exomtngear.com/blogs/article/k4-main-bag-access) |
| Exo K4 5000 | roll-top + horseshoe panel that "can be laid back" | [Exo](https://exomtngear.com/blogs/article/k4-main-bag-access) |
| Stone Glacier Sky 5900 | large front U / panel zip, reach "items on the bottom, without unloading" | [goHUNT Sky 5900](https://shop.gohunt.com/products/stone-glacier-sky-5900-backpack) |
| KUIU Pro LT / Pro Divide | "full horseshoe zipper" main opening | [ActiveJunky, PRO LT 4000](https://www.activejunky.com/product/kuiu-pro-lt-4000-pack), [KUIU PRO Divide 4500](https://www.kuiu.com/products/pro-divide-4500-pack-ash) |
| Mystery Ranch 3-ZIP (Metcalf, Overload, Pintler, Selway, Terraframe) | "3-ZIP design for easy, rapid access"; the 3-ZIP packs also carry bottom, front and side compression straps | [Mystery Ranch, Overload](https://www.mysteryranch.com/overload-pack), [Black Ovis, Pintler](https://www.blackovis.com/mystery-ranch-pintler-pack-bag-only) (search summary), [Backcountry, Terraframe 3-Zip 50](https://www.backcountry.com/mystery-ranch-terraframe-3-zip-50l-backpack) (search summary) |
| Mystery Ranch Marshall | dual full-length side zips + top shroud | [Bass Pro, Marshall](https://www.basspro.com/shop/en/mystery-ranch-marshall-backpack) |
| Cabela's Multi-Day hunting pack | "top-loading and large clamshell openings", meat shelf with bottom support | [armsagora listing](https://armsagora.com/cabelas-multi-day-hunting-backpack-900009894313) (search summary) |
| goHUNT bowhunting pack guide | names a pack with a "full clamshell zip" and one with a "270° zipper" plus a load shelf | [goHUNT, how to pick a bowhunting pack](https://www.gohunt.com/browse/gear-lists-and-reviews/how-to-pick-the-right-backpack-for-bowhunting) (search summary) |
| Kifaru panel loaders (357 Mag review) | front panel unzips for loading; "the outer compression strap ... keeps the front panel from fully unzipping when heavy items are placed in the top mesh pocket" | [ROKSLIDE review](https://rokslide.com/?p=22957) (search summary) |

Read-across for TAILGATE:
1. **Nobody we found opens the full aft face of a framed meat hauler down to the floor.** The leaders stop at a
   horseshoe or U inside a surround (Exo 5000, KUIU Pro, Sky 5900) or use side zips (Mystery Ranch). A full
   clamshell is a luggage / duffel idea that appears on cheaper hunting packs (Cabela's, goHUNT's "full clamshell")
   ([armsagora](https://armsagora.com/cabelas-multi-day-hunting-backpack-900009894313),
   [goHUNT](https://www.gohunt.com/browse/gear-lists-and-reviews/how-to-pick-the-right-backpack-for-bowhunting)).
2. **Compression straps that cross a panel zip are the leaders' habit** (Mystery Ranch 3-ZIP packs list front and side
   compression next to the 3-ZIP; Kifaru's compression strap keeps the panel from unzipping)
   ([Black Ovis, Pintler](https://www.blackovis.com/mystery-ranch-pintler-pack-bag-only),
   [ROKSLIDE 357 Mag](https://rokslide.com/?p=22957)). We found **no maker statement that the straps are there to
   unload the zip**: that function is our engineering claim, checked in the cloth sim (analysis/bag_comp_C.md).
3. **Strap clutter is a known complaint.** A Kings Camo review says most framed hunting packs "end up as a chaotic wad
   of straps and buckles" ([GearJunkie, Kings XKG Summit 5200](https://gearjunkie.com/hunting/kings-camo-xkg-summit-5200-backpack-review),
   search summary); lashing over a horseshoe blocks it ([byland.co, KUIU Ultra 3000](https://byland.co/blog/kuiu-ultra-3000-review),
   [BA §2.2]); a Metcalf side zip sits under side buckles
   ([Sportsman's Warehouse, Metcalf](https://SportsmansWarehouse.com/hunting-gear-supplies/hunting-packs/hunting-expedition-packs/mystery-ranch-metcalf-hunting-backpack-coyote/p/p237115), [BA §2.3]).
   TAILGATE answer: 3 lid straps only, all with the G-hook on one side, so one sweep of the right hand opens the lid.

## 2. Zip blowout: what fails and why

| Finding | Source |
|---|---|
| Main zips blow out on a full pack; one hunter finished the hunt "with just the two slider bodies holding the lid closed" | [ROKSLIDE, wary about zippers](https://rokslide.com/forums/threads/is-anybody-else-wary-about-zippers-on-hard-use-packs.138401/), [BA §1.6] |
| Most posters blame over-stuffing | same thread, [Eastmans, Blacks Creek](https://forum.eastmans.com/threads/blacks-creek.796), [HuntTalk](https://www.hunttalk.com/threads/why-my-pack-sucks-kifaru-stone-glacier-exo-seek-mystery-ranch-kuiu-etc.290968/post-2852334) |
| A Kifaru Spike Camp zipper blew out on an elk hunt | [ROKSLIDE (search summary)](https://rokslide.com/forums/threads/is-anybody-else-wary-about-zippers-on-hard-use-packs.138401/) |
| Badlands panel connectors failed on a bear pack-out at ~75 lb; zip pulls broke and were replaced by paracord | [ROKSLIDE, Badlands zippers](https://rokslide.com/forums/threads/badlands-zippers-still-garbage.189312/post-1832621) (search summary) |
| A split zip "closes as you pull the slider but separates just behind it": a worn / spread slider; fix by squeezing the slider plates with pliers, or replace the slider | [iFixit, repairing a zipper slider](https://www.ifixit.com/Guide/Repairing+Zipper+Slider/35496), [Treeline Review, how to fix zippers](https://www.treelinereview.com/learn-skills/how-to-fix-zippers), [Hyperlite support, DIY zipper repairs](https://support.hyperlitemountaingear.com/en-US/diy-zipper-repairs-880378) |
| REI staff: "Missing zipper teeth or crushed zipper sliders are generally unfixable problems for that specific zipper" | [AOL / Popular Mechanics](https://www.aol.com/lifestyle/broken-zipper-don-t-toss-185800769.html) (search summary) |
| A busted zipper "is also very difficult to repair"; a single side zip on a full bag "might become just a narrow slit" | [BPL forum](https://backpackinglight.com/forums/topic/thoughts-on-packs-with-a-single-side-zip-versus-bottom-zip/), [BA §2.3] |
| "U-zip at the bottom": good bottom access, "not so great access to things in the middle" | [BPL forum](https://backpackinglight.com/forums/topic/thoughts-on-packs-with-a-single-side-zip-versus-bottom-zip/) |

Mechanism (our reading of the sources above): the chain itself is strong in a straight pull, and failures come from
(a) closing the slider on a chain that is already in tension (over-stuffing: the slider is the clamp that pulls the
two edges together, and its jaws spread), then (b) a spread slider no longer locks the teeth and the chain opens behind
it under load ([iFixit](https://www.ifixit.com/Guide/Repairing+Zipper+Slider/35496)). **Design rule taken: the zip
must never be the part that pulls a full bag closed, and must not carry the bag's hoop tension when closed.**

## 3. Zip size

| Data | Source |
|---|---|
| #10 coil chain: distributor lists 272 lb (~1210 N) chain crosswise and 185 lb (~820 N) folded crosswise breaking strength | [Albrights Supply, #10 coil chain](https://www.albrightssupply.com/coil-zipper-chain-10-black-czi10b) (search summary; not stated as YKK data) |
| Coats Opti RT polyester coil (luggage / outdoor): lateral strength > 979 N (size not stated) | [Coats Opti RT datasheet](https://www.coats.com/-/media/Coats/Files/Opti-RT/Opti_RT.pdf?rev=-1) (search summary) |
| YKK luggage zips: crosswise strength is also tested after abrasion with 400-grit paper | [YKK Americas, RC luggage zippers](https://ykkamericas.com/wp-content/uploads/2021/10/rc-luggage-compressed.pdf) (search summary) |
| Our record `coil_zipper_10`: 900 N crosswise (ESTIMATE, ASTM D2061), 9 mm chain, 20 g/m | `data/materials/hardware/coil_zipper_10.yaml` |
| #10 matches the leaders' main zips; O-13 rejected #8 on the main bag | `analysis/corrie_body.md` D4 |

DECISION: **#10 coil** (not #8, not molded). It is the record we have, the conservative record value (900 N) is below
both cited figures, and #10 sliders are the size a gloved hand can work. A #10 Vislon would add mass and noise
(record note: coil is quieter than molded teeth).

## 4. Garages and protection

| Practice | Source |
|---|---|
| CORRIE parks both door sliders under fabric garages so they cannot walk open under load and stay reachable with gloves | `analysis/corrie_body.md` D4 (our design, built on [BA §1.6]) |
| Exo sews a stash pocket into the back of the horseshoe panel (the opening panel carries a pocket) | [Exo](https://exomtngear.com/blogs/article/k4-main-bag-access) |
| Zip pulls break; paracord pulls replace them | [ROKSLIDE, Badlands](https://rokslide.com/forums/threads/badlands-zippers-still-garbage.189312/post-1832621) (search summary) |

TAILGATE takes: one slider garage at the closed park point, boots over the two zip feet, storm flaps along the legs
(they also frame the lid in the owner's camo), cord pulls (no metal tabs), and IMP-4 on the inside of the lid (Exo's
panel-pocket idea, our existing part).

## 5. Patents and IP

- Our guardrails stand (docs/DECISIONS.md 2026-11-01; corrie_body.md D8): no fabric panel between frame and bag,
  under-straps pin to pin, lifters on the crown, nothing between the spreader and the z 330 bar. TAILGATE changes only
  the aft face, which none of them touch.
- A zipped clamshell lid and compression straps over a zip are old, generic luggage and pack construction (the 3-ZIP,
  horseshoe and clamshell packs above). We did not search the patent databases for this team entry: **flag for the
  patent attorney review** already planned before tooling (DECISIONS 2026-11-01).
- Original IP: the TAILGATE name, the lid layout and the camo flap framing are ours; no maker's look is copied.
