# Bag competition, team D (MODULE): research (2026-11-10)

Scope: modular bag systems (a shell or harness on a frame carrying removable dry bags, pods or compartments), what
users like and dislike about them, what modules weigh, and how meat is kept close to the frame in a bag. Reuses
`docs/research/bag_body_architectures.md` [BA] and `docs/research/meat_carry_mechanisms.md` [MC] where marked; every
new claim carries its URL. Benchmarks only: no brand's look, name or pattern is copied.

## 1. What modular hunting systems exist

| System | What is modular | Source |
|---|---|---|
| Eberlestock modular hunting pack system | frame plus interchangeable bags and add-on pouches; reviewed as a "modular hunting pack system" | [Sportsman's News video review](https://news.sportsmans.com/product-review/video-product-review-eberlestock-modular-hunting-pack-system), [HuntinFool, ModFrame with Brooks bag](https://www.huntinfool.com/articles/topic/gear/eberlestock-modframe-with-brooks-bag) |
| Exo Mountain Gear K-series | removable pack bags in four sizes, interchangeable on one frame; quick-release to reach the load shelf | [Western Hunter, K4 7200 system](https://westernhunter.net/gear-reviews/exo-mtn-gear-k4-7200-pack-system/), [GearJunkie, K3 4800](https://gearjunkie.com/packs/exo-mountain-gear-k3-4800-review-efficient-hunting-pack) |
| Badlands Vario | frame plus accessories; heavy-duty meat shelf; pack can mount outside the shelf | [American Hunter, first look](https://www.americanhunter.org/content/first-look-badlands-vario-modular-hunting-pack-system) |
| KUIU PRO | bag used only with its frame and suspension; "modular design keeps gear from rolling around" (reviewer) | [American Hunter, PRO LT field test](https://www.americanhunter.org/content/field-tested-kuiu-pro-lt-pack-system), [Outdoor Empire, KUIU PRO bag review](https://outdoorempire.com/?p=23345) |
| Tatonka Modulus | integrated fold-out meat shelf; heavy loads close to the back | [Hunting & Fishing NZ, Modulus testfired](https://www.huntingandfishing.co.nz/blog/post/tatonka-modulus-pack-testfired) |
| Stone Glacier Terminus | internal collapsible **load cell** (36 L) for boned meat, next to the back, inside the bag | [Stone Glacier, load cell vs load shelf](https://www.stoneglacier.com/blogs/the-vestibule/load-cell-vs-load-shelf) [BA §6, MC §1.1] |
| Kifaru (Reckoning, Ma Deuce) | add-on pouches, bellowed side pockets on one frame | [ROKSLIDE Reckoning review](https://www.rokslide.com/kifaru-reckoning-review/) [BA §6] |
| Seek Outside | removable straps on gatekeeper buckles; strip the pack down | [GearJunkie Goshawk 4800](https://gearjunkie.com/hunting/seek-outside-goshawk-4800-hunting-pack-review) [BA §6] |
| Earlier in this repo: CRADLE | open harness + four round roll-top dry bags; +161 g, CG 168 mm aft, 45.5 in tall, open sides snag brush | `designs/pack_5200/analysis/bag_alternatives.md` U.2–U.3 |

## 2. User pain points that a modular bag must not repeat

- **Accessory creep: heavy and costly once the add-ons are on.** GearJunkie on a modular hunting pack: "heavy", limited
  organisation, and expensive add-ons needed to get the full benefit of the system
  ([GearJunkie, best hunting backpacks](https://gearjunkie.com/outdoor/hunt-fish/best-hunting-backpack)). Kifaru users
  name "price and weight once accessories are added" ([ROKSLIDE, Ark vs Duplex](https://www.rokslide.com/kifaru-ark-frame-vs-kifaru-duplex-frame/)) [BA §6].
  -> CACHE books every module in `bag_system_g` and lists what each one weighs so the hunter can leave it home.
- **Loud zips.** Stone Glacier Sky review: "zippers are loud" ([GearJunkie, best hunting backpack](https://gearjunkie.com/packs/best-hunting-backpack)).
  -> modules close by roll + G-hook (no zip, no buckle); one #5 zip on the KILL module only.
- **Armpit-deep reach in top-loaders** (A2) and **zip blow-outs on full bags** (A1) [BA §3].
  -> the door (kept from CORRIE) is a drawer front for the modules; modules carry the hoop load of their own contents
  (ASSUMPTION, not tested), so the door zip sees less of it.
- **Round dry bags waste corners and push the load aft** (CRADLE, this repo: CG 168 mm, +16 mm vs SPINE).
  -> CACHE modules are flat-sided boxes cut to the shell's section; the frame-zone module is a 110 mm slab.
- **Load cell hard to scrub of blood** (Terminus users, [ROKSLIDE Terminus review](https://rokslide.com/forums/threads/stone-glacier-terminus-review.267237/page-8)) [BA §6].
  -> CACHE's meat liner is a removable module (wash it in a creek or a sink); the record for 40D silpoly notes blood
  rinses off its slick face and suggests it for "a removable, washable meat-shelf liner"
  (`data/materials/textiles/silicone_coated_poly_ripstop_40d.yaml`).
- **Meat close to the back** is what users praise in shelves and load cells
  ([Hunting & Fishing NZ, Modulus](https://www.huntingandfishing.co.nz/blog/post/tatonka-modulus-pack-testfired),
  [Stone Glacier](https://www.stoneglacier.com/blogs/the-vestibule/load-cell-vs-load-shelf)).
  -> the SWAP slab sits exactly where IM1-IM3 hold the meat.
- **Dry bag inside the main bag** is common reviewer advice for keeping gear dry
  ([GearJunkie, best hunting backpacks](https://gearjunkie.com/outdoor/hunt-fish/best-hunting-backpack)).
  -> modules are that dry bag; the shell can drop the roll-top (fly + lid + modules keep the gear dry).

## 3. What modules weigh (benchmarks for the mass model)

| Item | Mass | Source |
|---|---|---|
| Sea to Summit Ultra-Sil dry sack, 20 L | 50 g (spec table), 57-58 g (retailers) | [Basecamp Gear spec](https://www.basecampgear.co.uk/equipment-c392/stuffsacks-drybags-c466/drybags-c1000/sea-to-summit-ultra-sil-drysacks-p1841), [Absolute Snow](https://www.absolute-snow.co.uk/sea-to-summit-ultra-sil-dry-bag-20l-waterproof-gear-sack) |
| Hyperlite pods (DCF): small 6.8 L / large 10 L | 1.2 / 1.3 oz (34 / 37 g) | [SectionHiker, HMG pods](https://sectionhiker.com/hyperlite-mountain-gear-packing-pods-review/) |
| Six Moon Designs pack pods (silnylon) | 1.0-1.1 oz each | [SectionHiker, SMD pods](https://sectionhiker.com/six-moon-designs-pack-pods-review/) |
| Reviewer view: pods replace stuff sacks "without a weight penalty" | | [SectionHiker, HMG pods](https://sectionhiker.com/hyperlite-mountain-gear-packing-pods-review/) |
| Reviewer view: zipped pods make access "much easier" than stuff sacks | | [PMags, SMD pack pods](https://pmags.com/gear-review-smd-pack-pods) |
| Caution: pods are not waterproof unless sealed; "easy to get carried away" with sacks | | [Garage Grown Gear, pros and cons of pods](https://www.garagegrowngear.com/en-au/blogs/gear-gab/pros-cons-ultralight-pack-pods) |

Reading: a hunter already carries 2-4 stuff sacks of ~35-60 g each. CACHE's three modules (computed 61.7 / 44.0 /
36.4 g) are in that class. That is an argument about *carried* weight. The competition counts the pack, so
`bag_system_g` includes them (section 5 of the analysis shows both views).

## 4. Design language (distilled, not copied)

- Lids: floating or detachable lids are common; optional lids exist on several bags [BA §6.2].
- Side carry: open side pockets / straps for tripod, bottle, stock (Stone Glacier Sky, Exo) [BA §6]; tripod carry
  on the side under straps is the norm.
- Cottage builds: rectangles, straight seams, straight tube collars [BA §4], which fits a beginner on one machine.
- Clamshell, shaped pods that "fit perfectly inside backpacks" are the pod makers' pitch
  ([Backpacking Light, HMG pod review](https://backpackinglight.com/hyperlight-mountain-gear-pod-review/)). CACHE's
  modules are cut to the shell's section for the same reason. Colour-coding is this team's DECISION (not researched):
  three muted solids (sage, stone, brown) and a blaze pull tab only on the KILL module, which is findable at a kill
  site and hidden inside the bag.

## 5. Patents and IP

- DECISIONS 2026-11-01: load lifters never move onto the extension posts (Mystery Ranch US 10,952,523 scope). CACHE
  does not touch the frame or lifters.
- A removable liner held against the frame side by the existing internal straps is not the Stone Glacier sewn load
  cell; no patent on a removable meat liner module was found in this research (not a search report: flag for the
  attorney review already planned before tooling).
- Names: "CACHE" and the module names (SWAP, CAMP, KILL, LID) are generic words; no brand pack line by those names
  was found in the sources above.

## 6. Gaps

- No measured data on hoop load sharing between an inner module and the outer shell (the door-zip claim in section 2
  is an ASSUMPTION).
- No published abrasion data for silpoly against boned meat and bone ends; the SWAP slab uses 70D nylon on its frame
  face and floor for that reason (ASSUMPTION, test listed in the analysis).
