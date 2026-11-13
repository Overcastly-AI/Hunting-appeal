# H1 printed frame body: print and build package (Pack 5200)

H1 is the frame the owner adopted on 2026-11-10 (`docs/DECISIONS.md`). It is the same branching PAHT-CF body as
today, re-sized locally (about 65 g lighter on the printed body), split at z = 234 mm into two halves that are
**bolted, not glued**: 4 titanium M5 bolts in printed bosses. Engineering record:
`designs/pack_5200/analysis/frame_h1.md`. Source code: `huntkit/gendesign/frame_h1.py`.

> **Rev BL-027 (2026-11-12):** these files are now body **H1-G0.55-B1/2.5**: H1 + BL-024's lower-body growth
> (fatigue on the cloth-sim loads) + BL-027's thicker mid bar and upper inboard branches (Euler buckling on the
> cloth-sim loads) + the **28 mm IM3 cheeks** (BL-021). Each flat half is one closed shell (BL-015's loose island and
> slivers removed). Record: `designs/pack_5200/analysis/h1_buckling.md` (`huntkit/gendesign/h1_buckling.py`,
> `python -m huntkit.gendesign.h1_buckling --export`). R1 is still held for MT-1 (meat-strap cinch, BL-024).
>
> **Rev BL-042 (2026-11-13):** the files before this had **no working fairleads**: the voxel model stops at the bag
> envelope (y 16 mm), and every fairlead was cut off there (no front wall, no pin hole, a solid throat). All 12
> fairleads (hinge, US1, US2, IM1, IM2, IM3, both sides) are now added whole, with exact pin holes and clear
> throats, and checked by slicing this STL (`huntkit/gendesign/h1_fairleads.py`, record
> `designs/pack_5200/analysis/h1_fairleads.md`). The **hinge fairlead (z 60) is new**: 20 mm throat (was 18),
> 5.5 mm clear under the pin for the 3-ply webbing eye (was 1.9), pin centre 10.1 mm above the stay surface
> (was 6.5), and a saddle that wraps the stay down to its centreline with a 45° underside. The bag side must
> meet `bag_attach.HINGE_EYE_ENVELOPE`. Test pieces for HE-FIT and IM3-EC are in `test_pieces/`.
>
> Status: **engineering release candidate.** These files are not yet the released frame
> (`designs/pack_5200/print/frame/` is still today's body). Print the first article only after coupon CA-1
> (`designs/pack_5200/tests_physical/CA1_fatigue_rig.md`) and the joint stubs CA-5 pass.

## Files

| file | what | mass | print time |
|---|---|---:|---:|
| `h1_lower_flat.stl` / `.3mf` | lower half (feet to z 234), laid flat: wearer face on the plate | 331.2 g (0.73 lb) | about 11.7 h |
| `h1_upper_flat.stl` / `.3mf` | upper half (z 234 to the top), laid flat | 513.8 g (1.13 lb) | about 18.2 h |
| `h1_assembled.stl` | the whole body in frame coordinates (x right, y aft toward the bag, z up from the feet), for checks and renders | 845.7 g | |
| `test_pieces/hefit_hinge_fairlead_R.stl` / `.3mf` | HE-FIT test piece: the z 60 right hinge fairlead on an 80 mm stay segment, cut from the file above | 31.9 g | |
| `test_pieces/im3ec_cheek_R.stl` / `.3mf` | IM3-EC coupon: the z 520 right IM3 eye (28 mm cheek) on a 120 mm stay segment | 66.8 g | |

- Masses are from the mesh volume × 1.06 g/cm³. The analysis raster (2 mm) of this body is 800.7 g; it cannot hold
  the fairleads above y 16, which add 37.2 g in the mesh (ledger row H1F, `analysis/h1_fairleads.json`).
- Print time is volume / 8 mm³/s + 8 % waste.
- The meshes are smooth, re-meshed surfaces, not voxels. Exact features are cut in with Boolean geometry:
  - bores printed at Ø17.4, reamed to 18.0;
  - bolt holes printed at Ø4.8, reamed to 5.1;
  - head counterbores Ø12.4;
  - washer slots and hex nut traps;
  - **all 12 fairlead eye holes printed at Ø7.0, reamed to 7.2** for the UHMWPE pin sleeves (BL-042). The IM3 cheeks
    are 28 mm tall along the stay (were 18), 8 mm thick, throat 18 mm. The hinge cheeks are 18 mm tall, 8 mm thick,
    throat 20 mm, on a saddle round the stay. Every throat is cut clear from its floor up.
- Each file is one closed, watertight shell. Footprints 279 × 235 × 74 mm and
  279 × 309 × 60 mm fit the H2S bed (taller than before: the fairleads now stand up to 17.7 mm proud of the stay).
- What changed against the 2026-11-10 files you can see: the mid bar (z 330) is about 2 mm fuller across, the two
  upper inboard branches (z 330 to the crown) about 5 mm fuller, the lumbar struts / pan and stay feet slightly
  fuller (BL-024), and the IM3 eyes taller.

## Shopping list for one frame (besides the parts you already have for today's frame)

| part | qty | note |
|---|---:|---|
| Bambu PAHT-CF | 0.95 kg | about 846 g of part + 8 % waste |
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
6. **Supports: none, except under the 10 IM / US fairleads (BL-042).**
   - The cheeks of the fairleads at z 95, 142, 190, 330 and 520 stand beside the stay with a flat underside about
     8 × 18 mm (8 × 28 at IM3) facing the plate. Paint-on supports under those 10 cheek pairs only. The hinge
     fairleads (z 60) have a 45° underside and need none.
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
   Fairlead eyes (all 12: z 60, 95, 142, 190, 330, 520, both stays): ream each to **7.2 mm** from both sides and
   press in the UHMWPE pin sleeves. The hinge pin (z 60) spans a 20 mm throat: it is 2 mm longer than the others.
2. Hip mount: press the M5 heat-set inserts and fit the SLM Ti pivot mount.
3. Press the UHMWPE bushings into the 18.0 mm bores.
4. Fit the carbon crown (rev C), the rack, the pawl and the pulley guides, as in `../frame/PRODUCTION.md`.
5. Spreader: Sandwich v2, unchanged. The clips at z 166 / 260 / 400 snap over the same stay sections as today. The
   z 260 clip sits 3 mm above the bosses.
   - **One change:** the H1 stay is 4 mm fuller on the bag side at z 119. Make the bonded stand-off pad under the
     bottom tab **0.5 mm** instead of 4.5 mm. A thin PAHT-CF shim is enough, or bond the tab straight onto the
     stay.

## 7. Check before use

1. Weigh the body after annealing and reaming. Expect about 846 g (1.86 lb). More than 880 g means
   over-extrusion; check the flow.
2. First article: HA-LS-1 T9, T1–T5, T4b with a dial on the branch, T4c at −20 °C
   (`designs/pack_5200/analysis/load_standard.md`).
   - Pencil marks across z 234 must not step more than 0.5 mm after unloading. The joint must not open visibly
     under the 300 lb T1 load.
3. Re-torque the 4 bolts to 1.0 N m after the first 24 h and after the first trip.
