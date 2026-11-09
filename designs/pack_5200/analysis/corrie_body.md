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
| **Loaded CG, cloth sim (rev B, 2026-11-08; superseded by rev B.1, section 11.4: all 9 converged)** | **190.4 / 172.3 / 136.4 mm (fill) and 185.6 / 168.5 / 139.2 mm (meat)** at 15 / 19 / 23 in; inside rev C (205 / 190 mm). PROVISIONAL: 7 of 9 coarse cases did not converge | `huntkit/clothsim` scenarios `corrie_PR{15,19,23}`, table in §5a. Replaces the earlier estimate 189 / 179 / 170 and 181 / 174 / 166 mm |

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
   - Done 2026-11-09 (section 11.4): all 9 converged, 1 kg pouch + 85 mm scope in, pattern-source tag fixed. Open: roll / clip loads, finer floor-corner mesh.
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

## 11. Rev B.1 (2026-11-09): pockets IMP-1..6, IMP-8 and hipbelt B integrated

Source: DECISIONS 2026-11-09 ("Owner delegated the open choices"). Concept level, the released SPINE files are not
changed. Code: `corrie.py` (section "Rev B.1": `bag_pockets()`, `hip_layout(size)`, `holster()`, `belt_b(size)`,
`weight_table(size)`, `integration()`), `corrie_loadout.py` (config `integrated:<size>`), clothsim scenarios
`corrie_PR{15,19,23}c` and the control `corrie_PR15s`, renders `corrie_b1_viz3d.py` + `huntkit/viz3d/corrie_b1.py`.
Tests: `tests/test_corrie_b1.py`. Every piece below is a `huntkit.patterns` Piece with finished (seam-line) dims, SA
8 mm (10 mm on B-09c), material from `data/materials/`; mass is cut area x record gsm plus the hardware listed.
Hours are the `bag_concepts.HOURS` beginner model (ASSUMPTION: rank, not plan). All seams are straight.

### 11.1 Pieces

| Id | Piece | Size mm (in) | Material (record) | Mass g | Attachment |
|---|---|---|---|---:|---|
| **IMP-1** scope sleeve, left wing (M-01L inside) | IMP1-a panel 330 x 430; IMP1-b facing 300 x 420; 3 mm XLPE 300 x 420; top shock cord 0.5 m + cord lock | 13.0 x 16.9 | `cordura_330d_nylon66`, `robic_100d_ripstop`, `xlpe_foam` (33 kg/m3) | **56.4** (fab 40.2) | Panel sewn to the wing's inside face on 2 straight vertical lines 160 mm apart (20 mm in from each wing edge) before the wing is hemmed; bottom excess folded into 2 x 85 mm box pleats caught in the wing hem; XLPE faces the bag. Section perimeter 330 + 160 = 490 mm against ~430 mm needed by an 85 mm angled spotter (110 x 150 section + 5 %); 372 mm scope in a 430 mm sleeve (z 165-595) |
| **IMP-2** hydration sleeve B-09c + 2 ports | tube 250 x 430 (cut 500 x 430, one side seam); 2 Hypalon port frames 40 x 60, slot 12 x 40 | 9.8 x 16.9 | `robic_100d_ripstop`, `hypalon_coated_nylon` | **34.6** (replaces SPINE B-09 10.9) | Hangs by a G-hook from a 25 mm tab bartacked on B-06f at x 0, z 985 (flat-work); bottom corners on 2 mm Dyneema loops to 2 webbing tabs on B-01 at z 560, x +/-100. Spans z 545-975: clear of IM3 (z 520 +/- 19), the IM ports are untouched. Ports in both B-03 gussets at z 700, 20 mm aft of the frame seam (R-19 both sides), above the wings (z 600), below the collar seam (z 736). ASSUMPTION: with a bladder in, the roll closes at or above z 990 |
| **IMP-3** 1 L bottle holster, belt B right wing | IMP3-a mesh tube 290 x 240; IMP3-b base 95 x 95; IMP3-c back 105 x 210; 2 wing tabs + 2 straps with G-hooks; 0.4 m shock cord + cord lock | | `power_mesh_nylon_spandex`, `cordura_330d_nylon66` | **37.4** | 2 x 25 mm tabs bartacked to the wing shell HB-W1 (shell only, flat-work) inside the HDPE zone, 20 mm from the top and bottom edges; the holster's 2 G-hooks hook them. The lower hook is the lower tie hipbelt_fit.md section 7 asks for (a couple, so the bottle cannot roll the wing down and out). Bottle axis behind the crest on every size (S -22, M -46, L -70, XL -84, XXL -108 mm); the soft back panel runs 30 mm (S) and 6 mm (M) past the crest: check at fit test HB-1 |
| **IMP-4** kill-kit / first-aid pocket, inside the door | IMP4-a face 200 x 280; IMP4-b bellows strip 760 x 60 (bottom + 2 sides); #5 zip 180 mm, slider, cord pull | 7.9 x 11.0, bellows 2.4 | `robic_100d_ripstop`, `coil_zipper_5` | **17.7** | Sewn flat to the door's inside face at z 350-630 before the door zip goes in. **Resized from the study's 300 x 340**: the door is only 246 mm wide at z 350 (304 at the hinge), so 200 mm leaves 23 mm a side to the zip line. Interior 192 x 272 x 58 mm (3.0 L): kill kit + first aid fit; elk game bags (55 mm) stay in the aft column above the sill (door class) |
| **IMP-5** hipbelt pockets, belt B | Face cut to the developed cone-cut wing outline 10 mm inside the binding, gusset 55 mm, #8 zip, per size below | | `cordura_330d_nylon66`, `coil_zipper_8` | 13.2-20.7 per pocket | Pocket sub-assembly sewn to HB-W1 in flat-work, edges caught in the wing binding; clear of the 30 mm root zone and the soft tip / 2:1 D-ring. Each face is 2 straight runs + 1 pivot at the crest-zone station (max bow 0.8 mm, under the 5 mm curve rule) |
| **IMP-6** phone pocket, left shoulder strap | IMP6-a power-mesh face 90 x 175; IMP6-b 330D back 90 x 175; 2 wrap straps 25 mm x 0.15 m + 2 G-hooks; 0.25 m shock cord + cord lock | 3.5 x 6.9 | `power_mesh_nylon_spandex`, `cordura_330d_nylon66` | **23.6** | Mesh over 330D, sewn on 3 sides, shock-cord top (no hook-and-loop); 2 wrap straps hook round the strap (moves to either strap). Interior 168 x 84 x 18 mm (ASSUMPTION: 18 mm mesh stretch): takes a 160 x 80 x 10 mm phone. The J-strap is 58-72 mm wide; the pocket overhangs ~13 mm a side |
| **IMP-8** bow cam cup, foot of the right wing | IMP8-a 130 x 160 folded (65 x 160 cup); IMP8-b Hypalon base 60 x 100 | | `cordura_330d_nylon66`, `hypalon_coated_nylon` | **10.6** | Back edge caught in the B-03R / B-05 bound seam at the aft corner, below the wing (z 35-150). Restores SPINE SH-04's function |

Shock cord has no record: the 2 mm Dyneema cord mass (2.5 g/m) is used as the proxy (ASSUMPTION). Beginner hours:
IMP-1 2.4, IMP-2 1.7, IMP-3 2.0, IMP-4 2.0, IMP-6 1.1, IMP-8 0.8 h (= 10.0 h), IMP-5 1.3-1.8 h per pocket (it replaces
today's HP-01/02, so roughly neutral), plus belt B +1.3 h (hipbelt_fit.md).

**IMP-5 per size** (`hip_layout`; wing room = wing - 30 root - 35 tip, hipbelt_fit.md section 7):

| Belt | Wing mm | Crest from root | Left pocket: length / interior mm / L (cu in) | Right wing | Phone (160) in a belt pocket |
|---|---:|---:|---|---|---|
| S 27-31 in | 157 | 105 | 72 / 57 x 103 x 50 / 0.29 (18) | holster only | no |
| M 30-34 | 197 | 129 | 112 / 97 x 102 x 50 / 0.49 (30) | holster only | no |
| L 33-37 | 232 | 153 | 147 / 132 x 102 x 50 / 0.67 (41) | holster only (52 mm left < 80 mm minimum) | no |
| XL 36-40 | 266 | 167 | 181 / 166 x 101 x 50 / 0.84 (51) | holster + mini pocket 66 mm (51 x 90 x 50, 0.23 L) | **yes** |
| XXL 39-44 | 304 | 191 | 219 / 204 x 101 x 50 / 1.03 (63) | holster + pocket 104 mm (89 x 92 x 50, 0.41 L) | **yes** |

This confirms the decision's premise: the phone fits a belt pocket only on XL/XXL, hence IMP-6. DECISION (this
revision): the holster takes the right wing's stiffened zone on every size, so the right pocket exists only where >= 80
mm is left (XL, XXL). The study's IMP-5 "200/160 x 130" face is replaced by these per-size faces.

### 11.2 Hipbelt B on CORRIE (concept) and the weight table

Belt body per size (`belt_b`: `hipbelt_concepts.belt_bom` + the materials-engineer records of 2026-11-09, commit
64e431c: D-ring `d_ring_25mm_aluminium` 6 g x 2 replaces 5 g x 2; grip print `silicone_grip_print` 46 g/m2 x the printed
face (0.09-0.14 m2) replaces 5 g, booked but **not credited** in friction until HB-2; 2:1 lock legs 2 x
`ladder_lock_25mm_heavy` 7 g added):

| | S | M | L | XL | XXL |
|---|---:|---:|---:|---:|---:|
| belt_bom B (hipbelt_fit.md) g | 183.3 | 209.2 | 231.5 | 253.4 | 277.5 |
| **Belt B body on CORRIE** g (oz) | **198.6** (7.0) | **225.1** (7.9) | **247.9** (8.7) | **270.3** (9.5) | **294.9** (10.4) |
| vs today's belt body (165.0 g, size M) | +33.6 | +60.1 | +82.9 | +105.3 | +129.9 |

Load path (structural-fea-engineer, `hipbelt_structural.md`, landed 2026-11-09): the flat PA66 centre plate FAILS
(C2 SF/req 0.61, fatigue 0.20); the recommended curved 6061-T6 1.5 mm bow-tie + hub + latch, root/tip doublers,
thrust washer is **110.4 g** (size M) against the 45 g plate + latch still booked: **+65.4 g** here (their "+59 g" is
against 51 g, which counted the 6 g cant snap that `belt_bom` already deletes; same net). Their ~10 g ASSUMPTION
for the frame-side pad interface is replaced by the designed pad seat, 60.9 g (11.2a). Also from that note and used here: HDPE floats (no fastener), stitched-ear wing
joint, and the **2:1 routing fix** (anchor on the buckle half -> round the tip D-ring -> back through the lock on the
buckle half -> tail; the render follows it). Their open flag on the 2 x M5 inserts (SF/req 0.995-1.14) stays theirs.


### 11.2a Lumbar pad seat on the frame face and the belt-B load path (DECISIONS 2026-11-09, structural items 1-6)

The lumbar push (413 N at 15 in, 1 g) must go pad -> frame lumbar pan, never through the centre plate or the Ti pivot
(the frame FE already reacts it on the `lumbar_pad` springs P11..P33). `corrie.pad_seat()`:

| Part | Size mm | Record | g |
|---|---|---|---:|
| 2 standoff rails, bonded to the pan face, either side of a 70 mm vertical channel | 55 x 140 x 6 | `eva_foam_45c` | 10.2 |
| Pad backer (the pad's dual-density stack + wedge sit on it; it bridges the channel) | 190 x 150 x 1.0 | `hdpe_sheet` | 27.2 |
| Slip liner on the backer's channel face | 70 x 140 x 0.5 | `hdpe_sheet` | 4.7 |
| Top sleeve: slips over the pan's 25 mm top return flange (z 190) | 190 x 40 | `hypalon_coated_nylon` | 7.6 |
| Bottom strap round the pan's lower edge (z 50) + ladder lock | 25 x 400 | webbing + `ladder_lock_25mm` | 11.2 |
| **Seat total** | | | **60.9** |

Stack from the body: spacer face, EVA 30C 6 + EVA 45C 6 + terraced wedge (belt B), HDPE backer, rails, frame pan
(zone y -48..-27). The 6061-T6 bow-tie (1.5 mm, 210 wide, 60 mm spine, 140 mm ears, rolled R 420 / 14.6 deg end slope,
PA66 hub on the 10 mm Ti pin, POM thrust washer; 94.6 g) runs in the channel: 10 mm side play, 4.5 mm depth play
(>= 4 mm asked), so the belt rolls +/-8 deg on the pin (9.5 deg of side clearance at the spine edge) while the pad stays
still. The pad seat fits inside the pan (250 x 140 mm). No hook-and-loop, nothing fastened into the printed body.
Wing joint: stitched ear (plate ear inside the wing root, 1000D doubler each face, 2 rows of 22 x 2 mm holes, hand
saddle-stitched tex 135), HDPE floats. 2:1 routing corrected (hipbelt_fit.md 4.1 updated). Ti mount to 4 x M5
heat-set inserts (frame owner; no mass change booked here).

**CORRIE B.1 weight table, belt M** (`corrie.weight_table("M")`):

| Item | g | Source |
|---|---:|---|
| SPINE released pack (belt M) | 3495.6 | geometry.yaml weight.total_g |
| CORRIE body group (rev B, 552.0 g) vs SPINE body group (333.2 g) | +218.8 | `corrie.build()`, same metric |
| SPINE floating side pockets: CORRIE has none (the wings replace them) | -60.3 | geometry.yaml row. **Correction:** the rev B total carried them |
| SPINE B-09 hydration sleeve (replaced by IMP-2) | -10.9 | panels.yaml |
| IMP-2 / IMP-1 / IMP-4 / IMP-6 / IMP-8 | +34.6 / +56.4 / +17.7 / +23.6 / +10.6 | `bag_pockets()` |
| Hipbelt body: today -> belt B (M) | +60.1 | above |
| Hipbelt pockets: HP-01/02 + zip (24.7 g) -> IMP-5 left pocket (M) | -9.5 | `hip_layout("M")` |
| IMP-3 bottle holster | +37.4 | `holster()` |
| Belt B load path: 6061-T6 bow-tie + PA66 hub + latch, root/tip 1000D doublers, ear thread, POM washer (110.4 g) replacing the 45 g PA66 plate + latch | +65.4 | hipbelt_structural.md section 0; = their +59.4 g vs 51 g booked, because the 6 g cant snap is already deleted in the belt B row |
| Lumbar pad seat on the frame face (`pad_seat()`, 11.2a) | +60.9 | records; replaces the structural note's ~10 g ASSUMPTION |
| **CORRIE B.1 total, belt M** | **4000.4 g (8.82 lb)** | |

| Belt size | S | M | L | XL | XXL |
|---|---:|---:|---:|---:|---:|
| Pack total g | 3971.9 | **4000.4** | 4025.0 | 4061.5 | 4090.1 |
| lb | 8.76 | **8.82** | 8.87 | 8.95 | 9.02 |
| vs SPINE 3496 g (7.71 lb) | +476 | **+505** | +529 | +566 | +595 |
| vs the ~6.6 lb target (2994 g) | +978 | **+1006** | +1031 | +1068 | +1096 |

Notes. The rev B "3725 g" in section 4 was the rev A body (563.0 g); rev B's own body is 552.0 g, so rev B was
3714 g, and 3654 g without the side pockets it never had. The load-path row is size M for every size (ASSUMPTION).
The weight is accepted for now (DECISIONS 2026-11-09); the whole-pack weight pass follows this integration.
Biggest levers for it: pad seat (61 g: an 0.8 mm backer saves 5 g; a backer that is also the belt's lumbar shell stiffener would save more), centre plate (95 g; 7075 1.2 mm candidate -12.5 g, hipbelt_structural.md section 6), body
group (+219 g vs SPINE), scope sleeve (56 g), held fabric swaps.

### 11.3 Loadouts re-run (`corrie_loadout.py`, config `integrated:<size>`, all loadouts, all belt sizes)

Changes to the model: the zones are the B.1 pieces above (real interiors, belt pocket per size, holster, strap pocket);
two 1 L bottles are carried as two units; on a pack-out the bladder stays in its hung sleeve and the meat packs round it
(overflow aft); the sim peel now comes from the converged rev B.1 runs (section 11.4).

**Hourly / constant items that are NOT reachable with the pack on** (requirement: class <= 1):

| Loadout | S | M | L | XL | XXL |
|---|---|---|---|---|---|
| Day hunt | snacks | snacks | snacks | **0** | **0** |
| 6-day elk, rifle | snacks | snacks | snacks | **0** | **0** |
| 6-day elk, archery | snacks | snacks | snacks | **0** | **0** |
| 8-day sheep | GPS, 2nd bottle, snacks | GPS, 2nd bottle, snacks | GPS, 2nd bottle, snacks | 2nd bottle, snacks | 2nd bottle |

Rev B (no pockets): 4-6 misses per loadout (loadout_study.md section 4). Now phone (IMP-6), bladder (IMP-2), bottle
(IMP-3) and inReach (strap clip) are reachable on every size and loadout. **Residual misses, confirmed:**
- **Snacks on S-L** (150 x 100 x 35 mm, 0.5 L): longer than the S/M/L pocket interior (57 / 97 / 132 mm) and more
  volume than S/M hold. User-guide mitigation (not modelled): carry the day's snacks as 2 x 0.25 L stacks <= 95 mm
  long; one fits the M/L pocket (97 / 132 x 102 x 50). It does not fit S.
- **Sheep GPS on S-L** (160 mm): same pocket length limit; on XL the GPS takes the pocket and the snacks miss.
- **Sheep 2nd bottle**: one holster; the second bottle rides in the bag (as the study predicted).
- Pack-out days (meat in): glassing/weather layers above the door (puffy, mid layer, rain pants, pad) are class 5. Not
  hourly; expected with 45 kg of meat in.

**Bag-load CG** (belt M; hip, chest and hand items excluded as in rev C; +peel from the converged sims):

| Case | Bag load kg | Main bag used / free L | CG y geo mm | **+15 in peel (limit)** | +19 in | CG z | Float? |
|---|---:|---|---:|---:|---:|---:|---|
| Day | 7.7 | 12.2 / 75.7 | 112 | **168 (205)** | 150 | 567 | no |
| Day + 40 kg meat | 7.1 + 40 | 9.9 / 33.4 | 83 | **136 (190)** | 119 | 491 | no |
| 6-day elk rifle | 16.2 | 44.7 / 43.2 | 105 | **161 (205)** | 143 | 470 | no |
| Elk + 45 kg meat | 11.3 + 45 | 33.2 / 4.6 | 99 | **152 (190)** | 135 | 473 | no |
| Elk archery | 14.8 | 44.7 / 43.2 | 104 | **161 (205)** | 142 | 478 | no |
| 8-day sheep | 18.6 | 53.6 / 34.2 | 117 | **173 (205)** | 154 | 426 | no |
| Sheep + 30 kg meat | 13.4 + 30 | 41.5 / 13.0 | 97 | **150 (190)** | 133 | 434 | no |

All inside HA-LS-1 rev C (y 205 / 190, z <= 590). Tightest: sheep 173 mm (margin 32), elk pack-out 152 (margin 38).
The hung bladder raises the day-load CG z to 567 (limit 590). The pockets move the gear CG by < 10 mm against rev B.
Lateral x: day +26 mm right (tripod, head, poles and rain jacket on the right wing against a 709 g spotter on the left;
the holster bottle is on the belt and is not in the bag CG), elk/sheep within +/-5 mm.

### 11.4 Cloth sims at 15 / 19 / 23 in: converged (rev C sign-off gate)

**Why rev B did not converge.** Diagnosed on 15 in fill (scratch diagnosis, then confirmed in the runs). The residual
sits on 3-8 B-01 nodes at the lower spreader / frame plate edges (x -26..+13, y 15, z 87-156). The Levenberg-Marquardt
damping climbs to 1e4 and the residual alternates 1.65 / 2.48 N. A linearised-contact polish cycles between the same
two states (true residual 2.3 <-> 3.4 N). Cause: the trilinear gap field (`GapField`) has a gradient kink along plate
edges, and a node on that crease has no smooth equilibrium. It is neither the step size (the 50 mm step cap is
never active at the end), the load ramp (every ramp stage stalls the same way), nor damping.

**Fix (additive in `huntkit/clothsim`; defaults leave SPINE runs unchanged):**
1. `GapField.smoothed(sigma)`: Gaussian rounding of the sampled gap. A flat face is unchanged (a linear field is
   invariant under a symmetric blur; tested). Scenario key `contact.smooth_mm` (default 0).
2. Rounding continuation in `run_case`: ramp on the 6 mm rounded field, then `contact.smooth_continuation`
   [4, 3, 2, 1, 0] mm, each stage from the last, straps not re-cinched. If a stage does not converge, the last
   converged stage is kept and reported (`contact_rounding_mm` in results.json).
3. `case.external`: dead loads for the 1 kg pouch (1.088 kg with the pouch, on the collar closure nodes) and the 85 mm
   spotter in the left-wing sleeve (1.955 kg, half on the wing-root seam B-03L | B-01, half on the strap loops in
   B-03L | B-02u, z 165-595, ASSUMPTION 50 / 50). They ramp with the fill. A mass-weighted CG including them is reported
   (`cg_with_external_mm`).
4. The stale pattern-source tag in results.json now names `concepts/corrie.py` for CORRIE runs.

Bias of the rounding, measured. 15 in, continuation 6 -> 0 mm: fill CG y 188.5 / 189.8 / 190.0 / 190.7 / 191.6 /
192.3 mm at 6 / 4 / 3 / 2 / 1 / 0 mm (scratch study; it re-cinched at each step, which over-tightens, so it
over-states the trend). Rounding lowers the CG by about 2-4 mm, so a case reported at a rounding > 0 must be read with
+4 mm. The table below says which rounding each case converged at.

| Run | Case | Converged (rounding of the reported stage) | Final residual N | Closed vol L (cu in) | Contents CG y mm | CG y incl. pouch + scope mm (rev C limit, margin) | CG z mm | e_max % (piece) | warp / weft % | worst seam N/mm (SF) |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 in | packed | yes (3.0 mm) | 0.12 | 92.7 (5657) | 169.5 | n/a | 540 | 3.7 (B-06) | 1.20 / 0.42 | 0.23 B-02h/B-06 (49.2) |
| 15 in | fill | yes (6.0 mm) | 0.27 | 88.1 (5374) | 190.9 | 191.3 (205, margin 13.7) | 497 | 17.4 (B-05) | 1.84 / 1.36 | 1.50 B-03L/B-05 (13.6) |
| 15 in | meat | yes (6.0 mm) | 0.22 | 88.3 (5385) | 184.0 | 184.4 (190, margin 5.6) | 508 | 15.9 (B-05) | 1.80 / 1.18 | 1.99 B-03L/B-05 (10.3) |
| 19 in | packed | yes (3.0 mm) | 0.48 | 92.9 (5668) | 158.5 | n/a | 546 | 4.3 (B-03R) | 1.33 / 0.45 | 0.32 door/B-02u (63.9) |
| 19 in | fill | yes (3.0 mm) | 0.50 | 88.4 (5396) | 172.0 | 172.4 (205, margin 32.6) | 509 | 18.3 (B-03L) | 2.62 / 1.57 | 1.36 B-03L/B-05 (15.1) |
| 19 in | meat | yes (3.0 mm) | 0.46 | 88.0 (5372) | 166.8 | 167.2 (190, margin 22.8) | 516 | 15.2 (B-05) | 2.09 / 1.38 | 1.83 B-03L/B-05 (11.2) |
| 23 in | packed | yes (3.0 mm) | 0.50 | 91.2 (5567) | 140.0 | n/a | 550 | 5.8 (B-03R) | 1.48 / 0.45 | 0.33 door/B-02u (62.0) |
| 23 in | fill | yes (6.0 mm) | 0.46 | 87.0 (5310) | 130.8 | 131.2 (205, margin 73.8) | 517 | 16.9 (B-03L) | 2.37 / 1.30 | 1.14 B-03L/B-05 (18.0) |
| 23 in | meat | yes (4.0 mm) | 0.44 | 86.6 (5285) | 133.9 | 134.1 (190, margin 55.9) | 524 | 13.8 (B-05) | 1.97 / 1.37 | 1.59 B-03L/B-05 (12.8) |
| 15 in control (rounding only, no pouch/scope) | packed | yes (3.0 mm) | 0.12 | 92.7 (5657) | 169.5 | n/a | 540 | 3.7 (B-06) | 1.20 / 0.42 | 0.23 B-02h/B-06 (49.2) |
| 15 in control (rounding only, no pouch/scope) | fill | yes (6.0 mm) | 0.43 | 88.9 (5427) | 188.4 | 188.4 (205, margin 16.6) | 499 | 19.0 (B-05) | 1.88 / 1.31 | 1.55 B-03L/B-05 (13.2) |
| 15 in control (rounding only, no pouch/scope) | meat | yes (6.0 mm) | 0.17 | 89.0 (5430) | 180.7 | 180.7 (190, margin 9.3) | 509 | 15.5 (B-05) | 1.64 / 1.28 | 1.89 B-03L/B-05 (10.8) |

Runs: `outputs/clothsim/corrie_PR{15,19,23}c/` (h 40 mm, the rev B mesh) and the control `corrie_PR15s`. Sweep (15 in,
gas only): 90.8 / 92.2 / 93.2 / 94.4 L at 0.25 / 0.5 / 1 / 2 kPa. **All 9 cases converged** (residual < 0.5 N),
against 2 of 9 in rev B. Each case is reported at the lowest contact rounding that converged (3-6 mm); stepping
further toward 0 mm stalled again on the same plate-edge crease. Volume: 87.0-88.4 L (5310-5396 cu in) loaded,
91.2-92.9 L (5567-5668 cu in) packed, against the 85.2 L (5199 cu in) R-01 design number; the 4.0 L pouch is extra.
Pouch + scope effect (15c vs the 15s control): fill CG y +2.9 mm, meat +3.7 mm, volume -0.8 / -0.7 L. Strain read
as in 5a item 2: warp / weft <= 2.6 %, the 13-19 % e_max is shear in the buckled gussets and floor corners.

**Rev C read-out.** **Pass on every case, marginal at 15 in meat.**

| Torso | Fill CG y, mass-weighted with pouch + scope (limit 205) | + rounding bias <= 4 mm | Meat CG y (limit 190) | + bias |
|---|---|---|---|---|
| 15 in | 191.3 (margin 13.7) | <= 195.3 (margin >= 9.7) | **184.4 (margin 5.6)** | **<= 188.4 (margin >= 1.6)** |
| 19 in | 172.4 (32.6) | <= 176.4 | 167.2 (22.8) | <= 171.2 |
| 23 in | 131.2 (73.8) | <= 135.2 | 134.1 (55.9) | <= 138.1 |

CG z 497-524 mm (rev C basis z 550, limit 590). The rev C sign-off gate (converged 15 in fill and meat with the
pouch) is met. Recommendation to the owner / structural-fea-engineer: sign off rev C for CORRIE, recording that the 15 in
meat case has 1.6-5.6 mm of margin. That is inside model error, so the prototype load test should measure the
loaded-bag CG at 15 in with 30 kg on IM1-IM3 (a plumb-line / two-scale CG check). The lever that buys margin is the
pouch: strapped to the frame-side hem as designed instead of riding the tipped collar closure, it is worth ~4 mm.

Not modelled (unchanged from 5a): the roll itself (the collar closes flat at the fill line, roll clips off), the wings'
squeeze, the tripod on the right wing, swells, the hydration sleeve. Sensitivity `corrie_PR15cr` (roll clips cinched):
CG within 0.5 mm, volume +0.4 L. The pouch is carried on the collar closure. In the sim that closure tips aft (y ~330,
z ~890) on every fill case, with or without the pouch, so the pouch's lever is an upper bound: strapped to the
frame-side hem as designed (y ~76) it would bring the CG ~4 mm forward.

### 11.5 Access table (6-day elk rifle, belt M; class 0 body, 1 pack on, 3 pack off outside, 4 door, 5 roll-top)

| Item | Freq | Rev B zone (class) | B.1 zone (class) | OK |
|---|---|---|---|---|
| Phone 160 mm | hourly | top pouch (3) | **IMP-6 strap pocket (1)** | yes |
| inReach | hourly | strap clip (1) | strap clip (1) | yes |
| 2 L bladder | hourly | bag, frame half (5) | **IMP-2 sleeve, hose to the strap (1)** | yes |
| 1 L bottle | hourly | wing / bag (3-5) | **IMP-3 holster (1)** | yes |
| Snacks | hourly | top pouch (3) | top pouch (3) on S-L; left pocket (1) on XL/XXL | **S-L no** |
| 65 mm spotter | glassing | under the left wing, loose (3) | **IMP-1 sleeve (3)** | yes |
| Tripod, head, rain jacket, poles | glassing / weather | right wing (3) | right wing (3) | yes |
| Kill kit, first aid | kill / emergency | aft column, under other gear (4-5) | **IMP-4 door pocket (4)** | yes |
| Game bags | kill | aft column low (4) | aft column low (4) | yes |
| Puffy, mid layer | glassing | aft column high (4) | aft column high (4) | yes |

### 11.6 Renders (Blender Cycles, `huntkit/viz3d/cycles_render.py`)

Model `huntkit/viz3d/corrie_b1.py` (GLB `outputs/pack3d_corrie_b1/corrie_b1.glb`, viewer next to it). Belt B is a
real swept, padded body on the mannequin's own pelvis section: size L for the 34.6 in mannequin, lumbar 190 mm shell,
wings with the B height profile (150 / 145 at 45 % / 105 mm), leaning in by the 5 deg cone, 30 -> 11 mm thick,
bound edges, spacer face, quilting lines, 2:1 webbing to D-rings, heavy ladder locks, 50 mm buckle and stabilizers. The
mannequin is in a relaxed A-pose for these renders, so the forearms do not hide the hips. The spotter is drawn 70 mm
out of its sleeve to show it. New option `cycles_render.py --shots <json>` (custom named cameras, additive).

| # | File | View |
|---|---|---|
| 1 | `outputs/screens/20261109_corrie_1.png` | hero 3/4 rear on the wearer: belt B, scope sleeve left, tripod right |
| 2 | `outputs/screens/20261109_corrie_2.png` | side, wearer's right: hose port and hose to the bite valve, bottle holster |
| 3 | `outputs/screens/20261109_corrie_3.png` | door open: IMP-4 kill-kit pocket with blaze pull, IM1-IM3 behind |
| 4 | `outputs/screens/20261109_corrie_4.png` | rear: IMP-1 sleeve with the 85 mm spotter (left), tripod (right) |
| 5 | `outputs/screens/20261109_corrie_5.png` | belt B front 3/4: cone-cut padded wings, 2:1 pulls, D-rings, holster + bottle, left pocket |
| 6 | `outputs/screens/20261109_corrie_6.png` | left shoulder strap: IMP-6 phone pocket; hose on the right strap |
| 7 | `outputs/screens/20261109_corrie_7.png` | cutaway from above, bag and straps off: lumbar pad seat (HDPE backer, sleeve) on the frame pan |

Copied to `docs/screens/`: `_1`, `_3`, `_4`, `_5`. Superseded: `outputs/screens/20261108_cycles_*.png`,
`20261108_hipbelt_6/7.png` (block belt).

### 11.7 Open after B.1

1. Rev C sign-off: see 11.4.
2. pattern-maker: draft the B.1 pieces (all straight); IMP-5 faces per size from `hip_layout`.
3. materials-engineer: a shock-cord record (3 mm) and a power-mesh stretch value for the IMP-6 18 mm depth.
4. Weight pass (DECISIONS): the pack is 8.82 lb (4000 g) at belt M, 2.2 lb (1006 g) over the target.
5. Snacks / GPS on S-L: user-guide packing rule, or a second strap pocket (+24 g) if the owner wants zero misses.
6. structural-fea-engineer flags carried: the M5 insert record / test, the centre-plate pad-on-the-frame interface.

## 12. Rev B.2 (2026-11-09): the owner-approved weight cuts

Source: DECISIONS 2026-11-09 "Owner: 'Yes' to the weight-pass recommendation" and "Package C adopted where it passes".
Item definitions and grams: `analysis/weight_pass_corrie.md` (generated by `weight_pass_corrie.py`, which is still
computed on B.1 so every cut keeps its B.1 baseline). Code: `corrie.py` `SPECS` / `SPEC`: **B.2 is the default**;
`CORRIE_SPEC=B.1` (env), `spec="B.1"` (functions) or `python corrie.py --spec B.1` reproduces B.1. Masses use the
records as of commit ec18d6d (Robic 100D 90 -> 125 g/m2, ULTRA 200 125 -> 133 g/m2, `shock_cord_3mm` 6 g/m in place of
the 2 mm Dyneema proxy), so **B.1 itself is now 4042.3 g at belt M**, not the 4000.4 g first published.
Tests: `tests/test_corrie_b2.py` (+ B.1 pinned in `test_corrie_b1.py`, `test_weight_pass_corrie.py`).

### 12.1 What changed (applied in `corrie.py`)

| Id | Change in B.2 | Where in code | g at belt M |
|---|---|---|---:|
| A-1 | Belt B face ships unprinted until HB-2 (belt_bom's 5 g grip line out) | `belt_b()` | -4.9 |
| A-2 | Haul-wrap tails W1-W3 250 -> 150 mm (haul path unchanged) | `b2_rows()` | -5.4 |
| B-1 | No grosgrain on the 7.28 m of body seams: 301 seam + 2nd row 6 mm in, trim, hot-knife sear (seams tagged `seared`) | `build()` | 0 booked (-36.4 real) |
| B-2 | SH-03 roll-hem camo band deleted, hem B-07 stays 330D body solid (chosen over S-12) | `build()` | -15.8 |
| B-3/4/5 | Pouch 280 x 190 x 60 mm (2.7 L): top 330D solid, base + boxing 100D Robic, zip L-20 mm, camo pull tab SH-08 25 x 60 folded | `build()` | -23.6 |
| B-6 | IMP-1 scope sleeve panel 330D -> 100D Robic | `bag_pockets()` | -8.5 |
| B-7 | IMP-6 phone pocket bartacked to the left J-strap, no wrap straps / G-hooks | `bag_pockets()` | -13.4 |
| B-10 | Hypalon -> laser-cut TPU-coated 840D on B-12 strap ports, IMP-2 hose-port frames, IMP-8 cam-cup base (quieter part lost: TPU edge can tick) | `bag_pockets()`, `b2_rows()` | -12.8 |
| G-1 | Binding on the body seams left bound after B-1: 0 m | `b2_rows()` | 0.0 |
| G-2 | Rain fly re-cut for the box shell (0.718 vs SPINE 0.630 m2 outer shell) | `b2_rows()` | +6.5 |

Not applied: B-8 / B-9 (held fabric swaps; the materials-engineer now rates O-3 "proceed", so B-9 could come back
for about -9 g or more (the 70D record is new) if the owner releases it), all of package C (below), the S-items. If the B-1 wash swatch fails, the
binding comes back: G-1 = +36.4 g (7.28 m x 5 g/m, ASSUMPTION), or only on the ULTRA 200 seams if only they fray.

### 12.2 Mass, belt S-XXL (`corrie.weight_table(size)`)

| Belt | S | M | L | XL | XXL |
|---|---:|---:|---:|---:|---:|
| B.1, current records g | 4013.8 | 4042.3 | 4066.9 | 4103.4 | 4132.0 |
| **B.2 g** | **3936.6** | **3964.5** | **3988.6** | **4024.6** | **4052.7** |
| **B.2 lb** | **8.68** | **8.74** | **8.79** | **8.87** | **8.93** |
| B.2 vs B.1 g | -77.2 | -77.8 | -78.3 | -78.8 | -79.3 |
| **B.2 + C (gated) g** | 3882.5 | **3910.4** | 3934.5 | 3970.5 | 3998.6 |
| B.2 + C lb | 8.56 | **8.62** | 8.67 | 8.75 | 8.82 |
| vs the ~3800 g (8.4 lb) publish number | +83 | +110 | +135 | +171 | +199 |

**B.2 + C row** (`corrie.package_c_rows()`, from `weight_c_structural_results.json`, size-independent): C-1+C-2+C-3
(7075-T6 1.2 mm bow-tie cold slip-rolled to the R 417 template, D28 hub, 2 x D31 holes, SF/req 1.08) -25.0 g; C-9
(printed body, inward offset <= 1.75 mm, fatigue 1.020) -45.6 g; C-4 failed -> pad backer CFRP quasi-iso 0.8 mm
+8.1 g; C-7 failed -> yoke plate CFRP 1.8 mm +8.5 g. **Net -54.0 g.** Still pending and not counted: C-5 (-7.5 g,
PT-3 strip test on ULTRA 200), C-6 (-6.2 g, slot pull test), C-8 (-7.2 g, rail fit on 3 backs): -20.9 g if all pass.

**Against the owner's ~3.8 kg (8.4 lb):** B.2 + C is 3910 g (8.62 lb) at belt M, **110 g over**. Most of the miss is
records, not design: the Robic and ULTRA corrections plus the real shock cord add +41.9 g to the same B.1 pack, and the
C-4 / C-7 fixes add +16.6 g. With C-5 / C-6 / C-8 passing and B-9 released it would be about 3880 g; 3800 g at belt M
needs the lighter-frame study (frame_light2) or a T-item from the weight pass (section 5 there).

### 12.3 Loadout, CG, volume (`corrie_loadout.py` re-run, all loadouts x belts S-XXL)

The body geometry is unchanged (rev B box, flat-panel 75.9 L, collar seam z 736.3, uniform-fill CG unchanged); the
converged cloth sims (11.4) stand: no shell geometry changed, so they were not re-run. What moves is the pouch:
2.7 L instead of 4.0 L (interior 260 x 175 x 55 mm still takes the 150 x 100 x 35 snack stack and the 160 mm GPS),
and it rides 5 mm lower (`POUCH_ABOVE_TOP` 75 -> 70 mm).

| Loadout | Access vs B.1 | Bag CG y + 15 in peel (limit) | CG z | Main bag used |
|---|---|---|---|---|
| Day hunt, S-XXL | toilet kit (daily) leaves the pouch. The model then parks it in the door pocket and the kill kit falls to the bag floor (class 5): a packing-order artifact. Packed by the IMP-4 rule (kill kit owns the door pocket, toilet kit to the bag top) **no new miss** | 168.4 -> 170.4 (205) | 567 -> 550 | +0.6 L |
| 6-day elk (rifle, archery), S-XXL | **unchanged** | 161.3 -> 161.0 (205) | -3 mm | same |
| Elk / day pack-outs (40-45 kg) | unchanged | <= +0.4 mm (190) | | +0.7 L |
| 8-day sheep, S-XL | the rain jacket (1.8 L) leaves the pouch for the aft column top and pushes the **trekking poles above the door hinge (class 5): a new glassing miss** | 172.8 -> 174.3 (205) | about -1 mm | +1.5 L |
| 8-day sheep, XXL | beanie / fire kit trade places with the pouch (no new class failure in the dry case) | 172.7 -> 174.5 | | +0.6 L |
| Sheep pack-out (30 kg) | rain jacket class 5 (was beanie) | 150.3 -> 150.7 (190) | | +1.5 L |

All cases stay inside HA-LS-1 rev C (tightest: sheep 174.5 mm, margin 30.5). The B-5 cost is real but small: on the
8-day sheep load the poles go in the bag at glassing stops. User-guide rule: on sheep loads the rain jacket rides under
the right-wing straps on top of the tripod, or the owner reverts B-5 alone (+11 g, 4.0 L pouch).

### 12.4 Prototype test list (CORRIE, all gates in one place)

| Test | What | Pass | Gates | New in B.2 |
|---|---|---|---|---|
| **WP-1** wash-swatch fray | Each body seam pairing as built without binding (330D|330D, 330D|ULTRA 200, 500D|330D, 100D|ULTRA collar), 301 + 2nd row 6 mm in, trimmed, hot-knife seared; 3 machine-wash cycles (R-12) | no fray past row 2 | B-1 | **yes** |
| PT-3 (rebuilt) | HE eye on B-18 + B-01 + B-05 seam swatch, **built without binding as sewn in B.2** | 5 of 5 hold 1530 N | B-1, C-5 (also on ULTRA 200) | rebuild |
| **WP-2** C-6 slot pull | B-11 lash tab in laser-cut TPU 840D, 25 x 5 slot, pulled in the slot's working direction (the strap's pull on a bow riser / muzzle keeper; slot direction to be confirmed on the tab drawing, materials-engineer flag); 5 samples | 5 of 5 hold the 450 N buckle class, no slot tear | C-6 | **yes** |
| **WP-3** gloved tail | 150 mm tail on W1-W3 ladder locks, winter gloves, loaded and slack | release and re-tension in one grab | A-2 | **yes** |
| **WP-4** fly fit | re-cut F-01 over the packed box shell, wings closed, pouch on | covers the shell to the B-05 seam, no gap at the hinge band | G-2 | **yes** |
| **WP-5** trim tick | TPU 840D B-12 ports / hose-port frames / cam-cup base against webbing, walking test | no audible tick at 1 m | B-10 | **yes** |
| HB-2 | grip-face friction | as hipbelt_fit.md | grip print comes back only if it passes (A-1) | |
| HB-5 | 7075-T6 1.2 bow-tie with 2 x D31 holes and the D28 hub: proof + 1e5 cycles; template check of the end slope 14.6 +/- 2 deg | weight_c_structural.md | C-1, C-2, C-3 | **yes (7075)** |
| Pad-seat sag | CFRP 0.8 mm backer on the rails over a pan offcut, 413 N on a 150 x 190 foam block, 8 h | no contact with the bow-tie spine | C-4 correction | **yes** |
| T1(c) | hipbelt-off 225 lb hang, dial on the 1.8 mm yoke tip | load_standard.md | C-7 correction | dial added |
| T5 | frame cycle test on the C-9 body | load_standard.md (fatigue governs at ~1.0) | C-9 | C-9 body |
| C-8 rail fit | 130 / 70 rails on 3 backs | peak <= 14 kPa, comfort | C-8 | |
| PT-1..PT-7, HB-1, HB-3, HB-4, HB-6, HB-7, 15 in CG plumb check (11.4) | as before | | | |

### 12.5 Open checks from C-9 (printed body thinned by up to 1.75 mm)

`outputs/weight_c/c9_body.json` gives the removed mass per region (lumbar struts / pan 10.0 g, stay feet 9.1 g) but
not the per-surface offset, and the offset field needs the 6 min voxel domain that belongs to the structural-fea-engineer:
**not re-checked here, listed open.** Reasoning for the pad seat: the EVA rails are bonded to the pan face, so if the
face recedes, rails and backer move with it and the 4.5 mm depth play (6 mm rail - 1.5 mm spine) is unchanged; the
bow-tie stays on the Ti pin (the pivot boss is a keep region), so its spine sits up to 1.75 mm closer to the backer.
If the re-exported STL shows a pan-face offset > 1 mm under the rails, shim the rails by that amount. **Open:** (1)
measure the pan face under the rails on the C-9 STL; (2) stay-foot boot fit on the C-9 stay feet (9.1 g removed there).

### 12.6 Renders (Blender Cycles, `huntkit/viz3d/corrie_b2.py`, `corrie_b2_viz3d.py`)

Fixes against the B.1 renders: (1) **wing camo bar**: the B.1 bar was the last grid columns of a panel that stretched
over the scope sleeve, 0.2 mm off the wing face, so it spread and z-fought into a torn shape; now the wing is relaxed in
both directions over a capsule obstacle and the bar is the true 25 mm from the free edge, 0.6 mm proud
(`corrie._wing(clean=True)`); (2) **mannequin**: a retail display form (one loft from the hip cut to a domed neck cap,
no arms, on a stand) replaces the clay figure with capsule arms; (3) **belt B**: pillow section (crowned outer face,
thin edges), black 20 mm binding, quilt channels following the crown (`belt_b_parts(padded=True)`). B.2 content shown:
solid roll-top hem, 2.7 L pouch with solid top and camo pull tab.

| # | File | View |
|---|---|---|
| 1 | `outputs/screens/20261109_corrie_b2_1.png` | hero 3/4 rear on the display form |
| 2 | `outputs/screens/20261109_corrie_b2_2.png` | side, wearer's right |
| 3 | `outputs/screens/20261109_corrie_b2_3.png` | belt B front 3/4 |
| 4 | `outputs/screens/20261109_corrie_b2_4.png` | scope sleeve left, tripod right |

Copied to `docs/screens/`: `_1`, `_3`, `_4`.

### 12.7 Flags

1. Released SPINE tables drift with the new records: `build_geometry.py` would move `geometry.yaml` total 3495.6 ->
   3523.7 g (B-06 Robic +21.7, B-01 ULTRA +2.7, B-09 +4.3, P-01..03, thread +0.8); `tests/test_build_geometry.py` fails
   2 tests. Not edited (released files): orchestrator / owner call. When it is regenerated, `corrie.SPINE_TOTAL_G`,
   `SPINE_BODY_G`, `SPINE_SIDE_POCKETS_G`, `SPINE_B09_G` must move with it (net effect on CORRIE about +4 g).
2. B.2 + C misses the 3.8 kg publish number by 110 g at belt M (12.2).
3. The 2:1 / pocket / holster geometry is unchanged; hipbelt pockets keep B.1 masses (no record change touches them).

## Screenshots

Rev B.1 renders (2026-11-09): section 11.6. The list below is rev B (2026-11-08).

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
