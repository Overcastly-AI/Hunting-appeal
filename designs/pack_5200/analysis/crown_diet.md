# BL-017: a lighter crown and torso-adjust block that stays adjustable (study, nothing adopted)

Owner: structural-fea-engineer, 2026-11-11. Ticket: `docs/backlog/BL-017-crown-block-diet.md`. Standard: HA-LS-1
rev C ([load_standard.md](load_standard.md)), every case of both bag-couple variants (C = couple on the crown bar,
C_im3 = couple on the IM3 hooks), including C8 hipbelt-off (governs the legs and spine) and C6p posts (governs the
corner bonds). Baseline: H1 ([frame_h1.md](frame_h1.md)) with the adjustable torso kept (DECISIONS 2026-11-11, after
BL-007 [frame_fixed_torso.md](frame_fixed_torso.md)).

- Code: `huntkit/gendesign/crown_diet.py` (imports `frame_cg_recheck`, `rev_c_verification`, `frame_fixed`,
  `frame_h1`, `frame_comp_d`, `huntkit.fea`, `huntkit.mass.ledger`; nothing copied). Tests: `tests/test_crown_diet.py`.
- Results: [crown_diet_results.json](crown_diet_results.json). Run: `python -m huntkit.gendesign.crown_diet all`
  (about 10 min on 2 cores from cold; beam runs and voxel solves cached in `outputs/crown_diet/`).
- Figure: `outputs/screens/20261111_BL017_1.png` (saving per option and size; crown margin map).
- Masses from the mass ledger (`huntkit.mass.ledger`, config `corrie_b2_h1`, belt M: **3927.0 g**) plus item deltas,
  each traced below. Imperial in brackets.

> **BL-035 refresh (pack-designer, 2026-11-13).** `crown_diet_results.json` was re-run on the record masses: the
> torso-adjust cam is `cam_25mm_al` 12.2 g (was 12 g) and the release-cord toggle `pom_toggle` 1.7 g (was 3 g), so the
> torso-adjust row is 40.6 g (was 41.7 g) and (d1) saves **45.4 g** (was 45.2). The ledger pack (`corrie_b2_h1`, belt
> M) is now **3973.5 g** (was 3927.0): +26.0 g #10 door sliders, +16.0 g stainless US tri-glides, +1.9 g IMP-4 #5
> slider (BL-034 records), +4.5 g elastic hook keepers, -0.8 g lifter tri-glides, -1.1 g torso adjust (BL-035). The
> recommended option saves **112.6 / 93.6 / 74.6 g** (S / M / L; was 112.4 / 93.4 / 74.4); with it the pack is
> 3879.9 g at M. The tables below keep the BL-017 figures; the JSON holds the current ones.

## 0. Result

| | H1 today | **recommended: (a)+(d1)+(c17 bore 19)** | (a)+(d2)+(c17 bore 19) | (a)+(d1), no leg change |
|---|---:|---:|---:|---:|
| block saving S / M / L, g | 0 | **112.4 / 93.4 / 74.4** | 101.6 / 82.6 / 63.6 | 92.0 / 72.8 / **53.5** |
| block saving, oz (M) | 0 | **3.3** | 2.9 | 2.6 |
| frame (ledger rows) M, g | 1025.1 | 968.9 | 971.6 | 989.5 |
| CORRIE B.2 pack, belt M, size M, g (lb) | 3927.0 (8.66) | **3833.6 (8.45)** | 3844.4 (8.48) | 3854.2 (8.50) |
| crown legs FPF (min of sizes) | 1.116 | **1.127** (L) | 1.127 | 1.116 (L) |
| spine / top bar / corner-bond peak | 1.178 / 1.246 / 1.217 | 1.178 / 1.270 / 1.353 | same | 1.178 / 1.262 / 1.195 |
| body strength / fatigue (recorded basis) | 1.453 / 1.279 | 1.450 / **1.209** (c17b19, 15/19/23) | same | 1.453 / 1.279 |
| body fatigue, one tag per torso (like for like, §3.3) | 1.150 | **1.116** | 1.116 | 1.150 |
| torso adjust while worn | lengthen and shorten | lengthen only (shorten pack off) | both | lengthen only |
| sizes | one frame 15-23 in | 3 crown kits on one printed body: S 15-18, M 17.5-20.5, L 20-23 in | same | same |
| rev C | pass | **pass** | **pass** | pass |

- **Reproduced first** (beam model, same 42 rev C sets): crown legs **1.116** (C_im3, C8 hipbelt-off, 23 in), top
  bar **1.246** (C_im3) / 1.377 (C), spine **1.178** (C8, 15 in), corner-bond peak 1.217 (C6p posts, 15 in), leg ring
  crush 2.334, bushing bearing 17.6, rack 6.27, pawl cheek 1.40, buckling 1.854: all equal to
  `rev_c_verification_results.json`. Body (voxel, H1 solid, cached rev C sets): strength **1.453**, fatigue **1.279**,
  creep 2.730, equal to `frame_h1_results.json`.
- **Goal ≥ 60 g met at every size only with the leg change (c17 bore 19)**: 74.4 g at L, 93.4 g at M, 112.4 g at S.
  Without touching the legs, (a)+(d1) gives 92 / 73 / **54 g**: the L size misses 60 g, because the L kit has to keep
  H1's 430 mm legs and 300 mm spine (its top setting is H1's governing 23 in geometry).
- **No recommended option is below 1.0 on any check; the crown margins go up**, not down: legs 1.116 -> 1.127,
  corner peak 1.217 -> 1.353. The price is body fatigue reserve: 1.279 -> **1.209** on the recorded basis (CA-1 flip
  point 0.234 -> 0.248 against the 0.30 record; BL-007's fixed crown went to 0.277-0.289).
- The largest single saving is **(d1): delete the 3:1 pulley** (webbing, cam buckle, three guides: 45.2 g). The pawl
  already carries every rev C load (the beam model takes the pulley as slack), so no structural check changes.

## 1. The block, part by part (H1, 19 in unit)

| part | g | source | governing margin (rev C, min of both couples) |
|---|---:|---|---|
| crown legs 2 × 430 mm, OD 16 [±45 / UD × 8 / ±45] | 88.1 | beam model (frame.yaml) = 73.8 + 14.3 rev C | FPF **1.116** (C_im3, C8, 23 in, member CLbot-CL530: the leg inside the stay at the minimum 155.8 mm overlap); fatigue 1.358; ring crush 2.33 |
| crown top bar 214 mm | 20.2 | beam model = 17.9 + 2.1 | FPF 1.246 (C_im3, C8, 15 in) |
| crown spine 300 mm | 29.4 | beam model = 26.0 + 3.4 | FPF **1.178** (C8, 15 in, SP81-SP150) |
| crown-corner bondlines 0.8 mm | 2.2 | frame_mass_production.json crown_fix_lines_g | bond peak 1.217 (C6p, 15 in); bond fatigue 2.11 |
| spine clamp | 6.0 | pack5200.HW (ASSUMPTION there) | not checked |
| UHMWPE bushings 4 × 70 mm | 16.7 | pack5200 hardware formula | bearing 17.6, ring crush 2.33 |
| rack PA66-GF30 300 mm | 22.0 | pack5200.HW (ASSUMPTION there) | 6.27 |
| pawl housing + spring + Ti pawl | 14.0 | pack5200.HW (ASSUMPTION there) | pawl cheek 1.40 |
| pawl 304 bushings + pin | 9.9 | frame_branch.pack_numbers | pawl cheek 1.40 |
| pulley guides (3) | 8.0 | pack5200.HW (ASSUMPTION there) | none (pulley slack) |
| pulley webbing 25 mm × 1.4 m | 25.2 | ledger torso-adjust row; poly_webbing_25mm 18 g/m | webbing 582 |
| cam buckle | 12.0 | ledger torso-adjust row (ASSUMPTION there) | cam hold 67 walking, 6.1 hipbelt-off |
| release cord + toggle | 4.5 | ledger torso-adjust row balance | none |
| **block** | **258.3 (9.1 oz)** | | |

The legs, spine and corner bonds sit at 1.12-1.22, so thinning the tubes is out (as the ticket says). Everything
below the line "rack" (95.6 g) is mechanism, not structure.

## 2. Options

### (a) Three crown kits on one printed body (±1.5 in each)

Sizes **S 15-18, M 17.5-20.5, L 20-23 in** (travel 76.2 mm = ±38 mm each, 0.5 in overlap between sizes). The
printed body is H1, unchanged (same print files). Per size the legs, the spine and the rack are cut so that **at the
top of the size the leg sits in the stay exactly as H1's leg does at 23 in** (overlap 155.8 mm: the geometry that
governs the legs), and the spine passes the pawl by H1's 16 mm.

| size | leg cut, mm (in) | spine, mm | rack, mm | overlap top / bottom, mm | deepest leg bottom z |
|---|---:|---:|---:|---:|---:|
| S 15-18 | 303.0 (11.9) | 173.0 | 173.0 | 155.8 / 232.0 | 298 |
| M 17.5-20.5 | 366.5 (14.4) | 236.5 | 173.0 | 155.8 / 232.0 | 298 |
| L 20-23 | 430.0 (16.9) = H1 | 300.0 = H1 | 173.0 | 155.8 / 232.0 | 298 |
| H1 15-23 | 430 | 300 | 300 | 155.8 / 359.0 | 176 |

Saving: S 53.7, M 34.4, **L 15.2 g** (legs 26.0 / 13.0 / 0, spine 12.5 / 6.2 / 0, rack strip 8.4, pulley webbing
3 × 127 mm 6.9 g). The L kit can only shorten the rack.

Crown checks (beam model, every rev C case at each size's ends, M also at 19 in):

| kit | legs | top bar | spine | corner peak | ring crush | bearing | buckling | pawl cheek |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| S (15, 18) | 1.149 (C8, 18) | 1.262 | 1.178 | **1.195** (C6p, 15) | 2.12 | 16.0 | 1.884 | 1.41 |
| M (17.5, 19, 20.5) | 1.128 (C8, 20.5) | 2.378 | 1.738 | 1.427 | 2.73 | 20.6 | 1.934 | 2.00 |
| L (20, 23) | 1.116 (= H1) | 2.325 | 1.191 | 1.517 | 3.05 | 23.0 | 1.854 | 2.77 |

**The leg-in-sleeve effect (BL-007).** A shorter leg no longer reaches the bottom of the sleeve, so at the low end
of each size the stay below z 298 carries its bending alone. On the H1 body (one tag per torso, §3.3) the worst
fatigue per kit is S **1.298** (18 in), M **1.225** (20.5 in), L **1.150** (23 in, identical to H1's governing
set); the body minimum is unchanged (1.150 = H1). The kits do not cost fatigue because every size's top setting
reproduces H1's 23 in leg-in-stay geometry, and the low settings carry less crown moment.

**Shortening the printed sleeves as well does cost fatigue and saves little.** The sleeve below z 290 is empty in
every kit. Opening it from Ø18 to Ø20 (z 160-290, outside the z 234 joint and spreader-clip zones, as BL-007 (c))
removes **3.9 g** and drops body fatigue 1.150 -> **1.081** (per-torso basis; 6 %). Not recommended.

### (b) Pinned positions instead of rack and pawl

- **Pin through the carbon leg** (information): with the open-hole factor 0.55 on the leg FPF, a hole fails anywhere
  above **z 413** (C_im3, C8, 15 in), while the pin must sit above the top of the low bushing at the highest setting
  (**z 444**). Usable travel: **0 mm**. It also breaks the "no holes in carbon tubes" rule (geometry.yaml handoff
  notes). Rejected.
- **Index plunger** (Ø5 Ti tip, ASSUMPTION 6 g, in the pawl housing) in a perforated PA66-GF30 strip (holes Ø5 at
  12.7 mm pitch, no holes in carbon), taking the pawl's load path: at the factored 850 N, strip bearing 2.94, strip
  shear-out 4.85, tip bending 4.23. Mass: −2.5 g of strip holes, plunger ≈ pawl + spring (ASSUMPTION 6 g each), and
  it removes the release cord (−4.5 g) because the plunger is pulled at the housing. Resolution 12.7 mm (½ in)
  instead of 4 mm, no adjustment while worn, a loose pin rattles (quiet-pack rule). **The plunger itself saves
  2.5 g**; the 52 g in the chart is the pulley and cord that (b) makes useless. Rejected: (d1) gets the pulley saving
  and keeps the pawl.

### (c) Larger-diameter, thinner-wall legs

Same family [twill ±45 / UD 0 × n / twill ±45] (0.22 mm twill, 0.125 mm UD plies).

| leg | wall / ID, mm | EI / H1 | g/mm | legs FPF | ring crush | corner peak | bore / bushing | body |
|---|---|---:|---:|---:|---:|---:|---|---|
| H1 16 × 8 | 1.44 / 13.12 | 1.00 | 0.1025 | 1.116 | 2.33 | 1.217 | 18.0 / 1 mm | H1 |
| **17 × 7** | 1.315 / 14.37 | 1.10 | 0.1006 | **1.127** | 1.90 | 1.377 | 18.0 / **0.5 mm** | unchanged: fatigue 1.149 (per torso) |
| **17 × 7, bore 19** | same | 1.10 | 0.1006 | **1.127** | 1.90 | 1.377 | **19.0 / 1 mm** | wall 4.41 -> 3.91 mm (A's 3.6 floor kept): **−20.1 g**, fatigue **1.116** per torso, **1.209** recorded basis |
| 17 × 6 (same EI) | 1.19 / 14.62 | 0.97 | 0.0916 | **0.980 fails** | 1.58 | 1.416 | 18.0 / 0.5 | – |
| 18 × 6 (same EI) | 1.19 / 15.62 | 1.17 | 0.0974 | 1.107 | 1.51 | 1.557 | 20.0 / 1 mm | wall 3.41 mm (**below A's 3.6 mm floor**): −38.3 g, fatigue **1.036** per torso |
| 18 × 5 | 1.065 / 15.87 | 1.01 | 0.0877 | **0.937 fails** | 1.22 | 1.613 | 20.0 / 1 mm | – |

- **Same stiffness is not same strength**: at equal EI a larger tube runs a higher strain at the same moment, so
  17 × 6 and 18 × 5 fail the leg FPF. The leg mass itself barely moves (17 × 7: −1.6 g). The saving is in what the
  bigger leg lets the sleeve do.
- **17 × 7 with a 19.0 mm bore** (1 mm bushings as today) is the useful one: −20.8 g in all (body −20.1, legs −1.6,
  bushings +0.8), the leg and corner margins go **up**, and the body keeps A's 3.6 mm bushing-seat floor. The bore is
  reamed after printing anyway: **the H1 print files are used unchanged, reamed to 19.0 instead of 18.0**.
- 17 × 7 with 0.5 mm bushings in the 18.0 bore (−8.3 g, no body change) avoids any fatigue cost but rests on a
  0.5 mm UHMWPE wall surviving wear (ASSUMPTION, §6).
- 18 × 6 / bore 20 (−40.9 g) breaks A's wall floor and leaves body fatigue at 1.036; not recommended while CA-1 is
  open (same reason the owner held BL-007 (c)).

### (d) The 3:1 pulley replaced by a simpler lock

The rack and pawl are already the lock: the rev C model takes the pulley as slack and the pawl as carrying
everything (rack 6.27, pawl cheek 1.40), so removing the pulley changes **no structural check**.

- **(d1) pawl only** (recommended): delete the webbing (1.4 m), the cam buckle and the three guides: **−45.2 g**. Keep
  the release cord and toggle on the left shoulder strap. Lengthen while worn: pull the toggle and shrug (the crown
  is pushed up by 32 N at static carry). Shorten: unweight the pack (or take it off), pull the toggle, push the crown
  down by hand; the pawl drops into the nearest 4 mm tooth.
- **(d2) 1:1 pull-down strap**: 0.45 m of 25 mm webbing from the spine bottom through guide A (lumbar top) to a grab
  tab, keeps shortening while worn: tail pull 44 N standing, 71 N at the 1.6 g walking peak (limit 200 N). −34.4 g.
  Costs 10.8 g over (d1).

### (e) Shorter bushings (found while breaking the block down)

70 -> 50 mm: −4.0 g; ring crush 2.33 -> **1.67**, bearing 12.6, beam loads unchanged (tested); the voxel model spreads
each bushing force over 40 mm whatever its length, so the body is unchanged. Small; not in the recommendation
(it would also cut the sliding length-to-diameter ratio from 3.9 to 2.8; ASSUMPTION that 2.8 does not bind).

## 3. Recommended: (a) three crown kits + (d1) pawl only + (c) 17 × 7 legs in a 19.0 mm bore

### 3.1 Mass (ledger basis, g)

| item | S | M | L |
|---|---:|---:|---:|
| crown legs (OD 17 × 7, cut per size) | −27.1 | −14.4 | −1.6 |
| spine cut per size | −12.5 | −6.2 | 0 |
| rack 300 -> 173 mm (strip part, pa66_gf30 1370 kg/m³) | −8.4 | −8.4 | −8.4 |
| UHMWPE bushings OD 17 + 1 mm wall | +0.8 | +0.8 | +0.8 |
| sleeve bore reamed 18 -> 19 (H1 solid, voxel count) | −20.1 | −20.1 | −20.1 |
| pulley guides | −8.0 | −8.0 | −8.0 |
| pulley webbing 1.4 m, cam buckle (soft goods) | −37.2 | −37.2 | −37.2 |
| **block saving** | **−112.4 (4.0 oz)** | **−93.4 (3.3 oz)** | **−74.4 (2.6 oz)** |
| frame (ledger frame rows), g | 949.9 | 968.9 | 987.9 |
| CORRIE B.2 belt M, g (lb) | 3814.6 (8.41) | 3833.6 (8.45) | 3852.6 (8.49) |

Not counted: hood ladder B-20 shortened (§4), about −2 g on the bag.

### 3.2 Crown checks (beam model, rev C, every case at each kit's settings)

| kit | legs | top bar | spine | corner avg / peak | ring crush | bearing | crown fatigue | buckling | rack | pawl cheek |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| S | 1.161 | 1.270 | 1.178 | 2.58 / 1.353 | 1.72 | 17.1 | 2.72 | 1.892 | 6.27 | 1.42 |
| M | 1.140 | 2.388 | 1.749 | 3.06 / 1.609 | 2.22 | 21.9 | 1.76 | 1.937 | 6.27 | 2.02 |
| L | 1.127 | 2.368 | 1.200 | 3.25 / 1.707 | 2.48 | 24.5 | 1.37 | 1.857 | 6.27 | 2.79 |
| H1 | 1.116 | 1.246 | 1.178 | 2.34 / 1.217 | 2.33 | 17.6 | 1.36 | 1.854 | 6.27 | 1.40 |

Corner-bond fatigue (peak, 1.6 g) 3.46 / 3.91 / 2.54 (H1 2.11).

### 3.3 Body (voxel, 2 mm, H1 solid reamed to 19.0)

| basis | strength | fatigue | creep | buckling | z 234 joint str. / fat. |
|---|---:|---:|---:|---:|---:|
| H1, recorded basis (one tag per couple, torsos 15/19/23) | 1.453 | 1.279 | 2.730 | 1.313 | 1.964 / 1.22 |
| bore 19, recorded basis | 1.450 | **1.209** | 2.578 | 1.315 | – / 1.228 |
| H1, one tag per torso | 1.474 | 1.150 | 2.454 | 1.313 | 1.964 / 1.22 |
| recommended (bore 19, three kits), one tag per torso | 1.491 | **1.116** | 2.381 | 1.315 | – / 1.228 |

Per kit (one tag per torso, worst fatigue): S 1.277, M 1.201, L 1.116; governing set C_im3 static carry, 23 in,
stay sleeve wall (as H1).

**Why two bases.** `frame_comp_d.solve_fields` excludes, per scenario tag, the elements under *every* load patch of
that tag's sets (the FI99 rule's load-patch exclusion). With 15, 19 and 23 in under one tag, the 23 in set is credited
with the exclusion of the 19 in set's bushing band (z ~260-300), which lies in the 23 in hot spot. The kits have
different torso lists, so every variant here, and H1, is also run with one tag per torso (each set excludes only its
own patches). On that basis H1 is **1.150**, not 1.279. Both bases pass; the per-torso basis is the conservative,
like-for-like one. (Found, not fixed: see the report.)

### 3.4 Parts and build steps

Parts out: 3 pulley guides, 1.4 m webbing, cam buckle (−5). Parts changed: legs OD 17 (special order, the same
vendor wrap as today), bushings ID 17 / OD 19, extension-post plug and corner-wrap liner (fit the 14.37 mm leg ID
instead of 13.1 mm), spine and rack cut per size. Printed body: H1 files, unchanged.

1. Print and anneal H1 as released (anneal with a 16 mm rod through each bore, as today).
2. Ream both sleeve bores to **19.0 mm** (was 18.0) over z 160-544.
3. Order OD 17.0 ± 0.1 legs [twill ±45 / UD 0 × 7 / twill ±45], wall 1.315 mm, ID 14.37; cut per size (S 303,
   M 366.5, L 430 mm).
4. Bond the 70 mm UHMWPE bushing (ID 17, wall 1 mm) on each leg end; seat the top bushing in the stay-top collar.
5. Make the extension-post plug and corner-wrap liner for the 14.37 mm ID (sand the plug, never the tube).
6. Cut the spine (S 173, M 236.5, L 300 mm) and the rack (173 mm); bond and screw the rack on as today.
7. Build the crown corners as today (0.8 mm bead bondline, 30 mm wraps; corner coping now for OD 17).
8. Fit the pawl and the release cord + toggle. No pulley.

A wrong size is fixed by fitting another crown kit (legs + top bar + spine + rack, bonded at the corners) on the same
body; the body and harness are common to all sizes.

## 4. Effect on hood ladder B-20 and the harness yoke

- **B-20 hood ladder:** one rung per 0.5 in setting. Today 17 rungs over 250 mm; a kit covers 3 in, so **7 rungs
  (about 94 mm)** per size. About −2.2 g per pack (ASSUMPTION: BL-007's 2.5 g per 360 mm of Hypalon strip; not
  counted above). Hood B-19, guys, B-22 tabs: unchanged. Lifters stay on the top bar at every setting (US 10,952,523
  guardrail unchanged).
- **Harness yoke:** unchanged, at 150 mm down the spine. On the S spine (173 mm) 23 mm of spine remains below the
  yoke; with (d1) the moving pulley guide B at the spine bottom is gone, so nothing else needs that length
  (ASSUMPTION: the yoke clamp extends ≤ 20 mm below its centre; check on the yoke drawing). The release toggle stays
  on the left shoulder strap.

## 5. Fit consequences (plain)

- One printed frame for everyone stays; the crown becomes one of three kits. Within a kit the torso adjusts over
  3 in, continuously in 4 mm steps, exactly as today. The owner decision "one pack adjusts to fit everyone"
  (2026-11-01) narrows to "one frame body, three crown kits".
- With (d1), lengthening still works while the pack is on; shortening needs the pack unweighted. (d2) keeps
  shortening on the body for 10.8 g.

## 6. Assumptions

- ASSUMPTION: the beam-model bushing / pawl stiffnesses (pack5200 defaults) hold for shorter legs and OD 17 legs.
  Test: T1 strain gauges on a leg at z 520 for an S kit at 18 in; pass = leg moment within 15 % of the beam model.
- ASSUMPTION: the pulley carries no load once the pawl is engaged (pack5200 model, carried from rev C). Test: T1 and
  T1(c) with the pulley removed; pass = crown set ≤ 1 mm, no pawl slip.
- ASSUMPTION: masses of the rack (22 g), pawl housing (14 g), guides (8 g), clamp (6 g), cam (12 g), toggle (3 g) as
  booked; rack strip share = 300 × 12 × 4 mm × 1370 kg/m³ = 19.7 g, the rest inserts. Test: weigh on the first build.
- ASSUMPTION: a 1.315 mm, 7-UD OD 17 tube is available as a special-order wrap at OD ± 0.1 mm (same vendors as today's
  OD 16 legs). Test: vendor quote and an incoming OD/ID check.
- ASSUMPTION: reaming the H1 sleeve to 19.0 leaves the voxel wall the model assumes (3.91 mm); the as-printed bore is
  reamed today, so this is the same operation. Test: measure the wall at z 300 and z 520 on the first article.
- ASSUMPTION: the per-torso body basis (§3.3) is the conservative reading of the FI99 exclusion rule.
- ASSUMPTION (c, 0.5 mm bushing option only): a 0.5 mm UHMWPE bushing wall lasts. Test: 10 000-cycle slide-wear
  coupon at the C1 bushing pressure; pass = wall loss < 0.15 mm.
- ASSUMPTION (b): plunger 6 g; Ti pawl + spring 6 g of the 14 g pawl row; PA66-GF30 bearing allowable = conditioned UTS
  125 MPa; shear 67 MPa (geometry.yaml lock basis).
- ASSUMPTION (d2): 0.45 m of strap; guide friction μ 0.10 over 180°.
- ASSUMPTION (e): a 50 mm bushing (L/D 2.8) slides without binding. Test: slide trial loaded at 20 N offset.
- Fatigue rests on PAHT-CF 0.30 at 1e5 (CA-1), as H1. CA-1 flip point (recorded basis): H1 0.234, recommended 0.248.

## 7. Mass reductions that keep the SF (not taken)

| idea | Δ g | condition |
|---|---:|---|
| (e) bushings 70 -> 50 mm | −4.0 (OD 16) | slide trial; ring crush 1.67 |
| 18 × 6 legs in a 20 mm bore instead of 17 × 7 / 19 | −20.1 more | only if CA-1 proves well above 0.30 and A's 3.6 mm floor is waived (fatigue 1.036 per torso) |
| 0.5 mm bushings with 17 × 7 in the 18 bore instead of the 19 bore | +12.5 (lighter option is 19 bore) | no fatigue cost; wear coupon |
| drop the release cord + toggle (adjust pack-off only) | −4.5 | owner: no on-body lengthening |

## 8. Plain-language summary for the owner

You keep the sliding, adjustable crown. Three changes take about **93 g (3.3 oz) off a size-M pack**, 74-112 g
(2.6-4.0 oz) depending on size: (1) instead of one crown that slides 8 inches, make three crown kits (S, M, L) that
each slide 3 inches on the same printed frame, so the legs, spine and rack can be shorter; (2) drop the pulley and cam
buckle, keeping the toothed rack and pawl, which already hold all the load; (3) use a slightly fatter, thinner-walled
carbon leg (17 mm instead of 16 mm) and ream the printed sleeve 1 mm larger. Every strength check still passes, and
the carbon crown margins actually improve. What you give up: one crown no longer fits 15-23 in (you pick a kit, and
can swap it later on the same frame), you can no longer shorten the torso while wearing the pack (lengthening still
works; for 11 g a simple pull strap brings shortening back), and the frame's fatigue reserve drops a little (about 5 %,
much less than the fixed crown in BL-007).
