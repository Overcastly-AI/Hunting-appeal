# How framed packs carry back-panel pressure (BL-005 research)

Owner: structural-fea-engineer, 2026-11-10/11. Purpose: before judging whether one stiff part can both stop meat
pressing through the window (spreader) and spread stay load on the skin (rail backers), list how the market and the
literature split those two jobs. Every claim has a URL. "Fetched" = the page was read for this file; "search summary"
= the claim is from a search-engine summary of the page (secondary); "via back_comfort.md" = the citation was
fetched for `designs/pack_5200/analysis/back_comfort.md` and is reused here.

## 1. Three architectures

| Architecture | How the back-panel pressure gets to the skin | Who | Source |
|---|---|---|---|
| **Framesheet + stays** (one sheet on the body side of the stays) | The sheet is between load and back. Mystery Ranch lists "HDPE plastic for torsional rigidity", "dense XPE foam for targeted flexibility at top and bottom" and "four vertical, composite stays" for the Guide Light MT frame. The older Terraplane used a 0.060 in HDPE sheet with two 1/4 in fibreglass stays | Mystery Ranch, Kifaru Duplex (1/16 in sheet) | [MR Spring 24 workbook](https://issuu.com/mysteryranch/docs/s24_mr_outdoor_wb_issuu) (search summary); Terraplane and Kifaru via back_comfort.md ([Blister](https://blisterreview.com/recommended/mystery-ranch-terraplane), [RMS Gear](https://rmsgear.com/products/kifaru-duplex-lite-frame)) |
| **Frame is the sheet** (moulded carbon panel) | One stiff shell does load path, barrier and back spread; foam pads on it | KUIU carbon frame (11 oz on KUIU's page), Kifaru ARK ("a solid sheet of sturdy, lightweight carbon") | via back_comfort.md: [KUIU](https://kuiu.com/products/kuiu-carbon-fiber-frame-carbonfiber), [GearJunkie ARK](https://gearjunkie.com/outdoor/hunt-fish/first-look-kifaru-ark-frame) |
| **Open frame, stays + cross members, foam on the frame** | No full sheet: cross stays stop the load barrelling into the back; a foam back pad and lumbar pad sit on the frame. Seek Outside: "Cross Stays (7075) prevent barreling at all frame heights and reduce back intrusion", removable, 4 oz the pair, lumbar pad an add-on | Seek Outside Revolution, Exo K4 (reported: no frame sheet, two vertical and thinner horizontal carbon stays, closed-cell foam back panel), Stone Glacier Krux | [Seek Outside](https://seekoutside.com/revolution-suspension-and-frame/) (fetched 2026-11-10); Exo and Stone Glacier via back_comfort.md ([Rokslide K4, reported](https://rokslide.com/forums/threads/exo-mountain-k4.279017/page-2), [Stone Glacier](https://stoneglacier.com/pages/selecting-a-hunting-frame-which-stone-glacier-frame-is-right-for-you)) |
| **Suspended (tensioned) mesh** | A mesh trampoline on a perimeter frame touches the back; the bag is held off it. Reviewers report the best airflow, and the load sits further from the back | Osprey Exos (AirSpeed) | [CleverHiker Exos review](https://www.cleverhiker.com/backpacking/osprey-exos-58-backpack-review/) (search summary) |

What this pack has today is a fourth arrangement: an open frame (like the third row) with a **bag-side** sandwich
barrier between the stays (the spreader) and **wearer-side** foam rails with stiff backer strips on the stays. Nobody
on the list publishes a separate wearer-side backer strip; foam-on-stay packs (Exo, Stone Glacier) do not publish
how the foam is backed.

## 2. What the leaders imply for "one part, two jobs"

- A single sheet doing barrier + back spread works when the sheet is on the **body side** of the stays (framesheet,
  carbon shell). Then it is the part the back presses on, and the foam goes on it.
- Moving our spreader there puts it 28 mm (the stay diameter) closer to the back; the leaders that do this have a
  thick foam or lumbar stack between sheet and back (Mystery Ranch "dense XPE foam"), not an air gutter. That is the
  cost found in `back_system_integration.md` (a2).
- Suspended mesh is the light way to spread pressure when the frame is a perimeter hoop; it trades the bag sitting
  further aft (reviewers above). Our stays are inboard (x ±115), so a mesh between them would sit over the meat
  window and carry no stay load. Not pursued.
- Frame-sheet distortion under heavy load (sides pulled in, cylindrical sheet, uneven load distribution) is described
  as a known problem in US 6,626,342 B1 background ([USPTO PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6626342), search summary). Patent guardrail: a wearer-side backer strip in a rail sleeve is
  ordinary pad construction; nothing found that claims it.
- Hobbyist builders: 1/32 in HDPE too flimsy, 1/16 in too heavy for a sheet; aluminium stays stiffer per gram than a
  polymer sheet ([Backpacking Light forum](https://backpackinglight.com/forums/topic/frame-sheet-hdpe-vs-abs-vs-umhw-vs/), search summary; anecdotal).

## 3. Skin-pressure comfort data (the 14 kPa rule)

Reused from `designs/pack_5200/analysis/back_comfort.md`, which holds the fetched sources:

- Golriz et al. 2017 (Work 58): prolonged load-carriage limit used as the 14 kPa peak at the 1.6 g walking peak
  (back_comfort.md, the basis of `spreader.PEAK_KPA`).
- Wettenschwiler et al., PLOS ONE 10(11):e0142004 (2015): skin occlusion ~16 kPa (Holloway), ischaemia 5.6–9.5 kPa
  (Sangeorzan), 20 kPa mean shoulder pressure uncomfortable for 90 % (Bryant); no single limit given
  ([PMC4631336](https://pmc.ncbi.nlm.nih.gov/articles/PMC4631336/), fetched for back_comfort.md).
- Soft-tissue indentation moduli 10–90 kPa (abdomen 11–13 kPa, lower limb 10–89 kPa): the basis of the 60 kPa
  design tissue column and the 20 kPa sensitivity ([PolyU](https://research.polyu.edu.hk/en/publications/a-hand-held-indentation-system-for-the-assessment-of-mechanical-p/), [Scilit](https://www.scilit.net/publications/28f0aabc780ba8ce95797fdac2073c58), via back_comfort.md).
- Minicel L200 XLPE: 48 kPa at 25 %, 103 kPa at 50 %, 12 % compression set ([foambymail](https://www.foambymail.com/product/minicel-l200.html), via back_comfort.md).
- Pressure-mapping evidence on back panels is thin: an AHFE 2023 paper (children, standing) found a padded air-mesh
  panel with a curved board spread back pressure more evenly than a plain pack, whose lower edge pressed locally into
  the lumbar region; no kPa values are published in the abstract ([AHFE open access](https://openaccess.cms-conferences.org/publications/book/978-1-958651-90-2/article/978-1-958651-90-2_2), fetched). A strap/hip-belt study moved pressure from shoulders to hips with a hip belt ([JFBI 2019](https://ojs.global-sci.org/index.php/JFBI/article/view/13045), search summary). No published pressure map of a framed hunting pack's back panel was found; the T9-day pressure-mat test remains the settling test.

## 4. Composite strip data used

- 200 g 2×2 twill carbon ply 0.22 mm, E 58 GPa, Xt/Xc 600/570 MPa (`cfrp_t300_3k_woven_epoxy_ply`), ROHACELL 71 / 110
  IG-F (shear modulus 29 / 50 MPa, shear 1.3 / 2.4 MPa, compression 1.5 / 3.0 MPa; [Evonik IG-F TDS](https://media.easycomposites.eu/datasheets/Rohacell-IG-F-TDS.pdf), via back_comfort.md / the records). Thinnest ROHACELL 71 IG-F sheet offered by Easy Composites is 3 mm ([Easy Composites](https://www.easycomposites.eu/Rohacell71-IG-F-PMI-Foam-Core), via back_comfort.md): a 2 mm core needs a sanded-down or special-order sheet.
