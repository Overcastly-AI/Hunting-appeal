# Pack 5200 hipbelt B: structural check (wing joint, centre plate, Ti pivot, 2:1 pull)

Owner: structural-fea-engineer, 2026-11-09. Status: **analysis; proposes design changes (section 0).** Nothing in the
released geometry, YAML or patterns was edited.

Inputs: belt B adopted 2026-11-09 (`docs/DECISIONS.md`); flags in [hipbelt_fit.md](hipbelt_fit.md) section 6;
loads and factors from HA-LS-1 rev C ([load_standard.md](load_standard.md), `huntkit/fea/load_standard.py`).
Code: `huntkit/gendesign/hipbelt_structure.py` (all checks, figures), `huntkit/gendesign/hipbelt_pivot_fe.py` (SLM Ti
mount FE re-run). Results: `analysis/hipbelt_structural_results.json`, `outputs/gendesign/pivot_recheck.json`.
Tests: `tests/test_hipbelt_structure.py` (13 pass, including 4 closed-form solver checks).

**SF/req** below is the capacity divided by the factored demand. The case factor is already in the load, so
**≥ 1.0 passes**. Units: mm, N, MPa, g. Imperial values are in brackets.

---

## 0. Summary

| Item | Result | Status |
|---|---|---|
| **Centre plate as drawn** (flat PA66-GF30 plate backing the lumbar pad, 45 g booked) | Bending off the 36 mm hub: C2 SF/req **0.61**, walking fatigue **0.20**. A plate that passes in PA66 is over 150 g | **FAILS: redesign** |
| **Centre plate, recommended**: curved 6061-T6 1.5 mm bow-tie; lumbar pad bears on the frame lumbar pan | C2 **1.21**, C1 1.94, fatigue **1.20**, creep 3.9; 95 g | passes |
| Centre plate, fallback: pad stays on the plate; ribbed 7075-T6 (0.8 skin, 8 mm ribs, machined) | C2 1.59, fatigue **1.25**; 121 g | passes, heavier |
| **Fixed wing joint "stitched ear"** (ear inside the wing root, 2 × 22 holes of 2 mm, hand saddle-stitched, tex 135) | thread per hole fatigue **1.82** (C2 3.03); plate bearing 6.7; textile 9.5 | passes |
| Wing shell (330D) carrying T, HDPE floating | C2 2.15, fatigue 1.67; stretch about 9 mm per XXL wing at the walking peak | passes |
| **Ti pivot**: does the existing 8.6 / 19.7 include the lumbar push? | **No.** Every HP load set in the lug study has Fy = 0 | re-checked |
| Ti pivot with H on the pin (FE re-run, 49 load sets) | static **4.69** (was 8.51 reproduced, record 8.56), fatigue **4.25** (was 19.4) | passes |
| Ti pin, CP hub bore, thrust face (hand checks, H on the pin) | 4.91 / 1.66 (fatigue) / 13.3 | passes |
| 2 × M5 heat-set inserts, Ti mount to the printed boss | **1.14** with H on the frame; **0.995** with H on the pin (ASSUMPTION insert capacity) | **flag: never checked before; needs a record and test** |
| **2:1 pull**, belt-side anchor (D-ring tab box-X) | 4.71; textile under the tab 4.74; D-ring 3.08 | passes |
| Heavy ladder lock (record `ladder_lock_25mm_heavy`) | slip 1.72 × lock leg at the walking peak (criterion ≥ 1.5); stumble 1.38; break 1.67 | passes; **test-qualify** |
| **2:1 routing as written in hipbelt_fit.md §4.1** | lock between the anchor and the D-ring holds the full T: slip 1.01 | **fix the routing** |
| **HDPE creep at the D-ring tab** | floating HDPE carries no net tension: OK. Fastened at both ends: sustained bearing 9.2 MPa vs 5 → creep SF/req **0.55** | **rule: HDPE floats** |
| 50 mm buckle | 1.50 | passes |

**Design changes needed**
1. **Centre plate (new part).** Move the lumbar pad so it bears on the frame lumbar pan, which is what the frame FE
   already assumes (`frames.py` group `lumbar_pad` P11..P33 with ky 30 N/mm; the `hipbelt` HP spring has ky 0). The
   centre plate becomes a **6061-T6 1.5 mm water-jet bow-tie** (spine 60 mm tall, ears 140 mm tall, 210 mm wide),
   **rolled to an arc with a 14.6 deg end slope (R ≈ 420 mm)**, with a PA66-GF30 hub bushing (Ø36 × 12) for the
   10 mm Ti pin and a POM thrust washer. 95 g vs 45 g booked. Curvature is the lever: the same plate flat fails
   (fatigue 0.40). If the pack-designer wants the pad to roll with the belt, use the fallback ribbed 7075 plate
   (121 g, machined).
2. **Wing joint = stitched ear**, no cant snap and no fastener through the HDPE (section 2).
3. **HDPE stiffener floats**: no rivet, screw or stitch fixes it at the root. Tab stitches through it are allowed.
4. **2:1 routing**: anchor on the buckle half → round the D-ring on the wing tip → back through the ladder lock on
   the buckle half → tail. The lock must come after the D-ring.
5. **M5 mount screws**: the frame owner should add a heat-set insert record and a pull-out test (or move to 3-4 × M5).

**Mass of the load-path members** (per belt, size M): centre plate 94.6 g (6061 plate 77.5, PA66 hub 13.5, latch
4.0); 1000D root doublers 10.2 g; 1000D tip doublers 4.1 g; ear thread 0.5 g; POM thrust washer 1.0 g; total
**110.4 g vs 51 g booked** (plate + latch 45, cant snap 6). The pack goes up about **+59 g** (3540 → ~3600 g,
7.9 lb), before any frame-side pad interface (ASSUMPTION ~10 g, pack-designer).

---

## 1. Loads (HA-LS-1 rev C)

| Set | T per side | H lumbar push | V hip (80 %) | basis |
|---|---|---|---|---|
| **C2** stumble 2.0 g × 1.5 (governs strength) | **1000 N** (225 lbf) | 1239 N | 1601 N | T: 483 N × 2.0/1.6 × 1.5 = 906 N, rounded up (ASSUMPTION: users above the 42 in ANSUR band, over-cinching) |
| C1 static 1.0 g × 2.0 | 604 N | 826 N | 1067 N | T at 1 g = 483 / 1.6 |
| **walk** 0 → 1.6 g, 1e5 cycles (fatigue) | 483 N | 661 N | 854 N | worst B form (M42, XXL), `hipbelt_results.json` |
| carry 1 g, sustained (creep) | 302 N | 413 N | 534 N | |

- T = the wing tension the fit model needs to hold 80 % × 68 kg at the 1.6 g walking peak (μ 0.3).
- H = 68 kg × g × 205 mm / (yoke z − 120). The worst torso is 15 in (lever 331 mm): 413 N at 1 g.
- Wing direction at the plate edge: θ = 9.8–19.4 deg forward of lateral over the 16 ANSUR forms (fit-model
  sections); **20 deg** design for a flat plate. Vertical share per wing: **0.40** (the fit model gives wings
  0.57–0.79 of the hip load). Lumbar pressure centroid −4 to +16 mm about the pin (fit model); **±20 mm** is used
  where it matters (pivot).
- C3 (1.6 g × 1.5 = 2.4), C5/C6 (2.0 g × 1.5, CG 190 / 185 mm) and C7 (91 kg × 1.6 g × 1.0) are enveloped by C2 for
  the belt. C4 and C8 put no load on the belt.

## 2. Fixed wing-to-centre-plate joint: "stitched ear"

**Geometry (buildable).** Each side of the centre plate ends in an **ear** 30 × 140 mm (1.2 × 5.5 in). The ear
slides into the wing root between the 330D outer shell and the inner face, with a **1000D Cordura doubler on each
face** (ear + 20 mm, 50 × 150 mm). Two vertical rows of **Ø2.0 mm holes at 6 mm pitch, 22 per row**, at 12 mm and
22 mm in from the ear root. The outer row is **8 mm** from the ear edge, and the end holes 6 mm from the top and
bottom. The holes are drilled with the water-jet profile, then deburred and lightly countersunk both sides. Hand
**saddle-stitch** through all layers, tex 135 bonded nylon, two needles, one pass per hole (about 45 min per side).
The wing binding closes over the ear edge. No rivets, no screws, no cant snap. The cone angle is set by the cut wing
pattern; the ear only holds it.

**Why stitching.** The tension, the vertical shear (wing share up to 0.40 V) and the cant moment all go in over the
full 140 mm root as many small loads. A rivet or screw through the 1.0 mm HDPE would put 60–80 MPa bearing on HDPE
(yield 26 MPa) at C2. A fabric loop round a slot bar carries T but grips the vertical shear only by friction
(0.47 T, against V/T = 0.7–1.05 needed).

**Checks** (`ear_check`). In-plane resultant R = √(T² + V_w²). Outer row 60 %, end holes 1.5 × the row mean
(ASSUMPTION). Hole capacity = 1.5 × thread break (repo seam rule, `clothsim.fabric`). Bearing width = 2 thread
diameters.

| Check | C2 | walk (fatigue) | basis |
|---|---|---|---|
| Thread per hole | 48.6 N vs 147 N → **3.03** | 24.2 N vs 0.3 × 147 → **1.82** | ASSUMPTION: textile 1e5 limit 0.3 × break |
| Plate bearing (thread on 1.5 mm Al) | 36 MPa → 6.7 | 17.9 MPa → 13.2 | 6061-T6 S-basis yield |
| Shear-out to the ear edge | 2.3 MPa → 52 | 103 | |
| Net section at the outer row | 6.9 MPa → 35 | Kt 3 → 23.6 | |
| Textile (330D + 1000D, both faces) | 8.5 N/mm → 15.7 | 9.5 | seam efficiency 0.8 |

**Wing body.** With the HDPE floating, the 330D shell carries T. At the tip (105 mm tall) the line load is 9.5 N/mm
at C2 vs 0.8 × 25.6 N/mm → **2.15**. Walking: 4.6 N/mm = 18 % of the strip strength → fatigue **1.67**. Stretch at
the walking peak is 3.0 % (secant, ±50 %), about **9 mm per XXL wing**, mostly elastic. Cut the wing shell with the
**warp along the wing** (k_warp 128 vs k_weft 85 N/mm).

## 3. Centre plate (never analysed before)

**Model** (`cp_model`, `cp_check`). A plate grillage (strips along x and z, `huntkit.fea.frame`) on a **Winkler
foundation**. The foundation is the B lumbar foams (EVA 45C 6 + EVA 30C 6) plus 25 mm of tissue, the fit model's own
k = 0.0022 N/mm³. The pin is held in x, z and pitch, and is free in roll (elastomer bushing). The wing pulls go in at
the stitch rows. Out-of-plane bending comes from the grillage. In-plane membrane stress comes from a closed form at the
hub-edge and spine sections (a grillage is a poor membrane). The two are superposed, which is conservative.
Allowables:
- PA66-GF30: conditioned UTS 125 × hot 0.8; fatigue 0.3 UTS at 1e5 (repo precedent, `lugs.py`); creep 0.25 UTS.
- Metals: S-basis yield; fatigue from the repo Basquin curve with Goodman at R = 0 (`fea.fatigue`).
- Kt 2.0 in fatigue (ASSUMPTION: radiused corners ≥ 3 mm, hub fillet).

**Verification** (`tests/test_hipbelt_structure.py`):
- Strip cantilever δ = PL³/3EI and σ = 6PL/bt²: within 0.1 %.
- Simply supported strip wL²/8 and 5wL⁴/384EI: within 1 %.
- Hetényi beam on an elastic foundation (w₀ = Pλ/2k, M₀ = P/4λ): within 2–3 %.
- Annular plate, clamped hub and free edge (Roark Table 11.2 case 2L): K = 0.1736 at b/a = 0.5 (Roark 0.1730); the
  narrow-ring limit q(a − b)²/2 within 1 %.
- Equilibrium of the plate model.

| Variant | Mass | C2 | C1 | walk (fatigue) | carry (creep) | Walking pressure under the plate |
|---|---|---|---|---|---|---|
| **As drawn**: flat PA66-GF30 3 mm, pad on the plate | 135 g (not 45) | **0.61** | 0.86 | **0.20** | 0.54 | 27–41 kPa |
| PA66 plate with ribs (2.5 skin, 14–22 mm ribs; flat or curved) | 155–173 g | 1.0–1.9 | | 0.35–0.60 | | |
| **Fallback**: pad on the plate, 7075-T6 0.8 skin + 8 mm ribs at x 0/±25/±50/±75 and z 0, machined | 121 g | 1.59 | 2.16 | **1.25** | 4.3 | 33–34 kPa (rigid, as the fit model assumed) |
| **Recommended**: pad on the frame, 6061-T6 1.5 mm bow-tie, curved 14.6 deg | **95 g** | **1.21** | 1.94 | **1.20** | 3.89 | 2–6 kPa (hoop pull only) |
| Same, flat | 95 g | 0.39 | 0.65 | 0.40 | 1.29 | 8–26 kPa |

- **Why the drawn plate fails.** It is a 140 × 150 mm pad backer held only at a 36 mm hub. The annular-plate closed
  form gives M = 0.56 q a² at the hub (a = 82 mm). At the walking load (q = 47 kPa) that is 177 N mm/mm, so a solid
  PA66 plate needs 7.5 mm to meet the fatigue allowable. No 45 g PA66 part can do this, and the current belt (C0) has
  the same untested part.
- **Why curving works.** A flat plate meets the wrapped wing at θ = 10–19 deg, and the wing then pulls the ears toward
  the body with T sin θ. Rolled to the median end slope (14.6 deg), the residual is at most 4.8 deg (ASSUMPTION
  floor 3 deg). The hoop tension then acts as an arch force, not a bending load. Roll 1.5 mm 6061-T6 by hand over a
  ~400 mm form (springback: check with a template).
- **Bow-tie and pad on the frame.** The frame model already reacts the lumbar push on the lumbar pan grid (C1 15 in:
  384 N at P11..P33 vs 413 N here), and the printed-body and rev C checks include it. So H never enters the belt plate
  or the pivot. **Pack-designer to resolve:** seat the pad backer on the frame back-pad zone (y −27..−48) with a
  4 mm clear channel for the plate spine; the pad then stays still while the belt rolls ±8 deg (HDPE slip liner on
  the channel). The fit model's "rigid lumbar, no pitch" assumption still holds.
- Deflection at C2: 6.2 mm at the ear tips into the foam. The C2 peak is near the hub (spine at x 18–25 mm).

## 4. Ti hip pivot (z 120): the fore-aft lumbar push

**Does the existing check include it? No.** The generative-design lug loads are the frame-model reactions at HP. In
that model the lumbar push goes to the `lumbar_pad` springs (P11..P33) and the `hipbelt` spring at HP has ky = 0. So
all 21 HP load sets in `outputs/gendesign/stage_specs.pkl` have **Fy = 0**. They are vertical (534–1145 N) plus a
side-hill lateral load.

**Re-check** (`hipbelt_pivot_fe.py`). The same lug was re-optimised (same SIMP, the same 3 load sets, vf 0.025,
deterministic). The record is reproduced: **8.51** vs 8.56, fatigue **19.4** vs 19.7. The fine-mesh verification
(15 549 solid voxels at 0.69 mm) then ran under every original set plus each set with H on the pin axis (+y, toward
the frame) and the pad-offset moment Mx = −eH for e = ±20 mm. H per case (rev C CG; 15 / 19 / 23 in):

- static 413 / 316 / 256 N
- C2 826 / 632 / 512 N
- side-hill 661 N (15 in)
- meat 766 N (15 in)
- tall 746 N (15 in)
- overload 820 N (15 in)

| | without H (record) | **with H on the pin** |
|---|---|---|
| SLM Ti mount, static SF/req (all cases) | 8.51 (side-hill 23 in) | **4.69** (C2, 15 in, pad centroid 20 mm high) |
| SLM Ti mount, fatigue (walking, Goodman, as-built HIP 200 MPa) | 19.4 | **4.25** (σmax 89 MPa) |
| Ti pin Ø10 bending (Ti-6Al-4V S-basis 827) | 8.45 | **4.91** C2, 5.67 walk |
| PA66 hub bore bearing (engagement 12 mm) | 7.5 | 2.37 C2, **1.66** walk |
| Hub thrust face via POM washer (Ø36) | n/a | 18.9 |
| 2 × M5 heat-set inserts, mount to printed boss (prying about the D32 boss edge) | 1051 N → **1.14** | 1206 N → **0.995** |

- The pivot passes either way. With the recommended plate (pad on the frame), H stays off the pin and the record
  numbers stand.
- H is compressive: the pad pushes the plate onto the mount. The POM latch carries none of it, so the mount face must
  bear through a **POM thrust washer**, not the elastomer.
- **New flag (frame owner):** the 2 × M5 brass heat-set inserts that hold the SLM mount on the printed boss are not
  checked anywhere, and `data/materials` has no insert record. Insert capacity ASSUMPTION: 1500 N × hot 0.8. Even
  without H, SF/req is only 1.14. Add a record and a pull-out test, or go to 4 × M5 on a D40 boss.

## 5. 2:1 pull path: belt-side anchor, lock, HDPE creep

**Routing.** As written in hipbelt_fit.md §4.1, the webbing is anchored at the wing tip, runs through the lock, then
round the D-ring. With that order, once the hand lets go the D-ring legs go slack and the lock holds the full T:
slip 490 / 483 → **1.01**. **Correct routing:** anchor on the buckle half → round the D-ring on the wing tip → back
through the ladder lock on the buckle half → tail. The lock leg is then T / (2 × 0.85) (materials record basis).

| Item | Demand | Capacity | SF/req |
|---|---|---|---|
| **Belt-side anchor**: D-ring tab, 25 mm poly webbing round the D-ring, box-X 25 × 40 mm, tex 135 at 3.5 mm, through the shell + a 1000D tip doubler 60 × 100 | T = 1000 N (C2) | 4711 N (half the box-X length effective, ASSUMPTION) | **4.71** |
| Textile under the box (load spreads at 30 deg: 71 mm effective) | 1000 N | 4738 N | 4.74 |
| D-ring 25 mm Al (Extremtextil 71719) | 1000 N | 3080 N | 3.08 |
| Heavy ladder lock, slip at the walking peak | 284 N | 490 N (slip = 0.5 × rating, ASSUMPTION in the record) | 1.72 → **1.15** on the 1.5 criterion |
| Heavy ladder lock, slip at the 2.0 g stumble | 355 N | 490 N | 1.38 (momentary slip only) |
| Heavy ladder lock, break | 588 N | 981 N | 1.67 |
| 50 mm buckle | 1000 N | 1500 N | 1.50 |
| 25 mm webbing | 588 N | 13 344 N | 22.7 |

**HDPE creep at the D-ring tab.** B as defined here does not fasten the HDPE at the root, so the HDPE is a free body
and carries **no net tension**. The tab stitches may pierce it, and nothing creeps. If the HDPE were fixed at both
ends (as by the old cant snap), it would take **87 %** of T, being 8.6 × stiffer than the shell. The tab needle holes
would then see 9.2 MPa sustained against a 5 MPa long-term limit (ASSUMPTION: PE80 MRS 8 MPa, ISO 12162, ÷ 1.6), so
creep SF/req **0.55**. Fatigue would be 0.68 and shear-out creep to the soft-tip end 0.52.
**Rule: the HDPE floats.**

## 6. Mass reductions that keep SF/req ≥ 1 (candidates, not yet checked)

1. 7075-T6 1.2 mm bow-tie instead of 6061 1.5 mm. In this model it passes at 1.77 (fatigue), 82 g (−12.5 g), but
   7075-T6 cannot be rolled cold: form it in O temper and age it (service), or machine the arc.
2. PA66 hub bushing Ø36 × 12 → Ø28 × 10 (−6 g). Re-check the hub bore bearing (walk 1.66 with H; 5.3 without).
3. Lightening holes in the bow-tie spine flanges between x 30 and 55 (−5 g). Needs a re-run: the spine carries the
   C2 peak.

## 7. Assumptions (also tagged in the code)

- ASSUMPTION: T_f 1000 N per side.
- ASSUMPTION: θ 20 deg flat / residual ≥ 3 deg curved.
- ASSUMPTION: wing V share 0.40 per side.
- ASSUMPTION: pad centroid ±20 mm (pivot).
- ASSUMPTION: hot knockdown 0.8 on PA66.
- ASSUMPTION: PA66 fatigue 0.3 UTS and creep 0.25 UTS (no fatigue or creep field in `pa66_gf30`; materials-engineer
  to add a cited S-N curve).
- ASSUMPTION: Kt 2.0 (fatigue, radiused corners) and Kt 3 (open hole).
- ASSUMPTION: HDPE long-term 5 MPa and fatigue 10 MPa (no creep data in `hdpe_sheet`; materials-engineer to add).
- ASSUMPTION: thread diameter 0.45 mm.
- ASSUMPTION: outer stitch row 60 %; end holes 1.5 ×.
- ASSUMPTION: textile 1e5 limit 0.3 × break.
- ASSUMPTION: box-X 50 % effective; 30 deg spread under the tab.
- ASSUMPTION: 2:1 efficiency 0.85 (hipbelt_fit.md).
- ASSUMPTION: M5 heat-set insert 1500 N.
- ASSUMPTION: the grillage stands in for a plate; bending and membrane are superposed.
- ASSUMPTION: Winkler foundation k = 0.0022 N/mm³, linear (no lift-off modelled; no tension appeared in the
  recommended case).
- ASSUMPTION: shallow arc modelled flat with a reduced wing angle.

## 8. Tests to add (prototype)

- **HB-4 ear joint**: one ear stitched into a wing-root coupon; pull at 20 deg to 1.5 kN (C2 × 1.5). Pass: no thread
  break and hole elongation < 0.5 mm.
- **HB-5 plate proof**: plate on the Ti pin over a foam block; 1.0 kN per ear at the residual angle, plus 1.6 kN
  vertical. Pass: no yield (scribed grid). Then 1e5 cycles 0 → walk loads (T5 rig).
- **HB-6 M5 insert pull-out** in the printed body material, 5 inserts. Pass ≥ 1.5 kN.
- **HB-7 lock slip**: as the record notes; done with the corrected routing.

## Screens

- `outputs/screens/20261109_hipbelt_fea_1.png` (copy `analysis/hipbelt_structural_1.png`): utilisation chart, worst
  case per item.
- `outputs/screens/20261109_hipbelt_fea_2.png` (copy `analysis/hipbelt_structural_2.png`): recommended plate,
  grillage bending utilisation (C2) and deflection on the foundation.
