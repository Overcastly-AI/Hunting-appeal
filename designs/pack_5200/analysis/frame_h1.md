# H1 printed frame body: generated, verified, joint designed

Owner: structural-fea-engineer, 2026-11-10. Decision: `docs/DECISIONS.md` 2026-11-10 (owner adopted H1). Judge:
[frame_comp_verdict.md](frame_comp_verdict.md). Standard: HA-LS-1 rev C ([load_standard.md](load_standard.md)).

- Code: `huntkit/gendesign/frame_h1.py`. It imports team A (`frame_comp_A`: primitives, floors, buckling cuts) and
  team D (`frame_comp_d`: solve, failure rule, offset step, hard-point restore). Nothing is copied.
- Tests: `tests/test_frame_h1.py`.
- Results: [frame_h1_results.json](frame_h1_results.json). Mass: [frame_mass_h1.json](frame_mass_h1.json).
- Print package: [`print/frame_h1/`](../print/frame_h1/README.md). Coupon plan:
  [`tests_physical/CA1_fatigue_rig.md`](../tests_physical/CA1_fatigue_rig.md).
- Run: `python -m huntkit.gendesign.frame_h1 all` (about 15 min on 2 cores), or `push`, `verify`, `export`,
  `render` separately.

## 0. Result: actual numbers against the judge's estimate

| | today (dowels booked) | judge's H1 estimate | **H1 actual** |
|---|---:|---:|---:|
| printed body, g | 823.2 | ≈ 745 + 25.6 bosses | **757.7** (bosses 27.3 and floors 13.0 included) |
| print mesh (what the slicer sees), g | 782 | – | 764.5 (lower 293.5 + upper 470.9) |
| z 234 joint parts, g | 18.5 (8 dowels + MMA) | 30.9 (Ti bolts and nuts 22.4 + 4 dowels 8.5) | **28.0** (4 Ti M5 × 45 low head 17.7, booked with the ISO 4762 head mass; nuts 4.5; 8 washers 5.8; no dowels) |
| **frame**, g | 1081.1 | ≈ 1040.9 | **1025.1 (2.26 lb)** |
| **frame + spreader**, g | 1243.4 | ≈ 1203.2 | **1187.4 (2.62 lb)**, −56.0 g |
| **CORRIE B.2 pack, belt M**, g | 3982.9 (8.78 lb) | ≈ 3942.7 | **3926.9 (8.66 lb)** |
| body strength margin | 1.51 | ≈ 1.45 | **1.45** (C8 hipbelt-off, 15 in, upper bar / pawl housing) |
| body fatigue margin (0.30, 1e5, 1.6 g) | 1.04 | ≈ 1.25 | **1.28** (C1 static carry, IM3 couple, 23 in) |
| body creep-rupture margin | 2.23 | ≈ 2.67 | **2.73** |
| branch Euler buckling (A rule) | 1.50 | ≥ 1.16 | **1.31** (upper branch R, C4 set-down, 23 in) |
| **z 234 joint, strength / fatigue** | dowel pull-out 1.03 (never re-solved) | not computed | **1.96 / 1.22** (fatigue: boss bending + prying) |
| CA-1 flip point (H1 fails if the coupon ratio is below) | 0.287 (A) | 0.24 | **0.234** |
| body fatigue if CA-1 proves 0.40 | | | 1.71 |
| torsion stiffness vs today (23 °C) | 1.00 | | 0.75 |
| unit cost incl. spreader, qty 1 | about $427 | $441 | **about $437** (§5) |

**H1 passes HA-LS-1 rev C** on all 42 sets: 27 crown-bar and 15 IM3-couple sets, torsos 15/19/23, both bag-couple
variants. It passes strength, fatigue, creep, branch buckling, the dry joint and every interface keep-out (§4).

It is **16 g lighter than the judge's estimate**, for three reasons:
- the dowels are gone (the fitted bolts take the shear);
- the bosses are lighter than A's hand estimate once the voxels they share with the stay are counted once;
- the push converged slightly lower than the judge's run.

The joint margins hold only because the bosses were moved off A's fore/aft layout (§3).

## 1. Method

1. **Start:** team D's PAHT-CF control (`outputs/frame_comp_d/paht_fdm_run2_best.npz`, the cumulative surface
   shift of D's SDF offset tool).
2. **Re-size** (`frame_h1.push`). D's `offset_step`, continued with the judge's settings:
   - local-radius cap 0.45, thinning below 0.85 × target, target 1.04, 6 iterations;
   - every iterate re-assembled as the D offset body plus:
     - fairleads and pads restored (`D.restore_hardpoints`), plus today's material within 6 mm of each pad, so no
       pad floats;
     - branches held at D's control section;
     - **A's floors** as A primitives at floor scale: branch, strut and mid bar r ≥ 5.0 mm, foot ball r ≥ 8.4 mm;
     - the **4 joint bosses**, minus the bolt holes, counterbores and traps;
     - keep-outs (passive solid/void) re-imposed, largest connected part with the pivot kept.
   - Every iterate is solved on all 42 sets: one PARDISO factorisation, `D.solve_fields` + `D.evaluate`, the release
     FI99 layer rule with clamp and load-patch exclusion.
   - A's branch buckling is computed on the same solve.
   - Accept rule: min(strength, fatigue, creep) ≥ 1.02 (ASSUMPTION, voxel noise reserve) and buckling ≥ 1.0.
3. **Verify** (`frame_h1.verify`): the chosen iterate with the final joint geometry, solved again. Body margins per
   case, per torso and per couple variant; fatigue at 0.40; A's buckling; the joint check (§3); keep-outs (§4);
   bore continuity (§3.4); torsion.
4. **Solver verification.** The voxel solver and stress recovery are checked against closed forms in
   `tests/test_frame_topopt.py` (cantilever, Saint-Venant torsion) and `tests/test_frame_comp_d.py` (M c / I). The
   new joint mechanics are checked against hand solutions in `tests/test_frame_h1.py`: pure tension, uniform
   compression, moment lever bounds, offset bolt equilibrium, boss bending, capacities.

Push history (`outputs/frame_h1/push.json`, figure `20261110_h1_5.png`). Every iterate passes. Fatigue sits flat at
1.28: it is set at the sleeve wall and bushing seat, which the keep-outs hold.

| it | raster g | strength | fatigue | creep | buckling |
|---:|---:|---:|---:|---:|---:|
| 0 (D control + floors + bosses) | 788.6 | 1.54 | 1.29 | 2.75 | 1.24 |
| 1 | 770.6 | 1.50 | 1.28 | 2.74 | 1.29 |
| 3 | 762.1 | 1.47 | 1.28 | 2.74 | 1.37 |
| 6 (chosen) | 756.4 | 1.45 | 1.28 | 2.73 | 1.35 |
| **verify** (final joint geometry) | **757.7** | **1.45** | **1.28** | **2.73** | **1.31** |

## 2. Body rev C results (verify)

| variant | torso 15 | torso 19 | torso 23 |
|---|---|---|---|
| couple on crown bar: strength / fatigue / creep | **1.45** (C8, upper bar / pawl) / 1.61 / 3.44 | 2.15 / 1.71 / 3.64 | 2.17 / 1.77 / 3.77 |
| couple on IM3: strength / fatigue / creep | 1.47 (C8) / 1.52 / 3.25 | 2.10 / 1.47 / 3.14 | 2.14 / **1.28** / **2.73** |

Per case, minimum over torsos and both variants (margin = SF / requirement, requirement in the factor):

| case | margin |
|---|---:|
| C1 static carry | 3.41 |
| C2 drop 2.5 g | 2.28 |
| C3 side-hill torsion | 2.05 |
| C4 single-stay set-down | 2.43 |
| C5 meat straps | 2.48 |
| C6 tall load / C6p posts | 3.40 |
| C7 overload haul | 3.48 |
| C8 hipbelt-off | **1.45** |

Branch buckling, A's rule (K 1, E × 0.6 hot × 0.7 creep, P_cr ≥ 1.5 × factored):

| member | margin |
|---|---:|
| lower branch L / R | 1.48 / 8.0 |
| upper branch L / R | 5.3 / **1.31** |
| mid bar | never in compression |

Member families (A's grouping, g; today in brackets from the judge's re-check):

| family | H1 g (today g) |
|---|---|
| foot | 7.8 (15.7) |
| stay below the sleeve | 113.3 (128.3) |
| sleeve | 262.7 (241.8, the bosses sit here) |
| top / upper bar / pawl | 195.2 (211.1) |
| branch | 70.2 (83.2) |
| strut | 87.9 (112.5) |
| mid bar | 20.7 (30.7) |

- Mid bar: the r 5.0 mm floor is a primitive. On the 2 mm raster its cut reads r_eq 4.8 mm, which is how a 5.0 mm
  circle rasterises.
- Foot balls: at the A floor (8.4 mm).
- Figures: `20261110_h1_3.png` (utilisation and the voxels removed and added against today).

## 3. The dry z 234 joint

### 3.1 Why A's layout was changed

A put one bolt fore and one aft of the 18 mm bore, 12 mm from its axis (lever 24 mm), with a side nut trap. On the
real geometry that is not buildable:
- an M5 hole 12 mm from the bore axis leaves **0.25 mm** to the bore;
- the 12 mm washer trap would cut through the bushing seat;
- a boss fore of the stay sits under the 10 mm XLPE back rails, and a boss aft sits under the spreader.

A first layout, point-symmetric at ±15° inside the stay silhouette (12 mm washers), works out at strength 1.01 and
fatigue **0.79** (washer bearing). With 15 mm washers it reaches 1.05, but the boss then stands proud of the wearer
face. The fore/aft lever is too short inside the silhouette.

### 3.2 Layout chosen (joint search over about 210 layouts, 12 and 15 mm washers, on the it0 cut)

Per stay, positions in mm about the bore axis (x outboard, y aft):
- bolt 1 at **(16.4, 10.0)**, outboard-aft;
- bolt 2 at **(−19.0, 5.0)**, inboard-aft, its boss merging into the branch root.

Placement rules (`frame_h1.boss_envelope`, all satisfied):
- No boss stands proud of the wearer face, where the XLPE rails sit.
- The outboard boss stands proud of the bag face only outboard of the spreader edge (x 123.4 > 121) and inside the
  bag envelope (local y 18.0 < 18.5).
- The bosses end at z 252, 3 mm below the z 255 bottom edge of the z 260 spreader clip.
- The clip sections at z 166 / 260 / 400 are identical to today's.

| part | spec |
|---|---|
| bolt | Ti gr5 M5 × 45 **DIN 7984 low head** (3.5 mm), 4 in all. The head top at z 254.5 clears the z 255 clip band; an ISO 4762 head would reach z 256. |
| washers | M5 × 12 × 1.0 under the head and under the nut (12 mm OD is load-bearing) |
| nut | A2 M5 × 4 in a hex side trap: the outboard trap opens outward, the inboard one toward the wearer face, so it does not cut the branch |
| plugs | head bears at z 250 (16 mm plug in the upper half), nut washer at z 212 (22 mm plug in the lower half) |
| holes | printed 4.8, reamed 5.1. The bolts are fitted: they take the shear, so no dowels. |
| torque | 1.0 N m snug + blue threadlocker. **Preload is not credited.** |

### 3.3 Joint check (`frame_h1.joint_check`, all 42 sets, both stays)

Contact model:
- the real z 234 voxel cut of each side (stay, bosses and the branch crossing the split) acts as a rigid dry face;
- the contact takes no tension (contact stiffness E_hot / 10 mm, ASSUMPTION);
- the bolts are tension-only springs (Ti, grip 38 mm);
- active-set solution, exact for this piecewise-linear problem.

Bolt force is multiplied by **1.25 prying** (team B ASSUMPTION). Static at the factored load; fatigue at C1 × 1.6 /
factor against 0.30 × the knocked-down allowable.

| check | capacity | strength margin | fatigue margin (1.6 g) |
|---|---|---:|---:|
| washer bearing on the plug (load along frame z, in the layers: 0.8 × 88) | 6524 N | 2.22 | 1.33 |
| plug shear-out, 2 planes × min plug 16 mm × 12, at 0.6 × 0.8 × 47 (interlayer) | 8663 N | 2.95 | 1.77 |
| **boss bending + prying**: cantilever from the stay wall to the bolt (a = r_bolt − 13.4), depth 16, width 16, release layer FI on the rotated stress (B's check, missing in A) | | 2.04 | **1.22** |
| Ti bolt tension 0.7 UTS × As / thread fatigue 0.25 UTS × As (B rule) | 8896 / 3177 N | 3.03 | 2.16 |
| fitted-bolt hole bearing (shear V / 2 + torque / (2 r)) | 5745 N | 7.51 | 5.57 |
| Ti bolt shear | 7194 N | 9.41 | |
| dry-face contact pressure vs 0.8 × 88 | 70.4 MPa | 1.96 | |

- Worst factored bolt force: **2933 N**, prying included (C3 side-hill, IM3 couple, 23 in).
- The branch crosses the split and carries up to 484 N of tension (factored). The contact model has the bolts carry
  it; nothing is assumed of the branch faces.
- **Joint: strength 1.96, fatigue 1.22. It is now the weakest fatigue item of the frame** (body 1.28), as the judge
  expected.
- Sensitivity: at 15 mm washers the best layout was 1.24; at a 12 mm washer with the bolts inside the stay
  silhouette it was 0.79. The bag-side outboard boss is what makes the joint work.

### 3.4 Bore continuity for the crown-leg sleeve

- **Ligaments** from every joint void to the 18.0 mm bore, sampled on a 0.2 mm grid at each feature height:
  - bolt hole 7.8 mm;
  - washer and nut traps 4.0 mm;
  - counterbore 3.87 mm;
  - all against the 3.6 mm wall floor (margin 1.07).
- **Leg travel.** The crown leg bottom sits at z 171 / 273 / 374 for torso 15 / 19 / 23 in. At 15 in the 70 mm
  UHMWPE low bushing straddles the split (z 171–241), so the bore must be one hole.
- **How continuity is made.**
  - The fitted bolts locate the halves (5.1 reamed holes, about ±0.05 mm).
  - The bores are printed at 17.4 and **reamed to 18.0 through both halves after bolt-up**, so the step is zero by
    construction.
  - The halves become a matched pair.
  - The sleeve keep-out walls (4.41 mm) are intact around the whole bore (`keepouts`: sleeve present 1.00, bore
    empty 1.00).

## 4. Interface keep-outs (verify)

| item | result |
|---|---|
| sleeve walls L/R, pawl housing, hip pivot, pads (as in today's printed body) | 100 % present |
| bores L/R, spine channel | 100 % empty |
| bag fairleads (8) | 100 % present |
| voxels outside the envelope | 0 |
| bosses: wearer face flush; bag side outboard of the spreader and inside the envelope; \|x\| ≤ 142 < 152; top z 252 < clip z 255; low bolt head top z 254.5 < 255 | all pass |
| spreader clip sections z 166 / 260 / 400 | identical to today |
| **spreader bottom tab, z 119** | **changed.** The H1 stay is 4.0 mm fuller on the bag side (aft surface y 10.0 against 6.0, from the growth at the strut junction). The 4.5 mm bonded stand-off pad becomes 0.5 mm. Tab position unchanged. |
| pad voxels of the raster that the body does not reach (456 voxels, e.g. load-wing lash points) | floating in today's raster too, not in today's print; unchanged |

## 5. Mass and cost

Mass booking ([frame_mass_h1.json](frame_mass_h1.json)) on the verdict's basis: fixed interfaces 239.4 g, spreader
162.3 g, pack rest 2739.5 g. The body is booked on the same 2 mm raster as today (823.2 − (823.24 − 757.72)).

**Dowel correction.** Today's frame is 1062.6 g + 18.5 g for the z 234 dowels and MMA that were never booked =
**1081.1 g**. The correction is added to `frame_mass_production.json` as new keys (`z234_dowels_mma_g`,
`frame_g_with_dowels`). `frame_g` is left at 1062.6 for its consumers until the release below.

Cost, quantity 1, PRODUCTION.md basis: about $437 against $427 today.
- Filament $66.0 (764 g + 8 %, $80/kg) and 15 % reprint allowance $9.9.
- Machine 27 h $27.3.
- Joint hardware about $20: 4 Ti M5 × 45 at $4.50 (ASSUMPTION, A's figure), nuts and washers $2.
- Dowels −$4.50.
- Everything else as today, including the $207 spreader.

## 6. Mass reductions that keep the SF (not taken)

| idea | Δ g (est.) | condition |
|---|---:|---|
| CA-1 proves 0.40 → re-run the push at 0.40 | −50 to −70 (A's 686 g body is an unconverged estimate) | body fatigue 1.71 now, so there is room. The joint (1.22) does not get lighter: it is set by the boss and washer. Buckling 1.31 then governs the branches. |
| A2 nuts and washers to Ti | −6 | cost |
| outboard boss length: plug 22 → 18 mm in the lower half | −2 | boss bending uses the shorter upper plug, so no effect |
| thin the sleeve outer surface to the 3.6 mm wall floor (judge's untried idea) | −15 to −35 | needs a new bushing-seat keep-out; the fatigue hot spot sits at the sleeve wall, so it must be re-solved |

## 7. To release: exactly what changes in the released files

Not done here (owner rule: released print files and `geometry.yaml` are not edited by this task). On release:

> **Update BL-027 (2026-11-12):** `print/frame_h1/` now holds body **H1-G0.55-B1/2.5** (H1 + BL-024 lower-body
> growth + BL-027 mid bar +1.0 mm / upper branches +2.5 mm + 28 mm IM3 cheeks), each flat half one closed shell
> (`analysis/h1_buckling.md` section 6). Release numbers change accordingly: printed body **800.7 g** raster
> (808.5 g mesh) instead of 757.7 g, so in items 2 and 4 use the frame_mass_h1.json value once the orchestrator
> re-books it (body +42.9 g over H1); print time about 28.6 h; the body row in item 6 becomes the BL-024 / BL-027 sim
> numbers (strength 1.58, fatigue 1.175 sim / 1.205 beam, creep 2.51), the joint row 1.95 / 1.25 beam, and the
> buckling row **1.22 sim / 1.36 beam**. R1 is still held for MT-1 (CINCH_STATIC, BL-024).

1. **`designs/pack_5200/print/frame/`**
   - Replace `genframe_assembled.stl`, `genframe_lower_flat.stl/.3mf` and `genframe_upper_flat.stl/.3mf` with
     `print/frame_h1/h1_assembled.stl`, `h1_lower_flat.*` and `h1_upper_flat.*` (renamed). Keep
     `genframe_barrier.*` and `fiber_paths_principal_stress.csv`.
   - Note: the released flat halves today (441 cm³ together) do not match the released assembled body (738 cm³).
     They appear to be from an older body. Check this before anything is printed from that folder.
2. **`print/frame/PRODUCTION.md`**
   - "What you are printing": body 823 → **758 g**, frame 1063 → **1025 g**, with spreader 1225 → **1187 g**. The
     split stays at z 234; the "2 mm check of the continuous body" bullet becomes the bolted-joint statement (§3).
   - "Bond and hardware" step 3: dowels + MMA + flame treatment → 4 Ti M5 × 45 DIN 7984, 12 mm washers, nuts in traps,
     1.0 N m, ream the 18.0 bores through both halves after bolt-up.
   - Anneal: the rod goes through bores printed at 17.4 (it still fits a 16 mm rod).
   - Spreader step 5: the z 119 stand-off pad goes from 4.5 to 0.5 mm.
   - QC: add "joint does not open under T1" and "re-torque after 24 h".
   - Unit cost table: filament 71.1 → 66.0, reprint 10.7 → 9.9, machine 27.4 → 27.3, carbon dowels 4.5 → 0, new
     line "joint bolts, nuts, washers 20.0". Total about 437.
   - Print time about 27 h (unchanged).
3. **`print/frame/README.md`**: Assembly steps 1–3 (dowels, MMA) → the steps in `print/frame_h1/README.md` §3–5.
4. **`analysis/frame_mass_production.json`**: `printed_body_g` 823.2 → **757.7**, `printed_body_basis` → H1 raster.
   Add `z234_joint_g` **28.0** (hardware, no dowels). `frame_g` 1062.6 → **1025.1**. Drop the interim
   `frame_g_with_dowels`.
5. **`geometry.yaml`**: regenerate with `designs/pack_5200/build_geometry.py`; do not hand-edit. It reads `frame_g`
   from the JSON. Expected CORRIE B.2 belt M **3926.9 g (8.66 lb)**.
6. **`analysis/rev_c_verification.md`** body row: 1.51 / 1.04 / 2.23 → **1.45 / 1.28 / 2.73**. Add a joint row
   (1.96 / 1.22) and a buckling row (1.31).
7. **Spreader package** (`cut/spreader/`): z 119 stand-off pad thickness 4.5 → 0.5 mm. Re-run `spreader.evaluate`
   on the H1 body: the stays are 0.75 × as stiff in torsion, and the clip sections are unchanged.
8. **viz3d**: point `generative_frame_dir` at the released folder (or at `outputs/pack3d_h1/` meanwhile).
   `h1_frame.glb` is a drop-in.
9. `data/materials/polymers/pa12_cf_fdm_paht.yaml`: **no change** until CA-1. `fatigue_1e5_ratio` stays 0.30.

## 8. Open risks and coupons

| item | margin | rests on | coupon |
|---|---:|---|---|
| joint fatigue: boss bending + prying | 1.22 | prying 1.25 (B), cantilever boss model, no preload | **CA-5**, the eccentric stub pull (`tests_physical/CA1_fatigue_rig.md` §7) |
| body fatigue | 1.28 | PAHT-CF 0.30 at 1e5 | **CA-1** (flip at 0.234) |
| branch buckling | 1.31 | K 1, E × 0.42 | T4b with a dial on the branch |
| load path | | beam-model loads are independent of the body; the H1 body is 0.75 × as stiff in torsion (D was 0.45) | T1 deflection, D-T1-style torsion check on the first article |
| feel | | 25 % softer in torsion than today | owner's carry test |

## Assumptions

- ASSUMPTION: voxel noise reserve 2 % (accept iterates at ≥ 1.02); push settings as the judge's (cap 0.45, u_lo 0.85).
- ASSUMPTION: prying factor 1.25 on bolt tension (team B); contact length 10 mm at the hot modulus; no preload credit.
- ASSUMPTION: boss bending is a cantilever from the stay outer radius 13.41 mm to the bolt axis, depth = the shorter
  plug (16 mm), width = boss diameter (16 mm). The stress is rotated into the print frame and checked with the
  release layer FI.
- ASSUMPTION: the fitted 5.1 mm bolts take all the shear (V / 2 + T / 2r); friction is not credited.
- ASSUMPTION: Ti M5 × 45 $4.50 each; A2 nut and washer masses from the ISO 4032 and 12 × 5.3 × 1 geometry.
- ASSUMPTION: the spreader half-width is 121 mm (242 mm part, PRODUCTION.md), centred.
- ASSUMPTION: print mass = mesh volume × 1.06 g/cm³; the booked mass uses the analysis raster, as today's does.
