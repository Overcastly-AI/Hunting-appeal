# CORRIE: the owner's bag body (engineered concept, step before pattern release)

Owner: pack-designer. Date 2026-11-07. Owner pick (DECISIONS, commit 92e60f6): "13 with a u shape zipper and a roller
top. We also need a pouch up top for loose goods" = concept 13 MANTLE (side compression wings) + the HATCH horseshoe
(U) zip door + roll-top + a top pouch. Name **CORRIE** (a glacial cirque; original).

Code: `designs/pack_5200/concepts/corrie.py` (geometry, pieces, seams, mass, checks),
`corrie_render.py` (renders). Tests: `tests/test_corrie.py`. Built on the concept library
(`bag_concepts.py`, `bag_concepts_wide.py`) and measured with the same metric code as the 13-concept study
(`analysis/bag_alternatives.md`). **The released SPINE files are not changed.** Research:
`docs/research/bag_body_architectures.md` (cited as [BA §n]).

## 1. What it is (one paragraph)

A tapered flat-panel box body (85.2 L to the fill line, 15.5 in wide, 11.4 in deep, 40.2 in tall) on the unchanged
frame interface. The **aft face** carries a **horseshoe door** (#10 coil, 1258 mm, z 110–650, hinged at the top). Two
**side compression wings** (200 × 450 mm) are sewn into the frame-side corner seams and cinch to webbing loops sewn
into the **aft corner seams**, outboard of the door zip, so the wings stay cinched when the door opens. A **removable
4.0 L top pouch** rides on the closed roll. Camo is used only at wear lines and edges: chevron kick plate, roll-top hem
band, wing leading-edge bars, door zip garages and the pouch top.

## 2. Body decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Door on the aft face.** | The wings cover the side panels; the aft face is the only face they leave free. |
| D2 | **Wing straps hook to 25 mm webbing loops caught in the aft corner seams** (gusset / U-surround), 2 per wing at z 260 and 490. The door zip runs 45 mm inboard of those seams. | The wings compress with the door closed, and the door opens without undoing a wing. No stitching crosses the zip path. |
| D3 | **Door z 110 → 650, hinge at the top, R 60 lower corners** (the U opens down one side, across the bottom and up the other). | Clear width 214 / 242 / 281 mm at IM1 / IM2 / IM3 (z 190 / 330 / 520): every meat strap and its hooks can be reached. The sill is 75 mm above the floor (z 35), so low gear comes out without unpacking. The top at z 650 leaves the hinge band free for B-22. |
| D4 | **Zip: #10 coil, two sliders, cord pulls, fabric garages.** 3 mm Dyneema pull loops in a rubber sleeve (no metal tabs, quiet), sliders park in two camo zip garages (SH-07, 40 × 60) at the upper ends of the U. | #10 matches the leaders' main zips and our released zip (O-13 rejected #8 on the main bag). The record is `coil_zipper_10`: crosswise 900 N, quietness 4. Garages stop a slider walking open under load and keep it reachable with gloves. Zip failure is the top field complaint (A1 [BA §3]); see §6 risk 1. |
| D5 | **Guy tabs B-22 move from z 752 to z 695 on the hinge band** (x ±149). | The box collar seam is at z 736, so the 50 × 60 tab now spans z 665–725: 11 mm under the collar seam and 15 mm above the door top. The guys still run from the hood ears (x ±95, bar z 702.6 at 19 in) to the tabs, 292 mm long, now 1.5° below horizontal (SPINE: 9.1° up). That is a more direct forward pull on the bag top, but it must be confirmed in the cloth sim (§5). |
| D6 | **Frame-side collar strip B-06f in ULTRA 200.** | The B-20 hood-ladder top (z 795) is 59 mm above the box collar seam (z 736). The top rungs must sit on laminate, not 100D (concept-study rule). |
| D7 | **W1–W3 stay** (frozen D-20) for haul, float and antlers. In daily carry the wings do the side compression, so W1–W3 can stay unclipped on their gusset keepers and do not cross the door. | The owner's freeze stands. Merging W1/W2 into the wing straps is offered as owner question Q3. |
| D8 | **Rest of the frame interface unchanged.** Hood B-19 on the crown bar, B-20 ladders on B-01, IM2/IM3 rated hooks on T2 + B-23 / T3 + B-17, hinge pins + HE eyes + B-18 in the B-01 / B-05 seam, B-24 float links via T3, under-strap channels on the floor, internal meat straps IM1–IM3 through the B-01 ports at the 8 swell crests, bow riser carry (B-11 loops), rain fly in its base pocket. | Patent guardrails H1–H4 are untouched: no fabric panel between frame and bag, under-straps pin to pin, lifters on the crown, nothing between the spreader and the z 330 bar. |

## 3. Top pouch: removable 4.0 L pouch on the roll (chosen)

**Options compared**
- **(a) Lid-style pouch riding the closed roll.** Chosen.
- **(b) Fixed pocket on the upper aft face.** Small, sits under the hinge band and the guys, and fights the door.
- **(c) A full floating lid** like the current 4.9 L accessory, which has 4 magnetic buckles and weighs 141 g.

**What users say [BA §6]**
- Lids are valued for small loose items and for lashing heads and antlers. Exo's floating lid "works well for securing loose items" ([ROKSLIDE K4 review](https://rokslide.com/forums/threads/exo-mountain-gear-k4-pack-review-updated-3-28-23.299208/post-3806816)).
- The Mystery Ranch Metcalf lid's "two large, zippered pockets" are praised ([GunsAmerica](https://gunsamerica.com/digest/mystery-ranch-metcalf-75-backcountry-hunting-pack-review)).
- Users want the lid to be separate. A KUIU ICON 6 owner disliked that the lid is not sold on its own ([ROKSLIDE ICON 6 thread](https://rokslide.com/forums/threads/new-kuiu-icon-6.455714/)), and optional lids are common: Granite Gear Crown3, Seek Outside and Kifaru Absaroka ([OutdoorGearLab Crown3](https://www.outdoorgearlab.com/reviews/camping-and-hiking/ultralight-backpack/granite-gear-crown3-60), [GearJunkie Absaroka](https://gearjunkie.com/outdoor/hunt-fish/kifaru-absaroka-review)).
- Pockets you cannot reach are the recurring hate ([CleverHiker Crown3](https://cleverhiker.com/backpacking/granite-gear-crown3-backpack-review); Exo added a forward-facing lower pocket "nearly everyone can reach": [Exo stretch pockets](https://exomtngear.com/blogs/article/k4-stretch-pockets)).

**Design**
- Boxed: top + base 320 × 210 mm and one boxing strip 1060 × 70 mm. Straight seams only; the 4 corners are pivots.
- 4.0 L (320 × 210 × 70 with 15 % corner loss, ASSUMPTION), 244 cu in. Not counted in the 5200.
- **One straight #8 coil zip, 300 mm, on the aft long edge**, with one slider, a glove cord pull and a garage at the closed end. This is the edge a partner can reach, and you can reach it with the pack off. A straight edge zip is the easiest to sew and to work with gloves.
- **Attachment, all 25 mm G-hooks (HAUL family, the same part as W1–W3 and the wings):** 2 rear straps 120 mm to webbing loops on the frame-side hem, and 2 front straps to the roll-clip webbing.
  - **Roll-top access:** unhook the 2 fronts and flip the pouch back; the rear straps keep it on the pack.
  - **Removal:** unhook all four.
  - **Hood and guys:** the pouch sits on the roll at about z 1100, above the hood (z ~703), the B-20 ladders (to z 795) and the guys, so it touches none of them.
- **Camo:** pouch top in printable 630D (owner base camo); base and strip in 330D solid. No hook-and-loop, no magnets.
- **Mass:** 52.3 g fabric + 9.4 g zip + 26.1 g straps, hooks and pull = **87.8 g**, against 141.2 g for today's optional lid.

## 4. Mass and simplicity: what was cut (naive merge → CORRIE)

Naive merge = MANTLE wings as drawn (230–250 × 700 mm, camo-bound edges, 3 straps a side) + HATCH door + today's 4.9 L
lid. All from `corrie.build(optimised=False)`, same metric code.

| Item | Naive | CORRIE | Change | How |
|---|---:|---:|---:|---|
| Wings (fabric) | 66.0 g | 36.9 g | −29.1 | 200 × 450 mm rectangles (z 150–600, the zone a tripod or pad needs), hemmed edges instead of binding |
| Camo accents | 71.9 g | 49.7 g | −22.2 | 1.2 m camo binding per wing replaced by a 25 × 450 leading-edge bar; zip garages added (+2.5 g) |
| Wing hardware | 80.4 g | 53.6 g | −26.8 | 2 straps per wing instead of 3. One hook family: G-hook + ladder lock, the same parts as W1–W3, so they swap in the field |
| Top pouch / lid | 141.2 g | 87.8 g | −53.4 | boxed 4.0 L pouch, one #8 zip, G-hooks instead of 4 magnetic buckles |
| Zips | 38.4 g | 47.8 g | +9.4 | pouch zip added (#8, 1 slider) |
| **Bag-body group** | **694.5 g** | **563.0 g** | **−131.5 g** | |

**CORRIE against SPINE (released)**
- **Body group:** 563.0 g against 333.2 g, so **+229.8 g**.
- **Pack total:** 3495.6 + 229.8 = **3725 g (8.21 lb)**. Like for like with SPINE carrying its optional lid (3637 g): **+88 g**.
- **Gap to the published target:** the owner's ~6.6 lb (2976 g) is not met by CORRIE, nor by SPINE (7.71 lb today).

**Not applied (fabric swaps are on hold per the owner):**
- Side gussets in Challenge ULTRA 200: they sit under the wings, so the louder film face is shielded. Saves −21.8 g, with better abrasion (2000 vs 800 Taber) and tear (250 vs 90 N) ([records](../../../data/materials/)).
- Merging W1/W2 into the wing straps: owner question Q3.

**Simplicity**
- 33 cut pieces (8 of them identical boxed swells and 8 small camo pieces).
- 13.8 m of seams, **1 curved seam**: the door zip with its two R 60 corners. Everything else is straight seams and pivots on flat panels.
- 2 zips.
- **~32 h** beginner estimate (ASSUMPTION model), against ~35 h for SPINE and 29 h for the naive merge, which booked the lid as bought.
- The hours by operation are in `corrie.numbers()`. Hardest step: setting the U-zip around the two R 60 corners (practise on the hipbelt-pocket drill, BUILD_PLAN step 3).

## 5. Numbers

| Quantity | Value | Basis |
|---|---|---|
| Main bag | **85.2 L / 5199 cu in** to the fill line | R-01 rule, concept integrator (checked against SPINE to 0.06 %), dome law calibrated on SPINE |
| Top pouch | **4.0 L / 244 cu in** (not counted) | 320 × 210 × 70 mm × 0.85 (ASSUMPTION) |
| Total with pouch | 89.2 L / 5443 cu in | |
| Height, width, depth | fill 40.2 in (1021 mm), 15.5 in, 11.4 in max (10.7 in above the setback) | concept envelope |
| Collar seam | z 736.3 | solved for 85.2 L |
| Body group / pack | 563.0 g (+229.8 g vs SPINE) / **3725 g, 8.21 lb** | cut area × record gsm, records, ASSUMPTIONs listed |
| Pieces / seams / curved | 33 / 13.8 m / 1 | `huntkit.patterns` pieces, `check_seams` ≤ 0.91 mm |
| Zips | door #10, 1258 mm, 2 sliders; pouch #8, 300 mm, 1 slider | |
| Beginner hours | ~32 h | ASSUMPTION model (`bag_concepts.HOURS`) |
| Uniform-fill CG | y 148.6 / z 557.7 mm (SPINE 148.2 / 592.5) | concept integrator |
| With 1 kg in the pouch (68 kg rated) | y 147.5 / z 566 mm | lever sum (pouch centre y 76, z 1131) |
| **Loaded CG, cloth sim (rev B, 2026-11-08)** | **190.4 / 172.3 / 136.4 mm (fill) and 185.6 / 168.5 / 139.2 mm (meat)** at 15 / 19 / 23 in; inside rev C (205 / 190 mm). PROVISIONAL: 7 of 9 coarse cases did not converge | `huntkit/clothsim` scenarios `corrie_PR{15,19,23}`, table in §5a. Replaces the earlier estimate 189 / 179 / 170 and 181 / 174 / 166 mm |

### 5a. Cloth sim, rev B (depth ×0.894), run 2026-11-08

Box-body loader `huntkit/clothsim/corrie_bag.py` (pieces B-01, B-03R/L, B-02u, B-02door, B-02h, B-05, B-06 on the
unchanged frame interface; door zip modelled as a closed sewn seam; wings, pouch, swells and binding not modelled).
Outputs: `outputs/clothsim/corrie_PR{15,19,23}/` (h 40 mm), `outputs/clothsim/corrie_PR19_fine/` (h 25 mm, fill +
packed only, the render drape). Rev A is archived as `corrie_revA_PR*`. Rev C limits from HA-LS-1: 205 mm bag
(fill) cases, 190 mm meat cases.

| Run | Case | Converged | Closed vol L (cu in) | Contents CG y mm (rev C limit) | e_max % (piece) | max warp / weft % | max shear deg | worst seam N/mm (SF) |
|---|---|---|---|---|---|---|---|---|
| 15 in | fill 68 kg | NO (res 1.58 N) | 88.9 (5424) | 190.4 (205, margin 14.6) | 17.0 (B-03R) | 1.89 / 1.31 | 35.7 | 1.42 B-03L/B-05 (14.5) |
| 15 in | meat 38 kg | yes | 88.8 (5418) | 185.6 (190, margin **4.4**) | 14.3 (B-03R) | 1.74 / 1.23 | 27.2 | 1.68 B-03L/B-05 (12.2) |
| 15 in | packed 0.5 kPa | NO (res 1.42 N) | 92.8 (5662) | 169.3 (n/a) | 3.7 (B-06) | 1.18 / 0.42 | 5.6 | 0.30 door/B-02u (68) |
| 19 in | fill | NO (res 1.86 N) | 89.0 (5432) | 172.3 (205, margin 32.7) | 17.3 (B-03L) | 2.66 / 1.48 | 31.2 | 1.24 B-03L/B-05 (16.5) |
| 19 in | meat | NO (res 1.73 N) | 88.7 (5410) | 168.5 (190, margin 21.5) | 13.2 (B-03R) | 2.13 / 1.37 | 24.5 | 1.52 B-03L/B-05 (13.5) |
| 19 in | packed | NO (res 1.54 N) | 92.8 (5664) | 161.8 (n/a) | 4.2 (B-03R) | 1.36 / 0.45 | 6.6 | 0.32 door/B-02u (64) |
| 23 in | fill | NO (res 1.90 N) | 87.2 (5324) | 136.4 (205, margin 68.6) | 16.9 (B-03L) | 2.33 / 1.38 | 27.5 | 1.18 B-03L/B-05 (17.4) |
| 23 in | meat | NO (res 3.16 N) | 86.8 (5296) | 139.2 (190, margin 50.8) | 12.0 (B-05) | 2.21 / 1.38 | 22.9 | 1.42 B-03L/B-05 (14.4) |
| 23 in | packed | yes | 91.3 (5571) | 142.1 (n/a) | 5.6 (B-03R) | 1.56 / 0.59 | 7.9 | 0.42 door/B-02u (48) |
| 19 in fine | fill | NO (res 1.08 N) | 87.3 (5328) | 172.9 (205, margin 32.1) | 19.6 (B-02u) | 5.35 / 2.17 | 32.3 | **3.02 door/B-02u (6.8)** |
| 19 in fine | packed | NO (res 2.44 N) | 92.2 (5623) | 156.4 (n/a) | 11.2 (B-02u) | 3.17 / 1.07 | 38.2 | 1.81 door/B-02u (11.3) |

Volume: 87–89 L (5300–5430 cu in) loaded, 91–93 L (5570–5660 cu in) under the 0.5 kPa packed pressure, against
SPINE's 86–87 L in the same sim and the 85.2 L (5199 cu in) R-01 design number. The pouch (4.0 L) is not in any of these.

**How far to trust this (read before using any number above).**
1. **Non-convergence.** Only 2 of 11 cases converged (15 in meat, 23 in packed). The others stopped at residuals of
   1.1–3.2 N (stalled or max_iter). The CGs are therefore PROVISIONAL. They all pass rev C, and the margins are large
   except **15 in meat at 4.4 mm**, the one converged case. That case decides rev C sign-off for CORRIE: it passes, but
   4.4 mm is inside plausible model error. The 1 kg pouch does not eat the margin (by the §5 lever sum it moves y
   ~1 mm toward the frame), but it adds height. Hold rev C sign-off for CORRIE until the
   15 in fill / meat cases converge (smaller load steps, more iterations) and the pouch mass is in the sim.
2. **The 12–20 % "strain" is not fabric stretch.** e_max is the principal Green strain including in-plane shear. In
   the same cases warp and weft strain stay at 1.1–2.7 % (5.4 % fine mesh), but shear reaches 23–36° in the side
   gussets and floor, and the gussets show 72–96 % wrinkle area. So the gussets are over-length and buckled under the
   wings' footprint, and the shear sits at the B-03/B-05 corners, where the sim pinches the box corner into a few
   triangles. Tensions there are low (0.5–2.9 N/mm). Read it as "excess cloth, folded", not "about to tear". Two
   actions: (a) check whether the B-03 depth (d_bot 170 → d_nom 270) is longer than the filled shape needs (the box
   rounds out, so the gusset has spare width), and (b) re-mesh the floor corners finer before quoting a strain.
3. **Seam loads are not mesh-converged.** The door seam carries 0.89–0.96 N/mm (SF 21–23) at h 40 mm, but **3.02 N/mm
   (SF 6.8)** at h 25 mm. A 3.4× change between meshes means the peak is a stress concentration at the door's R 60
   corners that the mesh has not resolved. Use the fine value (SF 6.8) as the working number. It is still above the
   seam requirement, but the PT-7 door-zip proof test (§6.1) stays mandatory.
4. **Metadata.** Each `results.json` still names `patterns_v31.py build_body` as its pattern source (copied from the
   SPINE scenario template). The pieces listed in `mesh.pieces` are CORRIE's (B-02door, B-02u, B-02h), so the runs
   are CORRIE. The source tag is stale and needs fixing in `huntkit/clothsim` before release.
5. The sim closes the collar flat at the fill line. It does not model the roll, the clips, the wings or the
   pouch, so the side bulge under the wings is an upper bound.

**Rev C impact.** Every rev B CG is inside HA-LS-1 rev C (205 mm bag, 190 mm meat). The tightest case is 15 in meat
(185.6 mm, margin 4.4 mm), not 15 in fill as the estimate said. The estimate was close for 15 in (189 vs 190.4) and
pessimistic for 19 and 23 in: the box peels less than SPINE at the longer torsos. Sign-off is held per item 1 above.

**Render-vs-pattern conflict found while rendering (pattern-maker).** The chevron kick plate SH-01a, as drafted
(peak 140 mm at the aft centre, `accents_common`), reaches z 175 at the centre. The door zip runs at z 110 there,
so the plate would cross the zip and the door's R 60 corners. In the renders the plate stops 15 mm below the zip
line. The pattern needs the same change: either a 60 mm peak, or a top edge that follows the door's U, 15 mm below the
zip.

## 6. Risks and how they are handled

1. **The 1.26 m door zip is in hoop tension when the bag is stuffed (A1).** The wings take the side bulge, the roll-top
   takes height, IM1–IM3 carry the meat against B-01 (not against the door), and the zip ends in garages. There is no
   proof data on a #10 coil at this length. Proposed test **PT-7**: zip the door on a 68 kg sandbag fill, apply a 1.6 g
   walking load for 30 min, then 50 open/close cycles with gloves; accept with no tooth separation.
2. **Rain on the door.** It is a coil zip without a storm flap (quiet and simple), and the rain fly in the base pocket
   covers the aft face. The garages shield the two ends.
3. **Box look.** The owner chose it knowing it is the box family. The edgy look comes from the angular kick plate,
   the wing leading-edge bars and the U zip line.
4. **Guy geometry (D5) and head clearance R-28.** The bag face above the shoulders is the same setback face as SPINE,
   but the collar seam is 45 mm lower. R-28 must be re-run with the CORRIE profile, together with the cloth sim.

## 7. Pieces list (body group; frame-interface parts B-11, B-12, B-16–B-24 and the fly as released)

| Id | Piece | Qty | Material (record) | Notes |
|---|---|---:|---|---|
| B-01 | frame-side panel, flat, Z-fold setback (creases z 560 / 631.2) | 1 | `challenge_ultra_200` | 8 swell windows, 6 IM ports, B-17/B-18/B-23 tabs, B-20 ladders, hinge-eye notches, as released positions |
| B-03 | side gusset (wing root in its frame seam, strap loops in its aft seam) | 2 | `cordura_330d_nylon66` | 3-segment frame edge (setback), mirror pair |
| B-05 | bottom 272 × 190 | 1 | `cordura_500d_nylon66` | under-strap channels B-16, fly pocket F-02 as released |
| B-02u | U-surround (aft face below z 650, door cut-out, R 60 inner corners) | 1 | `cordura_330d_nylon66` | |
| B-02door | horseshoe door | 1 | `cordura_330d_nylon66` | |
| B-02h | hinge band (z 650 → collar seam) | 1 | `cordura_330d_nylon66` | B-22 tabs at x ±149, z 695 |
| B-06f / B-06 | roll-top collar, frame-side strip / rest (tapered tube, top 1171.6 mm) | 1 / 1 | `challenge_ultra_200` / `robic_100d_ripstop` | B-20 ladder tops on B-06f |
| B-07, B-07s | roll-top hem, 2 HDPE strips 0.8 × 20 | 1, 2 | `cordura_330d_nylon66`, `hdpe_sheet` | as released |
| B-13x | boxed fairlead swell 122 × 82 | 8 | `challenge_ultra_200` | straight seams, replaces the cone caps |
| M-01 | side compression wing 200 × 450, hemmed | 2 | `cordura_330d_nylon66` | 2 strap G-hooks each |
| L-21 / L-22 / L-23 | pouch top / base / boxing strip | 1 / 1 / 1 | `polyester_ht_630d_printable` / `cordura_330d_nylon66` ×2 | #8 zip in L-21 / L-23 aft seam |
| SH-01a, SH-01b | chevron kick plate, aft / side | 1, 2 | `polyester_ht_630d_printable` | wear line |
| SH-03 | roll-top hem band 1172 × 30 | 1 | same | |
| SH-06 | wing leading-edge bar 25 × 450 | 2 | same | |
| SH-07 | door zip garage 40 × 60 | 2 | same | |

**Hardware**
- Door: #10 coil × 1.26 m with 2 sliders.
- Pouch: #8 coil × 0.30 m with 1 slider.
- 3 cord pulls.
- G-hooks (HAUL family): 4 for the wings + 4 for the pouch.
- Ladder locks: 4.
- 25 mm webbing: about 1.9 m.

## 8. Next steps (pattern-maker and others)

1. **pattern-maker**
   - Draft CORRIE from `corrie.build(c)`: the pieces already exist as `huntkit.patterns` Pieces with seams and allowances (bound body seams 12 mm, zip 10 mm, flat-work 8 mm).
   - Add notches every 50 mm, B-01 crease lines, the wing-root line and the strap-loop marks at z 260 / 490 on the aft corner seam.
   - Mark the B-22 position (z 695) on B-02h and the B-20 ladder continuation onto B-06f.
   - Transfer all released frame-interface marks from v3.1 B-01 / B-01b / B-01u onto the one-piece B-01, at the same x and z.
   - Boxed swell: window 90 × 50 in B-01 and a corner-box line 16 mm.
   - Tiled PDF + DXF and a cut list in the release format.
2. **pack-designer / cloth sim**
   - Done 2026-11-08: box-body loader (`huntkit/clothsim/corrie_bag.py`), rev B runs PR15 / PR19 / PR23 + PR19 fine (§5a).
   - Open: converge the 15 in fill / meat cases; add the 1 kg pouch and the roll / clip loads; fix the stale pattern-source tag; finer floor-corner mesh.
   - Re-run R-28 on the CORRIE profile.
3. **structural-fea-engineer:** confirm rev C with the sim CGs; nothing new on the frame.
4. **materials-engineer:** a #10 coil 1.3 m door proof plan (PT-7); a rubber-sleeve pull record; a G-hook record (4 g is still an ASSUMPTION).
5. **manufacturing-engineer:** build-step order. Flat-work first (swells, tabs, ladders, wing roots, strap loops, garages, kick plates), then the door zip into the U-surround while flat, then box seams, collar, hem. The pouch is a separate sub-assembly.

## 9. Assumptions (new)

| Item | Assumption |
|---|---|
| Door geometry | Inset 45 mm, z 110–650, R 60 |
| Pouch | Size, 15 % corner loss, 1 kg loose-goods load |
| Wing straps | 2 per wing at z 260 / 490, 0.30 m each incl. loop |
| Hardware masses | G-hook 4 g; #8 slider 4 g; cord pull 1.5 g |
| Cloth-sim CG estimate | SPINE peel transferred to CORRIE |
| B-22 | z 695 tab; guy geometry acceptable pending the sim |
| Fill / corner shape | Filled-bag bulge ±5 % as R-01 |

## 10. Open questions for the owner

1. Should the door hinge at the top (opens upward; chosen, because gear cannot spill when the pack stands) or at the bottom (opens like a duffel when the pack lies down)?
2. Does the 4.0 L pouch (88 g, removable, all-G-hook) suit you, or do you want the bigger 4.9 L lid that converts to a hip pack?
3. Should W1 and W2 be merged into the wing straps? It would save about 70 g, but the wings would then also have to wrap meat in float mode.
4. Should the side gussets be in ULTRA 200 under the wings (−22 g, tougher, a little louder)? This is a fabric swap, so it stays on hold until you say.

## Screenshots

3D renders (2026-11-08), viz3d pipeline (same materials, owner camo texture, lighting, frame, hood, harness and
renderer as the accepted SPINE renders). The bag skin is the cloth-sim drape of the sewn flat pieces (PR19 fine,
**packed** case). Wings, roll, pouch, straps and the open door are placed geometry on that surface (not simulated).
Script: `designs/pack_5200/concepts/corrie_viz3d.py`; builder: `huntkit/viz3d/corrie.py`; viewer:
`outputs/pack3d_corrie/corrie_viewer.html`.

- `outputs/screens/20261108_corrie_1.png`: 3/4 rear (SPINE hero angle)
- `outputs/screens/20261108_corrie_2.png`: side profile on the mannequin
- `outputs/screens/20261108_corrie_3.png`: horseshoe door open, folded up, IM1–IM3 inside
- `outputs/screens/20261108_corrie_4.png`: tripod under the right wing
- `outputs/screens/20261108_corrie_5.png`: top pouch seated on the roll
- `outputs/screens/20261108_corrie_6.png`: float meat mode, 170 mm (6.7 in) loop
- `outputs/screens/20261108_corrie_7.png`: SPINE vs CORRIE, one fixed camera (SPINE rolled to 61 L, CORRIE packed 92 L)
- Copied to `docs/screens/`: `_1`, `_3`, `_4`, `_7`
- Superseded: `outputs/screens/20261107_corrie_*.png` (pyvista concept renders)
