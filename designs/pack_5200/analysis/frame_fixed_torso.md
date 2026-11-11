# BL-007: a printed-to-size frame without the telescoping crown (study, nothing adopted)

Owner: structural-fea-engineer, 2026-11-11. Ticket: `docs/backlog/BL-007-fixed-torso-frame.md`. Standard: HA-LS-1
rev C ([load_standard.md](load_standard.md)), all 42 sets (27 crown-bar + 15 IM3 couple, torsos 15 / 19 / 23 in).
Baseline: H1 ([frame_h1.md](frame_h1.md)).

- Code: `huntkit/gendesign/frame_fixed.py` (imports `frame_h1`, `frame_comp_d`, `frame_comp_A`,
  `frame_cg_recheck`, `huntkit.fea`, `huntkit.mass.ledger`; nothing is copied). Tests: `tests/test_frame_fixed.py`.
- Results: [frame_fixed_results.json](frame_fixed_results.json). Research:
  [docs/research/fixed_vs_adjustable_frames.md](../../../docs/research/fixed_vs_adjustable_frames.md).
- Run: `python -m huntkit.gendesign.frame_fixed all` (about 15 min on 2 cores; beam models cached in
  `outputs/frame_fixed/`). `sweep` re-runs the printed-leg sweep.
- Figures: `outputs/screens/20261111_BL007_1.png` (Cycles: H1 | (c) | (b) at 19 in),
  `outputs/screens/20261111_BL007_2.png` (mass and governing margins per variant).
- Masses come from the mass ledger (`huntkit.mass.ledger`, config `corrie_b2_h1`, belt M: **3927.0 g**). Imperial
  in brackets.

## 0. Result

| | H1 (telescoping) | (a) fixed crown | (c) fixed + stays re-sized | (b) printed upper frame |
|---|---:|---:|---:|---:|
| frame at 19 in, g (lb) | 1025.1 (2.26) | **979.1 (2.16)** | **964.3 (2.13)** | 1231.5 (2.72) |
| change vs H1, g | 0 | **−46.0** | **−60.8** | **+206.4** |
| frame over 15–23 in, g | 1025.1 | 958.3–999.9 | 943.5–985.1 | 1159.2–1303.7 |
| CORRIE B.2 pack, belt M, 19 in, g (lb) | 3927.0 (8.66) | **3839.3 (8.46)** | **3824.5 (8.43)** | 4091.7 (9.02) |
| pack change vs H1, g (oz) | 0 | **−87.7 (−3.1)** | **−102.5 (−3.6)** | +164.7 (+5.8) |
| body strength / fatigue / creep | 1.45 / 1.28 / 2.73 | 1.64 / **1.08** / 2.31 | 1.59 / **1.04** / 2.21 | 1.59 / **1.04** / 2.22 |
| branch buckling (A rule) | 1.31 | 1.23 | 1.32 | 1.34 |
| z 234 joint strength / fatigue | 1.96 / 1.22 | 1.96 / 1.23 | 1.96 / 1.23 | 1.96 / 1.23 |
| crown-to-stay interface (min) | pawl cheek 1.40 | socket 1.18 (top-shim leg ring crush) | 1.18 | z 544 joint 2.39 fat., corner 1.93 |
| body torsion stiffness vs H1 | 1.00 | 1.00 | 0.97 | 0.97 (body only) |
| print time (h) | 27.0 | 27.0 | 26.5 | 34.4 |
| printed parts / all parts | 2 / ~37 | 2 / ~41 | 2 / ~41 | 4 / ~58 |
| unit cost, qty 1, incl. spreader | ≈ $437 | ≈ $427 | ≈ $425 | ≈ $474 |
| **rev C** | pass | **pass** | **pass** | **pass** |

- **H1 reproduced first** (`h1_reproduce`): same solid, same 42 sets: 757.7 g raster, strength **1.453**, fatigue
  **1.279**, creep 2.730, buckling 1.313, joint 1.964 / 1.22, all equal to `frame_h1_results.json`.
- **Every variant passes every rev C check** (§2–§4). The pack saving of (a) and (c) is about **88–103 g
  (3.1–3.6 oz)**, of which 41.7 g is the pulley webbing, cam buckle and release cord (ledger torso-adjust row).
- **The cost is fatigue reserve.** Body fatigue falls from 1.28 to 1.08 (a) and 1.04 (c). The CA-1 flip point
  (coupon fatigue ratio below which the body fails) moves from 0.234 to **0.277 (a)** and **0.289 (c)**, against
  the 0.30 record: a 4–8 % shortfall in CA-1 would fail (c). H1's own reserve was 22 %.
- **Re-sizing the stays (c) buys only 14.8 g** on top of (a). The sleeve walls are not dead weight: without the leg
  inside the stay, the stay carries all the bending below the socket (§2.2).
- **(b) printed upper frame does not pay**: +206 g at 19 in, because a PAHT-CF leg has to be OD 34 × 3.5 mm to
  match the 16 mm carbon leg in fatigue, and the carbon corner wrap has to be replaced by a printed socket plus a
  7075 bar-end plug.

## 1. Variants and method

**Common to (a), (b), (c)** (owner-frozen features kept): crown top bar and spine tube kept; lifters stay on the top
bar at every size (US 10,952,523 guardrail unchanged: nothing moves to the posts); the spine passes the old pawl
housing, which becomes a **lateral spine guide** (the pawl detail with its 304 bushings, slotted along the spine so
it takes no axial load). The rack, pawl, three pulley guides, webbing, cam buckle and release cord are deleted. The
torso is set by printing / cutting per unit; fine adjust is at the yoke (§5).

| variant | crown-to-stay connection | body |
|---|---|---|
| **(a) fixed crown** | each carbon leg cut to the unit length, seated only in the top 149 mm of the stay (**socket z 395–544**): UHMWPE shim 40 mm at z 400–440, shim 60 mm at z 484–544, **2 Ti M5 × 30 cross-bolts per leg at z 445** (reamed 5.1 through socket and leg, 90° apart in plan) | H1 body unchanged (same print files) |
| **(c) = (a) + re-size** | as (a) | below the socket the sleeve keep-out and the pulley pads are released; the empty channel is opened from Ø18 to **Ø20** (wall ≥ 3.4 mm, never adding material outside H1's stay); z 234 joint and spreader-clip seats pinned to H1; H1's push continued 5 iterates on the fixed-crown sets, same accept rule (≥ 1.02, buckling ≥ 1.0) |
| **(b) printed upper frame** | PAHT-CF legs OD 34 × 3.5 printed per size, bolted to the stay top at z 544 with the H1 joint method (4 Ti M5 × 45 in bosses per leg, dry face, no preload credit, prying 1.25); printed corner sockets (80 mm) on the carbon top bar with a 7075 tube bonded inside each bar end and 2 Ti M5 cross-bolts | (c) body |

**Load path (re-solved, not assumed).** The rev C beam model of `frame.yaml` was rebuilt for each variant
(`modify_model`): the leg bottom node moves into the socket (z 420), the two leg links become shim links (radial)
with the axial stiffness at the cross-bolts, and the spine guide loses its axial stiffness. All 42 sets were solved
again (`beam_runs`, buckling eigenvalues on the crown-bar sets); the new interface loads were applied to the 2 mm
voxel body with D's solver and the release FI99 rule. For (b) the legs are PAHT-CF tubes in the beam model, and
buckling is re-solved with the printed-leg E × 0.6 hot × 0.7 creep (A's rule).

**Bed (b).** H2S bed 340 × 320 mm, 340 tall: the body stays two halves (0–234, 234–544); each leg (82–235 mm plus
the socket) is a separate print. **4 printed segments, 3 joints** (z 234, and z 544 on each leg) plus two bolted
corners.

**Socket sizing found during the study.** A 94 mm socket with two 25 mm shims fails **leg ring crush 0.42**
(C8 hipbelt-off, IM3, 15 in); 40 + 40 mm shims over 149 mm still give 0.92; the 60 mm top shim gives 1.18. The
shim couple forces are scaled by 1.17 because the beam link sits at z 530 and the top-shim centre at z 514
(`LEVER_CORR`, conservative).

## 2. Body rev C results (voxel, 2 mm, both couple variants)

### 2.1 Margins per torso (strength / fatigue / creep)

| variant | crown bar 15 | crown bar 19 | crown bar 23 | IM3 15 | IM3 19 | IM3 23 |
|---|---|---|---|---|---|---|
| H1 | 1.45 / 1.61 / 3.44 | 2.15 / 1.71 / 3.64 | 2.17 / 1.77 / 3.77 | 1.47 / 1.52 / 3.25 | 2.10 / 1.47 / 3.14 | 2.14 / **1.28** / 2.73 |
| (a) | 1.64 / 1.42 / 3.03 | 2.40 / 1.49 / 3.18 | 2.11 / 1.53 / 3.27 | 1.67 / 1.35 / 2.87 | 2.22 / 1.25 / 2.66 | 1.93 / **1.08** / 2.31 |
| (c) | 1.60 / 1.41 / 3.01 | 2.31 / 1.48 / 3.16 | 1.98 / 1.53 / 3.26 | 1.62 / 1.34 / 2.85 | 2.16 / 1.22 / 2.59 | 1.84 / **1.04** / 2.21 |
| (b) | 1.59 / 1.41 / 3.01 | 2.30 / 1.48 / 3.16 | 1.98 / 1.53 / 3.26 | 1.61 / 1.33 / 2.84 | 2.15 / 1.22 / 2.60 | 1.85 / **1.04** / 2.22 |

Per case (min over torsos and both couples, margin = SF / requirement):

| case | H1 | (a) | (c) | (b) |
|---|---:|---:|---:|---:|
| C1 static carry | 3.41 | 2.89 | 2.77 | 2.77 |
| C2 drop 2.5 g | 2.28 | 1.93 | 1.84 | 1.85 |
| C3 side-hill torsion | 2.05 | 2.14 | 2.05 | 2.04 |
| C4 single-stay set-down | 2.43 | 2.87 | 2.81 | 2.80 |
| C5 meat straps | 2.48 | 2.11 | 1.98 | 1.98 |
| C6 tall load / C6p posts | 3.40 | 2.98 / 2.84 | 2.96 / 2.82 | 2.96 / 2.82 |
| C7 overload haul | 3.48 | 2.97 | 2.78 | 2.79 |
| C8 hipbelt-off | **1.45** | **1.64** | **1.59** | **1.59** |
| fatigue (C1 at 1.6 g, PAHT 0.30) | 1.28 | **1.08** | **1.04** | **1.04** |
| creep-rupture (C1 1 g, 40 °C) | 2.73 | 2.31 | 2.21 | 2.22 |
| branch buckling, A rule (lower L / upper L / upper R) | 1.48 / 5.3 / 1.31 | **1.23** / 2.35 / 4.44 | **1.32** / 2.68 / 3.45 | **1.34** / 2.80 / 3.36 |

### 2.2 What moved and why

- **Strength improves** (1.45 → 1.64 / 1.59): C8 governed at the upper bar / pawl housing, which carried the crown's
  850 N axial load. With the axial load taken at the leg cross-bolts, the upper bar centre sees only the lateral
  spine-guide force.
- **Fatigue falls** (1.28 → 1.08 / 1.04): the C1 hot spot is now the stay wall in and just below the socket
  (z 260–440, IM3 couple, 23 in). In H1 the 430 mm leg spans the stay between two bushings and carries part of the
  stay bending; a short socket puts the whole leg moment into 149 mm of stay and leaves the stay below it to carry
  the bending alone.
- **Why (c) is only 14.8 g lighter.** Push on the H1 Ø18 channel: −1.1 g in 3 iterates (the free wall was about
  1 mm outside a 2.5 mm floor; log `outputs/frame_fixed/push_c_bore18.log`). Channel opened to Ø22 (2.4 mm wall):
  fatigue **1.00**, below the 1.02 accept reserve (rejected; files in `outputs/frame_fixed/try_r11/`). Channel Ø20
  (3.4 mm wall), chosen: −14.8 g, fatigue 1.04 at the lightest passing iterate (it 1). Iterate 5 is 0.15 g heavier
  at fatigue **1.09**; a release should take it (`push_c.json`).
- Keep-outs ((a), (c), (b)): socket walls and pawl/guide housing present 100 %, socket bores and spine channel empty
  100 %, fairleads 100 %, pivot 100 %, 0 voxels outside the envelope, **spreader-clip sections identical to H1**
  (the first (c) run grew 560 voxels onto the clip seats; they are now pinned to H1).

### 2.3 Member masses (printed body families, A grouping, g)

| family | H1 = (a) | (c), (b) body |
|---|---:|---:|
| foot | 7.8 | 7.8 |
| stay below the old sleeve | 113.3 | 112.8 |
| sleeve region (stay z 160–544, bosses) | 262.7 | 251.7 |
| top / upper bar / guide housing | 195.2 | 192.5 |
| branch | 70.2 | 70.2 |
| strut | 87.9 | 87.7 |
| mid bar | 20.7 | 20.2 |

## 3. Crown and interface checks (beam model, re-solved)

Margin = SF / requirement, worst of 42 sets; "C" = couple on the crown bar, "IM3" = couple on the IM3 hooks.

| check | H1 (rev C record) C / IM3 | (a), (c) C / IM3 | (b) C / IM3 |
|---|---|---|---|
| crown legs FPF | 1.39 / 1.12 | 1.41 / 1.13 | printed: 1.82 / **1.54** |
| printed legs fatigue / creep (PAHT 0.30 / 0.40) | – | – | 4.84 / **1.16**; 10.3 / 2.48 |
| top bar FPF | 1.38 / 1.25 | 1.35 / 1.24 | 1.34 / 1.23 |
| spine FPF | 1.18 / 1.18 | 1.18 / **1.15** | 1.17 / **1.13** |
| corner bond average / Volkersen peak | 2.34 / 1.22 (C), 4.33 / 1.76 (IM3) | 2.21 / **1.12**, 3.18 / **1.10** | n/a (printed corner) |
| crown member fatigue (FI ≤ 0.5 at 1.6 g) | 3.27 / 1.36 | 3.23 / 1.36 | 3.23 / 1.91 |
| frame buckling (≥ 1.5 × factor) | 1.85 | 1.84 | 1.82 (legs at E × 0.42) |
| pawl cheek / spine guide (304 bushing, 1/FI99) | 1.40 / 1.41 | 1.53 / 1.54 | 1.52 / 1.53 |
| rack / cam hold | 6.27 / 67 | deleted | deleted |

Fixed-crown socket ((a), (c); `socket_checks`):

| check | strength C / IM3 | fatigue at 1.6 g C / IM3 |
|---|---|---|
| leg ring crush under the 60 mm top shim (CFRP FPF, 60° contact) | 1.38 / **1.18** | 6.29 / 2.07 (FI ≤ 0.5) |
| leg ring crush under the 40 mm low shim | 2.06 / 1.65 | 8.71 / 2.00 |
| leg at the cross-bolt hole (FPF × 0.55 open hole) | 2.22 / 1.78 | 9.51 / 2.17 |
| cross-bolt Ti double shear / leg pin bearing / socket bearing / shear-out | 67.7 / 16.3 / 14.6 / 46.7 | ≥ 69 |
| printed bore bearing under the shims (across layers) | ≥ 15.9 | ≥ 16.2 |
| UHMWPE shim bearing | 8.14 / 6.93 | |

(The pack5200 leg-ring row in the results JSON, 1.08 / 0.92, assumes both shims are 40 mm; it is kept as info
and superseded by the 60 mm top-shim row above.)

(b) only:

| check | strength | fatigue at 1.6 g |
|---|---:|---:|
| printed leg sweep OD × t (min of strength, fatigue, creep, buckling) | 30 × 4: fatigue **0.95 fails**; 32 × 4: 1.10; **34 × 3.5: 1.16 (lightest passing, 0.356 g/mm)**; 34 × 4: 1.27; 38 × 3.5: 1.49 | |
| z 544 leg joint: washer bearing / plug shear / Ti tension / boss bending / contact / hole bearing | 3.03 / 4.03 / 4.14 / 3.73 / 6.22 / 20.9 | 2.39 / – / 3.88 / 2.93 |
| corner socket: bare top bar ring crush (no plug) | **0.43 fails** (info: why the plug is needed) | |
| corner socket with the 7075 plug: bar ring / plug ring / bar pin bearing / bore bearing | **1.93** / 6.28 / 2.03 / 12.4 | |

## 4. Mass, print, parts, cost (19 in unit; ledger basis)

| item, g | (a) | (c) | (b) |
|---|---:|---:|---:|
| printed body (ledger H1 row 757.7, raster change applied) | 757.7 | 742.9 | 742.9 |
| crown, rack, pawl, bushings, Ti mount, inserts, crown fix (ledger rows) | 239.4 | 239.4 | 239.4 |
| z 234 joint parts (ledger rows) | 28.0 | 28.0 | 28.0 |
| carbon legs (beam-model rev C leg 0.1025 g/mm) | −26.1 (2 × 303 mm, not 430) | −26.1 | −88.1 (removed) |
| rack + pawl + pulley guides (`frame.yaml` mass_g) | −44.0 | −44.0 | −44.0 |
| UHMWPE bushings 4 × 70 mm → shims 2 × (40 + 60) mm | −4.8 | −4.8 | −16.7 |
| cross-bolts 4 Ti M5 × 30 + A2 nuts + washers | +20.9 | +20.9 | – |
| yoke fine-adjust strip + pin (ASSUMPTION) | +8.0 | +8.0 | +8.0 |
| corner bondlines (crown fix line) | – | – | −2.2 |
| printed legs OD 34 × 3.5, 2 × 159 mm | – | – | +112.8 |
| printed corner sockets (ASSUMPTION OD 30 × 80 + gusset) | – | – | +83.8 |
| 7075 bar-end plugs 15.8 × 2 × 80 | – | – | +39.0 |
| z 544 bosses / 8 Ti M5 × 45 + nuts + washers / corner 4 Ti M5 × 30 | – | – | +54.6 / +56.0 / +18.0 |
| **frame** | **979.1** | **964.3** | **1231.5** |
| torso-adjust soft goods (ledger row, pack side) | −41.7 | −41.7 | −41.7 |
| **CORRIE B.2 belt M** | **3839.3 (8.46 lb)** | **3824.5 (8.43 lb)** | **4091.7 (9.02 lb)** |

Per size (frame g, pack g): (c) 16 in 948.7 / 3808.9; 18 in 959.1 / 3819.3; 20 in 969.5 / 3829.7; 22 in 979.9 /
3840.1. (a) is 14.8 g heavier at every size. The leg length is the only size-dependent item (5.2 g per 0.5 in).

Print: (a) 27.0 h (same files as H1); (c) 26.5 h (749 g print, scaled from H1's 764.5 g / 27 h); (b) 34.4 h.
Parts: (a) and (c) lose the rack, pawl, spring, 3 guides, webbing, cam buckle, cord and toggle, 4 bushings, and gain
4 shims, 4 cross-bolts + nuts + washers and the yoke strip: about the same count, **fewer moving parts and no field
adjustment**. (b) adds 2 printed legs, 8 joint bolts and 16 washers, 4 corner bolts and 2 bonded plugs.

Build steps ((a), (c)): print and anneal as H1; bolt z 234; ream the socket 18.0 over z 395–544 only (no ream-through
over the whole stay: the ream through both halves at the joint is no longer needed); cut legs from the size table;
bond the shims; build the crown corners as today; insert legs and drill + ream 5.1 through socket and leg on a jig;
fit cross-bolts; set the yoke strip. (b): four prints, anneal four, bolt three joints, bond the bar-end plugs, drill
and bolt the corners.

Cost, qty 1, as deltas from H1's ≈ $437 (`cost_usd`): (a) ≈ **$427**, (c) ≈ **$425** (−$21 rack, pawl, pulley,
cam; −$9 shorter legs; +$19 cross-bolts at A's $4.50; +$2 strip); (b) ≈ **$474** (+$58 bolts, +$28 filament and
machine).

## 5. Fit consequences (plain)

- **Fine adjust left:** ±25 mm (±1.0 in) at the yoke, by re-pinning the yoke on a 60 mm toothed strip on the spine.
  It is set at fitting, not on the trail. Today the crown moves 203 mm, continuously, while worn.
- **Sizes for 15–23 in:** **4** printed sizes at ±1 in: 15–17, 17–19, 19–21, 21–23 in (nominal 16 / 18 / 20 / 22).
  This matches the leaders: KUIU sells 3 frame heights with 4 in of strap travel; Kifaru 22 / 24 / 26 in frames;
  Exo two frames with a 1.5 in extension; none adjusts frame height while worn (research §2). Carbon leg cut lengths:
  226 / 277 / 328 / 379 mm (along the axis, from the socket bottom).
- **If the size is wrong:** for (a) / (c) the body is the same at every size (one print file): the fix is **a new
  pair of carbon legs (about $9 of tube) and re-drilling the cross-bolt holes**, about 1 h for the owner, if the
  wrong size is caught before the bolts are drilled through the socket. A second drilling of the same socket is not
  analysed (ASSUMPTION: drill the second pair at 90° to the first; check before it is relied on). For (b) a wrong
  size is two new leg prints (≈ 6 h).
- **Torso changes later** (layers, a second owner, resale): ±1 in at the yoke, then new legs. No published resale
  data was found (research §2.5).
- **Bag attachment:** the hood ladder **B-20 shrinks to one rung per size**: its 17 rungs (one per crown setting)
  are not needed because the bar does not move on a given unit. Cut a 3-rung strip of about 70 mm, or keep the 17-rung
  strip as the size-agnostic part (about −2.5 g if cut, ASSUMPTION). Hood B-19, guys, B-22 tabs, lifters on the
  bar: unchanged. The spreader and its clips are unchanged (clip seats identical to H1).
- **The owner decision "universal fit: one pack adjusts to fit everyone" (2026-11-01) is given up** for a sized
  frame with fine adjust. This is the main thing the owner trades.

## 6. Assumptions

- ASSUMPTION: shim and bolt link stiffness 2 × 10⁴ / 5 × 10⁴ N/mm (pack5200 bushing and pawl defaults). Test: T1 with
  strain gauges on a leg at z 520 and on the stay at z 380; pass = measured leg moment within 15 % of the beam model.
- ASSUMPTION: the spine guide takes no axial load (slotted). Test: T1(c) hipbelt-off with a dial on the spine at the
  guide; slot must not bottom.
- ASSUMPTION: UD-rich leg wall pin bearing 300 MPa × 0.8 hot/wet (team C A1) and open-hole factor 0.55 at the
  cross-bolt. Test: RC-2-style pin-bearing coupon on the actual leg tube, and an open-hole bend coupon.
- ASSUMPTION: shim couple forces scaled by 1.17 for the 16 mm offset between the beam node (z 530) and the top-shim
  centre (z 514). Test: none needed (conservative); re-solve with a z 514 node if a release is made.
- ASSUMPTION: ±25.4 mm fine adjust is enough per size (half of KUIU's published 4 in). Test: fit 6 wearers at both
  ends of each size on the T9 rig with 30 lb; pass = lifters 30–60°, belt on the iliac crest at both ends.
- ASSUMPTION: the checked crown heights (601 / 703 / 804 mm) bracket every size, and moving the yoke ±25 mm on the
  spine changes the spine margin (1.13–1.15) by less than its reserve. Test: re-run `beam_runs` with the yoke node at
  SP125 and SP175.
- ASSUMPTION: yoke strip + pin 8 g, $2; rack + pawl + guides $6; webbing + cam + cord + toggle $15; Ti M5 $4.50 (A).
- ASSUMPTION (b): corner socket OD 30 × 80 + 4 g gusset; 7075 plug 15.8 × 2 × 80 bonded; z 544 bosses 4 × r 8 ×
  16 mm on each side. Test: none (b is not recommended).
- ASSUMPTION: printed leg (b) checked with the leg axis in the layers, torsion and transverse shear as interlayer
  shear (conservative).
- ASSUMPTION: H1's accept rule and push settings (reserve 1.02, cap 0.45, u_lo 0.85); voxel noise reserve 2 %.
- Fatigue at the socket rests on PAHT-CF 0.30 at 1e5 (CA-1). Flip points: (a) 0.277, (c) 0.289 (H1 0.234).
- Exported render meshes drop islands below 5 cm³ (`clean_mesh`): the released `h1_assembled.stl` carries 4 slivers
  and `h1_lower_flat.stl` a 0.57 cm³ island + 3 slivers (BL-015). The print files are not changed.

## 7. Mass reductions that keep the SF (not taken)

| idea | Δ g | condition |
|---|---:|---|
| spine shortened per size (yoke − 50 mm to the top bar) | −5 to −11 | 15–19 in sizes; spine guide must still reach z 520 |
| A2 cross-bolt nuts and washers to Ti | −2 | cost |
| take push iterate 5 for (c) instead of 1 | +0.15 | fatigue 1.04 → 1.09: recommended |
| CA-1 proves 0.40 | then (c) fatigue ≈ 1.39 | the channel could open further (Ø22 gave 1.00 at 0.30) |

## 8. Plain-language trade-off for the owner

Printing the torso length into each frame and dropping the sliding crown saves about **90–100 g (3–3.5 oz)** on the
whole pack: 46 g on the frame with the same printed body (a), 61 g if the stays are also thinned (c), plus 42 g of
pulley webbing and cam buckle. It passes every rev C check, is slightly cheaper (about $10) and has fewer moving
parts. What you give up is the on-body, continuous 8 in torso adjustment you asked for on 2026-11-01 ("one pack fits
everyone"). Instead you would build in 4 sizes (15–17, 17–19, 19–21, 21–23 in) with ±1 in of fine adjustment at the
yoke, which is how KUIU, Kifaru, Exo and Stone Glacier sell their frames. If a size is wrong, you cut and fit a new
pair of carbon legs (about $9, an hour). The engineering price is fatigue reserve: the frame's fatigue margin drops
from 1.28 to 1.04–1.08, so the CA-1 coupon must come in within 4–8 % of the assumed value instead of 22 %. Printing the
upper frame in plastic as well (b) is a bad trade: +206 g and $37 more. If you want the saving, choose (a) first
(same print files as H1, decide after CA-1), and (c) only once CA-1 has passed.
