# Pack 5200: beginner builder plan

> **THE BAG: build it from `outputs/release/pack5200_corrie_f_rev3/` (2026-11-13, RD-21, BL-034).** CORRIE F rev 3,
> door D2. Start with `patterns/README.md` (print and check the test square, tape the pages, read a piece, build
> order), then follow `manufacturing/op_sequence.md` operation by operation (machine, needle, thread, SPI, stitch,
> seam, sketch, QC point for each), `manufacturing/load_points.csv` for every bartack and box-X, and
> `manufacturing/qc_sheet.md` / `release_tests.csv` for the gates. The tech pack
> `manufacturing/techpack_corrie_f_rev3.pdf` has all of it in one file. The skill ladder below is still a good way to
> learn the operations, but its piece ids and step 9 are the old SPINE bag: use the rev 3 ids from the release.
>
> **STOP for everything else (2026-11-10): the rest of this plan is out of date.** It still describes the PA66 centre
> plate, girth-hitched stubs and the hinge-back bay mode (frame, belt, harness and meat-haul steps), all of which were
> replaced. Do not build those parts from it. See `docs/release_delta_register.md` (R1-R3 releases).


**v3 "SPINE" update (2026-11-01).** The bag is now a teardrop roll-top built from 4 developed gores
(frame-side B-01, outer face B-02a/b split by the diagonal zip, 2 side gores B-03), a flat oval bottom
and a straight roll-top collar. There are no box corners, no side zips, no lid (optional accessory) and
no load wings. The steps below are updated; piece ids refer to the v3 `panels.yaml`.

**v3.1 update (2026-11-01).** The bag is deeper (11.9 in) and shorter (42 in to the fill line); B-01 has a 30 mm
step aft near its top (head setback) and **6 meat-strap ports** (B-12). **The shelf lip is gone**: meat is held by
3 internal 38 mm straps (IM1–IM3) that hook to webbing stubs girth-hitched on the frame. The frame is v2 (straight
stays). Old step 6 (shelf lip) is now "haul wraps + meat harness".

For the owner, a first-time sewer with no machine yet. Goal: a working prototype in ~10–14 weeks
of evenings and weekends, by climbing a **skill ladder**. Each practice project uses the exact
operations the real pack needs, in cheaper fabric and lower-stakes parts. Every practice piece is
usable gear, so nothing is wasted. Piece ids (`B-01`, `H-03`, …) refer to `panels.yaml`. The
patterns come from the pattern-maker as true-scale tiled PDFs with a 100 mm / 4 in test square.
Print the PDFs at 100 %, then check the square with a ruler before cutting anything.

## 0. Equipment (prototype stage)

| Item | Why | Approx. |
|---|---|---|
| Walking-foot (compound or upper-and-lower feed) lockstitch that takes **135x17 / DPx17 needles up to 140/22**, sews **tex 135** top and bobbin and clears at least 6 mm under the raised foot, **and sews a 304 zigzag up to 5 mm wide** (the BT-S / BT-M tacks and elastic laps; e.g. a portable straight / zigzag walking foot). A straight-stitch-only walking foot is acceptable only if every 304 tack is sewn as the **BT-301 fallback**: 4 passes over the tack length at 2 mm stitch, backtacked; unrated, like every 304 tack in rev 3 (BL-041 Y-3; `outputs/release/pack5200_corrie_f_rev3/manufacturing/README.md`). A domestic or "heavy-duty domestic" machine (130/705H needles) cannot sew the rev 3 load points as specified (BL-040; `outputs/release/pack5200_corrie_f_rev3/manufacturing/README.md`) | 840D TPU plus webbing layers stall light machines; every box-X and proof specimen is specified on Nm 140/22 + tex 135 | $300–900 |
| Needles (DPx17, round point R): Nm 90/14 (light), 110/18 (body), 140/22 (box-X); ball point SUK 90/14 for the mesh | per the rev 3 op sequence | $15 |
| Thread: `bonded_nylon_tex70` (light fabrics, mesh, lid, liner), `bonded_nylon_tex90` (body), `bonded_nylon_tex135` (box-X), one cone each | Per the rev 3 op sequence (BL-041 n-9) | $40 |
| Rotary cutter (45 mm + 60 mm), self-healing mat 600×900, quilting rulers 6×24 in | Accurate straight cuts on slippery nylon | $90 |
| Hot knife (or a soldering iron with a blade tip) | Seals webbing, Cordura and cord ends | $40 |
| Wonder-clips (no pins: pin holes leak in coated fabric), seam ripper, awl, chalk/silver pen | | $25 |
| Grommet/eyelet press kit (8 mm) | Drain grommets | $30 |
| Kitchen scale (1 g) | Weight-budget tracking against `geometry.yaml` | $15 |
| For the frame (if built yourself): dust mask P3/N100, nitrile gloves, fine-tooth saw + miter box, 120/240 grit, IPA, digital caliper, oven/thermometer for the 65 °C post-cure | Carbon dust is an irritant and conductive. Cut it wet | $120 |

Production scale-up (later, from the factory tech pack): a single-needle walking-foot industrial
(301), a bartack machine, a binding attachment, and a cutting table. Or skip all of that and send
the tech pack to a contract factory.

## 1. Skill ladder

| Step | Practice project | Operations learned (ISO stitch) | Pack parts it prepares you for | Time |
|---|---|---|---|---|
| 1 | **Machine drills** on scrap: 20 straight lines at 3 mm from the edge, pivots at corners, 10 bartacks, backtacks, stitch length 2.5–3.5 mm | Straight 301, pivot, backtack, tension setting | Everything | 2 evenings |
| 2 | **Stuff sack** (repo demo pattern, `huntkit.patterns.cli demo`) in `robic_100d_ripstop` | Cylinder + round base (curve into straight), drawcord channel, seam finish | Roll-top collar `B-06/07`, bottom oval `B-05`, hydration sleeve `B-09` | 1 weekend |
| 3 | **Hipbelt pocket** `HP-01/02` (make 3 and keep the best 2) | Zip insertion (#8 coil), gusseted box shape, small curves, binding | All zips, floating side pockets `P-01..03`, fly base pocket `F-02` | 1 weekend |
| 4 | **Camo shard practice panel**: sew SH-01 onto a 500D scrap | Edge-turn and topstitch angular appliqué, sharp outside/inside corners, sewing through 2 layers + Hypalon tab | All shards, lash tabs `B-11` | 2 evenings |
| 5 | **Roll-top collar + rain fly** `B-06/B-07`, `F-01..03` | Long straight tube seam, folded hem with an inserted 0.8 mm HDPE strip, elastic hem on silicone-coated fabric (use tape, not pins), tether | Main-bag collar; the fly is your first light-fabric project | 1 weekend |
| 6 | **Haul wraps + internal meat harness**: wraps W1–W3; meat straps IM1–IM3 (rev 3: 25 mm, hot-knifed ends, a sewn end loop; the cam sewn to an IMC tab that carries the hook / carabiner, sketch SK-11); 6 frame stubs (200 mm, sewn eye); 6 port patches `B-12` on a Challenge Ultra 200 scrap | Webbing bartacks for load (box-X, tex 135, 140/22), hook and cam terminations, laser-cut slot through Hypalon + laminate, sewing Challenge Ultra 200 (walking foot, 3.5 mm stitch) | Frame-side panel `B-01` (same laminate, real ports) | 1 weekend |
| 7 | **Back panel + harness straps + crown pulley** `BP-*`, `HS-J*`, pulley webbing | Foam sandwiches (pre-cut foam), spacer mesh, binding around foam, matching left/right mirror pieces. Then thread the 3:1 crown pulley (sealed 25 mm webbing through the 3 guides into the cam buckle) and tie the pawl release cord to its strap toggle | Hipbelt wings | 1–2 weekends |
| 8 | **Hipbelt M** `H-01..09` (2-stage lumbar), rifle-boot mount tabs `R-03` on **both** wings | Graded parts, stiffener insertion, the 50 mm buckle and webbing bartacks under load | Other belt sizes | 1–2 weekends |
| 9 | **Main bag** `B-01..B-12`, `D-01`, `SH-01..04` | Teardrop assembly in order: (a) flat-work: SPINE band `D-01` onto `B-02b` (lower edge + right end), camo binding `SH-02` on its mouth, corner shards `SH-01`, cam cup `SH-04`, LINK/lash tabs, wrap keeper loops, **6 meat-strap port patches `B-12` on the inside of `B-01` (slot 45 × 6 at x ±100, z 190/330/520 frame heights: check against the frame before cutting)**, hydration sleeve on `B-01`, floating pockets on `B-03`; (b) the **diagonal zip** joining `B-02a` to `B-02b` with the backing strip `B-08`, band mouth lying over it as the storm flap; (c) curved gore seams face ↔ side gores ↔ frame panel, matching notches every 50 mm of centre-line length; (d) bottom oval `B-05` with the fly base pocket; (e) collar + roll hem | — | 2–3 weekends |
| 10 | **Integration**: fit to frame, field test with a sandbag | Adjust strap lengths, record mass | — | 1 weekend |

Rule of thumb: **all flat-work goes on before panels become 3D.** Shards, tabs, pockets, ladders
and zips are sewn while the panel lies flat. Box seams come last.

Before each step, make a 150 × 150 mm test sample of the exact layer stack (e.g. shard + 500D +
Hypalon tab) and adjust tension until both sides look the same.

## 2. What's hard, and why

| Hard thing | Why it's hard | How we make it easier |
|---|---|---|
| Sewing **840D TPU-coated nylon** | It's stiff and grippy. The coating sticks to the presser foot and the layers creep | Walking foot, Teflon foot or tape on the bed, longer stitch (3.5 mm), clips not pins |
| **Curved gore seams** (v3.1 teardrop: ~760 mm long, more curved than v3, seam-length mismatch ≤ 5.8 mm on the outer face) | Two curves of opposite sense must meet without puckers or twist | Match notches every 50 mm (from `panels.yaml` seam lines), clip the allowance on the concave side, sew with the convex piece on top. Practise on a half-scale gore pair in scrap first |
| **Bottom oval** (`B-05` into the gore ring) | Easing a long tube edge onto a closed oval | Quarter-notch both, pin with clips at 8 points, sew bottom-up with the needle down at every pivot. The stuff sack (step 2) is the rehearsal |
| **Diagonal SPINE zip** (509 mm on a seam at 39°) | Bias-ish edges stretch and wave | Stay-stitch both face edges first, baste the zip with 6 mm basting tape, keep the band mouth out of the seam (it lies over the zip, it is not sewn into it) |
| **Load-bearing bartacks** (lifters, shelf straps, hipbelt) | These carry the 3.3 kN proof load. A bad tack fails in the field | Box-X pattern, tex 135, 140/22 needle. Test 3 samples to failure before using it on the pack (hang a bucket of sand, or use a luggage scale + lever) |
| **Foam sandwiches** (straps, belt) | Foam shifts and the binding wanders | Outsource die-cut foam; glue-stick the foam to the mesh; sew the binding with a binding foot |
| **Many-layer stacks** at tab and ladder points (up to 6 layers + webbing) | Needle deflection, skipped stitches | Hammer the seam flat, use a bigger needle and slow hand-crank through the thickest spot |
| **Carbon frame bonding** | Surface prep, bondline control and cure decide the strength. You can't see a bad bond | Outsource first (below). If DIY: jig, glass-bead bondline, coupon test the adhesive first |

## 3. Outsource initially (recommended)

| Part | Outsource to | Why |
|---|---|---|
| **Carbon frame** (cut tubes, bonded nodes, inserts, crown with post sockets) | A composite shop or bike-frame builder, using the FEA engineer's drawings | It's the safety-critical load path. Bond prep and cure are hard to verify at home. **Minimum:** buy the tubes pre-cut and have the plates (lumbar plate, crown spine, yoke plate) **waterjet-cut** from DXF |
| **Torso lock**: PA66-GF30 toothed rack (4 mm pitch), Ti pawl, spring, POM housing | Rack: 3D-printed nylon-CF for prototype 1 (proof-test it to 1334 N both ways before use), then injection-molded or machined PA66-GF30. Pawl: machine shop | Tooth geometry and the pawl spring decide whether it locks reliably. The owner just screws the rack onto the inserts |
| Ti hipbelt pivot pin, bonded inserts | A machine shop (send a print) | Tolerance |
| Pulley guides (UHMWPE-lined rings) and metal cam buckle | Buy off the shelf (climbing/rescue or pack hardware suppliers) | Beginner bolts or sews them on; no fabrication |
| **Foam die-cutting** (EVA 45C/30C, XLPE: `H-03/04/08`, `HS-*3/4`, `BP-02/04`) | A foam converter from DXF | Clean bevelled edges. Hand-cut foam looks and feels lumpy |
| HDPE stiffeners (`H-05`, `S-05`) | Waterjet or a CNC router shop from DXF | Smooth radiused edges that won't wear through the fabric |
| Camo shard fabric (`polyester_ht_630d_printable`) | A sublimation print bureau, printing the owner base camo | Small runs; 1–2 m is plenty for several prototypes |
| Hardware families: aluminium G-hooks (HAUL), POM toggles + quick-pins (LINK), 38 mm hooks + cams (MEAT), magnetic buckles (QUICK) | Buy off the shelf (pack-hardware suppliers) | Tactile coding only works if each family really is different in the hand: check them blind with gloves before sewing |
| Roll hem strip (0.8 × 20 mm HDPE) | Waterjet / CNC router from DXF, or hand-cut strip with rounded ends | Sharp corners wear through fabric |
| MEAT family hardware: 38 mm aluminium sliding-gate hooks (6) and 38 mm metal cam buckles with pull-tabs (3) | Buy off the shelf (pack/rescue hardware suppliers) | Proof-test 5 of each to 910 N before sewing (§5a) |
| Hypalon tabs, slot holes | Laser cutter (local makerspace) | Precise slots, sealed edges |
| Hipbelt centre plate (PA66-GF30) | 3D-printed nylon-CF for the prototype; injection mold for production | Complex shape |

What stays with the owner: **all the sewing**. That's the skill being built, and it's where the
design gets proven.

## 4. Path to mass production
1. Prototype 1 → field test → change list (the owner logs mass, fit and failures).
2. Prototype 2 with fixes. Pattern-maker regrades. Manufacturing-engineer writes the tech pack:
   DXF, nested markers, op sequence with ISO stitches and SPI, QC points and BOM costs.
3. Factory sample round. The camo shards switch to rotary-printed 500D at MOQ (~1000 m).
4. Frame: move to a composite supplier with a fixture-bonded process and a proof test on every
   frame (R-02).

## 5a. Meat-mode check (v3.1, before the first loaded hike)
0. **Proof tests first** (R-29): hang 910 N (93 kg, 205 lb) for 1 min from 5 samples each of: a 38 mm box-X bartack, a
   sliding-gate hook, a cam buckle on 38 mm webbing (mark the webbing: < 3 mm slip). Any failure: change hardware.
1. Girth-hitch the 6 stubs on the frame right at the node wraps (z 190 / 330 / 520). Fit the bag: each stub eye must
   poke through its B-01 port.
2. **Bag-on meat mode**: 30 kg sandbags in game bags inside the bag, high against B-01; hook IM1–IM3 to the stub eyes,
   cam tight; walk 30 min on a slope: no load shift you can feel; time it (≤ 60 s with gloves).
3. **Bay mode**: pop the 4 LINK toggles, let out W1–W3, the bag hinges back on its 2 bottom quick-pins; stub eyes slide
   out of the ports; hook the same straps stub-to-stub round the sandbags, re-cinch the wraps: ≤ 90 s, < 25 mm slip
   after 30 min (R-08/R-09).
4. **Frame-only**: a 36 kg sandbag "quarter" with IM1–IM3 + W1/W2: < 25 mm slip after 30 min (no shelf: friction hold).
5. Wash: unhook the straps, machine-wash cold, dry: hooks and cams still work.
6. **Head check (R-28)**: at your torso setting, bag full and collar unrolled, look up at a ridge: side photo; you
   should reach ~30° of neck tilt before touching the bag.

## 5. Torso-adjust check (do this before the first loaded hike)
1. With the pack empty, pull the release toggle, run the crown through its full travel with the
   pulley tail, and confirm the pawl clicks into the rack along the whole range.
2. Hang 136 kg (300 lb, ≈ 1334 N) from the crown top bar with the frame held upside-down, then
   right-way-up: no slip either way. Use sandbags and a luggage scale.
3. Mark the rack with your torso setting in paint pen so you can see creep at a glance.

## 6. Safety notes
- Proof-test every frame and every load bartack sample before carrying a real load.
- Carbon dust: cut it wet, wear a mask, vacuum (don't sweep).
- Don't leave the frame in a hot car above 60 °C. The epoxy softens (materials overview).
