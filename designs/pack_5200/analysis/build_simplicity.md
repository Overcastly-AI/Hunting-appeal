# Pack 5200 v3.1: build-simplicity audit

Owner: manufacturing-engineer. Date 2026-11-07. Status: **PROPOSAL ONLY.** Nothing here changes geometry, patterns or
YAML. The bag body shape (B-01/B-02/B-03/B-05 outlines, setback seams, swells) is out of scope: the pack-designer is
drafting alternative bodies (`concepts/`, `analysis/bag_alternatives.md`).

Numbers come from `designs/pack_5200/build_simplicity.py` → `analysis/build_simplicity_results.json`. Run
`python designs/pack_5200/build_simplicity.py` to regenerate the counts, hours and charts. Inputs:
`outputs/release/pack5200_v3.1_patterns/cutlist.csv` (pieces, perimeters, binding lengths),
`cut/attachment/README.md` and `analysis/bag_attachment.md` §5 (attachment parts, box-X, safety factors),
`panels.yaml` (webbing cut list), `geometry.yaml` (weight rows, hardware families), and the records in `data/materials/`.

Owner request: "Keep optimising and making this better but still simple to build." The builder is a first-timer with
no machine yet (DECISIONS 2026-11-01).

## 1. The build today (base pack: size M belt, J straps, fly; no lid, no rifle boot, F-03 removed)

| Item | Count | Source |
|---|---:|---|
| Cut pieces, total | **124** (69 piece types) | cutlist.csv + attachment parts + BP-06/BP-08 |
| — hand-cut fabric (rotary, from paper templates) | 73 | cutlist.csv, non-sheet materials |
| — laser / die / waterjet (bought or makerspace) | 48 + 3 composite | Hypalon, HDPE, foams (35), attachment Hypalon/HDPE/XLPE (13), BP-08 ×2, BP-06 |
| Webbing parts (hot-knifed) | 52 (104 hot-cut ends) | panels.yaml webbing_cut_list + patterns_v31 cut list + attachment README |
| Materials (sheet/roll goods) | **18** (12 sewn fabrics + 4 foams + HDPE + 2 composite) | `results.pieces.materials` |
| Colours (fabric + webbing) | ASSUMPTION ≥ 6: body solid, ULTRA stock colour, camo print (2 bases), mesh, Hypalon, webbing black / coyote / bone | geometry.yaml hardware_families; DESIGN §4.5 |
| Hardware / webbing / thread SKUs (soft goods) | **32** | §4, chart 2 |
| Stitch types | 2: ISO 301 lockstitch and 304 zigzag (bar tacks). Patterns: straight seam, double-row perimeter, box-X, bar tack, binding, topstitch | bag_attachment §5, patterns_v31 |
| Box-X load joints | **68** (36 off-bag webbing parts, 12 bag flat-work, 7 hood, 6 hipbelt, 6 harness, 1 fly tether) | ops model |
| Bar tacks (304) | **32** (12 port ends, 6 keepers, 4 ladder ends, 4 back-panel tabs, 2 HE necks, 2 roll clips, 2 hose ports) | patterns_v31 drill marks, bag_attachment §5 |
| Binding runs | **6** runs, 10.4 m: bag inside seams 3.96, shoulder straps 2.12, back mesh 1.63, band mouth SH-02 1.16 (bias camo), wings 1.16, lumbar 0.42 | cutlist.md binding rows |
| Curved 3D seams | 12.7 m (gores 4 × 0.765, bottom ring, collar ring, setback + shoulder seams, pocket and fly seams) | ops model |
| Set-in swells | 8 (16 cone-cap halves B-13..B-15) | cutlist.csv |
| Zips set | 4 (#10 diagonal, #5 fly pocket, 2 × #8 hipbelt) | cutlist.md |
| Taped seams | 0 (R-13; O-9 rejected) | — |
| Laminating / composite | BP-06 sandwich (vacuum bag, 60 °C post-cure), B-19L glued in, J heat-formed on a 19 mm dowel | cut/spreader/README.md, attachment README |
| Seam allowances in use | **6** values: 0, 8, 10, 12, 15, 20 mm | cutlist.csv |
| Proof tests | 9 rigs: PT-1..PT-6 + meat bartack, meat hook, cam (R-29) | bag_attachment §5, BUILD_PLAN §5a |
| Machines implied by the spec | walking foot that runs **tex 135**, zigzag (304), hot knife, laser, waterjet, vacuum bag + oven, 3D printer, grommet press | — |

### 1.1 Beginner hours by subassembly (ASSUMPTION model)

ASSUMPTION: minutes per operation unit are in `build_simplicity.OP_MIN`, for example box-X 8 min, curved 3D seam
35 min/m, binding 30 min/m, swell 60 min, diagonal zip 150 min, hand-cut piece 6 min. Rework is +20 % on a first
build. Calibration: the total of about 99 h is about 12 weeks at 8 h/week, inside the 10–14 week evenings-and-weekends
plan in `BUILD_PLAN.md`. Forum reports give 6–30 h for first **frameless** packs, and one builder needed 3 weeks with
"seam ripping, re-sewing" ([BPL first MYOG pack][bpl1], [BPL 60 L framed][bpl2], [r/myog][rmyog]). This pack has
68 box-X joints and 8 swells, so a few times that is plausible. Treat the hours as a ranking tool, not a quote.

| Subassembly | Now h | After h | Main driver |
|---|---:|---:|---|
| Bag flat-work (B-01 swells, ports, tabs, tongues, band, zip, shards) | 24.7 | 22.6 | **8 swells ≈ 9.6 h with rework (bag body: out of scope)**, diagonal zip 3 h |
| Cutting + kitting | 13.4 | 12.5 | 73 hand-cut pieces, 52 webbing parts |
| Proof tests + fit | 10.8 | 8.3 | 9 separate rigs |
| Bag 3D assembly | 9.0 | 6.9 | 3.96 m interior binding, gore and ring seams |
| Hipbelt (M) | 8.7 | 8.1 | 3 foam sandwiches, 1.6 m binding, 2 pocket zips |
| Composite parts (spreader BP-06) | 8.0 | 0.5 | vacuum-bag layup by a beginner (ASSUMPTION 8 h) |
| Webbing + load parts | 7.0 | 6.5 | 36 box-X |
| Harness (J) | 5.2 | 4.8 | 2.1 m binding over foam |
| Rain fly + pocket | 4.7 | 4.7 | silpoly curved seams, 3 m hem |
| Back panel | 3.0 | 3.0 | mesh binding, sleeves |
| Side pockets | 2.2 | 2.2 | |
| Crown hood | 2.0 | 1.9 | 7 box-X, J forming |
| Jig + template kit (new) | — | 2.0 | one-off, pays back in rework |
| **Total** | **98.6** | **84.0** | **−14.6 h (−15 %)**. Excludes frame printing (27 h unattended, `print/frame/PRODUCTION.md`) |

Chart: `outputs/screens/20261107_buildsimp_1.png`.

## 2. Ranked simplifications

Every load-path item states its current safety factor or test and why the change is safe. Mass and cost are per pack.
Cost uses record prices (`data/materials/*.yaml cost_usd`) unless marked ASSUMPTION.

### 2.1 Quick wins (no function, look or load change; recommend now)

| Rank | ID | Change | Hours | Mass | Cost | Load path / risk |
|---:|---|---|---:|---:|---:|---|
| 1 | **S-05** | **Outsource the BP-06 Sandwich v2 spreader** (layup, vacuum bag, post-cure, CNC route) and the BP-08 carbon backers to the composite / waterjet shop that already gets the DXFs (`cut/spreader/`). The owner only checks and fits them. | **−7.5** | 0 | ASSUMPTION +$80 labour (no quote) | Same part, same spec (BP-06 rev C: FPF 1.25, fatigue 1.09, `analysis/spreader.md`). Add incoming checks: mass 162 g ± 5 %, flat within 1 mm, notch roots R6, sealed edges. Lower risk than a first-time vacuum bag. |
| 2 | **S-14** | **One proof-test bench, one session.** A steel 5 mm pin fixture, a 300 kg crane scale and a lever or ratchet (the rig in `load_standard.md` §T1). Run PT-1..PT-6 plus the R-29 meat tests back to back, 5 samples each. | **−2.0** | 0 | ASSUMPTION $60 rig (needed anyway) | Same loads and pass criteria (`bag_attachment.md` §5 table). Only the setup is shared. |
| 3 | **S-03a** | **One thread colour** (match the body solid) for tex 90 and tex 135, and **drop `bonded_poly_tex90`**: two threads instead of three. | **−0.5** (fewer changes) | 0 | ASSUMPTION −$20 (one spool fewer) | Every perimeter capacity in `bag_attachment.md` §5 (B-17 3277 N, B-18 3277 N, B-22 1024 N, B-23 3628 N) is already computed with `bonded_nylon_tex90` (64 N), so no SF changes. Meat-zone body seams are SF ≥ 19 at 1 g (`cloth_sim.md`). Nylon loses some wet strength, and that is the condition the numbers already assume. |
| 4 | **S-02** | **Replace all 32 zigzag (304) bar tacks with 301**: a 3-pass 10 mm straight bar for the fray-stops (port ends, B-20 ends, HE necks, hose ports, keepers, back-panel tabs) and a 25 × 15 box-X for the 2 roll-clip straps. **This removes the need for a zigzag machine**, so one straight-stitch industrial does the whole pack. | 0 | 0 | 0 | No 304 tack is in any capacity calculation. Ports carry no load (B-12 note). B-20 is governed by the rung (SF 4.00) and its long-edge double rows. HE is governed by the B-18 seam (SF 2.31); its neck tack only holds the tri-fold shape. The roll-clip strap goes from a tack to a box-X, which is stronger (25 mm buckle record 450 N). |
| 5 | **S-10** | **Jig and template kit** (owner's printer + offcuts): (a) box-X marking windows 38×38, 25×25, 38×20, 50×40 with the 3 mm drill-hole pips; (b) a webbing length board with stops for all 52 parts and ID tags; (c) a **B-24 loop jig** with pins at the 120 / 170 / 220 mm apex lines (the spec is ±3 mm); (d) a 10 mm magnetic seam guide; (e) a **kitting tray per subassembly** with hardware pre-counted, checked blind with gloves (R-25); (f) L/R + face marks in silver pen at cutting; (g) a 100 mm test-square check on every print (already in BUILD_PLAN). | **−1.2 net** (−3.2 rework, +2.0 to make) | 0 | ASSUMPTION +$25 | Error-proofing only. The loop jig protects the float-gap CG numbers (127 / 158 / 189 mm, DESIGN §4.9). |
| 6 | **S-07** | **One colour for every 38 mm webbing** (bone/stone, the MEAT colour) on IM, US, B-24, eyes and tongues. Today only IM1–IM3 have a colour. HAUL coyote 25 mm stays (tactile/colour family R-25). | 0 | 0 | 0 (one roll fewer to buy) | Same material id `poly_webbing_38mm` (20 016 N): no SF changes. |
| 7 | **S-08** | **Fly pocket zip #5 → #8 coil**, the same chain and slider as the hipbelt pockets. Zip SKUs 3 → 2 in the base pack. | 0 | +2 g (0.23 m × 5 g/m + slider ASSUMPTION 1 g) | +$0.23 | Not a load path. A bigger pull is easier with gloves. |

Quick wins together: about **−11 h**, **+2 g**, about **+$145 one-off / +$80 per pack** (most of it the composite shop,
an ASSUMPTION until quoted).

### 2.2 Needs owner OK (changes look, mass or a frozen detail)

| Rank | ID | Change | Hours | Mass | Cost | Load path / risk |
|---:|---|---|---:|---:|---:|---|
| 1 | **S-03** | **Drop the 3.96 m of grosgrain binding on the main-bag inside seams.** Sew the 301 seam, add a second row 6 mm into the allowance, trim, and sear the Cordura raw edge with the hot knife. Optionally have the 10 Cordura/ULTRA body panels laser-cut at the makerspace (sealed edge, no tracing). | **−2.0** | **−20 g** (ASSUMPTION grosgrain 5 g/m, no record) | −$2 binding (ASSUMPTION $0.50/m); +$15 if laser-cut (ASSUMPTION) | No seam capacity counts the binding. Body seams SF ≥ 19 at 1 g (`cloth_sim.md`). The loaded B-01\|B-05 seam (HE/B-18) is governed by the B-05 fabric strip, 2355 N, SF 2.31, and that stays the same. **PT-3 swatches must then be built without binding**, as built. Risk: ULTRA 200 laminate edge fray and a rougher inside where game bags rub. Gate: a 3-cycle machine-wash swatch test (R-12) with no fray past the second row. |
| 2 | **S-01** | **One 38 mm hook part for all 12 hooks**: the rated ≥ 2200 N bag hook replaces the 6 meat-strap 1500 N hooks. One SKU, one proof test (PT-1 covers it), and a 1500 N hook can never be clipped into a bag position (that would be SF 1.06 at IM3, D-29). | −0.4 (one test rig fewer) | **+30 g** (6 × +5 g, `attach_system_results.json`) | **+$18** (6 × ($6 rated − $3 meat), both ASSUMPTION) | The meat legs need 605 N (R-29, factor 2.0). Hook margin goes from 2.48 to 3.64 and bag-off hook SF from 6.67 to 9.8. The **cam stays the governing part (1100 N, margin 1.82), unchanged**. It is the same sliding-gate 38 mm geometry already hooked into the same fairlead eyes on IM2/IM3, so the fit is proven. Stronger in every case. |
| 3 | **S-12** | **Make the roll-top hem B-07 from the camo 630D** and delete the SH-03 overlay. The camo then runs round the whole hem, not only the outer half. | −0.8 | +1.5 g | ASSUMPTION +$0.50 | Not a load path. Look change (accent DECISION 2026-11-01): owner call. |
| 4 | **S-13** | **Band-mouth binding SH-02: bias-cut camo 630D → the pre-folded 20 mm grosgrain** used elsewhere. One bias-cut fold-and-press piece fewer on a stretch edge. | −0.2 | +0.7 g | −$0.30 | Not a load path. The storm-flap edge loses its camo stripe. If S-03 is taken, grosgrain is still bought for the belt, lumbar, straps and back mesh. |
| 5 | **S-09** | **Three seam allowances only: 0 (laser/die), 10 (every seam), 20 (every hem or channel)**. Non-body pieces now (8 → 10: HP-01/02, B-08; 15 → 20: B-16 sides, BP-05 top, H-10 top). The body's 12 mm (bound) and the 8 mm swell caps move to 10 when the pack-designer's new body is drafted, if S-03 is taken. | not modelled (fewer wrong-guide errors) | < ±2 g | 0 | Seam lines don't move, only the cut line. Pattern-maker regenerates. Not a load path. |
| 6 | **S-15** | **Robic 210D → Cordura 330D** for BP-05 rail sleeves, BP-07 pad back and the H-10 wedge sleeve (210D's only uses since F-03 left). One fabric fewer to buy. | 0 | **+7.5 g** (0.188 m² × 40 gsm) | −$0.54/pack, and no 1 yd minimum buy (~$18) | Not a load path: the sleeves hold the rails, and the spreader and frame take the load. 330D abrades better against the BP-08 carbon edges. |
| — | linked | O-5 (bottom B-05 → ULTRA 200, owner on hold, `bag_weight_plan.md`): if adopted, move B-16 to ULTRA too. 500D then only remains on the rifle-boot accessory, and the base pack loses one more fabric. | 0 | −7.6 g (O-5) | +$1.56 (O-5) | as O-5 |

With the S-03/S-01/S-12/S-13 set: about **−3.4 h**, **+12 g** net (−20 + 30 + 1.5 + 0.7), about **+$16** per pack.

### 2.3 Rejected or flagged (with the reason)

| ID | Idea | Why not now |
|---|---|---|
| X-1 | **Run tex 90 everywhere so a portable Sailrite LSZ-1 class machine (Tex 30–92 max, [Sailrite][sr]) can sew the whole pack** | The biggest possible machine saving (about $1k portable vs a $1.5–2.5k industrial, ASSUMPTION), but it touches every box-X. On the `bag_attachment.md` formula a box-X drops by 64/98 = 0.65: T3 5256 → 3432 N (the rated hook, SF 1.55, still governs), HE 3432 N (the B-18 seam, SF 2.31, still governs), B-24 loop 4089 → 2670 N (SF 2.84 > hook 2.34). The meat-strap end bartack (ASSUMPTION 2700 N at tex 135) would drop to about 1760 N against the 605 N requirement. **Lifter, hipbelt-strap and stabilizer box-X loads are not on file anywhere.** T1(c) hangs 102 kg on the straps and lifters, and BUILD_PLAN quotes a 3.3 kN proof. **FLAG → structural-fea-engineer**: a per-joint table of factored loads for every harness/hipbelt box-X and a go/no-go for tex 90. Not recommended until then. |
| X-2 | Delete the B-23 backing under T2 | T2 tear-out capacity without it (box-X through ULTRA 200 alone) has no number. SF 9.00 today is with the backing. FLAG → structural. |
| X-3 | Hipbelt wings turned (bagged) instead of bound | The wing shell carries belt tension to the 50 mm box-X, and the R-03 rifle tabs are caught in the bottom binding (rifle-boot load). Load path with no SF on file. FLAG → structural. Hipbelt binding stays. |
| X-4 | Shoulder straps turned instead of bound (S-04) | The model gives **no hour saving** (+0.4 h: turn, stuff two foams, close the end, topstitch, against binding). It is −10.6 g, but it changes how the sternum rails and the lifter box-X sit in the harness, which is load path (T1(c)). Not worth it. Bind with a clip-and-two-pass method. |
| X-5 | Merge B-01/B-01b/B-01u, merge face pieces, drop the swells | **Bag body: out of scope** (pack-designer concepts). For that work: the 8 swells are the largest single block of beginner time (≈ 9.6 h with rework, ~10 % of the build), and every IM/hinge port and bar tack sits on them. A body that needs no swells, or a pressing form for the cone caps, is the biggest build lever left. |
| X-6 | Webbing ladder (daisy chain) instead of the laser-cut B-20 Hypalon ladders | Load path (rung SF 4.00, 17 rungs at 12.7 mm pitch = one per crown setting). A daisy-chain pitch does not match the crown rack. Keep. |
| X-7 | Remove the back-mesh BP-01 binding | Spacer mesh curls and frays at a cut edge on the wearer side. Keep. |
| X-8 | Off-the-shelf pack cover instead of the fitted fly | Integrated fly is owner-frozen (R-27, "fly counts in base"). |
| X-9 | Diagonal zip #8 or one slider | Owner rejected (O-13/O-14, §4.11 freeze). |
| X-10 | One comfort foam (EVA 30C belt vs perforated EVA straps) | Outsourced die-cut, so no sewing hours. It is a comfort and breathability choice: materials-engineer. |
| X-11 | Buy a bartack machine (Juki LK-1900 class) or outsource bartacks | Not needed. Every load joint is a 301 box-X, and after S-02 there is no 304 tack. Most box-X go through bag panels and can't be sent out. Off-bag webbing parts (36 box-X) could go to a sail loft only if the owner's machine can't run tex 135. |
| X-12 | Binder attachment | About 6 m of binding remains after S-03. Clip-and-two-pass is fine for one prototype. Revisit for batches. |
| X-13 | Merge the 25 mm and 38 mm tri-glides, or the 25 mm and 38 mm cams | Different webbing widths. The 38 mm cam is already one part on IM and US. |

## 3. Hardware and SKU consolidation

32 → 27 soft-goods SKUs (chart `outputs/screens/20261107_buildsimp_2.png`):

| Family | Now | After | Removed |
|---|---:|---:|---|
| Hooks | 3 | 2 | 1500 N meat hook (S-01, owner OK) |
| Zips | 3 | 2 | #5 coil (S-08) |
| Toggles + small parts | 7 | 6 | pawl-release strap toggle → same POM 30×8×5 toggle as the hood (ASSUMPTION: it fits the release cord, check on the bench) |
| Webbing + binding | 6 | 5 | second 38 mm colour (S-07) |
| Thread | 3 | 2 | bonded poly tex 90 (S-03a) |
| Buckles (50 SR, 25 SR, Fidlock), adjusters (25 LL, 25/38 tri-glide, 25/38 cam), elastic | 10 | 10 | kept: tactile families R-25 or different widths |

## 4. Minimal machine and tool kit (beginner, first pack)

Prices are ASSUMPTIONs from retail listings, not quotes.

**Buy first**
1. **Single-needle compound-feed (walking-foot) industrial lockstitch with a servo motor and table**: Juki DU-1181N, or
   a used Consew 206RB-class. ASSUMPTION $1,000 used to $2,300 new. Juki lists thread #40–#8, DP×17 needles size
   14–23 and a 15 mm knee lift ([Juki DU-1181N][juki]), so it runs the **tex 135 box-X** and stacks of up to 6 layers
   plus webbing. The servo lets a beginner sew stitch by stitch. Straight stitch only is enough after S-02.
   - Needles (DP×17 / 135×17), round point R (no leather-cutting points on coated fabric or ULTRA laminate):
     Nm 90/14 with tex 70 for silpoly and 100D; Nm 100/16 with tex 90 for the body; Nm 125–130/20–21 with tex 135 for box-X.
   - Stitch: 301; body 8 SPI (3.2 mm); box-X 7 SPI (3.6 mm) with a 3-stitch backtack (`bag_attachment.md` §5).
2. **Hot knife** for webbing ends and searing Cordura edges: ASSUMPTION $60–100.
3. Rotary cutters 45/60 mm, a 600 × 900 mat and 6 × 24 in rulers (BUILD_PLAN $90). Wonder clips, 6 mm basting tape
   (zips), awl, seam ripper, silver pen.
4. **Proof-test rig** (S-14): a 300 kg crane scale, a steel 5 mm pin fixture, and a ratchet or lever. ASSUMPTION $60.
5. 8 mm grommet press ($30), kitchen scale ($15), and a heat gun plus 19 mm dowel for the hood J (ASSUMPTION $25).

**By hand:** thread cams, hooks, tri-glides and ladder locks; set the toggles; set the grommets; glue B-19L; heat-form
the hood; tie and seal the Dyneema pull loops; girth-hitch and test-fit on the frame.

**Outsource:** Hypalon/HDPE/XLPE laser parts (makerspace, from `cut/attachment/*.dxf` and the release DXFs); foam
die-cut (EVA 45C/30C/perforated, XLPE); BP-08 waterjet; **BP-06 composite (S-05)**; camo sublimation print; frame print
(owner printer, 27 h, or a service). Optional: laser-cut the 10 body panels (S-03).

**Do not buy yet:** a bartacker, a binder attachment, a zigzag machine or a domestic "heavy-duty" machine. A domestic
machine or a Sailrite LSZ-1 tops out around tex 90 and cannot run the tex 135 box-X spec unless X-1 comes back
cleared.

## 5. Owner decisions needed

1. **S-03** drop the main-bag interior binding (−2.0 h, −20 g, −$2), after a wash-test swatch.
2. **S-01** one rated hook for all 12 hooks (+30 g, +$18, error-proof, one proof test).
3. **S-12 / S-13** camo hem instead of the SH-03 overlay, and grosgrain instead of the camo band-mouth binding (look changes).
4. **S-09** three seam allowances (pattern-maker regenerates the non-body pieces).
5. **S-15** retire Robic 210D for 330D (+7.5 g, one fabric fewer).
6. Machine: a walking-foot industrial (recommended), or wait for the structural answer on **X-1** (tex 90 / portable machine).

Hand-offs: **structural-fea-engineer**: X-1 (per-joint factored loads for the lifter, hipbelt-strap, stabilizer and
meat-strap box-X; go/no-go at tex 90), X-2 (T2 without B-23), X-3 (turned hipbelt). **pack-designer**: X-5 (the swells
are ~10 % of the build). **pattern-maker**: S-09 after owner OK. **materials-engineer**: records for grosgrain 20 mm,
the rated 38 mm hook, the 25/38 mm tri-glides and the 38 mm cam.

## 6. Assumptions

- Minutes per operation (`OP_MIN`), rework 20 % (12 % with jigs), composite layup 8 h: beginner estimates. Calibrated to
  BUILD_PLAN's 10–14 weeks and to forum first-pack reports (below). No time study yet: log real times on prototype 1.
- Op quantities: lengths from cutlist.csv perimeters. Seam lengths for the 3D body (tier seams 0.9 m, setback and
  shoulder seams 0.8 m, collar ring 1.2 m) and the fly (2.7 m) are estimates from the piece outlines.
- Prices: composite labour $80, laser $15, jigs $25, rig $60, thread spool $20, grosgrain $0.50/m and 5 g/m (no
  record), meat hook $3 and rated hook $6 (existing ASSUMPTIONs in `bag_weight_plan.py` / `attach_system_results.json`),
  machine prices.
- Colour count (≥ 6): no colourway file exists for the pack yet.

## Sources

- [Sailrite Ultrafeed LSZ spec (thread range Tex 30–92, zigzag 0–5 mm)][sr]
- [Juki DU-1181N spec sheet (thread #40–#8, needle 14–23, knee lift 15 mm)][juki]
- First-pack build times: [BPL "first MYOG pack"][bpl1], [BPL "60 L framed backpack, first real MYOG project"][bpl2], [r/myog first pack][rmyog]

[sr]: https://www.sailrite.com/Sailrite-Ultrafeed-LSZ-Walking-Foot-Sewing-Machine-110V
[juki]: https://www.juki.co.jp/industrial_e/admin/pdata/filedata/321/du1181n.pdf
[bpl1]: https://backpackinglight.com/forums/topic/first-myog-pack
[bpl2]: https://backpackinglight.com/forums/topic/60l-framed-backpack-my-first-real-myog-project-finished/
[rmyog]: https://lr.eu.psf.lt/r/myog/comments/1d1n17b/i_made_my_first_backpacking_pack

## Screenshots

- `outputs/screens/20261107_buildsimp_1.png`: hours by subassembly, now vs after
- `outputs/screens/20261107_buildsimp_2.png`: hardware/webbing/thread SKU consolidation
