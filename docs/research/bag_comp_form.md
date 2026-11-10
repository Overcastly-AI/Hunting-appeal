# Bag competition, Team E FORM: research (2026-11-10)

Owner: pack-designer (Team E). Purpose: the cited research step for the CHERT bag entry
(`designs/pack_5200/bag_comp/form/`). It builds on `docs/research/bag_body_architectures.md` and
`docs/research/hunting_loadouts.md` (their URLs are re-cited here where a claim depends on them). Benchmarks are about
performance and design language only; no brand look, pattern, logo or name is copied.

## 1. What the market's design language says (benchmarks, not templates)

1. **Premium mountain-hunting packs are judged on comfort, features, build quality and capability, and a spotting-scope
   pocket is a 2025 feature that reviewers notice.** Outdoor Life's 2025 test scores each pack on these four counts and
   calls out Stone Glacier's new side-zip accessory pocket and large spotting-scope pocket
   ([Outdoor Life, best hunting backpacks 2025](https://www.outdoorlife.com/gear/best-hunting-backpacks-2025.md);
   [Outdoor Life 2026](https://www.outdoorlife.com/gear/best-hunting-backpacks-2026/)).
   Implication for CHERT: styling must not cost any of the CORRIE features (scope sleeve, tripod wing, pouch, belt
   pockets). It keeps all of them.
2. **Panel access on a hunting pack comes as a straight zip, a horseshoe or a U-zip under a roll-top.** A straight zip
   is lighter and simpler. A horseshoe "can be laid back" so you can see into the bag
   ([Exo, K4 main bag access](https://exomtngear.com/blogs/article/k4-main-bag-access)). The 2025 roundups show both types
   on current packs ([Field & Stream, best hunting backpacks](https://www.fieldandstream.com/outdoor-gear/best-hunting-backpacks/)).
   CHERT keeps CORRIE's horseshoe principle. The legs of the U run up the chamfer creases.
3. **Users are wary of zips on hard-use packs.** Forum reports describe main zips failing on full packs, usually from
   over-stuffing, and "a point of failure" is a common view of panel loaders
   ([ROKSLIDE, wary about zippers](https://rokslide.com/forums/threads/is-anybody-else-wary-about-zippers-on-hard-use-packs.138401/);
   [Backpacking Light, panel loaders](https://backpackinglight.com/forums/topic/what-are-peoples-thoughts-on-panel-loader-backpacks/)).
   A repaired zip that works flat "pops open under tension", so zips must be tested loaded
   ([Purism repair note](https://buildstatus.puri.sm/fix-broken-zipper-backpack)).
   CHERT response: the zip sits in a seam with a crease on each side (the chamfer), so the hoop load in the aft face
   runs into the blade facet, not straight across the zip. The roll-top still closes the bag if the zip fails (as CORRIE).
   This is an argument, not a test. The loaded zip test stays on the prototype list.
4. **Cottage and premium makers build the body from simple panels; beginner roll-top patterns are almost all
   rectangles** ([trueelena roll-top backpack pattern](https://sewing-patterns.trueelena.org/accessories/bags/roll_top_backpack/index.html);
   [SectionHiker, Unaweep 4800](https://sectionhiker.com/paradox-packs-unaweep-4800-backpack-for-winter-use/)).
   So CHERT's shape has to come from straight-seamed facets (a chamfer is one more straight seam per side), not from
   curved gores.
5. **Low-end camo packs sell "all-over camo" as their look** (for example the TIDEWE listing, in Next Camo G2)
   ([desertcart TIDEWE listing](https://www.desertcart.nl/products/459799764-tidewe-hunting-backpack-waterproof-camo-hunting-pack-with-rain-cover)).
   The owner's brief is the opposite: mostly solid, with camo as edgy accents. That is a way to set the product apart.

## 2. Why camo on the corners (function, not only style)

6. **Disruptive patches on a target's outline delay detection in human field tests.** Patches crossing a human
   outline (the head) increased detection time significantly, and they worked best on a target that already
   matches the background ([Selj et al., SPIE 2015](https://astronomicaltelescopes.spiedigitallibrary.org/conference-proceedings-of-spie/9653/96530S/Disruptive-camouflage-tricks-the-human-eye--a-study-of/10.1117/12.2194157.full);
   [FFI summary](https://www.ffi.no/publikasjoner/arkiv/disruptive-camouflage-tricks-the-human-eye-a-study-of-detection-times-of-two-near-similar-targets-in-natural-backgrounds)).
   A follow-up found minor disruptive patches on the head or shoulder outline harder to detect overall
   ([FFI, minor disruptive patches](https://publications.ffi.no/en/item/disruptive-coloration-in-woodland-camouflage-evaluation-of-camouflage-effectiveness-due-to-minor-disruptive-patches)).
7. **Edge-intersecting patches improve survival in animals by impairing recognition**
   ([PMC3871342, edge patches](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871342); background:
   [Disruptive coloration](https://wikipedia.com/wiki/Disruptive_pattern)). The evidence base on human-carried gear is
   small ([same SPIE paper](https://astronomicaltelescopes.spiedigitallibrary.org/conference-proceedings-of-spie/9653/96530S/Disruptive-camouflage-tricks-the-human-eye--a-study-of/10.1117/12.2194157.full)).
   **Design consequence (CHERT's key styling decision):** put the camo where the pack's outline is, on the two aft
   vertical corners (the silhouette edge seen from behind and from the side) and the lower-rear corner (the fang).
   Keep the big flat faces solid. The solid-plus-edge layout is the owner's look, and the one place camo does the most
   optical work. The claim is qualitative; no detection test was run.

## 3. Pain points the shape addresses

8. **Boxy look:** CORRIE's own review lists "boxy look" as a weak spot to fix (`designs/pack_5200/bag_comp/RULES.md`,
   team A brief). A chamfered corner is the cheapest way to break a box silhouette with straight seams. The box
   bulges in the cloth sim anyway (`designs/pack_5200/analysis/corrie_body.md` 11.4), so the chamfer mostly adds a
   second highlight line on each corner.
9. **Load close to the back:** the hunting-pack advice is to pack heavy items close to the frame
   ([KUIU, pack organization](https://kuiu.com/blogs/hunting-tips/proper-hunting-pack-organization);
   [Exo, minimal internal organization](https://exomtngear.com/blogs/article/why-do-k4-bags-have-minimal-internal-organization)).
   Cutting the two aft corners removes volume at the largest lever arm, which moves the CG forward (computed in
   `form.py`: uniform-fill CG y 133.4 vs CORRIE 134.7 mm at equal design-rule volume).

## 4. Name and IP check

10. "Knap" (the first name) was dropped because a "Knap Sacks, LLC" trademark covers backpacks
    ([Justia trademarks](https://trademarks.justia.com/owners/knapp-sacks-llc-2144388)) and a "Rift Knap Sack" product exists
    ([ATACZ](https://atacz.com/products/knapsack)). **CHERT** returned no pack brand in a search of hunting-pack makers
    ([search sample: Outdoor Life 2026 list](https://www.outdoorlife.com/gear/best-hunting-backpacks-2026/),
    [Field & Stream brands](https://www.fieldandstream.com/gear/best-backpack-brands/)). That is not a legal clearance.
11. Patents: the door, roll-top, wings and pouch are CORRIE's, which already went through the guardrails in
    docs/DECISIONS.md. A chamfered pack corner and a zip in a seam are generic construction. No patent was found
    claiming a zip in a corner seam bounded by a chamfer facet, but this was a short search, not a freedom-to-operate
    study ([Google Patents, example of a pack patent in the earlier search set](https://patents.google.com/patent/US8960513)).
    Flag for design-reviewer.
