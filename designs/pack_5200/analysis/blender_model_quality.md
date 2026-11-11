# BL-018: Blender model quality (asset library and fabric realism)

Date 2026-11-11. Code: `huntkit/viz3d/assets/` and `huntkit/viz3d/studio.py`. Tests: `tests/test_viz3d_assets.py`.
How to use it: `huntkit/viz3d/README.md`, section "Studio layer". No design changed: this ticket changes how the
existing CORRIE B.2 geometry is modelled and lit, nothing about what the pack is.

## 1. Result in one paragraph

The old Cycles renders had real lighting on simple models. The new layer replaces the models: the cloth is the
cloth-sim drape refined to about 3 mm and wrinkled by its own strain field, seams are raised ridges with stitch
rows, webbing has thickness and a weave, buckles are solids with through-slots and the webbing wrapped through them,
and the door zip is two meshed coils on tape with a slider and cord pull. The macro frames (buckle, zip) read as
photographs of sewn goods. The full-pack frames read as a soft sewn pack, not as CAD, but they are not yet
photographic: the roll-top, the top pouch and the wings are still the old lofted shapes with wrinkles added on top
(section 6).

## 2. What changed, by ticket task

| Task | Before | Now | Where |
|---|---|---|---|
| 1 Hardware | superellipsoid blocks | 20 parametric solids (manifold3d: profile, extrude, Minkowski-rounded edges, CSG slots and cavities), all watertight | `assets/hardware.py` |
| 2 Webbing | flat ribbon | swept section with half-round selvedges, UV in mm (weft picks 1.05 mm, herringbone), wraps through each buckle, tails with a folded bartacked stop, keepers; the cloth is pressed in under it and pillows beside it | `assets/webbing.py`, `fabric.py` |
| 3 Seams | 4 mm piping tubes | plain seam seen from the face: crease, an 8 mm ridge where the allowance is pressed over, one stitch row 2.5 mm off at 3.0 mm pitch, ridge and cloth gathered at the stitch pitch; bartack (42 stitches) and box-X | `assets/seams.py` |
| 4 Zips | ribbon + tube | two interlocked monofilament coils at the record's chain width, tapes with stitch rows, slider, cord pull with grip, stops; a parted half for the open door | `assets/zips.py` |
| 5 Fabric | smoothed skin + shader bump | refine to 3.2 mm edges, displacement along the normal from: slack wrinkles (minor principal stretch below 1), cloth "hand", seam crease and pucker, strap pillowing, flattening under anything sitting on the cloth. Clamped to 5 mm. Cloth thickness (`solidify`) and linings that follow the face cloth | `assets/fabric.py` |
| 6 Materials | 8 shaders by glTF name | `studio.MATERIALS`: a shader spec per material key naming its record: 330D plain weave, 840D basket, 100D and UHMWPE-grid ripstop, grosgrain, webbing, thread, zip tape and coil, spacer mesh with open cells, XLPE, Hypalon, POM, anodised aluminium, titanium, printed PAHT-CF with layer lines, 2x2 twill carbon | `studio.py` |
| 7 Scene | shadow-catcher floor on a painted gradient | real paper sweep (floor, 0.9 m cove, wall) turned behind the subject for every shot, key / fill / rim softboxes plus a top strip, gradient world, depth of field per shot, presets hero / side / front34 / macro, fabric-covered display form | `studio.py` |
| 8 API | per-concept scripts | `studio.render(concept_scene, shots, out_dir)`; `ConceptScene.add_fabric / add_seams_from_pieces / add_seam / add_strap / add_hardware / add_zip / add_part / add_pack`; wearer hook for BL-019 | `studio.py`, README |
| 9 Proof | | CORRIE B.2 rebuilt (`studio.corrie_b2_scene`): 196 parts, 1.32 M vertices, 20 seam lines, 83 strap dent lines, built in 20-26 s | section 4 |

## 3. Numbers and where they come from

### 3.1 Hardware (mm, inches in brackets)

Local frame: +x along the webbing, +y across it, +z out of the cloth. A value from a record is met within 0.5 mm
(test). Everything marked ASSUMPTION is typical of the class the record names and is used only for the picture; the
test that settles each is a caliper on the purchased part or the maker's drawing.

| Kind | L x W x T mm (in) | Slot / key mm | Sources |
|---|---|---|---|
| bag_hook_38 | 48.0 x 52.0 x 6.9 (1.89 x 2.05 x 0.27) | 39.5 | bag_attachment.md bag hooks 38 mm; ASSUMPTION: L, T, W, mouth, slot |
| cam_buckle_25 | 44.0 x 34.8 x 14.6 (1.73 x 1.37 x 0.58) | 26.5 | -; ASSUMPTION: L, T, W, slot |
| cam_buckle_38 | 52.0 x 47.8 x 16.0 (2.05 x 1.88 x 0.63) | 39.5 | -; ASSUMPTION: L, T, W, slot |
| cord_lock | 24.0 x 17.0 x 12.0 (0.94 x 0.67 x 0.47) | 4.5 | record cord_lock_spring cord_diameter_max_mm; ASSUMPTION: L, T, W, hole |
| d_ring_25 | 25.0 x 34.0 x 3.9 (0.98 x 1.34 x 0.15) | 26.0 | record d_ring_25mm_aluminium section_thickness_mm; record d_ring_25mm_aluminium width_mm; ASSUMPTION: inner_h, inner_w |
| g_hook_25 | 27.0 x 37.0 x 3.5 (1.06 x 1.46 x 0.14) | 26.5 | -; ASSUMPTION: L, T, W, slot |
| g_hook_38 | 27.0 x 50.0 x 3.5 (1.06 x 1.97 x 0.14) | 39.5 | -; ASSUMPTION: L, T, W, slot |
| ladder_lock_25 | 38.0 x 33.0 x 8.5 (1.50 x 1.30 x 0.33) | 26.5 | record ladder_lock_25mm width_mm; ASSUMPTION: L, T, W, slot |
| ladder_lock_25_heavy | 49.9 x 34.2 x 10.3 (1.96 x 1.35 x 0.41) | 26.5 | record ladder_lock_25mm_heavy; ASSUMPTION: slot |
| side_release_25 | 62.0 x 34.0 x 11.0 (2.44 x 1.34 x 0.43) | 26.5 | record buckle_side_release_25mm width_mm; ASSUMPTION: L, T, W, slot |
| side_release_38 | 76.0 x 47.0 x 13.0 (2.99 x 1.85 x 0.51) | 39.5 | record buckle_side_release_38mm width_mm; ASSUMPTION: L, T, W, slot |
| side_release_50 | 92.0 x 59.0 x 15.5 (3.62 x 2.32 x 0.61) | 51.5 | record buckle_side_release_50mm width_mm; ASSUMPTION: L, T, W, slot |
| tri_glide_25 | 24.0 x 33.0 x 3.2 (0.94 x 1.30 x 0.13) | 26.5 | -; ASSUMPTION: L, T, W, slot |
| tri_glide_38 | 28.0 x 46.0 x 3.6 (1.10 x 1.81 x 0.14) | 39.5 | -; ASSUMPTION: L, T, W, slot |
| zip_pull_10 | 30.6 x 11.2 x 1.6 (1.20 x 0.44 x 0.06) |  | record coil_zipper_10 chain_width_mm; ASSUMPTION: L, T, W |
| zip_pull_5 | 19.7 x 7.2 x 1.6 (0.78 x 0.29 x 0.06) |  | record coil_zipper_5 chain_width_mm; ASSUMPTION: L, T, W |
| zip_pull_8 | 26.5 x 9.8 x 1.6 (1.04 x 0.38 x 0.06) |  | record coil_zipper_8 chain_width_mm; ASSUMPTION: L, T, W |
| zip_slider_10 | 22.5 x 18.0 x 10.1 (0.89 x 0.71 x 0.40) | 9.6 | record coil_zipper_10 chain_width_mm; ASSUMPTION: L, T, W, throat |
| zip_slider_5 | 14.5 x 11.6 x 8.1 (0.57 x 0.46 x 0.32) | 6.4 | record coil_zipper_5 chain_width_mm; ASSUMPTION: L, T, W, throat |
| zip_slider_8 | 19.5 x 15.6 x 9.3 (0.77 x 0.61 x 0.37) | 8.4 | record coil_zipper_8 chain_width_mm; ASSUMPTION: L, T, W, throat |

Envelope notes: `bag_hook_38` T 6.9 includes the gate (plate 4.0); `cam_buckle` W includes the pin ends (0.4 mm each
side).

### 3.2 Other parameters

| Parameter | Value | Source |
|---|---|---|
| Stitch length | 3.0 mm (8.5 per inch) | ASSUMPTION: middle of "2.5-3.5 mm" in `designs/pack_5200/BUILD_PLAN.md` step 1. Settled by the op sheet's SPI per seam |
| Thread diameter | 0.36 mm (0.014 in) | ASSUMPTION for bonded nylon Tex 70 (the record has no diameter). Measure the cone |
| Seam allowance shown as ridge | 8 mm (0.31 in), 0.75 mm (0.03 in) proud | ASSUMPTION. Settled by the pattern release seam allowances |
| Seam type | plain seam, allowance pressed to one side, one topstitch row | ASSUMPTION: the legacy model drew every seam as external piping. Settled by the op sheet |
| Webbing thickness | 1.5 mm at 25 mm, 1.8 mm at 38 / 50 mm | ASSUMPTION (records give width and mass). Caliper on the roll |
| Zip chain width | 5.8 / 7.8 / 9.0 mm for #5 / #8 / #10 | records `coil_zipper_*` `chain_width_mm` |
| Coil pitch, monofilament, tape | 0.22, 0.10, 1.75 x chain width; tape 0.6 mm thick | ASSUMPTION. Measure the purchased chain |
| Weave pitches | 330D 0.42 mm, 840D basket 1.2 mm, 100D 0.25 mm with 4 mm grid | ASSUMPTION. Count threads on the purchased cloth |
| Printed-part layer height | 0.2 mm | ASSUMPTION. The slicer profile |
| Fabric pass amplitudes | `assets.fabric.Look`: fold 3.2 mm, hand 0.45 mm, seam dip 1.1 mm, pucker 0.55 mm, pillow 2.2 mm | ASSUMPTION, chosen by eye for 330D pack cloth. A photo of the first sewn prototype settles them |

### 3.3 The 5 mm bound (task 5)

Displacement is along the surface normal and clamped to 5.0 mm, so no vertex of a draped part moves more than 5 mm
from the huntkit drape. Measured on the B.2 build (max = distance from each displaced vertex to the refined drape):

| Part | vertices | mean slack | max move mm | RMS mm |
|---|---|---|---|---|
| corrie_body | 117 702 | 0.54 | 5.00 (0.20 in) | 1.25 |
| corrie_door | 16 653 | 0.49 | 2.50 | 0.65 |
| corrie_kick | 6 159 | 0.60 | 5.00 | 0.68 |
| corrie_bottom | 5 073 | 0.73 | 5.00 | 1.58 |
| corrie_roll | 14 019 | 0.75 (set) | 2.65 | 0.89 |
| corrie_pouch | 7 213 | 0.30 (set) | 2.88 | 0.79 |
| corrie_wing_L | 29 230 | 0.12 (set) | 5.00 | 0.58 |
| beltB_shell | 55 253 | 0.10 (set) | 5.00 | 0.82 |

"Mean slack" is the share of full wrinkle amplitude; for the four sim-draped parts it comes from the strain field
(slack 1 at 8 % in-plane compression), for the lofted legacy parts it is a set value because they have no flat
pattern. The 5.00 values are the clamp working. Taut against slack is shown in `20261110_BL018_9.png` and tested
(a 6 % slack panel has more than 3 times the RMS displacement of a 3 % taut one).

### 3.4 Render time (4 shared CPU cores, CPU only, OIDN)

| Mode | Size, samples | Seconds per frame (measured) |
|---|---|---|
| quick | 800 x 600, 16-20 | 28-57 (one macro took 61 s at 20 samples; quick is now 16 samples) |
| preview | 1200 x 900, 40 | 92-206 |
| final | 1600 x 1200, 72 | hero 334, side 273, belt 421, door 437, buckle 301, zip 308 |

The second pass of hero, belt and zip took 712, 709 and 424 s with other agents loading the same cores, so expect up to twice these times under load. Scene build (stage 1) 20-26 s; GLB 64.5 MB (scratch, `outputs/studio_work/`, not tracked). Final frames take 2 to 4
times longer than the old path (100-150 s) because the scene has 1.3 M vertices and a real backdrop.

## 4. Proof set

`outputs/screens/20261110_BL018_<n>.png` (best six copied to `docs/screens/`):

1. before / after sheet against `docs/screens/20261109_corrie_b2_1.png` and `_3.png`
2. hero, 3/4 rear on the display form
3. side, wearer's right
4. hipbelt B, front 3/4
5. horseshoe door open
6. macro: roll-top clip (25 mm side-release, wrapped webbing, box-X)
7. macro: door zip corner (#10 coil, slider, cord pull, garage, topstitched seams)
8. asset board (every hardware kind on webbing over a 330D swatch, a seam, a bartack, a zip)
9. fabric pass: taut and slack panel

## 5. Defect log

| # | Seen in | Defect | Status |
|---|---|---|---|
| 1 | first hardware board | webbing read as lengthwise stripes (herringbone phase too strong, sheen 0.7) | fixed: phase 0.9, sheen 0.25 |
| 2 | first hero | pack filled a third of the frame; flat light hid the wrinkles | fixed: "frame: pack" + zoom, key up and world down |
| 3 | first hero | body cloth washed out to pale mint | fixed: key 210 W, 330D sheen 0.22 |
| 4 | door, quick | "worm" wrinkles (slack gain 14, sharp valleys) | fixed: gain 12, wavelength 26-58 mm, softer profile |
| 5 | buckle macro | lumpy patches where the blocker mask was patchy | reduced: mask smoothed on the mesh; a mottled band is still visible under the hinge-band strap in frames 6 and 7 (open) |
| 6 | buckle macro | first camera sat behind the tripod head | fixed: left-side clip |
| 7 | test | slot test read degenerate triangles as hits | fixed in the test; slots are real openings |
| 8 | BL-002 note | dark blotches on the folded-open door (legacy lining cut through the door) | fixed: legacy lining dropped, lining rebuilt 1.2 mm inside the displaced door |
| 9 | BL-002 note | captions printed over the subject | fixed: caption band below the picture |
| 10 | belt (frame 4) | grey shard floating under the hose pocket on the form's chest | OPEN. The adapter now drops `imp6_hw` and strap-tip slivers under 80 mm, but the shard is still in the final frame, so it is another legacy harness piece; not traced |
| 11 | zip macro (frame 7), faintly in hero | a saw-tooth band of mottled surface left of the door zip, and the same mottled band under the hinge-band strap in frame 6 | PARTLY. The seam ridge that followed the mesh edges is fixed (seam lines smoothed over 24 mm). The band itself remains: where the cloth is pressed in (seam crease, strap) an inner legacy surface about 1-2 mm inside the skin shows through. Not traced to a part |
| 12 | door | three or four dark dimples high on the body left of the pouch | open: G-hook wraps of the pouch straps sit partly under the displaced cloth |
| 13 | all full views | roll-top is a tube with a spiral end, pouch a soft box, wings hemmed slabs | open: legacy lofts, section 6 |
| 14 | belt | 50 mm buckle and belt ladder locks have no webbing wrapped through them; pocket and pouch zips are still the legacy tube | open: those call sites give no strap frame |
| 15 | side | tripod, frame and under-strap hardware are the legacy shapes | open, out of this ticket's proof set |
| 16 | all | camo accents look blocky | not a defect of the render: the owner camo is a pixel design, rastered at 5.4 px/mm |
| 17 | swatch frame 9 | the seam on the slack panel is nearly hidden by the wrinkles; faint vertical ribbing near the strap on the taut panel (strap creases at 17 mm) | open, cosmetic |

## 6. Honest limits

- The "5 mm" pass cannot make folds deeper than 5 mm. Real compression straps and a rolled closure make folds of
  10-30 mm. Those need the shape itself to change (Blender's cloth solver or a finer huntkit drape with strap
  forces). That is why the roll-top and the strap cinch points still look too tidy.
- Legacy adapter: `studio.upgraded_legacy()` swaps the old block hardware and ribbons for the new assets at the old
  call sites. Where the old site gave a strap direction, the piece is threaded; where it gave only a block position
  (belt buckle, sternum buckle), the piece is placed without wraps. A concept written against `ConceptScene`
  directly does not have this limit.
- Stitches are 0.36 mm thread: they resolve in macros and at 1600 px in detail crops, not in a full-pack frame.
- Hardware internals (springs, cam teeth geometry, slider channels) are plausible, not measured.

## 7. Wearer hook (BL-019)

`studio.render(..., wearer="huntkit.viz3d.wearer:build_wearer", wearer_kwargs={...}, pack_on_torso=4x4, torso=...)`.
The callback runs inside Blender after the pack is imported; the display form is hidden, the floor drops to the
figure's boots, and pack shots frame figure and pack together. Tested with a stand-in post
(`studio.marker_wearer`) through the subprocess path. Not tested with the real figure: `wearer.py` is BL-019's and
needs its downloaded assets. Its figure is fitted to an 18.5 in torso; the legacy pack builds 15 / 19 / 23 in
harness variants only, so BL-019 has to choose 19 or bring its own fitted harness.
