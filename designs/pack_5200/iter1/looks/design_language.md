# CORRIE F design language brief (iteration 1, looks track, BL-063)

Date: 2026-11-24. Owner rubric: `docs/RUBRIC.md` (strong is a gate, then lighter, then looks better).
Research behind every rule: `docs/research/design_language_iter1.md` (principles P1 to P8, sources S1 to S14).
Renders and concepts: section 9. Code: `looks_render.py` (renders), `concepts_mass.py` (mass deltas, from the release
cut list and the material records), test `tests/test_looks_iter1.py`.

Scope. This brief and the concepts touch **colour, print files, trim colour and strap tidy-ups only**. No geometry,
pattern outline, frame or load path is changed here (the frame-weight and system-weight tracks own those). Where a
rule would need a pattern or frame change, it is written as a rule for those tracks to apply, not applied.

## 0. One line

**A calm sage column with a dark tonal skeleton, and camo only where it does a job: at the edges that skyline or
take the kicks.** Everything else is restraint.

## 1. What today's pack looks like, and what reads "engineering-first"

See section 9.1 for the renders. In short (each item is checked on `20261124_iter1_looks_base_*`):

| # | Where | What the eye gets | Why it reads unresolved | Principle |
|---|---|---|---|---|
| L1 | aft face, all views | three W straps in Deadfall Shadow (#313120, near-black olive), two crown straps, door zip tape and the binding draw ~10 dark lines across a mid-tone sage body | high-contrast webbing turns every strap into a graphic; the bag reads as "strapped", not shaped | P4 |
| L2 | aft corners | the camo blade U is 25 to 40 mm wide: from 3 m it reads as **piping**, not as a camo panel | camo too narrow to read as an accent; it also doubles the zip line | P3 |
| L3 | whole bag | camo in **six** places on a set (blade U, kick strip, two garages, two lid corner caps, plus the FP mouth bands and kick bands on the gussets) | confetti: no single accent zone | P3 |
| L4 | top | crown lid, two crown straps with four locks, the bridle, blaze toggles, guy ports, roll clips and the roll ends curling ~28 mm past the bag sides, all within 150 mm | the top is the busiest zone and the one that skylines; nothing reads as one cap | P7 |
| L5 | side view | the black back panel and frame stand 40 mm proud of the bag edge (D-4 in `corrie_f_renders.md`), the bottle and the black hardware sit on the same line | a dark slab plus hardware noise at the hip | P8 |
| L6 | frame (bag off, `docs/screens/20261112_BL026_8.png`) | faceted generative nodes and blobs on the visible lower body, mixed with tube-and-clevis parts | looks like an FE result, two languages on one frame | P8 |
| L7 | day load | crumpled shell under three straps (D-13) | volume without form; compression shows as wrinkles | P7 |

What already works and must be kept: the tall, narrow, straight-sided column (370 to 420 mm wide, 85 L); the
strap-free door face; one rated hardware family; all locks on the right gusset; tails rolled in keepers (BL-031); the
body-colour panel binding (BL-026); a dark, matte frame that sits inside the bag outline from behind.

## 2. Silhouette

1. **One column.** From behind the bag is a straight-sided column, width constant ±15 mm from the floor to the collar
   seam, with a flat base and a single rounded cap (roll + lid). No wings, no side bulges that are not load. (Today:
   met at 6-day; the full and day states are the cloth's job, L7.)
2. **The cap is one shape.** Roll and lid read as one rounded block: same colour, the crown straps tonal, nothing
   standing above it but the two toggles. (Concept C makes this the accent zone.)
3. **Side profile: parallel faces.** Bag face parallel to the back from the belt to the lid, constant depth; the
   frame shows only as a thin dark line between harness and bag. Anything proud of that line (bottle, pod, tripod) is
   an add-on and may break it.
4. **Width discipline.** Nothing (frame, back panel, belt wing, roll ends) visibly wider than the bag from behind. Today's back
   panel overhang (L5) is a back-system decision, listed as an owner decision, not changed here.

## 3. Line language shared by bag and frame

- **Verticals carry, horizontals hold.** The structural verticals (frame stays, aft corner seams, gusset seams) are
  the long lines; the only horizontals on the aft face are the three W straps (W1 z ≈ 100 to 245, W2 z ≈ 255 to 415,
  W3 z ≈ 690 to 715 mm on the 6-day drape) and the hinge-band seam. Nothing else may cross the door horizontally.
- **Radii family.** Bag corners R 55 (door), R 60 class at the cap; frame visible edges R ≥ 3 mm with node blends
  R ≥ 12 mm (section 8). Use the same family everywhere: no sharp bag corner next to a blobby frame node.
- **Echo, don't decorate.** A colour break sits on a line that already exists: a seam, a fold (the roll), or the
  edge of a printed piece. A rake or diagonal is allowed only where a structural line already rakes (the H1 lower
  branches); none does on the bag today, so no diagonal colour breaks in this iteration.

## 4. Seam and panel-line rules

1. A colour break happens **only** (a) on an existing seam, or (b) as a **print boundary inside one printed piece**
   (engineered placement print: 0 g, no seam, no sewing risk; the camo release already prints each piece in its own
   frame, `outputs/release/pack5200_corrie_f_rev3/camo/README.md` section 3).
2. **No new seam for looks** unless it deletes an overlay or saves mass that the ledger shows.
3. Topstitch and seam thread **tonal** (Elk Wallow on Sage); never contrast stitching on the outside.
4. Bound edges (back-panel binding, pocket mouths, lid edges) in body or harness colour; never black on sage.
5. Zips: coil zips with tonal tape; garages in body colour; one blaze pull only on the openings that must be found
   with gloves in the dark (IMP-4 kill-kit pocket today).
6. **No printed (HyperD 300) fabric where a strap, clip or tab pulls.** HyperD 300 tears at 31.6 / 24.5 N and grabs at
   351 / 236 N against 90 / 80 N and 1000 / 800 N for the 330D it would replace
   (`data/materials/textiles/polyester_300d_printable.yaml`, `cordura_330d_nylon66.yaml`). Camo on a load-bearing
   panel stays on 630D printable (heavier) or does not happen.

## 5. Colour blocking (Krummholz, first build)

| Role | Colour | Hex | Where | Share of the visible bag, per primary view |
|---|---|---|---|---|
| Body | Krummholz Sage | #6E745B | shell, door, gussets, lid (unless the accent), garages | ≥ 70 % |
| Tonal skeleton | Elk Wallow | #5E5A40 | harness, hipbelt, **all webbing, binding, zip tape, cord, thread** | 5 to 15 % |
| Camo accent | Owner Base, 4 inks (Bench Grass #AE9D6C, Sidehill Olive #8B8148, Bleached Tine #C6B497, Deadfall Shadow #313120), 380 mm repeat, upright | — | **one zone per view** (concept choice, section 9) | 10 to 25 % |
| Base / hardware | Deadfall Shadow | #313120 | bottom B-05 (TPU 840D), acetal hardware (matte black or ITW Foliage, S13), frame | ≤ 10 % |
| Signal | blaze | #ff5b14 | one cord pull per glove-critical opening; nothing structural | < 1 % |

Rules:
1. **Camo reads as a panel or not at all.** Minimum camo dimension 120 mm (about one third of the 380 mm repeat, so
   at least two ink shapes show across it). Narrower camo pieces print solid body colour. (BL-067, review 7 m6: this
   rule is absolute; concept C's 75 mm kick strip broke it, which is one reason C' drops the plinth. The lid walls,
   85 mm tall, print solid for the same reason.)
2. **One accent zone per pack** (BL-067: was "per view", which C's cap + plinth broke in the back and 3/4 views), and
   it sits at an edge: the top (skyline, concepts C and C'), the sides (concept B) or the base (kick strip). Never as
   a stripe through the middle of a face.
3. The Cirquefall alternate camo may replace Owner Base 1 : 1 in the same zones (apparel accent mocks,
   `docs/screens/accent_mocks_jacket_pack.png`); never both on one pack.
4. The pack and the apparel share the body and skeleton colours; the apparel's camo yoke/shoulder accent and the
   pack's camo cap (concept C) sit at the same height on the carried figure, which ties the system together.

## 6. Hardware and strap-tail rules

1. **One family, one finish**: 25 mm acetal (G-hooks, ladder locks, side releases) in one colour, matte. Option for
   the owner: ITW Foliage instead of black (S13); confirm against the sage with a sample card. (BL-067, review 7 m6:
   hardware that sits ON a camo zone must be tonal or hidden. Black locks on the light cap ink read as the loudest
   marks on the pack; C' takes the rear crown locks off and draws the rest in Foliage.)
2. **Locks live on the right gusset** (today) or under a fold; nothing on the door face.
3. **Tails**: ≤ 100 mm loose, rolled into an elastic keeper, pointing down or aft (BL-031 rule, kept). Webbing
   colour tonal, so a tail that does escape reads as a shadow, not a stripe.
4. **Toggles and pulls**: tonal except the one blaze pull per glove-critical opening. The guy toggles go tonal
   (concepts A to C); a guy toggle is found by touch on the bar, not by sight.
5. **Narrowest rated webbing** (25 mm, BL-003): keep; do not add wider "feature" webbing.

## 7. Mark (logo) placement, original

- **The mark**: an original glyph, an open cirque bowl (U) under a single ridge stroke, drawn as one 2.5 mm line;
  no lettering on the outside. Our own design; no resemblance to any outdoor brand's mark is intended or allowed
  (check against the brands in `docs/research/pack_market_2026.md` before it is digitised).
- **One mark per pack exterior**, 40 mm wide, tonal embroidery (Elk Wallow on Sage), centred on the B-02h hinge band
  just under the lid (visible from behind, hidden from the front). ASSUMPTION MARK-MASS: ≤ 0.5 g of thread; settled
  by weighing the first embroidered band. Embroidery is sewn before B-02h is joined; it must stay out of the zip
  stitch line (≥ 10 mm).
- Second, optional: a 0.3 mm debossed mark moulded into the crown fitting's outer face (0 g; frame-track decision).
- No reflective, no woven badge with a crinkly backing, no hook-and-loop flag (quiet rule).

## 8. Frame surface styling (rules for the frame track; nothing applied here)

Visible faces of the H1 body (bag on: the lower body below the bag floor and the upper branches beside the lid; bag
off: everything facing aft or outboard):

1. **Two-face rule.** Generative / topology-optimised shape stays on the faces nobody sees (bag-facing, inner).
   Faces seen from behind and from the side get a **swept, constant-section** look: parallel ribs, flat or single-
   curvature tops, constant wall where the FE allows. If a visible face needs extra material, add it as a rib in the
   same language, not as a blob.
2. **Fillets**: visible outer edges R 3 mm, node blends R ≥ 12 mm, all tangent (G1 minimum). Do not fillet a face that
   carries a pin, clevis or clip interface.
3. **Rib language**: ribs run along the load (vertical on stays, along the branch on branches), end in a tangent
   run-out over ≥ 3 × rib height, rib top R = half rib width.
4. **Finish**: matte, as printed PAHT-CF; layer lines vertical on stays (the print orientation already gives this).
   No paint (mass, chips, noise). Colour stays black/Deadfall: the frame is the dark skeleton.
5. **Mass**: a cosmetic face must be mass-neutral or lighter: trade a fillet's added material against removed
   blob material in the same region; any section change goes back through HA-LS-1 rev C (buckling is the
   tightest row: 1.05 of record, 0.85 on the real section I_min per BL-061, under re-check in BL-065 / BL-066). That check belongs to structural-fea-engineer.

## 9. Concepts against today's baseline

### 9.1 How they were made, and what the pictures can and cannot show

`looks_render.py` builds the rev 3 picture scene (`huntkit/viz3d/corrie_f.py`, cloth pass on the fine drape, H1
frame, belt B, 6 ft hunter, 19 in setting), then re-splits the bag mesh **by its real pattern pieces** (B-01, B-02u,
B-02door, B-03L/R, B-05, B-06 from the cloth skin's piece labels) and changes only materials and colours. The one
split that is not a pattern piece is concept C's B-02u (camo kick strip, solid blades): a print boundary inside one
printed piece. Geometry, strap paths, frame and belt are byte-for-byte the rev 3 scene, so every difference in the
sheets is colour, print or trim. Same cameras, 1600 x 1200, 48 samples.

Not shown by the picture model (stated, not hidden): the FP hip-reach pockets (FP-a mesh, FP-b camo mouth band) and the
SH-01b kick bands on the gussets are not drawn; the W1 / W2 slant on the door is the solved taut path, not a pattern
line. In concept C the whole roll is drawn camo; in the build its outer B-07 hem turn stays 330D sage, so the roll
will show a sage band at its end. Renders are 3D models, not photographs.

### 9.2 Today (baseline): `20261124_iter1_looks_1.png` (6-day) and `_2.png` (day load)

Confirms section 1. The worst three, in order: (1) the **top**: crown lid with four locks, and the **rolled closure's ends
curling out past the bag sides like handlebars** (roll x ±238 mm against the bag's ±210 mm on the 6-day scene, so about
28 mm proud each side), with the roll-clip straps and guy lines hanging off them (front and back views), (2) **camo as piping**: the 25 to
40 mm blades read as trim lines beside the zip, the kick strip is the only camo that reads as a panel, (3) **W1 / W2
cross the door on a slant** and converge at the right gusset locks, which reads as a strapped parcel. Side view: the
frame line, guy wires and the grey mesh bottle holster are the busiest band. Front view: the grey mesh strap pocket
is the loudest object (grey against an olive system).

### 9.3 Concept A, TONAL (restraint only): `20261124_iter1_looks_3.png`

| | |
|---|---|
| Changes | webbing, binding, zip tape, cord and thread Elk Wallow (#5E5A40) instead of Deadfall Shadow; SH-07 garages and B-29f lid caps printed solid body colour (print-file change); guy toggles tonal |
| Pattern / geometry | none. Print files: SH-07 and B-29f placed art becomes a solid fill (`camo_corrie_f_rev3.py`). BOM: colour on the webbing, binding, zip, thread and toggle lines |
| Mass | **0.0 g** (`concepts_mass.py`; ASSUMPTION TONAL-WEB: the olive dye lot has the same g/m; settled by weighing 1 m of each before cutting) |
| Strength / sewing risk | none (same records, same parts) |
| Camo print | 0.182 m² a set (from 0.201) |
| Read | a small, real gain: straps sit back, the top loses two camo fragments. It does **not** fix L2 (piping) or L4 (busy top); from 5 m it looks like today |

### 9.4 Concept B, FLANKS: `20261124_iter1_looks_4.png`

| | |
|---|---|
| Changes | A's tonal trim; both side gussets B-03L/R printed camo; the blade U and garages printed solid body colour (the aft face becomes one clean sage slab) |
| Pattern / geometry | none to outlines. B-03 changes material in the cut list, marker and BOM; two large placed-print pieces (B-03L/R, 0.319 m² cut) are added to the print files; B-02u / SH-07 art becomes a solid fill |
| Mass | on HyperD 300: **-15.0 g**; on 630D printable: **+35.1 g**; on mill-printed 330D nylon: 0 g but only through a mill run (MOQ 50 to 100 yd, camo README route C) |
| Strength / sewing risk | **fails the Strong gate on HyperD 300 as drawn.** The gussets carry the W1 to W3 lock tabs, the RT roll-clip tabs, eight B-11 tabs, the hose ports, IMP-8, FP and the B-26 keeper. HyperD 300 grab 351 / 236 N, tear 31.6 / 24.5 N against 1000 / 800 N and 90 / 80 N for 330D (records). Would need `mfg_corrie_f_rev3.py --check` re-run and very likely doublers (mass). On 630D printable it passes on strength but adds 35 g (fails "lighter") and 630D has no small-batch print source |
| Camo print | 0.406 m² a set; about 2 sets per HyperD yard instead of 3 (ASSUMPTION NEST-65: the release set tile's 65 % use) |
| Read | the strongest side and 3/4 picture: big, edgy camo flanks framing a clean solid face; from behind the camo shows only as a thin edge. But it puts the camo where the loads and abrasion are |

### 9.5 Concept C, CROWN + PLINTH: `20261124_iter1_looks_5.png`

| | |
|---|---|
| Changes | A's tonal trim; camo on the **cap** (roll collar B-06 and the crown lid shell B-29a, c, d, e) and on the **plinth** (B-02u printed camo on its 75 mm kick strip only, blades solid); SH-07 and FP-b mouth bands printed solid; B-07 hem and B-29g strap channels stay 330D in body colour (they carry the roll clip and the crown straps) |
| Pattern / geometry | none to outlines. B-06, B-29a, B-29c, B-29d, B-29e change material (HyperD 300 printed) in cut list, marker and BOM; their placed art is added to the print files; B-02u art becomes camo below the kick-strip line and solid above (print boundary, no seam) |
| Mass | **-5.2 g** (`concepts_mass.py`: B-06 +3.0 g, lid shell -8.2 g). Option: delete the B-29f caps on a camo lid, -4.2 g more (they are abrasion overlays; keep unless AB-1 shows HyperD lasts at the lid corners) |
| Strength / sewing risk | low. No rated load point is on B-06 (pattern: notch pairs to B-06f and B-07 only; the RT strap starts on B-07, which stays 330D) or on the lid shell (crown straps run in B-29g, kept 330D). Risks to test: (1) roll-fold durability of the PU-coated HyperD in the collar (new specimen in AB-1: 500 roll/unroll cycles on a B-06 strip, ASSUMPTION ROLL-FOLD), (2) collar hydrostatic head after washing (HyperD 19000 mm new, 1000 mm after 10 washes; robic 1500 mm estimate), (3) colour match of a printed solid next to dyed 330D (strike-off ΔE00, camo README section 4). Sews like today's lid; the lid's #5 zip seam is in HyperD (low load) |
| Camo print | 0.628 m² a set; about 1 set per HyperD yard instead of 3 (ASSUMPTION NEST-65), so about $42 of print per bag instead of $14 (camo README route A prices) |
| Read | the camo sits at the two edges of the column: the cap and the base. The cap is the part that skylines over a ridge and the part a deer sees above brush, and it is also where the hardware clutter is; the print hides the four locks and the strap crossings. The face stays clean sage. From the front the camo cap shows over the shoulders, which is the same height as the apparel's camo yoke (`docs/screens/accent_mocks_jacket_pack.png`): one system |

### 9.6 Scores (rubric order: strong is a gate, then lighter, then looks)

Looks criteria are the five from `docs/RUBRIC.md` axis 3, scored by me on the sheets (the design-reviewer pass is the
real score). P = pass, p = partial, F = fail.

| Criterion | Today | A | B | C |
|---|---|---|---|---|
| **Strong (gate)** | baseline | P (no change) | **F** on HyperD; P on 630D or mill-printed 330D | P, pending AB-1 + roll-fold specimen |
| **Lighter** | 0 | 0.0 g | -15.0 g (HyperD, fails gate) / +35.1 g (630D) / 0 g (mill) | **-5.2 g** (-9.4 g with caps deleted) |
| L1 one silhouette and line language, bag + frame | p | p | p | **P** (cap reads as one block) |
| L2 clean panel / seam lines | p | p | **P** | **P** |
| L3 solid colourway, camo as edgy accent panels | F (piping, confetti) | p | **P** | **P** |
| L4 no hardware clutter / hanging tails | F | p | p | p (top masked, W slant remains) |
| L5 frame surfaces intentional | F | F | F | F (frame track, section 8) |
| Looks total (P = 1, p = 0.5) | 1.0 | 1.5 | 3.0 | **3.5** |

### 9.7 Recommendation

**Adopt C (crown + plinth) with A's tonal trim** for the first build, gated by AB-1 (already ordered as the first
HyperD yard) plus one added roll-fold specimen. It passes the strength gate by keeping every strap and clip load on
330D, it is 5.2 g lighter, it fixes the two worst reads (camo as piping, a busy top) and it ties the pack to the
apparel accent system. B is the better *side* picture but puts printed fabric under eight load points; it is only
worth reopening for a mill-printed 330D production run.

If AB-1 fails, C falls back to **A** (0 g) with the B-02u blade U printed solid above the kick strip (so the plinth
survives on 630D), which is the camo README's solid-630D fallback with one print boundary.

### 9.8 Follow-ups that the paint cannot do (for other tracks; 0 g or lighter)

1. **Level W1 / W2 across the door** (pattern-maker + pack-designer): lock tab heights on the right gusset set so each
   W strap crosses the door within ±10 mm of level. 0 g; check against the tripod and RT tab rules.
2. **Roll ends** (pattern-maker): the rolled closure is wider than the bag (x ±238 against ±210 mm in the scene), so
   its ends read as handlebars in the front and back views. Taper the B-06 / B-07 roll ends so the roll finishes at
   the bag's side line. Saves a little fabric (lighter); the RT strap origin on the roll end (DECISION RT-ORIGIN) and
   the roll-clip path must be re-run (`huntkit.viz3d.corrie_f.roll_clip_paths`).
3. **Mesh colour** (materials-engineer): the shoulder strap pocket, bottle holster and FP-a power mesh in a dark olive
   instead of grey; 0 g if the same mesh comes in that colour (ASSUMPTION MESH-COL).
4. **Frame surfaces**: section 8 rules on the next frame revision.
5. **Back-panel overhang (D-4)**: owner decision, back-system track.

## 10. Concept C′ (BL-067, after review 7)

Orchestrator call 2026-11-24 (review 7 M5 to M7, m6, m7): C is replaced by **C′ = camo on the lid crown only + A's
Elk Wallow trim, no plinth, B-06 solid on its own fabric**, plus the clutter fixes the rubric failed. Unlike A to C,
C′ is **not a paint-over**: `looks_render.py --concept Cp` re-solves the cloth (own cache, `outputs/looks_iter1/Cp_cloth`)
with two geometry proposals drawn in, so they can be judged on real drape. The release is untouched; every geometry
item below is a precise follow-up for pattern-maker (section 10.4). Mass: `concepts_mass.py` (`ledger_concepts`), checks:
`looks_render.py --cp-checks` -> `cp_checks.json`. Renders: `outputs/screens/20261124_bl067_{1..4}.png`.

### 10.1 What C′ changes

| # | Change | Kind | Rubric criterion |
|---|---|---|---|
| 1 | Camo on the lid crown **B-29a only** (HyperD 300 printed, 0.106 m², > 120 mm both ways); B-29f corner caps printed to match; lid walls B-29c/d/e (85 mm tall, under the 120 mm rule) and base B-29b solid | fabric / print | 3 |
| 2 | B-02u blade U printed **solid** body colour (no plinth); SH-07, FP-b solid; roll collar B-06 solid on its scenario fabric (robic 100D now, 70D after tests) | print | 3, 2 |
| 3 | A's trim: webbing, binding, zip tape, cord, thread Elk Wallow; guy toggles tonal | colour | 4 |
| 4 | **W-LEVEL:** W1 on the frame lash points z 250 R + z 250 L, W2 on z 420 R + z 420 L (today a helix: W1 80 → 250, W2 250 → 420). Same hard points (they exist both sides at 80 / 250 / 420, `geometry.yaml`), same W rows; both wraps cross the door level | anchor choice | 2 |
| 5 | **ROLL-TAPER:** collar tapered so the flattened mouth is 2 × 192 = 384 mm (today 2 × 262.4 = 525 = W + D); the roll finishes inside the bag's side line instead of 28 mm proud and bent down 75° ("handlebars") | pattern | 1, 4 |
| 6 | **LID-LOCK:** the two rear crown-strap ladder locks deleted; the strap's rear end is folded and box-X'd on the same B-28t tab (the rated row keeps its box) → 2 visible lid locks instead of 4 | pattern / BOM | 4 |
| 7 | Hardware drawn in an ITW-type **Foliage** acetal (ASSUMPTION HW-TONAL; the owner's build-1 call is matte black, sample card ordered) | colour | 4 |
| 8 | Mesh (IMP-3 holster, IMP-6 phone pocket, FP-a) drawn **dark olive** (ASSUMPTION MESH-COL, 10.3) | colour | 4 |
| 9 | Roll-clip tails drawn stowed flat under the K-RT keeper, pointing down (no outward roll) | assembly | 4 |

### 10.2 Mass on the ledger basis (review 7 M5; `iter1_weight.rows(scen, cfg)`)

Every concept against the ledger's own fabric per scenario (the lid is an as-hunted add-on, never base):

| Concept | base, proven now | base, after tests | as hunted, proven now | as hunted, after tests |
|---|---:|---:|---:|---:|
| A tonal | 0.0 | 0.0 | 0.0 | 0.0 |
| B flanks (HyperD gussets) | -15.0 | +0.3 | -15.0 | +0.3 |
| C (review 7 reproduced) | +3.0 | +15.2 | -5.2 | +7.0 |
| **C′ colour/print only** | **0.0** | **0.0** | **-5.0** | **-5.0** |
| **C′ with geometry (taper + RT re-cut + lid locks)** | **-15.4** | **-12.9** | **-34.4** | **-31.9** |

Geometry rows (`concepts_mass.json` ledger.Cp.geometry): ROLL-TAPER -17.9 g P / -15.4 g A (wedge 0.070 m² off
B-06 + B-06f at their side seams, hem B-07 and the two B-07s strips -26.8 %; ASSUMPTION TAPER-WEDGE: linear over the
494.8 mm collar); RT re-cut +2.5 g (cut 565 → 635 mm, 10.4); LID-LOCK -14.0 g as hunted (2 × 7 g heavy ladder lock;
ASSUMPTION LOCK-WEB: net webbing 0 g). B was the only concept the old cut-list basis made look lighter that the
after-tests basis does not (+0.3 g: A already swaps the gussets to ULTRAGrid).

Volume: the standing collar (full load) loses about **0.8 L** (`collar_volume_loss_L`, ASSUMPTION COLLAR-RULED), so
the main bag stays inside 85 L ± 3. Access: the mouth opening falls from 1050 to 768 mm perimeter (-27 %); the D2 door
is the main access, but a game bag through the top gets tighter (LOADOUT check in 10.4).

### 10.3 Checks re-run

- **Roll-clip path** (`corrie_f.roll_clip_paths` on the C′ cloth, the BL-043 check; `cp_checks.json`): today 202-424 mm
  (day / full), C′ **261-491 mm**. The tapered roll's ends no longer bend 75° down toward the tab, so with the RTM tab
  where the release has it (201 mm under the collar seam) the strap is ~68 mm longer: RT cut 565 → **635 mm** by
  strap_tails' rule (grip 50 mm at the longest path). Tail at the 6-day setting 254 mm (today 253): the RT-TAIL-EXC
  exception stays, kept by the K-RT keeper. The strap now lies on the gusset over its whole run (bears on the cloth
  from z ~505 up to the roll end) and passes the B-11 muzzle tabs at **14-15 mm** stand-off (today 33-37 mm).
  W3 vs roll: C′ moves the roll out of W3's band at M 20.5 / L 20 in on the 6-day load (from "on the roll" to "below").
- **W paths** (cloth meta): W1 6-day 822 → 819 mm, W2 837 → 819 mm; day load W2 -43 mm. Cuts unchanged (sized for haul),
  tails stowed in the existing K-W keepers.
- **Bag load points** (`mfg_corrie_f_rev3.py --check`): unchanged by C′ as drawn (no pattern edit made): 32 points,
  min SF **1.36** (B-25), no holds. **RT / RTM are now rated** (review 7 m9): ASSUMPTION RT-LOAD 225 N (the W wrap
  envelope, S9: a lashed load or a lift by the roll), box-X + base fabric under the loaded edge → **SF 2.28**, buckle
  margin 2.0 (450 N ESTIMATE), proof **RT-PULL 338 N** added to the release gates.
- **Mesh colour:** no stocked olive *stretch* power mesh was confirmed. A retail listing shows a nylon/spandex power
  mesh in "Dark Olive" (search summary only, the page blocks fetching: secondary), and an inelastic MIL-C-8061 nylon
  raschel mesh is stocked in ranger green / foliage / coyote (ahh.biz, fetched 2026-11-24) but is not a drop-in for
  the stretch pockets. The olive in the renders is **ASSUMPTION MESH-COL**; the build stays on the grey/black mesh
  until materials-engineer sources a brightener-free olive power mesh (Shelby lists its 4 mm spacer mesh in Ranger
  Green, which covers the back panel only).

### 10.4 Follow-ups for pattern-maker (precise; nothing half-done in the release)

1. **P1 W-LEVEL** — `geometry.yaml haul_wraps`: W1 `anchor_R: load_wing_lash_z250_R`, `anchor_L: load_wing_lash_z250_L`,
   z_R = z_L = z_at_19in = 250; W2 `z420_R` / `z420_L`, 420. Re-run `kw_heights` (K-W keeper notches on the aft corner
   seams move to the level crossings), strap_tails W rows (BL-031 cuts; carry path -3 / -18 mm at 6-day), `--check`.
   Clearances to confirm: B-11 bow tabs z 470-560 stay 38 mm above W2's top edge; IMP-8 (z 35-150) is freed of W1;
   FP (z 150-380) already crossed at z 250 both sides today. **Risk:** the tripod loses its lowest wrap (z 80 → 250);
   the T9 / add-on fit must show the tripod's lower end held (B-26 keeper or IMP-8). **Structural:** W now loads the
   R z 420 and L z 250 lash points (mirror images of points loaded today); structural-fea-engineer to confirm the mirror.
2. **P2 ROLL-TAPER** — B-06 and B-06f: at each B-06 | B-06f side seam take 70.4 mm off each piece's edge at the mouth,
   tapering straight to 0 at the collar seam (mouth perimeter 1049.8 → 768.0 mm, flattened 384 mm). B-07 hem
   -281.8 mm in length; B-07s strips each shortened to the 384 mm flattened mouth less the current end margin; RT box
   and the clip-path notch move with the hem ends (DECISION RT-ORIGIN stays: the strap leaves the roll end). RT cut
   635 mm (`cp_checks.json`) **or** raise the RTM tab by about 60-70 mm (the roll end no longer drops) to keep the
   565 mm cut; either way re-check the B-11 muzzle-tab stand-off (14-15 mm drawn; BL-041 RT-FWD `mk_dx`) and W3 / hose
   port clearances, then `--check` (must stay min SF ≥ 1.36, no holds) and LOADOUT (game bag through the top).
3. **P3 LID-LOCK** — B-28 rear end: no ladder lock; fold 30 mm and box-X on the B-28t tab (same box, same LL-H proof
   row; the hardware column becomes "none"). Re-run strap_tails B-28 rows: the front lock now takes the whole
   adjustment, its tail grows (keeper already there). BOM -2 heavy ladder locks.

### 10.5 Score (pass / fail per criterion, my own reading of `20261124_bl067_1..4.png`; the design-reviewer's is the real one)

| Criterion | Today | C (review 7) | **C′ as drawn** | C′ with build-1 hardware (matte black) and grey mesh |
|---|---|---|---|---|
| Strong gate | baseline | pass (pending AB-1) | **pass**: no load piece changes fabric; min SF 1.36 unchanged; RT now rated 2.28; geometry items gated by `--check` in P1-P3 | same |
| Lighter | 0 | heavier (+3.0 / +15.2 base) | **0 base, -5.0 as hunted**; with geometry -15.4 / -12.9 base | same |
| 1 one silhouette and line language, bag + frame | F | F | **F** — the bag column now reads clean (roll inside the side line, one cap), but the back-panel overhang (D-4) still shows as a dark slab in the 3/4 and side views, the frame line shows below the bag and in the side view, and the day load is a crumpled shell (L7) | F |
| 2 clean panel and seam lines | F | F | **P** — W1 / W2 level across the door, no camo piping, plain blade U | P |
| 3 solid colourway, camo as edgy accent panels | F | P | **P** — one zone, at the top edge, one piece | P |
| 4 no hardware clutter or hanging tails | F | F | **P** — 2 lid locks instead of 4, tonal; tails stowed; olive mesh; the right gusset still carries the W lock column + roll buckle in the side view (tonal) | **F** (black locks on the camo cap, grey mesh pocket) |
| 5 frame surfaces look intentional | F | F | **F** (frame track; bag-off view in `_4`) | F |
| **Total** | 0/5 | 1/5 | **3/5** | **2/5** |

Not fixed and why: criterion 1 needs the D-4 back-panel decision (owner, back-system track) and the frame line;
criterion 5 is the frame track (section 8). The day-load crumple (L7) is cloth physics on a near-empty bag; only a
lighter, stiffer shell or a compression sleeve would change it.
