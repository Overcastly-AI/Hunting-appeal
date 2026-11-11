# A hunter wearing the pack (BL-019)

Date: 2026-11-10 / 11. Code: `huntkit/viz3d/wearer.py`. Tests: `tests/test_viz3d_wearer.py`.
Sources and licences: `docs/research/human_figure_sources.md`, `huntkit/viz3d/assets/human_manifest.json`.

Every image here is a **rendered 3D figure (Blender Cycles), not a photograph**. Each caption says so.

## 1. What was built

- A parametric adult figure (MakeHuman base mesh through the MPFB 2 extension, CC0 assets) sized from ANSUR II.
- Plain clothing in solid colours from `designs/apparel/colorways.yaml`: long-sleeve mid-layer top (Lichen Stone),
  trousers (Spruce Shadow), cap (Elk Wallow), brown leather boots. **Generic: our apparel line is not designed yet.**
  The cut is the CC0 MakeHuman garment mesh, recoloured; no logo, no camo. A jacket outfit (`outfit="jacket"`) exists
  in code and was not rendered.
- CORRIE B.2 (the unchanged `huntkit.viz3d.corrie_b2` model) put on the figure: the body is aligned to the pack's back
  line and belt height, then the shoulder straps, yoke pad, sternum strap, hose, phone pocket and the whole hipbelt
  are re-fitted radially onto the clothed body and pressed into the cloth.
- Five poses: `stand` (hero), `front` (poles in hand), `side`, `walk` (uphill, poles), `kneel` (glassing).
- Two scenes: studio (BL-018's rig: `studio.setup_render`, `make_backdrop`, `make_lights`, `place_lights`, `finish`)
  and outdoor (Poly Haven HDRI "Drakensberg Solitary Mountain", grass ground, grass blades generated in code).

## 2. The wearer (owner requirement 2026-11-10: the hunter is 6 ft tall)

Default figure: a man of **1829 mm (6 ft 0 in)** stature. That is the **86th percentile** of ANSUR II men (n 4082,
mean 1756 mm, SD 68.6 mm). Every other target is the ANSUR II linear regression on stature at 1829 mm
(`wearer.ANSUR`, computed from the public CSVs; `wearer.derive_ansur` reproduces the table).

**Torso length that results: 471.6 mm (18.6 in)**, C7 to iliac crest, vertical (cervicale height minus iliocristale
height; standard error of the regression 20.2 mm). That is the 74th percentile of ANSUR men's torsos.
**Pack torso setting used: 18.5 in (469.9 mm)**, the nearest 0.5 in crown setting. Not 19 in.

| Dimension | ANSUR II at 1829 mm | Figure as built | Difference |
|---|---|---|---|
| Stature | 1829 mm (72.0 in) | 1829.0 mm | 0 |
| Cervicale (C7) height | 1583.4 mm (62.3 in) | 1583.5 mm | +0.1 mm |
| Iliac crest height | 1111.9 mm (43.8 in) | 1112.0 mm | +0.1 mm |
| **Torso, C7 to crest** | **471.6 mm (18.6 in)** | **471.5 mm** | −0.1 mm |
| Crotch height | 888.3 mm (35.0 in) | 888.6 mm | +0.3 mm |
| Waist girth at the navel | 965 mm (38.0 in) | 876 mm (34.5 in) | **−89 mm (−0.8 SEE)** |
| Waist breadth / depth | 336 / 244 mm | 318 / 225 mm | −18 / −18 mm |
| Buttock girth | 1047 mm (41.2 in) | 1025 mm | −22 mm (see note) |
| Body mass | 92.6 kg (204 lb) | not modelled | |

Notes:
- **The figure is slimmer at the waist than the ANSUR average for his height** (876 mm against 965 mm). The MakeHuman
  waist-girth morph grows the waist all round and fills the lumbar hollow, which the lumbar pad sits in, so it is
  capped (`WAIST_MORPH_MAX`). The shortfall is inside one standard error (109 mm) and is stated, not hidden.
- Buttock girth and hip breadth are measured with the legs apart (MakeHuman rest pose), so they are indicative only.
  Hip breadth read this way is 402 mm against 356 mm and is not a valid comparison.
- Age, face and skin are styling sliders (`FIGURE_LOOK`), not anthropometry.

ASSUMPTIONS in the figure:
- ASSUMPTION: the iliac crest is 5 mm above the navel (ANSUR regression values 1111.9 and 1106.8 mm at 1829 mm). The
  crest is not a surface feature of the mesh. Settles with: a palpated crest on a 3D scan of a real wearer.
- ASSUMPTION: C7 is the point on the back midline where the neck leaves the thoracic curve (mesh vertices 857 / 858).
  Settles with: the same scan.
- ASSUMPTION: "torso length" is the vertical C7 to crest distance, as the viz3d model uses it. `geometry.yaml` says
  "measured along the spine"; along the curve it reads about 10 to 15 mm longer, which would put this man at 19 in.
  Settles with: the owner's fitting instruction (tape along the spine, or two heights against a wall).

Optional variants (not rendered in this ticket):

| Variant | Sex | Stature | Torso target | Torso as built | Comment |
|---|---|---|---|---|---|
| 15 in | woman | 1597 mm (5 ft 2.9 in), 31st percentile | 381.0 mm | 381.0 mm | 15 in is the 19th percentile of ANSUR women's torsos |
| 23 in | man | 1965 mm (6 ft 5.4 in), 99th percentile | 584.2 mm | 559.7 mm (22.0 in) | **Not met.** 23 in is longer than the longest male torso in ANSUR II (546 mm); the morphs run out 24 mm short |

## 3. Fit numbers (standing pose, default wearer)

| Item | Design value | As drawn on the figure | Comment |
|---|---|---|---|
| Torso setting | 0.5 in steps, 15 to 23 in | 18.5 in (469.9 mm) for a 471.6 mm torso | 1.7 mm apart |
| Belt height | centred on the iliac crest, FCS z 120 mm | belt mid-height z 120.0 mm at the back, 119.3 mm at the sides | on the crest |
| Belt size | S to XL by waist (L = 34 to 38 in) | L; figure waist 34.5 in | padded wings end at the side of the hip on this body (see defect 4) |
| Lifter angle | 40.6° (requirement R-04: 35 to 50°) | **34° left and right** (34 to 35° in the other poses) | **below the design value; see below** |
| Head gap, neutral | 67.5 mm (2D model, 50th percentile male head) | 92 mm standing (3D, nearest pack part); 55 mm walking with 13° lean; 87 mm kneeling | not the same measurement: 3D minimum distance against a 2D sagittal gap |
| Strap and belt contact | pads touch the body | pads pressed 5 mm (straps) and 7 mm (belt) into the cloth; see section 6 for the contact fraction | by construction |
| Trunk lean | not specified | 4° standing, 13° uphill, 7° kneeling | pack rigid on the trunk |
| Back offset | back panel on the back | body brought to the display form's back line less 4 mm | touches at the tightest height |

**Lifter angle.** Before the re-fit the same measurement on the model gives 41.0° (the design 40.6°), so the method
is sound. After the straps are laid on this figure's shoulders the forward end of each lifter sits about 20 mm
higher, and the angle drops to about 34°. Either the display form's shoulder line is lower than a real 6 ft man's, or
the radial re-fit lifts the strap crown too far. This is a drawing result, not a test. It is worth one protractor
check on the first prototype on a tall wearer (R-04's own verification).

How the fit is done (`wearer.fit_pack`): about a vertical centre line (fanning out above the armpits), rays are cast
through the pads and the clothed body on a 1° by 4 mm grid. Each pad point moves along its ray by "body radius −
press − pad inner radius", so the pad keeps its thickness, its height and its angle round the body. Webbing and
hardware beyond the pads are laid on the cloth. The cloth under the pads is pushed in by the same amount with a soft
edge. Webbing that runs back to the frame is blended to stay fixed there.

ASSUMPTION: press depths 5 mm (straps) and 7 mm (belt) are visual, with no pressure or tissue model. Settles with: a
pressure-mat fit on the prototype.

## 4. Images

| File | Shot |
|---|---|
| `outputs/screens/20261110_BL019_1.png` | hero: standing, 3/4 rear, studio |
| `outputs/screens/20261110_BL019_2.png` | front 3/4 with poles, studio |
| `outputs/screens/20261110_BL019_3.png` | side profile, studio |
| `outputs/screens/20261110_BL019_4.png` | walking uphill with trekking poles, outdoor |
| `outputs/screens/20261110_BL019_5.png` | kneeling and glassing, outdoor |
| `outputs/screens/20261110_BL019_6.png` | standing 3/4 rear, outdoor |
| `outputs/screens/20261110_BL019_7.png` | fit detail: shoulders, lifters, belt, from the wearer's right rear |
| `outputs/screens/20261110_BL019_8.png` | fit detail: belt front, bottle, sternum strap |

Best five copied to `docs/screens/`: 1, 2, 4, 5, 6.

1600 × 1200, 96 samples, OpenImageDenoise, CPU. Measured with other jobs sharing the 4 cores: 130 to 450 s a frame.
Building the figure, dressing, posing and fitting the pack takes 11 to 13 s. The HDRI's sun stands 33° above the
horizon: lower than midday, not a true low sun.

## 5. Defect log

Fixed during the work:

| # | Defect seen | Fix |
|---|---|---|
| 1 | `cycles_render.build_materials` repainted the figure white | pack is imported and shaded before the figure is built |
| 2 | Belt pads and webbing buried under the shirt hem (rays stopped at the trouser waistband) | body radius taken at the outermost cloth layer within 22 mm |
| 3 | Front belt webbing cut straight through the belly | strap meshes are subdivided to 12 mm before fitting |
| 4 | The viz3d belt B is drawn open at the front (buckle on one tip, D-ring on the other) | `wearer.py` adds a 38 mm webbing band on the cloth between the wing tips; the model is unchanged |
| 5 | Waist morph filled the lumbar hollow, a barrel-shaped trunk | morph capped; girth shortfall reported in section 2 |
| 6 | Cap rim ragged; scalp showing through the crown | planar rim; crown stood off again after smoothing; frames 2, 3, 4, 5, 7, 8 re-rendered |
| 7 | Binoculars pointed at the sky, hands not on them | direction taken from the head bone; wrists placed by two-bone IK |
| 8 | Outdoor subject backlit | HDRI sun azimuth measured with a shadow-stick render; sun now 35° round from the camera |
| 9 | A Blender factory reset between poses broke MPFB | `clear_scene()` empties the file instead |

Open (visible if you look for them):

| # | Defect | Where |
|---|---|---|
| 1 | Clothing is smooth: few folds at elbows, knees and waist. No cloth simulation was run; the drape is the garment mesh plus its normal map | all frames |
| 2 | The top is a plain crew neck with no collar, zip or cuffs; trousers show a faint five-pocket jeans stitch from the normal map | close-ups |
| 3 | The face is a default MakeHuman face with no stubble or hair under the cap. It reads as a person at full-figure scale and as a 3D character in close-up | frame 8 |
| 4 | Padded belt wings end at the side of the hip, under the hanging arm, so they are hard to see from the front | frames 2, 8 |
| 5 | The cloth dent at pad edges is soft but there is no bulge beside the pad | frame 7 |
| 6 | Hands: thumbs are not wrapped round the pole grips; fingers overlap the binocular barrels slightly | frames 2, 4, 5, 8 |
| 7 | Outdoor ground beyond the grass blades is a flat textured plane and repeats | frames 4, 5, 6 |
| 8 | Kneeling: the pack and hipbelt stay rigid on the trunk; the front thigh passes close under the belt wing with no contact modelled | frame 5 |
| 9 | Pole tips and baskets are placed on the ground plane, not pushed into it | frames 2, 4 |
| 10 | Lifter angle draws at 34° (section 3) | frames 3, 7 |

## 6. Tests

`python -m pytest -q tests/test_viz3d_wearer.py`: five tests always run (spec, regression table, variants, manifest,
palette); two more run when `bpy` and the assets are present (figure dimensions against the ANSUR targets within
5 mm; pack fit: belt on the crest within 5 mm, pad contact, lifter angle, head gap). Results are in the ticket report.

## 7. How to re-run

```
BPY=<scratch>/bpyenv/bin/python                       # huntkit/viz3d/README.md, bpy 5.0.1
export HUNTKIT_HUMAN_ASSETS=<a cache folder outside the repo>
$BPY -m huntkit.viz3d.wearer fetch                    # 360 MB, checks SHA-256 against the manifest
python3 -m huntkit.viz3d.wearer model                 # outputs/pack3d_wearer/corrie_b2_wearer.glb (about 1 min)
$BPY -m huntkit.viz3d.wearer render --shots hero,front --quick     # 800 x 600 look check
$BPY -m huntkit.viz3d.wearer render --shots all       # the eight frames above
python3 -m huntkit.viz3d.wearer spec                  # the wearer's ANSUR numbers
```

For another concept:

```python
from huntkit.viz3d.wearer import build_wearer
w = build_wearer(pose="stand", glb="outputs/<concept>/<concept>.glb")     # w.objects, w.fit, w.ground
```

or through BL-018's studio layer: `studio.render(scene, shots, out_dir, wearer="huntkit.viz3d.wearer:studio_wearer",
wearer_kwargs={"pose": "stand"})` with each shot's `state.torso` set to 18.5. `studio_wearer` fits the harness and
belt meshes it finds in the scene by name and returns the pack-on-torso transform. **This hook is written against
studio.py as it stood on 2026-11-11 and has not been run end to end**; the standalone path above is the tested one.
The concept's GLB must contain the 18.5 in crown variant (`wearer.build_pack_glb` shows how).
