# Meat carry without the swing: alternatives to "between mode"

Owner: pack-designer. 2026-11-06.

> **Status (2026-11-06): the owner chose Concept A and it is implemented.** All three gaps are kept (120 / 170 /
> 220 mm; the owner packs boned and bone-in meat). The link is part **B-24** (38 mm x 435 mm, the final cut is 5 mm
> shorter than the 440 mm estimate below; +54.4 g). Records: `analysis/meat_haul_modes.md` C (loads, lever),
> `analysis/bag_attachment.md` §5 (B-24 strength, PT-6) and §7 (float procedure, 128 s),
> `cut/attachment/attachment_parts.pdf` / `.dxf` (B-24 1:1), `geometry.yaml` weight group
> `float-mode stand-off links B-24`, DESIGN.md D-33. The structural hand-off is §8 below. Sections 1-7 are the
> study as the owner saw it.
Trigger: the owner saw the 3D render of between mode (the bag pivots about 28.5 deg on the z 60 hinge pins to open a
wedge for a quarter) and said: "I do not like the swing motion. Research other bags."
Research: `docs/research/meat_carry_mechanisms.md` (this phase) on top of `docs/research/bag_attachment_research.md`.
Today's modes: `analysis/meat_haul_modes.md` (A bag on, A2 between, B bag off), `analysis/bag_attachment.md` §7.

## Decision asked of the owner

**Recommended: Concept A, "parallel float".** Between mode retires. For bulk meat the bag comes off its pins, the meat
goes on the frame the same way as the bag-off haul (pin-to-pin cradle + IM1-IM3 eye to eye), and the bag hangs back on
**two short 38 mm stand-off links** clipped to the IM3 eyes, parallel to the frame, at a set gap of 120 / 170 / 220 mm
(4.7 / 6.7 / 8.7 in). W1-W3 close round it. The bag never pivots in use.

- **Mass +55 g** (2 links with rated hooks). **No frame change**, no new bag panel, no fabric between bag and frame.
- Loaded lever, 36 kg (79 lb) quarter + 12 kg (26 lb) of gear: CG **158 mm** aft at the 170 mm gap (swing today
  **179 mm**); 68 kg rated: **142-171 mm** (rev C meat case 190 mm). Inside rev C as long as the smallest gap that fits
  the meat is used (36 kg at the 220 mm gap is 189 mm: on the line).
- Time about **120 s** (swing today 70 s; bag-off haul 108 s). Slower, because the pins come out.
- Patent: no fabric panel, lifters untouched, nothing near the spreader/z 330 gap: low. FTO read on US 12,495,885 stays
  open.

## 1. What the research says (short)

From `meat_carry_mechanisms.md` §3:

1. **No leader pins the bag on a bottom hinge for meat.** They either translate the bag aft on lengthened straps over
   a floor (Stone Glacier, Mystery Ranch, Eberlestock) or take the bag off, fix the meat to the frame and lay the bag
   back over it (KUIU ICON, Initial Ascent, Kifaru, Exo's own steps, Seek Outside). Where a "V" appears (Exo, KUIU) it
   comes from cinching the lower straps first, not from a pivot.
2. **Meat to the frame first, bag second** is what owners like (Exo frame-only straps, Kifaru Grab-It "no sagging",
   Paradox "compress the meat against the frame by itself", IA pannier). We already have this: the pin-to-pin cradle and
   IM1-IM3 eye to eye.
3. **The pain points to design against:** sag / rides low; bag top flops; straps too short over a full load; time and
   fiddling; wrong-buckle confusion.
4. **Leverage:** SG measured 32 lb -> 14 lb of leverage by stacking the same load high and close; keep the meat an
   even thickness the height of the frame.

Our swing works (the cleats, hinge and cradle pass in `meat_haul_modes.md` A2), but it forces a wedge: 71 mm at IM1,
250 mm at IM3, so the bag's upper aft corner swings furthest from the back, the hood cannot re-engage, and the meat must
be shaped to the wedge.

## 2. Hard constraints (all three concepts are checked against these)

| # | constraint | source |
|---|---|---|
| H1 | No fabric meat shelf / panel between frame and bag; no frame-to-bag strap under such a panel | US 12,495,885 (Eberlestock) claims 1, 9; DECISIONS 2026-11-01 (no meat shelf) |
| H2 | Under-straps run pin to pin (US1 z 95, US2 z 142) | `meat_haul_modes.md`, US 12,495,885 |
| H3 | Lifters stay on the crown top bar in every mode | US 10,952,523 (Mystery Ranch) |
| H4 | No bag webbing between the spreader and the z 330 cross member | US 8,381,956 (Mystery Ranch, est. to 2027) |
| H5 | Meat held by internal meat straps IM1-IM3 | DECISIONS 2026-11-01 |
| H6 | Generative printed frame, no new frame feature for this | DECISIONS 2026-11-01, `bag_attachment.md` §9 |
| H7 | Sandwich v2 spreader is the bearing face | DECISIONS 2026-11-05 |
| H8 | HA-LS-1 rev C: meat cases 190 mm aft, bag cases 205 mm at z 550 | `load_standard.md`, DECISIONS 2026-11-06 |

## 3. The concepts

Sketches: `outputs/screens/20261106_meatcarry_1.png` (today vs A / B / C, side view), `_2.png` (Concept A: link and
steps), `_3.png` (how the leaders move the bag), `_4.png` (lever comparison).

### Concept A: parallel float on stand-off links (recommended)

**How it works.** The bag comes off exactly as in the bag-off procedure (hood lift, four bag hooks, two cams, two hinge
pins). The quarter, in its game bag, goes on the frame exactly as in the bag-off haul: in the two pin-to-pin
under-straps (the cradle), bone toward the spreader, IM1-IM3 hooked eye to eye over it and cammed. Then two
**stand-off links (SL)** hook onto the IM3 captive eyes (z 520, x +/-115), one per side. Each link is 38 mm webbing with
a rated hook at the frame end and three sewn loops at the bag end. The bag is stood behind the meat, upright and
parallel to the frame, and its two T3 bag hooks clip into the loop that matches the meat's thickness. W1-W3 then close
round bag and meat (ladder locks, as today). The bag translates straight back; nothing rotates.

```
     frame (stays)          meat on cradle + IM          bag (upright)
        |  IM3 eye o==SL link==loop o- T3 hook  |              |
        |                 [ game bag ]          |   gear       |
        |  US1/US2 cradle \_______/             |              |
```

**What holds what.** Meat: cradle (vertical) + IM1-IM3 (cinch to the spreader), i.e. the bag-off haul path already
checked (cradle 489 N, cam SF 2.25; IM 225 N, hook SF 6.67, `meat_haul_modes.md` B). Bag: hangs from the two links at
IM3 (vertical and top-in), W1-W3 hold it to the meat (horizontal). The bag no longer carries any meat load.

**Gap.** Loops at 120 / 170 / 220 mm bag-to-frame gap. Space between bag and frame at 170 mm: about 32 L (1930 cu in);
at 220 mm about 41 L (2500 cu in), the same as the SG and KUIU published sling volumes (ASSUMPTION: 300 mm meat width,
z 80-700). The 85.2 L main bag is unchanged and still counts alone.

**Changes to existing parts.**

| part | change |
|---|---|
| bag hooks (T2/T3, 4 x 2200 N) | No change. In float mode the two T3 hooks clip into the SL loops; the two T2 hooks hang on their elastic keepers |
| crown hood B-19 + guys TG | No change. In float mode the hood is lifted and lies on the bag top (as in today's between mode); the guys stay sewn to it. Lifters stay on the crown (H3) |
| B-20 hood ladder | No change |
| hinge pins + HE eye + B-18 doubler | No change to the parts. In float mode the pins are pulled (as for bag-off) and stay tethered to the bag. **The hinge is no longer used as a hinge in any carry mode**: the A2 "between" case (hinge 264 N) retires; HE / B-18 stay sized by the bag-on 1019 N factored case |
| under-straps US1 / US2 | No change; pin to pin (H2). In float mode they are the meat cradle, as in the bag-off haul |
| IM1-IM3 meat straps | No change; eye to eye over the meat (H5) |
| W1-W3 haul wraps | No change. Length check at the 220 mm gap: needed about carry path + 2 x 220 = W1 1010 / W2 1082 / W3 1288 mm, available haul path 1190 / 1262 / 1468 mm (`geometry.yaml` haul_wraps) |
| **new: SL stand-off links x 2** | 38 mm `poly_webbing_38mm`, cut 440 mm. Frame end: rated 38 mm hook (same part as the bag hooks, >= 2200 N) in a 45 mm fold, box-X 38 x 38. Bag end: three loops (25 mm opening) at 120 / 170 / 220 mm gap, each a 50 mm fold with a full-width bartack. Stowed in the lid or hipbelt pocket |
| frame, spreader | No change (H6, H7). The IM3 eye is the same captive eye that takes a bag hook today; nothing is added between the spreader and the z 330 bar (H4) |

**Mass delta: +54.6 g, call it +55 g.** Webbing 2 x 0.44 m x 28 g/m = 24.6 g (`poly_webbing_38mm` record); hooks 2 x 14 g
(ASSUMPTION, `bag_attachment.md` §13); thread 2 g. Option: the repair kit already carries a spare rated hook and 0.6 m
of 38 mm webbing (45 g, not in base weight); the links could replace those (the spare hook rides on a link), net about
+30 g in the carried kit. Not counted here.

**Load CG / rev C.** Simple lever sum (ASSUMPTION: 12 kg / 26 lb of gear left in the bag; meat a uniform slab whose CG
is at half the gap from the bag-side face of the spreader at y 19 mm; bag gear CG at the uniform-fill 148 mm from the
bag's frame face, `geometry.yaml` bag.cg_uniform_fill, moved aft by the gap):

| case | swing today | A, gap 120 | A, gap 170 | A, gap 220 | rev C meat case |
|---|---:|---:|---:|---:|---:|
| 36 kg quarter + 12 kg gear | **179 mm** (84 N m) | 127 (60 N m) | **158** (74 N m) | 189 (89 N m) | 190 mm |
| 56 kg meat + 12 kg gear (68 kg rated) | 159 (106 N m) | 113 (75 N m) | 142 (95 N m) | **171** (114 N m) | 190 mm (127 N m) |

The swing row uses today's assumptions (meat CG 110 mm, `meat_haul.py`; bag CG rotated 28.5 deg about the z 60 pin, which
puts the gear at 387 mm aft, z 466). The float keeps the bag's gear closer at the usual gaps because the bag does not tip
back. Rule for the user guide: **use the smallest loop the meat fits** (the 220 mm loop with a light load is on the
190 mm line). Moments at 1 g are under the rev C C5 moment (68 kg x 190 mm = 127 N m) in every row.

New load on the frame: the bag hangs on the IM3 eyes through the links. Worst case, all 12 kg on two links at 30 deg
(no help from W1-W3 or friction): 118 N per link at 1 g, **353 N factored** (x 3.0). That is below the 1415 N factored
bag-hook load the IM3 eye already carries in bag-on (`bag_attachment.md` §3); hook SF 6.2. The meat path is the bag-off
haul already checked. **Hand-off:** structural-fea-engineer to confirm that the IM3 eye with meat strap + link together
stays inside the rev C IM3 envelope, and to add "float" in place of "between" in the frame cases. Cloth sim not needed
for the meat; a quick sim of the hanging bag would confirm the sag (pain point 1).

**User steps (gloved estimate, ASSUMPTION: 4 s a hook or pin, 3 s a cam, 10 s to place the bag).**

1. Bag off: set down, hood lift, 4 bag hooks, 2 cams, 2 pins, lift clear (52 s, `bag_attachment.md` §7).
2. Quarter in the cradle, bone to the spreader, cam the under-straps to about 70 mm belly (12 s).
3. IM1-IM3 eye to eye over the meat, cam (24 s).
4. Hook the two links on the IM3 eyes (8 s). (Can be done before step 2.)
5. Stand the bag behind the meat, upright; clip each T3 hook into the loop that just touches (10 s + 4 s).
6. Close W1-W3 round bag and meat (18 s).

**About 128 s**, or about 120 s if the links stay hooked on the IM3 eyes under keepers. Today's swing is 70 s; the
bag-off haul is 108 s. The 2-minute bag-off limit does not apply to a haul mode; field reports put strap-pack conversions
at "a few seconds" (Exo review) to about 30 + 30 s (SG, reported).

**What it fixes from the research list.** Sag: the meat is on the frame, the bag carries none. Flop: the bag is hung at
IM3 and wrapped by W3 on the crown. Straps too short: the W lengths are checked above. Wrong buckle: the links use the
bag's own hooks and the frame's own eyes; nothing new to mis-clip. The top re-attach over meat (K4 lesson): the hood is
not re-engaged, as today.

**What it costs.** Two loose parts to carry (or lose); pins out and back in (as for bag-off); about 50 s slower than the
swing.

**Patent risk: low.** H1: no fabric panel between frame and bag; the meat floor is the pin-to-pin under-straps
(frame to frame); the links run frame to bag but there is no panel for them to be "underneath". Do not sell or show a
game bag / pannier that attaches to both frame and bag. H3: lifters untouched. H4: links are at z 520, above the
spreader (z 112-430) and the z 330 bar. Spacing a bag aft of a frame on adjustable straps is taught by Mystery Ranch's
US 8,579,171 (listed expired, lapsed 2025-12-15: confirm in the FTO read). No live claim found on hanging a bag on
links clipped to frame eyes.

**Beginner sewability: easy.** Two straight webbing parts: hot-knife cut, one box-X round a hook bed, three bartacks.
Same stitch as T2/T3 (box-X 7 SPI, tex 135, `bag_attachment.md` §5). Four plies of 38 mm at each bartack: the same
machine as the rest of the joint.

### Concept B: bag-off only, bag strapped over the meat (no links)

**How it works.** Steps 1-3 of A, then the full bag is laid behind the meat and held **only** by W1-W3 (the Initial
Ascent / KUIU ICON method). Between mode retires; nothing is added. Variant B2 (today's bag-off haul step 4): bag strapped
over the crown with W3; rejected for a full bag (gear above the head, R-28 head clearance and a high CG).

**Changes.** None to hooks, hood, guys, ladder, pins, under-straps or W1-W3. Procedure text only.
**Mass delta: 0 g.**
**CG / rev C.** Nominally the same lever as A at the same gap, but the gap is not set by anything: the bag finds its own
height and lean against the meat and the wraps. The research's top two complaints are exactly this: sag (KUIU "sag a
little", MR "rides low") and flop (SO "flopping around" without top straps). Our W1 / W2 cross diagonally (R z 80 to L
z 250, R z 250 to L z 420), which helps against sag but does not hang the bag. The bag's weight sits on the meat and
the wraps' friction (ASSUMPTION mu 0.4, `meat_haul.py`), so a wet game bag or a short load lets the bag slide down.
**User steps.** About 106 s (A without the links).
**Patent risk.** Low (as A; nothing added).
**Beginner sewability.** Nothing to sew.
**Verdict.** The cheapest answer, and the most-used method in the field, but it accepts the top pain point. It is A
without the two links; if the owner wants 0 g, this is the fallback, and the links can be added later without changing
anything else.

### Concept C: meat inside the bag against the spreader (bag-on mode only)

**How it works.** No separate between mode. All meat goes inside the bag, in a game bag, against B-01 and the spreader,
held by IM1-IM3 through the B-01 ports (today's mode A, the Stone Glacier Terminus "Load Cell" idea without a sewn
cell). Bone-in quarters too big for the bag use the bag-off haul (mode B).
**Changes.** None to any attachment part. Between mode and its procedure retire. The hinge stays a hinge only for putting
the bag on.
**Mass delta: 0 g.** (A sewn meat sleeve/cell was set aside by the owner at the 2026-11-05 feature freeze; not proposed.)
**CG / rev C.** This **is** the rev C meat case: cloth sim meat contents 181 / 174 / 166 mm at 15 / 19 / 23 in (168 / 163 /
159 mm with the meat at 150 mm), inside 190 (`bag_attachment.md` §2). The best-characterised option.
**User steps.** Lay the pack on its back pad, open the roll-top, take the gear out (into the fly bag), lower the game bag
down B-01, hook IM1-IM3 through the ports and cam, repack the gear on top, roll and clip. Estimate 3-4 min (ASSUMPTION,
not timed). The weak point: IM1 is at z 190, about 0.9 m (35 in) below the fill line at z 1101, so the lowest hook is a
long gloved reach down a narrow tube; the diagonal zip ends at z 631 and does not help at the frame face.
**Pain points from the field.** Unpack and repack every load; blood inside the main bag (Terminus owners line it with
game bags; SG staff advise a separate cell bag); bulky bone-in quarters do not fit (KUIU rep, reported). Some owners
prefer it as "much faster and easier, and more comfortable" (Rokslide, reported) for boned meat.
**Patent risk.** None found (meat in the bag on internal straps is the released design).
**Beginner sewability.** Nothing to sew.
**Verdict.** Keep it as the everyday boned-meat mode (it already exists), but it does not replace a bulk-meat mode on its
own.

## 4. Side by side

| | A parallel float (links) | B bag-off, bag over meat | C meat inside the bag |
|---|---|---|---|
| bag motion | off pins, hung back parallel on links at a set gap | off pins, laid over meat, finds its own place | none |
| meat held by | cradle + IM1-IM3 on the frame | cradle + IM1-IM3 on the frame | IM1-IM3 through the ports, bag floor + under-straps |
| bag held by | 2 links at IM3 + W1-W3 | W1-W3 only | pins, hooks, hood, guys |
| new parts | 2 stand-off links | none | none |
| mass | **+55 g** | 0 | 0 |
| CG, 36 + 12 kg | 158 mm (170 gap) | ~158 nominal, not held | sim 174 mm (19 in, 68 kg case) |
| rev C | inside (smallest loop that fits) | inside nominally | is the rev C case |
| time | ~120-128 s | ~106 s | ~3-4 min |
| top pain point answered | sag, flop | neither | sag (bag shell), but slow and bloody |
| patent risk | low (no panel, FTO '885) | low | none found |
| sewing | 2 webbing parts, box-X + bartacks | none | none |

## 5. Recommendation

**Concept A.** It removes the swing the owner disliked and does what every leader does (bag aft of a frame that holds
the meat), but it answers the two complaints the strap-only packs leave open: the bag is hung, so it does not sag, and it
is held parallel at a chosen gap, so the lever is set, not left to the wraps. It uses our existing hard points (IM3 eyes,
the cradle, W1-W3, the rated bag hooks), adds 55 g of webbing and hooks, needs no frame or bag panel change and keeps all
four patent guardrails. C stays as the everyday boned-meat mode; B is A's 0-gram fallback.

**If adopted (later, not in this task):** `meat_haul.py` "between" -> "float" (load case: meat path = bag-off haul + bag
hang on IM3); `attach_system.PROCEDURES` between -> float steps; DESIGN.md decision row; `build_geometry.py` weight row
(+55 g); the SL drawing in `cut/attachment/`; the 3D render scene; structural re-check of the IM3 eye with link + meat
strap; a timed gloved trial.

## 6. Open questions for the owner

1. **What did you dislike: the motion itself, the look of the tipped bag in the render, or the time?** A answers the
   first two at a cost of about 50 s; if it was time, C (or the swing) is quicker.
2. **Accept +55 g** for the two links (pack 3447 -> about 3502 g, 7.72 lb), or B at 0 g?
3. **Gap steps 120 / 170 / 220 mm** assume boned meat to a bone-in elk hindquarter. What do you usually pack: boned
   meat in game bags, or bone-in quarters? (Sets the loops; ASSUMPTION today.)
4. **Links carried always, or only on a meat trip?** (Base-weight counting.)
5. FTO read on US 12,495,885 and the US 8,579,171 lapse: still open from 2026-11-05.

## 7. Assumptions

- 12 kg of gear in the bag on a meat trip; meat a uniform slab with its CG at half the gap; bag gear CG 148 mm from the
  bag's frame face (uniform-fill value) at the gap. Lever arithmetic, not a cloth sim.
- Rated hook 14 g, 2200 N (`bag_attachment.md` §13). Link at 30 deg carrying all the bag's weight, factor 3.0.
- Space between bag and frame = gap x 300 mm x 620 mm (z 80-700).
- Times: 4 s a hook or pin, 3 s a cam, 10 s to place the bag; gloved, not timed.
- C's 3-4 min is a guess for unpack, load, repack; not timed.

## 8. Hand-off to the structural-fea-engineer (float mode, 2026-11-06)

> **Answered 2026-11-06 (structural-fea-engineer, [float_fea.md](float_fea.md)).** IM3 eye solved directly with the
> float vectors: design 559 N SF **4.01**, fatigue **2.04**; misuse 1142 N SF **2.08**, fatigue **1.11** (0.75 mm mesh
> -2 %). The printed cheek at the 1415 N bag-on hook case gives SF 1.54 and the misuse vector sits inside it. Friction
> is **not** credited (no sourced coefficient, no measured clamp force): US1 fatigue 0.95 at 56 kg stands, so the
> **float meat limit on the frame is 53 kg (116 lb)**, cradle cammed to the 70 mm belly (at 50 mm: about 41 kg).
> The between case is in no envelope. HA-LS-1 rev C note: `load_standard.md` §4.3.

Do not re-run the bag-side checks; they are in the records. These are the frame-side loads that changed. Factored =
HA-LS-1 x 3.0 (2.0 g x 1.5) unless stated; per side; FCS (y aft, z up). Source: `analysis/meat_haul_modes.json`
`float` (`meat_haul.analyse`, cradle basis `cradle_fea.json`).

**1. IM3 captive eye (z 520, x +/-115): meat-strap leg + one B-24 link on the same eye.**

| case | what | link N | eye resultant N | fy N (aft) | fz N | IM3 cleat SF (scaled) | fatigue SF (scaled) |
|---|---|---:|---:|---:|---:|---:|---:|
| design | 36 kg meat on the frame + 12 kg gear in the bag (ASSUMPTION) | **353** | **559** | 531 | -177 | 3.87 | 2.18 |
| misuse envelope | 36 kg meat + 32 kg in the bag (rest of the 68 kg rating) | **941** | **1142** | 1040 | -471 | 1.90 | **1.07** |

Basis: meat-strap leg 225 N aft (150 N hand cinch x 1.5, the bag-off rule); link 30 deg below horizontal (aft and
down) carrying the whole bag (no W1-W3 friction credited). The scaled SFs are the IM3 fine-mesh fairlead solve
(`bag_attachment_results.json`, 554 N) scaled by force, so the direction change (more downward than the solved aft
pull) is NOT checked. **Ask:** solve the IM3 fairlead with the envelope vector (1040 aft, -471 down) and confirm it is
inside the rev C IM3 bag-couple case (bag-on factored IM3 hook load 1415 N, `attach_system_results.json`).

**2. Cradle anchors US1 (z 95) / US2 (z 142): unchanged from the bag-off haul** for the design case: US1 489 N
(fy 418, fz -254), strength SF 3.28, fatigue SF 1.47; US2 326 N, SF 4.91 / 2.21; cam SF 2.25.
**Open:** 56 kg of meat on the frame (68 kg rating minus 12 kg of gear) is NOT in the design case: on the
no-friction rule US1 = 760 N, strength SF 2.11, **fatigue SF 0.95**, cam SF 1.45. Either credit the W1-W3 squeeze /
IM friction (mu 0.4, 5 clamping straps) or keep the float meat limit at one quarter (36 kg); recommend which.

**3. IM1 / IM2 eyes:** 225 N aft each (meat-strap cinch only), as bag-off.

**4. Hinge pins z 60:** **0 N in float** (pins pulled, tethered to the bag). The retired `between` case (hinge 264 N,
IM3 496 N, CG 110 mm assumption) can be dropped from any envelope that still lists it. Bag-on hinge (1019 N
factored, HE / B-18) is unchanged.

**5. Load CG for the frame cases** (lever sum, not a cloth sim; rev C meat case 190 mm):

| gap | 36 kg meat + 12 kg gear | 56 kg meat + 12 kg gear |
|---:|---:|---:|
| 120 | 127 mm | 113 mm |
| 170 | 158 mm | 142 mm |
| 220 | 189 mm | 171 mm |

All inside rev C; the 220 mm gap with a light meat load is on the line (user rule: smallest loop that fits). A T9
measurement in float at 220 mm is worth adding.

**6. Crown top bar:** the hood is lifted in float (no hood capture, no guy load). W3 still wraps from the crown, as
in the retired mode; its path at 220 mm (about 1288 mm) is inside the 1468 mm haul path.

**7. Not changed:** spreader face pressure (the meat bears on the spreader exactly as in bag-off), lifters (stay on
the crown corner wraps), hipbelt pivot.

## Screenshots

- `outputs/screens/20261106_meatcarry_1.png`
- `outputs/screens/20261106_meatcarry_2.png`
- `outputs/screens/20261106_meatcarry_3.png`
- `outputs/screens/20261106_meatcarry_4.png`
- `docs/screens/20261106_pack3d_float.png` (implemented float, 170 mm)
- `docs/screens/20261106_pack3d_float220.png` (220 mm)
- `docs/screens/20261106_pack3d_float_links.png` (B-24 links at IM3, X-ray)
- `docs/screens/20261106_attach_6_float.png` (load path), `docs/screens/20261105_attach_4.png` (procedure storyboard),
  `docs/screens/20261105_attach_5.png` (parts incl. B-24)
