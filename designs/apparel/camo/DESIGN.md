# Cirquefall camo family + solid colorway system — design rationale

Owner: camo-designer · Engine: `huntkit/camo/` · Specs: `designs/apparel/camo/*.yaml` ·
Solids: `designs/apparel/colorways.yaml` · Previews: `designs/apparel/camo/previews/` ·
Print files: `outputs/camo/` (regenerate with `python -m huntkit.camo.cli all`).

All numbers below come from `previews/<pattern>_metrics.json` (made by
`huntkit.camo.export.analyze`), unless marked `ASSUMPTION:`.

## 1. Product direction

The line is mostly **solid** garments and pack, with camo used as **accent panels**: shoulder
yokes, forearms, side and underarm panels, knee and seat panels, pack lid, side pockets and
hipbelt wings. The look should be light, rugged, edgy and functional, not full-coverage camo.
So the family has two scales:

| Pattern | File | Repeat (W×H) | Use |
|---|---|---|---|
| **Cirquefall** | `cirquefall.yaml` | 760 × 760 mm | full-fill garments and big panels, multi-season western mountain |
| **Cirquefall Shard** | `cirquefall_shard.yaml` | 380 × 380 mm | **accent panels** (150–400 mm), same rules with all lengths ×0.5 |
| **Cirquefall Firn** | `cirquefall_firn.yaml` | 760 × 760 mm | late season / snow transition, full-fill |
| **Cirquefall Firn Shard** | `cirquefall_firn_shard.yaml` | 380 × 380 mm | late-season accent panels |

ASSUMPTION: the 760 mm horizontal repeat gives 2 repeats across 1520 mm print width. The
380 mm accent repeat gives 4 repeats across, and it divides a 760 mm drum or screen evenly.
Both are exactly periodic in x and y (FFT noise and toroidal Voronoi), so tiling has no seam
(see `*_tile2x2.png`, where the red ticks mark the repeat joins, and `tests/test_camo.py`).

## 2. Originality

Cirquefall comes entirely from our own procedural rules: periodic, domain-warped
Voronoi "talus slabs", FFT fractal tone fields, Voronoi fracture lines, and a two-scale
fleck layer, all with fractal edge roughness. Nothing was traced from, sampled from, or
tuned to look like a commercial pattern. It isn't digital or pixelated, it isn't a
topographic contour pattern, it isn't a branch or leaf photo-realistic pattern, and it isn't
built from optical gradient bands. The visual idea is **fractured flagstone and talus
plates with lichen flecks**, which is rock rather than foliage. The palette names and the
"HA xx-xxxx" codes are our own internal identifiers.

## 3. How the pattern is built (macro + micro)

The engine (`engine.py`) gives every layer a scalar field built at a fixed field resolution
(1.25 px/mm full scale, 2.0 px/mm accent), so the pattern looks identical at every output DPI:

1. **Macro (230–520 mm at full scale; ×0.5 for Shard).** A periodic Voronoi tessellation
   (`cell_mm: 230`, jitter 0.9) gives each cell a random tone, and a 420 mm fbm tone field is
   blended in. A gentle domain warp (`amp_mm: 30`) keeps the slab edges *angular but not
   geometric*. Four macro layers (light *granite*, *sage*, *grass*, dark *spruce*) threshold
   that shared field. The dark layer uses the *negated* light field, so light and dark masses
   always sit opposite each other, which maximizes the macro luminance edge.
2. **Mid: fractures.** The *basalt* layer is `exp(-(F2−F1)/8 mm)` on the same tessellation,
   so the darkest ink runs along slab boundaries like shadowed cracks. Fractures are
   modulated toward the dark masses (shadows pool there). This layer outlines the macro
   shapes, so the slab edges stay readable as distance grows.
3. **Micro (5–38 mm).** Dark flecks are clustered *inside the light slabs*, and light flecks
   *inside the dark masses* (`modulate` on the macro field). Inside each macro shape this adds
   strong local contrast, which averages out to the macro tone once the observer can no
   longer resolve it. That's the hand-off from micro to macro.
4. **Edges.** A small-scale fbm (3–16 mm) is added before thresholding, so every boundary is
   fractal rather than smooth. The result is upsampled with a periodic Catmull-Rom
   resampler, so 300 dpi edges are clean, not stair-stepped.
5. **Exact coverage.** Thresholds are solved top-down, so each ink's *visible* share matches
   the spec. The max abs error is 0.0013 (Cirquefall), 0.0029 (Shard) and 0.0007 (Firn).
6. **Flat inks.** Output contains only palette colours (one screen or separation per ink;
   SVG separations are in `outputs/camo/*_separations.svg`). The optional `micro_texture`
   tonal grain is OFF, because it would break flat separations. It's meant for digital
   sublimation only.

## 4. Palettes and luminance distribution

**Cirquefall** (6 inks). Coverage shows the visible share. L* is the D65 value; L*u is the
ungulate-simulated value.

| Ink | Hex | Coverage | L* | L*u |
|---|---|---|---|---|
| Scree Dust | #9F9888 | 18 % | 63.0 | 62.7 |
| Granite Fleck | #BEB9AC | 19 % | 75.2 | 75.0 |
| Krummholz Sage | #6E745B | 20 % | 47.7 | 48.0 |
| Cured Grass | #A08A68 | 12 % | 58.6 | 57.7 |
| Spruce Shadow | #4A4B3C | 24 % | 31.4 | 31.4 |
| Basalt Ink | #2D2B27 | 7 % | 17.6 | 17.5 |

Luminance bands: **dark (L*<40) 31 %, mid 32 %, light (L*≥60) 37 %**. The coverage-weighted
mean L* is 51.0 and the mean colour is #898473. The ink L* values span 17.6 to 75.2, roughly
evenly spaced (about 10–16 L* steps), so the pattern has a full tonal ladder rather than
clustering in the mids. Mid-tone camo turns into a flat blob at distance.

**Cirquefall Firn** (5 inks): Firn #D5D6D0 (L* 85.4, 32 %), Wind Slab #A9ACA6 (70.0, 24 %),
Frost Sage #80867A (55.1, 16 %), Bare Timber #5A5348 (35.7, 22 %) and Basalt Ink (17.6, 6 %).
Bands are **dark 28 %, mid 16 %, light 56 %**, with mean L* 61.8. Snow is never pure white;
Firn is L* 85 to avoid glare and specular "white patch" signatures. The macro tone field is
stretched horizontally (aniso 1.5), so light masses read as wind bands and snow on ledges.

## 5. Dichromat (ungulate) contrast analysis

**Model** (`color.py`): deer and elk have S (~455 nm) and M (~537 nm) cones and no L cone.
The closest human analogue is therefore *protanopia* (L missing), not deuteranopia, because
the deer M cone sits within a few nm of the human M cone. We apply the Viénot, Brettel &
Mollon (1999) protanope projection in LMS space. The approximation is stated honestly: it
ignores the 455 vs ~440 nm S-cone shift, UV sensitivity (RGB has no UV channel, which is
handled by the no-OBA spec), and rod vision. It's a *screening* tool. Physical lab dips need
spectral (UV-VIS-NIR) checks.

**Result: no ink pair collapses** (ΔE00 < 5 in the ungulate sim) in any palette. These are the
key Cirquefall pairs (ΔE00 human → ungulate, Michelson luminance contrast in the ungulate sim):

| Pair | ΔE00 human | ΔE00 ungulate | Michelson (ungulate) |
|---|---|---|---|
| sage / grass (green vs tan, the classic red-green risk) | 16.6 | **10.1** | 0.21 |
| scree / grass | 8.8 | 8.2 | 0.10 (weakest pair) |
| scree / granite | 9.7 | 9.8 | 0.21 |
| sage / spruce | 14.9 | 14.8 | 0.42 |
| spruce / basalt | 11.8 | 11.4 | 0.48 |
| granite / spruce (macro light vs dark) | 42.8 | 42.4 | **0.75** |
| granite / basalt | 55.8 | 55.6 | 0.91 |

Design decision: in an early draft, sage (#767C63) and grass (#937E5E) were only ~2 L* apart,
and in the ungulate sim they nearly merged. We pushed them apart in *luminance* (sage L* 47.7,
grass L* 58.6), so the pair still separates by ΔE00 10 for a dichromat. That's the general
rule here: **every ink pair has to differ in luminance, not just hue.** Because the palette is
low-chroma earth tone, the ungulate sim changes it only slightly (pair ΔE00 human vs ungulate
differs by under 3 except sage/grass). That's intended: nothing in the pattern depends on
red-green hue contrast that a deer can't see.

Firn's weakest pair is firn/windslab: ΔE00 10.9, Michelson 0.24.

**Habitat match** (pattern mean vs ASSUMPTION reference backgrounds in `color.BACKGROUNDS`,
ΔE00 in ungulate sim). Cirquefall: sagebrush **1.8**, talus/scree 6.7, dry bunchgrass 8.0,
late aspen bark 14.3, dark timber 24.3. Firn: talus 5.1, late aspen bark 5.1, sagebrush 10.7,
shaded snow 12.4. The open-country mean match is very close. In dark timber, the dark inks
(spruce and basalt, about 31 % of area) carry the pattern rather than the mean.

## 6. Distance behaviour

`vision.py` blurs in linear light to the acuity limit, then resamples at the observer's
Nyquist spacing. ASSUMPTION: ungulate acuity is 6 cpd (about 20/100); human is 30 cpd; haze is
not modelled. The ungulate cycle is 29 mm at 10 m, 145 mm at 50 m, 436 mm at 150 m and 873 mm
at 300 m. Values below are RMS luminance contrast of a ≥1.5 m patch. The ungulate column uses
deer acuity and deer colour.

| Distance | Cirquefall human | Cirquefall ungulate | Shard ungulate | Firn ungulate |
|---|---|---|---|---|
| 0 m | 0.67 | 0.67 | 0.67 | 0.64 |
| 10 m | 0.54 | 0.44 | 0.38 | 0.43 |
| 50 m | 0.44 | 0.35 | 0.25 | 0.34 |
| 150 m | 0.38 | 0.24 | 0.10 | 0.21 |
| 300 m | 0.34 | 0.11 | 0.01 | 0.08 |

How to read this:
- **5–50 m (micro):** the flecks fall below the deer's resolution by about 10–20 m and merge
  into the macro tones. That's when internal contrast drops from 0.67 to 0.44.
- **50–150 m (macro):** the 230 mm slabs and fractures keep 0.24–0.35 RMS contrast on the
  full-scale pattern. This is the shape-breaking scale.
- **Accent (Shard) at range:** a 380 mm periodic pattern averages to its mean beyond about
  150 m (0.01 at 300 m). That's expected and intended. **At range, the silhouette break for
  the accent system comes from the panel layout** (solid body blocks against camo yokes,
  forearms and sides), not from inside the print. See the "Talus jacket on sagebrush" rows in
  `previews/cirquefall_shard_distance.png`. At 50–150 m the yoke and side panels still split
  the torso into separate tonal blocks. At 300 m, the Krummholz Sage body reads as a slightly
  darker block on sagebrush (solid vs sagebrush ΔE00 9.0 in the ungulate sim). For sage and
  grass country, the Scree Dust (ΔE00 5.3 vs sagebrush, 2.8 vs talus) or Cured Grass (1.7 vs
  dry bunchgrass) bodies are the better field picks. Spruce Shadow (2.8 vs dark timber floor)
  suits timber.

## 7. Accent scale: why Shard exists

Panel test (`export.panel_test`): 400 random square windows per size. A "flat blob" means one
ink covers more than 70 % of the window.

| Window | Cirquefall (760) blob fraction | Shard (380) blob fraction | Shard median inks ≥5 % |
|---|---|---|---|
| 150 mm | **9.5 %** | **0 %** | 5 |
| 250 mm | 0 % | 0 % | 6 |
| 400 mm | 0 % | 0 % | 6 |

Firn: 12.5 % at 150 mm for full scale, 0 % for Firn Shard. At full scale, about 1 in 10 small
panels (forearm, hipbelt wing) would land inside one slab and read as a mismatched solid. At
accent scale, every 150 mm panel holds 1–2 slab facets, a fracture line, flecks and five inks.
Use **Shard on any panel under ~400 mm**; use full scale only on panels over ~400 mm or on
full-fill garments.

## 8. Solids and camo as one system

`colorways.yaml` defines 6 solids. **Every solid is also an ink in the camo** (identical hex),
so a camo panel seamed to a solid body shares a colour across the seam, and the transition
looks intentional:

| Solid | Hex | L*a*b* | In camo |
|---|---|---|---|
| Scree Dust | #9F9888 | 63.0 −0.3 9.3 | Cirquefall (background ink) |
| Wind Slab | #A9ACA6 | 70.0 −2.2 2.7 | Firn (background ink) |
| Krummholz Sage | #6E745B | 47.7 −7.0 13.1 | Cirquefall |
| Cured Grass | #A08A68 | 58.6 3.2 21.3 | Cirquefall |
| Spruce Shadow | #4A4B3C | 31.4 −3.4 8.8 | Cirquefall (dark mass) |
| Basalt Ink | #2D2B27 | 17.6 0.0 2.9 | all (fracture ink); trim only |

`accent_pairings` gives each body + accent + trim + thread combination:
- **Talus:** Sage body + Shard, Basalt trim.
- **Scree:** Scree Dust body + Shard, Spruce trim.
- **Timber:** Spruce body + Shard, Basalt trim.
- **Firnline:** Wind Slab body + Firn Shard, Basalt trim.

Thread matches the body, because the contrast should come from the seam *geometry*, not from
topstitching. The dye-lot QC tolerance is ΔE00 ≤ 1.0 (panel-to-panel ≤ 0.6, |ΔL*| ≤ 0.7 on
darks). **No optical brighteners** are allowed anywhere in the chain, verified with a 365 nm
lamp check per lot.

## 9. Design language: faceted, functional accent geometry

The edgy look comes from **seam lines that do work**, not from decoration. Rules for the
pattern-maker and apparel-designer (shown in `previews/accent_mocks_jacket_pack.png`):

1. **Shard panels, never rectangles.** Accent panels are bounded by straight cuts at 15–40°
   to the grain, meeting at chevron points. No curved "swoosh" boundaries and no
   symmetric-logo shapes. The straight cuts echo the angular Voronoi slab edges inside the
   print.
2. **Asymmetric diagonal yoke.** The shoulder yoke's lower edge is a broken diagonal that
   drops lower on one side (a 150 mm vs 175–205 mm drop, with a chevron notch off-centre).
   *Function:* it moves the shoulder seam off the pack-strap pressure line, and the yoke can
   be a tougher face fabric where straps abrade.
3. **Forearm chevrons = articulation.** The forearm accent is a chevron whose apex sits at
   the elbow bend. *Function:* the chevron seam carries the pre-bent elbow dart (two
   straight seams replace a curved dart), and the panel can be a higher-abrasion fabric
   (glassing on rocks, crawling).
4. **Side and underarm shards = gussets.** Long tapered shards under the arm and down the
   side. *Function:* stretch or air-permeable side panels for venting and reach; the taper
   means no seam crosses the hipbelt zone.
5. **Knee and seat panels (pants).** A diamond knee shard whose upper and lower points carry
   the knee articulation darts, and a seat shard with its point at center back. *Function:*
   abrasion reinforcement where you kneel and sit, cut on the same angles as the jacket so
   the system reads as one family.
6. **Pack.** The lid, side pockets and hipbelt wings are camo, so the parts that sit on the
   pack's silhouette edges break its outline. A diagonal front shard runs parallel to the
   compression straps. The base is Basalt Ink as an abrasion overlay. *Function:* all camo
   parts are separate panels anyway (lid, pockets, wings), so camo costs no extra seams.
7. **Hem dart line.** A single asymmetric diagonal seam on the lower front (visible in the
   mock) can carry a hem-shaping dart or a hand-pocket bag edge.
8. **Seam colour.** Panel seams are drawn in the trim colour in the mocks. In production,
   expose them only where they're functional (taped or bonded seams in trim colour on
   shells); otherwise thread matches the body.

ASSUMPTION: mock silhouettes are approximate men's L flat views, for visual
communication only. Real panel geometry belongs to the pattern-maker (`huntkit/patterns`).

## 10. Files

| What | Where |
|---|---|
| 300 dpi seamless repeat TIFF (LZW) + PNG, per pattern | `outputs/camo/<pattern>_repeat_300dpi.{tif,png}` |
| SVG vector separations (one group per ink) | `outputs/camo/<pattern>_separations.svg` |
| 72 dpi repeat preview | `previews/<pattern>_repeat_72dpi.png` |
| 2×2 seamless proof | `previews/<pattern>_tile2x2.png` |
| Dichromat preview (human / ungulate / ungulate luminance) | `previews/<pattern>_dichromat.png` |
| Distance series 0/10/50/150/300 m (human + ungulate) | `previews/<pattern>_distance.png` (Shard version also includes the jacket-on-sagebrush mock) |
| Metrics JSON | `previews/<pattern>_metrics.json` |
| Swatch card (camo inks + solids, with ungulate chips) | `previews/palette_swatch_card.png` |
| Accent mocks (jacket + pack × 4 pairings) | `previews/accent_mocks_jacket_pack.png` |
| Full-fill jacket mock | `previews/fullfill_jacket_mock.png` |

CLI: `python -m huntkit.camo.cli render <pattern> [--dpi 300] [--out DIR] [--no-tiff] [--no-svg]`,
`swatches`, `mocks`, `analyze <pattern>`, `all`.

## 11. Open items

- Get lab dips on the chosen base fabrics. Replace design targets with approved LAB values,
  and run UV-VIS-NIR reflectance on dyed or printed swatches. Check the NIR signature: dark
  inks should not be NIR-black (a common sublimation problem), but that's a physical test and
  can't be measured from RGB.
- Field-photo validation: replace `color.BACKGROUNDS` (an eyeballed ASSUMPTION) with measured
  backgrounds from calibrated photos.
- Confirm with the printer whether the 380 mm accent repeat or a 760 mm drum holding 2×2
  accent repeats is cheaper.
