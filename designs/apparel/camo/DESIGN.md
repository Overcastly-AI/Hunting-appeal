# Hunting-Appeal camo — design rationale

## 0. Owner Base (primary)

> **STATUS: REAL FILE (2026-11-04).** The owner's master SVG (`source/owner_base.svg`, PR #1)
> is ingested by `load_owner_base()` (source `svg`, cairosvg back end). Every number and image in
> this section is measured on the real artwork. The procedural proxy (`owner_base_proxy`) is
> retired for design use and kept only as a test fixture and fallback. Proxy-era numbers are kept
> for comparison in `owner_base.yaml › real_vs_proxy`.

Decision (DECISIONS 2026-11-01): the owner's 4-colour SVG is the **primary** camo. Cirquefall
(sections 1–11 below) is the **alternate**. Garments stay mostly solid, with Owner Base on the
same shard/chevron accent panels as before.

**Files.** Spec: `owner_base.yaml`. Pipeline: `huntkit/camo/owner_base.py`. Previews and
metrics: `huntkit/camo/owner_export.py`, which writes `previews/owner_base_*.png`,
`owner_base_metrics.json` and `owner_base_scale_study.json`. Print TIFFs go to
`outputs/camo/owner_base_{full_760,accent_380}mm_300dpi.tif` (8976 px and 4488 px square,
LZW, 4 flat inks; not tracked).

### 0.1 Ingestion pipeline
1. **Parse.** The parser reads `<rect>/<path>/<polygon>` in paint order, along with
   fill/style, fill-rule and translate/scale/matrix transforms. Path data uses straight
   segments only: M/L/H/V/Z, absolute and relative, with implicit lineto and several
   subpaths per path (`M..L..zM..`). Curves raise an error.
2. **Rasterise at any DPI.** If cairosvg is available (it is installed here) it is used,
   with crisp edges and an inherited even-odd fill. Each pixel is then snapped to the
   nearest ink by ΔE00, so the output is 4 flat separations. The fallback is a pure-numpy
   scanline filler: exact pixel-centre sampling, even-odd or nonzero. The two back ends
   agree to within boundary pixels (tested).
3. **Seam check (`edge_wrap_check`).** This computes the mean ΔE00 across the wrap seam as a
   robust z-score against the 127 interior 7.8125-unit grid lines. Grid lines are the fair
   reference because the seam is a boundary of every pixel grid. Seamless means z ≤ 3.5.
   Calibration: seamless proxies scored z ≤ 2.9, and tiles with an artificial seam scored
   z ≥ 4.2. **The real owner tile scores z = 0.6 (x) / 1.7 (y): seamless, no fix applied.**
4. **Fix if not seamless.** The default is **offset-blend**: a half-repeat-offset copy is
   cross-faded in *label space* using a noisy smoothstep mask (x pass, then y pass). It
   keeps the 4 inks and the repeat size. **Mirror** (a 2×2 reflected tile) is only a
   fallback, because it doubles the repeat and shows symmetry axes. Which one was applied
   is recorded in the metrics `seam_check`.

### 0.2 The real artwork (measured)
- **Structure.** Macro blobs traced on the 180-cell grid with 45° corner cuts, as described.
  They are **strongly vertically elongated** (streaks about 2–3× taller than wide). Dark, olive
  and tan alternate across the width every ~100–150 mm at full scale. Square pixel clusters
  (64- and 128-grid) sit along nearly every blob edge. Light tan appears as small highlights
  on blob edges, never as an overlay.
- **Coverage (real):** olive **33.6 %**, dark **29.7 %**, tan field **29.3 %**, light tan
  **7.5 %** (proxy was 25.6 / 22.0 / 41.6 / 10.8). Luminance bands are dark 30 % / mid 34 % /
  light 37 % (proxy 22 / 26 / 52). Weighted mean L* is **48.5** (proxy 53.2), and the mean
  colour is **#8C8056**. The real file is darker and more evenly balanced than the proxy.
- **Blob sizes, full 760 mm (median):** dark 153 mm, olive 132 mm, tan 126 mm, light tan 51 mm.
  At the 380 mm accent scale they are half that.

### 0.3 Owner palette under deer vision (exact; no proxy involved)

| Ink | Hex | L* | deer-sim L* |
|---|---|---|---|
| Bench Grass (field) | #AE9D6C | 65.1 | 64.4 |
| Sidehill Olive | #8B8148 | 53.7 | 53.2 |
| Bleached Tine (light tan) | #C6B497 | 74.1 | 73.4 |
| Deadfall Shadow (dark) | #313120 | 19.9 | 19.9 |

| Pair | ΔE00 human → deer | Michelson (deer) |
|---|---|---|
| tan / light tan | 9.3 → **9.0** | **0.16 (weakest)** |
| tan / olive | 10.6 → 10.2 | 0.22 |
| olive / light tan | 19.3 → 18.6 | 0.37 |
| olive / dark | 30.5 → 30.0 | 0.76 |
| tan / dark | 42.4 → 41.3 | 0.84 |
| light tan / dark | 53.5 → 52.0 | 0.88 |

- **No pair merges for deer** (every pair has ΔE00 ≥ 5). The deer simulation removes most of
  the hue difference between olive and tan (both shift green). What separates them is
  mostly luminance (ΔL* 11).
- **Tan vs light tan:** ΔE00 is 9.0 and Michelson is 0.16. That's enough up close, and
  better than Cirquefall's weakest pair (0.10). But it's purely tonal, and the highlights
  (real file: 51 mm median at full scale, 25 mm at accent) disappear for deer by about
  17 m (full) or 9 m (accent). So it works, but it's the
  weakest link.
- **Luminance spread:** L* runs 20 → 54 → 65 → 74. Three inks sit within 20 L*, and there's
  a 34 L* gap below olive with no mid-dark ink. At range, the dark ink carries almost all of
  the macro contrast.

### 0.4 Physical repeat (scale study, REAL geometry)

Candidates were scored with `repeat_scale_study` on four measures: finest pixel ≥ 2.5 mm
(printable floor), repeats across 1520 mm, deer RMS contrast by distance (vision.py, 6 cpd
ASSUMPTION), and the panel flat-blob test. Proxy values are in brackets.

| Repeat | finest px | across 1520 | deer RMS 50 / 150 / 300 m | flat-blob @150 mm | dark blob, deer-visible to |
|---|---|---|---|---|---|
| 508 | 4.0 mm | 2.99 | 0.20 / 0.03 / 0.01 | 0 % | 35 m |
| 610 | 4.8 mm | 2.49 | 0.24 / 0.04 / 0.01 | 0 % | 42 m |
| 640 | 5.0 mm | 2.38 | 0.25 / 0.05 / 0.01 | 0 % | 44 m |
| **760 (full)** | 5.9 mm | **2.00** | **0.28 / 0.07 / 0.02** (0.36 / 0.20 / 0.07) | 0.3 % (18 %) | **53 m** |
| 305 | **2.4 mm ✗** | 4.98 | 0.10 / 0.01 / 0.00 | 0 % | 21 m |
| 320 | 2.5 mm (at floor) | 4.75 | 0.11 / 0.01 / 0.00 | 0 % | 22 m |
| **380 (accent)** | 3.0 mm | **4.00** | 0.14 / 0.02 / 0.00 (0.26 / 0.07 / 0.00) | 0 % (4.5 %) | 26 m |

- **Full scale stays 760 mm.** It still gives the most deer contrast at range and tiles exactly
  2× across 1520 mm on the Cirquefall drum. The real art is fine on small panels too: only
  0.3 % of 150 mm windows land in plain field, against 18 % for the proxy.
- **Accent scale stays 380 mm.** All 4 inks appear in every 150 mm panel, and the finest pixel
  is 3.0 mm, above the 2.5 mm floor.
- **What the real file changes.** Deer contrast falls off **faster** than the proxy predicted.
  At full scale it is 0.28 at 50 m and 0.07 at 150 m (proxy 0.36 / 0.20). At accent scale it
  is 0.14 at 50 m. The blobs are larger, but the tight vertical dark/olive/tan alternation
  averages out once the deer's acuity cycle (145 mm at 50 m, 436 mm at 150 m) spans one
  stripe set. So beyond ~150 m (full) or ~50 m (accent), a deer sees the print as a flat
  #8C8056. At that range the solid-body vs accent-panel layout does the silhouette breaking
  (see the jacket rows in `owner_base_distance.png`).
- The flat-blob argument for 380 is gone. 380 vs 760 on accents is now a trade between
  close-range busy-ness and deer-visible range (26 m vs 53 m). This is offered to the owner
  in 0.6; the default is unchanged.

### 0.5 Colorways (colorways.yaml, primary)
The solids are three owner inks (**Sidehill Olive, Bench Grass, Deadfall Shadow**; same hex,
so the colour continues across the seam) plus two derived neutrals:
- **Elk Wallow #5E5A40** (L* 38): bridges the dark/olive gap.
- **Lichen Stone #918B7D** (L* 58, C* 8): a low-chroma talus/sage neutral.

Every solid has a ΔE00 ≤ 1.0 dye-lot tolerance (darks also need |ΔL*| ≤ 0.7) and a no-OBA
note. Pairings, all with Owner Base accent panels at 380 mm and Deadfall Shadow trim:
**Sidehill** (olive body, flagship), **Benchland** (tan), **Wallow** (timber/rain),
**Lichen** (talus/late season). The Cirquefall solids and pairings are kept under
`alternate:`.

### 0.6 Recommendations (owner colours unchanged; re-derived on the real file)
1. Keep the 4 inks and the artwork exactly as supplied. Close the L* 20 → 54 gap in the
   *system*: use Elk Wallow (L* 38) bodies for timber.
2. **Dark share target met.** Dark is 29.7 % against the ≥ 18 % target. Dark blobs carry the
   macro contrast, and deer can resolve them to ~53 m at full scale and ~26 m at accent scale.
3. Keep 760 mm full-fill and 380 mm accents. Panel size no longer forces the accent scale:
   the real art has no flat-field problem at either scale.
4. **Owner decision offered:** put large accent panels (≥ 250 mm: yoke, pack lid, hipbelt
   wings) on the 760 repeat. That roughly doubles the deer-resolvable range (~50 m vs ~25 m)
   and uses one drum. Narrow forearm and side panels stay at 380.
5. Past ~150 m the print reads as one colour (#8C8056) for deer. Make the accent panels
   large, asymmetric, and crossing the shoulder and hip lines, so the layout breaks the
   silhouette where the print can't.
6. **Grain:** the art is vertically elongated. Cut panels with the repeat upright, so the
   streaks echo standing grass and timber trunks. Lock the marker rotation to 0°/180°, never 90°.
7. Light tan is only 7.5 % and sits on edges next to olive or dark. That hides the weak
   tan/light-tan step (Michelson 0.16), so no change is needed.
8. Habitat: the mean colour is closest to dry bunchgrass (deer ΔE00 6.0, proxy 2.6) and
   sagebrush (8.3). Against dark timber it is 24.3 (proxy 28.1), better than the proxy but still
   weak. Use the Wallow body or Cirquefall Firn for timber and snow (30.2). Body vs
   background (deer ΔE00): Lichen Stone on sage 2.2 and talus 3.9, Bench Grass on grass 5.1,
   Elk Wallow on timber floor 9.5.
9. On lab dips, hold olive and tan chroma (C* 32 and 28) to the low side. Check that the
   dark ink isn't NIR-black. No OBA, especially on the light inks.

### 0.7 Previews
All are rendered from the real SVG with no PROXY labels: `previews/owner_base_swatch_card.png`,
`owner_base_distance.png`, `owner_base_dichromat.png`, `owner_base_accent_mocks.png` (jacket +
pack × Sidehill/Benchland/Wallow) and `owner_base_tile2x2.png`. Phone copies are
`outputs/screens/20261104_ownerbase_real_{1..5}.png`. The pack hero render
(`outputs/screens/20261104_pack3d_hero.png`) uses the real texture (viz3d log: `camo: owner_base SVG`).

---

# Alternate: Cirquefall camo family + its solid colorway system

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
   drops lower on one side (≈140 mm at one armhole vs ≈175 mm at the other, with an off-centre chevron notch to ≈205 mm).
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
