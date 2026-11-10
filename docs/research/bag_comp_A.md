# Bag competition, Team A EVOLVE: research (2026-11-10)

Scope: what the leaders and their users say about the four CORRIE B.2 weak spots the brief names (snacks within
reach on small belts, trekking-pole stowage on heavy loads, the boxy look, the floor-corner seam), plus the
construction methods the fixes use. Benchmarks only: no maker's shape, name, pattern or trade dress is copied. This
reuses `docs/research/bag_body_architectures.md` [BA] and `docs/research/hunting_loadouts.md` [HL]. Every claim
below carries its URL. Where the source is a forum post or a retailer page, it is marked "(forum)" or "(retailer)".

## 1. Hourly items: snacks and the GPS within reach on every belt size

- [A1] Hipbelt pockets that are too small are a recurring complaint; HMG "completely redesigned their hip belt
  pockets ... to make them much bigger and easier to access" after customer feedback
  ([CleverHiker, HMG hip belt pockets](https://www.cleverhiker.com/backpacking/new-hmg-hip-belt-pockets-review/)).
- [A2] Even a pocket big enough for "a small rangefinder or a couple trail bars" can sit "a bit too far back on my
  hips even when mounted as far forward as possible" (Mystery Ranch, reviewer)
  ([Pack Hacker, Forager Hip Mini](https://packhacker.com/travel-gear/mystery-ranch/forager-hip-mini)). On a small
  belt the pocket length is what runs out first; CORRIE B.1/B.2 confirmed it (S/M/L interiors 57 / 97 / 132 mm
  against a 150 mm snack stack, `analysis/corrie_body.md` 11.3).
- [A3] Big belt pouches load the belt and get in the way of the stride; Rokslide's staff "have never been a fan of
  big pouches on the hipbelt" (forum) ([Rokslide, Kifaru pouch on K4 belt](https://rokslide.com/forums/threads/kifaru-pouch-on-exo-k4-belt.332989/)).
  So growing the belt pocket on S is the wrong lever.
- [A4] Exo sells a separate K4 hipbelt pouch that holds "about as much as a large sandwich bag"
  ([Packstack, K4 hipbelt pouch](https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-hipbelt-pouch);
  [Exo product](https://exomtngear.com/collections/k4/products/k4-hipbelt-pouch)): leaders treat snacks as a
  belt-adjacent, pack-on item.
- [A5] Hunters carry snacks on the move, hourly, together with water and the phone [HL table, `hunting_loadouts.md`
  section 5] ([Exo rifle list](https://exomtngear.com/blogs/article/rifle-hunting-gear-list) as cited there).

## 2. Pole stowage that does not depend on a free wing

- [A6] Hunters stow poles in side pockets and reach them pack-on: "I can reach my poles ... stored in the side pouch,
  without removing the pack" (forum, Stone Glacier owner)
  ([Rokslide, how do you carry trekking poles](https://rokslide.com/forums/threads/how-do-you-carry-trekking-poles.322500/));
  the thread also notes that with a bow or rifle in one hand one pole is often enough, and that side-pocket poles are
  harder to reach than strap-mounted ones (same thread,
  [post](https://rokslide.com/forums/threads/how-do-you-carry-trekking-poles.322500/post-3248337)).
- [A7] Exo's side pockets include a **forward-facing lower compartment** "nearly everyone can reach" with the pack on
  ([Exo, K4 stretch pockets](https://exomtngear.com/blogs/article/k4-stretch-pockets)) [BA table].
- [A8] Shock-cord grip loop + tip pocket is the common pole-stow pattern: Zpacks sells pole holsters as shock-cord
  loops at the strap and belt ([Zpacks pole holsters](https://zpacks.com/products/trekking-pole-holsters-both-sides-of-pack));
  Mystery Ranch's Pop Up 30 has "stretch-woven side pockets for water bottle or trekking poles" (retailer)
  ([North 40, Pop Up 30](https://north40.com/mystery-ranch-pop-up-30-backpack-2)); Eberlestock's Brute Scout has
  side bottle pockets with bungee retention that take poles (retailer)
  ([Scheels, Brute Scout](https://www.scheels.com/p/702982-BRUTESCOUT)).
- [A9] Collapsed folding carbon poles are 33-40 cm (retailer)
  ([EMS, BD Distance Carbon Z](https://www.ems.com/black-diamond-distance-carbon-z-trekking-poles/2047964.html)),
  so a pocket that holds the tips plus one loop at the top holds them (our `loadouts.yaml` trekking_poles 400 mm).

## 3. Silhouette: box versus tapered

- [A10] The leaders' hunting bags read as slim, tapered bags (Stone Glacier "slim tapered bag", Exo "slim roll-top")
  ([goHUNT Sky 5900](https://shop.gohunt.com/products/stone-glacier-sky-5900-backpack),
  [Exo stretch pockets](https://exomtngear.com/blogs/article/k4-stretch-pockets)) [BA section 4 table].
- [A11] No maker states why their bags taper [BA section 2.5]; a tapered box made of trapezoid panels keeps every seam
  straight [BA section 2.5]. Our taper is therefore an owner-look decision (the owner disliked the boxy look,
  DECISIONS log), not a performance claim.
- [A12] The owner's look rule is "mostly solid colours, camo as edgy accent panels" (`CLAUDE.md`, RULES.md): a camo base
  band (wear zone) is the accent the rule asks for, and it is where CORRIE already put camo (chevron kick plate)
  [`analysis/corrie_body.md` section 1].

## 4. Floor corner and base construction

- [A13] A bathtub floor exists to keep the floor seams off the wear surface; "bathtub designs always imply seams in the
  corners" (tent practice; we found no backpack-specific source, so this is an analogy)
  ([Mountains for Everybody, bathtub floor](https://mountainsforeverybody.com/what-is-a-bathtub-floor-on-a-tent);
  [CORE, tub floors](https://www.coreequipment.com/blogs/discover-more/stay-dry-with-core-are-tub-floors-always-better)).
- [A14] Pack-bottom stitching wears and users look for ways to protect it (forum)
  ([BackpackingLight, protect stitching on bottom of pack](https://backpackinglight.com/forums/topic/how-to-protect-stitching-on-bottom-of-pack)).
- [A15] Camo-printed 500D Cordura is a stock, by-the-yard fabric (retailer)
  ([Rocky Woods 500D camo](https://rockywoods.com/products/500-denier-mil-spec-cordura-nylon-fabric-multicam-standard-camo-pattern),
  [Sailrite Cordura 500D camo](https://www.sailrite.com/Cordura-500D-MultiCam-Original-60-Fabric)), so the owner's
  camo can be printed on the same 500D the floor already uses (a print vendor run; the record mass is kept,
  ASSUMPTION, materials-engineer to add a printed-500D record).
- [A16] CORRIE's own cloth sims put the worst seam force on the B-03 | B-05 gusset-to-floor seam at the frame-side
  corner on all 9 cases (1.14-1.99 N/mm) [`analysis/corrie_body.md` section 11.4].

## 5. Patents and IP (guardrails in docs/DECISIONS.md)

- Side bottle / pole holsters: US 5,114,059 (side bottle holsters) is expired by term, as already logged for IMP-3
  (`concepts/corrie_loadout.py` improvements, [Google Patents US5114059](https://patents.google.com/patent/US5114059A/en)).
- Stretch side pockets and shock-cord pole loops are generic, multi-maker features ([A7], [A8]).
- No change touches the frame interface, so guardrails H1-H4 stay as CORRIE's.

## 6. What we take from this

1. Move the snack / GPS home off the graded belt and onto the bag at hip height, forward-facing [A1-A4, A7].
2. Give the poles their own boot + loop so they never compete with the tripod or the rain jacket for a wing [A6-A9].
3. Round the aft corners and taper the shoulder into the roll; camo goes on the base wear band [A10-A12].
4. Use a tub wall so the floor-corner seam leaves the bulge corner; check it in the cloth sim [A13-A16].
