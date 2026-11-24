# BL-064 Iteration 1, materials records for the system weight levers

**Agent:** materials-engineer · **Size:** S · **Depends on:** BL-062 (`designs/pack_5200/iter1/system/iter1_weight.md`
follow-ups, `docs/research/weight_iter1.md`) · **Date:** 2026-11-24

Goal: replace the secondary figures behind the iter1 levers N1 to N7 and G-3 with sourced material records, and define
the physical test for each lever that is not yet defined. Records only. No ledger, pattern or iter1 code changes.

## Deliverables

| File | What |
|---|---|
| `data/materials/textiles/spacer_mesh_3d_230.yaml` | N1 mesh, 3 mm, 230 g/m2 (Extremtextil art. 73068), **estimate**: secondary source only |
| `data/materials/textiles/spacer_mesh_3d_320.yaml` | N2 mesh, 3 mm, 320 g/m2 (Extremtextil art. 70807), datasheet; 320 vs 390 resolved |
| `data/materials/textiles/spacer_mesh_3d.yaml` | re-sourced: stands for Shelby Outdoor 3D Spacer Mesh 4 mm; booked 380 g/m2 kept |
| `data/materials/hardware/triglide_25mm_ti.yaml` | N3 Ti tri-glide, 4 g (maker page), no rating |
| `data/materials/webbing/dyneema_webbing_25mm_thin.yaml` | N6 webbing, 10.2 g/m, 12 000 N, no slip data |
| `data/materials/hardware/slider_8.yaml` | G-3 #8 coil slider, 8.5 g |
| `tests/test_materials.py` | one assertion updated: the `zipper_size=8` hardware query now also returns `slider_8` |

## 1. Records and key values

| Record | Key values | Source (fetched 2026-11-24) | Confidence |
|---|---|---|---|
| `spacer_mesh_3d_230` | 230 g/m2 (6.8 oz/yd2), 3.0 mm, 1600 mm roll, PES, slightly elastic, EUR 12.90/m incl. VAT (USD 7.38/m2 ex VAT) | Extremtextil art. 73068. **Secondary**: search-engine summary only. The product page returns 404 to the fetch tool and the 3D-mesh category page no longer lists it (special-price item, may be gone). | estimate |
| (fallbacks in the 230 record) | Rockywoods 3.0 mm coloured 7.7 oz/yd2 = 261 g/m2; Rockywoods DNB138 mil-spec 7.95 oz/yd2 = 270 g/m2, 2.8 mm. Both sold out today | rockywoods.com product pages | datasheet (vendor) |
| `spacer_mesh_3d_320` | 320 g/m2 (9.4 oz/yd2), 3.0 mm, 1600 mm roll, PES, inelastic, shrink ≤ 5 % in wash, EUR 19.90/m (USD 11.39/m2 ex VAT) | Extremtextil art. 70807 product page | datasheet |
| 320 vs 390 | **Resolved.** The maker page says: "From July 2026, this product has changed slightly. The weight is now 320g/sqm instead of 390g/sqm." Old stock or reseller lots can still be 390. **Weigh a swatch on receipt** (accept 320 ± 10 %). | same | – |
| (alternative in the 320 record) | Shelby Outdoor 3D Spacer Mesh 3 mm: 330 g/m2 ± 10 %, 160 cm, **Martindale ≥ 35 000 rev at 9 kPa, breaking force ≥ 150 N (EN ISO 13934-1)**. The only spacer mesh found with published wear data | shelbyoutdoor.com p106303 | datasheet (vendor) |
| `spacer_mesh_3d` (re-sourced) | Booked 380 g/m2 kept (ledger-safe). Stands for Shelby Outdoor 3D Spacer Mesh 4 mm: 350 g/m2 ± 5 %, ~4 mm, 150 cm. Market bracket 340 (RBTR 1/8 in) to 400 g/m2 (Extremtextil 2.7 mm). Thickness 4.5 → 4.0 mm (no code reads it) | shelbyoutdoor.com p109518; RBTR; Extremtextil | estimate (booked value is an ASSUMPTION, 8.6 % over the stand-in) |
| `triglide_25mm_ti` | 4.0 g each (0.14 oz), Grade 5 Ti, USD 8.50 per **pair**; **no rating, no bar dimensions published**; sold out | brautigamexpeditionworks.com (maker). The reach.dog URL in the research file is now HTTP 410 | datasheet (mass only) |
| `dyneema_webbing_25mm_thin` | 10.2 g/m (0.11 oz/ft), 0.7 mm, **12 000 N (1200 daN, 2698 lbf)**, black/orange, EUR 2.90/m; maker: "only suitable for limited use with buckles", "can twist relatively easily" | Extremtextil art. 72979 | datasheet |
| ladder-lock / buckle slip on thin UHMWPE | **None published.** RBTR (Venom 0.6 mm UHMWPE): "increased chance for slippage … do not recommend … cinch buckles, or other buckles". Forum reports have no numbers. → test LL-D | RBTR Venom page; hammockforums thread 159464 | – |
| `slider_8` | 8.5 g (0.301 oz) single pull non-lock, USD 0.82; Shelby YKK 8C double-pull 7.3 g, 16 × 13 × 11 mm, EUR 1.00 at 500+ | rockywoods.com 34-PU-C8; shelbyoutdoor.com p105339 | datasheet (vendor) |

What the records change for the iter1 levers (scaling of the BL-062 figures, not re-run):
- **N1** stands at −45.1 g only if the 230 g/m2 article can be bought. If it can't, the 261 to 270 g/m2 Rockywoods
  meshes give −35.8 / −33.1 g (45.1 × (380 − m) / 150).
- **N2:** at 320 g/m2, −6.3 g as booked. A 390 g/m2 old lot gives +1.1 g, so the lever is gone. The Shelby 3 mm at
  330 g/m2 gives −5.3 g, and it has wear data.
- **N3:** the mass is now the maker's figure, 4 g. The price is USD 4.25 a part (iter1 assumes USD 12). Strength is
  still unknown: TG-TI and US-BS-Ti below.
- **N6:** the break is 12 000 N, not 11 768 N (iter1 read daN as kgf, which errs 1.9 % on the safe side). Slip is
  unpublished, so the lever stays PENDING LL-D.
- **G-3:** with `slider_8` on the door the change saves another 2 × (19.0 − 8.5) = **−21.0 g**.
  `weight_push.door_zip8()` keeps the 19 g #10 sliders.

## 2. Physical test specs for the iter1 levers

None of these existed before this ticket except US-BS, HB-1, LL-H, PT-7 and MT-1, which are defined in
`designs/pack_5200/physical_test_kit.py`. The tests below reuse their fixtures, conditions and the LL-H freezer rule
("COLD" means a home freezer at −18 °C or colder, accepted as −20 °C). Pass lines marked ASSUMPTION are engineering
choices that the pack-designer or structural agent should confirm before the test lot is ordered.

| Test | Lever | Method (standard) | Samples | Pass line |
|---|---|---|---|---|
| **MESH-1a** abrasion | N1, N2 | Martindale, **ASTM D4966** / **ISO 12947-2**, 9 kPa, standard wool abradant, wearer (mesh) face up. Outsourced lab: the owner has no Martindale. Run the current mesh lot as a control | 4 specimens per mesh (230, 320, control) | no hole and no broken face yarn (ISO 12947-2 knit end-point) at **20 000 rev**. ASSUMPTION: 20 000 rev from iter1 N1. The Shelby 3 mm publishes ≥ 35 000 |
| **MESH-1b** compression | N1, N2 | thickness gauge per **ISO 5084** at 1 kPa, then at 14 kPa (the back-rail comfort limit, `analysis/back_rail.md`), dry; then repeat after MESH-1a | 5 readings × 3 specimens per mesh | thickness at 14 kPa ≥ 50 % of the 1 kPa value. ASSUMPTION: no air gap collapse under the rails. Report the measured gsm (5 punches of 100 cm2) in the same session |
| **MESH-2** comfort and sweat | N1 | back panel A/B: the left half in the candidate mesh, the right in the control (swap sides for tester 3). 30 kg in the pack, 2 h walk with a 300 m climb, BP-3 FSR strips under both rails; weigh the panels dry and right after the walk | 3 testers | peak FSR candidate / control ≤ 1.10 on 3 of 3; no hot spot or rail edge felt (asked blind); sweat pick-up of the candidate ≤ control + 10 % (ASSUMPTION) |
| **HB-1** (existing) | N2 | as defined in `physical_test_kit.py`, built with the 320 g/m2 wing and lumbar faces | as defined | as defined |
| **US-BS-Ti** | N3 | the existing US-BS procedure with the Ti tri-glide as backstop: cam forced open, strap runs to the backstop, hold 1080 N (110.1 kg) for 1 min; dry, wet (10 min soak), COLD (freezer) on fresh 25 mm poly webbing each time | 3 Ti parts per condition (buy 6 = 3 pairs; reuse a part only if the caliper shows no bar set) | strap stopped within 10 mm and held 1 min, 3 of 3 per condition (the US-BS line); no bar set > 0.2 mm (caliper before and after, ASSUMPTION); no webbing cut |
| **TG-TI** | N3 | weigh 5 parts and caliper the bars; on 2 parts ramp-pull to failure at 50 mm/min in the US-BS threading (crane scale + winch, or a lab) | 5 weighed, 2 destroyed | mean mass ≤ 4.5 g; peak ≥ 1620 N (1.5 × 1080 N, ASSUMPTION) with no webbing cut below 1080 N; report the failure mode |
| **AB-2** collar rub | N4 | reciprocating rub rig: rolled B-06f collar (70D, 3 turns as built) clamped over a 25 mm crown-bar offcut with a B-25 bridle tab, ±20 mm stroke at 1 Hz, 20 N normal load (ASSUMPTION: about the bridle tension at rest, to be confirmed by the pack-designer); control: the same in ULTRA 200X | 3 × 70D + 1 control | **5000 cycles**, no hole and no coating wear-through (no light through it on a light box); control shows less or equal wear |
| **SLV-1** sleeve chafe | N5 | the same rub rig: 70D sleeve strip over the backer strip's cut carbon edge, 10 mm stroke (ASSUMPTION: stay-to-back slip), normal force = 13.8 kPa × contact area (rev C peak, `back_rail.md`; about 33 N on a 20 × 120 mm contact); control: Robic 210D | 3 × 70D + 1 control | **10 000 cycles**, no wear-through and no cut ripstop grid yarn over the edge |
| **LL-D** Dyneema in the heavy ladder lock | N6 | the LL-H procedure on `dyneema_webbing_25mm_thin`: 5 `ladder_lock_25mm_heavy` threaded as on W1-W3, paint-pen mark, hang **338 N** (34.5 kg, the W proof = 1.5 × 225 N, `loadpath_verification.md` S9) 1 h dry; then fresh webbing wet (10 min soak) 1 h; then fresh webbing COLD 10 min. **Creep:** a 24 h hang at 225 N, dry. **Data run:** 2 extra locks ramped at 50 mm/min to the first 5 mm of slip | 5 locks × 3 conditions + 5 creep + 2 ramp (fresh webbing each, about 12 m) | slip < 5 mm, 5 of 5, in each condition at 338 N; creep slip < 5 mm after 24 h; report the ramp slip onset. Any fail means polyester stays on W1-W3 |
| **LL-D box** (with LL-D) | N6 | the MT-1 box-X specimen sewn in 0.7 mm Dyneema webbing (25 × 25 box-X, tex 135, the W1-W3 stitch spec), hang 338 N for 1 min | 5 | no broken stitch and no seam slip > 2 mm, 5 of 5 (the MT-1 line at the W load) |
| **SH-1** ULTRAGrid strap and belt shells | N7 | (a) cloth strip: **ASTM D5035** 50 mm strip, warp and weft; (b) seam: **ASTM D1683** on the wing-root seam and on the J-strap-to-yoke seam as built (thread and SPI per the BOM); (c) part: J-strap-to-yoke joint hung at 478 N for 1 min (1.5 × 1.6 g × 199 N shoulder-strap tension, `frame_cg_recheck.md`; factoring rule as in `h1_rev5.md`; ASSUMPTION: pack-designer to confirm that 199 N governs). Run 330D as the control in (a) and (b) | (a) 5 warp + 5 weft; (b) 5 per seam; (c) 3 straps | (a) ≥ 25.6 N/mm along the wing (≥ 1280 N per 50 mm), the strip strength `hipbelt_structural.md` §2 credits the 330D shell with (wing SF 2.15); (b) seam efficiency ≥ 0.8 (that file's assumption); (c) 3 of 3 with no seam opening > 2 mm |
| **PT-7** (existing) + weigh | G-3 | PT-7 as defined, with `slider_8` on #8 chain; weigh 5 sliders | as defined; 5 sliders | PT-7 line; slider mean ≤ 9 g |

Cost basis for the new buys (records): Ti tri-glide 3 pairs USD 25.50; Dyneema thin about 12 m, about USD 32 ex VAT;
mesh 0.5 m of each candidate, under USD 20 each. Martindale and ASTM D5035 / D1683 are lab tests (quote before the lot).

## 3. Open questions

1. **N1 supply.** The 230 g/m2 article is unverified and may be sold out. Ask Extremtextil (stock, swatch, brightener)
   before you put N1 into the after-tests. Without it, N1 is about −33 to −36 g.
2. **Ti tri-glide supply.** BEW is sold out in both sizes. Ask for a restock date. No other 25 mm Ti tri-glide under 11 g was found.
3. **Pass-line ASSUMPTIONs** in section 2 (AB-2 normal load and stroke, SLV-1 stroke, SH-1 strap load, TG-TI 1620 N,
   MESH-1b 50 %): the pack-designer should confirm them, and the structural agent should confirm SH-1.
