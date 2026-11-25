# Metal-stay frames with printed joints: research for BL-080 (2026-11-25)

Owner: pack-designer. Purpose: the cited basis for the BL-080 architecture study
([frame_concepts.md](../../designs/pack_5200/iter2/frame_concepts.md)). It covers how framed hunting packs build their
frames, published frame weights and prices, patents on stay-to-hub frames, user pain points, US stock and prices for
6061 / 7075 tube and flat bar, bending options, and material data. Other brands are **performance benchmarks only**:
no shapes, names or trade dress are copied.

Rules: every claim has a URL. Where a site blocked fetching (Rokslide, Metals Depot, OnlineMetals, McMaster, TW
Metals, Justia: HTTP 403 on 2026-11-25), the claim comes from the search-engine snippet and is marked
**(secondary)**. Earlier in-repo research is reused by link, not re-fetched:
[pack_market_2026.md](pack_market_2026.md), [light_frame_architectures.md](light_frame_architectures.md),
[fixed_vs_adjustable_frames.md](fixed_vs_adjustable_frames.md).

## 1. How framed hunting packs build their frames

| Frame | Stays / members | Joints and hip / yoke interfaces | Fit adjustment | Source |
|---|---|---|---|---|
| Seek Outside Revolution | 6061-T6 aluminium U-frame (tube), **7075 cross stays** | "Patented Articulating Frame"; the hipbelt is bolted to the bottom of the frame through a grommet and screw, and swivels up and down; 2 belt grommets set the lower connection | frame height 24-28 in, 2 / 4 in extensions | [Seek Revolution][seek-rev], [Seek Peregrine][seek-per], [BPL Divide review][bpl-divide] (frame described as rigid U, belt swivels), [GearJunkie Unaweep][gj-unaweep] (secondary: "bolted directly to the bottom of the frame") |
| Kifaru Duplex / DT (legacy) | two **flat aluminium stays, about 1 in wide**, hand-bent to the back; composite stays (carbon + wood) offered "with exactly the same rigidity" | stays slide in sleeves of the frame sheet / belt | stay length 22 / 24 / 26 in; owners bend aluminium stays to their spine | [Kifaru composite stays][kif-stays]; alloy 7075 vs 6061 unresolved: forum posts cite "1 in by 1/8 in 7075" (older) and "1 in by 1/4 in 6000 series" (newer) ([Rokslide WTK thread][rs-kifal], secondary) |
| Stone Glacier Krux / Krux Evo | four carbon-composite stays in an X, sewn into a fabric frame sheet | no rigid hub: belt and harness on the frame sheet | harness height by hook-and-loop | [pack_market_2026.md](pack_market_2026.md) §2, [goHUNT Krux Evo][gh-evo] |
| Exo Mtn Gear K4 | two custom carbon stays + carbon links joined by sewn Cordura; plastic sheet runs from the lumbar into the belt | sewn joints | 4 frame heights | [Exo K4][exo-k4], [pack_market_2026.md](pack_market_2026.md) |
| Mystery Ranch Guide Light MT | sources conflict: "removable 7000 Series aerospace aluminum frame" (MR workbook) vs carbon stays in an X (goHUNT) | stays sewn into the frame body | patented Futura yoke micro-adjusts torso length | [MR S24 workbook][mr-wb] (secondary), [goHUNT Metcalf][gh-mr] (secondary) |
| Barney's / Frontier Gear of Alaska freighter | classic aircraft-aluminium tube frame, folding shelf on aluminium pins | welded / pinned tube frame | fixed | [GunsAmerica review][ga-fga] (8.5 lb frame + bag with shelf and top bar removed; USD 619 dated) |
| Sitka Mountain Hauler, Eberlestock Modframe | 6061-T6 tube frame; aluminium + polycarbonate | | waist sizes / "unlimited" torso | [pack_market_2026.md](pack_market_2026.md) |

Reading:
- **Metal tube frames are the heavy-hauler standard** (Seek, Barney's, Sitka). The one light, high-rated metal frame
  (Seek Revolution, 2 lb 9 oz, 200+ lb) is a **6061 tube U** with 7075 cross members and the belt bolted to the frame.
- **Flat aluminium stays** (Kifaru) are prized because owners can bend them to their back, and Kifaru states that
  "flexible" stays are not suitable for a real pack: rigidity is the design goal, not flex ([Kifaru][kif-stays]).
- Nobody publishes how the stays join the hip mount, lifters and yoke beyond "bolted" (Seek) or "sewn" (SG, Exo).

## 2. Published frame weights and prices (benchmarks only)

| Frame (frame + suspension as sold) | Weight | Rating | Price (USD) | Source |
|---|---:|---|---:|---|
| Seek Outside Revolution 24 in | 2 lb 9 oz (1162 g); 2 lb 3 oz minimum, cross stays out | 200+ lb (frame "> 300 lb vertical") | 385 | [Seek Revolution][seek-rev], [Seek Peregrine][seek-per] |
| Stone Glacier Krux Evo | 2 lb 7 oz (1105 g), M belt | 150+ lb | 300 (retailer) | [goHUNT][gh-evo], [Reach.dog][rd-evo] (secondary price) |
| Stone Glacier Krux | 2 lb 12 oz (1247 g) | 150+ lb | 399 (retailer) | [Gearfool][gf-krux] (secondary) |
| Exo K4 | 2 lb 15 oz (1332 g); measured 1361 g | 150+ lb | 384.99 | [Exo K4][exo-k4], [Packstack][ps-k4] |
| Kifaru composite stay kit (stays only) | "up to 9 oz" lighter than aluminium stays | | 116 (CAD storefront) | [Kifaru][kif-stays] |

These are frame + harness + belt weights; our comparison basis in this study is the **frame body only** (H1 1069.3 g,
H1c 1404.7 g, BL-077 §8), so the leaders' numbers are a ceiling check, not a like-for-like target.

## 3. Patents on stay-and-hub frames (screen, not legal advice)

| Patent | Owner | Plain claim / feature | Risk to a metal-stay + printed-joint frame | Design-around |
|---|---|---|---|---|
| US 11,759,000 B2 (pub. US 2021/0393023 A1), "Backpack frame", granted 2023-09-19, est. expiry 2035-10 | Cabela's LLC | two pairs of side rails that **cross** (X rail sets) between upper and lower cross members, narrowest between them; an extensible inverted-U tube above the upper cross member, height set by a spring pin in holes in the rails | Low: our stays are a single parallel pair, no crossed rails; our crown telescopes inside the stays on a rack + pawl, not a spring pin in rail holes | Keep two parallel stays; no X rail sets; no spring-pin hole row in the stays ([Google Patents][pat-000]) |
| US 7,793,809 B2 "Backpack frame", est. expiry 2028-10 | Here Be Dragons LLC (Howell) | panel frame: base and top panels, side rails angled in to a stabilising rib and out again, concave cut-outs with radii 25-75 % of rail width | Low: a moulded panel frame, not tube stays | Do not adopt a one-piece panel with a waisted rib ([Google Patents][pat-809]) |
| US 8,381,956 B2 / US 8,561,866 B2 "Backpack frame system" (+ US 7,673,777) | Mystery Ranch (Gleason) | stays captured in sleeves on a membrane; flexible joints between stays; yoke adjusted on the membrane by hook-and-loop with an adjuster blade | Low-medium for the yoke only if we moved to a membrane-mounted hook-and-loop yoke (we do not: our yoke rides the crown spine, and hook-and-loop is banned in hunt mode) | Keep the crown-spine yoke ([US 8,381,956][pat-956], [US 8,561,866][pat-866]) |
| US 10,952,523 B2 "Backpack with pop up frame" | Mystery Ranch | lifters move to the frame top in an extended mode | Unchanged guardrail: lifters stay on the crown top bar | [pack_market_2026.md](pack_market_2026.md) §6 |
| Seek Outside "Patented Articulating Frame" | Seek Outside | number not published on the product pages; the feature is a U-frame with a belt bolted at the frame bottom that swivels | **Medium for concept B with a belt bolted to a bottom bar.** Unknown claims | Keep the H1 centre Ti hip pivot (one boss on the lumbar member); ask counsel to search the Seek assignee before any bolted-bottom-bar belt ([Seek][seek-rev]) |
| US 4,214,685 (K-2, 1980), US 4,307,826, US 4,194,656, US 4,015,759 | various | tubular frames with pivoting hip connectors, hip tubes, offset shafts into belt sockets | Expired (20-year term from the 1970s-80s filings) | Prior art that tube stays + a centre hip pivot are old and free ([US 4,214,685][pat-685], [US 4,015,759][pat-759]) |
| KUIU USRE48,093 / US 9,095,203 | KUIU | one-piece slotted laminated frame | Low (unchanged): multi-part metal frame | [pack_market_2026.md](pack_market_2026.md) |
| Divergent node-to-tube patents (US 10,668,965 etc.) | Divergent | AM nodes with adhesive injection ports, tube engagement features | Low if printed parts clamp or bolt (no injected bond ports) | [light_frame_architectures.md](light_frame_architectures.md) §4 |

The patents found do not claim a twin parallel tube stay frame joined by bolted or clamped nodes with a centre hip
pivot; that architecture is decades old (expired tubular-frame patents above).

## 4. User pain points

| Pain point | Evidence | What it means for us |
|---|---|---|
| **Frame squeaks and creaks** at contact points (frame vs bag, frame vs belt, plastic hardware) on KUIU, Exo, Mystery Ranch, Kifaru | many Rokslide threads ([Pack squeak cure][rs-squeak], [MR Metcalf loud squeaks][rs-mr], [KUIU frame noise][rs-kuiu], [Exo squeaking][rs-exo]) (secondary); cures: tape at contacts, paraffin wax, graphite, loosening side tension straps | Metal-to-metal and metal-to-print joints must be **preloaded tight or isolated**: no sliding contact under gait. Every clamp gets a thin TPU or UHMWPE liner at the tube, every bolted joint a threadlocker and a torque value; quiet-mode test in the build plan |
| **Aluminium stays bend** under heavy loads, or are bent on purpose to fit | Kifaru owners bend aluminium stays to their back; Kifaru warns flexible stays shift load to the shoulders ([Kifaru][kif-stays]; [Rokslide][rs-kifal], secondary) | A thin flat stay is the wrong section for a 150 lb meat load with a 190-205 mm CG offset (concept A numbers). A tube keeps its shape; fit comes from the crown and the hip pivot, not from bending the stay |
| **Fit adjustment** is a top buyer criterion; SG / KUIU use hook-and-loop harness height, Exo uses 4 frame heights, Seek 24-28 in frames | [pack_market_2026.md](pack_market_2026.md) §2-3, [fixed_vs_adjustable_frames.md](fixed_vs_adjustable_frames.md) | Keep the telescoping crown (legs slide inside the stays). A tube stay gives the bore for free; a flat stay needs a printed sleeve, which is the part that fails |
| **Meat-mode disassembly** is fiddly | Outdoor Life best-elk-packs (secondary, search snippet) | unchanged by this study (bag and attachment carry over) |

## 5. Stock, prices and forming (US, small quantity)

| Stock | Spec | Price (USD) | Weight | Source |
|---|---|---:|---|---|
| 7/8 in OD x .049 in 6061-T6 drawn tube | ID 0.777 in | 48 in: 30.00 (12 in 12.50, 24 in 18.75) | 0.15 lb/ft | [Speedy Metals p-4568][sm-875-049] |
| 7/8 in OD x .065 in 6061-T6 drawn tube | ID 0.745 in | 48 in: 38.88 (by the inch 0.90) | 0.0162 lb/in | [Speedy Metals p-4569][sm-875-065] |
| 7/8 in OD x .035 in 6061-T6 tube | ASTM B210 | 6 ft: 34.39 (Zoro Select) | 0.11 lb/ft (OnlineMetals) | search listings: [Zoro][zoro-875-035], [OnlineMetals][om-875-035] (secondary) |
| 1 in OD x .049 in 6061-T6 drawn tube | ID 0.902 in | 48 in: 34.56 (by the inch 0.80) | 0.0144 lb/in | [Speedy Metals p-4586][sm-1-049] |
| 3/4 in OD x .035 in 6061-T6 drawn tube | ID 0.680 in | 48 in: 19.96 (by the inch 0.46) | 0.0077 lb/in | [Speedy Metals pc-4563][sm-750-035] |
| 1/2 x 1 in 7075-T6 flat bar (the nearest cited 7075 flat) | cold finish | 12 in: 20.00; by the inch 1.11 | 0.05 lb/in | [Speedy Metals p-2689][sm-7075-flat] |
| 7075-T6 drawn **tube** | OD 1/2-3 in stocked by TW Metals (aerospace distributor) | no small-quantity price found; not on McMaster / Speedy / OnlineMetals in 7/8 in | | [TW Metals][tw-7075] (secondary); McMaster lists 7075 bar, sheet, angle but no round tube in the search ([McMaster 7075][mc-7075], secondary) |
| SendCutSend laser tube cutting (6061-T6 round 0.75 x .063, 1.0 x .063, 1.5 x .065 in...) | +/-0.005 in cut features, max 60 in | from USD 39 per order, instant quote | | [SCS tube][scs-tube], [SCS tube service][scs-tube-svc] |
| SendCutSend sheet bending | aluminium 5052 / 6061 0.040-0.125 in; **no bending on 7075** (cracks) | instant quote | | [SCS bending FAQ][scs-bend], [SCS 7075][scs-7075] |

Reading:
- **6061-T6 drawn tube is the beginner's alloy**: stocked in every size we need, cut to length by the inch, USD 30-39 for
  both stays. **7075 tube is not a small-quantity stock item** in our sizes; 7075 is available as flat bar and plate.
- A 7/8 in tube at .049 wall has a 19.74 mm bore: the existing OD 16 crown legs slide in with a 1.8 mm UHMWPE
  bushing (frame.yaml v2 used an 18.4 mm bore). The crown kit carries over.

Bending:
- 6061-T6 tube cracks below about 3.5-4 D bend radius; a 3 D die is "on the edge" ([RogueFab][rf-bend]); The Fabricator
  notes bendability falls from O to T4 to T6 ([Fabricator][fab-6061]). Annealing then bending leaves the tube near O / T4,
  well below T6 strength, so a home anneal is not acceptable for a stay (a forum claim that 6061 "returns to T6 in about
  a week" is wrong: natural ageing reaches T4, T6 needs artificial ageing; [Wikipedia 6061][wiki-6061]).
- Hand benders for 3/4 in tube with a 3 in radius cost USD 140-290 (Yellow Jacket, Imperial) ([search listing][hf-bend],
  secondary), **over the USD 50 tool cap**. Harbor Freight offers no mandrel bender ([SlashGear][sg-hf], secondary).
- 7075-T6 has low cold formability ([Wikipedia 7075][wiki-7075]); a 7075 flat stay can only take a gentle hand bend
  over a former (a plywood jig), which is how Kifaru owners shape stays (secondary).
- Conclusion: **straight stays** (the v2 / H1 stay axis is already straight, `geometry.yaml` `stay_lower_R` /
  `stay_upper_R` collinear) need no bending at all. A bent U needs a bending service (quote only).

## 6. Material data (records)

- `alu_6061_t6` and `alu_7075_t6` already exist in `data/materials/metals/` with MMPDS S-basis yields (241 / 462 MPa),
  fatigue limits (96.5 / 159 MPa, R. R. Moore, 5e8) and costs per kg, but their sources carry no URLs.
- Added: **`alu_6061_t6_drawn_tube.yaml`**, the stock form this study chooses, with cited minimums (290 / 240 MPa,
  ASTM B241 / B210 drawn tube under 1 in, [ASTM B241 snippet][astm-b241] secondary; [Wikipedia 6061][wiki-6061]),
  the AA bearing yield 386 MPa at e/D 2 and the 97 MPa R. R. Moore fatigue limit ([Wikipedia 6061][wiki-6061];
  AA typical data sheet as quoted in search, secondary), the Speedy Metals prices above, and the stock sizes.
- Materials-engineer handoff (not blocking): a cited **notched / joint S-N curve** for 6061-T6 tube with a transverse
  hole and a clamp (MMPDS 3.6.2 or the Aluminum Design Manual fatigue categories) to replace the Basquin + Kt
  screen used here; a cited **friction coefficient** for anodised 6061 on TPU / PAHT-CF clamp liners, wet.

## 7. What this means for BL-080

1. Use **6061-T6 drawn tube stays**, straight, cut by the inch; no bending tools.
2. Keep the **crown legs inside the stays** (the tube gives the bore); fit stays adjustable without bending stays.
3. Join with **bolts and clamps**, not bonds; printed parts only in bearing or clamping (BL-077 / BL-079 lesson).
4. Keep the **centre Ti hip pivot** (patent-clean versus a bolted bottom-bar belt).
5. Every joint preloaded and lined against squeak; a quiet test in the build plan.

[seek-rev]: https://checkout.seekoutside.com/revolution-suspension-and-frame/
[seek-per]: https://sectionhiker.com/out/wukjpg1z
[bpl-divide]: https://backpackinglight.com/seek-outside-divide-4500-review/
[gj-unaweep]: https://gearjunkie.com/packs/seek-outside-unaweep-6300-review
[kif-stays]: https://kifaru.net/en-ca/products/composite-stay-kits
[rs-kifal]: https://rokslide.com/forums/threads/wtk-kifaru-aluminum-stays.421510/
[gh-evo]: https://shop.gohunt.com/products/krux-evo-frame
[rd-evo]: https://reach.dog/shop/1-shot-gear/products/stone-glacier-krux-evo-frame
[gf-krux]: https://www.gearfool.com/products/stone-glacier-krux-frame-1
[exo-k4]: https://exomtngear.com/products/k4-frame-system
[ps-k4]: https://www.packstack.io/reviews/pack/exo-mountain-gear-k4-frame-system
[mr-wb]: https://issuu.com/mysteryranch/docs/s24_mr_outdoor_wb_issuu
[gh-mr]: https://gohunt.com/browse/gear-lists-and-reviews/new-2024-mystery-ranch-metcalf-hunting-backpacks-just-released
[ga-fga]: https://gunsamerica.com/digest/hunt365-frontier-gear-of-alaska-pack-review
[pat-000]: https://patents.google.com/patent/US20210393023A1/en
[pat-809]: https://patents.google.com/patent/US7793809B2/en
[pat-956]: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8381956
[pat-866]: https://patents.google.com/patent/US8561866
[pat-685]: https://patents.google.com/patent/US4214685
[pat-759]: https://patents.google.com/patent/US4015759
[rs-squeak]: https://rokslide.com/forums/threads/pack-squeak-cure.179512/page-2
[rs-mr]: https://rokslide.com/forums/threads/mystery-ranch-metcalf-loud-squeaks.318235/
[rs-kuiu]: https://rokslide.com/forums/threads/kuiu-pack-frame-help-the-noise-is-making-me-insane.114946/
[rs-exo]: https://rokslide.com/forums/threads/exo-squeaking.34140
[sm-875-049]: https://speedymetals.com/p-4568-78-od-x-0049-wall-tube-6061-t6-aluminum.aspx
[sm-875-065]: https://speedymetals.com/p-4569-78-od-x-0065-wall-tube-6061-t6-aluminum.aspx
[sm-1-049]: https://speedymetals.com/p-4586-1-od-x-049-wall-tube-6061-t6-aluminum.aspx
[sm-750-035]: https://www.speedymetals.com/pc-4563-8371-34-od-x-0035-wall-tube-6061-t6-aluminum.aspx
[sm-7075-flat]: https://speedymetals.com/p-2689-12-x-1-7075-t651-aluminum-cold-finish.aspx
[zoro-875-035]: https://www.zoro.com/tw-metals-78-od-x-0035-wall-6061-seamless-aluminum-tubing-6-ft-42935-6/i/G9422290/
[om-875-035]: https://www.onlinemetals.com/en/buy/aluminum/0-875-od-x-0-035-wall-x-0-805-id-aluminum-round-tube-6061-t6-drawn/pid/20531
[tw-7075]: https://www.twmetals.com/7075-drawn-aluminum-tubing.html
[mc-7075]: https://www.mcmaster.com/aluminum/material~aluminum/material~7075-aluminum
[scs-tube]: https://sendcutsend.com/materials/tube/6061-aluminum/
[scs-tube-svc]: https://sendcutsend.com/services/tube-cutting/
[scs-bend]: https://sendcutsend.com/faq/what-materials-are-available-for-bending/
[scs-7075]: https://sendcutsend.com/materials/7075-aluminum/
[rf-bend]: https://www.roguefab.com/aluminum-pipe-benders/
[fab-6061]: https://www.thefabricator.com/article/bending/strategies-for-bending-6061-t6-aluminum
[wiki-6061]: https://en.wikipedia.org/wiki/6061_aluminium_alloy
[wiki-7075]: https://en.wikipedia.org/wiki/7075_aluminium_alloy
[hf-bend]: https://www.zoro.com/imperial-lever-bender-34-in-3-in-radius-364-fha-12/i/G0983884/
[sg-hf]: https://www.slashgear.com/1933880/harbor-freight-tube-bender-how-much-cost-is-tool-any-good-user-review
[astm-b241]: https://store.astm.org/b0210_b0210m-26.html
