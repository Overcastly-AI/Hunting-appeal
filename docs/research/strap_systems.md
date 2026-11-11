# Strap systems: meat carry and compression from one strap set (BL-003)

Owner: pack-designer. Dates: 2026-11-10/11. Ticket: `docs/backlog/BL-003-strap-consolidation.md`.
Used by: `designs/pack_5200/concepts/strap_arch.py`, `designs/pack_5200/analysis/strap_architecture.md`.

**Method.** Maker pages first, fetched with the web-fetch tool; quotes are verbatim from the fetched page. Where the page
did not answer and only a search-engine summary or a forum post did, the claim is marked **secondary**. Rokslide
threads are not fetched (HTTP 403 in BL-008); a claim that rests on them is secondary. Performance benchmark only:
no brand's layout, hardware arrangement, names or trade dress is copied.

## 1. How the leaders get meat carry and compression from their straps

| Brand / system | Meat carry | Compression | One strap set for both? | Strap width / hardware | Source |
|---|---|---|---|---|---|
| Stone Glacier (Krux, Xcurve, R3 frames; Sky bags) | "Load-Shelf" integrated in every frame: the bag is pulled off the frame and meat or gear packed "in between the bag and the frame" | bag compression straps; the shelf straps are extended for a pack-out | partly: shelf straps on the frame hold the meat; the bag's own straps reattach "bottom up" over it (**secondary**, SG guide via search summary) | "The load is supported by 12 connection points to the frame via 1" webbing"; "Heavy-duty, 1" Duraflex military approved buckles and webbing" | [Gearfool Krux][gf-krux]; [SG Load-Shelf][sg-shelf]; [SG load cell vs load shelf][sg-lcls]; pack-out steps: [SG One Frame for Every Hunt][sg-one] (**secondary**) |
| Exo Mountain Gear K4 | "Compression straps built into the frame offer secure compression for quarters, boned-out meat, load cells" | the same frame straps, plus an upper side strap on the bag for tall items | **yes**: "4 pairs of integrated compression straps"; with a bag on, two pairs hold the load to the frame and two pairs connect the bag; frame alone, "all 4 sets of straps can be used to secure the load" | width and buckle not stated | [Exo K4 5000][exo-5000]; [Exo frame compression straps tip][exo-tip] |
| Seek Outside (Unaweep + Revolution) | load shelf included; internal load-shelf anchor points in side-zip bags | "Eight compression straps (removable)", "Six side straps (three on each side)", "Two bottom straps", "One over the top compression strap" | **yes**: "Compression straps are moveable and removable"; "Connect two together to make extra long straps for big or awkward loads" | Gatekeeper buckles; no published strength (search 2026-11-10) | [Seek Unaweep 6300][seek-6300]; [Seek Gatekeeper sets][seek-gk] |
| Mystery Ranch (Overload) | "OVERLOAD feature provides functional expandability via a load sling between the pack and the frame" (a fabric shelf; our patent guardrail forbids one) | "Front, bottom, and side compression straps" | partly: a user review says "the black buckled straps held quarters tight to the hypalon panel" | colour-coded buckles | [MR Overload][mr-ol] |
| Kifaru (ARK frame) | "the all-new Loop Lock strap attachment system will make strapping quarters and other awkwardly shaped items much easier" | not described on the frame page | not stated; forum users run bag straps through the frame for meat (**secondary**) | no strap specs or ratings published (search 2026-11-10) | [Kifaru ARK frame][kf-ark]; [Kifaru Loop Lock][kf-ll] |

**Reading.**
1. The leaders who say how they do it (Exo, Seek) use **one set of removable 1 in (25 mm) class straps** for both compression and
   meat; the straps are frame-anchored (Exo) or movable between bag and frame (Seek).
2. Nobody describes side wings plus a separate set of wrap straps plus internal meat straps. Our five systems are unusual
   (`bag_weight_review_20261110.md` §2.1).
3. Stone Glacier states 1 in webbing at all 12 frame connection points; no leader describes 38 mm (1.5 in) meat straps.
4. **No leader publishes a strap, hook or buckle rating.** Seek's Gatekeeper and Kifaru's Loop Lock have no load figure
   on any page found.

## 2. Light rated hardware (published figures)

| Part | Mass | Published strength | Notes | Source |
|---|---:|---|---|---|
| AustriAlpin DY25K-G aluminium G-hook, 25 mm | 8 g | "Breaking load tensile strength 1.2kN"; "withstands loads up to 0.9 kN without permanent deformation" | maker page | [AustriAlpin DY25K-G][aa-25] |
| AustriAlpin DY38K-G aluminium G-hook, 38 mm | 16 g | 1.5 kN breaking load; 0.9 kN no-set | maker datasheet (PDF text) | [AustriAlpin DY38K-G datasheet][aa-38] |
| Alutica Mega Clip hook, 25 / 38 mm (anodised Al, stainless bail) | 13.0 / 14.0 g | "reasonable maximum expected working loads" 22 kg (50 lb); "Not for safely supporting human loads"; no break figure | reseller page | [Trimmers/ahh.biz Alutica][alutica] |
| Austere Mfg cam buckle with spring, 25 mm (Al, stainless, Ti pin) | 12.2 g | none published; "The design makes it almost impossible for the webbing to slip through" | reseller page; not certified | [Extremtextil Austere 25 mm][austere] |
| Cam strap buckle 25 mm (alloy) | not stated | "Cam Buckle break load = 450kg" (4.4 kN) | material from search summary (**secondary**) | [Jimmy Green 79496][jg-cam] |
| AustriAlpin DY25AFB frame buckle (Al), 25 mm | 10 g | 7.5 kN tensile | a fixed frame buckle, not an adjuster (**secondary**, search summary of the maker datasheet) | [AustriAlpin DY25AFB][aa-fb] |
| ITW Ladderloc / Super Ladderloc 25 mm (acetal) | 4 / 7 g | 687 / 981 N tensile; no maker publishes slip | already in our records | `data/materials/hardware/ladder_lock_25mm*.yaml` |
| 25 mm side-release (Duraflex/ITW class) | 9 g | 450 N break (estimate) | already in our records | `data/materials/hardware/buckle_side_release_25mm.yaml` |
| Steel 1 in wire / snap hooks (cargo) | heavy | 3300 lb assembly break, 1100 lb WLL | cargo-class; far too heavy for a pack | [Trucking Depot 1 in wire hook][td-hook] |
| Sewn loop over a pin | (webbing only) | webbing record 13344 N (25 mm) / 20016 N (38 mm); the bartack governs (ASSUMPTION 2700 N on 38 mm) | our US1/US2 already use a sewn eye on the left pin | `data/materials/webbing/poly_webbing_*mm.yaml`; `build_geometry.BARTACK_38_N` |

**Reading.**
1. A rated 25 mm aluminium G-hook (8 g, 1.2 kN) is lighter than our assumed 38 mm sliding-gate meat hook (9 g, 1500 N
   ASSUMPTION). The one rated 38 mm Al G-hook found is **16 g**, so our 9 g assumption looks optimistic.
2. Its 0.9 kN no-set load sits just below the 910 N meat-strap proof load (DECISIONS 2026-11-10, BL-016). That is a
   conflict to settle (strap_architecture.md section 10).
3. Our HAUL G-hook is booked at 4 g with no rating; the rated aluminium hooks found weigh 8 to 16 g.
4. No 25 mm cam with both a published mass and a published slip or break rating was found. The 25 mm cam stays an
   ASSUMPTION (13 g, slip 1100 N, the same slip assumption as today's 38 mm cam) until the proof test.

## 3. Design language and patents touched

Exo's frame straps and Seek's movable straps are performance benchmarks only; REC's frame-anchored wraps are our
existing W1–W3 (geometry.yaml, 2026-11-01), which predate this research. Patent guardrails checked in
`strap_architecture.md` section 6 (Eberlestock US 12,495,885 no fabric shelf; Mystery Ranch US 10,952,523 lifters on the
crown; US 8,381,956 nothing between the spreader and the z 330 cross member).

[gf-krux]: https://www.gearfool.com/products/stone-glacier-krux-frame-1
[sg-shelf]: https://stoneglacier.com/pages/load-shelf
[sg-lcls]: https://www.stoneglacier.com/blogs/the-vestibule/load-cell-vs-load-shelf
[sg-one]: https://www.stoneglacier.com/blogs/the-vestibule/one-frame-for-every-hunt
[exo-5000]: https://exomtngear.com/4800
[exo-tip]: https://exomtngear.com/blogs/article/k4-quick-tip-frame-compression-straps
[seek-6300]: https://checkout.seekoutside.com/unaweep-6300/
[seek-gk]: https://seekoutside.com/gatekeeper-set-1-hd-size-set-of-3/
[mr-ol]: https://www.mysteryranch.com/overload-pack
[kf-ark]: https://kifaru.net/collections/all/products/ark-frame
[kf-ll]: https://kifaru.net/products/ark-loop-lock
[aa-25]: https://www.austrialpin.at/en/components/thread-back-buckles/detail/dy25k-g-g-hook-aluminium/
[aa-38]: https://www.austrialpin.at/en/service/data-sheet/pdf/dy38k-g-g-hook-aluminium/
[aa-fb]: https://www.austrialpin.at/en/service/data-sheet/pdf/dy25afb-frame-buckle/
[alutica]: https://www.ahh.biz/hardware/hooks/carabiners/alutica-mega-clip-hooks.php
[austere]: https://www.extremtextil.de/en/cam-buckle-w.-spring-aluminium-austere-mfg-25mm/72713.SW
[jg-cam]: https://jimmygreen.com/webbing-restraint-straps/79496-cam-strap-buckle-25mm
[td-hook]: https://www.truckingdepot.com/1-inch-wire-hook-tie-down-hardware
