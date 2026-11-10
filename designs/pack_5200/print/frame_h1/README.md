# H1 printed frame body: print and build package (Pack 5200)

H1 is the frame the owner adopted on 2026-11-10 (`docs/DECISIONS.md`). It is the same branching PAHT-CF body as
today, re-sized locally (about 65 g lighter on the printed body), split at z = 234 mm into two halves that are
**bolted, not glued**: 4 titanium M5 bolts in printed bosses. Engineering record:
`designs/pack_5200/analysis/frame_h1.md`. Source code: `huntkit/gendesign/frame_h1.py`.

> Status: **engineering release candidate.** These files are not yet the released frame
> (`designs/pack_5200/print/frame/` is still today's body). Print the first article only after coupon CA-1
> (`designs/pack_5200/tests_physical/CA1_fatigue_rig.md`) and the joint stubs CA-5 pass.

## Files

| file | what | mass | print time |
|---|---|---:|---:|
| `h1_lower_flat.stl` / `.3mf` | lower half (feet to z 234), laid flat: wearer face on the plate | 293.5 g (0.65 lb) | about 10.4 h |
| `h1_upper_flat.stl` / `.3mf` | upper half (z 234 to the top), laid flat | 470.9 g (1.04 lb) | about 16.7 h |
| `h1_assembled.stl` | the whole body in frame coordinates (x right, y aft toward the bag, z up from the feet), for checks and renders | 764.5 g | |

- Masses are from the mesh volume × 1.06 g/cm³. The booked body mass is 757.7 g on the 2 mm analysis raster.
- Print time is volume / 8 mm³/s + 8 % waste.
- The meshes are smooth, re-meshed surfaces, not voxels. Exact features are cut in with Boolean geometry:
  - bores printed at Ø17.4, reamed to 18.0;
  - bolt holes printed at Ø4.8, reamed to 5.1;
  - head counterbores Ø12.4;
  - washer slots and hex nut traps.
- Both halves are watertight and fit the H2S bed: 279 × 235 × 64 mm (11.0 × 9.2 × 2.5 in) and 279 × 309 × 52 mm
  (11.0 × 12.2 × 2.1 in).

## Shopping list for one frame (besides the parts you already have for today's frame)

| part | qty | note |
|---|---:|---|
| Bambu PAHT-CF | 0.85 kg | about 764 g of part + 8 % waste |
| Ti gr5 **low-head** socket cap screw M5 × 45 (DIN 7984, 3.5 mm head) | 4 | Not M5 × 40: it does not reach through the nut. Not a standard ISO 4762 head (5 mm): it stands 1 mm into the band of the z 260 spreader clip. An ISO 7380 button head M5 × 45 also fits. |
| M5 hex nut A2 (ISO 4032, 8 mm across flats, 4 mm thick) | 4 | thin nuts do not fit the trap |
| M5 washer, 12 mm OD × 1.0 mm, A2 | 8 | **12 mm OD is load-bearing**. A standard 10 mm washer is not enough. |
| 5.1 mm reamer (or a 5.1 mm drill bit, sharp) | 1 | bolt holes |
| 18.0 mm reamer | 1 | same as today |
| medium threadlocker (blue) | | |

No carbon dowels, no MMA in the body joint, no flame treatment. You still need MMA for the crown corners, as
PRODUCTION.md describes.

## 1. Print (both halves, same settings as today's frame)

1. Dry the spool at **80 °C for 10–12 h**. Print from a dry box.
2. Use a hardened **0.6 mm** nozzle. Nozzle **290 °C**, bed **100 °C**, chamber closed, part cooling **≤ 30 %**,
   aux fan off.
3. Layer **0.20 mm**, **6 walls**, **6** top and bottom layers, infill **100 %**. Never a gyroid in place of the
   limbs.
4. **Orientation: as in the files.** The wearer face is on the plate (layer normal = frame y), which is the same
   as today. Do not rotate the parts. The analysis assumes the layers run along the stays.
5. Seam on the wearer face (the plate side). Brim 8 mm.
6. **Supports: none.**
   - The bores, bolt holes and counterbores are horizontal round holes that bridge on their own.
   - A rough bridge inside a bore is fine; you ream it.
   - The nut traps are side slots, about 5.6 mm tall, and bridge cleanly.
   - Turn on tree supports only if the slicer flags a bridge longer than 15 mm.
7. Print the CA-1 coupons in the same job if they fit, or at least from the same spool and profile.

## 2. Anneal

**90 °C for 6 h**, each half on a flat plate, with a 16 mm rod through each sleeve bore so the bores stay straight.
Cool in the oven. Dry again (80 °C, 4 h) if the parts sat out for more than a day.

## 3. Clean up and ream

1. Ream the 4 bolt holes in each half to **5.1 mm**, from the split face outward. Go slowly and keep the reamer
   square to the split face. A drill guide or a drill press helps.
2. Dry-fit a nut into each trap. It must slide in from the side and must not turn. If it is tight, file the slot
   lightly: never more than 0.2 mm.
3. Lightly sand the two split faces flat on 120-grit paper taped to a flat board, about 10 strokes, until both faces
   touch over the whole stay section with no rocking.

## 4. Bolt the halves together (the dry z 234 joint)

1. Put a 12 mm washer and then a nut into each of the 4 side traps on the lower half. The washer goes on the side
   toward the split face, under the ledge.
2. Stand the halves on the flat board. Slide a 16 mm rod through both sleeve bores so they line up.
3. Put a 12 mm washer under each bolt head. Drop the bolts into the counterbores of the upper half, through the
   split face, and into the nuts. Add one drop of blue threadlocker on the threads.
4. Tighten each bolt to **1.0 N m** (snug: about two fingers on a short hex key). Tighten in a cross pattern, twice.
   **Do not over-torque.** The nylon creeps, and the joint is designed with no credit for clamping force.
5. Check with your fingernail that there is no step across the split on any face.

## 5. Ream the crown-leg bores through the joint

The crown leg and its 70 mm UHMWPE bushing slide **across** the z 234 split at the 15 in torso setting (the leg
bottom reaches z 171). So the bore must be one continuous hole.

1. With the halves bolted up, ream each sleeve bore to **18.0 mm in one pass** from the top, through the split.
2. Mark the two halves as a matched pair (a scribe line across the split on each stay). Never swap halves between
   frames.
3. Slide a crown leg with its bushing through the full travel. It must not catch at z 234.

## 6. Inserts, bushings and crown (same as today)

1. Pawl: ream each cheek to **8.0 mm** and press in the 304 sleeve (OD 8.0, ID 4.2, length 8).
2. Hip mount: press the M5 heat-set inserts and fit the SLM Ti pivot mount.
3. Press the UHMWPE bushings into the 18.0 mm bores.
4. Fit the carbon crown (rev C), the rack, the pawl and the pulley guides, as in `../frame/PRODUCTION.md`.
5. Spreader: Sandwich v2, unchanged. The clips at z 166 / 260 / 400 snap over the same stay sections as today. The
   z 260 clip sits 3 mm above the bosses.
   - **One change:** the H1 stay is 4 mm fuller on the bag side at z 119. Make the bonded stand-off pad under the
     bottom tab **0.5 mm** instead of 4.5 mm. A thin PAHT-CF shim is enough, or bond the tab straight onto the
     stay.

## 7. Check before use

1. Weigh the body after annealing and reaming. Expect about 760 g (1.68 lb). More than 790 g means over-extrusion;
   check the flow.
2. First article: HA-LS-1 T9, T1–T5, T4b with a dial on the branch, T4c at −20 °C
   (`designs/pack_5200/analysis/load_standard.md`).
   - Pencil marks across z 234 must not step more than 0.5 mm after unloading. The joint must not open visibly
     under the 300 lb T1 load.
3. Re-torque the 4 bolts to 1.0 N m after the first 24 h and after the first trip.
