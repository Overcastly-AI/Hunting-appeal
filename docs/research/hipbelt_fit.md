# Hipbelt fit and load transfer: research (2026-11-08)

Owner request: "the hip belt needs improvement, to better fit the hips. It takes all the load."
Research phase for the Pack 5200 hipbelt redesign (CLAUDE.md "research first"). Every claim carries a URL. Searches
and page reads were done on 2026-11-08. Where a page could not be opened (403), the claim is marked "(search
summary)": the wording came from the search engine's extract of that page, not a full read. Brands are performance
benchmarks only: no shapes, names or trade dress are copied.

Analysis and concepts built on this: `designs/pack_5200/analysis/hipbelt_fit.md`, model `huntkit/gendesign/hipbelt.py`.

---

## 1. Biomechanics

### 1.1 How much of the load should the hips carry?

- **The commonly cited figure is 80 %.** REI's backpack guide says 80 % or more of the weight should be supported by
  the hips (search summary, https://www.rei.com/learn/expert-advice/backpack.html). The AMC fitting guide gives about
  80 % to the hips and 20 % to the shoulders (search summary, https://www.outdoors.org/?p=947). Alpkit's guide gives
  60–80 % (https://alpkit.com/blogs/spotlight/understanding-backpack-fit-the-complete-guide). None of these cite a
  measurement.
- **The one measured figure found is much lower.** LaFiandra, Harman, Frykman and Pandorf (2002), "What percentage of
  a backpack's weight is supported by the hips?", Med Sci Sports Exerc 34(5) suppl. S159
  (https://katalog.lib.cas.cz/KNAV/EdsRecord/edb,113921956). A citing paper reports the finding as about **30 %** on
  the hips for adult men (https://ojs.ub.uni-konstanz.de/cpa/article/view/1264/1186). A CDC document gives a similar
  ~30 % for a framed pack with a hip belt (https://stacks.cdc.gov/view/cdc/216789/cdc_216789_DS1.pdf). The abstract's
  methods were not available.
- Backpacker magazine measured the hip/shoulder split with force sensors and noted that it shifts as you walk
  (https://www.backpacker.com/gear/backpacks/backpack-load-test-outside-lab/).
- Military reviews agree on the direction: hip belts reduce shoulder pressure and should be used whenever possible
  (Knapik et al. 2004, https://pubmed.ncbi.nlm.nih.gov/14964502/). Holewijn (1990) found skin pressure under the
  straps was the limiting factor unless a waist belt took the load off the shoulders
  (https://link.springer.com/doi/10.1007/BF00357606).

**Reading.** 80 % is a design target, not a law of nature. The measured share depends on the belt fit, the frame and
the strap settings. Our R-07 keeps 80 % as the design case for the belt. It is the conservative choice for the belt,
because a belt sized for 80 % also works at 60 %. Section 3 of the analysis shows what holding 80 % at 68 kg costs in
belt tension and pressure.

### 1.2 Pelvis and iliac crest anatomy; male and female differences

- **Where the belt sits.** Measure around the iliac crest, about 1 in below the navel, feeling out to the side; do not
  use pant size (Exo, https://exomtngear.com/sizing). REI: measure around the top of the hips, hugging the iliac
  crest, which is slightly higher than the pant beltline (https://www.rei.com/learn/expert-advice/backpacks-torso-hip-size.html).
  AMC: the crest should sit in the middle of the waistbelt (search summary, https://www.outdoors.org/?p=947).
- **The female pelvis is broader and shallower** (StatPearls, https://www.ncbi.nlm.nih.gov/books/NBK519068/).
- **The crest itself is only weakly dimorphic.** A study of 150 adult hip bones found only slight sexual dimorphism in
  crest shape (https://soar.wichita.edu/server/api/core/bitstreams/7b300d21-dcf3-487e-9ebc-65ac4da9d5ac/content). A
  geometric-morphometric study of 129 skeletons found almost no crest-shape dimorphism
  (https://vufind.lboro.ac.uk/PrimoRecord/cdi_proquest_miscellaneous_2573441761). **So the belt-relevant difference
  between men and women is the soft-tissue cone between the waist and the hips, not the crest bone shape.** We
  measured that cone in ANSUR II (below).
- **ANSUR II (US Army 2012 survey, public release, men n 4082, women n 1986,**
  https://www.openlab.psu.edu/ansur2/**).** Crest-level (omphalion) waist circumference: men p5/p50/p95
  30.2 / 36.9 / 44.5 in, women 28.0 / 33.5 / 40.9 in. Omphalion height equals iliocristale height within 6 mm
  (men's medians 1055 vs 1061 mm), so the ANSUR waist circumference is the belt circumference. Hip cone half-angle
  (buttock vs waist circumference over the height between them): men p5/p50/p95 **−1.2 / 4.4 / 8.9 deg**, women
  **4.2 / 10.0 / 14.6 deg**. Lateral cone (hip breadth vs waist breadth): men 3.4 deg median, women 10.5 deg. The cone
  is also **steeper for smaller waists in both sexes** (men 7.7 deg at 28 in, 0.5 deg at 42 in). Derived in
  `designs/pack_5200/analysis/hipbelt_anthro.yaml` (`hipbelt.derive_anthro`).
- **ASIS position.** Inter-ASIS distance 22.7 ± 1.6 cm in a CT study of 200 adults
  (https://link.springer.com/article/10.1007/s00256-009-0791-x). The ASIS distance changes little with waist size,
  so on a small waist the ASIS sits relatively further back around the body. A fixed 72 % padded length runs the wing
  tip onto the ASIS for small users (analysis §3.3).

### 1.3 Conical vs cylindrical belts

- Women's belts are conical and more curved, men's straighter; a straight-cut belt may not sit well on a flared pelvis
  (https://outdoors.nordling.de/area/conical-hip-belts,
  https://outdoors.nordling.de/learn/how-does-the-male-and-female-pelvic-structure-differ-in-relation-to-hip-belt-fit).
  This site looks auto-generated: treat it as a statement of common practice, not evidence. Its "45–60 deg canting"
  figure is not supported anywhere else and is not used.
- A KUIU PRO user reports the belt "not curving in enough at the top to grip my hips when loaded heavy"
  (https://rokslide.com/forums/threads/new-kuiu-pro-suspension-and-pro-bag-review.132719/page-2, search summary).
- **Geometry (our own, analysis §2):** a cone is developable. Its flat pattern is an annular sector, so a wing that
  fits a cone must be cut with a curved centreline. A straight strip can only make a cylinder (or a tilted cylinder),
  whatever angle it is mounted at. The current belt's 0/5/10 deg cant snap tilts a straight wing; it cannot make it
  conical.

### 1.4 Pressure thresholds

- **Blood occlusion at 16 kPa** body-surface pressure (Holloway et al. 1976). **5.6–9.5 kPa** can be enough for
  ischaemia (Sangeorzan et al. 1989). Both via Wettenschwiler et al. 2015 (https://pmc.ncbi.nlm.nih.gov/articles/PMC4631336/).
- **20 kPa average shoulder pressure was uncomfortable for 90 % of soldiers** (Bryant 2001, via the same paper).
  14 kPa is the prolonged-carriage limit used for the back panel (Golriz et al. 2017, `analysis/back_comfort.md`).
- **The hip tolerates more than the shoulder.** At equal discomfort, p_hip = 2.135 p_shoulder + 18.75 kPa
  (Wettenschwiler 2015, Eq. 1). Scribano & Burns (1970) put the hip at 2–3 times the shoulder's tolerance (via the
  same paper). Applying Eq. 1 to the 14 kPa shoulder limit gives **48.6 kPa as the equal-discomfort hip peak**.
- **Pressure-pain thresholds (algometer)** are measured with a 1 cm² probe ramped at 30–50 kPa/s
  (https://medicaljournalssweden.se/jrm/article/download/41756/47347/121600,
  https://bmcmusculoskeletdisord.biomedcentral.com/track/pdf/10.1186/1471-2474-11-234). Bony prominences in the distal limbs
  are around 580 kPa (search summary,
  https://vufind-test.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-c4739-cad1b9a2ba6f6b399f842c2f0841a5df0578103e5f7b6aef584d2ef34802bf7f2).
  **No site-specific PPT for the ASIS or crest top was found.** Those values are seconds-long pain onsets and do not
  apply to hours of carry. We tag a 30 kPa "bony" watch level as an ASSUMPTION.

### 1.5 Hot spots

The ASIS ("hip pointers"), the top of the iliac crest, the lumbar/sacrum and the thigh/hip flexor below a belt that
sits too low (§4 below; Exo: too-big belt sags and presses the hip flexors,
https://exomtngear.com/blogs/article/why-do-we-make-the-k4-hipbelt-in-5-sizes).

---

## 2. Published load-carriage pressure research

- **Wettenschwiler et al. 2015, PLOS ONE, "Mechanical Predictors of Discomfort during Load Carriage"**
  (https://pmc.ncbi.nlm.nih.gov/articles/PMC4631336/). Pressure mats and strap force sensors, 20 kg load, hip-belt
  tension set to **30 / 60 / 90 / 120 N**. Static peak pressure (or static strap force) predicts discomfort at the
  shoulder and hip (p < 0.001). Hip discomfort = 0.052 x peak kPa + 1.127 (R² 0.86). Most static peaks exceeded the
  16 kPa occlusion level. Absolute hip pressures are in supplementary Table S3 (not read).
- **Mackie et al.** (Queen's University load-carriage simulator) found hip-belt use and strap adjustment had the
  largest effects on shoulder strap force after pack weight (via
  https://ocr.docketalarm.com/cases/PTAB/IPR2016-01866/Inter_Partes_Review_of_U.S._Pat._8590757/09-23-2016-Petitioner/Exhibit-1081-81-Mackie/,
  search summary).
- **Inge et al. 2023, Colorado School of Mines poster** (n 3 service members, 40 % body-weight pack + armour, 10 deg
  up/down slopes): peak **shoulder** pressure 36–38 kPa shoulder-only versus 25–30 kPa with the hip belt engaged
  (https://undergraduateresearch.mines.edu/project/p105-2023). It is a small pilot, so treat it as an indication only.
- **Holewijn 1990** (https://link.springer.com/doi/10.1007/BF00357606) and **Knapik 2004**
  (https://pubmed.ncbi.nlm.nih.gov/14964502/): see §1.1.
- **Friction (needed for the slip model).** Skin–textile friction ranges from **0.27 to 0.71** with large differences
  between people (UCL, https://discovery-pp.ucl.ac.uk/id/eprint/10049846/1/Cottenden_Falloon_Cottenden_120716.pdf).
  Fabric on the forearm gives 0.69–0.78 (https://www.jstage.jst.go.jp/article/senshoshi1960/22/1/22_1_38/_article/-char/en).
  Polyamide (nylon) fabrics gave the lowest coefficient (Ramalho, via https://mdpi.com/2075-4442/4/1/6, search
  summary). Moist skin can more than double the friction (search summary, https://pmc.ncbi.nlm.nih.gov/articles/PMC2607440).
  **We use μ = 0.30 (low end) and 0.50 as the sensitivity.** The governing interface may be shirt-on-skin, not
  belt-on-shirt, so a grippy belt face only helps up to that limit.

---

## 3. What the leaders do (performance only)

| Brand | What is published | Source |
|---|---|---|
| **Stone Glacier** SG 3-Piece Belt | S 28–30 / M 31–36 / L 37+ in; "can go larger than the listed range, not smaller"; size down between sizes. **12.8 oz (363 g)**. Removable lumbar pad: foam layers "can be trimmed and moved vertically to create a roll in the pad at any level", with **non-slip fabric** to lock the belt to the back. 500D Cordura + X-Pac; 1 in Duraflex buckles | https://stoneglacier.com/collections/sg-products/products/sg-3-piece-belt |
| **Exo Mtn Gear** K4 | **5 belt sizes**, overlapping; measure at the crest, never pant size; "the hipbelt is the number one component of a pack's performance"; too big sags onto the hip flexors, too small leaves the padding short of the hip bones. 500D Cordura, "premium foams". A user bought the lumbar kit for slippage: it helped but did not stop it | https://exomtngear.com/blogs/article/why-do-we-make-the-k4-hipbelt-in-5-sizes, https://exomtngear.com/sizing, https://exomtngear.com/products/k4-hipbelt, https://rokslide.com/forums/threads/exo-pack-belt-size.272349 |
| **Mystery Ranch** | Waist belts XS/S 26–32, S/M 31–36, M/L 35–40, L/XL 39+ in (retailer); "Re-Direct" waist belt "for effective weight transfer"; **patented lumbar wrap** (number not given); size down between sizes | https://www.blackovis.com/gear/packs/mystery-ranch-pop-up-waistbelt (search summary), https://equipment.adsinc.com/collections/mystery-ranch, https://www.mysteryranch.com/load-carriage-architecture-of-a-mystery-ranch-pack |
| **Kifaru** | Belt XS ≤ 30, S 31–34, M 34–38, L 39–46 in. A user found the stock lumbar too stiff and thick and sitting low on the tailbone, with no other option | https://kifaru.net/pages/frame-size-guide, https://rokslide.com/forums/threads/lumbar-pad.369578/post-3795342 |
| **KUIU** PRO | Two belt sizes: S/M 28–34 in, L/XL 34–52 in; "fully adjustable … lumbar, and waist belt"; consider layers. ICON belt reportedly 6 in at its tallest (forum) | https://www.kuiu.com/pro-suspension/62022-VC.html, https://www.kuiu.com/pages/faq-2, https://rokslide.com/forums/threads/new-kuiu-icon-6.455714/post-4754983 |
| **Seek Outside** | Full-wrap, self-articulating belt; **single centre buckle with 4-way forward-pull mechanical advantage; top and bottom tension adjust independently**; belt attached to the frame (grommet + screw, 3 positions, on the Peregrine). Users: "forward pull ALWAYS trumps side pull for heavy loads", others disagree | https://seekoutside.com/revolution-suspension-and-frame/, https://seekoutside.com/hipbelt-gen-2-0-blackout/, https://backpackinglight.com/forums/topic/see-outside-unaweep-or-revolution/ |
| **Hyperlite** | Removable belts (pockets or gear loops), wide adjustment ranges (pocket belt S 26.5–49 in), separate extender | https://support.hyperlitemountaingear.com/en-US/what-are-the-hip-belt-adjustments-for-each-torso-size-909559, https://hyperlitemountaingear.com/products/removable-hip-belt |
| **Osprey** | Custom-moldable belts (BioForm / IsoForm CM): **dual-density, heat-moulded** at the retailer; some models now discontinued | https://www.rei.com/product/748423/osprey-bioform-custom-moldable-hipbelt-mens, https://rei.com/product/111306 |
| **Arc'teryx** Bora (RotoGlide) | Belt on a **swivel joint that also glides vertically** (about 1.5 in) and follows hip motion; reviewers rate it a real benefit | https://www.backpacker.com/gear-item/arcteryx-bora/, https://www.altitude-sports.com/blog/arcteryx-bora-ar-backpack-review/, https://digitaltrends.com/outdoors/arcteryx-bora-ar-rotoglide-hip-belt |
| **Granite Gear** Re-Fit | **Length-adjustable belt** (about 26–42 in, model-dependent), dual density, adjusted by opening a hook-and-loop closure | https://nextadventure.net/pages/granite-gear-backpack-size-chart-and-fit-guide, https://www.ems.com/granite-gear-lutsen-45-pack/2032547.html |

**Feature map.** Pivots and articulation (Arc'teryx, Seek, our Ti roll pivot); interchangeable or length-adjustable
belts (SG, Exo, Kifaru, Hyperlite, Granite Gear); heat-moldable dual-density foam (Osprey); a grippy or shapeable
lumbar (SG, Exo kit, MR lumbar wrap); forward-pull mechanical advantage with separate top and bottom tension (Seek);
4–5 belt sizes with overlap (Exo, MR). The hunting leaders all treat the lumbar as the heavy-load contact.

---

## 4. User pain points (hunting / heavy loads)

- **Bruised hips from cranking the belt:** "I have to really crank on the hip belt over my iliac crests for it to stay
  up until I can't breathe and my hips are red and bruised", with Leukotape on the "hip pointers" before pack-outs
  (Rokslide, https://rokslide.com/forums/threads/best-modern-hunting-packs-for-skinny-guys-with-ghost-hips.416893/post-4289321,
  search summary).
- **Belt slip and settling under meat loads:** the belt runs out of adjustment "as my iliac crests compress during a
  hike"; a wider belt helped but "the pack still slid down"
  (https://rokslide.com/forums/threads/waistbelt-slip.322689/, https://rokslide.com/forums/threads/first-heavy-pack-out-nightmares.335477/,
  search summary). Our market research P1 lists slipping, crest hot spots and a soft lumbar above ~65 lb for Exo, SG,
  MR, Kifaru and Seek (`docs/research/pack_market_2026.md` §P1).
- **Belt too short:** the webbing digs in when cranked; the padding does not cover the crest
  (https://backpackinglight.com/forums/topic/19925/, search summary). Too short rides high
  (https://www.trekitt.co.uk/blog/fit-your-backpack/).
- **Belt too long / too big:** cannot be pulled tight; sags onto the hip flexors
  (https://exomtngear.com/blogs/article/why-do-we-make-the-k4-hipbelt-in-5-sizes). Worn below the crest it "squeezes
  your musculature" (https://backpackinglight.com/forums/topic/19925/), causing thigh pain
  (https://rokslide.com/forums/threads/hipbelt-pain-on-my-thighs.416617).
- **Gap at the crest:** a belt that does not curve in at the top cannot grip the hips (KUIU PRO user above).
- **Lumbar:** too thin for some users (MR, Kifaru, Exo) and too thick and low for others (Kifaru). Users ask for
  adjustable shape (all above).

---

## 5. Patents (avoid, do not copy; counsel to confirm before tooling)

| Patent | Owner / status | What it claims (as read) | Our position |
|---|---|---|---|
| **US 12,588,748 B2** "Adjustable backpack" (https://patents.google.com/patent/US12588748B2/en) | Amer Sports Canada (Arc'teryx parent); **granted 2026-03-31**, priority 2023-04-21, est. expiry 2044 | Claim 1: a sleeve between pack and frame receiving a removable hip belt. **Claims 4 and 15: rear left/right hip-belt end portions "repositionable and selectively retainable at different angles relative to one another"**, held by two straps connected at different locations. Dependent claim 14: each side has upper and lower rigid bands with a **more flexible iliac-crest receiving panel** between them | The **current 0/5/10 deg cant snap** adjusts the wing angle. It is a snap, not the claimed two-strap arrangement, but it is close in function. **Concepts A/B/C delete it**: the cone is cut into the pattern, the angle is fixed. Keep the HDPE one continuous sheet across the crest; do not split it into upper and lower bands with a soft window (claim 14) |
| US 12,582,217 B2 "Adjustable backpack" (https://patents.google.com/patent/US12582217B2/en) | Amer Sports Canada, active | Claims cover the shoulder-strap length adjustment only; a hip-belt angle retainer appears only in the description | No conflict |
| US 2006/0060625 A1 "Custom molded backpack hipbelt and method" (https://patents.google.com/patent/US20060060625A1/en) | Kuder, Pfotenhauer; **abandoned 2009** | Thermo-moldable EVA belt heated and shaped to the wearer | Free to use; we do not heat-mould (a beginner build) |
| US 2008/0035686 A1 "Backpack pivot system" (https://patents.google.com/patent/US20080035686A1/en) | Gregory Mountain Products; **abandoned 2010** | Waist belt on a pivot that lets it rotate relative to the frame | Free; our Ti roll pivot is unchanged |
| **US 10,806,238 B2** "Backpack with dynamic flexible hip belt" (https://patents.google.com/patent/US10806238B2/en) | Samsonite; **active to ~2038** | A resilient member couples the hip belt to the frame and expands/contracts as they move (claim 1 not read) | Our existing pivot has an **elastomer centring bushing**. This is not a new feature of this study, but **flag it to counsel** |
| US 6,609,642 "Mechanical advantage backpack" (https://patents.google.com/patent/US6609642) | Heinz et al., 2003 (filed 2001; 20-year term likely ended, verify) | Cable around pulley banks at the lumbar segment fronts, 4:1–30:1 | Our 2:1 is plain webbing through a D-ring, no cable or pulley banks |
| **US 10,638,827 B1** "Modular hip belt with gross and fine adjustment" (https://patents.google.com/patent/US10638827) | Pressio LLC, active | Buckle for gross adjustment plus a cord pulley assembly with a catch for fine adjustment | Avoid cord + pulley + catch tensioners; webbing 2:1 only |
| US 11,064,794 / US 10,165,846 "Backpacks with cooperatively adjusted hip belts and compression straps" (https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11064794) | active | Adjustment straps link hip-belt segments to compression straps | Our belt pull is independent of the bag compression |
| Mystery Ranch "patented lumbar wrap" (https://www.mysteryranch.com/load-carriage-architecture-of-a-mystery-ranch-pack; patent list https://issuu.com/mysteryranch/docs/f23_hunt_mr_2022_final_digital) | number not identified | — | Our lumbar is a pad on a centre plate; no wrap from the frame. **Counsel to identify the number** |
| US 5,954,253 "Flexible frame load carrying system" (https://patents.google.com/patent/US5954253) | old, expired | Hip support with pivoting lateral supports | — |
| Seek Outside "patented articulating frame" (number not published) | — | — | Already flagged in `pack_market_2026.md` |
