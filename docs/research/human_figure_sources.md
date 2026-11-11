# Human figure sources for product renders (BL-019)

Date: 2026-11-10 / 11. Question: which open 3D human sources can we use for commercial product images of the pack on
a person, with what licence, and which one do we build on?

Every licence line below is quoted from the page or file named next to it. Pages that could not be fetched are marked
"secondary".

## Decision

**Route taken: MPFB 2 (the MakeHuman add-on for Blender) with the CC0 MakeHuman system assets.** It runs headless in
our `bpy` 5.0.1 wheel (tested: the extension registers, builds a human, rigs it, dresses it and bakes a pose in about
12 s). The fallback (rig and shape a CC0 base mesh ourselves) was not needed.

Why: it is the only candidate that gives a parametric body (so the figure can be sized from ANSUR II), a rig, skin,
eyes, clothes and shoes under one licence that puts no condition on the pictures we make.

## Candidates

| Source | What it is | Licence (quoted) | Commercial product images | Verdict |
|---|---|---|---|---|
| MakeHuman core assets via MPFB 2 | Parametric base mesh `hm08`, about 1,200 morph targets, rigs, skin shaders | "All core assets are shared under Creative Commons, CC0. The effective consequence of this is that you are free to do as you see fit with the asset or derivates of the assets. You do not need to pay anything, include any copyright notices nor give attribution." (https://static.makehumancommunity.org/about/license.html) | Yes | **Used** |
| MakeHuman system assets pack | Skins, eyes, eyebrows, eyelashes, hair, clothes, shoes | Asset table lists every item as "CC0" (https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html); each file header: "This asset was explicitly released as CC0 in september 2020." (for example `clothes/shoes03/shoes03.mhclo` in the pack) | Yes | **Used** |
| MPFB 2 code | The Blender extension that assembles the above | "The source code of MPFB is shared under GPL" (same licence page); extension listing: `SPDX:GPL-3.0-or-later` (https://extensions.blender.org/add-ons/mpfb/, API record) | Yes: GPL covers the program. We run it as a tool and do not ship it; images are not derivative works of the code | **Used as a tool** |
| MakeHuman exports in general | (confirms the point above) | "You can copy, modify, distribute and perform the work, even for commercial purposes, all without asking permission. The exported models end up being licensed CC0 (Creative Commons Zero)." (https://static.makehumancommunity.org/makehuman/faq/can_i_sell_models_created_with_makehuman.html) | Yes | supports the decision |
| Blender Studio Human Base Meshes v1.4.1 | Sculpting base meshes, realistic and stylised, no rig, no clothes | "Human Base Meshes v1.4.1 by Blender Studio and community contributions ... 49 MB – CC0" (https://www.blender.org/download/demo-files/) | Yes | **Fallback, not used.** Fixed shapes: no parametric sizing, no rig, no clothing. More work for a worse ANSUR match |
| Poly Haven | HDRIs, textures (used for the outdoor scene) | "Our assets are all licensed as CC0, which is effectively Public Domain even in jurisdictions that do not support the Public Domain." (https://polyhaven.com/license) | Yes | **Used** (one HDRI, one ground texture) |
| SMPL / SMPL-X (Max Planck) | Statistical body model | "This software/data and the associated license is for academic research purposes. ... Software Copyright License for non-commercial scientific research purposes ... For commercial use please email smpl@max-planck-innovation.de" (https://smpl.is.tue.mpg.de/modellicense.html) | **No** without a paid licence | **Rejected** |
| Mixamo (Adobe) characters | Rigged characters and animations | Adobe FAQ page returned HTTP 403 to our fetch: **secondary, not verified** | Unclear to us | **Rejected** (terms not verified, needs an Adobe account, fixed characters) |
| Community MakeHuman assets (user uploads) | Extra clothes, hair, beards | Mixed per asset (CC0, CC-BY, others) | Case by case | **Not used.** Only the system pack, where every item is CC0 |
| Paid libraries (RenderPeople, Daz, Character Creator) | Scanned or sculpted people | Commercial EULAs, not open | Possible, with cost and licence review | Out of scope for this ticket; see "Owner decisions" in `designs/pack_5200/analysis/hunter_figure.md` |

## What we downloaded, and where it lives

Nothing is in the repo. `huntkit/viz3d/assets/human_manifest.json` holds URL, version, SHA-256, size and licence for
each file; `python -m huntkit.viz3d.wearer fetch` rebuilds the cache (`HUNTKIT_HUMAN_ASSETS`, default
`~/.cache/huntkit/human_assets`) and refuses a file whose checksum differs.

| Asset | Version | Licence | Used for |
|---|---|---|---|
| MPFB 2 extension (`add-on-mpfb-v2.0.18.zip`, 46 MB) from extensions.blender.org | 2.0.18 | code GPL-3.0-or-later; bundled base mesh, targets, rigs CC0 | body, morphs, `game_engine` rig, skin shader |
| MakeHuman system assets (`makehuman_system_assets_cc0.zip`, 281 MB) from files.makehumancommunity.org | server date 2024-04-14 | CC0 | skin `middleage_caucasian_male`, `eyes/high-poly`, `eyebrow001`, `eyelashes01`, garment meshes `male_casualsuit02` (top and trousers) and `male_casualsuit05` (jacket variant), `shoes03` (boots) |
| Poly Haven HDRI "Drakensberg Solitary Mountain", 4k (25 MB) | published 2022-09-02 | CC0 | outdoor light and backdrop |
| Poly Haven texture "Grass Ground", 2k, diffuse / normal / roughness (11 MB) | 2k JPG | CC0 | outdoor ground |

Made by us, in code (`huntkit/viz3d/wearer.py`), no third-party content: the cap, trekking poles, binoculars, grass
blades, every clothing colour (from `designs/apparel/colorways.yaml`) and the fabric shaders. The garment textures that
ship with the MakeHuman clothes (denim, a printed chest motif, stripes) are **not** used; only the mesh and its normal
map are, under our own solid colours. No logo or other brand's pattern appears anywhere.

## Notes for whoever changes this

- MPFB writes a small log-level config under `~/.config/blender/5.0/mpfb/` the first time it loads. That is outside
  the repo and harmless.
- A Blender factory reset unregisters the extension; `wearer.clear_scene()` empties the file without one.
- The figure's ethnicity, age and face are styling sliders (`FIGURE_LOOK` in `wearer.py`), not anthropometry. Only
  the lengths and girths are tied to ANSUR II.
- ANSUR II itself (US Army 2012; Gordon et al., NATICK/TR-15/007, 2014; public release at
  https://www.openlab.psu.edu/ansur2/) is a US Government work. We store regression coefficients computed from it,
  not the data.
