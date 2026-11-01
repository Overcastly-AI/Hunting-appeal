# Production frame — tubes, bond, proof, cost

Pack 5200 frame. The structure is the **v2 carbon-tube ladder** (`designs/pack_5200/frame.yaml`), not the solid PAHT print. The back system is unchanged: a **2.0 mm quasi-isotropic carbon spreader** clipped to the stays, and **10 mm XLPE rails** on the stay lines, with mesh over the air gap. Record: `designs/pack_5200/analysis/mass_cut.md` and `back_comfort.md`. Units mm unless noted.

`genframe_assembled.stl` is the retired solid ladder (1291 g, pack 7.51 lb, about 46 h). Do not print it as the frame.

## What you are building

- Stays: two straight roll-wrapped carbon tubes, OD 20 mm, foot to stay top. Cut length 525 mm each.
- Bars: mid bar OD 18 mm, upper bar OD 22 mm, both between the stays.
- Crown: legs OD 16 mm, top bar OD 18 mm, spine OD 20 mm. The rack, pawl housing and pulley guides are the printed PAHT parts (44 g, about 1.6 h).
- Lumbar: formed quasi-isotropic carbon plate, 1.5 mm, bonded to both stays.
- Spreader: bought quasi-isotropic plate, 2.0 mm, cut 208 × 300 mm, clipped to the stay nodes on the bag side.
- Rails: two XLPE pads, 100 × 420 × 10 mm, on the wearer face of the stays. Mesh over the rails only.
- Frame **763 g** with the spreader. Pack **2434 g (5.37 lb)**.

## The small print (rack, pawl, guides)

- Material: **Bambu PAHT-CF** (`pa12_cf_fdm_paht`).
- Dry the spool **80 C for 10–12 h**. Hardened **0.6 mm** nozzle. Nozzle **290 C**, bed **100 C**, chamber closed, part cooling **≤ 30 %**.
- Layer **0.20 mm**, walls enough to make the section solid, infill **100 %** on the pawl cheeks.
- Anneal the pawl housing **90 C for 6 h** on a flat plate, with the pin bore fixtured, then cool in the oven.
- Pawl: ream each cheek to **8.0 mm** and press a 304 sleeve, OD 8.0 mm, ID 4.2 mm, length 8 mm. Pin is a 4 mm slip fit, side to side. Cheek wall 8 mm.

## Bond

1. Stay bores take the UHMWPE crown bushings. No holes through the stay wall for the rack: the rack is a strip on the crown spine.
2. Tube joints are coped, tacked with MMA (`adhesive_methacrylate_ma`), then carbon-wrapped 0.75 mm, 30 mm onto each tube (40 mm on a through-joint). Scarf the wrap ends. Room-temperature cure, then 65 C.
3. Lumbar plate bonds to both stays from about z 50 to z 190. The Ti hip-pivot mount bolts to the pad-up.
4. Spreader clips to the stay nodes (IM1–IM3). It is not a substitute for the lumbar plate.
5. Foot boots stay. The shelf pivot is gone; do not add a shelf boss.

MMA shear used in the check is 6 MPa hot/wet. The T6 coupons still have to confirm it before a batch.

## QC proof load

HA-LS-1 rev B tests in `analysis/load_standard.md` (T1–T5). On the first article add:

| check | load | pass |
|---|---|---|
| T1 static | 300 lb in the bag | no crack, crown set ≤ 1 mm |
| T1(c) hipbelt off | 225 lb | no whitening at the pawl bushing or the upper-bar wrap |
| Bone end | 400 N (90 lbf) through a 22 mm dowel, normal to the spreader, at the window center, toward the wearer | no crack; spreader deflection stays inside the 14 mm pad standoff; the window mesh does not go hard against the back |
| Joint | read during T1 | pencil marks across a wrap do not step more than 0.5 mm after unload |

## Unit cost (one frame, USD)

| item | USD |
|---|---:|
| carbon tubes (record $30/m at 16 mm, scaled by diameter) | 99.40 |
| lumbar plate material | 8.31 |
| wrap kit (ASSUMPTION) | 25.00 |
| MMA | 2.00 |
| foot boots (ASSUMPTION) | 8.00 |
| UHMWPE bushings (ASSUMPTION) | 5.00 |
| SLM Ti hip mount (ASSUMPTION) | 35.00 |
| PAHT rack, pawl, guides | 3.80 |
| machine, 1.6 h at $1/h (ASSUMPTION) | 1.56 |
| QI carbon spreader | 14.56 |
| XLPE rails (ASSUMPTION) | 3.00 |
| **total** | **205.63** |

The dollar total is about the same as the retired 46 h print. The change is the mass and the printer time: 1.6 h instead of 46 h, and no anneal of a 530 mm nylon stay.

## Do not

- Do not print `genframe_assembled.stl` as the frame. That file is the retired solid ladder.
- Do not leave a loaded frame in a closed vehicle if you have built the PAHT prototype instead. The production stays are carbon; they do not have the nylon creep problem. The printed pawl housing still does.
- Do not skip the −20 C empty drop on the first article.
