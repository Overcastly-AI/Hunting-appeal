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
> **Rev BL-045 (2026-11-13):** every IM / US pin also carries a webbing eye, so the other **10 fairleads (z 95, 142,
> 190, 330, 520) now have the hinge's clearance**: 20 mm throat, 5.5 mm under the pin, saddle with a 45° underside
> (on the crown sleeve the root stops 1 mm above the bore). The lower half no longer drops a loose piece (the right
> lower-branch tip at z 217–234 is now fused to its bolt boss, as in the analysis). Record:
> `designs/pack_5200/analysis/crown_and_fairlead_checks.md`. The bag side must meet `bag_attach.imus_eye_envelope`.
>
> **Rev BL-047 (2026-11-13):** the pawl now fits. BL-046 re-made the spine channel for the OD 20 tube + 6 mm rack
> (22 x 36.3 mm, housing z 496-535.6); this rev adds the **pawl pivot bore** through both cheeks (printed 7.6, ream
> 8.0, centre z 500, 4 mm fore of the rack tooth tips), **cheek bosses** down to z 491.5 under it, and a **window in
> the housing's fore wall** (x +/-9) for the pawl's swing and its release cord. The old pawl
> (`../crown_pawl_fdm_pacf.stl`, `../crown_pawl_slm.stl`) does **not** fit H1: swung to release it stands 5 mm proud
> of the housing into the yoke's path. Use the **low-profile pawl** in this folder (`crown_pawl_lp_*`). Both hinge
> fairleads (z 60) have the throat floor relieved 1 mm deep next to each cheek (bag review m-1). Slice-checked on
> this STL through the full pawl swing (`huntkit/gendesign/h1_pawl.py`); record
> `designs/pack_5200/analysis/crown_gnl.md`. Assembled 886.2 g, lower 342.7 g, upper 543.5 g, one closed shell each.
>
> **Rev BL-049 (2026-11-13):** (1) the **hinge fairleads (z 60) are bigger**: cheeks 10 mm thick (was 8) and 36 mm
> tall, reaching 27 mm up the stay above the pin (still 9 mm below it); the throat floor is 1 mm lower across the
> whole throat (6.5 mm clear under the pin, was 5.5) and BL-047's relief groove beside the cheeks is gone. The sims
> pull the hinge eye inboard and up; the old hinge failed fatigue that way. The **hinge pin is now 5 mm
> Ti-6Al-4V, 44 mm long** (a 7075 pin fails the 1019 N check). (2) **The under-strap stations moved to their own
> lanes on printed lug arms**: US1 (z 95) on an arm **45 mm inboard** of each stay (pin at x +/-70), US2 (z 142) on
> an arm **50 mm outboard** (pin at x +/-165). The old US fairleads on the stays are gone. The lower half is now
> **367.5 mm wide and does not fit the H2S bed** (best rotation 343 x 323 mm before the brim): see
> `designs/pack_5200/analysis/h1_lanes.md` (owner decision). The lug arms overhang: **tree supports under the four
> arms** (the only supports on the frame). Assembled 974.2 g, lower 430.7 g, upper 543.5 g, one closed shell each;
> slice checks pass (12 fairleads with their eye stacks, spine channel, pawl swing). Test pieces re-cut:
> `test_pieces/hefit_hinge_fairlead_R` (the new hinge), `test_pieces/im3ec_cheek_R`, and the US route piece
> `test_pieces/us_route_stay_R` (hinge + both lane lugs).
>
> **Rev BL-050 (2026-11-13): the lower half fits the H2S again.** US2 stays at x +/-165 (moving it in to x 147, the
> most the bed allows, puts the strap onto the hinge fairlead: -3.2 mm). Instead the **US2 outer cheek is a bolt-on
> piece**: each US2 fairlead is split in its throat floor at x +/-163; the outer floor and outer cheek print on their
> own as `us2_clevis_R` / `us2_clevis_L` (14.1 g each) and bolt to the frame with two Ti
> M5 x 40 low-head screws each (nuts in side traps that open to the wearer face). The lower half is written **already
> turned on the plate** (321.1 x 299.6 mm; with the 8 mm brim
> 3.0 / 4.4 mm spare): **do not rotate it in the slicer.** `h1_assembled.stl` is
> the frame as assembled (clevises in place). Assembled 995.1 g, lower 423.4 g, upper
> 543.5 g, clevises 2 x 14.1 g; slice checks pass. Record
> `designs/pack_5200/analysis/h1_bedfit.md`. `test_pieces/us_route_stay_R` now prints without the US2 outer cheek:
> bolt `us2_clevis_R` onto it.
>
> **Rev BL-051 (2026-11-13): the stay crown is whole again over z 86-152.** Since BL-049 the bag face of both stays
> sat 2-4 mm low where the old US1 / US2 fairleads used to be (z 86-104 and z 131-152): removing the old fairlead
> stubs had taken the top of the stay with them. The stay section is now continuous there (crown top within 0.3 mm of
> the plain stay, slice-checked on `h1_assembled.stl`). Assembled 997.7 g (+2.6 g), lower 425.9 g, upper 543.5 g
> (unchanged), clevises 2 x 14.1 g; the lower half's footprint and plate rotation are unchanged. All test pieces
> re-cut. Record `designs/pack_5200/analysis/h1_crown.md`. **The z 234 joint and the US2 clevises use different
> screws and washers: see the BOM IDs in the shopping list and keep them in separate labelled bags.**
>
> Status: **engineering release candidate.** These files are not yet the released frame
> (`designs/pack_5200/print/frame/` is still today's body). Print the first article only after coupon CA-1
> (`designs/pack_5200/tests_physical/CA1_fatigue_rig.md`) and the joint stubs CA-5 pass.

## Files

| file | what | mass | print time |
|---|---|---:|---:|
| `h1_lower_flat.stl` / `.3mf` | lower half (feet to z 234), laid flat: wearer face on the plate, **turned 163.5 deg to fit the H2S (BL-050): print it as it loads** | 425.9 g (0.94 lb, BL-051) | about 15.1 h |
| `h1_upper_flat.stl` / `.3mf` | upper half (z 234 to the top), laid flat | 543.5 g (1.20 lb) | about 19.2 h |
| `h1_assembled.stl` | the whole frame as assembled (body + the two US2 clevises) in frame coordinates (x right, y aft toward the bag, z up from the feet), for checks and renders | 997.7 g (BL-051) | |
| `us2_clevis_R.stl` / `.3mf`, `us2_clevis_L.stl` / `.3mf` | US2 outer cheek + outer throat floor (BL-050), bolts onto the lower half at x +/-163; laid flat, wearer face on the plate | 14.1 g each | about 0.5 h each |
| `crown_pawl_lp_fdm_pacf.stl` / `.3mf` | low-profile crown pawl, PAHT-CF prototype, 16 mm wide, 100 % infill (BL-047) | 4.3 g | about 0.5 h |
| `crown_pawl_lp_slm.stl` / `.3mf` | low-profile crown pawl, Ti-6Al-4V SLM + HIP, 12 mm wide (BL-047) | 13.3 g | - |
| `test_pieces/hefit_hinge_fairlead_R.stl` / `.3mf` | HE-FIT test piece: the z 60 right hinge fairlead (BL-049 size) on an 80 mm stay segment, cut from the file above | 41.6 g (BL-051) | |
| `test_pieces/us_route_stay_R.stl` / `.3mf` | US route piece (HE-FIT step 0, FIT-US): right stay z 40-160 with the hinge and both lane lugs; BL-050: without the US2 outer cheek, bolt `us2_clevis_R` on (it also tests the clevis joint) | see `analysis/us_route.json` test_piece | |
| `test_pieces/im3ec_cheek_R.stl` / `.3mf` | IM3-EC coupon: the z 520 right IM3 eye (28 mm cheek) on a 120 mm stay segment | 68.6 g | |

- Masses are from the mesh volume × 1.06 g/cm³. The analysis raster (2 mm) of this body is 800.7 g; it cannot hold
  the fairleads above y 16, which add 50.4 g in the mesh (BL-045) (ledger row H1F, `analysis/h1_fairleads.json`).
- Print time is volume / 8 mm³/s + 8 % waste.
- The meshes are smooth, re-meshed surfaces, not voxels. Exact features are cut in with Boolean geometry:
  - bores printed at Ø17.4, reamed to 18.0;
  - bolt holes printed at Ø4.8, reamed to 5.1;
  - head counterbores Ø12.4;
  - washer slots and hex nut traps;
  - **all 12 fairlead eye holes printed at Ø7.0, reamed to 7.2** for the UHMWPE pin sleeves (BL-042). The IM3 cheeks
    are 28 mm tall along the stay, the others 18 mm; all 8 mm thick, throat 20 mm, on a saddle round the stay
    (BL-045). Every throat is cut clear from its floor up.
- Each file is one closed, watertight shell. Footprints 280 × 235 × 77 mm and
  280 × 309 × 64 mm fit the H2S bed (taller than before: the fairleads now stand up to 17.7 mm proud of the stay).
- What changed against the 2026-11-10 files you can see: the mid bar (z 330) is about 2 mm fuller across, the two
  upper inboard branches (z 330 to the crown) about 5 mm fuller, the lumbar struts / pan and stay feet slightly
  fuller (BL-024), and the IM3 eyes taller.

## Shopping list for one frame (besides the parts you already have for today's frame)

| part | qty | note |
|---|---:|---|
| Bambu PAHT-CF | 1.08 kg | about 998 g of part + 8 % waste (BL-051) |
| Ti-6Al-4V pin, 5 mm h8 ground, 44 mm, with a clip groove (or a 5 x 44 Ti clevis pin) | 2 | BL-049 hinge pins (3.8 g each); not 7075 |
| **HW-J234-SCR** Ti gr5 **low-head** socket cap screw **M5 × 45** (DIN 7984, 3.5 mm head) | 4 | z 234 joint only. Not M5 × 40: it does not reach through the nut. Not a standard ISO 4762 head (5 mm): it stands 1 mm into the band of the z 260 spreader clip. An ISO 7380 button head M5 × 45 also fits. |
| **HW-J234-WSH** M5 washer **12 mm OD** × 1.0 mm, A2 | 8 | z 234 joint only. **12 mm OD is load-bearing**: a 10 mm washer (HW-US2-WSH) is not enough here. |
| **HW-US2-SCR** Ti gr5 low-head socket cap screw **M5 × 40** (DIN 7984) | 4 | US2 clevises only (BL-050), 2 per side. An M5 × 45 is 5 mm too long: its tip bottoms in the blind tail hole (it ends at x +/-142.5) before the head seats. |
| **HW-US2-WSH** M5 washer **10 mm OD** × 1.0 mm, A2 (DIN 433) | 8 | US2 clevises only (BL-050): a 12 mm washer does not fit the 29 mm block. |
| **HW-M5-NUT** M5 hex nut A2 (ISO 4032, 8 mm across flats, 4 mm thick) | 8 | the same nut for both joints (4 + 4); thin nuts do not fit the traps |
| 5.1 mm reamer (or a 5.1 mm drill bit, sharp) | 1 | bolt holes |
| 18.0 mm reamer | 1 | same as today |
| medium threadlocker (blue) | | |

> **Two screw lengths and two washer sizes (BOM mix-up risk).** HW-J234-SCR (M5 × 45) and HW-US2-SCR (M5 × 40) look
> alike, and so do HW-J234-WSH (12 mm OD) and HW-US2-WSH (10 mm OD). Keep each in its own bag labelled with its BOM ID
> and joint ("z 234 joint" / "US2 clevis"). Check before fitting: lay the screw against a ruler (45 or 40 mm under
> the head) and the washer against a caliper (12 or 10 mm). Fit the z 234 joint first and put its leftovers away
> before you open the US2 bag.

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
6. **Supports: none, except tree supports under the four US lug arms (BL-049)**: they stand off the stays as
   cantilevers (US1 45 mm inboard at z 90-106, US2 50 mm outboard at z 127-157).
   - Since BL-045 all 12 fairleads are saddles with a 45° underside outboard of |x| 9 mm; they print without
     supports.
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

1. Put a 12 mm washer (HW-J234-WSH) and then a nut into each of the 4 side traps on the lower half. The washer goes on the side
   toward the split face, under the ledge.
2. Stand the halves on the flat board. Slide a 16 mm rod through both sleeve bores so they line up.
3. Put a 12 mm washer (HW-J234-WSH) under each bolt head. Drop the M5 × 45 bolts (HW-J234-SCR) into the counterbores of the upper half, through the
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

1. Pawl: ream the pivot bore (printed 7.6, at z 500 through both cheeks of the pawl housing) to **8.0 mm** from each
   side and press in the 304 sleeve (OD 8.0, ID 4.2, length 8) flush with each cheek's outer face. Fit the
   **low-profile pawl** (`crown_pawl_lp_*`, not the old one) on the 4 mm pin with a 0.5 mm music-wire torsion spring
   beside it (one leg on the pawl's tang, the other on the window's lower edge); the release cord runs out through
   the fore-wall window. Check: pull the cord to the stop: the rack slides both ways; let go: the pawl snaps back
   into the teeth.
   Fairlead eyes (all 12: z 60, 95, 142, 190, 330, 520, both stays): ream each to **7.2 mm** from both sides and
   press in the UHMWPE pin sleeves. The hinge pin (z 60) is **5 mm Ti-6Al-4V, 44 mm** (BL-049: 10 mm cheeks); the
   others stay 5 mm 7075.
   **US2 clevises (BL-050):** ream the two bolt holes in each clevis and in the lower half's US2 block (x +/-145 to
   163, printed 4.8) to **5.1 mm**. Drop a 10 mm washer (HW-US2-WSH) + M5 nut into each side trap from the wearer face (the nut is held
   by its flats), put the clevis on its block (its flat face against the frame's at x +/-163, the throat floors
   flush), push the M5 × 40 screws (HW-US2-SCR, not the z 234 M5 × 45) with a 10 mm washer (HW-US2-WSH) under the head in from the clevis's outer face and snug them
   (about 1 N m, blue threadlocker; preload is not counted on). Then ream the US2 eye (both cheeks, assembled) to
   7.2 mm so the two cheeks line up, and press the sleeve. Feel the throat floor across the joint line: no step;
   break the edges 0.3 mm if the eye catches.
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
