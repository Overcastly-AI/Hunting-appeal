# Bag and weight review, 2026-11-10

Orchestrator review of the bag competition entries and the whole-pack mass, written to seed the backlog in
`docs/backlog/`. Nothing in the design was changed by this review.

**Status of the numbers:** masses come from `analysis/weight_pass_corrie.json` (CORRIE B.1 booking, belt M,
4042 g) and the five `bag_comp/*/result.json` files. I did not re-run the teams' tests or sims. Savings
marked "estimate" are my estimates and are unverified; the tickets exist to prove or kill them.

> **CORRECTION 2026-11-10 (BL-008, `docs/research/published_weight_definitions.md`):** the assumption in §2
> is wrong for Stone Glacier and Exo. Both count their meat carry in the FRAME weight (SG: integrated load
> shelf in the frame; Exo: compression straps built into the frame). Split their way, our bag side is about
> 1080 g, level with their bags (1026–1077 g). **The whole gap is on the frame side: 2562 g (frame, back
> system, belt, harness, meat straps) against 1247–1332 g.** The 842 g of straps and hardware is still real
> mass and still worth cutting, but it is a frame-side problem, and the frame-side tickets (BL-003, BL-005,
> BL-006, BL-007, BL-017) matter most. Like for like on published system weight we are 904–1337 g heavier.

## 1. Where the pack stands

| Config (belt M) | Mass |
|---|---|
| CORRIE B.2, today's frame (dowels booked) | 3983 g (8.78 lb) |
| CORRIE B.2 on the H1 frame | 3927 g (8.66 lb) |
| + package C (gated by tests) | about 3873 g (8.54 lb) |
| Leaders, published system weight | 2308–2790 g (5.1–6.2 lb) |

## 2. Main finding: the weight is in straps, hardware and suspension, not in bag fabric

The earlier weight pass said "the bag side is lighter than the leaders". That compared our bag fabric and
pockets (779 g) with their complete bags (1021–1077 g). Their bag weight includes their compression straps,
meat-carry straps and frame attachment. Ours books those separately. Like for like:

| Bag side, like for like | g |
|---|---:|
| Bag body | 548 |
| Bag pockets | 163 |
| Top pouch | 88 |
| Rain fly | 68 |
| **Meat haul + compression straps** | **539** |
| **Bag-to-frame attachment** | **303** |
| **Ours, total** | **1709** |
| Stone Glacier Sky 5900 bag | 1021 |
| Exo K4 5000 bag + lid | 1077 + 230 |

ASSUMPTION: the leaders' bag weights include their straps and attachment hardware; BL-008 verifies this.

So the bag side is roughly 400–700 g heavier than the leaders, and almost all of it is the 842 g of straps
and hardware. Frame plus suspension is the other gap: 2289 g against 1162–1400 g.

### 2.1 The strap systems (842 g)

Five separate strap systems do overlapping jobs:

| System | g | Job |
|---|---:|---|
| Internal meat harness IM1–IM3 (38 mm straps, 6 sliding-gate hooks, 3 cams) | 254 | holds meat in the bag against the spreader |
| Under-strap cradle US1/US2 | 122 | holds meat when the bag is off |
| Haul wraps W1–W3 | 108 | wrap bag and meat in float mode; compression in carry |
| Float links B-24 | 54 | hang the bag behind the meat |
| Bag-to-frame attachment (8 fairleads, 8 pins, 4 hooks, hood, ladder, guys, tabs) | 303 | holds the bag on the frame |

On top of these sit the wing straps, the pouch straps and the roll-top straps (in the bag-body group).
The loadout study showed boned meat fits inside the bag, so float mode is rarely needed, yet its parts ride
in the base weight. Team B (FELL) already showed the wings can go if W1/W2 do the compression. Team C
(TAILGATE) showed three straps at the IM heights can carry the bag's hoop load so the door zip is unloaded
(zip SF 78). One external strap set could do compression, zip unloading, side carry and float wrapping.

### 2.2 Back system (414 g)

Back panel 251 g (mesh, 120 mm XLPE rails, carbon backer strips, sleeves, pad) plus the Sandwich v2 spreader
162 g. Two stiff layers sit a few centimetres apart, the spreader on the bag side of the stays and the rail
backers on the wearer side. Nobody has checked whether one structure can do both jobs.

### 2.3 Hipbelt B (559 g, against 363 g for the Stone Glacier 3-piece belt)

50 mm webbing, buckle and stabilizers 92 g; centre plate 78 g (package C takes 25 g); HDPE wing stiffeners
41 g; bottle holster 39 g; pad seat 61 g.

### 2.4 Frame (H1, 1025 g)

The carbon crown, rack, pawl, guides, bushings and the long sleeves the crown legs slide in exist for the
telescoping torso adjust. The frame is printed per unit, so the torso length could be printed in, with a
small fine-adjust at the harness yoke. Team E measured the upper stays that carry the sleeves at 342 g.
No study has tested a fixed-torso frame.

## 3. Bag competition: what the five entries show

All five teams converged all their cloth sims and produced Blender renders, but none reported; the usage
limit stopped them. All five reuse the CORRIE rev B box shell, so this was a feature competition on one
body, not five different bags.

| Entry | Bag system g (own metric) | vs CORRIE B.2 | Curved seams | Hours | 15 in meat CG (limit 190) | Access misses day/elk/sheep |
|---|---:|---:|---:|---:|---:|---|
| A EVOLVE "CORRIE E" | 734.6 | +24 | 2 | 38.3 | 179.6 | 0 / 0 / 0 |
| B LEAN "FELL" | 583.1 (day 445) | −133 | 0 | 27.9 | 175.4 | 0 / 0 / 4 |
| C OPEN "TAILGATE" | 758.7 | +48 | 1 | 25.7 | 185.0 | 0 / 0 / 1 |
| D MODULE "CACHE" | 991.0 | +99 | 1 | 37.9 | 182.1 | 0 / 0 / 2 |
| E FORM "CHERT" | 739.3 | +18 | 1 | 27.7 | 187.4 | 1 / 0 / 3 |

**Problem:** the teams used four different baselines for the same CORRIE B.2 bag system (710.6, 716.5, 721.7
and 892.1 g). The deltas are comparable within a team but not across teams. BL-001 fixes this.

**Best idea from each:**
- **A:** hip-reach pockets on the wings give zero access misses on every belt size; rounded door corners
  widen the door from 214–281 mm to 294–334 mm.
- **B:** lighter fabrics (ULTRAGrid, 70D collar, ULTRA 200X floor), no wings, add-on pods only when the trip
  needs them: −133 g, zero curved seams, the best 15 in CG (its shell is 3 % shallower).
- **C:** lid straps at the IM heights carry the hoop load; the full aft face opens; fewest hours.
- **D:** a removable wipeable slab that holds the sleep kit and becomes the meat liner, so blood stays off
  the bag; a snack pocket on the shoulder strap.
- **E:** camo chamfer blades on the aft corners, where the panel line, the camo break and the door zip are
  one line. The best-looking entry.

**Shared weaknesses:**
- **15 in torso meat CG is thin for everyone** (175–187 mm against 190, before a +4 mm sim bias). Only the
  shallower FELL shell has real margin. Shape matters more than features here.
- **Look:** every render reads as an inflated sack that mushrooms above the shoulders. The renders use the
  92 L "packed" case; no entry shows a day load or a 6-day load cinched down.
- **Sheep load:** the second bottle is out of reach on four of five entries.

## 4. Direction

1. **One merged bag ("CORRIE F"):** the FELL shell and fabrics, a shape tuned for the 15 in CG, hip-reach
   pockets from A, the unloaded-zip strap idea from C, the meat liner from D and the camo lines from E.
2. **One strap architecture** for compression, door unloading, side carry and meat hauling, with float parts
   as a meat-trip kit.
3. **Diet studies** on the attachment, back system and hipbelt.
4. **A fixed-torso printed frame study**, the largest single lever left on the frame.
5. **One mass ledger**, so every comparison uses the same definitions.

**Potential (estimates, unverified; the tickets decide):**

| Lever | Estimate |
|---|---:|
| Strap consolidation, float kit out of base | −250 to −300 g |
| Attachment diet | −60 to −100 g |
| Bag body and fabrics (merged bag) | −100 to −150 g |
| Back system integration | −80 to −120 g |
| Hipbelt diet | −60 to −80 g |
| Fixed-torso frame | −150 to −300 g |
| Fatigue coupon CA-1 at 0.40 (physical test) | −70 g |

If most of these hold, the pack lands around 3000–3200 g (6.6–7.1 lb) with the features kept. That is
a stack of unverified estimates; expect some to fail.
