# Originality note: CORRIE F rev 3 camo (Owner Base, accent 380 mm)

Signed into the release by the camo-designer agent, 2026-11-13, for review M-10. Research and citations:
`docs/research/camo_originality_print_2026.md`. Numbers: `originality_metrics.json` (this folder).

## What the camo is
- **Pattern:** Owner Base, the owner's own 4-ink SVG (`designs/apparel/camo/source/owner_base.svg`, DECISIONS
  2026-11-01, ingested 2026-11-04). It is not a Claude-generated pattern and not a trace of any commercial pattern
  as far as this repo records. Claude changed nothing in the artwork. The only processing is rasterising it, snapping
  it to 4 inks, and removing the 1-px rasteriser seams (`placed.clean_hairlines`; 0.4 % of pixels).
- **Scale:** accent repeat 380 x 380 mm, as in `owner_base.yaml` and in the rev 3 renders
  (`huntkit/viz3d`: `studio.MATERIALS["camo"]` -> `cycles_render.owner_camo_png`, `camo_repeat_mm` 380).

## Checks run

| Check | Result | What it proves |
|---|---|---|
| Class-level comparison against the **published descriptions** of Sitka Optifade, KUIU Valo / Vias / Verde, First Lite Fusion / Cipher / Specter, MARPAT/CADPAT | Owner Base shares the macro-blob + pixel-micro **concept** with Optifade and the pixel concept with MARPAT. Its palette (4 inks, no grey, no brown) differs from the described KUIU palettes. First Lite publishes no structure. | Only that the design family overlaps, which is common and not protectable. It says nothing about copying. |
| Image-level copy indicator `ncc_max` (shift, 8 flips/rotations, 0.8-1.25x scale), calibrated | derivative of the owner file 0.96 (flagged); a procedural pattern built to the same statistics 0.27 (clear); Cirquefall 0.16 (clear). Thresholds: >= 0.60 copy, < 0.35 clear | That the tool can tell a copy from a look-alike. |
| Image-level check of Owner Base **against commercial patterns** | **NOT RUN.** The repo holds no commercial camo images (benchmark-only rule). | Nothing yet. |

## Open before production (owner actions)
1. **Provenance (owner):** sign below that you made the Owner Base artwork yourself or hold the rights to it, and did not
   trace or adapt a commercial pattern.
2. **Image check:** photograph swatches you legally own of Optifade (Subalpine / Open Country), KUIU Valo / Vias /
   Verde 2.0 and First Lite Fusion / Cipher flat, square-on, in daylight, with a ruler in frame. Then for each:
   `python -m huntkit.camo.originality compare outputs/release/pack5200_corrie_f_rev3/camo/print/owner_base_accent_380mm_300dpi.png <photo.jpg> --ppmm-a 11.811 --ppmm-b <px per mm from the ruler>`.
   Any `ncc_max` >= 0.35 goes to an IP attorney before you sell anything.
3. This is a screening note, not legal clearance.

Owner provenance statement: ______________________________  date: __________
