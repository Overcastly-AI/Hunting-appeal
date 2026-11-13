# Bag-to-frame attachment system

Owner: pack-designer. Attachment phase, 2026-11-05; hood relieved at the crown corner wraps 2026-11-06 (2.5); float mode with the B-24 stand-off links replaces the hinge swing 2026-11-06. This is the whole joint between the Spine bag and the printed branch frame, bottom to top: hinge eyes, under-straps, IM2/IM3 bag hooks, a **crown hood** on the top bar and two **top side guys**. The frame side (fairleads, pins, sleeves, their FEA) is unchanged and is kept at the end as the 2026-11-01 record. Research: `docs/research/bag_attachment_research.md`. Load standard: HA-LS-1 rev B.

Code: `huntkit/gendesign/attach_system.py` (system, sims, strengths, drawings, screens) and `huntkit/gendesign/bag_attach.py` (fairleads; `write_docs` / `docs_only` write this file). Numbers: `analysis/attach_system_results.json`. Drawings: `cut/attachment/attachment_parts.pdf` / `.dxf` (1:1).

## Decision

- **Top anchor: crown hood + two fixed-length top side guys** (cloth-sim runs PR15/PR19/PR23, hood lip relieved at the corner wraps). Load CG, 68 kg fill (C1): **189 / 179 / 170 mm** at 15 / 19 / 23 in (before: 223 mm at 19 in). Meat case (C5 contents): 181 / 174 / 166 mm; with the meat at its HA-LS-1 150 mm: 167 / 163 / 159 mm.
- **The 180 mm goal is met at 19 and 23 in and missed at 15 in by 9 mm on the fill case** (meat case on the line). Nothing on the frame is higher than the 15 in top bar (z 601); every concept simulated is worst there. Owner choice 1 below.
- **Head clearance R-28 passes** at every torso with the simulated wall and the hood on the bar: first contact **31 deg or later** (requirement > 30 deg).
- **IM3 hook fixed**: all four bag hooks become one **rated >= 2200 N** part, proof PT-1 at **2120 N**, which is 1.5 x the C5 IM3 load of 1415 N (hood-off case). SF on the rated hook **1.55** (was 1.06).
- **Bag off 52 s** (limit 120 s), bag on 59 s, float mode 128 s with the meat loaded, bag-off haul 108 s. Estimates for gloved hands, not a timed trial.
- **Float mode replaces the hinge swing (owner 2026-11-06).** For bulk meat the bag comes off its pins, the meat goes on the frame (cradle + IM1-IM3) and the bag hangs upright behind it on two B-24 stand-off links clipped to the IM3 eyes, at a 120 / 170 / 220 mm gap. The bag never pivots in use. The hinge pins, HE eyes and B-18 doublers stay: they are the bag's bottom anchor in bag-on mode (factored 1019 N per side, section 5) and the bag is still put on by tipping it onto them. Links: +54.4 g, their own weight group (section 11). Study: `analysis/meat_carry_alternatives.md`; research: `docs/research/meat_carry_mechanisms.md`.
- **Mass +128 g**: pack 3316 -> **3444 g (7.59 lb)**. Marginal cost about **$16**. No new frame feature.

## 1. The joint, bottom to top

| # | station | frame side (unchanged) | bag side | closer | bag off | float mode |
|---|---|---|---|---|---|---|
| 1 | hinge, z 60 | fairlead, UHMWPE sleeve | HE eye on B-18 doubler | tethered 5 mm 7075 pull-pin (cord pull loop) | pull | pull (tethered to the bag) |
| 2 | US1 z 95, US2 z 142 | cradle fairleads, eye L, cam R | B-16 floor channels | 38 mm cam + tri-glide | pop, slide off (straps stay) | pop, slide off; the straps are the meat cradle |
| 3 | IM1, z 190 | captive eye | none (meat strap only) | - | - | meat strap |
| 4 | IM2, z 330 | captive eye | T2 tongue + B-23 backing | rated 38 mm hook | unclip | unclip (keeper) |
| 5 | IM3, z 520 | captive eye | T3 tongue on B-17 | rated 38 mm hook | unclip | T3 hook into a B-24 link loop; link hook on the IM3 eye |
| 6 | crown top bar, z 601-804 | carbon bar, OD 18 | B-19 hood on 2 x B-20 ladder (one rung per setting) | gravity + peel seat it; lift tab to release | lift | lift, lies on the bag top |
| 7 | top side guys | via the hood | TG from the hood ears to B-22 on B-02d (x +/-149, z 752) | ladder lock + tri-glide, set once | come with the hood | come with the hood |

Lifters stay on the crown corner wraps (not part of the joint). W1-W3 stay the haul wraps / carry compression.

## 2. Top anchor

### 2.1 What was simulated

`python -m huntkit.clothsim.cli run --scenario huntkit/clothsim/scenarios/pack5200_v31_att_<run>.yaml --cases packed,fill,meat --no-sweep --no-render`. Coarse mesh h 40, 68 kg at 1 g. Every run except the baseline has B-17, B-18 and crown contact; W3 moves with the crown. Fill CGs are +/-5 mm (fill cases stop at a 4-19 N residual, as in phase 1); meat cases converge. New sim key: `attachments.pocket` (CONTRACTS 7).

| run | torso | concept | fill CG | meat CG | meat at 150 + gear | IM3 1 g N | top anchor 1 g N | R-28 first contact deg (fill / meat) | gap at 30 deg mm |
|---|---:|---|---:|---:|---:|---:|---|---|---:|
| baseline | 19 | phase-1 bag, no top anchor (before) | 223 | 206 | 181 | 338 | - | 33 / 33 | 4.9 |
| T0 | 19 | IM3 tab B-17 + hinge doubler B-18, no top anchor | 205 | 193 | 174 | 472 | - | 33 / 33 | 4.9 |
| A | 19 | crown-bar tie x +/-70 (study A) | 192 | 186 | 170 | 470 | CT_R 4, CT_L 14 | 33 / 33 | 4.9 |
| D | 15 | crown-bar tie at 15 in (study D) | 202 | 192 | 173 | 467 | CT_R 0, CT_L 0 | 33 / 33 | 4.9 |
| G | 19 | study G: crown tie + fixed forward guys | 179 | 174 | 163 | 450 | CT_R 0, CT_L 0, TG_R 20, TG_L 20 | 33 / 33 | 4.9 |
| G15 | 15 | study G at 15 in | 189 | 183 | 168 | 440 | CT_R 0, CT_L 0, TG_R 12, TG_L 13 | 33 / 32 | 3.4 |
| G23 | 23 | study G at 23 in | 167 | 164 | 158 | 432 | CT_R 3, CT_L 14, TG_R 20, TG_L 22 | 33 / 33 | 4.9 |
| L19 | 19 | load lifters counted as the top anchor | 180 | 175 | 164 | 458 | LF_R 26, LF_L 20 | 33 / 33 | 4.9 |
| P15 | 15 | crown hood only | 201 | 190 | 172 | 462 | pocket 0 | 33 / 33 | 4.9 |
| P19 | 19 | crown hood only | 186 | 182 | 168 | 456 | pocket 24 | 33 / 33 | 4.9 |
| P23 | 23 | crown hood only | 180 | 175 | 164 | 457 | pocket 29 | 33 / 33 | 4.9 |
| PG15 | 15 | crown hood (full-width lip, 2026-11-05) + top side guys | 189 | 181 | 167 | 439 | TG_R 10, TG_L 11, pocket 0 | 33 / 31 | 0.6 |
| PG19 | 19 | crown hood (full-width lip, 2026-11-05) + top side guys | 177 | 173 | 163 | 448 | TG_R 18, TG_L 20, pocket 3 | 33 / 33 | 4.9 |
| PG23 | 23 | crown hood (full-width lip, 2026-11-05) + top side guys | 168 | 165 | 158 | 434 | TG_R 21, TG_L 23, pocket 3 | 33 / 33 | 4.9 |
| PR15 | 15 | crown hood, lip relieved at the corner wraps + top side guys | 189 | 181 | 167 | 439 | TG_R 10, TG_L 11, pocket 0 | 33 / 31 | 0.6 |
| PR19 | 19 | crown hood, lip relieved at the corner wraps + top side guys | 179 | 174 | 163 | 451 | TG_R 20, TG_L 20, pocket 0 | 33 / 33 | 4.9 |
| PR23 | 23 | crown hood, lip relieved at the corner wraps + top side guys | 170 | 166 | 159 | 436 | TG_R 22, TG_L 24, pocket 0 | 33 / 33 | 4.9 |
| PGc15 | 15 | crown hood + guys cinched 60 N after loading | 181 | 172 | 162 | 444 | TG_R 23, TG_L 24, pocket 0 | 31 / 28 | 0.0 |
| PGc19 | 19 | crown hood + guys cinched 60 N after loading | 173 | 166 | 159 | 439 | TG_R 26, TG_L 28, pocket 0 | 33 / 33 | 4.9 |

Top anchor N is the meat case; `pocket` is the hood capture summed over its width. R-28 uses the DESIGN 4.7 head model with the simulated wall (drafted face moved by the sim + 3 mm) instead of the 15 mm bulge, plus the hood on the bar. The published check (bare bar, 15 mm bulge) gives 34 deg / 6.8 mm; with the hood on the bar 33 deg / 4.9 mm. The bar governs, not the wall.

### 2.2 Why the hood + guys

- **The hood beats the crown tie as the bar anchor.** Alone at 19 in it gives 186 / 182 mm against 192 / 186 for the two-point tie (A): it holds B-01 across the bar width instead of at x +/-70. That is the research's best-in-class pattern: the frame top captured by the bag (KUIU ICON 6 stay pockets, Initial Ascent slots, the Mystery Ranch collar), here as one hood on the bar.
- **A bar anchor alone is not enough at any torso.** At 23 in the hood alone is 180 mm (the bag between IM3 at z 520 and the bar at z 804 bulges aft), at 15 in it carries nothing (0 N) and gives 201 mm. What pulls the CG in is the pair of guys holding the aft upper corners forward (study finding 3).
- **Hood + guys vs study G (tie + guys):** 179 vs 179 mm at 19 in, 170 vs 167 at 23 in, 189 vs 189 at 15 in: the same within the +/-5 mm scatter. The hood wins on use, not on CG: the guys are sewn to its ears, so one lift releases the whole top (hood and both guys) and one drop re-seats it. Nothing at the top is threaded, clipped or tensioned with the bag on, which is the field's failure point (K4 dealer's ~18 cases, research 3.3). G needs two more clips at the bar and the guy anchors crowd the lifter lugs at x +/-105.
- **Load lifters as the anchor (L19)** reach 180 / 175 mm, about the same, but only by routing the lifter to the bag in bag-on and back to the frame in bag-off. That is the switching in US 10,952,523, and with the bag off the lifters would need a second anchor. Rejected. On our rigid crown a lifter that stays on the crown does not change the bag-to-frame peel at all (it loads the frame, not the bag).
- **Cinching the guys** (60 N after loading, PGc) buys 8 mm at 15 in (181 / 172 mm) but R-28 then **fails: first contact 28 deg** (the top is pulled toward the head); at 19 in it gives 173 / 166 mm, R-28 33 deg. So the guys are set once on the packed bag and never cranked (the instruction is 'snug, do not crank'). This is the study's B finding again: cinched top straps over-pull toward the head.

### 2.5 Hood and the crown corner wraps (2026-11-06)

The frame re-check (`frame_cg_recheck.md` 5.1) found that the carbon corner wraps cover the top bar from the leg face (x +/-107) to about x +/-77, at OD about 19.5, and cannot be shortened (an 11 mm overlap fails the corner bond). The 2026-11-05 hood asked for bare bar over x +/-96: its lip and HDPE stiffener would have borne on the wrap step and the ply drop, putting the hood capture and the guy loads into the bond end. Fix on the hood, not the frame:

- **Lip relief:** the lip, J-curl, hem, B-19s stiffener and B-19L lining stop at x +/-66 (132 mm on bare OD 18 bar). The outer 29 mm each side of the 190 mm shell is back ply and crown only, ending at fold 2 with an R4 root. Shell width, ears, guys, tongues and the ladder do not change.
- **Why 66 and not 77:** the hood floats 9 mm a side between the crown legs, so the lip edge can reach x 75: 2 mm short of the wrap step. Over the wraps the crown sits on the 3 mm lining in the bare zone, 2.25 mm above the wrap (radial step 0.75 mm). Nothing touches the wraps in use.
- **Cloth sim re-run** with the hood capture narrowed to x +/-66 (conservative: the shell still holds B-01 wider than that):

| torso | fill CG full lip (PG) | fill CG relieved (PR) | meat CG PG | meat CG PR | hood 1 g N PG / PR (meat) | guys 1 g N PR (meat) | R-28 deg PR (fill / meat) | gap at 30 deg PR mm |
|---:|---:|---:|---:|---:|---|---|---|---:|
| 15 | 189 | **189** | 181 | **181** | 0 / 0 | 10 / 11 | 33 / 31 | 0.6 |
| 19 | 177 | **179** | 173 | **174** | 3 / 0 | 20 / 20 | 33 / 33 | 4.9 |
| 23 | 168 | **170** | 165 | **166** | 3 / 0 | 22 / 24 | 33 / 33 | 4.9 |

The CG holds within the +/-5 mm fill scatter (accepted 189 / 177 / 168 mm), and R-28 still passes at every torso. With the narrower capture the hood itself carries almost nothing and the two guys take the top (a few N more each); the hood's job is to give the guys their anchor and centre the top. The guy factored load and the lip capacity (132 mm of Hypalon on the bar) are in section 5. The PR19 meat case stops at a 0.8 N residual (not flagged converged); the other meat cases converge.

### 2.3 Why the hood is lift-and-drop, not snap-on

The bag goes on by tipping it onto the z 60 pins, 643 mm below the bar (in use it no longer pivots: the float replaced the swing, 2026-11-06). Seen from the bag, the bar arrives on a 643 mm arc that is level at the bar: it comes in from the wearer side. Peel is the same motion. So any bag part that stops the peel is also in the way when the bag is tipped shut. A pocket cannot be made to catch the bar passively. The hood is lifted 25 mm by its tab (B-01 above IM3 is slack in compression, and the hood rides on its ladder), the bag top is pressed to the crown, and the hood is let go. It drops over the bar. Under load the J-lip seats it harder: the peel pushes it down onto the bar. Lift and drop are about 3 s each, with no strap to stretch over meat.

### 2.4 The 15 in setting

At 15 in the top bar is at z 601, 500 mm below the bag top. Best head-safe result: 189 mm fill / 181 mm meat (meat at 150: 167). The structural re-check already running uses a 205 mm C1 envelope and 175 mm for C5/C7, so the frame is covered. Higher anchors need a frame part above the crown (accessory posts: IP opinion on US 10,952,523, owner choice 1).

## 3. IM3 hook

With B-17 the IM3 bag hook carries 472 N at 1 g with no top anchor (T0) and 451 N with the hood and guys: the top anchor relieves it only 21 N. The hook is designed for the hood-off case (a user who forgets the hood): C5 factored **1415 N**.

| option | rating N | SF at C5 | mass change | verdict |
|---|---:|---:|---:|---|
| keep the 1500 N hook (assumption) | 1500 | 1.06 | 0 | fails a 1.5 qualification margin |
| hood relieves IM3 | 1500 | 1.11 | 0 | still thin, and lost if the hood is off |
| two hooks per side on one eye | 2 x 1500 | not credited | +18 g | uneven share on one 38 mm eye; rejected |
| **rated 38 mm hook, all four bag hooks** | **>= 2200** | **1.55** | **+20 g** | **chosen**; same handling and times; one spare part |

Proof test PT-1: five hooks hold **2120 N** for 60 s (1.5 x C5), gate closes after; then one hook per lot of 25 to 1415 N. The old 830 N test is retired for the bag hooks. The meat-strap hooks (6) keep the 1500 N assumption and their own 830 N test (meat_haul_modes.md).

## 4. Sway, barndoor and the side compression

- **Barndoor (bag yawing on the frame):** held at three heights on both sides: the hinge pins (z 60), the IM2/IM3 hooks (z 330/520), and at the top the hood between the crown legs (190 mm hood, 208 mm between the leg faces: 9 mm a side, then Hypalon on carbon). The guys are symmetric, so they centre the top.
- **Sway (side lean of the top):** the guys are the top side-compression straps. They run from the hood ears outside the side gores to the aft corners, so cinching the top sideways and holding it forward is one strap per side. W1-W3 stay the frame-anchored wraps for the lower and middle bag and for float mode. The roll-top clips stay on the gores.
- **Small loads:** the guys are fixed at the full-bag length; for a part-full bag pull the tails one more step (they are ladder locks) and W1-W3 take up the rest.

## 5. Sewn side

Stitch standards. Load joints: box-X, ISO 301 lockstitch, **7 SPI** (3.6 mm), `bonded_nylon_tex135` (98 N), needle Nm 140 / 22, 3-stitch backtack. Patch perimeters: double row 3 and 9 mm in, 301, **8 SPI** (3.2 mm), `bonded_nylon_tex90` (64 N), needle Nm 110 / 18. Thread line strength = 1.5 x break / stitch length (CONTRACTS 7): 40.5 N/mm box, 30.2 N/mm per perimeter row. Patches are capped by 0.8 x the weaker strip strength.

| id | part | qty | material | cut | fold / make | stitch | backing | placement |
|---|---|---:|---|---|---|---|---|---|
| HE | hinge eye (sewn eye on the tethered z 60 pull-pin) | 2 | `poly_webbing_38mm` | 38 mm x 150 mm | end folded back 50 mm into a 25 mm eye for the 5 mm pin; first 30 mm tri-folded lengthwise to an 18 mm neck (fairlead throat) and held with a 304 bartack across the neck; tail runs down into the B-01|B-05 seam | box-X 38 x 38 through eye plies + B-18 + B-01, 301, 7 SPI, `bonded_nylon_tex135` | B-18 doubler (inside B-01), lower edge caught in the B-01|B-05 seam | x +/-115 at the hinge-eye notch, eye top at z 60 |
| B-18 | hinge-eye doubler | 2 | `hypalon_coated_nylon` | 90 x 45, laser-cut, R6 corners | flat | double-row perimeter 3 / 9 mm from the edge, 301; lower edge in the B-01|B-05 seam, 8 SPI, `bonded_nylon_tex90` | - | INSIDE B-01, centred on the hinge eye |
| T2 | IM2 bag-hook tongue | 2 | `poly_webbing_38mm` | 38 mm x 160 mm | end folded 45 mm round the hook bed into a 20 mm loop, box-X; other end box-X to B-01 | box-X 38 x 38 both ends, 301, 7 SPI, `bonded_nylon_tex135` | B-23 backing 60 x 60 Hypalon inside B-01 (new) | B-01 outside, box at x +/-115, z 260 (existing 'im2 bag-hook strap box-X' drill marks); loop at the IM2 eye z 330 |
| B-23 | IM2 tongue backing (new) | 2 | `hypalon_coated_nylon` | 60 x 60, laser-cut, R6 | flat | single-row perimeter 3 mm, 301 (the tongue box-X goes through it), 8 SPI, `bonded_nylon_tex90` | - | INSIDE B-01, centred on the IM2 tongue box at x +/-115, z 260 |
| T3 | IM3 bag-hook tongue | 2 | `poly_webbing_38mm` | 38 mm x 160 mm | as T2 | box-X 38 x 38 both ends, 301, 7 SPI, `bonded_nylon_tex135` | B-17 tab (outside B-01) | box at x +/-115, z 450 on B-17; loop at the IM3 eye z 520 |
| B-17 | IM3 bag-hook tab | 2 | `hypalon_coated_nylon` | 90 x 110, laser-cut, R6 | flat | double-row perimeter 3 / 9 mm, 301; 80 mm stitch line across the load, 8 SPI, `bonded_nylon_tex90` | - | OUTSIDE B-01 under the IM3 swell, centred x +/-115, z 450 |
| B-19 | crown hood shell (new) | 1 | `hypalon_coated_nylon` | 190 x 130 blank + 2 ears 30 x 40, laser-cut | fold 1 (back/crown) and fold 2 (crown/lip) square on a 19 mm dowel; lip relieved over the outer 29 mm each side (lip on bare bar over x +/-66, clear of the crown corner wraps); lip hem 14 mm turned in over the HDPE stiffener B-19s; lining B-19L glued inside the crown | lip hem: single row 301 at 3 mm; tongues box-X 25 x 25; ears: guy box-X 25 x 25, 7 SPI, `bonded_nylon_tex135` | - | rides on the crown top bar between the crown legs (shell x +/-95, lip bears on bare bar x +/-66) |
| HT | hood tongues (woven into the ladder, POM toggle end) | 2 | `poly_webbing_25mm` | 25 mm x 120 mm | one end box-X to the hood back ply at x +/-60; other end folded over a POM toggle 30 x 8 x 5 and box-X'd | box-X 25 x 25 both ends, 301, 7 SPI, `bonded_nylon_tex135` | - | woven in at the rung for the torso setting (rung k = crown setting k) |
| B-20 | hood ladder strip (new) | 2 | `hypalon_coated_nylon` | 40 x 250, 17 slots 27 x 5 at 12.7 mm pitch, laser-cut | flat | double-row both long edges 2 / 5 mm (clear of the slots) + bartack both ends, 301, 8 SPI, `bonded_nylon_tex90` | - | OUTSIDE B-01b/B-01u, centred x +/-60, z 545-795 (sewn after the B-01 tiers are joined; follows the setback) |
| TG | top side guy (fixed length, set once) | 2 | `poly_webbing_25mm` | 25 mm x 500 mm | hood end box-X on the ear; bag end through a 25 mm ladder lock + tri-glide keeper on B-22, tail 100 mm in an elastic keeper | box-X 25 x 25 (hood end), 301, 7 SPI, `bonded_nylon_tex135` | B-22 corner tab | hood ear x +/-95 -> B-02d at x +/-149, z 752 (outer face, upper corner); free length about 314 mm |
| B-22 | guy corner tab (new) | 2 | `hypalon_coated_nylon` | 50 x 60, laser-cut, R6 | flat | double-row perimeter; ladder-lock tab (25 mm x 70 mm webbing) box-X 21 x 25 through it (LLT + B-22 + B-02d, one pass), 8 SPI, `bonded_nylon_tex90` | - | OUTSIDE B-02d at x +/-149, z 752 |
| B-24 | float-mode stand-off link (new) | 2 | `poly_webbing_38mm` | 38 mm x 435 mm | hook end folded 45 mm round the bed of a rated 38 mm hook, box-X; three loops (25 mm opening, 50 mm of webbing each) with their bed at 120 / 170 / 220 mm from the hook bed, each closed with a 34 x 20 box-X; 20 mm tail, heat-sealed | box-X 34 x 30 (hook) + 3 x box-X 34 x 20 (loops), 301, 7 SPI, `bonded_nylon_tex135` | - | hook on the IM3 captive eye (z 520, x +/-115); the bag's T3 hook clips into a loop (float mode only; stowed in the lid or hipbelt pocket) |

Strength (per side, factored HA-LS-1 x 3.0 or the beam model, whichever is larger):

| id | factored N | basis | capacities N | governs | SF | qualification N |
|---|---:|---|---|---|---:|---:|
| HE | 1019 | max(sim hinge eye x 3.0, beam model) | box-X 5256; webbing on pin 10008; B-18 seam (80 mm, B-05 strip governs) 2355 | B-18 seam (80 mm, B-05 strip governs) | **2.31** | 1530 |
| B-18 | 1019 | as HE | perimeter seam (80 mm loaded) 3277 | perimeter seam (80 mm loaded) | **3.22** | 1530 |
| T2 | 403 | max(sim IM2 x 3.0, beam model) | box-X 5256; webbing on hook bed 10008; B-23 tear-out (2 x 60 mm) 4915; hook (rated) 2200 | hook (rated) | **5.45** | 610 |
| B-23 | 403 | as T2 | tear-out (2 x 60 mm) 3628 | tear-out (2 x 60 mm) | **9.00** | 610 |
| T3 | 1415 | max(sim IM3 x 3.0 incl. hood-off T0 472 N, beam model) | box-X 5256; webbing on hook bed 10008; hook (rated) 2200; B-17 seam (80 mm loaded) 3277 | hook (rated) | **1.55** | 2120 |
| B-17 | 1415 | as T3 | perimeter seam (80 mm loaded) 3277 | perimeter seam (80 mm loaded) | **2.32** | 2120 |
| B-19 | 381 | sim hood capture + 2 guys, x 3.0 | lip on bare bar (Hypalon strip x 132) 5407; 2 tongue box-X 25 6916 | lip on bare bar (Hypalon strip x 132) | **14.18** | 570 |
| HT | 79 | sim hood capture per side x 3.0 | box-X 25 3458; POM toggle (ASSUMPTION) 670; webbing 6672 | POM toggle (ASSUMPTION) | **8.51** | 120 |
| B-20 | 79 | as HT | rung bar (7.7 mm, 30 deg sag) 315 | rung bar (7.7 mm, 30 deg sag) | **4.00** | 120 |
| TG | 112 | sim guy x 3.0 | box-X 25 3458; ladder lock slip 300; webbing 6672 | ladder lock slip | **2.68** | 170 |
| B-22 | 112 | as TG | perimeter seam (50 mm loaded) 1024; LLT box-X 21 x 25 3186 | perimeter seam (50 mm loaded) | **9.15** | 170 |
| B-24 | 941 | 32 kg bag on two links at 30 deg x 3.0 (misuse envelope; design case 12 kg = 353 N) | box-X (hook end) 4430; loop box-X 34 x 20 3786; webbing on hook bed 10008; hook (rated) 2200 | hook (rated) | **2.34** | 1410 |

Proof tests (owner bench, before the first sewn bag):

| test | what | rig | load N | covers | accept | then |
|---|---|---|---:|---|---|---|
| PT-1 | 38 mm bag hook (all four bag hooks, one part) | hook on a 5 mm pin, 38 mm webbing loop on the bed | 2120 | C5 IM3 factored 1415 N (hood-off, T0) x 1.5 | 5 of 5 hold, gate closes after | every lot of 25: one hook to 1415 N |
| PT-2 | T3 tongue on B-17 on a B-01 swatch | swatch clamped 120 mm wide, pull on the tongue loop | 2120 | IM3 sewn path (box-X, tab seam, laminate) | 5 of 5 hold, no stitch break, no laminate tear | first article only |
| PT-3 | HE eye on B-18 + B-01 + B-05 seam swatch | 5 mm pin through the eye | 1530 | hinge factored 1019 N | 5 of 5 hold | first article only |
| PT-4 | crown hood on an 18 mm tube | pull B-01 swatch aft through the ladder, guys pulled aft-outward | 570 | hood capture + both guys x 3.0 | hood stays seated, no toggle pull-through | repeat at -10 C (HDPE lip) |
| PT-5 | guy ladder lock with the tri-glide keeper | 25 mm webbing, 10 cycles 0-load | 170 | guy x 3.0 | slip < 5 mm over 10 cycles | - |
| PT-6 | B-24 stand-off link, hook end and the 220 mm loop | link hook on a 5 mm pin, 38 mm webbing loop through the 220 mm loop, pull in line | 1410 | link misuse envelope 941 N x 1.5 | 5 of 5 hold, no box-X break, gate closes after | first article; then 1 link per lot of 25 to 941 N |

## 6. Quiet

Checklist = the noise sources owners name (research 3.4) plus the four inferred rules there.

| source | how this joint answers it |
|---|---|
| dry webbing and buckles | No side-release buckle anywhere in the joint. Only plastic: two guy ladder locks (set once, on the outer face, touching fabric only) and two POM toggles buried in webbing. Captive eyes and the hood lip are rubbed with paraffin at assembly (owners' wax fix). |
| webbing loops at the frame | Captive eyes sit on pins in UHMWPE sleeves in an 18 mm throat; the bag hooks are loaded whenever the bag is on, and hang on elastic keepers when it is off. Hooks keep their TPU sleeves. The B-24 float links ride in a pocket except in float mode, where the hanging bag keeps their hooks loaded. |
| frame rails rubbing inside the bag | No frame part is inside the bag. B-01 keeps 2 mm of air over every cleat (swells). The hood is outside the bag, on the bar, and does not slide in use. |
| dirt in frame joints | The hood is open at the bottom and the ladder slots drain. Pins and sleeves are field spares. |
| cold fabric | Hypalon and HDPE stay flexible; PT-4 is repeated at -10 C. |
| hard part taps a hard part when empty | Pull-pins have Dyneema cord loops, not metal rings. The hood crown rests on the bar at every setting (one rung per setting) and is lined with 3 mm XLPE where it touches. Toggles are inside webbing. |
| sliding cloth on the stays | Nothing bears on the stays: the spreader takes the meat, the swells clear the cleats, the hood seats on the bar and moves only when the torso setting changes. |
| pin rattle | Sleeve pressed into the cheek, silicone washer under the pull loop. Replace the sleeve when the eye clicks or has felt play (about 0.3 mm); spare sleeves are in the repair kit. |
| hook-and-loop in the opening path | None in the joint (no hook-and-loop anywhere in hunt mode). |

## 7. Procedures

### Bag on (bag off, frame empty) - about 59 s

1. Lay the frame on its back pad, crown away from you. Stand the bag behind it with the frame panel (B-01) facing the frame. (10 s)
2. First time only: weave the two hood tongues through the B-20 ladder at your crown setting (rung number = the setting number on the crown rack; the rung list is printed on B-20) and push each POM toggle through the next slot.
3. Tip the bag onto the frame so each hinge eye sits between the cheeks of the z 60 fairlead. Push the pull-pin through cheek, sleeve, eye, cheek. Seat the silicone washer. Both sides. (12 s)
4. Lift the bag floor. Lay the two under-straps in the floor channels (US1 rear, US2 front) and cam them until the floor is snug. (12 s)
5. Clip the four bag hooks onto the IM2 and IM3 eyes, gate toward the bag. Work bottom up: IM2 left and right, then IM3. (16 s)
6. Lift the hood by its tab, press the top of the bag against the crown, let go. The hood drops over the top bar. Check: the hood sits on the bar across its width and its lip is in front of the bar. (3 s)
7. Pack the bag. Pull each top-guy tail until the guy is snug (no slack, do not crank it), slide the tri-glide against the ladder lock and tuck the tail in its keeper. (6 s)
8. Lifters and hipbelt as usual.

### Bag off (keep it under 120 s) - about 52 s

1. Set the pack down on its back pad. (3 s)
2. Lift the hood tab and ease the top of the bag about 10 cm aft so the hood clears the bar. The guys stay on the hood and come with the bag. (3 s)
3. Unclip the four bag hooks, IM3 first, then IM2. Hang each on its elastic keeper. (16 s)
4. Pop the two under-strap cams. Slide the floor channels off the straps. The straps stay on their pins: they are the cradle. (12 s)
5. Pull the two hinge pins. They stay tethered to the bag eyes. (8 s)
6. Lift the bag clear. (10 s)

### Float mode (meat on the frame, bag hung upright behind it on the B-24 links) - about 128 s

1. Take the bag off (procedure above). Lay the frame on its back pad, crown toward the meat. (52 s)
2. Set the quarter (in a game bag) in the two under-straps, bone toward the spreader. Cam them until the belly is about 70 mm. (12 s)
3. Hook IM1-IM3 meat straps eye to eye over the meat and cam them. A hock can sit on IM1. (24 s)
4. Hook one B-24 stand-off link on each IM3 eye, gate toward the bag, beside the meat-strap hook. Let the loops hang aft along the sides of the meat. (8 s)
5. Stand the bag upright behind the meat, frame panel (B-01) toward it. Clip each T3 bag hook into the link loop that just touches the bag (120, 170 or 220 mm; use the smallest that fits). The T2 hooks stay on their keepers; the hood lies on the bag top and is not put on the bar. (14 s)
6. Close W1-W3 round the bag and the meat (ladder locks). (18 s)

### Bag-off meat haul (frame and cradle only) - about 108 s

1. Take the bag off (procedure above). (52 s)
2. Set the quarter in the two under-straps, bone toward the spreader. Cam them until the belly is about 70 mm. (12 s)
3. Hook IM1-IM3 eye to eye over the meat and cam them. A hock can sit on IM1. (24 s)
4. Fold the empty bag flat and strap it over the crown with W3. (20 s)

### Field repair kit (hipbelt pocket)

1. Lost hinge pin: fit the spare 5 mm pin. No spare: 6 turns of the 3 mm cord through the eye and the cleat hole, double fisherman's knot. (120 s)
2. Broken bag hook: clip the spare hook on the tongue loop. No spare: 4 turns of cord through the tongue loop and the eye, knot. (90 s)
3. Cracked fairlead cleat: girth-hitch the 0.6 m of 38 mm webbing round the stay above the cleat and clip the hook (or the eye) to it. (120 s)
4. Lost hood toggle: fit the spare toggle, or tie the tongue end through the next slot with cord. (60 s)
5. Torn hood: tie the hood ears to the top bar at x +/-70 with two turns of cord each. The guys still work (study candidate G). (120 s)
6. Clicking pin (oval sleeve): pin out, push the old UHMWPE sleeve out with the pin, press in the spare. (180 s)
7. Guy slipping: half hitch the tail round the ladder lock. (15 s)

Repair kit: spare 5 mm 7075 pin with cord pull loop, 2 UHMWPE sleeves, spare 38 mm bag hook (2.2 kN), 3 mm Dyneema-core cord, 1.5 m, 38 mm webbing, 0.6 m, spare POM toggle, about 44 g (not in the base weight).

## 8. Patent guardrails (engineering read, not a legal opinion)

| patent | how the joint stays clear | status |
|---|---|---|
| US 12,495,885 (Eberlestock, load sling) | Under-straps US1/US2 run frame pin to frame pin (eye on the left pin, cam on the right pin) through channels sewn on the bag floor. No separate fabric shelf panel, and no strap ends on the bag. The hood is above the bag top and is not a sling. Float mode (2026-11-06): the meat sits on those frame-to-frame straps; the two B-24 links run from the IM3 eyes (z 520, above the meat floor) to the bag's T3 hooks, and there is no fabric panel between frame and bag for any strap to run under. | compliant as drawn; FTO read still required before release |
| US 10,952,523 (Mystery Ranch, pop-up frame) | Load lifters stay on the crown corner wraps at every setting and in every mode. The 'lifters as anchor' option (L19) would route the lifter to the bag in bag-on and to the frame in bag-off: that is the switching the claim describes, so it is rejected whatever its CG. The hood sits on the crown bar but is not a lifter connector. | compliant |
| US 8,381,956 (Mystery Ranch, membrane + stay gap, est. to 2027) | No bag tab or strap is tucked between the spreader and the z 330 cross member. The IM2 tongue reaches the IM2 eye at the stay face through the spreader's 30 mm edge notch, aft of the spreader; nothing goes behind the spreader. | compliant |
| US 8,579,171 / 8,348,114 (Mystery Ranch, expired per Google) | Their description includes a collar with an inverted pocket over the frame top. The crown hood is that family of idea (public domain if expired). | confirm expiry in the FTO read |

Original IP: The hood is a single J-profile Hypalon cap between the crown legs, on a woven one-rung-per-setting ladder, with the guys sewn to its ears. It is not KUIU's Hypalon stay pockets, Initial Ascent's slots or a Mystery Ranch frame cap, and copies no brand's hardware layout, shape, colour or name.

## 9. Frame interface (for the structural-fea-engineer)

- No new printed feature and no edit to `print/frame`. The hood uses the existing carbon crown top bar.
- Crown top bar (2026-11-06, replaces 'bare x +/-96'): the corner wraps stay as built (x +/-77 to +/-107, OD ~19.5). The hood's lip, stiffener and lining bear on bare OD 18 +/- 0.3 bar over x +/-66 only (2 mm clear of the wrap step with the hood floated 9 mm to one leg); keep x +/-75 free of any bonded lug, label or tape.
- New load on the crown top bar (factored, HA-LS-1 x 3.0): hood capture 158 N total, spread over x +/-66 on the bar's wearer-side face, pointing aft (1.19 N/mm, was 0.83 over x +/-95); each guy 112 N, from the hood ear at x +/-95 pointing aft and outboard toward the face corner (x +/-149, z 752), now reaching the bar through the hood shell and the lip (x +/-66), not at the ear. Nothing bears on the wraps. Add both to the C1/C5 re-check with the bag CG below.
- Bag CG envelope for the frame re-check, chosen system (1 g sim, +/-5 mm on fill): see the 'Top anchor' table; worst is the 15 in setting.
- Float mode (2026-11-06, replaces the hinge swing): each IM3 captive eye carries its meat-strap leg (225 N aft, factored hand cinch) plus one B-24 link (353 N factored, 30 deg below horizontal, aft and down; 12 kg bag): resultant 559 N per side. Misuse envelope (32 kg in the bag): link 941 N, eye 1142 N per side, below the 1415 N bag-hook case the IM3 eye already carries in bag-on. The hinge pins carry nothing in float mode. Full list: analysis/meat_carry_alternatives.md section 8.

## 10. Pattern-maker hand-off

| piece | change |
|---|---|
| B-01 (lower) | Mark B-23 backing placements INSIDE at x +/-115, z 260, centred on the existing 'im2 bag-hook strap box-X' drill marks. No outline change. |
| B-01b / B-01u | Mark the two B-20 ladder strips OUTSIDE, centred x +/-60, z 545-795, both long-edge stitch lines (3 and 9 mm in) and the end bartacks. They cross the B-01|B-01b and B-01b|B-01u seams: sew after the three tiers are joined, before B-01 joins B-03. No outline change. |
| B-02d | Mark the B-22 corner tabs OUTSIDE at x +/-149, z 752 and the ladder-lock tab box-X. Sew before B-02d joins the collar. |
| B-17, B-18 | Unchanged (2026-11-05). B-17 now carries tongue T3 for the rated hook. |
| B-19 / B-19s / B-19L (rev 2026-11-06) | Hood lip relieved: the lip, J-curl and hem exist only over the centre 132 mm (x +/-66); the outer 29 mm each side ends at fold 2 with an R4 root. Back ply, crown, ears and the 190 mm shell width are unchanged. B-19s HDPE 180 -> 124 mm, B-19L XLPE 180 -> 128 mm. Blank outline, fold 2 and hem lines redrawn in cut/attachment/attachment_parts.pdf / .dxf. |
| new pieces | B-19 hood shell (Hypalon, laser-cut, fold lines etched), B-19s lip stiffener (HDPE 1.5), B-19L lining (XLPE 3), B-20 x2 ladder strips (Hypalon, 17 slots), B-22 x2 corner tabs, B-23 x2 IM2 backings. No seam allowance (laser-cut, edge-stitched). True-scale in cut/attachment/attachment_parts.pdf / .dxf. |
| webbing cut list | add: HT hood tongues 2 x 25 mm x 120; TG guys 2 x 25 mm x 500; ladder-lock tabs 2 x 25 mm x 70; hood grab tab 1 x 25 mm x 90; B-24 float links 2 x 38 mm x 435 (2026-11-06). Unchanged: HE 2 x 38 x 150, T2/T3 4 x 38 x 160. |
| hardware list | bag hooks 4 x 38 mm rated >= 2200 N (replaces the 1500 N assumption on the bag hooks only; the meat-strap hooks are unchanged); 2 x POM toggle; 2 x 25 mm ladder lock; 2 x tri-glide; Dyneema cord pull loops replace the metal rings on the two hinge pins; 2 more rated 38 mm hooks on the B-24 float links (2026-11-06). |

## 11. Mass and cost of this phase

| part | g |
|---|---:|
| crown hood B-19 (Hypalon blank + ears + hem) | 24.3 |
| hood lip stiffener B-19s (HDPE 1.5) | 3.9 |
| hood lining B-19L (XLPE 3) | 0.6 |
| hood ladder strips B-20 x2 | 20.0 |
| hood tongues x2 + POM toggles | 7.7 |
| hood grab tab (25 mm x 90) | 1.6 |
| top side guys x2 (25 mm webbing) | 18.0 |
| guy ladder locks + tri-glides + ladder-lock tabs | 15.7 |
| guy corner tabs B-22 x2 | 5.9 |
| guy tail elastic keepers x2 | 1.2 |
| IM2 tongue backings B-23 x2 | 7.1 |
| bag hooks 1500 N -> 2200 N rated (4 x +5 g) | 20.0 |
| thread (box-X + perimeters) | 2.0 |
| **delta** | **128.1** |


Float-mode stand-off links B-24 (owner 2026-11-06), booked as their own weight group, not in the delta above: 38 mm webbing, 2 x 435 mm 24.4 g; rated 38 mm hooks (2), same part as the bag hooks 28.0 g; thread (box-X + loop box-X) 2.0 g; **+54.4 g**.

Pack (this phase) 3316 -> **3444 g (7.59 lb)**, 468 g over the published 2976 g. Basis: hypalon_coated_nylon 1000 gsm, hdpe_sheet, xlpe_foam, poly_webbing_25mm, ladder_lock_25mm, pom_toggle, triglide_25mm records; hook mass ASSUMPTION; elastic keeper 0.6 g history (corrie_f re-books it on elastic_25mm). Marginal cost about $16 (records' prices; hook $6.00 and toggle $0.50 ASSUMPTION).

## 12. Owner choices (recommendation first)

1. **15-16.5 in settings: accept the 15 in result (recommended)**, fill CG 189 mm, inside the 205 mm envelope of the frame re-check that is running; cinching the guys there gets closer to 180 but fails R-28 (2.2). The alternative is a hood on the accessory extension posts for short torsos: it needs an IP opinion on US 10,952,523, a C6p-type frame case and an R-28 check with posts.
2. **Accept +128 g for the joint (recommended)**: pack 3444 g (7.59 lb), 468 g over the published 2976 g. Without the top anchor the frame has to carry the 205 mm CG at every torso.
3. **One rated hook for all four bag hooks (recommended, +20 g)** or rated hooks at IM3 only (+10 g, two hook types in the kit).
4. **FTO read on US 12,495,885 and confirmation that US 8,579,171 / 8,348,114 are expired** before release (recommended; open since the research).
5. Lighter options if the weight is not accepted: ladder strips in 500D Cordura with bound slots (about -11 g, less durable at the slots), rated hooks at IM3 only (-10 g), no tri-glide keepers on the guys (-6 g; research says keep them).

## 13. Assumptions

- Box-X load share ETA_BOX 0.5 of the stitch path; webbing on a 5 mm pin or hook bed keeps 50 % of its break; seam efficiency 0.8 and grab/strip 31.25 mm from huntkit/clothsim/fabrics.yaml. Proof tests PT-1..PT-5 replace these.
- Qualification load = 1.5 x the HA-LS-1 factored load (n = 5 sample scatter allowance).
- Bag hook: 38 mm forged 7075 sliding-gate class, rated >= 2200 N, 14 g, $6.00: a purchase requirement, proven by PT-1. No hook record exists yet (materials-engineer to add one from the bought part).
- POM toggle 30 x 8 x 5 mm, 3 g, bending pull-through 670 N (pom_acetal ~65 MPa, Z 33 mm3).
- Tri-glide 3 g, elastic keeper 0.6 g, hood rung bar fails at 30 deg sag.
- Cloth sim: crown hood = tension-only legs from the B-01 rows within 25 mm of the bar to the bar's bag face, free to slide in z and x (hood on a ladder, not sewn at one height); 1 mm Hypalon ply ~ 38 mm webbing EA per 40 mm strip; free hood depth 16 mm (the drafted gap at 19-23 in). Ladder tongues at x +/-60 hold B-01. Released (PR) runs hold the row out to x +/-66 (the relieved lip on bare bar); the superseded PG runs held it to x +/-92. Hood-alone loads (P runs, x +/-92) stay the bound for the hood capture.
- Hood float 9 mm a side between the crown legs; wrap step from x +/-77 (frame.yaml: 30 mm wrap, 8 mm ply drop, OD ~19.5); a 2 mm margin from the lip edge to the step.
- Guys fixed length: elastic 25 mm webbing snug (30 N) at the drafted shape, i.e. set once on the packed bag.
- R-28 with the sim wall adds 3 mm (fabric + coarse mesh) and the hood (+1 mm in front of the bar, +4 mm over it).
- Procedure seconds: 4 s a hook or pin, 3 s a cam pop or a hood lift, 10 s to place or clear the bag (gloved, not timed).

## Screenshots (this phase)

Phone previews in `outputs/screens/20261105_attach_1..5.png`; milestone copies (cited) in `docs/screens/`:

- `docs/screens/20261105_attach_1.png`
- `docs/screens/20261105_attach_2.png`
- `docs/screens/20261105_attach_3.png`
- `docs/screens/20261105_attach_4.png`
- `docs/screens/20261105_attach_5.png`
- `docs/screens/20261106_backpanel_4.png`

## Frame side: branch fairleads (record of 2026-11-01, still current)

Superseded in this record by the system sections above: the bag-hook rating (section 3), the detach time (Decision) and the open questions. The fairlead geometry, pins, sleeves and their FEA are unchanged.

The Spine bag hangs on the printed branching frame. The fairlead is a small cleat
grown on the bag face of each stay. A 5 mm 7075 pin through a UHMWPE sleeve holds a
short webbing eye. The bag clips to that eye. The branch window is not filled, and
nothing sits on the wearer side of the stay.

Code: `huntkit/gendesign/bag_attach.py`. Load standard: HA-LS-1 rev B.

### Recommendation

**Branch fairlead.** Eight identical printed cleats, at the hinge and at IM1–IM3, both sides.

- Added mass **117 g**. Pack goes from 2865 g to **2982 g (6.58 lb)**.
- Printed fairlead, fine mesh 1.00 mm. Minimum strength SF **2.97**. Minimum fatigue SF **1.67**.
- Pin double-shear SF **14.4** (7075-T6 S-basis). Sleeve bearing SF **2.32**.
- Bag off in about **34 s** (four hooks and two hinge pins; 2026-11-01 estimate, before the under-straps and the hood).
- Marginal hardware and filament about **$48**. Extra print time about **1.75 h**.

Bag-off is a required mode (owner, 2026-11-01). The same fairleads take the
meat straps eye-to-eye once the bag is off. The haul modes (bag on, float, bag off; the float replaced the hinge swing 2026-11-06),
and the safety factors are in `analysis/meat_haul_modes.md`. The eight B-01 swells are accepted.

### Why this one

- A sleeve over the limbs is light and strong and hides the branch. The frame is the product.
- Webbing passed through the branch window has to come back on the wearer side of the stay.
  That strand lands in the pad gap. The window is kept open so the split stays visible.
- A magnetic buckle is rated 300 N. The hinge sees 726 N factored.
- A 25 mm side-release is rated 450 N. A 38 mm side-release is rated 900 N, SF 1.24 on the hinge, and that rating is an estimate. Neither is the closer.
- A cam will hold a pull and then walk under a day of gait. The torso-adjust study already rejected it as a lock.
- A rail covers the stay face, adds a slider that can tap, and weighs more than the fairleads.
- A printed clip's hook tongue is still at fatigue SF 0.28 with an
  18 mm root. The tongue is pulled across the layers, and a thicker
  root does not fix it. A cracked tongue means reprinting the frame. The fairlead's pin and eye come off.

The closer on IM2 and IM3 was the aluminium sliding-gate hook assumed for the meat
harness (1500 N, 9 g), SF **2.71** on the beam-model load. The cloth sim with the B-17 tab raised that load; the bag hooks are now a rated part (section 3). The hinge does not use a hook:
the bag's sewn eye is on the pin, the bag's bottom anchor in bag-on mode (2026-11-01 note: the pin was also a hinge for a bay load; retired 2026-11-06, float mode).
The bartack on that eye is the v3.1 assumption, 2700 N, SF **3.72**.

### Loads

Factored force on one side. The vector is the beam-model node force times the case factor.
CG for the bag cases is 148 mm, the v3.1 bag. Set-down loads the foot, not these nodes.

| station | z mm | case | N | aft N | down N | what clips |
|---|---:|---|---:|---:|---:|---|
| hinge | 60 | tall_load | 726 | 190 | 700 | bag hinge and the bay pivot |
| im1 | 190 | meat_straps | 267 | 248 | 100 | meat strap IM1 only |
| im2 | 330 | tall_load_posts | 403 | 391 | 100 | bag clip and meat strap IM2, beside the branch window |
| im3 | 520 | tall_load_posts | 554 | 545 | 100 | bag clip and meat strap IM3 |

### Safety factors

Failure index is the layered PAHT check (in-plane, layer-normal, interlayer shear).
The 99th percentile is taken on the fairlead plastic, not on the clamped end of the stay stub.
Fatigue scales that index from the factored case down to the 1.6 g walking peak, then divides
into the 0.3 fatigue ratio. Creep rupture uses the 1 g stress and the 0.4 ratio.
Bearing allowable is 0.8 × Z tensile, because an aft pull bears across the layers.

| fairlead | host r mm | mesh mm | strength SF | fatigue SF | creep SF | bearing SF | added g |
|---|---:|---:|---:|---:|---:|---:|---:|
| hinge 1.00 mm | 9.4 | 1.00 | 2.97 | 1.67 | 3.56 | 5.97 | 6.2 |
| im3 1.00 mm | 16.8 | 1.00 | 3.91 | 2.20 | 4.70 | 7.82 | 6.1 |

Pin, double shear, governing hinge load: yield SF **14.4**, fatigue SF **16.1**. UHMWPE sleeve projected bearing SF **2.32** (9.1 MPa). The sleeve is a wear part. Replace it when the hole goes oval.

The coarse mesh is in the results JSON. The fine mesh is the number above. The cheek is 8 mm,
so a 1 mm element is eight through the thickness, not a one-voxel skin.

#### Load lifters and the hipbelt

Neither interface moves onto the printed fairleads.

- **Hipbelt.** The Ti pivot is unchanged. Factored drop load at the 80 % hip share is **1600 N**. The mount's checked SF/required is 8.6 (static) and fatigue 19.7 (`analysis/generative_design.md`). The lumbar struts already carry it; the branch-frame minimum is 1.66 on hipbelt-off, which is this path with the belt undone.
- **Load lifters.** They stay on the carbon crown corner wraps, never on the extension posts (US 10,952,523). Spring split kz 3 / (3+10) of the non-hip load, angle 40.6° from horizontal. Factored tension **71 N** per side. Webbing SF **188** on the 25 mm polyester record. Ladder-lock slip SF **4.2** on that split, **1.69** with the hipbelt off, and **1.95** if the lifters are assumed to take half the non-hip load.
- The half-share sensitivity is the reason for a **tri-glide keeper** behind each ladder lock.
  The ladder lock adjusts. The keeper stops the tail so a slip cannot dump the lifter.
  The sewn loop on the crown lug is the structural end. It does not depend on the ladder lock.

### Options

| option | added g | detach s | governing SF | pass | why it lost, or why it won |
|---|---:|---:|---:|---|---|
| Branch fairlead | 117 | 34 | 1.67 | yes | shows the branch |
| Printed clip ear | 58 | 20 | 0.28 | no | tongue fatigue 0.28 at a 18 mm root |
| Webbing through window | 40 | 45 | 0.40 | no | return strand crosses the back |
| Sleeve over the limbs | 18 | 180 | 2.00 | no | hides the frame |
| Magnetic buckle | 90 | 12 | 0.41 | no | 300 N vs 726 N |
| Cam strap | 132 | 30 | 1.99 | no | creeps under gait |
| Rail and slider | 273 | 25 | 2.50 | no | covers the stay face |
| 25 mm buckle in series | 54 | 30 | 0.62 | no | 450 N break |
| 38 mm buckle in series | 108 | 30 | 1.24 | no | estimate, thin at the hinge |

Detach times are assumptions for gloved hands: 4 s a hook, 4 s a tethered pin, 10 s to clear the bag.
A sleeve is three minutes because the crown and the hipbelt block sliding it off.

### Mass and cost

| part | g |
|---|---:|
| printed fairleads (8) | 49.4 |
| 7075 pins (8) | 19.3 |
| UHMWPE sleeves (8) | 2.3 |
| bag hooks, 38 mm Al (4) | 36.0 |
| TPU hook sleeves (4) | 4.0 |
| webbing eyes, net of old stubs | -6.7 |
| bag-side straps | 17.9 |
| B-01 swell patches | 12.3 |
| elastic keepers | 8.1 |
| lifter tri-glide keepers | 5.2 |
| old LINK hardware removed | -30.8 |
| **delta** | **117** |

Pack **2982 g (6.58 lb)**. The 5.0 lb target is still missed, by **714 g**. This attachment is not the reason; the branch frame already was.

Cost is marginal. Filament $4.26, scrap $0.64, extra machine time $1.75, hooks pins and webbing $41.20. **$48** on top of the frame.

### How it is built

- Fairlead root is blended into the stay. It does not break into the 18 mm sleeve bore.
  The bore is cut after the fairlead in `frame_sdf`.
- Pin axis is lateral, so the hole lies in the print layers (build direction is frame y).
  The hole is a drawn loop in each layer, not a bridge in mid-air.
- UHMWPE sleeve, OD 7.2 mm, pressed into the cheeks. The pin turns in the sleeve, not in the nylon.
- Hinge pins (z 60) have a pull ring and a silicone washer, tethered to the bag eye.
  Pull them and the bag leaves (bag off and float mode; the hinged bay load was retired 2026-11-06).
- IM1 (z 190) keeps a captive eye for the meat strap. The bag does not clip there.
  IM2 (z 330) and IM3 (z 520) take a bag hook and a meat hook on the same eye.
- B-01 is only 20 mm aft of the stay centre, so the stay crown leaves a few millimetres.
  Each fairlead stands about 14 mm proud of the surface.
  A feathered 16 mm swell in B-01, 90 mm long, puts 2 mm of air over the cleat
  so it does not rub the cloth or print a point into the meat. The swell is inside the bag.
- The Sandwich v2 spreader (BP-06 rev B, `spreader.md`) is notched 30 mm in height at the z 142, z 190, z 330 fairleads,
  with R6 roots and 6 mm of air round each cleat (`cut/spreader/README.md`). The notch is at the edge landing,
  not in the window span. The rails and the mesh are untouched.
- Slack hooks sit under a 3 mm elastic keeper so an empty pack does not click on the stalk.
- Field repair: spare pin, spare sleeve, spare hook, in the hipbelt pocket. A cracked cleat
  is bypassed with a girth hitch of the same 38 mm webbing around the stay. The stay is intact.

### Screenshots

- `docs/screens/20261101_attach_1_options.png`
- `docs/screens/20261101_attach_2_closeup.png`
- `docs/screens/20261101_attach_3_exploded.png`
- `docs/screens/20261101_attach_4_fea.png`

### Assumptions

- Hook 1500 N and 9 g, bartack 2700 N, cam 1100 N / 22 g: carried over from DESIGN.md §4.5 (2026-11-01). The bag hooks are now the rated part and PT-1 (section 3); the bartacks are checked by stitch count in section 5.
- Pin price $2.50 is a small-shop assumption; tri-glide 2.6 g (triglide_25mm record) and elastic hook keeper 1.35 g (elastic_25mm x 90 mm cut, ASSUMPTION) since BL-035. Aluminium strength is the 7075 record, S-basis.
- UHMWPE sleeve strength is the sheet yield, 21 MPa. No fatigue number is published here; the sleeve is replaceable.
- B-01 patch 200 gsm is an assumption. The cloth is the same `challenge_ultra_200` as the panel; the gram is the patch area.
- Detach and attach seconds are gloved-hand assumptions, not a timed trial.
- Lifter share uses the spring stiffnesses in `load_cases.py`. The half-share line is a sensitivity, not the design case.
- Hip share 80 % is the load-standard assumption.
- Fairlead FEA is a stay stub with fixed ends. It does not re-solve the whole frame. The fairlead is added material, and the bore is not opened, so the published branch-frame factors still stand.
- Cam creep is the note already in `geometry.yaml` crown_retention (cam teeth hold, webbing walks).
- Rail mass uses `alu_6061_t6` density and a 20 × 4 mm bar, 520 mm, two of them, plus 12 g sliders (assumption).
- Sleeve mass is two 500 × 90 mm wraps at 200 gsm (assumption). It is rejected on the look, not on the grams.

### Open questions for the owner (2026-11-01)

1. Closed: the bag-hook rating is section 3 (rated part, PT-1). The meat-strap hooks keep the 830 N test.
2. IM1 stays a meat anchor only (no bag clip).
