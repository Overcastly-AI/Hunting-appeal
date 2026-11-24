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
| L1 | aft face, all views | three near-black W straps, two crown straps, door zip tape and the binding draw ~10 dark lines across a mid-tone sage body | high-contrast webbing turns every strap into a graphic; the bag reads as "strapped", not shaped | P4 |
| L2 | aft corners | the camo blade U is 25 to 40 mm wide: from 3 m it reads as **piping**, not as a camo panel | camo too narrow to read as an accent; it also doubles the zip line | P3 |
| L3 | whole bag | camo in **six** places on a set (blade U, kick strip, two garages, two lid corner caps, plus the FP mouth bands and kick bands on the gussets) | confetti: no single accent zone | P3 |
| L4 | top | crown lid, two crown straps with four locks, the bridle, blaze toggles, guy ports and roll clips all within 150 mm | the top is the busiest zone and the one that skylines; nothing reads as one cap | P7 |
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
4. **Width discipline.** Nothing (frame, back panel, belt wing) visibly wider than the bag from behind. Today's back
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
   at least two ink shapes show across it). Narrower camo pieces print solid body colour.
2. **One accent zone per view**, and it sits at an edge: the top (skyline, concept C), the sides (concept B) or the
   base (kick strip). Never as a stripe through the middle of a face.
3. The Cirquefall alternate camo may replace Owner Base 1 : 1 in the same zones (apparel accent mocks,
   `docs/screens/accent_mocks_jacket_pack.png`); never both on one pack.
4. The pack and the apparel share the body and skeleton colours; the apparel's camo yoke/shoulder accent and the
   pack's camo cap (concept C) sit at the same height on the carried figure, which ties the system together.

## 6. Hardware and strap-tail rules

1. **One family, one finish**: 25 mm acetal (G-hooks, ladder locks, side releases) in one colour, matte. Option for
   the owner: ITW Foliage instead of black (S13); confirm against the sage with a sample card.
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
   blob material in the same region; any section change goes back through HA-LS-1 rev C (buckling margin 1.05 is the
   tightest row, `docs/RUBRIC.md`). That check belongs to structural-fea-engineer.

## 9. Concepts against today's baseline

Placeholder, filled after the renders (section below is replaced).
