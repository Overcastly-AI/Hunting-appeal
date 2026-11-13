# H1 fairleads: complete on the print files, and a hinge the eye can pass (BL-042)

Date 2026-11-13. Ticket `docs/backlog/BL-042-h1-fairleads.md`, findings Z-1 / Z-2 of `review_20261113_rev3_third.md`. Code `huntkit/gendesign/h1_fairleads.py` (`python -m huntkit.gendesign.h1_fairleads`), geometry `huntkit/gendesign/bag_attach.py` (`HINGE_GEOM`, `HINGE_EYE_ENVELOPE`), export `frame_h1.print_mesh` / `h1_buckling.export_print`, tests `tests/test_h1_fairleads.py`. Results `h1_fairleads.json`.

## Summary

- **Z-2 fixed and checked on the STL itself.** Before: every one of the 12 fairleads in `print/frame_h1/h1_assembled.stl` was cut off at y 15.46 (the voxel envelope): no front wall, no pin hole, a solid throat at the hinge, IM1 and IM2. After: all 12 are whole (bounds y max 25.9 mm). Slicing the exported STL through every pin axis and every cheek: before **0 / 12 pass**, after **12 / 12 pass**.
- **Z-1 fixed.** Hinge fairlead (z 60): gap under the pin 1.9 -> **5.50 mm** measured on the STL (3-ply eye 4.5 mm + 1.0 mm margin; 0.22 in); throat 18 -> **20.0 mm** measured (18 mm neck, 19 mm worst case, 1.0 mm clear; 0.79 in). The eye's ply stack plus margin overlaps the section by 0.000 mm2 (before: 68.2 mm2).
- **Cheek strength kept and raised.** Rev C governing hinge load (724 N factored, tall_load): 1/FI99 2.97 -> **3.73**, fatigue 1.67 -> **2.10**. On the CORRIE F sim hinge-pin vectors with their sideways pull (never checked before): fatigue 0.79 (fails) -> **1.17**, strength 1.41 -> **2.08**. The fix that does it is a saddle: the hinge fairlead's root and cheeks now wrap the stay down to its centreline (45 deg underside outboard of the stay).
- **Mass.** The completed fairleads add **+37.2 g (1.31 oz)** to the printed body (mesh 808.5 -> 845.7 g). The 2 mm raster never held them above y 16, so this mass was never booked (ledger C1 removed the fairleads as 'inside the raster'). Booked now as ledger row **H1F** (H1 configs only).
- **Body checks re-run** on the voxel body as printed (throat stubs cleared, holes emptied, hinge saddle added): every rev C basis moves by at most 0.006 (section 5).
- **Test pieces** for HE-FIT and IM3-EC are cut from the fixed mesh (`print/frame_h1/test_pieces/`), and the test kit points at them.

## 1. What was wrong (Z-2), measured on the old STL

`frame_topopt.build_domain` voids everything above `env.y_hi(z)` (grid top `Y_HI_GRID` 16 mm). The fairleads stand 14-17 mm proud of the stay, so most of each one is outside the voxel model. `frame_h1.assemble` restores them as hard points and then re-applies the void; `print_mesh` meshed what was left and never added them back. `frame_h1.keepouts` counted fairlead voxels only inside the envelope, so it read 1.000.

Slice check of the old file (plane z through each pin axis, plane x through each cheek), right side, against the geometry that file claimed (2026-11-01 fairleads, 28 mm IM3 cheek):

| station | floor y / design | gap under pin mm | throat clear mm | hole (vertical) mm | front wall mm | cheek height mm | pass |
|---|---|---:|---:|---:|---:|---:|---|
| hinge_R z 60 | 15.45 / 10.34 | -3.21 | 0.0 | 25.4 (open to the bag) | 0.0 | 0.0 | **no** |
| us1_R z 95 | 9.94 / 9.51 | 1.47 | 80.0 | 26.4 (open to the bag) | 0.0 | 0.0 | **no** |
| us2_R z 142 | 8.02 / 8.40 | 2.28 | 80.0 | 25.4 (open to the bag) | 0.0 | 0.0 | **no** |
| im1_R z 190 | 14.76 / 12.60 | -0.27 | 0.0 | 25.1 (open to the bag) | 0.0 | 0.0 | **no** |
| im2_R z 330 | 11.79 / 9.70 | -0.20 | 0.0 | 26.5 (open to the bag) | 0.0 | 0.0 | **no** |
| im3_R z 520 | 9.89 / 9.09 | 1.10 | 80.0 | 26.2 (open to the bag) | 0.0 | 0.0 | **no** |

A hole 'vertical' of 25-28 mm means no material above the pin at all: the hole is an open slot. A throat of 0 mm is a solid throat. The left side reads the same (`h1_fairleads.json` `check_before`).

## 2. The fix in the export

`frame_h1.print_mesh` now calls `h1_fairleads.add_fairleads` after the body's exact features:

1. each fairlead is meshed from `bag_attach.fairlead_local` with its station geometry (0.25 mm marching cubes, off-grid so no face sits on a node) and unioned onto the smooth body;
2. each throat is cleared: a prism from the floor up past the tip, minus the fairlead itself, so the voxel stub goes and the fairlead's own fillets stay;
3. each pin hole is cut exactly, Ø7 printed (reamed to 7.2 for the UHMWPE sleeve, ASSUMPTION HOLE_REAM as the IM3 eyes and the bores).

`h1_buckling.export_print` now also reloads every written STL (as a slicer does: vertices merged) and refuses a file that is not closed. The IM3-only hole cut there is gone (print_mesh cuts all 12).

| file | g | lb | watertight | shells | footprint mm |
|---|---:|---:|---|---:|---|
| h1_assembled.stl | 845.7 | 1.86 | True | 1 | |
| h1_lower_flat.stl | 331.2 | 0.73 | True | 1 | 279 x 234 x 74 |
| h1_upper_flat.stl | 513.8 | 1.13 | True | 1 | 279 x 309 x 60 |

Slice check of the new file (design = the BL-042 geometry), right side; the left side passes the same:

| station | floor y / design | gap under pin mm (design) | throat mm (design) | hole ring Ø mm | centre err mm | front wall mm | cheek mm | cheek height mm | pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| hinge_R z 60 | 10.34 / 10.34 | 5.50 (5.50) | 20.0 (20) | 6.98 | 0.00 | 4.09 | 8.00 | 18.0 | yes |
| us1_R z 95 | 9.51 / 9.51 | 1.90 (1.90) | 18.0 (18) | 6.99 | 0.00 | 4.09 | 8.00 | 18.0 | yes |
| us2_R z 142 | 8.40 / 8.40 | 1.90 (1.90) | 18.0 (18) | 6.99 | 0.00 | 4.10 | 8.00 | 18.0 | yes |
| im1_R z 190 | 12.61 / 12.60 | 1.89 (1.90) | 18.0 (18) | 6.99 | 0.00 | 4.10 | 8.00 | 18.0 | yes |
| im2_R z 330 | 9.70 / 9.70 | 1.90 (1.90) | 18.0 (18) | 6.99 | 0.00 | 4.09 | 8.00 | 18.0 | yes |
| im3_R z 520 | 9.09 / 9.09 | 1.90 (1.90) | 18.0 (18) | 6.99 | 0.00 | 4.08 | 8.00 | 28.0 | yes |

The IM3 cheeks are **28 mm** tall (BL-021) on both sides. Hinge eye check by step (half-width mm, plies' thickness mm, clear gap mm): [[2.0, 4.5, 5.5], [9.5, 3.0, 4.44]].

The check (`check_stl`, tolerances `TOL`): hole ring Ø >= 7.0 - 0.15 and centred within 0.3 in plane x; the vertical void at the pin >= 6.85 and centred; front wall >= design - 0.3; cheek thickness >= design - 0.3; cheek height >= design - 0.5; throat clear >= design - 0.2 from the pin's underside to the tip; floor within 0.8 of design and gap >= design - 0.3 at the throat centre; for the hinge, no material inside the eye's ply stack + 1 mm margin. A test clips a correct body at y 15.46 and asserts the check fails.

`frame_h1.keepouts` no longer reports 'fairleads present'. It reports the voxel stub fraction under its real name and runs `check_stl` on the print STL.

## 3. Hinge fairlead geometry (Z-1)

The eye is the neck: op 4.05 folds each long edge of the 38 mm webbing 10 mm in, so under the pin the eye is 3 plies over the middle 2 mm and 2 plies out to the 18 mm edge (HE-T 1.5 mm a ply). The stay-side ply passes between the pin and the throat floor.

| | 2026-11-01 | BL-042 hinge |
|---|---:|---:|
| throat mm | 18.0 | 20.0 |
| cheek thickness mm | 8.0 | 8.0 |
| cheek half-height mm | 9.0 | 9.0 |
| pin centre above stay surface mm | 6.5 | 10.1 |
| throat floor above stay surface mm | 2.1 | 2.1 |
| root depth into the stay mm | 2.0 | 9.3545 |
| 45 deg underside from |x| mm | - | 9.0 |
| gap under the pin mm | 1.90 | 5.50 |
| tip above stay surface mm | 14.1 | 17.7 |

**The bag must meet `bag_attach.HINGE_EYE_ENVELOPE`** (import it; the module constants `THROAT`, `HOLE_PROUD`, `HALF_Z` stay the IM / US fairleads):

```
station_z_mm: 60.0
pin_d_mm: 5.0
pin_centre_above_stay_surface_mm: 10.1
throat_floor_above_stay_surface_mm: 2.1
gap_under_pin_mm: 5.5
eye_plies_design: 3
eye_ply_t_mm: 1.5
eye_thickness_design_mm: 4.5
gap_clearance_over_eye_mm: 1.0
eye_section_steps_mm: [[2.0, 4.5], [9.5, 3.0]]
eye_margin_mm: 1.0
throat_mm: 20.0
neck_w_max_mm: 19.0
throat_clearance_over_max_neck_mm: 1.0
throat_clearance_over_nominal_neck_mm: 2.0
cheek_half_z_mm: 9.0
cheek_tip_above_stay_surface_mm: 17.7
stay_r_mm_at_z60: 9.3545
pin_centre_from_stay_centre_mm: 19.4545
```

For the HE section model this moves the pin 3.6 mm further from the stay (toward B-01); the cheek half-height (9 mm) is unchanged, so `cheek_lo = pin_z - 9` holds.

**Why a saddle.** Raising the pin alone (same root) lengthens the lever on the root: the first try (pin up, floor down 1 mm) fell to 1/FI99 1.35 on rev C. The sweep (`OUT/sweep*.json`, 1 mm voxels, rev C + 12 sim vectors) showed the critical spot is where the fairlead's root meets the stay (a 2 mm embed on a narrow stay), not the cheek: thicker cheeks (8 -> 12 mm) changed nothing, taller cheeks helped but move the cheek bottom into the bag's box, and taking the root down to the stay centreline fixed it. A 45 deg underside from |x| 9 mm keeps it printable face-down.

## 4. Cheek and pin checks (rev C and sim loads)

`fairlead_fea` is `bag_attach.solve_fairlead` (same mesh, load rule, end caps, PAHT layer FI, FI99 over the yoke), with the sideways part of a load pushing the cheek's inner face (im3_body_simloads.eye_fea's rule). With the 2026-11-01 geometry and the rev C load it reproduces the rev C record exactly (test). 1 mm voxels.

| hinge fairlead | rev C 1/FI99 | rev C fatigue | rev C creep | sim strength | sim fatigue | sim creep | worst sim run |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-11-01, stay circle r 9.35 | 2.97 | 1.67 | 3.57 | 1.41 | 0.79 | 1.69 | F_PR15_fineFM|meat|L (250 N at 1 g) |
| BL-042, stay circle | 3.73 | 2.10 | 4.48 | 2.08 | 1.17 | 2.49 | F_PR15_fineFM|meat|L (250 N at 1 g) |
| 2026-11-01, stay ellipse 6 x 9.35 | 2.08 | 1.17 | 2.49 | 0.92 | 0.52 | 1.10 | F_PR15_fineFM|meat|L (250 N at 1 g) |
| BL-042, stay ellipse 6 x 9.35 | 3.36 | 1.89 | 4.03 | 2.07 | 1.16 | 2.48 | F_PR15_fineFM|meat|L (250 N at 1 g) |

Requirements: 1/FI99 >= 1.0 on the factored load (HA-LS-1 rev C), fatigue >= 1.0 (rev C) and >= 1.15 on the sim loads (BL-021 / BL-024 goal). Sim loads: the 12 CORRIE F rev 1 hinge-pin vectors (fill and meat, 3 torsos, coarse and fine, both sides mirrored onto one cheek), x 3.0 for strength, x 1.6 for fatigue, x 1.0 for creep (ASSUMPTION SIM_BODY of BL-021). The 2026-11-01 hinge **fails fatigue on the sim loads (0.79)**: their sideways pull (the bag floor spanning pin to pin, up to 196 N at 1 g) was never run on the hinge cheek.

- Pin bending (legacy, 5 mm 7075-T6, span throat + cheek, load spread over the throat): rev C 251 MPa, yield SF 1.84 (S-basis 462), fatigue SF 1.71 (Goodman R 0 from the record's 159 MPa x 0.9 surface); sim 313 MPa, yield 1.47, fatigue 1.37.
- Pin bending (bl042, 5 mm 7075-T6, span throat + cheek, load spread over the throat): rev C 266 MPa, yield SF 1.74 (S-basis 462), fatigue SF 1.62 (Goodman R 0 from the record's 159 MPa x 0.9 surface); sim 332 MPa, yield 1.39, fatigue 1.29.
- IM3 28 mm cheek (geometry unchanged), rev C governing IM3 force 605 N: 1/FI99 5.24, fatigue 2.95. BL-021's sim-load eye check (`im3_body_simloads`) is on the same geometry and is not affected.

## 5. Did any structural check depend on the clipped geometry?

- **Fairlead cheek / pin checks** (rev C record, BL-021, BL-024, BL-027): no. They mesh `fairlead_local` whole on a stay stub; they never used the print mesh. They did use the 2026-11-01 hinge geometry, now replaced: re-run in section 4.
- **Body checks** (42 rev C sets x 4 bases, Euler buckling, z 234 joint): they run on the 2 mm voxel body, which holds the fairlead stubs below y 16. The print now clears the throat stubs (up to 0.75 cm3 a station) and adds the hinge saddle, so the body was re-run as printed (`voxel_as_printed`, 540 voxels out, 652 in):

| basis | strength before / after | fatigue before / after | creep before / after | buckling before / after | joint S / F after |
|---|---|---|---|---|---|
| fine_sm8 | 1.677 / 1.677 | 1.175 / 1.172 | 2.507 / 2.501 | 1.223 / 1.220 | 2.08 / 1.73 |
| fine | 1.677 / 1.677 | 1.196 / 1.193 | 2.551 / 2.546 | 1.223 / 1.220 | 2.08 / 1.73 |
| beam | 1.578 / 1.578 | 1.205 / 1.203 | 2.571 / 2.567 | 1.358 / 1.353 | 1.95 / 1.25 |
| fine_sm8.cyc | 1.677 / 1.677 | 0.782 / 0.781 | 1.668 / 1.667 | 1.035 / 1.037 | 2.12 / 1.07 |

`fine_sm8.cyc` fatigue was below 1 before this ticket (BL-024 cinch-cycled set, R1 hold for MT-1); BL-042 does not change that.

- **Mass records:** the 2 mm raster masses (h1_buckling.json 800.7 g) are unchanged; the fairlead mass outside the raster is the new ledger row H1F.

## 6. Mass

| step | g | oz |
|---|---:|---:|
| 12 fairlead solids (union, net of what the body already held) | +44.2 | +1.56 |
| throats cleared | -4.9 | -0.17 |
| 12 pin holes | -2.2 | -0.08 |
| **net, ledger H1F** | +37.2 | +1.31 |

Basis: print_mesh volume before / after h1_fairleads.add_fairleads x 1.06 g/cm3 (pre-simplify). Ledger: `huntkit/mass/ledger.py` H1F (H1 configs), source `h1_fairleads.json`.

**Mass reduction that keeps the SF (not applied):** the 10 IM / US fairleads carry the 2026-11-01 geometry, whose own rev C margins are >= 2.97 (hinge) / 3.60 (IM3). They could lose material only with a per-station check against their own loads; BL-004's attachment diet is the place for that.

**Print note.** The 10 IM / US fairleads keep the 2026-11-01 shape: each cheek stands beside the stay with a flat underside facing the plate (about 8 x 18 mm; 8 x 28 at IM3). The pre-BL-042 files had the same ledges (clipped), and the print README said 'supports: none'. It now asks for paint-on supports under those 10 cheek pairs. The hinge saddle's underside is 45 deg outboard of |x| 9 mm.

## 7. Test pieces (HE-FIT, IM3-EC)

- `print/frame_h1/test_pieces/hefit_hinge_fairlead_R.stl` (+ `.3mf`, + `_frame_coords.stl`): HE-FIT: z 60 R hinge fairlead, 80 mm stay segment; 31.9 g; watertight True, 1 shell; slice check passes.
- `print/frame_h1/test_pieces/im3ec_cheek_R.stl` (+ `.3mf`, + `_frame_coords.stl`): IM3-EC: z 520 R IM3 eye, 28 mm cheek, 120 mm stay segment; 66.8 g; watertight True, 1 shell; slice check passes.

`designs/pack_5200/physical_test_kit.py` (HE-FIT, IM3-EC, run order) now names these files. The released guide `outputs/release/test_kit/guides/G2.md` still says 'from the H1 STL' until the kit is re-released.

## 8. Assumptions

- ASSUMPTION HE-T: webbing ply 1.5 mm (patterns_corrie_f_rev3.HE_T). Settled by a caliper on the bought roll.
- ASSUMPTION HE-GAP-MARGIN: 1.0 mm over the eye's ply stack under the pin (print tolerance, webbing scatter, the eye riding round the pin). Settled by HE-FIT: a 3-ply eye slides round the pin by hand.
- ASSUMPTION HE-NECK-TOL: folded neck 18 +-1 mm; throat 20 leaves 1 mm on the widest neck. Settled by measuring 5 sewn necks, and by HE-FIT.
- ASSUMPTION HOLE_REAM: eyes printed 7.0, reamed 7.2 (as the bores). Settled at first article: sleeve press-in by hand, no cracking.
- ASSUMPTION STAY-AX: the H1 stay at the hinge is narrower than the stay_radius circle; ellipse half-width 6 mm as a sensitivity (both results tabled). Settled by the first-article T1-T5 tests with the hinge loaded.
- ASSUMPTION SIM_BODY: BL-021's scaling of the sim's 1 g frame forces (x 3.0 / 1.6 / 1.0). Settled by T9 and the frame strain gauges.
- ASSUMPTION PIN-KS: pin fatigue: rotating-beam 159 MPa x 0.9 machined surface, Goodman to R 0. Settled by a supplier fatigue figure or a pin bend-fatigue test on the CA-1 rig.
- ASSUMPTION THROAT-Z: the throat is cleared to the cheek ends + 4 mm along the stay; the eye legs leave toward the bag inside that. Settled by HE-FIT.

## 9. Screenshots

- `outputs/screens/20261113_BL042_1.png`
- `outputs/screens/20261113_BL042_2.png`
- `outputs/screens/20261113_BL042_3.png`
