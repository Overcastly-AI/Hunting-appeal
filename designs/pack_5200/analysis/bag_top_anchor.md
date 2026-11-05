# Bag-top anchoring: cloth-sim diagnosis and candidate concepts

Owner: pack-designer, 2026-11-05. **Status: diagnosis and candidate input to the bag-to-frame attachment design phase
(research-first, next).** The hardware and the attach/detach procedure are NOT chosen here; `bag_attachment.md` is
unchanged. Specified now: the IM3 hook tab (B-17), the hinge-eye doubler (B-18) and the bow riser carry.

- Problem (`cloth_sim.md` §3.2): under 68 kg the bag peels aft off the frame above the IM3 hooks (z 520). Aft depth
  goes from 339 mm drafted to 438 mm (meat) and 469 mm (fill). The load CG ends up 206 / 223 mm aft, against the 150 / 180 mm
  that HA-LS-1 C5 / C1 assume.
- Goal set for this study: a load CG of 180 mm or less, without pushing the bag into the head zone (R-28).
- Code: `huntkit/clothsim` (additive scenario keys below). Scenarios: `huntkit/clothsim/scenarios/pack5200_v31_tab_doubler.yaml`
  and `pack5200_v31_anchor_*.yaml`. Comparison and screenshots: `python designs/pack_5200/bag_top_anchor.py`
  (`outputs/clothsim/bagtop_compare.json`, `outputs/clothsim/bagtop_table.md`). CLI diffs:
  `outputs/clothsim/diff_bagtop_{tab_doubler,anchor_A_crownbar,anchor_G_stiff_forward}.md`.

```
python -m huntkit.clothsim.cli run --scenario huntkit/clothsim/scenarios/pack5200_v31_anchor_G_stiff_forward.yaml \
       --cases packed,fill,meat --no-sweep --no-render
python -m huntkit.clothsim.cli diff outputs/clothsim/pack5200_v31_baseline/results.json \
       outputs/clothsim/pack5200_v31_anchor_G_stiff_forward/results.json
python designs/pack_5200/bag_top_anchor.py
```

## 1. What changed in the simulator (additive, defaults reproduce phase 1)

| scenario key | model | why |
|---|---|---|
| `attachments.hinge.doubler_mm` | Tension legs (38 mm webbing EA) from every B-01\|B-05 seam node within ±doubler/2 of the eye into the pinned eye node. Only the eye node is pinned. | A first version pinned all three doubler nodes. Because the coarse seam curves round the corner (nodes at y 21 / 31 / 64), that locked bag rotation about the hinge, which the real pin allows (it is the bulk-mode hinge). The pinned-nodes CG gain was an artifact and has been discarded. |
| `attachments.hooks.tab: {stations, width_mm}` | Hook strap as a bridle: one elastic leg from each B-01 node across `width_mm` to the eye, pretension split. Reported summed, plus leg max. | IM3 tab B-17 |
| `attachments.ties.list[]` | A strap from a bag point (`pieces`, `at: [x, z]`, optional bridle `width_mm`, optional `via` keepers) to a fixed frame anchor. `mode: elastic` = fixed length, snug at the drafted shape. `mode: cinched` = ladder lock, re-cinched on the loaded bag (3 % take-up, same as the wraps). | Top anchor candidates |
| `contact.crown` | Rigid one-sided contact with the carbon crown, which is not in `genframe_assembled.stl` (the print stops at z 540). Legs OD 22 on the frame axis, top bar OD 18 25 mm aft of the leg axis, spine OD 20 300 mm long (`frame.yaml`, `geometry.yaml` crown). | Without it, a tie can pull the wall through the crown. |
| `model.Pins(k=array)`, report groups, `contact_crown` in results, CG rows in `diff` | | reporting |

**ASSUMPTION:** spine tube centre y = top-bar centre − 25 mm, i.e. on the leg axis (not in the frame records).

## 2. The B-01 vs spreader "3.1 mm inside" flag: checked, no redraft

The pattern's own fine B-01 mesh (`patterns_v31` V3, about 664 nodes in the spreader footprint) was compared with the
spreader STL front skin:

- Over the sheet face, the drafted B-01 sits on the skin within **0.2–0.6 mm**. The sheet leans with the stays, so the skin
  is at y 16.7 at z 190 and y 12.9 at z 390. This is fabric thickness, not interference.
- The two bonded **10/8 mm edge tubes** (top z 412–430, bottom z 112–120) stand **7–10 mm proud** of the skin, and
  the drafted B-01 runs through their crowns (max 10.1 mm at z 423). The coarse sim mesh averages this to −3.1 mm.
- A taut cloth line from the hinge (z 60) to above the IM3 tab (z 470), drawn over the two ridges (upper convex hull),
  is only **+1.2 mm (0.3 %)** longer than the drafted line. ULTRA 200 takes that as strain. Under the meat case the
  panel touches 95 % of the footprint (`cloth_sim.md` §3.5).
- **Decision: no B-01 change.** Moving B-01 3–4 mm aft would add the same 3–4 mm to every CG offset in this study
  and buy nothing. A note for the spreader owner (structural-fea-engineer): the edge tubes put two line contacts
  under the meat. If the bone-end test shows a crease there, the tubes could move to the wearer face.

## 3. Results (coarse mesh h 40, 68 kg at 1.0 g, contents CG = volume centroid, y from FCS y = 0)

Every run except the baseline carries the IM3 tab (80 mm) and the hinge doubler (80 mm), plus crown contact.
"Wall toward head" is the largest forward move of the frame-side wall at x = 0 above the crown top bar, loaded against
drafted. For scale, the R-28 check (`head_clearance`, DESIGN §4.7) leaves **6.8 mm** at 30° extension for a 23 in p50 male.
The hinge seam figure is the eye force over the 80 mm doubler. The baseline figure is a one-node peak (`cloth_sim.md` §3.4).

**fill** (HA-LS-1 C1 assumes 180 mm)

| run | concept | CG aft mm | aft depth mm | IM3 hook N | hinge eye N | hinge seam N/mm | top anchors N (1 g) | wall toward head mm | volume L |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | phase-1 bag | 223 | 469 | 324 | 242 | 4.5 | – | 0 | 83.6 |
| T0 | IM3 tab + hinge doubler only | 205 | 439 | 403 | 171 | 2.1 | – | 0 | 84.0 |
| A | crown-bar tie x ±70 at the bar (z 703, 19 in), fixed length | 192 | 414 | 387 | 167 | 2.1 | 21 / 29 | 0 | 84.3 |
| B | A + top guys, cinched 120 N, forward to the bar ends | 171 | 376 | 386 | 158 | 2.0 | guys 41 / 40 | **16** | 83.7 |
| C | tie at the collar seam z 775 (fixed frame anchor) | 180 | 397 | 398 | 161 | 2.0 | 29 / 33 | **21** | 84.5 |
| D | as A at the 15 in setting (bar z 601) | 202 | 431 | 402 | 171 | 2.1 | 17 / 8 | 9 | 84.1 |
| E | as A, cinched 80 N (soft) | 188 | 407 | 350 | 163 | 2.0 | 69 / 31 | 7 | 84.3 |
| F | A + guys cinched, down-forward to the z 420 lash points | 189 | 408 | 397 | 169 | 2.1 | guys 29 / 23 | 0 | 83.8 |
| **G** | **A + forward top guys, fixed length (stiff)** | **179** | 388 | 388 | 161 | 2.0 | guys 32 / 32 | 6 | 84.1 |
| H | A + down-forward guys, fixed length | 191 | 414 | 387 | 167 | 2.1 | guys 0 / 0 | 0 | 84.3 |

**meat** (30 kg meat on IM1–IM3 + 38 kg gear; HA-LS-1 C5 assumes 150 mm)

| run | CG aft mm | meat + gear CG mm* | aft depth mm | IM3 hook N | hinge eye N | hinge seam N/mm | top anchors N | wall toward head mm | volume L |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 206 | 181 | 438 | 338 | 374 | 6.3 (node) | – | 0 | 83.7 |
| T0 | 193 | 174 | 416 | **472** | 340 | 4.2 | – | 0 | 83.8 |
| A | 186 | 170 | 406 | 470 | 336 | 4.2 | 4 / 14 | 1 | 83.8 |
| B | 164 | 158 | 368 | 436 | 325 | 4.1 | guys 28 / 30 | **23** | 83.2 |
| C | 176 | 164 | 393 | 461 | 328 | 4.1 | 15 / 22 | **21** | 84.0 |
| D | 192 | 173 | 415 | 467 | 340 | 4.3 | 0 / 0 | 20 (z 635) | 83.8 |
| E | 182 | 168 | 401 | 433 | 334 | 4.2 | 53 / 17 | 9 | 83.9 |
| F | 182 | 168 | 398 | 472 | 341 | 4.3 | guys 32 / 27 | 2 | 82.9 |
| **G** | **174** | **163** | 384 | 450 | 329 | 4.1 | guys 20 / 20 | 12 | 83.7 |
| H | 186 | 170 | 405 | 469 | 336 | 4.2 | guys 0 / 0 | 1 | 83.8 |

\* Supplementary: the 30 kg of meat at its HA-LS-1 CG (150 mm; it is cinched to the spreader and does not follow the
bag) combined with 38 kg of gear at the bag's volume centroid. The sim's "CG" column treats the whole contents as uniform.

Accuracy: the meat cases converge (residual ≤ 0.9 N). The fill cases stop at a residual of 5–19 N (as in phase 1), so
take fill CGs as **±5 mm** and volumes as ±1 L. Differences of 2–3 mm between runs are noise.

## 4. What drives the CG (anchor height, direction, stiffness)

1. **Hold B-01 wide at IM3 first.** The 80 mm tab alone (T0) takes 13–18 mm off the CG, because the bridle holds
   the panel across its width instead of at one point. The price is that **the IM3 hook carries 40 % more**
   (338 → 472 N meat): the hook now reacts more of the bag's overturning moment. See §6.
2. **Height is the strongest lever.** A tie at the crown top bar is worth a further 7–13 mm at 19 in (A). The same tie at
   15 in (D, z 601) gains almost nothing over T0 (192 / 202 mm), and the frame-side wall bulges 20 mm toward the
   wearer above it. A tie at the collar seam (C, z 775) gives 176 / 180 mm. Roughly **−1 mm of CG for every 8–10 mm of anchor
   height** between z 600 and z 775.
3. **Direction: the anchor must pull the TOP of the bag forward, near horizontally.** Guys from the aft upper
   corners (z 760) forward to the top bar (B, G) are the only kind that reach 180 mm at 19 in. Guys run down and forward to
   the z 420 lash points (F, H) do nothing: the corner moves along their arc and they go slack (0 N when fixed length).
   Do not pursue them.
4. **Stiffness and set-up: fixed length beats cinched.** Cinched guys (B, 120 N ladder-lock model) over-pull. They
   reach 164–171 mm, but they push the top 16–23 mm toward the head. The same guys at fixed length, set snug on the
   packed bag (G), hold 174 / 179 mm with 6–12 mm toward the head. A soft cinched crown tie (E, 80 N) is a little better
   than a snug fixed one (A) on CG, but it also pulls 7–9 mm toward the head.
5. **Anchor loads are small.** No top anchor exceeds 70 N at 1 g (about 210 N at the C5 3.0 × factor). The anchor
   problem is geometry, not strength.
6. **Volume** stays at 82.9–84.5 L under 68 kg (5060–5160 cu in) in every run (baseline 83.6–83.7 L). Anchoring
   does not cost capacity.

## 5. Candidate concepts for the attachment phase

| # | concept | frame feature | fill / meat CG | head | verdict |
|---|---|---|---|---|---|
| **1** | **Crown-bar tie (A).** Two short ties from B-01u at x ±70 round the crown top bar. The bag-side point must follow the crown (z 601–779), e.g. a vertical row of tie points. | **existing** (crown top bar; the x ±70 spots of the retired LINK toggles) | 192 / 186 at 19 in; **202 / 192 at 15 in** | safe (≤ 1 mm) | Necessary but **not sufficient**: misses 180 by 12–22 mm. |
| **2** | **Crown-bar tie + fixed-length forward top guys (G).** As 1, plus two straps from the aft upper corners (face/gore seam, z ~760) forward to the top bar ends (x ±100). Length set on the packed bag, then locked (not cinched under load). | **existing** (top bar; the guy anchors share the bar with the lifter lugs at x ±105, so spacing needs work) | **179 / 174** at 19 in | **6–12 mm toward the head: borderline** against the 6.8 mm R-28 margin | **Best candidate.** The only head-plausible concept that meets 180 at 19 in. Needs the R-28 re-check with the loaded profile, and a 15 in run. |
| 3 | **High anchor at the collar seam (C).** A tie at z ~775, independent of torso. | **NEW frame feature** (not drawn; frame print files not edited): two anchor points at x ±70, z 775 ± 10 at every torso setting, bag-facing surface at y ≤ 21, rated ≥ 3 × 35 N per side. A fixed-height bar or plate on the stay tops is one way. Making the extension posts (accessory) the bag anchor is another, but it needs an IP opinion (MR US 10,952,523 concerns raising the frame top; lifters must stay on the crown). | 180 / 176 | **21 mm toward the head: fails** R-28 unless the anchor also backs the wall | Study case showing the effect of height; not recommended as drawn. |

Rejected: down-forward guys to the lash points (F, H: slack), and cinched forward guys (B: head intrusion).

## 6. Specified now (bag side)

- **B-17 IM3 bag-hook tab** (×2): 90 × 110 mm `hypalon_coated_nylon` on the outside of B-01 under the IM3 swell,
  centred on the hook-strap bartack (x ±115, z 450). The hook strap is box-X bartacked to the tab, and the tab is stitched on
  an **80 mm** wide perimeter. 19.8 g for the pair.
  - **Warning:** with the tab, the sim IM3 hook force is **450–472 N per side at 1 g** in the meat case (was 338 N), with
    the largest bridle leg 241–267 N. At the C5 3.0 × factor that is **1416 N against the assumed 1500 N hook: SF 1.06**.
  - The open hook proof test (830 N, `meat_haul_modes.md`) is **not enough** for this. The attachment phase must either test the
    hook to ≥ 1.5 × 1416 N or pick a stronger IM3 hook (or two). A top anchor relieves IM3 only a little (G 450 N, B 436 N).
- **B-18 hinge-eye doubler** (×2): 90 × 45 mm Hypalon on the inside of B-01, lower edge caught in the B-01\|B-05
  seam, centred on the eye (x ±115). The eye is box-X'd through doubler and B-01. Hinge eye force in the sim is 329–341 N (meat), so
  **4.1–4.3 N/mm over 80 mm of seam** (target < 6 N/mm; ≥ 63 mm would have been enough). 8.1 g for the pair.
- Both are compatible with both meat-haul modes and the 120 s bag-off. They are sewn to the bag and move with it. The hinge
  pins and the IM3 hooks release exactly as now. Any top anchor (candidates 1–2) adds 2 or 4 releases, about 4 s each
  (`bag_attachment.md` gloved-hand assumption), so detach goes 40 s → about 48–56 s against the 120 s limit. In `between` mode the top
  anchors must be released with the IM2/IM3 hooks so the bag can swing open.
- **Bow riser carry** (owner freeze): two 25 mm webbing loops threaded through the B-11 lash tabs on the right face,
  plus one 25 mm G-hook strap over the riser (HAUL family). The cam/limb end sits in the band cam cup (SH-04). 12.1 g.

Weight (`geometry.yaml → weight`, from `build_geometry.py`): +27.8 g load spreaders, +12.1 g bow carry, +0.9 g thread.
Pack **3030 → 3071 g (6.77 lb)**. Candidate 2's hardware (2 ties + 2 guys + 4 G-hooks or equivalent) would add about 30–40 g
(ASSUMPTION, not in the budget until the attachment phase picks it).

## 7. For the structural-fea-engineer: the CG still exceeds HA-LS-1

No head-safe anchor brings the C1 fill CG to 180 mm at every torso. The C5 meat case is above 150 mm in every run,
anchored or not, even with the meat held at 150 mm (combined 163–181 mm). **Do not wait for the attachment phase to
re-check the frame.** Suggested envelope for the re-check (ASSUMPTION, from the table above, ±5 mm sim scatter included):

| case | HA-LS-1 today | re-check at | basis |
|---|---:|---:|---|
| C1 static carry (and the other bag-carry cases) | 180 mm | **205 mm** aft, CG z ~550 | candidate 1 at 15 in: 202 (fill) |
| C5 / C7 meat on the internal straps | 150 mm | **175 mm** aft | meat + gear combined, candidate 1 at 15 in: 173 |

The load standard is not changed here. Also check the crown top bar for the anchor loads: ≤ 70 N per side at 1 g, so
≤ 210 N at C5, applied horizontally at x ±70 (candidate 1) and x ±100 (candidate 2).

## 8. Limits (in addition to `cloth_sim.md` §4)

- **One torso (19 in) for every run except D.** Candidate 2 at 15 / 23 in is not run.
- **No friction, and no roll.** The collar is a 320 mm tube closed flat at the fill line. A real rolled top with the
  HDPE stiffener is shorter and stiffer, so the real top lean is probably smaller than simulated, and all CGs here lean conservative.
- **Simplified attachments.** The bridles and doublers are point legs on a 40 mm mesh. Tab and doubler stitching is not modelled. The crown spine
  y position is an ASSUMPTION. The head is not modelled: "wall toward head" is a proxy for R-28.
- The contents CG is a volume centroid (uniform contents), which overstates the meat case. Hence the supplementary column.

## 9. Pattern-maker: regenerate

`patterns_v31.py` / `outputs/release/pack5200_v3.1_patterns` (the release is not edited here):

1. **B-01**: mark the B-17 tab placement (outside face, x ±115, centre z 450, 90 × 110, 80 mm stitch line) and the B-18
   doubler placement (inside face, centred on the hinge-eye notch, 90 × 45, lower edge in the B-01|B-05 seam allowance). **No
   change to the B-01 outline** (§2).
2. **New pieces B-17** (×2) and **B-18** (×2), Hypalon, laser-cut, no seam allowance. Add them to the cut list, the marker and the DXF/PDF.
3. **B-03 R / B-02 (right face)**: mark the bow riser loop positions through the B-11 lash tabs. Add to the webbing cut
   list two 25 mm loops of 100 mm and one 25 mm G-hook strap of 250 mm, plus one G-hook.
4. Do **not** add any top-anchor pieces yet (attachment phase).

## Screenshots

- `outputs/screens/20261105_bagtop_1.png`: side profile at x = 0, fill and meat, baseline vs candidates A, G, C, with CG markers.
- `outputs/screens/20261105_bagtop_2.png`: B-01 frame-side layout (B-17, B-18, tie heights) and the anchor directions in side view.
