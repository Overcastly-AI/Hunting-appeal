# CORRIE loadout study: what goes in the bag, where it goes, and what to change

Owner: pack-designer. Date 2026-11-08. Status: **study and proposals only. CORRIE geometry is not changed.**
Owner request: "How can this improve? Research what goes into a bag."

| What | Where |
|---|---|
| Research (cited, every claim has a URL) | `docs/research/hunting_loadouts.md` ([HL §n]) |
| Loadout data (3 canonical loadouts, 40 items, each mass and volume cited or ASSUMPTION) | `designs/pack_5200/loadouts.yaml` |
| Packing model, CG, access, spotter options, improvements | `designs/pack_5200/concepts/corrie_loadout.py` |
| Renders | `designs/pack_5200/concepts/corrie_loadout_render.py` |
| Numbers | `outputs/loadout/loadout_results.json` (`python designs/pack_5200/concepts/corrie_loadout.py --render`) |
| Tests | `tests/test_corrie_loadout.py` (7 tests) |

## 1. Findings in one screen

1. **CORRIE has room.** The main bag is 88.4 L sewn (cloth-sim rev B mean, 5390 cu in). The 6-day elk loadout uses
   45 L (2750 cu in) of it and the 8-day sheep loadout 56 L (3440 cu in), so there are 32-48 L of headroom. On the
   day-6 pack-out, camp plus 45 kg (99 lb) of boned meat still fits inside the bag, with about 5 L (300 cu in) to
   spare. Every case stays inside the 68 kg (150 lb) rating, and float mode is never needed.
2. **CG is not the problem.** Every loadout and every pack-out sits inside HA-LS-1 rev C even after adding the 15 in
   cloth-sim peel. The worst gear case is sheep at 183 mm against the 205 mm limit; the worst meat case is 156 mm
   against 190. The load CG height is z 430-455 for multi-day loads, below the rev C basis of z 550.
3. **Access is the problem.** Today **every hourly item fails** in every loadout, because none can be reached with the
   pack on. Water has no pack-on home: CORRIE dropped SPINE's side pockets and has **no hydration sleeve or hose
   port**, although **R-19 (frozen)** requires one. The phone does not fit today's hipbelt pocket. Snacks end up in the
   top pouch. Only the inReach works, on a strap clip.
4. **The spotter has no designed home.** It does fit under a plain wing: 65 mm fits, and 85 mm fits with the wing let
   out to 150 mm. But it then rides loose against the gusset with nothing to stop knocks, and the leaders all give the
   scope a dedicated pocket or sleeve [HL §3.2].
5. **The wings saturate on a sheep load.** An 85 mm spotter plus a medium tripod, head, sit pad and rain jacket fill
   both wings (5.7 and 5.9 of 6 L), so the trekking poles end up inside the bag.
6. **Day loads sink to the floor.** The roll cannot close below the door hinge band at z 650 (ASSUMPTION), which leaves
   53 L below it. A 12 L day load therefore sits in the bottom 300 mm, and a loose bladder rides at z 75 instead of at
   shoulder-blade height. The wings compress only z 150-600 of the sides.
7. **The kill kit and first aid are reachable through the door but not organised.** They end up in the aft-low column,
   under whatever was packed after them. The door opens upward, so an open pocket on it would spill.

## 2. Loadouts (`loadouts.yaml`)

Totals exclude worn clothes and the weapon in the hands. "Bag load" is what the bag and frame carry; the chest
harness, hipbelt and strap items go to the body.

| Loadout | Carried | In the bag load | Packed volume | Pack total with CORRIE (3725 g) |
|---|---:|---:|---:|---:|
| Day hunt from camp (rifle, Oct) | 10.7 kg (23.6 lb) | 9.1 kg | 23.8 L (1450 cu in) | 14.4 kg (31.8 lb) |
| 6-day elk / mule deer, rifle | 19.2 kg (42.3 lb) | 17.4 kg | 53.5 L (3260 cu in) | 22.9 kg (50.5 lb) |
| 6-day elk, archery (no spotter; bow, calls, decoy) | 18.1 kg (39.9 lb) | 16.2 kg | 52 L | 21.8 kg (48.1 lb) |
| 8-day sheep / goat, rifle | 21.6 kg (47.6 lb) | 20.0 kg | 64.0 L (3900 cu in) | 25.3 kg (55.8 lb) |

These land inside the published bands: 45-55 lb for a 5-7 day elk hunt and 41 lb packed for 14 days of sheep
[HL §1]. Food is 816 g/day for elk (1.8 lb, Exo) and 680 g/day for sheep (1.5 lb); the day's snacks are taken out of
the food bag. Water is 2 L in a bladder plus 1 L in a bottle (elk), or 2 × 1 L bottles (sheep, as SG_LYLE). The
spotter class is 50 mm on the day hunt, 65 mm on 6-day elk, none for archery, and 85 mm on sheep. Mass and volume by
category are in screen 3.

## 3. Model (simple, traceable)

- **Columns.** The main bag is two half-depth columns along z: F (frame half) and A (aft half). Each column's area is
  half of CORRIE's rev B section, scaled by the bulge factor 88.4 / 75.9 = 1.165, so that the full bag holds the sewn
  volume from the cloth sim instead of the 75.9 L flat-panel rule (corrie.py REVS note).
- **Stacking.** Items stack bottom-up in band order (low, mid, high). Each item takes its effective volume: packed
  volume divided by a fill efficiency of 0.90 for soft items, 0.75 for rigid items and 0.85 in pockets (ASSUMPTION).
  The layer model reproduces CORRIE's own uniform-fill CG within 6 mm in y (tested).
- **Placement.** Each item has a zone preference list; the first zone that exists in the configuration, has room and
  fits the item's dimensions wins.
  - Wings: 6 L each (ASSUMPTION), items up to 150 mm thick, carried at z 375.
  - Pouch: 4.0 L, interior 300 × 195 × 65 mm.
  - Hipbelt pockets: 0.97 L, interior 145 × 92 × 50 mm (ASSUMPTION from the HP-01 cut).
  - Roll: closes no lower than z 650, with the pouch on top.
- **CG.** The bag-load CG counts everything the bag carries. Hipbelt, chest and hands are excluded, as in rev C.
  - Rev C check: geometric CG + peel. The peel is the sim CG minus the model's geometric CG of the same case: 55.7 mm
    (fill) and 54.8 mm (meat: 30 kg meat + 38 kg fill, the sim's own case) at 15 in; 37.6 / 37.7 mm at 19 in.
  - Applying the 68 kg peel to 10-60 kg loads is conservative.
- **Access classes.** 0 = on body; 1 = pack on; 3 = pack off, outside (wings, pouch); 4 = pack off, through the door
  (aft half, item above the sill and below the hinge); 5 = roll-top or unpack.
  - Rule (DECISION, this study): constant and hourly items need class ≤ 1, as the owner asked ("without taking the
    pack off or opening the roll-top"). Glassing, weather, kill and emergency items need ≤ 4. Daily and camp items:
    anything.
- **Meat case.** Day 6 (or the kill day): the game bags are full, and half a day of food is left.
  - Meat goes in column F against B-01 on IM1-IM3, and frame-half gear moves aft.
  - If the meat does not fit, float mode is used (B-24, 170 mm gap, ≤ 53 kg).
  - Meat: 1.0 kg/L in game bags (ASSUMPTION).

## 4. Results per loadout (CORRIE today)

| Loadout | Main bag used / free | Meat that still fits (volume / rating) | Bag-load CG y geo / +15 in peel (limit) | CG z | Access misses (today) |
|---|---|---|---|---|---|
| Day | 11.6 / 76.8 L | 69 kg / 59 kg | 103 / **158** (205) | 334 | 5: phone, bladder, bottle, snacks, kill kit |
| Day + 40 kg meat | 9.3 L gear + meat, 34.6 L free | in bag | 83 / **138** (190) | 532 | (pack-out) |
| 6-day elk rifle | 45.1 / 43.3 L | 39 kg / 50 kg | 107 / **162** (205) | 429 | 4: phone, bladder, bottle, snacks |
| 6-day elk + 45 kg meat (day 6) | 33.6 L gear + meat, **4.8 L free** | in bag | 101 / **156** (190) | 520 | (pack-out) |
| 6-day elk archery | 43.4 / 45.0 L | 41 kg / 52 kg | 102 / **157** (205) | 436 | 4: as rifle |
| 8-day sheep | 56.3 / 32.1 L | 29 kg / 48 kg | 124 / **180** (205) | 455 | 6: phone, GPS, bottle, snacks, poles (wings full), rain pants (above the door) |
| 8-day sheep + 30 kg meat | 44.2 L gear + meat, 10.8 L free | in bag | 100 / **155** (190) | 463 | (pack-out) |

**Verdicts**

- **Day.** Fit: OK, with huge headroom. CG: OK. Access: **FAIL** (water, phone, snacks; the kill kit sits under the
  sill). The load sinks to the floor and the bladder rides at z 75.
- **6-day elk (rifle and archery).** Fit: OK, 43 L free going in. Pack-out: 45 kg of meat fits in the bag with 5 L to
  spare; more than about 50 kg would need float mode. CG: OK, margin 43 mm (gear) and 34 mm (meat). Heavy items sit
  close to the frame at shoulder-blade height: food 4.65 kg at y 71, z 345-549 and the bladder 2.1 kg at z 556-597, so
  7.2 kg is in the frame half between z 330 and 650. Access: **FAIL** on the 4 hourly items only.
- **8-day sheep.** Fit: OK, 32 L free. CG: OK, the tightest of the set at 183 mm with the 15 in peel (margin 22 mm),
  because the 1.9 kg spotter and the 1.1 kg tripod ride in the wings at y 113. Access: **FAIL** on hourly items. The
  wings are full, so the poles go inside.
- **Lateral balance.** The spotter in the left wing and the tripod in the right (the KUIU rule) keep x within ±10 mm on
  the elk and sheep loads. On the day load with the bottle moved to the hipbelt it is 27 mm right of centre, because the
  right wing carries the tripod, head, poles and rain jacket against a 709 g spotter on the left.

## 5. Spotter and tripod placement (open owner question)

Tripod: under the right wing on every loadout. The folded 371-470 mm (14.6-18.5 in) legs fit the 450 mm wing with up
to 150 mm of overhang; this is the existing render 20261108_corrie_4. Spotter options, computed:

| Option | 6-day elk (65 mm, 1585 g): access / CG +peel | 8-day sheep (85 mm, 1910 g): access / CG +peel | Mass | Notes |
|---|---|---|---|---|
| **(a) padded sleeve in the left wing (IMP-1)** | 3 (pack off, outside) / 161 mm | 3 / 183 mm | +45 g | Quiet (XLPE liner, nothing to hit), protected when the pack is set down, balances the tripod. Same position as (b). |
| (b) bought padded case under a plain wing | 3 / 162 mm | 3 / 180 mm | +150 g (ASSUMPTION case) | 0 build hours; 85 mm in a case is ~162 mm thick, past the 150 mm wing reach. Rattle depends on the case. |
| (c) inside via the door (aft half, mid) | 4 (pack off, open door) / 165 mm | 4 / 176 mm | 0 | Lowest sheep CG (it rides inboard), but every glassing stop means opening the 1.26 m door zip under load (PT-7 risk), and the spotter competes with the kill kit and puffy for the door zone. |

**Recommendation: (a).** CG differences between the options are 1-7 mm, so CG does not decide. Access and quiet do: (a)
is reachable without opening the bag, is protected, and costs 45 g and about 1.7 h. Option (b) is the zero-sew fallback
for 50-65 mm scopes.

## 6. Improvements (proposals; ranked; no CORRIE geometry changed)

Mass is the cut area plus seam allowance × the record gsm (`data/materials/`) plus hardware. Hours come from the
`bag_concepts.HOURS` beginner model (ASSUMPTION; use it to rank, not to plan evenings).

| Rank | Id | Change | Problem it solves (research) | Mass | Beginner h | IP / guardrail read |
|---:|---|---|---|---:|---:|---|
| 1 | **IMP-2** | Restore hydration sleeve B-09 (100D, 250 × 430) hung from the B-06f collar strip above IM3 (z ≥ 545), 2 bound hose ports at the collar seam | R-19 is frozen and CORRIE does not meet it. Water is hourly; hunters drink more from a bladder [HL §2.4]. It also hangs the bladder at z ~640, near the frame, instead of on the floor in a day load | **17.5 g** | **1.9** | Same part as the released SPINE B-09. Not on the frame interface: H1-H4 untouched |
| 2 | **IMP-1** | Padded scope sleeve on the inside of the left wing: 330D tube, 3 mm XLPE liner on the bag side, shock-cord top | The spotter has no home [HL §3.2]; damage and rattle [HL §4.3] | **44.8 g** | **1.7** | US 8,960,513 lapsed for fees (2019) and claims a hinged-cover front optics compartment with tripod-leg holders, which this is not. Wing pockets for scopes are prior art (Eberlestock X2). H1-H4 untouched |
| 3 | **IMP-3** | Hipbelt bottle holster for a 1 L bottle (power mesh, 330D base and back, shock cord, 2 loops onto the belt), right side | No pack-on bottle spot; the bottle is the common backup or main water [HL §2.4] | **29.7 g** | **1.9** | US 5,114,059 (side holsters, 1992) has expired. Common product class. Hipbelt only |
| 4 | **IMP-4** | Zipped bellows pocket inside the door (100D, 300 × 340, 50 mm gusset, #5 coil zip 280 mm), sewn flat before the door zip goes in | Kill kit, game bags and first aid at the door, not at the bottom [HL §2.8, §4.1]. It must zip because the door opens upward | **23.9 g** | **2.1** | Generic internal pocket, no hook-and-loop. On the door, not the frame side |
| 5 | **IMP-5** | Taller hipbelt pockets: HP-01 face 180/140 × 110 → 200/160 × 130 mm, gusset 55 → 60 mm (0.97 → ~1.3 L, 59 → 79 cu in) | A large phone (160 mm) does not fit today's ~145 mm interior; this is a top complaint [HL §4.2] | **4.1 g** | **0.3** | Size change only |
| 6 | IMP-7 | Silpoly wet-gear sack 400 × 500 for a wet shelter, carried outside the dry bag under the pouch | Wet shelter away from the sleep system [HL §4.4] | 14.2 g | 0.9 | Stuff sack |
| 7 | IMP-6 | Stretch phone / inReach pocket on the left shoulder strap | Pack-on phone; optional once IMP-5 fits it [HL §4.2] | 10.5 g | 0.9 | Common accessory; harness part |
| 8 | IMP-8 | Bow cam / limb cup at the foot of the right wing (330D cup, Hypalon base) | CORRIE kept the riser loops but lost SPINE's band cam cup (SH-04), so the archery loadout has no lower seat for the bow | 10.6 g | 0.8 | Restores a released SPINE function |

**Recommended short set: IMP-2, IMP-1, IMP-3, IMP-4, IMP-5.**

- Mass: **+120 g (4.2 oz)**, so the pack goes from 3725 to about 3845 g (8.21 → 8.48 lb).
- Build time: **+7.8 h** beginner (ASSUMPTION model). Each item is a flat rectangle or tube with straight seams and no
  curves.
- Result: hourly-access misses go from 4-6 per loadout to **0 on the day, elk rifle and elk archery loads**. Sheep
  keeps 2 misses: the second bottle (one holster) and the poles (wings full). The bag-load CG moves by less than 4 mm
  on any loadout.
- IMP-8 is worth adding if the owner hunts archery.

Before / after zone-access table (6-day elk): screen 4. Packing maps: screens 1 (today) and 2 (with the set).

**Not proposed, with reasons:**
- No sewn meat liner: frozen "no sewn meat sleeve". Blood is handled by game bags or a compactor bag, the ULTRA 200
  B-01, drain grommets and a creek rinse [HL §4.5].
- No rattle fixes beyond IMP-1. Pack the stove inside the pot with soft items around it; this is a packing rule
  [HL §4.3], not a sewn feature.
- No second wing or pocket for the sheep poles. Carry them in the hands, or lash them under W1-W3. Adding wing area
  costs build time for one use case.

## 7. Owner decisions

1. **Spotter home: (a) wing sleeve, (b) a bought case under a plain wing, or (c) inside via the door?**
   Recommendation: (a).
2. **Adopt the short set IMP-1..5** (+120 g, ~7.8 h)? IMP-2 is arguably not optional, because R-19 is frozen.
3. **Archery: add IMP-8** (cam cup, +11 g)?
4. **Day-hunt compression.** With 53 L below the hinge band, should the user guide say "roll the collar into the body
   and clip W1-W3 across the aft face for day loads", or do you want a lower roll stop (a geometry change, not
   proposed here)?
5. **Hipbelt pocket size (IMP-5).** This changes HP-01 on the hipbelt, which SPINE also uses. Change both?

## 8. Assumptions (new in this study)

| Item | Assumption |
|---|---|
| Fill efficiency | 0.90 soft, 0.75 rigid, 0.85 in pockets |
| Wing capacity | 6 L usable per wing, items ≤ 150 mm thick, ≤ 150 mm overhang, carried at z 375 |
| Hipbelt pocket interior | today 145 × 92 × 50 mm; IMP-5 175 × 112 × 55 mm |
| Roll stop | the roll cannot close below z 650 (door hinge band) |
| Meat | 1.0 kg/L in game bags; pack-out loads 40 / 45 / 30 kg (day, elk, sheep) |
| Peel | 68 kg sim peel applied to lighter loads (conservative) |
| Access rule | constant and hourly items need pack-on access (class ≤ 1) |
| Item envelopes | spotter diameters, food 0.5 kg/L, clothing stuffed volumes, bugle tube 280 g (see `loadouts.yaml`) |
| Spotter case | 150 g, 6 mm wall |

## 9. Hand-offs (if the owner adopts the set)

- **pattern-maker:** B-09 on CORRIE's B-01 / B-06f; the M-01L sleeve; the door pocket on B-02door (flat-work, before
  the zip); the HP-01 resize; the holster.
- **materials-engineer:** a 3 mm XLPE sheet record (the mass uses the generic `xlpe_foam` density, 33 kg/m³); a #5
  slider mass (3 g ASSUMPTION).
- **manufacturing-engineer:** the door pocket goes into flat-work before the door zip; the B-09 loop is caught in the
  B-06f seam.
- **cloth sim:** none needed. The proposals add < 50 g to the bag and do not change the shell.

## Screenshots

- `outputs/screens/20261108_loadout_1.png`: packing map, 6-day elk, CORRIE today (side cutaway + aft view, colour =
  access frequency)
- `outputs/screens/20261108_loadout_2.png`: the same with IMP-1..5
- `outputs/screens/20261108_loadout_3.png`: mass and volume by category, three trips
- `outputs/screens/20261108_loadout_4.png`: before / after access table
- Copied to `docs/screens/`: `_2`, `_4`
