# Camo originality and custom-print sourcing (CORRIE F rev 3 camo release)

camo-designer, 2026-11-13. Fixes review M-10 (`designs/pack_5200/analysis/review_20261113_rev3_release.md`).
All web sources accessed 2026-11-13. Competitor material is used as a **benchmark only**: no commercial camo image is
stored, traced, sampled or used to tune anything in this repo. Release files: `outputs/release/pack5200_corrie_f_rev3/camo/`.

## 1. What the commercial patterns are, as published

Only what the cited sources say. Where a source gives no structural detail, that is recorded as unknown, not guessed
(machine-readable copy: `designs/apparel/camo/originality_refs.yaml`).

| Pattern | Published structure | Sources |
|---|---|---|
| Sitka / GORE Optifade (Open Country, Subalpine, Elevated II, Cover) | Macro pattern breaks up the 3D shape; micro layer of small digital pixels adds background noise; Open Country uses large neutral macro areas for long range. Built on ungulate vision (dichromat, blue/yellow) with the UGA Deer Lab for Cover. | [Sitka: types of camo](https://www.sitkagear.com/experience/types-of-camo), [Kinute / Sitka story](https://kinute.com/stories/633614810-hiding-in-plain-sight-sitka-gear-s-science-based-approach-to-camouflage), [Sitka support: what is Optifade](https://support.sitkagear.com/hc/en-us/articles/4415229190683-What-is-GORE-OPTIFADE-Concealment), [Hook & Barrel on Optifade Cover](https://hookandbarrel.com/science-behind-sitkas-optifade-cover-camo/) |
| KUIU Valo | Large macro pattern with micro detail; six colours: desert tan, prairie-grass yellow, stone grey, coyote brown, olive drab, minimal black; for deciduous / frost-burnt cover. | [KUIU: inside look at Valo](https://kuiu.com/blogs/innovation/inside-look-at-valo), [American Hunter](https://www.americanhunter.org/content/kuiu-valo-coast-to-coast-camouflage), [Game & Fish](https://www.gameandfishmag.com/editorial/kuiu-introduces-new-valo-camouflage/376511) |
| KUIU Vias | Alpine, high contrast, rocky broken ground; tan, light grey, dark grey, brown, black. | [KUIU: inside look at Valo](https://kuiu.com/blogs/innovation/inside-look-at-valo), [Hook & Barrel: KUIU patterns explained](https://www.hookandbarrel.com/gear/kuiu-camo-patterns-explained) |
| KUIU Verde / Verde 2.0 | Darkest of the three, green-heavy, for wet / lush timber. | same as Vias |
| First Lite Fusion / Cipher / Specter | Fusion (western timber/shade) and Cipher use the same algorithm with different palettes; Specter tuned to whitetail vision after 3 years of testing. **No structural description published.** | [First Lite camouflage](https://firstlite.com/pages/first-lite-camouflage), [Ammoland on Cipher](https://www.ammoland.com/2017/01/same-science-new-pattern-first-lites-new-cipher-camouflage-pattern/), [GearJunkie on Specter](https://gearjunkie.com/outdoor/hunt-fish/first-lite-specter-whitetail-camouflage) |
| MARPAT (USMC) / CADPAT | Multi-scale pattern of small rectangular pixels, based on CADPAT. Design patent US D491372 S ("Camouflage pattern for sheet material and uniforms", filed 2001-06-19) and US 6805957 B1 (uniform). Items in the pattern come only from authorised makers. | [Wikipedia: MARPAT](https://en.wikipedia.org/wiki/MARPAT), [Camopedia: MARPAT](https://camopedia.org/index.php/MARPAT) |

## 2. What the law protects (why "concept overlap" is not the question)

- Camo artwork is enforced as copyright (and trade dress / trademark). Kryptek won $1,075,000 and an injunction
  against Salt Armour ([Simmons Firm summary](https://www.simmonsfirm.com/?p=5506)); ASAT Outdoors sued Supreme over a
  1985-copyrighted pattern ([Hypebeast](https://hypebeast.com/2019/11/supreme-tribal-camouflage-pattern-copyright-lawsuit-asat-outdoors-chapter-4));
  Jordan Outdoor sued Yeezy, who argued the rights are "thin" ([The Fashion Law](https://www.thefashionlaw.com/yeezy-denies-copying-camo/));
  Haas Outdoors (Mossy Oak) v. Dryshod survived a motion to dismiss on ownership, copying and substantial similarity
  ([Studicata summary](https://www.studicata.com/summaries/united-states-district-court-western-district-of-texas/haas-outdoors-inc-v-dryshod-international-llc-2019-bzrz3s/)).
- Crye Precision v. Concealed Carrier (E.D.N.Y. 2024): the court called the pattern functional with at best "thin"
  protection, **and still found substantial similarity and likely infringement**
  ([midpage](https://app.midpage.ai/case/crye-precision-llc-v-concealed-10659435)).
- Takeaway: generic ideas (macro + micro scales, pixel micro, a tan/olive/dark palette, deer-vision tuning) are shared
  across the industry and are not owned. The **specific arrangement of shapes** is. So the test that matters is
  image-to-image resemblance of the actual artwork, not whether the design concept matches.
- MARPAT's design patent (filed 2001) is US design-patent law territory; a design patent from an application filed
  before 2015-05-13 runs 14 years from grant (35 U.S.C. 173). ASSUMPTION: it has expired; confirm on USPTO before relying
  on it. Its pixel-only arrangement is unlike Owner Base in any case (section 3).

## 3. Owner Base against the references

Owner Base is the owner's own 4-ink SVG (DECISIONS 2026-11-01; `designs/apparel/camo/source/owner_base.svg`). It is
not generated by Claude, so its provenance rests on the owner's statement.

Structure, measured by `huntkit.camo.originality.describe` (see `originality_metrics.json` in the release):
4 flat inks (L* 19.9 / 53.7 / 65.1 / 74.1), axis-alignment 0.68 (square-pixel micro: yes), vertical streaks
(coherence 0.28 at 90 deg), dark blobs with an area-weighted median of about 83 mm at the 380 mm accent scale.

- **Concept family overlap:** Optifade (macro + digital pixel micro) and MARPAT/CADPAT (pixel). This is reported, not
  hidden. Differences in the published descriptions: MARPAT is pixels only; Owner Base macro is traced organic blobs
  with 45 deg corners and pixels only along blob edges, strongly vertical (grass/timber streaks).
- **Palette:** KUIU Valo (6 colours with grey and coyote brown) and Vias (grey-dominant) differ in count and family;
  Owner Base has no grey and no brown ink. Tan/olive/near-black palettes are common to most western patterns.
- **First Lite:** nothing published to compare at class level.

## 4. The similarity check: what it does and what it cannot prove

`huntkit/camo/originality.py`; tests `tests/test_camo_originality.py`.

- **Copy indicator `ncc_max`:** peak normalised cross-correlation of luminance between two artworks at a common
  physical scale, maximised over every cyclic shift, the 8 flips/rotations and 0.8-1.25x scale. Calibrated on cases
  built from repo art only:

  | case | ncc_max | verdict |
  |---|---|---|
  | Owner Base vs itself shifted, rescaled 10 %, 15 % pixels re-inked, recoloured | ~0.96 | probable copy |
  | Owner Base vs the retired proxy (procedural, built to match its statistics) | ~0.27 | no resemblance |
  | Owner Base vs Cirquefall Shard | ~0.16 | no resemblance |

  Thresholds: >= 0.60 probable copy (stop, get IP advice); < 0.35 no image-level resemblance; between = inconclusive.
  The radial power spectrum of the proxy matches Owner Base at 0.999, which shows that *style* statistics cannot tell
  copies from look-alikes; the shift/flip/scale-searched correlation can.
- **What it can show:** that one specific image is (or is not) a shifted, flipped, rescaled, re-inked or recoloured
  copy of another specific image.
- **What it cannot show:** (a) anything about patterns it was not given: no commercial image is in the repo, so **no
  image-level check against Optifade, KUIU, First Lite or MARPAT has been run**; (b) a heavily redrawn derivative
  (same composition, new shapes) can score low; a court judges "substantial similarity" by eye; (c) who created the
  owner's artwork. It is a screening tool, not legal clearance.
- **To close it:** photograph legally owned swatches (one per competitor pattern) flat, square-on, in daylight, with a
  ruler in frame; then `python -m huntkit.camo.originality compare ours.png swatch.jpg --ppmm-a 11.81 --ppmm-b <px/mm>`.
  Any result >= 0.35 goes to an IP attorney before production. The owner signs the provenance line in the release README.

## 5. Custom-print vendors (sublimation / pigment on polyester)

| Vendor | Base | Process | Minimum | Price | Files | Lead time | Source |
|---|---|---|---|---|---|---|---|
| Ripstop by the Roll, Design Your Own | HyperD 300 (repo record `polyester_300d_printable`), 58 in, 56 in usable | dye-sublimation (OutdoorINK, Durham NC; DYO page does not name the process) | 1 linear yd; 8 x 8 in sample | $30.25/yd; sample $5.00 | PNG/JPG/WebP/SVG <= 50 MB, sRGB IEC61966-2.1, >= 150 dpi (OutdoorINK: 300 dpi mandatory) | 3-5 business days processing (OutdoorINK) + ship; DYO not published | [product JSON](https://ripstopbytheroll.com/products/hyperd-300.json), [design-tool help](https://help.ripstopbytheroll.com/en-US/using-the-design-tool-for-custom-uploads-226767), [OutdoorINK info](https://ripstopbytheroll.com/pages/outdoorink-info) |
| Contrado | Polyester Canvas, 100 % woven polyester ~260 gsm, uncoated (not a repo record) | POD; page says UV inks and water-based inks (conflicting) | none; <= 0.8 sq yd fixed | $37.46 up to 0.8 sq yd; $49.95 / $45.00 / $43.00 per sq yd at 1-3 / 3-10 / 10-20; test print $16.85 | flattened TIFF / JPEG, 200 dpi, sRGB, max width 1.42 yd | 1-2 days + 1-2 days ship | [Contrado polyester canvas](https://www.contrado.com/polyester-canvas-fabric) |
| Custom-print mill program (e.g. Wazoodle with Yarrington Mills) | the mill's printable polyester; for our 630D: print before coating | disperse dye sublimation/transfer | 50-100 yd per print per fabric | strike-off $5 (6 x 6 in) or $50 (36 in x width); print price quoted | TIFF >= 150 dpi at 100 %, seamless in length and width, CMYK not managed, tile <= 200 in | artwork 3-5 d, strike-off 2-4 wk, production 3-6 wk | [Wazoodle custom print program](https://help.wazoodle.com/article/819-custom-print-program-discovery) |
| Oxford / Cordura mills (Asia) | 500-600D camo oxford | quote | quote (marketplace lists 1000 "units") | quote | quote | 25-35 days (mh-chine listing) | [mh-chine 500D camo](https://www.mh-chine.com/products/500d-nylon-66-camouflage-pattern-cordura-material), [Alibaba listing](https://www.alibaba.com/product-detail/Custom-fabric-printing-100-polyester-fabric_1600638515447.html?s=p) |
| Rocky Woods | 600D coated polyester, optic-white prepared-for-print face, white PU back (blank) | none (blank for a bureau) | 60 yd roll | $623.25/roll; sold out | n/a | 3 business days | [Rocky Woods 600D optic white](https://rockywoods.com/products/600d-coated-polyester-fabric-optic-white-sold-per-roll) |
| Rocky Woods 1000D CORDURA HP custom print | 1000D CORDURA HP polyester | library prints only | one 50 yd roll | $748.50/roll | library only (no own art) | n/a | [Rocky Woods 1000D custom print](https://rockywoods.com/products/1000-denier-coated-cordura-hp-polyester-fabric-custom-print) |

No US bureau with a published per-yard price for sublimating **customer-supplied** fabric was found (one search; trade
articles only). One printer FAQ declines customer fabric because it tests its own bases.

### Coating and heat
Dye sublimation transfers at roughly 180-220 C. A PU-leather supplier reports scorching, melting and blistering of PU
under sublimation ([Qiansin](https://www.qiansin.com/news/in-depth-analysis-of-printing-processes-for-white-pu-synthetic-leather-prevention-of-fabric-damage-caused-by-high-temperature-sublimation-heat-transfer/);
vendor source with a product to sell). A patent describes holding a heat-sensitive layer below its melt point with a
temperature gradient ([US12179505B2](https://patents.google.com/patent/US12179505)). The 630D record has an
ether-TPU back coat. So the 630D route needs **print-then-coat at the mill**, or a strike-off that proves the coat
(hydrostatic head and peel) after transfer. RBTR prints HyperD 300 with its PU back, so that route is proven by the
vendor, not by us; AB-1 checks it.

## 6. Conclusions used in the release

1. The only cited, orderable small-batch route for real custom artwork on a pack-grade, coated polyester is **RBTR
   HyperD 300** ($30.25/yd, 1 yd minimum). That base is gated by AB-1 + a print swatch (BL-037 G-2), and the BL-038 test
   kit already buys 1 yd of it. The release's `hyperd300_1yd_2sets_ab1` file makes that one yard carry two complete
   camo sets **and** the AB-1 specimens.
2. The primary 630D base has no small-batch custom-print source. A mill run is 50-100 yd (≈ 180-360 sets) and
   6-10 weeks. Until then the review's fallback (solid 630D) stands for structural builds.
3. Contrado's canvas is a quick look/fit stand-in only (uncoated, no strength data, not in `data/materials/`).
