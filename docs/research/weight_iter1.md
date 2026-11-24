# Iteration 1, system weight: research (BL-062)

Owner: pack-designer. Date: 2026-11-24. Ticket: `docs/backlog/BL-062-iter1-weight.md`. Companion analysis:
`designs/pack_5200/iter1/system/iter1_weight.md`.

**Method.** Maker pages first, then retailers, then reviews. Every number has a URL or points to an earlier cited
repo research file that has one. If a page did not render for the fetch tool, or the figure comes only from a
search-engine summary, it is marked **secondary**. "Inference" marks arithmetic on a brand's own numbers.
Conversions: 1 lb = 453.592 g, 1 oz = 28.3495 g, 1 USD = 1/1.09 EUR (ASSUMPTION, the same rate the repo's records use).

Scope (ticket): everything except the frame body and its pins and hardware. The frame is being worked on separately
(structural track).

## 1. Answer in six lines

1. **Leaders publish line items for frame, bag and lid, never for the hipbelt or the harness on their own.** SG,
   Exo, Kifaru and KUIU sell the frame "with belt" (and harness) as one number. The only split we can get is by
   inference (section 2).
2. **Our non-frame suspension (back panel + spreader + belt + harness) is already level with the leaders.** After the
   tests it is 954 g. KUIU's ICON 6 "suspension" by inference is 1052 g (with hip pouches), and SG's whole Krux
   (frame, belt, harness, shelf) is 1105 g. The excess is the frame body: 1387 g after the tests, against a 388 g
   KUIU frame. The frame track owns that lever, not this ticket.
3. **On quiet woven fabrics the bag shell is at the floor.** ULTRAGrid 210D (132 g/m²) is already in after-tests.
   The only lighter Challenge cloth found, ULTRA 100X (122 g/m²), is a PET-film laminate (louder) and only 8 % lighter
   than ULTRA 200X. DCF and other laminates break the quiet rule (owner-frozen).
4. **Three material levers are real and new:** 3D spacer mesh at 230–320 g/m² in place of the ~380 g/m² estimate we
   book; thin UHMWPE (Dyneema) webbing at 10.2 g/m in place of 18 g/m polyester, but only where no buckle grips it
   (the maker says "limited use with buckles"); and a titanium tri-glide at 4 g in place of the 11 g stainless
   backstop (secondary).
5. **Hardware is near its floor.** A CNC-aluminium 25 mm ladder lock is 5.8–9.2 g, against our 7 g heavy acetal lock.
   That is no saving, and it is unrated for slip. Lighter rated hooks than AustriAlpin's 8 g G-hook were not found.
6. **What the leaders make modular:** lids (SG, Exo), hipbelt pockets (SG, Exo, Seek, Kifaru separate; KUIU
   removable), bottle holders (Exo, KUIU), compression straps (KUIU, Seek removable) and the hydration sleeve (SG
   separate). Nobody makes the meat carry modular. It is in the frame weight (SG shelf, Exo frame straps).

## 2. Line-item weights of the leading 5000+ cu in meat haulers

| Pack | Item | Published | g | Source |
|---|---|---|---:|---|
| Stone Glacier | Krux frame (EVO) "with medium belt" | 2 lb 7 oz | 1105 | SG frames page: "Krux Frame - 2 lbs. 7oz. with medium belt" ([SG frames & bags][sg-fb]) |
| Stone Glacier | Xcurve frame with medium belt | 3 lb 1 oz | 1389 | same page ([SG frames & bags][sg-fb]) |
| Stone Glacier | Krux (original) with medium belt | 2 lb 12 oz | 1247 | [Gearfool Krux][gf-krux] (repo: `published_weight_definitions.md` 2.1) |
| Stone Glacier | Sky 5900 bag only | 2 lb 4.2 oz | 1026 | [SG Sky 5900][sg-sky] (repo 2.1) |
| Stone Glacier | Sky lid | 6.1 oz | 173 | [SG lid][sg-lid] (repo 2.1) |
| Stone Glacier | Krux hipbelt / harness alone | not published | – | search of SG and retailer pages 2026-11-24: belt only sold with the frame ([goHunt Krux EVO][gh-krux-evo], [SG frames & bags][sg-fb]) |
| Exo | K4 frame system (frame, belt, harness) | 2 lb 15 oz | 1332 | [Exo K4 frame][exo-frame] (repo 2.1); Packstack lists 1361 g (**secondary**, [Packstack][ps-k4]) |
| Exo | EXS frame (22 in, thinner harness) | 2 lb 11 oz | 1219 | **secondary** (search summary of [Exo EXS][exo-exs]) |
| Exo | K4 5000 bag only / lid | 2 lb 6 oz / 8.1 oz | 1077 / 230 | [Exo K4 5000][exo-5000], [Exo lid][exo-lid] (repo 2.1) |
| Exo | hipbelt pouch / Nalgene holder | 3.4 / 3.8 oz | 96 / 108 | [Exo pouch][exo-pouch] (repo 3, **secondary**) |
| KUIU | ICON 6 frame REG / TALL | 13.1 / 13.7 oz | 371 / 388 | SPECS table ([KUIU whitepaper][kuiu-wp], fetched 2026-11-24) |
| KUIU | ICON 6 6000 bag only / lid | 2 lb 15.9 oz / 7.7 oz | 1350 / 218 | same |
| KUIU | ICON 6 6000 full kit (frame, suspension, bag) | 6 lb 2.4 oz | 2790 | same |
| KUIU | **suspension (belt + harness + hip pouches), inference** | – | **1052** | 2790 − 1350 − 388 (TALL frame; lid assumed out, as the table lists it separately). Inference |
| Kifaru | ARK frame with M / L belt | 3 lb 1.4 oz / 3 lb 2 oz | 1400 / 1417 | [goHunt ARK][gh-ark] (repo 2.1) |
| Kifaru | Duplex Lite frame, M belt, long straps | 3.5 lb | 1588 | **secondary** (search summary of [Kifaru Duplex Lite][kf-dl]) |
| Kifaru | small belt pocket | 2.8 oz | 79.5 | **secondary**, forum weighing ([Rokslide Kifaru weights][rs-kf], 403 to the fetch tool) |
| Seek Outside | Revolution frame, 24 in | 2 lb 9 oz | 1162 | [Seek Revolution][seek-rev] (repo 2.1) |
| Seek Outside | Revolution minimum (cross stays and extra compression off) | 2 lb 3 oz | 992 | same page; cross stays "about 4 oz", over-the-top strap "about 2 oz" (**secondary** for the two part figures, search summary of the same page) |
| Seek Outside | harness / hipbelt (L) | 8.4 / 10.4 oz | 238 / 295 | **secondary**: a Backpacking Light forum post about a Seek pack, model not stated ([BPL forum][bpl-seek]) |

**Reading for us.** Our after-tests split (belt M, base, from `weight_rollup_v2`):

| our function | g | nearest leader figure | g | note |
|---|---:|---|---:|---|
| frame body + crown + hip mount (out of scope) | 1387 | KUIU ICON 6 frame (TALL) | 388 | the gap: 3.6x |
| back panel + spreader + belt + harness | 954 | KUIU suspension (inference) | 1052 | ours is lighter, without hip pouches |
| frame + suspension | 2341 | SG Krux EVO (frame, belt, harness, shelf) | 1105 | +1236 g, nearly all frame body |
| hipbelt | 393 | SG 3-piece belt (repo `hipbelt_fit.md` 3) | 363 | +30 g |
| bag shell + pockets + fly pocket + compression | 584 | SG Sky 5900 bag only | 1026 | SG's bag includes its own compression |

So in this ticket's scope the system is at or below the leaders, part by part. Real grams outside the frame can come
only from materials that are lighter than the leaders use, or from moving features to add-ons.

## 3. Lighter material options with spec sheets

### 3.1 Fabrics (quiet rule: no film laminates on brushed faces)

| Material | g/m² | Strength / abrasion | Quiet | Source | Verdict |
|---|---:|---|---|---|---|
| ULTRAGrid 210D (in after tests, record) | 132 | Taber 1100 (Challenge scale; ≈ 330D CORDURA); tear "does not tear" (D2261) | 3 | [Challenge EcoPak guide 2023][ecopak23], [Extremtextil ULTRAGrid][et-ug] (record `ultragrid_210d_uhmwpe_ripstop`) | already used on the bag body; **candidate for the harness and belt shells** (330D, 180 g/m², record) |
| Challenge ULTRA 100X | 122 | tear and Taber not on the page | 2 (PET film) | [RBTR ULTRA 100][rbtr-u100] | rejected: 8 % under ULTRA 200X (133 g/m²), louder, no published tear |
| ULTRA 200X (in use on B-01, B-06f, floor, record) | 133 | tear 459 / 593 N, Taber 4400 | 2 | record `challenge_ultra_200` | kept on B-01 / floor (abrasion) |
| 70D nylon ripstop PU (in use on collar B-06, record) | 92 | Elmendorf tear 52 / 37 N, Martindale >10000 | 3 | record `nylon_ripstop_70d` (RBTR data sheet) | **candidate for the frame-side collar B-06f** (now ULTRA 200X) |
| DCF / DCF hybrid | 18–150 | – | 1–2 | records `dcf_*` | rejected: crinkle (owner-frozen quiet rule, R-4 in `weight_push.md`) |

### 3.2 Spacer mesh (body faces: back panel, J-straps, belt)

We book `spacer_mesh_3d` at 380 g/m², 4.5 mm (record, **ESTIMATE**: "supplier listings 300–450 gsm").

| Mesh | g/m² | Thickness | Source |
|---|---:|---:|---|
| 3D mesh, 3 mm, inelastic, polyester | 320 | 3.0 mm | Extremtextil category listing, art. 70807, €19.90/m ([Extremtextil 3D mesh][et-3d], fetched 2026-11-24). The product page title for the same article says 390 g/m², so the gram figure conflicts (**check on a swatch**) |
| 3D mesh, 2.7 mm, inelastic | 400 | 2.7 mm | same listing, art. 73187 |
| 3D mesh, 3 mm, COOLMAX, elastic | 330 | 3.0 mm | same listing, art. 70847 |
| 3D mesh, 3 mm, slightly elastic, polyester | **230** | 3.0 mm | **secondary**: search summary of Extremtextil art. 73068 (1600 mm roll, €12.90/m); the product page returned 404 to the fetch tool |

No maker publishes abrasion or compression data for these meshes. A lighter face is a comfort and wear question,
not a load path, so it needs physical gates (section 5) and a materials record before anything is booked.

### 3.3 Webbing (25 mm)

| Webbing | g/m | Break | Source | Note |
|---|---:|---:|---|---|
| heavyweight polyester (in use, record `poly_webbing_25mm`) | 18 | 13.3 kN (ESTIMATE) | record | – |
| polyester 25 mm, standard (Extremtextil) | 18 | 4.9 kN (500 daN) | **secondary** (search summary of [Extremtextil PES 25][et-pes25]) | no lighter polyester found |
| security webbing, HT polyester 25 mm | 26 | 8.8 kN | **secondary** ([Extremtextil security 25][et-sec25]) | heavier |
| **Dyneema thin 25 mm, 100 % UHMWPE** | **10.2** | 11.8 kN (1200 daN), 0.7 mm | [Extremtextil Dyneema thin 25][et-dy25] (fetched 2026-11-24): "suitable only for limited use with buckles", "can twist fairly easily", black, €2.90/m | lighter by 43 %; no buckle slip data |
| Dyneema 25 mm, standard | 21.1 | 16.1 kN, 1.1 mm | **secondary** ([Extremtextil Dyneema 25][et-dy25s]) | heavier than our polyester |

### 3.4 Hardware

| Part | g | Rating | Source | vs ours |
|---|---:|---|---|---|
| tri-glide 25 mm, stainless (in use, US backstop) | 11 | 3.75 kN | record `triglide_25mm` (Extremtextil art. 70460) | – |
| **tri-glide 25 mm, titanium** (Brautigam Expedition Works) | **4** | not published | **secondary** (search summary of the [Brautigam listing][bew-tg]); sold in pairs | −7 g each; needs a backstop pull test |
| ladder lock 25 mm, CNC aluminium (Austere pin) | 5.78 | not published | **secondary** ([Wizard Works Austere][ww-austere]) | −1.2 g vs the 7 g heavy acetal (ASSUMPTION mass); slip unrated |
| ladder lock 25 mm, aluminium "ergonomic" | 9.2 | 3.26 kN break | **secondary** ([Extremtextil alu ladderlock][et-alu-ll]) | heavier |
| G-hook 25 mm aluminium (in use) | 8 | 1.2 kN break, 0.9 kN no-set | record `g_hook_25mm_aluminium` (AustriAlpin data sheet) | no lighter rated hook found |
| 25 mm cam, CNC aluminium (in use) | 12.2 | slip 1100 N (ASSUMPTION) | record `cam_25mm_al` | the owner fixed the aluminium cams |

### 3.5 Foam

The belt and J-strap load foams are already XLPE L200 in after-tests (BL-037). No lighter closed-cell foam with a
datasheet and a compression set at least as good was found in this pass. No new lever.

## 4. What the leaders make modular

| Brand | Modular / sold separately | Fixed | Source |
|---|---|---|---|
| Stone Glacier | lid ("comes standard", not in the headline), hipbelt accessory pockets, hydration sleeve | load shelf in the frame, bag-to-frame webbing (12 points) | [SG Sky 5900][sg-sky], [SG lid][sg-lid], repo `published_weight_definitions.md` 2.2; frames and bags "interchangeable" ([SG frames & bags][sg-fb]) |
| Exo | lid in the system, hipbelt pouch and Nalgene holder sold separately, no rain cover | meat straps "built into the frame" | [Exo K4 5000][exo-5000] (repo 2.2) |
| KUIU ICON 6 | bags swap on one frame; hip-belt pouches removable and replaceable with a holster, a hydration holder or a bear-spray holder; daisy-chain compression straps removable | lid not sold separately | [KUIU whitepaper][kuiu-wp] (fetched 2026-11-24) |
| Seek Outside | hipbelt pockets optional; 8 compression straps removable; cross stays removable (−4 oz, secondary) | load shelf included | [Seek Unaweep 6300][seek-6300], [Seek Revolution][seek-rev] |
| Kifaru | lid not included; belt pockets sold separately (secondary weighing) | sewn Nalgene pockets | repo 2.2; [Rokslide][rs-kf] (**secondary**) |

**Pattern:** pockets and lids are add-ons everywhere. Compression is removable at KUIU and Seek. The meat carry is
part of the frame at every brand.

## 5. What this research changes in our proposal

- **Mesh:** a supplier record at 230 and 320 g/m² is needed before booking (materials-engineer follow-up). Gates: a
  Martindale / brush wear test on the mesh face and a 3-tester comfort and sweat carry.
- **Dyneema webbing:** use it only on runs with no buckle grip, or prove slip on the heavy ladder lock first. The
  haul wraps run through ladder locks, so that swap carries real risk (aggressive option only).
- **Ti tri-glide:** the 4 g figure is secondary and no rating is published. It needs a record plus the existing US-BS
  backstop test, run on Ti.
- **Fabrics:** ULTRAGrid on the J-strap and belt shells uses a fabric already gated for the bag body (owner swatch +
  strip test). No new fabric class.
- **Modular:** leader practice supports moving pockets (FP-L/R, IMP-4, IMP-6, and if the owner agrees IMP-2 / IMP-5L)
  to add-ons that ship in the box. On the as-hunted mass that costs grams, because toggles and loops weigh something.

[sg-fb]: https://stoneglacier.com/blogs/the-vestibule/stone-glacier-frames-bags
[sg-sky]: https://www.stoneglacier.com/products/sky-5900-xcurve-krux
[sg-lid]: https://www.stoneglacier.com/products/sky-series-lid
[gf-krux]: https://www.gearfool.com/products/stone-glacier-krux-frame-1
[gh-krux-evo]: https://shop.gohunt.com/products/krux-evo-frame
[exo-frame]: https://exomtngear.com/collections/k4-pack-systems/products/k4-frame-system
[exo-exs]: https://exomtngear.com/exsframe
[exo-5000]: https://exomtngear.com/4800
[exo-lid]: https://exomtngear.com/lid
[exo-pouch]: https://exomtngear.com/products/k4-hipbelt-pouch
[ps-k4]: https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system
[kuiu-wp]: https://www.kuiu.com/blogs/do-your-research/icon-6-pack-system-whitepaper
[gh-ark]: https://shop.gohunt.com/products/kifaru-ark-frame
[kf-dl]: https://www.Kifaru.net/products/duplex-lite-frame
[rs-kf]: https://rokslide.com/forums/threads/kifaru-weights-for-the-ounce-counters.66046/
[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[seek-6300]: https://checkout.seekoutside.com/unaweep-6300/
[bpl-seek]: https://backpackinglight.com/forums/topic/why-the-divide-is-so-heavy/
[ecopak23]: https://static1.squarespace.com/static/62018e9b29f2cd0fc23c3a0c/t/63d8117224b90b2859f159a4/1675104626522/2023_EcoPak-Guide_v3.pdf
[et-ug]: https://www.extremtextil.de/ultragrid-210den-recycling-nylon-with-white-uhmw-pe-ripstop-132g-sqm/72595
[rbtr-u100]: https://ripstopbytheroll.com/products/challenge-ultra-100
[et-3d]: https://www.extremtextil.de/en/fabrics/spacer-fabrics/3d-mesh
[et-pes25]: https://www.extremtextil.de/en/webbing-polyester-25mm.html
[et-sec25]: https://www.extremtextil.de/en/security-webbing-polyester-25mm.html
[et-dy25]: https://www.extremtextil.de/en/dyneema-webbing-100-dyneema-thin-25mm/72979
[et-dy25s]: https://www.extremtextil.de/en/dyneema-webbing-100-dyneema-25mm/71976
[bew-tg]: https://reach.dog/shop/brautigam-expedition-works/products/titanium-tri-glide
[ww-austere]: https://www.wizard.works/shop/accessories/accessories-brands/austere/preorder-austere-pin-ladder-lock/
[et-alu-ll]: https://www.extremtextil.de/en/ladderlock-25mm-aluminium-ergonomic.html
