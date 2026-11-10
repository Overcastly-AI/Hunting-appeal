# Frame competition, team D (SERVICE): one-piece SLS PA12 body

Owner: structural-fea-engineer (team D), 2026-11-10. Rules: `designs/pack_5200/frame_comp/RULES.md`.
Research (with a URL on every property): [docs/research/frame_comp_d.md](../../../docs/research/frame_comp_d.md).
Code: `huntkit/gendesign/frame_comp_d.py`. Tests: `tests/test_frame_comp_d.py` (6 pass). Results:
`designs/pack_5200/frame_comp/D/result.json`, `summary_rows.json`, and the STLs in the same folder. Scratch:
`outputs/frame_comp_d/`.

```
python -c "from huntkit.gendesign import frame_comp_d as D; D.run(); D.run2(); D.run2(mats=('pa12_sls',)); D.finalize('pa12_sls'); D.finalize('pa11_mjf'); D.write_results()"
```
That is about 35 min on a shared 4-core machine.

## 0. Verdict

| | today | **team D: SLS PA12, one piece** |
|---|---:|---:|
| printed body, g | 823 (PAHT-CF FDM, 2 pieces + 8 dowels) | **744** (SLS PA12, 1 piece) |
| frame, g | 1063 | **965** |
| frame + spreader, g | 1225 | **1127** (−98) |
| CORRIE B.2 pack, size M, g | 3964.5 | **3866.5** |
| body strength / fatigue / creep margin | 1.51 / 1.04 / 2.23 | 1.21 / 1.12 / 1.37 |
| frame-wide worst strength / fatigue | 1.12 crown legs / 1.04 body | 1.12 crown legs (unchanged) / 1.09 spreader (unchanged) |
| torsion stiffness of the body vs today (RT) | 1.00 | **0.45** |
| owner printing | 27 h + dry 12 h + anneal 6 h + dowel bond | none: upload one STL, pay, receive |
| unit cost incl. spreader, USD (1 / 10 / 100) | about 427 | 641 / 614 / 566 |

**Passes HA-LS-1 rev C** on every case, at torsos 15/19/23 in, with both bag-couple variants (42 sets), strength,
fatigue and creep. **Mass vs today: −98 g.** Read section 5 before scoring the mass. Most of the gain comes
from the re-sizing tool, not from the material. The same tool run on PAHT-CF reached 747 g with more margin and had
not converged. Per gram of structure, the service material is **not** better than PAHT-CF. Its real advantages
are lower density (0.95 vs 1.06), one piece (no split, no dowels, −18.5 g, no bond), isotropy, and no owner printing.

## 1. Method

- Loads: every rev C set from the frame.yaml beam model (`rev_c_verification.beam_runs`, buckling off): 27 sets
  with the couple on the crown bar and 15 with it on IM3, at torsos 15/19/23. This is the same load path as every
  release check. ASSUMPTION: the body's modulus does not enter the load path. The beam model uses its own stays,
  as in `rev_c_verification.md` §7.
- Body: the 2 mm voxel raster of the released branch body (`spreader_layout.raster(None, 2.0)`).
- **Stress does not depend on E** (the loads are applied forces), so one solve per geometry serves every material.
  Check: the PAHT-CF rule on the release body reproduces the release record exactly (**strength 1.510, fatigue
  1.044, creep 2.228** vs 1.51 / 1.04 / 2.23 in `rev_c_verification.md`).
- Failure rules (FI99 over non-patch voxels, as the release):
  - PAHT-CF: the release layer rule (`frame_topopt.layer_failure_index`);
  - PA11 / PA12 (powder bed, isotropic): von Mises / (0.8 × s);
  - SLS PA12-CF: Tsai-Hill in the frame plane (X 85 along the stays = recoater, Y 55 across, S 30 ASSUMPTION),
    through-thickness 45 MPa, interlayer shear 0.6 × 45.
- Fatigue and creep are computed from C1 exactly as `frame_cg_recheck.summarize_body`: FI at 1.6 g / fatigue ratio,
  and FI at 1 g / creep ratio.
- **Fatigue ratio from cited data:** Avanzini 2022 MJF PA12, Smax = 44 N^-0.034 (R 0.05). At 1e5 the mean is 29.7 MPa
  and the lower bound mean/√1.84 is **21.9 MPa**. Ratio to 48 MPa: **0.457** (PA11 on 50 MPa: 0.439). The fatigue
  allowable after the 0.8 knock is **17.5 MPa**, against 21.1 MPa assumed for PAHT-CF.
- Re-sizing (fully stressed SDF offset): the surface moves out by r (U^(1/3) − 1) where the 6 mm max-filtered
  utilisation U × 1.04 > 1, at most 3 mm per step. It moves in where U < 0.70, capped at 0.3 r (the weight_c C-9
  rule). Bores, sleeves, pawl housing, pivot boss, pads and spine channel never move in. After sizing, **the 8
  fairleads and all hard-point pads are restored** to today's geometry (+17 g), and the body is re-verified on all
  42 sets.
- Verification (tests): the Basquin numbers reproduce Avanzini Tab. 2. The iso and ortho rules reproduce
  uniaxial limits. The PAHT rule matches the release function. The unit-E voxel stress recovery matches M c / I on a
  cantilever (within 8 %). The voxel solver itself is verified against Timoshenko and Saint-Venant in
  `tests/test_frame_topopt.py`.

## 2. Material screen on today's shape (no re-sizing)

| material | body g | strength | fatigue | creep | verdict |
|---|---:|---:|---:|---:|---|
| PAHT-CF FDM (today, check) | 823 | 1.51 | 1.04 | 2.23 | pass |
| MJF PA12 | 784 | 0.81 | 0.91 | 1.11 | **fail** |
| MJF PA11 | 815 | 0.84 | 0.91 | 1.16 | **fail** |
| SLS PA12-CF (fibres along the stays) | 854 | 0.94 | 0.87 | 1.86 | **fail**, and heavier |

A straight material swap fails. Carbon-filled SLS is 4 % denser and weak across the recoater (55 MPa), and has
**no published fatigue data**. It was dropped.

## 3. Re-sized bodies

| body | g | strength | fatigue | creep | torsion vs today | split joint |
|---|---:|---:|---:|---:|---:|---|
| MJF PA11, JLC3DP (370 × 276 × 360 mm: **must split** at z 234) | 817 | 1.22 | 1.12 | 1.42 | 0.49 | 2 × 2 M5 bolts per stay, 40 mm pitch, 14 mm lap: SF 2.70, fatigue 2.23 (the 1 × 2 / 24 mm layout gives 1.23 / **1.01**) |
| **SLS PA12, one piece (630 × 330 × 550 mm)** | **744** | **1.21** | **1.12** | **1.37** | **0.45** | none |
| control: PAHT-CF, same tool, 6 steps, fairleads not restored | 747 | 1.52 | 1.26 | 2.68 | 0.88 | (today's dowels) |

Per-case body margins of the chosen body (worst torso):

| case | couple on crown bar | couple on IM3 |
|---|---:|---:|
| C1 static_carry | 2.63 | 1.96 |
| C2 drop_2p5g | 1.75 | 1.30 |
| C3 side_hill_torsion | 1.58 | 1.52 |
| C4 single_stay_setdown | 2.05 | 2.01 |
| C5 meat_straps | 1.45 | – |
| C6 tall_load | 2.34 | – |
| C6p tall_load_posts | 2.31 | – |
| C7 overload_haul | 2.04 | – |
| C8 hipbelt_off_abuse | **1.21** (15 in, upper bar / pawl housing) | 1.22 |
| fatigue (C1 at 1.6 g) | 1.50 | **1.12** (23 in) |
| creep (C1 at 1 g, 40 °C 8 h) | 1.84 | **1.37** |

The re-sizing moved material **into** the upper bar and pawl housing, the mid bar ends, the lower stays and the
lumbar struts (orange in `20261110_compD_2.png`). It took material **out of** the inboard branches, the stay
feet and the sleeve flanks.

## 4. Other load-path checks

| part | check | margin | basis |
|---|---|---:|---|
| pawl cheek, 8 mm, 304 bushing | factored pawl force 2156 / 850 N | **1.43** | `frame_production.cheek_check`, s = 48 iso (12 mm cheek: 2.11) |
| fairlead hinge cheek | strength / fatigue / creep | 1.62 / 1.39 / 1.70 | release 1 mm results × allowable ratio (ASSUMPTION, same stress state) |
| fairlead IM3 cheek | strength / fatigue / creep | 1.96 / 1.68 / 2.06 | as above |
| lower stay buckling (z 0–78, Ø18.6, hot/wet E 908 MPa, C4 limit 1334 N) | eigen / (1.5 × 1.5) | 2.88 | Euler, pin-pin (closed form) |
| crown, spreader, rack, hooks, pins | unchanged parts, unchanged loads | 1.09 (spreader fatigue) … | `rev_c_verification.md` |
| M5 heat-set inserts (hip pivot) | pull-out / torque-out | **coupon D-I1** | no SLS data found |

## 5. Honesty notes

1. **The material does not save mass. The tool does.** The PAHT-CF control on the same re-sizing reached 747 g
   at strength 1.52 and fatigue 1.26 and was still falling. Restoring its fairleads (about +18 g) gives about 765 g
   with plenty of margin left. A converged PAHT-CF body would very likely be lighter than 744 g. A home MONO entry
   that uses this kind of sizing should beat this one on mass. What SERVICE uniquely gives is **one piece, no
   printing, no anneal, no dowel bond**, which counts for build simplicity.
2. **Stiffness halves.** The body torsion stiffness at RT is 0.45 × today's (E 1650 vs 3860). At 40 °C wet PA12 sits in
   its glass transition (Tg onset 27 °C, NETZSCH DMA), so it is about 0.42 × today hot as well. HA-LS-1 has no
   stiffness rule, but the T1 "deflection within ±30 % of FEA" check and the carry feel will notice. The crown
   carbon legs inside the sleeves carry most of the upper-frame bending, which helps.
3. **Creep near Tg.** The 40 °C creep margin of 1.37 rests on an assumed rupture ratio of 0.35. No published 40 °C creep
   rupture data exist for powder-bed PA12. A body left loaded in a hot truck is the scenario that breaks this, as it
   is for PAHT ("Do not" list).
4. The fatigue curve is MJF PA12, applied to SLS PA12. The research doc gives a Goodman cross-check of SLS PA12
   (18 MPa amplitude at R −1 → about 26 MPa Smax at R 0, against 27.7 for MJF). Coupon D-F1 must use bars from the
   ordered build.
5. The service price ($0.40/g) is a cited UK per-cm³ benchmark, not a Materialise quote. Materialise quotes
   online only.
6. The STLs are 2 mm voxel surfaces (upsampled and smoothed). Before ordering, re-mesh them from the SDF plus the
   offset field for a clean surface. ASSUMPTION: the surface finish of a powder-bed part is not worse in fatigue
   than the Avanzini bars, which were as-printed MJF.

## 6. Ordering and build (owner)

1. Upload `designs/pack_5200/frame_comp/D/body_pa12_sls_onepiece.stl` (265 × 65 × 545 mm) to the Materialise
   PA 12 (SLS) instant quote. Natural white, or "extra smooth" vapour smoothing (envelope 560 × 360 × 330: it fits).
   Black dye is limited to 400 mm at Materialise, so dye at home (RIT-type nylon dye bath) if wanted. ASSUMPTION:
   a 60 °C dye bath does not distort the part; hang it on a rod through both sleeve bores.
2. Ask for 6 tensile bars and 6 fatigue bars **in the same build** (coupons D-C1, D-F1).
3. Ream the sleeve bores to 18.0 mm, ream the pawl cheeks and press in the 304 sleeves, and fit 4 × M5 heat-set
   inserts at the pivot. Then assemble the crown, bushings and spreader exactly as in `print/frame/PRODUCTION.md`.
   No anneal. No dowels. No MMA on the body.
4. The alternative if the owner wants the cheapest and toughest-in-cold route is MJF PA11 at JLC3DP ($0.30/g), 2
   parts (`body_pa11_mjf_split_lower/upper.stl`) and a bolted half-lap at z 234. This is **heavier than today**:
   frame + spreader 1250 g. Not recommended.

## 7. Assumptions

- ASSUMPTION: rev C body loads from the beam model, independent of body material (release practice).
- ASSUMPTION: SLS PA12 48 MPa isotropic (Materialise page), 0.8 hot/wet knock, von Mises rule.
- ASSUMPTION: fatigue lower bound = Avanzini mean / √T, applied to SLS PA12; creep-rupture ratio 0.35.
- ASSUMPTION: re-sizing parameters (6 mm smoothing, U_lo 0.70, 3 mm per step, 0.3 r cap, target 1.04, keep fatigue
  ≥ 1.02).
- ASSUMPTION: dowels and dowel MMA in today's frame = 18.5 g (8 × Ø5 × 70 mm, 1550 kg/m³, + 1.5 g MMA), removed.
- ASSUMPTION: split-joint hardware for the PA11 option is 49.6 g (8 Ti M5 × 30, 8 Ti nuts, 8 printed bosses).
- ASSUMPTION: PA bearing capacity of a bolt = 0.8 × s × d × t (coupon D-J1).
- ASSUMPTION: costs: same per-gram price at 10 units, −15 % at 100, $30 shipping per order, today's hardware and
  spreader $313.3.
- ASSUMPTION: build 5 h (ream, press, inserts, crown bond as today).

## Screenshots

- `outputs/screens/20261110_compD_1.png`: Cycles, today's body (left) next to the one-piece SLS body (right)
- `outputs/screens/20261110_compD_2.png`: utilisation of the chosen body, and the voxels added and removed vs today
- `outputs/screens/20261110_compD_3.png`: frame + spreader mass and body margins for every candidate, with the PAHT control
