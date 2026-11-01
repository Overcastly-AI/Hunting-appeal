# Pack 5200: beginner builder plan

For the owner, a first-time sewer with no machine yet. Goal: a working prototype in ~10–14 weeks
of evenings and weekends, by climbing a **skill ladder**. Each practice project uses the exact
operations the real pack needs, in cheaper fabric and lower-stakes parts. Every practice piece is
usable gear, so nothing is wasted. Piece ids (`B-01`, `H-03`, …) refer to `panels.yaml`. The
patterns come from the pattern-maker as true-scale tiled PDFs with a 100 mm / 4 in test square.
Print the PDFs at 100 %, then check the square with a ruler before cutting anything.

## 0. Equipment (prototype stage)

| Item | Why | Approx. |
|---|---|---|
| Walking-foot machine, or a heavy-duty domestic machine that handles tex 90–135 thread and a 110/18–120/19 needle | 840D TPU plus webbing layers stall light machines. A walking foot stops the TPU fabric from creeping | $300–900 |
| Needles: 100/16 (body), 110/18 (webbing), 120/19 (bartacks); round point for coated fabric | | $15 |
| Thread: `bonded_nylon_tex90`, `bonded_nylon_tex135`, `bonded_poly_tex90` | Per the material picks | $40 |
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
| 2 | **Stuff sack** (repo demo pattern, `huntkit.patterns.cli demo`) in `robic_100d_ripstop` | Cylinder + round base (curve into straight), drawcord channel, seam finish | Extension collar `B-06/07`, hydration sleeve `B-09` | 1 weekend |
| 3 | **Hipbelt pocket** `HP-01/02` (make 3 and keep the best 2) | Zip insertion (#8 coil), gusseted box shape, small curves, binding | All zips, side pockets `P-01/02`, lid | 1 weekend |
| 4 | **Camo shard practice panel**: sew SH-01 onto a 500D scrap | Edge-turn and topstitch angular appliqué, sharp outside/inside corners, sewing through 2 layers + Hypalon tab | All shards, lash tabs `B-11` | 2 evenings |
| 5 | **Lid** `L-01..05` | Box gusset around radiused corners, AquaGuard zip, under-lid pocket, buckle/webbing tabs | Main bag corners (same R-corner-to-strip operation, bigger) | 1–2 weekends |
| 6 | **Load shelf + load wings** `S-01..04` | Sewing 840D TPU (the hardest fabric), webbing bartacks for load (tex 135, 120/19), grommets | Frame-side panel `B-01`, bottom `B-05` | 1 weekend |
| 7 | **Back panel + harness straps + crown pulley** `BP-*`, `HS-J*`, pulley webbing | Foam sandwiches (pre-cut foam), spacer mesh, binding around foam, matching left/right mirror pieces. Then thread the 3:1 crown pulley (sealed 25 mm webbing through the 3 guides into the cam buckle) and tie the pawl release cord to its strap toggle | Hipbelt wings | 1–2 weekends |
| 8 | **Hipbelt M** `H-01..08`, rifle-boot mount tabs `R-03` on **both** wings | Graded parts, stiffener insertion, the 50 mm buckle and webbing bartacks under load | Other belt sizes | 1–2 weekends |
| 9 | **Main bag** `B-01..12`, `SH-01/02` | Full box-bag assembly in order: flat-work first (shards, tabs, ladders, pockets on the flat panels), then **both** side zips (`B-03a/b` ×2, garages `B-08` ×2), then box seams, bottom, collar, binding | — | 2–3 weekends |
| 10 | **Integration**: fit to frame, field test with a sandbag | Adjust strap lengths, record mass | — | 1 weekend |

Rule of thumb: **all flat-work goes on before panels become 3D.** Shards, tabs, pockets, ladders
and zips are sewn while the panel lies flat. Box seams come last.

Before each step, make a 150 × 150 mm test sample of the exact layer stack (e.g. shard + 500D +
Hypalon tab) and adjust tension until both sides look the same.

## 2. What's hard, and why

| Hard thing | Why it's hard | How we make it easier |
|---|---|---|
| Sewing **840D TPU-coated nylon** | It's stiff and grippy. The coating sticks to the presser foot and the layers creep | Walking foot, Teflon foot or tape on the bed, longer stitch (3.5 mm), clips not pins |
| **Box corners** (R60 bag bottom, R50 lid) | Turning a strip around a curve without puckers | Match notches every 25 mm (the pattern has them), clip the allowance, sew slowly with the needle down at each pivot. The lid is the rehearsal |
| **Full-length side zips, both sides** (2 × 835 mm, ambidextrous) | Long straight seams across two strips; easy to wave. Doing it twice means the second one is better: sew the left side first, it's the less-used side for most | Baste with 6 mm double-sided basting tape first; mark matching notches at 100 mm spacing |
| **Load-bearing bartacks** (lifters, shelf straps, hipbelt) | These carry the 3.3 kN proof load. A bad tack fails in the field | Box-X pattern, tex 135, 120/19 needle. Test 3 samples to failure before using it on the pack (hang a bucket of sand, or use a luggage scale + lever) |
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
