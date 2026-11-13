# Crown top bar wall under the guy / crown-strap loops (review Y-4), CORRIE F rev 3

structural-fea-engineer, 2026-11-13. Code: `huntkit/gendesign/crown_tube_guy_loop.py`
(`python -m huntkit.gendesign.crown_tube_guy_loop`). Tests: `tests/test_crown_tube_guy_loop.py` (9 pass).
Results: `crown_tube_guy_loop.json`. Screen: `outputs/screens/20261113_crowntube_1.png`.

## Verdict

- **Review Y-4 is right.** On the repo's own ring rule (basis A below), the bare OD 18 bar under today's 25 mm
  B-25 sleeve fails:
  - the guy + crown-strap envelope (323 N): **SF 0.90 static, 0.85 fatigue**;
  - kit L alone: 0.93 static, 0.89 fatigue;
  - kit M passes by a thin margin (1.02 / 1.02). Kit S passes (1.13 / 1.13).
- **TL-1 at 432 N would likely mark or crack the bare bar.** Basis A puts the bar's pristine, room-temperature
  capacity under a 25 mm loop at **454 N**, and the corrected proof load is 494 N.
- **Recommended fix:** make the **B-25 bridle from 38 mm webbing**, with the sleeve shifted inboard to x 26.5–64.5.
  It adds **+3.4 g (0.12 oz)**, is a bag-side part, and needs no frame change.
  - Basis A with this fix: **SF 1.36 static, 1.27 fatigue**.
  - Pristine capacity rises to 671 N, so a 494 N TL-1 should pass.
- **Lightest fix on paper:** add one UD 90° ply inside the bar wall, **+2.1 g**. It is a frame (vendor wrap) change
  and has the thinnest margin (fatigue 1.06), so it is offered as the alternative.
- **TL-1 must be re-specified:**
  - proof load **494 N (50.4 kg / 111 lb)**;
  - specimen = the real rev C bar stock carrying the as-built 38 mm B-25 sleeve, with both toggles in the tab;
  - the fixture reacts the load by beam action;
  - a crush / ovalisation pass criterion (section 6);
  - add **TL-1b**, one bare-bar step test, to measure which ring model is real.
- The physically better ring models put today's bar at **SF 1.22 (basis B)** and **8.6 (basis C)**. The bar is
  probably fine in reality. HA-LS-1, however, credits a spread contact only after a passing coupon, and TL-1b is
  that coupon.

## 1. What bears on the crown top bar (rev 3)

| loop | on the bar | width | load path | checked |
|---|---|---|---|---|
| B-25 bridle sleeves | sewn round the bare bar at x ±52 (band x 39.5–64.5), `corrie_f.guy_bridle` | 25 mm | everything below enters the bar here | yes |
| port guy TG (B-25 tab → B-27 port → B-22 inside) | toggle in the B-25 tab | via the sleeve | aft, into the bag | yes |
| B-28 crown strap | toggle in a second fold of the **same** B-25 tab | via the sleeve | up the frame face | yes, alone and with the guy |
| GBL "guy bar loop" 25 × 170 mm | round the bar (BL-004 REC), still in the rev 3 cut list / op 7.19 / load table at 244 N | 25 mm | rev 1+ toggles the guy into B-25, not GBL | same numbers as the 25 mm sleeve: **fails like it if it carries a guy**. See section 8 |
| load lifters | lugs on the crown-corner **wraps** at x ±105 (`build_geometry.LIFTER_X`, node loads) | – | not a webbing loop on the bare bar | **not applicable** |

**Bar:** every crown kit (S 15–18, M 17.5–20.5, L 20–23 in) uses the same bar, `frame.yaml frame.top_bar_section`.
This is asserted by `kit_sections()` at both ends of every kit.

- OD 18 mm, wall 1.065 mm, `[±45 twill / UD 0 ×5 / ±45 twill]`;
- 230 mm centreline, 214 mm cut, **18.8 g** (0.66 oz) by CLT area × density (the frame ledger books 20.0 g);
- hoop properties: D22 2953 N·mm, A22 20 724 N/mm;
- `crown_diet` cuts only the legs, spine and rack per size.

Masses of the load-path members on this path:

| member | mass |
|---|---|
| top bar | 18.8 g |
| B-25 bridle | 7.43 g (412.5 mm of 25 mm webbing) |
| TG port guys | 500 mm each (cut list) |
| B-28 crown straps | per kit (`crown_kit_straps`) |

## 2. Loads (current, factored)

Source: `corrie_f.bl029_table()`, the rev 3 fine sims (over_port). These give the port guy and crown strap 1 g forces
from the same run, so each pair is concurrent:

| torso | guy at 1 g (fill / meat) | crown strap at 1 g |
|---|---|---|
| 15 in | 51.3 / 33.7 N | 11.6 N |
| 19 in | 74.5 / 54.9 N | 7.0 N |
| 23 in | 95.8 / 68.3 N | 6.8 N |

Envelope inputs: `corrie_f.GUY_1G_MAX_N` 96 N, crown strap 1 g max 11.6 N, hand cinch 80 N (`CROWN_PRE_N`).

Load combinations on **one B-25 sleeve**:
- C5 stumble: 1 g × 3.0;
- C1 static with the hand cinch: guy × 2.0 + cinch × 1.5;
- fatigue: 1.6 × (guy + crown strap).

| | guy 1 g | crown 1 g | guy alone ×3 | **guy + crown, ×3** | guy ×2 + cinch ×1.5 | **governing static** | vector sum ×3 | fatigue peak (1.6 g) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| kit S (18 in) | 68.7 | 11.6 | 206 | 241 | 257 | **257 N** | 209 | 128.5 N |
| kit M (20.5 in) | 82.5 | 7.0 | 248 | 269 | 285 | **285 N** | 248 | 143.2 N |
| kit L (23 in) | 95.8 | 6.8 | 287 | 308 | 312 | **312 N** | 288 | 164.2 N |
| **envelope** | 96.0 | 11.6 | 288 | **323** | 312 | **323 N (72.6 lbf)** | 290 | **172.2 N** |

- The crown strap's own "288 N envelope" applies to the case where the crown strap holds the top alone with the guy
  off. That load equals the guy-alone value, so it never governs.
- ASSUMPTION: LOAD_INTERP. The guy force varies linearly with torso between the 15 / 19 / 23 in sims, and each kit
  is checked at its tallest setting. The crown strap takes the larger of the two bracketing sims.
- ASSUMPTION: COLLINEAR. Guy and crown-strap forces are added as scalars. In the sims they are about 90° apart (guy
  aft, strap up the frame face), so the vector sum is about 10 % lower.
- ASSUMPTION: CINCH. The 80 N hand cinch × 1.5 is combined with the guy at the C1 static factor, because the cinch
  is applied with the pack at rest.

## 3. Method: three ring models, verified

The wall under a loop is checked as a ring slice as wide as the bearing.
- Running loads N(θ)/w and M(θ)/w go into CLT first-ply failure (Tsai-Wu) of the bar laminate, **with the HA-LS-1
  knockdowns** (hot/wet 0.8, impact 0.65 on compression).
- The bar's own bending at the sleeve and its beam shear flow are added at every angle with the worse sign. Both
  guys pull, the bar is taken as fixed-fixed between the corners (M = P a²/L, a = 63 mm), and the spine support is
  ignored (ASSUMPTION: BAR_BENDING). These terms take about 1.5 % off the capacity (295 → 291 N).
- Requirement: SF ≥ 1.0 on the factored load (HA-LS-1: the factor is in the load), and FI ≤ 0.5 at the 1.6 g peak
  (fatigue).

| basis | model | peak ring moment | status |
|---|---|---|---|
| **A (design)** | Roark point-load ring, M = 0.318 F Rm / w, N = −F/2w at the same point. **Identical to `frame_cg_recheck.bar_local`** (reproduced to 1e-9: 295.0 N at 25 mm, rev C wall; 228 N on the rev B wall) | 0.318 F R | HA-LS-1 ring rule (load_standard.md §4, "Crown bushings"): point-load ring; spread contact credited only with a passing coupon |
| B | concentrated strap load reacted by the bar's **beam shear flow** q = F sin θ/(πR), the real reaction. No spreading credit | 0.239 F R | creditable after TL-1b |
| C | strap wrapped over 180°, uniform pressure, same shear-flow reaction | 0.015 F R | creditable after TL-1b (ASSUMPTION: WRAP_UNIFORM) |

**Solver verification** (`tests/test_crown_tube_guy_loop.py`). The Fourier ring solution
`ring_fourier` (an extension of `huntkit.fea.rings` to tangential loads) and an independent 360-element ring on
`huntkit.fea.frame` were both checked:

| check | closed form | Fourier | FE |
|---|---:|---:|---:|
| Roark case 1, M under the load / F R | 0.3183 | 0.3180 | 0.3139 (element-averaged) |
| Roark case 1, M at 90° | 0.1817 | 0.1817 | – |
| Roark case 1, N at 90° / F | −0.500 | −0.500 | – |
| Roark case 1, ΔD = 0.1488 F R³/EI (F 100 N, 25 mm) | 0.1224 mm | – | 0.1236 mm |
| Bruhn ring frame, point load on shear flow, M / F R | 0.2387 | 0.2385 | 0.2350 |
| 180° wrap on shear flow, M / F R | – | 0.0146 | 0.0154 |

FE support reactions are below 0.003 N for 100 N applied, so the loads balance.

## 4. Re-run of the wall check: today's 25 mm sleeve, rev C bar

| | basis A capacity (knocked down / pristine RT) | static SF (≥ 1.0) | fatigue SF (FI 0.5 / FI@1.6 g) | B static / fatigue | C static / fatigue |
|---|---|---:|---:|---|---|
| kit S | 291 / 454 N | **1.13** | **1.13** | 1.52 / 1.53 | 10.8 / 10.8 |
| kit M | 291 / 454 N | **1.02** | **1.02** | 1.38 / 1.37 | 9.7 / 9.7 |
| kit L | 291 / 454 N | **0.93** | **0.89** | 1.26 / 1.19 | 8.9 / 8.4 |
| **envelope** | 291 / 454 N | **0.90** | **0.85** | 1.22 / 1.14 | 8.6 / 8.0 |

- The guy alone at 288 N gives basis-A SF 1.01. This is the review's "about 1.0", and the old register's 1.21 rests
  on the stale 244 N.
- Fatigue fails even for the guy alone: 1.6 × 96 = 154 N gives FI 0.53.
- The `corrie_f_body.md` 13.5 line "288 N against 312 N, strength 1.36" is the bar **bending** check, not this
  ring check.

## 5. Fixes (basis A, envelope 323 N static, 172 N fatigue peak)

| option | bearing | capacity (kd / RT) | static SF | fatigue SF | Δ mass per pack | where | verdict |
|---|---:|---|---:|---:|---:|---|---|
| today, 25 mm B-25 sleeve | 25 | 291 / 454 N | 0.90 | 0.85 | 0 | – | **fail** |
| **B-25 in 38 mm webbing**, sleeve x 26.5–64.5 | 38 | 439 / 671 N | **1.36** | **1.27** | **+3.39 g** | bag side (frame-fitted bridle) | **pass, recommended** |
| B-25 in 50 mm webbing | 50 | 573 / 861 N | 1.77 | 1.66 | +6.35 g | bag side | does not fit: sleeve reaches x 14.5, 0.5 mm into the spine clamp |
| HDPE liner 1.6 × 40 mm under the 25 mm sleeve | 28.2 | 328 / 508 N | 1.02 | 0.95 | +7.53 g | frame | fail |
| printed PA12-CF collar 2 × 40 mm | 40 | 461 / 703 N | 1.43 | 1.34 | +10.76 g | frame | pass, heavy; also needs a PAHT creep / fatigue check |
| **bar + 1 UD 90° ply inside** (wall 1.19) | 25 | 366 / 623 N | 1.13 | 1.06 | **+2.09 g** | frame, every kit | pass, **lightest**; thin margin |
| bar + 1 twill 0/90 inside (wall 1.285) | 25 | 417 / 720 N | 1.29 | 1.21 | +3.46 g | frame | pass |
| bar + 2 UD 90° plies `[±45/90/0×5/90/±45]` (wall 1.315) | 25 | 734 / 1285 N | 2.27 | 2.13 | +4.15 g | frame | pass, most margin |

**Why the 38 mm B-25 and not the +2.1 g ply:**
- **Gate:** TL-1 is a bag-cut gate. The bridle is a sewn part on the current release path and needs no frame
  re-release.
- **Margin:** 1.27 against 1.06 in fatigue.
- **Testability:** TL-1 tests the 38 mm sleeve directly as built.
- **Cost of the difference:** 1.3 g.

The ply fixes are exact CLT and need no new assumption. If the crown bar is ordered again anyway (for example after
TL-1b), the 2-ply hoop wall (+4.15 g) is the robust frame-side answer, and with it the bridle can go back to 25 mm
(−3.4 g, net +0.8 g).

**38 mm B-25 geometry:**
- The outboard edge stays at x 64.5, 4.5 mm from the corner-wrap scarf at x 69. The sleeve runs inboard to x 26.5,
  11.5 mm from the spine clamp (≥ 10 mm, `MIN_CLEAR_MM`).
- The tabs sit on the sleeve. Pack-designer to decide whether the toggle tab stays at x 52 or moves to the sleeve
  centre (x 45.5, a 6.5 mm shift of the guy and crown-strap line at the bar; the B-27 port slit and the 30 mm lid
  channels absorb it).
- One piece as today: 387 mm of poly_webbing_38mm, **10.82 g** against 7.43 g.
- ASSUMPTION: WIDE_SLEEVE. The 25 mm tab pull spreads over the full 38 mm sleeve. TL-1 proves it on the as-built
  part.

Per kit: S passes today and M passes by a thin margin. A single bridle part for every kit is simpler and is
recommended. If the owner wants the gram, kit S could keep 25 mm.

## 6. TL-1: correct proof load and pass criteria

**Proof load: 494 N (50.4 kg on the scale, 111 lbf).** It is the larger of two rules:
- **Sewn / hardware rule:** 1.5 × the factored envelope = 1.5 × 323 = **484 N**. 432 N covered the guy alone and
  missed the shared crown-strap load.
- **Bar rule:** the pristine room-temperature coupon has to show the *knocked-down* capacity ≥ factored, so
  proof = 323 / KD_eff, where KD_eff = 0.654 (knocked-down / pristine basis-A capacity at 38 mm). That gives
  **494 N**, which governs.

Checks on the parts at 494 N:
- 38 mm sleeve pristine capacity: 671 N (proof / capacity 0.74), so the test should pass even on basis A.
- POM toggle (670 N ASSUMPTION): 1.36.
- B-25 tab box-X: 2504 N.
- The heavy ladder lock at B-22 carries the guy only. LL-H stays at 432 N against its 490 N slip.

**Specimen and rig (TL-1a, 5 specimens, with the fix fitted):**
- **Tube:** the real crown top bar stock (rev C `[±45/0×5/±45]`, wall 1.065, same vendor, same clear coat). Not a
  generic 18 mm offcut: the hoop ring capacity depends on the layup. Cut it ≥ 160 mm long.
- **Fittings:** the as-built 38 mm B-25 sleeve (lap bartacked as at frame assembly), with the guy toggle and the
  crown-strap toggle both in the tab.
- **Support:** clamp the tube ends in V-blocks ≥ 40 mm outside the sleeve edges, so the bar reacts the load as a
  beam (shear flow), as on the frame. **No cradle or saddle under the sleeve:** a cradle opposite the loop turns the
  test into a point-pair crush (basis A) and over-tests it.
- **Loading:** pull on the guy toggle, aft and outward as in the field, in steps of 100 / 200 / 300 / 400 / 494 N.
  Hold 60 s at 494 N. Keep the cold repeat (1 sample after 4 h in the freezer: POM).

**Pass criteria (all must hold, 5 of 5):**
1. Holds 494 N for 60 s. The toggle does not pull through or crack; no broken stitch.
2. No crackle or crack sound during loading (listen, or put a phone microphone on the tube).
3. **Linear response:** the ovalisation reading at 494 N is within 1.15 × the linear extrapolation of the 100–300 N
   readings, with no knee.
4. **Ovalisation limit:** measure the elastic change of the diameter along the pull with a dial gauge on a C-frame,
   on the bare tube 2 mm outboard of the sleeve edge. It must be ≤ **0.40 mm** at 494 N. That is the basis A upper
   bound at the loop centre; basis B predicts 0.20 mm and basis C 0.005 mm. A larger reading means the bar is softer
   than the most conservative model: stop and report.
5. **Permanent set:** after unloading, remove the sleeve and measure the diameter at the loop centre at 0° and 90°
   with a micrometer. The out-of-round must be ≤ **0.02 mm** more than the pre-test reading.
6. No crush mark, whitening or resin crack under a 10× loupe, and the tap test is clean, against the untested
   control length.

**TL-1b (new, 1–2 specimens, bare bar, today's 25 mm sleeve, same rig):**
- Step-load to 494 N, or stop at the first knee or sound. Record ovalisation against load.
- Predicted at 288 N: ΔD 0.35 mm (A), 0.18 mm (B), 0.004 mm (C).
- Basis A predicts first-ply failure at 454 N, pristine.
- **Reading the result:**
  - If it holds 494 N, stays linear and its ΔD is ≤ the basis-B line, then basis B (or C) is credited for this bar,
    as T7 does for the bushings. Kits S and M could then keep the 25 mm sleeve.
  - If it marks, the 38 mm fix is confirmed as necessary.
- TL-1b is a data test, not a gate. TL-1a is the gate.

## 7. Assumptions

- ASSUMPTION: RING_SLICE. The wall is a ring slice as wide as the bearing; the tube either side is not credited.
  Settled by TL-1b.
- ASSUMPTION: BASIS_A. Design to the existing point-load ring rule; spread contact is credited only after a passing
  coupon (TL-1b).
- ASSUMPTION: WRAP_UNIFORM (basis C). Uniform strap pressure over the 180° wrap; friction is not mobilised under a
  symmetric pull.
- ASSUMPTION: LOAD_INTERP, COLLINEAR, CINCH, BAR_BENDING (section 2 / 3).
- ASSUMPTION: WIDE_SLEEVE. The 38 mm sleeve spreads the 25 mm tab pull over 38 mm. Settled by TL-1a.
- ASSUMPTION: LINER_SPREAD / COLLAR_SPREAD. HDPE spreads only by w + 2t; the printed collar spreads over its 40 mm
  length with no ring-moment share credited.
- Inherited from upstream: the guy and crown-strap 1 g forces (cloth sim), the 80 N cinch, the 670 N POM toggle,
  `SPINE_CLAMP_HALF`, `MIN_CLEAR_MM`, and the corner-wrap extent x 77–107 with an 8 mm scarf.

## 8. Downstream changes (not made here: the pack-designer owns these files)

1. **`patterns_corrie_f_rev3.py`, B-25:**
   - material poly_webbing_25mm → **poly_webbing_38mm**;
   - sleeve band x 26.5–64.5 (centre 45.5); run sleeve-to-spine-clamp 11.5 mm a side;
   - cut **387 mm** (was 412.5);
   - tab position (x 52 or x 45.5) is the pack-designer's call.
2. **GBL (patterns line 1229, mfg line 790, cut list, op 7.19):** rev 1+ routes the guy toggle into B-25, so GBL looks
   like a BL-004 leftover. Either delete it from rev 3 (−6.1 g for 2 × 170 mm), or state what it carries. If it bears
   on the bar it needs the same 38 mm treatment. Its 244 N load-table row is stale either way (now 288 N guy /
   323 N shared).
3. **`mfg_corrie_f_rev3.py`:**
   - BOM: add poly_webbing_38mm (0.39 m per bag), drop 0.41 m of 25 mm;
   - load_points rows "B-25 bridle toggle tab": design load **323 N** (guy + crown strap), proof 494 N;
   - op 7.16: hot-knife at 38 mm; the box-X on the tab is unchanged (21 × 15).
4. **`physical_test_kit.py` / `test_register.csv` TL-1 / `G2.md` §13:**
   - proof 432 → **494 N (50.4 kg)**;
   - specimen, rig and pass criteria as in section 6;
   - add **TL-1b**;
   - register margin text "toggle proof 1.83; bar wall 1.21" → "toggle proof 1.36; bar wall 1.36 static / 1.27 fatigue
     (38 mm B-25, basis A)".
5. **`loadpath_verification.md` A3 (`loadpath_check.py`):**
   - part = B-25 38 mm sleeve; demand 288 → 323 N; width 25 → 38;
   - add the fatigue row with the crown strap;
   - note the shared tab.
6. **Mass ledger:** B-25 7.43 → 10.82 g (+3.39 g base). As hunted +3.4 g; meat trip +3.4 g.
7. **`corrie_f_body.md` 13.5 / 15.2:** say that "288 N vs 312 N, 1.36" is bar bending, and point the ring check here.
8. **Frame side:** none for the recommended fix. If the hoop-ply option is chosen instead, change
   `frame.yaml frame.top_bar_section` and the stock row, then re-run `crown_diet` / `rev_c_verification` for the bar.
