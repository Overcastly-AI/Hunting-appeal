# Cloth simulation of the sewn v3.1 bag (phase 1 prototype)

Owner: structural-fea-engineer, 2026-11-05. Code: `huntkit/clothsim/` (contract `docs/CONTRACTS.md` §7).
Method research: `docs/research/cloth_sim_methods.md`. Results: `outputs/clothsim/pack5200_v31_baseline/results.json`.
Viewer: `outputs/clothsim/pack5200_v31_baseline/clothsim_meat_viewer.html` (offline, huntkit.viz3d three.js).

```
python -m huntkit.clothsim.cli validate                      # analytic checks + PNG
python -m huntkit.clothsim.cli run                           # coarse bag, all cases (~7 min), GLB, PNGs
python -m huntkit.clothsim.cli run --scenario huntkit/clothsim/scenarios/pack5200_v31_wide_gores.yaml --no-sweep
python -m huntkit.clothsim.cli diff outputs/clothsim/pack5200_v31_baseline/results.json \
                                    outputs/clothsim/pack5200_v31_wide_gores/results.json --png diff.png
```

## 1. What the sim does

1. **Pieces.** It reads the real v3.1 body pieces from `designs/pack_5200/patterns_v31.py` `build_body`, the same
   code that wrote `outputs/release/pack5200_v3.1_patterns`. The file is only read, never edited, and the pieces are
   cached. The pieces are B-01, B-01b, B-01u, B-02a to B-02d (the diagonal zip counts as a seam, plus the 2 darts),
   B-03 R and L, B-05 and B-06. B-06 is the collar, modelled up to the fill line.
   Each flat pattern is triangulated in its own plane (coarse h = 40 mm: 846 nodes, 1688 triangles; `--fine` uses
   h = 25 mm). The flat shape is the rest state of every triangle.
2. **Sewing.** Seams are joined by notch position. Both sides of a seam take the same points on the master surface,
   which is exactly how the pattern's 50 mm notches pair them. The sewn bag comes out closed: 33 seam groups,
   **0 open boundary segments**, 0 missing edges.
3. **Fabric.** Each triangle is an orthotropic membrane (CST, Green strain), with warp along the piece's grain
   arrow. Shear and bending are low, and the cloth goes slack in compression, which is how wrinkles show up.
   Stiffness is break strength over break elongation (`huntkit/clothsim/fabrics.yaml`):

   | material | k warp / weft N/mm | shear N/mm | bending N mm | basis |
   |---|---|---|---|---|
   | cordura_330d_nylon66 | 128 / 85 | 1.0 | 0.10 | record grab / 31.25 mm; 25 / 30 % elongation ASSUMPTION |
   | cordura_500d_nylon66 | 198 / 123 | 1.5 | 0.20 | as above |
   | robic_100d_ripstop | 70 / 48 | 0.5 | 0.03 | as above |
   | challenge_ultra_200 | 1500 / 1500 | 15 | 0.25 | ASSUMPTION: no tensile data in the record (60 N/mm at 4 %) |

4. **Loads and supports.**
   - Gravity on the fabric (169.5 g of modelled cloth).
   - Contents: polytropic packed fill, p = p_pack (V_c/V)^3. The gear resists being squeezed.
   - Granular gear weight by Janssen: lateral p_h = K p_v with μ 0.4 and K 0.4 (ASSUMPTION). The rest of the weight
     sits on the floor.
   - Meat: HA-LS-1 rev B §4.1 at 1.0 g. 70 % of the meat weight goes into the frame-half of the floor. The face
     pressure on B-01 over the spreader width at z 60 to 330 is 6 × 150 N cinch plus the overturning pulls
     10 / 47 / 96 N, so 1052 N. The other 30 % goes by friction straight into the IM strap anchors, so it never
     reaches the cloth.
   - Rigid one-sided contact with `genframe_assembled.stl` and the spreader `genframe_barrier.stl`, using a
     smooth gap field.
   - Hinge eyes: stiff pins at z 60.
   - Bag hooks at IM2 and IM3: 38 mm hook straps, tension-only.
   - Under-straps US1 and US2: 150 N cammed. Wraps W1 to W3: 80 N.
   - Every strap is cinched by the owner on the loaded bag, then behaves as elastic webbing with a 3 % cinch take-up
     (ASSUMPTION).
5. **Solve.** Static equilibrium by damped Newton on the total potential energy, with load ramps 0.25, 0.5 and 1.0
   and then a re-cinch step.

## 2. Validation (before using it): `outputs/screens/20261105_clothsim_1.png`, tests in `tests/test_clothsim.py`

| check | closed form | sim error |
|---|---|---|
| Inflated closed cylinder R 100, 5 kPa: hoop tension | p r | **−0.14 %** |
| same: axial tension | p r / 2 | **−0.19 %** |
| same: **longitudinal seam line force** (welded-node method used on the bag) | p r | **−0.5 %** |
| same: end-cap seam line force | p r / 2 | **+2.3 %** (coarse cap rim) |
| same: radius growth | R (1 + p R / k) | 0.000 % |
| Hanging sheet (catenary), span 400, length 500: sag | a (cosh(S/2a) − 1) | **+0.04 %** |
| same: horizontal tension / vertical reaction | w a / w L/2 | −0.01 % / 0.00 %; shape error 0.04 mm |
| Flat-pattern area: mesher vs polygon (dart notch) | exact | 0.000 % |
| Draped sheet, 3D area / flat area | 1 | −0.02 % |
| Every energy term: gradient vs finite difference | | < 2e-4 relative |
| Sewn bag, sewn area / flat area (meat case) | ≈ 1 (slack allowed) | −1.8 % (the slack, wrinkled cloth) |

`python -m pytest -q`: 264 passed, 1 skipped. The skipped one is the optional full-bag smoke test (`CLOTHSIM_FULL=1`).

## 3. Results on the v3.1 bag (coarse mesh)

Cases: (a) `empty`, hanging, 0.05 kPa of loft. (b1) `packed`, 0.5 kPa, no weight. (b) `fill`, 68 kg rated
(HA-LS-1 C1) granular. (c) `meat`, 30 kg meat on IM1 to IM3 plus 38 kg of gear, so 68 kg total, at 1.0 g.

### 3.1 Filled volume (`20261105_clothsim_5.png`, right)

| | closed at the fill line | body below the collar seam |
|---|---|---|
| design (`build_geometry`) / release pattern check | 85.1 L / 85.0 L (5188 cu in) | as drafted on the master surface: 59.9 L |
| sewn bag, 0.25 / 0.5 / 1 / 2 kPa packing (no weight) | **86.0 / 86.5 / 86.9 / 87.5 L** (5250 to 5340 cu in) | 62.5 / 62.8 / 63.1 / 63.5 L |
| `packed` (0.5 kPa, on the frame, under-straps cammed) | 87.2 L | 63.6 L |
| `fill`, 68 kg / `meat` | 83.6 / 83.7 L (5100 cu in) | 59.6 / 59.8 L |

- **The sewn bag holds about 86 to 87 L to the fill line, +1 to +3 % over the 85 L target.** The panels round out
  past the drafted shape. The body gains 4 to 6 % over its drafted volume, at 0.5 to 2 % warp/weft strain.
- Under 68 kg the volume drops by about 3 L (to 83.6 L), because the floor tucks in and the straps squeeze the bag.
- The fill-line closure is idealised as a flat seam (front half on back half). Rolling three times takes up the
  150 mm above it, so the ±1 L between runs (non-unique slack states) is the honest error bar.

### 3.2 Shape and profile under the meat load (`20261105_clothsim_2.png`, `_6.png`, `_5.png` left)

- **The upper bag leans aft.** The B-01 face stays on the spreader up to about z 520 (the IM3 hooks). Above that,
  the bag peels off the frame face. Its aft-most point goes from 339 mm (drafted) to **438 mm (meat)** and
  **469 mm (fill)**, and the top drops from z 1101 to about z 1000. The W3 crown wrap at 80 N barely holds it:
  its tension stays near 20 N because the strap path shortens as the top folds aft.
- The floor sags **71 mm (meat) / 82 mm (fill)** below z 35 between the hinge pins and the under-straps. The
  cammed under-straps relax from 150 N to 19 to 47 N as the floor finds its shape.
- The contents CG is **206 mm aft, z 542 (meat)** and 223 mm aft (fill). HA-LS-1 uses 150 mm (meat) and 180 mm
  (carry). The soft, leaning bag puts the CG further aft than the frame load standard assumes (see section 5).

### 3.3 Strain hot spots and wrinkles (`20261105_clothsim_3.png`)

- Yarn strains are small everywhere: warp at most 1.7 % and weft at most 6.1 %, both on the floor at the hinge
  eyes. Large principal strains (12 to 19 %) are **trellis shear** (up to 39 to 52°). They sit in the **lower
  side gores B-03 R/L at z 50 to 160, next to the hinge-pin corners**. That is where the floor, frame panel and
  gore meet, and the floor is pulled out sideways while the corner is held at the pin. On the real bag this area
  will show diagonal wrinkles and seam twist at the bottom corners.
- Slack / wrinkle-prone area (minimum principal strain < −2 %) under the meat load:

  | piece | B-05 | B-03 L / R | B-02b | B-02d | B-06 | B-02a | B-01 | B-01b, B-01u |
  |---|---|---|---|---|---|---|---|---|
  | slack area | 79 % | 73 / 66 % | 56 % | 52 % | 47 % | 16 % | 9 % | 0 % |

  The floor puckers between its supports. The gores take the shortening. The upper face B-02d (the dart panel)
  wrinkles around the darts. The collar is slack (it gets rolled). The frame panel stays smooth on the spreader.

### 3.4 Seam line force vs seam strength (`20261105_clothsim_4.png`)

Seam strength = min(1.5 × 64 N / 3.5 mm = 27.4 N/mm for Tex 90 301, 0.8 × weaker strip strength). On the
330D seams the fabric governs at 20.5 N/mm, on the collar (100D) at 11.5 N/mm.

| seam (meat case peak, ends and attachment nodes excluded) | N/mm | strength | SF at 1.0 g | SF / 3.0 (C5 2.0 g × 1.5, linear) |
|---|---|---|---|---|
| B-01 \| B-05 (frame panel / floor) | 1.38 | 27.4 | 19.8 | 6.6 |
| **B-03L \| B-05 (gore / floor)** | 1.05 | 20.5 | **19.5** | **6.5** |
| B-03R \| B-05 | 0.97 | 20.5 | 21.0 | 7.0 |
| B-01 \| B-01b, B-01b \| B-01u (setback and shoulder seams) | 0.75 | 27.4 | 37 | 12 |
| B-01u \| B-06 (collar seam, 100D side) | 0.31 | 11.5 | 37 | 12 |
| every other body seam | < 0.43 | 20.5 | > 48 | > 16 |

- The highest *flagged* value is **6.3 N/mm at the hinge-eye node** on B-01 | B-05 (SF 4.4 at 1 g, 1.5 at
  3.0 × rated). In the sim that load lands on one node; on the bag it goes into the eye bartack and reinforcement.
  The number depends on the mesh and is not a seam result. **The hinge-eye reinforcement must spread ~375 N
  (meat, 1 g) over ≥ 60 mm of seam to stay under 6 N/mm.**
- The fill seams are the same size: 0.93 N/mm peak, B-03L | B-05, SF 22.

### 3.5 Bag on the frame and spreader

- The spreader carries the bag: **979 N** in the meat case. That is the meat face load minus friction, which the
  sim leaves out. Contact covers **95 %** of the B-01 footprint (581 of 770 cm²), so it bears well, at a mean
  **17 kPa**. That is above the 13 kPa peak in `spreader.md`, which comes from a different model; see section 5.
  The frame tubes take only 32 N.
- **Design flag:** the drafted B-01 surface sits **up to 3.1 mm inside the spreader face** (32 nodes). The fabric is
  pushed aft on assembly, so B-01 should be drafted ~3 to 4 mm further aft, or the spreader setback checked.
- Attachment forces (meat, 1.0 g), against capacity:

  | attachment | force | capacity (ASSUMPTION ratings) | SF at 1 g |
  |---|---|---|---|
  | hinge eyes R / L | 375 / 310 N | 2700 N box-X bartack | 7.2 / 8.7 |
  | IM3 bag hooks R / L | 338 / 319 N | 1500 N hook | 4.4 / 4.7 |
  | IM2 bag hooks R / L | 74 / 168 N | 1500 N | 20 / 9 |
  | under-straps US1 / US2 | 45 / 19 N | 1100 N cam | > 24 |
  | wraps W1 / W2 / W3 | 12 / 19 / 18 N | 300 N ladder lock | > 15 |

  At HA-LS-1 C5 (2.0 g × 1.5 = 3.0 × these, linear), the **IM3 bag hook comes to 1.5 SF** and the hinge bartack
  to 2.4. **The IM3 hook is the critical bag-to-frame part, not a seam.** That fits the open hook proof test in
  `meat_haul_modes.md`.

### 3.6 Panel-adjustment example (`20261105_clothsim_7.png`, `outputs/clothsim/diff_wide_gores.md`)

Both B-03 gores were cut 4 % wider (`panels: {B-03: {scale_weft: 1.04}}`) and sewn to the unchanged floor and
collar, so the extra width eases in. Results for the meat case:

- volume +0.99 L (body +0.95 L), aft depth +4 mm
- gore warp strain 1.69 % to 1.64 %; peak gore/floor seam force −2 %
- IM3 hook forces −2 %
- gore slack area up (more ease, more wrinkles)

The workflow is: change the YAML, `run`, `diff`.

## 4. What the sim can and cannot predict (honest limits)

It **can** predict:
- the shape of the sewn bag from the real flat pattern, and its volume (±1 L)
- where yarn strain and shear concentrate
- where the cloth goes slack (wrinkle-prone)
- statically balanced seam line forces (the cylinder check matches p r to 0.5 %)
- how load splits between hinges, hooks, straps, spreader and frame
- before/after trends for a panel change

It **cannot** predict:
- **Stitch slip, seam slippage, needle-hole tear, thread abrasion or seam opening.** A seam is a perfect weld.
- **Fabric creep, relaxation, hysteresis, wet strength or UV ageing.** The fabric is linear elastic, with secant
  stiffness from break data and ASSUMPTION elongations, and Challenge Ultra 200 has no tensile data at all. Strain
  numbers are ±50 %. Seam forces depend on load balance and barely on stiffness.
- **Self-contact.** Panels can pass through each other. The empty bag is held open with 0.05 kPa because the sim
  cannot show how an empty bag collapses or folds.
- **Contents mechanics.** Gear is a polytropic gas plus a Janssen lateral pressure, with μ, K and n all
  ASSUMPTIONS. Real gear has shape and stiffness and hangs partly on the walls. Meat is the HA-LS-1 load set, not
  a modelled body.
- **Friction.** None at the spreader, the straps or the gear. Straps slide freely through the bag nodes they
  pass. Real straps would hold the top in better.
- **The roll itself.** The roll, the HDPE stiffener and the roll clips are not modelled. The closure is a flat seam
  at the fill line.
- **Features left out:** swells, ports, sleeve, pockets, band, binding, zip tape stiffness, foam. Point loads at
  hinge/hook nodes are mesh-dependent, as section 3.4 says.
- **Convergence.** The bag cases stop at a residual of 1.5 to 9 N per node (tolerance 0.5 N, against about 40 N
  of seam force per node). The slack cloth has many nearly free states. `results.json` `solve` lists every stage.
  Global numbers are good to about ±2 %. Single-node peaks are worse.
- Dynamic loads (stumble, drop) are not simulated. The 3.0 × factor above is a linear scale-up.

## 5. Recommended actions

1. **IM3 bag hooks**: these are the critical attachment, at SF 1.5 at C5 if the 1500 N rating holds. Proof-test
   them, as already planned, and consider a bag-side tab spreading the hook load over ≥ 80 mm of B-01.
2. **Hinge-eye reinforcement**: spread about 375 N per eye (1 g) over ≥ 60 mm of the B-01/B-05 seam with a
   Hypalon or 500D doubler, to cut the gore-corner shear wrinkles.
3. **Top of the bag**: give the frame panel a top attachment, such as a crown tab or a stiffer W3 path. The bag
   above IM3 leans aft by about 100 mm and moves the load CG to 206 to 223 mm aft, beyond HA-LS-1's 150 / 180 mm.
   The pack-designer should take this up, and the frame cases should be re-checked with the larger CG offset.
4. **B-01 vs spreader interference**: 3.1 mm. Re-check the B-01 draft offset against the spreader face.
5. **Seams**: all body seams are SF ≥ 19 at 1 g and ≥ 6.5 at the 3.0 × C5 factor. Tex 90 at 3.5 mm is
   adequate; seam mass cannot be cut further by thread choice.
6. The sim needs measured fabric tensile curves (warp, weft, bias) for the four fabrics, and a Challenge Ultra 200
   tensile test, before its strain numbers are used for sizing.

ASSUMPTION list (also in `huntkit/clothsim/fabrics.yaml` and `scenarios/pack5200_v31.yaml`):
- grab strength ≈ 1.25 × a 25 mm strip
- break elongations
- shear, bending and compression fraction 0.01
- seam efficiency 0.8
- Tex 90 at 3.5 mm on every body seam
- 0.5 kPa packing pressure, polytropic n = 3, Janssen μ = K = 0.4, gear weight on the floor
- cinch tensions 150 / 80 N and 3 % cinch take-up
- hinge pin stiffness 200 N/mm; hook strap 70 mm below the eye
- W3 anchors at (±115, 0, 702.6)
- empty loft 0.05 kPa
- hardware ratings taken from geometry.yaml
