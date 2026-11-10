# Proposal: "base" and "as hunted" weight configurations (BL-008)

Owner: pack-designer. Date: 2026-11-10. **Status: proposal. It changes no design and no mass; it only moves items
between reporting configurations.** Research behind it: `docs/research/published_weight_definitions.md`.

## 0. Summary

| Configuration (CORRIE B.2 on frame H1, belt M) | g | lb | Leaders' nearest equivalent |
|---|---:|---:|---|
| **Base**: everything sewn or pinned on, plus the meat carry and compression the leaders also count | **3700.4** | **8.16** (8 lb 2.5 oz) | SG / Kifaru headline (no lid) |
| Base + top pouch | 3764.6 | 8.30 | Exo / Seek / IA headline (with lid) |
| **As hunted**: base + top pouch + bottle holster + rain fly | **3872.4** | **8.54** (8 lb 8.6 oz) | no leader publishes this |
| Meat trip: as hunted + float links B-24 | 3926.8 | 8.66 | = today's full booking (`frame_mass_h1.json` 3926.9 g) |

- Reclassifying moves **226.4 g (8.0 oz)** out of the headline: pouch 64.2, holster 38.8, fly 69.0 and float links
  54.4 g. **It saves nothing**: the hunter carries the same pack.
- **On the like-for-like basis our pack is 0.90 to 1.34 kg (2.0 to 2.9 lb) heavier than each leader's published
  system, or +32 % to +58 %** (§4; Seek Outside +2.08 kg). The 2994 g (6.6 lb) target is **706 g** away from base and
  878 g from as hunted.
- When we split the pack the way SG and Exo split theirs (meat carry on the frame side), the **bag side (≈1080 g) is
  level with the leaders' bags (1026–1077 g)**. The gap sits on the frame side: 2562 g against 1247–1332 g (§5). This
  corrects the review's §2 reading, which put the 842 g of straps and attachment on the bag side and compared it
  with leader bags that don't carry their meat straps.

## 1. Basis and traceability

- BL-001 (`huntkit/mass/ledger.py`) has **not** landed (the directory doesn't exist on 2026-11-10). Per the ticket,
  items come from the groups and parts in `analysis/weight_pass_corrie.json` (CORRIE B.1 booking). They're moved to
  B.2 with the B.2 rows of `corrie.weight_table("M")`, and the frame is the H1 figure from `analysis/frame_mass_h1.json`.
- Check: the item list below sums to **3926.8 g**, against `frame_mass_h1.json` `h1.corrie_b2_M_g` **3926.9 g**
  (rounding of 0.1 g).
- System names are BL-001's (`frame`, `back`, `belt`, `harness`, `bag_shell`, `bag_pockets`, `pouch`, `fly`,
  `straps_meat`, `straps_compression`, `attachment`, `misc`), so the ledger can carry this proposal as its
  `base: bool` flag plus a config tag. **When BL-001 lands, these numbers must be re-read from the ledger. They're
  not to be quoted from this file afterwards.**
- B.2 moves used (from `corrie.weight_table` B.2 minus B.1, belt M): grip print off (A-1, −4.9 g), haul-wrap tails
  (A-2, −5.4), SH-03 camo band out (B-2, −15.8), pouch 4.0 → 2.71 L (B-3/4/5, pouch 87.9 → 64.2 per
  `weight_pass_corrie.json` `packages.take` T-2), IMP-1 −8.5, IMP-2 −2.5, IMP-6 sewn to the strap −13.4, IMP-8
  −3.1, B-12 ports −7.2 (B-10), rain fly re-cut +6.5 (G-2). Frame 1062.6 → H1 1025.1 g.

## 2. The rule

An item is **base** if any of these holds:
- (a) it can't come off without a needle or a tool: sewn, pinned or bonded;
- (b) it's part of the load path or the frame/bag interface;
- (c) it's meat carry or bag compression that the leaders build into their frame or bag and count (SG's integrated
  load shelf, Exo's frame straps, Seek's compression straps).

An item is an **add-on** if it clips or hooks on and off by hand, and the leaders either sell it separately or leave
it out of their figure (lid at SG and Kifaru, bottle holder, rain cover, hipbelt pouch). **As hunted** = base + the
add-ons a typical multi-day rifle or bow hunt carries. Float links are carried only when the hunter plans to float
meat on the frame, so they sit in a separate meat-trip line.

## 3. Item by item (belt M, H1 frame)

| Id | Item | BL-001 system | g | Config | Why | Source |
|---|---|---|---:|---|---|---|
| FR | Frame H1 (printed body, crown, rack/pawl, pivot mount, joint hardware) | frame | 1025.1 | base | (b) | `frame_mass_h1.json` h1.frame_g |
| TA | Torso adjust (3:1 pulley, cam, release cord) | frame | 41.7 | base | (b) | `weight_pass_corrie.json` groups |
| BK | Back system: Sandwich v2 spreader 162.3 + back panel 251.3 | back | 413.6 | base | (b) | groups |
| HN | Harness: J-straps, yoke, lifters, sternum | harness | 212.5 | base | (b) | groups |
| BB | Hipbelt B body, load path, 2:1 pull, pad seat, wing-tip shards (B.2: no grip print) | belt | 499.8 | base | (b) | group − IMP-5L − IMP-3 − grip rows |
| IMP-5L | Hipbelt pocket, M (sewn into the wing binding) | belt | 15.2 | base | (a) | parts |
| IMP-3 | 1 L bottle holster (2 G-hooks on 2 wing tabs) | belt | 38.8 | **as hunted** | clips on; Exo and KUIU sell it separately | parts / `corrie.holster()` |
| BS | Bag body B.2: shell, collar, wings + 4 wing straps, door + #10 zip, roll-top + buckles, bow-riser loops, lash tabs | bag_shell | 532.2 | base | (a) | group − SH-03 (B-2) |
| IMP-1 | Scope sleeve (sewn inside the left wing) | bag_pockets | 54.5 | base | (a); SG's scope pocket is part of its bag | `corrie.weight_table` B.2 |
| IMP-2 | Hydration sleeve + 2 hose ports | bag_pockets | 40.3 | base | (a) | same |
| IMP-4 | Door pocket | bag_pockets | 22.0 | base | (a) | same |
| IMP-6 | Phone pocket (B.2: sewn to the left J-strap) | bag_pockets | 11.1 | base | (a) | same |
| IMP-8 | Bow cam / limb cup | bag_pockets | 7.5 | base | (a) | same |
| POUCH | Top pouch 2.71 L (4 G-hooks) | pouch | 64.2 | **as hunted** | clips on; SG and Kifaru leave the lid out of the headline | `weight_pass_corrie.json` take T-2 |
| FLYPKT | Fly base pocket F-02 (stays on the bag) | fly | 5.9 | base | (a) | `panels.yaml` F-02 |
| FLY | Rain fly F-01 (re-cut, G-2) + elastic hem, tether, #5 pocket zip | fly | 69.0 | **as hunted** | no leader counts a rain cover | group + G-2 − F-02 |
| IM | Internal meat harness IM1–IM3 + strap ports (B.2) | straps_meat | 247.2 | base | (b)(c); owner-frozen | parts + B-10 row |
| US | Under-strap cradle US1/US2, pin to pin | straps_meat | 122.4 | base | (b)(c); the equivalent of SG's integrated shelf | parts |
| B24 | Float stand-off links B-24 ×2 (hook on the IM3 eyes) | straps_meat | 54.4 | **meat trip** | hooks on; only for float mode | parts |
| W | Haul wraps W1–W3 (compression in carry; A-2) | straps_compression | 102.7 | base | (c); Seek counts its compression straps | parts + A-2 row |
| AT | Bag-to-frame attachment (fairleads, pins, hooks, hood, ladders, guys, tabs) | attachment | 303.3 | base | (b) | groups |
| TH | Thread + labels | misc | 41.4 | base | (a) | groups |
| RC | Booking reconciliation | misc | 2.0 | base | (a) | groups |
| | **Base** | | **3700.4** | | | |
| | **As hunted** add-ons (IMP-3 + POUCH + FLY) | | **172.0** | | | |
| | **Meat trip** add-on (B24) | | **54.4** | | | |
| | **Total** | | **3926.8** | | | check: 3926.9 |

Known booking approximations (each under 10 g, and each should be split in BL-001):
- ASSUMPTION: the 15.8 g "fly elastic hem, #5 pocket zip + slider, tether" row isn't split, so the pocket's #5 zip
  (it stays on the bag) is counted in the as-hunted add-on. This flatters base by a few grams. Settled by: a row split
  in the ledger, or weighing the zip on the prototype.
- ASSUMPTION: the two 25 mm wing tabs the holster hooks to are inside the 38.8 g holster row, so they're counted as an
  add-on although they stay on the belt. Settled by: the same.

## 4. Like for like: our base against each leader on the leader's inclusions

The adjustment column brings our pack to the leader's inclusions. We remove sewn items the leader explicitly sells
separately and add our add-ons where the leader's figure includes the equivalent. All leader figures and inclusions
are from `docs/research/published_weight_definitions.md`.

| Leader (published figure) | Leader g (lb) | Our basis | Ours g (lb) | Ours − leader |
|---|---:|---|---:|---:|
| SG Sky 5900 + Krux, M belt, no lid | 2308 (5.09) | base − IMP-5L − IMP-2 (SG sells hip pockets and the hydration sleeve separately) | 3644.9 (8.04) | **+1337 g (+2.95 lb), +58 %** |
| SG Sky 5900 + Xcurve, M belt, no lid | 2396 (5.28) | same | 3644.9 (8.04) | +1249 g (+2.75 lb), +52 % |
| Exo K4 5000, bag + frame + lid | 2637 (5.81) | base + pouch − IMP-5L | 3749.4 (8.27) | **+1113 g (+2.45 lb), +42 %** |
| KUIU ICON 6 6000 full kit (hip pockets supplied; lid not stated) | 2790 (6.15) | base (+64.2 g if their figure includes the lid) | 3700.4 (8.16) | +911 g (+2.01 lb), +33 % |
| KUIU PRO 6000 full kit incl. hip pouches (legacy, secondary) | 2639 (5.82) | base | 3700.4 (8.16) | +1061 g (+2.34 lb), +40 % |
| MR Beartooth 85 (inclusions not stated; lid part of product) | 2812 (6.20) | base + pouch | 3764.6 (8.30) | +952 g (+2.10 lb), +34 % |
| MR Metcalf 100, workbook "full" (secondary) | 2708 (5.97) | base + pouch | 3764.6 (8.30) | +1057 g (+2.33 lb), +39 % |
| Kifaru ARK M + Absaroka, no lid, sewn Nalgene pockets | 2835 (6.25) | base + IMP-3 holster | 3739.2 (8.24) | +904 g (+1.99 lb), +32 % |
| Seek Outside Unaweep 6300 shipped (lid, Talon, shelf, 9 compression straps; 24 in frame) | 1673 (3.69) | base + pouch − IMP-5L | 3749.4 (8.27) | +2077 g (+4.58 lb), +124 % |
| Initial Ascent IA5K (frame, hipbelt, shoulder straps, bag, lid) | 2722 (6.00) | base + pouch | 3764.6 (8.30) | +1043 g (+2.30 lb), +38 % |

Notes:
- The leaders publish one belt size (M where stated) and usually don't state the frame height. Ours is one frame for
  every torso, at belt M.
- IMP-1 (scope sleeve), IMP-4, IMP-6 and IMP-8 stay in every comparison. Each leader has its own equivalent pockets,
  and none states what its pockets weigh.
- Against the two owner favourites (SG, Exo), base is **1.1–1.3 kg (2.5–2.9 lb) heavy**. The reclassification
  doesn't change that verdict.

## 5. Where the gap is, on the leaders' own split

SG and Exo publish frame weights that include the meat carry ("Integrated Load Shelf"; "compression straps built
into the frame"). Splitting our base the same way:

| Side | Ours (items) | Ours g | SG | Exo |
|---|---|---:|---:|---:|
| Frame side | FR + TA + BK + HN + BB + IM + US | 2562.3 | Krux, M belt: 1247 | K4 frame: 1332 |
| Bag side | BS + IMP-1/2/4/6/8 + W + AT + FLYPKT | 1079.5 | Sky 5900 bag: 1026 | K4 5000 bag: 1077 |
| Unsplit | IMP-5L + TH + RC | 58.6 | — | — |

ASSUMPTION: the attachment (303.3 g) is booked to the bag side. Neither SG nor Exo says which half carries its
frame-to-bag webbing. Moving all of it to the frame side gives bag 776 g / frame 2866 g, and the conclusion holds
either way. Settled by: nothing on our side; it's a statement about how the leaders split, which only weighing one of
their frames and bags would answer.

**Reading.** On the leaders' split, our bag is level with theirs, and the frame side is about double:
+1230 to +1315 g. The levers are the ones BL-003 to BL-007 and BL-017 already target: frame, back system, belt, meat
harness and under-straps. BL-003 (strap consolidation) should treat IM/US/W as **frame-side** mass when it benchmarks.

## 6. What we would publish (proposal)

Follow Exo's practice, the only leader that is fully explicit: publish three rows, each with a stated belt size.
1. **Base** (belt M): 3700 g / 8 lb 2.5 oz today.
2. **Base + top pouch**: 3765 g / 8 lb 4.8 oz today. Compare this with Exo, Seek and IA.
3. **As hunted** (base + pouch + holster + fly): 3872 g / 8 lb 8.6 oz today.

Plus a line saying the float links (54 g / 1.9 oz) are a meat-trip kit, and a per-belt-size table from the ledger
(S–XXL). Weights to be confirmed on the prototype scale before anything is published: the leaders' claims hold to
about ±50 g when an outlet weighs them, and Sitka's +15 % shows the cost of not checking.

## 7. Owner decisions needed

1. **Adopt the base / as-hunted rule (§2)?** Top pouch, bottle holster and rain fly become add-ons, and the float
   links become a meat-trip kit. Nothing is removed from the pack or the box.
2. **Which number does the 6.6 lb (2994 g) target apply to?** Recommendation: **base**, the SG/Kifaru definition. Base
   is 706 g over it today. Whichever definition is chosen, the target isn't met.
3. **Headline with or without the lid?** Recommendation: publish both rows (§6), as Exo does.
4. **Ship the add-ons in the box or sell them separately?** This is a product/pricing decision. Market research
   P10 (`docs/research/pack_market_2026.md` §4) favoured a complete kit, and the accounting is the same either way.
5. Optional, and **a design change, so not proposed here**: IMP-1, IMP-2 and IMP-5L are sewn, so they stay in base.
   Making them clip-on would move up to 110 g (3.9 oz) out of base. Any such change belongs to a design ticket
   (BL-011 merged bag / BL-006 hipbelt diet), not to this accounting proposal.
