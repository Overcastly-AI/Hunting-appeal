# Generative printed frame - print package (Pack 5200)

> **DO NOT PRINT FROM THIS FOLDER (2026-11-10).** These files are superseded by the H1 frame (`designs/pack_5200/print/frame_h1/`, pending release). They also have a known defect: the flat halves (441 cm3 together) do not match the assembled body (738 cm3), so they look like an older body. Other open corrections apply as well: the lumbar backer and yoke-plate fixes, and the P-1 bondline. See `designs/pack_5200/analysis/frame_h1.md` §7 for the release list.


Production process, proof load, cost and the print-farm plan: `PRODUCTION.md` in this folder.
The engineering record is `designs/pack_5200/analysis/production_frame.md`.

Source: `huntkit/gendesign/frame_report.py` from the topology optimization in `designs/pack_5200/analysis/printed_frame_study.md`. Units mm. Frame coordinates: x = wearer's right, y = aft (toward the bag), z = up from the stay feet.

## Files

| file | what |
|---|---|
| genframe_lower_flat.stl / .3mf | lower segment, already laid flat (wearer face on the plate) |
| genframe_upper_flat.stl / .3mf | upper segment, flat |
| genframe_assembled.stl | whole body in frame coordinates, including the eight bag fairleads (`huntkit.gendesign.bag_attach`) |
| genframe_rods.stl | (hybrid variant only) the 4 pultruded carbon rods in frame coordinates |
| fiber_paths_principal_stress.csv | continuous-fiber target paths (if printing with continuous fiber) |

## Material

Recommended: **Bambu PAHT-CF** (PA12-based CF nylon: keeps its properties wet better than PA6-CF; data/materials/polymers/pa12_cf_fdm_paht.yaml). PA6-CF is the stiffer/stronger alternative (+9 % mass, absorbs more water). Both were analysed in printed_frame_study.md.

## Bambu H2S settings (PAHT-CF)

- Dry the filament 80 C / 10-12 h; print from a dry box. Hardened 0.6 mm nozzle (0.4 mm works, ~1.6x the time).
- Nozzle 280-300 C, bed 80-100 C with glue, chamber closed (heated if available), aux fan off, part cooling <= 30 %.
- Layer 0.25 mm (0.6 nozzle). **6 walls**, top/bottom 6 layers, infill **100 %** (the optimizer already removed what is not needed; every remaining member is load-carrying). Line width 0.65.
- Orientation: as in the files (laid flat, layer normal = frame y): the frame's bending stresses run along the layers; the Z (interlayer) strength only sees through-thickness shear. Supports: tree, only where the slicer flags bridges > 15 mm (sleeve-bore undersides: let the slicer bridge them; ream after).
- Seam aligned on the wearer face. Brim 5 mm.
- **Anneal** after printing: 90 C for 4-6 h in an oven with the part supported on a flat plate, cool slowly; then dry before bonding.

## Assembly

1. Ream the crown sleeves to 18.0 mm (UHMWPE bushings press in) and the 4 dowel holes to 5.1 mm.
2. Cut 4 dowels from 5 mm pultruded carbon rod, 100 mm long (diamond disc), scuff + clean.
3. Abrade + flame/plasma treat the butt faces and dowel holes, bond with MMA (frame.yaml adhesive): dowels into the lower segment, then the upper segment on; clamp the segments on a flat board, check the two sleeve bores are coaxial with a 16 mm rod through each, cure 24 h.
4. Press in M5 heat-set inserts at the hip-pivot boss and the anchor pads; bolt the SLM Ti hip mount.
5. Slide the carbon crown legs into the sleeves, fit the rack/pawl, pulley guides and bushings as on the tube frame.

## Per segment

| segment | mass g | print h | filament g | cost USD | footprint mm |
|---|---|---|---|---|---|
| lower | 211 | 7.5 | 228 | 18.25 | 256 x 234 x 64 |
| upper | 257 | 9.1 | 277 | 22.18 | 257 x 310 x 58 |

Proof-test the first frame to load_standard.md (T1-T5, T2 with game bags on the internal straps), plus a 40 C / 8 h creep hold at 150 lb and a -20 C empty drop (printed_frame_study.md section 5).
