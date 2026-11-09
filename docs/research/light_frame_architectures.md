# Light frame architectures: printed nodes on carbon tubes (research, 2026-11-09)

Owner: structural-fea-engineer. Purpose: the cited basis for the lighter-frame study 2
([frame_light2.md](../../designs/pack_5200/analysis/frame_light2.md)). The owner approved the study on 2026-11-09
(DECISIONS row "Owner: 'Yes' to the weight-pass recommendation", item 4): keep the generative-print look, build it
at home (Bambu H2S class printer, bought tubes, bonded in jigs), and pass HA-LS-1 rev C including fatigue.

Benchmarks come from the cited sources below, not from memory. Where no source was found, this says so.

## 1. Printed or additively made nodes joining carbon tubes

| Example | Node | Tube joint | What it shows | Source |
|---|---|---|---|---|
| Robot Bike Co R160 (UK) | SLM Ti-6Al-4V lugs (Renishaw), heat-treated, bearing seats CNC-finished | Carbon tubes bonded into **double-lap joints, about 25 mm deep, Ti inside and outside the tube**; the double lap was chosen to keep peel (out-of-plane) loads off the bond | The production answer for bonded tube-in-lug frames is a double lap and a stiff (metal) lug | [The Engineer][eng-robot], [Metal AM][mam-robot], [Pinkbike review][pb-robot] |
| Bastion Cycles (AU) | SLM Ti lugs, made to fit each rider | Filament-wound carbon tubes bonded into the lugs; a broken tube can be replaced | Same architecture; repairability is a selling point | [The Radavist][rad-bastion], [New Atlas][na-bastion] |
| Burton Bikes Raptor I | AM Ti-6Al-4V lugs | Bonded carbon tubes | Same | [Metal AM][mam-burton] |
| Fenix Composites road bike (DE) | Ti lugs by cold metal fusion | Thermoplastic carbon tubes joined by induction heating, no adhesive, reversible | A non-adhesive route (not available to a home builder) | [CompositesWorld][cw-fenix] |
| DIY / FPV drone frames | FDM nylon (PA12-GF, PA-CF), PETG, ASA nodes | 16 mm carbon tubes glued into printed sockets; builders stress sanding and clamping | Printed-node tube frames are common in hobby drones, but **no published joint strength or mass breakdown was found** | [Flite Test][ft-quad], [MakerWorld frame][mw-frame], [ArduPilot forum][ap-quad], [Formlabs drones][fl-drones] |
| Divergent / Czinger (cars) | AM aluminium nodes | Tubes bonded into nodes through injection ports and channels; tongue-and-groove features | Industrial printed-node space frames are heavily patented (section 4) | [US 10,668,965][pat-965], [US 10,605,285][pat-285], [US 11,110,514][pat-514] |

Reading: every product that bonds carbon tubes into printed lugs and carries real loads uses a **metal** lug
(Ti or Al) and a **double-lap** socket. Hobby drones use printed nylon sockets, but they publish nothing about joint
strength, and their loads are small. Nobody publishes a structural pack or bike frame with load-bearing printed
polymer lugs.

## 2. Bond strength of carbon tube in a printed polyamide socket (published data)

| Joint | Adhesive / prep | Strength | Failure | Source |
|---|---|---|---|---|
| MJF PA12 single lap, 12.5 mm overlap | media-blasted (Ra about 10.7 um), degreased; 3M DP620NS (PU) | **5.0 +/- 0.25 MPa** | adhesive (interface): no adhesive left on the PA12 | Sedlacek et al., *Polymers* 17(22):3020 (2025) [PMC12656205][sed25] |
| same | 3M DP490 (toughened epoxy) | 3.7 +/- 0.25 MPa | adhesive | same |
| same | Loctite EA 9466 (epoxy) | 3.7 +/- 0.14 MPa | adhesive | same |
| same | Loctite HY 4090 (CA-epoxy hybrid) | 3.8 +/- 0.26 MPa | adhesive | same |
| FDM TPU to PBF PA12 | Loctite 401 + 770 primer, no plasma or flame | 3.0 MPa (best of the set) | | [PMC12824215][pa12-tpu] |
| FFF PA-CF (carbon-filled polyamide) to aluminium, single lap | sanding vs grit blasting of the Al | **1 to 6.6 MPa**, rising with roughness | | Martins et al., *Appl. Sci.* 13:4429 (2023) [MDPI][mart23] |
| Thermoplastic carbon/polyamide (CFRP-PA) joints | plasma pretreatment | about **+90 %** lap shear on average (no absolute value in the abstract) | | [PNNL][pnnl-plasma] |
| CFRP (thermoset), atmospheric plasma | plasma vs as received | 31.6 vs 8.6 MPa | | [PMC6401756][cfrp-plasma] |
| Single-lap tubular CFRP tube (OD 30, 2 mm) in an L-PBF AlSi10Mg sleeve, DP490 | topology-optimised sleeve | static strength unchanged by the optimisation, fatigue life much better (ductile adhesive) | | Ascher and Spath, preprint 202503.2292 / *Materials* 18:2170 (2025) [preprint][asch25], [MDPI][asch25b] |

What this means for us:
- **Printed polyamide bonds fail at the interface, at 3.7 to 5.0 MPa**, even after blasting. That is a quarter of
  the 20 MPa the frame uses for MMA on carbon. The 6 MPa hot/wet value the 2026-11-01 printed-frame study assumed
  for MMA on flame-treated nylon has **no published source** (it was marked ASSUMPTION there).
- Plasma or flame treatment roughly doubles polyamide bonds in the studies that measured it, but no PA12 or PAHT
  value was found, so no credit is taken. The design value used in the study is **5.0 MPa dry x 0.8 hot/wet = 4.0
  MPa** (ASSUMPTION: MMA on sanded, flame-treated PAHT-CF reaches at least the best published PA12 value). Coupon
  test T6 must measure it.
- Joint strength rises with bond area up to a limit and is nearly insensitive to bondline thickness (TU Delft
  thesis on CFRP-Al tubular joints, [Lavalette 2020][delft-tube]). A soft printed adherend makes the Volkersen peak
  worse, because the load transfers near the socket lip.

## 3. Published pack-frame masses and architectures

| Frame | Architecture | Mass | Source |
|---|---|---|---|
| Stone Glacier Krux | 4 straight carbon-composite stays in an "X", fabric (500D Cordura, X-Pac) frame sheet; 150+ lb | 2 lb 12 oz with M belt (Krux); 2 lb 7 oz (Krux Evo) | [Remi Warren listing][sg-rw], [goHUNT Krux Evo][sg-evo], [Gearfool][sg-gf] |
| Exo Mtn Gear K4 | custom carbon-composite stays, plastic-sheet belt backbone; 150+ lb | 2 lb 15 oz frame system (measured 1361 g) | [Exo K4][exo-k4], [Packstack][ps-k4], [Carryology][car-k4] |
| Kifaru ARK | one carbon-fibre sheet with cross support, two lengths | 3.1 lb (3.09) frame with M belt | [goHUNT][kif-gh], [Rokslide review][kif-rs] |
| Seek Outside Revolution | 6061 Al U-frame, 7075 cross stays, belt bolted to the frame | 2 lb 9 oz at 24 in | [Seek Outside][seek-rev] |
| KUIU ICON 6 | thermoplastic carbon sheet (frame sheet only 13.7 oz) | | [KUIU whitepaper][kuiu-wp] |

Cited in-repo comparison (frame + suspension): ours 2288 g vs 1162-1400 g for those four
([weight_pass_corrie.md](../../designs/pack_5200/analysis/weight_pass_corrie.md) section 3).

Reading: the light leaders all carry the load on **straight carbon stays or a carbon sheet**, with no rigid crown
or torso rack in the frame, and most of their mass sits in foam, belt and harness. None uses printed structure. None
has our telescoping carbon crown with a rack and pawl (about 0.24 kg with its hardware) or our printed bag hard
points. That fixes a floor under any frame that keeps our interfaces.

## 4. Patents relevant to a printed-node carbon pack frame (not legal advice)

| Patent | Owner | What it claims (plain words) | Risk | Design-around |
|---|---|---|---|---|
| US 10,668,965 "Nodes with integrated adhesive ports and channels" ([PDF][pat-965]) | Divergent Technologies | AM node with built-in adhesive injection ports and channels that route adhesive into the tube joint | **Medium** if our knuckles had injection ports | Butter the tube and the socket and push it in (no ports, no internal channels); or the TENDON route, where the load-carrying bond is a hand-laid wrap |
| US 10,605,285 / US 10,480,555 / US 11,174,884 "Systems and methods for joining node and tube structures" ([285][pat-285], [555][pat-555], [884][pat-884]) | Divergent | node with tube-engagement protrusions engaging the tube ID and OD, adhesive between; vehicle structures | **Medium** for a double-lap spigot socket, depending on the claims | Ask counsel. TENDON has no spigot; the printed former sits only outside the tube |
| US 11,110,514 "Apparatus and methods for connecting nodes to tubes in transport structures" ([PDF][pat-514]) | Divergent | node-to-tube connection features (claims directed to transport structures) | Low to medium | as above |
| US 10,952,523 B2 "Backpack with pop up frame" | Mystery Ranch | load lifters move to the frame top in an extended mode | Unchanged guardrail: lifters stay on the crown top bar (DECISIONS 2026-11-01) | Crown and lifters unchanged in every concept |
| USRE48,093 E1, US 9,095,203 B2, US 9,636,875 B2 | KUIU | one-piece moulded / laminated slotted carbon frame with a U-tongue | Low: our frames are multi-part tube frames | Do not move to a one-piece slotted sheet |
| Robot Bike Co, Atherton | | No patent applications found in their names (search 2026-11-09; a patent attorney's blog reports none for Atherton) | Low | [Boult Wade Tennant][bwt] |
| SG, Exo | | No patents found (pack_market_2026.md section 6) | Low; trade dress: do not copy the SG X-stay cage look | Original knuckle language |

Get a freedom-to-operate opinion before tooling, as the market research already requires.

## 5. Gaps (no source found)

- Pull-out strength of a carbon tube bonded into an FDM PA-CF socket: none published. T6 coupons must give it.
- Fatigue of adhesive bonds to printed polyamide: none found. HA-LS-1 uses 0.3 x lap shear.
- Mass or strength of a hobby drone printed node: none quantified.
- PU adhesive shear modulus (DP620NS): not on the data sheets found; the strain at break is 110 % ([3M TDS][dp620]).

## Sources

[eng-robot]: https://theengineer.co.uk/bespoke-bike-company-puts-additive-in-the-frame
[mam-robot]: https://www.metal-am.com/?p=60758
[pb-robot]: https://m.pinkbike.com/news/robot-bike-co-r160-custom-review-2016.html
[rad-bastion]: https://theradavist.com/bastian-cycles-uses-3d-printed-titanium-lugs-with-carbon-tubes
[na-bastion]: https://newatlas.com/bastion-cycles-3d-printed-titanium-bike/42066
[mam-burton]: https://www.metal-am.com/?p=117858
[cw-fenix]: https://www.compositesworld.com/articles/cfrtp-bike-frame-with-reversible-joint-connection-surpasses-classic-racing-bike-challenges
[ft-quad]: https://flitetest.com/articles/3d-printed-fpv-quadcopter
[mw-frame]: https://makerworld.com/en/models/3378057
[ap-quad]: https://discuss.ardupilot.org/t/building-a-better-quad-frame/27703/85
[fl-drones]: https://formlabs.com/industries/drones/
[pat-965]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10668965
[pat-285]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10605285
[pat-555]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10480555
[pat-884]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11174884
[pat-514]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11110514
[sed25]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12656205/
[pa12-tpu]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12824215/
[mart23]: https://mdpi.com/2076-3417/13/7/4429
[pnnl-plasma]: https://www.pnnl.gov/publications/experimental-and-numerical-study-plasma-treatment-effects-adhesive-joints-metals
[cfrp-plasma]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6401756
[asch25]: https://www.preprints.org/manuscript/202503.2292
[asch25b]: https://mdpi.com/1996-1944/18/10/2170
[delft-tube]: https://repository.tudelft.nl/record/uuid:be68fb95-335d-45d1-9a1e-b35098d6ab84
[sg-rw]: https://remiwarren.com/products/krux-frame
[sg-evo]: https://shop.gohunt.com/products/krux-evo-frame
[sg-gf]: https://www.gearfool.com/collections/gear/products/stone-glacier-krux-frame-1
[exo-k4]: https://exomtngear.com/products/k4-frame-system
[ps-k4]: https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system
[car-k4]: https://www.carryology.com/reviews-2/exo-mtn-gear-k4-review
[kif-gh]: https://shop.gohunt.com/products/kifaru-ark-frame
[kif-rs]: https://www.rokslide.com/?p=24807
[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[kuiu-wp]: https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper
[bwt]: https://www.boult.com/bulletin/a-dream-mountain-bike-courtesy-of-additive-manufacture/
[dp620]: https://www.3market.cz/user/related_files/3m____scotch-weld____urethane_adhesive_dp620ns_black_20230309.pdf
